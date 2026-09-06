// nycsim/vehicle/LongitudinalSim.h — deterministic longitudinal integration of the player car.
//
// Fixed-step RK4 over the tractive force / resistance balance of Powertrain.h. Used for the
// acceptance tests (0-60 mph, braking distance, top speed) and by the traffic model when a car has
// to be driven to a target speed without the engine in the loop.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"
#include "nycsim/vehicle/Friction.h"
#include "nycsim/vehicle/Powertrain.h"
#include "nycsim/vehicle/VehicleSpec.h"

namespace nycsim {
namespace vehicle {

struct DriveConditions {
  SurfaceClass surface = SurfaceClass::DryAsphalt;
  double wetness = 0.0;
  double snowCover = 0.0;
  double iceRisk = 0.0;
  double gradeRad = 0.0;
  bool engineRunning = true;
  /// Friction coefficient actually used.
  double mu() const { return frictionFor(surface, wetness, snowCover, iceRisk); }
};

struct AccelResult {
  double timeS = 0.0;
  double distanceM = 0.0;
  double finalSpeedMps = 0.0;
  double peakAccelMps2 = 0.0;
  bool reachedTarget = false;
};

/// Time and distance to accelerate from `fromMps` to `toMps` at full throttle.
/// Fails (ErrorCode::NoConvergence) when the car cannot reach the target within `maxTimeS`.
NYCSIM_API Result<AccelResult> accelerationRun(const VehicleSpec& spec, double fromMps, double toMps,
                                               const DriveConditions& cond, double dtS = 0.001,
                                               double maxTimeS = 120.0);

/// 0-60 mph in seconds — the published acceptance figure of ADR-009.
NYCSIM_API Result<double> zeroToSixtyS(const VehicleSpec& spec,
                                       const DriveConditions& cond = DriveConditions());

struct BrakingResult {
  double distanceM = 0.0;
  double timeS = 0.0;
  double meanDecelMps2 = 0.0;
};
/// Straight-line braking from `fromMps` to rest at the traction limit of the surface.
NYCSIM_API BrakingResult brakingRun(const VehicleSpec& spec, double fromMps,
                                    const DriveConditions& cond, double dtS = 0.001);

/// One fixed step of the longitudinal state (speed in, speed out), RK4 on dv/dt = a(v).
NYCSIM_API double stepSpeed(const VehicleSpec& spec, double speedMps, double throttle,
                            const DriveConditions& cond, double dtS);

}  // namespace vehicle
}  // namespace nycsim
