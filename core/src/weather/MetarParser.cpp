#include "nycsim/weather/MetarParser.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include "nycsim/time/NyTime.h"

namespace nycsim {
namespace weather {
namespace metar {

namespace {

bool isDigit(char c) { return c >= '0' && c <= '9'; }
bool isUpper(char c) { return c >= 'A' && c <= 'Z'; }

bool allDigits(const std::string& s, size_t from, size_t count) {
  if (from + count > s.size()) return false;
  for (size_t i = 0; i < count; ++i) {
    if (!isDigit(s[from + i])) return false;
  }
  return true;
}

int toInt(const std::string& s, size_t from, size_t count) {
  int v = 0;
  for (size_t i = 0; i < count; ++i) v = v * 10 + (s[from + i] - '0');
  return v;
}

double roundTo(double v, int digits) {
  double f = 1.0;
  for (int i = 0; i < digits; ++i) f *= 10.0;
  return std::round(v * f) / f;
}

struct PhenEntry {
  const char* code;
  uint32_t bit;
};
constexpr PhenEntry kPhenTable[] = {
    {"DZ", kPhDZ}, {"RA", kPhRA}, {"SN", kPhSN}, {"SG", kPhSG}, {"IC", kPhIC}, {"PL", kPhPL},
    {"GR", kPhGR}, {"GS", kPhGS}, {"UP", kPhUP}, {"BR", kPhBR}, {"FG", kPhFG}, {"FU", kPhFU},
    {"VA", kPhVA}, {"DU", kPhDU}, {"SA", kPhSA}, {"HZ", kPhHZ}, {"PY", kPhPY}, {"PO", kPhPO},
    {"SQ", kPhSQ}, {"FC", kPhFC}, {"SS", kPhSS}, {"DS", kPhDS},
};
constexpr int kPhenCount = static_cast<int>(sizeof(kPhenTable) / sizeof(kPhenTable[0]));

uint32_t phenBit(const char* two) {
  for (int i = 0; i < kPhenCount; ++i) {
    if (kPhenTable[i].code[0] == two[0] && kPhenTable[i].code[1] == two[1]) return kPhenTable[i].bit;
  }
  return 0;
}

struct DescEntry {
  const char* code;
  Descriptor d;
};
constexpr DescEntry kDescTable[] = {{"MI", Descriptor::MI}, {"BC", Descriptor::BC},
                                    {"PR", Descriptor::PR}, {"DR", Descriptor::DR},
                                    {"BL", Descriptor::BL}, {"SH", Descriptor::SH},
                                    {"TS", Descriptor::TS}, {"FZ", Descriptor::FZ}};

Descriptor descriptorOf(const char* two) {
  for (const DescEntry& e : kDescTable) {
    if (e.code[0] == two[0] && e.code[1] == two[1]) return e.d;
  }
  return Descriptor::None;
}

/// DDHHMMZ
bool matchTime(const std::string& t, int& day, int& hour, int& minute) {
  if (t.size() != 7 || t[6] != 'Z' || !allDigits(t, 0, 6)) return false;
  day = toInt(t, 0, 2);
  hour = toInt(t, 2, 2);
  minute = toInt(t, 4, 2);
  return true;
}

/// (\d{3}|VRB|///)(\d{2,3}|//)(G\d{2,3})?(KT|MPS|KMH)
struct WindMatch {
  std::string dir;
  std::string speed;
  std::string gust;
  std::string unit;
};
bool matchWind(const std::string& t, WindMatch& m) {
  size_t i = 0;
  if (t.size() < 5) return false;
  if (t.compare(0, 3, "VRB") == 0 || t.compare(0, 3, "///") == 0) {
    m.dir = t.substr(0, 3);
    i = 3;
  } else if (allDigits(t, 0, 3)) {
    m.dir = t.substr(0, 3);
    i = 3;
  } else {
    return false;
  }
  if (t.compare(i, 2, "//") == 0) {
    m.speed = "//";
    i += 2;
  } else if (allDigits(t, i, 3)) {
    m.speed = t.substr(i, 3);
    i += 3;
  } else if (allDigits(t, i, 2)) {
    m.speed = t.substr(i, 2);
    i += 2;
  } else {
    return false;
  }
  m.gust.clear();
  if (i < t.size() && t[i] == 'G') {
    ++i;
    if (allDigits(t, i, 3)) {
      m.gust = t.substr(i, 3);
      i += 3;
    } else if (allDigits(t, i, 2)) {
      m.gust = t.substr(i, 2);
      i += 2;
    } else {
      return false;
    }
  }
  const std::string rest = t.substr(i);
  if (rest != "KT" && rest != "MPS" && rest != "KMH") return false;
  m.unit = rest;
  // A three-digit speed must not be a shortened two-digit speed followed by a unit letter; the
  // greedy order above already prefers three digits, matching the Python regex \d{2,3}.
  return true;
}

/// \d{3}V\d{3}
bool matchWindVar(const std::string& t, int& from, int& to) {
  if (t.size() != 7 || t[3] != 'V' || !allDigits(t, 0, 3) || !allDigits(t, 4, 3)) return false;
  from = toInt(t, 0, 3);
  to = toInt(t, 4, 3);
  return true;
}

/// ([MP])?(\d{1,2})?((\d)/(\d{1,2}))?SM  — at least the whole or the fraction must be present.
struct VisSm {
  char prefix = '\0';
  bool hasWhole = false;
  int whole = 0;
  bool hasFraction = false;
  int num = 0, den = 1;
};
bool matchVisSm(const std::string& t, VisSm& v) {
  if (t.size() < 3 || t.compare(t.size() - 2, 2, "SM") != 0) return false;
  size_t i = 0;
  const size_t end = t.size() - 2;
  v = VisSm();
  if (i < end && (t[i] == 'M' || t[i] == 'P')) {
    v.prefix = t[i];
    ++i;
  }
  // whole part: 1..2 digits not followed by '/'
  size_t j = i;
  while (j < end && isDigit(t[j])) ++j;
  const size_t digits = j - i;
  if (digits > 0 && (j == end || t[j] != '/')) {
    if (digits > 2) return false;
    v.hasWhole = true;
    v.whole = toInt(t, i, digits);
    i = j;
  }
  if (i < end) {
    // fraction: (\d)/(\d{1,2})
    if (!isDigit(t[i])) return false;
    v.num = t[i] - '0';
    ++i;
    if (i >= end || t[i] != '/') return false;
    ++i;
    size_t k = i;
    while (k < end && isDigit(t[k])) ++k;
    const size_t dd = k - i;
    if (dd < 1 || dd > 2) return false;
    v.den = toInt(t, i, dd);
    if (v.den == 0) return false;
    v.hasFraction = true;
    i = k;
  }
  if (i != end) return false;
  return v.hasWhole || v.hasFraction;
}

/// (\d{4})(NDV|N|NE|E|SE|S|SW|W|NW)?
bool matchVisM(const std::string& t, int& metres) {
  if (t.size() < 4 || !allDigits(t, 0, 4)) return false;
  const std::string suffix = t.substr(4);
  static const char* kDirs[] = {"", "NDV", "N", "NE", "E", "SE", "S", "SW", "W", "NW"};
  bool ok = false;
  for (const char* d : kDirs) {
    if (suffix == d) {
      ok = true;
      break;
    }
  }
  if (!ok) return false;
  metres = toInt(t, 0, 4);
  return true;
}

/// R\d{2}[LCR]?/[PM]?\d{4}(V[PM]?\d{4})?(FT)?[UDN]?
bool matchRvr(const std::string& t) {
  size_t i = 0;
  if (t.size() < 7 || t[0] != 'R') return false;
  i = 1;
  if (!allDigits(t, i, 2)) return false;
  i += 2;
  if (i < t.size() && (t[i] == 'L' || t[i] == 'C' || t[i] == 'R')) ++i;
  if (i >= t.size() || t[i] != '/') return false;
  ++i;
  if (i < t.size() && (t[i] == 'P' || t[i] == 'M')) ++i;
  if (!allDigits(t, i, 4)) return false;
  i += 4;
  if (i < t.size() && t[i] == 'V') {
    ++i;
    if (i < t.size() && (t[i] == 'P' || t[i] == 'M')) ++i;
    if (!allDigits(t, i, 4)) return false;
    i += 4;
  }
  if (t.compare(i, 2, "FT") == 0) i += 2;
  if (i < t.size() && (t[i] == 'U' || t[i] == 'D' || t[i] == 'N')) ++i;
  return i == t.size();
}

/// ([+-])?(VC)?(descriptor)?(phenomenon+)?
bool matchWx(const std::string& t, Intensity& intensity, Descriptor& desc, uint32_t& phen,
             bool& hasDescriptorOrPhen) {
  size_t i = 0;
  intensity = Intensity::Moderate;
  desc = Descriptor::None;
  phen = 0;
  hasDescriptorOrPhen = false;
  if (t.empty()) return false;
  if (t[0] == '+') {
    intensity = Intensity::Heavy;
    i = 1;
  } else if (t[0] == '-') {
    intensity = Intensity::Light;
    i = 1;
  }
  if (t.compare(i, 2, "VC") == 0) {
    intensity = Intensity::Vicinity;
    i += 2;
  }
  if (i + 2 <= t.size()) {
    const Descriptor d = descriptorOf(t.c_str() + i);
    if (d != Descriptor::None) {
      desc = d;
      i += 2;
      hasDescriptorOrPhen = true;
    }
  }
  while (i + 2 <= t.size()) {
    const uint32_t b = phenBit(t.c_str() + i);
    if (b == 0) return false;
    phen |= b;
    hasDescriptorOrPhen = true;
    i += 2;
  }
  if (i != t.size()) return false;
  return true;
}

/// (FEW|SCT|BKN|OVC|VV)(\d{3}|///)(CB|TCU|///)?
bool matchSky(const std::string& t, CloudLayer& layer) {
  size_t i = 0;
  if (t.compare(0, 3, "FEW") == 0) {
    layer.cover = Cover::FEW;
    i = 3;
  } else if (t.compare(0, 3, "SCT") == 0) {
    layer.cover = Cover::SCT;
    i = 3;
  } else if (t.compare(0, 3, "BKN") == 0) {
    layer.cover = Cover::BKN;
    i = 3;
  } else if (t.compare(0, 3, "OVC") == 0) {
    layer.cover = Cover::OVC;
    i = 3;
  } else if (t.compare(0, 2, "VV") == 0) {
    layer.cover = Cover::VV;
    i = 2;
  } else {
    return false;
  }
  if (t.compare(i, 3, "///") == 0) {
    layer.baseM = WeatherState::kNaN();
    i += 3;
  } else if (allDigits(t, i, 3)) {
    layer.baseM = roundTo(toInt(t, i, 3) * 100.0 * kFootM, 1);
    i += 3;
  } else {
    return false;
  }
  layer.cb = false;
  layer.tcu = false;
  const std::string suffix = t.substr(i);
  if (suffix.empty() || suffix == "///") return true;
  if (suffix == "CB") {
    layer.cb = true;
    return true;
  }
  if (suffix == "TCU") {
    layer.tcu = true;
    return true;
  }
  return false;
}

/// (M?\d{2})/(M?\d{2})?
bool matchTemp(const std::string& t, double& tempC, double& dewC, bool& hasDew) {
  size_t i = 0;
  double sign = 1.0;
  if (i < t.size() && t[i] == 'M') {
    sign = -1.0;
    ++i;
  }
  if (!allDigits(t, i, 2)) return false;
  tempC = sign * toInt(t, i, 2);
  i += 2;
  if (i >= t.size() || t[i] != '/') return false;
  ++i;
  if (i == t.size()) {
    hasDew = false;
    dewC = WeatherState::kNaN();
    return true;
  }
  double dsign = 1.0;
  if (t[i] == 'M') {
    dsign = -1.0;
    ++i;
  }
  if (!allDigits(t, i, 2)) return false;
  dewC = dsign * toInt(t, i, 2);
  i += 2;
  if (i != t.size()) return false;
  hasDew = true;
  return true;
}

bool isTrendStart(const std::string& t) {
  if (t == "NOSIG" || t == "TEMPO" || t == "BECMG" || t == "NSW" || t == "RMK") return true;
  if (t.size() >= 6 && t.compare(0, 2, "FM") == 0) {
    size_t n = 0;
    for (size_t i = 2; i < t.size(); ++i) {
      if (!isDigit(t[i])) return false;
      ++n;
    }
    return n >= 4 && n <= 6;
  }
  return false;
}

bool isStationId(const std::string& t) {
  if (t.size() != 4) return false;
  if (!isUpper(t[0])) return false;
  for (size_t i = 1; i < 4; ++i) {
    if (!isUpper(t[i]) && !isDigit(t[i])) return false;
  }
  return true;
}

std::vector<std::string> splitWhitespace(const std::string& s) {
  std::vector<std::string> out;
  size_t i = 0;
  while (i < s.size()) {
    while (i < s.size() && (s[i] == ' ' || s[i] == '\t')) ++i;
    const size_t start = i;
    while (i < s.size() && s[i] != ' ' && s[i] != '\t') ++i;
    if (i > start) out.push_back(s.substr(start, i - start));
  }
  return out;
}

/// "YYYY/MM/DD HH:MM" tgftp header line.
bool matchHeaderLine(const std::string& s, double& unixOut) {
  if (s.size() != 16 || s[4] != '/' || s[7] != '/' || s[10] != ' ' || s[13] != ':') return false;
  if (!allDigits(s, 0, 4) || !allDigits(s, 5, 2) || !allDigits(s, 8, 2) || !allDigits(s, 11, 2) ||
      !allDigits(s, 14, 2)) {
    return false;
  }
  unixOut = static_cast<double>(nytime::unixFromCivilUtc(toInt(s, 0, 4), toInt(s, 5, 2), toInt(s, 8, 2),
                                                         toInt(s, 11, 2), toInt(s, 14, 2), 0));
  return true;
}

void parseRemarks(MetarReport& rep) {
  const std::vector<std::string> toks = splitWhitespace(rep.remarks);
  for (size_t j = 0; j < toks.size(); ++j) {
    const std::string& t = toks[j];
    if (t == "$") {
      rep.maintenanceFlag = true;
      continue;
    }
    if (t.size() == 6 && t.compare(0, 3, "SLP") == 0 && allDigits(t, 3, 3)) {
      const double v = toInt(t, 3, 3) / 10.0;  // tenths of hPa, leading 9 or 10 dropped
      rep.seaLevelPressureHpa = v < 50.0 ? 1000.0 + v : 900.0 + v;
      continue;
    }
    if (t.size() == 9 && t[0] == 'T' && (t[1] == '0' || t[1] == '1') && allDigits(t, 2, 3) &&
        (t[5] == '0' || t[5] == '1') && allDigits(t, 6, 3)) {
      rep.tempC = (t[1] == '1' ? -1.0 : 1.0) * toInt(t, 2, 3) / 10.0;
      rep.dewpointC = (t[5] == '1' ? -1.0 : 1.0) * toInt(t, 6, 3) / 10.0;
      continue;
    }
    if (t.size() == 5 && t[0] == 'P' && allDigits(t, 1, 4)) {
      rep.precipLastHourMm = roundTo(toInt(t, 1, 4) * kHundredthInchMm, 3);
      continue;
    }
    if (t.size() == 5 && t.compare(0, 2, "4/") == 0 && allDigits(t, 2, 3)) {
      rep.snowDepthCm = roundTo(toInt(t, 2, 3) * kInchCm, 2);
      continue;
    }
    if (t.size() == 6 && t.compare(0, 3, "931") == 0 && allDigits(t, 3, 3)) {
      rep.snowfall6hCm = roundTo(toInt(t, 3, 3) / 10.0 * kInchCm, 2);
      continue;
    }
    if (t.size() == 6 && t.compare(0, 3, "933") == 0 && allDigits(t, 3, 3)) {
      rep.snowWaterEquivalentMm = roundTo(toInt(t, 3, 3) / 10.0 * 25.4, 2);
      continue;
    }
    if (t.size() == 5 && t[0] == '6' && allDigits(t, 1, 4)) {
      rep.precip36hMm = roundTo(toInt(t, 1, 4) * kHundredthInchMm, 3);
      continue;
    }
    if (t.size() == 5 && t[0] == '7' && allDigits(t, 1, 4)) {
      rep.precip24hMm = roundTo(toInt(t, 1, 4) * kHundredthInchMm, 3);
      continue;
    }
    if (t == "WND" && j >= 1 && toks[j - 1] == "PK" && j + 1 < toks.size()) {
      // (\d{3})(\d{2,3})/(\d{2})?(\d{2})
      const std::string& p = toks[j + 1];
      const size_t slash = p.find('/');
      if (slash == std::string::npos) continue;
      const size_t head = slash;
      const size_t tail = p.size() - slash - 1;
      if (head < 5 || head > 6 || (tail != 2 && tail != 4)) continue;
      if (!allDigits(p, 0, head)) continue;
      bool tailDigits = true;
      for (size_t k = slash + 1; k < p.size(); ++k) tailDigits = tailDigits && isDigit(p[k]);
      if (!tailDigits) continue;
      rep.peakWindDirDeg = toInt(p, 0, 3);
      rep.peakWindMps = roundTo(toInt(p, 3, head - 3) * kKtToMps, 3);
    }
  }
}

}  // namespace

const char* intensityCode(Intensity i) {
  switch (i) {
    case Intensity::Light: return "-";
    case Intensity::Moderate: return "";
    case Intensity::Heavy: return "+";
    case Intensity::Vicinity: return "VC";
  }
  return "";
}

int intensityRank(Intensity i) {
  switch (i) {
    case Intensity::Light: return 0;
    case Intensity::Moderate: return 1;
    case Intensity::Heavy: return 2;
    case Intensity::Vicinity: return 0;
  }
  return 0;
}

double coverFraction(Cover c) {
  switch (c) {
    case Cover::SKC:
    case Cover::CLR:
    case Cover::NSC:
    case Cover::NCD: return 0.0;
    case Cover::FEW: return 0.1875;
    case Cover::SCT: return 0.4375;
    case Cover::BKN: return 0.75;
    case Cover::OVC:
    case Cover::VV: return 1.0;
  }
  return 0.0;
}

double MetarReport::ceilingM() const {
  double best = WeatherState::kNaN();
  for (const CloudLayer& c : clouds) {
    if (c.cover != Cover::BKN && c.cover != Cover::OVC && c.cover != Cover::VV) continue;
    if (std::isnan(c.baseM)) continue;
    if (std::isnan(best) || c.baseM < best) best = c.baseM;
  }
  return best;
}

bool MetarReport::thunder() const {
  for (const WeatherGroup& g : weather) {
    if (g.thunderstorm()) return true;
  }
  return false;
}

Result<double> resolveObservationTime(int32_t day, int32_t hour, int32_t minute, double referenceUnix) {
  if (std::isnan(referenceUnix)) {
    return fail(ErrorCode::InvalidArgument, "METAR: no reference time to place the day/hour group");
  }
  const nytime::DateTime ref = nytime::civilFromUnix(referenceUnix);
  int32_t y = ref.year;
  int32_t m = ref.month;
  for (int i = 0; i < 3; ++i) {
    if (day >= 1 && day <= nytime::daysInMonth(y, m)) {
      const double cand = static_cast<double>(nytime::unixFromCivilUtc(y, m, day, hour, minute, 0));
      if (cand <= referenceUnix + 2.0 * 3600.0) return cand;
    }
    --m;
    if (m == 0) {
      m = 12;
      --y;
    }
  }
  return fail(ErrorCode::ParseError, "METAR: cannot place the day-of-month relative to the reference time",
              day);
}

Result<MetarReport> parseMetar(const char* text, double referenceUnix) {
  if (!text) return fail(ErrorCode::InvalidArgument, "METAR: null text");
  // Split into non-empty trimmed lines.
  std::vector<std::string> lines;
  {
    std::string cur;
    for (const char* p = text;; ++p) {
      if (*p == '\n' || *p == '\r' || *p == '\0') {
        size_t a = 0, b = cur.size();
        while (a < b && (cur[a] == ' ' || cur[a] == '\t')) ++a;
        while (b > a && (cur[b - 1] == ' ' || cur[b - 1] == '\t')) --b;
        if (b > a) lines.push_back(cur.substr(a, b - a));
        cur.clear();
        if (*p == '\0') break;
      } else {
        cur.push_back(*p);
      }
    }
  }
  if (lines.empty()) return fail(ErrorCode::ParseError, "METAR: empty text");
  double headerTime = WeatherState::kNaN();
  if (matchHeaderLine(lines[0], headerTime)) {
    lines.erase(lines.begin());
    if (lines.empty()) return fail(ErrorCode::ParseError, "METAR: header without a report body");
  }
  std::string raw;
  for (size_t i = 0; i < lines.size(); ++i) {
    if (i) raw.push_back(' ');
    raw += lines[i];
  }
  while (!raw.empty() && (raw.back() == '=' || raw.back() == ' ')) raw.pop_back();

  MetarReport rep;
  rep.raw = raw;
  std::string body = raw;
  const size_t rmk = raw.find(" RMK ");
  if (rmk != std::string::npos) {
    body = raw.substr(0, rmk);
    rep.remarks = raw.substr(rmk + 5);
  } else if (raw.size() >= 4 && raw.compare(raw.size() - 4, 4, " RMK") == 0) {
    body = raw.substr(0, raw.size() - 4);
  }

  const std::vector<std::string> toks = splitWhitespace(body);
  size_t i = 0;
  if (i < toks.size() && (toks[i] == "METAR" || toks[i] == "SPECI")) {
    rep.reportType = toks[i];
    ++i;
  }
  if (i < toks.size() && toks[i] == "COR") {
    rep.corrected = true;
    ++i;
  }
  if (i >= toks.size() || !isStationId(toks[i])) {
    return fail(ErrorCode::ParseError, "METAR: missing station identifier");
  }
  rep.station = toks[i];
  ++i;
  if (i < toks.size()) {
    int day = 0, hour = 0, minute = 0;
    if (matchTime(toks[i], day, hour, minute)) {
      if (!(day >= 1 && day <= 31 && hour <= 24 && minute <= 59)) {
        return fail(ErrorCode::ParseError, "METAR: invalid time group");
      }
      rep.day = day;
      rep.hour = hour;
      rep.minute = minute;
      ++i;
      const double ref = !std::isnan(headerTime) ? headerTime : referenceUnix;
      if (!std::isnan(ref)) {
        const Result<double> t = resolveObservationTime(day, hour % 24, minute, ref);
        if (!t) return t.error();
        rep.observationTimeUnix = t.value();
      }
    }
  }
  while (i < toks.size() && (toks[i] == "AUTO" || toks[i] == "COR" || toks[i] == "NIL" ||
                             toks[i] == "RTD" || toks[i] == "CCA" || toks[i] == "CCB" ||
                             toks[i] == "CCC")) {
    if (toks[i] == "AUTO") {
      rep.automatic = true;
    } else if (toks[i] == "NIL") {
      rep.nil = true;
    } else {
      rep.corrected = true;
    }
    ++i;
  }

  bool seenTemp = false;
  while (i < toks.size()) {
    const std::string& tok = toks[i];
    if (isTrendStart(tok)) {
      std::string trend;
      for (size_t k = i; k < toks.size(); ++k) {
        if (k > i) trend.push_back(' ');
        trend += toks[k];
      }
      rep.trend = trend;
      break;
    }
    if (tok == "$") {
      rep.maintenanceFlag = true;
      ++i;
      continue;
    }
    WindMatch wm;
    if (std::isnan(rep.windSpeedMps) && !seenTemp && matchWind(tok, wm)) {
      const double f = wm.unit == "KT" ? kKtToMps : (wm.unit == "MPS" ? 1.0 : kKmhToMps);
      if (wm.speed != "//") {
        rep.windSpeedMps = roundTo(toInt(wm.speed, 0, wm.speed.size()) * f, 3);
      }
      if (!wm.gust.empty()) rep.windGustMps = roundTo(toInt(wm.gust, 0, wm.gust.size()) * f, 3);
      if (wm.dir == "VRB") {
        rep.windVariable = true;
      } else if (wm.dir != "///") {
        rep.windDirDeg = toInt(wm.dir, 0, 3);
      }
      if (rep.windSpeedMps == 0.0 && (wm.dir == "000" || wm.dir == "VRB")) {
        rep.windCalm = true;
        rep.windDirDeg = WeatherState::kNaN();
      }
      ++i;
      continue;
    }
    int vFrom = 0, vTo = 0;
    if (!std::isnan(rep.windSpeedMps) && std::isnan(rep.windDirFromDeg) &&
        matchWindVar(tok, vFrom, vTo)) {
      rep.windDirFromDeg = vFrom;
      rep.windDirToDeg = vTo;
      ++i;
      continue;
    }
    if (tok == "CAVOK") {
      rep.cavok = true;
      rep.visibilityM = kVisUnlimitedM;
      rep.visibilityGreaterThan = true;
      if (!rep.hasSkyClearCode) {
        rep.hasSkyClearCode = true;
        rep.skyClearCode = Cover::NSC;
      }
      ++i;
      continue;
    }
    if (std::isnan(rep.visibilityM) && !seenTemp) {
      // "1 1/2SM" spelled as two tokens.
      bool wholeToken = tok.size() >= 1 && tok.size() <= 2;
      for (char c : tok) wholeToken = wholeToken && isDigit(c);
      if (wholeToken && i + 1 < toks.size()) {
        VisSm frac;
        if (matchVisSm(toks[i + 1], frac) && frac.hasFraction && !frac.hasWhole &&
            frac.prefix == '\0') {
          const double v = toInt(tok, 0, tok.size()) + static_cast<double>(frac.num) / frac.den;
          rep.visibilityM = roundTo(v * kStatuteMileM, 1);
          i += 2;
          continue;
        }
      }
      VisSm vs;
      if (matchVisSm(tok, vs)) {
        const double v = (vs.hasWhole ? vs.whole : 0) +
                         (vs.hasFraction ? static_cast<double>(vs.num) / vs.den : 0.0);
        rep.visibilityM = roundTo(v * kStatuteMileM, 1);
        rep.visibilityLessThan = vs.prefix == 'M';
        rep.visibilityGreaterThan = vs.prefix == 'P' || v >= 10.0;
        ++i;
        continue;
      }
      int metres = 0;
      const bool mm = matchVisM(tok, metres);
      const bool afterTimeGroup = [&]() {
        if (i < 2 || i - 1 >= toks.size()) return false;
        int a = 0, b = 0, c = 0;
        return matchTime(toks[i - 1], a, b, c);
      }();
      if ((mm && !std::isnan(rep.windSpeedMps)) || (mm && afterTimeGroup)) {
        if (metres == 9999) {
          rep.visibilityM = kVisUnlimitedM;
          rep.visibilityGreaterThan = true;
        } else if (metres == 0) {
          rep.visibilityLessThan = true;
          rep.visibilityM = 50.0;  // "0000" means < 50 m
        } else {
          rep.visibilityM = metres;
        }
        ++i;
        continue;
      }
    }
    if (matchRvr(tok)) {
      rep.rvr.push_back(tok);
      ++i;
      continue;
    }
    if (!seenTemp && tok != "SKC" && tok != "CLR" && tok != "NSC" && tok != "NCD") {
      Intensity intensity = Intensity::Moderate;
      Descriptor desc = Descriptor::None;
      uint32_t phen = 0;
      bool any = false;
      if (matchWx(tok, intensity, desc, phen, any) && any) {
        WeatherGroup g;
        g.raw = tok;
        g.intensity = intensity;
        g.descriptor = desc;
        g.phenomena = phen;
        rep.weather.push_back(g);
        ++i;
        continue;
      }
    }
    if (tok == "SKC" || tok == "CLR" || tok == "NSC" || tok == "NCD") {
      rep.hasSkyClearCode = true;
      rep.skyClearCode = tok == "SKC" ? Cover::SKC
                                      : (tok == "CLR" ? Cover::CLR
                                                      : (tok == "NSC" ? Cover::NSC : Cover::NCD));
      ++i;
      continue;
    }
    CloudLayer layer;
    if (matchSky(tok, layer)) {
      if (layer.cover == Cover::VV) rep.verticalVisibilityM = layer.baseM;
      rep.clouds.push_back(layer);
      ++i;
      continue;
    }
    double tC = 0.0, dC = 0.0;
    bool hasDew = false;
    if (!seenTemp && matchTemp(tok, tC, dC, hasDew)) {
      rep.tempC = tC;
      rep.dewpointC = hasDew ? dC : WeatherState::kNaN();
      seenTemp = true;
      ++i;
      continue;
    }
    if (tok.size() == 5 && tok[0] == 'A' && allDigits(tok, 1, 4)) {
      rep.altimeterHpa = roundTo(toInt(tok, 1, 4) / 100.0 * kInHgToHpa, 1);
      ++i;
      continue;
    }
    if (tok.size() == 5 && tok[0] == 'Q' && allDigits(tok, 1, 4)) {
      rep.altimeterHpa = toInt(tok, 1, 4);
      ++i;
      continue;
    }
    rep.unparsed.push_back(tok);
    ++i;
  }
  parseRemarks(rep);
  return rep;
}

std::vector<std::string> splitReports(const char* text) {
  std::vector<std::string> out;
  if (!text) return out;
  std::vector<std::string> cur;
  std::string line;
  for (const char* p = text;; ++p) {
    if (*p == '\n' || *p == '\r' || *p == '\0') {
      size_t a = 0, b = line.size();
      while (a < b && (line[a] == ' ' || line[a] == '\t')) ++a;
      while (b > a && (line[b - 1] == ' ' || line[b - 1] == '\t')) --b;
      const std::string s = b > a ? line.substr(a, b - a) : std::string();
      line.clear();
      if (!s.empty()) {
        double dummy = 0.0;
        if (matchHeaderLine(s, dummy)) {
          if (!cur.empty()) {
            std::string joined;
            for (size_t i = 0; i < cur.size(); ++i) {
              if (i) joined.push_back('\n');
              joined += cur[i];
            }
            out.push_back(joined);
          }
          cur.clear();
        }
        cur.push_back(s);
      }
      if (*p == '\0') break;
    } else {
      line.push_back(*p);
    }
  }
  if (!cur.empty()) {
    std::string joined;
    for (size_t i = 0; i < cur.size(); ++i) {
      if (i) joined.push_back('\n');
      joined += cur[i];
    }
    out.push_back(joined);
  }
  return out;
}

// ---- weather-group semantics ----------------------------------------------------------------------

double intensityRateMmph(PrecipType type, Intensity intensity) {
  const int k = intensityRank(intensity);  // light 0, moderate 1, heavy 2 (vicinity -> light)
  switch (type) {
    case PrecipType::Rain: {
      const double v[3] = {1.0, 4.0, 10.0};
      return v[k];
    }
    case PrecipType::Drizzle: {
      const double v[3] = {0.2, 0.5, 1.0};
      return v[k];
    }
    case PrecipType::Snow: {
      const double v[3] = {0.5, 1.5, 3.0};
      return v[k];
    }
    case PrecipType::Sleet: {
      const double v[3] = {1.0, 3.0, 6.0};
      return v[k];
    }
    case PrecipType::FreezingRain: {
      const double v[3] = {0.5, 2.0, 4.0};
      return v[k];
    }
    case PrecipType::None: return 0.0;
  }
  return 0.0;
}

void classifyPrecipitation(const std::vector<WeatherGroup>& groups, double tempC, PrecipType& type,
                           Intensity& intensity) {
  // Mirrors weather.py classify_precipitation: the initial best is (none, moderate); a strictly
  // higher-ranked kind wins, an equal kind wins on the higher intensity class.
  type = PrecipType::None;
  intensity = Intensity::Moderate;
  for (const WeatherGroup& g : groups) {
    if (!g.precipitating()) continue;
    const uint32_t ph = g.phenomena;
    PrecipType kind;
    if (g.descriptor == Descriptor::FZ && (ph & (kPhRA | kPhDZ)) != 0) {
      kind = PrecipType::FreezingRain;
    } else if ((ph & (kPhPL | kPhGS | kPhGR)) != 0 ||
               ((ph & kPhSN) != 0 && (ph & (kPhRA | kPhDZ)) != 0)) {
      kind = PrecipType::Sleet;
    } else if ((ph & (kPhSN | kPhSG | kPhIC)) != 0) {
      kind = PrecipType::Snow;
    } else if ((ph & kPhRA) != 0) {
      kind = PrecipType::Rain;
    } else if ((ph & kPhUP) != 0) {
      kind = (std::isnan(tempC) || tempC > 1.0) ? PrecipType::Rain : PrecipType::Snow;
    } else if ((ph & kPhDZ) != 0) {
      kind = PrecipType::Drizzle;
    } else {
      continue;
    }
    if (precipTypeRank(kind) > precipTypeRank(type) ||
        (kind == type && intensityRank(g.intensity) > intensityRank(intensity))) {
      type = kind;
      intensity = g.intensity;
    }
  }
}

void precipitationRateMmph(const std::vector<WeatherGroup>& groups, double precipLastHourMm,
                           double tempC, double& rateMmph, PrecipRateBasis& basis) {
  PrecipType type = PrecipType::None;
  Intensity intensity = Intensity::Moderate;
  classifyPrecipitation(groups, tempC, type, intensity);
  if (type == PrecipType::None) {
    rateMmph = 0.0;
    basis = PrecipRateBasis::None;
    return;
  }
  if (!std::isnan(precipLastHourMm)) {
    if (precipLastHourMm > 0.0) {
      rateMmph = roundTo(precipLastHourMm, 3);
      basis = PrecipRateBasis::Measured;
      return;
    }
    rateMmph = kTraceRateMmph;
    basis = PrecipRateBasis::Trace;
    return;
  }
  double rate = intensityRateMmph(type, intensity);
  for (const WeatherGroup& g : groups) {
    if (g.thunderstorm() && g.precipitating()) {
      rate *= kThunderstormRateFactor;
      break;
    }
  }
  rateMmph = rate;
  basis = PrecipRateBasis::Class;
}

uint16_t obscurationBits(const std::vector<WeatherGroup>& groups) {
  uint16_t bits = 0;
  for (const WeatherGroup& g : groups) {
    if (g.intensity == Intensity::Vicinity) continue;
    const uint32_t ph = g.phenomena & (kObscurationMask | kOtherMask);
    if (ph & kPhBR) bits |= kObscBR;
    if (ph & kPhFG) bits |= kObscFG;
    if (ph & kPhFU) bits |= kObscFU;
    if (ph & kPhVA) bits |= kObscVA;
    if (ph & kPhDU) bits |= kObscDU;
    if (ph & kPhSA) bits |= kObscSA;
    if (ph & kPhHZ) bits |= kObscHZ;
    if (ph & kPhPY) bits |= kObscPY;
    if (ph & kPhPO) bits |= kObscPO;
    if (ph & kPhSQ) bits |= kObscSQ;
    if (ph & kPhFC) bits |= kObscFC;
    if (ph & kPhSS) bits |= kObscSS;
    if (ph & kPhDS) bits |= kObscDS;
  }
  return bits;
}

bool thunderPresent(const std::vector<WeatherGroup>& groups) {
  for (const WeatherGroup& g : groups) {
    if (g.descriptor == Descriptor::TS) return true;
  }
  return false;
}

double cloudCoverFraction(const std::vector<CloudLayer>& layers, bool hasSkyClearCode) {
  if (!layers.empty()) {
    double best = 0.0;
    for (const CloudLayer& c : layers) best = std::fmax(best, coverFraction(c.cover));
    return best;
  }
  if (hasSkyClearCode) return 0.0;
  return WeatherState::kNaN();
}

Result<WeatherState> weatherStateFromMetar(const MetarReport& rep, double nowUnix,
                                           double observedAtUnix) {
  const double tObs = !std::isnan(observedAtUnix) ? observedAtUnix : rep.observationTimeUnix;
  if (std::isnan(tObs)) {
    return fail(ErrorCode::ParseError, "METAR: report without a resolvable observation time");
  }
  if (nowUnix - tObs > kMaxObservationAgeS) {
    return fail(ErrorCode::StateError, "METAR: observation too old",
                static_cast<int64_t>(nowUnix - tObs));
  }
  if (std::isnan(rep.tempC) || rep.nil) {
    return fail(ErrorCode::ParseError, "METAR: report without a temperature");
  }
  WeatherState s;
  s.source = Source::Metar;
  s.observedAtUnix = tObs;
  s.station = rep.station;
  s.tempC = rep.tempC;
  s.dewpointC = rep.dewpointC;
  s.rh = std::isnan(rep.dewpointC) ? WeatherState::kNaN() : relativeHumidity(rep.tempC, rep.dewpointC);
  s.windMps = rep.windSpeedMps;
  s.windGustMps = rep.windGustMps;
  setWind(s, (rep.windVariable || rep.windCalm) ? WeatherState::kNaN() : rep.windDirDeg);
  s.visibilityM = rep.visibilityM;
  s.pressureHpa = !std::isnan(rep.seaLevelPressureHpa) ? rep.seaLevelPressureHpa : rep.altimeterHpa;
  PrecipType type = PrecipType::None;
  Intensity intensity = Intensity::Moderate;
  classifyPrecipitation(rep.weather, rep.tempC, type, intensity);
  s.precipType = type;
  precipitationRateMmph(rep.weather, rep.precipLastHourMm, rep.tempC, s.precipRateMmph,
                        s.precipRateBasis);
  s.thunder = thunderPresent(rep.weather);
  s.obscuration = obscurationBits(rep.weather);
  s.cloudCover = cloudCoverFraction(rep.clouds, rep.hasSkyClearCode);
  if (!std::isnan(rep.snowDepthCm)) {
    s.snowDepthCm = rep.snowDepthCm;
    s.snowDepthSource = SnowDepthSource::Observed;
  }
  s.rawText = rep.raw;
  return s;
}

}  // namespace metar
}  // namespace weather
}  // namespace nycsim
