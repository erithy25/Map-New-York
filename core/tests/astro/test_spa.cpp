#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>

#include "astro_cases.h"
#include "usno_cases.h"
#include "nycsim/astro/Spa.h"
#include "nycsim/time/NyTime.h"

using namespace nycsim;
using namespace nycsim::astro;

namespace {

/// Absolute difference of two compass angles, accounting for the 0/360 wrap.
double angleDiff(double a, double b) {
  const double d = std::fabs(limitDegrees180pm(a - b));
  return d;
}

}  // namespace

TEST_SUITE("astro") {
  TEST_CASE("NREL SPA reference case (Reda & Andreas table A5.1)") {
    // 2003-10-17 12:30:30 local (UTC-7) at 39.742476 N, 105.1786 W, 1830.14 m, 820 mbar, 11 C,
    // Delta-T = 67 s. Published result: zenith 50.11162 deg, azimuth 194.34024 deg.
    Observer obs;
    obs.latitudeDeg = 39.742476;
    obs.longitudeDeg = -105.1786;
    obs.elevationM = 1830.14;
    obs.pressureMbar = 820.0;
    obs.temperatureC = 11.0;
    nytime::DateTime utc;
    utc.year = 2003;
    utc.month = 10;
    utc.day = 17;
    utc.hour = 19;
    utc.minute = 30;
    utc.second = 30.0;
    const double jd = nytime::julianDay(utc);
    CHECK(jd == doctest::Approx(2452930.312847222).epsilon(1e-12));

    const SolarPosition p = solarPositionJd(jd, obs, 67.0);
    // The mandated acceptance: both angles within 0.001 deg of the published values.
    CHECK(std::fabs(p.zenith - 50.11162) < 0.001);
    CHECK(std::fabs(p.azimuth - 194.34024) < 0.001);
    // Every intermediate of SPA table A5.1 (the paper prints these to 6-9 digits).
    CHECK(std::fabs(p.geocentric.L - 24.0182616917) < 1e-8);
    CHECK(std::fabs(p.geocentric.B - (-0.0001011219)) < 1e-9);
    CHECK(std::fabs(p.geocentric.R - 0.9965422974) < 1e-9);
    CHECK(std::fabs(p.geocentric.theta - 204.0182616917) < 1e-8);
    CHECK(std::fabs(p.geocentric.deltaPsi - (-0.00399840)) < 1e-8);
    CHECK(std::fabs(p.geocentric.deltaEpsilon - 0.00166657) < 1e-8);
    CHECK(std::fabs(p.geocentric.epsilon - 23.440465) < 1e-6);
    CHECK(std::fabs(p.geocentric.lambda - 204.0085519281) < 1e-8);
    CHECK(std::fabs(p.geocentric.nu - 318.5119) < 1e-4);
    CHECK(std::fabs(p.geocentric.alpha - 202.22741) < 1e-5);
    CHECK(std::fabs(p.geocentric.delta - (-9.31434)) < 1e-5);
    CHECK(std::fabs(p.hourAngle - 11.105900) < 1e-5);
    CHECK(std::fabs(p.deltaPrime - (-9.316179)) < 1e-6);
    CHECK(std::fabs(p.hourAnglePrime - 11.10627) < 1e-5);
    CHECK(std::fabs(p.elevationUncorrected - 39.872046) < 1e-6);
    CHECK(std::fabs(p.refraction - 0.016332) < 1e-6);
    CHECK(std::fabs(p.elevation - 39.888378) < 1e-6);
    CHECK(std::fabs(p.azimuthAstro - 14.340240) < 1e-6);
    // Zenith + elevation is exactly 90 by construction.
    CHECK(p.zenith + p.elevation == doctest::Approx(90.0).epsilon(1e-14));
  }

  TEST_CASE("Sun position matches the Python SPA reference at 121 instants through 2026") {
    double worstAngle = 0.0;
    double worstRa = 0.0;
    double worstR = 0.0;
    for (int i = 0; i < nycsim_test_astro::kSpaSampleCount; ++i) {
      const auto& s = nycsim_test_astro::kSpaSamples[i];
      const SolarPosition p = solarPositionUnix(s.unix_s, kCentralPark);
      worstAngle = std::fmax(worstAngle, std::fabs(p.zenith - s.zenith));
      worstAngle = std::fmax(worstAngle, angleDiff(p.azimuth, s.azimuth));
      worstAngle = std::fmax(worstAngle, std::fabs(p.elevationUncorrected - s.e0));
      worstAngle = std::fmax(worstAngle, std::fabs(p.refraction - s.refraction));
      worstRa = std::fmax(worstRa, angleDiff(p.geocentric.alpha, s.ra));
      worstRa = std::fmax(worstRa, std::fabs(p.geocentric.delta - s.dec));
      worstR = std::fmax(worstR, std::fabs(p.distanceAu - s.r_au));
    }
    CHECK(nycsim_test_astro::kSpaSampleCount == 121);
    CHECK(worstAngle < 1e-9);
    CHECK(worstRa < 1e-9);
    CHECK(worstR < 1e-12);
  }

  TEST_CASE("angle helpers") {
    CHECK(limitDegrees(370.0) == doctest::Approx(10.0));
    CHECK(limitDegrees(-10.0) == doctest::Approx(350.0));
    CHECK(limitDegrees(0.0) == 0.0);
    CHECK(limitDegrees180pm(190.0) == doctest::Approx(-170.0));
    CHECK(limitDegrees180pm(-190.0) == doctest::Approx(170.0));
    CHECK(limitDegrees180pm(180.0) == doctest::Approx(-180.0));
    CHECK(limitZeroToOne(1.25) == doctest::Approx(0.25));
    CHECK(limitZeroToOne(-0.25) == doctest::Approx(0.75));
  }

  TEST_CASE("sunrise / transit / sunset for New York local dates match the Python reference") {
    double worst = 0.0;
    for (int i = 0; i < nycsim_test_astro::kSunEventCaseCount; ++i) {
      const auto& c = nycsim_test_astro::kSunEventCases[i];
      nytime::Date d;
      d.year = c.y;
      d.month = c.mo;
      d.day = c.d;
      const Result<SunEvents> ev = sunEventsLocal(d, kCentralPark);
      REQUIRE(ev.ok());
      REQUIRE(ev.value().hasSunrise);
      REQUIRE(ev.value().hasSunset);
      worst = std::fmax(worst, std::fabs(ev.value().sunriseUnix - c.sunrise));
      worst = std::fmax(worst, std::fabs(ev.value().transitUnix - c.transit));
      worst = std::fmax(worst, std::fabs(ev.value().sunsetUnix - c.sunset));
    }
    CHECK(worst < 1e-3);  // seconds
  }

  TEST_CASE("sunrise / transit / sunset match the USNO one-day tables to the minute") {
    // Ground truth fetched from the U.S. Naval Observatory Astronomical Applications API v4 for
    // 40.7831 N, 73.9712 W (docs/verification/core/gen_usno_cases.py; raw responses archived in
    // docs/verification/core/usno_oneday.json). USNO publishes whole minutes.
    int worstRise = 0, worstTransit = 0, worstSet = 0, worstCivil = 0;
    for (int i = 0; i < nycsim_test_usno::kUsnoDayCount; ++i) {
      const auto& u = nycsim_test_usno::kUsnoDays[i];
      nytime::Date d;
      d.year = u.y;
      d.month = u.mo;
      d.day = u.d;
      const Result<SunEvents> ev = sunEventsLocal(d, kCentralPark);
      REQUIRE(ev.ok());
      REQUIRE(ev.value().hasSunrise);
      REQUIRE(ev.value().hasSunset);
      // The offset USNO used for the local clock must be the one nytime derives.
      const Result<nytime::Offset> off = nytime::nyOffset(ev.value().transitUnix);
      REQUIRE(off.ok());
      CHECK(off.value().seconds == u.tz_hours * 3600);
      auto localMinutes = [&](double unix_s) {
        const nytime::DateTime l = nytime::civilFromUnix(unix_s + u.tz_hours * 3600);
        return l.hour * 60 + l.minute;
      };
      worstRise = std::max(worstRise, std::abs(localMinutes(ev.value().sunriseUnix) - u.rise_min));
      worstTransit = std::max(worstTransit, std::abs(localMinutes(ev.value().transitUnix) - u.transit_min));
      worstSet = std::max(worstSet, std::abs(localMinutes(ev.value().sunsetUnix) - u.set_min));
      const Result<SunEvents> civil = sunEventsLocal(d, kCentralPark, kCivilTwilightH0Deg);
      REQUIRE(civil.ok());
      REQUIRE(civil.value().hasSunrise);
      REQUIRE(civil.value().hasSunset);
      worstCivil = std::max(worstCivil, std::abs(localMinutes(civil.value().sunriseUnix) - u.civil_begin_min));
      worstCivil = std::max(worstCivil, std::abs(localMinutes(civil.value().sunsetUnix) - u.civil_end_min));
      // Transit lies between rise and set and the Sun is highest there.
      CHECK(ev.value().transitUnix > ev.value().sunriseUnix);
      CHECK(ev.value().transitUnix < ev.value().sunsetUnix);
      const double eTransit = solarPositionUnix(ev.value().transitUnix, kCentralPark).elevation;
      CHECK(eTransit > solarPositionUnix(ev.value().transitUnix - 600.0, kCentralPark).elevation);
      CHECK(eTransit > solarPositionUnix(ev.value().transitUnix + 600.0, kCentralPark).elevation);
      // The Sun's apparent elevation at the computed rise/set is the rise/set threshold.
      CHECK(std::fabs(solarPositionUnix(ev.value().sunriseUnix, kCentralPark).elevationUncorrected -
                      kRiseSetH0Deg) < 0.02);
      CHECK(std::fabs(solarPositionUnix(ev.value().sunsetUnix, kCentralPark).elevationUncorrected -
                      kRiseSetH0Deg) < 0.02);
    }
    CHECK(nycsim_test_usno::kUsnoDayCount == 15);
    CHECK(worstRise <= 1);
    CHECK(worstTransit <= 1);
    CHECK(worstSet <= 1);
    CHECK(worstCivil <= 1);
  }

  TEST_CASE("twilight thresholds order correctly and polar cases are reported, not faked") {
    nytime::Date d;
    d.year = 2026;
    d.month = 6;
    d.day = 21;
    const SunEvents civil = sunRiseTransitSet(d, kCentralPark, kCivilTwilightH0Deg);
    const SunEvents naut = sunRiseTransitSet(d, kCentralPark, kNauticalTwilightH0Deg);
    const SunEvents astro = sunRiseTransitSet(d, kCentralPark, kAstronomicalTwilightH0Deg);
    const SunEvents geom = sunRiseTransitSet(d, kCentralPark, kRiseSetH0Deg);
    REQUIRE(civil.hasSunrise);
    REQUIRE(naut.hasSunrise);
    REQUIRE(astro.hasSunrise);
    CHECK(astro.sunriseUnix < naut.sunriseUnix);
    CHECK(naut.sunriseUnix < civil.sunriseUnix);
    CHECK(civil.sunriseUnix < geom.sunriseUnix);
    CHECK(geom.sunsetUnix < civil.sunsetUnix);
    CHECK(civil.sunsetUnix < naut.sunsetUnix);
    CHECK(naut.sunsetUnix < astro.sunsetUnix);
    // Above the Arctic circle in June the Sun does not set: the event is absent, never invented.
    Observer arctic;
    arctic.latitudeDeg = 78.22;   // Longyearbyen
    arctic.longitudeDeg = 15.65;
    arctic.elevationM = 0.0;
    const SunEvents polar = sunRiseTransitSet(d, arctic, kRiseSetH0Deg);
    CHECK_FALSE(polar.hasSunrise);
    CHECK_FALSE(polar.hasSunset);
    CHECK(polar.transitUnix > 0.0);
  }

  TEST_CASE("Manhattanhenge: azimuth criterion 299.0 +/- 0.5 deg, dates match the Python reference") {
    ManhattanhengeEvent buf[64];
    int totalChecked = 0;
    int cursor = 0;
    for (int32_t year = 2024; year <= 2028; ++year) {
      const uint32_t n = manhattanhenge(year, kTudorCity42nd, buf, 64);
      REQUIRE(n > 0);
      for (uint32_t i = 0; i < n; ++i) {
        const ManhattanhengeEvent& e = buf[i];
        // Every returned event satisfies the mandated criterion.
        CHECK(std::fabs(e.azimuthDeg - kManhattanStreetSunsetAzimuthDeg) <= kManhattanhengeToleranceDeg);
        CHECK(std::fabs(e.deltaFromGridDeg) <= kManhattanhengeToleranceDeg);
        CHECK(e.localDate.year == year);
        // Cross-check against the Python reference list (same order).
        REQUIRE(cursor < nycsim_test_astro::kHengeCaseCount);
        const auto& c = nycsim_test_astro::kHengeCases[cursor];
        CHECK(c.year == year);
        CHECK(c.mo == e.localDate.month);
        CHECK(c.d == e.localDate.day);
        CHECK((c.full != 0) == e.full);
        CHECK(std::fabs(c.azimuth - e.azimuthDeg) < 1e-6);
        CHECK(std::fabs(c.delta - e.deltaFromGridDeg) < 1e-6);
        CHECK((c.best != 0) == e.bestInSeason);
        ++cursor;
        ++totalChecked;
      }
      // Exactly four "best in season" events per year: full/half x spring/summer.
      int best = 0;
      for (uint32_t i = 0; i < n; ++i) best += buf[i].bestInSeason ? 1 : 0;
      CHECK(best == 4);
      // Events fall in the two known windows: late May and mid July.
      for (uint32_t i = 0; i < n; ++i) {
        CHECK((buf[i].localDate.month == 5 || buf[i].localDate.month == 7));
      }
    }
    CHECK(cursor == nycsim_test_astro::kHengeCaseCount);
    CHECK(totalChecked == 91);
    // The four 2026 best dates, spelled out (the sunset azimuth is what is asserted).
    const uint32_t n26 = manhattanhenge(2026, kTudorCity42nd, buf, 64);
    int bestSeen = 0;
    for (uint32_t i = 0; i < n26; ++i) {
      if (!buf[i].bestInSeason) continue;
      ++bestSeen;
      CHECK(std::fabs(buf[i].azimuthDeg - 299.0) < 0.15);
    }
    CHECK(bestSeen == 4);
    // Degenerate arguments are rejected without writing anything.
    CHECK(manhattanhenge(2026, kTudorCity42nd, nullptr, 10) == 0);
    CHECK(manhattanhenge(2026, kTudorCity42nd, buf, 0) == 0);
    // A tolerance of 0 yields no event (no date matches 299.0 exactly).
    CHECK(manhattanhenge(2026, kTudorCity42nd, buf, 64, 0.0) == 0);
  }

  TEST_CASE("timeOfEveningElevation reports failure instead of guessing") {
    nytime::Date d;
    d.year = 2026;
    d.month = 6;
    d.day = 21;
    const Result<SunsetAzimuth> ok = timeOfEveningElevation(d, kFullSunElevationDeg, kTudorCity42nd);
    REQUIRE(ok.ok());
    CHECK(ok.value().azimuthDeg > 290.0);
    CHECK(ok.value().azimuthDeg < 310.0);
    const SolarPosition p = solarPositionUnix(ok.value().unix_s, kTudorCity42nd);
    CHECK(std::fabs(p.elevation - kFullSunElevationDeg) < 1e-3);
    // 40 deg elevation is never reached in the evening window in NYC in December.
    d.month = 12;
    d.day = 21;
    const Result<SunsetAzimuth> bad = timeOfEveningElevation(d, 40.0, kTudorCity42nd);
    CHECK_FALSE(bad.ok());
    CHECK(bad.error().code == ErrorCode::NoConvergence);
  }
}
