// Tile streaming: drives nycsim::tiling::TileScheduler (through FNYCTileSchedulerAdapter) from the player camera and
// turns the tier transitions it returns into UE level-streaming requests.
//
// Threading model (ARCHITECTURE §3, §13 "no allocation in per-frame hot paths"):
//   * game thread   — samples the camera, filters velocity, launches one worker task per scheduler step, applies a
//                     bounded number of level requests per frame, polls level status, draws the debug HUD.
//   * worker thread — runs the whole scheduler step (distance, hysteresis, budget, ordering). The adapter is touched
//                     by exactly one thread at a time: the game thread only reads results after Task.IsCompleted().
//
// Tier -> level mapping (one level loaded per tile at a time; skyline levels are shared):
//   L0  -> {TileLevelRoot}/{t_m3_7}/{t_m3_7}_L0      per-tile: shells + kit + props + roads + terrain
//   L1  -> {TileLevelRoot}/{t_m3_7}/{t_m3_7}_L1      per-tile: shells with facade shader, impostor trees
//   L2  -> {SkylineLevelRoot}/S4_{sx}_{sy}           merged 4 km HLOD, shared by up to 16 tiles
//   L3  -> {SkylineLevelRoot}/S16_{sx}_{sy}          merged 16 km HLOD, shared by up to 256 tiles
// A skyline level is loaded only while *no* tile inside it is at a finer tier, which is what keeps the merged HLOD
// mesh from double-drawing the tiles that are already resident at L0/L1 (and, for S16, at L2).
#pragma once

#include "CoreMinimal.h"
#include "CoreAdapter/NYCTileScheduler.h"
#include "Subsystems/WorldSubsystem.h"
#include "Tasks/Task.h"
#include "UObject/ObjectPtr.h"

#include "NYCTileStreamingSubsystem.generated.h"

class APlayerController;
class UCanvas;
class ULevelStreamingDynamic;
class UNYCWorldSubsystem;

/** Snapshot of the streaming state, cheap to copy; the debug HUD, the console commands and Python read this. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCStreamingStats
{
	GENERATED_BODY()

	/** Tiles per tier, five entries indexed by ENYCTier (0 = Unloaded .. 4 = L0). A TArray, not a C array:
	 *  UHT refuses to expose static arrays to Blueprint. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	TArray<int32> TilesPerTier = {0, 0, 0, 0, 0};

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int32 LevelsLoaded = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int32 LevelsVisible = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int32 LevelsPending = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int32 QueuedRequests = 0;

	/** Scheduler cost-model estimate of the resident bytes (core TileCostModel over the resident tiers). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	double EstimatedResidentMB = 0.0;

	/** Cost-model estimate of only the levels this subsystem actually has loaded (excludes tiers denied by the queue). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	double AppliedResidentMB = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	double BudgetMB = 0.0;

	/** Physical memory used by the process (FPlatformMemory), the number the budget is validated against. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	double ProcessPhysicalMB = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	float LastSchedulerStepMs = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	float LastApplyMs = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int64 TotalLoads = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int64 TotalUnloads = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int64 TotalBudgetDenials = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int64 SchedulerUpdates = 0;

	/** Tiles whose level package is missing on disk (content not imported yet); each is logged once. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	int32 MissingLevels = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	bool bOverBudget = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	FVector CameraNycTm = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	FVector2D CameraVelocityMps = FVector2D::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	float CameraHeadingDeg = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Streaming")
	FIntPoint CameraTile = FIntPoint::ZeroValue;
};

/** Fired on the game thread after a tile's tier changed and the corresponding level request was issued. */
DECLARE_MULTICAST_DELEGATE_ThreeParams(FNYCOnTileTierChanged, FIntPoint /*Tile*/, ENYCTier /*From*/, ENYCTier /*To*/);

UCLASS()
class NYCSIMRUNTIME_API UNYCTileStreamingSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	// USubsystem / FTickableGameObject
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickable() const override;
	virtual TStatId GetStatId() const override;

	/** Tier the scheduler currently assigns to a tile (Unloaded when the tile is not in tiles.nycb). */
	ENYCTier GetTileTier(const FIntPoint& Tile) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Streaming")
	int32 GetTileTierIndex(const FIntPoint& Tile) const { return static_cast<int32>(GetTileTier(Tile)); }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Streaming")
	FNYCStreamingStats GetStats() const { return Stats; }

	/** True when the streaming level that carries this tile's tier is loaded *and* visible. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Streaming")
	bool IsTileResident(const FIntPoint& Tile) const;

	/** Tiles currently at L0 or L1, i.e. the tiles whose per-tile level is (or is becoming) resident. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Streaming")
	TArray<FIntPoint> GetResidentTiles() const;

	/** Overrides the camera used by the scheduler (headless drive-throughs, cinematics, the import commandlet). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Streaming")
	void SetCameraOverride(const FVector& UELocation, float HeadingDeg, const FVector2D& VelocityMps);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Streaming")
	void ClearCameraOverride();

	/** Blocks until every issued request has finished (used by the commandlet and by teleports). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Streaming")
	void FlushStreaming();

	/** Forgets every tier and re-issues the whole set from the current camera (after a content reimport). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Streaming")
	void ResetStreaming();

	FNYCOnTileTierChanged& OnTileTierChanged() { return TileTierChanged; }

	/** True once tiles.nycb has been parsed and the scheduler exists. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Streaming")
	bool IsReady() const { return Scheduler.IsValid(); }

	// ---- console output (called by the nycsim.Streaming.* commands registered in the .cpp) ---------------------
	void PrintStats(FOutputDevice& Ar) const;
	void PrintTile(const FIntPoint& Tile, FOutputDevice& Ar) const;
	/** Dumps every managed level and its load/visible/pending state. */
	void PrintLevels(FOutputDevice& Ar) const;

