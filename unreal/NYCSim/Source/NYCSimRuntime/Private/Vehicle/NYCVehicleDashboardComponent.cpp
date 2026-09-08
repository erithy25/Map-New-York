#include "Vehicle/NYCVehicleDashboardComponent.h"

#include "Blueprint/UserWidget.h"
#include "Components/MeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Vehicle/NYCVehicleAnimInstance.h"
#include "Vehicle/NYCVehicleContract.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

namespace
{
/// Critically damped second-order step: x'' = w^2 (target - x) - 2 w x'. `Tau` is the time constant.
void DampNeedle(float& Value, float& Velocity, float Target, float Tau, float DeltaTime)
{
	const float Omega = 1.f / FMath::Max(0.01f, Tau);
	const float Accel = Omega * Omega * (Target - Value) - 2.f * Omega * Velocity;
	Velocity += Accel * DeltaTime;
	Value += Velocity * DeltaTime;
}

constexpr float kLitresPerUsGallon = 3.785411784f;
constexpr float kMilesPerCm = 1.f / 160934.4f;
}  // namespace

UNYCVehicleDashboardComponent::UNYCVehicleDashboardComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UNYCVehicleDashboardComponent::Initialise(UMeshComponent* InMesh, UNYCVehicleMovementComponent* InMovement)
{
	Mesh = InMesh;
	Movement = InMovement;

	if (const USkeletalMeshComponent* Skeletal = Cast<USkeletalMeshComponent>(Mesh))
	{
		AnimInstance = Cast<UNYCVehicleAnimInstance>(Skeletal->GetAnimInstance());
	}
	if (Mesh == nullptr)
	{
		return;
	}

	auto MakeMaterial = [this](const TCHAR* SlotName) -> UMaterialInstanceDynamic* {
		const int32 Index = FNYCVehicleContract::SlotIndex(Mesh, FName(SlotName));
		return Index != INDEX_NONE ? Mesh->CreateDynamicMaterialInstance(Index) : nullptr;
	};
	GaugeSpeedMaterial = MakeMaterial(NYCVehicleSlots::GaugeSpeed);
	GaugeRpmMaterial = MakeMaterial(NYCVehicleSlots::GaugeRpm);
	GaugeFuelMaterial = MakeMaterial(NYCVehicleSlots::GaugeFuel);
	GaugeTempMaterial = MakeMaterial(NYCVehicleSlots::GaugeTemp);
	ScreenCentreMaterial = MakeMaterial(NYCVehicleSlots::ScreenCentre);
	ScreenClusterMaterial = MakeMaterial(NYCVehicleSlots::ScreenCluster);
}

UWidgetComponent* UNYCVehicleDashboardComponent::CreateCentreScreen(TSubclassOf<UUserWidget> WidgetClass)
{
	AActor* Owner = GetOwner();
	if (Owner == nullptr || Mesh == nullptr || WidgetClass == nullptr)
	{
		return nullptr;
	}
	const FName Socket(NYCVehicleBones::SocketScreenCentre);
	if (!Mesh->DoesSocketExist(Socket))
	{
		UE_LOG(LogNYCSim, Warning,
			   TEXT("Dashboard: socket '%s' is absent from the vehicle mesh; the centre screen is not created "
					"(the GPS is still available on the HUD)."),
			   *Socket.ToString());
		return nullptr;
	}

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();
	const int32 Resolution = FMath::Clamp(Settings.CentreScreenResolution, 64, 2048);

	CentreScreen = NewObject<UWidgetComponent>(Owner, TEXT("NYCCentreScreen"));
	CentreScreen->SetupAttachment(Mesh, Socket);
	CentreScreen->SetWidgetSpace(EWidgetSpace::World);
	CentreScreen->SetWidgetClass(WidgetClass);
	// The 2019 Fusion's SYNC 3 screen is 8 inches diagonal, 16:9 -> 17.7 x 10.0 cm.
	CentreScreen->SetDrawSize(FVector2D(Resolution, Resolution * 10.f / 17.7f));
	CentreScreen->SetDrawAtDesiredSize(false);
	CentreScreen->SetPivot(FVector2D(0.5f, 0.5f));
	CentreScreen->SetTwoSided(false);
	CentreScreen->SetTickWhenOffscreen(false);
	CentreScreen->SetBlendMode(EWidgetBlendMode::Opaque);
	// 1 unreal unit per pixel by default; scale so the widget covers 17.7 cm of glass.
	CentreScreen->SetRelativeScale3D(FVector(17.7f / static_cast<float>(Resolution)));
	CentreScreen->SetRelativeRotation(FRotator(0.f, 90.f, 0.f));
	CentreScreen->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	CentreScreen->RegisterComponent();

	if (ScreenCentreMaterial != nullptr)
	{
		if (UTextureRenderTarget2D* Target = CentreScreen->GetRenderTarget())
		{
			ScreenCentreMaterial->SetTextureParameterValue(FName(NYCVehicleParams::ScreenTexture), Target);
		}
	}
	return CentreScreen;
}

