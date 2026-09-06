"""Verification tests for the New Jersey buildings stage (`buildings/nj_tiles.py` + `--source nj`).

These are written to fail if the work is wrong, not to restate that it was done:

* every New Jersey building sits inside the tile it is filed under, and its ``tile``/``tx``/``ty``
  columns agree with its own geometry;
* no New Jersey building lands inside the five boroughs — checked against the city's own borough
  boundary polygons, by centroid *and* by polygon overlap;
* the New Jersey table never contaminates the New York one: nine tiles carry both files, and they
  share no row, no key and no borough code;
* the fidelity bitfield matches the source columns **row for row** — HEIGHT_REAL exactly where the
  source published a height, HEIGHT_INFERRED exactly where it did not, and the eight bits New Jersey
  has no source for clear on all 231,399 rows;
* ground elevation really comes from the project's terrain: re-sampled independently through
  ``terrain.segment_z`` and compared to the published column;
* the shells' triangle counts and bounding boxes are consistent with the footprints they came from,
  and each shell spans exactly ``ground_z`` to ``roof_z``.

Run: ``python3 -m pytest tests/test_nj_buildings.py -v``
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import shapely

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "buildings"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))

from nycsim_pipeline.buildings import nj_tiles as nj  # noqa: E402
from nycsim_pipeline.buildings import schema as S  # noqa: E402
from nycsim_pipeline.crs import NYC_TM, TILE_SIZE_M  # noqa: E402
from nycsim_pipeline.paths import BLENDER_OUT, PROCESSED, RAW  # noqa: E402
from nycsim_pipeline.tiling import Tile  # noqa: E402

TILES_DIR = PROCESSED / "tiles"
SOURCE_PARQUET = nj.SOURCE_PARQUET
BOROUGH_BOUNDARIES = RAW / "nyc_opendata" / "borough_boundaries.geojson"
SHELL_TILES = ["t_-8_3", "t_-8_2", "t_-9_5"]      # Newport / Jersey City waterfront, Bergen fabric
SAMPLE_BUILDINGS = 40
IOU_MIN = 0.97
HEIGHT_TOL_M = 0.01
GROUND_TOL_M = 0.01

_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
              5125: ("I", 4), 5126: ("f", 4)}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def nj_tile_files() -> list[Path]:
    return sorted(TILES_DIR.glob(f"*/{nj.TILE_FILENAME}"))


@pytest.fixture(scope="session")
def tile_files() -> list[Path]:
    files = nj_tile_files()
    if not files:
        pytest.skip("the New Jersey buildings stage has not been run")
    return files


@pytest.fixture(scope="session")
def all_rows(tile_files):
    """Every published New Jersey row, with its geometry, as one arrow table + shapely array."""
    import pyarrow as pa

    tabs = [pq.read_table(p) for p in tile_files]
    table = pa.concat_tables(tabs, promote_options="none")
    geoms = shapely.from_wkb(table["footprint"].to_numpy(zero_copy_only=False))
    return table, geoms


@pytest.fixture(scope="session")
def source_rows():
    if not SOURCE_PARQUET.exists():
        pytest.skip(f"{SOURCE_PARQUET} missing")
    return pq.read_table(SOURCE_PARQUET, columns=["build_id", "height_m", "area_m2", "occ_class", "county"])


# --------------------------------------------------------------------------- the table itself
def test_every_tile_file_declares_the_new_jersey_schema_and_its_own_tile(tile_files):
    for p in tile_files:
        meta = {k.decode(): v.decode() for k, v in pq.ParquetFile(p).metadata.metadata.items()}
        assert meta["nycsim.schema"] == nj.SCHEMA_ID, p
        assert meta["nycsim.tile"] == p.parent.name, p
        assert meta["nycsim.borough"] == str(nj.BOROUGH_NJ), p
        assert meta["nycsim.license"] == nj.LICENSE, p
        assert int(meta["nycsim.rows"]) == pq.ParquetFile(p).metadata.num_rows, p
        geo = json.loads(meta["geo"])
        assert geo["primary_column"] == "footprint", p
        col = geo["columns"]["footprint"]
        assert col["encoding"] == "WKB" and col["edges"] == "planar", p
        assert NYC_TM.equals(col["crs"]), f"{p}: geometry CRS is not NYC_TM"


def test_schema_columns_and_types_match_the_declared_schema(tile_files, all_rows):
    table, _ = all_rows
    want = nj.arrow_schema()
    assert [f.name for f in table.schema] == [f.name for f in want]
    for got, exp in zip(table.schema, want):
        assert got.type == exp.type, f"{got.name}: {got.type} != {exp.type}"
    for name in table.schema.names:
        assert table[name].null_count == 0, f"{name} has nulls"


def test_every_building_sits_inside_the_tile_it_is_filed_under(tile_files):
    """Filed by centroid (the New York convention), so the centroid must be in the tile bounds."""
    bad: list[str] = []
    for p in tile_files:
        t = Tile.parse(p.parent.name)
        x0, y0, x1, y1 = t.bounds
        tab = pq.read_table(p, columns=["bin", "tile", "tx", "ty", "centroid_x", "centroid_y", "footprint"])
        cx = tab["centroid_x"].to_numpy()
        cy = tab["centroid_y"].to_numpy()
        out = (cx < x0) | (cx >= x1) | (cy < y0) | (cy >= y1)
        if out.any():
            bad.append(f"{p.parent.name}: {int(out.sum())} centroids outside {t.bounds}")
        tiles = np.asarray(tab["tile"].to_pylist())
        if not (tiles == t.name).all():
            bad.append(f"{p.parent.name}: tile column disagrees with the file location")
        if not (tab["tx"].to_numpy() == t.tx).all() or not (tab["ty"].to_numpy() == t.ty).all():
            bad.append(f"{p.parent.name}: tx/ty columns disagree with the tile name")
        # the centroid the file publishes must be the centroid of the geometry it publishes
        g = shapely.from_wkb(tab["footprint"].to_numpy(zero_copy_only=False))
        c = shapely.centroid(g)
        d = np.hypot(shapely.get_x(c) - cx, shapely.get_y(c) - cy)
        if d.max() > 1e-6:
            bad.append(f"{p.parent.name}: centroid column is not the geometry centroid (max {d.max():.3g} m)")
    assert not bad, "\n".join(bad[:20])


def test_footprints_only_cross_a_tile_edge_by_their_own_size(all_rows):
    """A footprint may cross the tile edge — the Newport Centre and the Newark Airport hangars are
    bigger than a tile is wide — but never further than the building itself measures.  A row filed
    against the wrong tile shows up here even when its centroid test passes.
    """
    table, geoms = all_rows
    tx = table["tx"].to_numpy().astype(np.float64) * TILE_SIZE_M
    ty = table["ty"].to_numpy().astype(np.float64) * TILE_SIZE_M
    xmin, ymin, xmax, ymax = shapely.bounds(geoms).T
    w, h = xmax - xmin, ymax - ymin
    over_x = np.maximum(tx - xmin, xmax - (tx + TILE_SIZE_M))
    over_y = np.maximum(ty - ymin, ymax - (ty + TILE_SIZE_M))
    assert (over_x <= w + 1e-6).all() and (over_y <= h + 1e-6).all(), "a footprint is filed against the wrong tile"
    assert max(w.max(), h.max()) < 2000.0, f"a footprint spans {max(w.max(), h.max()):.0f} m"
    big = int(((over_x > 0) | (over_y > 0)).sum())
    assert big < 0.05 * len(w), f"{big} of {len(w)} footprints cross a tile edge"


def test_no_new_jersey_building_lands_inside_the_five_boroughs(all_rows):
    """Checked against the city's own borough polygons, by centroid and by area overlap."""
    if not BOROUGH_BOUNDARIES.exists():
        pytest.skip(f"{BOROUGH_BOUNDARIES} missing")
    import pyogrio

    table, geoms = all_rows
    gdf = pyogrio.read_dataframe(BOROUGH_BOUNDARIES)
    boro = shapely.union_all(shapely.set_precision(
        np.asarray(gdf.to_crs(NYC_TM).geometry.values, dtype=object), 0.0))
    cx = table["centroid_x"].to_numpy()
    cy = table["centroid_y"].to_numpy()
    pts = shapely.points(cx, cy)
    inside = shapely.contains(boro, pts)
    assert not inside.any(), (
        f"{int(inside.sum())} New Jersey centroids fall inside the five boroughs, "
        f"first at {cx[inside][:3]}, {cy[inside][:3]}")
    # and no footprint may overlap the city by a meaningful area either
    tree = shapely.STRtree(geoms)
    hit = tree.query(boro, predicate="intersects")
    overlap = np.array([shapely.area(shapely.intersection(geoms[i], boro)) for i in hit]) if len(hit) else np.zeros(0)
    assert (overlap < 1.0).all(), (
        f"{int((overlap >= 1.0).sum())} New Jersey footprints overlap the five boroughs, "
        f"largest {overlap.max():.1f} m^2")


