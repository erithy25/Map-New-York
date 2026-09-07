#include "nycsim/astro/Moon.h"

#include <cmath>

#include "nycsim/time/NyTime.h"

namespace nycsim {
namespace astro {

namespace {
#include "SpaTables.inc"  // NOLINT(bugprone-suspicious-include) - generated numeric tables

constexpr const char* kPhaseNames[8] = {"New Moon",  "Waxing Crescent", "First Quarter",
                                        "Waxing Gibbous", "Full Moon", "Waning Gibbous",
                                        "Last Quarter",   "Waning Crescent"};

double clampUnit(double x) { return x < -1.0 ? -1.0 : (x > 1.0 ? 1.0 : x); }

}  // namespace

const char* moonPhaseName(MoonPhase p) {
  const int i = static_cast<int>(p);
  return (i >= 0 && i < 8) ? kPhaseNames[i] : "?";
}

MoonPhase moonPhaseFromElongation(double elongationDeg) {
  const double wrapped = std::fmod(elongationDeg + 22.5, 360.0);
  const double positive = wrapped < 0.0 ? wrapped + 360.0 : wrapped;
  int idx = static_cast<int>(std::floor(positive / 45.0));
  if (idx < 0) idx = 0;
  if (idx > 7) idx = 7;
  return static_cast<MoonPhase>(idx);
}

MoonGeocentric moonGeocentric(double jde) {
  MoonGeocentric m;
  m.jde = jde;
  const double T = (jde - 2451545.0) / 36525.0;
  m.T = T;
  const double T2 = T * T, T3 = T2 * T, T4 = T3 * T;
  m.Lp = limitDegrees(218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3 / 538841.0 - T4 / 65194000.0);
  m.D = limitDegrees(297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3 / 545868.0 - T4 / 113065000.0);
  m.M = limitDegrees(357.5291092 + 35999.0502909 * T - 0.0001536 * T2 + T3 / 24490000.0);
  m.Mp = limitDegrees(134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3 / 69699.0 - T4 / 14712000.0);
  m.F = limitDegrees(93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3 / 3526000.0 + T4 / 863310000.0);
  const double A1 = limitDegrees(119.75 + 131.849 * T);
  const double A2 = limitDegrees(53.09 + 479264.290 * T);
  const double A3 = limitDegrees(313.45 + 481266.484 * T);
  m.E = 1.0 - 0.002516 * T - 0.0000074 * T * T;
  const double E2 = m.E * m.E;

  double sl = 0.0, sr = 0.0, sb = 0.0;
  for (int i = 0; i < kMoonLrCount; ++i) {
    const int32_t d = kMoonLr[i][0], mm = kMoonLr[i][1], mp = kMoonLr[i][2], f = kMoonLr[i][3];
    const double arg = (d * m.D + mm * m.M + mp * m.Mp + f * m.F) * kDeg;
    const int32_t am = mm < 0 ? -mm : mm;
    const double k = am == 1 ? m.E : (am == 2 ? E2 : 1.0);
    sl += k * kMoonLr[i][4] * std::sin(arg);
    sr += k * kMoonLr[i][5] * std::cos(arg);
  }
  for (int i = 0; i < kMoonBCount; ++i) {
    const int32_t d = kMoonB[i][0], mm = kMoonB[i][1], mp = kMoonB[i][2], f = kMoonB[i][3];
    const double arg = (d * m.D + mm * m.M + mp * m.Mp + f * m.F) * kDeg;
    const int32_t am = mm < 0 ? -mm : mm;
    const double k = am == 1 ? m.E : (am == 2 ? E2 : 1.0);
    sb += k * kMoonB[i][4] * std::sin(arg);
  }
  sl += 3958.0 * std::sin(A1 * kDeg) + 1962.0 * std::sin((m.Lp - m.F) * kDeg) + 318.0 * std::sin(A2 * kDeg);
  sb += -2235.0 * std::sin(m.Lp * kDeg) + 382.0 * std::sin(A3 * kDeg) +
        175.0 * std::sin((A1 - m.F) * kDeg) + 175.0 * std::sin((A1 + m.F) * kDeg) +
        127.0 * std::sin((m.Lp - m.Mp) * kDeg) - 115.0 * std::sin((m.Lp + m.Mp) * kDeg);
  m.sigmaL = sl;
  m.sigmaB = sb;
  m.sigmaR = sr;

  m.longitude = limitDegrees(m.Lp + sl / 1e6);
  m.latitude = sb / 1e6;
  m.distanceKm = 385000.56 + sr / 1000.0;
  m.parallaxDeg = std::asin(kEarthRadiusKm / m.distanceKm) * kRad;
  double deltaEps = 0.0;
  nutation(T, m.deltaPsi, deltaEps);
  m.epsilon = trueEclipticObliquity(T / 10.0, deltaEps);
  m.apparentLongitude = limitDegrees(m.longitude + m.deltaPsi);
  m.rightAscension = geocentricRightAscension(m.apparentLongitude, m.epsilon, m.latitude);
  m.declination = geocentricDeclination(m.latitude, m.epsilon, m.apparentLongitude);
  return m;
}

void moonIllumination(const MoonGeocentric& moon, const GeocentricSun& sun, double& k,
                      double& phaseAngleDeg, double& elongationDeg) {
  const double a0 = sun.alpha * kDeg, d0 = sun.delta * kDeg;
  const double a = moon.rightAscension * kDeg, d = moon.declination * kDeg;
  const double cosPsi =
      clampUnit(std::sin(d0) * std::sin(d) + std::cos(d0) * std::cos(d) * std::cos(a0 - a));
  const double psi = std::acos(cosPsi);
  const double rKm = sun.R * kAuKm;
  const double i = std::atan2(rKm * std::sin(psi), moon.distanceKm - rKm * std::cos(psi));
  k = (1.0 + std::cos(i)) / 2.0;
  phaseAngleDeg = i * kRad;
  elongationDeg = limitDegrees(moon.apparentLongitude - sun.lambda);
}

MoonPosition moonPositionJd(double jd, const Observer& obs, double deltaT_s) {
  MoonPosition p;
  const double jde = julianEphemerisDay(jd, deltaT_s);
  p.geocentric = moonGeocentric(jde);
  const MoonGeocentric& m = p.geocentric;
  const GeocentricSun s = geocentricSun(jd, deltaT_s);
  const double h = observerHourAngle(s.nu, obs.longitudeDeg, m.rightAscension);
  double da = 0.0, dp = 0.0, hp = 0.0;
  topocentricCorrections(obs.latitudeDeg, obs.elevationM, m.parallaxDeg, h, m.declination, da, dp, hp);
  p.elevationUncorrected = topocentricElevationAngle(obs.latitudeDeg, dp, hp);
  p.semidiameterDeg = std::asin(kMoonRadiusRatio * std::sin(m.parallaxDeg * kDeg)) * kRad;
  const double de = atmosphericRefractionCorrection(obs.pressureMbar, obs.temperatureC,
                                                    p.elevationUncorrected, obs.atmosRefractDeg,
                                                    p.semidiameterDeg);
  p.elevation = p.elevationUncorrected + de;
  p.zenith = 90.0 - p.elevation;
  p.azimuth = limitDegrees(topocentricAzimuthAstro(hp, obs.latitudeDeg, dp) + 180.0);
  p.distanceKm = m.distanceKm;
  moonIllumination(m, s, p.illuminatedFraction, p.phaseAngleDeg, p.elongationDeg);
  p.waxing = p.elongationDeg < 180.0;
  p.phase = moonPhaseFromElongation(p.elongationDeg);
  p.ageFraction = p.elongationDeg / 360.0;
  return p;
}

MoonPosition moonPositionUnix(double unix_s, const Observer& obs) {
  return moonPositionJd(nytime::julianDayFromUnix(unix_s), obs, nytime::deltaTSeconds(unix_s));
}

}  // namespace astro
}  // namespace nycsim
