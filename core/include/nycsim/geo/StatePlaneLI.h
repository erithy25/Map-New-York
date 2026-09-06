// EPSG:2263 — NAD83 / New York Long Island (US survey feet).
//   Lambert Conformal Conic 2SP on GRS80: lat1 40°40'N, lat2 41°02'N, lat0 40°10'N, lon0 74°W,
//   false easting 984 250 ftUS (= 300 000 m exactly), false northing 0.
//
// Datum: NAD83 is treated as identical to WGS84 (null shift). This is what pyproj/PROJ applies for
// EPSG:2263 -> NYC_TM ("NAD83 to WGS 84 (1)", EPSG:1188, declared accuracy 4 m; the physical
// NAD83(2011)–WGS84(G2139) offset in New York is about 1.0–1.5 m horizontally). The NYC datasets
// (footprints, LION, planimetrics) are all NAD83, so relative geometry is unaffected; the
// assumption only shifts the whole world with respect to GNSS WGS84 by ≈ 1 m, which is below the
// terrain resolution (2 m) and the footprint accuracy.
#pragma once

#include "nycsim/Config.h"
#include "nycsim/geo/Ellipsoid.h"
#include "nycsim/geo/LambertConformalConic.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace geo {

inline constexpr LccParams kStatePlaneLIParams{kGRS80,
                                               40.0 + 40.0 / 60.0,
                                               41.0 + 2.0 / 60.0,
                                               40.0 + 10.0 / 60.0,
                                               -74.0,
                                               300000.0,
                                               0.0};

/// The EPSG:2263 projection in metres (constructed on first use; thread-safe).
NYCSIM_API const LambertConformalConic& statePlaneLI();

/// NAD83 lon/lat (degrees) -> EPSG:2263 easting/northing in US survey feet.
NYCSIM_API Result<XY> lonLatToStatePlaneFt(double lon_deg, double lat_deg);
/// EPSG:2263 (ftUS) -> NAD83 lon/lat (degrees).
NYCSIM_API Result<LatLon> statePlaneFtToLonLat(double x_ft, double y_ft);
/// EPSG:2263 (ftUS) -> NYC_TM metres, null NAD83≈WGS84 shift (see file comment).
NYCSIM_API Result<XY> statePlaneFtToTm(double x_ft, double y_ft);
/// NYC_TM metres -> EPSG:2263 (ftUS), null NAD83≈WGS84 shift.
NYCSIM_API Result<XY> tmToStatePlaneFt(double x_m, double y_m);

}  // namespace geo
}  // namespace nycsim
