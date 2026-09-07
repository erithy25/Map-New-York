#include "World/NYCWaterActor.h"

#include "CoreAdapter/NYCGeo.h"
#include "NYCSimRuntime.h"
#include "World/NYCSimWorldSettings.h"

#include "Components/DynamicMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Dom/JsonObject.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Generators/RectangleMeshGenerator.h"
#include "HAL/FileManager.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	const FName ParamWaterMask(TEXT("WaterMask"));
	const FName ParamHasMask(TEXT("HasMask"));
	const FName ParamTileOrigin(TEXT("TileOriginUE"));
	const FName ParamFlowVector(TEXT("FlowVector"));
	const FName ParamWaterLevel(TEXT("WaterLevelCm"));
	const FName ParamTidal(TEXT("Tidal"));
	const FName ParamKind(TEXT("KindIndex"));

	constexpr double MetresToUE = 100.0;
	constexpr double TileSizeM = 1000.0;
}

ANYCWaterActor::ANYCWaterActor()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.05f; // 20 Hz: the geometry only changes when the camera crosses a tile edge
	SetCanBeDamaged(false);

	RootScene = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootScene->SetMobility(EComponentMobility::Movable);
	SetRootComponent(RootScene);
}

void ANYCWaterActor::BeginPlay()
{
	Super::BeginPlay();

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	WaterMaterial = Cast<UMaterialInterface>(Settings.WaterMaterialPath.TryLoad());
	if (!WaterMaterial)
	{
		WaterMaterial = UMaterial::GetDefaultMaterial(MD_Surface);
		UE_LOG(LogNYCSim, Warning,
			TEXT("Water: %s could not be loaded; the engine default surface material is used so the water is still ")
			TEXT("visible. Run Content/Python/import_assets.py to create M_NYC_Water."),
			*Settings.WaterMaterialPath.ToString());
	}

	LoadWaterJson();

	// Far ring: four strips whose sizes never change (only their position follows the camera).
	const double FarHalfM = FMath::Max(2000.0, Settings.WaterFarExtentKilometres * 1000.0);
	const double NearHalfM = (WaterTiles.Num() > 0) ? (2 * Settings.WaterNearRadiusTiles + 1) * TileSizeM * 0.5 : 0.0;
	const double GapM = FMath::Max(0.0, FarHalfM - NearHalfM);
	const int32 FarQuads = FMath::Clamp(Settings.WaterFarQuads, 4, 512);

	FarComponents.Reset();
	FarMaterials.Reset();
	if (GapM > 1.0)
	{
		// 0 = north, 1 = south, 2 = west, 3 = east (NYC_TM axes; the offsets are applied in UpdateFarRing).
		const double Sizes[4][2] = {
			{2.0 * FarHalfM, GapM},
			{2.0 * FarHalfM, GapM},
			{GapM, 2.0 * NearHalfM},
			{GapM, 2.0 * NearHalfM},
		};
		for (int32 i = 0; i < 4; ++i)
		{
			const double WidthM = Sizes[i][0];
			const double HeightM = Sizes[i][1];
			if (WidthM <= 1.0 || HeightM <= 1.0)
			{
				continue;
			}
			UDynamicMeshComponent* Component = NewObject<UDynamicMeshComponent>(this);
			Component->SetupAttachment(RootScene);
			Component->RegisterComponent();
			Component->SetMobility(EComponentMobility::Movable);
			Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetCastShadow(false);
			Component->bCastDynamicShadow = false;
			const int32 QuadsX = FMath::Max(1, FMath::RoundToInt32(FarQuads * WidthM / (2.0 * FarHalfM)));
			const int32 QuadsY = FMath::Max(1, FMath::RoundToInt32(FarQuads * HeightM / (2.0 * FarHalfM)));
			SetPatchGeometry(Component, WidthM * MetresToUE, HeightM * MetresToUE, QuadsX, QuadsY);
			UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(WaterMaterial, this);
			MID->SetScalarParameterValue(ParamHasMask, 0.f);
			MID->SetScalarParameterValue(ParamTidal, 1.f);
			MID->SetScalarParameterValue(ParamKind, static_cast<float>(KindIndex(TEXT("ocean"))));
			Component->SetMaterial(0, MID);
			FarComponents.Add(Component);
			FarMaterials.Add(MID);
		}
	}

	UpdateAllMaterialParameters();
	UE_LOG(LogNYCSim, Log, TEXT("Water: %d water tiles, level %.3f m, far ring %.0f km, %d far strips%s"),
		WaterTiles.Num(), WaterLevelMetres, FarHalfM / 1000.0, FarComponents.Num(),
		LoadError.IsEmpty() ? TEXT("") : *FString::Printf(TEXT("  [%s]"), *LoadError));
}

void ANYCWaterActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	Patches.Reset();
	WaterTiles.Reset();
	Super::EndPlay(EndPlayReason);
}

bool ANYCWaterActor::ReloadWaterData()
{
	WaterTiles.Reset();
	MasksLoaded = 0;
	bHasCameraTile = false;
	LastCameraTile = FIntPoint(MIN_int32, MIN_int32);
	for (FPatch& P : Patches)
	{
		P.bInUse = false;
		if (P.Component.IsValid())
		{
			P.Component->SetVisibility(false);
		}
	}
	return LoadWaterJson();
}

bool ANYCWaterActor::LoadWaterJson()
{
	LoadError.Empty();
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString Path = UNYCSimWorldSettings::ResolveProjectPath(Settings.UnrealWaterJsonPath);
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		LoadError = FString::Printf(TEXT("cannot read %s"), *Path);
		UE_LOG(LogNYCSim, Warning, TEXT("Water: %s (only the far ocean ring is rendered)"), *LoadError);
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		LoadError = FString::Printf(TEXT("%s is not valid JSON"), *Path);
		UE_LOG(LogNYCSim, Error, TEXT("Water: %s"), *LoadError);
		return false;
	}
	int32 SchemaVersion = 0;
	if (!Root->TryGetNumberField(TEXT("schema_version"), SchemaVersion) || SchemaVersion != 1)
	{
		LoadError = FString::Printf(TEXT("%s: schema_version %d unsupported (expected 1)"), *Path, SchemaVersion);
		UE_LOG(LogNYCSim, Error, TEXT("Water: %s"), *LoadError);
		return false;
	}
	Root->TryGetNumberField(TEXT("water_level_m"), WaterLevelMetres);

	// §14.1 flow: the tide snapshot the pipeline captured; the live poller overwrites it through SetTide().
	const TSharedPtr<FJsonObject>* Flow = nullptr;
	if (Root->TryGetObjectField(TEXT("flow"), Flow) && Flow && Flow->IsValid())
	{
		(*Flow)->TryGetStringField(TEXT("station"), TideStation);
		(*Flow)->TryGetNumberField(TEXT("current_speed_mps"), CurrentSpeedMps);
		(*Flow)->TryGetNumberField(TEXT("current_dir_deg"), CurrentDirDeg);
		double Level = 0.0;
		if ((*Flow)->TryGetNumberField(TEXT("water_level_m"), Level))
		{
			WaterLevelMetres = Level;
		}
	}

	const TSharedPtr<FJsonObject>* Tiles = nullptr;
	if (Root->TryGetObjectField(TEXT("tiles"), Tiles) && Tiles && Tiles->IsValid())
	{
		for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : (*Tiles)->Values)
		{
			FIntPoint TileIndex;
			if (!NYCGeo::ParseTileName(Pair.Key, TileIndex) || !Pair.Value.IsValid())
			{
				continue;
			}
			const TSharedPtr<FJsonObject>* Entry = nullptr;
			if (!Pair.Value->TryGetObject(Entry) || !Entry || !Entry->IsValid())
			{
				continue;
			}
			FWaterTile T;
			T.Tile = TileIndex;
			double Fraction = 0.0;
			(*Entry)->TryGetNumberField(TEXT("water_fraction"), Fraction);
			T.WaterFraction = static_cast<float>(FMath::Clamp(Fraction, 0.0, 1.0));
			(*Entry)->TryGetStringField(TEXT("dominant_kind"), T.DominantKind);
			(*Entry)->TryGetBoolField(TEXT("tidal"), T.bTidal);
			double Shoreline = 0.0;
			(*Entry)->TryGetNumberField(TEXT("shoreline_m"), Shoreline);
			T.ShorelineMetres = static_cast<float>(Shoreline);
			(*Entry)->TryGetNumberField(TEXT("structures"), T.Structures);
			if (T.WaterFraction > 0.f)
			{
				WaterTiles.Add(TileIndex, MoveTemp(T));
			}
		}
	}
	return true;
}

