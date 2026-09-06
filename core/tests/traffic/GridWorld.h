#pragma once
// Shared fixture for the traffic / routing / pedestrian suites: a synthetic
// Midtown grid with signals, a calibration table and (optionally) an attached
// router.  Kept header-only so every suite that needs it can include it.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/peds/SidewalkGraph.h"
#include "nycsim/routing/RoadGraph.h"
#include "nycsim/routing/Router.h"
#include "nycsim/traffic/Density.h"
#include "nycsim/traffic/Signals.h"
#include "nycsim/traffic/SyntheticGrid.h"
#include "nycsim/traffic/TrafficSim.h"

namespace nycsim_test {

struct GridWorld {
  nycsim::routing::RoadGraph graph;
  nycsim::traffic::SignalTable signals;
  nycsim::traffic::DensityTable density;
  nycsim::routing::Router router;
  nycsim::peds::SidewalkGraph walk;
  std::string error;

  bool build(const nycsim::traffic::SyntheticGridSpec& spec, float veh_per_km_lane = 0.f,
             float ped_per_m2 = 0.f, bool attach_router = false, bool build_sidewalks = false) {
    if (!nycsim::traffic::SyntheticGrid::build(spec, graph, signals, &error)) return false;
    const uint16_t nta = density.addNta("MN17");  // Midtown-South NTA code
    nycsim::traffic::DensityCell cell;
    cell.veh_per_km_lane = veh_per_km_lane;
    cell.ped_per_m2 = ped_per_m2;
    cell.taxi_share = 0.15f;
    cell.truck_share = 0.08f;
    cell.bus_share = 0.02f;
    cell.bike_share = 0.05f;
    density.fill(nta, cell);
    if (attach_router && !router.attach(graph, 4, 7)) {
      error = router.lastError();
      return false;
    }
    if (build_sidewalks) {
      nycsim::peds::SidewalkBuildParams wp;
      if (!walk.buildFromRoadGraph(graph, &signals, wp)) {
        error = walk.lastError();
        return false;
      }
    }
    return true;
  }
};

// Oriented-box overlap (separating axis) between two vehicles, with each box
// scaled by `shrink` so that a mirror-touching pair is not reported.
inline bool boxesOverlap(const nycsim::traffic::Vehicle& a, const nycsim::traffic::Vehicle& b, float shrink) {
  const float ax = std::cos(a.heading_rad), ay = std::sin(a.heading_rad);
  const float bx = std::cos(b.heading_rad), by = std::sin(b.heading_rad);
  const float ahl = a.length_m * 0.5f * shrink, ahw = a.width_m * 0.5f * shrink;
  const float bhl = b.length_m * 0.5f * shrink, bhw = b.width_m * 0.5f * shrink;
  const float dx = b.pos.x - a.pos.x, dy = b.pos.y - a.pos.y;
  const float axes[4][2] = {{ax, ay}, {-ay, ax}, {bx, by}, {-by, bx}};
  for (int i = 0; i < 4; ++i) {
    const float nx = axes[i][0], ny = axes[i][1];
    const float ra = ahl * std::fabs(ax * nx + ay * ny) + ahw * std::fabs(-ay * nx + ax * ny);
    const float rb = bhl * std::fabs(bx * nx + by * ny) + bhw * std::fabs(-by * nx + bx * ny);
    if (std::fabs(dx * nx + dy * ny) > ra + rb) return false;
  }
  return true;
}

// Counts overlapping vehicle pairs with a uniform grid: each vehicle is tested
// against its own cell and the four forward neighbours, so every pair is seen
// exactly once.  (The O(n²) version is far too slow for a ten-minute run.)
inline uint32_t countCollisions(const nycsim::traffic::TrafficSim& sim, float shrink = 0.90f) {
  const size_t n = sim.vehicleCount();
  if (n < 2) return 0;
  const float cell = 20.f;
  float minx = 1e30f, miny = 1e30f, maxx = -1e30f;
  for (size_t i = 0; i < n; ++i) {
    const nycsim::traffic::Vehicle& v = sim.vehicle(i);
    minx = std::min(minx, v.pos.x);
    miny = std::min(miny, v.pos.y);
    maxx = std::max(maxx, v.pos.x);
  }
  const uint64_t nx = static_cast<uint64_t>((maxx - minx) / cell) + 2u;
  std::vector<uint64_t> keys(n);
  for (size_t i = 0; i < n; ++i) {
    const nycsim::traffic::Vehicle& v = sim.vehicle(i);
    const uint64_t cx = static_cast<uint64_t>((v.pos.x - minx) / cell);
    const uint64_t cy = static_cast<uint64_t>((v.pos.y - miny) / cell);
    keys[i] = ((cy * nx + cx) << 20) | static_cast<uint64_t>(i);
  }
  std::sort(keys.begin(), keys.end());
  auto cellRange = [&](uint64_t c, size_t& b, size_t& e) {
    const auto lo = std::lower_bound(keys.begin(), keys.end(), c << 20);
    const auto hi = std::lower_bound(keys.begin(), keys.end(), (c + 1u) << 20);
    b = static_cast<size_t>(lo - keys.begin());
    e = static_cast<size_t>(hi - keys.begin());
  };
  uint32_t hits = 0;
  for (size_t k = 0; k < n; ++k) {
    const uint64_t c = keys[k] >> 20;
    const size_t ia = static_cast<size_t>(keys[k] & 0xFFFFFull);
    const nycsim::traffic::Vehicle& a = sim.vehicle(ia);
    const uint64_t cy = c / nx, cx = c % nx;
    const uint64_t neigh[5] = {c, c + 1u, (cy + 1u) * nx + cx, (cy + 1u) * nx + cx + 1u,
                               cx > 0 ? (cy + 1u) * nx + cx - 1u : c};
    for (int nb = 0; nb < 5; ++nb) {
      if (nb == 4 && cx == 0) continue;
      size_t b = 0, e = 0;
      cellRange(neigh[nb], b, e);
      for (size_t j = b; j < e; ++j) {
        const size_t ib = static_cast<size_t>(keys[j] & 0xFFFFFull);
        if (nb == 0 && ib <= ia) continue;   // same cell: each pair once
        if (ib == ia) continue;
        const nycsim::traffic::Vehicle& bv = sim.vehicle(ib);
        const float dx = bv.pos.x - a.pos.x, dy = bv.pos.y - a.pos.y;
        const float reach = (a.length_m + bv.length_m) * 0.5f;
        if (dx * dx + dy * dy > reach * reach) continue;
        if (boxesOverlap(a, bv, shrink)) ++hits;
      }
    }
  }
  return hits;
}

}  // namespace nycsim_test
