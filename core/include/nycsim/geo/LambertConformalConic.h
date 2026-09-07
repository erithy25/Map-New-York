// Lambert Conformal Conic, two standard parallels (Snyder 1987, "Map Projections — A Working
// Manual", USGS PP 1395, pp. 104-110; the formulas used by PROJ's lcc).
#pragma once

#include "nycsim/Config.h"
#include "nycsim/geo/Ellipsoid.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace geo {

struct LccParams {
  Ellipsoid ellipsoid = kGRS80;
  double lat1_deg = 0.0;  ///< first standard parallel
  double lat2_deg = 0.0;  ///< second standard parallel
  double lat0_deg = 0.0;  ///< latitude of false origin
  double lon0_deg = 0.0;  ///< longitude of false origin (central meridian)
  double x0_m = 0.0;      ///< false easting, metres
  double y0_m = 0.0;      ///< false northing, metres
};

class NYCSIM_API LambertConformalConic {
 public:
  explicit LambertConformalConic(const LccParams& params);

  /// Geographic -> projected (metres). Fails for non-finite input or |lat| >= 90.
  Result<XY> forward(LatLon p) const;
  /// Projected (metres) -> geographic. Fails for non-finite input or a point at/beyond the apex.
  Result<LatLon> inverse(XY p) const;
  /// Point scale factor (LCC is conformal: same in every direction).
  Result<double> scale(LatLon p) const;

  const LccParams& params() const { return params_; }
  double coneConstant() const { return n_; }

 private:
  double msfn(double sinphi, double cosphi) const;
  double tsfn(double phi, double sinphi) const;

  LccParams params_;
  double e_;
  double e2_;
  double n_;
  double F_;
  double rho0_;
};

}  // namespace geo
}  // namespace nycsim
