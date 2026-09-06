#include "UI/NYCGpsSubsystem.h"

#include <memory>
#include <string>
#include <utility>

#include "Async/Async.h"
#include "CoreAdapter/GameplayRoadNetwork.h"
#include "CoreAdapter/NYCGeo.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NYCSimRuntime.h"
#include "Traffic/NYCRoadNetworkSubsystem.h"
#include "UI/NYCGpsWidget.h"

/** Router plus its scratch, kept out of the header so no core type leaks into the module's public API. */
struct FNYCGpsRouterState
{
	std::unique_ptr<nycsim::routing::Router> Router;
	nycsim::routing::RouteResult Result;
	nycsim::routing::RouteProfile Profile;
	const nycsim_gameplay::RoadNetwork* Network = nullptr;
};

namespace
{
constexpr float kCmPerMetre = 100.f;

ENYCManoeuvre ToManoeuvre(nycsim::routing::Instruction::Kind Kind)
{
	using Kind_t = nycsim::routing::Instruction::Kind;
	switch (Kind)
	{
	case Kind_t::Depart: return ENYCManoeuvre::Depart;
	case Kind_t::TurnLeft: return ENYCManoeuvre::TurnLeft;
	case Kind_t::TurnRight: return ENYCManoeuvre::TurnRight;
	case Kind_t::SlightLeft: return ENYCManoeuvre::SlightLeft;
	case Kind_t::SlightRight: return ENYCManoeuvre::SlightRight;
	case Kind_t::SharpLeft: return ENYCManoeuvre::SharpLeft;
	case Kind_t::SharpRight: return ENYCManoeuvre::SharpRight;
	case Kind_t::UTurn: return ENYCManoeuvre::UTurn;
	case Kind_t::Ramp: return ENYCManoeuvre::Ramp;
	case Kind_t::Bridge: return ENYCManoeuvre::Bridge;
	case Kind_t::Tunnel: return ENYCManoeuvre::Tunnel;
	case Kind_t::Arrive: return ENYCManoeuvre::Arrive;
	case Kind_t::Continue:
	default: return ENYCManoeuvre::Continue;
	}
}

FString KindLabel(nycsim_gameplay::SearchEntry::Kind Kind)
{
	switch (Kind)
	{
	case nycsim_gameplay::SearchEntry::Kind::Address: return TEXT("Address");
	case nycsim_gameplay::SearchEntry::Kind::Street: return TEXT("Street");
	case nycsim_gameplay::SearchEntry::Kind::BusStop: return TEXT("Bus stop");
	case nycsim_gameplay::SearchEntry::Kind::Landmark: return TEXT("Landmark");
	default: return TEXT("Place");
	}
}
}  // namespace

UNYCGpsSubsystem::UNYCGpsSubsystem() = default;

bool UNYCGpsSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World != nullptr && World->IsGameWorld();
}

void UNYCGpsSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UNYCRoadNetworkSubsystem>();
	Super::Initialize(Collection);
	RouterState = MakeUnique<FNYCGpsRouterState>();

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.gps.search"), TEXT("nycsim.gps.search <text> - list matching destinations."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>& Args, UWorld*, FOutputDevice& Ar) {
				const FString Query = FString::Join(Args, TEXT(" "));
				const TArray<FNYCGpsSearchResult> Results = Search(Query, 12);
				Ar.Logf(TEXT("%d result(s) for '%s'"), Results.Num(), *Query);
				for (const FNYCGpsSearchResult& Result : Results)
				{
					Ar.Logf(TEXT("  [%s] %s  (%.0f m)"), *Result.Kind, *Result.Label, Result.DistanceMetres);
				}
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.gps.route"), TEXT("nycsim.gps.route <text> - route to the best match for <text>."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>& Args, UWorld*, FOutputDevice& Ar) {
				const FString Query = FString::Join(Args, TEXT(" "));
				const TArray<FNYCGpsSearchResult> Results = Search(Query, 1);
				if (Results.Num() == 0)
				{
					Ar.Logf(TEXT("no destination matches '%s'"), *Query);
					return;
				}
				if (SetDestinationWorld(Results[0].WorldLocation))
				{
					Ar.Logf(TEXT("routing to %s: %.0f m, ETA %.0f s, %d instructions"), *Results[0].Label,
							RemainingMetres, EtaSeconds, Instructions.Num());
				}
				else
				{
					Ar.Logf(TEXT("no route to %s"), *Results[0].Label);
				}
			})));

	ConsoleCommands.Add(new FAutoConsoleCommandWithWorldArgsAndOutputDevice(
		TEXT("nycsim.gps.clear"), TEXT("Cancel the current route."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateLambda(
			[this](const TArray<FString>&, UWorld*, FOutputDevice& Ar) {
				ClearDestination();
				Ar.Logf(TEXT("route cleared"));
			})));
}

