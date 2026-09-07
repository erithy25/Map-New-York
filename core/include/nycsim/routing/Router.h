#pragma once
// nycsim/routing/Router.h — lane-level routing for the GPS and the traffic AI.
//
// Algorithm: bidirectional A* with landmark potentials (ALT, Goldberg &
// Harrelson 2005) over the unified lane graph (road lanes + junction lanes +
// same-segment lane-change edges).  No contraction hierarchies: the graph is
// mutable at runtime (closures, turn restrictions, time-dependent penalties)
// and ALT's preprocessing (a few Dijkstras) survives edge-weight increases.
//
// Cost = travel time in seconds:
//   w(u→v) = traverse(v) + penalty(v)
//   traverse(v) = length(v) / min(speed(v), profile.max_speed) × congestion(hour) × kindFactor
//   penalty(v)  = turn penalty (junction lanes) + control delay (signal expected
//                 delay r²/2C, stop/yield fixed) + left-across-traffic × congestion(hour)
//   lane-change edge (u → left/right neighbour) = profile.lane_change_cost_s
// Landmark distances are computed with the lower-bound weights (congestion 1,
// no profile caps), so every profile/hour query keeps A* admissible.
//
// Threading: a Router is single-threaded; hosts that route from several
// threads create one Router per thread (they share the graph, which is
// immutable during queries).  Query scratch is preallocated on attach();
// results are written into caller-owned RouteResult buffers whose capacity is
// reused, so steady-state routing does not allocate.

#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/routing/RoadGraph.h"

namespace nycsim {
namespace routing {

struct RouteProfile {
  uint32_t lane_kinds = kMotorLaneKinds;
  bool allow_highway = true;
  bool allow_bridge = true;
  bool allow_tunnel = true;
  float max_speed_mps = 40.f;
  // Multiplier on non-bike-lane traversal (cyclists: 1.6 → prefer bike lanes).
  float non_bike_lane_factor = 1.f;
  // Multiplier on all turn penalties (trucks/buses 1.5).
  float turn_penalty_scale = 1.f;
  float lane_change_cost_s = 2.f;
  // Departure time of day (seconds since local midnight) and day-of-week class
  // (0 weekday, 1 Saturday, 2 Sunday) — selects the congestion multiplier.
  float depart_time_s = 8.f * 3600.f;
  uint8_t dow = 0;
  // Temporary avoidance (re-route on block): extra seconds when entering this lane.
  uint32_t avoid_lane = kInvalidIndex;
  float avoid_penalty_s = 600.f;
};

struct CostModel {
  float right_turn_s = 2.5f;
  float left_turn_s = 6.0f;
  float uturn_s = 20.f;
  float left_across_traffic_s = 8.f;  // permissive left through opposing flow (peak, × congestion)
  float stop_sign_s = 4.f;
  float all_way_stop_s = 6.f;
  float yield_s = 2.f;
  // Signal delay used when the node is signalized but no plan is attached:
  // 45 s red in a 90 s cycle → 45²/(2·90) = 11.25 s.
  float default_signal_delay_s = 11.25f;
  // Travel-time multipliers by hour (weekday / Saturday / Sunday), ≥ 1.
  float congestion[3][24];
  CostModel();
  float congestionAt(float time_of_day_s, uint8_t dow) const;
};

struct Instruction {
  enum class Kind : uint8_t {
    Depart, Continue, TurnLeft, TurnRight, SlightLeft, SlightRight, SharpLeft, SharpRight, UTurn, Ramp, Bridge, Tunnel, Arrive
  };
  Kind kind = Kind::Continue;
  float distance_m = 0.f;    // distance driven since the previous instruction
  float cumulative_m = 0.f;  // distance from the route start to this manoeuvre
  uint32_t lane = kInvalidIndex;  // lane where the manoeuvre begins (junction lane for turns)
  Vec3 position;
  std::string street;  // street the instruction leads onto
  std::string text;    // e.g. "Turn left onto 5th Ave"
};

struct RouteResult {
  bool ok = false;
  std::vector<uint32_t> lanes;  // lane indices in driving order (from_lane … to_lane)
  float cost_s = 0.f;     // generalized cost = ETA with penalties and congestion
  float eta_s = 0.f;      // same as cost_s (kept separately for hosts that reweight)
  float free_flow_s = 0.f;
  float length_m = 0.f;
  uint32_t settled = 0;  // nodes settled by the search (diagnostics)
  std::vector<Instruction> instructions;
  std::vector<Vec3> polyline;  // minimap polyline (lane vertices, ≤ 1 per 2 m)
  void clear() {
    ok = false;
    lanes.clear();
    cost_s = eta_s = free_flow_s = length_m = 0.f;
    settled = 0;
    instructions.clear();
    polyline.clear();
  }
};

struct RouteQuery {
  uint32_t from_lane = kInvalidIndex;
  float from_s = 0.f;
  uint32_t to_lane = kInvalidIndex;
  float to_s = 0.f;
  RouteProfile profile;
  bool want_instructions = true;
  bool want_polyline = true;
};

class Router {
 public:
  Router();
  // Preprocess landmarks.  `landmarks` 0 → plain bidirectional Dijkstra.
  bool attach(const RoadGraph& g, uint32_t landmarks = 8, uint64_t seed = 1);
  bool attached() const { return graph_ != nullptr; }
  const std::string& lastError() const { return error_; }

