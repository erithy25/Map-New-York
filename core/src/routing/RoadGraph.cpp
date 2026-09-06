// nycsim/routing/RoadGraph.cpp — see RoadGraph.h.
#include "nycsim/routing/RoadGraph.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace nycsim {
namespace routing {

namespace {

constexpr float kPi = 3.14159265358979f;

inline float len2d(const Vec3& a, const Vec3& b) {
  const float dx = b.x - a.x, dy = b.y - a.y;
  return std::sqrt(dx * dx + dy * dy);
}

// ----- little-endian field readers (portable, no type punning) -----
inline uint32_t rdU32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) | (static_cast<uint32_t>(p[2]) << 16) |
         (static_cast<uint32_t>(p[3]) << 24);
}
inline uint64_t rdU64(const uint8_t* p) { return static_cast<uint64_t>(rdU32(p)) | (static_cast<uint64_t>(rdU32(p + 4)) << 32); }
inline int64_t rdI64(const uint8_t* p) { return static_cast<int64_t>(rdU64(p)); }
inline int32_t rdI32(const uint8_t* p) { return static_cast<int32_t>(rdU32(p)); }
inline float rdF32(const uint8_t* p) {
  const uint32_t u = rdU32(p);
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
inline int8_t rdI8(const uint8_t* p) { return static_cast<int8_t>(p[0]); }

struct NycbSection {
  const uint8_t* data = nullptr;
  uint64_t size = 0;
  uint32_t element_size = 0;
  uint32_t element_count = 0;
  bool present = false;
};

}  // namespace

RoadGraph::RoadGraph() { names_.emplace_back(""); name_by_text_.emplace("", 0u); }

void RoadGraph::clear() {
  *this = RoadGraph();
}

void RoadGraph::reserve(size_t nodes, size_t segments, size_t lanes, size_t junction_lanes, size_t vertices) {
  nodes_.reserve(nodes);
  segments_.reserve(segments);
  lanes_.reserve(lanes + junction_lanes);
  vertices_.reserve(vertices);
  cumlen_.reserve(vertices);
  seg_vertices_.reserve(vertices);
  pending_junctions_.reserve(junction_lanes);
  lane_seg_ids_.reserve(lanes);
  lane_has_geometry_.reserve(lanes);
}

bool RoadGraph::fail(const char* msg) {
  error_ = msg;
  finalized_ = false;
  return false;
}

uint32_t RoadGraph::addNode(NodeId id, Vec3 pos, Control control, uint8_t signal_source) {
  const uint32_t idx = static_cast<uint32_t>(nodes_.size());
  Node n;
  n.id = id;
  n.pos = pos;
  n.control = control;
  n.signal_source = signal_source;
  nodes_.push_back(n);
  node_by_id_[id] = idx;
  finalized_ = false;
  return idx;
}

uint32_t RoadGraph::addSegment(SegmentId id, NodeId from, NodeId to, const Vec3* pts, size_t n, const SegmentAttrs& attrs,
                               std::string_view name) {
  const uint32_t idx = static_cast<uint32_t>(segments_.size());
  Segment s;
  s.id = id;
  s.attrs = attrs;
  s.first_vertex = static_cast<uint32_t>(seg_vertices_.size());
  s.vertex_count = static_cast<uint32_t>(n);
  float len = 0.f;
  for (size_t i = 0; i < n; ++i) {
    seg_vertices_.push_back(pts[i]);
    if (i > 0) len += len2d(pts[i - 1], pts[i]);
  }
  s.length_m = len;
  std::string key(name);
  auto it = name_by_text_.find(key);
  if (it == name_by_text_.end()) {
    s.name = static_cast<uint32_t>(names_.size());
    names_.push_back(key);
    name_by_text_.emplace(std::move(key), s.name);
  } else {
    s.name = it->second;
  }
  segments_.push_back(s);
  seg_from_ids_.push_back(from);
  seg_to_ids_.push_back(to);
  seg_by_id_[id] = idx;
  finalized_ = false;
  return idx;
}

uint32_t RoadGraph::addLane(LaneId id, SegmentId segment, int8_t index_from_center, int8_t direction, LaneKind kind,
                            float width_m, float speed_mps, const Vec3* pts, size_t n) {
  // Road lanes must all be added before junction lanes (junction lanes are
  // appended after road_lane_count_).  Enforce by refusing once a junction exists.
  if (!pending_junctions_.empty()) {
    error_ = "addLane after addJunctionLane is not allowed";
    return kInvalidIndex;
  }
  const uint32_t idx = static_cast<uint32_t>(lanes_.size());
  Lane l;
  l.id = id;
  l.index_from_center = index_from_center;
  l.direction = direction >= 0 ? 1 : -1;
  l.kind = kind;
  l.width_m = width_m;
  l.speed_mps = speed_mps;
  if (n >= 2) {
    l.first_vertex = static_cast<uint32_t>(vertices_.size());
    l.vertex_count = static_cast<uint32_t>(n);
    for (size_t i = 0; i < n; ++i) vertices_.push_back(pts[i]);
    lane_has_geometry_.push_back(1);
  } else {
    l.first_vertex = kInvalidIndex;
    l.vertex_count = 0;
    lane_has_geometry_.push_back(0);
  }
  lanes_.push_back(l);
  lane_seg_ids_.push_back(segment);
  lane_by_id_[id] = idx;
  road_lane_count_ = lanes_.size();
  finalized_ = false;
  return idx;
}

void RoadGraph::addLaneSuccessor(LaneId lane, LaneId successor) {
  pending_succ_.push_back({lane, successor});
  finalized_ = false;
}

