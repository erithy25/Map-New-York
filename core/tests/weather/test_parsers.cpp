#include <doctest/doctest.h>

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "nycsim/io/Json.h"
#include "nycsim/weather/MetarParser.h"
#include "nycsim/weather/NwsParser.h"
#include "nycsim/weather/OpenMeteoParser.h"
#include "nycsim/weather/WeatherState.h"
#include "weather_cases.h"

using namespace nycsim;
using namespace nycsim::weather;

namespace {

std::string readFixture(const char* name) {
  std::string path = std::string(NYCSIM_TEST_DATA_DIR) + "/weather/" + name;
  std::FILE* f = std::fopen(path.c_str(), "rb");
  REQUIRE_MESSAGE(f != nullptr, "missing fixture " << path);
  std::string out;
  char buf[8192];
  size_t n = 0;
  while ((n = std::fread(buf, 1, sizeof buf, f)) > 0) out.append(buf, n);
  std::fclose(f);
  return out;
}

/// NaN-aware comparison used everywhere below: both NaN passes, otherwise |a-b| <= tol.
bool same(double a, double b, double tol = 1e-9) {
  if (std::isnan(a) && std::isnan(b)) return true;
  if (std::isnan(a) || std::isnan(b)) return false;
  return std::fabs(a - b) <= tol;
}

void checkAgainst(const WeatherState& s, const nycsim_test_weather::ExpectedState& e,
                  const char* label) {
  INFO("case ", label);
  CHECK(s.station == std::string(e.station));
  CHECK(static_cast<int32_t>(s.source) == e.source);
  CHECK(same(s.observedAtUnix, e.observed_at, 1e-6));
  CHECK(same(s.tempC, e.temp_c));
  CHECK(same(s.dewpointC, e.dewpoint_c, 1e-9));
  CHECK(same(s.rh, e.rh, 1e-9));
  CHECK(same(s.windMps, e.wind_mps, 1e-9));
  CHECK(same(s.windGustMps, e.wind_gust_mps, 1e-9));
  CHECK(same(s.windDirDeg, e.wind_dir_deg, 1e-9));
  CHECK(same(s.windFromHeading, e.wind_from_heading, 1e-9));
  CHECK(same(s.windToHeading, e.wind_to_heading, 1e-9));
  CHECK(static_cast<int32_t>(s.precipType) == e.precip_type);
  CHECK(same(s.precipRateMmph, e.precip_rate_mmph, 1e-9));
  CHECK(static_cast<int32_t>(s.precipRateBasis) == e.precip_rate_basis);
  CHECK(same(s.cloudCover, e.cloud_cover, 1e-12));
  CHECK(same(s.visibilityM, e.visibility_m, 1e-6));
  CHECK(same(s.pressureHpa, e.pressure_hpa, 1e-9));
  CHECK(same(s.snowDepthCm, e.snow_depth_cm, 1e-9));
  CHECK(static_cast<int32_t>(s.snowDepthSource) == e.snow_depth_source);
  CHECK(same(s.snowfallRateCmph, e.snowfall_rate_cmph, 1e-9));
  CHECK(s.thunder == e.thunder);
  CHECK(s.obscuration == e.obscuration);
  std::string why;
  CHECK_MESSAGE(s.valid(&why), why);
}

}  // namespace

