#include "Character/NYCVehicleInteractionComponent.h"

#include "Character/NYCCharacterAnimInstance.h"
#include "Character/NYCPlayerCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "NYCSimRuntime.h"
#include "Vehicle/NYCPlayerVehicle.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

namespace
{
constexpr float kCmPerMetre = 100.f;
}

UNYCVehicleInteractionComponent::UNYCVehicleInteractionComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

void UNYCVehicleInteractionComponent::BeginPlay()
{
	Super::BeginPlay();
}

ANYCPlayerCharacter* UNYCVehicleInteractionComponent::GetCharacter() const
{
	return Cast<ANYCPlayerCharacter>(GetOwner());
}

float UNYCVehicleInteractionComponent::GetVehicleSteer() const
{
	const ANYCPlayerVehicle* Vehicle = CurrentVehicle.Get();
	if (Vehicle == nullptr || Vehicle->GetNYCMovement() == nullptr)
	{
		return 0.f;
	}
	return Vehicle->GetNYCMovement()->GetDriverSteer();
}

ANYCPlayerVehicle* UNYCVehicleInteractionComponent::FindNearbyVehicle() const
{
	const ANYCPlayerCharacter* Character = GetCharacter();
	UWorld* World = GetWorld();
	if (Character == nullptr || World == nullptr)
	{
		return nullptr;
	}
	const FVector Origin = Character->GetActorLocation();
	const float RangeSq = FMath::Square(InteractRangeMetres * kCmPerMetre);

	ANYCPlayerVehicle* Best = nullptr;
	float BestDistSq = RangeSq;
	for (TActorIterator<ANYCPlayerVehicle> It(World); It; ++It)
	{
		ANYCPlayerVehicle* Vehicle = *It;
		if (!IsValid(Vehicle))
		{
			continue;
		}
		const float DistSq = static_cast<float>(FVector::DistSquared(Origin, Vehicle->GetActorLocation()));
		if (DistSq < BestDistSq)
		{
			BestDistSq = DistSq;
			Best = Vehicle;
		}
	}
	return Best;
}

bool UNYCVehicleInteractionComponent::TryInteract()
{
	if (IsBusy())
	{
		return false;
	}
	if (IsInVehicle())
	{
		return TryExitVehicle();
	}
	return TryEnterVehicle(FindNearbyVehicle());
}

bool UNYCVehicleInteractionComponent::TryEnterVehicle(ANYCPlayerVehicle* Vehicle)
{
	if (Vehicle == nullptr || IsBusy() || IsInVehicle())
	{
		return false;
	}
	ANYCPlayerCharacter* Character = GetCharacter();
	if (Character == nullptr)
	{
		return false;
	}
	// A moving car cannot be entered; the door would be torn off.
	if (Vehicle->GetVelocity().Size() > 60.f)
	{
		UE_LOG(LogNYCSim, Verbose, TEXT("Interaction: the car is still moving; cannot enter."));
		return false;
	}
	TargetVehicle = Vehicle;
	EnterState(ENYCInteractionState::ApproachingVehicle);
	return true;
}

bool UNYCVehicleInteractionComponent::TryExitVehicle()
{
	ANYCPlayerVehicle* Vehicle = CurrentVehicle.Get();
	if (Vehicle == nullptr || !IsInVehicle())
	{
		return false;
	}
	if (Vehicle->GetNYCMovement() != nullptr && Vehicle->GetNYCMovement()->GetSpeedKph() > 4.f)
	{
		UE_LOG(LogNYCSim, Verbose, TEXT("Interaction: too fast to get out."));
		return false;
	}
	ExitTransform = Vehicle->GetDriverEntryTransform();
	Vehicle->SetDriverDoorOpen(true);
	EnterState(ENYCInteractionState::Exiting);
	return true;
}

