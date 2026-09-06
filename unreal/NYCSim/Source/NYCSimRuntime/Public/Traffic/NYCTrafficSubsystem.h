// Drives the city's traffic and pedestrians.
//
// The simulation itself runs on a worker thread at a fixed 20 Hz (FNYCTrafficWorker) over the shared road network
// (UNYCRoadNetworkSubsystem). This subsystem is the game-thread half: it publishes the observer, reads the latest
// double-buffered snapshot, and maps agents onto pooled actors — no actor is ever spawned or destroyed while
// driving, which is what keeps the frame time flat.
//
// Pool policy
//   * one ANYCTrafficVehicle per live vehicle agent, up to MaxTrafficVehicles;
//   * one ANYCPedestrian per live pedestrian agent, up to MaxPedestrians;
//   * the pool grows on demand up to those caps and never shrinks;
//   * an actor whose agent has gone is released this frame and is reused on the next one;
//   * distance-based LOD, with the cutoffs in UNYCGameplaySettings.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "NYCTrafficSubsystem.generated.h"

class ANYCPedestrian;
class ANYCPlayerVehicle;
class ANYCTrafficVehicle;
class UNYCRoadNetworkSubsystem;
class USkeletalMesh;
class USoundBase;
class UAnimSequence;
class FNYCTrafficWorker;
struct FNYCSimSnapshot;

/** Live counters for the HUD and the console. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCTrafficStats
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 Vehicles = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 Pedestrians = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 VehicleActorsPooled = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 PedestrianActorsPooled = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	float TrafficStepMs = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	float PedStepMs = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 Honks = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 RedLightEntries = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 MissingFleetMeshes = 0;
};

UCLASS()
class NYCSIMRUNTIME_API UNYCTrafficSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	UNYCTrafficSubsystem();

	// UWorldSubsystem
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// FTickableGameObject
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** The player's car; the spawn ring follows it and the AI brakes for it. Null when the player is on foot. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Traffic")
	void SetPlayerVehicle(ANYCPlayerVehicle* Vehicle);

	/** Sets the observer directly (used when the player is on foot or in a free camera). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Traffic")
	void SetObserverTransform(const FVector& Location, const FVector& Forward, float SpeedMps);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Traffic")
	void SetPaused(bool bPaused);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Traffic")
	bool IsPaused() const { return bPaused; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Traffic")
	FNYCTrafficStats GetStats() const { return Stats; }

	/** Time of day and day class the density model uses; the sky subsystem calls this when the clock moves. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Traffic")
	void SetTimeOfDay(int32 Hour, int32 DayClass);

	/** Weather coupling: 0..1 wetness and snow cover, rain rate in mm/h, and whether headlights are due. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Traffic")
	void SetWeather(float Wetness, float SnowCover, float RainRateMmH, float TemperatureC, bool bHeadlights);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Traffic")
	void SetDensityScale(float VehicleScale, float PedestrianScale);

private:
	void TryStartWorker();
	void UpdateVehicles(const FNYCSimSnapshot& Snapshot, float DeltaTime);
	void UpdatePedestrians(const FNYCSimSnapshot& Snapshot, float DeltaTime);
	void DispatchEvents(const FNYCSimSnapshot& Snapshot);
	void PublishObserver();
	void LoadFleetAssets();
	void LoadCrowdAssets();
	USkeletalMesh* FleetMeshFor(uint8 VehicleClass);
	USkeletalMesh* CrowdMeshFor(uint8 Archetype);
	FLinearColor PaintFor(uint8 VehicleClass, int32 AgentId) const;
	/** Index into VehiclePool, or INDEX_NONE when the pool is at its cap. */
	int32 AcquireVehicleActor();
	/** Index into PedestrianPool, or INDEX_NONE when the pool is at its cap. */
	int32 AcquirePedestrianActor();
	int32 LodForDistance(float DistanceMetres, float FirstCutMetres) const;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ANYCTrafficVehicle>> VehiclePool;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ANYCPedestrian>> PedestrianPool;

	UPROPERTY(Transient)
	TMap<uint8, TObjectPtr<USkeletalMesh>> FleetMeshes;

	UPROPERTY(Transient)
	TMap<uint8, TObjectPtr<USkeletalMesh>> CrowdMeshes;

	UPROPERTY(Transient)
	TObjectPtr<USoundBase> SirenSound;

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> CrowdWalkClip;

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> CrowdIdleClip;

	UPROPERTY(Transient)
	TWeakObjectPtr<ANYCPlayerVehicle> PlayerVehicle;

	TUniquePtr<FNYCTrafficWorker> Worker;
	TUniquePtr<FNYCSimSnapshot> Snapshot;

	TMap<int32, int32> VehicleActorByAgent;
	TMap<int32, int32> PedestrianActorByAgent;
	TArray<int32> FreeVehicleActors;
	TArray<int32> FreePedestrianActors;
	TSet<int32> SeenAgents;

	FNYCTrafficStats Stats;
	FVector ObserverLocation = FVector::ZeroVector;
	FVector ObserverForward = FVector::ForwardVector;
	float ObserverSpeedMps = 0.f;
	uint64 LastConsumedStep = 0;
	bool bStarted = false;
	bool bPaused = false;
	bool bReportedMissingFleet = false;
	TArray<FAutoConsoleCommandWithWorldArgsAndOutputDevice*> ConsoleCommands;
};
