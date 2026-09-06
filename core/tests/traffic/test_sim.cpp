// Whole-simulation behaviour: determinism, collision freedom, saturation flow,
// bus dwell, emergency yielding, double parking, honking, player reaction,
// re-routing, density convergence and the spawn/despawn ring.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "GridWorld.h"

using namespace nycsim;
using namespace nycsim::traffic;
using nycsim_test::countCollisions;
using nycsim_test::GridWorld;

namespace {

SyntheticGridSpec gridSpec(int avenues, int streets) {
  SyntheticGridSpec s;
  s.avenues = avenues;
  s.streets = streets;
  s.bike_lane_every = 3;
  s.commercial_avenues = true;
  return s;
}

uint32_t laneIndexOf(const routing::RoadGraph& g, routing::SegmentId seg, int index, int direction) {
  return g.laneIndex(SyntheticGrid::laneId(seg, index, direction));
}

}  // namespace

TEST_SUITE("traffic") {

TEST_CASE("the same seed replays the same trajectories") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(gridSpec(5, 8), 30.f, 0.f, true), w.error);
  TrafficConfig cfg;
  cfg.max_vehicles = 500;
  cfg.use_player_ring = false;

  auto run = [&](uint64_t seed, uint32_t steps) {
    TrafficSim sim;
    REQUIRE(sim.configure(w.graph, w.signals, cfg, seed));
    sim.setDensityTable(&w.density);
    sim.setRouter(&w.router);
    sim.setTimeOfDay(9.f * 3600.f, 0);
    sim.prefill();
    std::vector<uint64_t> hashes;
    for (uint32_t i = 0; i < steps; ++i) {
      sim.step();
      if (i % 100 == 0) hashes.push_back(sim.trajectoryHash());
    }
    hashes.push_back(sim.trajectoryHash());
    return hashes;
  };

  const std::vector<uint64_t> a = run(12345u, 1200);
  const std::vector<uint64_t> b = run(12345u, 1200);
  const std::vector<uint64_t> c = run(999u, 1200);
  REQUIRE(a.size() == b.size());
  CHECK(a == b);
  CHECK(a.back() != 0u);
  CHECK(a != c);
}

TEST_CASE("ten minutes of two thousand vehicles in Midtown without a collision") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(gridSpec(10, 20), 21.f, 0.f, true), w.error);
  TrafficConfig cfg;
  cfg.max_vehicles = 2600;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE_MESSAGE(sim.configure(w.graph, w.signals, cfg, 606060u), sim.lastError());
  sim.setDensityTable(&w.density);
  sim.setRouter(&w.router);
  sim.setTimeOfDay(8.f * 3600.f, 0);
  const uint32_t filled = sim.prefill();
  MESSAGE("prefilled " << filled << " vehicles, target " << sim.targetVehicles());
  CHECK(filled > 1500u);

  uint32_t collisions = 0;
  uint32_t worst = 0;
  float min_mean_speed = 1e9f;
  for (int i = 0; i < 12000; ++i) {  // 10 minutes at 20 Hz
    sim.step();
    if (i % 4 == 0) {  // 5 Hz sampling: a real overlap persists far longer
      const uint32_t c = countCollisions(sim);
      collisions += c;
      worst = std::max(worst, c);
    }
    min_mean_speed = std::min(min_mean_speed, sim.stats().mean_speed_mps);
  }
  MESSAGE("vehicles " << sim.stats().vehicles << ", collisions " << collisions << " (worst step " << worst
                      << "), mean speed " << sim.stats().mean_speed_mps << " m/s, honks "
                      << sim.stats().honks << ", lane changes " << sim.stats().lane_changes);
  CHECK(sim.stats().vehicles > 1500u);
  CHECK(collisions == 0u);
  CHECK(sim.stats().mean_speed_mps > 1.0f);  // the network must not gridlock
}

