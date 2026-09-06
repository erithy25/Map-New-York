#include "Character/NYCNavigationSubsystem.h"

#include "Components/BrushComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavMesh/RecastNavMesh.h"
#include "NavModifierComponent.h"

#include <type_traits>
#include <utility>
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "NYCSimRuntime.h"

namespace
{
constexpr float kCmPerMetre = 100.f;

const FName TagSidewalk(TEXT("NYCSidewalk"));
const FName TagPlaza(TEXT("NYCPlaza"));
const FName TagPark(TEXT("NYCPark"));
const FName TagBridgeWalkway(TEXT("NYCBridgeWalkway"));
const FName TagRoadbed(TEXT("NYCRoadbed"));
const FName TagNotWalkable(TEXT("NYCNotWalkable"));

// ARecastNavMesh gained SetRuntimeGenerationMode after 5.0 and the underlying property is protected, so the call
// goes through a detector: when it is unavailable the subsystem says exactly which project setting to change
// instead of silently generating nothing at runtime.
template <typename T, typename = void>
struct THasSetRuntimeGenerationMode : std::false_type
{
};

template <typename T>
struct THasSetRuntimeGenerationMode<
	T, decltype(static_cast<void>(std::declval<T&>().SetRuntimeGenerationMode(ERuntimeGenerationType::Dynamic)))>
	: std::true_type
{
};

template <typename T>
bool TrySetDynamicGeneration(T& NavMesh)
{
	if constexpr (THasSetRuntimeGenerationMode<T>::value)
	{
		NavMesh.SetRuntimeGenerationMode(ERuntimeGenerationType::Dynamic);
		return true;
	}
	else
	{
		return NavMesh.GetRuntimeGenerationMode() == ERuntimeGenerationType::Dynamic;
	}
}
}  // namespace

UNYCNavArea_Sidewalk::UNYCNavArea_Sidewalk()
{
	DefaultCost = 1.f;
	DrawColor = FColor(120, 200, 255);
}

UNYCNavArea_Park::UNYCNavArea_Park()
{
	// A park path is as good as a sidewalk; grass costs a little more, and one class covers both because the
	// planimetric open-space polygons do not separate them.
	DefaultCost = 1.4f;
	DrawColor = FColor(120, 220, 130);
}

UNYCNavArea_Roadbed::UNYCNavArea_Roadbed()
{
	// Walkable (people cross, and jaywalk) but six times the cost, so a route uses the sidewalk and only crosses
	// where it must.
	DefaultCost = 6.f;
	FixedAreaEnteringCost = 40.f;
	DrawColor = FColor(220, 140, 120);
}

UNYCNavigationSubsystem::UNYCNavigationSubsystem() = default;

bool UNYCNavigationSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World != nullptr && World->IsGameWorld();
}

void UNYCNavigationSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
}

void UNYCNavigationSubsystem::Deinitialize()
{
	if (IsValid(BoundsVolume))
	{
		BoundsVolume->Destroy();
		BoundsVolume = nullptr;
	}
	TaggedActors.Reset();
	bBoundsPlaced = false;
	Super::Deinitialize();
}

TStatId UNYCNavigationSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCNavigationSubsystem, STATGROUP_Tickables);
}

