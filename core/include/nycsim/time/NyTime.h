// nycsim/time/NyTime.h — civil time for the simulation: UTC <-> America/New_York, the US federal
// DST rule as arithmetic, Julian day and Delta-T (ARCHITECTURE §11).
//
// This is the C++ port of services/nycsim_live/timesync.py; every function here has a
// same-named Python counterpart and the test suite cross-checks the DST rule against a table
// generated with Python `zoneinfo` for every day 2007-01-01 .. 2099-12-31 plus every hour of every
// transition day (docs/verification/core/gen_dst.py).
//
// The namespace is `nytime` rather than `time` so that unqualified calls to the C library's
// ::time() inside nycsim code keep resolving.
//
// Conventions
//   * Proleptic Gregorian civil dates; POSIX seconds (no leap seconds, every UTC day is 86400 s).
//   * Offsets are seconds to ADD to UTC to get local time (EST -18000, EDT -14400).
//   * Nothing allocates; nothing throws; no static initialisation with side effects.
#pragma once

#include <cstdint>

#include "nycsim/Config.h"
#include "nycsim/util/Result.h"

namespace nycsim {
namespace nytime {

inline constexpr int64_t kSecondsPerDay = 86400;
inline constexpr int32_t kEstOffsetS = -5 * 3600;
inline constexpr int32_t kEdtOffsetS = -4 * 3600;
inline constexpr double kUnixEpochJd = 2440587.5;  ///< JD of 1970-01-01T00:00:00Z
inline constexpr double kJ2000Jd = 2451545.0;      ///< 2000-01-01T12:00:00 TT
inline constexpr double kTtMinusTaiS = 32.184;
inline constexpr const char* kTzName = "America/New_York";
/// Earliest year for which the arithmetic US federal rule is defined (Uniform Time Act 1966).
inline constexpr int kFirstArithmeticDstYear = 1967;

struct Date {
  int32_t year = 1970;
  int32_t month = 1;  ///< 1..12
  int32_t day = 1;    ///< 1..31
};

struct DateTime {
  int32_t year = 1970;
  int32_t month = 1;
  int32_t day = 1;
  int32_t hour = 0;
  int32_t minute = 0;
  double second = 0.0;
};

// ---- calendar arithmetic -------------------------------------------------------------------------

NYCSIM_API bool isLeapYear(int32_t year);
/// Days in a month; 0 when `month` is outside 1..12.
NYCSIM_API int32_t daysInMonth(int32_t year, int32_t month);
/// 0 = Sunday .. 6 = Saturday (Sakamoto, proleptic Gregorian).
NYCSIM_API int32_t dayOfWeek(int32_t year, int32_t month, int32_t day);
/// Day-of-month of the n-th (1-based) `weekday` (0 = Sunday) of the month; 0 if there is no such day.
NYCSIM_API int32_t nthWeekdayOfMonth(int32_t year, int32_t month, int32_t weekday, int32_t n);
/// Day-of-month of the last `weekday` of the month.
NYCSIM_API int32_t lastWeekdayOfMonth(int32_t year, int32_t month, int32_t weekday);
/// Days since 1970-01-01 (Howard Hinnant's algorithm; exact for the whole int32 year range).
NYCSIM_API int64_t daysFromCivil(int32_t year, int32_t month, int32_t day);
/// Inverse of daysFromCivil.
NYCSIM_API Date civilFromDays(int64_t days);
NYCSIM_API int64_t unixFromCivilUtc(int32_t year, int32_t month, int32_t day, int32_t hour = 0,
                                    int32_t minute = 0, int32_t second = 0);
/// Splits a POSIX instant into UTC calendar fields (seconds carry the fractional part).
NYCSIM_API DateTime civilFromUnix(double unix_s);
/// 1..366 for a civil date.
NYCSIM_API int32_t dayOfYear(int32_t year, int32_t month, int32_t day);

// ---- US federal DST rule -------------------------------------------------------------------------

struct DstBounds {
  int32_t year = 0;
  int64_t startUnix = 0;  ///< instant local standard time reaches 02:00 (07:00 UTC) on the start date
  int64_t endUnix = 0;    ///< instant local daylight time reaches 02:00 (06:00 UTC) on the end date
  Date startDate;
  Date endDate;
};

/// DST interval for America/New_York under the federal rules in force that year (>= 1967):
///   2007-  : 2nd Sunday of March 02:00 EST -> 1st Sunday of November 02:00 EDT
///   1987-2006: 1st Sunday of April        -> last Sunday of October
///   1976-1986: last Sunday of April       -> last Sunday of October
///   1975     : 23 February (Emergency Daylight Saving Time Energy Act) -> last Sunday of October
///   1974     : 6 January                  -> last Sunday of October
///   1967-1973: last Sunday of April       -> last Sunday of October
/// Years before 1967 are city/state ordinances that are not reducible to one arithmetic rule and
/// are rejected (ErrorCode::OutOfRange).
NYCSIM_API Result<DstBounds> usDstBounds(int32_t year);

struct Offset {
  int32_t seconds = kEstOffsetS;
  bool isDst = false;
  const char* abbreviation = "EST";  ///< "EST" | "EDT"
};

/// UTC offset of America/New_York at a POSIX instant (>= 1967-01-01).
NYCSIM_API Result<Offset> nyOffset(double unix_s);

/// True when the *local* wall clock reading `unix_s + offset` is inside the repeated hour of the
/// autumn transition (the hour 01:00-01:59 local occurs twice). Useful for UI disambiguation.
NYCSIM_API bool inAmbiguousLocalHour(double unix_s);

// ---- Julian day ----------------------------------------------------------------------------------

/// Julian Day of a UTC calendar instant (Meeus ch. 7 / SPA eq. 4, Gregorian branch).
NYCSIM_API double julianDay(const DateTime& utc);
NYCSIM_API double julianDayFromUnix(double unix_s);
NYCSIM_API double unixFromJulianDay(double jd);

// ---- Delta-T (TT - UT1) --------------------------------------------------------------------------

/// TAI-UTC (whole seconds) in force at a POSIX instant; 10 s before 1972 by convention.
NYCSIM_API int32_t taiMinusUtc(double unix_s);
/// Espenak & Meeus (2006) polynomial fit for Delta-T in seconds, years -500 .. 2150+.
NYCSIM_API double deltaTPolynomial(double yearDecimal);
/// Delta-T = TT - UT1 (seconds). Between 1972 and (last leap second + 20 y) the exact relation
/// 32.184 + (TAI-UTC) - DUT1 is used; outside that span the polynomial is used.
NYCSIM_API double deltaTSeconds(double unix_s, double dut1_s = 0.0);

// ---- SimTime -------------------------------------------------------------------------------------

/// Everything the engine needs from the clock, computed once per frame from one UTC instant.
struct SimTime {
  double unixS = 0.0;
  DateTime utc;
  double jd = 0.0;        ///< Julian Day (UT)
  double jde = 0.0;       ///< Julian Ephemeris Day (TT)
  double deltaTS = 0.0;
  DateTime local;         ///< America/New_York wall clock
  int32_t utcOffsetS = kEstOffsetS;
  bool isDst = false;
  const char* tzAbbreviation = "EST";
  double secondsSinceLocalMidnight = 0.0;
  int32_t dayOfYear = 1;  ///< of the local date
  int64_t dstStartUnix = 0;
  int64_t dstEndUnix = 0;

  double localHours() const { return secondsSinceLocalMidnight / 3600.0; }
};

NYCSIM_API Result<SimTime> simTime(double unix_s);

}  // namespace nytime
}  // namespace nycsim