TEST_CASE("saturation flow of a signalized approach is in the HCM range") {
  SyntheticGridSpec spec = gridSpec(4, 5);
  spec.avenue_spacing_m = 300.f;  // long street segments so a queue fits
  spec.stop_sign_every = 0;
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;

  // Eastbound street 2, approach from avenue 0 to avenue 1, continuing east.
  const uint32_t approach = laneIndexOf(g, SyntheticGrid::streetSegmentId(0, 2), 0, +1);
  const uint32_t onward = laneIndexOf(g, SyntheticGrid::streetSegmentId(1, 2), 0, +1);
  REQUIRE(approach != routing::kInvalidIndex);
  REQUIRE(onward != routing::kInvalidIndex);
  const uint32_t junction = g.junctionBetween(approach, onward);
  REQUIRE(junction != routing::kInvalidIndex);

  TrafficConfig cfg;
  cfg.max_vehicles = 400;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE(sim.configure(g, w.signals, cfg, 77u));
  sim.setRouter(&w.router);
  sim.setTimeOfDay(8.f * 3600.f, 0);

  const float lane_len = g.lane(approach).length_m;
  std::unordered_map<uint32_t, uint32_t> last_lane;
  uint32_t crossings = 0;
  double green_s = 0.0;
  for (int i = 0; i < 24000; ++i) {  // 20 minutes = 13 cycles
    // Keep the queue saturated: refill the back of the approach lane.
    float min_s = 1e9f;
    for (size_t k = 0; k < sim.vehicleCount(); ++k)
      if (sim.vehicle(k).lane == approach) min_s = std::min(min_s, sim.vehicle(k).s);
    if (min_s > 12.f) sim.spawn(VehicleClass::Sedan, approach, 3.f, onward, lane_len * 0.5f);

    sim.step();
    if (sim.laneSignal(junction) == VehSignal::Green) green_s += static_cast<double>(cfg.dt);
    for (size_t k = 0; k < sim.vehicleCount(); ++k) {
      const Vehicle& v = sim.vehicle(k);
      const auto it = last_lane.find(v.id);
      const uint32_t prev = it == last_lane.end() ? routing::kInvalidIndex : it->second;
      last_lane[v.id] = v.lane;
      if (prev == approach && v.lane == junction) ++crossings;
    }
  }
  const double flow = green_s > 1.0 ? static_cast<double>(crossings) / green_s * 3600.0 : 0.0;
  MESSAGE("discharged " << crossings << " vehicles in " << green_s << " s of green → " << flow
                        << " veh/h/lane (HCM base saturation flow 1900 pc/h/ln)");
  CHECK(crossings > 50u);
  CHECK(flow > 600.0);
  CHECK(flow < 2200.0);
}

TEST_CASE("buses follow their route and dwell 15-45 s at every stop") {
  SyntheticGridSpec spec = gridSpec(4, 6);
  spec.avenue_spacing_m = 300.f;
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;

  // A route with four stops along eastbound street 2.
  BusRouteTable buses;
  uint16_t headway[24];
  for (int h = 0; h < 24; ++h) headway[h] = 6;
  const uint32_t route = buses.addRoute("M42", headway);
  int64_t stop_id = 1;
  uint32_t stops_added = 0;
  for (int i = 0; i < 3; ++i) {
    const uint32_t lane = laneIndexOf(g, SyntheticGrid::streetSegmentId(i, 2), 0, +1);
    REQUIRE(lane != routing::kInvalidIndex);
    for (float frac : {0.35f, 0.75f}) {
      const float s = g.lane(lane).length_m * frac;
      const routing::LanePose p = g.poseAt(lane, s);
      buses.addStop(route, stop_id++, lane, s, p.pos, "stop", true);
      ++stops_added;
    }
  }
  buses.finalize();
  CHECK(buses.stopCount() == stops_added);
  CHECK(buses.headwaySeconds(route, 8) == doctest::Approx(360.f));
  uint32_t n = 0;
  const uint32_t* onlane = buses.stopsOnLane(laneIndexOf(g, SyntheticGrid::streetSegmentId(0, 2), 0, +1), n);
  CHECK(n == 2u);
  REQUIRE(onlane != nullptr);
  CHECK(buses.stop(onlane[0]).s < buses.stop(onlane[1]).s);

  TrafficConfig cfg;
  cfg.max_vehicles = 40;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE(sim.configure(g, w.signals, cfg, 5150u));
  sim.setRouter(&w.router);
  sim.setBusRoutes(&buses);
  sim.setTimeOfDay(10.f * 3600.f, 0);
  const uint32_t bus = sim.spawn(VehicleClass::MtaBus,
                                 laneIndexOf(g, SyntheticGrid::streetSegmentId(0, 2), 0, +1), 5.f);
  REQUIRE(bus != routing::kInvalidIndex);
  REQUIRE(sim.byId(bus) != nullptr);
  CHECK(sim.byId(bus)->bus_route == route);

  std::vector<float> dwells;
  float current = 0.f;
  bool dwelling = false;
  float travelled = 0.f;
  for (int i = 0; i < 24000; ++i) {
    sim.step();
    const Vehicle* v = sim.byId(bus);
    if (v == nullptr) break;
    travelled = v->distance_m;
    const bool now = v->state == DriveState::BusDwelling;
    if (now) {
      current += cfg.dt;
    } else if (dwelling) {
      dwells.push_back(current);
      current = 0.f;
    }
    dwelling = now;
  }
  MESSAGE("bus dwells: " << dwells.size() << ", travelled " << travelled << " m");
  CHECK(dwells.size() >= 3u);
  CHECK(travelled > 400.f);
  for (float d : dwells) {
    CHECK(d >= cfg.bus_dwell_min_s - 0.2f);
    CHECK(d <= cfg.bus_dwell_max_s + 1.5f);
  }
}

