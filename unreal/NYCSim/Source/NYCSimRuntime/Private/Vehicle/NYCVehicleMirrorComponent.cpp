#include "Vehicle/NYCVehicleMirrorComponent.h"

#include "Components/MeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Vehicle/NYCVehicleContract.h"

UNYCVehicleMirrorComponent::UNYCVehicleMirrorComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UNYCVehicleMirrorComponent::AddMirror(FName Bone, FName PreferredSlot, float FovDeg, bool bConvex)
{
	AActor* Owner = GetOwner();
	if (Owner == nullptr || Mesh == nullptr || Bone.IsNone())
	{
		return;
	}
	// DoesSocketExist() answers for bones as well as sockets on a skeletal mesh, so this is the one check needed.
	if (!Mesh->DoesSocketExist(Bone))
	{
		return;
	}

	// The glass slot: the per-mirror one if the mesh carries it, otherwise the shared MIRROR_GLASS.
	FName Slot = PreferredSlot;
	int32 SlotIndex = FNYCVehicleContract::SlotIndex(Mesh, Slot);
	if (SlotIndex == INDEX_NONE)
	{
		Slot = FName(NYCVehicleSlots::MirrorGlass);
		SlotIndex = FNYCVehicleContract::SlotIndex(Mesh, Slot);
	}
	if (SlotIndex == INDEX_NONE)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Mirrors: no MIRROR_GLASS slot for bone '%s'; that mirror stays static."),
			   *Bone.ToString());
		return;
	}

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	const int32 Resolution = FMath::Clamp(Settings.MirrorResolution, 32, 1024);

	UTextureRenderTarget2D* Target = NewObject<UTextureRenderTarget2D>(Owner);
	Target->RenderTargetFormat = RTF_RGBA8_SRGB;
	Target->ClearColor = FLinearColor::Black;
	Target->bAutoGenerateMips = false;
	Target->InitAutoFormat(Resolution, Resolution);
	Target->UpdateResourceImmediate(true);
	OwnedTargets.Add(Target);

	USceneCaptureComponent2D* Capture = NewObject<USceneCaptureComponent2D>(
		Owner, *FString::Printf(TEXT("NYCMirrorCapture_%s"), *Bone.ToString()));
	Capture->SetupAttachment(Mesh, Bone);
	Capture->bCaptureEveryFrame = false;
	Capture->bCaptureOnMovement = false;
	Capture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
	Capture->TextureTarget = Target;
	Capture->FOVAngle = FovDeg;
	Capture->ProjectionType = ECameraProjectionMode::Perspective;
	Capture->MaxViewDistanceOverride = Settings.MirrorMaxRangeMetres * 100.f;
	Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives;
	// A mirror faces backwards along the car; the bone's own axis is the glass normal by the rig contract, so the
	// capture only has to look the other way.
	Capture->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
	// Keep the cost down: no motion blur or bloom in a 256 px mirror.
	Capture->ShowFlags.SetMotionBlur(false);
	Capture->ShowFlags.SetBloom(false);
	Capture->ShowFlags.SetAntiAliasing(true);
	Capture->RegisterComponent();
	OwnedCaptures.Add(Capture);

	UMaterialInstanceDynamic* Material = Mesh->CreateDynamicMaterialInstance(SlotIndex);
	if (Material != nullptr)
	{
		Material->SetTextureParameterValue(FName(NYCVehicleParams::MirrorTexture), Target);
		// US FMVSS 111 lets the passenger-side mirror be convex; the shader widens the image by this factor.
		Material->SetScalarParameterValue(FName(TEXT("MirrorConvex")), bConvex ? 1.f : 0.f);
		OwnedMaterials.Add(Material);
	}

	FMirror Mirror;
	Mirror.Bone = Bone;
	Mirror.GlassSlot = Slot;
	Mirror.Capture = Capture;
	Mirror.Target = Target;
	Mirror.Material = Material;
	Mirror.bConvex = bConvex;
	Mirrors.Add(MoveTemp(Mirror));
}

void UNYCVehicleMirrorComponent::Initialise(UMeshComponent* InMesh)
{
	Mesh = InMesh;
	Mirrors.Reset();
	if (Mesh == nullptr)
	{
		return;
	}
	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	if (Settings.MirrorResolution <= 0)
	{
		UE_LOG(LogNYCSim, Log, TEXT("Mirrors: disabled by MirrorResolution = 0."));
		return;
	}

	AddMirror(FName(NYCVehicleBones::MirrorLeft), FName(NYCVehicleSlots::MirrorGlassLeft), DoorMirrorFovDeg,
			  /*bConvex*/ false);
	AddMirror(FName(NYCVehicleBones::MirrorRight), FName(NYCVehicleSlots::MirrorGlassRight),
			  DoorMirrorFovDeg * 1.35f, /*bConvex*/ true);
	AddMirror(FName(NYCVehicleBones::MirrorInterior), FName(NYCVehicleSlots::MirrorGlassInterior),
			  InteriorMirrorFovDeg, /*bConvex*/ false);

	UE_LOG(LogNYCSim, Log, TEXT("Mirrors: %d captures at %d px."), Mirrors.Num(), Settings.MirrorResolution);
}

void UNYCVehicleMirrorComponent::SetMirrorsActive(bool bInActive)
{
	bActive = bInActive;
}

void UNYCVehicleMirrorComponent::SetFocusedMirror(int32 MirrorIndex)
{
	FocusedMirror = FMath::Clamp(MirrorIndex, 0, FMath::Max(0, Mirrors.Num() - 1));
}

void UNYCVehicleMirrorComponent::TickComponent(float DeltaTime, ELevelTick TickType,
											   FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (!bActive || Mirrors.Num() == 0 || DeltaTime <= 0.f)
	{
		return;
	}

	for (int32 i = 0; i < Mirrors.Num(); ++i)
	{
		FMirror& Mirror = Mirrors[i];
		if (Mirror.Capture == nullptr)
		{
			continue;
		}
		const float Hz = (i == FocusedMirror) ? FocusedCaptureHz : BackgroundCaptureHz;
		const float Interval = 1.f / FMath::Max(1.f, Hz);
		Mirror.Accumulator += DeltaTime;
		if (Mirror.Accumulator >= Interval)
		{
			Mirror.Accumulator = 0.f;
			Mirror.Capture->CaptureScene();
		}
	}
}

void UNYCVehicleMirrorComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (FMirror& Mirror : Mirrors)
	{
		if (Mirror.Capture != nullptr)
		{
			Mirror.Capture->TextureTarget = nullptr;
		}
	}
	Mirrors.Reset();
	OwnedCaptures.Reset();
	OwnedTargets.Reset();
	OwnedMaterials.Reset();
	Super::EndPlay(EndPlayReason);
}
