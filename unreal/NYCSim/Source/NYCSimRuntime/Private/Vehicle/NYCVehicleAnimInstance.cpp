#include "Vehicle/NYCVehicleAnimInstance.h"

#include "Animation/AnimInstance.h"
#include "BoneContainer.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "Vehicle/NYCVehicleContract.h"

void FNYCVehicleAnimProxy::Initialize(UAnimInstance* InAnimInstance)
{
	FAnimInstanceProxy::Initialize(InAnimInstance);
	bResolved = false;
	if (InAnimInstance != nullptr)
	{
		Resolve(InAnimInstance->GetSkelMeshComponent());
	}
}

void FNYCVehicleAnimProxy::Resolve(const USkeletalMeshComponent* Mesh)
{
	if (Mesh == nullptr || Mesh->GetSkeletalMeshAsset() == nullptr)
	{
		return;
	}
	auto Index = [Mesh](const TCHAR* BoneName) { return Mesh->GetBoneIndex(FName(BoneName)); };

	WheelBone[0] = Index(NYCVehicleBones::WheelFrontLeft);
	WheelBone[1] = Index(NYCVehicleBones::WheelFrontRight);
	WheelBone[2] = Index(NYCVehicleBones::WheelRearLeft);
	WheelBone[3] = Index(NYCVehicleBones::WheelRearRight);

	SteeringWheelBone = Index(NYCVehicleBones::SteeringWheel);

	NeedleBone[0] = Index(NYCVehicleBones::NeedleSpeed);
	NeedleBone[1] = Index(NYCVehicleBones::NeedleRpm);
	NeedleBone[2] = Index(NYCVehicleBones::NeedleFuel);
	NeedleBone[3] = Index(NYCVehicleBones::NeedleTemp);
	GearSelectorBone = Index(NYCVehicleBones::GearSelector);

	DoorBone[0] = Index(NYCVehicleBones::DoorFrontLeft);
	DoorBone[1] = Index(NYCVehicleBones::DoorFrontRight);
	DoorBone[2] = Index(NYCVehicleBones::DoorRearLeft);
	DoorBone[3] = Index(NYCVehicleBones::DoorRearRight);
	HoodBone = Index(NYCVehicleBones::Hood);
	TrunkBone = Index(NYCVehicleBones::Trunk);

	WindowBone[0] = Index(NYCVehicleBones::WindowFrontLeft);
	WindowBone[1] = Index(NYCVehicleBones::WindowFrontRight);
	WindowBone[2] = Index(NYCVehicleBones::WindowRearLeft);
	WindowBone[3] = Index(NYCVehicleBones::WindowRearRight);

	WiperBone[0] = Index(NYCVehicleBones::WiperLeft);
	WiperBone[1] = Index(NYCVehicleBones::WiperRight);
	WiperBone[2] = Index(NYCVehicleBones::WiperRear);

	MirrorBone[0] = Index(NYCVehicleBones::MirrorLeft);
	MirrorBone[1] = Index(NYCVehicleBones::MirrorRight);

	bResolved = true;
}

void FNYCVehicleAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	if (const UNYCVehicleAnimInstance* Instance = Cast<UNYCVehicleAnimInstance>(InAnimInstance))
	{
		State = Instance->AnimState;
	}
	if (!bResolved && InAnimInstance != nullptr)
	{
		Resolve(InAnimInstance->GetSkelMeshComponent());
	}
	BuildDeltas();
}

