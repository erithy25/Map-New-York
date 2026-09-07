// The get-in / get-out sequence.
//
// A real entry is five beats, and the component runs them as an explicit state machine so each one can be
// interrupted cleanly (the player walks away, the car drives off, the door is blocked):
//
//   1. Approach   — walk to SKT_DriverEntry beside the driver's door (steering, not teleporting).
//   2. OpenDoor   — play Door_Open, swing the door on the car.
//   3. Enter      — play Vehicle_Enter_L while the capsule is attached to SKT_DriverSeat and blended in.
//   4. Seated     — hide the character, possess the car, close the door.
//   ... and the exit is the same in reverse, with the character un-hidden at SKT_DriverEntry.
//
// The component owns the possession swap, so nothing else has to know that the player is two pawns.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NYCVehicleInteractionComponent.generated.h"

class ANYCPlayerCharacter;
class ANYCPlayerVehicle;

UENUM(BlueprintType)
enum class ENYCInteractionState : uint8
{
	Idle = 0,
	ApproachingVehicle,
	OpeningDoor,
	Entering,
	Seated,
	Exiting,
	ClosingDoor
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FNYCVehicleOccupancyChanged, ANYCPlayerVehicle*, Vehicle, bool,
											 bEntered);

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleInteractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleInteractionComponent();

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Enters the nearest vehicle, or starts getting out of the current one. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Interaction")
	bool TryInteract();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Interaction")
	bool TryEnterVehicle(ANYCPlayerVehicle* Vehicle);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Interaction")
	bool TryExitVehicle();

	UFUNCTION(BlueprintPure, Category = "NYCSim|Interaction")
	bool IsInVehicle() const { return State == ENYCInteractionState::Seated; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Interaction")
	bool IsBusy() const { return State != ENYCInteractionState::Idle && State != ENYCInteractionState::Seated; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Interaction")
	ENYCInteractionState GetState() const { return State; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Interaction")
	ANYCPlayerVehicle* GetCurrentVehicle() const { return CurrentVehicle.Get(); }

	/** Steering input of the car the character is driving, for the seated animation. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Interaction")
	float GetVehicleSteer() const;

	/** The nearest vehicle the character could get into right now (for the "press F" prompt). */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Interaction")
	ANYCPlayerVehicle* FindNearbyVehicle() const;

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Interaction")
	FNYCVehicleOccupancyChanged OnOccupancyChanged;

	/** Bound to ANYCPlayerVehicle::OnExitRequested while seated. */
	UFUNCTION()
	void HandleExitRequested();

	/** Radius within which the "get in" prompt appears, metres. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Interaction", meta = (ClampMin = "0.5"))
	float InteractRangeMetres = 4.5f;

	/** How close the character must get to the entry point before the door opens, centimetres. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Interaction", meta = (ClampMin = "10.0"))
	float EntryToleranceCm = 55.f;

	/** Seconds the door takes to swing before the entry animation starts. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Interaction", meta = (ClampMin = "0.0"))
	float DoorOpenSeconds = 0.55f;

	/** Length of the entry / exit animation when the clip is missing. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Interaction", meta = (ClampMin = "0.1"))
	float FallbackEntrySeconds = 1.4f;

	/** The approach gives up after this long (the car drove off, or the path is blocked). */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Interaction", meta = (ClampMin = "1.0"))
	float ApproachTimeoutSeconds = 8.f;

private:
	void EnterState(ENYCInteractionState NewState);
	void TickApproach(float DeltaTime);
	void TickEnter(float DeltaTime);
	void TickExit(float DeltaTime);
	void FinishEntry();
	void FinishExit();
	ANYCPlayerCharacter* GetCharacter() const;
	/** True when the driver's door is on the character's left (US left-hand drive: always the left door). */
	bool UseLeftDoor() const { return true; }

	UPROPERTY(Transient)
	TWeakObjectPtr<ANYCPlayerVehicle> CurrentVehicle;

	UPROPERTY(Transient)
	TWeakObjectPtr<ANYCPlayerVehicle> TargetVehicle;

	ENYCInteractionState State = ENYCInteractionState::Idle;
	float StateTime = 0.f;
	float SequenceLength = 0.f;
	FTransform SeatTransform;
	FTransform ExitTransform;
};
