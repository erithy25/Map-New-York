// A pooled AI vehicle. One actor is reused for many agents over a session: the traffic subsystem hands it the
// agent's class and state each frame, and the actor swaps its mesh only when the class changes.
//
// Nothing here simulates: the position, heading, speed, indicator and brake state all come from the traffic
// worker's snapshot. The actor is responsible for turning that into a convincing vehicle — wheels that roll and
// steer, lamps that flash, a bus destination sign with the real route name, a taxi roof light that goes out when
// the cab is hired, a siren with Doppler, and a level of detail that keeps 900 of these affordable.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NYCTrafficVehicle.generated.h"

class UAudioComponent;
class UNYCVehicleAnimInstance;
class UNYCVehicleLightsComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class UTextRenderComponent;

/** What the subsystem hands over each frame; a UE-side mirror of nycsim_gameplay::VehicleSnapshot. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCTrafficVehicleState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	int32 AgentId = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	uint8 VehicleClass = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	FVector Location = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	FRotator Rotation = FRotator::ZeroRotator;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	float SpeedMps = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	float WheelSpinDeg = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	float SteerDeg = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bBraking = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bIndicateLeft = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bIndicateRight = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bHazards = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bSiren = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bDoorsOpen = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	bool bHeadlights = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	float Honk = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Traffic")
	FString DestinationSign;
};

UCLASS()
class NYCSIMRUNTIME_API ANYCTrafficVehicle : public AActor
{
	GENERATED_BODY()

public:
	ANYCTrafficVehicle();

	virtual void Tick(float DeltaTime) override;

	/** Puts the actor into service for an agent; `Mesh` may be null while the fleet assets are missing. */
	void Acquire(int32 InAgentId, uint8 InVehicleClass, USkeletalMesh* InMesh, const FLinearColor& InPaint);

	/** Returns the actor to the pool: hidden, ticking off, no audio. */
	void Release();

	bool IsInUse() const { return AgentId != 0; }
	int32 GetAgentId() const { return AgentId; }
	uint8 GetVehicleClass() const { return VehicleClass; }

	/** Applies one simulation step. `bTeleport` skips the smoothing (used on acquire). */
	void ApplyState(const FNYCTrafficVehicleState& State, float DeltaTime, bool bTeleport);

	/** 0 = full detail, 1 = no per-frame skeletal update, 2 = distant (lamps only), 3 = hidden. */
	void SetLodLevel(int32 Level);

	int32 GetLodLevel() const { return LodLevel; }

	/** Ground speed from the last simulation step; the ambience bed measures the traffic around the listener. */
	float GetSpeedMps() const { return CurrentSpeedMps; }

	/** The bus destination sign text (empty for anything that is not a bus). */
	void SetDestinationSign(const FString& Text);

	/** Taxi roof light: on = for hire. */
	void SetForHire(bool bForHire);

	/** Siren sound; the subsystem supplies the asset once. */
	void SetSirenSound(class USoundBase* Sound);

	USkeletalMeshComponent* GetMeshComponent() const { return Mesh; }

private:
	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Traffic")
	TObjectPtr<USkeletalMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Traffic")
	TObjectPtr<UNYCVehicleLightsComponent> Lights;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Traffic")
	TObjectPtr<UTextRenderComponent> DestinationSign;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Traffic")
	TObjectPtr<UAudioComponent> SirenAudio;

	UPROPERTY(Transient)
	TObjectPtr<UNYCVehicleAnimInstance> AnimInstance;

	int32 AgentId = 0;
	uint8 VehicleClass = 0;
	int32 LodLevel = 0;
	float CurrentSpeedMps = 0.f;
	bool bSirenPlaying = false;
	bool bForHire = true;
	float WheelSpinDeg = 0.f;
	FVector SmoothedLocation = FVector::ZeroVector;
	FRotator SmoothedRotation = FRotator::ZeroRotator;
};
