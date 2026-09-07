// nycsim/weather/WorldEffects.h — the ARCHITECTURE §11 "weather -> world" mapping table.
//
// One pure function turns a WeatherState into the scalar drives the renderer, the physics and the
// crowd consume: road wetness and puddles, snow cover, fog density, wind for flags and awnings,
// umbrella and plow/salt probabilities, tyre-surface class, headlight/wiper state and the sky's
// overcast factor. It is deterministic, allocation free and has no engine dependency, so both the
// Unreal runtime and the tests evaluate exactly the same numbers.
//
// This mapping has no Python counterpart in services/nycsim_live (that package stops at the
// observation). It is therefore specified here and is the authority; the table below states each
// constant and where it comes from. Every output is clamped to its documented range.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/vehicle/Friction.h"
#include "nycsim/weather/WeatherState.h"

namespace nycsim {
namespace weather {

/// How the world should be dressed. All scalars are 0..1 unless a unit is named.
struct WorldEffects {
  double wetness = 0.0;          ///< road/pavement wetness for the material's roughness+specular
  double puddles = 0.0;          ///< puddle coverage (lags wetness; needs sustained rain)
  double snowCover = 0.0;        ///< horizontal-surface snow coverage
  double snowDepthM = 0.0;       ///< metres, for displacement and plough berms
  double iceRisk = 0.0;          ///< black-ice probability driver (freezing rain / refreeze)
  double fogDensity = 0.0;       ///< exponential height-fog density multiplier
  double windSpeedMps = 0.0;     ///< sustained wind for cloth/foliage
  double windGustMps = 0.0;
  double windHeadingDeg = 0.0;   ///< compass direction the air moves TOWARDS
  double flagSway = 0.0;         ///< normalised cloth amplitude
  double umbrellaShare = 0.0;    ///< fraction of pedestrians carrying an open umbrella
  double pedestrianDensityScale = 1.0;  ///< multiplier on the calibrated sidewalk density
  double plowActivity = 0.0;     ///< DSNY plow/salt spreader spawn weight
  double overcast = 0.0;         ///< sky cloud fraction actually used for lighting
  double rainRateMmph = 0.0;     ///< particle-system rate driver
  double snowRateCmph = 0.0;
  bool headlights = false;       ///< daytime-visibility rule (NY VTL 375(2): wipers on -> lights on)
  bool wipers = false;
  int32_t wiperSpeed = 0;        ///< 0 off, 1 intermittent, 2 low, 3 high
  bool thunder = false;
  vehicle::SurfaceClass surface = vehicle::SurfaceClass::DryAsphalt;
};

/// Thresholds and gains of the mapping (ARCHITECTURE §11). They are constants of the world, not
/// tuning knobs of an individual scene, so they live with the mapping and are unit-tested.
struct WorldEffectsConfig {
  // -- wetness: a road is fully wet after ~2 mm/h of rain and dries with an e-folding of 45 min.
  double fullWetRateMmph = 2.0;
  double dryingHalfLifeS = 2700.0;
  // -- puddles: only sustained moderate rain ponds; NYC crowned asphalt drains fast.
  double puddleOnsetMmph = 1.5;
  double puddleFullMmph = 8.0;
  double puddleDryingHalfLifeS = 5400.0;
  // -- snow: 2 cm covers grass and pavement completely for rendering purposes.
  double fullCoverDepthCm = 2.0;
  // -- fog: visibility 10 km -> 0, 200 m -> 1 (log-linear); mist (BR) and fog (FG) force a floor.
  double fogClearVisibilityM = 10000.0;
  double fogFullVisibilityM = 200.0;
  double mistFogFloor = 0.25;
  double fogFogFloor = 0.6;
  // -- crowd: umbrellas appear from drizzle upwards; density falls in hard weather.
  double umbrellaOnsetMmph = 0.2;
  double umbrellaFullMmph = 3.0;
  double umbrellaMaxShare = 0.72;      ///< not everyone owns one
  double minPedestrianScale = 0.35;
  // -- plows: DSNY deploys at 5 cm accumulation, full fleet by 15 cm; salt below freezing.
  double plowOnsetDepthCm = 5.0;
  double plowFullDepthCm = 15.0;
  // -- wipers
  double wiperIntermittentMmph = 0.05;
  double wiperLowMmph = 1.0;
  double wiperHighMmph = 5.0;
  // -- flags: a 25 m/s gust is the visual maximum.
  double flagFullWindMps = 25.0;
};

/// State the mapping carries between frames (wetness and puddles have memory).
struct WorldEffectsState {
  double wetness = 0.0;
  double puddles = 0.0;
  bool initialised = false;
};

/// Instantaneous mapping (no memory): wetness/puddles are the equilibrium values for this weather.
NYCSIM_API WorldEffects worldEffects(const WeatherState& s,
                                     const WorldEffectsConfig& cfg = WorldEffectsConfig());

/// Time-stepped mapping: wetness and puddles relax towards their equilibrium with the configured
/// half-lives, so a shower leaves the streets wet for a while. `dtS` <= 0 initialises the state.
NYCSIM_API WorldEffects worldEffectsStep(const WeatherState& s, WorldEffectsState& state, double dtS,
                                         const WorldEffectsConfig& cfg = WorldEffectsConfig());

}  // namespace weather
}  // namespace nycsim
