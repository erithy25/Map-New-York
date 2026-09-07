#include "Sky/NYCSkyTimeSubsystem.h"

#include "CoreAdapter/NYCGeo.h"
#include "NYCSimRuntime.h"
#include "World/NYCSimWorldSettings.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"

namespace
{
	/** Sky/ephemeris update period. The sun moves 0.0042 deg/s, so 5 Hz is far below the visible threshold. */
	TAutoConsoleVariable<float> CVarSkyHz(
		TEXT("nycsim.Sky.Hz"), 5.f,
		TEXT("Ephemeris and sky-actor update rate in Hz."), ECVF_Default);

	TAutoConsoleVariable<float> CVarCloudSunAttenuation(
		TEXT("nycsim.Sky.CloudSunAttenuation"), 0.55f,
		TEXT("How much total cloud cover dims the direct sun light (0 = not at all; set 0 when volumetric cloud ")
		TEXT("shadows are enabled, which already does it)."),
		ECVF_Default);

	TAutoConsoleVariable<int32> CVarSkyDebug(
		TEXT("nycsim.Sky.Debug"), 0,
		TEXT("1: log the sun/moon state at every ephemeris update."), ECVF_Cheat);

	UNYCSkyTimeSubsystem* SkyFor(UWorld* World)
	{
		return World ? World->GetSubsystem<UNYCSkyTimeSubsystem>() : nullptr;
	}

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GPrintSunCmd(
		TEXT("nycsim.PrintSun"),
		TEXT("Prints the simulation clock, sun and moon position, sunrise/transit/sunset, civil twilight and the ")
		TEXT("street-lighting state."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCSkyTimeSubsystem* Sky = SkyFor(World))
				{
					Sky->PrintSun(Ar);
				}
				else
				{
					Ar.Logf(TEXT("nycsim: no sky subsystem in this world"));
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GSetTimeCmd(
		TEXT("nycsim.Sky.SetTime"),
		TEXT("nycsim.Sky.SetTime <ISO-8601 UTC | now>: pins the simulation clock (e.g. 2026-07-12T00:20:00Z)."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				UNYCSkyTimeSubsystem* Sky = SkyFor(World);
				if (!Sky)
				{
					return;
				}
				if (Args.Num() < 1)
				{
					Ar.Logf(TEXT("usage: nycsim.Sky.SetTime 2026-07-12T00:20:00Z   |   nycsim.Sky.SetTime now"));
					return;
				}
				if (Args[0].Equals(TEXT("now"), ESearchCase::IgnoreCase))
				{
					Sky->SetFollowRealTime(true);
					Ar.Logf(TEXT("nycsim: clock follows the system clock again"));
					return;
				}
				if (Sky->SetSimTimeIso8601(Args[0]))
				{
					Ar.Logf(TEXT("nycsim: clock set to %s (local %s)"), *Args[0], *Sky->GetLocalTime().ToString());
				}
				else
				{
					Ar.Logf(TEXT("nycsim: '%s' is not an ISO-8601 UTC instant"), *Args[0]);
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GTimeScaleCmd(
		TEXT("nycsim.Sky.TimeScale"),
		TEXT("nycsim.Sky.TimeScale <x>: seconds of simulated time per real second (1 = real time)."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				UNYCSkyTimeSubsystem* Sky = SkyFor(World);
				if (!Sky)
				{
					return;
				}
				if (Args.Num() >= 1)
				{
					Sky->SetTimeScale(FCString::Atof(*Args[0]));
				}
				Ar.Logf(TEXT("nycsim: sky time scale is now %s"), Args.Num() >= 1 ? *Args[0] : TEXT("(unchanged)"));
			}));
}

bool UNYCSkyTimeSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (!Super::ShouldCreateSubsystem(Outer))
	{
		return false;
	}
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

void UNYCSkyTimeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	Observer.LatitudeDeg = Settings.ObserverLatitudeDeg;
	Observer.LongitudeDeg = Settings.ObserverLongitudeDeg;
	Observer.ElevationMetres = Settings.ObserverAltitudeMetres;
	TimeScale = FMath::Clamp<double>(Settings.TimeScale, 0.0, 3600.0);
	bFollowRealTime = Settings.bUseRealTime;

	SimUnixSeconds = NYCAstro::NowUnixSeconds();
	if (!bFollowRealTime && !Settings.FixedUtcTimeIso8601.IsEmpty())
	{
		double Fixed = 0.0;
		if (NYCAstro::ParseIso8601Utc(Settings.FixedUtcTimeIso8601, Fixed))
		{
			SimUnixSeconds = Fixed;
		}
		else
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Sky: FixedUtcTimeIso8601 '%s' is not ISO-8601; starting from the system clock."),
				*Settings.FixedUtcTimeIso8601);
		}
	}

	if (!Settings.WeatherMaterialParameterCollection.IsEmpty())
	{
		ParameterCollection = LoadObject<UMaterialParameterCollection>(nullptr, *Settings.WeatherMaterialParameterCollection);
		if (!ParameterCollection)
		{
			UE_LOG(LogNYCSim, Warning,
				TEXT("Sky: material parameter collection %s not found; sky parameters are not published to materials. ")
				TEXT("Run Content/Python/import_assets.py to create MPC_Weather."),
				*Settings.WeatherMaterialParameterCollection);
		}
	}

	UpdateEphemeris();
	UE_LOG(LogNYCSim, Log, TEXT("Sky: core %s, observer %.4f %.4f, %s, local %s %s, sun %.2f deg alt / %.2f deg az"),
		*NYCAstro::CoreVersion(), Observer.LatitudeDeg, Observer.LongitudeDeg,
		bFollowRealTime ? TEXT("real time") : TEXT("fixed time"),
		*SimTime.Local.ToString(), *SimTime.TzAbbreviation, Sun.ElevationDeg, Sun.AzimuthDeg);
}

void UNYCSkyTimeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	// Actors are created here, not in Initialize(): world subsystems initialise before the world is ready to spawn.
	EnsureSkyActors();
	UpdateEphemeris();
	ApplyToActors();
	UpdateStreetLighting();
	UpdateStarSphere();
	WriteMaterialParameterCollection();
}

