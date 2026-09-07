// The car radio.
//
// Reads the station list produced by unreal/tools/fetch_radio.py (assets/audio/radio/stations.json, copied into
// the packaged content by the import script) and plays the imported USoundWave for each track. Every track was
// fetched with a machine-checked licence — CC0, Public Domain or plain CC BY — and its provenance is recorded
// both in a per-file <track>.ogg.license.json and in the per-directory LICENSE.json the licence report scans.
//
// Behaviour of a real dial:
//   * stations keep playing while you are not listening, so tuning back lands mid-track, not at a track start;
//   * a station change costs a short burst of static;
//   * the announcer's "you're listening to ..." is not synthesised — nothing is invented; the station name and
//     the track title come from the licence records and are shown, not spoken.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "NYCRadioSubsystem.generated.h"

class UAudioComponent;
class USoundBase;
class USoundWave;

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCRadioTrack
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Title;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Artist;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Licence;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString LicenceUrl;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	float DurationSeconds = 0.f;

	/** Loudness-normalisation gain the fetcher measured, decibels. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	float GainDb = 0.f;

	/** Content path of the imported sound wave. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString SoundPath;
};

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCRadioStation
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Id;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Name;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	float FrequencyMhz = 0.f;

	/** "FM" or "AM". */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Band;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	FString Genre;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Radio")
	TArray<FNYCRadioTrack> Tracks;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FNYCRadioStationChanged, int32, StationIndex, const FString&,
											 StationName);

UCLASS()
class NYCSIMRUNTIME_API UNYCRadioSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	UNYCRadioSubsystem();

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Radio")
	int32 GetStationCount() const { return Stations.Num(); }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Radio")
	bool GetStation(int32 Index, FNYCRadioStation& OutStation) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Radio")
	int32 GetCurrentStationIndex() const { return CurrentStation; }

	/** -1 = off. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Radio")
	void SetStation(int32 Index);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Radio")
	void NextStation();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Radio")
	void PreviousStation();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Radio")
	void SetPowerOn(bool bOn);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Radio")
	bool IsPowerOn() const { return bPowerOn; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Radio")
	void SetVolume(float Volume01);

	/** The line the head unit shows: station, then the current track and its artist. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Radio")
	FString GetDisplayText() const;

	/** Attribution line for the CC-BY tracks, shown in the credits panel. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Radio")
	FString GetAttributionText() const;

	/** The audio component the car's head unit plays through; the vehicle attaches it to the cabin. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Radio")
	void AttachToVehicle(USceneComponent* Parent, FName SocketName);

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Radio")
	FNYCRadioStationChanged OnStationChanged;

private:
	bool LoadStations();
	void StartTrack(int32 StationIndex, int32 TrackIndex, float StartOffsetSeconds);
	void AdvanceTrack();
	USoundBase* LoadTrackSound(const FNYCRadioTrack& Track) const;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> Player;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> StaticPlayer;

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> StaticSound;

	TArray<FNYCRadioStation> Stations;
	/** Per station: which track is playing and how far into it, so a station keeps running while unheard. */
	TArray<int32> StationTrack;
	TArray<float> StationElapsed;

	int32 CurrentStation = -1;
	float Volume = 0.55f;
	float StaticTimer = 0.f;
	bool bPowerOn = false;
	bool bLoaded = false;
	FString LoadError;
	TArray<FAutoConsoleCommandWithWorldArgsAndOutputDevice*> ConsoleCommands;
};
