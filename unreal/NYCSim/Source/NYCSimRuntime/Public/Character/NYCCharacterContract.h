// The character rig and animation contract between Blender (blender/character/**) and Unreal.
//
// The skeleton uses the UE5 Mannequin naming (ADR-010: the character is built from MakeHuman/MPFB2 CC0 assets and
// retargeted onto the Mannequin hierarchy), so the same animation set drives the player, the crowd and any future
// third-party clip without a retarget asset. Everything the runtime binds to is listed here by name; the Blender
// export and the UE import script both validate against these lists.
//
// Animation clips live under UNYCGameplaySettings::CharacterAnimationRoot as `AS_<id>`, e.g. AS_Walk_Fwd. Missing
// clips are reported once by name and the state machine falls back to the nearest clip it does have, so a partial
// animation set still produces a walking character rather than a T-pose.
#pragma once

#include "CoreMinimal.h"

/** UE5-Mannequin bone names the runtime addresses directly. */
namespace NYCCharacterBones
{
	inline const TCHAR* const Root = TEXT("root");
	inline const TCHAR* const Pelvis = TEXT("pelvis");
	inline const TCHAR* const Spine01 = TEXT("spine_01");
	inline const TCHAR* const Spine02 = TEXT("spine_02");
	inline const TCHAR* const Spine03 = TEXT("spine_03");
	inline const TCHAR* const Spine04 = TEXT("spine_04");
	inline const TCHAR* const Spine05 = TEXT("spine_05");
	inline const TCHAR* const Neck01 = TEXT("neck_01");
	inline const TCHAR* const Neck02 = TEXT("neck_02");
	inline const TCHAR* const Head = TEXT("head");

	inline const TCHAR* const ClavicleLeft = TEXT("clavicle_l");
	inline const TCHAR* const ClavicleRight = TEXT("clavicle_r");
	inline const TCHAR* const UpperArmLeft = TEXT("upperarm_l");
	inline const TCHAR* const UpperArmRight = TEXT("upperarm_r");
	inline const TCHAR* const LowerArmLeft = TEXT("lowerarm_l");
	inline const TCHAR* const LowerArmRight = TEXT("lowerarm_r");
	inline const TCHAR* const HandLeft = TEXT("hand_l");
	inline const TCHAR* const HandRight = TEXT("hand_r");

	inline const TCHAR* const ThighLeft = TEXT("thigh_l");
	inline const TCHAR* const ThighRight = TEXT("thigh_r");
	inline const TCHAR* const CalfLeft = TEXT("calf_l");
	inline const TCHAR* const CalfRight = TEXT("calf_r");
	inline const TCHAR* const FootLeft = TEXT("foot_l");
	inline const TCHAR* const FootRight = TEXT("foot_r");
	inline const TCHAR* const BallLeft = TEXT("ball_l");
	inline const TCHAR* const BallRight = TEXT("ball_r");

	// IK bones the Mannequin carries and the vehicle pose uses to plant hands on the wheel and feet on the pedals.
	inline const TCHAR* const IkFootRoot = TEXT("ik_foot_root");
	inline const TCHAR* const IkFootLeft = TEXT("ik_foot_l");
	inline const TCHAR* const IkFootRight = TEXT("ik_foot_r");
	inline const TCHAR* const IkHandRoot = TEXT("ik_hand_root");
	inline const TCHAR* const IkHandGun = TEXT("ik_hand_gun");
	inline const TCHAR* const IkHandLeft = TEXT("ik_hand_l");
	inline const TCHAR* const IkHandRight = TEXT("ik_hand_r");

	// Sockets the gameplay attaches to.
	inline const TCHAR* const SocketHead = TEXT("SKT_HeadCamera");
	inline const TCHAR* const SocketHandRight = TEXT("SKT_HandR");
	inline const TCHAR* const SocketHandLeft = TEXT("SKT_HandL");
	inline const TCHAR* const SocketBack = TEXT("SKT_Back");
}

/** Animation clip ids. `AS_<id>` under CharacterAnimationRoot. */
namespace NYCCharacterAnims
{
	// Locomotion.
	inline const TCHAR* const Idle = TEXT("Idle");
	inline const TCHAR* const IdleLookAround = TEXT("Idle_LookAround");
	inline const TCHAR* const WalkForward = TEXT("Walk_Fwd");
	inline const TCHAR* const WalkBackward = TEXT("Walk_Bwd");
	inline const TCHAR* const WalkLeft = TEXT("Walk_Left");
	inline const TCHAR* const WalkRight = TEXT("Walk_Right");
	inline const TCHAR* const JogForward = TEXT("Jog_Fwd");
	inline const TCHAR* const JogBackward = TEXT("Jog_Bwd");
	inline const TCHAR* const JogLeft = TEXT("Jog_Left");
	inline const TCHAR* const JogRight = TEXT("Jog_Right");
	inline const TCHAR* const SprintForward = TEXT("Sprint_Fwd");
	inline const TCHAR* const JogStart = TEXT("Jog_Start");
	inline const TCHAR* const JogStop = TEXT("Jog_Stop");

