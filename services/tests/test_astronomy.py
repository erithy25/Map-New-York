"""Sun (NREL SPA), Moon (Meeus) and Manhattanhenge, against published reference values and USNO fixtures."""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
import os

import pytest

from conftest import FIXTURES
from nycsim_live import astronomy as A
from nycsim_live import timesync as T

# NREL SPA, Reda & Andreas, "Solar Position Algorithm for Solar Radiation Applications" (NREL/TP-560-34302,
# revised 2008), Appendix A.5 worked example: 2003-10-17 12:30:30 local at UTC-7 (= 19:30:30 UTC),
# 39.742476 N, 105.1786 W, 1830.14 m, 820 mbar, 11 °C, ΔT = 67 s.
SPA_OBSERVER = A.Observer(39.742476, -105.1786, 1830.14, pressure_mbar=820.0, temperature_c=11.0)
SPA_UTC = dt.datetime(2003, 10, 17, 19, 30, 30, tzinfo=dt.timezone.utc)
SPA_DELTA_T = 67.0


@pytest.fixture(scope="module")
def spa():
    return A.solar_position(SPA_UTC, SPA_OBSERVER, delta_t_s=SPA_DELTA_T)


@pytest.mark.parametrize(
    "field,expected,tol",
    [
        ("jd", 2452930.312847, 1e-6),
        ("hour_angle", 11.105900, 1e-5),
        ("elevation_uncorrected", 39.872046, 1e-5),
        ("elevation", 39.888378, 1e-6),
        ("zenith", 50.111622, 1e-6),
        ("azimuth_astro", 14.340241, 1e-6),
        ("azimuth", 194.340241, 1e-6),
    ],
)
def test_spa_reference_case(spa, field, expected, tol):
    assert getattr(spa, field) == pytest.approx(expected, abs=tol)


@pytest.mark.parametrize(
    "field,expected,tol",
    [
        ("L", 24.0182616, 1e-6),
        ("B", -0.0001011219, 1e-9),
        ("R", 0.9965422974, 1e-9),
        ("delta_psi", -0.00399840, 1e-8),
        ("delta_epsilon", 0.00166657, 1e-8),
        ("epsilon", 23.440465, 1e-6),
        ("lamda", 204.0085519, 1e-6),
        ("nu", 318.5119, 1e-4),
        ("alpha", 202.22741, 1e-5),
        ("delta", -9.31434, 1e-5),
    ],
)
def test_spa_reference_intermediates(spa, field, expected, tol):
    assert getattr(spa.geocentric, field) == pytest.approx(expected, abs=tol)


def test_spa_topocentric_parallax_and_semidiameter(spa):
    assert spa.xi == pytest.approx(0.002451, abs=1e-6)  # 8.794" / R
    assert spa.semidiameter == pytest.approx(A.SUN_RADIUS_DEG / spa.geocentric.R, rel=1e-12)
    assert spa.refraction == pytest.approx(spa.elevation - spa.elevation_uncorrected, abs=1e-12)


def test_spa_sunrise_transit_set_reference_case():
    """SPA A.5 for the same site/date: sunrise 06:12:43, transit 11:46:04, sunset 17:18:51 local (UTC-7).

    Evaluated on the *local* day: SPA A.2 itself yields fractions of a UT day, and at 105° W the evening
    sunset falls just after 00 UT of the next UT day."""
    ev = A.sun_events_at_offset(dt.date(2003, 10, 17), SPA_OBSERVER, -7 * 3600)
    tz = dt.timezone(dt.timedelta(hours=-7))
    assert ev.sunrise.astimezone(tz).strftime("%H:%M:%S") == "06:12:43"
    assert ev.transit.astimezone(tz).strftime("%H:%M:%S") == "11:46:04"
    assert ev.sunset.astimezone(tz).strftime("%H:%M:%S") == "17:18:51"


