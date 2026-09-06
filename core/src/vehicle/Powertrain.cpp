#include "nycsim/vehicle/Powertrain.h"

#include <cmath>

namespace nycsim {
namespace vehicle {

namespace {
/// Speed floor for the P/v evaluation: below ~0.5 m/s the transaxle is torque-limited anyway, and
/// this keeps the expression finite at standstill.
constexpr double kSpeedEpsMps = 0.5;
constexpr double kGravity = 9.80665;

double clamp01(double v) { return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }
}  // namespace

double cornerSpeedMps(const VehicleSpec& spec, bool engineRunning) {
  const double power =
      (engineRunning ? spec.powertrain.systemPowerW : spec.powertrain.motorPowerW) *
      spec.powertrain.drivelineEfficiency;
  if (!(spec.powertrain.maxWheelForceN > 0.0)) return 0.0;
  return power / spec.powertrain.maxWheelForceN;
}

double tractiveForceN(const VehicleSpec& spec, double speedMps, double throttle, bool engineRunning) {
  const double t = clamp01(throttle);
  if (t <= 0.0) return 0.0;
  const double power =
      (engineRunning ? spec.powertrain.systemPowerW : spec.powertrain.motorPowerW) *
      spec.powertrain.drivelineEfficiency;
  const double v = std::fmax(std::fabs(speedMps), kSpeedEpsMps);
  const double byPower = power / v;
  const double f = byPower < spec.powertrain.maxWheelForceN ? byPower : spec.powertrain.maxWheelForceN;
  return f * t;
}

double rollingResistanceN(const VehicleSpec& spec, double massKg, double speedMps) {
  if (std::fabs(speedMps) < 1e-6) return 0.0;
  return spec.tyre.rollingResistanceCoefficient * massKg * kGravity;
}

double aeroDragN(const VehicleSpec& spec, double speedMps) {
  return 0.5 * spec.aero.airDensityKgM3 * spec.aero.dragCoefficient * spec.aero.frontalAreaM2 *
         speedMps * std::fabs(speedMps);
}

double gradeForceN(double massKg, double gradeRad) { return massKg * kGravity * std::sin(gradeRad); }

double longitudinalAccelMps2(const VehicleSpec& spec, double speedMps, double throttle, double mu,
                             double gradeRad, bool engineRunning) {
  const double massKg = spec.mass.testMassKg();
  double f = tractiveForceN(spec, speedMps, throttle, engineRunning);
  // Traction limit of the driven axle.
  const double aMax = tractionLimitedAccelMps2(mu, spec.mass.frontWeightFraction, spec.mass.cgHeightM,
                                               spec.dimensions.wheelbaseM);
  const double fMax = aMax * massKg * spec.mass.rotatingInertiaFactor;
  if (f > fMax) f = fMax;
  const double resistance = rollingResistanceN(spec, massKg, speedMps) + aeroDragN(spec, speedMps) +
                            gradeForceN(massKg, gradeRad);
  return (f - resistance) / (massKg * spec.mass.rotatingInertiaFactor);
}

double steadyTopSpeedMps(const VehicleSpec& spec, double mu) {
  double lo = 0.0;
  double hi = spec.powertrain.topSpeedMps;
  auto surplus = [&](double v) { return longitudinalAccelMps2(spec, v, 1.0, mu, 0.0, true); };
  if (surplus(hi) > 0.0) return hi;  // limiter, not drag, is the constraint
  for (int i = 0; i < 100; ++i) {
    const double mid = 0.5 * (lo + hi);
    if (surplus(mid) > 0.0) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  return 0.5 * (lo + hi);
}

}  // namespace vehicle
}  // namespace nycsim
