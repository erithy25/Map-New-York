#include "Vehicle/NYCVehicleDamageComponent.h"

#include "CoreAdapter/GameplayVehicleDynamics.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NYCSimRuntime.h"
#include "Vehicle/NYCVehicleLightsComponent.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

namespace
{
constexpr int32 kRegionCount = static_cast<int32>(ENYCDamageRegion::Count);

/// Lamp slots that live inside each damage region.
const TArray<FName>& LampsInRegion(ENYCDamageRegion Region)
{
	static const TArray<FName> Front = {
		FName(NYCVehicleSlots::HeadLeft), FName(NYCVehicleSlots::HeadRight),
		FName(NYCVehicleSlots::HighBeamLeft), FName(NYCVehicleSlots::HighBeamRight),
		FName(NYCVehicleSlots::DrlLeft), FName(NYCVehicleSlots::DrlRight),
		FName(NYCVehicleSlots::FogLeft), FName(NYCVehicleSlots::FogRight),
		FName(NYCVehicleSlots::IndicatorFrontLeft), FName(NYCVehicleSlots::IndicatorFrontRight)};
	static const TArray<FName> Rear = {
		FName(NYCVehicleSlots::TailLeft), FName(NYCVehicleSlots::TailRight),
		FName(NYCVehicleSlots::BrakeLeft), FName(NYCVehicleSlots::BrakeRight),
		FName(NYCVehicleSlots::ReverseLeft), FName(NYCVehicleSlots::ReverseRight),
		FName(NYCVehicleSlots::IndicatorRearLeft), FName(NYCVehicleSlots::IndicatorRearRight),
		FName(NYCVehicleSlots::PlateLight)};
	static const TArray<FName> Left = {FName(NYCVehicleSlots::IndicatorSideLeft)};
	static const TArray<FName> Right = {FName(NYCVehicleSlots::IndicatorSideRight)};
	static const TArray<FName> None;

	switch (Region)
	{
	case ENYCDamageRegion::Front: return Front;
	case ENYCDamageRegion::Rear: return Rear;
	case ENYCDamageRegion::Left: return Left;
	case ENYCDamageRegion::Right: return Right;
	default: return None;
	}
}
}  // namespace

UNYCVehicleDamageComponent::UNYCVehicleDamageComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UNYCVehicleDamageComponent::Initialise(USkeletalMeshComponent* InMesh, UNYCVehicleLightsComponent* InLights,
											UNYCVehicleMovementComponent* InMovement)
{
	Mesh = InMesh;
	Lights = InLights;
	Movement = InMovement;
	RegionMaterials.Reset();
	RegionMaterials.SetNum(kRegionCount);
	if (Mesh == nullptr)
	{
		return;
	}

	for (int32 i = 0; i < kRegionCount; ++i)
	{
		const FName Slot = FNYCVehicleContract::DamageSlot(static_cast<ENYCDamageRegion>(i));
		const int32 Index = FNYCVehicleContract::SlotIndex(Mesh, Slot);
		RegionMaterials[i] = Index != INDEX_NONE ? Mesh->CreateDynamicMaterialInstance(Index) : nullptr;
	}
	const int32 GlassIndex = FNYCVehicleContract::SlotIndex(Mesh, FName(NYCVehicleSlots::Glass));
	GlassMaterial = GlassIndex != INDEX_NONE ? Mesh->CreateDynamicMaterialInstance(GlassIndex) : nullptr;
	const int32 PaintIndex = FNYCVehicleContract::SlotIndex(Mesh, FName(NYCVehicleSlots::BodyPaint));
	BodyPaintMaterial = PaintIndex != INDEX_NONE ? Mesh->CreateDynamicMaterialInstance(PaintIndex) : nullptr;

	// Half-extents of the body, used to classify a contact point into a region. Taken from the published overall
	// dimensions rather than from the mesh bounds, so a mirror sticking out does not skew the classification.
	const nycsim_gameplay::PlayerVehicleSpec Spec;
	HalfExtentsLocal = FVector(Spec.lengthM * 50.f, Spec.widthM * 50.f, Spec.heightM * 50.f);
}

ENYCDamageRegion UNYCVehicleDamageComponent::ClassifyRegion(const FVector& LocalContact) const
{
	// Normalise into the body box, then take the dominant face.
	const FVector N(LocalContact.X / FMath::Max(1.f, static_cast<float>(HalfExtentsLocal.X)),
					LocalContact.Y / FMath::Max(1.f, static_cast<float>(HalfExtentsLocal.Y)),
					LocalContact.Z / FMath::Max(1.f, static_cast<float>(HalfExtentsLocal.Z)));
	const float AX = FMath::Abs(N.X);
	const float AY = FMath::Abs(N.Y);
	const float AZ = FMath::Abs(N.Z);

	// The roof only counts when the contact is clearly above the waistline, otherwise a high side hit reads as a
	// side hit, which is what a real quarter-panel impact is.
	if (AZ > AX && AZ > AY && N.Z > 0.35f)
	{
		return ENYCDamageRegion::Roof;
	}
	if (AX >= AY)
	{
		return N.X >= 0.f ? ENYCDamageRegion::Front : ENYCDamageRegion::Rear;
	}
	return N.Y >= 0.f ? ENYCDamageRegion::Right : ENYCDamageRegion::Left;
}

