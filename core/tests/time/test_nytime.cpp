#include <doctest/doctest.h>

#include <cmath>
#include <string>

#include "dst_table.h"
#include "nycsim/time/NyTime.h"

using namespace nycsim;
using namespace nycsim::nytime;

namespace {

// Julian Day and Delta-T cross-check values produced by services/nycsim_live/timesync.py
// (python3 -c "from nycsim_live import timesync; timesync.julian_day(...)").
struct JdCase {
  int32_t y, mo, d, h, mi, s;
  double jd;
  double deltaT;
};
constexpr JdCase kJdCases[] = {
    {1970, 1, 1, 0, 0, 0, 2440587.5, 40.19294086136705},
    {2000, 1, 1, 12, 0, 0, 2451545.0, 64.184},
    {2003, 10, 17, 19, 30, 30, 2452930.312847222, 64.184},
    {2026, 9, 6, 11, 12, 13, 2461289.9668171294, 69.184},
    {1899, 12, 31, 12, 0, 0, 2415020.0, -2.7036201840062404},
    {2100, 3, 1, 0, 0, 0, 2488128.5, 203.12072251604408},
    {1582, 10, 15, 0, 0, 0, 2299160.5, 129.11506630267414},
    {2024, 2, 29, 23, 59, 59, 2460370.499988426, 69.184},
    {1972, 6, 30, 23, 59, 59, 2441499.499988426, 42.184},
    {2017, 1, 1, 0, 0, 0, 2457754.5, 69.184},
    {1968, 4, 28, 7, 0, 0, 2439974.7916666665, 38.568948932897975},
    {2050, 7, 4, 16, 20, 0, 2469992.1805555555, 94.03037538057062},
};

bool tableIsDst(int32_t dayIndex) {
  return (nycsim_test_dst::kIsDstBits[static_cast<size_t>(dayIndex) >> 3] &
          (1u << (static_cast<unsigned>(dayIndex) & 7u))) != 0;
}

}  // namespace

