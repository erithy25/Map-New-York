// Chaos wheel definitions for the player car (ADR-009: 2019 Ford Fusion Hybrid SE, 225/50R17).
//
// Numbers come from the published specification through
// Private/CoreAdapter/GameplayVehicleDynamics.h (PlayerVehicleSpec), so the wheels, the movement component and the
// audio synthesiser cannot drift apart. Only geometry and per-axle roles live here; the *dynamic* grip is written
// every frame by UNYCVehicleMovementComponent from the surface under the wheel and the weather.
#pragma once

#include "CoreMinimal.h"
#include "ChaosVehicleWheel.h"
#include "NYCVehicleWheels.generated.h"

/** Shared setup: 225/50R17 on a 17x8 rim, MacPherson front / integral-link rear geometry. */
UCLASS(Abstract)
class NYCSIMRUNTIME_API UNYCVehicleWheelBase : public UChaosVehicleWheel
{
	GENERATED_BODY()

public:
	UNYCVehicleWheelBase();
};

/** Front axle: steered, driven (transverse hybrid drivetrain), 2200 Nm brake torque. */
UCLASS()
class NYCSIMRUNTIME_API UNYCVehicleWheelFront : public UNYCVehicleWheelBase
{
	GENERATED_BODY()

public:
	UNYCVehicleWheelFront();
};

/** Rear axle: unsteered, undriven, 1400 Nm brake torque, carries the handbrake. */
UCLASS()
class NYCSIMRUNTIME_API UNYCVehicleWheelRear : public UNYCVehicleWheelBase
{
	GENERATED_BODY()

public:
	UNYCVehicleWheelRear();
};