def test_the_new_jersey_table_never_contaminates_the_new_york_one(tile_files):
    """Nine tiles carry both files.  They must share no key, no row and no borough code."""
    shared = [p for p in tile_files if (p.parent / "buildings.parquet").exists()]
    assert shared, "no tile carries both tables — the separation is untested"
    for p in shared:
        njt = pq.read_table(p, columns=["bin", "borough"])
        nyc = pq.read_table(p.parent / "buildings.parquet", columns=["bin", "borough"])
        assert set(np.unique(njt["borough"].to_numpy())) == {nj.BOROUGH_NJ}, p
        assert nj.BOROUGH_NJ not in set(np.unique(nyc["borough"].to_numpy())), (
            f"{p.parent.name}/buildings.parquet carries borough {nj.BOROUGH_NJ} rows")
        overlap = set(njt["bin"].to_pylist()) & set(nyc["bin"].to_pylist())
        assert not overlap, f"{p.parent.name}: {len(overlap)} keys shared between the two tables"
    # and the New York table was not rewritten by this stage
    nyc_schema = pq.ParquetFile(shared[0].parent / "buildings.parquet").metadata.metadata
    assert nyc_schema[b"nycsim.schema"] == S.SCHEMA_ID.encode()


# --------------------------------------------------------------------------- fidelity
def test_fidelity_bits_match_the_source_columns_row_for_row(all_rows, source_rows):
    table, _ = all_rows
    src_id = source_rows["build_id"].to_numpy()
    src_h = source_rows["height_m"].to_numpy(zero_copy_only=False).astype(np.float64)
    lookup = {int(b): float(h) for b, h in zip(src_id, src_h)}

    build_id = table["build_id"].to_numpy()
    fid = table["fidelity"].to_numpy()
    height = table["height"].to_numpy().astype(np.float64)
    hsrc = table["height_source"].to_numpy()
    assert len(set(build_id.tolist())) <= len(build_id)

    src = np.array([lookup.get(int(b), np.nan) for b in build_id])
    assert np.isfinite(np.where(np.isnan(src), 0.0, src)).all(), "a published row has no source row"
    has_source_height = np.isfinite(src) & (src > 0) & (src < nj.MAX_PLAUSIBLE_HEIGHT_M)

    height_real = (fid >> int(S.Fidelity.HEIGHT_REAL)) & 1
    height_inf = (fid >> int(S.Fidelity.HEIGHT_INFERRED)) & 1
    assert np.array_equal(height_real.astype(bool), has_source_height), (
        f"HEIGHT_REAL disagrees with the source on {int((height_real.astype(bool) != has_source_height).sum())} rows")
    assert np.array_equal(height_inf.astype(bool), ~has_source_height)
    assert not (height_real & height_inf).any(), "a row claims both a real and an inferred height"

    # the published height must be the source height, unmodified, wherever it claims to be real
    d = np.abs(height[has_source_height] - src[has_source_height])
    assert d.max() < 1e-3, f"a HEIGHT_REAL row was rescaled by up to {d.max():.3f} m"
    assert (hsrc[has_source_height] == S.SRC_LIDAR).all()
    assert (hsrc[~has_source_height] == S.SRC_NEIGHBOURS).all()

    assert ((fid >> int(S.Fidelity.FOOTPRINT_REAL)) & 1).all(), "every footprint is real"
    for bit in (S.Fidelity.FLOORS_INFERRED, S.Fidelity.FACADE_INFERRED):
        assert (((fid >> int(bit)) & 1) == 1).all(), f"{bit.name} must be set on every New Jersey row"
    for bit in nj.NEVER_SET_BITS:
        n = int(((fid >> int(bit)) & 1).sum())
        assert n == 0, f"{bit.name} is set on {n} New Jersey rows and there is no source for it"


