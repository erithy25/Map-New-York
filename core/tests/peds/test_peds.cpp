// Pedestrians: sidewalk graph construction, wall containment, crossing
// compliance, the jaywalking model, activities, the 12-dimensional variety
// vector and density convergence.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <unordered_map>
#include <vector>

#include "../traffic/GridWorld.h"
#include "nycsim/peds/PedSim.h"

using namespace nycsim;
using namespace nycsim::peds;
using nycsim_test::GridWorld;

namespace {

traffic::SyntheticGridSpec pedSpec(int avenues, int streets) {
  traffic::SyntheticGridSpec s;
  s.avenues = avenues;
  s.streets = streets;
  s.commercial_avenues = true;
  s.bike_lane_every = 3;
  return s;
}

// Adds the POI kinds the activity model needs but which the road graph alone
// cannot supply (subway entrances, benches, stoops, landmarks, park gates).
void addCityPois(SidewalkGraph& w, const routing::RoadGraph& g, uint32_t stride) {
  const PoiKind kinds[5] = {PoiKind::SubwayEntrance, PoiKind::Bench, PoiKind::Stoop, PoiKind::Landmark,
                            PoiKind::ParkEntrance};
  uint32_t k = 0;
  for (uint32_t n = 0; n < w.nodeCount(); n += stride) {
    const routing::Vec3 p = w.node(n).pos;
    w.addPoi(p, kinds[k % 5], "poi");
    ++k;
  }
  (void)g;
}

// Distance from a point to a segment.
float segDist(float px, float py, const Wall& s) {
  const float dx = s.x2 - s.x1, dy = s.y2 - s.y1;
  const float len2 = dx * dx + dy * dy;
  float t = len2 > 1e-9f ? ((px - s.x1) * dx + (py - s.y1) * dy) / len2 : 0.f;
  t = std::max(0.f, std::min(1.f, t));
  const float cx = s.x1 + t * dx, cy = s.y1 + t * dy;
  return std::sqrt((px - cx) * (px - cx) + (py - cy) * (py - cy));
}

// True when segment p→q properly crosses segment a→b.
bool crosses(float px, float py, float qx, float qy, const Wall& w) {
  const float rx = qx - px, ry = qy - py;
  const float sx = w.x2 - w.x1, sy = w.y2 - w.y1;
  const float denom = rx * sy - ry * sx;
  if (std::fabs(denom) < 1e-9f) return false;
  const float ax = w.x1 - px, ay = w.y1 - py;
  const float t = (ax * sy - ay * sx) / denom;
  const float u = (ax * ry - ay * rx) / denom;
  return t > 0.f && t < 1.f && u > 0.f && u < 1.f;
}

// A stub taxi fleet: one available cab parked next to the given point.
struct StubTaxi {
  float x = 0.f, y = 0.f;
  bool available = true;
  uint32_t hails = 0;

  static float tta(const void*, float, float, float) { return 1e9f; }
  static bool freeTaxi(const void* ctx, float x, float y, float r, traffic::TaxiSighting& out) {
    const StubTaxi* self = static_cast<const StubTaxi*>(ctx);
    if (!self->available) return false;
    const float dx = self->x - x, dy = self->y - y;
    const float d = std::sqrt(dx * dx + dy * dy);
    if (d > r) return false;
    out.agent = 1;
    out.x = self->x;
    out.y = self->y;
    out.distance = d;
    return true;
  }
  static bool hail(void* ctx, uint32_t, float, float) {
    StubTaxi* self = static_cast<StubTaxi*>(ctx);
    ++self->hails;
    return true;
  }
  traffic::VehicleProbe probe() {
    traffic::VehicleProbe p;
    p.ctx = this;
    p.time_to_arrival = &StubTaxi::tta;
    p.free_taxi = &StubTaxi::freeTaxi;
    p.hail = &StubTaxi::hail;
    return p;
  }
};

}  // namespace

