#include "Traffic/NYCRoadNetworkSubsystem.h"

#include "Async/Async.h"
#include "CoreAdapter/GameplayRoadNetwork.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NYCSimRuntime.h"
#include "World/NYCSimWorldSettings.h"

namespace
{
/// Reads a file through Unreal's platform file layer so packaged (pak) builds work.
bool UnrealFileReader(void* /*Context*/, const std::string& Path, std::vector<uint8_t>& Out, std::string& Error)
{
	const FString FilePath = UTF8_TO_TCHAR(Path.c_str());
	if (!IFileManager::Get().FileExists(*FilePath))
	{
		Error = nycsim_gameplay::RoadNetwork::kMissingFile;
		return false;
	}
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *FilePath))
	{
		Error = TCHAR_TO_UTF8(*FString::Printf(TEXT("could not read %s"), *FilePath));
		return false;
	}
	Out.assign(Bytes.GetData(), Bytes.GetData() + Bytes.Num());
	return true;
}
}  // namespace

UNYCRoadNetworkSubsystem::UNYCRoadNetworkSubsystem() = default;

bool UNYCRoadNetworkSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	// Game worlds only: the editor preview and inactive worlds have no traffic.
	const UWorld* World = Cast<UWorld>(Outer);
	return World != nullptr && (World->IsGameWorld());
}

void UNYCRoadNetworkSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Network = MakeUnique<nycsim_gameplay::RoadNetwork>();
	StartLoad();

	InfoCommand = new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.roads.info"), TEXT("Print the loaded road network's counts and load notes."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				if (!bReady)
				{
					Ar.Logf(TEXT("road network: not ready (%s)"), LoadError.IsEmpty() ? TEXT("loading") : *LoadError);
					return;
				}
				Ar.Logf(TEXT("road network%s: %d nodes, %d segments, %d road lanes, %d junction lanes, %d signal "
							 "plans, %d search entries, loaded in %.2f s"),
						Info.bSynthetic ? TEXT(" (synthetic grid)") : TEXT(""), Info.Nodes, Info.Segments,
						Info.RoadLanes, Info.JunctionLanes, Info.SignalPlans, Info.SearchEntries, Info.LoadSeconds);
				for (const FString& Note : Notes)
				{
					Ar.Logf(TEXT("  note: %s"), *Note);
				}
			}));
}

void UNYCRoadNetworkSubsystem::Deinitialize()
{
	if (InfoCommand != nullptr)
	{
		delete InfoCommand;
		InfoCommand = nullptr;
	}
	// The traffic subsystem stops its worker in its own Deinitialize, which the collection runs first for
	// dependent subsystems; by the time we get here nothing else is reading the graph.
	Network.Reset();
	bReady = false;
	Super::Deinitialize();
}

void UNYCRoadNetworkSubsystem::Reload()
{
	bReady = false;
	StartLoad();
}

void UNYCRoadNetworkSubsystem::StartLoad()
{
	if (bLoading.Load())
	{
		return;
	}
	bLoading.Store(true);

	const UNYCSimWorldSettings& WorldSettings = UNYCSimWorldSettings::Get();
	const FString RuntimeDir = UNYCSimWorldSettings::ResolveProjectPath(WorldSettings.RuntimeDataDir);
	nycsim_gameplay::RoadNetwork* Target = Network.Get();
	TWeakObjectPtr<UNYCRoadNetworkSubsystem> WeakThis(this);

	AsyncTask(ENamedThreads::AnyBackgroundThreadNormalTask, [WeakThis, Target, RuntimeDir]() {
		std::string Error;
		const std::string Dir = TCHAR_TO_UTF8(*RuntimeDir);
		bool bSuccess = Target->load(Dir, Error, &UnrealFileReader, nullptr);
		FString ErrorText = UTF8_TO_TCHAR(Error.c_str());

		if (!bSuccess)
		{
			// No runtime data yet (the roads stage has not produced roadgraph.nycb): fall back to the synthetic
			// Manhattan grid so the world is still drivable, and say so loudly.
			std::string GridError;
			if (Target->buildSyntheticGrid(10, 26, -4200.f, 900.f, GridError))
			{
				bSuccess = true;
				ErrorText = FString::Printf(
					TEXT("roadgraph.nycb unavailable (%s); using the synthetic Manhattan grid instead"), *ErrorText);
			}
			else
			{
				ErrorText = FString::Printf(TEXT("%s; synthetic fallback also failed: %s"), *ErrorText,
											UTF8_TO_TCHAR(GridError.c_str()));
			}
		}

		AsyncTask(ENamedThreads::GameThread, [WeakThis, bSuccess, ErrorText]() {
			if (UNYCRoadNetworkSubsystem* Self = WeakThis.Get())
			{
				Self->LoadError = ErrorText;
				Self->FinishLoad(bSuccess);
			}
		});
	});
}

void UNYCRoadNetworkSubsystem::FinishLoad(bool bSuccess)
{
	bLoading.Store(false);
	Notes.Reset();
	if (bSuccess && Network.IsValid() && Network->loaded())
	{
		const nycsim_gameplay::RoadNetworkStats& Stats = Network->stats();
		Info.Nodes = static_cast<int32>(Stats.nodes);
		Info.Segments = static_cast<int32>(Stats.segments);
		Info.RoadLanes = static_cast<int32>(Stats.roadLanes);
		Info.JunctionLanes = static_cast<int32>(Stats.junctionLanes);
		Info.SignalPlans = static_cast<int32>(Stats.signalPlans);
		Info.SearchEntries = static_cast<int32>(Network->searchEntryCount());
		Info.LoadSeconds = static_cast<float>(Stats.loadSeconds);
		Info.bSynthetic = Network->isSynthetic();
		for (const std::string& Note : Network->notes())
		{
			Notes.Add(UTF8_TO_TCHAR(Note.c_str()));
		}
		bReady = true;

		UE_LOG(LogNYCSim, Log,
			   TEXT("Road network ready%s: %d nodes, %d segments, %d road lanes, %d junction lanes, %d signal "
					"plans, %d search entries (%.2f s)."),
			   Info.bSynthetic ? TEXT(" [synthetic grid]") : TEXT(""), Info.Nodes, Info.Segments, Info.RoadLanes,
			   Info.JunctionLanes, Info.SignalPlans, Info.SearchEntries, Info.LoadSeconds);
		for (const FString& Note : Notes)
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Road network note: %s"), *Note);
		}
		if (!LoadError.IsEmpty())
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Road network: %s"), *LoadError);
		}
	}
	else
	{
		bReady = false;
		UE_LOG(LogNYCSim, Error, TEXT("Road network failed to load: %s"), *LoadError);
	}
	OnNetworkReady.Broadcast(bReady);
}
