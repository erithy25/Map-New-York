#include "nycsim/weather/NwsParser.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include "nycsim/weather/MetarParser.h"

namespace nycsim {
namespace weather {

namespace {

/// MADIS quality control: X rejected, Q questioned, B subjective-bad.
bool badQc(const json::Value* field) {
  const json::Value* qc = field->find("qualityControl");
  if (!qc || !qc->isString()) return false;
  const std::string_view s = qc->asString();
  return s == "X" || s == "Q" || s == "B";
}

/// Numeric value of an NWS measurement object, NaN when absent, null or QC-rejected.
double qcValue(const json::Value* parent, const char* key) {
  if (!parent) return WeatherState::kNaN();
  const json::Value* f = parent->find(key);
  if (!f || !f->isObject()) return WeatherState::kNaN();
  const json::Value* v = f->find("value");
  if (!v || !v->isNumber()) return WeatherState::kNaN();
  if (badQc(f)) return WeatherState::kNaN();
  return v->asNumber();
}

std::string lower(std::string_view s) {
  std::string out(s);
  for (char& c : out) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  return out;
}

/// presentWeather.weather -> (precipitation kind, obscuration bit). Kind None means "no precip".
struct NwsWeatherEntry {
  const char* name;
  PrecipType kind;
  uint16_t obscuration;
  bool known;  ///< the token is in the table (as opposed to unmapped)
};
constexpr NwsWeatherEntry kNwsWeatherMap[] = {
    {"rain", PrecipType::Rain, 0, true},
    {"rain_showers", PrecipType::Rain, 0, true},
    {"drizzle", PrecipType::Drizzle, 0, true},
    {"snow", PrecipType::Snow, 0, true},
    {"snow_showers", PrecipType::Snow, 0, true},
    {"snow_grains", PrecipType::Snow, 0, true},
    {"ice_crystals", PrecipType::Snow, 0, true},
    {"sleet", PrecipType::Sleet, 0, true},
    {"ice_pellets", PrecipType::Sleet, 0, true},
    {"hail", PrecipType::Sleet, 0, true},
    {"snow_pellets", PrecipType::Sleet, 0, true},
    {"freezing_rain", PrecipType::FreezingRain, 0, true},
    {"freezing_drizzle", PrecipType::FreezingRain, 0, true},
    {"unknown_precipitation", PrecipType::Rain, 0, true},
    {"unknown", PrecipType::None, 0, true},
    {"thunderstorms", PrecipType::None, 0, true},
    {"fog_mist", PrecipType::None, kObscBR, true},
    {"fog", PrecipType::None, kObscFG, true},
    {"freezing_fog", PrecipType::None, kObscFG, true},
    {"haze", PrecipType::None, kObscHZ, true},
    {"smoke", PrecipType::None, kObscFU, true},
    {"dust", PrecipType::None, kObscDU, true},
    {"sand", PrecipType::None, kObscSA, true},
    {"volcanic_ash", PrecipType::None, kObscVA, true},
    {"squalls", PrecipType::None, kObscSQ, true},
    {"funnel_cloud", PrecipType::None, kObscFC, true},
    {"dust_whirls", PrecipType::None, kObscPO, true},
    {"sandstorm", PrecipType::None, kObscSS, true},
    {"duststorm", PrecipType::None, kObscDS, true},
};

NwsWeatherEntry lookupNwsWeather(const std::string& name) {
  for (const NwsWeatherEntry& e : kNwsWeatherMap) {
    if (name == e.name) return e;
  }
  return NwsWeatherEntry{"", PrecipType::None, 0, false};
}

metar::Intensity intensityFromNws(const json::Value* w) {
  const json::Value* v = w->find("intensity");
  if (!v || !v->isString()) return metar::Intensity::Moderate;
  const std::string s = lower(v->asString());
  if (s == "light") return metar::Intensity::Light;
  if (s == "heavy") return metar::Intensity::Heavy;
  return metar::Intensity::Moderate;
}

uint32_t phenomenaForKind(PrecipType k) {
  switch (k) {
    case PrecipType::Rain: return metar::kPhRA;
    case PrecipType::Drizzle: return metar::kPhDZ;
    case PrecipType::Snow: return metar::kPhSN;
    case PrecipType::Sleet: return metar::kPhPL;
    case PrecipType::FreezingRain: return metar::kPhRA;
    case PrecipType::None: return 0;
  }
  return 0;
}

bool startsWithAny(std::string_view s, std::initializer_list<const char*> prefixes) {
  for (const char* p : prefixes) {
    const size_t n = std::strlen(p);
    if (s.size() >= n && s.compare(0, n, p) == 0) return true;
  }
  return false;
}

metar::Cover coverFromNwsAmount(std::string_view amount, bool& ok) {
  ok = true;
  if (amount == "SKC") return metar::Cover::SKC;
  if (amount == "CLR") return metar::Cover::CLR;
  if (amount == "NSC") return metar::Cover::NSC;
  if (amount == "NCD") return metar::Cover::NCD;
  if (amount == "FEW") return metar::Cover::FEW;
  if (amount == "SCT") return metar::Cover::SCT;
  if (amount == "BKN") return metar::Cover::BKN;
  if (amount == "OVC") return metar::Cover::OVC;
  if (amount == "VV") return metar::Cover::VV;
  ok = false;
  return metar::Cover::FEW;
}

}  // namespace

// ---- GridSeries -----------------------------------------------------------------------------------

GridSeries::GridSeries(const json::Value* layer, double scale) {
  if (!layer || !layer->isObject()) return;
  const json::Value* values = layer->find("values");
  if (!values || !values->isArray()) return;
  for (const json::Value& entry : values->items()) {
    if (!entry.isObject()) continue;
    const json::Value* v = entry.find("value");
    if (!v || !v->isNumber()) continue;
    const json::Value* vt = entry.find("validTime");
    if (!vt || !vt->isString()) continue;
    const std::string valid(vt->str());
    const size_t slash = valid.find('/');
    const std::string start = slash == std::string::npos ? valid : valid.substr(0, slash);
    const Result<double> t0 = parseIso8601(start.c_str());
    if (!t0) continue;
    const double scaled = v->asNumber() * scale;
    t_.push_back(t0.value());
    v_.push_back(scaled);
    if (slash != std::string::npos && slash + 1 < valid.size()) {
      const Result<double> dur = parseIsoDuration(valid.c_str() + slash + 1);
      if (dur) {
        // Hold the value to the end of its validity so a long segment does not tilt the interpolation.
        t_.push_back(t0.value() + dur.value() - 1.0);
        v_.push_back(scaled);
      }
    }
  }
  // Stable sort by time, keeping the (t, v) pairing.
  std::vector<size_t> order(t_.size());
  for (size_t i = 0; i < order.size(); ++i) order[i] = i;
  std::stable_sort(order.begin(), order.end(), [this](size_t a, size_t b) {
    if (t_[a] != t_[b]) return t_[a] < t_[b];
    return v_[a] < v_[b];
  });
  std::vector<double> t2(t_.size()), v2(v_.size());
  for (size_t i = 0; i < order.size(); ++i) {
    t2[i] = t_[order[i]];
    v2[i] = v_[order[i]];
  }
  t_.swap(t2);
  v_.swap(v2);
}

double GridSeries::valueAt(double unix_s) const {
  if (t_.size() < 2 || unix_s < t_.front() || unix_s > t_.back()) return WeatherState::kNaN();
  size_t lo = 0;
  size_t hi = t_.size() - 1;
  while (hi - lo > 1) {
    const size_t mid = (lo + hi) / 2;
    if (t_[mid] <= unix_s) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  if (t_[hi] == t_[lo]) return v_[lo];
  const double f = (unix_s - t_[lo]) / (t_[hi] - t_[lo]);
  return v_[lo] + f * (v_[hi] - v_[lo]);
}

// ---- NwsForecastBlend -----------------------------------------------------------------------------

Result<NwsForecastBlend> NwsForecastBlend::fromJson(const json::Value& gridpoint) {
  const json::Value* p = gridpoint.find("properties");
  if (!p || !p->isObject()) {
    return fail(ErrorCode::ParseError, "NWS gridpoint: no properties object");
  }
  NwsForecastBlend b;
  const json::Value* ut = p->find("updateTime");
  if (ut && ut->isString()) {
    const Result<double> t = parseIso8601(std::string(ut->str()).c_str());
    if (t) b.updateTime_ = t.value();
  }
  b.temp_ = GridSeries(p->find("temperature"), 1.0);
  b.dewpoint_ = GridSeries(p->find("dewpoint"), 1.0);
  b.rh_ = GridSeries(p->find("relativeHumidity"), 1.0);
  b.wind_ = GridSeries(p->find("windSpeed"), kKmhToMps);
  b.gust_ = GridSeries(p->find("windGust"), kKmhToMps);
  b.cloud_ = GridSeries(p->find("skyCover"), 0.01);
  b.visibility_ = GridSeries(p->find("visibility"), 1.0);
  return b;
}

bool NwsForecastBlend::apply(WeatherState& s, double nowUnix) const {
  const double tObs = s.observedAtUnix;
  if (std::isnan(tObs) || nowUnix - tObs < kBlendMinAgeS) return false;
  bool changed = false;
  struct Field {
    const GridSeries* series;
    double* target;
    double limit;
    int clampKind;  // 0 none, 1 [0,1], 2 [0,100], 3 >= 0
  };
  const Field fields[] = {
      {&temp_, &s.tempC, kLimitTempC, 0},
      {&dewpoint_, &s.dewpointC, kLimitDewpointC, 0},
      {&rh_, &s.rh, kLimitRh, 2},
      {&wind_, &s.windMps, kLimitWindMps, 3},
      {&gust_, &s.windGustMps, kLimitWindGustMps, 3},
      {&cloud_, &s.cloudCover, kLimitCloudCover, 1},
      {&visibility_, &s.visibilityM, kLimitVisibilityM, 3},
  };
  for (const Field& f : fields) {
    if (std::isnan(*f.target)) continue;
    const double fNow = f.series->valueAt(nowUnix);
    const double fObs = f.series->valueAt(tObs);
    if (std::isnan(fNow) || std::isnan(fObs)) continue;
    const double delta = clampD(fNow - fObs, -f.limit, f.limit);
    double v = *f.target + delta;
    if (f.clampKind == 1) v = clampD(v, 0.0, 1.0);
    else if (f.clampKind == 2) v = clampD(v, 0.0, 100.0);
    else if (f.clampKind == 3) v = std::fmax(0.0, v);
    *f.target = v;
    changed = true;
  }
  if (changed && !std::isnan(s.tempC) && !std::isnan(s.dewpointC)) {
    s.dewpointC = std::fmin(s.dewpointC, s.tempC);
    s.rh = relativeHumidity(s.tempC, s.dewpointC);
  }
  s.interpolated = changed;
  return changed;
}

// ---- observation parser ---------------------------------------------------------------------------

Result<WeatherState> parseNwsObservation(const json::Value& doc, double nowUnix) {
  const json::Value* p = doc.find("properties");
  if (!p || !p->isObject()) return fail(ErrorCode::ParseError, "NWS: no properties object");
  const json::Value* ts = p->find("timestamp");
  if (!ts || !ts->isString()) return fail(ErrorCode::ParseError, "NWS: observation without timestamp");
  NYCSIM_TRY(tObs, parseIso8601(std::string(ts->str()).c_str()));
  if (nowUnix - tObs > kMaxObservationAgeS) {
    return fail(ErrorCode::StateError, "NWS: observation too old", static_cast<int64_t>(nowUnix - tObs));
  }
  const double temp = qcValue(p, "temperature");
  if (std::isnan(temp)) return fail(ErrorCode::ParseError, "NWS: observation without temperature");

  WeatherState s;
  s.source = Source::Nws;
  s.observedAtUnix = tObs;
  const json::Value* stationId = p->find("stationId");
  if (stationId && stationId->isString()) {
    s.station = std::string(stationId->str());
  } else {
    const json::Value* station = p->find("station");
    if (station && station->isString()) {
      const std::string url(station->str());
      const size_t slash = url.rfind('/');
      s.station = slash == std::string::npos ? url : url.substr(slash + 1);
    }
  }
  s.tempC = temp;
  s.dewpointC = qcValue(p, "dewpoint");
  double rh = qcValue(p, "relativeHumidity");
  if (std::isnan(rh) && !std::isnan(s.dewpointC)) rh = relativeHumidity(temp, s.dewpointC);
  s.rh = rh;
  if (std::isnan(s.dewpointC) && !std::isnan(rh)) s.dewpointC = dewpointFromRh(temp, rh);
  const double ws = qcValue(p, "windSpeed");
  s.windMps = std::isnan(ws) ? WeatherState::kNaN() : ws * kKmhToMps;
  const double wg = qcValue(p, "windGust");
  s.windGustMps = std::isnan(wg) ? WeatherState::kNaN() : wg * kKmhToMps;
  const double wd = qcValue(p, "windDirection");
  setWind(s, (std::isnan(wd) || (ws == 0.0 && wd == 0.0)) ? WeatherState::kNaN() : wd);
  s.visibilityM = qcValue(p, "visibility");
  const double slp = qcValue(p, "seaLevelPressure");
  const double bp = qcValue(p, "barometricPressure");
  if (!std::isnan(slp)) {
    s.pressureHpa = slp / 100.0;
  } else if (!std::isnan(bp)) {
    s.pressureHpa = bp / 100.0;
  }

  // ---- present weather
  std::vector<metar::WeatherGroup> groups;
  uint16_t obsc = 0;
  bool thunder = false;
  const json::Value* pw = p->find("presentWeather");
  if (pw && pw->isArray()) {
    for (const json::Value& w : pw->items()) {
      if (!w.isObject()) continue;
      const json::Value* wname = w.find("weather");
      const std::string name = (wname && wname->isString()) ? lower(wname->asString()) : std::string();
      const NwsWeatherEntry entry = lookupNwsWeather(name);
      const json::Value* rawv = w.find("rawString");
      const std::string raw = (rawv && rawv->isString()) ? std::string(rawv->str()) : std::string();
      if (!raw.empty()) {
        const std::string synthetic = "XXXX 000000Z " + raw;
        const Result<metar::MetarReport> r = metar::parseMetar(synthetic.c_str(), WeatherState::kNaN());
        if (r) {
          for (const metar::WeatherGroup& g : r.value().weather) groups.push_back(g);
        }
      }
      const json::Value* mod = w.find("modifier");
      const bool modThunder = mod && mod->isString() && mod->asString() == "thunderstorms";
      if (name == "thunderstorms" || modThunder ||
          startsWithAny(raw, {"TS", "-TS", "+TS", "VCTS"})) {
        thunder = true;
      }
      obsc |= entry.obscuration;
      if (entry.kind != PrecipType::None && raw.empty()) {
        // No raw group: synthesize one from the decoded fields so the classifier sees it.
        metar::WeatherGroup g;
        g.intensity = intensityFromNws(&w);
        g.descriptor =
            entry.kind == PrecipType::FreezingRain ? metar::Descriptor::FZ : metar::Descriptor::None;
        g.phenomena = phenomenaForKind(entry.kind);
        g.raw = name;
        groups.push_back(g);
      }
    }
  }
  s.thunder = thunder || metar::thunderPresent(groups);
  s.obscuration = static_cast<uint16_t>(obsc | metar::obscurationBits(groups));

  PrecipType kind = PrecipType::None;
  metar::Intensity governing = metar::Intensity::Moderate;
  metar::classifyPrecipitation(groups, temp, kind, governing);
  s.precipType = kind;
  const double p1h = qcValue(p, "precipitationLastHour");
  metar::precipitationRateMmph(groups, p1h, temp, s.precipRateMmph, s.precipRateBasis);
  if (kind == PrecipType::None && !std::isnan(p1h) && p1h > 0.0) {
    // Measured precipitation without a present-weather group (ASOS between showers): the type is
    // taken from the temperature and the measurement is the rate.
    s.precipType = temp > 1.0 ? PrecipType::Rain : PrecipType::Snow;
    s.precipRateMmph = p1h;
    s.precipRateBasis = PrecipRateBasis::Measured;
  }

  // ---- sky
  std::vector<metar::CloudLayer> layers;
  const json::Value* cl = p->find("cloudLayers");
  bool sawCloudLayersArray = false;
  if (cl && cl->isArray()) {
    sawCloudLayersArray = true;
    for (const json::Value& c : cl->items()) {
      if (!c.isObject()) continue;
      const json::Value* amount = c.find("amount");
      if (!amount || !amount->isString()) continue;
      bool ok = false;
      const metar::Cover cover = coverFromNwsAmount(amount->asString(), ok);
      if (!ok) continue;
      metar::CloudLayer layer;
      layer.cover = cover;
      const json::Value* base = c.find("base");
      layer.baseM = WeatherState::kNaN();
      if (base && base->isObject()) {
        const json::Value* bv = base->find("value");
        if (bv && bv->isNumber()) layer.baseM = bv->asNumber();
      }
      layers.push_back(layer);
    }
  }
  const json::Value* textDesc = p->find("textDescription");
  const bool clearCode =
      sawCloudLayersArray && cl->size() == 0 && textDesc && textDesc->isString() && !textDesc->str().empty();
  s.cloudCover = metar::cloudCoverFraction(layers, clearCode);

  // ---- raw METAR message: snow depth and a pressure fallback
  const json::Value* rawMsg = p->find("rawMessage");
  std::string raw;
  if (rawMsg && rawMsg->isString()) raw = std::string(rawMsg->str());
  if (!raw.empty()) {
    const Result<metar::MetarReport> r = metar::parseMetar(raw.c_str(), nowUnix);
    if (r) {
      if (!std::isnan(r.value().snowDepthCm)) {
        s.snowDepthCm = r.value().snowDepthCm;
        s.snowDepthSource = SnowDepthSource::Observed;
      }
      if (std::isnan(s.pressureHpa) && !std::isnan(r.value().seaLevelPressureHpa)) {
        s.pressureHpa = r.value().seaLevelPressureHpa;
      }
    }
  }
  if (!raw.empty()) {
    s.rawText = raw;
  } else if (textDesc && textDesc->isString()) {
    s.rawText = std::string(textDesc->str());
  }
  return s;
}

}  // namespace weather
}  // namespace nycsim