	// Turn in place.
	inline const TCHAR* const TurnLeft90 = TEXT("Turn_L_90");
	inline const TCHAR* const TurnRight90 = TEXT("Turn_R_90");
	inline const TCHAR* const TurnLeft180 = TEXT("Turn_L_180");
	inline const TCHAR* const TurnRight180 = TEXT("Turn_R_180");

	// Air.
	inline const TCHAR* const JumpStart = TEXT("Jump_Start");
	inline const TCHAR* const JumpLoop = TEXT("Jump_Loop");
	inline const TCHAR* const JumpLand = TEXT("Jump_Land");
	inline const TCHAR* const FallLoop = TEXT("Fall_Loop");
	inline const TCHAR* const LandHard = TEXT("Land_Hard");

	// Crouch.
	inline const TCHAR* const CrouchIdle = TEXT("Crouch_Idle");
	inline const TCHAR* const CrouchWalk = TEXT("Crouch_Walk");

	// Vehicle.
	inline const TCHAR* const EnterVehicleLeft = TEXT("Vehicle_Enter_L");
	inline const TCHAR* const EnterVehicleRight = TEXT("Vehicle_Enter_R");
	inline const TCHAR* const ExitVehicleLeft = TEXT("Vehicle_Exit_L");
	inline const TCHAR* const ExitVehicleRight = TEXT("Vehicle_Exit_R");
	inline const TCHAR* const SitDrive = TEXT("Vehicle_Sit_Drive");
	inline const TCHAR* const SitIdle = TEXT("Vehicle_Sit_Idle");
	inline const TCHAR* const SteerLeft = TEXT("Vehicle_Steer_L");
	inline const TCHAR* const SteerRight = TEXT("Vehicle_Steer_R");
	inline const TCHAR* const OpenDoor = TEXT("Door_Open");
	inline const TCHAR* const CloseDoor = TEXT("Door_Close");

	// Incidental.
	inline const TCHAR* const CheckPhone = TEXT("Check_Phone");
	inline const TCHAR* const Point = TEXT("Point");
	inline const TCHAR* const Talk = TEXT("Talk");
	inline const TCHAR* const PressButton = TEXT("Press_Button");
	inline const TCHAR* const Shiver = TEXT("Shiver");
	inline const TCHAR* const HoldUmbrella = TEXT("Hold_Umbrella");
}

/** Material parameters on the character's clothing/skin materials. */
namespace NYCCharacterParams
{
	inline const TCHAR* const BodyVariant = TEXT("BodyVariant");
	inline const TCHAR* const ClothingVariant = TEXT("ClothingVariant");
	inline const TCHAR* const SkinTone = TEXT("SkinTone");
	inline const TCHAR* const Wetness = TEXT("Wetness");
}

/** Morph target (ARKit blendshape) names used for the face; the full ARKit 52 are present on the rig. */
namespace NYCCharacterMorphs
{
	inline const TCHAR* const EyeBlinkLeft = TEXT("eyeBlinkLeft");
	inline const TCHAR* const EyeBlinkRight = TEXT("eyeBlinkRight");
	inline const TCHAR* const JawOpen = TEXT("jawOpen");
	inline const TCHAR* const MouthSmileLeft = TEXT("mouthSmileLeft");
	inline const TCHAR* const MouthSmileRight = TEXT("mouthSmileRight");
	inline const TCHAR* const BrowInnerUp = TEXT("browInnerUp");
	inline const TCHAR* const EyeLookInLeft = TEXT("eyeLookInLeft");
	inline const TCHAR* const EyeLookOutLeft = TEXT("eyeLookOutLeft");
	inline const TCHAR* const EyeLookInRight = TEXT("eyeLookInRight");
	inline const TCHAR* const EyeLookOutRight = TEXT("eyeLookOutRight");
	inline const TCHAR* const EyeLookUpLeft = TEXT("eyeLookUpLeft");
	inline const TCHAR* const EyeLookDownLeft = TEXT("eyeLookDownLeft");
	inline const TCHAR* const EyeLookUpRight = TEXT("eyeLookUpRight");
	inline const TCHAR* const EyeLookDownRight = TEXT("eyeLookDownRight");
}

/** Helpers shared by the player character, the crowd and the editor validation. */
class NYCSIMRUNTIME_API FNYCCharacterContract
{
public:
	/** Bones every clip and every runtime feature needs. */
	static const TArray<FName>& RequiredBones();
	/** IK bones and sockets used when present. */
	static const TArray<FName>& OptionalBones();
	/** Every animation clip id the locomotion machine and the vehicle sequence can use. */
	static const TArray<FName>& AnimationIds();
	/** Clips without which the character cannot move convincingly. */
	static const TArray<FName>& RequiredAnimationIds();

	/** `AS_<id>` in the configured animation directory, as a package path. */
	static FString AnimationObjectPath(const FString& AnimationRoot, FName Id);

	/** Checks a mesh's skeleton against RequiredBones(); returns the missing ones. */
	static TArray<FName> MissingBones(const class USkeletalMeshComponent* Mesh);
};
