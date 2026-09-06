#include "Audio/NYCVehicleAudioComponent.h"

#include "Audio/NYCProceduralSourceComponent.h"
#include "Audio/NYCRadioSubsystem.h"
#include "Components/AudioComponent.h"
#include "Components/MeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "NYCSimRuntime.h"
#include "Player/NYCGameplaySettings.h"
#include "Sound/SoundBase.h"
#include "Vehicle/NYCVehicleBodyComponent.h"
#include "Vehicle/NYCVehicleContract.h"
#include "Vehicle/NYCVehicleLightsComponent.h"
#include "Vehicle/NYCVehicleMovementComponent.h"

namespace
{
constexpr float kCmPerMetre = 100.f;
}

UNYCVehicleAudioComponent::UNYCVehicleAudioComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UNYCVehicleAudioComponent::BeginPlay()
{
	Super::BeginPlay();
}

UNYCProceduralSourceComponent* UNYCVehicleAudioComponent::MakeSource(const TCHAR* Name, uint8 Kind, FName Socket,
																	 float Gain)
{
	AActor* Owner = GetOwner();
	if (Owner == nullptr)
	{
		return nullptr;
	}
	UNYCProceduralSourceComponent* Source = NewObject<UNYCProceduralSourceComponent>(Owner, Name);
	Source->SetKind(static_cast<ENYCSourceKind>(Kind));
	Source->SetSourceGain(Gain);
	USceneComponent* Parent = Mesh != nullptr ? static_cast<USceneComponent*>(Mesh) : static_cast<USceneComponent*>(this);
	const FName UseSocket = (Mesh != nullptr && Mesh->DoesSocketExist(Socket)) ? Socket : NAME_None;
	Source->SetupAttachment(Parent, UseSocket);
	Source->RegisterComponent();
	Source->Start();
	return Source;
}

UAudioComponent* UNYCVehicleAudioComponent::TryMakeMetaSound(const TCHAR* Name, const FSoftObjectPath& Path,
															 FName Socket)
{
	if (Path.IsNull())
	{
		return nullptr;
	}
	USoundBase* Sound = Cast<USoundBase>(Path.TryLoad());
	if (Sound == nullptr)
	{
		return nullptr;
	}
	AActor* Owner = GetOwner();
	if (Owner == nullptr)
	{
		return nullptr;
	}
	UAudioComponent* Component = NewObject<UAudioComponent>(Owner, Name);
	Component->bAutoActivate = false;
	Component->SetSound(Sound);
	USceneComponent* Parent = Mesh != nullptr ? static_cast<USceneComponent*>(Mesh) : static_cast<USceneComponent*>(this);
	const FName UseSocket = (Mesh != nullptr && Mesh->DoesSocketExist(Socket)) ? Socket : NAME_None;
	Component->SetupAttachment(Parent, UseSocket);
	Component->RegisterComponent();
	Component->Play();
	bUsingMetaSounds = true;
	return Component;
}

