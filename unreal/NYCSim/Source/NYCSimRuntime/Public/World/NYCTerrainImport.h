// Landscape import from the pipeline's per-tile heightmaps (DATA_CONTRACTS §3):
//   data/processed/tiles/{tile}/terrain.png   16-bit grayscale, 501 x 501 samples, 2 m spacing, north row first
//   data/processed/tiles/{tile}/terrain.json  {z_min_m, z_scale_m, samples, spacing_m, water_level_m, sources}
// Elevation of sample v: z = z_min_m + v * z_scale_m  (metres, NAVD88).
//
// UE landscape geometry
// ---------------------
// A landscape's quad count per component must be SubsectionSizeQuads * NumSubsections with SubsectionSizeQuads in
// {7, 15, 31, 63, 127, 255} (the heightmap textures are powers of two). 500 quads (= 501 samples) is divisible by
// none of them, so the importer resamples the 501-sample grid to 505 samples = 504 quads = 8 x 8 components of 63
// quads — the UE default component size — and the horizontal scale becomes 100000/504 = 198.412698 cm per quad, so
// the landscape still covers exactly 1000 m. The resampling is bilinear and, because the target edge samples land
// exactly on the source edge samples (j = 0 -> s = 0, j = 504 -> s = 500), the tile borders stay bit-exact and
// neighbouring landscapes are watertight.
//
// Heights are passed through unchanged: the PNG's 16-bit value *is* the landscape height value. The affine mapping
// to metres is carried by the actor transform:
//   DrawScale.Z = z_scale_m * 12800          (UE landscape height unit = DrawScale.Z / 128 cm)
//   ActorZ      = (z_min_m + 32768 * z_scale_m) * 100 cm
// so world Z (cm) = ActorZ + (H - 32768) * z_scale_m * 100 = (z_min_m + H * z_scale_m) * 100. Exact, no requantisation.
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"

#include "NYCTerrainImport.generated.h"

class ALandscape;
class ULevel;
class UMaterialInterface;

/** Contents of tiles/{tile}/terrain.json (DATA_CONTRACTS §3). */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCTerrainMeta
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	FString Tile;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	double ZMinMetres = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	double ZScaleMetres = 0.0025;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	int32 Samples = 501;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	double SpacingMetres = 2.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	double WaterLevelMetres = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	TArray<FString> Sources;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	int32 SchemaVersion = 0;
};

/** Result of importing one tile; also what the commandlet and the Python scripts report. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCTerrainImportResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	FIntPoint Tile = FIntPoint::ZeroValue;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	bool bSuccess = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	FString Error;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	FString LandscapeName;

	/** Elevation range actually present in the heightmap, metres NAVD88. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	double MinElevationMetres = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	double MaxElevationMetres = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Terrain")
	int32 ComponentCount = 0;
};

/**
 * Terrain import. Everything that reads the pipeline's files works in any build (the commandlet, the streaming
 * subsystem's sanity checks and the tests use it); the landscape creation itself is editor-only because
 * ALandscape::Import is.
 */
UCLASS()
class NYCSIMRUNTIME_API UNYCTerrainImporter : public UObject
{
	GENERATED_BODY()

public:
	/** 501 samples at 2 m, inclusive edges (DATA_CONTRACTS §3). */
	static constexpr int32 SourceSamples = 501;
	/** 505 samples = 504 quads = 8 x 8 components of 63 quads (see the file header for why 501 cannot be used). */
	static constexpr int32 LandscapeSamples = 505;
	static constexpr int32 SubsectionSizeQuads = 63;
	static constexpr int32 NumSubsections = 1;
	static constexpr int32 ComponentsPerSide = 8;
	/** Centimetres per landscape quad so that 504 quads cover exactly 1000 m. */
	static constexpr double QuadSizeCm = 100000.0 / 504.0;

	/** Parses tiles/{tile}/terrain.json. Returns false and fills OutError on any schema problem. */
	static bool LoadTerrainMeta(const FString& JsonPath, FNYCTerrainMeta& OutMeta, FString& OutError);

	/** Loads a 16-bit grayscale PNG of ExpectedSamples^2 into OutHeights (row 0 = north). */
	static bool LoadHeightmap(const FString& PngPath, int32 ExpectedSamples, TArray<uint16>& OutHeights, FString& OutError);

	/** Bilinear 501 -> 505 resample; edge samples are preserved exactly. */
	static void ResampleToLandscapeGrid(const TArray<uint16>& Source, int32 SourceSamples_, TArray<uint16>& OutHeights);

	/** Transform of the tile's landscape actor: NW corner of the tile, scale from the terrain.json z mapping. */
	static FTransform LandscapeTransform(const FIntPoint& Tile, const FNYCTerrainMeta& Meta);

	/**
	 * Creates one ALandscape for a tile in World (in OverrideLevel when given, else the world's current level).
	 * Editor builds only; in a runtime build it fails with an explanatory error.
	 */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Terrain", meta = (WorldContext = "World"))
	static FNYCTerrainImportResult ImportTileLandscape(UWorld* World, const FString& TileName, const FString& ProcessedTilesDir,
		UMaterialInterface* LandscapeMaterial, ULevel* OverrideLevel);

	/** Imports every tile named in Tiles (tile names, e.g. "t_-3_7"). Returns one result per tile. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Terrain", meta = (WorldContext = "World"))
	static TArray<FNYCTerrainImportResult> ImportTiles(UWorld* World, const TArray<FString>& Tiles,
		const FString& ProcessedTilesDir, UMaterialInterface* LandscapeMaterial);

	/** Tile names under ProcessedTilesDir that have both terrain.png and terrain.json. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Terrain")
	static TArray<FString> FindTilesWithTerrain(const FString& ProcessedTilesDir);

	/** Reads terrain.json only (Blueprint/Python-friendly wrapper). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Terrain")
	static bool ReadTerrainMeta(const FString& JsonPath, FNYCTerrainMeta& OutMeta, FString& OutError);
};
