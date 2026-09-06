// GameplayVehicleDynamics — the player car's published specification and its tyre-friction model.
//
// Pure C++ (std only, no Unreal): this is the data that ARCHITECTURE §7 fixes for the player vehicle, expressed
// once so that the Chaos setup (NYCVehicleMovementComponent), the audio synthesiser (NYCVehicleAudioComponent)
// and the standalone self-test all read the same numbers.
//
// `core/include/nycsim/vehicle/VehicleSpec.h` landed on 2026-09-06 and is authoritative for every published and
// derived figure of the 2019 Fusion Hybrid. This struct is the UE-facing translation of
// `nycsim::vehicle::fusionHybrid2019()`: every field below that core also carries now holds core's value, and
// unreal/tools/gameplay_selftest.cpp asserts them field by field against `fusionHybrid2019()`, so the two cannot
// drift apart silently. The remaining fields are the ones core does not model (steering-wheel travel for the
// SteeringWheel bone, suspension frequency for the Chaos setup, per-axle brake torques, and the engine torque
// curve the audio synthesiser needs); each carries its own derivation. The differences between core's
// longitudinal model and this one are listed in docs/verification/unreal_gameplay/REPORT.md.
#pragma once

#include <cstdint>

namespace nycsim_gameplay
{

/// Surface classes, in the order of the [/Script/Engine.PhysicsSettings] PhysicalSurfaces block in
/// Config/DefaultEngine.ini (SurfaceType1..13). `Default` is EPhysicalSurface::SurfaceType_Default (no material).
enum class SurfaceClass : uint8_t
{
	Default = 0,
	Asphalt = 1,
	Concrete = 2,
	Cobble = 3,
	SteelPlate = 4,
	PaintedMarking = 5,
	Gravel = 6,
	Boardwalk = 7,
	Grass = 8,
	Sidewalk = 9,
	Water = 10,
	Metal = 11,
	Snow = 12,
	Ice = 13,
	Count
};

/// Peak longitudinal tyre friction coefficient for one surface, dry and soaked.
struct SurfaceFriction
{
	float dry = 1.0f;
	float wet = 0.7f;
	/// Rolling resistance multiplier relative to asphalt (gravel and grass drag more).
	float rollingResistance = 1.0f;
	/// Amplitude of the road-roughness excitation this surface feeds into the suspension, metres RMS.
	float roughnessM = 0.004f;
	const char* name = "asphalt";
};

/// Published specification of the player car (ADR-009: 2019 Ford Fusion Hybrid SE).
struct PlayerVehicleSpec
{
	// Body (Ford 2019 Fusion order guide; millimetres in the source, metres here).
	float lengthM = 4.872f;
	float widthM = 1.852f;          ///< body without mirrors
	float widthMirrorsM = 2.121f;   ///< mirrors extended
	float heightM = 1.476f;
	float wheelbaseM = 2.850f;
	float trackFrontM = 1.580f;   ///< core PUBLISHED 62.2 in
	float trackRearM = 1.583f;    ///< core PUBLISHED 62.3 in
	float groundClearanceM = 0.140f;
	float massKg = 1685.f;          ///< curb mass, hybrid trim
	float frontMassShare = 0.58f;   ///< core PUBLISHED 58/42 static distribution
	float cogHeightM = 0.548f;      ///< core DERIVED 0.371 x roof height
	float dragCoefficient = 0.27f;  ///< core PUBLISHED Cd
	float frontalAreaM2 = 2.27f;    ///< core PUBLISHED 24.4 sq ft

	// Tyres: 225/50R17 (SE Hybrid standard fitment).
	float tyreWidthM = 0.225f;
	float tyreAspect = 0.50f;
	float rimDiameterInch = 17.f;
	/// Rolling (loaded) radius. SAE J1270 puts it at 0.967 of the unloaded radius at rated load, which is what
	/// core's Tyre::rollingRadiusM() uses; this is the same formula on the same size code.
	float wheelRadiusM() const
	{
		const float unloaded = 0.5f * (rimDiameterInch * 0.0254f + 2.f * tyreWidthM * tyreAspect);
		return unloaded * 0.967f;
	}

