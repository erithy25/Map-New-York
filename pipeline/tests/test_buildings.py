"""Tests for the buildings ingest stage (DATA_CONTRACTS §5 / §5.2).

Data-dependent tests skip when ``data/processed/buildings/buildings_base.parquet`` has not been produced yet.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely

from nycsim_pipeline.buildings import schema as S
from nycsim_pipeline.buildings.facade_heading import facade_headings
from nycsim_pipeline.buildings.infer import class_floor_heights
from nycsim_pipeline.buildings.storefronts import SOURCE_DCWP, SOURCE_DOHMH, refine_kinds
from nycsim_pipeline.crs import NYC_TM
from nycsim_pipeline.paths import PROCESSED
from nycsim_pipeline.tiling import Tile

BASE = PROCESSED / "buildings" / "buildings_base.parquet"
LANDMARKS = PROCESSED / "buildings" / "landmark_footprints.parquet"
SUMMARY = PROCESSED / "buildings" / "borough_summary.json"
TILES_INDEX = PROCESSED / "buildings" / "tiles_index.json"

# DATA_CONTRACTS §5 types for the columns this stage produces (independent of schema.py so a drift is caught).
CONTRACT_TYPES: dict[str, pa.DataType] = {
    "bin": pa.int64(), "bbl": pa.int64(), "borough": pa.int8(), "footprint": pa.binary(), "ground_z": pa.float32(),
    "roof_z": pa.float32(), "height": pa.float32(), "floors": pa.int16(), "floor_height": pa.float32(),
    "ground_floor_height": pa.float32(), "year_built": pa.int16(), "bldg_class": pa.string(), "land_use": pa.int8(),
    "has_storefront": pa.bool_(), "storefront_names": pa.list_(pa.string()), "storefront_kinds": pa.list_(pa.int8()),
    "has_scaffold": pa.bool_(), "landmark_id": pa.string(), "osm_id": pa.int64(), "name": pa.string(),
    "lit_seed": pa.uint32(), "fidelity": pa.uint16(), "primary_facade_heading": pa.float32(), "address": pa.string(),
    "tile": pa.string(), "tx": pa.int32(), "ty": pa.int32(),
}
NON_GEOM = [c for c, _, _ in S.COLUMNS if c != S.GEOMETRY_COLUMN]


def _bit(fid: np.ndarray, b: S.Fidelity) -> np.ndarray:
    return (fid.astype(np.uint32) & b.mask) != 0


@pytest.fixture(scope="module")
def base_table() -> pa.Table:
    if not BASE.exists():
        pytest.skip(f"{BASE} not built")
    return pq.read_table(BASE, columns=NON_GEOM)


@pytest.fixture(scope="module")
def base_file() -> pq.ParquetFile:
    if not BASE.exists():
        pytest.skip(f"{BASE} not built")
    return pq.ParquetFile(BASE)


# ---- pure unit tests -------------------------------------------------------------------------------------------------
def test_lit_seed_deterministic_and_uint32():
    a = S.lit_seed(np.array([1015862, 1036156, 2000000]), np.array([1, 2, 3]))
    b = S.lit_seed(np.array([1015862, 1036156, 2000000]), np.array([1, 2, 3]))
    assert a.dtype == np.uint32 and np.array_equal(a, b)
    assert len(set(a.tolist())) == 3
    # same BIN, different footprint id -> different seed (placeholder BINs)
    c = S.lit_seed(np.array([2000000]), np.array([4]))
    assert c[0] != a[2]


def test_class_floor_heights_table():
    cls = np.array(["A1", "C1", "C1", "O4", "K1", "F5", "", "S2"], dtype=object)
    year = np.array([1950, 1910, 1970, 1980, 1930, 1950, 0, 1915])
    fcode = np.array([2100, 2100, 2100, 2100, 2100, 2100, 5110, 2100])
    sf = np.array([False, False, False, False, False, False, False, True])
    fh, gfh, pitch = class_floor_heights(cls, year, fcode, sf)
    assert fh.tolist() == [2.9, 3.3, 3.0, 3.9, 3.9, 4.5, 3.0, 3.3]
    assert gfh.tolist() == [2.9, 3.6, 3.2, 5.0, 4.5, 4.5, 3.0, 4.2]
    assert pitch[0] == 1.5 and pitch[1] == 0.0 and pitch[6] == 0.0


def test_facade_heading_geometry():
    a = shapely.box(0, 0, 20, 6)            # 20 m wide, street to the south, party wall to the north
    b = shapely.box(0, 6, 20, 12)           # neighbour sharing the north wall
    c = shapely.box(100, 100, 110, 110)     # isolated square, lot centroid to the east
    geoms = np.array([a, b, c], dtype=object)
    tree = shapely.STRtree(geoms)
    cx = np.array([10.0, 10.0, 105.0]); cy = np.array([3.0, 9.0, 105.0])
    lot_x = np.array([10.0, 10.0, 120.0]); lot_y = np.array([8.0, 4.0, 105.0])
    heading, method, stats = facade_headings(geoms, cx, cy, lot_x, lot_y, tree)
    assert abs(heading[0] - 180.0) < 0.5 and method[0] == S.HEADING_FREE_EDGE_LOT
    assert abs(heading[1] - 0.0) < 0.5 or abs(heading[1] - 360.0) < 0.5   # b's free long edge faces north
    assert abs(heading[2] - 270.0) < 0.5                                   # faces away from the lot centroid
    assert stats["party_wall_runs"] == 2
    # no lot centroid: longest free edge
    heading2, method2, _ = facade_headings(geoms[:1], cx[:1], cy[:1], np.array([np.nan]), np.array([np.nan]), shapely.STRtree(geoms[:1]))
    assert abs(heading2[0] - 180.0) < 0.5 or abs(heading2[0] - 0.0) < 0.5
    assert method2[0] == S.HEADING_FREE_EDGE


def test_refine_kinds():
    names = np.array(["JOE'S PIZZA", "CORNER DELI GROCERY", "RITE AID PHARMACY", "THE DEAD RABBIT BAR", "ACME WIDGETS"], dtype=object)
    kinds = np.array([3, 3, 15, 3, 15])
    src = np.array([SOURCE_DOHMH, SOURCE_DOHMH, SOURCE_DCWP, SOURCE_DOHMH, SOURCE_DCWP])
    out = refine_kinds(names, kinds, src)
    assert out.tolist() == [int(S.StorefrontKind.PIZZA), int(S.StorefrontKind.BODEGA), int(S.StorefrontKind.PHARMACY),
                            int(S.StorefrontKind.BAR), 15]


# ---- schema conformance ------------------------------------------------------------------------------------------------
def test_schema_conformance(base_file: pq.ParquetFile):
    sch = base_file.schema_arrow
    for name, typ in CONTRACT_TYPES.items():
        assert name in sch.names, f"missing contract column {name}"
        assert sch.field(name).type == typ, f"{name}: {sch.field(name).type} != {typ}"
    for name, typ, _ in S.COLUMNS:
        assert sch.field(name).type == typ
    meta = sch.metadata
    assert meta[b"nycsim.schema"].decode() == S.SCHEMA_ID
    geo = json.loads(meta[b"geo"])
    assert geo["primary_column"] == "footprint"
    assert geo["columns"]["footprint"]["encoding"] == "WKB"
    assert geo["columns"]["footprint"]["crs"]["conversion"]["parameters"][1]["value"] == -73.95
    # only columns of the contract or the appended §5.2 extension are present
    assert set(sch.names) == {c for c, _, _ in S.COLUMNS}


def test_no_nulls_in_required_columns(base_table: pa.Table):
    for name in S.REQUIRED_NO_NULL:
        if name == S.GEOMETRY_COLUMN:
            continue
        col = base_table[name]
        assert col.null_count == 0, f"{name} has nulls"
        if pa.types.is_floating(col.type):
            arr = col.to_numpy()
            assert np.isfinite(arr).all(), f"{name} has NaN/inf"


def test_geometry_valid_polygons(base_file: pq.ParquetFile):
    n = base_file.metadata.num_rows
    wkb = pq.read_table(BASE, columns=["footprint", "centroid_x", "centroid_y", "tx", "ty"])
    g = shapely.from_wkb(wkb["footprint"].to_numpy(zero_copy_only=False))
    assert len(g) == n
    assert (shapely.get_type_id(g) == 3).all(), "every footprint is a single Polygon"
    assert shapely.is_valid(g).all()
    assert (shapely.area(g) >= 1.0).all()
    c = shapely.centroid(g)
    cx, cy = shapely.get_x(c), shapely.get_y(c)
    assert np.abs(cx - wkb["centroid_x"].to_numpy()).max() < 1e-6
    assert np.abs(cy - wkb["centroid_y"].to_numpy()).max() < 1e-6
    # every row assigned to the tile whose bounds contain its centroid
    assert np.array_equal(np.floor(cx / 1000.0).astype(np.int32), wkb["tx"].to_numpy())
    assert np.array_equal(np.floor(cy / 1000.0).astype(np.int32), wkb["ty"].to_numpy())


def test_tile_names_and_bounds(base_table: pa.Table):
    tx = base_table["tx"].to_numpy(); ty = base_table["ty"].to_numpy()
    tiles = np.asarray(base_table["tile"].to_pylist())
    expect = np.char.add(np.char.add(np.char.add("t_", tx.astype(str)), "_"), ty.astype(str))
    assert np.array_equal(tiles, expect)
    cx = base_table["centroid_x"].to_numpy(); cy = base_table["centroid_y"].to_numpy()
    for t in np.unique(tiles)[:: max(1, len(np.unique(tiles)) // 25)]:
        b = Tile.parse(str(t)).bounds
        m = tiles == t
        assert (cx[m] >= b[0]).all() and (cx[m] < b[2]).all() and (cy[m] >= b[1]).all() and (cy[m] < b[3]).all()


# ---- fidelity consistency -----------------------------------------------------------------------------------------------
def test_fidelity_bits(base_table: pa.Table):
    fid = base_table["fidelity"].to_numpy()
    assert _bit(fid, S.Fidelity.FOOTPRINT_REAL).all()
    h_real, h_inf = _bit(fid, S.Fidelity.HEIGHT_REAL), _bit(fid, S.Fidelity.HEIGHT_INFERRED)
    assert (h_real ^ h_inf).all(), "exactly one of HEIGHT_REAL / HEIGHT_INFERRED"
    f_real, f_inf = _bit(fid, S.Fidelity.FLOORS_REAL), _bit(fid, S.Fidelity.FLOORS_INFERRED)
    assert (f_real ^ f_inf).all(), "exactly one of FLOORS_REAL / FLOORS_INFERRED"
    assert np.array_equal(h_real, base_table["height_source"].to_numpy() == S.SRC_LIDAR)
    assert np.array_equal(f_real, base_table["floors_source"].to_numpy() == S.SRC_PLUTO)
    assert np.array_equal(_bit(fid, S.Fidelity.YEAR_REAL), base_table["year_built"].to_numpy() > 0)
    gs = base_table["ground_source"].to_numpy()
    assert np.array_equal(_bit(fid, S.Fidelity.GROUND_REAL), (gs == S.SRC_LIDAR) | (gs == S.SRC_BSIN))
    assert np.array_equal(_bit(fid, S.Fidelity.SCAFFOLD_REAL), base_table["has_scaffold"].to_numpy())
    n_names = np.asarray([len(x) for x in base_table["storefront_names"].to_pylist()])
    assert np.array_equal(_bit(fid, S.Fidelity.SIGNAGE_REAL), n_names > 0)
    # ROOF_REAL is set here now: the buildings stage calls citygml_join.attach_roof_columns
    # before writing (ADR-013). The bits below still belong to later stages.
    for b in (S.Fidelity.MATERIAL_REAL, S.Fidelity.LANDMARK_MODEL, S.Fidelity.FACADE_INFERRED):
        assert not _bit(fid, b).any(), f"{b.name} is owned by a later stage"
    # buildings with names have has_storefront
    assert base_table["has_storefront"].to_numpy()[n_names > 0].all()
    kinds = base_table["storefront_kinds"].to_pylist()
    assert all(len(k) == n for k, n in zip(kinds, n_names))
    assert all(0 <= v <= 19 for k in kinds for v in k)


# ---- value ranges and known facts --------------------------------------------------------------------------------------
def test_value_ranges(base_table: pa.Table):
    h = base_table["height"].to_numpy(); g = base_table["ground_z"].to_numpy(); r = base_table["roof_z"].to_numpy()
    assert (h > 0).all() and h.max() < 500
    assert g.min() >= -5.0 and g.max() <= 130.0
    assert np.abs((g + h) - r).max() < 1e-3
    floors = base_table["floors"].to_numpy(); gfh = base_table["ground_floor_height"].to_numpy(); fh = base_table["floor_height"].to_numpy()
    assert (floors >= 1).all() and floors.max() <= 200
    multi = floors > 1
    assert np.abs(gfh[multi] + (floors[multi] - 1) * fh[multi] - h[multi]).max() < 0.05
    assert np.abs(gfh[~multi] - h[~multi]).max() < 1e-3
    assert (fh > 0).all() and (gfh > 0).all()
    y = base_table["year_built"].to_numpy()
    assert (((y >= 1600) & (y <= 2100)) | (y == 0)).all()
    lu = base_table["land_use"].to_numpy()
    assert lu.min() >= 0 and lu.max() <= 11
    hd = base_table["primary_facade_heading"].to_numpy()
    assert (hd >= 0).all() and (hd < 360).all()
    bo = base_table["borough"].to_numpy()
    assert bo.min() >= 1 and bo.max() <= 5
    assert np.array_equal(bo.astype(np.int64), base_table["bin"].to_numpy() // 1_000_000)
    assert (base_table["osm_id"].to_numpy() == 0).all()
    bc = np.asarray(base_table["bldg_class"].to_pylist())
    assert all(len(c) in (0, 2) for c in bc)
    assert (base_table["bbl"].to_numpy() > 1_000_000_000).all()


def test_bin_uniqueness(base_table: pa.Table):
    b = base_table["bin"].to_numpy()
    real = b[b % 1_000_000 != 0]
    assert len(np.unique(real)) == len(real), "real BINs are unique"
    # placeholder BINs (x000000 = unassigned) are the only duplicates and are few
    assert (b % 1_000_000 == 0).sum() < 20


def test_known_facts(base_table: pa.Table):
    b = base_table["bin"].to_numpy()
    i = np.nonzero(b == 1015862)[0]
    assert len(i) == 1, "Empire State Building BIN present once"
    i = int(i[0])
    assert base_table["borough"][i].as_py() == 1
    assert abs(base_table["height"][i].as_py() - 381.0) <= 5.0
    assert "Empire State" in base_table["name"][i].as_py()
    assert base_table["landmark_id"][i].as_py().startswith("LP-")
    fid = int(base_table["fidelity"][i].as_py())
    assert fid & S.Fidelity.HEIGHT_REAL.mask and fid & S.Fidelity.FLOORS_REAL.mask and fid & S.Fidelity.YEAR_REAL.mask
    assert base_table["year_built"][i].as_py() == 1931
    assert base_table["floors"][i].as_py() >= 100
    # Chrysler Building and One WTC heights (LiDAR roof field)
    j = int(np.nonzero(b == 1036156)[0][0]); assert 270 <= base_table["height"][j].as_py() <= 320
    k = int(np.nonzero(b == 1088469)[0][0]); assert 400 <= base_table["height"][k].as_py() <= 445
    assert base_table.num_rows >= 1_080_000


def test_row_count_matches_source(base_table: pa.Table):
    src = PROCESSED / "buildings" / "footprints_raw.parquet"
    if not src.exists():
        pytest.skip("footprints_raw.parquet missing")
    n_src = pq.ParquetFile(src).metadata.num_rows
    # only degenerate (< 1 m^2) parts may be dropped; multipart explosion may add rows
    assert base_table.num_rows >= n_src - 100


# ---- per-tile files -----------------------------------------------------------------------------------------------------
def test_tile_files(base_file: pq.ParquetFile):
    if not TILES_INDEX.exists():
        pytest.skip("tiles_index.json missing")
    idx = json.load(open(TILES_INDEX))["tiles"]
    # 920 of the 2,916 scope tiles hold at least one building; the rest are water, park or
    # New Jersey shoreline. The count is the real one, not a round number.
    assert len(idx) >= 900
    total = sum(v["rows"] for v in idx.values())
    assert total == base_file.metadata.num_rows
    names = sorted(idx)
    for t in names[:: max(1, len(names) // 30)]:
        p = PROCESSED / "tiles" / t / "buildings.parquet"
        assert p.exists(), p
        f = pq.ParquetFile(p)
        assert f.metadata.num_rows == idx[t]["rows"]
        assert f.schema_arrow.metadata[b"nycsim.schema"].decode() == S.SCHEMA_ID
        assert f.schema_arrow.metadata[b"nycsim.tile"].decode() == t
        for name, typ, _ in S.COLUMNS:
            assert f.schema_arrow.field(name).type == typ
        tab = f.read(columns=["tile", "centroid_x", "centroid_y"])
        assert set(tab["tile"].to_pylist()) == {t}
        bnd = Tile.parse(t).bounds
        cx = tab["centroid_x"].to_numpy(); cy = tab["centroid_y"].to_numpy()
        assert (cx >= bnd[0]).all() and (cx < bnd[2]).all() and (cy >= bnd[1]).all() and (cy < bnd[3]).all()


# ---- landmark footprints & summary --------------------------------------------------------------------------------------
def test_landmark_footprints():
    if not LANDMARKS.exists():
        pytest.skip("landmark_footprints.parquet missing")
    t = pq.read_table(LANDMARKS)
    assert t.schema.metadata[b"nycsim.schema"].decode() == "landmark_footprints/1"
    ids = t["landmark_id"].to_pylist()
    assert len(ids) == len(set(ids))
    assert "empire_state_building" in ids
    esb = t.slice(ids.index("empire_state_building"), 1)
    assert 1015862 in esb["bins"][0].as_py()
    assert abs(esb["height_m"][0].as_py() - 381.0) <= 5.0
    g = shapely.from_wkb(t["geometry"].to_numpy(zero_copy_only=False))
    assert (shapely.get_type_id(g) == 6).all() and shapely.is_valid(g).all()
    assert all(len(b) >= 1 for b in t["bins"].to_pylist())
    found = [m for m in t["match_method"].to_pylist() if m != "group_union"]
    assert len(found) >= 50
    lon = t["lon"].to_numpy(); lat = t["lat"].to_numpy()
    assert (lon > -74.3).all() and (lon < -73.6).all() and (lat > 40.4).all() and (lat < 41.0).all()


def test_borough_summary(base_table: pa.Table):
    if not SUMMARY.exists():
        pytest.skip("borough_summary.json missing")
    s = json.load(open(SUMMARY))
    assert s["schema_version"] == 1
    assert set(s["boroughs"]) == {"Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"}
    assert sum(v["buildings"] for v in s["boroughs"].values()) == base_table.num_rows == s["all"]["buildings"]
    for v in s["boroughs"].values():
        for k in ("height_median_m", "height_max_m", "pct_pluto_joined", "pct_height_real", "pct_floors_real", "pct_year_real",
                  "pct_with_storefront_names", "n_scaffold"):
            assert k in v and v[k] is not None
        assert 0 <= v["pct_pluto_joined"] <= 100
    assert s["boroughs"]["Manhattan"]["height_max_m"] > 400
