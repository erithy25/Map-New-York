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
