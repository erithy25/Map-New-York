"""Empire State Building tower lights and NOAA CO-OPS tides/currents, against recorded pages/responses."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from conftest import FakeFetch, load_json, load_text
from nycsim_live import esb_lights as E
from nycsim_live import net
from nycsim_live import tides as TD


# =========================================================================== ESB
def test_parse_recorded_tower_lights_page():
    page = E.parse_tower_lights_page(load_text("esb_tower_lights.html"))
    assert set(page) == {"yesterday", "today", "tomorrow"}
    today = page["today"]
    assert today is not None
    assert dt.date.fromisoformat(today.date) == dt.date(2026, 9, 5)
    assert today.colors and all(isinstance(c, str) for c in today.colors)
    assert len(today.rgb) == len(today.colors)
    assert all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in today.rgb)
    assert today.source_url == E.TOWER_LIGHTS_URL
    assert today.fallback is False
    for key, delta in (("yesterday", -1), ("tomorrow", 1)):
        if page[key] is not None:
            assert dt.date.fromisoformat(page[key].date) == dt.date(2026, 9, 5) + dt.timedelta(days=delta)


def test_parse_recorded_calendar_page():
    cal = E.parse_calendar_page(load_text("esb_calendar.html"))
    assert len(cal) >= 5
    for d, e in cal.items():
        assert isinstance(d, dt.date) and e.date == d.isoformat()
        assert e.colors and len(e.rgb) == len(e.colors)
        assert e.hours


def test_parse_pages_raise_on_changed_markup():
    with pytest.raises(E.ESBParseError, match="three-days-lights-wrapper"):
        E.parse_tower_lights_page("<html><body><p>redesigned</p></body></html>")
    with pytest.raises(E.ESBParseError, match="lights-calendar-view"):
        E.parse_calendar_page("<html><body><p>redesigned</p></body></html>")


@pytest.mark.parametrize(
    "text,names",
    [
        ("Red, White & Blue", ["Red", "White", "Blue"]),
        ("Red, white and blue", ["Red", "White", "Blue"]),
        ("Signature White", ["Signature White"]),
        ("Purple and Gold", ["Purple", "Gold"]),
        ("Red / White / Blue", ["Red", "White", "Blue"]),
        ("Green colors", ["Green"]),
    ],
)
def test_split_color_names(text, names):
    assert E.split_color_names(text) == names


def test_colors_to_rgb_flags_unknown_names():
    rgb, unknown = E.colors_to_rgb(["Red", "Blue"])
    assert len(rgb) == 2 and unknown == []
    rgb2, unknown2 = E.colors_to_rgb(["Chartreuse Sparkle"])
    assert unknown2 == ["Chartreuse Sparkle"] and rgb2 == []  # never invents an RGB for a name it does not know
    rgb3, unknown3 = E.colors_to_rgb(["Giants Blue"])  # resolved through the last word
    assert unknown3 == [] and rgb3 == [list(E.COLOR_RGB["blue"])]
    # a record whose colours all fail to resolve is still lit, with signature white, and records the failure
    e = E._make(dt.date(2026, 9, 6), "Chartreuse Sparkle", "test", None, E.TOWER_LIGHTS_URL)
    assert e.rgb == [list(E.SIGNATURE_WHITE_RGB)] and e.unknown_colors == ["Chartreuse Sparkle"]
    assert e.colors == ["Chartreuse Sparkle"]


def test_rainbow_expands_to_the_documented_sequence():
    rgb, unknown = E.colors_to_rgb(["Rainbow"])
    assert unknown == []
    assert rgb == [list(c) for _, c in E.RAINBOW_SEQUENCE]


def test_canonical_color_name():
    assert E.canonical_color_name("  RED lights ") == "Red"
    assert E.canonical_color_name("signature white") == "Signature White"


def test_signature_white_fallback():
    e = E.signature_white(dt.date(2026, 9, 6), "no schedule")
    assert e.colors == [E.SIGNATURE_WHITE_NAME] and e.fallback is True
    assert e.rgb == [list(E.SIGNATURE_WHITE_RGB)]
    assert e.hours == E.DEFAULT_HOURS


def test_service_uses_the_page_then_writes_a_snapshot(tmp_path):
    fetch = FakeFetch({"tower-lights/calendar": load_text("esb_calendar.html"), "tower-lights": load_text("esb_tower_lights.html")})
    svc = E.ESBLightsService(out_path=tmp_path / "esb.json", fetch=fetch, clock=lambda: 1788000000.0)
    e = svc.poll(dt.date(2026, 9, 5))
    assert e.date == "2026-09-05" and e.fallback is False
    doc = json.loads((tmp_path / "esb.json").read_text())
    assert doc["date"] == "2026-09-05" and doc["colors"] == e.colors and doc["schema_version"] == E.SCHEMA_VERSION
    assert doc["fetched_at"].endswith("Z")


def test_service_falls_back_to_signature_white_when_both_pages_fail(tmp_path):
    fetch = FakeFetch({"esbnyc.com": net.HttpError("u", "503", 503)})
    svc = E.ESBLightsService(out_path=tmp_path / "esb.json", fetch=fetch, clock=lambda: 1788000000.0)
    e = svc.poll(dt.date(2026, 9, 6))
    assert e.colors == [E.SIGNATURE_WHITE_NAME] and e.fallback is True
    assert "unavailable" in e.reason


def test_service_falls_back_when_the_date_is_not_listed(tmp_path):
    fetch = FakeFetch({"tower-lights/calendar": load_text("esb_calendar.html"), "tower-lights": load_text("esb_tower_lights.html")})
    svc = E.ESBLightsService(out_path=tmp_path / "esb.json", fetch=fetch, clock=lambda: 1788000000.0)
    e = svc.poll(dt.date(2030, 1, 1))
    assert e.fallback is True and e.colors == [E.SIGNATURE_WHITE_NAME]


def test_service_caches_within_the_refresh_window(tmp_path):
    fetch = FakeFetch({"tower-lights/calendar": load_text("esb_calendar.html"), "tower-lights": load_text("esb_tower_lights.html")})
    t = {"v": 1788000000.0}
    svc = E.ESBLightsService(out_path=tmp_path / "esb.json", fetch=fetch, clock=lambda: t["v"])
    svc.poll(dt.date(2026, 9, 5))
    n = len(fetch.calls)
    t["v"] += 60.0
    svc.poll(dt.date(2026, 9, 5))
    assert len(fetch.calls) == n
    t["v"] += 3601.0
    svc.poll(dt.date(2026, 9, 5))
    assert len(fetch.calls) > n


# =========================================================================== tides
def test_parse_water_level():
    wl = TD.parse_water_level(load_json("coops_wl_battery.json"))
    assert wl.station == "8518750"
    assert wl.level_mllw_m == pytest.approx(1.779)
    assert wl.quality == "p"
    assert wl.observed_unix == TD._coops_time("2026-09-05 19:00")


def test_parse_water_level_errors():
    with pytest.raises(TD.TidesError):
        TD.parse_water_level({"error": {"message": "No data was found"}})
    with pytest.raises(TD.TidesError):
        TD.parse_water_level({"data": []})
    with pytest.raises(TD.TidesError):
        TD.parse_water_level({"metadata": {"id": "1"}, "data": [{"t": "2026-09-05 19:00", "v": ""}]})


def test_parse_datum_offset():
    off = TD.parse_datum_offset(load_json("coops_meta_8518750_metric.json"))
    assert off == pytest.approx(TD.NAVD88_MINUS_MLLW_M_FALLBACK, abs=0.02)
    with pytest.raises(TD.TidesError):
        TD.parse_datum_offset({"units": "feet", "datums": [{"name": "NAVD88", "value": 1.0}, {"name": "MLLW", "value": 0.0}]})
    with pytest.raises(TD.TidesError):
        TD.parse_datum_offset({"units": "meters", "datums": [{"name": "MLLW", "value": 0.0}]})


def test_water_level_datum_conversion_is_applied():
    wl = TD.parse_water_level(load_json("coops_wl_battery.json"))
    off = TD.parse_datum_offset(load_json("coops_meta_8518750_metric.json"))
    assert wl.level_mllw_m - off == pytest.approx(1.779 - off)


@pytest.mark.parametrize("name", ["coops_cur_NYH1924.json", "coops_cur_NYH1920.json", "coops_cur_NYH1927.json", "coops_cur_n03020.json"])
def test_parse_currents(name):
    st = name[len("coops_cur_") : -len(".json")]
    s = TD.parse_currents(load_json(name), st)
    assert s.station == st
    assert len(s.predictions) >= 4
    assert 0.0 <= s.flood_dir_deg < 360.0 and 0.0 <= s.ebb_dir_deg < 360.0
    assert list(s.predictions) == sorted(s.predictions, key=lambda p: p.unix)
    assert any(p.velocity_cms > 0 for p in s.predictions) and any(p.velocity_cms < 0 for p in s.predictions)


def test_parse_currents_errors():
    with pytest.raises(TD.TidesError):
        TD.parse_currents({"error": {"message": "bad station"}}, "X")
    with pytest.raises(TD.TidesError):
        TD.parse_currents({"current_predictions": {"cp": []}}, "X")


def test_interpolate_velocity_is_linear_and_bounded():
    s = TD.parse_currents(load_json("coops_cur_NYH1924_h.json"), "NYH1924")
    p = s.predictions
    assert TD.interpolate_velocity(s, p[0].unix) == pytest.approx(p[0].velocity_cms)
    assert TD.interpolate_velocity(s, p[-1].unix) == pytest.approx(p[-1].velocity_cms)
    mid = 0.5 * (p[0].unix + p[1].unix)
    assert TD.interpolate_velocity(s, mid) == pytest.approx(0.5 * (p[0].velocity_cms + p[1].velocity_cms))
    assert TD.interpolate_velocity(s, p[0].unix - 1) is None
    assert TD.interpolate_velocity(s, p[-1].unix + 1) is None


def test_velocity_to_flow_phases():
    s = TD.parse_currents(load_json("coops_cur_NYH1924.json"), "NYH1924")
    speed, heading, phase = TD.velocity_to_flow(s, 100.0)
    assert speed == pytest.approx(1.0) and heading == s.flood_dir_deg and phase == "flood"
    speed, heading, phase = TD.velocity_to_flow(s, -50.0)
    assert speed == pytest.approx(0.5) and heading == s.ebb_dir_deg and phase == "ebb"
    assert TD.velocity_to_flow(s, 2.0)[2] == "slack"
    assert TD.velocity_to_flow(s, -4.9)[2] == "slack"


def test_parse_hilo():
    preds = TD.parse_hilo(load_json("coops_wl_pred_battery.json"))
    assert len(preds) >= 4
    assert {p.kind for p in preds} <= {"H", "L"}
    assert all(p.level_mllw_m > -1.0 for p in preds)
    kinds = [p.kind for p in preds]
    assert all(a != b for a, b in zip(kinds, kinds[1:]))  # highs and lows alternate


def test_compass_to_math_convention():
    assert TD.compass_to_math(0.0) == pytest.approx(90.0)
    assert TD.compass_to_math(241.0) == pytest.approx(209.0)


def test_url_builders_carry_the_required_parameters():
    u = TD.water_level_url()
    assert "station=8518750" in u and "datum=MLLW" in u and "units=metric" in u and "time_zone=gmt" in u
    begin = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    assert "20260905" in TD.hilo_predictions_url(TD.BATTERY_STATION, begin)
    assert "interval=30" in TD.currents_url("NYH1924", begin)
    assert TD.BATTERY_STATION in TD.datums_url()


def test_tides_service_full_snapshot(tmp_path):
    routes = {
        "product=water_level": load_text("coops_wl_battery.json"),
        "datums": load_text("coops_meta_8518750_metric.json"),
        "product=predictions&": load_text("coops_wl_pred_battery.json"),
        "NYH1924": load_text("coops_cur_NYH1924.json"),
        "NYH1920": load_text("coops_cur_NYH1920.json"),
        "NYH1927": load_text("coops_cur_NYH1927.json"),
        "n03020": load_text("coops_cur_n03020.json"),
    }
    now = TD._coops_time("2026-09-05 19:00") + 300
    svc = TD.TidesService(out_path=tmp_path / "tides.json", fetch=FakeFetch(routes), clock=lambda: now)
    snap = svc.poll()
    assert snap.errors == []
    assert snap.stale is False
    assert snap.water_level_mllw_m == pytest.approx(1.779)
    assert snap.water_level_m == pytest.approx(1.779 - snap.navd88_minus_mllw_m)
    assert snap.current_station == "NYH1924"
    assert snap.current_speed_mps is not None and snap.current_phase in ("flood", "ebb", "slack")
    assert snap.current_dir_deg == pytest.approx(TD.compass_to_math(snap.current_heading))
    assert len(snap.currents) == len(TD.CURRENT_STATIONS)
    doc = json.loads((tmp_path / "tides.json").read_text())
    for k in ("station", "current_speed_mps", "current_dir_deg", "water_level_m", "predicted_at"):
        assert k in doc  # DATA_CONTRACTS §12 keys
    assert doc["schema_version"] == TD.SCHEMA_VERSION


def test_tides_service_marks_itself_stale_when_the_water_level_fails(tmp_path):
    routes = {"product=water_level": net.HttpError("u", "503", 503), "datums": load_text("coops_meta_8518750_metric.json"),
              "product=predictions&": load_text("coops_wl_pred_battery.json"), "NYH1924": load_text("coops_cur_NYH1924.json"),
              "NYH1920": load_text("coops_cur_NYH1920.json"), "NYH1927": load_text("coops_cur_NYH1927.json"),
              "n03020": load_text("coops_cur_n03020.json")}
    now = TD._coops_time("2026-09-05 19:00") + 300
    svc = TD.TidesService(out_path=tmp_path / "tides.json", fetch=FakeFetch(routes), clock=lambda: now)
    snap = svc.poll()
    assert snap.stale is True and any("water_level" in e for e in snap.errors)
    assert snap.water_level_m is None


def test_tides_service_uses_the_published_datum_when_the_datum_call_fails(tmp_path):
    routes = {"product=water_level": load_text("coops_wl_battery.json"), "datums": net.HttpError("u", "503", 503),
              "product=predictions&": load_text("coops_wl_pred_battery.json"), "NYH1924": load_text("coops_cur_NYH1924.json"),
              "NYH1920": load_text("coops_cur_NYH1920.json"), "NYH1927": load_text("coops_cur_NYH1927.json"),
              "n03020": load_text("coops_cur_n03020.json")}
    now = TD._coops_time("2026-09-05 19:00") + 300
    svc = TD.TidesService(out_path=tmp_path / "tides.json", fetch=FakeFetch(routes), clock=lambda: now)
    snap = svc.poll()
    assert snap.navd88_minus_mllw_m == pytest.approx(TD.NAVD88_MINUS_MLLW_M_FALLBACK)
    assert any("datums" in e for e in snap.errors)


def test_tides_service_reports_a_rejected_stale_water_level(tmp_path):
    routes = {"product=water_level": load_text("coops_wl_battery.json"), "datums": load_text("coops_meta_8518750_metric.json"),
              "product=predictions&": load_text("coops_wl_pred_battery.json"), "NYH1924": load_text("coops_cur_NYH1924.json"),
              "NYH1920": load_text("coops_cur_NYH1920.json"), "NYH1927": load_text("coops_cur_NYH1927.json"),
              "n03020": load_text("coops_cur_n03020.json")}
    now = TD._coops_time("2026-09-05 19:00") + TD.MAX_WATER_LEVEL_AGE_S + 60
    svc = TD.TidesService(out_path=tmp_path / "tides.json", fetch=FakeFetch(routes), clock=lambda: now)
    snap = svc.poll()
    assert snap.stale is True and any("too old" in e for e in snap.errors)
