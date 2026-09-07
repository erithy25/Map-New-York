#include "Peds/NYCPedestrian.h"

#include "Animation/AnimSequence.h"
#include "Character/NYCCharacterContract.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "CoreAdapter/GameplayPedSim.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NYCSimRuntime.h"

namespace
{
/// Nominal stride of the walk clip, metres per second, used to derive the play rate from the agent's speed.
constexpr float kWalkClipSpeedMps = 1.34f;
}  // namespace

ANYCPedestrian::ANYCPedestrian()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->bEnableUpdateRateOptimizations = true;
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	// The crowd skeleton's root is at the feet with +X forward, like the UE5 Mannequin.
	Mesh->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));

	Umbrella = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Umbrella"));
	Umbrella->SetupAttachment(Mesh, FName(NYCCharacterBones::HandRight));
	Umbrella->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Umbrella->SetVisibility(false);

	Bag = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Bag"));
	Bag->SetupAttachment(Mesh, FName(NYCCharacterBones::HandLeft));
	Bag->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Bag->SetVisibility(false);

	Phone = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Phone"));
	Phone->SetupAttachment(Mesh, FName(NYCCharacterBones::HandRight));
	Phone->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Phone->SetVisibility(false);

	SetActorHiddenInGame(true);
}

void ANYCPedestrian::SetClips(UAnimSequence* InWalk, UAnimSequence* InIdle)
{
	WalkClip = InWalk;
	IdleClip = InIdle;
}

void ANYCPedestrian::SetProps(UStaticMesh* InUmbrella, UStaticMesh* InBag, UStaticMesh* InPhone)
{
	if (Umbrella != nullptr && InUmbrella != nullptr)
	{
		Umbrella->SetStaticMesh(InUmbrella);
	}
	if (Bag != nullptr && InBag != nullptr)
	{
		Bag->SetStaticMesh(InBag);
	}
	if (Phone != nullptr && InPhone != nullptr)
	{
		Phone->SetStaticMesh(InPhone);
	}
}

void ANYCPedestrian::Acquire(int32 InAgentId, USkeletalMesh* InMesh, uint8 InArchetype, uint8 InVariant)
{
	AgentId = InAgentId;
	const bool bMeshChanged = Mesh->GetSkeletalMeshAsset() != InMesh;
	Archetype = InArchetype;
	Variant = InVariant;

	if (bMeshChanged)
	{
		Mesh->SetSkeletalMesh(InMesh);
		bPlayingWalk = false;
	}

	// The colour variant drives the clothing material's palette parameters, so two agents with the same body do
	// not look identical (ARCHITECTURE §10: no duplicates within 60 m, which the simulation guarantees).
	const int32 SlotCount = Mesh->GetMaterialSlotNames().Num();
	for (int32 i = 0; i < SlotCount; ++i)
	{
		if (UMaterialInstanceDynamic* Dynamic = Mesh->CreateDynamicMaterialInstance(i))
		{
			Dynamic->SetScalarParameterValue(FName(NYCCharacterParams::ClothingVariant),
											 static_cast<float>(Variant) / 255.f);
			Dynamic->SetScalarParameterValue(FName(NYCCharacterParams::BodyVariant),
											 static_cast<float>(Archetype) / 255.f);
		}
	}

	LodLevel = 0;
	CurrentFlags = 0xFF;  // force a prop refresh on the first ApplyState
	SetActorHiddenInGame(false);
	Mesh->SetVisibility(true, true);
}

void ANYCPedestrian::Release()
{
	AgentId = 0;
	SetActorHiddenInGame(true);
	Mesh->SetVisibility(false, true);
	Umbrella->SetVisibility(false);
	Bag->SetVisibility(false);
	Phone->SetVisibility(false);
	Mesh->Stop();
	bPlayingWalk = false;
	SetActorLocation(FVector(0.f, 0.f, -100000.f));
}

void ANYCPedestrian::UpdateProps(uint8 Flags)
{
	if (Flags == CurrentFlags)
	{
		return;
	}
	CurrentFlags = Flags;
	const bool bVisible = LodLevel <= 1;
	Umbrella->SetVisibility(bVisible && (Flags & nycsim_gameplay::kPedUmbrella) != 0);
	Bag->SetVisibility(bVisible && (Flags & nycsim_gameplay::kPedBag) != 0);
	Phone->SetVisibility(bVisible && (Flags & nycsim_gameplay::kPedPhone) != 0);
}

void ANYCPedestrian::SetLodLevel(int32 Level)
{
	Level = FMath::Clamp(Level, 0, 3);
	if (Level == LodLevel)
	{
		return;
	}
	LodLevel = Level;
	switch (LodLevel)
	{
	case 0:
		Mesh->SetVisibility(true, true);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		break;
	case 1:
		Mesh->SetVisibility(true, true);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
		break;
	case 2:
		Mesh->SetVisibility(true, true);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickMontagesWhenNotRendered;
		Umbrella->SetVisibility(false);
		Bag->SetVisibility(false);
		Phone->SetVisibility(false);
		break;
	default:
		Mesh->SetVisibility(false, true);
		Umbrella->SetVisibility(false);
		Bag->SetVisibility(false);
		Phone->SetVisibility(false);
		break;
	}
}

void ANYCPedestrian::ApplyState(const FNYCPedestrianState& State, float DeltaTime, bool bTeleport)
{
	if (bTeleport)
	{
		SmoothedLocation = State.Location;
		SmoothedRotation = State.Rotation;
	}
	else
	{
		SmoothedLocation = FMath::VInterpTo(SmoothedLocation, State.Location, DeltaTime, 16.f);
		SmoothedRotation = FMath::RInterpTo(SmoothedRotation, State.Rotation, DeltaTime, 10.f);
	}
	SetActorLocationAndRotation(SmoothedLocation, SmoothedRotation);

	UpdateProps(State.Flags);

	if (LodLevel >= 3)
	{
		return;
	}

	const bool bWalking = State.SpeedMps > 0.15f;
	if (bWalking != bPlayingWalk || Mesh->GetSingleNodeInstance() == nullptr)
	{
		UAnimSequence* Clip = bWalking ? WalkClip.Get() : IdleClip.Get();
		if (Clip != nullptr)
		{
			Mesh->PlayAnimation(Clip, /*bLooping*/ true);
			bPlayingWalk = bWalking;
		}
	}
	if (bWalking)
	{
		// Play rate follows the agent's speed so the feet do not slide: the clip was authored at 1.34 m/s.
		Mesh->SetPlayRate(FMath::Clamp(State.SpeedMps / kWalkClipSpeedMps, 0.55f, 1.9f));
	}
}
