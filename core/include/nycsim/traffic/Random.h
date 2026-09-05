#pragma once
// nycsim/traffic/Random.h — deterministic, allocation-free PRNG shared by the
// traffic, routing and pedestrian modules.  SplitMix64 (Steele, Lea & Flood,
// OOPSLA 2014) — 64-bit state, period 2^64, passes BigCrush.  All simulation
// randomness must go through this type so that a given seed reproduces the
// same trajectories bit-for-bit on every platform (no <random>, whose
// distributions are implementation-defined).

#include <cstdint>
#include <cmath>

namespace nycsim {

class Rng {
 public:
  Rng() = default;
  explicit Rng(uint64_t seed) { reseed(seed); }

  void reseed(uint64_t seed) { state_ = seed * 0x9E3779B97F4A7C15ull + 0xD1B54A32D192ED03ull; }

  uint64_t next() {
    uint64_t z = (state_ += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
  }

  // Uniform in [0,1).  24 random bits → exactly representable, platform-stable.
  float uniform() { return static_cast<float>(next() >> 40) * (1.0f / 16777216.0f); }
  float uniform(float lo, float hi) { return lo + (hi - lo) * uniform(); }
  // Uniform integer in [0, n).  n == 0 returns 0.
  uint32_t below(uint32_t n) { return n == 0 ? 0u : static_cast<uint32_t>((next() >> 32) % n); }
  bool chance(float p) { return uniform() < p; }

  // Standard normal via Box–Muller; deterministic given the state.
  float normal() {
    float u1 = uniform();
    if (u1 < 1e-7f) u1 = 1e-7f;
    const float u2 = uniform();
    const float r = std::sqrt(-2.0f * std::log(u1));
    return r * std::cos(6.28318530718f * u2);
  }
  float normal(float mean, float sd) { return mean + sd * normal(); }
  // Normal clipped to [lo, hi] (re-sampling would break the fixed draw count).
  float normalClamped(float mean, float sd, float lo, float hi) {
    const float v = normal(mean, sd);
    return v < lo ? lo : (v > hi ? hi : v);
  }
  // Exponential with the given rate (events per unit); rate <= 0 → +inf.
  float exponential(float rate) {
    if (rate <= 0.f) return INFINITY;
    float u = uniform();
    if (u < 1e-7f) u = 1e-7f;
    return -std::log(u) / rate;
  }

  uint64_t state() const { return state_; }

 private:
  uint64_t state_ = 0x853C49E6748FEA9Bull;
};

// FNV-1a 64-bit — used for trajectory hashes in determinism tests.
struct Fnv1a64 {
  uint64_t h = 0xCBF29CE484222325ull;
  void add(const void* data, size_t n) {
    const unsigned char* p = static_cast<const unsigned char*>(data);
    for (size_t i = 0; i < n; ++i) {
      h ^= p[i];
      h *= 0x100000001B3ull;
    }
  }
  void addU32(uint32_t v) { add(&v, sizeof v); }
  void addF32(float v) { add(&v, sizeof v); }
};

}  // namespace nycsim
