"""Sun and Moon for the simulation sky.

* Sun: NREL Solar Position Algorithm (Reda & Andreas, *Solar Energy* 76 (2004) 577–589, corrected
  2008; NREL/TP-560-34302). Full implementation: Earth heliocentric VSOP87-derived series (L0–L5, B0–B1,
  R0–R4), IAU 1980 nutation (63 terms), true obliquity, aberration, apparent sidereal time,
  geocentric → topocentric parallax, atmospheric refraction, azimuth/zenith and the rise/transit/set
  procedure of SPA Appendix A.2. Stated accuracy ±0.0003° (years −2000…6000) given exact ΔT.
* Moon: Meeus, *Astronomical Algorithms* 2nd ed., ch. 47 (full 60+60 periodic terms, ±10″ in
  longitude, ±4″ in latitude, ±4 km in distance), ch. 48 illuminated fraction / phase angle, plus the
  same topocentric+refraction chain as the Sun.
* Manhattanhenge: date search on the setting-Sun azimuth against the Manhattan street grid.

Angles are degrees unless a name ends in ``_rad``. Azimuth is compass (0 = north, 90 = east) to match
DATA_CONTRACTS ``*_heading`` convention; the SPA "astronomers' azimuth" (from south) is exposed as
``azimuth_astro``. Every function is deterministic and side-effect free so the C++ port can be diffed
against these outputs.
"""
from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass
from typing import Final, Iterable, Sequence

from . import timesync

# --------------------------------------------------------------------------- constants
SUN_RADIUS_DEG: Final = 0.26667  # SPA constant (mean apparent semi-diameter)
ATMOS_REFRACT_HORIZON_DEG: Final = 0.5667  # SPA default refraction at the horizon
RISE_SET_H0_DEG: Final = -(SUN_RADIUS_DEG + ATMOS_REFRACT_HORIZON_DEG)  # -0.83337 (upper limb, USNO convention)
EARTH_RADIUS_KM: Final = 6378.14
AU_KM: Final = 149597870.7
STANDARD_PRESSURE_MBAR: Final = 1013.25
STANDARD_TEMPERATURE_C: Final = 15.0

DEG: Final = math.pi / 180.0
RAD: Final = 180.0 / math.pi

# --------------------------------------------------------------------------- SPA periodic terms (Reda & Andreas Table A4.2)
# Each row: (A, B, C) with term = A * cos(B + C * JME)
L_TERMS: Final[tuple[tuple[tuple[float, float, float], ...], ...]] = (
    (  # L0
        (175347046.0, 0.0, 0.0), (3341656.0, 4.6692568, 6283.07585), (34894.0, 4.6261, 12566.1517), (3497.0, 2.7441, 5753.3849),
        (3418.0, 2.8289, 3.5231), (3136.0, 3.6277, 77713.7715), (2676.0, 4.4181, 7860.4194), (2343.0, 6.1352, 3930.2097),
        (1324.0, 0.7425, 11506.7698), (1273.0, 2.0371, 529.691), (1199.0, 1.1096, 1577.3435), (990.0, 5.233, 5884.927),
        (902.0, 2.045, 26.298), (857.0, 3.508, 398.149), (780.0, 1.179, 5223.694), (753.0, 2.533, 5507.553),
        (505.0, 4.583, 18849.228), (492.0, 4.205, 775.523), (357.0, 2.92, 0.067), (317.0, 5.849, 11790.629),
        (284.0, 1.899, 796.298), (271.0, 0.315, 10977.079), (243.0, 0.345, 5486.778), (206.0, 4.806, 2544.314),
        (205.0, 1.869, 5573.143), (202.0, 2.458, 6069.777), (156.0, 0.833, 213.299), (132.0, 3.411, 2942.463),
        (126.0, 1.083, 20.775), (115.0, 0.645, 0.98), (103.0, 0.636, 4694.003), (102.0, 0.976, 15720.839),
        (102.0, 4.267, 7.114), (99.0, 6.21, 2146.17), (98.0, 0.68, 155.42), (86.0, 5.98, 161000.69),
        (85.0, 1.3, 6275.96), (85.0, 3.67, 71430.7), (80.0, 1.81, 17260.15), (79.0, 3.04, 12036.46),
        (75.0, 1.76, 5088.63), (74.0, 3.5, 3154.69), (74.0, 4.68, 801.82), (70.0, 0.83, 9437.76),
        (62.0, 3.98, 8827.39), (61.0, 1.82, 7084.9), (57.0, 2.78, 6286.6), (56.0, 4.39, 14143.5),
        (56.0, 3.47, 6279.55), (52.0, 0.19, 12139.55), (52.0, 1.33, 1748.02), (51.0, 0.28, 5856.48),
        (49.0, 0.49, 1194.45), (41.0, 5.37, 8429.24), (41.0, 2.4, 19651.05), (39.0, 6.17, 10447.39),
        (37.0, 6.04, 10213.29), (37.0, 2.57, 1059.38), (36.0, 1.71, 2352.87), (36.0, 1.78, 6812.77),
        (33.0, 0.59, 17789.85), (30.0, 0.44, 83996.85), (30.0, 2.74, 1349.87), (25.0, 3.16, 4690.48),
    ),
    (  # L1
        (628331966747.0, 0.0, 0.0), (206059.0, 2.678235, 6283.07585), (4303.0, 2.6351, 12566.1517), (425.0, 1.59, 3.523),
        (119.0, 5.796, 26.298), (109.0, 2.966, 1577.344), (93.0, 2.59, 18849.23), (72.0, 1.14, 529.69),
        (68.0, 1.87, 398.15), (67.0, 4.41, 5507.55), (59.0, 2.89, 5223.69), (56.0, 2.17, 155.42),
        (45.0, 0.4, 796.3), (36.0, 0.47, 775.52), (29.0, 2.65, 7.11), (21.0, 5.34, 0.98),
        (19.0, 1.85, 5486.78), (19.0, 4.97, 213.3), (17.0, 2.99, 6275.96), (16.0, 0.03, 2544.31),
        (16.0, 1.43, 2146.17), (15.0, 1.21, 10977.08), (12.0, 2.83, 1748.02), (12.0, 3.26, 5088.63),
        (12.0, 5.27, 1194.45), (12.0, 2.08, 4694.0), (11.0, 0.77, 553.57), (10.0, 1.3, 6286.6),
        (10.0, 4.24, 1349.87), (9.0, 2.7, 242.73), (9.0, 5.64, 951.72), (8.0, 5.3, 2352.87),
        (6.0, 2.65, 9437.76), (6.0, 4.67, 4690.48),
    ),
    (  # L2
        (52919.0, 0.0, 0.0), (8720.0, 1.0721, 6283.0758), (309.0, 0.867, 12566.152), (27.0, 0.05, 3.52),
        (16.0, 5.19, 26.3), (16.0, 3.68, 155.42), (10.0, 0.76, 18849.23), (9.0, 2.06, 77713.77),
        (7.0, 0.83, 775.52), (5.0, 4.66, 1577.34), (4.0, 1.03, 7.11), (4.0, 3.44, 5573.14),
        (3.0, 5.14, 796.3), (3.0, 6.05, 5507.55), (3.0, 1.19, 242.73), (3.0, 6.12, 529.69),
        (3.0, 0.31, 398.15), (3.0, 2.28, 553.57), (2.0, 4.38, 5223.69), (2.0, 3.75, 0.98),
    ),
    (  # L3
        (289.0, 5.844, 6283.076), (35.0, 0.0, 0.0), (17.0, 5.49, 12566.15), (3.0, 5.2, 155.42),
        (1.0, 4.72, 3.52), (1.0, 5.3, 18849.23), (1.0, 5.97, 242.73),
    ),
    (  # L4
        (114.0, 3.142, 0.0), (8.0, 5.63, 6283.07), (1.0, 3.84, 12566.15),
    ),
    (  # L5
        (1.0, 3.14, 0.0),
    ),
)

