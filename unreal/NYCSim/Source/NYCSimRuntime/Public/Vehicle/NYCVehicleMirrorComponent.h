// Working mirrors: one scene capture per mirror, rendered into the MIRROR_GLASS_* material slots.
//
// Mirrors are the single most expensive feature on a car (each one is a full scene render), so this component is
// deliberate about cost:
//   * captures are manual (bCaptureEveryFrame = false) and are triggered at a configurable rate — 30 Hz for the
//     mirror the driver is looking at, 10 Hz for the others, 0 when the interior/chase camera is not active;
//   * the render targets are small (256 px by default) and use SCS_FinalColorLDR so no HDR buffer is kept;
//   * the capture's far distance is clamped to MirrorMaxRangeMetres, which keeps the whole skyline out of a
//     mirror that shows fifty metres of street.
//
// The mirror's field of view and the convex distortion of the passenger-side mirror ("objects in mirror are
// closer than they appear", US spherical convex mirror) are applied as capture FOV and a material parameter.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NYCVehicleMirrorComponent.generated.h"

class UMaterialInstanceDynamic;
class UMeshComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;

UCLASS(ClassGroup = (NYCSim), meta = (BlueprintSpawnableComponent))
class NYCSIMRUNTIME_API UNYCVehicleMirrorComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNYCVehicleMirrorComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Creates a capture for each Mirror_* bone present on the mesh. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Mirrors")
	void Initialise(UMeshComponent* InMesh);

	/** Captures only run while this is true (the camera rig switches it off outside the interior/chase views). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Mirrors")
	void SetMirrorsActive(bool bActive);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Mirrors")
	bool AreMirrorsActive() const { return bActive; }

	/** 0 = left, 1 = right, 2 = interior. The focused mirror captures at the full rate. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Mirrors")
	void SetFocusedMirror(int32 MirrorIndex);

	UFUNCTION(BlueprintPure, Category = "NYCSim|Mirrors")
	int32 GetMirrorCount() const { return Mirrors.Num(); }

	UPROPERTY(EditAnywhere, Category = "NYCSim|Mirrors", meta = (ClampMin = "1.0", ClampMax = "120.0"))
	float FocusedCaptureHz = 30.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Mirrors", meta = (ClampMin = "1.0", ClampMax = "60.0"))
	float BackgroundCaptureHz = 10.f;

	/** Door-mirror field of view. US door mirrors are about 17° (flat driver's side) / 25° (convex passenger). */
	UPROPERTY(EditAnywhere, Category = "NYCSim|Mirrors", meta = (ClampMin = "5.0", ClampMax = "120.0"))
	float DoorMirrorFovDeg = 22.f;

	UPROPERTY(EditAnywhere, Category = "NYCSim|Mirrors", meta = (ClampMin = "5.0", ClampMax = "120.0"))
	float InteriorMirrorFovDeg = 34.f;

private:
	struct FMirror
	{
		FName Bone;
		FName GlassSlot;
		TObjectPtr<USceneCaptureComponent2D> Capture = nullptr;
		TObjectPtr<UTextureRenderTarget2D> Target = nullptr;
		TObjectPtr<UMaterialInstanceDynamic> Material = nullptr;
		float Accumulator = 0.f;
		bool bConvex = false;
	};

	void AddMirror(FName Bone, FName PreferredSlot, float FovDeg, bool bConvex);

	UPROPERTY(Transient)
	TObjectPtr<UMeshComponent> Mesh;

	UPROPERTY(Transient)
	TArray<TObjectPtr<USceneCaptureComponent2D>> OwnedCaptures;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UTextureRenderTarget2D>> OwnedTargets;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> OwnedMaterials;

	TArray<FMirror> Mirrors;
	int32 FocusedMirror = 0;
	bool bActive = true;
};
