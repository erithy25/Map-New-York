// core/bench/bench_stream.cpp — TileScheduler driven along a real, long route.
//
// The scheduler has unit tests but has never driven a real journey.  This takes
// the route the roads stage verified — Fordham Road & Grand Concourse in the
// Bronx to Hylan Boulevard & Richmond Avenue on Staten Island, 49.38 km across
// the Verrazzano-Narrows Bridge — computes it on the real lane graph, and flies
// the camera along it at highway speed, reporting what the streamer does.
//
// The tile catalogue is built from what is actually on disk: every
// data/processed/tiles/t_*/ (terrain) and blender_out/tiles/t_*/ (buildings),
// with the real file sizes, so the memory budget is checked against real bytes
// as well as against the engine's TileCostModel estimate.
#include <sys/stat.h>
#include <sys/types.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <dirent.h>
#include <map>
#include <string>
#include <vector>

#include "bench_common.h"
#include "bench_options.h"
#include "bench_world.h"
#include "nycsim/io/Json.h"
#include "nycsim/tiling/Tile.h"
#include "nycsim/tiling/TileScheduler.h"

namespace nycbench {

using namespace nycsim;

namespace {

struct DiskTile {
  int32_t tx = 0, ty = 0;
  uint64_t terrain_bytes = 0;
  uint64_t building_bytes = 0;
  uint32_t buildings = 0;
  bool has_terrain = false, has_land = false, has_water = false;
};

uint64_t fileSize(const std::string& path) {
  struct stat st {};
  if (stat(path.c_str(), &st) != 0) return 0;
  return static_cast<uint64_t>(st.st_size);
}

/// Parses "t_<tx>_<ty>"; false for anything else (including "_logs", "_merged").
bool parseTileDir(const char* name, int32_t& tx, int32_t& ty) {
  const Result<tiling::Tile> t = tiling::Tile::parse(std::string_view(name));
  if (!t) return false;
  tx = t.value().tx;
  ty = t.value().ty;
  return true;
}

/// Reads a JSON file; returns false (with `why` filled) on any failure.
bool readJson(const std::string& path, json::Value& out, std::string& why) {
  std::vector<uint8_t> bytes;
  if (!readFile(path.c_str(), bytes)) {
    why = "cannot read " + path;
    return false;
  }
  Result<json::Value> v =
      json::parse(std::string_view(reinterpret_cast<const char*>(bytes.data()), bytes.size()));
  if (!v) {
    why = path + ": " + std::string(v.error().message);
    return false;
  }
  out = std::move(v.value());
  return true;
}

/// Scans both tile trees.  `bad` counts directories whose metadata could not be
/// read; they are still catalogued (with zero counts) and reported.
std::vector<DiskTile> scanTiles(const std::string& terrain_dir, const std::string& building_dir,
                                uint32_t& bad, std::string& first_error) {
  std::map<int64_t, DiskTile> byKey;
  auto key = [](int32_t tx, int32_t ty) {
    return (static_cast<int64_t>(tx) << 32) ^ static_cast<int64_t>(static_cast<uint32_t>(ty));
  };
  bad = 0;

  DIR* d = opendir(terrain_dir.c_str());
  if (d != nullptr) {
    while (const dirent* e = readdir(d)) {
      int32_t tx = 0, ty = 0;
      if (!parseTileDir(e->d_name, tx, ty)) continue;
      DiskTile t;
      t.tx = tx;
      t.ty = ty;
      const std::string base = terrain_dir + "/" + e->d_name;
      t.terrain_bytes = fileSize(base + "/terrain.png") + fileSize(base + "/props.parquet");
      t.has_terrain = t.terrain_bytes > 0;
      json::Value meta;
      std::string why;
      if (readJson(base + "/terrain.json", meta, why)) {
        const json::Value* land = meta.find("has_land");
        const json::Value* water = meta.find("has_water");
        t.has_land = land != nullptr && land->asBool(false);
        t.has_water = water != nullptr && water->asBool(false);
      } else {
        ++bad;
        if (first_error.empty()) first_error = why;
      }
      byKey[key(tx, ty)] = t;
    }
    closedir(d);
  } else {
    first_error = "cannot open " + terrain_dir;
  }

  d = opendir(building_dir.c_str());
  if (d != nullptr) {
    while (const dirent* e = readdir(d)) {
      int32_t tx = 0, ty = 0;
      if (!parseTileDir(e->d_name, tx, ty)) continue;
      DiskTile& t = byKey[key(tx, ty)];
      t.tx = tx;
      t.ty = ty;
      const std::string base = building_dir + "/" + e->d_name;
      t.building_bytes = fileSize(base + "/tile_buildings.glb");
      json::Value meta;
      std::string why;
      if (readJson(base + "/manifest.json", meta, why)) {
        const json::Value* b = meta.find("buildings");
        const json::Value* solids = b != nullptr ? b->find("solids") : nullptr;
        if (solids != nullptr && solids->isNumber())
          t.buildings = static_cast<uint32_t>(solids->asNumber(0.0));
      } else {
        ++bad;
        if (first_error.empty()) first_error = why;
      }
    }
    closedir(d);
  } else if (first_error.empty()) {
    first_error = "cannot open " + building_dir;
  }

  std::vector<DiskTile> out;
  out.reserve(byKey.size());
  for (const auto& kv : byKey) out.push_back(kv.second);
  return out;
}

double distanceToTile(int32_t tx, int32_t ty, double x, double y) {
  const tiling::TileBounds b = tiling::Tile{tx, ty}.bounds();
  const double dx = std::max(std::max(b.xmin - x, 0.0), x - b.xmax);
  const double dy = std::max(std::max(b.ymin - y, 0.0), y - b.ymax);
  return std::sqrt(dx * dx + dy * dy);
}

}  // namespace

int runStream(Args& args) {
  std::string runtime = defaultRuntimeDir();
  std::string terrain_dir = "data/processed/tiles";
  std::string building_dir = "blender_out/tiles";
  std::string csv;
  double speed_kmh = 100.0, budget_gb = 8.0;
  uint64_t from_node = 48752, to_node = 83848;
  args.text("--runtime", runtime);
  args.text("--terrain-dir", terrain_dir);
  args.text("--building-dir", building_dir);
  args.text("--csv", csv);
  args.number("--speed", speed_kmh);
  args.number("--budget-gb", budget_gb);
  args.integer64("--from-node", from_node);
  args.integer64("--to-node", to_node);
  if (!args.ok()) return args.fail();

  std::printf("nycsim_bench stream\n");
  printLoad("before");

  // ---- catalogue -------------------------------------------------------
  uint32_t bad = 0;
  std::string why;
  Stopwatch sw;
  const std::vector<DiskTile> disk = scanTiles(terrain_dir, building_dir, bad, why);
  const double scan_ms = sw.lapWallMs();
  if (disk.empty()) {
    std::fprintf(stderr, "no tiles found under %s or %s (%s)\n", terrain_dir.c_str(),
                 building_dir.c_str(), why.c_str());
    return 1;
  }
  uint64_t terrain_total = 0, building_total = 0, buildings = 0;
  uint32_t with_terrain = 0, with_buildings = 0;
  for (const DiskTile& t : disk) {
    terrain_total += t.terrain_bytes;
    building_total += t.building_bytes;
    buildings += t.buildings;
    if (t.has_terrain) ++with_terrain;
    if (t.building_bytes > 0) ++with_buildings;
  }
  std::printf("  catalogue        %zu tiles in %.0f ms: %u with terrain, %u with buildings,"
              " %llu buildings\n",
              disk.size(), scan_ms, with_terrain, with_buildings,
              static_cast<unsigned long long>(buildings));
  std::printf("  on disk          terrain %s, buildings %s, total %s\n", mb(terrain_total).c_str(),
              mb(building_total).c_str(), mb(terrain_total + building_total).c_str());
  if (bad > 0) std::printf("  metadata         %u tile(s) with unreadable metadata; first: %s\n", bad, why.c_str());

  std::vector<tiling::TileInfo> infos;
  infos.reserve(disk.size());
  // TileScheduler sorts its entries by (ty, tx); `disk` is keyed by (tx, ty), so
  // the real byte sizes are looked up by coordinate rather than by index.
  std::map<int64_t, uint64_t> real_by_tile;
  auto tileKey = [](int32_t tx, int32_t ty) {
    return (static_cast<int64_t>(tx) << 32) ^ static_cast<int64_t>(static_cast<uint32_t>(ty));
  };
  for (size_t i = 0; i < disk.size(); ++i) {
    const DiskTile& t = disk[i];
    tiling::TileInfo ti;
    ti.tx = t.tx;
    ti.ty = t.ty;
    ti.nBuildings = t.buildings;
    ti.nProps = 0;  // props.parquet row counts are not readable from C++; see REPORT
    ti.flags = static_cast<uint8_t>((t.has_terrain ? tiling::TileInfo::kHasTerrain : 0) |
                                    (t.has_water ? tiling::TileInfo::kHasWater : 0) |
                                    (t.has_land ? tiling::TileInfo::kHasLand : 0));
    infos.push_back(ti);
    real_by_tile[tileKey(t.tx, t.ty)] = t.terrain_bytes + t.building_bytes;
  }

  // ---- route -----------------------------------------------------------
  World w;
  std::string err;
  if (!w.loadCity(runtime, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  if (!w.attachRouter(6, 1u, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  const uint32_t na = w.graph.nodeIndex(static_cast<routing::NodeId>(from_node));
  const uint32_t nb = w.graph.nodeIndex(static_cast<routing::NodeId>(to_node));
  if (na == routing::kInvalidIndex || nb == routing::kInvalidIndex) {
    std::fprintf(stderr, "node id %llu or %llu is not in the road graph\n",
                 static_cast<unsigned long long>(from_node), static_cast<unsigned long long>(to_node));
    return 1;
  }
  const routing::Vec3 pa = w.graph.node(na).pos;
  const routing::Vec3 pb = w.graph.node(nb).pos;
  routing::RouteProfile profile;
  routing::RouteResult route;
  if (!w.router.routePoints(pa.x, pa.y, pb.x, pb.y, profile, route, 120.f) || !route.ok) {
    std::fprintf(stderr, "no route between the two intersections: %s\n", w.router.lastError().c_str());
    return 1;
  }
  // Which named streets, and how many Verrazzano segments — the roads stage
  // asserts 24, so the route can be identified rather than trusted.
  uint32_t verrazzano = 0;
  std::vector<uint32_t> seen_segments;
  for (uint32_t lane : route.lanes) {
    const uint32_t seg = w.graph.laneSegment(lane);
    if (seg == routing::kInvalidIndex) continue;
    if (std::find(seen_segments.begin(), seen_segments.end(), seg) != seen_segments.end()) continue;
    seen_segments.push_back(seg);
    const std::string_view name = w.graph.segmentName(seg);
    if (name.find("VERRAZZANO") != std::string_view::npos) ++verrazzano;
  }
  std::printf("  route            %zu lanes, %zu segments, %.2f km, free flow %.1f min,"
              " %u Verrazzano segments\n",
              route.lanes.size(), seen_segments.size(), static_cast<double>(route.length_m) / 1000.0,
              static_cast<double>(route.free_flow_s) / 60.0, verrazzano);
  std::printf("  polyline         %zu points\n", route.polyline.size());
  if (route.polyline.size() < 2) {
    std::fprintf(stderr, "route polyline too short to drive\n");
    return 1;
  }

  // ---- drive -----------------------------------------------------------
  tiling::SchedulerConfig cfg;
  cfg.budgetBytes = static_cast<uint64_t>(budget_gb * 1024.0 * 1024.0 * 1024.0);
  tiling::TileCostModel cost;
  tiling::TileScheduler sched(Span<const tiling::TileInfo>(infos.data(), infos.size()), cfg, cost);

  const double dt = 0.05;  // 20 Hz, the simulation's own step
  const double speed = speed_kmh / 3.6;
  double travelled = 0.0, t_s = 0.0;
  size_t seg_i = 0;
  double seg_pos = 0.0;
  uint64_t updates = 0, protected_evictions = 0, budget_denials_seen = 0;
  uint32_t peak_resident = 0;
  uint32_t peak_by_tier[5] = {0, 0, 0, 0, 0};
  uint64_t peak_model_bytes = 0, peak_real_bytes = 0;
  double worst_evicted_distance = 1e30;

  FILE* csv_f = csv.empty() ? nullptr : std::fopen(csv.c_str(), "w");
  if (csv_f != nullptr)
    std::fprintf(csv_f, "t_s,km,resident_tiles,model_bytes,real_bytes,loads,unloads\n");

  Stopwatch step_sw;
  std::vector<double> update_ms;
  while (seg_i + 1 < route.polyline.size()) {
    const routing::Vec3& a = route.polyline[seg_i];
    const routing::Vec3& b = route.polyline[seg_i + 1];
    const double sx = static_cast<double>(b.x) - static_cast<double>(a.x);
    const double sy = static_cast<double>(b.y) - static_cast<double>(a.y);
    const double len = std::sqrt(sx * sx + sy * sy);
    if (len < 1e-6) {
      ++seg_i;
      continue;
    }
    seg_pos += speed * dt;
    while (seg_pos >= len && seg_i + 1 < route.polyline.size()) {
      seg_pos -= len;
      ++seg_i;
      break;
    }
    if (seg_i + 1 >= route.polyline.size()) break;
    const double u = std::min(seg_pos / len, 1.0);
    tiling::CameraState cam;
    cam.x_m = static_cast<double>(a.x) + sx * u;
    cam.y_m = static_cast<double>(a.y) + sy * u;
    cam.vx_mps = sx / len * speed;
    cam.vy_mps = sy / len * speed;
    cam.heading_deg = std::atan2(cam.vx_mps, cam.vy_mps) * 180.0 / 3.14159265358979323846;
    cam.time_s = t_s;

    step_sw.reset();
    const std::vector<tiling::Transition>& tr = sched.update(cam);
    update_ms.push_back(step_sw.lapWallMs());
    ++updates;
    for (const tiling::Transition& x : tr) {
      const bool coarser = static_cast<int>(x.to) < static_cast<int>(x.from);
      if (!coarser) continue;
      const double d = distanceToTile(x.tx, x.ty, cam.x_m, cam.y_m);
      if (d < cfg.protectRadius_m) {
        ++protected_evictions;
        worst_evicted_distance = std::min(worst_evicted_distance, d);
      }
      if (x.budgetLimited) ++budget_denials_seen;
    }

    uint32_t resident = 0;
    uint64_t model_bytes = 0, real_now = 0;
    uint32_t by_tier[5] = {0, 0, 0, 0, 0};
    const Span<const tiling::TileScheduler::Entry> entries = sched.entries();
    for (size_t i = 0; i < entries.size(); ++i) {
      const tiling::TileScheduler::Entry& e = entries[i];
      ++by_tier[static_cast<size_t>(e.tier)];
      if (e.tier == tiling::Tier::Unloaded) continue;
      ++resident;
      model_bytes += cost.bytes(e.info, e.tier);
      const auto it = real_by_tile.find(tileKey(e.info.tx, e.info.ty));
      if (it != real_by_tile.end()) real_now += it->second;
    }
    if (resident > peak_resident) {
      for (size_t k = 0; k < 5; ++k) peak_by_tier[k] = by_tier[k];
    }
    peak_resident = std::max(peak_resident, resident);
    peak_model_bytes = std::max(peak_model_bytes, model_bytes);
    peak_real_bytes = std::max(peak_real_bytes, real_now);

    travelled += speed * dt;
    t_s += dt;
    if (csv_f != nullptr && (updates % 200u) == 0u)
      std::fprintf(csv_f, "%.2f,%.3f,%u,%llu,%llu,%llu,%llu\n", t_s, travelled / 1000.0, resident,
                   static_cast<unsigned long long>(model_bytes),
                   static_cast<unsigned long long>(real_now),
                   static_cast<unsigned long long>(sched.stats().totalLoads),
                   static_cast<unsigned long long>(sched.stats().totalUnloads));
  }
  if (csv_f != nullptr) {
    std::fclose(csv_f);
    std::printf("  wrote %s\n", csv.c_str());
  }

  const tiling::SchedulerStats& st = sched.stats();
  std::printf("  drive            %.2f km at %.0f km/h, %llu updates over %.1f simulated minutes\n",
              travelled / 1000.0, speed_kmh, static_cast<unsigned long long>(updates), t_s / 60.0);
  printDist("update (ms)", distribution(update_ms));
  std::printf("  transitions      %llu loads, %llu unloads, %llu upgrades, %llu downgrades\n",
              static_cast<unsigned long long>(st.totalLoads),
              static_cast<unsigned long long>(st.totalUnloads),
              static_cast<unsigned long long>(st.totalUpgrades),
              static_cast<unsigned long long>(st.totalDowngrades));
  std::printf("  peak resident    %u tiles;  model estimate %s, real bytes on disk %s\n", peak_resident,
              mb(peak_model_bytes).c_str(), mb(peak_real_bytes).c_str());
  std::printf("  peak by tier     L0 %u, L1 %u, L2 %u, L3 %u, unloaded %u\n", peak_by_tier[4],
              peak_by_tier[3], peak_by_tier[2], peak_by_tier[1], peak_by_tier[0]);
  std::printf("  budget           %.1f GB;  %llu tile-updates coarsened by the budget,"
              " over budget flag %s\n",
              budget_gb, static_cast<unsigned long long>(st.totalBudgetDenials),
              st.overBudget ? "SET" : "clear");
  std::printf("  protection ring  %llu transition(s) coarsened a tile within %.0f m of the camera%s\n",
              static_cast<unsigned long long>(protected_evictions), cfg.protectRadius_m,
              protected_evictions == 0 ? " — none, as required" : "");
  if (protected_evictions > 0)
    std::printf("                   closest such tile was %.1f m away\n", worst_evicted_distance);
  std::printf("  budget-limited   %llu of those transitions were budget driven\n",
              static_cast<unsigned long long>(budget_denials_seen));
  printLoad("after");
  return protected_evictions == 0 ? 0 : 1;
}

}  // namespace nycbench
