#include "Vehicle/NYCPlayerVehicle.h"

#include "Audio/NYCVehicleAudioComponent.h"
#include "CoreAdapter/GameplayVehicleDynamics.h"
#include "Camera/CameraComponent.h"
#include "CineCameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Player/NYCInputConfig.h"
#include "Traffic/NYCTrafficSubsystem.h"
#include "UI/NYCGpsSubsystem.h"
#include "Vehicle/NYCVehicleAnimInstance.h"
#include "Vehicle/NYCVehicleBodyComponent.h"
#include "Vehicle/NYCVehicleContract.h"
#include "Vehicle/NYCVehicleDamageComponent.h"
#include "Vehicle/NYCVehicleDashboardComponent.h"
#include "Vehicle/NYCVehicleLightsComponent.h"
#include "Vehicle/NYCVehicleMirrorComponent.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

namespace
{
constexpr float kCmPerMetre = 100.f;
}

ANYCPlayerVehicle::ANYCPlayerVehicle(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UNYCVehicleMovementComponent>(
		  AWheeledVehiclePawn::VehicleMovementComponentName))
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;

	NYCMovement = Cast<UNYCVehicleMovementComponent>(GetVehicleMovementComponent());

	USkeletalMeshComponent* MeshComponent = GetMesh();
	if (MeshComponent != nullptr)
	{
		MeshComponent->SetCollisionProfileName(FName(TEXT("Vehicle")));
		MeshComponent->BodyInstance.bSimulatePhysics = true;
		MeshComponent->BodyInstance.bNotifyRigidBodyCollision = true;
		MeshComponent->SetGenerateOverlapEvents(true);
		MeshComponent->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		MeshComponent->SetAnimInstanceClass(UNYCVehicleAnimInstance::StaticClass());
	}

	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraArm"));
	SpringArm->SetupAttachment(MeshComponent);
	SpringArm->TargetArmLength = 360.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);
	Camera->bUsePawnControlRotation = false;

	CineCamera = CreateDefaultSubobject<UCineCameraComponent>(TEXT("CineCamera"));
	CineCamera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);
	CineCamera->SetActive(false);

	CameraRig = CreateDefaultSubobject<UNYCCameraRigComponent>(TEXT("CameraRig"));
	Lights = CreateDefaultSubobject<UNYCVehicleLightsComponent>(TEXT("Lights"));
	Dashboard = CreateDefaultSubobject<UNYCVehicleDashboardComponent>(TEXT("Dashboard"));
	Body = CreateDefaultSubobject<UNYCVehicleBodyComponent>(TEXT("BodyControls"));
	Mirrors = CreateDefaultSubobject<UNYCVehicleMirrorComponent>(TEXT("Mirrors"));
	Damage = CreateDefaultSubobject<UNYCVehicleDamageComponent>(TEXT("Damage"));
	VehicleAudio = CreateDefaultSubobject<UNYCVehicleAudioComponent>(TEXT("VehicleAudio"));
}

void ANYCPlayerVehicle::ApplyMeshAndContract()
{
	USkeletalMeshComponent* MeshComponent = GetMesh();
	if (MeshComponent == nullptr)
	{
		return;
	}

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	PlateNumber = Settings.PlayerPlateNumber;

	if (MeshComponent->GetSkeletalMeshAsset() == nullptr && !Settings.PlayerVehicleMesh.IsNull())
	{
		if (USkeletalMesh* Loaded = Cast<USkeletalMesh>(Settings.PlayerVehicleMesh.TryLoad()))
		{
			MeshComponent->SetSkeletalMesh(Loaded);
		}
		else
		{
			UE_LOG(LogNYCSim, Error,
				   TEXT("Player vehicle: '%s' could not be loaded. The pawn drives as an invisible physics body "
						"until the vehicle import stage has run."),
				   *Settings.PlayerVehicleMesh.ToString());
		}
	}

	const FNYCVehicleContractReport Report = FNYCVehicleContract::Validate(MeshComponent);
	if (Report.IsComplete())
	{
		UE_LOG(LogNYCSim, Log, TEXT("Player vehicle mesh satisfies the contract: %s"), *Report.ToText());
	}
	else
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Player vehicle mesh does not satisfy the contract: %s"), *Report.ToText());
	}

	// Paint colour and plate: both are material parameters on named slots.
	const int32 PaintIndex = FNYCVehicleContract::SlotIndex(MeshComponent, FName(NYCVehicleSlots::BodyPaint));
	if (PaintIndex != INDEX_NONE)
	{
		if (UMaterialInstanceDynamic* Paint = MeshComponent->CreateDynamicMaterialInstance(PaintIndex))
		{
			Paint->SetVectorParameterValue(FName(NYCVehicleParams::PaintColor), Settings.PlayerPaintColor);
		}
	}
}

