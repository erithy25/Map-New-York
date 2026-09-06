// nycsim/traffic/SyntheticGrid.cpp — see SyntheticGrid.h.
#include "nycsim/traffic/SyntheticGrid.h"

#include <cmath>
#include <cstdio>
#include <vector>

namespace nycsim {
namespace traffic {

using namespace routing;

namespace {

const char* ordinalSuffix(int n) {
  const int m100 = n % 100, m10 = n % 10;
  if (m100 >= 11 && m100 <= 13) return "th";
  if (m10 == 1) return "st";
  if (m10 == 2) return "nd";
  if (m10 == 3) return "rd";
  return "th";
}

struct LaneRec {
  LaneId id;
  SegmentId seg;
  int index;
  int dir;
  LaneKind kind;
  NodeId start, end;
  float dx, dy;  // unit travel direction
  bool is_avenue;
  int i, j;      // grid coordinates of the owning segment
};

struct JlRec {
  LaneId id;
  uint32_t from_rec, to_rec;
  TurnType turn;
  int32_t group;
  NodeId node;
};

}  // namespace

void SyntheticGrid::avenueName(int i, char* buf, size_t n) {
  const int num = i + 1;
  std::snprintf(buf, n, "%d%s Ave", num, ordinalSuffix(num));
}

void SyntheticGrid::streetName(const SyntheticGridSpec& s, int j, char* buf, size_t n) {
  const int num = s.first_street_number + j;
  std::snprintf(buf, n, "W %d%s St", num, ordinalSuffix(num));
}

bool SyntheticGrid::build(const SyntheticGridSpec& spec, RoadGraph& g, SignalTable& signals, std::string* error) {
  g.clear();
  signals.clear();
  if (spec.avenues < 2 || spec.streets < 2 || spec.avenues > 999) {
    if (error) *error = "synthetic grid: need 2..999 avenues and ≥ 2 streets";
    return false;
  }
  const float mph = 0.44704f;
  const float av_speed = spec.avenue_speed_mph * mph, st_speed = spec.street_speed_mph * mph;
  char name[64];

  // ---- nodes
  for (int j = 0; j < spec.streets; ++j) {
    for (int i = 0; i < spec.avenues; ++i) {
      Vec3 p{spec.origin_x + static_cast<float>(i) * spec.avenue_spacing_m, spec.origin_y + static_cast<float>(j) * spec.street_spacing_m, 0.f};
      const Control c = streetStopControlled(spec, j) ? Control::Stop : Control::Signal;
      g.addNode(nodeId(i, j), p, c, c == Control::Signal ? 4 : 0);
    }
  }

  std::vector<LaneRec> recs;
  recs.reserve(static_cast<size_t>(spec.avenues) * spec.streets * 12);

  auto addLanesForSegment = [&](SegmentId seg, int dir, int travel, bool parking, bool bike, float speed, NodeId a, NodeId b,
                                float dx, float dy, bool is_avenue, int gi, int gj) {
    // a→b is the segment geometry direction; dir=+1 travels a→b.
    const NodeId start = dir > 0 ? a : b, end = dir > 0 ? b : a;
    const float tx = dir > 0 ? dx : -dx, ty = dir > 0 ? dy : -dy;
    int idx = 0;
    for (int k = 0; k < travel; ++k, ++idx) {
      const LaneId id = laneId(seg, idx, dir);
      g.addLane(id, seg, static_cast<int8_t>(idx), static_cast<int8_t>(dir), LaneKind::Travel, spec.lane_width_m, speed);
      recs.push_back({id, seg, idx, dir, LaneKind::Travel, start, end, tx, ty, is_avenue, gi, gj});
    }
    if (parking) {
      const LaneId id = laneId(seg, idx, dir);
      g.addLane(id, seg, static_cast<int8_t>(idx), static_cast<int8_t>(dir), LaneKind::Parking, spec.parking_width_m, 4.f);
      recs.push_back({id, seg, idx, dir, LaneKind::Parking, start, end, tx, ty, is_avenue, gi, gj});
      ++idx;
    }
    if (bike) {
      const LaneId id = laneId(seg, idx, dir);
      g.addLane(id, seg, static_cast<int8_t>(idx), static_cast<int8_t>(dir), LaneKind::Bike, spec.bike_width_m, 6.7f);
      recs.push_back({id, seg, idx, dir, LaneKind::Bike, start, end, tx, ty, is_avenue, gi, gj});
      ++idx;
    }
  };

  // ---- avenue segments (south → north geometry)
  for (int i = 0; i < spec.avenues; ++i) {
    const bool two_way = avenueTwoWay(spec, i);
    const bool north = avenueNorthbound(i);
    const bool bike = avenueHasBikeLane(spec, i);
    avenueName(i, name, sizeof name);
    for (int j = 0; j + 1 < spec.streets; ++j) {
      const SegmentId seg = avenueSegmentId(i, j);
      const NodeId a = nodeId(i, j), b = nodeId(i, j + 1);
      Vec3 pts[2] = {{spec.origin_x + i * spec.avenue_spacing_m, spec.origin_y + j * spec.street_spacing_m, 0.f},
                     {spec.origin_x + i * spec.avenue_spacing_m, spec.origin_y + (j + 1) * spec.street_spacing_m, 0.f}};
      SegmentAttrs at;
      at.rw_type = RwType::Street;
      at.traffic_dir = two_way ? TrafficDir::TwoWay : (north ? TrafficDir::Forward : TrafficDir::Backward);
      at.travel_lanes = static_cast<uint8_t>(spec.avenue_travel_lanes * (two_way ? 2 : 1));
      at.park_lanes = static_cast<uint8_t>(spec.parking_lanes ? (two_way ? 2 : 1) : 0);
      const int dirs = two_way ? 2 : 1;
      at.width_m = dirs * (spec.avenue_travel_lanes * spec.lane_width_m + (spec.parking_lanes ? spec.parking_width_m : 0.f) +
                           (bike ? spec.bike_width_m : 0.f));
      at.speed_mph = static_cast<uint8_t>(spec.avenue_speed_mph);
      at.bike_lane = bike ? BikeLane::Protected : BikeLane::None;
      at.borough = 1;
      at.flags = spec.commercial_avenues ? kSegCommercial : 0u;
      g.addSegment(seg, a, b, pts, 2, at, name);
      if (two_way || north) addLanesForSegment(seg, +1, spec.avenue_travel_lanes, spec.parking_lanes, bike, av_speed, a, b, 0.f, 1.f, true, i, j);
      if (two_way || !north) addLanesForSegment(seg, -1, spec.avenue_travel_lanes, spec.parking_lanes, bike, av_speed, a, b, 0.f, 1.f, true, i, j);
    }
  }
  // ---- street segments (west → east geometry)
  for (int j = 0; j < spec.streets; ++j) {
    const bool east = streetEastbound(j);
    streetName(spec, j, name, sizeof name);
    for (int i = 0; i + 1 < spec.avenues; ++i) {
      const SegmentId seg = streetSegmentId(i, j);
      const NodeId a = nodeId(i, j), b = nodeId(i + 1, j);
      Vec3 pts[2] = {{spec.origin_x + i * spec.avenue_spacing_m, spec.origin_y + j * spec.street_spacing_m, 0.f},
                     {spec.origin_x + (i + 1) * spec.avenue_spacing_m, spec.origin_y + j * spec.street_spacing_m, 0.f}};
      SegmentAttrs at;
      at.rw_type = RwType::Street;
      at.traffic_dir = east ? TrafficDir::Forward : TrafficDir::Backward;
      at.travel_lanes = static_cast<uint8_t>(spec.street_travel_lanes);
      at.park_lanes = static_cast<uint8_t>(spec.parking_lanes ? 1 : 0);
      at.width_m = spec.street_travel_lanes * spec.lane_width_m + (spec.parking_lanes ? spec.parking_width_m : 0.f) + 3.f;
      at.speed_mph = static_cast<uint8_t>(spec.street_speed_mph);
      at.borough = 1;
      g.addSegment(seg, a, b, pts, 2, at, name);
      addLanesForSegment(seg, east ? +1 : -1, spec.street_travel_lanes, spec.parking_lanes, false, st_speed, a, b, 1.f, 0.f, false, i, j);
    }
  }

  // ---- junction lanes
  // Index lanes by start/end node.
  const size_t node_count = static_cast<size_t>(spec.avenues) * spec.streets;
  std::vector<std::vector<uint32_t>> incoming(node_count), outgoing(node_count);
  auto nodeSlot = [&](NodeId id) { return static_cast<size_t>(id - 1) / 1000 * spec.avenues + static_cast<size_t>((id - 1) % 1000); };
  for (uint32_t r = 0; r < recs.size(); ++r) {
    incoming[nodeSlot(recs[r].end)].push_back(r);
    outgoing[nodeSlot(recs[r].start)].push_back(r);
  }
  std::vector<JlRec> jls;
  LaneId next_jl = 1000000000LL;
  std::vector<uint32_t> node_jl_begin(node_count + 1, 0);

  auto maxIndexOfKinds = [&](const LaneRec& a, bool with_bike) {
    int mx = -1;
    for (const LaneRec& r : recs)
      if (r.seg == a.seg && r.dir == a.dir && (r.kind == LaneKind::Travel || (with_bike && r.kind == LaneKind::Bike))) mx = std::max(mx, r.index);
    return mx;
  };
  auto findLane = [&](SegmentId seg, int dir, LaneKind kind, int index) -> int {
    for (uint32_t r = 0; r < recs.size(); ++r)
      if (recs[r].seg == seg && recs[r].dir == dir && recs[r].kind == kind && recs[r].index == index) return static_cast<int>(r);
    return -1;
  };
  auto maxTravelIndex = [&](SegmentId seg, int dir) {
    int mx = -1;
    for (const LaneRec& r : recs)
      if (r.seg == seg && r.dir == dir && r.kind == LaneKind::Travel) mx = std::max(mx, r.index);
    return mx;
  };
  auto bikeLane = [&](SegmentId seg, int dir) -> int {
    for (uint32_t r = 0; r < recs.size(); ++r)
      if (recs[r].seg == seg && recs[r].dir == dir && recs[r].kind == LaneKind::Bike) return static_cast<int>(r);
    return -1;
  };

  for (size_t ns = 0; ns < node_count; ++ns) {
    node_jl_begin[ns] = static_cast<uint32_t>(jls.size());
    const int gi = static_cast<int>(ns % spec.avenues), gj = static_cast<int>(ns / spec.avenues);
    const NodeId nid = nodeId(gi, gj);
    const bool stop_node = streetStopControlled(spec, gj);
    for (uint32_t ai : incoming[ns]) {
      const LaneRec& a = recs[ai];
      if (a.kind == LaneKind::Parking) continue;
      // group outgoing by (segment, dir)
      for (uint32_t bi : outgoing[ns]) {
        const LaneRec& b = recs[bi];
        if (b.kind == LaneKind::Parking) continue;
        if (b.seg == a.seg && !spec.allow_uturns) continue;
        const float dot = a.dx * b.dx + a.dy * b.dy;
        const float cross = a.dx * b.dy - a.dy * b.dx;
        TurnType turn;
        if (dot > 0.7f) turn = TurnType::Straight;
        else if (dot < -0.7f) turn = TurnType::UTurn;
        else turn = cross > 0.f ? TurnType::Left : TurnType::Right;
        // ---- pairing rules (one junction lane per (a, target segment))
        int target = -1;
        switch (turn) {
          case TurnType::Straight: {
            if (a.kind == LaneKind::Bike) {
              const int bl = bikeLane(b.seg, b.dir);
              target = bl >= 0 ? bl : findLane(b.seg, b.dir, LaneKind::Travel, maxTravelIndex(b.seg, b.dir));
            } else {
              const int idx = std::min(a.index, maxTravelIndex(b.seg, b.dir));
              target = findLane(b.seg, b.dir, LaneKind::Travel, idx);
            }
            break;
          }
          case TurnType::Right: {
            if (a.index != maxIndexOfKinds(a, true)) break;  // only the rightmost travel/bike lane turns right
            if (a.kind == LaneKind::Bike) {
              const int bl = bikeLane(b.seg, b.dir);
              target = bl >= 0 ? bl : findLane(b.seg, b.dir, LaneKind::Travel, maxTravelIndex(b.seg, b.dir));
            } else {
              target = findLane(b.seg, b.dir, LaneKind::Travel, maxTravelIndex(b.seg, b.dir));
            }
            break;
          }
          case TurnType::Left: {
            if (a.kind != LaneKind::Travel || a.index != 0) break;  // leftmost travel lane only
            target = findLane(b.seg, b.dir, LaneKind::Travel, 0);
            break;
          }
          case TurnType::UTurn: {
            if (!spec.allow_uturns || a.kind != LaneKind::Travel || a.index != 0) break;
            target = findLane(b.seg, b.dir, LaneKind::Travel, 0);
            break;
          }
        }
        if (target < 0 || static_cast<uint32_t>(target) != bi) continue;  // emit once, for the chosen target only
        JlRec j;
        j.id = next_jl++;
        j.from_rec = ai;
        j.to_rec = bi;
        j.turn = turn;
        j.group = stop_node ? -1 : (a.is_avenue ? 0 : 1);
        j.node = nid;
        jls.push_back(j);
      }
    }
  }
  node_jl_begin[node_count] = static_cast<uint32_t>(jls.size());

  // ---- yield lists and registration
  std::vector<LaneId> yields;
  for (size_t ns = 0; ns < node_count; ++ns) {
    const int gj = static_cast<int>(ns / spec.avenues);
    const bool stop_node = streetStopControlled(spec, gj);
    for (uint32_t k = node_jl_begin[ns]; k < node_jl_begin[ns + 1]; ++k) {
      const JlRec& J = jls[k];
      const LaneRec& jf = recs[J.from_rec];
      const LaneRec& jt = recs[J.to_rec];
      yields.clear();
      for (uint32_t m = node_jl_begin[ns]; m < node_jl_begin[ns + 1]; ++m) {
        if (m == k) continue;
        const JlRec& K = jls[m];
        const LaneRec& kf = recs[K.from_rec];
        const LaneRec& kt = recs[K.to_rec];
        const float opposing = jf.dx * kf.dx + jf.dy * kf.dy;  // < -0.7 → opposite approach
        if (J.turn == TurnType::Left && opposing < -0.7f &&
            (K.turn == TurnType::Straight || (K.turn == TurnType::Right && kt.seg == jt.seg)))
          yields.push_back(K.id);
        if (stop_node && !jf.is_avenue && kf.is_avenue) yields.push_back(K.id);  // minor street yields to the avenue
      }
      g.addJunctionLane(J.id, jf.id, jt.id, J.turn, J.group, nullptr, 0, yields.empty() ? nullptr : yields.data(), yields.size());
    }
  }

  if (!g.finalize()) {
    if (error) *error = g.lastError();
    return false;
  }
  for (uint32_t li = 0; li < g.laneCount(); ++li) g.setLaneNta(li, 0);

  // ---- signals
  const float street_width = spec.street_travel_lanes * spec.lane_width_m + (spec.parking_lanes ? spec.parking_width_m : 0.f) + 3.f;
  for (size_t ns = 0; ns < node_count; ++ns) {
    const int gi = static_cast<int>(ns % spec.avenues), gj = static_cast<int>(ns / spec.avenues);
    if (streetStopControlled(spec, gj)) continue;
    bool has0 = false, has1 = false;
    for (uint32_t k = node_jl_begin[ns]; k < node_jl_begin[ns + 1]; ++k) {
      if (jls[k].group == 0) has0 = true;
      if (jls[k].group == 1) has1 = true;
    }
    if (!has0 && !has1) continue;
    const int ng = (has0 ? 1 : 0) + (has1 ? 1 : 0);
    const float split = spec.cycle_s / static_cast<float>(ng);
    SignalPhase ph[2];
    int n = 0;
    const bool two_way = avenueTwoWay(spec, gi), bike = avenueHasBikeLane(spec, gi);
    const float avenue_width = (two_way ? 2.f : 1.f) * (spec.avenue_travel_lanes * spec.lane_width_m +
                                                       (spec.parking_lanes ? spec.parking_width_m : 0.f) + (bike ? spec.bike_width_m : 0.f));
    for (int grp = 0; grp < 2; ++grp) {
      if ((grp == 0 && !has0) || (grp == 1 && !has1)) continue;
      SignalPhase p;
      p.group = grp;
      p.lpi_s = spec.lpi_s;
      p.yellow_s = spec.yellow_s;
      p.allred_s = spec.allred_s;
      p.green_s = std::max(5.f, split - p.lpi_s - p.yellow_s - p.allred_s);
      // pedestrians walking parallel to this group's vehicles cross the OTHER street
      const float crossing = grp == 0 ? street_width : avenue_width;
      const float clearance = p.lpi_s + p.green_s + p.yellow_s;
      p.ped_flash_s = std::min(clearance, std::max(7.f, crossing / 1.07f));
      p.ped_walk_s = std::max(0.f, clearance - p.ped_flash_s);
      ph[n++] = p;
    }
    float offset = 0.f;
    if (spec.progression_speed_mps > 0.1f) {
      const bool north = two_way || avenueNorthbound(gi);
      const int steps = north ? gj : (spec.streets - 1 - gj);
      offset = std::fmod(static_cast<float>(steps) * spec.street_spacing_m / spec.progression_speed_mps, spec.cycle_s);
    }
    signals.addPlan(nodeId(gi, gj), static_cast<int32_t>(ns), offset, ph, static_cast<size_t>(n));
  }
  if (!signals.bind(g)) {
    if (error) *error = signals.lastError();
    return false;
  }
  return true;
}

}  // namespace traffic
}  // namespace nycsim
