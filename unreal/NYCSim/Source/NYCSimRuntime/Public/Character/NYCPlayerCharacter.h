// The player on foot.
//
// A standard ACharacter with the UE5-Mannequin-named skeleton (FNYCCharacterContract), driven by
// UNYCCharacterAnimInstance. Speeds are the real ones: a New Yorker walks at 1.4 m/s, jogs at 3.4 and sprints at
// 6.0, so the movement component's MaxWalkSpeed is set per state rather than left at the template's 600 cm/s.
//
// Getting in and out of the car is UNYCVehicleInteractionComponent's job; this class only forwards the input and
// swaps the mapping context when the possession changes.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "NYCPlayerCharacter.generated.h"

class UCameraComponent;
class UNYCCharacterAnimInstance;
class UNYCVehicleInteractionComponent;
class USpringArmComponent;
struct FInputActionValue;

UCLASS()
class NYCSIMRUNTIME_API ANYCPlayerCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	explicit ANYCPlayerCharacter(const FObjectInitializer& ObjectInitializer);

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void Landed(const FHitResult& Hit) override;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Character")
	UNYCVehicleInteractionComponent* GetInteraction() const { return Interaction; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Character")
	UNYCCharacterAnimInstance* GetNYCAnimInstance() const;

	/** Third person by default; the interaction sequence and the photo mode switch it. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Character")
	void SetFirstPerson(bool bFirstPerson);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Character")
	bool IsFirstPerson() const { return bFirstPerson; }

	/** Walking / jogging / sprinting speeds in metres per second (the movement component works in cm/s). */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Character")
	float WalkSpeedMps = 1.4f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Character")
	float JogSpeedMps = 3.4f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Character")
	float SprintSpeedMps = 6.0f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Character")
	float CrouchSpeedMps = 0.9f;

protected:
	void OnMove(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnJumpPressed(const FInputActionValue& Value);
	void OnSprintStart(const FInputActionValue& Value);
	void OnSprintStop(const FInputActionValue& Value);
	void OnCrouchToggle(const FInputActionValue& Value);
	void OnInteract(const FInputActionValue& Value);
	void OnCycleCamera(const FInputActionValue& Value);

private:
	void UpdateLocomotionInput(float DeltaTime);
	void PublishObserver();

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Character")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Character")
	TObjectPtr<UCameraComponent> ThirdPersonCamera;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Character")
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Character")
	TObjectPtr<UNYCVehicleInteractionComponent> Interaction;

	FVector2D MoveInput = FVector2D::ZeroVector;
	bool bSprinting = false;
	bool bFirstPerson = false;
	float LastVerticalSpeedMps = 0.f;
};
