#include "Weather/NYCWeatherSubsystem.h"

#include "CoreAdapter/NYCAstro.h"
#include "CoreAdapter/NYCGeo.h"
#include "NYCSimRuntime.h"
#include "Sky/NYCSkyTimeSubsystem.h"
#include "World/NYCSimWorldSettings.h"
#include "World/NYCWaterActor.h"

#include "Debug/DebugDrawService.h"
#include "Dom/JsonObject.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	TAutoConsoleVariable<int32> CVarWeatherOverlay(
		TEXT("nycsim.Overlay"), 0,
		TEXT("0 off, 1 the weather overlay (provider, observation age, staleness, world effects), 2 adds the ")
		TEXT("per-provider circuit-breaker state and the raw METAR."),
		ECVF_Cheat);

	TAutoConsoleVariable<int32> CVarWeatherFx(
		TEXT("nycsim.Weather.FX"), 1,
		TEXT("0 disables the rain/snow/steam/splash Niagara systems (the material drives stay live)."),
		ECVF_Default);

	UNYCWeatherSubsystem* WeatherFor(UWorld* World)
	{
		return World ? World->GetSubsystem<UNYCWeatherSubsystem>() : nullptr;
	}

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GPrintWeatherCmd(
		TEXT("nycsim.PrintWeather"),
		TEXT("Prints the current observation, its provider and age, the provider circuit breakers and the world effects."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCWeatherSubsystem* Weather = WeatherFor(World))
				{
					Weather->PrintWeather(Ar);
				}
				else
				{
					Ar.Logf(TEXT("nycsim: no weather subsystem in this world"));
				}
			}));

	FAutoConsoleCommandWithWorldArgsAndOutputDevice GPollWeatherCmd(
		TEXT("nycsim.Weather.Poll"),
		TEXT("Fetches every provider immediately instead of waiting for the 60 s cadence."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(
			[](const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
			{
				if (UNYCWeatherSubsystem* Weather = WeatherFor(World))
				{
					Weather->RequestPollNow();
					Ar.Logf(TEXT("nycsim: weather poll requested"));
				}
			}));

	/** Niagara user-parameter names (the contract the four systems must expose; see unreal/README.md). */
	const FName ParamRateMmph(TEXT("RateMmph"));
	const FName ParamRateCmph(TEXT("RateCmph"));
	const FName ParamWindVelocity(TEXT("WindVelocity"));
	const FName ParamIntensity(TEXT("Intensity"));
	const FName ParamWetness(TEXT("Wetness"));
	const FName ParamTemperatureC(TEXT("TemperatureC"));

	const TCHAR* PrecipName(ENYCPrecipType T)
	{
		switch (T)
		{
		case ENYCPrecipType::Rain: return TEXT("rain");
		case ENYCPrecipType::Snow: return TEXT("snow");
		case ENYCPrecipType::Sleet: return TEXT("sleet");
		case ENYCPrecipType::FreezingRain: return TEXT("freezing_rain");
		case ENYCPrecipType::Drizzle: return TEXT("drizzle");
		default: return TEXT("none");
		}
	}
}

bool UNYCWeatherSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	if (!Super::ShouldCreateSubsystem(Outer))
	{
		return false;
	}
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

void UNYCWeatherSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UNYCSkyTimeSubsystem>();
	Super::Initialize(Collection);

	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	Service = MakeUnique<FNYCWeatherService>(FMath::Max(10.f, Settings.WeatherPollSeconds));

	Settings.MetarStations.ParseIntoArray(MetarStations, TEXT(","), true);
	for (FString& Station : MetarStations)
	{
		Station.TrimStartAndEndInline();
		Station.ToUpperInline();
	}
	if (MetarStations.Num() == 0)
	{
		MetarStations.Add(TEXT("KLGA"));
	}

	if (!Settings.WeatherMaterialParameterCollection.IsEmpty())
	{
		ParameterCollection = LoadObject<UMaterialParameterCollection>(nullptr, *Settings.WeatherMaterialParameterCollection);
	}

	// Seed from the snapshot services/nycsim_live wrote, so the very first frame already has real weather.
	const FString SeedPath = UNYCSimWorldSettings::ResolveProjectPath(Settings.WeatherJsonPath);
	FString SeedText;
	if (FFileHelper::LoadFileToString(SeedText, *SeedPath))
	{
		FString Error;
		if (Service->RestoreFromJson(SeedText, Error))
		{
			Weather = Service->Current();
			UE_LOG(LogNYCSim, Log, TEXT("Weather: seeded from %s (source %s, station %s, observed %s)"),
				*SeedPath, *Weather.Source, *Weather.Station, *NYCAstro::FormatIso8601Utc(Weather.ObservedAtUnix));
		}
		else
		{
			UE_LOG(LogNYCSim, Warning, TEXT("Weather: %s could not be read as weather.json: %s"), *SeedPath, *Error);
		}
	}
	else
	{
		UE_LOG(LogNYCSim, Log, TEXT("Weather: no seed snapshot at %s; the first live poll provides the first observation."), *SeedPath);
	}
}

void UNYCWeatherSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	for (TActorIterator<ANYCWaterActor> It(&InWorld); It; ++It)
	{
		WaterActor = *It;
		break;
	}
	EnsureFxActor();

	if (!IsRunningCommandlet() && InWorld.GetNetMode() != NM_DedicatedServer)
	{
		OverlayHandle = UDebugDrawService::Register(
			TEXT("Game"), FDebugDrawDelegate::CreateUObject(this, &UNYCWeatherSubsystem::DrawOverlay));
	}
	RequestPollNow();
}

void UNYCWeatherSubsystem::Deinitialize()
{
	if (OverlayHandle.IsValid())
	{
		UDebugDrawService::Unregister(OverlayHandle);
		OverlayHandle.Reset();
	}
	WeatherUpdated.Clear();
	WorldEffectsUpdated.Clear();
	Service.Reset();
	Super::Deinitialize();
}

bool UNYCWeatherSubsystem::IsTickable() const
{
	return IsInitialized() && Service.IsValid();
}

TStatId UNYCWeatherSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UNYCWeatherSubsystem, STATGROUP_Tickables);
}

void UNYCWeatherSubsystem::RequestPollNow()
{
	TimeSinceFetch = 1e9;
	TimeSinceEsb = 1e9;
	TimeSinceTide = 1e9;
}

void UNYCWeatherSubsystem::Tick(float DeltaTime)
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const double NowUnix = NYCAstro::NowUnixSeconds();

	TimeSinceFetch += DeltaTime;
	TimeSinceEsb += DeltaTime;
	TimeSinceTide += DeltaTime;

	if (TimeSinceFetch >= FMath::Max(10.f, Settings.WeatherPollSeconds))
	{
		TimeSinceFetch = 0.0;
		StartFetches(NowUnix);
		PollCore(NowUnix);
	}
	if (TimeSinceEsb >= FMath::Max(60.f, Settings.EsbPollSeconds))
	{
		TimeSinceEsb = 0.0;
		ReadEsbLights(NowUnix);
	}
	if (TimeSinceTide >= FMath::Max(60.f, Settings.TidePollSeconds))
	{
		TimeSinceTide = 0.0;
		ReadTides(NowUnix);
		PushTideToWater();
	}

	ApplyEffects(DeltaTime);
}

// ------------------------------------------------------------------------------------------------------ http

void UNYCWeatherSubsystem::StartFetches(double NowUnix)
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	if (!Settings.bUseLiveWeather)
	{
		return;
	}
	StartRequest(ENYCWeatherProvider::Nws,
		FNYCWeatherService::ProviderUrl(ENYCWeatherProvider::Nws, Settings.NwsStationId, Settings.OpenMeteoLatitude, Settings.OpenMeteoLongitude),
		Settings.NwsStationId);
	StartRequest(ENYCWeatherProvider::NwsGridpoint,
		FNYCWeatherService::ProviderUrl(ENYCWeatherProvider::NwsGridpoint, Settings.NwsStationId, Settings.OpenMeteoLatitude, Settings.OpenMeteoLongitude),
		Settings.NwsStationId);
	StartRequest(ENYCWeatherProvider::OpenMeteo,
		FNYCWeatherService::ProviderUrl(ENYCWeatherProvider::OpenMeteo, FString(), Settings.OpenMeteoLatitude, Settings.OpenMeteoLongitude),
		FString());
	for (const FString& Station : MetarStations)
	{
		StartRequest(ENYCWeatherProvider::Metar, FNYCWeatherService::MetarUrl(Station), Station);
	}
}

