#include "nycsim/geo/TransverseMercator.h"

#include <cmath>

namespace nycsim {
namespace geo {

namespace {

// Karney (2011) eq. 35/36: alpha_j and beta_j as polynomials in the third flattening n.
void krugerCoefficients(double n, double* alpha, double* beta) {
  const double n2 = n * n, n3 = n2 * n, n4 = n3 * n, n5 = n4 * n, n6 = n5 * n;
  alpha[1] = n / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800;
  alpha[2] = 13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360;
  alpha[3] = 61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440;
  alpha[4] = 49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600;
  alpha[5] = 34729 * n5 / 80640 - 3418889 * n6 / 1995840;
  alpha[6] = 212378941 * n6 / 319334400;

  beta[1] = n / 2 - 2 * n2 / 3 + 37 * n3 / 96 - n4 / 360 - 81 * n5 / 512 + 96199 * n6 / 604800;
  beta[2] = n2 / 48 + n3 / 15 - 437 * n4 / 1440 + 46 * n5 / 105 - 1118711 * n6 / 3870720;
  beta[3] = 17 * n3 / 480 - 37 * n4 / 840 - 209 * n5 / 4480 + 5569 * n6 / 90720;
  beta[4] = 4397 * n4 / 161280 - 11 * n5 / 504 - 830251 * n6 / 7257600;
  beta[5] = 4583 * n5 / 161280 - 108847 * n6 / 3991680;
  beta[6] = 20648693 * n6 / 638668800;
}

bool finite(double v) { return std::isfinite(v); }

}  // namespace

TransverseMercator::TransverseMercator(const TmParams& params) : params_(params) {
  const Ellipsoid& el = params_.ellipsoid;
  n_ = el.n();
  e2_ = el.e2();
  e_ = std::sqrt(e2_);
  const double n2 = n_ * n_;
  // Rectifying radius A = a/(1+n) (1 + n^2/4 + n^4/64 + n^6/256 + ...)
  A_ = el.a / (1.0 + n_) * (1.0 + n2 / 4.0 + n2 * n2 / 64.0 + n2 * n2 * n2 / 256.0);
  alpha_[0] = beta_[0] = 0.0;
  krugerCoefficients(n_, alpha_, beta_);
  // Meridian distance of lat0: xi at (lat0, dlon=0) -> k0*A*xi
  m0_ = 0.0;
  double tau, taup, xi1, eta1;
  gaussSchreiber(params_.lat0_deg * kDegToRad, 0.0, tau, taup, xi1, eta1);
  double xi = xi1;
  for (int j = 1; j <= 6; ++j) xi += alpha_[j] * std::sin(2.0 * j * xi1);  // cosh(0) = 1
  m0_ = params_.k0 * A_ * xi;
}

// tau' = conformal tangent from geographic tangent tau = tan(phi). Karney eq. 7.
double TransverseMercator::taupf(double tau) const {
  const double tau1 = std::hypot(1.0, tau);
  const double sig = std::sinh(e_ * std::atanh(e_ * tau / tau1));
  return std::hypot(1.0, sig) * tau - sig * tau1;
}

// Inverse of taupf by Newton's method (Karney eq. 19-21; GeographicLib Math::tauf).
double TransverseMercator::tauf(double taup) const {
  const double e2m = 1.0 - e2_;
  // Initial guess: taup/(1-e^2) is accurate to O(e^2) and always converges quickly.
  double tau = taup / e2m;
  const double stol = 1e-16 * std::fmax(1.0, std::fabs(taup)) * 0.1;
  for (int i = 0; i < 8; ++i) {
    const double taupa = taupf(tau);
    const double dtau = (taup - taupa) * (1.0 + e2m * tau * tau) /
                        (e2m * std::hypot(1.0, tau) * std::hypot(1.0, taupa));
    tau += dtau;
    if (!(std::fabs(dtau) >= stol)) break;
  }
  return tau;
}

void TransverseMercator::gaussSchreiber(double lat_rad, double dlon_rad, double& tau, double& taup,
                                        double& xi1, double& eta1) const {
  tau = std::tan(lat_rad);
  taup = taupf(tau);
  const double cl = std::cos(dlon_rad);
  const double sl = std::sin(dlon_rad);
  xi1 = std::atan2(taup, cl);
  eta1 = std::asinh(sl / std::hypot(taup, cl));
}

Result<XY> TransverseMercator::forward(LatLon p) const {
  if (!finite(p.lat_deg) || !finite(p.lon_deg)) {
    return fail(ErrorCode::InvalidArgument, "TransverseMercator::forward: non-finite input");
  }
  if (p.lat_deg < -90.0 || p.lat_deg > 90.0) {
    return fail(ErrorCode::OutOfRange, "TransverseMercator::forward: latitude outside [-90, 90]");
  }
  double dlon = p.lon_deg - params_.lon0_deg;
  dlon = std::fmod(dlon, 360.0);
  if (dlon > 180.0) dlon -= 360.0;
  if (dlon < -180.0) dlon += 360.0;
  if (std::fabs(dlon) > 90.0) {
    return fail(ErrorCode::OutOfRange,
                "TransverseMercator::forward: more than 90 deg from the central meridian");
  }
  double tau, taup, xi1, eta1;
  gaussSchreiber(p.lat_deg * kDegToRad, dlon * kDegToRad, tau, taup, xi1, eta1);
  double xi = xi1, eta = eta1;
  for (int j = 1; j <= 6; ++j) {
    const double a2 = 2.0 * j;
    xi += alpha_[j] * std::sin(a2 * xi1) * std::cosh(a2 * eta1);
    eta += alpha_[j] * std::cos(a2 * xi1) * std::sinh(a2 * eta1);
  }
  const double kA = params_.k0 * A_;
  return XY{kA * eta + params_.x0_m, kA * xi - m0_ + params_.y0_m};
}

Result<LatLon> TransverseMercator::inverse(XY p) const {
  if (!finite(p.x) || !finite(p.y)) {
    return fail(ErrorCode::InvalidArgument, "TransverseMercator::inverse: non-finite input");
  }
  const double kA = params_.k0 * A_;
  const double xi = (p.y - params_.y0_m + m0_) / kA;
  const double eta = (p.x - params_.x0_m) / kA;
  // Domain of the series: |eta| <= ~pi/2 (about 10,000 km from the CM); beyond, the inverse is
  // not meaningful.
  if (std::fabs(eta) > 1.6 || std::fabs(xi) > 1.6 * kPi) {
    return fail(ErrorCode::OutOfRange, "TransverseMercator::inverse: point outside the projection domain");
  }
  double xi1 = xi, eta1 = eta;
  for (int j = 1; j <= 6; ++j) {
    const double a2 = 2.0 * j;
    xi1 -= beta_[j] * std::sin(a2 * xi) * std::cosh(a2 * eta);
    eta1 -= beta_[j] * std::cos(a2 * xi) * std::sinh(a2 * eta);
  }
  const double sh = std::sinh(eta1);
  const double cx = std::cos(xi1);
  const double taup = std::sin(xi1) / std::hypot(sh, cx);
  const double lam = std::atan2(sh, cx);
  const double tau = tauf(taup);
  const double lat = std::atan(tau) * kRadToDeg;
  double lon = params_.lon0_deg + lam * kRadToDeg;
  if (lon > 180.0) lon -= 360.0;
  if (lon < -180.0) lon += 360.0;
  return LatLon{lat, lon};
}

Result<TransverseMercator::Factors> TransverseMercator::factors(LatLon p) const {
  if (!finite(p.lat_deg) || !finite(p.lon_deg)) {
    return fail(ErrorCode::InvalidArgument, "TransverseMercator::factors: non-finite input");
  }
  double dlon = p.lon_deg - params_.lon0_deg;
  dlon = std::fmod(dlon, 360.0);
  if (dlon > 180.0) dlon -= 360.0;
  if (dlon < -180.0) dlon += 360.0;
  if (std::fabs(dlon) > 90.0 || std::fabs(p.lat_deg) >= 90.0) {
    return fail(ErrorCode::OutOfRange, "TransverseMercator::factors: outside the domain");
  }
  const double phi = p.lat_deg * kDegToRad;
  const double lam = dlon * kDegToRad;
  double tau, taup, xi1, eta1;
  gaussSchreiber(phi, lam, tau, taup, xi1, eta1);
  // Spherical (Gauss-Schreiber) part on the conformal sphere.
  const double cl = std::cos(lam), sl = std::sin(lam);
  const double gamma1 = std::atan2(taup * sl, std::hypot(1.0, taup) * cl);
  const double k1 = std::hypot(1.0, taup) / std::hypot(taup, cl);
  // Series part (Karney eq. 26-27).
  double pp = 1.0, qq = 0.0;
  for (int j = 1; j <= 6; ++j) {
    const double a2 = 2.0 * j;
    pp += a2 * alpha_[j] * std::cos(a2 * xi1) * std::cosh(a2 * eta1);
    qq += a2 * alpha_[j] * std::sin(a2 * xi1) * std::sinh(a2 * eta1);
  }
  const double gamma2 = std::atan2(qq, pp);
  const double k2 = std::hypot(pp, qq);
  // Ellipsoid -> conformal sphere scale: cos(chi) sqrt(1 - e^2 sin^2 phi) / (a cos phi).
  const double sphi = std::sin(phi);
  const double kEll = std::hypot(1.0, tau) * std::sqrt(1.0 - e2_ * sphi * sphi) /
                      (params_.ellipsoid.a * std::hypot(1.0, taup));
  Factors f;
  f.scale = params_.k0 * A_ * k1 * k2 * kEll;
  f.convergence_deg = (gamma1 + gamma2) * kRadToDeg;
  return f;
}

}  // namespace geo
}  // namespace nycsim
