#pragma once
// nycsim/routing/RoadGraph.h — in-memory lane-level road graph.
//
// Mirrors DATA_CONTRACTS.md §7 (roads/*.parquet) and §15 (runtime/roadgraph.nycb).
// Two ways to populate it:
//   * builder API  (addNode / addSegment / addLane / addJunctionLane / finalize)
//     — used by tests, the synthetic grid and by hosts that assemble graphs
//     from their own data;
//   * loadFromNycb(data, len) — reads the §15 byte layout directly with a
//     self-contained little-endian reader (no dependency on core/io).
//
// Design rules (see docs/verification/traffic/REPORT.md):
//   * no exceptions in the public API — every fallible call returns bool and
//     leaves a message in lastError();
//   * road lanes and junction lanes share ONE index space ("lane index") so
//     the router and the traffic simulation treat "the next lane" uniformly;
//   * all polylines are stored in travel order with cumulative 2-D lengths, so
//     `s` (metres along the lane) is the only longitudinal coordinate anywhere;
//   * nothing here allocates after finalize(); queries write into caller buffers.

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace nycsim {
namespace routing {

using NodeId = int64_t;
using SegmentId = int64_t;
using LaneId = int64_t;

constexpr uint32_t kInvalidIndex = 0xFFFFFFFFu;
constexpr uint16_t kNoNta = 0xFFFFu;

struct Vec3 {
  float x = 0.f, y = 0.f, z = 0.f;
};
struct Vec2 {
  float x = 0.f, y = 0.f;
};

// §7 roads/segments.parquet rw_type
enum class RwType : uint8_t {
  Street = 1, Highway = 2, Bridge = 3, Tunnel = 4, Boardwalk = 5, Path = 6, StepStreet = 7,
  Driveway = 8, Ramp = 9, Alley = 10, Unknown = 11, NonPhysical = 12, UTurn = 13, Ferry = 14
};
// §7 traffic_dir
enum class TrafficDir : uint8_t { TwoWay = 0, Forward = 1, Backward = 2, None = 3 };
// §7 lanes.kind
enum class LaneKind : int8_t { Travel = 0, Parking = 1, Bike = 2, Bus = 3, Turn = 4, Shoulder = 5 };
// §7 junction_lanes.turn
enum class TurnType : uint8_t { Straight = 0, Left = 1, Right = 2, UTurn = 3 };
// §7 nodes.control
enum class Control : uint8_t { None = 0, Signal = 1, Stop = 2, AllWayStop = 3, Yield = 4 };
// §7 bike_lane
enum class BikeLane : uint8_t { None = 0, Protected = 1, Standard = 2, Sharrow = 3, Greenway = 4 };

constexpr uint32_t laneKindBit(LaneKind k) { return 1u << static_cast<unsigned>(static_cast<int8_t>(k)); }
constexpr uint32_t kAllLaneKinds = 0x3Fu;
constexpr uint32_t kMotorLaneKinds = laneKindBit(LaneKind::Travel) | laneKindBit(LaneKind::Turn);
constexpr uint32_t kBusLaneKinds = kMotorLaneKinds | laneKindBit(LaneKind::Bus) | laneKindBit(LaneKind::Parking);
constexpr uint32_t kEmergencyLaneKinds = kMotorLaneKinds | laneKindBit(LaneKind::Bus) | laneKindBit(LaneKind::Shoulder);
constexpr uint32_t kBikeLaneKinds = kMotorLaneKinds | laneKindBit(LaneKind::Bike);

// Segment flags (extension over §7; documented in the report).
constexpr uint32_t kSegCommercial = 1u << 0;  // ground-floor retail frontage → double-parking candidates
constexpr uint32_t kSegBusLane = 1u << 1;     // §7 bus_lane
constexpr uint32_t kSegTruckRoute = 1u << 2;  // §7 truck_route != 0
constexpr uint32_t kSegNoSpawn = 1u << 3;     // host-set: never spawn here (tunnels, ramps, player garage...)

struct SegmentAttrs {
  RwType rw_type = RwType::Street;
  TrafficDir traffic_dir = TrafficDir::TwoWay;
  uint8_t travel_lanes = 1;
  uint8_t park_lanes = 0;
  float width_m = 9.0f;
  uint8_t speed_mph = 25;  // NYC default since 2014 (Vision Zero, Local Law 2014/054)
  BikeLane bike_lane = BikeLane::None;
  uint8_t surface = 0;
  uint8_t borough = 1;
  uint32_t flags = 0;
};

struct Node {
  NodeId id = 0;
  Vec3 pos;
  Control control = Control::None;
  uint8_t signal_source = 0;
  uint32_t first_seg = 0, seg_count = 0;  // incident segments (node_segs_)
  uint32_t first_jl = 0, jl_count = 0;    // junction lanes through this node (node_jls_)
};

struct Segment {
  SegmentId id = 0;
  uint32_t from_node = kInvalidIndex, to_node = kInvalidIndex;
  uint32_t first_vertex = 0, vertex_count = 0;  // seg_vertices_
  SegmentAttrs attrs;
  uint32_t name = 0;  // names_ index
  float length_m = 0.f;
  uint32_t first_lane = 0, lane_count = 0;  // seg_lanes_
};

struct Lane {
  LaneId id = 0;
  uint32_t segment = kInvalidIndex;  // road lanes only
  uint32_t node = kInvalidIndex;     // junction lanes: the intersection node; road lanes: downstream node
  int8_t index_from_center = 0;      // 0 = nearest the centreline (leftmost in travel direction), grows to the curb
  int8_t direction = 1;              // +1 along segment geometry, -1 against
  LaneKind kind = LaneKind::Travel;
  uint8_t is_junction = 0;
  TurnType turn = TurnType::Straight;  // junction lanes
  uint8_t disabled = 0;                // turn restriction / closure
  uint16_t nta = kNoNta;
  int32_t signal_group = -1;  // junction lanes; -1 = not signal-controlled
  float width_m = 3.0f;
  float speed_mps = 11.176f;  // 25 mph
  float length_m = 0.f;
  uint32_t first_vertex = 0, vertex_count = 0;  // vertices_ / cumlen_
  uint32_t first_succ = 0, succ_count = 0;      // succ_
  uint32_t first_pred = 0, pred_count = 0;      // pred_
  uint32_t first_yield = 0, yield_count = 0;    // yield_ (junction lanes)
  uint32_t left = kInvalidIndex, right = kInvalidIndex;  // adjacent same-direction lanes (road lanes)
  uint32_t from_lane = kInvalidIndex, to_lane = kInvalidIndex;  // junction lanes
};

struct LanePose {
  Vec3 pos;
  Vec2 dir;            // unit tangent (x east, y north)
  float heading_rad;   // mathematical: 0 = +x (east), counter-clockwise
  float compass_deg;   // 0 = north, clockwise (DATA_CONTRACTS "_heading" convention)
};

struct NearestLane {
  uint32_t lane = kInvalidIndex;
  float s = 0.f;         // metres along the lane
  float lateral = 0.f;   // signed offset, +left of travel direction
  float distance = 0.f;  // planar distance to the lane centreline
};

class RoadGraph {
 public:
  RoadGraph();

  // ------------------------------------------------------------ builder API
  void clear();
  void reserve(size_t nodes, size_t segments, size_t lanes, size_t junction_lanes, size_t vertices);
  uint32_t addNode(NodeId id, Vec3 pos, Control control, uint8_t signal_source = 0);
  // `pts` are the segment centreline vertices from `from` to `to`.
  uint32_t addSegment(SegmentId id, NodeId from, NodeId to, const Vec3* pts, size_t n, const SegmentAttrs& attrs,
                      std::string_view name);
  // `pts` may be given in either orientation; finalize() orients them in travel
  // order using the segment's node positions.  n == 0 derives the polyline by
  // offsetting the segment centreline (offset = (index_from_center + 0.5) × width
  // to the right of the travel direction, contract §7 lane model).
  uint32_t addLane(LaneId id, SegmentId segment, int8_t index_from_center, int8_t direction, LaneKind kind,
                   float width_m, float speed_mps, const Vec3* pts = nullptr, size_t n = 0);
  // Explicit lane→lane continuation (contract `successors`).  Junction lanes
  // register themselves as successors of `from_lane` automatically.
  void addLaneSuccessor(LaneId lane, LaneId successor);
  // n == 0 → geometry generated (straight line or quadratic Bézier through the node).
  uint32_t addJunctionLane(LaneId id, LaneId from_lane, LaneId to_lane, TurnType turn, int32_t signal_group,
                           const Vec3* pts = nullptr, size_t n = 0, const LaneId* yield_to = nullptr,
                           size_t n_yield = 0);
  // Resolves ids, orients polylines, builds adjacency + spatial index.
  bool finalize();
  // DATA_CONTRACTS §15 runtime/roadgraph.nycb — parses and finalizes.
  bool loadFromNycb(const uint8_t* data, size_t len);

  // Post-finalize mutation (allowed: flags/NTA/closures do not change topology).
  void setSegmentFlags(uint32_t seg, uint32_t flags);
  void setLaneNta(uint32_t lane, uint16_t nta);
  void setLaneDisabled(uint32_t lane, bool disabled);
  // Turn restriction: disables every junction lane from→to. Returns count disabled.
  uint32_t restrictTurn(LaneId from_lane, LaneId to_lane);

  bool finalized() const { return finalized_; }
  const std::string& lastError() const { return error_; }

  // ------------------------------------------------------------- queries
  size_t nodeCount() const { return nodes_.size(); }
  size_t segmentCount() const { return segments_.size(); }
  size_t laneCount() const { return lanes_.size(); }  // road + junction
  size_t roadLaneCount() const { return road_lane_count_; }
  size_t junctionLaneCount() const { return lanes_.size() - road_lane_count_; }
  uint16_t ntaCount() const { return nta_count_; }

  const Node& node(uint32_t i) const { return nodes_[i]; }
  const Segment& segment(uint32_t i) const { return segments_[i]; }
  const Lane& lane(uint32_t i) const { return lanes_[i]; }

  uint32_t nodeIndex(NodeId id) const;
  uint32_t segmentIndex(SegmentId id) const;
  uint32_t laneIndex(LaneId id) const;          // road lanes
  uint32_t junctionLaneIndex(LaneId id) const;  // junction lanes

  std::string_view segmentName(uint32_t seg) const { return names_[segments_[seg].name]; }
  // Junction lanes report the street they lead onto (to_lane's segment).
  std::string_view laneStreetName(uint32_t lane) const;
  uint32_t laneSegment(uint32_t lane) const;  // junction → to_lane's segment

  const uint32_t* successors(uint32_t lane, uint32_t& n) const {
    n = lanes_[lane].succ_count;
    return succ_.data() + lanes_[lane].first_succ;
  }
  const uint32_t* predecessors(uint32_t lane, uint32_t& n) const {
    n = lanes_[lane].pred_count;
    return pred_.data() + lanes_[lane].first_pred;
  }
  const uint32_t* yieldTo(uint32_t lane, uint32_t& n) const {
    n = lanes_[lane].yield_count;
    return yield_.data() + lanes_[lane].first_yield;
  }
  const uint32_t* segmentLanes(uint32_t seg, uint32_t& n) const {
    n = segments_[seg].lane_count;
    return seg_lanes_.data() + segments_[seg].first_lane;
  }
  const uint32_t* nodeJunctionLanes(uint32_t node, uint32_t& n) const {
    n = nodes_[node].jl_count;
    return node_jls_.data() + nodes_[node].first_jl;
  }
  const uint32_t* nodeSegments(uint32_t node, uint32_t& n) const {
    n = nodes_[node].seg_count;
    return node_segs_.data() + nodes_[node].first_seg;
  }
  const Vec3* laneVertices(uint32_t lane, uint32_t& n) const {
    n = lanes_[lane].vertex_count;
    return vertices_.data() + lanes_[lane].first_vertex;
  }
  const float* laneCumulative(uint32_t lane) const { return cumlen_.data() + lanes_[lane].first_vertex; }
  const Vec3* segmentVertices(uint32_t seg, uint32_t& n) const {
    n = segments_[seg].vertex_count;
    return seg_vertices_.data() + segments_[seg].first_vertex;
  }

  LanePose poseAt(uint32_t lane, float s, float lateral = 0.f) const;
  Vec3 pointAt(uint32_t lane, float s) const;
  uint32_t laneStartNode(uint32_t lane) const;
  uint32_t laneEndNode(uint32_t lane) const;
  bool laneAllows(uint32_t lane, uint32_t kinds_mask) const {
    const Lane& l = lanes_[lane];
    return !l.disabled && (laneKindBit(l.kind) & kinds_mask) != 0;
  }
  // The junction lane connecting `from` → `to`, or kInvalidIndex.
  uint32_t junctionBetween(uint32_t from_lane, uint32_t to_lane) const;

  // Nearest road lane (optionally junction lanes too) to a planar point.
  NearestLane nearestLane(float x, float y, uint32_t kinds_mask = kAllLaneKinds, float max_dist = 60.f,
                          bool include_junction = false) const;
  // Project a point onto one lane; false when farther than max_dist from it.
  bool projectOnLane(uint32_t lane, float x, float y, float& s, float& lateral, float& dist,
                     float max_dist = 1e30f) const;
  // Lanes whose polyline comes within `radius` of (x,y).  Writes ≤ cap indices;
  // returns the number found (may exceed cap: caller sees truncation).
  uint32_t lanesNear(float x, float y, float radius, uint32_t* out, uint32_t cap, bool include_junction) const;

  void bounds(float& minx, float& miny, float& maxx, float& maxy) const {
    minx = minx_;
    miny = miny_;
    maxx = maxx_;
    maxy = maxy_;
  }

 private:
  struct PendingSucc {
    LaneId lane, succ;
  };
  struct PendingJunction {
    uint32_t lane_index;
    LaneId from, to;
    uint32_t first_yield, yield_count;  // into pending_yield_ids_
    bool generated_geometry;
  };
  struct GridEntry {
    uint32_t lane, seg;
  };

  bool fail(const char* msg);
  bool buildLaneGeometry();
  bool orientLane(Lane& l, const Segment& seg);
  void computeCumulative(Lane& l);
  bool buildJunctionGeometry(uint32_t lane_index);
  void buildAdjacency();
  void buildNeighbours();
  void buildSpatialIndex();
  void sampleBezier(const Vec3& p0, const Vec3& c, const Vec3& p1, uint32_t count);
  static float segDist2(float px, float py, const Vec3& a, const Vec3& b, float& t);

  std::vector<Node> nodes_;
  std::vector<Segment> segments_;
  std::vector<Lane> lanes_;
  std::vector<Vec3> vertices_;      // lane vertices (travel order)
  std::vector<float> cumlen_;       // parallel to vertices_
  std::vector<Vec3> seg_vertices_;  // segment centrelines
  std::vector<std::string> names_;
  std::vector<uint32_t> succ_, pred_, yield_, seg_lanes_, node_jls_, node_segs_;

  std::unordered_map<NodeId, uint32_t> node_by_id_;
  std::unordered_map<SegmentId, uint32_t> seg_by_id_;
  std::unordered_map<LaneId, uint32_t> lane_by_id_;
  std::unordered_map<LaneId, uint32_t> junction_by_id_;
  std::unordered_map<std::string, uint32_t> name_by_text_;

  // pre-finalize staging
  std::vector<PendingSucc> pending_succ_;
  std::vector<PendingJunction> pending_junctions_;
  std::vector<LaneId> pending_yield_ids_;
  std::vector<NodeId> seg_from_ids_, seg_to_ids_;
  std::vector<SegmentId> lane_seg_ids_;
  std::vector<uint8_t> lane_has_geometry_;

  // spatial index over lane polyline pieces (CSR)
  std::vector<uint32_t> grid_start_;
  std::vector<GridEntry> grid_entries_;
  float grid_minx_ = 0, grid_miny_ = 0, grid_cell_ = 50.f;
  uint32_t grid_nx_ = 1, grid_ny_ = 1;

  float minx_ = 0, miny_ = 0, maxx_ = 0, maxy_ = 0;
  size_t road_lane_count_ = 0;
  uint16_t nta_count_ = 0;
  bool finalized_ = false;
  std::string error_;
};

// Small geometry helpers shared with the traffic and pedestrian modules.
inline float dist2d(const Vec3& a, const Vec3& b) {
  const float dx = a.x - b.x, dy = a.y - b.y;
  return std::sqrt(dx * dx + dy * dy);
}

}  // namespace routing
}  // namespace nycsim
