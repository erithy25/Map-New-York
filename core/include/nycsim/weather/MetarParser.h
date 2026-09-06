// nycsim/weather/MetarParser.h — METAR / SPECI decoder (FMH-1 chapter 12, ICAO Annex 3).
//
// C++ port of services/nycsim_live/metar.py. Handles the body groups: report type, station,
// day/time, AUTO/COR/NIL, wind (KT/MPS/KMH, VRB, gusts, direction variation), visibility (statute
// miles including mixed fractions and M/P prefixes, metres with a direction, CAVOK), RVR,
// present weather (intensity/vicinity, descriptors MI BC PR DR BL SH TS FZ, precipitation
// DZ RA SN SG IC PL GR GS UP, obscurations BR FG FU VA DU SA HZ PY, other PO SQ FC SS DS),
// sky (SKC CLR NSC NCD FEW SCT BKN OVC VV with CB/TCU), temperature/dew point, altimeter (A/Q) and
// the remarks the simulation uses: SLP, T-group, P-group, 4/sss snow depth, 931/933 snow groups,
// 6/7 precipitation groups and PK WND. Trend groups (NOSIG/TEMPO/BECMG/FM) terminate the body.
//
// Units are SI at parse time: m/s, metres, degrees Celsius, hPa, mm, cm. No regular expressions,
// no exceptions, no allocation beyond the report's own vectors.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"
#include "nycsim/weather/WeatherState.h"

namespace nycsim {
namespace weather {
namespace metar {

inline constexpr double kKtToMps = 0.514444;  ///< 1852 m / 3600 s, rounded as in FMH-1
inline constexpr double kStatuteMileM = 1609.344;
inline constexpr double kFootM = 0.3048;
inline constexpr double kInHgToHpa = 33.86389;
inline constexpr double kHundredthInchMm = 0.254;
inline constexpr double kInchCm = 2.54;
/// "10SM" / 9999 / CAVOK as reported by ASOS: at least 10 statute miles.
inline constexpr double kVisUnlimitedM = 16093.44;

/// Precipitation phenomena, obscurations and "other" as a bit set (a group may carry several).
enum PhenomenonBit : uint32_t {
  kPhDZ = 1u << 0,  kPhRA = 1u << 1,  kPhSN = 1u << 2,  kPhSG = 1u << 3,  kPhIC = 1u << 4,
  kPhPL = 1u << 5,  kPhGR = 1u << 6,  kPhGS = 1u << 7,  kPhUP = 1u << 8,
  kPhBR = 1u << 9,  kPhFG = 1u << 10, kPhFU = 1u << 11, kPhVA = 1u << 12, kPhDU = 1u << 13,
  kPhSA = 1u << 14, kPhHZ = 1u << 15, kPhPY = 1u << 16,
  kPhPO = 1u << 17, kPhSQ = 1u << 18, kPhFC = 1u << 19, kPhSS = 1u << 20, kPhDS = 1u << 21,
};
inline constexpr uint32_t kPrecipitationMask =
    kPhDZ | kPhRA | kPhSN | kPhSG | kPhIC | kPhPL | kPhGR | kPhGS | kPhUP;
inline constexpr uint32_t kObscurationMask =
    kPhBR | kPhFG | kPhFU | kPhVA | kPhDU | kPhSA | kPhHZ | kPhPY;
inline constexpr uint32_t kOtherMask = kPhPO | kPhSQ | kPhFC | kPhSS | kPhDS;

enum class Descriptor : uint8_t { None = 0, MI, BC, PR, DR, BL, SH, TS, FZ };
/// "-" light, "" moderate, "+" heavy, "VC" in the vicinity.
enum class Intensity : uint8_t { Light = 0, Moderate, Heavy, Vicinity };
NYCSIM_API const char* intensityCode(Intensity i);
NYCSIM_API int intensityRank(Intensity i);  ///< light 0, moderate 1, heavy 2, vicinity 0

struct WeatherGroup {
  std::string raw;
  Intensity intensity = Intensity::Moderate;
  Descriptor descriptor = Descriptor::None;
  uint32_t phenomena = 0;

