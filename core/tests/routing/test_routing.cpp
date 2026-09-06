// Lane graph and router: structural invariants, geometry round trips and route
// connectivity on the synthetic Midtown grid.
#include <doctest/doctest.h>

#include <cmath>
#include <vector>

#include "../traffic/GridWorld.h"

using namespace nycsim;
using namespace nycsim::routing;
using nycsim_test::GridWorld;

namespace {

traffic::SyntheticGridSpec smallSpec() {
  traffic::SyntheticGridSpec s;
  s.avenues = 5;
  s.streets = 8;
  s.bike_lane_every = 3;
  s.two_way_avenue_every = 4;
  s.stop_sign_every = 5;
  return s;
}

}  // namespace

TEST_SUITE("routing") {

TEST_CASE("synthetic grid builds a consistent lane graph") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(smallSpec()), w.error);
  const RoadGraph& g = w.graph;
  CHECK(g.finalized());
  CHECK(g.nodeCount() == 5u * 8u);
  CHECK(g.segmentCount() > 0u);
  CHECK(g.roadLaneCount() > 0u);
  CHECK(g.junctionLaneCount() > 0u);
  CHECK(g.laneCount() == g.roadLaneCount() + g.junctionLaneCount());

  uint32_t travel = 0, bike = 0, parking = 0;
  for (uint32_t li = 0; li < g.roadLaneCount(); ++li) {
    const Lane& l = g.lane(li);
    CHECK(l.is_junction == 0);
    CHECK(l.segment != kInvalidIndex);
    CHECK(l.length_m > 0.f);
    CHECK(l.vertex_count >= 2u);
    if (l.kind == LaneKind::Travel) ++travel;
    if (l.kind == LaneKind::Bike) ++bike;
    if (l.kind == LaneKind::Parking) ++parking;
  }
  CHECK(travel > 0u);
  CHECK(bike > 0u);
  CHECK(parking > 0u);

  // Every junction lane is wired both ways and has a plausible geometry.
  for (uint32_t li = static_cast<uint32_t>(g.roadLaneCount()); li < g.laneCount(); ++li) {
    const Lane& jl = g.lane(li);
    REQUIRE(jl.is_junction != 0);
    REQUIRE(jl.from_lane != kInvalidIndex);
    REQUIRE(jl.to_lane != kInvalidIndex);
    CHECK(jl.node != kInvalidIndex);
    CHECK(jl.length_m > 0.5f);
    uint32_t n = 0;
    const uint32_t* succ = g.successors(jl.from_lane, n);
    bool linked = false;
    for (uint32_t k = 0; k < n; ++k) linked = linked || succ[k] == li;
    CHECK(linked);
    const uint32_t* sj = g.successors(li, n);
    bool to_linked = false;
    for (uint32_t k = 0; k < n; ++k) to_linked = to_linked || sj[k] == jl.to_lane;
    CHECK(to_linked);
    CHECK(g.junctionBetween(jl.from_lane, jl.to_lane) == li);
  }
}

TEST_CASE("lane geometry round trips through poseAt / projectOnLane") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(smallSpec()), w.error);
  const RoadGraph& g = w.graph;
  uint32_t checked = 0;
  for (uint32_t li = 0; li < g.laneCount(); li += 7) {
    const Lane& l = g.lane(li);
    for (float f = 0.05f; f < 1.f; f += 0.3f) {
      const float s = l.length_m * f;
      const LanePose p = g.poseAt(li, s);
      float s2 = 0.f, lat = 0.f, dist = 0.f;
      REQUIRE(g.projectOnLane(li, p.pos.x, p.pos.y, s2, lat, dist, 5.f));
      CHECK(std::fabs(s2 - s) < 0.05f);
      CHECK(std::fabs(lat) < 0.05f);
      CHECK(std::fabs(p.dir.x * p.dir.x + p.dir.y * p.dir.y - 1.f) < 1e-3f);
      // Compass and mathematical headings agree.
      const float compass = std::fmod(450.f - p.heading_rad * 57.2957795f, 360.f);
      CHECK(std::fabs(compass - p.compass_deg) < 0.05f);
      // A lateral offset moves left of the travel direction.
      const LanePose q = g.poseAt(li, s, 1.f);
      CHECK(((q.pos.x - p.pos.x) * -p.dir.y + (q.pos.y - p.pos.y) * p.dir.x) > 0.9f);
      ++checked;
    }
  }
  CHECK(checked > 20u);
}