void UNYCSkyTimeSubsystem::Deinitialize()
{
	StreetLightingChanged.Clear();
	SkyUpdated.Clear();
	Super::Deinitialize();
}

bool UNYCSkyTimeSubsystem::IsTickable() const
{
	return IsInitialized();
}

TStatId UNYCSkyTimeSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCSkyTimeSubsystem, STATGROUP_Tickables);
}

void UNYCSkyTimeSubsystem::Tick(float DeltaTime)
{
	if (bFollowRealTime)
	{
		SimUnixSeconds = NYCAstro::NowUnixSeconds();
	}
	else
	{
		SimUnixSeconds += DeltaTime * TimeScale;
	}

	TimeSinceEphemeris += DeltaTime;
	const double Period = 1.0 / FMath::Max(0.1f, CVarSkyHz.GetValueOnGameThread());
	if (TimeSinceEphemeris < Period)
	{
		return;
	}
	TimeSinceEphemeris = 0.0;

	UpdateEphemeris();
	ApplyToActors();
	UpdateStreetLighting();
	UpdateStarSphere();
	WriteMaterialParameterCollection();
	SkyUpdated.Broadcast(Sun.ElevationDeg, Sun.AzimuthDeg);

	if (CVarSkyDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNYCSim, Log, TEXT("Sky: %s %s  sun %.3f/%.3f  moon %.3f/%.3f k=%.3f %s  lights %s"),
			*SimTime.Local.ToString(), *SimTime.TzAbbreviation, Sun.ElevationDeg, Sun.AzimuthDeg,
			Moon.ElevationDeg, Moon.AzimuthDeg, Moon.IlluminatedFraction, *Moon.PhaseName,
			bStreetLightsOn ? TEXT("on") : TEXT("off"));
	}
}