void UNYCNavigationSubsystem::ConfigureRecast()
{
	if (bRecastConfigured)
	{
		return;
	}
	UWorld* World = GetWorld();
	UNavigationSystemV1* NavSystem = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
	if (NavSystem == nullptr)
	{
		return;
	}
	for (ANavigationData* Data : NavSystem->NavDataSet)
	{
		ARecastNavMesh* Recast = Cast<ARecastNavMesh>(Data);
		if (Recast == nullptr)
		{
			continue;
		}
		// A pedestrian: 34 cm radius, 176 cm tall, able to step a 20 cm kerb and climb a 35° ramp.
		Recast->AgentRadius = 34.f;
		Recast->AgentHeight = 176.f;
		Recast->AgentMaxStepHeight = 22.f;
		Recast->AgentMaxSlope = 38.f;
		Recast->CellSize = 12.f;   // 12 cm cells resolve a 1.5 m sidewalk into 12 cells
		Recast->CellHeight = 8.f;
		Recast->MergeRegionSize = 400.f;
		Recast->MinRegionArea = 200.f;
		Recast->TileSizeUU = 1000.f;  // 10 m Recast tiles: fast partial rebuilds while streaming
		const bool bDynamic = TrySetDynamicGeneration(*Recast);
		Recast->RebuildAll();
		bRecastConfigured = true;
		if (bDynamic)
		{
			UE_LOG(LogNYCSim, Log,
				   TEXT("Navigation: Recast configured for a 34 cm / 176 cm pedestrian with dynamic runtime "
						"generation."));
		}
		else
		{
			UE_LOG(LogNYCSim, Warning,
				   TEXT("Navigation: the RecastNavMesh is not set to dynamic runtime generation, so the navmesh "
						"will not follow the streamed city. Set Project Settings > Navigation Mesh > Runtime "
						"Generation to 'Dynamic'."));
		}
	}
	if (!bRecastConfigured)
	{
		UE_LOG(LogNYCSim, Warning,
			   TEXT("Navigation: no RecastNavMesh in the world; the character walks on collision only. Add a "
					"RecastNavMesh actor to the persistent level (the import script places one)."));
		bRecastConfigured = true;  // do not spam
	}
}

void UNYCNavigationSubsystem::EnsureBoundsVolume()
{
	if (IsValid(BoundsVolume))
	{
		return;
	}
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	BoundsVolume = World->SpawnActor<ANavMeshBoundsVolume>(ANavMeshBoundsVolume::StaticClass(), FVector::ZeroVector,
														   FRotator::ZeroRotator, Params);
	if (BoundsVolume == nullptr)
	{
		UE_LOG(LogNYCSim, Error, TEXT("Navigation: could not spawn the navigation bounds volume."));
		return;
	}
	BoundsVolume->SetActorScale3D(FVector(BoundsHalfSizeMetres * kCmPerMetre / 100.f,
										  BoundsHalfSizeMetres * kCmPerMetre / 100.f,
										  BoundsHalfHeightMetres * kCmPerMetre / 100.f));
	if (UBrushComponent* Brush = BoundsVolume->GetBrushComponent())
	{
		Brush->SetMobility(EComponentMobility::Movable);
	}
	UE_LOG(LogNYCSim, Log, TEXT("Navigation: bounds volume created (%.0f x %.0f x %.0f m)."),
		   BoundsHalfSizeMetres * 2.f, BoundsHalfSizeMetres * 2.f, BoundsHalfHeightMetres * 2.f);
}

void UNYCNavigationSubsystem::MoveBoundsTo(const FVector& Centre)
{
	if (!IsValid(BoundsVolume))
	{
		return;
	}
	BoundsVolume->SetActorLocation(Centre);
	BoundsCentre = Centre;
	bBoundsPlaced = true;

	UWorld* World = GetWorld();
	if (UNavigationSystemV1* NavSystem = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World))
	{
		// Tell the navigation system the bounds moved so it rebuilds only the tiles that changed.
		NavSystem->OnNavigationBoundsUpdated(BoundsVolume);
	}
}

