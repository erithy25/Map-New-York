#include "Traffic/NYCTrafficWorker.h"

#include "CoreAdapter/GameplayRoadNetwork.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "NYCSimRuntime.h"

FNYCTrafficWorker::FNYCTrafficWorker() = default;

FNYCTrafficWorker::~FNYCTrafficWorker()
{
	Shutdown();
}

bool FNYCTrafficWorker::Start(const nycsim_gameplay::RoadNetwork& InNetwork,
							  const nycsim_gameplay::TrafficConfig& TrafficConfig,
							  const nycsim_gameplay::PedConfig& PedConfig, FString& OutError)
{
	OutError.Reset();
	Network = &InNetwork;

	std::string Error;
	if (!Traffic.init(InNetwork, TrafficConfig, Error))
	{
		OutError = UTF8_TO_TCHAR(Error.c_str());
		return false;
	}
	if (!Peds.init(InNetwork, PedConfig, Error))
	{
		OutError = UTF8_TO_TCHAR(Error.c_str());
		return false;
	}

	PendingTrafficConfig = TrafficConfig;
	PendingPedConfig = PedConfig;
	bStopRequested = false;
	LastPublishSeconds = FPlatformTime::Seconds();

	Thread = FRunnableThread::Create(this, TEXT("NYCSimTraffic"), 0, TPri_BelowNormal);
	if (Thread == nullptr)
	{
		OutError = TEXT("could not create the traffic worker thread");
		return false;
	}
	return true;
}

void FNYCTrafficWorker::Stop()
{
	bStopRequested = true;
}

void FNYCTrafficWorker::Shutdown()
{
	bStopRequested = true;
	if (Thread != nullptr)
	{
		Thread->WaitForCompletion();
		delete Thread;
		Thread = nullptr;
	}
	Network = nullptr;
}

void FNYCTrafficWorker::SetObserver(const nycsim_gameplay::TrafficObserver& Observer)
{
	FScopeLock Lock(&InputLock);
	PendingObserver = Observer;
}

void FNYCTrafficWorker::SetTrafficConfig(const nycsim_gameplay::TrafficConfig& Config)
{
	FScopeLock Lock(&InputLock);
	PendingTrafficConfig = Config;
	bTrafficConfigDirty = true;
}

void FNYCTrafficWorker::SetPedConfig(const nycsim_gameplay::PedConfig& Config)
{
	FScopeLock Lock(&InputLock);
	PendingPedConfig = Config;
	bPedConfigDirty = true;
}

bool FNYCTrafficWorker::ReadSnapshot(FNYCSimSnapshot& Out, uint64& InOutLastStep)
{
	FScopeLock Lock(&SnapshotLock);
	const FNYCSimSnapshot& Front = Buffers[FrontBuffer];
	if (Front.Step == InOutLastStep)
	{
		return false;
	}
	Out.SimTime = Front.SimTime;
	Out.Step = Front.Step;
	Out.Vehicles = Front.Vehicles;
	Out.Peds = Front.Peds;
	Out.Events = Front.Events;
	InOutLastStep = Front.Step;
	return true;
}

float FNYCTrafficWorker::GetInterpolationAlpha() const
{
	FScopeLock Lock(&SnapshotLock);
	const double StepSeconds = FMath::Max(0.001, static_cast<double>(Traffic.config().stepSeconds));
	const double Elapsed = FPlatformTime::Seconds() - LastPublishSeconds;
	return static_cast<float>(FMath::Clamp(Elapsed / StepSeconds, 0.0, 1.0));
}

void FNYCTrafficWorker::StepOnce()
{
	{
		FScopeLock Lock(&InputLock);
		Traffic.setObserver(PendingObserver);
		Peds.setObserver(PendingObserver);
		if (bTrafficConfigDirty)
		{
			Traffic.setConfig(PendingTrafficConfig);
			bTrafficConfigDirty = false;
		}
		if (bPedConfigDirty)
		{
			Peds.setConfig(PendingPedConfig);
			bPedConfigDirty = false;
		}
	}

	const int32 BackBuffer = 1 - FrontBuffer;
	FNYCSimSnapshot& Back = Buffers[BackBuffer];

	// Cross-feed last step's results, then step both simulations.
	Peds.updateVehicles(Back.Vehicles);
	Peds.writeObstacles(Obstacles);
	Traffic.setPedObstacles(Obstacles);

	Traffic.step();
	Peds.step();

	Back.Clear();
	Traffic.writeSnapshot(Back.Vehicles);
	Peds.writeSnapshot(Back.Peds);
	Traffic.drainEvents(Back.Events);
	Back.SimTime = Traffic.simTime();
	Back.Step = Traffic.stepCount();

	PublishedVehicles = static_cast<uint32>(Back.Vehicles.size());
	PublishedPeds = static_cast<uint32>(Back.Peds.size());
	PublishedRedLightEntries = Traffic.stats().redLightEntries;
	PublishedHonks = Traffic.stats().honks;
	AverageTrafficStepMs = Traffic.stats().avgStepMs;
	AveragePedStepMs = Peds.stats().avgStepMs;

	{
		FScopeLock Lock(&SnapshotLock);
		FrontBuffer = BackBuffer;
		LastPublishSeconds = FPlatformTime::Seconds();
	}
}

uint32 FNYCTrafficWorker::Run()
{
	const double StepSeconds = FMath::Max(0.005, static_cast<double>(Traffic.config().stepSeconds));
	double NextStepAt = FPlatformTime::Seconds();

	while (!bStopRequested)
	{
		if (bPausedFlag)
		{
			FPlatformProcess::Sleep(0.02f);
			NextStepAt = FPlatformTime::Seconds();
			continue;
		}

		StepOnce();

		NextStepAt += StepSeconds;
		const double Now = FPlatformTime::Seconds();
		const double Wait = NextStepAt - Now;
		if (Wait > 0.0)
		{
			FPlatformProcess::Sleep(static_cast<float>(Wait));
		}
		else if (Wait < -StepSeconds * 4.0)
		{
			// The worker fell more than four steps behind (a stall, or a machine that cannot keep up). Resync
			// rather than trying to catch up, which would only make the frame time worse.
			UE_LOG(LogNYCSim, Warning, TEXT("Traffic worker fell %.0f ms behind; resynchronising."),
				   -Wait * 1000.0);
			NextStepAt = Now;
		}
	}
	return 0;
}
