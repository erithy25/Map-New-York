// Adapter over nycsim::tiling::TileScheduler (core/include/nycsim/tiling/TileScheduler.h).
// Exposes UE-typed structs; the core types never leave this adapter. Not thread-safe: the owner guarantees that
// Update() runs on one thread at a time (UNYCTileStreamingSubsystem runs it on a worker task and reads results on
// the game thread only after the task completes).
#pragma once

#include "CoreMinimal.h"
#include "CoreAdapter/NYCNycb.h"

namespace nycsim { namespace tiling { class TileScheduler; } }

/** Mirrors nycsim::tiling::Tier: finer tiers have larger values. */
enum class ENYCTier : uint8
{
	Unloaded = 0,
	L3 = 1,
	L2 = 2,
	L1 = 3,
	L0 = 4
};

NYCSIMRUNTIME_API const TCHAR* NYCTierName(ENYCTier Tier);

struct FNYCCameraState
{
	FVector2D PositionMetres = FVector2D::ZeroVector; // NYC_TM east/north
	FVector2D VelocityMps = FVector2D::ZeroVector;    // NYC_TM east/north
	double HeadingDeg = 0.0;                          // compass heading of the view direction
	double TimeSeconds = 0.0;
};

struct FNYCTileTransition
{
	FIntPoint Tile = FIntPoint::ZeroValue;
	ENYCTier From = ENYCTier::Unloaded;
	ENYCTier To = ENYCTier::Unloaded;
	double TimeSeconds = 0.0;
	double DistanceNowMetres = 0.0;
	bool bBudgetLimited = false;
};

struct FNYCSchedulerStats
{
	uint64 ResidentBytes = 0;
	uint32 CountByTier[5] = {0, 0, 0, 0, 0};
	bool bOverBudget = false;
	uint64 TotalLoads = 0;
	uint64 TotalUnloads = 0;
	uint64 TotalUpgrades = 0;
	uint64 TotalDowngrades = 0;
	uint64 TotalBudgetDenials = 0;
	uint64 Updates = 0;
};

struct FNYCSchedulerConfig
{
	double L0LoadMetres = 900.0;
	double L0UnloadMetres = 1300.0;
	double L1LoadMetres = 2500.0;
	double L1UnloadMetres = 3000.0;
	double L2LoadMetres = 12000.0;
	double L2UnloadMetres = 13000.0;
	double L3LoadMetres = 40000.0;
	double L3UnloadMetres = 43000.0;
	double ProtectRadiusMetres = 300.0;
	double LookaheadSeconds = 1.5;
	double ForwardConeHalfAngleDeg = 45.0;
	double ForwardConeWeight = 0.7;
	uint64 BudgetBytes = 8ull << 30;
	double UpgradeHeadroom = 0.05;
};

class NYCSIMRUNTIME_API FNYCTileSchedulerAdapter
{
public:
	/** Builds the core scheduler over every record of tiles.nycb. An invalid config falls back to the core defaults
	 *  (reported by IsConfigValid()). */
	FNYCTileSchedulerAdapter(const FNYCTilesTable& Tiles, const FNYCSchedulerConfig& Config);
	~FNYCTileSchedulerAdapter();

	FNYCTileSchedulerAdapter(const FNYCTileSchedulerAdapter&) = delete;
	FNYCTileSchedulerAdapter& operator=(const FNYCTileSchedulerAdapter&) = delete;

	/** Recomputes tiers; appends the transitions to apply (nearest-first) to OutTransitions. */
	void Update(const FNYCCameraState& Camera, TArray<FNYCTileTransition>& OutTransitions);

	ENYCTier TierOf(const FIntPoint& Tile) const;
	bool Contains(const FIntPoint& Tile) const;
	int32 TileCount() const;
	FNYCSchedulerStats Stats() const;
	bool IsConfigValid() const { return bConfigValid; }
	/** Estimated resident bytes of one tile at a tier (core TileCostModel). */
	uint64 EstimateBytes(const FIntPoint& Tile, ENYCTier Tier) const;
	void Reset();

private:
	TUniquePtr<nycsim::tiling::TileScheduler> Impl;
	bool bConfigValid = true;
};
