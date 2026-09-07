#include "CoreAdapter/NYCWeather.h"

#include "NYCSimRuntime.h"

#include <string>
#include <vector>

#include "nycsim/io/Json.h"
#include "nycsim/util/Error.h"
#include "nycsim/util/Result.h"
#include "nycsim/vehicle/Friction.h"
#include "nycsim/weather/MetarParser.h"
#include "nycsim/weather/NwsParser.h"
#include "nycsim/weather/OpenMeteoParser.h"
#include "nycsim/weather/WeatherService.h"
#include "nycsim/weather/WeatherState.h"
#include "nycsim/weather/WorldEffects.h"

namespace
{
	using nycsim::weather::WeatherState;

	FString ToFString(const std::string& S) { return FString(UTF8_TO_TCHAR(S.c_str())); }
	FString ToFString(const char* S) { return FString(UTF8_TO_TCHAR(S ? S : "")); }

	float SafeFloat(double V, float Fallback = 0.f)
	{
		return WeatherState::has(V) ? static_cast<float>(V) : Fallback;
	}

	ENYCPrecipType ToUE(nycsim::weather::PrecipType T)
	{
		switch (T)
		{
		case nycsim::weather::PrecipType::Rain: return ENYCPrecipType::Rain;
		case nycsim::weather::PrecipType::Snow: return ENYCPrecipType::Snow;
		case nycsim::weather::PrecipType::Sleet: return ENYCPrecipType::Sleet;
		case nycsim::weather::PrecipType::FreezingRain: return ENYCPrecipType::FreezingRain;
		case nycsim::weather::PrecipType::Drizzle: return ENYCPrecipType::Drizzle;
		default: return ENYCPrecipType::None;
		}
	}

	void Convert(const WeatherState& S, double CeilingMetres, FNYCWeatherState& Out)
	{
		Out.Source = ToFString(nycsim::weather::sourceName(S.source));
		Out.Station = ToFString(S.station);
		Out.ObservedAtUnix = WeatherState::has(S.observedAtUnix) ? S.observedAtUnix : 0.0;
		Out.FetchedAtUnix = WeatherState::has(S.fetchedAtUnix) ? S.fetchedAtUnix : 0.0;
		Out.StaleAgeSeconds = WeatherState::has(S.staleAgeS) ? S.staleAgeS : 0.0;
		Out.bValid = S.valid(nullptr);
		Out.bHasTemperature = WeatherState::has(S.tempC);
		Out.TemperatureC = SafeFloat(S.tempC);
		Out.DewpointC = SafeFloat(S.dewpointC);
		Out.RelativeHumidityPercent = SafeFloat(S.rh, 50.f);
		Out.bHasWind = WeatherState::has(S.windMps);
		Out.WindMps = SafeFloat(S.windMps);
		Out.WindGustMps = SafeFloat(S.windGustMps);
		Out.WindFromHeadingDeg = SafeFloat(S.windFromHeading);
		Out.PrecipType = ToUE(S.precipType);
		Out.bHasPrecipRate = WeatherState::has(S.precipRateMmph);
		Out.PrecipRateMmph = SafeFloat(S.precipRateMmph);
		Out.bHasCloudCover = WeatherState::has(S.cloudCover);
		Out.CloudCover = SafeFloat(S.cloudCover);
		Out.bHasVisibility = WeatherState::has(S.visibilityM);
		Out.VisibilityMetres = SafeFloat(S.visibilityM, 16093.f);
		Out.PressureHpa = SafeFloat(S.pressureHpa, 1013.25f);
		Out.bHasSnowDepth = WeatherState::has(S.snowDepthCm);
		Out.SnowDepthCm = SafeFloat(S.snowDepthCm);
		Out.bThunder = S.thunder;
		Out.CloudBaseMetres = CeilingMetres > 0.0 ? static_cast<float>(CeilingMetres) : 0.f;
		Out.Obscuration = ToFString(nycsim::weather::obscurationList(S.obscuration));
		Out.bInterpolated = S.interpolated;
		Out.RawText = ToFString(S.rawText);
	}
}

