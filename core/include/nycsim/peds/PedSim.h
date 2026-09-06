#pragma once
// nycsim/peds/PedSim.h — the New York crowd.
//
// Deterministic, fixed-step (20 Hz) social-force simulation on the sidewalk
// graph: Helbing driving/repulsion/obstacle forces inside sidewalk corridors,
// crosswalks gated by the real signal phase (with a jaywalking model and
// per-agent risk tolerance), an activity state machine (walk to a POI, wait,
// enter the subway, hail a cab, sit on a stoop or bench, jog a park loop,
// photograph a landmark), and the 12-dimensional variety vector with a
// no-duplicates-within-60 m rule.
//
// Wall safety is structural, not statistical: an agent's lateral offset inside
// its corridor is hard-clamped every step, so it cannot leave the sidewalk
// through a building line however large the forces become.
//
// Allocation contract: everything is sized in configure(); step() allocates
// nothing.  Determinism contract: one Rng stream per agent, seeded from
// (world seed, agent id).

#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/peds/SidewalkGraph.h"
#include "nycsim/peds/SocialForce.h"
#include "nycsim/peds/Variety.h"
#include "nycsim/traffic/Density.h"
#include "nycsim/traffic/Interop.h"
#include "nycsim/traffic/PlayerProxy.h"
#include "nycsim/traffic/Random.h"
#include "nycsim/traffic/Signals.h"
#include "nycsim/traffic/SpatialHash.h"

namespace nycsim {
namespace peds {

enum class PedActivity : uint8_t {
  Walk = 0,        // heading for the current goal
  WaitCurb,        // at a crosswalk, waiting for the phase or a gap
  Cross,           // inside a crosswalk
  Browse,          // stopped at a storefront
  Sit,             // stoop or bench
  Jog,             // park loop at running speed
  Photograph,      // stopped, facing a landmark
  HailCab,         // arm out at the kerb
  RideAway,        // in a taxi, about to be removed
  EnterSubway,     // at a subway entrance, about to be removed
  Count
};

enum : uint8_t {
  kPedOnRoad = 1u << 0,      // inside a crosswalk or jaywalking
  kPedJaywalker = 1u << 1,   // will cross against the signal given a gap
  kPedJaywalking = 1u << 2,  // doing it right now
  kPedWantsCab = 1u << 3,
  kPedJogger = 1u << 4,
  kPedTourist = 1u << 5,
  kPedFastZone = 1u << 6,    // Midtown walking speed
  kPedHasGoal = 1u << 7
};

struct PedConfig {
  float dt = 0.05f;
  uint32_t max_peds = 24000;

  SocialForceParams force;
  float body_radius_m = 0.25f;   // shoulder half-width used in the repulsion
  float corridor_shoulder_m = 0.30f;  // clearance kept from the corridor edge

  // Desired speeds.  Weidmann (1993) gives a free walking speed of
  // 1.34 ± 0.26 m/s; NYCSim uses N(1.40, 0.20) clipped to [0.6, 2.2] and
  // N(1.60, 0.20) inside the Midtown fast zone (ARCHITECTURE §10).
  float speed_mean = 1.40f, speed_sd = 0.20f;
  float speed_min = 0.60f, speed_max = 2.20f;
  float fast_zone_speed_mean = 1.60f;
  float jog_speed_mps = 2.90f;
  float max_speed_factor = 1.30f;

  // Crossing behaviour.
  float jaywalk_share = 0.30f;        // share of agents that will cross against
  float flash_cross_risk = 0.55f;     // risk needed to start on flashing DW
  float crossing_margin_s = 2.0f;     // gap needed beyond the crossing time
  float curb_wait_max_s = 120.f;      // give up and re-route after this
  float unsignalized_gap_s = 5.0f;    // required vehicle gap with no signal

  // Activities.
  float browse_min_s = 15.f, browse_max_s = 120.f;
  float sit_min_s = 60.f, sit_max_s = 600.f;
  float photo_min_s = 10.f, photo_max_s = 60.f;
  float jog_min_s = 300.f, jog_max_s = 1500.f;
  float hail_radius_m = 40.f;         // a taxi with its light on this close
  float hail_timeout_s = 90.f;
  float taxi_board_s = 8.f;
  float subway_enter_s = 3.f;
  float sit_share = 0.10f, jog_share = 0.04f, tourist_share = 0.12f, cab_share = 0.06f;

  // Variety.
  float uniqueness_radius_m = 60.f;
  uint32_t uniqueness_retries = 8;

  // Spawn / despawn.
  float spawn_rate_per_s = 200.f;
  float despawn_m = 900.f;
  bool use_player_ring = true;
  uint32_t max_paths_per_step = 96;
  float ped_per_m2_default = 0.02f;
};

struct Pedestrian {
  uint32_t id = 0;
  float x = 0.f, y = 0.f, z = 0.f;
  float vx = 0.f, vy = 0.f;
  float desired_speed = 1.4f;
  float risk = 0.f;  // [0,1]; > 1 − jaywalk_share ⇒ jaywalker
  uint32_t edge = routing::kInvalidIndex;
  float s = 0.f;        // metres along the edge from node a
  float lateral = 0.f;  // signed offset from the centreline (+left of a→b)
  float pref_lateral = 0.f;
  float prev_x = 0.f, prev_y = 0.f;  // last step's position (wall constraint)
  int8_t dir = 1;  // +1 towards b, −1 towards a
  PedActivity activity = PedActivity::Walk;
  uint8_t flags = 0;
  float timer = 0.f;
  float wait_time = 0.f;
  uint32_t goal_poi = routing::kInvalidIndex;
  uint32_t path_len = 0, path_pos = 0;
  uint32_t hail_agent = routing::kInvalidIndex;
  VarietyVector variety;
  uint64_t signature = 0;
  Rng rng;
};

struct PedStats {
  uint32_t peds = 0;
  uint32_t spawned = 0, despawned = 0, spawn_failures = 0;
  uint32_t crossing = 0, waiting = 0, jaywalking = 0, sitting = 0, jogging = 0;
  uint32_t hailing = 0, cabs_hailed = 0, subway_entries = 0, photographs = 0;
  uint32_t uniqueness_redraws = 0, uniqueness_failures = 0;
  uint32_t paths_built = 0, path_failures = 0;
  float mean_speed_mps = 0.f;
  float target_peds = 0.f;
  double sim_time_s = 0.0;
};

class PedSim {
 public:
  static constexpr uint32_t kPathCap = 24;

