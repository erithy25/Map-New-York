#include "Audio/NYCRadioSubsystem.h"

#include "Components/AudioComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"

namespace
{
/// Static burst when the dial moves, seconds.
constexpr float kTuningStaticSeconds = 0.35f;
}  // namespace

UNYCRadioSubsystem::UNYCRadioSubsystem() = default;

bool UNYCRadioSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World != nullptr && World->IsGameWorld();
}

void UNYCRadioSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	bLoaded = LoadStations();

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	Volume = Settings.RadioVolume;
	StaticSound = Cast<USoundBase>(
		FSoftObjectPath(FString::Printf(TEXT("%s/radio_static_1.radio_static_1"), *Settings.SfxContentRoot)).TryLoad());

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.radio.list"), TEXT("List the radio stations and their licences."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				if (!bLoaded)
				{
					Ar.Logf(TEXT("radio: no stations (%s)"), *LoadError);
					return;
				}
				for (int32 i = 0; i < Stations.Num(); ++i)
				{
					const FNYCRadioStation& Station = Stations[i];
					Ar.Logf(TEXT("%d. %.1f %s  %s  (%s, %d tracks)"), i, Station.FrequencyMhz, *Station.Band,
							*Station.Name, *Station.Genre, Station.Tracks.Num());
				}
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.radio.tune"), TEXT("nycsim.radio.tune <index> - tune the radio (-1 = off)."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>& Args, UWorld*, FOutputDevice& Ar) {
				const int32 Index = Args.Num() > 0 ? FCString::Atoi(*Args[0]) : -1;
				SetStation(Index);
				Ar.Logf(TEXT("%s"), *GetDisplayText());
			})));
}

void UNYCRadioSubsystem::Deinitialize()
{
	for (FAutoConsoleCommandWithWorldArgsAndOutputDevice* Command : ConsoleCommands)
	{
		delete Command;
	}
	ConsoleCommands.Reset();
	if (IsValid(Player))
	{
		Player->Stop();
		Player->DestroyComponent();
		Player = nullptr;
	}
	if (IsValid(StaticPlayer))
	{
		StaticPlayer->Stop();
		StaticPlayer->DestroyComponent();
		StaticPlayer = nullptr;
	}
	Super::Deinitialize();
}

TStatId UNYCRadioSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCRadioSubsystem, STATGROUP_Tickables);
}

