// Signal plans and signal compliance: phase geometry, LPI, all-red, 100 % red
// compliance for the law-abiding classes and "no right turn on red" as a
// property of every run.
#include <doctest/doctest.h>

#include <cmath>
#include <unordered_map>
#include <vector>

#include "GridWorld.h"

using namespace nycsim;
using namespace nycsim::traffic;
using nycsim_test::GridWorld;

namespace {

SyntheticGridSpec midtownSpec(int avenues, int streets) {
  SyntheticGridSpec s;
  s.avenues = avenues;
  s.streets = streets;
  s.bike_lane_every = 3;
  s.cycle_s = 90.f;
  s.lpi_s = 7.f;
  return s;
}

// Runs a simulation and reports every transition from a road lane into a
// junction lane together with the signal state at that instant.
struct EntryMonitor {
  const TrafficSim* sim = nullptr;
  const routing::RoadGraph* graph = nullptr;
  std::unordered_map<uint32_t, uint32_t> last_lane;
  uint32_t entries = 0;
  uint32_t red_entries_law_abiding = 0;
  uint32_t red_entries_total = 0;
  uint32_t right_on_red = 0;
  uint32_t green_entries = 0;
  uint32_t yellow_entries = 0;

  void sample() {
    for (size_t i = 0; i < sim->vehicleCount(); ++i) {
      const Vehicle& v = sim->vehicle(i);
      const auto it = last_lane.find(v.id);
      const uint32_t prev = it == last_lane.end() ? routing::kInvalidIndex : it->second;
      last_lane[v.id] = v.lane;
      if (prev == v.lane || prev == routing::kInvalidIndex) continue;
      const routing::Lane& l = graph->lane(v.lane);
      if (l.is_junction == 0) continue;
      ++entries;
      const VehSignal sig = sim->laneSignal(v.lane);
      if (sig == VehSignal::Green) ++green_entries;
      if (sig == VehSignal::Yellow) ++yellow_entries;
      if (sig != VehSignal::Red) continue;
      ++red_entries_total;
      if ((v.flags & kVehSiren) != 0) continue;  // NY VTL §1104 exemption
      if ((v.flags & kVehLawAbiding) != 0) ++red_entries_law_abiding;
      if (l.turn == routing::TurnType::Right) ++right_on_red;
    }
  }
};

}  // namespace

TEST_SUITE("traffic") {

TEST_CASE("signal plans have a conflict-free two-phase geometry") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(midtownSpec(4, 6)), w.error);
  const SignalTable& t = w.signals;
  REQUIRE(t.planCount() > 0u);
  for (uint32_t pi = 0; pi < t.planCount(); ++pi) {
    const SignalPlan& plan = t.plan(pi);
    CHECK(plan.node_index != routing::kInvalidIndex);
    uint32_t n = 0;
    const SignalPhase* ph = t.phases(pi, n);
    REQUIRE(n >= 1u);
    float total = 0.f;
    for (uint32_t k = 0; k < n; ++k) {
      CHECK(ph[k].green_s > 0.f);
      CHECK(ph[k].yellow_s == doctest::Approx(3.0f));   // NYC DOT standard
      CHECK(ph[k].allred_s == doctest::Approx(2.0f));
      CHECK(ph[k].lpi_s == doctest::Approx(7.0f));      // LPI where flagged
      // The pedestrian clearance is sized for a 1.07 m/s (3.5 ft/s) walk.
      CHECK(ph[k].ped_flash_s >= 7.f);
      CHECK(ph[k].ped_walk_s + ph[k].ped_flash_s <= ph[k].duration() + 0.01f);
      total += ph[k].duration();
    }
    CHECK(total == doctest::Approx(plan.cycle_s).epsilon(0.001));

    // Sample the whole cycle: two vehicle groups are never green together, and
    // a group's own pedestrians never have WALK while it is green (they get it
    // during the LPI and the opposing phase).
    for (float t_s = 0.f; t_s < plan.cycle_s; t_s += 0.25f) {
      const double abs_t = static_cast<double>(t_s);
      const VehSignal g0 = t.vehicleState(pi, 0, abs_t);
      const VehSignal g1 = t.vehicleState(pi, 1, abs_t);
      const bool go0 = g0 == VehSignal::Green || g0 == VehSignal::Yellow;
      const bool go1 = g1 == VehSignal::Green || g1 == VehSignal::Yellow;
      const bool both_go = go0 && go1;
      CHECK_FALSE(both_go);
    }
  }
}

