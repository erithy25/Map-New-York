#include "Vehicle/NYCVehicleMovementComponent.h"

#include <type_traits>
#include <utility>

#include "CoreAdapter/GameplayVehicleDynamics.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "NYCSimRuntime.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Player/NYCGameplaySettings.h"
#include "Vehicle/NYCVehicleContract.h"
#include "Vehicle/NYCVehicleWheels.h"

namespace
{
using nycsim_gameplay::PlayerVehicleSpec;
using nycsim_gameplay::SurfaceClass;
using nycsim_gameplay::TyreFrictionModel;

const PlayerVehicleSpec& Spec()
{
	static const PlayerVehicleSpec Value;
	return Value;
}

const TyreFrictionModel& Friction()
{
	static const TyreFrictionModel Value;
	return Value;
}

/// EPhysicalSurface -> the tyre model's surface class. The mapping is the order of the PhysicalSurfaces block in
/// Config/DefaultEngine.ini (SurfaceType1 = Asphalt ... SurfaceType13 = Ice), so it is a straight cast with a
/// guard for anything outside the declared range.
SurfaceClass ToSurfaceClass(EPhysicalSurface Surface)
{
	const int32 Index = static_cast<int32>(Surface);
	if (Index <= 0 || Index >= static_cast<int32>(SurfaceClass::Count))
	{
		return SurfaceClass::Default;
	}
	return static_cast<SurfaceClass>(Index);
}

// UE 5.4 exposes a runtime setter for per-wheel grip on the wheeled movement component. It has not existed in
// every 5.x release, so it is called through a detector rather than assumed: when the member is absent the
// authored UChaosVehicleWheel::FrictionForceMultiplier is written instead, which the component reads when it
// pushes wheel configuration to the physics thread. Both paths are compiled from the same call site below.
template <typename T, typename = void>
struct THasSetWheelFrictionMultiplier : std::false_type
{
};

template <typename T>
struct THasSetWheelFrictionMultiplier<
	T, decltype(static_cast<void>(std::declval<T&>().SetWheelFrictionMultiplier(0, 1.0f)))> : std::true_type
{
};

template <typename T>
void ApplyWheelFriction(T& Component, int32 WheelIndex, float Multiplier)
{
	if constexpr (THasSetWheelFrictionMultiplier<T>::value)
	{
		Component.SetWheelFrictionMultiplier(WheelIndex, Multiplier);
	}
	else
	{
		if (Component.Wheels.IsValidIndex(WheelIndex) && Component.Wheels[WheelIndex] != nullptr)
		{
			Component.Wheels[WheelIndex]->FrictionForceMultiplier = Multiplier;
		}
	}
}

constexpr float kCmPerMetre = 100.f;
}  // namespace

UNYCVehicleMovementComponent::UNYCVehicleMovementComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
	ConfigureFromSpec();
}

