#pragma once
// nycsim/traffic/Signals.h — traffic-signal plans (DATA_CONTRACTS §7
// roads/signals.parquet, §15 runtime/signals.nycb) and their pure time
// functions.  State is a function of absolute simulation time only, so the
// traffic and pedestrian modules stay deterministic and never store per-signal
// mutable state.
//
// Phase model (NYC DOT two-phase pretimed controller with LPI where flagged):
//   phase i = [ LPI lpi_s | green_s | yellow_s | allred_s ]
//     vehicles of `group`: RED during LPI, GREEN, YELLOW, RED(all-red)
//     pedestrians parallel to `group`: WALK for ped_walk_s from the phase start
//       (this covers the LPI), then FLASH (flashing DON'T WALK / countdown)
//       for ped_flash_s, then steady DON'T WALK.
//   Phases run in order; the effective cycle is the sum of phase durations
//   (the contract's cycle_s is checked against it, see bind()).
//
// Calibration constants (documented in docs/verification/traffic/REPORT.md):
//   cycle 90 s (Midtown/major arterials) or 60 s (neighbourhood streets),
//   yellow 3.0 s, all-red 2.0 s (NYC DOT standard pretimed intervals),
//   LPI 7 s where flagged, flashing DON'T WALK sized for 3.5 ft/s (1.07 m/s)
//   crossing speed per MUTCD §4E.06 (NYC uses 3.5 ft/s).

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/routing/RoadGraph.h"

namespace nycsim {
namespace traffic {

enum class VehSignal : uint8_t { Red = 0, Yellow = 1, Green = 2, Off = 3 };
enum class PedSignal : uint8_t { DontWalk = 0, Walk = 1, Flash = 2, Off = 3 };

struct SignalPhase {
  int32_t group = 0;
  float green_s = 33.f;
  float yellow_s = 3.f;
  float allred_s = 2.f;
  float ped_walk_s = 14.f;   // WALK (incl. LPI)
  float ped_flash_s = 24.f;  // flashing DON'T WALK
  float lpi_s = 0.f;         // leading pedestrian interval
  float duration() const { return lpi_s + green_s + yellow_s + allred_s; }
};

struct SignalPlan {
  int64_t node_id = 0;
  int32_t controller_id = 0;
  float cycle_s = 90.f;   // effective (sum of phases)
  float offset_s = 0.f;
  uint32_t first_phase = 0, phase_count = 0;
  uint32_t node_index = routing::kInvalidIndex;  // set by bind()
};

// Default NYC DOT-style two-phase plan (both movements get an equal split).
struct DefaultPlanParams {
  float cycle_s = 90.f;
  float yellow_s = 3.f;
  float allred_s = 2.f;
  float lpi_s = 7.f;       // 0 disables
  float ped_flash_s = 0.f;  // 0 → computed from crossing distance / 1.07 m/s (min 7 s)
  float crossing_distance_m = 18.f;  // used when ped_flash_s == 0
};

class SignalTable {
 public:
  static constexpr uint32_t kMaxCachedGroups = 8;

  void clear();
  void reserve(size_t plans, size_t phases);
  uint32_t addPlan(int64_t node_id, int32_t controller_id, float offset_s, const SignalPhase* phases, size_t n);
  // §15 runtime/signals.nycb.  Does not bind (call bind afterwards).
  bool loadFromNycb(const uint8_t* data, size_t len);
  // Resolve node ids → node indices against a finalized graph.  Unknown nodes
  // are kept (node_index = kInvalidIndex) but reported in lastError().
  bool bind(const routing::RoadGraph& g);
  // For every node with control == Signal and no plan, synthesize a default
  // plan whose phases are the distinct signal groups of the node's junction
  // lanes (in ascending order).  Returns the number of plans added.
  uint32_t addDefaultPlans(const routing::RoadGraph& g, const DefaultPlanParams& p);

  size_t planCount() const { return plans_.size(); }
  const SignalPlan& plan(uint32_t i) const { return plans_[i]; }
  const SignalPhase* phases(uint32_t plan, uint32_t& n) const {
    n = plans_[plan].phase_count;
    return phases_.data() + plans_[plan].first_phase;
  }
  uint32_t planForNode(uint32_t node_index) const {
    return node_index < node_to_plan_.size() ? node_to_plan_[node_index] : routing::kInvalidIndex;
  }
  const std::string& lastError() const { return error_; }

