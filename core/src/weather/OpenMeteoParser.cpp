#include "nycsim/weather/OpenMeteoParser.h"

#include <cmath>
#include <cstdio>
#include <string>

namespace nycsim {
namespace weather {

namespace {

struct WmoEntry {
  int32_t code;
  PrecipType type;
  metar::Intensity intensity;
  bool thunder;
  uint16_t obscuration;
};
constexpr WmoEntry kWmoTable[] = {
    {0, PrecipType::None, metar::Intensity::Moderate, false, 0},
    {1, PrecipType::None, metar::Intensity::Moderate, false, 0},
    {2, PrecipType::None, metar::Intensity::Moderate, false, 0},
    {3, PrecipType::None, metar::Intensity::Moderate, false, 0},
    {45, PrecipType::None, metar::Intensity::Moderate, false, kObscFG},
    {48, PrecipType::None, metar::Intensity::Moderate, false, kObscFG},
    {51, PrecipType::Drizzle, metar::Intensity::Light, false, 0},
    {53, PrecipType::Drizzle, metar::Intensity::Moderate, false, 0},
    {55, PrecipType::Drizzle, metar::Intensity::Heavy, false, 0},
    {56, PrecipType::FreezingRain, metar::Intensity::Light, false, 0},
    {57, PrecipType::FreezingRain, metar::Intensity::Heavy, false, 0},
    {61, PrecipType::Rain, metar::Intensity::Light, false, 0},
    {63, PrecipType::Rain, metar::Intensity::Moderate, false, 0},
    {65, PrecipType::Rain, metar::Intensity::Heavy, false, 0},
    {66, PrecipType::FreezingRain, metar::Intensity::Light, false, 0},
    {67, PrecipType::FreezingRain, metar::Intensity::Heavy, false, 0},
    {71, PrecipType::Snow, metar::Intensity::Light, false, 0},
    {73, PrecipType::Snow, metar::Intensity::Moderate, false, 0},
    {75, PrecipType::Snow, metar::Intensity::Heavy, false, 0},
    {77, PrecipType::Snow, metar::Intensity::Light, false, 0},
    {80, PrecipType::Rain, metar::Intensity::Light, false, 0},
    {81, PrecipType::Rain, metar::Intensity::Moderate, false, 0},
    {82, PrecipType::Rain, metar::Intensity::Heavy, false, 0},
    {85, PrecipType::Snow, metar::Intensity::Light, false, 0},
    {86, PrecipType::Snow, metar::Intensity::Heavy, false, 0},
    {95, PrecipType::Rain, metar::Intensity::Moderate, true, 0},
    {96, PrecipType::Sleet, metar::Intensity::Moderate, true, 0},
    {99, PrecipType::Sleet, metar::Intensity::Heavy, true, 0},
};

double numberOr(const json::Value* parent, const char* key, double fallback) {
  if (!parent) return fallback;
  const json::Value* v = parent->find(key);
  if (!v || !v->isNumber()) return fallback;
  return v->asNumber();
}

bool hasNumber(const json::Value* parent, const char* key) {
  if (!parent) return false;
  const json::Value* v = parent->find(key);
  return v && v->isNumber();
}

}  // namespace

WmoMapping wmoCodeMapping(int32_t code) {
  for (const WmoEntry& e : kWmoTable) {
    if (e.code == code) {
      WmoMapping m;
      m.type = e.type;
      m.intensity = e.intensity;
      m.thunder = e.thunder;
      m.obscuration = e.obscuration;
      m.known = true;
      return m;
    }
  }
  return WmoMapping();
}

Result<WeatherState> parseOpenMeteo(const json::Value& doc, double nowUnix) {
  const json::Value* err = doc.find("error");
  if (err && err->isBool() && err->asBool()) {
    return fail(ErrorCode::StateError, "Open-Meteo: API reported an error");
  }
  const json::Value* cur = doc.find("current");
  if (!cur || !cur->isObject() || !hasNumber(cur, "temperature_2m")) {
    return fail(ErrorCode::ParseError, "Open-Meteo: response without a usable current block");
  }
  const json::Value* timeV = cur->find("time");
  if (!timeV || !timeV->isString()) {
    return fail(ErrorCode::ParseError, "Open-Meteo: current block without a time");
  }
  NYCSIM_TRY(tObs, parseIso8601(std::string(timeV->str()).c_str()));
  if (nowUnix - tObs > kMaxObservationAgeS) {
    return fail(ErrorCode::StateError, "Open-Meteo: current block too old",
                static_cast<int64_t>(nowUnix - tObs));
  }
  double intervalS = numberOr(cur, "interval", 900.0);
  if (!(intervalS > 0.0)) intervalS = 900.0;

  WeatherState s;
  s.source = Source::OpenMeteo;
  s.observedAtUnix = tObs;
  {
    char buf[96];
    const double lat = numberOr(&doc, "latitude", kCentralParkLat);
    const double lon = numberOr(&doc, "longitude", kCentralParkLon);
    const int n = std::snprintf(buf, sizeof buf, "open-meteo:%g,%g", lat, lon);
    if (n > 0) s.station.assign(buf, static_cast<size_t>(n));
  }
  s.tempC = numberOr(cur, "temperature_2m", WeatherState::kNaN());
  s.rh = hasNumber(cur, "relative_humidity_2m") ? numberOr(cur, "relative_humidity_2m", 0.0)
                                                : WeatherState::kNaN();
  s.dewpointC = hasNumber(cur, "dew_point_2m") ? numberOr(cur, "dew_point_2m", 0.0)
                                               : WeatherState::kNaN();
  if (std::isnan(s.dewpointC) && !std::isnan(s.rh)) s.dewpointC = dewpointFromRh(s.tempC, s.rh);
  if (std::isnan(s.rh) && !std::isnan(s.dewpointC)) s.rh = relativeHumidity(s.tempC, s.dewpointC);
  s.windMps = hasNumber(cur, "wind_speed_10m") ? numberOr(cur, "wind_speed_10m", 0.0)
                                               : WeatherState::kNaN();
  s.windGustMps = hasNumber(cur, "wind_gusts_10m") ? numberOr(cur, "wind_gusts_10m", 0.0)
                                                   : WeatherState::kNaN();
  const bool haveDir = hasNumber(cur, "wind_direction_10m");
  setWind(s, (!haveDir || s.windMps == 0.0) ? WeatherState::kNaN()
                                            : numberOr(cur, "wind_direction_10m", 0.0));
  s.cloudCover = hasNumber(cur, "cloud_cover")
                     ? clampD(numberOr(cur, "cloud_cover", 0.0) / 100.0, 0.0, 1.0)
                     : WeatherState::kNaN();
  s.pressureHpa = hasNumber(cur, "pressure_msl") ? numberOr(cur, "pressure_msl", 0.0)
                                                 : WeatherState::kNaN();

  const int32_t code = static_cast<int32_t>(numberOr(cur, "weather_code", 0.0));
  WmoMapping m = wmoCodeMapping(code);
  const double perH = 3600.0 / intervalS;
  const double precip = numberOr(cur, "precipitation", 0.0) * perH;  // mm in the interval -> mm/h
  const double rain = numberOr(cur, "rain", 0.0) + numberOr(cur, "showers", 0.0);
  const double snowCm = numberOr(cur, "snowfall", 0.0);  // cm in the interval
  PrecipType kind = m.type;
  if (kind == PrecipType::None && precip > 0.0) {
    // The code says dry but the model produced precipitation: type from the rain/snow partition.
    kind = (rain > 0.0 && snowCm > 0.0) ? PrecipType::Sleet
                                        : (snowCm > 0.0 ? PrecipType::Snow : PrecipType::Rain);
  }
  if (kind != PrecipType::None) {
    if (precip > 0.0) {
      s.precipRateMmph = precip;
      s.precipRateBasis = PrecipRateBasis::Measured;
    } else {
      s.precipRateMmph = metar::intensityRateMmph(kind, m.intensity);
      s.precipRateBasis = PrecipRateBasis::Class;
    }
  } else {
    s.precipRateMmph = 0.0;
    s.precipRateBasis = PrecipRateBasis::None;
  }
  s.precipType = kind;
  s.thunder = m.thunder;
  s.obscuration = m.obscuration;
  if (snowCm > 0.0) {
    s.snowfallRateCmph = snowCm * perH;
  } else if (kind == PrecipType::Snow || kind == PrecipType::Sleet) {
    s.snowfallRateCmph = 0.0;
  }

  // Visibility comes from the minutely_15 block at the sample closest to the current time.
  const json::Value* m15 = doc.find("minutely_15");
  if (m15 && m15->isObject()) {
    const json::Value* times = m15->find("time");
    const json::Value* vis = m15->find("visibility");
    if (times && times->isArray() && vis && vis->isArray()) {
      double bestDelta = 0.0;
      double bestValue = WeatherState::kNaN();
      bool have = false;
      const size_t n = times->size();
      for (size_t i = 0; i < n; ++i) {
        const json::Value* tv = times->at(i);
        const json::Value* vv = vis->at(i);
        if (!tv || !tv->isString() || !vv || !vv->isNumber()) continue;
        const Result<double> ts = parseIso8601(std::string(tv->str()).c_str());
        if (!ts) continue;
        const double d = std::fabs(ts.value() - tObs);
        if (!have || d < bestDelta) {
          have = true;
          bestDelta = d;
          bestValue = vv->asNumber();
        }
      }
      if (have && bestDelta <= 15.0 * 60.0) s.visibilityM = bestValue;
    }
  }
  {
    char buf[32];
    const int n = std::snprintf(buf, sizeof buf, "WMO %d", code);
    if (n > 0) s.rawText.assign(buf, static_cast<size_t>(n));
  }
  return s;
}

}  // namespace weather
}  // namespace nycsim
