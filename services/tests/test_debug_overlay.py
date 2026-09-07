"""The debug overlay text block: formatting primitives, completeness, and the staleness markers."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from conftest import load_json, load_text
from nycsim_live import astronomy as A
from nycsim_live import debug_overlay as D
from nycsim_live import timesync as T
from nycsim_live import weather as W
from nycsim_live.worldmapping import WorldMapper

UTC = dt.datetime(2026, 9, 6, 11, 24, 40, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def observation() -> W.WeatherObservation:
    doc = load_json("nws_obs_KNYC.json")
    o = W.parse_nws_observation(doc, W.parse_iso8601(doc["properties"]["timestamp"]) + 600)
    o.fetched_at = W.iso_utc(W.parse_iso8601(doc["properties"]["timestamp"]) + 600)
    o.stale_age_s = 600.0
    o.provider_status = {"nws": "closed", "open_meteo": "closed", "metar": "closed"}
    return o


@pytest.fixture(scope="module")
def block(observation, tmp_path_factory) -> str:
    m = WorldMapper(tmp_path_factory.mktemp("ov") / "world.json", clock=lambda: 0.0)
    world = m.update(observation, 0.0)
    return D.render(T.sim_time(UTC), observation, world, esb=json.loads(_esb_doc()), tides=json.loads(_tides_doc()))


def _esb_doc() -> str:
    return json.dumps({"date": "2026-09-06", "colors": ["Red", "White", "Blue"], "rgb": [[230, 20, 20], [255, 255, 255], [0, 70, 255]],
                       "hours": "sunset to 02:00", "reason": "In Honor of Labor Day", "fallback": False, "fetched_at": "2026-09-06T11:24:41Z"})


def _tides_doc() -> str:
    return json.dumps({"station": "8518750", "water_level_m": 0.21, "water_level_mllw_m": 1.056, "water_level_observed_at": "2026-09-06T11:18:00Z",
                       "current_station": "NYH1924", "current_speed_mps": 1.4194, "current_heading": 241.0, "current_dir_deg": 209.0,
                       "current_phase": "ebb", "stale": False, "errors": [],
                       "next_tides": [{"utc": "2026-09-06T14:38:00Z", "kind": "L", "level_m": -0.608}]})


# --------------------------------------------------------------------------- primitives
@pytest.mark.parametrize("heading,point", [(0.0, "N"), (11.2, "N"), (11.3, "NNE"), (90.0, "E"), (180.0, "S"), (270.0, "W"), (350.0, "N"), (None, D.NONE_TEXT)])
def test_compass_point(heading, point):
    assert D.compass_point(heading) == point


def test_compass_point_covers_all_sixteen():
    assert {D.compass_point(a * 22.5) for a in range(16)} == set(D._COMPASS)


@pytest.mark.parametrize(
    "seconds,text",
    [(None, D.NONE_TEXT), (0, "0s"), (9, "9s"), (59, "59s"), (60, "1m 00s"), (249, "4m 09s"), (3600, "1h 00m 00s"), (3849, "1h 04m 09s"), (-30, "-30s")],
)
def test_fmt_duration(seconds, text):
    assert D.fmt_duration(seconds) == text


def test_fmt_num_and_bool():
    assert D.fmt_num(None) == D.NONE_TEXT
    assert D.fmt_num(float("nan")) == D.NONE_TEXT
    assert D.fmt_num(1.25, 1, "C") == "1.2 C" or D.fmt_num(1.25, 1, "C") == "1.3 C"  # banker's rounding
    assert D.fmt_num(-3.0, 1, "C", plus=True) == "-3.0 C"
    assert D.fmt_num(3.0, 1, "C", plus=True) == "+3.0 C"
    assert D.fmt_num(0.0, 0) == "0"
    assert D.fmt_bool(None) == D.NONE_TEXT
    assert (D.fmt_bool(True), D.fmt_bool(False)) == ("yes", "no")
    assert D.fmt_list([]) == "none" and D.fmt_list(["FG", "BR"]) == "FG, BR"


def test_fmt_num_never_uses_scientific_notation():
    assert "e" not in D.fmt_num(1e-9, 6)
    assert "e" not in D.fmt_num(1e12, 2)


def test_header_and_line_layout():
    h = D.header("TIME")
    assert len(h) == D.WIDTH and h.startswith("== TIME ") and h.endswith("=")
    ln = D.line("wind", "calm")
    assert ln.startswith(" wind") and ln[1 + D.LABEL_W : 1 + D.LABEL_W + 2] == ": "
    assert D.line("wind", "calm", "!")[0] == "!"


# --------------------------------------------------------------------------- sections
def test_every_weather_field_appears(observation, block):
    labels = ["provider", "station", "observed at", "fetched at", "stale age", "schema version", "temperature",
              "dewpoint", "relative humidity", "wind", "wind dir (math)", "wind to", "precipitation",
              "snowfall rate", "snow depth", "cloud cover", "visibility", "pressure (MSL)", "thunder",
              "obscuration", "interpolated", "raw"]
    for lbl in labels:
        assert f" {lbl:<{D.LABEL_W}}: " in block, lbl


def test_all_sections_present(block):
    for title in ("TIME", "SUN (NREL SPA)", "MOON (Meeus 47/48)", "WEATHER", "WORLD MAPPING", "PROVIDERS", "ESB TOWER LIGHTS", "TIDES / CURRENTS"):
        assert D.header(title) in block


def test_values_from_the_recorded_observation_are_rendered(observation, block):
    assert "NWS  age" in block
    assert " station               : KNYC" in block
    assert observation.observed_at in block
    assert f"{observation.temp_c:+.1f} C" in block


def test_null_fields_render_as_an_em_dash_not_zero():
    o = W.WeatherObservation(source="metar", observed_at="2026-09-06T11:00:00Z", station="KNYC", temp_c=None, wind_mps=None)
    text = D.weather_section(o, W.parse_iso8601("2026-09-06T11:10:00Z"))
    joined = "\n".join(text)
    assert f"temperature           : {D.NONE_TEXT}" in joined
    assert f"wind                  : {D.NONE_TEXT}" in joined
    assert f"visibility            : {D.NONE_TEXT}" in joined
    assert "0.0" not in joined.split("precipitation")[0]


def test_stale_data_is_marked_in_the_header_and_every_line():
    o = W.WeatherObservation(source="stale", observed_at="2026-09-06T05:00:00Z", station="KNYC", temp_c=10.0, stale_age_s=23000.0)
    lines = D.weather_section(o, W.parse_iso8601("2026-09-06T11:24:40Z"))
    assert "** STALE **" in lines[1]
    assert "6h 24m 40s" in lines[1]
    assert all(ln.startswith("!") for ln in lines[1:])


def test_a_live_but_very_old_observation_is_also_marked():
    o = W.WeatherObservation(source="nws", observed_at="2026-09-06T05:00:00Z", station="KNYC", temp_c=10.0, stale_age_s=23000.0)
    assert "** STALE **" in D.weather_section(o, W.parse_iso8601("2026-09-06T11:24:40Z"))[1]


def test_fresh_data_is_not_marked(observation):
    lines = D.weather_section(observation, W.parse_iso8601(observation.observed_at) + 600)
    assert "STALE" not in lines[1]
    assert all(ln.startswith((" ", "=")) for ln in lines)


def test_open_breakers_are_marked():
    lines = D.providers_section({"nws": "open(240s)", "open_meteo": "closed", "metar": "half_open"})
    assert any(ln.startswith("!") and "nws" in ln for ln in lines)
    assert all(not ln.startswith("!") for ln in lines if "open_meteo" in ln or "metar" in ln)
    assert D.providers_section(None)[-1].endswith(D.NONE_TEXT)


def test_time_section_matches_the_simtime():
    t = T.sim_time(UTC)
    lines = "\n".join(D.time_section(t))
    assert "2026-09-06 11:24:40Z" in lines
    assert "2026-09-06 07:24:40 EDT" in lines
    assert "-4 h  dst=yes" in lines
    assert f"{t.jd:.6f}" in lines and f"{t.delta_t_s:.3f} s" in lines


def test_sun_and_moon_sections_are_numeric():
    sun = A.solar_position(UTC, A.CENTRAL_PARK)
    events = A.sun_events_local(dt.date(2026, 9, 6), A.CENTRAL_PARK)
    lines = "\n".join(D.sun_section(sun, events))
    assert f"{sun.azimuth:.4f} deg" in lines and D.compass_point(sun.azimuth) in lines
    assert "sunrise / transit" in lines and "sunset" in lines
    moon = A.moon_position(UTC, A.CENTRAL_PARK)
    mlines = "\n".join(D.moon_section(moon))
    assert moon.phase_name in mlines
    assert ("waxing" if moon.waxing else "waning") in mlines


def test_esb_and_tides_sections():
    e = "\n".join(D.esb_section(json.loads(_esb_doc())))
    assert "Red, White, Blue" in e and "(230,20,20)" in e and "In Honor of Labor Day" in e
    assert D.esb_section(None)[-1].endswith(D.NONE_TEXT)
    t = "\n".join(D.tides_section(json.loads(_tides_doc())))
    assert "0.210 m NAVD88" in t and "1.056 m MLLW" in t
    assert "1.419 m/s WSW [ebb]" in t
    assert "next L" in t
    stale = D.tides_section(dict(json.loads(_tides_doc()), stale=True, errors=["water_level: 503"]))
    assert all(ln.startswith(("!", "=")) for ln in stale)


def test_world_section_reports_every_derived_quantity(observation, tmp_path):
    m = WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    w = m.update(observation, 0.0)
    lines = "\n".join(D.world_section(w))
    for lbl in ("wetness", "puddles", "road ice", "snow cover", "snow melting", "plow / salt", "fog density",
                "extinction", "wind vector ENU", "wind vector UE", "umbrella prob.", "window condensation", "missing fields"):
        assert f" {lbl:<{D.LABEL_W}}: " in lines, lbl


# --------------------------------------------------------------------------- whole block
def test_block_is_stable_and_never_wider_than_the_canvas(block):
    lines = block.splitlines()
    assert lines[-1] == "=" * D.WIDTH
    assert len(lines) > 50
    for ln in lines:
        assert len(ln) <= 110, ln  # a monospace canvas line budget; raw METAR is the longest field


def test_block_is_deterministic(observation, tmp_path):
    m = WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    w = m.update(observation, 0.0)
    t = T.sim_time(UTC)
    a = D.render(t, observation, w)
    b = D.render(t, observation, w)
    assert a == b


def test_render_computes_sun_and_moon_when_not_supplied(observation):
    text = D.render(T.sim_time(UTC), observation)
    assert D.header("SUN (NREL SPA)") in text and D.header("MOON (Meeus 47/48)") in text
    assert D.header("WORLD MAPPING") not in text  # omitted when no world state is passed


def test_write_is_atomic(tmp_path, block):
    p = tmp_path / "overlay.txt"
    D.write(block, p)
    assert p.read_text(encoding="utf-8") == block
    assert not (tmp_path / "overlay.txt.tmp").exists()
    D.write("shorter\n", p)
    assert p.read_text(encoding="utf-8") == "shorter\n"


def test_recorded_live_overlay_still_renders_the_same_shape():
    """The overlay written by the live verification run (data/processed/live/overlay.txt) must keep the
    same section order and header widths as the code produces today."""
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[2] / "data" / "processed" / "live" / "overlay.txt"
    if not path.exists():
        pytest.skip("no live overlay recorded in this checkout")
    recorded = path.read_text(encoding="utf-8").splitlines()
    headers = [ln for ln in recorded if ln.startswith("== ")]
    assert [h.split()[1] for h in headers] == ["TIME", "SUN", "MOON", "WEATHER", "WORLD", "PROVIDERS", "ESB", "TIDES"]
    assert all(len(h) == D.WIDTH for h in headers)