bool UNYCRadioSubsystem::LoadStations()
{
	Stations.Reset();
	StationTrack.Reset();
	StationElapsed.Reset();
	LoadError.Reset();

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	const FString Path = UNYCGameplaySettings::ResolvePath(Settings.RadioStationsJson);
	FString Json;
	if (!FFileHelper::LoadFileToString(Json, *Path))
	{
		LoadError = FString::Printf(TEXT("stations.json not found at %s"), *Path);
		UE_LOG(LogNYCSim, Warning, TEXT("Radio: %s; the radio has no stations."), *LoadError);
		return false;
	}

	TSharedPtr<FJsonObject> Doc;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Doc) || !Doc.IsValid())
	{
		LoadError = TEXT("stations.json is not valid JSON");
		UE_LOG(LogNYCSim, Error, TEXT("Radio: %s"), *LoadError);
		return false;
	}
	const int32 SchemaVersion = Doc->GetIntegerField(TEXT("schema_version"));
	if (SchemaVersion != 1)
	{
		LoadError = FString::Printf(TEXT("stations.json schema_version %d is not 1"), SchemaVersion);
		UE_LOG(LogNYCSim, Error, TEXT("Radio: %s"), *LoadError);
		return false;
	}

	FString ContentRoot = Settings.RadioContentRoot;
	ContentRoot.RemoveFromEnd(TEXT("/"));

	const TArray<TSharedPtr<FJsonValue>>* StationArray = nullptr;
	if (!Doc->TryGetArrayField(TEXT("stations"), StationArray) || StationArray == nullptr)
	{
		LoadError = TEXT("stations.json has no 'stations' array");
		return false;
	}

	int32 TotalTracks = 0;
	for (const TSharedPtr<FJsonValue>& Value : *StationArray)
	{
		const TSharedPtr<FJsonObject> Object = Value->AsObject();
		if (!Object.IsValid())
		{
			continue;
		}
		FNYCRadioStation Station;
		Station.Id = Object->GetStringField(TEXT("id"));
		Station.Name = Object->GetStringField(TEXT("name"));
		Station.FrequencyMhz = static_cast<float>(Object->GetNumberField(TEXT("frequency_mhz")));
		Object->TryGetStringField(TEXT("band"), Station.Band);
		Object->TryGetStringField(TEXT("genre"), Station.Genre);

		const TArray<TSharedPtr<FJsonValue>>* TrackArray = nullptr;
		if (Object->TryGetArrayField(TEXT("tracks"), TrackArray) && TrackArray != nullptr)
		{
			for (const TSharedPtr<FJsonValue>& TrackValue : *TrackArray)
			{
				const TSharedPtr<FJsonObject> TrackObject = TrackValue->AsObject();
				if (!TrackObject.IsValid())
				{
					continue;
				}
				FNYCRadioTrack Track;
				Track.Title = TrackObject->GetStringField(TEXT("title"));
				TrackObject->TryGetStringField(TEXT("artist"), Track.Artist);
				TrackObject->TryGetStringField(TEXT("licence"), Track.Licence);
				TrackObject->TryGetStringField(TEXT("licence_url"), Track.LicenceUrl);
				Track.DurationSeconds = static_cast<float>(TrackObject->GetNumberField(TEXT("duration_s")));
				Track.GainDb = static_cast<float>(TrackObject->GetNumberField(TEXT("gain_db")));

				// The import manifest writes the content path it actually assigned into the index as
				// "sound_path", and that is the one to use. Deriving it here as well is how the two
				// disagreed: the manifest's safe_asset_name puts an underscore in front of a leading
				// digit, because a UE asset name may not begin with one, so "01_gunther_freischutz.ogg"
				// imports as _01_gunther_freischutz while the rule below looks for 01_gunther_freischutz.
				// The fallback stays for an index written before the manifest carried the field.
				FString ResolvedPath;
				if (TrackObject->TryGetStringField(TEXT("sound_path"), ResolvedPath) && !ResolvedPath.IsEmpty())
				{
					Track.SoundPath = ResolvedPath;
				}
				else
				{
					// "jazz/fluffy_ruffles_rag.ogg" -> /Game/NYCSim/Audio/Radio/jazz/fluffy_ruffles_rag
					const FString RelativeFile = TrackObject->GetStringField(TEXT("file"));
					FString Directory;
					FString FileName;
					if (!RelativeFile.Split(TEXT("/"), &Directory, &FileName))
					{
						Directory = Station.Id;
						FileName = RelativeFile;
					}
					const FString Stem = FPaths::GetBaseFilename(FileName);
					Track.SoundPath = FString::Printf(TEXT("%s/%s/%s.%s"), *ContentRoot, *Directory, *Stem, *Stem);
				}
				Station.Tracks.Add(MoveTemp(Track));
			}
		}
		if (Station.Tracks.Num() == 0)
		{
			continue;
		}
		TotalTracks += Station.Tracks.Num();
		Stations.Add(MoveTemp(Station));
	}

	StationTrack.Init(0, Stations.Num());
	StationElapsed.Init(0.f, Stations.Num());

	UE_LOG(LogNYCSim, Log, TEXT("Radio: %d stations, %d tracks from %s."), Stations.Num(), TotalTracks, *Path);
	return Stations.Num() > 0;
}

bool UNYCRadioSubsystem::GetStation(int32 Index, FNYCRadioStation& OutStation) const
{
	if (!Stations.IsValidIndex(Index))
	{
		return false;
	}
	OutStation = Stations[Index];
	return true;
}

