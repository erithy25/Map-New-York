// core/bench/bench_step.cpp — the per-step measurements: the synthetic Midtown
// grid, the real city, and the memory-bounded soak run.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "bench_common.h"
#include "bench_options.h"
#include "bench_world.h"

namespace nycbench {

using namespace nycsim;

namespace {

struct StepOptions {
  uint32_t vehicles = 5000;
  uint32_t peds = 20000;
  uint32_t steps = 1200;
  uint32_t warmup = 200;
  uint64_t seed = 20260906u;
  bool with_peds = true;
  std::string csv;
};

/// Result of a measured run.
struct StepResult {
  Dist traffic_wall, ped_wall, total_wall;
  Dist total_cpu;
  double contention_pct = 0;
  uint32_t vehicles = 0, peds = 0;
  uint64_t traffic_hash = 0, ped_hash = 0;
};

/// The densest 500 m cell of signalised intersections: a dense street grid, not
/// the expressway that a raw lane-kilometre histogram picks.  Chosen from the
/// data rather than from a guess.
void densestPoint(const routing::RoadGraph& g, float& out_x, float& out_y) {
  float minx, miny, maxx, maxy;
  g.bounds(minx, miny, maxx, maxy);
  const float cell = 500.f;
  const uint32_t nx = static_cast<uint32_t>((maxx - minx) / cell) + 1u;
  const uint32_t ny = static_cast<uint32_t>((maxy - miny) / cell) + 1u;
  std::vector<float> acc(static_cast<size_t>(nx) * ny, 0.f);
  uint32_t signalised = 0;
  for (uint32_t ni = 0; ni < g.nodeCount(); ++ni) {
    if (g.node(ni).control != routing::Control::Signal) continue;
    ++signalised;
    const routing::Vec3& p = g.node(ni).pos;
    const uint32_t cx = static_cast<uint32_t>(std::min(std::max((p.x - minx) / cell, 0.f),
                                                       static_cast<float>(nx - 1u)));
    const uint32_t cy = static_cast<uint32_t>(std::min(std::max((p.y - miny) / cell, 0.f),
                                                       static_cast<float>(ny - 1u)));
    acc[static_cast<size_t>(cy) * nx + cx] += 1.f;
  }
  if (signalised == 0) {  // synthetic worlds without Control::Signal nodes
    for (uint32_t li = 0; li < g.laneCount(); ++li) {
      const routing::Lane& l = g.lane(li);
      if (l.is_junction != 0) continue;
      const routing::LanePose p = g.poseAt(li, l.length_m * 0.5f);
      const uint32_t cx = static_cast<uint32_t>(std::min(std::max((p.pos.x - minx) / cell, 0.f),
                                                         static_cast<float>(nx - 1u)));
      const uint32_t cy = static_cast<uint32_t>(std::min(std::max((p.pos.y - miny) / cell, 0.f),
                                                         static_cast<float>(ny - 1u)));
      acc[static_cast<size_t>(cy) * nx + cx] += l.length_m;
    }
  }
  size_t best = 0;
  for (size_t i = 1; i < acc.size(); ++i)
    if (acc[i] > acc[best]) best = i;
  out_x = minx + (static_cast<float>(best % nx) + 0.5f) * cell;
  out_y = miny + (static_cast<float>(best / nx) + 0.5f) * cell;
}

/// Explicit seeding inside a radius of (x, y).
///
/// The production spawner samples a lane from a city-wide CDF and then rejects
/// it if it falls outside the player's ring, so on the real graph it accepts
/// roughly one lane in a thousand and can never fill the ring (measured: 86
/// vehicles against a target of 304,878).  That is a defect of the spawner, not
/// of the step, and fixing it would change the spawn sequence and therefore the
/// ring test's counts — so the benchmark seeds the fleet through the public
/// spawn() API instead, and the report says so.
uint32_t seedVehiclesNear(traffic::TrafficSim& sim, const routing::RoadGraph& g, float x, float y,
                          float radius_m, uint32_t want, uint64_t seed) {
  std::vector<uint32_t> lanes;
  const float step = 60.f;
  for (float dy = -radius_m; dy <= radius_m; dy += step) {
    for (float dx = -radius_m; dx <= radius_m; dx += step) {
      if (dx * dx + dy * dy > radius_m * radius_m) continue;
      uint32_t buf[64];
      const uint32_t n = g.lanesNear(x + dx, y + dy, step, buf, 64, false);
      for (uint32_t k = 0; k < std::min(n, 64u); ++k) {
        const routing::Lane& l = g.lane(buf[k]);
        if (l.is_junction != 0 || l.disabled != 0 || l.kind != routing::LaneKind::Travel) continue;
        if (l.length_m < 15.f) continue;
        lanes.push_back(buf[k]);
      }
    }
  }
  std::sort(lanes.begin(), lanes.end());
  lanes.erase(std::unique(lanes.begin(), lanes.end()), lanes.end());
  if (lanes.empty()) return 0;
  nycsim::Rng rng;
  rng.reseed(seed);
  uint32_t made = 0, attempts = 0;
  while (made < want && attempts < want * 20u + 1000u) {
    ++attempts;
    const uint32_t lane = lanes[rng.below(static_cast<uint32_t>(lanes.size()))];
    const float len = g.lane(lane).length_m;
    const float s = rng.uniform(2.f, std::max(3.f, len - 2.f));
    if (sim.spawn(traffic::VehicleClass::Sedan, lane, s, routing::kInvalidIndex, 0.f, true) !=
        routing::kInvalidIndex)
      ++made;
  }
  return made;
}

uint32_t seedPedsNear(peds::PedSim& sim, const peds::SidewalkGraph& w, float x, float y, float radius_m,
                      uint32_t want, uint64_t seed) {
  std::vector<uint32_t> edges;
  for (uint32_t e = 0; e < w.edgeCount(); ++e) {
    const peds::WalkEdge& ed = w.edge(e);
    const routing::Vec3 mid = w.pointOn(e, ed.length_m * 0.5f, 0.f);
    const float dx = mid.x - x, dy = mid.y - y;
    if (dx * dx + dy * dy > radius_m * radius_m) continue;
    edges.push_back(e);
  }
  if (edges.empty()) return 0;
  nycsim::Rng rng;
  rng.reseed(seed);
  uint32_t made = 0, attempts = 0;
  while (made < want && attempts < want * 20u + 1000u) {
    ++attempts;
    const uint32_t e = edges[rng.below(static_cast<uint32_t>(edges.size()))];
    const float s = rng.uniform(0.f, w.edge(e).length_m);
    if (sim.spawn(e, s, true) != routing::kInvalidIndex) ++made;
  }
  return made;
}

/// Steps both simulations and collects the distributions.  `player` is moved
/// along +y so the spawn/despawn ring keeps working.
StepResult measure(traffic::TrafficSim& tsim, peds::PedSim* psim, traffic::PlayerProxy player,
                   float dt, float miny, float maxy, const StepOptions& o) {
  std::vector<double> tw, pw, tot_w, tot_c;
  tw.reserve(o.steps);
  pw.reserve(o.steps);
  tot_w.reserve(o.steps);
  tot_c.reserve(o.steps);
  Stopwatch sw;
  for (uint32_t i = 0; i < o.warmup + o.steps; ++i) {
    player.y += player.speed_mps * dt;
    if (player.y > maxy - 50.f) player.y = miny + 50.f;
    tsim.setPlayer(player);
    if (psim != nullptr) psim->setPlayer(player);

    double w0 = 0, c0 = 0, w1 = 0, c1 = 0;
    sw.reset();
    tsim.step();
    sw.lap(w0, c0);
    if (psim != nullptr) psim->step();
    sw.lap(w1, c1);
    if (i < o.warmup) continue;
    tw.push_back(w0);
    pw.push_back(w1);
    tot_w.push_back(w0 + w1);
    tot_c.push_back(c0 + c1);
  }
  StepResult r;
  double wall_sum = 0, cpu_sum = 0;
  for (double v : tot_w) wall_sum += v;
  for (double v : tot_c) cpu_sum += v;
  r.traffic_wall = distribution(tw);
  r.ped_wall = distribution(pw);
  r.total_wall = distribution(tot_w);
  r.total_cpu = distribution(tot_c);
  r.contention_pct = wall_sum > 1e-9 ? (wall_sum - cpu_sum) / wall_sum * 100.0 : 0.0;
  r.vehicles = tsim.stats().vehicles;
  r.peds = psim != nullptr ? psim->stats().peds : 0u;
  r.traffic_hash = tsim.trajectoryHash();
  r.ped_hash = psim != nullptr ? psim->trajectoryHash() : 0u;
  if (!o.csv.empty()) {
    FILE* f = std::fopen(o.csv.c_str(), "w");
    if (f == nullptr) {
      std::fprintf(stderr, "  warning: cannot write %s\n", o.csv.c_str());
    } else {
      std::fprintf(f, "step,traffic_ms,peds_ms,total_wall_ms,total_cpu_ms\n");
      for (size_t i = 0; i < tot_w.size(); ++i)
        std::fprintf(f, "%zu,%.6f,%.6f,%.6f,%.6f\n", i, tw[i], pw[i], tot_w[i], tot_c[i]);
      std::fclose(f);
      std::printf("  wrote %s\n", o.csv.c_str());
    }
  }
  return r;
}

void report(const StepResult& r) {
  std::printf("  fleet            %u vehicles, %u pedestrians\n", r.vehicles, r.peds);
  printDist("traffic (wall)", r.traffic_wall);
  printDist("peds (wall)", r.ped_wall);
  printDist("combined wall", r.total_wall);
  printDist("combined CPU", r.total_cpu);
  std::printf("  contention       %.1f %% of wall time was not on-CPU\n", r.contention_pct);
  std::printf("  budget           8.000 ms at 20 Hz -> %s on CPU time (%.1f %% of budget)\n",
              r.total_cpu.mean < 8.0 ? "PASS" : "FAIL", r.total_cpu.mean / 8.0 * 100.0);
  std::printf("  trajectory hash  traffic %016llx  peds %016llx\n",
              static_cast<unsigned long long>(r.traffic_hash),
              static_cast<unsigned long long>(r.ped_hash));
}

bool parseCommon(Args& args, StepOptions& o) {
  args.integer("--vehicles", o.vehicles);
  args.integer("--peds", o.peds);
  args.integer("--steps", o.steps);
  args.integer("--warmup", o.warmup);
  args.integer64("--seed", o.seed);
  if (args.flag("--no-peds")) o.with_peds = false;
  args.text("--csv", o.csv);
  return true;
}

}  // namespace

// ------------------------------------------------------------- synthetic
int runSynthetic(Args& args) {
  StepOptions o;
  parseCommon(args, o);
  uint32_t avenues = 14, streets = 28;
  args.integer("--avenues", avenues);
  args.integer("--streets", streets);
  if (!args.ok()) return args.fail();

  std::printf("nycsim_bench synthetic\n");
  printLoad("before");
  World w;
  std::string err;
  if (!w.buildSynthetic(static_cast<int>(avenues), static_cast<int>(streets), err)) {
    std::fprintf(stderr, "grid build failed: %s\n", err.c_str());
    return 1;
  }
  if (!w.buildSidewalks(err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  w.setUniformDensity(o.vehicles, o.peds);
  if (!w.attachRouter(6, o.seed, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }

  traffic::TrafficConfig tcfg;
  tcfg.max_vehicles = o.vehicles + 500u;
  tcfg.use_player_ring = true;
  tcfg.spawn_outer_m = 1.0e6f;  // the grid is smaller than the ring: hold the fleet
  tcfg.despawn_m = 1.0e6f;
  traffic::TrafficSim tsim;
  Stopwatch sw;
  if (!tsim.configure(w.graph, w.signals, tcfg, o.seed)) {
    std::fprintf(stderr, "traffic configure failed: %s\n", tsim.lastError().c_str());
    return 1;
  }
  w.times().traffic_cfg_ms = sw.lapWallMs();
  tsim.setDensityTable(&w.density);
  tsim.setRouter(&w.router);
  tsim.setTimeOfDay(8.5f * 3600.f, 0);

  peds::PedConfig pcfg;
  pcfg.max_peds = o.peds + 2000u;
  pcfg.use_player_ring = true;
  pcfg.despawn_m = 1.0e6f;
  peds::PedSim psim;
  if (o.with_peds) {
    if (!psim.configure(w.walk, &w.signals, pcfg, o.seed)) {
      std::fprintf(stderr, "peds configure failed: %s\n", psim.lastError().c_str());
      return 1;
    }
    w.times().ped_cfg_ms = sw.lapWallMs();
    psim.setDensityTable(&w.density);
    psim.setTimeOfDay(8.5f * 3600.f, 0);
    psim.setFastZone(w.uniform_nta, true);
    tsim.setPedProbe(psim.pedProbe());
    psim.setVehicleProbe(tsim.vehicleProbe());
  }

  float minx, miny, maxx, maxy;
  w.graph.bounds(minx, miny, maxx, maxy);
  traffic::PlayerProxy player;
  player.valid = true;
  player.x = (minx + maxx) * 0.5f;
  player.y = miny + 50.f;
  player.heading_rad = 1.5707963f;
  player.speed_mps = 9.f;
  tsim.setPlayer(player);
  if (o.with_peds) psim.setPlayer(player);

  sw.reset();
  const uint32_t made_v = tsim.prefill(o.vehicles + 1000u);
  const uint32_t made_p = o.with_peds ? psim.prefill(o.peds) : 0u;
  w.times().prefill_ms = sw.lapWallMs();

  std::printf("  grid             %u avenues x %u streets, %zu nodes, %zu lanes, %.1f lane-km\n", avenues,
              streets, w.sizes().nodes, w.sizes().lanes, w.sizes().lane_km);
  std::printf("  sidewalks        %zu nodes, %zu edges, %.0f m2, %zu walls\n", w.sizes().walk_nodes,
              w.sizes().walk_edges, w.sizes().sidewalk_m2, w.sizes().walk_walls);
  std::printf("  build            graph %.1f ms, sidewalks %.1f ms, router %.1f ms, configure %.1f ms,"
              " prefill %.1f ms\n",
              w.times().graph_ms, w.times().sidewalk_ms, w.times().router_ms, w.times().traffic_cfg_ms,
              w.times().prefill_ms);
  std::printf("  prefilled        %u vehicles, %u pedestrians\n", made_v, made_p);
  std::fflush(stdout);

  const StepResult r = measure(tsim, o.with_peds ? &psim : nullptr, player, tcfg.dt, miny, maxy, o);
  std::printf("  steps measured   %u (after %u warm-up)\n", o.steps, o.warmup);
  report(r);
  std::printf("  resident         %s (peak %s)\n", mb(residentBytes()).c_str(),
              mb(peakResidentBytes()).c_str());
  printLoad("after");
  return 0;
}

// ------------------------------------------------------------------ city
int runCity(Args& args) {
  StepOptions o;
  o.steps = 600;
  parseCommon(args, o);
  std::string runtime = defaultRuntimeDir();
  args.text("--runtime", runtime);
  const bool no_sidewalks = args.flag("--no-sidewalks");
  const bool real_density = !args.flag("--uniform-density");
  double spawn_outer = 900.0, despawn = 1400.0, signal_window = -1.0, seed_radius = 1000.0;
  uint32_t max_routes = 8;
  args.number("--spawn-outer", spawn_outer);
  args.number("--despawn", despawn);
  args.number("--signal-window", signal_window);
  args.number("--seed-radius", seed_radius);
  args.integer("--max-routes", max_routes);
  uint32_t max_paths = 96;
  double ped_cell = 0.0;
  args.integer("--max-paths", max_paths);
  args.number("--ped-cell", ped_cell);
  const bool use_spawner = args.flag("--use-spawner");
  double player_x = 0, player_y = 0;
  const bool have_px = args.number("--player-x", player_x);
  const bool have_py = args.number("--player-y", player_y);
  if (!args.ok()) return args.fail();

  std::printf("nycsim_bench city\n");
  printLoad("before");
  World w;
  std::string err;
  const uint64_t rss0 = residentBytes();
  if (!w.loadCity(runtime, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  std::printf("  artefacts        %s\n", runtime.c_str());
  std::printf("  graph            %zu nodes, %zu segments, %zu lanes (%zu junction), %.0f lane-km\n",
              w.sizes().nodes, w.sizes().segments, w.sizes().lanes, w.sizes().junction_lanes,
              w.sizes().lane_km);
  std::printf("  signals          %zu plans%s\n", w.sizes().signal_plans,
              w.signals.lastError().empty() ? "" : (" [" + w.signals.lastError() + "]").c_str());
  std::printf("  density          %zu polygons, %u NTAs;  transit %zu bus routes\n",
              w.sizes().density_cells, w.density.ntaCount(), w.sizes().bus_routes);
  std::printf("  load times       read %.0f ms, graph %.0f ms, signals %.0f ms, density %.0f ms,"
              " transit %.0f ms\n",
              w.times().read_ms, w.times().graph_ms, w.times().signals_ms, w.times().density_ms,
              w.times().transit_ms);
  std::printf("  resident         %s after loading (was %s)\n", mb(residentBytes()).c_str(),
              mb(rss0).c_str());
  std::fflush(stdout);

  if (!no_sidewalks && o.with_peds) {
    if (!w.buildSidewalks(err)) {
      std::fprintf(stderr, "%s\n", err.c_str());
      return 1;
    }
    std::printf("  sidewalks        %zu nodes, %zu edges, %.0f m2, %zu walls in %.0f ms (resident %s)\n",
                w.sizes().walk_nodes, w.sizes().walk_edges, w.sizes().sidewalk_m2, w.sizes().walk_walls,
                w.times().sidewalk_ms, mb(residentBytes()).c_str());
  } else {
    o.with_peds = false;
  }
  std::fflush(stdout);

  if (!w.attachRouter(6, o.seed, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  std::printf("  router           attached in %.0f ms (resident %s)\n", w.times().router_ms,
              mb(residentBytes()).c_str());
  std::fflush(stdout);

  float px = 0, py = 0;
  densestPoint(w.graph, px, py);
  if (have_px) px = static_cast<float>(player_x);
  if (have_py) py = static_cast<float>(player_y);
  const routing::NearestLane snap = w.graph.nearestLane(px, py, routing::kAllLaneKinds, 500.f);
  if (snap.lane != routing::kInvalidIndex)
    std::printf("  camera           (%.0f, %.0f) on %.*s\n", static_cast<double>(px),
                static_cast<double>(py), static_cast<int>(w.graph.laneStreetName(snap.lane).size()),
                w.graph.laneStreetName(snap.lane).data());

  traffic::TrafficConfig tcfg;
  tcfg.max_vehicles = o.vehicles + 1000u;
  tcfg.use_player_ring = true;
  tcfg.spawn_outer_m = static_cast<float>(spawn_outer);
  tcfg.despawn_m = static_cast<float>(despawn);
  tcfg.max_routes_per_step = max_routes;
  traffic::TrafficSim tsim;
  Stopwatch sw;
  if (!tsim.configure(w.graph, w.signals, tcfg, o.seed)) {
    std::fprintf(stderr, "traffic configure failed: %s\n", tsim.lastError().c_str());
    return 1;
  }
  w.times().traffic_cfg_ms = sw.lapWallMs();
  std::printf("  traffic config   %.0f ms (junction conflicts over %zu junction lanes), resident %s\n",
              w.times().traffic_cfg_ms, w.sizes().junction_lanes, mb(residentBytes()).c_str());
  std::fflush(stdout);

  if (real_density) {
    tsim.setDensityTable(&w.density);
  } else {
    w.setUniformDensity(o.vehicles, o.peds);
    tsim.setDensityTable(&w.density);
  }
  tsim.setRouter(&w.router);
  tsim.setBusRoutes(&w.buses);
  tsim.setTimeOfDay(8.5f * 3600.f, 0);

  peds::PedConfig pcfg;
  pcfg.max_peds = o.peds + 2000u;
  pcfg.use_player_ring = true;
  pcfg.despawn_m = static_cast<float>(despawn);
  pcfg.max_paths_per_step = max_paths;
  pcfg.hash_cell_m = static_cast<float>(ped_cell);
  peds::PedSim psim;
  if (o.with_peds) {
    if (!psim.configure(w.walk, &w.signals, pcfg, o.seed)) {
      std::fprintf(stderr, "peds configure failed: %s\n", psim.lastError().c_str());
      return 1;
    }
    psim.setDensityTable(&w.density);
    psim.setTimeOfDay(8.5f * 3600.f, 0);
    tsim.setPedProbe(psim.pedProbe());
    psim.setVehicleProbe(tsim.vehicleProbe());
  }

  traffic::PlayerProxy player;
  player.valid = true;
  player.x = px;
  player.y = py;
  player.heading_rad = 1.5707963f;
  player.speed_mps = 9.f;
  tsim.setPlayer(player);
  if (o.with_peds) psim.setPlayer(player);

  if (signal_window > 0.0) {
    const float h = static_cast<float>(signal_window) * 0.5f;
    w.signals.setActiveWindow(px - h, py - h, px + h, py + h);
    std::printf("  signal window    %.0f m square around the camera\n", signal_window);
  }

  sw.reset();
  uint32_t made_v = 0, made_p = 0;
  if (use_spawner) {
    made_v = tsim.prefill(o.vehicles + 1000u);
    made_p = o.with_peds ? psim.prefill(o.peds) : 0u;
  } else {
    // Seeded explicitly inside `seed_radius` of the camera — see the comment on
    // seedVehiclesNear() for why the production spawner cannot do this.
    made_v = seedVehiclesNear(tsim, w.graph, px, py, static_cast<float>(seed_radius), o.vehicles, o.seed);
    if (o.with_peds)
      made_p = seedPedsNear(psim, w.walk, px, py, static_cast<float>(seed_radius), o.peds, o.seed);
  }
  w.times().prefill_ms = sw.lapWallMs();
  std::printf("  fill             %u vehicles, %u pedestrians in %.0f ms (%s; density target %.0f"
              " vehicles city-wide)\n",
              made_v, made_p, w.times().prefill_ms,
              use_spawner ? "prefill(), city-wide" : "seeded within the radius",
              static_cast<double>(tsim.targetVehicles()));
  std::printf("  budgets          %u route queries and %u pedestrian paths per step;"
              " crowd hash cell %s\n",
              max_routes, o.with_peds ? max_paths : 0u,
              ped_cell > 0.01 ? std::to_string(static_cast<int>(ped_cell)).c_str() : "auto");
  std::fflush(stdout);

  float minx, miny, maxx, maxy;
  w.graph.bounds(minx, miny, maxx, maxy);
  const StepResult r = measure(tsim, o.with_peds ? &psim : nullptr, player, tcfg.dt,
                               py - static_cast<float>(seed_radius) * 0.5f,
                               py + static_cast<float>(seed_radius) * 0.5f, o);
  std::printf("  steps measured   %u (after %u warm-up)\n", o.steps, o.warmup);
  report(r);
  if (signal_window > 0.0)
    std::printf("  signal refresh   %u of %zu plans per step\n", w.signals.cachedPlanCount(),
                w.sizes().signal_plans);
  std::printf("  resident         %s (peak %s)\n", mb(residentBytes()).c_str(),
              mb(peakResidentBytes()).c_str());
  printLoad("after");
  return 0;
}

// ------------------------------------------------------------------ soak
int runSoak(Args& args) {
  StepOptions o;
  o.warmup = 0;
  parseCommon(args, o);
  double minutes = 35.0;
  uint32_t sample_every = 200;
  args.number("--minutes", minutes);
  args.integer("--sample-steps", sample_every);
  const bool city = args.flag("--city");
  std::string runtime = defaultRuntimeDir();
  args.text("--runtime", runtime);
  if (!args.ok()) return args.fail();

  std::printf("nycsim_bench soak\n");
  printLoad("before");
  World w;
  std::string err;
  if (city) {
    if (!w.loadCity(runtime, err)) {
      std::fprintf(stderr, "%s\n", err.c_str());
      return 1;
    }
  } else if (!w.buildSynthetic(14, 28, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  if (o.with_peds && !w.buildSidewalks(err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  if (!city) w.setUniformDensity(o.vehicles, o.peds);
  if (!w.attachRouter(6, o.seed, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }

  float px = 0, py = 0;
  densestPoint(w.graph, px, py);
  float minx, miny, maxx, maxy;
  w.graph.bounds(minx, miny, maxx, maxy);

  // A tight ring, so agents are created and destroyed continuously: the point
  // of the run is churn, not fleet size.
  traffic::TrafficConfig tcfg;
  tcfg.max_vehicles = o.vehicles + 1000u;
  tcfg.use_player_ring = true;
  tcfg.spawn_outer_m = 700.f;
  tcfg.despawn_m = 1000.f;
  traffic::TrafficSim tsim;
  if (!tsim.configure(w.graph, w.signals, tcfg, o.seed)) {
    std::fprintf(stderr, "traffic configure failed: %s\n", tsim.lastError().c_str());
    return 1;
  }
  tsim.setDensityTable(&w.density);
  tsim.setRouter(&w.router);
  tsim.setTimeOfDay(8.5f * 3600.f, 0);

  peds::PedConfig pcfg;
  pcfg.max_peds = o.peds + 2000u;
  pcfg.use_player_ring = true;
  pcfg.despawn_m = 700.f;
  peds::PedSim psim;
  if (o.with_peds) {
    if (!psim.configure(w.walk, &w.signals, pcfg, o.seed)) {
      std::fprintf(stderr, "peds configure failed: %s\n", psim.lastError().c_str());
      return 1;
    }
    psim.setDensityTable(&w.density);
    psim.setTimeOfDay(8.5f * 3600.f, 0);
    tsim.setPedProbe(psim.pedProbe());
    psim.setVehicleProbe(tsim.vehicleProbe());
  }

  traffic::PlayerProxy player;
  player.valid = true;
  player.x = px;
  player.y = py;
  player.heading_rad = 1.5707963f;
  player.speed_mps = 11.f;
  tsim.setPlayer(player);
  if (o.with_peds) psim.setPlayer(player);
  tsim.prefill(o.vehicles);
  if (o.with_peds) psim.prefill(o.peds);

  const uint32_t total_steps = static_cast<uint32_t>(minutes * 60.0 / static_cast<double>(tcfg.dt));
  std::printf("  world            %s, %.0f lane-km, %zu sidewalk edges\n", city ? "real city" : "synthetic",
              w.sizes().lane_km, w.sizes().walk_edges);
  std::printf("  plan             %.1f simulated minutes = %u steps at %.0f Hz, sampling RSS every %u\n",
              minutes, total_steps, 1.0 / static_cast<double>(tcfg.dt), sample_every);
  std::fflush(stdout);

  std::vector<double> t_min, rss_mb;
  FILE* csv = o.csv.empty() ? nullptr : std::fopen(o.csv.c_str(), "w");
  if (csv != nullptr) std::fprintf(csv, "step,sim_minutes,rss_bytes,vehicles,peds,spawned,despawned\n");
  // The camera walks a closed loop so the ring sweeps new ground continuously.
  const float radius = 600.f;
  for (uint32_t i = 0; i < total_steps; ++i) {
    const float ang = static_cast<float>(i) * 0.0009f;
    player.x = px + radius * std::cos(ang);
    player.y = py + radius * std::sin(ang);
    player.heading_rad = ang + 1.5707963f;
    tsim.setPlayer(player);
    if (o.with_peds) psim.setPlayer(player);
    tsim.step();
    if (o.with_peds) psim.step();
    if (i % sample_every != 0u) continue;
    const double minute = static_cast<double>(i) * static_cast<double>(tcfg.dt) / 60.0;
    const uint64_t rss = residentBytes();
    t_min.push_back(minute);
    rss_mb.push_back(static_cast<double>(rss) / (1024.0 * 1024.0));
    if (csv != nullptr)
      std::fprintf(csv, "%u,%.4f,%llu,%u,%u,%u,%u\n", i, minute, static_cast<unsigned long long>(rss),
                   tsim.stats().vehicles, o.with_peds ? psim.stats().peds : 0u, tsim.stats().spawned,
                   tsim.stats().despawned);
  }
  if (csv != nullptr) {
    std::fclose(csv);
    std::printf("  wrote %s\n", o.csv.c_str());
  }

  // The first minute is warm-up: buffers reach their high-water mark and the
  // allocator settles.  The slope that matters is the one after that.
  size_t from = 0;
  while (from + 1 < t_min.size() && t_min[from] < 1.0) ++from;
  std::vector<double> tt(t_min.begin() + static_cast<ptrdiff_t>(from), t_min.end());
  std::vector<double> rr(rss_mb.begin() + static_cast<ptrdiff_t>(from), rss_mb.end());
  const double k = slope(tt, rr);
  double lo = 1e30, hi = -1e30;
  for (double v : rr) {
    lo = std::min(lo, v);
    hi = std::max(hi, v);
  }
  std::printf("  churn            %u spawns, %u despawns (vehicles); %u / %u (pedestrians)\n",
              tsim.stats().spawned, tsim.stats().despawned,
              o.with_peds ? psim.stats().spawned : 0u, o.with_peds ? psim.stats().despawned : 0u);
  std::printf("  population       %u vehicles, %u pedestrians at the end\n", tsim.stats().vehicles,
              o.with_peds ? psim.stats().peds : 0u);
  std::printf("  RSS samples      %zu after the first simulated minute, %.1f - %.1f MB (spread %.2f MB)\n",
              rr.size(), lo, hi, hi - lo);
  std::printf("  RSS slope        %+.4f MB per simulated minute (%+.2f MB per simulated hour)\n", k,
              k * 60.0);
  std::printf("  resident         %s (peak %s)\n", mb(residentBytes()).c_str(),
              mb(peakResidentBytes()).c_str());
  printLoad("after");
  return 0;
}

}  // namespace nycbench
