#include "Audio/NYCAmbienceEmitter.h"

#include "Audio/NYCProceduralSourceComponent.h"
#include "Components/AudioComponent.h"
#include "NYCSimRuntime.h"

namespace
{
/// The zones this build can synthesise when no licensed recording is imported for them.
bool HasSynthesiser(ENYCAmbienceZone Zone)
{
	return Zone == ENYCAmbienceZone::SubwayGrate || Zone == ENYCAmbienceZone::SteamVent ||
		   Zone == ENYCAmbienceZone::TrafficBed;
}

ENYCSourceKind SourceKindFor(ENYCAmbienceZone Zone)
{
	switch (Zone)
	{
	case ENYCAmbienceZone::SubwayGrate: return ENYCSourceKind::Rumble;
	case ENYCAmbienceZone::SteamVent: return ENYCSourceKind::Steam;
	// Distant traffic is tyre-on-road noise: broadband, its centre frequency rising with speed. That is exactly
	// what the tyre generator produces, and here it is driven by the vehicles the simulation actually has in the
	// zone rather than by a recording of somebody else's street.
	default: return ENYCSourceKind::Tyre;
	}
}

/// An idling queue still makes noise, so the generator never sees a speed of zero.
constexpr float kMinBedSpeedMps = 2.5f;
}  // namespace

ANYCAmbienceEmitter::ANYCAmbienceEmitter()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	SetActorEnableCollision(false);

	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	// Emitters are re-pointed at zones as the player moves, so nothing here may be a static component.
	Root->SetMobility(EComponentMobility::Movable);
	SetRootComponent(Root);

	Loop = CreateDefaultSubobject<UAudioComponent>(TEXT("Loop"));
	Loop->SetupAttachment(Root);
	Loop->SetMobility(EComponentMobility::Movable);
	Loop->bAutoActivate = false;
	Loop->bAllowSpatialization = true;
	Loop->bIsUISound = false;
	Loop->bStopWhenOwnerDestroyed = true;

	Synth = CreateDefaultSubobject<UNYCProceduralSourceComponent>(TEXT("Synth"));
	Synth->SetupAttachment(Root);
	Synth->SetMobility(EComponentMobility::Movable);
	Synth->bAutoActivate = false;
	Synth->bAllowSpatialization = true;
}

void ANYCAmbienceEmitter::ScheduleNextTrain()
{
	// Uniform in [0.55, 1.45] x headway. NYCT publishes headways, not timetables, for the numbered and lettered
	// lines below 20-minute frequencies, and the observed spread around a published headway is about this wide.
	RandomState = RandomState * 1664525u + 1013904223u;
	const float U = static_cast<float>(RandomState >> 8) * (1.f / 16777216.f);
	NextTrainSeconds = HeadwaySeconds * (0.55f + 0.90f * U);
}

void ANYCAmbienceEmitter::Assign(int32 InZoneHandle, ENYCAmbienceZone InZone, const FNYCAmbienceVoiceSpec& Spec)
{
	const bool bZoneChanged = ZoneHandle != InZoneHandle || Zone != InZone;
	if (bZoneChanged)
	{
		StopVoice();
	}

	ZoneHandle = InZoneHandle;
	Zone = InZone;
	RadiusMetres = FMath::Max(2.f, Spec.RadiusMetres);
	HeadwaySeconds = FMath::Max(20.f, Spec.HeadwaySeconds);
	// A licensed recording wins; the synthesiser is what runs when there is none.
	bSynthetic = Spec.LoopSound == nullptr && HasSynthesiser(InZone);
	RandomState = static_cast<uint32>(Spec.Seed) * 2654435761u + 0x9E3779B9u;

	SetActorLocation(Spec.Location);
	SetActorHiddenInGame(true);
	SetActorTickEnabled(true);

	if (bSynthetic)
	{
		if (Synth != nullptr)
		{
			Synth->SetKind(SourceKindFor(InZone));
			// Intensity is the zone's character, not its level: the level is SetSourceGain(), applied per tick.
			Synth->SetAmbience(1.f, InZone == ENYCAmbienceZone::SteamVent ? 0.8f : 0.35f);
			if (bZoneChanged)
			{
				Synth->AttenuationSettings = Spec.Attenuation;
				Synth->SetSourceGain(0.f);
			}
		}
		if (InZone == ENYCAmbienceZone::SubwayGrate && bZoneChanged)
		{
			ScheduleNextTrain();
		}
	}
	else if (Loop != nullptr && bZoneChanged)
	{
		// Attenuation has to be in place before Play(): the active sound copies it when it starts.
		Loop->AttenuationSettings = Spec.Attenuation;
		Loop->SetSound(Spec.LoopSound);
		Loop->SetVolumeMultiplier(0.f);
	}

	TargetGain = FMath::Clamp(Spec.Gain, 0.f, 2.f);
	if (TargetGain > 0.f)
	{
		StartVoice();
	}
}

