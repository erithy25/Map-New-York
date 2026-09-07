// nycsim traffic/pedestrian benchmark.
//
// Target (docs/ARCHITECTURE.md §12 / the traffic lane brief): 5,000 vehicles +
// 20,000 pedestrians must step at 20 Hz in under 8 ms single-threaded.  The
// benchmark builds a synthetic Midtown grid large enough to hold that fleet at
// a realistic density, wires the two simulations to each other through their
// probes (so the pedestrian look-ups drivers do, and the taxi/gap look-ups
// pedestrians do, are part of the measurement), warms up, and then reports the
// per-step wall time distribution.
//
//   ./nycsim_traffic_bench [--vehicles N] [--peds N] [--steps N] [--avenues N]
//                          [--streets N] [--seed N] [--no-peds] [--csv path]
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "nycsim/peds/PedSim.h"
#include "nycsim/peds/SidewalkGraph.h"
#include "nycsim/routing/Router.h"
#include "nycsim/traffic/SyntheticGrid.h"
#include "nycsim/traffic/TrafficSim.h"

using namespace nycsim;

namespace {

struct Options {
  uint32_t vehicles = 5000;
  uint32_t peds = 20000;
  uint32_t steps = 1200;   // one simulated minute at 20 Hz
  uint32_t warmup = 200;
  int avenues = 14;
  int streets = 28;
  uint64_t seed = 20260906u;
  bool with_peds = true;
  std::string csv;
};

double percentile(std::vector<double>& v, double p) {
  if (v.empty()) return 0.0;
  std::sort(v.begin(), v.end());
  const size_t k = static_cast<size_t>(p * static_cast<double>(v.size() - 1) + 0.5);
  return v[std::min(k, v.size() - 1)];
}

int usage() {
  std::printf(
      "usage: nycsim_traffic_bench [--vehicles N] [--peds N] [--steps N]\n"
      "                            [--avenues N] [--streets N] [--seed N]\n"
      "                            [--no-peds] [--csv FILE]\n");
  return 2;
}

}  // namespace