FNYCWeatherService::FNYCWeatherService(double PollIntervalSeconds)
{
	EffectsState = MakeUnique<nycsim::weather::WorldEffectsState>();

	std::vector<nycsim::weather::Provider> Providers;

	// --- NWS (primary): station observation, optionally carried along the gridpoint forecast trend.
	{
		nycsim::weather::Provider P;
		P.name = "nws";
		P.fetch = [this](double NowUnix) -> nycsim::Result<WeatherState>
		{
			const FDocument& Doc = NwsDoc;
			if (!Doc.bValid || Doc.ReceivedUnix < 0.0)
			{
				return nycsim::fail(nycsim::ErrorCode::IoError, "no NWS document", Doc.HttpStatus);
			}
			if (NowUnix - Doc.ReceivedUnix > MaxDocumentAgeSeconds)
			{
				return nycsim::fail(nycsim::ErrorCode::StateError, "NWS document too old",
					static_cast<int64_t>(NowUnix - Doc.ReceivedUnix));
			}
			const std::string Text(TCHAR_TO_UTF8(*Doc.Body));
			nycsim::Result<nycsim::json::Value> Parsed = nycsim::json::parse(Text);
			if (!Parsed)
			{
				return nycsim::failWith(Parsed.error());
			}
			nycsim::Result<WeatherState> State = nycsim::weather::parseNwsObservation(Parsed.value(), NowUnix);
			if (!State)
			{
				return nycsim::failWith(State.error());
			}
			if (GridpointDoc.bValid && GridpointDoc.ReceivedUnix >= 0.0 &&
				NowUnix - GridpointDoc.ReceivedUnix <= nycsim::weather::kNwsGridpointTtlS)
			{
				const std::string GridText(TCHAR_TO_UTF8(*GridpointDoc.Body));
				nycsim::Result<nycsim::json::Value> Grid = nycsim::json::parse(GridText);
				if (Grid)
				{
					nycsim::Result<nycsim::weather::NwsForecastBlend> Blend =
						nycsim::weather::NwsForecastBlend::fromJson(Grid.value());
					if (Blend)
					{
						Blend.value().apply(State.value(), NowUnix);
					}
				}
			}
			return State;
		};
		Providers.push_back(std::move(P));
	}

	// --- Open-Meteo (secondary).
	{
		nycsim::weather::Provider P;
		P.name = "open_meteo";
		P.fetch = [this](double NowUnix) -> nycsim::Result<WeatherState>
		{
			const FDocument& Doc = OpenMeteoDoc;
			if (!Doc.bValid || Doc.ReceivedUnix < 0.0)
			{
				return nycsim::fail(nycsim::ErrorCode::IoError, "no Open-Meteo document", Doc.HttpStatus);
			}
			if (NowUnix - Doc.ReceivedUnix > MaxDocumentAgeSeconds)
			{
				return nycsim::fail(nycsim::ErrorCode::StateError, "Open-Meteo document too old",
					static_cast<int64_t>(NowUnix - Doc.ReceivedUnix));
			}
			const std::string Text(TCHAR_TO_UTF8(*Doc.Body));
			nycsim::Result<nycsim::json::Value> Parsed = nycsim::json::parse(Text);
			if (!Parsed)
			{
				return nycsim::failWith(Parsed.error());
			}
			return nycsim::weather::parseOpenMeteo(Parsed.value(), NowUnix);
		};
		Providers.push_back(std::move(P));
	}

	// --- METAR (tertiary): raw text from tgftp, decoded by the core's FMH-1 parser.
	{
		nycsim::weather::Provider P;
		P.name = "metar";
		P.fetch = [this](double NowUnix) -> nycsim::Result<WeatherState>
		{
			const FDocument& Doc = MetarDoc;
			if (!Doc.bValid || Doc.ReceivedUnix < 0.0)
			{
				return nycsim::fail(nycsim::ErrorCode::IoError, "no METAR document", Doc.HttpStatus);
			}
			if (NowUnix - Doc.ReceivedUnix > MaxDocumentAgeSeconds)
			{
				return nycsim::fail(nycsim::ErrorCode::StateError, "METAR document too old",
					static_cast<int64_t>(NowUnix - Doc.ReceivedUnix));
			}
			const std::string Text(TCHAR_TO_UTF8(*Doc.Body));
			nycsim::Result<nycsim::weather::metar::MetarReport> Report =
				nycsim::weather::metar::parseMetar(Text.c_str(), NowUnix);
			if (!Report)
			{
				return nycsim::failWith(Report.error());
			}
			const double Ceiling = Report.value().ceilingM();
			if (WeatherState::has(Ceiling))
			{
				CeilingMetres = Ceiling;
			}
			else if (Report.value().clouds.empty() && Report.value().hasSkyClearCode)
			{
				CeilingMetres = -1.0; // sky clear: no ceiling, and that is a fact, not a gap
			}
			return nycsim::weather::metar::weatherStateFromMetar(
				Report.value(), NowUnix, Report.value().observationTimeUnix);
		};
		Providers.push_back(std::move(P));
	}

	Service = MakeUnique<nycsim::weather::WeatherService>(std::move(Providers), PollIntervalSeconds);
}

