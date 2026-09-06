#include "Audio/NYCAudioSubsystem.h"

#include "Audio/NYCAmbienceEmitter.h"
#include "Audio/NYCProceduralSourceComponent.h"
#include "Audio/NYCRadioSubsystem.h"
#include "Components/AudioComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "Traffic/NYCTrafficSubsystem.h"
#include "Vehicle/NYCPlayerVehicle.h"

namespace
{
constexpr float kCmPerMetre = 100.f;

/// Speed of sound in air at 15 C, metres per second.
constexpr float kSpeedOfSound = 340.3f;

/// How often the ambience assignment is recomputed. Zones do not move and the listener is not a bullet.
constexpr float kAmbienceUpdateSeconds = 0.25f;

/// How often the weather parameters are read out of the material parameter collection.
constexpr float kWeatherUpdateSeconds = 0.25f;

/// The listener has to move this far before a tag rescan is worth doing (streaming will have brought actors in).
constexpr float kRescanDistanceMetres = 400.f;

/// Minimum seconds between tag rescans, whatever the movement.
constexpr float kRescanIntervalSeconds = 10.f;

/// Traffic-bed geometry: four voices at this distance, each measuring this radius.
constexpr float kTrafficBedOffsetMetres = 30.f;
constexpr float kTrafficBedRadiusMetres = 70.f;

/// The four traffic-bed directions, in world axes.
const FVector kTrafficBedOffsets[4] = {FVector(1.f, 0.f, 0.f), FVector(-1.f, 0.f, 0.f), FVector(0.f, 1.f, 0.f),
									   FVector(0.f, -1.f, 0.f)};

constexpr int32 kMaxHornVoices = 8;
constexpr int32 kMaxScreechVoices = 6;

constexpr int32 kZoneKindCount = static_cast<int32>(ENYCAmbienceZone::Count);

/// The actor tags that make an ambience zone, in ENYCAmbienceZone order.
const TCHAR* const kZoneTags[] = {
	TEXT("NYCAmbienceTraffic"), TEXT("NYCSubwayGrate"),  TEXT("NYCSteamVent"), TEXT("NYCPark"),
	TEXT("NYCWaterfront"),      TEXT("NYCConstruction"), TEXT("NYCCrowd"),     TEXT("NYCHelicopterCorridor"),
};
static_assert(static_cast<int32>(UE_ARRAY_COUNT(kZoneTags)) == kZoneKindCount,
			  "kZoneTags must cover every ENYCAmbienceZone");

/// The imported sound each zone kind prefers. Empty means "always synthesised"; a name that is not imported
/// means the zone is synthesised if it has a generator and silent if it does not.
///
/// Nothing here maps to assets/audio/sfx/traffic_bed_1.ogg: the Commons search for a city traffic ambience
/// returned a railway-station tunnel recorded in Tampere. It is licensed (CC-BY-4.0) and kept with its record,
/// but it is not a New York street, so no zone plays it.
const TCHAR* const kZoneLoops[] = {
	TEXT("amb_traffic"),    TEXT(""),                 TEXT(""),          TEXT("amb_park"),
	TEXT("amb_waterfront"), TEXT("amb_construction"), TEXT("amb_crowd"), TEXT("amb_helicopter"),
};
static_assert(static_cast<int32>(UE_ARRAY_COUNT(kZoneLoops)) == kZoneKindCount,
			  "kZoneLoops must cover every ENYCAmbienceZone");

const TCHAR* ZoneName(ENYCAmbienceZone Zone)
{
	const int32 Index = static_cast<int32>(Zone);
	return Index >= 0 && Index < kZoneKindCount ? kZoneTags[Index] : TEXT("?");
}

const TCHAR* BusName(ENYCAudioBus Bus)
{
	switch (Bus)
	{
	case ENYCAudioBus::Master: return TEXT("master");
	case ENYCAudioBus::Vehicle: return TEXT("vehicle");
	case ENYCAudioBus::Traffic: return TEXT("traffic");
	case ENYCAudioBus::Ambience: return TEXT("ambience");
	case ENYCAudioBus::Radio: return TEXT("radio");
	case ENYCAudioBus::UI: return TEXT("ui");
	default: return TEXT("?");
	}
}
}  // namespace

UNYCAudioSubsystem::UNYCAudioSubsystem()
{
	for (int32 i = 0; i < static_cast<int32>(ENYCAudioBus::Count); ++i)
	{
		BusGain[i] = 1.f;
	}
}

bool UNYCAudioSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World != nullptr && World->IsGameWorld();
}

TStatId UNYCAudioSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCAudioSubsystem, STATGROUP_Tickables);
}

void UNYCAudioSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	MaxEmitters = FMath::Clamp(Settings.MaxAmbienceEmitters, 0, 64);
	BusGain[static_cast<int32>(ENYCAudioBus::Master)] = FMath::Clamp(Settings.MasterVolume, 0.f, 2.f);

	WeatherCollection = Cast<UMaterialParameterCollection>(Settings.WeatherParameterCollection.TryLoad());
	if (WeatherCollection != nullptr)
	{
		for (const FCollectionScalarParameter& Param : WeatherCollection->ScalarParameters)
		{
			if (Param.ParameterName == Settings.WeatherRainRateParameter)
			{
				bHasRainRateParam = true;
			}
			else if (Param.ParameterName == Settings.WeatherWindSpeedParameter)
			{
				bHasWindSpeedParam = true;
			}
		}
	}
	else
	{
		UE_LOG(LogNYCSim, Log,
			   TEXT("Audio: no weather collection at '%s'; the on-foot rain and wind bed stays silent."),
			   *Settings.WeatherParameterCollection.ToString());
	}

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.audio.stats"), TEXT("Ambience, one-shot and Doppler counts."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				Ar.Logf(TEXT("zones %d (%d silent)  emitters %d/%d  one-shots %d (dropped %d)  doppler %d"),
						Stats.Zones, Stats.SilentZones, Stats.ActiveEmitters, Stats.EmitterPool, Stats.ActiveOneShots,
						Stats.DroppedOneShots, Stats.DopplerSources);
				Ar.Logf(TEXT("traffic bed %d vehicles  rain %.2f mm/h  wind %.1f m/s  listener %s"),
						Stats.TrafficBedVehicles, Stats.RainRateMmH, Stats.WindSpeedMps,
						Stats.bListenerInVehicle ? TEXT("in vehicle") : TEXT("on foot"));
				for (int32 i = 0; i < static_cast<int32>(ENYCAudioBus::Count); ++i)
				{
					Ar.Logf(TEXT("  bus %-9s %.2f"), BusName(static_cast<ENYCAudioBus>(i)), BusGain[i]);
				}
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.audio.zones"), TEXT("List the ambience zones nearest the listener."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				int32 Listed = 0;
				for (const FZoneRecord& Zone : Zones)
				{
					const float DistanceM =
						static_cast<float>(FVector::Dist(Zone.Location, ListenerLocation)) / kCmPerMetre;
					if (DistanceM > 600.f || Listed >= 40)
					{
						continue;
					}
					++Listed;
					Ar.Logf(TEXT("  %-22s %6.0f m  r=%.0f m  gain %.2f%s"), ZoneName(Zone.Zone), DistanceM,
							Zone.RadiusMetres, Zone.Gain,
							LoopSoundFor(Zone.Zone) == nullptr ? TEXT("  [synthesised or silent]") : TEXT(""));
				}
				Ar.Logf(TEXT("%d of %d zones within 600 m"), Listed, Zones.Num());
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.audio.rescan"), TEXT("Re-derive the tag-driven ambience zones from the loaded actors."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				Ar.Logf(TEXT("%d ambience zones"), ScanWorldForAmbienceZones());
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.audio.bus"), TEXT("nycsim.audio.bus <master|vehicle|traffic|ambience|radio|ui> <gain>"),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>& Args, UWorld*, FOutputDevice& Ar) {
				if (Args.Num() < 2)
				{
					Ar.Logf(TEXT("nycsim.audio.bus <bus> <gain>"));
					return;
				}
				for (int32 i = 0; i < static_cast<int32>(ENYCAudioBus::Count); ++i)
				{
					const ENYCAudioBus Bus = static_cast<ENYCAudioBus>(i);
					if (Args[0].Equals(BusName(Bus), ESearchCase::IgnoreCase))
					{
						SetBusGain(Bus, FCString::Atof(*Args[1]));
						Ar.Logf(TEXT("bus %s = %.2f"), BusName(Bus), BusGain[i]);
						return;
					}
				}
				Ar.Logf(TEXT("unknown bus '%s'"), *Args[0]);
			})));
}

void UNYCAudioSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	bBeganPlay = true;

	ScanWorldForAmbienceZones();

	// Four traffic-bed voices around the listener. They are separate from the zone pool because their level comes
	// from the traffic simulation rather than from a placed zone.
	for (int32 i = 0; i < 4; ++i)
	{
		if (ANYCAmbienceEmitter* Emitter = SpawnEmitter())
		{
			TrafficBedEmitters.Add(Emitter);
		}
	}

	// The on-foot weather bed. Non-spatialised: rain and wind are everywhere, not in one direction.
	WorldRain = NewObject<UNYCProceduralSourceComponent>(&InWorld, TEXT("NYCWorldRain"));
	WorldRain->SetMobility(EComponentMobility::Movable);
	WorldRain->SetKind(ENYCSourceKind::Rain);
	WorldRain->bAllowSpatialization = false;
	WorldRain->SetSourceGain(0.f);
	WorldRain->RegisterComponentWithWorld(&InWorld);

	WorldWind = NewObject<UNYCProceduralSourceComponent>(&InWorld, TEXT("NYCWorldWind"));
	WorldWind->SetMobility(EComponentMobility::Movable);
	WorldWind->SetKind(ENYCSourceKind::Wind);
	WorldWind->bAllowSpatialization = false;
	WorldWind->SetSourceGain(0.f);
	WorldWind->RegisterComponentWithWorld(&InWorld);

	ApplyBusesToRadio();
}

