"""World mapping: every formula, the exact ODE integrators and the persisted state."""
from __future__ import annotations

import json
import math

import pytest

from nycsim_live import worldmapping as WM
from nycsim_live.weather import WeatherObservation


def obs(**kw) -> WeatherObservation:
    base = dict(source="nws", observed_at="2026-09-05T18:51:00Z", temp_c=15.0, dewpoint_c=8.0, rh=63.0,
                wind_mps=3.0, wind_from_heading=270.0, wind_to_heading=90.0, wind_dir_deg=180.0,
                cloud_cover=0.3, visibility_m=16090.0, pressure_hpa=1013.0)
    base.update(kw)
    return WeatherObservation(**base)


# --------------------------------------------------------------------------- integrator
def test_lag_is_the_exact_first_order_solution():
    assert WM.lag(0.0, 1.0, 0.0, 100.0) == 0.0
    assert WM.lag(0.0, 1.0, 100.0, 100.0) == pytest.approx(1.0 - math.exp(-1.0))
    assert WM.lag(1.0, 0.0, 100.0, 100.0) == pytest.approx(math.exp(-1.0))
    # cadence independence: one 600 s step == ten 60 s steps
    one = WM.lag(0.0, 1.0, 600.0, 300.0)
    x = 0.0
    for _ in range(10):
        x = WM.lag(x, 1.0, 60.0, 300.0)
    assert one == pytest.approx(x, rel=1e-12)
    assert WM.lag(0.3, 0.9, 10.0, 0.0) == 0.9  # tau 0 -> jump to the target


# --------------------------------------------------------------------------- wetness
def test_wetness_target_from_precipitation():
    assert WM.wetness_target(obs(precip_type="none", precip_rate_mmph=0.0)) == 0.0
    assert WM.wetness_target(obs(precip_type="rain", precip_rate_mmph=0.01)) == pytest.approx(WM.WET_ONSET, abs=0.01)
    assert WM.wetness_target(obs(precip_type="rain", precip_rate_mmph=WM.WET_SATURATION_MMPH)) == pytest.approx(1.0)
    assert WM.wetness_target(obs(precip_type="rain", precip_rate_mmph=50.0)) == 1.0
    half = WM.wetness_target(obs(precip_type="rain", precip_rate_mmph=WM.WET_SATURATION_MMPH / 2))
    assert half == pytest.approx(WM.WET_ONSET + (1 - WM.WET_ONSET) * 0.5)


def test_wetness_target_frozen_precipitation():
    cold = obs(precip_type="snow", precip_rate_mmph=2.5, temp_c=-5.0, rh=80.0)
    assert WM.wetness_target(cold) == 0.0  # dry snow on a frozen surface leaves no film
    warm = obs(precip_type="snow", precip_rate_mmph=2.5, temp_c=2.0, rh=80.0)
    assert WM.wetness_target(warm) == pytest.approx(WM.SNOW_WET_FRACTION)


def test_wetness_target_fog_and_dew():
    fog = obs(precip_type="none", precip_rate_mmph=0.0, visibility_m=200.0, obscuration=["FG"], rh=99.0)
    assert WM.wetness_target(fog) == pytest.approx(WM.FOG_WETNESS)
    dew = obs(precip_type="none", precip_rate_mmph=0.0, rh=98.0, visibility_m=16090.0)
    assert WM.wetness_target(dew) == pytest.approx(WM.DEW_WETNESS)
    dry = obs(precip_type="none", precip_rate_mmph=0.0, rh=96.9, visibility_m=16090.0)
    assert WM.wetness_target(dry) == 0.0


def test_tau_wet_shrinks_with_rate():
    assert WM.tau_wet_s(0.0) == pytest.approx(WM.TAU_WET_BASE_S)
    assert WM.tau_wet_s(2.0) == pytest.approx(WM.TAU_WET_BASE_S / 2.0)
    assert WM.tau_wet_s(1000.0) == WM.TAU_WET_MIN_S