uint32_t RoadGraph::addJunctionLane(LaneId id, LaneId from_lane, LaneId to_lane, TurnType turn, int32_t signal_group,
                                    const Vec3* pts, size_t n, const LaneId* yield_to, size_t n_yield) {
  const uint32_t idx = static_cast<uint32_t>(lanes_.size());
  Lane l;
  l.id = id;
  l.is_junction = 1;
  l.turn = turn;
  l.signal_group = signal_group;
  l.kind = LaneKind::Travel;
  if (n >= 2) {
    l.first_vertex = static_cast<uint32_t>(vertices_.size());
    l.vertex_count = static_cast<uint32_t>(n);
    for (size_t i = 0; i < n; ++i) vertices_.push_back(pts[i]);
  } else {
    l.first_vertex = kInvalidIndex;
    l.vertex_count = 0;
  }
  lanes_.push_back(l);
  PendingJunction pj;
  pj.lane_index = idx;
  pj.from = from_lane;
  pj.to = to_lane;
  pj.first_yield = static_cast<uint32_t>(pending_yield_ids_.size());
  pj.yield_count = static_cast<uint32_t>(n_yield);
  pj.generated_geometry = n < 2;
  for (size_t i = 0; i < n_yield; ++i) pending_yield_ids_.push_back(yield_to[i]);
  pending_junctions_.push_back(pj);
  junction_by_id_[id] = idx;
  finalized_ = false;
  return idx;
}

void RoadGraph::setSegmentFlags(uint32_t seg, uint32_t flags) { segments_[seg].attrs.flags = flags; }
void RoadGraph::setLaneNta(uint32_t lane, uint16_t nta) {
  lanes_[lane].nta = nta;
  if (nta != kNoNta && nta + 1 > nta_count_) nta_count_ = static_cast<uint16_t>(nta + 1);
}
void RoadGraph::setLaneDisabled(uint32_t lane, bool disabled) { lanes_[lane].disabled = disabled ? 1 : 0; }

uint32_t RoadGraph::restrictTurn(LaneId from_lane, LaneId to_lane) {
  const uint32_t f = laneIndex(from_lane), t = laneIndex(to_lane);
  if (f == kInvalidIndex || t == kInvalidIndex) return 0;
  uint32_t n = 0, count = 0;
  const uint32_t* s = successors(f, n);
  for (uint32_t i = 0; i < n; ++i) {
    const Lane& l = lanes_[s[i]];
    if (l.is_junction && l.to_lane == t) {
      lanes_[s[i]].disabled = 1;
      ++count;
    }
  }
  return count;
}

uint32_t RoadGraph::nodeIndex(NodeId id) const {
  auto it = node_by_id_.find(id);
  return it == node_by_id_.end() ? kInvalidIndex : it->second;
}
uint32_t RoadGraph::segmentIndex(SegmentId id) const {
  auto it = seg_by_id_.find(id);
  return it == seg_by_id_.end() ? kInvalidIndex : it->second;
}
uint32_t RoadGraph::laneIndex(LaneId id) const {
  auto it = lane_by_id_.find(id);
  return it == lane_by_id_.end() ? kInvalidIndex : it->second;
}
uint32_t RoadGraph::junctionLaneIndex(LaneId id) const {
  auto it = junction_by_id_.find(id);
  return it == junction_by_id_.end() ? kInvalidIndex : it->second;
}

uint32_t RoadGraph::laneSegment(uint32_t lane) const {
  const Lane& l = lanes_[lane];
  if (!l.is_junction) return l.segment;
  return l.to_lane == kInvalidIndex ? kInvalidIndex : lanes_[l.to_lane].segment;
}

std::string_view RoadGraph::laneStreetName(uint32_t lane) const {
  const uint32_t seg = laneSegment(lane);
  return seg == kInvalidIndex ? std::string_view() : segmentName(seg);
}

uint32_t RoadGraph::laneStartNode(uint32_t lane) const {
  const Lane& l = lanes_[lane];
  if (l.is_junction) return l.node;
  const Segment& s = segments_[l.segment];
  return l.direction > 0 ? s.from_node : s.to_node;
}
uint32_t RoadGraph::laneEndNode(uint32_t lane) const {
  const Lane& l = lanes_[lane];
  if (l.is_junction) return l.node;
  return l.node;
}

uint32_t RoadGraph::junctionBetween(uint32_t from_lane, uint32_t to_lane) const {
  uint32_t n = 0;
  const uint32_t* s = successors(from_lane, n);
  for (uint32_t i = 0; i < n; ++i)
    if (lanes_[s[i]].is_junction && lanes_[s[i]].to_lane == to_lane) return s[i];
  return kInvalidIndex;
}

// ------------------------------------------------------------------ geometry

void RoadGraph::computeCumulative(Lane& l) {
  float acc = 0.f;
  for (uint32_t i = 0; i < l.vertex_count; ++i) {
    if (i > 0) acc += len2d(vertices_[l.first_vertex + i - 1], vertices_[l.first_vertex + i]);
    cumlen_[l.first_vertex + i] = acc;
  }
  l.length_m = acc;
}

bool RoadGraph::orientLane(Lane& l, const Segment& seg) {
  const Vec3& up = l.direction > 0 ? nodes_[seg.from_node].pos : nodes_[seg.to_node].pos;
  const Vec3& a = vertices_[l.first_vertex];
  const Vec3& b = vertices_[l.first_vertex + l.vertex_count - 1];
  if (len2d(a, up) > len2d(b, up)) std::reverse(vertices_.begin() + l.first_vertex, vertices_.begin() + l.first_vertex + l.vertex_count);
  return true;
}