void FNYCVehicleAnimProxy::BuildDeltas()
{
	Driven.Reset(20);
	auto Add = [this](int32 BoneIndex, const FQuat& Rotation, const FVector& Translation) {
		if (BoneIndex == INDEX_NONE)
		{
			return;
		}
		FDriven Entry;
		Entry.MeshBoneIndex = BoneIndex;
		Entry.Rotation = Rotation;
		Entry.Translation = Translation;
		Driven.Add(Entry);
	};

	// Wheels: roll about local Y, steer about local Z (NYCVehicleContract.h bone-axis table). The suspension
	// displacement moves the wheel bone up along local Z.
	for (int32 i = 0; i < 4; ++i)
	{
		const FQuat Roll(FVector::YAxisVector, FMath::DegreesToRadians(State.WheelSpinDeg[i]));
		const FQuat Steer(FVector::ZAxisVector, FMath::DegreesToRadians(State.WheelSteerDeg[i]));
		Add(WheelBone[i], Steer * Roll, FVector(0.f, 0.f, State.WheelSuspensionCm[i]));
	}

	Add(SteeringWheelBone, FQuat(FVector::XAxisVector, FMath::DegreesToRadians(State.SteeringWheelDeg)),
		FVector::ZeroVector);

	const float NeedleDeg[4] = {State.NeedleSpeedDeg, State.NeedleRpmDeg, State.NeedleFuelDeg, State.NeedleTempDeg};
	for (int32 i = 0; i < 4; ++i)
	{
		Add(NeedleBone[i], FQuat(FVector::XAxisVector, FMath::DegreesToRadians(NeedleDeg[i])), FVector::ZeroVector);
	}
	Add(GearSelectorBone, FQuat(FVector::XAxisVector, FMath::DegreesToRadians(State.GearSelectorDeg)),
		FVector::ZeroVector);

	for (int32 i = 0; i < 4; ++i)
	{
		Add(DoorBone[i], FQuat(FVector::ZAxisVector, FMath::DegreesToRadians(State.DoorDeg[i])), FVector::ZeroVector);
		Add(WindowBone[i], FQuat::Identity, FVector(0.f, 0.f, -State.WindowDropCm[i]));
	}
	Add(HoodBone, FQuat(FVector::YAxisVector, FMath::DegreesToRadians(State.HoodDeg)), FVector::ZeroVector);
	Add(TrunkBone, FQuat(FVector::YAxisVector, FMath::DegreesToRadians(State.TrunkDeg)), FVector::ZeroVector);

	for (int32 i = 0; i < 3; ++i)
	{
		Add(WiperBone[i], FQuat(FVector::ZAxisVector, FMath::DegreesToRadians(State.WiperDeg[i])), FVector::ZeroVector);
	}
	for (int32 i = 0; i < 2; ++i)
	{
		Add(MirrorBone[i], FQuat(FVector::ZAxisVector, FMath::DegreesToRadians(State.MirrorFoldDeg[i])),
			FVector::ZeroVector);
	}
}

bool FNYCVehicleAnimProxy::Evaluate(FPoseContext& Output)
{
	Output.ResetToRefPose();
	if (Driven.Num() == 0)
	{
		return true;
	}

	const FBoneContainer& BoneContainer = Output.Pose.GetBoneContainer();
	for (const FDriven& Entry : Driven)
	{
		if (Entry.MeshBoneIndex == INDEX_NONE)
		{
			continue;
		}
		const FCompactPoseBoneIndex CompactIndex =
			BoneContainer.MakeCompactPoseIndex(FMeshPoseBoneIndex(Entry.MeshBoneIndex));
		if (CompactIndex.GetInt() == INDEX_NONE || !Output.Pose.IsValidIndex(CompactIndex))
		{
			continue;
		}
		FTransform& Bone = Output.Pose[CompactIndex];
		// Deltas are applied in the bone's own space on top of the reference pose, so the rig's rest position is
		// always the closed / parked / zero state.
		Bone.SetRotation(Bone.GetRotation() * Entry.Rotation);
		Bone.AddToTranslation(Entry.Translation);
		Bone.NormalizeRotation();
	}
	return true;
}

FAnimInstanceProxy* UNYCVehicleAnimInstance::CreateAnimInstanceProxy()
{
	return &Proxy;
}

void UNYCVehicleAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy)
{
	// The proxy is a member, not a heap allocation: nothing to free.
	(void)InProxy;
}