private:
	/** One streaming level this subsystem owns (per-tile L0/L1 or a shared skyline cell). The strong reference lives
	 *  in ManagedStreamingLevels (a UPROPERTY) so the GC keeps the object even if the world drops it. */
	struct FManagedLevel
	{
		TWeakObjectPtr<ULevelStreamingDynamic> Streaming;
		FName PackageName = NAME_None;
		bool bWanted = false;      ///< the desired state, set by ApplyDesiredState
		bool bRequested = false;   ///< SetShouldBeLoaded(bWanted) has been called for this state
		bool bMissing = false;     ///< the package does not exist on disk; never requested again
		uint64 EstimatedBytes = 0; ///< cost-model bytes attributed to this level while it is loaded
	};

	struct FPendingRequest
	{
		FName PackageName = NAME_None;
		bool bLoad = false;
		double PriorityMetres = 0.0;
	};

	// ---- pipeline ---------------------------------------------------------------------------------------------
	bool BuildScheduler();
	bool SampleCamera(float DeltaTime, FNYCCameraState& OutCamera);
	void LaunchSchedulerStep(const FNYCCameraState& Camera);
	void CollectSchedulerResults();
	void RecomputeDesiredLevels();
	void ApplyPendingRequests();
	void UpdateStats();

	// ---- level helpers ----------------------------------------------------------------------------------------
	FString TileLevelPackage(const FIntPoint& Tile, ENYCTier Tier) const;
	FString SkylineLevelPackage(const FIntPoint& ParentCell, int32 KilometresPerCell) const;
	FManagedLevel* FindOrAddLevel(const FString& PackageName, uint64 EstimatedBytes);
	void SetLevelWanted(const FString& PackageName, bool bWanted, uint64 EstimatedBytes, double PriorityMetres);
	void ReleaseAllLevels();

	// ---- debug --------------------------------------------------------------------------------------------------
	void DrawDebugHUD(UCanvas* Canvas, APlayerController* PC);

	// ---- state ------------------------------------------------------------------------------------------------
	TUniquePtr<FNYCTileSchedulerAdapter> Scheduler;
	FNYCSchedulerConfig SchedulerConfig;

	/** Desired per-tile level (tier L0/L1 only) and the skyline cells derived from the tier map. */
	TMap<FIntPoint, ENYCTier> TierByTile;
	TMap<FName, FManagedLevel> Levels;
	TArray<FPendingRequest> PendingRequests;

	/** Strong references to every ULevelStreamingDynamic created here (GC anchor). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<ULevelStreamingDynamic>> ManagedStreamingLevels;

	/** Set once per scheduler result; RecomputeDesiredLevels() rebuilds the wanted set from TierByTile. */
	bool bTierMapDirty = false;

	// worker task
	UE::Tasks::FTask SchedulerTask;
	TArray<FNYCTileTransition> WorkerTransitions;
	FNYCSchedulerStats WorkerStats;
	double WorkerStepSeconds = 0.0;
	bool bTaskInFlight = false;

	// camera filtering
	bool bHasPreviousCamera = false;
	FVector PreviousCameraUE = FVector::ZeroVector;
	FVector2D FilteredVelocityMps = FVector2D::ZeroVector;
	float FilteredHeadingDeg = 0.f;
	bool bCameraOverride = false;
	FVector OverrideLocationUE = FVector::ZeroVector;
	float OverrideHeadingDeg = 0.f;
	FVector2D OverrideVelocityMps = FVector2D::ZeroVector;
	double TimeSinceLastStep = 0.0;
	double SimTimeSeconds = 0.0;

	uint64 AppliedResidentBytes = 0;
	uint64 EffectiveBudgetBytes = 0;
	int32 MissingLevelCount = 0;
	FNYCStreamingStats Stats;

	FNYCOnTileTierChanged TileTierChanged;

	FDelegateHandle DebugDrawHandle;
};