void UNYCAudioSubsystem::Deinitialize()
{
	for (FAutoConsoleCommandWithWorldArgsAndOutputDevice* Command : ConsoleCommands)
	{
		delete Command;
	}
	ConsoleCommands.Empty();

	for (FNYCOneShotVoice& Voice : HornVoices)
	{
		if (Voice.Source != nullptr)
		{
			Voice.Source->Stop();
		}
	}
	for (FNYCOneShotVoice& Voice : ScreechVoices)
	{
		if (Voice.Source != nullptr)
		{
			Voice.Source->Stop();
		}
	}
	if (WorldRain != nullptr)
	{
		WorldRain->Stop();
	}
	if (WorldWind != nullptr)
	{
		WorldWind->Stop();
	}
	for (ANYCAmbienceEmitter* Emitter : Emitters)
	{
		if (Emitter != nullptr)
		{
			Emitter->Release();
		}
	}
	for (ANYCAmbienceEmitter* Emitter : TrafficBedEmitters)
	{
		if (Emitter != nullptr)
		{
			Emitter->Release();
		}
	}
	Emitters.Empty();
	TrafficBedEmitters.Empty();
	DopplerSources.Empty();
	Zones.Empty();
	ZoneIndexByHandle.Empty();

	Super::Deinitialize();
}

// ---- assets -------------------------------------------------------------------------------------------------

USoundBase* UNYCAudioSubsystem::FindSfx(const FString& BaseName)
{
	if (BaseName.IsEmpty())
	{
		return nullptr;
	}
	if (TObjectPtr<USoundBase>* Found = SfxCache.Find(BaseName))
	{
		return *Found;
	}
	FString Root = UNYCGameplaySettings::Get().SfxContentRoot;
	Root.RemoveFromEnd(TEXT("/"));
	const FString Path = FString::Printf(TEXT("%s/%s.%s"), *Root, *BaseName, *BaseName);
	USoundBase* Sound = Cast<USoundBase>(FSoftObjectPath(Path).TryLoad());
	SfxCache.Add(BaseName, Sound);
	if (Sound == nullptr)
	{
		UE_LOG(LogNYCSim, Log, TEXT("Audio: '%s' is not imported."), *Path);
	}
	return Sound;
}

USoundAttenuation* UNYCAudioSubsystem::GetAttenuation(float FalloffMetres)
{
	const int32 Key = FMath::Clamp(FMath::RoundToInt(FalloffMetres / 10.f), 1, 200);
	if (TObjectPtr<USoundAttenuation>* Found = AttenuationCache.Find(Key))
	{
		return *Found;
	}

	USoundAttenuation* Attenuation = NewObject<USoundAttenuation>(this);
	FSoundAttenuationSettings& S = Attenuation->Attenuation;
	S.bAttenuate = true;
	S.bSpatialize = true;
	// Natural sound: the falloff is specified in decibels at the far edge, which is what a real source does.
	S.DistanceAlgorithm = EAttenuationDistanceModel::NaturalSound;
	S.dBAttenuationAtMax = -60.f;
	S.AttenuationShape = EAttenuationShape::Sphere;
	// The sphere radius is the full-volume region; the falloff starts at its surface.
	S.AttenuationShapeExtents = FVector(300.f, 0.f, 0.f);
	S.FalloffDistance = static_cast<float>(Key) * 10.f * kCmPerMetre;
	// Air absorbs the top end with distance; without this a horn 200 m away is as bright as one beside you.
	S.bAttenuateWithLPF = true;
	S.LPFRadiusMin = S.FalloffDistance * 0.25f;
	S.LPFRadiusMax = S.FalloffDistance;
	AttenuationCache.Add(Key, Attenuation);
	return Attenuation;
}

USoundBase* UNYCAudioSubsystem::LoopSoundFor(ENYCAmbienceZone Zone)
{
	const int32 Index = static_cast<int32>(Zone);
	if (Index < 0 || Index >= kZoneKindCount)
	{
		return nullptr;
	}
	const FString Name = kZoneLoops[Index];
	if (Name.IsEmpty())
	{
		return nullptr;
	}
	USoundBase* Sound = FindSfx(Name);
	if (Sound == nullptr && (ReportedMissingLoops & (1u << Index)) == 0)
	{
		ReportedMissingLoops |= (1u << Index);
		UE_LOG(LogNYCSim, Log,
			   TEXT("Audio: ambience zone '%s' has no licensed recording imported ('%s'); those zones stay silent."),
			   ZoneName(Zone), *Name);
	}
	return Sound;
}

// ---- zones --------------------------------------------------------------------------------------------------