// ------------------------------------------------------------------------------------------------- ephemeris

void UNYCSkyTimeSubsystem::UpdateEphemeris()
{
	FString Error;
	bEphemerisValid = NYCAstro::ComputeSimTime(SimUnixSeconds, SimTime, Error);
	if (!bEphemerisValid)
	{
		if (ClockError != Error)
		{
			ClockError = Error;
			UE_LOG(LogNYCSim, Error, TEXT("Sky: %s"), *Error);
		}
		return;
	}
	ClockError.Empty();
	Sun = NYCAstro::SunAt(SimUnixSeconds, Observer);
	Moon = NYCAstro::MoonAt(SimUnixSeconds, Observer);

	// Rise/set and civil twilight only change once a day; recompute every 15 minutes of simulated time.
	TimeSinceSunEvents += 1.0 / FMath::Max(0.1f, CVarSkyHz.GetValueOnGameThread());
	if (TimeSinceSunEvents >= 900.0)
	{
		TimeSinceSunEvents = 0.0;
		FString EventError;
		if (!NYCAstro::SunEventsForInstant(SimUnixSeconds, Observer, NYCAstro::RiseSetAltitudeDeg(), RiseSet, EventError))
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Sky: sunrise/sunset unavailable: %s"), *EventError);
		}
		if (!NYCAstro::SunEventsForInstant(SimUnixSeconds, Observer, NYCAstro::CivilTwilightAltitudeDeg(), CivilEvents, EventError))
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Sky: civil twilight unavailable: %s"), *EventError);
		}
	}
}

bool UNYCSkyTimeSubsystem::SetSimTimeIso8601(const FString& Iso8601Utc)
{
	double Unix = 0.0;
	if (!NYCAstro::ParseIso8601Utc(Iso8601Utc, Unix))
	{
		return false;
	}
	SimUnixSeconds = Unix;
	bFollowRealTime = false;
	TimeSinceSunEvents = 1e9;
	UpdateEphemeris();
	ApplyToActors();
	UpdateStreetLighting();
	UpdateStarSphere();
	WriteMaterialParameterCollection();
	return true;
}

void UNYCSkyTimeSubsystem::SetFollowRealTime(bool bFollow)
{
	bFollowRealTime = bFollow;
	if (bFollow)
	{
		SimUnixSeconds = NYCAstro::NowUnixSeconds();
		TimeSinceSunEvents = 1e9;
		UpdateEphemeris();
		ApplyToActors();
	}
}

void UNYCSkyTimeSubsystem::SetTimeScale(float Scale)
{
	TimeScale = FMath::Clamp<double>(Scale, 0.0, 3600.0);
	if (TimeScale != 1.0)
	{
		bFollowRealTime = false;
	}
}

// ----------------------------------------------------------------------------------------------- sky actors

