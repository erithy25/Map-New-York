#include "Vehicle/NYCVehicleBodyComponent.h"

#include "Components/MeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Vehicle/NYCVehicleAnimInstance.h"
#include "Vehicle/NYCVehicleContract.h"

namespace
{
/// The five intermittent delay detents on the stalk, seconds between sweeps.
constexpr float kIntermittentDelays[5] = {0.8f, 2.0f, 4.0f, 7.0f, 12.0f};
}  // namespace

UNYCVehicleBodyComponent::UNYCVehicleBodyComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UNYCVehicleBodyComponent::Initialise(UMeshComponent* InMesh)
{
	Mesh = InMesh;
	if (const USkeletalMeshComponent* Skeletal = Cast<USkeletalMeshComponent>(Mesh))
	{
		AnimInstance = Cast<UNYCVehicleAnimInstance>(Skeletal->GetAnimInstance());
	}
}

// ------------------------------------------------------------------------------------------------- wipers

void UNYCVehicleBodyComponent::SetWiperMode(ENYCWiperMode Mode)
{
	WiperMode = Mode;
	if (Mode == ENYCWiperMode::Off)
	{
		// The wiper always finishes the sweep it is on and parks; it never stops mid-glass.
		bWiperRunning = WiperPhase > 0.001f;
	}
	else
	{
		bWiperRunning = true;
		WiperDelayTimer = 0.f;
	}
}

void UNYCVehicleBodyComponent::CycleWiperMode()
{
	switch (WiperMode)
	{
	case ENYCWiperMode::Off: SetWiperMode(ENYCWiperMode::Intermittent); break;
	case ENYCWiperMode::Intermittent: SetWiperMode(ENYCWiperMode::Low); break;
	case ENYCWiperMode::Low: SetWiperMode(ENYCWiperMode::High); break;
	case ENYCWiperMode::High: SetWiperMode(ENYCWiperMode::Automatic); break;
	case ENYCWiperMode::Automatic:
	default: SetWiperMode(ENYCWiperMode::Off); break;
	}
}

void UNYCVehicleBodyComponent::MistWipe()
{
	bMistPending = true;
	bWiperRunning = true;
}

void UNYCVehicleBodyComponent::SetIntermittentSetting(int32 Setting)
{
	IntermittentSetting = FMath::Clamp(Setting, 0, 4);
}

void UNYCVehicleBodyComponent::SetRainRate(float MillimetresPerHour)
{
	RainRateMmH = FMath::Max(0.f, MillimetresPerHour);
}

float UNYCVehicleBodyComponent::CurrentSweepSeconds() const
{
	// One cycle is out and back; the half-cycle (one sweep) is what the phase counts in 0..1 steps.
	float CyclesPerMinute = WiperLowCyclesPerMinute;
	switch (WiperMode)
	{
	case ENYCWiperMode::High:
		CyclesPerMinute = WiperHighCyclesPerMinute;
		break;
	case ENYCWiperMode::Automatic:
		// The rain sensor picks the speed: intermittent below 1 mm/h, low to 6 mm/h, high above.
		CyclesPerMinute = RainRateMmH > 6.f ? WiperHighCyclesPerMinute : WiperLowCyclesPerMinute;
		break;
	default:
		break;
	}
	return 60.f / FMath::Max(1.f, CyclesPerMinute) * 0.5f;
}

float UNYCVehicleBodyComponent::IntermittentDelaySeconds() const
{
	if (WiperMode == ENYCWiperMode::Automatic)
	{
		// Rain-sensing delay: 12 s at a trace, down to a continuous sweep at 6 mm/h.
		if (RainRateMmH >= 6.f)
		{
			return 0.f;
		}
		const float T = FMath::Clamp(RainRateMmH / 6.f, 0.f, 1.f);
		return FMath::Lerp(12.f, 0.f, T);
	}
	return kIntermittentDelays[FMath::Clamp(IntermittentSetting, 0, 4)];
}

