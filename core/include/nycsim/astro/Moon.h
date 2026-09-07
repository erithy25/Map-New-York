// nycsim/astro/Moon.h — lunar position, illumination and phase.
//
// Meeus, "Astronomical Algorithms" 2nd ed., ch. 47 (the complete periodic series of tables 47.A and
// 47.B plus the additive terms of eq. 47.6/47.7: +/-10" in longitude, +/-4" in latitude, +/-4 km in
// distance) and ch. 48 (illuminated fraction and phase angle), fed through the same topocentric
// parallax + refraction chain as the Sun in Spa.h.
//
// C++ port of the Moon half of services/nycsim_live/astronomy.py.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/astro/Spa.h"

namespace nycsim {
namespace astro {

/// Meeus 55.1 ratio of the Moon's radius to the Earth's equatorial radius.
inline constexpr double kMoonRadiusRatio = 0.272481;

enum class MoonPhase : uint8_t {
  New = 0,
  WaxingCrescent,
  FirstQuarter,
  WaxingGibbous,
  Full,
  WaningGibbous,
  LastQuarter,
  WaningCrescent,
};
NYCSIM_API const char* moonPhaseName(MoonPhase p);
/// Eight-phase index from the Moon-Sun elongation; principal phases get a +/-22.5 deg window.
NYCSIM_API MoonPhase moonPhaseFromElongation(double elongationDeg);

struct MoonGeocentric {
  double jde = 0.0, T = 0.0;
  double Lp = 0.0;   ///< mean longitude
  double D = 0.0;    ///< mean elongation
  double M = 0.0;    ///< Sun mean anomaly
  double Mp = 0.0;   ///< Moon mean anomaly
  double F = 0.0;    ///< argument of latitude
  double E = 0.0;
  double sigmaL = 0.0, sigmaB = 0.0, sigmaR = 0.0;
  double longitude = 0.0;         ///< geocentric ecliptic lambda (mean equinox of date)
  double latitude = 0.0;          ///< beta
  double distanceKm = 0.0;        ///< Delta
  double parallaxDeg = 0.0;       ///< pi
  double apparentLongitude = 0.0; ///< lambda + delta-psi
  double deltaPsi = 0.0, epsilon = 0.0;
  double rightAscension = 0.0, declination = 0.0;
};

struct MoonPosition {
  MoonGeocentric geocentric;
  double azimuth = 0.0;              ///< compass
  double elevation = 0.0;            ///< apparent (refracted)
  double elevationUncorrected = 0.0;
  double zenith = 0.0;
  double distanceKm = 0.0;
  double semidiameterDeg = 0.0;      ///< topocentric
  double illuminatedFraction = 0.0;  ///< k, 0..1
  double phaseAngleDeg = 0.0;        ///< i, 0 = full, 180 = new
  double elongationDeg = 0.0;        ///< lambda_moon - lambda_sun in [0, 360); < 180 = waxing
  bool waxing = false;
  MoonPhase phase = MoonPhase::New;
  double ageFraction = 0.0;          ///< elongation / 360
};

NYCSIM_API MoonGeocentric moonGeocentric(double jde);
/// (illuminated fraction k, phase angle i in degrees, elongation in degrees) — Meeus 48.1-48.3.
NYCSIM_API void moonIllumination(const MoonGeocentric& moon, const GeocentricSun& sun, double& k,
                                 double& phaseAngleDeg, double& elongationDeg);
NYCSIM_API MoonPosition moonPositionJd(double jd, const Observer& obs, double deltaT_s);
NYCSIM_API MoonPosition moonPositionUnix(double unix_s, const Observer& obs);

}  // namespace astro
}  // namespace nycsim