B_TERMS: Final[tuple[tuple[tuple[float, float, float], ...], ...]] = (
    (  # B0
        (280.0, 3.199, 84334.662), (102.0, 5.422, 5507.553), (80.0, 3.88, 5223.69), (44.0, 3.7, 2352.87), (32.0, 4.0, 1577.34),
    ),
    (  # B1
        (9.0, 3.9, 5507.55), (6.0, 1.73, 5223.69),
    ),
)

R_TERMS: Final[tuple[tuple[tuple[float, float, float], ...], ...]] = (
    (  # R0
        (100013989.0, 0.0, 0.0), (1670700.0, 3.0984635, 6283.07585), (13956.0, 3.05525, 12566.1517), (3084.0, 5.1985, 77713.7715),
        (1628.0, 1.1739, 5753.3849), (1576.0, 2.8469, 7860.4194), (925.0, 5.453, 11506.77), (542.0, 4.564, 3930.21),
        (472.0, 3.661, 5884.927), (346.0, 0.964, 5507.553), (329.0, 5.9, 5223.694), (307.0, 0.299, 5573.143),
        (243.0, 4.273, 11790.629), (212.0, 5.847, 1577.344), (186.0, 5.022, 10977.079), (175.0, 3.012, 18849.228),
        (110.0, 5.055, 5486.778), (98.0, 0.89, 6069.78), (86.0, 5.69, 15720.84), (86.0, 1.27, 161000.69),
        (65.0, 0.27, 17260.15), (63.0, 0.92, 529.69), (57.0, 2.01, 83996.85), (56.0, 5.24, 71430.7),
        (49.0, 3.25, 2544.31), (47.0, 2.58, 775.52), (45.0, 5.54, 9437.76), (43.0, 6.01, 6275.96),
        (39.0, 5.36, 4694.0), (38.0, 2.39, 8827.39), (37.0, 0.83, 19651.05), (37.0, 4.9, 12139.55),
        (36.0, 1.67, 12036.46), (35.0, 1.84, 2942.46), (33.0, 0.24, 7084.9), (32.0, 0.18, 5088.63),
        (32.0, 1.78, 398.15), (28.0, 1.21, 6286.6), (28.0, 1.9, 6279.55), (26.0, 4.59, 10447.39),
    ),
    (  # R1
        (103019.0, 1.10749, 6283.07585), (1721.0, 1.0644, 12566.1517), (702.0, 3.142, 0.0), (32.0, 1.02, 18849.23),
        (31.0, 2.84, 5507.55), (25.0, 1.32, 5223.69), (18.0, 1.42, 1577.34), (10.0, 5.91, 10977.08),
        (9.0, 1.42, 6275.96), (9.0, 0.27, 5486.78),
    ),
    (  # R2
        (4359.0, 5.7846, 6283.0758), (124.0, 5.579, 12566.152), (12.0, 3.14, 0.0), (9.0, 3.63, 77713.77),
        (6.0, 1.87, 5573.14), (3.0, 5.47, 18849.23),
    ),
    (  # R3
        (145.0, 4.273, 6283.076), (7.0, 3.92, 12566.15),
    ),
    (  # R4
        (4.0, 2.56, 6283.08),
    ),
)

# Nutation (IAU 1980, 63 terms). Y: multipliers of X0..X4; PE: (a, b, c, d) in 0.0001 arcsec.
NUTATION_Y: Final[tuple[tuple[int, int, int, int, int], ...]] = (
    (0, 0, 0, 0, 1), (-2, 0, 0, 2, 2), (0, 0, 0, 2, 2), (0, 0, 0, 0, 2), (0, 1, 0, 0, 0), (0, 0, 1, 0, 0), (-2, 1, 0, 2, 2),
    (0, 0, 0, 2, 1), (0, 0, 1, 2, 2), (-2, -1, 0, 2, 2), (-2, 0, 1, 0, 0), (-2, 0, 0, 2, 1), (0, 0, -1, 2, 2), (2, 0, 0, 0, 0),
    (0, 0, 1, 0, 1), (2, 0, -1, 2, 2), (0, 0, -1, 0, 1), (0, 0, 1, 2, 1), (-2, 0, 2, 0, 0), (0, 0, -2, 2, 1), (2, 0, 0, 2, 2),
    (0, 0, 2, 2, 2), (0, 0, 2, 0, 0), (-2, 0, 1, 2, 2), (0, 0, 0, 2, 0), (-2, 0, 0, 2, 0), (0, 0, -1, 2, 1), (0, 2, 0, 0, 0),
    (2, 0, -1, 0, 1), (-2, 2, 0, 2, 2), (0, 1, 0, 0, 1), (-2, 0, 1, 0, 1), (0, -1, 0, 0, 1), (0, 0, 2, -2, 0), (2, 0, -1, 2, 1),
    (2, 0, 1, 2, 2), (0, 1, 0, 2, 2), (-2, 1, 1, 0, 0), (0, -1, 0, 2, 2), (2, 0, 0, 2, 1), (2, 0, 1, 0, 0), (-2, 0, 2, 2, 2),
    (-2, 0, 1, 2, 1), (2, 0, -2, 0, 1), (2, 0, 0, 0, 1), (0, -1, 1, 0, 0), (-2, -1, 0, 2, 1), (-2, 0, 0, 0, 1), (0, 0, 2, 2, 1),
    (-2, 0, 2, 0, 1), (-2, 1, 0, 2, 1), (0, 0, 1, -2, 0), (-1, 0, 1, 0, 0), (-2, 1, 0, 0, 0), (1, 0, 0, 0, 0), (0, 0, 1, 2, 0),
    (0, 0, -2, 2, 2), (-1, -1, 1, 0, 0), (0, 1, 1, 0, 0), (0, -1, 1, 2, 2), (2, -1, -1, 2, 2), (0, 0, 3, 2, 2), (2, -1, 0, 2, 2),
)
NUTATION_PE: Final[tuple[tuple[float, float, float, float], ...]] = (
    (-171996, -174.2, 92025, 8.9), (-13187, -1.6, 5736, -3.1), (-2274, -0.2, 977, -0.5), (2062, 0.2, -895, 0.5),
    (1426, -3.4, 54, -0.1), (712, 0.1, -7, 0), (-517, 1.2, 224, -0.6), (-386, -0.4, 200, 0), (-301, 0, 129, -0.1),
    (217, -0.5, -95, 0.3), (-158, 0, 0, 0), (129, 0.1, -70, 0), (123, 0, -53, 0), (63, 0, 0, 0), (63, 0.1, -33, 0),
    (-59, 0, 26, 0), (-58, -0.1, 32, 0), (-51, 0, 27, 0), (48, 0, 0, 0), (46, 0, -24, 0), (-38, 0, 16, 0), (-31, 0, 13, 0),
    (29, 0, 0, 0), (29, 0, -12, 0), (26, 0, 0, 0), (-22, 0, 0, 0), (21, 0, -10, 0), (17, -0.1, 0, 0), (16, 0, -8, 0),
    (-16, 0.1, 7, 0), (-15, 0, 9, 0), (-13, 0, 7, 0), (-12, 0, 6, 0), (11, 0, 0, 0), (-10, 0, 5, 0), (-8, 0, 3, 0),
    (7, 0, -3, 0), (-7, 0, 0, 0), (-7, 0, 3, 0), (-7, 0, 3, 0), (6, 0, 0, 0), (6, 0, -3, 0), (6, 0, -3, 0), (-6, 0, 3, 0),
    (-6, 0, 3, 0), (5, 0, 0, 0), (-5, 0, 3, 0), (-5, 0, 3, 0), (-5, 0, 3, 0), (4, 0, 0, 0), (4, 0, 0, 0), (4, 0, 0, 0),
    (-4, 0, 0, 0), (-4, 0, 0, 0), (-4, 0, 0, 0), (3, 0, 0, 0), (-3, 0, 0, 0), (-3, 0, 0, 0), (-3, 0, 0, 0), (-3, 0, 0, 0),
    (-3, 0, 0, 0), (-3, 0, 0, 0), (-3, 0, 0, 0),
)


