#pragma once
// nycsim/peds/SidewalkGraph.h — the pedestrian network: sidewalk corridors with
// real widths, crosswalks bound to signal groups, plaza and park-path edges,
// walls, and the points of interest the activity model walks to.
//
// Geometry model.  An edge is a straight corridor of width `width_m` between
// two nodes.  A pedestrian's position is (edge, s along the edge, lateral
// offset); the lateral offset is hard-clamped to ±(width/2 − shoulder), which
// is what makes wall penetration impossible rather than merely unlikely: the
// outer boundary of a sidewalk corridor is the building line and the inner one
// is the curb.  Hosts may additionally register explicit wall segments (a
// construction shed, a plaza planter) which are enforced the same way.
//
// Data sources (DATA_CONTRACTS §7 roads/pavement/{tile}.parquet kind 1
// sidewalk / 3 plaza / 5 crosswalk) once the roads stage produces them; until
// then buildFromRoadGraph() derives a correct network from the lane graph,
// which is what the tests and the benchmark use.

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "nycsim/routing/RoadGraph.h"
#include "nycsim/traffic/Signals.h"

namespace nycsim {
namespace peds {

enum class WalkEdgeKind : uint8_t { Sidewalk = 0, Crosswalk = 1, Plaza = 2, Stair = 3, ParkPath = 4 };

enum class PoiKind : uint8_t {
  Storefront = 0,
  SubwayEntrance = 1,
  BusStop = 2,
  ParkEntrance = 3,
  Landmark = 4,
  Bench = 5,
  Stoop = 6,
  Kerb = 7,  // taxi-hailing spot
  Count
};

struct WalkNode {
  routing::Vec3 pos;
  uint32_t first_edge = 0, edge_count = 0;
  uint16_t nta = routing::kNoNta;
  uint8_t is_corner = 0;
};

struct WalkEdge {
  uint32_t a = routing::kInvalidIndex, b = routing::kInvalidIndex;
  float length_m = 0.f;
  float width_m = 4.0f;
  WalkEdgeKind kind = WalkEdgeKind::Sidewalk;
  // Crosswalks only: the signal plan and the vehicle group whose green phase
  // runs parallel to this crossing (Signals.h: pedestrians parallel to `group`
  // get WALK).  plan == kInvalidIndex ⇒ unsignalized crossing.
  uint32_t signal_plan = routing::kInvalidIndex;
  int32_t signal_group = -1;
  uint32_t road_node = routing::kInvalidIndex;  // intersection node it belongs to
  float dirx = 1.f, diry = 0.f;                 // unit a→b
};

struct WalkPoi {
  routing::Vec3 pos;
  uint32_t edge = routing::kInvalidIndex;
  float s = 0.f;  // metres along that edge
  PoiKind kind = PoiKind::Storefront;
  uint32_t name = 0;
};

struct Wall {
  float x1 = 0.f, y1 = 0.f, x2 = 0.f, y2 = 0.f;
};

struct SidewalkBuildParams {
  float sidewalk_width_m = 4.6f;   // NYC DOT Street Design Manual: 4.6 m (15 ft)
  float min_sidewalk_width_m = 1.8f;  // ADA minimum clear path 1.5 m + furniture
  float crosswalk_width_m = 3.7f;  // NYC standard 12 ft continental crosswalk
  float corner_radius_m = 4.5f;    // curb return
  bool crosswalks = true;
  bool walls_on_building_line = true;
  float poi_spacing_m = 40.f;      // storefront POIs along commercial frontage
  bool bus_stop_pois = true;
};

class SidewalkGraph {
 public:
  void clear();
  void reserve(size_t nodes, size_t edges);
  uint32_t addNode(const routing::Vec3& p, bool corner = false, uint16_t nta = routing::kNoNta);
  uint32_t addEdge(uint32_t a, uint32_t b, float width_m, WalkEdgeKind kind);
  void setCrosswalkSignal(uint32_t edge, uint32_t plan, int32_t group, uint32_t road_node);
  uint32_t addPoi(const routing::Vec3& p, PoiKind kind, std::string_view name);
  void addWall(float x1, float y1, float x2, float y2);
  // Builds adjacency, edge geometry, the POI index and the spatial index.
  bool finalize();
  bool finalized() const { return finalized_; }
  const std::string& lastError() const { return error_; }

  // Derives sidewalks, corners and signalized crosswalks from the lane graph.
  // `signals` may be null (all crossings become unsignalized).
  bool buildFromRoadGraph(const routing::RoadGraph& g, const traffic::SignalTable* signals,
                          const SidewalkBuildParams& p);

  size_t nodeCount() const { return nodes_.size(); }
  size_t edgeCount() const { return edges_.size(); }
  size_t poiCount() const { return pois_.size(); }
  size_t wallCount() const { return walls_.size(); }
  const WalkNode& node(uint32_t i) const { return nodes_[i]; }
  const WalkEdge& edge(uint32_t i) const { return edges_[i]; }
  const WalkPoi& poi(uint32_t i) const { return pois_[i]; }
  const Wall& wall(uint32_t i) const { return walls_[i]; }
  std::string_view poiName(uint32_t i) const {
    return i < names_.size() ? std::string_view(names_[i]) : std::string_view();
  }
  const uint32_t* nodeEdges(uint32_t n, uint32_t& count) const {
    count = nodes_[n].edge_count;
    return node_edges_.data() + nodes_[n].first_edge;
  }
  const uint32_t* poisOfKind(PoiKind k, uint32_t& count) const {
    const uint32_t ki = static_cast<uint32_t>(k);
    count = poi_kind_count_[ki];
    return poi_by_kind_.data() + poi_kind_first_[ki];
  }