  void setCostModel(const CostModel& m) { cost_ = m; }
  const CostModel& costModel() const { return cost_; }
  // Extra per-lane entry cost (seconds), e.g. signal expected delay for a
  // junction lane.  Applied in queries AND in landmark preprocessing when set
  // before attach(); otherwise only in queries (still admissible: ≥ 0).
  void setLaneExtraCost(uint32_t lane, float seconds);
  float laneExtraCost(uint32_t lane) const { return lane < extra_.size() ? extra_[lane] : 0.f; }

  bool route(const RouteQuery& q, RouteResult& out);
  // Address / POI → nearest allowed lane → route.
  bool routePoints(float x0, float y0, float x1, float y1, const RouteProfile& profile, RouteResult& out,
                   float snap_radius_m = 60.f);
  NearestLane snap(float x, float y, const RouteProfile& profile, float snap_radius_m = 60.f) const;

  // Instruction / polyline generation on an existing lane sequence.
  void buildInstructions(const uint32_t* lanes, size_t n, float from_s, float to_s, std::vector<Instruction>& out) const;
  void buildPolyline(const uint32_t* lanes, size_t n, float from_s, float to_s, std::vector<Vec3>& out) const;
  // Cost of one edge u→v under a profile (exposed for tests and the traffic AI).
  float edgeCost(uint32_t u, uint32_t v, const RouteProfile& p, float congestion) const;
  bool edgeAllowed(uint32_t v, const RouteProfile& p) const;
  // Free-flow traversal time of a lane (no congestion).
  float traverseSeconds(uint32_t v) const;

  uint32_t landmarkCount() const { return static_cast<uint32_t>(landmarks_.size()); }
  const std::vector<uint32_t>& landmarks() const { return landmarks_; }

 private:
  struct HeapItem {
    float key;
    uint32_t node;
  };
  struct Heap {
    std::vector<HeapItem> a;
    void clear() { a.clear(); }
    bool empty() const { return a.empty(); }
    void push(float key, uint32_t node);
    HeapItem pop();
    float topKey() const { return a.front().key; }
  };

  float penalty(uint32_t v, const RouteProfile* p, float congestion) const;
  float lowerBoundEdge(uint32_t u, uint32_t v) const;
  void dijkstraLowerBound(uint32_t source, bool reverse, std::vector<float>& dist);
  void selectLandmarks(uint32_t count, uint64_t seed);
  float potentialForward(uint32_t v, uint32_t t) const;   // lower bound dist(v, t)
  float potentialReverse(uint32_t v, uint32_t s) const;   // lower bound dist(s, v)
  void chooseActiveLandmarks(uint32_t s, uint32_t t);
  static const char* compass8(float heading_rad);

  const RoadGraph* graph_ = nullptr;
  CostModel cost_;
  std::vector<float> extra_;
  std::string error_;

  // ALT tables: dist_from_[L*n + v] = d(L, v), dist_to_[L*n + v] = d(v, L)
  std::vector<uint32_t> landmarks_;
  std::vector<float> dist_from_, dist_to_;
  uint32_t active_[6];
  uint32_t active_count_ = 0;

  // query scratch
  std::vector<float> df_, dr_;
  std::vector<uint32_t> pf_, pr_, stamp_f_, stamp_r_;
  std::vector<uint8_t> settled_f_, settled_r_;
  std::vector<uint32_t> touched_;
  Heap hf_, hr_;
  uint32_t stamp_ = 0;
  std::vector<float> scratch_dist_;
  std::vector<uint32_t> tmp_path_;
};

}  // namespace routing
}  // namespace nycsim