def test_the_published_fidelity_share_is_the_measured_one(all_rows):
    table, _ = all_rows
    fid = table["fidelity"].to_numpy()
    n = len(fid)
    real = float(((fid >> int(S.Fidelity.HEIGHT_REAL)) & 1).sum()) / n
    assert 0.73 < real < 0.74, f"height-real share {real:.4f} is not the measured 73.7 %"
    doc = json.loads((PROCESSED / "buildings_nj" / "buildings_nj_summary.json").read_text())
    assert doc["buildings"] == n
    assert abs(doc["pct_height_real"] - 100.0 * real) < 0.01
    assert doc["n_roof_real"] == doc["n_floors_real"] == doc["n_year_real"] == doc["n_ground_real"] == 0


def test_no_row_claims_a_roof_shape_or_a_landmark(all_rows):
    table, _ = all_rows
    assert set(np.unique(table["roof_type"].to_numpy())) == {nj.ROOF_TYPE_FLAT}
    assert set(table["landmark_id"].to_pylist()) == {""}
    assert set(table["bldg_class"].to_pylist()) == {""}
    assert set(np.unique(table["year_built"].to_numpy())) == {0}
    assert set(np.unique(table["borough"].to_numpy())) == {nj.BOROUGH_NJ}


def test_addresses_are_the_source_addresses_and_never_invented(all_rows, source_rows):
    """``address`` is the one free-text field with a real source; it must be verbatim or empty."""
    table, _ = all_rows
    src = pq.read_table(SOURCE_PARQUET, columns=["build_id", "address"])
    lookup = {int(b): (a or "") for b, a in zip(src["build_id"].to_numpy(), src["address"].to_pylist())}
    got = table["address"].to_pylist()
    ids = table["build_id"].to_numpy()
    bad = [(int(b), g) for b, g in zip(ids, got) if g != lookup.get(int(b), "")]
    assert not bad, f"{len(bad)} addresses differ from the source, e.g. {bad[:3]}"


