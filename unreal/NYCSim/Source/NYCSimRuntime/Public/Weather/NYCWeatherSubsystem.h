// Live weather: FHttpModule fetchers on a 60 s cadence feeding the core's WeatherService (ADR-011 chain
// NWS -> Open-Meteo -> METAR -> stale), the ARCHITECTURE §11 weather -> world mapping applied to MPC_Weather and to
// the rain / snow / steam / splash Niagara systems, the Empire State Building crown colour from esb_lights.json, the
// NOAA CO-OPS tide handed to ANYCWaterActor, and the debug overlay (console: nycsim.Overlay).
//
// Everything the world shows is measured or derived from measurements by a documented formula in the core. When no
// provider answers, the last good observation is re-shown with source "stale" and its age — the overlay says so.
#pragma once

#include "CoreMinimal.h"
#include "CoreAdapter/NYCWeather.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/ObjectPtr.h"

#include "Interfaces/IHttpRequest.h"

#include "NYCWeatherSubsystem.generated.h"

class ANYCWaterActor;
class APlayerController;
class UCanvas;
class UMaterialParameterCollection;
class UNiagaraComponent;
class UNiagaraSystem;
class UNYCSkyTimeSubsystem;

/** Empire State Building crown for the current local date (services/nycsim_live/esb_lights.py output). */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCEsbLighting
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Date;

	/** Canonical colour names as the ESB publishes them. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	TArray<FString> ColorNames;

	/** One entry per colour name, in the published order. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	TArray<FLinearColor> Colors;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Reason;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString SourceUrl;

	/** True when the scrape failed and the building's signature white is being shown. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bFallback = true;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bValid = false;
};

/** NOAA CO-OPS tide/current snapshot (DATA_CONTRACTS §12 tides.json). */
USTRUCT(BlueprintType)
struct NYCSIMRUNTIME_API FNYCTideState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Station;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double WaterLevelMetres = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double CurrentSpeedMps = 0.0;

	/** Mathematical angle (0 = east, CCW) the water flows toward. */
	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double CurrentDirDeg = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	FString Phase;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	double ObservedAtUnix = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "NYCSim|Weather")
	bool bValid = false;
};

DECLARE_MULTICAST_DELEGATE_OneParam(FNYCOnWeatherUpdated, const FNYCWeatherState& /*State*/);
DECLARE_MULTICAST_DELEGATE_OneParam(FNYCOnWorldEffectsUpdated, const FNYCWorldEffects& /*Effects*/);

UCLASS()
class NYCSIMRUNTIME_API UNYCWeatherSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickable() const override;
	virtual TStatId GetStatId() const override;

	UFUNCTION(BlueprintPure, Category = "NYCSim|Weather")
	FNYCWeatherState GetWeather() const { return Weather; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Weather")
	FNYCWorldEffects GetWorldEffects() const { return Effects; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Weather")
	FNYCEsbLighting GetEsbLighting() const { return Esb; }

	UFUNCTION(BlueprintPure, Category = "NYCSim|Weather")
	FNYCTideState GetTide() const { return Tide; }

	/** Seconds since the winning observation was taken. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Weather")
	float GetObservationAgeSeconds() const;

	/** True when the current record is a re-emitted last-known-good one. */
	UFUNCTION(BlueprintPure, Category = "NYCSim|Weather")
	bool IsStale() const { return Weather.Source == TEXT("stale"); }

	/** Forces a poll now (console, tests, and the first frame). */
	UFUNCTION(BlueprintCallable, Category = "NYCSim|Weather")
	void RequestPollNow();

	FNYCOnWeatherUpdated& OnWeatherUpdated() { return WeatherUpdated; }
	FNYCOnWorldEffectsUpdated& OnWorldEffectsUpdated() { return WorldEffectsUpdated; }

	void PrintWeather(FOutputDevice& Ar) const;

private:
	void StartFetches(double NowUnix);
	void StartRequest(ENYCWeatherProvider Provider, const FString& Url, const FString& Station);
	void OnHttpComplete(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bConnectedSuccessfully,
		ENYCWeatherProvider Provider, FString Station);
	void PollCore(double NowUnix);
	void ApplyEffects(float DeltaSeconds);
	void WriteMaterialParameterCollection();
	void UpdateNiagara();
	void EnsureFxActor();
	void ReadEsbLights(double NowUnix);
	void ReadTides(double NowUnix);
	void PushTideToWater();
	void PushAtmosphereToSky();
	void DrawOverlay(UCanvas* Canvas, APlayerController* PC);

	TUniquePtr<FNYCWeatherService> Service;

	FNYCWeatherState Weather;
	FNYCWorldEffects Effects;
	FNYCEsbLighting Esb;
	FNYCTideState Tide;

	double TimeSinceFetch = 1e9;
	double TimeSinceEsb = 1e9;
	double TimeSinceTide = 1e9;
	double LastPollUnix = 0.0;
	int32 InFlightRequests = 0;
	int32 TotalRequests = 0;
	int32 TotalRequestFailures = 0;
	TArray<FString> MetarStations;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> ParameterCollection;

	UPROPERTY(Transient)
	TObjectPtr<AActor> FxActor;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> RainComponent;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> SnowComponent;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> SteamComponent;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> SplashComponent;

	UPROPERTY(Transient)
	TObjectPtr<ANYCWaterActor> WaterActor;

	FNYCOnWeatherUpdated WeatherUpdated;
	FNYCOnWorldEffectsUpdated WorldEffectsUpdated;
	FDelegateHandle OverlayHandle;
	bool bMissingFxLogged = false;
};