FNYCWeatherService::~FNYCWeatherService() = default;

FString FNYCWeatherService::ProviderUrl(ENYCWeatherProvider Provider, const FString& Station, double LatitudeDeg, double LongitudeDeg)
{
	switch (Provider)
	{
	case ENYCWeatherProvider::Nws:
	{
		FString Url = ToFString(nycsim::weather::kNwsObsUrlTemplate);
		return Url.Replace(TEXT("{station}"), *Station);
	}
	case ENYCWeatherProvider::NwsGridpoint:
		return ToFString(nycsim::weather::kNwsGridpointUrl);
	case ENYCWeatherProvider::OpenMeteo:
	{
		// The core owns the query string (the decoder depends on exactly these fields); only the site moves.
		FString Url = ToFString(nycsim::weather::kOpenMeteoUrl);
		Url = Url.Replace(TEXT("latitude=40.7831"), *FString::Printf(TEXT("latitude=%.4f"), LatitudeDeg));
		Url = Url.Replace(TEXT("longitude=-73.9712"), *FString::Printf(TEXT("longitude=%.4f"), LongitudeDeg));
		return Url;
	}
	case ENYCWeatherProvider::Metar:
	default:
		return MetarUrl(Station);
	}
}

FString FNYCWeatherService::MetarUrl(const FString& Station)
{
	return FString::Printf(TEXT("https://tgftp.nws.noaa.gov/data/observations/metar/stations/%s.TXT"), *Station.ToUpper());
}

FNYCWeatherService::FDocument& FNYCWeatherService::DocumentFor(ENYCWeatherProvider Provider)
{
	switch (Provider)
	{
	case ENYCWeatherProvider::Nws: return NwsDoc;
	case ENYCWeatherProvider::OpenMeteo: return OpenMeteoDoc;
	case ENYCWeatherProvider::NwsGridpoint: return GridpointDoc;
	case ENYCWeatherProvider::Metar:
	default: return MetarDoc;
	}
}

const FNYCWeatherService::FDocument& FNYCWeatherService::DocumentFor(ENYCWeatherProvider Provider) const
{
	return const_cast<FNYCWeatherService*>(this)->DocumentFor(Provider);
}

void FNYCWeatherService::SetProviderDocument(ENYCWeatherProvider Provider, const FString& Body, double ReceivedUnix,
	bool bSuccess, int32 HttpStatus, const FString& Error)
{
	FDocument& Doc = DocumentFor(Provider);
	Doc.HttpStatus = HttpStatus;
	if (bSuccess && !Body.IsEmpty())
	{
		Doc.Body = Body;
		Doc.ReceivedUnix = ReceivedUnix;
		Doc.bValid = true;
		Doc.Error.Empty();
	}
	else
	{
		// The previous document is kept: the core's staleness rules decide whether it is still usable.
		Doc.Error = Error;
		Doc.bValid = Doc.bValid && !Doc.Body.IsEmpty();
	}
}

void FNYCWeatherService::SetMetarDocument(const FString& Station, const FString& Text, double ReceivedUnix,
	bool bSuccess, int32 HttpStatus, const FString& Error)
{
	if (!bSuccess || Text.IsEmpty())
	{
		MetarDoc.HttpStatus = HttpStatus;
		MetarDoc.Error = Error;
		return;
	}
	// Keep the freshest station: tgftp files carry the report time, and the core resolves it at parse time.
	if (!MetarDoc.bValid || ReceivedUnix >= MetarDoc.ReceivedUnix)
	{
		MetarDoc.Body = Text;
		MetarDoc.ReceivedUnix = ReceivedUnix;
		MetarDoc.bValid = true;
		MetarDoc.HttpStatus = HttpStatus;
		MetarDoc.Error.Empty();
		MetarStation = Station;
	}
}

