#include "Streaming/NYCTileStreamingSubsystem.h"

#include "CoreAdapter/NYCGeo.h"
#include "NYCSimRuntime.h"
#include "World/NYCSimWorldSettings.h"
#include "World/NYCWorldSubsystem.h"

#include "Debug/DebugDrawService.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/Level.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMemory.h"
#include "Misc/PackageName.h"

namespace
{
	constexpr double MegaByte = 1024.0 * 1024.0;

	/** Scheduler steps per second. The core scheduler is hysteretic, so 10 Hz is ample at 30 m/s (3 m per step). */
	TAutoConsoleVariable<float> CVarSchedulerHz(
		TEXT("nycsim.Streaming.Hz"), 10.f,
		TEXT("Tile scheduler steps per second (the step itself runs on a worker thread)."),
		ECVF_Default);

	TAutoConsoleVariable<int32> CVarStreamingDebug(
		TEXT("nycsim.Streaming.Debug"), 0,
		TEXT("0 off, 1 on-screen streaming HUD (tiers, budget, requests), 2 adds the per-tier tile grid."),
		ECVF_Cheat);

	TAutoConsoleVariable<int32> CVarStreamingEnabled(
		TEXT("nycsim.Streaming.Enabled"), 1,
		TEXT("0 freezes the scheduler at the tiers it last produced (levels stay as they are)."),
		ECVF_Default);

	/** Camera speed above which the filtered velocity is clamped; a teleport must not pre-load half the city. */
	constexpr double MaxCameraSpeedMps = 80.0;   // 288 km/h
	constexpr double TeleportDistanceM = 150.0;  // per-frame jump treated as a teleport (velocity reset)

