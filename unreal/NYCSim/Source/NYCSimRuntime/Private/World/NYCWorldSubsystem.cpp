#include "World/NYCWorldSubsystem.h"
#include "World/NYCSimWorldSettings.h"
#include "CoreAdapter/NYCGeo.h"
#include "NYCSimRuntime.h"

#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

bool UNYCWorldSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (!Super::ShouldCreateSubsystem(Outer))
	{
		return false;
	}
	const UWorld* World = Cast<UWorld>(Outer);
	if (!World)
	{
		return false;
	}
	switch (World->WorldType)
	{
	case EWorldType::Game:
	case EWorldType::PIE:
	case EWorldType::Editor:
		return true;
	default:
		return false;
	}
}

void UNYCWorldSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Reload();
	if (!IsRunningCommandlet())
	{
		WorldInfoCmd = new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
			TEXT("nycsim.WorldInfo"),
			TEXT("Prints CRS, tile count, tile extent and the camera's NYC_TM / WGS84 position."),
			FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateUObject(this, &UNYCWorldSubsystem::PrintWorldInfo));
	}
}

void UNYCWorldSubsystem::Deinitialize()
{
	delete WorldInfoCmd;
	WorldInfoCmd = nullptr;
	Super::Deinitialize();
}

bool UNYCWorldSubsystem::Reload()
{
	bReady = false;
	LoadError.Empty();
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString CrsPath = UNYCSimWorldSettings::ResolveProjectPath(Settings.CrsJsonPath);
	const FString TilesPath = UNYCSimWorldSettings::ResolveProjectPath(Settings.TilesNycbPath);

	FString Err;
	if (!LoadCrs(CrsPath, Err))
	{
		LoadError = Err;
		UE_LOG(LogNYCSim, Error, TEXT("crs.json: %s"), *Err);
		return false;
	}
	if (!TilesFile.Load(TilesPath, Err) || !Tiles.Parse(TilesFile, Err))
	{
		LoadError = Err;
		UE_LOG(LogNYCSim, Error, TEXT("tiles.nycb: %s"), *Err);
		return false;
	}
	bReady = true;
	const FIntRect E = Tiles.TileExtent();
	UE_LOG(LogNYCSim, Log, TEXT("World data ready: CRS %s, %d tiles, tx [%d..%d] ty [%d..%d], z [%.1f, %.1f] m"),
		*CrsName, Tiles.Num(), E.Min.X, E.Max.X, E.Min.Y, E.Max.Y, Tiles.GlobalZMin(), Tiles.GlobalZMax());
	return true;
}

bool UNYCWorldSubsystem::LoadCrs(const FString& Path, FString& OutError)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *Path);
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = FString::Printf(TEXT("%s is not valid JSON"), *Path);
		return false;
	}
	int32 SchemaVersion = 0;
	if (!Root->TryGetNumberField(TEXT("schema_version"), SchemaVersion) || SchemaVersion != 1)
	{
		OutError = FString::Printf(TEXT("%s: schema_version %d unsupported (expected 1)"), *Path, SchemaVersion);
		return false;
	}
	if (!Root->TryGetStringField(TEXT("name"), CrsName) || CrsName != TEXT("NYC_TM"))
	{
		OutError = FString::Printf(TEXT("%s: CRS name '%s' is not NYC_TM"), *Path, *CrsName);
		return false;
	}
	if (!Root->TryGetStringField(TEXT("proj4"), CrsProj4String))
	{
		OutError = FString::Printf(TEXT("%s: missing proj4"), *Path);
		return false;
	}
	// The core carries the same definition; both must agree token for token (ADR-002: never hard-code elsewhere).
	auto Normalise = [](const FString& S)
	{
		TArray<FString> Tokens;
		S.ParseIntoArrayWS(Tokens);
		Tokens.Sort();
		return FString::Join(Tokens, TEXT(" "));
	};
	if (Normalise(CrsProj4String) != Normalise(NYCGeo::CoreProj4()))
	{
		OutError = FString::Printf(TEXT("%s: proj4 '%s' differs from the core's '%s'"), *Path, *CrsProj4String, *NYCGeo::CoreProj4());
		return false;
	}
	if (!Root->TryGetNumberField(TEXT("tile_size_m"), CrsTileSize) || !FMath::IsNearlyEqual(CrsTileSize, NYCGeo::TileSizeMetres, 1e-6))
	{
		OutError = FString::Printf(TEXT("%s: tile_size_m %.3f != %.0f"), *Path, CrsTileSize, NYCGeo::TileSizeMetres);
		return false;
	}
	return true;
}