bool RoadGraph::buildLaneGeometry() {
  // Count same-direction lanes per segment for centring one-way roadbeds.
  std::vector<uint8_t> same_dir(segments_.size() * 2, 0);
  for (size_t i = 0; i < road_lane_count_; ++i) {
    const Lane& l = lanes_[i];
    same_dir[l.segment * 2 + (l.direction > 0 ? 0 : 1)]++;
  }
  std::vector<Vec3> tmp;
  for (size_t i = 0; i < road_lane_count_; ++i) {
    Lane& l = lanes_[i];
    const Segment& seg = segments_[l.segment];
    if (lane_has_geometry_[i]) {
      orientLane(l, seg);
      continue;
    }
    if (seg.vertex_count < 2) return fail("segment has fewer than 2 vertices; cannot derive lane geometry");
    // Offset the centreline to the right of the travel direction.
    float offset = (static_cast<float>(l.index_from_center) + 0.5f) * l.width_m;
    if (seg.attrs.traffic_dir != TrafficDir::TwoWay) {
      const uint8_t n_same = same_dir[l.segment * 2 + (l.direction > 0 ? 0 : 1)];
      offset = (static_cast<float>(l.index_from_center) + 0.5f - 0.5f * static_cast<float>(n_same)) * l.width_m;
    }
    tmp.clear();
    const Vec3* sv = seg_vertices_.data() + seg.first_vertex;
    const uint32_t n = seg.vertex_count;
    // Travel-ordered centreline.
    for (uint32_t k = 0; k < n; ++k) tmp.push_back(l.direction > 0 ? sv[k] : sv[n - 1 - k]);
    l.first_vertex = static_cast<uint32_t>(vertices_.size());
    l.vertex_count = n;
    for (uint32_t k = 0; k < n; ++k) {
      // averaged normal
      float tx = 0.f, ty = 0.f;
      if (k > 0) {
        tx += tmp[k].x - tmp[k - 1].x;
        ty += tmp[k].y - tmp[k - 1].y;
      }
      if (k + 1 < n) {
        tx += tmp[k + 1].x - tmp[k].x;
        ty += tmp[k + 1].y - tmp[k].y;
      }
      const float tl = std::sqrt(tx * tx + ty * ty);
      if (tl > 1e-6f) {
        tx /= tl;
        ty /= tl;
      }
      // right normal of (tx,ty) is (ty,-tx)
      Vec3 p = tmp[k];
      p.x += ty * offset;
      p.y += -tx * offset;
      vertices_.push_back(p);
    }
  }
  cumlen_.resize(vertices_.size(), 0.f);
  for (size_t i = 0; i < road_lane_count_; ++i) computeCumulative(lanes_[i]);
  return true;
}

void RoadGraph::sampleBezier(const Vec3& p0, const Vec3& c, const Vec3& p1, uint32_t count) {
  for (uint32_t i = 0; i < count; ++i) {
    const float t = static_cast<float>(i) / static_cast<float>(count - 1);
    const float u = 1.f - t;
    Vec3 p;
    p.x = u * u * p0.x + 2.f * u * t * c.x + t * t * p1.x;
    p.y = u * u * p0.y + 2.f * u * t * c.y + t * t * p1.y;
    p.z = u * u * p0.z + 2.f * u * t * c.z + t * t * p1.z;
    vertices_.push_back(p);
  }
}

bool RoadGraph::buildJunctionGeometry(uint32_t li) {
  Lane& jl = lanes_[li];
  const Lane& from = lanes_[jl.from_lane];
  const Lane& to = lanes_[jl.to_lane];
  const Vec3 p0 = vertices_[from.first_vertex + from.vertex_count - 1];
  const Vec3 p1 = vertices_[to.first_vertex];
  if (jl.vertex_count >= 2) {
    // orient so that the polyline starts at the from-lane end
    const Vec3& a = vertices_[jl.first_vertex];
    const Vec3& b = vertices_[jl.first_vertex + jl.vertex_count - 1];
    if (len2d(a, p0) > len2d(b, p0))
      std::reverse(vertices_.begin() + jl.first_vertex, vertices_.begin() + jl.first_vertex + jl.vertex_count);
    return true;
  }
  // Tangents at the ends.
  const Vec3& pa = vertices_[from.first_vertex + (from.vertex_count >= 2 ? from.vertex_count - 2 : 0)];
  const Vec3& pb = vertices_[to.first_vertex + (to.vertex_count >= 2 ? 1 : 0)];
  float d0x = p0.x - pa.x, d0y = p0.y - pa.y;
  float d1x = pb.x - p1.x, d1y = pb.y - p1.y;
  const float l0 = std::sqrt(d0x * d0x + d0y * d0y), l1 = std::sqrt(d1x * d1x + d1y * d1y);
  const float dist = len2d(p0, p1);
  jl.first_vertex = static_cast<uint32_t>(vertices_.size());
  if (dist < 0.05f) {
    // Degenerate: two coincident points, give it a hair of length.
    vertices_.push_back(p0);
    Vec3 q = p1;
    q.x += 0.05f;
    vertices_.push_back(q);
    jl.vertex_count = 2;
    return true;
  }
  if (l0 < 1e-4f || l1 < 1e-4f || jl.turn == TurnType::Straight) {
    vertices_.push_back(p0);
    vertices_.push_back(p1);
    jl.vertex_count = 2;
    return true;
  }
  d0x /= l0;
  d0y /= l0;
  d1x /= l1;
  d1y /= l1;
  // Control point = intersection of the two tangent lines (fallback: midpoint).
  const float den = d0x * d1y - d0y * d1x;
  Vec3 c;
  if (std::fabs(den) > 1e-4f) {
    const float t = ((p1.x - p0.x) * d1y - (p1.y - p0.y) * d1x) / den;
    c.x = p0.x + d0x * t;
    c.y = p0.y + d0y * t;
    c.z = 0.5f * (p0.z + p1.z);
    // Guard against wild control points on near-parallel tangents.
    if (len2d(c, p0) > 3.f * dist || t < 0.f) {
      c.x = 0.5f * (p0.x + p1.x);
      c.y = 0.5f * (p0.y + p1.y);
    }
  } else {
    c.x = 0.5f * (p0.x + p1.x);
    c.y = 0.5f * (p0.y + p1.y);
    c.z = 0.5f * (p0.z + p1.z);
  }
  const uint32_t samples = jl.turn == TurnType::UTurn ? 12u : 8u;
  sampleBezier(p0, c, p1, samples);
  jl.vertex_count = samples;
  return true;
}

// ---------------------------------------------------------------- adjacency