	// Hybrid powertrain: 2.0 L Atkinson I4 + 88 kW traction motor, 188 hp (140 kW) combined, eCVT, FWD.
	float maxRpm = 6000.f;
	float idleRpm = 0.f;            ///< a hybrid idles the engine off; the audio model uses electricIdleRpm
	float electricIdleRpm = 750.f;  ///< engine speed the ICE assumes when it starts under load
	float engineMoiKgM2 = 0.20f;
	/// Combined-system torque at the crankshaft-equivalent shaft, Nm, sampled every 1000 rpm from 0 to 6000.
	/// 140 kW peak occurs at 5000 rpm (267 Nm), matching the published 188 hp.
	float torqueCurveNm[7] = {260.f, 300.f, 300.f, 290.f, 280.f, 267.f, 220.f};
	/// Single-ratio eCVT reduction: 6000 rpm ↔ 45.8 m/s (165 km/h) on the standard tyre.
	float finalDriveRatio = 4.50f;
	float reverseRatio = 4.50f;
	float transmissionEfficiency = 0.94f;

	// Brakes and steering.
	float maxBrakeTorqueFrontNm = 2200.f;
	float maxBrakeTorqueRearNm = 1400.f;
	float handbrakeTorqueNm = 1600.f;
	float maxSteerAngleDeg = 35.f;      ///< at the road wheel, lock-to-lock 2.7 turns
	float steerAngleAt100KphDeg = 9.f;  ///< speed-sensitive steering limit
	float steeringWheelLockDeg = 486.f; ///< 2.7 turns × 360 / 2 to each side, used by the SteeringWheel bone

	// Suspension (MacPherson front, integral-link rear).
	float suspensionTravelM = 0.16f;
	float suspensionNaturalFrequencyHz = 1.35f;
	float suspensionDampingRatio = 0.42f;

	// Fuel / energy.
	float fuelTankLitres = 53.f;
	float batteryKwh = 1.4f;
	/// Combined EPA rating 42 mpg → litres per 100 km.
	float combinedLPer100km = 5.6f;

	/// Torque at an arbitrary engine speed, linearly interpolated inside the sampled curve.
	float torqueAtRpm(float rpm) const;
	/// Road speed (m/s) at an engine speed in the single forward ratio.
	float speedAtRpm(float rpm) const;
	/// Engine speed for a road speed (clamped to [electricIdleRpm, maxRpm]).
	float rpmAtSpeed(float speedMps) const;
	/// Aerodynamic drag force (N) at a road speed, sea-level air density 1.225 kg/m³.
	float dragForceN(float speedMps) const;
};

/// The friction table. `wetness` and `snow` come from the MPC_Weather material parameter collection that the
/// weather subsystem drives (0..1 each); `ice` is set when the surface temperature is below freezing and the road
/// is wet, which is what the weather model reports as freezing rain / black ice.
class TyreFrictionModel
{
public:
	TyreFrictionModel();

	const SurfaceFriction& surface(SurfaceClass s) const;

	/// Peak friction coefficient for a surface under the current weather.
	/// wetness/snowCover/iceCover are clamped to [0,1]; snow and ice override the wet blend because they sit on
	/// top of the surface. Result is clamped to [0.08, 1.35].
	float peakFriction(SurfaceClass s, float wetness, float snowCover, float iceCover) const;

	/// Multiplier applied to the Chaos wheel friction (1.0 = the wheel's authored dry-asphalt grip).
	float frictionMultiplier(SurfaceClass s, float wetness, float snowCover, float iceCover) const;

	/// Longitudinal rolling-resistance coefficient (dimensionless) for the surface under the weather.
	float rollingResistance(SurfaceClass s, float wetness, float snowCover) const;

	/// Speed (m/s) above which a 225/50R17 tyre aquaplanes on `waterDepthMm` of standing water.
	/// Gallaway/NASA form v = 6.36 × p^0.21 × d^-0.44 (p in psi, d in mm) — returns a large value in the dry.
	float aquaplaneSpeedMps(float waterDepthMm, float tyrePressureKpa) const;

	/// Reference dry-asphalt peak used to normalise the multipliers.
	float referenceDryPeak() const { return table_[static_cast<int>(SurfaceClass::Asphalt)].dry; }

private:
	SurfaceFriction table_[static_cast<int>(SurfaceClass::Count)];
};

}  // namespace nycsim_gameplay
