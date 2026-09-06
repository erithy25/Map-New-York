#include "nycsim/geo/LambertConformalConic.h"

#include <cmath>

namespace nycsim {
namespace geo {

namespace {
constexpr double kHalfPi = kPi / 2.0;
constexpr double kQuarterPi = kPi / 4.0;
}  // namespace

// Snyder eq. 14-15: m = cos(phi) / sqrt(1 - e^2 sin^2 phi)
double LambertConformalConic::msfn(double sinphi, double cosphi) const {
  return cosphi / std::sqrt(1.0 - e2_ * sinphi * sinphi);
}

// Snyder eq. 15-9: t = tan(pi/4 - phi/2) / ((1 - e sin phi)/(1 + e sin phi))^(e/2)
double LambertConformalConic::tsfn(double phi, double sinphi) const {
  const double es = e_ * sinphi;
  return std::tan(kQuarterPi - phi / 2.0) / std::pow((1.0 - es) / (1.0 + es), e_ / 2.0);
}

LambertConformalConic::LambertConformalConic(const LccParams& params) : params_(params) {
  e2_ = params_.ellipsoid.e2();
  e_ = std::sqrt(e2_);
  const double phi1 = params_.lat1_deg * kDegToRad;
  const double phi2 = params_.lat2_deg * kDegToRad;
  const double phi0 = params_.lat0_deg * kDegToRad;
  const double s1 = std::sin(phi1), c1 = std::cos(phi1);
  const double s2 = std::sin(phi2), c2 = std::cos(phi2);
  const double m1 = msfn(s1, c1);
  const double t1 = tsfn(phi1, s1);
  if (std::fabs(phi1 - phi2) >= 1e-10) {
    const double m2 = msfn(s2, c2);
    const double t2 = tsfn(phi2, s2);
    n_ = std::log(m1 / m2) / std::log(t1 / t2);  // Snyder 15-8
  } else {
    n_ = s1;  // tangent cone
  }
  F_ = m1 / (n_ * std::pow(t1, n_));  // Snyder 15-10
  const double t0 = tsfn(phi0, std::sin(phi0));
  rho0_ = params_.ellipsoid.a * F_ * std::pow(t0, n_);  // Snyder 15-7a
}

Result<XY> LambertConformalConic::forward(LatLon p) const {
  if (!std::isfinite(p.lat_deg) || !std::isfinite(p.lon_deg)) {
    return fail(ErrorCode::InvalidArgument, "LambertConformalConic::forward: non-finite input");
  }
  if (std::fabs(p.lat_deg) >= 90.0) {
    return fail(ErrorCode::OutOfRange, "LambertConformalConic::forward: latitude at a pole");
  }
  const double phi = p.lat_deg * kDegToRad;
  double dlon = p.lon_deg - params_.lon0_deg;
  dlon = std::fmod(dlon, 360.0);
  if (dlon > 180.0) dlon -= 360.0;
  if (dlon < -180.0) dlon += 360.0;
  const double t = tsfn(phi, std::sin(phi));
  const double rho = params_.ellipsoid.a * F_ * std::pow(t, n_);  // 15-7
  const double theta = n_ * dlon * kDegToRad;                      // 14-4
  return XY{params_.x0_m + rho * std::sin(theta), params_.y0_m + rho0_ - rho * std::cos(theta)};
}

Result<LatLon> LambertConformalConic::inverse(XY p) const {
  if (!std::isfinite(p.x) || !std::isfinite(p.y)) {
    return fail(ErrorCode::InvalidArgument, "LambertConformalConic::inverse: non-finite input");
  }
  double dx = p.x - params_.x0_m;
  double dy = rho0_ - (p.y - params_.y0_m);
  if (n_ < 0.0) {
    dx = -dx;
    dy = -dy;
  }
  const double rho = std::hypot(dx, dy);
  if (rho == 0.0) {
    // Apex of the cone: latitude is the pole, longitude undefined -> central meridian.
    return LatLon{n_ > 0.0 ? 90.0 : -90.0, params_.lon0_deg};
  }
  const double theta = std::atan2(dx, dy);  // 14-11
  const double t = std::pow(rho / (params_.ellipsoid.a * F_), 1.0 / n_);  // 15-11
  // Snyder 7-9: iterate phi = pi/2 - 2 atan(t ((1 - e sin phi)/(1 + e sin phi))^(e/2)).
  double phi = kHalfPi - 2.0 * std::atan(t);
  for (int i = 0; i < 20; ++i) {
    const double es = e_ * std::sin(phi);
    const double next = kHalfPi - 2.0 * std::atan(t * std::pow((1.0 - es) / (1.0 + es), e_ / 2.0));
    const double d = std::fabs(next - phi);
    phi = next;
    if (d < 1e-15) break;
  }
  double lon = params_.lon0_deg + (theta / n_) * kRadToDeg;  // 14-9
  if (lon > 180.0) lon -= 360.0;
  if (lon < -180.0) lon += 360.0;
  return LatLon{phi * kRadToDeg, lon};
}

Result<double> LambertConformalConic::scale(LatLon p) const {
  if (!std::isfinite(p.lat_deg) || std::fabs(p.lat_deg) >= 90.0) {
    return fail(ErrorCode::OutOfRange, "LambertConformalConic::scale: invalid latitude");
  }
  const double phi = p.lat_deg * kDegToRad;
  const double s = std::sin(phi), c = std::cos(phi);
  const double m = msfn(s, c);
  const double t = tsfn(phi, s);
  const double rho = params_.ellipsoid.a * F_ * std::pow(t, n_);
  return rho * n_ / (params_.ellipsoid.a * m);  // Snyder 15-4
}

}  // namespace geo
}  // namespace nycsim
