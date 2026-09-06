#pragma once
// nycsim/peds/SocialForce.h — the Helbing social-force terms, as pure inline
// functions so they can be unit-tested on their own.
//
// Helbing & Molnár, "Social force model for pedestrian dynamics", Phys. Rev. E
// 51, 4282 (1995), with the anisotropy factor of Helbing, Farkas & Vicsek,
// "Simulating dynamical features of escape panic", Nature 407, 487 (2000) and
// the body-contact term of the same paper for dense crowds:
//
//   driving      f0  = (v0·e − v) / τ
//   repulsion    fij = A·exp((r_ij − d_ij)/B)·n_ij·(λ + (1−λ)(1+cos φ)/2)
//   contact      + k·max(0, r_ij − d_ij)·n_ij          (d < r only)
//   obstacle     fiw = A_w·exp((r_i − d_iw)/B_w)·n_iw
//
// Units are accelerations (m/s²), i.e. forces per unit mass, which is how the
// 1995 paper writes them; A = 2.1 m/s², B = 0.3 m, τ = 0.5 s, λ = 0.35 are the
// published values.  See docs/verification/traffic/REPORT.md §Calibration.
//
// exp() is evaluated with expNegApprox(), a libm-free approximation whose
// maximum relative error over the range this model uses is measured in
// tests/peds/test_social_force.cpp.  Using it rather than std::exp keeps the
// crowd bit-reproducible across platforms and standard libraries.

#include <cmath>

namespace nycsim {
namespace peds {

// e^-x for x ≥ 0, via (1 − x/64)^64.  Monotone, exact at 0, saturates to 0.
inline float expNegApprox(float x) {
  if (x <= 0.f) return 1.f;
  if (x >= 60.f) return 0.f;
  float t = 1.f - x * (1.f / 64.f);
  t *= t;  // ^2
  t *= t;  // ^4
  t *= t;  // ^8
  t *= t;  // ^16
  t *= t;  // ^32
  t *= t;  // ^64
  return t;
}

struct SocialForceParams {
  float tau_s = 0.5f;
  float A = 2.1f;
  float B = 0.3f;
  float lambda = 0.35f;
  float body_k = 120.f;   // contact spring [1/s²]
  float wall_A = 10.0f;
  float wall_B = 0.2f;
  float cutoff_m = 2.0f;
};

struct Force2 {
  float x = 0.f, y = 0.f;
};

// (v0·e − v)/τ
inline Force2 drivingForce(const SocialForceParams& p, float v0, float ex, float ey, float vx, float vy) {
  const float inv_tau = 1.f / (p.tau_s > 0.01f ? p.tau_s : 0.01f);
  return Force2{(v0 * ex - vx) * inv_tau, (v0 * ey - vy) * inv_tau};
}

// Repulsion of j on i.  (dx,dy) = pos_i − pos_j; (ex,ey) is i's heading.
inline Force2 pedRepulsion(const SocialForceParams& p, float dx, float dy, float dist, float radius_sum, float ex,
                           float ey) {
  Force2 f;
  if (dist < 1e-4f) {
    // Exactly coincident: push along i's heading normal, deterministically.
    f.x = p.A * ey;
    f.y = -p.A * ex;
    return f;
  }
  const float nx = dx / dist, ny = dy / dist;
  float mag = p.A * expNegApprox((dist - radius_sum) / (p.B > 0.01f ? p.B : 0.01f));
  // Anisotropy: what is behind me influences me less.
  const float cos_phi = -(nx * ex + ny * ey);  // +1 when j is straight ahead
  mag *= p.lambda + (1.f - p.lambda) * 0.5f * (1.f + cos_phi);
  if (dist < radius_sum) mag += p.body_k * (radius_sum - dist);
  f.x = mag * nx;
  f.y = mag * ny;
  return f;
}

// Repulsion of a wall/obstacle whose closest point is (dx,dy) away from i.
inline Force2 wallRepulsion(const SocialForceParams& p, float dx, float dy, float dist, float radius) {
  Force2 f;
  if (dist < 1e-4f) return f;
  const float mag = p.wall_A * expNegApprox((dist - radius) / (p.wall_B > 0.01f ? p.wall_B : 0.01f));
  f.x = mag * dx / dist;
  f.y = mag * dy / dist;
  return f;
}

}  // namespace peds
}  // namespace nycsim