void ANYCPlayerVehicle::BeginPlay()
{
	Super::BeginPlay();

	ApplyMeshAndContract();

	USkeletalMeshComponent* MeshComponent = GetMesh();
	NYCMovement = Cast<UNYCVehicleMovementComponent>(GetVehicleMovementComponent());

	if (Lights != nullptr)
	{
		Lights->Initialise(MeshComponent, /*bSpawnRealLights*/ true);
	}
	if (Dashboard != nullptr)
	{
		Dashboard->Initialise(MeshComponent, NYCMovement);
	}
	if (Body != nullptr)
	{
		Body->Initialise(MeshComponent);
	}
	if (Mirrors != nullptr)
	{
		Mirrors->Initialise(MeshComponent);
	}
	if (Damage != nullptr)
	{
		Damage->Initialise(MeshComponent, Lights, NYCMovement);
	}
	if (CameraRig != nullptr)
	{
		CameraRig->Initialise(MeshComponent, SpringArm, Camera, CineCamera, NYCMovement);
	}
	if (VehicleAudio != nullptr)
	{
		VehicleAudio->Initialise(MeshComponent, NYCMovement, Body, Lights);
	}
	if (NYCMovement != nullptr)
	{
		NYCMovement->SetIgnition(true);
	}
	if (Body != nullptr && VehicleAudio != nullptr)
	{
		// The horn and wiper events go straight to the audio component.
		Body->OnHornChanged.AddDynamic(VehicleAudio, &UNYCVehicleAudioComponent::HandleHorn);
		Body->OnWiperSweep.AddDynamic(VehicleAudio, &UNYCVehicleAudioComponent::HandleWiperSweep);
	}
	if (Lights != nullptr && VehicleAudio != nullptr)
	{
		Lights->OnRelayClick.AddDynamic(VehicleAudio, &UNYCVehicleAudioComponent::HandleIndicatorRelay);
	}
	if (Damage != nullptr && VehicleAudio != nullptr)
	{
		Damage->OnImpact.AddDynamic(VehicleAudio, &UNYCVehicleAudioComponent::HandleImpact);
	}

	PublishObserverToTraffic();

	if (Dashboard != nullptr)
	{
		// The centre screen shows the GPS; the widget class comes from the GPS subsystem so the same widget is
		// used on the screen and on the HUD.
		if (UWorld* World = GetWorld())
		{
			if (UNYCGpsSubsystem* Gps = World->GetSubsystem<UNYCGpsSubsystem>())
			{
				Dashboard->CreateCentreScreen(Gps->GetScreenWidgetClass());
			}
		}
	}
}

void ANYCPlayerVehicle::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	if (const APlayerController* PlayerController = Cast<APlayerController>(NewController))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Input =
				ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PlayerController->GetLocalPlayer()))
		{
			UNYCInputConfig* Config = UNYCInputConfig::Get(this);
			Input->RemoveMappingContext(Config->GetOnFootContext());
			Input->AddMappingContext(Config->GetDrivingContext(), 0);
			Input->AddMappingContext(Config->GetCommonContext(), 10);
		}
	}
	SetDriverPresent(true);
}

void ANYCPlayerVehicle::UnPossessed()
{
	if (const APlayerController* PlayerController = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Input =
				ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PlayerController->GetLocalPlayer()))
		{
			Input->RemoveMappingContext(UNYCInputConfig::Get(this)->GetDrivingContext());
		}
	}
	Super::UnPossessed();
}

