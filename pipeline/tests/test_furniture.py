"""Tests for the furniture and transit stages.

Unit tests run on synthetic inputs and are always executed. The integration tests at the bottom validate the
real artefacts (``tiles/{tile}/props.parquet``, ``transit/*.parquet``, ``runtime/transit.nycb``) against
DATA_CONTRACTS and are skipped when the stage has not been run in this working copy.
"""
from __future__ import annotations

import io
import json
import math
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely

from nycsim_pipeline.contracts import validate_parquet
from nycsim_pipeline.furniture import allometry, catalog, dedupe, rules, schema, trees
from nycsim_pipeline.furniture.elevation import GroundModel
from nycsim_pipeline.paths import PROCESSED
from nycsim_pipeline.runtime import nycb
from nycsim_pipeline.transit import gtfs as G
from nycsim_pipeline.transit.build import BUS_ROUTE_DTYPE, BUS_STOP_DTYPE, ROUTE_STOP_DTYPE, VERTEX_DTYPE

TILES = PROCESSED / "tiles"
TRANSIT = PROCESSED / "transit"
RUNTIME = PROCESSED / "runtime"


# --------------------------------------------------------------------------------------- allometry

def test_allometry_is_monotone_and_bounded():
    for species in ("Platanus x acerifolia", "Pyrus calleryana", "Acer", "Nonexistent species", None):
        hmax, _k = allometry.params_for(species)
        d = np.arange(1.0, 200.0, 1.0)
        h = allometry.height_array([species] * len(d), d)
        assert np.all(np.diff(h) > 0), f"{species}: height must increase with DBH"
        assert h[0] > allometry.BREAST_HEIGHT_M
        assert h[-1] < allometry.BREAST_HEIGHT_M + hmax
        # a 450-inch DBH outlier must still be a plausible tree, not an extrapolation blow-up:
        # the curve saturates at BREAST_HEIGHT_M + H_max and can never exceed it
        assert allometry.height_m(species, 450 * 2.54) <= hmax + allometry.BREAST_HEIGHT_M + 1e-9


def test_allometry_species_lookup_order():
    assert allometry.params_for("Quercus palustris") == allometry.SPECIES_PARAMS["Quercus palustris"]
    # unknown species of a known genus falls back to the genus
    assert allometry.params_for("Quercus notaspecies") == allometry.SPECIES_PARAMS["Quercus"]
    assert allometry.params_for("Totally unknown") == allometry.DEFAULT_PARAMS
    assert allometry.params_for("") == allometry.DEFAULT_PARAMS


def test_allometry_unknown_dbh_is_a_sapling():
    h = allometry.height_m("Platanus x acerifolia", 0.0)
    assert h == pytest.approx(allometry.height_m("Platanus x acerifolia", allometry.UNKNOWN_DBH_CM))
    assert 1.5 < h < 6.0


def test_dbh_inches_to_cm():
    assert allometry.dbh_inches_to_cm(np.array([10.0]))[0] == pytest.approx(25.4)


def test_crown_diameter_scales_with_class():
    h = np.array([10.0, 10.0])
    c = allometry.crown_diameter_m(h, ["Cornus", "Platanus x acerifolia"])
    assert c[0] > c[1]        # ornamentals are wider than tall relative to canopy trees


# --------------------------------------------------------------------------------------- catalog

def test_catalog_ids_are_unique_and_contiguous():
    ids = [k.id for k in catalog.KINDS]
    assert ids == list(range(len(ids)))
    assert len({k.name for k in catalog.KINDS}) == len(ids)


def test_catalog_json_shape():
    doc = catalog.catalog_json({"tree": 5})
    assert doc["schema_version"] == 1
    assert doc["dedupe"]["radius_m"] == dedupe.RADIUS_M
    by_name = {k["name"]: k for k in doc["kinds"]}
    assert by_name["tree"]["count"] == 5
    assert by_name["hydrant"]["count"] == 0
    for k in doc["kinds"]:
        assert k["datasets"], f"{k['name']} has no dataset provenance"
        assert k["dims_source"], f"{k['name']} has no dimension source"


def test_z_source_enum_documents_the_survey_fallback():
    assert catalog.Z_SOURCE["spot_elev"] == 3 and catalog.Z_SOURCE["spot_elev_far"] == 4


# --------------------------------------------------------------------------------------- schema

def test_empty_columns_covers_every_field():
    cols = schema.empty_columns(3)
    assert set(cols) == {n for n, _ in schema.FIELDS}
    assert np.isnan(cols["z"]).all() and np.isnan(cols["heading"]).all()
    tbl = pa.table({f.name: pa.array(cols[f.name], type=f.type) for f in schema.arrow_schema()},
                   schema=schema.arrow_schema())
    assert tbl.num_rows == 3
    assert tbl.schema.metadata[b"nycsim.schema"] == b"props/1"


# --------------------------------------------------------------------------------------- dedupe

def _cols(kinds, xs, ys, datasets, sources=None):
    n = len(kinds)
    return {"kind": np.array(kinds, dtype=np.int16), "x": np.array(xs, dtype=float), "y": np.array(ys, dtype=float),
            "dataset_id": list(datasets), "source": np.array(sources if sources is not None else [0] * n, dtype=np.int8)}


def test_dedupe_keeps_authority_over_osm_within_radius():
    names = catalog.KIND_ID
    cols = _cols([names["citibike_dock"], names["bike_rack"]], [0.0, 1.0], [0.0, 0.0],
                 ["citibike_gbfs_stations", "osm_newyork_pbf"])
    keep, rep = dedupe.dedupe(cols, {v: k for k, v in names.items()})
    assert keep.tolist() == [True, False]
    assert rep["rows_dropped"] == 1
    assert rep["by_pair"][0]["dropped_dataset"] == "osm_newyork_pbf"


def test_dedupe_respects_the_radius():
    names = catalog.KIND_ID
    cols = _cols([names["citibike_dock"], names["bike_rack"]], [0.0, 1.6], [0.0, 0.0],
                 ["citibike_gbfs_stations", "osm_newyork_pbf"])
    keep, rep = dedupe.dedupe(cols, {v: k for k, v in names.items()})
    assert keep.all() and rep["rows_dropped"] == 0


def test_dedupe_never_merges_different_groups():
    names = catalog.KIND_ID
    cols = _cols([names["hydrant"], names["tree"]], [0.0, 0.5], [0.0, 0.0], ["hydrants", "street_trees_2015"])
    keep, _ = dedupe.dedupe(cols, {v: k for k, v in names.items()})
    assert keep.all(), "a hydrant next to a tree is two real objects"


def test_dedupe_drops_rule_rows_first():
    names = catalog.KIND_ID
    cols = _cols([names["street_lamp"], names["street_lamp"]], [0.0, 0.4], [0.0, 0.0],
                 ["rule:lamp_30_40m_alt", "osm_newyork_pbf"], sources=[1, 0])
    keep, _ = dedupe.dedupe(cols, {v: k for k, v in names.items()})
    assert keep.tolist() == [False, True]


def test_dedupe_is_deterministic_under_input_order():
    names = catalog.KIND_ID
    ks = [names["hydrant"]] * 3
    a = dedupe.dedupe(_cols(ks, [0.0, 0.5, 5.0], [0, 0, 0], ["hydrants"] * 3), {v: k for k, v in names.items()})[0]
    assert a.tolist() == [True, False, True]


# --------------------------------------------------------------------------------------- rules

def _segment_frame(tmp_path: Path, lines, widths, rw_types, boroughs) -> Path:
    t = pa.table({
        "segment_id": pa.array(np.arange(1, len(lines) + 1, dtype=np.int64)),
        "geometry": pa.array([shapely.to_wkb(g) for g in lines], type=pa.binary()),
        "rw_type": pa.array(np.array(rw_types, dtype=np.int8)),
        "width_m": pa.array(np.array(widths, dtype=np.float32)),
        "borough": pa.array(np.array(boroughs, dtype=np.int8)),
    })
    p = tmp_path / "segments.parquet"
    pq.write_table(t, p)
    return p


def test_rules_skipped_without_roads(tmp_path):
    parts, rep = rules.build_rule_props({}, tmp_path / "does_not_exist.parquet")
    assert parts == [] and rep["skipped"] is True and "does not exist" in rep["reason"]


def test_street_lamp_rule_spacing_sides_and_offset(tmp_path):
    line = shapely.linestrings([[0.0, 0.0], [1000.0, 0.0]])       # 1 km due east
    p = _segment_frame(tmp_path, [line], [12.0], [1], [1])
    seg = rules.load_segments(p)
    lamps = rules.street_lamps(seg, np.empty((0, 2)))
    x, y = np.asarray(lamps["x"]), np.asarray(lamps["y"])
    assert len(x) > 20
    offset = 12.0 / 2 + rules.LAMP_CURB_OFFSET_M
    assert np.allclose(np.abs(y), offset), "lamps stand offset from the centreline by width/2 + curb offset"
    assert set(np.sign(y).tolist()) == {1.0, -1.0}, "sides must alternate"
    order = np.argsort(x)
    d = np.diff(x[order])
    assert rules.LAMP_SPACING_MIN_M - 1e-6 <= d.min() and d.max() <= rules.LAMP_SPACING_MAX_M + 1e-6
    assert np.all(np.asarray(lamps["source"]) == 1)
    assert all(s.startswith("rule:") for s in lamps["dataset_id"])


