#include "Traffic/NYCTrafficSubsystem.h"

#include "Animation/AnimSequence.h"
#include "Audio/NYCAudioSubsystem.h"
#include "CoreAdapter/GameplayPedSim.h"
#include "CoreAdapter/GameplayRoadNetwork.h"
#include "CoreAdapter/GameplayTrafficSim.h"
#include "CoreAdapter/NYCGeo.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NYCSimRuntime.h"
#include "Peds/NYCPedestrian.h"
#include "Player/NYCGameplaySettings.h"
#include "Sound/SoundBase.h"
#include "Traffic/NYCRoadNetworkSubsystem.h"
#include "Traffic/NYCTrafficVehicle.h"
#include "Traffic/NYCTrafficWorker.h"
#include "Vehicle/NYCPlayerVehicle.h"

namespace
{
constexpr float kCmPerMetre = 100.f;

/** NYC fleet colours. Taxis, liveries and emergency vehicles are fixed; private cars follow the real
 *  registration mix (white, black, grey and silver are about two-thirds of the US fleet). */
FLinearColor PrivateCarColour(uint32 Hash)
{
	static const FLinearColor Palette[] = {
		FLinearColor(0.78f, 0.78f, 0.79f),   // silver
		FLinearColor(0.86f, 0.87f, 0.88f),   // white
		FLinearColor(0.04f, 0.04f, 0.045f),  // black
		FLinearColor(0.22f, 0.23f, 0.24f),   // graphite
		FLinearColor(0.35f, 0.36f, 0.38f),   // grey
		FLinearColor(0.45f, 0.06f, 0.07f),   // dark red
		FLinearColor(0.05f, 0.11f, 0.30f),   // navy
		FLinearColor(0.08f, 0.24f, 0.16f),   // dark green
		FLinearColor(0.14f, 0.30f, 0.55f),   // blue
		FLinearColor(0.55f, 0.42f, 0.20f),   // beige
	};
	// Weighted so the first five (neutral) colours dominate, matching the real distribution.
	static const uint32 Weights[] = {18, 22, 20, 9, 9, 5, 6, 3, 5, 3};
	uint32 Total = 0;
	for (uint32 W : Weights)
	{
		Total += W;
	}
	uint32 Pick = Hash % Total;
	for (int32 i = 0; i < UE_ARRAY_COUNT(Weights); ++i)
	{
		if (Pick < Weights[i])
		{
			return Palette[i];
		}
		Pick -= Weights[i];
	}
	return Palette[0];
}

uint32 HashAgent(int32 AgentId)
{
	uint32 H = static_cast<uint32>(AgentId) * 2654435761u;
	H ^= H >> 15;
	H *= 2246822519u;
	H ^= H >> 13;
	return H;
}
}  // namespace

UNYCTrafficSubsystem::UNYCTrafficSubsystem() = default;

bool UNYCTrafficSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World != nullptr && World->IsGameWorld();
}

void UNYCTrafficSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UNYCRoadNetworkSubsystem>();
	Super::Initialize(Collection);

	Snapshot = MakeUnique<FNYCSimSnapshot>();
	Worker = MakeUnique<FNYCTrafficWorker>();

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.traffic.stats"), TEXT("Print traffic and pedestrian counters."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				Ar.Logf(TEXT("traffic: %d vehicles (%d actors pooled), %d pedestrians (%d actors pooled)"),
						Stats.Vehicles, Stats.VehicleActorsPooled, Stats.Pedestrians, Stats.PedestrianActorsPooled);
				Ar.Logf(TEXT("worker: %.3f ms/step traffic, %.3f ms/step peds; %d honks, %d red-light entries"),
						Stats.TrafficStepMs, Stats.PedStepMs, Stats.Honks, Stats.RedLightEntries);
				Ar.Logf(TEXT("fleet meshes missing: %d"), Stats.MissingFleetMeshes);
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.traffic.density"), TEXT("nycsim.traffic.density <vehicles> [pedestrians] - density scale."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>& Args, UWorld*, FOutputDevice& Ar) {
				const float Vehicles = Args.Num() > 0 ? FCString::Atof(*Args[0]) : 1.f;
				const float Peds = Args.Num() > 1 ? FCString::Atof(*Args[1]) : Vehicles;
				SetDensityScale(Vehicles, Peds);
				Ar.Logf(TEXT("density scale: vehicles %.2f, pedestrians %.2f"), Vehicles, Peds);
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.traffic.pause"), TEXT("Toggle the traffic simulation."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				SetPaused(!bPaused);
				Ar.Logf(TEXT("traffic %s"), bPaused ? TEXT("paused") : TEXT("running"));
			})));
}

