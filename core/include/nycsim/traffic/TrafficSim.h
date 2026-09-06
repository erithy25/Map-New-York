#pragma once
// nycsim/traffic/TrafficSim.h — the NYC driving agents.
//
// Deterministic, fixed-step (20 Hz) micro-simulation on the lane graph:
//   longitudinal  IDM            (Idm.h)
//   lateral       MOBIL          (Mobil.h)
//   control       signal compliance with the NYC rule set (no right on red,
//                 LPI, all-red), stop-sign first-come/right-hand-rule,
//                 yield and unsignalized gap acceptance (HCM critical
//                 headways), junction conflict locking
//   New York      box blocking, double parking on commercial blocks, honking,
//                 emergency vehicles with pull-right yielding, buses with
//                 dwell, cyclists preferring bike lanes, taxis with roof
//                 lights that can be hailed
//   player        TTC braking, in-lane swerve, full stop for a person in the
//                 road, and a spawn/despawn ring that never creates or removes
//                 an agent inside the player's protected region
//
// Determinism contract: every random draw comes from Rng (SplitMix64); each
// agent owns a stream seeded from (world seed, agent id) so results do not
// depend on iteration order, and accelerations for step n+1 are computed from
// the state at step n only.  Same seed + same inputs ⇒ identical trajectory
// hash (see tests/traffic/test_determinism.cpp).
//
// Allocation contract: every buffer is sized in configure(); step() performs no
// heap allocation.  Spawns above `max_vehicles` are refused, not grown.
//
// Threading: one TrafficSim is single-threaded.  Hosts run it on a worker
// thread and read the published state between steps.

#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/routing/RoadGraph.h"
#include "nycsim/routing/Router.h"
#include "nycsim/traffic/BusRoutes.h"
#include "nycsim/traffic/Density.h"
#include "nycsim/traffic/Idm.h"
#include "nycsim/traffic/Interop.h"
#include "nycsim/traffic/Mobil.h"
#include "nycsim/traffic/PlayerProxy.h"
#include "nycsim/traffic/Random.h"
#include "nycsim/traffic/Signals.h"
#include "nycsim/traffic/SpatialHash.h"
#include "nycsim/traffic/VehicleClass.h"

namespace nycsim {
namespace traffic {

// ---------------------------------------------------------------- config
// Every constant here has a source in docs/verification/traffic/REPORT.md
// §Calibration.  Hosts may change any of them between steps.
struct TrafficConfig {
  float dt = 0.05f;  // 20 Hz (ARCHITECTURE §9)
  uint32_t max_vehicles = 6000;

  // --- IDM / MOBIL -------------------------------------------------------
  float mobil_politeness = 0.20f;   // Kesting et al. 2007 recommend 0.0–0.5
  float mobil_threshold = 0.20f;    // Δa_th [m/s²]
  float mobil_b_safe = 4.0f;        // [m/s²]
  float lc_gap_front_m = 4.0f;      // explicit gap acceptance on top of MOBIL
  float lc_gap_rear_m = 5.0f;
  float keep_right_bias = 0.10f;    // [m/s²] — NY VTL 1120(a) keep right
  float route_pressure_m = 220.f;   // mandatory-change ramp before the junction
  float route_pressure_max = 6.0f;  // [m/s²] bias at the stop line
  float bike_lane_bias = 3.0f;      // cyclists pulled towards the bike lane
  float lane_change_min_speed = 1.5f;   // [m/s] no lane changes from standstill
  float lane_change_cooldown_s = 8.0f;  // hysteresis: no lane-change oscillation

  // --- signals -----------------------------------------------------------
  float yellow_reaction_s = 1.0f;   // driver reaction before braking (ITE)
  float red_run_window_s = 0.8f;    // late entry window for non-law-abiding
  // Distance from the end of the approach lane back to the stopped vehicle's
  // front bumper.  NYC DOT Street Design Manual: a 12 ft (3.66 m) continental
  // crosswalk starting at the kerb line, with the stop line about 4 ft behind
  // it — 5 m in total, which is also what SidewalkGraph places its crossings
  // at, so a queue never stands on the crosswalk.
  float stop_line_setback_m = 5.0f;
  bool no_right_on_red = true;      // NYC Traffic Rules §4-03(a)(2) — always