void UNYCVehicleBodyComponent::UpdateWipers(float DeltaTime)
{
	// Water accumulates at the rain rate and is cleared by a sweep passing over the glass.
	const float Accumulation = FMath::Clamp(RainRateMmH / 8.f, 0.f, 1.f);
	ScreenWetness = FMath::Clamp(ScreenWetness + (Accumulation - 0.05f) * DeltaTime * 0.6f, 0.f, 1.f);

	const bool bWantsRun = bMistPending || WiperMode == ENYCWiperMode::Low || WiperMode == ENYCWiperMode::High ||
						   (WiperMode == ENYCWiperMode::Intermittent) ||
						   (WiperMode == ENYCWiperMode::Automatic && RainRateMmH > 0.15f);

	if (!bWiperRunning)
	{
		if (bWantsRun)
		{
			bWiperRunning = true;
			WiperDelayTimer = 0.f;
		}
		else
		{
			WiperAngle = FMath::FInterpConstantTo(WiperAngle, 0.f, DeltaTime, WiperSweepDeg * 2.f);
			return;
		}
	}

	if (WiperDelayTimer > 0.f)
	{
		WiperDelayTimer -= DeltaTime;
		WiperAngle = 0.f;
		if (WiperDelayTimer > 0.f)
		{
			return;
		}
	}

	const float SweepSeconds = FMath::Max(0.05f, CurrentSweepSeconds());
	WiperPhase += DeltaTime / SweepSeconds;

	// Track sweep ends so the audio gets one event per pass, with the dryness that makes rubber squeak.
	const int32 Half = static_cast<int32>(WiperPhase);
	if (Half != LastSweepHalf)
	{
		LastSweepHalf = Half;
		OnWiperSweep.Broadcast(1.f - ScreenWetness);
		// A sweep clears most of the water from the swept area.
		ScreenWetness = FMath::Max(0.f, ScreenWetness - 0.55f);
	}

	if (WiperPhase >= 2.f)
	{
		// A full cycle finished with the blade back on the park peg.
		WiperPhase = 0.f;
		LastSweepHalf = -1;
		bMistPending = false;
		WiperAngle = 0.f;

		const bool bContinuous = WiperMode == ENYCWiperMode::Low || WiperMode == ENYCWiperMode::High ||
								 (WiperMode == ENYCWiperMode::Automatic && RainRateMmH >= 6.f);
		if (WiperMode == ENYCWiperMode::Off ||
			(WiperMode == ENYCWiperMode::Automatic && RainRateMmH <= 0.15f))
		{
			bWiperRunning = false;  // parked
		}
		else if (!bContinuous)
		{
			WiperDelayTimer = IntermittentDelaySeconds();
		}
	}
	else
	{
		// Triangle sweep with eased ends, which is what the four-bar linkage produces.
		const float T = WiperPhase < 1.f ? WiperPhase : 2.f - WiperPhase;
		const float Eased = T * T * (3.f - 2.f * T);
		WiperAngle = Eased * WiperSweepDeg;
	}
}

// ------------------------------------------------------------------------------------------------ windows

void UNYCVehicleBodyComponent::SetWindowTarget(int32 WindowIndex, float Target01)
{
	if (WindowIndex >= 0 && WindowIndex < 4)
	{
		WindowTarget[WindowIndex] = FMath::Clamp(Target01, 0.f, 1.f);
	}
}

void UNYCVehicleBodyComponent::NudgeWindow(int32 WindowIndex, float Direction)
{
	if (WindowIndex < 0 || WindowIndex >= 4)
	{
		return;
	}
	// A held switch moves the glass; the target follows the current position so releasing stops it.
	WindowTarget[WindowIndex] = FMath::Clamp(WindowOpen[WindowIndex] + FMath::Sign(Direction) * 0.06f, 0.f, 1.f);
}

void UNYCVehicleBodyComponent::ExpressWindow(int32 WindowIndex, bool bDown)
{
	SetWindowTarget(WindowIndex, bDown ? 1.f : 0.f);
}

float UNYCVehicleBodyComponent::GetWindowOpen(int32 WindowIndex) const
{
	return (WindowIndex >= 0 && WindowIndex < 4) ? WindowOpen[WindowIndex] : 0.f;
}

float UNYCVehicleBodyComponent::GetCabinOpenness() const
{
	return (WindowOpen[0] + WindowOpen[1]) * 0.5f;
}

