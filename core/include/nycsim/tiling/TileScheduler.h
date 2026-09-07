// TileScheduler — decides the level-of-detail tier of every tile from the camera state
// (ARCHITECTURE §3, ADR-008). Engine-agnostic and deterministic: the same sequence of camera
// states yields the same sequence of transitions, independent of the catalogue's input order.
//
// Rules implemented:
//  * Tiers L0..L3 with load/unload radii and hysteresis (defaults: L0 900/1300 m, L1 2.5/3.0 km,
//    L2 12/13 km, L3 40/43 km). A tile upgrades when it comes within the finer tier's load radius
//    and downgrades only once it is beyond its current tier's unload radius.
//  * Distances are measured to the tile square (0 inside) from both the current camera position
//    and the position predicted `lookahead_s` (1.5 s) ahead along the velocity; the smaller of the
//    two is used, so tiles ahead are pre-loaded and tiles just left are kept.
//  * Nothing within `protectRadius_m` (300 m) of the camera is ever unloaded, downgraded or
//    evicted; such tiles are always L0 and are exempt from the memory budget.
//  * Memory budget: bytes per tile per tier come from TileCostModel applied to the tiles.nycb
//    record. Tiles are granted their target tier nearest-first (forward-cone weighted); when a
//    tier does not fit it is degraded to the finest tier that does, so the farthest L0 tiles are
//    evicted first. Upgrades need `upgradeHeadroom` (5 %) spare below the budget, keeping a tile
//    at its tier needs only the budget itself — this hysteresis prevents budget thrash.
//  * Ordering of the returned transitions: nearest-first, tiles inside the forward cone
//    (± forwardConeHalfAngle_deg around the heading) have their distance scaled by
//    forwardConeWeight (< 1), ties broken by (ty, tx).
#pragma once

#include <cstdint>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/tiling/Tile.h"
#include "nycsim/util/Span.h"

namespace nycsim {
namespace tiling {

/// Finer tiers have larger values so `a > b` means "a is finer than b".
enum class Tier : uint8_t { Unloaded = 0, L3 = 1, L2 = 2, L1 = 3, L0 = 4 };
NYCSIM_API const char* tierName(Tier t);
constexpr int tierIndex(Tier t) { return static_cast<int>(t); }

/// One tile of runtime/tiles.nycb (DATA_CONTRACTS §15 `tiles` record, unpacked).
struct TileInfo {
  int32_t tx = 0;
  int32_t ty = 0;
  float zMin = 0.0f;
  float zMax = 0.0f;
  uint32_t nBuildings = 0;
  uint32_t nProps = 0;
  uint8_t flags = 0;  ///< has_terrain=1, has_water=2, has_land=4
  uint8_t boroughMask = 0;

  static constexpr uint8_t kHasTerrain = 1;
  static constexpr uint8_t kHasWater = 2;
  static constexpr uint8_t kHasLand = 4;
  Tile tile() const { return Tile{tx, ty}; }
};

struct TierRadii {
  double load_m;
  double unload_m;
};

struct SchedulerConfig {
  TierRadii l0{900.0, 1300.0};
  TierRadii l1{2500.0, 3000.0};
  TierRadii l2{12000.0, 13000.0};
  TierRadii l3{40000.0, 43000.0};
  double protectRadius_m = 300.0;
  double lookahead_s = 1.5;
  double forwardConeHalfAngle_deg = 45.0;
  double forwardConeWeight = 0.7;
  uint64_t budgetBytes = 8ull << 30;  ///< 8 GiB CPU-resident cap (ARCHITECTURE §3)
  double upgradeHeadroom = 0.05;