TEST_CASE("leading pedestrian interval gives the crossing a head start") {
  SignalTable t;
  SignalPhase ph[2];
  for (int i = 0; i < 2; ++i) {
    ph[i].group = i;
    ph[i].lpi_s = 7.f;
    ph[i].green_s = 33.f;
    ph[i].yellow_s = 3.f;
    ph[i].allred_s = 2.f;
    ph[i].ped_walk_s = 15.f;
    ph[i].ped_flash_s = 25.f;
  }
  const uint32_t plan = t.addPlan(1, 1, 0.f, ph, 2);
  CHECK(t.plan(plan).cycle_s == doctest::Approx(90.f));

  // First seven seconds of phase 0: vehicles red, parallel pedestrians walking.
  for (float s = 0.1f; s < 6.9f; s += 0.5f) {
    CHECK(t.vehicleState(plan, 0, s) == VehSignal::Red);
    CHECK(t.pedState(plan, 0, s) == PedSignal::Walk);
  }
  CHECK(t.vehicleState(plan, 0, 8.0) == VehSignal::Green);
  CHECK(t.pedState(plan, 0, 8.0) == PedSignal::Walk);
  CHECK(t.pedState(plan, 0, 20.0) == PedSignal::Flash);
  CHECK(t.pedState(plan, 0, 44.0) == PedSignal::DontWalk);
  // Yellow then all-red at the end of the phase.
  CHECK(t.vehicleState(plan, 0, 41.0) == VehSignal::Yellow);
  CHECK(t.vehicleState(plan, 0, 44.0) == VehSignal::Red);
  CHECK(t.vehicleState(plan, 1, 44.0) == VehSignal::Red);  // all-red overlap
  CHECK(t.timeToGreen(plan, 1, 44.0) == doctest::Approx(8.0f).epsilon(0.02));
  CHECK(t.greenRemaining(plan, 0, 10.0) == doctest::Approx(30.f).epsilon(0.02));
  CHECK(t.redFraction(plan, 0) == doctest::Approx(1.f - 36.f / 90.f).epsilon(0.01));
  CHECK(t.expectedDelay(plan, 0) > 0.f);

  // The per-step cache agrees with the pure functions.
  for (float s = 0.f; s < 90.f; s += 0.37f) {
    t.cacheStates(s);
    for (int32_t grp = 0; grp < 2; ++grp) {
      CHECK(t.cachedVehicleState(plan, grp) == t.vehicleState(plan, grp, s));
      CHECK(t.cachedPedState(plan, grp) == t.pedState(plan, grp, s));
    }
  }
}

TEST_CASE("law-abiding drivers never enter on red, and nobody turns right on red") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(midtownSpec(6, 10), 28.f, 0.f, true), w.error);
  TrafficConfig cfg;
  cfg.max_vehicles = 1200;
  cfg.use_player_ring = false;
  TrafficSim sim;
  REQUIRE_MESSAGE(sim.configure(w.graph, w.signals, cfg, 20260906u), sim.lastError());
  sim.setDensityTable(&w.density);
  sim.setRouter(&w.router);
  sim.setTimeOfDay(8.5f * 3600.f, 0);
  CHECK(sim.prefill() > 100u);

  EntryMonitor mon;
  mon.sim = &sim;
  mon.graph = &w.graph;
  for (int i = 0; i < 3600; ++i) {  // three simulated minutes
    sim.step();
    mon.sample();
  }
  MESSAGE("junction entries " << mon.entries << ", on green " << mon.green_entries << ", on yellow "
                              << mon.yellow_entries << ", on red " << mon.red_entries_total);
  CHECK(mon.entries > 500u);
  CHECK(mon.red_entries_law_abiding == 0u);
  CHECK(mon.right_on_red == 0u);
  // The red-light runners in the fleet do exist (2 % of sedans, 10 % of taxis).
  CHECK(mon.green_entries > mon.red_entries_total);
  CHECK(sim.stats().vehicles > 100u);
}

