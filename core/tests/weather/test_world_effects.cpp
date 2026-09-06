#include <doctest/doctest.h>

#include <cmath>

#include "nycsim/vehicle/Friction.h"
#include "nycsim/weather/WorldEffects.h"

using namespace nycsim;
using namespace nycsim::weather;

namespace {

WeatherState clearDay() {
  WeatherState s;
  s.source = Source::Nws;
  s.observedAtUnix = 1788691860.0;
  s.tempC = 22.0;
  s.dewpointC = 12.0;
  s.rh = relativeHumidity(22.0, 12.0);
  s.cloudCover = 0.1875;
  s.visibilityM = 16090.0;
  s.pressureHpa = 1015.0;
  s.windMps = 3.0;
  s.windGustMps = 5.0;
  setWind(s, 250.0);
  s.precipType = PrecipType::None;
  s.precipRateMmph = 0.0;
  s.precipRateBasis = PrecipRateBasis::None;
  return s;
}

WeatherState rain(double rateMmph) {
  WeatherState s = clearDay();
  s.precipType = PrecipType::Rain;
  s.precipRateMmph = rateMmph;
  s.precipRateBasis = PrecipRateBasis::Measured;
  s.cloudCover = 1.0;
  s.visibilityM = 4000.0;
  return s;
}

WeatherState snowStorm(double rateMmph, double depthCm, double tempC) {
  WeatherState s = clearDay();
  s.tempC = tempC;
  s.dewpointC = tempC - 1.0;
  s.rh = relativeHumidity(s.tempC, s.dewpointC);
  s.precipType = PrecipType::Snow;
  s.precipRateMmph = rateMmph;
  s.precipRateBasis = PrecipRateBasis::Class;
  s.snowfallRateCmph = rateMmph;
  s.snowDepthCm = depthCm;
  s.snowDepthSource = SnowDepthSource::Model;
  s.cloudCover = 1.0;
  s.visibilityM = 800.0;
  s.windMps = 12.0;
  s.windGustMps = 20.0;
  return s;
}

}  // namespace