TEST_CASE("traffic pulls right for an emergency vehicle") {
  SyntheticGridSpec spec = gridSpec(4, 6);
  spec.avenue_spacing_m = 300.f;
  spec.avenue_travel_lanes = 3;
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;
  const routing::SegmentId seg = SyntheticGrid::streetSegmentId(0, 2);
  const uint32_t lane = laneIndexOf(g, seg, 0, +1);
  REQUIRE(lane != routing::kInvalidIndex);
  const float len = g.lane(lane).length_m;

  TrafficConfig cfg;
  cfg.max_vehicles = 60;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE(sim.configure(g, w.signals, cfg, 31337u));
  sim.setRouter(&w.router);
  sim.setTimeOfDay(14.f * 3600.f, 0);

  std::vector<uint32_t> traffic_ids;
  for (int k = 0; k < 8; ++k) {
    const uint32_t id = sim.spawn(VehicleClass::Sedan, lane, 40.f + static_cast<float>(k) * 18.f);
    if (id != routing::kInvalidIndex) traffic_ids.push_back(id);
  }
  REQUIRE(traffic_ids.size() >= 6u);
  const uint32_t amb = sim.spawn(VehicleClass::Ambulance, lane, 8.f);
  REQUIRE(amb != routing::kInvalidIndex);
  const_cast<Vehicle*>(sim.byId(amb))->flags |= kVehSiren;

  uint32_t yielding_peak = 0;
  float min_lateral = 0.f;
  for (int i = 0; i < 400; ++i) {
    sim.step();
    uint32_t yielding = 0;
    for (uint32_t id : traffic_ids) {
      const Vehicle* v = sim.byId(id);
      if (v == nullptr) continue;
      if ((v->flags & kVehYieldingEv) != 0) ++yielding;
      min_lateral = std::min(min_lateral, v->lateral);
    }
    yielding_peak = std::max(yielding_peak, yielding);
    if (sim.byId(amb) == nullptr) break;
  }
  MESSAGE("peak vehicles yielding to the siren: " << yielding_peak << ", most-right lateral " << min_lateral
                                                  << " m");
  CHECK(yielding_peak >= 2u);
  CHECK(min_lateral < -0.2f);  // pulled towards the kerb
  CHECK(len > 100.f);
}

TEST_CASE("double parking frequency follows the configured rate") {
  SyntheticGridSpec spec = gridSpec(6, 10);
  spec.commercial_avenues = true;
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 26.f, 0.f, true), w.error);

  auto run = [&](float scale) {
    TrafficConfig cfg;
    cfg.max_vehicles = 900;
    cfg.use_player_ring = false;
    cfg.double_park_scale = scale;
    TrafficSim sim;
    REQUIRE(sim.configure(w.graph, w.signals, cfg, 20240401u));
    sim.setDensityTable(&w.density);
    sim.setRouter(&w.router);
    sim.setTimeOfDay(11.f * 3600.f, 0);
    sim.prefill();
    uint32_t peak = 0;
    for (int i = 0; i < 6000; ++i) {
      sim.step();
      peak = std::max(peak, sim.stats().double_parked);
    }
    return peak;
  };

  const uint32_t none = run(0.f);
  const uint32_t normal = run(1.f);
  const uint32_t heavy = run(6.f);
  MESSAGE("double-parked peak — off: " << none << ", nominal: " << normal << ", 6x: " << heavy);
  CHECK(none == 0u);
  CHECK(normal > 0u);
  CHECK(heavy > normal);
}