int32 UNYCNavigationSubsystem::ApplyNavAreasToTaggedActors()
{
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return 0;
	}
	int32 Applied = 0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (!IsValid(Actor) || Actor->Tags.Num() == 0 || TaggedActors.Contains(Actor))
		{
			continue;
		}

		TSubclassOf<UNavArea> AreaClass = nullptr;
		bool bNotWalkable = false;
		if (Actor->Tags.Contains(TagSidewalk) || Actor->Tags.Contains(TagPlaza) ||
			Actor->Tags.Contains(TagBridgeWalkway))
		{
			AreaClass = UNYCNavArea_Sidewalk::StaticClass();
		}
		else if (Actor->Tags.Contains(TagPark))
		{
			AreaClass = UNYCNavArea_Park::StaticClass();
		}
		else if (Actor->Tags.Contains(TagRoadbed))
		{
			AreaClass = UNYCNavArea_Roadbed::StaticClass();
		}
		else if (Actor->Tags.Contains(TagNotWalkable))
		{
			bNotWalkable = true;
		}
		else
		{
			continue;
		}

		TArray<UPrimitiveComponent*> Primitives;
		Actor->GetComponents<UPrimitiveComponent>(Primitives);
		for (UPrimitiveComponent* Primitive : Primitives)
		{
			if (Primitive == nullptr)
			{
				continue;
			}
			Primitive->SetCanEverAffectNavigation(!bNotWalkable);
		}

		// A non-default area (park cost, roadbed cost) is applied with a nav modifier component, which is the
		// engine's supported way to stamp an area class over an actor's bounds at runtime. Sidewalks, plazas and
		// bridge walkways keep the default area, which is already the cheapest.
		if (!bNotWalkable && AreaClass != nullptr && AreaClass != UNYCNavArea_Sidewalk::StaticClass())
		{
			UNavModifierComponent* Modifier = Actor->FindComponentByClass<UNavModifierComponent>();
			if (Modifier == nullptr)
			{
				Modifier = NewObject<UNavModifierComponent>(Actor);
				Modifier->SetupAttachment(Actor->GetRootComponent());
				Modifier->RegisterComponent();
			}
			Modifier->SetAreaClass(AreaClass);
		}
		TaggedActors.Add(Actor);
		++Applied;
	}
	TaggedActorCount += Applied;
	if (Applied > 0)
	{
		UE_LOG(LogNYCSim, Verbose, TEXT("Navigation: nav areas applied to %d newly streamed actors (%d total)."),
			   Applied, TaggedActorCount);
	}
	return Applied;
}

bool UNYCNavigationSubsystem::ProjectToNavigation(const FVector& Point, FVector& OutProjected,
												  float SearchExtentCm) const
{
	UWorld* World = GetWorld();
	UNavigationSystemV1* NavSystem = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
	if (NavSystem == nullptr)
	{
		return false;
	}
	FNavLocation Location;
	const FVector Extent(SearchExtentCm, SearchExtentCm, SearchExtentCm);
	if (NavSystem->ProjectPointToNavigation(Point, Location, Extent))
	{
		OutProjected = Location.Location;
		return true;
	}
	return false;
}

float UNYCNavigationSubsystem::WalkablePathLength(const FVector& From, const FVector& To) const
{
	UWorld* World = GetWorld();
	UNavigationSystemV1* NavSystem = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
	if (NavSystem == nullptr)
	{
		return -1.f;
	}
	double Length = 0.0;
	const ENavigationQueryResult::Type Result = NavSystem->GetPathLength(From, To, Length);
	return Result == ENavigationQueryResult::Success ? static_cast<float>(Length) : -1.f;
}

void UNYCNavigationSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	ConfigureRecast();
	EnsureBoundsVolume();

	const APlayerController* PlayerController = World->GetFirstPlayerController();
	if (PlayerController == nullptr)
	{
		return;
	}
	FVector ViewLocation;
	FRotator ViewRotation;
	PlayerController->GetPlayerViewPoint(ViewLocation, ViewRotation);

	const float Threshold = BoundsHalfSizeMetres * kCmPerMetre * RecentreFraction;
	if (!bBoundsPlaced || FVector::Dist2D(ViewLocation, BoundsCentre) > Threshold)
	{
		MoveBoundsTo(FVector(ViewLocation.X, ViewLocation.Y, ViewLocation.Z));
	}

	SweepTimer += DeltaTime;
	if (SweepTimer >= TagSweepSeconds)
	{
		SweepTimer = 0.f;
		ApplyNavAreasToTaggedActors();
	}
}
