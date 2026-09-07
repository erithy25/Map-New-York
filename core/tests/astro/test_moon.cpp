#include <doctest/doctest.h>

#include <cmath>
#include <string>

#include "astro_cases.h"
#include "usno_cases.h"
#include "nycsim/astro/Moon.h"
#include "nycsim/time/NyTime.h"

using namespace nycsim;
using namespace nycsim::astro;

TEST_SUITE("astro") {
  TEST_CASE("Meeus example 47.a (1992 April 12, 0h TD)") {
    // Meeus, Astronomical Algorithms 2nd ed., example 47.a: JDE = 2448724.5 gives
    // lambda = 133.162655 deg, beta = -3.229126 deg, Delta = 368409.7 km, pi = 0.991990 deg.
    const MoonGeocentric m = moonGeocentric(2448724.5);
    CHECK(std::fabs(m.T - (-0.077221081451)) < 1e-11);
    CHECK(std::fabs(m.Lp - 134.290182) < 1e-5);
    CHECK(std::fabs(m.D - 113.842304) < 1e-5);
    CHECK(std::fabs(m.M - 97.643514) < 1e-5);
    CHECK(std::fabs(m.Mp - 5.150833) < 1e-5);
    CHECK(std::fabs(m.F - 219.889721) < 1e-5);
    CHECK(std::fabs(m.sigmaL - (-1127527.0)) < 1.0);
    CHECK(std::fabs(m.sigmaB - (-3229126.0)) < 1.0);
    CHECK(std::fabs(m.sigmaR - (-16590875.0)) < 1.0);
    CHECK(std::fabs(m.longitude - 133.162655) < 1e-5);
    CHECK(std::fabs(m.latitude - (-3.229126)) < 1e-5);
    CHECK(std::fabs(m.distanceKm - 368409.7) < 0.1);
    CHECK(std::fabs(m.parallaxDeg - 0.991990) < 1e-5);
  }

  TEST_CASE("Meeus example 48.a illuminated fraction") {
    // Example 48.a: 1992 April 12, 0h TD -> phase angle i = 69.0756 deg, k = 0.6786.
    const double jde = 2448724.5;
    const MoonGeocentric m = moonGeocentric(jde);
    const GeocentricSun s = geocentricSun(jde, 0.0);
    double k = 0.0, i = 0.0, elong = 0.0;
    moonIllumination(m, s, k, i, elong);
    CHECK(std::fabs(i - 69.0756) < 0.01);
    CHECK(std::fabs(k - 0.6786) < 1e-4);
    CHECK(elong > 100.0);
    CHECK(elong < 115.0);
  }

  TEST_CASE("Moon position matches the Python reference at 97 instants") {
    double worstAngle = 0.0;
    double worstDist = 0.0;
    double worstK = 0.0;
    int phaseMismatches = 0;
    for (int i = 0; i < nycsim_test_astro::kMoonSampleCount; ++i) {
      const auto& s = nycsim_test_astro::kMoonSamples[i];
      const MoonPosition p = moonPositionUnix(s.unix_s, kCentralPark);
      worstAngle = std::fmax(worstAngle, std::fabs(limitDegrees180pm(p.azimuth - s.azimuth)));
      worstAngle = std::fmax(worstAngle, std::fabs(p.elevation - s.elevation));
      worstAngle = std::fmax(worstAngle, std::fabs(limitDegrees180pm(p.geocentric.rightAscension - s.ra)));
      worstAngle = std::fmax(worstAngle, std::fabs(p.geocentric.declination - s.dec));
      worstAngle = std::fmax(worstAngle, std::fabs(p.phaseAngleDeg - s.phase_angle));
      worstAngle = std::fmax(worstAngle, std::fabs(limitDegrees180pm(p.elongationDeg - s.elongation)));
      worstDist = std::fmax(worstDist, std::fabs(p.distanceKm - s.distance_km));
      worstK = std::fmax(worstK, std::fabs(p.illuminatedFraction - s.k));
      if (static_cast<int32_t>(p.phase) != s.phase_index) ++phaseMismatches;
    }
    CHECK(nycsim_test_astro::kMoonSampleCount == 97);
    CHECK(worstAngle < 1e-9);
    CHECK(worstDist < 1e-6);
    CHECK(worstK < 1e-12);
    CHECK(phaseMismatches == 0);
  }

  TEST_CASE("phase naming and the synodic cycle") {
    CHECK(moonPhaseFromElongation(0.0) == MoonPhase::New);
    CHECK(moonPhaseFromElongation(45.0) == MoonPhase::WaxingCrescent);
    CHECK(moonPhaseFromElongation(90.0) == MoonPhase::FirstQuarter);
    CHECK(moonPhaseFromElongation(135.0) == MoonPhase::WaxingGibbous);
    CHECK(moonPhaseFromElongation(180.0) == MoonPhase::Full);
    CHECK(moonPhaseFromElongation(225.0) == MoonPhase::WaningGibbous);
    CHECK(moonPhaseFromElongation(270.0) == MoonPhase::LastQuarter);
    CHECK(moonPhaseFromElongation(315.0) == MoonPhase::WaningCrescent);
    CHECK(moonPhaseFromElongation(359.9) == MoonPhase::New);
    CHECK(moonPhaseFromElongation(-1.0) == MoonPhase::New);
    CHECK(std::string(moonPhaseName(MoonPhase::Full)) == "Full Moon");
    CHECK(std::string(moonPhaseName(static_cast<MoonPhase>(9))) == "?");

    // 2026 new moons (Astronomical Almanac / USNO phases of the Moon, UTC):
    // Jan 18 19:52, Feb 17 12:01, Mar 19 01:23. The elongation must be near 0 and k near 0.
    struct NewMoon {
      int32_t y, mo, d, h, mi;
    };
    const NewMoon news[] = {{2026, 1, 18, 19, 52}, {2026, 2, 17, 12, 1}, {2026, 3, 19, 1, 23}};
    for (const NewMoon& nm : news) {
      const double t = static_cast<double>(nytime::unixFromCivilUtc(nm.y, nm.mo, nm.d, nm.h, nm.mi, 0));
      const MoonPosition p = moonPositionUnix(t, kCentralPark);
      const double e = std::fabs(limitDegrees180pm(p.elongationDeg));
      CHECK(e < 0.6);                       // < 0.6 deg of the exact conjunction in longitude
      CHECK(p.illuminatedFraction < 0.005);  // essentially dark
      CHECK(p.phase == MoonPhase::New);
    }
    // 2026 full moons: Jan 3 10:03, Feb 1 22:09, Mar 3 11:38 UTC.
    const NewMoon fulls[] = {{2026, 1, 3, 10, 3}, {2026, 2, 1, 22, 9}, {2026, 3, 3, 11, 38}};
    for (const NewMoon& fm : fulls) {
      const double t = static_cast<double>(nytime::unixFromCivilUtc(fm.y, fm.mo, fm.d, fm.h, fm.mi, 0));
      const MoonPosition p = moonPositionUnix(t, kCentralPark);
      CHECK(std::fabs(limitDegrees180pm(p.elongationDeg - 180.0)) < 0.6);
      CHECK(p.illuminatedFraction > 0.995);
      CHECK(p.phase == MoonPhase::Full);
    }
  }

  TEST_CASE("illuminated fraction matches the USNO one-day tables") {
    // USNO publishes the illuminated fraction of the Moon's disc at 12:00 local time, rounded to a
    // whole per cent (docs/verification/core/usno_oneday.json).
    double worst = 0.0;
    for (int i = 0; i < nycsim_test_usno::kUsnoDayCount; ++i) {
      const auto& u = nycsim_test_usno::kUsnoDays[i];
      const double noonLocalUnix =
          static_cast<double>(nytime::unixFromCivilUtc(u.y, u.mo, u.d, 12, 0, 0)) -
          u.tz_hours * 3600.0;
      const MoonPosition p = moonPositionUnix(noonLocalUnix, kCentralPark);
      const double pct = p.illuminatedFraction * 100.0;
      worst = std::fmax(worst, std::fabs(pct - static_cast<double>(u.moon_fracillum_pct)));
    }
    CHECK(nycsim_test_usno::kUsnoDayCount == 15);
    CHECK(worst < 0.6);  // USNO rounds to whole per cent
  }

  TEST_CASE("physical ranges over a full synodic month") {
    // Sample every 37 minutes for 30 days and check the whole state stays physical.
    const double t0 = static_cast<double>(nytime::unixFromCivilUtc(2026, 4, 1, 0, 0, 0));
    double minDist = 1e12, maxDist = 0.0, minK = 1.0, maxK = 0.0, maxSemi = 0.0, minSemi = 1e9;
    bool sawWaxing = false, sawWaning = false, sawUp = false, sawDown = false;
    for (int i = 0; i < 30 * 24 * 60 / 37; ++i) {
      const double t = t0 + i * 37.0 * 60.0;
      const MoonPosition p = moonPositionUnix(t, kCentralPark);
      CHECK(p.illuminatedFraction >= 0.0);
      CHECK(p.illuminatedFraction <= 1.0);
      CHECK(p.elongationDeg >= 0.0);
      CHECK(p.elongationDeg < 360.0);
      CHECK(p.azimuth >= 0.0);
      CHECK(p.azimuth < 360.0);
      CHECK(p.elevation >= -91.0);
      CHECK(p.elevation <= 91.0);
      CHECK(p.zenith + p.elevation == doctest::Approx(90.0).epsilon(1e-12));
      CHECK(p.phaseAngleDeg >= 0.0);
      CHECK(p.phaseAngleDeg <= 180.0);
      minDist = std::fmin(minDist, p.distanceKm);
      maxDist = std::fmax(maxDist, p.distanceKm);
      minK = std::fmin(minK, p.illuminatedFraction);
      maxK = std::fmax(maxK, p.illuminatedFraction);
      minSemi = std::fmin(minSemi, p.semidiameterDeg);
      maxSemi = std::fmax(maxSemi, p.semidiameterDeg);
      sawWaxing = sawWaxing || p.waxing;
      sawWaning = sawWaning || !p.waxing;
      sawUp = sawUp || p.elevation > 40.0;
      sawDown = sawDown || p.elevation < -40.0;
      // Refraction is only applied at or above the refracted horizon.
      if (p.elevationUncorrected < -1.5) CHECK(p.elevation == p.elevationUncorrected);
    }
    // Perigee/apogee bracket the real 356,500-406,700 km range.
    CHECK(minDist > 356000.0);
    CHECK(minDist < 372000.0);
    CHECK(maxDist > 398000.0);
    CHECK(maxDist < 407000.0);
    CHECK(minK < 0.02);
    CHECK(maxK > 0.98);
    // Apparent semi-diameter 0.245-0.28 deg (14.7'-16.8').
    CHECK(minSemi > 0.24);
    CHECK(maxSemi < 0.29);
    CHECK(sawWaxing);
    CHECK(sawWaning);
    CHECK(sawUp);
    CHECK(sawDown);
  }
}
