// Chaos wheeled-vehicle movement for the player car, configured entirely in C++ from the published specification
// and extended with the two things the stock component does not do:
//
//   1. **Surface- and weather-dependent grip.** Every physics frame each wheel traces the surface beneath it,
//      resolves its EPhysicalSurface to a nycsim_gameplay::SurfaceClass and asks the tyre model for the peak
//      friction under the current wetness / snow / ice (ARCHITECTURE §7: dry asphalt 1.0, wet 0.7, wet steel plate
//      0.55, wet paint 0.6, snow 0.3, ice 0.15). Aquaplaning above the NASA threshold cuts grip further.
//   2. **Pavement roughness.** The same trace yields a roughness amplitude per surface class (Belgian block is 4x
//      asphalt); a deterministic value-noise field over world position turns it into a bounded vertical force at
//      each contact patch, which is what makes cobbles, steel plates and patched asphalt feel different and what
//      drives the camera shake and the tyre-noise synthesiser.
//
// Everything else — engine, transmission, steering, differential, suspension — is set from PlayerVehicleSpec in
// the constructor, so there is no Blueprint or data asset to keep in sync.
#pragma once

#include "CoreMinimal.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Chaos/ChaosEngineInterface.h"
#include "NYCVehicleMovementComponent.generated.h"

class UMaterialParameterCollection;

/** Per-wheel surface state sampled by the trace, published for audio, VFX and the HUD. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCWheelSurface
{
	GENERATED_BODY()

	/** EPhysicalSurface reported by the trace (SurfaceType1..13 per Config/DefaultEngine.ini). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	TEnumAsByte<EPhysicalSurface> PhysicalSurface = SurfaceType_Default;

	/** Peak friction coefficient after weather. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	float PeakFriction = 1.f;

	/** Roughness amplitude in metres RMS for this surface. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	float Roughness = 0.f;

	/** True when the trace found ground under the wheel this frame. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	bool bInContact = false;

	/** Contact point in world space (unset when !bInContact). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	FVector ContactPoint = FVector::ZeroVector;

	/** 0..1 how much of the tyre's grip is lost to standing water at the current speed. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Vehicle")
	float Aquaplaning = 0.f;
};

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleMovementComponent : public UChaosWheeledVehicleMovementComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleMovementComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/// The one entry point the pawn uses for driver input. It caches the values (the base class keeps its
	/// processed inputs private in some engine versions) and forwards them to the Chaos setters.
	/// All four are 0..1 except Steer, which is -1..1 (left negative).
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetDriverInput(float Throttle, float Brake, float Steer, float Handbrake);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetDriverThrottle() const { return DriverThrottle; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetDriverBrake() const { return DriverBrake; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetDriverSteer() const { return DriverSteer; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetDriverHandbrake() const { return DriverHandbrake; }

	// ---- weather -------------------------------------------------------------------------------------------
	/** 0..1 road wetness, snow cover and ice cover. Normally driven from MPC_Weather; call this to override. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetWeather(float InWetness, float InSnowCover, float InIceCover, float InWaterDepthMm);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetWetness() const { return Wetness; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetSnowCover() const { return SnowCover; }

	/** When true (default) the component samples MPC_Weather every WeatherSampleSeconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NYCSim|Weather")
	bool bReadWeatherFromParameterCollection = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NYCSim|Weather", meta = (ClampMin = "0.05"))
	float WeatherSampleSeconds = 0.5f;

	// ---- surface -------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	const FNYCWheelSurface& GetWheelSurface(int32 WheelIndex) const;

	/** Mean of the four wheels' peak friction (drives the traction warning and the tyre audio). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetAverageGrip() const { return AverageGrip; }

	/** Current road-roughness excitation, 0..1, already scaled by speed. Used by camera shake and audio. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetRoughnessSignal() const { return RoughnessSignal; }

	/** Dominant surface under the vehicle (the surface most wheels are on). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	TEnumAsByte<EPhysicalSurface> GetDominantSurface() const { return DominantSurface; }

	/** Speed in km/h (the dashboard shows mph; this is the raw value). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetSpeedKph() const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetSpeedMph() const;

	/** Engine speed normalised to 0..1 over the published rev range (for the tachometer and the audio). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetNormalisedRpm() const;

	/** Fuel level 0..1. The hybrid drivetrain consumes at the published 5.6 L/100 km, load-weighted. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetFuelFraction() const { return FuelLitres / FuelCapacityLitres; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void Refuel() { FuelLitres = FuelCapacityLitres; }

	/** Battery state of charge 0..1 for the hybrid readout. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetBatteryFraction() const { return BatterySoc; }

	/** True while the internal-combustion engine is running (a hybrid shuts it off at rest and on light load). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	bool IsEngineRunning() const { return bEngineRunning; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetIgnition(bool bOn);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	bool IsIgnitionOn() const { return bIgnitionOn; }

	/** Steering-wheel rotation in degrees (± steeringWheelLockDeg), for the SteeringWheel bone. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	float GetSteeringWheelAngleDeg() const;

	/** Multiplies the tyre grip loss the damage model applies (a burst tyre keeps a fraction of its grip). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetWheelDamage(int32 WheelIndex, float Damage01);

protected:
	/** Vertical force cap applied by the roughness model, as a fraction of the vehicle's weight. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Surface", meta = (ClampMin = "0.0", ClampMax = "0.25"))
	float MaxRoughnessForceFraction = 0.06f;

	/** Length of the downward trace from the wheel centre, in centimetres. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Surface", meta = (ClampMin = "10.0"))
	float SurfaceTraceLengthCm = 90.f;

private:
	void ConfigureFromSpec();
	void SampleWeather();
	void UpdateSurfaceGrip(float DeltaTime);
	void ApplyRoughness(float DeltaTime);
	void UpdateEnergy(float DeltaTime);

	/// Deterministic value noise over world metres; the pavement's fine texture between the trace samples.
	static float RoughnessNoise(double X, double Y, float Frequency);

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> WeatherCollection;

	TArray<FNYCWheelSurface> WheelSurfaces;
	TArray<float> WheelDamage;

	float Wetness = 0.f;
	float SnowCover = 0.f;
	float IceCover = 0.f;
	float WaterDepthMm = 0.f;
	float WeatherTimer = 0.f;
	bool bWeatherParamsResolved = false;
	bool bHasWetnessParam = false;
	bool bHasSnowParam = false;
	bool bHasIceParam = false;
	bool bHasWaterDepthParam = false;

	float AverageGrip = 1.f;
	float RoughnessSignal = 0.f;
	float RoughnessPhase = 0.f;
	TEnumAsByte<EPhysicalSurface> DominantSurface = SurfaceType_Default;

	float DriverThrottle = 0.f;
	float DriverBrake = 0.f;
	float DriverSteer = 0.f;
	float DriverHandbrake = 0.f;

	float FuelCapacityLitres = 53.f;
	float FuelLitres = 53.f;
	float BatterySoc = 0.65f;
	bool bIgnitionOn = false;
	bool bEngineRunning = false;
};