const FNYCWeatherState& FNYCWeatherService::Poll(double NowUnix)
{
	const WeatherState& S = Service->poll(NowUnix);
	Convert(S, CeilingMetres, Current);
	return Current;
}

FNYCWorldEffects FNYCWeatherService::StepWorldEffects(double DeltaSeconds)
{
	const nycsim::weather::WorldEffects E =
		nycsim::weather::worldEffectsStep(Service->current(), *EffectsState, DeltaSeconds);

	FNYCWorldEffects Out;
	Out.Wetness = static_cast<float>(E.wetness);
	Out.Puddles = static_cast<float>(E.puddles);
	Out.SnowCover = static_cast<float>(E.snowCover);
	Out.SnowDepthMetres = static_cast<float>(E.snowDepthM);
	Out.IceRisk = static_cast<float>(E.iceRisk);
	Out.FogDensity = static_cast<float>(E.fogDensity);
	Out.WindSpeedMps = static_cast<float>(E.windSpeedMps);
	Out.WindGustMps = static_cast<float>(E.windGustMps);
	Out.WindHeadingDeg = static_cast<float>(E.windHeadingDeg);
	Out.FlagSway = static_cast<float>(E.flagSway);
	Out.UmbrellaShare = static_cast<float>(E.umbrellaShare);
	Out.PedestrianDensityScale = static_cast<float>(E.pedestrianDensityScale);
	Out.PlowActivity = static_cast<float>(E.plowActivity);
	Out.Overcast = static_cast<float>(E.overcast);
	Out.RainRateMmph = static_cast<float>(E.rainRateMmph);
	Out.SnowRateCmph = static_cast<float>(E.snowRateCmph);
	Out.bHeadlights = E.headlights;
	Out.bWipers = E.wipers;
	Out.WiperSpeed = E.wiperSpeed;
	Out.bThunder = E.thunder;
	Out.SurfaceClass = static_cast<uint8>(E.surface);
	Out.SurfaceName = ToFString(nycsim::vehicle::surfaceClassName(E.surface));
	return Out;
}

bool FNYCWeatherService::RestoreFromJson(const FString& JsonText, FString& OutError)
{
	const std::string Text(TCHAR_TO_UTF8(*JsonText));
	nycsim::Result<WeatherState> Restored = nycsim::weather::fromWeatherJson(Text.c_str());
	if (!Restored)
	{
		const FString Message = ToFString(Restored.error().message);
		const FString CodeName = ToFString(nycsim::errorCodeName(Restored.error().code));
		OutError = FString::Printf(TEXT("%s (%s)"), Message.IsEmpty() ? TEXT("parse error") : *Message, *CodeName);
		return false;
	}
	Service->restoreLastGood(Restored.value());
	Convert(Restored.value(), CeilingMetres, Current);
	return true;
}

FString FNYCWeatherService::ToJson() const
{
	const std::vector<nycsim::weather::ProviderStatus> Status = Service->providerStatus(Service->current().fetchedAtUnix);
	return ToFString(nycsim::weather::toWeatherJson(Service->current(), Status));
}

TArray<FNYCProviderStatus> FNYCWeatherService::ProviderStatus(double NowUnix) const
{
	TArray<FNYCProviderStatus> Out;
	const std::vector<nycsim::weather::ProviderStatus> Status = Service->providerStatus(NowUnix);
	Out.Reserve(static_cast<int32>(Status.size()));
	for (const nycsim::weather::ProviderStatus& S : Status)
	{
		FNYCProviderStatus Entry;
		Entry.Name = ToFString(S.name);
		Entry.Status = ToFString(S.status);
		const FDocument* Doc = nullptr;
		if (Entry.Name == TEXT("nws")) { Doc = &NwsDoc; }
		else if (Entry.Name == TEXT("open_meteo")) { Doc = &OpenMeteoDoc; }
		else if (Entry.Name == TEXT("metar")) { Doc = &MetarDoc; }
		if (Doc)
		{
			Entry.DocumentAgeSeconds = Doc->ReceivedUnix >= 0.0 ? NowUnix - Doc->ReceivedUnix : -1.0;
			Entry.LastError = Doc->Error;
			Entry.HttpStatus = Doc->HttpStatus;
		}
		Out.Add(MoveTemp(Entry));
	}
	return Out;
}

uint64 FNYCWeatherService::PollCount() const { return Service->polls(); }
uint64 FNYCWeatherService::FailureCount() const { return Service->failures(); }