void UNYCTrafficSubsystem::Deinitialize()
{
	if (Worker.IsValid())
	{
		Worker->Shutdown();
		Worker.Reset();
	}
	for (FAutoConsoleCommandWithWorldArgsAndOutputDevice* Command : ConsoleCommands)
	{
		delete Command;
	}
	ConsoleCommands.Reset();

	for (ANYCTrafficVehicle* Actor : VehiclePool)
	{
		if (IsValid(Actor))
		{
			Actor->Destroy();
		}
	}
	for (ANYCPedestrian* Actor : PedestrianPool)
	{
		if (IsValid(Actor))
		{
			Actor->Destroy();
		}
	}
	VehiclePool.Reset();
	PedestrianPool.Reset();
	Snapshot.Reset();
	bStarted = false;
	Super::Deinitialize();
}

TStatId UNYCTrafficSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCTrafficSubsystem, STATGROUP_Tickables);
}

void UNYCTrafficSubsystem::SetPlayerVehicle(ANYCPlayerVehicle* Vehicle)
{
	PlayerVehicle = Vehicle;
}

void UNYCTrafficSubsystem::SetObserverTransform(const FVector& Location, const FVector& Forward, float SpeedMps)
{
	ObserverLocation = Location;
	ObserverForward = Forward.GetSafeNormal2D();
	ObserverSpeedMps = SpeedMps;
}

void UNYCTrafficSubsystem::SetPaused(bool bInPaused)
{
	bPaused = bInPaused;
	if (Worker.IsValid())
	{
		Worker->SetPaused(bPaused);
	}
}

void UNYCTrafficSubsystem::SetTimeOfDay(int32 Hour, int32 DayClass)
{
	if (!Worker.IsValid() || !bStarted)
	{
		return;
	}
	nycsim_gameplay::TrafficConfig TrafficConfig = Worker->MutableTrafficSim().config();
	TrafficConfig.hour = static_cast<uint8_t>(FMath::Clamp(Hour, 0, 23));
	TrafficConfig.dow = static_cast<uint8_t>(FMath::Clamp(DayClass, 0, 2));
	Worker->SetTrafficConfig(TrafficConfig);

	nycsim_gameplay::PedConfig PedConfig;
	PedConfig.hour = TrafficConfig.hour;
	PedConfig.dow = TrafficConfig.dow;
	PedConfig.maxPeds = static_cast<uint32_t>(UNYCGameplaySettings::Get().MaxPedestrians);
	PedConfig.densityScale = UNYCGameplaySettings::Get().PedestrianDensityScale;
	Worker->SetPedConfig(PedConfig);
}

void UNYCTrafficSubsystem::SetWeather(float Wetness, float SnowCover, float RainRateMmH, float TemperatureC,
									  bool bHeadlights)
{
	if (!Worker.IsValid() || !bStarted)
	{
		return;
	}
	nycsim_gameplay::TrafficConfig TrafficConfig = Worker->MutableTrafficSim().config();
	TrafficConfig.wetness = FMath::Clamp(Wetness, 0.f, 1.f);
	TrafficConfig.snowCover = FMath::Clamp(SnowCover, 0.f, 1.f);
	TrafficConfig.headlightsOn = bHeadlights;
	Worker->SetTrafficConfig(TrafficConfig);

	nycsim_gameplay::PedConfig PedConfig;
	PedConfig.hour = TrafficConfig.hour;
	PedConfig.dow = TrafficConfig.dow;
	PedConfig.rainRateMmH = FMath::Max(0.f, RainRateMmH);
	PedConfig.snowCover = TrafficConfig.snowCover;
	PedConfig.temperatureC = TemperatureC;
	PedConfig.maxPeds = static_cast<uint32_t>(UNYCGameplaySettings::Get().MaxPedestrians);
	PedConfig.densityScale = UNYCGameplaySettings::Get().PedestrianDensityScale;
	Worker->SetPedConfig(PedConfig);
}