USoundBase* UNYCRadioSubsystem::LoadTrackSound(const FNYCRadioTrack& Track) const
{
	return Cast<USoundBase>(FSoftObjectPath(Track.SoundPath).TryLoad());
}

void UNYCRadioSubsystem::AttachToVehicle(USceneComponent* Parent, FName SocketName)
{
	if (Parent == nullptr)
	{
		return;
	}
	AActor* Owner = Parent->GetOwner();
	if (Owner == nullptr)
	{
		return;
	}
	if (!IsValid(Player))
	{
		Player = NewObject<UAudioComponent>(Owner, TEXT("NYCRadioPlayer"));
		Player->bAutoActivate = false;
		Player->bAllowSpatialization = true;
		Player->RegisterComponent();
	}
	if (!IsValid(StaticPlayer))
	{
		StaticPlayer = NewObject<UAudioComponent>(Owner, TEXT("NYCRadioStatic"));
		StaticPlayer->bAutoActivate = false;
		StaticPlayer->bAllowSpatialization = true;
		StaticPlayer->SetSound(StaticSound);
		StaticPlayer->RegisterComponent();
	}
	Player->AttachToComponent(Parent, FAttachmentTransformRules::SnapToTargetNotIncludingScale, SocketName);
	StaticPlayer->AttachToComponent(Parent, FAttachmentTransformRules::SnapToTargetNotIncludingScale, SocketName);
}

void UNYCRadioSubsystem::StartTrack(int32 StationIndex, int32 TrackIndex, float StartOffsetSeconds)
{
	if (!Stations.IsValidIndex(StationIndex) || !IsValid(Player))
	{
		return;
	}
	const FNYCRadioStation& Station = Stations[StationIndex];
	if (!Station.Tracks.IsValidIndex(TrackIndex))
	{
		return;
	}
	const FNYCRadioTrack& Track = Station.Tracks[TrackIndex];
	USoundBase* Sound = LoadTrackSound(Track);
	if (Sound == nullptr)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Radio: sound '%s' is not imported; skipping '%s'."), *Track.SoundPath,
			   *Track.Title);
		return;
	}
	Player->SetSound(Sound);
	// The fetcher measured each track's loudness and stored the gain that brings it to -14 LUFS.
	Player->SetVolumeMultiplier(Volume * FMath::Pow(10.f, Track.GainDb / 20.f));
	Player->Play(FMath::Max(0.f, StartOffsetSeconds));
}

void UNYCRadioSubsystem::SetStation(int32 Index)
{
	const int32 Clamped = Stations.IsValidIndex(Index) ? Index : -1;
	if (Clamped == CurrentStation)
	{
		return;
	}
	CurrentStation = Clamped;

	if (IsValid(Player))
	{
		Player->Stop();
	}
	if (CurrentStation < 0)
	{
		OnStationChanged.Broadcast(-1, FString());
		return;
	}

	bPowerOn = true;
	StaticTimer = kTuningStaticSeconds;
	if (IsValid(StaticPlayer) && StaticPlayer->Sound != nullptr)
	{
		StaticPlayer->SetVolumeMultiplier(Volume * 0.6f);
		StaticPlayer->Play();
	}
	// Tuning in lands wherever that station happens to be, exactly like a real one.
	StartTrack(CurrentStation, StationTrack[CurrentStation], StationElapsed[CurrentStation]);
	OnStationChanged.Broadcast(CurrentStation, Stations[CurrentStation].Name);
}

void UNYCRadioSubsystem::NextStation()
{
	if (Stations.Num() == 0)
	{
		return;
	}
	SetStation(CurrentStation + 1 >= Stations.Num() ? 0 : CurrentStation + 1);
}

void UNYCRadioSubsystem::PreviousStation()
{
	if (Stations.Num() == 0)
	{
		return;
	}
	SetStation(CurrentStation <= 0 ? Stations.Num() - 1 : CurrentStation - 1);
}

