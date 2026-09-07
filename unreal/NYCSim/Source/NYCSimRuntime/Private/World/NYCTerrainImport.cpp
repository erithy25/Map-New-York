#include "World/NYCTerrainImport.h"

#include "CoreAdapter/NYCGeo.h"
#include "NYCSimRuntime.h"

#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

#if WITH_EDITOR
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeProxy.h"
#endif

bool UNYCTerrainImporter::LoadTerrainMeta(const FString& JsonPath, FNYCTerrainMeta& OutMeta, FString& OutError)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *JsonPath))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *JsonPath);
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = FString::Printf(TEXT("%s is not valid JSON"), *JsonPath);
		return false;
	}
	int32 SchemaVersion = 0;
	if (!Root->TryGetNumberField(TEXT("schema_version"), SchemaVersion) || SchemaVersion != 1)
	{
		OutError = FString::Printf(TEXT("%s: schema_version %d unsupported (expected 1)"), *JsonPath, SchemaVersion);
		return false;
	}
	OutMeta = FNYCTerrainMeta();
	OutMeta.SchemaVersion = SchemaVersion;
	Root->TryGetStringField(TEXT("tile"), OutMeta.Tile);
	if (!Root->TryGetNumberField(TEXT("z_min_m"), OutMeta.ZMinMetres) ||
		!Root->TryGetNumberField(TEXT("z_scale_m"), OutMeta.ZScaleMetres) ||
		!Root->TryGetNumberField(TEXT("samples"), OutMeta.Samples))
	{
		OutError = FString::Printf(TEXT("%s: z_min_m / z_scale_m / samples missing"), *JsonPath);
		return false;
	}
	Root->TryGetNumberField(TEXT("spacing_m"), OutMeta.SpacingMetres);
	Root->TryGetNumberField(TEXT("water_level_m"), OutMeta.WaterLevelMetres);
	const TArray<TSharedPtr<FJsonValue>>* SourcesJson = nullptr;
	if (Root->TryGetArrayField(TEXT("sources"), SourcesJson) && SourcesJson)
	{
		for (const TSharedPtr<FJsonValue>& V : *SourcesJson)
		{
			FString S;
			if (V.IsValid() && V->TryGetString(S))
			{
				OutMeta.Sources.Add(S);
			}
		}
	}
	if (OutMeta.Samples != SourceSamples)
	{
		OutError = FString::Printf(TEXT("%s: samples %d != %d (DATA_CONTRACTS §3)"), *JsonPath, OutMeta.Samples, SourceSamples);
		return false;
	}
	if (!FMath::IsFinite(OutMeta.ZMinMetres) || !FMath::IsFinite(OutMeta.ZScaleMetres) || OutMeta.ZScaleMetres < 0.0)
	{
		OutError = FString::Printf(TEXT("%s: z_min_m %.6f / z_scale_m %.9f out of range"), *JsonPath, OutMeta.ZMinMetres, OutMeta.ZScaleMetres);
		return false;
	}
	return true;
}

bool UNYCTerrainImporter::ReadTerrainMeta(const FString& JsonPath, FNYCTerrainMeta& OutMeta, FString& OutError)
{
	return LoadTerrainMeta(JsonPath, OutMeta, OutError);
}

bool UNYCTerrainImporter::LoadHeightmap(const FString& PngPath, int32 ExpectedSamples, TArray<uint16>& OutHeights, FString& OutError)
{
	OutHeights.Reset();
	FImage Image;
	if (!FImageUtils::LoadImage(*PngPath, Image))
	{
		OutError = FString::Printf(TEXT("cannot decode %s as an image"), *PngPath);
		return false;
	}
	if (Image.SizeX != ExpectedSamples || Image.SizeY != ExpectedSamples)
	{
		OutError = FString::Printf(TEXT("%s: %dx%d, expected %dx%d"), *PngPath, Image.SizeX, Image.SizeY, ExpectedSamples, ExpectedSamples);
		return false;
	}
	if (Image.Format != ERawImageFormat::G16)
	{
		// The contract says 16-bit grayscale; anything else is converted rather than silently misread, and the
		// conversion is reported so the pipeline can be fixed.
		UE_LOG(LogNYCSim, Warning, TEXT("%s is not 16-bit grayscale (format %d); converting to G16."), *PngPath, static_cast<int32>(Image.Format));
		Image.ChangeFormat(ERawImageFormat::G16, EGammaSpace::Linear);
	}
	const TArrayView64<uint16> Grey = Image.AsG16();
	const int64 Expected = static_cast<int64>(ExpectedSamples) * ExpectedSamples;
	if (Grey.Num() != Expected)
	{
		OutError = FString::Printf(TEXT("%s: %lld samples after decode, expected %lld"), *PngPath, Grey.Num(), Expected);
		return false;
	}
	OutHeights.SetNumUninitialized(static_cast<int32>(Expected));
	FMemory::Memcpy(OutHeights.GetData(), Grey.GetData(), static_cast<SIZE_T>(Expected) * sizeof(uint16));
	return true;
}

