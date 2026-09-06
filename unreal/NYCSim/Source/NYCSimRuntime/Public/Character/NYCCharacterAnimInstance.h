// The player character's locomotion state machine and pose evaluation, in C++.
//
// ADR-001 rules out authoring an Animation Blueprint here, so the graph is a small, explicit machine:
//
//        Idle <-> Walk <-> Jog <-> Sprint          (ground, speed-driven, 4-way directional)
//          |        |                              (crouch swaps the ground set)
//          +--> JumpStart -> JumpLoop -> Land      (air)
//          +--> TurnInPlace L/R 90/180             (stationary, yaw error)
//          +--> Action (one-shot: enter/exit vehicle, open door, press button)
//        SitDrive  <->  Steer L/R                  (in a vehicle)
//
// Pose evaluation blends at most five clips: two adjacent cardinal directions inside the lower tier, the same two
// inside the upper tier, and a one-shot action clip layered on top. Everything is driven from
// FNYCLocomotionInput, which the character writes once per frame on the game thread and the proxy copies in
// PreUpdate, so the worker thread never touches game state.
//
// Clips are resolved by name from UNYCGameplaySettings::CharacterAnimationRoot through FNYCCharacterContract.
// A missing clip falls back to the nearest one that exists (walk -> idle, jog -> walk, sprint -> jog) and is
// reported once, so a partial animation set still animates instead of T-posing.
#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "NYCCharacterAnimInstance.generated.h"

class UAnimSequence;

UENUM(BlueprintType)
enum class ENYCLocomotionState : uint8
{
	Idle = 0,
	Walk,
	Jog,
	Sprint,
	CrouchIdle,
	CrouchWalk,
	JumpStart,
	JumpLoop,
	Land,
	TurnInPlace,
	InVehicle,
	Action
};

/** One-shot actions the character can request; they play once and return to locomotion. */
UENUM(BlueprintType)
enum class ENYCCharacterAction : uint8
{
	None = 0,
	EnterVehicleLeft,
	EnterVehicleRight,
	ExitVehicleLeft,
	ExitVehicleRight,
	OpenDoor,
	CloseDoor,
	CheckPhone,
	PressButton,
	Point
};

/** Everything the state machine reads. Written on the game thread, copied in PreUpdate. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCLocomotionInput
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	float SpeedMps = 0.f;

	/** Movement direction relative to the character's facing, degrees, -180..180 (0 = forward). */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	float MovementAngleDeg = 0.f;

	/** Yaw the character still has to turn to face the aim direction, degrees. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	float YawErrorDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	float AimPitchDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	bool bInAir = false;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	bool bCrouched = false;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	bool bSprinting = false;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	bool bInVehicle = false;

	/** -1..1 steering input while driving, used to blend the steer poses. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	float VehicleSteer = 0.f;

	/** Vertical speed, m/s; the landing state uses it to pick a soft or hard landing. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	float VerticalSpeedMps = 0.f;
};

/** Worker-thread proxy: the whole machine lives here. */
USTRUCT()
struct NYCSIMRUNTIME_API FNYCCharacterAnimProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FNYCCharacterAnimProxy() = default;
	explicit FNYCCharacterAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void Initialize(UAnimInstance* InAnimInstance) override;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void Update(float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	ENYCLocomotionState GetState() const { return State; }

private:
	struct FTierClips
	{
		UAnimSequence* Forward = nullptr;
		UAnimSequence* Backward = nullptr;
		UAnimSequence* Left = nullptr;
		UAnimSequence* Right = nullptr;
	};

	void UpdateStateMachine(float DeltaSeconds);
	void SelectClips();
	/** Adjacent cardinal pair for a movement angle, with the blend fraction between them. */
	void DirectionalPair(const FTierClips& Tier, float AngleDeg, UAnimSequence*& OutA, UAnimSequence*& OutB,
						 float& OutAlpha) const;

	FNYCLocomotionInput Input;
	ENYCLocomotionState State = ENYCLocomotionState::Idle;
	ENYCCharacterAction Action = ENYCCharacterAction::None;

	// Clip set, resolved once by the anim instance on the game thread.
	FTierClips WalkTier;
	FTierClips JogTier;
	UAnimSequence* IdleClip = nullptr;
	UAnimSequence* SprintClip = nullptr;
	UAnimSequence* CrouchIdleClip = nullptr;
	UAnimSequence* CrouchWalkClip = nullptr;
	UAnimSequence* JumpStartClip = nullptr;
	UAnimSequence* JumpLoopClip = nullptr;
	UAnimSequence* JumpLandClip = nullptr;
	UAnimSequence* LandHardClip = nullptr;
	UAnimSequence* TurnLeft90Clip = nullptr;
	UAnimSequence* TurnRight90Clip = nullptr;
	UAnimSequence* TurnLeft180Clip = nullptr;
	UAnimSequence* TurnRight180Clip = nullptr;
	UAnimSequence* SitDriveClip = nullptr;
	UAnimSequence* SteerLeftClip = nullptr;
	UAnimSequence* SteerRightClip = nullptr;
	UAnimSequence* ActionClip = nullptr;

	// Evaluation plan produced by SelectClips().
	UAnimSequence* LowerA = nullptr;
	UAnimSequence* LowerB = nullptr;
	UAnimSequence* UpperA = nullptr;
	UAnimSequence* UpperB = nullptr;
	float LowerDirAlpha = 0.f;
	float UpperDirAlpha = 0.f;
	float TierAlpha = 0.f;
	float PlayRate = 1.f;
	bool bLoopLocomotion = true;

	float LocomotionTime = 0.f;
	float ActionTime = 0.f;
	float ActionLength = 0.f;
	float ActionBlend = 0.f;
	float TurnTime = 0.f;
	float StateTime = 0.f;

	friend class UNYCCharacterAnimInstance;
};

UCLASS(Transient)
class NYCSIMRUNTIME_API UNYCCharacterAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** Loads the clip set from the configured animation directory. Safe to call more than once. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Character")
	void ResolveClips();

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Character")
	void SetLocomotionInput(const FNYCLocomotionInput& InInput) { LocomotionInput = InInput; }

	/** Requests a one-shot action; it starts on the next update and clears itself when it finishes. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Character")
	void RequestAction(ENYCCharacterAction InAction);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Character")
	ENYCCharacterAction GetPendingAction() const { return PendingAction; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Character")
	ENYCLocomotionState GetLocomotionState() const { return Proxy.GetState(); }

	/** Clip ids that were requested but not found, for the report and the editor validation. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Character")
	TArray<FName> GetMissingClips() const { return MissingClips; }

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Character")
	FNYCLocomotionInput LocomotionInput;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;
	virtual void NativeInitializeAnimation() override;

	friend struct FNYCCharacterAnimProxy;

private:
	UAnimSequence* Load(const TCHAR* Id);

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UAnimSequence>> Clips;

	TArray<FName> MissingClips;
	ENYCCharacterAction PendingAction = ENYCCharacterAction::None;
	bool bClipsResolved = false;
	FNYCCharacterAnimProxy Proxy;
};