void ANYCPlayerVehicle::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (Input == nullptr)
	{
		UE_LOG(LogNYCSim, Error,
			   TEXT("Player vehicle: the input component is not an EnhancedInputComponent. Check "
					"DefaultInputComponentClass in Config/DefaultInput.ini."));
		return;
	}

	UNYCInputConfig* Config = UNYCInputConfig::Get(this);
	auto Bind = [&](ENYCInputAction Action, ETriggerEvent Event, void (ANYCPlayerVehicle::*Handler)(const FInputActionValue&)) {
		if (UInputAction* InputAction = Config->GetAction(Action))
		{
			Input->BindAction(InputAction, Event, this, Handler);
		}
	};

	Bind(ENYCInputAction::Throttle, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnThrottle);
	Bind(ENYCInputAction::Throttle, ETriggerEvent::Completed, &ANYCPlayerVehicle::OnThrottle);
	Bind(ENYCInputAction::Brake, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnBrake);
	Bind(ENYCInputAction::Brake, ETriggerEvent::Completed, &ANYCPlayerVehicle::OnBrake);
	Bind(ENYCInputAction::Steer, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnSteer);
	Bind(ENYCInputAction::Steer, ETriggerEvent::Completed, &ANYCPlayerVehicle::OnSteer);
	Bind(ENYCInputAction::Handbrake, ETriggerEvent::Started, &ANYCPlayerVehicle::OnHandbrakeStart);
	Bind(ENYCInputAction::Handbrake, ETriggerEvent::Completed, &ANYCPlayerVehicle::OnHandbrakeStop);
	Bind(ENYCInputAction::ToggleReverse, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnToggleReverse);
	Bind(ENYCInputAction::Horn, ETriggerEvent::Started, &ANYCPlayerVehicle::OnHornStart);
	Bind(ENYCInputAction::Horn, ETriggerEvent::Completed, &ANYCPlayerVehicle::OnHornStop);
	Bind(ENYCInputAction::CycleHeadlights, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnCycleHeadlights);
	Bind(ENYCInputAction::ToggleFogLights, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnToggleFogLights);
	Bind(ENYCInputAction::IndicateLeft, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnIndicateLeft);
	Bind(ENYCInputAction::IndicateRight, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnIndicateRight);
	Bind(ENYCInputAction::ToggleHazards, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnToggleHazards);
	Bind(ENYCInputAction::CycleWipers, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnCycleWipers);
	Bind(ENYCInputAction::WindowDown, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnWindowDown);
	Bind(ENYCInputAction::WindowUp, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnWindowUp);
	Bind(ENYCInputAction::CycleCamera, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnCycleCamera);
	Bind(ENYCInputAction::PhotoMode, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnPhotoMode);
	Bind(ENYCInputAction::LookAround, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnLookAround);
	Bind(ENYCInputAction::RadioNext, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnRadioNext);
	Bind(ENYCInputAction::RadioPrevious, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnRadioPrevious);
	Bind(ENYCInputAction::ExitVehicle, ETriggerEvent::Triggered, &ANYCPlayerVehicle::OnExitVehicle);
}

// ------------------------------------------------------------------------------------------- input handlers

void ANYCPlayerVehicle::OnThrottle(const FInputActionValue& Value)
{
	Throttle = FMath::Clamp(Value.Get<float>(), 0.f, 1.f);
}

void ANYCPlayerVehicle::OnBrake(const FInputActionValue& Value)
{
	BrakeInput = FMath::Clamp(Value.Get<float>(), 0.f, 1.f);
}

void ANYCPlayerVehicle::OnSteer(const FInputActionValue& Value)
{
	SteerInput = FMath::Clamp(Value.Get<float>(), -1.f, 1.f);
}

void ANYCPlayerVehicle::OnHandbrakeStart(const FInputActionValue&)
{
	HandbrakeInput = 1.f;
}

void ANYCPlayerVehicle::OnHandbrakeStop(const FInputActionValue&)
{
	HandbrakeInput = 0.f;
}

void ANYCPlayerVehicle::OnToggleReverse(const FInputActionValue&)
{
	if (NYCMovement == nullptr)
	{
		return;
	}
	// The selector only moves when the car is nearly stopped, as the real transmission interlock requires.
	if (NYCMovement->GetSpeedKph() > 3.f)
	{
		return;
	}
	bReverseSelected = !bReverseSelected;
	NYCMovement->SetTargetGear(bReverseSelected ? -1 : 1, /*bImmediate*/ true);
}

void ANYCPlayerVehicle::OnHornStart(const FInputActionValue&)
{
	if (Body != nullptr)
	{
		Body->SetHorn(true);
	}
}

void ANYCPlayerVehicle::OnHornStop(const FInputActionValue&)
{
	if (Body != nullptr)
	{
		Body->SetHorn(false);
	}
}