TEST_CASE("fleet density converges to the calibration table") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(gridSpec(8, 14), 24.f, 0.f, true), w.error);
  TrafficConfig cfg;
  cfg.max_vehicles = 2200;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE(sim.configure(w.graph, w.signals, cfg, 4711u));
  sim.setDensityTable(&w.density);
  sim.setRouter(&w.router);
  sim.setTimeOfDay(8.f * 3600.f, 0);

  // From an empty world, the spawner must reach the target and hold it.
  for (int i = 0; i < 7200; ++i) sim.step();  // six simulated minutes
  const float target = sim.targetVehicles();
  const float got = static_cast<float>(sim.stats().vehicles);
  const float measured = sim.measuredDensity(0);
  MESSAGE("target " << target << " vehicles, present " << got << ", measured density " << measured
                    << " veh/km/lane (table 24)");
  REQUIRE(target > 100.f);
  CHECK(got > target * 0.85f);
  CHECK(got < target * 1.05f);
  CHECK(measured > 24.f * 0.75f);
  CHECK(measured < 24.f * 1.10f);

  // Halving the table halves the fleet.
  DensityCell low;
  low.veh_per_km_lane = 10.f;
  low.taxi_share = 0.15f;
  w.density.fill(0, low);
  sim.setDensityTable(&w.density);
  for (int i = 0; i < 12000; ++i) sim.step();
  MESSAGE("after halving: target " << sim.targetVehicles() << ", present " << sim.stats().vehicles);
  CHECK(static_cast<float>(sim.stats().vehicles) < target * 0.7f);
}

TEST_CASE("no agent is created or removed inside the player's protected region") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(gridSpec(8, 14), 22.f, 0.f, true), w.error);
  TrafficConfig cfg;
  cfg.max_vehicles = 1500;
  cfg.use_player_ring = true;
  // A tight streaming band so the ring is exercised hard: agents are recycled
  // as soon as they fall 500 m behind the player, and re-created ahead of him.
  cfg.spawn_outer_m = 450.f;
  cfg.despawn_m = 500.f;
  TrafficSim sim;
  REQUIRE(sim.configure(w.graph, w.signals, cfg, 8080u));
  sim.setDensityTable(&w.density);
  sim.setRouter(&w.router);
  sim.setTimeOfDay(18.f * 3600.f, 0);

  PlayerProxy player;
  player.valid = true;
  float minx, miny, maxx, maxy;
  w.graph.bounds(minx, miny, maxx, maxy);
  player.x = minx + 200.f;
  player.y = (miny + maxy) * 0.5f;
  player.heading_rad = 0.f;
  player.speed_mps = 9.f;
  sim.setPlayer(player);
  sim.prefill();

  std::unordered_map<uint32_t, routing::Vec3> known;
  for (size_t i = 0; i < sim.vehicleCount(); ++i) known[sim.vehicle(i).id] = sim.vehicle(i).pos;
  uint32_t bad_spawn = 0, bad_despawn = 0, spawns = 0, despawns = 0;
  for (int i = 0; i < 4000; ++i) {
    // The player drives east and keeps turning, so the protected cone both
    // sweeps and translates over the network.
    player.heading_rad += 0.004f;
    player.x += player.speed_mps * cfg.dt * std::cos(player.heading_rad) * 0.5f;
    player.y += player.speed_mps * cfg.dt * std::sin(player.heading_rad) * 0.5f;
    player.x = std::min(player.x, maxx - 200.f);
    player.y = std::max(std::min(player.y, maxy - 100.f), miny + 100.f);
    sim.setPlayer(player);
    sim.step();
    std::unordered_set<uint32_t> live;
    for (size_t k = 0; k < sim.vehicleCount(); ++k) {
      const Vehicle& v = sim.vehicle(k);
      live.insert(v.id);
      if (known.find(v.id) == known.end()) {
        ++spawns;
        if (player.inProtectedRegion(v.pos.x, v.pos.y)) ++bad_spawn;
      }
      known[v.id] = v.pos;
    }
    for (auto it = known.begin(); it != known.end();) {
      if (live.count(it->first) == 0) {
        ++despawns;
        if (player.inProtectedRegion(it->second.x, it->second.y)) ++bad_despawn;
        it = known.erase(it);
      } else {
        ++it;
      }
    }
  }
  MESSAGE("spawns " << spawns << " (violations " << bad_spawn << "), despawns " << despawns
                    << " (violations " << bad_despawn << ")");
  CHECK(spawns > 20u);
  CHECK(despawns > 20u);
  CHECK(bad_spawn == 0u);
  CHECK(bad_despawn == 0u);
}