int32 UNYCAudioSubsystem::RegisterAmbienceZone(ENYCAmbienceZone Zone, const FVector& Location, float RadiusMetres,
											   float Gain)
{
	FZoneRecord Record;
	Record.Location = Location;
	Record.Zone = Zone;
	Record.RadiusMetres = FMath::Clamp(RadiusMetres, 2.f, 800.f);
	Record.Gain = FMath::Clamp(Gain, 0.f, 2.f);
	Record.Handle = NextZoneHandle++;
	ZoneIndexByHandle.Add(Record.Handle, Zones.Num());
	Zones.Add(Record);
	Stats.Zones = Zones.Num();
	return Record.Handle;
}

void UNYCAudioSubsystem::UnregisterAmbienceZone(int32 Handle)
{
	const int32* IndexPtr = ZoneIndexByHandle.Find(Handle);
	if (IndexPtr == nullptr)
	{
		return;
	}
	const int32 Index = *IndexPtr;
	ZoneIndexByHandle.Remove(Handle);
	Zones.RemoveAtSwap(Index);
	if (Zones.IsValidIndex(Index))
	{
		ZoneIndexByHandle.Add(Zones[Index].Handle, Index);
	}
	for (ANYCAmbienceEmitter* Emitter : Emitters)
	{
		if (Emitter != nullptr && Emitter->GetZoneHandle() == Handle)
		{
			Emitter->Release();
		}
	}
	Stats.Zones = Zones.Num();
}

int32 UNYCAudioSubsystem::ScanWorldForAmbienceZones()
{
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return 0;
	}

	// Tag-derived zones are rebuilt wholesale; zones registered by code (SourceActor unset) survive.
	for (int32 i = Zones.Num() - 1; i >= 0; --i)
	{
		if (Zones[i].SourceActor.IsValid() || Zones[i].SourceActor.IsStale())
		{
			const int32 Handle = Zones[i].Handle;
			ZoneIndexByHandle.Remove(Handle);
			Zones.RemoveAtSwap(i);
			if (Zones.IsValidIndex(i))
			{
				ZoneIndexByHandle.Add(Zones[i].Handle, i);
			}
			for (ANYCAmbienceEmitter* Emitter : Emitters)
			{
				if (Emitter != nullptr && Emitter->GetZoneHandle() == Handle)
				{
					Emitter->Release();
				}
			}
		}
	}

	int32 Added = 0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (Actor == nullptr || Actor->Tags.Num() == 0)
		{
			continue;
		}
		for (int32 Kind = 0; Kind < kZoneKindCount; ++Kind)
		{
			if (!Actor->Tags.Contains(FName(kZoneTags[Kind])))
			{
				continue;
			}
			// The zone is as big as the actor: a park is hundreds of metres across, a steam vent is one.
			FVector Origin = FVector::ZeroVector;
			FVector Extent = FVector::ZeroVector;
			Actor->GetActorBounds(false, Origin, Extent);
			const float RadiusM = FMath::Clamp(
				static_cast<float>(FMath::Max(Extent.X, Extent.Y)) / kCmPerMetre, 3.f, 400.f);

			FZoneRecord Record;
			Record.Location = Origin;
			Record.Zone = static_cast<ENYCAmbienceZone>(Kind);
			Record.RadiusMetres = RadiusM;
			Record.Gain = 1.f;
			Record.Handle = NextZoneHandle++;
			Record.SourceActor = Actor;
			ZoneIndexByHandle.Add(Record.Handle, Zones.Num());
			Zones.Add(Record);
			++Added;
		}
	}

	LastScanLocation = ListenerLocation;
	ScanTimer = 0.f;
	Stats.Zones = Zones.Num();
	UE_LOG(LogNYCSim, Log, TEXT("Audio: %d tag-derived ambience zones (%d zones total)."), Added, Zones.Num());
	return Zones.Num();
}

ANYCAmbienceEmitter* UNYCAudioSubsystem::SpawnEmitter()
{
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	return World->SpawnActor<ANYCAmbienceEmitter>(ANYCAmbienceEmitter::StaticClass(), FTransform::Identity, Params);
}

// ---- mix ----------------------------------------------------------------------------------------------------

void UNYCAudioSubsystem::SetBusGain(ENYCAudioBus Bus, float Gain)
{
	const int32 Index = static_cast<int32>(Bus);
	if (Index < 0 || Index >= static_cast<int32>(ENYCAudioBus::Count))
	{
		return;
	}
	BusGain[Index] = FMath::Clamp(Gain, 0.f, 2.f);
	if (Bus == ENYCAudioBus::Radio || Bus == ENYCAudioBus::Master)
	{
		ApplyBusesToRadio();
	}
}

float UNYCAudioSubsystem::GetBusGain(ENYCAudioBus Bus) const
{
	const int32 Index = static_cast<int32>(Bus);
	return Index >= 0 && Index < static_cast<int32>(ENYCAudioBus::Count) ? BusGain[Index] : 1.f;
}

float UNYCAudioSubsystem::GetEffectiveGain(ENYCAudioBus Bus) const
{
	return GetBusGain(ENYCAudioBus::Master) * (Bus == ENYCAudioBus::Master ? 1.f : GetBusGain(Bus));
}