# --------------------------------------------------------------------------- helpers
def limit_degrees(deg: float) -> float:
    """Wrap to [0, 360)."""
    deg = math.fmod(deg, 360.0)
    return deg + 360.0 if deg < 0 else deg


def limit_degrees180pm(deg: float) -> float:
    """Wrap to [-180, 180)."""
    deg = math.fmod(deg, 360.0)
    if deg < -180.0:
        deg += 360.0
    elif deg >= 180.0:
        deg -= 360.0
    return deg


def limit_zero_to_one(x: float) -> float:
    x = x - math.floor(x)
    return x


def third_order_polynomial(a: float, b: float, c: float, d: float, x: float) -> float:
    return ((a * x + b) * x + c) * x + d


# --------------------------------------------------------------------------- time scales
def julian_century(jd: float) -> float:
    return (jd - 2451545.0) / 36525.0


def julian_ephemeris_day(jd: float, delta_t_s: float) -> float:
    return jd + delta_t_s / 86400.0


def julian_ephemeris_millennium(jce: float) -> float:
    return jce / 10.0


# --------------------------------------------------------------------------- Earth heliocentric position (SPA 3.2)
def _periodic_sum(terms: Sequence[tuple[float, float, float]], jme: float) -> float:
    return math.fsum(a * math.cos(b + c * jme) for a, b, c in terms)


def _series(term_groups: Sequence[Sequence[tuple[float, float, float]]], jme: float) -> float:
    total = 0.0
    for i, group in enumerate(term_groups):
        total += _periodic_sum(group, jme) * jme**i
    return total / 1e8


def earth_heliocentric_longitude(jme: float) -> float:
    """L in degrees [0, 360)."""
    return limit_degrees(_series(L_TERMS, jme) * RAD)


def earth_heliocentric_latitude(jme: float) -> float:
    """B in degrees."""
    return _series(B_TERMS, jme) * RAD


def earth_radius_vector(jme: float) -> float:
    """R in astronomical units."""
    return _series(R_TERMS, jme)


# --------------------------------------------------------------------------- nutation, obliquity (SPA 3.4, 3.5)
def nutation(jce: float) -> tuple[float, float]:
    """(Δψ longitude, Δε obliquity) in degrees, IAU 1980 series (SPA 3.4)."""
    x = (
        third_order_polynomial(1 / 189474.0, -0.0019142, 445267.11148, 297.85036, jce),
        third_order_polynomial(-1 / 300000.0, -0.0001603, 35999.05034, 357.52772, jce),
        third_order_polynomial(1 / 56250.0, 0.0086972, 477198.867398, 134.96298, jce),
        third_order_polynomial(1 / 327270.0, -0.0036825, 483202.017538, 93.27191, jce),
        third_order_polynomial(1 / 450000.0, 0.0020708, -1934.136261, 125.04452, jce),
    )
    sum_psi = 0.0
    sum_eps = 0.0
    for y, (a, b, c, d) in zip(NUTATION_Y, NUTATION_PE):
        arg = DEG * math.fsum(xi * yi for xi, yi in zip(x, y))
        sum_psi += (a + b * jce) * math.sin(arg)
        sum_eps += (c + d * jce) * math.cos(arg)
    return sum_psi / 36000000.0, sum_eps / 36000000.0


def mean_ecliptic_obliquity_arcsec(jme: float) -> float:
    u = jme / 10.0
    return (84381.448 + u * (-4680.93 + u * (-1.55 + u * (1999.25 + u * (-51.38 + u * (-249.67 + u * (-39.05 + u * (7.12 + u * (27.87 + u * (5.79 + u * 2.45))))))))))


def true_ecliptic_obliquity(jme: float, delta_epsilon: float) -> float:
    return mean_ecliptic_obliquity_arcsec(jme) / 3600.0 + delta_epsilon


# --------------------------------------------------------------------------- aberration, sidereal time (SPA 3.6-3.8)
def aberration_correction(r_au: float) -> float:
    return -20.4898 / (3600.0 * r_au)


def greenwich_mean_sidereal_time(jd: float, jc: float) -> float:
    return limit_degrees(280.46061837 + 360.98564736629 * (jd - 2451545.0) + jc * jc * (0.000387933 - jc / 38710000.0))


def greenwich_apparent_sidereal_time(nu0: float, delta_psi: float, epsilon: float) -> float:
    return nu0 + delta_psi * math.cos(epsilon * DEG)


# --------------------------------------------------------------------------- geocentric sun (SPA 3.9)
def geocentric_right_ascension(lamda: float, epsilon: float, beta: float) -> float:
    lr, er, br = lamda * DEG, epsilon * DEG, beta * DEG
    return limit_degrees(math.atan2(math.sin(lr) * math.cos(er) - math.tan(br) * math.sin(er), math.cos(lr)) * RAD)


def geocentric_declination(beta: float, epsilon: float, lamda: float) -> float:
    br, er = beta * DEG, epsilon * DEG
    return math.asin(math.sin(br) * math.cos(er) + math.cos(br) * math.sin(er) * math.sin(lamda * DEG)) * RAD


@dataclass(frozen=True)
class GeocentricSun:
    jd: float
    jde: float
    jc: float
    jce: float
    jme: float
    L: float  # Earth heliocentric longitude (deg)
    B: float  # Earth heliocentric latitude (deg)
    R: float  # AU
    theta: float  # geocentric longitude (deg)
    beta: float  # geocentric latitude (deg)
    delta_psi: float
    delta_epsilon: float
    epsilon: float  # true obliquity
    delta_tau: float  # aberration
    lamda: float  # apparent sun longitude
    nu0: float  # mean sidereal time at Greenwich
    nu: float  # apparent sidereal time
    alpha: float  # geocentric right ascension
    delta: float  # geocentric declination