void UNYCWeatherSubsystem::StartRequest(ENYCWeatherProvider Provider, const FString& Url, const FString& Station)
{
	if (Url.IsEmpty())
	{
		return;
	}
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(Url);
	Request->SetVerb(TEXT("GET"));
	Request->SetTimeout(FMath::Clamp(Settings.HttpTimeoutSeconds, 1.f, 60.f));
	// api.weather.gov requires an identifying User-Agent; the others accept it.
	Request->SetHeader(TEXT("User-Agent"), Settings.HttpUserAgent);
	Request->SetHeader(TEXT("Accept"), Provider == ENYCWeatherProvider::Metar
		? TEXT("text/plain") : TEXT("application/geo+json, application/json;q=0.9, */*;q=0.5"));
	Request->OnProcessRequestComplete().BindUObject(this, &UNYCWeatherSubsystem::OnHttpComplete, Provider, Station);
	++InFlightRequests;
	++TotalRequests;
	if (!Request->ProcessRequest())
	{
		--InFlightRequests;
		++TotalRequestFailures;
		UE_LOG(LogNYCSim, Warning, TEXT("Weather: could not start the request for %s"), *Url);
	}
}

void UNYCWeatherSubsystem::OnHttpComplete(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bConnectedSuccessfully,
	ENYCWeatherProvider Provider, FString Station)
{
	InFlightRequests = FMath::Max(0, InFlightRequests - 1);
	if (!Service.IsValid())
	{
		return;
	}
	const double NowUnix = NYCAstro::NowUnixSeconds();
	const int32 Code = Response.IsValid() ? Response->GetResponseCode() : 0;
	const bool bOk = bConnectedSuccessfully && Response.IsValid() && EHttpResponseCodes::IsOk(Code);
	const FString Body = bOk ? Response->GetContentAsString() : FString();
	FString Error;
	if (!bOk)
	{
		++TotalRequestFailures;
		Error = !bConnectedSuccessfully ? TEXT("connection failed")
			: !Response.IsValid() ? TEXT("no response")
			: FString::Printf(TEXT("HTTP %d"), Code);
		UE_LOG(LogNYCSim, Verbose, TEXT("Weather: %s fetch failed (%s)"),
			Provider == ENYCWeatherProvider::Metar ? *Station : TEXT("provider"), *Error);
	}
	if (Provider == ENYCWeatherProvider::Metar)
	{
		Service->SetMetarDocument(Station, Body, NowUnix, bOk, Code, Error);
	}
	else
	{
		Service->SetProviderDocument(Provider, Body, NowUnix, bOk, Code, Error);
	}
	// Poll as soon as the documents of this round have arrived, so the world is never a cadence behind.
	if (InFlightRequests == 0)
	{
		PollCore(NowUnix);
	}
}

void UNYCWeatherSubsystem::PollCore(double NowUnix)
{
	if (!Service.IsValid())
	{
		return;
	}
	Weather = Service->Poll(NowUnix);
	LastPollUnix = NowUnix;
	WeatherUpdated.Broadcast(Weather);
	PushAtmosphereToSky();
}

// --------------------------------------------------------------------------------------------------- effects

void UNYCWeatherSubsystem::ApplyEffects(float DeltaSeconds)
{
	if (!Service.IsValid())
	{
		return;
	}
	Effects = Service->StepWorldEffects(DeltaSeconds);
	WriteMaterialParameterCollection();
	UpdateNiagara();
	WorldEffectsUpdated.Broadcast(Effects);
}