void UNYCAudioSubsystem::ApplyBusesToRadio()
{
	if (UWorld* World = GetWorld())
	{
		if (UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
		{
			Radio->SetVolume(UNYCGameplaySettings::Get().RadioVolume * GetEffectiveGain(ENYCAudioBus::Radio));
		}
	}
}

// ---- one-shots ----------------------------------------------------------------------------------------------

UNYCProceduralSourceComponent* UNYCAudioSubsystem::MakeVoice(ENYCSourceKind Kind, float FalloffMetres)
{
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return nullptr;
	}
	UNYCProceduralSourceComponent* Source = NewObject<UNYCProceduralSourceComponent>(World);
	// The voice is moved to wherever the event happened, so it must not be a static component.
	Source->SetMobility(EComponentMobility::Movable);
	Source->SetKind(Kind);
	Source->bAllowSpatialization = true;
	Source->AttenuationSettings = GetAttenuation(FalloffMetres);
	Source->SetSourceGain(0.f);
	Source->RegisterComponentWithWorld(World);
	return Source;
}

int32 UNYCAudioSubsystem::AcquireVoice(TArray<FNYCOneShotVoice>& Pool, int32 MaxVoices, ENYCSourceKind Kind,
									   float FalloffMetres)
{
	for (int32 i = 0; i < Pool.Num(); ++i)
	{
		if (Pool[i].Remaining <= 0.f && Pool[i].Source != nullptr)
		{
			return i;
		}
	}
	if (Pool.Num() >= MaxVoices)
	{
		++Stats.DroppedOneShots;
		return INDEX_NONE;
	}
	UNYCProceduralSourceComponent* Source = MakeVoice(Kind, FalloffMetres);
	if (Source == nullptr)
	{
		return INDEX_NONE;
	}
	FNYCOneShotVoice Voice;
	Voice.Source = Source;
	return Pool.Add(Voice);
}

void UNYCAudioSubsystem::PlayTrafficHorn(const FVector& Location, float Intensity)
{
	// A city horn carries a long way: 110 dB at 2 m is still audible 300 m down an avenue.
	const int32 Index = AcquireVoice(HornVoices, kMaxHornVoices, ENYCSourceKind::Horn, 300.f);
	if (Index == INDEX_NONE)
	{
		return;
	}
	FNYCOneShotVoice& Voice = HornVoices[Index];
	Voice.Intensity = FMath::Clamp(Intensity, 0.f, 1.f);
	// A tap is about 0.2 s; leaning on it is about a second.
	Voice.Sounding = 0.18f + 0.85f * Voice.Intensity;
	Voice.Remaining = Voice.Sounding + 0.35f;
	if (Voice.Source != nullptr)
	{
		Voice.Source->SetWorldLocation(Location);
		Voice.Source->SetSourceGain(FMath::Lerp(0.45f, 1.f, Voice.Intensity) *
									GetEffectiveGain(ENYCAudioBus::Traffic));
		Voice.Source->SetHornPressed(true);
		Voice.Source->Start();
	}
}

void UNYCAudioSubsystem::PlayTyreScreech(const FVector& Location, float Intensity)
{
	const int32 Index = AcquireVoice(ScreechVoices, kMaxScreechVoices, ENYCSourceKind::Tyre, 140.f);
	if (Index == INDEX_NONE)
	{
		return;
	}
	FNYCOneShotVoice& Voice = ScreechVoices[Index];
	Voice.Intensity = FMath::Clamp(Intensity, 0.f, 1.f);
	// A locked wheel at 30 mph stops in about 0.9 s; a hard brake that does not lock is shorter.
	Voice.Sounding = 0.35f + 0.55f * Voice.Intensity;
	Voice.Remaining = Voice.Sounding;
	if (Voice.Source != nullptr)
	{
		Voice.Source->SetWorldLocation(Location);
		Voice.Source->SetSourceGain(FMath::Lerp(0.5f, 1.f, Voice.Intensity) * GetEffectiveGain(ENYCAudioBus::Traffic));
		Voice.Source->SetTyre(12.f * Voice.Intensity, 0.5f, Voice.Intensity, 0.f);
		Voice.Source->Start();
	}
}

void UNYCAudioSubsystem::PlayOneShot(USoundBase* Sound, const FVector& Location, float Volume, float Pitch,
									 float FalloffMetres)
{
	UWorld* World = GetWorld();
	if (Sound == nullptr || World == nullptr)
	{
		return;
	}
	UGameplayStatics::PlaySoundAtLocation(World, Sound, Location, FRotator::ZeroRotator,
										  FMath::Clamp(Volume, 0.f, 2.f) * GetEffectiveGain(ENYCAudioBus::Traffic),
										  FMath::Clamp(Pitch, 0.4f, 2.f), 0.f, GetAttenuation(FalloffMetres));
}