TEST_SUITE("peds") {

TEST_CASE("the sidewalk graph derived from the road graph is well formed") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(5, 8), 0.f, 0.05f, false, true), w.error);
  const SidewalkGraph& s = w.walk;
  CHECK(s.finalized());
  CHECK(s.nodeCount() > 100u);
  CHECK(s.edgeCount() > 100u);
  CHECK(s.wallCount() > 50u);

  uint32_t crosswalks = 0, signalized = 0, sidewalks = 0;
  for (uint32_t e = 0; e < s.edgeCount(); ++e) {
    const WalkEdge& ed = s.edge(e);
    CHECK(ed.length_m > 0.f);
    CHECK(ed.width_m >= 1.8f);
    CHECK(ed.a < s.nodeCount());
    CHECK(ed.b < s.nodeCount());
    CHECK(std::fabs(ed.dirx * ed.dirx + ed.diry * ed.diry - 1.f) < 1e-3f);
    if (ed.kind == WalkEdgeKind::Crosswalk) {
      ++crosswalks;
      if (ed.signal_plan != routing::kInvalidIndex && ed.signal_group >= 0) ++signalized;
      CHECK(ed.width_m == doctest::Approx(3.7f));  // NYC 12 ft continental
    } else {
      ++sidewalks;
      // 4.6 m along the block (DOT Street Design Manual); a corner link is
      // widthed by its own (short) length so its corridor cannot bulge through
      // the building line.
      CHECK(ed.width_m >= 1.8f);
      CHECK(ed.width_m <= 4.61f);
    }
  }
  MESSAGE("sidewalk edges " << sidewalks << ", crosswalks " << crosswalks << " (signalized " << signalized
                            << "), walls " << s.wallCount() << ", POIs " << s.poiCount());
  CHECK(crosswalks > 20u);
  CHECK(signalized > crosswalks / 2u);
  CHECK(s.poiCount() > 20u);

  // Connectivity: a path exists between distant corners.
  std::vector<uint32_t> buf(PedSim::kPathCap);
  const uint32_t n = s.path(0, static_cast<uint32_t>(s.nodeCount()) - 1, buf.data(),
                            static_cast<uint32_t>(buf.size()));
  CHECK(n > 0u);

  // Geometry round trip.
  for (uint32_t e = 0; e < s.edgeCount(); e += 17) {
    const routing::Vec3 p = s.pointOn(e, s.edge(e).length_m * 0.4f, 1.1f);
    float sp = 0.f, lat = 0.f;
    s.projectOnEdge(e, p.x, p.y, sp, lat);
    CHECK(sp == doctest::Approx(s.edge(e).length_m * 0.4f).epsilon(0.01));
    CHECK(lat == doctest::Approx(1.1f).epsilon(0.01));
  }
}

TEST_CASE("the variety vector matches the generator contract") {
  CHECK(kVarietyDims == 12u);
  uint64_t combos = 1;
  for (uint32_t d = 0; d < kVarietyDims; ++d) {
    CHECK(kVarietyLevels[d] >= 4u);
    CHECK(std::string(varietyName(d)).size() > 2u);
    combos *= kVarietyLevels[d];
  }
  MESSAGE("distinguishable appearances: " << combos);
  CHECK(combos > 1000000000ull);

  Rng rng(99);
  VarietyVector a = drawVariety(rng);
  for (uint32_t d = 0; d < kVarietyDims; ++d) {
    CHECK(a.v[d] >= 0.f);
    CHECK(a.v[d] < 1.f);
    CHECK(a.level(d) < kVarietyLevels[d]);
  }
  CHECK(a.signature() == a.signature());
  CHECK(a.heightMetres() > 1.0f);
  CHECK(a.heightMetres() < 2.0f);
  // A change in one dimension changes the signature.
  VarietyVector b = a;
  b.v[7] = a.v[7] > 0.5f ? 0.05f : 0.95f;
  CHECK(a.signature() != b.signature());
  // Quantization boundaries.
  VarietyVector c;
  for (uint32_t d = 0; d < kVarietyDims; ++d) c.v[d] = 0.999999f;
  CHECK(c.level(0) == kVarietyLevels[0] - 1u);
  for (uint32_t d = 0; d < kVarietyDims; ++d) c.v[d] = 0.f;
  CHECK(c.signature() == 0u);
}

