// Sky and time: real America/New_York civil time and a full NREL-SPA sun / Meeus moon ephemeris (through
// CoreAdapter/NYCAstro) driving the directional lights, the sky atmosphere, the volumetric cloud layer, the height
// fog, the sky light and the star sphere — and the city's street lighting, which switches at civil dusk.
//
// Division of labour with the weather subsystem: this subsystem owns the *actors*, the weather subsystem owns the
// *observations*. UNYCWeatherSubsystem pushes cloud cover, cloud base, visibility, humidity and wind here through
// ApplyAtmosphere(); nothing else writes to the sky actors.
//
// Console: nycsim.PrintSun, nycsim.Sky.SetTime <ISO-8601 UTC|now>, nycsim.Sky.TimeScale <x>, nycsim.Sky.Debug 0|1.
#pragma once

#include "CoreMinimal.h"
#include "CoreAdapter/NYCAstro.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/ObjectPtr.h"

#include "NYCSkyTimeSubsystem.generated.h"

class ADirectionalLight;
class AExponentialHeightFog;
class ASkyAtmosphere;
class ASkyLight;
class AStaticMeshActor;
class AVolumetricCloud;
class UMaterialInstanceDynamic;
class UMaterialParameterCollection;

/** Atmospheric state handed over by the weather subsystem. All fields are observations, never invented. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCAtmosphereParams
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	bool bValid = false;

	/** Total cloud cover, 0..1. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float CloudCover = 0.f;

	/** Ceiling / lowest broken-or-overcast layer, metres above ground. 0 = unknown. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float CloudBaseMetres = 0.f;

	/** Meteorological visibility, metres. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float VisibilityMetres = 16000.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float RelativeHumidityPercent = 50.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float TemperatureC = 15.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float WindSpeedMps = 0.f;

	/** Compass heading the wind blows *from*. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Sky")
	float WindFromHeadingDeg = 0.f;
};

/** Broadcast when the street lighting switches (civil dusk / civil dawn, with hysteresis). */
DECLARE_MULTICAST_DELEGATE_OneParam(FNYCOnStreetLightingChanged, bool /*bOn*/);
/** Broadcast every sky update with the new sun elevation; cheap enough for per-frame consumers to ignore. */
DECLARE_MULTICAST_DELEGATE_TwoParams(FNYCOnSkyUpdated, double /*SunElevationDeg*/, double /*SunAzimuthDeg*/);

UCLASS()
class NYCSIMRUNTIME_API UNYCSkyTimeSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickable() const override;
	virtual TStatId GetStatId() const override;

	// ---- clock ----------------------------------------------------------------------------------------------
	/** POSIX seconds of the simulation clock (real time, or the fixed instant advanced by TimeScale). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	double GetSimUnixSeconds() const { return SimUnixSeconds; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	FDateTime GetLocalTime() const { return SimTime.Local; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	FString GetTimeZoneAbbreviation() const { return SimTime.TzAbbreviation; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	bool IsDaylightSaving() const { return SimTime.bIsDst; }

	/** Sets the clock to an instant and stops following the system clock. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Sky")
	bool SetSimTimeIso8601(const FString& Iso8601Utc);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Sky")
	void SetFollowRealTime(bool bFollow);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Sky")
	void SetTimeScale(float Scale);

	// ---- ephemeris ------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	double GetSunElevationDeg() const { return Sun.ElevationDeg; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	double GetSunAzimuthDeg() const { return Sun.AzimuthDeg; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	double GetMoonElevationDeg() const { return Moon.ElevationDeg; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	float GetMoonIlluminatedFraction() const { return static_cast<float>(Moon.IlluminatedFraction); }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	FString GetMoonPhaseName() const { return Moon.PhaseName; }

	/** True between civil dusk and civil dawn (the switch the city's street lighting follows). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	bool AreStreetLightsOn() const { return bStreetLightsOn; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	FVector GetSunDirectionUE() const { return Sun.DirectionUE; }

	const FNYCSunState& SunState() const { return Sun; }
	const FNYCMoonState& MoonState() const { return Moon; }
	const FNYCSimTime& TimeState() const { return SimTime; }
	const FNYCSunEvents& SunEvents() const { return RiseSet; }
	const FNYCSunEvents& CivilTwilight() const { return CivilEvents; }

	// ---- weather hand-off -----------------------------------------------------------------------------------
	/** Applied to the cloud layer, the height fog and the direct-light attenuation. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Sky")
	void ApplyAtmosphere(const FNYCAtmosphereParams& Params);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Sky")
	FNYCAtmosphereParams GetAtmosphere() const { return Atmosphere; }

	FNYCOnStreetLightingChanged& OnStreetLightingChanged() { return StreetLightingChanged; }
	FNYCOnSkyUpdated& OnSkyUpdated() { return SkyUpdated; }

	/** Console output for nycsim.PrintSun. */
	void PrintSun(FOutputDevice& Ar) const;

private:
	void EnsureSkyActors();
	void UpdateEphemeris();
	void ApplyToActors();
	void UpdateStreetLighting();
	void UpdateStarSphere();
	void WriteMaterialParameterCollection();
	/** UE exponential-fog density that reproduces a meteorological visibility (see the .cpp for the calibration). */
	static float FogDensityForVisibility(float VisibilityMetres);

	// clock
	double SimUnixSeconds = 0.0;
	bool bFollowRealTime = true;
	double TimeScale = 1.0;
	double TimeSinceEphemeris = 0.0;
	double TimeSinceSunEvents = 1e9;

	// state
	FNYCObserver Observer;
	FNYCSimTime SimTime;
	FNYCSunState Sun;
	FNYCMoonState Moon;
	FNYCSunEvents RiseSet;
	FNYCSunEvents CivilEvents;
	FNYCAtmosphereParams Atmosphere;
	bool bStreetLightsOn = false;
	bool bEphemerisValid = false;
	FString ClockError;

	// actors
	UPROPERTY(Transient)
	TObjectPtr<ADirectionalLight> SunLight;

	UPROPERTY(Transient)
	TObjectPtr<ADirectionalLight> MoonLight;

	UPROPERTY(Transient)
	TObjectPtr<ASkyAtmosphere> SkyAtmosphere;

	UPROPERTY(Transient)
	TObjectPtr<AVolumetricCloud> VolumetricCloud;

	UPROPERTY(Transient)
	TObjectPtr<AExponentialHeightFog> HeightFog;

	UPROPERTY(Transient)
	TObjectPtr<ASkyLight> SkyLight;

	UPROPERTY(Transient)
	TObjectPtr<AStaticMeshActor> StarSphere;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> CloudMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> StarMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> ParameterCollection;

	FNYCOnStreetLightingChanged StreetLightingChanged;
	FNYCOnSkyUpdated SkyUpdated;
};