void UNYCAudioSubsystem::UpdateOneShots(float DeltaTime)
{
	int32 Active = 0;
	for (FNYCOneShotVoice& Voice : HornVoices)
	{
		if (Voice.Remaining <= 0.f)
		{
			continue;
		}
		++Active;
		Voice.Remaining -= DeltaTime;
		Voice.Sounding -= DeltaTime;
		if (Voice.Source == nullptr)
		{
			continue;
		}
		if (Voice.Sounding <= 0.f)
		{
			Voice.Source->SetHornPressed(false);
		}
		if (Voice.Remaining <= 0.f)
		{
			Voice.Source->SetHornPressed(false);
			Voice.Source->Stop();
			Voice.Remaining = 0.f;
		}
	}
	for (FNYCOneShotVoice& Voice : ScreechVoices)
	{
		if (Voice.Remaining <= 0.f)
		{
			continue;
		}
		++Active;
		Voice.Remaining -= DeltaTime;
		if (Voice.Source == nullptr)
		{
			continue;
		}
		// The slip bleeds off as the wheel comes back under the driver.
		const float T = FMath::Clamp(Voice.Remaining / FMath::Max(0.01f, Voice.Sounding), 0.f, 1.f);
		Voice.Source->SetTyre(12.f * Voice.Intensity * T, 0.5f, Voice.Intensity * T, 0.f);
		if (Voice.Remaining <= 0.f)
		{
			Voice.Source->Stop();
			Voice.Remaining = 0.f;
		}
	}
	Stats.ActiveOneShots = Active;
}

// ---- Doppler ------------------------------------------------------------------------------------------------

void UNYCAudioSubsystem::RegisterDopplerSource(UAudioComponent* Component)
{
	if (Component == nullptr)
	{
		return;
	}
	for (const FDopplerSource& Source : DopplerSources)
	{
		if (Source.Component.Get() == Component)
		{
			return;
		}
	}
	FDopplerSource Source;
	Source.Component = Component;
	Source.LastLocation = Component->GetComponentLocation();
	Source.bHasLast = false;
	DopplerSources.Add(Source);
}

void UNYCAudioSubsystem::UnregisterDopplerSource(UAudioComponent* Component)
{
	for (int32 i = DopplerSources.Num() - 1; i >= 0; --i)
	{
		UAudioComponent* Existing = DopplerSources[i].Component.Get();
		if (Existing == Component || Existing == nullptr)
		{
			if (Existing != nullptr)
			{
				Existing->SetPitchMultiplier(1.f);
			}
			DopplerSources.RemoveAtSwap(i);
		}
	}
}