def geocentric_sun(jd: float, delta_t_s: float) -> GeocentricSun:
    jc = julian_century(jd)
    jde = julian_ephemeris_day(jd, delta_t_s)
    jce = julian_century(jde)
    jme = julian_ephemeris_millennium(jce)
    L = earth_heliocentric_longitude(jme)
    B = earth_heliocentric_latitude(jme)
    R = earth_radius_vector(jme)
    theta = limit_degrees(L + 180.0)
    beta = -B
    dpsi, deps = nutation(jce)
    eps = true_ecliptic_obliquity(jme, deps)
    dtau = aberration_correction(R)
    lamda = limit_degrees(theta + dpsi + dtau)
    nu0 = greenwich_mean_sidereal_time(jd, jc)
    nu = greenwich_apparent_sidereal_time(nu0, dpsi, eps)
    alpha = geocentric_right_ascension(lamda, eps, beta)
    delta = geocentric_declination(beta, eps, lamda)
    return GeocentricSun(jd, jde, jc, jce, jme, L, B, R, theta, beta, dpsi, deps, eps, dtau, lamda, nu0, nu, alpha, delta)


# --------------------------------------------------------------------------- observer & topocentric (SPA 3.10-3.14)
@dataclass(frozen=True)
class Observer:
    latitude_deg: float  # geodetic, north positive
    longitude_deg: float  # east positive
    elevation_m: float = 0.0
    pressure_mbar: float = STANDARD_PRESSURE_MBAR
    temperature_c: float = STANDARD_TEMPERATURE_C
    atmos_refract_deg: float = ATMOS_REFRACT_HORIZON_DEG  # refraction at the horizon used for the rise/set gate


CENTRAL_PARK: Final = Observer(40.7831, -73.9712, 40.0)
# Manhattanhenge viewpoint: 42nd Street at Tudor City Place overlook looking west along 42nd Street.
TUDOR_CITY_42ND: Final = Observer(40.7489, -73.9711, 20.0)


def observer_hour_angle(nu: float, longitude: float, alpha: float) -> float:
    return limit_degrees(nu + longitude - alpha)


def equatorial_horizontal_parallax(r_au: float) -> float:
    return 8.794 / (3600.0 * r_au)


def topocentric_corrections(lat: float, elev_m: float, xi: float, h: float, delta: float) -> tuple[float, float, float]:
    """Return (Δα, α'−α is Δα, δ', H') given hour angle h and geocentric δ (SPA 3.12/3.13)."""
    lat_r, xi_r, h_r, d_r = lat * DEG, xi * DEG, h * DEG, delta * DEG
    u = math.atan(0.99664719 * math.tan(lat_r))
    x = math.cos(u) + elev_m * math.cos(lat_r) / 6378140.0
    y = 0.99664719 * math.sin(u) + elev_m * math.sin(lat_r) / 6378140.0
    da_r = math.atan2(-x * math.sin(xi_r) * math.sin(h_r), math.cos(d_r) - x * math.sin(xi_r) * math.cos(h_r))
    delta_prime = math.atan2((math.sin(d_r) - y * math.sin(xi_r)) * math.cos(da_r), math.cos(d_r) - x * math.sin(xi_r) * math.cos(h_r)) * RAD
    return da_r * RAD, delta_prime, h - da_r * RAD


def topocentric_elevation_angle(lat: float, delta_prime: float, h_prime: float) -> float:
    lat_r, d_r = lat * DEG, delta_prime * DEG
    return math.asin(math.sin(lat_r) * math.sin(d_r) + math.cos(lat_r) * math.cos(d_r) * math.cos(h_prime * DEG)) * RAD


def atmospheric_refraction_correction(pressure_mbar: float, temperature_c: float, e0: float, atmos_refract: float = ATMOS_REFRACT_HORIZON_DEG, body_radius_deg: float = SUN_RADIUS_DEG) -> float:
    """Δe (deg) — SPA eq. 42 (Bennett/Meeus form); applied only when the body is at or above the refracted horizon."""
    if e0 >= -(body_radius_deg + atmos_refract):
        return (pressure_mbar / 1010.0) * (283.0 / (273.0 + temperature_c)) * 1.02 / (60.0 * math.tan((e0 + 10.3 / (e0 + 5.11)) * DEG))
    return 0.0


def topocentric_azimuth_astro(h_prime: float, lat: float, delta_prime: float) -> float:
    """Azimuth measured westward from south (SPA eq. 44)."""
    h_r, lat_r, d_r = h_prime * DEG, lat * DEG, delta_prime * DEG
    return limit_degrees(math.atan2(math.sin(h_r), math.cos(h_r) * math.sin(lat_r) - math.tan(d_r) * math.cos(lat_r)) * RAD)


@dataclass(frozen=True)
class SolarPosition:
    utc: _dt.datetime
    jd: float
    delta_t_s: float
    geocentric: GeocentricSun
    hour_angle: float  # H (deg)
    xi: float  # equatorial horizontal parallax (deg)
    alpha_prime: float  # topocentric right ascension
    delta_prime: float  # topocentric declination
    hour_angle_prime: float  # H' (deg)
    elevation_uncorrected: float  # e0
    refraction: float  # Δe
    elevation: float  # e = e0 + Δe (apparent, refracted)
    zenith: float  # θ = 90 − e
    azimuth_astro: float  # from south, westward
    azimuth: float  # compass, from north eastward
    distance_au: float
    semidiameter: float  # apparent angular radius (deg)

    def as_dict(self) -> dict:
        return {
            "utc": self.utc.isoformat().replace("+00:00", "Z"),
            "azimuth_deg": self.azimuth,
            "elevation_deg": self.elevation,
            "zenith_deg": self.zenith,
            "elevation_uncorrected_deg": self.elevation_uncorrected,
            "refraction_deg": self.refraction,
            "right_ascension_deg": self.geocentric.alpha,
            "declination_deg": self.geocentric.delta,
            "distance_au": self.distance_au,
            "semidiameter_deg": self.semidiameter,
            "delta_t_s": self.delta_t_s,
        }


def solar_position_jd(jd: float, observer: Observer, delta_t_s: float, utc: _dt.datetime | None = None) -> SolarPosition:
    g = geocentric_sun(jd, delta_t_s)
    h = observer_hour_angle(g.nu, observer.longitude_deg, g.alpha)
    xi = equatorial_horizontal_parallax(g.R)
    da, dp, hp = topocentric_corrections(observer.latitude_deg, observer.elevation_m, xi, h, g.delta)
    e0 = topocentric_elevation_angle(observer.latitude_deg, dp, hp)
    de = atmospheric_refraction_correction(observer.pressure_mbar, observer.temperature_c, e0, observer.atmos_refract_deg)
    e = e0 + de
    az_astro = topocentric_azimuth_astro(hp, observer.latitude_deg, dp)
    return SolarPosition(
        utc=utc if utc is not None else timesync.datetime_from_julian_day(jd),
        jd=jd,
        delta_t_s=delta_t_s,
        geocentric=g,
        hour_angle=h,
        xi=xi,
        alpha_prime=limit_degrees(g.alpha + da),
        delta_prime=dp,
        hour_angle_prime=hp,
        elevation_uncorrected=e0,
        refraction=de,
        elevation=e,
        zenith=90.0 - e,
        azimuth_astro=az_astro,
        azimuth=limit_degrees(az_astro + 180.0),
        distance_au=g.R,
        semidiameter=SUN_RADIUS_DEG / g.R,
    )


