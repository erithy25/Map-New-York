#include "Character/NYCCharacterAnimInstance.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "AnimationRuntime.h"
#include "BonePose.h"
#include "Character/NYCCharacterContract.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"

namespace
{
/// Speed thresholds, m/s. A New Yorker walks at 1.4, jogs at 3.4 and sprints at 6.0.
constexpr float kWalkSpeed = 1.6f;
constexpr float kJogSpeed = 3.6f;
constexpr float kSprintSpeed = 6.0f;
/// A hard landing is anything faster than a 2 m fall.
constexpr float kHardLandingSpeed = 6.3f;
/// Turn-in-place fires above this yaw error while standing still.
constexpr float kTurnInPlaceDeg = 55.f;

float ClipLength(const UAnimSequence* Clip)
{
	return Clip != nullptr ? Clip->GetPlayLength() : 0.f;
}

/// Evaluates one clip into `Out`; leaves the reference pose when the clip is missing.
void EvaluateClip(const UAnimSequence* Clip, float Time, bool bLoop, FPoseContext& Out)
{
	Out.ResetToRefPose();
	if (Clip == nullptr)
	{
		return;
	}
	FAnimationPoseData PoseData(Out);
	FAnimExtractContext Context(static_cast<double>(Time), /*bExtractRootMotion*/ false, FDeltaTimeRecord(), bLoop);
	Clip->GetAnimationPose(PoseData, Context);
}
}  // namespace

// ------------------------------------------------------------------------------------------------- proxy

void FNYCCharacterAnimProxy::Initialize(UAnimInstance* InAnimInstance)
{
	FAnimInstanceProxy::Initialize(InAnimInstance);
	State = ENYCLocomotionState::Idle;
	LocomotionTime = 0.f;
	ActionTime = 0.f;
	ActionBlend = 0.f;
}

void FNYCCharacterAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);

	UNYCCharacterAnimInstance* Instance = Cast<UNYCCharacterAnimInstance>(InAnimInstance);
	if (Instance == nullptr)
	{
		return;
	}
	Input = Instance->LocomotionInput;

	// Copy the resolved clip set (cheap raw pointers; the instance keeps the strong references).
	auto Get = [Instance](const TCHAR* Id) -> UAnimSequence* {
		const TObjectPtr<UAnimSequence>* Found = Instance->Clips.Find(FName(Id));
		return Found != nullptr ? Found->Get() : nullptr;
	};
	IdleClip = Get(NYCCharacterAnims::Idle);
	WalkTier.Forward = Get(NYCCharacterAnims::WalkForward);
	WalkTier.Backward = Get(NYCCharacterAnims::WalkBackward);
	WalkTier.Left = Get(NYCCharacterAnims::WalkLeft);
	WalkTier.Right = Get(NYCCharacterAnims::WalkRight);
	JogTier.Forward = Get(NYCCharacterAnims::JogForward);
	JogTier.Backward = Get(NYCCharacterAnims::JogBackward);
	JogTier.Left = Get(NYCCharacterAnims::JogLeft);
	JogTier.Right = Get(NYCCharacterAnims::JogRight);
	SprintClip = Get(NYCCharacterAnims::SprintForward);
	CrouchIdleClip = Get(NYCCharacterAnims::CrouchIdle);
	CrouchWalkClip = Get(NYCCharacterAnims::CrouchWalk);
	JumpStartClip = Get(NYCCharacterAnims::JumpStart);
	JumpLoopClip = Get(NYCCharacterAnims::JumpLoop);
	JumpLandClip = Get(NYCCharacterAnims::JumpLand);
	LandHardClip = Get(NYCCharacterAnims::LandHard);
	TurnLeft90Clip = Get(NYCCharacterAnims::TurnLeft90);
	TurnRight90Clip = Get(NYCCharacterAnims::TurnRight90);
	TurnLeft180Clip = Get(NYCCharacterAnims::TurnLeft180);
	TurnRight180Clip = Get(NYCCharacterAnims::TurnRight180);
	SitDriveClip = Get(NYCCharacterAnims::SitDrive);
	SteerLeftClip = Get(NYCCharacterAnims::SteerLeft);
	SteerRightClip = Get(NYCCharacterAnims::SteerRight);

	// Pick up a pending action request.
	if (Instance->PendingAction != ENYCCharacterAction::None && Action == ENYCCharacterAction::None)
	{
		Action = Instance->PendingAction;
		Instance->PendingAction = ENYCCharacterAction::None;
		const TCHAR* Id = nullptr;
		switch (Action)
		{
		case ENYCCharacterAction::EnterVehicleLeft: Id = NYCCharacterAnims::EnterVehicleLeft; break;
		case ENYCCharacterAction::EnterVehicleRight: Id = NYCCharacterAnims::EnterVehicleRight; break;
		case ENYCCharacterAction::ExitVehicleLeft: Id = NYCCharacterAnims::ExitVehicleLeft; break;
		case ENYCCharacterAction::ExitVehicleRight: Id = NYCCharacterAnims::ExitVehicleRight; break;
		case ENYCCharacterAction::OpenDoor: Id = NYCCharacterAnims::OpenDoor; break;
		case ENYCCharacterAction::CloseDoor: Id = NYCCharacterAnims::CloseDoor; break;
		case ENYCCharacterAction::CheckPhone: Id = NYCCharacterAnims::CheckPhone; break;
		case ENYCCharacterAction::PressButton: Id = NYCCharacterAnims::PressButton; break;
		case ENYCCharacterAction::Point: Id = NYCCharacterAnims::Point; break;
		default: break;
		}
		ActionClip = Id != nullptr ? Get(Id) : nullptr;
		ActionTime = 0.f;
		ActionLength = ClipLength(ActionClip);
		if (ActionClip == nullptr)
		{
			// Nothing to play: complete the action immediately so the gameplay sequence is not blocked.
			Action = ENYCCharacterAction::None;
		}
	}
}