FVector UNYCWorldSubsystem::NycTmToUE(const FVector& P) const { return NYCGeo::NycTmToUE(P); }
FVector UNYCWorldSubsystem::UEToNycTm(const FVector& UE) const { return NYCGeo::UEToNycTm(UE); }
bool UNYCWorldSubsystem::LonLatToUE(double Lon, double Lat, double Alt, FVector& OutUE) const { return NYCGeo::LonLatToUE(Lon, Lat, Alt, OutUE); }
bool UNYCWorldSubsystem::UEToLonLat(const FVector& UE, double& OutLon, double& OutLat, double& OutAlt) const { return NYCGeo::UEToLonLat(UE, OutLon, OutLat, OutAlt); }
double UNYCWorldSubsystem::HeadingToUEYaw(double HeadingDeg) const { return NYCGeo::HeadingToUEYaw(HeadingDeg); }
FIntPoint UNYCWorldSubsystem::TileOfUE(const FVector& UE) const { return NYCGeo::TileOfUE(UE); }
FString UNYCWorldSubsystem::TileName(const FIntPoint& Tile) const { return NYCGeo::TileName(Tile); }

bool UNYCWorldSubsystem::GetTileInfo(const FIntPoint& Tile, FNYCTileInfo& Out) const
{
	const FNYCTileRecord* R = Tiles.Find(Tile);
	if (!R)
	{
		return false;
	}
	Out.Tile = Tile;
	Out.ZMinMetres = R->ZMin;
	Out.ZMaxMetres = R->ZMax;
	Out.NumBuildings = static_cast<int32>(FMath::Min<uint32>(R->NumBuildings, MAX_int32));
	Out.NumProps = static_cast<int32>(FMath::Min<uint32>(R->NumProps, MAX_int32));
	Out.bHasTerrain = R->HasTerrain();
	Out.bHasWater = R->HasWater();
	Out.bHasLand = R->HasLand();
	Out.BoroughMask = R->BoroughMask;
	return true;
}

TArray<FIntPoint> UNYCWorldSubsystem::AllTiles() const
{
	TArray<FIntPoint> Out;
	Out.Reserve(Tiles.Num());
	for (const FNYCTileRecord& R : Tiles.Records())
	{
		Out.Add(R.Tile());
	}
	return Out;
}

FBox UNYCWorldSubsystem::TileBoundsUE(const FIntPoint& Tile) const
{
	const FNYCTileRecord* R = Tiles.Find(Tile);
	const double ZMin = R ? R->ZMin : Tiles.GlobalZMin();
	// Building tops: shells can rise 540 m above ground (One WTC); the box is generous so streaming distance tests
	// against the tile's 3-D extent rather than its ground plane.
	const double ZMax = (R ? R->ZMax : Tiles.GlobalZMax()) + 550.0;
	return NYCGeo::TileBoundsUE(Tile, ZMin, ZMax);
}

void UNYCWorldSubsystem::GetGlobalZRange(float& OutMin, float& OutMax) const
{
	OutMin = Tiles.GlobalZMin();
	OutMax = Tiles.GlobalZMax();
}

void UNYCWorldSubsystem::PrintWorldInfo(const TArray<FString>& Args, UWorld* InWorld, FOutputDevice& Ar)
{
	Ar.Logf(TEXT("NYCSim world: ready=%d crs=%s tiles=%d error='%s'"), bReady ? 1 : 0, *CrsName, Tiles.Num(), *LoadError);
	const FIntRect E = Tiles.TileExtent();
	Ar.Logf(TEXT("  tile extent tx [%d..%d] ty [%d..%d]  z [%.1f, %.1f] m"), E.Min.X, E.Max.X, E.Min.Y, E.Max.Y, Tiles.GlobalZMin(), Tiles.GlobalZMax());
	if (InWorld)
	{
		FVector CamPos = FVector::ZeroVector;
		if (const APlayerController* PC = InWorld->GetFirstPlayerController())
		{
			FRotator CamRot;
			PC->GetPlayerViewPoint(CamPos, CamRot);
		}
		const FVector Tm = NYCGeo::UEToNycTm(CamPos);
		double Lon = 0.0, Lat = 0.0;
		const bool bGeo = NYCGeo::NycTmToLonLat(Tm.X, Tm.Y, Lon, Lat);
		const FIntPoint Tile = NYCGeo::TileOfNycTm(Tm.X, Tm.Y);
		Ar.Logf(TEXT("  camera UE (%.0f, %.0f, %.0f) cm = NYC_TM (%.2f, %.2f, %.2f) m = %s  tile %s%s"),
			CamPos.X, CamPos.Y, CamPos.Z, Tm.X, Tm.Y, Tm.Z,
			bGeo ? *FString::Printf(TEXT("lat %.6f lon %.6f"), Lat, Lon) : TEXT("(outside projection domain)"),
			*NYCGeo::TileName(Tile), Tiles.Find(Tile) ? TEXT("") : TEXT(" [no tile record]"));
	}
}
