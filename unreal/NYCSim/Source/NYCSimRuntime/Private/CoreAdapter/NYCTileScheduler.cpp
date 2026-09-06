#include "CoreAdapter/NYCTileScheduler.h"

#include <vector>

#include "nycsim/tiling/Tile.h"
#include "nycsim/tiling/TileScheduler.h"
#include "nycsim/util/Span.h"

namespace
{
	using nycsim::tiling::Tier;

	ENYCTier ToUE(Tier T) { return static_cast<ENYCTier>(static_cast<uint8>(T)); }

	nycsim::tiling::SchedulerConfig ToCore(const FNYCSchedulerConfig& C)
	{
		nycsim::tiling::SchedulerConfig Out;
		Out.l0 = {C.L0LoadMetres, C.L0UnloadMetres};
		Out.l1 = {C.L1LoadMetres, C.L1UnloadMetres};
		Out.l2 = {C.L2LoadMetres, C.L2UnloadMetres};
		Out.l3 = {C.L3LoadMetres, C.L3UnloadMetres};
		Out.protectRadius_m = C.ProtectRadiusMetres;
		Out.lookahead_s = C.LookaheadSeconds;
		Out.forwardConeHalfAngle_deg = C.ForwardConeHalfAngleDeg;
		Out.forwardConeWeight = C.ForwardConeWeight;
		Out.budgetBytes = C.BudgetBytes;
		Out.upgradeHeadroom = C.UpgradeHeadroom;
		return Out;
	}

	nycsim::tiling::TileInfo ToCore(const FNYCTileRecord& R)
	{
		nycsim::tiling::TileInfo T;
		T.tx = R.Tx;
		T.ty = R.Ty;
		T.zMin = R.ZMin;
		T.zMax = R.ZMax;
		T.nBuildings = R.NumBuildings;
		T.nProps = R.NumProps;
		T.flags = R.Flags;
		T.boroughMask = R.BoroughMask;
		return T;
	}
}

const TCHAR* NYCTierName(ENYCTier Tier)
{
	switch (Tier)
	{
	case ENYCTier::Unloaded: return TEXT("Unloaded");
	case ENYCTier::L3: return TEXT("L3");
	case ENYCTier::L2: return TEXT("L2");
	case ENYCTier::L1: return TEXT("L1");
	case ENYCTier::L0: return TEXT("L0");
	default: return TEXT("?");
	}
}

FNYCTileSchedulerAdapter::FNYCTileSchedulerAdapter(const FNYCTilesTable& Tiles, const FNYCSchedulerConfig& Config)
{
	std::vector<nycsim::tiling::TileInfo> Infos;
	Infos.reserve(static_cast<size_t>(Tiles.Num()));
	for (const FNYCTileRecord& R : Tiles.Records())
	{
		Infos.push_back(ToCore(R));
	}
	const nycsim::tiling::SchedulerConfig CoreConfig = ToCore(Config);
	bConfigValid = CoreConfig.valid();
	Impl = MakeUnique<nycsim::tiling::TileScheduler>(
		nycsim::Span<const nycsim::tiling::TileInfo>(Infos.data(), Infos.size()), CoreConfig, nycsim::tiling::TileCostModel());
}

FNYCTileSchedulerAdapter::~FNYCTileSchedulerAdapter() = default;

void FNYCTileSchedulerAdapter::Update(const FNYCCameraState& Camera, TArray<FNYCTileTransition>& Out)
{
	nycsim::tiling::CameraState C;
	C.x_m = Camera.PositionMetres.X;
	C.y_m = Camera.PositionMetres.Y;
	C.vx_mps = Camera.VelocityMps.X;
	C.vy_mps = Camera.VelocityMps.Y;
	C.heading_deg = Camera.HeadingDeg;
	C.time_s = Camera.TimeSeconds;
	const std::vector<nycsim::tiling::Transition>& Tr = Impl->update(C);
	Out.Reserve(Out.Num() + static_cast<int32>(Tr.size()));
	for (const nycsim::tiling::Transition& T : Tr)
	{
		FNYCTileTransition U;
		U.Tile = FIntPoint(T.tx, T.ty);
		U.From = ToUE(T.from);
		U.To = ToUE(T.to);
		U.TimeSeconds = T.time_s;
		U.DistanceNowMetres = T.distanceNow_m;
		U.bBudgetLimited = T.budgetLimited;
		Out.Add(U);
	}
}

ENYCTier FNYCTileSchedulerAdapter::TierOf(const FIntPoint& Tile) const
{
	return ToUE(Impl->tierOf(Tile.X, Tile.Y));
}

bool FNYCTileSchedulerAdapter::Contains(const FIntPoint& Tile) const
{
	return Impl->contains(Tile.X, Tile.Y);
}

int32 FNYCTileSchedulerAdapter::TileCount() const
{
	return static_cast<int32>(Impl->tileCount());
}

FNYCSchedulerStats FNYCTileSchedulerAdapter::Stats() const
{
	const nycsim::tiling::SchedulerStats& S = Impl->stats();
	FNYCSchedulerStats Out;
	Out.ResidentBytes = S.residentBytes;
	for (int32 i = 0; i < 5; ++i)
	{
		Out.CountByTier[i] = S.countByTier[i];
	}
	Out.bOverBudget = S.overBudget;
	Out.TotalLoads = S.totalLoads;
	Out.TotalUnloads = S.totalUnloads;
	Out.TotalUpgrades = S.totalUpgrades;
	Out.TotalDowngrades = S.totalDowngrades;
	Out.TotalBudgetDenials = S.totalBudgetDenials;
	Out.Updates = S.updates;
	return Out;
}

uint64 FNYCTileSchedulerAdapter::EstimateBytes(const FIntPoint& Tile, ENYCTier Tier) const
{
	for (const nycsim::tiling::TileScheduler::Entry& E : Impl->entries())
	{
		if (E.info.tx == Tile.X && E.info.ty == Tile.Y)
		{
			return Impl->costModel().bytes(E.info, static_cast<nycsim::tiling::Tier>(static_cast<uint8>(Tier)));
		}
	}
	return 0;
}

void FNYCTileSchedulerAdapter::Reset()
{
	Impl->reset();
}
