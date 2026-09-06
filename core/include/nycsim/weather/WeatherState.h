// nycsim/weather/WeatherState.h — the live weather record (DATA_CONTRACTS §12 `weather.json` plus
// the §12.1 extension) and the small numeric helpers shared by every provider parser.
//
// C++ port of the `WeatherObservation` dataclass and the helper functions of
// services/nycsim_live/weather.py. Field names, units, formulas and constants are identical; the
// test suite parses the same fixtures through both and compares number for number.
//
// Missing values are NaN (not 0): a value is either measured, derived from measured values by a
// documented formula, or unknown. Nothing here invents weather.
#pragma once

#include <cstdint>
#include <string>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace weather {

inline constexpr int32_t kSchemaVersion = 1;
/// Observations older than this are treated as a provider failure (weather.py MAX_OBSERVATION_AGE_S).
inline constexpr double kMaxObservationAgeS = 2.5 * 3600.0;
/// Observations younger than this are used as-is (no forecast-anchored blend).
inline constexpr double kBlendMinAgeS = 10.0 * 60.0;
inline constexpr double kPollIntervalS = 60.0;
inline constexpr double kCentralParkLat = 40.7831;
inline constexpr double kCentralParkLon = -73.9712;
inline constexpr double kKmhToMps = 1.0 / 3.6;

enum class PrecipType : uint8_t { None = 0, Rain, Snow, Sleet, FreezingRain, Drizzle };
NYCSIM_API const char* precipTypeName(PrecipType t);   ///< contract spelling: "freezing_rain", ...
NYCSIM_API bool precipTypeFromName(const char* name, PrecipType& out);
/// Ordering used to pick the governing type when several groups are reported (weather.py `rank`).
NYCSIM_API int precipTypeRank(PrecipType t);

enum class Source : uint8_t { Nws = 0, OpenMeteo, Metar, Stale };
NYCSIM_API const char* sourceName(Source s);           ///< "nws" | "open_meteo" | "metar" | "stale"
NYCSIM_API bool sourceFromName(const char* name, Source& out);

enum class SnowDepthSource : uint8_t { None = 0, Observed, Model };
NYCSIM_API const char* snowDepthSourceName(SnowDepthSource s);

enum class PrecipRateBasis : uint8_t { None = 0, Measured, Class, Trace, Model };
NYCSIM_API const char* precipRateBasisName(PrecipRateBasis b);

/// Obscuration / "other" phenomena present at the station, as a bit set. The names are the METAR
/// codes the contract's `obscuration` list carries.
enum ObscurationBit : uint16_t {
  kObscNone = 0,
  kObscBR = 1u << 0,   ///< mist
  kObscFG = 1u << 1,   ///< fog
  kObscFU = 1u << 2,   ///< smoke
  kObscVA = 1u << 3,   ///< volcanic ash
  kObscDU = 1u << 4,   ///< widespread dust
  kObscSA = 1u << 5,   ///< sand
  kObscHZ = 1u << 6,   ///< haze
  kObscPY = 1u << 7,   ///< spray
  kObscPO = 1u << 8,   ///< dust/sand whirls
  kObscSQ = 1u << 9,   ///< squalls
  kObscFC = 1u << 10,  ///< funnel cloud
  kObscSS = 1u << 11,  ///< sandstorm
  kObscDS = 1u << 12,  ///< duststorm
};
/// Two-letter code for a single bit ("" for a non-single bit).
NYCSIM_API const char* obscurationCode(uint16_t singleBit);
/// Bit for a two-letter code, 0 if unknown.
NYCSIM_API uint16_t obscurationBit(const char* code);
/// Sorted, comma-free list of codes, e.g. "BR FG". Empty when no bit is set.
NYCSIM_API std::string obscurationList(uint16_t bits);

/// DATA_CONTRACTS §12 `weather.json` (through `stale_age_s`) plus the §12.1 extension fields.
struct WeatherState {
  int32_t schemaVersion = kSchemaVersion;
  double observedAtUnix = kNaN();   ///< ISO-8601 UTC in JSON
  std::string station;
  Source source = Source::Stale;
  double tempC = kNaN();
  double dewpointC = kNaN();
  double rh = kNaN();               ///< percent 0..100
  double windMps = kNaN();
  double windGustMps = kNaN();
  double windDirDeg = kNaN();       ///< mathematical (0 = east, ccw), direction the wind blows FROM
  PrecipType precipType = PrecipType::None;
  double precipRateMmph = kNaN();   ///< liquid equivalent
  double cloudCover = kNaN();       ///< 0..1
  double visibilityM = kNaN();
  double pressureHpa = kNaN();      ///< sea level
  double snowDepthCm = kNaN();
  bool thunder = false;
  double fetchedAtUnix = kNaN();
  double staleAgeS = kNaN();
  // ---- §12.1 extension
  double windFromHeading = kNaN();  ///< compass, meteorological "from"
  double windToHeading = kNaN();    ///< compass, direction of air motion
  SnowDepthSource snowDepthSource = SnowDepthSource::None;
  double snowfallRateCmph = kNaN();
  PrecipRateBasis precipRateBasis = PrecipRateBasis::None;
  uint16_t obscuration = kObscNone;
  bool interpolated = false;
  std::string rawText;

  static double kNaN();
  static bool has(double v);

  /// True when every contract invariant holds (ranges, enum validity, consistency).
  NYCSIM_API bool valid(std::string* why = nullptr) const;
};

// ---- numeric helpers (ported 1:1 from weather.py) -------------------------------------------------

/// Compass (0 = N, clockwise) -> mathematical (0 = E, counter-clockwise), degrees in [0, 360).
NYCSIM_API double compassToMath(double headingDeg);
NYCSIM_API double mathToCompass(double mathDeg);
/// August-Roche-Magnus (a = 17.625, b = 243.04 C); percent, clamped 0..100.
NYCSIM_API double relativeHumidity(double tempC, double dewpointC);
NYCSIM_API double dewpointFromRh(double tempC, double rhPercent);
NYCSIM_API double clampD(double x, double lo, double hi);
/// Sets windDirDeg / windFromHeading / windToHeading from a compass "from" heading (NaN clears all).
NYCSIM_API void setWind(WeatherState& s, double fromHeading);

/// ISO-8601 -> POSIX seconds. Accepts "Z", +/-hh:mm and +/-hhmm offsets, fractional seconds and a
/// missing zone (taken as UTC, as Open-Meteo emits). Fails on anything else.
NYCSIM_API Result<double> parseIso8601(const char* text);
/// POSIX seconds -> "YYYY-MM-DDTHH:MM:SSZ".
NYCSIM_API std::string isoUtc(double unix_s);
/// ISO-8601 duration "P[n]DT[n]H[n]M[n]S" -> seconds (NWS gridpoint validTime).
NYCSIM_API Result<double> parseIsoDuration(const char* text);

}  // namespace weather
}  // namespace nycsim