# --------------------------------------------------------------------------- ground from terrain
def test_ground_elevation_is_the_projects_own_terrain(tile_files):
    """Re-sample the published terrain independently and compare with the published column.

    The source's ``ground_elev_m`` is null on all 231,336 rows, so this column is the only thing
    standing between the New Jersey shells and a made-up ground plane.  A constant, a zero or a
    plane would all fail here.
    """
    from nycsim_pipeline.terrain.segment_z import ZSampler

    rng = np.random.default_rng(20260906)
    picks = [tile_files[i] for i in rng.choice(len(tile_files), size=min(12, len(tile_files)), replace=False)]
    sampler = ZSampler(missing="nearest")
    worst = 0.0
    for p in picks:
        tab = pq.read_table(p, columns=["footprint", "centroid_x", "centroid_y", "ground_z", "ground_source"])
        assert (tab["ground_source"].to_numpy() == S.SRC_TERRAIN).all(), p
        geoms = shapely.from_wkb(tab["footprint"].to_numpy(zero_copy_only=False))
        k = min(25, len(geoms))
        sel = rng.choice(len(geoms), size=k, replace=False)
        for i in sel:
            ring = shapely.get_coordinates(shapely.get_exterior_ring(geoms[i]))
            if len(ring) > nj.GROUND_SAMPLE_MAX_VERTICES:
                ring = ring[::int(math.ceil(len(ring) / nj.GROUND_SAMPLE_MAX_VERTICES))]
            xs = np.append(ring[:, 0], tab["centroid_x"][int(i)].as_py())
            ys = np.append(ring[:, 1], tab["centroid_y"][int(i)].as_py())
            z = np.asarray(sampler.sample(xs, ys))
            expect = float(np.nanmin(z))
            got = float(tab["ground_z"][int(i)].as_py())
            worst = max(worst, abs(got - expect))
    assert worst < GROUND_TOL_M, f"ground_z is {worst:.3f} m from an independent terrain sample"


