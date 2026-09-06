#include "Traffic/NYCTrafficVehicle.h"

#include "Audio/NYCAudioSubsystem.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NYCSimRuntime.h"
#include "Sound/SoundBase.h"
#include "Vehicle/NYCVehicleAnimInstance.h"
#include "Vehicle/NYCVehicleContract.h"
#include "Vehicle/NYCVehicleLightsComponent.h"

ANYCTrafficVehicle::ANYCTrafficVehicle()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	// Traffic actors are driven by the simulation, never by the physics solver.
	SetActorEnableCollision(true);

	Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(FName(TEXT("Vehicle")));
	Mesh->SetSimulatePhysics(false);
	Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	Mesh->SetAnimInstanceClass(UNYCVehicleAnimInstance::StaticClass());
	Mesh->bEnableUpdateRateOptimizations = true;
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;

	Lights = CreateDefaultSubobject<UNYCVehicleLightsComponent>(TEXT("Lights"));

	DestinationSign = CreateDefaultSubobject<UTextRenderComponent>(TEXT("DestinationSign"));
	DestinationSign->SetupAttachment(Mesh, FName(NYCVehicleBones::SocketDestinationSign));
	DestinationSign->SetHorizontalAlignment(EHTA_Center);
	DestinationSign->SetVerticalAlignment(EVRTA_TextCenter);
	DestinationSign->SetWorldSize(11.f);
	DestinationSign->SetTextRenderColor(FColor(255, 176, 32));
	DestinationSign->SetVisibility(false);
	DestinationSign->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	SirenAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("Siren"));
	SirenAudio->SetupAttachment(Mesh);
	SirenAudio->bAutoActivate = false;
	// Doppler and distance attenuation come from the sound's attenuation settings; the emitter only has to move.
	SirenAudio->bAllowSpatialization = true;
	SirenAudio->bOverrideAttenuation = false;

	SetActorHiddenInGame(true);
	SetActorTickEnabled(false);
}

void ANYCTrafficVehicle::Acquire(int32 InAgentId, uint8 InVehicleClass, USkeletalMesh* InMesh,
								 const FLinearColor& InPaint)
{
	AgentId = InAgentId;
	const bool bClassChanged = VehicleClass != InVehicleClass || Mesh->GetSkeletalMeshAsset() != InMesh;
	VehicleClass = InVehicleClass;

	if (bClassChanged)
	{
		Mesh->SetSkeletalMesh(InMesh);
		AnimInstance = Cast<UNYCVehicleAnimInstance>(Mesh->GetAnimInstance());
		// Lamps are emissive-only for AI traffic: 900 spot lights would not fit in any frame budget.
		Lights->Initialise(Mesh, /*bSpawnRealLights*/ false);

		const int32 PaintIndex = FNYCVehicleContract::SlotIndex(Mesh, FName(NYCVehicleSlots::BodyPaint));
		if (PaintIndex != INDEX_NONE)
		{
			if (UMaterialInstanceDynamic* Paint = Mesh->CreateDynamicMaterialInstance(PaintIndex))
			{
				Paint->SetVectorParameterValue(FName(NYCVehicleParams::PaintColor), InPaint);
			}
		}
	}

	WheelSpinDeg = 0.f;
	LodLevel = 0;
	SetActorHiddenInGame(false);
	SetActorTickEnabled(true);
	Mesh->SetVisibility(true, true);
}

void ANYCTrafficVehicle::Release()
{
	AgentId = 0;
	SetActorHiddenInGame(true);
	SetActorTickEnabled(false);
	Mesh->SetVisibility(false, true);
	DestinationSign->SetVisibility(false);
	if (SirenAudio != nullptr && bSirenPlaying)
	{
		SirenAudio->Stop();
		bSirenPlaying = false;
		if (UWorld* World = GetWorld())
		{
			if (UNYCAudioSubsystem* Audio = World->GetSubsystem<UNYCAudioSubsystem>())
			{
				Audio->UnregisterDopplerSource(SirenAudio);
			}
		}
	}
	CurrentSpeedMps = 0.f;
	SetActorLocation(FVector(0.f, 0.f, -100000.f));
}

void ANYCTrafficVehicle::SetDestinationSign(const FString& Text)
{
	if (DestinationSign == nullptr)
	{
		return;
	}
	const bool bShow = !Text.IsEmpty() && LodLevel <= 1;
	DestinationSign->SetVisibility(bShow);
	if (bShow && DestinationSign->Text.ToString() != Text)
	{
		DestinationSign->SetText(FText::FromString(Text));
	}
}

void ANYCTrafficVehicle::SetForHire(bool bInForHire)
{
	bForHire = bInForHire;
	if (Lights != nullptr)
	{
		// The medallion roof light is lit when the cab is available, dark when hired: the same convention the
		// TLC's rooftop lamp uses.
		Lights->SetLampBroken(FName(NYCVehicleSlots::TaxiRoofLight), bForHire ? 0.f : 1.f);
	}
}

