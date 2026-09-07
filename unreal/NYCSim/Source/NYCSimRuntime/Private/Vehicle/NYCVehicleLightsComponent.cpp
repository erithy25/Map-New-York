#include "Vehicle/NYCVehicleLightsComponent.h"

#include "Components/MeshComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NYCSimRuntime.h"

namespace
{
/// FMVSS 108 allows 60-120 flashes per minute; production relays run at 85, i.e. a 0.706 s period.
constexpr float kFlashPeriod = 60.f / 85.f;
/// A dead bulb on the flashing side halves the relay's load and roughly doubles the rate.
constexpr float kHyperFlashPeriod = kFlashPeriod * 0.5f;

// Lamp response times. The 2019 Fusion has LED tail/brake/DRL and halogen low beams, fogs and reverse lamps.
constexpr float kLedRise = 0.020f;
constexpr float kLedFall = 0.025f;
constexpr float kHalogenRise = 0.180f;
constexpr float kHalogenFall = 0.250f;
}  // namespace

UNYCVehicleLightsComponent::UNYCVehicleLightsComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UNYCVehicleLightsComponent::BeginPlay()
{
	Super::BeginPlay();
}

void UNYCVehicleLightsComponent::AddLamp(FName Slot, float RiseSeconds, float FallSeconds)
{
	if (Mesh == nullptr)
	{
		return;
	}
	const int32 Index = FNYCVehicleContract::SlotIndex(Mesh, Slot);
	if (Index == INDEX_NONE)
	{
		return;
	}
	UMaterialInstanceDynamic* Dynamic = Mesh->CreateDynamicMaterialInstance(Index);
	if (Dynamic == nullptr)
	{
		return;
	}
	OwnedMaterials.Add(Dynamic);

	FLamp Lamp;
	Lamp.Slot = Slot;
	Lamp.Material = Dynamic;
	Lamp.RiseSeconds = RiseSeconds;
	Lamp.FallSeconds = FallSeconds;
	Lamps.Add(MoveTemp(Lamp));
}

UNYCVehicleLightsComponent::FLamp* UNYCVehicleLightsComponent::Find(FName Slot)
{
	for (FLamp& Lamp : Lamps)
	{
		if (Lamp.Slot == Slot)
		{
			return &Lamp;
		}
	}
	return nullptr;
}

void UNYCVehicleLightsComponent::SetTarget(FName Slot, float Value)
{
	if (FLamp* Lamp = Find(Slot))
	{
		Lamp->Target = FMath::Clamp(Value, 0.f, 1.f);
	}
}

