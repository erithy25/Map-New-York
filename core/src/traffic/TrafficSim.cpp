// nycsim/traffic/TrafficSim.cpp — see TrafficSim.h.
//
// Step order (fixed 20 Hz):
//   1. clocks, signal cache, per-step index (agents sorted by lane and s),
//      spatial hash, player lane projection, emergency-vehicle list;
//   2. decide()   — reads only state from step n, writes new_accel_/new_lane_/
//                   new_swerve_/new_flags_;
//   3. integrate() — applies the decisions, advances along the path, hard
//                   stop-line barrier, pose update;
//   4. spawn / despawn against the density target and the player ring;
//   5. statistics.
#include "nycsim/traffic/TrafficSim.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace nycsim {
namespace traffic {

using routing::kInvalidIndex;
using routing::Lane;
using routing::LaneKind;
using routing::TurnType;
using routing::Vec3;

namespace {

constexpr uint32_t kClaimsPerNode = 8;
constexpr float kBigDistance = 1.0e9f;
// Lateral acceleration budget on intersection turns (AASHTO Green Book gives
// 15 mph / 6.7 m/s as the design turning speed for a 25 ft corner radius; with
// R ≈ 9 m that is a_lat ≈ 1.5 m/s² for cars).
constexpr float kTurnLatAccel = 1.5f;

inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
inline float fz(size_t v) { return static_cast<float>(v); }

// Packed sort key: 24 bits lane | 24 bits (s × 4) | 16 bits agent index.
inline uint64_t packKey(uint32_t lane, float s, uint32_t idx) {
  const float sq = s < 0.f ? 0.f : s * 4.f;
  uint32_t q = sq > 16777215.f ? 16777215u : static_cast<uint32_t>(sq);
  return (static_cast<uint64_t>(lane) << 40) | (static_cast<uint64_t>(q) << 16) | static_cast<uint64_t>(idx & 0xFFFFu);
}
inline uint32_t keyIndex(uint64_t k) { return static_cast<uint32_t>(k & 0xFFFFu); }
inline float keyS(uint64_t k) { return static_cast<float>((k >> 16) & 0xFFFFFFull) * 0.25f; }

// Proper intersection of two 2-D segments; returns the parameters along each.
bool segIntersect(const Vec3& p1, const Vec3& p2, const Vec3& q1, const Vec3& q2, float& t, float& u) {
  const float rx = p2.x - p1.x, ry = p2.y - p1.y;
  const float sx = q2.x - q1.x, sy = q2.y - q1.y;
  const float denom = rx * sy - ry * sx;
  if (std::fabs(denom) < 1e-9f) return false;
  const float qpx = q1.x - p1.x, qpy = q1.y - p1.y;
  t = (qpx * sy - qpy * sx) / denom;
  u = (qpx * ry - qpy * rx) / denom;
  return t >= 0.f && t <= 1.f && u >= 0.f && u <= 1.f;
}

}  // namespace

TrafficSim::TrafficSim() { honks_.resize(128); }

// ---------------------------------------------------------------- configure
bool TrafficSim::configure(const routing::RoadGraph& g, const SignalTable& sig, const TrafficConfig& cfg,
                           uint64_t seed) {
  error_.clear();
  if (!g.finalized()) {
    error_ = "TrafficSim: road graph is not finalized";
    return false;
  }
  if (g.laneCount() == 0) {
    error_ = "TrafficSim: road graph has no lanes";
    return false;
  }
  if (g.laneCount() >= (1u << 24)) {
    error_ = "TrafficSim: more than 2^24 lanes is not supported by the step index";
    return false;
  }
  graph_ = &g;
  signals_ = &sig;
  cfg_ = cfg;
  if (cfg_.max_vehicles > 65535u) cfg_.max_vehicles = 65535u;  // 16-bit index in the sort key
  if (cfg_.dt <= 0.f) cfg_.dt = 0.05f;

  const size_t cap = cfg_.max_vehicles;
  veh_.clear();
  veh_.reserve(cap);
  slot_of_id_.assign(cap, kInvalidIndex);
  free_ids_.clear();
  free_ids_.reserve(cap);
  for (size_t i = cap; i > 0; --i) free_ids_.push_back(static_cast<uint32_t>(i - 1));
  path_pool_.assign(cap * kPathCap, kInvalidIndex);
  order_keys_.reserve(cap);
  order_.assign(cap, kInvalidIndex);
  new_accel_.assign(cap, 0.f);
  new_swerve_.assign(cap, 0.f);
  new_flags_.assign(cap, 0u);
  new_lane_.assign(cap, kInvalidIndex);
  ev_limit_.assign(cap, kBigDistance);
  pending_routes_.clear();
  pending_routes_.reserve(cap);

  const size_t lanes = g.laneCount();
  lane_first_.assign(lanes, 0u);
  lane_num_.assign(lanes, 0u);
  lane_stamp_.assign(lanes, 0u);
  stamp_ = 0;

  float minx, miny, maxx, maxy;
  g.bounds(minx, miny, maxx, maxy);
  hash_.configure(minx - 50.f, miny - 50.f, maxx + 50.f, maxy + 50.f, 15.f, cfg_.max_vehicles);

  claims_.assign(g.nodeCount() * kClaimsPerNode, NodeClaim{});

  lc_claims_.clear();
  lc_claims_.reserve(cap);
  lc_head_.assign(lanes, kInvalidIndex);
  lc_stamp_.assign(lanes, 0u);
  straddle_head_.assign(lanes, kInvalidIndex);
  straddle_stamp_.assign(lanes, 0u);
  straddle_next_.assign(cap, kInvalidIndex);
  conflicts_.clear();
  conflict_first_.assign(lanes, 0u);
  conflict_count_.assign(lanes, 0u);
  jl_lock_.assign(lanes, JunctionLock{});
  if (cfg_.build_junction_conflicts) buildJunctionConflicts();

  // NTA lane-kilometres (travel and bus lanes only — the density contract is
  // "vehicles per lane-km", DATA_CONTRACTS §10).
  nta_lane_km_.assign(static_cast<size_t>(g.ntaCount()) + 1u, 0.f);
  for (uint32_t li = 0; li < lanes; ++li) {
    const Lane& l = g.lane(li);
    if (l.is_junction != 0) continue;
    if (l.kind != LaneKind::Travel && l.kind != LaneKind::Bus) continue;
    const size_t slot = l.nta == routing::kNoNta ? nta_lane_km_.size() - 1 : l.nta;
    if (slot < nta_lane_km_.size()) nta_lane_km_[slot] += l.length_m * 0.001f;
  }

  honk_count_ = 0;
  time_s_ = 0.0;
  step_ix_ = 0;
  spawn_credit_ = 0.f;
  spawn_hour_ = 0xFF;
  next_id_ = 0;
  seed_ = seed;
  rng_.reseed(seed);
  stats_ = TrafficStats{};
  rebuildSpawnWeights();
  return true;
}

void TrafficSim::reset(uint64_t seed) {
  veh_.clear();
  std::fill(slot_of_id_.begin(), slot_of_id_.end(), kInvalidIndex);
  free_ids_.clear();
  for (size_t i = slot_of_id_.size(); i > 0; --i) free_ids_.push_back(static_cast<uint32_t>(i - 1));
  std::fill(claims_.begin(), claims_.end(), NodeClaim{});
  pending_routes_.clear();
  honk_count_ = 0;
  time_s_ = 0.0;
  step_ix_ = 0;
  spawn_credit_ = 0.f;
  next_id_ = 0;
  seed_ = seed;
  rng_.reseed(seed);
  stats_ = TrafficStats{};
}

void TrafficSim::setDensityTable(const DensityTable* d) {
  density_ = d;
  spawn_hour_ = 0xFF;
  rebuildSpawnWeights();
}

void TrafficSim::setTimeOfDay(float seconds_since_midnight, uint8_t dow) {
  tod_s_ = std::fmod(seconds_since_midnight, 86400.f);
  if (tod_s_ < 0.f) tod_s_ += 86400.f;
  dow_ = dow > 2 ? 0u : dow;
  const uint8_t hour = static_cast<uint8_t>(tod_s_ / 3600.f);
  if (hour != spawn_hour_) rebuildSpawnWeights();
}

// Precomputes the origin/destination sampling distribution: every travel lane
// weighted by (lane length × vehicles per lane-km of its NTA at the current
// hour), indexed spatially so a draw can be restricted to the streamed region
// (ADR-021).  Lanes are added in index order, so the cumulative sums are the
// same floats the flat array carried before the index existed.
void TrafficSim::rebuildSpawnWeights() {
  spawn_index_.clear();
  origin_region_ = RegionSampler::Region{};
  dest_region_ = RegionSampler::Region{};
  if (graph_ == nullptr) return;
  const uint8_t hour = static_cast<uint8_t>(clampf(tod_s_ / 3600.f, 0.f, 23.f));
  spawn_hour_ = hour;
  for (uint32_t li = 0; li < graph_->laneCount(); ++li) {
    const Lane& l = graph_->lane(li);
    if (l.is_junction != 0 || l.disabled != 0) continue;
    if (l.kind != LaneKind::Travel) continue;
    if (l.length_m < 15.f) continue;
    const uint32_t seg = l.segment;
    if (seg != kInvalidIndex && (graph_->segment(seg).attrs.flags & routing::kSegNoSpawn) != 0) continue;
    float w = l.length_m;
    if (density_ != nullptr && l.nta != routing::kNoNta) {
      const DensityCell& c = density_->get(l.nta, hour, dow_);
      w *= std::max(0.01f, c.veh_per_km_lane);
    }
    const routing::Vec3 mid = graph_->pointAt(li, 0.5f * l.length_m);
    spawn_index_.add(li, mid.x, mid.y, w, 0.5f * l.length_m);
  }
  spawn_index_.build();
  // Sized once, here, so refreshing a region inside step() never allocates.
  spawn_index_.reserveRegion(origin_region_);
  spawn_index_.reserveRegion(dest_region_);
}

// Re-centres the two sampling regions on the player.  Without a streaming ring
// there is no region: the whole graph is drawn from, exactly as before.
void TrafficSim::refreshSpawnRegions() {
  if (spawn_index_.empty()) return;
  if (!cfg_.use_player_ring || !player_.valid) {
    origin_region_.radius = -1.f;
    dest_region_.radius = -1.f;
    return;
  }
  const float slack = std::max(0.f, cfg_.region_slack_m);
  spawn_index_.refresh(origin_region_, player_.x, player_.y, std::max(1.f, cfg_.spawn_outer_m), slack);
  const float dr = cfg_.dest_radius_m > 0.f ? cfg_.dest_radius_m : cfg_.despawn_m;
  spawn_index_.refresh(dest_region_, player_.x, player_.y, std::max(1.f, dr), slack);
}

// --------------------------------------------------------- junction conflicts
void TrafficSim::buildJunctionConflicts() {
  const routing::RoadGraph& g = *graph_;
  const size_t lanes = g.laneCount();
  std::vector<std::vector<Conflict>> tmp(lanes);
  for (uint32_t ni = 0; ni < g.nodeCount(); ++ni) {
    uint32_t n = 0;
    const uint32_t* jls = g.nodeJunctionLanes(ni, n);
    if (n < 2 || n > 64) continue;
    for (uint32_t a = 0; a < n; ++a) {
      for (uint32_t b = a + 1; b < n; ++b) {
        const uint32_t la = jls[a], lb = jls[b];
        const Lane& A = g.lane(la);
        const Lane& B = g.lane(lb);
        float sa = -1.f, sb = -1.f;
        ConflictKind kind = ConflictKind::Cross;
        if (A.from_lane == B.from_lane) {
          sa = 0.f;
          sb = 0.f;  // diverging from the same approach lane
          kind = ConflictKind::SameOrigin;
        } else if (A.to_lane == B.to_lane) {
          sa = A.length_m;
          sb = B.length_m;  // merging into the same receiving lane
          kind = ConflictKind::Merge;
        } else {
          uint32_t na = 0, nb = 0;
          const Vec3* va = g.laneVertices(la, na);
          const Vec3* vb = g.laneVertices(lb, nb);
          const float* ca = g.laneCumulative(la);
          const float* cb = g.laneCumulative(lb);
          for (uint32_t i = 0; i + 1 < na && sa < 0.f; ++i) {
            for (uint32_t j = 0; j + 1 < nb; ++j) {
              float t = 0.f, u = 0.f;
              if (!segIntersect(va[i], va[i + 1], vb[j], vb[j + 1], t, u)) continue;
              sa = ca[i] + t * (ca[i + 1] - ca[i]);
              sb = cb[j] + u * (cb[j + 1] - cb[j]);
              break;
            }
          }
        }
        if (sa < 0.f || sb < 0.f) continue;
        tmp[la].push_back(Conflict{lb, sa, sb, kind});
        tmp[lb].push_back(Conflict{la, sb, sa, kind});
      }
    }
  }
  size_t total = 0;
  for (const auto& v : tmp) total += v.size();
  conflicts_.clear();
  conflicts_.reserve(total);
  for (size_t li = 0; li < lanes; ++li) {
    conflict_first_[li] = static_cast<uint32_t>(conflicts_.size());
    conflict_count_[li] = static_cast<uint32_t>(tmp[li].size());
    for (const Conflict& c : tmp[li]) conflicts_.push_back(c);
  }
}

// ------------------------------------------------------------------ indexing
// Sorts the agents by (lane, s) and rebuilds the per-lane ranges.  Called at
// the top of the step and again after the lane transitions, so the non-overlap
// pass sees the positions the agents actually ended up in.
void TrafficSim::buildOrder() {
  ++stamp_;
  order_keys_.clear();
  for (uint32_t i = 0; i < veh_.size(); ++i) order_keys_.push_back(packKey(veh_[i].lane, veh_[i].s, i));
  std::sort(order_keys_.begin(), order_keys_.end());
  uint32_t run_lane = kInvalidIndex, run_start = 0;
  for (uint32_t k = 0; k < order_keys_.size(); ++k) {
    const uint32_t lane = static_cast<uint32_t>(order_keys_[k] >> 40);
    if (lane != run_lane) {
      if (run_lane != kInvalidIndex && run_lane < lane_num_.size()) lane_num_[run_lane] = k - run_start;
      run_lane = lane;
      run_start = k;
      if (lane < lane_first_.size()) {
        lane_first_[lane] = k;
        lane_stamp_[lane] = stamp_;
      }
    }
  }
  if (run_lane != kInvalidIndex && run_lane < lane_num_.size())
    lane_num_[run_lane] = static_cast<uint32_t>(order_keys_.size()) - run_start;

  for (uint32_t i = 0; i < veh_.size(); ++i) {
    const uint32_t from = veh_[i].lc_from;
    if (from == kInvalidIndex || from >= straddle_head_.size()) continue;
    if (straddle_stamp_[from] != stamp_) {
      straddle_stamp_[from] = stamp_;
      straddle_head_[from] = kInvalidIndex;
    }
    straddle_next_[i] = straddle_head_[from];
    straddle_head_[from] = i;
  }
}

TrafficSim::Neighbour TrafficSim::leaderIncludingStraddlers(uint32_t lane, float s, float half_len,
                                                            uint32_t skip) const {
  Neighbour r = leaderInLane(lane, s, half_len, skip);
  if (lane >= straddle_stamp_.size() || straddle_stamp_[lane] != stamp_) return r;
  for (uint32_t k = straddle_head_[lane]; k != kInvalidIndex; k = straddle_next_[k]) {
    if (k == skip) continue;
    const Vehicle& o = veh_[k];
    if (o.s <= s) continue;
    const float gap = (o.s - o.length_m * 0.5f) - (s + half_len);
    if (r.index != kInvalidIndex && gap >= r.gap) continue;
    r.index = k;
    r.gap = gap;
    r.speed = o.speed;
  }
  return r;
}

TrafficSim::Neighbour TrafficSim::followerIncludingStraddlers(uint32_t lane, float s, float half_len,
                                                              uint32_t skip) const {
  Neighbour r = followerInLane(lane, s, half_len, skip);
  if (lane >= straddle_stamp_.size() || straddle_stamp_[lane] != stamp_) return r;
  for (uint32_t k = straddle_head_[lane]; k != kInvalidIndex; k = straddle_next_[k]) {
    if (k == skip) continue;
    const Vehicle& o = veh_[k];
    if (o.s >= s) continue;
    const float gap = (s - half_len) - (o.s + o.length_m * 0.5f);
    if (r.index != kInvalidIndex && gap >= r.gap) continue;
    r.index = k;
    r.gap = gap;
    r.speed = o.speed;
  }
  return r;
}

void TrafficSim::rebuildIndex() {
  buildOrder();
  lc_claims_.clear();
  hash_.begin();
  ev_list_.clear();
  for (uint32_t i = 0; i < veh_.size(); ++i) {
    if (!hash_.insert(i, veh_[i].pos.x, veh_[i].pos.y)) ++stats_.hash_drops;
    if ((veh_[i].flags & kVehSiren) != 0) ev_list_.push_back(i);
  }
  hash_.end();
}

bool TrafficSim::laneSlotClaimed(uint32_t lane, float s, float half_len) const {
  if (lane >= lc_stamp_.size() || lc_stamp_[lane] != stamp_) return false;
  for (uint32_t k = lc_head_[lane]; k != kInvalidIndex; k = lc_claims_[k].next) {
    const LcClaim& c = lc_claims_[k];
    if (std::fabs(c.s - s) < c.half + half_len + cfg_.lc_gap_rear_m) return true;
  }
  return false;
}

void TrafficSim::claimLaneSlot(uint32_t lane, float s, float half_len) {
  if (lane >= lc_stamp_.size()) return;
  if (lc_stamp_[lane] != stamp_) {
    lc_stamp_[lane] = stamp_;
    lc_head_[lane] = kInvalidIndex;
  }
  lc_claims_.push_back(LcClaim{s, half_len, lc_head_[lane]});
  lc_head_[lane] = static_cast<uint32_t>(lc_claims_.size() - 1);
}

TrafficSim::Neighbour TrafficSim::leaderInLane(uint32_t lane, float s, float half_len, uint32_t skip) const {
  Neighbour r;
  if (lane >= lane_stamp_.size() || lane_stamp_[lane] != stamp_) return r;
  const uint32_t first = lane_first_[lane], count = lane_num_[lane];
  const uint64_t probe = packKey(lane, s, 0);
  const auto begin = order_keys_.begin() + static_cast<ptrdiff_t>(first);
  const auto end = begin + static_cast<ptrdiff_t>(count);
  auto it = std::lower_bound(begin, end, probe);
  for (; it != end; ++it) {
    const uint32_t j = keyIndex(*it);
    if (j == skip) continue;
    const Vehicle& o = veh_[j];
    if (o.s <= s) continue;
    r.index = j;
    r.gap = (o.s - o.length_m * 0.5f) - (s + half_len);
    r.speed = o.speed;
    return r;
  }
  return r;
}

TrafficSim::Neighbour TrafficSim::followerInLane(uint32_t lane, float s, float half_len, uint32_t skip) const {
  Neighbour r;
  if (lane >= lane_stamp_.size() || lane_stamp_[lane] != stamp_) return r;
  const uint32_t first = lane_first_[lane], count = lane_num_[lane];
  const uint64_t probe = packKey(lane, s, 0);
  const auto begin = order_keys_.begin() + static_cast<ptrdiff_t>(first);
  const auto end = begin + static_cast<ptrdiff_t>(count);
  auto it = std::lower_bound(begin, end, probe);
  while (it != begin) {
    --it;
    const uint32_t j = keyIndex(*it);
    if (j == skip) continue;
    const Vehicle& o = veh_[j];
    if (o.s >= s) continue;
    r.index = j;
    r.gap = (s - half_len) - (o.s + o.length_m * 0.5f);
    r.speed = o.speed;
    return r;
  }
  return r;
}

// Leader along the agent's own path, crossing up to four lanes.
TrafficSim::Neighbour TrafficSim::leaderAhead(const Vehicle& v, float horizon_m) const {
  Neighbour best;
  const uint32_t self = indexOfId(v.id);
  const float hl = v.length_m * 0.5f;
  float base = -(v.s + hl);
  uint32_t lane = v.lane;
  uint32_t pp = v.path_pos;
  const uint32_t* path = pathOf(v.id);
  for (int k = 0; k < 4; ++k) {
    const float from_s = (k == 0) ? v.s : -1.f;
    const Neighbour n = leaderIncludingStraddlers(lane, from_s, 0.f, k == 0 ? self : kInvalidIndex);
    if (n.index != kInvalidIndex) {
      const Vehicle& o = veh_[n.index];
      best.index = n.index;
      best.gap = base + (o.s - o.length_m * 0.5f);
      best.speed = o.speed;
      if (best.gap < 0.f) best.gap = 0.f;
      return best;
    }
    base += graph_->lane(lane).length_m;
    if (base > horizon_m) break;
    ++pp;
    if (pp >= v.path_len) break;
    lane = path[pp];
    if (lane == kInvalidIndex) break;
  }
  return best;
}

float TrafficSim::laneOccupancyAhead(uint32_t lane, float from_s, float span_m) const {
  if (lane >= lane_stamp_.size() || lane_stamp_[lane] != stamp_) return 0.f;
  const uint32_t first = lane_first_[lane], count = lane_num_[lane];
  float occupied = 0.f;
  for (uint32_t k = 0; k < count; ++k) {
    const Vehicle& o = veh_[keyIndex(order_keys_[first + k])];
    if (o.s < from_s || o.s > from_s + span_m) continue;
    occupied += o.length_m + 2.f;
  }
  return span_m > 0.1f ? occupied / span_m : 0.f;
}

// ------------------------------------------------------------------ helpers
IdmParams TrafficSim::idmOf(const Vehicle& v) const {
  const VehicleClassParams& p = classParams(v.cls);
  IdmParams i;
  i.a = p.max_accel;
  i.b = p.comfort_decel;
  i.b_max = p.max_decel;
  i.T = p.headway_T;
  i.s0 = p.min_gap_s0;
  i.v0 = v.v0;
  return i;
}

uint32_t TrafficSim::indexOfId(uint32_t id) const {
  return id < slot_of_id_.size() ? slot_of_id_[id] : kInvalidIndex;
}

const Vehicle* TrafficSim::byId(uint32_t id) const {
  const uint32_t s = indexOfId(id);
  return s == kInvalidIndex ? nullptr : &veh_[s];
}

bool TrafficSim::inProtectedRegion(float x, float y) const {
  return cfg_.use_player_ring && player_.inProtectedRegion(x, y);
}

uint32_t TrafficSim::nextJunction(const Vehicle& v) const {
  if (graph_ == nullptr) return kInvalidIndex;
  if (graph_->lane(v.lane).is_junction != 0) return kInvalidIndex;
  if (v.path_pos + 1 >= v.path_len) return kInvalidIndex;
  const uint32_t nl = pathOf(v.id)[v.path_pos + 1];
  if (nl == kInvalidIndex || nl >= graph_->laneCount()) return kInvalidIndex;
  return graph_->lane(nl).is_junction != 0 ? nl : kInvalidIndex;
}

VehSignal TrafficSim::laneSignal(uint32_t lane) const {
  if (graph_ == nullptr || signals_ == nullptr || lane >= graph_->laneCount()) return VehSignal::Off;
  const Lane& l = graph_->lane(lane);
  if (l.is_junction == 0 || l.signal_group < 0) return VehSignal::Off;
  const uint32_t plan = signals_->planForNode(l.node);
  if (plan == kInvalidIndex) return VehSignal::Off;
  return signals_->cachedVehicleState(plan, l.signal_group);
}

float TrafficSim::measuredDensity(uint16_t nta) const {
  if (graph_ == nullptr) return 0.f;
  const size_t slot = nta == routing::kNoNta ? nta_lane_km_.size() - 1 : nta;
  if (slot >= nta_lane_km_.size() || nta_lane_km_[slot] <= 1e-4f) return 0.f;
  uint32_t count = 0;
  for (const Vehicle& v : veh_) {
    const Lane& l = graph_->lane(v.lane);
    if (l.is_junction != 0) continue;
    if (l.nta == nta) ++count;
  }
  return static_cast<float>(count) / nta_lane_km_[slot];
}

// ------------------------------------------------------------------- routing
bool TrafficSim::routeAgent(Vehicle& v, uint32_t to_lane, float to_s, uint32_t avoid_lane) {
  if (router_ == nullptr || !router_->attached() || to_lane == kInvalidIndex) {
    ++stats_.route_failures;
    return false;
  }
  const VehicleClassParams& cp = classParams(v.cls);
  routing::RouteQuery q;
  q.from_lane = v.lane;
  q.from_s = v.s;
  q.to_lane = to_lane;
  q.to_s = to_s;
  q.want_instructions = false;
  q.want_polyline = false;
  q.profile.lane_kinds = cp.lane_kinds;
  q.profile.allow_highway = cp.allow_highway;
  q.profile.max_speed_mps = cp.max_speed_mps;
  q.profile.non_bike_lane_factor = cp.is_bike ? 1.6f : 1.f;
  q.profile.turn_penalty_scale = (cp.is_truck || cp.is_bus) ? 1.5f : 1.f;
  q.profile.depart_time_s = tod_s_;
  q.profile.dow = dow_;
  q.profile.avoid_lane = avoid_lane;
  q.profile.avoid_penalty_s = 180.f;  // a detour, not a ban
  if (!router_->route(q, route_scratch_) || route_scratch_.lanes.empty()) {
    ++stats_.route_failures;
    return false;
  }
  uint32_t* path = pathOf(v.id);
  const size_t n = std::min<size_t>(route_scratch_.lanes.size(), kPathCap);
  for (size_t k = 0; k < n; ++k) path[k] = route_scratch_.lanes[k];
  v.path_len = static_cast<uint32_t>(n);
  v.path_pos = 0;
  v.lane = path[0];
  v.dest_lane = to_lane;
  v.dest_s = to_s;
  v.flags |= kVehHasRoute;
  ++stats_.route_calls;
  return true;
}

// Buses follow a real route: the destination is always the next scheduled stop.
void TrafficSim::assignBusRoute(Vehicle& v) {
  if (buses_ == nullptr || buses_->routeCount() == 0) return;
  uint32_t best_route = kInvalidIndex, best_k = 0;
  float best_d = 1e30f;
  for (uint32_t r = 0; r < buses_->routeCount(); ++r) {
    uint32_t n = 0;
    const uint32_t* ss = buses_->routeStops(r, n);
    for (uint32_t k = 0; k < n; ++k) {
      const BusStop& st = buses_->stop(ss[k]);
      if (st.lane == v.lane && st.s > v.s) {
        best_route = r;
        best_k = k;
        best_d = -1.f;
        break;
      }
      const float dx = st.pos.x - v.pos.x, dy = st.pos.y - v.pos.y;
      const float d = dx * dx + dy * dy;
      if (d < best_d) {
        best_d = d;
        best_route = r;
        best_k = k;
      }
    }
    if (best_d < 0.f) break;
  }
  if (best_route == kInvalidIndex) return;
  v.bus_route = static_cast<uint16_t>(best_route);
  v.bus_next_stop = static_cast<uint16_t>(best_k);
  // A bus with a route but no path to its next stop would otherwise wander with
  // nothing to show for it; the failure is counted (routeAgent) or, when there
  // is no router at all, counted here.
  if (!advanceBusToNextStop(v)) ++stats_.route_failures;
}

bool TrafficSim::advanceBusToNextStop(Vehicle& v) {
  if (buses_ == nullptr || v.bus_route == 0xFFFFu) return false;
  uint32_t n = 0;
  const uint32_t* ss = buses_->routeStops(v.bus_route, n);
  if (n == 0) return false;
  const uint32_t k = v.bus_next_stop % n;
  const BusStop& st = buses_->stop(ss[k]);
  v.bus_next_stop = static_cast<uint16_t>((k + 1u) % n);
  if (st.lane == kInvalidIndex) return false;
  if (router_ == nullptr || !router_->attached()) return false;
  return routeAgent(v, st.lane, st.s);
}

void TrafficSim::extendPath(Vehicle& v) {
  uint32_t* path = pathOf(v.id);
  if (v.path_pos > kPathCap / 2 && v.path_len > v.path_pos) {
    const uint32_t keep = v.path_len - v.path_pos;
    std::memmove(path, path + v.path_pos, static_cast<size_t>(keep) * sizeof(uint32_t));
    v.path_len = keep;
    v.path_pos = 0;
  }
  const VehicleClassParams& cp = classParams(v.cls);
  while (v.path_len < kPathCap && v.path_len - v.path_pos < 8) {
    const uint32_t last = path[v.path_len - 1];
    uint32_t n = 0;
    const uint32_t* succ = graph_->successors(last, n);
    // Weighted choice: straight ahead is the default, turns are less likely,
    // U-turns only as a last resort.  Bikes and buses prefer their own lanes.
    uint32_t best[8];
    float w[8];
    uint32_t m = 0;
    for (uint32_t k = 0; k < n && m < 8; ++k) {
      const uint32_t c = succ[k];
      if (!graph_->laneAllows(c, cp.lane_kinds)) continue;
      const Lane& cl = graph_->lane(c);
      float weight = 1.f;
      if (cl.is_junction != 0) {
        switch (cl.turn) {
          case TurnType::Straight: weight = 6.f; break;
          case TurnType::Right: weight = 2.f; break;
          case TurnType::Left: weight = 1.5f; break;
          case TurnType::UTurn: weight = 0.05f; break;
        }
      }
      if (cp.is_bike && cl.kind == LaneKind::Bike) weight *= 3.f;
      if (cp.is_bus && cl.kind == LaneKind::Bus) weight *= 3.f;
      best[m] = c;
      w[m] = weight;
      ++m;
    }
    if (m == 0) break;
    float total = 0.f;
    for (uint32_t k = 0; k < m; ++k) total += w[k];
    float pick = v.rng.uniform() * total;
    uint32_t chosen = best[m - 1];
    for (uint32_t k = 0; k < m; ++k) {
      pick -= w[k];
      if (pick <= 0.f) {
        chosen = best[k];
        break;
      }
    }
    path[v.path_len++] = chosen;
  }
}

bool TrafficSim::advanceLane(Vehicle& v) {
  uint32_t* path = pathOf(v.id);
  int guard = 0;
  while (v.s >= graph_->lane(v.lane).length_m && guard++ < 4) {
    const float len = graph_->lane(v.lane).length_m;
    if ((v.flags & kVehHasRoute) != 0 && v.lane == v.dest_lane && v.s >= v.dest_s) return false;
    if (v.path_pos + 1 >= v.path_len) {
      extendPath(v);
      if (v.path_pos + 1 >= v.path_len) {
        // Dead end (the edge of the network, or a closure): hold at the end of
        // the lane and recycle as soon as the player ring allows it, otherwise
        // the agent would stand there for ever and block the lane.
        v.s = len;
        v.speed = 0.f;
        v.exit_now = 1;
        return true;
      }
    }
    const uint32_t next_lane = path[v.path_pos + 1];
    // Never drive into an occupied cell: if the head of the receiving lane is
    // taken, hold at the end of this one (the box-blocking check gates entry,
    // but the receiving lane can fill while we are inside the junction).
    if (next_lane < graph_->laneCount()) {
      const Neighbour head = leaderIncludingStraddlers(next_lane, -1.f, 0.f, kInvalidIndex);
      if (head.index != kInvalidIndex &&
          veh_[head.index].s - veh_[head.index].length_m * 0.5f < v.length_m * 0.5f + 0.1f) {
        v.s = len - 0.01f;
        v.speed = 0.f;
        return true;
      }
    }
    const bool was_junction = graph_->lane(v.lane).is_junction != 0;
    v.s -= len;
    ++v.path_pos;
    v.lane = path[v.path_pos];
    v.flags &= static_cast<uint8_t>(~(kVehStoppedDone | kVehBlockedBox));
    if (was_junction) {
      v.junction_time = 0.f;
      releaseClaim(v);
    }
    if (was_junction) releaseJunction(v);
  }
  return true;
}

// ---------------------------------------------------------- right of way
void TrafficSim::releaseClaim(Vehicle& v) {
  if (v.claim_node == kInvalidIndex) return;
  NodeClaim* c = claims_.data() + static_cast<size_t>(v.claim_node) * kClaimsPerNode;
  for (uint32_t k = 0; k < kClaimsPerNode; ++k)
    if (c[k].used != 0 && c[k].agent == v.id) c[k] = NodeClaim{};
  v.claim_node = kInvalidIndex;
}

float TrafficSim::criticalGap(const Lane& jl, bool major) const {
  if (major) return cfg_.gap_major_left_s;
  switch (jl.turn) {
    case TurnType::Right: return cfg_.gap_minor_right_s;
    case TurnType::Straight: return cfg_.gap_minor_through_s;
    case TurnType::Left: return cfg_.gap_minor_left_s;
    case TurnType::UTurn: return cfg_.gap_minor_left_s + 1.f;
  }
  return cfg_.gap_minor_through_s;
}

// True when no conflicting vehicle arrives within `critical_gap_s`.
bool TrafficSim::gapAccepted(const Vehicle& v, uint32_t junction_lane, float critical_gap_s) const {
  uint32_t n = 0;
  const uint32_t* yl = graph_->yieldTo(junction_lane, n);
  for (uint32_t k = 0; k < n; ++k) {
    const uint32_t other = yl[k];
    const Lane& ol = graph_->lane(other);
    // Anyone already inside the intersection on that movement blocks us.
    if (other < lane_stamp_.size() && lane_stamp_[other] == stamp_ && lane_num_[other] > 0) return false;
    if (ol.is_junction == 0) continue;
    const uint32_t approach = ol.from_lane;
    if (approach == kInvalidIndex || approach >= lane_stamp_.size()) continue;
    if (lane_stamp_[approach] != stamp_) continue;
    const uint32_t first = lane_first_[approach], count = lane_num_[approach];
    if (count == 0) continue;
    const float alen = graph_->lane(approach).length_m;
    // The vehicle closest to the stop line is the last one in the run.
    const Vehicle& o = veh_[keyIndex(order_keys_[first + count - 1])];
    if (o.id == v.id) continue;
    const float dist = alen - o.s;
    if (dist < 0.f) return false;
    const float tta = dist / std::max(1.0f, o.speed);
    if (o.speed < 0.4f && dist > 6.f) continue;  // stopped and not creeping
    if (tta < critical_gap_s) return false;
  }
  return true;
}

// Junction occupancy: is any conflicting junction lane occupied near the point
// where it crosses this one?
bool TrafficSim::junctionClear(const Vehicle& v, uint32_t junction_lane) const {
  const uint32_t first = conflict_first_[junction_lane], count = conflict_count_[junction_lane];
  for (uint32_t k = 0; k < count; ++k) {
    const Conflict& c = conflicts_[first + k];
    // A crossing movement claimed by somebody else this step is off limits:
    // without this, two vehicles deciding in the same step would both find the
    // intersection empty and enter it together.
    if (c.kind == ConflictKind::Cross && c.other < jl_lock_.size()) {
      const JunctionLock& lk = jl_lock_[c.other];
      if (lk.owner != kInvalidIndex && lk.owner != v.id && lk.expiry > time_s_ &&
          indexOfId(lk.owner) != kInvalidIndex)
        return false;
    }
    if (c.other >= lane_stamp_.size() || lane_stamp_[c.other] != stamp_) continue;
    const uint32_t f = lane_first_[c.other], n = lane_num_[c.other];
    for (uint32_t j = 0; j < n; ++j) {
      const Vehicle& o = veh_[keyIndex(order_keys_[f + j])];
      if (o.id == v.id) continue;
      const float half = o.length_m * 0.5f + 1.5f;
      if (o.s > c.s_other - half - v.length_m && o.s < c.s_other + half) return false;
    }
  }
  return true;
}

void TrafficSim::lockJunction(const Vehicle& v, uint32_t junction_lane) {
  if (junction_lane >= jl_lock_.size()) return;
  JunctionLock& lk = jl_lock_[junction_lane];
  if (lk.owner != kInvalidIndex && lk.owner != v.id && lk.expiry > time_s_ &&
      indexOfId(lk.owner) != kInvalidIndex)
    return;  // somebody else holds it (junctionClear already refused us)
  lk.owner = v.id;
  lk.expiry = time_s_ + 1.0;
}

void TrafficSim::releaseJunction(const Vehicle& v) {
  const uint32_t lane = v.lane;
  if (lane < jl_lock_.size() && jl_lock_[lane].owner == v.id) jl_lock_[lane] = JunctionLock{};
}

// Space on the receiving lane for the whole vehicle (the "don't block the box"
// rule, NYC Traffic Rules §4-07(b)(2)).
bool TrafficSim::exitSpaceAvailable(const Vehicle& v, uint32_t junction_lane) const {
  const Lane& jl = graph_->lane(junction_lane);
  const uint32_t to = jl.to_lane;
  if (to == kInvalidIndex || to >= graph_->laneCount()) return true;
  const IdmParams p = idmOf(v);
  const Neighbour n = leaderInLane(to, 0.f, 0.f, kInvalidIndex);
  if (n.index == kInvalidIndex) return true;
  const Vehicle& o = veh_[n.index];
  const float free_space = o.s - o.length_m * 0.5f;
  return free_space >= v.length_m + p.s0;
}

// First-come-first-served with the New York tie-breakers: the vehicle on the
// right goes first, and a left turn yields to a straight movement from the
// opposite approach (NY VTL §1142, §1141).
bool TrafficSim::stopSignPriority(Vehicle& v, uint32_t node, uint32_t junction_lane) {
  const Lane& jl = graph_->lane(junction_lane);
  const routing::LanePose pose = graph_->poseAt(jl.from_lane, graph_->lane(jl.from_lane).length_m);
  NodeClaim* base = claims_.data() + static_cast<size_t>(node) * kClaimsPerNode;

  // Register / refresh our claim.
  int mine = -1;
  for (uint32_t k = 0; k < kClaimsPerNode; ++k) {
    if (base[k].used != 0 && base[k].agent == v.id) {
      mine = static_cast<int>(k);
      break;
    }
  }
  if (mine < 0) {
    for (uint32_t k = 0; k < kClaimsPerNode; ++k) {
      NodeClaim& c = base[k];
      if (c.used != 0) {
        // Drop stale claims (agent gone, or it moved on).
        const uint32_t slot = indexOfId(c.agent);
        if (slot == kInvalidIndex || veh_[slot].claim_node != node) c = NodeClaim{};
      }
      if (c.used == 0) {
        c.used = 1;
        c.agent = v.id;
        c.arrival = static_cast<float>(time_s_);
        c.dirx = pose.dir.x;
        c.diry = pose.dir.y;
        c.turn = static_cast<uint8_t>(jl.turn);
        mine = static_cast<int>(k);
        v.claim_node = node;
        v.claim_time = c.arrival;
        break;
      }
    }
    if (mine < 0) return false;  // table full: wait, retry next step
  }
  const NodeClaim& me = base[mine];
  for (uint32_t k = 0; k < kClaimsPerNode; ++k) {
    if (static_cast<int>(k) == mine || base[k].used == 0) continue;
    const NodeClaim& c = base[k];
    const uint32_t slot = indexOfId(c.agent);
    if (slot == kInvalidIndex || veh_[slot].claim_node != node) continue;
    const float dot = me.dirx * c.dirx + me.diry * c.diry;
    if (dot > 0.7f) continue;  // same approach: they are simply ahead in the queue
    if (c.arrival < me.arrival - 0.05f) return false;  // first come, first served
    if (c.arrival <= me.arrival + 0.05f) {
      const float cross = me.dirx * c.diry - me.diry * c.dirx;
      if (cross > 0.5f) return false;  // the vehicle on our right goes first
      if (dot < -0.7f && me.turn == static_cast<uint8_t>(TurnType::Left) &&
          c.turn != static_cast<uint8_t>(TurnType::Left))
        return false;  // left turn yields to the opposing straight
    }
  }
  return true;
}

// Returns the distance at which the agent must stop (kBigDistance = go).
float TrafficSim::signalStopDistance(const Vehicle& v, uint32_t junction_lane, float dist_to_line,
                                     bool& entered_on_red) {
  entered_on_red = false;
  const Lane& jl = graph_->lane(junction_lane);
  if (jl.signal_group < 0) return kBigDistance;
  const uint32_t plan = signals_->planForNode(jl.node);
  if (plan == kInvalidIndex) return kBigDistance;
  const VehSignal sig = signals_->cachedVehicleState(plan, jl.signal_group);
  if (sig == VehSignal::Green || sig == VehSignal::Off) return kBigDistance;

  const VehicleClassParams& cp = classParams(v.cls);
  // Emergency vehicles on a run may proceed through a red after slowing
  // (NY VTL §1104(b)(2)); they still have to yield, which the conflict and
  // gap checks below enforce.
  if ((v.flags & kVehSiren) != 0) return kBigDistance;

  if (sig == VehSignal::Yellow) {
    const float d_stop = stoppingDistance(v.speed, cp.comfort_decel, cfg_.yellow_reaction_s);
    if (dist_to_line < d_stop) return kBigDistance;  // dilemma zone: proceed
    return dist_to_line;
  }
  // Red.  New York has no right turn on red anywhere in the five boroughs
  // (NYC Traffic Rules §4-03(a)(2)) unless a sign permits it, and no such sign
  // exists in the data, so this is an absolute rule — not even the drivers who
  // will run a late red take it.
  if (cfg_.no_right_on_red && jl.turn == TurnType::Right) return dist_to_line;
  const bool law_abiding = (v.flags & kVehLawAbiding) != 0;
  if (!law_abiding && dist_to_line < v.speed * cfg_.red_run_window_s && v.speed > 3.f) {
    entered_on_red = true;
    return kBigDistance;
  }
  return dist_to_line;
}

// --------------------------------------------------------------- player
float TrafficSim::playerConstraint(const Vehicle& v, float& swerve_out, bool& brake_hard) {
  swerve_out = 0.f;
  brake_hard = false;
  if (!player_.valid) return kBigDistance;
  const float dx = player_.x - v.pos.x, dy = player_.y - v.pos.y;
  if (dx * dx + dy * dy > 90.f * 90.f) return kBigDistance;

  // Longitudinal position of the player in the agent's own lane frame.
  float s = 0.f, lat = 0.f, dist = 0.f;
  float best = kBigDistance;
  const uint32_t* path = pathOf(v.id);
  float base = -(v.s + v.length_m * 0.5f);
  uint32_t lane = v.lane, pp = v.path_pos;
  for (int k = 0; k < 3; ++k) {
    if (graph_->projectOnLane(lane, player_.x, player_.y, s, lat, dist, 12.f)) {
      const float gap = base + s - player_.half_length_m;
      const float lateral_sep = std::fabs(lat - (k == 0 ? v.lateral : 0.f));
      const float clear = v.width_m * 0.5f + player_.half_width_m + 0.25f;
      if (gap > -3.f && gap < 70.f) {
        if (lateral_sep < clear || player_.on_foot) {
          const float stop_at = player_.on_foot ? gap - cfg_.player_person_stop_m : gap;
          if (stop_at < best) best = stop_at < 0.f ? 0.f : stop_at;
          const float closing = v.speed - player_.speed_mps;
          if (closing > 0.3f && gap / closing < cfg_.player_ttc_brake_s) brake_hard = true;
        } else if (lateral_sep < cfg_.player_lane_halfwidth_m + clear && gap < 30.f && !player_.on_foot) {
          // Squeeze past inside the lane rather than stopping dead.
          swerve_out = (lat >= v.lateral ? -1.f : 1.f) * cfg_.player_swerve_m;
        }
      }
    }
    base += graph_->lane(lane).length_m;
    ++pp;
    if (pp >= v.path_len) break;
    lane = path[pp];
    if (lane == kInvalidIndex) break;
  }
  return best;
}

// Emergency vehicles: pull right and slow down (NY VTL §1144).
// The yield field for the whole fleet, computed once per step from the poses
// the spatial hash was built on.  A vehicle only reaches this rule when it is
// driving (decide() returns earlier for a parked or dwelling agent), so the
// same state filter is applied here; the flag of an agent that never asks is
// left alone, exactly as before.
void TrafficSim::updateEmergencyField() {
  const uint32_t n = static_cast<uint32_t>(veh_.size());
  std::fill_n(ev_limit_.begin(), n, kBigDistance);
  auto asks = [](const Vehicle& v) {
    return (v.flags & kVehSiren) == 0 &&
           (v.state == DriveState::Driving || v.state == DriveState::StoppedAtLine ||
            v.state == DriveState::WaitingRow);
  };
  for (uint32_t i = 0; i < n; ++i) {
    Vehicle& v = veh_[i];
    if (asks(v)) v.flags &= static_cast<uint8_t>(~kVehYieldingEv);
  }
  if (ev_list_.empty()) return;
  const float radius = cfg_.emergency_radius_m;
  const float r2 = radius * radius;
  for (uint32_t ei : ev_list_) {
    const Vehicle& e = veh_[ei];
    const float ex = std::cos(e.heading_rad), ey = std::sin(e.heading_rad);
    const float epx = e.pos.x, epy = e.pos.y;
    const uint32_t eid = e.id;
    hash_.query(epx, epy, radius, [&](uint32_t i) {
      if (i >= n) return;
      Vehicle& v = veh_[i];
      if (v.id == eid || !asks(v)) return;
      const float dx = v.pos.x - epx, dy = v.pos.y - epy;
      const float d2 = dx * dx + dy * dy;
      if (d2 > r2) return;
      // Only yield to a siren that is behind us and pointing our way.
      const float along = dx * ex + dy * ey;   // > 0 when we are ahead of it
      const float lateral = std::fabs(-dx * ey + dy * ex);
      if (along < -5.f || along > radius || lateral > 12.f) return;
      v.flags |= kVehYieldingEv;
      ++stats_.emergency_yields;
      // slow, keep creeping to the curb
      ev_limit_[i] = std::min(ev_limit_[i], 6.f + along * 0.2f);
    });
  }
}

// Where a vehicle must yield to people already in the roadway.  The crossings
// a vehicle traverses are: the one across its own approach (at its stop line —
// people there are crossing against the signal), the ones inside the junction,
// and, for a turn, the crossing on the street it turns into, which is exactly
// where the New York turning conflict happens: that crossing has WALK while the
// turning driver has green, and the driver is the one who must give way
// (NY VTL §1151, NYC Traffic Rules §4-04).
float TrafficSim::pedestrianConstraint(const Vehicle& v, uint32_t junction_lane, float dist_to_line) const {
  if (!ped_probe_.valid()) return kBigDistance;
  const float band = cfg_.stop_line_setback_m - 2.5f;  // centre of the crosswalk band
  float best = kBigDistance;
  if (junction_lane != kInvalidIndex && dist_to_line < 25.f && (step_ix_ + v.id) % 4u == 0u) {
    const Lane& jl = graph_->lane(junction_lane);
    const Lane& from = graph_->lane(jl.from_lane);
    // 1. our own stop-line crossing
    const routing::LanePose ours = graph_->poseAt(jl.from_lane, std::max(0.f, from.length_m - band));
    if (ped_probe_.roadPeds(ours.pos.x, ours.pos.y, 3.5f) > 0) best = std::min(best, dist_to_line);
    // 2. the crossing on the receiving street
    if (jl.to_lane != kInvalidIndex && jl.to_lane < graph_->laneCount()) {
      const Lane& to = graph_->lane(jl.to_lane);
      const routing::LanePose recv = graph_->poseAt(jl.to_lane, std::min(band, to.length_m * 0.4f));
      if (ped_probe_.roadPeds(recv.pos.x, recv.pos.y, 4.0f) > 0) best = std::min(best, dist_to_line);
    }
    // 3. anybody inside the box itself
    const routing::LanePose mid = graph_->poseAt(junction_lane, jl.length_m * 0.5f);
    if (ped_probe_.roadPeds(mid.pos.x, mid.pos.y, 3.5f) > 0) best = std::min(best, dist_to_line);
  }
  const Lane& cur = graph_->lane(v.lane);
  if (cur.is_junction != 0) {
    // Already committed: keep looking ahead along the connector and into the
    // receiving lane, every step — there are few vehicles inside a junction.
    const float look = std::min(cur.length_m, v.s + 3.f + v.speed * 1.2f);
    const routing::LanePose ahead = graph_->poseAt(v.lane, look);
    if (ped_probe_.roadPeds(ahead.pos.x, ahead.pos.y, 3.0f) > 0)
      best = std::min(best, std::max(0.f, look - v.s - v.length_m * 0.5f));
    if (cur.to_lane != kInvalidIndex && cur.to_lane < graph_->laneCount()) {
      const Lane& to = graph_->lane(cur.to_lane);
      const routing::LanePose recv = graph_->poseAt(cur.to_lane, std::min(band, to.length_m * 0.4f));
      if (ped_probe_.roadPeds(recv.pos.x, recv.pos.y, 4.0f) > 0)
        best = std::min(best, std::max(0.f, cur.length_m - v.s + band - v.length_m * 0.5f));
    }
  } else if ((step_ix_ + v.id) % 4u == 0u && v.speed > 1.f) {
    // Mid-block jaywalkers: sampled at 5 Hz, staggered by agent id.
    const float look = std::min(20.f, 4.f + v.speed * 1.6f);
    const routing::LanePose ahead = graph_->poseAt(v.lane, std::min(v.s + look, cur.length_m));
    if (ped_probe_.roadPeds(ahead.pos.x, ahead.pos.y, 2.5f) > 0) best = std::min(best, look - 2.f);
  }
  return best;
}

// ------------------------------------------------------------ lane changing
void TrafficSim::considerLaneChange(uint32_t i, float a_current) {
  Vehicle& v = veh_[i];
  const Lane& l = graph_->lane(v.lane);
  if (l.is_junction != 0 || v.lc_cooldown > 0.f || v.speed < cfg_.lane_change_min_speed) return;
  if (v.state != DriveState::Driving) return;
  // Re-evaluated at 4 Hz, staggered across the fleet: MOBIL is the most
  // expensive thing an agent does and no driver reconsiders twenty times a
  // second.  A mandatory change still gets 4 chances a second, which is ample
  // over the 220 m route-pressure ramp.
  if ((step_ix_ + v.id) % 5u != 0u) return;
  const VehicleClassParams& cp = classParams(v.cls);
  const IdmParams p = idmOf(v);
  const uint32_t* path = pathOf(v.id);

  // Which side does the route need?  path[path_pos+1] is the junction lane; if
  // it does not start from our lane we must move towards the one that does.
  int need_side = 0;
  float pressure = 0.f;
  if (v.path_pos + 1 < v.path_len) {
    const uint32_t jl = path[v.path_pos + 1];
    if (jl != kInvalidIndex && graph_->lane(jl).is_junction != 0 && graph_->lane(jl).from_lane != v.lane) {
      const uint32_t want = graph_->lane(jl).from_lane;
      if (want < graph_->laneCount() && graph_->lane(want).segment == l.segment) {
        need_side = graph_->lane(want).index_from_center < l.index_from_center ? -1 : 1;
        const float d = std::max(0.f, l.length_m - v.s);
        pressure = cfg_.route_pressure_max * clampf(1.f - d / std::max(10.f, cfg_.route_pressure_m), 0.f, 1.f);
      }
    }
  }

  const uint32_t self = i;
  uint32_t chosen = kInvalidIndex;
  float best_adv = 0.f;
  uint8_t chosen_dir = 0;
  for (int side = 0; side < 2; ++side) {
    uint32_t target = side == 0 ? l.left : l.right;
    // A parking-protected bike lane sits behind the parked cars: a cyclist
    // crosses the parking lane at a gap to reach it (nobody else may).
    if (cp.is_bike && target != kInvalidIndex && target < graph_->laneCount() &&
        graph_->lane(target).kind == LaneKind::Parking) {
      const uint32_t beyond = side == 0 ? graph_->lane(target).left : graph_->lane(target).right;
      if (beyond != kInvalidIndex && beyond < graph_->laneCount() &&
          graph_->lane(beyond).kind == LaneKind::Bike)
        target = beyond;
    }
    if (target == kInvalidIndex || target >= graph_->laneCount()) continue;
    if (!graph_->laneAllows(target, cp.lane_kinds)) continue;
    const Lane& tl = graph_->lane(target);
    if (tl.direction != l.direction || tl.segment != l.segment) continue;
    if (v.s > tl.length_m - v.length_m) continue;

    const Neighbour lead_new = leaderIncludingStraddlers(target, v.s, v.length_m * 0.5f, self);
    const Neighbour foll_new = followerIncludingStraddlers(target, v.s, v.length_m * 0.5f, self);
    const Neighbour foll_old = followerInLane(v.lane, v.s, v.length_m * 0.5f, self);
    const Neighbour lead_old = leaderInLane(v.lane, v.s, v.length_m * 0.5f, self);

    MobilInput in;
    in.a_self = a_current;
    in.a_self_new = lead_new.index == kInvalidIndex
                        ? idmFreeAccel(p, v.speed)
                        : idmAccel(p, v.speed, lead_new.gap, v.speed - lead_new.speed);
    in.politeness = cp.politeness > 0.f ? cp.politeness : cfg_.mobil_politeness;
    in.threshold = cfg_.mobil_threshold;
    in.b_safe = cfg_.mobil_b_safe;
    in.gap_front = lead_new.index == kInvalidIndex ? kBigDistance : lead_new.gap;
    in.gap_rear = foll_new.index == kInvalidIndex ? kBigDistance : foll_new.gap;
    in.min_gap_front = cfg_.lc_gap_front_m;
    in.min_gap_rear = cfg_.lc_gap_rear_m;
    if (foll_new.index != kInvalidIndex) {
      const Vehicle& f = veh_[foll_new.index];
      const IdmParams fp = idmOf(f);
      const Neighbour f_lead = leaderInLane(target, f.s, f.length_m * 0.5f, self);
      in.a_new_follower = f_lead.index == kInvalidIndex
                              ? idmFreeAccel(fp, f.speed)
                              : idmAccel(fp, f.speed, f_lead.gap, f.speed - f_lead.speed);
      in.a_new_follower_new = idmAccel(fp, f.speed, foll_new.gap, f.speed - v.speed);
    }
    if (foll_old.index != kInvalidIndex) {
      const Vehicle& f = veh_[foll_old.index];
      const IdmParams fp = idmOf(f);
      in.a_old_follower = idmAccel(fp, f.speed, foll_old.gap, f.speed - v.speed);
      const float gap_after = lead_old.index == kInvalidIndex
                                  ? kBigDistance
                                  : foll_old.gap + v.length_m + lead_old.gap;
      in.a_old_follower_new = lead_old.index == kInvalidIndex
                                  ? idmFreeAccel(fp, f.speed)
                                  : idmAccel(fp, f.speed, gap_after, f.speed - lead_old.speed);
    }

    // Bias terms.
    float bias = 0.f;
    const int this_side = side == 0 ? -1 : 1;
    if (need_side != 0) bias += (this_side == need_side ? pressure : -pressure);
    if (cp.is_bike) {
      // Cyclists work their way towards the bike lane one lane at a time, so
      // the incentive has to reward every step of the way, not only the last.
      int bike_ix = 127;
      uint32_t ns = 0;
      const uint32_t* seg_lanes = graph_->segmentLanes(l.segment, ns);
      for (uint32_t q = 0; q < ns; ++q) {
        const Lane& c = graph_->lane(seg_lanes[q]);
        if (c.kind == LaneKind::Bike && c.direction == l.direction && c.disabled == 0)
          bike_ix = std::min<int>(bike_ix, c.index_from_center);
      }
      if (bike_ix != 127) {
        const int here = std::abs(static_cast<int>(l.index_from_center) - bike_ix);
        const int there = std::abs(static_cast<int>(tl.index_from_center) - bike_ix);
        if (there < here) bias += cfg_.bike_lane_bias;
        if (there > here) bias -= cfg_.bike_lane_bias;
      }
      if (tl.kind == LaneKind::Bike) bias += cfg_.bike_lane_bias;
      if (l.kind == LaneKind::Bike && tl.kind != LaneKind::Bike) bias -= cfg_.bike_lane_bias;
    }
    if (cp.is_bus && tl.kind == LaneKind::Bus) bias += 1.5f;
    if ((v.flags & kVehYieldingEv) != 0 && this_side > 0) bias += 4.f;
    // Keep right only when we are not being held up where we are: a keep-right
    // bias that can cancel the switching threshold makes drivers oscillate.
    if (need_side == 0 && this_side > 0 && tl.kind == LaneKind::Travel && a_current > -0.2f)
      bias += std::min(cfg_.keep_right_bias, cfg_.mobil_threshold * 0.5f);
    in.bias = bias;
    if (pressure > 1.f && this_side == need_side) in.threshold = 0.f;

    const MobilResult r = mobilEvaluate(in);
    if (!r.accept) continue;
    if (laneSlotClaimed(target, v.s, v.length_m * 0.5f)) continue;
    const float adv = r.advantage + bias;
    if (chosen == kInvalidIndex || adv > best_adv) {
      chosen = target;
      best_adv = adv;
      chosen_dir = static_cast<uint8_t>(side == 0 ? 1 : 2);
      // Cut-off honk: the new follower is forced to brake hard.
      if (foll_new.index != kInvalidIndex) {
        const Vehicle& f = veh_[foll_new.index];
        const float closing = f.speed - v.speed;
        if (closing > 0.5f && foll_new.gap / closing < cfg_.honk_ttc_s) emitHonk(f, HonkReason::CutOff);
      }
    }
  }
  if (chosen == kInvalidIndex) return;

  new_lane_[i] = chosen;
  claimLaneSlot(chosen, v.s, v.length_m * 0.5f);
  v.lc_dir = chosen_dir;
  v.lc_cooldown = cfg_.lane_change_cooldown_s;
  ++stats_.lane_changes;
}

// ------------------------------------------------------- New York behaviours
void TrafficSim::considerDoublePark(Vehicle& v) {
  if (v.state != DriveState::Driving) return;
  const VehicleClassParams& cp = classParams(v.cls);
  const float rate = cp.double_park_rate_per_km * cfg_.double_park_scale;
  if (rate <= 0.f) return;
  const Lane& l = graph_->lane(v.lane);
  if (l.is_junction != 0 || l.segment == kInvalidIndex) return;
  const routing::Segment& seg = graph_->segment(l.segment);
  if ((seg.attrs.flags & routing::kSegCommercial) == 0 || seg.attrs.park_lanes == 0) return;
  // Only the curb-side travel lane; the vehicle stops where it is.
  if (l.right != kInvalidIndex && graph_->lane(l.right).kind == LaneKind::Travel) return;
  if (v.s < 12.f || v.s > l.length_m - 12.f) return;
  // Poisson process along the road: P(stop in dt) = rate/km × distance.
  const float p_step = rate * 0.001f * v.speed * cfg_.dt;
  if (!v.rng.chance(p_step)) return;
  // Not right on top of another double-parked vehicle.
  for (const Vehicle& o : veh_) {
    if (o.state != DriveState::DoubleParked) continue;
    const float dx = o.pos.x - v.pos.x, dy = o.pos.y - v.pos.y;
    if (dx * dx + dy * dy < cfg_.double_park_min_gap_m * cfg_.double_park_min_gap_m) return;
  }
  v.state = DriveState::DoubleParked;
  v.state_timer = v.rng.uniform(cfg_.double_park_min_s, cfg_.double_park_max_s);
  v.lateral_target = -(l.width_m * 0.5f - v.width_m * 0.5f - 0.1f);
}

void TrafficSim::considerBusStop(Vehicle& v, float& stop_dist) {
  if (buses_ == nullptr || v.bus_route == 0xFFFFu) return;
  if (v.state == DriveState::BusDwelling) return;
  uint32_t n = 0;
  const uint32_t* stops = buses_->stopsOnLane(v.lane, n);
  if (stops == nullptr) return;
  for (uint32_t k = 0; k < n; ++k) {
    const BusStop& st = buses_->stop(stops[k]);
    const float d = st.s - v.s;
    if (d < -2.f || d > cfg_.bus_stop_zone_m + v.speed * 3.f) continue;
    if (static_cast<uint32_t>(v.bus_stop_ix) == stops[k]) continue;
    // IDM settles s0 short of a stationary obstacle, so the target it is given
    // is the flag pole plus s0; the bus then comes to rest beside the stop.
    stop_dist = std::min(stop_dist, std::max(0.f, d + classParams(v.cls).min_gap_s0));
    if (d < 2.0f && v.speed < 0.5f) {
      v.state = DriveState::BusDwelling;
      v.state_timer = v.rng.uniform(cfg_.bus_dwell_min_s, cfg_.bus_dwell_max_s);
      v.bus_stop_ix = static_cast<uint16_t>(stops[k]);
    }
    return;
  }
}

void TrafficSim::emitHonk(const Vehicle& v, HonkReason r) {
  if (honk_count_ >= cfg_.max_honks_per_step || honk_count_ >= honks_.size()) return;
  HonkEvent& e = honks_[honk_count_++];
  e.x = v.pos.x;
  e.y = v.pos.y;
  e.z = v.pos.z;
  e.agent = v.id;
  e.cls = v.cls;
  e.reason = r;
  ++stats_.honks;
}

// ------------------------------------------------------------------ decide
void TrafficSim::decide(uint32_t i) {
  Vehicle& v = veh_[i];
  const IdmParams p = idmOf(v);
  const VehicleClassParams& cp = classParams(v.cls);
  new_lane_[i] = kInvalidIndex;
  new_swerve_[i] = 0.f;
  new_flags_[i] = 0u;

  // Parked / dwelling states: stand still until the timer expires.
  if (v.state != DriveState::Driving && v.state != DriveState::StoppedAtLine &&
      v.state != DriveState::WaitingRow) {
    new_accel_[i] = v.speed > 0.05f ? -p.b_max : 0.f;
    v.state_timer -= cfg_.dt;
    if (v.state_timer <= 0.f) {
      // Merge back only when there is a gap behind us.
      const Neighbour back = followerInLane(v.lane, v.s, v.length_m * 0.5f, i);
      if (back.index == kInvalidIndex || back.gap > 8.f + veh_[back.index].speed * 1.0f) {
        const bool was_dwelling = v.state == DriveState::BusDwelling;
        v.state = DriveState::Driving;
        v.lateral_target = 0.f;
        v.state_timer = 0.f;
        if (v.cls == VehicleClass::Taxi || v.cls == VehicleClass::BoroTaxi)
          v.flags |= kVehRoofLight;
        if (was_dwelling) advanceBusToNextStop(v);
      } else {
        v.state_timer = 0.5f;
      }
    }
    return;
  }

  float a = idmFreeAccel(p, v.speed);
  const Lane& l = graph_->lane(v.lane);

  // 1. car following along the path
  const Neighbour lead = leaderAhead(v, 140.f);
  if (lead.index != kInvalidIndex)
    a = std::min(a, idmAccel(p, v.speed, lead.gap, v.speed - lead.speed));

  // 2. virtual obstacles → the nearest distance at which we must be stopped
  float stop_dist = kBigDistance;
  bool gate_open = true;
  bool held_by_signal = false;  // waiting for a phase is not "blocked"


  // 2a. turn speed on the junction lane we are on / about to enter
  if (l.is_junction != 0 && l.turn != TurnType::Straight) {
    const float turn_v = curveSpeed(std::max(4.f, l.length_m * 0.55f), kTurnLatAccel);
    if (v.speed > turn_v) a = std::min(a, -std::min(p.b_max, (v.speed - turn_v) / 0.6f));
  }

  const uint32_t jl = nextJunction(v);
  float dist_to_line = kBigDistance;
  if (jl != kInvalidIndex) {
    dist_to_line = std::max(0.f, l.length_m - cfg_.stop_line_setback_m - (v.s + v.length_m * 0.5f));
    const Lane& jlane = graph_->lane(jl);
    const uint32_t node = jlane.node;

    // Slow for the turn ahead.
    if (jlane.turn != TurnType::Straight && dist_to_line < 30.f) {
      const float turn_v = curveSpeed(std::max(4.f, jlane.length_m * 0.55f), kTurnLatAccel);
      if (v.speed > turn_v) {
        const float need = (v.speed * v.speed - turn_v * turn_v) / (2.f * std::max(1.f, dist_to_line + 1.f));
        a = std::min(a, -std::min(p.b_max, need));
      }
    }

    bool entered_on_red = false;
    float signal_stop = kBigDistance;
    const bool signalized = jlane.signal_group >= 0 && signals_->planForNode(node) != kInvalidIndex;
    if (signalized) signal_stop = signalStopDistance(v, jl, dist_to_line, entered_on_red);

    bool may_enter = signal_stop >= kBigDistance;
    if (!may_enter) {
      stop_dist = std::min(stop_dist, signal_stop);
      held_by_signal = true;
    }

    if (may_enter) {
      const routing::Control ctrl = graph_->node(node).control;
      if (!signalized && (ctrl == routing::Control::Stop || ctrl == routing::Control::AllWayStop)) {
        if ((v.flags & kVehStoppedDone) == 0) {
          if (dist_to_line < 2.5f && v.speed < cfg_.stop_speed_mps) {
            v.flags |= kVehStoppedDone;
            v.dwell_timer = cfg_.stop_dwell_s;
          }
          may_enter = false;
        } else if (v.dwell_timer > 0.f) {
          v.dwell_timer -= cfg_.dt;
          may_enter = false;
        } else {
          may_enter = stopSignPriority(v, node, jl);
        }
      } else if (!signalized && ctrl == routing::Control::Yield) {
        may_enter = gapAccepted(v, jl, criticalGap(jlane, false));
      }
      // Explicit yield list (permissive left, minor movements) always applies.
      uint32_t ny = 0;
      graph_->yieldTo(jl, ny);
      if (may_enter && ny > 0) {
        const bool major = jlane.turn == TurnType::Left && signalized;
        may_enter = gapAccepted(v, jl, criticalGap(jlane, major));
      }
      if (may_enter && !junctionClear(v, jl)) may_enter = false;
      if (may_enter && !exitSpaceAvailable(v, jl)) {
        // Box blocking: probability rises with the local congestion level.
        const float occ = laneOccupancyAhead(graph_->lane(jl).to_lane, 0.f, 60.f);
        const float pb = clampf(cfg_.box_block_p_free + (cfg_.box_block_p_jam - cfg_.box_block_p_free) * occ,
                                0.f, 1.f);
        if ((v.flags & kVehBlockedBox) != 0 || v.rng.chance(pb * cfg_.dt * 4.f)) {
          v.flags |= kVehBlockedBox;
          ++stats_.box_blocks;
        } else {
          may_enter = false;
        }
      }
      if (may_enter && dist_to_line < 25.f && pedestrianConstraint(v, jl, dist_to_line) <= dist_to_line + 0.01f)
        may_enter = false;  // somebody is in a crossing we would drive over
      if (may_enter) lockJunction(v, jl);
      if (!may_enter) stop_dist = std::min(stop_dist, dist_to_line);
    }
    gate_open = may_enter;
    if (entered_on_red && dist_to_line < 1.5f) ++stats_.red_light_entries;
    if (!may_enter && v.speed < 0.5f && dist_to_line < 3.f)
      v.state = signalized ? DriveState::StoppedAtLine : DriveState::WaitingRow;
    else if (v.state != DriveState::Driving)
      v.state = DriveState::Driving;
  } else if (v.state != DriveState::Driving) {
    v.state = DriveState::Driving;
  }

  // 2b. pedestrians in front of us (crossings, the box, jaywalkers)
  stop_dist = std::min(stop_dist, pedestrianConstraint(v, jl, dist_to_line));

  // 2c. deadlock breaker: a vehicle stuck inside the intersection creeps out.
  if (l.is_junction != 0) {
    lockJunction(v, v.lane);  // hold the crossing until we are out of it
    v.junction_time += cfg_.dt;
    if (v.junction_time > cfg_.box_stuck_release_s) stop_dist = kBigDistance;
  }

  // 2c. bus stop
  considerBusStop(v, stop_dist);

  // 2d. emergency vehicles (field computed once per step by updateEmergencyField)
  const float ev = ev_limit_[i];
  if (ev < kBigDistance) {
    stop_dist = std::min(stop_dist, ev);
    new_swerve_[i] = -1.4f;  // pull to the right
  }

  // 2e. the player
  float swerve = 0.f;
  bool brake_hard = false;
  const float pl = playerConstraint(v, swerve, brake_hard);
  if (pl < kBigDistance) stop_dist = std::min(stop_dist, pl);
  if (swerve != 0.f) new_swerve_[i] = swerve;
  if (brake_hard) {
    a = -p.b_max;
    if (v.honk_cooldown <= 0.f && v.rng.chance(classParams(v.cls).honk_propensity)) {
      emitHonk(v, HonkReason::Player);
      v.honk_cooldown = cfg_.honk_cooldown_s;
    }
  }

#ifdef NYCSIM_TRAFFIC_TRACE
  if (std::getenv("NYCSIM_TRACE") != nullptr && v.id == static_cast<uint32_t>(atoi(std::getenv("NYCSIM_TRACE")))) {
    std::printf("    trace id=%u v=%.2f v0=%.2f a_before=%.2f stop=%.2f lead=%d leadgap=%.2f jl=%u turn=%d gate=%d\n",
                v.id, static_cast<double>(v.speed), static_cast<double>(v.v0), static_cast<double>(a),
                static_cast<double>(stop_dist), static_cast<int>(lead.index != kInvalidIndex),
                static_cast<double>(lead.gap), jl,
                jl != kInvalidIndex ? static_cast<int>(graph_->lane(jl).turn) : -1,
                static_cast<int>(gate_open));
  }
#endif
  if (stop_dist < kBigDistance) a = std::min(a, idmStopAccel(p, v.speed, stop_dist));
  a = clampf(a, -p.b_max, p.a);
  new_accel_[i] = a;
  if (gate_open) new_flags_[i] |= 1u;

  // 3. lateral
  considerLaneChange(i, a);
  considerDoublePark(v);

  // 4. honking: blocked for longer than the patience threshold.  Waiting for a
  // red is not being blocked — a New Yorker leans on the horn when the light is
  // green and the car in front has not moved, not while it is still red.
  const bool blocked = v.speed < 0.7f && !held_by_signal &&
                       (lead.index != kInvalidIndex ? lead.gap < 12.f : stop_dist < 12.f);
  if (blocked) {
    v.blocked_time += cfg_.dt;
  } else {
    v.blocked_time = 0.f;
  }
  if (v.blocked_time > cfg_.honk_blocked_s && v.honk_cooldown <= 0.f) {
    if (v.rng.chance(cp.honk_propensity)) emitHonk(v, HonkReason::Blocked);
    v.honk_cooldown = cfg_.honk_cooldown_s;
  }

  // 5. re-route when hopelessly stuck
  if (v.blocked_time > cfg_.reroute_block_s && v.reroute_cooldown <= 0.f && (v.flags & kVehHasRoute) != 0) {
    v.reroute_cooldown = cfg_.reroute_cooldown_s;
    if (pending_routes_.size() < pending_routes_.capacity()) pending_routes_.push_back(v.id);
  }
}

// --------------------------------------------------------------- integrate
void TrafficSim::integrate(uint32_t i) {
  Vehicle& v = veh_[i];
  const VehicleClassParams& cp = classParams(v.cls);
  const float dt = cfg_.dt;
  v.accel = new_accel_[i];
  v.speed += v.accel * dt;
  if (v.speed < 0.f) v.speed = 0.f;
  const float vmax = cp.max_speed_mps;
  if (v.speed > vmax) v.speed = vmax;
  v.flags = static_cast<uint8_t>(v.accel < -0.6f ? (v.flags | kVehBrake) : (v.flags & ~kVehBrake));

  // Lane change: commit the longitudinal position to the new lane, animate the
  // lateral offset from the old lane centre.
  if (new_lane_[i] != kInvalidIndex) {
    const Lane& from = graph_->lane(v.lane);
    const uint32_t to = new_lane_[i];
    const Lane& tol = graph_->lane(to);
    const float offset = static_cast<float>(tol.index_from_center - from.index_from_center) *
                         (from.width_m + tol.width_m) * 0.5f;
    v.lateral += offset;  // + is left of travel, index grows to the curb
    v.s = clampf(v.s, 0.f, tol.length_m - 0.01f);
    v.lc_from = v.lane;
    v.lane = to;
    uint32_t* path = pathOf(v.id);
    path[v.path_pos] = to;
    // Re-link the tail: keep the route if a junction lane connects the new lane
    // to the same receiving lane, otherwise wander and ask for a re-route.
    bool relinked = false;
    if (v.path_pos + 2 < v.path_len) {
      const uint32_t next_road = path[v.path_pos + 2];
      uint32_t j = graph_->junctionBetween(to, next_road);
      if (j == kInvalidIndex && next_road < graph_->laneCount()) {
        // The route continues on that street but through a different lane of
        // it: splice in whichever connector reaches the same segment, rather
        // than throwing the whole route away and asking the router again (a
        // re-route per lane change is by far the most expensive thing the
        // simulation can do).
        const uint32_t want_seg = graph_->lane(next_road).segment;
        const int8_t want_dir = graph_->lane(next_road).direction;
        uint32_t ns = 0;
        const uint32_t* succ = graph_->successors(to, ns);
        for (uint32_t k = 0; k < ns; ++k) {
          const Lane& cand = graph_->lane(succ[k]);
          if (cand.is_junction == 0 || cand.to_lane == kInvalidIndex) continue;
          const Lane& dest = graph_->lane(cand.to_lane);
          if (dest.segment != want_seg || dest.direction != want_dir) continue;
          if (!graph_->laneAllows(succ[k], cp.lane_kinds) || !graph_->laneAllows(cand.to_lane, cp.lane_kinds))
            continue;
          j = succ[k];
          break;
        }
        if (j != kInvalidIndex) path[v.path_pos + 2] = graph_->lane(j).to_lane;
      }
      if (j != kInvalidIndex) {
        path[v.path_pos + 1] = j;
        relinked = true;
      }
    }
    if (!relinked) {
      v.path_len = v.path_pos + 1;
      if ((v.flags & kVehHasRoute) != 0 && pending_routes_.size() < pending_routes_.capacity())
        pending_routes_.push_back(v.id);
      extendPath(v);
    }
  }

  const float ds = v.speed * dt;
  v.s += ds;
  v.distance_m += ds;

  // Hard stop-line barrier: an agent that was told not to enter the junction
  // never crosses it, whatever the numerical integration says.
  if ((new_flags_[i] & 1u) == 0) {
    const Lane& l = graph_->lane(v.lane);
    if (l.is_junction == 0) {
      const float limit = l.length_m - cfg_.stop_line_setback_m - v.length_m * 0.5f;
      if (v.s > limit) {
        v.s = limit;
        v.speed = 0.f;
      }
    }
  }

  // Lateral animation.
  float target = v.lateral_target + new_swerve_[i];
  if (new_lane_[i] == kInvalidIndex && v.state == DriveState::Driving && new_swerve_[i] == 0.f)
    target = v.lateral_target;
  const float rate = cfg_.lateral_rate_mps * dt;
  if (v.lateral < target - rate) {
    v.lateral += rate;
  } else if (v.lateral > target + rate) {
    v.lateral -= rate;
  } else {
    v.lateral = target;
    if (v.lc_dir != 0) v.lc_dir = 0;
    v.lc_from = kInvalidIndex;
  }
  if (std::fabs(v.lateral) < 0.35f || v.lc_from == v.lane) v.lc_from = kInvalidIndex;

  v.honk_cooldown = std::max(0.f, v.honk_cooldown - dt);
  v.lc_cooldown = std::max(0.f, v.lc_cooldown - dt);
  v.reroute_cooldown = std::max(0.f, v.reroute_cooldown - dt);
  if (v.state == DriveState::Driving) v.state_timer += dt;
}

// Hard non-overlap constraint along each lane, applied after integration in the
// step-start order (vehicles do not overtake inside a lane, so that order still
// holds).  IDM is collision-free in exact arithmetic; this makes it so at a
// 50 ms step as well, and absorbs the one case IDM cannot see — two agents
// changing into the same gap from opposite sides in the same step.
void TrafficSim::laneClamp() {
  uint32_t k = 0;
  while (k < order_keys_.size()) {
    const uint32_t lane = static_cast<uint32_t>(order_keys_[k] >> 40);
    uint32_t end = k;
    while (end < order_keys_.size() && static_cast<uint32_t>(order_keys_[end] >> 40) == lane) ++end;
    // Walk from the front of the lane backwards.
    for (uint32_t j = end; j > k + 1; --j) {
      Vehicle& lead = veh_[keyIndex(order_keys_[j - 1])];
      Vehicle& foll = veh_[keyIndex(order_keys_[j - 2])];
      if (lead.lane != lane || foll.lane != lane) continue;  // changed lane this step
      const float limit = lead.s - lead.length_m * 0.5f - foll.length_m * 0.5f - 0.05f;
      if (foll.s > limit) {
        foll.s = limit;
        if (foll.speed > lead.speed) foll.speed = lead.speed;
      }
      if (foll.s < 0.f) foll.s = 0.f;
    }
    k = end;
  }
}

void TrafficSim::resolveOverlaps(bool cross_lane) {
  laneClamp();
  if (!cross_lane) return;
  // Across a lane boundary: the leader may already be on the next lane of the
  // path (entering a junction, leaving one).  leaderAhead() follows the path,
  // so one deficit correction per agent closes that case too.
  for (uint32_t i = 0; i < veh_.size(); ++i) {
    Vehicle& v = veh_[i];
    const Neighbour ld = leaderAhead(v, 30.f);
    if (ld.index == kInvalidIndex || ld.gap >= 0.05f) continue;
    v.s += ld.gap - 0.05f;
    if (v.s < 0.f) v.s = 0.f;
    if (v.speed > ld.speed) v.speed = ld.speed;
  }
  // …and against the agents that are only laterally in this lane.
  for (uint32_t i = 0; i < veh_.size(); ++i) {
    Vehicle& v = veh_[i];
    if (v.lane >= straddle_stamp_.size() || straddle_stamp_[v.lane] != stamp_) continue;
    const Neighbour ld = leaderIncludingStraddlers(v.lane, v.s, v.length_m * 0.5f, i);
    if (ld.index == kInvalidIndex || ld.gap >= 0.05f) continue;
    v.s += ld.gap - 0.05f;
    if (v.s < 0.f) v.s = 0.f;
    if (v.speed > ld.speed) v.speed = ld.speed;
  }
  // A vehicle that is changing lanes still physically occupies the lane it is
  // leaving until the lateral animation finishes.
  for (uint32_t i = 0; i < veh_.size(); ++i) {
    Vehicle& v = veh_[i];
    if (v.lc_from == kInvalidIndex || v.lc_from >= graph_->laneCount()) continue;
    const float half = v.length_m * 0.5f;
    const Neighbour ld = leaderIncludingStraddlers(v.lc_from, v.s, half, i);
    if (ld.index != kInvalidIndex && ld.gap < 0.05f) {
      v.s += ld.gap - 0.05f;
      if (v.s < 0.f) v.s = 0.f;
      if (v.speed > ld.speed) v.speed = ld.speed;
    }
    const Neighbour fl = followerIncludingStraddlers(v.lc_from, v.s, half, i);
    if (fl.index != kInvalidIndex && fl.gap < 0.05f) {
      Vehicle& f = veh_[fl.index];
      f.s += fl.gap - 0.05f;
      if (f.s < 0.f) f.s = 0.f;
      if (f.speed > v.speed) f.speed = v.speed;
    }
  }
  laneClamp();
}

namespace {
// Penetration depth of two oriented boxes along the separating axes; ≤ 0 when
// they are apart.
// Half-extent of a vehicle's box projected on the unit axis (nx,ny).
float boxRadiusOn(const Vehicle& v, float nx, float ny) {
  const float hx = std::cos(v.heading_rad), hy = std::sin(v.heading_rad);
  return v.length_m * 0.5f * std::fabs(hx * nx + hy * ny) +
         v.width_m * 0.5f * std::fabs(-hy * nx + hx * ny);
}

// How far `mover` has to travel backwards along its own heading before its box
// clears `other`'s.  For a rear-end overlap this is the penetration depth; for
// two bodies side by side it is the whole longitudinal clearance, which is the
// case a penetration-depth push cannot resolve.
float clearanceAlongHeading(const Vehicle& mover, const Vehicle& other) {
  const float nx = std::cos(mover.heading_rad), ny = std::sin(mover.heading_rad);
  const float dx = other.pos.x - mover.pos.x, dy = other.pos.y - mover.pos.y;
  const float need = boxRadiusOn(mover, nx, ny) + boxRadiusOn(other, nx, ny) - std::fabs(dx * nx + dy * ny);
  return need > 0.f ? need : 0.f;
}

float boxPenetration(const Vehicle& a, const Vehicle& b) {
  const float ax = std::cos(a.heading_rad), ay = std::sin(a.heading_rad);
  const float bx = std::cos(b.heading_rad), by = std::sin(b.heading_rad);
  const float ahl = a.length_m * 0.5f, ahw = a.width_m * 0.5f;
  const float bhl = b.length_m * 0.5f, bhw = b.width_m * 0.5f;
  const float dx = b.pos.x - a.pos.x, dy = b.pos.y - a.pos.y;
  const float axes[4][2] = {{ax, ay}, {-ay, ax}, {bx, by}, {-by, bx}};
  float least = 1e9f;
  for (int i = 0; i < 4; ++i) {
    const float nx = axes[i][0], ny = axes[i][1];
    const float ra = ahl * std::fabs(ax * nx + ay * ny) + ahw * std::fabs(-ay * nx + ax * ny);
    const float rb = bhl * std::fabs(bx * nx + by * ny) + bhw * std::fabs(-by * nx + bx * ny);
    const float sep = ra + rb - std::fabs(dx * nx + dy * ny);
    if (sep <= 0.f) return 0.f;
    least = std::min(least, sep);
  }
  return least;
}
}  // namespace

// Impenetrability. The longitudinal model keeps agents apart inside a lane and
// along a path, but two cases are outside its frame: a body that straddles two
// lanes for the two seconds a lane change takes, and two bodies on connectors
// that cross inside a junction. This pass works on the rendered poses, so it
// closes both: whichever agent is behind gives way along its own lane. Bounded
// to 1 m per step so it never shows as a jump.
uint32_t TrafficSim::separateBodies() {
  const uint32_t n = static_cast<uint32_t>(veh_.size());
  uint32_t moved = 0;
  for (uint32_t i = 0; i < n; ++i) {
    const float reach = veh_[i].length_m * 0.5f + 6.5f;
    hash_.query(veh_[i].pos.x, veh_[i].pos.y, reach, [&](uint32_t j) {
      if (j <= i || j >= veh_.size()) return;
      Vehicle& a = veh_[i];
      Vehicle& b = veh_[j];
      const float pen = boxPenetration(a, b);
      if (pen <= 0.f) return;
      // The one whose own heading points at the other is behind, so it yields.
      const float dx = b.pos.x - a.pos.x, dy = b.pos.y - a.pos.y;
      const float a_ahead = dx * std::cos(a.heading_rad) + dy * std::sin(a.heading_rad);
      (void)pen;
      // Give way with whichever of the two can: an agent pinned at the start of
      // its first lane has nowhere to go, and then the other one moves instead.
      auto giveWay = [&](Vehicle& mover, const Vehicle& other) {
        const float back = std::min(clearanceAlongHeading(mover, other) + 0.05f, 2.5f);
        if (back <= 0.05f) return false;
        float s_new = mover.s - back;
        uint32_t new_lane = mover.lane;
        if (s_new < 0.f) {
          // Nowhere left on this lane: step back onto the one we came from, but
          // only into space that is free there.
          uint32_t* mpath = pathOf(mover.id);
          if (mover.path_pos == 0 || mpath[mover.path_pos - 1] >= graph_->laneCount()) return false;
          new_lane = mpath[mover.path_pos - 1];
          const float deficit = -s_new;
          s_new = std::max(0.f, graph_->lane(new_lane).length_m - deficit);
          const Neighbour behind =
              followerInLane(new_lane, s_new, mover.length_m * 0.5f, indexOfId(mover.id));
          const Neighbour front = leaderInLane(new_lane, s_new, mover.length_m * 0.5f, indexOfId(mover.id));
          if ((behind.index != kInvalidIndex && behind.gap < 0.1f) ||
              (front.index != kInvalidIndex && front.gap < 0.1f))
            return false;
          --mover.path_pos;
          mover.lane = new_lane;
          mover.junction_time = 0.f;
        }
        mover.s = s_new;
        if (mover.speed > other.speed) mover.speed = other.speed;
        updatePose(mover);
        return true;
      };
      bool ok = a_ahead > 0.f ? (giveWay(a, b) || giveWay(b, a)) : (giveWay(b, a) || giveWay(a, b));
      if (!ok) {
        // Both are wedged — typically one nosing into a junction with the queue
        // right behind it.  Edge them apart sideways instead, which is what a
        // driver does in that situation and which nothing else constrains.
        const float nx = -std::sin(a.heading_rad), ny = std::cos(a.heading_rad);  // a's left
        const float sep = boxRadiusOn(a, nx, ny) + boxRadiusOn(b, nx, ny) -
                          std::fabs(dx * nx + dy * ny);
        if (sep > 0.f) {
          // Only `a` is moved: `b`'s lateral is expressed in its own lane frame,
          // which points the other way when the two are travelling in opposite
          // directions, and a sign mistake there would push them together.
          const float shift = std::min(sep + 0.05f, 0.5f);
          const float side = (dx * nx + dy * ny) >= 0.f ? -1.f : 1.f;  // away from b
          const float before = a.lateral;
          a.lateral = clampf(a.lateral + side * shift, -2.5f, 2.5f);
          if (a.lateral != before) {
            updatePose(a);
            ok = true;
          }
        }
      }
      if (ok) ++moved;
    });
  }
  return moved;
}

void TrafficSim::updatePose(Vehicle& v) {
  const routing::LanePose pose = graph_->poseAt(v.lane, v.s, v.lateral);
  v.pos = pose.pos;
  v.heading_rad = pose.heading_rad;
}

// ---------------------------------------------------------------- spawning
bool TrafficSim::laneFreeAt(uint32_t lane, float s, float len) const {
  if (lane < straddle_stamp_.size() && straddle_stamp_[lane] == stamp_) {
    for (uint32_t k = straddle_head_[lane]; k != kInvalidIndex; k = straddle_next_[k]) {
      const Vehicle& o = veh_[k];
      if (std::fabs(o.s - s) < (o.length_m + len) * 0.5f + cfg_.spawn_headway_m) return false;
    }
  }
  if (lane >= lane_stamp_.size() || lane_stamp_[lane] != stamp_) return true;
  const uint32_t first = lane_first_[lane], count = lane_num_[lane];
  for (uint32_t k = 0; k < count; ++k) {
    const Vehicle& o = veh_[keyIndex(order_keys_[first + k])];
    if (std::fabs(o.s - s) < (o.length_m + len) * 0.5f + cfg_.spawn_headway_m) return false;
  }
  return true;
}

// Cyclists belong in the bike lane and buses in the bus lane when the segment
// has one; the OD sampler only ever picks travel lanes.
uint32_t TrafficSim::preferredLaneFor(uint32_t lane, VehicleClass c) const {
  const VehicleClassParams& cp = classParams(c);
  if (!cp.is_bike && !cp.is_bus) return lane;
  const uint32_t seg = graph_->lane(lane).segment;
  if (seg == kInvalidIndex) return lane;
  const int8_t dir = graph_->lane(lane).direction;
  uint32_t n = 0;
  const uint32_t* lanes = graph_->segmentLanes(seg, n);
  const LaneKind want = cp.is_bike ? LaneKind::Bike : LaneKind::Bus;
  for (uint32_t k = 0; k < n; ++k) {
    const Lane& cand = graph_->lane(lanes[k]);
    if (cand.direction != dir || cand.kind != want || cand.disabled != 0) continue;
    return lanes[k];
  }
  return lane;
}

uint32_t TrafficSim::sampleOriginLane(Rng& rng) {
  return spawn_index_.sample(origin_region_, rng.uniform());
}

uint32_t TrafficSim::sampleDestLane(Rng& rng) {
  return spawn_index_.sample(dest_region_, rng.uniform());
}

VehicleClass TrafficSim::sampleClass(Rng& rng, uint16_t nta) const {
  DensityCell c;
  if (density_ != nullptr && nta != routing::kNoNta) {
    c = density_->get(nta, static_cast<uint8_t>(clampf(tod_s_ / 3600.f, 0.f, 23.f)), dow_);
  } else {
    // Default NYC mix when no calibration table is attached (see REPORT.md).
    c.taxi_share = 0.15f;
    c.truck_share = 0.08f;
    c.bus_share = 0.02f;
    c.bike_share = 0.05f;
  }
  const float u = rng.uniform();
  float acc = c.taxi_share;
  if (u < acc) return rng.chance(0.7f) ? VehicleClass::Taxi : VehicleClass::BoroTaxi;
  acc += c.truck_share;
  if (u < acc) {
    const float t = rng.uniform();
    if (t < 0.45f) return VehicleClass::BoxTruck;
    if (t < 0.85f) return VehicleClass::Van;
    return VehicleClass::DsnyTruck;
  }
  acc += c.bus_share;
  if (u < acc) return VehicleClass::MtaBus;
  acc += c.bike_share;
  if (u < acc) {
    const float t = rng.uniform();
    if (t < 0.55f) return VehicleClass::Cyclist;
    if (t < 0.9f) return VehicleClass::Ebike;
    return VehicleClass::Moped;
  }
  const float t = rng.uniform();
  if (t < 0.55f) return VehicleClass::Sedan;
  if (t < 0.85f) return VehicleClass::Suv;
  if (t < 0.95f) return VehicleClass::BlackCar;
  return VehicleClass::Nypd;
}

uint32_t TrafficSim::spawn(VehicleClass c, uint32_t lane, float s, uint32_t dest_lane, float dest_s,
                           bool ignore_player_ring) {
  if (graph_ == nullptr || free_ids_.empty() || lane >= graph_->laneCount()) {
    ++stats_.spawn_failures;
    return kInvalidIndex;
  }
  const Lane& l = graph_->lane(lane);
  const VehicleClassParams& cp = classParams(c);
  if (!graph_->laneAllows(lane, cp.lane_kinds)) {
    ++stats_.spawn_failures;
    return kInvalidIndex;
  }
  s = clampf(s, 0.f, std::max(0.01f, l.length_m - 0.01f));
  const routing::LanePose pose = graph_->poseAt(lane, s);
  if (!ignore_player_ring && inProtectedRegion(pose.pos.x, pose.pos.y)) {
    ++stats_.spawn_failures;
    return kInvalidIndex;
  }

  const uint32_t id = free_ids_.back();
  free_ids_.pop_back();
  Vehicle v;
  v.id = id;
  v.cls = c;
  v.lane = lane;
  v.s = s;
  v.length_m = cp.length_m;
  v.width_m = cp.width_m;
  v.rng.reseed(seed_ ^ (0x9E3779B97F4A7C15ull * (static_cast<uint64_t>(id) + 1u) + next_id_));
  ++next_id_;
  const float posted = l.speed_mps > 0.5f ? l.speed_mps : 11.176f;
  v.v0 = std::min(cp.max_speed_mps, posted * cp.desired_speed_factor * v.rng.normalClamped(1.f, 0.08f, 0.8f, 1.25f));
  if (v.rng.chance(cp.law_abiding_share)) v.flags |= kVehLawAbiding;
  if (cp.is_emergency && v.rng.chance(0.35f)) {
    v.flags |= kVehSiren;
    v.v0 = std::min(cp.max_speed_mps, v.v0 * cfg_.emergency_speed_factor);
  }
  if (cp.is_taxi && v.rng.chance(cfg_.taxi_free_share)) v.flags |= kVehRoofLight;
  v.speed = std::min(v.v0, posted * 0.7f);
  v.spawn_time = static_cast<float>(time_s_);
  v.pos = pose.pos;
  v.heading_rad = pose.heading_rad;

  veh_.push_back(v);
  const uint32_t slot = static_cast<uint32_t>(veh_.size() - 1);
  slot_of_id_[id] = slot;
  Vehicle& nv = veh_[slot];
  uint32_t* path = pathOf(id);
  path[0] = lane;
  nv.path_len = 1;
  nv.path_pos = 0;
  // Routing is budgeted like everything else: an agent that cannot be routed in
  // this step drives on its wander path and picks its route up within a second.
  if (dest_lane != kInvalidIndex && router_ != nullptr && router_->attached() &&
      routes_this_step_ < cfg_.max_routes_per_step) {
    ++routes_this_step_;
    if (!routeAgent(nv, dest_lane, dest_s)) extendPath(nv);
  } else {
    extendPath(nv);
    if (dest_lane != kInvalidIndex) {
      nv.dest_lane = dest_lane;
      nv.dest_s = dest_s;
      if (pending_routes_.size() < pending_routes_.capacity()) pending_routes_.push_back(id);
    }
  }
  if (cp.is_bus) assignBusRoute(nv);
  ++stats_.spawned;
  return id;
}

bool TrafficSim::despawn(uint32_t id, bool ignore_player_ring) {
  const uint32_t slot = indexOfId(id);
  if (slot == kInvalidIndex) return false;
  Vehicle& v = veh_[slot];
  if (!ignore_player_ring && inProtectedRegion(v.pos.x, v.pos.y)) return false;
  releaseClaim(v);
  const uint32_t last = static_cast<uint32_t>(veh_.size() - 1);
  if (slot != last) {
    veh_[slot] = veh_[last];
    slot_of_id_[veh_[slot].id] = slot;
  }
  veh_.pop_back();
  slot_of_id_[id] = kInvalidIndex;
  free_ids_.push_back(id);
  ++stats_.despawned;
  return true;
}

void TrafficSim::updateSpawnDespawn() {
  // Despawn: arrived, or too far from the player, and outside the ring.
  for (uint32_t i = 0; i < veh_.size();) {
    Vehicle& v = veh_[i];
    bool remove = false;
    if ((v.flags & kVehHasRoute) != 0 && v.bus_route == 0xFFFFu && v.lane == v.dest_lane &&
        v.s >= v.dest_s - 0.5f)
      remove = true;
    if (v.exit_now != 0) remove = true;
    if (!remove && player_.valid && cfg_.use_player_ring) {
      const float dx = v.pos.x - player_.x, dy = v.pos.y - player_.y;
      if (dx * dx + dy * dy > cfg_.despawn_m * cfg_.despawn_m) remove = true;
    }
    if (remove && despawn(v.id)) continue;  // veh_[i] is now a different agent
    if (remove) {
      // Inside the protected region: keep it alive and let it wander on.
      v.flags &= static_cast<uint8_t>(~kVehHasRoute);
      v.dest_lane = kInvalidIndex;
      extendPath(v);
      if (v.path_pos + 1 < v.path_len) v.exit_now = 0;
    }
    ++i;
  }

  // Spawn towards the density target.
  float target = 0.f;
  if (density_ != nullptr) {
    const uint8_t hour = static_cast<uint8_t>(clampf(tod_s_ / 3600.f, 0.f, 23.f));
    for (uint16_t nta = 0; nta < density_->ntaCount() && nta < nta_lane_km_.size(); ++nta)
      target += nta_lane_km_[nta] * density_->get(nta, hour, dow_).veh_per_km_lane;
  }
  stats_.target_vehicles = target;
  if (density_ == nullptr) return;

  // Above target (the table dropped, or the hour changed): retire agents at the
  // same rate the spawner uses, always outside the player's protected region.
  if (fz(veh_.size()) > target + 1.f) {
    retire_credit_ += cfg_.spawn_rate_per_s * cfg_.dt;
    while (retire_credit_ >= 1.f && fz(veh_.size()) > target) {
      retire_credit_ -= 1.f;
      bool done = false;
      for (uint32_t k = 0; k < veh_.size() && !done; ++k) {
        retire_cursor_ = (retire_cursor_ + 1u) % static_cast<uint32_t>(veh_.size());
        const Vehicle& v = veh_[retire_cursor_];
        if (v.state != DriveState::Driving) continue;  // never mid-manoeuvre
        done = despawn(v.id);
      }
      if (!done) break;
    }
  } else {
    retire_credit_ = 0.f;
  }

  spawn_credit_ += cfg_.spawn_rate_per_s * cfg_.dt;
  while (spawn_credit_ >= 1.f) {
    spawn_credit_ -= 1.f;
    if (fz(veh_.size()) >= target || veh_.size() >= cfg_.max_vehicles) break;
    bool done = false;
    for (int attempt = 0; attempt < 6 && !done; ++attempt) {
      const uint32_t lane = sampleOriginLane(rng_);
      if (lane == kInvalidIndex) return;
      const Lane& l = graph_->lane(lane);
      const float s = rng_.uniform(2.f, std::max(3.f, l.length_m - 2.f));
      const routing::LanePose pose = graph_->poseAt(lane, s);
      if (inProtectedRegion(pose.pos.x, pose.pos.y)) continue;
      if (player_.valid && cfg_.use_player_ring) {
        const float dx = pose.pos.x - player_.x, dy = pose.pos.y - player_.y;
        if (dx * dx + dy * dy > cfg_.spawn_outer_m * cfg_.spawn_outer_m) continue;
      }
      const VehicleClass c = sampleClass(rng_, l.nta);
      const uint32_t use_lane = preferredLaneFor(lane, c);
      if (!graph_->laneAllows(use_lane, classParams(c).lane_kinds)) continue;
      if (!laneFreeAt(use_lane, s, classParams(c).length_m)) continue;
      uint32_t dest = kInvalidIndex;
      float dest_s = 0.f;
      if (router_ != nullptr && router_->attached() && routes_this_step_ < cfg_.max_routes_per_step) {
        dest = sampleDestLane(rng_);
        if (dest != kInvalidIndex) {
          dest_s = graph_->lane(dest).length_m * 0.5f;
          ++routes_this_step_;
        }
      }
      done = spawn(c, use_lane, s, dest, dest_s) != kInvalidIndex;
    }
    if (!done) ++stats_.spawn_failures;
  }
}

uint32_t TrafficSim::prefill(uint32_t max_spawns) {
  if (graph_ == nullptr || density_ == nullptr) return 0;
  const uint8_t hour = static_cast<uint8_t>(clampf(tod_s_ / 3600.f, 0.f, 23.f));
  float target = 0.f;
  for (uint16_t nta = 0; nta < density_->ntaCount() && nta < nta_lane_km_.size(); ++nta)
    target += nta_lane_km_[nta] * density_->get(nta, hour, dow_).veh_per_km_lane;
  stats_.target_vehicles = target;
  rebuildIndex();
  refreshSpawnRegions();
  uint32_t made = 0;
  uint32_t attempts = 0;
  const uint32_t want = std::min<uint32_t>(static_cast<uint32_t>(std::max(0.f, target)), cfg_.max_vehicles);
  while (veh_.size() < want && made < max_spawns && attempts < want * 24u + 4096u) {
    ++attempts;
    const uint32_t lane = sampleOriginLane(rng_);
    if (lane == kInvalidIndex) break;
    const Lane& l = graph_->lane(lane);
    const float s = rng_.uniform(2.f, std::max(3.f, l.length_m - 2.f));
    const routing::LanePose pose = graph_->poseAt(lane, s);
    if (inProtectedRegion(pose.pos.x, pose.pos.y)) continue;
    // The spawn band, exactly as the steady-state spawner applies it: the index
    // restricts the draw, this decides it.  Before ADR-021 prefill() filled the
    // whole city and the ring kept 86 of 6,000 vehicles.
    if (player_.valid && cfg_.use_player_ring) {
      const float dx = pose.pos.x - player_.x, dy = pose.pos.y - player_.y;
      if (dx * dx + dy * dy > cfg_.spawn_outer_m * cfg_.spawn_outer_m) continue;
    }
    const VehicleClass c = sampleClass(rng_, l.nta);
    const uint32_t use_lane = preferredLaneFor(lane, c);
    if (!graph_->laneAllows(use_lane, classParams(c).lane_kinds)) continue;
    if (!laneFreeAt(use_lane, s, classParams(c).length_m)) continue;
    uint32_t dest = kInvalidIndex;
    float dest_s = 0.f;
    if (router_ != nullptr && router_->attached()) {
      dest = sampleDestLane(rng_);
      if (dest != kInvalidIndex) dest_s = graph_->lane(dest).length_m * 0.5f;
    }
    if (spawn(c, use_lane, s, dest, dest_s) != kInvalidIndex) {
      ++made;
      rebuildIndex();
    }
  }
  return made;
}

// -------------------------------------------------------------------- step
void TrafficSim::step() {
  if (graph_ == nullptr) return;
  honk_count_ = 0;
  routes_this_step_ = 0;
  time_s_ += static_cast<double>(cfg_.dt);
  tod_s_ += cfg_.dt;
  if (tod_s_ >= 86400.f) tod_s_ -= 86400.f;
  const uint8_t hour = static_cast<uint8_t>(tod_s_ / 3600.f);
  if (hour != spawn_hour_) rebuildSpawnWeights();
  refreshSpawnRegions();
  if (signals_ != nullptr) const_cast<SignalTable*>(signals_)->cacheStates(time_s_);

  rebuildIndex();
  updateEmergencyField();

  const uint32_t n = static_cast<uint32_t>(veh_.size());
  for (uint32_t i = 0; i < n; ++i) decide(i);
  for (uint32_t i = 0; i < n; ++i) integrate(i);
  resolveOverlaps(false);
  for (uint32_t i = 0; i < n; ++i) {
    Vehicle& v = veh_[i];
    if (!advanceLane(v)) {
      // Reached the destination: handled by updateSpawnDespawn().
      v.s = std::min(v.s, graph_->lane(v.lane).length_m);
      v.speed = 0.f;
    }
  }
  // Lane changes and junction entries move agents between lanes; re-sort and
  // apply the non-overlap constraint again on the lanes they ended up in.
  buildOrder();
  resolveOverlaps(true);
  for (uint32_t i = 0; i < n; ++i) updatePose(veh_[i]);
  // Impenetrability, relaxed against the final poses until nothing moves
  // (giving way to one neighbour can bring an agent up against another).  This
  // is the last thing in the step that touches a position, so nothing can
  // reintroduce an overlap afterwards.  In free flow the first sweep finds
  // nothing and the loop ends immediately.
  for (int sweep = 0; sweep < 8; ++sweep) {
    hash_.begin();
    for (uint32_t i = 0; i < n; ++i)
      if (!hash_.insert(i, veh_[i].pos.x, veh_[i].pos.y)) ++stats_.hash_drops;
    hash_.end();
    if (separateBodies() == 0) break;
  }

  // Deferred routing (budgeted so the step time stays bounded).
  while (!pending_routes_.empty() && routes_this_step_ < cfg_.max_routes_per_step) {
    const uint32_t id = pending_routes_.back();
    pending_routes_.pop_back();
    const uint32_t slot = indexOfId(id);
    if (slot == kInvalidIndex) continue;
    Vehicle& v = veh_[slot];
    if (v.dest_lane == kInvalidIndex) continue;
    ++routes_this_step_;
    if (router_ != nullptr && router_->attached()) {
      // Avoid the street we are stuck trying to get into — not the connector
      // itself, which would send the agent round the block to reach the very
      // lane it is queued for.
      const uint32_t jl = nextJunction(v);
      const uint32_t avoid = jl != kInvalidIndex ? graph_->lane(jl).to_lane : kInvalidIndex;
      if (routeAgent(v, v.dest_lane, v.dest_s, avoid)) ++stats_.reroutes;
    }
  }

  // Spare routing budget goes to agents that are still wandering because the
  // budget was exhausted when they spawned: every agent ends up
  // destination-driven within a few seconds.
  while (routes_this_step_ < cfg_.max_routes_per_step && !veh_.empty() && router_ != nullptr &&
         router_->attached()) {
    bool assigned = false;
    for (uint32_t k = 0; k < veh_.size(); ++k) {
      goal_cursor_ = (goal_cursor_ + 1u) % static_cast<uint32_t>(veh_.size());
      Vehicle& v = veh_[goal_cursor_];
      if ((v.flags & kVehHasRoute) != 0 || v.bus_route != 0xFFFFu) continue;
      const uint32_t dest = sampleDestLane(rng_);
      if (dest == kInvalidIndex || dest == v.lane) break;
      ++routes_this_step_;
      routeAgent(v, dest, graph_->lane(dest).length_m * 0.5f);
      assigned = true;
      break;
    }
    if (!assigned) break;
  }

  updateSpawnDespawn();
  ++step_ix_;
  publishStats();
}

void TrafficSim::publishStats() {
  stats_.vehicles = static_cast<uint32_t>(veh_.size());
  stats_.sim_time_s = time_s_;
  stats_.stopped_at_red = 0;
  stats_.in_junction = 0;
  stats_.double_parked = 0;
  stats_.dwelling = 0;
  float sum = 0.f;
  for (const Vehicle& v : veh_) {
    sum += v.speed;
    if (v.state == DriveState::StoppedAtLine) ++stats_.stopped_at_red;
    if (v.state == DriveState::DoubleParked) ++stats_.double_parked;
    if (v.state == DriveState::BusDwelling || v.state == DriveState::TaxiPickup) ++stats_.dwelling;
    if (graph_->lane(v.lane).is_junction != 0) ++stats_.in_junction;
  }
  stats_.mean_speed_mps = veh_.empty() ? 0.f : sum / fz(veh_.size());
}

uint64_t TrafficSim::trajectoryHash() const {
  // Ordered by agent id so the memory layout (swap-remove) cannot leak in.
  Fnv1a64 h;
  for (uint32_t id = 0; id < slot_of_id_.size(); ++id) {
    const uint32_t slot = slot_of_id_[id];
    if (slot == kInvalidIndex) continue;
    const Vehicle& v = veh_[slot];
    h.addU32(id);
    h.addU32(v.lane);
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(v.s * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(v.speed * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(v.lateral * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(v.pos.x * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(v.pos.y * 1000.f)));
    h.addU32(static_cast<uint32_t>(v.flags) | (static_cast<uint32_t>(v.state) << 8) |
             (static_cast<uint32_t>(v.cls) << 16));
  }
  return h.h;
}

// ------------------------------------------------------------------ probes
float TrafficSim::timeToArrivalProbe(const void* ctx, float x, float y, float r) {
  const TrafficSim* self = static_cast<const TrafficSim*>(ctx);
  float best = 1e9f;
  self->hash_.query(x, y, r, [&](uint32_t i) {
    if (i >= self->veh_.size()) return;  // despawned since the hash was built
    const Vehicle& v = self->veh_[i];
    const float dx = x - v.pos.x, dy = y - v.pos.y;
    const float d2 = dx * dx + dy * dy;
    if (d2 > r * r) return;
    const float d = std::sqrt(d2);
    const float hx = std::cos(v.heading_rad), hy = std::sin(v.heading_rad);
    const float along = dx * hx + dy * hy;
    if (along < -1.f) return;  // already past the point
    const float t = along / std::max(0.5f, v.speed);
    if (d < 4.f) best = std::min(best, 0.f);
    else best = std::min(best, t);
  });
  return best;
}

bool TrafficSim::freeTaxiProbe(const void* ctx, float x, float y, float r, TaxiSighting& out) {
  const TrafficSim* self = static_cast<const TrafficSim*>(ctx);
  float best = r;
  bool found = false;
  self->hash_.query(x, y, r, [&](uint32_t i) {
    if (i >= self->veh_.size()) return;
    const Vehicle& v = self->veh_[i];
    if ((v.flags & kVehRoofLight) == 0) return;
    if (v.state != DriveState::Driving) return;
    const float dx = x - v.pos.x, dy = y - v.pos.y;
    const float d = std::sqrt(dx * dx + dy * dy);
    if (d > best) return;
    best = d;
    out.agent = v.id;
    out.x = v.pos.x;
    out.y = v.pos.y;
    out.distance = d;
    found = true;
  });
  return found;
}

bool TrafficSim::hailProbe(void* ctx, uint32_t agent, float x, float y) {
  TrafficSim* self = static_cast<TrafficSim*>(ctx);
  const uint32_t slot = self->indexOfId(agent);
  if (slot == kInvalidIndex) return false;
  Vehicle& v = self->veh_[slot];
  if ((v.flags & kVehRoofLight) == 0 || v.state != DriveState::Driving) return false;
  v.flags &= static_cast<uint8_t>(~kVehRoofLight);
  v.state = DriveState::TaxiPickup;
  v.state_timer = self->cfg_.taxi_pickup_s;
  v.target_x = x;
  v.target_y = y;
  const Lane& l = self->graph_->lane(v.lane);
  v.lateral_target = -(l.width_m * 0.5f - v.width_m * 0.5f - 0.1f);
  return true;
}

VehicleProbe TrafficSim::vehicleProbe() {
  VehicleProbe p;
  p.ctx = this;
  p.time_to_arrival = &TrafficSim::timeToArrivalProbe;
  p.free_taxi = &TrafficSim::freeTaxiProbe;
  p.hail = &TrafficSim::hailProbe;
  return p;
}

}  // namespace traffic
}  // namespace nycsim