void UNYCTrafficSubsystem::SetDensityScale(float VehicleScale, float PedestrianScale)
{
	if (!Worker.IsValid() || !bStarted)
	{
		return;
	}
	nycsim_gameplay::TrafficConfig TrafficConfig = Worker->MutableTrafficSim().config();
	TrafficConfig.vehicleDensityScale = FMath::Clamp(VehicleScale, 0.f, 8.f);
	Worker->SetTrafficConfig(TrafficConfig);

	nycsim_gameplay::PedConfig PedConfig;
	PedConfig.hour = TrafficConfig.hour;
	PedConfig.dow = TrafficConfig.dow;
	PedConfig.densityScale = FMath::Clamp(PedestrianScale, 0.f, 8.f);
	PedConfig.maxPeds = static_cast<uint32_t>(UNYCGameplaySettings::Get().MaxPedestrians);
	Worker->SetPedConfig(PedConfig);
}

void UNYCTrafficSubsystem::LoadFleetAssets()
{
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	FString Root = Settings.TrafficVehicleMeshRoot;
	Root.RemoveFromEnd(TEXT("/"));

	int32 Missing = 0;
	const uint8 ClassCount = nycsim_gameplay::vehicleClassCount();
	for (uint8 i = 0; i < ClassCount; ++i)
	{
		const nycsim_gameplay::VehicleClassInfo Info = nycsim_gameplay::vehicleClassInfo(i);
		const FString Name = FString::Printf(TEXT("SK_%s"), UTF8_TO_TCHAR(Info.name));
		const FString Path = FString::Printf(TEXT("%s/%s.%s"), *Root, *Name, *Name);
		if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(FSoftObjectPath(Path).TryLoad()))
		{
			FleetMeshes.Add(i, Mesh);
		}
		else
		{
			++Missing;
			UE_LOG(LogNYCSim, Warning, TEXT("Traffic: fleet mesh '%s' (class '%s', body '%s') not found."), *Path,
				   UTF8_TO_TCHAR(Info.name), UTF8_TO_TCHAR(Info.body));
		}
	}
	Stats.MissingFleetMeshes = Missing;

	SirenSound = Cast<USoundBase>(
		FSoftObjectPath(FString::Printf(TEXT("%s/S_Siren.S_Siren"), *Settings.SfxContentRoot)).TryLoad());
	if (SirenSound == nullptr)
	{
		UE_LOG(LogNYCSim, Log,
			   TEXT("Traffic: no siren sound at %s/S_Siren; emergency vehicles run silent until the audio import "
					"stage has run."),
			   *Settings.SfxContentRoot);
	}
}

void UNYCTrafficSubsystem::LoadCrowdAssets()
{
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	FString Root = Settings.PedestrianMeshRoot;
	Root.RemoveFromEnd(TEXT("/"));

	int32 Found = 0;
	for (uint8 i = 0; i < nycsim_gameplay::PedSim::kArchetypeCount; ++i)
	{
		const FString Name = FString::Printf(TEXT("SK_Ped_%02d"), i);
		const FString Path = FString::Printf(TEXT("%s/%s.%s"), *Root, *Name, *Name);
		if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(FSoftObjectPath(Path).TryLoad()))
		{
			CrowdMeshes.Add(i, Mesh);
			++Found;
		}
	}
	if (Found == 0)
	{
		UE_LOG(LogNYCSim, Warning,
			   TEXT("Traffic: no crowd meshes under %s (expected SK_Ped_00 .. SK_Ped_%02d); pedestrians simulate "
					"but are not drawn."),
			   *Root, nycsim_gameplay::PedSim::kArchetypeCount - 1);
	}
	else
	{
		UE_LOG(LogNYCSim, Log, TEXT("Traffic: %d of %d crowd archetypes loaded."), Found,
			   static_cast<int32>(nycsim_gameplay::PedSim::kArchetypeCount));
	}

	CrowdWalkClip = Cast<UAnimSequence>(
		FSoftObjectPath(FString::Printf(TEXT("%s/Anims/AS_Walk_Fwd.AS_Walk_Fwd"), *Root)).TryLoad());
	CrowdIdleClip =
		Cast<UAnimSequence>(FSoftObjectPath(FString::Printf(TEXT("%s/Anims/AS_Idle.AS_Idle"), *Root)).TryLoad());
}

USkeletalMesh* UNYCTrafficSubsystem::FleetMeshFor(uint8 VehicleClass)
{
	if (const TObjectPtr<USkeletalMesh>* Found = FleetMeshes.Find(VehicleClass))
	{
		return Found->Get();
	}
	// Fall back to the sedan so a missing body still puts a car on the road rather than a hole in the traffic.
	if (const TObjectPtr<USkeletalMesh>* Sedan = FleetMeshes.Find(0))
	{
		return Sedan->Get();
	}
	return nullptr;
}

