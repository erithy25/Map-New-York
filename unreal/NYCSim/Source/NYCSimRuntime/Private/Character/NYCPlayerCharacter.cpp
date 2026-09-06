#include "Character/NYCPlayerCharacter.h"

#include "Camera/CameraComponent.h"
#include "Character/NYCCharacterAnimInstance.h"
#include "Character/NYCCharacterContract.h"
#include "Character/NYCVehicleInteractionComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Player/NYCInputConfig.h"
#include "Traffic/NYCTrafficSubsystem.h"

namespace
{
constexpr float kCmPerMetre = 100.f;
}

ANYCPlayerCharacter::ANYCPlayerCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	PrimaryActorTick.bCanEverTick = true;

	// A 1.78 m adult: capsule half-height 88 cm, radius 34 cm (the value the navmesh agent uses too).
	UCapsuleComponent* Capsule = GetCapsuleComponent();
	Capsule->InitCapsuleSize(34.f, 88.f);

	USkeletalMeshComponent* MeshComponent = GetMesh();
	// The Mannequin's mesh origin is at the feet facing +Y, so it is offset down by the half-height and yawed.
	MeshComponent->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -88.f), FRotator(0.f, -90.f, 0.f));
	MeshComponent->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	MeshComponent->SetAnimInstanceClass(UNYCCharacterAnimInstance::StaticClass());
	MeshComponent->SetCollisionProfileName(FName(TEXT("CharacterMesh")));

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.f, 540.f, 0.f);
	Movement->MaxWalkSpeed = JogSpeedMps * kCmPerMetre;
	Movement->MaxWalkSpeedCrouched = CrouchSpeedMps * kCmPerMetre;
	Movement->JumpZVelocity = 420.f;
	Movement->AirControl = 0.25f;
	Movement->BrakingDecelerationWalking = 1400.f;
	Movement->GroundFriction = 8.f;
	Movement->MaxStepHeight = 30.f;      // a New York kerb is 15-20 cm; a stoop step is 18 cm
	Movement->SetWalkableFloorAngle(50.f);
	Movement->NavAgentProps.AgentRadius = 34.f;
	Movement->NavAgentProps.AgentHeight = 176.f;
	Movement->NavAgentProps.bCanCrouch = true;
	Movement->GetNavAgentPropertiesRef().bCanJump = true;

	bUseControllerRotationYaw = false;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 300.f;
	CameraBoom->SocketOffset = FVector(0.f, 45.f, 60.f);
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 12.f;

	ThirdPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ThirdPersonCamera"));
	ThirdPersonCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	ThirdPersonCamera->bUsePawnControlRotation = false;
	ThirdPersonCamera->SetFieldOfView(85.f);

	FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	FirstPersonCamera->SetupAttachment(MeshComponent, FName(NYCCharacterBones::Head));
	FirstPersonCamera->bUsePawnControlRotation = true;
	FirstPersonCamera->SetRelativeLocation(FVector(10.f, 0.f, 0.f));
	FirstPersonCamera->SetFieldOfView(95.f);
	FirstPersonCamera->SetActive(false);

	Interaction = CreateDefaultSubobject<UNYCVehicleInteractionComponent>(TEXT("VehicleInteraction"));
}

void ANYCPlayerCharacter::BeginPlay()
{
	Super::BeginPlay();

	USkeletalMeshComponent* MeshComponent = GetMesh();
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (MeshComponent != nullptr && MeshComponent->GetSkeletalMeshAsset() == nullptr &&
		!Settings.PlayerCharacterMesh.IsNull())
	{
		if (USkeletalMesh* Loaded = Cast<USkeletalMesh>(Settings.PlayerCharacterMesh.TryLoad()))
		{
			MeshComponent->SetSkeletalMesh(Loaded);
		}
		else
		{
			UE_LOG(LogNYCSim, Error,
				   TEXT("Player character: '%s' could not be loaded; the character walks invisibly until the "
						"character import stage has run."),
				   *Settings.PlayerCharacterMesh.ToString());
		}
	}

	const TArray<FName> Missing = FNYCCharacterContract::MissingBones(MeshComponent);
	if (Missing.Num() > 0)
	{
		TArray<FString> Names;
		for (const FName& Name : Missing)
		{
			Names.Add(Name.ToString());
		}
		UE_LOG(LogNYCSim, Warning, TEXT("Player character skeleton is missing %d contract bones: %s"), Missing.Num(),
			   *FString::Join(Names, TEXT(", ")));
	}

	if (UNYCCharacterAnimInstance* Anim = GetNYCAnimInstance())
	{
		Anim->ResolveClips();
	}
}

