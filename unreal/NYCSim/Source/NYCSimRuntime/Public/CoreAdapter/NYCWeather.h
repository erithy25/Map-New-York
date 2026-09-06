// Adapter over nycsim::weather: the ADR-011 provider chain (NWS -> Open-Meteo -> METAR -> stale), the METAR/NWS/
// Open-Meteo decoders and the ARCHITECTURE §11 weather -> world mapping. Nothing else in the runtime includes
// nycsim/weather/*.h.
//
// Fetching stays in Unreal (FHttpModule, asynchronous) while every decision stays in the core: the subsystem hands
// each raw provider document to SetProviderDocument() as it arrives, and Poll() then runs the core's
// WeatherService, whose per-provider fetch callbacks decode the cached document synchronously. A provider with no
// fresh document fails its callback, which is exactly the failure the core's circuit breaker expects.
#pragma once

#include "CoreMinimal.h"

#include "NYCWeather.generated.h"

/** Which upstream a document came from (mirrors nycsim::weather::Source, plus the NWS gridpoint document). */
UENUM(BlueprintType)
enum class ENYCWeatherProvider : uint8
{
	Nws = 0,
	OpenMeteo,
	Metar,
	NwsGridpoint
};

UENUM(BlueprintType)
enum class ENYCPrecipType : uint8
{
	None = 0,
	Rain,
	Snow,
	Sleet,
	FreezingRain,
	Drizzle
};

/** DATA_CONTRACTS §12 weather.json + §12.1 extension. NaN in the core becomes bHas* = false here. */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCWeatherState
{
	GENERATED_BODY()

	/** "nws" | "open_meteo" | "metar" | "stale". */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Source = TEXT("stale");

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Station;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double ObservedAtUnix = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double FetchedAtUnix = 0.0;

	/** Seconds since the observation was taken (the number the debug overlay shows). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double StaleAgeSeconds = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bValid = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float TemperatureC = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float DewpointC = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float RelativeHumidityPercent = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float WindMps = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float WindGustMps = 0.f;

	/** Compass heading the wind blows FROM (the core's wind_from_heading). */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float WindFromHeadingDeg = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	ENYCPrecipType PrecipType = ENYCPrecipType::None;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float PrecipRateMmph = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float CloudCover = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float VisibilityMetres = 16093.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float PressureHpa = 1013.25f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float SnowDepthCm = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bThunder = false;

	/** Ceiling (lowest BKN/OVC/VV base) from the most recent METAR; 0 when no METAR reported one. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float CloudBaseMetres = 0.f;

	/** "BR FG" style obscuration list from the core. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Obscuration;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bInterpolated = false;

	/** Raw METAR text when the winning source is METAR. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString RawText;

	// per-field presence: the core distinguishes "unknown" (NaN) from zero and so must the world
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHasTemperature = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHasWind = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHasCloudCover = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHasVisibility = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHasPrecipRate = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHasSnowDepth = false;
};

/** ARCHITECTURE §11 weather -> world mapping (nycsim::weather::WorldEffects). */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCWorldEffects
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float Wetness = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float Puddles = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float SnowCover = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float SnowDepthMetres = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float IceRisk = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float FogDensity = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float WindSpeedMps = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float WindGustMps = 0.f;

	/** Compass heading the air moves TOWARDS. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float WindHeadingDeg = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float FlagSway = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float UmbrellaShare = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float PedestrianDensityScale = 1.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float PlowActivity = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float Overcast = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float RainRateMmph = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	float SnowRateCmph = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bHeadlights = false;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bWipers = false;

	/** 0 off, 1 intermittent, 2 low, 3 high. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	int32 WiperSpeed = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bThunder = false;

	/** nycsim::vehicle::SurfaceClass index; the name is in SurfaceName. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	uint8 SurfaceClass = 0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString SurfaceName = TEXT("dry_asphalt");
};

/** Status of one provider's circuit breaker, for the overlay. */
struct FNYCProviderStatus
{
	FString Name;
	/** "closed" | "half_open" | "open(NNNs)". */
	FString Status;
	/** Age of the cached document in seconds; negative when nothing has been received. */
	double DocumentAgeSeconds = -1.0;
	FString LastError;
	int32 HttpStatus = 0;
};

namespace nycsim { namespace weather { class WeatherService; struct WorldEffectsState; } }

/**
 * Owns the core WeatherService and the document cache. Not thread-safe: every call happens on the game thread
 * (the HTTP completion delegates run there too).
 */
class NYCSIMRUNTIME_API FNYCWeatherService
{
public:
	explicit FNYCWeatherService(double PollIntervalSeconds = 60.0);
	~FNYCWeatherService();

	FNYCWeatherService(const FNYCWeatherService&) = delete;
	FNYCWeatherService& operator=(const FNYCWeatherService&) = delete;

	/** URL for a provider, built from the core's own constants so the decoder always sees the query it expects. */
	static FString ProviderUrl(ENYCWeatherProvider Provider, const FString& Station, double LatitudeDeg, double LongitudeDeg);
	/** tgftp METAR URL for one station. */
	static FString MetarUrl(const FString& Station);

	/** Stores a document that has just arrived (or records the failure when bSuccess is false). */
	void SetProviderDocument(ENYCWeatherProvider Provider, const FString& Body, double ReceivedUnix, bool bSuccess,
		int32 HttpStatus, const FString& Error);

	/** Adds one station's raw METAR text; the freshest station wins at poll time. */
	void SetMetarDocument(const FString& Station, const FString& Text, double ReceivedUnix, bool bSuccess,
		int32 HttpStatus, const FString& Error);

	/** Runs one core poll and returns the state the world should use. Never fails. */
	const FNYCWeatherState& Poll(double NowUnix);

	const FNYCWeatherState& Current() const { return Current; }

	/** Advances the memory of the wetness/puddle model and returns the world effects. */
	FNYCWorldEffects StepWorldEffects(double DeltaSeconds);

	/** Seeds the last-known-good state from a §12 weather.json document (offline start). */
	bool RestoreFromJson(const FString& JsonText, FString& OutError);
	/** Serialises the current state as a §12 weather.json document. */
	FString ToJson() const;

	TArray<FNYCProviderStatus> ProviderStatus(double NowUnix) const;

	uint64 PollCount() const;
	uint64 FailureCount() const;

	/** Documents older than this are not offered to the core (they would defeat the staleness rules). */
	static constexpr double MaxDocumentAgeSeconds = 300.0;

private:
	struct FDocument
	{
		FString Body;
		double ReceivedUnix = -1.0;
		bool bValid = false;
		int32 HttpStatus = 0;
		FString Error;
	};

	FDocument& DocumentFor(ENYCWeatherProvider Provider);
	const FDocument& DocumentFor(ENYCWeatherProvider Provider) const;

	TUniquePtr<nycsim::weather::WeatherService> Service;
	TUniquePtr<nycsim::weather::WorldEffectsState> EffectsState;
	FDocument NwsDoc;
	FDocument OpenMeteoDoc;
	FDocument MetarDoc;
	FDocument GridpointDoc;
	FString MetarStation;
	/** Ceiling from the most recent decoded METAR, metres; < 0 when unknown. */
	double CeilingMetres = -1.0;
	FNYCWeatherState Current;
};