void UNYCVehicleBodyComponent::UpdateWindows(float DeltaTime)
{
	for (int32 i = 0; i < 4; ++i)
	{
		const float TravelSeconds = i < 2 ? FrontWindowTravelSeconds : RearWindowTravelSeconds;
		const float Rate = 1.f / FMath::Max(0.1f, TravelSeconds);
		WindowOpen[i] = FMath::FInterpConstantTo(WindowOpen[i], WindowTarget[i], DeltaTime, Rate);
	}
}

// -------------------------------------------------------------------------------------------------- doors

void UNYCVehicleBodyComponent::SetDoorOpen(int32 DoorIndex, bool bOpen)
{
	if (DoorIndex < 0 || DoorIndex >= 4)
	{
		return;
	}
	const bool bWasOpen = DoorTarget[DoorIndex] > 0.5f;
	DoorTarget[DoorIndex] = bOpen ? 1.f : 0.f;
	if (bWasOpen != bOpen)
	{
		OnDoorChanged.Broadcast(DoorIndex, bOpen);
	}
}

bool UNYCVehicleBodyComponent::IsDoorOpen(int32 DoorIndex) const
{
	return (DoorIndex >= 0 && DoorIndex < 4) && DoorOpen[DoorIndex] > 0.02f;
}

bool UNYCVehicleBodyComponent::IsAnyDoorAjar() const
{
	for (int32 i = 0; i < 4; ++i)
	{
		if (DoorOpen[i] > 0.02f)
		{
			return true;
		}
	}
	return HoodOpen > 0.02f || TrunkOpen > 0.02f;
}

void UNYCVehicleBodyComponent::UpdateDoors(float DeltaTime)
{
	const float Rate = 1.f / FMath::Max(0.05f, DoorSwingSeconds);
	for (int32 i = 0; i < 4; ++i)
	{
		DoorOpen[i] = FMath::FInterpConstantTo(DoorOpen[i], DoorTarget[i], DeltaTime, Rate);
	}
	HoodOpen = FMath::FInterpConstantTo(HoodOpen, HoodTarget, DeltaTime, 1.f / 1.2f);
	TrunkOpen = FMath::FInterpConstantTo(TrunkOpen, TrunkTarget, DeltaTime, 1.f / 1.2f);
	MirrorFold = FMath::FInterpConstantTo(MirrorFold, MirrorFoldTarget, DeltaTime, 1.f / FMath::Max(0.1f, MirrorFoldSeconds));
}

// --------------------------------------------------------------------------------------------------- horn

void UNYCVehicleBodyComponent::SetHorn(bool bPressed)
{
	if (bHorn != bPressed)
	{
		bHorn = bPressed;
		OnHornChanged.Broadcast(bHorn);
	}
}

// --------------------------------------------------------------------------------------------------- tick

void UNYCVehicleBodyComponent::PushAnimState()
{
	if (AnimInstance == nullptr)
	{
		return;
	}
	FNYCVehicleAnimState& State = AnimInstance->AnimState;
	// Both front blades sweep together; the right blade is mirrored, which the rig's local axis handles, so both
	// receive the same positive angle. The rear blade runs at half the sweep.
	State.WiperDeg[0] = WiperAngle;
	State.WiperDeg[1] = WiperAngle;
	State.WiperDeg[2] = WiperAngle * 0.5f;

	for (int32 i = 0; i < 4; ++i)
	{
		State.DoorDeg[i] = DoorOpen[i] * DoorOpenDeg;
		State.WindowDropCm[i] = WindowOpen[i] * WindowGlassHeightCm;
	}
	State.HoodDeg = HoodOpen * 62.f;
	State.TrunkDeg = TrunkOpen * 72.f;
	State.MirrorFoldDeg[0] = MirrorFold * MirrorFoldDeg;
	State.MirrorFoldDeg[1] = -MirrorFold * MirrorFoldDeg;
}

void UNYCVehicleBodyComponent::TickComponent(float DeltaTime, ELevelTick TickType,
											 FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (DeltaTime <= 0.f)
	{
		return;
	}
	if (AnimInstance == nullptr)
	{
		if (const USkeletalMeshComponent* Skeletal = Cast<USkeletalMeshComponent>(Mesh))
		{
			AnimInstance = Cast<UNYCVehicleAnimInstance>(Skeletal->GetAnimInstance());
		}
	}

	UpdateWipers(DeltaTime);
	UpdateWindows(DeltaTime);
	UpdateDoors(DeltaTime);
	PushAnimState();
}
