// nycsim/vehicle/Powertrain.h — tractive effort of the Fusion Hybrid's power-split eCVT.
//
// A power-split hybrid has no gear steps: below a corner speed the transaxle is torque-limited
// (the motor's peak torque through the fixed reduction), above it the system's peak power is the
// ceiling. That is the whole model:
//
//   F_wheel(v) = min(maxWheelForceN, systemPowerW * drivelineEfficiency / max(v, v_eps)) * throttle
//
// with the same power ceiling used for the EV-only mode when the engine is not running. Resistances
// (rolling, aerodynamic, grade) are separate so the same functions serve the traffic model.
#pragma once

#include "nycsim/Config.h"
#include "nycsim/vehicle/Friction.h"
#include "nycsim/vehicle/VehicleSpec.h"

namespace nycsim {
namespace vehicle {

/// Peak tractive force at the contact patch at speed `speedMps` (N). `throttle` is 0..1.
NYCSIM_API double tractiveForceN(const VehicleSpec& spec, double speedMps, double throttle = 1.0,
                                 bool engineRunning = true);
/// Corner speed: below it the eCVT is torque-limited, above it power-limited (m/s).
NYCSIM_API double cornerSpeedMps(const VehicleSpec& spec, bool engineRunning = true);
/// Rolling resistance (N), always opposing motion; zero at rest.
NYCSIM_API double rollingResistanceN(const VehicleSpec& spec, double massKg, double speedMps);
/// Aerodynamic drag (N) at the spec's air density.
NYCSIM_API double aeroDragN(const VehicleSpec& spec, double speedMps);
/// Grade force (N); `gradeRad` is positive uphill.
NYCSIM_API double gradeForceN(double massKg, double gradeRad);
/// Net longitudinal acceleration (m/s^2) including the rotating-inertia allowance, with the
/// tractive force capped by the surface's traction limit.
NYCSIM_API double longitudinalAccelMps2(const VehicleSpec& spec, double speedMps, double throttle,
                                        double mu, double gradeRad = 0.0, bool engineRunning = true);
/// Steady-state top speed on level ground for a given friction coefficient (m/s), found by
/// bisection on tractive force minus resistance; never exceeds the published limiter.
NYCSIM_API double steadyTopSpeedMps(const VehicleSpec& spec, double mu);

}  // namespace vehicle
}  // namespace nycsim
