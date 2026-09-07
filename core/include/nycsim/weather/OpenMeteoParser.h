// nycsim/weather/OpenMeteoParser.h — Open-Meteo forecast API decoder (secondary provider, ADR-011).
//
// C++ port of `parse_open_meteo` in services/nycsim_live/weather.py, including the WMO 4677 code
// table, the interval-to-rate conversion, the rain/snow partition fallback when the code says dry,
// and the visibility lookup in the `minutely_15` block.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/io/Json.h"
#include "nycsim/util/Result.h"
#include "nycsim/weather/MetarParser.h"
#include "nycsim/weather/WeatherState.h"

namespace nycsim {
namespace weather {

inline constexpr const char* kOpenMeteoUrl =
    "https://api.open-meteo.com/v1/forecast?latitude=40.7831&longitude=-73.9712"
    "&current=temperature_2m,relative_humidity_2m,dew_point_2m,precipitation,rain,showers,snowfall,"
    "weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
    "&minutely_15=temperature_2m,precipitation,rain,snowfall,weather_code,visibility,wind_speed_10m,"
    "wind_direction_10m,wind_gusts_10m&forecast_minutely_15=12&timezone=UTC&wind_speed_unit=ms";

struct WmoMapping {
  PrecipType type = PrecipType::None;
  metar::Intensity intensity = metar::Intensity::Moderate;
  bool thunder = false;
  uint16_t obscuration = 0;
  bool known = false;  ///< false when the code is not in the table (treated as dry)
};
/// WMO 4677 present-weather code as used by Open-Meteo.
NYCSIM_API WmoMapping wmoCodeMapping(int32_t code);

/// Decodes an Open-Meteo `/v1/forecast` response with a `current` block.
NYCSIM_API Result<WeatherState> parseOpenMeteo(const json::Value& doc, double nowUnix);

}  // namespace weather
}  // namespace nycsim