void UNYCVehicleLightsComponent::Initialise(UMeshComponent* InMesh, bool bSpawnRealLights)
{
	Mesh = InMesh;
	Lamps.Reset();
	OwnedMaterials.Reset();
	if (Mesh == nullptr)
	{
		UE_LOG(LogNYCSim, Warning, TEXT("NYCVehicleLights: Initialise called with no mesh; lamps disabled."));
		return;
	}

	// Halogen lamps.
	AddLamp(FName(NYCVehicleSlots::HeadLeft), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::HeadRight), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::HighBeamLeft), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::HighBeamRight), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::FogLeft), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::FogRight), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::ReverseLeft), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::ReverseRight), kHalogenRise, kHalogenFall);
	AddLamp(FName(NYCVehicleSlots::PlateLight), kHalogenRise, kHalogenFall);

	// LED lamps.
	AddLamp(FName(NYCVehicleSlots::DrlLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::DrlRight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::TailLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::TailRight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::BrakeLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::BrakeRight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::BrakeCentre), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::IndicatorFrontLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::IndicatorFrontRight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::IndicatorRearLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::IndicatorRearRight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::IndicatorSideLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::IndicatorSideRight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::InteriorLight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::DashBacklight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::TaxiRoofLight), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::EmergencyBarLeft), kLedRise, kLedFall);
	AddLamp(FName(NYCVehicleSlots::EmergencyBarRight), kLedRise, kLedFall);

	if (!bSpawnRealLights)
	{
		return;
	}

	AActor* Owner = GetOwner();
	if (Owner == nullptr)
	{
		return;
	}

	auto MakeSpot = [&](const TCHAR* Name, FName Socket, float OuterCone, float InnerCone) -> USpotLightComponent* {
		USpotLightComponent* Spot = NewObject<USpotLightComponent>(Owner, Name);
		Spot->SetupAttachment(Mesh, Socket);
		Spot->SetMobility(EComponentMobility::Movable);
		Spot->SetIntensityUnits(ELightUnits::Lumens);
		Spot->SetIntensity(0.f);
		Spot->SetAttenuationRadius(6000.f);
		Spot->SetOuterConeAngle(OuterCone);
		Spot->SetInnerConeAngle(InnerCone);
		Spot->SetLightColor(FLinearColor(1.f, 0.96f, 0.90f));
		Spot->SetCastShadows(true);
		Spot->SetVolumetricScatteringIntensity(1.2f);
		Spot->RegisterComponent();
		return Spot;
	};

	// The headlight sockets are the lamp material slots' bones when present; otherwise the lamps sit at the
	// bumper camera socket, which is the front of the car by the mesh contract.
	const FName LeftSocket = Mesh->DoesSocketExist(FName(TEXT("SKT_Head_L"))) ? FName(TEXT("SKT_Head_L"))
																			 : FName(NYCVehicleBones::SocketCameraBumper);
	const FName RightSocket = Mesh->DoesSocketExist(FName(TEXT("SKT_Head_R"))) ? FName(TEXT("SKT_Head_R"))
																			  : FName(NYCVehicleBones::SocketCameraBumper);
	HeadlightLeft = MakeSpot(TEXT("NYCHeadlightL"), LeftSocket, 42.f, 14.f);
	HeadlightRight = MakeSpot(TEXT("NYCHeadlightR"), RightSocket, 42.f, 14.f);
	if (HeadlightLeft != nullptr && LeftSocket == FName(NYCVehicleBones::SocketCameraBumper))
	{
		HeadlightLeft->SetRelativeLocation(FVector(0.f, -70.f, 0.f));
		HeadlightRight->SetRelativeLocation(FVector(0.f, 70.f, 0.f));
	}

	ReverseLight = MakeSpot(TEXT("NYCReverseLight"), FName(NYCVehicleBones::SocketPlateRear), 60.f, 30.f);
	if (ReverseLight != nullptr)
	{
		ReverseLight->SetLightColor(FLinearColor(0.92f, 0.95f, 1.f));
		ReverseLight->SetRelativeRotation(FRotator(-10.f, 180.f, 0.f));
		ReverseLight->SetAttenuationRadius(1200.f);
		ReverseLight->SetCastShadows(false);
	}

	InteriorLight = NewObject<URectLightComponent>(Owner, TEXT("NYCInteriorLight"));
	InteriorLight->SetupAttachment(Mesh, FName(NYCVehicleBones::SocketCameraInterior));
	InteriorLight->SetMobility(EComponentMobility::Movable);
	InteriorLight->SetIntensityUnits(ELightUnits::Lumens);
	InteriorLight->SetIntensity(0.f);
	InteriorLight->SetSourceWidth(18.f);
	InteriorLight->SetSourceHeight(6.f);
	InteriorLight->SetAttenuationRadius(220.f);
	InteriorLight->SetLightColor(FLinearColor(1.f, 0.93f, 0.82f));
	InteriorLight->SetCastShadows(false);
	InteriorLight->RegisterComponent();
}

void UNYCVehicleLightsComponent::SetHeadlightMode(ENYCHeadlightMode Mode)
{
	HeadlightMode = Mode;
}

