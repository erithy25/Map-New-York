"""Civil time for the simulation: UTC -> America/New_York, DST rules, Julian day, Delta-T.

Reference implementation for ``core/live/TimeSync.{h,cpp}`` (ARCHITECTURE.md §11). Two independent
paths give the local offset:

* :func:`zoneinfo_offset` — the IANA database via :mod:`zoneinfo` (authoritative, needs tzdata).
* :func:`us_dst_offset` — pure integer arithmetic of the US federal DST rule as applied to New York
  since 1967 (Uniform Time Act 1966, amendments of 1974/1975/1986 and the Energy Policy Act 2005).
  This is what the C++ core ports; the test-suite cross-checks it against zoneinfo for every day
  2000–2100 and every hour of every transition day.

All arithmetic is on proleptic-Gregorian civil dates and POSIX seconds (no leap seconds; UTC days
are exactly 86 400 s, which is what the engine clock delivers).
"""
from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass
from typing import Final

try:  # zoneinfo is stdlib; tzdata may be missing on minimal images -> zoneinfo_offset raises then.
    import zoneinfo as _zoneinfo

    NYC_TZ: Final = _zoneinfo.ZoneInfo("America/New_York")
except Exception as _e:  # pragma: no cover - only on hosts without tz database
    NYC_TZ = None  # type: ignore[assignment]
    _ZONEINFO_ERROR = _e

TZ_NAME: Final = "America/New_York"
EST_OFFSET_S: Final = -5 * 3600
EDT_OFFSET_S: Final = -4 * 3600
UNIX_EPOCH_JD: Final = 2440587.5  # JD of 1970-01-01T00:00:00Z
J2000_JD: Final = 2451545.0  # 2000-01-01T12:00:00 TT
SECONDS_PER_DAY: Final = 86400

_DAYS_IN_MONTH: Final = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


# --------------------------------------------------------------------------- calendar arithmetic
def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError(f"month out of range: {month}")
    if month == 2 and is_leap_year(year):
        return 29
    return _DAYS_IN_MONTH[month - 1]