  // Points of interest near a position, over a coarse grid built by finalize().
  // The activity model draws a goal from the streamed region rather than from
  // the whole city (ADR-021), which is what keeps the walk-graph A* local: a
  // goal chosen city-wide sends the search across five boroughs.
  //
  // Selecting one uniformly takes two calls — count, then take the n-th — so
  // that no buffer, no allocation and exactly one random draw are involved.
  // Both walk the same cells in the same order, so "the n-th" is stable.
  // `kind == PoiKind::Count` matches any kind.
  uint32_t poiCountNear(float x, float y, float radius, PoiKind kind) const;
  uint32_t poiNthNear(float x, float y, float radius, PoiKind kind, uint32_t n) const;

  // Position of (edge, s, lateral) in world space.
  routing::Vec3 pointOn(uint32_t edge, float s, float lateral) const;
  // Projects a world point onto one edge.
  void projectOnEdge(uint32_t edge, float x, float y, float& s, float& lateral) const;
  // Nearest edge to a point, searching a spatial grid; kInvalidIndex if none
  // within `max_dist`.
  uint32_t nearestEdge(float x, float y, float max_dist, float& s_out, float& lateral_out) const;
  // Walls within `radius` of (x,y); writes at most `cap` indices.
  uint32_t wallsNear(float x, float y, float radius, uint32_t* out, uint32_t cap) const;

  // A* over the walk graph (metres, crosswalks penalized by `cross_penalty_m`).
  // Writes the node sequence, returns the count (0 = no path, > cap = truncated).
  uint32_t path(uint32_t from_node, uint32_t to_node, uint32_t* out, uint32_t cap,
                float cross_penalty_m = 12.f) const;
  uint32_t edgeBetween(uint32_t a, uint32_t b) const;
  uint32_t otherEnd(uint32_t edge, uint32_t n) const {
    return edges_[edge].a == n ? edges_[edge].b : edges_[edge].a;
  }

  void bounds(float& minx, float& miny, float& maxx, float& maxy) const {
    minx = minx_;
    miny = miny_;
    maxx = maxx_;
    maxy = maxy_;
  }

 private:
  struct GridCell {
    uint32_t first, count;
  };
  void buildSpatialIndex();
  void buildPoiIndex();
  // Visits every POI of `kind` whose position lies within `radius` of (x, y),
  // in grid order.  `fn(poi_index)` returns false to stop the walk.
  template <class Fn>
  void forEachPoiNear(float x, float y, float radius, PoiKind kind, Fn&& fn) const {
    if (pgrid_start_.empty() || radius <= 0.f) return;
    const int cx0 = poiCellX(x - radius), cx1 = poiCellX(x + radius);
    const int cy0 = poiCellY(y - radius), cy1 = poiCellY(y + radius);
    const float r2 = radius * radius;
    const bool any_kind = kind == PoiKind::Count;
    for (int cy = cy0; cy <= cy1; ++cy) {
      for (int cx = cx0; cx <= cx1; ++cx) {
        const size_t cell = static_cast<size_t>(cy) * pnx_ + static_cast<size_t>(cx);
        for (uint32_t k = pgrid_start_[cell]; k < pgrid_start_[cell + 1]; ++k) {
          const uint32_t pi = pgrid_items_[k];
          const WalkPoi& poi = pois_[pi];
          if (!any_kind && poi.kind != kind) continue;
          const float dx = poi.pos.x - x, dy = poi.pos.y - y;
          if (dx * dx + dy * dy > r2) continue;
          if (!fn(pi)) return;
        }
      }
    }
  }
  int poiCellX(float x) const {
    const int c = static_cast<int>((x - px0_) / pcell_);
    return c < 0 ? 0 : (c >= static_cast<int>(pnx_) ? static_cast<int>(pnx_) - 1 : c);
  }
  int poiCellY(float y) const {
    const int c = static_cast<int>((y - py0_) / pcell_);
    return c < 0 ? 0 : (c >= static_cast<int>(pny_) ? static_cast<int>(pny_) - 1 : c);
  }
  uint32_t internName(std::string_view s);

  std::vector<WalkNode> nodes_;
  std::vector<WalkEdge> edges_;
  std::vector<WalkPoi> pois_;
  std::vector<Wall> walls_;
  std::vector<std::string> names_;
  std::vector<uint32_t> node_edges_;
  std::vector<uint32_t> poi_by_kind_;
  uint32_t poi_kind_first_[static_cast<uint32_t>(PoiKind::Count)] = {0};
  uint32_t poi_kind_count_[static_cast<uint32_t>(PoiKind::Count)] = {0};

  // uniform grid over edges and over walls
  std::vector<uint32_t> egrid_start_, egrid_items_;
  std::vector<uint32_t> wgrid_start_, wgrid_items_;
  // coarser uniform grid over the points of interest (goal selection)
  std::vector<uint32_t> pgrid_start_, pgrid_items_;
  float px0_ = 0.f, py0_ = 0.f, pcell_ = 100.f;
  uint32_t pnx_ = 1, pny_ = 1;
  float gx0_ = 0.f, gy0_ = 0.f, gcell_ = 25.f;
  uint32_t gnx_ = 1, gny_ = 1;
  float minx_ = 0.f, miny_ = 0.f, maxx_ = 0.f, maxy_ = 0.f;

  // A* scratch (mutable: path() is logically const)
  mutable std::vector<float> gscore_;
  mutable std::vector<uint32_t> came_, stamp_, heap_;
  mutable std::vector<float> heap_key_;
  mutable uint32_t stamp_counter_ = 0;

  std::string error_;
  bool finalized_ = false;
};

}  // namespace peds
}  // namespace nycsim