void UNYCVehicleInteractionComponent::EnterState(ENYCInteractionState NewState)
{
	State = NewState;
	StateTime = 0.f;

	ANYCPlayerCharacter* Character = GetCharacter();
	UNYCCharacterAnimInstance* Anim = Character != nullptr ? Character->GetNYCAnimInstance() : nullptr;

	switch (State)
	{
	case ENYCInteractionState::OpeningDoor:
		if (ANYCPlayerVehicle* Vehicle = TargetVehicle.Get())
		{
			Vehicle->SetDriverDoorOpen(true);
		}
		if (Anim != nullptr)
		{
			Anim->RequestAction(ENYCCharacterAction::OpenDoor);
		}
		SequenceLength = DoorOpenSeconds;
		break;

	case ENYCInteractionState::Entering:
		if (Anim != nullptr)
		{
			Anim->RequestAction(UseLeftDoor() ? ENYCCharacterAction::EnterVehicleLeft
											  : ENYCCharacterAction::EnterVehicleRight);
		}
		SequenceLength = FallbackEntrySeconds;
		if (const ANYCPlayerVehicle* Vehicle = TargetVehicle.Get())
		{
			SeatTransform = Vehicle->GetDriverSeatTransform();
		}
		if (Character != nullptr && Character->GetCharacterMovement() != nullptr)
		{
			// The capsule stops colliding while the body slides into the seat.
			Character->GetCharacterMovement()->StopMovementImmediately();
			Character->GetCharacterMovement()->SetMovementMode(MOVE_None);
			Character->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		}
		break;

	case ENYCInteractionState::Exiting:
		if (Anim != nullptr)
		{
			Anim->RequestAction(UseLeftDoor() ? ENYCCharacterAction::ExitVehicleLeft
											  : ENYCCharacterAction::ExitVehicleRight);
		}
		SequenceLength = FallbackEntrySeconds;
		break;

	case ENYCInteractionState::ClosingDoor:
		if (Anim != nullptr)
		{
			Anim->RequestAction(ENYCCharacterAction::CloseDoor);
		}
		SequenceLength = DoorOpenSeconds;
		break;

	default:
		SequenceLength = 0.f;
		break;
	}
}

void UNYCVehicleInteractionComponent::TickApproach(float DeltaTime)
{
	ANYCPlayerCharacter* Character = GetCharacter();
	ANYCPlayerVehicle* Vehicle = TargetVehicle.Get();
	if (Character == nullptr || Vehicle == nullptr)
	{
		EnterState(ENYCInteractionState::Idle);
		return;
	}
	if (StateTime > ApproachTimeoutSeconds)
	{
		UE_LOG(LogNYCSim, Verbose, TEXT("Interaction: approach timed out."));
		EnterState(ENYCInteractionState::Idle);
		return;
	}

	const FTransform Entry = Vehicle->GetDriverEntryTransform();
	const FVector ToEntry = Entry.GetLocation() - Character->GetActorLocation();
	const float Distance = static_cast<float>(ToEntry.Size2D());
	if (Distance <= EntryToleranceCm)
	{
		EnterState(ENYCInteractionState::OpeningDoor);
		return;
	}
	// Steer toward the door rather than teleporting: the locomotion machine keeps animating throughout.
	Character->AddMovementInput(ToEntry.GetSafeNormal2D(), FMath::Min(1.f, Distance / 200.f));
}

void UNYCVehicleInteractionComponent::TickEnter(float DeltaTime)
{
	ANYCPlayerCharacter* Character = GetCharacter();
	const ANYCPlayerVehicle* Vehicle = TargetVehicle.Get();
	if (Character == nullptr || Vehicle == nullptr)
	{
		EnterState(ENYCInteractionState::Idle);
		return;
	}
	// Slide the capsule into the seat over the clip's length; the entry animation carries the body.
	const float Alpha = FMath::Clamp(StateTime / FMath::Max(0.05f, SequenceLength), 0.f, 1.f);
	const FVector Target = SeatTransform.GetLocation();
	const FVector Current = FMath::Lerp(Character->GetActorLocation(), Target, FMath::Min(1.f, DeltaTime * 8.f));
	Character->SetActorLocation(Current);
	Character->SetActorRotation(
		FMath::RInterpTo(Character->GetActorRotation(), SeatTransform.Rotator(), DeltaTime, 6.f));

	if (Alpha >= 1.f)
	{
		FinishEntry();
	}
}

