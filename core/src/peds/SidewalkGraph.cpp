// nycsim/peds/SidewalkGraph.cpp — see SidewalkGraph.h.
#include "nycsim/peds/SidewalkGraph.h"

#include <algorithm>
#include <cmath>

namespace nycsim {
namespace peds {

using routing::kInvalidIndex;
using routing::Vec3;

namespace {

inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Distance from (px,py) to segment (ax,ay)-(bx,by); `t` is the parameter.
float pointSegDist(float px, float py, float ax, float ay, float bx, float by, float& t) {
  const float dx = bx - ax, dy = by - ay;
  const float len2 = dx * dx + dy * dy;
  t = len2 > 1e-9f ? ((px - ax) * dx + (py - ay) * dy) / len2 : 0.f;
  t = clampf(t, 0.f, 1.f);
  const float cx = ax + t * dx, cy = ay + t * dy;
  return std::sqrt((px - cx) * (px - cx) + (py - cy) * (py - cy));
}

}  // namespace

void SidewalkGraph::clear() {
  nodes_.clear();
  edges_.clear();
  pois_.clear();
  walls_.clear();
  names_.clear();
  node_edges_.clear();
  poi_by_kind_.clear();
  egrid_start_.clear();
  egrid_items_.clear();
  wgrid_start_.clear();
  wgrid_items_.clear();
  for (uint32_t k = 0; k < static_cast<uint32_t>(PoiKind::Count); ++k) {
    poi_kind_first_[k] = 0;
    poi_kind_count_[k] = 0;
  }
  error_.clear();
  finalized_ = false;
}

void SidewalkGraph::reserve(size_t nodes, size_t edges) {
  nodes_.reserve(nodes);
  edges_.reserve(edges);
}

uint32_t SidewalkGraph::addNode(const Vec3& p, bool corner, uint16_t nta) {
  WalkNode n;
  n.pos = p;
  n.is_corner = corner ? 1u : 0u;
  n.nta = nta;
  nodes_.push_back(n);
  finalized_ = false;
  return static_cast<uint32_t>(nodes_.size() - 1);
}

uint32_t SidewalkGraph::addEdge(uint32_t a, uint32_t b, float width_m, WalkEdgeKind kind) {
  if (a >= nodes_.size() || b >= nodes_.size() || a == b) return kInvalidIndex;
  WalkEdge e;
  e.a = a;
  e.b = b;
  e.width_m = width_m > 0.6f ? width_m : 0.6f;
  e.kind = kind;
  const float dx = nodes_[b].pos.x - nodes_[a].pos.x, dy = nodes_[b].pos.y - nodes_[a].pos.y;
  e.length_m = std::sqrt(dx * dx + dy * dy);
  if (e.length_m < 1e-4f) return kInvalidIndex;
  e.dirx = dx / e.length_m;
  e.diry = dy / e.length_m;
  edges_.push_back(e);
  finalized_ = false;
  return static_cast<uint32_t>(edges_.size() - 1);
}

void SidewalkGraph::setCrosswalkSignal(uint32_t edge, uint32_t plan, int32_t group, uint32_t road_node) {
  if (edge >= edges_.size()) return;
  edges_[edge].signal_plan = plan;
  edges_[edge].signal_group = group;
  edges_[edge].road_node = road_node;
}

uint32_t SidewalkGraph::internName(std::string_view s) {
  for (uint32_t i = 0; i < names_.size(); ++i)
    if (names_[i] == s) return i;
  names_.emplace_back(s);
  return static_cast<uint32_t>(names_.size() - 1);
}

uint32_t SidewalkGraph::addPoi(const Vec3& p, PoiKind kind, std::string_view name) {
  WalkPoi poi;
  poi.pos = p;
  poi.kind = kind;
  poi.name = internName(name);
  pois_.push_back(poi);
  finalized_ = false;
  return static_cast<uint32_t>(pois_.size() - 1);
}

void SidewalkGraph::addWall(float x1, float y1, float x2, float y2) {
  walls_.push_back(Wall{x1, y1, x2, y2});
  finalized_ = false;
}

bool SidewalkGraph::finalize() {
  error_.clear();
  if (nodes_.empty() || edges_.empty()) {
    error_ = "sidewalk graph: no nodes or no edges";
    return false;
  }
  // CSR adjacency.
  std::vector<uint32_t> count(nodes_.size() + 1, 0u);
  for (const WalkEdge& e : edges_) {
    ++count[e.a + 1];
    ++count[e.b + 1];
  }
  for (size_t i = 0; i < nodes_.size(); ++i) count[i + 1] += count[i];
  node_edges_.assign(count.back(), 0u);
  std::vector<uint32_t> cur(count.begin(), count.end() - 1);
  for (uint32_t i = 0; i < edges_.size(); ++i) {
    node_edges_[cur[edges_[i].a]++] = i;
    node_edges_[cur[edges_[i].b]++] = i;
  }
  for (size_t i = 0; i < nodes_.size(); ++i) {
    nodes_[i].first_edge = count[i];
    nodes_[i].edge_count = count[i + 1] - count[i];
  }

  // Bounds.
  minx_ = miny_ = 1e30f;
  maxx_ = maxy_ = -1e30f;
  for (const WalkNode& n : nodes_) {
    minx_ = std::min(minx_, n.pos.x);
    miny_ = std::min(miny_, n.pos.y);
    maxx_ = std::max(maxx_, n.pos.x);
    maxy_ = std::max(maxy_, n.pos.y);
  }
  for (const Wall& w : walls_) {
    minx_ = std::min(minx_, std::min(w.x1, w.x2));
    miny_ = std::min(miny_, std::min(w.y1, w.y2));
    maxx_ = std::max(maxx_, std::max(w.x1, w.x2));
    maxy_ = std::max(maxy_, std::max(w.y1, w.y2));
  }

  buildSpatialIndex();

  // Snap POIs onto the nearest edge and bucket them by kind.
  for (WalkPoi& p : pois_) {
    float s = 0.f, lat = 0.f;
    p.edge = nearestEdge(p.pos.x, p.pos.y, 60.f, s, lat);
    p.s = s;
  }
  poi_by_kind_.clear();
  poi_by_kind_.reserve(pois_.size());
  uint32_t acc = 0;
  for (uint32_t k = 0; k < static_cast<uint32_t>(PoiKind::Count); ++k) {
    poi_kind_first_[k] = acc;
    uint32_t n = 0;
    for (uint32_t i = 0; i < pois_.size(); ++i) {
      if (static_cast<uint32_t>(pois_[i].kind) != k) continue;
      if (pois_[i].edge == kInvalidIndex) continue;
      poi_by_kind_.push_back(i);
      ++n;
    }
    poi_kind_count_[k] = n;
    acc += n;
  }

  gscore_.assign(nodes_.size(), 0.f);
  came_.assign(nodes_.size(), kInvalidIndex);
  stamp_.assign(nodes_.size(), 0u);
  stamp_counter_ = 0;
  finalized_ = true;
  return true;
}

void SidewalkGraph::buildSpatialIndex() {
  gcell_ = 25.f;
  gx0_ = minx_ - 5.f;
  gy0_ = miny_ - 5.f;
  gnx_ = std::max(1u, static_cast<uint32_t>((maxx_ - minx_ + 10.f) / gcell_) + 1u);
  gny_ = std::max(1u, static_cast<uint32_t>((maxy_ - miny_ + 10.f) / gcell_) + 1u);
  const size_t nc = static_cast<size_t>(gnx_) * gny_;

  auto cellsFor = [&](float ax, float ay, float bx, float by, int& cx0, int& cy0, int& cx1, int& cy1) {
    cx0 = static_cast<int>((std::min(ax, bx) - gx0_) / gcell_);
    cx1 = static_cast<int>((std::max(ax, bx) - gx0_) / gcell_);
    cy0 = static_cast<int>((std::min(ay, by) - gy0_) / gcell_);
    cy1 = static_cast<int>((std::max(ay, by) - gy0_) / gcell_);
    cx0 = std::clamp(cx0, 0, static_cast<int>(gnx_) - 1);
    cx1 = std::clamp(cx1, 0, static_cast<int>(gnx_) - 1);
    cy0 = std::clamp(cy0, 0, static_cast<int>(gny_) - 1);
    cy1 = std::clamp(cy1, 0, static_cast<int>(gny_) - 1);
  };

  egrid_start_.assign(nc + 1, 0u);
  for (const WalkEdge& e : edges_) {
    int cx0, cy0, cx1, cy1;
    cellsFor(nodes_[e.a].pos.x, nodes_[e.a].pos.y, nodes_[e.b].pos.x, nodes_[e.b].pos.y, cx0, cy0, cx1, cy1);
    for (int cy = cy0; cy <= cy1; ++cy)
      for (int cx = cx0; cx <= cx1; ++cx)
        ++egrid_start_[static_cast<size_t>(cy) * gnx_ + static_cast<size_t>(cx) + 1u];
  }
  for (size_t i = 0; i < nc; ++i) egrid_start_[i + 1] += egrid_start_[i];
  egrid_items_.assign(egrid_start_[nc], 0u);
  {
    std::vector<uint32_t> cur(egrid_start_.begin(), egrid_start_.end() - 1);
    for (uint32_t i = 0; i < edges_.size(); ++i) {
      const WalkEdge& e = edges_[i];
      int cx0, cy0, cx1, cy1;
      cellsFor(nodes_[e.a].pos.x, nodes_[e.a].pos.y, nodes_[e.b].pos.x, nodes_[e.b].pos.y, cx0, cy0, cx1, cy1);
      for (int cy = cy0; cy <= cy1; ++cy)
        for (int cx = cx0; cx <= cx1; ++cx)
          egrid_items_[cur[static_cast<size_t>(cy) * gnx_ + static_cast<size_t>(cx)]++] = i;
    }
  }

  wgrid_start_.assign(nc + 1, 0u);
  for (const Wall& w : walls_) {
    int cx0, cy0, cx1, cy1;
    cellsFor(w.x1, w.y1, w.x2, w.y2, cx0, cy0, cx1, cy1);
    for (int cy = cy0; cy <= cy1; ++cy)
      for (int cx = cx0; cx <= cx1; ++cx)
        ++wgrid_start_[static_cast<size_t>(cy) * gnx_ + static_cast<size_t>(cx) + 1u];
  }
  for (size_t i = 0; i < nc; ++i) wgrid_start_[i + 1] += wgrid_start_[i];
  wgrid_items_.assign(wgrid_start_[nc], 0u);
  {
    std::vector<uint32_t> cur(wgrid_start_.begin(), wgrid_start_.end() - 1);
    for (uint32_t i = 0; i < walls_.size(); ++i) {
      const Wall& w = walls_[i];
      int cx0, cy0, cx1, cy1;
      cellsFor(w.x1, w.y1, w.x2, w.y2, cx0, cy0, cx1, cy1);
      for (int cy = cy0; cy <= cy1; ++cy)
        for (int cx = cx0; cx <= cx1; ++cx)
          wgrid_items_[cur[static_cast<size_t>(cy) * gnx_ + static_cast<size_t>(cx)]++] = i;
    }
  }
}

Vec3 SidewalkGraph::pointOn(uint32_t edge, float s, float lateral) const {
  const WalkEdge& e = edges_[edge];
  const Vec3& a = nodes_[e.a].pos;
  const Vec3& b = nodes_[e.b].pos;
  const float t = e.length_m > 1e-4f ? clampf(s / e.length_m, 0.f, 1.f) : 0.f;
  Vec3 p;
  p.x = a.x + (b.x - a.x) * t - e.diry * lateral;
  p.y = a.y + (b.y - a.y) * t + e.dirx * lateral;
  p.z = a.z + (b.z - a.z) * t;
  return p;
}

void SidewalkGraph::projectOnEdge(uint32_t edge, float x, float y, float& s, float& lateral) const {
  const WalkEdge& e = edges_[edge];
  const Vec3& a = nodes_[e.a].pos;
  const float rx = x - a.x, ry = y - a.y;
  s = rx * e.dirx + ry * e.diry;
  lateral = -rx * e.diry + ry * e.dirx;
}

uint32_t SidewalkGraph::nearestEdge(float x, float y, float max_dist, float& s_out, float& lateral_out) const {
  s_out = 0.f;
  lateral_out = 0.f;
  if (egrid_start_.empty()) return kInvalidIndex;
  int cx = static_cast<int>((x - gx0_) / gcell_);
  int cy = static_cast<int>((y - gy0_) / gcell_);
  const int rings = std::max(1, static_cast<int>(max_dist / gcell_) + 1);
  float best = max_dist;
  uint32_t best_edge = kInvalidIndex;
  for (int r = 0; r <= rings; ++r) {
    bool any = false;
    for (int dy = -r; dy <= r; ++dy) {
      for (int dx = -r; dx <= r; ++dx) {
        if (std::abs(dx) != r && std::abs(dy) != r) continue;
        const int gx = cx + dx, gy = cy + dy;
        if (gx < 0 || gy < 0 || gx >= static_cast<int>(gnx_) || gy >= static_cast<int>(gny_)) continue;
        const size_t cell = static_cast<size_t>(gy) * gnx_ + static_cast<size_t>(gx);
        for (uint32_t k = egrid_start_[cell]; k < egrid_start_[cell + 1]; ++k) {
          any = true;
          const uint32_t ei = egrid_items_[k];
          const WalkEdge& e = edges_[ei];
          float t = 0.f;
          const float d = pointSegDist(x, y, nodes_[e.a].pos.x, nodes_[e.a].pos.y, nodes_[e.b].pos.x,
                                       nodes_[e.b].pos.y, t);
          if (d < best) {
            best = d;
            best_edge = ei;
            s_out = t * e.length_m;
          }
        }
      }
    }
    if (best_edge != kInvalidIndex && static_cast<float>(r) * gcell_ > best) break;
    (void)any;
  }
  if (best_edge != kInvalidIndex) {
    float s = 0.f, lat = 0.f;
    projectOnEdge(best_edge, x, y, s, lat);
    s_out = s;
    lateral_out = lat;
  }
  return best_edge;
}

uint32_t SidewalkGraph::wallsNear(float x, float y, float radius, uint32_t* out, uint32_t cap) const {
  if (wgrid_start_.empty() || cap == 0) return 0;
  int cx0 = static_cast<int>((x - radius - gx0_) / gcell_);
  int cx1 = static_cast<int>((x + radius - gx0_) / gcell_);
  int cy0 = static_cast<int>((y - radius - gy0_) / gcell_);
  int cy1 = static_cast<int>((y + radius - gy0_) / gcell_);
  cx0 = std::clamp(cx0, 0, static_cast<int>(gnx_) - 1);
  cx1 = std::clamp(cx1, 0, static_cast<int>(gnx_) - 1);
  cy0 = std::clamp(cy0, 0, static_cast<int>(gny_) - 1);
  cy1 = std::clamp(cy1, 0, static_cast<int>(gny_) - 1);
  uint32_t n = 0;
  for (int cy = cy0; cy <= cy1; ++cy) {
    for (int cx = cx0; cx <= cx1; ++cx) {
      const size_t cell = static_cast<size_t>(cy) * gnx_ + static_cast<size_t>(cx);
      for (uint32_t k = wgrid_start_[cell]; k < wgrid_start_[cell + 1] && n < cap; ++k) {
        const uint32_t wi = wgrid_items_[k];
        bool dup = false;
        for (uint32_t j = 0; j < n; ++j)
          if (out[j] == wi) {
            dup = true;
            break;
          }
        if (!dup) out[n++] = wi;
      }
    }
  }
  return n;
}

uint32_t SidewalkGraph::edgeBetween(uint32_t a, uint32_t b) const {
  if (a >= nodes_.size()) return kInvalidIndex;
  uint32_t n = 0;
  const uint32_t* es = nodeEdges(a, n);
  for (uint32_t k = 0; k < n; ++k) {
    const WalkEdge& e = edges_[es[k]];
    if ((e.a == a && e.b == b) || (e.b == a && e.a == b)) return es[k];
  }
  return kInvalidIndex;
}

uint32_t SidewalkGraph::path(uint32_t from_node, uint32_t to_node, uint32_t* out, uint32_t cap,
                             float cross_penalty_m) const {
  if (!finalized_ || from_node >= nodes_.size() || to_node >= nodes_.size() || cap == 0) return 0;
  if (from_node == to_node) {
    out[0] = from_node;
    return 1;
  }
  ++stamp_counter_;
  heap_.clear();
  heap_key_.clear();
  auto heuristic = [&](uint32_t n) {
    const float dx = nodes_[n].pos.x - nodes_[to_node].pos.x;
    const float dy = nodes_[n].pos.y - nodes_[to_node].pos.y;
    return std::sqrt(dx * dx + dy * dy);
  };
  auto push = [&](float key, uint32_t n) {
    heap_.push_back(n);
    heap_key_.push_back(key);
    size_t i = heap_.size() - 1;
    while (i > 0) {
      const size_t parent = (i - 1) / 2;
      if (heap_key_[parent] <= heap_key_[i]) break;
      std::swap(heap_key_[parent], heap_key_[i]);
      std::swap(heap_[parent], heap_[i]);
      i = parent;
    }
  };
  auto pop = [&]() {
    const uint32_t top = heap_.front();
    heap_.front() = heap_.back();
    heap_key_.front() = heap_key_.back();
    heap_.pop_back();
    heap_key_.pop_back();
    size_t i = 0;
    for (;;) {
      const size_t l = 2 * i + 1, r = l + 1;
      size_t m = i;
      if (l < heap_.size() && heap_key_[l] < heap_key_[m]) m = l;
      if (r < heap_.size() && heap_key_[r] < heap_key_[m]) m = r;
      if (m == i) break;
      std::swap(heap_key_[m], heap_key_[i]);
      std::swap(heap_[m], heap_[i]);
      i = m;
    }
    return top;
  };

  gscore_[from_node] = 0.f;
  came_[from_node] = kInvalidIndex;
  stamp_[from_node] = stamp_counter_;
  push(heuristic(from_node), from_node);
  bool found = false;
  uint32_t guard = 0;
  const uint32_t limit = static_cast<uint32_t>(nodes_.size()) * 4u + 1024u;
  while (!heap_.empty() && guard++ < limit) {
    const uint32_t u = pop();
    if (u == to_node) {
      found = true;
      break;
    }
    uint32_t n = 0;
    const uint32_t* es = nodeEdges(u, n);
    for (uint32_t k = 0; k < n; ++k) {
      const WalkEdge& e = edges_[es[k]];
      const uint32_t v = e.a == u ? e.b : e.a;
      const float w = e.length_m + (e.kind == WalkEdgeKind::Crosswalk ? cross_penalty_m : 0.f);
      const float g = gscore_[u] + w;
      if (stamp_[v] == stamp_counter_ && gscore_[v] <= g) continue;
      stamp_[v] = stamp_counter_;
      gscore_[v] = g;
      came_[v] = u;
      push(g + heuristic(v), v);
    }
  }
  if (!found) return 0;
  // Unwind.
  uint32_t n = 0;
  uint32_t at = to_node;
  while (at != kInvalidIndex) {
    ++n;
    if (at == from_node) break;
    at = came_[at];
  }
  if (n > cap) return n;  // caller sees the truncation
  uint32_t w = n;
  at = to_node;
  while (at != kInvalidIndex && w > 0) {
    out[--w] = at;
    if (at == from_node) break;
    at = came_[at];
  }
  return n;
}

// ------------------------------------------------------- derive from roads
bool SidewalkGraph::buildFromRoadGraph(const routing::RoadGraph& g, const traffic::SignalTable* signals,
                                       const SidewalkBuildParams& p) {
  clear();
  if (!g.finalized()) {
    error_ = "sidewalk graph: road graph is not finalized";
    return false;
  }
  const size_t nseg = g.segmentCount();
  const size_t nnode = g.nodeCount();
  reserve(nseg * 4 + nnode * 4, nseg * 6);

  // Two sidewalk nodes per (segment endpoint, side).
  // corner_[node * 8 + slot] holds the walk node created for one (segment,side)
  // at that intersection, so crossings can connect the right corners.
  struct Corner {
    uint32_t walk_node;
    uint32_t segment;
    int side;  // -1 right of a→b, +1 left
    float ang;
  };
  std::vector<std::vector<Corner>> corners(nnode);

  // The two widest streets meeting at each node decide how far the crosswalks
  // sit from the node: a crossing must clear the intersection box, and the stop
  // line (TrafficConfig::stop_line_setback_m) sits behind it.
  std::vector<float> half1(nnode, 0.f), half2(nnode, 0.f);
  for (uint32_t si = 0; si < nseg; ++si) {
    const routing::Segment& seg = g.segment(si);
    const float h = seg.attrs.width_m * 0.5f;
    for (uint32_t n : {seg.from_node, seg.to_node}) {
      if (n == kInvalidIndex || n >= nnode) continue;
      if (h > half1[n]) {
        half2[n] = half1[n];
        half1[n] = h;
      } else if (h > half2[n]) {
        half2[n] = h;
      }
    }
  }
  auto crossingSetback = [&](uint32_t node, float own_half) {
    const float other = half1[node] > own_half + 1e-3f ? half1[node] : half2[node];
    return other + 0.3f + p.crosswalk_width_m * 0.5f;
  };

  for (uint32_t si = 0; si < nseg; ++si) {
    const routing::Segment& seg = g.segment(si);
    if (seg.from_node == kInvalidIndex || seg.to_node == kInvalidIndex) continue;
    if (seg.attrs.rw_type == routing::RwType::Highway || seg.attrs.rw_type == routing::RwType::Ramp ||
        seg.attrs.rw_type == routing::RwType::Ferry || seg.attrs.rw_type == routing::RwType::NonPhysical)
      continue;
    const Vec3& a = g.node(seg.from_node).pos;
    const Vec3& b = g.node(seg.to_node).pos;
    const float dx = b.x - a.x, dy = b.y - a.y;
    const float len = std::sqrt(dx * dx + dy * dy);
    if (len < 6.f) continue;
    const float ux = dx / len, uy = dy / len;
    const float half = seg.attrs.width_m * 0.5f;
    const float sw = std::max(p.min_sidewalk_width_m, p.sidewalk_width_m);
    const float off = half + sw * 0.5f;
    const float setback_a =
        std::min(std::max(crossingSetback(seg.from_node, half), p.corner_radius_m), len * 0.4f);
    const float setback_b =
        std::min(std::max(crossingSetback(seg.to_node, half), p.corner_radius_m), len * 0.4f);

    for (int side = -1; side <= 1; side += 2) {
      // side = -1 → right of the a→b direction (normal (uy, -ux))
      const float nx = side < 0 ? uy : -uy;
      const float ny = side < 0 ? -ux : ux;
      Vec3 pa{a.x + ux * setback_a + nx * off, a.y + uy * setback_a + ny * off, a.z};
      Vec3 pb{b.x - ux * setback_b + nx * off, b.y - uy * setback_b + ny * off, b.z};
      const uint32_t na = addNode(pa, true);
      const uint32_t nb = addNode(pb, true);
      const uint32_t e = addEdge(na, nb, sw, WalkEdgeKind::Sidewalk);
      if (e == kInvalidIndex) continue;
      corners[seg.from_node].push_back(Corner{na, si, side, std::atan2(uy, ux)});
      corners[seg.to_node].push_back(Corner{nb, si, side, std::atan2(-uy, -ux)});
      if (p.walls_on_building_line) {
        // The building line runs along the outer edge of the corridor.
        addWall(pa.x + nx * sw * 0.5f, pa.y + ny * sw * 0.5f, pb.x + nx * sw * 0.5f, pb.y + ny * sw * 0.5f);
      }
      // Storefront POIs along commercial frontage.
      if ((seg.attrs.flags & routing::kSegCommercial) != 0 && p.poi_spacing_m > 1.f) {
        const int count = static_cast<int>(len / p.poi_spacing_m);
        for (int k = 1; k <= count; ++k) {
          const float t = static_cast<float>(k) / static_cast<float>(count + 1);
          Vec3 q{pa.x + (pb.x - pa.x) * t, pa.y + (pb.y - pa.y) * t, pa.z};
          addPoi(q, PoiKind::Storefront, g.segmentName(si));
        }
      }
    }
  }

  // Corner-to-corner links and crosswalks at every intersection.
  for (uint32_t ni = 0; ni < nnode; ++ni) {
    std::vector<Corner>& cs = corners[ni];
    if (cs.size() < 2) continue;
    std::sort(cs.begin(), cs.end(), [](const Corner& x, const Corner& y) {
      if (x.ang != y.ang) return x.ang < y.ang;
      if (x.segment != y.segment) return x.segment < y.segment;
      return x.side < y.side;
    });
    // Walk around the intersection: adjacent corners in angular order that
    // belong to different segments are joined by a corner sidewalk; the two
    // corners of the SAME segment are the two ends of its crosswalk.
    for (size_t k = 0; k < cs.size(); ++k) {
      const Corner& c0 = cs[k];
      const Corner& c1 = cs[(k + 1) % cs.size()];
      if (c0.walk_node == c1.walk_node) continue;
      const float sw = std::max(p.min_sidewalk_width_m, p.sidewalk_width_m);
      if (c0.segment != c1.segment) {
        // A corner link is short, and a short edge with a full-width corridor
        // is a wide disc the lateral clamp barely constrains — which is how a
        // pedestrian ends up on the building side of the corner.  Width it by
        // its own length instead.
        if (edgeBetween(c0.walk_node, c1.walk_node) == kInvalidIndex) {
          const float dx = nodes_[c1.walk_node].pos.x - nodes_[c0.walk_node].pos.x;
          const float dy = nodes_[c1.walk_node].pos.y - nodes_[c0.walk_node].pos.y;
          const float link = std::sqrt(dx * dx + dy * dy);
          addEdge(c0.walk_node, c1.walk_node, clampf(link, p.min_sidewalk_width_m, sw),
                  WalkEdgeKind::Sidewalk);
        }
      } else if (p.crosswalks) {
        const uint32_t e = addEdge(c0.walk_node, c1.walk_node, p.crosswalk_width_m, WalkEdgeKind::Crosswalk);
        if (e == kInvalidIndex) continue;
        // Pedestrians crossing segment S walk parallel to the traffic coming
        // from the other streets: use that movement's signal group.
        // Pedestrians crossing street S walk parallel to the traffic on the
        // streets that cross S, so the crossing takes THAT movement's group.
        // Comparing segment ids is not enough: the opposite approach of the
        // same street is a different segment but the same direction, and using
        // its group would put pedestrians in the roadway on its green.
        int32_t group = -1;
        uint32_t plan = kInvalidIndex;
        if (signals != nullptr) {
          plan = signals->planForNode(ni);
          if (plan != kInvalidIndex) {
            const routing::Segment& crossed = g.segment(c0.segment);
            const Vec3& ca = g.node(crossed.from_node).pos;
            const Vec3& cb = g.node(crossed.to_node).pos;
            float sdx = cb.x - ca.x, sdy = cb.y - ca.y;
            const float slen = std::sqrt(sdx * sdx + sdy * sdy);
            if (slen > 1e-4f) {
              sdx /= slen;
              sdy /= slen;
            }
            uint32_t njl = 0;
            const uint32_t* jls = g.nodeJunctionLanes(ni, njl);
            for (uint32_t j = 0; j < njl; ++j) {
              const routing::Lane& jl = g.lane(jls[j]);
              if (jl.signal_group < 0 || jl.from_lane == kInvalidIndex) continue;
              const routing::Lane& from = g.lane(jl.from_lane);
              const routing::LanePose pose = g.poseAt(jl.from_lane, from.length_m);
              if (std::fabs(pose.dir.x * sdx + pose.dir.y * sdy) > 0.7f) continue;  // parallel
              if (group < 0 || jl.signal_group < group) group = jl.signal_group;
            }
          }
        }
        setCrosswalkSignal(e, group >= 0 ? plan : kInvalidIndex, group, ni);
      }
    }
  }

  if (p.bus_stop_pois) {
    // Kerb POIs (taxi hailing) at every corner.
    for (uint32_t n = 0; n < nodes_.size(); ++n)
      if (nodes_[n].is_corner != 0 && (n % 4u) == 0u) addPoi(nodes_[n].pos, PoiKind::Kerb, "kerb");
  }

  if (!finalize()) return false;
  // NTA per walk node from the nearest road lane.
  for (WalkNode& n : nodes_) {
    const routing::NearestLane nl = g.nearestLane(n.pos.x, n.pos.y, routing::kAllLaneKinds, 40.f, false);
    if (nl.lane != kInvalidIndex) n.nta = g.lane(nl.lane).nta;
  }
  return true;
}

}  // namespace peds
}  // namespace nycsim