def solar_position(utc: _dt.datetime, observer: Observer = CENTRAL_PARK, delta_t_s: float | None = None) -> SolarPosition:
    """Topocentric, refracted Sun position for a UTC instant (naive datetimes are UTC)."""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=_dt.timezone.utc)
    utc = utc.astimezone(_dt.timezone.utc)
    jd = timesync.julian_day(utc)
    if delta_t_s is None:
        delta_t_s = timesync.delta_t_seconds(utc.timestamp())
    return solar_position_jd(jd, observer, delta_t_s, utc)


# --------------------------------------------------------------------------- sunrise / transit / sunset (SPA A.2)
@dataclass(frozen=True)
class SunEvents:
    date_utc: _dt.date  # the UT day evaluated
    sunrise: _dt.datetime | None  # None when the Sun does not rise/set that day
    transit: _dt.datetime
    sunset: _dt.datetime | None
    h0_deg: float

    def as_dict(self) -> dict:
        f = lambda t: None if t is None else t.isoformat().replace("+00:00", "Z")  # noqa: E731
        return {"date_utc": self.date_utc.isoformat(), "sunrise_utc": f(self.sunrise), "transit_utc": f(self.transit), "sunset_utc": f(self.sunset), "h0_deg": self.h0_deg}


def _approx_sun_hour_angle_h0(lat: float, delta0: float, h0_prime: float) -> float | None:
    lat_r, d_r = lat * DEG, delta0 * DEG
    arg = (math.sin(h0_prime * DEG) - math.sin(lat_r) * math.sin(d_r)) / (math.cos(lat_r) * math.cos(d_r))
    if arg < -1.0 or arg > 1.0:
        return None
    return math.acos(arg) * RAD


def _rts_interp(v_prev: float, v0: float, v_next: float, n: float, is_ra: bool) -> float:
    a = v0 - v_prev
    b = v_next - v0
    if is_ra:  # right ascension may wrap through 360
        if abs(a) >= 2.0:
            a = limit_zero_to_one(a)
        if abs(b) >= 2.0:
            b = limit_zero_to_one(b)
    c = b - a
    return v0 + n * (a + b + c * n) / 2.0


def sun_rise_transit_set(date_utc: _dt.date, observer: Observer = CENTRAL_PARK, delta_t_s: float | None = None, h0_deg: float = RISE_SET_H0_DEG) -> SunEvents:
    """Sunrise, solar transit and sunset (UTC) on a UT calendar day per SPA Appendix A.2.

    ``h0_deg`` is the geometric altitude of the Sun's centre at rise/set: −0.8333° (upper limb on the
    horizon with standard refraction) reproduces USNO tables; −6/−12/−18 give civil/nautical/astronomical
    twilight.
    """
    jd0 = timesync.julian_day(_dt.datetime(date_utc.year, date_utc.month, date_utc.day, tzinfo=_dt.timezone.utc))
    if delta_t_s is None:
        delta_t_s = timesync.delta_t_seconds(timesync.unix_from_julian_day(jd0 + 0.5))
    nu = geocentric_sun(jd0, 0.0).nu  # apparent sidereal time at 0 UT
    alpha: list[float] = []
    delta: list[float] = []
    for i in (-1, 0, 1):
        g = geocentric_sun(jd0 + i, 0.0)  # 0h TT of each day (SPA uses ΔT=0 here)
        alpha.append(g.alpha)
        delta.append(g.delta)
    lat, lon = observer.latitude_deg, observer.longitude_deg
    m0 = limit_zero_to_one((alpha[1] - lon - nu) / 360.0)
    h0 = _approx_sun_hour_angle_h0(lat, delta[1], h0_deg)
    if h0 is None:
        m = [m0, None, None]
    else:
        m = [m0, limit_zero_to_one(m0 - h0 / 360.0), limit_zero_to_one(m0 + h0 / 360.0)]
    results: list[float | None] = []
    h_prime = []
    h_alt = []
    dp_list = []
    for i in range(3):
        mi = m[i]
        if mi is None:
            h_prime.append(None)
            h_alt.append(None)
            dp_list.append(None)
            continue
        nu_i = nu + 360.985647 * mi
        n = mi + delta_t_s / 86400.0
        a_i = _rts_interp(alpha[0], alpha[1], alpha[2], n, True)
        d_i = _rts_interp(delta[0], delta[1], delta[2], n, False)
        hp = limit_degrees180pm(nu_i + lon - a_i)
        h_prime.append(hp)
        dp_list.append(d_i)
        h_alt.append(topocentric_elevation_angle(lat, d_i, hp))
    transit_frac = m[0] - h_prime[0] / 360.0
    results.append(transit_frac)
    for i in (1, 2):
        if m[i] is None:
            results.append(None)
            continue
        frac = m[i] + (h_alt[i] - h0_deg) / (360.0 * math.cos(dp_list[i] * DEG) * math.cos(lat * DEG) * math.sin(h_prime[i] * DEG))
        results.append(frac)

    def to_dt(frac: float | None) -> _dt.datetime | None:
        if frac is None:
            return None
        return timesync.datetime_from_julian_day(jd0 + frac)

    return SunEvents(date_utc, to_dt(results[1]), to_dt(results[0]), to_dt(results[2]), h0_deg)


def sun_events_local(local_date: _dt.date, observer: Observer = CENTRAL_PARK, h0_deg: float = RISE_SET_H0_DEG) -> SunEvents:
    """Rise/transit/set that fall on a New York *local* calendar day.

    The UT day whose events are searched is chosen so that the returned instants, converted to
    America/New_York, fall on ``local_date`` (NYC is UTC−4/−5, so the local day's sunset can fall on the
    next UT day). Each of the three events is validated independently.
    """
    out: dict[str, _dt.datetime | None] = {"sunrise": None, "transit": None, "sunset": None}
    for offset in (0, 1):
        ev = sun_rise_transit_set(local_date + _dt.timedelta(days=offset), observer, h0_deg=h0_deg)
        for key in ("sunrise", "transit", "sunset"):
            t = getattr(ev, key)
            if t is None or out[key] is not None:
                continue
            off, _ = timesync.nyc_offset(t.timestamp())
            if (t + _dt.timedelta(seconds=off)).date() == local_date:
                out[key] = t
    if out["transit"] is None:  # cannot happen at NYC latitude; keep the UT-day value rather than fail
        out["transit"] = sun_rise_transit_set(local_date, observer, h0_deg=h0_deg).transit
    return SunEvents(local_date, out["sunrise"], out["transit"], out["sunset"], h0_deg)


