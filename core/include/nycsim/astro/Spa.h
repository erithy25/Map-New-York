// nycsim/astro/Spa.h — NREL Solar Position Algorithm (Reda & Andreas, Solar Energy 76 (2004)
// 577-589, corrected 2007/2008; NREL/TP-560-34302) and the rise/transit/set procedure of its
// Appendix A.2.
//
// Complete implementation: Earth heliocentric VSOP87-derived series (L0-L5, B0-B1, R0-R4), IAU 1980
// nutation (63 terms), true obliquity, aberration, apparent sidereal time, geocentric -> topocentric
// parallax, atmospheric refraction, azimuth/zenith. Stated accuracy +/-0.0003 deg for the years
// -2000..6000 given an exact Delta-T.
//
// C++ port of services/nycsim_live/astronomy.py; the test suite reproduces the NREL reference case
// (2003-10-17 12:30:30 UTC-7, 39.742476 N, 105.1786 W, 1830.14 m, 820 mbar, 11 C ->
// zenith 50.11162 deg, azimuth 194.34024 deg) and diffs a year of positions against the Python
// implementation.
//
// Angles are degrees. `azimuth` is compass (0 = north, 90 = east) to match the DATA_CONTRACTS
// `*_heading` convention; the SPA "astronomers' azimuth" (westward from south) is `azimuthAstro`.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/time/NyTime.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace astro {

inline constexpr double kPi = 3.14159265358979323846;
inline constexpr double kDeg = kPi / 180.0;
inline constexpr double kRad = 180.0 / kPi;

inline constexpr double kSunRadiusDeg = 0.26667;          ///< SPA mean apparent semi-diameter
inline constexpr double kAtmosRefractHorizonDeg = 0.5667; ///< SPA default refraction at the horizon
/// Geometric altitude of the Sun's centre at rise/set (upper limb on the horizon, USNO convention).
inline constexpr double kRiseSetH0Deg = -(kSunRadiusDeg + kAtmosRefractHorizonDeg);
inline constexpr double kCivilTwilightH0Deg = -6.0;
inline constexpr double kNauticalTwilightH0Deg = -12.0;
inline constexpr double kAstronomicalTwilightH0Deg = -18.0;
inline constexpr double kEarthRadiusKm = 6378.14;
inline constexpr double kAuKm = 149597870.7;
inline constexpr double kStandardPressureMbar = 1013.25;
inline constexpr double kStandardTemperatureC = 15.0;

// ---- angle helpers (shared with Moon.h) -----------------------------------------------------------
NYCSIM_API double limitDegrees(double deg);      ///< wrap to [0, 360)
NYCSIM_API double limitDegrees180pm(double deg); ///< wrap to [-180, 180)
NYCSIM_API double limitZeroToOne(double x);      ///< x - floor(x)

struct Observer {
  double latitudeDeg = 40.7831;   ///< geodetic, north positive
  double longitudeDeg = -73.9712; ///< east positive
  double elevationM = 40.0;
  double pressureMbar = kStandardPressureMbar;
  double temperatureC = kStandardTemperatureC;
  double atmosRefractDeg = kAtmosRefractHorizonDeg;
};

/// Central Park (the NWS KNYC observation site) — the simulation's default sky observer.
inline constexpr Observer kCentralPark{40.7831, -73.9712, 40.0, kStandardPressureMbar,
                                       kStandardTemperatureC, kAtmosRefractHorizonDeg};
/// 42nd Street at Tudor City Place: the Manhattanhenge viewpoint looking west along 42nd Street.
inline constexpr Observer kTudorCity42nd{40.7489, -73.9711, 20.0, kStandardPressureMbar,
                                         kStandardTemperatureC, kAtmosRefractHorizonDeg};

/// Geocentric Sun, all SPA intermediate quantities (degrees except R in AU).
struct GeocentricSun {
  double jd = 0.0, jde = 0.0, jc = 0.0, jce = 0.0, jme = 0.0;
  double L = 0.0, B = 0.0, R = 0.0;   ///< Earth heliocentric longitude/latitude/radius
  double theta = 0.0, beta = 0.0;     ///< geocentric Sun longitude/latitude
  double deltaPsi = 0.0, deltaEpsilon = 0.0, epsilon = 0.0;
  double deltaTau = 0.0;              ///< aberration
  double lambda = 0.0;                ///< apparent Sun longitude
  double nu0 = 0.0, nu = 0.0;         ///< mean / apparent sidereal time at Greenwich
  double alpha = 0.0, delta = 0.0;    ///< geocentric right ascension / declination
};

struct SolarPosition {
  double jd = 0.0;
  double deltaTS = 0.0;
  GeocentricSun geocentric;
  double hourAngle = 0.0;            ///< H
  double xi = 0.0;                   ///< equatorial horizontal parallax
  double alphaPrime = 0.0;           ///< topocentric right ascension
  double deltaPrime = 0.0;           ///< topocentric declination
  double hourAnglePrime = 0.0;       ///< H'
  double elevationUncorrected = 0.0; ///< e0
  double refraction = 0.0;           ///< delta-e
  double elevation = 0.0;            ///< e = e0 + delta-e (apparent)
  double zenith = 0.0;               ///< 90 - e
  double azimuthAstro = 0.0;         ///< westward from south
  double azimuth = 0.0;              ///< compass, from north eastward
  double distanceAu = 0.0;
  double semidiameterDeg = 0.0;
};

