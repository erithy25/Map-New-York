// Reference ellipsoids and basic geodetic value types.
#pragma once

#include "nycsim/Config.h"

namespace nycsim {
namespace geo {

struct Ellipsoid {
  double a;  ///< semi-major axis, metres
  double f;  ///< flattening

  constexpr double b() const { return a * (1.0 - f); }
  constexpr double e2() const { return f * (2.0 - f); }         ///< first eccentricity squared
  constexpr double n() const { return f / (2.0 - f); }          ///< third flattening
};

/// WGS 84 (EPSG:7030).
inline constexpr Ellipsoid kWGS84{6378137.0, 1.0 / 298.257223563};
/// GRS 1980 (EPSG:7019), used by NAD83.
inline constexpr Ellipsoid kGRS80{6378137.0, 1.0 / 298.257222101};

struct LatLon {
  double lat_deg;
  double lon_deg;
};

struct XY {
  double x;
  double y;
};

inline constexpr double kPi = 3.14159265358979323846;
inline constexpr double kDegToRad = kPi / 180.0;
inline constexpr double kRadToDeg = 180.0 / kPi;

}  // namespace geo
}  // namespace nycsim