# --------------------------------------------------------------------------- Moon (Meeus ch. 47/48)
# (D, M, M', F, Σl coefficient, Σr coefficient) — Table 47.A
MOON_LR: Final[tuple[tuple[int, int, int, int, int, int], ...]] = (
    (0, 0, 1, 0, 6288774, -20905355), (2, 0, -1, 0, 1274027, -3699111), (2, 0, 0, 0, 658314, -2955968), (0, 0, 2, 0, 213618, -569925),
    (0, 1, 0, 0, -185116, 48888), (0, 0, 0, 2, -114332, -3149), (2, 0, -2, 0, 58793, 246158), (2, -1, -1, 0, 57066, -152138),
    (2, 0, 1, 0, 53322, -170733), (2, -1, 0, 0, 45758, -204586), (0, 1, -1, 0, -40923, -129620), (1, 0, 0, 0, -34720, 108743),
    (0, 1, 1, 0, -30383, 104755), (2, 0, 0, -2, 15327, 10321), (0, 0, 1, 2, -12528, 0), (0, 0, 1, -2, 10980, 79661),
    (4, 0, -1, 0, 10675, -34782), (0, 0, 3, 0, 10034, -23210), (4, 0, -2, 0, 8548, -21636), (2, 1, -1, 0, -7888, 24208),
    (2, 1, 0, 0, -6766, 30824), (1, 0, -1, 0, -5163, -8379), (1, 1, 0, 0, 4987, -16675), (2, -1, 1, 0, 4036, -12831),
    (2, 0, 2, 0, 3994, -10445), (4, 0, 0, 0, 3861, -11650), (2, 0, -3, 0, 3665, 14403), (0, 1, -2, 0, -2689, -7003),
    (2, 0, -1, 2, -2602, 0), (2, -1, -2, 0, 2390, 10056), (1, 0, 1, 0, -2348, 6322), (2, -2, 0, 0, 2236, -9884),
    (0, 1, 2, 0, -2120, 5751), (0, 2, 0, 0, -2069, 0), (2, -2, -1, 0, 2048, -4950), (2, 0, 1, -2, -1773, 4130),
    (2, 0, 0, 2, -1595, 0), (4, -1, -1, 0, 1215, -3958), (0, 0, 2, 2, -1110, 0), (3, 0, -1, 0, -892, 3258),
    (2, 1, 1, 0, -810, 2616), (4, -1, -2, 0, 759, -1897), (0, 2, -1, 0, -713, -2117), (2, 2, -1, 0, -700, 2354),
    (2, 1, -2, 0, 691, 0), (2, -1, 0, -2, 596, 0), (4, 0, 1, 0, 549, -1423), (0, 0, 4, 0, 537, -1117),
    (4, -1, 0, 0, 520, -1571), (1, 0, -2, 0, -487, -1739), (2, 1, 0, -2, -399, 0), (0, 0, 2, -2, -381, -4421),
    (1, 1, 1, 0, 351, 0), (3, 0, -2, 0, -340, 0), (4, 0, -3, 0, 330, 0), (2, -1, 2, 0, 327, 0),
    (0, 2, 1, 0, -323, 1165), (1, 1, -1, 0, 299, 0), (2, 0, 3, 0, 294, 0), (2, 0, -1, -2, 0, 8752),
)
# (D, M, M', F, Σb coefficient) — Table 47.B
MOON_B: Final[tuple[tuple[int, int, int, int, int], ...]] = (
    (0, 0, 0, 1, 5128122), (0, 0, 1, 1, 280602), (0, 0, 1, -1, 277693), (2, 0, 0, -1, 173237), (2, 0, -1, 1, 55413),
    (2, 0, -1, -1, 46271), (2, 0, 0, 1, 32573), (0, 0, 2, 1, 17198), (2, 0, 1, -1, 9266), (0, 0, 2, -1, 8822),
    (2, -1, 0, -1, 8216), (2, 0, -2, -1, 4324), (2, 0, 1, 1, 4200), (2, 1, 0, -1, -3359), (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211), (2, -1, -1, -1, 2065), (0, 1, -1, -1, -1870), (4, 0, -1, -1, 1828), (0, 1, 0, 1, -1794),
    (0, 0, 0, 3, -1749), (0, 1, -1, 1, -1565), (1, 0, 0, 1, -1491), (0, 1, 1, 1, -1475), (0, 1, 1, -1, -1410),
    (0, 1, 0, -1, -1344), (1, 0, 0, -1, -1335), (0, 0, 3, 1, 1107), (4, 0, 0, -1, 1021), (4, 0, -1, 1, 833),
    (0, 0, 1, -3, 777), (4, 0, -2, 1, 671), (2, 0, 0, -3, 607), (2, 0, 2, -1, 596), (2, -1, 1, -1, 491),
    (2, 0, -2, 1, -451), (0, 0, 3, -1, 439), (2, 0, 2, 1, 422), (2, 0, -3, -1, 421), (2, 1, -1, 1, -366),
    (2, 1, 0, 1, -351), (4, 0, 0, 1, 331), (2, -1, 1, 1, 315), (2, -2, 0, -1, 302), (0, 0, 1, 3, -283),
    (2, 1, 1, -1, -229), (1, 1, 0, -1, 223), (1, 1, 0, 1, 223), (0, 1, -2, -1, -220), (2, 1, -1, -1, -220),
    (1, 0, 1, 1, -185), (2, -1, -2, -1, 181), (0, 1, 2, 1, -177), (4, 0, -2, -1, 176), (4, -1, -1, -1, 166),
    (1, 0, 1, -1, -164), (4, 0, 1, -1, 132), (1, 0, -1, -1, -119), (4, -1, 0, -1, 115), (2, -2, 0, 1, 107),
)


@dataclass(frozen=True)
class MoonGeocentric:
    jde: float
    T: float
    Lp: float  # mean longitude
    D: float  # mean elongation
    M: float  # Sun mean anomaly
    Mp: float  # Moon mean anomaly
    F: float  # argument of latitude
    E: float
    sigma_l: float
    sigma_b: float
    sigma_r: float
    longitude: float  # geocentric ecliptic λ (mean equinox of date, no nutation)
    latitude: float  # β
    distance_km: float  # Δ
    parallax: float  # π (deg)
    apparent_longitude: float  # λ + Δψ
    delta_psi: float
    epsilon: float
    right_ascension: float
    declination: float