void ANYCPlayerVehicle::OnCycleHeadlights(const FInputActionValue&)
{
	if (Lights != nullptr)
	{
		Lights->CycleHeadlights();
	}
}

void ANYCPlayerVehicle::OnToggleFogLights(const FInputActionValue&)
{
	if (Lights != nullptr)
	{
		bFogLightsOn = !bFogLightsOn;  // the switch is a latching push-button on this car
		Lights->SetFogLights(bFogLightsOn);
	}
}

void ANYCPlayerVehicle::OnIndicateLeft(const FInputActionValue&)
{
	if (Lights != nullptr)
	{
		Lights->SetTurnSignal(Lights->GetTurnSignal() == ENYCTurnSignal::Left ? ENYCTurnSignal::None
																			 : ENYCTurnSignal::Left);
	}
}

void ANYCPlayerVehicle::OnIndicateRight(const FInputActionValue&)
{
	if (Lights != nullptr)
	{
		Lights->SetTurnSignal(Lights->GetTurnSignal() == ENYCTurnSignal::Right ? ENYCTurnSignal::None
																			  : ENYCTurnSignal::Right);
	}
}

void ANYCPlayerVehicle::OnToggleHazards(const FInputActionValue&)
{
	if (Lights != nullptr)
	{
		Lights->ToggleHazards();
	}
}

void ANYCPlayerVehicle::OnCycleWipers(const FInputActionValue&)
{
	if (Body != nullptr)
	{
		Body->CycleWiperMode();
	}
}

void ANYCPlayerVehicle::OnWindowDown(const FInputActionValue&)
{
	if (Body != nullptr)
	{
		Body->NudgeWindow(0, +1.f);
	}
}

void ANYCPlayerVehicle::OnWindowUp(const FInputActionValue&)
{
	if (Body != nullptr)
	{
		Body->NudgeWindow(0, -1.f);
	}
}

void ANYCPlayerVehicle::OnCycleCamera(const FInputActionValue&)
{
	if (CameraRig != nullptr)
	{
		CameraRig->CycleMode();
	}
}

void ANYCPlayerVehicle::OnPhotoMode(const FInputActionValue&)
{
	if (CameraRig == nullptr)
	{
		return;
	}
	if (CameraRig->IsPhotoMode())
	{
		CameraRig->ExitPhotoMode();
	}
	else
	{
		CameraRig->EnterPhotoMode();
	}
}

void ANYCPlayerVehicle::OnLookAround(const FInputActionValue& Value)
{
	if (CameraRig != nullptr)
	{
		const FVector2D Axis = Value.Get<FVector2D>();
		CameraRig->AddLookInput(Axis.X, -Axis.Y);
	}
}

void ANYCPlayerVehicle::OnRadioNext(const FInputActionValue&)
{
	if (VehicleAudio != nullptr)
	{
		VehicleAudio->NextRadioStation();
	}
}

void ANYCPlayerVehicle::OnRadioPrevious(const FInputActionValue&)
{
	if (VehicleAudio != nullptr)
	{
		VehicleAudio->PreviousRadioStation();
	}
}

void ANYCPlayerVehicle::OnExitVehicle(const FInputActionValue&)
{
	// The character owns the enter/exit sequence; the vehicle only publishes that the driver wants out.
	OnExitRequested.Broadcast();
}

// ------------------------------------------------------------------------------------------------- runtime

FTransform ANYCPlayerVehicle::GetDriverSeatTransform() const
{
	const USkeletalMeshComponent* MeshComponent = GetMesh();
	const FName Socket(NYCVehicleBones::SocketDriverSeat);
	if (MeshComponent != nullptr && MeshComponent->DoesSocketExist(Socket))
	{
		return MeshComponent->GetSocketTransform(Socket);
	}
	return GetActorTransform();
}

FTransform ANYCPlayerVehicle::GetDriverEntryTransform() const
{
	const USkeletalMeshComponent* MeshComponent = GetMesh();
	const FName Socket(NYCVehicleBones::SocketDriverEntry);
	if (MeshComponent != nullptr && MeshComponent->DoesSocketExist(Socket))
	{
		return MeshComponent->GetSocketTransform(Socket);
	}
	// Fall back to a point one metre to the left of the driver's seat at ground level.
	FTransform Seat = GetDriverSeatTransform();
	Seat.AddToTranslation(Seat.GetRotation().GetRightVector() * -110.f);
	Seat.SetLocation(FVector(Seat.GetLocation().X, Seat.GetLocation().Y, GetActorLocation().Z));
	return Seat;
}