void UNYCWeatherSubsystem::WriteMaterialParameterCollection()
{
	UWorld* World = GetWorld();
	if (!ParameterCollection || !World)
	{
		return;
	}
	auto Scalar = [this, World](const TCHAR* Name, float Value)
	{
		UKismetMaterialLibrary::SetScalarParameterValue(World, ParameterCollection, FName(Name), Value);
	};
	Scalar(TEXT("Wetness"), Effects.Wetness);
	Scalar(TEXT("Puddles"), Effects.Puddles);
	Scalar(TEXT("SnowCover"), Effects.SnowCover);
	Scalar(TEXT("SnowDepthM"), Effects.SnowDepthMetres);
	Scalar(TEXT("IceRisk"), Effects.IceRisk);
	Scalar(TEXT("FogDensity"), Effects.FogDensity);
	Scalar(TEXT("WindSpeedMps"), Effects.WindSpeedMps);
	Scalar(TEXT("WindGustMps"), Effects.WindGustMps);
	Scalar(TEXT("WindHeadingDeg"), Effects.WindHeadingDeg);
	Scalar(TEXT("FlagSway"), Effects.FlagSway);
	Scalar(TEXT("Overcast"), Effects.Overcast);
	Scalar(TEXT("RainRateMmph"), Effects.RainRateMmph);
	Scalar(TEXT("SnowRateCmph"), Effects.SnowRateCmph);
	Scalar(TEXT("TemperatureC"), Weather.TemperatureC);
	Scalar(TEXT("Thunder"), Effects.bThunder ? 1.f : 0.f);
	Scalar(TEXT("Stale"), IsStale() ? 1.f : 0.f);

	const double WindToRad = FMath::DegreesToRadians(90.0 - Effects.WindHeadingDeg); // compass -> mathematical
	const FVector WindUE = NYCGeo::DirectionToUE(FVector(FMath::Cos(WindToRad), FMath::Sin(WindToRad), 0.0));
	UKismetMaterialLibrary::SetVectorParameterValue(World, ParameterCollection, FName(TEXT("WindVector")),
		FLinearColor(static_cast<float>(WindUE.X), static_cast<float>(WindUE.Y), 0.f, Effects.WindSpeedMps));

	const FLinearColor Crown = (Esb.bValid && Esb.Colors.Num() > 0) ? Esb.Colors[0] : FLinearColor::White;
	UKismetMaterialLibrary::SetVectorParameterValue(World, ParameterCollection, FName(TEXT("ESBCrownColor")), Crown);
	const FLinearColor Crown2 = (Esb.bValid && Esb.Colors.Num() > 1) ? Esb.Colors[1] : Crown;
	UKismetMaterialLibrary::SetVectorParameterValue(World, ParameterCollection, FName(TEXT("ESBCrownColor2")), Crown2);
	const FLinearColor Crown3 = (Esb.bValid && Esb.Colors.Num() > 2) ? Esb.Colors[2] : Crown2;
	UKismetMaterialLibrary::SetVectorParameterValue(World, ParameterCollection, FName(TEXT("ESBCrownColor3")), Crown3);
	Scalar(TEXT("ESBColorCount"), static_cast<float>(Esb.Colors.Num()));
}

void UNYCWeatherSubsystem::EnsureFxActor()
{
	UWorld* World = GetWorld();
	if (!World || FxActor)
	{
		return;
	}
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();

	FActorSpawnParameters Spawn;
	Spawn.ObjectFlags = RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	FxActor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Spawn);
	if (!FxActor)
	{
		return;
	}
	USceneComponent* Root = NewObject<USceneComponent>(FxActor, TEXT("WeatherFxRoot"));
	Root->SetMobility(EComponentMobility::Movable);
	FxActor->SetRootComponent(Root);
	Root->RegisterComponent();

	auto MakeComponent = [this, Root](const FSoftObjectPath& Path, const TCHAR* Name) -> UNiagaraComponent*
	{
		UNiagaraSystem* System = Cast<UNiagaraSystem>(Path.TryLoad());
		if (!System)
		{
			if (!bMissingFxLogged)
			{
				bMissingFxLogged = true;
				UE_LOG(LogNYCSim, Warning,
					TEXT("Weather: Niagara system %s is missing. Precipitation particles are off; every material, ")
					TEXT("fog, wind and physics drive still follows the live observation. See unreal/README.md ")
					TEXT("'Niagara systems' for the four assets and the user parameters they must expose."),
					*Path.ToString());
			}
			return nullptr;
		}
		UNiagaraComponent* Component = NewObject<UNiagaraComponent>(FxActor, Name);
		Component->SetAsset(System);
		Component->SetAutoActivate(false);
		Component->SetupAttachment(Root);
		Component->RegisterComponent();
		return Component;
	};

	RainComponent = MakeComponent(Settings.RainNiagaraSystem, TEXT("Rain"));
	SnowComponent = MakeComponent(Settings.SnowNiagaraSystem, TEXT("Snow"));
	SteamComponent = MakeComponent(Settings.SteamNiagaraSystem, TEXT("Steam"));
	SplashComponent = MakeComponent(Settings.SplashNiagaraSystem, TEXT("Splash"));
}