void UNYCVehicleMovementComponent::ConfigureFromSpec()
{
	const PlayerVehicleSpec& S = Spec();

	// ---- chassis -------------------------------------------------------------------------------------------
	Mass = S.massKg;
	ChassisWidth = S.widthM * kCmPerMetre;
	ChassisHeight = S.heightM * kCmPerMetre;
	DragCoefficient = S.dragCoefficient;
	DownforceCoefficient = 0.3f;
	bEnableCenterOfMassOverride = true;
	// Longitudinal centre of gravity from the 57/43 front weight distribution: it sits (frontShare - 0.5) of the
	// wheelbase forward of the wheelbase midpoint, i.e. 20 cm forward for this car. The mesh origin is at the
	// wheelbase midpoint by the Blender export contract (+X forward), so the offset is used directly.
	const float WheelbaseCm = S.wheelbaseM * kCmPerMetre;
	CenterOfMassOverride =
		FVector((S.frontMassShare - 0.5f) * WheelbaseCm, 0.f, S.cogHeightM * kCmPerMetre);

	bMechanicalSimEnabled = true;
	bSuspensionEnabled = true;
	bWheelFrictionEnabled = true;

	// ---- wheels --------------------------------------------------------------------------------------------
	WheelSetups.SetNum(4);
	WheelSetups[0].WheelClass = UNYCVehicleWheelFront::StaticClass();
	WheelSetups[0].BoneName = FNYCVehicleContract::WheelBone(0);
	WheelSetups[1].WheelClass = UNYCVehicleWheelFront::StaticClass();
	WheelSetups[1].BoneName = FNYCVehicleContract::WheelBone(1);
	WheelSetups[2].WheelClass = UNYCVehicleWheelRear::StaticClass();
	WheelSetups[2].BoneName = FNYCVehicleContract::WheelBone(2);
	WheelSetups[3].WheelClass = UNYCVehicleWheelRear::StaticClass();
	WheelSetups[3].BoneName = FNYCVehicleContract::WheelBone(3);
	for (FChaosWheelSetup& Setup : WheelSetups)
	{
		Setup.AdditionalOffset = FVector::ZeroVector;
	}

	// ---- engine --------------------------------------------------------------------------------------------
	// The Chaos torque curve is normalised 0..1 and scaled by MaxTorque, so MaxTorque is the peak of the
	// published combined-system curve and the keys are curve(rpm) / peak.
	float PeakTorque = 0.f;
	for (float Value : S.torqueCurveNm)
	{
		PeakTorque = FMath::Max(PeakTorque, Value);
	}
	EngineSetup.MaxTorque = PeakTorque;
	EngineSetup.MaxRPM = S.maxRpm;
	EngineSetup.EngineIdleRPM = S.electricIdleRpm;
	EngineSetup.EngineBrakeEffect = 0.05f;  // a hybrid regenerates instead of engine-braking hard
	EngineSetup.EngineRevUpMOI = S.engineMoiKgM2 * 20.f;
	EngineSetup.EngineRevDownRate = 600.f;
	if (FRichCurve* Curve = EngineSetup.TorqueCurve.GetRichCurve())
	{
		Curve->Reset();
		for (int32 i = 0; i < 7; ++i)
		{
			const float Rpm = S.maxRpm * static_cast<float>(i) / 6.f;
			Curve->AddKey(Rpm, PeakTorque > 0.f ? S.torqueCurveNm[i] / PeakTorque : 0.f);
		}
	}

	// ---- transmission: single-ratio eCVT ---------------------------------------------------------------------
	TransmissionSetup.bUseAutomaticGears = true;
	TransmissionSetup.bUseAutoReverse = false;
	TransmissionSetup.FinalRatio = S.finalDriveRatio;
	TransmissionSetup.ForwardGearRatios.Reset();
	TransmissionSetup.ForwardGearRatios.Add(1.0f);
	TransmissionSetup.ReverseGearRatios.Reset();
	TransmissionSetup.ReverseGearRatios.Add(S.reverseRatio / S.finalDriveRatio);
	TransmissionSetup.ChangeUpRPM = S.maxRpm;      // one gear: never shifts up
	TransmissionSetup.ChangeDownRPM = 0.f;
	TransmissionSetup.GearChangeTime = 0.f;
	TransmissionSetup.TransmissionEfficiency = S.transmissionEfficiency;

	// ---- steering ------------------------------------------------------------------------------------------
	SteeringSetup.SteeringType = ESteeringType::Ackermann;
	SteeringSetup.AngleRatio = 0.7f;
	if (FRichCurve* Curve = SteeringSetup.SteeringCurve.GetRichCurve())
	{
		Curve->Reset();
		// Speed-sensitive steering: full lock parking, 9° at 100 km/h (spec), tapering above.
		Curve->AddKey(0.f, 1.0f);
		Curve->AddKey(20.f, 0.85f);
		Curve->AddKey(60.f, 0.45f);
		Curve->AddKey(100.f, S.steerAngleAt100KphDeg / S.maxSteerAngleDeg);
		Curve->AddKey(160.f, 0.16f);
	}

	// ---- differential --------------------------------------------------------------------------------------
	DifferentialSetup.DifferentialType = EVehicleDifferential::FrontWheelDrive;
	DifferentialSetup.FrontRearSplit = 1.0f;

	FuelCapacityLitres = S.fuelTankLitres;
	FuelLitres = S.fuelTankLitres * 0.72f;

	WheelSurfaces.SetNum(4);
	WheelDamage.Init(0.f, 4);
}