def day_of_week(year: int, month: int, day: int) -> int:
    """0 = Sunday … 6 = Saturday (Sakamoto's algorithm, proleptic Gregorian)."""
    t = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    if month < 3:
        year -= 1
    return (year + year // 4 - year // 100 + year // 400 + t[month - 1] + day) % 7


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> int:
    """Day-of-month of the n-th (1-based) given weekday (0 = Sunday)."""
    if not 1 <= n <= 5:
        raise ValueError("n must be 1..5")
    first = 1 + (weekday - day_of_week(year, month, 1)) % 7
    d = first + 7 * (n - 1)
    if d > days_in_month(year, month):
        raise ValueError(f"no {n}-th weekday {weekday} in {year}-{month:02d}")
    return d


def last_weekday_of_month(year: int, month: int, weekday: int) -> int:
    dim = days_in_month(year, month)
    return dim - (day_of_week(year, month, dim) - weekday) % 7


def days_from_civil(year: int, month: int, day: int) -> int:
    """Days since 1970-01-01 for a proleptic Gregorian date (H. Hinnant's algorithm, exact for all int years)."""
    y = year - (month <= 2)
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    mp = (month + 9) % 12
    doy = (153 * mp + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(days: int) -> tuple[int, int, int]:
    """Inverse of :func:`days_from_civil`."""
    z = days + 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return (y + (m <= 2), m, d)


def unix_from_civil_utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> int:
    return days_from_civil(year, month, day) * SECONDS_PER_DAY + hour * 3600 + minute * 60 + second


# --------------------------------------------------------------------------- US DST rule (arithmetic)
@dataclass(frozen=True)
class DstBounds:
    """DST interval for one year as POSIX seconds: DST in effect for start_unix <= t < end_unix."""

    year: int
    start_unix: int  # instant local standard time reaches 02:00 (= 07:00 UTC) on the start date
    end_unix: int  # instant local daylight time reaches 02:00 (= 06:00 UTC) on the end date
    start_date: tuple[int, int, int]
    end_date: tuple[int, int, int]


def us_dst_bounds(year: int) -> DstBounds:
    """DST start/end for America/New_York under the federal rules in force that year.

    * 2007-…  : second Sunday of March 02:00 EST  -> first Sunday of November 02:00 EDT
    * 1987-2006: first Sunday of April 02:00 EST   -> last Sunday of October 02:00 EDT
    * 1976-1986: last Sunday of April 02:00 EST    -> last Sunday of October 02:00 EDT
    * 1975     : 23 February (Emergency DST Act)   -> last Sunday of October (26 Oct)
    * 1974     : 6 January  (Emergency DST Act)    -> last Sunday of October (27 Oct)
    * 1967-1973: last Sunday of April              -> last Sunday of October (Uniform Time Act 1966)

    Years before 1967 had New York City ordinances not reducible to a single arithmetic rule; callers
    must use :func:`zoneinfo_offset` there (a ValueError is raised).
    """
    if year < 1967:
        raise ValueError("US federal DST rule arithmetic is defined for 1967 onwards; use zoneinfo for earlier years")
    if year >= 2007:
        sm, sd = 3, nth_weekday_of_month(year, 3, 0, 2)
        em, ed = 11, nth_weekday_of_month(year, 11, 0, 1)
    elif year >= 1987:
        sm, sd = 4, nth_weekday_of_month(year, 4, 0, 1)
        em, ed = 10, last_weekday_of_month(year, 10, 0)
    elif year == 1974:
        sm, sd = 1, 6
        em, ed = 10, last_weekday_of_month(year, 10, 0)
    elif year == 1975:
        sm, sd = 2, 23
        em, ed = 10, last_weekday_of_month(year, 10, 0)
    else:  # 1967-1973, 1976-1986
        sm, sd = 4, last_weekday_of_month(year, 4, 0)
        em, ed = 10, last_weekday_of_month(year, 10, 0)
    # 02:00 local standard time = 07:00 UTC ; 02:00 local daylight time = 06:00 UTC
    start = unix_from_civil_utc(year, sm, sd, 2) - EST_OFFSET_S
    end = unix_from_civil_utc(year, em, ed, 2) - EDT_OFFSET_S
    return DstBounds(year, start, end, (year, sm, sd), (year, em, ed))


def us_dst_offset(unix_s: float) -> tuple[int, bool]:
    """(UTC offset seconds, is_dst) for America/New_York from the arithmetic rule. Valid 1967-01-01 onwards."""
    days = math.floor(unix_s / SECONDS_PER_DAY)
    year = civil_from_days(int(days))[0]
    b = us_dst_bounds(year)
    if b.start_unix <= unix_s < b.end_unix:
        return EDT_OFFSET_S, True
    return EST_OFFSET_S, False


def zoneinfo_offset(unix_s: float) -> tuple[int, bool]:
    """(UTC offset seconds, is_dst) from the IANA database (authoritative cross-check)."""
    if NYC_TZ is None:  # pragma: no cover
        raise RuntimeError(f"tz database unavailable: {_ZONEINFO_ERROR}")
    t = _dt.datetime.fromtimestamp(unix_s, tz=_dt.timezone.utc).astimezone(NYC_TZ)
    off = t.utcoffset()
    dst = t.dst()
    assert off is not None
    return int(off.total_seconds()), bool(dst and dst.total_seconds() != 0)


def nyc_offset(unix_s: float) -> tuple[int, bool]:
    """Preferred offset: zoneinfo when available (covers pre-1967 history), else the arithmetic rule."""
    if NYC_TZ is not None:
        return zoneinfo_offset(unix_s)
    return us_dst_offset(unix_s)


# --------------------------------------------------------------------------- Julian day
def julian_day(utc: _dt.datetime) -> float:
    """Julian Day for a UTC instant (Meeus ch. 7 / SPA eq. 4). Naive datetimes are taken as UTC."""
    if utc.tzinfo is not None:
        utc = utc.astimezone(_dt.timezone.utc)
    y, m = utc.year, utc.month
    d = utc.day + (utc.hour + (utc.minute + (utc.second + utc.microsecond / 1e6) / 60.0) / 60.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = math.floor(y / 100.0)
    b = 2 - a + math.floor(a / 4.0)  # Gregorian calendar (all dates handled here are Gregorian)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def julian_day_from_unix(unix_s: float) -> float:
    return unix_s / SECONDS_PER_DAY + UNIX_EPOCH_JD


def unix_from_julian_day(jd: float) -> float:
    return (jd - UNIX_EPOCH_JD) * SECONDS_PER_DAY


def datetime_from_julian_day(jd: float) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(unix_from_julian_day(jd), tz=_dt.timezone.utc)


# --------------------------------------------------------------------------- Delta T (TT - UT1)
# TAI-UTC after each leap second (UTC date the new value took effect). Complete as of 2026-09; no leap
# second has been scheduled since 2017-01-01 (IERS Bulletin C). TT = TAI + 32.184 s.
LEAP_SECONDS: Final[tuple[tuple[tuple[int, int, int], int], ...]] = (
    ((1972, 1, 1), 10), ((1972, 7, 1), 11), ((1973, 1, 1), 12), ((1974, 1, 1), 13), ((1975, 1, 1), 14),
    ((1976, 1, 1), 15), ((1977, 1, 1), 16), ((1978, 1, 1), 17), ((1979, 1, 1), 18), ((1980, 1, 1), 19),
    ((1981, 7, 1), 20), ((1982, 7, 1), 21), ((1983, 7, 1), 22), ((1985, 7, 1), 23), ((1988, 1, 1), 24),
    ((1990, 1, 1), 25), ((1991, 1, 1), 26), ((1992, 7, 1), 27), ((1993, 7, 1), 28), ((1994, 7, 1), 29),
    ((1996, 1, 1), 30), ((1997, 7, 1), 31), ((1999, 1, 1), 32), ((2006, 1, 1), 33), ((2009, 1, 1), 34),
    ((2012, 7, 1), 35), ((2015, 7, 1), 36), ((2017, 1, 1), 37),
)
TT_MINUS_TAI_S: Final = 32.184


def tai_minus_utc(unix_s: float) -> int:
    """TAI-UTC (whole seconds) in force at a POSIX instant; 10 s before 1972 by convention here."""
    v = 10
    for (y, m, d), n in LEAP_SECONDS:
        if unix_s >= unix_from_civil_utc(y, m, d):
            v = n
        else:
            break
    return v


def delta_t_polynomial(year_decimal: float) -> float:
    """Espenak & Meeus (2006) polynomial fit for ΔT (seconds), years -500 .. 2150 (NASA eclipse web site).

    Used only for dates before 1972 (no leap-second bookkeeping) and after the era covered by
    :data:`LEAP_SECONDS` + 20 years, where the physical relation below no longer applies.
    """
    y = year_decimal
    if y < -500:
        u = (y - 1820) / 100
        return -20 + 32 * u * u
    if y < 500:
        u = y / 100
        return 10583.6 - 1014.41 * u + 33.78311 * u**2 - 5.952053 * u**3 - 0.1798452 * u**4 + 0.022174192 * u**5 + 0.0090316521 * u**6
    if y < 1600:
        u = (y - 1000) / 100
        return 1574.2 - 556.01 * u + 71.23472 * u**2 + 0.319781 * u**3 - 0.8503463 * u**4 - 0.005050998 * u**5 + 0.0083572073 * u**6
    if y < 1700:
        t = y - 1600
        return 120 - 0.9808 * t - 0.01532 * t**2 + t**3 / 7129
    if y < 1800:
        t = y - 1700
        return 8.83 + 0.1603 * t - 0.0059285 * t**2 + 0.00013336 * t**3 - t**4 / 1174000
    if y < 1860:
        t = y - 1800
        return 13.72 - 0.332447 * t + 0.0068612 * t**2 + 0.0041116 * t**3 - 0.00037436 * t**4 + 0.0000121272 * t**5 - 0.0000001699 * t**6 + 0.000000000875 * t**7
    if y < 1900:
        t = y - 1860
        return 7.62 + 0.5737 * t - 0.251754 * t**2 + 0.01680668 * t**3 - 0.0004473624 * t**4 + t**5 / 233174
    if y < 1920:
        t = y - 1900
        return -2.79 + 1.494119 * t - 0.0598939 * t**2 + 0.0061966 * t**3 - 0.000197 * t**4
    if y < 1941:
        t = y - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    if y < 1961:
        t = y - 1950
        return 29.07 + 0.407 * t - t**2 / 233 + t**3 / 2547
    if y < 1986:
        t = y - 1975
        return 45.45 + 1.067 * t - t**2 / 260 - t**3 / 718
    if y < 2005:
        t = y - 2000
        return 63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3 + 0.000651814 * t**4 + 0.00002373599 * t**5
    if y < 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    if y < 2150:
        u = (y - 1820) / 100
        return -20 + 32 * u * u - 0.5628 * (2150 - y)
    u = (y - 1820) / 100
    return -20 + 32 * u * u


def delta_t_seconds(unix_s: float, dut1_s: float = 0.0) -> float:
    """ΔT = TT − UT1 in seconds at a POSIX instant.

    From 1972 to (last leap second + 20 y) the exact relation ΔT = 32.184 + (TAI−UTC) − DUT1 is used with
    DUT1 = ``dut1_s`` (|DUT1| < 0.9 s by the definition of UTC, so the default 0 is within 0.9 s of truth,
    i.e. < 0.004° of hour angle). Outside that span the Espenak–Meeus polynomial is used.
    """
    year = civil_from_days(math.floor(unix_s / SECONDS_PER_DAY))[0]
    last_leap_year = LEAP_SECONDS[-1][0][0]
    if unix_s < unix_from_civil_utc(1972, 1, 1) or year > last_leap_year + 20:
        frac = (unix_s - unix_from_civil_utc(year, 1, 1)) / ((366 if is_leap_year(year) else 365) * SECONDS_PER_DAY)
        return delta_t_polynomial(year + frac)
    return TT_MINUS_TAI_S + tai_minus_utc(unix_s) - dut1_s


# --------------------------------------------------------------------------- SimTime
@dataclass(frozen=True)
class SimTime:
    """Everything the engine needs from the clock, computed once per frame from a single UTC instant."""

    utc: _dt.datetime
    unix_s: float
    jd: float  # Julian Day (UT)
    jde: float  # Julian Ephemeris Day (TT) = jd + delta_t/86400
    delta_t_s: float
    local: _dt.datetime  # tz-aware America/New_York
    utc_offset_s: int
    is_dst: bool
    tz_abbreviation: str  # "EST" | "EDT"
    local_date: tuple[int, int, int]
    seconds_since_local_midnight: float
    day_of_year: int
    dst_start_unix: int
    dst_end_unix: int

    @property
    def local_hours(self) -> float:
        return self.seconds_since_local_midnight / 3600.0

    def as_dict(self) -> dict:
        return {
            "utc": self.utc.isoformat().replace("+00:00", "Z"),
            "unix_s": self.unix_s,
            "jd": self.jd,
            "jde": self.jde,
            "delta_t_s": self.delta_t_s,
            "local": self.local.isoformat(),
            "utc_offset_s": self.utc_offset_s,
            "is_dst": self.is_dst,
            "tz": self.tz_abbreviation,
            "local_date": "%04d-%02d-%02d" % self.local_date,
            "seconds_since_local_midnight": self.seconds_since_local_midnight,
            "day_of_year": self.day_of_year,
        }


def sim_time(utc: _dt.datetime) -> SimTime:
    """Build a :class:`SimTime` for a UTC instant (naive datetimes are treated as UTC)."""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=_dt.timezone.utc)
    else:
        utc = utc.astimezone(_dt.timezone.utc)
    unix_s = utc.timestamp()
    off, dst = nyc_offset(unix_s)
    local_tz = _dt.timezone(_dt.timedelta(seconds=off), "EDT" if dst else "EST")
    local = utc.astimezone(local_tz)
    jd = julian_day(utc)
    dt_s = delta_t_seconds(unix_s)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    ssm = (local - midnight).total_seconds()
    b = us_dst_bounds(local.year) if local.year >= 1967 else None
    return SimTime(
        utc=utc,
        unix_s=unix_s,
        jd=jd,
        jde=jd + dt_s / SECONDS_PER_DAY,
        delta_t_s=dt_s,
        local=local,
        utc_offset_s=off,
        is_dst=dst,
        tz_abbreviation="EDT" if dst else "EST",
        local_date=(local.year, local.month, local.day),
        seconds_since_local_midnight=ssm,
        day_of_year=local.timetuple().tm_yday,
        dst_start_unix=b.start_unix if b else 0,
        dst_end_unix=b.end_unix if b else 0,
    )


def sim_time_now() -> SimTime:
    """Current real time (system clock, UTC) mapped to New York civil time."""
    return sim_time(_dt.datetime.now(tz=_dt.timezone.utc))