void ANYCWaterActor::SetTide(double InWaterLevelMetres, double InCurrentSpeedMps, double InCurrentDirDeg, bool bPredicted)
{
	if (FMath::IsFinite(InWaterLevelMetres) && FMath::Abs(InWaterLevelMetres) < 10.0)
	{
		WaterLevelMetres = InWaterLevelMetres;
	}
	if (FMath::IsFinite(InCurrentSpeedMps) && InCurrentSpeedMps >= 0.0 && InCurrentSpeedMps < 10.0)
	{
		CurrentSpeedMps = InCurrentSpeedMps;
	}
	if (FMath::IsFinite(InCurrentDirDeg))
	{
		CurrentDirDeg = InCurrentDirDeg;
	}
	bTidePredicted = bPredicted;
	LastTideUpdateSeconds = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	// The actor itself never moves: every patch is positioned in world space, so the surface height is applied there.
	UpdateAllMaterialParameters();
}

FIntPoint ANYCWaterActor::CameraTileNow(bool& bOutValid) const
{
	bOutValid = false;
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (!PC)
	{
		return FIntPoint::ZeroValue;
	}
	FVector Location = FVector::ZeroVector;
	FRotator Rotation = FRotator::ZeroRotator;
	PC->GetPlayerViewPoint(Location, Rotation);
	bOutValid = true;
	return NYCGeo::TileOfUE(Location);
}

void ANYCWaterActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	bool bValid = false;
	const FIntPoint CameraTile = CameraTileNow(bValid);
	if (!bValid)
	{
		return;
	}
	if (!bHasCameraTile || CameraTile != LastCameraTile)
	{
		LastCameraTile = CameraTile;
		bHasCameraTile = true;
		RebuildNearPatches(CameraTile);
		UpdateFarRing(CameraTile);
	}

	// One mask decode per tick at most: 501 x 501 PNGs cost well under a millisecond and the set changes rarely.
	for (FPatch& Patch : Patches)
	{
		if (!Patch.bInUse)
		{
			continue;
		}
		FWaterTile* Tile = WaterTiles.Find(Patch.Tile);
		if (Tile && !Tile->bMaskTried)
		{
			if (EnsureMask(*Tile))
			{
				UpdatePatchMaterial(Patch, *Tile);
			}
			break;
		}
	}
}