void UNYCVehicleAudioComponent::Initialise(UMeshComponent* InMesh, UNYCVehicleMovementComponent* InMovement,
										   UNYCVehicleBodyComponent* InBody, UNYCVehicleLightsComponent* InLights)
{
	Mesh = InMesh;
	Movement = InMovement;
	Body = InBody;
	Lights = InLights;
	if (bInitialised)
	{
		return;
	}
	bInitialised = true;

	const UNYCGameplaySettings& Settings = UNYCGameplaySettings::Get();

	// MetaSound sources take precedence when the assets exist; otherwise the C++ synthesisers run.
	EngineMetaSound = TryMakeMetaSound(TEXT("NYCEngineMS"), Settings.EngineMetaSound,
									   FName(NYCVehicleBones::SocketEngineBay));
	TyreMetaSound = TryMakeMetaSound(TEXT("NYCTyreMS"), Settings.TyreMetaSound, FName(NYCVehicleBones::WheelRearLeft));
	WindMetaSound = TryMakeMetaSound(TEXT("NYCWindMS"), Settings.WindMetaSound,
									 FName(NYCVehicleBones::SocketCameraInterior));
	RainMetaSound = TryMakeMetaSound(TEXT("NYCRainMS"), Settings.RainMetaSound,
									 FName(NYCVehicleBones::SocketCameraInterior));
	WiperMetaSound = TryMakeMetaSound(TEXT("NYCWiperMS"), Settings.WiperMetaSound, FName(NYCVehicleBones::WiperLeft));

	if (EngineMetaSound == nullptr)
	{
		EngineSource = MakeSource(TEXT("NYCEngineSynth"), static_cast<uint8>(ENYCSourceKind::Engine),
								  FName(NYCVehicleBones::SocketEngineBay), 0.9f);
	}
	if (TyreMetaSound == nullptr)
	{
		TyreSource = MakeSource(TEXT("NYCTyreSynth"), static_cast<uint8>(ENYCSourceKind::Tyre),
								FName(NYCVehicleBones::WheelRearLeft), 0.8f);
	}
	if (WindMetaSound == nullptr)
	{
		WindSource = MakeSource(TEXT("NYCWindSynth"), static_cast<uint8>(ENYCSourceKind::Wind),
								FName(NYCVehicleBones::SocketCameraInterior), 0.7f);
	}
	if (RainMetaSound == nullptr)
	{
		RainSource = MakeSource(TEXT("NYCRainSynth"), static_cast<uint8>(ENYCSourceKind::Rain),
								FName(NYCVehicleBones::SocketCameraInterior), 0.8f);
	}
	if (WiperMetaSound == nullptr)
	{
		WiperSource = MakeSource(TEXT("NYCWiperSynth"), static_cast<uint8>(ENYCSourceKind::Wiper),
								 FName(NYCVehicleBones::WiperLeft), 0.7f);
	}
	// The horn is always procedural: no licensable recording was available (see the stage report).
	HornSource = MakeSource(TEXT("NYCHornSynth"), static_cast<uint8>(ENYCSourceKind::Horn),
							FName(NYCVehicleBones::SocketHorn), 1.0f);

	// One-shot player for the relay click, impacts and chimes.
	if (AActor* Owner = GetOwner())
	{
		OneShot = NewObject<UAudioComponent>(Owner, TEXT("NYCVehicleOneShot"));
		OneShot->bAutoActivate = false;
		OneShot->SetupAttachment(Mesh != nullptr ? static_cast<USceneComponent*>(Mesh)
												 : static_cast<USceneComponent*>(this));
		OneShot->RegisterComponent();
	}

	ImpactSound = Cast<USoundBase>(
		FSoftObjectPath(FString::Printf(TEXT("%s/collision_crash_1.collision_crash_1"), *Settings.SfxContentRoot))
			.TryLoad());
	GlassSound = Cast<USoundBase>(
		FSoftObjectPath(FString::Printf(TEXT("%s/glass_break_1.glass_break_1"), *Settings.SfxContentRoot)).TryLoad());

	// The head unit lives in the cabin.
	if (UWorld* World = GetWorld())
	{
		if (UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
		{
			Radio->AttachToVehicle(Mesh != nullptr ? static_cast<USceneComponent*>(Mesh)
												   : static_cast<USceneComponent*>(this),
								   FName(NYCVehicleBones::SocketCameraInterior));
		}
	}

	UE_LOG(LogNYCSim, Log, TEXT("Vehicle audio: %s sources in use."),
		   bUsingMetaSounds ? TEXT("MetaSound (with C++ synthesisers where an asset is missing)")
							: TEXT("C++ procedural"));
}

void UNYCVehicleAudioComponent::SetMetaSoundFloat(UAudioComponent* Component, FName Parameter, float Value)
{
	if (Component != nullptr)
	{
		Component->SetFloatParameter(Parameter, Value);
	}
}

void UNYCVehicleAudioComponent::PushParameters(float DeltaTime)
{
	if (Movement == nullptr)
	{
		return;
	}
	const float SpeedMps = FMath::Abs(Movement->GetForwardSpeed()) / kCmPerMetre;
	const float Rpm = Movement->GetEngineRotationSpeed();
	const float Throttle = Movement->GetDriverThrottle();
	const float Load = FMath::Clamp(Throttle * 0.7f + FMath::Clamp(SpeedMps / 30.f, 0.f, 1.f) * 0.3f, 0.f, 1.f);
	const float ElectricMix = Movement->IsEngineRunning() ? 0.f : 1.f;
	const float Roughness = Movement->GetRoughnessSignal();
	const float Wetness = Movement->GetWetness();

	// Slip: how far below the dry-asphalt reference the current grip is, plus the handbrake.
	const float Grip = Movement->GetAverageGrip();
	float Slip = FMath::Clamp(1.f - Grip, 0.f, 1.f) * FMath::Clamp(SpeedMps / 8.f, 0.f, 1.f);
	Slip = FMath::Max(Slip, Movement->GetDriverHandbrake() * FMath::Clamp(SpeedMps / 6.f, 0.f, 1.f));

	const float WindowOpen = Body != nullptr ? Body->GetCabinOpenness() : 0.f;
	const float ScreenWetness = Body != nullptr ? Body->GetScreenWetness() : 0.f;
	// The rain source reads the same rain rate the wipers do; the roof is louder with the windows shut.
	const float RainRate = ScreenWetness * 8.f;

	if (EngineSource != nullptr)
	{
		EngineSource->SetEngine(Rpm, Load, Throttle, ElectricMix);
		EngineSource->SetTyre(SpeedMps, 0.f, 0.f, 0.f);  // the electric whine needs the road speed
	}
	if (TyreSource != nullptr)
	{
		TyreSource->SetTyre(SpeedMps, Roughness, Slip, Wetness);
	}
	if (WindSource != nullptr)
	{
		WindSource->SetWind(SpeedMps, WindowOpen);
	}
	if (RainSource != nullptr)
	{
		RainSource->SetRain(RainRate * (1.f - 0.4f * WindowOpen), ScreenWetness);
	}

	SetMetaSoundFloat(EngineMetaSound, FName(TEXT("RPM")), Rpm);
	SetMetaSoundFloat(EngineMetaSound, FName(TEXT("Load")), Load);
	SetMetaSoundFloat(EngineMetaSound, FName(TEXT("Throttle")), Throttle);
	SetMetaSoundFloat(EngineMetaSound, FName(TEXT("ElectricMix")), ElectricMix);
	SetMetaSoundFloat(TyreMetaSound, FName(TEXT("Speed")), SpeedMps);
	SetMetaSoundFloat(TyreMetaSound, FName(TEXT("Roughness")), Roughness);
	SetMetaSoundFloat(TyreMetaSound, FName(TEXT("Slip")), Slip);
	SetMetaSoundFloat(TyreMetaSound, FName(TEXT("Wetness")), Wetness);
	SetMetaSoundFloat(WindMetaSound, FName(TEXT("Speed")), SpeedMps);
	SetMetaSoundFloat(WindMetaSound, FName(TEXT("WindowOpen")), WindowOpen);
	SetMetaSoundFloat(RainMetaSound, FName(TEXT("RainRate")), RainRate);
	SetMetaSoundFloat(RainMetaSound, FName(TEXT("WiperWet")), ScreenWetness);
}

void UNYCVehicleAudioComponent::HandleHorn(bool bPressed)
{
	if (HornSource != nullptr)
	{
		HornSource->SetHornPressed(bPressed);
	}
}

void UNYCVehicleAudioComponent::HandleWiperSweep(float DryFactor)
{
	if (WiperSource != nullptr)
	{
		WiperSource->TriggerWiperSweep(DryFactor);
	}
	SetMetaSoundFloat(WiperMetaSound, FName(TEXT("Dryness")), DryFactor);
	if (WiperMetaSound != nullptr)
	{
		WiperMetaSound->SetTriggerParameter(FName(TEXT("Sweep")));
	}
}

void UNYCVehicleAudioComponent::HandleIndicatorRelay(bool bOn)
{
	// The relay click is a 4 ms transient; the horn synth is the only oscillator on the car that can produce it
	// without an asset, so the click is played through the one-shot component when a sample exists and is
	// otherwise left silent rather than faked with something that does not sound like a relay.
	if (OneShot == nullptr || OneShot->Sound == nullptr)
	{
		return;
	}
	if (bOn)
	{
		OneShot->Play();
	}
}

void UNYCVehicleAudioComponent::HandleImpact(FVector WorldLocation, float Severity, uint8 Region)
{
	(void)Region;
	UWorld* World = GetWorld();
	if (World == nullptr)
	{
		return;
	}
	if (ImpactSound != nullptr)
	{
		UGameplayStatics::PlaySoundAtLocation(World, ImpactSound, WorldLocation,
											  FMath::Clamp(0.3f + Severity, 0.f, 1.5f),
											  FMath::Lerp(1.15f, 0.85f, FMath::Clamp(Severity, 0.f, 1.f)));
	}
	if (GlassSound != nullptr && Severity > 0.45f)
	{
		UGameplayStatics::PlaySoundAtLocation(World, GlassSound, WorldLocation, FMath::Clamp(Severity, 0.f, 1.f));
	}
}

void UNYCVehicleAudioComponent::NextRadioStation()
{
	if (UWorld* World = GetWorld())
	{
		if (UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
		{
			Radio->NextStation();
		}
	}
}

void UNYCVehicleAudioComponent::PreviousRadioStation()
{
	if (UWorld* World = GetWorld())
	{
		if (UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
		{
			Radio->PreviousStation();
		}
	}
}

void UNYCVehicleAudioComponent::ToggleRadioPower()
{
	if (UWorld* World = GetWorld())
	{
		if (UNYCRadioSubsystem* Radio = World->GetSubsystem<UNYCRadioSubsystem>())
		{
			Radio->SetPowerOn(!Radio->IsPowerOn());
		}
	}
}

FString UNYCVehicleAudioComponent::GetRadioText() const
{
	const UWorld* World = GetWorld();
	const UNYCRadioSubsystem* Radio = World != nullptr ? World->GetSubsystem<UNYCRadioSubsystem>() : nullptr;
	return Radio != nullptr ? Radio->GetDisplayText() : FString();
}

void UNYCVehicleAudioComponent::TickComponent(float DeltaTime, ELevelTick TickType,
											  FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (DeltaTime <= 0.f)
	{
		return;
	}
	// The wipers push their own rain rate through the body component; keep them in step with the weather.
	if (Body != nullptr && Movement != nullptr)
	{
		// Wetness is 0..1; the wiper model wants mm/h, and 8 mm/h is a soaked road.
		Body->SetRainRate(Movement->GetWetness() * 8.f);
	}
	PushParameters(DeltaTime);
}