void UNYCAudioSubsystem::UpdateDoppler(float DeltaTime)
{
	if (DeltaTime <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	for (int32 i = DopplerSources.Num() - 1; i >= 0; --i)
	{
		FDopplerSource& Source = DopplerSources[i];
		UAudioComponent* Component = Source.Component.Get();
		if (Component == nullptr || !IsValid(Component))
		{
			DopplerSources.RemoveAtSwap(i);
			continue;
		}
		const FVector Location = Component->GetComponentLocation();
		if (!Source.bHasLast)
		{
			Source.LastLocation = Location;
			Source.bHasLast = true;
			continue;
		}
		const FVector VelocityCm = (Location - Source.LastLocation) / DeltaTime;
		Source.LastLocation = Location;

		const FVector ToListener = ListenerLocation - Location;
		const float DistanceCm = ToListener.Size();
		if (DistanceCm < 50.f)
		{
			Component->SetPitchMultiplier(1.f);
			continue;
		}
		const FVector Unit = ToListener / DistanceCm;
		// f' = f (c - v_listener.u) / (c - v_source.u), u pointing from the source to the listener: a source
		// closing on the listener has a positive component and raises the pitch, which is the sign that matters.
		const float SourceAlong = FMath::Clamp(static_cast<float>(FVector::DotProduct(VelocityCm, Unit)) / kCmPerMetre,
											   -60.f, 60.f);
		const float ListenerAlong =
			FMath::Clamp(static_cast<float>(FVector::DotProduct(ListenerVelocity, Unit)) / kCmPerMetre, -60.f, 60.f);
		const float Pitch = FMath::Clamp((kSpeedOfSound - ListenerAlong) / (kSpeedOfSound - SourceAlong), 0.78f, 1.28f);
		Component->SetPitchMultiplier(Pitch);
	}
	Stats.DopplerSources = DopplerSources.Num();
}

// ---- per-frame ----------------------------------------------------------------------------------------------

void UNYCAudioSubsystem::UpdateListener(float DeltaTime)
{
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	APlayerController* PC = World->GetFirstPlayerController();
	if (PC == nullptr)
	{
		return;
	}
	FVector Location = ListenerLocation;
	FRotator Rotation = FRotator::ZeroRotator;
	PC->GetPlayerViewPoint(Location, Rotation);
	if (DeltaTime > KINDA_SMALL_NUMBER)
	{
		const FVector Raw = (Location - ListenerLocation) / DeltaTime;
		// A camera cut is not a velocity: anything faster than 90 m/s is a teleport, not the player moving.
		ListenerVelocity = Raw.SizeSquared() > FMath::Square(9000.f) ? FVector::ZeroVector : Raw;
	}
	ListenerLocation = Location;
	ListenerForward = Rotation.Vector();
	bListenerInVehicle = Cast<ANYCPlayerVehicle>(PC->GetPawn()) != nullptr;
	Stats.bListenerInVehicle = bListenerInVehicle;
}

void UNYCAudioSubsystem::UpdateWeather()
{
	UWorld* World = GetWorld();
	if (World == nullptr || WeatherCollection == nullptr)
	{
		return;
	}
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (bHasRainRateParam)
	{
		RainRateMmH = FMath::Max(0.f, UKismetMaterialLibrary::GetScalarParameterValue(
										  World, WeatherCollection, Settings.WeatherRainRateParameter));
	}
	if (bHasWindSpeedParam)
	{
		WindSpeedMps = FMath::Max(0.f, UKismetMaterialLibrary::GetScalarParameterValue(
										   World, WeatherCollection, Settings.WeatherWindSpeedParameter));
	}
	Stats.RainRateMmH = RainRateMmH;
	Stats.WindSpeedMps = WindSpeedMps;

	// Inside the car you hear the cabin's own rain and wind sources, not the street's.
	const float Interior = bListenerInVehicle ? 0.15f : 1.f;
	const float Bus = GetEffectiveGain(ENYCAudioBus::Ambience);

	if (WorldRain != nullptr)
	{
		WorldRain->SetWorldLocation(ListenerLocation);
		WorldRain->SetRain(RainRateMmH, 0.f);
		WorldRain->SetSourceGain(RainRateMmH > 0.05f ? 0.8f * Interior * Bus : 0.f);
	}
	if (WorldWind != nullptr)
	{
		WorldWind->SetWorldLocation(ListenerLocation);
		// Street-level wind heard by a standing listener: the aperture term stands in for the open street.
		WorldWind->SetWind(WindSpeedMps, 1.f);
		WorldWind->SetSourceGain(WindSpeedMps > 0.5f ? 0.6f * Interior * Bus : 0.f);
	}
}

void UNYCAudioSubsystem::UpdateTrafficBed(float DeltaTime)
{
	(void)DeltaTime;
	UWorld* World = GetWorld();
	if (World == nullptr || TrafficBedEmitters.Num() == 0)
	{
		return;
	}
	UNYCTrafficSubsystem* Traffic = World->GetSubsystem<UNYCTrafficSubsystem>();
	const float Bus = GetEffectiveGain(ENYCAudioBus::Ambience);
	const float OffsetCm = kTrafficBedOffsetMetres * kCmPerMetre;
	int32 Total = 0;
	for (int32 i = 0; i < TrafficBedEmitters.Num() && i < 4; ++i)
	{
		ANYCAmbienceEmitter* Emitter = TrafficBedEmitters[i];
		if (Emitter == nullptr)
		{
			continue;
		}
		const FVector Centre = ListenerLocation + kTrafficBedOffsets[i] * OffsetCm;
		int32 Vehicles = 0;
		float MeanSpeed = 0.f;
		if (Traffic != nullptr)
		{
			Traffic->GetLocalTraffic(Centre, kTrafficBedRadiusMetres, Vehicles, MeanSpeed);
		}
		Total += Vehicles;

		FNYCAmbienceVoiceSpec Spec;
		Spec.Location = Centre;
		Spec.RadiusMetres = kTrafficBedRadiusMetres;
		Spec.Gain = Bus;
		Spec.LoopSound = LoopSoundFor(ENYCAmbienceZone::TrafficBed);
		Spec.Attenuation = GetAttenuation(kTrafficBedRadiusMetres * 2.f);
		Spec.Seed = i;
		// The handle is negative so it can never collide with a real zone handle.
		Emitter->Assign(-1 - i, ENYCAmbienceZone::TrafficBed, Spec);
		Emitter->SetTrafficLevel(Vehicles, MeanSpeed);
		Emitter->SetGain(Bus);
	}
	Stats.TrafficBedVehicles = Total;
}

void UNYCAudioSubsystem::UpdateAmbience(float DeltaTime)
{
	(void)DeltaTime;
	if (MaxEmitters <= 0)
	{
		return;
	}

	// Everything within earshot: the zone's own radius plus the distance its falloff still carries.
	struct FCandidate
	{
		int32 ZoneIndex;
		float DistanceSq;
	};
	TArray<FCandidate> Candidates;
	Candidates.Reserve(FMath::Min(Zones.Num(), 256));
	for (int32 i = 0; i < Zones.Num(); ++i)
	{
		const FZoneRecord& Zone = Zones[i];
		const float ReachCm = (Zone.RadiusMetres + 120.f) * kCmPerMetre;
		const float DistanceSq = static_cast<float>(FVector::DistSquared(Zone.Location, ListenerLocation));
		if (DistanceSq <= ReachCm * ReachCm)
		{
			Candidates.Add({i, DistanceSq});
		}
	}
	Candidates.Sort([](const FCandidate& A, const FCandidate& B) { return A.DistanceSq < B.DistanceSq; });
	if (Candidates.Num() > MaxEmitters)
	{
		Candidates.SetNum(MaxEmitters);
	}

	TSet<int32> Chosen;
	Chosen.Reserve(Candidates.Num());
	for (const FCandidate& Candidate : Candidates)
	{
		Chosen.Add(Zones[Candidate.ZoneIndex].Handle);
	}

	// Release the voices whose zone dropped out of the set.
	for (ANYCAmbienceEmitter* Emitter : Emitters)
	{
		if (Emitter != nullptr && Emitter->IsInUse() && !Chosen.Contains(Emitter->GetZoneHandle()))
		{
			Emitter->Release();
		}
	}

	const float Bus = GetEffectiveGain(ENYCAudioBus::Ambience);
	int32 Active = 0;
	int32 Silent = 0;
	for (const FCandidate& Candidate : Candidates)
	{
		const FZoneRecord& Zone = Zones[Candidate.ZoneIndex];

		int32 EmitterIndex = INDEX_NONE;
		for (int32 i = 0; i < Emitters.Num(); ++i)
		{
			if (Emitters[i] != nullptr && Emitters[i]->GetZoneHandle() == Zone.Handle)
			{
				EmitterIndex = i;
				break;
			}
		}
		if (EmitterIndex == INDEX_NONE)
		{
			for (int32 i = 0; i < Emitters.Num(); ++i)
			{
				if (Emitters[i] != nullptr && !Emitters[i]->IsInUse())
				{
					EmitterIndex = i;
					break;
				}
			}
		}
		if (EmitterIndex == INDEX_NONE && Emitters.Num() < MaxEmitters)
		{
			if (ANYCAmbienceEmitter* Emitter = SpawnEmitter())
			{
				EmitterIndex = Emitters.Add(Emitter);
			}
		}
		if (EmitterIndex == INDEX_NONE || Emitters[EmitterIndex] == nullptr)
		{
			continue;
		}

		FNYCAmbienceVoiceSpec Spec;
		Spec.Location = Zone.Location;
		Spec.RadiusMetres = Zone.RadiusMetres;
		Spec.Gain = Zone.Gain * Bus;
		Spec.HeadwaySeconds = HeadwaySecondsForHour();
		Spec.LoopSound = LoopSoundFor(Zone.Zone);
		Spec.Attenuation = GetAttenuation(Zone.RadiusMetres + 80.f);
		Spec.Seed = Zone.Handle;
		Emitters[EmitterIndex]->Assign(Zone.Handle, Zone.Zone, Spec);
		Emitters[EmitterIndex]->SetGain(Zone.Gain * Bus);

		if (Emitters[EmitterIndex]->IsAudible())
		{
			++Active;
		}
		else
		{
			++Silent;
		}
	}

	Stats.ActiveEmitters = Active;
	Stats.SilentZones = Silent;
	Stats.EmitterPool = Emitters.Num() + TrafficBedEmitters.Num();
	Stats.Zones = Zones.Num();
}

float UNYCAudioSubsystem::HeadwaySecondsForHour() const
{
	// NYCT scheduled headways on a trunk line: about 2-5 min in the peaks, 8-10 min midday, 20 min overnight.
	int32 Hour = 8;
	if (UWorld* World = GetWorld())
	{
		if (UNYCTrafficSubsystem* Traffic = World->GetSubsystem<UNYCTrafficSubsystem>())
		{
			Hour = Traffic->GetHour();
		}
	}
	if ((Hour >= 7 && Hour < 10) || (Hour >= 16 && Hour < 19))
	{
		return 180.f;
	}
	if (Hour >= 0 && Hour < 5)
	{
		return 1200.f;
	}
	return 540.f;
}

void UNYCAudioSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!bBeganPlay)
	{
		return;
	}

	UpdateListener(DeltaTime);
	UpdateDoppler(DeltaTime);
	UpdateOneShots(DeltaTime);

	WeatherTimer += DeltaTime;
	if (WeatherTimer >= kWeatherUpdateSeconds)
	{
		WeatherTimer = 0.f;
		UpdateWeather();
	}

	AmbienceTimer += DeltaTime;
	if (AmbienceTimer >= kAmbienceUpdateSeconds)
	{
		UpdateAmbience(AmbienceTimer);
		UpdateTrafficBed(AmbienceTimer);
		AmbienceTimer = 0.f;
	}

	// Streaming brings new tagged actors in as the player crosses the city; rescan when they have moved far
	// enough for that to be true, and never more often than every ten seconds.
	ScanTimer += DeltaTime;
	if (ScanTimer >= kRescanIntervalSeconds &&
		FVector::DistSquared(ListenerLocation, LastScanLocation) >
			FMath::Square(kRescanDistanceMetres * kCmPerMetre))
	{
		ScanWorldForAmbienceZones();
	}
}