def test_street_lamp_rule_skips_narrow_streets(tmp_path):
    line = shapely.linestrings([[0.0, 0.0], [1000.0, 0.0]])
    p = _segment_frame(tmp_path, [line], [rules.MIN_LAMP_WIDTH_M - 0.5], [1], [1])
    lamps = rules.street_lamps(rules.load_segments(p), np.empty((0, 2)))
    assert len(lamps["x"]) == 0


def test_street_lamp_rule_is_suppressed_near_a_mapped_lamp(tmp_path):
    line = shapely.linestrings([[0.0, 0.0], [1000.0, 0.0]])
    p = _segment_frame(tmp_path, [line], [12.0], [1], [1])
    seg = rules.load_segments(p)
    free = rules.street_lamps(seg, np.empty((0, 2)))
    mapped = np.column_stack([np.arange(0.0, 1000.0, 5.0), np.zeros(200)])
    covered = rules.street_lamps(seg, mapped)
    assert len(free["x"]) > 0 and len(covered["x"]) == 0


def test_manhole_rule_spacing(tmp_path):
    y = rules.steam_north_limit_y() - 500.0
    p = _segment_frame(tmp_path, [shapely.linestrings([[0.0, y], [4000.0, y]])], [12.0], [1], [1])
    manholes, _ = rules.manholes_and_steam(rules.load_segments(p), np.empty((0, 2)))
    mx = np.sort(np.asarray(manholes["x"]))
    assert len(mx) > 90
    assert np.allclose(np.diff(mx), rules.MANHOLE_SPACING_M, atol=1e-6)


def test_steam_vent_rule_is_confined_to_the_con_edison_district(tmp_path):
    y = rules.steam_north_limit_y() - 500.0
    inside = shapely.linestrings([[0.0, y], [4000.0, y]])
    north_of_96 = shapely.linestrings([[0.0, y + 6000.0], [4000.0, y + 6000.0]])
    other_borough = shapely.linestrings([[0.0, y - 100.0], [4000.0, y - 100.0]])
    narrow = shapely.linestrings([[0.0, y - 200.0], [4000.0, y - 200.0]])
    p = _segment_frame(tmp_path, [inside, north_of_96, other_borough, narrow],
                       [12.0, 12.0, 12.0, 6.0], [1, 1, 1, 1], [1, 1, 3, 1])
    _, steam = rules.manholes_and_steam(rules.load_segments(p), np.empty((0, 2)))
    sy = np.asarray(steam["y"])
    assert len(sy) > 0
    assert np.all(sy <= rules.steam_north_limit_y()), "no vent north of 96th Street"
    assert np.allclose(sy, y), "only the wide Manhattan segment inside the district gets vents"
    assert np.all(np.asarray(steam["source"]) == 1)
    assert len(sy) == pytest.approx(4000.0 / rules.STEAM_SPACING_M, abs=1)


def test_manhole_rule_is_suppressed_near_a_mapped_manhole(tmp_path):
    y = 0.0
    p = _segment_frame(tmp_path, [shapely.linestrings([[0.0, y], [1000.0, y]])], [12.0], [1], [2])
    seg = rules.load_segments(p)
    free, _ = rules.manholes_and_steam(seg, np.empty((0, 2)))
    mapped = np.column_stack([np.arange(0.0, 1000.0, 5.0), np.zeros(200)])
    covered, _ = rules.manholes_and_steam(seg, mapped)
    assert len(free["x"]) > 0 and len(covered["x"]) == 0


def test_rule_hash_is_deterministic():
    v = np.array([1, 2, 3, 12345678], dtype=np.int64)
    a = rules._hash01(v)
    b = rules._hash01(v)
    assert np.array_equal(a, b) and a.min() >= 0.0 and a.max() < 1.0
    assert not np.array_equal(a, rules._hash01(v, salt=7))


# --------------------------------------------------------------------------------------- elevation

def test_ground_model_idw_and_source_flags():
    gx = np.array([0.0, 100.0, 0.0, 100.0])
    gy = np.array([0.0, 0.0, 100.0, 100.0])
    gz = np.array([10.0, 10.0, 10.0, 10.0])
    gm = GroundModel(gx, gy, gz, n_spot=4)
    z, src = gm.sample(np.array([50.0, 100000.0]), np.array([50.0, 100000.0]))
    assert z[0] == pytest.approx(10.0)
    assert src[0] == catalog.Z_SOURCE["spot_elev"]
    assert src[1] == catalog.Z_SOURCE["spot_elev_far"]


def test_ground_model_interpolates_between_levels():
    gm = GroundModel(np.array([0.0, 10.0]), np.array([0.0, 0.0]), np.array([0.0, 20.0]), n_spot=2)
    z, _ = gm.sample(np.array([5.0]), np.array([0.0]))
    assert 5.0 < z[0] < 15.0


# --------------------------------------------------------------------------------------- trees loader

def _tree_csv(tmp_path: Path) -> Path:
    header = ",".join(trees.COLUMNS)
    rows = [
        "1,10,0,Alive,Good,Quercus palustris,pin oak,40.75,-73.98,1,OnCurb,NoDamage,MN17,1 X ST",
        "2,0,12,Stump,,,,40.75,-73.98,1,OnCurb,NoDamage,MN17,2 X ST",
        "3,8,0,Dead,,Acer rubrum,red maple,40.75,-73.98,1,OnCurb,NoDamage,MN17,3 X ST",
        "4,0,0,Alive,Poor,,,40.76,-73.97,1,OffsetFromCurb,Damage,MN17,4 X ST",
    ]
    p = tmp_path / "trees.csv"
    p.write_text(header + "\n" + "\n".join(rows) + "\n")
    return p


def test_tree_census_excludes_dead_and_stumps(tmp_path):
    tc = trees.load_trees(_tree_csv(tmp_path))
    assert (tc.n_total, tc.n_alive, tc.n_dead, tc.n_stump) == (4, 2, 1, 1)
    assert tc.df.height == 2
    assert tc.n_no_dbh == 1 and tc.n_no_species == 1
    assert tc.df["height_m"].to_list()[0] > 1.37
    assert tc.df["variant"].to_list() == [0, 2]     # Good -> 0, Poor -> 2
    assert tc.species_counts[0][0] in {"Quercus palustris", ""}


# --------------------------------------------------------------------------------------- GTFS

def _make_feed(tmp_path: Path, name: str, *, with_calendar: bool = True) -> Path:
    files = {
        "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nT,Test Transit,http://x,America/New_York\n",
        "routes.txt": "route_id,agency_id,route_short_name,route_long_name,route_type,route_color\n"
                      "R1,T,R1,Test Route,3,FF0000\n",
        "trips.txt": "route_id,service_id,trip_id,direction_id,shape_id\n"
                     "R1,WK,t1,0,s1\nR1,WK,t2,1,s1\nR1,WK,t3,0,s1\nR1,SU,t4,0,s1\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
                     "100,  Stop A,  40.75, -73.98,0,\n101,Stop B,40.76,-73.97,0,\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                          "t1,08:00:00,08:00:00,100,1\nt1,08:10:00,08:10:00,101,2\n"
                          "t2,08:20:00,08:20:00,101,1\nt2,08:30:00,08:30:00,100,2\n"
                          "t3,08:40:00,08:40:00,100,1\nt3,08:50:00,08:50:00,101,2\n"
                          "t4,09:00:00,09:00:00,100,1\n",
        "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
                      "s1, 40.75, -73.98,1\ns1,40.76,-73.97,2\n",
        "calendar_dates.txt": "service_id,date,exception_type\nWK,20260909,1\n",
    }
    if with_calendar:
        files["calendar.txt"] = ("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
                                 "WK,1,1,1,1,1,0,0,20260101,20271231\nSU,0,0,0,0,0,0,1,20260101,20271231\n")
        files["calendar_dates.txt"] = "service_id,date,exception_type\n"
    p = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(p, "w") as z:
        for fn, body in files.items():
            z.writestr(fn, body)
    return p


def test_gtfs_active_services_from_calendar(tmp_path):
    feed = G.Feed("test", _make_feed(tmp_path, "f"))
    assert G.active_services(feed, date(2026, 9, 9)) == {"WK"}      # Wednesday
    assert G.active_services(feed, date(2026, 9, 13)) == {"SU"}     # Sunday
    day, svc = G.pick_service_date(feed)
    assert day == date(2026, 9, 9) and svc == {"WK"}


def test_gtfs_active_services_from_calendar_dates_only(tmp_path):
    feed = G.Feed("test", _make_feed(tmp_path, "g", with_calendar=False))
    assert G.active_services(feed, date(2026, 9, 9)) == {"WK"}
    assert G.active_services(feed, date(2026, 9, 10)) == set()


def test_gtfs_calendar_dates_removal_wins(tmp_path):
    p = _make_feed(tmp_path, "h")
    with zipfile.ZipFile(p, "a") as z:
        z.writestr("calendar_dates.txt", "service_id,date,exception_type\nWK,20260909,2\n")
    feed = G.Feed("test", p)
    assert "WK" not in G.active_services(feed, date(2026, 9, 9))


def test_gtfs_headway_and_route_stops(tmp_path):
    from nycsim_pipeline.transit import build as B

    feed = G.Feed("test", _make_feed(tmp_path, "i"))
    res = B.read_feed(feed, tmp_path / "scratch")
    assert res.trips.height == 3                                     # SU trip excluded
    assert set(map(tuple, res.route_stops.rows())) == {("R1", "100"), ("R1", "101")}
    hw = B.headway_table(res.route_hours)
    # three trips start in hour 8 across two directions -> 60 * 2 / 3 = 40 min
    assert hw["R1"][8] == 40
    assert hw["R1"][10] == 0
    assert len(hw["R1"]) == 24


