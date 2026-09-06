#include "nycsim/vehicle/LongitudinalSim.h"

#include <cmath>

namespace nycsim {
namespace vehicle {

namespace {
constexpr double kGravity = 9.80665;
}  // namespace

double stepSpeed(const VehicleSpec& spec, double speedMps, double throttle,
                 const DriveConditions& cond, double dtS) {
  const double mu = cond.mu();
  auto accel = [&](double v) {
    return longitudinalAccelMps2(spec, v, throttle, mu, cond.gradeRad, cond.engineRunning);
  };
  const double k1 = accel(speedMps);
  const double k2 = accel(speedMps + 0.5 * dtS * k1);
  const double k3 = accel(speedMps + 0.5 * dtS * k2);
  const double k4 = accel(speedMps + dtS * k3);
  return speedMps + dtS / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4);
}

Result<AccelResult> accelerationRun(const VehicleSpec& spec, double fromMps, double toMps,
                                    const DriveConditions& cond, double dtS, double maxTimeS) {
  if (!(dtS > 0.0) || !std::isfinite(dtS)) {
    return fail(ErrorCode::InvalidArgument, "vehicle: non-positive integration step");
  }
  if (!(toMps > fromMps)) {
    return fail(ErrorCode::InvalidArgument, "vehicle: acceleration target below the start speed");
  }
  const double mu = cond.mu();
  AccelResult r;
  double v = fromMps;
  double t = 0.0;
  double x = 0.0;
  while (t < maxTimeS) {
    const double a = longitudinalAccelMps2(spec, v, 1.0, mu, cond.gradeRad, cond.engineRunning);
    if (a > r.peakAccelMps2) r.peakAccelMps2 = a;
    if (a <= 0.0 && v < toMps) {
      return fail(ErrorCode::NoConvergence,
                  "vehicle: the car cannot accelerate further under these conditions");
    }
    const double vNext = stepSpeed(spec, v, 1.0, cond, dtS);
    if (vNext >= toMps) {
      // Linear interpolation inside the last step for a step-size-independent answer.
      const double frac = (toMps - v) / (vNext - v);
      x += 0.5 * (v + toMps) * dtS * frac;
      t += dtS * frac;
      v = toMps;
      r.reachedTarget = true;
      break;
    }
    x += 0.5 * (v + vNext) * dtS;
    v = vNext;
    t += dtS;
  }
  r.timeS = t;
  r.distanceM = x;
  r.finalSpeedMps = v;
  if (!r.reachedTarget) {
    return fail(ErrorCode::NoConvergence, "vehicle: target speed not reached within the time limit");
  }
  return r;
}

Result<double> zeroToSixtyS(const VehicleSpec& spec, const DriveConditions& cond) {
  NYCSIM_TRY(r, accelerationRun(spec, 0.0, kSixtyMphMps, cond));
  return r.timeS;
}

BrakingResult brakingRun(const VehicleSpec& spec, double fromMps, const DriveConditions& cond,
                         double dtS) {
  BrakingResult out;
  if (!(fromMps > 0.0) || !(dtS > 0.0)) return out;
  const double mu = cond.mu();
  // All four wheels brake, so the deceleration ceiling is mu*g capped by the friction system.
  const double aBrake = std::fmin(mu * kGravity, spec.brakes.maxFrictionDecelG * kGravity);
  const double massKg = spec.mass.testMassKg();
  double v = fromMps;
  double t = 0.0;
  double x = 0.0;
  while (v > 0.0 && t < 60.0) {
    const double resist =
        (rollingResistanceN(spec, massKg, v) + aeroDragN(spec, v) + gradeForceN(massKg, cond.gradeRad)) /
        (massKg * spec.mass.rotatingInertiaFactor);
    const double a = aBrake + resist;
    const double vNext = std::fmax(0.0, v - a * dtS);
    x += 0.5 * (v + vNext) * dtS;
    t += dtS;
    v = vNext;
  }
  out.distanceM = x;
  out.timeS = t;
  out.meanDecelMps2 = t > 0.0 ? fromMps / t : 0.0;
  return out;
}

}  // namespace vehicle
}  // namespace nycsim
