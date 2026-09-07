// core/bench/bench_signals.cpp — SignalTable::cacheStates on the real table.
//
// cacheStates is O(refreshed plans x kMaxCachedGroups).  On the synthetic
// Midtown grid that is a few thousand operations a step; on the real table it is
// 19,814 x 8 = 158,512, every step, for the whole city, when only the streamed
// region can possibly be looked at.  This measures the whole-table cost, the
// windowed cost, and checks that the two produce the same signal states.
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

int runSignals(Args& args) {
  std::string runtime = defaultRuntimeDir();
  uint32_t steps = 2000;
  double window = 3000.0;
  args.text("--runtime", runtime);
  args.integer("--steps", steps);
  args.number("--window", window);
  if (!args.ok()) return args.fail();

  std::printf("nycsim_bench signals\n");
  printLoad("before");
  World w;
  std::string err;
  if (!w.loadCity(runtime, err)) {
    std::fprintf(stderr, "%s\n", err.c_str());
    return 1;
  }
  const size_t plans = w.signals.planCount();
  std::printf("  table            %zu plans bound to %zu graph nodes\n", plans, w.sizes().nodes);
  if (plans == 0) {
    std::fprintf(stderr, "signal table is empty\n");
    return 1;
  }

  // Centre the window where the plans are densest, which is where a player
  // would be: the busiest 1 km cell of the plan grid.
  float minx = 1e30f, miny = 1e30f, maxx = -1e30f, maxy = -1e30f;
  std::vector<float> px, py;
  px.reserve(plans);
  py.reserve(plans);
  for (uint32_t i = 0; i < plans; ++i) {
    const uint32_t ni = w.signals.plan(i).node_index;
    if (ni == routing::kInvalidIndex) continue;
    const routing::Vec3& p = w.graph.node(ni).pos;
    px.push_back(p.x);
    py.push_back(p.y);
    minx = std::min(minx, p.x);
    miny = std::min(miny, p.y);
    maxx = std::max(maxx, p.x);
    maxy = std::max(maxy, p.y);
  }
  if (px.empty()) {
    std::fprintf(stderr, "no plan is bound to a graph node\n");
    return 1;
  }
  const float cell = 1000.f;
  const uint32_t gnx = static_cast<uint32_t>((maxx - minx) / cell) + 1u;
  const uint32_t gny = static_cast<uint32_t>((maxy - miny) / cell) + 1u;
  std::vector<uint32_t> hist(static_cast<size_t>(gnx) * gny, 0u);
  for (size_t i = 0; i < px.size(); ++i) {
    const uint32_t cx = static_cast<uint32_t>((px[i] - minx) / cell);
    const uint32_t cy = static_cast<uint32_t>((py[i] - miny) / cell);
    ++hist[static_cast<size_t>(std::min(cy, gny - 1u)) * gnx + std::min(cx, gnx - 1u)];
  }
  size_t best = 0;
  for (size_t i = 1; i < hist.size(); ++i)
    if (hist[i] > hist[best]) best = i;
  const float cx0 = minx + (static_cast<float>(best % gnx) + 0.5f) * cell;
  const float cy0 = miny + (static_cast<float>(best / gnx) + 0.5f) * cell;
  std::printf("  plan extent      %.0f x %.0f km; densest 1 km cell holds %u plans at (%.0f, %.0f)\n",
              static_cast<double>(maxx - minx) / 1000.0, static_cast<double>(maxy - miny) / 1000.0,
              hist[best], static_cast<double>(cx0), static_cast<double>(cy0));

  // ---- whole table -----------------------------------------------------
  w.signals.clearActiveWindow();
  std::vector<double> full_ms;
  full_ms.reserve(steps);
  Stopwatch sw;
  double t = 0.0;
  for (uint32_t i = 0; i < steps; ++i) {
    t += 0.05;
    double wall = 0, cpu = 0;
    sw.reset();
    w.signals.cacheStates(t);
    sw.lap(wall, cpu);
    full_ms.push_back(cpu);
  }
  const uint32_t full_plans = w.signals.cachedPlanCount();
  // Record the states of every plan so the windowed run can be compared.
  std::vector<uint8_t> reference(plans * 2u, 0u);
  for (uint32_t i = 0; i < plans; ++i) {
    reference[i * 2u] = static_cast<uint8_t>(w.signals.cachedVehicleState(i, 0));
    reference[i * 2u + 1u] = static_cast<uint8_t>(w.signals.cachedPedState(i, 0));
  }

  // ---- windowed --------------------------------------------------------
  const float h = static_cast<float>(window) * 0.5f;
  w.signals.setActiveWindow(cx0 - h, cy0 - h, cx0 + h, cy0 + h);
  std::vector<double> win_ms;
  win_ms.reserve(steps);
  double t2 = 0.0;
  for (uint32_t i = 0; i < steps; ++i) {
    t2 += 0.05;
    double wall = 0, cpu = 0;
    sw.reset();
    w.signals.setActiveWindow(cx0 - h, cy0 - h, cx0 + h, cy0 + h);
    w.signals.cacheStates(t2);
    sw.lap(wall, cpu);
    win_ms.push_back(cpu);
  }
  const uint32_t win_plans = w.signals.cachedPlanCount();

  // The window must not change what anybody reads: a plan outside it is not
  // memoized, and the accessor computes it instead.
  uint32_t mismatches = 0;
  for (uint32_t i = 0; i < plans; ++i) {
    if (reference[i * 2u] != static_cast<uint8_t>(w.signals.cachedVehicleState(i, 0))) ++mismatches;
    if (reference[i * 2u + 1u] != static_cast<uint8_t>(w.signals.cachedPedState(i, 0))) ++mismatches;
  }

  const Dist f = distribution(full_ms);
  const Dist g = distribution(win_ms);
  std::printf("  whole table      %u plans refreshed per step\n", full_plans);
  printDist("full (CPU ms)", f);
  std::printf("  window %.0f m     %u plans refreshed per step (%.1f %% of the table)\n", window,
              win_plans, 100.0 * static_cast<double>(win_plans) / static_cast<double>(plans));
  printDist("window (CPU ms)", g);
  std::printf("  speed-up         %.1fx  (%.4f ms saved per step, %.2f %% of an 8 ms budget)\n",
              g.mean > 1e-9 ? f.mean / g.mean : 0.0, f.mean - g.mean, (f.mean - g.mean) / 8.0 * 100.0);
  std::printf("  agreement        %u of %zu plan states differ between the two modes%s\n", mismatches,
              plans * 2u, mismatches == 0 ? " — none, the window is transparent" : "");
  printLoad("after");
  return mismatches == 0 ? 0 : 1;
}

}  // namespace nycbench
