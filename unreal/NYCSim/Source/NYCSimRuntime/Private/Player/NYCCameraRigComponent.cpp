#include "Player/NYCCameraRigComponent.h"

#include "Camera/CameraComponent.h"
#include "CineCameraComponent.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"
#include "NYCSimRuntime.h"
#include "Vehicle/NYCVehicleContract.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

namespace
{
constexpr float kCmPerMetre = 100.f;

/// A short, deterministic multi-frequency shake so cobblestones do not read as a sine wave.
float ShakeSignal(float Phase, float Seed)
{
	return 0.6f * FMath::Sin(Phase * 37.f + Seed) + 0.3f * FMath::Sin(Phase * 91.f + Seed * 2.3f) +
		   0.1f * FMath::Sin(Phase * 173.f + Seed * 5.1f);
}
}  // namespace

UNYCCameraRigComponent::UNYCCameraRigComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UNYCCameraRigComponent::Initialise(USceneComponent* InMesh, USpringArmComponent* InSpringArm,
										UCameraComponent* InCamera, UCineCameraComponent* InCineCamera,
										UNYCVehicleMovementComponent* InMovement)
{
	Mesh = InMesh;
	SpringArm = InSpringArm;
	Camera = InCamera;
	CineCamera = InCineCamera;
	Movement = InMovement;
	ActivateFor(Mode);
}

FName UNYCCameraRigComponent::SocketFor(ENYCCameraMode InMode) const
{
	switch (InMode)
	{
	case ENYCCameraMode::Hood: return FName(NYCVehicleBones::SocketCameraHood);
	case ENYCCameraMode::Bumper: return FName(NYCVehicleBones::SocketCameraBumper);
	case ENYCCameraMode::Interior: return FName(NYCVehicleBones::SocketCameraInterior);
	case ENYCCameraMode::Chase:
	default: return FName(NYCVehicleBones::SocketCameraChase);
	}
}

void UNYCCameraRigComponent::ActivateFor(ENYCCameraMode NewMode)
{
	if (Camera == nullptr || SpringArm == nullptr)
	{
		return;
	}

	const bool bCine = NewMode == ENYCCameraMode::Cinematic || NewMode == ENYCCameraMode::Photo;
	Camera->SetActive(!bCine);
	if (CineCamera != nullptr)
	{
		CineCamera->SetActive(bCine);
	}

	switch (NewMode)
	{
	case ENYCCameraMode::Chase:
		SpringArm->bUsePawnControlRotation = false;
		SpringArm->bInheritPitch = false;
		SpringArm->bInheritRoll = false;
		SpringArm->bInheritYaw = true;
		SpringArm->bEnableCameraLag = true;
		SpringArm->bEnableCameraRotationLag = true;
		SpringArm->CameraLagSpeed = 8.f;
		SpringArm->CameraRotationLagSpeed = 7.f;
		SpringArm->bDoCollisionTest = true;
		SpringArm->ProbeSize = 14.f;
		SpringArm->TargetArmLength = ChaseDistanceRestCm;
		SpringArm->SetRelativeLocation(FVector(0.f, 0.f, ChaseHeightCm));
		SpringArm->SetRelativeRotation(FRotator(ChasePitchDeg, 0.f, 0.f));
		Camera->SetFieldOfView(80.f);
		Camera->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
		break;

	case ENYCCameraMode::Hood:
	case ENYCCameraMode::Bumper:
	case ENYCCameraMode::Interior:
	{
		SpringArm->bEnableCameraLag = false;
		SpringArm->bEnableCameraRotationLag = false;
		SpringArm->bDoCollisionTest = false;
		SpringArm->TargetArmLength = 0.f;
		SpringArm->SetRelativeLocation(FVector::ZeroVector);
		SpringArm->SetRelativeRotation(FRotator::ZeroRotator);
		const FName Socket = SocketFor(NewMode);
		if (Mesh != nullptr && Mesh->DoesSocketExist(Socket))
		{
			SpringArm->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Socket);
		}
		// Interior 65° gives roughly the real cabin's angular scale on a 27" monitor; the bonnet views are wider.
		Camera->SetFieldOfView(NewMode == ENYCCameraMode::Interior ? 65.f : 90.f);
		Camera->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
		break;
	}

	case ENYCCameraMode::Cinematic:
		if (CineCamera != nullptr)
		{
			CineCamera->SetCurrentFocalLength(40.f);
			CineCamera->CurrentAperture = 2.2f;
			CineCamera->FocusSettings.FocusMethod = ECameraFocusMethod::Tracking;
		}
		CinematicTime = 0.f;
		CinematicShot = 0;
		break;

	case ENYCCameraMode::Photo:
		if (CineCamera != nullptr)
		{
			CineCamera->SetCurrentFocalLength(PhotoFocalLengthMm);
			CineCamera->CurrentAperture = PhotoAperture;
			CineCamera->FocusSettings.FocusMethod = ECameraFocusMethod::Manual;
			CineCamera->FocusSettings.ManualFocusDistance = PhotoFocusDistanceCm;
		}
		break;

	default:
		break;
	}

	// Re-attach the spring arm to the chase socket for the chase view.
	if (NewMode == ENYCCameraMode::Chase && Mesh != nullptr)
	{
		const FName Socket = SocketFor(ENYCCameraMode::Chase);
		if (Mesh->DoesSocketExist(Socket))
		{
			SpringArm->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Socket);
		}
	}
}