void UNYCVehicleInteractionComponent::TickExit(float DeltaTime)
{
	ANYCPlayerCharacter* Character = GetCharacter();
	if (Character == nullptr)
	{
		EnterState(ENYCInteractionState::Idle);
		return;
	}
	const float Alpha = FMath::Clamp(StateTime / FMath::Max(0.05f, SequenceLength), 0.f, 1.f);
	Character->SetActorLocation(FMath::Lerp(Character->GetActorLocation(), ExitTransform.GetLocation(),
											FMath::Min(1.f, DeltaTime * 6.f)));
	if (Alpha >= 1.f)
	{
		FinishExit();
	}
}

void UNYCVehicleInteractionComponent::FinishEntry()
{
	ANYCPlayerCharacter* Character = GetCharacter();
	ANYCPlayerVehicle* Vehicle = TargetVehicle.Get();
	if (Character == nullptr || Vehicle == nullptr)
	{
		EnterState(ENYCInteractionState::Idle);
		return;
	}

	AController* Controller = Character->GetController();
	CurrentVehicle = Vehicle;

	// Park the character in the seat, hide it and hand control to the car.
	Character->SetActorEnableCollision(false);
	Character->GetMesh()->SetVisibility(false, true);
	Character->AttachToActor(Vehicle, FAttachmentTransformRules::KeepWorldTransform);
	Vehicle->SetDriverDoorOpen(false);
	Vehicle->SetDriverPresent(true);
	Vehicle->OnExitRequested.AddDynamic(this, &UNYCVehicleInteractionComponent::HandleExitRequested);

	if (APlayerController* PlayerController = Cast<APlayerController>(Controller))
	{
		PlayerController->Possess(Vehicle);
	}

	State = ENYCInteractionState::Seated;
	StateTime = 0.f;
	OnOccupancyChanged.Broadcast(Vehicle, /*bEntered*/ true);
	UE_LOG(LogNYCSim, Log, TEXT("Interaction: seated in %s."), *Vehicle->GetName());
}

void UNYCVehicleInteractionComponent::FinishExit()
{
	ANYCPlayerCharacter* Character = GetCharacter();
	ANYCPlayerVehicle* Vehicle = CurrentVehicle.Get();
	if (Character == nullptr)
	{
		EnterState(ENYCInteractionState::Idle);
		return;
	}

	Character->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	Character->SetActorLocationAndRotation(ExitTransform.GetLocation(), ExitTransform.Rotator());
	Character->SetActorEnableCollision(true);
	Character->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Character->GetMesh()->SetVisibility(true, true);
	if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
	{
		Movement->SetMovementMode(MOVE_Walking);
	}

	if (Vehicle != nullptr)
	{
		Vehicle->SetDriverPresent(false);
		Vehicle->OnExitRequested.RemoveDynamic(this, &UNYCVehicleInteractionComponent::HandleExitRequested);
		if (APlayerController* PlayerController = Cast<APlayerController>(Vehicle->GetController()))
		{
			PlayerController->Possess(Character);
		}
	}

	OnOccupancyChanged.Broadcast(Vehicle, /*bEntered*/ false);
	CurrentVehicle = nullptr;
	TargetVehicle = nullptr;
	EnterState(ENYCInteractionState::ClosingDoor);
	if (Vehicle != nullptr)
	{
		Vehicle->SetDriverDoorOpen(false);
	}
	UE_LOG(LogNYCSim, Log, TEXT("Interaction: out of the car."));
}

void UNYCVehicleInteractionComponent::HandleExitRequested()
{
	TryExitVehicle();
}

void UNYCVehicleInteractionComponent::TickComponent(float DeltaTime, ELevelTick TickType,
													FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	StateTime += DeltaTime;

	switch (State)
	{
	case ENYCInteractionState::ApproachingVehicle:
		TickApproach(DeltaTime);
		break;
	case ENYCInteractionState::OpeningDoor:
		if (StateTime >= SequenceLength)
		{
			EnterState(ENYCInteractionState::Entering);
		}
		break;
	case ENYCInteractionState::Entering:
		TickEnter(DeltaTime);
		break;
	case ENYCInteractionState::Exiting:
		TickExit(DeltaTime);
		break;
	case ENYCInteractionState::ClosingDoor:
		if (StateTime >= SequenceLength)
		{
			EnterState(ENYCInteractionState::Idle);
		}
		break;
	default:
		break;
	}
}