def test_limit_helpers():
    assert A.limit_degrees(-1.0) == pytest.approx(359.0)
    assert A.limit_degrees(721.0) == pytest.approx(1.0)
    assert A.limit_degrees180pm(190.0) == pytest.approx(-170.0)
    assert A.limit_degrees180pm(-190.0) == pytest.approx(170.0)
    assert A.limit_zero_to_one(-0.25) == pytest.approx(0.75)


def test_refraction_is_switched_off_well_below_the_horizon():
    assert A.atmospheric_refraction_correction(1013.25, 15.0, -5.0) == 0.0
    # SPA eq. 42 at e0 = 0, 1013.25 mbar, 15 C: (P/1010)(283/288)(1.02/(60 tan(10.3/5.11 deg))) = 0.47617 deg
    assert A.atmospheric_refraction_correction(1013.25, 15.0, 0.0) == pytest.approx(0.47617, abs=1e-5)
    # lower pressure and higher temperature both reduce refraction
    assert A.atmospheric_refraction_correction(820.0, 30.0, 0.0) < A.atmospheric_refraction_correction(1013.25, 0.0, 0.0)


# --------------------------------------------------------------------------- USNO cross-checks
def _usno_files():
    return sorted(glob.glob(os.path.join(str(FIXTURES), "usno", "usno_*.json")))


@pytest.mark.parametrize("path", _usno_files(), ids=lambda p: os.path.basename(p)[5:-5])
def test_sun_events_match_usno(path):
    """USNO ``/api/rstt/oneday`` for Central Park. The API renders its times in the fixed offset it was
    queried with, so days on which New York changes offset are compared in that same fixed offset."""
    doc = json.load(open(path, encoding="utf-8"))["properties"]["data"]
    date = dt.date(doc["year"], doc["month"], doc["day"])
    tz = dt.timezone(dt.timedelta(hours=doc["tz"]))
    ev = A.sun_events_local(date, A.CENTRAL_PARK)
    want = {e["phen"]: e["time"] for e in doc["sundata"]}
    for phen, attr in (("Rise", "sunrise"), ("Upper Transit", "transit"), ("Set", "sunset")):
        if phen not in want:
            continue
        got = getattr(ev, attr).astimezone(tz)
        h, m = (int(x) for x in want[phen].split(":"))
        delta = (got.hour * 60 + got.minute + got.second / 60.0) - (h * 60 + m)
        assert abs(delta) <= 1.0, f"{date} {phen}: got {got:%H:%M:%S}, USNO {want[phen]}"


@pytest.mark.parametrize("path", _usno_files(), ids=lambda p: os.path.basename(p)[5:-5])
def test_moon_illumination_matches_usno(path):
    """USNO publishes the illuminated fraction at 00:00 in the queried offset, rounded to a percent."""
    doc = json.load(open(path, encoding="utf-8"))["properties"]["data"]
    tz = dt.timezone(dt.timedelta(hours=doc["tz"]))
    midnight = dt.datetime(doc["year"], doc["month"], doc["day"], tzinfo=tz)
    want = int(doc["fracillum"].rstrip("%"))
    # USNO does not document which instant of the day its rounded percentage refers to, so require the value
    # to lie inside the day's range (the fraction is monotone over a day away from the principal phases).
    ks = [A.moon_position(midnight.astimezone(dt.timezone.utc) + dt.timedelta(hours=h), A.CENTRAL_PARK).illuminated_fraction * 100.0 for h in range(0, 25, 4)]
    assert min(ks) - 1.0 <= want <= max(ks) + 1.0, f"USNO {want}% outside [{min(ks):.1f}, {max(ks):.1f}]"


