#include "nycsim/time/NyTime.h"

#include <cmath>

namespace nycsim {
namespace nytime {

namespace {

constexpr int32_t kDaysInMonth[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};

/// Floor division for int64 (C++ / truncates towards zero).
int64_t floorDiv(int64_t a, int64_t b) {
  const int64_t q = a / b;
  return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q;
}

/// TAI-UTC after each leap second, as (year, month, day, value). Complete as of 2026-09; no leap
/// second has been scheduled since 2017-01-01 (IERS Bulletin C).
struct LeapEntry {
  int32_t year, month, day, tai;
};
constexpr LeapEntry kLeapSeconds[] = {
    {1972, 1, 1, 10},  {1972, 7, 1, 11},  {1973, 1, 1, 12},  {1974, 1, 1, 13},  {1975, 1, 1, 14},
    {1976, 1, 1, 15},  {1977, 1, 1, 16},  {1978, 1, 1, 17},  {1979, 1, 1, 18},  {1980, 1, 1, 19},
    {1981, 7, 1, 20},  {1982, 7, 1, 21},  {1983, 7, 1, 22},  {1985, 7, 1, 23},  {1988, 1, 1, 24},
    {1990, 1, 1, 25},  {1991, 1, 1, 26},  {1992, 7, 1, 27},  {1993, 7, 1, 28},  {1994, 7, 1, 29},
    {1996, 1, 1, 30},  {1997, 7, 1, 31},  {1999, 1, 1, 32},  {2006, 1, 1, 33},  {2009, 1, 1, 34},
    {2012, 7, 1, 35},  {2015, 7, 1, 36},  {2017, 1, 1, 37},
};
constexpr int kLeapCount = static_cast<int>(sizeof(kLeapSeconds) / sizeof(kLeapSeconds[0]));

double poly(const double* c, int n, double t) {
  double v = 0.0;
  for (int i = n - 1; i >= 0; --i) v = v * t + c[i];
  return v;
}

}  // namespace

// ---- calendar arithmetic -------------------------------------------------------------------------

bool isLeapYear(int32_t year) {
  return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}

int32_t daysInMonth(int32_t year, int32_t month) {
  if (month < 1 || month > 12) return 0;
  if (month == 2 && isLeapYear(year)) return 29;
  return kDaysInMonth[month - 1];
}

int32_t dayOfWeek(int32_t year, int32_t month, int32_t day) {
  static const int32_t t[12] = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4};
  if (month < 1 || month > 12) return 0;
  int64_t y = year;
  if (month < 3) --y;
  const int64_t s = y + floorDiv(y, 4) - floorDiv(y, 100) + floorDiv(y, 400) + t[month - 1] + day;
  const int64_t m = s % 7;
  return static_cast<int32_t>(m < 0 ? m + 7 : m);
}

int32_t nthWeekdayOfMonth(int32_t year, int32_t month, int32_t weekday, int32_t n) {
  if (n < 1 || n > 5 || weekday < 0 || weekday > 6) return 0;
  const int32_t dim = daysInMonth(year, month);
  if (dim == 0) return 0;
  const int32_t first = 1 + ((weekday - dayOfWeek(year, month, 1)) % 7 + 7) % 7;
  const int32_t d = first + 7 * (n - 1);
  return d > dim ? 0 : d;
}

int32_t lastWeekdayOfMonth(int32_t year, int32_t month, int32_t weekday) {
  const int32_t dim = daysInMonth(year, month);
  if (dim == 0 || weekday < 0 || weekday > 6) return 0;
  return dim - ((dayOfWeek(year, month, dim) - weekday) % 7 + 7) % 7;
}

int64_t daysFromCivil(int32_t year, int32_t month, int32_t day) {
  int64_t y = year;
  y -= month <= 2;
  const int64_t era = floorDiv(y, 400);
  const int64_t yoe = y - era * 400;                                       // [0, 399]
  const int64_t mp = (static_cast<int64_t>(month) + 9) % 12;               // [0, 11]
  const int64_t doy = (153 * mp + 2) / 5 + day - 1;                        // [0, 365]
  const int64_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;               // [0, 146096]
  return era * 146097 + doe - 719468;
}

Date civilFromDays(int64_t days) {
  const int64_t z = days + 719468;
  const int64_t era = floorDiv(z, 146097);
  const int64_t doe = z - era * 146097;                                       // [0, 146096]
  const int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;  // [0, 399]
  const int64_t y = yoe + era * 400;
  const int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);                // [0, 365]
  const int64_t mp = (5 * doy + 2) / 153;                                     // [0, 11]
  const int64_t d = doy - (153 * mp + 2) / 5 + 1;                             // [1, 31]
  const int64_t m = mp < 10 ? mp + 3 : mp - 9;                                // [1, 12]
  Date out;
  out.year = static_cast<int32_t>(y + (m <= 2));
  out.month = static_cast<int32_t>(m);
  out.day = static_cast<int32_t>(d);
  return out;
}

