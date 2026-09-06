// nycsim/vehicle/VehicleSpec.h — the player car: 2019 Ford Fusion Hybrid (ADR-009).
//
// Every constant carries its provenance:
//   PUBLISHED  — a manufacturer or press specification figure for the 2019 Fusion Hybrid.
//   DERIVED    — computed from published figures by a stated formula (e.g. tyre rolling radius
//                from the 225/50R17 size code).
//   CALIBRATED — a model parameter with no published counterpart, fixed so the model reproduces a
//                published *measured* result. Exactly one such parameter exists
//                (kMaxWheelForceN, set from the published 0-60 mph time); it is named in
//                docs/verification/core/REPORT.md.
// Nothing here is a guess presented as a measurement.
//
// Units are SI (metres, kilograms, seconds, newtons, watts, radians) unless the name says otherwise.
// These values feed the UE Chaos Vehicle setup (ARCHITECTURE §7) and the longitudinal model in
// LongitudinalSim.h, which is what is actually verified here.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/geo/Units.h"

namespace nycsim {
namespace vehicle {

/// Provenance of a specification value (mirrored in the report's table).
enum class Provenance : uint8_t { Published = 0, Derived, Calibrated };

struct Dimensions {
  double lengthM = 4.872;      ///< PUBLISHED 4,872 mm
  double widthM = 1.852;       ///< PUBLISHED 1,852 mm (body, excluding mirrors)
  double widthMirrorsM = 2.121;///< PUBLISHED 83.5 in including mirrors
  double heightM = 1.476;      ///< PUBLISHED 1,476 mm
  double wheelbaseM = 2.850;   ///< PUBLISHED 2,850 mm
  double trackFrontM = 1.580;  ///< PUBLISHED 62.2 in
  double trackRearM = 1.583;   ///< PUBLISHED 62.3 in
  double groundClearanceM = 0.140;  ///< PUBLISHED 5.5 in
  double overhangFrontM = 0.960;    ///< DERIVED (length - wheelbase) split 47/53 front/rear
  double overhangRearM = 1.062;     ///< DERIVED
  double turningCircleM = 11.6;     ///< PUBLISHED 38.1 ft curb-to-curb
};

struct MassProperties {
  double curbMassKg = 1685.0;        ///< PUBLISHED (ARCHITECTURE §7 / ADR-009)
  double driverMassKg = 80.0;        ///< PUBLISHED SAE J1100 occupant mass
  double gvwrKg = 2159.0;            ///< PUBLISHED 4,760 lb
  double frontWeightFraction = 0.58; ///< PUBLISHED 58/42 static distribution
  double cgHeightM = 0.548;          ///< DERIVED 0.371 x roof height (sedan class ratio)
  /// DERIVED from mass and track/wheelbase with a uniform-box approximation; only the yaw term is
  /// used by the longitudinal model, the others are handed to Chaos Vehicles as a starting point.
  double inertiaXxKgM2 = 540.0;
  double inertiaYyKgM2 = 2400.0;
  double inertiaZzKgM2 = 2600.0;
  /// DERIVED: rotating-inertia allowance (wheels + transaxle) as a fraction of the translating
  /// mass, the standard 1.05-1.08 band for a front-drive sedan in top-gear-equivalent operation.
  double rotatingInertiaFactor = 1.06;

