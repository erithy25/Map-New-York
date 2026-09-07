// The city's audio: what you hear that is not attached to your own car.
//
// Responsibilities:
//   * the ambience bed - a pool of ANYCAmbienceEmitter voices re-pointed at the nearest ambience zones, plus four
//     traffic-bed voices whose gain follows the vehicles the traffic simulation actually has around you;
//   * the one-shots the traffic simulation raises (a horn, a locked wheel) as pooled spatial voices;
//   * Doppler on moving emitters - sirens above all, which is the one place in the game where a wrong pitch is
//     immediately obvious;
//   * the weather bed on foot (rain and wind read from MPC_Weather, the same collection the car reads);
//   * the mix: six gain buses applied to everything this subsystem owns, to the car through
//     UNYCVehicleAudioComponent, and to the radio through UNYCRadioSubsystem.
//
// Ambience zones come from three places, all of them real data:
//   1. actor tags in the loaded world (the tag contract below), scanned at begin-play, on demand, and when the
//      listener has moved far enough that streaming will have brought new actors in;
//   2. explicit RegisterAmbienceZone() calls;
//   3. the four traffic-bed voices, whose level is measured from the live traffic simulation.
//
// Tag contract (an actor may carry more than one; the zone radius comes from the actor's bounds):
//   NYCAmbienceTraffic   a street or plaza that should carry a traffic bed of its own
//   NYCSubwayGrate       a sidewalk grate over a subway tunnel        (synthesised)
//   NYCSteamVent         a Con Edison steam vent                      (synthesised)
//   NYCPark              park interior (shared with the navmesh area tag)
//   NYCWaterfront        river edge, pier, esplanade
//   NYCConstruction      an active construction site
//   NYCCrowd             a place that carries crowd noise
//   NYCHelicopterCorridor the East River / Hudson helicopter routes
//
// Zone kinds with no licensed recording in assets/audio stay silent and are counted in GetStats().SilentZones;
// nothing is invented to fill them.
#pragma once

#include "Audio/NYCAmbienceEmitter.h"
#include "Audio/NYCProceduralSourceComponent.h"
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "NYCAudioSubsystem.generated.h"

class ANYCAmbienceEmitter;
class UAudioComponent;
class UMaterialParameterCollection;
class UNYCProceduralSourceComponent;
class UNYCRadioSubsystem;
class UNYCTrafficSubsystem;
class USoundAttenuation;
class USoundBase;

UENUM(BlueprintType)
enum class ENYCAudioBus : uint8
{
	Master = 0,
	Vehicle,
	Traffic,
	Ambience,
	Radio,
	UI,
	Count UMETA(Hidden)
};

/** One pooled spatial voice for a traffic horn or a tyre screech. */
USTRUCT()
struct FNYCOneShotVoice
{
	GENERATED_BODY()

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> Source = nullptr;

	/** Seconds left before the voice returns to the pool; <= 0 means free. */
	float Remaining = 0.f;

	/** Seconds left of the sounding part (the horn button held down, the wheel still locked). */
	float Sounding = 0.f;