def test_ground_is_a_real_surface_not_a_plane(all_rows):
    table, _ = all_rows
    z = table["ground_z"].to_numpy().astype(np.float64)
    assert np.isfinite(z).all()
    assert (z != 0.0).sum() > 0.99 * len(z), "ground looks like a zero plane"
    assert z.max() - z.min() > 100.0, "the Palisades are 150 m above the Hackensack meadows"
    assert -10.0 < z.min() < 5.0 and 100.0 < z.max() < 250.0, (z.min(), z.max())
    roof = table["roof_z"].to_numpy().astype(np.float64)
    h = table["height"].to_numpy().astype(np.float64)
    assert np.abs(roof - (z + h)).max() < 1e-3, "roof_z is not ground_z + height"


# --------------------------------------------------------------------------- shells
def _accessor(g, index: int) -> np.ndarray:
    acc = g.accessors[index]
    assert acc.bufferView is not None, "accessor has no bufferView (compressed file?)"
    bv = g.bufferViews[acc.bufferView]
    fmt, size = _COMPONENT[acc.componentType]
    ncomp = _NCOMP[acc.type]
    blob = g.binary_blob()
    base = (bv.byteOffset or 0) + (acc.byteOffset or 0)
    stride = bv.byteStride or (size * ncomp)
    out = np.empty((acc.count, ncomp), dtype=np.float64 if fmt == "f" else np.int64)
    for i in range(acc.count):
        out[i] = struct.unpack_from("<" + fmt * ncomp, blob, base + i * stride)
    return out if ncomp > 1 else out[:, 0]


def _lod_of(name: str) -> int:
    return 1 if name.endswith("_LOD1") else (2 if name.endswith("_LOD2") else 0)


def _collect_lod0(g) -> dict[int, dict]:
    """LOD0 triangles per building key, in tile-local NYC_TM metres (glTF is Y-up)."""
    per: dict[int, dict] = {}
    for mesh in g.meshes:
        if _lod_of(mesh.name) != 0:
            continue
        for prim in mesh.primitives:
            attrs = {k: v for k, v in vars(prim.attributes).items() if v is not None}
            pos = _accessor(g, attrs["POSITION"])
            idx = _accessor(g, prim.indices).astype(np.int64).reshape(-1, 3)
            keys = np.rint(_accessor(g, attrs["_BIN"])).astype(np.int64)
            xyz = np.column_stack([pos[:, 0], -pos[:, 2], pos[:, 1]])
            tri_key = keys[idx[:, 0]]
            for b in np.unique(tri_key):
                sel = tri_key == b
                rec = per.setdefault(int(b), {"pos": [], "tris": 0})
                rec["pos"].append(xyz[np.unique(idx[sel])])
                rec["tris"] += int(sel.sum())
    for rec in per.values():
        rec["pos"] = np.vstack(rec["pos"])
    return per


@pytest.fixture(scope="session")
def shell_tile():
    pygltflib = pytest.importorskip("pygltflib")
    for tile in SHELL_TILES:
        glb = BLENDER_OUT / "tiles" / tile / "tile_buildings_nj.glb"
        if glb.exists() and (glb.parent / "manifest_nj.json").exists():
            return tile, glb, pygltflib.GLTF2().load(str(glb))
    pytest.skip("no New Jersey tile shell has been built yet")


