#include <doctest/doctest.h>

#include <cmath>
#include <string>
#include <vector>

#include "nycsim/io/Json.h"
#include "nycsim/weather/WeatherService.h"

using namespace nycsim;
using namespace nycsim::weather;

namespace {

WeatherState makeState(Source src, double observedAt, double tempC) {
  WeatherState s;
  s.source = src;
  s.observedAtUnix = observedAt;
  s.station = src == Source::Nws ? "KNYC" : (src == Source::OpenMeteo ? "open-meteo:40.78,-73.97" : "KLGA");
  s.tempC = tempC;
  s.dewpointC = tempC - 3.0;
  s.rh = relativeHumidity(s.tempC, s.dewpointC);
  s.cloudCover = 0.4375;
  s.visibilityM = 16090.0;
  s.pressureHpa = 1013.8;
  setWind(s, 250.0);
  s.windMps = 4.0;
  return s;
}

/// A provider whose next result the test controls.
struct Scripted {
  explicit Scripted(const char* n) : name(n) {}
  std::string name;
  bool shouldFail = true;
  WeatherState next;
  int calls = 0;

  Provider make() {
    Provider p;
    p.name = name;
    p.fetch = [this](double now) -> Result<WeatherState> {
      ++calls;
      if (shouldFail) return fail(ErrorCode::IoError, "scripted failure");
      WeatherState s = next;
      s.observedAtUnix = now - 120.0;
      return s;
    };
    return p;
  }
};

}  // namespace