TEST_SUITE("time") {
  TEST_CASE("civil calendar arithmetic round-trips over four centuries") {
    CHECK(isLeapYear(2000));
    CHECK_FALSE(isLeapYear(1900));
    CHECK(isLeapYear(2024));
    CHECK_FALSE(isLeapYear(2023));
    CHECK(daysInMonth(2024, 2) == 29);
    CHECK(daysInMonth(2023, 2) == 28);
    CHECK(daysInMonth(2023, 13) == 0);
    // 1970-01-01 was a Thursday (4), 2026-09-06 a Sunday (0).
    CHECK(dayOfWeek(1970, 1, 1) == 4);
    CHECK(dayOfWeek(2026, 9, 6) == 0);
    CHECK(dayOfWeek(1900, 1, 1) == 1);
    CHECK(daysFromCivil(1970, 1, 1) == 0);
    CHECK(daysFromCivil(2000, 1, 1) == 10957);
    CHECK(unixFromCivilUtc(2000, 1, 1, 0, 0, 0) == 946684800);
    // days <-> civil is a bijection on 1800-01-01 .. 2199-12-31 (146,097 days).
    int64_t mismatches = 0;
    for (int64_t d = daysFromCivil(1800, 1, 1); d <= daysFromCivil(2199, 12, 31); ++d) {
      const Date c = civilFromDays(d);
      if (daysFromCivil(c.year, c.month, c.day) != d) ++mismatches;
      if (c.day < 1 || c.day > daysInMonth(c.year, c.month)) ++mismatches;
    }
    CHECK(mismatches == 0);
    CHECK(dayOfYear(2024, 12, 31) == 366);
    CHECK(dayOfYear(2023, 12, 31) == 365);
    CHECK(dayOfYear(2026, 9, 6) == 249);
    // nth / last weekday
    CHECK(nthWeekdayOfMonth(2026, 3, 0, 2) == 8);    // 2nd Sunday of March 2026
    CHECK(nthWeekdayOfMonth(2026, 11, 0, 1) == 1);   // 1st Sunday of November 2026
    CHECK(nthWeekdayOfMonth(2026, 2, 0, 5) == 0);    // no 5th Sunday in Feb 2026
    CHECK(lastWeekdayOfMonth(2026, 10, 0) == 25);
    CHECK(nthWeekdayOfMonth(2026, 3, 7, 1) == 0);    // invalid weekday
  }

  TEST_CASE("civilFromUnix / julianDay match timesync.py") {
    for (const JdCase& c : kJdCases) {
      DateTime t;
      t.year = c.y;
      t.month = c.mo;
      t.day = c.d;
      t.hour = c.h;
      t.minute = c.mi;
      t.second = c.s;
      CHECK(std::fabs(julianDay(t) - c.jd) < 1e-9);
      const int64_t u = unixFromCivilUtc(c.y, c.mo, c.d, c.h, c.mi, c.s);
      // julianDayFromUnix agrees with the calendar formula for post-1970 instants.
      if (c.y >= 1970) CHECK(std::fabs(julianDayFromUnix(static_cast<double>(u)) - c.jd) < 1e-9);
      CHECK(std::fabs(deltaTSeconds(static_cast<double>(u)) - c.deltaT) < 1e-9);
      const DateTime back = civilFromUnix(static_cast<double>(u));
      CHECK(back.year == c.y);
      CHECK(back.month == c.mo);
      CHECK(back.day == c.d);
      CHECK(back.hour == c.h);
      CHECK(back.minute == c.mi);
      CHECK(std::fabs(back.second - c.s) < 1e-6);
    }
    // Julian day <-> unix inverse over a long span.
    for (double u = -3.0e9; u <= 4.0e9; u += 7.77e6) {
      CHECK(std::fabs(unixFromJulianDay(julianDayFromUnix(u)) - u) < 1e-3);
    }
    CHECK(julianDayFromUnix(0.0) == kUnixEpochJd);
  }

  TEST_CASE("leap seconds and Delta-T model") {
    CHECK(taiMinusUtc(static_cast<double>(unixFromCivilUtc(1971, 1, 1))) == 10);
    CHECK(taiMinusUtc(static_cast<double>(unixFromCivilUtc(1972, 1, 1))) == 10 + 0);  // first entry is 10
    CHECK(taiMinusUtc(static_cast<double>(unixFromCivilUtc(1972, 7, 1))) == 11);
    CHECK(taiMinusUtc(static_cast<double>(unixFromCivilUtc(2016, 12, 31))) == 36);
    CHECK(taiMinusUtc(static_cast<double>(unixFromCivilUtc(2017, 1, 1))) == 37);
    CHECK(taiMinusUtc(static_cast<double>(unixFromCivilUtc(2026, 1, 1))) == 37);
    // 2000-01-01: the polynomial fit is anchored at 63.86 s.
    CHECK(deltaTPolynomial(2000.0) == doctest::Approx(63.86).epsilon(1e-9));
    // Between 1972 and 2037 the exact relation is used: 32.184 + (TAI-UTC).
    CHECK(deltaTSeconds(static_cast<double>(unixFromCivilUtc(2020, 6, 1))) ==
          doctest::Approx(32.184 + 37.0).epsilon(1e-12));
    // Beyond (last leap second + 20 y) the Espenak-Meeus polynomial takes over. The switch is a
    // real discontinuity of the model, identical in the Python reference: 69.184 s -> 83.233 s at
    // 2038-01-01 (the polynomial's extrapolated Delta-T assumes leap seconds that have not been
    // announced). It is asserted here so a change in either implementation is caught.
    const double a = deltaTSeconds(static_cast<double>(unixFromCivilUtc(2037, 12, 31)));
    const double b = deltaTSeconds(static_cast<double>(unixFromCivilUtc(2038, 1, 1)));
    CHECK(a == doctest::Approx(69.184).epsilon(1e-9));
    CHECK(b == doctest::Approx(83.232976).epsilon(1e-9));
    CHECK(std::fabs(b - a) == doctest::Approx(14.048976).epsilon(1e-6));
    CHECK(deltaTSeconds(std::nan("")) == 0.0);
  }

  TEST_CASE("US DST rule: transition instants match the IANA database for 2007-2099") {
    int failures = 0;
    for (const auto& row : nycsim_test_dst::kDstTransitions) {
      const int32_t year = static_cast<int32_t>(row[0]);
      const Result<DstBounds> b = usDstBounds(year);
      REQUIRE(b.ok());
      if (b.value().startUnix != row[1] || b.value().endUnix != row[2]) {
        ++failures;
        MESSAGE("year " << year << " start " << b.value().startUnix << " != " << row[1] << " end "
                        << b.value().endUnix << " != " << row[2]);
      }
    }
    CHECK(failures == 0);
    CHECK(usDstBounds(1966).ok() == false);
    CHECK(usDstBounds(1966).error().code == ErrorCode::OutOfRange);
    // Historic rules the C++ port must also reproduce (checked against the published federal law).
    CHECK(usDstBounds(2006).value().startDate.month == 4);
    CHECK(usDstBounds(2006).value().startDate.day == 2);      // 1st Sunday of April 2006
    CHECK(usDstBounds(2006).value().endDate.day == 29);       // last Sunday of October 2006
    CHECK(usDstBounds(1974).value().startDate.month == 1);
    CHECK(usDstBounds(1974).value().startDate.day == 6);
    CHECK(usDstBounds(1975).value().startDate.month == 2);
    CHECK(usDstBounds(1975).value().startDate.day == 23);
    CHECK(usDstBounds(1980).value().startDate.month == 4);
    CHECK(usDstBounds(1980).value().startDate.day == 27);     // last Sunday of April 1980
  }

  TEST_CASE("nyOffset matches zoneinfo for every day 2007-01-01 .. 2099-12-31") {
    int failures = 0;
    for (int32_t i = 0; i < nycsim_test_dst::kDayCount; ++i) {
      const double t = static_cast<double>(nycsim_test_dst::kFirstDayUnix) +
                       static_cast<double>(i) * static_cast<double>(kSecondsPerDay) + 12.0 * 3600.0;
      const Result<Offset> o = nyOffset(t);
      if (!o) {
        ++failures;
        continue;
      }
      const bool expect = tableIsDst(i);
      if (o.value().isDst != expect ||
          o.value().seconds != (expect ? kEdtOffsetS : kEstOffsetS) ||
          std::string(o.value().abbreviation) != (expect ? "EDT" : "EST")) {
        ++failures;
        if (failures < 5) MESSAGE("day index " << i << " unix " << t << " expected dst=" << expect);
      }
    }
    CHECK(nycsim_test_dst::kDayCount == 33968);
    CHECK(failures == 0);
  }

  TEST_CASE("nyOffset matches zoneinfo at every hour of every transition day 2007-2099") {
    int failures = 0;
    int checked = 0;
    for (const auto& td : nycsim_test_dst::kTransitionHours) {
      const Result<DstBounds> b = usDstBounds(td.year);
      REQUIRE(b.ok());
      const int64_t inst = td.which == 0 ? b.value().startUnix : b.value().endUnix;
      const int64_t dayStart = inst - (inst % kSecondsPerDay);
      for (int h = 0; h < 24; ++h) {
        const double t = static_cast<double>(dayStart + h * 3600);
        const Result<Offset> o = nyOffset(t);
        REQUIRE(o.ok());
        const bool expect = td.hours[h] == 'D';
        ++checked;
        if (o.value().isDst != expect) {
          ++failures;
          if (failures < 5) MESSAGE("year " << td.year << " which " << td.which << " hour " << h);
        }
      }
    }
    CHECK(checked == 93 * 2 * 24);
    CHECK(failures == 0);
  }

  TEST_CASE("DST boundary instants are half-open [start, end)") {
    const DstBounds b = usDstBounds(2026).value();
    CHECK_FALSE(nyOffset(static_cast<double>(b.startUnix) - 1.0).value().isDst);
    CHECK(nyOffset(static_cast<double>(b.startUnix)).value().isDst);
    CHECK(nyOffset(static_cast<double>(b.endUnix) - 1.0).value().isDst);
    CHECK_FALSE(nyOffset(static_cast<double>(b.endUnix)).value().isDst);
    // The autumn repeated hour is flagged.
    CHECK(inAmbiguousLocalHour(static_cast<double>(b.endUnix)));
    CHECK(inAmbiguousLocalHour(static_cast<double>(b.endUnix) + 3599.0));
    CHECK_FALSE(inAmbiguousLocalHour(static_cast<double>(b.endUnix) + 3600.0));
    CHECK_FALSE(inAmbiguousLocalHour(static_cast<double>(b.startUnix)));
  }

  TEST_CASE("SimTime assembles the per-frame clock state") {
    // 2026-07-04T16:20:00Z is 12:20:00 EDT.
    const double t = static_cast<double>(unixFromCivilUtc(2026, 7, 4, 16, 20, 0));
    const Result<SimTime> r = simTime(t);
    REQUIRE(r.ok());
    const SimTime& s = r.value();
    CHECK(s.isDst);
    CHECK(s.utcOffsetS == kEdtOffsetS);
    CHECK(std::string(s.tzAbbreviation) == "EDT");
    CHECK(s.local.year == 2026);
    CHECK(s.local.month == 7);
    CHECK(s.local.day == 4);
    CHECK(s.local.hour == 12);
    CHECK(s.local.minute == 20);
    CHECK(s.secondsSinceLocalMidnight == doctest::Approx(12 * 3600 + 20 * 60));
    CHECK(s.localHours() == doctest::Approx(12.0 + 20.0 / 60.0));
    CHECK(s.dayOfYear == 185);
    CHECK(s.jde > s.jd);
    CHECK(s.jde - s.jd == doctest::Approx(s.deltaTS / 86400.0));
    CHECK(s.dstStartUnix == usDstBounds(2026).value().startUnix);
    CHECK(s.dstEndUnix == usDstBounds(2026).value().endUnix);
    // A January instant is EST and the local date can be the previous UTC day.
    const Result<SimTime> w = simTime(static_cast<double>(unixFromCivilUtc(2026, 1, 15, 2, 30, 0)));
    REQUIRE(w.ok());
    CHECK_FALSE(w.value().isDst);
    CHECK(w.value().local.day == 14);
    CHECK(w.value().local.hour == 21);
    CHECK(std::string(w.value().tzAbbreviation) == "EST");
    CHECK_FALSE(simTime(std::nan("")).ok());
    CHECK_FALSE(nyOffset(std::nan("")).ok());
  }
}