void RoadGraph::buildAdjacency() {
  const size_t L = lanes_.size();
  std::vector<uint32_t> cnt(L + 1, 0);
  // successors: explicit + junctions + junction→to
  struct Pair {
    uint32_t a, b;
  };
  std::vector<Pair> edges;
  edges.reserve(pending_succ_.size() + pending_junctions_.size() * 2);
  for (const PendingSucc& ps : pending_succ_) {
    const uint32_t a = laneIndex(ps.lane);
    uint32_t b = laneIndex(ps.succ);
    if (b == kInvalidIndex) b = junctionLaneIndex(ps.succ);
    if (a != kInvalidIndex && b != kInvalidIndex && a != b) edges.push_back({a, b});
  }
  for (const PendingJunction& pj : pending_junctions_) {
    const Lane& jl = lanes_[pj.lane_index];
    edges.push_back({jl.from_lane, pj.lane_index});
    edges.push_back({pj.lane_index, jl.to_lane});
  }
  std::sort(edges.begin(), edges.end(), [](const Pair& x, const Pair& y) { return x.a < y.a || (x.a == y.a && x.b < y.b); });
  edges.erase(std::unique(edges.begin(), edges.end(), [](const Pair& x, const Pair& y) { return x.a == y.a && x.b == y.b; }),
              edges.end());
  for (const Pair& e : edges) cnt[e.a + 1]++;
  for (size_t i = 0; i < L; ++i) cnt[i + 1] += cnt[i];
  succ_.assign(edges.size(), 0);
  for (size_t i = 0; i < L; ++i) {
    lanes_[i].first_succ = cnt[i];
    lanes_[i].succ_count = cnt[i + 1] - cnt[i];
  }
  {
    std::vector<uint32_t> cur(cnt.begin(), cnt.end() - 1);
    for (const Pair& e : edges) succ_[cur[e.a]++] = e.b;
  }
  // predecessors
  std::fill(cnt.begin(), cnt.end(), 0u);
  for (const Pair& e : edges) cnt[e.b + 1]++;
  for (size_t i = 0; i < L; ++i) cnt[i + 1] += cnt[i];
  pred_.assign(edges.size(), 0);
  for (size_t i = 0; i < L; ++i) {
    lanes_[i].first_pred = cnt[i];
    lanes_[i].pred_count = cnt[i + 1] - cnt[i];
  }
  {
    std::vector<uint32_t> cur(cnt.begin(), cnt.end() - 1);
    for (const Pair& e : edges) pred_[cur[e.b]++] = e.a;
  }
  // yield lists (junction ids first, then road lane ids)
  yield_.clear();
  for (const PendingJunction& pj : pending_junctions_) {
    Lane& jl = lanes_[pj.lane_index];
    jl.first_yield = static_cast<uint32_t>(yield_.size());
    for (uint32_t k = 0; k < pj.yield_count; ++k) {
      const LaneId yid = pending_yield_ids_[pj.first_yield + k];
      uint32_t y = junctionLaneIndex(yid);
      if (y == kInvalidIndex) y = laneIndex(yid);
      if (y != kInvalidIndex && y != pj.lane_index) yield_.push_back(y);
    }
    jl.yield_count = static_cast<uint32_t>(yield_.size()) - jl.first_yield;
  }
  // segment → lanes
  const size_t S = segments_.size();
  std::vector<uint32_t> sc(S + 1, 0);
  for (size_t i = 0; i < road_lane_count_; ++i) sc[lanes_[i].segment + 1]++;
  for (size_t i = 0; i < S; ++i) sc[i + 1] += sc[i];
  seg_lanes_.assign(road_lane_count_, 0);
  for (size_t i = 0; i < S; ++i) {
    segments_[i].first_lane = sc[i];
    segments_[i].lane_count = sc[i + 1] - sc[i];
  }
  {
    std::vector<uint32_t> cur(sc.begin(), sc.end() - 1);
    for (size_t i = 0; i < road_lane_count_; ++i) seg_lanes_[cur[lanes_[i].segment]++] = static_cast<uint32_t>(i);
  }
  // node → segments, node → junction lanes
  const size_t N = nodes_.size();
  std::vector<uint32_t> nc(N + 1, 0);
  for (const Segment& s : segments_) {
    nc[s.from_node + 1]++;
    if (s.to_node != s.from_node) nc[s.to_node + 1]++;
  }
  for (size_t i = 0; i < N; ++i) nc[i + 1] += nc[i];
  node_segs_.assign(nc[N], 0);
  for (size_t i = 0; i < N; ++i) {
    nodes_[i].first_seg = nc[i];
    nodes_[i].seg_count = nc[i + 1] - nc[i];
  }
  {
    std::vector<uint32_t> cur(nc.begin(), nc.end() - 1);
    for (size_t i = 0; i < S; ++i) {
      node_segs_[cur[segments_[i].from_node]++] = static_cast<uint32_t>(i);
      if (segments_[i].to_node != segments_[i].from_node) node_segs_[cur[segments_[i].to_node]++] = static_cast<uint32_t>(i);
    }
  }
  std::fill(nc.begin(), nc.end(), 0u);
  for (size_t i = road_lane_count_; i < L; ++i) nc[lanes_[i].node + 1]++;
  for (size_t i = 0; i < N; ++i) nc[i + 1] += nc[i];
  node_jls_.assign(nc[N], 0);
  for (size_t i = 0; i < N; ++i) {
    nodes_[i].first_jl = nc[i];
    nodes_[i].jl_count = nc[i + 1] - nc[i];
  }
  {
    std::vector<uint32_t> cur(nc.begin(), nc.end() - 1);
    for (size_t i = road_lane_count_; i < L; ++i) node_jls_[cur[lanes_[i].node]++] = static_cast<uint32_t>(i);
  }
}