void UNYCVehicleLightsComponent::CycleHeadlights()
{
	switch (HeadlightMode)
	{
	case ENYCHeadlightMode::Off: HeadlightMode = ENYCHeadlightMode::DaytimeRunning; break;
	case ENYCHeadlightMode::DaytimeRunning: HeadlightMode = ENYCHeadlightMode::Low; break;
	case ENYCHeadlightMode::Low: HeadlightMode = ENYCHeadlightMode::High; break;
	case ENYCHeadlightMode::High: HeadlightMode = ENYCHeadlightMode::Automatic; break;
	case ENYCHeadlightMode::Automatic:
	default: HeadlightMode = ENYCHeadlightMode::Off; break;
	}
}

void UNYCVehicleLightsComponent::SetTurnSignal(ENYCTurnSignal Signal)
{
	if (TurnSignal == ENYCTurnSignal::Hazard && Signal != ENYCTurnSignal::Hazard)
	{
		// The hazard switch overrides the stalk; remember the request for when the hazards go off.
		PreHazardSignal = Signal;
		return;
	}
	if (TurnSignal != Signal)
	{
		// Restart the relay so the first flash is a full one, exactly like a real thermal flasher.
		FlasherTime = 0.f;
		bFlasherOn = Signal != ENYCTurnSignal::None;
		if (bFlasherOn)
		{
			OnRelayClick.Broadcast(true);
		}
	}
	TurnSignal = Signal;
	SelfCancelIntegral = 0.f;
	bSelfCancelArmed = false;
}

void UNYCVehicleLightsComponent::ToggleHazards()
{
	if (TurnSignal == ENYCTurnSignal::Hazard)
	{
		TurnSignal = PreHazardSignal;
		PreHazardSignal = ENYCTurnSignal::None;
	}
	else
	{
		PreHazardSignal = TurnSignal;
		TurnSignal = ENYCTurnSignal::Hazard;
	}
	FlasherTime = 0.f;
	bFlasherOn = TurnSignal != ENYCTurnSignal::None;
	OnRelayClick.Broadcast(bFlasherOn);
}

void UNYCVehicleLightsComponent::UpdateSelfCancel(float SteeringInput, float DeltaTime)
{
	if (TurnSignal != ENYCTurnSignal::Left && TurnSignal != ENYCTurnSignal::Right)
	{
		SelfCancelIntegral = 0.f;
		bSelfCancelArmed = false;
		return;
	}
	// The stalk cancels when the wheel has turned past ~60 % of lock in the signalled direction and come back.
	const float Signed = TurnSignal == ENYCTurnSignal::Left ? -SteeringInput : SteeringInput;
	SelfCancelIntegral += Signed * DeltaTime;
	if (Signed > 0.35f)
	{
		bSelfCancelArmed = true;
	}
	if (bSelfCancelArmed && Signed < 0.08f && SelfCancelIntegral > 0.25f)
	{
		SetTurnSignal(ENYCTurnSignal::None);
	}
}

void UNYCVehicleLightsComponent::SetBrake(bool bBraking)
{
	bBrakeOn = bBraking;
}

void UNYCVehicleLightsComponent::SetReverse(bool bReversing)
{
	bReverseOn = bReversing;
}

void UNYCVehicleLightsComponent::SetFogLights(bool bOn)
{
	bFogOn = bOn;
}

void UNYCVehicleLightsComponent::SetInteriorLight(bool bOn)
{
	bInteriorOn = bOn;
}

void UNYCVehicleLightsComponent::SetDashBrightness(float Brightness01)
{
	DashBrightness = FMath::Clamp(Brightness01, 0.f, 1.f);
}

void UNYCVehicleLightsComponent::SetLampBroken(FName SlotName, float Broken01)
{
	if (FLamp* Lamp = Find(SlotName))
	{
		Lamp->Broken = FMath::Clamp(Broken01, 0.f, 1.f);
		if (Lamp->Material != nullptr)
		{
			Lamp->Material->SetScalarParameterValue(FName(NYCVehicleParams::Broken), Lamp->Broken);
		}
	}
}