void ANYCWaterActor::RebuildNearPatches(const FIntPoint& CameraTile)
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const int32 Radius = FMath::Clamp(Settings.WaterNearRadiusTiles, 0, 12);
	const int32 Quads = FMath::Clamp(Settings.WaterPatchQuads, 4, 256);

	for (FPatch& P : Patches)
	{
		P.bInUse = false;
	}

	TArray<FIntPoint> Wanted;
	Wanted.Reserve((2 * Radius + 1) * (2 * Radius + 1));
	for (int32 Dy = -Radius; Dy <= Radius; ++Dy)
	{
		for (int32 Dx = -Radius; Dx <= Radius; ++Dx)
		{
			const FIntPoint Tile(CameraTile.X + Dx, CameraTile.Y + Dy);
			if (WaterTiles.Contains(Tile))
			{
				Wanted.Add(Tile);
			}
		}
	}

	// Keep the patches that already show a wanted tile, so crossing a tile boundary only touches the ring's edge.
	TSet<FIntPoint> Covered;
	for (FPatch& P : Patches)
	{
		if (P.Component.IsValid() && Wanted.Contains(P.Tile) && !Covered.Contains(P.Tile))
		{
			P.bInUse = true;
			Covered.Add(P.Tile);
		}
	}
	for (const FIntPoint& Tile : Wanted)
	{
		if (Covered.Contains(Tile))
		{
			continue;
		}
		FPatch* Free = Patches.FindByPredicate([](const FPatch& P) { return !P.bInUse && P.Component.IsValid(); });
		if (!Free)
		{
			UDynamicMeshComponent* Component = AcquirePatch(Quads);
			if (!Component)
			{
				break;
			}
			FPatch New;
			New.Component = Component;
			New.Quads = Quads;
			Patches.Add(New);
			Free = &Patches.Last();
		}
		Free->bInUse = true;
		Free->Tile = Tile;
		Covered.Add(Tile);

		const FVector Centre = NYCGeo::TileCentreUE(Tile, 0.0);
		Free->Component->SetWorldLocation(FVector(Centre.X, Centre.Y, WaterLevelMetres * MetresToUE));
		Free->Component->SetVisibility(true);
		if (FWaterTile* WaterTile = WaterTiles.Find(Tile))
		{
			UpdatePatchMaterial(*Free, *WaterTile);
		}
	}

	ActivePatchCount = 0;
	for (FPatch& P : Patches)
	{
		if (!P.Component.IsValid())
		{
			continue;
		}
		P.Component->SetVisibility(P.bInUse);
		ActivePatchCount += P.bInUse ? 1 : 0;
	}
}

void ANYCWaterActor::UpdateFarRing(const FIntPoint& CameraTile)
{
	if (FarComponents.Num() == 0)
	{
		return;
	}
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const double FarHalfM = FMath::Max(2000.0, Settings.WaterFarExtentKilometres * 1000.0);
	const double NearHalfM = (WaterTiles.Num() > 0) ? (2 * Settings.WaterNearRadiusTiles + 1) * TileSizeM * 0.5 : 0.0;
	const double MidM = (FarHalfM + NearHalfM) * 0.5;
	const FVector2D CentreTm = NYCGeo::TileOriginMetres(CameraTile) + FVector2D(TileSizeM * 0.5, TileSizeM * 0.5);

	// Offsets in NYC_TM (east, north) for north, south, west, east strips, in the order they were created.
	const FVector2D Offsets[4] = {
		FVector2D(0.0, MidM),
		FVector2D(0.0, -MidM),
		FVector2D(-MidM, 0.0),
		FVector2D(MidM, 0.0),
	};
	const int32 Count = FMath::Min(FarComponents.Num(), 4);
	for (int32 i = 0; i < Count; ++i)
	{
		if (!FarComponents[i])
		{
			continue;
		}
		const FVector Position = NYCGeo::NycTmToUE(
			FVector(CentreTm.X + Offsets[i].X, CentreTm.Y + Offsets[i].Y, WaterLevelMetres));
		FarComponents[i]->SetWorldLocation(Position);
	}
}

UDynamicMeshComponent* ANYCWaterActor::AcquirePatch(int32 Quads)
{
	UDynamicMeshComponent* Component = NewObject<UDynamicMeshComponent>(this);
	if (!Component)
	{
		return nullptr;
	}
	Component->SetupAttachment(RootScene);
	Component->RegisterComponent();
	Component->SetMobility(EComponentMobility::Movable);
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetCastShadow(false);
	Component->bCastDynamicShadow = false;
	SetPatchGeometry(Component, TileSizeM * MetresToUE, TileSizeM * MetresToUE, Quads, Quads);
	UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(WaterMaterial, this);
	Component->SetMaterial(0, MID);
	PatchComponents.Add(Component);
	return Component;
}