def test_new_jersey_shells_are_a_sibling_file_that_never_replaces_a_new_york_one(shell_tile):
    tile, glb, g = shell_tile
    assert glb.name == "tile_buildings_nj.glb"
    m = json.loads((glb.parent / "manifest_nj.json").read_text())
    assert m["stage"] == "buildings_nj_mesh" and m["source"] == "nj"
    assert m["table"] == nj.TILE_FILENAME
    assert all(n.name.startswith(f"{tile}_nj_") for n in g.meshes), [n.name for n in g.meshes][:3]
    nyc = glb.parent / "tile_buildings.glb"
    if nyc.exists():
        assert json.loads((glb.parent / "manifest.json").read_text())["stage"] == "buildings_mesh"
    extras = (g.asset.extras or {}).get("nycsim")
    assert extras["crs"] == "NYC_TM" and extras["tile"] == tile
    assert extras["roof_steps"] == "off", "New Jersey has no CityGML massing to recover steps from"


def test_shell_triangle_counts_are_consistent_with_the_footprints(shell_tile):
    """Every shell is a closed prism over its own ring: triangles scale with the ring, not with air."""
    tile, glb, g = shell_tile
    m = json.loads((glb.parent / "manifest_nj.json").read_text())
    per = _collect_lod0(g)
    tab = pq.read_table(TILES_DIR / tile / nj.TILE_FILENAME,
                        columns=["bin", "footprint", "ground_z", "roof_z", "height"])
    geoms = shapely.from_wkb(tab["footprint"].to_numpy(zero_copy_only=False))
    keys = tab["bin"].to_numpy()
    assert len(per) == m["buildings"]["solids"], (
        f"{len(per)} shells in the glb, {m['buildings']['solids']} claimed in the manifest")
    assert set(per) <= set(int(k) for k in keys), "a shell carries a key the tile table does not"
    total_glb = sum(r["tris"] for r in per.values())
    assert total_glb == m["triangles"]["lod0"], (total_glb, m["triangles"]["lod0"])

    # The mesh is extruded from the *cleaned* ring (2 cm snap, holes kept), so the count is measured
    # against that ring, not the raw one.  A closed flat-roofed prism over n vertices costs 2n wall
    # triangles plus a cap and a floor of n-2 each, and the parapet adds another band: between 4n and
    # 12n.  Outside that window the mesh is not the footprint it claims to be.
    import shellgeom as sg

    cleaned = sg.clean_footprints(geoms)
    for i, key in enumerate(keys):
        rec = per.get(int(key))
        if rec is None:
            continue
        n_ring = 0
        for part in cleaned[i]:
            for ring in shapely.get_rings(part):
                n_ring += max(len(shapely.get_coordinates(ring)) - 1, 3)
        assert n_ring >= 3, f"{tile} key {key}: cleaning left no ring"
        assert 4 * n_ring - 4 <= rec["tris"] <= 14 * n_ring + 24, (
            f"{tile} key {key}: {rec['tris']} triangles over a {n_ring}-vertex cleaned ring")


def test_shell_bounding_boxes_match_the_footprints_and_the_heights(shell_tile):
    tile, glb, g = shell_tile
    per = _collect_lod0(g)
    x0, y0 = Tile.parse(tile).x0, Tile.parse(tile).y0
    tab = pq.read_table(TILES_DIR / tile / nj.TILE_FILENAME,
                        columns=["bin", "footprint", "ground_z", "roof_z"])
    geoms = shapely.from_wkb(tab["footprint"].to_numpy(zero_copy_only=False))
    keys = tab["bin"].to_numpy()
    gz = tab["ground_z"].to_numpy().astype(np.float64)
    rz = tab["roof_z"].to_numpy().astype(np.float64)
    rng = np.random.default_rng(7)
    sel = rng.choice(len(keys), size=min(SAMPLE_BUILDINGS, len(keys)), replace=False)
    checked = 0
    for i in sel:
        rec = per.get(int(keys[i]))
        if rec is None:
            continue
        checked += 1
        p = rec["pos"]
        bx0, by0, bx1, by1 = shapely.bounds(geoms[i]) - np.array([x0, y0, x0, y0])
        assert p[:, 0].min() >= bx0 - 0.05 and p[:, 0].max() <= bx1 + 0.05, f"{tile} {keys[i]} x"
        assert p[:, 1].min() >= by0 - 0.05 and p[:, 1].max() <= by1 + 0.05, f"{tile} {keys[i]} y"
        # the shell must cover most of the footprint bbox, not sit in a corner of it
        assert (p[:, 0].max() - p[:, 0].min()) > 0.6 * (bx1 - bx0), f"{tile} {keys[i]} too narrow"
        assert (p[:, 1].max() - p[:, 1].min()) > 0.6 * (by1 - by0), f"{tile} {keys[i]} too shallow"
        assert abs(p[:, 2].min() - gz[i]) < HEIGHT_TOL_M, f"{tile} {keys[i]} does not sit on ground_z"
        assert abs(p[:, 2].max() - rz[i]) < HEIGHT_TOL_M, f"{tile} {keys[i]} does not reach roof_z"
    assert checked >= 10, f"only {checked} shells checked"