void UNYCWeatherSubsystem::UpdateNiagara()
{
	UWorld* World = GetWorld();
	if (!World || !FxActor)
	{
		return;
	}
	// The precipitation volume follows the view: the systems emit inside a box around the camera.
	if (const APlayerController* PC = World->GetFirstPlayerController())
	{
		FVector Location = FVector::ZeroVector;
		FRotator Rotation = FRotator::ZeroRotator;
		PC->GetPlayerViewPoint(Location, Rotation);
		FxActor->SetActorLocation(Location);
	}

	const bool bFxEnabled = CVarWeatherFx.GetValueOnGameThread() != 0;
	const double WindToRad = FMath::DegreesToRadians(90.0 - Effects.WindHeadingDeg);
	const FVector WindUE = NYCGeo::DirectionToUE(FVector(FMath::Cos(WindToRad), FMath::Sin(WindToRad), 0.0))
		* (Effects.WindSpeedMps * 100.0);

	auto Drive = [&](UNiagaraComponent* Component, bool bWanted, float Rate, const FName& RateParam)
	{
		if (!Component)
		{
			return;
		}
		const bool bActive = bWanted && bFxEnabled;
		if (bActive)
		{
			Component->SetVariableFloat(RateParam, Rate);
			Component->SetVariableFloat(ParamIntensity, FMath::Clamp(Rate / 10.f, 0.f, 1.f));
			Component->SetVariableVec3(ParamWindVelocity, WindUE);
			Component->SetVariableFloat(ParamWetness, Effects.Wetness);
			Component->SetVariableFloat(ParamTemperatureC, Weather.TemperatureC);
			if (!Component->IsActive())
			{
				Component->Activate();
			}
		}
		else if (Component->IsActive())
		{
			Component->Deactivate();
		}
	};

	const bool bRaining = Effects.RainRateMmph > 0.01f;
	const bool bSnowing = Effects.SnowRateCmph > 0.01f;
	Drive(RainComponent, bRaining, Effects.RainRateMmph, ParamRateMmph);
	Drive(SnowComponent, bSnowing, Effects.SnowRateCmph, ParamRateCmph);
	Drive(SplashComponent, bRaining && Effects.Wetness > 0.2f, Effects.RainRateMmph, ParamRateMmph);
	// Steam from the manholes and the district steam system: visible whenever the air is cold enough for the plume to
	// condense (Con Edison's steam loop runs all year; the plume is a temperature effect, not a weather event).
	Drive(SteamComponent, Weather.bHasTemperature && Weather.TemperatureC < 12.f,
		FMath::Clamp((12.f - Weather.TemperatureC) / 20.f, 0.f, 1.f), ParamIntensity);
}

void UNYCWeatherSubsystem::PushAtmosphereToSky()
{
	UWorld* World = GetWorld();
	UNYCSkyTimeSubsystem* Sky = World ? World->GetSubsystem<UNYCSkyTimeSubsystem>() : nullptr;
	if (!Sky)
	{
		return;
	}
	FNYCAtmosphereParams Params;
	Params.bValid = true;
	Params.CloudCover = Weather.bHasCloudCover ? Weather.CloudCover : 0.f;
	Params.CloudBaseMetres = Weather.CloudBaseMetres;
	Params.VisibilityMetres = Weather.bHasVisibility ? Weather.VisibilityMetres : 16093.f;
	Params.RelativeHumidityPercent = Weather.RelativeHumidityPercent;
	Params.TemperatureC = Weather.TemperatureC;
	Params.WindSpeedMps = Effects.WindSpeedMps;
	Params.WindFromHeadingDeg = Weather.WindFromHeadingDeg;
	Sky->ApplyAtmosphere(Params);
}

// -------------------------------------------------------------------------------------------- esb and tides