	float Intensity = 0.f;
};

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCAudioStats
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 Zones = 0;

	/** Zones whose kind has no licensed recording imported, so they are silent. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 SilentZones = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 ActiveEmitters = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 EmitterPool = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 DopplerSources = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 ActiveOneShots = 0;

	/** One-shots dropped because every pooled voice was busy. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 DroppedOneShots = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	int32 TrafficBedVehicles = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	float RainRateMmH = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	float WindSpeedMps = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Audio")
	bool bListenerInVehicle = false;
};

UCLASS()
class NYCSIMRUNTIME_API UNYCAudioSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	UNYCAudioSubsystem();

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	// ---- one-shots raised by the traffic simulation ----------------------------------------------------------
	/** A simulated driver leaning on the horn. `Intensity` 0..1 is how long and how hard. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void PlayTrafficHorn(const FVector& Location, float Intensity);

	/** A locked wheel: `Intensity` 0..1 is the slip. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void PlayTyreScreech(const FVector& Location, float Intensity);

	/** Spatial one-shot from an imported sound (collision, glass, door). Null sound is a no-op. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void PlayOneShot(USoundBase* Sound, const FVector& Location, float Volume, float Pitch, float FalloffMetres);

	// ---- shared assets ---------------------------------------------------------------------------------------
	/** Loads (and caches) `<SfxContentRoot>/<BaseName>.<BaseName>`; null when that sound was never imported. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	USoundBase* FindSfx(const FString& BaseName);

	/** A cached natural-falloff attenuation with the given falloff distance, rounded to 10 m. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	USoundAttenuation* GetAttenuation(float FalloffMetres);

	// ---- Doppler ---------------------------------------------------------------------------------------------
	/** Registers a moving emitter for Doppler shift (sirens). Re-registering the same component is a no-op. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void RegisterDopplerSource(UAudioComponent* Component);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void UnregisterDopplerSource(UAudioComponent* Component);

	// ---- ambience --------------------------------------------------------------------------------------------
	/** Adds a zone that is not derived from an actor tag. Returns a handle for UnregisterAmbienceZone(). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	int32 RegisterAmbienceZone(ENYCAmbienceZone Zone, const FVector& Location, float RadiusMetres, float Gain);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void UnregisterAmbienceZone(int32 Handle);

	/** Re-derives the tag-driven zones from the actors currently loaded. Returns the zone count. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	int32 ScanWorldForAmbienceZones();

	// ---- mix -------------------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Audio")
	void SetBusGain(ENYCAudioBus Bus, float Gain);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	float GetBusGain(ENYCAudioBus Bus) const;

	/** Master x bus, the number a source should actually multiply its own gain by. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	float GetEffectiveGain(ENYCAudioBus Bus) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	FNYCAudioStats GetStats() const { return Stats; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Audio")
	FVector GetListenerLocation() const { return ListenerLocation; }

private:
	/** A place in the world that carries an ambience. Zones are records; emitters are the voices that play them. */
	struct FZoneRecord
	{
		FVector Location = FVector::ZeroVector;
		ENYCAmbienceZone Zone = ENYCAmbienceZone::TrafficBed;
		float RadiusMetres = 40.f;
		float Gain = 1.f;
		int32 Handle = INDEX_NONE;
		/** Set for tag-derived zones; a rescan rebuilds exactly these. */
		TWeakObjectPtr<AActor> SourceActor;
	};

	void UpdateListener(float DeltaTime);
	void UpdateWeather();
	void UpdateAmbience(float DeltaTime);
	void UpdateTrafficBed(float DeltaTime);
	void UpdateDoppler(float DeltaTime);
	void UpdateOneShots(float DeltaTime);
	void ApplyBusesToRadio();
	ANYCAmbienceEmitter* SpawnEmitter();
	UNYCProceduralSourceComponent* MakeVoice(ENYCSourceKind Kind, float FalloffMetres);
	int32 AcquireVoice(TArray<FNYCOneShotVoice>& Pool, int32 MaxVoices, ENYCSourceKind Kind, float FalloffMetres);
	USoundBase* LoopSoundFor(ENYCAmbienceZone Zone);
	float HeadwaySecondsForHour() const;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ANYCAmbienceEmitter>> Emitters;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ANYCAmbienceEmitter>> TrafficBedEmitters;

	UPROPERTY(Transient)
	TArray<FNYCOneShotVoice> HornVoices;

	UPROPERTY(Transient)
	TArray<FNYCOneShotVoice> ScreechVoices;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> WorldRain;

	UPROPERTY(Transient)
	TObjectPtr<UNYCProceduralSourceComponent> WorldWind;

	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<USoundBase>> SfxCache;

	UPROPERTY(Transient)
	TMap<int32, TObjectPtr<USoundAttenuation>> AttenuationCache;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> WeatherCollection;

	TArray<FZoneRecord> Zones;
	TMap<int32, int32> ZoneIndexByHandle;

	struct FDopplerSource
	{
		TWeakObjectPtr<UAudioComponent> Component;
		FVector LastLocation = FVector::ZeroVector;
		bool bHasLast = false;
	};
	TArray<FDopplerSource> DopplerSources;

	float BusGain[static_cast<int32>(ENYCAudioBus::Count)];

	FVector ListenerLocation = FVector::ZeroVector;
	FVector ListenerVelocity = FVector::ZeroVector;
	FVector ListenerForward = FVector::ForwardVector;
	FVector LastScanLocation = FVector::ZeroVector;
	FNYCAudioStats Stats;

	float RainRateMmH = 0.f;
	float WindSpeedMps = 0.f;
	float WeatherTimer = 0.f;
	float AmbienceTimer = 0.f;
	float ScanTimer = 0.f;
	int32 NextZoneHandle = 1;
	int32 MaxEmitters = 24;
	bool bListenerInVehicle = false;
	bool bHasRainRateParam = false;
	bool bHasWindSpeedParam = false;
	bool bBeganPlay = false;
	/** Zone kinds already reported as having no licensed recording, so the log says it once. */
	uint32 ReportedMissingLoops = 0;

	TArray<FAutoConsoleCommandWithWorldArgsAndOutputDevice*> ConsoleCommands;
};
