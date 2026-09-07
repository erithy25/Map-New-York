// core/bench/nycsim_bench — the performance and robustness measurements for
// docs/verification/performance/REPORT.md.
//
//   nycsim_bench synthetic   14 x 28 Midtown grid, 5,000 vehicles + 20,000
//                            pedestrians, wall AND thread-CPU time per step
//   nycsim_bench city        the real artefacts under data/processed/runtime
//   nycsim_bench soak        >= 30 simulated minutes with spawn/despawn churn,
//                            sampling the resident set size and fitting a slope
//   nycsim_bench signals     SignalTable::cacheStates on the real 19,814-plan
//                            table, whole table vs. streamed window
//   nycsim_bench stream      TileScheduler driven along the Fordham Road ->
//                            Hylan Boulevard route at highway speed
//
// Every command prints the load average before and after, because four vCPUs
// are shared with other agents and a wall-clock number without it is not a
// measurement.
#include <cstdio>
#include <cstring>
#include <string>

#include "bench_options.h"

namespace {

int usage() {
  std::printf(
      "usage: nycsim_bench <command> [options]\n"
      "\n"
      "  synthetic  [--vehicles N] [--peds N] [--steps N] [--warmup N]\n"
      "             [--avenues N] [--streets N] [--seed N] [--no-peds] [--csv FILE]\n"
      "  city       [--runtime DIR] [--vehicles N] [--peds N] [--steps N] [--warmup N]\n"
      "             [--seed N] [--no-peds] [--no-sidewalks] [--signal-window M]\n"
      "             [--hash-cell M] [--csv FILE]\n"
      "  soak       [--minutes M] [--vehicles N] [--peds N] [--sample-steps N] [--csv FILE]\n"
      "             [--city] [--runtime DIR]\n"
      "  signals    [--runtime DIR] [--steps N] [--window M]\n"
      "  stream     [--runtime DIR] [--terrain-dir DIR] [--building-dir DIR]\n"
      "             [--from-node ID] [--to-node ID] [--speed KMH] [--budget-gb G] [--csv FILE]\n");
  return 2;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return usage();
  const std::string cmd = argv[1];
  nycbench::Args args(argc - 2, argv + 2);
  if (cmd == "synthetic") return nycbench::runSynthetic(args);
  if (cmd == "city") return nycbench::runCity(args);
  if (cmd == "soak") return nycbench::runSoak(args);
  if (cmd == "signals") return nycbench::runSignals(args);
  if (cmd == "stream") return nycbench::runStream(args);
  std::fprintf(stderr, "unknown command '%s'\n", cmd.c_str());
  return usage();
}