USkeletalMesh* UNYCTrafficSubsystem::CrowdMeshFor(uint8 Archetype)
{
	if (const TObjectPtr<USkeletalMesh>* Found = CrowdMeshes.Find(Archetype))
	{
		return Found->Get();
	}
	for (const TPair<uint8, TObjectPtr<USkeletalMesh>>& Pair : CrowdMeshes)
	{
		return Pair.Value.Get();
	}
	return nullptr;
}

FLinearColor UNYCTrafficSubsystem::PaintFor(uint8 VehicleClass, int32 AgentId) const
{
	const nycsim_gameplay::VehicleClassInfo Info = nycsim_gameplay::vehicleClassInfo(VehicleClass);
	const FString Name = UTF8_TO_TCHAR(Info.name);
	if (Name == TEXT("taxi"))
	{
		return FLinearColor(0.95f, 0.62f, 0.02f);  // TLC "taxi yellow" (Dupont M6284)
	}
	if (Name == TEXT("boro_taxi"))
	{
		return FLinearColor(0.10f, 0.53f, 0.30f);  // apple green Street Hail Livery
	}
	if (Name == TEXT("nypd"))
	{
		return FLinearColor(0.86f, 0.87f, 0.88f);  // white with the blue stripe as a livery decal
	}
	if (Name == TEXT("fdny_engine") || Name == TEXT("fdny_ladder"))
	{
		return FLinearColor(0.52f, 0.03f, 0.03f);
	}
	if (Name == TEXT("ambulance"))
	{
		return FLinearColor(0.88f, 0.88f, 0.90f);
	}
	if (Name == TEXT("mta_bus"))
	{
		return FLinearColor(0.72f, 0.73f, 0.75f);  // MTA silver/blue
	}
	if (Name == TEXT("dsny_truck"))
	{
		return FLinearColor(0.85f, 0.86f, 0.88f);  // DSNY white
	}
	if (Name == TEXT("black_car"))
	{
		return FLinearColor(0.03f, 0.03f, 0.035f);
	}
	return PrivateCarColour(HashAgent(AgentId));
}

ANYCTrafficVehicle* UNYCTrafficSubsystem::AcquireVehicleActor()
{
	if (FreeVehicleActors.Num() > 0)
	{
		return VehiclePool[FreeVehicleActors.Pop(EAllowShrinking::No)];
	}
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (VehiclePool.Num() >= Settings.MaxTrafficVehicles)
	{
		return nullptr;
	}
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.ObjectFlags |= RF_Transient;
	ANYCTrafficVehicle* Actor = World->SpawnActor<ANYCTrafficVehicle>(
		ANYCTrafficVehicle::StaticClass(), FVector(0.f, 0.f, -100000.f), FRotator::ZeroRotator, Params);
	if (Actor == nullptr)
	{
		return nullptr;
	}
	Actor->SetSirenSound(SirenSound);
	VehiclePool.Add(Actor);
	return Actor;
}

ANYCPedestrian* UNYCTrafficSubsystem::AcquirePedestrianActor()
{
	if (FreePedestrianActors.Num() > 0)
	{
		return PedestrianPool[FreePedestrianActors.Pop(EAllowShrinking::No)];
	}
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (PedestrianPool.Num() >= Settings.MaxPedestrians)
	{
		return nullptr;
	}
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.ObjectFlags |= RF_Transient;
	ANYCPedestrian* Actor = World->SpawnActor<ANYCPedestrian>(
		ANYCPedestrian::StaticClass(), FVector(0.f, 0.f, -100000.f), FRotator::ZeroRotator, Params);
	if (Actor == nullptr)
	{
		return nullptr;
	}
	Actor->SetClips(CrowdWalkClip, CrowdIdleClip);
	PedestrianPool.Add(Actor);
	return Actor;
}

int32 UNYCTrafficSubsystem::LodForDistance(float DistanceMetres, float FirstCutMetres) const
{
	if (DistanceMetres < FirstCutMetres)
	{
		return 0;
	}
	if (DistanceMetres < FirstCutMetres * 2.f)
	{
		return 1;
	}
	if (DistanceMetres < FirstCutMetres * 4.f)
	{
		return 2;
	}
	return 3;
}