void UNYCGpsSubsystem::Deinitialize()
{
	for (FAutoConsoleCommandWithWorldArgsAndOutputDevice* Command : ConsoleCommands)
	{
		delete Command;
	}
	ConsoleCommands.Reset();
	RouterState.Reset();
	Super::Deinitialize();
}

TStatId UNYCGpsSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCGpsSubsystem, STATGROUP_Tickables);
}

TSubclassOf<UUserWidget> UNYCGpsSubsystem::GetScreenWidgetClass() const
{
	return UNYCGpsWidget::StaticClass();
}

void UNYCGpsSubsystem::StartRouterAsync()
{
	if (bRouterStarting || bRouterReady)
	{
		return;
	}
	UWorld* World = GetWorld();
	UNYCRoadNetworkSubsystem* Roads = World != nullptr ? World->GetSubsystem<UNYCRoadNetworkSubsystem>() : nullptr;
	if (Roads == nullptr || !Roads->IsReady())
	{
		return;
	}
	const nycsim_gameplay::RoadNetwork* Network = Roads->GetNetwork();
	if (Network == nullptr)
	{
		return;
	}
	bRouterStarting = true;
	RouterState->Network = Network;

	TWeakObjectPtr<UNYCGpsSubsystem> WeakThis(this);
	FNYCGpsRouterState* State = RouterState.Get();
	AsyncTask(ENamedThreads::AnyBackgroundThreadNormalTask, [WeakThis, State, Network]() {
		std::string Error;
		// Eight ALT landmarks: preprocessing is a handful of Dijkstras and it keeps a city-wide query in the
		// low milliseconds, which is what makes an instant re-route possible.
		std::unique_ptr<nycsim::routing::Router> Router = Network->makeRouter(8, Error);
		const FString ErrorText = UTF8_TO_TCHAR(Error.c_str());
		nycsim::routing::Router* Raw = Router.release();
		AsyncTask(ENamedThreads::GameThread, [WeakThis, State, Raw, ErrorText]() {
			std::unique_ptr<nycsim::routing::Router> Owned(Raw);
			UNYCGpsSubsystem* Self = WeakThis.Get();
			if (Self == nullptr)
			{
				return;
			}
			if (Owned)
			{
				State->Router = std::move(Owned);
				Self->bRouterReady = true;
				UE_LOG(LogNYCSim, Log, TEXT("GPS: router attached (%u landmarks)."),
					   State->Router->landmarkCount());
			}
			else
			{
				UE_LOG(LogNYCSim, Error, TEXT("GPS: router could not attach: %s"), *ErrorText);
			}
			Self->bRouterStarting = false;
		});
	});
}

FVector UNYCGpsSubsystem::GetPlayerWorldLocation() const
{
	const UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return FVector::ZeroVector;
	}
	if (const APlayerController* PlayerController = World->GetFirstPlayerController())
	{
		if (const APawn* Pawn = PlayerController->GetPawn())
		{
			return Pawn->GetActorLocation();
		}
		FVector Location;
		FRotator Rotation;
		PlayerController->GetPlayerViewPoint(Location, Rotation);
		return Location;
	}
	return FVector::ZeroVector;
}