def moon_geocentric(jde: float) -> MoonGeocentric:
    """Meeus ch. 47 with all periodic terms of tables 47.A/47.B and the additive terms of eq. 47.6/47.7."""
    T = (jde - 2451545.0) / 36525.0
    Lp = limit_degrees(218.3164477 + 481267.88123421 * T - 0.0015786 * T**2 + T**3 / 538841.0 - T**4 / 65194000.0)
    D = limit_degrees(297.8501921 + 445267.1114034 * T - 0.0018819 * T**2 + T**3 / 545868.0 - T**4 / 113065000.0)
    M = limit_degrees(357.5291092 + 35999.0502909 * T - 0.0001536 * T**2 + T**3 / 24490000.0)
    Mp = limit_degrees(134.9633964 + 477198.8675055 * T + 0.0087414 * T**2 + T**3 / 69699.0 - T**4 / 14712000.0)
    F = limit_degrees(93.2720950 + 483202.0175233 * T - 0.0036539 * T**2 - T**3 / 3526000.0 + T**4 / 863310000.0)
    A1 = limit_degrees(119.75 + 131.849 * T)
    A2 = limit_degrees(53.09 + 479264.290 * T)
    A3 = limit_degrees(313.45 + 481266.484 * T)
    E = 1.0 - 0.002516 * T - 0.0000074 * T * T
    E2 = E * E
    sl = 0.0
    sr = 0.0
    for d, m, mp, f, cl, cr in MOON_LR:
        arg = (d * D + m * M + mp * Mp + f * F) * DEG
        k = E if abs(m) == 1 else (E2 if abs(m) == 2 else 1.0)
        sl += k * cl * math.sin(arg)
        sr += k * cr * math.cos(arg)
    sb = 0.0
    for d, m, mp, f, cb in MOON_B:
        arg = (d * D + m * M + mp * Mp + f * F) * DEG
        k = E if abs(m) == 1 else (E2 if abs(m) == 2 else 1.0)
        sb += k * cb * math.sin(arg)
    sl += 3958.0 * math.sin(A1 * DEG) + 1962.0 * math.sin((Lp - F) * DEG) + 318.0 * math.sin(A2 * DEG)
    sb += (-2235.0 * math.sin(Lp * DEG) + 382.0 * math.sin(A3 * DEG) + 175.0 * math.sin((A1 - F) * DEG) + 175.0 * math.sin((A1 + F) * DEG)
           + 127.0 * math.sin((Lp - Mp) * DEG) - 115.0 * math.sin((Lp + Mp) * DEG))
    lon = limit_degrees(Lp + sl / 1e6)
    lat = sb / 1e6
    dist = 385000.56 + sr / 1000.0
    pi = math.asin(EARTH_RADIUS_KM / dist) * RAD
    dpsi, deps = nutation(T)
    eps = true_ecliptic_obliquity(T / 10.0, deps)
    app_lon = limit_degrees(lon + dpsi)
    ra = geocentric_right_ascension(app_lon, eps, lat)
    dec = geocentric_declination(lat, eps, app_lon)
    return MoonGeocentric(jde, T, Lp, D, M, Mp, F, E, sl, sb, sr, lon, lat, dist, pi, app_lon, dpsi, eps, ra, dec)


PHASE_NAMES: Final = ("New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent")


@dataclass(frozen=True)
class MoonPosition:
    utc: _dt.datetime
    geocentric: MoonGeocentric
    azimuth: float
    elevation: float  # refracted apparent
    elevation_uncorrected: float
    zenith: float
    distance_km: float
    semidiameter: float  # deg (topocentric)
    illuminated_fraction: float  # k, 0..1
    phase_angle: float  # i (deg), 0 = full, 180 = new
    elongation: float  # λ_moon − λ_sun (deg, 0..360): <180 waxing
    waxing: bool
    phase_name: str
    age_fraction: float  # 0 = new, 0.5 = full, ~1 = new again (elongation/360)

    def as_dict(self) -> dict:
        return {
            "utc": self.utc.isoformat().replace("+00:00", "Z"),
            "azimuth_deg": self.azimuth,
            "elevation_deg": self.elevation,
            "distance_km": self.distance_km,
            "semidiameter_deg": self.semidiameter,
            "illuminated_fraction": self.illuminated_fraction,
            "phase_angle_deg": self.phase_angle,
            "elongation_deg": self.elongation,
            "waxing": self.waxing,
            "phase_name": self.phase_name,
            "age_fraction": self.age_fraction,
            "right_ascension_deg": self.geocentric.right_ascension,
            "declination_deg": self.geocentric.declination,
            "ecliptic_longitude_deg": self.geocentric.longitude,
            "ecliptic_latitude_deg": self.geocentric.latitude,
        }


def moon_illumination(moon: MoonGeocentric, sun: GeocentricSun) -> tuple[float, float, float]:
    """(illuminated fraction k, phase angle i deg, elongation deg) — Meeus eq. 48.2/48.3/48.1."""
    a0, d0 = sun.alpha * DEG, sun.delta * DEG
    a, d = moon.right_ascension * DEG, moon.declination * DEG
    cos_psi = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a0 - a)
    cos_psi = max(-1.0, min(1.0, cos_psi))
    psi = math.acos(cos_psi)
    R_km = sun.R * AU_KM
    i = math.atan2(R_km * math.sin(psi), moon.distance_km - R_km * math.cos(psi))
    k = (1.0 + math.cos(i)) / 2.0
    elong = limit_degrees(moon.apparent_longitude - sun.lamda)
    return k, i * RAD, elong


def phase_name(elongation_deg: float) -> str:
    """Eight-phase name from Moon−Sun elongation; principal phases get a ±11.25° window (1/16 of the cycle)."""
    idx = int(((elongation_deg + 22.5) % 360.0) // 45.0)
    return PHASE_NAMES[idx]


def moon_position(utc: _dt.datetime, observer: Observer = CENTRAL_PARK, delta_t_s: float | None = None) -> MoonPosition:
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=_dt.timezone.utc)
    utc = utc.astimezone(_dt.timezone.utc)
    jd = timesync.julian_day(utc)
    if delta_t_s is None:
        delta_t_s = timesync.delta_t_seconds(utc.timestamp())
    jde = julian_ephemeris_day(jd, delta_t_s)
    m = moon_geocentric(jde)
    s = geocentric_sun(jd, delta_t_s)
    h = observer_hour_angle(s.nu, observer.longitude_deg, m.right_ascension)
    da, dp, hp = topocentric_corrections(observer.latitude_deg, observer.elevation_m, m.parallax, h, m.declination)
    e0 = topocentric_elevation_angle(observer.latitude_deg, dp, hp)
    semid = math.asin(0.272481 * math.sin(m.parallax * DEG)) * RAD  # Meeus 55.1: k = 0.272481
    de = atmospheric_refraction_correction(observer.pressure_mbar, observer.temperature_c, e0, observer.atmos_refract_deg, semid)
    e = e0 + de
    az = limit_degrees(topocentric_azimuth_astro(hp, observer.latitude_deg, dp) + 180.0)
    k, i, elong = moon_illumination(m, s)
    return MoonPosition(
        utc=utc, geocentric=m, azimuth=az, elevation=e, elevation_uncorrected=e0, zenith=90.0 - e, distance_km=m.distance_km,
        semidiameter=semid, illuminated_fraction=k, phase_angle=i, elongation=elong, waxing=elong < 180.0, phase_name=phase_name(elong),
        age_fraction=elong / 360.0,
    )


# --------------------------------------------------------------------------- Manhattanhenge
# Manhattan street grid (Commissioners' Plan of 1811). The avenues run 29.0° east of true north, so the
# numbered cross-streets run 29.0° + 90° = 119.0° (looking east) / 299.0° (looking west). A sunset aligned
# with the street grid therefore has compass azimuth 299.0°; the grid is rotated 29.0° clockwise from a
# true east–west line. (Measured values in the literature range 28.9°–29.1°; 29.0° is used here.)
MANHATTAN_GRID_ROTATION_DEG: Final = 29.0
MANHATTAN_STREET_SUNSET_AZIMUTH_DEG: Final = 270.0 + MANHATTAN_GRID_ROTATION_DEG  # 299.0
MANHATTANHENGE_TOLERANCE_DEG: Final = 0.5
# Apparent (refracted, topocentric) elevation of the disc centre used for the two classic variants.
# "Full sun": whole disc visible, lower limb on the street-end horizon; the brief fixes this at 0.5°, i.e. a
# street-end horizon at 0.5 − 0.2667 = 0.233° (New Jersey shoreline seen from mid-Manhattan street level).
# "Half sun": disc centre on that same horizon, i.e. one solar radius (SUN_RADIUS_DEG) lower.
FULL_SUN_ELEVATION_DEG: Final = 0.5
STREET_HORIZON_ELEVATION_DEG: Final = FULL_SUN_ELEVATION_DEG - SUN_RADIUS_DEG  # 0.23333
HALF_SUN_ELEVATION_DEG: Final = STREET_HORIZON_ELEVATION_DEG


