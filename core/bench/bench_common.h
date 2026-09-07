#pragma once
// core/bench/bench_common.h — measurement primitives shared by the performance
// benchmarks (docs/verification/performance/REPORT.md).
//
// Three things the traffic lane's own benchmark does not do and that this stage
// needs:
//
//   1. Wall time AND thread CPU time per step.  Four vCPUs are shared with
//      other agents, so a wall-clock mean folds the simulation's own cost
//      together with the time the scheduler took the thread away.  CPU time is
//      the part that is ours; (wall - cpu) is the contention.
//   2. Resident set size sampling, for the memory-bounded soak run.
//   3. Load average at the start and end of every measurement, recorded in the
//      output so two runs can be compared honestly.
//
// Header-only, no exceptions, C++17.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#include <unistd.h>  // sysconf, for the page size in residentBytes()

namespace nycbench {

// ---------------------------------------------------------------- timing
inline double wallSeconds() {
  timespec ts{};
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return static_cast<double>(ts.tv_sec) + static_cast<double>(ts.tv_nsec) * 1e-9;
}

/// CPU time consumed by the calling thread.  Excludes time the thread spent
/// off-CPU, which is exactly the contention this machine has.
inline double threadCpuSeconds() {
  timespec ts{};
  clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
  return static_cast<double>(ts.tv_sec) + static_cast<double>(ts.tv_nsec) * 1e-9;
}

/// Paired wall/CPU stopwatch.  `lap()` returns milliseconds of each.
class Stopwatch {
 public:
  Stopwatch() { reset(); }
  void reset() {
    w0_ = wallSeconds();
    c0_ = threadCpuSeconds();
  }
  void lap(double& wall_ms, double& cpu_ms) {
    const double w = wallSeconds(), c = threadCpuSeconds();
    wall_ms = (w - w0_) * 1000.0;
    cpu_ms = (c - c0_) * 1000.0;
    w0_ = w;
    c0_ = c;
  }
  double lapWallMs() {
    double w = 0, c = 0;
    lap(w, c);
    return w;
  }

 private:
  double w0_ = 0, c0_ = 0;
};

// ------------------------------------------------------------ statistics
struct Dist {
  double mean = 0, p50 = 0, p95 = 0, p99 = 0, max = 0, min = 0;
  size_t n = 0;
};

/// Sorts `v` in place.
inline Dist distribution(std::vector<double>& v) {
  Dist d;
  d.n = v.size();
  if (v.empty()) return d;
  double sum = 0;
  for (double x : v) sum += x;
  d.mean = sum / static_cast<double>(v.size());
  std::sort(v.begin(), v.end());
  auto at = [&](double p) {
    const size_t k = static_cast<size_t>(p * static_cast<double>(v.size() - 1) + 0.5);
    return v[std::min(k, v.size() - 1)];
  };
  d.min = v.front();
  d.p50 = at(0.50);
  d.p95 = at(0.95);
  d.p99 = at(0.99);
  d.max = v.back();
  return d;
}

inline void printDist(const char* label, Dist d) {
  std::printf("  %-16s mean %8.3f  p50 %8.3f  p95 %8.3f  p99 %8.3f  max %8.3f  (n=%zu)\n", label, d.mean,
              d.p50, d.p95, d.p99, d.max, d.n);
}

/// Least-squares slope of y against x (units of y per unit of x).  Returns 0
/// when fewer than two distinct samples.
inline double slope(const std::vector<double>& x, const std::vector<double>& y) {
  const size_t n = std::min(x.size(), y.size());
  if (n < 2) return 0.0;
  double sx = 0, sy = 0;
  for (size_t i = 0; i < n; ++i) {
    sx += x[i];
    sy += y[i];
  }
  const double mx = sx / static_cast<double>(n), my = sy / static_cast<double>(n);
  double num = 0, den = 0;
  for (size_t i = 0; i < n; ++i) {
    const double dx = x[i] - mx;
    num += dx * (y[i] - my);
    den += dx * dx;
  }
  return den > 1e-12 ? num / den : 0.0;
}

// ---------------------------------------------------------------- memory
/// Resident set size of this process in bytes, 0 when /proc is unreadable.
inline uint64_t residentBytes() {
  FILE* f = std::fopen("/proc/self/statm", "r");
  if (f == nullptr) return 0;
  unsigned long total = 0, resident = 0;
  const int got = std::fscanf(f, "%lu %lu", &total, &resident);
  std::fclose(f);
  if (got != 2) return 0;
  const long page = sysconf(_SC_PAGESIZE);
  return static_cast<uint64_t>(resident) * static_cast<uint64_t>(page > 0 ? page : 4096);
}

/// Peak resident set size in bytes (VmHWM), 0 when unavailable.
inline uint64_t peakResidentBytes() {
  FILE* f = std::fopen("/proc/self/status", "r");
  if (f == nullptr) return 0;
  char line[256];
  uint64_t kb = 0;
  while (std::fgets(line, sizeof(line), f) != nullptr) {
    if (std::strncmp(line, "VmHWM:", 6) == 0) {
      unsigned long v = 0;
      if (std::sscanf(line + 6, "%lu", &v) == 1) kb = v;
      break;
    }
  }
  std::fclose(f);
  return kb * 1024u;
}

// ----------------------------------------------------------- environment
struct LoadAvg {
  double one = 0, five = 0, fifteen = 0;
};

inline LoadAvg loadAverage() {
  LoadAvg l;
  FILE* f = std::fopen("/proc/loadavg", "r");
  if (f == nullptr) return l;
  if (std::fscanf(f, "%lf %lf %lf", &l.one, &l.five, &l.fifteen) != 3) l = LoadAvg{};
  std::fclose(f);
  return l;
}

inline void printLoad(const char* when) {
  const LoadAvg l = loadAverage();
  std::printf("  load %-8s %.2f %.2f %.2f\n", when, l.one, l.five, l.fifteen);
}

// ------------------------------------------------------------------- I/O
/// Reads a whole file.  Returns false and leaves `out` empty on any failure.
inline bool readFile(const char* path, std::vector<uint8_t>& out) {
  out.clear();
  FILE* f = std::fopen(path, "rb");
  if (f == nullptr) return false;
  if (std::fseek(f, 0, SEEK_END) != 0) {
    std::fclose(f);
    return false;
  }
  const long len = std::ftell(f);
  if (len < 0 || std::fseek(f, 0, SEEK_SET) != 0) {
    std::fclose(f);
    return false;
  }
  out.resize(static_cast<size_t>(len));
  const size_t got = len == 0 ? 0 : std::fread(out.data(), 1, out.size(), f);
  const bool ok = got == out.size();
  std::fclose(f);
  if (!ok) out.clear();
  return ok;
}

inline std::string mb(uint64_t bytes) {
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%.1f MB", static_cast<double>(bytes) / (1024.0 * 1024.0));
  return std::string(buf);
}

}  // namespace nycbench