void ANYCWaterActor::SetPatchGeometry(UDynamicMeshComponent* Component, double WidthCm, double HeightCm, int32 QuadsX, int32 QuadsY)
{
	using namespace UE::Geometry;
	FRectangleMeshGenerator Generator;
	Generator.Origin = FVector3d::Zero();
	Generator.Normal = FVector3f::UnitZ();
	Generator.Width = WidthCm;
	Generator.Height = HeightCm;
	// The generator's defaults put the rectangle in the XY plane with a +Z normal, which is what water needs.
	Generator.WidthVertexCount = FMath::Max(2, QuadsX + 1);
	Generator.HeightVertexCount = FMath::Max(2, QuadsY + 1);
	Generator.Generate();

	FDynamicMesh3 Mesh(&Generator);
	Component->SetMesh(MoveTemp(Mesh));
	Component->NotifyMeshUpdated();
}

void ANYCWaterActor::UpdatePatchMaterial(FPatch& Patch, const FWaterTile& Tile)
{
	if (!Patch.Component.IsValid())
	{
		return;
	}
	UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(Patch.Component->GetMaterial(0));
	if (!MID)
	{
		MID = UMaterialInstanceDynamic::Create(WaterMaterial, this);
		Patch.Component->SetMaterial(0, MID);
	}
	Patch.Material = MID;

	const FVector2D Origin = NYCGeo::TileOriginMetres(Tile.Tile);
	const FVector NorthWest = NYCGeo::NycTmToUE(FVector(Origin.X, Origin.Y + TileSizeM, 0.0));
	MID->SetVectorParameterValue(ParamTileOrigin, FLinearColor(
		static_cast<float>(NorthWest.X), static_cast<float>(NorthWest.Y), static_cast<float>(TileSizeM * MetresToUE), 0.f));
	MID->SetScalarParameterValue(ParamKind, static_cast<float>(KindIndex(Tile.DominantKind)));
	MID->SetScalarParameterValue(ParamTidal, Tile.bTidal ? 1.f : 0.f);
	if (Tile.MaskTexture.IsValid())
	{
		MID->SetTextureParameterValue(ParamWaterMask, Tile.MaskTexture.Get());
		MID->SetScalarParameterValue(ParamHasMask, 1.f);
	}
	else
	{
		// No mask yet: the patch covers the whole tile at the measured coverage so it never flashes as a hard square.
		MID->SetScalarParameterValue(ParamHasMask, 0.f);
	}
	MID->SetScalarParameterValue(ParamWaterLevel, static_cast<float>(WaterLevelMetres * MetresToUE));

	const double DirRad = FMath::DegreesToRadians(CurrentDirDeg);
	const FVector FlowUE = NYCGeo::DirectionToUE(FVector(FMath::Cos(DirRad), FMath::Sin(DirRad), 0.0));
	MID->SetVectorParameterValue(ParamFlowVector, FLinearColor(
		static_cast<float>(FlowUE.X), static_cast<float>(FlowUE.Y), static_cast<float>(Tile.bTidal ? CurrentSpeedMps : 0.0), 0.f));
}

void ANYCWaterActor::UpdateAllMaterialParameters()
{
	const double DirRad = FMath::DegreesToRadians(CurrentDirDeg);
	const FVector FlowUE = NYCGeo::DirectionToUE(FVector(FMath::Cos(DirRad), FMath::Sin(DirRad), 0.0));
	const FLinearColor Flow(static_cast<float>(FlowUE.X), static_cast<float>(FlowUE.Y), static_cast<float>(CurrentSpeedMps), 0.f);
	const float LevelCm = static_cast<float>(WaterLevelMetres * MetresToUE);

	for (const TObjectPtr<UMaterialInstanceDynamic>& MID : FarMaterials)
	{
		if (MID)
		{
			MID->SetVectorParameterValue(ParamFlowVector, Flow);
			MID->SetScalarParameterValue(ParamWaterLevel, LevelCm);
		}
	}
	for (FPatch& Patch : Patches)
	{
		if (const FWaterTile* Tile = WaterTiles.Find(Patch.Tile))
		{
			UpdatePatchMaterial(Patch, *Tile);
		}
	}
	// Move every component to the new surface height.
	for (FPatch& Patch : Patches)
	{
		if (Patch.Component.IsValid())
		{
			const FVector Location = Patch.Component->GetComponentLocation();
			Patch.Component->SetWorldLocation(FVector(Location.X, Location.Y, LevelCm));
		}
	}
	for (const TObjectPtr<UDynamicMeshComponent>& Component : FarComponents)
	{
		if (Component)
		{
			const FVector Location = Component->GetComponentLocation();
			Component->SetWorldLocation(FVector(Location.X, Location.Y, LevelCm));
		}
	}
}

