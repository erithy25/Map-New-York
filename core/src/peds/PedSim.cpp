// nycsim/peds/PedSim.cpp — see PedSim.h.
#include "nycsim/peds/PedSim.h"

#include <algorithm>
#include <cmath>

namespace nycsim {
namespace peds {

using routing::kInvalidIndex;
using routing::Vec3;
using traffic::PedSignal;

namespace {
inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
inline float fz(size_t v) { return static_cast<float>(v); }
constexpr float kWallQueryRadius = 1.4f;
}  // namespace

PedSim::PedSim() = default;

bool PedSim::configure(const SidewalkGraph& w, const traffic::SignalTable* sig, const PedConfig& cfg,
                       uint64_t seed) {
  error_.clear();
  if (!w.finalized()) {
    error_ = "PedSim: sidewalk graph is not finalized";
    return false;
  }
  walk_ = &w;
  signals_ = sig;
  cfg_ = cfg;
  if (cfg_.dt <= 0.f) cfg_.dt = 0.05f;
  if (cfg_.max_peds > 1000000u) cfg_.max_peds = 1000000u;

  const size_t cap = cfg_.max_peds;
  peds_.clear();
  peds_.reserve(cap);
  slot_of_id_.assign(cap, kInvalidIndex);
  free_ids_.clear();
  free_ids_.reserve(cap);
  for (size_t i = cap; i > 0; --i) free_ids_.push_back(static_cast<uint32_t>(i - 1));
  path_pool_.assign(cap * kPathCap, kInvalidIndex);
  fx_.assign(cap, 0.f);
  fy_.assign(cap, 0.f);

  float minx, miny, maxx, maxy;
  w.bounds(minx, miny, maxx, maxy);
  hash_.configure(minx - 20.f, miny - 20.f, maxx + 20.f, maxy + 20.f,
                  std::max(1.0f, cfg_.force.cutoff_m), static_cast<uint32_t>(cap));
  sig_hash_.configure(minx - 20.f, miny - 20.f, maxx + 20.f, maxy + 20.f,
                      std::max(10.f, cfg_.uniqueness_radius_m), static_cast<uint32_t>(cap));

  // Sidewalk area per NTA and the spawn CDF over walkable edges.
  uint16_t max_nta = 0;
  for (uint32_t n = 0; n < w.nodeCount(); ++n)
    if (w.node(n).nta != routing::kNoNta) max_nta = std::max(max_nta, w.node(n).nta);
  nta_sidewalk_m2_.assign(static_cast<size_t>(max_nta) + 2u, 0.f);
  fast_zone_.assign(nta_sidewalk_m2_.size(), 0u);
  spawn_edges_.clear();
  spawn_cdf_.clear();
  float acc = 0.f;
  for (uint32_t e = 0; e < w.edgeCount(); ++e) {
    const WalkEdge& ed = w.edge(e);
    if (ed.kind == WalkEdgeKind::Crosswalk) continue;
    const float area = ed.length_m * ed.width_m;
    const uint16_t nta = w.node(ed.a).nta;
    const size_t slot = nta == routing::kNoNta ? nta_sidewalk_m2_.size() - 1 : nta;
    if (slot < nta_sidewalk_m2_.size()) nta_sidewalk_m2_[slot] += area;
    acc += area;
    spawn_edges_.push_back(e);
    spawn_cdf_.push_back(acc);
  }
  if (spawn_edges_.empty()) {
    error_ = "PedSim: sidewalk graph has no walkable (non-crosswalk) edges";
    return false;
  }

  time_s_ = 0.0;
  step_ix_ = 0;
  next_id_ = 0;
  spawn_credit_ = 0.f;
  seed_ = seed;
  rng_.reseed(seed);
  stats_ = PedStats{};
  return true;
}

void PedSim::reset(uint64_t seed) {
  peds_.clear();
  std::fill(slot_of_id_.begin(), slot_of_id_.end(), kInvalidIndex);
  free_ids_.clear();
  for (size_t i = slot_of_id_.size(); i > 0; --i) free_ids_.push_back(static_cast<uint32_t>(i - 1));
  time_s_ = 0.0;
  step_ix_ = 0;
  next_id_ = 0;
  spawn_credit_ = 0.f;
  seed_ = seed;
  rng_.reseed(seed);
  stats_ = PedStats{};
}

void PedSim::setFastZone(uint16_t nta, bool fast) {
  const size_t slot = nta == routing::kNoNta ? fast_zone_.size() - 1 : nta;
  if (slot < fast_zone_.size()) fast_zone_[slot] = fast ? 1u : 0u;
}

void PedSim::setTimeOfDay(float seconds_since_midnight, uint8_t dow) {
  tod_s_ = std::fmod(seconds_since_midnight, 86400.f);
  if (tod_s_ < 0.f) tod_s_ += 86400.f;
  dow_ = dow > 2 ? 0u : dow;
}

uint32_t PedSim::indexOfId(uint32_t id) const {
  return id < slot_of_id_.size() ? slot_of_id_[id] : kInvalidIndex;
}

float PedSim::edgeWidthHalf(uint32_t edge) const {
  const float half = walk_->edge(edge).width_m * 0.5f;
  return std::max(0.05f, half - cfg_.corridor_shoulder_m);
}

// --------------------------------------------------------------- appearance
bool PedSim::signatureUnique(uint64_t sig, float x, float y, uint32_t skip_id) const {
  bool unique = true;
  const float r = cfg_.uniqueness_radius_m;
  sig_hash_.query(x, y, r, [&](uint32_t i) {
    if (!unique || i >= peds_.size()) return;
    const Pedestrian& o = peds_[i];
    if (o.id == skip_id) return;
    if (o.signature != sig) return;
    const float dx = o.x - x, dy = o.y - y;
    if (dx * dx + dy * dy <= r * r) unique = false;
  });
  return unique;
}

void PedSim::drawAppearance(Pedestrian& p) {
  for (uint32_t k = 0; k <= cfg_.uniqueness_retries; ++k) {
    p.variety = drawVariety(p.rng);
    p.signature = p.variety.signature();
    if (signatureUnique(p.signature, p.x, p.y, p.id)) return;
    ++stats_.uniqueness_redraws;
  }
  ++stats_.uniqueness_failures;
}

// ------------------------------------------------------------------ goals
void PedSim::chooseGoal(Pedestrian& p) {
  p.flags &= static_cast<uint8_t>(~kPedHasGoal);
  p.goal_poi = kInvalidIndex;
  PoiKind want = PoiKind::Storefront;
  const float u = p.rng.uniform();
  if ((p.flags & kPedJogger) != 0) {
    want = PoiKind::ParkEntrance;
  } else if ((p.flags & kPedWantsCab) != 0 && u < 0.6f) {
    want = PoiKind::Kerb;
  } else if ((p.flags & kPedTourist) != 0 && u < 0.5f) {
    want = PoiKind::Landmark;
  } else if (u < 0.50f) {
    want = PoiKind::Storefront;
  } else if (u < 0.66f) {
    want = PoiKind::SubwayEntrance;
  } else if (u < 0.76f) {
    want = PoiKind::BusStop;
  } else if (u < 0.85f) {
    want = PoiKind::Bench;
  } else if (u < 0.93f) {
    want = PoiKind::Stoop;
  } else {
    want = PoiKind::Landmark;
  }
  uint32_t n = 0;
  const uint32_t* list = walk_->poisOfKind(want, n);
  if (n == 0) {
    list = walk_->poisOfKind(PoiKind::Storefront, n);
  }
  if (n == 0) {
    // No POIs at all: walk to a random node.
    const uint32_t node = p.rng.below(static_cast<uint32_t>(walk_->nodeCount()));
    pathTo(p, node);
    return;
  }
  const uint32_t poi_ix = list[p.rng.below(n)];
  const WalkPoi& poi = walk_->poi(poi_ix);
  if (poi.edge == kInvalidIndex) return;
  const WalkEdge& e = walk_->edge(poi.edge);
  const uint32_t goal_node = poi.s < e.length_m * 0.5f ? e.a : e.b;
  p.goal_poi = poi_ix;
  if (pathTo(p, goal_node)) p.flags |= kPedHasGoal;
}

uint32_t PedSim::currentNodeAhead(const Pedestrian& p) const {
  const WalkEdge& e = walk_->edge(p.edge);
  return p.dir > 0 ? e.b : e.a;
}

bool PedSim::pathTo(Pedestrian& p, uint32_t goal_node) {
  uint32_t* path = pathOf(p.id);
  const uint32_t from = currentNodeAhead(p);
  if (goal_node == from) {
    path[0] = from;
    p.path_len = 1;
    p.path_pos = 0;
    return true;
  }
  if (paths_this_step_ >= cfg_.max_paths_per_step) {
    ++stats_.path_failures;
    p.path_len = 0;
    p.path_pos = 0;
    return false;
  }
  ++paths_this_step_;
  const uint32_t n = walk_->path(from, goal_node, path, kPathCap);
  ++stats_.paths_built;
  if (n == 0 || n > kPathCap) {
    ++stats_.path_failures;
    p.path_len = 0;
    p.path_pos = 0;
    return false;
  }
  p.path_len = n;
  p.path_pos = 0;
  return true;
}

void PedSim::arriveAtGoal(Pedestrian& p) {
  p.path_len = 0;
  p.path_pos = 0;
  PoiKind kind = PoiKind::Storefront;
  if (p.goal_poi != kInvalidIndex && p.goal_poi < walk_->poiCount()) kind = walk_->poi(p.goal_poi).kind;
  switch (kind) {
    case PoiKind::SubwayEntrance:
      p.activity = PedActivity::EnterSubway;
      p.timer = cfg_.subway_enter_s;
      ++stats_.subway_entries;
      break;
    case PoiKind::Bench:
    case PoiKind::Stoop:
      p.activity = PedActivity::Sit;
      p.timer = p.rng.uniform(cfg_.sit_min_s, cfg_.sit_max_s);
      break;
    case PoiKind::Landmark:
      p.activity = PedActivity::Photograph;
      p.timer = p.rng.uniform(cfg_.photo_min_s, cfg_.photo_max_s);
      ++stats_.photographs;
      break;
    case PoiKind::ParkEntrance:
      p.activity = PedActivity::Jog;
      p.timer = p.rng.uniform(cfg_.jog_min_s, cfg_.jog_max_s);
      chooseGoal(p);
      return;
    case PoiKind::Kerb:
      if ((p.flags & kPedWantsCab) != 0) {
        p.activity = PedActivity::HailCab;
        p.timer = cfg_.hail_timeout_s;
        break;
      }
      p.activity = PedActivity::Browse;
      p.timer = p.rng.uniform(cfg_.browse_min_s, cfg_.browse_max_s);
      break;
    case PoiKind::BusStop:
      p.activity = PedActivity::Browse;
      p.timer = p.rng.uniform(cfg_.browse_min_s, cfg_.browse_max_s * 1.5f);
      break;
    case PoiKind::Storefront:
    case PoiKind::Count:
    default:
      p.activity = PedActivity::Browse;
      p.timer = p.rng.uniform(cfg_.browse_min_s, cfg_.browse_max_s);
      break;
  }
}

// ------------------------------------------------------------- crossing
PedSignal PedSim::crosswalkState(uint32_t edge) const {
  if (edge >= walk_->edgeCount()) return PedSignal::Off;
  const WalkEdge& e = walk_->edge(edge);
  if (signals_ == nullptr || e.signal_plan == kInvalidIndex || e.signal_group < 0) return PedSignal::Off;
  return signals_->cachedPedState(e.signal_plan, e.signal_group);
}

bool PedSim::mayEnterCrosswalk(const Pedestrian& p, uint32_t edge) const {
  const WalkEdge& e = walk_->edge(edge);
  if (e.kind != WalkEdgeKind::Crosswalk) return true;
  const PedSignal ps = crosswalkState(edge);
  const float cross_time = e.length_m / std::max(0.5f, p.desired_speed);
  const bool jay = (p.flags & kPedJaywalker) != 0;
  if (ps == PedSignal::Walk) return true;
  if (ps == PedSignal::Flash) return jay && p.risk >= cfg_.flash_cross_risk;

  // Unsignalized crossing: everybody uses gap acceptance (NY VTL §1151 gives
  // the pedestrian the right of way, but nobody steps in front of a bus).
  const Vec3 mid = walk_->pointOn(edge, e.length_m * 0.5f, 0.f);
  const float need = cross_time + cfg_.crossing_margin_s * (1.5f - p.risk);
  const float tta = veh_probe_.valid() ? veh_probe_.timeToArrival(mid.x, mid.y, 70.f) : 1e9f;
  if (ps == PedSignal::Off) return tta > std::max(cfg_.unsignalized_gap_s, need);
  // Steady DON'T WALK: only a jaywalker, and only with a real gap.
  if (!jay) return false;
  return tta > need;
}

// ----------------------------------------------------------------- update
void PedSim::updateAgent(uint32_t i) {
  Pedestrian& p = peds_[i];
  fx_[i] = 0.f;
  fy_[i] = 0.f;
  const WalkEdge& e = walk_->edge(p.edge);

  // Activity timers.
  bool stationary = false;
  switch (p.activity) {
    case PedActivity::Browse:
    case PedActivity::Sit:
    case PedActivity::Photograph:
      stationary = true;
      p.timer -= cfg_.dt;
      if (p.timer <= 0.f) {
        p.activity = PedActivity::Walk;
        chooseGoal(p);
      }
      break;
    case PedActivity::HailCab: {
      stationary = true;
      p.timer -= cfg_.dt;
      traffic::TaxiSighting sight;
      if (veh_probe_.freeTaxi(p.x, p.y, cfg_.hail_radius_m, sight)) {
        if (veh_probe_.hailTaxi(sight.agent, p.x, p.y)) {
          p.hail_agent = sight.agent;
          p.activity = PedActivity::RideAway;
          p.timer = cfg_.taxi_board_s;
          ++stats_.cabs_hailed;
        }
      }
      if (p.timer <= 0.f && p.activity == PedActivity::HailCab) {
        p.flags &= static_cast<uint8_t>(~kPedWantsCab);
        p.activity = PedActivity::Walk;
        chooseGoal(p);
      }
      break;
    }
    case PedActivity::RideAway:
    case PedActivity::EnterSubway:
      stationary = true;
      p.timer -= cfg_.dt;
      break;
    case PedActivity::WaitCurb:
      stationary = true;
      p.wait_time += cfg_.dt;
      break;
    case PedActivity::Walk:
    case PedActivity::Cross:
    case PedActivity::Jog:
    case PedActivity::Count:
    default:
      break;
  }
  if ((p.flags & kPedJogger) != 0 && p.activity == PedActivity::Jog) {
    p.timer -= cfg_.dt;
    if (p.timer <= 0.f) {
      p.flags &= static_cast<uint8_t>(~kPedJogger);
      p.activity = PedActivity::Walk;
      chooseGoal(p);
    }
  }

  if (stationary) {
    // Damp to a standstill; the repulsion still applies so a crowd does not
    // pile into a stationary agent.
    fx_[i] = -p.vx / std::max(0.05f, cfg_.force.tau_s);
    fy_[i] = -p.vy / std::max(0.05f, cfg_.force.tau_s);
  } else {
    // Desired direction: the far end of the corridor, offset to the walking
    // side (New Yorkers keep right).
    const float look = 4.0f;
    const float target_s = clampf(p.s + static_cast<float>(p.dir) * look, 0.f, e.length_m);
    const float target_lat = -static_cast<float>(p.dir) * p.pref_lateral;
    const Vec3 target = walk_->pointOn(p.edge, target_s, clampf(target_lat, -edgeWidthHalf(p.edge),
                                                                edgeWidthHalf(p.edge)));
    float ex = target.x - p.x, ey = target.y - p.y;
    const float el = std::sqrt(ex * ex + ey * ey);
    if (el > 1e-4f) {
      ex /= el;
      ey /= el;
    } else {
      ex = e.dirx * static_cast<float>(p.dir);
      ey = e.diry * static_cast<float>(p.dir);
    }
    float v0 = p.desired_speed;
    if (p.activity == PedActivity::Jog) v0 = cfg_.jog_speed_mps;
    // Hurry across the roadway, especially when the countdown is flashing.
    if (p.activity == PedActivity::Cross) {
      v0 *= 1.15f;
      if (crosswalkState(p.edge) != PedSignal::Walk) v0 *= 1.20f;
    }
    const Force2 f = drivingForce(cfg_.force, v0, ex, ey, p.vx, p.vy);
    fx_[i] = f.x;
    fy_[i] = f.y;
  }

  // Pedestrian repulsion.
  const float heading_len = std::sqrt(p.vx * p.vx + p.vy * p.vy);
  const float hx = heading_len > 0.05f ? p.vx / heading_len : e.dirx * static_cast<float>(p.dir);
  const float hy = heading_len > 0.05f ? p.vy / heading_len : e.diry * static_cast<float>(p.dir);
  const float cutoff = cfg_.force.cutoff_m;
  const float r_sum = 2.f * cfg_.body_radius_m;
  hash_.query(p.x, p.y, cutoff, [&](uint32_t j) {
    if (j == i || j >= peds_.size()) return;
    const Pedestrian& o = peds_[j];
    const float dx = p.x - o.x, dy = p.y - o.y;
    const float d2 = dx * dx + dy * dy;
    if (d2 > cutoff * cutoff) return;
    const float d = std::sqrt(d2);
    const Force2 rf = pedRepulsion(cfg_.force, dx, dy, d, r_sum, hx, hy);
    fx_[i] += rf.x;
    fy_[i] += rf.y;
  });

  // Walls: only evaluated near the corridor edge — the hard clamp in
  // integrate() is what actually guarantees non-penetration.
  const float half = edgeWidthHalf(p.edge);
  if (std::fabs(p.lateral) > half - 0.9f && walk_->wallCount() != 0) {
    uint32_t buf[8];
    const uint32_t nw = walk_->wallsNear(p.x, p.y, kWallQueryRadius, buf, 8);
    for (uint32_t k = 0; k < nw; ++k) {
      const Wall& w = walk_->wall(buf[k]);
      const float wx = w.x2 - w.x1, wy = w.y2 - w.y1;
      const float len2 = wx * wx + wy * wy;
      float t = len2 > 1e-9f ? ((p.x - w.x1) * wx + (p.y - w.y1) * wy) / len2 : 0.f;
      t = clampf(t, 0.f, 1.f);
      const float cx = w.x1 + t * wx, cy = w.y1 + t * wy;
      const float dx = p.x - cx, dy = p.y - cy;
      const float d = std::sqrt(dx * dx + dy * dy);
      if (d > kWallQueryRadius) continue;
      const Force2 wf = wallRepulsion(cfg_.force, dx, dy, d, cfg_.body_radius_m);
      fx_[i] += wf.x;
      fy_[i] += wf.y;
    }
  }

  // The player is an obstacle like any other body, only bigger.
  if (player_.valid) {
    const float dx = p.x - player_.x, dy = p.y - player_.y;
    const float d2 = dx * dx + dy * dy;
    if (d2 < 25.f) {
      const float d = std::sqrt(d2);
      const Force2 pf = pedRepulsion(cfg_.force, dx, dy, d,
                                     cfg_.body_radius_m + std::max(player_.half_width_m, 0.4f), hx, hy);
      fx_[i] += pf.x * 1.5f;
      fy_[i] += pf.y * 1.5f;
    }
  }
}

void PedSim::integrate(uint32_t i) {
  Pedestrian& p = peds_[i];
  const float dt = cfg_.dt;
  p.vx += fx_[i] * dt;
  p.vy += fy_[i] * dt;
  const float vmax = p.desired_speed * cfg_.max_speed_factor + 0.5f;
  const float sp = std::sqrt(p.vx * p.vx + p.vy * p.vy);
  if (sp > vmax) {
    p.vx = p.vx / sp * vmax;
    p.vy = p.vy / sp * vmax;
  }
  p.x += p.vx * dt;
  p.y += p.vy * dt;

  float s = 0.f, lat = 0.f;
  walk_->projectOnEdge(p.edge, p.x, p.y, s, lat);
  p.s = s;
  p.lateral = lat;

  const float len = walk_->edge(p.edge).length_m;
  const bool arrived = (p.dir > 0 && p.s >= len) || (p.dir < 0 && p.s <= 0.f);
  if (arrived && p.activity != PedActivity::Sit && p.activity != PedActivity::Browse &&
      p.activity != PedActivity::Photograph && p.activity != PedActivity::HailCab &&
      p.activity != PedActivity::RideAway && p.activity != PedActivity::EnterSubway) {
    advanceEdge(p);
  }

  const float half = edgeWidthHalf(p.edge);
  p.lateral = clampf(p.lateral, -half, half);
  p.s = clampf(p.s, 0.f, walk_->edge(p.edge).length_m);
  const Vec3 q = walk_->pointOn(p.edge, p.s, p.lateral);
  p.x = q.x;
  p.y = q.y;
  p.z = q.z;
  p.flags = static_cast<uint8_t>(walk_->edge(p.edge).kind == WalkEdgeKind::Crosswalk
                                     ? (p.flags | kPedOnRoad)
                                     : (p.flags & ~(kPedOnRoad | kPedJaywalking)));
}

// Carries the world position across an edge change instead of snapping to the
// node: a snap would teleport the agent by up to half a corridor width, which
// is how a pedestrian ends up on the far side of a building line.
void PedSim::reprojectOntoEdge(Pedestrian& p) {
  float s = 0.f, lat = 0.f;
  walk_->projectOnEdge(p.edge, p.x, p.y, s, lat);
  const float half = edgeWidthHalf(p.edge);
  p.s = clampf(s, 0.f, walk_->edge(p.edge).length_m);
  p.lateral = clampf(lat, -half, half);
  const Vec3 q = walk_->pointOn(p.edge, p.s, p.lateral);
  p.x = q.x;
  p.y = q.y;
  p.z = q.z;
}

// Node reached: take the next edge of the path, or wait at the kerb.
bool PedSim::advanceEdge(Pedestrian& p) {
  const uint32_t node = currentNodeAhead(p);
  const uint32_t* path = pathOf(p.id);
  uint32_t next_node = kInvalidIndex;

  if (p.path_len > 0 && p.path_pos < p.path_len && path[p.path_pos] == node) {
    if (p.path_pos + 1 < p.path_len) {
      next_node = path[p.path_pos + 1];
    } else {
      arriveAtGoal(p);
      p.vx = 0.f;
      p.vy = 0.f;
      return true;
    }
  }
  if (next_node == kInvalidIndex) {
    // No plan (budget exhausted, unreachable goal, or wandering): take a
    // random continuation that is not an immediate turn-back.
    uint32_t n = 0;
    const uint32_t* es = walk_->nodeEdges(node, n);
    if (n == 0) {
      p.dir = static_cast<int8_t>(-p.dir);
      return false;
    }
    uint32_t pick = kInvalidIndex;
    uint32_t tries = 0;
    while (tries++ < 6) {
      const uint32_t cand = es[p.rng.below(n)];
      if (cand == p.edge && n > 1) continue;
      if (walk_->edge(cand).kind == WalkEdgeKind::Crosswalk && !mayEnterCrosswalk(p, cand)) continue;
      pick = cand;
      break;
    }
    if (pick == kInvalidIndex) {
      p.activity = PedActivity::WaitCurb;
      p.dir = static_cast<int8_t>(-p.dir);
      p.vx = 0.f;
      p.vy = 0.f;
      return false;
    }
    p.edge = pick;
    p.dir = walk_->edge(pick).a == node ? 1 : -1;
    reprojectOntoEdge(p);
    p.activity = walk_->edge(pick).kind == WalkEdgeKind::Crosswalk ? PedActivity::Cross : PedActivity::Walk;
    p.wait_time = 0.f;
    if (p.path_len > 0) p.path_len = 0;
    return true;
  }

  const uint32_t next_edge = walk_->edgeBetween(node, next_node);
  if (next_edge == kInvalidIndex) {
    p.path_len = 0;
    chooseGoal(p);
    return false;
  }
  if (!mayEnterCrosswalk(p, next_edge)) {
    p.activity = PedActivity::WaitCurb;
    p.vx = 0.f;
    p.vy = 0.f;
    p.s = p.dir > 0 ? walk_->edge(p.edge).length_m : 0.f;
    if (p.wait_time > cfg_.curb_wait_max_s) {
      p.wait_time = 0.f;
      p.path_len = 0;
      chooseGoal(p);
    }
    return false;
  }
  const bool crossing = walk_->edge(next_edge).kind == WalkEdgeKind::Crosswalk;
  if (crossing && crosswalkState(next_edge) != PedSignal::Walk) p.flags |= kPedJaywalking;
  p.edge = next_edge;
  p.dir = walk_->edge(next_edge).a == node ? 1 : -1;
  reprojectOntoEdge(p);
  p.path_pos += 1;
  p.wait_time = 0.f;
  p.activity = crossing ? PedActivity::Cross : (((p.flags & kPedJogger) != 0) ? PedActivity::Jog
                                                                             : PedActivity::Walk);
  return true;
}

// ------------------------------------------------------------------- step
void PedSim::rebuildHashes() {
  hash_.begin();
  sig_hash_.begin();
  for (uint32_t i = 0; i < peds_.size(); ++i) {
    hash_.insert(i, peds_[i].x, peds_[i].y);
    sig_hash_.insert(i, peds_[i].x, peds_[i].y);
  }
  hash_.end();
  sig_hash_.end();
}

void PedSim::step() {
  if (walk_ == nullptr) return;
  paths_this_step_ = 0;
  time_s_ += static_cast<double>(cfg_.dt);
  tod_s_ += cfg_.dt;
  if (tod_s_ >= 86400.f) tod_s_ -= 86400.f;
  if (signals_ != nullptr) signals_->cacheStates(time_s_);

  rebuildHashes();
  const uint32_t n = static_cast<uint32_t>(peds_.size());
  for (uint32_t i = 0; i < n; ++i) updateAgent(i);
  for (uint32_t i = 0; i < n; ++i) integrate(i);

  // Remove the agents that have left the world (subway, taxi).
  for (uint32_t i = 0; i < peds_.size();) {
    Pedestrian& p = peds_[i];
    if ((p.activity == PedActivity::EnterSubway || p.activity == PedActivity::RideAway) && p.timer <= 0.f) {
      if (despawn(p.id)) continue;
      p.activity = PedActivity::Walk;
      chooseGoal(p);
    }
    ++i;
  }

  updateSpawnDespawn();
  ++step_ix_;

  stats_.peds = static_cast<uint32_t>(peds_.size());
  stats_.sim_time_s = time_s_;
  stats_.crossing = stats_.waiting = stats_.jaywalking = stats_.sitting = 0;
  stats_.jogging = stats_.hailing = 0;
  float sum = 0.f;
  for (const Pedestrian& p : peds_) {
    sum += std::sqrt(p.vx * p.vx + p.vy * p.vy);
    switch (p.activity) {
      case PedActivity::Cross: ++stats_.crossing; break;
      case PedActivity::WaitCurb: ++stats_.waiting; break;
      case PedActivity::Sit: ++stats_.sitting; break;
      case PedActivity::Jog: ++stats_.jogging; break;
      case PedActivity::HailCab: ++stats_.hailing; break;
      default: break;
    }
    if ((p.flags & kPedJaywalking) != 0) ++stats_.jaywalking;
  }
  stats_.mean_speed_mps = peds_.empty() ? 0.f : sum / fz(peds_.size());
}

// -------------------------------------------------------------- spawning
uint32_t PedSim::spawn(uint32_t edge, float s, bool ignore_player_ring) {
  if (walk_ == nullptr || free_ids_.empty() || edge >= walk_->edgeCount()) {
    ++stats_.spawn_failures;
    return kInvalidIndex;
  }
  const WalkEdge& e = walk_->edge(edge);
  s = clampf(s, 0.f, e.length_m);
  const Vec3 pos = walk_->pointOn(edge, s, 0.f);
  if (!ignore_player_ring && cfg_.use_player_ring && player_.inProtectedRegion(pos.x, pos.y)) {
    ++stats_.spawn_failures;
    return kInvalidIndex;
  }

  const uint32_t id = free_ids_.back();
  free_ids_.pop_back();
  Pedestrian p;
  p.id = id;
  p.edge = edge;
  p.s = s;
  p.x = pos.x;
  p.y = pos.y;
  p.z = pos.z;
  p.rng.reseed(seed_ ^ (0x9E3779B97F4A7C15ull * (static_cast<uint64_t>(id) + 1u) + next_id_));
  ++next_id_;
  p.dir = p.rng.chance(0.5f) ? 1 : -1;

  const uint16_t nta = walk_->node(e.a).nta;
  const size_t slot = nta == routing::kNoNta ? fast_zone_.size() - 1 : nta;
  const bool fast = slot < fast_zone_.size() && fast_zone_[slot] != 0;
  if (fast) p.flags |= kPedFastZone;
  const float mean = fast ? cfg_.fast_zone_speed_mean : cfg_.speed_mean;
  p.desired_speed = p.rng.normalClamped(mean, cfg_.speed_sd, cfg_.speed_min, cfg_.speed_max);
  p.risk = p.rng.uniform();
  if (p.risk > 1.f - cfg_.jaywalk_share) p.flags |= kPedJaywalker;
  if (p.rng.chance(cfg_.jog_share)) {
    p.flags |= kPedJogger;
    p.activity = PedActivity::Jog;
    p.timer = p.rng.uniform(cfg_.jog_min_s, cfg_.jog_max_s);
  }
  if (p.rng.chance(cfg_.tourist_share)) p.flags |= kPedTourist;
  if (p.rng.chance(cfg_.cab_share)) p.flags |= kPedWantsCab;
  p.pref_lateral = p.rng.uniform(0.15f, std::max(0.2f, edgeWidthHalf(edge) - 0.2f));
  p.vx = e.dirx * static_cast<float>(p.dir) * p.desired_speed * 0.5f;
  p.vy = e.diry * static_cast<float>(p.dir) * p.desired_speed * 0.5f;

  peds_.push_back(p);
  const uint32_t idx = static_cast<uint32_t>(peds_.size() - 1);
  slot_of_id_[id] = idx;
  Pedestrian& np = peds_[idx];
  drawAppearance(np);
  chooseGoal(np);
  ++stats_.spawned;
  return id;
}

bool PedSim::despawn(uint32_t id, bool ignore_player_ring) {
  const uint32_t slot = indexOfId(id);
  if (slot == kInvalidIndex) return false;
  Pedestrian& p = peds_[slot];
  if (!ignore_player_ring && cfg_.use_player_ring && player_.inProtectedRegion(p.x, p.y)) return false;
  const uint32_t last = static_cast<uint32_t>(peds_.size() - 1);
  if (slot != last) {
    peds_[slot] = peds_[last];
    slot_of_id_[peds_[slot].id] = slot;
  }
  peds_.pop_back();
  slot_of_id_[id] = kInvalidIndex;
  free_ids_.push_back(id);
  ++stats_.despawned;
  return true;
}

void PedSim::updateSpawnDespawn() {
  if (player_.valid && cfg_.use_player_ring) {
    for (uint32_t i = 0; i < peds_.size();) {
      const Pedestrian& p = peds_[i];
      const float dx = p.x - player_.x, dy = p.y - player_.y;
      if (dx * dx + dy * dy > cfg_.despawn_m * cfg_.despawn_m && despawn(p.id)) continue;
      ++i;
    }
  }
  float target = 0.f;
  if (density_ != nullptr) {
    const uint8_t hour = static_cast<uint8_t>(clampf(tod_s_ / 3600.f, 0.f, 23.f));
    for (uint16_t nta = 0; nta < density_->ntaCount() && nta < nta_sidewalk_m2_.size(); ++nta)
      target += nta_sidewalk_m2_[nta] * density_->get(nta, hour, dow_).ped_per_m2;
  }
  stats_.target_peds = target;
  if (density_ == nullptr) return;

  spawn_credit_ += cfg_.spawn_rate_per_s * cfg_.dt;
  while (spawn_credit_ >= 1.f) {
    spawn_credit_ -= 1.f;
    if (fz(peds_.size()) >= target || peds_.size() >= cfg_.max_peds) break;
    bool done = false;
    for (int attempt = 0; attempt < 4 && !done; ++attempt) {
      const float pick = rng_.uniform() * spawn_cdf_.back();
      const auto it = std::lower_bound(spawn_cdf_.begin(), spawn_cdf_.end(), pick);
      const size_t ix = std::min(static_cast<size_t>(it - spawn_cdf_.begin()), spawn_edges_.size() - 1);
      const uint32_t edge = spawn_edges_[ix];
      const float s = rng_.uniform(0.f, walk_->edge(edge).length_m);
      done = spawn(edge, s) != kInvalidIndex;
    }
    if (!done) ++stats_.spawn_failures;
  }
}

uint32_t PedSim::prefill(uint32_t count) {
  if (walk_ == nullptr || spawn_cdf_.empty()) return 0;
  uint32_t made = 0;
  uint32_t attempts = 0;
  const uint32_t saved_budget = cfg_.max_paths_per_step;
  cfg_.max_paths_per_step = 0xFFFFFFFFu;  // load time: no per-step budget
  while (made < count && peds_.size() < cfg_.max_peds && attempts < count * 8u + 512u) {
    ++attempts;
    const float pick = rng_.uniform() * spawn_cdf_.back();
    const auto it = std::lower_bound(spawn_cdf_.begin(), spawn_cdf_.end(), pick);
    const size_t ix = std::min(static_cast<size_t>(it - spawn_cdf_.begin()), spawn_edges_.size() - 1);
    const uint32_t edge = spawn_edges_[ix];
    const float s = rng_.uniform(0.f, walk_->edge(edge).length_m);
    if (spawn(edge, s) != kInvalidIndex) {
      ++made;
      if ((made & 63u) == 0u) rebuildHashes();  // keep the uniqueness test honest
    }
  }
  cfg_.max_paths_per_step = saved_budget;
  rebuildHashes();
  return made;
}

// ------------------------------------------------------------------ queries
uint32_t PedSim::duplicateSignatures() const {
  uint32_t dup = 0;
  const float r = cfg_.uniqueness_radius_m;
  for (uint32_t i = 0; i < peds_.size(); ++i) {
    const Pedestrian& p = peds_[i];
    bool bad = false;
    sig_hash_.query(p.x, p.y, r, [&](uint32_t j) {
      if (bad || j == i || j >= peds_.size()) return;
      const Pedestrian& o = peds_[j];
      if (o.signature != p.signature) return;
      const float dx = o.x - p.x, dy = o.y - p.y;
      if (dx * dx + dy * dy <= r * r) bad = true;
    });
    if (bad) ++dup;
  }
  return dup;
}

float PedSim::measuredDensity(uint16_t nta) const {
  const size_t slot = nta == routing::kNoNta ? nta_sidewalk_m2_.size() - 1 : nta;
  if (slot >= nta_sidewalk_m2_.size() || nta_sidewalk_m2_[slot] < 1.f) return 0.f;
  uint32_t count = 0;
  for (const Pedestrian& p : peds_)
    if (walk_->node(walk_->edge(p.edge).a).nta == nta) ++count;
  return static_cast<float>(count) / nta_sidewalk_m2_[slot];
}

uint64_t PedSim::trajectoryHash() const {
  Fnv1a64 h;
  for (uint32_t id = 0; id < slot_of_id_.size(); ++id) {
    const uint32_t slot = slot_of_id_[id];
    if (slot == kInvalidIndex) continue;
    const Pedestrian& p = peds_[slot];
    h.addU32(id);
    h.addU32(p.edge);
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(p.x * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(p.y * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(p.vx * 1000.f)));
    h.addU32(static_cast<uint32_t>(static_cast<int32_t>(p.vy * 1000.f)));
    h.addU32(static_cast<uint32_t>(p.flags) | (static_cast<uint32_t>(p.activity) << 8));
    h.add(&p.signature, sizeof p.signature);
  }
  return h.h;
}

uint32_t PedSim::roadPedsProbe(const void* ctx, float x, float y, float r) {
  const PedSim* self = static_cast<const PedSim*>(ctx);
  uint32_t n = 0;
  self->hash_.query(x, y, r, [&](uint32_t i) {
    if (i >= self->peds_.size()) return;
    const Pedestrian& p = self->peds_[i];
    if ((p.flags & kPedOnRoad) == 0) return;
    const float dx = p.x - x, dy = p.y - y;
    if (dx * dx + dy * dy <= r * r) ++n;
  });
  return n;
}

traffic::PedProbe PedSim::pedProbe() {
  traffic::PedProbe p;
  p.ctx = this;
  p.road_peds = &PedSim::roadPedsProbe;
  return p;
}

}  // namespace peds
}  // namespace nycsim
