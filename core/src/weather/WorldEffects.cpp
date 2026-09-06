#include "nycsim/weather/WorldEffects.h"

#include <cmath>

namespace nycsim {
namespace weather {

namespace {

double clamp01(double v) { return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }

/// 0 at `a`, 1 at `b`, linear in between (works for a > b too).
double ramp(double x, double a, double b) {
  if (a == b) return x >= a ? 1.0 : 0.0;
  return clamp01((x - a) / (b - a));
}

double valueOr(double v, double fallback) { return std::isnan(v) ? fallback : v; }

/// Liquid-water rate reaching the road (mm/h). Snow and sleet do not wet the road while they lie.
double liquidRate(const WeatherState& s) {
  const double r = valueOr(s.precipRateMmph, 0.0);
  switch (s.precipType) {
    case PrecipType::Rain:
    case PrecipType::Drizzle:
    case PrecipType::FreezingRain: return r;
    case PrecipType::Sleet: return 0.5 * r;  // half melts on contact on a city street
    case PrecipType::Snow:
    case PrecipType::None: return 0.0;
  }
  return 0.0;
}

/// Exponential relaxation towards `target` with the given half-life.
double relax(double current, double target, double dtS, double halfLifeS) {
  if (!(halfLifeS > 0.0) || !(dtS > 0.0)) return target;
  const double k = std::pow(0.5, dtS / halfLifeS);
  return target + (current - target) * k;
}

}  // namespace

WorldEffects worldEffects(const WeatherState& s, const WorldEffectsConfig& cfg) {
  WorldEffectsState st;
  return worldEffectsStep(s, st, -1.0, cfg);
}

WorldEffects worldEffectsStep(const WeatherState& s, WorldEffectsState& state, double dtS,
                              const WorldEffectsConfig& cfg) {
  WorldEffects w;
  const double rate = valueOr(s.precipRateMmph, 0.0);
  const double liquid = liquidRate(s);
  const double tempC = valueOr(s.tempC, 10.0);
  const double snowDepthCm = valueOr(s.snowDepthCm, 0.0);

  // ---- wetness and puddles (equilibrium, then relaxation)
  double wetTarget = ramp(liquid, 0.0, cfg.fullWetRateMmph);
  if (liquid <= 0.0) wetTarget = 0.0;
  // Melting snow keeps the road wet even without falling liquid.
  if (snowDepthCm > 0.0 && tempC > 1.0) wetTarget = std::fmax(wetTarget, 0.6);
  // Fog and high humidity leave a damp sheen but never a wet road.
  if ((s.obscuration & (kObscFG | kObscBR)) != 0) wetTarget = std::fmax(wetTarget, 0.25);
  double puddleTarget = ramp(liquid, cfg.puddleOnsetMmph, cfg.puddleFullMmph);
  if (tempC < -1.0) puddleTarget = 0.0;  // it is freezing: no standing water

  if (!state.initialised || dtS <= 0.0) {
    state.wetness = wetTarget;
    state.puddles = puddleTarget;
    state.initialised = true;
  } else {
    const double wetHalfLife = wetTarget > state.wetness ? 60.0 : cfg.dryingHalfLifeS;
    const double puddleHalfLife = puddleTarget > state.puddles ? 180.0 : cfg.puddleDryingHalfLifeS;
    state.wetness = relax(state.wetness, wetTarget, dtS, wetHalfLife);
    state.puddles = relax(state.puddles, puddleTarget, dtS, puddleHalfLife);
  }
  w.wetness = clamp01(state.wetness);
  w.puddles = clamp01(std::fmin(state.puddles, state.wetness));

  // ---- snow
  w.snowDepthM = snowDepthCm / 100.0;
  w.snowCover = ramp(snowDepthCm, 0.0, cfg.fullCoverDepthCm);
  w.snowRateCmph = valueOr(s.snowfallRateCmph, s.precipType == PrecipType::Snow ? rate * 1.0 : 0.0);
  if (std::isnan(w.snowRateCmph)) w.snowRateCmph = 0.0;
  w.rainRateMmph = liquid;

  // ---- ice risk: freezing rain is the worst case; wet road below freezing is the next.
  if (s.precipType == PrecipType::FreezingRain && rate > 0.0) {
    w.iceRisk = clamp01(0.6 + 0.4 * ramp(rate, 0.0, 2.0));
  } else if (tempC <= 0.0 && w.wetness > 0.2) {
    w.iceRisk = clamp01(w.wetness * ramp(-tempC, 0.0, 4.0));
  } else if (tempC <= 0.0 && snowDepthCm > 0.0) {
    w.iceRisk = clamp01(0.2 * ramp(-tempC, 0.0, 8.0));
  }

  // ---- fog: log-linear in visibility between 10 km and 200 m, with a floor for reported FG/BR.
  const double vis = valueOr(s.visibilityM, cfg.fogClearVisibilityM);
  if (vis < cfg.fogClearVisibilityM) {
    const double lv = std::log(std::fmax(vis, 10.0));
    const double lo = std::log(cfg.fogFullVisibilityM);
    const double hi = std::log(cfg.fogClearVisibilityM);
    w.fogDensity = clamp01((hi - lv) / (hi - lo));
  }
  if ((s.obscuration & kObscFG) != 0) w.fogDensity = std::fmax(w.fogDensity, cfg.fogFogFloor);
  else if ((s.obscuration & kObscBR) != 0) w.fogDensity = std::fmax(w.fogDensity, cfg.mistFogFloor);

  // ---- wind
  w.windSpeedMps = valueOr(s.windMps, 0.0);
  w.windGustMps = std::fmax(w.windSpeedMps, valueOr(s.windGustMps, w.windSpeedMps));
  w.windHeadingDeg = valueOr(s.windToHeading, 0.0);
  w.flagSway = clamp01(w.windGustMps / cfg.flagFullWindMps);

  // ---- crowd
  w.umbrellaShare = cfg.umbrellaMaxShare * ramp(liquid, cfg.umbrellaOnsetMmph, cfg.umbrellaFullMmph);
  double density = 1.0;
  density -= 0.45 * ramp(rate, 0.0, 6.0);                    // rain or snow drives people indoors
  density -= 0.25 * ramp(-tempC, 0.0, 15.0);                 // deep cold
  density -= 0.20 * ramp(tempC, 30.0, 38.0);                 // heat
  density -= 0.20 * ramp(w.windGustMps, 12.0, 25.0);         // gales
  density -= 0.20 * ramp(snowDepthCm, 2.0, 20.0);            // lying snow
  w.pedestrianDensityScale = std::fmax(cfg.minPedestrianScale, density);

  // ---- DSNY plough / salt activity
  double plow = ramp(snowDepthCm, cfg.plowOnsetDepthCm, cfg.plowFullDepthCm);
  if (s.precipType == PrecipType::Snow && rate > 0.0) plow = std::fmax(plow, 0.3);
  if (tempC <= 0.0 && (s.precipType == PrecipType::FreezingRain || w.iceRisk > 0.4)) {
    plow = std::fmax(plow, 0.5);  // salt spreaders
  }
  w.plowActivity = clamp01(plow);

  // ---- sky, lights and wipers
  w.overcast = clamp01(valueOr(s.cloudCover, 0.0));
  w.thunder = s.thunder;
  if (rate >= cfg.wiperHighMmph) {
    w.wiperSpeed = 3;
  } else if (rate >= cfg.wiperLowMmph) {
    w.wiperSpeed = 2;
  } else if (rate >= cfg.wiperIntermittentMmph || w.fogDensity > 0.4) {
    w.wiperSpeed = 1;
  }
  w.wipers = w.wiperSpeed > 0;
  // NY VTL 375(2)(a): headlights whenever the wipers are in continuous use, and in low visibility.
  w.headlights = w.wiperSpeed >= 2 || w.fogDensity > 0.3 || vis < 1000.0;

  // ---- the surface class the tyre model should use for an asphalt road under this weather
  if (w.snowCover > 0.5) {
    w.surface = vehicle::SurfaceClass::PackedSnow;
  } else if (w.iceRisk > 0.5) {
    w.surface = vehicle::SurfaceClass::Ice;
  } else if (w.wetness > 0.35) {
    w.surface = vehicle::SurfaceClass::WetAsphalt;
  } else {
    w.surface = vehicle::SurfaceClass::DryAsphalt;
  }
  return w;
}

}  // namespace weather
}  // namespace nycsim