bool ANYCWaterActor::EnsureMask(FWaterTile& Tile)
{
	if (Tile.bMaskTried)
	{
		return Tile.MaskSize > 0;
	}
	Tile.bMaskTried = true;

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString Dir = UNYCSimWorldSettings::ResolveProjectPath(Settings.WaterMaskDir);
	const FString Path = Dir / (NYCGeo::TileName(Tile.Tile) + TEXT(".png"));
	if (!IFileManager::Get().FileExists(*Path))
	{
		return false;
	}
	FImage Image;
	if (!FImageUtils::LoadImage(*Path, Image))
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Water: cannot decode mask %s"), *Path);
		return false;
	}
	if (Image.SizeX != Image.SizeY || Image.SizeX < 2)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Water: mask %s is %dx%d, expected a square"), *Path, Image.SizeX, Image.SizeY);
		return false;
	}
	if (Image.Format != ERawImageFormat::G8)
	{
		Image.ChangeFormat(ERawImageFormat::G8, EGammaSpace::Linear);
	}
	const TArrayView64<uint8> Grey = Image.AsG8();
	Tile.MaskSize = Image.SizeX;
	Tile.Mask.SetNumUninitialized(Image.SizeX * Image.SizeY);
	FMemory::Memcpy(Tile.Mask.GetData(), Grey.GetData(), static_cast<SIZE_T>(Tile.Mask.Num()));

	UTexture2D* Texture = UTexture2D::CreateTransient(Tile.MaskSize, Tile.MaskSize, PF_G8,
		*FString::Printf(TEXT("T_WaterMask_%s"), *NYCGeo::TileAssetName(Tile.Tile)));
	if (Texture)
	{
		Texture->SRGB = false;
		Texture->NeverStream = true;
		Texture->Filter = TF_Bilinear;
		Texture->AddressX = TA_Clamp;
		Texture->AddressY = TA_Clamp;
		Texture->CompressionSettings = TC_Grayscale;
		if (FTexturePlatformData* PlatformData = Texture->GetPlatformData())
		{
			if (PlatformData->Mips.Num() > 0)
			{
				FTexture2DMipMap& Mip = PlatformData->Mips[0];
				if (void* Dest = Mip.BulkData.Lock(LOCK_READ_WRITE))
				{
					FMemory::Memcpy(Dest, Tile.Mask.GetData(), static_cast<SIZE_T>(Tile.Mask.Num()));
				}
				Mip.BulkData.Unlock();
			}
		}
		Texture->UpdateResource();
		MaskTextures.Add(Texture); // UPROPERTY anchor: the texture lives exactly as long as this actor
		Tile.MaskTexture = Texture;
	}
	++MasksLoaded;
	return true;
}

int32 ANYCWaterActor::KindIndex(const FString& Kind)
{
	if (Kind.Equals(TEXT("river"), ESearchCase::IgnoreCase)) return 0;
	if (Kind.Equals(TEXT("bay"), ESearchCase::IgnoreCase)) return 1;
	if (Kind.Equals(TEXT("ocean"), ESearchCase::IgnoreCase)) return 2;
	if (Kind.Equals(TEXT("lake"), ESearchCase::IgnoreCase)) return 3;
	if (Kind.Equals(TEXT("pond"), ESearchCase::IgnoreCase)) return 4;
	if (Kind.Equals(TEXT("canal"), ESearchCase::IgnoreCase)) return 5;
	if (Kind.Equals(TEXT("basin"), ESearchCase::IgnoreCase)) return 6;
	return 7;
}