bool UNYCGpsSubsystem::ComputeRoute(const FVector& FromWorld, const FVector& ToWorld)
{
	if (!bRouterReady || !RouterState.IsValid() || RouterState->Router == nullptr)
	{
		return false;
	}
	const FVector From = NYCGeo::UEToNycTm(FromWorld);
	const FVector To = NYCGeo::UEToNycTm(ToWorld);

	RouterState->Result.clear();
	const bool bOk = RouterState->Router->routePoints(
		static_cast<float>(From.X), static_cast<float>(From.Y), static_cast<float>(To.X), static_cast<float>(To.Y),
		RouterState->Profile, RouterState->Result, /*snap radius*/ 80.f);

	Instructions.Reset();
	RoutePolyline.Reset();
	NextInstructionIndex = 0;

	if (!bOk || !RouterState->Result.ok)
	{
		bHasRoute = false;
		RemainingMetres = 0.f;
		EtaSeconds = 0.f;
		OnRouteChanged.Broadcast(false);
		return false;
	}

	Instructions.Reserve(static_cast<int32>(RouterState->Result.instructions.size()));
	for (const nycsim::routing::Instruction& Source : RouterState->Result.instructions)
	{
		FNYCGpsInstruction Instruction;
		Instruction.Manoeuvre = ToManoeuvre(Source.kind);
		Instruction.Text = UTF8_TO_TCHAR(Source.text.c_str());
		Instruction.Street = UTF8_TO_TCHAR(Source.street.c_str());
		Instruction.CumulativeMetres = Source.cumulative_m;
		Instruction.WorldLocation = NYCGeo::NycTmToUE(FVector(Source.position.x, Source.position.y, Source.position.z));
		Instructions.Add(MoveTemp(Instruction));
	}

	RoutePolyline.Reserve(static_cast<int32>(RouterState->Result.polyline.size()));
	for (const nycsim::routing::Vec3& Point : RouterState->Result.polyline)
	{
		RoutePolyline.Add(NYCGeo::NycTmToUE(FVector(Point.x, Point.y, Point.z)));
	}

	RemainingMetres = RouterState->Result.length_m;
	EtaSeconds = RouterState->Result.eta_s;
	DestinationWorld = ToWorld;
	bHasRoute = true;
	OnRouteChanged.Broadcast(true);

	UE_LOG(LogNYCSim, Log, TEXT("GPS: route %.0f m, ETA %.0f s, %d instructions, %d polyline points."),
		   RemainingMetres, EtaSeconds, Instructions.Num(), RoutePolyline.Num());
	return true;
}

bool UNYCGpsSubsystem::SetDestinationWorld(const FVector& WorldLocation)
{
	DestinationWorld = WorldLocation;
	RerouteTimer = 0.f;
	return ComputeRoute(GetPlayerWorldLocation(), WorldLocation);
}

void UNYCGpsSubsystem::ClearDestination()
{
	bHasRoute = false;
	Instructions.Reset();
	RoutePolyline.Reset();
	RemainingMetres = 0.f;
	EtaSeconds = 0.f;
	NextInstructionIndex = 0;
	OnRouteChanged.Broadcast(false);
}

bool UNYCGpsSubsystem::GetNextInstruction(FNYCGpsInstruction& OutInstruction, float& OutDistanceMetres) const
{
	if (!bHasRoute || !Instructions.IsValidIndex(NextInstructionIndex))
	{
		return false;
	}
	OutInstruction = Instructions[NextInstructionIndex];
	const FVector Player = GetPlayerWorldLocation();
	OutDistanceMetres = static_cast<float>(FVector::Dist2D(Player, OutInstruction.WorldLocation)) / kCmPerMetre;
	return true;
}

void UNYCGpsSubsystem::UpdateProgress(const FVector& PlayerWorld)
{
	if (!bHasRoute || RoutePolyline.Num() < 2)
	{
		return;
	}

	// Nearest point on the route polyline, and the distance from it.
	float BestDistSq = TNumericLimits<float>::Max();
	int32 BestSegment = 0;
	float BestAlpha = 0.f;
	for (int32 i = 0; i + 1 < RoutePolyline.Num(); ++i)
	{
		const FVector A = RoutePolyline[i];
		const FVector B = RoutePolyline[i + 1];
		const FVector AB = B - A;
		const double LengthSq = AB.SizeSquared2D();
		double Alpha = 0.0;
		if (LengthSq > 1.0)
		{
			Alpha = FMath::Clamp(FVector::DotProduct(PlayerWorld - A, AB) / LengthSq, 0.0, 1.0);
		}
		const FVector Closest = A + AB * Alpha;
		const float DistSq = static_cast<float>(FVector::DistSquared2D(PlayerWorld, Closest));
		if (DistSq < BestDistSq)
		{
			BestDistSq = DistSq;
			BestSegment = i;
			BestAlpha = static_cast<float>(Alpha);
		}
	}

	// Remaining distance along the polyline from the projection to the end.
	double Remaining = 0.0;
	{
		const FVector A = RoutePolyline[BestSegment];
		const FVector B = RoutePolyline[BestSegment + 1];
		Remaining += FVector::Dist2D(A + (B - A) * BestAlpha, B);
		for (int32 i = BestSegment + 1; i + 1 < RoutePolyline.Num(); ++i)
		{
			Remaining += FVector::Dist2D(RoutePolyline[i], RoutePolyline[i + 1]);
		}
	}
	const float NewRemaining = static_cast<float>(Remaining) / kCmPerMetre;
	// Scale the ETA by how much of the route is left, so it counts down with the distance.
	if (RemainingMetres > 1.f)
	{
		EtaSeconds *= NewRemaining / RemainingMetres;
	}
	RemainingMetres = NewRemaining;

	// Advance the instruction once the player is past it.
	while (Instructions.IsValidIndex(NextInstructionIndex))
	{
		const float Distance =
			static_cast<float>(FVector::Dist2D(PlayerWorld, Instructions[NextInstructionIndex].WorldLocation)) /
			kCmPerMetre;
		if (Distance < 18.f && NextInstructionIndex + 1 < Instructions.Num())
		{
			++NextInstructionIndex;
			continue;
		}
		break;
	}

	// Arrived?
	if (RemainingMetres < 12.f)
	{
		UE_LOG(LogNYCSim, Log, TEXT("GPS: arrived."));
		ClearDestination();
		return;
	}

	// Off route: recompute.
	const float OffRouteMetres = FMath::Sqrt(BestDistSq) / kCmPerMetre;
	if (OffRouteMetres > OffRouteToleranceMetres && RerouteTimer >= RerouteCooldownSeconds)
	{
		RerouteTimer = 0.f;
		UE_LOG(LogNYCSim, Verbose, TEXT("GPS: %.0f m off route; recomputing."), OffRouteMetres);
		ComputeRoute(PlayerWorld, DestinationWorld);
	}
}

