#include "bench_world.h"

#include <algorithm>
#include <cmath>

#include "bench_common.h"

namespace nycbench {

using namespace nycsim;

const char* defaultRuntimeDir() { return "data/processed/runtime"; }

void World::measure() {
  sizes_.nodes = graph.nodeCount();
  sizes_.segments = graph.segmentCount();
  sizes_.lanes = graph.laneCount();
  sizes_.junction_lanes = graph.junctionLaneCount();
  sizes_.signal_plans = signals.planCount();
  sizes_.bus_routes = buses.routeCount();
  double km = 0.0;
  for (uint32_t li = 0; li < graph.laneCount(); ++li) {
    const routing::Lane& l = graph.lane(li);
    if (l.is_junction == 0 &&
        (l.kind == routing::LaneKind::Travel || l.kind == routing::LaneKind::Bus))
      km += static_cast<double>(l.length_m) * 0.001;
  }
  sizes_.lane_km = km;
}

bool World::buildSynthetic(int avenues, int streets, std::string& error) {
  Stopwatch sw;
  traffic::SyntheticGridSpec spec;
  spec.avenues = avenues;
  spec.streets = streets;
  spec.bike_lane_every = 3;
  spec.commercial_avenues = true;
  if (!traffic::SyntheticGrid::build(spec, graph, signals, &error)) return false;
  times_.graph_ms = sw.lapWallMs();
  measure();
  return true;
}

bool World::loadCity(const std::string& runtime_dir, std::string& error) {
  std::vector<uint8_t> buf;
  Stopwatch sw;

  const std::string rg = runtime_dir + "/roadgraph.nycb";
  if (!readFile(rg.c_str(), buf)) {
    error = "cannot read " + rg;
    return false;
  }
  times_.read_ms += sw.lapWallMs();
  if (!graph.loadFromNycb(buf.data(), buf.size())) {
    error = "roadgraph.nycb: " + graph.lastError();
    return false;
  }
  times_.graph_ms = sw.lapWallMs();
  buf.clear();
  buf.shrink_to_fit();

  const std::string sg = runtime_dir + "/signals.nycb";
  if (!readFile(sg.c_str(), buf)) {
    error = "cannot read " + sg;
    return false;
  }
  times_.read_ms += sw.lapWallMs();
  if (!signals.loadFromNycb(buf.data(), buf.size())) {
    error = "signals.nycb: " + signals.lastError();
    return false;
  }
  // bind() reports unknown nodes through lastError() but still succeeds; that
  // is information, not a failure, so it is surfaced by the caller.
  signals.bind(graph);
  times_.signals_ms = sw.lapWallMs();

  const std::string dn = runtime_dir + "/density.nycb";
  if (readFile(dn.c_str(), buf)) {
    if (!density.loadFromNycb(buf.data(), buf.size())) {
      error = "density.nycb: rejected by DensityTable::loadFromNycb";
      return false;
    }
    sizes_.density_cells = density.polygonCount();
  } else {
    error = "cannot read " + dn;
    return false;
  }
  times_.density_ms = sw.lapWallMs();

  const std::string tn = runtime_dir + "/transit.nycb";
  if (readFile(tn.c_str(), buf)) {
    has_transit = buses.loadFromNycb(buf.data(), buf.size(), graph);
    if (!has_transit) {
      error = "transit.nycb: rejected by BusRouteTable::loadFromNycb";
      return false;
    }
  } else {
    error = "cannot read " + tn;
    return false;
  }
  times_.transit_ms = sw.lapWallMs();

  measure();
  return true;
}

bool World::buildSidewalks(std::string& error) {
  Stopwatch sw;
  peds::SidewalkBuildParams wp;
  if (!walk.buildFromRoadGraph(graph, &signals, wp)) {
    error = "sidewalk build failed: " + walk.lastError();
    return false;
  }
  times_.sidewalk_ms = sw.lapWallMs();
  sizes_.walk_nodes = walk.nodeCount();
  sizes_.walk_edges = walk.edgeCount();
  sizes_.walk_pois = walk.poiCount();
  sizes_.walk_walls = walk.wallCount();
  double area = 0.0;
  for (uint32_t e = 0; e < walk.edgeCount(); ++e) {
    const peds::WalkEdge& ed = walk.edge(e);
    if (ed.kind != peds::WalkEdgeKind::Crosswalk)
      area += static_cast<double>(ed.length_m) * static_cast<double>(ed.width_m);
  }
  sizes_.sidewalk_m2 = area;
  return true;
}

bool World::attachRouter(uint32_t landmarks, uint64_t seed, std::string& error) {
  Stopwatch sw;
  if (!router.attach(graph, landmarks, seed)) {
    error = "router attach failed: " + router.lastError();
    return false;
  }
  times_.router_ms = sw.lapWallMs();
  return true;
}

void World::setUniformDensity(uint32_t vehicles, uint32_t peds_wanted) {
  uniform_nta = density.addNta("BENCH");
  traffic::DensityCell cell;
  cell.veh_per_km_lane = sizes_.lane_km > 1.0
                             ? static_cast<float>(static_cast<double>(vehicles) / sizes_.lane_km)
                             : 20.f;
  cell.ped_per_m2 = sizes_.sidewalk_m2 > 1.0
                        ? static_cast<float>(static_cast<double>(peds_wanted) / sizes_.sidewalk_m2)
                        : 0.02f;
  cell.taxi_share = 0.15f;
  cell.truck_share = 0.08f;
  cell.bus_share = 0.02f;
  cell.bike_share = 0.05f;
  density.fill(uniform_nta, cell);
}

}  // namespace nycbench