  // Pure time functions.  `t` is absolute simulation time in seconds.
  VehSignal vehicleState(uint32_t plan, int32_t group, double t) const;
  PedSignal pedState(uint32_t plan, int32_t group, double t) const;
  // Seconds until the group's next green start (0 if green now).
  float timeToGreen(uint32_t plan, int32_t group, double t) const;
  // Seconds of green remaining (0 if not green).
  float greenRemaining(uint32_t plan, int32_t group, double t) const;
  // Router statistics: expected delay for a uniformly random arrival, r²/(2C)
  // (Webster's uniform-delay term without the flow ratio), and the red share.
  float expectedDelay(uint32_t plan, int32_t group) const;
  float redFraction(uint32_t plan, int32_t group) const;
  // Group known to this plan?
  bool hasGroup(uint32_t plan, int32_t group) const;

  // Per-step cache for hot loops: fills states for groups 0..kMaxCachedGroups-1.
  // Logically const (a memoization of the pure time functions above), so the
  // traffic simulation can hold the table by const reference.
  //
  // Cost is O(refreshed plans x 8).  On the synthetic Midtown grid that is
  // 3,000 operations a step; on the real 19,814-plan table it is 158,000, of
  // which all but a few hundred are for intersections nowhere near the player.
  // setActiveWindow() restricts the refresh to the plans inside the streamed
  // region; a plan outside it is simply not memoized, and the accessors below
  // fall back to the pure time function, so the value a caller sees is the same
  // either way — only the cost changes.
  void cacheStates(double t) const;
  /// Refresh only the plans whose intersection lies in this rectangle (metres,
  /// NYC_TM).  Requires bind().  Cheap to call every step: the plan list is
  /// only rebuilt when the covered grid cells change.
  void setActiveWindow(float minx, float miny, float maxx, float maxy) const;
  /// Back to refreshing every plan (the default).
  void clearActiveWindow() const;
  /// Plans the last cacheStates() actually refreshed (diagnostics).
  uint32_t cachedPlanCount() const { return cached_plans_; }

  VehSignal cachedVehicleState(uint32_t plan, int32_t group) const {
    if (group < 0 || group >= static_cast<int32_t>(kMaxCachedGroups)) return VehSignal::Off;
    if (plan >= cache_stamp_.size()) return VehSignal::Off;  // no such plan
    if (cache_stamp_[plan] != cache_epoch_) return vehicleState(plan, group, cache_time_);
    return static_cast<VehSignal>(veh_cache_[plan * kMaxCachedGroups + static_cast<uint32_t>(group)]);
  }
  PedSignal cachedPedState(uint32_t plan, int32_t group) const {
    if (group < 0 || group >= static_cast<int32_t>(kMaxCachedGroups)) return PedSignal::Off;
    if (plan >= cache_stamp_.size()) return PedSignal::Off;  // no such plan
    if (cache_stamp_[plan] != cache_epoch_) return pedState(plan, group, cache_time_);
    return static_cast<PedSignal>(ped_cache_[plan * kMaxCachedGroups + static_cast<uint32_t>(group)]);
  }
  double cachedTime() const { return cache_time_; }

 private:
  float cycleTime(uint32_t plan, double t) const;
  void cacheOnePlan(uint32_t pi, double t) const;
  void buildPlanGrid();
  uint32_t cellOfPos(float x, float y) const;
  struct PlanPos {
    float x, y;
    uint32_t plan;
  };
  std::vector<PlanPos> plan_pos_;
  std::vector<SignalPlan> plans_;
  std::vector<SignalPhase> phases_;
  std::vector<uint32_t> node_to_plan_;
  // Coarse grid over the plans, built by bind(), used by setActiveWindow().
  std::vector<uint32_t> grid_first_, grid_plans_;
  float grid_x0_ = 0.f, grid_y0_ = 0.f, grid_cell_ = 1000.f;
  uint32_t grid_nx_ = 0, grid_ny_ = 0;
  mutable std::vector<uint32_t> active_;
  mutable bool window_active_ = false;
  mutable int win_cx0_ = 0, win_cy0_ = 0, win_cx1_ = -1, win_cy1_ = -1;
  mutable std::vector<uint8_t> veh_cache_, ped_cache_;
  mutable std::vector<uint32_t> cache_stamp_;
  mutable uint32_t cache_epoch_ = 0;
  mutable uint32_t cached_plans_ = 0;
  mutable double cache_time_ = -1.0;
  std::string error_;
};

}  // namespace traffic
}  // namespace nycsim
