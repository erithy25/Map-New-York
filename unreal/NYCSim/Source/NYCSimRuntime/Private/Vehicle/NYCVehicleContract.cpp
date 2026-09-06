#include "Vehicle/NYCVehicleContract.h"

#include "Components/MeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkinnedAssetCommon.h"
#include "NYCSimRuntime.h"
#include "ReferenceSkeleton.h"

FString FNYCVehicleContractReport::ToText() const
{
	TStringBuilder<512> Builder;
	Builder.Appendf(TEXT("bones %d ok"), FoundBones);
	if (MissingBones.Num() > 0)
	{
		Builder.Appendf(TEXT(", %d missing (%s)"), MissingBones.Num(), *FString::Join(MissingBones, TEXT(", ")));
	}
	Builder.Appendf(TEXT("; slots %d ok"), FoundSlots);
	if (MissingSlots.Num() > 0)
	{
		Builder.Appendf(TEXT(", %d missing (%s)"), MissingSlots.Num(), *FString::Join(MissingSlots, TEXT(", ")));
	}
	if (MissingSockets.Num() > 0)
	{
		Builder.Appendf(TEXT("; sockets missing (%s)"), *FString::Join(MissingSockets, TEXT(", ")));
	}
	return Builder.ToString();
}

const TArray<FName>& FNYCVehicleContract::RequiredBones()
{
	static const TArray<FName> Bones = {
		FName(NYCVehicleBones::Body),
		FName(NYCVehicleBones::WheelFrontLeft), FName(NYCVehicleBones::WheelFrontRight),
		FName(NYCVehicleBones::WheelRearLeft), FName(NYCVehicleBones::WheelRearRight),
		FName(NYCVehicleBones::DoorFrontLeft), FName(NYCVehicleBones::DoorFrontRight),
		FName(NYCVehicleBones::SteeringWheel),
	};
	return Bones;
}

const TArray<FName>& FNYCVehicleContract::OptionalBones()
{
	static const TArray<FName> Bones = {
		FName(NYCVehicleBones::DoorRearLeft), FName(NYCVehicleBones::DoorRearRight),
		FName(NYCVehicleBones::Hood), FName(NYCVehicleBones::Trunk), FName(NYCVehicleBones::FuelFlap),
		FName(NYCVehicleBones::WiperLeft), FName(NYCVehicleBones::WiperRight), FName(NYCVehicleBones::WiperRear),
		FName(NYCVehicleBones::WindowFrontLeft), FName(NYCVehicleBones::WindowFrontRight),
		FName(NYCVehicleBones::WindowRearLeft), FName(NYCVehicleBones::WindowRearRight),
		FName(NYCVehicleBones::MirrorLeft), FName(NYCVehicleBones::MirrorRight),
		FName(NYCVehicleBones::MirrorInterior),
		FName(NYCVehicleBones::NeedleSpeed), FName(NYCVehicleBones::NeedleRpm),
		FName(NYCVehicleBones::NeedleFuel), FName(NYCVehicleBones::NeedleTemp),
		FName(NYCVehicleBones::GearSelector), FName(NYCVehicleBones::TurnStalk), FName(NYCVehicleBones::WiperStalk),
	};
	return Bones;
}

const TArray<FName>& FNYCVehicleContract::RequiredSockets()
{
	static const TArray<FName> Sockets = {
		FName(NYCVehicleBones::SocketDriverSeat),
		FName(NYCVehicleBones::SocketCameraChase),
		FName(NYCVehicleBones::SocketCameraInterior),
	};
	return Sockets;
}