void FNYCCharacterAnimProxy::UpdateStateMachine(float DeltaSeconds)
{
	const ENYCLocomotionState Previous = State;

	if (Action != ENYCCharacterAction::None && ActionClip != nullptr)
	{
		State = ENYCLocomotionState::Action;
		ActionTime += DeltaSeconds;
		ActionBlend = FMath::Min(1.f, ActionBlend + DeltaSeconds / 0.12f);
		if (ActionTime >= ActionLength)
		{
			Action = ENYCCharacterAction::None;
			ActionClip = nullptr;
			ActionTime = 0.f;
		}
	}
	else
	{
		ActionBlend = FMath::Max(0.f, ActionBlend - DeltaSeconds / 0.18f);

		if (Input.bInVehicle)
		{
			State = ENYCLocomotionState::InVehicle;
		}
		else if (Input.bInAir)
		{
			if (State != ENYCLocomotionState::JumpLoop && State != ENYCLocomotionState::JumpStart)
			{
				State = ENYCLocomotionState::JumpStart;
				StateTime = 0.f;
			}
			else if (State == ENYCLocomotionState::JumpStart && StateTime > ClipLength(JumpStartClip) * 0.8f)
			{
				State = ENYCLocomotionState::JumpLoop;
				StateTime = 0.f;
			}
		}
		else if (State == ENYCLocomotionState::JumpLoop || State == ENYCLocomotionState::JumpStart)
		{
			State = ENYCLocomotionState::Land;
			StateTime = 0.f;
		}
		else if (State == ENYCLocomotionState::Land &&
				 StateTime < ClipLength(Input.VerticalSpeedMps < -kHardLandingSpeed ? LandHardClip : JumpLandClip))
		{
			// Stay in the landing state until the clip finishes, unless the player is already running again.
			if (Input.SpeedMps > kWalkSpeed)
			{
				State = ENYCLocomotionState::Jog;
				StateTime = 0.f;
			}
		}
		else if (Input.bCrouched)
		{
			State = Input.SpeedMps > 0.15f ? ENYCLocomotionState::CrouchWalk : ENYCLocomotionState::CrouchIdle;
		}
		else if (Input.SpeedMps < 0.15f)
		{
			const bool bWantsTurn = FMath::Abs(Input.YawErrorDeg) > kTurnInPlaceDeg;
			if (bWantsTurn && State != ENYCLocomotionState::TurnInPlace)
			{
				State = ENYCLocomotionState::TurnInPlace;
				TurnTime = 0.f;
			}
			else if (State != ENYCLocomotionState::TurnInPlace)
			{
				State = ENYCLocomotionState::Idle;
			}
		}
		else if (Input.bSprinting && Input.SpeedMps > kJogSpeed)
		{
			State = ENYCLocomotionState::Sprint;
		}
		else if (Input.SpeedMps > kWalkSpeed)
		{
			State = ENYCLocomotionState::Jog;
		}
		else
		{
			State = ENYCLocomotionState::Walk;
		}

		if (State == ENYCLocomotionState::TurnInPlace)
		{
			TurnTime += DeltaSeconds;
			const UAnimSequence* Clip = FMath::Abs(Input.YawErrorDeg) > 135.f
											? (Input.YawErrorDeg < 0.f ? TurnLeft180Clip : TurnRight180Clip)
											: (Input.YawErrorDeg < 0.f ? TurnLeft90Clip : TurnRight90Clip);
			if (TurnTime >= ClipLength(Clip) || FMath::Abs(Input.YawErrorDeg) < 8.f || Input.SpeedMps > 0.2f)
			{
				State = Input.SpeedMps > 0.15f ? ENYCLocomotionState::Walk : ENYCLocomotionState::Idle;
			}
		}
	}

	StateTime = (State == Previous) ? StateTime + DeltaSeconds : 0.f;
}

