// agent_snapshot — run the shipped traffic and pedestrian simulations headlessly around one point
// and write the frame they produce as JSON, so a still render can show the agents the simulation
// actually puts there.
//
// This is not a second simulation.  It steps exactly the code the Unreal traffic subsystem steps —
// nycsim_gameplay::TrafficSim and nycsim_gameplay::PedSim from
// unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter — over the real city loaded from
// data/processed/runtime/*.nycb, and serialises the same VehicleSnapshot / PedSnapshot records that
// UNYCTrafficSubsystem reads out of the worker's double buffer (NYCTrafficWorker.h ReadSnapshot).
// unreal/tools/gameplay_selftest.cpp compiles those same four files against a synthetic grid; this
// tool compiles them against the shipped road graph, which is the only difference.
//
// Build (from the repository root; blender/verify/agents.py runs exactly this):
//   g++ -std=c++17 -O2 -o blender_out/verify/agent_snapshot
//       -Icore/include -Iunreal/NYCSim/Source/NYCSimRuntime/Private
//       blender/verify/agent_snapshot.cpp
//       unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter/Gameplay*.cpp
//       core/src/routing/*.cpp core/src/traffic/*.cpp core/src/vehicle/*.cpp
//
// blender/verify/agents.py builds it on demand and reads what it writes.
//
// Two configuration values are deliberately not the gameplay defaults, and the reason is written
// into the output so a reader of the sheet can see it:
//   * protect_radius_m = 0 and protect_cone_cos > 1.  The protected region is a gameplay rule that
//     stops agents appearing or vanishing in view of a *moving player*; it is why the default
//     configuration leaves a 250 m hole, plus the whole +-78 deg cone ahead, empty of spawns.  A
//     still frame has no player and no pop-in to hide, and that hole is exactly the part of the
//     frame the camera is looking at.
//   * the observer stands still.  Everything else — the density table, the fleet mix, the signal
//     plans, the spawn rules, the driver and walker models — is left as shipped.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "CoreAdapter/GameplayPedSim.h"
#include "CoreAdapter/GameplayRoadNetwork.h"
#include "CoreAdapter/GameplayTrafficSim.h"
#include "nycsim/traffic/VehicleClass.h"

using namespace nycsim_gameplay;

namespace {

struct Options {
  std::string runtime_dir = "data/processed/runtime";
  std::string out;              // "-" for stdout
  double x = 0.0, y = 0.0;      // observer, NYC_TM metres
  double heading_deg = 0.0;     // compass bearing the camera looks along (metadata only)
  uint32_t hour = 8;
  uint32_t dow = 0;             // 0 weekday, 1 Saturday, 2 Sunday
  uint64_t seed = 20260907ull;
  double warmup_s = 180.0;      // simulated seconds before the frame is taken
  double vehicle_radius_m = 420.0;
  double ped_radius_m = 220.0;
  uint32_t max_vehicles = 2400;
  uint32_t max_peds = 3000;
  double rain_mm_h = 0.0;
  double temperature_c = 15.0;
  double snow_cover = 0.0;
  bool headlights = false;
  bool quiet = false;
};

int usage() {
  std::printf(
      "usage: agent_snapshot --x X --y Y [--runtime DIR] [--out FILE]\n"
      "                     [--heading-deg D] [--hour H] [--dow D] [--seed S]\n"
      "                     [--warmup-s T] [--vehicle-radius M] [--ped-radius M]\n"
      "                     [--max-vehicles N] [--max-peds N]\n"
      "                     [--rain-mm-h R] [--temperature-c T] [--snow-cover S]\n"
      "                     [--headlights] [--quiet]\n");
  return 2;
}

/// JSON string escape (the only text that reaches the output is our own and the network's notes).
std::string esc(const std::string& s) {
  std::string o;
  o.reserve(s.size() + 8);
  for (const char c : s) {
    switch (c) {
      case '"': o += "\\\""; break;
      case '\\': o += "\\\\"; break;
      case '\n': o += "\\n"; break;
      case '\r': o += "\\r"; break;
      case '\t': o += "\\t"; break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          char b[8];
          std::snprintf(b, sizeof b, "\\u%04x", c);
          o += b;
        } else {
          o += c;
        }
    }
  }
  return o;
}