void UNYCTrafficSubsystem::TryStartWorker()
{
	if (bStarted || !Worker.IsValid())
	{
		return;
	}
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	UNYCRoadNetworkSubsystem* Roads = World->GetSubsystem<UNYCRoadNetworkSubsystem>();
	if (Roads == nullptr || !Roads->IsReady())
	{
		return;
	}
	const nycsim_gameplay::RoadNetwork* Network = Roads->GetNetwork();
	if (Network == nullptr)
	{
		return;
	}

	LoadFleetAssets();
	LoadCrowdAssets();

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	nycsim_gameplay::TrafficConfig TrafficConfig;
	TrafficConfig.maxVehicles = static_cast<uint32_t>(FMath::Max(0, Settings.MaxTrafficVehicles));
	TrafficConfig.vehicleDensityScale = Settings.TrafficDensityScale;

	nycsim_gameplay::PedConfig PedConfig;
	PedConfig.maxPeds = static_cast<uint32_t>(FMath::Max(0, Settings.MaxPedestrians));
	PedConfig.densityScale = Settings.PedestrianDensityScale;

	FString Error;
	if (!Worker->Start(*Network, TrafficConfig, PedConfig, Error))
	{
		UE_LOG(LogNYCSim, Error, TEXT("Traffic worker failed to start: %s"), *Error);
		Worker.Reset();
		return;
	}
	bStarted = true;
	UE_LOG(LogNYCSim, Log, TEXT("Traffic worker started: up to %d vehicles and %d pedestrians at 20 Hz."),
		   Settings.MaxTrafficVehicles, Settings.MaxPedestrians);
}

void UNYCTrafficSubsystem::PublishObserver()
{
	nycsim_gameplay::TrafficObserver Observer;

	const ANYCPlayerVehicle* Vehicle = PlayerVehicle.Get();
	if (IsValid(Vehicle))
	{
		const FVector Ue = Vehicle->GetActorLocation();
		const FVector Tm = NYCGeo::UEToNycTm(Ue);
		const FVector Forward = NYCGeo::DirectionFromUE(Vehicle->GetActorForwardVector());
		Observer.x = static_cast<float>(Tm.X);
		Observer.y = static_cast<float>(Tm.Y);
		Observer.z = static_cast<float>(Tm.Z);
		Observer.dirX = static_cast<float>(Forward.X);
		Observer.dirY = static_cast<float>(Forward.Y);
		Observer.speedMps = static_cast<float>(Vehicle->GetVelocity().Size()) / kCmPerMetre;
		Observer.playerVehicleValid = true;
		Observer.playerX = Observer.x;
		Observer.playerY = Observer.y;
		Observer.playerDirX = Observer.dirX;
		Observer.playerDirY = Observer.dirY;
		Observer.playerSpeedMps = Observer.speedMps;
	}
	else
	{
		const FVector Tm = NYCGeo::UEToNycTm(ObserverLocation);
		const FVector Forward = NYCGeo::DirectionFromUE(ObserverForward);
		Observer.x = static_cast<float>(Tm.X);
		Observer.y = static_cast<float>(Tm.Y);
		Observer.z = static_cast<float>(Tm.Z);
		Observer.dirX = static_cast<float>(Forward.X);
		Observer.dirY = static_cast<float>(Forward.Y);
		Observer.speedMps = ObserverSpeedMps;
		Observer.playerVehicleValid = false;
	}

	Worker->SetObserver(Observer);
}