void UNYCVehicleDashboardComponent::SetBacklight(float Value01)
{
	Backlight = FMath::Clamp(Value01, 0.f, 1.f);
}

FString UNYCVehicleDashboardComponent::GetGearText() const
{
	if (Movement == nullptr)
	{
		return TEXT("P");
	}
	const int32 Gear = Movement->GetCurrentGear();
	if (Gear < 0)
	{
		return TEXT("R");
	}
	if (Gear == 0)
	{
		return Movement->GetSpeedKph() < 0.5f ? TEXT("P") : TEXT("N");
	}
	return TEXT("D");
}

void UNYCVehicleDashboardComponent::UpdateNeedles(float DeltaTime)
{
	if (Movement == nullptr)
	{
		return;
	}
	const float SpeedTarget = FMath::Clamp(Movement->GetSpeedMph() / FMath::Max(1.f, SpeedoMaxMph), 0.f, 1.f);
	const float RpmTarget =
		FMath::Clamp(Movement->GetEngineRotationSpeed() / FMath::Max(1.f, TachoMaxRpm), 0.f, 1.f);
	const float FuelTarget = FMath::Clamp(Movement->GetFuelFraction(), 0.f, 1.f);
	// Coolant temperature: the needle sits at 0.5 (the "normal" band) once warm; it takes about 4 minutes.
	const float TempTarget = Movement->IsEngineRunning() ? 0.5f : 0.12f;

	DampNeedle(SpeedNeedle, SpeedNeedleVel, SpeedTarget, 0.25f, DeltaTime);
	DampNeedle(RpmNeedle, RpmNeedleVel, RpmTarget, 0.12f, DeltaTime);
	FuelNeedle = FMath::FInterpTo(FuelNeedle, FuelTarget, DeltaTime, 1.f / 2.5f);
	TempNeedle = FMath::FInterpTo(TempNeedle, TempTarget, DeltaTime, 1.f / 60.f);

	SpeedNeedle = FMath::Clamp(SpeedNeedle, 0.f, 1.05f);
	RpmNeedle = FMath::Clamp(RpmNeedle, 0.f, 1.05f);

	if (AnimInstance != nullptr)
	{
		FNYCVehicleAnimState& State = AnimInstance->AnimState;
		State.NeedleSpeedDeg = SpeedNeedle * SpeedoSweepDeg;
		State.NeedleRpmDeg = RpmNeedle * TachoSweepDeg;
		State.NeedleFuelDeg = FuelNeedle * SmallGaugeSweepDeg;
		State.NeedleTempDeg = TempNeedle * SmallGaugeSweepDeg;
		// Gear selector detents: P 0°, R 8°, N 16°, D 24°.
		const int32 Gear = Movement->GetCurrentGear();
		const float Detent = Gear < 0 ? 8.f : (Gear == 0 ? (Movement->GetSpeedKph() < 0.5f ? 0.f : 16.f) : 24.f);
		State.GearSelectorDeg = Detent;
	}
}