const TArray<FName>& FNYCVehicleContract::OptionalSockets()
{
	static const TArray<FName> Sockets = {
		FName(NYCVehicleBones::SocketPassengerSeat), FName(NYCVehicleBones::SocketDriverEntry),
		FName(NYCVehicleBones::SocketCameraHood), FName(NYCVehicleBones::SocketCameraBumper),
		FName(NYCVehicleBones::SocketExhaustLeft), FName(NYCVehicleBones::SocketExhaustRight),
		FName(NYCVehicleBones::SocketEngineBay), FName(NYCVehicleBones::SocketPlateFront),
		FName(NYCVehicleBones::SocketPlateRear), FName(NYCVehicleBones::SocketHorn),
		FName(NYCVehicleBones::SocketRoofLight), FName(NYCVehicleBones::SocketDestinationSign),
	};
	return Sockets;
}

const TArray<FName>& FNYCVehicleContract::LightSlots()
{
	static const TArray<FName> Slots = {
		FName(NYCVehicleSlots::HeadLeft), FName(NYCVehicleSlots::HeadRight),
		FName(NYCVehicleSlots::HighBeamLeft), FName(NYCVehicleSlots::HighBeamRight),
		FName(NYCVehicleSlots::DrlLeft), FName(NYCVehicleSlots::DrlRight),
		FName(NYCVehicleSlots::FogLeft), FName(NYCVehicleSlots::FogRight),
		FName(NYCVehicleSlots::TailLeft), FName(NYCVehicleSlots::TailRight),
		FName(NYCVehicleSlots::BrakeLeft), FName(NYCVehicleSlots::BrakeRight), FName(NYCVehicleSlots::BrakeCentre),
		FName(NYCVehicleSlots::ReverseLeft), FName(NYCVehicleSlots::ReverseRight),
		FName(NYCVehicleSlots::IndicatorFrontLeft), FName(NYCVehicleSlots::IndicatorFrontRight),
		FName(NYCVehicleSlots::IndicatorRearLeft), FName(NYCVehicleSlots::IndicatorRearRight),
		FName(NYCVehicleSlots::IndicatorSideLeft), FName(NYCVehicleSlots::IndicatorSideRight),
		FName(NYCVehicleSlots::PlateLight), FName(NYCVehicleSlots::InteriorLight),
		FName(NYCVehicleSlots::DashBacklight),
	};
	return Slots;
}

const TArray<FName>& FNYCVehicleContract::InstrumentSlots()
{
	static const TArray<FName> Slots = {
		FName(NYCVehicleSlots::GaugeSpeed), FName(NYCVehicleSlots::GaugeRpm), FName(NYCVehicleSlots::GaugeFuel),
		FName(NYCVehicleSlots::ScreenCentre), FName(NYCVehicleSlots::ScreenCluster),
	};
	return Slots;
}

const TArray<FName>& FNYCVehicleContract::DamageSlots()
{
	static const TArray<FName> Slots = {
		FName(NYCVehicleSlots::DamageFront), FName(NYCVehicleSlots::DamageRear), FName(NYCVehicleSlots::DamageLeft),
		FName(NYCVehicleSlots::DamageRight), FName(NYCVehicleSlots::DamageRoof),
	};
	return Slots;
}

FName FNYCVehicleContract::WheelBone(int32 WheelIndex)
{
	switch (WheelIndex)
	{
	case 0: return FName(NYCVehicleBones::WheelFrontLeft);
	case 1: return FName(NYCVehicleBones::WheelFrontRight);
	case 2: return FName(NYCVehicleBones::WheelRearLeft);
	case 3: return FName(NYCVehicleBones::WheelRearRight);
	default: return NAME_None;
	}
}

FName FNYCVehicleContract::DoorBone(int32 DoorIndex)
{
	switch (DoorIndex)
	{
	case 0: return FName(NYCVehicleBones::DoorFrontLeft);
	case 1: return FName(NYCVehicleBones::DoorFrontRight);
	case 2: return FName(NYCVehicleBones::DoorRearLeft);
	case 3: return FName(NYCVehicleBones::DoorRearRight);
	default: return NAME_None;
	}
}

