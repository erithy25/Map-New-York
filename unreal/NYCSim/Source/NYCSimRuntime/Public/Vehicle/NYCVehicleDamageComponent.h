// Per-region collision damage: deformation, light breakage and glass cracking.
//
// The body is divided into the five DMG_* regions of the mesh contract. An impact is classified by the contact
// point in the vehicle's own frame, converted to a damage increment from the normal impulse, and applied three
// ways:
//   * deformation — the region's morph target (DMG_<region>_dent) is driven to the accumulated damage, and the
//     region's material gets DentAmount so the shader can break up the specular highlight on the crumpled panel;
//   * light breakage — a lamp inside the damaged region is broken once that region passes its breakage threshold,
//     which stops it emitting and makes the indicator hyperflash (UNYCVehicleLightsComponent::SetLampBroken);
//   * glass — the windows and windscreen adjacent to the region get CrackAmount, and past 0.75 the pane is
//     considered shattered and drops.
//
// Damage never repairs itself; Repair() resets everything (used by the debug console and a body shop).
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicle/NYCVehicleContract.h"
#include "NYCVehicleDamageComponent.generated.h"

class UMaterialInstanceDynamic;
class UMeshComponent;
class UNYCVehicleLightsComponent;
class UNYCVehicleMovementComponent;
class USkeletalMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FNYCVehicleImpact, FVector, WorldLocation, float, Severity, uint8,
											   Region);

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleDamageComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleDamageComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Damage")
	void Initialise(USkeletalMeshComponent* InMesh, UNYCVehicleLightsComponent* InLights,
					UNYCVehicleMovementComponent* InMovement);

	/** Feed an impact: world contact point, normal impulse magnitude (UE units) and the other actor's mass. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Damage")
	void ApplyImpact(const FVector& WorldLocation, const FVector& NormalImpulse, float OtherMassKg);

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Damage")
	void Repair();

	UFUNCTION(BlueprintPure, Category = "NYCSim|Damage")
	float GetRegionDamage(ENYCDamageRegion Region) const;

	/** Worst region damage, used by the HUD and by the AI's "that car is wrecked" test. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Damage")
	float GetWorstDamage() const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Damage")
	float GetGlassCracking() const { return GlassCrack; }

	/** True once the front is damaged enough that the car should not be drivable. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Damage")
	bool IsDisabled() const;

	UPROPERTY(BlueprintAssignable, Category = "NYCSim|Damage")
	FNYCVehicleImpact OnImpact;

	/** Impulse (kg·cm/s) that produces full damage on one region. Tuned so a 30 km/h barrier hit writes the car
	 *  off and a 5 km/h parking knock leaves a visible dent. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Damage", meta = (ClampMin = "1000.0"))
	float ImpulseForFullDamage = 260000.f;

	/** Region damage past which the lamps inside it break. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Damage", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float LampBreakThreshold = 0.35f;

	/** Region damage past which the adjacent glass starts to craze. */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Damage", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float GlassCrackThreshold = 0.45f;

	/** Minimum seconds between two impacts counting separately (stops a scrape becoming a hundred hits). */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Damage", meta = (ClampMin = "0.0"))
	float ImpactCooldownSeconds = 0.25f;

private:
	ENYCDamageRegion ClassifyRegion(const FVector& LocalContact) const;
	void PushToMesh();
	void BreakLampsIn(ENYCDamageRegion Region);

	UPROPERTY(Transient)
	TObjectPtr<USkeletalMeshComponent> Mesh;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleLightsComponent> Lights;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleMovementComponent> Movement;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> RegionMaterials;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GlassMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> BodyPaintMaterial;

	float RegionDamage[static_cast<int32>(ENYCDamageRegion::Count)] = {0.f, 0.f, 0.f, 0.f, 0.f};
	float AppliedDamage[static_cast<int32>(ENYCDamageRegion::Count)] = {0.f, 0.f, 0.f, 0.f, 0.f};
	bool bLampsBroken[static_cast<int32>(ENYCDamageRegion::Count)] = {false, false, false, false, false};
	float GlassCrack = 0.f;
	float ImpactCooldown = 0.f;
	FVector HalfExtentsLocal = FVector(240.f, 92.f, 74.f);
};