void UNYCVehicleDashboardComponent::UpdateGaugeMaterials()
{
	const FName ValueParam(NYCVehicleParams::GaugeValue);
	const FName EmissiveParam(NYCVehicleParams::Emissive);
	if (GaugeSpeedMaterial != nullptr)
	{
		GaugeSpeedMaterial->SetScalarParameterValue(ValueParam, SpeedNeedle);
		GaugeSpeedMaterial->SetScalarParameterValue(EmissiveParam, Backlight);
	}
	if (GaugeRpmMaterial != nullptr)
	{
		GaugeRpmMaterial->SetScalarParameterValue(ValueParam, RpmNeedle);
		GaugeRpmMaterial->SetScalarParameterValue(EmissiveParam, Backlight);
	}
	if (GaugeFuelMaterial != nullptr)
	{
		GaugeFuelMaterial->SetScalarParameterValue(ValueParam, FuelNeedle);
		GaugeFuelMaterial->SetScalarParameterValue(EmissiveParam, Backlight);
	}
	if (GaugeTempMaterial != nullptr)
	{
		GaugeTempMaterial->SetScalarParameterValue(ValueParam, TempNeedle);
		GaugeTempMaterial->SetScalarParameterValue(EmissiveParam, Backlight);
	}
	if (ScreenCentreMaterial != nullptr)
	{
		ScreenCentreMaterial->SetScalarParameterValue(EmissiveParam, FMath::Max(0.35f, Backlight));
	}
	if (ScreenClusterMaterial != nullptr)
	{
		ScreenClusterMaterial->SetScalarParameterValue(EmissiveParam, FMath::Max(0.35f, Backlight));
		ScreenClusterMaterial->SetScalarParameterValue(FName(TEXT("WarningMask")), static_cast<float>(WarningMask));
	}
}

void UNYCVehicleDashboardComponent::UpdateTrip(float DeltaTime)
{
	if (Movement == nullptr)
	{
		return;
	}
	const float DistanceMiles = FMath::Abs(Movement->GetForwardSpeed()) * DeltaTime * kMilesPerCm;
	OdometerMiles += DistanceMiles;
	TripMiles += DistanceMiles;

	// Instantaneous economy: fuel actually burned over a 5 s sliding window.
	const float FuelNow = Movement->GetFuelFraction() * 53.f;
	if (LastFuelLitres < 0.f)
	{
		LastFuelLitres = FuelNow;
	}
	const float Burned = FMath::Max(0.f, LastFuelLitres - FuelNow);
	LastFuelLitres = FuelNow;
	MpgAccumulator += Burned;
	MpgWindow += DeltaTime;
	MpgDistanceMiles += DistanceMiles;
	if (MpgWindow >= 5.f)
	{
		const float Gallons = MpgAccumulator / kLitresPerUsGallon;
		InstantMpg = Gallons > 1e-5f ? MpgDistanceMiles / Gallons : 99.9f;
		InstantMpg = FMath::Clamp(InstantMpg, 0.f, 99.9f);
		MpgAccumulator = 0.f;
		MpgWindow = 0.f;
		MpgDistanceMiles = 0.f;
	}

	// Warning lamps that the dashboard owns itself.
	int32 Mask = WarningMask & ~(static_cast<int32>(ENYCWarningLamp::LowFuel) |
								 static_cast<int32>(ENYCWarningLamp::Battery));
	if (Movement->GetFuelFraction() < 0.12f)
	{
		Mask |= static_cast<int32>(ENYCWarningLamp::LowFuel);
	}
	if (Movement->GetBatteryFraction() < 0.10f)
	{
		Mask |= static_cast<int32>(ENYCWarningLamp::Battery);
	}
	WarningMask = Mask;
}

void UNYCVehicleDashboardComponent::TickComponent(float DeltaTime, ELevelTick TickType,
												  FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (DeltaTime <= 0.f || Movement == nullptr)
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
	UpdateNeedles(DeltaTime);
	UpdateGaugeMaterials();
	UpdateTrip(DeltaTime);
}