def test_tau_dry_reference_state_and_monotonicity():
    ref = WM.tau_dry_s(20.0, 50.0, 0.0, 0.0)
    assert ref == pytest.approx(WM.TAU_DRY_BASE_S)
    assert WM.tau_dry_s(20.0, 20.0, 0.0, 0.0) < ref  # drier air dries faster
    assert WM.tau_dry_s(20.0, 50.0, 6.0, 0.0) < ref  # wind dries faster
    assert WM.tau_dry_s(30.0, 50.0, 0.0, 0.0) == pytest.approx(ref / 2.0)  # +10 K doubles evaporation
    assert WM.tau_dry_s(20.0, 50.0, 0.0, 1.0) == pytest.approx(ref / 2.5)  # full sun
    assert WM.tau_dry_s(-5.0, 50.0, 0.0, 0.0) > WM.tau_dry_s(0.1, 50.0, 0.0, 0.0)  # freezing slows it
    assert WM.tau_dry_s(100.0, 1.0, 40.0, 1.0) == WM.TAU_DRY_MIN_S
    assert WM.tau_dry_s(-60.0, 100.0, 0.0, 0.0) == WM.TAU_DRY_MAX_S
    assert WM.tau_dry_s(20.0, None, 0.0, 0.0) == pytest.approx(ref)  # unknown RH -> reference


def test_solar_factor():
    assert WM.solar_factor(None, 0.0) == 0.0
    assert WM.solar_factor(-5.0, 0.0) == 0.0
    assert WM.solar_factor(90.0, 0.0) == pytest.approx(1.0)
    assert WM.solar_factor(90.0, 1.0) == pytest.approx(0.3)
    assert WM.solar_factor(30.0, 0.0) == pytest.approx(0.5)


def test_wetness_rises_in_rain_and_dries_afterwards(tmp_path):
    m = WM.WorldMapper(tmp_path / "world.json", clock=lambda: 0.0)
    rain = obs(precip_type="rain", precip_rate_mmph=5.0)
    m.update(rain, 0.0)
    assert m.state.wetness == 0.0  # the first update only seeds the clock
    m.update(rain, 600.0)
    assert m.state.wetness > 0.9 and m.state.drying is False
    dry = obs(precip_type="none", precip_rate_mmph=0.0, rh=40.0, temp_c=25.0, wind_mps=5.0)
    s = m.update(dry, 600.0 + 6 * 3600.0)
    assert s.drying is True and 0.0 <= s.wetness < 0.05
    assert s.tau_used_s == pytest.approx(WM.tau_dry_s(25.0, 40.0, 5.0, 0.0))


def test_wetness_state_survives_a_restart(tmp_path):
    p = tmp_path / "world.json"
    m = WM.WorldMapper(p, clock=lambda: 0.0)
    m.update(obs(precip_type="rain", precip_rate_mmph=5.0), 0.0)
    m.update(obs(precip_type="rain", precip_rate_mmph=5.0), 900.0)
    saved = m.state.wetness
    m2 = WM.WorldMapper(p, clock=lambda: 900.0)
    assert m2.wetness == pytest.approx(round(saved, 4))
    assert m2.last_update == 900.0


def test_corrupt_state_file_starts_dry(tmp_path):
    p = tmp_path / "world.json"
    p.write_text('{"wetness": "soaking"}')
    m = WM.WorldMapper(p, clock=lambda: 0.0)
    assert m.wetness == 0.0 and m.puddle == 0.0


