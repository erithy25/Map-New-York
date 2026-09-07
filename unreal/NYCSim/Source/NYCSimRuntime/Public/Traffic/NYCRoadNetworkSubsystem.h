// Owns the one copy of the lane graph, signal plans, density table and destination index that the whole gameplay
// lane shares (traffic, pedestrians, GPS, minimap).
//
// Loading a city-scale roadgraph.nycb is seconds of work, so it happens on a worker thread; everything that needs
// it either waits on OnNetworkReady or polls IsReady(). After the load nothing mutates, so the graph can be read
// from the traffic worker thread and the game thread at the same time without a lock.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "NYCRoadNetworkSubsystem.generated.h"

namespace nycsim_gameplay
{
class RoadNetwork;
}

DECLARE_MULTICAST_DELEGATE_OneParam(FNYCRoadNetworkReady, bool /*bSuccess*/);

/** Counts surfaced to Blueprint and to the console command. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCRoadNetworkInfo
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	int32 Nodes = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	int32 Segments = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	int32 RoadLanes = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	int32 JunctionLanes = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	int32 SignalPlans = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	int32 SearchEntries = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	float LoadSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Roads")
	bool bSynthetic = false;
};

UCLASS()
class NYCSIMRUNTIME_API UNYCRoadNetworkSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	UNYCRoadNetworkSubsystem();

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Roads")
	bool IsReady() const { return bReady; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Roads")
	FNYCRoadNetworkInfo GetInfo() const { return Info; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Roads")
	FString GetLoadError() const { return LoadError; }

	/** Non-fatal notes from the load (missing optional files, unbound signal nodes, ...). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Roads")
	TArray<FString> GetNotes() const { return Notes; }

	/** Nullptr until IsReady(). Read-only and thread-safe once non-null. */
	const nycsim_gameplay::RoadNetwork* GetNetwork() const { return bReady ? Network.Get() : nullptr; }

	/** Fires on the game thread when the load finishes (immediately if it already has). */
	FNYCRoadNetworkReady OnNetworkReady;

	/** Re-loads from disk (used after the import commandlet copies new runtime data). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Roads")
	void Reload();

private:
	void StartLoad();
	void FinishLoad(bool bSuccess);

	TUniquePtr<nycsim_gameplay::RoadNetwork> Network;
	FNYCRoadNetworkInfo Info;
	FString LoadError;
	TArray<FString> Notes;
	TAtomic<bool> bLoading{false};
	bool bReady = false;
	FAutoConsoleCommandWithWorldArgsAndOutputDevice* InfoCommand = nullptr;
};