  bool precipitating() const {
    return intensity != Intensity::Vicinity && (phenomena & kPrecipitationMask) != 0;
  }
  bool thunderstorm() const { return descriptor == Descriptor::TS; }
};

enum class Cover : uint8_t { SKC = 0, CLR, NSC, NCD, FEW, SCT, BKN, OVC, VV };
NYCSIM_API double coverFraction(Cover c);  ///< okta midpoints: FEW .1875 SCT .4375 BKN .75 OVC/VV 1

struct CloudLayer {
  Cover cover = Cover::FEW;
  double baseM = WeatherState::kNaN();  ///< NaN when reported as ///
  bool cb = false;
  bool tcu = false;
};

struct MetarReport {
  std::string raw;
  std::string reportType = "METAR";
  std::string station;
  int32_t day = -1, hour = -1, minute = -1;
  double observationTimeUnix = WeatherState::kNaN();
  bool automatic = false;
  bool corrected = false;
  bool nil = false;
  double windDirDeg = WeatherState::kNaN();
  bool windVariable = false;
  bool windCalm = false;
  double windSpeedMps = WeatherState::kNaN();
  double windGustMps = WeatherState::kNaN();
  double windDirFromDeg = WeatherState::kNaN();
  double windDirToDeg = WeatherState::kNaN();
  double visibilityM = WeatherState::kNaN();
  bool visibilityLessThan = false;
  bool visibilityGreaterThan = false;
  bool cavok = false;
  std::vector<std::string> rvr;
  std::vector<WeatherGroup> weather;
  std::vector<CloudLayer> clouds;
  bool hasSkyClearCode = false;
  Cover skyClearCode = Cover::CLR;
  double verticalVisibilityM = WeatherState::kNaN();
  double tempC = WeatherState::kNaN();
  double dewpointC = WeatherState::kNaN();
  double altimeterHpa = WeatherState::kNaN();
  double seaLevelPressureHpa = WeatherState::kNaN();
  double precipLastHourMm = WeatherState::kNaN();  ///< P group (0.0 = trace)
  double precip36hMm = WeatherState::kNaN();
  double precip24hMm = WeatherState::kNaN();
  double snowDepthCm = WeatherState::kNaN();       ///< 4/sss
  double snowfall6hCm = WeatherState::kNaN();      ///< 931sss
  double snowWaterEquivalentMm = WeatherState::kNaN();  ///< 933sss
  double peakWindDirDeg = WeatherState::kNaN();
  double peakWindMps = WeatherState::kNaN();
  std::string remarks;
  std::string trend;
  std::vector<std::string> unparsed;
  bool maintenanceFlag = false;

  /// Lowest BKN/OVC/VV base, NaN when the sky is clear or not reported.
  double ceilingM() const;
  bool thunder() const;
};

/// Most recent UTC instant with the given day-of-month/hour/minute at or before `referenceUnix`
/// (+ 2 h slack for reports time-stamped slightly ahead of the receiving clock).
NYCSIM_API Result<double> resolveObservationTime(int32_t day, int32_t hour, int32_t minute,
                                                 double referenceUnix);

/// Parses one METAR/SPECI. `text` may carry the tgftp two-line format (date line + report) and a
/// trailing '='. `referenceUnix` resolves the day/hour/minute group; pass NaN to leave the
/// observation time unresolved.
NYCSIM_API Result<MetarReport> parseMetar(const char* text, double referenceUnix);

/// Splits a tgftp-style text (date line + report, possibly several) into individual reports.
NYCSIM_API std::vector<std::string> splitReports(const char* text);

// ---- weather-group semantics ----------------------------------------------------------------------

/// Representative liquid-equivalent rate (mm/h) per (type, intensity class), FMH-1 §8.5 bands.
NYCSIM_API double intensityRateMmph(PrecipType type, Intensity intensity);
inline constexpr double kTraceRateMmph = 0.1;
inline constexpr double kThunderstormRateFactor = 1.5;

/// Maps present-weather groups to the contract `precip_type` and the governing intensity.
/// Priority: freezing_rain > sleet > snow > rain > drizzle > none. Vicinity groups do not count.
NYCSIM_API void classifyPrecipitation(const std::vector<WeatherGroup>& groups, double tempC,
                                      PrecipType& type, Intensity& intensity);
/// (rate mm/h liquid equivalent, basis). A measured hourly amount is authoritative when > 0; P0000
/// with precipitating weather is a trace; otherwise the intensity class representative is used,
/// x1.5 when the precipitation is thunderstorm-driven.
NYCSIM_API void precipitationRateMmph(const std::vector<WeatherGroup>& groups, double precipLastHourMm,
                                      double tempC, double& rateMmph, PrecipRateBasis& basis);
/// Obscuration / other phenomena at the station as WeatherState obscuration bits.
NYCSIM_API uint16_t obscurationBits(const std::vector<WeatherGroup>& groups);
/// TS at the station or in the vicinity (VCTS) — both are audible in the world.
NYCSIM_API bool thunderPresent(const std::vector<WeatherGroup>& groups);
/// Total cover 0..1 (largest reported layer amount); NaN when the sky was not reported.
NYCSIM_API double cloudCoverFraction(const std::vector<CloudLayer>& layers, bool hasSkyClearCode);

/// Fills the contract fields of a WeatherState from a decoded report (weather.py
/// `observation_from_metar`). `observedAtUnix` overrides the report's own time when finite.
NYCSIM_API Result<WeatherState> weatherStateFromMetar(const MetarReport& rep, double nowUnix,
                                                      double observedAtUnix);

}  // namespace metar
}  // namespace weather
}  // namespace nycsim