void UNYCRadioSubsystem::SetPowerOn(bool bOn)
{
	bPowerOn = bOn;
	if (!bOn)
	{
		if (IsValid(Player))
		{
			Player->Stop();
		}
	}
	else if (CurrentStation >= 0)
	{
		StartTrack(CurrentStation, StationTrack[CurrentStation], StationElapsed[CurrentStation]);
	}
	else if (Stations.Num() > 0)
	{
		SetStation(0);
	}
}

void UNYCRadioSubsystem::SetVolume(float Volume01)
{
	Volume = FMath::Clamp(Volume01, 0.f, 1.f);
	if (IsValid(Player) && Stations.IsValidIndex(CurrentStation))
	{
		const FNYCRadioStation& Station = Stations[CurrentStation];
		if (Station.Tracks.IsValidIndex(StationTrack[CurrentStation]))
		{
			const float GainDb = Station.Tracks[StationTrack[CurrentStation]].GainDb;
			Player->SetVolumeMultiplier(Volume * FMath::Pow(10.f, GainDb / 20.f));
		}
	}
}

FString UNYCRadioSubsystem::GetDisplayText() const
{
	if (!bPowerOn || !Stations.IsValidIndex(CurrentStation))
	{
		return TEXT("RADIO OFF");
	}
	const FNYCRadioStation& Station = Stations[CurrentStation];
	const int32 TrackIndex = StationTrack[CurrentStation];
	if (!Station.Tracks.IsValidIndex(TrackIndex))
	{
		return FString::Printf(TEXT("%.1f %s  %s"), Station.FrequencyMhz, *Station.Band, *Station.Name);
	}
	const FNYCRadioTrack& Track = Station.Tracks[TrackIndex];
	return FString::Printf(TEXT("%.1f %s  %s  ·  %s — %s"), Station.FrequencyMhz, *Station.Band, *Station.Name,
						   *Track.Artist, *Track.Title);
}

FString UNYCRadioSubsystem::GetAttributionText() const
{
	if (!Stations.IsValidIndex(CurrentStation))
	{
		return FString();
	}
	const FNYCRadioStation& Station = Stations[CurrentStation];
	const int32 TrackIndex = StationTrack[CurrentStation];
	if (!Station.Tracks.IsValidIndex(TrackIndex))
	{
		return FString();
	}
	const FNYCRadioTrack& Track = Station.Tracks[TrackIndex];
	return FString::Printf(TEXT("%s — %s (%s)"), *Track.Artist, *Track.Title, *Track.Licence);
}

void UNYCRadioSubsystem::AdvanceTrack()
{
	if (!Stations.IsValidIndex(CurrentStation))
	{
		return;
	}
	const FNYCRadioStation& Station = Stations[CurrentStation];
	StationTrack[CurrentStation] = (StationTrack[CurrentStation] + 1) % Station.Tracks.Num();
	StationElapsed[CurrentStation] = 0.f;
	StartTrack(CurrentStation, StationTrack[CurrentStation], 0.f);
}

void UNYCRadioSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (Stations.Num() == 0)
	{
		return;
	}

	// Every station's playhead advances whether or not it is the one being listened to.
	for (int32 i = 0; i < Stations.Num(); ++i)
	{
		const FNYCRadioStation& Station = Stations[i];
		if (!Station.Tracks.IsValidIndex(StationTrack[i]))
		{
			StationTrack[i] = 0;
			StationElapsed[i] = 0.f;
			continue;
		}
		StationElapsed[i] += DeltaTime;
		const float Duration = FMath::Max(1.f, Station.Tracks[StationTrack[i]].DurationSeconds);
		if (StationElapsed[i] >= Duration)
		{
			StationElapsed[i] = 0.f;
			StationTrack[i] = (StationTrack[i] + 1) % Station.Tracks.Num();
			if (i == CurrentStation && bPowerOn)
			{
				StartTrack(i, StationTrack[i], 0.f);
			}
		}
	}

	if (StaticTimer > 0.f)
	{
		StaticTimer -= DeltaTime;
		if (StaticTimer <= 0.f && IsValid(StaticPlayer))
		{
			StaticPlayer->Stop();
		}
	}
}
