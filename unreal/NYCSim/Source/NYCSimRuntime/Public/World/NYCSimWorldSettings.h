// Project-wide settings for the NYCSim world: data paths, streaming radii, sky/time and weather endpoints.
// Config section: [/Script/NYCSimRuntime.NYCSimWorldSettings] in Config/DefaultEngine.ini (defaultconfig).
#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "NYCSimWorldSettings.generated.h"

UCLASS(Config = Engine, DefaultConfig, meta = (DisplayName = "NYCSim World"))
class NYCSIMRUNTIME_API UNYCSimWorldSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UNYCSimWorldSettings();

	static const UNYCSimWorldSettings& Get();

	/** Resolve a settings path: absolute paths are returned unchanged, relative paths are relative to the project dir. */
	static FString ResolveProjectPath(const FString& InPath);

	// ---- data ---------------------------------------------------------------------------------------------------
	/** Directory holding the pipeline's runtime/*.nycb files, live/*.json snapshots and crs.json. */
	UPROPERTY(Config, EditAnywhere, Category = "Data")
	FString RuntimeDataDir = TEXT("Content/NYCSim/Runtime");

	UPROPERTY(Config, EditAnywhere, Category = "Data")
	FString CrsJsonPath = TEXT("Content/NYCSim/Runtime/crs.json");

	UPROPERTY(Config, EditAnywhere, Category = "Data")
	FString TilesNycbPath = TEXT("Content/NYCSim/Runtime/tiles.nycb");

	/** Root content path of the per-tile streaming levels: {Root}/{tile}/L0, {Root}/{tile}/L1. */
	UPROPERTY(Config, EditAnywhere, Category = "Data")
	FString TileLevelRoot = TEXT("/Game/NYCSim/Tiles");

	/** Root content path of the always-loaded L2/L3 skyline levels partitioned by 16 km: {Root}/S_{sx}_{sy}. */
	UPROPERTY(Config, EditAnywhere, Category = "Data")
	FString SkylineLevelRoot = TEXT("/Game/NYCSim/Skyline");

	// ---- streaming ----------------------------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "100.0"))
	float LoadRadiusL0Metres = 900.f;

	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "100.0"))
	float UnloadRadiusL0Metres = 1300.f;

	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "500.0"))
	float LoadRadiusL1Metres = 2500.f;

	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "500.0"))
	float UnloadRadiusL1Metres = 3000.f;

	/** Seconds of camera motion the scheduler looks ahead (ARCHITECTURE §3: 1.5 s at 30 m/s pre-loads 45 m ahead). */
	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "0.0", ClampMax = "10.0"))
	float PredictiveLookaheadSeconds = 1.5f;

	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "512"))
	int32 GpuBudgetMegabytes = 6144;

	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "512"))
	int32 CpuBudgetMegabytes = 8192;

	/** Maximum level load requests issued per frame (keeps hitching bounded). */
	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "1", ClampMax = "64"))
	int32 MaxLoadRequestsPerFrame = 4;

	UPROPERTY(Config, EditAnywhere, Category = "Streaming", meta = (ClampMin = "1", ClampMax = "64"))
	int32 MaxUnloadRequestsPerFrame = 4;

	// ---- sky / time ---------------------------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	FString TimeZoneIanaName = TEXT("America/New_York");

	/** True: the simulation clock follows the real system clock. False: FixedUtcTimeIso8601 + TimeScale. */
	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	bool bUseRealTime = true;

	/** ISO-8601 UTC instant used when bUseRealTime is false, e.g. 2026-07-12T00:20:00Z (Manhattanhenge sunset). */
	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	FString FixedUtcTimeIso8601;

	UPROPERTY(Config, EditAnywhere, Category = "Sky", meta = (ClampMin = "0.0", ClampMax = "3600.0"))
	float TimeScale = 1.f;

	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	FString StarMapTexturePath = TEXT("/Game/NYCSim/Sky/T_StarMap");

	// ---- weather ------------------------------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "Weather", meta = (ClampMin = "10.0"))
	float WeatherPollSeconds = 60.f;

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString WeatherMaterialParameterCollection = TEXT("/Game/NYCSim/Materials/MPC_Weather.MPC_Weather");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString EsbLightsUrl = TEXT("https://www.esbnyc.com/about/tower-lights/calendar");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString NwsStationId = TEXT("KNYC");

	/** NWS forecast office/grid, e.g. OKX/33,37 (Central Park). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString NwsGridpoint = TEXT("OKX/33,37");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString MetarStations = TEXT("KLGA,KJFK,KEWR");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	double OpenMeteoLatitude = 40.7794;

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	double OpenMeteoLongitude = -73.9692;

	/** NOAA CO-OPS water-level station (8518750 = The Battery). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString NoaaTideStationId = TEXT("8518750");

	/** NOAA CO-OPS current station (NYH1927 = Hell Gate / East River). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString NoaaCurrentStationId = TEXT("NYH1927");

	// ---- water --------------------------------------------------------------------------------------------------
	/** §14.1 unreal_water.json: bodies, per-tile coverage and the tide snapshot ANYCWaterActor starts from. */
	UPROPERTY(Config, EditAnywhere, Category = "Water")
	FString UnrealWaterJsonPath = TEXT("Content/NYCSim/Runtime/unreal_water.json");

	/** Directory of the per-tile 8-bit shoreline masks ({tile}.png, 501 x 501, 1 texel = 2 m). */
	UPROPERTY(Config, EditAnywhere, Category = "Water")
	FString WaterMaskDir = TEXT("Content/NYCSim/Runtime/water_masks");

	UPROPERTY(Config, EditAnywhere, Category = "Water")
	FSoftObjectPath WaterMaterialPath = FSoftObjectPath(TEXT("/Game/NYCSim/Materials/M_NYC_Water.M_NYC_Water"));

	/** Tiles around the camera that get their own masked water patch. 3 -> a 7 x 7 km block. */
	UPROPERTY(Config, EditAnywhere, Category = "Water", meta = (ClampMin = "0", ClampMax = "12"))
	int32 WaterNearRadiusTiles = 3;

	UPROPERTY(Config, EditAnywhere, Category = "Water", meta = (ClampMin = "4", ClampMax = "256"))
	int32 WaterPatchQuads = 64;

	/** Half-extent of the far water ring: 40 km keeps the Atlantic and the Hudson under the horizon from any viewpoint. */
	UPROPERTY(Config, EditAnywhere, Category = "Water", meta = (ClampMin = "4.0", ClampMax = "120.0"))
	float WaterFarExtentKilometres = 40.f;

	UPROPERTY(Config, EditAnywhere, Category = "Water", meta = (ClampMin = "4", ClampMax = "512"))
	int32 WaterFarQuads = 96;

	UPROPERTY(Config, EditAnywhere, Category = "Water")
	bool bSpawnWaterActor = true;

	// ---- sky (continued) ----------------------------------------------------------------------------------------
	/** Observer used for the sun/moon ephemeris: Belvedere Castle, Central Park (the NWS KNYC station). A single
	 *  observer is correct to well under a pixel across a 50 km city (the sun's parallax over 50 km is ~0.0004 deg). */
	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	double ObserverLatitudeDeg = 40.7794;

	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	double ObserverLongitudeDeg = -73.9692;

	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	double ObserverAltitudeMetres = 35.0;

	/** Sun altitude at which the street lighting switches on/off (civil dusk = -6 deg). */
	UPROPERTY(Config, EditAnywhere, Category = "Sky", meta = (ClampMin = "-18.0", ClampMax = "10.0"))
	double StreetLightSunAltitudeDeg = -6.0;

	/** Hysteresis around StreetLightSunAltitudeDeg so the lights do not flicker at the threshold. */
	UPROPERTY(Config, EditAnywhere, Category = "Sky", meta = (ClampMin = "0.0", ClampMax = "3.0"))
	double StreetLightHysteresisDeg = 0.35;

	UPROPERTY(Config, EditAnywhere, Category = "Sky")
	bool bSpawnSkyActors = true;

	/** Clear-sky illuminance of the sun disc at the zenith, lux (UE's physical light unit). */
	UPROPERTY(Config, EditAnywhere, Category = "Sky", meta = (ClampMin = "1000.0"))
	float SunIntensityLux = 120000.f;

	/** Full-moon illuminance, lux (0.25 lx is the measured full-moon value; UE renders it with the moon light). */
	UPROPERTY(Config, EditAnywhere, Category = "Sky", meta = (ClampMin = "0.0"))
	float MoonIntensityLux = 0.25f;

	// ---- weather (continued) ------------------------------------------------------------------------------------
	/** Snapshots written by services/nycsim_live (used as the seed before the first live poll answers). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString WeatherJsonPath = TEXT("Content/NYCSim/Live/weather.json");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString EsbLightsJsonPath = TEXT("Content/NYCSim/Live/esb_lights.json");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString TidesJsonPath = TEXT("Content/NYCSim/Live/tides.json");

	/** False: never touch the network; the JSON snapshots above are the only source. */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	bool bUseLiveWeather = true;

	/** api.weather.gov requires a contact in the User-Agent (its terms of service). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FString HttpUserAgent = TEXT("NYCSim/1.0 (https://github.com/nycsim; contact via repository)");

	UPROPERTY(Config, EditAnywhere, Category = "Weather", meta = (ClampMin = "1.0", ClampMax = "60.0"))
	float HttpTimeoutSeconds = 12.f;

	/** Observations older than this are treated as a provider failure (services/nycsim_live/weather.py). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather", meta = (ClampMin = "60.0"))
	float MaxObservationAgeSeconds = 9000.f;

	UPROPERTY(Config, EditAnywhere, Category = "Weather", meta = (ClampMin = "60.0"))
	float TidePollSeconds = 600.f;

	UPROPERTY(Config, EditAnywhere, Category = "Weather", meta = (ClampMin = "300.0"))
	float EsbPollSeconds = 3600.f;

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FSoftObjectPath RainNiagaraSystem = FSoftObjectPath(TEXT("/Game/NYCSim/FX/NS_Rain.NS_Rain"));

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FSoftObjectPath SnowNiagaraSystem = FSoftObjectPath(TEXT("/Game/NYCSim/FX/NS_Snow.NS_Snow"));

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FSoftObjectPath SteamNiagaraSystem = FSoftObjectPath(TEXT("/Game/NYCSim/FX/NS_Steam.NS_Steam"));

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FSoftObjectPath SplashNiagaraSystem = FSoftObjectPath(TEXT("/Game/NYCSim/FX/NS_RainSplash.NS_RainSplash"));

	// ---- game ---------------------------------------------------------------------------------------------------
	/** Class path of the player pawn (agent 2's vehicle pawn). Falls back to a fly-camera pawn if unresolvable. */
	UPROPERTY(Config, EditAnywhere, Category = "Game")
	FSoftClassPath DefaultPawnClassPath = FSoftClassPath(TEXT("/Script/NYCSimRuntime.NYCPlayerVehiclePawn"));

	/** Spawn location in NYC_TM metres (east, north, up) used when the map has no PlayerStart. Default: Times Square. */
	UPROPERTY(Config, EditAnywhere, Category = "Game")
	FVector DefaultSpawnNycTm = FVector(-4180.0, 1720.0, 14.0);

	UPROPERTY(Config, EditAnywhere, Category = "Game")
	float DefaultSpawnHeadingDeg = 30.f;

	virtual FName GetCategoryName() const override { return FName(TEXT("Project")); }
};