TEST_SUITE("weather") {
  TEST_CASE("METAR grammar: 20 reports covering the whole body and remark grammar") {
    for (int i = 0; i < nycsim_test_weather::kMetarCaseCount; ++i) {
      const auto& c = nycsim_test_weather::kMetarCases[i];
      INFO("METAR case ", c.label);
      const Result<metar::MetarReport> r = metar::parseMetar(c.text, c.reference_unix);
      REQUIRE(r.ok());
      const metar::MetarReport& m = r.value();
      CHECK(m.station == std::string(c.station));
      CHECK(same(m.observationTimeUnix, c.observation_unix, 1e-6));
      CHECK(m.nil == c.nil);
      CHECK(m.automatic == c.automatic);
      CHECK(same(m.windDirDeg, c.wind_dir));
      CHECK(same(m.windSpeedMps, c.wind_speed, 1e-9));
      CHECK(same(m.windGustMps, c.wind_gust, 1e-9));
      CHECK(m.windVariable == c.wind_variable);
      CHECK(m.windCalm == c.wind_calm);
      CHECK(same(m.visibilityM, c.visibility_m, 1e-6));
      CHECK(m.visibilityLessThan == c.vis_less);
      CHECK(m.visibilityGreaterThan == c.vis_greater);
      CHECK(m.cavok == c.cavok);
      CHECK(static_cast<int32_t>(m.weather.size()) == c.n_weather_groups);
      CHECK(static_cast<int32_t>(m.clouds.size()) == c.n_clouds);
      CHECK(static_cast<int32_t>(m.rvr.size()) == c.n_rvr);
      CHECK(static_cast<int32_t>(m.unparsed.size()) == c.n_unparsed);
      CHECK(same(m.tempC, c.temp_c));
      CHECK(same(m.dewpointC, c.dewpoint_c));
      CHECK(same(m.altimeterHpa, c.altimeter_hpa, 1e-9));
      CHECK(same(m.seaLevelPressureHpa, c.slp_hpa, 1e-9));
      CHECK(same(m.precipLastHourMm, c.precip_1h_mm, 1e-9));
      CHECK(same(m.snowDepthCm, c.snow_depth_cm, 1e-9));
      CHECK(same(m.snowfall6hCm, c.snowfall_6h_cm, 1e-9));
      CHECK(same(m.snowWaterEquivalentMm, c.snow_we_mm, 1e-9));
      CHECK(same(m.peakWindDirDeg, c.peak_wind_dir, 1e-9));
      CHECK(same(m.peakWindMps, c.peak_wind_mps, 1e-9));
      CHECK(same(m.ceilingM(), c.ceiling_m, 1e-6));
      CHECK(m.trend == std::string(c.trend));
      // Semantics
      PrecipType type = PrecipType::None;
      metar::Intensity intensity = metar::Intensity::Moderate;
      metar::classifyPrecipitation(m.weather, m.tempC, type, intensity);
      CHECK(static_cast<int32_t>(type) == c.precip_type);
      double rate = 0.0;
      PrecipRateBasis basis = PrecipRateBasis::None;
      metar::precipitationRateMmph(m.weather, m.precipLastHourMm, m.tempC, rate, basis);
      CHECK(same(rate, c.precip_rate, 1e-9));
      CHECK(static_cast<int32_t>(basis) == c.precip_basis);
      CHECK(metar::thunderPresent(m.weather) == c.thunder);
      CHECK(metar::obscurationBits(m.weather) == c.obscuration);
      CHECK(same(metar::cloudCoverFraction(m.clouds, m.hasSkyClearCode), c.cloud_cover, 1e-12));
    }
    CHECK(nycsim_test_weather::kMetarCaseCount == 20);
  }

  TEST_CASE("METAR: specific grammar details spelled out") {
    // Mixed-fraction statute-mile visibility as two tokens.
    const auto a = metar::parseMetar("KEWR 020551Z 08006KT 1 3/4SM BR OVC004 07/07 A3021", 1.7e9);
    REQUIRE(a.ok());
    CHECK(a.value().visibilityM == doctest::Approx(2816.4).epsilon(1e-6));
    CHECK(a.value().weather.size() == 1);
    CHECK(a.value().weather[0].phenomena == metar::kPhBR);
    CHECK_FALSE(a.value().weather[0].precipitating());
    // Altimeter conversion: A2996 -> 29.96 inHg x 33.86389 = 1014.55 hPa, rounded to 1 decimal.
    const auto b = metar::parseMetar("KNYC 061051Z 00000KT 10SM CLR 18/16 A2996", 1.7e9);
    REQUIRE(b.ok());
    CHECK(b.value().altimeterHpa == doctest::Approx(1014.6).epsilon(1e-9));
    CHECK(b.value().windCalm);
    CHECK(std::isnan(b.value().windDirDeg));
    CHECK(b.value().windSpeedMps == 0.0);
    CHECK(b.value().visibilityGreaterThan);
    // Q-code pressure is hPa directly.
    const auto c = metar::parseMetar("EDDF 011250Z 07004KT 9999 FEW035 21/09 Q1018 NOSIG", 1.7e9);
    REQUIRE(c.ok());
    CHECK(c.value().altimeterHpa == 1018.0);
    CHECK(c.value().visibilityM == doctest::Approx(metar::kVisUnlimitedM));
    CHECK(c.value().trend == "NOSIG");
    CHECK(c.value().windSpeedMps == doctest::Approx(2.058).epsilon(1e-9));  // 4 kt, rounded to 3 dp
    // Vertical visibility and a snow-depth remark.
    const auto d = metar::parseMetar(
        "KNYC 070851Z 03014G22KT 1/2SM SN FZFG VV006 M03/M05 A2978 RMK AO2 4/008 P0006", 1.7e9);
    REQUIRE(d.ok());
    CHECK(d.value().verticalVisibilityM == doctest::Approx(182.9).epsilon(1e-6));
    CHECK(d.value().snowDepthCm == doctest::Approx(20.32).epsilon(1e-9));
    CHECK(d.value().precipLastHourMm == doctest::Approx(1.524).epsilon(1e-9));  // P0006 = 0.06 in
    CHECK(d.value().tempC == -3.0);
    CHECK(d.value().dewpointC == -5.0);
    CHECK(d.value().weather.size() == 2);
    CHECK(d.value().weather[1].descriptor == metar::Descriptor::FZ);
    CHECK((d.value().weather[1].phenomena & metar::kPhFG) != 0);
    // T-group overrides the coarse temperature.
    const auto e = metar::parseMetar("KNYC 061051Z 00000KT 10SM CLR 18/16 A2996 RMK T01780156", 1.7e9);
    REQUIRE(e.ok());
    CHECK(e.value().tempC == doctest::Approx(17.8));
    CHECK(e.value().dewpointC == doctest::Approx(15.6));
    // A station identifier is mandatory.
    CHECK_FALSE(metar::parseMetar("061051Z 00000KT", 1.7e9).ok());
    CHECK_FALSE(metar::parseMetar("", 1.7e9).ok());
    CHECK_FALSE(metar::parseMetar(nullptr, 1.7e9).ok());
    // Unknown tokens are collected, never silently dropped.
    const auto f = metar::parseMetar("KJFK 011200Z 10SM XYZZY 20/10 A3000", 1.7e9);
    REQUIRE(f.ok());
    CHECK(f.value().unparsed.size() == 1);
    CHECK(f.value().unparsed[0] == "XYZZY");
  }

  TEST_CASE("METAR precipitation classification and class rates") {
    struct Case {
      const char* body;
      PrecipType type;
      double rate;
      PrecipRateBasis basis;
    };
    // The rate is the FMH-1 class representative unless a P group measured one.
    const Case cases[] = {
        {"-RA", PrecipType::Rain, 1.0, PrecipRateBasis::Class},
        {"RA", PrecipType::Rain, 4.0, PrecipRateBasis::Class},
        {"+RA", PrecipType::Rain, 10.0, PrecipRateBasis::Class},
        {"-DZ", PrecipType::Drizzle, 0.2, PrecipRateBasis::Class},
        {"-SN", PrecipType::Snow, 0.5, PrecipRateBasis::Class},
        {"+SN", PrecipType::Snow, 3.0, PrecipRateBasis::Class},
        {"PL", PrecipType::Sleet, 3.0, PrecipRateBasis::Class},
        {"-FZRA", PrecipType::FreezingRain, 0.5, PrecipRateBasis::Class},
        {"RASN", PrecipType::Sleet, 3.0, PrecipRateBasis::Class},
        {"+TSRA", PrecipType::Rain, 15.0, PrecipRateBasis::Class},  // x1.5 thunderstorm factor
        {"VCSH", PrecipType::None, 0.0, PrecipRateBasis::None},
        {"BR", PrecipType::None, 0.0, PrecipRateBasis::None},
    };
    for (const Case& c : cases) {
      INFO("group ", c.body);
      const std::string text = std::string("KNYC 011200Z 09010KT 5SM ") + c.body + " OVC010 05/04 A3000";
      const auto r = metar::parseMetar(text.c_str(), 1.7e9);
      REQUIRE(r.ok());
      PrecipType type = PrecipType::None;
      metar::Intensity intensity = metar::Intensity::Moderate;
      metar::classifyPrecipitation(r.value().weather, r.value().tempC, type, intensity);
      CHECK(type == c.type);
      double rate = 0.0;
      PrecipRateBasis basis = PrecipRateBasis::None;
      metar::precipitationRateMmph(r.value().weather, r.value().precipLastHourMm, r.value().tempC, rate,
                                   basis);
      CHECK(rate == doctest::Approx(c.rate).epsilon(1e-9));
      CHECK(basis == c.basis);
    }
    // UP (unknown precipitation) resolves by temperature.
    const auto warm = metar::parseMetar("KNYC 011200Z 09010KT 5SM UP OVC010 05/04 A3000", 1.7e9);
    const auto cold = metar::parseMetar("KNYC 011200Z 09010KT 5SM UP OVC010 M05/M07 A3000", 1.7e9);
    REQUIRE(warm.ok());
    REQUIRE(cold.ok());
    PrecipType t1 = PrecipType::None, t2 = PrecipType::None;
    metar::Intensity i1, i2;
    metar::classifyPrecipitation(warm.value().weather, warm.value().tempC, t1, i1);
    metar::classifyPrecipitation(cold.value().weather, cold.value().tempC, t2, i2);
    CHECK(t1 == PrecipType::Rain);
    CHECK(t2 == PrecipType::Snow);
    // A measured hourly amount beats the class representative; P0000 is a trace.
    const auto measured =
        metar::parseMetar("KNYC 011200Z 09010KT 5SM -RA OVC010 05/04 A3000 RMK P0025", 1.7e9);
    REQUIRE(measured.ok());
    double rate = 0.0;
    PrecipRateBasis basis = PrecipRateBasis::None;
    metar::precipitationRateMmph(measured.value().weather, measured.value().precipLastHourMm,
                                 measured.value().tempC, rate, basis);
    CHECK(rate == doctest::Approx(6.35).epsilon(1e-9));
    CHECK(basis == PrecipRateBasis::Measured);
    const auto trace =
        metar::parseMetar("KNYC 011200Z 09010KT 5SM -RA OVC010 05/04 A3000 RMK P0000", 1.7e9);
    REQUIRE(trace.ok());
    metar::precipitationRateMmph(trace.value().weather, trace.value().precipLastHourMm,
                                 trace.value().tempC, rate, basis);
    CHECK(rate == doctest::Approx(metar::kTraceRateMmph));
    CHECK(basis == PrecipRateBasis::Trace);
  }

  TEST_CASE("METAR observation-time resolution and multi-report text") {
    // 2026-09-06T11:00Z reference, report timed 061051Z -> the same day.
    const double ref = 1788692400.0;  // 2026-09-06T11:00:00Z
    const Result<double> t = metar::resolveObservationTime(6, 10, 51, ref);
    REQUIRE(t.ok());
    CHECK(t.value() == doctest::Approx(1788691860.0));
    // A report timed on day 31 seen on the 1st resolves into the previous month.
    const double ref2 = 1788692400.0 + 26.0 * 86400.0;  // 2026-10-02T11:00Z
    const Result<double> t2 = metar::resolveObservationTime(30, 23, 51, ref2);
    REQUIRE(t2.ok());
    CHECK(t2.value() < ref2);
    CHECK(ref2 - t2.value() < 3.0 * 86400.0);
    // Without a reference the time cannot be resolved and that is reported, not guessed.
    CHECK_FALSE(metar::resolveObservationTime(6, 10, 51, WeatherState::kNaN()).ok());
    // tgftp multi-report splitting.
    const char* two =
        "2026/09/06 10:51\nKNYC 061051Z 00000KT 10SM CLR 18/16 A2996\n"
        "2026/09/06 11:51\nKNYC 061151Z 04003KT 10SM CLR 19/16 A2995\n";
    const std::vector<std::string> parts = metar::splitReports(two);
    REQUIRE(parts.size() == 2);
    const auto p0 = metar::parseMetar(parts[0].c_str(), WeatherState::kNaN());
    const auto p1 = metar::parseMetar(parts[1].c_str(), WeatherState::kNaN());
    REQUIRE(p0.ok());
    REQUIRE(p1.ok());
    // The header line supplies the reference time, so both resolve without an external clock.
    CHECK(p0.value().observationTimeUnix == doctest::Approx(1788691860.0));
    CHECK(p1.value().observationTimeUnix == doctest::Approx(1788695460.0));
    CHECK(p1.value().tempC == 19.0);
  }

  TEST_CASE("live METAR fixtures parse identically to the Python reference") {
    struct Fx {
      const char* file;
      const nycsim_test_weather::ExpectedState* expected;
    };
    const Fx fixtures[] = {
        {"metar_KNYC.txt", &nycsim_test_weather::kMetarKNYC},
        {"metar_KLGA.txt", &nycsim_test_weather::kMetarKLGA},
        {"metar_KJFK.txt", &nycsim_test_weather::kMetarKJFK},
        {"metar_KEWR.txt", &nycsim_test_weather::kMetarKEWR},
    };
    for (const Fx& f : fixtures) {
      const std::string text = readFixture(f.file);
      const Result<metar::MetarReport> r = metar::parseMetar(text.c_str(), f.expected->now_unix);
      REQUIRE_MESSAGE(r.ok(), f.file);
      const Result<WeatherState> s =
          metar::weatherStateFromMetar(r.value(), f.expected->now_unix, WeatherState::kNaN());
      REQUIRE(s.ok());
      checkAgainst(s.value(), *f.expected, f.file);
    }
  }

  TEST_CASE("live NWS observation fixtures parse identically to the Python reference") {
    struct Fx {
      const char* file;
      const nycsim_test_weather::ExpectedState* plain;
      const nycsim_test_weather::ExpectedState* blended;
      bool blendApplied;
    };
    const Fx fixtures[] = {
        {"nws_KNYC.json", &nycsim_test_weather::kNwsKNYC, &nycsim_test_weather::kNwsKNYCBlended,
         nycsim_test_weather::kNwsKNYCBlendApplied},
        {"nws_KLGA.json", &nycsim_test_weather::kNwsKLGA, &nycsim_test_weather::kNwsKLGABlended,
         nycsim_test_weather::kNwsKLGABlendApplied},
        {"nws_KJFK.json", &nycsim_test_weather::kNwsKJFK, &nycsim_test_weather::kNwsKJFKBlended,
         nycsim_test_weather::kNwsKJFKBlendApplied},
    };
    const std::string gridText = readFixture("nws_gridpoint.json");
    const Result<json::Value> grid = json::parse(gridText);
    REQUIRE(grid.ok());
    const Result<NwsForecastBlend> blend = NwsForecastBlend::fromJson(grid.value());
    REQUIRE(blend.ok());
    for (const Fx& f : fixtures) {
      const std::string text = readFixture(f.file);
      const Result<json::Value> doc = json::parse(text);
      REQUIRE_MESSAGE(doc.ok(), f.file);
      const Result<WeatherState> s = parseNwsObservation(doc.value(), f.plain->now_unix);
      REQUIRE_MESSAGE(s.ok(), f.file);
      checkAgainst(s.value(), *f.plain, f.file);
      CHECK_FALSE(s.value().interpolated);
      // The same observation carried along the gridpoint forecast trend.
      const Result<WeatherState> s2 = parseNwsObservation(doc.value(), f.blended->now_unix);
      REQUIRE(s2.ok());
      WeatherState blendedState = s2.value();
      const bool applied = blend.value().apply(blendedState, f.blended->now_unix);
      CHECK(applied == f.blendApplied);
      CHECK(blendedState.interpolated == f.blendApplied);
      checkAgainst(blendedState, *f.blended, f.file);
    }
    // A young observation is never blended.
    const std::string text = readFixture("nws_KNYC.json");
    const Result<json::Value> doc = json::parse(text);
    REQUIRE(doc.ok());
    Result<WeatherState> young = parseNwsObservation(doc.value(), nycsim_test_weather::kNwsKNYC.now_unix);
    REQUIRE(young.ok());
    WeatherState y = young.value();
    CHECK_FALSE(blend.value().apply(y, nycsim_test_weather::kNwsKNYC.now_unix));
    CHECK(same(y.tempC, nycsim_test_weather::kNwsKNYC.temp_c));
  }

  TEST_CASE("live Open-Meteo fixture parses identically to the Python reference") {
    const std::string text = readFixture("open_meteo.json");
    const Result<json::Value> doc = json::parse(text);
    REQUIRE(doc.ok());
    const Result<WeatherState> s = parseOpenMeteo(doc.value(), nycsim_test_weather::kOpenMeteo.now_unix);
    REQUIRE(s.ok());
    checkAgainst(s.value(), nycsim_test_weather::kOpenMeteo, "open_meteo.json");
    CHECK(s.value().rawText.compare(0, 4, "WMO ") == 0);
  }

  TEST_CASE("provider parsers reject unusable documents instead of inventing values") {
    const double now = 1.788e9;
    // NWS: no properties / no timestamp / no temperature / too old.
    const Result<json::Value> empty = json::parse("{}");
    REQUIRE(empty.ok());
    CHECK_FALSE(parseNwsObservation(empty.value(), now).ok());
    const Result<json::Value> noTs = json::parse("{\"properties\":{}}");
    REQUIRE(noTs.ok());
    CHECK(parseNwsObservation(noTs.value(), now).error().code == ErrorCode::ParseError);
    const Result<json::Value> noTemp =
        json::parse("{\"properties\":{\"timestamp\":\"2026-09-06T10:51:00+00:00\"}}");
    REQUIRE(noTemp.ok());
    CHECK(parseNwsObservation(noTemp.value(), 1788692400.0).error().code == ErrorCode::ParseError);
    const Result<json::Value> old = json::parse(
        "{\"properties\":{\"timestamp\":\"2026-09-06T00:00:00+00:00\","
        "\"temperature\":{\"value\":18.0}}}");
    REQUIRE(old.ok());
    CHECK(parseNwsObservation(old.value(), 1788692400.0).error().code == ErrorCode::StateError);
    // A QC-rejected temperature is discarded, not used.
    const Result<json::Value> badQc = json::parse(
        "{\"properties\":{\"timestamp\":\"2026-09-06T10:51:00+00:00\","
        "\"temperature\":{\"value\":18.0,\"qualityControl\":\"X\"}}}");
    REQUIRE(badQc.ok());
    CHECK_FALSE(parseNwsObservation(badQc.value(), 1788692400.0).ok());
    // Open-Meteo: no current block / stale / API error.
    CHECK_FALSE(parseOpenMeteo(empty.value(), now).ok());
    const Result<json::Value> omErr = json::parse("{\"error\":true,\"reason\":\"nope\"}");
    REQUIRE(omErr.ok());
    CHECK(parseOpenMeteo(omErr.value(), now).error().code == ErrorCode::StateError);
    const Result<json::Value> omOld = json::parse(
        "{\"latitude\":40.78,\"longitude\":-73.97,\"current\":{\"time\":\"2026-09-06T00:00\","
        "\"interval\":900,\"temperature_2m\":18.0}}");
    REQUIRE(omOld.ok());
    CHECK(parseOpenMeteo(omOld.value(), 1788692400.0).error().code == ErrorCode::StateError);
    // METAR without a temperature.
    const auto r = metar::parseMetar("KNYC 061051Z 00000KT 10SM CLR A2996", 1788692400.0);
    REQUIRE(r.ok());
    CHECK_FALSE(metar::weatherStateFromMetar(r.value(), 1788692400.0, WeatherState::kNaN()).ok());
  }

  TEST_CASE("WMO code table and the Open-Meteo rain/snow partition") {
    CHECK(wmoCodeMapping(0).type == PrecipType::None);
    CHECK(wmoCodeMapping(45).obscuration == kObscFG);
    CHECK(wmoCodeMapping(51).type == PrecipType::Drizzle);
    CHECK(wmoCodeMapping(51).intensity == metar::Intensity::Light);
    CHECK(wmoCodeMapping(65).type == PrecipType::Rain);
    CHECK(wmoCodeMapping(65).intensity == metar::Intensity::Heavy);
    CHECK(wmoCodeMapping(67).type == PrecipType::FreezingRain);
    CHECK(wmoCodeMapping(75).type == PrecipType::Snow);
    CHECK(wmoCodeMapping(95).thunder);
    CHECK(wmoCodeMapping(99).type == PrecipType::Sleet);
    CHECK_FALSE(wmoCodeMapping(1234).known);
    // A dry code with model precipitation: type comes from the rain/snow partition.
    auto build = [](const char* extra) {
      return std::string(
                 "{\"latitude\":40.7831,\"longitude\":-73.9712,\"current\":{"
                 "\"time\":\"2026-09-06T11:00\",\"interval\":900,\"temperature_2m\":1.0,"
                 "\"weather_code\":3,") +
             extra + "}}";
    };
    const double now = 1788692400.0;
    const Result<json::Value> rainDoc = json::parse(build("\"precipitation\":0.5,\"rain\":0.5").c_str());
    REQUIRE(rainDoc.ok());
    const Result<WeatherState> rain = parseOpenMeteo(rainDoc.value(), now);
    REQUIRE(rain.ok());
    CHECK(rain.value().precipType == PrecipType::Rain);
    CHECK(rain.value().precipRateMmph == doctest::Approx(2.0));  // 0.5 mm per 900 s -> 2 mm/h
    CHECK(rain.value().precipRateBasis == PrecipRateBasis::Measured);
    const Result<json::Value> snowDoc =
        json::parse(build("\"precipitation\":0.4,\"snowfall\":0.5").c_str());
    REQUIRE(snowDoc.ok());
    const Result<WeatherState> snow = parseOpenMeteo(snowDoc.value(), now);
    REQUIRE(snow.ok());
    CHECK(snow.value().precipType == PrecipType::Snow);
    CHECK(snow.value().snowfallRateCmph == doctest::Approx(2.0));
    const Result<json::Value> mixDoc =
        json::parse(build("\"precipitation\":0.4,\"rain\":0.2,\"snowfall\":0.3").c_str());
    REQUIRE(mixDoc.ok());
    CHECK(parseOpenMeteo(mixDoc.value(), now).value().precipType == PrecipType::Sleet);
  }

  TEST_CASE("numeric helpers match the Python formulas") {
    // August-Roche-Magnus round trip.
    for (double t = -20.0; t <= 40.0; t += 2.5) {
      for (double rh = 5.0; rh <= 100.0; rh += 5.0) {
        const double td = dewpointFromRh(t, rh);
        CHECK(relativeHumidity(t, td) == doctest::Approx(rh).epsilon(1e-9));
        CHECK(td <= t + 1e-9);
      }
    }
    CHECK(relativeHumidity(20.0, 20.0) == doctest::Approx(100.0));
    CHECK(relativeHumidity(30.0, -10.0) < 10.0);
    // Angle conventions (DATA_CONTRACTS preamble).
    CHECK(compassToMath(0.0) == doctest::Approx(90.0));
    CHECK(compassToMath(90.0) == doctest::Approx(0.0));
    CHECK(compassToMath(180.0) == doctest::Approx(270.0));
    CHECK(compassToMath(270.0) == doctest::Approx(180.0));
    CHECK(mathToCompass(compassToMath(37.0)) == doctest::Approx(37.0));
    WeatherState s;
    setWind(s, 250.0);
    CHECK(s.windFromHeading == doctest::Approx(250.0));
    CHECK(s.windToHeading == doctest::Approx(70.0));
    CHECK(s.windDirDeg == doctest::Approx(200.0));
    setWind(s, WeatherState::kNaN());
    CHECK(std::isnan(s.windDirDeg));
    CHECK(std::isnan(s.windFromHeading));
    // ISO-8601 parsing and formatting.
    CHECK(parseIso8601("2026-09-06T10:51:00Z").value() == doctest::Approx(1788691860.0));
    CHECK(parseIso8601("2026-09-06T10:51:00+00:00").value() == doctest::Approx(1788691860.0));
    CHECK(parseIso8601("2026-09-06T06:51:00-04:00").value() == doctest::Approx(1788691860.0));
    CHECK(parseIso8601("2026-09-06T10:51").value() == doctest::Approx(1788691860.0));
    CHECK(parseIso8601("2026-09-06T10:51:00.500Z").value() == doctest::Approx(1788691860.5));
    CHECK_FALSE(parseIso8601("2026-09-06").ok());
    CHECK_FALSE(parseIso8601("not a time").ok());
    CHECK_FALSE(parseIso8601(nullptr).ok());
    CHECK(isoUtc(1788691860.0) == "2026-09-06T10:51:00Z");
    // ISO-8601 durations (NWS gridpoint validTime).
    CHECK(parseIsoDuration("PT1H").value() == doctest::Approx(3600.0));
    CHECK(parseIsoDuration("PT6H").value() == doctest::Approx(21600.0));
    CHECK(parseIsoDuration("P1DT2H30M").value() == doctest::Approx(86400.0 + 9000.0));
    CHECK(parseIsoDuration("PT45S").value() == doctest::Approx(45.0));
    CHECK_FALSE(parseIsoDuration("1H").ok());
    CHECK_FALSE(parseIsoDuration("P").ok());
    // Obscuration bit set <-> code list.
    CHECK(obscurationBit("FG") == kObscFG);
    CHECK(obscurationBit("ZZ") == 0);
    CHECK(obscurationList(kObscBR | kObscFG) == "BR FG");
    CHECK(obscurationList(0).empty());
    CHECK(std::string(obscurationCode(kObscHZ)) == "HZ");
  }

  TEST_CASE("GridSeries interpolation") {
    const char* doc =
        "{\"values\":["
        "{\"validTime\":\"2026-09-06T10:00:00+00:00/PT1H\",\"value\":10.0},"
        "{\"validTime\":\"2026-09-06T11:00:00+00:00/PT1H\",\"value\":14.0},"
        "{\"validTime\":\"2026-09-06T12:00:00+00:00/PT1H\",\"value\":null}]}";
    const Result<json::Value> v = json::parse(doc);
    REQUIRE(v.ok());
    const GridSeries s(&v.value(), 1.0);
    CHECK(s.size() == 4);  // two entries, each held to the end of its validity
    CHECK(s.valueAt(1788688800.0) == doctest::Approx(10.0));            // 10:00
    CHECK(s.valueAt(1788688800.0 + 3599.0) == doctest::Approx(10.0));   // held to 10:59:59
    CHECK(s.valueAt(1788692400.0) == doctest::Approx(14.0));            // 11:00
    CHECK(std::isnan(s.valueAt(1788688800.0 - 1.0)));                   // before the span
    CHECK(std::isnan(s.valueAt(1788692400.0 + 4000.0)));                // after the span
    const GridSeries emptySeries(nullptr, 1.0);
    CHECK(emptySeries.size() == 0);
    CHECK(std::isnan(emptySeries.valueAt(1788692400.0)));
  }
}
