#include "nycsim/tiling/TileScheduler.h"

#include <algorithm>
#include <cmath>

#include "nycsim/geo/Ellipsoid.h"

namespace nycsim {
namespace tiling {

const char* tierName(Tier t) {
  switch (t) {
    case Tier::Unloaded: return "unloaded";
    case Tier::L3: return "L3";
    case Tier::L2: return "L2";
    case Tier::L1: return "L1";
    case Tier::L0: return "L0";
  }
  return "?";
}

const TierRadii& SchedulerConfig::radii(Tier t) const {
  switch (t) {
    case Tier::L0: return l0;
    case Tier::L1: return l1;
    case Tier::L2: return l2;
    case Tier::L3:
    case Tier::Unloaded: break;
  }
  return l3;
}

bool SchedulerConfig::valid() const {
  const TierRadii* r[4] = {&l0, &l1, &l2, &l3};
  for (int i = 0; i < 4; ++i) {
    if (!(r[i]->load_m > 0.0) || !(r[i]->unload_m > r[i]->load_m)) return false;
    if (i > 0 && !(r[i]->load_m > r[i - 1]->unload_m)) return false;
  }
  if (!(protectRadius_m >= 0.0) || !(protectRadius_m < l0.load_m)) return false;
  if (!(lookahead_s >= 0.0) || !std::isfinite(lookahead_s)) return false;
  if (!(forwardConeHalfAngle_deg >= 0.0) || forwardConeHalfAngle_deg > 180.0) return false;
  if (!(forwardConeWeight > 0.0) || forwardConeWeight > 1.0) return false;
  if (!(upgradeHeadroom >= 0.0) || upgradeHeadroom >= 1.0) return false;
  return true;
}

uint64_t TileCostModel::bytes(const TileInfo& tile, Tier tier) const {
  const uint64_t nb = tile.nBuildings;
  const uint64_t np = tile.nProps;
  const uint64_t shells = nb * shellBytesPerBuilding;
  const bool terrain = (tile.flags & TileInfo::kHasTerrain) != 0 || (tile.flags & TileInfo::kHasLand) != 0;
  switch (tier) {
    case Tier::Unloaded: return 0;
    case Tier::L0:
      return fixedBytes + (terrain ? terrainBytesL01 : 0) + shells + nb * kitBytesPerBuildingL0 +
             np * propBytesL0;
    case Tier::L1:
      return fixedBytes + (terrain ? terrainBytesL01 : 0) + shells + nb * facadeBytesPerBuildingL1 +
             np * propBytesL1;
    case Tier::L2:
      return fixedBytes / 4 + (terrain ? terrainBytesL2 : 0) +
             static_cast<uint64_t>(std::llround(static_cast<double>(shells) * shellFractionL2));
    case Tier::L3:
      return fixedBytes / 16 + (terrain ? terrainBytesL3 : 0) +
             static_cast<uint64_t>(std::llround(static_cast<double>(shells) * shellFractionL3));
  }
  return 0;
}

namespace {

constexpr Tier kFinestToCoarsest[4] = {Tier::L0, Tier::L1, Tier::L2, Tier::L3};

Tier coarser(Tier t) {
  switch (t) {
    case Tier::L0: return Tier::L1;
    case Tier::L1: return Tier::L2;
    case Tier::L2: return Tier::L3;
    case Tier::L3:
    case Tier::Unloaded: break;
  }
  return Tier::Unloaded;
}

}  // namespace

TileScheduler::TileScheduler(Span<const TileInfo> tiles, const SchedulerConfig& config,
                             const TileCostModel& cost)
    : config_(config.valid() ? config : SchedulerConfig()), cost_(cost) {
  entries_.reserve(tiles.size());
  for (const TileInfo& t : tiles) {
    Entry e;
    e.info = t;
    entries_.push_back(e);
  }
  std::stable_sort(entries_.begin(), entries_.end(),
                   [](const Entry& a, const Entry& b) { return a.info.tile() < b.info.tile(); });
  // Drop duplicates (keep first occurrence of each (tx, ty)).
  entries_.erase(std::unique(entries_.begin(), entries_.end(),
                             [](const Entry& a, const Entry& b) { return a.info.tile() == b.info.tile(); }),
                 entries_.end());
  order_.resize(entries_.size());
  target_.resize(entries_.size(), Tier::Unloaded);
  budgetLimited_.resize(entries_.size(), 0);
  transitions_.reserve(entries_.size());
}

int TileScheduler::findIndex(int32_t tx, int32_t ty) const {
  const Tile key{tx, ty};
  auto it = std::lower_bound(entries_.begin(), entries_.end(), key,
                             [](const Entry& e, const Tile& k) { return e.info.tile() < k; });
  if (it == entries_.end() || !(it->info.tile() == key)) return -1;
  return static_cast<int>(it - entries_.begin());
}

Tier TileScheduler::tierOf(int32_t tx, int32_t ty) const {
  const int i = findIndex(tx, ty);
  return i < 0 ? Tier::Unloaded : entries_[static_cast<size_t>(i)].tier;
}

bool TileScheduler::contains(int32_t tx, int32_t ty) const { return findIndex(tx, ty) >= 0; }

void TileScheduler::reset() {
  for (Entry& e : entries_) {
    e.tier = Tier::Unloaded;
    e.radiiTier = Tier::Unloaded;
  }
  transitions_.clear();
  stats_ = SchedulerStats();
}

Tier TileScheduler::tierFromRadii(double d, Tier current) const {
  Tier candidate = Tier::Unloaded;
  for (Tier t : kFinestToCoarsest) {
    if (d < config_.radii(t).load_m) {
      candidate = t;
      break;
    }
  }
  if (current != Tier::Unloaded && current > candidate) {
    // Hysteresis: keep the finer current tier until beyond its unload radius.
    if (d <= config_.radii(current).unload_m) return current;
  }
  return candidate;
}

const std::vector<Transition>& TileScheduler::update(const CameraState& camera) {
  transitions_.clear();
  const size_t n = entries_.size();
  const double cx = std::isfinite(camera.x_m) ? camera.x_m : 0.0;
  const double cy = std::isfinite(camera.y_m) ? camera.y_m : 0.0;
  const double vx = std::isfinite(camera.vx_mps) ? camera.vx_mps : 0.0;
  const double vy = std::isfinite(camera.vy_mps) ? camera.vy_mps : 0.0;
  const double px = cx + vx * config_.lookahead_s;
  const double py = cy + vy * config_.lookahead_s;
  const double heading = std::isfinite(camera.heading_deg) ? camera.heading_deg : 0.0;
  const double hx = std::sin(heading * geo::kDegToRad);  // east component
  const double hy = std::cos(heading * geo::kDegToRad);  // north component
  const double cosHalf = std::cos(config_.forwardConeHalfAngle_deg * geo::kDegToRad);

  // 1. Distances, protection, radii-based target tier.
  for (size_t i = 0; i < n; ++i) {
    Entry& e = entries_[i];
    const Tile tile = e.info.tile();
    e.distanceNow_m = distanceToTile(tile, cx, cy);
    const double dPred = distanceToTile(tile, px, py);
    e.distanceEff_m = std::fmin(e.distanceNow_m, dPred);
    e.protectedNow = e.distanceNow_m <= config_.protectRadius_m;
    const double dx = tile.centreX() - cx;
    const double dy = tile.centreY() - cy;
    const double len = std::hypot(dx, dy);
    e.inForwardCone = len > 0.0 && (dx * hx + dy * hy) / len >= cosHalf;
    e.priority = e.inForwardCone ? e.distanceEff_m * config_.forwardConeWeight : e.distanceEff_m;
    e.radiiTier = e.protectedNow ? Tier::L0 : tierFromRadii(e.distanceEff_m, e.tier);
    target_[i] = e.radiiTier;
    budgetLimited_[i] = 0;
    order_[i] = static_cast<uint32_t>(i);
  }

  // 2. Deterministic priority order: nearest first (cone-weighted), then (ty, tx).
  std::sort(order_.begin(), order_.end(), [this](uint32_t a, uint32_t b) {
    const Entry& ea = entries_[a];
    const Entry& eb = entries_[b];
    if (ea.priority != eb.priority) return ea.priority < eb.priority;
    return ea.info.tile() < eb.info.tile();
  });

  // 3. Budget pass: grant tiers nearest-first, degrade what does not fit.
  const uint64_t budget = config_.budgetBytes;
  const uint64_t upgradeLimit =
      static_cast<uint64_t>(static_cast<double>(budget) * (1.0 - config_.upgradeHeadroom));
  uint64_t resident = 0;
  bool overBudget = false;
  for (uint32_t idx : order_) {
    Entry& e = entries_[idx];
    Tier t = target_[idx];
    if (t == Tier::Unloaded) continue;
    if (e.protectedNow) {
      resident += cost_.bytes(e.info, t);
      if (resident > budget) overBudget = true;
      continue;
    }
    for (;;) {
      const uint64_t c = cost_.bytes(e.info, t);
      const uint64_t limit = (t > e.tier) ? upgradeLimit : budget;
      if (resident + c <= limit) {
        resident += c;
        break;
      }
      t = coarser(t);
      budgetLimited_[idx] = 1;
      if (t == Tier::Unloaded) break;
    }
    if (budgetLimited_[idx]) ++stats_.totalBudgetDenials;
    target_[idx] = t;
  }

  // 4. Apply and record transitions in priority order.
  SchedulerStats s = stats_;
  s.residentBytes = resident;
  s.overBudget = overBudget;
  for (uint32_t& c : s.countByTier) c = 0;
  for (uint32_t idx : order_) {
    Entry& e = entries_[idx];
    const Tier t = target_[idx];
    if (t != e.tier) {
      Transition tr;
      tr.tx = e.info.tx;
      tr.ty = e.info.ty;
      tr.from = e.tier;
      tr.to = t;
      tr.time_s = camera.time_s;
      tr.distanceNow_m = e.distanceNow_m;
      tr.budgetLimited = budgetLimited_[idx] != 0;
      transitions_.push_back(tr);
      if (e.tier == Tier::Unloaded) ++s.totalLoads;
      if (t == Tier::Unloaded) ++s.totalUnloads;
      if (t > e.tier) {
        ++s.totalUpgrades;
      } else {
        ++s.totalDowngrades;
      }
      e.tier = t;
    }
    ++s.countByTier[tierIndex(e.tier)];
  }
  ++s.updates;
  stats_ = s;
  return transitions_;
}

}  // namespace tiling
}  // namespace nycsim