/// What the density table asks for over the lanes the traffic spawner considers, recomputed here
/// from the public road-network API rather than read out of the simulation, so the snapshot can
/// state the target beside the count it reached.
struct DensityTarget {
  double vehicles = 0.0;
  double lane_km = 0.0;
  double ped = 0.0;
  double sidewalk_m2 = 0.0;
  uint32_t lanes = 0;
  uint32_t segments = 0;
  uint32_t lanes_with_nta = 0;
};

DensityTarget densityTargets(const RoadNetwork& net, const Options& o, const TrafficConfig& tcfg,
                             const PedConfig& pcfg) {
  namespace routing = nycsim::routing;
  const routing::RoadGraph& g = net.graph();
  DensityTarget t;

  std::vector<uint32_t> found(8192, 0u);
  const float radius = std::max(tcfg.spawnRadiusM + 80.f, pcfg.spawnRadiusM + 40.f);
  const uint32_t n = std::min<uint32_t>(
      g.lanesNear(static_cast<float>(o.x), static_cast<float>(o.y), radius, found.data(),
                  static_cast<uint32_t>(found.size()), false),
      static_cast<uint32_t>(found.size()));

  std::vector<uint32_t> segs;
  for (uint32_t i = 0; i < n; ++i) {
    const uint32_t li = found[i];
    if (li >= g.laneCount()) continue;
    const routing::Lane& l = g.lane(li);
    if (l.is_junction != 0 || l.segment == routing::kInvalidIndex) continue;
    const routing::Segment& seg = g.segment(l.segment);

    // --- vehicles: the traffic spawner's own lane filter -------------------------------------
    const float dx = g.pointAt(li, 0.5f * l.length_m).x - static_cast<float>(o.x);
    const float dy = g.pointAt(li, 0.5f * l.length_m).y - static_cast<float>(o.y);
    const bool in_veh_ring = (dx * dx + dy * dy) <= (tcfg.spawnRadiusM + 80.f) * (tcfg.spawnRadiusM + 80.f);
    if (in_veh_ring && g.laneAllows(li, routing::kMotorLaneKinds) && l.length_m >= 12.f &&
        (seg.attrs.flags & routing::kSegNoSpawn) == 0 &&
        seg.attrs.rw_type != routing::RwType::NonPhysical && seg.attrs.rw_type != routing::RwType::Ferry &&
        seg.attrs.rw_type != routing::RwType::StepStreet && seg.attrs.rw_type != routing::RwType::Path) {
      const double km = static_cast<double>(l.length_m) / 1000.0;
      const nycsim::traffic::DensityCell& cell =
          net.densityForLane(li, static_cast<uint8_t>(o.hour), static_cast<uint8_t>(o.dow));
      const double per_km = cell.veh_per_km_lane > 0.f ? static_cast<double>(cell.veh_per_km_lane)
                                                       : static_cast<double>(tcfg.fallbackVehPerKmLane);
      t.lane_km += km;
      t.vehicles += km * per_km;
      ++t.lanes;
      if (l.nta != routing::kNoNta) ++t.lanes_with_nta;
    }

    // --- pedestrians: the walker spawner's own segment filter ---------------------------------
    if (seg.attrs.rw_type == routing::RwType::Highway || seg.attrs.rw_type == routing::RwType::Tunnel ||
        seg.attrs.rw_type == routing::RwType::Ferry || seg.attrs.rw_type == routing::RwType::NonPhysical ||
        seg.attrs.rw_type == routing::RwType::Ramp) {
      continue;
    }
    if (std::find(segs.begin(), segs.end(), l.segment) != segs.end()) continue;
    const float sdx = g.pointAt(li, 0.5f * l.length_m).x - static_cast<float>(o.x);
    const float sdy = g.pointAt(li, 0.5f * l.length_m).y - static_cast<float>(o.y);
    if ((sdx * sdx + sdy * sdy) > (pcfg.spawnRadiusM + 40.f) * (pcfg.spawnRadiusM + 40.f)) continue;
    segs.push_back(l.segment);
    const double area = 2.0 * static_cast<double>(seg.length_m) * static_cast<double>(pcfg.sidewalkWidthM);
    uint32_t nl = 0;
    const uint32_t* lanes = g.segmentLanes(l.segment, nl);
    double per_m2 = static_cast<double>(pcfg.fallbackPedPerM2);
    if (nl > 0) {
      const nycsim::traffic::DensityCell& cell =
          net.densityForLane(lanes[0], static_cast<uint8_t>(o.hour), static_cast<uint8_t>(o.dow));
      if (cell.ped_per_m2 > 0.f) per_m2 = static_cast<double>(cell.ped_per_m2);
    }
    t.sidewalk_m2 += area;
    t.ped += area * per_m2;
  }
  t.segments = static_cast<uint32_t>(segs.size());
  return t;
}

}  // namespace