void RoadGraph::buildNeighbours() {
  std::vector<uint32_t> group;
  for (size_t si = 0; si < segments_.size(); ++si) {
    for (int dir = -1; dir <= 1; dir += 2) {
      group.clear();
      uint32_t n = 0;
      const uint32_t* ls = segmentLanes(static_cast<uint32_t>(si), n);
      for (uint32_t k = 0; k < n; ++k)
        if (lanes_[ls[k]].direction == dir) group.push_back(ls[k]);
      std::sort(group.begin(), group.end(),
                [this](uint32_t a, uint32_t b) { return lanes_[a].index_from_center < lanes_[b].index_from_center; });
      for (size_t k = 0; k < group.size(); ++k) {
        lanes_[group[k]].left = k > 0 ? group[k - 1] : kInvalidIndex;
        lanes_[group[k]].right = k + 1 < group.size() ? group[k + 1] : kInvalidIndex;
      }
    }
  }
}

void RoadGraph::buildSpatialIndex() {
  minx_ = miny_ = 1e30f;
  maxx_ = maxy_ = -1e30f;
  for (const Vec3& v : vertices_) {
    minx_ = std::min(minx_, v.x);
    miny_ = std::min(miny_, v.y);
    maxx_ = std::max(maxx_, v.x);
    maxy_ = std::max(maxy_, v.y);
  }
  for (const Node& n : nodes_) {
    minx_ = std::min(minx_, n.pos.x);
    miny_ = std::min(miny_, n.pos.y);
    maxx_ = std::max(maxx_, n.pos.x);
    maxy_ = std::max(maxy_, n.pos.y);
  }
  if (minx_ > maxx_) {
    minx_ = miny_ = 0.f;
    maxx_ = maxy_ = 1.f;
  }
  grid_cell_ = 50.f;
  grid_minx_ = minx_ - 1.f;
  grid_miny_ = miny_ - 1.f;
  grid_nx_ = static_cast<uint32_t>((maxx_ - grid_minx_) / grid_cell_) + 2;
  grid_ny_ = static_cast<uint32_t>((maxy_ - grid_miny_) / grid_cell_) + 2;
  const size_t nc = static_cast<size_t>(grid_nx_) * grid_ny_;
  grid_start_.assign(nc + 1, 0u);
  auto cellRange = [this](const Vec3& a, const Vec3& b, int& cx0, int& cy0, int& cx1, int& cy1) {
    cx0 = static_cast<int>((std::min(a.x, b.x) - grid_minx_) / grid_cell_);
    cx1 = static_cast<int>((std::max(a.x, b.x) - grid_minx_) / grid_cell_);
    cy0 = static_cast<int>((std::min(a.y, b.y) - grid_miny_) / grid_cell_);
    cy1 = static_cast<int>((std::max(a.y, b.y) - grid_miny_) / grid_cell_);
    cx0 = std::clamp(cx0, 0, static_cast<int>(grid_nx_) - 1);
    cx1 = std::clamp(cx1, 0, static_cast<int>(grid_nx_) - 1);
    cy0 = std::clamp(cy0, 0, static_cast<int>(grid_ny_) - 1);
    cy1 = std::clamp(cy1, 0, static_cast<int>(grid_ny_) - 1);
  };
  for (size_t li = 0; li < lanes_.size(); ++li) {
    const Lane& l = lanes_[li];
    for (uint32_t k = 0; k + 1 < l.vertex_count; ++k) {
      int cx0, cy0, cx1, cy1;
      cellRange(vertices_[l.first_vertex + k], vertices_[l.first_vertex + k + 1], cx0, cy0, cx1, cy1);
      for (int cy = cy0; cy <= cy1; ++cy)
        for (int cx = cx0; cx <= cx1; ++cx) grid_start_[static_cast<size_t>(cy) * grid_nx_ + static_cast<size_t>(cx) + 1]++;
    }
  }
  for (size_t c = 0; c < nc; ++c) grid_start_[c + 1] += grid_start_[c];
  grid_entries_.assign(grid_start_[nc], GridEntry{0, 0});
  std::vector<uint32_t> cur(grid_start_.begin(), grid_start_.end() - 1);
  for (size_t li = 0; li < lanes_.size(); ++li) {
    const Lane& l = lanes_[li];
    for (uint32_t k = 0; k + 1 < l.vertex_count; ++k) {
      int cx0, cy0, cx1, cy1;
      cellRange(vertices_[l.first_vertex + k], vertices_[l.first_vertex + k + 1], cx0, cy0, cx1, cy1);
      for (int cy = cy0; cy <= cy1; ++cy)
        for (int cx = cx0; cx <= cx1; ++cx)
          grid_entries_[cur[static_cast<size_t>(cy) * grid_nx_ + static_cast<size_t>(cx)]++] = GridEntry{static_cast<uint32_t>(li), k};
    }
  }
}

bool RoadGraph::finalize() {
  error_.clear();
  if (nodes_.empty()) return fail("graph has no nodes");
  // segments → node indices
  for (size_t i = 0; i < segments_.size(); ++i) {
    Segment& s = segments_[i];
    s.from_node = nodeIndex(seg_from_ids_[i]);
    s.to_node = nodeIndex(seg_to_ids_[i]);
    if (s.from_node == kInvalidIndex || s.to_node == kInvalidIndex) return fail("segment references unknown node id");
    if (s.vertex_count < 2) {
      // Synthesize a straight centreline from the node positions.
      s.first_vertex = static_cast<uint32_t>(seg_vertices_.size());
      seg_vertices_.push_back(nodes_[s.from_node].pos);
      seg_vertices_.push_back(nodes_[s.to_node].pos);
      s.vertex_count = 2;
      s.length_m = len2d(nodes_[s.from_node].pos, nodes_[s.to_node].pos);
    }
  }
  // road lanes → segment indices, downstream node
  for (size_t i = 0; i < road_lane_count_; ++i) {
    Lane& l = lanes_[i];
    l.segment = segmentIndex(lane_seg_ids_[i]);
    if (l.segment == kInvalidIndex) return fail("lane references unknown segment id");
    const Segment& s = segments_[l.segment];
    l.node = l.direction > 0 ? s.to_node : s.from_node;
    if (l.vertex_count == 1) return fail("lane polyline with a single vertex");
  }
  if (!buildLaneGeometry()) return false;
  // junction lanes
  for (const PendingJunction& pj : pending_junctions_) {
    Lane& jl = lanes_[pj.lane_index];
    jl.from_lane = laneIndex(pj.from);
    jl.to_lane = laneIndex(pj.to);
    if (jl.from_lane == kInvalidIndex || jl.to_lane == kInvalidIndex) return fail("junction lane references unknown lane id");
    jl.node = lanes_[jl.from_lane].node;
    jl.width_m = lanes_[jl.from_lane].width_m;
    jl.speed_mps = std::min(lanes_[jl.from_lane].speed_mps, lanes_[jl.to_lane].speed_mps);
    if (jl.turn != TurnType::Straight) jl.speed_mps = std::min(jl.speed_mps, jl.turn == TurnType::UTurn ? 3.0f : 6.7f);  // 15 mph turning
    jl.kind = lanes_[jl.to_lane].kind;
    if (!buildJunctionGeometry(pj.lane_index)) return false;
  }
  cumlen_.resize(vertices_.size(), 0.f);
  for (size_t i = road_lane_count_; i < lanes_.size(); ++i) computeCumulative(lanes_[i]);
  buildAdjacency();
  buildNeighbours();
  buildSpatialIndex();
  nta_count_ = 0;
  for (const Lane& l : lanes_)
    if (l.nta != kNoNta && l.nta + 1 > nta_count_) nta_count_ = static_cast<uint16_t>(l.nta + 1);
  finalized_ = true;
  return true;
}

