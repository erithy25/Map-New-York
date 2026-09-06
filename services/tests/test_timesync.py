"""Civil time: calendar arithmetic, the US DST rule cross-checked against zoneinfo, Julian day, ΔT."""
from __future__ import annotations

import datetime as dt

import pytest

from nycsim_live import timesync as T


# --------------------------------------------------------------------------- calendar arithmetic
@pytest.mark.parametrize("y,expected", [(1900, False), (2000, True), (2024, True), (2025, False), (2100, False), (2400, True)])
def test_leap_year(y, expected):
    assert T.is_leap_year(y) is expected


def test_day_of_week_matches_datetime_for_a_century():
    d = dt.date(2000, 1, 1)
    end = dt.date(2100, 1, 1)
    while d < end:
        # datetime: Monday=0..Sunday=6 ; ours: Sunday=0..Saturday=6
        assert T.day_of_week(d.year, d.month, d.day) == (d.weekday() + 1) % 7
        d += dt.timedelta(days=1)


def test_days_from_civil_roundtrip():
    for y in (1, 1583, 1900, 1970, 2000, 2026, 2100, 9999):
        for m in range(1, 13):
            for day in (1, 15, T.days_in_month(y, m)):
                n = T.days_from_civil(y, m, day)
                assert T.civil_from_days(n) == (y, m, day)


def test_days_from_civil_epoch():
    assert T.days_from_civil(1970, 1, 1) == 0
    assert T.days_from_civil(2000, 1, 1) == 10957
    assert T.unix_from_civil_utc(2026, 9, 6, 11, 24, 40) == int(dt.datetime(2026, 9, 6, 11, 24, 40, tzinfo=dt.timezone.utc).timestamp())


def test_nth_and_last_weekday():
    assert T.nth_weekday_of_month(2026, 3, 0, 2) == 8  # second Sunday of March 2026
    assert T.nth_weekday_of_month(2026, 11, 0, 1) == 1  # first Sunday of November 2026
    assert T.last_weekday_of_month(2006, 10, 0) == 29
    with pytest.raises(ValueError):
        T.nth_weekday_of_month(2026, 2, 0, 5)


# --------------------------------------------------------------------------- DST
def test_us_dst_bounds_known_years():
    b = T.us_dst_bounds(2026)
    assert b.start_date == (2026, 3, 8) and b.end_date == (2026, 11, 1)
    assert T.us_dst_bounds(2006).start_date == (2006, 4, 2)
    assert T.us_dst_bounds(2006).end_date == (2006, 10, 29)
    assert T.us_dst_bounds(1986).start_date == (1986, 4, 27)
    assert T.us_dst_bounds(1975).start_date == (1975, 2, 23)
    assert T.us_dst_bounds(1974).start_date == (1974, 1, 6)
    with pytest.raises(ValueError):
        T.us_dst_bounds(1966)


@pytest.mark.skipif(T.NYC_TZ is None, reason="tz database unavailable")
def test_dst_rule_matches_zoneinfo_every_day_2000_2100():
    """The mandated cross-check: the pure-arithmetic rule the C++ core ports must agree with the IANA
    database at 12:00 UTC (a time that is unambiguous on every civil day) for every day 2000-01-01 .. 2100-12-31."""
    t = T.unix_from_civil_utc(2000, 1, 1, 12)
    end = T.unix_from_civil_utc(2101, 1, 1, 12)
    days = 0
    while t < end:
        assert T.us_dst_offset(t) == T.zoneinfo_offset(t), f"mismatch at {dt.datetime.fromtimestamp(t, dt.timezone.utc)}"
        t += T.SECONDS_PER_DAY
        days += 1
    assert days == 36890


@pytest.mark.skipif(T.NYC_TZ is None, reason="tz database unavailable")
def test_dst_rule_matches_zoneinfo_every_hour_of_every_transition_day_1967_2100():
    for year in range(1967, 2101):
        b = T.us_dst_bounds(year)
        for date in (b.start_date, b.end_date):
            base = T.unix_from_civil_utc(*date) - T.EST_OFFSET_S - 12 * 3600
            for h in range(48):
                t = base + h * 3600
                assert T.us_dst_offset(t) == T.zoneinfo_offset(t), f"mismatch {year} {date} +{h}h"


@pytest.mark.skipif(T.NYC_TZ is None, reason="tz database unavailable")
def test_dst_boundaries_are_exact_to_the_second():
    for year in (2007, 2026, 2050, 2099):
        b = T.us_dst_bounds(year)
        assert T.us_dst_offset(b.start_unix - 1) == (T.EST_OFFSET_S, False)
        assert T.us_dst_offset(b.start_unix) == (T.EDT_OFFSET_S, True)
        assert T.us_dst_offset(b.end_unix - 1) == (T.EDT_OFFSET_S, True)
        assert T.us_dst_offset(b.end_unix) == (T.EST_OFFSET_S, False)