void UNYCVehicleMovementComponent::BeginPlay()
{
	Super::BeginPlay();

	WheelSurfaces.SetNum(FMath::Max(4, WheelSetups.Num()));
	WheelDamage.SetNumZeroed(WheelSurfaces.Num());

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (bReadWeatherFromParameterCollection && !Settings.WeatherParameterCollection.IsNull())
	{
		WeatherCollection = Cast<UMaterialParameterCollection>(Settings.WeatherParameterCollection.TryLoad());
	}
	if (WeatherCollection != nullptr)
	{
		// Resolve which of the documented parameters this collection actually declares, once, so the per-frame
		// sampler never asks for a name that would log a warning every tick.
		for (const FCollectionScalarParameter& Param : WeatherCollection->ScalarParameters)
		{
			if (Param.ParameterName == Settings.WeatherWetnessParameter)
			{
				bHasWetnessParam = true;
			}
			else if (Param.ParameterName == Settings.WeatherSnowParameter)
			{
				bHasSnowParam = true;
			}
			else if (Param.ParameterName == Settings.WeatherIceParameter)
			{
				bHasIceParam = true;
			}
			else if (Param.ParameterName == Settings.WeatherWaterDepthParameter)
			{
				bHasWaterDepthParam = true;
			}
		}
		bWeatherParamsResolved = true;
		UE_LOG(LogNYCSim, Log,
			   TEXT("Vehicle weather: MPC '%s' provides wetness=%d snow=%d ice=%d waterDepth=%d"),
			   *WeatherCollection->GetName(), bHasWetnessParam ? 1 : 0, bHasSnowParam ? 1 : 0, bHasIceParam ? 1 : 0,
			   bHasWaterDepthParam ? 1 : 0);
	}
	else if (bReadWeatherFromParameterCollection)
	{
		UE_LOG(LogNYCSim, Warning,
			   TEXT("Vehicle weather: '%s' could not be loaded; grip stays at the dry values until "
					"SetWeather() is called."),
			   *Settings.WeatherParameterCollection.ToString());
	}
}

void UNYCVehicleMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType,
												 FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (DeltaTime <= 0.f)
	{
		return;
	}

	WeatherTimer += DeltaTime;
	if (bReadWeatherFromParameterCollection && WeatherTimer >= WeatherSampleSeconds)
	{
		WeatherTimer = 0.f;
		SampleWeather();
	}

	UpdateSurfaceGrip(DeltaTime);
	ApplyRoughness(DeltaTime);
	UpdateEnergy(DeltaTime);
}

void UNYCVehicleMovementComponent::SetDriverInput(float Throttle, float Brake, float Steer, float Handbrake)
{
	DriverThrottle = FMath::Clamp(Throttle, 0.f, 1.f);
	DriverBrake = FMath::Clamp(Brake, 0.f, 1.f);
	DriverSteer = FMath::Clamp(Steer, -1.f, 1.f);
	DriverHandbrake = FMath::Clamp(Handbrake, 0.f, 1.f);

	// With the ignition off the driver can still steer and brake, but nothing drives the wheels.
	SetThrottleInput(bIgnitionOn ? DriverThrottle : 0.f);
	SetBrakeInput(DriverBrake);
	SetSteeringInput(DriverSteer);
	SetHandbrakeInput(DriverHandbrake > 0.5f);
}

void UNYCVehicleMovementComponent::SampleWeather()
{
	if (WeatherCollection == nullptr || !bWeatherParamsResolved)
	{
		return;
	}
	const UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (bHasWetnessParam)
	{
		Wetness = FMath::Clamp(
			UKismetMaterialLibrary::GetScalarParameterValue(World, WeatherCollection, Settings.WeatherWetnessParameter),
			0.f, 1.f);
	}
	if (bHasSnowParam)
	{
		SnowCover = FMath::Clamp(
			UKismetMaterialLibrary::GetScalarParameterValue(World, WeatherCollection, Settings.WeatherSnowParameter),
			0.f, 1.f);
	}
	if (bHasIceParam)
	{
		IceCover = FMath::Clamp(
			UKismetMaterialLibrary::GetScalarParameterValue(World, WeatherCollection, Settings.WeatherIceParameter),
			0.f, 1.f);
	}
	if (bHasWaterDepthParam)
	{
		WaterDepthMm = FMath::Clamp(UKismetMaterialLibrary::GetScalarParameterValue(
										World, WeatherCollection, Settings.WeatherWaterDepthParameter),
									0.f, 25.f);
	}
	else
	{
		// No explicit depth channel: a fully wet road carries about 1 mm of film in steady rain (NCHRP 108).
		WaterDepthMm = Wetness * 1.2f;
	}
}