void FNYCCharacterAnimProxy::DirectionalPair(const FTierClips& Tier, float AngleDeg, UAnimSequence*& OutA,
											 UAnimSequence*& OutB, float& OutAlpha) const
{
	// Cardinals at -180 (back), -90 (left), 0 (forward), +90 (right), +180 (back).
	UAnimSequence* const Cardinals[5] = {Tier.Backward, Tier.Left, Tier.Forward, Tier.Right, Tier.Backward};
	const float Angle = FMath::Clamp(AngleDeg, -180.f, 180.f);
	const float Position = (Angle + 180.f) / 90.f;  // 0..4
	const int32 Index = FMath::Clamp(static_cast<int32>(Position), 0, 3);
	OutA = Cardinals[Index] != nullptr ? Cardinals[Index] : Tier.Forward;
	OutB = Cardinals[Index + 1] != nullptr ? Cardinals[Index + 1] : Tier.Forward;
	OutAlpha = Position - static_cast<float>(Index);
}

void FNYCCharacterAnimProxy::SelectClips()
{
	LowerA = LowerB = UpperA = UpperB = nullptr;
	LowerDirAlpha = UpperDirAlpha = 0.f;
	TierAlpha = 0.f;
	PlayRate = 1.f;
	bLoopLocomotion = true;

	switch (State)
	{
	case ENYCLocomotionState::Idle:
		LowerA = LowerB = IdleClip;
		break;

	case ENYCLocomotionState::Walk:
	{
		// Idle -> directional walk by speed.
		LowerA = LowerB = IdleClip;
		DirectionalPair(WalkTier, Input.MovementAngleDeg, UpperA, UpperB, UpperDirAlpha);
		TierAlpha = FMath::Clamp(Input.SpeedMps / kWalkSpeed, 0.f, 1.f);
		PlayRate = FMath::Clamp(Input.SpeedMps / 1.34f, 0.5f, 1.6f);
		break;
	}

	case ENYCLocomotionState::Jog:
	{
		DirectionalPair(WalkTier, Input.MovementAngleDeg, LowerA, LowerB, LowerDirAlpha);
		DirectionalPair(JogTier, Input.MovementAngleDeg, UpperA, UpperB, UpperDirAlpha);
		TierAlpha = FMath::Clamp((Input.SpeedMps - kWalkSpeed) / (kJogSpeed - kWalkSpeed), 0.f, 1.f);
		PlayRate = FMath::Clamp(Input.SpeedMps / 3.4f, 0.6f, 1.5f);
		break;
	}

	case ENYCLocomotionState::Sprint:
	{
		DirectionalPair(JogTier, Input.MovementAngleDeg, LowerA, LowerB, LowerDirAlpha);
		UpperA = UpperB = SprintClip != nullptr ? SprintClip : JogTier.Forward;
		TierAlpha = FMath::Clamp((Input.SpeedMps - kJogSpeed) / (kSprintSpeed - kJogSpeed), 0.f, 1.f);
		PlayRate = FMath::Clamp(Input.SpeedMps / 6.0f, 0.7f, 1.4f);
		break;
	}

	case ENYCLocomotionState::CrouchIdle:
		LowerA = LowerB = CrouchIdleClip != nullptr ? CrouchIdleClip : IdleClip;
		break;

	case ENYCLocomotionState::CrouchWalk:
		LowerA = LowerB = CrouchIdleClip != nullptr ? CrouchIdleClip : IdleClip;
		UpperA = UpperB = CrouchWalkClip != nullptr ? CrouchWalkClip : WalkTier.Forward;
		TierAlpha = FMath::Clamp(Input.SpeedMps / kWalkSpeed, 0.f, 1.f);
		PlayRate = FMath::Clamp(Input.SpeedMps / 1.1f, 0.5f, 1.5f);
		break;

	case ENYCLocomotionState::JumpStart:
		LowerA = LowerB = JumpStartClip != nullptr ? JumpStartClip : IdleClip;
		bLoopLocomotion = false;
		break;

	case ENYCLocomotionState::JumpLoop:
		LowerA = LowerB = JumpLoopClip != nullptr ? JumpLoopClip : IdleClip;
		break;

	case ENYCLocomotionState::Land:
	{
		UAnimSequence* Clip = Input.VerticalSpeedMps < -kHardLandingSpeed ? LandHardClip : JumpLandClip;
		LowerA = LowerB = Clip != nullptr ? Clip : IdleClip;
		bLoopLocomotion = false;
		break;
	}

	case ENYCLocomotionState::TurnInPlace:
	{
		UAnimSequence* Clip = FMath::Abs(Input.YawErrorDeg) > 135.f
								  ? (Input.YawErrorDeg < 0.f ? TurnLeft180Clip : TurnRight180Clip)
								  : (Input.YawErrorDeg < 0.f ? TurnLeft90Clip : TurnRight90Clip);
		LowerA = LowerB = Clip != nullptr ? Clip : IdleClip;
		bLoopLocomotion = false;
		break;
	}

	case ENYCLocomotionState::InVehicle:
	{
		LowerA = LowerB = SitDriveClip != nullptr ? SitDriveClip : IdleClip;
		// Steering blends toward the left or right pose; at centre it is the plain driving pose.
		UAnimSequence* SteerClip = Input.VehicleSteer < 0.f ? SteerLeftClip : SteerRightClip;
		UpperA = UpperB = SteerClip != nullptr ? SteerClip : LowerA;
		TierAlpha = FMath::Clamp(FMath::Abs(Input.VehicleSteer), 0.f, 1.f);
		PlayRate = 1.f;
		break;
	}

	case ENYCLocomotionState::Action:
	default:
		LowerA = LowerB = IdleClip;
		break;
	}
}