void UNYCSkyTimeSubsystem::EnsureSkyActors()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();

	// Reuse whatever the level already contains; only spawn what is missing (and only when allowed).
	for (TActorIterator<ADirectionalLight> It(World); It; ++It)
	{
		ADirectionalLight* Light = *It;
		if (!Light)
		{
			continue;
		}
		UDirectionalLightComponent* Component = Cast<UDirectionalLightComponent>(Light->GetLightComponent());
		if (!Component)
		{
			continue;
		}
		if (!SunLight && Component->AtmosphereSunLightIndex == 0)
		{
			SunLight = Light;
		}
		else if (!MoonLight && Component->AtmosphereSunLightIndex == 1)
		{
			MoonLight = Light;
		}
	}
	for (TActorIterator<ASkyAtmosphere> It(World); It && !SkyAtmosphere; ++It) { SkyAtmosphere = *It; }
	for (TActorIterator<AVolumetricCloud> It(World); It && !VolumetricCloud; ++It) { VolumetricCloud = *It; }
	for (TActorIterator<AExponentialHeightFog> It(World); It && !HeightFog; ++It) { HeightFog = *It; }
	for (TActorIterator<ASkyLight> It(World); It && !SkyLight; ++It) { SkyLight = *It; }

	if (!Settings.bSpawnSkyActors)
	{
		return;
	}

	FActorSpawnParameters Spawn;
	Spawn.ObjectFlags = RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

	if (!SunLight)
	{
		SunLight = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), FTransform::Identity, Spawn);
		if (SunLight)
		{
			if (UDirectionalLightComponent* C = Cast<UDirectionalLightComponent>(SunLight->GetLightComponent()))
			{
				C->SetMobility(EComponentMobility::Movable);
				C->bAtmosphereSunLight = true;
				C->AtmosphereSunLightIndex = 0;
				C->SetDynamicShadowCascades(4);
				C->SetShadowBias(0.6f);
				C->SetIntensity(Settings.SunIntensityLux);
				C->SetLightColor(FLinearColor::White);
				C->MarkRenderStateDirty();
			}
		}
	}
	if (!MoonLight)
	{
		MoonLight = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), FTransform::Identity, Spawn);
		if (MoonLight)
		{
			if (UDirectionalLightComponent* C = Cast<UDirectionalLightComponent>(MoonLight->GetLightComponent()))
			{
				C->SetMobility(EComponentMobility::Movable);
				C->bAtmosphereSunLight = true;
				C->AtmosphereSunLightIndex = 1;
				C->SetIntensity(Settings.MoonIntensityLux);
				// Moonlight is sunlight reflected off a grey body: neutral, very slightly blue after the eye adapts.
				C->SetLightColor(FLinearColor(0.78f, 0.85f, 1.f));
				C->SetDynamicShadowCascades(2);
				C->MarkRenderStateDirty();
			}
		}
	}
	if (!SkyAtmosphere)
	{
		SkyAtmosphere = World->SpawnActor<ASkyAtmosphere>(ASkyAtmosphere::StaticClass(), FTransform::Identity, Spawn);
	}
	if (!VolumetricCloud)
	{
		VolumetricCloud = World->SpawnActor<AVolumetricCloud>(AVolumetricCloud::StaticClass(), FTransform::Identity, Spawn);
	}
	if (!HeightFog)
	{
		HeightFog = World->SpawnActor<AExponentialHeightFog>(AExponentialHeightFog::StaticClass(), FTransform::Identity, Spawn);
		if (HeightFog)
		{
			if (UExponentialHeightFogComponent* C = HeightFog->GetComponent())
			{
				C->SetMobility(EComponentMobility::Movable);
				C->SetFogHeightFalloff(0.08f);   // NYC haze thins out over ~120 m
				C->SetVolumetricFog(true);
				C->SetStartDistance(150.f);      // 1.5 m: fog must not wash out the windscreen
			}
		}
	}
	if (!SkyLight)
	{
		SkyLight = World->SpawnActor<ASkyLight>(ASkyLight::StaticClass(), FTransform::Identity, Spawn);
		if (SkyLight)
		{
			if (USkyLightComponent* C = SkyLight->GetLightComponent())
			{
				C->SetMobility(EComponentMobility::Movable);
				C->SourceType = SLS_CapturedScene;
				C->bRealTimeCapture = true;
				C->bLowerHemisphereIsBlack = false;
				C->SetIntensity(1.f);
				C->MarkRenderStateDirty();
			}
		}
	}

	// Cloud material instance: the coverage parameter is driven from the observed cloud cover.
	if (VolumetricCloud)
	{
		if (UVolumetricCloudComponent* C = VolumetricCloud->GetComponent())
		{
			if (UMaterialInterface* Base = C->Material)
			{
				CloudMaterial = UMaterialInstanceDynamic::Create(Base, this);
				if (CloudMaterial)
				{
					C->SetMaterial(CloudMaterial);
				}
			}
			else
			{
				UE_LOG(LogNYCSim, Warning,
					TEXT("Sky: the volumetric cloud component has no material; cloud cover will only move the layer ")
					TEXT("altitude. Assign a cloud material (Engine's m_SimpleVolumetricCloud works) to drive coverage."));
			}
		}
	}

	// Star sphere: engine sphere mesh, inside-out via a two-sided unlit material, rotated by sidereal time.
	if (!StarSphere && !Settings.StarMapTexturePath.IsEmpty())
	{
		UStaticMesh* SphereMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		UMaterialInterface* StarBase = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/NYCSim/Materials/M_NYC_StarMap.M_NYC_StarMap"));
		if (SphereMesh && StarBase)
		{
			StarSphere = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform::Identity, Spawn);
			if (StarSphere)
			{
				UStaticMeshComponent* C = StarSphere->GetStaticMeshComponent();
				C->SetMobility(EComponentMobility::Movable);
				C->SetStaticMesh(SphereMesh);
				C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				C->SetCastShadow(false);
				C->bCastDynamicShadow = false;
				// The engine sphere has a 50 cm radius, so 200 000 x puts the star shell at 100 km — outside
				// everything the city can draw and still inside the atmosphere shell.
				C->SetWorldScale3D(FVector(200000.0));
				StarMaterial = UMaterialInstanceDynamic::Create(StarBase, this);
				if (StarMaterial)
				{
					C->SetMaterial(0, StarMaterial);
				}
			}
		}
		else
		{
			UE_LOG(LogNYCSim, Log,
				TEXT("Sky: no star sphere (mesh %s, material %s). The night sky falls back to the sky atmosphere's ")
				TEXT("own night luminance."),
				SphereMesh ? TEXT("ok") : TEXT("missing"), StarBase ? TEXT("ok") : TEXT("missing"));
		}
	}
}