void UNYCVehicleMovementComponent::SetWeather(float InWetness, float InSnowCover, float InIceCover,
											  float InWaterDepthMm)
{
	bReadWeatherFromParameterCollection = false;
	Wetness = FMath::Clamp(InWetness, 0.f, 1.f);
	SnowCover = FMath::Clamp(InSnowCover, 0.f, 1.f);
	IceCover = FMath::Clamp(InIceCover, 0.f, 1.f);
	WaterDepthMm = FMath::Clamp(InWaterDepthMm, 0.f, 25.f);
}

const FNYCWheelSurface& UNYCVehicleMovementComponent::GetWheelSurface(int32 WheelIndex) const
{
	static const FNYCWheelSurface Empty;
	return WheelSurfaces.IsValidIndex(WheelIndex) ? WheelSurfaces[WheelIndex] : Empty;
}

void UNYCVehicleMovementComponent::SetWheelDamage(int32 WheelIndex, float Damage01)
{
	if (WheelDamage.IsValidIndex(WheelIndex))
	{
		WheelDamage[WheelIndex] = FMath::Clamp(Damage01, 0.f, 1.f);
	}
}

void UNYCVehicleMovementComponent::UpdateSurfaceGrip(float DeltaTime)
{
	USkeletalMeshComponent* Mesh = Cast<USkeletalMeshComponent>(UpdatedPrimitive);
	UWorld* World = GetWorld();
	if (Mesh == nullptr || World == nullptr)
	{
		return;
	}

	const PlayerVehicleSpec& S = Spec();
	const TyreFrictionModel& Model = Friction();
	const float SpeedMps = FMath::Abs(GetForwardSpeed()) / kCmPerMetre;
	const float AquaplaneSpeed = Model.aquaplaneSpeedMps(WaterDepthMm, /*tyre pressure*/ 241.f);

	FCollisionQueryParams Params(SCENE_QUERY_STAT(NYCVehicleSurface), /*bTraceComplex*/ true, GetOwner());
	Params.bReturnPhysicalMaterial = true;

	float GripSum = 0.f;
	int32 GripCount = 0;
	int32 SurfaceVotes[static_cast<int32>(SurfaceClass::Count)] = {};
	float RoughnessSum = 0.f;

	for (int32 i = 0; i < WheelSurfaces.Num(); ++i)
	{
		FNYCWheelSurface& Out = WheelSurfaces[i];
		Out.bInContact = false;
		Out.Aquaplaning = 0.f;

		const FName Bone = WheelSetups.IsValidIndex(i) ? WheelSetups[i].BoneName : FNYCVehicleContract::WheelBone(i);
		if (Bone.IsNone() || Mesh->GetBoneIndex(Bone) == INDEX_NONE)
		{
			continue;
		}
		const FVector Start = Mesh->GetBoneLocation(Bone, EBoneSpaces::WorldSpace);
		const FVector End = Start - FVector(0.f, 0.f, SurfaceTraceLengthCm);

		FHitResult Hit;
		if (!World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
		{
			// Airborne (or over a hole in the collision): keep the last grip so the solver does not jolt.
			ApplyWheelFriction(*this, i, FMath::Max(0.1f, AverageGrip * 2.0f));
			continue;
		}

		const EPhysicalSurface Surface =
			Hit.PhysMaterial.IsValid() ? Hit.PhysMaterial->SurfaceType.GetValue() : SurfaceType_Default;
		const SurfaceClass Class = ToSurfaceClass(Surface);
		float Peak = Model.peakFriction(Class, Wetness, SnowCover, IceCover);

		// Dynamic aquaplaning: grip falls off once the tyre outruns the water's escape speed.
		if (SpeedMps > AquaplaneSpeed)
		{
			const float Excess = FMath::Clamp((SpeedMps - AquaplaneSpeed) / FMath::Max(1.f, AquaplaneSpeed), 0.f, 1.f);
			Out.Aquaplaning = Excess;
			Peak *= FMath::Lerp(1.f, 0.15f, Excess);
		}
		// A damaged (flat / burst) tyre keeps roughly a third of its grip.
		if (WheelDamage.IsValidIndex(i))
		{
			Peak *= FMath::Lerp(1.f, 0.35f, WheelDamage[i]);
		}

		Out.PhysicalSurface = Surface;
		Out.PeakFriction = Peak;
		Out.Roughness = Model.surface(Class).roughnessM;
		Out.bInContact = true;
		Out.ContactPoint = Hit.ImpactPoint;

		const int32 ClassIndex = static_cast<int32>(Class);
		if (ClassIndex >= 0 && ClassIndex < static_cast<int32>(SurfaceClass::Count))
		{
			++SurfaceVotes[ClassIndex];
		}
		GripSum += Peak;
		++GripCount;
		RoughnessSum += Out.Roughness;

		// The authored wheel grip (FrictionForceMultiplier = 2.0) corresponds to dry asphalt, so the runtime
		// multiplier is 2.0 x (peak / dry-asphalt peak).
		const float Reference = Model.referenceDryPeak();
		ApplyWheelFriction(*this, i, 2.0f * (Reference > 0.f ? Peak / Reference : 1.f));
	}

	AverageGrip = GripCount > 0 ? GripSum / static_cast<float>(GripCount) : 1.f;

	int32 BestVotes = 0;
	int32 BestClass = 0;
	for (int32 c = 0; c < static_cast<int32>(SurfaceClass::Count); ++c)
	{
		if (SurfaceVotes[c] > BestVotes)
		{
			BestVotes = SurfaceVotes[c];
			BestClass = c;
		}
	}
	DominantSurface = static_cast<EPhysicalSurface>(BestClass);

	// Roughness excitation: amplitude x speed, low-passed so it does not flicker at surface joints.
	const float MeanRoughness = GripCount > 0 ? RoughnessSum / static_cast<float>(GripCount) : 0.f;
	const float Target = FMath::Clamp(MeanRoughness / 0.018f, 0.f, 1.f) * FMath::Clamp(SpeedMps / 14.f, 0.f, 1.f);
	RoughnessSignal = FMath::FInterpTo(RoughnessSignal, Target, DeltaTime, 8.f);
}

float UNYCVehicleMovementComponent::RoughnessNoise(double X, double Y, float Frequency)
{
	// Deterministic hash-based value noise: the same world point always produces the same bump, so a road feels
	// identical on every pass and on every machine. (No texture is available at runtime: the roads stage writes
	// pavement roughness per tile in roads/pavement/{tile}.parquet, which is not part of the runtime NYCB set.)
	const double Fx = X * Frequency;
	const double Fy = Y * Frequency;
	const int64 Ix = static_cast<int64>(FMath::FloorToDouble(Fx));
	const int64 Iy = static_cast<int64>(FMath::FloorToDouble(Fy));
	const double Tx = Fx - static_cast<double>(Ix);
	const double Ty = Fy - static_cast<double>(Iy);

	auto Hash = [](int64 X0, int64 Y0) -> float {
		uint64 H = static_cast<uint64>(X0) * 0x9E3779B97F4A7C15ull ^ static_cast<uint64>(Y0) * 0xC2B2AE3D27D4EB4Full;
		H ^= H >> 29;
		H *= 0xBF58476D1CE4E5B9ull;
		H ^= H >> 32;
		return static_cast<float>(H >> 40) * (1.f / 16777216.f) * 2.f - 1.f;
	};

	const float Sx = static_cast<float>(Tx * Tx * (3.0 - 2.0 * Tx));
	const float Sy = static_cast<float>(Ty * Ty * (3.0 - 2.0 * Ty));
	const float A = FMath::Lerp(Hash(Ix, Iy), Hash(Ix + 1, Iy), Sx);
	const float B = FMath::Lerp(Hash(Ix, Iy + 1), Hash(Ix + 1, Iy + 1), Sx);
	return FMath::Lerp(A, B, Sy);
}

void UNYCVehicleMovementComponent::ApplyRoughness(float DeltaTime)
{
	UPrimitiveComponent* Body = UpdatedPrimitive;
	if (Body == nullptr || !Body->IsSimulatingPhysics() || MaxRoughnessForceFraction <= 0.f)
	{
		return;
	}
	const float SpeedMps = FMath::Abs(GetForwardSpeed()) / kCmPerMetre;
	if (SpeedMps < 0.6f)
	{
		return;
	}

	const float WeightN = Mass * 9.81f;
	const float MaxForce = WeightN * MaxRoughnessForceFraction;
	for (int32 i = 0; i < WheelSurfaces.Num(); ++i)
	{
		const FNYCWheelSurface& Surface = WheelSurfaces[i];
		if (!Surface.bInContact || Surface.Roughness <= 0.f)
		{
			continue;
		}
		const FVector Point = Surface.ContactPoint;
		// Two octaves: 1.4 m (joints, plates, potholes) and 0.16 m (aggregate, cobble crowns).
		const double Xm = Point.X / kCmPerMetre;
		const double Ym = Point.Y / kCmPerMetre;
		const float Noise = 0.7f * RoughnessNoise(Xm, Ym, 0.7f) + 0.3f * RoughnessNoise(Xm, Ym, 6.2f);
		const float Amplitude = FMath::Clamp(Surface.Roughness / 0.018f, 0.f, 1.5f);
		const float SpeedFactor = FMath::Clamp(SpeedMps / 12.f, 0.f, 1.2f);
		const float ForceN = FMath::Clamp(Noise * Amplitude * SpeedFactor, -1.f, 1.f) * MaxForce;
		Body->AddForceAtLocation(FVector(0.f, 0.f, ForceN * 100.f), Point);  // N -> UE force units (cm-based)
	}
	RoughnessPhase += DeltaTime;
}

void UNYCVehicleMovementComponent::UpdateEnergy(float DeltaTime)
{
	const PlayerVehicleSpec& S = Spec();
	const float SpeedMps = FMath::Abs(GetForwardSpeed()) / kCmPerMetre;
	const float Throttle = DriverThrottle;

	if (!bIgnitionOn)
	{
		bEngineRunning = false;
		return;
	}

	// A power-split hybrid runs the ICE when the battery is low or the demand exceeds the motor's 88 kW.
	const bool bNeedsEngine = BatterySoc < 0.30f || (Throttle > 0.45f && SpeedMps > 4.f) || SpeedMps > 22.f;
	bEngineRunning = bNeedsEngine && FuelLitres > 0.05f;

	// Consumption: the published 5.6 L/100 km combined, scaled by instantaneous load, only while the ICE runs.
	if (bEngineRunning)
	{
		const float Load = FMath::Clamp(0.35f + Throttle, 0.f, 1.6f);
		const float LitresPerMetre = (S.combinedLPer100km / 100000.f) * Load;
		FuelLitres = FMath::Max(0.f, FuelLitres - LitresPerMetre * SpeedMps * DeltaTime);
		BatterySoc = FMath::Min(1.f, BatterySoc + 0.004f * DeltaTime);
	}
	else if (Throttle > 0.02f)
	{
		// Battery-only propulsion: 1.4 kWh pack, ~14 kW at part throttle.
		const float DrawKw = 14.f * Throttle;
		BatterySoc = FMath::Max(0.f, BatterySoc - (DrawKw * DeltaTime / 3600.f) / S.batteryKwh);
	}
	else if (SpeedMps > 1.f && DriverBrake > 0.02f)
	{
		// Regeneration under braking, capped at 30 kW.
		const float RegenKw = FMath::Min(30.f, 30.f * DriverBrake);
		BatterySoc = FMath::Min(1.f, BatterySoc + (RegenKw * DeltaTime / 3600.f) / S.batteryKwh);
	}
}

void UNYCVehicleMovementComponent::SetIgnition(bool bOn)
{
	bIgnitionOn = bOn;
	if (!bOn)
	{
		bEngineRunning = false;
		SetThrottleInput(0.f);
		DriverThrottle = 0.f;
	}
}

float UNYCVehicleMovementComponent::GetSpeedKph() const
{
	return FMath::Abs(GetForwardSpeed()) * 0.036f;  // cm/s -> km/h
}

float UNYCVehicleMovementComponent::GetSpeedMph() const
{
	return GetSpeedKph() * 0.621371f;
}

float UNYCVehicleMovementComponent::GetNormalisedRpm() const
{
	const PlayerVehicleSpec& S = Spec();
	const float Rpm = GetEngineRotationSpeed();
	return FMath::Clamp(Rpm / FMath::Max(1.f, S.maxRpm), 0.f, 1.f);
}

float UNYCVehicleMovementComponent::GetSteeringWheelAngleDeg() const
{
	const PlayerVehicleSpec& S = Spec();
	return DriverSteer * S.steeringWheelLockDeg;
}