void FNYCCharacterAnimProxy::Update(float DeltaSeconds)
{
	FAnimInstanceProxy::Update(DeltaSeconds);
	UpdateStateMachine(DeltaSeconds);
	SelectClips();
	LocomotionTime += DeltaSeconds * PlayRate;
}

bool FNYCCharacterAnimProxy::Evaluate(FPoseContext& Output)
{
	// Writes the locomotion result straight into `Dest`; never copies a pose context, only blends into one.
	auto EvaluateLocomotion = [this, &Output](FPoseContext& Dest) {
		const bool bHasUpper = (UpperA != nullptr || UpperB != nullptr) && TierAlpha > KINDA_SMALL_NUMBER;

		auto EvaluateTier = [this, &Output](UAnimSequence* A, UAnimSequence* B, float DirAlpha, FPoseContext& Into) {
			if (A != nullptr && B != nullptr && A != B && DirAlpha > KINDA_SMALL_NUMBER &&
				DirAlpha < 1.f - KINDA_SMALL_NUMBER)
			{
				FPoseContext PoseA(Output);
				FPoseContext PoseB(Output);
				EvaluateClip(A, LocomotionTime, bLoopLocomotion, PoseA);
				EvaluateClip(B, LocomotionTime, bLoopLocomotion, PoseB);
				const FAnimationPoseData DataA(PoseA);
				const FAnimationPoseData DataB(PoseB);
				FAnimationPoseData OutData(Into);
				FAnimationRuntime::BlendTwoPosesTogether(DataA, DataB, 1.f - DirAlpha, OutData);
			}
			else
			{
				EvaluateClip(DirAlpha >= 0.5f && B != nullptr ? B : A, LocomotionTime, bLoopLocomotion, Into);
			}
		};

		if (!bHasUpper)
		{
			EvaluateTier(LowerA, LowerB, LowerDirAlpha, Dest);
			return;
		}

		FPoseContext LowerPose(Output);
		FPoseContext UpperPose(Output);
		EvaluateTier(LowerA, LowerB, LowerDirAlpha, LowerPose);
		EvaluateTier(UpperA, UpperB, UpperDirAlpha, UpperPose);
		const FAnimationPoseData LowerData(LowerPose);
		const FAnimationPoseData UpperData(UpperPose);
		FAnimationPoseData OutData(Dest);
		FAnimationRuntime::BlendTwoPosesTogether(LowerData, UpperData, 1.f - TierAlpha, OutData);
	};

	if (ActionBlend > KINDA_SMALL_NUMBER && ActionClip != nullptr)
	{
		FPoseContext Locomotion(Output);
		EvaluateLocomotion(Locomotion);

		FPoseContext ActionPose(Output);
		EvaluateClip(ActionClip, ActionTime, /*bLoop*/ false, ActionPose);

		const FAnimationPoseData LocomotionData(Locomotion);
		const FAnimationPoseData ActionData(ActionPose);
		FAnimationPoseData OutData(Output);
		FAnimationRuntime::BlendTwoPosesTogether(LocomotionData, ActionData, 1.f - ActionBlend, OutData);
	}
	else
	{
		EvaluateLocomotion(Output);
	}
	return true;
}