void ANYCPlayerVehicle::SetDriverDoorOpen(bool bOpen)
{
	if (Body != nullptr)
	{
		Body->SetDoorOpen(0, bOpen);
	}
}

void ANYCPlayerVehicle::SetDriverPresent(bool bPresent)
{
	bDriverPresent = bPresent;
	if (!bPresent)
	{
		Throttle = 0.f;
		BrakeInput = 0.f;
		SteerInput = 0.f;
		HandbrakeInput = 1.f;  // the handbrake goes on when the driver gets out
	}
	if (Lights != nullptr)
	{
		Lights->SetInteriorLight(!bPresent);
	}
}

void ANYCPlayerVehicle::UpdateWeatherCoupling(float DeltaTime)
{
	WeatherSampleTimer += DeltaTime;
	if (WeatherSampleTimer < 0.5f)
	{
		return;
	}
	WeatherSampleTimer = 0.f;

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	UMaterialParameterCollection* Collection =
		Cast<UMaterialParameterCollection>(Settings.WeatherParameterCollection.TryLoad());
	if (Collection == nullptr || GetWorld() == nullptr)
	{
		return;
	}
	bool bHasRain = false;
	for (const FCollectionScalarParameter& Param : Collection->ScalarParameters)
	{
		if (Param.ParameterName == Settings.WeatherRainRateParameter)
		{
			bHasRain = true;
			break;
		}
	}
	if (bHasRain && Body != nullptr)
	{
		const float RainRate =
			UKismetMaterialLibrary::GetScalarParameterValue(GetWorld(), Collection, Settings.WeatherRainRateParameter);
		Body->SetRainRate(FMath::Max(0.f, RainRate));
	}
}

void ANYCPlayerVehicle::UpdateLightsFromState(float DeltaTime)
{
	if (Lights == nullptr || NYCMovement == nullptr)
	{
		return;
	}
	const float Speed = NYCMovement->GetForwardSpeed();
	Lights->SetBrake(BrakeInput > 0.05f || HandbrakeInput > 0.5f);
	Lights->SetReverse(bReverseSelected && Speed < -5.f);
	Lights->UpdateSelfCancel(SteerInput, DeltaTime);

	// The dash lights up with the marker lights, as the real dimmer circuit does.
	const float Backlight = Lights->AreHeadlightsOn() || Lights->GetHeadlightMode() == ENYCHeadlightMode::DaytimeRunning
								? 0.85f
								: 0.f;
	Lights->SetDashBrightness(Backlight);
	if (Dashboard != nullptr)
	{
		Dashboard->SetBacklight(Backlight);
		int32 Mask = Dashboard->GetWarningLamps();
		Mask &= ~(static_cast<int32>(ENYCWarningLamp::DoorAjar) | static_cast<int32>(ENYCWarningLamp::Headlights) |
				  static_cast<int32>(ENYCWarningLamp::HighBeam) | static_cast<int32>(ENYCWarningLamp::TurnLeft) |
				  static_cast<int32>(ENYCWarningLamp::TurnRight));
		if (Body != nullptr && Body->IsAnyDoorAjar())
		{
			Mask |= static_cast<int32>(ENYCWarningLamp::DoorAjar);
		}
		if (Lights->AreHeadlightsOn())
		{
			Mask |= static_cast<int32>(ENYCWarningLamp::Headlights);
		}
		if (Lights->GetHeadlightMode() == ENYCHeadlightMode::High)
		{
			Mask |= static_cast<int32>(ENYCWarningLamp::HighBeam);
		}
		if (Lights->GetTurnSignal() == ENYCTurnSignal::Left || Lights->GetTurnSignal() == ENYCTurnSignal::Hazard)
		{
			Mask |= static_cast<int32>(ENYCWarningLamp::TurnLeft);
		}
		if (Lights->GetTurnSignal() == ENYCTurnSignal::Right || Lights->GetTurnSignal() == ENYCTurnSignal::Hazard)
		{
			Mask |= static_cast<int32>(ENYCWarningLamp::TurnRight);
		}
		Dashboard->SetWarningLamps(Mask);
	}
}