def test_shell_footprint_area_matches_the_source_polygon(shell_tile):
    """The wall footprint recovered from the mesh must be the polygon the table publishes."""
    tile, glb, g = shell_tile
    per = _collect_lod0(g)
    x0, y0 = Tile.parse(tile).x0, Tile.parse(tile).y0
    tab = pq.read_table(TILES_DIR / tile / nj.TILE_FILENAME, columns=["bin", "footprint", "ground_z"])
    geoms = shapely.from_wkb(tab["footprint"].to_numpy(zero_copy_only=False))
    keys = tab["bin"].to_numpy()
    gz = tab["ground_z"].to_numpy().astype(np.float64)
    rng = np.random.default_rng(11)
    sel = rng.choice(len(keys), size=min(SAMPLE_BUILDINGS, len(keys)), replace=False)
    checked, worst = 0, 1.0
    for i in sel:
        rec = per.get(int(keys[i]))
        if rec is None:
            continue
        base = rec["pos"][np.abs(rec["pos"][:, 2] - gz[i]) < 0.02][:, :2]
        if len(base) < 3:
            continue
        hull = shapely.convex_hull(shapely.multipoints(base))
        want = shapely.convex_hull(shapely.transform(geoms[i], lambda c: c - np.array([x0, y0])))
        inter = shapely.area(shapely.intersection(hull, want))
        union = shapely.area(shapely.union(hull, want))
        iou = inter / union if union > 0 else 0.0
        worst = min(worst, iou)
        checked += 1
    assert checked >= 10, f"only {checked} shells checked"
    assert worst >= IOU_MIN, f"a shell base differs from its footprint (worst IoU {worst:.4f})"


def test_the_shell_run_covered_every_tile_that_has_a_table(tile_files):
    """A tile with a New Jersey table and no New Jersey shell is a hole in the skyline."""
    pytest.importorskip("pygltflib")
    built = {p.parent.name for p in (BLENDER_OUT / "tiles").glob("*/tile_buildings_nj.glb")}
    if not built:
        pytest.skip("no New Jersey shells have been built yet")
    want = {p.parent.name for p in tile_files}
    missing = sorted(want - built)
    assert not missing, f"{len(missing)} New Jersey tiles have a table but no shell: {missing[:10]}"
    stale = sorted(built - want)
    assert not stale, f"{len(stale)} New Jersey shells survive without a table: {stale[:10]}"


def test_the_verification_scene_loads_the_new_jersey_shells():
    """The shells only matter if the renderer picks them up, so load one New Jersey tile through
    ``blender/verify/scene.py`` and check the objects arrive."""
    pytest.importorskip("bpy")
    sys.path.insert(0, str(REPO_ROOT / "blender" / "verify"))
    import bpy
    import scene as vscene

    tile = None
    for cand in SHELL_TILES:
        if (BLENDER_OUT / "tiles" / cand / "tile_buildings_nj.glb").exists():
            tile = cand
            break
    if tile is None:
        pytest.skip("no New Jersey shell has been built yet")
    t = Tile.parse(tile)
    cx, cy = t.x0 + 500.0, t.y0 + 500.0
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)
    rep = vscene.add_buildings(cx, cy, 400.0, lod0_radius_m=2000.0)
    assert tile in rep["imported"], rep
    assert tile in rep.get("new_jersey", []), "the scene report does not record the New Jersey file"
    names = [ob.name for ob in bpy.data.objects if ob.type == "MESH"]
    nj_objects = [n for n in names if f"{tile}_nj_" in n]
    assert nj_objects, f"no New Jersey objects in the scene, got {names[:5]}"
    assert rep["triangles"] > 0
    zs = [(ob.matrix_world @ v.co).z for ob in bpy.data.objects if ob.type == "MESH"
          for v in ob.data.vertices]
    tab = pq.read_table(TILES_DIR / tile / nj.TILE_FILENAME, columns=["ground_z", "roof_z"])
    assert min(zs) >= float(tab["ground_z"].to_numpy().min()) - 0.05
    assert max(zs) <= float(tab["roof_z"].to_numpy().max()) + 0.05


