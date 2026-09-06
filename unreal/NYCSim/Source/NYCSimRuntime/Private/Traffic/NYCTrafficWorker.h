// The traffic/pedestrian worker thread.
//
// Runs TrafficSim and PedSim at a fixed 20 Hz (ARCHITECTURE §9) on a background thread and publishes each step
// through a double buffer. The game thread never touches the simulation: it writes the observer into a small
// input block under a lock and reads whichever snapshot buffer is currently the front one.
//
// Ordering inside a step (the one-frame coupling is deliberate and documented in the stage report):
//   1. the pedestrians see last step's vehicles (gap acceptance),
//   2. the vehicles see last step's pedestrians in the roadway (yielding),
//   3. traffic steps, then pedestrians step,
//   4. both snapshots are written to the back buffer and the buffers are swapped.
#pragma once

#include "CoreMinimal.h"
#include "HAL/Runnable.h"
#include "HAL/RunnableThread.h"
#include "HAL/ThreadSafeBool.h"
#include "Misc/ScopeLock.h"

#include <vector>

#include "CoreAdapter/GameplayPedSim.h"
#include "CoreAdapter/GameplayTrafficSim.h"

namespace nycsim_gameplay
{
class RoadNetwork;
}

/** One published simulation step. Plain data; copied wholesale by the swap. */
struct FNYCSimSnapshot
{
	double SimTime = 0.0;
	uint64 Step = 0;
	std::vector<nycsim_gameplay::VehicleSnapshot> Vehicles;
	std::vector<nycsim_gameplay::PedSnapshot> Peds;
	std::vector<nycsim_gameplay::TrafficEvent> Events;

	void Clear()
	{
		Vehicles.clear();
		Peds.clear();
		Events.clear();
	}
};

class FNYCTrafficWorker : public FRunnable
{
public:
	FNYCTrafficWorker();
	virtual ~FNYCTrafficWorker() override;

	/** Starts the thread. `Network` must stay alive and unmodified for the worker's lifetime. */
	bool Start(const nycsim_gameplay::RoadNetwork& Network, const nycsim_gameplay::TrafficConfig& TrafficConfig,
			   const nycsim_gameplay::PedConfig& PedConfig, FString& OutError);
	void Stop() override;
	void Shutdown();

	// FRunnable
	virtual uint32 Run() override;

	/** Game thread -> worker. Cheap: copies a small POD under a lock. */
	void SetObserver(const nycsim_gameplay::TrafficObserver& Observer);
	void SetTrafficConfig(const nycsim_gameplay::TrafficConfig& Config);
	void SetPedConfig(const nycsim_gameplay::PedConfig& Config);
	void SetPaused(bool bPaused) { bPausedFlag = bPaused; }

	/** Worker -> game thread. Copies the front buffer into `Out`; returns false when nothing new has been
	 *  published since `LastStep`. */
	bool ReadSnapshot(FNYCSimSnapshot& Out, uint64& InOutLastStep);

	/** Interpolation alpha between the published step and the next one, from the wall clock. */
	float GetInterpolationAlpha() const;

	double GetAverageTrafficStepMs() const { return AverageTrafficStepMs; }
	double GetAveragePedStepMs() const { return AveragePedStepMs; }
	uint32 GetVehicleCount() const { return PublishedVehicles; }
	uint32 GetPedCount() const { return PublishedPeds; }
	uint32 GetRedLightEntries() const { return PublishedRedLightEntries; }
	uint32 GetHonks() const { return PublishedHonks; }
	bool IsRunning() const { return Thread != nullptr && !bStopRequested; }

	/** Adds the bus routes from runtime/transit.nycb before the thread starts. */
	nycsim_gameplay::TrafficSim& MutableTrafficSim() { return Traffic; }

private:
	void StepOnce();

	nycsim_gameplay::TrafficSim Traffic;
	nycsim_gameplay::PedSim Peds;
	const nycsim_gameplay::RoadNetwork* Network = nullptr;

	FRunnableThread* Thread = nullptr;
	FThreadSafeBool bStopRequested{false};
	FThreadSafeBool bPausedFlag{false};

	mutable FCriticalSection InputLock;
	nycsim_gameplay::TrafficObserver PendingObserver;
	nycsim_gameplay::TrafficConfig PendingTrafficConfig;
	nycsim_gameplay::PedConfig PendingPedConfig;
	bool bTrafficConfigDirty = false;
	bool bPedConfigDirty = false;

	mutable FCriticalSection SnapshotLock;
	FNYCSimSnapshot Buffers[2];
	int32 FrontBuffer = 0;
	double LastPublishSeconds = 0.0;

	// Scratch owned by the worker thread.
	std::vector<nycsim_gameplay::PedObstacle> Obstacles;

	// Published statistics (written by the worker, read by the game thread; atomic-sized scalars).
	TAtomic<uint32> PublishedVehicles{0};
	TAtomic<uint32> PublishedPeds{0};
	TAtomic<uint32> PublishedRedLightEntries{0};
	TAtomic<uint32> PublishedHonks{0};
	double AverageTrafficStepMs = 0.0;
	double AveragePedStepMs = 0.0;
};