void UNYCTrafficSubsystem::UpdateVehicles(const FNYCSimSnapshot& InSnapshot, float DeltaTime)
{
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	const TArray<FString>* RouteNames = nullptr;
	(void)RouteNames;

	SeenAgents.Reset();
	for (const nycsim_gameplay::VehicleSnapshot& Agent : InSnapshot.Vehicles)
	{
		const int32 AgentId = static_cast<int32>(Agent.id);
		SeenAgents.Add(AgentId);

		int32* PoolIndex = VehicleActorByAgent.Find(AgentId);
		bool bTeleport = false;
		ANYCTrafficVehicle* Actor = nullptr;
		if (PoolIndex != nullptr && VehiclePool.IsValidIndex(*PoolIndex))
		{
			Actor = VehiclePool[*PoolIndex];
		}
		else
		{
			Actor = AcquireVehicleActor();
			if (Actor == nullptr)
			{
				continue;  // pool at its cap: this agent simulates without a body this frame
			}
			Actor->Acquire(AgentId, Agent.cls, FleetMeshFor(Agent.cls), PaintFor(Agent.cls, AgentId));
			VehicleActorByAgent.Add(AgentId, VehiclePool.IndexOfByKey(Actor));
			bTeleport = true;
		}

		FNYCTrafficVehicleState State;
		State.AgentId = AgentId;
		State.VehicleClass = Agent.cls;
		State.Location = NYCGeo::NycTmToUE(FVector(Agent.x, Agent.y, Agent.z));
		// The simulation's heading is mathematical (0 = east, counter-clockwise); UE yaw is the compass form.
		State.Rotation = FRotator(0.f, NYCGeo::MathAngleToUEYaw(FMath::RadiansToDegrees(Agent.headingRad)), 0.f);
		State.SpeedMps = Agent.speedMps;
		State.WheelSpinDeg = FMath::RadiansToDegrees(Agent.wheelSpinRad);
		State.SteerDeg = FMath::RadiansToDegrees(Agent.steerRad);
		State.bBraking = (Agent.flags & nycsim_gameplay::kVehBrake) != 0;
		State.bIndicateLeft = (Agent.flags & nycsim_gameplay::kVehIndicatorLeft) != 0;
		State.bIndicateRight = (Agent.flags & nycsim_gameplay::kVehIndicatorRight) != 0;
		State.bHazards = (Agent.flags & nycsim_gameplay::kVehHazard) != 0;
		State.bSiren = (Agent.flags & nycsim_gameplay::kVehSiren) != 0;
		State.bDoorsOpen = (Agent.flags & nycsim_gameplay::kVehDoorsOpen) != 0;
		State.bHeadlights = (Agent.flags & nycsim_gameplay::kVehHeadlights) != 0;
		State.Honk = static_cast<float>(Agent.honking) / 255.f;

		if (Agent.routeName != 0xFFFFu && Worker.IsValid())
		{
			const std::vector<std::string>& Names = Worker->MutableTrafficSim().routeNames();
			if (Agent.routeName < Names.size())
			{
				State.DestinationSign = UTF8_TO_TCHAR(Names[Agent.routeName].c_str());
			}
		}

		const float DistanceMetres = static_cast<float>(FVector::Dist(State.Location, ObserverLocation)) / kCmPerMetre;
		Actor->SetLodLevel(LodForDistance(DistanceMetres, Settings.TrafficLodDistanceMetres));
		Actor->ApplyState(State, DeltaTime, bTeleport);

		const nycsim_gameplay::VehicleClassInfo Info = nycsim_gameplay::vehicleClassInfo(Agent.cls);
		if (Info.isTaxi)
		{
			// A cab shows its roof light when it is moving without a fare; the simulation has no fare model, so
			// the light follows the agent's own deterministic hash and its speed, which reads correctly.
			Actor->SetForHire((HashAgent(AgentId) & 1u) != 0 || Agent.speedMps < 0.5f);
		}
	}

	// Release the actors whose agents are gone.
	for (auto It = VehicleActorByAgent.CreateIterator(); It; ++It)
	{
		if (SeenAgents.Contains(It.Key()))
		{
			continue;
		}
		const int32 Index = It.Value();
		if (VehiclePool.IsValidIndex(Index))
		{
			VehiclePool[Index]->Release();
			FreeVehicleActors.Add(Index);
		}
		It.RemoveCurrent();
	}

	Stats.Vehicles = static_cast<int32>(InSnapshot.Vehicles.size());
	Stats.VehicleActorsPooled = VehiclePool.Num();
}