  PedSim();
  // `w` must be finalized; `sig` may be null (every crossing unsignalized).
  bool configure(const SidewalkGraph& w, const traffic::SignalTable* sig, const PedConfig& cfg, uint64_t seed);
  bool configured() const { return walk_ != nullptr; }
  const std::string& lastError() const { return error_; }
  void reset(uint64_t seed);

  void setConfig(const PedConfig& c) { cfg_ = c; }
  const PedConfig& config() const { return cfg_; }
  void setVehicleProbe(const traffic::VehicleProbe& p) { veh_probe_ = p; }
  void setPlayer(const traffic::PlayerProxy& p) { player_ = p; }
  void setDensityTable(const traffic::DensityTable* d) { density_ = d; }
  // NTAs whose walking speed is the Midtown distribution.
  void setFastZone(uint16_t nta, bool fast);
  void setTimeOfDay(float seconds_since_midnight, uint8_t dow);

  void step();
  double time() const { return time_s_; }
  uint32_t prefill(uint32_t count);

  uint32_t spawn(uint32_t edge, float s, bool ignore_player_ring = false);
  bool despawn(uint32_t id, bool ignore_player_ring = false);

  size_t pedCount() const { return peds_.size(); }
  const Pedestrian& ped(size_t i) const { return peds_[i]; }
  const Pedestrian* peds() const { return peds_.data(); }
  uint32_t indexOfId(uint32_t id) const;
  const PedStats& stats() const { return stats_; }
  uint64_t trajectoryHash() const;

  // Probe handed to the traffic simulation.
  traffic::PedProbe pedProbe();

  // Queries used by the tests.
  // Number of agents whose signature duplicates another agent's within
  // `uniqueness_radius_m`.  0 is the contract.
  uint32_t duplicateSignatures() const;
  // Pedestrians per square metre of sidewalk in one NTA.
  float measuredDensity(uint16_t nta) const;
  traffic::PedSignal crosswalkState(uint32_t edge) const;

 private:
  void rebuildHashes();
  void updateAgent(uint32_t i);
  void integrate(uint32_t i);
  void chooseGoal(Pedestrian& p);
  bool pathTo(Pedestrian& p, uint32_t goal_node);
  uint32_t currentNodeAhead(const Pedestrian& p) const;
  bool mayEnterCrosswalk(const Pedestrian& p, uint32_t edge) const;
  void arriveAtGoal(Pedestrian& p);
  void updateSpawnDespawn();
  void drawAppearance(Pedestrian& p);
  bool signatureUnique(uint64_t sig, float x, float y, uint32_t skip_id) const;
  uint32_t* pathOf(uint32_t id) { return path_pool_.data() + static_cast<size_t>(id) * kPathCap; }
  const uint32_t* pathOf(uint32_t id) const { return path_pool_.data() + static_cast<size_t>(id) * kPathCap; }
  bool advanceEdge(Pedestrian& p);
  void reprojectOntoEdge(Pedestrian& p);
  bool crossesWall(float x0, float y0, float x1, float y1) const;
  float edgeWidthHalf(uint32_t edge) const;

  static uint32_t roadPedsProbe(const void* ctx, float x, float y, float r);

  const SidewalkGraph* walk_ = nullptr;
  const traffic::SignalTable* signals_ = nullptr;
  const traffic::DensityTable* density_ = nullptr;
  traffic::VehicleProbe veh_probe_;
  traffic::PlayerProxy player_;
  PedConfig cfg_;
  std::string error_;

  std::vector<Pedestrian> peds_;
  std::vector<uint32_t> slot_of_id_;
  std::vector<uint32_t> free_ids_;
  std::vector<uint32_t> path_pool_;
  std::vector<uint8_t> fast_zone_;
  std::vector<float> nta_sidewalk_m2_;
  std::vector<uint32_t> spawn_edges_;
  std::vector<float> spawn_cdf_;

  SpatialHash hash_;       // neighbours, cell ≈ the repulsion cutoff
  SpatialHash sig_hash_;   // 60 m cells for the uniqueness rule
  SpatialHash road_hash_;  // only the agents on the roadway — drivers query this
  std::vector<uint32_t> road_ids_;
  std::vector<float> fx_, fy_;

  Rng rng_;
  uint64_t seed_ = 1;
  double time_s_ = 0.0;
  uint64_t step_ix_ = 0;
  float tod_s_ = 8.f * 3600.f;
  uint8_t dow_ = 0;
  uint32_t next_id_ = 0;
  uint32_t paths_this_step_ = 0;
  float spawn_credit_ = 0.f;
  PedStats stats_;
};

}  // namespace peds
}  // namespace nycsim
