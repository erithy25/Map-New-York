#include "Character/NYCCharacterContract.h"

#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

const TArray<FName>& FNYCCharacterContract::RequiredBones()
{
	static const TArray<FName> Bones = {
		FName(NYCCharacterBones::Root),          FName(NYCCharacterBones::Pelvis),
		FName(NYCCharacterBones::Spine01),       FName(NYCCharacterBones::Spine02),
		FName(NYCCharacterBones::Spine03),       FName(NYCCharacterBones::Neck01),
		FName(NYCCharacterBones::Head),          FName(NYCCharacterBones::ClavicleLeft),
		FName(NYCCharacterBones::ClavicleRight), FName(NYCCharacterBones::UpperArmLeft),
		FName(NYCCharacterBones::UpperArmRight), FName(NYCCharacterBones::LowerArmLeft),
		FName(NYCCharacterBones::LowerArmRight), FName(NYCCharacterBones::HandLeft),
		FName(NYCCharacterBones::HandRight),     FName(NYCCharacterBones::ThighLeft),
		FName(NYCCharacterBones::ThighRight),    FName(NYCCharacterBones::CalfLeft),
		FName(NYCCharacterBones::CalfRight),     FName(NYCCharacterBones::FootLeft),
		FName(NYCCharacterBones::FootRight),
	};
	return Bones;
}

const TArray<FName>& FNYCCharacterContract::OptionalBones()
{
	static const TArray<FName> Bones = {
		FName(NYCCharacterBones::Spine04),    FName(NYCCharacterBones::Spine05),
		FName(NYCCharacterBones::Neck02),     FName(NYCCharacterBones::BallLeft),
		FName(NYCCharacterBones::BallRight),  FName(NYCCharacterBones::IkFootRoot),
		FName(NYCCharacterBones::IkFootLeft), FName(NYCCharacterBones::IkFootRight),
		FName(NYCCharacterBones::IkHandRoot), FName(NYCCharacterBones::IkHandGun),
		FName(NYCCharacterBones::IkHandLeft), FName(NYCCharacterBones::IkHandRight),
	};
	return Bones;
}

const TArray<FName>& FNYCCharacterContract::AnimationIds()
{
	static const TArray<FName> Ids = {
		FName(NYCCharacterAnims::Idle),           FName(NYCCharacterAnims::IdleLookAround),
		FName(NYCCharacterAnims::WalkForward),    FName(NYCCharacterAnims::WalkBackward),
		FName(NYCCharacterAnims::WalkLeft),       FName(NYCCharacterAnims::WalkRight),
		FName(NYCCharacterAnims::JogForward),     FName(NYCCharacterAnims::JogBackward),
		FName(NYCCharacterAnims::JogLeft),        FName(NYCCharacterAnims::JogRight),
		FName(NYCCharacterAnims::SprintForward),  FName(NYCCharacterAnims::JogStart),
		FName(NYCCharacterAnims::JogStop),        FName(NYCCharacterAnims::TurnLeft90),
		FName(NYCCharacterAnims::TurnRight90),    FName(NYCCharacterAnims::TurnLeft180),
		FName(NYCCharacterAnims::TurnRight180),   FName(NYCCharacterAnims::JumpStart),
		FName(NYCCharacterAnims::JumpLoop),       FName(NYCCharacterAnims::JumpLand),
		FName(NYCCharacterAnims::FallLoop),       FName(NYCCharacterAnims::LandHard),
		FName(NYCCharacterAnims::CrouchIdle),     FName(NYCCharacterAnims::CrouchWalk),
		FName(NYCCharacterAnims::EnterVehicleLeft), FName(NYCCharacterAnims::EnterVehicleRight),
		FName(NYCCharacterAnims::ExitVehicleLeft),  FName(NYCCharacterAnims::ExitVehicleRight),
		FName(NYCCharacterAnims::SitDrive),       FName(NYCCharacterAnims::SitIdle),
		FName(NYCCharacterAnims::SteerLeft),      FName(NYCCharacterAnims::SteerRight),
		FName(NYCCharacterAnims::OpenDoor),       FName(NYCCharacterAnims::CloseDoor),
		FName(NYCCharacterAnims::CheckPhone),     FName(NYCCharacterAnims::Point),
		FName(NYCCharacterAnims::Talk),           FName(NYCCharacterAnims::PressButton),
		FName(NYCCharacterAnims::Shiver),         FName(NYCCharacterAnims::HoldUmbrella),
	};
	return Ids;
}

const TArray<FName>& FNYCCharacterContract::RequiredAnimationIds()
{
	static const TArray<FName> Ids = {
		FName(NYCCharacterAnims::Idle),
		FName(NYCCharacterAnims::WalkForward),
		FName(NYCCharacterAnims::JogForward),
	};
	return Ids;
}

FString FNYCCharacterContract::AnimationObjectPath(const FString& AnimationRoot, FName Id)
{
	const FString Name = FString::Printf(TEXT("AS_%s"), *Id.ToString());
	FString Root = AnimationRoot;
	Root.RemoveFromEnd(TEXT("/"));
	return FString::Printf(TEXT("%s/%s.%s"), *Root, *Name, *Name);
}

TArray<FName> FNYCCharacterContract::MissingBones(const USkeletalMeshComponent* Mesh)
{
	TArray<FName> Missing;
	if (Mesh == nullptr || Mesh->GetSkeletalMeshAsset() == nullptr)
	{
		Missing.Add(FName(TEXT("<no skeletal mesh>")));
		return Missing;
	}
	for (const FName& Bone : RequiredBones())
	{
		if (Mesh->GetBoneIndex(Bone) == INDEX_NONE)
		{
			Missing.Add(Bone);
		}
	}
	return Missing;
}
