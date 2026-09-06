// A pooled crowd pedestrian.
//
// Like the traffic vehicles these actors are recycled: the subsystem hands each one an agent's appearance
// (archetype mesh + colour variant) and its state each frame. Locomotion is a single walk/idle clip whose play
// rate follows the agent's speed — a full locomotion state machine is reserved for the player character, because
// at a thousand agents the cost of one is the difference between shipping a crowd and not.
//
// Props follow the weather and the agent flags: an umbrella above 0.3 mm/h of rain, a coat below 12 °C, a bag, a
// phone, headphones, a dog. They are attached to the UE5-Mannequin sockets on the crowd skeleton.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NYCPedestrian.generated.h"

class UAnimSequence;
class USkeletalMesh;
class USkeletalMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;

USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCPedestrianState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	int32 AgentId = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	FVector Location = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	FRotator Rotation = FRotator::ZeroRotator;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	float SpeedMps = 0.f;

	/** 0 walking, 1 waiting to cross, 2 crossing, 3 idle. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	uint8 State = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	uint8 Archetype = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	uint8 Variant = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Peds")
	uint8 Flags = 0;
};

UCLASS()
class NYCSIMRUNTIME_API ANYCPedestrian : public AActor
{
	GENERATED_BODY()

public:
	ANYCPedestrian();

	void Acquire(int32 InAgentId, USkeletalMesh* InMesh, uint8 InArchetype, uint8 InVariant);
	void Release();

	bool IsInUse() const { return AgentId != 0; }
	int32 GetAgentId() const { return AgentId; }
	uint8 GetArchetype() const { return Archetype; }

	/** Animation clips shared by every pedestrian; set once by the subsystem. */
	void SetClips(UAnimSequence* InWalk, UAnimSequence* InIdle);

	/** Props shared by every pedestrian; set once by the subsystem (any may be null). */
	void SetProps(UStaticMesh* InUmbrella, UStaticMesh* InBag, UStaticMesh* InPhone);

	void ApplyState(const FNYCPedestrianState& State, float DeltaTime, bool bTeleport);

	/** 0 = animated, 1 = animated only when rendered, 2 = static pose, 3 = hidden. */
	void SetLodLevel(int32 Level);

	int32 GetLodLevel() const { return LodLevel; }

private:
	void UpdateProps(uint8 Flags);

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Peds")
	TObjectPtr<USkeletalMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Peds")
	TObjectPtr<UStaticMeshComponent> Umbrella;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Peds")
	TObjectPtr<UStaticMeshComponent> Bag;

	UPROPERTY(VisibleAnywhere, Category = "NYCSim|Peds")
	TObjectPtr<UStaticMeshComponent> Phone;

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> WalkClip;

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> IdleClip;

	int32 AgentId = 0;
	uint8 Archetype = 0;
	uint8 Variant = 0;
	uint8 CurrentFlags = 0;
	int32 LodLevel = 0;
	bool bPlayingWalk = false;
	FVector SmoothedLocation = FVector::ZeroVector;
	FRotator SmoothedRotation = FRotator::ZeroRotator;
};