void UNYCSkyTimeSubsystem::ApplyToActors()
{
	if (!bEphemerisValid)
	{
		return;
	}
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const float CloudAttenuation = FMath::Clamp(CVarCloudSunAttenuation.GetValueOnGameThread(), 0.f, 1.f);
	const float Cover = Atmosphere.bValid ? FMath::Clamp(Atmosphere.CloudCover, 0.f, 1.f) : 0.f;

	if (SunLight)
	{
		// The light's +X axis is the direction the light travels, i.e. from the sun toward the ground.
		const FVector Travel = -Sun.DirectionUE;
		SunLight->SetActorRotation(FRotationMatrix::MakeFromX(Travel).Rotator());
		if (UDirectionalLightComponent* C = Cast<UDirectionalLightComponent>(SunLight->GetLightComponent()))
		{
			const bool bVisible = Sun.ElevationDeg > -8.0;
			C->SetVisibility(bVisible);
			if (bVisible)
			{
				C->SetIntensity(Settings.SunIntensityLux * (1.f - CloudAttenuation * Cover));
			}
		}
	}
	if (MoonLight)
	{
		MoonLight->SetActorRotation(FRotationMatrix::MakeFromX(-Moon.DirectionUE).Rotator());
		if (UDirectionalLightComponent* C = Cast<UDirectionalLightComponent>(MoonLight->GetLightComponent()))
		{
			// The moon only lights the city once the sun is well down and it is itself above the horizon.
			const bool bVisible = Moon.ElevationDeg > -1.0 && Sun.ElevationDeg < -2.0;
			C->SetVisibility(bVisible);
			if (bVisible)
			{
				C->SetIntensity(Settings.MoonIntensityLux
					* static_cast<float>(FMath::Clamp(Moon.IlluminatedFraction, 0.0, 1.0))
					* (1.f - CloudAttenuation * Cover));
			}
		}
	}
	if (SkyLight)
	{
		if (USkyLightComponent* C = SkyLight->GetLightComponent())
		{
			// A real-time capture reacts to the atmosphere on its own; only the recapture cadence is ours.
			if (C->bRealTimeCapture == false)
			{
				C->RecaptureSky();
			}
		}
	}
}