  // --- stop / yield ------------------------------------------------------
  float stop_speed_mps = 0.35f;     // "complete stop" threshold (NY VTL 1172)
  float stop_dwell_s = 1.0f;
  float gap_major_left_s = 4.1f;    // HCM 6th ed. Exhibit 20-14 base critical
  float gap_minor_right_s = 6.2f;   // headways for two-way stop control
  float gap_minor_through_s = 6.5f;
  float gap_minor_left_s = 7.1f;
  float follow_up_s = 3.3f;         // HCM base follow-up headway, minor left

  // --- box blocking ------------------------------------------------------
  float box_block_p_free = 0.02f;   // P(enter without exit space) at low density
  float box_block_p_jam = 0.35f;    // …and at jam density
  float box_stuck_release_s = 20.f; // creep out of the box after this long

  // --- double parking ----------------------------------------------------
  float double_park_scale = 1.0f;   // multiplies the per-class rate/km
  float double_park_min_s = 30.f;
  float double_park_max_s = 180.f;
  float double_park_min_gap_m = 25.f;  // spacing between double-parked vehicles

  // --- honking -----------------------------------------------------------
  float honk_blocked_s = 3.0f;      // blocked longer than this → honk
  float honk_ttc_s = 1.5f;          // cut off with TTC below this → honk
  float honk_cooldown_s = 6.0f;
  uint32_t max_honks_per_step = 128;

  // --- emergency ---------------------------------------------------------
  float emergency_radius_m = 70.f;  // drivers yield inside this radius
  float emergency_speed_factor = 1.35f;

  // --- player ------------------------------------------------------------
  float player_ttc_brake_s = 1.5f;
  float player_lane_halfwidth_m = 1.6f;  // corridor treated as "in my lane"
  float player_swerve_m = 1.1f;          // in-lane lateral swerve
  float player_person_stop_m = 6.0f;     // stop this far short of a person
  bool use_player_ring = true;

  // --- buses -------------------------------------------------------------
  float bus_dwell_min_s = 15.f;
  float bus_dwell_max_s = 45.f;
  float bus_stop_zone_m = 12.f;

  // --- taxis -------------------------------------------------------------
  float taxi_pickup_s = 12.f;
  float taxi_free_share = 0.45f;  // share of cruising taxis with the light on

  // --- spawning ----------------------------------------------------------
  float spawn_inner_m = 250.f;   // never inside the player's protected region
  float spawn_outer_m = 900.f;   // spawn band around the player
  float despawn_m = 1400.f;      // beyond this the agent is recycled
  float spawn_rate_per_s = 60.f; // cap on spawns per simulated second
  float spawn_headway_m = 12.f;  // minimum clear space at the spawn point
  uint32_t max_routes_per_step = 8;   // routing is amortized across steps
  float reroute_block_s = 90.f;  // genuinely stuck, not merely waiting for a phase
  float reroute_cooldown_s = 45.f;
  bool build_junction_conflicts = true;

  float lateral_rate_mps = 1.2f;  // lane-change / swerve lateral speed
};

// ------------------------------------------------------------- agent state
enum class DriveState : uint8_t {
  Driving = 0,
  StoppedAtLine,   // holding at a red / stop line
  WaitingRow,      // stopped, waiting for a gap or right of way
  DoubleParked,    // pulled over on a commercial block
  BusDwelling,     // at a bus stop
  TaxiPickup,      // hailed, at the curb
  Count
};

enum : uint8_t {
  kVehLawAbiding = 1u << 0,  // never enters on red
  kVehSiren = 1u << 1,       // emergency run in progress
  kVehRoofLight = 1u << 2,   // taxi available for hire
  kVehYieldingEv = 1u << 3,  // pulling right for an emergency vehicle
  kVehBlockedBox = 1u << 4,  // decided to enter without exit space
  kVehStoppedDone = 1u << 5, // completed the mandatory stop at a stop sign
  kVehBrake = 1u << 6,       // brake lights
  kVehHasRoute = 1u << 7     // path leads to dest_lane (else it is wandering)
};

struct Vehicle {
  uint32_t id = 0;
  VehicleClass cls = VehicleClass::Sedan;
  DriveState state = DriveState::Driving;
  uint8_t flags = 0;
  uint8_t lc_dir = 0;  // 0 none, 1 changing left, 2 changing right

  uint32_t lane = routing::kInvalidIndex;
  float s = 0.f;
  float speed = 0.f, accel = 0.f;
  float lateral = 0.f, lateral_target = 0.f;

  routing::Vec3 pos;      // world position of the vehicle centre
  float heading_rad = 0.f;

  float length_m = 4.9f, width_m = 1.8f;
  float v0 = 11.176f;  // desired free-flow speed

  uint32_t path_len = 0, path_pos = 0;
  uint32_t dest_lane = routing::kInvalidIndex;
  float dest_s = 0.f;