// ------------------------------------------------------------------- queries

LanePose RoadGraph::poseAt(uint32_t lane, float s, float lateral) const {
  const Lane& l = lanes_[lane];
  LanePose out;
  const Vec3* v = vertices_.data() + l.first_vertex;
  const float* c = cumlen_.data() + l.first_vertex;
  const uint32_t n = l.vertex_count;
  if (n == 0) return out;
  if (n == 1) {
    out.pos = v[0];
    out.dir = {1.f, 0.f};
    out.heading_rad = 0.f;
    out.compass_deg = 90.f;
    return out;
  }
  if (s < 0.f) s = 0.f;
  if (s > l.length_m) s = l.length_m;
  // upper_bound on cumulative lengths
  uint32_t lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const uint32_t mid = (lo + hi) / 2;
    if (c[mid] <= s) lo = mid;
    else hi = mid;
  }
  const float seg_len = c[hi] - c[lo];
  const float t = seg_len > 1e-6f ? (s - c[lo]) / seg_len : 0.f;
  float dx = v[hi].x - v[lo].x, dy = v[hi].y - v[lo].y;
  const float dl = std::sqrt(dx * dx + dy * dy);
  if (dl > 1e-6f) {
    dx /= dl;
    dy /= dl;
  } else {
    dx = 1.f;
    dy = 0.f;
  }
  out.pos.x = v[lo].x + (v[hi].x - v[lo].x) * t - dy * lateral;
  out.pos.y = v[lo].y + (v[hi].y - v[lo].y) * t + dx * lateral;
  out.pos.z = v[lo].z + (v[hi].z - v[lo].z) * t;
  out.dir = {dx, dy};
  out.heading_rad = std::atan2(dy, dx);
  float compass = 90.f - out.heading_rad * 180.f / kPi;
  while (compass < 0.f) compass += 360.f;
  while (compass >= 360.f) compass -= 360.f;
  out.compass_deg = compass;
  return out;
}

Vec3 RoadGraph::pointAt(uint32_t lane, float s) const { return poseAt(lane, s, 0.f).pos; }

float RoadGraph::segDist2(float px, float py, const Vec3& a, const Vec3& b, float& t) {
  const float dx = b.x - a.x, dy = b.y - a.y;
  const float l2 = dx * dx + dy * dy;
  t = l2 > 1e-9f ? ((px - a.x) * dx + (py - a.y) * dy) / l2 : 0.f;
  t = std::clamp(t, 0.f, 1.f);
  const float qx = a.x + dx * t - px, qy = a.y + dy * t - py;
  return qx * qx + qy * qy;
}

bool RoadGraph::projectOnLane(uint32_t lane, float x, float y, float& s, float& lateral, float& dist, float max_dist) const {
  const Lane& l = lanes_[lane];
  const Vec3* v = vertices_.data() + l.first_vertex;
  const float* c = cumlen_.data() + l.first_vertex;
  float best = 1e30f, best_s = 0.f, best_lat = 0.f;
  for (uint32_t k = 0; k + 1 < l.vertex_count; ++k) {
    float t;
    const float d2 = segDist2(x, y, v[k], v[k + 1], t);
    if (d2 < best) {
      best = d2;
      best_s = c[k] + (c[k + 1] - c[k]) * t;
      const float dx = v[k + 1].x - v[k].x, dy = v[k + 1].y - v[k].y;
      const float cross = dx * (y - v[k].y) - dy * (x - v[k].x);
      best_lat = cross >= 0.f ? std::sqrt(d2) : -std::sqrt(d2);
    }
  }
  if (best >= 1e29f) return false;
  dist = std::sqrt(best);
  if (dist > max_dist) return false;
  s = best_s;
  lateral = best_lat;
  return true;
}