def test_gtfs_seconds_handles_after_midnight(tmp_path):
    import polars as pl

    s = G._seconds(pl.Series(["25:30:00", "00:05:00"]))
    assert s.to_list() == [25 * 3600 + 1800, 300]


def test_gtfs_shape_lines(tmp_path):
    feed = G.Feed("test", _make_feed(tmp_path, "j"))
    lines = G.shape_lines(feed, {"s1"})
    assert lines["s1"].shape == (2, 2)
    assert lines["s1"][0].tolist() == [-73.98, 40.75]


# --------------------------------------------------------------------------------------- integration

props_files = sorted(TILES.glob("*/props.parquet")) if TILES.exists() else []
needs_props = pytest.mark.skipif(not props_files, reason="furniture stage has not been run")
needs_transit = pytest.mark.skipif(not (TRANSIT / "bus_routes.parquet").exists(),
                                   reason="transit stage has not been run")


@needs_props
def test_props_conform_to_contract_section_8():
    for p in props_files[:40]:
        assert validate_parquet("props", p) == [], p


@needs_props
def test_props_rows_are_inside_their_tile():
    summary = json.loads((PROCESSED / "furniture" / "build_summary.json").read_text())
    total = 0
    for p in props_files:
        t = pq.read_table(p, columns=["x", "y", "tile", "tx", "ty", "kind", "source", "prop_id"])
        tx = t.column("tx").to_numpy(zero_copy_only=False)
        ty = t.column("ty").to_numpy(zero_copy_only=False)
        x = t.column("x").to_numpy(zero_copy_only=False)
        y = t.column("y").to_numpy(zero_copy_only=False)
        assert np.all(np.floor(x / 1000.0).astype(int) == tx)
        assert np.all(np.floor(y / 1000.0).astype(int) == ty)
        assert len(set(t.column("tile").to_pylist())) == 1
        total += t.num_rows
    assert total == summary["rows"] if "rows" in summary else total > 0