UNYCCharacterAnimInstance* ANYCPlayerCharacter::GetNYCAnimInstance() const
{
	const USkeletalMeshComponent* MeshComponent = GetMesh();
	return MeshComponent != nullptr ? Cast<UNYCCharacterAnimInstance>(MeshComponent->GetAnimInstance()) : nullptr;
}

void ANYCPlayerCharacter::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	if (const APlayerController* PlayerController = Cast<APlayerController>(NewController))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Input =
				ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PlayerController->GetLocalPlayer()))
		{
			UNYCInputConfig* Config = UNYCInputConfig::Get(this);
			Input->RemoveMappingContext(Config->GetDrivingContext());
			Input->AddMappingContext(Config->GetOnFootContext(), 0);
			Input->AddMappingContext(Config->GetCommonContext(), 10);
		}
	}
}

void ANYCPlayerCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (Input == nullptr)
	{
		return;
	}
	UNYCInputConfig* Config = UNYCInputConfig::Get(this);
	auto Bind = [&](ENYCInputAction Action, ETriggerEvent Event,
					void (ANYCPlayerCharacter::*Handler)(const FInputActionValue&)) {
		if (UInputAction* InputAction = Config->GetAction(Action))
		{
			Input->BindAction(InputAction, Event, this, Handler);
		}
	};

	Bind(ENYCInputAction::Move, ETriggerEvent::Triggered, &ANYCPlayerCharacter::OnMove);
	Bind(ENYCInputAction::Move, ETriggerEvent::Completed, &ANYCPlayerCharacter::OnMove);
	Bind(ENYCInputAction::LookAround, ETriggerEvent::Triggered, &ANYCPlayerCharacter::OnLook);
	Bind(ENYCInputAction::Jump, ETriggerEvent::Triggered, &ANYCPlayerCharacter::OnJumpPressed);
	Bind(ENYCInputAction::Sprint, ETriggerEvent::Started, &ANYCPlayerCharacter::OnSprintStart);
	Bind(ENYCInputAction::Sprint, ETriggerEvent::Completed, &ANYCPlayerCharacter::OnSprintStop);
	Bind(ENYCInputAction::Crouch, ETriggerEvent::Triggered, &ANYCPlayerCharacter::OnCrouchToggle);
	Bind(ENYCInputAction::Interact, ETriggerEvent::Triggered, &ANYCPlayerCharacter::OnInteract);
	Bind(ENYCInputAction::CycleCamera, ETriggerEvent::Triggered, &ANYCPlayerCharacter::OnCycleCamera);
}

void ANYCPlayerCharacter::OnMove(const FInputActionValue& Value)
{
	MoveInput = Value.Get<FVector2D>();
	if (Controller == nullptr)
	{
		return;
	}
	const FRotator YawOnly(0.f, Controller->GetControlRotation().Yaw, 0.f);
	const FVector Forward = FRotationMatrix(YawOnly).GetUnitAxis(EAxis::X);
	const FVector Right = FRotationMatrix(YawOnly).GetUnitAxis(EAxis::Y);
	AddMovementInput(Forward, MoveInput.Y);
	AddMovementInput(Right, MoveInput.X);
}

void ANYCPlayerCharacter::OnLook(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(-Axis.Y);
}

void ANYCPlayerCharacter::OnJumpPressed(const FInputActionValue&)
{
	Jump();
}

void ANYCPlayerCharacter::OnSprintStart(const FInputActionValue&)
{
	bSprinting = true;
}

void ANYCPlayerCharacter::OnSprintStop(const FInputActionValue&)
{
	bSprinting = false;
}

void ANYCPlayerCharacter::OnCrouchToggle(const FInputActionValue&)
{
	if (bIsCrouched)
	{
		UnCrouch();
	}
	else
	{
		Crouch();
	}
}

void ANYCPlayerCharacter::OnInteract(const FInputActionValue&)
{
	if (Interaction != nullptr)
	{
		Interaction->TryInteract();
	}
}

