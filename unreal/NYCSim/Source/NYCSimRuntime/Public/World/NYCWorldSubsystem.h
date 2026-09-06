// World subsystem: loads crs.json + runtime/tiles.nycb, validates the CRS against the core, and offers coordinate
// conversion (NYC_TM <-> UE <-> WGS84) and tile lookups to every other subsystem, actor and Python script.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "CoreAdapter/NYCNycb.h"
#include "NYCWorldSubsystem.generated.h"

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCTileInfo
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	FIntPoint Tile = FIntPoint::ZeroValue;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	float ZMinMetres = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	float ZMaxMetres = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	int32 NumBuildings = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	int32 NumProps = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	bool bHasTerrain = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	bool bHasWater = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	bool bHasLand = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim")
	uint8 BoroughMask = 0;
};

UCLASS()
class NYCSIMRUNTIME_API UNYCWorldSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	// UWorldSubsystem
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** True once crs.json validated and tiles.nycb parsed. Conversions work regardless (they are pure core math). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	bool IsWorldDataReady() const { return bReady; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	FString GetLoadError() const { return LoadError; }

	// ---- coordinates (thin wrappers over NYCGeo, exposed for Python/Blueprint-less callers) -----------------------
	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	FVector NycTmToUE(const FVector& EastNorthUpMetres) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	FVector UEToNycTm(const FVector& UECentimetres) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	bool LonLatToUE(double LonDeg, double LatDeg, double AltMetres, FVector& OutUE) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	bool UEToLonLat(const FVector& UE, double& OutLonDeg, double& OutLatDeg, double& OutAltMetres) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	double HeadingToUEYaw(double HeadingDeg) const;

	// ---- tiles --------------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	FIntPoint TileOfUE(const FVector& UE) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	FString TileName(const FIntPoint& Tile) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	bool GetTileInfo(const FIntPoint& Tile, FNYCTileInfo& OutInfo) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	int32 NumTiles() const { return Tiles.Num(); }

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	TArray<FIntPoint> AllTiles() const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	FBox TileBoundsUE(const FIntPoint& Tile) const;

	/** Terrain z range across every tile (metres NAVD88); used for camera clip planes and water level sanity checks. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	void GetGlobalZRange(float& OutMinMetres, float& OutMaxMetres) const;

	const FNYCTilesTable& TilesTable() const { return Tiles; }
	const FNYCTileRecord* FindTileRecord(const FIntPoint& Tile) const { return Tiles.Find(Tile); }

	/** Proj4 string read from crs.json ("" until loaded). */
	const FString& CrsProj4() const { return CrsProj4String; }

	/** Re-reads crs.json and tiles.nycb (used by the import commandlet after copying new runtime data). */
	bool Reload();

private:
	bool LoadCrs(const FString& Path, FString& OutError);
	void PrintWorldInfo(const TArray<FString>& Args, UWorld* InWorld, FOutputDevice& Ar);

	FNYCNycbFile TilesFile;
	FNYCTilesTable Tiles;
	FString CrsProj4String;
	FString CrsName;
	double CrsTileSize = 0.0;
	bool bReady = false;
	FString LoadError;
	FAutoConsoleCommandWithWorldArgsAndOutputDevice* WorldInfoCmd = nullptr;
};
