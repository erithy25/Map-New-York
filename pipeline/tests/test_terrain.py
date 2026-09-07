"""Tests for the terrain & water stage (DATA_CONTRACTS §2, §3, §4).

Pure tests (lattice algebra, PNG encoding, IDW weighting, name cleaning, tile index merging) always run.
Data-dependent tests skip when the artefact they need has not been produced yet.
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
from PIL import Image

from nycsim_pipeline.crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, TILE_SIZE_M, lonlat_to_tm
from nycsim_pipeline.paths import PROCESSED
from nycsim_pipeline.terrain import grid, index as tindex, tiles as ttiles
from nycsim_pipeline.terrain.grid import NODATA, SAMPLES, SPACING_M, Z_SCALE_M, encode_png_values, lattice_grid, quantize, tile_transform
from nycsim_pipeline.tiling import Tile, scope_tiles
from nycsim_pipeline.water.classify import clean_name, is_open_water, kind_from_planimetric

TILES_DIR = PROCESSED / "tiles"
INDEX_PARQUET = TILES_DIR / "index.parquet"
HYDRO = PROCESSED / "water" / "hydrography.parquet"
SHORE = PROCESSED / "water" / "shoreline.parquet"
STRUCT = PROCESSED / "water" / "structures.parquet"
WTILES = PROCESSED / "water" / "water_tiles.parquet"
POINTS = PROCESSED / "terrain" / "ground_points.parquet"
COVERAGE = PROCESSED / "terrain" / "coverage.json"

SOME_TILES = ["t_-1_1", "t_0_0", "t_-3_7", "t_-2_5"]


# --------------------------------------------------------------------------- lattice / encoding
def test_tile_has_inclusive_edges():
    assert SAMPLES == int(TILE_SIZE_M / SPACING_M) + 1 == 501


def test_tile_transform_puts_pixel_centres_on_even_metres():
    t = Tile(-3, 7)
    tr = tile_transform(t)
    # pixel (0,0) centre
    cx, cy = tr.c + SPACING_M / 2, tr.f - SPACING_M / 2
    assert cx == pytest.approx(t.x0)
    assert cy == pytest.approx(t.y0 + TILE_SIZE_M)
    assert (cx % SPACING_M) == 0 and (cy % SPACING_M) == 0


def test_neighbouring_tile_windows_share_a_sample_line():
    a, b = Tile(0, 0), Tile(1, 0)
    ta, tb = tile_transform(a), tile_transform(b)
    east_col_centre = ta.c + SPACING_M / 2 + (SAMPLES - 1) * SPACING_M
    west_col_centre = tb.c + SPACING_M / 2
    assert east_col_centre == pytest.approx(west_col_centre)


def test_lattice_grid_is_aligned_and_inclusive():
    tr, w, h = lattice_grid(101.0, -37.0, 507.0, 63.0)
    assert (tr.c + SPACING_M / 2) % SPACING_M == 0
    assert w == int((508 - 100) / SPACING_M) + 1
    assert h == int((64 + 38) / SPACING_M) + 1


def test_quantize_snaps_to_global_quantum():
    z = np.array([0.0, 1.0011, -2.34567, 125.6789])
    q = quantize(z)
    assert np.allclose(np.round(q / Z_SCALE_M) - q / Z_SCALE_M, 0, atol=1e-9)
    assert np.max(np.abs(q - z)) <= Z_SCALE_M / 2 + 1e-12


def test_encode_png_values_round_trip_is_exact_for_quantized_input():
    rng = np.random.default_rng(7)
    z = quantize(rng.uniform(-20.0, 130.0, size=(64, 64)))
    vals, z_min, scale = encode_png_values(z)
    assert scale == Z_SCALE_M
    back = z_min + vals.astype(np.float64) * scale
    assert np.max(np.abs(back - z)) < 1e-9


def test_encode_png_values_rejects_non_finite():
    with pytest.raises(ValueError):
        encode_png_values(np.array([0.0, np.nan]))


def test_png_scale_covers_the_relief_of_a_single_tile():
    """z_min is per tile, so the 16-bit budget must cover the worst *tile* span, not the city's range.

    The measured worst case over the 2,916 scope tiles is 140.2 m (t_2_26, Westchester hills), against a
    163.8 m budget at the 2.5 mm quantum. A larger quantum is refused by ``tiles.build_tile`` because two
    tiles encoded at different quanta would not share bit-identical edges.
    """
    assert 65535 * Z_SCALE_M > 145.0


# --------------------------------------------------------------------------- densification maths
def test_idw_weight_vanishes_at_the_radius():
    r = ttiles.IDW_RADIUS_M
    d = np.array([0.5, 1.0, 7.5, r - 1e-9, r])
    w = ((r - d) / (r * d)) ** 2
    assert w[0] > w[1] > w[2] > w[3]
    assert w[3] == pytest.approx(0.0, abs=1e-16)


def test_stamp_covers_the_whole_radius():
    # a point may sit up to half a sample from its nearest lattice point in each axis
    assert ttiles.STAMP_K * SPACING_M >= ttiles.IDW_RADIUS_M + SPACING_M / 2


def test_densify_pulls_the_surface_onto_a_survey_point():
    n = 64
    tr = tile_transform(Tile(0, 0), 0)
    z = np.full((n, n), 10.0)
    valid = np.ones((n, n), dtype=bool)
    x0c, y0c = tr.c + SPACING_M / 2, tr.f - SPACING_M / 2
    px, py = x0c + 10 * SPACING_M, y0c - 10 * SPACING_M
    idx = _PointsStub(np.array([px]), np.array([py]), np.array([11.5], dtype=np.float32), np.array([0], dtype=np.uint8))
    bounds = (x0c - 1, y0c - n * SPACING_M, x0c + n * SPACING_M, y0c + 1)
    out, stats = ttiles.densify(z, valid, tr, (n, n), idx, bounds)
    assert stats["used_spot"] == 1 and stats["rejected_spot"] == 0
    assert out[10, 10] == pytest.approx(11.5, abs=1e-6)      # exactly on the point
    assert out[10, 18] == pytest.approx(10.0, abs=1e-9)      # 16 m away: outside the radius
    assert 10.0 < out[10, 13] < 11.5                          # 6 m away: partial pull


def test_densify_rejects_outliers_beyond_three_metres():
    n = 32
    tr = tile_transform(Tile(0, 0), 0)
    z = np.full((n, n), 10.0)
    valid = np.ones((n, n), dtype=bool)
    x0c, y0c = tr.c + SPACING_M / 2, tr.f - SPACING_M / 2
    idx = _PointsStub(np.array([x0c + 8 * SPACING_M]), np.array([y0c - 8 * SPACING_M]),
                      np.array([25.0], dtype=np.float32), np.array([1], dtype=np.uint8))
    bounds = (x0c - 1, y0c - n * SPACING_M, x0c + n * SPACING_M, y0c + 1)
    out, stats = ttiles.densify(z, valid, tr, (n, n), idx, bounds)
    assert stats["rejected_bldg"] == 1 and stats["used_bldg"] == 0
    assert np.all(out == 10.0)


# --------------------------------------------------------------------------- sub-datum repair
def _flat_window(n=64, z0=4.0):
    tr = tile_transform(Tile(0, 0), 0)
    z = np.full((n, n), z0)
    valid = np.ones((n, n), dtype=bool)
    water = np.zeros((n, n), dtype=bool)
    water_z = np.full((n, n), np.nan, dtype=np.float32)
    deck = np.zeros((n, n), dtype=bool)
    return tr, z, valid, water, water_z, deck


def test_sub_datum_pit_beside_open_water_becomes_the_water_surface():
    """A pier slip: the 1 m DEM drops to the harbour bed a few metres from a water polygon."""
    tr, z, valid, water, water_z, deck = _flat_window()
    water[:, 40:] = True                       # open water to the east
    water_z[:, 40:] = 0.0
    z[30:33, 36:39] = -19.0                    # slip between the piers, 8-2 m from the water edge
    pts = _PointsStub(np.zeros(0), np.zeros(0), np.zeros(0, np.float32), np.zeros(0, np.uint8))
    out, st = ttiles.repair_sub_datum(z, valid, water, deck, water_z, np.zeros_like(valid), pts, tr)
    assert st["px_below_floor"] == 9 and st["px_to_water"] == 9 and st["px_filled_idw"] == 0
    assert np.allclose(out[30:33, 36:39], 0.0)
    assert out.min() >= ttiles.LAND_FLOOR_M


def test_sub_datum_pit_inland_is_closed_from_its_rim():
    """A tunnel mouth / construction pit far from water is interpolated from the sound samples around it."""
    tr, z, valid, water, water_z, deck = _flat_window(z0=6.0)
    z[20:24, 20:24] = -25.0
    pts = _PointsStub(np.zeros(0), np.zeros(0), np.zeros(0, np.float32), np.zeros(0, np.uint8))
    out, st = ttiles.repair_sub_datum(z, valid, water, deck, water_z, np.zeros_like(valid), pts, tr)
    assert st["px_below_floor"] == 16 and st["px_to_water"] == 0
    assert st["px_filled_idw"] == 16
    assert np.allclose(out[20:24, 20:24], 6.0, atol=1e-6)     # rim is flat at 6 m
    assert out.min() >= ttiles.LAND_FLOOR_M


def test_sub_datum_kept_where_a_survey_point_corroborates_it():
    """The Battery Underpass really is below the datum: a survey point inside the pit protects it."""
    tr, z, valid, water, water_z, deck = _flat_window()
    z[30:33, 30:33] = -4.0
    low = np.zeros_like(valid)
    low[29:34, 29:34] = True                   # low_survey_mask around a -4 m spot elevation
    pts = _PointsStub(np.zeros(0), np.zeros(0), np.zeros(0, np.float32), np.zeros(0, np.uint8))
    out, st = ttiles.repair_sub_datum(z, valid, water, deck, water_z, low, pts, tr)
    assert st["px_kept_surveyed"] == 9 and st["px_to_water"] == 0 and st["px_filled_idw"] == 0
    assert np.allclose(out[30:33, 30:33], -4.0)


def test_low_survey_mask_covers_only_the_radius_of_a_sub_floor_point():
    tr = tile_transform(Tile(0, 0), 0)
    x0c, y0c = tr.c + SPACING_M / 2, tr.f - SPACING_M / 2
    pts = _PointsStub(np.array([x0c + 10 * SPACING_M, x0c + 40 * SPACING_M]),
                      np.array([y0c - 10 * SPACING_M, y0c - 40 * SPACING_M]),
                      np.array([-3.5, 12.0], dtype=np.float32), np.array([0, 0], dtype=np.uint8))
    n = 64
    bounds = (x0c - 1, y0c - n * SPACING_M, x0c + n * SPACING_M, y0c + 1)
    m = ttiles.low_survey_mask(pts, tr, (n, n), bounds)
    assert m[10, 10] and m[10, 17]                       # 0 m and 14 m from the -3.5 m point
    assert not m[10, 19]                                 # 18 m away: outside the fill radius
    assert not m[40, 40]                                 # the +12 m point never protects anything


def test_survey_fill_uses_the_nearest_points_and_ignores_the_window():
    tr = tile_transform(Tile(0, 0), 0)
    x0c, y0c = tr.c + SPACING_M / 2, tr.f - SPACING_M / 2
    pts = _PointsStub(np.array([x0c, x0c + 200.0]), np.array([y0c, y0c]),
                      np.array([5.0, 90.0], dtype=np.float32), np.array([0, 0], dtype=np.uint8))
    v = ttiles.survey_fill(pts, np.array([x0c + 4.0]), np.array([y0c]))
    assert v[0] == pytest.approx(5.0, abs=0.5)          # dominated by the point 4 m away
    far = ttiles.survey_fill(pts, np.array([x0c + 5000.0]), np.array([y0c]))
    assert not np.isfinite(far[0])                       # nothing within 240 m -> caller uses the datum


class _PointsStub:
    """Minimal stand-in for points.PointIndex."""

    def __init__(self, x, y, z, kind):
        self.x, self.y, self.z, self.kind = x, y, z, kind

    def query_bbox(self, xmin, ymin, xmax, ymax):
        m = (self.x >= xmin) & (self.x <= xmax) & (self.y >= ymin) & (self.y <= ymax)
        return np.flatnonzero(m)


# --------------------------------------------------------------------------- water classification
def test_planimetric_feature_codes_map_to_contract_kinds():
    assert kind_from_planimetric(2600, "") == "lake"
    assert kind_from_planimetric(2660, "UPPER NEW YORK BAY") == "bay"
    assert kind_from_planimetric(2630, "GOWANUS CANAL") == "canal"
    assert kind_from_planimetric(2660, "ATLANTIC OCEAN") == "ocean"
    assert kind_from_planimetric(2640, "anything") == "marsh"
    with pytest.raises(ValueError):
        kind_from_planimetric(1234, "")


def test_clean_name_drops_placeholders_including_nan():
    assert clean_name(float("nan")) == ""
    assert clean_name(None) == ""
    assert clean_name(" UNSET ") == ""
    assert clean_name("HUDSON RIVER") == "HUDSON RIVER"


def test_marsh_is_not_open_water():
    assert not is_open_water("marsh")
    assert all(is_open_water(k) for k in ("river", "bay", "ocean", "lake", "pond", "canal", "basin"))


# --------------------------------------------------------------------------- tiles/index.parquet
def test_index_table_preserves_other_stages_counts():
    tiles = [Tile(0, 0), Tile(1, 0)]
    prev = pa.table({"tile": pa.array(["t_0_0", "t_1_0"]), "n_buildings": pa.array([37, 0], pa.int32()),
                     "n_road_segments": pa.array([5, 0], pa.int32()), "n_props": pa.array([0, 9], pa.int32()),
                     "n_trees": pa.array([0, 0], pa.int32())})
    terrain = {"t_0_0": {"z_min": 1.0, "z_max": 9.0, "has_water": False, "has_land": True}}
    tbl = tindex.build_table(tiles, terrain, prev)
    d = tbl.to_pydict()
    assert d["n_buildings"] == [37, 0]
    assert d["n_props"] == [0, 9]
    assert d["has_terrain"] == [True, False]
    assert d["z_max"][0] == pytest.approx(9.0)
    assert d["z_min"][1] is None


def test_index_lock_is_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(tindex, "LOCK_PATH", tmp_path / "index.lock")
    with tindex.index_lock():
        with pytest.raises(TimeoutError):
            with tindex.index_lock(timeout_s=0.5):
                pass


# --------------------------------------------------------------------------- produced artefacts
@pytest.mark.skipif(not COVERAGE.exists(), reason="coverage audit not run")
def test_every_borough_is_fully_covered_by_the_source_grid():
    doc = json.loads(COVERAGE.read_text())
    for name, b in doc["boroughs"].items():
        assert b["coverage_pct"] == pytest.approx(100.0, abs=0.01), f"{name} coverage {b['coverage_pct']}"
        assert b["void_px"] == 0


@pytest.mark.skipif(not POINTS.exists(), reason="ground point cache not built")
def test_ground_points_are_sorted_and_plausible():
    t = pq.read_table(POINTS)
    assert (pq.read_schema(POINTS).metadata or {}).get(b"nycsim.schema") == b"terrain.ground_points/1"
    y = t.column("y").to_numpy(zero_copy_only=False)
    assert np.all(np.diff(y) >= 0), "points must be in global (y, x) order for reproducible sums"
    z = t.column("z").to_numpy(zero_copy_only=False)
    assert z.min() > -60.0 and z.max() < 400.0
    assert t.num_rows > 1_200_000


@pytest.mark.skipif(not (TILES_DIR / "t_0_0" / "terrain.png").exists(), reason="terrain tiles not built")
@pytest.mark.parametrize("name", SOME_TILES)
def test_tile_png_and_json_match_the_contract(name):
    d = TILES_DIR / name
    if not (d / "terrain.png").exists():
        pytest.skip(f"{name} not built")
    doc = json.loads((d / "terrain.json").read_text())
    assert doc["schema_version"] == 1
    assert doc["samples"] == SAMPLES and doc["spacing_m"] == SPACING_M
    assert doc["z_scale_m"] == Z_SCALE_M
    assert doc["water_level_m"] == 0.0
    assert doc["sources"], "at least one source must be named"
    img = np.asarray(Image.open(d / "terrain.png"))
    assert img.dtype == np.uint16 and img.shape == (SAMPLES, SAMPLES)
    z = img.astype(np.float64) * doc["z_scale_m"] + doc["z_min_m"]
    assert np.all(np.isfinite(z))
    assert z.min() == pytest.approx(doc["z_min_m"], abs=1e-6)
    assert z.max() == pytest.approx(doc["z_max_m"], abs=1e-6)
    assert sum(doc["px"][k] for k in ("3dep_1m", "3dep_19", "3dep_13", "void_filled_sea")) <= SAMPLES * SAMPLES


@pytest.mark.skipif(not (TILES_DIR / "t_0_0" / "terrain.png").exists(), reason="terrain tiles not built")
def test_adjacent_tiles_share_identical_edges():
    from nycsim_pipeline.terrain.verify import check_seams
    res = check_seams(["t_-1_0", "t_0_0", "t_1_0", "t_-1_1", "t_0_1", "t_1_1"])
    assert res["pairs_checked"] >= 4
    assert res["max_edge_difference_m"] <= 0.001


@pytest.mark.skipif(not (TILES_DIR / "t_0_0" / "terrain.png").exists(), reason="terrain tiles not built")
def test_sample_z_matches_the_stored_grid_and_is_continuous_across_a_seam():
    from nycsim_pipeline.terrain.segment_z import ZSampler
    s = ZSampler(missing="nan")
    t = Tile(0, 0)
    doc = json.loads((TILES_DIR / t.name / "terrain.json").read_text())
    img = np.asarray(Image.open(TILES_DIR / t.name / "terrain.png"))
    z = img.astype(np.float64) * doc["z_scale_m"] + doc["z_min_m"]
    # exact lattice point (row 100 from north, column 200)
    x = t.x0 + 200 * SPACING_M
    y = t.y0 + TILE_SIZE_M - 100 * SPACING_M
    assert s.sample(x, y) == pytest.approx(z[100, 200], abs=1e-6)
    # a point 1 mm either side of the shared eastern edge
    xe = t.x0 + TILE_SIZE_M
    a = s.sample(xe - 0.001, y)
    b = s.sample(xe + 0.001, y)
    if np.isfinite(a) and np.isfinite(b):
        assert abs(a - b) < 0.05


@pytest.mark.skipif(not HYDRO.exists(), reason="water stage not run")
def test_hydrography_contract_columns_and_named_bodies():
    from nycsim_pipeline.contracts import validate_parquet
    assert validate_parquet("hydrography", HYDRO) == []
    t = pq.read_table(HYDRO, columns=["name", "kind", "tidal", "water_id", "is_open_water"])
    names = {n.upper() for n in t.column("name").to_pylist() if n}
    for expected in ("HUDSON RIVER", "EAST RIVER", "HARLEM RIVER", "UPPER NEW YORK BAY", "LOWER NEW YORK BAY",
                     "JAMAICA BAY", "NEWTOWN CREEK", "GOWANUS CANAL", "BRONX RIVER", "KILL VAN KULL",
                     "ARTHUR KILL", "LONG ISLAND SOUND", "ATLANTIC OCEAN"):
        assert expected in names, f"{expected} missing from hydrography names"
    wid = np.asarray(t.column("water_id").to_pylist())
    assert len(set(wid.tolist())) == len(wid), "water_id must be unique"
    assert set(t.column("kind").to_pylist()) <= {"river", "bay", "ocean", "lake", "pond", "canal", "basin", "marsh"}


@pytest.mark.skipif(not HYDRO.exists(), reason="water stage not run")
def test_tidal_bodies_sit_at_the_datum_and_inland_bodies_do_not():
    t = pq.read_table(HYDRO, columns=["tidal", "level_mode", "water_z_m", "name"]).to_pydict()
    tid = [i for i, v in enumerate(t["tidal"]) if v]
    assert tid, "no tidal bodies"
    for i in tid:
        assert t["level_mode"][i] == "tidal"
        assert t["water_z_m"][i] == pytest.approx(0.0)
    res = [i for i, n in enumerate(t["name"]) if n and "RESERVOIR" in n.upper()]
    assert res, "no reservoir in the hydrography"
    assert any((t["water_z_m"][i] or 0) > 5.0 for i in res), "every reservoir was flattened to sea level"


@pytest.mark.skipif(not SHORE.exists() or not STRUCT.exists(), reason="water stage not run")
def test_shoreline_and_structure_kinds_are_from_the_contract():
    sl = pq.read_table(SHORE, columns=["kind"]).column("kind").to_pylist()
    assert set(sl) <= {"natural", "bulkhead", "pier", "riprap"}
    st = pq.read_table(STRUCT, columns=["kind", "deck_z_m"])
    assert set(st.column("kind").to_pylist()) <= {"pier", "dock", "wharf", "jetty", "seawall"}
    z = np.asarray(st.column("deck_z_m").to_pylist(), dtype=float)
    assert np.isfinite(z).all()


@pytest.mark.skipif(not WTILES.exists(), reason="water stage not run")
def test_water_tiles_cover_every_scope_tile_once():
    t = pq.read_table(WTILES, columns=["tile", "has_open_water"])
    names = t.column("tile").to_pylist()
    assert len(names) == len(set(names)) == len(scope_tiles())


@pytest.mark.skipif(not INDEX_PARQUET.exists(), reason="tiles/index.parquet not written")
def test_tiles_index_matches_the_contract():
    from nycsim_pipeline.contracts import validate_parquet
    assert validate_parquet("tiles_index", INDEX_PARQUET) == []
    t = pq.read_table(INDEX_PARQUET)
    d = t.to_pydict()
    assert len(d["tile"]) == len(scope_tiles())
    assert all(v for v in d["has_terrain"]), "every scope tile must carry terrain"
    for i, name in enumerate(d["tile"]):
        tile = Tile.parse(name)
        assert d["x0"][i] == tile.x0 and d["y0"][i] == tile.y0
        assert set(d["borough_codes"][i] or []) <= {0, 1, 2, 3, 4, 5, 6, 7}
        assert d["z_min"][i] is not None and d["z_max"][i] >= d["z_min"][i]


@pytest.mark.skipif(not INDEX_PARQUET.exists(), reason="tiles/index.parquet not written")
def test_known_manhattan_tile_is_manhattan():
    t = pq.read_table(INDEX_PARQUET, columns=["tile", "borough_codes"]).to_pydict()
    codes = dict(zip(t["tile"], t["borough_codes"]))
    x, y = lonlat_to_tm(-73.9857, 40.7484)   # Empire State Building
    tile = Tile(math.floor(x / TILE_SIZE_M), math.floor(y / TILE_SIZE_M))
    assert 1 in codes[tile.name]
    x, y = lonlat_to_tm(-74.1502, 40.5795)   # Todt Hill, Staten Island
    tile = Tile(math.floor(x / TILE_SIZE_M), math.floor(y / TILE_SIZE_M))
    assert 5 in codes[tile.name]


@pytest.mark.skipif(not (TILES_DIR / "t_0_0" / "terrain.json").exists(), reason="terrain tiles not built")
def test_no_published_tile_falls_below_the_deepest_surveyed_ground():
    """Extremes guard. Nothing anywhere may sit below -6 m (the deepest surveyed ground in NYC is the
    Battery Underpass at -4.03 m). The upper bound is 135 m over the five boroughs (Todt Hill is 124.9 m)
    and 220 m over the rest of the scope box, which clips the New Jersey Watchung ridge (real, 170-210 m
    in the 1/3" DEM) and the lower Westchester hills."""
    from nycsim_pipeline.terrain.verify import EXTREME_HIGH_M, EXTREME_HIGH_SCOPE_M, EXTREME_LOW_M
    nyc = set()
    if INDEX_PARQUET.exists():
        t = pq.read_table(INDEX_PARQUET, columns=["tile", "borough_codes"]).to_pydict()
        nyc = {n for n, cs in zip(t["tile"], t["borough_codes"]) if cs and set(cs) & {1, 2, 3, 4, 5}}
    lows, highs_nyc, highs_all = [], [], []
    for d in sorted(TILES_DIR.glob("t_*/terrain.json")):
        doc = json.loads(d.read_text())
        lows.append((doc["z_min_m"], doc["tile"]))
        highs_all.append((doc["z_max_m"], doc["tile"]))
        if doc["tile"] in nyc:
            highs_nyc.append((doc["z_max_m"], doc["tile"]))
    assert lows, "no tiles built"
    lo, hi = min(lows), max(highs_all)
    assert lo[0] >= EXTREME_LOW_M, f"tile {lo[1]} reaches {lo[0]:.2f} m"
    assert hi[0] <= EXTREME_HIGH_SCOPE_M, f"tile {hi[1]} reaches {hi[0]:.2f} m"
    if highs_nyc:
        hn = max(highs_nyc)
        assert hn[0] <= EXTREME_HIGH_M, f"NYC tile {hn[1]} reaches {hn[0]:.2f} m"


@pytest.mark.skipif(not (TILES_DIR / "t_-11_-8" / "terrain.json").exists(), reason="terrain tiles not built")
def test_known_sub_datum_artefacts_are_repaired_and_accounted():
    """The four deepest source artefacts (Stapleton pier slip, Hudson Line portal, Sunnyside Yard portal,
    Brooklyn Navy Yard dry docks) must be closed, and each tile must say what it did."""
    for name, source_floor in (("t_-11_-8", -21.0), ("t_-5_6", -26.0), ("t_1_5", -19.0), ("t_-2_0", -12.0)):
        f = TILES_DIR / name / "terrain.json"
        if not f.exists():
            pytest.skip(f"{name} not built")
        doc = json.loads(f.read_text())
        sd = doc["sub_datum"]
        assert sd["z_min_before_m"] <= source_floor, f"{name} source minimum changed"
        assert doc["z_min_m"] >= ttiles.LAND_FLOOR_M - 1e-6, f"{name} still holds a sub-datum pit"
        repaired = sd["px_to_water"] + sd["px_filled_idw"] + sd["px_filled_survey"] + sd["px_filled_datum"]
        assert repaired == sd["px_below_floor"] - sd["px_kept_surveyed"] > 0
        assert "sub_datum_repair" in doc["sources"]


@pytest.mark.skipif(not (PROCESSED / "terrain" / "overview_16m.tif").exists(), reason="overview not built")
def test_overview_is_a_strict_decimation_of_the_tiles():
    """Every 16 m overview sample must equal the published 2 m sample at the same coordinate, exactly."""
    import rasterio
    with rasterio.open(PROCESSED / "terrain" / "overview_16m.tif") as ds:
        assert ds.dtypes[0] == "float32"
        assert ds.res == (16.0, 16.0)
        assert (ds.transform.c + 8.0) % 16.0 == 0        # pixel centres on the 16 m lattice
        a = ds.read(1)
        assert np.isfinite(a).all(), "overview must have no voids inside the scope"
        tr = ds.transform
    rng = np.random.default_rng(11)
    checked = 0
    for _ in range(200):
        row = int(rng.integers(0, a.shape[0]))
        col = int(rng.integers(0, a.shape[1]))
        x = tr.c + 16.0 * col + 8.0
        y = tr.f - 16.0 * row - 8.0
        tile = Tile(math.floor(x / TILE_SIZE_M), math.floor(y / TILE_SIZE_M))
        d = TILES_DIR / tile.name
        if not (d / "terrain.png").exists():
            continue
        doc = json.loads((d / "terrain.json").read_text())
        img = np.asarray(Image.open(d / "terrain.png")).astype(np.float64)
        z = img * doc["z_scale_m"] + doc["z_min_m"]
        c = int(round((x - tile.x0) / SPACING_M))
        r = int(round((tile.y0 + TILE_SIZE_M - y) / SPACING_M))
        # the overview is float32, so equality holds to the float32 resolution at these magnitudes
        # (2e-5 m at 200 m), four orders of magnitude below the 2.5 mm elevation quantum
        assert a[row, col] == pytest.approx(z[r, c], abs=1e-4), f"{tile.name} ({r},{c})"
        checked += 1
    assert checked >= 100