@needs_props
def test_prop_ids_are_unique_and_encode_the_kind():
    seen: set[int] = set()
    for p in props_files:
        t = pq.read_table(p, columns=["prop_id", "kind"])
        ids = t.column("prop_id").to_numpy(zero_copy_only=False)
        kinds = t.column("kind").to_numpy(zero_copy_only=False)
        assert np.all(ids // 10_000_000_000 == kinds)
        before = len(seen)
        seen.update(ids.tolist())
        assert len(seen) == before + len(ids), f"duplicate prop_id in {p}"


@needs_props
def test_props_catalog_counts_match_the_tiles():
    doc = json.loads((PROCESSED / "furniture" / "props_catalog.json").read_text())
    counted: dict[int, int] = {}
    for p in props_files:
        k = pq.read_table(p, columns=["kind"]).column("kind").to_numpy(zero_copy_only=False)
        for kk, c in zip(*np.unique(k, return_counts=True)):
            counted[int(kk)] = counted.get(int(kk), 0) + int(c)
    for kind in doc["kinds"]:
        assert kind["count"] == counted.get(kind["id"], 0), kind["name"]


@needs_props
def test_every_prop_has_provenance():
    for p in props_files[:60]:
        t = pq.read_table(p, columns=["source", "dataset_id"])
        src = np.asarray(t.column("source").to_pylist())
        ds = t.column("dataset_id").to_pylist()
        assert set(np.unique(src).tolist()) <= {0, 1}
        assert all(d for d in ds), "dataset_id must name the source or the rule"
        for s, d in zip(src, ds):
            assert (s == 1) == d.startswith("rule:")


@needs_props
def test_trees_carry_species_and_measured_dbh():
    """The census half of the tree layer. The OSM half is covered by ``test_osm_trees.py``."""
    tree_id = catalog.KIND_ID["tree"]
    n = 0
    n_unknown_dbh = 0
    for p in props_files:
        t = pq.read_table(p, columns=["kind", "dbh_cm", "height_m", "height_source", "species", "dataset_id"])
        k = t.column("kind").to_numpy(zero_copy_only=False)
        ds = np.asarray(t.column("dataset_id").to_pylist(), dtype=object)
        m = (k == tree_id) & (ds == "street_trees_2015")
        if not m.any():
            continue
        n += int(m.sum())
        h = t.column("height_m").to_numpy(zero_copy_only=False)[m]
        d = t.column("dbh_cm").to_numpy(zero_copy_only=False)[m]
        hs = t.column("height_source").to_numpy(zero_copy_only=False)[m]
        assert np.all(np.isfinite(h)) and h.min() > 1.37 and h.max() < 45.0
        assert np.all(d >= 0)                       # 0 = the census recorded no diameter
        n_unknown_dbh += int((d == 0).sum())
        assert np.all(hs == catalog.HEIGHT_SOURCE["allometry"])
        assert (np.asarray(t.column("species").to_pylist())[m] != "").sum() > 0
    assert n > 600_000, "the 2015 census has ~652k living trees"
    summary = json.loads((PROCESSED / "furniture" / "build_summary.json").read_text())
    dropped = sum(p["count"] for p in summary["dedupe"]["by_pair"]
                  if p["group"] == "tree" and p["dropped_dataset"] == "street_trees_2015")
    assert n == summary["trees"]["alive_placed"] - dropped, "every living census tree is placed exactly once"
    assert 0 < n_unknown_dbh <= summary["trees"]["alive_without_dbh_treated_as_5cm"]


@needs_transit
def test_transit_tables_conform_to_contract_section_9():
    assert validate_parquet("bus_routes", TRANSIT / "bus_routes.parquet") == []
    assert validate_parquet("bus_stops", TRANSIT / "bus_stops.parquet") == []


@needs_transit
def test_bus_headways_are_plausible():
    t = pq.read_table(TRANSIT / "bus_routes.parquet", columns=["route_id", "headway_min"])
    hw = t.column("headway_min").to_pylist()
    assert all(len(v) == 24 for v in hw)
    flat = np.array([x for v in hw for x in v])
    assert flat.min() >= 0 and flat.max() <= 32767
    served = flat[flat > 0]
    assert served.size > 1000
    assert np.median(served) <= 120, "a median weekday headway over two hours would mean the join is wrong"


@needs_transit
def test_bus_route_geometry_is_in_nyc_tm():
    t = pq.read_table(TRANSIT / "bus_routes.parquet", columns=["geometry"])
    g = shapely.from_wkb(t.column("geometry").to_pylist())
    b = shapely.total_bounds(np.asarray(g, dtype=object))
    assert -40000 < b[0] and b[2] < 40000 and -40000 < b[1] and b[3] < 40000
    assert json.loads(pq.ParquetFile(TRANSIT / "bus_routes.parquet").schema_arrow.metadata[b"geo"])["primary_column"] == "geometry"


@needs_transit
def test_subway_entrances_have_lines_and_globes():
    t = pq.read_table(TRANSIT / "subway_entrances.parquet")
    lines = t.column("lines").to_pylist()
    globes = np.asarray(t.column("has_globe").to_pylist())
    assert t.num_rows > 1000
    assert sum(1 for v in lines if v) / t.num_rows > 0.95
    assert set(np.unique(globes).tolist()) <= {0, 1, 2}
    assert (globes == 1).sum() > 100
    assert set(t.column("kind").to_pylist()) <= {"stair", "escalator", "elevator"}


@needs_transit
def test_rail_structures_have_deck_heights():
    t = pq.read_table(TRANSIT / "rail_structures.parquet")
    kinds = np.asarray(t.column("kind").to_pylist())
    h = np.asarray(t.column("deck_height_m").to_pylist(), dtype=float)
    src = np.asarray(t.column("deck_height_source").to_pylist(), dtype=int)
    assert set(np.unique(kinds).tolist()) <= {"elevated", "viaduct", "embankment", "open_cut"}
    elevated = kinds == "elevated"
    assert elevated.sum() > 0
    assert np.isfinite(h[elevated]).all()
    assert (src == 0).sum() > 0, "at least some deck heights must come from surveyed bridge elevation points"
    assert np.nanmedian(h[elevated]) > 2.0


@needs_transit
def test_ferry_routes_include_the_staten_island_ferry():
    t = pq.read_table(TRANSIT / "ferry_routes.parquet")
    ids = t.column("route_id").to_pylist()
    assert "SIF" in ids
    g = shapely.from_wkb(t.column("geometry").to_pylist()[ids.index("SIF")])
    assert 7000 < shapely.length(g) / max(shapely.get_num_geometries(g), 1) < 12000, \
        "St George - Whitehall is 8.4 km"
    term = pq.read_table(TRANSIT / "ferry_terminals.parquet")
    names = [n.lower() for n in term.column("name").to_pylist()]
    assert any("st. george" in n or "st george" in n for n in names)
    assert any("whitehall" in n for n in names)


@needs_transit
@pytest.mark.skipif(not (RUNTIME / "transit.nycb").exists(), reason="nycb not exported")
def test_transit_nycb_round_trip():
    r = nycb.NycbReader(RUNTIME / "transit.nycb")
    assert set(r.sections) >= {"bus_routes", "bus_stops", "route_stops", "vertices", "strtab"}
    routes = r.read("bus_routes", BUS_ROUTE_DTYPE)
    stops = r.read("bus_stops", BUS_STOP_DTYPE)
    rstops = r.read("route_stops", ROUTE_STOP_DTYPE)
    verts = r.read("vertices", VERTEX_DTYPE)
    blob = r.strings()
    assert len(routes) == pq.ParquetFile(TRANSIT / "bus_routes.parquet").metadata.num_rows
    assert len(stops) == pq.ParquetFile(TRANSIT / "bus_stops.parquet").metadata.num_rows
    assert routes["first_vertex"].max() + routes["vertex_count"].max() <= len(verts) + routes["vertex_count"].max()
    for row in routes[:20]:
        name = r.string_at(int(row["name_str"]), blob)
        assert name
        assert int(row["first_vertex"]) + int(row["vertex_count"]) <= len(verts)
        assert int(row["first_stop"]) + int(row["stop_count"]) <= len(rstops)
        assert row["headway_min"].shape == (24,)
    ids = set(stops["id"].tolist())
    assert set(rstops["stop_id"].tolist()) <= ids
    assert np.isfinite(verts["x"]).all() and np.abs(verts["x"]).max() < 40000


# --------------------------------------------------------------------------------------------
# Rooftop props (furniture/rooftop.py)


def test_lift_puts_a_rooftop_prop_on_its_buildings_roof():
    """A planimetric cooling tower is digitised on a roof; a ground elevation buries it."""
    import numpy as np

    from nycsim_pipeline.furniture import rooftop

    kind = np.array([28, 28, 0], dtype=np.int16)
    z = np.array([10.0, 10.0, 10.0], dtype=np.float32)
    z_source = np.array([3, 3, 3], dtype=np.int8)
    attrs = ['{"bin":1000001}', '{"bin":9999999}', '{"bin":1000001}']
    stats = rooftop.lift(kind, z, z_source, attrs, {1000001: 55.5})

    assert stats == {"rooftop_rows": 2, "lifted": 1, "unmatched": 1,
                     "rise_m": {"min": 45.5, "median": 45.5, "max": 45.5}, "below_ground": 0}
    assert z[0] == pytest.approx(55.5)
    assert z_source[0] == rooftop.Z_SOURCE_ROOF
    assert z[1] == pytest.approx(10.0), "a BIN with no measured roof keeps the surveyed ground z"
    assert z_source[1] == 3
    assert z[2] == pytest.approx(10.0), "a street tree is not a rooftop prop"


def test_lift_is_idempotent():
    import numpy as np

    from nycsim_pipeline.furniture import rooftop

    kind = np.array([28], dtype=np.int16)
    z = np.array([10.0], dtype=np.float32)
    z_source = np.array([3], dtype=np.int8)
    attrs = ['{"bin":7}']
    rooftop.lift(kind, z, z_source, attrs, {7: 30.0})
    again = rooftop.lift(kind, z, z_source, attrs, {7: 30.0})
    assert z[0] == pytest.approx(30.0)
    assert again["rise_m"]["median"] == pytest.approx(0.0)


@needs_props
def test_every_surveyed_cooling_tower_stands_on_a_roof_or_says_why_not():
    """No cooling tower may still carry a ground z_source once the stage has run.

    All 81,684 of them did: the ground model is right for the other 33 kinds and wrong for this one,
    and nothing said so, because nothing placed them either.
    """
    import json as _json

    from nycsim_pipeline.furniture import rooftop

    lifted = ground = 0
    for p in props_files[:120]:
        t = pq.read_table(p, columns=["kind", "z_source", "attrs"])
        k = t.column("kind").to_numpy(zero_copy_only=False)
        zs = t.column("z_source").to_numpy(zero_copy_only=False)
        at = t.column("attrs").to_pylist()
        for i in np.nonzero(np.isin(k, rooftop.ROOFTOP_KINDS))[0]:
            if int(zs[i]) == rooftop.Z_SOURCE_ROOF:
                lifted += 1
            else:
                ground += 1
                bin_ = _json.loads(at[i] or "{}").get("bin")
                assert bin_ is not None, "a rooftop prop with neither a roof z nor a BIN to find one"
    if lifted + ground == 0:
        pytest.skip("no rooftop props in the sampled tiles")
    assert lifted / (lifted + ground) > 0.9, (
        f"only {lifted} of {lifted + ground} sampled cooling towers stand on a roof")


def test_a_kind_another_stage_builds_is_not_counted_as_a_missing_asset():
    """A curb ramp has no prop asset on purpose: it is cut into the pavement mesh (J21).

    Both reports used to call that a gap. The renderer listed 81 curb ramps as ``unmapped`` on a
    Bronx sheet whose pavement had every one of them cut into it, and the manifest carried them in
    ``prop_kinds_without_an_asset``. A gap figure that moves when one stage takes work over from
    another is measuring the division of labour, not the gap, so the two are counted apart.
    """
    from nycsim_pipeline.furniture import assets as A

    assert "curb_ramp" in A.BUILT_ELSEWHERE, "the curb ramp is built by the pavement stage"
    for name, why in A.BUILT_ELSEWHERE.items():
        assert why.strip(), f"{name} is declared built elsewhere without saying by what"

    index = A.PropAssets(by_id={}, by_kind={}, kind_names={7: "curb_ramp", 8: "payphone"},
                         kit_by_id={})
    entry, why = index.resolve(7)
    assert entry is None
    assert A.is_built_elsewhere(why), f"a curb ramp resolved with reason {why!r}"
    assert why.endswith("curb_ramp"), "the reason has to keep the kind so a report can name it"

    entry, why = index.resolve(8)
    assert entry is None
    assert not A.is_built_elsewhere(why), "a payphone has no asset anywhere; that is a real gap"
    assert why == "payphone", "a real gap names the kind so the report can list it"


# --- street lamp fixtures (J56) ------------------------------------------------------------

def test_a_declared_variant_map_beats_the_position_of_the_asset_in_a_sorted_list():
    """``variant`` is an enum the catalogue writes on the asset; it is not a list index.

    ``resolve`` used to return ``choices[v % len(choices)]`` over the id-sorted assets of a kind.
    For ``street_lamp`` that is right for 1 and 3 by coincidence of the alphabet and wrong for the
    other two: variant 2 is declared ``lamp_bishops_crook`` and the modulo returns ``lamp_highmast``,
    variant 4 is declared ``lamp_highmast`` and wraps round to ``lamp_bishops_crook``.
    """
    from nycsim_pipeline.furniture import assets as A

    entries = [{"id": "lamp_bishops_crook", "dataset_kind": "street_lamp", "tags": ["variant:2"]},
               {"id": "lamp_cobra_davit", "dataset_kind": "street_lamp", "tags": ["variant:1"]},
               {"id": "lamp_highmast", "dataset_kind": "street_lamp", "tags": ["variant:4"]},
               {"id": "lamp_park_twin", "dataset_kind": "street_lamp", "tags": ["variant:3"]}]
    by_kind = {"street_lamp": sorted(entries, key=lambda e: e["id"])}
    index = A.PropAssets(by_id={e["id"]: e for e in entries}, by_kind=by_kind,
                         kind_names={14: "street_lamp"}, kit_by_id={},
                         variants_by_kind={"street_lamp": A.declared_variants(entries)})

    for variant, want in ((1, "lamp_cobra_davit"), (2, "lamp_bishops_crook"),
                          (3, "lamp_park_twin"), (4, "lamp_highmast")):
        entry, why = index.resolve(14, variant=variant)
        assert entry["id"] == want, f"variant {variant} resolved to {entry['id']}, not {want}"
        assert why == "ok"

    # The list-position rule would have wrapped 4 to index 0.
    assert by_kind["street_lamp"][4 % 4]["id"] == "lamp_bishops_crook"


def test_an_unknown_lamp_variant_takes_the_citywide_default_and_says_so():
    """0 means "nothing in the data said"; it must not silently become whichever id sorts first.

    14,690 of the 16,971 OSM lamp nodes tag nothing about their fixture. Under the old rule they all
    became Bishop's Crooks -- a restored historic fixture NYC has a few thousand of. The default is
    a rule and the reason string has to admit it.
    """
    from nycsim_pipeline.furniture import assets as A

    entries = [{"id": "lamp_bishops_crook", "dataset_kind": "street_lamp", "tags": ["variant:2"]},
               {"id": "lamp_cobra_davit", "dataset_kind": "street_lamp", "tags": ["variant:1"]}]
    index = A.PropAssets(by_id={e["id"]: e for e in entries},
                         by_kind={"street_lamp": sorted(entries, key=lambda e: e["id"])},
                         kind_names={14: "street_lamp"}, kit_by_id={},
                         variants_by_kind={"street_lamp": A.declared_variants(entries)})
    assert A.DEFAULT_VARIANT["street_lamp"] == 1
    for bad in (0, 9, None, "x"):
        entry, why = index.resolve(14, variant=bad)
        assert entry["id"] == "lamp_cobra_davit", f"variant {bad!r} -> {entry['id']}"
        assert why.startswith("variant_default:"), why


def test_a_kind_that_declares_no_variant_map_still_resolves_and_does_not_wrap():
    from nycsim_pipeline.furniture import assets as A

    entries = [{"id": "bench_a", "dataset_kind": "bench"}, {"id": "bench_b", "dataset_kind": "bench"}]
    index = A.PropAssets(by_id={e["id"]: e for e in entries}, by_kind={"bench": entries},
                         kind_names={5: "bench"}, kit_by_id={})
    assert index.resolve(5, variant=0)[0]["id"] == "bench_a"
    assert index.resolve(5, variant=1)[0]["id"] == "bench_b"
    entry, why = index.resolve(5, variant=2)
    assert entry["id"] == "bench_a" and why == "variant_out_of_range:2", why


def test_the_lamp_fixture_comes_from_the_tag_that_describes_the_mast():
    """``lamp_mount`` says what the fixture is; ``lamp_type`` says what the bulb is.

    The lookup this replaces searched ``support + subtype`` for "cobra", "bishop", "historic" and
    "pedestrian". Measured against the real extract, none of those four strings occurs on any of the
    16,971 lamp nodes, so every one of them fell through to variant 0.
    """
    from nycsim_pipeline.furniture.datasets import lamp_variant

    assert lamp_variant({"lamp_mount": "bent_mast"}) == (1, "lamp_mount=bent_mast")
    assert lamp_variant({"lamp_mount": "straight_mast"})[0] == 1
    assert lamp_variant({"lamp_mount": "angled_mast"})[0] == 1
    assert lamp_variant({"lamp_mount": "high_mast"}) == (4, "lamp_mount=high_mast")
    assert lamp_variant({"lamp_mount": "lamppost"}) == (3, "lamp_mount=lamppost")
    assert lamp_variant({"light:mount": "bent_mast"})[0] == 1
    assert lamp_variant({"light_source": "lantern"}) == (3, "light_source=lantern")
    assert lamp_variant({"lamp_mount": "BENT_MAST"})[0] == 1, "OSM values are not case-normalised"

    # A light source is not a mast: led/electric/fluorescent say nothing about the pole.
    for t in ({"lamp_type": "led"}, {"lamp_type": "electric"}, {"support": "pole"}, {}):
        assert lamp_variant(t) == (0, ""), t

    # A mount the catalogue has no mesh for is recorded as such, not guessed into a pole variant.
    v, why = lamp_variant({"lamp_mount": "bollard"})
    assert v == 0 and why.startswith("no_asset:"), (v, why)


def test_the_park_post_rule_leaves_a_measurement_and_a_parkway_alone():
    """A rule may fill a gap; it may not overwrite what the data actually says.

    Central Park's drives carry a cast-iron post-top lantern and the road rule stamps a DOT cobra
    head on every pole it places. The parkways that run through park land -- Belt, Grand Central,
    Cross Island, Richmond -- are lit with cobra heads and must keep them.
    """
    import json as _json

    import numpy as np
    import shapely
    from nycsim_pipeline.furniture import park_lamps as PL

    square = shapely.geometry.box(0.0, 0.0, 100.0, 100.0)
    tree = shapely.STRtree([square])
    real_park_ground = PL.park_ground
    PL.park_ground = lambda: (tree, np.array(["Test Park"]))
    try:
        cols = {
            "kind": np.array([14, 14, 14, 14, 14, 3], dtype=np.int16),
            "variant": np.array([1, 1, 3, 4, 1, 0], dtype=np.int16),
            "x": np.array([50.0, 50.0, 50.0, 50.0, 500.0, 50.0]),
            "y": np.array([50.0, 60.0, 70.0, 80.0, 50.0, 50.0]),
            "dataset_id": ["rule:lamp_30_40m_alt"] * 5 + ["osm_newyork_pbf"],
            "attrs": [_json.dumps({"rw_type": 1}), _json.dumps({"rw_type": 2}), "", "", "", ""],
        }
        hw, unknown = PL.highway_mask_from_attrs(cols["attrs"])
        rep = PL.apply(cols, 14, highway_mask=hw)
    finally:
        PL.park_ground = real_park_ground

    got = list(cols["variant"])
    assert got[0] == PL.PARK_VARIANT, "a rule-placed pole on a park street becomes a park post"
    assert got[1] == 1, "a pole on a parkway keeps its cobra head"
    assert got[2] == 3 and got[3] == 4, "a measured fixture is not overwritten by a rule"
    assert got[4] == 1, "a pole outside the park is untouched"
    assert got[5] == 0, "a row that is not a lamp is untouched"
    assert rep["moved"] == 1 and rep["road_class_excluded"] == 1
    assert unknown == 4
    assert PL.RULE_ID in cols["dataset_id"][0], "the row has to name the rule that re-fixtured it"
    assert cols["dataset_id"][1] == "rule:lamp_30_40m_alt", "an untouched row keeps its provenance"


def test_the_lamp_rule_records_the_road_class_it_placed_against():
    """:mod:`.park_lamps` must not have to ask "which segment is nearest" afterwards.

    That question has a different answer from "which segment put this pole here" -- the pole sits
    half a carriageway plus 0.6 m off its own centreline, which on a park drive beside a parkway is
    nearer the parkway.
    """
    import json as _json

    import numpy as np
    import shapely
    from nycsim_pipeline.furniture import rules as R

    seg = {"rw_type": np.array([1, 2], dtype=np.int8),
           "width_m": np.array([12.0, 20.0]),
           "segment_id": np.array([11, 22], dtype=np.int64),
           "geometry": [shapely.LineString([(0, 0), (0, 200)]),
                        shapely.LineString([(300, 0), (300, 200)])]}
    cols = R.street_lamps(seg, np.empty((0, 2)))
    assert len(cols["x"]) > 0
    got = {int(_json.loads(a)["rw_type"]) for a in cols["attrs"]}
    assert got == {1, 2}, got
    assert set(np.asarray(cols["variant"])) == {1}, "the road rule still places the DOT cobra head"


def test_an_avenue_mall_is_not_park_interior():
    """NYC Parks owns the Broadway and Park Avenue malls, so they arrive as ``park_ground``.

    A lamp standing on the Park Avenue mall is lighting Park Avenue. The separator is the polygon's
    own short side: measured, the named malls run 2.1 to 10.1 m across and the parks 27.4 to 46.4 m.
    """
    import shapely
    from nycsim_pipeline.furniture import park_lamps as PL

    assert PL.short_side_m(shapely.geometry.box(0, 0, 400, 7.2)) == pytest.approx(7.2)
    assert PL.short_side_m(shapely.geometry.box(0, 0, 400, 7.2)) < PL.MIN_PARK_WIDTH_M
    assert PL.short_side_m(shapely.geometry.box(0, 0, 800, 34.1)) > PL.MIN_PARK_WIDTH_M
    # A rotated strip is measured across its own short side, not its bounding box.
    strip = shapely.affinity.rotate(shapely.geometry.box(0, 0, 400, 6.7), 37.0)
    assert PL.short_side_m(strip) == pytest.approx(6.7, abs=1e-6)
    # Degenerate geometry is never park interior.
    assert PL.short_side_m(shapely.Point(1, 1)) == 0.0


def test_a_parkway_mainline_typed_as_a_street_still_keeps_its_cobra_head():
    """``rw_type`` alone lets the parkways through, so the rule reads ``nonped`` as well.

    Measured over the real segments: **1,384 vehicles-only segments carry ``rw_type`` 1, plain
    street**, and the ten commonest names among all 10,160 of them are Long Island Expy, Belt Pkwy,
    Cross Bronx Expy, Grand Central Pkwy, BQE, Van Wyck, Gowanus, FDR Drive, Bruckner and Major
    Deegan. Before this the Grand Central Parkway mainline was getting park lamps where it crosses
    its own parkland.
    """
    import json as _json

    from nycsim_pipeline.furniture import park_lamps as PL

    rows = [_json.dumps({"rw_type": 1, "nonped": ""}),      # an ordinary park street
            _json.dumps({"rw_type": 1, "nonped": "V"}),     # Grand Central Pkwy, typed as street
            _json.dumps({"rw_type": 1, "nonped": "D"}),     # Hudson River Greenway
            _json.dumps({"rw_type": 2, "nonped": ""}),      # highway class
            _json.dumps({"rw_type": 1}),                    # written before nonped was carried
            ""]                                              # an OSM node: no road at all
    mask, unknown = PL.highway_mask_from_attrs(rows)
    assert list(mask) == [False, True, False, True, False, False]
    assert unknown == 1, "only the row with no rw_type at all is unknown"
    assert PL.NONPED_VEHICLES_ONLY == "V"


def test_the_lamp_rule_carries_both_the_road_class_and_the_pedestrian_flag():
    import json as _json

    import numpy as np
    import shapely
    from nycsim_pipeline.furniture import rules as R

    seg = {"rw_type": np.array([1, 1], dtype=np.int8),
           "width_m": np.array([12.0, 20.0]),
           "segment_id": np.array([11, 22], dtype=np.int64),
           "nonped": np.array(["", "V"], dtype=object),
           "geometry": [shapely.LineString([(0, 0), (0, 200)]),
                        shapely.LineString([(300, 0), (300, 200)])]}
    cols = R.street_lamps(seg, np.empty((0, 2)))
    got = {(int(d["rw_type"]), str(d["nonped"])) for d in (_json.loads(a) for a in cols["attrs"])}
    assert got == {(1, ""), (1, "V")}, got


# --------------------------------------------------------------------------- J70: a tree is its measured height
def test_a_tree_is_drawn_at_the_height_its_own_row_records():
    """The census measures a trunk diameter and ``allometry`` turns it into a height by a published
    species curve.  Until J70 that number only chose one of three exported sizes and was then
    discarded, so what stood on the street was whatever height the kit had exported: a pin oak's
    three assets are 11.8, 18.3 and 22.6 m and a plane tree's are 20.7, 24.0 and 27.7 m, while the
    bin edges were 7 m and 12 m.  A tree measured at 8 m stood 18.3 m over the pavement."""
    from pathlib import Path

    from nycsim_pipeline.furniture import assets as A

    root = Path(__file__).resolve().parents[2]
    idx = A.load(root / "data" / "processed", root / "blender_out")
    if not idx.asset_height_m:
        pytest.skip("props_asset_catalog.json not produced yet")

    for species, want in (("Quercus palustris", 8.0), ("Quercus palustris", 18.0),
                          ("Platanus x acerifolia", 9.0), ("Tilia cordata", 5.0),
                          ("Ginkgo biloba", 14.0), ("Acer platanoides", 11.0)):
        entry, why, scale = idx.tree_asset(species, want)
        assert entry is not None, f"{species} resolved to no asset"
        h = idx.asset_height_m.get(entry["id"])
        assert h and h > 0, f"{entry['id']} publishes no height"
        assert A.TREE_SCALE_MIN <= scale <= A.TREE_SCALE_MAX
        drawn = h * scale
        assert abs(drawn - want) < 0.05, (
            f"{species} measured {want} m is drawn {drawn:.1f} m as {entry['id']} "
            f"({h:.1f} m x {scale:.3f}); reason {why}")

    # The nearest exported size must be chosen, so the scale stays as near 1 as the kit allows.
    entry, _why, scale = idx.tree_asset("Quercus palustris", 18.0)
    assert entry["id"] == "tree_pin_oak_medium", f"18 m pin oak resolved to {entry['id']}"
    assert 0.95 < scale < 1.05


def test_only_a_tree_is_ever_scaled_away_from_the_size_it_was_exported_at():
    """Every other prop is a manufactured object whose size is a measurement in its own glb -- a
    hydrant, a bus stop sign, a mailbox.  Scaling one would make the frame lie about it, and
    ``audit_prop_assets`` checks each against its catalogue entry on the assumption that nothing
    scales it.  Only ``tree`` rows carry a height to be drawn at."""
    from pathlib import Path

    from nycsim_pipeline.furniture import assets as A

    root = Path(__file__).resolve().parents[2]
    idx = A.load(root / "data" / "processed", root / "blender_out")
    if not idx.kind_names:
        pytest.skip("props_catalog.json not produced yet")

    scaled = []
    for kind_id, name in sorted(idx.kind_names.items()):
        if name == "tree":
            continue
        for variant in range(4):
            _entry, _why, scale = idx.resolve_scaled(kind_id, variant=variant, height_m=9.0)
            if scale != 1.0:
                scaled.append(f"{name} (kind {kind_id}, variant {variant}) -> x{scale}")
    assert not scaled, "a non-tree prop was scaled away from its exported size:\n  " + "\n  ".join(scaled)


# --------------------------------------------------------------------------------------- citi bike expansion

def _station_cols(capacity: int, x: float = 0.0, y: float = 0.0, station_id: str = "s1", name: str = "A St & B St") -> dict:
    from nycsim_pipeline.furniture import citibike as C  # noqa: F401  (module under test)

    cols = schema.empty_columns(2)
    cols["kind"] = np.array([catalog.KIND_ID["citibike_dock"], catalog.KIND_ID["hydrant"]], dtype=np.int16)
    cols["x"] = np.array([x, x + 50.0])
    cols["y"] = np.array([y, y + 50.0])
    cols["capacity"] = np.array([capacity, 0], dtype=np.int16)
    cols["text"] = [name, ""]
    cols["dataset_id"] = ["citibike_gbfs_stations", "hydrants"]
    cols["attrs"] = [json.dumps({"station_id": station_id, "short_name": "1.01", "region_id": 71, "capacity": capacity}),
                     json.dumps({"unitid": "H1"})]
    return cols


def _segment_along(bearing_deg: float, through=(0.0, 0.0), half_len: float = 100.0, segment_id: int = 9,
                   rw_type: int = 1, name: str = "A ST") -> dict:
    b = math.radians(bearing_deg)
    ux, uy = math.sin(b), math.cos(b)
    line = shapely.LineString([(through[0] - half_len * ux, through[1] - half_len * uy),
                               (through[0] + half_len * ux, through[1] + half_len * uy)])
    return {"segment_id": np.array([segment_id], dtype=np.int64), "geometry": np.array([line], dtype=object),
            "rw_type": np.array([rw_type], dtype=np.int8), "width_m": np.array([12.0]), "borough": np.array([1], dtype=np.int8),
            "street_name": np.array([name], dtype=object)}


def _segments(*segs: dict) -> dict:
    return {k: np.concatenate([s[k] for s in segs]) for k in segs[0]}


def _parts(out: dict, variant: int) -> list[int]:
    kind = np.asarray(out["kind"])
    var = np.asarray(out["variant"])
    return [int(i) for i in np.flatnonzero((kind == catalog.KIND_ID["citibike_dock"]) & (var == variant))]


def _expand(capacity: int, bearing: float | None = 37.0, status=None, station_xy=(0.0, 0.0), seg_through=(0.0, 0.0)):
    from nycsim_pipeline.furniture import citibike as C

    cols = _station_cols(capacity, *station_xy)
    seg = _segment_along(bearing, through=seg_through) if bearing is not None else None
    sx, sy = np.array([station_xy[0]]), np.array([station_xy[1]])
    axes = C.station_facing(sx, sy, seg, C.station_axes(sx, sy, seg))
    return C.expand(cols, catalog.KIND_ID["citibike_dock"], axes, status)


def test_citibike_station_is_a_kiosk_and_n_docks_at_0_9_m_along_the_kerb():
    """A station of capacity N is N dock units and one kiosk, 0.90 m apart along the kerb bearing."""
    from nycsim_pipeline.furniture import citibike as C

    out, rep = _expand(5, bearing=37.0)
    docks, kiosks, bikes = _parts(out, 2), _parts(out, 1), _parts(out, 3)
    assert len(docks) == 5 and len(kiosks) == 1 and len(bikes) == 0
    assert rep["stations"] == 1 and rep["kiosks"] == 1 and rep["docks"] == 5 and rep["bikes"] == 0
    # the hydrant that was not a station is untouched, and the station row itself is gone
    assert int((np.asarray(out["kind"]) == catalog.KIND_ID["hydrant"]).sum()) == 1
    assert len(out["x"]) == 7
    x = np.asarray(out["x"]); y = np.asarray(out["y"])
    order = sorted(docks, key=lambda i: json.loads(out["attrs"][i])["dock_index"])
    for a, b in zip(order, order[1:]):
        d = math.hypot(x[b] - x[a], y[b] - y[a])
        assert abs(d - C.PITCH_M) < 1e-6
        bearing = math.degrees(math.atan2(x[b] - x[a], y[b] - y[a])) % 180.0
        assert abs(bearing - 37.0) < 3.0, bearing
    # centred on the GBFS point
    assert abs(x[order].mean()) < 1e-9 and abs(y[order].mean()) < 1e-9
    # the station of this fixture stands ON the segment, so the side is a coin (rep says so) and the front
    # is the coin's away side, axis + 90 = 127; the tileable +X of the dock lies along the kerb either way
    assert rep["side"] == {"left": 0, "right": 0, "on": 1} and rep["side_from_offset_under_0_5m"] == 1
    for i in docks + kiosks:
        assert abs(float(out["heading"][i]) - ((37.0 + 90.0) % 360.0)) < 1e-3
    # the kiosk is one pitch beyond dock 0, at the axis+180 (south/west) end
    k = kiosks[0]
    assert abs(math.hypot(x[k] - x[order[0]], y[k] - y[order[0]]) - C.PITCH_M) < 1e-6
    assert x[k] < x[order[0]] and y[k] < y[order[0]]
    # the station's record lives on the kiosk: sum(capacity) over the kind == dock count
    assert int(out["capacity"][k]) == 5 and all(int(out["capacity"][i]) == 0 for i in docks)
    assert int(np.asarray(out["capacity"])[np.asarray(out["kind"]) == catalog.KIND_ID["citibike_dock"]].sum()) == len(docks)
    for i in docks + kiosks:
        a = json.loads(out["attrs"][i])
        assert a["station_id"] == "s1" and a["name"] == "A St & B St" and out["text"][i] == "A St & B St"
        assert a["axis_source"] == "nearest_segment" and a["axis_segment_id"] == 9 and abs(a["axis_deg"] - 37.0) < 0.01
        assert a["part"] in ("dock", "kiosk")
    assert rep["axis_source"] == {"nearest_segment": 1}
    assert "rules" in rep and any("0.90 m pitch" in r for r in rep["rules"])


def test_citibike_zero_capacity_station_is_its_kiosk_alone():
    out, rep = _expand(0)
    assert len(_parts(out, 2)) == 0 and len(_parts(out, 1)) == 1
    assert rep["docks"] == 0 and rep["kiosks"] == 1
    assert rep["zero_capacity"] == [{"station_id": "s1", "name": "A St & B St"}]
    k = _parts(out, 1)[0]
    assert float(out["x"][k]) == 0.0 and float(out["y"][k]) == 0.0, "no run: the kiosk stands on the GBFS point"


def test_citibike_station_with_no_segment_in_reach_has_no_axis_and_lies_east_west():
    from nycsim_pipeline.furniture import citibike as C

    # the only segment runs 40 m north of the station, beyond AXIS_MAX_M
    out, rep = _expand(4, bearing=90.0, seg_through=(0.0, 40.0))
    assert rep["axis_source"] == {"none": 1}
    assert rep["stations_with_no_axis"][0]["station_id"] == "s1"
    assert abs(rep["stations_with_no_axis"][0]["nearest_segment_m"] - 40.0) < 0.2
    docks = _parts(out, 2)
    assert all(np.isnan(float(out["heading"][i])) for i in docks + _parts(out, 1))
    y = np.asarray(out["y"])[docks]
    x = np.sort(np.asarray(out["x"])[docks])
    assert np.allclose(y, 0.0) and np.allclose(np.diff(x), C.PITCH_M)
    for i in docks:
        a = json.loads(out["attrs"][i])
        assert a["axis_source"] == "none" and "axis_deg" not in a
    # the same station with a segment 10 m away takes its axis from it
    out2, rep2 = _expand(4, bearing=90.0, seg_through=(0.0, 10.0))
    assert rep2["axis_source"] == {"nearest_segment": 1}
    assert abs(rep2["axis_distance_m"]["p50"] - 10.0) < 0.2


def test_citibike_no_bike_row_exists_without_an_occupancy_source():
    """No station_status snapshot -> no bikes, and the report says what is missing and how to fetch it."""
    from nycsim_pipeline.furniture import citibike as C

    out, rep = _expand(5, status=None)
    assert _parts(out, 3) == [] and rep["bikes"] == 0
    assert rep["bikes_detail"]["absent"] == "no station_status snapshot in this build"
    assert rep["bikes_detail"]["fetch"] == C.FETCH_STATUS
    assert C.load_status(Path("/nonexistent/citibike_gbfs_station_status.json")) is None
    # every variant-3 row anywhere must name the snapshot it came from: none here, so none does
    assert not any(json.loads(a).get("snapshot_last_updated") for a in out["attrs"] if a)


def _status(bikes: int, ebikes: int = 0, station_id: str = "s1", last_updated: int = 1788951780) -> dict:
    return {"source_id": "citibike_gbfs_station_status", "path": "fixture", "last_updated": last_updated,
            "last_updated_iso": "2026-09-09T11:03:00Z", "ttl_s": 60, "version": "2.3",
            "by_station": {station_id: {"num_bikes_available": bikes, "num_ebikes_available": ebikes,
                                        "num_docks_available": 0, "is_installed": 1, "is_renting": 1, "last_reported": 0}}}


def test_citibike_bikes_come_only_from_the_snapshot_fill_from_the_kiosk_end_and_carry_its_instant():
    from nycsim_pipeline.furniture import citibike as C

    # the segment runs at bearing 37 through a point 5 m to the station's left (bearing 37 - 90 from it), so
    # the station stands on the segment's right and "away from the roadway" is bearing 37 + 90 = 127
    left = (5.0 * math.sin(math.radians(-53.0)), 5.0 * math.cos(math.radians(-53.0)))
    out, rep = _expand(5, bearing=37.0, status=_status(3, ebikes=2), seg_through=left)
    docks, bikes = _parts(out, 2), _parts(out, 3)
    assert len(bikes) == 3 and rep["bikes"] == 3
    x = np.asarray(out["x"]); y = np.asarray(out["y"])
    by_index = {json.loads(out["attrs"][i])["dock_index"]: i for i in docks}
    assert all(abs(float(out["heading"][i]) - 127.0) < 1e-3 for i in docks), "front away from the centreline"
    assert all(json.loads(out["attrs"][i])["side"] == "right" and json.loads(out["attrs"][i])["facing"] == "away_from_roadway"
               for i in docks)
    b = math.radians(127.0)
    fx, fy = math.sin(b), math.cos(b)                      # the dock's front, as the consumers rotate it
    for i in bikes:
        a = json.loads(out["attrs"][i])
        assert a["part"] == "bike" and a["dock_index"] in (0, 1, 2)
        assert a["snapshot_last_updated"] == 1788951780
        assert a["num_bikes_available"] == 3 and a["num_ebikes_available"] == 2
        d = by_index[a["dock_index"]]
        assert abs((x[i] - x[d]) + C.BIKE_SETBACK_M * fx) < 1e-6 and abs((y[i] - y[d]) + C.BIKE_SETBACK_M * fy) < 1e-6
        assert abs(float(out["heading"][i]) - float(out["heading"][d])) < 1e-6
        assert out["dataset_id"][i] == "citibike_gbfs_station_status"
    det = rep["bikes_detail"]
    assert det["snapshot_last_updated"] == 1788951780 and det["placed"] == 3 and det["stations_joined"] == 1
    # capped at capacity, and the cap is counted
    out, rep = _expand(5, status=_status(9))
    assert len(_parts(out, 3)) == 5 and rep["bikes_detail"]["capped_by_capacity"] == 4
    assert rep["bikes_detail"]["stations_reporting_more_bikes_than_capacity"][0]["num_bikes_available"] == 9
    # a station the snapshot does not know stays empty and is counted as unmatched
    out, rep = _expand(5, status=_status(4, station_id="other"))
    assert len(_parts(out, 3)) == 0 and rep["bikes_detail"]["stations_unmatched"] == 1


def test_citibike_load_status_reads_the_gbfs_document(tmp_path):
    from nycsim_pipeline.furniture import citibike as C

    p = tmp_path / "citibike_gbfs_station_status.json"
    p.write_text(json.dumps({"last_updated": 1788951780, "ttl": 60, "version": "2.3", "data": {"stations": [
        {"station_id": "s1", "num_bikes_available": 4, "num_ebikes_available": 1, "num_docks_available": 6,
         "is_installed": 1, "is_renting": 0, "last_reported": 1788951700}]}}))
    st = C.load_status(p)
    assert st["last_updated"] == 1788951780 and st["last_updated_iso"] == "2026-09-09T11:03:00Z" and st["ttl_s"] == 60
    assert st["by_station"]["s1"]["num_bikes_available"] == 4 and st["by_station"]["s1"]["is_renting"] == 0


def test_citibike_expand_refuses_rows_that_are_already_parts():
    from nycsim_pipeline.furniture import citibike as C

    out, _ = _expand(3)
    kind_id = catalog.KIND_ID["citibike_dock"]
    n = int((np.asarray(out["kind"]) == kind_id).sum())
    axes = C.station_axes(np.zeros(n), np.zeros(n), None)
    with pytest.raises(ValueError, match="already expanded"):
        C.expand(out, kind_id, axes, None)
    with pytest.raises(ValueError, match="axes cover"):
        C.expand(_station_cols(3), kind_id, C.station_axes(np.zeros(2), np.zeros(2), None), None)


def test_citibike_expansion_must_run_after_dedupe():
    """Documents why build.py expands after dedupe: the 0.9 m pitch is inside the 1.5 m bike_parking radius,
    so an expanded station sent through dedupe loses docks. If this test ever passes with no drops, the
    ordering guard has become unnecessary; until then, moving expand() earlier deletes docks silently."""
    out, _ = _expand(5)
    names = {v: k for k, v in catalog.KIND_ID.items()}
    keep, rep = dedupe.dedupe(out, names)
    kind_id = catalog.KIND_ID["citibike_dock"]
    parts = np.asarray(out["kind"]) == kind_id
    assert int((~keep[parts]).sum()) >= 2, "dedupe would delete docks from an expanded station"
    assert rep["rows_dropped"] >= 2


# --------------------------------------------------------------------------------------- kerb heading and side

def _kerb_cols(kinds: list[str], xy=(0.0, 0.0), attrs: list[dict] | None = None, heading: list[float] | None = None) -> dict:
    cols = schema.empty_columns(len(kinds) + 1)
    cols["kind"] = np.array([catalog.KIND_ID[k] for k in kinds] + [catalog.KIND_ID["hydrant"]], dtype=np.int16)
    cols["x"] = np.full(len(kinds) + 1, xy[0]); cols["y"] = np.full(len(kinds) + 1, xy[1])
    cols["attrs"] = [json.dumps(a, separators=(",", ":")) for a in (attrs or [{} for _ in kinds])] + [json.dumps({"unitid": "H1"})]
    if heading is not None:
        h = np.asarray(cols["heading"], dtype=np.float32).copy()
        h[:len(kinds)] = np.array(heading, dtype=np.float32)
        cols["heading"] = h
    return cols


def _left_of(bearing_deg: float, m: float) -> tuple[float, float]:
    """A point ``m`` metres to the left of a line through the origin running at ``bearing_deg``."""
    b = math.radians(bearing_deg - 90.0)
    return m * math.sin(b), m * math.cos(b)


def test_kerb_side_and_facing_from_the_worked_example():
    """A prop 5 m left of a segment running bearing 37: side = left, toward_roadway = 127, and per kind the
    front the rule table gives -- shelters and the newsstand 307 (away), Link and blade 37 (along), rack 127
    (toward). Mirrored to the right side the perpendiculars swap and the along-kerb headings stay."""
    from nycsim_pipeline.furniture import kerb as K

    kinds = list(K.KINDS)
    for side, sign in (("left", 1.0), ("right", -1.0)):
        px, py = _left_of(37.0, 5.0 * sign)
        cols = _kerb_cols(kinds, (px, py))
        out, rep = K.apply(cols, Path("/nonexistent"), seg=_segment_along(37.0))
        toward = 127.0 if side == "left" else 307.0
        want = {"bus_shelter": (toward + 180) % 360, "bike_shelter": (toward + 180) % 360, "newsstand": (toward + 180) % 360,
                "linknyc": 37.0, "bus_stop_sign": 37.0, "bike_rack": toward}
        for i, k in enumerate(kinds):
            a = json.loads(out["attrs"][i])
            assert abs(float(out["heading"][i]) - want[k]) < 1e-3, (side, k, float(out["heading"][i]), want[k])
            assert a["side"] == side and a["facing"] == K.FACING[k] and a["axis_source"] == "nearest_segment"
            assert abs(a["axis_deg"] - 37.0) < 0.01 and a["axis_segment_id"] == 9 and abs(a["axis_distance_m"] - 5.0) < 0.01
            assert a["rules"] == K.RULES_ID and a["heading_rule"] == f"{K.RULES_ID}:{k}:{K.FACING[k]}"
        # the hydrant is untouched
        assert np.isnan(float(out["heading"][len(kinds)])) and json.loads(out["attrs"][len(kinds)]) == {"unitid": "H1"}
        assert rep["kinds"]["bus_shelter"]["side"] == {"left": int(side == "left"), "right": int(side == "right"), "on": 0}
    # the sign convention against the geometry directly: cross > 0 is left of the digitised direction
    proj = np.array([[0.0, 0.0]]); tangent = np.array([[math.sin(math.radians(37.0)), math.cos(math.radians(37.0))]])
    lx, ly = _left_of(37.0, 5.0)
    assert K.side_of_centreline(np.array([lx]), np.array([ly]), proj, tangent)["side"] == ["left"]
    assert K.side_of_centreline(np.array([-lx]), np.array([-ly]), proj, tangent)["side"] == ["right"]
    assert K.side_of_centreline(np.array([0.0]), np.array([0.0]), proj, tangent)["side"] == ["on"]


def test_kerb_no_segment_in_reach_leaves_nan_and_says_so():
    from nycsim_pipeline.furniture import kerb as K

    cols = _kerb_cols(["bus_shelter", "bike_rack"])
    out, rep = K.apply(cols, Path("/nonexistent"), seg=_segment_along(90.0, through=(0.0, 40.0)))
    for i in range(2):
        a = json.loads(out["attrs"][i])
        assert np.isnan(float(out["heading"][i]))
        assert a["axis_source"] == "none" and "facing" not in a and "side" not in a and a["rules"] == K.RULES_ID
        assert abs(a["axis_distance_m"] - 40.0) < 0.2
    assert rep["kinds"]["bus_shelter"]["heading_nan"] == 1 and rep["kinds"]["bus_shelter"]["no_axis"]["count"] == 1
    assert rep["heading_written"] == 0


def test_kerb_keeps_a_heading_the_source_carried():
    """An OSM bike rack with direction=200 keeps 200, and its attrs say the source heading was kept."""
    from nycsim_pipeline.furniture import kerb as K

    cols = _kerb_cols(["bike_rack", "bike_rack"], _left_of(37.0, 5.0), heading=[200.0, float("nan")])
    out, rep = K.apply(cols, Path("/nonexistent"), seg=_segment_along(37.0))
    a0, a1 = json.loads(out["attrs"][0]), json.loads(out["attrs"][1])
    assert float(out["heading"][0]) == 200.0 and a0["kept_source_heading"] is True and a0["heading_source"] == "osm_direction"
    assert "facing" not in a0
    assert abs(float(out["heading"][1]) - 127.0) < 1e-3 and a1["facing"] == "toward_roadway" and a1["heading_source"] == "kerb_axis"
    assert rep["kinds"]["bike_rack"]["kept_source_heading"] == 1 and rep["kinds"]["bike_rack"]["heading_written"] == 1


def test_kerb_ignores_a_path_in_favour_of_a_street():
    """A path (rw_type 6) 3 m away is not a kerb; the street 10 m away is the axis."""
    from nycsim_pipeline.furniture import kerb as K

    path = _segment_along(120.0, through=_left_of(120.0, 3.0), segment_id=1, rw_type=6, name="ROOSEVELT I HOUSES PED PATH")
    street = _segment_along(37.0, through=_left_of(37.0, -10.0), segment_id=2, rw_type=1, name="DEKALB AV")
    cols = _kerb_cols(["bus_shelter"])
    out, rep = K.apply(cols, Path("/nonexistent"), seg=_segments(path, street))
    a = json.loads(out["attrs"][0])
    assert a["axis_segment_id"] == 2 and a["axis_rw_type"] == 1 and abs(a["axis_deg"] - 37.0) < 0.01
    assert abs(a["axis_distance_m"] - 10.0) < 0.01
    assert rep["kinds"]["bus_shelter"]["class_mask"]["nearest_segment_changed"] == 1
    # with only the path in reach the shelter has no axis, and the summary says which line was in reach
    out, rep = K.apply(_kerb_cols(["bus_shelter"]), Path("/nonexistent"), seg=path)
    assert json.loads(out["attrs"][0])["axis_source"] == "none"
    assert rep["kinds"]["bus_shelter"]["no_axis"]["only_a_non_roadway_line_within_25m"] == 1


def test_kerb_prefers_the_street_the_source_names():
    """A shelter nearer to COURT ST than to its own ATLANTIC AV takes Atlantic (axis_match = named_street);
    with no name in reach it falls back to the nearest (axis_match = nearest)."""
    from nycsim_pipeline.furniture import kerb as K

    court = _segment_along(10.0, through=_left_of(10.0, 6.0), segment_id=1, name="COURT ST")
    atlantic = _segment_along(100.0, through=_left_of(100.0, 9.0), segment_id=2, name="ATLANTIC AVE")
    seg = _segments(court, atlantic)
    out, rep = K.apply(_kerb_cols(["bus_shelter"], attrs=[{"shelter_id": "BR0049", "corner": "NW",
                                                            "on_street": "ATLANTIC AVENUE", "cross_street": "COURT STREET"}]),
                       Path("/nonexistent"), seg=seg)
    a = json.loads(out["attrs"][0])
    assert a["axis_segment_id"] == 2 and a["axis_match"] == "named_street" and abs(a["axis_deg"] - 100.0) < 0.01
    assert a["shelter_id"] == "BR0049" and a["corner"] == "NW" and a["on_street"] == "ATLANTIC AVENUE", "existing attrs survive"
    ns = rep["kinds"]["bus_shelter"]["named_street"]
    assert ns["named_street_matched"] == 1 and ns["differs_from_nearest"] == 1 and ns["axis_changed_over_30deg"] == 1
    out, rep = K.apply(_kerb_cols(["bus_shelter"], attrs=[{"shelter_id": "X", "on_street": "FULTON ST"}]), Path("/nonexistent"), seg=seg)
    a = json.loads(out["attrs"][0])
    assert a["axis_segment_id"] == 1 and a["axis_match"] == "nearest"
    assert rep["kinds"]["bus_shelter"]["named_street"]["fell_back_to_nearest"] == 1
    # the same for a bus stop sign, whose street is the first name of 'ON ST/CROSS ST'
    cols = _kerb_cols(["bus_stop_sign"]); cols["text"] = ["ATLANTIC AV/COURT ST", ""]
    out, rep = K.apply(cols, Path("/nonexistent"), seg=seg)
    assert json.loads(out["attrs"][0])["axis_segment_id"] == 2
    assert K.normalise_street("East 34th Street") == "E 34 ST" and K.normalise_street("ATLANTIC AVE.") == "ATLANTIC AV"


def test_kerb_apply_is_idempotent_and_touches_nothing_else():
    """A second pass finds no NaN among the six kinds and changes nothing; every non-kerb kind's heading and
    attrs are byte-identical before and after."""
    from nycsim_pipeline.furniture import kerb as K

    kinds = list(K.KINDS) + ["street_lamp", "hydrant", "citibike_dock"]
    cols = _kerb_cols(kinds, _left_of(37.0, 5.0), heading=[float("nan")] * len(K.KINDS) + [200.0, float("nan"), 45.0])
    before = {k: (list(v) if isinstance(v, list) else np.asarray(v).copy()) for k, v in cols.items()}
    out, rep = K.apply(cols, Path("/nonexistent"), seg=_segment_along(37.0))
    n = len(K.KINDS)
    for k in out:
        if k in ("heading", "attrs"):
            continue
        if isinstance(out[k], list):
            assert out[k] == before[k], k
        else:
            assert np.array_equal(np.asarray(out[k]), before[k], equal_nan=True), k
    assert out["attrs"][n:] == before["attrs"][n:]
    assert np.array_equal(np.asarray(out["heading"])[n:], before["heading"][n:], equal_nan=True)
    h1 = np.asarray(out["heading"]).copy(); a1 = list(out["attrs"])
    out2, rep2 = K.apply(out, Path("/nonexistent"), seg=_segment_along(37.0))
    assert np.array_equal(np.asarray(out2["heading"]), h1, equal_nan=True) and list(out2["attrs"]) == a1
    assert rep2["heading_written"] == 0 and rep2["kept_source_heading"] == 0
    assert sum(r["already_written_by_an_earlier_pass"] for r in rep2["kinds"].values()) == n


def test_kerb_rules_are_named_in_the_summary_and_in_every_written_row():
    from nycsim_pipeline.furniture import kerb as K

    out, rep = K.apply(_kerb_cols(list(K.KINDS), _left_of(37.0, 5.0)), Path("/nonexistent"), seg=_segment_along(37.0))
    assert rep["rules"] == list(K.RULES) and rep["rules_id"] == K.RULES_ID
    assert rep["facing"] == K.FACING and set(K.FACING) == set(K.KINDS)
    for k in K.KINDS:
        assert any(r.startswith(f"{k}:") or r.startswith(f"{k} and ") for r in K.RULES), k
    for i in range(len(K.KINDS)):
        assert json.loads(out["attrs"][i])["rules"] == K.RULES_ID
    # and the citibike parts now carry the side, read the same way
    from nycsim_pipeline.furniture import citibike as C
    assert any("kerb.side_of_centreline" in r for r in C.RULES)