int64_t unixFromCivilUtc(int32_t year, int32_t month, int32_t day, int32_t hour, int32_t minute,
                         int32_t second) {
  return daysFromCivil(year, month, day) * kSecondsPerDay + hour * 3600 + minute * 60 + second;
}

DateTime civilFromUnix(double unix_s) {
  const double dayF = std::floor(unix_s / static_cast<double>(kSecondsPerDay));
  const int64_t days = static_cast<int64_t>(dayF);
  double rem = unix_s - dayF * static_cast<double>(kSecondsPerDay);
  if (rem < 0.0) rem = 0.0;
  if (rem >= static_cast<double>(kSecondsPerDay)) rem = std::nextafter(static_cast<double>(kSecondsPerDay), 0.0);
  const Date d = civilFromDays(days);
  DateTime out;
  out.year = d.year;
  out.month = d.month;
  out.day = d.day;
  out.hour = static_cast<int32_t>(rem / 3600.0);
  rem -= out.hour * 3600.0;
  out.minute = static_cast<int32_t>(rem / 60.0);
  out.second = rem - out.minute * 60.0;
  return out;
}

int32_t dayOfYear(int32_t year, int32_t month, int32_t day) {
  return static_cast<int32_t>(daysFromCivil(year, month, day) - daysFromCivil(year, 1, 1)) + 1;
}

// ---- US federal DST rule -------------------------------------------------------------------------

Result<DstBounds> usDstBounds(int32_t year) {
  if (year < kFirstArithmeticDstYear) {
    return fail(ErrorCode::OutOfRange,
                "nytime: the arithmetic US DST rule is defined from 1967; earlier years need the IANA database",
                year);
  }
  int32_t sm = 0, sd = 0, em = 0, ed = 0;
  if (year >= 2007) {
    sm = 3;
    sd = nthWeekdayOfMonth(year, 3, 0, 2);
    em = 11;
    ed = nthWeekdayOfMonth(year, 11, 0, 1);
  } else if (year >= 1987) {
    sm = 4;
    sd = nthWeekdayOfMonth(year, 4, 0, 1);
    em = 10;
    ed = lastWeekdayOfMonth(year, 10, 0);
  } else if (year == 1974) {
    sm = 1;
    sd = 6;
    em = 10;
    ed = lastWeekdayOfMonth(year, 10, 0);
  } else if (year == 1975) {
    sm = 2;
    sd = 23;
    em = 10;
    ed = lastWeekdayOfMonth(year, 10, 0);
  } else {  // 1967-1973 and 1976-1986
    sm = 4;
    sd = lastWeekdayOfMonth(year, 4, 0);
    em = 10;
    ed = lastWeekdayOfMonth(year, 10, 0);
  }
  if (sd == 0 || ed == 0) return fail(ErrorCode::Internal, "nytime: DST date arithmetic failed", year);
  DstBounds b;
  b.year = year;
  b.startDate = Date{year, sm, sd};
  b.endDate = Date{year, em, ed};
  // 02:00 local standard time == 07:00 UTC; 02:00 local daylight time == 06:00 UTC.
  b.startUnix = unixFromCivilUtc(year, sm, sd, 2) - kEstOffsetS;
  b.endUnix = unixFromCivilUtc(year, em, ed, 2) - kEdtOffsetS;
  return b;
}