// ---- SPA building blocks (public so tests and the Moon share them) ---------------------------------
NYCSIM_API double julianCentury(double jd);
NYCSIM_API double julianEphemerisDay(double jd, double deltaT_s);
NYCSIM_API double earthHeliocentricLongitude(double jme);
NYCSIM_API double earthHeliocentricLatitude(double jme);
NYCSIM_API double earthRadiusVector(double jme);
/// IAU 1980 nutation in longitude and obliquity (degrees).
NYCSIM_API void nutation(double jce, double& deltaPsi, double& deltaEpsilon);
NYCSIM_API double meanEclipticObliquityArcsec(double jme);
NYCSIM_API double trueEclipticObliquity(double jme, double deltaEpsilon);
NYCSIM_API double greenwichMeanSiderealTime(double jd, double jc);
NYCSIM_API double geocentricRightAscension(double lambda, double epsilon, double beta);
NYCSIM_API double geocentricDeclination(double beta, double epsilon, double lambda);
NYCSIM_API double observerHourAngle(double nu, double longitudeDeg, double alpha);
NYCSIM_API double equatorialHorizontalParallax(double r_au);
/// SPA 3.12/3.13: parallax in right ascension (deltaAlpha), topocentric declination and hour angle.
NYCSIM_API void topocentricCorrections(double latDeg, double elevM, double xi, double h, double delta,
                                       double& deltaAlpha, double& deltaPrime, double& hPrime);
NYCSIM_API double topocentricElevationAngle(double latDeg, double deltaPrime, double hPrime);
/// SPA eq. 42; returns 0 when the body is below the refracted horizon.
NYCSIM_API double atmosphericRefractionCorrection(double pressureMbar, double temperatureC, double e0,
                                                  double atmosRefractDeg = kAtmosRefractHorizonDeg,
                                                  double bodyRadiusDeg = kSunRadiusDeg);
NYCSIM_API double topocentricAzimuthAstro(double hPrime, double latDeg, double deltaPrime);

NYCSIM_API GeocentricSun geocentricSun(double jd, double deltaT_s);
NYCSIM_API SolarPosition solarPositionJd(double jd, const Observer& obs, double deltaT_s);
/// Convenience: Delta-T from nytime::deltaTSeconds for the given POSIX instant.
NYCSIM_API SolarPosition solarPositionUnix(double unix_s, const Observer& obs);

// ---- rise / transit / set (SPA Appendix A.2) -------------------------------------------------------

struct SunEvents {
  nytime::Date dateUtc;
  bool hasSunrise = false;
  bool hasSunset = false;
  double sunriseUnix = 0.0;
  double transitUnix = 0.0;
  double sunsetUnix = 0.0;
  double h0Deg = kRiseSetH0Deg;
};

/// Rise, transit and set on a UT calendar day. `h0Deg` selects the event: -0.8333 reproduces the
/// USNO sunrise/sunset tables, -6/-12/-18 give civil/nautical/astronomical twilight.
NYCSIM_API SunEvents sunRiseTransitSet(nytime::Date dateUtc, const Observer& obs,
                                       double h0Deg = kRiseSetH0Deg);
/// Rise/transit/set that fall on a New York *local* calendar day (the local day's sunset can land
/// on the next UT day). Each event is validated independently.
NYCSIM_API Result<SunEvents> sunEventsLocal(nytime::Date localDate, const Observer& obs,
                                            double h0Deg = kRiseSetH0Deg);

// ---- Manhattanhenge --------------------------------------------------------------------------------
// Manhattan's street grid (Commissioners' Plan of 1811) is rotated 29.0 deg clockwise from a true
// east-west line, so a sunset aligned with the numbered cross-streets has compass azimuth 299.0 deg.
inline constexpr double kManhattanGridRotationDeg = 29.0;
inline constexpr double kManhattanStreetSunsetAzimuthDeg = 270.0 + kManhattanGridRotationDeg;  // 299.0
inline constexpr double kManhattanhengeToleranceDeg = 0.5;
/// "Full sun": whole disc above the street-end horizon -> disc centre at +0.5 deg apparent elevation.
inline constexpr double kFullSunElevationDeg = 0.5;
/// "Half sun": disc centre on the same street-end horizon, one solar radius lower.
inline constexpr double kHalfSunElevationDeg = kFullSunElevationDeg - kSunRadiusDeg;

struct SunsetAzimuth {
  nytime::Date localDate;
  double unix_s = 0.0;
  double elevationDeg = 0.0;
  double azimuthDeg = 0.0;
  double deltaFromGridDeg = 0.0;  ///< azimuth - 299.0
};

/// Evening instant at which the apparent (refracted, topocentric) solar elevation equals
/// `elevationDeg`, found by bisection between solar transit and 90 min after geometric sunset.
NYCSIM_API Result<SunsetAzimuth> timeOfEveningElevation(nytime::Date localDate, double elevationDeg,
                                                        const Observer& obs,
                                                        double tolerance_s = 0.05);

struct ManhattanhengeEvent {
  bool full = false;  ///< true = full-sun variant, false = half-sun
  nytime::Date localDate;
  double unix_s = 0.0;
  double azimuthDeg = 0.0;
  double deltaFromGridDeg = 0.0;
  bool bestInSeason = false;  ///< closest match of its kind before / after the June solstice
};

/// Every local date in `year` whose setting Sun is within `toleranceDeg` of 299.0 deg. Writes at
/// most `cap` events into `out` and returns the number written (the search window is 1 May..15 Aug).
NYCSIM_API uint32_t manhattanhenge(int32_t year, const Observer& obs, ManhattanhengeEvent* out,
                                   uint32_t cap,
                                   double toleranceDeg = kManhattanhengeToleranceDeg);

}  // namespace astro
}  // namespace nycsim