void ANYCTrafficVehicle::SetSirenSound(USoundBase* Sound)
{
	if (SirenAudio != nullptr && SirenAudio->Sound != Sound)
	{
		SirenAudio->SetSound(Sound);
	}
}

void ANYCTrafficVehicle::SetLodLevel(int32 Level)
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
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
		Mesh->SetComponentTickEnabled(true);
		break;
	case 1:
		// Beyond the LOD distance the wheels stop being posed every frame: a car at 120 m does not read as
		// having still wheels, and this is the single biggest saving for a crowd of skeletal meshes.
		Mesh->SetVisibility(true, true);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPose;
		Mesh->SetComponentTickEnabled(false);
		break;
	case 2:
		Mesh->SetVisibility(true, true);
		Mesh->SetComponentTickEnabled(false);
		DestinationSign->SetVisibility(false);
		break;
	default:
		Mesh->SetVisibility(false, true);
		Mesh->SetComponentTickEnabled(false);
		DestinationSign->SetVisibility(false);
		break;
	}
}

void ANYCTrafficVehicle::ApplyState(const FNYCTrafficVehicleState& State, float DeltaTime, bool bTeleport)
{
	if (bTeleport)
	{
		SmoothedLocation = State.Location;
		SmoothedRotation = State.Rotation;
	}
	else
	{
		// The simulation publishes at 20 Hz; smoothing to the target over ~2 steps removes the stepping without
		// visibly lagging behind (at 12 m/s the maximum error is under 6 cm).
		const float Rate = 14.f;
		SmoothedLocation = FMath::VInterpTo(SmoothedLocation, State.Location, DeltaTime, Rate);
		SmoothedRotation = FMath::RInterpTo(SmoothedRotation, State.Rotation, DeltaTime, Rate);
	}
	SetActorLocationAndRotation(SmoothedLocation, SmoothedRotation, /*bSweep*/ false, nullptr,
								ETeleportType::TeleportPhysics);

	if (Lights != nullptr)
	{
		Lights->SetBrake(State.bBraking);
		Lights->SetHeadlightMode(State.bHeadlights ? ENYCHeadlightMode::Low : ENYCHeadlightMode::DaytimeRunning);
		ENYCTurnSignal Signal = ENYCTurnSignal::None;
		if (State.bHazards)
		{
			Signal = ENYCTurnSignal::Hazard;
		}
		else if (State.bIndicateLeft)
		{
			Signal = ENYCTurnSignal::Left;
		}
		else if (State.bIndicateRight)
		{
			Signal = ENYCTurnSignal::Right;
		}
		if (Lights->GetTurnSignal() != Signal)
		{
			Lights->SetTurnSignal(Signal);
		}
	}

	if (AnimInstance != nullptr && LodLevel == 0)
	{
		FNYCVehicleAnimState& Anim = AnimInstance->AnimState;
		WheelSpinDeg = FMath::Fmod(State.WheelSpinDeg, 360.f);
		for (int32 i = 0; i < 4; ++i)
		{
			Anim.WheelSpinDeg[i] = WheelSpinDeg;
			Anim.WheelSteerDeg[i] = i < 2 ? State.SteerDeg : 0.f;
		}
		// Buses open their doors at a stop; everything else keeps them shut.
		const float DoorDeg = State.bDoorsOpen ? 85.f : 0.f;
		Anim.DoorDeg[0] = DoorDeg;
		Anim.DoorDeg[1] = DoorDeg;
	}

	if (SirenAudio != nullptr)
	{
		if (State.bSiren && !bSirenPlaying && SirenAudio->Sound != nullptr && LodLevel <= 2)
		{
			SirenAudio->Play();
			bSirenPlaying = true;
			// An emergency vehicle passing at 20 m/s shifts its siren by about a semitone either side of the
			// pass, which is the most audible Doppler in the game; the audio subsystem applies it from the
			// component's own motion.
			if (UWorld* World = GetWorld())
			{
				if (UNYCAudioSubsystem* Audio = World->GetSubsystem<UNYCAudioSubsystem>())
				{
					Audio->RegisterDopplerSource(SirenAudio);
				}
			}
		}
		else if ((!State.bSiren || LodLevel > 2) && bSirenPlaying)
		{
			SirenAudio->Stop();
			bSirenPlaying = false;
			if (UWorld* World = GetWorld())
			{
				if (UNYCAudioSubsystem* Audio = World->GetSubsystem<UNYCAudioSubsystem>())
				{
					Audio->UnregisterDopplerSource(SirenAudio);
				}
			}
		}
	}

	CurrentSpeedMps = State.SpeedMps;
	SetDestinationSign(State.DestinationSign);
}

void ANYCTrafficVehicle::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	// The state is pushed by the subsystem; the tick only exists so the components (lights flasher) run.
	(void)DeltaTime;
}
