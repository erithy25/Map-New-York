// NYC_TM (east, north, up; metres; right-handed Z-up) <-> Unreal Engine world coordinates
// (left-handed Z-up, centimetres): UE.X = east*100, UE.Y = -north*100, UE.Z = up*100.
// ARCHITECTURE §2. This is the only place this mapping is written down.
//
// Rotations: UE yaw is measured about +Z from +X towards +Y (clockwise seen from above, since
// +Y points south). Compass heading (0 = north, clockwise) maps to yaw = heading - 90.
// Mathematical angle (0 = east, counter-clockwise) maps to yaw = -angle.
#pragma once

#include "nycsim/Config.h"

namespace nycsim {
namespace geo {

struct WorldPos {
  double east_m;
  double north_m;
  double up_m;
};

struct UEVector {
  double x_cm;
  double y_cm;
  double z_cm;
};

inline constexpr double kMetresToUE = 100.0;

constexpr UEVector toUE(const WorldPos& p) {
  return UEVector{p.east_m * kMetresToUE, -p.north_m * kMetresToUE, p.up_m * kMetresToUE};
}
constexpr UEVector toUE(double east_m, double north_m, double up_m) {
  return toUE(WorldPos{east_m, north_m, up_m});
}
constexpr WorldPos fromUE(const UEVector& v) {
  return WorldPos{v.x_cm / kMetresToUE, -v.y_cm / kMetresToUE, v.z_cm / kMetresToUE};
}

/// Wraps degrees to [0, 360).
constexpr double wrapDeg360(double d) {
  double r = d - 360.0 * static_cast<double>(static_cast<long long>(d / 360.0));
  if (r < 0.0) r += 360.0;
  if (r >= 360.0) r -= 360.0;
  return r;
}
/// Wraps degrees to [-180, 180).
constexpr double wrapDeg180(double d) {
  double r = wrapDeg360(d);
  return r >= 180.0 ? r - 360.0 : r;
}

/// Compass heading (0 = north, clockwise) -> UE yaw degrees in [-180, 180).
constexpr double headingToUEYaw(double heading_deg) { return wrapDeg180(heading_deg - 90.0); }
/// UE yaw -> compass heading in [0, 360).
constexpr double ueYawToHeading(double yaw_deg) { return wrapDeg360(yaw_deg + 90.0); }
/// Mathematical angle (0 = east, counter-clockwise) -> UE yaw in [-180, 180).
constexpr double mathAngleToUEYaw(double angle_deg) { return wrapDeg180(-angle_deg); }
/// UE yaw -> mathematical angle in [0, 360).
constexpr double ueYawToMathAngle(double yaw_deg) { return wrapDeg360(-yaw_deg); }
/// Mathematical angle -> compass heading.
constexpr double mathAngleToHeading(double angle_deg) { return wrapDeg360(90.0 - angle_deg); }
constexpr double headingToMathAngle(double heading_deg) { return wrapDeg360(90.0 - heading_deg); }

/// Direction vector (unit, ENU) -> UE direction (unit, left-handed).
constexpr UEVector directionToUE(double east, double north, double up) {
  return UEVector{east, -north, up};
}

}  // namespace geo
}  // namespace nycsim
