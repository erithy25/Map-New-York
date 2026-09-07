// Project settings owned by the gameplay lane (vehicle, character, traffic, pedestrians, GPS, audio).
//
// Kept separate from UNYCSimWorldSettings (world/streaming/sky/weather) so the two Unreal agents never edit the
// same class. Config section: [/Script/NYCSimRuntime.NYCGameplaySettings] in Config/DefaultGame.ini.
//
// Every asset reference is a soft path resolved at runtime; nothing here hard-links content, so the module still
// links and runs before the import commandlet has produced any of it (the subsystems log exactly which path
// failed to resolve and fall back to a working default).
#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "NYCGameplaySettings.generated.h"

UCLASS(Config = Game, DefaultConfig, meta = (DisplayName = "NYCSim Gameplay"))
class NYCSIMRUNTIME_API UNYCGameplaySettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UNYCGameplaySettings();

	static const UNYCGameplaySettings& Get();

	virtual FName GetCategoryName() const override { return FName(TEXT("Project")); }

	// ---- weather coupling ----------------------------------------------------------------------------------
	/** Material parameter collection the weather subsystem drives (same asset as UNYCSimWorldSettings names). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FSoftObjectPath WeatherParameterCollection =
		FSoftObjectPath(TEXT("/Game/NYCSim/Materials/MPC_Weather.MPC_Weather"));

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherWetnessParameter = TEXT("Wetness");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherSnowParameter = TEXT("SnowCover");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherIceParameter = TEXT("IceCover");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherWaterDepthParameter = TEXT("WaterDepthMm");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherRainRateParameter = TEXT("RainRateMmH");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherWindSpeedParameter = TEXT("WindSpeedMps");

	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherTemperatureParameter = TEXT("TemperatureC");

	/** Scalar parameter the sky subsystem sets to 1 when headlights are due (civil twilight or heavy rain). */
	UPROPERTY(Config, EditAnywhere, Category = "Weather")
	FName WeatherNightParameter = TEXT("NightFactor");

	// ---- vehicle -------------------------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "Vehicle")
	FSoftObjectPath PlayerVehicleMesh =
		FSoftObjectPath(TEXT("/Game/NYCSim/Vehicles/Player/SK_FusionHybrid.SK_FusionHybrid"));

	/** Registration plate rendered onto the PLATE_FACE slot. NY plates are three letters, four digits. */
	UPROPERTY(Config, EditAnywhere, Category = "Vehicle")
	FString PlayerPlateNumber = TEXT("KDT 4419");

	UPROPERTY(Config, EditAnywhere, Category = "Vehicle")
	FLinearColor PlayerPaintColor = FLinearColor(0.045f, 0.055f, 0.070f, 1.f);

	/** Mirror scene-capture resolution per mirror (square). 0 disables the mirrors. */
	UPROPERTY(Config, EditAnywhere, Category = "Vehicle", meta = (ClampMin = "0", ClampMax = "1024"))
	int32 MirrorResolution = 256;

	/** Distance in metres beyond which mirror captures stop updating (they are the most expensive feature). */
	UPROPERTY(Config, EditAnywhere, Category = "Vehicle", meta = (ClampMin = "0.0"))
	float MirrorMaxRangeMetres = 120.f;

	/** Centre-console screen render-target size. */
	UPROPERTY(Config, EditAnywhere, Category = "Vehicle", meta = (ClampMin = "64", ClampMax = "2048"))
	int32 CentreScreenResolution = 512;

	// ---- traffic and pedestrians ---------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "Traffic", meta = (ClampMin = "0", ClampMax = "4000"))
	int32 MaxTrafficVehicles = 900;

	UPROPERTY(Config, EditAnywhere, Category = "Traffic", meta = (ClampMin = "0", ClampMax = "6000"))
	int32 MaxPedestrians = 1400;

	UPROPERTY(Config, EditAnywhere, Category = "Traffic", meta = (ClampMin = "0.1", ClampMax = "4.0"))
	float TrafficDensityScale = 1.f;

	UPROPERTY(Config, EditAnywhere, Category = "Traffic", meta = (ClampMin = "0.1", ClampMax = "4.0"))
	float PedestrianDensityScale = 1.f;

	/** Content path holding one skeletal mesh per ADR-009 fleet body, named SK_<body id>. */
	UPROPERTY(Config, EditAnywhere, Category = "Traffic")
	FString TrafficVehicleMeshRoot = TEXT("/Game/NYCSim/Vehicles/Fleet");

	UPROPERTY(Config, EditAnywhere, Category = "Traffic")
	FString PedestrianMeshRoot = TEXT("/Game/NYCSim/Characters/Crowd");

	/** Distance (metres) at which a traffic actor drops to its low-detail proxy. */
	UPROPERTY(Config, EditAnywhere, Category = "Traffic", meta = (ClampMin = "10.0"))
	float TrafficLodDistanceMetres = 120.f;

	UPROPERTY(Config, EditAnywhere, Category = "Traffic", meta = (ClampMin = "10.0"))
	float PedestrianLodDistanceMetres = 45.f;

	// ---- character -----------------------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "Character")
	FSoftObjectPath PlayerCharacterMesh =
		FSoftObjectPath(TEXT("/Game/NYCSim/Characters/Player/SK_Player.SK_Player"));

	/** Directory containing the animation set named by FNYCCharacterAnims (AS_<clip>). */
	UPROPERTY(Config, EditAnywhere, Category = "Character")
	FString CharacterAnimationRoot = TEXT("/Game/NYCSim/Characters/Player/Anims");

	// ---- UI ------------------------------------------------------------------------------------------------
	UPROPERTY(Config, EditAnywhere, Category = "UI")
	FSoftObjectPath HudFont = FSoftObjectPath(TEXT("/Game/NYCSim/Fonts/F_Overpass.F_Overpass"));

	UPROPERTY(Config, EditAnywhere, Category = "UI", meta = (ClampMin = "60.0"))
	float MinimapDefaultRangeMetres = 220.f;

	// ---- audio ---------------------------------------------------------------------------------------------
	/** Directory the radio station sound waves were imported into (mirrors assets/audio/radio/<station>/). */
	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FString RadioContentRoot = TEXT("/Game/NYCSim/Audio/Radio");

	/** Path (relative to the project directory unless absolute) of the fetcher's stations.json. */
	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FString RadioStationsJson = TEXT("Content/NYCSim/Audio/stations.json");

	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FString SfxContentRoot = TEXT("/Game/NYCSim/Audio/SFX");

	/** MetaSound sources used when they exist; the C++ synthesisers cover the same parameters when they do not. */
	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FSoftObjectPath EngineMetaSound =
		FSoftObjectPath(TEXT("/Game/NYCSim/Audio/MS_Engine.MS_Engine"));

	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FSoftObjectPath TyreMetaSound = FSoftObjectPath(TEXT("/Game/NYCSim/Audio/MS_Tyres.MS_Tyres"));

	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FSoftObjectPath WindMetaSound = FSoftObjectPath(TEXT("/Game/NYCSim/Audio/MS_Wind.MS_Wind"));

	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FSoftObjectPath RainMetaSound = FSoftObjectPath(TEXT("/Game/NYCSim/Audio/MS_Rain.MS_Rain"));

	UPROPERTY(Config, EditAnywhere, Category = "Audio")
	FSoftObjectPath WiperMetaSound = FSoftObjectPath(TEXT("/Game/NYCSim/Audio/MS_Wipers.MS_Wipers"));

	UPROPERTY(Config, EditAnywhere, Category = "Audio", meta = (ClampMin = "0.0", ClampMax = "2.0"))
	float MasterVolume = 1.f;

	UPROPERTY(Config, EditAnywhere, Category = "Audio", meta = (ClampMin = "0.0", ClampMax = "2.0"))
	float RadioVolume = 0.55f;

	UPROPERTY(Config, EditAnywhere, Category = "Audio", meta = (ClampMin = "0", ClampMax = "64"))
	int32 MaxAmbienceEmitters = 24;

	// ---- input ---------------------------------------------------------------------------------------------
	/** Enhanced Input assets created by the editor import commandlet. Missing assets fall back to the equivalent
	 *  transient contexts built in C++ by FNYCInputConfig, so the game is playable without any content. */
	UPROPERTY(Config, EditAnywhere, Category = "Input")
	FSoftObjectPath DrivingMappingContext =
		FSoftObjectPath(TEXT("/Game/NYCSim/Input/IMC_Driving.IMC_Driving"));

	UPROPERTY(Config, EditAnywhere, Category = "Input")
	FSoftObjectPath OnFootMappingContext =
		FSoftObjectPath(TEXT("/Game/NYCSim/Input/IMC_OnFoot.IMC_OnFoot"));

	UPROPERTY(Config, EditAnywhere, Category = "Input")
	FSoftObjectPath CommonMappingContext =
		FSoftObjectPath(TEXT("/Game/NYCSim/Input/IMC_Common.IMC_Common"));

	/** Resolves a project-relative path the same way UNYCSimWorldSettings does. */
	static FString ResolvePath(const FString& InPath);
};