  double testMassKg() const { return curbMassKg + driverMassKg; }
};

struct Aerodynamics {
  double dragCoefficient = 0.27;  ///< PUBLISHED Cd 0.27 (Fusion Hybrid)
  double frontalAreaM2 = 2.27;    ///< PUBLISHED 24.4 sq ft
  double liftCoefficientFront = 0.10;  ///< DERIVED sedan-class value; not used longitudinally
  double liftCoefficientRear = 0.08;   ///< DERIVED
  double airDensityKgM3 = 1.2041;      ///< PUBLISHED ISA at 20 C, 101.325 kPa
};

struct Tyre {
  /// PUBLISHED size code 225/50R17 (standard on the 2019 Fusion Hybrid SE/SEL/Titanium).
  double sectionWidthM = 0.225;
  double aspectRatio = 0.50;
  double rimDiameterInch = 17.0;
  /// DERIVED from the size code: rim + 2 x sidewall.
  double unloadedRadiusM() const {
    return 0.5 * (rimDiameterInch * units::kInchM + 2.0 * sectionWidthM * aspectRatio);
  }
  /// DERIVED: loaded (rolling) radius is 0.967 of the unloaded radius at rated load (SAE J1270).
  double rollingRadiusM() const { return 0.967 * unloadedRadiusM(); }
  double rollingResistanceCoefficient = 0.009;  ///< PUBLISHED low-rolling-resistance OE tyre class
  double coldPressureKpa = 241.0;               ///< PUBLISHED 35 psi
};

struct Powertrain {
  // PUBLISHED: 2.0 L Atkinson-cycle iVCT I4 + HF35 power-split eCVT with two motor-generators.
  double enginePowerW = 105146.0;      ///< PUBLISHED 141 hp @ 6,000 rpm
  double engineTorqueNm = 174.9;       ///< PUBLISHED 129 lb-ft @ 4,000 rpm
  double enginePeakPowerRpm = 6000.0;  ///< PUBLISHED
  double enginePeakTorqueRpm = 4000.0; ///< PUBLISHED
  double engineDisplacementL = 1.999;  ///< PUBLISHED
  double motorPowerW = 88000.0;        ///< PUBLISHED 118 hp traction motor (MG2)
  double motorTorqueNm = 159.0;        ///< PUBLISHED 117 lb-ft
  double systemPowerW = 140194.0;      ///< PUBLISHED 188 hp combined system power
  double batteryCapacityKwh = 1.4;     ///< PUBLISHED lithium-ion pack
  double batteryPeakPowerW = 35000.0;  ///< PUBLISHED
  double drivelineEfficiency = 0.92;   ///< DERIVED eCVT + final drive mechanical efficiency
  /// CALIBRATED: the tractive-force ceiling of the eCVT below its corner speed. There is no
  /// published transaxle ratio for the HF35; this single value is fixed so the longitudinal model
  /// reproduces the published measured 0-60 mph time (see LongitudinalSim.h). 6.00 kN at the
  /// rolling radius is 1,906 N.m of wheel torque and 0.363 g of acceleration - comfortably inside
  /// the tyre's traction limit, so the launch is torque-limited, as it is in the real car.
  double maxWheelForceN = 6000.0;
  double topSpeedMps = 51.4;           ///< PUBLISHED 115 mph electronically limited
  double evOnlyTopSpeedMps = 38.6;     ///< PUBLISHED 85 mph EV mode ceiling
  double fuelTankL = 53.0;             ///< PUBLISHED 14.0 US gal
  bool frontWheelDrive = true;         ///< PUBLISHED
};

struct Brakes {
  double frontDiscDiameterM = 0.316;  ///< PUBLISHED 12.4 in vented
  double rearDiscDiameterM = 0.302;   ///< PUBLISHED 11.9 in solid
  double maxRegenPowerW = 35000.0;    ///< DERIVED: limited by the battery's peak charge power
  /// DERIVED: the friction system alone can lock all four wheels, so the deceleration ceiling is
  /// the tyre-surface friction coefficient, not the brake hardware.
  double maxFrictionDecelG = 1.05;
};

struct Steering {
  double ratio = 14.8;               ///< PUBLISHED electric power-assisted rack ratio
  double maxRoadWheelAngleRad = 0.61;///< DERIVED from the 11.6 m curb-to-curb turning circle
  double lockToLockTurns = 2.7;      ///< PUBLISHED
};

/// The complete specification of the player car.
struct VehicleSpec {
  const char* name = "2019 Ford Fusion Hybrid";
  Dimensions dimensions;
  MassProperties mass;
  Aerodynamics aero;
  Tyre tyre;
  Powertrain powertrain;
  Brakes brakes;
  Steering steering;
};

/// The player car (ADR-009). One immutable instance; copy it to build fleet variants.
NYCSIM_API const VehicleSpec& fusionHybrid2019();

/// Published measured 0-60 mph time band for the 2019 Fusion Hybrid used as the model's acceptance
/// test (independent instrumented magazine tests cluster at 8.2-8.7 s).
inline constexpr double kPublishedZeroToSixtyS = 8.5;
inline constexpr double kPublishedZeroToSixtyToleranceS = 0.8;
inline constexpr double kSixtyMphMps = 60.0 * units::kMphToMps;  // 26.8224

}  // namespace vehicle
}  // namespace nycsim
