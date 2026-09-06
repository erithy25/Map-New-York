#pragma once
// nycsim/traffic/Idm.h — Intelligent Driver Model (Treiber, Hennecke & Helbing,
// "Congested traffic states in empirical observations and microscopic
// simulations", Phys. Rev. E 62, 1805 (2000)), in the collision-free form used
// throughout NYCSim.
//
//   s*(v, Δv) = s0 + max(0, v·T + v·Δv / (2·sqrt(a·b)))
//   dv/dt     = a · [ 1 − (v/v0)^δ − (s*/s)² ]
//
// with δ = 4 (the standard exponent), Δv = v − v_lead (positive when closing)
// and s the bumper-to-bumper gap.  Per-class a, b, T, s0 come from
// VehicleClass.cpp; the calibration sources are listed in
// docs/verification/traffic/REPORT.md §Calibration.
//
// Everything here is a pure inline function of its arguments: no state, no
// allocation, no libm call other than the multiplications below, so the model
// is bit-reproducible for a given input sequence on any IEEE-754 target.

#include <algorithm>
#include <cmath>

namespace nycsim {
namespace traffic {

struct IdmParams {
  float a = 1.4f;       // maximum acceleration [m/s²]
  float b = 2.0f;       // comfortable deceleration [m/s²]
  float b_max = 8.0f;   // emergency braking cap [m/s²] (positive magnitude)
  float T = 1.1f;       // desired time headway [s]
  float s0 = 2.0f;      // minimum standstill gap [m]
  float v0 = 11.176f;   // desired speed [m/s]
};

// Free-road term only (no leader).
inline float idmFreeAccel(const IdmParams& p, float v) {
  const float x = p.v0 > 0.01f ? v / p.v0 : 1.f;
  const float x2 = x * x;
  return p.a * (1.f - x2 * x2);
}

// Full IDM.  `gap` is bumper-to-bumper metres (may be ≤ 0 for an overlap, which
// yields the emergency deceleration), `dv` = v − v_lead.
inline float idmAccel(const IdmParams& p, float v, float gap, float dv) {
  const float sqrt_ab = std::sqrt(std::max(0.01f, p.a * p.b));
  float s_star = p.s0 + v * p.T + v * dv / (2.f * sqrt_ab);
  if (s_star < p.s0) s_star = p.s0;
  const float s = gap > 0.05f ? gap : 0.05f;
  const float ratio = s_star / s;
  const float acc = idmFreeAccel(p, v) - p.a * ratio * ratio;
  return std::clamp(acc, -p.b_max, p.a);
}

// Deceleration required to stop `distance` metres ahead (a red light, a stop
// line, a pedestrian in the crosswalk, the player standing in the lane).  The
// obstacle is stationary, so Δv = v and the gap is reduced by s0 already being
// inside `distance`.
inline float idmStopAccel(const IdmParams& p, float v, float distance) {
  return idmAccel(p, v, distance, v);
}

// Kinematic check used by the yellow-light decision zone and by emergency
// braking: distance needed to stop from v at deceleration b after a reaction
// time t_react.  (AASHTO Green Book stopping-sight-distance form.)
inline float stoppingDistance(float v, float b, float t_react) {
  const float bb = b > 0.1f ? b : 0.1f;
  return v * t_react + (v * v) / (2.f * bb);
}

// Speed limit on a curve of radius R for a lateral acceleration budget
// (AASHTO: 0.15 g comfortable on turns; NYCSim uses 1.5 m/s² for cars).
inline float curveSpeed(float radius_m, float lat_accel) {
  if (radius_m <= 0.5f) return 2.0f;
  return std::sqrt(std::max(0.1f, lat_accel) * radius_m);
}

}  // namespace traffic
}  // namespace nycsim