void UNYCSkyTimeSubsystem::ApplyAtmosphere(const FNYCAtmosphereParams& Params)
{
	Atmosphere = Params;
	Atmosphere.bValid = true;

	if (VolumetricCloud)
	{
		if (UVolumetricCloudComponent* C = VolumetricCloud->GetComponent())
		{
			// The observed ceiling is the cloud layer's bottom; the layer thickness follows the cover (a 300 m thin
			// deck at few/scattered, up to 3 km at overcast) because no provider reports cloud-top height.
			const float BaseKm = Params.CloudBaseMetres > 50.f ? Params.CloudBaseMetres / 1000.f : 2.f;
			const float ThicknessKm = FMath::Lerp(0.3f, 3.0f, FMath::Clamp(Params.CloudCover, 0.f, 1.f));
			C->SetLayerBottomAltitude(BaseKm);
			C->SetLayerHeight(ThicknessKm);
			C->SetTracingMaxDistance(50.f);
		}
	}
	if (CloudMaterial)
	{
		CloudMaterial->SetScalarParameterValue(TEXT("CloudCoverage"), FMath::Clamp(Params.CloudCover, 0.f, 1.f));
		CloudMaterial->SetScalarParameterValue(TEXT("Coverage"), FMath::Clamp(Params.CloudCover, 0.f, 1.f));
		CloudMaterial->SetScalarParameterValue(TEXT("WindSpeed"), Params.WindSpeedMps);
		CloudMaterial->SetScalarParameterValue(TEXT("WindHeading"), Params.WindFromHeadingDeg);
	}
	if (HeightFog)
	{
		if (UExponentialHeightFogComponent* C = HeightFog->GetComponent())
		{
			C->SetFogDensity(FogDensityForVisibility(Params.VisibilityMetres));
			// Humid air scatters more at low level; the second fog layer carries the ground haze.
			C->SetSecondFogDensity(FogDensityForVisibility(Params.VisibilityMetres) * 0.5f
				* FMath::Clamp((Params.RelativeHumidityPercent - 70.f) / 30.f, 0.f, 1.f));
			C->SetSecondFogHeightOffset(0.f);
			C->SetSecondFogHeightFalloff(0.5f);
		}
	}
	ApplyToActors();
}

float UNYCSkyTimeSubsystem::FogDensityForVisibility(float VisibilityMetres)
{
	// Meteorological visibility V corresponds to an extinction coefficient sigma = 3.912 / V (Koschmieder, 2 % contrast
	// threshold). UE's FogDensity is not in 1/m, so one calibration constant ties the two together: UE's default
	// density 0.02 is a clear day, which the WMO defines as V >= 10 km, giving scale = 0.02 / (3.912 / 10000) = 51.1.
	constexpr float Scale = 51.1f;
	const float V = FMath::Max(30.f, VisibilityMetres);
	return FMath::Clamp(Scale * 3.912f / V, 0.002f, 3.f);
}

void UNYCSkyTimeSubsystem::UpdateStreetLighting()
{
	if (!bEphemerisValid)
	{
		return;
	}
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const double Threshold = Settings.StreetLightSunAltitudeDeg;
	const double Hysteresis = FMath::Max(0.0, Settings.StreetLightHysteresisDeg);
	const bool bWasOn = bStreetLightsOn;
	if (!bStreetLightsOn && Sun.ElevationDeg < Threshold - Hysteresis)
	{
		bStreetLightsOn = true;
	}
	else if (bStreetLightsOn && Sun.ElevationDeg > Threshold + Hysteresis)
	{
		bStreetLightsOn = false;
	}
	if (bWasOn != bStreetLightsOn)
	{
		UE_LOG(LogNYCSim, Log, TEXT("Sky: street lighting %s at %s %s (sun %.2f deg)"),
			bStreetLightsOn ? TEXT("ON") : TEXT("OFF"), *SimTime.Local.ToString(), *SimTime.TzAbbreviation, Sun.ElevationDeg);
		StreetLightingChanged.Broadcast(bStreetLightsOn);
	}
}