void UNYCWeatherSubsystem::ReadEsbLights(double NowUnix)
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString Path = UNYCSimWorldSettings::ResolveProjectPath(Settings.EsbLightsJsonPath);
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		if (!Esb.bValid)
		{
			// No file: the crown shows the building's signature white, which is what it actually does on a night
			// with no scheduled lighting.
			Esb.ColorNames = {TEXT("White")};
			Esb.Colors = {FLinearColor::White};
			Esb.Reason = TEXT("no esb_lights.json; signature white");
			Esb.bFallback = true;
			Esb.bValid = true;
		}
		return;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Weather: %s is not valid JSON"), *Path);
		return;
	}
	FNYCEsbLighting New;
	Root->TryGetStringField(TEXT("date"), New.Date);
	Root->TryGetStringField(TEXT("reason"), New.Reason);
	Root->TryGetStringField(TEXT("source_url"), New.SourceUrl);
	Root->TryGetBoolField(TEXT("fallback"), New.bFallback);
	const TArray<TSharedPtr<FJsonValue>>* Names = nullptr;
	if (Root->TryGetArrayField(TEXT("colors"), Names) && Names)
	{
		for (const TSharedPtr<FJsonValue>& V : *Names)
		{
			FString Name;
			if (V.IsValid() && V->TryGetString(Name))
			{
				New.ColorNames.Add(Name);
			}
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* Rgb = nullptr;
	if (Root->TryGetArrayField(TEXT("rgb"), Rgb) && Rgb)
	{
		for (const TSharedPtr<FJsonValue>& V : *Rgb)
		{
			const TArray<TSharedPtr<FJsonValue>>* Triple = nullptr;
			if (!V.IsValid() || !V->TryGetArray(Triple) || !Triple || Triple->Num() < 3)
			{
				continue;
			}
			const double R = (*Triple)[0]->AsNumber();
			const double G = (*Triple)[1]->AsNumber();
			const double B = (*Triple)[2]->AsNumber();
			// The published values are 8-bit sRGB; the crown is an emissive light, so linearise before use.
			New.Colors.Add(FLinearColor(FColor(
				static_cast<uint8>(FMath::Clamp(R, 0.0, 255.0)),
				static_cast<uint8>(FMath::Clamp(G, 0.0, 255.0)),
				static_cast<uint8>(FMath::Clamp(B, 0.0, 255.0)))));
		}
	}
	if (New.Colors.Num() == 0)
	{
		New.Colors.Add(FLinearColor::White);
		if (New.ColorNames.Num() == 0)
		{
			New.ColorNames.Add(TEXT("White"));
		}
	}
	New.bValid = true;
	const bool bChanged = New.Date != Esb.Date || New.ColorNames != Esb.ColorNames;
	Esb = MoveTemp(New);
	if (bChanged)
	{
		UE_LOG(LogNYCSim, Log, TEXT("Weather: ESB crown %s for %s (%s)%s"),
			*FString::Join(Esb.ColorNames, TEXT(" / ")), *Esb.Date, *Esb.Reason,
			Esb.bFallback ? TEXT(" [fallback]") : TEXT(""));
	}
}

void UNYCWeatherSubsystem::ReadTides(double NowUnix)
{
	const UNYCSimWorldSettings& Settings = UNYCSimWorldSettings::Get();
	const FString Path = UNYCSimWorldSettings::ResolveProjectPath(Settings.TidesJsonPath);
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		return;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		UE_LOG(LogNYCSim, Warning, TEXT("Weather: %s is not valid JSON"), *Path);
		return;
	}
	FNYCTideState New;
	Root->TryGetStringField(TEXT("station"), New.Station);
	Root->TryGetNumberField(TEXT("water_level_m"), New.WaterLevelMetres);
	Root->TryGetNumberField(TEXT("current_speed_mps"), New.CurrentSpeedMps);
	Root->TryGetNumberField(TEXT("current_dir_deg"), New.CurrentDirDeg);
	Root->TryGetStringField(TEXT("current_phase"), New.Phase);
	FString ObservedAt;
	if (Root->TryGetStringField(TEXT("predicted_at"), ObservedAt))
	{
		NYCAstro::ParseIso8601Utc(ObservedAt, New.ObservedAtUnix);
	}
	New.bValid = true;
	Tide = MoveTemp(New);
}

void UNYCWeatherSubsystem::PushTideToWater()
{
	if (!Tide.bValid)
	{
		return;
	}
	if (!WaterActor)
	{
		if (UWorld* World = GetWorld())
		{
			for (TActorIterator<ANYCWaterActor> It(World); It; ++It)
			{
				WaterActor = *It;
				break;
			}
		}
	}
	if (WaterActor)
	{
		// tides.json carries the observed water level when CO-OPS answered and the harmonic prediction otherwise;
		// an empty phase means no current observation was available for this poll.
		WaterActor->SetTide(Tide.WaterLevelMetres, Tide.CurrentSpeedMps, Tide.CurrentDirDeg, Tide.Phase.IsEmpty());
	}
}

