"""Tests for the traffic calibration stage (DATA_CONTRACTS §10 and the §15 ``runtime/density.nycb``).

Three groups:

* **unit** — the speed model, the profile estimator, the regression, the NYCB record layouts and the
  fleet-mix document.  These run without any built artefact.
* **coverage / value range** — ``density.parquet`` covers every 2020 NTA × 24 h × 3 day types exactly
  once, has no NaNs, every share is in [0, 1] and the four shares sum to at most 1.
* **monotonic sanity** — Midtown at 17:00 above Midtown at 04:00 and above Tottenville at 17:00, plus
  the same ordering for pedestrians, a peak-vs-night ordering for every borough, and for-hire shares
  that fall from Manhattan to Staten Island.

The data-dependent groups skip when the stage has not been run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import pytest

from nycsim_pipeline.paths import PROCESSED
from nycsim_pipeline.traffic import DAY_TYPES, HOURS, N_NTA_EXPECTED, SCHEMA_NAME
from nycsim_pipeline.traffic import fleet_mix as FM
from nycsim_pipeline.traffic import model as M
from nycsim_pipeline.traffic import runtime_export as RX
from nycsim_pipeline.traffic import speed as SP
from nycsim_pipeline.traffic import shares as SH
from nycsim_pipeline.traffic.build import CONTRACT_COLUMNS
from nycsim_pipeline.traffic.counts import us_holidays
from nycsim_pipeline.traffic.segments import normalize_street

DENSITY = PROCESSED / "traffic" / "density.parquet"
DETAIL = PROCESSED / "traffic" / "density_detail.parquet"
FLEET = PROCESSED / "traffic" / "fleet_mix.json"
SUMMARY = PROCESSED / "traffic" / "build_summary.json"
NYCB = PROCESSED / "runtime" / "density.nycb"

SHARE_COLUMNS = ["taxi_share", "truck_share", "bus_share", "bike_share"]
MIDTOWN = "MN0502"          # Midtown-Times Square
MIDTOWN_SOUTH = "MN0501"    # Midtown South-Flatiron-Union Square
TOTTENVILLE = "SI0305"      # Tottenville-Charleston


# ----------------------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def density() -> pl.DataFrame:
    if not DENSITY.exists():
        pytest.skip(f"{DENSITY} not built — run `python -m nycsim_pipeline.traffic.build`")
    return pl.read_parquet(DENSITY)


@pytest.fixture(scope="module")
def detail() -> pl.DataFrame:
    if not DETAIL.exists():
        pytest.skip(f"{DETAIL} not built")
    return pl.read_parquet(DETAIL)


@pytest.fixture(scope="module")
def summary() -> dict:
    if not SUMMARY.exists():
        pytest.skip(f"{SUMMARY} not built")
    return json.loads(SUMMARY.read_text())


@pytest.fixture(scope="module")
def fleet() -> dict:
    if not FLEET.exists():
        pytest.skip(f"{FLEET} not built")
    return json.loads(FLEET.read_text())


def _cell(df: pl.DataFrame, code: str, hour: int, dow: int, col: str) -> float:
    sub = df.filter((pl.col("nta_code") == code) & (pl.col("hour") == hour) & (pl.col("dow") == dow))
    assert sub.height == 1, f"{code} {hour} {dow}: {sub.height} rows"
    return float(sub[col][0])


# ----------------------------------------------------------------------------- unit: speed model
def test_speed_falls_from_free_flow_to_capacity_speed():
    cls = np.array([0, 1, 2, 3, 4], dtype=np.int8)
    posted = np.full(5, 40.0)
    vf = SP.free_flow_kmh(cls, posted)
    qc = SP.capacity(cls)
    vc = SP.speed_at_capacity_kmh(cls, vf)
    assert np.all(vc < vf) and np.all(vc > 0)
    assert np.allclose(SP.speed_of_flow(np.zeros(5), vf, vc, qc), vf)
    assert np.allclose(SP.speed_of_flow(qc, vf, vc, qc), vc)
    # beyond capacity the speed stays at the capacity speed (the model has no congested branch)
    assert np.allclose(SP.speed_of_flow(qc * 3, vf, vc, qc), vc)
    # monotonically decreasing in flow
    for q in (0.0, 100.0, 400.0, 900.0, 2000.0):
        assert np.all(SP.speed_of_flow(np.full(5, q), vf, vc, qc)
                      >= SP.speed_of_flow(np.full(5, q + 50.0), vf, vc, qc) - 1e-12)


def test_density_of_flow_is_monotonic_and_capped():
    cls = np.array([2], dtype=np.int8)
    vf = SP.free_flow_kmh(cls, np.array([40.0]))
    qc = SP.capacity(cls)
    vc = SP.speed_at_capacity_kmh(cls, vf)
    q = np.linspace(0, 5000, 300)
    k = SP.density_of_flow(q, vf, vc, qc)
    assert k[0] == 0.0
    assert np.all(np.diff(k) >= -1e-9)
    assert k.max() <= SP.K_JAM + 1e-9
    # k = q / v at a flow well below capacity
    assert math.isclose(float(SP.density_of_flow(np.array([300.0]), vf, vc, qc)[0]),
                        300.0 / float(SP.speed_of_flow(np.array([300.0]), vf, vc, qc)[0]), rel_tol=1e-9)


def test_free_flow_speeds_are_the_documented_ones():
    cls = np.array([0, 1, 2, 3, 4], dtype=np.int8)
    vf = SP.free_flow_kmh(cls, np.full(5, 40.234))     # 25 mph
    assert math.isclose(vf[0], 88.5, rel_tol=1e-9)     # freeway 55 mph
    assert math.isclose(vf[1], 48.3, rel_tol=1e-9)     # ramp 30 mph
    assert 24.0 < vf[2] < 26.0                          # arterial 0.62 x posted
    assert 23.0 < vf[3] < 25.0
    assert 22.0 < vf[4] < 24.0
    k_cap = SP.capacity(cls) / SP.speed_at_capacity_kmh(cls, vf)
    assert 40 < k_cap[0] < 50                           # HCM: 45 veh/km/lane at freeway capacity
    assert np.all(k_cap < SP.K_JAM)


def test_road_class_assignment():
    rw = np.array([1, 1, 2, 9, 1, 3])
    lanes = np.array([1, 4, 3, 1, 2, 4])
    trafdir = np.array(["TF", "TW", "TW", "FT", "TW", "TW"])
    truck = np.array([False, False, False, False, True, False])
    c = SP.road_class(rw, lanes, trafdir, truck)
    assert c.tolist() == [4, 2, 0, 1, 2, 2]


# ----------------------------------------------------------------------------- unit: regression
def test_weighted_ridge_recovers_a_known_linear_model():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(400, 3))
    y = 2.0 + 1.5 * X[:, 0] - 0.75 * X[:, 1] + rng.normal(scale=0.05, size=400)
    reg = M.fit_regression(X, y, np.ones(400), ["a", "b", "c"], ridge=1e-6)
    pred = reg.predict(X)
    assert reg.r2 > 0.99
    assert reg.r2_loo > 0.99
    assert abs(float(np.corrcoef(pred, y)[0, 1]) - 1.0) < 0.01
    assert reg.n == 400 and reg.rmse < 0.1
    d = reg.as_dict()
    assert d["features"] == ["a", "b", "c"] and len(d["beta"]) == 4


def test_regression_rejects_non_finite_input():
    X = np.zeros((10, 2))
    X[0, 0] = np.nan
    with pytest.raises(ValueError):
        M.fit_regression(X, np.zeros(10), np.ones(10), ["a", "b"])
    with pytest.raises(ValueError):
        M.fit_regression(np.zeros((10, 2)), np.zeros(10), np.ones(10), ["a"])


def test_profile_estimator_is_not_dominated_by_a_quiet_site():
    # two sites: a busy one with a flat profile, a very quiet one that doubles at hour 5.
    q = np.full((2, 24, 3), np.nan)
    q[0] = 100.0
    q[1] = 0.5
    q[1, 5, :] = 5.0
    level = np.array([100.0, 0.6875])
    w = np.ones(2)
    p = M._weighted_profile(q, level, w)
    assert 0.9 < p[0, 0] < 1.1
    assert p[5, 0] < 1.15, "one quiet site must not multiply the pooled hour"


def test_segment_features_shape_and_names():
    X, names = M.segment_features(np.array([1, 2]), np.array([2, 4]), np.array(["TW", "FT"]),
                                  np.array([25, 50]), np.array([30.0, np.nan]), np.array([False, True]),
                                  ["W 34 ST", "QUEENS BLVD"])
    assert X.shape == (2, len(names))
    assert np.isfinite(X).all()
    assert names[0] == "log_travel_lanes" and "is_avenue" in names


# ----------------------------------------------------------------------------- unit: helpers
def test_street_normalisation():
    assert normalize_street("EAST 34TH STREET") == "E 34 ST"
    assert normalize_street("Queens Boulevard") == "QUEENS BLVD"
    assert normalize_street(None) == ""


def test_holidays_are_observed_dates():
    h = us_holidays(2025)
    import datetime as dt
    assert dt.date(2025, 7, 4) in h            # Independence Day, a Friday
    assert dt.date(2025, 11, 27) in h          # Thanksgiving
    assert dt.date(2025, 11, 28) in h          # the Friday after
    assert dt.date(2025, 6, 19) in h           # Juneteenth (from 2021)
    assert dt.date(2025, 3, 14) not in h


def test_nycb_record_layouts_match_the_cpp_reader():
    assert RX.CELL_DTYPE.itemsize == 32
    assert RX.POLY_DTYPE.itemsize == 12
    assert RX.VERTEX_DTYPE.itemsize == 12
    off = {n: RX.CELL_DTYPE.fields[n][1] for n in RX.CELL_DTYPE.names}
    assert off == {"nta_str": 0, "hour": 4, "dow": 5, "pad": 6, "veh_per_km_lane": 8, "ped_per_m2": 12,
                   "taxi_share": 16, "truck_share": 20, "bus_share": 24, "bike_share": 28}


# ----------------------------------------------------------------------------- coverage & ranges
def test_schema_and_metadata(density: pl.DataFrame):
    assert list(density.columns) == CONTRACT_COLUMNS
    meta = pq.read_schema(DENSITY).metadata or {}
    assert meta.get(b"nycsim.schema", b"").decode() == SCHEMA_NAME
    assert density.schema["nta_code"] == pl.Utf8
    for c in ["veh_per_km_lane", "ped_per_m2_sidewalk", *SHARE_COLUMNS]:
        assert density.schema[c] in (pl.Float64, pl.Float32), c


def test_full_coverage_every_nta_hour_daytype(density: pl.DataFrame):
    assert density.height == N_NTA_EXPECTED * HOURS * DAY_TYPES == 18864
    assert density["nta_code"].n_unique() == N_NTA_EXPECTED
    keys = density.select(["nta_code", "hour", "dow"])
    assert keys.unique().height == density.height
    per_nta = density.group_by("nta_code").agg(pl.len().alias("n"))
    assert per_nta["n"].min() == per_nta["n"].max() == HOURS * DAY_TYPES
    assert sorted(density["hour"].unique().to_list()) == list(range(HOURS))
    assert sorted(density["dow"].unique().to_list()) == list(range(DAY_TYPES))


def test_no_nans_anywhere(density: pl.DataFrame):
    for c in density.columns:
        assert density[c].null_count() == 0, c
    for c in ["veh_per_km_lane", "ped_per_m2_sidewalk", *SHARE_COLUMNS]:
        v = density[c].to_numpy()
        assert np.isfinite(v).all(), c


def test_value_ranges(density: pl.DataFrame):
    veh = density["veh_per_km_lane"].to_numpy()
    assert veh.min() >= 0.0
    assert veh.max() <= SP.K_JAM
    ped = density["ped_per_m2_sidewalk"].to_numpy()
    assert ped.min() >= 0.0
    assert ped.max() <= 6.0, "6 ped/m² is Fruin LOS F; an NTA average must be far below it"
    for c in SHARE_COLUMNS:
        v = density[c].to_numpy()
        assert v.min() >= 0.0 and v.max() <= 1.0, c


def test_shares_sum_to_at_most_one(density: pl.DataFrame):
    tot = np.sum([density[c].to_numpy() for c in SHARE_COLUMNS], axis=0)
    assert tot.max() <= 1.0 + 1e-9
    assert tot.min() >= 0.0


def test_source_column_is_a_known_tag(density: pl.DataFrame):
    allowed = {"atr_recent", "atr_mixed", "atr_older", "landuse_model", "no_roads"}
    assert set(density["source"].unique().to_list()) <= allowed
    # a source is a property of the NTA, so it is constant over its 72 cells
    per = density.group_by("nta_code").agg(pl.col("source").n_unique().alias("n"))
    assert per["n"].max() == 1


def test_ntas_without_roads_are_empty_and_flagged(density: pl.DataFrame):
    no_roads = density.filter(pl.col("source") == "no_roads")
    if no_roads.height:
        assert float(no_roads["veh_per_km_lane"].max()) == 0.0
    with_roads = density.filter(pl.col("source") != "no_roads")
    assert float(with_roads["veh_per_km_lane"].min()) > 0.0


# ----------------------------------------------------------------------------- monotonic sanity
def test_midtown_rush_hour_beats_midtown_at_night(density: pl.DataFrame):
    peak = _cell(density, MIDTOWN, 17, 0, "veh_per_km_lane")
    night = _cell(density, MIDTOWN, 4, 0, "veh_per_km_lane")
    assert peak > night
    assert peak > 3 * night, f"Midtown 17:00 {peak:.1f} vs 04:00 {night:.1f} is not a rush hour"


def test_midtown_rush_hour_beats_tottenville_rush_hour(density: pl.DataFrame):
    mid = _cell(density, MIDTOWN, 17, 0, "veh_per_km_lane")
    tot = _cell(density, TOTTENVILLE, 17, 0, "veh_per_km_lane")
    assert mid > tot
    assert mid > 3 * tot, f"Midtown {mid:.1f} vs Tottenville {tot:.1f}"


def test_pedestrian_density_follows_the_same_ordering(density: pl.DataFrame):
    mid = _cell(density, MIDTOWN_SOUTH, 13, 0, "ped_per_m2_sidewalk")
    mid_night = _cell(density, MIDTOWN_SOUTH, 4, 0, "ped_per_m2_sidewalk")
    tot = _cell(density, TOTTENVILLE, 13, 0, "ped_per_m2_sidewalk")
    assert mid > mid_night
    assert mid > 5 * tot, f"Midtown South {mid:.4f} vs Tottenville {tot:.4f} ped/m²"


def test_every_borough_is_busier_in_the_evening_peak_than_at_04(detail: pl.DataFrame):
    d = (detail.filter((pl.col("dow") == 0) & (pl.col("lane_km") > 0) & pl.col("hour").is_in([4, 17]))
         .group_by(["borough", "hour"])
         .agg(((pl.col("veh_per_km_lane") * pl.col("lane_km")).sum() / pl.col("lane_km").sum()).alias("k"))
         .pivot(on="hour", index="borough", values="k"))
    for row in d.iter_rows(named=True):
        assert row["17"] > row["4"], f"borough {row['borough']}: 17:00 {row['17']} <= 04:00 {row['4']}"


def test_manhattan_is_the_densest_borough_at_the_peak(detail: pl.DataFrame):
    d = (detail.filter((pl.col("dow") == 0) & (pl.col("hour") == 17) & (pl.col("lane_km") > 0))
         .group_by("borough")
         .agg(((pl.col("veh_per_km_lane") * pl.col("lane_km")).sum() / pl.col("lane_km").sum()).alias("k"))
         .sort("k", descending=True))
    assert int(d["borough"][0]) == 1
    assert int(d["borough"][-1]) == 5, "Staten Island should be the least dense borough"


def test_for_hire_share_decreases_from_manhattan_outward(detail: pl.DataFrame):
    d = (detail.filter((pl.col("dow") == 0) & (pl.col("hour") == 8))
         .group_by("borough").agg(pl.col("taxi_share").median().alias("s")).sort("borough"))
    s = {int(r["borough"]): float(r["s"]) for r in d.iter_rows(named=True)}
    assert s[1] > s[3] > s[5]
    assert s[1] > s[2] > s[5]
    assert s[5] < 0.05, "for-hire vehicles are a rounding error on Staten Island"


def test_weekend_night_is_busier_than_weekday_night_in_manhattan(detail: pl.DataFrame):
    def k(dow: int) -> float:
        sub = detail.filter((pl.col("dow") == dow) & (pl.col("hour") == 2) & (pl.col("borough") == 1)
                            & (pl.col("lane_km") > 0))
        return float((sub["veh_per_km_lane"] * sub["lane_km"]).sum() / sub["lane_km"].sum())
    assert k(1) > k(0), "02:00 on a Saturday must be busier than 02:00 on a weekday"


def test_speeds_are_lowest_when_density_is_highest(detail: pl.DataFrame):
    cbd = detail.filter(pl.col("is_cbd") & (pl.col("dow") == 0)).group_by("hour").agg(
        pl.col("veh_per_km_lane").mean().alias("k"), pl.col("speed_kmh").mean().alias("v")).sort("hour")
    k = cbd["k"].to_numpy()
    v = cbd["v"].to_numpy()
    assert float(np.corrcoef(k, v)[0, 1]) < -0.8
    assert 5.0 < v[k.argmax()] < 20.0, "Manhattan CBD peak-hour travel speed should be about 7 mph"


# ----------------------------------------------------------------------------- fleet mix
def test_fleet_mix_document(fleet: dict):
    FM.validate_fleet_mix(fleet)
    assert [c["name"] for c in fleet["classes"]] == list(FM.CLASSES)
    assert len(FM.CLASSES) == 18
    assert all(c["basis"] for c in fleet["classes"])
    assert all(c["fleet_vehicles"] > 0 for c in fleet["classes"])


def test_fleet_mix_covers_every_region_and_band(fleet: dict):
    seen = {(e["borough"], e["cbd"], e["band"]) for e in fleet["mix"]}
    assert len(seen) == len(FM.REGIONS) * len(FM.TIME_BANDS)
    hours = sorted(h for hs in fleet["time_bands"].values() for h in hs)
    assert hours == list(range(24))


def test_horse_carriages_and_pedicabs_only_in_manhattan(fleet: dict):
    for e in fleet["mix"]:
        if e["borough"] != 1:
            assert e["share"]["horse_carriage"] == 0.0, e["region"]
            assert e["share"]["pedicab"] == 0.0, e["region"]
    cbd_midday = next(e for e in fleet["mix"] if e["borough"] == 1 and e["cbd"] and e["band"] == "midday")
    cbd_night = next(e for e in fleet["mix"] if e["borough"] == 1 and e["cbd"] and e["band"] == "night")
    assert cbd_midday["share"]["horse_carriage"] > 0.0
    assert cbd_night["share"]["horse_carriage"] == 0.0, "the carriage curfew is 21:00"
    assert cbd_midday["share"]["pedicab"] > cbd_night["share"]["pedicab"]


def test_taxi_split_is_manhattan_heavy_for_yellow_and_outer_for_green(fleet: dict):
    cbd = next(e for e in fleet["mix"] if e["borough"] == 1 and e["cbd"] and e["band"] == "midday")
    si = next(e for e in fleet["mix"] if e["borough"] == 5 and e["band"] == "midday")
    assert cbd["within_group"]["taxi"]["taxi"] > si["within_group"]["taxi"]["taxi"]
    assert si["within_group"]["taxi"]["black_car"] > 0.8


def test_fleet_mix_groups_partition_the_classes(fleet: dict):
    members = [c for g in fleet["groups"].values() for c in g]
    assert sorted(members) == sorted(FM.CLASSES)
    assert len(members) == len(set(members))


# ----------------------------------------------------------------------------- runtime binary
def test_runtime_nycb_round_trips(density: pl.DataFrame):
    if not NYCB.exists():
        pytest.skip(f"{NYCB} not built")
    info = RX.verify_density_nycb(NYCB, density)
    assert info["cells"] == density.height
    assert info["cell_element_size"] == 32
    assert set(info["sections"]) == {"cells", "nta_polys", "vertices", "strtab"}
    assert info["rings"] >= N_NTA_EXPECTED
    assert info["vertices"] > info["rings"] * 3


def test_runtime_nycb_polygons_are_closed_rings():
    if not NYCB.exists():
        pytest.skip(f"{NYCB} not built")
    from nycsim_pipeline.runtime.nycb import NycbReader
    r = NycbReader(NYCB)
    polys = r.read("nta_polys", RX.POLY_DTYPE)
    verts = r.read("vertices", RX.VERTEX_DTYPE)
    for p in polys[:: max(1, len(polys) // 40)]:
        f, n = int(p["first_vertex"]), int(p["vertex_count"])
        assert n >= 4
        assert math.isclose(float(verts[f]["x"]), float(verts[f + n - 1]["x"]), abs_tol=1e-3)
        assert math.isclose(float(verts[f]["y"]), float(verts[f + n - 1]["y"]), abs_tol=1e-3)
        assert float(verts[f]["z"]) == 0.0
    r.close()


# ----------------------------------------------------------------------------- reported evidence
def test_summary_records_the_fitted_models(summary: dict):
    lm = summary["level_model"]
    assert 0.0 <= lm["stage1_road_class"]["r2"] <= 1.0
    assert 0.0 <= lm["stage2_land_use"]["r2"] <= 1.0
    assert lm["stage2_land_use"]["n"] > 150
    assert lm["nta_r2_with_land_use"] > lm["nta_r2_road_class_only"], \
        "adding land use must improve the NTA-level fit"
    assert lm["ntas_with_sites"] + lm["ntas_from_regression"] == N_NTA_EXPECTED
    ped = summary["pedestrians"]
    assert ped["regression"]["r2"] > 0.5 and ped["sites"] >= 90
    assert 30.0 < ped["walkable_sidewalk_km2"] < 80.0
    assert summary["monotonic_checks"]["midtown_17_gt_midtown_04"]
    assert summary["monotonic_checks"]["midtown_17_gt_tottenville_17"]


def test_summary_totals_are_physically_plausible(summary: dict):
    vkm = summary["density"]["citywide_veh_km_per_weekday"]
    assert 5e7 < vkm < 2e8, "NYC drives roughly 100 million vehicle-km on a weekday"
    peds = summary["pedestrians"]["citywide_present_13h_weekday"]
    assert 2e5 < peds < 3e6, "pedestrians on the sidewalks at 13:00"
    occ = summary["shares"]["for_hire_occupancy"]
    assert set(occ) == set(SH.OCCUPANCY) and all(0.4 < v <= 1.0 for v in occ.values())


def test_figures_exist():
    out = Path(__file__).resolve().parents[2] / "docs" / "verification" / "traffic_density"
    for name in ("density_08.png", "density_22.png"):
        p = out / name
        if not p.exists():
            pytest.skip(f"{p} not rendered — run `python -m nycsim_pipeline.traffic.report`")
        assert p.stat().st_size > 20_000
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