  const TierRadii& radii(Tier t) const;
  /// Validates the ordering constraints (load < unload, radii increase with tier, ...).
  bool valid() const;
};

/// Resident-memory estimate per tile per tier. Constants follow ARCHITECTURE §4.3/§3 (1.2 KB per
/// building shell, 40-byte kit placement records, 501x501 16-bit heightmaps, HLOD fractions).
struct TileCostModel {
  uint64_t fixedBytes = 64u * 1024u;                       ///< bookkeeping, roads, water plane
  uint64_t terrainBytesL01 = 501u * 501u * 2u + 501u * 501u * 4u;  ///< heightmap + layer weights
  uint64_t terrainBytesL2 = 128u * 1024u;                  ///< share of the 4 km merged terrain
  uint64_t terrainBytesL3 = 16u * 1024u;                   ///< share of the 16 km merged terrain
  uint64_t shellBytesPerBuilding = 1200;                   ///< §4.3
  uint64_t kitBytesPerBuildingL0 = 48u * (40u + 64u);      ///< ~48 placements x (record + xform)
  uint64_t facadeBytesPerBuildingL1 = 64;                  ///< facade shader parameters
  uint64_t propBytesL0 = 256;
  uint64_t propBytesL1 = 32;                               ///< impostors
  double shellFractionL2 = 0.15;                           ///< merged / decimated HLOD
  double shellFractionL3 = 0.03;                           ///< only buildings >= 40 m

  uint64_t bytes(const TileInfo& tile, Tier tier) const;
};

struct CameraState {
  double x_m = 0.0;
  double y_m = 0.0;
  double vx_mps = 0.0;
  double vy_mps = 0.0;
  double heading_deg = 0.0;  ///< compass heading of the view direction (0 = north, clockwise)
  double time_s = 0.0;       ///< simulation time, recorded in transitions
};

struct Transition {
  int32_t tx;
  int32_t ty;
  Tier from;
  Tier to;
  double time_s;
  double distanceNow_m;  ///< distance from the (unpredicted) camera when the transition happened
  bool budgetLimited;    ///< the tier is coarser than the radii alone would give
};

struct SchedulerStats {
  uint64_t residentBytes = 0;
  uint32_t countByTier[5] = {0, 0, 0, 0, 0};
  bool overBudget = false;  ///< protected tiles alone exceed the budget
  uint64_t totalLoads = 0;      ///< Unloaded -> any
  uint64_t totalUnloads = 0;    ///< any -> Unloaded
  uint64_t totalUpgrades = 0;   ///< finer tier (includes loads)
  uint64_t totalDowngrades = 0; ///< coarser tier (includes unloads)
  uint64_t totalBudgetDenials = 0;  ///< tile-updates where the budget forced a coarser tier
  uint64_t updates = 0;
};

class NYCSIM_API TileScheduler {
 public:
  struct Entry {
    TileInfo info;
    Tier tier = Tier::Unloaded;
    Tier radiiTier = Tier::Unloaded;  ///< tier the radii alone would give (before budget)
    double distanceNow_m = 0.0;
    double distanceEff_m = 0.0;  ///< min(current, predicted)
    double priority = 0.0;       ///< cone-weighted distance used for ordering
    bool protectedNow = false;
    bool inForwardCone = false;
  };

  /// Copies the catalogue; entries are stored sorted by (ty, tx). Duplicate (tx, ty) records
  /// keep the first occurrence. An invalid config is replaced by the defaults.
  TileScheduler(Span<const TileInfo> tiles, const SchedulerConfig& config = SchedulerConfig(),
                const TileCostModel& cost = TileCostModel());

  /// Recomputes tiers and returns the transitions to apply, nearest-first. No allocation after
  /// the first call with a stable catalogue.
  const std::vector<Transition>& update(const CameraState& camera);

  Tier tierOf(int32_t tx, int32_t ty) const;
  bool contains(int32_t tx, int32_t ty) const;
  size_t tileCount() const { return entries_.size(); }
  Span<const Entry> entries() const { return Span<const Entry>(entries_.data(), entries_.size()); }
  const SchedulerStats& stats() const { return stats_; }
  const SchedulerConfig& config() const { return config_; }
  const TileCostModel& costModel() const { return cost_; }

  /// Forget every tier (everything becomes Unloaded) without emitting transitions.
  void reset();

 private:
  int findIndex(int32_t tx, int32_t ty) const;
  Tier tierFromRadii(double d, Tier current) const;

  SchedulerConfig config_;
  TileCostModel cost_;
  std::vector<Entry> entries_;
  std::vector<uint32_t> order_;
  std::vector<Tier> target_;
  std::vector<uint8_t> budgetLimited_;
  std::vector<Transition> transitions_;
  SchedulerStats stats_;
};

}  // namespace tiling
}  // namespace nycsim
