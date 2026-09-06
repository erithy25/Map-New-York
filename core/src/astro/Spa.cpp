#include "nycsim/astro/Spa.h"

#include <algorithm>
#include <cmath>

namespace nycsim {
namespace astro {

namespace {
#include "SpaTables.inc"  // NOLINT(bugprone-suspicious-include) - generated numeric tables

double periodicSum(const double (*terms)[3], int count, double jme) {
  double total = 0.0;
  for (int i = 0; i < count; ++i) total += terms[i][0] * std::cos(terms[i][1] + terms[i][2] * jme);
  return total;
}

double series(const double (*terms)[3], const int* counts, int groups, double jme) {
  double total = 0.0;
  double jmePow = 1.0;
  int offset = 0;
  for (int g = 0; g < groups; ++g) {
    total += periodicSum(terms + offset, counts[g], jme) * jmePow;
    offset += counts[g];
    jmePow *= jme;
  }
  return total / 1e8;
}

double thirdOrderPolynomial(double a, double b, double c, double d, double x) {
  return ((a * x + b) * x + c) * x + d;
}

/// SPA A.2 three-point interpolation; `isRa` handles the 360-degree wrap of right ascension.
double rtsInterp(double vPrev, double v0, double vNext, double n, bool isRa) {
  double a = v0 - vPrev;
  double b = vNext - v0;
  if (isRa) {
    if (std::fabs(a) >= 2.0) a = limitZeroToOne(a);
    if (std::fabs(b) >= 2.0) b = limitZeroToOne(b);
  }
  const double c = b - a;
  return v0 + n * (a + b + c * n) / 2.0;
}

/// acos of the SPA A.2 sunrise hour angle; returns false when the Sun never reaches h0 that day.
bool approxSunHourAngleH0(double lat, double delta0, double h0Prime, double& out) {
  const double latR = lat * kDeg;
  const double dR = delta0 * kDeg;
  const double arg =
      (std::sin(h0Prime * kDeg) - std::sin(latR) * std::sin(dR)) / (std::cos(latR) * std::cos(dR));
  if (!(arg >= -1.0 && arg <= 1.0)) return false;
  out = std::acos(arg) * kRad;
  return true;
}

}  // namespace

// ---- angle helpers --------------------------------------------------------------------------------

double limitDegrees(double deg) {
  double d = std::fmod(deg, 360.0);
  return d < 0.0 ? d + 360.0 : d;
}

double limitDegrees180pm(double deg) {
  double d = std::fmod(deg, 360.0);
  if (d < -180.0) d += 360.0;
  else if (d >= 180.0) d -= 360.0;
  return d;
}

double limitZeroToOne(double x) { return x - std::floor(x); }

// ---- SPA building blocks --------------------------------------------------------------------------

double julianCentury(double jd) { return (jd - 2451545.0) / 36525.0; }

double julianEphemerisDay(double jd, double deltaT_s) { return jd + deltaT_s / 86400.0; }

double earthHeliocentricLongitude(double jme) {
  return limitDegrees(series(kLTerms, kLTermsCounts, kLTermsGroupCount, jme) * kRad);
}

double earthHeliocentricLatitude(double jme) {
  return series(kBTerms, kBTermsCounts, kBTermsGroupCount, jme) * kRad;
}

double earthRadiusVector(double jme) {
  return series(kRTerms, kRTermsCounts, kRTermsGroupCount, jme);
}

void nutation(double jce, double& deltaPsi, double& deltaEpsilon) {
  const double x[5] = {
      thirdOrderPolynomial(1.0 / 189474.0, -0.0019142, 445267.11148, 297.85036, jce),
      thirdOrderPolynomial(-1.0 / 300000.0, -0.0001603, 35999.05034, 357.52772, jce),
      thirdOrderPolynomial(1.0 / 56250.0, 0.0086972, 477198.867398, 134.96298, jce),
      thirdOrderPolynomial(1.0 / 327270.0, -0.0036825, 483202.017538, 93.27191, jce),
      thirdOrderPolynomial(1.0 / 450000.0, 0.0020708, -1934.136261, 125.04452, jce),
  };
  double sumPsi = 0.0;
  double sumEps = 0.0;
  for (int i = 0; i < kNutationCount; ++i) {
    double arg = 0.0;
    for (int j = 0; j < 5; ++j) arg += x[j] * kNutationY[i][j];
    arg *= kDeg;
    sumPsi += (kNutationPE[i][0] + kNutationPE[i][1] * jce) * std::sin(arg);
    sumEps += (kNutationPE[i][2] + kNutationPE[i][3] * jce) * std::cos(arg);
  }
  deltaPsi = sumPsi / 36000000.0;
  deltaEpsilon = sumEps / 36000000.0;
}

double meanEclipticObliquityArcsec(double jme) {
  const double u = jme / 10.0;
  return 84381.448 +
         u * (-4680.93 +
              u * (-1.55 +
                   u * (1999.25 +
                        u * (-51.38 +
                             u * (-249.67 +
                                  u * (-39.05 + u * (7.12 + u * (27.87 + u * (5.79 + u * 2.45)))))))));
}

double trueEclipticObliquity(double jme, double deltaEpsilon) {
  return meanEclipticObliquityArcsec(jme) / 3600.0 + deltaEpsilon;
}

double greenwichMeanSiderealTime(double jd, double jc) {
  return limitDegrees(280.46061837 + 360.98564736629 * (jd - 2451545.0) +
                      jc * jc * (0.000387933 - jc / 38710000.0));
}

double geocentricRightAscension(double lambda, double epsilon, double beta) {
  const double lr = lambda * kDeg, er = epsilon * kDeg, br = beta * kDeg;
  return limitDegrees(
      std::atan2(std::sin(lr) * std::cos(er) - std::tan(br) * std::sin(er), std::cos(lr)) * kRad);
}

double geocentricDeclination(double beta, double epsilon, double lambda) {
  const double br = beta * kDeg, er = epsilon * kDeg;
  return std::asin(std::sin(br) * std::cos(er) + std::cos(br) * std::sin(er) * std::sin(lambda * kDeg)) *
         kRad;
}

double observerHourAngle(double nu, double longitudeDeg, double alpha) {
  return limitDegrees(nu + longitudeDeg - alpha);
}

double equatorialHorizontalParallax(double r_au) { return 8.794 / (3600.0 * r_au); }

void topocentricCorrections(double latDeg, double elevM, double xi, double h, double delta,
                            double& deltaAlpha, double& deltaPrime, double& hPrime) {
  const double latR = latDeg * kDeg, xiR = xi * kDeg, hR = h * kDeg, dR = delta * kDeg;
  const double u = std::atan(0.99664719 * std::tan(latR));
  const double x = std::cos(u) + elevM * std::cos(latR) / 6378140.0;
  const double y = 0.99664719 * std::sin(u) + elevM * std::sin(latR) / 6378140.0;
  const double daR = std::atan2(-x * std::sin(xiR) * std::sin(hR),
                                std::cos(dR) - x * std::sin(xiR) * std::cos(hR));
  deltaPrime = std::atan2((std::sin(dR) - y * std::sin(xiR)) * std::cos(daR),
                          std::cos(dR) - x * std::sin(xiR) * std::cos(hR)) *
               kRad;
  deltaAlpha = daR * kRad;
  hPrime = h - deltaAlpha;
}

double topocentricElevationAngle(double latDeg, double deltaPrime, double hPrime) {
  const double latR = latDeg * kDeg, dR = deltaPrime * kDeg;
  return std::asin(std::sin(latR) * std::sin(dR) +
                   std::cos(latR) * std::cos(dR) * std::cos(hPrime * kDeg)) *
         kRad;
}

double atmosphericRefractionCorrection(double pressureMbar, double temperatureC, double e0,
                                       double atmosRefractDeg, double bodyRadiusDeg) {
  if (e0 >= -(bodyRadiusDeg + atmosRefractDeg)) {
    return (pressureMbar / 1010.0) * (283.0 / (273.0 + temperatureC)) * 1.02 /
           (60.0 * std::tan((e0 + 10.3 / (e0 + 5.11)) * kDeg));
  }
  return 0.0;
}

double topocentricAzimuthAstro(double hPrime, double latDeg, double deltaPrime) {
  const double hR = hPrime * kDeg, latR = latDeg * kDeg, dR = deltaPrime * kDeg;
  return limitDegrees(
      std::atan2(std::sin(hR), std::cos(hR) * std::sin(latR) - std::tan(dR) * std::cos(latR)) * kRad);
}

GeocentricSun geocentricSun(double jd, double deltaT_s) {
  GeocentricSun g;
  g.jd = jd;
  g.jc = julianCentury(jd);
  g.jde = julianEphemerisDay(jd, deltaT_s);
  g.jce = julianCentury(g.jde);
  g.jme = g.jce / 10.0;
  g.L = earthHeliocentricLongitude(g.jme);
  g.B = earthHeliocentricLatitude(g.jme);
  g.R = earthRadiusVector(g.jme);
  g.theta = limitDegrees(g.L + 180.0);
  g.beta = -g.B;
  nutation(g.jce, g.deltaPsi, g.deltaEpsilon);
  g.epsilon = trueEclipticObliquity(g.jme, g.deltaEpsilon);
  g.deltaTau = -20.4898 / (3600.0 * g.R);
  g.lambda = limitDegrees(g.theta + g.deltaPsi + g.deltaTau);
  g.nu0 = greenwichMeanSiderealTime(jd, g.jc);
  g.nu = g.nu0 + g.deltaPsi * std::cos(g.epsilon * kDeg);
  g.alpha = geocentricRightAscension(g.lambda, g.epsilon, g.beta);
  g.delta = geocentricDeclination(g.beta, g.epsilon, g.lambda);
  return g;
}

SolarPosition solarPositionJd(double jd, const Observer& obs, double deltaT_s) {
  SolarPosition p;
  p.jd = jd;
  p.deltaTS = deltaT_s;
  p.geocentric = geocentricSun(jd, deltaT_s);
  const GeocentricSun& g = p.geocentric;
  p.hourAngle = observerHourAngle(g.nu, obs.longitudeDeg, g.alpha);
  p.xi = equatorialHorizontalParallax(g.R);
  double da = 0.0;
  topocentricCorrections(obs.latitudeDeg, obs.elevationM, p.xi, p.hourAngle, g.delta, da,
                         p.deltaPrime, p.hourAnglePrime);
  p.alphaPrime = limitDegrees(g.alpha + da);
  p.elevationUncorrected = topocentricElevationAngle(obs.latitudeDeg, p.deltaPrime, p.hourAnglePrime);
  p.refraction = atmosphericRefractionCorrection(obs.pressureMbar, obs.temperatureC,
                                                 p.elevationUncorrected, obs.atmosRefractDeg);
  p.elevation = p.elevationUncorrected + p.refraction;
  p.zenith = 90.0 - p.elevation;
  p.azimuthAstro = topocentricAzimuthAstro(p.hourAnglePrime, obs.latitudeDeg, p.deltaPrime);
  p.azimuth = limitDegrees(p.azimuthAstro + 180.0);
  p.distanceAu = g.R;
  p.semidiameterDeg = kSunRadiusDeg / g.R;
  return p;
}

SolarPosition solarPositionUnix(double unix_s, const Observer& obs) {
  return solarPositionJd(nytime::julianDayFromUnix(unix_s), obs, nytime::deltaTSeconds(unix_s));
}

// ---- rise / transit / set -------------------------------------------------------------------------

SunEvents sunRiseTransitSet(nytime::Date dateUtc, const Observer& obs, double h0Deg) {
  SunEvents ev;
  ev.dateUtc = dateUtc;
  ev.h0Deg = h0Deg;
  nytime::DateTime midnight;
  midnight.year = dateUtc.year;
  midnight.month = dateUtc.month;
  midnight.day = dateUtc.day;
  const double jd0 = nytime::julianDay(midnight);
  const double deltaT = nytime::deltaTSeconds(nytime::unixFromJulianDay(jd0 + 0.5));

  const double nu = geocentricSun(jd0, 0.0).nu;  // apparent sidereal time at 0 UT
  double alpha[3];
  double delta[3];
  for (int i = 0; i < 3; ++i) {
    const GeocentricSun g = geocentricSun(jd0 + (i - 1), 0.0);  // SPA uses Delta-T = 0 here
    alpha[i] = g.alpha;
    delta[i] = g.delta;
  }
  const double lat = obs.latitudeDeg;
  const double lon = obs.longitudeDeg;
  const double m0 = limitZeroToOne((alpha[1] - lon - nu) / 360.0);
  double h0 = 0.0;
  const bool bracketed = approxSunHourAngleH0(lat, delta[1], h0Deg, h0);

  double m[3] = {m0, 0.0, 0.0};
  bool valid[3] = {true, false, false};
  if (bracketed) {
    m[1] = limitZeroToOne(m0 - h0 / 360.0);
    m[2] = limitZeroToOne(m0 + h0 / 360.0);
    valid[1] = valid[2] = true;
  }

  double hPrime[3] = {0.0, 0.0, 0.0};
  double hAlt[3] = {0.0, 0.0, 0.0};
  double dPrime[3] = {0.0, 0.0, 0.0};
  for (int i = 0; i < 3; ++i) {
    if (!valid[i]) continue;
    const double nuI = nu + 360.985647 * m[i];
    const double n = m[i] + deltaT / 86400.0;
    const double aI = rtsInterp(alpha[0], alpha[1], alpha[2], n, true);
    const double dI = rtsInterp(delta[0], delta[1], delta[2], n, false);
    hPrime[i] = limitDegrees180pm(nuI + lon - aI);
    dPrime[i] = dI;
    hAlt[i] = topocentricElevationAngle(lat, dI, hPrime[i]);
  }

  ev.transitUnix = nytime::unixFromJulianDay(jd0 + (m[0] - hPrime[0] / 360.0));
  for (int i = 1; i < 3; ++i) {
    if (!valid[i]) continue;
    const double frac = m[i] + (hAlt[i] - h0Deg) / (360.0 * std::cos(dPrime[i] * kDeg) *
                                                    std::cos(lat * kDeg) * std::sin(hPrime[i] * kDeg));
    if (i == 1) {
      ev.sunriseUnix = nytime::unixFromJulianDay(jd0 + frac);
      ev.hasSunrise = true;
    } else {
      ev.sunsetUnix = nytime::unixFromJulianDay(jd0 + frac);
      ev.hasSunset = true;
    }
  }
  return ev;
}

Result<SunEvents> sunEventsLocal(nytime::Date localDate, const Observer& obs, double h0Deg) {
  SunEvents out;
  out.dateUtc = localDate;
  out.h0Deg = h0Deg;
  bool haveTransit = false;
  for (int offset = 0; offset < 2; ++offset) {
    const nytime::Date d =
        nytime::civilFromDays(nytime::daysFromCivil(localDate.year, localDate.month, localDate.day) + offset);
    const SunEvents ev = sunRiseTransitSet(d, obs, h0Deg);
    struct Cand {
      bool has;
      double t;
      int which;  // 0 sunrise, 1 transit, 2 sunset
    };
    const Cand cands[3] = {{ev.hasSunrise, ev.sunriseUnix, 0}, {true, ev.transitUnix, 1},
                           {ev.hasSunset, ev.sunsetUnix, 2}};
    for (const Cand& c : cands) {
      if (!c.has) continue;
      if (c.which == 0 && out.hasSunrise) continue;
      if (c.which == 1 && haveTransit) continue;
      if (c.which == 2 && out.hasSunset) continue;
      const Result<nytime::Offset> off = nytime::nyOffset(c.t);
      if (!off) return off.error();
      const nytime::DateTime local = nytime::civilFromUnix(c.t + off.value().seconds);
      if (local.year != localDate.year || local.month != localDate.month || local.day != localDate.day) {
        continue;
      }
      if (c.which == 0) {
        out.sunriseUnix = c.t;
        out.hasSunrise = true;
      } else if (c.which == 1) {
        out.transitUnix = c.t;
        haveTransit = true;
      } else {
        out.sunsetUnix = c.t;
        out.hasSunset = true;
      }
    }
  }
  if (!haveTransit) {
    // Cannot happen at NYC latitude; keep the UT-day transit rather than reporting no transit.
    out.transitUnix = sunRiseTransitSet(localDate, obs, h0Deg).transitUnix;
  }
  return out;
}

// ---- Manhattanhenge -------------------------------------------------------------------------------

Result<SunsetAzimuth> timeOfEveningElevation(nytime::Date localDate, double elevationDeg,
                                             const Observer& obs, double tolerance_s) {
  NYCSIM_TRY(ev, sunEventsLocal(localDate, obs));
  if (!ev.hasSunset) {
    return fail(ErrorCode::NotFound, "astro: the Sun does not set on that local date");
  }
  double lo = ev.transitUnix;
  double hi = ev.sunsetUnix + 90.0 * 60.0;
  const double deltaT = nytime::deltaTSeconds(lo);
  auto f = [&](double t) {
    return solarPositionJd(nytime::julianDayFromUnix(t), obs, deltaT).elevation - elevationDeg;
  };
  if (f(lo) < 0.0 || f(hi) > 0.0) {
    return fail(ErrorCode::NoConvergence, "astro: target elevation not bracketed between transit and sunset");
  }
  // The apparent elevation is strictly decreasing on [transit, sunset + 90 min] at NYC latitude.
  for (int guard = 0; guard < 200 && hi - lo > tolerance_s; ++guard) {
    const double mid = 0.5 * (lo + hi);
    if (f(mid) > 0.0) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  const double t = 0.5 * (lo + hi);
  const SolarPosition p = solarPositionJd(nytime::julianDayFromUnix(t), obs, deltaT);
  SunsetAzimuth sa;
  sa.localDate = localDate;
  sa.unix_s = t;
  sa.elevationDeg = elevationDeg;
  sa.azimuthDeg = p.azimuth;
  sa.deltaFromGridDeg = p.azimuth - kManhattanStreetSunsetAzimuthDeg;
  return sa;
}

uint32_t manhattanhenge(int32_t year, const Observer& obs, ManhattanhengeEvent* out, uint32_t cap,
                        double toleranceDeg) {
  if (!out || cap == 0) return 0;
  const int64_t first = nytime::daysFromCivil(year, 5, 1);
  const int64_t last = nytime::daysFromCivil(year, 8, 15);
  const int64_t solstice = nytime::daysFromCivil(year, 6, 21);
  uint32_t n = 0;
  for (int64_t day = first; day <= last && n < cap; ++day) {
    const nytime::Date d = nytime::civilFromDays(day);
    const double elevations[2] = {kFullSunElevationDeg, kHalfSunElevationDeg};
    for (int k = 0; k < 2 && n < cap; ++k) {
      const Result<SunsetAzimuth> sa = timeOfEveningElevation(d, elevations[k], obs);
      if (!sa) continue;
      if (std::fabs(sa.value().deltaFromGridDeg) > toleranceDeg) continue;
      ManhattanhengeEvent e;
      e.full = k == 0;
      e.localDate = d;
      e.unix_s = sa.value().unix_s;
      e.azimuthDeg = sa.value().azimuthDeg;
      e.deltaFromGridDeg = sa.value().deltaFromGridDeg;
      out[n++] = e;
    }
  }
  // Flag the best match of each kind in each season (before / from the June solstice).
  for (int kind = 0; kind < 2; ++kind) {
    for (int season = 0; season < 2; ++season) {
      uint32_t best = cap;
      double bestDelta = 1e300;
      for (uint32_t i = 0; i < n; ++i) {
        const ManhattanhengeEvent& e = out[i];
        if (e.full != (kind == 0)) continue;
        const int64_t dd = nytime::daysFromCivil(e.localDate.year, e.localDate.month, e.localDate.day);
        const bool before = dd < solstice;
        if (before != (season == 0)) continue;
        if (std::fabs(e.deltaFromGridDeg) < bestDelta) {
          bestDelta = std::fabs(e.deltaFromGridDeg);
          best = i;
        }
      }
      if (best < n) out[best].bestInSeason = true;
    }
  }
  // Sort by (date, kind) — the list is short, an insertion sort keeps this allocation free.
  for (uint32_t i = 1; i < n; ++i) {
    ManhattanhengeEvent key = out[i];
    const int64_t keyDay = nytime::daysFromCivil(key.localDate.year, key.localDate.month, key.localDate.day);
    uint32_t j = i;
    while (j > 0) {
      const ManhattanhengeEvent& prev = out[j - 1];
      const int64_t prevDay = nytime::daysFromCivil(prev.localDate.year, prev.localDate.month, prev.localDate.day);
      const bool greater = prevDay > keyDay || (prevDay == keyDay && !prev.full && key.full);
      if (!greater) break;
      out[j] = out[j - 1];
      --j;
    }
    out[j] = key;
  }
  return n;
}

}  // namespace astro
}  // namespace nycsim