TArray<FNYCGpsSearchResult> UNYCGpsSubsystem::Search(const FString& Query, int32 MaxResults) const
{
	TArray<FNYCGpsSearchResult> Out;
	const UWorld* World = GetWorld();
	const UNYCRoadNetworkSubsystem* Roads = World != nullptr ? World->GetSubsystem<UNYCRoadNetworkSubsystem>() : nullptr;
	const nycsim_gameplay::RoadNetwork* Network = Roads != nullptr ? Roads->GetNetwork() : nullptr;
	if (Network == nullptr || Query.IsEmpty())
	{
		return Out;
	}

	const int32 Cap = FMath::Clamp(MaxResults, 1, 64);
	TArray<nycsim_gameplay::SearchHit> Hits;
	Hits.SetNum(Cap);
	const std::string Needle = TCHAR_TO_UTF8(*Query);
	const uint32 Found = Network->search(Needle, Hits.GetData(), static_cast<uint32_t>(Cap));

	const FVector Player = GetPlayerWorldLocation();
	for (uint32 i = 0; i < Found; ++i)
	{
		const nycsim_gameplay::SearchEntry& Entry = Network->searchEntry(Hits[static_cast<int32>(i)].entry);
		FNYCGpsSearchResult Result;
		Result.Label = UTF8_TO_TCHAR(Entry.label.c_str());
		Result.Kind = KindLabel(Entry.kind);
		Result.WorldLocation = NYCGeo::NycTmToUE(FVector(Entry.x, Entry.y, 0.0));
		Result.DistanceMetres = static_cast<float>(FVector::Dist2D(Player, Result.WorldLocation)) / kCmPerMetre;
		Out.Add(MoveTemp(Result));
	}
	return Out;
}

void UNYCGpsSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	RerouteTimer += DeltaTime;

	if (!bRouterReady)
	{
		StartRouterAsync();
		return;
	}

	const FVector Player = GetPlayerWorldLocation();

	// Current street: snap the player to the nearest lane and read its name.
	const UWorld* World = GetWorld();
	const UNYCRoadNetworkSubsystem* Roads = World != nullptr ? World->GetSubsystem<UNYCRoadNetworkSubsystem>() : nullptr;
	if (const nycsim_gameplay::RoadNetwork* Network = Roads != nullptr ? Roads->GetNetwork() : nullptr)
	{
		const FVector Tm = NYCGeo::UEToNycTm(Player);
		const nycsim::routing::NearestLane Nearest = Network->graph().nearestLane(
			static_cast<float>(Tm.X), static_cast<float>(Tm.Y), nycsim::routing::kAllLaneKinds, 45.f, false);
		CurrentStreet = Nearest.lane != nycsim::routing::kInvalidIndex
							? UTF8_TO_TCHAR(Network->laneStreetName(Nearest.lane).c_str())
							: FString();
	}

	UpdateProgress(Player);
}
