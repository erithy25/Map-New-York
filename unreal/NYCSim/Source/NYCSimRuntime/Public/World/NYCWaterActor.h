// Water: a camera-following tiled ocean built from the pipeline's water data.
//
// Inputs (produced by pipeline/nycsim_pipeline/unreal/manifest.py, DATA_CONTRACTS §4 and §14.1):
//   Runtime/unreal_water.json          bodies, per-tile water_fraction / dominant_kind / tidal / mask reference, flow
//   Runtime/water_masks/{tile}.png     8-bit, 501 x 501, 1 texel = 2 m, 255 = water — the same grid as terrain.png
//   live tide (NOAA CO-OPS) pushed in by UNYCWeatherSubsystem::SetTide -> water level and current
//
// Geometry: near ring — one dynamic-mesh patch per water tile within NearRadiusTiles, each with that tile's shoreline
// mask bound to its material instance; far ring — four strips that fill from the near block out to FarExtentKilometres
// so the harbour, the Hudson and the Atlantic still read from the George Washington Bridge and from Brooklyn Heights.
// Everything is rebuilt only when the camera crosses a tile boundary; between crossings the actor is idle.
//
// Material contract (M_NYC_Water, created by Content/Python/import_assets.py):
//   Texture2D WaterMask     the tile's shoreline mask (near patches only)
//   Scalar    HasMask       1 near, 0 far
//   Vector    TileOriginUE  (X, Y) = UE position of the tile's north-west corner in cm, Z = tile size in cm
//   Vector    FlowVector    (X, Y) = unit flow direction in UE space, Z = speed in m/s
//   Scalar    WaterLevelCm  surface height in UE cm
//   Scalar    Tidal         1 when the body is tidal
//   Scalar    KindIndex     0 river, 1 bay, 2 ocean, 3 lake, 4 pond, 5 canal, 6 basin, 7 unknown
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UObject/ObjectPtr.h"

#include "NYCWaterActor.generated.h"

class UDynamicMeshComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UTexture2D;

/** What the world looks like at a point: used by the vehicle, audio and camera code to ask "is this water?". */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCWaterSample
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	bool bIsWater = false;

	/** Mask coverage at the sample, 0..1 (bilinear); < 1 near the shoreline. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	float Coverage = 0.f;

	/** Water surface height in UE cm (tide included). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	double SurfaceZ = 0.0;

	/** Positive when the query point is below the surface, cm. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	double DepthBelowSurface = 0.0;

	/** Surface current in UE space, cm/s (zero for non-tidal bodies). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	FVector FlowVelocity = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	FString Kind;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Water")
	bool bTidal = false;
};

UCLASS()
class NYCSIMRUNTIME_API ANYCWaterActor : public AActor
{
	GENERATED_BODY()

public:
	ANYCWaterActor();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	/** Live tide from NOAA CO-OPS. Level is metres NAVD88, direction is mathematical (0 = east, CCW) toward which the
	 *  water flows — the convention of services/nycsim_live/tides.py and DATA_CONTRACTS §12. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Water")
	void SetTide(double WaterLevelMetres, double CurrentSpeedMps, double CurrentDirDeg, bool bPredicted);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Water")
	double GetWaterLevelMetres() const { return WaterLevelMetres; }

	/** Water state at a world position. Uses the per-tile mask when the tile is loaded, else the body coverage. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Water")
	FNYCWaterSample SampleWaterAtUE(const FVector& UELocation) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Water")
	int32 GetActivePatchCount() const { return ActivePatchCount; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Water")
	int32 GetWaterTileCount() const { return WaterTiles.Num(); }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Water")
	FString GetLoadError() const { return LoadError; }

	/** Re-reads unreal_water.json and drops every cached mask (used after a reimport). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Water")
	bool ReloadWaterData();

	void PrintWaterInfo(FOutputDevice& Ar) const;

private:
	/** One tile of §14.1 `tiles`, plus its lazily loaded mask. */
	struct FWaterTile
	{
		FIntPoint Tile = FIntPoint::ZeroValue;
		float WaterFraction = 0.f;
		FString DominantKind;
		bool bTidal = false;
		float ShorelineMetres = 0.f;
		int32 Structures = 0;
		/** 8-bit coverage, MaskSize x MaskSize, row 0 = north. Empty until the mask is loaded (or if it is missing). */
		TArray<uint8> Mask;
		int32 MaskSize = 0;
		bool bMaskTried = false;
		TWeakObjectPtr<UTexture2D> MaskTexture;
	};

	struct FPatch
	{
		TWeakObjectPtr<UDynamicMeshComponent> Component;
		TWeakObjectPtr<UMaterialInstanceDynamic> Material;
		FIntPoint Tile = FIntPoint::ZeroValue;
		int32 Quads = 0;
		bool bInUse = false;
	};

	bool LoadWaterJson();
	void RebuildNearPatches(const FIntPoint& CameraTile);
	void UpdateFarRing(const FIntPoint& CameraTile);
	void UpdatePatchMaterial(FPatch& Patch, const FWaterTile& Tile);
	void UpdateAllMaterialParameters();
	bool EnsureMask(FWaterTile& Tile);
	UDynamicMeshComponent* AcquirePatch(int32 Quads);
	void SetPatchGeometry(UDynamicMeshComponent* Component, double WidthCm, double HeightCm, int32 QuadsX, int32 QuadsY);
	static int32 KindIndex(const FString& Kind);
	FIntPoint CameraTileNow(bool& bOutValid) const;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> RootScene;

	/** Near-ring patches (pooled) and the four far strips. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UDynamicMeshComponent>> PatchComponents;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UDynamicMeshComponent>> FarComponents;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FarMaterials;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> WaterMaterial;

	/** Transient shoreline-mask textures built from the staged PNGs (GC anchor; freed with the actor). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UTexture2D>> MaskTextures;

	TArray<FPatch> Patches;
	TMap<FIntPoint, FWaterTile> WaterTiles;

	FIntPoint LastCameraTile = FIntPoint(MIN_int32, MIN_int32);
	bool bHasCameraTile = false;
	int32 ActivePatchCount = 0;
	int32 MasksLoaded = 0;
	FString LoadError;

	// tide state
	double WaterLevelMetres = 0.0;
	double CurrentSpeedMps = 0.0;
	double CurrentDirDeg = 0.0;
	bool bTidePredicted = true;
	FString TideStation;
	double LastTideUpdateSeconds = -1.0;
};
