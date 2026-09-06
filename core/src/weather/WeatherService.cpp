#include "nycsim/weather/WeatherService.h"

#include <cmath>
#include <cstdio>
#include <cstring>

#include "nycsim/io/Json.h"

namespace nycsim {
namespace weather {

namespace {

double roundTo3(double v) { return std::round(v * 1000.0) / 1000.0; }
double roundTo2(double v) { return std::round(v * 100.0) / 100.0; }

void setOrNull(json::Value& obj, const char* key, double v) {
  if (std::isnan(v)) {
    obj.set(key, json::Value(nullptr));
  } else {
    obj.set(key, json::Value(roundTo3(v)));
  }
}

double numberOrNaN(const json::Value& obj, const char* key) {
  const json::Value* v = obj.find(key);
  if (!v || !v->isNumber()) return WeatherState::kNaN();
  return v->asNumber();
}

}  // namespace

// ---- CircuitBreaker -------------------------------------------------------------------------------

CircuitBreaker::CircuitBreaker(const char* name, int32_t failureThreshold, double openSeconds)
    : name_(name ? name : ""),
      failureThreshold_(failureThreshold > 0 ? failureThreshold : 1),
      openSeconds_(openSeconds > 0.0 ? openSeconds : 1.0) {}

bool CircuitBreaker::allow(double now) {
  if (state_ == State::Open) {
    if (!std::isnan(openedAt_) && now - openedAt_ >= openSeconds_) {
      state_ = State::HalfOpen;
      return true;
    }
    return false;
  }
  return true;
}

void CircuitBreaker::recordSuccess(double now) {
  state_ = State::Closed;
  consecutiveFailures_ = 0;
  openedAt_ = WeatherState::kNaN();
  lastError_.clear();
  lastSuccessAt_ = now;
}

void CircuitBreaker::recordFailure(double now, const char* error) {
  ++consecutiveFailures_;
  lastError_ = error ? error : "";
  if (state_ == State::HalfOpen || consecutiveFailures_ >= failureThreshold_) {
    state_ = State::Open;
    openedAt_ = now;
  }
}

std::string CircuitBreaker::status(double now) const {
  if (state_ == State::Open && !std::isnan(openedAt_)) {
    const double remaining = std::fmax(0.0, openSeconds_ - (now - openedAt_));
    char buf[32];
    const int n = std::snprintf(buf, sizeof buf, "open(%.0fs)", remaining);
    return n > 0 ? std::string(buf, static_cast<size_t>(n)) : std::string("open");
  }
  if (state_ == State::HalfOpen) return "half_open";
  return "closed";
}

// ---- SnowModel ------------------------------------------------------------------------------------

double SnowModel::snowLiquidRatio(double tempC, PrecipType type) {
  if (type == PrecipType::Sleet) return 3.0;
  if (std::isnan(tempC) || tempC >= 0.0) return 8.0;
  if (tempC >= -5.0) return 10.0;
  if (tempC >= -10.0) return 13.0;
  return 18.0;
}

void SnowModel::restore(double depthCm, double lastUpdateUnix, SnowDepthSource source) {
  depthCm_ = depthCm > 0.0 ? depthCm : 0.0;
  lastUpdateUnix_ = lastUpdateUnix;
  source_ = source;
}

void SnowModel::update(WeatherState& s, double nowUnix) {
  if (s.snowDepthSource == SnowDepthSource::Observed && !std::isnan(s.snowDepthCm)) {
    depthCm_ = s.snowDepthCm;
    source_ = SnowDepthSource::Observed;
  } else {
    const double dtH = std::isnan(lastUpdateUnix_)
                           ? 0.0
                           : clampD((nowUnix - lastUpdateUnix_) / 3600.0, 0.0, kMaxStepH);
    double depth = depthCm_;
    double rateCmph = 0.0;
    const double precipRate = std::isnan(s.precipRateMmph) ? 0.0 : s.precipRateMmph;
    if ((s.precipType == PrecipType::Snow || s.precipType == PrecipType::Sleet) && precipRate > 0.0) {
      if (!std::isnan(s.snowfallRateCmph) && s.snowfallRateCmph > 0.0) {
        rateCmph = s.snowfallRateCmph;
      } else {
        rateCmph = precipRate * snowLiquidRatio(s.tempC, s.precipType) / 10.0;
        s.snowfallRateCmph = rateCmph;
      }
    }
    depth += rateCmph * dtH;
    if (!std::isnan(s.tempC) && s.tempC > 1.0) depth -= kMeltCmPerHPerC * (s.tempC - 1.0) * dtH;
    if ((s.precipType == PrecipType::Rain || s.precipType == PrecipType::Drizzle ||
         s.precipType == PrecipType::FreezingRain) &&
        precipRate > 0.0) {
      depth -= kRainMeltCmPerMm * precipRate * dtH;
    }
    depth *= std::fmax(0.0, 1.0 - kSettlePerDay * dtH / 24.0);
    depthCm_ = std::fmax(0.0, depth);
    source_ = depthCm_ > 0.0 ? SnowDepthSource::Model : SnowDepthSource::None;
    s.snowDepthCm = roundTo2(depthCm_);
    s.snowDepthSource = source_;
  }
  lastUpdateUnix_ = nowUnix;
}

// ---- WeatherService -------------------------------------------------------------------------------

WeatherService::WeatherService(std::vector<Provider> providers, double pollIntervalS)
    : providers_(std::move(providers)), pollIntervalS_(pollIntervalS) {
  breakers_.reserve(providers_.size());
  for (const Provider& p : providers_) breakers_.emplace_back(p.name.c_str());
}

void WeatherService::restoreLastGood(const WeatherState& s) {
  lastGood_ = s;
  hasLastGood_ = true;
}

CircuitBreaker* WeatherService::breaker(const char* name) {
  if (!name) return nullptr;
  for (size_t i = 0; i < providers_.size(); ++i) {
    if (providers_[i].name == name) return &breakers_[i];
  }
  return nullptr;
}

std::vector<ProviderStatus> WeatherService::providerStatus(double nowUnix) const {
  std::vector<ProviderStatus> out;
  out.reserve(breakers_.size());
  for (const CircuitBreaker& b : breakers_) out.push_back(ProviderStatus{b.name(), b.status(nowUnix)});
  return out;
}

const WeatherState& WeatherService::poll(double nowUnix) {
  ++polls_;
  bool got = false;
  WeatherState obs;
  for (size_t i = 0; i < providers_.size(); ++i) {
    CircuitBreaker& b = breakers_[i];
    if (!b.allow(nowUnix)) continue;
    if (!providers_[i].fetch) {
      b.recordFailure(nowUnix, "provider has no fetch function");
      continue;
    }
    Result<WeatherState> r = providers_[i].fetch(nowUnix);
    if (!r) {
      b.recordFailure(nowUnix, r.error().message);
      continue;
    }
    b.recordSuccess(nowUnix);
    obs = r.value();
    got = true;
    break;
  }
  if (got) {
    obs.fetchedAtUnix = nowUnix;
    obs.staleAgeS = std::isnan(obs.observedAtUnix) ? WeatherState::kNaN()
                                                   : std::fmax(0.0, nowUnix - obs.observedAtUnix);
    snow_.update(obs, nowUnix);
    lastGood_ = obs;
    hasLastGood_ = true;
    current_ = obs;
  } else {
    ++failures_;
    if (hasLastGood_) {
      WeatherState stale = lastGood_;
      stale.source = Source::Stale;
      stale.fetchedAtUnix = nowUnix;
      stale.staleAgeS = std::isnan(stale.observedAtUnix)
                            ? WeatherState::kNaN()
                            : std::fmax(0.0, nowUnix - stale.observedAtUnix);
      stale.interpolated = false;
      // Keep melting / settling from the last known temperature.
      stale.snowDepthSource = SnowDepthSource::Model;
      if (snow_.source() == SnowDepthSource::Observed) stale.snowDepthSource = SnowDepthSource::Model;
      snow_.update(stale, nowUnix);
      current_ = stale;
    } else {
      WeatherState empty;
      empty.source = Source::Stale;
      empty.fetchedAtUnix = nowUnix;
      empty.snowDepthSource = SnowDepthSource::None;
      current_ = empty;
    }
  }
  return current_;
}

// ---- JSON -----------------------------------------------------------------------------------------

std::string toWeatherJson(const WeatherState& s, const std::vector<ProviderStatus>& status) {
  json::Value o = json::Value::object();
  o.set("schema_version", json::Value(s.schemaVersion));
  o.set("observed_at", std::isnan(s.observedAtUnix) ? json::Value(nullptr)
                                                    : json::Value(isoUtc(s.observedAtUnix)));
  o.set("station", s.station.empty() ? json::Value(nullptr) : json::Value(s.station));
  o.set("source", json::Value(sourceName(s.source)));
  setOrNull(o, "temp_c", s.tempC);
  setOrNull(o, "dewpoint_c", s.dewpointC);
  setOrNull(o, "rh", s.rh);
  setOrNull(o, "wind_mps", s.windMps);
  setOrNull(o, "wind_gust_mps", s.windGustMps);
  setOrNull(o, "wind_dir_deg", s.windDirDeg);
  o.set("precip_type", json::Value(precipTypeName(s.precipType)));
  setOrNull(o, "precip_rate_mmph", s.precipRateMmph);
  setOrNull(o, "cloud_cover", s.cloudCover);
  setOrNull(o, "visibility_m", s.visibilityM);
  setOrNull(o, "pressure_hpa", s.pressureHpa);
  setOrNull(o, "snow_depth_cm", s.snowDepthCm);
  o.set("thunder", json::Value(s.thunder));
  o.set("fetched_at", std::isnan(s.fetchedAtUnix) ? json::Value(nullptr)
                                                  : json::Value(isoUtc(s.fetchedAtUnix)));
  setOrNull(o, "stale_age_s", s.staleAgeS);
  // ---- §12.1 extension
  setOrNull(o, "wind_from_heading", s.windFromHeading);
  setOrNull(o, "wind_to_heading", s.windToHeading);
  o.set("snow_depth_source", json::Value(snowDepthSourceName(s.snowDepthSource)));
  setOrNull(o, "snowfall_rate_cmph", s.snowfallRateCmph);
  o.set("precip_rate_basis", json::Value(precipRateBasisName(s.precipRateBasis)));
  json::Value obsc = json::Value::array();
  {
    const std::string list = obscurationList(s.obscuration);
    size_t i = 0;
    while (i < list.size()) {
      const size_t sp = list.find(' ', i);
      const size_t end = sp == std::string::npos ? list.size() : sp;
      obsc.push(json::Value(list.substr(i, end - i)));
      i = end == list.size() ? end : end + 1;
    }
  }
  o.set("obscuration", std::move(obsc));
  o.set("interpolated", json::Value(s.interpolated));
  o.set("raw_text", s.rawText.empty() ? json::Value(nullptr) : json::Value(s.rawText));
  json::Value ps = json::Value::object();
  for (const ProviderStatus& p : status) ps.set(p.name, json::Value(p.status));
  o.set("provider_status", std::move(ps));
  return json::dump(o, 1);
}

Result<WeatherState> fromWeatherJson(const char* text) {
  if (!text) return fail(ErrorCode::InvalidArgument, "weather: null JSON text");
  NYCSIM_TRY(doc, json::parse(text));
  if (!doc.isObject()) return fail(ErrorCode::ParseError, "weather: weather.json is not an object");
  WeatherState s;
  const json::Value* sv = doc.find("schema_version");
  if (!sv || !sv->isNumber() || static_cast<int32_t>(sv->asInt()) != kSchemaVersion) {
    return fail(ErrorCode::UnsupportedVersion, "weather: unsupported weather.json schema_version");
  }
  const json::Value* srcV = doc.find("source");
  if (!srcV || !srcV->isString() || !sourceFromName(std::string(srcV->str()).c_str(), s.source)) {
    return fail(ErrorCode::ParseError, "weather: unknown source");
  }
  const json::Value* obs = doc.find("observed_at");
  if (obs && obs->isString()) {
    NYCSIM_TRY(t, parseIso8601(std::string(obs->str()).c_str()));
    s.observedAtUnix = t;
  }
  const json::Value* fetched = doc.find("fetched_at");
  if (fetched && fetched->isString()) {
    const Result<double> t = parseIso8601(std::string(fetched->str()).c_str());
    if (t) s.fetchedAtUnix = t.value();
  }
  const json::Value* st = doc.find("station");
  if (st && st->isString()) s.station = std::string(st->str());
  s.tempC = numberOrNaN(doc, "temp_c");
  s.dewpointC = numberOrNaN(doc, "dewpoint_c");
  s.rh = numberOrNaN(doc, "rh");
  s.windMps = numberOrNaN(doc, "wind_mps");
  s.windGustMps = numberOrNaN(doc, "wind_gust_mps");
  s.windDirDeg = numberOrNaN(doc, "wind_dir_deg");
  s.precipRateMmph = numberOrNaN(doc, "precip_rate_mmph");
  s.cloudCover = numberOrNaN(doc, "cloud_cover");
  s.visibilityM = numberOrNaN(doc, "visibility_m");
  s.pressureHpa = numberOrNaN(doc, "pressure_hpa");
  s.snowDepthCm = numberOrNaN(doc, "snow_depth_cm");
  s.staleAgeS = numberOrNaN(doc, "stale_age_s");
  s.windFromHeading = numberOrNaN(doc, "wind_from_heading");
  s.windToHeading = numberOrNaN(doc, "wind_to_heading");
  s.snowfallRateCmph = numberOrNaN(doc, "snowfall_rate_cmph");
  const json::Value* pt = doc.find("precip_type");
  if (pt && pt->isString() && !precipTypeFromName(std::string(pt->str()).c_str(), s.precipType)) {
    return fail(ErrorCode::ParseError, "weather: unknown precip_type");
  }
  const json::Value* th = doc.find("thunder");
  if (th && th->isBool()) s.thunder = th->asBool();
  const json::Value* interp = doc.find("interpolated");
  if (interp && interp->isBool()) s.interpolated = interp->asBool();
  const json::Value* sds = doc.find("snow_depth_source");
  if (sds && sds->isString()) {
    const std::string v(sds->str());
    s.snowDepthSource = v == "observed" ? SnowDepthSource::Observed
                                        : (v == "model" ? SnowDepthSource::Model : SnowDepthSource::None);
  }
  const json::Value* prb = doc.find("precip_rate_basis");
  if (prb && prb->isString()) {
    const std::string v(prb->str());
    s.precipRateBasis = v == "measured" ? PrecipRateBasis::Measured
                                        : (v == "class" ? PrecipRateBasis::Class
                                                        : (v == "trace" ? PrecipRateBasis::Trace
                                                                        : (v == "model" ? PrecipRateBasis::Model
                                                                                        : PrecipRateBasis::None)));
  }
  const json::Value* ob = doc.find("obscuration");
  if (ob && ob->isArray()) {
    for (const json::Value& e : ob->items()) {
      if (!e.isString()) continue;
      s.obscuration |= obscurationBit(std::string(e.str()).c_str());
    }
  }
  const json::Value* rt = doc.find("raw_text");
  if (rt && rt->isString()) s.rawText = std::string(rt->str());
  return s;
}

}  // namespace weather
}  // namespace nycsim