void UNYCCameraRigComponent::SetMode(ENYCCameraMode NewMode)
{
	if (NewMode == Mode)
	{
		return;
	}
	if (Mode == ENYCCameraMode::Photo && NewMode != ENYCCameraMode::Photo)
	{
		ExitPhotoMode();
		return;
	}
	PreviousMode = Mode;
	Mode = NewMode;
	LookYaw = 0.f;
	LookPitch = 0.f;
	ActivateFor(Mode);
}

void UNYCCameraRigComponent::CycleMode()
{
	// Photo mode is entered explicitly, not by cycling.
	int32 Next = static_cast<int32>(Mode) + 1;
	if (Next >= static_cast<int32>(ENYCCameraMode::Photo))
	{
		Next = 0;
	}
	SetMode(static_cast<ENYCCameraMode>(Next));
}

void UNYCCameraRigComponent::AddLookInput(float YawDelta, float PitchDelta)
{
	if (FMath::IsNearlyZero(YawDelta) && FMath::IsNearlyZero(PitchDelta))
	{
		return;
	}
	LookIdleTime = 0.f;
	LookYaw = FMath::Clamp(LookYaw + YawDelta, -HeadLookYawLimitDeg, HeadLookYawLimitDeg);
	LookPitch = FMath::Clamp(LookPitch + PitchDelta, -HeadLookPitchLimitDeg, HeadLookPitchLimitDeg);
}

void UNYCCameraRigComponent::EnterPhotoMode()
{
	if (Mode == ENYCCameraMode::Photo || Camera == nullptr)
	{
		return;
	}
	PreviousMode = Mode;
	Mode = ENYCCameraMode::Photo;

	const UCameraComponent* Source = Camera;
	PhotoLocation = Source->GetComponentLocation();
	PhotoRotation = Source->GetComponentRotation();
	PhotoVelocity = FVector::ZeroVector;

	if (CineCamera != nullptr)
	{
		CineCamera->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
		CineCamera->SetWorldLocationAndRotation(PhotoLocation, PhotoRotation);
	}
	ActivateFor(Mode);

	if (bPhotoPausesWorld)
	{
		UGameplayStatics::SetGamePaused(GetOwner(), true);
	}
}