	UNYCTileStreamingSubsystem* SubsystemFor(UWorld* World)
	{
		return World ? World->GetSubsystem<UNYCTileStreamingSubsystem>() : nullptr;
	}

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GStatsCmd(
		TEXT("nycsim.Streaming.Stats"),
		TEXT("Prints tile counts per tier, the memory budget and the level request queue."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCTileStreamingSubsystem* S = SubsystemFor(World))
				{
					S->PrintStats(Ar);
				}
				else
				{
					Ar.Logf(TEXT("nycsim: no tile streaming subsystem in this world"));
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GLevelsCmd(
		TEXT("nycsim.Streaming.Levels"),
		TEXT("Lists every managed streaming level with its wanted/loaded/visible state."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCTileStreamingSubsystem* S = SubsystemFor(World))
				{
					S->PrintLevels(Ar);
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GTileCmd(
		TEXT("nycsim.Streaming.Tile"),
		TEXT("nycsim.Streaming.Tile <t_tx_ty | tx ty>: tier, level package and load state of one tile."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				UNYCTileStreamingSubsystem* S = SubsystemFor(World);
				if (!S)
				{
					return;
				}
				FIntPoint Tile = FIntPoint::ZeroValue;
				if (Args.Num() == 1 && NYCGeo::ParseTileName(Args[0], Tile))
				{
					S->PrintTile(Tile, Ar);
				}
				else if (Args.Num() >= 2)
				{
					S->PrintTile(FIntPoint(FCString::Atoi(*Args[0]), FCString::Atoi(*Args[1])), Ar);
				}
				else
				{
					Ar.Logf(TEXT("usage: nycsim.Streaming.Tile t_-3_7  |  nycsim.Streaming.Tile -3 7"));
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GFlushCmd(
		TEXT("nycsim.Streaming.Flush"),
		TEXT("Blocks until every pending level load/unload has completed."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCTileStreamingSubsystem* S = SubsystemFor(World))
				{
					S->FlushStreaming();
					Ar.Logf(TEXT("nycsim: streaming flushed"));
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GResetCmd(
		TEXT("nycsim.Streaming.Reset"),
		TEXT("Unloads every managed level and re-runs the scheduler from scratch."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCTileStreamingSubsystem* S = SubsystemFor(World))
				{
					S->ResetStreaming();
					Ar.Logf(TEXT("nycsim: streaming reset"));
				}
			}));
}

// ---------------------------------------------------------------------------------------------------- lifecycle

bool UNYCTileStreamingSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (!Super::ShouldCreateSubsystem(Outer))
	{
		return false;
	}
	const UWorld* World = Cast<UWorld>(Outer);
	if (!World)
	{
		return false;
	}
	// Game and PIE only: in the editor world the level browser owns level visibility.
	return World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE;
}

void UNYCTileStreamingSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UNYCWorldSubsystem>();
	Super::Initialize(Collection);

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	SchedulerConfig.L0LoadMetres = Settings.LoadRadiusL0Metres;
	SchedulerConfig.L0UnloadMetres = Settings.UnloadRadiusL0Metres;
	SchedulerConfig.L1LoadMetres = Settings.LoadRadiusL1Metres;
	SchedulerConfig.L1UnloadMetres = Settings.UnloadRadiusL1Metres;
	SchedulerConfig.LookaheadSeconds = Settings.PredictiveLookaheadSeconds;
	SchedulerConfig.BudgetBytes = static_cast<uint64>(FMath::Max(512, Settings.CpuBudgetMegabytes)) * 1024ull * 1024ull;
	EffectiveBudgetBytes = SchedulerConfig.BudgetBytes;

	BuildScheduler();

	const UWorld* World = GetWorld();
	if (!IsRunningCommandlet() && World && World->GetNetMode() != NM_DedicatedServer)
	{
		DebugDrawHandle = UDebugDrawService::Register(
			TEXT("Game"), FDebugDrawDelegate::CreateUObject(this, &UNYCTileStreamingSubsystem::DrawDebugHUD));
	}
}

void UNYCTileStreamingSubsystem::Deinitialize()
{
	if (SchedulerTask.IsValid())
	{
		SchedulerTask.Wait();
	}
	bTaskInFlight = false;
	if (DebugDrawHandle.IsValid())
	{
		UDebugDrawService::Unregister(DebugDrawHandle);
		DebugDrawHandle.Reset();
	}
	ReleaseAllLevels();
	Scheduler.Reset();
	Super::Deinitialize();
}

bool UNYCTileStreamingSubsystem::IsTickable() const
{
	return IsInitialized() && Scheduler.IsValid();
}

TStatId UNYCTileStreamingSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCTileStreamingSubsystem, STATGROUP_Tickables);
}

bool UNYCTileStreamingSubsystem::BuildScheduler()
{
	Scheduler.Reset();
	TierByTile.Reset();
	const UWorld* World = GetWorld();
	const UNYCWorldSubsystem* WorldSub = World ? World->GetSubsystem<UNYCWorldSubsystem>() : nullptr;
	if (!WorldSub || !WorldSub->IsWorldDataReady())
	{
		UE_LOG(LogNYCSim, Error, TEXT("TileStreaming: world data not ready (%s); streaming is disabled."),
			WorldSub ? *WorldSub->GetLoadError() : TEXT("no world subsystem"));
		return false;
	}
	const FNYCTilesTable& Tiles = WorldSub->TilesTable();
	if (Tiles.Num() == 0)
	{
		UE_LOG(LogNYCSim, Error, TEXT("TileStreaming: tiles.nycb holds no tiles; streaming is disabled."));
		return false;
	}
	Scheduler = MakeUnique<FNYCTileSchedulerAdapter>(Tiles, SchedulerConfig);
	if (!Scheduler->IsConfigValid())
	{
		UE_LOG(LogNYCSim, Warning,
			TEXT("TileStreaming: NYCSimWorldSettings streaming radii are inconsistent (load >= unload or tiers not ")
			TEXT("ordered); the core defaults are used instead."));
	}
	TierByTile.Reserve(Tiles.Num());
	for (const FNYCTileRecord& R : Tiles.Records())
	{
		TierByTile.Add(R.Tile(), ENYCTier::Unloaded);
	}
	UE_LOG(LogNYCSim, Log, TEXT("TileStreaming: scheduler over %d tiles, budget %.0f MB, radii L0 %.0f/%.0f m L1 %.0f/%.0f m"),
		Scheduler->TileCount(), SchedulerConfig.BudgetBytes / MegaByte,
		SchedulerConfig.L0LoadMetres, SchedulerConfig.L0UnloadMetres,
		SchedulerConfig.L1LoadMetres, SchedulerConfig.L1UnloadMetres);
	return true;
}

// ------------------------------------------------------------------------------------------------------- tick

void UNYCTileStreamingSubsystem::Tick(float DeltaTime)
{
	if (!Scheduler.IsValid())
	{
		return;
	}
	SimTimeSeconds += DeltaTime;

	// 1. Harvest a finished worker step before anything else touches the adapter.
	CollectSchedulerResults();

	// 2. Launch the next step at the configured cadence.
	TimeSinceLastStep += DeltaTime;
	const double StepPeriod = 1.0 / FMath::Max(0.5f, CVarSchedulerHz.GetValueOnGameThread());
	if (!bTaskInFlight && TimeSinceLastStep >= StepPeriod && CVarStreamingEnabled.GetValueOnGameThread() != 0)
	{
		FNYCCameraState Camera;
		if (SampleCamera(DeltaTime, Camera))
		{
			TimeSinceLastStep = 0.0;
			LaunchSchedulerStep(Camera);
		}
	}

	// 3. Turn the tier map into level requests and issue a bounded number of them.
	if (bTierMapDirty)
	{
		RecomputeDesiredLevels();
		bTierMapDirty = false;
	}
	ApplyPendingRequests();
	UpdateStats();
}

bool UNYCTileStreamingSubsystem::SampleCamera(float DeltaTime, FNYCCameraState& OutCamera)
{
	FVector LocationUE = FVector::ZeroVector;
	double HeadingDeg = 0.0;

	if (bCameraOverride)
	{
		LocationUE = OverrideLocationUE;
		HeadingDeg = OverrideHeadingDeg;
	}
	else
	{
		const UWorld* World = GetWorld();
		const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (!PC)
		{
			return false;
		}
		FRotator Rotation = FRotator::ZeroRotator;
		PC->GetPlayerViewPoint(LocationUE, Rotation);
		HeadingDeg = NYCGeo::UEYawToHeading(Rotation.Yaw);
	}

	const FVector Tm = NYCGeo::UEToNycTm(LocationUE);

	FVector2D VelocityMps = FVector2D::ZeroVector;
	if (bCameraOverride)
	{
		VelocityMps = OverrideVelocityMps;
		FilteredVelocityMps = VelocityMps;
	}
	else if (bHasPreviousCamera && DeltaTime > KINDA_SMALL_NUMBER)
	{
		const FVector PrevTm = NYCGeo::UEToNycTm(PreviousCameraUE);
		const FVector2D DeltaM(Tm.X - PrevTm.X, Tm.Y - PrevTm.Y);
		if (DeltaM.Size() > TeleportDistanceM)
		{
			// Teleport: no predictive pre-load along a velocity that never existed.
			FilteredVelocityMps = FVector2D::ZeroVector;
		}
		else
		{
			const FVector2D Instant = DeltaM / DeltaTime;
			// 0.5 s time constant, frame-rate independent.
			const double Alpha = 1.0 - FMath::Exp(-DeltaTime / 0.5);
			FilteredVelocityMps += (Instant - FilteredVelocityMps) * Alpha;
			const double Speed = FilteredVelocityMps.Size();
			if (Speed > MaxCameraSpeedMps)
			{
				FilteredVelocityMps *= MaxCameraSpeedMps / Speed;
			}
		}
		VelocityMps = FilteredVelocityMps;
	}
	PreviousCameraUE = LocationUE;
	bHasPreviousCamera = true;
	FilteredHeadingDeg = static_cast<float>(HeadingDeg);

	OutCamera.PositionMetres = FVector2D(Tm.X, Tm.Y);
	OutCamera.VelocityMps = VelocityMps;
	OutCamera.HeadingDeg = HeadingDeg;
	OutCamera.TimeSeconds = SimTimeSeconds;

	Stats.CameraNycTm = Tm;
	Stats.CameraVelocityMps = VelocityMps;
	Stats.CameraHeadingDeg = static_cast<float>(HeadingDeg);
	Stats.CameraTile = NYCGeo::TileOfNycTm(Tm.X, Tm.Y);
	return true;
}

void UNYCTileStreamingSubsystem::LaunchSchedulerStep(const FNYCCameraState& Camera)
{
	WorkerTransitions.Reset();
	bTaskInFlight = true;
	FNYCTileSchedulerAdapter* Adapter = Scheduler.Get();
	SchedulerTask = UE::Tasks::Launch(UE_SOURCE_LOCATION, [this, Adapter, Camera]()
	{
		const double Start = FPlatformTime::Seconds();
		Adapter->Update(Camera, WorkerTransitions);
		WorkerStats = Adapter->Stats();
		WorkerStepSeconds = FPlatformTime::Seconds() - Start;
	});
}

void UNYCTileStreamingSubsystem::CollectSchedulerResults()
{
	if (!bTaskInFlight || !SchedulerTask.IsCompleted())
	{
		return;
	}
	bTaskInFlight = false;
	Stats.LastSchedulerStepMs = static_cast<float>(WorkerStepSeconds * 1000.0);
	Stats.TotalLoads = static_cast<int64>(WorkerStats.TotalLoads);
	Stats.TotalUnloads = static_cast<int64>(WorkerStats.TotalUnloads);
	Stats.TotalBudgetDenials = static_cast<int64>(WorkerStats.TotalBudgetDenials);
	Stats.SchedulerUpdates = static_cast<int64>(WorkerStats.Updates);
	Stats.EstimatedResidentMB = WorkerStats.ResidentBytes / MegaByte;
	Stats.bOverBudget = WorkerStats.bOverBudget;
	for (int32 i = 0; i < 5; ++i)
	{
		Stats.TilesPerTier[i] = static_cast<int32>(WorkerStats.CountByTier[i]);
	}
	if (WorkerTransitions.Num() == 0)
	{
		return;
	}
	for (const FNYCTileTransition& T : WorkerTransitions)
	{
		if (ENYCTier* Existing = TierByTile.Find(T.Tile))
		{
			*Existing = T.To;
		}
		else
		{
			TierByTile.Add(T.Tile, T.To);
		}
		TileTierChanged.Broadcast(T.Tile, T.From, T.To);
	}
	bTierMapDirty = true;
	WorkerTransitions.Reset();
}

// -------------------------------------------------------------------------------------- tier -> level mapping

FString UNYCTileStreamingSubsystem::TileLevelPackage(const FIntPoint& Tile, ENYCTier Tier) const
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString Name = NYCGeo::TileAssetName(Tile);
	return FString::Printf(TEXT("%s/%s/%s_%s"), *Settings.TileLevelRoot, *Name, *Name, NYCTierName(Tier));
}

FString UNYCTileStreamingSubsystem::SkylineLevelPackage(const FIntPoint& Cell, int32 KilometresPerCell) const
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString Sx = Cell.X < 0 ? FString::Printf(TEXT("m%d"), -Cell.X) : FString::Printf(TEXT("%d"), Cell.X);
	const FString Sy = Cell.Y < 0 ? FString::Printf(TEXT("m%d"), -Cell.Y) : FString::Printf(TEXT("%d"), Cell.Y);
	return FString::Printf(TEXT("%s/S%d_%s_%s"), *Settings.SkylineLevelRoot, KilometresPerCell, *Sx, *Sy);
}

void UNYCTileStreamingSubsystem::RecomputeDesiredLevels()
{
	if (!Scheduler.IsValid())
	{
		return;
	}
	// Clear the wanted flags; everything still wanted is set again below.
	for (TPair<FName, FManagedLevel>& Pair : Levels)
	{
		Pair.Value.bWanted = false;
	}
	PendingRequests.Reset();

	// Skyline cells: a 4 km cell is wanted only when none of its tiles is finer than L2, a 16 km cell only when none
	// of its tiles is finer than L3. Without this rule the merged HLOD mesh would draw on top of the detailed tiles.
	TMap<FIntPoint, uint8> Cell4Wanted;   // 1 = at least one tile wants L2, 2 = at least one tile is finer than L2
	TMap<FIntPoint, uint8> Cell16Wanted;
	TMap<FIntPoint, double> Cell4Distance;
	TMap<FIntPoint, double> Cell16Distance;

	const FVector2D CameraTm(Stats.CameraNycTm.X, Stats.CameraNycTm.Y);
	auto TileDistanceM = [&CameraTm](const FIntPoint& Tile)
	{
		const FVector2D Origin = NYCGeo::TileOriginMetres(Tile);
		const double Dx = FMath::Max3(Origin.X - CameraTm.X, 0.0, CameraTm.X - (Origin.X + NYCGeo::TileSizeMetres));
		const double Dy = FMath::Max3(Origin.Y - CameraTm.Y, 0.0, CameraTm.Y - (Origin.Y + NYCGeo::TileSizeMetres));
		return FMath::Sqrt(Dx * Dx + Dy * Dy);
	};

	for (const TPair<FIntPoint, ENYCTier>& Pair : TierByTile)
	{
		const FIntPoint Tile = Pair.Key;
		const ENYCTier Tier = Pair.Value;
		const double DistanceM = TileDistanceM(Tile);
		const FIntPoint Cell4 = NYCGeo::ParentTile(Tile, 1);
		const FIntPoint Cell16 = NYCGeo::ParentTile(Tile, 2);

		if (Tier == ENYCTier::L0 || Tier == ENYCTier::L1)
		{
			SetLevelWanted(TileLevelPackage(Tile, Tier), true, Scheduler->EstimateBytes(Tile, Tier), DistanceM);
			Cell4Wanted.FindOrAdd(Cell4) |= 2;
			Cell16Wanted.FindOrAdd(Cell16) |= 2;
		}
		else if (Tier == ENYCTier::L2)
		{
			Cell4Wanted.FindOrAdd(Cell4) |= 1;
			Cell16Wanted.FindOrAdd(Cell16) |= 2;
			if (double* D = Cell4Distance.Find(Cell4))
			{
				*D = FMath::Min(*D, DistanceM);
			}
			else
			{
				Cell4Distance.Add(Cell4, DistanceM);
			}
		}
		else if (Tier == ENYCTier::L3)
		{
			Cell16Wanted.FindOrAdd(Cell16) |= 1;
			if (double* D = Cell16Distance.Find(Cell16))
			{
				*D = FMath::Min(*D, DistanceM);
			}
			else
			{
				Cell16Distance.Add(Cell16, DistanceM);
			}
		}
	}

	for (const TPair<FIntPoint, uint8>& Cell : Cell4Wanted)
	{
		if (Cell.Value == 1) // wanted at L2 and no tile inside is finer
		{
			const double* D = Cell4Distance.Find(Cell.Key);
			SetLevelWanted(SkylineLevelPackage(Cell.Key, 4), true, 0, D ? *D : 0.0);
		}
	}
	for (const TPair<FIntPoint, uint8>& Cell : Cell16Wanted)
	{
		if (Cell.Value == 1)
		{
			const double* D = Cell16Distance.Find(Cell.Key);
			SetLevelWanted(SkylineLevelPackage(Cell.Key, 16), true, 0, D ? *D : 0.0);
		}
	}

	// Anything no longer wanted is queued for unload.
	for (TPair<FName, FManagedLevel>& Pair : Levels)
	{
		FManagedLevel& L = Pair.Value;
		if (!L.bWanted && !L.bMissing && L.Streaming.IsValid() && (L.Streaming->ShouldBeLoaded() || L.Streaming->IsLevelLoaded()))
		{
			FPendingRequest R;
			R.PackageName = L.PackageName;
			R.bLoad = false;
			R.PriorityMetres = 0.0; // unloads first: they free the budget the loads need
			PendingRequests.Add(R);
		}
	}

	// Nearest first for loads; unloads (priority 0) sort to the front.
	PendingRequests.Sort([](const FPendingRequest& A, const FPendingRequest& B)
	{
		if (A.bLoad != B.bLoad)
		{
			return !A.bLoad;
		}
		return A.PriorityMetres < B.PriorityMetres;
	});
}

UNYCTileStreamingSubsystem::FManagedLevel* UNYCTileStreamingSubsystem::FindOrAddLevel(const FString& PackageName, uint64 EstimatedBytes)
{
	const FName Key(*PackageName);
	if (FManagedLevel* Existing = Levels.Find(Key))
	{
		if (EstimatedBytes > 0)
		{
			Existing->EstimatedBytes = EstimatedBytes;
		}
		return Existing;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}
	FManagedLevel New;
	New.PackageName = Key;
	New.EstimatedBytes = EstimatedBytes;
	if (!FPackageName::DoesPackageExist(PackageName))
	{
		New.bMissing = true;
		++MissingLevelCount;
		UE_LOG(LogNYCSim, Warning, TEXT("TileStreaming: level package %s does not exist (content not imported?); it will not be requested again."), *PackageName);
		return &Levels.Add(Key, New);
	}
	ULevelStreamingDynamic* Streaming = NewObject<ULevelStreamingDynamic>(World, ULevelStreamingDynamic::StaticClass(), NAME_None, RF_Transient);
	Streaming->SetWorldAssetByPackageName(Key);
	Streaming->PackageNameToLoad = Key;
	Streaming->LevelTransform = FTransform::Identity;
	Streaming->bShouldBlockOnLoad = false;
	Streaming->bShouldBlockOnUnload = false;
	Streaming->SetShouldBeLoaded(false);
	Streaming->SetShouldBeVisible(false);
	World->AddStreamingLevel(Streaming);
	ManagedStreamingLevels.Add(Streaming);
	New.Streaming = Streaming;
	return &Levels.Add(Key, New);
}

void UNYCTileStreamingSubsystem::SetLevelWanted(const FString& PackageName, bool bWanted, uint64 EstimatedBytes, double PriorityMetres)
{
	FManagedLevel* Level = FindOrAddLevel(PackageName, EstimatedBytes);
	if (!Level || Level->bMissing)
	{
		return;
	}
	Level->bWanted = bWanted;
	if (!Level->Streaming.IsValid())
	{
		return;
	}
	const bool bAlready = Level->Streaming->ShouldBeLoaded();
	if (bWanted && !bAlready)
	{
		FPendingRequest R;
		R.PackageName = Level->PackageName;
		R.bLoad = true;
		R.PriorityMetres = PriorityMetres;
		PendingRequests.Add(R);
	}
}

void UNYCTileStreamingSubsystem::ApplyPendingRequests()
{
	const double Start = FPlatformTime::Seconds();
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	int32 LoadBudget = FMath::Max(1, Settings.MaxLoadRequestsPerFrame);
	int32 UnloadBudget = FMath::Max(1, Settings.MaxUnloadRequestsPerFrame);

	int32 Index = 0;
	while (Index < PendingRequests.Num() && (LoadBudget > 0 || UnloadBudget > 0))
	{
		const FPendingRequest& R = PendingRequests[Index];
		FManagedLevel* Level = Levels.Find(R.PackageName);
		if (!Level || Level->bMissing || !Level->Streaming.IsValid())
		{
			PendingRequests.RemoveAt(Index, 1, false);
			continue;
		}
		if (R.bLoad)
		{
			if (LoadBudget == 0)
			{
				++Index;
				continue;
			}
			// Apply-side memory cap: never start a load that would push the applied estimate past the budget.
			// Loads that do not fit stay queued and are re-evaluated next frame, after the unloads have landed.
			if (AppliedResidentBytes + Level->EstimatedBytes > EffectiveBudgetBytes && AppliedResidentBytes > 0)
			{
				++Index;
				continue;
			}
			Level->Streaming->SetShouldBeLoaded(true);
			Level->Streaming->SetShouldBeVisible(true);
			Level->bRequested = true;
			AppliedResidentBytes += Level->EstimatedBytes;
			--LoadBudget;
		}
		else
		{
			if (UnloadBudget == 0)
			{
				++Index;
				continue;
			}
			Level->Streaming->SetShouldBeVisible(false);
			Level->Streaming->SetShouldBeLoaded(false);
			Level->bRequested = true;
			AppliedResidentBytes = (AppliedResidentBytes > Level->EstimatedBytes) ? AppliedResidentBytes - Level->EstimatedBytes : 0;
			--UnloadBudget;
		}
		PendingRequests.RemoveAt(Index, 1, false);
	}
	Stats.LastApplyMs = static_cast<float>((FPlatformTime::Seconds() - Start) * 1000.0);
}

void UNYCTileStreamingSubsystem::ReleaseAllLevels()
{
	UWorld* World = GetWorld();
	for (TPair<FName, FManagedLevel>& Pair : Levels)
	{
		if (Pair.Value.Streaming.IsValid())
		{
			ULevelStreamingDynamic* Streaming = Pair.Value.Streaming.Get();
			Streaming->SetShouldBeVisible(false);
			Streaming->SetShouldBeLoaded(false);
			if (World)
			{
				World->RemoveStreamingLevel(Streaming);
			}
		}
	}
	Levels.Reset();
	ManagedStreamingLevels.Reset();
	PendingRequests.Reset();
	AppliedResidentBytes = 0;
	MissingLevelCount = 0;
}

// ------------------------------------------------------------------------------------------------------- stats

void UNYCTileStreamingSubsystem::UpdateStats()
{
	int32 Loaded = 0;
	int32 Visible = 0;
	int32 Pending = 0;
	for (const TPair<FName, FManagedLevel>& Pair : Levels)
	{
		const FManagedLevel& L = Pair.Value;
		if (!L.Streaming.IsValid())
		{
			continue;
		}
		if (L.Streaming->IsLevelLoaded())
		{
			++Loaded;
		}
		if (L.Streaming->IsLevelVisible())
		{
			++Visible;
		}
		if (L.Streaming->HasLoadRequestPending())
		{
			++Pending;
		}
	}
	Stats.LevelsLoaded = Loaded;
	Stats.LevelsVisible = Visible;
	Stats.LevelsPending = Pending;
	Stats.QueuedRequests = PendingRequests.Num();
	Stats.AppliedResidentMB = AppliedResidentBytes / MegaByte;
	Stats.BudgetMB = EffectiveBudgetBytes / MegaByte;
	Stats.MissingLevels = MissingLevelCount;
	const FPlatformMemoryStats Mem = FPlatformMemory::GetStats();
	Stats.ProcessPhysicalMB = Mem.UsedPhysical / MegaByte;
}

// ---------------------------------------------------------------------------------------------------- queries

ENYCTier UNYCTileStreamingSubsystem::GetTileTier(const FIntPoint& Tile) const
{
	const ENYCTier* Tier = TierByTile.Find(Tile);
	return Tier ? *Tier : ENYCTier::Unloaded;
}

bool UNYCTileStreamingSubsystem::IsTileResident(const FIntPoint& Tile) const
{
	const ENYCTier Tier = GetTileTier(Tile);
	if (Tier != ENYCTier::L0 && Tier != ENYCTier::L1)
	{
		return false;
	}
	const FManagedLevel* Level = Levels.Find(FName(*TileLevelPackage(Tile, Tier)));
	return Level && Level->Streaming.IsValid() && Level->Streaming->IsLevelVisible();
}

TArray<FIntPoint> UNYCTileStreamingSubsystem::GetResidentTiles() const
{
	TArray<FIntPoint> Out;
	Out.Reserve(64);
	for (const TPair<FIntPoint, ENYCTier>& Pair : TierByTile)
	{
		if (Pair.Value == ENYCTier::L0 || Pair.Value == ENYCTier::L1)
		{
			Out.Add(Pair.Key);
		}
	}
	Out.Sort([](const FIntPoint& A, const FIntPoint& B) { return A.Y != B.Y ? A.Y < B.Y : A.X < B.X; });
	return Out;
}

void UNYCTileStreamingSubsystem::SetCameraOverride(const FVector& UELocation, float HeadingDeg, const FVector2D& VelocityMps)
{
	bCameraOverride = true;
	OverrideLocationUE = UELocation;
	OverrideHeadingDeg = HeadingDeg;
	OverrideVelocityMps = VelocityMps;
	TimeSinceLastStep = TNumericLimits<double>::Max(); // step on the next tick
}

void UNYCTileStreamingSubsystem::ClearCameraOverride()
{
	bCameraOverride = false;
	bHasPreviousCamera = false;
	FilteredVelocityMps = FVector2D::ZeroVector;
}

void UNYCTileStreamingSubsystem::FlushStreaming()
{
	if (SchedulerTask.IsValid())
	{
		SchedulerTask.Wait();
	}
	bTaskInFlight = false;
	CollectSchedulerResults();
	if (bTierMapDirty)
	{
		RecomputeDesiredLevels();
		bTierMapDirty = false;
	}
	// Issue everything at once, ignoring the per-frame throttle: the caller has explicitly asked to block.
	for (const FPendingRequest& R : PendingRequests)
	{
		FManagedLevel* Level = Levels.Find(R.PackageName);
		if (!Level || Level->bMissing || !Level->Streaming.IsValid())
		{
			continue;
		}
		Level->Streaming->SetShouldBeLoaded(R.bLoad);
		Level->Streaming->SetShouldBeVisible(R.bLoad);
		Level->bRequested = true;
	}
	PendingRequests.Reset();
	if (UWorld* World = GetWorld())
	{
		World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
	}
	AppliedResidentBytes = 0;
	for (const TPair<FName, FManagedLevel>& Pair : Levels)
	{
		if (Pair.Value.bWanted)
		{
			AppliedResidentBytes += Pair.Value.EstimatedBytes;
		}
	}
	UpdateStats();
}

void UNYCTileStreamingSubsystem::ResetStreaming()
{
	if (SchedulerTask.IsValid())
	{
		SchedulerTask.Wait();
	}
	bTaskInFlight = false;
	ReleaseAllLevels();
	if (Scheduler.IsValid())
	{
		Scheduler->Reset();
	}
	for (TPair<FIntPoint, ENYCTier>& Pair : TierByTile)
	{
		Pair.Value = ENYCTier::Unloaded;
	}
	bHasPreviousCamera = false;
	FilteredVelocityMps = FVector2D::ZeroVector;
	TimeSinceLastStep = TNumericLimits<double>::Max();
	bTierMapDirty = false;
}

// ---------------------------------------------------------------------------------------------------- console

void UNYCTileStreamingSubsystem::PrintStats(FOutputDevice& Ar) const
{
	Ar.Logf(TEXT("NYCSim tile streaming: %s, %d tiles in the catalogue"),
		Scheduler.IsValid() ? TEXT("ready") : TEXT("NOT READY"), Scheduler.IsValid() ? Scheduler->TileCount() : 0);
	Ar.Logf(TEXT("  camera NYC_TM (%.1f, %.1f, %.1f) m  tile %s  heading %.1f deg  speed %.1f m/s"),
		Stats.CameraNycTm.X, Stats.CameraNycTm.Y, Stats.CameraNycTm.Z,
		*NYCGeo::TileName(Stats.CameraTile), Stats.CameraHeadingDeg, Stats.CameraVelocityMps.Size());
	Ar.Logf(TEXT("  tiers  L0 %d  L1 %d  L2 %d  L3 %d  unloaded %d"),
		Stats.TilesPerTier[static_cast<int32>(ENYCTier::L0)], Stats.TilesPerTier[static_cast<int32>(ENYCTier::L1)],
		Stats.TilesPerTier[static_cast<int32>(ENYCTier::L2)], Stats.TilesPerTier[static_cast<int32>(ENYCTier::L3)],
		Stats.TilesPerTier[static_cast<int32>(ENYCTier::Unloaded)]);
	Ar.Logf(TEXT("  levels loaded %d  visible %d  pending %d  queued %d  missing packages %d"),
		Stats.LevelsLoaded, Stats.LevelsVisible, Stats.LevelsPending, Stats.QueuedRequests, Stats.MissingLevels);
	Ar.Logf(TEXT("  memory  scheduler estimate %.0f MB  applied %.0f MB  budget %.0f MB  process %.0f MB%s"),
		Stats.EstimatedResidentMB, Stats.AppliedResidentMB, Stats.BudgetMB, Stats.ProcessPhysicalMB,
		Stats.bOverBudget ? TEXT("  [OVER BUDGET: protected tiles alone exceed it]") : TEXT(""));
	Ar.Logf(TEXT("  totals  loads %lld  unloads %lld  budget denials %lld  scheduler updates %lld"),
		Stats.TotalLoads, Stats.TotalUnloads, Stats.TotalBudgetDenials, Stats.SchedulerUpdates);
	Ar.Logf(TEXT("  timing  scheduler step %.2f ms (worker thread)  apply %.2f ms (game thread)"),
		Stats.LastSchedulerStepMs, Stats.LastApplyMs);
}

void UNYCTileStreamingSubsystem::PrintTile(const FIntPoint& Tile, FOutputDevice& Ar) const
{
	const ENYCTier Tier = GetTileTier(Tile);
	Ar.Logf(TEXT("tile %s: tier %s"), *NYCGeo::TileName(Tile), NYCTierName(Tier));
	if (Scheduler.IsValid() && !Scheduler->Contains(Tile))
	{
		Ar.Logf(TEXT("  not present in tiles.nycb"));
		return;
	}
	for (int32 i = static_cast<int32>(ENYCTier::L3); i <= static_cast<int32>(ENYCTier::L0); ++i)
	{
		const ENYCTier T = static_cast<ENYCTier>(i);
		Ar.Logf(TEXT("  %s cost estimate %.2f MB"), NYCTierName(T),
			Scheduler.IsValid() ? Scheduler->EstimateBytes(Tile, T) / MegaByte : 0.0);
	}
	if (Tier == ENYCTier::L0 || Tier == ENYCTier::L1)
	{
		const FString Package = TileLevelPackage(Tile, Tier);
		const FManagedLevel* Level = Levels.Find(FName(*Package));
		Ar.Logf(TEXT("  level %s: %s"), *Package,
			!Level ? TEXT("not managed")
			: Level->bMissing ? TEXT("PACKAGE MISSING")
			: !Level->Streaming.IsValid() ? TEXT("streaming object gone")
			: Level->Streaming->IsLevelVisible() ? TEXT("visible")
			: Level->Streaming->IsLevelLoaded() ? TEXT("loaded, not visible")
			: Level->Streaming->HasLoadRequestPending() ? TEXT("loading") : TEXT("requested"));
	}
	else if (Tier == ENYCTier::L2)
	{
		Ar.Logf(TEXT("  skyline level %s"), *SkylineLevelPackage(NYCGeo::ParentTile(Tile, 1), 4));
	}
	else if (Tier == ENYCTier::L3)
	{
		Ar.Logf(TEXT("  skyline level %s"), *SkylineLevelPackage(NYCGeo::ParentTile(Tile, 2), 16));
	}
}

void UNYCTileStreamingSubsystem::PrintLevels(FOutputDevice& Ar) const
{
	Ar.Logf(TEXT("NYCSim managed streaming levels: %d"), Levels.Num());
	TArray<FName> Names;
	Levels.GetKeys(Names);
	Names.Sort([](const FName& A, const FName& B) { return A.LexicalLess(B); });
	for (const FName& Name : Names)
	{
		const FManagedLevel& L = Levels.FindChecked(Name);
		Ar.Logf(TEXT("  %-60s wanted=%d missing=%d loaded=%d visible=%d pending=%d est=%.1f MB"),
			*Name.ToString(), L.bWanted ? 1 : 0, L.bMissing ? 1 : 0,
			L.Streaming.IsValid() && L.Streaming->IsLevelLoaded() ? 1 : 0,
			L.Streaming.IsValid() && L.Streaming->IsLevelVisible() ? 1 : 0,
			L.Streaming.IsValid() && L.Streaming->HasLoadRequestPending() ? 1 : 0,
			L.EstimatedBytes / MegaByte);
	}
}

void UNYCTileStreamingSubsystem::DrawDebugHUD(UCanvas* Canvas, APlayerController* PC)
{
	const int32 Mode = CVarStreamingDebug.GetValueOnGameThread();
	if (Mode <= 0 || !Canvas || !Scheduler.IsValid())
	{
		return;
	}
	UFont* Font = GEngine ? GEngine->GetSmallFont() : nullptr;
	if (!Font)
	{
		return;
	}
	const float X = 24.f;
	float Y = 90.f;
	const float LineHeight = 15.f;
	auto Line = [&](const FLinearColor& Colour, const FString& Text)
	{
		Canvas->SetDrawColor(Colour.ToFColor(true));
		Canvas->DrawText(Font, Text, X, Y);
		Y += LineHeight;
	};

	const FLinearColor White(1.f, 1.f, 1.f, 1.f);
	const FLinearColor Amber(1.f, 0.75f, 0.2f, 1.f);
	const FLinearColor Red(1.f, 0.3f, 0.25f, 1.f);

	Line(White, FString::Printf(TEXT("NYCSim streaming   tile %s   NYC_TM %.0f, %.0f m   %.1f m/s   hdg %.0f"),
		*NYCGeo::TileName(Stats.CameraTile), Stats.CameraNycTm.X, Stats.CameraNycTm.Y,
		Stats.CameraVelocityMps.Size(), Stats.CameraHeadingDeg));
	Line(White, FString::Printf(TEXT("tiers  L0 %d   L1 %d   L2 %d   L3 %d   (catalogue %d)"),
		Stats.TilesPerTier[static_cast<int32>(ENYCTier::L0)], Stats.TilesPerTier[static_cast<int32>(ENYCTier::L1)],
		Stats.TilesPerTier[static_cast<int32>(ENYCTier::L2)], Stats.TilesPerTier[static_cast<int32>(ENYCTier::L3)],
		Scheduler->TileCount()));
	Line(Stats.LevelsPending > 0 ? Amber : White,
		FString::Printf(TEXT("levels loaded %d   visible %d   loading %d   queued %d   missing %d"),
			Stats.LevelsLoaded, Stats.LevelsVisible, Stats.LevelsPending, Stats.QueuedRequests, Stats.MissingLevels));
	Line(Stats.bOverBudget ? Red : (Stats.AppliedResidentMB > Stats.BudgetMB * 0.9 ? Amber : White),
		FString::Printf(TEXT("memory  est %.0f MB   applied %.0f MB / %.0f MB   process %.0f MB"),
			Stats.EstimatedResidentMB, Stats.AppliedResidentMB, Stats.BudgetMB, Stats.ProcessPhysicalMB));
	Line(Stats.LastSchedulerStepMs > 4.f ? Amber : White,
		FString::Printf(TEXT("step %.2f ms (worker)   apply %.2f ms   updates %lld   denials %lld"),
			Stats.LastSchedulerStepMs, Stats.LastApplyMs, Stats.SchedulerUpdates, Stats.TotalBudgetDenials));

	if (Mode < 2)
	{
		return;
	}
	// Mode 2: a 21 x 21 tile map around the camera, one cell per tile, coloured by tier.
	const int32 Radius = 10;
	const float Cell = 9.f;
	const float GridX = X;
	const float GridY = Y + 6.f;
	for (int32 Dy = -Radius; Dy <= Radius; ++Dy)
	{
		for (int32 Dx = -Radius; Dx <= Radius; ++Dx)
		{
			const FIntPoint Tile(Stats.CameraTile.X + Dx, Stats.CameraTile.Y + Dy);
			const ENYCTier Tier = GetTileTier(Tile);
			FLinearColor Colour(0.12f, 0.12f, 0.12f, 0.6f);
			switch (Tier)
			{
			case ENYCTier::L0: Colour = FLinearColor(0.15f, 0.95f, 0.25f, 0.9f); break;
			case ENYCTier::L1: Colour = FLinearColor(0.95f, 0.85f, 0.15f, 0.9f); break;
			case ENYCTier::L2: Colour = FLinearColor(0.95f, 0.5f, 0.1f, 0.85f); break;
			case ENYCTier::L3: Colour = FLinearColor(0.5f, 0.3f, 0.7f, 0.8f); break;
			default: break;
			}
			if (!Scheduler->Contains(Tile))
			{
				Colour = FLinearColor(0.05f, 0.05f, 0.05f, 0.35f);
			}
			// North (+ty) is drawn upwards, so the row offset is negated.
			const float CellX = GridX + (Dx + Radius) * Cell;
			const float CellY = GridY + (Radius - Dy) * Cell;
			Canvas->SetDrawColor(Colour.ToFColor(true));
			Canvas->DrawTile(Canvas->DefaultTexture, CellX, CellY, Cell - 1.f, Cell - 1.f, 0.f, 0.f, 1.f, 1.f);
		}
	}
	Canvas->SetDrawColor(FColor::White);
	Canvas->DrawText(Font, TEXT("L0 green   L1 yellow   L2 orange   L3 violet   (camera at centre, north up)"),
		GridX, GridY + (2 * Radius + 1) * Cell + 4.f);
}