TEST_CASE("pedestrians stay inside their corridor and never cross a wall") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(5, 8), 0.f, 0.06f, false, true), w.error);
  addCityPois(w.walk, w.graph, 9);
  REQUIRE(w.walk.finalize());

  PedConfig cfg;
  cfg.max_peds = 3000;
  cfg.use_player_ring = false;
  PedSim sim;
  REQUIRE_MESSAGE(sim.configure(w.walk, &w.signals, cfg, 13131u), sim.lastError());
  sim.setTimeOfDay(9.f * 3600.f, 0);
  const uint32_t made = sim.prefill(1500);
  MESSAGE("prefilled " << made << " pedestrians");
  REQUIRE(made > 1000u);

  std::unordered_map<uint32_t, std::pair<float, float>> prev;
  for (size_t i = 0; i < sim.pedCount(); ++i) prev[sim.ped(i).id] = {sim.ped(i).x, sim.ped(i).y};

  uint32_t corridor_violations = 0, wall_crossings = 0, too_close = 0;
  float worst_overshoot = 0.f;
  for (int step = 0; step < 1200; ++step) {  // one simulated minute
    sim.step();
    for (size_t i = 0; i < sim.pedCount(); ++i) {
      const Pedestrian& p = sim.ped(i);
      const WalkEdge& e = w.walk.edge(p.edge);
      const float half = e.width_m * 0.5f;
      if (std::fabs(p.lateral) > half + 1e-3f) {
        ++corridor_violations;
        worst_overshoot = std::max(worst_overshoot, std::fabs(p.lateral) - half);
      }
      const auto it = prev.find(p.id);
      if (it != prev.end()) {
        uint32_t buf[8];
        const uint32_t nw = w.walk.wallsNear(p.x, p.y, 4.f, buf, 8);
        for (uint32_t k = 0; k < nw; ++k) {
          const Wall& wall = w.walk.wall(buf[k]);
          if (crosses(it->second.first, it->second.second, p.x, p.y, wall)) ++wall_crossings;
          if (segDist(p.x, p.y, wall) < 0.05f) ++too_close;
        }
      }
      prev[p.id] = {p.x, p.y};
    }
  }
  MESSAGE("corridor violations " << corridor_violations << " (worst " << worst_overshoot
                                 << " m), wall crossings " << wall_crossings << ", contacts " << too_close);
  CHECK(corridor_violations == 0u);
  CHECK(wall_crossings == 0u);
  CHECK(sim.stats().mean_speed_mps > 0.4f);
}

