// Runtime navigation over the walkable city: sidewalks, plazas, parks and bridge walkways.
//
// The city is streamed, so the navmesh cannot be built offline for 1,480 tiles. Instead this subsystem keeps a
// navigation bounds volume centred on the player (a 900 m box by default, the same radius as the L0 streaming
// ring) and lets Recast generate dynamically inside it. As the player moves more than a quarter of the box, the
// volume is re-centred and the navigation system is told the bounds changed.
//
// Which surfaces are walkable is decided by ACTOR TAGS, which is the contract with the world/streaming lane:
//
//   NYCSidewalk        the pavement between the kerb and the building line   (preferred, cost 1)
//   NYCPlaza           pedestrian plazas (k5k6-6jex)                          (preferred, cost 1)
//   NYCPark            park paths and lawns (DPR open space)                  (cost 1.4: people cut across grass)
//   NYCBridgeWalkway   the walkways on the East River bridges                 (cost 1)
//   NYCRoadbed         the carriageway                                        (cost 6: crossed, not walked along)
//   NYCNotWalkable     anything the character must never stand on             (excluded)
//
// Actors carrying one of those tags get the matching nav area class and are made navigation-relevant as they
// stream in; anything untagged keeps the engine's default behaviour, so the system degrades to "walk on whatever
// has collision" rather than to "no navmesh".
#pragma once

#include "CoreMinimal.h"
#include "NavAreas/NavArea.h"
#include "Subsystems/WorldSubsystem.h"
#include "NYCNavigationSubsystem.generated.h"

class ANavMeshBoundsVolume;
class ARecastNavMesh;

/** Sidewalks, plazas and bridge walkways: the cheapest way to get anywhere on foot. */
UCLASS()
class NYCSIMRUNTIME_API UNYCNavArea_Sidewalk : public UNavArea
{
	GENERATED_BODY()

public:
	UNYCNavArea_Sidewalk();
};

/** Park paths and lawns: walkable, slightly discouraged versus a paved route. */
UCLASS()
class NYCSIMRUNTIME_API UNYCNavArea_Park : public UNavArea
{
	GENERATED_BODY()

public:
	UNYCNavArea_Park();
};

/** The carriageway: crossable but expensive, so a path prefers the sidewalk and the crossing. */
UCLASS()
class NYCSIMRUNTIME_API UNYCNavArea_Roadbed : public UNavArea
{
	GENERATED_BODY()

public:
	UNYCNavArea_Roadbed();
};

UCLASS()
class NYCSIMRUNTIME_API UNYCNavigationSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	UNYCNavigationSubsystem();

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** Applies the nav area classes to every tagged actor currently in the world. Call after a tile streams in. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Navigation")
	int32 ApplyNavAreasToTaggedActors();

	/** Projects a world point onto the navmesh; false when there is no navmesh within `SearchExtentCm`. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Navigation")
	bool ProjectToNavigation(const FVector& Point, FVector& OutProjected, float SearchExtentCm = 250.f) const;

	/** Straight-line walkable path length in centimetres, or -1 when no path exists. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Navigation")
	float WalkablePathLength(const FVector& From, const FVector& To) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Navigation")
	bool IsNavigationReady() const { return bBoundsPlaced; }

	/** Half-size of the moving navigation bounds volume, metres. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Navigation", meta = (ClampMin = "50.0"))
	float BoundsHalfSizeMetres = 450.f;

	/** Vertical half-size, metres: enough for a bridge deck over a river. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Navigation", meta = (ClampMin = "20.0"))
	float BoundsHalfHeightMetres = 260.f;

	/** Re-centres the volume once the player has moved this fraction of the box. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Navigation", meta = (ClampMin = "0.05", ClampMax = "0.9"))
	float RecentreFraction = 0.25f;

	/** Seconds between tag sweeps (a tile streaming in brings new tagged actors). */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Navigation", meta = (ClampMin = "0.5"))
	float TagSweepSeconds = 2.f;

private:
	void EnsureBoundsVolume();
	void MoveBoundsTo(const FVector& Centre);
	void ConfigureRecast();

	UPROPERTY(Transient)
	TObjectPtr<ANavMeshBoundsVolume> BoundsVolume;

	UPROPERTY(Transient)
	TSet<TWeakObjectPtr<AActor>> TaggedActors;

	FVector BoundsCentre = FVector::ZeroVector;
	float SweepTimer = 0.f;
	bool bBoundsPlaced = false;
	bool bRecastConfigured = false;
	int32 TaggedActorCount = 0;
};