// ---------------------------------------------------------------------------------------------- instance

void UNYCCharacterAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();
	ResolveClips();
}

UAnimSequence* UNYCCharacterAnimInstance::Load(const TCHAR* Id)
{
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	const FString Path = FNYCCharacterContract::AnimationObjectPath(Settings.CharacterAnimationRoot, FName(Id));
	UAnimSequence* Clip = Cast<UAnimSequence>(FSoftObjectPath(Path).TryLoad());
	if (Clip != nullptr)
	{
		Clips.Add(FName(Id), Clip);
	}
	else
	{
		MissingClips.AddUnique(FName(Id));
	}
	return Clip;
}

void UNYCCharacterAnimInstance::ResolveClips()
{
	if (bClipsResolved)
	{
		return;
	}
	bClipsResolved = true;
	Clips.Reset();
	MissingClips.Reset();

	for (const FName& Id : FNYCCharacterContract::AnimationIds())
	{
		Load(*Id.ToString());
	}

	if (MissingClips.Num() > 0)
	{
		TArray<FString> Names;
		for (const FName& Name : MissingClips)
		{
			Names.Add(Name.ToString());
		}
		const bool bCritical = MissingClips.ContainsByPredicate([](const FName& Name) {
			return FNYCCharacterContract::RequiredAnimationIds().Contains(Name);
		});
		const FString Message = FString::Printf(
			TEXT("Character animation: %d of %d clips missing under '%s' (%s)"), MissingClips.Num(),
			FNYCCharacterContract::AnimationIds().Num(), *UNYCGameplaySettings::Get().CharacterAnimationRoot,
			*FString::Join(Names, TEXT(", ")));
		if (bCritical)
		{
			UE_LOG(LogNYCSim, Error, TEXT("%s"), *Message);
		}
		else
		{
			UE_LOG(LogNYCSim, Warning, TEXT("%s"), *Message);
		}
	}
	else
	{
		UE_LOG(LogNYCSim, Log, TEXT("Character animation: all %d clips resolved."),
			   FNYCCharacterContract::AnimationIds().Num());
	}
}

void UNYCCharacterAnimInstance::RequestAction(ENYCCharacterAction InAction)
{
	PendingAction = InAction;
}

FAnimInstanceProxy* UNYCCharacterAnimInstance::CreateAnimInstanceProxy()
{
	return &Proxy;
}

void UNYCCharacterAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy)
{
	(void)InProxy;
}