bool UNYCVehicleLightsComponent::AreHeadlightsOn() const
{
	return HeadlightMode == ENYCHeadlightMode::Low || HeadlightMode == ENYCHeadlightMode::High ||
		   HeadlightMode == ENYCHeadlightMode::Automatic;
}

bool UNYCVehicleLightsComponent::IsSideBroken(bool bLeft) const
{
	const FName Slots[3] = {bLeft ? FName(NYCVehicleSlots::IndicatorFrontLeft) : FName(NYCVehicleSlots::IndicatorFrontRight),
							bLeft ? FName(NYCVehicleSlots::IndicatorRearLeft) : FName(NYCVehicleSlots::IndicatorRearRight),
							bLeft ? FName(NYCVehicleSlots::IndicatorSideLeft) : FName(NYCVehicleSlots::IndicatorSideRight)};
	for (const FLamp& Lamp : Lamps)
	{
		for (const FName& Slot : Slots)
		{
			if (Lamp.Slot == Slot && Lamp.Broken > 0.5f)
			{
				return true;
			}
		}
	}
	return false;
}

void UNYCVehicleLightsComponent::UpdateFlasher(float DeltaTime)
{
	if (TurnSignal == ENYCTurnSignal::None)
	{
		if (bFlasherOn)
		{
			bFlasherOn = false;
			OnRelayClick.Broadcast(false);
		}
		FlasherTime = 0.f;
		return;
	}

	const bool bLeftActive = TurnSignal == ENYCTurnSignal::Left || TurnSignal == ENYCTurnSignal::Hazard;
	const bool bRightActive = TurnSignal == ENYCTurnSignal::Right || TurnSignal == ENYCTurnSignal::Hazard;
	const bool bHyper = (bLeftActive && IsSideBroken(true)) || (bRightActive && IsSideBroken(false));
	const float Period = bHyper ? kHyperFlashPeriod : kFlashPeriod;

	FlasherTime += DeltaTime;
	while (FlasherTime >= Period * 0.5f)
	{
		FlasherTime -= Period * 0.5f;
		bFlasherOn = !bFlasherOn;
		OnRelayClick.Broadcast(bFlasherOn);
	}
}

void UNYCVehicleLightsComponent::PushToMaterials(float DeltaTime)
{
	for (FLamp& Lamp : Lamps)
	{
		const float Target = Lamp.Target * (1.f - Lamp.Broken);
		const float Tau = Target > Lamp.Current ? Lamp.RiseSeconds : Lamp.FallSeconds;
		// First-order lamp response; the exponential form is stable at any frame rate.
		const float Alpha = Tau > KINDA_SMALL_NUMBER ? 1.f - FMath::Exp(-DeltaTime / Tau) : 1.f;
		Lamp.Current = FMath::Lerp(Lamp.Current, Target, FMath::Clamp(Alpha, 0.f, 1.f));
		if (Lamp.Material != nullptr)
		{
			Lamp.Material->SetScalarParameterValue(FName(NYCVehicleParams::Emissive), Lamp.Current * EmissiveScale);
		}
	}
}

void UNYCVehicleLightsComponent::UpdateRealLights()
{
	const FLamp* Head = nullptr;
	for (const FLamp& Lamp : Lamps)
	{
		if (Lamp.Slot == FName(NYCVehicleSlots::HeadLeft))
		{
			Head = &Lamp;
			break;
		}
	}
	const float HeadLevel = Head != nullptr ? Head->Current : (AreHeadlightsOn() ? 1.f : 0.f);
	const bool bHigh = HeadlightMode == ENYCHeadlightMode::High;
	const float Intensity = HeadLevel * (bHigh ? HighBeamIntensityLumens : HeadlightIntensityLumens);

	if (HeadlightLeft != nullptr)
	{
		HeadlightLeft->SetIntensity(Intensity);
		HeadlightLeft->SetOuterConeAngle(bHigh ? 28.f : 42.f);
		HeadlightLeft->SetVisibility(Intensity > 1.f);
	}
	if (HeadlightRight != nullptr)
	{
		HeadlightRight->SetIntensity(Intensity);
		HeadlightRight->SetOuterConeAngle(bHigh ? 28.f : 42.f);
		HeadlightRight->SetVisibility(Intensity > 1.f);
	}
	if (ReverseLight != nullptr)
	{
		const float Level = bReverseOn ? 320.f : 0.f;
		ReverseLight->SetIntensity(Level);
		ReverseLight->SetVisibility(Level > 1.f);
	}
	if (InteriorLight != nullptr)
	{
		const float Level = bInteriorOn ? 60.f : 0.f;
		InteriorLight->SetIntensity(Level);
		InteriorLight->SetVisibility(Level > 0.5f);
	}
}

