// Animation instance for every NYCSim vehicle mesh.
//
// A car has no keyframed animation: it has a rest pose plus a handful of bones the simulation drives (wheels,
// steering wheel, gauge needles, doors, windows, wipers, mirrors, gear selector). Rather than depend on an
// Animation Blueprint asset — which cannot be authored in this environment (ADR-001) — the pose is produced in
// C++ by an FAnimInstanceProxy that resets to the reference pose and applies the deltas listed in the bone-axis
// table in NYCVehicleContract.h.
//
// Every component that moves a bone writes into FNYCVehicleAnimState on the game thread; the proxy copies the
// struct once per frame in PreUpdate and reads only its own copy on the worker thread, so nothing races.
#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "NYCVehicleAnimInstance.generated.h"

/** Everything the vehicle rig needs, in engine units (degrees, centimetres). */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCVehicleAnimState
{
	GENERATED_BODY()

	/** Rolling angle per wheel, degrees, accumulated (wrapped to 0..360 by the proxy). */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float WheelSpinDeg[4] = {0.f, 0.f, 0.f, 0.f};

	/** Steer angle per wheel, degrees (rear wheels stay at 0). */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float WheelSteerDeg[4] = {0.f, 0.f, 0.f, 0.f};

	/** Suspension displacement per wheel, centimetres (positive = compressed). */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float WheelSuspensionCm[4] = {0.f, 0.f, 0.f, 0.f};

	/** Steering wheel rotation, degrees. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float SteeringWheelDeg = 0.f;

	/** Gauge needle sweeps, degrees from the rest peg. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float NeedleSpeedDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float NeedleRpmDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float NeedleFuelDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float NeedleTempDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float GearSelectorDeg = 0.f;

	/** Door swing, degrees: [0]=FL [1]=FR [2]=RL [3]=RR. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float DoorDeg[4] = {0.f, 0.f, 0.f, 0.f};

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float HoodDeg = 0.f;

	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float TrunkDeg = 0.f;

	/** Window drop, centimetres: [0]=FL [1]=FR [2]=RL [3]=RR. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float WindowDropCm[4] = {0.f, 0.f, 0.f, 0.f};

	/** Wiper sweep, degrees: [0]=left blade [1]=right blade [2]=rear. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float WiperDeg[3] = {0.f, 0.f, 0.f};

	/** Mirror fold, degrees: [0]=left [1]=right. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	float MirrorFoldDeg[2] = {0.f, 0.f};
};

/** Worker-thread proxy: resets to the reference pose and applies FNYCVehicleAnimState as local-space deltas. */
USTRUCT()
struct NYCSIMRUNTIME_API FNYCVehicleAnimProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FNYCVehicleAnimProxy() = default;
	explicit FNYCVehicleAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void Initialize(UAnimInstance* InAnimInstance) override;
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

private:
	/** One driven bone: its mesh bone index plus the delta to apply. */
	struct FDriven
	{
		int32 MeshBoneIndex = INDEX_NONE;
		FQuat Rotation = FQuat::Identity;
		FVector Translation = FVector::ZeroVector;
	};

	void Resolve(const USkeletalMeshComponent* Mesh);
	void BuildDeltas();

	FNYCVehicleAnimState State;
	TArray<FDriven> Driven;

	// Cached bone indices (INDEX_NONE when the rig does not have that bone).
	int32 WheelBone[4] = {INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE};
	int32 SteeringWheelBone = INDEX_NONE;
	int32 NeedleBone[4] = {INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE};
	int32 GearSelectorBone = INDEX_NONE;
	int32 DoorBone[4] = {INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE};
	int32 HoodBone = INDEX_NONE;
	int32 TrunkBone = INDEX_NONE;
	int32 WindowBone[4] = {INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE};
	int32 WiperBone[3] = {INDEX_NONE, INDEX_NONE, INDEX_NONE};
	int32 MirrorBone[2] = {INDEX_NONE, INDEX_NONE};
	bool bResolved = false;
};

UCLASS(Transient)
class NYCSIMRUNTIME_API UNYCVehicleAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** Game-thread state. Components write it directly; the proxy copies it in PreUpdate. */
	UPROPERTY(BlueprintReadWrite, Category = "NYCSim|Vehicle")
	FNYCVehicleAnimState AnimState;

	UFUNCTION(BlueprintCallable, Category = "NYCSim|Vehicle")
	void SetAnimState(const FNYCVehicleAnimState& InState) { AnimState = InState; }

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;

	friend struct FNYCVehicleAnimProxy;

private:
	FNYCVehicleAnimProxy Proxy;
};
