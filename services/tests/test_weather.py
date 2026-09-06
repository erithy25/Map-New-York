"""Weather providers, the ordered service, circuit breakers, staleness and the snow model."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from conftest import FakeFetch, load_json, load_text
from nycsim_live import metar as M
from nycsim_live import net
from nycsim_live import weather as W


def _now_of(iso: str) -> float:
    return W.parse_iso8601(iso)


# --------------------------------------------------------------------------- numeric helpers
def test_iso8601_variants():
    base = dt.datetime(2026, 9, 5, 18, 51, tzinfo=dt.timezone.utc).timestamp()
    for s in ("2026-09-05T18:51:00Z", "2026-09-05T18:51:00+00:00", "2026-09-05T14:51:00-04:00", "2026-09-05T18:51"):
        assert W.parse_iso8601(s) == pytest.approx(base)
    assert W.parse_iso8601("2026-09-05T18:51:00.500Z") == pytest.approx(base + 0.5)
    assert W.iso_utc(base) == "2026-09-05T18:51:00Z"


@pytest.mark.parametrize("compass,math_deg", [(0.0, 90.0), (90.0, 0.0), (180.0, 270.0), (270.0, 180.0), (45.0, 45.0)])
def test_angle_conventions(compass, math_deg):
    assert W.compass_to_math(compass) == pytest.approx(math_deg)
    assert W.math_to_compass(math_deg) == pytest.approx(compass)


def test_relative_humidity_and_dewpoint_are_inverse():
    for t in (-20.0, 0.0, 12.5, 30.0):
        for td in (t - 15.0, t - 3.0, t):
            rh = W.relative_humidity(t, td)
            assert 0.0 <= rh <= 100.0
            assert W.dewpoint_from_rh(t, rh) == pytest.approx(td, abs=1e-6)
    assert W.relative_humidity(20.0, 20.0) == pytest.approx(100.0)
    assert W.relative_humidity(20.0, 9.3) == pytest.approx(50.0, abs=0.5)


def test_set_wind_fills_all_three_representations():
    o = W.WeatherObservation()
    W.set_wind(o, 110.0)
    assert (o.wind_from_heading, o.wind_to_heading, o.wind_dir_deg) == (110.0, 290.0, pytest.approx(340.0))
    W.set_wind(o, None)
    assert o.wind_from_heading is None and o.wind_to_heading is None and o.wind_dir_deg is None
    W.set_wind(o, 370.0)
    assert o.wind_from_heading == pytest.approx(10.0)


# --------------------------------------------------------------------------- circuit breaker
def test_circuit_breaker_opens_after_three_failures_and_half_opens_after_five_minutes():
    b = W.CircuitBreaker("x")
    assert b.allow(0.0) and b.state == b.CLOSED
    b.record_failure(0.0, "e1")
    b.record_failure(1.0, "e2")
    assert b.state == b.CLOSED and b.allow(1.0)
    b.record_failure(2.0, "e3")
    assert b.state == b.OPEN and b.consecutive_failures == 3
    assert b.allow(2.0) is False
    assert b.allow(2.0 + 299.0) is False
    assert b.allow(2.0 + 300.0) is True and b.state == b.HALF_OPEN
    b.record_failure(302.0, "e4")  # a failed probe re-opens immediately
    assert b.state == b.OPEN and b.allow(302.0) is False
    assert b.allow(602.0) is True
    b.record_success(602.0)
    assert b.state == b.CLOSED and b.consecutive_failures == 0 and b.last_error is None


def test_circuit_breaker_success_resets_the_counter():
    b = W.CircuitBreaker("x")
    b.record_failure(0.0, "e")
    b.record_failure(1.0, "e")
    b.record_success(2.0)
    b.record_failure(3.0, "e")
    b.record_failure(4.0, "e")
    assert b.state == b.CLOSED


def test_circuit_breaker_status_string():
    b = W.CircuitBreaker("x")
    assert b.status(0.0) == "closed"
    for i in range(3):
        b.record_failure(float(i), "e")
    assert b.status(2.0) == "open(300s)"
    assert b.status(102.0) == "open(200s)"


# --------------------------------------------------------------------------- NWS
def test_parse_nws_observation_knyc():
    doc = load_json("nws_obs_KNYC.json")
    now = W.parse_iso8601(doc["properties"]["timestamp"]) + 600
    o = W.parse_nws_observation(doc, now)
    p = doc["properties"]
    assert o.source == "nws" and o.station == "KNYC"
    assert o.temp_c == pytest.approx(p["temperature"]["value"])
    assert o.dewpoint_c == pytest.approx(p["dewpoint"]["value"])
    assert o.rh == pytest.approx(p["relativeHumidity"]["value"], abs=1e-9)
    assert o.wind_mps == pytest.approx(p["windSpeed"]["value"] / 3.6)
    assert o.pressure_hpa == pytest.approx((p["seaLevelPressure"]["value"] or p["barometricPressure"]["value"]) / 100.0)
    assert o.visibility_m == pytest.approx(p["visibility"]["value"])
    assert o.precip_type in W.PRECIP_TYPES
    assert 0.0 <= o.cloud_cover <= 1.0
    assert o.raw_text == p["rawMessage"]


def test_parse_nws_observation_all_recorded_stations():
    for name in ("nws_obs_KNYC.json", "nws_obs_KLGA.json", "nws_obs_KJFK.json", "nws_obs_KDAB.json", "nws_obs_KDLH.json", "nws_obs_KLCH.json"):
        doc = load_json(name)
        now = W.parse_iso8601(doc["properties"]["timestamp"]) + 300
        o = W.parse_nws_observation(doc, now)
        assert o.temp_c is not None
        assert o.precip_type in W.PRECIP_TYPES
        assert o.precip_rate_basis in ("measured", "class", "trace", "model", "none")
        assert W.validate_contract(o.to_json_dict()) == ["missing fetched_at"] or o.fetched_at is None


def test_nws_rejects_stale_and_incomplete_observations():
    doc = load_json("nws_obs_KNYC.json")
    t = W.parse_iso8601(doc["properties"]["timestamp"])
    with pytest.raises(W.ProviderError, match="too old"):
        W.parse_nws_observation(doc, t + W.MAX_OBSERVATION_AGE_S + 1)
    bad = json.loads(json.dumps(doc))
    bad["properties"]["temperature"] = {"value": None, "qualityControl": "V"}
    with pytest.raises(W.ProviderError, match="without temperature"):
        W.parse_nws_observation(bad, t + 60)
    bad2 = json.loads(json.dumps(doc))
    bad2["properties"]["timestamp"] = None
    with pytest.raises(W.ProviderError, match="without timestamp"):
        W.parse_nws_observation(bad2, t + 60)


def test_nws_quality_control_rejects_bad_values():
    doc = load_json("nws_obs_KNYC.json")
    t = W.parse_iso8601(doc["properties"]["timestamp"])
    doc = json.loads(json.dumps(doc))
    doc["properties"]["visibility"] = {"value": 99999.0, "qualityControl": "X"}
    o = W.parse_nws_observation(doc, t + 60)
    assert o.visibility_m is None
    assert W._qc_value({"value": 5.0, "qualityControl": "V"}) == 5.0
    assert W._qc_value({"value": 5.0, "qualityControl": "Q"}) is None
    assert W._qc_value(None) is None


def test_nws_present_weather_is_decoded():
    """The recorded presentWeather blocks: -RA at KDAB, BR at KDLH, RA at KLCH, nothing at the NYC stations."""
    rain = load_json("nws_obs_KDAB.json")
    o = W.parse_nws_observation(rain, W.parse_iso8601(rain["properties"]["timestamp"]) + 60)
    assert o.precip_type == "rain" and o.precip_rate_mmph > 0.0 and o.thunder is False
    mist = load_json("nws_obs_KDLH.json")
    o2 = W.parse_nws_observation(mist, W.parse_iso8601(mist["properties"]["timestamp"]) + 60)
    assert o2.obscuration == ["BR"] and o2.precip_type == "none"
    dry = load_json("nws_obs_KNYC.json")
    o3 = W.parse_nws_observation(dry, W.parse_iso8601(dry["properties"]["timestamp"]) + 60)
    assert o3.precip_type == "none" and o3.obscuration == [] and o3.thunder is False


def test_nws_thunderstorm_and_fog_are_decoded_from_present_weather():
    """A synthetic presentWeather block in the exact api.weather.gov shape (thunderstorms + freezing fog)."""
    doc = load_json("nws_obs_KNYC.json")
    doc = json.loads(json.dumps(doc))
    doc["properties"]["presentWeather"] = [
        {"intensity": "heavy", "modifier": None, "weather": "rain", "rawString": "+TSRA"},
        {"intensity": None, "modifier": None, "weather": "thunderstorms", "rawString": "TS"},
        {"intensity": None, "modifier": None, "weather": "freezing_fog", "rawString": "FZFG"},
    ]
    o = W.parse_nws_observation(doc, W.parse_iso8601(doc["properties"]["timestamp"]) + 60)
    assert o.thunder is True
    assert o.precip_type == "rain"
    assert "FG" in o.obscuration
    assert o.precip_rate_basis == "class" and o.precip_rate_mmph == pytest.approx(10.0 * M.THUNDERSTORM_RATE_FACTOR)


def test_nws_measured_precipitation_without_a_present_weather_group():
    doc = json.loads(json.dumps(load_json("nws_obs_KNYC.json")))
    doc["properties"]["presentWeather"] = []
    doc["properties"]["precipitationLastHour"] = {"value": 2.5, "qualityControl": "V"}
    o = W.parse_nws_observation(doc, W.parse_iso8601(doc["properties"]["timestamp"]) + 60)
    assert o.precip_type == "rain" and o.precip_rate_basis == "measured" and o.precip_rate_mmph == pytest.approx(2.5)
    doc["properties"]["temperature"] = {"value": -4.0, "qualityControl": "V"}
    o2 = W.parse_nws_observation(doc, W.parse_iso8601(doc["properties"]["timestamp"]) + 60)
    assert o2.precip_type == "snow"


def test_iso_duration_parsing():
    assert W._duration_seconds("PT1H") == 3600
    assert W._duration_seconds("PT6H") == 6 * 3600
    assert W._duration_seconds("P1DT2H30M") == 86400 + 2 * 3600 + 1800
    with pytest.raises(ValueError):
        W._duration_seconds("nonsense")


def test_grid_series_interpolates_and_bounds():
    layer = {"values": [{"validTime": "2026-09-05T00:00:00+00:00/PT1H", "value": 10.0},
                        {"validTime": "2026-09-05T01:00:00+00:00/PT1H", "value": 20.0}]}
    s = W.GridSeries(layer)
    t0 = W.parse_iso8601("2026-09-05T00:00:00Z")
    assert s.value_at(t0) == pytest.approx(10.0)
    assert s.value_at(t0 + 1800) == pytest.approx(10.0)  # held across its validity
    assert s.value_at(t0 + 3600) == pytest.approx(20.0)
    assert s.value_at(t0 - 1) is None and s.value_at(t0 + 7200 + 1) is None
    assert W.GridSeries(None).value_at(t0) is None
    assert W.GridSeries({"values": [{"validTime": "2026-09-05T00:00:00+00:00/PT1H", "value": None}]}).value_at(t0) is None


def test_forecast_blend_carries_the_observation_along_the_trend_and_is_clamped():
    grid = load_json("nws_gridpoints.json")
    blend = W.NWSForecastBlend(grid)
    t = blend.series["temp_c"].t
    t_obs, now = t[0] + 60, t[0] + 4 * 3600
    f_obs, f_now = blend.series["temp_c"].value_at(t_obs), blend.series["temp_c"].value_at(now)
    o = W.WeatherObservation(observed_at=W.iso_utc(t_obs), temp_c=10.0, dewpoint_c=5.0, rh=71.0)
    assert blend.apply(o, now) is True
    assert o.interpolated is True
    assert o.temp_c == pytest.approx(10.0 + W.clamp(f_now - f_obs, -5.0, 5.0))
    assert o.dewpoint_c <= o.temp_c
    assert o.rh == pytest.approx(W.relative_humidity(o.temp_c, o.dewpoint_c))


def test_forecast_blend_is_skipped_for_fresh_observations():
    blend = W.NWSForecastBlend(load_json("nws_gridpoints.json"))
    t = blend.series["temp_c"].t[0]
    o = W.WeatherObservation(observed_at=W.iso_utc(t), temp_c=10.0)
    assert blend.apply(o, t + W.BLEND_MIN_AGE_S - 1) is False
    assert o.temp_c == 10.0 and o.interpolated is False


def test_nws_provider_falls_through_to_the_next_station():
    obs_doc = load_text("nws_obs_KLGA.json")
    ts = json.loads(obs_doc)["properties"]["timestamp"]
    fetch = FakeFetch({"stations/KNYC": net.HttpError("u", "503", 503), "stations/KLGA": obs_doc, "gridpoints": load_text("nws_gridpoints.json")})
    p = W.NWSProvider(fetch=fetch, use_forecast_blend=False)
    o = p.fetch(W.parse_iso8601(ts) + 60)
    assert o.station == "KLGA"
    assert any("KNYC" in c for c in fetch.calls) and any("KLGA" in c for c in fetch.calls)


def test_nws_provider_raises_when_every_station_fails():
    fetch = FakeFetch({"stations/": net.HttpError("u", "503", 503)})
    with pytest.raises(W.ProviderError):
        W.NWSProvider(fetch=fetch, use_forecast_blend=False).fetch(0.0)


# --------------------------------------------------------------------------- Open-Meteo
def test_parse_open_meteo_recorded():
    doc = load_json("openmeteo_current.json")
    cur = doc["current"]
    now = W.parse_iso8601(cur["time"]) + 300
    o = W.parse_open_meteo(doc, now)
    assert o.source == "open_meteo"
    assert o.temp_c == pytest.approx(cur["temperature_2m"])
    assert o.rh == pytest.approx(cur["relative_humidity_2m"])
    assert o.wind_mps == pytest.approx(cur["wind_speed_10m"])
    assert o.cloud_cover == pytest.approx(cur["cloud_cover"] / 100.0)
    assert o.pressure_hpa == pytest.approx(cur["pressure_msl"])
    assert o.raw_text == f"WMO {int(cur['weather_code'])}"
    assert o.precip_type in W.PRECIP_TYPES


@pytest.mark.parametrize(
    "code,kind,thunder,obsc",
    [(0, "none", False, []), (3, "none", False, []), (45, "none", False, ["FG"]), (51, "drizzle", False, []),
     (61, "rain", False, []), (65, "rain", False, []), (66, "freezing_rain", False, []), (71, "snow", False, []),
     (75, "snow", False, []), (77, "snow", False, []), (80, "rain", False, []), (86, "snow", False, []),
     (95, "rain", True, []), (96, "sleet", True, []), (99, "sleet", True, [])],
)
def test_wmo_code_mapping(code, kind, thunder, obsc):
    doc = {"latitude": 40.78, "longitude": -73.97,
           "current": {"time": "2026-09-05T18:45", "interval": 900, "temperature_2m": 5.0, "weather_code": code,
                       "precipitation": 0.0, "rain": 0.0, "showers": 0.0, "snowfall": 0.0}}
    o = W.parse_open_meteo(doc, W.parse_iso8601("2026-09-05T18:45") + 60)
    assert (o.precip_type, o.thunder, o.obscuration) == (kind, thunder, obsc)
    if kind == "none":
        assert o.precip_rate_mmph == 0.0 and o.precip_rate_basis == "none"
    else:
        assert o.precip_rate_mmph > 0.0 and o.precip_rate_basis == "class"


def test_open_meteo_measured_rate_beats_the_class_representative():
    doc = {"latitude": 40.78, "longitude": -73.97,
           "current": {"time": "2026-09-05T18:45", "interval": 900, "temperature_2m": 5.0, "weather_code": 61,
                       "precipitation": 0.75, "rain": 0.75, "showers": 0.0, "snowfall": 0.0}}
    o = W.parse_open_meteo(doc, W.parse_iso8601("2026-09-05T18:45") + 60)
    assert o.precip_rate_basis == "measured"
    assert o.precip_rate_mmph == pytest.approx(0.75 * 3600 / 900)  # mm in the interval -> mm/h


def test_open_meteo_types_precipitation_when_the_code_says_dry():
    base = {"time": "2026-09-05T18:45", "interval": 900, "temperature_2m": -2.0, "weather_code": 0, "rain": 0.0, "showers": 0.0}
    now = W.parse_iso8601("2026-09-05T18:45") + 60
    assert W.parse_open_meteo({"current": dict(base, precipitation=0.5, snowfall=0.4)}, now).precip_type == "snow"
    assert W.parse_open_meteo({"current": dict(base, precipitation=0.5, snowfall=0.0, rain=0.5)}, now).precip_type == "rain"
    assert W.parse_open_meteo({"current": dict(base, precipitation=0.5, snowfall=0.2, rain=0.3)}, now).precip_type == "sleet"


def test_open_meteo_errors():
    with pytest.raises(W.ProviderError):
        W.parse_open_meteo({"error": True, "reason": "bad latitude"}, 0.0)
    with pytest.raises(W.ProviderError):
        W.parse_open_meteo({}, 0.0)
    with pytest.raises(W.ProviderError):
        W.parse_open_meteo({"current": {"time": "2020-01-01T00:00", "temperature_2m": 1.0}}, 1.8e9)


def test_open_meteo_visibility_comes_from_the_nearest_minutely_sample():
    doc = load_json("openmeteo_current.json")
    o = W.parse_open_meteo(doc, W.parse_iso8601(doc["current"]["time"]) + 60)
    m15 = doc.get("minutely_15") or {}
    if m15.get("visibility"):
        assert o.visibility_m is not None


# --------------------------------------------------------------------------- METAR provider
def test_observation_from_metar_recorded():
    rep = M.parse_metar(load_text("metar_tgftp_KNYC.txt"))
    now = rep.observation_time.timestamp() + 600
    o = W.observation_from_metar(rep, now)
    assert o.source == "metar" and o.station == "KNYC"
    assert o.temp_c == 25.0 and o.dewpoint_c == 13.9
    assert o.rh == pytest.approx(W.relative_humidity(25.0, 13.9))
    assert o.wind_dir_deg is None  # VRB
    assert o.pressure_hpa == pytest.approx(1010.1)
    assert o.precip_type == "none" and o.cloud_cover == pytest.approx(0.4375)


def test_observation_from_metar_rejects_old_and_empty_reports():
    rep = M.parse_metar(load_text("metar_tgftp_KNYC.txt"))
    with pytest.raises(W.ProviderError, match="too old"):
        W.observation_from_metar(rep, rep.observation_time.timestamp() + W.MAX_OBSERVATION_AGE_S + 1)
    nil = M.parse_metar("KNYC 051851Z NIL", dt.datetime(2026, 9, 5, 19, 0, tzinfo=dt.timezone.utc))
    with pytest.raises(W.ProviderError):
        W.observation_from_metar(nil, nil.observation_time.timestamp() + 60)


def test_metar_provider_prefers_awc_then_falls_back_to_tgftp():
    rows = load_json("metar_awc_nyc.json")
    now = max(float(r["obsTime"]) for r in rows) + 600
    fetch = FakeFetch({"aviationweather.gov": json.dumps(rows)})
    o = W.METARProvider(fetch=fetch).fetch(now)
    assert o.source == "metar" and o.station in W.METAR_STATIONS
    assert len(fetch.calls) == 1
    fetch2 = FakeFetch({"aviationweather.gov": net.HttpError("u", "blocked by egress policy", 403),
                        "tgftp.nws.noaa.gov": load_text("metar_tgftp_KNYC.txt")})
    rep = M.parse_metar(load_text("metar_tgftp_KNYC.txt"))
    o2 = W.METARProvider(fetch=fetch2).fetch(rep.observation_time.timestamp() + 600)
    assert o2.station == "KNYC"
    assert any("tgftp" in c for c in fetch2.calls)


def test_metar_provider_raises_when_everything_fails():
    fetch = FakeFetch({"aviationweather.gov": net.HttpError("u", "403", 403), "tgftp": net.HttpError("u", "404", 404)})
    with pytest.raises(W.ProviderError):
        W.METARProvider(fetch=fetch).fetch(1.8e9)


# --------------------------------------------------------------------------- snow model
def test_snow_model_observed_depth_overrides_the_model(tmp_path):
    m = W.SnowModel(tmp_path / "snow.json")
    o = W.WeatherObservation(snow_depth_cm=12.7, snow_depth_source="observed", temp_c=-3.0)
    m.update(o, 1000.0)
    assert m.state.depth_cm == pytest.approx(12.7) and m.state.source == "observed"
    assert json.loads((tmp_path / "snow.json").read_text())["depth_cm"] == pytest.approx(12.7)


def test_snow_model_accumulates_then_melts(tmp_path):
    m = W.SnowModel(tmp_path / "snow.json")
    o = W.WeatherObservation(temp_c=-4.0, precip_type="snow", precip_rate_mmph=1.0)
    m.update(o, 0.0)  # first update only seeds the clock
    assert m.state.depth_cm == 0.0
    m.update(o, 3600.0)  # 1 h at 1 mm/h liquid with SLR 10 -> 1.0 cm, minus 2 %/day settling
    assert m.state.depth_cm == pytest.approx(1.0 * (1 - 0.02 / 24), rel=1e-6)
    assert o.snowfall_rate_cmph == pytest.approx(1.0)
    warm = W.WeatherObservation(temp_c=6.0, precip_type="none")
    m.update(warm, 3600.0 * 2)  # melt 0.06*(6-1) = 0.30 cm in an hour
    assert m.state.depth_cm == pytest.approx((1.0 * (1 - 0.02 / 24) - 0.30) * (1 - 0.02 / 24), rel=1e-6)
    assert warm.snow_depth_source == "model"


def test_snow_model_rain_on_snow_and_floor_at_zero(tmp_path):
    m = W.SnowModel(tmp_path / "snow.json")
    m.state = W.SnowState(depth_cm=0.5, last_update_unix=0.0, source="model")
    o = W.WeatherObservation(temp_c=8.0, precip_type="rain", precip_rate_mmph=5.0)
    m.update(o, 3600.0 * 3)
    assert m.state.depth_cm == 0.0 and o.snow_depth_source == "none"


@pytest.mark.parametrize("temp,slr", [(2.0, 8.0), (-1.0, 10.0), (-7.0, 13.0), (-15.0, 18.0), (None, 8.0)])
def test_snow_liquid_ratio_bands(temp, slr):
    assert W.SnowModel.snow_liquid_ratio(temp, "snow") == slr
    assert W.SnowModel.snow_liquid_ratio(temp, "sleet") == 3.0


def test_snow_model_step_is_capped(tmp_path):
    m = W.SnowModel(tmp_path / "snow.json")
    m.state = W.SnowState(depth_cm=10.0, last_update_unix=0.0, source="model")
    m.update(W.WeatherObservation(temp_c=11.0, precip_type="none"), 30 * 86400.0)
    # capped at MAX_STEP_H = 6 h: melt = 0.06*10*6 = 3.6 cm, not 30 days' worth
    assert m.state.depth_cm == pytest.approx((10.0 - 3.6) * (1 - 0.02 * 6 / 24), rel=1e-6)


# --------------------------------------------------------------------------- the service
def _service(tmp_path, routes, clock):
    return W.WeatherService(
        providers=[W.NWSProvider(fetch=FakeFetch(routes), use_forecast_blend=False),
                   W.OpenMeteoProvider(fetch=FakeFetch(routes)),
                   W.METARProvider(fetch=FakeFetch(routes))],
        out_path=tmp_path / "weather.json",
        clock=clock,
        snow_model=W.SnowModel(tmp_path / "snow.json"),
    )


def test_service_prefers_nws_and_writes_a_valid_snapshot(tmp_path):
    doc = load_text("nws_obs_KNYC.json")
    now = W.parse_iso8601(json.loads(doc)["properties"]["timestamp"]) + 600
    svc = _service(tmp_path, {"stations/KNYC": doc}, lambda: now)
    o = svc.poll()
    assert o.source == "nws" and o.station == "KNYC"
    assert o.fetched_at == W.iso_utc(now) and o.stale_age_s == pytest.approx(600.0, abs=1.0)
    written = json.loads((tmp_path / "weather.json").read_text())
    assert W.validate_contract(written) == []
    assert set(W.CONTRACT_KEYS + W.EXTENSION_KEYS) <= set(written)
    assert written["provider_status"] == {"nws": "closed", "open_meteo": "closed", "metar": "closed"}


def test_service_falls_through_the_provider_order(tmp_path):
    om = load_text("openmeteo_current.json")
    now = W.parse_iso8601(json.loads(om)["current"]["time"]) + 600
    svc = _service(tmp_path, {"stations/": net.HttpError("u", "503", 503), "open-meteo": om}, lambda: now)
    o = svc.poll()
    assert o.source == "open_meteo"
    assert svc.breakers["nws"].consecutive_failures == 1
    assert svc.breakers["open_meteo"].state == "closed"


def test_service_falls_through_to_metar(tmp_path):
    rows = load_json("metar_awc_nyc.json")
    now = max(float(r["obsTime"]) for r in rows) + 600
    svc = _service(tmp_path, {"stations/": net.HttpError("u", "503", 503),
                              "open-meteo": net.HttpError("u", "429", 429),
                              "aviationweather.gov": json.dumps(rows)}, lambda: now)
    o = svc.poll()
    assert o.source == "metar"


def test_service_goes_stale_and_keeps_the_last_good_values(tmp_path):
    doc = load_text("nws_obs_KNYC.json")
    t0 = W.parse_iso8601(json.loads(doc)["properties"]["timestamp"]) + 600
    clock = {"t": t0}
    good_routes = {"stations/KNYC": doc}
    svc = W.WeatherService(
        providers=[W.NWSProvider(fetch=FakeFetch(good_routes), use_forecast_blend=False)],
        out_path=tmp_path / "weather.json", clock=lambda: clock["t"], snow_model=W.SnowModel(tmp_path / "snow.json"))
    first = svc.poll()
    assert first.source == "nws"
    svc.providers[0]._fetch = FakeFetch({"stations/": net.HttpError("u", "503", 503)})
    clock["t"] = t0 + 3600
    stale = svc.poll()
    assert stale.source == "stale"
    assert stale.temp_c == first.temp_c and stale.station == first.station
    assert stale.observed_at == first.observed_at
    assert stale.stale_age_s == pytest.approx(4200.0, abs=1.0)
    assert stale.interpolated is False
    assert W.validate_contract(json.loads((tmp_path / "weather.json").read_text())) == []


def test_service_never_invents_values_when_it_has_no_history(tmp_path):
    svc = _service(tmp_path, {}, lambda: 1.8e9)
    o = svc.poll()
    assert o.source == "stale"
    assert o.temp_c is None and o.dewpoint_c is None and o.wind_mps is None and o.visibility_m is None
    assert o.precip_type == "none" and o.stale_age_s is None
    assert o.snow_depth_source == "none"


def test_service_skips_open_breakers(tmp_path):
    routes = {"stations/": net.HttpError("u", "503", 503)}
    fetch = FakeFetch(routes)
    svc = W.WeatherService(providers=[W.NWSProvider(fetch=fetch, use_forecast_blend=False)],
                           out_path=tmp_path / "weather.json", clock=lambda: 1.8e9,
                           snow_model=W.SnowModel(tmp_path / "snow.json"))
    for _ in range(3):
        svc.poll()
    calls_after_open = len(fetch.calls)
    assert svc.breakers["nws"].state == "open"
    svc.poll()
    assert len(fetch.calls) == calls_after_open  # no network traffic while the breaker is open
    assert svc.current.provider_status["nws"].startswith("open(")


def test_service_reloads_the_previous_snapshot_from_disk(tmp_path):
    doc = load_text("nws_obs_KNYC.json")
    t0 = W.parse_iso8601(json.loads(doc)["properties"]["timestamp"]) + 600
    svc = _service(tmp_path, {"stations/KNYC": doc}, lambda: t0)
    svc.poll()
    svc2 = W.WeatherService(providers=[W.NWSProvider(fetch=FakeFetch({}), use_forecast_blend=False)],
                            out_path=tmp_path / "weather.json", clock=lambda: t0 + 60,
                            snow_model=W.SnowModel(tmp_path / "snow.json"))
    assert svc2.last_good is not None and svc2.last_good.station == "KNYC"
    o = svc2.poll()
    assert o.source == "stale" and o.temp_c == svc.current.temp_c


def test_service_survives_a_provider_that_raises_an_unexpected_exception(tmp_path):
    class Exploding:
        name = "nws"

        def fetch(self, now):
            raise ZeroDivisionError("boom")

    svc = W.WeatherService(providers=[Exploding()], out_path=tmp_path / "weather.json", clock=lambda: 1.8e9,
                           snow_model=W.SnowModel(tmp_path / "snow.json"))
    o = svc.poll()
    assert o.source == "stale"
    assert svc.breakers["nws"].consecutive_failures == 1
    assert "ZeroDivisionError" in svc.breakers["nws"].last_error


def test_service_run_stops_after_max_polls(tmp_path):
    doc = load_text("nws_obs_KNYC.json")
    t0 = W.parse_iso8601(json.loads(doc)["properties"]["timestamp"]) + 600
    svc = _service(tmp_path, {"stations/KNYC": doc}, lambda: t0)
    svc.poll_interval_s = 0.0
    svc.run(max_polls=3)
    assert svc.polls == 3


# --------------------------------------------------------------------------- contract
def test_validate_contract_catches_every_violation():
    good = W.WeatherObservation(source="nws", observed_at="2026-09-05T18:51:00Z", fetched_at="2026-09-05T18:55:00Z",
                                temp_c=20.0, cloud_cover=0.5, wind_dir_deg=10.0).to_json_dict()
    assert W.validate_contract(good) == []
    assert "source 'nope'" in W.validate_contract(dict(good, source="nope"))
    assert "precip_type 'mist'" in W.validate_contract(dict(good, precip_type="mist"))
    assert "cloud_cover range" in W.validate_contract(dict(good, cloud_cover=1.5))
    assert "wind_dir_deg range" in W.validate_contract(dict(good, wind_dir_deg=360.0))
    assert "thunder not bool" in W.validate_contract(dict(good, thunder=1))
    assert "schema_version" in W.validate_contract(dict(good, schema_version=99))
    del good["station"]
    assert "missing station" in W.validate_contract(good)


def test_to_json_dict_rounds_and_keeps_nulls():
    o = W.WeatherObservation(temp_c=1.23456789, rh=None)
    d = o.to_json_dict()
    assert d["temp_c"] == 1.235 and d["rh"] is None
    assert d["obscuration"] == [] and d["provider_status"] == {}


# --------------------------------------------------------------------------- optional freshness preference
def test_strict_provider_order_is_the_default(tmp_path):
    """ADR-011: the first provider that answers wins, even with a much older observation."""
    nws = load_text("nws_obs_KNYC.json")
    t_nws = W.parse_iso8601(json.loads(nws)["properties"]["timestamp"])
    om = json.loads(load_text("openmeteo_current.json"))
    om["current"]["time"] = W.iso_utc(t_nws + 3600)  # an hour fresher
    routes = {"stations/KNYC": nws, "open-meteo": json.dumps(om)}
    fetch = FakeFetch(routes)
    svc = W.WeatherService(providers=[W.NWSProvider(fetch=fetch, use_forecast_blend=False), W.OpenMeteoProvider(fetch=fetch)],
                           out_path=tmp_path / "w.json", clock=lambda: t_nws + 4200, snow_model=W.SnowModel(tmp_path / "s.json"))
    o = svc.poll()
    assert o.source == "nws" and o.observed_at == W.iso_utc(t_nws)
    assert not any("open-meteo" in c for c in fetch.calls)


def test_prefer_freshest_queries_the_rest_only_when_the_leader_is_old(tmp_path):
    nws = load_text("nws_obs_KNYC.json")
    t_nws = W.parse_iso8601(json.loads(nws)["properties"]["timestamp"])
    om = json.loads(load_text("openmeteo_current.json"))
    om["current"]["time"] = W.iso_utc(t_nws + 3600)
    routes = {"stations/KNYC": nws, "open-meteo": json.dumps(om)}

    def build(now, threshold):
        f = FakeFetch(routes)
        return f, W.WeatherService(providers=[W.NWSProvider(fetch=f, use_forecast_blend=False), W.OpenMeteoProvider(fetch=f)],
                                   out_path=tmp_path / "w.json", clock=lambda: now, snow_model=W.SnowModel(tmp_path / "s.json"),
                                   prefer_freshest_age_s=threshold)

    f1, svc1 = build(t_nws + 4200, 2700.0)  # leader 70 min old -> keep looking, the fresher one wins
    o1 = svc1.poll()
    assert o1.source == "open_meteo" and o1.observed_at == W.iso_utc(t_nws + 3600)
    assert any("open-meteo" in c for c in f1.calls)

    f2, svc2 = build(t_nws + 600, 2700.0)  # leader 10 min old -> nobody else is queried
    o2 = svc2.poll()
    assert o2.source == "nws"
    assert not any("open-meteo" in c for c in f2.calls)