def test_moon_geocentric_meeus_example_47a():
    """Meeus, *Astronomical Algorithms* 2nd ed., example 47.a: 1992-04-12 00:00 TD."""
    m = A.moon_geocentric(2448724.5)
    assert m.Lp == pytest.approx(134.290182, abs=1e-5)
    assert m.D == pytest.approx(113.842304, abs=1e-5)
    assert m.M == pytest.approx(97.643514, abs=1e-5)
    assert m.Mp == pytest.approx(5.150833, abs=1e-5)
    assert m.F == pytest.approx(219.889721, abs=1e-5)
    assert m.sigma_l == pytest.approx(-1127527, abs=2.0)
    assert m.sigma_b == pytest.approx(-3229126, abs=2.0)
    assert m.sigma_r == pytest.approx(-16590875, abs=40.0)
    assert m.longitude == pytest.approx(133.162655, abs=1e-5)
    assert m.latitude == pytest.approx(-3.229126, abs=1e-5)
    assert m.distance_km == pytest.approx(368409.7, abs=0.1)
    assert m.parallax == pytest.approx(0.991990, abs=1e-5)


def test_moon_illumination_meeus_example_48a():
    """Meeus example 48.a: 1992-04-12, k = 0.6786, phase angle i = 69.0756°."""
    jde = 2448724.5
    m = A.moon_geocentric(jde)
    s = A.geocentric_sun(jde, 0.0)
    k, i, elong = A.moon_illumination(m, s)
    assert i == pytest.approx(69.0756, abs=0.02)
    assert k == pytest.approx(0.6786, abs=2e-4)
    assert 0.0 <= elong < 360.0


@pytest.mark.parametrize(
    "elong,name",
    [(0.0, "New Moon"), (30.0, "Waxing Crescent"), (90.0, "First Quarter"), (140.0, "Waxing Gibbous"),
     (180.0, "Full Moon"), (220.0, "Waning Gibbous"), (270.0, "Last Quarter"), (330.0, "Waning Crescent"),
     (22.4, "New Moon"), (22.6, "Waxing Crescent"), (337.6, "New Moon"), (337.4, "Waning Crescent"), (359.0, "New Moon")],
)
def test_phase_names(elong, name):
    assert A.phase_name(elong) == name


def test_moon_position_is_topocentric_and_refracted():
    utc = dt.datetime(2026, 9, 6, 11, 24, 40, tzinfo=dt.timezone.utc)
    m = A.moon_position(utc, A.CENTRAL_PARK)
    assert 0.0 <= m.azimuth < 360.0
    assert m.elevation >= m.elevation_uncorrected  # refraction never lowers a body above the horizon
    assert 0.24 < m.semidiameter < 0.29  # apparent lunar radius over the whole orbit
    assert 356000 < m.distance_km < 407000
    assert m.zenith == pytest.approx(90.0 - m.elevation)
    assert m.waxing == (m.elongation < 180.0)
    assert m.age_fraction == pytest.approx(m.elongation / 360.0)


# --------------------------------------------------------------------------- Manhattanhenge
def test_grid_azimuth_constants():
    assert A.MANHATTAN_STREET_SUNSET_AZIMUTH_DEG == pytest.approx(299.0)
    assert A.MANHATTAN_GRID_ROTATION_DEG == pytest.approx(29.0)
    assert A.HALF_SUN_ELEVATION_DEG == pytest.approx(A.FULL_SUN_ELEVATION_DEG - A.SUN_RADIUS_DEG)


def test_evening_elevation_is_monotonic_and_azimuth_grows_as_the_sun_sets():
    d = dt.date(2026, 5, 28)
    a = A.time_of_evening_elevation(d, 1.0, A.TUDOR_CITY_42ND)
    b = A.time_of_evening_elevation(d, A.FULL_SUN_ELEVATION_DEG, A.TUDOR_CITY_42ND)
    c = A.time_of_evening_elevation(d, A.HALF_SUN_ELEVATION_DEG, A.TUDOR_CITY_42ND)
    assert a.utc < b.utc < c.utc
    assert a.azimuth_deg < b.azimuth_deg < c.azimuth_deg