Result<Offset> nyOffset(double unix_s) {
  if (!std::isfinite(unix_s)) return fail(ErrorCode::InvalidArgument, "nytime: non-finite instant");
  const int64_t days = static_cast<int64_t>(std::floor(unix_s / static_cast<double>(kSecondsPerDay)));
  const int32_t year = civilFromDays(days).year;
  NYCSIM_TRY(b, usDstBounds(year));
  Offset o;
  if (unix_s >= static_cast<double>(b.startUnix) && unix_s < static_cast<double>(b.endUnix)) {
    o.seconds = kEdtOffsetS;
    o.isDst = true;
    o.abbreviation = "EDT";
  }
  return o;
}

bool inAmbiguousLocalHour(double unix_s) {
  if (!std::isfinite(unix_s)) return false;
  const int64_t days = static_cast<int64_t>(std::floor(unix_s / static_cast<double>(kSecondsPerDay)));
  const int32_t year = civilFromDays(days).year;
  const Result<DstBounds> b = usDstBounds(year);
  if (!b) return false;
  const double end = static_cast<double>(b.value().endUnix);
  return unix_s >= end && unix_s < end + 3600.0;
}

// ---- Julian day ----------------------------------------------------------------------------------

double julianDay(const DateTime& utc) {
  int32_t y = utc.year;
  int32_t m = utc.month;
  const double d = utc.day + (utc.hour + (utc.minute + utc.second / 60.0) / 60.0) / 24.0;
  if (m <= 2) {
    y -= 1;
    m += 12;
  }
  const double a = std::floor(y / 100.0);
  const double b = 2.0 - a + std::floor(a / 4.0);  // Gregorian
  return std::floor(365.25 * (y + 4716)) + std::floor(30.6001 * (m + 1)) + d + b - 1524.5;
}

double julianDayFromUnix(double unix_s) {
  return unix_s / static_cast<double>(kSecondsPerDay) + kUnixEpochJd;
}

double unixFromJulianDay(double jd) {
  return (jd - kUnixEpochJd) * static_cast<double>(kSecondsPerDay);
}

// ---- Delta-T -------------------------------------------------------------------------------------

int32_t taiMinusUtc(double unix_s) {
  int32_t v = 10;
  for (int i = 0; i < kLeapCount; ++i) {
    const LeapEntry& e = kLeapSeconds[i];
    if (unix_s >= static_cast<double>(unixFromCivilUtc(e.year, e.month, e.day))) {
      v = e.tai;
    } else {
      break;
    }
  }
  return v;
}