  float state_timer = 0.f;      // seconds in the current DriveState
  float dwell_timer = 0.f;      // mandatory stop-sign dwell countdown
  float blocked_time = 0.f;     // seconds effectively stopped in traffic
  float honk_cooldown = 0.f;
  float lc_cooldown = 0.f;
  float reroute_cooldown = 0.f;
  float junction_time = 0.f;    // seconds spent inside the current junction
  float spawn_time = 0.f;
  float distance_m = 0.f;

  uint32_t claim_node = routing::kInvalidIndex;  // stop-sign claim
  float claim_time = 0.f;
  uint8_t exit_now = 0;  // dead end reached: recycle as soon as the ring allows
  uint32_t lc_from = routing::kInvalidIndex;  // lane still occupied laterally

  uint16_t bus_route = 0xFFFFu;
  uint16_t bus_stop_ix = 0xFFFFu;   // stop currently being served
  uint16_t bus_next_stop = 0;       // index into the route's stop list
  float target_x = 0.f, target_y = 0.f;  // taxi pickup / double-park point

  Rng rng;
};

// ------------------------------------------------------------- host events
enum class HonkReason : uint8_t { Blocked = 0, CutOff = 1, Player = 2, Emergency = 3 };

struct HonkEvent {
  float x = 0.f, y = 0.f, z = 0.f;
  uint32_t agent = 0;
  VehicleClass cls = VehicleClass::Sedan;
  HonkReason reason = HonkReason::Blocked;
};

struct TrafficStats {
  uint32_t vehicles = 0;
  uint32_t spawned = 0, despawned = 0, spawn_failures = 0;
  uint32_t stopped_at_red = 0, in_junction = 0, double_parked = 0, dwelling = 0;
  uint32_t lane_changes = 0, honks = 0, reroutes = 0, route_calls = 0, red_light_entries = 0;
  uint32_t box_blocks = 0, emergency_yields = 0;
  float mean_speed_mps = 0.f;
  float target_vehicles = 0.f;
  double sim_time_s = 0.0;
};

// ------------------------------------------------------------------- sim
class TrafficSim {
 public:
  TrafficSim();

  // `g` must be finalized and `sig` bound to it; both must outlive the sim.
  bool configure(const routing::RoadGraph& g, const SignalTable& sig, const TrafficConfig& cfg, uint64_t seed);
  bool configured() const { return graph_ != nullptr; }
  const std::string& lastError() const { return error_; }
  void reset(uint64_t seed);  // removes every agent, keeps the graph

  void setConfig(const TrafficConfig& c) { cfg_ = c; }
  const TrafficConfig& config() const { return cfg_; }
  // Optional collaborators (all may stay null).
  void setRouter(routing::Router* r) { router_ = r; }
  void setDensityTable(const DensityTable* d);
  void setBusRoutes(const BusRouteTable* b) { buses_ = b; }
  void setPedProbe(const PedProbe& p) { ped_probe_ = p; }
  void setPlayer(const PlayerProxy& p) { player_ = p; }
  const PlayerProxy& player() const { return player_; }
  // Local clock: seconds since midnight and the day class (0 weekday, 1 Sat,
  // 2 Sun).  Selects the density cell and the congestion profile.
  void setTimeOfDay(float seconds_since_midnight, uint8_t dow);
  float timeOfDay() const { return tod_s_; }
  uint8_t dow() const { return dow_; }

  // One fixed step of cfg_.dt seconds.
  void step();
  double time() const { return time_s_; }
  uint64_t stepIndex() const { return step_ix_; }

  // Fill the world to the density table's target (routing without the per-step
  // budget).  Call once after configure(); safe to call again after a big
  // time-of-day jump.  Returns the number of agents spawned.
  uint32_t prefill(uint32_t max_spawns = 100000);

  // Explicit spawn (tests, scripted set pieces).  Returns the agent id or
  // kInvalidIndex.  `dest_lane` may be kInvalidIndex → the agent wanders.
  uint32_t spawn(VehicleClass c, uint32_t lane, float s, uint32_t dest_lane = routing::kInvalidIndex,
                 float dest_s = 0.f, bool ignore_player_ring = false);
  bool despawn(uint32_t id, bool ignore_player_ring = false);

  size_t vehicleCount() const { return veh_.size(); }
  const Vehicle& vehicle(size_t i) const { return veh_[i]; }
  const Vehicle* vehicles() const { return veh_.data(); }
  const Vehicle* byId(uint32_t id) const;
  uint32_t indexOfId(uint32_t id) const;