@dataclass(frozen=True)
class SunsetAzimuth:
    local_date: _dt.date
    utc: _dt.datetime  # instant at which the apparent elevation equals ``elevation_deg``
    elevation_deg: float
    azimuth_deg: float
    delta_from_grid_deg: float  # azimuth − 299.0

    def as_dict(self) -> dict:
        return {"local_date": self.local_date.isoformat(), "utc": self.utc.isoformat().replace("+00:00", "Z"), "elevation_deg": self.elevation_deg, "azimuth_deg": self.azimuth_deg, "delta_from_grid_deg": self.delta_from_grid_deg}


def time_of_evening_elevation(local_date: _dt.date, elevation_deg: float, observer: Observer, tolerance_s: float = 0.05) -> SunsetAzimuth | None:
    """Find the evening instant when the apparent (refracted, topocentric) solar elevation equals ``elevation_deg``.

    Bisection between solar transit and 90 minutes after geometric sunset; the elevation is strictly
    decreasing on that interval at NYC latitude. Returns None if the target is not bracketed.
    """
    ev = sun_events_local(local_date, observer)
    if ev.sunset is None or ev.transit is None:
        return None
    lo = ev.transit.timestamp()
    hi = ev.sunset.timestamp() + 90 * 60
    dt_lo = timesync.delta_t_seconds(lo)
    f = lambda t: solar_position_jd(timesync.julian_day_from_unix(t), observer, dt_lo).elevation - elevation_deg  # noqa: E731
    flo, fhi = f(lo), f(hi)
    if flo < 0 or fhi > 0:
        return None
    while hi - lo > tolerance_s:
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    t = 0.5 * (lo + hi)
    pos = solar_position_jd(timesync.julian_day_from_unix(t), observer, dt_lo)
    return SunsetAzimuth(local_date, _dt.datetime.fromtimestamp(t, tz=_dt.timezone.utc), elevation_deg, pos.azimuth, pos.azimuth - MANHATTAN_STREET_SUNSET_AZIMUTH_DEG)


@dataclass(frozen=True)
class ManhattanhengeEvent:
    kind: str  # "full" | "half"
    local_date: _dt.date
    utc: _dt.datetime
    azimuth_deg: float
    delta_from_grid_deg: float
    best_in_season: bool  # closest match of its kind before (spring) or after (summer) the solstice


def manhattanhenge(year: int, observer: Observer = TUDOR_CITY_42ND, tolerance_deg: float = MANHATTANHENGE_TOLERANCE_DEG) -> list[ManhattanhengeEvent]:
    """All local dates in ``year`` whose setting Sun is within ``tolerance_deg`` of the street azimuth (299.0°).

    "full" uses the disc centre at +0.5° apparent elevation (whole disc above the street horizon),
    "half" uses 0.0° (half the disc set). The best date of each kind in each season is flagged.
    """
    events: list[ManhattanhengeEvent] = []
    d = _dt.date(year, 5, 1)
    end = _dt.date(year, 8, 15)
    while d <= end:
        for kind, elev in (("full", FULL_SUN_ELEVATION_DEG), ("half", HALF_SUN_ELEVATION_DEG)):
            sa = time_of_evening_elevation(d, elev, observer)
            if sa is not None and abs(sa.delta_from_grid_deg) <= tolerance_deg:
                events.append(ManhattanhengeEvent(kind, d, sa.utc, sa.azimuth_deg, sa.delta_from_grid_deg, False))
        d += _dt.timedelta(days=1)
    solstice = _dt.date(year, 6, 21)
    out: list[ManhattanhengeEvent] = []
    for kind in ("full", "half"):
        for season in (lambda e: e.local_date < solstice, lambda e: e.local_date >= solstice):
            group = [e for e in events if e.kind == kind and season(e)]
            if not group:
                continue
            best = min(group, key=lambda e: abs(e.delta_from_grid_deg))
            for e in group:
                out.append(ManhattanhengeEvent(e.kind, e.local_date, e.utc, e.azimuth_deg, e.delta_from_grid_deg, e is best))
    out.sort(key=lambda e: (e.local_date, e.kind))
    return out


def manhattanhenge_sensitivity(year: int, observer: Observer = TUDOR_CITY_42ND, elevations: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25), grid_azimuths: Sequence[float] = (298.9, 299.0, 299.1)) -> list[dict]:
    """Best full-sun date per season as a function of the assumed disc-centre elevation and grid azimuth.

    Documents how strongly the announced dates depend on the horizon assumption (≈ 1 day per 0.2° of
    elevation, ≈ 1 day per 0.22° of grid azimuth) — see docs/LIVE_ALGORITHMS.md §2.6.
    """
    rows: list[dict] = []
    cache: dict[tuple[_dt.date, float], SunsetAzimuth | None] = {}
    solstice = _dt.date(year, 6, 21)
    dates = [_dt.date(year, 5, 15) + _dt.timedelta(days=i) for i in range(75)]
    for elev in elevations:
        series = []
        for d in dates:
            key = (d, elev)
            if key not in cache:
                cache[key] = time_of_evening_elevation(d, elev, observer)
            if cache[key] is not None:
                series.append(cache[key])
        for grid in grid_azimuths:
            for label, sel in (("spring", lambda s: s.local_date < solstice), ("summer", lambda s: s.local_date >= solstice)):
                group = [s for s in series if sel(s)]
                if not group:
                    continue
                best = min(group, key=lambda s: abs(s.azimuth_deg - grid))
                rows.append({"elevation_deg": elev, "grid_azimuth_deg": grid, "season": label, "best_date": best.local_date.isoformat(), "azimuth_deg": round(best.azimuth_deg, 3), "delta_deg": round(best.azimuth_deg - grid, 3), "utc": best.utc.isoformat().replace("+00:00", "Z")})
    return rows


def sunset_azimuth_series(year: int, observer: Observer = TUDOR_CITY_42ND, elevation_deg: float = FULL_SUN_ELEVATION_DEG, dates: Iterable[_dt.date] | None = None) -> list[SunsetAzimuth]:
    """Setting-Sun azimuth at a given apparent elevation for each date (default: every day of the year)."""
    if dates is None:
        d0 = _dt.date(year, 1, 1)
        dates = (d0 + _dt.timedelta(days=i) for i in range(366 if timesync.is_leap_year(year) else 365))
    out = []
    for d in dates:
        sa = time_of_evening_elevation(d, elevation_deg, observer)
        if sa is not None:
            out.append(sa)
    return out