void ANYCPlayerCharacter::OnCycleCamera(const FInputActionValue&)
{
	SetFirstPerson(!bFirstPerson);
}

void ANYCPlayerCharacter::SetFirstPerson(bool bInFirstPerson)
{
	bFirstPerson = bInFirstPerson;
	if (ThirdPersonCamera != nullptr)
	{
		ThirdPersonCamera->SetActive(!bFirstPerson);
	}
	if (FirstPersonCamera != nullptr)
	{
		FirstPersonCamera->SetActive(bFirstPerson);
	}
	if (USkeletalMeshComponent* MeshComponent = GetMesh())
	{
		// In first person the head fills the frame; hiding just that bone keeps the body visible looking down.
		if (bFirstPerson)
		{
			MeshComponent->HideBoneByName(FName(NYCCharacterBones::Head), EPhysBodyOp::PBO_None);
		}
		else
		{
			MeshComponent->UnHideBoneByName(FName(NYCCharacterBones::Head));
		}
	}
	if (GetCharacterMovement() != nullptr)
	{
		GetCharacterMovement()->bOrientRotationToMovement = !bFirstPerson;
	}
	bUseControllerRotationYaw = bFirstPerson;
}

void ANYCPlayerCharacter::Landed(const FHitResult& Hit)
{
	LastVerticalSpeedMps = static_cast<float>(GetVelocity().Z) / kCmPerMetre;
	Super::Landed(Hit);
}

void ANYCPlayerCharacter::UpdateLocomotionInput(float DeltaTime)
{
	UNYCCharacterAnimInstance* Anim = GetNYCAnimInstance();
	if (Anim == nullptr)
	{
		return;
	}
	const FVector Velocity = GetVelocity();
	const float SpeedMps = static_cast<float>(Velocity.Size2D()) / kCmPerMetre;

	FNYCLocomotionInput Input;
	Input.SpeedMps = SpeedMps;
	if (SpeedMps > 0.05f)
	{
		const FVector Forward = GetActorForwardVector();
		const FVector Direction = Velocity.GetSafeNormal2D();
		const float Dot = FVector::DotProduct(Forward, Direction);
		const float Cross = FVector::CrossProduct(Forward, Direction).Z;
		Input.MovementAngleDeg = FMath::RadiansToDegrees(FMath::Atan2(Cross, Dot));
	}
	if (Controller != nullptr)
	{
		Input.YawErrorDeg =
			FRotator::NormalizeAxis(Controller->GetControlRotation().Yaw - GetActorRotation().Yaw);
		Input.AimPitchDeg = FRotator::NormalizeAxis(Controller->GetControlRotation().Pitch);
	}
	Input.bInAir = GetCharacterMovement() != nullptr && GetCharacterMovement()->IsFalling();
	Input.bCrouched = bIsCrouched;
	Input.bSprinting = bSprinting;
	Input.bInVehicle = Interaction != nullptr && Interaction->IsInVehicle();
	Input.VerticalSpeedMps = Input.bInAir ? static_cast<float>(Velocity.Z) / kCmPerMetre : LastVerticalSpeedMps;
	if (Interaction != nullptr)
	{
		Input.VehicleSteer = Interaction->GetVehicleSteer();
	}
	Anim->SetLocomotionInput(Input);

	// The movement component's speed cap follows the gait so the animation and the physics agree.
	if (UCharacterMovementComponent* Movement = GetCharacterMovement())
	{
		const float Target = bSprinting ? SprintSpeedMps : (MoveInput.SizeSquared() > 0.6f ? JogSpeedMps : WalkSpeedMps);
		Movement->MaxWalkSpeed = FMath::FInterpTo(Movement->MaxWalkSpeed, Target * kCmPerMetre, DeltaTime, 6.f);
	}
}

void ANYCPlayerCharacter::PublishObserver()
{
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	if (UNYCTrafficSubsystem* Traffic = World->GetSubsystem<UNYCTrafficSubsystem>())
	{
		if (Interaction == nullptr || !Interaction->IsInVehicle())
		{
			Traffic->SetObserverTransform(GetActorLocation(), GetActorForwardVector(),
										  static_cast<float>(GetVelocity().Size()) / kCmPerMetre);
		}
	}
}

void ANYCPlayerCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UpdateLocomotionInput(DeltaTime);
	PublishObserver();
}
