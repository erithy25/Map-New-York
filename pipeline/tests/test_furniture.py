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