float UNYCWeatherSubsystem::GetObservationAgeSeconds() const
{
	if (Weather.ObservedAtUnix <= 0.0)
	{
		return -1.f;
	}
	return static_cast<float>(NYCAstro::NowUnixSeconds() - Weather.ObservedAtUnix);
}

// --------------------------------------------------------------------------------------------------- overlay

void UNYCWeatherSubsystem::DrawOverlay(UCanvas* Canvas, APlayerController* PC)
{
	const int32 Mode = CVarWeatherOverlay.GetValueOnGameThread();
	if (Mode <= 0 || !Canvas)
	{
		return;
	}
	UFont* Font = GEngine ? GEngine->GetSmallFont() : nullptr;
	if (!Font)
	{
		return;
	}
	const float X = Canvas->SizeX * 0.62f;
	float Y = 90.f;
	const float LineHeight = 15.f;
	auto Line = [&](const FLinearColor& Colour, const FString& Text)
	{
		Canvas->SetDrawColor(Colour.ToFColor(true));
		Canvas->DrawText(Font, Text, X, Y);
		Y += LineHeight;
	};

	const FLinearColor White(1.f, 1.f, 1.f, 1.f);
	const FLinearColor Amber(1.f, 0.75f, 0.2f, 1.f);
	const FLinearColor Red(1.f, 0.35f, 0.3f, 1.f);
	const float Age = GetObservationAgeSeconds();
	const bool bStale = IsStale();

	Line(bStale ? Red : White, FString::Printf(TEXT("NYCSim weather   source %s   station %s%s"),
		*Weather.Source.ToUpper(), Weather.Station.IsEmpty() ? TEXT("(none)") : *Weather.Station,
		bStale ? TEXT("   [STALE: no provider answered]") : TEXT("")));
	Line(Age > 3600.f ? Red : (Age > 900.f ? Amber : White),
		FString::Printf(TEXT("observed %s   age %s"),
			Weather.ObservedAtUnix > 0.0 ? *NYCAstro::FormatIso8601Utc(Weather.ObservedAtUnix) : TEXT("(never)"),
			Age < 0.f ? TEXT("n/a") : *FString::Printf(TEXT("%.0f s"), Age)));
	Line(White, FString::Printf(TEXT("%.1f C  dew %.1f C  RH %.0f %%  %.0f hPa  vis %.0f m  cloud %.0f %%%s"),
		Weather.TemperatureC, Weather.DewpointC, Weather.RelativeHumidityPercent, Weather.PressureHpa,
		Weather.VisibilityMetres, Weather.CloudCover * 100.f,
		Weather.CloudBaseMetres > 0.f ? *FString::Printf(TEXT(" base %.0f m"), Weather.CloudBaseMetres) : TEXT("")));
	Line(White, FString::Printf(TEXT("wind %.1f m/s from %.0f deg  gust %.1f m/s%s%s"),
		Weather.WindMps, Weather.WindFromHeadingDeg, Weather.WindGustMps,
		Weather.bThunder ? TEXT("  THUNDER") : TEXT(""),
		Weather.Obscuration.IsEmpty() ? TEXT("") : *FString::Printf(TEXT("  %s"), *Weather.Obscuration)));
	Line(White, FString::Printf(TEXT("precip %s %.2f mm/h   snow depth %.1f cm"),
		PrecipName(Weather.PrecipType), Weather.PrecipRateMmph, Weather.SnowDepthCm));
	Line(White, FString::Printf(TEXT("world: wet %.2f  puddle %.2f  snow %.2f (%.2f m)  fog %.2f  ice %.2f"),
		Effects.Wetness, Effects.Puddles, Effects.SnowCover, Effects.SnowDepthMetres, Effects.FogDensity, Effects.IceRisk));
	Line(White, FString::Printf(TEXT("       surface %s  wipers %d  headlights %d  umbrellas %.0f %%  plows %.2f"),
		*Effects.SurfaceName, Effects.WiperSpeed, Effects.bHeadlights ? 1 : 0,
		Effects.UmbrellaShare * 100.f, Effects.PlowActivity));
	if (Esb.bValid)
	{
		Line(White, FString::Printf(TEXT("ESB crown %s%s"), *FString::Join(Esb.ColorNames, TEXT(" / ")),
			Esb.bFallback ? TEXT(" [fallback]") : TEXT("")));
	}
	if (Tide.bValid)
	{
		Line(White, FString::Printf(TEXT("tide %s  %.2f m  current %.2f m/s toward %.0f deg %s"),
			*Tide.Station, Tide.WaterLevelMetres, Tide.CurrentSpeedMps, Tide.CurrentDirDeg, *Tide.Phase));
	}

	if (Mode < 2 || !Service.IsValid())
	{
		return;
	}
	Line(White, TEXT("providers (circuit breaker / document age):"));
	for (const FNYCProviderStatus& Status : Service->ProviderStatus(NYCAstro::NowUnixSeconds()))
	{
		const bool bBroken = !Status.Status.StartsWith(TEXT("closed"));
		Line(bBroken ? Amber : White, FString::Printf(TEXT("  %-11s %-12s doc %s%s%s"),
			*Status.Name, *Status.Status,
			Status.DocumentAgeSeconds < 0.0 ? TEXT("none") : *FString::Printf(TEXT("%.0f s"), Status.DocumentAgeSeconds),
			Status.HttpStatus > 0 ? *FString::Printf(TEXT("  HTTP %d"), Status.HttpStatus) : TEXT(""),
			Status.LastError.IsEmpty() ? TEXT("") : *FString::Printf(TEXT("  %s"), *Status.LastError)));
	}
	if (!Weather.RawText.IsEmpty())
	{
		Line(White, FString::Printf(TEXT("  %s"), *Weather.RawText.Left(110)));
	}
}