void UNYCTerrainImporter::ResampleToLandscapeGrid(const TArray<uint16>& Source, int32 InSourceSamples, TArray<uint16>& OutHeights)
{
	const int32 Dst = LandscapeSamples;
	OutHeights.SetNumUninitialized(Dst * Dst);
	const int32 SrcMax = InSourceSamples - 1;
	const double Ratio = static_cast<double>(SrcMax) / static_cast<double>(Dst - 1);

	// Precompute the per-axis weights: the mapping is separable and identical for rows and columns.
	TArray<int32> Index0;
	TArray<double> Weight;
	Index0.SetNumUninitialized(Dst);
	Weight.SetNumUninitialized(Dst);
	for (int32 j = 0; j < Dst; ++j)
	{
		const double S = FMath::Min(static_cast<double>(j) * Ratio, static_cast<double>(SrcMax));
		int32 I0 = FMath::FloorToInt32(S);
		if (I0 >= SrcMax)
		{
			I0 = FMath::Max(0, SrcMax - 1);
		}
		Index0[j] = I0;
		Weight[j] = S - static_cast<double>(I0);
	}

	for (int32 Row = 0; Row < Dst; ++Row)
	{
		const int32 R0 = Index0[Row];
		const int32 R1 = FMath::Min(R0 + 1, SrcMax);
		const double Wr = Weight[Row];
		const uint16* Row0 = Source.GetData() + static_cast<int64>(R0) * InSourceSamples;
		const uint16* Row1 = Source.GetData() + static_cast<int64>(R1) * InSourceSamples;
		uint16* Out = OutHeights.GetData() + static_cast<int64>(Row) * Dst;
		for (int32 Col = 0; Col < Dst; ++Col)
		{
			const int32 C0 = Index0[Col];
			const int32 C1 = FMath::Min(C0 + 1, SrcMax);
			const double Wc = Weight[Col];
			const double Top = static_cast<double>(Row0[C0]) * (1.0 - Wc) + static_cast<double>(Row0[C1]) * Wc;
			const double Bottom = static_cast<double>(Row1[C0]) * (1.0 - Wc) + static_cast<double>(Row1[C1]) * Wc;
			const double V = Top * (1.0 - Wr) + Bottom * Wr;
			Out[Col] = static_cast<uint16>(FMath::Clamp<int32>(FMath::RoundToInt32(V), 0, 65535));
		}
	}
}

FTransform UNYCTerrainImporter::LandscapeTransform(const FIntPoint& Tile, const FNYCTerrainMeta& Meta)
{
	const FVector2D Origin = NYCGeo::TileOriginMetres(Tile);
	// Landscape local +X is east and +Y is south (UE Y = -north), so the actor sits on the tile's north-west corner.
	const double LocationX = Origin.X * NYCGeo::MetresToUE;
	const double LocationY = -(Origin.Y + NYCGeo::TileSizeMetres) * NYCGeo::MetresToUE;
	const bool bFlat = !(Meta.ZScaleMetres > 0.0);
	const double ZScale = bFlat ? 1.0 : Meta.ZScaleMetres * 12800.0;
	const double LocationZ = bFlat
		? Meta.ZMinMetres * NYCGeo::MetresToUE
		: (Meta.ZMinMetres + 32768.0 * Meta.ZScaleMetres) * NYCGeo::MetresToUE;
	return FTransform(FRotator::ZeroRotator, FVector(LocationX, LocationY, LocationZ), FVector(QuadSizeCm, QuadSizeCm, ZScale));
}

TArray<FString> UNYCTerrainImporter::FindTilesWithTerrain(const FString& ProcessedTilesDir)
{
	TArray<FString> Out;
	IFileManager& FM = IFileManager::Get();
	TArray<FString> Dirs;
	FM.FindFiles(Dirs, *(ProcessedTilesDir / TEXT("*")), false, true);
	for (const FString& Dir : Dirs)
	{
		FIntPoint Tile;
		if (!NYCGeo::ParseTileName(Dir, Tile))
		{
			continue;
		}
		const FString Png = ProcessedTilesDir / Dir / TEXT("terrain.png");
		const FString Json = ProcessedTilesDir / Dir / TEXT("terrain.json");
		if (FM.FileExists(*Png) && FM.FileExists(*Json))
		{
			Out.Add(Dir);
		}
	}
	Out.Sort();
	return Out;
}