TEST_CASE("drivers brake for the player and stop for a person in the road") {
  SyntheticGridSpec spec = gridSpec(4, 6);
  spec.avenue_spacing_m = 300.f;
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;
  const uint32_t lane = laneIndexOf(g, SyntheticGrid::streetSegmentId(0, 2), 0, +1);
  REQUIRE(lane != routing::kInvalidIndex);

  SUBCASE("stalled player car becomes a leader") {
    TrafficConfig cfg;
    cfg.max_vehicles = 20;
    cfg.use_player_ring = false;
    TrafficSim sim;
    REQUIRE(sim.configure(g, w.signals, cfg, 606u));
    sim.setTimeOfDay(12.f * 3600.f, 0);
    PlayerProxy p;
    p.valid = true;
    const routing::LanePose stall = g.poseAt(lane, 150.f);
    p.x = stall.pos.x;
    p.y = stall.pos.y;
    p.heading_rad = stall.heading_rad;
    p.speed_mps = 0.f;
    sim.setPlayer(p);
    const uint32_t id = sim.spawn(VehicleClass::Sedan, lane, 20.f, routing::kInvalidIndex, 0.f, true);
    REQUIRE(id != routing::kInvalidIndex);
    float closest = 1e9f;
    for (int i = 0; i < 600; ++i) {
      sim.step();
      const Vehicle* v = sim.byId(id);
      if (v == nullptr || v->lane != lane) break;
      closest = std::min(closest, 150.f - v->s);
    }
    const Vehicle* v = sim.byId(id);
    REQUIRE(v != nullptr);
    MESSAGE("closest approach to the stalled player: " << closest << " m, final speed " << v->speed);
    CHECK(closest > 0.5f);
    CHECK(v->speed < 1.0f);
  }

  SUBCASE("player on foot stops the traffic further back") {
    TrafficConfig cfg;
    cfg.max_vehicles = 20;
    cfg.use_player_ring = false;
    TrafficSim sim;
    REQUIRE(sim.configure(g, w.signals, cfg, 607u));
    sim.setTimeOfDay(12.f * 3600.f, 0);
    PlayerProxy p;
    p.valid = true;
    const routing::LanePose stall = g.poseAt(lane, 150.f);
    p.x = stall.pos.x;
    p.y = stall.pos.y;
    p.heading_rad = stall.heading_rad + 1.5f;
    p.speed_mps = 0.f;
    p.on_foot = true;
    p.half_length_m = 0.3f;
    p.half_width_m = 0.3f;
    sim.setPlayer(p);
    const uint32_t id = sim.spawn(VehicleClass::Sedan, lane, 20.f, routing::kInvalidIndex, 0.f, true);
    REQUIRE(id != routing::kInvalidIndex);
    for (int i = 0; i < 600; ++i) {
      sim.step();
      const Vehicle* v = sim.byId(id);
      if (v == nullptr || v->lane != lane) break;
    }
    const Vehicle* v = sim.byId(id);
    REQUIRE(v != nullptr);
    const float gap = 150.f - v->s;
    MESSAGE("stopped " << gap << " m short of the person in the road");
    CHECK(gap > cfg.player_person_stop_m * 0.5f);
    CHECK(v->speed < 0.6f);
  }
}