TEST_CASE("law-abiding pedestrians only cross on WALK; jaywalkers use gaps") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(5, 8), 0.f, 0.05f, false, true), w.error);
  addCityPois(w.walk, w.graph, 7);
  REQUIRE(w.walk.finalize());

  PedConfig cfg;
  cfg.max_peds = 2500;
  cfg.use_player_ring = false;
  cfg.jaywalk_share = 0.30f;
  PedSim sim;
  REQUIRE(sim.configure(w.walk, &w.signals, cfg, 24680u));
  sim.setTimeOfDay(12.f * 3600.f, 0);
  REQUIRE(sim.prefill(1200) > 800u);

  std::unordered_map<uint32_t, uint32_t> last_edge;
  uint32_t entries = 0, on_walk = 0, law_abiding_violations = 0, jaywalk_entries = 0;
  uint32_t jaywalkers = 0, total = 0;
  for (int step = 0; step < 4800; ++step) {  // four simulated minutes
    sim.step();
    for (size_t i = 0; i < sim.pedCount(); ++i) {
      const Pedestrian& p = sim.ped(i);
      const auto it = last_edge.find(p.id);
      const uint32_t prev = it == last_edge.end() ? routing::kInvalidIndex : it->second;
      last_edge[p.id] = p.edge;
      if (prev == p.edge || prev == routing::kInvalidIndex) continue;
      if (w.walk.edge(p.edge).kind != WalkEdgeKind::Crosswalk) continue;
      const traffic::PedSignal ps = sim.crosswalkState(p.edge);
      // Unsignalized crossings are governed by gap acceptance, not by a phase
      // (NY VTL §1151 gives the pedestrian the right of way there); the
      // compliance rule under test is about signalized crosswalks.
      if (ps == traffic::PedSignal::Off) continue;
      ++entries;
      if (ps == traffic::PedSignal::Walk) ++on_walk;
      const bool jay = (p.flags & kPedJaywalker) != 0;
      if (ps != traffic::PedSignal::Walk) {
        if (!jay) ++law_abiding_violations;
        else ++jaywalk_entries;
      }
    }
  }
  for (size_t i = 0; i < sim.pedCount(); ++i) {
    ++total;
    if ((sim.ped(i).flags & kPedJaywalker) != 0) ++jaywalkers;
  }
  const float share = total > 0 ? static_cast<float>(jaywalkers) / static_cast<float>(total) : 0.f;
  MESSAGE("crosswalk entries " << entries << " (on WALK " << on_walk << ", against " << jaywalk_entries
                               << "), jaywalker share " << share);
  CHECK(entries > 100u);
  CHECK(law_abiding_violations == 0u);
  CHECK(jaywalk_entries > 0u);
  CHECK(share > 0.2f);
  CHECK(share < 0.4f);
}

TEST_CASE("appearances are unique within sixty metres") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(4, 6), 0.f, 0.05f, false, true), w.error);
  PedConfig cfg;
  cfg.max_peds = 2000;
  cfg.use_player_ring = false;
  PedSim sim;
  REQUIRE(sim.configure(w.walk, &w.signals, cfg, 5555u));
  sim.setTimeOfDay(9.f * 3600.f, 0);
  REQUIRE(sim.prefill(900) > 700u);
  CHECK(sim.duplicateSignatures() == 0u);
  for (int i = 0; i < 600; ++i) sim.step();
  // Motion can bring two agents within 60 m of one another; the check is
  // enforced at spawn, so report how many pairs the movement produced.
  const uint32_t dup = sim.duplicateSignatures();
  MESSAGE("duplicate signatures after one minute of walking: " << dup << " of " << sim.pedCount()
                                                               << ", redraws " << sim.stats().uniqueness_redraws
                                                               << ", failures " << sim.stats().uniqueness_failures);
  CHECK(sim.stats().uniqueness_failures == 0u);
  CHECK(dup == 0u);

  // Brute-force cross-check of the hashed query on the whole crowd.
  uint32_t brute = 0;
  for (size_t i = 0; i < sim.pedCount(); ++i) {
    for (size_t j = i + 1; j < sim.pedCount(); ++j) {
      if (sim.ped(i).signature != sim.ped(j).signature) continue;
      const float dx = sim.ped(i).x - sim.ped(j).x, dy = sim.ped(i).y - sim.ped(j).y;
      if (dx * dx + dy * dy <= cfg.uniqueness_radius_m * cfg.uniqueness_radius_m) ++brute;
    }
  }
  CHECK(brute == 0u);
}

TEST_CASE("walking speeds follow the calibrated distributions") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(4, 6), 0.f, 0.05f, false, true), w.error);
  PedConfig cfg;
  cfg.max_peds = 3000;
  cfg.use_player_ring = false;

  auto meanSpeed = [&](bool midtown) {
    PedSim sim;
    REQUIRE(sim.configure(w.walk, &w.signals, cfg, 31415u));
    if (midtown) sim.setFastZone(0, true);
    sim.prefill(1500);
    double sum = 0.0;
    for (size_t i = 0; i < sim.pedCount(); ++i) sum += static_cast<double>(sim.ped(i).desired_speed);
    return sim.pedCount() > 0 ? sum / static_cast<double>(sim.pedCount()) : 0.0;
  };
  const double normal = meanSpeed(false);
  const double fast = meanSpeed(true);
  MESSAGE("mean desired speed: " << normal << " m/s, Midtown " << fast << " m/s");
  CHECK(normal == doctest::Approx(1.40).epsilon(0.03));
  CHECK(fast == doctest::Approx(1.60).epsilon(0.03));
}

