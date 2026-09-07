// nycsim/weather/NwsParser.h — api.weather.gov decoders.
//
// C++ port of the NWS half of services/nycsim_live/weather.py:
//   * parseNwsObservation()  — the `stations/{id}/observations/latest` GeoJSON document;
//   * NwsForecastBlend       — the `gridpoints/OKX/34,45` forecast layers used to carry an hourly
//     observation along the forecast trend (the observation is never replaced, only offset by
//     F(now) - F(t_obs), clamped per quantity, and only when the observation is older than
//     kBlendMinAgeS).
//
// MADIS quality-control flags X (rejected), Q (questioned) and B (subjective bad) discard a value.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/io/Json.h"
#include "nycsim/util/Result.h"
#include "nycsim/weather/WeatherState.h"

namespace nycsim {
namespace weather {

inline constexpr const char* kNwsObsUrlTemplate =
    "https://api.weather.gov/stations/{station}/observations/latest";
/// From /points/40.7831,-73.9712 (Central Park).
inline constexpr const char* kNwsGridpointUrl = "https://api.weather.gov/gridpoints/OKX/34,45";
inline constexpr double kNwsGridpointTtlS = 30.0 * 60.0;

/// One NWS gridpoint layer as (start, value) samples, piecewise-linear between sample starts.
/// Each entry is stored twice (start and end-1) so a long validity does not tilt the interpolation.
class NYCSIM_API GridSeries {
 public:
  GridSeries() = default;
  /// `layer` is the gridpoint property object ({"values": [{"validTime": ..., "value": ...}]}).
  /// A null/absent layer yields an empty series. Malformed entries are skipped.
  GridSeries(const json::Value* layer, double scale);
  /// Interpolated value, NaN outside the sampled span or with fewer than two samples.
  double valueAt(double unix_s) const;
  size_t size() const { return t_.size(); }

 private:
  std::vector<double> t_;
  std::vector<double> v_;
};

/// Forecast-anchored interpolation between hourly observations.
class NYCSIM_API NwsForecastBlend {
 public:
  /// Clamp per quantity (weather.py NWSForecastBlend.LIMITS).
  static constexpr double kLimitTempC = 5.0;
  static constexpr double kLimitDewpointC = 5.0;
  static constexpr double kLimitWindMps = 5.0;
  static constexpr double kLimitWindGustMps = 6.0;
  static constexpr double kLimitCloudCover = 0.4;
  static constexpr double kLimitRh = 25.0;
  static constexpr double kLimitVisibilityM = 8000.0;

  NwsForecastBlend() = default;
  static Result<NwsForecastBlend> fromJson(const json::Value& gridpoint);
  /// Applies the blend in place; returns true when at least one field moved.
  bool apply(WeatherState& s, double nowUnix) const;
  double updateTimeUnix() const { return updateTime_; }

 private:
  GridSeries temp_, dewpoint_, rh_, wind_, gust_, cloud_, visibility_;
  double updateTime_ = WeatherState::kNaN();
};

/// Decodes an `observations/latest` document. Fails (ErrorCode::ParseError / StateError) when the
/// document has no timestamp, is older than kMaxObservationAgeS, or has no usable temperature.
NYCSIM_API Result<WeatherState> parseNwsObservation(const json::Value& doc, double nowUnix);

}  // namespace weather
}  // namespace nycsim