int main(int argc, char** argv) {
  Options o;
  for (int i = 1; i < argc; ++i) {
    const char* a = argv[i];
    auto next = [&](uint64_t& out) {
      if (i + 1 >= argc) return false;
      out = std::strtoull(argv[++i], nullptr, 10);
      return true;
    };
    uint64_t val = 0;
    if (std::strcmp(a, "--vehicles") == 0 && next(val)) o.vehicles = static_cast<uint32_t>(val);
    else if (std::strcmp(a, "--peds") == 0 && next(val)) o.peds = static_cast<uint32_t>(val);
    else if (std::strcmp(a, "--steps") == 0 && next(val)) o.steps = static_cast<uint32_t>(val);
    else if (std::strcmp(a, "--avenues") == 0 && next(val)) o.avenues = static_cast<int>(val);
    else if (std::strcmp(a, "--streets") == 0 && next(val)) o.streets = static_cast<int>(val);
    else if (std::strcmp(a, "--seed") == 0 && next(val)) o.seed = val;
    else if (std::strcmp(a, "--no-peds") == 0) o.with_peds = false;
    else if (std::strcmp(a, "--csv") == 0 && i + 1 < argc) o.csv = argv[++i];
    else return usage();
  }

  using clock = std::chrono::steady_clock;
  const auto t_build0 = clock::now();

  traffic::SyntheticGridSpec spec;
  spec.avenues = o.avenues;
  spec.streets = o.streets;
  spec.bike_lane_every = 3;
  spec.commercial_avenues = true;
  routing::RoadGraph graph;
  traffic::SignalTable signals;
  std::string err;
  if (!traffic::SyntheticGrid::build(spec, graph, signals, &err)) {
    std::fprintf(stderr, "grid build failed: %s\n", err.c_str());
    return 1;
  }

  // Lane-kilometres decide how many vehicles fit; the density table is set so
  // the spawner holds exactly the requested fleet size.
  double lane_km = 0.0;
  for (uint32_t li = 0; li < graph.laneCount(); ++li) {
    const routing::Lane& l = graph.lane(li);
    if (l.is_junction == 0 && (l.kind == routing::LaneKind::Travel || l.kind == routing::LaneKind::Bus))
      lane_km += static_cast<double>(l.length_m) * 0.001;
  }
  peds::SidewalkGraph walk;
  peds::SidewalkBuildParams wp;
  if (!walk.buildFromRoadGraph(graph, &signals, wp)) {
    std::fprintf(stderr, "sidewalk build failed: %s\n", walk.lastError().c_str());
    return 1;
  }
  double sidewalk_m2 = 0.0;
  for (uint32_t e = 0; e < walk.edgeCount(); ++e) {
    const peds::WalkEdge& ed = walk.edge(e);
    if (ed.kind != peds::WalkEdgeKind::Crosswalk)
      sidewalk_m2 += static_cast<double>(ed.length_m) * static_cast<double>(ed.width_m);
  }

  traffic::DensityTable density;
  const uint16_t nta = density.addNta("MN17");
  traffic::DensityCell cell;
  cell.veh_per_km_lane = lane_km > 1.0 ? static_cast<float>(static_cast<double>(o.vehicles) / lane_km) : 20.f;
  cell.ped_per_m2 = sidewalk_m2 > 1.0 ? static_cast<float>(static_cast<double>(o.peds) / sidewalk_m2) : 0.02f;
  cell.taxi_share = 0.15f;
  cell.truck_share = 0.08f;
  cell.bus_share = 0.02f;
  cell.bike_share = 0.05f;
  density.fill(nta, cell);

  routing::Router router;
  if (!router.attach(graph, 6, o.seed)) {
    std::fprintf(stderr, "router attach failed: %s\n", router.lastError().c_str());
    return 1;
  }
  const double build_ms =
      std::chrono::duration<double, std::milli>(clock::now() - t_build0).count();

  traffic::TrafficConfig tcfg;
  tcfg.max_vehicles = o.vehicles + 500u;
  tcfg.use_player_ring = true;
  // The protected region around the player still applies; the distance culls do
  // not, so the benchmark holds the fleet size it is asked to measure.
  tcfg.spawn_outer_m = 1.0e6f;
  tcfg.despawn_m = 1.0e6f;
  tcfg.spawn_rate_per_s = 60.f;   // streaming replaces the fleet, it does not churn it
  if (std::getenv("NYCSIM_BENCH_NOROUTE") != nullptr) tcfg.max_routes_per_step = 0;
  traffic::TrafficSim tsim;
  const auto t_cfg0 = clock::now();
  if (!tsim.configure(graph, signals, tcfg, o.seed)) {
    std::fprintf(stderr, "traffic configure failed: %s\n", tsim.lastError().c_str());
    return 1;
  }
  const double cfg_ms = std::chrono::duration<double, std::milli>(clock::now() - t_cfg0).count();
  tsim.setDensityTable(&density);
  tsim.setRouter(&router);
  tsim.setTimeOfDay(8.5f * 3600.f, 0);

  peds::PedConfig pcfg;
  pcfg.max_peds = o.peds + 2000u;
  pcfg.use_player_ring = true;
  pcfg.despawn_m = 1.0e6f;
  pcfg.spawn_rate_per_s = 200.f;
  peds::PedSim psim;
  if (o.with_peds && !psim.configure(walk, &signals, pcfg, o.seed)) {
    std::fprintf(stderr, "peds configure failed: %s\n", psim.lastError().c_str());
    return 1;
  }
  if (o.with_peds) {
    psim.setDensityTable(&density);
    psim.setTimeOfDay(8.5f * 3600.f, 0);
    psim.setFastZone(nta, true);
    tsim.setPedProbe(psim.pedProbe());
    psim.setVehicleProbe(tsim.vehicleProbe());
  }

  // The player drives up an avenue; the protection ring follows him.
  traffic::PlayerProxy player;
  player.valid = true;
  float minx, miny, maxx, maxy;
  graph.bounds(minx, miny, maxx, maxy);
  player.x = (minx + maxx) * 0.5f;
  player.y = miny + 50.f;
  player.heading_rad = 1.5707963f;
  player.speed_mps = 9.f;
  tsim.setPlayer(player);
  if (o.with_peds) psim.setPlayer(player);

  const auto t_fill0 = clock::now();
  const uint32_t veh_made = tsim.prefill(o.vehicles + 1000u);
  const uint32_t ped_made = o.with_peds ? psim.prefill(o.peds) : 0u;
  const double fill_ms = std::chrono::duration<double, std::milli>(clock::now() - t_fill0).count();

  std::printf("nycsim traffic benchmark\n");
  std::printf("  grid           %d avenues x %d streets, %zu nodes, %zu lanes (%zu junction), %.1f lane-km\n",
              o.avenues, o.streets, graph.nodeCount(), graph.laneCount(), graph.junctionLaneCount(), lane_km);
  std::printf("  sidewalks      %zu nodes, %zu edges, %.0f m2, %zu POIs, %zu walls\n", walk.nodeCount(),
              walk.edgeCount(), sidewalk_m2, walk.poiCount(), walk.wallCount());
  std::printf("  build/attach   %.1f ms (graph+router+sidewalks), configure %.1f ms, prefill %.1f ms\n",
              build_ms, cfg_ms, fill_ms);
  std::printf("  fleet          %u vehicles (target %.0f), %u pedestrians\n", veh_made,
              static_cast<double>(tsim.targetVehicles()), ped_made);
  std::fflush(stdout);

  for (uint32_t i = 0; i < o.warmup; ++i) {
    tsim.step();
    if (o.with_peds) psim.step();
  }

  std::vector<double> traffic_ms, ped_ms, total_ms;
  traffic_ms.reserve(o.steps);
  ped_ms.reserve(o.steps);
  total_ms.reserve(o.steps);
  for (uint32_t i = 0; i < o.steps; ++i) {
    // The player keeps moving so the spawn ring keeps working.
    player.y += player.speed_mps * tcfg.dt;
    if (player.y > maxy - 50.f) player.y = miny + 50.f;
    tsim.setPlayer(player);
    if (o.with_peds) psim.setPlayer(player);

    const auto a = clock::now();
    tsim.step();
    const auto b = clock::now();
    if (o.with_peds) psim.step();
    const auto c = clock::now();
    traffic_ms.push_back(std::chrono::duration<double, std::milli>(b - a).count());
    ped_ms.push_back(std::chrono::duration<double, std::milli>(c - b).count());
    total_ms.push_back(std::chrono::duration<double, std::milli>(c - a).count());
  }

  double sum = 0.0;
  for (double v : total_ms) sum += v;
  const double mean = total_ms.empty() ? 0.0 : sum / static_cast<double>(total_ms.size());
  double tsum = 0.0, psum = 0.0;
  for (double v : traffic_ms) tsum += v;
  for (double v : ped_ms) psum += v;

  std::printf("\n  steps measured %u (after %u warm-up steps)\n", o.steps, o.warmup);
  std::printf("  vehicles       %u   pedestrians %u\n", tsim.stats().vehicles,
              o.with_peds ? psim.stats().peds : 0u);
  std::printf("  traffic step   mean %.3f ms  p50 %.3f  p95 %.3f  p99 %.3f  max %.3f\n",
              traffic_ms.empty() ? 0.0 : tsum / static_cast<double>(traffic_ms.size()),
              percentile(traffic_ms, 0.50), percentile(traffic_ms, 0.95), percentile(traffic_ms, 0.99),
              percentile(traffic_ms, 1.0));
  std::printf("  peds step      mean %.3f ms  p50 %.3f  p95 %.3f  p99 %.3f  max %.3f\n",
              ped_ms.empty() ? 0.0 : psum / static_cast<double>(ped_ms.size()), percentile(ped_ms, 0.50),
              percentile(ped_ms, 0.95), percentile(ped_ms, 0.99), percentile(ped_ms, 1.0));
  std::printf("  combined step  mean %.3f ms  p50 %.3f  p95 %.3f  p99 %.3f  max %.3f\n", mean,
              percentile(total_ms, 0.50), percentile(total_ms, 0.95), percentile(total_ms, 0.99),
              percentile(total_ms, 1.0));
  std::printf("  budget         8.000 ms at 20 Hz  ->  %s (%.1f%% of budget, %.1fx real time)\n",
              mean < 8.0 ? "PASS" : "FAIL", mean / 8.0 * 100.0, mean > 1e-9 ? 50.0 / mean : 0.0);
  std::printf("  behaviour      mean speed %.2f m/s, lane changes %u, honks %u, double parked %u,\n"
              "                 in junction %u, stopped at red %u, reroutes %u, route calls %u\n",
              static_cast<double>(tsim.stats().mean_speed_mps), tsim.stats().lane_changes,
              tsim.stats().honks, tsim.stats().double_parked, tsim.stats().in_junction,
              tsim.stats().stopped_at_red, tsim.stats().reroutes, tsim.stats().route_calls);
  if (o.with_peds) {
    std::printf("  crowd          mean speed %.2f m/s, crossing %u, waiting %u, jaywalking %u, sitting %u,\n"
                "                 hailing %u, subway %u, redraws %u\n",
                static_cast<double>(psim.stats().mean_speed_mps), psim.stats().crossing,
                psim.stats().waiting, psim.stats().jaywalking, psim.stats().sitting, psim.stats().hailing,
                psim.stats().subway_entries, psim.stats().uniqueness_redraws);
  }

  if (!o.csv.empty()) {
    FILE* f = std::fopen(o.csv.c_str(), "w");
    if (f != nullptr) {
      std::fprintf(f, "step,traffic_ms,peds_ms,total_ms\n");
      for (size_t i = 0; i < total_ms.size(); ++i)
        std::fprintf(f, "%zu,%.6f,%.6f,%.6f\n", i, traffic_ms[i], ped_ms[i], total_ms[i]);
      std::fclose(f);
      std::printf("  wrote %s\n", o.csv.c_str());
    }
  }
  return mean < 8.0 ? 0 : 1;
}