TEST_CASE("no right on red holds even with a fleet of red-light runners") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(midtownSpec(5, 8), 30.f, 0.f, true), w.error);
  TrafficConfig cfg;
  cfg.max_vehicles = 600;
  cfg.use_player_ring = false;
  cfg.red_run_window_s = 3.0f;  // exaggerate the aggressive behaviour
  TrafficSim sim;
  REQUIRE(sim.configure(w.graph, w.signals, cfg, 4242u));
  sim.setDensityTable(&w.density);
  sim.setRouter(&w.router);
  sim.setTimeOfDay(17.5f * 3600.f, 0);
  sim.prefill();
  // Everybody is a red-light runner.
  for (size_t i = 0; i < sim.vehicleCount(); ++i)
    const_cast<Vehicle&>(sim.vehicle(i)).flags &= static_cast<uint8_t>(~kVehLawAbiding);

  EntryMonitor mon;
  mon.sim = &sim;
  mon.graph = &w.graph;
  for (int i = 0; i < 2400; ++i) {
    sim.step();
    mon.sample();
  }
  MESSAGE("entries on red by aggressive drivers: " << mon.red_entries_total);
  CHECK(mon.right_on_red == 0u);
}

}  // TEST_SUITE

// --------------------------------------------------------------------------
// The signal cache is a memoization over every plan in the city.  On the real
// table that is 19,814 plans a step, all but a few hundred of them at
// intersections nowhere near the player.  TrafficSim::step() and PedSim::step()
// now restrict the refresh to the streamed region -- the despawn disc, which is
// what ADR-021 calls the streamed region -- and these two cases are the whole
// contract: it must actually restrict, and it must change nothing a caller
// sees.
//
// Written because the same saving already existed as SignalTable::
// setActiveWindow and was called from nowhere but two benchmarks.  A host that
// has to remember to call it is a host that will forget, which is exactly how
// DensityTable::assignLaneNtas() came to be missing.
TEST_CASE("stepping with a player ring restricts the signal refresh to it") {
  GridWorld w;
  // 12 avenues x 40 streets at Manhattan spacing is 3.08 x 3.12 km -- large
  // enough that a ring cannot cover it, which is the point.
  REQUIRE(w.build(midtownSpec(12, 40), 40.f));
  REQUIRE(w.signals.planCount() > 0);

  TrafficConfig cfg;
  cfg.use_player_ring = true;
  cfg.despawn_m = 300.f;  // a 600 m square, well inside the 3 km grid
  TrafficSim sim;
  REQUIRE_MESSAGE(sim.configure(w.graph, w.signals, cfg, 4321u), sim.lastError());
  sim.setDensityTable(&w.density);

  const uint32_t all_plans = static_cast<uint32_t>(w.signals.planCount());

  SUBCASE("no player means the whole city, exactly as before") {
    sim.step();
    CHECK(w.signals.cachedPlanCount() == all_plans);
  }

  SUBCASE("a player ring restricts it, and every state is unchanged") {
    traffic::PlayerProxy p;
    p.valid = true;
    p.x = 0.f;
    p.y = 0.f;
    p.heading_rad = 0.f;
    sim.setPlayer(p);
    sim.step();

    const uint32_t restricted = w.signals.cachedPlanCount();
    CHECK(restricted > 0u);
    CHECK(restricted < all_plans);

    // Transparency: read every plan and group through the cached accessors,
    // then compare against the pure time functions at the same instant.  The
    // plans inside the window are memoized and the ones outside fall back, and
    // a caller must not be able to tell which is which.
    const double t = w.signals.cachedTime();
    uint32_t compared = 0, outside = 0;
    for (uint32_t pi = 0; pi < all_plans; ++pi) {
      for (int32_t g = 0; g < 8; ++g) {
        CHECK(w.signals.cachedVehicleState(pi, g) == w.signals.vehicleState(pi, g, t));
        CHECK(w.signals.cachedPedState(pi, g) == w.signals.pedState(pi, g, t));
        ++compared;
      }
    }
    outside = all_plans - restricted;
    CHECK(compared == all_plans * 8u);
    CHECK(outside > 0u);  // otherwise the comparison proved nothing
  }

  SUBCASE("a host that manages the window itself keeps it") {
    TrafficConfig own = cfg;
    own.signal_window_from_ring = false;
    sim.setConfig(own);
    traffic::PlayerProxy p;
    p.valid = true;
    p.x = 0.f;
    p.y = 0.f;
    sim.setPlayer(p);
    // A window the simulation would never choose: one grid cell at the far
    // corner.  If step() overrode it this count would be the ring's instead.
    w.signals.setActiveWindow(2000.f, 2000.f, 2400.f, 2400.f);
    const uint32_t chosen = [&] {
      w.signals.cacheStates(0.0);
      return w.signals.cachedPlanCount();
    }();
    sim.step();
    CHECK(w.signals.cachedPlanCount() == chosen);
    CHECK(w.signals.cachedPlanCount() < all_plans);
  }
}