void ANYCPlayerVehicle::PushWheelAnimState(float DeltaTime)
{
	USkeletalMeshComponent* MeshComponent = GetMesh();
	if (MeshComponent == nullptr || NYCMovement == nullptr)
	{
		return;
	}
	UNYCVehicleAnimInstance* Anim = Cast<UNYCVehicleAnimInstance>(MeshComponent->GetAnimInstance());
	if (Anim == nullptr)
	{
		return;
	}

	const nycsim_gameplay::PlayerVehicleSpec Spec;
	const float WheelCircumference = 2.f * PI * Spec.wheelRadiusM() * kCmPerMetre;
	const float SpeedCm = NYCMovement->GetForwardSpeed();
	const float DegPerSecond = WheelCircumference > 1.f ? (SpeedCm / WheelCircumference) * 360.f : 0.f;

	FNYCVehicleAnimState& State = Anim->AnimState;
	for (int32 i = 0; i < 4; ++i)
	{
		WheelSpinDeg[i] = FMath::Fmod(WheelSpinDeg[i] + DegPerSecond * DeltaTime, 360.f);
		State.WheelSpinDeg[i] = WheelSpinDeg[i];
		State.WheelSteerDeg[i] = i < 2 ? SteerInput * Spec.maxSteerAngleDeg : 0.f;
		const FNYCWheelSurface& Surface = NYCMovement->GetWheelSurface(i);
		// Suspension displacement from the contact point relative to the wheel bone's rest height.
		if (Surface.bInContact)
		{
			const FName Bone = FNYCVehicleContract::WheelBone(i);
			if (MeshComponent->GetBoneIndex(Bone) != INDEX_NONE)
			{
				const float BoneZ = static_cast<float>(MeshComponent->GetBoneLocation(Bone, EBoneSpaces::WorldSpace).Z);
				const float ContactZ = static_cast<float>(Surface.ContactPoint.Z);
				const float RestHeight = Spec.wheelRadiusM() * kCmPerMetre;
				State.WheelSuspensionCm[i] = FMath::Clamp(RestHeight - (BoneZ - ContactZ), -20.f, 20.f);
			}
		}
		else
		{
			State.WheelSuspensionCm[i] = FMath::FInterpTo(State.WheelSuspensionCm[i], 0.f, DeltaTime, 6.f);
		}
	}
	State.SteeringWheelDeg = NYCMovement->GetSteeringWheelAngleDeg();
}

void ANYCPlayerVehicle::PublishObserverToTraffic()
{
	// Registered once; the traffic subsystem pulls the observer transform itself every step.
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	if (UNYCTrafficSubsystem* Traffic = World->GetSubsystem<UNYCTrafficSubsystem>())
	{
		Traffic->SetPlayerVehicle(this);
	}
}

void ANYCPlayerVehicle::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UWorld* World = GetWorld())
	{
		if (UNYCTrafficSubsystem* Traffic = World->GetSubsystem<UNYCTrafficSubsystem>())
		{
			Traffic->SetPlayerVehicle(nullptr);
		}
	}
	Super::EndPlay(EndPlayReason);
}

void ANYCPlayerVehicle::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (DeltaTime <= 0.f)
	{
		return;
	}

	if (NYCMovement != nullptr)
	{
		NYCMovement->SetDriverInput(bDriverPresent ? Throttle : 0.f, BrakeInput, SteerInput, HandbrakeInput);
	}
	UpdateWeatherCoupling(DeltaTime);
	UpdateLightsFromState(DeltaTime);
	PushWheelAnimState(DeltaTime);

	if (Mirrors != nullptr && CameraRig != nullptr)
	{
		Mirrors->SetMirrorsActive(CameraRig->NeedsMirrors());
	}
}

void ANYCPlayerVehicle::NotifyHit(UPrimitiveComponent* MyComp, AActor* Other, UPrimitiveComponent* OtherComp,
								  bool bSelfMoved, FVector HitLocation, FVector HitNormal, FVector NormalImpulse,
								  const FHitResult& Hit)
{
	Super::NotifyHit(MyComp, Other, OtherComp, bSelfMoved, HitLocation, HitNormal, NormalImpulse, Hit);
	if (Damage == nullptr)
	{
		return;
	}
	float OtherMass = 0.f;
	if (OtherComp != nullptr && OtherComp->IsSimulatingPhysics())
	{
		OtherMass = OtherComp->GetMass();
	}
	Damage->ApplyImpact(HitLocation, NormalImpulse, OtherMass);
}