void ANYCAmbienceEmitter::Release()
{
	StopVoice();
	ZoneHandle = INDEX_NONE;
	Gain = 0.f;
	TargetGain = 0.f;
	TrafficGain = 0.f;
	SetActorTickEnabled(false);
}

void ANYCAmbienceEmitter::StartVoice()
{
	if (bSynthetic)
	{
		if (Synth != nullptr && !bSynthRunning)
		{
			Synth->Start();
			bSynthRunning = true;
		}
		bAudible = Synth != nullptr;
		return;
	}
	if (Loop == nullptr || Loop->Sound == nullptr)
	{
		// No licensed recording for this zone kind; the subsystem reports it once and the zone stays silent.
		bAudible = false;
		return;
	}
	if (!Loop->IsPlaying())
	{
		Loop->Play();
	}
	bAudible = true;
}

void ANYCAmbienceEmitter::StopVoice()
{
	if (Synth != nullptr && bSynthRunning)
	{
		Synth->Stop();
		bSynthRunning = false;
	}
	if (Loop != nullptr && Loop->IsPlaying())
	{
		Loop->Stop();
	}
	bAudible = false;
}

void ANYCAmbienceEmitter::SetGain(float InGain)
{
	TargetGain = FMath::Clamp(InGain, 0.f, 2.f);
	if (TargetGain <= 0.0005f && Gain <= 0.0005f)
	{
		StopVoice();
	}
	else if (!bAudible)
	{
		StartVoice();
	}
}

void ANYCAmbienceEmitter::SetTrafficLevel(int32 Vehicles, float MeanSpeedMps)
{
	// Street-level Leq in Manhattan runs from about 55 dBA on an empty side street to 78 dBA on a busy avenue
	// (NYC DEP noise code studies). 23 dB is a factor of 14 in pressure, and the count-to-loudness relation is
	// logarithmic, so a log curve over the vehicles actually inside the zone is the right shape.
	const float N = static_cast<float>(FMath::Max(0, Vehicles));
	TrafficGain = FMath::Clamp(FMath::Loge(1.f + N) / FMath::Loge(1.f + 18.f), 0.f, 1.f);
	// Free-flowing traffic is brighter than a queue; 1.0 at 12 m/s, 0.92 at a standstill.
	TrafficPitch = FMath::Clamp(0.92f + 0.08f * (MeanSpeedMps / 12.f), 0.90f, 1.06f);
	TrafficSpeedMps = FMath::Max(kMinBedSpeedMps, MeanSpeedMps);
}

void ANYCAmbienceEmitter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (ZoneHandle == INDEX_NONE)
	{
		return;
	}

	// 0.5 s glide, so a zone coming into range fades up instead of clicking on.
	const float Alpha = FMath::Clamp(DeltaTime / 0.5f, 0.f, 1.f);
	Gain += (TargetGain - Gain) * Alpha;

	float Applied = Gain;
	if (Zone == ENYCAmbienceZone::TrafficBed)
	{
		Applied *= TrafficGain;
	}

	if (bSynthetic)
	{
		if (Synth != nullptr)
		{
			if (Zone == ENYCAmbienceZone::TrafficBed)
			{
				// Roughness 0.55 is a worn asphalt street; the bed carries no slip and no spray of its own.
				Synth->SetTyre(TrafficSpeedMps, 0.55f, 0.f, 0.f);
			}
			Synth->SetSourceGain(Applied);
			if (Zone == ENYCAmbienceZone::SubwayGrate)
			{
				NextTrainSeconds -= DeltaTime;
				if (NextTrainSeconds <= 0.f)
				{
					// Only worth voicing when someone can hear it.
					if (Applied > 0.02f)
					{
						Synth->TriggerTrainPass(FMath::Clamp(0.6f + 0.4f * Applied, 0.f, 1.f));
					}
					ScheduleNextTrain();
				}
			}
		}
	}
	else if (Loop != nullptr && Loop->IsPlaying())
	{
		Loop->SetVolumeMultiplier(Applied);
		if (Zone == ENYCAmbienceZone::TrafficBed)
		{
			Loop->SetPitchMultiplier(TrafficPitch);
		}
	}

	if (Applied <= 0.0005f && Gain <= 0.0005f && TargetGain <= 0.0005f)
	{
		StopVoice();
	}
}
