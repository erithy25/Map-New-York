// The player's car: a 2019 Ford Fusion Hybrid on Chaos Vehicles (ADR-009).
//
// The pawn owns the mesh, the movement component and every subsystem that makes the car feel like a car —
// lights, dashboard, mirrors, body controls, damage, the camera rig and the audio. It binds Enhanced Input, feeds
// the traffic simulation its position as the observer, and hands the character over when the player gets out.
//
// Nothing here needs a Blueprint: the mesh comes from UNYCGameplaySettings::PlayerVehicleMesh, the anim instance
// is UNYCVehicleAnimInstance, and the input contexts come from UNYCInputConfig (assets when present, the
// documented default bindings otherwise).
#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "Player/NYCCameraRigComponent.h"
#include "NYCPlayerVehicle.generated.h"

class UAudioComponent;
class UCameraComponent;
class UCineCameraComponent;
class UInputAction;
class UNYCGpsSubsystem;
class UNYCVehicleAudioComponent;
class UNYCVehicleBodyComponent;
class UNYCVehicleDamageComponent;
class UNYCVehicleDashboardComponent;
class UNYCVehicleLightsComponent;
class UNYCVehicleMirrorComponent;
class UNYCVehicleMovementComponent;
class USpringArmComponent;
struct FInputActionValue;

/** Raised when the driver asks to get out; the character's interaction component runs the actual sequence. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FNYCExitVehicleRequested);

UCLASS()
class NYCSIMRUNTIME_API ANYCPlayerVehicle : public AWheeledVehiclePawn
{
	GENERATED_BODY()

public:
	explicit ANYCPlayerVehicle(const FObjectInitializer& ObjectInitializer);

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void NotifyHit(UPrimitiveComponent* MyComp, AActor* Other, UPrimitiveComponent* OtherComp,
						   bool bSelfMoved, FVector HitLocation, FVector HitNormal, FVector NormalImpulse,
						   const FHitResult& Hit) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void UnPossessed() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	// ---- accessors used by the other subsystems --------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCVehicleMovementComponent* GetNYCMovement() const { return NYCMovement; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCVehicleLightsComponent* GetLights() const { return Lights; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCVehicleBodyComponent* GetBody() const { return Body; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCVehicleDashboardComponent* GetDashboard() const { return Dashboard; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCVehicleDamageComponent* GetDamage() const { return Damage; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCCameraRigComponent* GetCameraRig() const { return CameraRig; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	UNYCVehicleAudioComponent* GetVehicleAudio() const { return VehicleAudio; }

	/** World-space transform of the driver's seat, used by the enter/exit sequence. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	FTransform GetDriverSeatTransform() const;

	/** World-space point the character walks to before opening the door. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	FTransform GetDriverEntryTransform() const;

	/** Opens/closes the driver's door (used by the enter/exit sequence). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetDriverDoorOpen(bool bOpen);

	/** Called by the character when it takes the wheel or gets out. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetDriverPresent(bool bPresent);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	bool HasDriver() const { return bDriverPresent; }

	/** The registration plate string rendered onto PLATE_FACE. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Vehicle")
	FString GetPlateNumber() const { return PlateNumber; }

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Vehicle")
	FNYCExitVehicleRequested OnExitRequested;

protected:
	// ---- input handlers --------------------------------------------------------------------------------------
	void OnThrottle(const FInputActionValue& Value);
	void OnBrake(const FInputActionValue& Value);
	void OnSteer(const FInputActionValue& Value);
	void OnHandbrakeStart(const FInputActionValue& Value);
	void OnHandbrakeStop(const FInputActionValue& Value);
	void OnToggleReverse(const FInputActionValue& Value);
	void OnHornStart(const FInputActionValue& Value);
	void OnHornStop(const FInputActionValue& Value);
	void OnCycleHeadlights(const FInputActionValue& Value);
	void OnToggleFogLights(const FInputActionValue& Value);
	void OnIndicateLeft(const FInputActionValue& Value);
	void OnIndicateRight(const FInputActionValue& Value);
	void OnToggleHazards(const FInputActionValue& Value);
	void OnCycleWipers(const FInputActionValue& Value);
	void OnWindowDown(const FInputActionValue& Value);
	void OnWindowUp(const FInputActionValue& Value);
	void OnCycleCamera(const FInputActionValue& Value);
	void OnPhotoMode(const FInputActionValue& Value);
	void OnLookAround(const FInputActionValue& Value);
	void OnRadioNext(const FInputActionValue& Value);
	void OnRadioPrevious(const FInputActionValue& Value);
	void OnExitVehicle(const FInputActionValue& Value);

private:
	void ApplyMeshAndContract();
	void UpdateWeatherCoupling(float DeltaTime);
	void UpdateLightsFromState(float DeltaTime);
	void PushWheelAnimState(float DeltaTime);
	void PublishObserverToTraffic();

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleMovementComponent> NYCMovement;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UCineCameraComponent> CineCamera;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCCameraRigComponent> CameraRig;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleLightsComponent> Lights;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleDashboardComponent> Dashboard;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleBodyComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleMirrorComponent> Mirrors;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleDamageComponent> Damage;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Vehicle")
	TObjectPtr<UNYCVehicleAudioComponent> VehicleAudio;

	float Throttle = 0.f;
	float BrakeInput = 0.f;
	float SteerInput = 0.f;
	float HandbrakeInput = 0.f;
	bool bReverseSelected = false;
	bool bFogLightsOn = false;
	bool bDriverPresent = true;
	float WheelSpinDeg[4] = {0.f, 0.f, 0.f, 0.f};
	float WeatherSampleTimer = 0.f;
	FString PlateNumber;
};

/**
 * Alias under the name Config/DefaultEngine.ini references
 * ([/Script/NYCSimRuntime.NYCSimWorldSettings] DefaultPawnClassPath = NYCPlayerVehiclePawn).
 * That setting belongs to the world/streaming lane, so rather than edit another agent's file the class it names
 * exists here and is exactly the player vehicle.
 */
UCLASS()
class NYCSIMRUNTIME_API ANYCPlayerVehiclePawn : public ANYCPlayerVehicle
{
	GENERATED_BODY()

public:
	explicit ANYCPlayerVehiclePawn(const FObjectInitializer& ObjectInitializer)
		: Super(ObjectInitializer)
	{
	}
};
