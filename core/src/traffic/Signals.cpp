// nycsim/traffic/Signals.cpp — see Signals.h.
#include "nycsim/traffic/Signals.h"

#include <algorithm>
#include <cmath>

#include "nycsim/routing/NycbLite.h"

namespace nycsim {
namespace traffic {

using routing::kInvalidIndex;

namespace {
constexpr float kPedCrossingSpeedMps = 1.07f;  // 3.5 ft/s, MUTCD §4E.06 / NYC DOT
constexpr float kMinWalk = 7.f;                // MUTCD minimum WALK interval
constexpr float kMinFlash = 7.f;
}  // namespace

void SignalTable::clear() {
  plans_.clear();
  phases_.clear();
  node_to_plan_.clear();
  veh_cache_.clear();
  ped_cache_.clear();
  cache_time_ = -1.0;
  error_.clear();
}

void SignalTable::reserve(size_t plans, size_t phases) {
  plans_.reserve(plans);
  phases_.reserve(phases);
}

uint32_t SignalTable::addPlan(int64_t node_id, int32_t controller_id, float offset_s, const SignalPhase* ph, size_t n) {
  SignalPlan p;
  p.node_id = node_id;
  p.controller_id = controller_id;
  p.offset_s = offset_s;
  p.first_phase = static_cast<uint32_t>(phases_.size());
  p.phase_count = static_cast<uint32_t>(n);
  float cycle = 0.f;
  for (size_t i = 0; i < n; ++i) {
    SignalPhase q = ph[i];
    q.lpi_s = std::max(0.f, q.lpi_s);
    q.green_s = std::max(0.f, q.green_s);
    q.yellow_s = std::max(0.f, q.yellow_s);
    q.allred_s = std::max(0.f, q.allred_s);
    q.ped_walk_s = std::max(0.f, q.ped_walk_s);
    q.ped_flash_s = std::max(0.f, q.ped_flash_s);
    // Pedestrian clearance must end before the conflicting green (end of yellow).
    const float ped_limit = q.lpi_s + q.green_s + q.yellow_s;
    if (q.ped_walk_s + q.ped_flash_s > ped_limit) {
      q.ped_flash_s = std::min(q.ped_flash_s, ped_limit);
      q.ped_walk_s = std::max(0.f, ped_limit - q.ped_flash_s);
    }
    cycle += q.duration();
    phases_.push_back(q);
  }
  p.cycle_s = cycle > 1e-3f ? cycle : 1.f;
  plans_.push_back(p);
  veh_cache_.resize(plans_.size() * kMaxCachedGroups, static_cast<uint8_t>(VehSignal::Off));
  ped_cache_.resize(plans_.size() * kMaxCachedGroups, static_cast<uint8_t>(PedSignal::Off));
  cache_time_ = -1.0;
  return static_cast<uint32_t>(plans_.size() - 1);
}

bool SignalTable::loadFromNycb(const uint8_t* data, size_t len) {
  clear();
  nycb::File f;
  if (!f.open(data, len)) {
    error_ = f.error;
    return false;
  }
  const nycb::Section controllers = f.section("controllers");
  const nycb::Section phases = f.section("phases");
  if (!controllers.present || !phases.present) {
    error_ = "signals.nycb: missing controllers/phases section";
    return false;
  }
  if (controllers.element_size != 28 || phases.element_size != 28) {
    error_ = "signals.nycb: unexpected element size (expected 28/28)";
    return false;
  }
  reserve(controllers.element_count, phases.element_count);
  SignalPhase tmp[32];
  for (uint32_t i = 0; i < controllers.element_count; ++i) {
    const uint8_t* p = controllers.at(i);
    const uint32_t fp = nycb::rdU32(p + 20), pc = nycb::rdU32(p + 24);
    if (static_cast<uint64_t>(fp) + pc > phases.element_count || pc > 32) {
      error_ = "signals.nycb: phase range out of bounds";
      return false;
    }
    for (uint32_t k = 0; k < pc; ++k) {
      const uint8_t* q = phases.at(fp + k);
      tmp[k].group = nycb::rdI32(q);
      tmp[k].green_s = nycb::rdF32(q + 4);
      tmp[k].yellow_s = nycb::rdF32(q + 8);
      tmp[k].allred_s = nycb::rdF32(q + 12);
      tmp[k].ped_walk_s = nycb::rdF32(q + 16);
      tmp[k].ped_flash_s = nycb::rdF32(q + 20);
      tmp[k].lpi_s = nycb::rdF32(q + 24);
    }
    const uint32_t idx = addPlan(nycb::rdI64(p), nycb::rdI32(p + 8), nycb::rdF32(p + 16), tmp, pc);
    // Contract cycle_s vs. effective: honour the declared cycle when the phases
    // are shorter by padding the last phase's all-red (keeps coordination).
    const float declared = nycb::rdF32(p + 12);
    SignalPlan& plan = plans_[idx];
    if (declared > plan.cycle_s + 0.01f && plan.phase_count > 0) {
      phases_[plan.first_phase + plan.phase_count - 1].allred_s += declared - plan.cycle_s;
      plan.cycle_s = declared;
    }
  }
  return true;
}

bool SignalTable::bind(const routing::RoadGraph& g) {
  node_to_plan_.assign(g.nodeCount(), kInvalidIndex);
  uint32_t unknown = 0;
  for (uint32_t i = 0; i < plans_.size(); ++i) {
    const uint32_t ni = g.nodeIndex(plans_[i].node_id);
    plans_[i].node_index = ni;
    if (ni == kInvalidIndex) {
      ++unknown;
      continue;
    }
    node_to_plan_[ni] = i;
  }
  if (unknown > 0) {
    error_ = "signals: " + std::to_string(unknown) + " plan(s) reference unknown node ids";
    return false;
  }
  error_.clear();
  return true;
}

uint32_t SignalTable::addDefaultPlans(const routing::RoadGraph& g, const DefaultPlanParams& p) {
  if (node_to_plan_.size() != g.nodeCount()) node_to_plan_.assign(g.nodeCount(), kInvalidIndex);
  uint32_t added = 0;
  int32_t groups[kMaxCachedGroups];
  SignalPhase phases[kMaxCachedGroups];
  for (uint32_t ni = 0; ni < g.nodeCount(); ++ni) {
    const routing::Node& node = g.node(ni);
    if (node.control != routing::Control::Signal || node_to_plan_[ni] != kInvalidIndex) continue;
    uint32_t n = 0;
    const uint32_t* jls = g.nodeJunctionLanes(ni, n);
    uint32_t ng = 0;
    for (uint32_t k = 0; k < n; ++k) {
      const int32_t gidx = g.lane(jls[k]).signal_group;
      if (gidx < 0) continue;
      bool seen = false;
      for (uint32_t q = 0; q < ng; ++q)
        if (groups[q] == gidx) seen = true;
      if (!seen && ng < kMaxCachedGroups) groups[ng++] = gidx;
    }
    if (ng == 0) continue;
    std::sort(groups, groups + ng);
    const float split = p.cycle_s / static_cast<float>(ng);
    for (uint32_t q = 0; q < ng; ++q) {
      SignalPhase ph;
      ph.group = groups[q];
      ph.lpi_s = p.lpi_s;
      ph.yellow_s = p.yellow_s;
      ph.allred_s = p.allred_s;
      ph.green_s = std::max(5.f, split - ph.lpi_s - ph.yellow_s - ph.allred_s);
      const float clearance = ph.lpi_s + ph.green_s + ph.yellow_s;
      ph.ped_flash_s = p.ped_flash_s > 0.f ? p.ped_flash_s : std::max(kMinFlash, p.crossing_distance_m / kPedCrossingSpeedMps);
      ph.ped_flash_s = std::min(ph.ped_flash_s, clearance);
      ph.ped_walk_s = std::max(std::min(kMinWalk, clearance - ph.ped_flash_s), clearance - ph.ped_flash_s);
      phases[q] = ph;
    }
    const uint32_t idx = addPlan(node.id, -1, 0.f, phases, ng);
    plans_[idx].node_index = ni;
    node_to_plan_[ni] = idx;
    ++added;
  }
  return added;
}

float SignalTable::cycleTime(uint32_t plan, double t) const {
  const SignalPlan& p = plans_[plan];
  double tc = std::fmod(t - static_cast<double>(p.offset_s), static_cast<double>(p.cycle_s));
  if (tc < 0.0) tc += p.cycle_s;
  return static_cast<float>(tc);
}

bool SignalTable::hasGroup(uint32_t plan, int32_t group) const {
  const SignalPlan& p = plans_[plan];
  for (uint32_t i = 0; i < p.phase_count; ++i)
    if (phases_[p.first_phase + i].group == group) return true;
  return false;
}

VehSignal SignalTable::vehicleState(uint32_t plan, int32_t group, double t) const {
  const SignalPlan& p = plans_[plan];
  const float tc = cycleTime(plan, t);
  float start = 0.f;
  VehSignal best = VehSignal::Off;
  for (uint32_t i = 0; i < p.phase_count; ++i) {
    const SignalPhase& ph = phases_[p.first_phase + i];
    if (ph.group == group) {
      VehSignal s = VehSignal::Red;
      const float local = tc - start;
      if (local >= ph.lpi_s && local < ph.lpi_s + ph.green_s) s = VehSignal::Green;
      else if (local >= ph.lpi_s + ph.green_s && local < ph.lpi_s + ph.green_s + ph.yellow_s) s = VehSignal::Yellow;
      if (best == VehSignal::Off || static_cast<int>(s) > static_cast<int>(best)) best = s;
    }
    start += ph.duration();
  }
  return best;
}

PedSignal SignalTable::pedState(uint32_t plan, int32_t group, double t) const {
  const SignalPlan& p = plans_[plan];
  const float tc = cycleTime(plan, t);
  float start = 0.f;
  PedSignal best = PedSignal::Off;
  for (uint32_t i = 0; i < p.phase_count; ++i) {
    const SignalPhase& ph = phases_[p.first_phase + i];
    if (ph.group == group) {
      PedSignal s = PedSignal::DontWalk;
      const float local = tc - start;
      if (local >= 0.f && local < ph.ped_walk_s) s = PedSignal::Walk;
      else if (local >= ph.ped_walk_s && local < ph.ped_walk_s + ph.ped_flash_s) s = PedSignal::Flash;
      // priority: Walk > Flash > DontWalk
      auto rank = [](PedSignal x) { return x == PedSignal::Walk ? 2 : (x == PedSignal::Flash ? 1 : 0); };
      if (best == PedSignal::Off || rank(s) > rank(best)) best = s;
    }
    start += ph.duration();
  }
  return best;
}

float SignalTable::timeToGreen(uint32_t plan, int32_t group, double t) const {
  const SignalPlan& p = plans_[plan];
  const float tc = cycleTime(plan, t);
  float start = 0.f, best = INFINITY;
  for (uint32_t i = 0; i < p.phase_count; ++i) {
    const SignalPhase& ph = phases_[p.first_phase + i];
    if (ph.group == group) {
      const float gs = start + ph.lpi_s, ge = gs + ph.green_s;
      if (tc >= gs && tc < ge) return 0.f;
      float d = gs - tc;
      if (d < 0.f) d += p.cycle_s;
      best = std::min(best, d);
    }
    start += ph.duration();
  }
  return std::isfinite(best) ? best : 0.f;
}

float SignalTable::greenRemaining(uint32_t plan, int32_t group, double t) const {
  const SignalPlan& p = plans_[plan];
  const float tc = cycleTime(plan, t);
  float start = 0.f;
  for (uint32_t i = 0; i < p.phase_count; ++i) {
    const SignalPhase& ph = phases_[p.first_phase + i];
    if (ph.group == group) {
      const float gs = start + ph.lpi_s, ge = gs + ph.green_s;
      if (tc >= gs && tc < ge) return ge - tc;
    }
    start += ph.duration();
  }
  return 0.f;
}

float SignalTable::redFraction(uint32_t plan, int32_t group) const {
  const SignalPlan& p = plans_[plan];
  float go = 0.f;
  bool found = false;
  for (uint32_t i = 0; i < p.phase_count; ++i) {
    const SignalPhase& ph = phases_[p.first_phase + i];
    if (ph.group == group) {
      go += ph.green_s + ph.yellow_s;
      found = true;
    }
  }
  if (!found) return 0.f;
  return std::clamp(1.f - go / p.cycle_s, 0.f, 1.f);
}

float SignalTable::expectedDelay(uint32_t plan, int32_t group) const {
  const SignalPlan& p = plans_[plan];
  const float r = redFraction(plan, group) * p.cycle_s;
  return r * r / (2.f * p.cycle_s);
}

void SignalTable::cacheStates(double t) {
  if (veh_cache_.size() != plans_.size() * kMaxCachedGroups) {
    veh_cache_.assign(plans_.size() * kMaxCachedGroups, static_cast<uint8_t>(VehSignal::Off));
    ped_cache_.assign(plans_.size() * kMaxCachedGroups, static_cast<uint8_t>(PedSignal::Off));
  }
  for (uint32_t pi = 0; pi < plans_.size(); ++pi) {
    const SignalPlan& p = plans_[pi];
    const float tc = cycleTime(pi, t);
    uint8_t* vc = veh_cache_.data() + pi * kMaxCachedGroups;
    uint8_t* pc = ped_cache_.data() + pi * kMaxCachedGroups;
    for (uint32_t gi = 0; gi < kMaxCachedGroups; ++gi) {
      vc[gi] = static_cast<uint8_t>(VehSignal::Off);
      pc[gi] = static_cast<uint8_t>(PedSignal::Off);
    }
    float start = 0.f;
    for (uint32_t i = 0; i < p.phase_count; ++i) {
      const SignalPhase& ph = phases_[p.first_phase + i];
      start += 0.f;
      if (ph.group >= 0 && ph.group < static_cast<int32_t>(kMaxCachedGroups)) {
        const float local = tc - start;
        VehSignal vs = VehSignal::Red;
        if (local >= ph.lpi_s && local < ph.lpi_s + ph.green_s) vs = VehSignal::Green;
        else if (local >= ph.lpi_s + ph.green_s && local < ph.lpi_s + ph.green_s + ph.yellow_s) vs = VehSignal::Yellow;
        PedSignal ps = PedSignal::DontWalk;
        if (local >= 0.f && local < ph.ped_walk_s) ps = PedSignal::Walk;
        else if (local >= ph.ped_walk_s && local < ph.ped_walk_s + ph.ped_flash_s) ps = PedSignal::Flash;
        uint8_t& v = vc[ph.group];
        uint8_t& q = pc[ph.group];
        if (v == static_cast<uint8_t>(VehSignal::Off) || static_cast<uint8_t>(vs) > v) v = static_cast<uint8_t>(vs);
        auto rank = [](uint8_t x) { return x == static_cast<uint8_t>(PedSignal::Walk) ? 2 : (x == static_cast<uint8_t>(PedSignal::Flash) ? 1 : (x == static_cast<uint8_t>(PedSignal::Off) ? -1 : 0)); };
        if (rank(static_cast<uint8_t>(ps)) > rank(q)) q = static_cast<uint8_t>(ps);
      }
      start += ph.duration();
    }
  }
  cache_time_ = t;
}

}  // namespace traffic
}  // namespace nycsim