void UNYCCameraRigComponent::ExitPhotoMode()
{
	if (Mode != ENYCCameraMode::Photo)
	{
		return;
	}
	if (bPhotoPausesWorld)
	{
		UGameplayStatics::SetGamePaused(GetOwner(), false);
	}
	if (CineCamera != nullptr && SpringArm != nullptr)
	{
		CineCamera->AttachToComponent(SpringArm, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	}
	Mode = PreviousMode;
	ActivateFor(Mode);
}

void UNYCCameraRigComponent::AddPhotoMove(float Forward, float Right, float Up)
{
	if (Mode != ENYCCameraMode::Photo)
	{
		return;
	}
	const FRotationMatrix Basis(PhotoRotation);
	PhotoVelocity += Basis.GetScaledAxis(EAxis::X) * Forward + Basis.GetScaledAxis(EAxis::Y) * Right +
					 FVector::UpVector * Up;
}

void UNYCCameraRigComponent::AdjustPhotoFocalLength(float Delta)
{
	PhotoFocalLengthMm = FMath::Clamp(PhotoFocalLengthMm + Delta, 12.f, 300.f);
	if (CineCamera != nullptr)
	{
		CineCamera->SetCurrentFocalLength(PhotoFocalLengthMm);
	}
}

void UNYCCameraRigComponent::AdjustPhotoAperture(float Delta)
{
	PhotoAperture = FMath::Clamp(PhotoAperture + Delta, 1.2f, 22.f);
	if (CineCamera != nullptr)
	{
		CineCamera->CurrentAperture = PhotoAperture;
	}
}

void UNYCCameraRigComponent::AdjustPhotoFocusDistance(float DeltaMetres)
{
	PhotoFocusDistanceCm = FMath::Clamp(PhotoFocusDistanceCm + DeltaMetres * kCmPerMetre, 20.f, 200000.f);
	if (CineCamera != nullptr)
	{
		CineCamera->FocusSettings.ManualFocusDistance = PhotoFocusDistanceCm;
	}
}

void UNYCCameraRigComponent::UpdateChase(float DeltaTime)
{
	if (SpringArm == nullptr)
	{
		return;
	}
	const float SpeedMps = Movement != nullptr ? FMath::Abs(Movement->GetForwardSpeed()) / kCmPerMetre : 0.f;
	const float T = FMath::Clamp(SpeedMps / 30.f, 0.f, 1.f);
	const float TargetLength = FMath::Lerp(ChaseDistanceRestCm, ChaseDistanceFastCm, T);
	SpringArm->TargetArmLength = FMath::FInterpTo(SpringArm->TargetArmLength, TargetLength, DeltaTime, 2.5f);

	// Rotation lag is relaxed when cornering hard so the car does not slide across the frame.
	const float Steer = Movement != nullptr ? FMath::Abs(Movement->GetDriverSteer()) : 0.f;
	SpringArm->CameraRotationLagSpeed = FMath::Lerp(7.f, 14.f, Steer);

	const float Yaw = bLookBack ? 180.f : LookYaw;
	SpringArm->SetRelativeRotation(FRotator(ChasePitchDeg + LookPitch, Yaw, 0.f));
}

void UNYCCameraRigComponent::UpdateInterior(float DeltaTime)
{
	if (Camera == nullptr)
	{
		return;
	}

	// Recentre the head when the player stops looking around.
	LookIdleTime += DeltaTime;
	if (LookIdleTime > 0.25f)
	{
		const float Rate = 1.f / FMath::Max(0.05f, HeadLookRecentreSeconds);
		LookYaw = FMath::FInterpTo(LookYaw, 0.f, DeltaTime, Rate * 4.f);
		LookPitch = FMath::FInterpTo(LookPitch, 0.f, DeltaTime, Rate * 4.f);
	}

	float LeanRoll = 0.f;
	float GlanceYaw = 0.f;
	float ShakePitch = 0.f;
	float ShakeYaw = 0.f;

	if (Movement != nullptr)
	{
		// Lateral acceleration from the body's own velocity, expressed in g.
		const AActor* Owner = GetOwner();
		if (Owner != nullptr)
		{
			const FVector LocalVelocity = Owner->GetActorTransform().InverseTransformVector(Owner->GetVelocity());
			const float LateralG = FMath::Clamp(LocalVelocity.Y / (kCmPerMetre * 9.81f), -1.f, 1.f);
			LateralLean = FMath::FInterpTo(LateralLean, LateralG, DeltaTime, 6.f);
			LeanRoll = -LateralLean * LateralLeanMaxDeg;
		}
		GlanceYaw = Movement->GetDriverSteer() * SteerGlanceMaxDeg;

		const float Roughness = Movement->GetRoughnessSignal();
		if (Roughness > 0.01f)
		{
			ShakePhase += DeltaTime;
			ShakePitch = ShakeSignal(ShakePhase, 1.7f) * Roughness * RoughnessShakeMaxDeg;
			ShakeYaw = ShakeSignal(ShakePhase, 4.3f) * Roughness * RoughnessShakeMaxDeg * 0.6f;
		}
	}

	const float Yaw = bLookBack ? 165.f : (LookYaw + GlanceYaw + ShakeYaw);
	Camera->SetRelativeRotation(FRotator(LookPitch + ShakePitch, Yaw, LeanRoll));
}

void UNYCCameraRigComponent::UpdateCinematic(float DeltaTime)
{
	if (CineCamera == nullptr || Mesh == nullptr)
	{
		return;
	}
	CinematicTime += DeltaTime;

	// Five shots on an 8 s cycle: low front three-quarter, high orbit, wheel-level tracking, rear chase, top-down.
	constexpr float ShotSeconds = 8.f;
	if (CinematicTime >= ShotSeconds)
	{
		CinematicTime = 0.f;
		CinematicShot = (CinematicShot + 1) % 5;
	}
	const float Alpha = CinematicTime / ShotSeconds;
	const FVector Centre = Mesh->GetComponentLocation();
	const float Yaw = Mesh->GetComponentRotation().Yaw;

	FVector Offset;
	float FocalLength = 40.f;
	switch (CinematicShot)
	{
	case 0:  // low front three-quarter, slow arc
		Offset = FVector(520.f, -380.f, 60.f);
		Offset = FRotator(0.f, Yaw + Alpha * 25.f, 0.f).RotateVector(Offset);
		FocalLength = 35.f;
		break;
	case 1:  // high orbit
		Offset = FRotator(0.f, Yaw + Alpha * 360.f, 0.f).RotateVector(FVector(-900.f, 0.f, 520.f));
		FocalLength = 28.f;
		break;
	case 2:  // wheel level tracking
		Offset = FRotator(0.f, Yaw, 0.f).RotateVector(FVector(-120.f, -320.f, 25.f));
		FocalLength = 24.f;
		break;
	case 3:  // rear chase, long lens
		Offset = FRotator(0.f, Yaw, 0.f).RotateVector(FVector(-1200.f, 0.f, 180.f));
		FocalLength = 85.f;
		break;
	default:  // top-down
		Offset = FVector(0.f, 0.f, 1400.f);
		FocalLength = 50.f;
		break;
	}

	const FVector Location = Centre + Offset;
	const FRotator Rotation = (Centre - Location).Rotation();
	CineCamera->SetWorldLocationAndRotation(Location, Rotation);
	CineCamera->SetCurrentFocalLength(FocalLength);
	CineCamera->FocusSettings.FocusMethod = ECameraFocusMethod::Manual;
	CineCamera->FocusSettings.ManualFocusDistance = static_cast<float>(Offset.Size());
}

void UNYCCameraRigComponent::UpdatePhoto(float DeltaTime)
{
	if (CineCamera == nullptr)
	{
		return;
	}
	// The world may be paused, so use unpaused real time for the free-fly.
	const float Dt = DeltaTime > 0.f ? DeltaTime : FApp::GetDeltaTime();
	PhotoRotation.Yaw += LookYaw;
	PhotoRotation.Pitch = FMath::Clamp(PhotoRotation.Pitch + LookPitch, -87.f, 87.f);
	LookYaw = 0.f;
	LookPitch = 0.f;

	PhotoLocation += PhotoVelocity * PhotoMoveSpeedMps * kCmPerMetre * Dt;
	PhotoVelocity = FMath::VInterpTo(PhotoVelocity, FVector::ZeroVector, Dt, 8.f);

	CineCamera->SetWorldLocationAndRotation(PhotoLocation, PhotoRotation);
}

void UNYCCameraRigComponent::TickComponent(float DeltaTime, ELevelTick TickType,
										   FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	switch (Mode)
	{
	case ENYCCameraMode::Chase: UpdateChase(DeltaTime); break;
	case ENYCCameraMode::Interior: UpdateInterior(DeltaTime); break;
	case ENYCCameraMode::Cinematic: UpdateCinematic(DeltaTime); break;
	case ENYCCameraMode::Photo: UpdatePhoto(DeltaTime); break;
	case ENYCCameraMode::Hood:
	case ENYCCameraMode::Bumper:
		// Fixed views: only the roughness shake applies.
		if (Camera != nullptr && Movement != nullptr)
		{
			const float Roughness = Movement->GetRoughnessSignal();
			ShakePhase += DeltaTime;
			const float Pitch = ShakeSignal(ShakePhase, 2.9f) * Roughness * RoughnessShakeMaxDeg * 0.7f;
			Camera->SetRelativeRotation(FRotator(Pitch, bLookBack ? 180.f : 0.f, 0.f));
		}
		break;
	default:
		break;
	}
}
