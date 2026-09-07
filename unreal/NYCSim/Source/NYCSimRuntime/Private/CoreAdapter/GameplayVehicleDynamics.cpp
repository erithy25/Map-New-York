#include "CoreAdapter/GameplayVehicleDynamics.h"

#include <algorithm>
#include <cmath>

namespace nycsim_gameplay
{

namespace
{
constexpr float kPi = 3.14159265358979323846f;

float clamp01(float v)
{
	return v < 0.f ? 0.f : (v > 1.f ? 1.f : v);
}
}  // namespace

// ------------------------------------------------------------------------------------------- PlayerVehicleSpec

float PlayerVehicleSpec::torqueAtRpm(float rpm) const
{
	const float step = maxRpm / 6.f;  // seven samples, six intervals
	if (!(rpm > 0.f))
	{
		return torqueCurveNm[0];
	}
	if (rpm >= maxRpm)
	{
		return torqueCurveNm[6];
	}
	const float pos = rpm / step;
	const int i = static_cast<int>(pos);
	const int i0 = std::min(i, 5);
	const float f = pos - static_cast<float>(i0);
	return torqueCurveNm[i0] + (torqueCurveNm[i0 + 1] - torqueCurveNm[i0]) * f;
}

float PlayerVehicleSpec::speedAtRpm(float rpm) const
{
	const float wheelRps = rpm / 60.f / finalDriveRatio;
	return wheelRps * 2.f * kPi * wheelRadiusM();
}

float PlayerVehicleSpec::rpmAtSpeed(float speedMps) const
{
	const float circumference = 2.f * kPi * wheelRadiusM();
	if (circumference <= 0.f)
	{
		return electricIdleRpm;
	}
	const float rpm = std::fabs(speedMps) / circumference * 60.f * finalDriveRatio;
	return std::clamp(rpm, electricIdleRpm, maxRpm);
}

float PlayerVehicleSpec::dragForceN(float speedMps) const
{
	constexpr float kAirDensity = 1.225f;
	return 0.5f * kAirDensity * dragCoefficient * frontalAreaM2 * speedMps * std::fabs(speedMps);
}

// ------------------------------------------------------------------------------------------ TyreFrictionModel

TyreFrictionModel::TyreFrictionModel()
{
	// Peak longitudinal friction coefficients. The six values ARCHITECTURE §7 fixes are used verbatim
	// (dry asphalt 1.0, wet 0.7, steel plate 0.55 wet, painted marking 0.6 wet, snow 0.3, ice 0.15).
	// Every surface that core's nycsim/vehicle/Friction.h also carries now holds core's value — the self-test
	// asserts them against frictionTable() so the two tables cannot drift. Default, Grass, Sidewalk and Water
	// have no core counterpart (they are UE physical-material slots, not DATA_CONTRACTS §7 road surfaces) and
	// keep the values documented in docs/verification/unreal_gameplay/REPORT.md.
	//                                                       dry    wet    roll  roughness (m RMS)  name
	table_[static_cast<int>(SurfaceClass::Default)]        = {1.00f, 0.70f, 1.00f, 0.0040f, "default"};
	table_[static_cast<int>(SurfaceClass::Asphalt)]        = {1.00f, 0.70f, 1.00f, 0.0045f, "asphalt"};
	table_[static_cast<int>(SurfaceClass::Concrete)]       = {0.95f, 0.65f, 0.98f, 0.0030f, "concrete"};
	// Belgian block: high dry grip, poor wet grip, and by far the roughest ride in the city.
	table_[static_cast<int>(SurfaceClass::Cobble)]         = {0.75f, 0.50f, 1.25f, 0.0180f, "cobble"};
	// Construction plates and bridge grating: §7 gives 0.55 wet.
	table_[static_cast<int>(SurfaceClass::SteelPlate)]     = {0.75f, 0.55f, 0.95f, 0.0060f, "steel plate"};
	// Thermoplastic markings and crosswalk paint: §7 gives 0.6 wet.
	table_[static_cast<int>(SurfaceClass::PaintedMarking)] = {0.90f, 0.60f, 1.00f, 0.0035f, "painted marking"};
	table_[static_cast<int>(SurfaceClass::Gravel)]         = {0.55f, 0.45f, 1.60f, 0.0140f, "gravel"};
	table_[static_cast<int>(SurfaceClass::Boardwalk)]      = {0.70f, 0.45f, 1.10f, 0.0110f, "boardwalk"};
	table_[static_cast<int>(SurfaceClass::Grass)]          = {0.55f, 0.42f, 2.10f, 0.0160f, "grass"};
	table_[static_cast<int>(SurfaceClass::Sidewalk)]       = {0.95f, 0.65f, 1.05f, 0.0055f, "sidewalk"};
	// Driving into the water is not a driving surface; the value keeps the solver stable if a wheel gets there.
	table_[static_cast<int>(SurfaceClass::Water)]          = {0.25f, 0.20f, 3.00f, 0.0100f, "water"};
	// Manhole covers, subway grates, trench plates.
	table_[static_cast<int>(SurfaceClass::Metal)]          = {0.75f, 0.55f, 0.95f, 0.0070f, "metal"};
	table_[static_cast<int>(SurfaceClass::Snow)]           = {0.30f, 0.30f, 1.80f, 0.0090f, "snow"};
	table_[static_cast<int>(SurfaceClass::Ice)]            = {0.15f, 0.15f, 1.10f, 0.0030f, "ice"};
}

const SurfaceFriction& TyreFrictionModel::surface(SurfaceClass s) const
{
	const int i = static_cast<int>(s);
	return table_[(i >= 0 && i < static_cast<int>(SurfaceClass::Count)) ? i : 0];
}

float TyreFrictionModel::peakFriction(SurfaceClass s, float wetness, float snowCover, float iceCover) const
{
	const SurfaceFriction& f = surface(s);
	const float w = clamp01(wetness);
	const float snow = clamp01(snowCover);
	const float ice = clamp01(iceCover);

	// A thin film reaches most of the wet loss quickly, then saturates: sqrt() shapes the first millimetre.
	float mu = f.dry + (f.wet - f.dry) * std::sqrt(w);

	// Lying snow and ice are their own contact surface, blended in by coverage.
	const float snowMu = table_[static_cast<int>(SurfaceClass::Snow)].dry;
	const float iceMu = table_[static_cast<int>(SurfaceClass::Ice)].dry;
	mu = mu * (1.f - snow) + snowMu * snow;
	mu = mu * (1.f - ice) + iceMu * ice;

	return std::clamp(mu, 0.08f, 1.35f);
}

float TyreFrictionModel::frictionMultiplier(SurfaceClass s, float wetness, float snowCover, float iceCover) const
{
	const float ref = referenceDryPeak();
	if (ref <= 0.f)
	{
		return 1.f;
	}
	return peakFriction(s, wetness, snowCover, iceCover) / ref;
}

float TyreFrictionModel::rollingResistance(SurfaceClass s, float wetness, float snowCover) const
{
	// Base coefficient for a passenger radial on asphalt (SAE J2452 range 0.010–0.013).
	constexpr float kBase = 0.011f;
	const SurfaceFriction& f = surface(s);
	const float w = clamp01(wetness);
	const float snow = clamp01(snowCover);
	// Standing water and lying snow add drag on top of the surface's own rolling resistance.
	const float weather = 1.f + 0.25f * w + 1.20f * snow;
	return kBase * f.rollingResistance * weather;
}

float TyreFrictionModel::aquaplaneSpeedMps(float waterDepthMm, float tyrePressureKpa) const
{
	if (waterDepthMm <= 0.05f)
	{
		return 1.0e6f;  // dry or damp: no dynamic aquaplaning
	}
	const float psi = std::max(5.f, tyrePressureKpa) * 0.145038f;
	const float d = std::max(0.05f, waterDepthMm);
	// Horne & Dreher (NASA TN D-2056, 1963): full dynamic hydroplaning at v_p [mph] = 10.35·√p(psi) once the
	// water film is deep enough to stop draining through the tread (≈ 2.5 mm for a passenger radial). Shallower
	// films raise the threshold; the exponent 0.26 matches the depth trend Gallaway et al. (FHWA-RD-75-11)
	// measured on 225-section tyres.
	float mph = 10.35f * std::sqrt(psi);
	if (d < 2.5f)
	{
		mph *= std::pow(2.5f / d, 0.26f);
	}
	return mph * 0.44704f;
}

}  // namespace nycsim_gameplay