def test_evening_elevation_rejects_unreachable_targets():
    """Apparent elevations between about -0.83° and -0.22° do not exist: the SPA switches refraction off at
    -(SUN_RADIUS + atmos_refract), so the apparent elevation jumps. The solver must return None, not the jump."""
    assert A.time_of_evening_elevation(dt.date(2026, 5, 28), -0.5, A.TUDOR_CITY_42ND) is None
    assert A.time_of_evening_elevation(dt.date(2026, 5, 28), 75.0, A.TUDOR_CITY_42ND) is None  # above the day's maximum


def test_manhattanhenge_2026_matches_the_recorded_verification_run():
    """Regression against docs/verification/live/manhattanhenge_2026.json (dates and azimuths)."""
    doc = json.load(open(os.path.join(os.path.dirname(str(FIXTURES)), "..", "..", "docs", "verification", "live", "manhattanhenge_2026.json"), encoding="utf-8"))
    best = {(e["kind"], e["local_date"][:7]): e for e in doc["events"] if e["best_in_season"]}
    assert best[("half", "2026-05")]["local_date"] == "2026-05-27"
    assert best[("full", "2026-05")]["local_date"] == "2026-05-28"
    assert best[("full", "2026-07")]["local_date"] == "2026-07-14"
    assert best[("half", "2026-07")]["local_date"] == "2026-07-15"
    for e in doc["events"]:
        sa = A.time_of_evening_elevation(dt.date.fromisoformat(e["local_date"]), doc["full_sun_elevation_deg"] if e["kind"] == "full" else doc["half_sun_elevation_deg"], A.TUDOR_CITY_42ND)
        assert sa is not None
        assert sa.azimuth_deg == pytest.approx(e["azimuth_deg"], abs=1e-3)


def test_manhattanhenge_events_are_symmetric_about_the_solstice():
    """A fixed (grid azimuth, elevation) criterion depends only on the solar declination, so the May and the
    July event of the same kind must occur at the same declination (within one day's 0.16° of declination)."""
    events = {(e.kind, e.local_date.month): e for e in A.manhattanhenge(2026) if e.best_in_season}
    for kind in ("full", "half"):
        may, july = events[(kind, 5)], events[(kind, 7)]
        d_may = A.solar_position(may.utc, A.TUDOR_CITY_42ND).geocentric.delta
        d_july = A.solar_position(july.utc, A.TUDOR_CITY_42ND).geocentric.delta
        assert abs(d_may - d_july) < 0.16, f"{kind}: {d_may} vs {d_july}"


def test_sunset_azimuth_series_covers_the_year_and_peaks_at_the_solstice():
    dates = [dt.date(2026, 6, 1) + dt.timedelta(days=i) for i in range(0, 40, 4)]
    series = A.sunset_azimuth_series(2026, A.TUDOR_CITY_42ND, dates=dates)
    assert len(series) == len(dates)
    peak = max(series, key=lambda s: s.azimuth_deg)
    assert dt.date(2026, 6, 17) <= peak.local_date <= dt.date(2026, 6, 25)
    assert all(s.delta_from_grid_deg == pytest.approx(s.azimuth_deg - 299.0) for s in series)


def test_declination_azimuth_relation_is_consistent():
    """Cross-check the azimuth with the closed-form spherical relation cos A = (sin δ − sin h sin φ)/(cos h cos φ)
    evaluated with the *topocentric* declination the SPA produced."""
    sa = A.time_of_evening_elevation(dt.date(2026, 5, 28), 0.5, A.TUDOR_CITY_42ND)
    p = A.solar_position(sa.utc, A.TUDOR_CITY_42ND)
    phi = math.radians(A.TUDOR_CITY_42ND.latitude_deg)
    h = math.radians(p.elevation_uncorrected)
    d = math.radians(p.delta_prime)
    cos_az = (math.sin(d) - math.sin(h) * math.sin(phi)) / (math.cos(h) * math.cos(phi))
    assert math.degrees(math.acos(max(-1.0, min(1.0, cos_az)))) == pytest.approx(360.0 - p.azimuth, abs=1e-4)