TEST_CASE("pedestrian density converges to the calibration table") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(6, 10), 0.f, 0.030f, false, true), w.error);
  PedConfig cfg;
  cfg.max_peds = 20000;
  cfg.use_player_ring = false;
  PedSim sim;
  REQUIRE(sim.configure(w.walk, &w.signals, cfg, 606u));
  sim.setDensityTable(&w.density);
  sim.setTimeOfDay(8.f * 3600.f, 0);
  for (int i = 0; i < 3000; ++i) sim.step();
  const float target = sim.stats().target_peds;
  const float got = static_cast<float>(sim.pedCount());
  MESSAGE("target " << target << " pedestrians, present " << got << ", measured "
                    << sim.measuredDensity(0) << " ped/m² (table 0.030)");
  REQUIRE(target > 100.f);
  CHECK(got > target * 0.9f);
  CHECK(got <= target * 1.02f);
  CHECK(sim.measuredDensity(0) == doctest::Approx(0.030f).epsilon(0.2));
}

TEST_CASE("activities: subway, sitting, photographs and hailing a cab") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(4, 6), 0.f, 0.05f, false, true), w.error);
  addCityPois(w.walk, w.graph, 5);
  REQUIRE(w.walk.finalize());

  PedConfig cfg;
  cfg.max_peds = 1500;
  cfg.use_player_ring = false;
  cfg.cab_share = 0.5f;    // half the crowd wants a taxi
  cfg.sit_share = 0.2f;
  cfg.tourist_share = 0.3f;
  PedSim sim;
  REQUIRE(sim.configure(w.walk, &w.signals, cfg, 8675309u));
  StubTaxi taxi;
  // Park the cab beside a kerb POI.
  uint32_t n = 0;
  const uint32_t* kerbs = w.walk.poisOfKind(PoiKind::Kerb, n);
  REQUIRE(n > 0u);
  taxi.x = w.walk.poi(kerbs[0]).pos.x;
  taxi.y = w.walk.poi(kerbs[0]).pos.y;
  sim.setVehicleProbe(taxi.probe());
  sim.setTimeOfDay(13.f * 3600.f, 0);
  REQUIRE(sim.prefill(800) > 500u);

  uint32_t seen_sit = 0, seen_photo = 0, seen_hail = 0;
  for (int i = 0; i < 6000; ++i) {
    sim.step();
    seen_sit = std::max(seen_sit, sim.stats().sitting);
    seen_hail = std::max(seen_hail, sim.stats().hailing);
    seen_photo = sim.stats().photographs;
  }
  MESSAGE("sitting peak " << seen_sit << ", hailing peak " << seen_hail << ", photographs " << seen_photo
                          << ", subway entries " << sim.stats().subway_entries << ", cabs hailed "
                          << sim.stats().cabs_hailed << ", jogging " << sim.stats().jogging);
  CHECK(seen_sit > 0u);
  CHECK(seen_photo > 0u);
  CHECK(sim.stats().subway_entries > 0u);
  CHECK(sim.stats().cabs_hailed > 0u);
  CHECK(taxi.hails > 0u);
}

TEST_CASE("the crowd replays identically from the same seed") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(4, 6), 0.f, 0.04f, false, true), w.error);
  addCityPois(w.walk, w.graph, 11);
  REQUIRE(w.walk.finalize());
  PedConfig cfg;
  cfg.max_peds = 1200;
  cfg.use_player_ring = false;

  auto run = [&](uint64_t seed) {
    PedSim sim;
    REQUIRE(sim.configure(w.walk, &w.signals, cfg, seed));
    sim.setDensityTable(&w.density);
    sim.setTimeOfDay(17.f * 3600.f, 0);
    sim.prefill(600);
    std::vector<uint64_t> h;
    for (int i = 0; i < 900; ++i) {
      sim.step();
      if (i % 150 == 0) h.push_back(sim.trajectoryHash());
    }
    h.push_back(sim.trajectoryHash());
    return h;
  };
  const std::vector<uint64_t> a = run(4242u);
  const std::vector<uint64_t> b = run(4242u);
  const std::vector<uint64_t> c = run(4243u);
  CHECK(a == b);
  CHECK(a != c);
}

