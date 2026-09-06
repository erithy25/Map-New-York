#include "Vehicle/NYCVehicleWheels.h"

#include "CoreAdapter/GameplayVehicleDynamics.h"

namespace
{
/// One shared instance so every wheel reads the same published specification.
const nycsim_gameplay::PlayerVehicleSpec& Spec()
{
	static const nycsim_gameplay::PlayerVehicleSpec Value;
	return Value;
}
}  // namespace

UNYCVehicleWheelBase::UNYCVehicleWheelBase()
{
	const nycsim_gameplay::PlayerVehicleSpec& S = Spec();

	// Geometry: metres in the spec, centimetres in Unreal.
	WheelRadius = S.wheelRadiusM() * 100.f;
	WheelWidth = S.tyreWidthM * 100.f;
	WheelMass = 22.f;  // 17" alloy + 225/50R17 tyre, kerb weight of one corner's unsprung rotating mass

	// Tyre model. FrictionForceMultiplier is the *authored dry-asphalt* grip; the movement component multiplies
	// the surface/weather factor into it every frame (UNYCVehicleMovementComponent::UpdateSurfaceGrip).
	FrictionForceMultiplier = 2.0f;
	CorneringStiffness = 1000.f;
	SideSlipModifier = 1.f;
	SlipThreshold = 20.f;
	SkidThreshold = 20.f;

	// Suspension: 1.35 Hz natural frequency, 0.42 damping ratio, 160 mm total travel (spec).
	SuspensionMaxRaise = S.suspensionTravelM * 100.f * 0.45f;
	SuspensionMaxDrop = S.suspensionTravelM * 100.f * 0.55f;
	SuspensionDampingRatio = S.suspensionDampingRatio;
	SuspensionSmoothing = 4;
	WheelLoadRatio = 0.5f;
	// Spring rate for a quarter-car at 1.35 Hz with ~420 kg on the corner: k = m (2 pi f)^2 = 30.2 kN/m.
	// Chaos wants N/cm.
	SpringRate = 302.f;
	SpringPreload = 50.f;
	RollbarScaling = 0.15f;

	// Shapecast keeps a 225-section tyre from dropping into kerb joints and subway grates at speed.
	SweepShape = ESweepShape::Shapecast;
}

UNYCVehicleWheelFront::UNYCVehicleWheelFront()
{
	const nycsim_gameplay::PlayerVehicleSpec& S = Spec();
	AxleType = EAxleType::Front;
	bAffectedBySteering = true;
	bAffectedByBrake = true;
	bAffectedByHandbrake = false;
	bAffectedByEngine = true;  // front-wheel drive
	MaxSteerAngle = S.maxSteerAngleDeg;
	MaxBrakeTorque = S.maxBrakeTorqueFrontNm;
	MaxHandBrakeTorque = 0.f;
}

UNYCVehicleWheelRear::UNYCVehicleWheelRear()
{
	const nycsim_gameplay::PlayerVehicleSpec& S = Spec();
	AxleType = EAxleType::Rear;
	bAffectedBySteering = false;
	bAffectedByBrake = true;
	bAffectedByHandbrake = true;
	bAffectedByEngine = false;
	MaxSteerAngle = 0.f;
	MaxBrakeTorque = S.maxBrakeTorqueRearNm;
	MaxHandBrakeTorque = S.handbrakeTorqueNm;
	// The rear axle carries less mass (57/43 front bias), so its spring is softer.
	SpringRate = 228.f;
}