TEST_SUITE("weather") {
  TEST_CASE("world effects: a clear day drives nothing") {
    const WorldEffects w = worldEffects(clearDay());
    CHECK(w.wetness == 0.0);
    CHECK(w.puddles == 0.0);
    CHECK(w.snowCover == 0.0);
    CHECK(w.snowDepthM == 0.0);
    CHECK(w.iceRisk == 0.0);
    CHECK(w.fogDensity == 0.0);
    CHECK(w.rainRateMmph == 0.0);
    CHECK(w.umbrellaShare == 0.0);
    CHECK(w.plowActivity == 0.0);
    CHECK_FALSE(w.wipers);
    CHECK(w.wiperSpeed == 0);
    CHECK_FALSE(w.headlights);
    CHECK(w.pedestrianDensityScale == doctest::Approx(1.0));
    CHECK(w.surface == vehicle::SurfaceClass::DryAsphalt);
    CHECK(w.windSpeedMps == doctest::Approx(3.0));
    CHECK(w.windGustMps == doctest::Approx(5.0));
    CHECK(w.windHeadingDeg == doctest::Approx(70.0));  // wind FROM 250 blows TOWARDS 70
    CHECK(w.overcast == doctest::Approx(0.1875));
  }

  TEST_CASE("world effects: rain wets the road, fills puddles and raises umbrellas monotonically") {
    double prevWet = -1.0, prevPuddle = -1.0, prevUmbrella = -1.0;
    for (double rate : {0.0, 0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0}) {
      const WorldEffects w = worldEffects(rain(rate));
      INFO("rate ", rate);
      CHECK(w.wetness >= prevWet);
      CHECK(w.puddles >= prevPuddle);
      CHECK(w.umbrellaShare >= prevUmbrella);
      CHECK(w.wetness >= 0.0);
      CHECK(w.wetness <= 1.0);
      CHECK(w.puddles <= w.wetness);
      CHECK(w.rainRateMmph == doctest::Approx(rate));
      prevWet = w.wetness;
      prevPuddle = w.puddles;
      prevUmbrella = w.umbrellaShare;
    }
    // 2 mm/h is fully wet by the documented threshold.
    CHECK(worldEffects(rain(2.0)).wetness == doctest::Approx(1.0));
    CHECK(worldEffects(rain(0.5)).wetness == doctest::Approx(0.25));
    // Puddles need sustained moderate rain.
    CHECK(worldEffects(rain(1.0)).puddles == 0.0);
    CHECK(worldEffects(rain(8.0)).puddles == doctest::Approx(1.0));
    // Umbrella share saturates below 1: not everyone owns one.
    CHECK(worldEffects(rain(16.0)).umbrellaShare == doctest::Approx(0.72));
    // Wipers and (by NY VTL 375) headlights follow the rate.
    CHECK(worldEffects(rain(0.0)).wiperSpeed == 0);
    CHECK(worldEffects(rain(0.2)).wiperSpeed == 1);
    CHECK(worldEffects(rain(2.0)).wiperSpeed == 2);
    CHECK(worldEffects(rain(9.0)).wiperSpeed == 3);
    CHECK(worldEffects(rain(2.0)).headlights);
    CHECK_FALSE(worldEffects(rain(0.2)).headlights);
    // A wet road is a wet-asphalt surface for the tyre model.
    CHECK(worldEffects(rain(4.0)).surface == vehicle::SurfaceClass::WetAsphalt);
    // Crowds thin out in heavy rain but never vanish.
    CHECK(worldEffects(rain(10.0)).pedestrianDensityScale < 0.7);
    CHECK(worldEffects(rain(10.0)).pedestrianDensityScale >= 0.35);
  }

  TEST_CASE("world effects: snow covers the ground, calls out the ploughs and changes the surface") {
    const WorldEffects light = worldEffects(snowStorm(0.5, 0.5, -3.0));
    const WorldEffects heavy = worldEffects(snowStorm(3.0, 18.0, -8.0));
    CHECK(light.snowCover == doctest::Approx(0.25));
    CHECK(heavy.snowCover == doctest::Approx(1.0));
    CHECK(heavy.snowDepthM == doctest::Approx(0.18));
    CHECK(light.plowActivity == doctest::Approx(0.3));  // snowing, but under the 5 cm threshold
    CHECK(heavy.plowActivity == doctest::Approx(1.0));
    CHECK(heavy.surface == vehicle::SurfaceClass::PackedSnow);
    CHECK(light.surface == vehicle::SurfaceClass::DryAsphalt);  // 0.5 cm is not yet a covered road
    // Snow does not wet the road while it lies.
    CHECK(light.wetness == 0.0);
    // But melting snow above 1 C does.
    WeatherState melting = snowStorm(0.0, 6.0, 4.0);
    melting.precipType = PrecipType::None;
    melting.precipRateMmph = 0.0;
    melting.precipRateBasis = PrecipRateBasis::None;
    CHECK(worldEffects(melting).wetness == doctest::Approx(0.6));
    // Deep snow and gales thin the crowd.
    CHECK(heavy.pedestrianDensityScale <= 0.5);
    CHECK(heavy.flagSway > 0.5);
  }

  TEST_CASE("world effects: freezing rain is the ice case and drives salt trucks") {
    WeatherState fzra = clearDay();
    fzra.tempC = -1.0;
    fzra.dewpointC = -2.0;
    fzra.rh = relativeHumidity(fzra.tempC, fzra.dewpointC);
    fzra.precipType = PrecipType::FreezingRain;
    fzra.precipRateMmph = 2.0;
    fzra.precipRateBasis = PrecipRateBasis::Measured;
    fzra.visibilityM = 3000.0;
    const WorldEffects w = worldEffects(fzra);
    CHECK(w.iceRisk == doctest::Approx(1.0));
    CHECK(w.surface == vehicle::SurfaceClass::Ice);
    CHECK(w.plowActivity >= 0.5);
    CHECK(w.puddles == 0.0);  // it is freezing: no standing water
    CHECK(w.wetness > 0.0);   // but the road is wet before it freezes
    // The friction the tyre model then uses is the normative ice value.
    CHECK(vehicle::frictionFor(w.surface, w.wetness, w.snowCover, w.iceRisk) ==
          doctest::Approx(0.15));
    // A wet road that then drops below freezing also raises the ice risk.
    WeatherState refreeze = rain(3.0);
    refreeze.tempC = -3.0;
    refreeze.dewpointC = -5.0;
    refreeze.rh = relativeHumidity(refreeze.tempC, refreeze.dewpointC);
    CHECK(worldEffects(refreeze).iceRisk > 0.5);
  }

  TEST_CASE("world effects: fog density from visibility and the reported obscuration") {
    WeatherState s = clearDay();
    CHECK(worldEffects(s).fogDensity == 0.0);
    s.visibilityM = 5000.0;
    const double mid = worldEffects(s).fogDensity;
    CHECK(mid > 0.0);
    CHECK(mid < 0.5);
    s.visibilityM = 200.0;
    CHECK(worldEffects(s).fogDensity == doctest::Approx(1.0));
    s.visibilityM = 50.0;
    CHECK(worldEffects(s).fogDensity == doctest::Approx(1.0));  // clamped
    // A reported BR/FG sets a floor even with generous visibility.
    WeatherState mist = clearDay();
    mist.obscuration = kObscBR;
    CHECK(worldEffects(mist).fogDensity == doctest::Approx(0.25));
    WeatherState fog = clearDay();
    fog.obscuration = kObscFG;
    CHECK(worldEffects(fog).fogDensity == doctest::Approx(0.6));
    CHECK(worldEffects(fog).headlights);
    CHECK(worldEffects(fog).wiperSpeed == 1);
    CHECK(worldEffects(fog).wetness == doctest::Approx(0.25));
    // Unknown visibility must not invent fog.
    WeatherState unknown = clearDay();
    unknown.visibilityM = WeatherState::kNaN();
    CHECK(worldEffects(unknown).fogDensity == 0.0);
  }

  TEST_CASE("world effects: wetness and puddles have memory across a shower") {
    WorldEffectsState st;
    // A 10-minute downpour.
    WorldEffects w = worldEffectsStep(rain(8.0), st, -1.0);
    CHECK(w.wetness == doctest::Approx(1.0));
    CHECK(w.puddles == doctest::Approx(1.0));
    // It stops: the road stays wet and dries with the documented half-life.
    const WeatherState after = clearDay();
    double t = 0.0;
    double lastWet = 1.0;
    while (t < 2700.0) {
      w = worldEffectsStep(after, st, 60.0);
      CHECK(w.wetness <= lastWet + 1e-12);
      lastWet = w.wetness;
      t += 60.0;
    }
    // 45 minutes is one half-life.
    CHECK(w.wetness == doctest::Approx(0.5).epsilon(0.02));
    CHECK(w.puddles > 0.0);
    CHECK(w.puddles < w.wetness + 1e-9);
    // Another two hours: 9,900 s of drying in all, i.e. 3.667 half-lives -> 0.5^3.667 = 0.0787.
    for (int i = 0; i < 120; ++i) w = worldEffectsStep(after, st, 60.0);
    CHECK(w.wetness == doctest::Approx(std::pow(0.5, 9900.0 / 2700.0)).epsilon(0.01));
    CHECK(w.wetness < 0.09);
    // Rain wets it again quickly (60 s half-life).
    w = worldEffectsStep(rain(4.0), st, 300.0);
    CHECK(w.wetness > 0.95);
    // A zero/negative step re-initialises to the equilibrium.
    WorldEffectsState fresh;
    const WorldEffects eq = worldEffectsStep(rain(1.0), fresh, 0.0);
    CHECK(eq.wetness == doctest::Approx(worldEffects(rain(1.0)).wetness));
  }

  TEST_CASE("world effects: every output stays inside its documented range for any input") {
    // Sweep a wide grid of physically possible weather and assert the invariants.
    int samples = 0;
    for (double temp : {-20.0, -5.0, -1.0, 0.0, 5.0, 15.0, 25.0, 35.0, 40.0}) {
      for (double rate : {0.0, 0.1, 1.0, 5.0, 20.0, 60.0}) {
        for (double depth : {0.0, 1.0, 5.0, 20.0, 60.0}) {
          for (double vis : {50.0, 500.0, 5000.0, 20000.0}) {
            for (int typeIdx = 0; typeIdx <= 5; ++typeIdx) {
              WeatherState s = clearDay();
              s.tempC = temp;
              s.dewpointC = temp - 2.0;
              s.rh = relativeHumidity(s.tempC, s.dewpointC);
              s.precipType = static_cast<PrecipType>(typeIdx);
              s.precipRateMmph = s.precipType == PrecipType::None ? 0.0 : rate;
              s.precipRateBasis =
                  s.precipType == PrecipType::None ? PrecipRateBasis::None : PrecipRateBasis::Measured;
              s.snowDepthCm = depth;
              s.snowDepthSource = depth > 0.0 ? SnowDepthSource::Model : SnowDepthSource::None;
              s.visibilityM = vis;
              s.windMps = 8.0;
              s.windGustMps = 30.0;
              const WorldEffects w = worldEffects(s);
              ++samples;
              CHECK(w.wetness >= 0.0);
              CHECK(w.wetness <= 1.0);
              CHECK(w.puddles >= 0.0);
              CHECK(w.puddles <= 1.0);
              CHECK(w.snowCover >= 0.0);
              CHECK(w.snowCover <= 1.0);
              CHECK(w.iceRisk >= 0.0);
              CHECK(w.iceRisk <= 1.0);
              CHECK(w.fogDensity >= 0.0);
              CHECK(w.fogDensity <= 1.0);
              CHECK(w.umbrellaShare >= 0.0);
              CHECK(w.umbrellaShare <= 0.72);
              CHECK(w.plowActivity >= 0.0);
              CHECK(w.plowActivity <= 1.0);
              CHECK(w.overcast >= 0.0);
              CHECK(w.overcast <= 1.0);
              CHECK(w.pedestrianDensityScale >= 0.35);
              CHECK(w.pedestrianDensityScale <= 1.0);
              CHECK(w.flagSway >= 0.0);
              CHECK(w.flagSway <= 1.0);
              CHECK(w.wiperSpeed >= 0);
              CHECK(w.wiperSpeed <= 3);
              CHECK(w.snowDepthM >= 0.0);
              CHECK(std::isfinite(w.windHeadingDeg));
              const double mu = vehicle::frictionFor(w.surface, w.wetness, w.snowCover, w.iceRisk);
              CHECK(mu >= 0.10);
              CHECK(mu <= 1.0);
            }
          }
        }
      }
    }
    CHECK(samples == 9 * 6 * 5 * 4 * 6);
    // An entirely unknown state (all NaN) must not crash or produce NaN drives.
    WeatherState nothing;
    const WorldEffects w = worldEffects(nothing);
    CHECK(std::isfinite(w.wetness));
    CHECK(std::isfinite(w.fogDensity));
    CHECK(std::isfinite(w.snowCover));
    CHECK(std::isfinite(w.pedestrianDensityScale));
    CHECK(w.surface == vehicle::SurfaceClass::DryAsphalt);
  }
}
