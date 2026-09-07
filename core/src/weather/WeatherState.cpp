#include "nycsim/weather/WeatherState.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>

#include "nycsim/time/NyTime.h"

namespace nycsim {
namespace weather {

namespace {

struct ObscEntry {
  uint16_t bit;
  const char* code;
};
constexpr ObscEntry kObscTable[] = {
    {kObscBR, "BR"}, {kObscDS, "DS"}, {kObscDU, "DU"}, {kObscFC, "FC"}, {kObscFG, "FG"},
    {kObscFU, "FU"}, {kObscHZ, "HZ"}, {kObscPO, "PO"}, {kObscPY, "PY"}, {kObscSA, "SA"},
    {kObscSQ, "SQ"}, {kObscSS, "SS"}, {kObscVA, "VA"},
};
constexpr int kObscCount = static_cast<int>(sizeof(kObscTable) / sizeof(kObscTable[0]));

bool readInt(const char*& p, int digits, int& out) {
  int v = 0;
  for (int i = 0; i < digits; ++i) {
    if (p[i] < '0' || p[i] > '9') return false;
    v = v * 10 + (p[i] - '0');
  }
  p += digits;
  out = v;
  return true;
}

}  // namespace

double WeatherState::kNaN() { return std::numeric_limits<double>::quiet_NaN(); }
bool WeatherState::has(double v) { return !std::isnan(v); }

const char* precipTypeName(PrecipType t) {
  switch (t) {
    case PrecipType::None: return "none";
    case PrecipType::Rain: return "rain";
    case PrecipType::Snow: return "snow";
    case PrecipType::Sleet: return "sleet";
    case PrecipType::FreezingRain: return "freezing_rain";
    case PrecipType::Drizzle: return "drizzle";
  }
  return "none";
}

bool precipTypeFromName(const char* name, PrecipType& out) {
  if (!name) return false;
  const PrecipType all[] = {PrecipType::None,  PrecipType::Rain,         PrecipType::Snow,
                            PrecipType::Sleet, PrecipType::FreezingRain, PrecipType::Drizzle};
  for (PrecipType t : all) {
    if (std::strcmp(name, precipTypeName(t)) == 0) {
      out = t;
      return true;
    }
  }
  return false;
}

int precipTypeRank(PrecipType t) {
  switch (t) {
    case PrecipType::None: return 0;
    case PrecipType::Drizzle: return 1;
    case PrecipType::Rain: return 2;
    case PrecipType::Snow: return 3;
    case PrecipType::Sleet: return 4;
    case PrecipType::FreezingRain: return 5;
  }
  return 0;
}

const char* sourceName(Source s) {
  switch (s) {
    case Source::Nws: return "nws";
    case Source::OpenMeteo: return "open_meteo";
    case Source::Metar: return "metar";
    case Source::Stale: return "stale";
  }
  return "stale";
}

bool sourceFromName(const char* name, Source& out) {
  if (!name) return false;
  const Source all[] = {Source::Nws, Source::OpenMeteo, Source::Metar, Source::Stale};
  for (Source s : all) {
    if (std::strcmp(name, sourceName(s)) == 0) {
      out = s;
      return true;
    }
  }
  return false;
}

const char* snowDepthSourceName(SnowDepthSource s) {
  switch (s) {
    case SnowDepthSource::None: return "none";
    case SnowDepthSource::Observed: return "observed";
    case SnowDepthSource::Model: return "model";
  }
  return "none";
}

const char* precipRateBasisName(PrecipRateBasis b) {
  switch (b) {
    case PrecipRateBasis::None: return "none";
    case PrecipRateBasis::Measured: return "measured";
    case PrecipRateBasis::Class: return "class";
    case PrecipRateBasis::Trace: return "trace";
    case PrecipRateBasis::Model: return "model";
  }
  return "none";
}

const char* obscurationCode(uint16_t singleBit) {
  for (int i = 0; i < kObscCount; ++i) {
    if (kObscTable[i].bit == singleBit) return kObscTable[i].code;
  }
  return "";
}

uint16_t obscurationBit(const char* code) {
  if (!code) return 0;
  for (int i = 0; i < kObscCount; ++i) {
    if (std::strcmp(kObscTable[i].code, code) == 0) return kObscTable[i].bit;
  }
  return 0;
}

std::string obscurationList(uint16_t bits) {
  std::string out;
  for (int i = 0; i < kObscCount; ++i) {  // kObscTable is in alphabetical order
    if ((bits & kObscTable[i].bit) == 0) continue;
    if (!out.empty()) out.push_back(' ');
    out += kObscTable[i].code;
  }
  return out;
}

bool WeatherState::valid(std::string* why) const {
  auto bad = [&](const char* m) {
    if (why) *why = m;
    return false;
  };
  if (schemaVersion != kSchemaVersion) return bad("schema_version");
  if (has(rh) && (rh < 0.0 || rh > 100.0)) return bad("rh range");
  if (has(cloudCover) && (cloudCover < 0.0 || cloudCover > 1.0)) return bad("cloud_cover range");
  if (has(windDirDeg) && (windDirDeg < 0.0 || windDirDeg >= 360.0)) return bad("wind_dir_deg range");
  if (has(windFromHeading) && (windFromHeading < 0.0 || windFromHeading >= 360.0)) {
    return bad("wind_from_heading range");
  }
  if (has(windToHeading) && (windToHeading < 0.0 || windToHeading >= 360.0)) {
    return bad("wind_to_heading range");
  }
  if (has(windMps) && windMps < 0.0) return bad("wind_mps negative");
  if (has(windGustMps) && windGustMps < 0.0) return bad("wind_gust_mps negative");
  if (has(visibilityM) && visibilityM < 0.0) return bad("visibility_m negative");
  if (has(precipRateMmph) && precipRateMmph < 0.0) return bad("precip_rate_mmph negative");
  if (has(snowDepthCm) && snowDepthCm < 0.0) return bad("snow_depth_cm negative");
  if (has(snowfallRateCmph) && snowfallRateCmph < 0.0) return bad("snowfall_rate_cmph negative");
  if (has(pressureHpa) && (pressureHpa < 800.0 || pressureHpa > 1120.0)) return bad("pressure_hpa range");
  if (has(tempC) && (tempC < -90.0 || tempC > 60.0)) return bad("temp_c range");
  if (has(dewpointC) && has(tempC) && dewpointC > tempC + 0.6) return bad("dewpoint above temperature");
  if (has(staleAgeS) && staleAgeS < 0.0) return bad("stale_age_s negative");
  if (precipType == PrecipType::None && has(precipRateMmph) && precipRateMmph > 0.0) {
    return bad("precip rate without a precipitation type");
  }
  if (precipType != PrecipType::None && precipRateBasis == PrecipRateBasis::None) {
    return bad("precipitation without a rate basis");
  }
  if ((obscuration & ~static_cast<uint16_t>(kObscBR | kObscFG | kObscFU | kObscVA | kObscDU | kObscSA |
                                            kObscHZ | kObscPY | kObscPO | kObscSQ | kObscFC | kObscSS |
                                            kObscDS)) != 0) {
    return bad("unknown obscuration bit");
  }
  if (why) why->clear();
  return true;
}

// ---- numeric helpers ------------------------------------------------------------------------------

double compassToMath(double headingDeg) {
  const double v = std::fmod(90.0 - headingDeg, 360.0);
  return v < 0.0 ? v + 360.0 : v;
}

double mathToCompass(double mathDeg) { return compassToMath(mathDeg); }

double relativeHumidity(double tempC, double dewpointC) {
  const double a = 17.625, b = 243.04;
  const double rh = 100.0 * std::exp(a * dewpointC / (b + dewpointC)) / std::exp(a * tempC / (b + tempC));
  return clampD(rh, 0.0, 100.0);
}

double dewpointFromRh(double tempC, double rhPercent) {
  const double a = 17.625, b = 243.04;
  const double rh = clampD(rhPercent, 0.1, 100.0) / 100.0;
  const double g = std::log(rh) + a * tempC / (b + tempC);
  return b * g / (a - g);
}

double clampD(double x, double lo, double hi) { return x < lo ? lo : (x > hi ? hi : x); }

void setWind(WeatherState& s, double fromHeading) {
  if (std::isnan(fromHeading)) {
    s.windDirDeg = s.windFromHeading = s.windToHeading = WeatherState::kNaN();
    return;
  }
  double h = std::fmod(fromHeading, 360.0);
  if (h < 0.0) h += 360.0;
  s.windFromHeading = h;
  s.windToHeading = std::fmod(h + 180.0, 360.0);
  s.windDirDeg = compassToMath(h);
}

Result<double> parseIso8601(const char* text) {
  if (!text) return fail(ErrorCode::InvalidArgument, "weather: null ISO-8601 timestamp");
  const char* p = text;
  while (*p == ' ' || *p == '\t') ++p;
  int y = 0, mo = 0, d = 0, h = 0, mi = 0, sec = 0;
  if (!readInt(p, 4, y) || *p++ != '-') return fail(ErrorCode::ParseError, "weather: bad ISO-8601 date");
  if (!readInt(p, 2, mo) || *p++ != '-') return fail(ErrorCode::ParseError, "weather: bad ISO-8601 date");
  if (!readInt(p, 2, d)) return fail(ErrorCode::ParseError, "weather: bad ISO-8601 date");
  if (*p != 'T' && *p != ' ') return fail(ErrorCode::ParseError, "weather: ISO-8601 without a time part");
  ++p;
  if (!readInt(p, 2, h) || *p++ != ':') return fail(ErrorCode::ParseError, "weather: bad ISO-8601 time");
  if (!readInt(p, 2, mi)) return fail(ErrorCode::ParseError, "weather: bad ISO-8601 time");
  double frac = 0.0;
  if (*p == ':') {
    ++p;
    if (!readInt(p, 2, sec)) return fail(ErrorCode::ParseError, "weather: bad ISO-8601 seconds");
    if (*p == '.') {
      ++p;
      double scale = 0.1;
      if (*p < '0' || *p > '9') return fail(ErrorCode::ParseError, "weather: empty fractional seconds");
      while (*p >= '0' && *p <= '9') {
        frac += (*p - '0') * scale;
        scale *= 0.1;
        ++p;
      }
    }
  }
  int offset = 0;
  if (*p == 'Z' || *p == 'z') {
    ++p;
  } else if (*p == '+' || *p == '-') {
    const int sign = *p == '-' ? -1 : 1;
    ++p;
    int oh = 0, om = 0;
    if (!readInt(p, 2, oh)) return fail(ErrorCode::ParseError, "weather: bad ISO-8601 zone");
    if (*p == ':') ++p;
    if (*p != '\0') {
      if (!readInt(p, 2, om)) return fail(ErrorCode::ParseError, "weather: bad ISO-8601 zone");
    }
    offset = sign * (oh * 3600 + om * 60);
  }
  while (*p == ' ' || *p == '\t') ++p;
  if (*p != '\0') return fail(ErrorCode::ParseError, "weather: trailing characters in ISO-8601");
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || h > 24 || mi > 59 || sec > 60) {
    return fail(ErrorCode::ParseError, "weather: ISO-8601 field out of range");
  }
  const int64_t base = nytime::unixFromCivilUtc(y, mo, d, h, mi, sec);
  return static_cast<double>(base - offset) + frac;
}

std::string isoUtc(double unix_s) {
  if (std::isnan(unix_s)) return std::string();
  const nytime::DateTime t = nytime::civilFromUnix(std::floor(unix_s));
  char buf[32];
  const int n = std::snprintf(buf, sizeof buf, "%04d-%02d-%02dT%02d:%02d:%02dZ", t.year, t.month, t.day,
                              t.hour, t.minute, static_cast<int>(t.second));
  return n > 0 ? std::string(buf, static_cast<size_t>(n)) : std::string();
}

Result<double> parseIsoDuration(const char* text) {
  if (!text || *text != 'P') return fail(ErrorCode::ParseError, "weather: bad ISO-8601 duration");
  const char* p = text + 1;
  double total = 0.0;
  bool inTime = false;
  bool any = false;
  while (*p != '\0') {
    if (*p == 'T') {
      inTime = true;
      ++p;
      continue;
    }
    if (*p < '0' || *p > '9') return fail(ErrorCode::ParseError, "weather: bad ISO-8601 duration");
    double v = 0.0;
    while (*p >= '0' && *p <= '9') {
      v = v * 10.0 + (*p - '0');
      ++p;
    }
    switch (*p) {
      case 'D': total += v * 86400.0; break;
      case 'H':
        if (!inTime) return fail(ErrorCode::ParseError, "weather: H outside the time part");
        total += v * 3600.0;
        break;
      case 'M':
        if (!inTime) return fail(ErrorCode::ParseError, "weather: months are not supported");
        total += v * 60.0;
        break;
      case 'S':
        if (!inTime) return fail(ErrorCode::ParseError, "weather: S outside the time part");
        total += v;
        break;
      default: return fail(ErrorCode::ParseError, "weather: unknown ISO-8601 duration unit");
    }
    ++p;
    any = true;
  }
  if (!any) return fail(ErrorCode::ParseError, "weather: empty ISO-8601 duration");
  return total;
}

}  // namespace weather
}  // namespace nycsim