NearestLane RoadGraph::nearestLane(float x, float y, uint32_t kinds_mask, float max_dist, bool include_junction) const {
  NearestLane out;
  if (!finalized_) return out;
  const int cx = static_cast<int>((x - grid_minx_) / grid_cell_);
  const int cy = static_cast<int>((y - grid_miny_) / grid_cell_);
  float best2 = max_dist * max_dist;
  const int max_r = static_cast<int>(max_dist / grid_cell_) + 1;
  for (int r = 0; r <= max_r; ++r) {
    // once the ring distance exceeds the best found, stop
    if (r > 0) {
      const float ring_min = (static_cast<float>(r) - 1.f) * grid_cell_;
      if (ring_min * ring_min > best2) break;
    }
    for (int dy = -r; dy <= r; ++dy) {
      for (int dx = -r; dx <= r; ++dx) {
        if (std::abs(dx) != r && std::abs(dy) != r) continue;  // ring only
        const int gx = cx + dx, gy = cy + dy;
        if (gx < 0 || gy < 0 || gx >= static_cast<int>(grid_nx_) || gy >= static_cast<int>(grid_ny_)) continue;
        const size_t cell = static_cast<size_t>(gy) * grid_nx_ + static_cast<size_t>(gx);
        for (uint32_t e = grid_start_[cell]; e < grid_start_[cell + 1]; ++e) {
          const GridEntry& ge = grid_entries_[e];
          const Lane& l = lanes_[ge.lane];
          if (l.is_junction && !include_junction) continue;
          if (l.disabled || (laneKindBit(l.kind) & kinds_mask) == 0) continue;
          const Vec3& a = vertices_[l.first_vertex + ge.seg];
          const Vec3& b = vertices_[l.first_vertex + ge.seg + 1];
          float t;
          const float d2 = segDist2(x, y, a, b, t);
          if (d2 < best2) {
            best2 = d2;
            out.lane = ge.lane;
            const float* c = cumlen_.data() + l.first_vertex;
            out.s = c[ge.seg] + (c[ge.seg + 1] - c[ge.seg]) * t;
            const float ddx = b.x - a.x, ddy = b.y - a.y;
            const float cross = ddx * (y - a.y) - ddy * (x - a.x);
            out.distance = std::sqrt(d2);
            out.lateral = cross >= 0.f ? out.distance : -out.distance;
          }
        }
      }
    }
  }
  return out;
}

uint32_t RoadGraph::lanesNear(float x, float y, float radius, uint32_t* out, uint32_t cap, bool include_junction) const {
  if (!finalized_) return 0;
  int cx0 = static_cast<int>((x - radius - grid_minx_) / grid_cell_);
  int cy0 = static_cast<int>((y - radius - grid_miny_) / grid_cell_);
  int cx1 = static_cast<int>((x + radius - grid_minx_) / grid_cell_);
  int cy1 = static_cast<int>((y + radius - grid_miny_) / grid_cell_);
  cx0 = std::clamp(cx0, 0, static_cast<int>(grid_nx_) - 1);
  cx1 = std::clamp(cx1, 0, static_cast<int>(grid_nx_) - 1);
  cy0 = std::clamp(cy0, 0, static_cast<int>(grid_ny_) - 1);
  cy1 = std::clamp(cy1, 0, static_cast<int>(grid_ny_) - 1);
  const float r2 = radius * radius;
  uint32_t found = 0;
  for (int cy = cy0; cy <= cy1; ++cy) {
    for (int cx = cx0; cx <= cx1; ++cx) {
      const size_t cell = static_cast<size_t>(cy) * grid_nx_ + static_cast<size_t>(cx);
      for (uint32_t e = grid_start_[cell]; e < grid_start_[cell + 1]; ++e) {
        const GridEntry& ge = grid_entries_[e];
        const Lane& l = lanes_[ge.lane];
        if (l.is_junction && !include_junction) continue;
        float t;
        const float d2 = segDist2(x, y, vertices_[l.first_vertex + ge.seg], vertices_[l.first_vertex + ge.seg + 1], t);
        if (d2 > r2) continue;
        // de-duplicate against what we already wrote (small caps → linear scan)
        bool dup = false;
        for (uint32_t k = 0; k < std::min(found, cap); ++k)
          if (out[k] == ge.lane) {
            dup = true;
            break;
          }
        if (dup) continue;
        if (found < cap) out[found] = ge.lane;
        ++found;
      }
    }
  }
  return found;
}

// --------------------------------------------------------------- NYCB reader