void UNYCWeatherSubsystem::PrintWeather(FOutputDevice& Ar) const
{
	Ar.Logf(TEXT("NYCSim weather: source %s  station %s  observed %s  age %.0f s  valid %d"),
		*Weather.Source, *Weather.Station,
		Weather.ObservedAtUnix > 0.0 ? *NYCAstro::FormatIso8601Utc(Weather.ObservedAtUnix) : TEXT("(never)"),
		GetObservationAgeSeconds(), Weather.bValid ? 1 : 0);
	Ar.Logf(TEXT("  %.1f C / dew %.1f C / RH %.0f %%   wind %.1f m/s from %.0f deg gust %.1f   %.0f hPa"),
		Weather.TemperatureC, Weather.DewpointC, Weather.RelativeHumidityPercent,
		Weather.WindMps, Weather.WindFromHeadingDeg, Weather.WindGustMps, Weather.PressureHpa);
	Ar.Logf(TEXT("  cloud %.0f %% base %.0f m   visibility %.0f m   precip %.2f mm/h   snow %.1f cm   thunder %d"),
		Weather.CloudCover * 100.f, Weather.CloudBaseMetres, Weather.VisibilityMetres,
		Weather.PrecipRateMmph, Weather.SnowDepthCm, Weather.bThunder ? 1 : 0);
	Ar.Logf(TEXT("  world effects: wetness %.2f  puddles %.2f  snow cover %.2f  fog %.2f  surface %s  wipers %d"),
		Effects.Wetness, Effects.Puddles, Effects.SnowCover, Effects.FogDensity, *Effects.SurfaceName, Effects.WiperSpeed);
	Ar.Logf(TEXT("  http: %d requests, %d failures, %d in flight"), TotalRequests, TotalRequestFailures, InFlightRequests);
	if (Service.IsValid())
	{
		Ar.Logf(TEXT("  core: %llu polls, %llu provider failures"), Service->PollCount(), Service->FailureCount());
		for (const FNYCProviderStatus& Status : Service->ProviderStatus(NYCAstro::NowUnixSeconds()))
		{
			Ar.Logf(TEXT("    %-11s %-12s document %s  %s"), *Status.Name, *Status.Status,
				Status.DocumentAgeSeconds < 0.0 ? TEXT("none") : *FString::Printf(TEXT("%.0f s old"), Status.DocumentAgeSeconds),
				*Status.LastError);
		}
	}
	if (Esb.bValid)
	{
		Ar.Logf(TEXT("  ESB crown: %s (%s)%s"), *FString::Join(Esb.ColorNames, TEXT(" / ")), *Esb.Reason,
			Esb.bFallback ? TEXT(" [fallback]") : TEXT(""));
	}
	if (Tide.bValid)
	{
		Ar.Logf(TEXT("  tide %s: %.2f m, current %.2f m/s toward %.0f deg (%s)"),
			*Tide.Station, Tide.WaterLevelMetres, Tide.CurrentSpeedMps, Tide.CurrentDirDeg, *Tide.Phase);
	}
}
