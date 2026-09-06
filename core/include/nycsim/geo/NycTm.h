// The project world CRS NYC_TM (ADR-002, DATA_CONTRACTS §1):
//   +proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m
// and the scope / tile constants mirrored from pipeline/nycsim_pipeline/crs.py.
#pragma once

#include "nycsim/Config.h"
#include "nycsim/geo/Ellipsoid.h"
#include "nycsim/geo/TransverseMercator.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace geo {

inline constexpr TmParams kNycTmParams{kWGS84, 40.7, -73.95, 1.0, 0.0, 0.0};
inline constexpr const char* kNycTmProj4 =
    "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs";

// Project scope bounding box in NYC_TM metres (crs.py SCOPE_*).
inline constexpr double kScopeXMin = -30000.0;
inline constexpr double kScopeXMax = 24000.0;
inline constexpr double kScopeYMin = -27000.0;
inline constexpr double kScopeYMax = 27000.0;

/// The NYC_TM projection (constructed on first use; thread-safe).
NYCSIM_API const TransverseMercator& nycTm();

/// WGS84 lon/lat (degrees) -> NYC_TM x/y (metres).
NYCSIM_API Result<XY> lonLatToTm(double lon_deg, double lat_deg);
/// NYC_TM x/y (metres) -> WGS84 lon/lat (degrees).
NYCSIM_API Result<LatLon> tmToLonLat(double x_m, double y_m);
/// True when a NYC_TM point lies inside the project scope box.
constexpr bool inScope(double x_m, double y_m) {
  return x_m >= kScopeXMin && x_m <= kScopeXMax && y_m >= kScopeYMin && y_m <= kScopeYMax;
}

}  // namespace geo
}  // namespace nycsim