FName FNYCVehicleContract::DamageSlot(ENYCDamageRegion Region)
{
	switch (Region)
	{
	case ENYCDamageRegion::Front: return FName(NYCVehicleSlots::DamageFront);
	case ENYCDamageRegion::Rear: return FName(NYCVehicleSlots::DamageRear);
	case ENYCDamageRegion::Left: return FName(NYCVehicleSlots::DamageLeft);
	case ENYCDamageRegion::Right: return FName(NYCVehicleSlots::DamageRight);
	case ENYCDamageRegion::Roof: return FName(NYCVehicleSlots::DamageRoof);
	default: return NAME_None;
	}
}

FName FNYCVehicleContract::DamageMorph(ENYCDamageRegion Region)
{
	switch (Region)
	{
	case ENYCDamageRegion::Front: return FName(NYCVehicleMorphs::DentFront);
	case ENYCDamageRegion::Rear: return FName(NYCVehicleMorphs::DentRear);
	case ENYCDamageRegion::Left: return FName(NYCVehicleMorphs::DentLeft);
	case ENYCDamageRegion::Right: return FName(NYCVehicleMorphs::DentRight);
	case ENYCDamageRegion::Roof: return FName(NYCVehicleMorphs::DentRoof);
	default: return NAME_None;
	}
}

bool FNYCVehicleContract::IsCollisionName(FName Name)
{
	return Name.ToString().StartsWith(TEXT("UCX_"), ESearchCase::CaseSensitive);
}

int32 FNYCVehicleContract::SlotIndex(const UMeshComponent* Mesh, FName SlotName)
{
	if (Mesh == nullptr || SlotName.IsNone())
	{
		return INDEX_NONE;
	}
	const TArray<FName> Names = Mesh->GetMaterialSlotNames();
	return Names.IndexOfByKey(SlotName);
}

FNYCVehicleContractReport FNYCVehicleContract::Validate(const USkeletalMeshComponent* Mesh)
{
	FNYCVehicleContractReport Report;
	if (Mesh == nullptr || Mesh->GetSkeletalMeshAsset() == nullptr)
	{
		Report.MissingBones.Add(TEXT("<no skeletal mesh>"));
		return Report;
	}

	for (const FName& Bone : RequiredBones())
	{
		if (Mesh->GetBoneIndex(Bone) == INDEX_NONE)
		{
			Report.MissingBones.Add(Bone.ToString());
		}
		else
		{
			++Report.FoundBones;
		}
	}
	for (const FName& Bone : OptionalBones())
	{
		if (Mesh->GetBoneIndex(Bone) != INDEX_NONE)
		{
			++Report.FoundBones;
		}
	}
	for (const FName& Socket : RequiredSockets())
	{
		if (!Mesh->DoesSocketExist(Socket))
		{
			Report.MissingSockets.Add(Socket.ToString());
		}
	}

	const TArray<FName> SlotNames = Mesh->GetMaterialSlotNames();
	auto CheckSlots = [&SlotNames, &Report](const TArray<FName>& Wanted, bool bRequired) {
		for (const FName& Slot : Wanted)
		{
			if (SlotNames.Contains(Slot))
			{
				++Report.FoundSlots;
			}
			else if (bRequired)
			{
				Report.MissingSlots.Add(Slot.ToString());
			}
		}
	};
	// Light and instrument slots are optional per vehicle body (a bicycle has none); the damage slots are the only
	// ones the player vehicle cannot do without, because the damage model addresses them by name.
	CheckSlots(LightSlots(), /*bRequired*/ false);
	CheckSlots(InstrumentSlots(), /*bRequired*/ false);
	CheckSlots(DamageSlots(), /*bRequired*/ false);

	// A UCX_ hull that survived import as a render section means the importer was misconfigured.
	for (const FName& Slot : SlotNames)
	{
		if (IsCollisionName(Slot))
		{
			Report.MissingSlots.Add(FString::Printf(TEXT("<collision hull %s left in render mesh>"), *Slot.ToString()));
		}
	}
	return Report;
}