void UNYCSkyTimeSubsystem::UpdateStarSphere()
{
	if (!StarSphere || !bEphemerisValid)
	{
		return;
	}
	UStaticMeshComponent* C = StarSphere->GetStaticMeshComponent();
	if (!C)
	{
		return;
	}
	// Keep the sphere centred on the view so it never parallaxes.
	if (const UWorld* World = GetWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			FVector Location = FVector::ZeroVector;
			FRotator Rotation = FRotator::ZeroRotator;
			PC->GetPlayerViewPoint(Location, Rotation);
			C->SetWorldLocation(Location);
		}
	}
	// The celestial sphere's pole sits due north at an altitude equal to the observer's latitude; the sphere spins
	// about that axis once per sidereal day. StarMapRightAscensionOffsetDeg absorbs the texture's RA origin.
	const FVector PoleUE = NYCAstro::AzimuthElevationToUE(0.0, Observer.LatitudeDeg);
	const FQuat Align = FQuat::FindBetweenNormals(FVector::UpVector, PoleUE);
	const FQuat Spin(PoleUE, FMath::DegreesToRadians(-Sun.LocalSiderealTimeDeg));
	C->SetWorldRotation((Spin * Align).Rotator());
	if (StarMaterial)
	{
		// Stars fade out as the sky brightens; fully visible once the sun is below astronomical twilight.
		const float Visibility = static_cast<float>(FMath::Clamp((-Sun.ElevationDeg - 6.0) / 12.0, 0.0, 1.0));
		StarMaterial->SetScalarParameterValue(TEXT("StarVisibility"), Visibility);
		StarMaterial->SetScalarParameterValue(TEXT("MoonIllumination"), static_cast<float>(Moon.IlluminatedFraction));
	}
}