void UNYCVehicleDamageComponent::ApplyImpact(const FVector& WorldLocation, const FVector& NormalImpulse,
											 float OtherMassKg)
{
	if (Mesh == nullptr || ImpactCooldown > 0.f)
	{
		return;
	}
	const AActor* Owner = GetOwner();
	if (Owner == nullptr)
	{
		return;
	}

	const float ImpulseSize = static_cast<float>(NormalImpulse.Size());
	if (ImpulseSize < ImpulseForFullDamage * 0.01f)
	{
		return;  // kerb rub / gentle contact
	}

	const FVector LocalContact = Owner->GetActorTransform().InverseTransformPosition(WorldLocation);
	const ENYCDamageRegion Region = ClassifyRegion(LocalContact);
	const int32 Index = static_cast<int32>(Region);

	// A heavier partner transfers more of the impulse into the panel.
	const float MassFactor = FMath::Clamp(OtherMassKg > 0.f ? FMath::Sqrt(OtherMassKg / 1685.f) : 1.f, 0.4f, 2.5f);
	const float Increment = FMath::Clamp(ImpulseSize / ImpulseForFullDamage, 0.f, 1.f) * MassFactor;

	RegionDamage[Index] = FMath::Clamp(RegionDamage[Index] + Increment, 0.f, 1.f);
	ImpactCooldown = ImpactCooldownSeconds;

	if (RegionDamage[Index] >= LampBreakThreshold && !bLampsBroken[Index])
	{
		BreakLampsIn(Region);
		bLampsBroken[Index] = true;
	}
	if (RegionDamage[Index] >= GlassCrackThreshold)
	{
		GlassCrack = FMath::Max(GlassCrack, (RegionDamage[Index] - GlassCrackThreshold) / (1.f - GlassCrackThreshold));
	}

	// A hard hit on a corner damages the tyre on that corner.
	if (Movement != nullptr && Increment > 0.4f)
	{
		const bool bFront = Region == ENYCDamageRegion::Front;
		const bool bLeft = LocalContact.Y < 0.f;
		const int32 Wheel = (bFront ? 0 : 2) + (bLeft ? 0 : 1);
		Movement->SetWheelDamage(Wheel, FMath::Clamp(Increment, 0.f, 1.f));
	}

	OnImpact.Broadcast(WorldLocation, FMath::Clamp(Increment, 0.f, 1.f), static_cast<uint8>(Region));
	UE_LOG(LogNYCSim, Verbose, TEXT("Vehicle impact: region %d, impulse %.0f, damage now %.2f"), Index, ImpulseSize,
		   RegionDamage[Index]);
}

void UNYCVehicleDamageComponent::BreakLampsIn(ENYCDamageRegion Region)
{
	if (Lights == nullptr)
	{
		return;
	}
	for (const FName& Slot : LampsInRegion(Region))
	{
		Lights->SetLampBroken(Slot, 1.f);
	}
}

void UNYCVehicleDamageComponent::Repair()
{
	for (int32 i = 0; i < kRegionCount; ++i)
	{
		RegionDamage[i] = 0.f;
		bLampsBroken[i] = false;
	}
	GlassCrack = 0.f;
	if (Lights != nullptr)
	{
		for (int32 i = 0; i < kRegionCount; ++i)
		{
			for (const FName& Slot : LampsInRegion(static_cast<ENYCDamageRegion>(i)))
			{
				Lights->SetLampBroken(Slot, 0.f);
			}
		}
	}
	if (Movement != nullptr)
	{
		for (int32 Wheel = 0; Wheel < 4; ++Wheel)
		{
			Movement->SetWheelDamage(Wheel, 0.f);
		}
	}
	PushToMesh();
}

float UNYCVehicleDamageComponent::GetRegionDamage(ENYCDamageRegion Region) const
{
	const int32 Index = static_cast<int32>(Region);
	return (Index >= 0 && Index < kRegionCount) ? RegionDamage[Index] : 0.f;
}

float UNYCVehicleDamageComponent::GetWorstDamage() const
{
	float Worst = 0.f;
	for (int32 i = 0; i < kRegionCount; ++i)
	{
		Worst = FMath::Max(Worst, RegionDamage[i]);
	}
	return Worst;
}

bool UNYCVehicleDamageComponent::IsDisabled() const
{
	return RegionDamage[static_cast<int32>(ENYCDamageRegion::Front)] > 0.9f;
}

void UNYCVehicleDamageComponent::PushToMesh()
{
	if (Mesh == nullptr)
	{
		return;
	}
	for (int32 i = 0; i < kRegionCount; ++i)
	{
		const ENYCDamageRegion Region = static_cast<ENYCDamageRegion>(i);
		const FName Morph = FNYCVehicleContract::DamageMorph(Region);
		if (!Morph.IsNone())
		{
			Mesh->SetMorphTarget(Morph, RegionDamage[i]);
		}
		if (RegionMaterials.IsValidIndex(i) && RegionMaterials[i] != nullptr)
		{
			RegionMaterials[i]->SetScalarParameterValue(FName(NYCVehicleParams::DentAmount), RegionDamage[i]);
		}
		AppliedDamage[i] = RegionDamage[i];
	}
	if (GlassMaterial != nullptr)
	{
		GlassMaterial->SetScalarParameterValue(FName(NYCVehicleParams::CrackAmount), GlassCrack);
	}
	if (BodyPaintMaterial != nullptr)
	{
		// A wrecked car is also a dirty car: scrapes take the clear coat off.
		BodyPaintMaterial->SetScalarParameterValue(FName(NYCVehicleParams::DentAmount), GetWorstDamage());
	}
}

void UNYCVehicleDamageComponent::TickComponent(float DeltaTime, ELevelTick TickType,
											   FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (ImpactCooldown > 0.f)
	{
		ImpactCooldown = FMath::Max(0.f, ImpactCooldown - DeltaTime);
	}
	// Only touch the mesh when something actually changed: SetMorphTarget dirties the skeletal mesh every call.
	for (int32 i = 0; i < kRegionCount; ++i)
	{
		if (!FMath::IsNearlyEqual(AppliedDamage[i], RegionDamage[i], 0.001f))
		{
			PushToMesh();
			break;
		}
	}
}