double deltaTPolynomial(double y) {
  double u = 0.0, t = 0.0;
  if (y < -500.0) {
    u = (y - 1820.0) / 100.0;
    return -20.0 + 32.0 * u * u;
  }
  if (y < 500.0) {
    u = y / 100.0;
    const double c[7] = {10583.6, -1014.41, 33.78311, -5.952053, -0.1798452, 0.022174192, 0.0090316521};
    return poly(c, 7, u);
  }
  if (y < 1600.0) {
    u = (y - 1000.0) / 100.0;
    const double c[7] = {1574.2, -556.01, 71.23472, 0.319781, -0.8503463, -0.005050998, 0.0083572073};
    return poly(c, 7, u);
  }
  if (y < 1700.0) {
    t = y - 1600.0;
    return 120.0 - 0.9808 * t - 0.01532 * t * t + t * t * t / 7129.0;
  }
  if (y < 1800.0) {
    t = y - 1700.0;
    return 8.83 + 0.1603 * t - 0.0059285 * t * t + 0.00013336 * t * t * t - t * t * t * t / 1174000.0;
  }
  if (y < 1860.0) {
    t = y - 1800.0;
    const double c[8] = {13.72,        -0.332447,     0.0068612,      0.0041116,
                         -0.00037436,  0.0000121272,  -0.0000001699,  0.000000000875};
    return poly(c, 8, t);
  }
  if (y < 1900.0) {
    t = y - 1860.0;
    return 7.62 + 0.5737 * t - 0.251754 * t * t + 0.01680668 * t * t * t -
           0.0004473624 * t * t * t * t + t * t * t * t * t / 233174.0;
  }
  if (y < 1920.0) {
    t = y - 1900.0;
    const double c[5] = {-2.79, 1.494119, -0.0598939, 0.0061966, -0.000197};
    return poly(c, 5, t);
  }
  if (y < 1941.0) {
    t = y - 1920.0;
    const double c[4] = {21.20, 0.84493, -0.076100, 0.0020936};
    return poly(c, 4, t);
  }
  if (y < 1961.0) {
    t = y - 1950.0;
    return 29.07 + 0.407 * t - t * t / 233.0 + t * t * t / 2547.0;
  }
  if (y < 1986.0) {
    t = y - 1975.0;
    return 45.45 + 1.067 * t - t * t / 260.0 - t * t * t / 718.0;
  }
  if (y < 2005.0) {
    t = y - 2000.0;
    const double c[6] = {63.86, 0.3345, -0.060374, 0.0017275, 0.000651814, 0.00002373599};
    return poly(c, 6, t);
  }
  if (y < 2050.0) {
    t = y - 2000.0;
    return 62.92 + 0.32217 * t + 0.005589 * t * t;
  }
  if (y < 2150.0) {
    u = (y - 1820.0) / 100.0;
    return -20.0 + 32.0 * u * u - 0.5628 * (2150.0 - y);
  }
  u = (y - 1820.0) / 100.0;
  return -20.0 + 32.0 * u * u;
}

double deltaTSeconds(double unix_s, double dut1_s) {
  if (!std::isfinite(unix_s)) return 0.0;
  const int64_t days = static_cast<int64_t>(std::floor(unix_s / static_cast<double>(kSecondsPerDay)));
  const int32_t year = civilFromDays(days).year;
  const int32_t lastLeapYear = kLeapSeconds[kLeapCount - 1].year;
  if (unix_s < static_cast<double>(unixFromCivilUtc(1972, 1, 1)) || year > lastLeapYear + 20) {
    const double yearStart = static_cast<double>(unixFromCivilUtc(year, 1, 1));
    const double yearLen = (isLeapYear(year) ? 366.0 : 365.0) * static_cast<double>(kSecondsPerDay);
    return deltaTPolynomial(year + (unix_s - yearStart) / yearLen);
  }
  return kTtMinusTaiS + taiMinusUtc(unix_s) - dut1_s;
}

// ---- SimTime -------------------------------------------------------------------------------------

Result<SimTime> simTime(double unix_s) {
  if (!std::isfinite(unix_s)) return fail(ErrorCode::InvalidArgument, "nytime: non-finite instant");
  NYCSIM_TRY(off, nyOffset(unix_s));
  SimTime t;
  t.unixS = unix_s;
  t.utc = civilFromUnix(unix_s);
  t.jd = julianDay(t.utc);
  t.deltaTS = deltaTSeconds(unix_s);
  t.jde = t.jd + t.deltaTS / static_cast<double>(kSecondsPerDay);
  t.utcOffsetS = off.seconds;
  t.isDst = off.isDst;
  t.tzAbbreviation = off.abbreviation;
  const double localUnix = unix_s + off.seconds;
  t.local = civilFromUnix(localUnix);
  t.secondsSinceLocalMidnight =
      t.local.hour * 3600.0 + t.local.minute * 60.0 + t.local.second;
  t.dayOfYear = dayOfYear(t.local.year, t.local.month, t.local.day);
  const Result<DstBounds> b = usDstBounds(t.local.year);
  if (b) {
    t.dstStartUnix = b.value().startUnix;
    t.dstEndUnix = b.value().endUnix;
  }
  return t;
}

}  // namespace nytime
}  // namespace nycsim