void UNYCTrafficSubsystem::UpdatePedestrians(const FNYCSimSnapshot& InSnapshot, float DeltaTime)
{
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();

	SeenAgents.Reset();
	for (const nycsim_gameplay::PedSnapshot& Agent : InSnapshot.Peds)
	{
		const int32 AgentId = static_cast<int32>(Agent.id);
		SeenAgents.Add(AgentId);

		int32* PoolIndex = PedestrianActorByAgent.Find(AgentId);
		bool bTeleport = false;
		ANYCPedestrian* Actor = nullptr;
		if (PoolIndex != nullptr && PedestrianPool.IsValidIndex(*PoolIndex))
		{
			Actor = PedestrianPool[*PoolIndex];
		}
		else
		{
			Actor = AcquirePedestrianActor();
			if (Actor == nullptr)
			{
				continue;
			}
			Actor->Acquire(AgentId, CrowdMeshFor(Agent.archetype), Agent.archetype, Agent.variant);
			PedestrianActorByAgent.Add(AgentId, PedestrianPool.IndexOfByKey(Actor));
			bTeleport = true;
		}

		FNYCPedestrianState State;
		State.AgentId = AgentId;
		State.Location = NYCGeo::NycTmToUE(FVector(Agent.x, Agent.y, Agent.z));
		State.Rotation = FRotator(0.f, NYCGeo::MathAngleToUEYaw(FMath::RadiansToDegrees(Agent.headingRad)), 0.f);
		State.SpeedMps = Agent.speedMps;
		State.State = Agent.state;
		State.Archetype = Agent.archetype;
		State.Variant = Agent.variant;
		State.Flags = Agent.flags;

		const float DistanceMetres = static_cast<float>(FVector::Dist(State.Location, ObserverLocation)) / kCmPerMetre;
		Actor->SetLodLevel(LodForDistance(DistanceMetres, Settings.PedestrianLodDistanceMetres));
		Actor->ApplyState(State, DeltaTime, bTeleport);
	}

	for (auto It = PedestrianActorByAgent.CreateIterator(); It; ++It)
	{
		if (SeenAgents.Contains(It.Key()))
		{
			continue;
		}
		const int32 Index = It.Value();
		if (PedestrianPool.IsValidIndex(Index))
		{
			PedestrianPool[Index]->Release();
			FreePedestrianActors.Add(Index);
		}
		It.RemoveCurrent();
	}

	Stats.Pedestrians = static_cast<int32>(InSnapshot.Peds.size());
	Stats.PedestrianActorsPooled = PedestrianPool.Num();
}

void UNYCTrafficSubsystem::DispatchEvents(const FNYCSimSnapshot& InSnapshot)
{
	if (InSnapshot.Events.empty())
	{
		return;
	}
	UWorld* World = GetWorld();
	UNYCAudioSubsystem* Audio = World != nullptr ? World->GetSubsystem<UNYCAudioSubsystem>() : nullptr;
	if (Audio == nullptr)
	{
		return;
	}
	for (const nycsim_gameplay::TrafficEvent& Event : InSnapshot.Events)
	{
		const FVector Location = NYCGeo::NycTmToUE(FVector(Event.x, Event.y, Event.z));
		switch (Event.kind)
		{
		case nycsim_gameplay::TrafficEvent::Kind::Honk:
			Audio->PlayTrafficHorn(Location, Event.intensity);
			break;
		case nycsim_gameplay::TrafficEvent::Kind::HardBrake:
			Audio->PlayTyreScreech(Location, Event.intensity);
			break;
		default:
			break;
		}
	}
}

void UNYCTrafficSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (!bStarted)
	{
		TryStartWorker();
		return;
	}
	if (!Worker.IsValid() || !Snapshot.IsValid())
	{
		return;
	}

	// The observer is the player's car, or whatever the on-foot pawn last published.
	if (!PlayerVehicle.IsValid())
	{
		if (const UWorld* World = GetWorld())
		{
			if (const APlayerController* PC = World->GetFirstPlayerController())
			{
				FVector Location;
				FRotator Rotation;
				PC->GetPlayerViewPoint(Location, Rotation);
				const APawn* Pawn = PC->GetPawn();
				SetObserverTransform(Location, Rotation.Vector(),
									 Pawn != nullptr ? static_cast<float>(Pawn->GetVelocity().Size()) / kCmPerMetre
													 : 0.f);
			}
		}
	}
	else
	{
		ObserverLocation = PlayerVehicle->GetActorLocation();
		ObserverForward = PlayerVehicle->GetActorForwardVector();
	}
	PublishObserver();

	const bool bNew = Worker->ReadSnapshot(*Snapshot, LastConsumedStep);
	if (bNew)
	{
		DispatchEvents(*Snapshot);
	}

	UpdateVehicles(*Snapshot, DeltaTime);
	UpdatePedestrians(*Snapshot, DeltaTime);

	Stats.TrafficStepMs = static_cast<float>(Worker->GetAverageTrafficStepMs());
	Stats.PedStepMs = static_cast<float>(Worker->GetAveragePedStepMs());
	Stats.Honks = static_cast<int32>(Worker->GetHonks());
	Stats.RedLightEntries = static_cast<int32>(Worker->GetRedLightEntries());
}
