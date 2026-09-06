// The camera rig: chase, hood, bumper, interior (with head look), cinematic and photo mode.
//
// The rig does not create its own components — the pawn creates the spring arm, the gameplay camera and the cine
// camera in its constructor and hands them over, which keeps every camera a proper default subobject and lets the
// pawn decide the attachment sockets from the mesh contract.
//
// Behaviour worth stating:
//   * Chase: spring arm with speed-proportional distance (3.6 m at rest, 5.4 m at 30 m/s), camera lag that eases
//     off in corners so the car does not swim, and a look-back key.
//   * Interior: the camera sits on SKT_CamInterior. Head look is free within ±80° yaw / ±45° pitch, recentres in
//     0.35 s when released, and adds two involuntary motions a driver actually makes — a lean into lateral
//     acceleration (up to 6°) and a glance into the turn proportional to steering (up to 12°).
//   * Road roughness from the movement component shakes the camera; the amplitude is what the tyre model reports
//     for the surface under the wheels, so cobblestones shake and fresh asphalt does not.
//   * Photo mode detaches the camera, frees it in six axes, and exposes focal length, aperture and focus distance
//     on the cine camera; it also pauses the world when asked.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NYCCameraRigComponent.generated.h"

class UCameraComponent;
class UCineCameraComponent;
class UNYCVehicleMovementComponent;
class USceneComponent;
class USpringArmComponent;

UENUM(BlueprintType)
enum class ENYCCameraMode : uint8
{
	Chase = 0,
	Hood,
	Bumper,
	Interior,
	Cinematic,
	Photo,
	Count UMETA(Hidden)
};

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCCameraRigComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCCameraRigComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Hands the rig the components the pawn owns. `Mesh` provides the camera sockets. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void Initialise(USceneComponent* InMesh, USpringArmComponent* InSpringArm, UCameraComponent* InCamera,
					UCineCameraComponent* InCineCamera, UNYCVehicleMovementComponent* InMovement);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void SetMode(ENYCCameraMode Mode);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void CycleMode();

	UFUNCTION(BlueprintPure, Category = "NYCSim|Camera")
	ENYCCameraMode GetMode() const { return Mode; }

	/** Head look / orbit input, in degrees per second scaled by the action value. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void AddLookInput(float YawDelta, float PitchDelta);

	/** Hold to look over your shoulder (chase and interior). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void SetLookBack(bool bEnabled) { bLookBack = bEnabled; }

	// ---- photo mode ----------------------------------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void EnterPhotoMode();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void ExitPhotoMode();

	UFUNCTION(BlueprintPure, Category = "NYCSim|Camera")
	bool IsPhotoMode() const { return Mode == ENYCCameraMode::Photo; }

	/** Free-fly input while in photo mode: forward/right/up in the camera's frame, metres per second. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void AddPhotoMove(float Forward, float Right, float Up);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void AdjustPhotoFocalLength(float Delta);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void AdjustPhotoAperture(float Delta);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void AdjustPhotoFocusDistance(float DeltaMetres);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Camera")
	void SetPhotoPausesWorld(bool bPause) { bPhotoPausesWorld = bPause; }

	/** True when the interior view is active, so the mirrors know they must render. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Camera")
	bool NeedsMirrors() const { return Mode == ENYCCameraMode::Interior || Mode == ENYCCameraMode::Chase; }

	// ---- tuning --------------------------------------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float ChaseDistanceRestCm = 360.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float ChaseDistanceFastCm = 540.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float ChaseHeightCm = 145.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float ChasePitchDeg = -9.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float HeadLookYawLimitDeg = 80.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float HeadLookPitchLimitDeg = 45.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float HeadLookRecentreSeconds = 0.35f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float LateralLeanMaxDeg = 6.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float SteerGlanceMaxDeg = 12.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float RoughnessShakeMaxDeg = 0.9f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Camera")
	float PhotoMoveSpeedMps = 6.f;

private:
	void UpdateChase(float DeltaTime);
	void UpdateInterior(float DeltaTime);
	void UpdateCinematic(float DeltaTime);
	void UpdatePhoto(float DeltaTime);
	void ActivateFor(ENYCCameraMode NewMode);
	FName SocketFor(ENYCCameraMode InMode) const;

	UPROPERTY(Transient)
	TObjectPtr<USceneComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(Transient)
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(Transient)
	TObjectPtr<UCineCameraComponent> CineCamera;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleMovementComponent> Movement;

	ENYCCameraMode Mode = ENYCCameraMode::Chase;
	ENYCCameraMode PreviousMode = ENYCCameraMode::Chase;

	float LookYaw = 0.f;
	float LookPitch = 0.f;
	float LookIdleTime = 0.f;
	bool bLookBack = false;

	float ShakePhase = 0.f;
	float LateralLean = 0.f;

	// Cinematic orbit state.
	float CinematicTime = 0.f;
	int32 CinematicShot = 0;

	// Photo mode state.
	FVector PhotoLocation = FVector::ZeroVector;
	FRotator PhotoRotation = FRotator::ZeroRotator;
	FVector PhotoVelocity = FVector::ZeroVector;
	float PhotoFocalLengthMm = 35.f;
	float PhotoAperture = 2.8f;
	float PhotoFocusDistanceCm = 1000.f;
	bool bPhotoPausesWorld = true;
};