TEST_CASE("drivers yield to pedestrians in the crosswalk") {
  GridWorld w;
  REQUIRE_MESSAGE(w.build(pedSpec(5, 8), 18.f, 0.06f, true, true), w.error);
  addCityPois(w.walk, w.graph, 9);
  REQUIRE(w.walk.finalize());

  traffic::TrafficConfig tcfg;
  tcfg.max_vehicles = 400;
  tcfg.use_player_ring = false;
  traffic::TrafficSim traffic_sim;
  REQUIRE(traffic_sim.configure(w.graph, w.signals, tcfg, 191919u));
  traffic_sim.setDensityTable(&w.density);
  traffic_sim.setRouter(&w.router);
  traffic_sim.setTimeOfDay(8.f * 3600.f, 0);

  PedConfig pcfg;
  pcfg.max_peds = 3000;
  pcfg.use_player_ring = false;
  PedSim ped_sim;
  REQUIRE(ped_sim.configure(w.walk, &w.signals, pcfg, 191919u));
  ped_sim.setDensityTable(&w.density);
  ped_sim.setTimeOfDay(8.f * 3600.f, 0);

  traffic_sim.setPedProbe(ped_sim.pedProbe());
  ped_sim.setVehicleProbe(traffic_sim.vehicleProbe());
  traffic_sim.prefill();
  ped_sim.prefill(1200);

  // Two counts: pedestrians who have the WALK phase (the driver must yield to
  // them — this has to be zero) and pedestrians crossing against the signal
  // (a jaywalker stepping off the kerb in front of a moving car is a real New
  // York event; the driver brakes, and the count is reported, not asserted).
  uint32_t hits_with_right_of_way = 0, hits_jaywalking = 0;
  uint32_t samples = 0, crossing_peak = 0;
  for (int i = 0; i < 3600; ++i) {
    traffic_sim.step();
    ped_sim.step();
    crossing_peak = std::max(crossing_peak, ped_sim.stats().crossing);
    if (i % 10 != 0) continue;
    ++samples;
    for (size_t v = 0; v < traffic_sim.vehicleCount(); ++v) {
      const traffic::Vehicle& veh = traffic_sim.vehicle(v);
      if (veh.speed < 1.0f) continue;
      for (size_t p = 0; p < ped_sim.pedCount(); ++p) {
        const Pedestrian& ped = ped_sim.ped(p);
        if ((ped.flags & kPedOnRoad) == 0) continue;
        const float dx = ped.x - veh.pos.x, dy = ped.y - veh.pos.y;
        const float d2 = dx * dx + dy * dy;
        const float reach = veh.length_m * 0.4f;
        if (d2 >= reach * reach) continue;
        // Only what is in front of the vehicle counts as a failure to yield;
        // somebody stepping off the kerb behind a car that has already cleared
        // the crossing is not one.
        if (dx * std::cos(veh.heading_rad) + dy * std::sin(veh.heading_rad) <= 0.f) continue;
        if (ped_sim.crosswalkState(ped.edge) == traffic::PedSignal::Walk) {
          ++hits_with_right_of_way;
        } else {
          ++hits_jaywalking;
        }
      }
    }
  }
  MESSAGE("vehicle/pedestrian conflicts over " << samples << " samples: " << hits_with_right_of_way
                                               << " with the WALK phase, " << hits_jaywalking
                                               << " against it (crossing peak " << crossing_peak << ")");
  CHECK(crossing_peak > 0u);
  CHECK(hits_with_right_of_way == 0u);
}

}  // TEST_SUITE