TEST_CASE("blocked drivers honk") {
  SyntheticGridSpec spec = gridSpec(4, 6);
  spec.avenue_spacing_m = 300.f;
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;
  const uint32_t lane = laneIndexOf(g, SyntheticGrid::streetSegmentId(0, 2), 0, +1);

  TrafficConfig cfg;
  cfg.max_vehicles = 60;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE(sim.configure(g, w.signals, cfg, 909u));
  sim.setTimeOfDay(12.f * 3600.f, 0);
  // A stalled player car with a queue of taxis behind it.
  PlayerProxy p;
  p.valid = true;
  const routing::LanePose stall = g.poseAt(lane, 200.f);
  p.x = stall.pos.x;
  p.y = stall.pos.y;
  p.heading_rad = stall.heading_rad;
  sim.setPlayer(p);
  for (int k = 0; k < 8; ++k)
    sim.spawn(VehicleClass::Taxi, lane, 190.f - static_cast<float>(k) * 9.f, routing::kInvalidIndex, 0.f, true);

  uint32_t blocked_honks = 0, player_honks = 0;
  for (int i = 0; i < 2400; ++i) {
    sim.step();
    uint32_t n = 0;
    const HonkEvent* ev = sim.honks(n);
    for (uint32_t k = 0; k < n; ++k) {
      if (ev[k].reason == HonkReason::Blocked) ++blocked_honks;
      if (ev[k].reason == HonkReason::Player) ++player_honks;
    }
  }
  MESSAGE("honks — blocked: " << blocked_honks << ", player: " << player_honks);
  CHECK(blocked_honks > 0u);
  CHECK(sim.stats().honks > 0u);
}

TEST_CASE("a blocked route is re-planned around the obstruction") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(gridSpec(6, 8), 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;
  std::vector<uint32_t> travel;
  for (uint32_t li = 0; li < g.roadLaneCount(); ++li)
    if (g.lane(li).kind == routing::LaneKind::Travel) travel.push_back(li);
  REQUIRE(travel.size() > 40u);

  routing::RouteQuery q;
  q.from_lane = travel.front();
  q.from_s = 1.f;
  q.to_lane = travel[travel.size() / 2];
  q.to_s = 5.f;
  routing::RouteResult first;
  REQUIRE(w.router.route(q, first));
  REQUIRE(first.lanes.size() > 3u);

  // Avoid a lane in the middle of that route: the router must go round it.
  const uint32_t blocked = first.lanes[first.lanes.size() / 2];
  q.profile.avoid_lane = blocked;
  q.profile.avoid_penalty_s = 900.f;
  routing::RouteResult second;
  REQUIRE(w.router.route(q, second));
  CHECK(second.ok);
  bool used = false;
  for (uint32_t lane : second.lanes) used = used || lane == blocked;
  MESSAGE("original " << first.lanes.size() << " lanes / " << first.cost_s << " s, detour "
                      << second.lanes.size() << " lanes / " << second.cost_s << " s");
  CHECK_FALSE(used);
  CHECK(second.cost_s >= first.cost_s - 1e-3f);
}

TEST_CASE("cyclists prefer bike lanes") {
  SyntheticGridSpec spec = gridSpec(6, 10);
  spec.bike_lane_every = 2;  // every other avenue has a protected bike lane
  GridWorld w;
  REQUIRE_MESSAGE(w.build(spec, 0.f, 0.f, true), w.error);
  const routing::RoadGraph& g = w.graph;
  TrafficConfig cfg;
  cfg.max_vehicles = 120;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE(sim.configure(g, w.signals, cfg, 2468u));
  sim.setRouter(&w.router);
  sim.setTimeOfDay(9.f * 3600.f, 0);

  // Put cyclists in the leftmost travel lane of an avenue that has a bike lane.
  std::vector<uint32_t> ids;
  for (int j = 0; j < 6; ++j) {
    const routing::SegmentId seg = SyntheticGrid::avenueSegmentId(0, j);
    const uint32_t lane = laneIndexOf(g, seg, 0, +1);
    if (lane == routing::kInvalidIndex) continue;
    // Deliberately dropped into the leftmost motor lane: the cyclist has to
    // work its way right, across the parking lane, into the protected lane.
    CHECK(g.lane(lane).kind == routing::LaneKind::Travel);
    const uint32_t id = sim.spawn(VehicleClass::Cyclist, lane, 20.f);
    if (id != routing::kInvalidIndex) ids.push_back(id);
  }
  REQUIRE(ids.size() >= 4u);
  uint32_t on_bike_lane = 0;
  for (int i = 0; i < 2000; ++i) sim.step();
  for (uint32_t id : ids) {
    const Vehicle* v = sim.byId(id);
    if (v == nullptr) continue;
    if (g.lane(v->lane).kind == routing::LaneKind::Bike) ++on_bike_lane;
  }
  MESSAGE(on_bike_lane << " of " << ids.size() << " cyclists ended up in a bike lane");
  CHECK(on_bike_lane * 2u >= static_cast<uint32_t>(ids.size()));
}

}  // TEST_SUITE