TEST_CASE("nearestLane finds the lane under a point") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(smallSpec()), w.error);
  const RoadGraph& g = w.graph;
  for (uint32_t li = 0; li < g.roadLaneCount(); li += 11) {
    const LanePose p = g.poseAt(li, g.lane(li).length_m * 0.5f);
    const NearestLane n = g.nearestLane(p.pos.x, p.pos.y, kAllLaneKinds, 20.f, false);
    REQUIRE(n.lane != kInvalidIndex);
    CHECK(n.distance < 1.0f);
  }
}

TEST_CASE("router returns connected, plausible routes") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(smallSpec(), 0.f, 0.f, true), w.error);
  const RoadGraph& g = w.graph;
  Router& r = w.router;
  CHECK(r.attached());
  CHECK(r.landmarkCount() > 0u);

  // Collect a few travel lanes spread over the grid.
  std::vector<uint32_t> travel;
  for (uint32_t li = 0; li < g.roadLaneCount(); ++li)
    if (g.lane(li).kind == LaneKind::Travel) travel.push_back(li);
  REQUIRE(travel.size() > 20u);

  uint32_t ok = 0;
  for (size_t k = 0; k + 13 < travel.size(); k += 13) {
    RouteQuery q;
    q.from_lane = travel[k];
    q.from_s = 1.f;
    q.to_lane = travel[k + 13];
    q.to_s = g.lane(travel[k + 13]).length_m * 0.5f;
    RouteResult res;
    if (!r.route(q, res)) continue;
    ++ok;
    REQUIRE(res.ok);
    CHECK(res.lanes.front() == q.from_lane);
    CHECK(res.lanes.back() == q.to_lane);
    CHECK(res.length_m > 0.f);
    CHECK(res.cost_s > 0.f);
    CHECK(res.free_flow_s <= res.cost_s + 1e-3f);
    CHECK(res.polyline.size() >= 2u);
    CHECK(!res.instructions.empty());
    CHECK(res.instructions.front().kind == Instruction::Kind::Depart);
    CHECK(res.instructions.back().kind == Instruction::Kind::Arrive);
    // Consecutive lanes must be joined by a successor edge or a lane change.
    for (size_t i = 0; i + 1 < res.lanes.size(); ++i) {
      const uint32_t a = res.lanes[i], b = res.lanes[i + 1];
      uint32_t n = 0;
      const uint32_t* succ = g.successors(a, n);
      bool linked = false;
      for (uint32_t j = 0; j < n; ++j) linked = linked || succ[j] == b;
      const bool sideways = g.lane(a).left == b || g.lane(a).right == b;
      CHECK_MESSAGE((linked || sideways), "route lanes ", a, " → ", b, " are not connected");
    }
  }
  CHECK(ok >= 3u);
}

TEST_CASE("routePoints snaps addresses onto the network") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(smallSpec(), 0.f, 0.f, true), w.error);
  const RoadGraph& g = w.graph;
  const LanePose a = g.poseAt(0, 5.f);
  uint32_t far = 0;
  for (uint32_t li = 0; li < g.roadLaneCount(); ++li)
    if (g.lane(li).kind == LaneKind::Travel) far = li;
  const LanePose b = g.poseAt(far, g.lane(far).length_m * 0.5f);
  RouteProfile p;
  RouteResult res;
  const bool got = w.router.routePoints(a.pos.x + 3.f, a.pos.y + 3.f, b.pos.x - 2.f, b.pos.y + 2.f, p, res);
  CHECK(got);
  if (got) {
    CHECK(res.length_m > 100.f);
    CHECK(res.eta_s > 10.f);
  }
}

TEST_CASE("turn restrictions and closures are honoured") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(smallSpec(), 0.f, 0.f, true), w.error);
  RoadGraph& g = w.graph;
  // Disable one junction lane and check the router never uses it again.
  uint32_t victim = kInvalidIndex;
  for (uint32_t li = static_cast<uint32_t>(g.roadLaneCount()); li < g.laneCount(); ++li) {
    if (g.lane(li).turn == TurnType::Left) {
      victim = li;
      break;
    }
  }
  REQUIRE(victim != kInvalidIndex);
  g.setLaneDisabled(victim, true);
  CHECK(g.lane(victim).disabled != 0);
  CHECK(!g.laneAllows(victim, kAllLaneKinds));

  RouteQuery q;
  q.from_lane = g.lane(victim).from_lane;
  q.from_s = 0.f;
  q.to_lane = g.lane(victim).to_lane;
  q.to_s = 1.f;
  RouteResult res;
  if (w.router.route(q, res)) {
    for (uint32_t lane : res.lanes) CHECK(lane != victim);
  }
}

}  // TEST_SUITE