int main(int argc, char** argv) {
  Options o;
  bool have_x = false, have_y = false;
  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    auto nextStr = [&](std::string& out) {
      if (i + 1 >= argc) return false;
      out = argv[++i];
      return true;
    };
    auto nextNum = [&](double& out) {
      if (i + 1 >= argc) return false;
      out = std::strtod(argv[++i], nullptr);
      return true;
    };
    double v = 0.0;
    if (a == "--runtime") { if (!nextStr(o.runtime_dir)) return usage(); }
    else if (a == "--out") { if (!nextStr(o.out)) return usage(); }
    else if (a == "--x") { if (!nextNum(o.x)) return usage(); have_x = true; }
    else if (a == "--y") { if (!nextNum(o.y)) return usage(); have_y = true; }
    else if (a == "--heading-deg") { if (!nextNum(o.heading_deg)) return usage(); }
    else if (a == "--hour") { if (!nextNum(v)) return usage(); o.hour = static_cast<uint32_t>(v); }
    else if (a == "--dow") { if (!nextNum(v)) return usage(); o.dow = static_cast<uint32_t>(v); }
    else if (a == "--seed") { if (!nextNum(v)) return usage(); o.seed = static_cast<uint64_t>(v); }
    else if (a == "--warmup-s") { if (!nextNum(o.warmup_s)) return usage(); }
    else if (a == "--vehicle-radius") { if (!nextNum(o.vehicle_radius_m)) return usage(); }
    else if (a == "--ped-radius") { if (!nextNum(o.ped_radius_m)) return usage(); }
    else if (a == "--max-vehicles") { if (!nextNum(v)) return usage(); o.max_vehicles = static_cast<uint32_t>(v); }
    else if (a == "--max-peds") { if (!nextNum(v)) return usage(); o.max_peds = static_cast<uint32_t>(v); }
    else if (a == "--rain-mm-h") { if (!nextNum(o.rain_mm_h)) return usage(); }
    else if (a == "--temperature-c") { if (!nextNum(o.temperature_c)) return usage(); }
    else if (a == "--snow-cover") { if (!nextNum(o.snow_cover)) return usage(); }
    else if (a == "--headlights") { o.headlights = true; }
    else if (a == "--quiet") { o.quiet = true; }
    else return usage();
  }
  if (!have_x || !have_y) return usage();
  if (o.hour > 23u) o.hour = 23u;
  if (o.dow > 2u) o.dow = 2u;

  RoadNetwork net;
  std::string error;
  if (!net.load(o.runtime_dir, error)) {
    std::fprintf(stderr, "agent_snapshot: road network did not load from %s: %s\n", o.runtime_dir.c_str(),
                 error.c_str());
    return 1;
  }

  TrafficConfig tcfg;
  tcfg.seed = o.seed;
  tcfg.maxVehicles = o.max_vehicles;
  tcfg.spawnRadiusM = static_cast<float>(o.vehicle_radius_m);
  tcfg.despawnRadiusM = static_cast<float>(o.vehicle_radius_m * 1.35);
  tcfg.simRadiusM = static_cast<float>(o.vehicle_radius_m * 1.30);
  // A still frame has no player: nothing is hidden by the protected region, and everything it
  // protects is what the camera is pointing at.  See the header comment.
  tcfg.protectRadiusM = 0.f;
  tcfg.protectConeCos = 2.f;  // dot product can never reach this, so no bearing is protected
  tcfg.hour = static_cast<uint8_t>(o.hour);
  tcfg.dow = static_cast<uint8_t>(o.dow);
  tcfg.wetness = o.rain_mm_h > 0.0 ? 1.f : 0.f;
  tcfg.snowCover = static_cast<float>(o.snow_cover);
  tcfg.headlightsOn = o.headlights;

  PedConfig pcfg;
  pcfg.seed = o.seed;
  pcfg.maxPeds = o.max_peds;
  pcfg.spawnRadiusM = static_cast<float>(o.ped_radius_m);
  pcfg.despawnRadiusM = static_cast<float>(o.ped_radius_m * 1.35);
  pcfg.protectRadiusM = 0.f;
  pcfg.hour = static_cast<uint8_t>(o.hour);
  pcfg.dow = static_cast<uint8_t>(o.dow);
  pcfg.rainRateMmH = static_cast<float>(o.rain_mm_h);
  pcfg.snowCover = static_cast<float>(o.snow_cover);
  pcfg.temperatureC = static_cast<float>(o.temperature_c);

  const DensityTarget target = densityTargets(net, o, tcfg, pcfg);

  TrafficSim traffic;
  PedSim peds;
  if (!traffic.init(net, tcfg, error)) {
    std::fprintf(stderr, "agent_snapshot: traffic init failed: %s\n", error.c_str());
    return 1;
  }
  if (!peds.init(net, pcfg, error)) {
    std::fprintf(stderr, "agent_snapshot: pedestrian init failed: %s\n", error.c_str());
    return 1;
  }

  TrafficObserver obs;
  obs.x = static_cast<float>(o.x);
  obs.y = static_cast<float>(o.y);
  obs.z = 0.f;
  // Compass bearing -> unit vector in NYC_TM (x east, y north).
  const double hr = o.heading_deg * 3.14159265358979323846 / 180.0;
  obs.dirX = static_cast<float>(std::sin(hr));
  obs.dirY = static_cast<float>(std::cos(hr));
  obs.speedMps = 0.f;
  obs.playerVehicleValid = false;

  std::vector<VehicleSnapshot> vehicles;
  std::vector<PedSnapshot> pedSnap;
  std::vector<PedObstacle> obstacles;
  std::vector<TrafficEvent> events;

  const int steps = std::max(1, static_cast<int>(o.warmup_s / static_cast<double>(tcfg.stepSeconds) + 0.5));
  for (int i = 0; i < steps; ++i) {
    traffic.setObserver(obs);
    peds.setObserver(obs);
    peds.updateVehicles(vehicles);
    peds.writeObstacles(obstacles);
    traffic.setPedObstacles(obstacles);
    traffic.step();
    peds.step();
    traffic.writeSnapshot(vehicles);
    peds.writeSnapshot(pedSnap);
    traffic.drainEvents(events);
    if (!o.quiet && (i + 1) % 400 == 0) {
      std::fprintf(stderr, "  step %d/%d  %zu vehicles, %zu pedestrians\n", i + 1, steps, vehicles.size(),
                   pedSnap.size());
    }
  }

  const TrafficStats& ts = traffic.stats();
  const PedStats& ps = peds.stats();
  const RoadNetworkStats& ns = net.stats();

  std::string out;
  out.reserve(vehicles.size() * 160 + pedSnap.size() * 120 + 4096);
  char b[1024];
  auto add = [&](const char* fmt, auto... args) {
    std::snprintf(b, sizeof b, fmt, args...);
    out += b;
  };

  out += "{\n";
  out += " \"schema\": \"nycsim.verify.agent_snapshot.v1\",\n";
  out +=
      " \"produced_by\": \"blender/verify/agent_snapshot.cpp — nycsim_gameplay::TrafficSim and "
      "nycsim_gameplay::PedSim (unreal/NYCSim/Source/NYCSimRuntime/Private/CoreAdapter), the same "
      "simulations the Unreal traffic subsystem steps, over the shipped road graph\",\n";
  out += " \"snapshot_records\": \"VehicleSnapshot / PedSnapshot, the structs UNYCTrafficSubsystem "
         "reads from FNYCSimSnapshot\",\n";
  add(" \"runtime_dir\": \"%s\",\n", esc(o.runtime_dir).c_str());
  add(" \"synthetic_network\": %s,\n", net.isSynthetic() ? "true" : "false");
  out += " \"network\": {";
  add("\"nodes\": %u, \"segments\": %u, \"road_lanes\": %u, \"junction_lanes\": %u, ", ns.nodes, ns.segments,
      ns.roadLanes, ns.junctionLanes);
  add("\"signal_plans\": %u, \"nta_cells\": %u, \"lanes_with_nta\": %u, \"load_seconds\": %.2f",
      ns.signalPlans, ns.ntaCells, ns.lanesWithNta, ns.loadSeconds);
  out += "},\n";
  out += " \"network_notes\": [";
  for (size_t i = 0; i < net.notes().size(); ++i) {
    if (i) out += ", ";
    out += "\"" + esc(net.notes()[i]) + "\"";
  }
  out += "],\n";
  out += " \"observer\": {";
  add("\"x\": %.3f, \"y\": %.3f, \"heading_deg\": %.2f, \"moving\": false", o.x, o.y, o.heading_deg);
  out += "},\n";
  add(" \"seed\": %llu,\n", static_cast<unsigned long long>(o.seed));
  add(" \"hour\": %u,\n", o.hour);
  add(" \"dow\": %u,\n", o.dow);
  add(" \"step_seconds\": %.4f,\n", static_cast<double>(tcfg.stepSeconds));
  add(" \"steps\": %d,\n", steps);
  add(" \"sim_seconds\": %.2f,\n", traffic.simTime());
  out += " \"config\": {\n";
  add("  \"vehicle_spawn_radius_m\": %.1f, \"vehicle_despawn_radius_m\": %.1f, \"max_vehicles\": %u,\n",
      static_cast<double>(tcfg.spawnRadiusM), static_cast<double>(tcfg.despawnRadiusM), tcfg.maxVehicles);
  add("  \"ped_spawn_radius_m\": %.1f, \"ped_despawn_radius_m\": %.1f, \"max_peds\": %u,\n",
      static_cast<double>(pcfg.spawnRadiusM), static_cast<double>(pcfg.despawnRadiusM), pcfg.maxPeds);
  add("  \"rain_mm_h\": %.2f, \"temperature_c\": %.1f, \"snow_cover\": %.2f, \"headlights\": %s,\n",
      o.rain_mm_h, o.temperature_c, o.snow_cover, o.headlights ? "true" : "false");
  out +=
      "  \"protected_region\": \"disabled (radius 0, no cone): the gameplay rule that stops agents "
      "appearing in view of a moving player would otherwise leave the whole foreground empty of "
      "spawns, and a still frame has no player\"\n";
  out += " },\n";
  out += " \"density_target\": {";
  add("\"vehicles\": %.1f, \"lane_km\": %.3f, \"lanes\": %u, \"lanes_with_nta\": %u, ", target.vehicles,
      target.lane_km, target.lanes, target.lanes_with_nta);
  add("\"pedestrians\": %.1f, \"sidewalk_m2\": %.0f, \"segments\": %u", target.ped, target.sidewalk_m2,
      target.segments);
  out += "},\n";
  out += " \"traffic_stats\": {";
  add("\"vehicles\": %u, \"spawned\": %u, \"despawned\": %u, \"spawn_failures\": %u, ", ts.vehicles,
      ts.spawnedTotal, ts.despawnedTotal, ts.spawnFailures);
  add("\"lane_changes\": %u, \"honks\": %u, \"stopped_at_signals\": %u, \"double_parked\": %u, ",
      ts.laneChanges, ts.honks, ts.stoppedAtSignals, ts.doubleParked);
  add("\"buses_dwelling\": %u, \"red_light_entries\": %u, \"dilemma_zone_entries\": %u, ", ts.busesDwelling,
      ts.redLightEntries, ts.dilemmaZoneEntries);
  add("\"min_leader_gap_m\": %.4f, \"avg_step_ms\": %.4f", static_cast<double>(ts.minLeaderGapM), ts.avgStepMs);
  out += "},\n";
  out += " \"ped_stats\": {";
  add("\"peds\": %u, \"spawned\": %u, \"despawned\": %u, \"crossing\": %u, \"waiting\": %u, ", ps.peds,
      ps.spawnedTotal, ps.despawnedTotal, ps.crossing, ps.waiting);
  add("\"jaywalking\": %u, \"unsafe_crossing_starts\": %u, \"avg_step_ms\": %.4f", ps.jaywalking,
      ps.unsafeCrossingStarts, ps.avgStepMs);
  out += "},\n";

  out += " \"vehicle_classes\": [";
  for (uint8_t c = 0; c < vehicleClassCount(); ++c) {
    const VehicleClassInfo info = vehicleClassInfo(c);
    if (c) out += ", ";
    add("{\"index\": %u, \"name\": \"%s\", \"body\": \"%s\", \"length_m\": %.3f, \"width_m\": %.3f, "
        "\"height_m\": %.3f}",
        static_cast<unsigned>(c), esc(info.name).c_str(), esc(info.body).c_str(),
        static_cast<double>(info.lengthM), static_cast<double>(info.widthM),
        static_cast<double>(info.heightM));
  }
  out += "],\n";

  add(" \"vehicle_count\": %zu,\n", vehicles.size());
  out += " \"vehicles\": [\n";
  for (size_t i = 0; i < vehicles.size(); ++i) {
    const VehicleSnapshot& v = vehicles[i];
    add("  {\"id\": %u, \"cls\": %u, \"flags\": %u, \"x\": %.3f, \"y\": %.3f, \"z\": %.3f, "
        "\"heading_rad\": %.5f, \"speed_mps\": %.3f, \"accel_mps2\": %.3f, \"steer_rad\": %.4f, "
        "\"length_m\": %.3f, \"width_m\": %.3f, \"honking\": %u}%s\n",
        v.id, static_cast<unsigned>(v.cls), static_cast<unsigned>(v.flags), static_cast<double>(v.x),
        static_cast<double>(v.y), static_cast<double>(v.z), static_cast<double>(v.headingRad),
        static_cast<double>(v.speedMps), static_cast<double>(v.accelMps2), static_cast<double>(v.steerRad),
        static_cast<double>(v.lengthM), static_cast<double>(v.widthM), static_cast<unsigned>(v.honking),
        i + 1 < vehicles.size() ? "," : "");
  }
  out += " ],\n";

  add(" \"ped_count\": %zu,\n", pedSnap.size());
  out += " \"pedestrians\": [\n";
  for (size_t i = 0; i < pedSnap.size(); ++i) {
    const PedSnapshot& p = pedSnap[i];
    add("  {\"id\": %u, \"x\": %.3f, \"y\": %.3f, \"z\": %.3f, \"heading_rad\": %.5f, "
        "\"speed_mps\": %.3f, \"state\": %u, \"archetype\": %u, \"variant\": %u, \"flags\": %u}%s\n",
        p.id, static_cast<double>(p.x), static_cast<double>(p.y), static_cast<double>(p.z),
        static_cast<double>(p.headingRad), static_cast<double>(p.speedMps), static_cast<unsigned>(p.state),
        static_cast<unsigned>(p.archetype), static_cast<unsigned>(p.variant), static_cast<unsigned>(p.flags),
        i + 1 < pedSnap.size() ? "," : "");
  }
  out += " ]\n}\n";

  if (o.out.empty() || o.out == "-") {
    std::fwrite(out.data(), 1, out.size(), stdout);
  } else {
    FILE* f = std::fopen(o.out.c_str(), "wb");
    if (f == nullptr) {
      std::fprintf(stderr, "agent_snapshot: cannot write %s\n", o.out.c_str());
      return 1;
    }
    std::fwrite(out.data(), 1, out.size(), f);
    std::fclose(f);
  }
  if (!o.quiet) {
    std::fprintf(stderr,
                 "agent_snapshot: %zu vehicles (density target %.0f), %zu pedestrians (target %.0f) "
                 "after %.0f s at seed %llu\n",
                 vehicles.size(), target.vehicles, pedSnap.size(), target.ped, traffic.simTime(),
                 static_cast<unsigned long long>(o.seed));
  }
  return 0;
}