void UNYCSkyTimeSubsystem::WriteMaterialParameterCollection()
{
	if (!ParameterCollection || !bEphemerisValid)
	{
		return;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	UKismetMaterialLibrary::SetScalarParameterValue(World, ParameterCollection, TEXT("StreetLightsOn"), bStreetLightsOn ? 1.f : 0.f);
	UKismetMaterialLibrary::SetScalarParameterValue(World, ParameterCollection, TEXT("SunElevationDeg"), static_cast<float>(Sun.ElevationDeg));
	UKismetMaterialLibrary::SetScalarParameterValue(World, ParameterCollection, TEXT("SunAzimuthDeg"), static_cast<float>(Sun.AzimuthDeg));
	UKismetMaterialLibrary::SetScalarParameterValue(World, ParameterCollection, TEXT("MoonIllumination"), static_cast<float>(Moon.IlluminatedFraction));
	UKismetMaterialLibrary::SetScalarParameterValue(World, ParameterCollection, TEXT("LocalTimeHours"), static_cast<float>(SimTime.LocalHours));
	UKismetMaterialLibrary::SetVectorParameterValue(World, ParameterCollection, TEXT("SunDirection"),
		FLinearColor(static_cast<float>(Sun.DirectionUE.X), static_cast<float>(Sun.DirectionUE.Y), static_cast<float>(Sun.DirectionUE.Z), 0.f));
}

// -------------------------------------------------------------------------------------------------- console

void UNYCSkyTimeSubsystem::PrintSun(FOutputDevice& Ar) const
{
	Ar.Logf(TEXT("NYCSim sky (core %s)"), *NYCAstro::CoreVersion());
	if (!bEphemerisValid)
	{
		Ar.Logf(TEXT("  clock invalid: %s"), *ClockError);
		return;
	}
	Ar.Logf(TEXT("  clock     %s  UTC %s  local %s %s  %s  scale %.2fx"),
		bFollowRealTime ? TEXT("real time") : TEXT("fixed    "),
		*SimTime.Utc.ToString(), *SimTime.Local.ToString(), *SimTime.TzAbbreviation,
		SimTime.bIsDst ? TEXT("(DST)") : TEXT("(standard)"), TimeScale);
	Ar.Logf(TEXT("  observer  %.5f N, %.5f E, %.0f m   Delta-T %.2f s   JD %.6f"),
		Observer.LatitudeDeg, Observer.LongitudeDeg, Observer.ElevationMetres, SimTime.DeltaTSeconds, SimTime.JulianDay);
	Ar.Logf(TEXT("  sun       azimuth %8.3f deg   elevation %7.3f deg   distance %.6f AU   semidiameter %.4f deg"),
		Sun.AzimuthDeg, Sun.ElevationDeg, Sun.DistanceAu, Sun.SemidiameterDeg);
	Ar.Logf(TEXT("            local apparent sidereal time %.4f deg (%.4f h)"),
		Sun.LocalSiderealTimeDeg, Sun.LocalSiderealTimeDeg / 15.0);
	Ar.Logf(TEXT("            delta from the Manhattan grid (299.0 deg): %+.3f deg"),
		Sun.AzimuthDeg - NYCAstro::ManhattanStreetSunsetAzimuthDeg());
	Ar.Logf(TEXT("  moon      azimuth %8.3f deg   elevation %7.3f deg   %s, %.1f %% illuminated, %.0f km"),
		Moon.AzimuthDeg, Moon.ElevationDeg, *Moon.PhaseName, Moon.IlluminatedFraction * 100.0, Moon.DistanceKm);
	if (RiseSet.bHasSunrise || RiseSet.bHasSunset)
	{
		Ar.Logf(TEXT("  sunrise   %s   transit %s   sunset %s   (h0 %.4f deg)"),
			RiseSet.bHasSunrise ? *NYCAstro::FormatIso8601Utc(RiseSet.SunriseUnix) : TEXT("(none)"),
			*NYCAstro::FormatIso8601Utc(RiseSet.TransitUnix),
			RiseSet.bHasSunset ? *NYCAstro::FormatIso8601Utc(RiseSet.SunsetUnix) : TEXT("(none)"),
			RiseSet.H0Deg);
	}
	if (CivilEvents.bHasSunrise || CivilEvents.bHasSunset)
	{
		Ar.Logf(TEXT("  civil     dawn %s   dusk %s"),
			CivilEvents.bHasSunrise ? *NYCAstro::FormatIso8601Utc(CivilEvents.SunriseUnix) : TEXT("(none)"),
			CivilEvents.bHasSunset ? *NYCAstro::FormatIso8601Utc(CivilEvents.SunsetUnix) : TEXT("(none)"));
	}
	Ar.Logf(TEXT("  lights    street lighting %s (threshold %.2f deg)"),
		bStreetLightsOn ? TEXT("ON") : TEXT("off"), UNYCSimWorldSettings::Get().StreetLightSunAltitudeDeg);
	Ar.Logf(TEXT("  actors    sun %s  moon %s  atmosphere %s  clouds %s  fog %s  skylight %s  stars %s"),
		SunLight ? TEXT("y") : TEXT("n"), MoonLight ? TEXT("y") : TEXT("n"),
		SkyAtmosphere ? TEXT("y") : TEXT("n"), VolumetricCloud ? TEXT("y") : TEXT("n"),
		HeightFog ? TEXT("y") : TEXT("n"), SkyLight ? TEXT("y") : TEXT("n"), StarSphere ? TEXT("y") : TEXT("n"));
	if (Atmosphere.bValid)
	{
		Ar.Logf(TEXT("  weather   cloud %.0f %%  base %.0f m  visibility %.0f m  RH %.0f %%  wind %.1f m/s from %.0f deg"),
			Atmosphere.CloudCover * 100.f, Atmosphere.CloudBaseMetres, Atmosphere.VisibilityMetres,
			Atmosphere.RelativeHumidityPercent, Atmosphere.WindSpeedMps, Atmosphere.WindFromHeadingDeg);
	}
}
