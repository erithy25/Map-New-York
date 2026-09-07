// Ellipsoidal Transverse Mercator, Krüger series to sixth order in the third flattening n
// (Karney, "Transverse Mercator with an accuracy of a few nanometers", J. Geod. 85, 2011).
// Same algorithm family as PROJ's default "poder/engsager" tmerc; accuracy ~ nm within 3900 km of
// the central meridian. Forward and inverse are exact inverses to double precision.
#pragma once

#include "nycsim/Config.h"
#include "nycsim/geo/Ellipsoid.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace geo {

struct TmParams {
  Ellipsoid ellipsoid = kWGS84;
  double lat0_deg = 0.0;  ///< latitude of natural origin
  double lon0_deg = 0.0;  ///< central meridian
  double k0 = 1.0;        ///< scale on the central meridian
  double x0_m = 0.0;      ///< false easting
  double y0_m = 0.0;      ///< false northing
};

class NYCSIM_API TransverseMercator {
 public:
  struct Factors {
    double scale;            ///< point scale factor k
    double convergence_deg;  ///< grid convergence gamma (PROJ sign convention: positive east of
                             ///< the central meridian in the northern hemisphere, where grid
                             ///< north lies east of true north)
  };

  explicit TransverseMercator(const TmParams& params);

  /// Geographic -> projected. Fails for non-finite input, |lat| > 90 or |lon - lon0| > 90 deg.
  Result<XY> forward(LatLon p) const;
  /// Projected -> geographic. Fails for non-finite input or a point outside the series domain.
  Result<LatLon> inverse(XY p) const;
  /// Point scale and grid convergence at a geographic position.
  Result<Factors> factors(LatLon p) const;

  const TmParams& params() const { return params_; }
  /// Rectifying radius A (metres).
  double rectifyingRadius() const { return A_; }

 private:
  void gaussSchreiber(double lat_rad, double dlon_rad, double& tau, double& taup, double& xi1,
                      double& eta1) const;
  double taupf(double tau) const;
  double tauf(double taup) const;

  TmParams params_;
  double n_;
  double e2_;
  double e_;
  double A_;
  double alpha_[7];  ///< alpha_[1..6]
  double beta_[7];   ///< beta_[1..6]
  double m0_;        ///< k0 * A * xi(lat0): meridian distance of the origin latitude
};

}  // namespace geo
}  // namespace nycsim
