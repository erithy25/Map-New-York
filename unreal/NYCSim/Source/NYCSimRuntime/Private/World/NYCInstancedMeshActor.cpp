#include "World/NYCInstancedMeshActor.h"

#include "NYCSimRuntime.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"

ANYCInstancedMeshActor::ANYCInstancedMeshActor()
{
	PrimaryActorTick.bCanEverTick = false;
	SetCanBeDamaged(false);

	Instances = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("Instances"));
	Instances->SetMobility(EComponentMobility::Static);
	Instances->SetCollisionProfileName(TEXT("NoCollision"));
	Instances->SetCastShadow(true);
	// 1 km tiles: instances outside the tile's own streaming radius are already unloaded, so per-instance culling
	// only has to hide the far half of the tile.
	Instances->InstanceStartCullDistance = 0;
	Instances->InstanceEndCullDistance = 0;
	SetRootComponent(Instances);
}

int32 ANYCInstancedMeshActor::SetupInstances(UStaticMesh* Mesh, const TArray<FTransform>& Transforms,
	FName CollisionProfile, bool bCastShadow)
{
	if (!Instances)
	{
		return 0;
	}
	if (!Mesh)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("%s: SetupInstances called without a mesh"), *GetName());
		return 0;
	}
	Instances->ClearInstances();
	Instances->SetStaticMesh(Mesh);
	if (!CollisionProfile.IsNone())
	{
		Instances->SetCollisionProfileName(CollisionProfile);
	}
	Instances->SetCastShadow(bCastShadow);
	return AddInstances(Transforms);
}

int32 ANYCInstancedMeshActor::AddInstances(const TArray<FTransform>& Transforms)
{
	if (!Instances || Transforms.Num() == 0)
	{
		return 0;
	}
	// bWorldSpace: the caller works in NYC_TM-derived world coordinates, not in the actor's local frame.
	const TArray<int32> Added = Instances->AddInstances(Transforms, /*bShouldReturnIndices*/ true, /*bWorldSpace*/ true);
	Instances->MarkRenderStateDirty();
	return Added.Num();
}

int32 ANYCInstancedMeshActor::GetInstanceCount() const
{
	return Instances ? Instances->GetInstanceCount() : 0;
}

void ANYCInstancedMeshActor::SetCullDistance(int32 StartCm, int32 EndCm)
{
	if (!Instances)
	{
		return;
	}
	Instances->InstanceStartCullDistance = FMath::Max(0, StartCm);
	Instances->InstanceEndCullDistance = FMath::Max(0, EndCm);
	Instances->MarkRenderStateDirty();
}
