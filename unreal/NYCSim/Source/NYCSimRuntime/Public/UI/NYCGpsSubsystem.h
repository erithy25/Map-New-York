// Satellite navigation: routing, turn-by-turn with real street names, ETA, and destination search.
//
// Everything routing-related comes from nycsim::routing::Router over the shared lane graph
// (UNYCRoadNetworkSubsystem), so the route the GPS draws is the same lane sequence the traffic AI would drive.
// The subsystem owns one Router (ALT with 8 landmarks, preprocessed once on a worker thread) and:
//
//   * snaps the player to a lane and reports the street they are on;
//   * routes to a destination and keeps the instruction list;
//   * advances the instruction as the player passes each manoeuvre, and re-routes when they leave the route by
//     more than OffRouteToleranceMetres;
//   * recomputes the ETA from the router's own cost model (which includes signal delay and congestion).
//
// Search covers every indexed destination: PLUTO/PAD addresses from runtime/pois.nycb, every street name in the
// graph, bus stops from runtime/transit.nycb, and landmarks when runtime/landmarks.nycb carries a point section.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "NYCGpsSubsystem.generated.h"

class UNYCRoadNetworkSubsystem;
class UUserWidget;

UENUM(BlueprintType)
enum class ENYCManoeuvre : uint8
{
	Depart = 0,
	Continue,
	TurnLeft,
	TurnRight,
	SlightLeft,
	SlightRight,
	SharpLeft,
	SharpRight,
	UTurn,
	Ramp,
	Bridge,
	Tunnel,
	Arrive
};

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCGpsInstruction
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	ENYCManoeuvre Manoeuvre = ENYCManoeuvre::Continue;

	/** Text as the router produced it, e.g. "Turn left onto 5 Ave". */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	FString Text;

	/** The street this manoeuvre leads onto. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	FString Street;

	/** Distance from the route start to this manoeuvre, metres. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	float CumulativeMetres = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	FVector WorldLocation = FVector::ZeroVector;
};

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCGpsSearchResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	FString Label;

	/** "Address", "Street", "Bus stop" or "Landmark". */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	FString Kind;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	FVector WorldLocation = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|GPS")
	float DistanceMetres = 0.f;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FNYCRouteChanged, bool, bHasRoute);

UCLASS()
class NYCSIMRUNTIME_API UNYCGpsSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	UNYCGpsSubsystem();

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** True once the router has finished its landmark preprocessing. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	bool IsReady() const { return bRouterReady; }

	UFUNCTION(BlueprintCallable, Category = "NYCSim|GPS")
	bool SetDestinationWorld(const FVector& WorldLocation);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|GPS")
	void ClearDestination();

	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	bool HasRoute() const { return bHasRoute; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	FVector GetDestination() const { return DestinationWorld; }

	/** Remaining distance along the route in metres. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	float GetRemainingMetres() const { return RemainingMetres; }

	/** Estimated time of arrival in seconds, from the router's cost model. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	float GetEtaSeconds() const { return EtaSeconds; }

	/** The manoeuvre coming up, and how far away it is. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	bool GetNextInstruction(FNYCGpsInstruction& OutInstruction, float& OutDistanceMetres) const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	TArray<FNYCGpsInstruction> GetInstructions() const { return Instructions; }

	/** The route as a world-space polyline (Unreal centimetres). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	const TArray<FVector>& GetRoutePolyline() const { return RoutePolyline; }

	/** Name of the street the player is currently on ("" when off the graph). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	FString GetCurrentStreet() const { return CurrentStreet; }

	/** Ranked destination search over addresses, street names, bus stops and landmarks. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|GPS")
	TArray<FNYCGpsSearchResult> Search(const FString& Query, int32 MaxResults = 12) const;

	/** Widget class the dashboard screen and the HUD both instantiate. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|GPS")
	TSubclassOf<UUserWidget> GetScreenWidgetClass() const;

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|GPS")
	FNYCRouteChanged OnRouteChanged;

	/** Distance from the route past which it is recomputed, metres. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|GPS", meta = (ClampMin = "5.0"))
	float OffRouteToleranceMetres = 28.f;

	/** Minimum seconds between two automatic re-routes. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|GPS", meta = (ClampMin = "0.5"))
	float RerouteCooldownSeconds = 3.f;

private:
	void StartRouterAsync();
	bool ComputeRoute(const FVector& FromWorld, const FVector& ToWorld);
	void UpdateProgress(const FVector& PlayerWorld);
	FVector GetPlayerWorldLocation() const;

	/** Opaque router state; defined in the .cpp so this header stays free of core includes. */
	TUniquePtr<struct FNYCGpsRouterState> RouterState;

	TArray<FNYCGpsInstruction> Instructions;
	TArray<FVector> RoutePolyline;
	FVector DestinationWorld = FVector::ZeroVector;
	FString CurrentStreet;
	float RemainingMetres = 0.f;
	float EtaSeconds = 0.f;
	float RerouteTimer = 0.f;
	int32 NextInstructionIndex = 0;
	bool bHasRoute = false;
	bool bRouterReady = false;
	bool bRouterStarting = false;
	TArray<FAutoConsoleCommandWithWorldArgsAndOutputDevice*> ConsoleCommands;
};