FNYCTerrainImportResult UNYCTerrainImporter::ImportTileLandscape(UWorld* World, const FString& TileName, const FString& ProcessedTilesDir,
	UMaterialInterface* LandscapeMaterial, ULevel* OverrideLevel)
{
	FNYCTerrainImportResult Result;
	if (!NYCGeo::ParseTileName(TileName, Result.Tile))
	{
		Result.Error = FString::Printf(TEXT("'%s' is not a tile name (t_{tx}_{ty})"), *TileName);
		return Result;
	}
	if (!World)
	{
		Result.Error = TEXT("no world");
		return Result;
	}

	const FString TileDir = ProcessedTilesDir / TileName;
	FNYCTerrainMeta Meta;
	if (!LoadTerrainMeta(TileDir / TEXT("terrain.json"), Meta, Result.Error))
	{
		return Result;
	}
	TArray<uint16> Source;
	if (!LoadHeightmap(TileDir / TEXT("terrain.png"), Meta.Samples, Source, Result.Error))
	{
		return Result;
	}

	uint16 MinValue = MAX_uint16;
	uint16 MaxValue = 0;
	for (const uint16 V : Source)
	{
		MinValue = FMath::Min(MinValue, V);
		MaxValue = FMath::Max(MaxValue, V);
	}
	Result.MinElevationMetres = Meta.ZMinMetres + static_cast<double>(MinValue) * Meta.ZScaleMetres;
	Result.MaxElevationMetres = Meta.ZMinMetres + static_cast<double>(MaxValue) * Meta.ZScaleMetres;

	TArray<uint16> Heights;
	ResampleToLandscapeGrid(Source, Meta.Samples, Heights);
	if (!(Meta.ZScaleMetres > 0.0))
	{
		// Flat tile: the affine mapping degenerates, so every sample sits at z_min (landscape mid-height).
		for (uint16& H : Heights)
		{
			H = 32768;
		}
	}

#if WITH_EDITOR
	const FTransform Transform = LandscapeTransform(Result.Tile, Meta);

	FActorSpawnParameters Spawn;
	Spawn.OverrideLevel = OverrideLevel ? OverrideLevel : World->GetCurrentLevel();
	Spawn.ObjectFlags = RF_Transactional;
	ALandscape* Landscape = World->SpawnActor<ALandscape>(ALandscape::StaticClass(), Transform, Spawn);
	if (!Landscape)
	{
		Result.Error = TEXT("SpawnActor<ALandscape> failed");
		return Result;
	}
	Landscape->bCanHaveLayersContent = false;
	Landscape->LandscapeMaterial = LandscapeMaterial;
	Landscape->SetActorTransform(Transform);
	Landscape->SetActorLabel(FString::Printf(TEXT("Landscape_%s"), *NYCGeo::TileAssetName(Result.Tile)));

	TMap<FGuid, TArray<uint16>> HeightDataPerLayer;
	HeightDataPerLayer.Add(FGuid(), MoveTemp(Heights));
	TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayerDataPerLayer;
	MaterialLayerDataPerLayer.Add(FGuid(), TArray<FLandscapeImportLayerInfo>());

	Landscape->Import(FGuid::NewGuid(), 0, 0, LandscapeSamples - 1, LandscapeSamples - 1,
		NumSubsections, SubsectionSizeQuads, HeightDataPerLayer, nullptr,
		MaterialLayerDataPerLayer, ELandscapeImportAlphamapType::Additive);

	// Static lighting is off in this project (r.AllowStaticLighting=False) but the field must still be sane.
	Landscape->StaticLightingLOD = static_cast<int32>(FMath::DivideAndRoundUp(FMath::CeilLogTwo(static_cast<uint32>(LandscapeSamples * LandscapeSamples)), 2u)) - 1;

	if (ULandscapeInfo* Info = Landscape->GetLandscapeInfo())
	{
		Info->UpdateLayerInfoMap(Landscape);
	}
	Landscape->RegisterAllComponents();

	Result.bSuccess = true;
	Result.LandscapeName = Landscape->GetName();
	Result.ComponentCount = ComponentsPerSide * ComponentsPerSide;
	UE_LOG(LogNYCSim, Log, TEXT("Terrain %s: landscape %s, z [%.2f, %.2f] m, %d components, scale (%.4f, %.4f, %.4f)"),
		*TileName, *Result.LandscapeName, Result.MinElevationMetres, Result.MaxElevationMetres, Result.ComponentCount,
		Transform.GetScale3D().X, Transform.GetScale3D().Y, Transform.GetScale3D().Z);
	return Result;
#else
	Result.Error = TEXT("landscape import needs an editor build (ALandscape::Import is WITH_EDITOR only)");
	return Result;
#endif
}

TArray<FNYCTerrainImportResult> UNYCTerrainImporter::ImportTiles(UWorld* World, const TArray<FString>& Tiles,
	const FString& ProcessedTilesDir, UMaterialInterface* LandscapeMaterial)
{
	TArray<FNYCTerrainImportResult> Out;
	Out.Reserve(Tiles.Num());
	int32 Failures = 0;
	for (const FString& Tile : Tiles)
	{
		FNYCTerrainImportResult R = ImportTileLandscape(World, Tile, ProcessedTilesDir, LandscapeMaterial, nullptr);
		if (!R.bSuccess)
		{
			++Failures;
			UE_LOG(LogNYCSim, Error, TEXT("Terrain %s: %s"), *Tile, *R.Error);
		}
		Out.Add(MoveTemp(R));
	}
	UE_LOG(LogNYCSim, Log, TEXT("Terrain import: %d tiles, %d failed"), Tiles.Num(), Failures);
	return Out;
}
