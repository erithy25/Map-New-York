#include <doctest/doctest.h>

#include <cmath>
#include <string>

#include "nycsim/geo/Units.h"
#include "nycsim/vehicle/Friction.h"
#include "nycsim/vehicle/LongitudinalSim.h"
#include "nycsim/vehicle/Powertrain.h"
#include "nycsim/vehicle/VehicleSpec.h"

using namespace nycsim;
using namespace nycsim::vehicle;

TEST_SUITE("vehicle") {
  TEST_CASE("2019 Ford Fusion Hybrid published dimensions and masses (ADR-009)") {
    const VehicleSpec& v = fusionHybrid2019();
    CHECK(std::string(v.name) == "2019 Ford Fusion Hybrid");
    // ARCHITECTURE §7 states the four figures the whole project is keyed to.
    CHECK(v.dimensions.lengthM == doctest::Approx(4.872));
    CHECK(v.dimensions.widthM == doctest::Approx(1.852));
    CHECK(v.dimensions.heightM == doctest::Approx(1.476));
    CHECK(v.dimensions.wheelbaseM == doctest::Approx(2.850));
    CHECK(v.mass.curbMassKg == doctest::Approx(1685.0));
    // Internal consistency of the derived geometry.
    CHECK(v.dimensions.overhangFrontM + v.dimensions.wheelbaseM + v.dimensions.overhangRearM ==
          doctest::Approx(v.dimensions.lengthM).epsilon(1e-9));
    CHECK(v.dimensions.widthMirrorsM > v.dimensions.widthM);
    CHECK(v.mass.gvwrKg > v.mass.testMassKg());
    CHECK(v.mass.testMassKg() == doctest::Approx(1765.0));
    CHECK(v.mass.frontWeightFraction > 0.5);
    CHECK(v.mass.frontWeightFraction < 0.65);
    CHECK(v.mass.cgHeightM < v.dimensions.heightM * 0.5);
    // Tyre geometry derived from the 225/50R17 size code.
    CHECK(v.tyre.unloadedRadiusM() == doctest::Approx(0.3284).epsilon(1e-3));
    CHECK(v.tyre.rollingRadiusM() == doctest::Approx(0.3176).epsilon(1e-3));
    CHECK(v.tyre.rollingRadiusM() < v.tyre.unloadedRadiusM());
    // Powertrain: the combined system figure is not the sum of the two sources (power split).
    CHECK(v.powertrain.systemPowerW == doctest::Approx(140194.0));
    CHECK(v.powertrain.systemPowerW / units::kHpToW == doctest::Approx(188.0).epsilon(1e-3));
    CHECK(v.powertrain.enginePowerW / units::kHpToW == doctest::Approx(141.0).epsilon(1e-3));
    CHECK(v.powertrain.motorPowerW / units::kHpToW == doctest::Approx(118.0).epsilon(2e-3));
    CHECK(v.powertrain.systemPowerW < v.powertrain.enginePowerW + v.powertrain.motorPowerW);
    CHECK(v.powertrain.frontWheelDrive);
    CHECK(v.powertrain.topSpeedMps == doctest::Approx(51.4));
    CHECK(v.powertrain.evOnlyTopSpeedMps < v.powertrain.topSpeedMps);
    CHECK(v.aero.dragCoefficient == doctest::Approx(0.27));
    CHECK(v.aero.frontalAreaM2 == doctest::Approx(2.27));
    // The calibrated launch force is well inside the tyre's traction limit, i.e. the car is
    // torque-limited off the line, as the real one is.
    const double aTorque = v.powertrain.maxWheelForceN / (v.mass.testMassKg() * v.mass.rotatingInertiaFactor);
    const double aTraction = tractionLimitedAccelMps2(1.0, v.mass.frontWeightFraction, v.mass.cgHeightM,
                                                      v.dimensions.wheelbaseM);
    CHECK(aTorque < aTraction);
    CHECK(aTorque == doctest::Approx(3.4335).epsilon(1e-3));  // 0.350 g
  }

  TEST_CASE("tyre-surface friction table: the six ARCHITECTURE §7 values are exact") {
    CHECK(frictionTable(SurfaceClass::DryAsphalt).dry == 1.00);
    CHECK(frictionTable(SurfaceClass::WetAsphalt).dry == 0.70);
    CHECK(frictionTable(SurfaceClass::SteelPlateWet).dry == 0.55);
    CHECK(frictionTable(SurfaceClass::PaintedMarkingWet).dry == 0.60);
    CHECK(frictionTable(SurfaceClass::Snow).dry == 0.30);
    CHECK(frictionTable(SurfaceClass::Ice).dry == 0.15);
    // Those four whose name fixes the condition cannot be moved by a wetness blend.
    for (SurfaceClass s : {SurfaceClass::SteelPlateWet, SurfaceClass::PaintedMarkingWet,
                           SurfaceClass::Snow, SurfaceClass::Ice}) {
      INFO("surface ", surfaceClassName(s));
      CHECK(frictionTable(s).dry == frictionTable(s).wet);
      for (double w = 0.0; w <= 1.0; w += 0.25) {
        CHECK(frictionFor(s, w, 0.0, 0.0) == doctest::Approx(frictionTable(s).dry));
      }
    }
    // Dry asphalt blends to exactly the wet-asphalt value at full wetness.
    CHECK(frictionFor(SurfaceClass::DryAsphalt, 0.0, 0.0, 0.0) == doctest::Approx(1.00));
    CHECK(frictionFor(SurfaceClass::DryAsphalt, 1.0, 0.0, 0.0) == doctest::Approx(0.70));
    CHECK(frictionFor(SurfaceClass::DryAsphalt, 0.5, 0.0, 0.0) == doctest::Approx(0.85));
    // Snow cover and ice pull any surface towards their own coefficients.
    CHECK(frictionFor(SurfaceClass::DryAsphalt, 0.0, 1.0, 0.0) == doctest::Approx(0.30));
    CHECK(frictionFor(SurfaceClass::DryAsphalt, 0.0, 0.0, 1.0) == doctest::Approx(0.15));
    CHECK(frictionFor(SurfaceClass::Concrete, 0.0, 0.0, 1.0) == doctest::Approx(0.15));
    // Names and the normative/extension split.
    CHECK(std::string(surfaceClassName(SurfaceClass::DryAsphalt)) == "dry_asphalt");
    CHECK(std::string(surfaceClassName(SurfaceClass::BelgianBlock)) == "belgian_block");
    int normative = 0;
    for (int i = 0; i < static_cast<int>(SurfaceClass::Count); ++i) {
      const SurfaceClass s = static_cast<SurfaceClass>(i);
      if (isNormativeSurface(s)) ++normative;
      // Every coefficient is physically plausible and dry >= wet.
      CHECK(frictionTable(s).dry > 0.0);
      CHECK(frictionTable(s).dry <= 1.0);
      CHECK(frictionTable(s).wet > 0.0);
      CHECK(frictionTable(s).wet <= frictionTable(s).dry);
      // Arguments outside 0..1 are clamped, never extrapolated.
      CHECK(frictionFor(s, -5.0, 0.0, 0.0) == doctest::Approx(frictionTable(s).dry));
      CHECK(frictionFor(s, 5.0, 0.0, 0.0) == doctest::Approx(frictionTable(s).wet));
    }
    CHECK(normative == 6);
    CHECK(static_cast<int>(SurfaceClass::Count) == 13);
  }

  TEST_CASE("traction limit accounts for longitudinal load transfer") {
    const VehicleSpec& v = fusionHybrid2019();
    const double a = tractionLimitedAccelMps2(1.0, v.mass.frontWeightFraction, v.mass.cgHeightM,
                                              v.dimensions.wheelbaseM);
    // Front-drive: the driven axle unloads as the car accelerates, so a < mu*g*frontFraction.
    CHECK(a < 1.0 * 9.80665 * v.mass.frontWeightFraction);
    CHECK(a > 0.0);
    // Lower friction, lower limit; monotone in mu.
    double prev = 0.0;
    for (double mu : {0.15, 0.3, 0.55, 0.6, 0.7, 1.0}) {
      const double x = tractionLimitedAccelMps2(mu, 0.58, 0.548, 2.85);
      CHECK(x > prev);
      prev = x;
    }
    // Degenerate inputs give 0 rather than a NaN or an infinity.
    CHECK(tractionLimitedAccelMps2(0.0, 0.58, 0.548, 2.85) == 0.0);
    CHECK(tractionLimitedAccelMps2(1.0, 0.58, 0.548, 0.0) == 0.0);
  }

  TEST_CASE("powertrain: torque-limited below the corner speed, power-limited above it") {
    const VehicleSpec& v = fusionHybrid2019();
    const double vc = cornerSpeedMps(v);
    CHECK(vc == doctest::Approx(v.powertrain.systemPowerW * v.powertrain.drivelineEfficiency /
                                v.powertrain.maxWheelForceN));
    CHECK(vc > 15.0);
    CHECK(vc < 25.0);
    // Below the corner speed the force is flat at the ceiling.
    CHECK(tractiveForceN(v, 0.0) == doctest::Approx(v.powertrain.maxWheelForceN));
    CHECK(tractiveForceN(v, vc - 1.0) == doctest::Approx(v.powertrain.maxWheelForceN));
    // Above it, F*v is the constant wheel power.
    const double p1 = tractiveForceN(v, vc + 5.0) * (vc + 5.0);
    const double p2 = tractiveForceN(v, vc + 20.0) * (vc + 20.0);
    CHECK(p1 == doctest::Approx(p2).epsilon(1e-9));
    CHECK(p1 == doctest::Approx(v.powertrain.systemPowerW * v.powertrain.drivelineEfficiency));
    // Throttle scales linearly and is clamped.
    CHECK(tractiveForceN(v, 10.0, 0.5) == doctest::Approx(0.5 * tractiveForceN(v, 10.0, 1.0)));
    CHECK(tractiveForceN(v, 10.0, 0.0) == 0.0);
    CHECK(tractiveForceN(v, 10.0, -1.0) == 0.0);
    CHECK(tractiveForceN(v, 10.0, 5.0) == doctest::Approx(tractiveForceN(v, 10.0, 1.0)));
    // EV-only mode is weaker above the corner speed and identical below it.
    CHECK(tractiveForceN(v, 5.0, 1.0, false) == doctest::Approx(tractiveForceN(v, 5.0, 1.0, true)));
    CHECK(tractiveForceN(v, 30.0, 1.0, false) < tractiveForceN(v, 30.0, 1.0, true));
    // Resistances.
    CHECK(rollingResistanceN(v, v.mass.testMassKg(), 0.0) == 0.0);
    CHECK(rollingResistanceN(v, v.mass.testMassKg(), 10.0) ==
          doctest::Approx(0.009 * 1765.0 * 9.80665));
    CHECK(aeroDragN(v, 0.0) == 0.0);
    CHECK(aeroDragN(v, 30.0) == doctest::Approx(0.5 * 1.2041 * 0.27 * 2.27 * 900.0));
    CHECK(aeroDragN(v, 30.0) == doctest::Approx(4.0 * aeroDragN(v, 15.0)).epsilon(1e-9));
    CHECK(gradeForceN(1765.0, 0.0) == doctest::Approx(0.0));
    CHECK(gradeForceN(1765.0, 0.1) > 0.0);
    CHECK(gradeForceN(1765.0, -0.1) < 0.0);
  }

  TEST_CASE("0-60 mph is 8.5 +/- 0.8 s, the published measured figure") {
    const VehicleSpec& v = fusionHybrid2019();
    DriveConditions dry;  // dry asphalt, level
    const Result<double> t = zeroToSixtyS(v, dry);
    REQUIRE(t.ok());
    const double seconds = t.value();
    MESSAGE("0-60 mph = " << seconds << " s");
    CHECK(std::fabs(seconds - kPublishedZeroToSixtyS) <= kPublishedZeroToSixtyToleranceS);
    CHECK(seconds > 7.0);   // sanity: it is not a sports car
    CHECK(seconds < 10.0);  // sanity: it is not a bus
    // The answer must not depend on the integration step.
    const Result<AccelResult> fine = accelerationRun(v, 0.0, kSixtyMphMps, dry, 0.0002);
    const Result<AccelResult> coarse = accelerationRun(v, 0.0, kSixtyMphMps, dry, 0.005);
    REQUIRE(fine.ok());
    REQUIRE(coarse.ok());
    CHECK(fine.value().timeS == doctest::Approx(coarse.value().timeS).epsilon(2e-3));
    CHECK(fine.value().reachedTarget);
    CHECK(fine.value().finalSpeedMps == doctest::Approx(kSixtyMphMps));
    // Distance covered in a 0-60 run is the usual 100-130 m for this class.
    CHECK(fine.value().distanceM > 100.0);
    CHECK(fine.value().distanceM < 135.0);
    // Peak acceleration is the torque-limited launch value.
    CHECK(fine.value().peakAccelMps2 == doctest::Approx(3.4335).epsilon(0.02));
    // 0-30 mph is well under half the 0-60 time (the launch is torque-limited, then power-limited).
    const Result<AccelResult> half = accelerationRun(v, 0.0, 0.5 * kSixtyMphMps, dry);
    REQUIRE(half.ok());
    CHECK(half.value().timeS < 0.5 * seconds);
    CHECK(half.value().timeS > 0.35 * seconds);
  }

  TEST_CASE("0-60 mph degrades correctly on bad surfaces and grades") {
    const VehicleSpec& v = fusionHybrid2019();
    const double dry = zeroToSixtyS(v, DriveConditions()).value();
    DriveConditions wet;
    wet.surface = SurfaceClass::WetAsphalt;
    DriveConditions snow;
    snow.surface = SurfaceClass::PackedSnow;
    DriveConditions ice;
    ice.surface = SurfaceClass::Ice;
    // Wet asphalt (mu 0.70) still allows 0.4 g at the driven axle, so the launch stays
    // torque-limited and the time is unchanged. That is the physically correct answer.
    CHECK(zeroToSixtyS(v, wet).value() == doctest::Approx(dry).epsilon(1e-6));
    // Snow and ice bite: the traction limit is now below the torque ceiling.
    const Result<double> onSnow = zeroToSixtyS(v, snow);
    REQUIRE(onSnow.ok());
    CHECK(onSnow.value() > dry * 1.2);
    // On sheet ice (mu 0.15) the traction limit is 0.83 m/s^2, so 60 mph takes about 39 s: the
    // model reports the real (absurd) number rather than refusing or capping it.
    const Result<double> onIce = zeroToSixtyS(v, ice);
    REQUIRE(onIce.ok());
    CHECK(onIce.value() > 30.0);
    CHECK(onIce.value() < 50.0);
    // A 10 % grade slows it down; a steep enough grade stops it.
    DriveConditions hill;
    hill.gradeRad = std::atan(0.10);
    const Result<double> uphill = zeroToSixtyS(v, hill);
    REQUIRE(uphill.ok());
    CHECK(uphill.value() > dry);
    DriveConditions wall;
    wall.gradeRad = std::atan(0.45);
    CHECK_FALSE(zeroToSixtyS(v, wall).ok());
    // Degenerate arguments are rejected.
    CHECK_FALSE(accelerationRun(v, 0.0, kSixtyMphMps, DriveConditions(), 0.0).ok());
    CHECK_FALSE(accelerationRun(v, 30.0, 10.0, DriveConditions()).ok());
  }

  TEST_CASE("braking distances match the friction table") {
    const VehicleSpec& v = fusionHybrid2019();
    // 60 mph -> 0 on dry asphalt: v^2 / (2 mu g) = 26.8224^2 / (2 * 1.0 * 9.80665) = 36.7 m,
    // slightly shorter once drag and rolling resistance are included.
    DriveConditions dry;
    const BrakingResult d = brakingRun(v, kSixtyMphMps, dry);
    CHECK(d.distanceM < 36.7);
    CHECK(d.distanceM > 33.0);
    CHECK(d.meanDecelMps2 > 9.0);
    // Wet asphalt (mu 0.70) is about 1/0.7 = 1.43x longer.
    DriveConditions wet;
    wet.surface = SurfaceClass::WetAsphalt;
    const BrakingResult w = brakingRun(v, kSixtyMphMps, wet);
    CHECK(w.distanceM > d.distanceM * 1.30);
    CHECK(w.distanceM < d.distanceM * 1.50);
    // Ice (mu 0.15) is roughly 6.7x the dry distance.
    DriveConditions ice;
    ice.surface = SurfaceClass::Ice;
    const BrakingResult i = brakingRun(v, kSixtyMphMps, ice);
    CHECK(i.distanceM > d.distanceM * 5.5);
    CHECK(i.distanceM < d.distanceM * 7.5);
    // 30 mph stops in about a quarter of the 60 mph distance.
    const BrakingResult half = brakingRun(v, 0.5 * kSixtyMphMps, dry);
    CHECK(half.distanceM == doctest::Approx(d.distanceM / 4.0).epsilon(0.08));
    // Degenerate inputs.
    CHECK(brakingRun(v, 0.0, dry).distanceM == 0.0);
    CHECK(brakingRun(v, 10.0, dry, 0.0).distanceM == 0.0);
  }

  TEST_CASE("steady top speed is limited by the electronic limiter, not by drag") {
    const VehicleSpec& v = fusionHybrid2019();
    const double top = steadyTopSpeedMps(v, 1.0);
    // 140 kW at the wheels against Cd*A drag would carry the car past the 51.4 m/s limiter, so the
    // limiter is what the model reports.
    CHECK(top == doctest::Approx(v.powertrain.topSpeedMps));
    CHECK(top / units::kMphToMps == doctest::Approx(115.0).epsilon(0.01));
    // The published 85 mph EV-only ceiling is a control decision, not a physics limit: the 88 kW
    // traction motor alone still has surplus tractive force at 38.6 m/s.
    VehicleSpec ev = v;
    ev.powertrain.systemPowerW = ev.powertrain.motorPowerW;
    CHECK(longitudinalAccelMps2(ev, v.powertrain.evOnlyTopSpeedMps, 1.0, 1.0) > 0.0);
    // A genuinely underpowered variant is drag-limited below the limiter, and there the net
    // acceleration is zero - which is what steadyTopSpeedMps solves for.
    VehicleSpec weak = v;
    weak.powertrain.systemPowerW = 25000.0;
    const double weakTop = steadyTopSpeedMps(weak, 1.0);
    CHECK(weakTop < v.powertrain.topSpeedMps);
    CHECK(weakTop > 25.0);
    CHECK(std::fabs(longitudinalAccelMps2(weak, weakTop, 1.0, 1.0)) < 1e-3);
  }

  TEST_CASE("the longitudinal integrator is deterministic and energy-consistent") {
    const VehicleSpec& v = fusionHybrid2019();
    DriveConditions dry;
    // Same inputs, same outputs, bit for bit.
    const double a = zeroToSixtyS(v, dry).value();
    const double b = zeroToSixtyS(v, dry).value();
    CHECK(a == b);
    // Coasting from 30 m/s with no throttle decelerates monotonically and never reverses.
    double speed = 30.0;
    double prev = speed;
    for (int i = 0; i < 2000; ++i) {
      speed = stepSpeed(v, speed, 0.0, dry, 0.01);
      CHECK(speed <= prev + 1e-12);
      prev = speed;
      if (speed <= 0.0) break;
    }
    CHECK(speed < 30.0);
    // The work-energy balance over a 0-60 run: the tractive work equals the kinetic energy gained
    // plus the resistive work, to better than 0.5 %.
    const Result<AccelResult> r = accelerationRun(v, 0.0, kSixtyMphMps, dry, 0.0005);
    REQUIRE(r.ok());
    const double m = v.mass.testMassKg() * v.mass.rotatingInertiaFactor;
    double tractiveWork = 0.0;
    double resistiveWork = 0.0;
    double s = 0.0;
    double x = 0.0;
    const double dt = 0.0005;
    while (s < kSixtyMphMps) {
      const double f = std::fmin(tractiveForceN(v, s, 1.0),
                                 tractionLimitedAccelMps2(1.0, v.mass.frontWeightFraction,
                                                          v.mass.cgHeightM, v.dimensions.wheelbaseM) *
                                     m);
      const double res = rollingResistanceN(v, v.mass.testMassKg(), s) + aeroDragN(v, s);
      const double next = stepSpeed(v, s, 1.0, dry, dt);
      const double ds = 0.5 * (s + next) * dt;
      tractiveWork += f * ds;
      resistiveWork += res * ds;
      x += ds;
      s = next;
    }
    const double kinetic = 0.5 * m * kSixtyMphMps * kSixtyMphMps;
    CHECK(tractiveWork == doctest::Approx(kinetic + resistiveWork).epsilon(0.005));
    CHECK(x == doctest::Approx(r.value().distanceM).epsilon(0.01));
  }
}
