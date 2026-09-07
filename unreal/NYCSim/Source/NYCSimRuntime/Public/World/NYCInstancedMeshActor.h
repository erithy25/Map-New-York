// Instanced placement holder: one actor per (tile, mesh) carrying every instance of that mesh in the tile as a
// hierarchical instanced static mesh (ARCHITECTURE §3 "L0 instancing via ISM/HISM per kit type per tile").
//
// It exists so the editor Python (Content/Python/build_levels.py) can place 14 000 kit pieces or 2 000 props per
// tile with one call and have them serialise into the tile's streaming level: the component is a default subobject
// of a real actor class, not a runtime-added component.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UObject/ObjectPtr.h"

#include "NYCInstancedMeshActor.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

UCLASS()
class NYCSIMRUNTIME_API ANYCInstancedMeshActor : public AActor
{
	GENERATED_BODY()

public:
	ANYCInstancedMeshActor();

	/**
	 * Replaces the mesh and every instance. Transforms are in world space.
	 * CollisionProfile "" keeps the component's default ("NoCollision" for kit pieces, "NYCBuildingShell" for props
	 * that must block the player). Returns the number of instances added.
	 */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|World")
	int32 SetupInstances(UStaticMesh* Mesh, const TArray<FTransform>& Transforms, FName CollisionProfile,
		bool bCastShadow = true);

	/** Appends more instances (world space) without touching the mesh. */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|World")
	int32 AddInstances(const TArray<FTransform>& Transforms);

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	int32 GetInstanceCount() const;

	UFUNCTION(BlueprintPure, Category = "NYCSim|World")
	UHierarchicalInstancedStaticMeshComponent* GetInstancedComponent() const { return Instances; }

	/** Distance in centimetres beyond which instances stop drawing (0 = never cull). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|World")
	void SetCullDistance(int32 StartCm, int32 EndCm);

private:
	UPROPERTY(VisibleAnywhere, Category = "NYCSim")
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Instances;
};