# --------------------------------------------------------------------------- manifest
def test_the_shell_index_matches_the_meshes_on_disk(tile_files):
    """``shells_index.json`` is the only audit trail for the meshes (blender_out is git-ignored),
    so its counts and hashes must be the ones on disk, not the ones from an earlier run."""
    idx_path = PROCESSED / "buildings_nj" / "shells_index.json"
    if not idx_path.exists():
        pytest.skip("the New Jersey shell index has not been written")
    idx = json.loads(idx_path.read_text())
    want = {p.parent.name for p in tile_files}
    assert set(idx["tiles"]) == want, "the shell index and the tile tables disagree on which tiles exist"
    assert idx["totals"]["tiles"] == len(want)
    tot = 0
    for tile, rec in idx["tiles"].items():
        m = json.loads((BLENDER_OUT / "tiles" / tile / "manifest_nj.json").read_text())
        assert rec["buildings"] == m["buildings"]["solids"], tile
        assert rec["triangles"] == {k: int(v) for k, v in m["triangles"].items()}, tile
        assert rec["bytes"] == (BLENDER_OUT / "tiles" / tile / "tile_buildings_nj.glb").stat().st_size, tile
        tot += rec["buildings"]
    assert tot == idx["totals"]["buildings"]
    published = sum(pq.ParquetFile(p).metadata.num_rows for p in tile_files)
    assert tot == published, f"{tot} shells for {published} published buildings"
    from nycsim_pipeline import manifest

    rng = np.random.default_rng(5)
    for tile in rng.choice(sorted(idx["tiles"]), size=3, replace=False):
        glb = BLENDER_OUT / "tiles" / str(tile) / "tile_buildings_nj.glb"
        assert manifest.sha256_of(glb) == idx["tiles"][str(tile)]["sha256"], f"{tile} glb has drifted"


def test_every_artifact_is_registered_in_the_manifest(tile_files):
    from nycsim_pipeline import manifest

    doc = json.loads((REPO_ROOT / "data" / "manifest" / "processed.json").read_text())["entries"]
    for key in ("buildings_nj_base", "buildings_nj_summary", "buildings_nj_tiles", "buildings_nj_shells"):
        assert key in doc, f"{key} is not recorded in data/manifest/processed.json"
        assert doc[key]["stage"] in ("buildings_nj", "buildings_nj_mesh")
        assert doc[key]["sources"] == [nj.SOURCE_ID]
        assert doc[key]["license"] == nj.LICENSE
    base = REPO_ROOT / doc["buildings_nj_base"]["path"]
    assert base.exists()
    assert manifest.sha256_of(base) == doc["buildings_nj_base"]["sha256"], "buildings_nj_base has drifted"
    idx = json.loads((REPO_ROOT / doc["buildings_nj_tiles"]["path"]).read_text())
    assert idx["filename"] == nj.TILE_FILENAME
    assert len(idx["tiles"]) == len(tile_files)
    rng = np.random.default_rng(3)
    for name in rng.choice(sorted(idx["tiles"]), size=min(5, len(idx["tiles"])), replace=False):
        p = TILES_DIR / str(name) / nj.TILE_FILENAME
        assert manifest.sha256_of(p) == idx["tiles"][str(name)]["sha256"], f"{name} has drifted"