# --------------------------------------------------------------------------- Julian day
@pytest.mark.parametrize(
    "date,jd",
    [
        ((2000, 1, 1, 12, 0, 0), 2451545.0),  # Meeus 7.a
        ((1999, 1, 1, 0, 0, 0), 2451179.5),
        ((1987, 1, 27, 0, 0, 0), 2446822.5),
        ((1957, 10, 4, 19, 26, 24), 2436116.31),  # Sputnik 1, Meeus 7.a
        ((2003, 10, 17, 19, 30, 30), 2452930.312847),  # NREL SPA reference case
    ],
)
def test_julian_day(date, jd):
    assert T.julian_day(dt.datetime(*date, tzinfo=dt.timezone.utc)) == pytest.approx(jd, abs=1e-6)


def test_julian_day_unix_roundtrip():
    for u in (0.0, 1e9, 1788693880.0):
        # JD is ~2.46e6, so one float64 ulp is 4.7e-10 d = 4.0e-5 s: the round-trip cannot be tighter.
        assert T.unix_from_julian_day(T.julian_day_from_unix(u)) == pytest.approx(u, abs=1e-4)
        assert T.julian_day_from_unix(u) == pytest.approx(T.julian_day(dt.datetime.fromtimestamp(u, dt.timezone.utc)), abs=1e-9)


# --------------------------------------------------------------------------- Delta T
def test_tai_minus_utc_steps():
    assert T.tai_minus_utc(T.unix_from_civil_utc(1971, 6, 1)) == 10
    assert T.tai_minus_utc(T.unix_from_civil_utc(1972, 1, 1)) == 10
    assert T.tai_minus_utc(T.unix_from_civil_utc(1972, 6, 30)) == 10
    assert T.tai_minus_utc(T.unix_from_civil_utc(1972, 7, 1)) == 11
    assert T.tai_minus_utc(T.unix_from_civil_utc(2016, 12, 31)) == 36
    assert T.tai_minus_utc(T.unix_from_civil_utc(2017, 1, 1)) == 37
    assert T.tai_minus_utc(T.unix_from_civil_utc(2026, 9, 6)) == 37


def test_delta_t_current_era():
    # 2026: TT-UT1 = 32.184 + 37 - DUT1; with DUT1 = 0 that is 69.184 s.
    assert T.delta_t_seconds(T.unix_from_civil_utc(2026, 9, 6)) == pytest.approx(69.184, abs=1e-9)
    assert T.delta_t_seconds(T.unix_from_civil_utc(2003, 10, 17)) == pytest.approx(64.184, abs=1e-9)


def test_delta_t_polynomial_known_values():
    # Espenak & Meeus fit, published check points (NASA eclipse site table), tolerance = fit residual.
    assert T.delta_t_polynomial(1900.0) == pytest.approx(-2.79, abs=0.5)
    assert T.delta_t_polynomial(2000.0) == pytest.approx(63.86, abs=0.5)
    assert T.delta_t_polynomial(1950.0) == pytest.approx(29.07, abs=1.0)


def test_delta_t_far_future_uses_polynomial():
    v = T.delta_t_seconds(T.unix_from_civil_utc(2100, 1, 1))
    assert v == pytest.approx(T.delta_t_polynomial(2100.0), abs=1e-6)
    assert 150.0 < v < 220.0


# --------------------------------------------------------------------------- SimTime
def test_sim_time_fields():
    s = T.sim_time(dt.datetime(2026, 9, 6, 11, 24, 40, tzinfo=dt.timezone.utc))
    assert s.tz_abbreviation == "EDT" and s.is_dst is True and s.utc_offset_s == -4 * 3600
    assert s.local_date == (2026, 9, 6)
    assert s.local.hour == 7 and s.local.minute == 24
    assert s.seconds_since_local_midnight == pytest.approx(7 * 3600 + 24 * 60 + 40)
    assert s.day_of_year == 249
    assert s.jde - s.jd == pytest.approx(s.delta_t_s / 86400.0)
    d = s.as_dict()
    assert d["tz"] == "EDT" and d["local_date"] == "2026-09-06"


def test_sim_time_winter_is_est():
    s = T.sim_time(dt.datetime(2026, 1, 15, 17, 0, tzinfo=dt.timezone.utc))
    assert s.tz_abbreviation == "EST" and s.utc_offset_s == -5 * 3600 and s.local.hour == 12


def test_sim_time_naive_input_is_utc():
    a = T.sim_time(dt.datetime(2026, 9, 6, 11, 24, 40))
    b = T.sim_time(dt.datetime(2026, 9, 6, 11, 24, 40, tzinfo=dt.timezone.utc))
    assert a.unix_s == b.unix_s