void UNYCVehicleLightsComponent::TickComponent(float DeltaTime, ELevelTick TickType,
											   FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (Mesh == nullptr || DeltaTime <= 0.f)
	{
		return;
	}

	UpdateFlasher(DeltaTime);

	const bool bMarkerLights = HeadlightMode != ENYCHeadlightMode::Off;
	const bool bLowBeam = AreHeadlightsOn();
	const bool bHighBeam = HeadlightMode == ENYCHeadlightMode::High;
	const bool bDrl = HeadlightMode == ENYCHeadlightMode::DaytimeRunning ||
					  HeadlightMode == ENYCHeadlightMode::Automatic || HeadlightMode == ENYCHeadlightMode::Off;

	SetTarget(FName(NYCVehicleSlots::HeadLeft), bLowBeam ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::HeadRight), bLowBeam ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::HighBeamLeft), bHighBeam ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::HighBeamRight), bHighBeam ? 1.f : 0.f);
	// The DRLs dim rather than switch off when the low beams come on, as the real unit does.
	SetTarget(FName(NYCVehicleSlots::DrlLeft), bDrl ? 1.f : 0.35f);
	SetTarget(FName(NYCVehicleSlots::DrlRight), bDrl ? 1.f : 0.35f);
	SetTarget(FName(NYCVehicleSlots::FogLeft), bFogOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::FogRight), bFogOn ? 1.f : 0.f);

	// Tail lamps glow at 35 % with the marker lights, full under braking; the CHMSL is brake-only.
	const float TailLevel = bBrakeOn ? 1.f : (bMarkerLights ? 0.35f : 0.f);
	SetTarget(FName(NYCVehicleSlots::TailLeft), TailLevel);
	SetTarget(FName(NYCVehicleSlots::TailRight), TailLevel);
	SetTarget(FName(NYCVehicleSlots::BrakeLeft), bBrakeOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::BrakeRight), bBrakeOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::BrakeCentre), bBrakeOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::ReverseLeft), bReverseOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::ReverseRight), bReverseOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::PlateLight), bMarkerLights ? 1.f : 0.f);

	const bool bLeftFlash = bFlasherOn && (TurnSignal == ENYCTurnSignal::Left || TurnSignal == ENYCTurnSignal::Hazard);
	const bool bRightFlash = bFlasherOn && (TurnSignal == ENYCTurnSignal::Right || TurnSignal == ENYCTurnSignal::Hazard);
	SetTarget(FName(NYCVehicleSlots::IndicatorFrontLeft), bLeftFlash ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::IndicatorRearLeft), bLeftFlash ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::IndicatorSideLeft), bLeftFlash ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::IndicatorFrontRight), bRightFlash ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::IndicatorRearRight), bRightFlash ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::IndicatorSideRight), bRightFlash ? 1.f : 0.f);

	SetTarget(FName(NYCVehicleSlots::InteriorLight), bInteriorOn ? 1.f : 0.f);
	SetTarget(FName(NYCVehicleSlots::DashBacklight), DashBrightness);

	PushToMaterials(DeltaTime);
	UpdateRealLights();
}
