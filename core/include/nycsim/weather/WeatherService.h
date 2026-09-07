// nycsim/weather/WeatherService.h — the ordered-provider state machine of ADR-011:
//   NWS -> Open-Meteo -> METAR -> stale
// with a per-provider circuit breaker, a 60 s cadence, a snow-depth model and the stale age
// surfaced to the debug overlay. Nothing is ever synthesised: when no provider answers, the last
// good observation is re-emitted with source = "stale" and its age.
//
// C++ port of the `CircuitBreaker`, `SnowModel` and `WeatherService` classes of
// services/nycsim_live/weather.py. Fetching is injected (std::function) so the engine supplies its
// own HTTP client and the tests supply recorded fixtures; core does no networking.
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"
#include "nycsim/weather/WeatherState.h"

namespace nycsim {
namespace weather {

/// 3 consecutive failures -> open for 5 min -> half-open probe -> closed on success (ADR-011).
class NYCSIM_API CircuitBreaker {
 public:
  enum class State : uint8_t { Closed = 0, Open, HalfOpen };

  explicit CircuitBreaker(const char* name = "", int32_t failureThreshold = 3,
                          double openSeconds = 300.0);

  /// True when a call may be attempted now (transitions Open -> HalfOpen when the timer expired).
  bool allow(double now);
  void recordSuccess(double now);
  void recordFailure(double now, const char* error);

  State state() const { return state_; }
  int32_t consecutiveFailures() const { return consecutiveFailures_; }
  const char* lastError() const { return lastError_.c_str(); }
  double lastSuccessAt() const { return lastSuccessAt_; }
  const char* name() const { return name_.c_str(); }
  /// "closed" | "half_open" | "open(NNNs)" — the string the overlay shows.
  std::string status(double now) const;

 private:
  std::string name_;
  int32_t failureThreshold_;
  double openSeconds_;
  State state_ = State::Closed;
  int32_t consecutiveFailures_ = 0;
  double openedAt_ = WeatherState::kNaN();
  std::string lastError_;
  double lastSuccessAt_ = WeatherState::kNaN();
};

/// Snow depth when no station reports it (KNYC/KLGA/KJFK carry 4/sss only during snow events).
/// Per update with elapsed dt (h, capped at 6):
///   accumulation += snowfall_rate_cmph * dt   (Open-Meteo `snowfall` when available, else
///                   liquid mm/h x SLR/10 with SLR(T) = 8 / 10 / 13 / 18 for snow and 3 for sleet)
///   melt         -= 0.06 * max(0, T - 1 C) * dt
///   rain-on-snow -= 0.02 * rain_rate_mmph * dt
///   settling     *= (1 - 0.02 * dt / 24)
/// An observed depth resets the state. The depth is clamped at 0.
class NYCSIM_API SnowModel {
 public:
  static constexpr double kMaxStepH = 6.0;
  static constexpr double kMeltCmPerHPerC = 0.06;
  static constexpr double kRainMeltCmPerMm = 0.02;
  static constexpr double kSettlePerDay = 0.02;

  /// Snow-to-liquid ratio (Roebber et al. 2003 climatology bands).
  static double snowLiquidRatio(double tempC, PrecipType type);

  void update(WeatherState& s, double nowUnix);
  double depthCm() const { return depthCm_; }
  SnowDepthSource source() const { return source_; }
  double lastUpdateUnix() const { return lastUpdateUnix_; }
  /// Restores persisted state (from live/snow_state.json).
  void restore(double depthCm, double lastUpdateUnix, SnowDepthSource source);

 private:
  double depthCm_ = 0.0;
  double lastUpdateUnix_ = WeatherState::kNaN();
  SnowDepthSource source_ = SnowDepthSource::None;
};

/// One provider: a name and a fetch function. The function returns a WeatherState or an Error;
/// any error counts as one breaker failure. The engine wires these to its HTTP client.
struct Provider {
  std::string name;
  std::function<Result<WeatherState>(double nowUnix)> fetch;
};

struct ProviderStatus {
  std::string name;
  std::string status;
};

class NYCSIM_API WeatherService {
 public:
  explicit WeatherService(std::vector<Provider> providers, double pollIntervalS = kPollIntervalS);

  /// One poll: tries each allowed provider in order, applies the snow model, fills fetched_at and
  /// stale_age_s, and returns the state that the world should use. Never fails: with no provider
  /// answering it returns the last good state marked stale, or an empty stale record.
  const WeatherState& poll(double nowUnix);

  const WeatherState& current() const { return current_; }
  bool hasLastGood() const { return hasLastGood_; }
  const WeatherState& lastGood() const { return lastGood_; }
  /// Seeds the last-known-good state (e.g. from a persisted live/weather.json).
  void restoreLastGood(const WeatherState& s);

  uint64_t polls() const { return polls_; }
  uint64_t failures() const { return failures_; }
  double pollIntervalS() const { return pollIntervalS_; }
  SnowModel& snowModel() { return snow_; }
  const SnowModel& snowModel() const { return snow_; }
  std::vector<ProviderStatus> providerStatus(double nowUnix) const;
  CircuitBreaker* breaker(const char* name);

 private:
  std::vector<Provider> providers_;
  std::vector<CircuitBreaker> breakers_;
  double pollIntervalS_;
  SnowModel snow_;
  WeatherState current_;
  WeatherState lastGood_;
  bool hasLastGood_ = false;
  uint64_t polls_ = 0;
  uint64_t failures_ = 0;
};

/// Serialises a WeatherState as the DATA_CONTRACTS §12 `weather.json` document (numbers rounded to
/// 3 decimals exactly as weather.py's `to_json_dict`). `providerStatus` may be empty.
NYCSIM_API std::string toWeatherJson(const WeatherState& s,
                                     const std::vector<ProviderStatus>& providerStatus);
/// Parses a §12 `weather.json` document back into a WeatherState (for the stale-restore path).
NYCSIM_API Result<WeatherState> fromWeatherJson(const char* text);

}  // namespace weather
}  // namespace nycsim