TEST_SUITE("weather") {
  TEST_CASE("circuit breaker: 3 failures open it, it half-opens after 5 min, success closes it") {
    CircuitBreaker b("nws");
    double t = 1000.0;
    CHECK(b.state() == CircuitBreaker::State::Closed);
    CHECK(b.status(t) == "closed");
    CHECK(b.allow(t));
    b.recordFailure(t, "boom");
    CHECK(b.state() == CircuitBreaker::State::Closed);
    CHECK(b.consecutiveFailures() == 1);
    CHECK(b.allow(t));
    b.recordFailure(t + 60.0, "boom");
    CHECK(b.state() == CircuitBreaker::State::Closed);
    b.recordFailure(t + 120.0, "boom again");
    CHECK(b.state() == CircuitBreaker::State::Open);
    CHECK(b.consecutiveFailures() == 3);
    CHECK(std::string(b.lastError()) == "boom again");
    // Closed for the next 5 minutes.
    CHECK_FALSE(b.allow(t + 121.0));
    CHECK_FALSE(b.allow(t + 419.0));
    CHECK(b.status(t + 121.0) == "open(299s)");
    // 300 s after opening it half-opens and allows one probe.
    CHECK(b.allow(t + 420.0));
    CHECK(b.state() == CircuitBreaker::State::HalfOpen);
    CHECK(b.status(t + 420.0) == "half_open");
    // A failed probe re-opens immediately.
    b.recordFailure(t + 421.0, "still down");
    CHECK(b.state() == CircuitBreaker::State::Open);
    CHECK_FALSE(b.allow(t + 500.0));
    // A successful probe closes it and clears the counter.
    CHECK(b.allow(t + 721.0));
    b.recordSuccess(t + 722.0);
    CHECK(b.state() == CircuitBreaker::State::Closed);
    CHECK(b.consecutiveFailures() == 0);
    CHECK(b.lastSuccessAt() == doctest::Approx(t + 722.0));
    CHECK(std::string(b.lastError()).empty());
  }

  TEST_CASE("service falls through NWS -> Open-Meteo -> METAR -> stale") {
    Scripted nws("nws");
    Scripted om("open_meteo");
    Scripted mt("metar");
    nws.next = makeState(Source::Nws, 0.0, 18.0);
    om.next = makeState(Source::OpenMeteo, 0.0, 17.5);
    mt.next = makeState(Source::Metar, 0.0, 17.0);
    std::vector<Provider> providers{nws.make(), om.make(), mt.make()};
    WeatherService svc(std::move(providers));
    double t = 1788692400.0;

    SUBCASE("primary succeeds: the others are never called") {
      nws.shouldFail = false;
      const WeatherState& s = svc.poll(t);
      CHECK(s.source == Source::Nws);
      CHECK(s.tempC == doctest::Approx(18.0));
      CHECK(s.staleAgeS == doctest::Approx(120.0));
      CHECK(s.fetchedAtUnix == doctest::Approx(t));
      CHECK(nws.calls == 1);
      CHECK(om.calls == 0);
      CHECK(mt.calls == 0);
      CHECK(svc.failures() == 0);
    }

    SUBCASE("primary fails: the secondary answers and the breaker counts one failure") {
      om.shouldFail = false;
      const WeatherState& s = svc.poll(t);
      CHECK(s.source == Source::OpenMeteo);
      CHECK(s.tempC == doctest::Approx(17.5));
      CHECK(nws.calls == 1);
      CHECK(om.calls == 1);
      CHECK(mt.calls == 0);
      CHECK(svc.breaker("nws")->consecutiveFailures() == 1);
      CHECK(svc.breaker("open_meteo")->state() == CircuitBreaker::State::Closed);
    }

    SUBCASE("two fail: the tertiary answers") {
      mt.shouldFail = false;
      const WeatherState& s = svc.poll(t);
      CHECK(s.source == Source::Metar);
      CHECK(nws.calls == 1);
      CHECK(om.calls == 1);
      CHECK(mt.calls == 1);
    }

    SUBCASE("all fail with nothing known: an empty stale record, never invented weather") {
      const WeatherState& s = svc.poll(t);
      CHECK(s.source == Source::Stale);
      CHECK(std::isnan(s.tempC));
      CHECK(std::isnan(s.observedAtUnix));
      CHECK(std::isnan(s.staleAgeS));
      CHECK(s.precipType == PrecipType::None);
      CHECK(s.snowDepthSource == SnowDepthSource::None);
      CHECK(svc.failures() == 1);
      CHECK_FALSE(svc.hasLastGood());
    }

    SUBCASE("all fail after a good poll: the last good state ages") {
      nws.shouldFail = false;
      svc.poll(t);
      CHECK(svc.hasLastGood());
      nws.shouldFail = true;
      const WeatherState& s = svc.poll(t + 900.0);
      CHECK(s.source == Source::Stale);
      CHECK(s.tempC == doctest::Approx(18.0));  // the last good values are kept
      CHECK(s.station == "KNYC");
      CHECK(s.staleAgeS == doctest::Approx(120.0 + 900.0));
      CHECK(s.fetchedAtUnix == doctest::Approx(t + 900.0));
      CHECK_FALSE(s.interpolated);
      CHECK(svc.failures() == 1);
      // The stale record still validates against the contract.
      std::string why;
      CHECK_MESSAGE(s.valid(&why), why);
    }
  }

  TEST_CASE("an open breaker is skipped, and recovery restores the primary") {
    Scripted nws("nws");
    Scripted om("open_meteo");
    nws.next = makeState(Source::Nws, 0.0, 18.0);
    om.next = makeState(Source::OpenMeteo, 0.0, 17.5);
    om.shouldFail = false;
    std::vector<Provider> providers{nws.make(), om.make()};
    WeatherService svc(std::move(providers));
    double t = 1788692400.0;
    for (int i = 0; i < 3; ++i) {
      CHECK(svc.poll(t + i * 60.0).source == Source::OpenMeteo);
    }
    CHECK(nws.calls == 3);
    CHECK(svc.breaker("nws")->state() == CircuitBreaker::State::Open);
    // While open, the primary is not called at all.
    svc.poll(t + 180.0);
    CHECK(nws.calls == 3);
    // After the open window it is probed again; the probe fails and it re-opens.
    svc.poll(t + 480.0);
    CHECK(nws.calls == 4);
    CHECK(svc.breaker("nws")->state() == CircuitBreaker::State::Open);
    // Once the primary recovers, the next probe closes the breaker and it wins again.
    nws.shouldFail = false;
    const WeatherState& s = svc.poll(t + 800.0);
    CHECK(s.source == Source::Nws);
    CHECK(svc.breaker("nws")->state() == CircuitBreaker::State::Closed);
    // Status strings for the overlay.
    const std::vector<ProviderStatus> st = svc.providerStatus(t + 800.0);
    REQUIRE(st.size() == 2);
    CHECK(st[0].name == "nws");
    CHECK(st[0].status == "closed");
    CHECK(st[1].name == "open_meteo");
  }

  TEST_CASE("a provider that throws no error but has no fetch function counts as a failure") {
    Provider broken;
    broken.name = "broken";
    std::vector<Provider> providers{broken};
    WeatherService svc(std::move(providers));
    const WeatherState& s = svc.poll(1788692400.0);
    CHECK(s.source == Source::Stale);
    CHECK(svc.breaker("broken")->consecutiveFailures() == 1);
    CHECK(svc.breaker("nope") == nullptr);
  }

  TEST_CASE("snow model: accumulation, melt, rain-on-snow, settling, observed reset") {
    SnowModel m;
    CHECK(m.depthCm() == 0.0);
    CHECK(m.source() == SnowDepthSource::None);
    // Snow-to-liquid ratio bands.
    CHECK(SnowModel::snowLiquidRatio(2.0, PrecipType::Snow) == 8.0);
    CHECK(SnowModel::snowLiquidRatio(-2.0, PrecipType::Snow) == 10.0);
    CHECK(SnowModel::snowLiquidRatio(-7.0, PrecipType::Snow) == 13.0);
    CHECK(SnowModel::snowLiquidRatio(-15.0, PrecipType::Snow) == 18.0);
    CHECK(SnowModel::snowLiquidRatio(-15.0, PrecipType::Sleet) == 3.0);
    CHECK(SnowModel::snowLiquidRatio(WeatherState::kNaN(), PrecipType::Snow) == 8.0);

    double t = 1788692400.0;
    WeatherState s;
    s.tempC = -4.0;
    s.precipType = PrecipType::Snow;
    s.precipRateMmph = 2.0;  // liquid equivalent
    s.precipRateBasis = PrecipRateBasis::Class;
    // First update has no elapsed time: nothing accumulates but the clock starts.
    m.update(s, t);
    CHECK(m.depthCm() == doctest::Approx(0.0));
    CHECK(s.snowDepthSource == SnowDepthSource::None);
    // One hour of 2 mm/h liquid at -4 C -> SLR 10 -> 2.0 cm, minus 2 %/day settling.
    m.update(s, t + 3600.0);
    CHECK(s.snowfallRateCmph == doctest::Approx(2.0));
    CHECK(m.depthCm() == doctest::Approx(2.0 * (1.0 - 0.02 / 24.0)).epsilon(1e-9));
    CHECK(s.snowDepthSource == SnowDepthSource::Model);
    CHECK(s.snowDepthCm == doctest::Approx(m.depthCm()).epsilon(1e-2));
    // The step is capped at 6 h even if the service was asleep for a day.
    const double before = m.depthCm();
    m.update(s, t + 3600.0 + 86400.0);
    CHECK(m.depthCm() < before + 6.0 * 2.0 + 1e-6);
    CHECK(m.depthCm() > before);
    // Warm rain melts it: 1 h at 11 C plus 4 mm/h of rain.
    WeatherState warm;
    warm.tempC = 11.0;
    warm.precipType = PrecipType::Rain;
    warm.precipRateMmph = 4.0;
    warm.precipRateBasis = PrecipRateBasis::Measured;
    const double beforeMelt = m.depthCm();
    m.update(warm, t + 3600.0 + 86400.0 + 3600.0);
    const double expected =
        (beforeMelt - SnowModel::kMeltCmPerHPerC * 10.0 - SnowModel::kRainMeltCmPerMm * 4.0) *
        (1.0 - SnowModel::kSettlePerDay / 24.0);
    CHECK(m.depthCm() == doctest::Approx(expected).epsilon(1e-9));
    // An observed depth resets the model.
    WeatherState observed;
    observed.snowDepthCm = 12.7;
    observed.snowDepthSource = SnowDepthSource::Observed;
    m.update(observed, t + 200000.0);
    CHECK(m.depthCm() == doctest::Approx(12.7));
    CHECK(m.source() == SnowDepthSource::Observed);
    // Depth never goes negative.
    WeatherState hot;
    hot.tempC = 30.0;
    for (int i = 0; i < 50; ++i) m.update(hot, t + 200000.0 + (i + 1) * 3600.0);
    CHECK(m.depthCm() == 0.0);
    CHECK(m.source() == SnowDepthSource::None);
    // Restore round trip.
    SnowModel m2;
    m2.restore(5.5, t, SnowDepthSource::Model);
    CHECK(m2.depthCm() == doctest::Approx(5.5));
    CHECK(m2.source() == SnowDepthSource::Model);
  }

  TEST_CASE("weather.json serialisation round trip and contract shape") {
    WeatherState s = makeState(Source::Nws, 1788691860.0, 18.0);
    s.fetchedAtUnix = 1788692160.0;
    s.staleAgeS = 300.0;
    s.precipType = PrecipType::Snow;
    s.precipRateMmph = 1.5;
    s.precipRateBasis = PrecipRateBasis::Class;
    s.snowfallRateCmph = 1.5;
    s.snowDepthCm = 4.32;
    s.snowDepthSource = SnowDepthSource::Model;
    s.obscuration = kObscBR | kObscFG;
    s.thunder = true;
    s.rawText = "KNYC 061051Z 00000KT 10SM CLR 18/16 A2996";
    std::vector<ProviderStatus> status{{"nws", "closed"}, {"open_meteo", "open(120s)"}};
    const std::string text = toWeatherJson(s, status);

    // Every DATA_CONTRACTS §12 key is present with the right kind of value.
    const Result<json::Value> doc = json::parse(text);
    REQUIRE(doc.ok());
    const json::Value& d = doc.value();
    const char* contractKeys[] = {"schema_version", "observed_at",   "station",     "source",
                                  "temp_c",         "dewpoint_c",    "rh",          "wind_mps",
                                  "wind_gust_mps",  "wind_dir_deg",  "precip_type", "precip_rate_mmph",
                                  "cloud_cover",    "visibility_m",  "pressure_hpa", "snow_depth_cm",
                                  "thunder",        "fetched_at",    "stale_age_s"};
    for (const char* k : contractKeys) {
      INFO("key ", k);
      CHECK(d.find(k) != nullptr);
    }
    const char* extensionKeys[] = {"wind_from_heading", "wind_to_heading", "snow_depth_source",
                                   "snowfall_rate_cmph", "precip_rate_basis", "obscuration",
                                   "interpolated", "raw_text", "provider_status"};
    for (const char* k : extensionKeys) {
      INFO("extension key ", k);
      CHECK(d.find(k) != nullptr);
    }
    CHECK(d.find("schema_version")->asInt() == 1);
    CHECK(d.find("source")->asString() == "nws");
    CHECK(d.find("precip_type")->asString() == "snow");
    CHECK(d.find("observed_at")->asString() == "2026-09-06T10:51:00Z");
    CHECK(d.find("fetched_at")->asString() == "2026-09-06T10:56:00Z");
    CHECK(d.find("thunder")->asBool());
    REQUIRE(d.find("obscuration")->isArray());
    CHECK(d.find("obscuration")->size() == 2);
    CHECK(d.find("obscuration")->at(0)->asString() == "BR");
    CHECK(d.find("obscuration")->at(1)->asString() == "FG");
    CHECK(d.find("provider_status")->find("nws")->asString() == "closed");
    CHECK(d.find("provider_status")->find("open_meteo")->asString() == "open(120s)");
    // Numbers are rounded to 3 decimals, exactly as weather.py's to_json_dict.
    CHECK(d.find("rh")->asNumber() == doctest::Approx(std::round(s.rh * 1000.0) / 1000.0));

    // Round trip through fromWeatherJson.
    const Result<WeatherState> back = fromWeatherJson(text.c_str());
    REQUIRE(back.ok());
    CHECK(back.value().source == Source::Nws);
    CHECK(back.value().station == "KNYC");
    CHECK(back.value().tempC == doctest::Approx(18.0));
    CHECK(back.value().precipType == PrecipType::Snow);
    CHECK(back.value().precipRateBasis == PrecipRateBasis::Class);
    CHECK(back.value().snowDepthSource == SnowDepthSource::Model);
    CHECK(back.value().obscuration == (kObscBR | kObscFG));
    CHECK(back.value().thunder);
    CHECK(back.value().observedAtUnix == doctest::Approx(1788691860.0));
    CHECK(back.value().staleAgeS == doctest::Approx(300.0));
    CHECK(back.value().rawText == s.rawText);

    // Missing values serialise as null and come back as NaN.
    WeatherState sparse;
    sparse.source = Source::Stale;
    const std::string sparseText = toWeatherJson(sparse, {});
    const Result<json::Value> sparseDoc = json::parse(sparseText);
    REQUIRE(sparseDoc.ok());
    CHECK(sparseDoc.value().find("temp_c")->isNull());
    CHECK(sparseDoc.value().find("observed_at")->isNull());
    const Result<WeatherState> sparseBack = fromWeatherJson(sparseText.c_str());
    REQUIRE(sparseBack.ok());
    CHECK(std::isnan(sparseBack.value().tempC));
    CHECK(sparseBack.value().source == Source::Stale);

    // Malformed documents are rejected.
    CHECK_FALSE(fromWeatherJson("not json").ok());
    CHECK_FALSE(fromWeatherJson("[]").ok());
    CHECK_FALSE(fromWeatherJson("{\"schema_version\":2,\"source\":\"nws\"}").ok());
    CHECK_FALSE(fromWeatherJson("{\"schema_version\":1,\"source\":\"guess\"}").ok());
    CHECK_FALSE(fromWeatherJson(nullptr).ok());
  }

  TEST_CASE("the service restores a persisted last-good state and keeps ageing it") {
    Scripted dead("nws");
    std::vector<Provider> providers{dead.make()};
    WeatherService svc(std::move(providers));
    WeatherState persisted = makeState(Source::Nws, 1788691860.0, 12.0);
    svc.restoreLastGood(persisted);
    CHECK(svc.hasLastGood());
    const WeatherState& s = svc.poll(1788691860.0 + 1800.0);
    CHECK(s.source == Source::Stale);
    CHECK(s.tempC == doctest::Approx(12.0));
    CHECK(s.staleAgeS == doctest::Approx(1800.0));
  }

  TEST_CASE("contract validation rejects impossible states") {
    WeatherState s = makeState(Source::Nws, 1788691860.0, 18.0);
    std::string why;
    CHECK(s.valid(&why));
    CHECK(why.empty());
    s.cloudCover = 1.5;
    CHECK_FALSE(s.valid(&why));
    CHECK(why == "cloud_cover range");
    s.cloudCover = 0.5;
    s.windDirDeg = 360.0;
    CHECK_FALSE(s.valid(&why));
    s.windDirDeg = 200.0;
    s.dewpointC = 25.0;
    CHECK_FALSE(s.valid(&why));
    s.dewpointC = 15.0;
    s.precipType = PrecipType::None;
    s.precipRateMmph = 3.0;
    CHECK_FALSE(s.valid(&why));
    s.precipRateMmph = 0.0;
    s.precipType = PrecipType::Rain;
    s.precipRateBasis = PrecipRateBasis::None;
    CHECK_FALSE(s.valid(&why));
    s.precipRateBasis = PrecipRateBasis::Class;
    s.precipRateMmph = 4.0;
    CHECK(s.valid(&why));
    s.pressureHpa = 1500.0;
    CHECK_FALSE(s.valid(&why));
  }
}
