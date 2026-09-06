#pragma once
// core/bench/bench_world.h — the two worlds the performance benchmarks run in.
//
//   SyntheticWorld — the 14 x 28 Midtown grid the traffic lane calibrated on,
//                    kept identical to core/traffic_standalone/bench_main.cpp so
//                    the two sets of numbers are comparable.
//   CityWorld      — the real artefacts under data/processed/runtime:
//                    roadgraph.nycb, signals.nycb, density.nycb, transit.nycb.
//
// Both own their graph, signal table, router and sidewalk graph, and hand out
// a configured TrafficSim / PedSim.  Loading is fallible and never throws: every
// entry point returns false and fills `error`.

#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/peds/PedSim.h"
#include "nycsim/peds/SidewalkGraph.h"
#include "nycsim/routing/RoadGraph.h"
#include "nycsim/routing/Router.h"
#include "nycsim/traffic/BusRoutes.h"
#include "nycsim/traffic/Density.h"
#include "nycsim/traffic/Signals.h"
#include "nycsim/traffic/SyntheticGrid.h"
#include "nycsim/traffic/TrafficSim.h"

namespace nycbench {

/// Timings of the one-off construction work, milliseconds.
struct BuildTimes {
  double read_ms = 0;
  double graph_ms = 0;
  double signals_ms = 0;
  double density_ms = 0;
  double transit_ms = 0;
  double router_ms = 0;
  double sidewalk_ms = 0;
  double traffic_cfg_ms = 0;
  double ped_cfg_ms = 0;
  double prefill_ms = 0;
};

struct WorldSizes {
  size_t nodes = 0, segments = 0, lanes = 0, junction_lanes = 0;
  size_t signal_plans = 0, density_cells = 0, bus_routes = 0;
  size_t walk_nodes = 0, walk_edges = 0, walk_pois = 0, walk_walls = 0;
  double lane_km = 0.0;
  double sidewalk_m2 = 0.0;
};

/// Shared state of a benchmark world.  Non-copyable: the simulations hold
/// pointers into it.
class World {
 public:
  World() = default;
  World(const World&) = delete;
  World& operator=(const World&) = delete;

  /// Builds the 14 x 28 synthetic grid.
  bool buildSynthetic(int avenues, int streets, std::string& error);

  /// Loads the real city.  `runtime_dir` is the directory holding
  /// roadgraph.nycb / signals.nycb / density.nycb / transit.nycb.
  bool loadCity(const std::string& runtime_dir, std::string& error);

  /// Derives the sidewalk network from the lane graph (needed for pedestrians).
  bool buildSidewalks(std::string& error);

  /// Attaches the ALT router (`landmarks` 0 = plain bidirectional Dijkstra).
  bool attachRouter(uint32_t landmarks, uint64_t seed, std::string& error);

  /// Overwrites the density table with a single synthetic cell sized so the
  /// spawner holds `vehicles` vehicles and `peds` pedestrians.  Used by the
  /// synthetic benchmark, where the real NTA table does not apply.
  void setUniformDensity(uint32_t vehicles, uint32_t peds);

  const WorldSizes& sizes() const { return sizes_; }
  const BuildTimes& times() const { return times_; }
  BuildTimes& times() { return times_; }

  nycsim::routing::RoadGraph graph;
  nycsim::traffic::SignalTable signals;
  nycsim::traffic::DensityTable density;
  nycsim::traffic::BusRouteTable buses;
  nycsim::routing::Router router;
  nycsim::peds::SidewalkGraph walk;

  bool has_transit = false;
  uint16_t uniform_nta = 0xFFFFu;

 private:
  void measure();
  WorldSizes sizes_;
  BuildTimes times_;
};

/// Default location of the runtime artefacts relative to the repository root.
const char* defaultRuntimeDir();

}  // namespace nycbench