bool RoadGraph::loadFromNycb(const uint8_t* data, size_t len) {
  clear();
  if (data == nullptr || len < 24) return fail("nycb: buffer too small for header");
  if (std::memcmp(data, "NYCB", 4) != 0) return fail("nycb: bad magic");
  const uint32_t version = rdU32(data + 4);
  if (version != 1) return fail("nycb: unsupported version");
  const uint32_t section_count = rdU32(data + 8);
  const uint64_t index_offset = rdU64(data + 16);  // 24-byte header: 4 bytes of padding after section_count
  if (section_count > 64) return fail("nycb: implausible section count");
  const uint64_t index_size = static_cast<uint64_t>(section_count) * 40u;
  if (index_offset > len || index_size > len - index_offset) return fail("nycb: section index out of bounds");

  NycbSection nodes, segments, vertices, lanes, lane_links, junction_lanes, yield_links, strtab;
  for (uint32_t i = 0; i < section_count; ++i) {
    const uint8_t* e = data + index_offset + static_cast<size_t>(i) * 40u;
    char name[17];
    std::memcpy(name, e, 16);
    name[16] = '\0';
    NycbSection s;
    const uint64_t off = rdU64(e + 16);
    s.size = rdU64(e + 24);
    s.element_size = rdU32(e + 32);
    s.element_count = rdU32(e + 36);
    if (off > len || s.size > len - off) return fail("nycb: section out of bounds");
    if (static_cast<uint64_t>(s.element_size) * s.element_count > s.size) return fail("nycb: section element extent exceeds size");
    s.data = data + off;
    s.present = true;
    if (std::strcmp(name, "nodes") == 0) nodes = s;
    else if (std::strcmp(name, "segments") == 0) segments = s;
    else if (std::strcmp(name, "vertices") == 0) vertices = s;
    else if (std::strcmp(name, "lanes") == 0) lanes = s;
    else if (std::strcmp(name, "lane_links") == 0) lane_links = s;
    else if (std::strcmp(name, "junction_lanes") == 0) junction_lanes = s;
    else if (std::strcmp(name, "yield_links") == 0) yield_links = s;
    else if (std::strcmp(name, "strtab") == 0) strtab = s;
  }
  if (!nodes.present || !segments.present || !vertices.present || !lanes.present) return fail("nycb: missing required section");
  if (nodes.element_size != 24) return fail("nycb: nodes element_size != 24");
  if (segments.element_size != 48) return fail("nycb: segments element_size != 48");
  if (vertices.element_size != 12) return fail("nycb: vertices element_size != 12");
  if (lanes.element_size != 48) return fail("nycb: lanes element_size != 48");
  if (lane_links.present && lane_links.element_size != 8) return fail("nycb: lane_links element_size != 8");
  if (junction_lanes.present && junction_lanes.element_size != 48) return fail("nycb: junction_lanes element_size != 48");
  if (yield_links.present && yield_links.element_size != 8) return fail("nycb: yield_links element_size != 8");

  auto str = [&](uint32_t off) -> std::string_view {
    if (!strtab.present || off >= strtab.size) return std::string_view();
    const char* p = reinterpret_cast<const char*>(strtab.data) + off;
    size_t n = 0;
    while (off + n < strtab.size && p[n] != '\0') ++n;
    return std::string_view(p, n);
  };
  auto vert = [&](uint32_t i) {
    const uint8_t* p = vertices.data + static_cast<size_t>(i) * 12u;
    return Vec3{rdF32(p), rdF32(p + 4), rdF32(p + 8)};
  };
  auto vertRangeOk = [&](uint32_t first, uint32_t count) {
    return static_cast<uint64_t>(first) + count <= vertices.element_count;
  };

  reserve(nodes.element_count, segments.element_count, lanes.element_count,
          junction_lanes.present ? junction_lanes.element_count : 0, vertices.element_count * 2);

  for (uint32_t i = 0; i < nodes.element_count; ++i) {
    const uint8_t* p = nodes.data + static_cast<size_t>(i) * 24u;
    const uint8_t control = p[20];
    addNode(rdI64(p), Vec3{rdF32(p + 8), rdF32(p + 12), rdF32(p + 16)},
            control <= 4 ? static_cast<Control>(control) : Control::None, p[21]);
  }
  std::vector<Vec3> pts;
  for (uint32_t i = 0; i < segments.element_count; ++i) {
    const uint8_t* p = segments.data + static_cast<size_t>(i) * 48u;
    const uint32_t fv = rdU32(p + 24), vc = rdU32(p + 28);
    if (!vertRangeOk(fv, vc)) return fail("nycb: segment vertex range out of bounds");
    pts.clear();
    for (uint32_t k = 0; k < vc; ++k) pts.push_back(vert(fv + k));
    SegmentAttrs a;
    const uint8_t rw = p[32];
    a.rw_type = (rw >= 1 && rw <= 14) ? static_cast<RwType>(rw) : RwType::Unknown;
    const uint8_t td = p[33];
    a.traffic_dir = td <= 3 ? static_cast<TrafficDir>(td) : TrafficDir::TwoWay;
    a.travel_lanes = p[34];
    a.park_lanes = p[35];
    a.width_m = rdF32(p + 36);
    a.speed_mph = p[40];
    a.bike_lane = p[41] <= 4 ? static_cast<BikeLane>(p[41]) : BikeLane::None;
    a.surface = p[42];
    a.borough = p[43];
    addSegment(rdI64(p), rdI64(p + 8), rdI64(p + 16), pts.data(), pts.size(), a, str(rdU32(p + 44)));
  }
  struct LaneLinkRange {
    uint32_t first, count;
  };
  std::vector<LaneLinkRange> link_ranges(lanes.element_count);
  for (uint32_t i = 0; i < lanes.element_count; ++i) {
    const uint8_t* p = lanes.data + static_cast<size_t>(i) * 48u;
    const uint32_t fv = rdU32(p + 28), vc = rdU32(p + 32);
    if (!vertRangeOk(fv, vc)) return fail("nycb: lane vertex range out of bounds");
    pts.clear();
    for (uint32_t k = 0; k < vc; ++k) pts.push_back(vert(fv + k));
    const int8_t kind = rdI8(p + 18);
    addLane(rdI64(p), rdI64(p + 8), rdI8(p + 16), rdI8(p + 17), (kind >= 0 && kind <= 5) ? static_cast<LaneKind>(kind) : LaneKind::Travel,
            rdF32(p + 20), rdF32(p + 24), pts.data(), pts.size());
    link_ranges[i] = {rdU32(p + 36), rdU32(p + 40)};
  }
  if (lane_links.present) {
    for (uint32_t i = 0; i < lanes.element_count; ++i) {
      const LaneLinkRange& r = link_ranges[i];
      if (static_cast<uint64_t>(r.first) + r.count > lane_links.element_count) return fail("nycb: lane_links range out of bounds");
      for (uint32_t k = 0; k < r.count; ++k)
        addLaneSuccessor(lanes_[i].id, rdI64(lane_links.data + static_cast<size_t>(r.first + k) * 8u));
    }
  }
  if (junction_lanes.present) {
    std::vector<LaneId> yields;
    for (uint32_t i = 0; i < junction_lanes.element_count; ++i) {
      const uint8_t* p = junction_lanes.data + static_cast<size_t>(i) * 48u;
      const uint32_t fv = rdU32(p + 32), vc = rdU32(p + 36);
      if (!vertRangeOk(fv, vc)) return fail("nycb: junction lane vertex range out of bounds");
      pts.clear();
      for (uint32_t k = 0; k < vc; ++k) pts.push_back(vert(fv + k));
      const uint32_t fy = rdU32(p + 40), yc = rdU32(p + 44);
      yields.clear();
      if (yc > 0) {
        if (!yield_links.present || static_cast<uint64_t>(fy) + yc > yield_links.element_count)
          return fail("nycb: yield_links range out of bounds");
        for (uint32_t k = 0; k < yc; ++k) yields.push_back(rdI64(yield_links.data + static_cast<size_t>(fy + k) * 8u));
      }
      const uint8_t turn = p[24];
      addJunctionLane(rdI64(p), rdI64(p + 8), rdI64(p + 16), turn <= 3 ? static_cast<TurnType>(turn) : TurnType::Straight,
                      rdI32(p + 28), pts.data(), pts.size(), yields.data(), yields.size());
    }
  }
  return finalize();
}

}  // namespace routing
}  // namespace nycsim
