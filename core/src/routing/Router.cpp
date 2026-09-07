// nycsim/routing/Router.cpp — see Router.h.
#include "nycsim/routing/Router.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace nycsim {
namespace routing {

namespace {
constexpr float kInf = 1e30f;
constexpr float kPi = 3.14159265358979f;
constexpr float kLaneChangeLowerBound = 0.5f;  // seconds; profiles are clamped to ≥ this
constexpr uint32_t kMaxActiveLandmarks = 4;

inline float wrapAngle(float a) {
  while (a > kPi) a -= 2.f * kPi;
  while (a < -kPi) a += 2.f * kPi;
  return a;
}
}  // namespace

// ------------------------------------------------------------------ CostModel

CostModel::CostModel() {
  // Weekday profile: ratio of free-flow to observed travel time by hour, shaped
  // on NYC DOT Mobility Report CBD average speeds (night ≈ 12 mph, midday
  // ≈ 7–8 mph, PM peak ≈ 7 mph) → multipliers 1.0 … 1.7.  Calibratable.
  static const float wk[24] = {1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.05f, 1.15f, 1.35f, 1.55f, 1.50f, 1.45f, 1.45f,
                               1.45f, 1.45f, 1.50f, 1.55f, 1.60f, 1.70f, 1.55f, 1.35f, 1.20f, 1.10f, 1.05f, 1.00f};
  static const float sat[24] = {1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.05f, 1.10f, 1.15f, 1.25f, 1.30f, 1.35f,
                                1.35f, 1.35f, 1.35f, 1.35f, 1.30f, 1.25f, 1.20f, 1.15f, 1.10f, 1.10f, 1.05f, 1.00f};
  static const float sun[24] = {1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.00f, 1.05f, 1.10f, 1.15f, 1.20f, 1.25f,
                                1.25f, 1.25f, 1.25f, 1.25f, 1.20f, 1.15f, 1.10f, 1.05f, 1.05f, 1.00f, 1.00f, 1.00f};
  for (int h = 0; h < 24; ++h) {
    congestion[0][h] = wk[h];
    congestion[1][h] = sat[h];
    congestion[2][h] = sun[h];
  }
}

float CostModel::congestionAt(float time_of_day_s, uint8_t dow) const {
  int h = static_cast<int>(std::floor(time_of_day_s / 3600.f));
  h = ((h % 24) + 24) % 24;
  const int d = dow > 2 ? 0 : dow;
  return std::max(1.f, congestion[d][h]);
}

// ---------------------------------------------------------------------- Heap

void Router::Heap::push(float key, uint32_t node) {
  a.push_back({key, node});
  size_t i = a.size() - 1;
  while (i > 0) {
    const size_t p = (i - 1) / 2;
    if (a[p].key <= a[i].key) break;
    std::swap(a[p], a[i]);
    i = p;
  }
}

Router::HeapItem Router::Heap::pop() {
  HeapItem top = a.front();
  a.front() = a.back();
  a.pop_back();
  size_t i = 0;
  const size_t n = a.size();
  while (true) {
    const size_t l = 2 * i + 1, r = l + 1;
    size_t m = i;
    if (l < n && a[l].key < a[m].key) m = l;
    if (r < n && a[r].key < a[m].key) m = r;
    if (m == i) break;
    std::swap(a[m], a[i]);
    i = m;
  }
  return top;
}

// -------------------------------------------------------------------- Router

Router::Router() { active_count_ = 0; }

float Router::traverseSeconds(uint32_t v) const {
  const Lane& l = graph_->lane(v);
  return l.length_m / std::max(l.speed_mps, 1.f);
}

float Router::penalty(uint32_t v, const RouteProfile* p, float congestion) const {
  const Lane& l = graph_->lane(v);
  float pen = 0.f;
  const float extra = laneExtraCost(v);
  if (l.is_junction) {
    const float scale = p ? p->turn_penalty_scale : 1.f;
    switch (l.turn) {
      case TurnType::Right: pen += cost_.right_turn_s * scale; break;
      case TurnType::Left:
        pen += cost_.left_turn_s * scale;
        if (l.yield_count > 0) pen += cost_.left_across_traffic_s * congestion;
        break;
      case TurnType::UTurn: pen += cost_.uturn_s * scale; break;
      default: break;
    }
    const Node& node = graph_->node(l.node);
    switch (node.control) {
      case Control::Signal: pen += extra >= 0.f ? extra : cost_.default_signal_delay_s; break;
      case Control::Stop: {
        // Only the minor approach stops: compare travel lanes of the from-segment
        // with the widest approach at the node.
        const Segment& from_seg = graph_->segment(graph_->lane(l.from_lane).segment);
        uint32_t n = 0;
        const uint32_t* segs = graph_->nodeSegments(l.node, n);
        uint8_t max_lanes = 0;
        for (uint32_t i = 0; i < n; ++i) max_lanes = std::max(max_lanes, graph_->segment(segs[i]).attrs.travel_lanes);
        if (from_seg.attrs.travel_lanes < max_lanes) pen += cost_.stop_sign_s;
        if (extra > 0.f) pen += extra;
        break;
      }
      case Control::AllWayStop: pen += cost_.all_way_stop_s + (extra > 0.f ? extra : 0.f); break;
      case Control::Yield: pen += cost_.yield_s + (extra > 0.f ? extra : 0.f); break;
      default: pen += extra > 0.f ? extra : 0.f; break;
    }
  } else if (extra > 0.f) {
    pen += extra;
  }
  if (p && v == p->avoid_lane) pen += p->avoid_penalty_s;
  return pen;
}

float Router::lowerBoundEdge(uint32_t /*u*/, uint32_t v) const { return traverseSeconds(v) + penalty(v, nullptr, 1.f); }

bool Router::edgeAllowed(uint32_t v, const RouteProfile& p) const {
  const Lane& l = graph_->lane(v);
  if (l.disabled || (laneKindBit(l.kind) & p.lane_kinds) == 0) return false;
  const uint32_t seg = graph_->laneSegment(v);
  if (seg == kInvalidIndex) return false;
  switch (graph_->segment(seg).attrs.rw_type) {
    case RwType::Highway: return p.allow_highway;
    case RwType::Bridge: return p.allow_bridge;
    case RwType::Tunnel: return p.allow_tunnel;
    case RwType::NonPhysical:
    case RwType::Ferry: return false;
    default: return true;
  }
}

float Router::edgeCost(uint32_t /*u*/, uint32_t v, const RouteProfile& p, float congestion) const {
  const Lane& l = graph_->lane(v);
  const float speed = std::max(1.f, std::min(l.speed_mps, p.max_speed_mps));
  float t = l.length_m / speed * congestion;
  if (l.kind != LaneKind::Bike && p.non_bike_lane_factor > 1.f) t *= p.non_bike_lane_factor;
  return t + penalty(v, &p, congestion);
}

void Router::setLaneExtraCost(uint32_t lane, float seconds) {
  if (lane < extra_.size()) extra_[lane] = seconds;
}

// ------------------------------------------------------------- preprocessing

void Router::dijkstraLowerBound(uint32_t source, bool reverse, std::vector<float>& dist) {
  const size_t n = graph_->laneCount();
  dist.assign(n, kInf);
  hf_.clear();
  dist[source] = 0.f;
  hf_.push(0.f, source);
  while (!hf_.empty()) {
    const HeapItem it = hf_.pop();
    const uint32_t u = it.node;
    if (it.key > dist[u]) continue;
    uint32_t cnt = 0;
    const uint32_t* adj = reverse ? graph_->predecessors(u, cnt) : graph_->successors(u, cnt);
    for (uint32_t i = 0; i < cnt; ++i) {
      const uint32_t v = adj[i];
      // reverse search: edge is v→u, weight depends on the entered lane u
      const float w = reverse ? lowerBoundEdge(v, u) : lowerBoundEdge(u, v);
      const float nd = dist[u] + w;
      if (nd < dist[v]) {
        dist[v] = nd;
        hf_.push(nd, v);
      }
    }
    const Lane& lu = graph_->lane(u);
    if (!lu.is_junction) {
      const uint32_t nb[2] = {lu.left, lu.right};
      for (uint32_t v : nb) {
        if (v == kInvalidIndex) continue;
        const float nd = dist[u] + kLaneChangeLowerBound;
        if (nd < dist[v]) {
          dist[v] = nd;
          hf_.push(nd, v);
        }
      }
    }
  }
}

void Router::selectLandmarks(uint32_t count, uint64_t seed) {
  const size_t n = graph_->laneCount();
  landmarks_.clear();
  dist_from_.clear();
  dist_to_.clear();
  if (count == 0 || n < 2) return;
  // Farthest-point selection over forward lower-bound distances.
  std::vector<float> min_dist(n, kInf);
  uint64_t z = seed * 0x9E3779B97F4A7C15ull + 1;
  z ^= z >> 33;
  uint32_t start = static_cast<uint32_t>(z % n);
  // The first landmark: farthest reachable lane from a random start.
  dijkstraLowerBound(start, false, scratch_dist_);
  uint32_t best = start;
  float bestd = -1.f;
  for (uint32_t v = 0; v < n; ++v)
    if (scratch_dist_[v] < kInf && scratch_dist_[v] > bestd) {
      bestd = scratch_dist_[v];
      best = v;
    }
  uint32_t next = best;
  for (uint32_t k = 0; k < count; ++k) {
    landmarks_.push_back(next);
    dist_from_.resize(static_cast<size_t>(k + 1) * n);
    dist_to_.resize(static_cast<size_t>(k + 1) * n);
    dijkstraLowerBound(next, false, scratch_dist_);
    std::copy(scratch_dist_.begin(), scratch_dist_.end(), dist_from_.begin() + static_cast<ptrdiff_t>(static_cast<size_t>(k) * n));
    for (uint32_t v = 0; v < n; ++v) min_dist[v] = std::min(min_dist[v], scratch_dist_[v]);
    dijkstraLowerBound(next, true, scratch_dist_);
    std::copy(scratch_dist_.begin(), scratch_dist_.end(), dist_to_.begin() + static_cast<ptrdiff_t>(static_cast<size_t>(k) * n));
    // pick the lane farthest from all chosen landmarks
    bestd = -1.f;
    uint32_t cand = kInvalidIndex;
    for (uint32_t v = 0; v < n; ++v) {
      if (min_dist[v] >= kInf) continue;
      bool is_lm = false;
      for (uint32_t lm : landmarks_)
        if (lm == v) is_lm = true;
      if (!is_lm && min_dist[v] > bestd) {
        bestd = min_dist[v];
        cand = v;
      }
    }
    if (cand == kInvalidIndex) break;
    next = cand;
  }
}

bool Router::attach(const RoadGraph& g, uint32_t landmarks, uint64_t seed) {
  error_.clear();
  if (!g.finalized()) {
    error_ = "router: graph not finalized";
    return false;
  }
  graph_ = &g;
  const size_t n = g.laneCount();
  if (extra_.size() != n) extra_.assign(n, -1.f);
  df_.assign(n, kInf);
  dr_.assign(n, kInf);
  pf_.assign(n, kInvalidIndex);
  pr_.assign(n, kInvalidIndex);
  stamp_f_.assign(n, 0u);
  stamp_r_.assign(n, 0u);
  settled_f_.assign(n, 0u);
  settled_r_.assign(n, 0u);
  touched_.reserve(n);
  hf_.a.reserve(n);
  hr_.a.reserve(n);
  tmp_path_.reserve(1024);
  stamp_ = 0;
  selectLandmarks(landmarks, seed);
  return true;
}

// ---------------------------------------------------------------- potentials

float Router::potentialForward(uint32_t v, uint32_t t) const {
  const size_t n = graph_->laneCount();
  float best = 0.f;
  for (uint32_t i = 0; i < active_count_; ++i) {
    const size_t base = static_cast<size_t>(active_[i]) * n;
    const float dvL = dist_to_[base + v], dtL = dist_to_[base + t];
    if (dvL < kInf && dtL < kInf) best = std::max(best, dvL - dtL);
    const float dLt = dist_from_[base + t], dLv = dist_from_[base + v];
    if (dLt < kInf && dLv < kInf) best = std::max(best, dLt - dLv);
  }
  return best;
}

float Router::potentialReverse(uint32_t v, uint32_t s) const {
  const size_t n = graph_->laneCount();
  float best = 0.f;
  for (uint32_t i = 0; i < active_count_; ++i) {
    const size_t base = static_cast<size_t>(active_[i]) * n;
    const float dLv = dist_from_[base + v], dLs = dist_from_[base + s];
    if (dLv < kInf && dLs < kInf) best = std::max(best, dLv - dLs);
    const float dsL = dist_to_[base + s], dvL = dist_to_[base + v];
    if (dsL < kInf && dvL < kInf) best = std::max(best, dsL - dvL);
  }
  return best;
}

void Router::chooseActiveLandmarks(uint32_t s, uint32_t t) {
  active_count_ = 0;
  const uint32_t L = static_cast<uint32_t>(landmarks_.size());
  if (L == 0) return;
  const size_t n = graph_->laneCount();
  // score = lower bound on dist(s,t) contributed by each landmark
  float scores[64];
  uint32_t order[64];
  const uint32_t Lc = std::min(L, 64u);
  for (uint32_t i = 0; i < Lc; ++i) {
    const size_t base = static_cast<size_t>(i) * n;
    float sc = 0.f;
    if (dist_to_[base + s] < kInf && dist_to_[base + t] < kInf) sc = std::max(sc, dist_to_[base + s] - dist_to_[base + t]);
    if (dist_from_[base + t] < kInf && dist_from_[base + s] < kInf) sc = std::max(sc, dist_from_[base + t] - dist_from_[base + s]);
    scores[i] = sc;
    order[i] = i;
  }
  std::sort(order, order + Lc, [&](uint32_t a, uint32_t b) { return scores[a] > scores[b]; });
  for (uint32_t i = 0; i < Lc && active_count_ < kMaxActiveLandmarks; ++i) active_[active_count_++] = order[i];
}

// -------------------------------------------------------------------- route

bool Router::route(const RouteQuery& q, RouteResult& out) {
  out.clear();
  if (!graph_) {
    error_ = "router: not attached";
    return false;
  }
  const size_t n = graph_->laneCount();
  if (q.from_lane >= n || q.to_lane >= n) {
    error_ = "router: lane index out of range";
    return false;
  }
  RouteProfile prof = q.profile;
  prof.lane_change_cost_s = std::max(prof.lane_change_cost_s, kLaneChangeLowerBound);
  const float cong = cost_.congestionAt(prof.depart_time_s, prof.dow);
  const uint32_t s = q.from_lane, t = q.to_lane;
  const Lane& ls = graph_->lane(s);
  const Lane& lt = graph_->lane(t);
  const float from_s = std::clamp(q.from_s, 0.f, ls.length_m);
  const float to_s = std::clamp(q.to_s, 0.f, lt.length_m);

  auto partialTraverse = [&](const Lane& l, float metres) {
    const float speed = std::max(1.f, std::min(l.speed_mps, prof.max_speed_mps));
    float tt = metres / speed * cong;
    if (l.kind != LaneKind::Bike && prof.non_bike_lane_factor > 1.f) tt *= prof.non_bike_lane_factor;
    return tt;
  };

  // Trivial: same lane, destination ahead.
  if (s == t && from_s <= to_s) {
    out.ok = true;
    out.lanes.push_back(s);
    out.cost_s = out.eta_s = partialTraverse(ls, to_s - from_s);
    out.free_flow_s = (to_s - from_s) / std::max(1.f, ls.speed_mps);
    out.length_m = to_s - from_s;
    if (q.want_instructions) buildInstructions(out.lanes.data(), 1, from_s, to_s, out.instructions);
    if (q.want_polyline) buildPolyline(out.lanes.data(), 1, from_s, to_s, out.polyline);
    return true;
  }

  // stamps
  if (++stamp_ == 0) {
    std::fill(stamp_f_.begin(), stamp_f_.end(), 0u);
    std::fill(stamp_r_.begin(), stamp_r_.end(), 0u);
    stamp_ = 1;
  }
  const uint32_t st = stamp_;
  touched_.clear();
  hf_.clear();
  hr_.clear();
  chooseActiveLandmarks(s, t);
  const bool use_alt = active_count_ > 0;

  auto P = [&](uint32_t v) -> float {
    if (!use_alt) return 0.f;
    return 0.5f * (potentialForward(v, t) - potentialReverse(v, s));
  };
  auto touch = [&](uint32_t v) {
    if (stamp_f_[v] != st && stamp_r_[v] != st) touched_.push_back(v);
  };
  auto setF = [&](uint32_t v, float d, uint32_t parent) {
    touch(v);
    if (stamp_f_[v] != st) {
      stamp_f_[v] = st;
      settled_f_[v] = 0;
      df_[v] = kInf;
    }
    if (d < df_[v]) {
      df_[v] = d;
      pf_[v] = parent;
      return true;
    }
    return false;
  };
  auto setR = [&](uint32_t v, float d, uint32_t parent) {
    touch(v);
    if (stamp_r_[v] != st) {
      stamp_r_[v] = st;
      settled_r_[v] = 0;
      dr_[v] = kInf;
    }
    if (d < dr_[v]) {
      dr_[v] = d;
      pr_[v] = parent;
      return true;
    }
    return false;
  };
  auto hasF = [&](uint32_t v) { return stamp_f_[v] == st && df_[v] < kInf; };
  auto hasR = [&](uint32_t v) { return stamp_r_[v] == st && dr_[v] < kInf; };

  float mu = kInf;
  uint32_t meet = kInvalidIndex;
  auto tryMeet = [&](uint32_t v) {
    if (hasF(v) && hasR(v)) {
      const float c = df_[v] + dr_[v];
      if (c < mu) {
        mu = c;
        meet = v;
      }
    }
  };

  // Initialise forward.
  const float tail_s = partialTraverse(ls, ls.length_m - from_s);
  if (s == t) {
    // destination behind us on the same lane: must loop — seed with successors
    uint32_t cnt = 0;
    const uint32_t* succ = graph_->successors(s, cnt);
    for (uint32_t i = 0; i < cnt; ++i) {
      const uint32_t v = succ[i];
      if (!edgeAllowed(v, prof)) continue;
      const float nd = tail_s + edgeCost(s, v, prof, cong);
      if (setF(v, nd, s)) hf_.push(nd + P(v), v);
    }
    const uint32_t nb[2] = {ls.left, ls.right};
    for (uint32_t v : nb) {
      if (v == kInvalidIndex || !edgeAllowed(v, prof)) continue;
      const float nd = tail_s + prof.lane_change_cost_s;
      if (setF(v, nd, s)) hf_.push(nd + P(v), v);
    }
  } else {
    setF(s, tail_s, kInvalidIndex);
    hf_.push(tail_s + P(s), s);
  }
  setR(t, 0.f, kInvalidIndex);
  hr_.push(0.f - P(t), t);
  tryMeet(t);

  uint32_t settled = 0;
  while (!hf_.empty() && !hr_.empty()) {
    if (hf_.topKey() + hr_.topKey() >= mu) break;
    const bool forward = hf_.topKey() <= hr_.topKey();
    if (forward) {
      const HeapItem it = hf_.pop();
      const uint32_t u = it.node;
      if (stamp_f_[u] != st || settled_f_[u]) continue;
      if (it.key > df_[u] + P(u) + 1e-3f) continue;  // stale entry
      settled_f_[u] = 1;
      ++settled;
      tryMeet(u);
      uint32_t cnt = 0;
      const uint32_t* succ = graph_->successors(u, cnt);
      for (uint32_t i = 0; i < cnt; ++i) {
        const uint32_t v = succ[i];
        if (!edgeAllowed(v, prof)) continue;
        const float nd = df_[u] + edgeCost(u, v, prof, cong);
        if (setF(v, nd, u)) {
          hf_.push(nd + P(v), v);
          tryMeet(v);
        }
      }
      const Lane& lu = graph_->lane(u);
      if (!lu.is_junction) {
        const uint32_t nb[2] = {lu.left, lu.right};
        for (uint32_t v : nb) {
          if (v == kInvalidIndex || !edgeAllowed(v, prof)) continue;
          const float nd = df_[u] + prof.lane_change_cost_s;
          if (setF(v, nd, u)) {
            hf_.push(nd + P(v), v);
            tryMeet(v);
          }
        }
      }
    } else {
      const HeapItem it = hr_.pop();
      const uint32_t u = it.node;
      if (stamp_r_[u] != st || settled_r_[u]) continue;
      if (it.key > dr_[u] - P(u) + 1e-3f) continue;
      settled_r_[u] = 1;
      ++settled;
      tryMeet(u);
      // edges v→u: weight = cost of entering u
      const float w_u = edgeCost(kInvalidIndex, u, prof, cong);
      uint32_t cnt = 0;
      const uint32_t* pred = graph_->predecessors(u, cnt);
      for (uint32_t i = 0; i < cnt; ++i) {
        const uint32_t v = pred[i];
        if (!edgeAllowed(u, prof)) break;  // u itself unusable: nothing enters it
        if (v != s && !edgeAllowed(v, prof)) continue;
        const float nd = dr_[u] + w_u;
        if (setR(v, nd, u)) {
          hr_.push(nd - P(v), v);
          tryMeet(v);
        }
      }
      const Lane& lu = graph_->lane(u);
      if (!lu.is_junction && edgeAllowed(u, prof)) {
        const uint32_t nb[2] = {lu.left, lu.right};
        for (uint32_t v : nb) {
          if (v == kInvalidIndex) continue;
          if (v != s && !edgeAllowed(v, prof)) continue;
          const float nd = dr_[u] + prof.lane_change_cost_s;
          if (setR(v, nd, u)) {
            hr_.push(nd - P(v), v);
            tryMeet(v);
          }
        }
      }
    }
  }
  out.settled = settled;
  if (meet == kInvalidIndex || mu >= kInf) {
    error_ = "router: no route";
    return false;
  }

  // Reconstruct lane sequence.
  tmp_path_.clear();
  for (uint32_t v = meet; v != kInvalidIndex; v = pf_[v]) {
    tmp_path_.push_back(v);
    if (v == s && !(s == t)) break;
    if (tmp_path_.size() > n) break;  // safety
  }
  if (s == t && (tmp_path_.empty() || tmp_path_.back() != s)) tmp_path_.push_back(s);
  std::reverse(tmp_path_.begin(), tmp_path_.end());
  out.lanes.assign(tmp_path_.begin(), tmp_path_.end());
  for (uint32_t v = pr_[meet]; v != kInvalidIndex; v = pr_[v]) {
    out.lanes.push_back(v);
    if (v == t || out.lanes.size() > n) break;
  }
  // Costs: forward counted the whole of t; keep only the driven part.
  const float t_full = edgeCost(kInvalidIndex, t, prof, cong);
  const float t_used = partialTraverse(lt, to_s) + penalty(t, &prof, cong);
  out.cost_s = std::max(0.f, mu - t_full + t_used);
  out.eta_s = out.cost_s;
  // Length / free-flow over the lane sequence (lane-change hops add nothing).
  float len = 0.f, ff = 0.f;
  for (size_t i = 0; i < out.lanes.size(); ++i) {
    const Lane& l = graph_->lane(out.lanes[i]);
    const bool hop = i > 0 && !l.is_junction && !graph_->lane(out.lanes[i - 1]).is_junction &&
                     graph_->lane(out.lanes[i - 1]).segment == l.segment;
    if (hop) continue;
    float m = l.length_m;
    if (i == 0) m -= from_s;
    if (i + 1 == out.lanes.size()) m -= (l.length_m - to_s);
    m = std::max(0.f, m);
    len += m;
    ff += m / std::max(1.f, l.speed_mps);
  }
  out.length_m = len;
  out.free_flow_s = ff;
  out.ok = true;
  if (q.want_instructions) buildInstructions(out.lanes.data(), out.lanes.size(), from_s, to_s, out.instructions);
  if (q.want_polyline) buildPolyline(out.lanes.data(), out.lanes.size(), from_s, to_s, out.polyline);
  return true;
}

NearestLane Router::snap(float x, float y, const RouteProfile& profile, float snap_radius_m) const {
  if (!graph_) return NearestLane{};
  return graph_->nearestLane(x, y, profile.lane_kinds, snap_radius_m, false);
}

bool Router::routePoints(float x0, float y0, float x1, float y1, const RouteProfile& profile, RouteResult& out,
                         float snap_radius_m) {
  out.clear();
  if (!graph_) {
    error_ = "router: not attached";
    return false;
  }
  const NearestLane a = snap(x0, y0, profile, snap_radius_m);
  const NearestLane b = snap(x1, y1, profile, snap_radius_m);
  if (a.lane == kInvalidIndex || b.lane == kInvalidIndex) {
    error_ = "router: no lane within snap radius";
    return false;
  }
  RouteQuery q;
  q.from_lane = a.lane;
  q.from_s = a.s;
  q.to_lane = b.lane;
  q.to_s = b.s;
  q.profile = profile;
  return route(q, out);
}

// ------------------------------------------------------------- instructions

const char* Router::compass8(float heading_rad) {
  // mathematical heading → compass sector
  float deg = 90.f - heading_rad * 180.f / kPi;
  while (deg < 0.f) deg += 360.f;
  while (deg >= 360.f) deg -= 360.f;
  static const char* names[8] = {"north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"};
  const int idx = static_cast<int>((deg + 22.5f) / 45.f) % 8;
  return names[idx];
}

void Router::buildInstructions(const uint32_t* lanes, size_t n, float from_s, float to_s, std::vector<Instruction>& out) const {
  out.clear();
  if (!graph_ || n == 0) return;
  const RoadGraph& g = *graph_;
  char buf[256];

  // Per-lane driven distance (lane-change hops count nothing).
  auto isHop = [&](size_t i) {
    if (i == 0) return false;
    const Lane& a = g.lane(lanes[i - 1]);
    const Lane& b = g.lane(lanes[i]);
    return !a.is_junction && !b.is_junction && a.segment == b.segment;
  };
  auto contrib = [&](size_t i) -> float {
    if (isHop(i)) return 0.f;
    const Lane& l = g.lane(lanes[i]);
    float m = l.length_m;
    if (i == 0) m -= from_s;
    // last driven lane: if the final lane is a hop, the previous one carries to_s
    size_t last = n - 1;
    while (last > 0 && isHop(last)) --last;
    if (i == last) m -= (l.length_m - to_s);
    return std::max(0.f, m);
  };

  const LanePose p0 = g.poseAt(lanes[0], from_s);
  std::string cur_name(g.laneStreetName(lanes[0]));
  {
    Instruction d;
    d.kind = Instruction::Kind::Depart;
    d.lane = lanes[0];
    d.position = p0.pos;
    d.street = cur_name;
    if (cur_name.empty()) std::snprintf(buf, sizeof buf, "Head %s", compass8(p0.heading_rad));
    else std::snprintf(buf, sizeof buf, "Head %s on %s", compass8(p0.heading_rad), cur_name.c_str());
    d.text = buf;
    out.push_back(d);
  }
  auto rwOf = [&](uint32_t lane) {
    const uint32_t seg = g.laneSegment(lane);
    return seg == kInvalidIndex ? RwType::Unknown : g.segment(seg).attrs.rw_type;
  };
  RwType cur_rw = rwOf(lanes[0]);
  float since = contrib(0), cumulative = 0.f;

  for (size_t i = 1; i < n; ++i) {
    const uint32_t li = lanes[i];
    const Lane& l = g.lane(li);
    if (l.is_junction) {
      const uint32_t to = l.to_lane;
      const std::string name_to(g.laneStreetName(to));
      const RwType rw = rwOf(to);
      // heading change
      const Lane& fl = g.lane(l.from_lane);
      const LanePose pin = g.poseAt(l.from_lane, fl.length_m);
      const LanePose pout = g.poseAt(to, 0.f);
      const float dth = wrapAngle(pout.heading_rad - pin.heading_rad);
      const float adeg = std::fabs(dth) * 180.f / kPi;
      Instruction ins;
      ins.lane = li;
      ins.position = g.poseAt(li, 0.f).pos;
      ins.street = name_to;
      bool emit = true;
      const bool same_name = name_to == cur_name;
      const char* onto = same_name ? "to stay on" : "onto";
      if (rw == RwType::Ramp && cur_rw != RwType::Ramp) {
        ins.kind = Instruction::Kind::Ramp;
        std::string target;
        for (size_t j = i + 1; j < n; ++j) {
          const Lane& lj = g.lane(lanes[j]);
          if (lj.is_junction) continue;
          if (rwOf(lanes[j]) != RwType::Ramp) {
            target = std::string(g.laneStreetName(lanes[j]));
            break;
          }
        }
        if (target.empty()) target = name_to;
        if (target.empty()) std::snprintf(buf, sizeof buf, "Take the ramp");
        else std::snprintf(buf, sizeof buf, "Take the ramp to %s", target.c_str());
        ins.street = target;
      } else if (rw == RwType::Bridge && cur_rw != RwType::Bridge && !name_to.empty()) {
        ins.kind = Instruction::Kind::Bridge;
        std::snprintf(buf, sizeof buf, "Continue over %s", name_to.c_str());
      } else if (rw == RwType::Tunnel && cur_rw != RwType::Tunnel && !name_to.empty()) {
        ins.kind = Instruction::Kind::Tunnel;
        std::snprintf(buf, sizeof buf, "Continue through %s", name_to.c_str());
      } else if (l.turn == TurnType::UTurn || adeg > 150.f) {
        ins.kind = Instruction::Kind::UTurn;
        if (name_to.empty()) std::snprintf(buf, sizeof buf, "Make a U-turn");
        else std::snprintf(buf, sizeof buf, "Make a U-turn %s %s", onto, name_to.c_str());
      } else if (l.turn == TurnType::Left || (l.turn == TurnType::Straight && dth > 25.f * kPi / 180.f)) {
        if (adeg < 60.f) {
          ins.kind = Instruction::Kind::SlightLeft;
          std::snprintf(buf, sizeof buf, name_to.empty() ? "Bear left" : "Bear left %s %s", onto, name_to.c_str());
        } else if (adeg < 135.f) {
          ins.kind = Instruction::Kind::TurnLeft;
          std::snprintf(buf, sizeof buf, name_to.empty() ? "Turn left" : "Turn left %s %s", onto, name_to.c_str());
        } else {
          ins.kind = Instruction::Kind::SharpLeft;
          std::snprintf(buf, sizeof buf, name_to.empty() ? "Turn sharply left" : "Turn sharply left %s %s", onto, name_to.c_str());
        }
      } else if (l.turn == TurnType::Right || (l.turn == TurnType::Straight && dth < -25.f * kPi / 180.f)) {
        if (adeg < 60.f) {
          ins.kind = Instruction::Kind::SlightRight;
          std::snprintf(buf, sizeof buf, name_to.empty() ? "Bear right" : "Bear right %s %s", onto, name_to.c_str());
        } else if (adeg < 135.f) {
          ins.kind = Instruction::Kind::TurnRight;
          std::snprintf(buf, sizeof buf, name_to.empty() ? "Turn right" : "Turn right %s %s", onto, name_to.c_str());
        } else {
          ins.kind = Instruction::Kind::SharpRight;
          std::snprintf(buf, sizeof buf, name_to.empty() ? "Turn sharply right" : "Turn sharply right %s %s", onto, name_to.c_str());
        }
      } else if (!same_name && !name_to.empty()) {
        ins.kind = Instruction::Kind::Continue;
        std::snprintf(buf, sizeof buf, "Continue onto %s", name_to.c_str());
      } else {
        emit = false;
      }
      if (emit) {
        ins.text = buf;
        ins.distance_m = since;
        cumulative += since;
        ins.cumulative_m = cumulative;
        since = 0.f;
        out.push_back(ins);
      }
      cur_name = name_to;
      cur_rw = rw;
    }
    since += contrib(i);
  }
  Instruction a;
  a.kind = Instruction::Kind::Arrive;
  a.lane = lanes[n - 1];
  a.position = g.poseAt(lanes[n - 1], to_s).pos;
  a.street = cur_name;
  a.distance_m = since;
  cumulative += since;
  a.cumulative_m = cumulative;
  if (cur_name.empty()) std::snprintf(buf, sizeof buf, "Arrive at your destination");
  else std::snprintf(buf, sizeof buf, "Arrive at your destination on %s", cur_name.c_str());
  a.text = buf;
  out.push_back(a);
}

void Router::buildPolyline(const uint32_t* lanes, size_t n, float from_s, float to_s, std::vector<Vec3>& out) const {
  out.clear();
  if (!graph_ || n == 0) return;
  const RoadGraph& g = *graph_;
  auto push = [&](const Vec3& p) {
    if (!out.empty()) {
      const Vec3& q = out.back();
      const float dx = p.x - q.x, dy = p.y - q.y;
      if (dx * dx + dy * dy < 4.f && !(n == 1)) return;  // ≤ 1 vertex per 2 m
    }
    out.push_back(p);
  };
  for (size_t i = 0; i < n; ++i) {
    const Lane& l = g.lane(lanes[i]);
    if (i > 0) {
      const Lane& prev = g.lane(lanes[i - 1]);
      if (!l.is_junction && !prev.is_junction && prev.segment == l.segment) continue;  // lane-change hop
    }
    const float s0 = i == 0 ? from_s : 0.f;
    const float s1 = i + 1 == n ? to_s : l.length_m;
    uint32_t vc = 0;
    const Vec3* v = g.laneVertices(lanes[i], vc);
    const float* c = g.laneCumulative(lanes[i]);
    push(g.pointAt(lanes[i], s0));
    for (uint32_t k = 0; k < vc; ++k)
      if (c[k] > s0 && c[k] < s1) push(v[k]);
    out.push_back(g.pointAt(lanes[i], s1));
  }
}

}  // namespace routing
}  // namespace nycsim