  const HonkEvent* honks(uint32_t& n) const {
    n = honk_count_;
    return honks_.data();
  }
  const TrafficStats& stats() const { return stats_; }

  // FNV-1a over the quantized state of every agent, ordered by agent id: the
  // determinism fingerprint.  Quantization: position 1 mm, speed 1 mm/s.
  uint64_t trajectoryHash() const;

  // Probes handed to the pedestrian simulation.
  VehicleProbe vehicleProbe();

  // --- queries used by the tests, the HUD and the audio system -------------
  // Target fleet size implied by the density table at the current hour.
  float targetVehicles() const { return stats_.target_vehicles; }
  // Vehicles per lane-km actually present, over the lanes of one NTA.
  float measuredDensity(uint16_t nta) const;
  // Signal state a vehicle on `lane` is facing (Off when not signalized).
  VehSignal laneSignal(uint32_t lane) const;
  // The junction lane the agent will use next (kInvalidIndex when unknown).
  uint32_t nextJunction(const Vehicle& v) const;
  bool inProtectedRegion(float x, float y) const;

 private:
  // -------------------------------------------------------------- internals
  struct Neighbour {
    uint32_t index = routing::kInvalidIndex;  // index into veh_
    float gap = 1e9f;                         // bumper to bumper [m]
    float speed = 0.f;
  };
  // How two junction lanes of one intersection interact.
  enum class ConflictKind : uint8_t {
    Cross = 0,       // their paths cross: mutually exclusive
    SameOrigin = 1,  // they diverge from the same approach lane
    Merge = 2        // they converge into the same receiving lane
  };
  struct Conflict {
    uint32_t other;   // conflicting junction lane
    float s_self;     // metres along this lane at the crossing point
    float s_other;
    ConflictKind kind;
  };
  // Mutual-exclusion lock on a crossing movement, refreshed every step by its
  // owner and expiring on its own if the owner vanishes.
  struct JunctionLock {
    uint32_t owner = routing::kInvalidIndex;
    double expiry = 0.0;
  };
  struct NodeClaim {
    uint32_t agent = 0xFFFFFFFFu;
    float arrival = 0.f;
    float dirx = 0.f, diry = 0.f;
    uint8_t turn = 0;
    uint8_t used = 0;
  };

  void rebuildIndex();
  void buildOrder();
  void rebuildSpawnWeights();
  void decide(uint32_t i);
  void integrate(uint32_t i);
  void resolveOverlaps(bool cross_lane);
  void laneClamp();
  uint32_t separateBodies();
  bool laneSlotClaimed(uint32_t lane, float s, float half_len) const;
  void claimLaneSlot(uint32_t lane, float s, float half_len);
  void updateSpawnDespawn();
  void publishStats();

  IdmParams idmOf(const Vehicle& v) const;
  Neighbour leaderInLane(uint32_t lane, float s, float half_len, uint32_t skip) const;
  Neighbour followerInLane(uint32_t lane, float s, float half_len, uint32_t skip) const;
  // Same, but also counting vehicles that are only laterally in the lane
  // because they are half way through a change out of it.
  Neighbour leaderIncludingStraddlers(uint32_t lane, float s, float half_len, uint32_t skip) const;
  Neighbour followerIncludingStraddlers(uint32_t lane, float s, float half_len, uint32_t skip) const;
  Neighbour leaderAhead(const Vehicle& v, float horizon_m) const;  // follows the path
  float laneOccupancyAhead(uint32_t lane, float from_s, float span_m) const;
  bool exitSpaceAvailable(const Vehicle& v, uint32_t junction_lane) const;
  bool junctionClear(const Vehicle& v, uint32_t junction_lane) const;
  void lockJunction(const Vehicle& v, uint32_t junction_lane);
  void releaseJunction(const Vehicle& v);
  bool gapAccepted(const Vehicle& v, uint32_t junction_lane, float critical_gap_s) const;
  float criticalGap(const routing::Lane& jl, bool major) const;
  bool stopSignPriority(Vehicle& v, uint32_t node, uint32_t junction_lane);
  void releaseClaim(Vehicle& v);
  float signalStopDistance(const Vehicle& v, uint32_t junction_lane, float dist_to_line, bool& entered_on_red);
  float playerConstraint(const Vehicle& v, float& swerve_out, bool& brake_hard);
  float emergencyConstraint(Vehicle& v);
  float pedestrianConstraint(const Vehicle& v, uint32_t junction_lane, float dist_to_line) const;
  void considerLaneChange(uint32_t i, float a_current);
  void considerDoublePark(Vehicle& v);
  void considerBusStop(Vehicle& v, float& stop_dist);
  void emitHonk(const Vehicle& v, HonkReason r);
  bool advanceLane(Vehicle& v);
  void extendPath(Vehicle& v);
  bool routeAgent(Vehicle& v, uint32_t to_lane, float to_s, uint32_t avoid_lane = routing::kInvalidIndex);
  void assignBusRoute(Vehicle& v);
  bool advanceBusToNextStop(Vehicle& v);
  uint32_t sampleSpawnLane(Rng& rng) const;
  uint32_t preferredLaneFor(uint32_t lane, VehicleClass c) const;
  VehicleClass sampleClass(Rng& rng, uint16_t nta) const;
  bool laneFreeAt(uint32_t lane, float s, float len) const;
  void buildJunctionConflicts();
  void updatePose(Vehicle& v);
  uint32_t* pathOf(uint32_t slot) { return path_pool_.data() + static_cast<size_t>(slot) * kPathCap; }
  const uint32_t* pathOf(uint32_t slot) const { return path_pool_.data() + static_cast<size_t>(slot) * kPathCap; }