# --------------------------------------------------------------------------- puddles
def test_puddles_need_a_saturated_surface_and_a_rate_above_the_drain(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    light = obs(precip_type="rain", precip_rate_mmph=1.0)  # below DRAIN_MMPH
    m.update(light, 0.0)
    m.update(light, 7200.0)
    assert m.state.wetness > 0.5 and m.state.puddle_level == 0.0
    heavy = obs(precip_type="rain", precip_rate_mmph=9.5)  # 8 mm/h above the drain -> full in 1 h
    m.update(heavy, 7200.0 + 60.0)
    m.update(heavy, 7200.0 + 3660.0)
    assert m.state.puddle_level == pytest.approx(1.0)
    assert m.state.puddle_depth_mm == pytest.approx(WM.PUDDLE_FULL_MM)


def test_puddles_drain_when_the_rain_stops(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    m.puddle, m.wetness, m.last_update = 1.0, 1.0, 0.0
    m.update(obs(precip_type="none", precip_rate_mmph=0.0), 1800.0)
    assert m.state.puddle_level < 0.9
    m.update(obs(precip_type="none", precip_rate_mmph=0.0), 1800.0 + 6 * 3600.0)
    assert m.state.puddle_level == 0.0


def test_road_ice_needs_water_and_freezing_temperatures(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    m.wetness, m.last_update = 0.6, 0.0
    assert m.update(obs(temp_c=-1.0, precip_type="none", precip_rate_mmph=0.0), 1.0).road_ice is True
    m.wetness = 0.6
    assert m.update(obs(temp_c=3.0, precip_type="none", precip_rate_mmph=0.0), 2.0).road_ice is False


# --------------------------------------------------------------------------- snow
def test_snow_cover_follows_the_depth_model(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    s = m.update(obs(temp_c=-3.0, precip_type="snow", precip_rate_mmph=1.0, snow_depth_cm=1.0, snow_depth_source="observed"), 0.0)
    assert s.snow_cover == pytest.approx(0.5)
    s = m.update(obs(temp_c=-3.0, precip_type="snow", precip_rate_mmph=1.0, snow_depth_cm=4.0, snow_depth_source="observed"), 3600.0)
    assert s.snow_cover == pytest.approx(1.0)


def test_snow_cover_melts_only_above_one_degree(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    m.snow_cover = m.snow_cover_road = 1.0
    m.last_update = 0.0
    cold = obs(temp_c=0.5, precip_type="none", precip_rate_mmph=0.0, snow_depth_cm=10.0, snow_depth_source="model")
    assert m.update(cold, 3600.0).snow_cover == pytest.approx(1.0)
    warm = obs(temp_c=11.0, precip_type="none", precip_rate_mmph=0.0, snow_depth_cm=10.0, snow_depth_source="model")
    s = m.update(warm, 7200.0)
    assert s.snow_cover == pytest.approx(1.0 - WM.SNOW_MELT_CM_PER_H_PER_C * 10.0 / WM.SNOW_FULL_COVER_CM)
    assert s.snow_melting is True


def test_road_is_cleared_faster_than_the_ground(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    m.snow_cover = m.snow_cover_road = 1.0
    m.last_update = 0.0
    lying = obs(temp_c=-2.0, precip_type="none", precip_rate_mmph=0.0, snow_depth_cm=8.0, snow_depth_source="model")
    s = m.update(lying, 1800.0)
    assert s.plow_active is True and s.salt_active is True
    assert s.snow_cover == pytest.approx(1.0)
    assert s.snow_cover_road == pytest.approx(1.0 - 0.5 * (WM.ROAD_CLEAR_TRAFFIC_PER_H + WM.ROAD_CLEAR_PLOW_PER_H + WM.ROAD_CLEAR_SALT_PER_H))
    s = m.update(lying, 3600.0 + 1800.0)  # a further hour with the full response leaves the road bare
    assert s.snow_cover_road == 0.0 and s.snow_cover == pytest.approx(1.0)


@pytest.mark.parametrize(
    "depth,temp,kind,plow,salt",
    [(0.0, 5.0, "none", False, False),
     (0.0, -2.0, "snow", False, True),
     (2.0, -2.0, "snow", False, True),
     (5.08, -2.0, "snow", True, True),
     (10.0, -2.0, "none", True, True),
     (10.0, 6.0, "none", False, False),
     (0.0, 3.0, "freezing_rain", False, True)],
)
def test_plow_and_salt_thresholds(depth, temp, kind, plow, salt):
    assert WM.plow_and_salt(depth, temp, kind) == (plow, salt)


def test_plow_threshold_is_two_inches():
    assert WM.PLOW_THRESHOLD_CM == pytest.approx(2.0 * 2.54)


# --------------------------------------------------------------------------- fog
@pytest.mark.parametrize("vis,density", [(None, 0.0), (0.0, 0.0), (20000.0, 0.0), (10000.0, 0.0), (50.0, 1.0), (10.0, 1.0)])
def test_fog_density_edges(vis, density):
    assert WM.fog_density_from_visibility(vis) == pytest.approx(density)


def test_fog_density_is_logarithmic():
    mid = math.sqrt(WM.FOG_VIS_CLEAR_M * WM.FOG_VIS_DENSE_M)  # 707 m
    assert WM.fog_density_from_visibility(mid) == pytest.approx(0.5, abs=1e-6)
    assert WM.fog_density_from_visibility(1000.0) == pytest.approx(math.log(10.0) / math.log(200.0), abs=1e-9)


def test_extinction_is_koschmieder():
    assert WM.extinction_per_m(1000.0) == pytest.approx(0.003912)
    assert WM.extinction_per_m(None) == 0.0
    assert WM.extinction_per_m(16090.0) == pytest.approx(WM.KOSCHMIEDER_K / 16090.0)


def test_fog_versus_haze_attribution(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    f = m.update(obs(visibility_m=500.0, obscuration=["FG"], precip_type="none", precip_rate_mmph=0.0), 0.0)
    assert f.fog_density > 0.5 and f.haze_density == 0.0
    h = m.update(obs(visibility_m=500.0, obscuration=["HZ"], rh=60.0, precip_type="none", precip_rate_mmph=0.0), 1.0)
    assert h.haze_density > 0.5 and h.fog_density == 0.0
    both = m.update(obs(visibility_m=500.0, obscuration=["HZ", "BR"], precip_type="none", precip_rate_mmph=0.0), 2.0)
    assert both.fog_density > 0.5 and both.haze_density == 0.0
    rain = m.update(obs(visibility_m=800.0, obscuration=[], rh=90.0, precip_type="rain", precip_rate_mmph=20.0), 3.0)
    assert rain.fog_density > 0.0  # heavy precipitation without a group still thickens the fog volume


# --------------------------------------------------------------------------- wind
@pytest.mark.parametrize(
    "from_heading,east,north",
    [(0.0, 0.0, -1.0), (90.0, -1.0, 0.0), (180.0, 0.0, 1.0), (270.0, 1.0, 0.0)],
)
def test_wind_vector_directions(from_heading, east, north):
    enu, ue = WM.wind_vectors(10.0, from_heading)
    assert enu[0] == pytest.approx(10.0 * east, abs=1e-9)
    assert enu[1] == pytest.approx(10.0 * north, abs=1e-9)
    assert enu[2] == 0.0
    assert ue == [pytest.approx(enu[0]), pytest.approx(-enu[1]), 0.0]  # UE.Y = -north


def test_wind_vector_magnitude_and_missing_direction():
    enu, _ = WM.wind_vectors(7.5, 215.0)
    assert math.hypot(enu[0], enu[1]) == pytest.approx(7.5)
    assert WM.wind_vectors(None, 90.0) == ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    assert WM.wind_vectors(5.0, None) == ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])


# --------------------------------------------------------------------------- umbrellas
def test_umbrella_probability_curve():
    assert WM.umbrella_probability("none", 0.0, 0.0) == 0.0
    assert WM.umbrella_probability("rain", 0.0, 0.0) == 0.0
    p1 = WM.umbrella_probability("rain", WM.UMBRELLA_RATE_SCALE_MMPH, 0.0)
    assert p1 == pytest.approx(WM.UMBRELLA_MAX * (1 - math.exp(-1.0)))
    assert WM.umbrella_probability("rain", 100.0, 0.0) == pytest.approx(WM.UMBRELLA_MAX)
    assert WM.umbrella_probability("snow", 5.0, 0.0) == pytest.approx(WM.umbrella_probability("rain", 5.0, 0.0) * 0.35, rel=1e-9)
    assert WM.umbrella_probability("drizzle", 5.0, 0.0) < WM.umbrella_probability("rain", 5.0, 0.0)


def test_umbrella_probability_collapses_in_strong_wind():
    calm = WM.umbrella_probability("rain", 5.0, 0.0)
    assert WM.umbrella_probability("rain", 5.0, WM.UMBRELLA_WIND_KNEE_MPS) == pytest.approx(calm)
    mid = WM.umbrella_probability("rain", 5.0, 12.5)
    assert calm > mid > WM.umbrella_probability("rain", 5.0, WM.UMBRELLA_WIND_ZERO_MPS)
    assert WM.umbrella_probability("rain", 5.0, 40.0) == pytest.approx(calm * WM.UMBRELLA_WIND_MIN)


# --------------------------------------------------------------------------- glass
def test_window_condensation_single_versus_double_glazing():
    assert WM.window_condensation(None, None) == (0.0, 0.0)
    assert WM.window_condensation(15.0, 10.0)[0] == 0.0
    # single glazing fogs near freezing, a sealed double unit does not
    single_in, _ = WM.window_condensation(0.0, -2.0, WM.R_TOTAL_SINGLE)
    double_in, _ = WM.window_condensation(0.0, -2.0, WM.R_TOTAL_DOUBLE)
    assert 0.0 < single_in <= 1.0 and double_in == 0.0
    assert WM.window_condensation(-20.0, -25.0, WM.R_TOTAL_SINGLE)[0] == 1.0


def test_window_condensation_matches_the_surface_temperature_formula():
    from nycsim_live.weather import dewpoint_from_rh

    t_out = -2.0
    t_si = WM.INDOOR_TEMP_C - (WM.R_SI / WM.R_TOTAL_SINGLE) * (WM.INDOOR_TEMP_C - t_out)
    td_in = dewpoint_from_rh(WM.INDOOR_TEMP_C, WM.INDOOR_RH)
    expected = min(1.0, max(0.0, (td_in - t_si) / WM.CONDENSATION_FULL_C))
    assert WM.window_condensation(t_out, -5.0, WM.R_TOTAL_SINGLE)[0] == pytest.approx(expected)


def test_exterior_condensation_needs_a_muggy_night_and_a_cooled_building():
    assert WM.window_condensation(30.0, 20.0)[1] == 0.0  # dry-ish air: no exterior condensation
    _, ext = WM.window_condensation(28.0, 27.5, WM.R_TOTAL_SINGLE)
    assert ext > 0.0
    assert WM.window_condensation(20.0, 19.9)[1] == 0.0  # below the AC threshold


def test_glazing_resistances_reproduce_the_published_u_values():
    assert 1.0 / WM.R_TOTAL_SINGLE == pytest.approx(5.75, abs=0.05)
    assert 1.0 / WM.R_TOTAL_DOUBLE == pytest.approx(2.78, abs=0.05)


# --------------------------------------------------------------------------- state document
def test_world_state_document_is_complete_and_rounded(tmp_path):
    p = tmp_path / "world.json"
    m = WM.WorldMapper(p, clock=lambda: 0.0)
    m.update(obs(precip_type="rain", precip_rate_mmph=3.0, stale_age_s=120.0), 0.0)
    s = m.update(obs(precip_type="rain", precip_rate_mmph=3.0, stale_age_s=180.0), 300.0)
    d = json.loads(p.read_text())
    assert d["schema_version"] == WM.SCHEMA_VERSION
    assert set(d) == set(s.to_json_dict())
    assert d["source"] == "nws" and d["observation_age_s"] == 180.0
    assert d["wind_vector_enu"][0] == pytest.approx(3.0)  # wind from 270 -> blowing east
    assert all(isinstance(v, (int, float, bool, str, list, type(None))) for v in d.values())


def test_missing_fields_are_listed_not_faked(tmp_path):
    m = WM.WorldMapper(tmp_path / "w.json", clock=lambda: 0.0)
    s = m.update(WeatherObservation(source="stale"), 0.0)
    assert set(s.missing) == {"temp_c", "dewpoint_c", "rh", "wind_mps", "wind_dir_deg", "cloud_cover", "visibility_m"}
    assert s.wetness == 0.0 and s.fog_density == 0.0 and s.extinction_per_m == 0.0
    assert s.wind_speed_mps == 0.0 and s.wind_from_heading is None
    assert s.window_condensation == 0.0 and s.umbrella_probability == 0.0