FNYCWaterSample ANYCWaterActor::SampleWaterAtUE(const FVector& UELocation) const
{
	FNYCWaterSample Out;
	Out.SurfaceZ = WaterLevelMetres * MetresToUE;
	Out.DepthBelowSurface = Out.SurfaceZ - UELocation.Z;

	const FVector Tm = NYCGeo::UEToNycTm(UELocation);
	const FIntPoint Tile = NYCGeo::TileOfNycTm(Tm.X, Tm.Y);
	const FWaterTile* WaterTile = WaterTiles.Find(Tile);
	if (!WaterTile)
	{
		// Outside every mapped tile the far ring is open water, but only beyond the mapped extent; inside the city
		// a tile without a record simply has no water.
		Out.bIsWater = false;
		return Out;
	}
	Out.Kind = WaterTile->DominantKind;
	Out.bTidal = WaterTile->bTidal;

	if (WaterTile->MaskSize > 1 && WaterTile->Mask.Num() == WaterTile->MaskSize * WaterTile->MaskSize)
	{
		const FVector2D Origin = NYCGeo::TileOriginMetres(Tile);
		const double Fx = FMath::Clamp((Tm.X - Origin.X) / TileSizeM, 0.0, 1.0) * (WaterTile->MaskSize - 1);
		const double Fy = (1.0 - FMath::Clamp((Tm.Y - Origin.Y) / TileSizeM, 0.0, 1.0)) * (WaterTile->MaskSize - 1);
		const int32 X0 = FMath::Clamp(FMath::FloorToInt32(Fx), 0, WaterTile->MaskSize - 1);
		const int32 Y0 = FMath::Clamp(FMath::FloorToInt32(Fy), 0, WaterTile->MaskSize - 1);
		const int32 X1 = FMath::Min(X0 + 1, WaterTile->MaskSize - 1);
		const int32 Y1 = FMath::Min(Y0 + 1, WaterTile->MaskSize - 1);
		const double Tx = Fx - X0;
		const double Ty = Fy - Y0;
		const uint8* M = WaterTile->Mask.GetData();
		const double Top = M[Y0 * WaterTile->MaskSize + X0] * (1.0 - Tx) + M[Y0 * WaterTile->MaskSize + X1] * Tx;
		const double Bottom = M[Y1 * WaterTile->MaskSize + X0] * (1.0 - Tx) + M[Y1 * WaterTile->MaskSize + X1] * Tx;
		Out.Coverage = static_cast<float>((Top * (1.0 - Ty) + Bottom * Ty) / 255.0);
	}
	else
	{
		// Without the mask the only honest answer is the tile's measured coverage; a tile that is entirely water
		// (fraction >= 0.999) is water everywhere, anything else is reported as "not known to be water".
		Out.Coverage = WaterTile->WaterFraction >= 0.999f ? 1.f : 0.f;
	}
	Out.bIsWater = Out.Coverage > 0.5f;
	if (Out.bIsWater && WaterTile->bTidal)
	{
		const double DirRad = FMath::DegreesToRadians(CurrentDirDeg);
		const FVector Dir = NYCGeo::DirectionToUE(FVector(FMath::Cos(DirRad), FMath::Sin(DirRad), 0.0));
		Out.FlowVelocity = Dir * (CurrentSpeedMps * MetresToUE);
	}
	return Out;
}

void ANYCWaterActor::PrintWaterInfo(FOutputDevice& Ar) const
{
	Ar.Logf(TEXT("NYCSim water: %d tiles with water, %d masks loaded, %d active patches, %d far strips"),
		WaterTiles.Num(), MasksLoaded, ActivePatchCount, FarComponents.Num());
	Ar.Logf(TEXT("  level %.3f m NAVD88 (%.1f cm UE)  current %.2f m/s toward %.1f deg (math)  station %s  %s"),
		WaterLevelMetres, WaterLevelMetres * MetresToUE, CurrentSpeedMps, CurrentDirDeg,
		TideStation.IsEmpty() ? TEXT("(none)") : *TideStation, bTidePredicted ? TEXT("predicted") : TEXT("observed"));
	if (!LoadError.IsEmpty())
	{
		Ar.Logf(TEXT("  load error: %s"), *LoadError);
	}
}
