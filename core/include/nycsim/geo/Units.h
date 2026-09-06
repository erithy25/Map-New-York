// Unit conversion constants (exact definitions where they exist).
#pragma once

namespace nycsim {
namespace units {

/// US survey foot: 1200/3937 m exactly. NYC State Plane (EPSG:2263), footprints, DEM, CityGML.
inline constexpr double kUsSurveyFootM = 1200.0 / 3937.0;  // 0.30480060960121924
/// International foot (exact).
inline constexpr double kIntlFootM = 0.3048;
inline constexpr double kMileM = 1609.344;           ///< statute mile (exact)
inline constexpr double kNauticalMileM = 1852.0;     ///< exact
inline constexpr double kMphToMps = kMileM / 3600.0;  // 0.44704
inline constexpr double kKnotToMps = kNauticalMileM / 3600.0;
inline constexpr double kKmhToMps = 1000.0 / 3600.0;
inline constexpr double kInHgToHPa = 33.86389;       ///< inch of mercury (conventional) to hPa
inline constexpr double kInchM = 0.0254;             ///< exact
inline constexpr double kLbfToN = 4.4482216152605;   ///< exact
inline constexpr double kHpToW = 745.69987158227022; ///< mechanical horsepower (exact)
inline constexpr double kLbToKg = 0.45359237;        ///< exact
inline constexpr double kGravity = 9.80665;          ///< standard gravity m/s^2

constexpr double usFtToM(double ft) { return ft * kUsSurveyFootM; }
constexpr double mToUsFt(double m) { return m / kUsSurveyFootM; }
constexpr double mphToMps(double v) { return v * kMphToMps; }
constexpr double mpsToMph(double v) { return v / kMphToMps; }

}  // namespace units
}  // namespace nycsim