  static float timeToArrivalProbe(const void* ctx, float x, float y, float r);
  static bool freeTaxiProbe(const void* ctx, float x, float y, float r, TaxiSighting& out);
  static bool hailProbe(void* ctx, uint32_t agent, float x, float y);

 public:
  static constexpr uint32_t kPathCap = 64;  // lanes of look-ahead per agent

 private:
  const routing::RoadGraph* graph_ = nullptr;
  const SignalTable* signals_ = nullptr;
  const DensityTable* density_ = nullptr;
  const BusRouteTable* buses_ = nullptr;
  routing::Router* router_ = nullptr;
  PedProbe ped_probe_;
  PlayerProxy player_;
  TrafficConfig cfg_;
  std::string error_;

  std::vector<Vehicle> veh_;          // dense, swap-removed
  std::vector<uint32_t> slot_of_id_;  // id → index into veh_
  std::vector<uint32_t> free_ids_;
  std::vector<uint32_t> path_pool_;   // kPathCap lane indices per id

  // per-step ordering index: agents sorted by (lane, s)
  std::vector<uint64_t> order_keys_;
  std::vector<uint32_t> order_;
  std::vector<uint32_t> lane_first_, lane_num_, lane_stamp_;
  uint32_t stamp_ = 0;

  SpatialHash hash_;
  std::vector<uint32_t> ev_list_;  // indices of vehicles running a siren
  std::vector<Conflict> conflicts_;
  std::vector<uint32_t> conflict_first_, conflict_count_;
  std::vector<JunctionLock> jl_lock_;
  // Lane-change slot reservations, valid for one step: two agents converging on
  // the same gap from opposite lanes must not both take it.
  struct LcClaim {
    float s, half;
    uint32_t next;
  };
  std::vector<LcClaim> lc_claims_;
  std::vector<uint32_t> lc_head_, lc_stamp_;
  // Per-lane list of the agents that are still laterally inside a lane they
  // have already left (lane change in progress), rebuilt with the order index.
  std::vector<uint32_t> straddle_head_, straddle_stamp_, straddle_next_;
  std::vector<NodeClaim> claims_;  // kClaimsPerNode per node
  std::vector<float> nta_lane_km_;
  std::vector<uint32_t> spawn_lanes_;
  std::vector<float> spawn_cdf_;
  std::vector<HonkEvent> honks_;
  uint32_t honk_count_ = 0;
  std::vector<float> new_accel_, new_swerve_;
  std::vector<uint8_t> new_flags_;
  std::vector<uint32_t> new_lane_;
  std::vector<uint32_t> pending_routes_;

  routing::RouteResult route_scratch_;
  routing::RouteProfile profile_scratch_;

  Rng rng_;
  uint64_t seed_ = 1;
  double time_s_ = 0.0;
  uint64_t step_ix_ = 0;
  float tod_s_ = 8.f * 3600.f;
  uint8_t dow_ = 0;
  uint8_t spawn_hour_ = 0xFF;
  float spawn_credit_ = 0.f;
  float retire_credit_ = 0.f;
  uint32_t retire_cursor_ = 0;
  uint32_t goal_cursor_ = 0;
  uint32_t next_id_ = 0;
  uint32_t routes_this_step_ = 0;
  TrafficStats stats_;
};

}  // namespace traffic
}  // namespace nycsim
