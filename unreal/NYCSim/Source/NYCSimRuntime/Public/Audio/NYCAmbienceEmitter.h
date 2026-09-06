// One voice of the city's ambience bed.
//
// Emitters are pooled by UNYCAudioSubsystem and re-pointed at whichever ambience zones are nearest the listener,
// exactly like the traffic and pedestrian actor pools: the zone list can be thousands of records long, the voice
// pool is a couple of dozen actors. They are not meant to be hand-placed - place a tagged actor (or call
// UNYCAudioSubsystem::RegisterAmbienceZone) and the pool will voice it.
//
// Three zone kinds are synthesised because no recording of them could be licensed from a source reachable here:
// a Con Edison steam vent, a subway grate, and the traffic bed itself - the last of which is better synthesised
// anyway, because it is then made of the traffic that is really around you rather than of somebody else's street.
// The rest play a licensed loop and stay silent while that loop is missing from the imported content, which the
// subsystem logs once per zone kind.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NYCAmbienceEmitter.generated.h"

class UAudioComponent;
class UNYCProceduralSourceComponent;
class USoundAttenuation;
class USoundBase;

UENUM(BlueprintType)
enum class ENYCAmbienceZone : uint8
{
	/** The rolling traffic bed: level and brightness follow the vehicles the simulation actually has in the zone
	 *  (synthesised from them unless a licensed street recording is imported as `amb_traffic`). */
	TrafficBed = 0,
	/** A subway grate: ventilation hum plus the swell of a train passing beneath (synthesised). */
	SubwayGrate,
	/** A Con Edison sidewalk steam vent (synthesised). */
	SteamVent,
	/** Park interior: birds and leaves. Needs a licensed recording. */
	Park,
	/** River edge: water against the bulkhead and the wind off the water. Needs a licensed recording. */
	Waterfront,
	/** An active construction site. Needs a licensed recording. */
	Construction,
	/** Sidewalk crowd babble (Times Square, Union Square, a subway entrance at rush hour). Needs a recording. */
	Crowd,
	/** The East River / Hudson helicopter corridors. Needs a licensed recording. */
	HelicopterCorridor,
	Count UMETA(Hidden)
};

/** Everything the subsystem hands an emitter when it points it at a zone. */
USTRUCT()
struct NYCSIMRUNTIME_API FNYCAmbienceVoiceSpec
{
	GENERATED_BODY()

	UPROPERTY()
	FVector Location = FVector::ZeroVector;

	UPROPERTY()
	float RadiusMetres = 40.f;

	UPROPERTY()
	float Gain = 1.f;

	/** Mean interval between train passes at a subway grate, seconds; from the line's headway at this hour. */
	UPROPERTY()
	float HeadwaySeconds = 300.f;

	UPROPERTY()
	TObjectPtr<USoundBase> LoopSound = nullptr;

	UPROPERTY()
	TObjectPtr<USoundAttenuation> Attenuation = nullptr;

	UPROPERTY()
	int32 Seed = 0;
};

UCLASS(NotPlaceable)
class NYCSIMRUNTIME_API ANYCAmbienceEmitter : public AActor
{
	GENERATED_BODY()

public:
	ANYCAmbienceEmitter();

	virtual void Tick(float DeltaTime) override;

	/** Points this voice at a zone. Safe to call on a voice that is already in use (it switches). */
	void Assign(int32 InZoneHandle, ENYCAmbienceZone InZone, const FNYCAmbienceVoiceSpec& Spec);

	/** Stops the voice and returns it to the pool. */
	void Release();

	bool IsInUse() const { return ZoneHandle != INDEX_NONE; }
	int32 GetZoneHandle() const { return ZoneHandle; }
	ENYCAmbienceZone GetZone() const { return Zone; }
	bool IsAudible() const { return bAudible; }

	/** 0..1 from the subsystem's distance falloff and bus gain; 0 stops the voice without releasing the zone. */
	void SetGain(float InGain);

	/** Traffic bed only: how much simulated traffic is actually inside the zone right now. */
	void SetTrafficLevel(int32 Vehicles, float MeanSpeedMps);

private:
	void StartVoice();
	void StopVoice();
	void ScheduleNextTrain();

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Audio")
	TObjectPtr<UAudioComponent> Loop;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Audio")
	TObjectPtr<UNYCProceduralSourceComponent> Synth;

	int32 ZoneHandle = INDEX_NONE;
	ENYCAmbienceZone Zone = ENYCAmbienceZone::TrafficBed;
	float Gain = 0.f;
	float TargetGain = 0.f;
	float RadiusMetres = 40.f;
	float HeadwaySeconds = 300.f;
	float NextTrainSeconds = 0.f;
	float TrafficGain = 0.f;
	float TrafficPitch = 1.f;
	float TrafficSpeedMps = 0.f;
	uint32 RandomState = 0x2545F491u;
	bool bSynthetic = false;
	bool bAudible = false;
	/** Tracked rather than asked of the synth, so the emitter never depends on USynthComponent::IsPlaying(). */
	bool bSynthRunning = false;
};
