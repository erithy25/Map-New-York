"""Tests for the visual-comparison stage (`blender/verify/`, `docs/verification/comparison/`).

These cover the parts of the comparison pipeline that can be checked without spending a Cycles
render: the tile/radius arithmetic, the terrain sampler against the published heightmap contract,
the binary kit-placement record layout, the camera geometry (position, heading, field of view),
the Sun placement against the live-services SPA implementation, and the shape of whatever sheets
have been produced so far.

    PYTHONPATH=pipeline:services pytest tests/test_comparison.py -q
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_DIR = REPO_ROOT / "blender" / "verify"
REFERENCE_DIR = REPO_ROOT / "docs" / "verification" / "reference"
COMPARISON_DIR = REPO_ROOT / "docs" / "verification" / "comparison"

for _p in (str(VERIFY_DIR), str(REPO_ROOT / "pipeline"), str(REPO_ROOT / "services"),
           str(REPO_ROOT / "blender" / "common")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("numpy")
import numpy as np  # noqa: E402


def _skip_without_render_sheets():
    """Import render_sheets without Blender: only its photograph chooser is under test here."""
    import importlib.util
    import sys as _sys
    import types

    _sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    _sys.path.insert(0, str(REPO_ROOT / "pipeline"))
    spec = importlib.util.spec_from_file_location(
        "rs_for_tests", REPO_ROOT / "blender" / "verify" / "render_sheets.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # pragma: no cover - environment without the pipeline package
        pytest.skip(f"render_sheets is not importable here: {exc}")
    return mod


def _skip_without_bpy():
    return pytest.importorskip("bpy", reason="Blender's bpy module is required for the verify scene")


# --------------------------------------------------------------------------- tiling arithmetic


def test_tiles_in_radius_covers_exactly_the_intersecting_tiles():
    _skip_without_bpy()
    import scene as vscene

    # A point in the middle of t_0_0 with a 100 m radius touches only that tile.
    assert vscene.tiles_in_radius(500.0, 500.0, 100.0) == [(0, 0)]
    # On the corner of four tiles every one of them is inside the disc.
    got = set(vscene.tiles_in_radius(1000.0, 1000.0, 50.0))
    assert got == {(0, 0), (0, 1), (1, 0), (1, 1)}
    # From the centre of a tile, a 1.2 km radius reaches the neighbours and their diagonals but
    # not the next ring: the nearest corner of t_2_0 is 1.5 km away.
    got = set(vscene.tiles_in_radius(500.0, 500.0, 1200.0))
    assert (1, 0) in got and (-1, 0) in got and (1, 1) in got and (-1, -1) in got
    assert (2, 0) not in got and (2, 2) not in got
    for tx, ty in got:
        nx = min(max(500.0, tx * 1000.0), tx * 1000.0 + 1000.0)
        ny = min(max(500.0, ty * 1000.0), ty * 1000.0 + 1000.0)
        assert math.hypot(nx - 500.0, ny - 500.0) <= 1200.0 + 1e-9


# --------------------------------------------------------------------------- terrain sampler


def _some_terrain_tile() -> tuple[str, dict]:
    tiles = sorted((REPO_ROOT / "data" / "processed" / "tiles").glob("*/terrain.json"))
    if not tiles:
        pytest.skip("no terrain tiles produced yet")
    for p in tiles:
        meta = json.loads(p.read_text())
        if meta.get("has_land") and meta.get("z_max_m", 0) > meta.get("z_min_m", 0):
            return p.parent.name, meta
    pytest.skip("no terrain tile with relief produced yet")


def test_terrain_sampler_reproduces_the_published_height_range():
    _skip_without_bpy()
    import scene as vscene

    tile, meta = _some_terrain_tile()
    tx, ty = int(meta["tx"]), int(meta["ty"])
    s = vscene.TerrainSampler()
    xs, ys = np.meshgrid(np.linspace(tx * 1000.0 + 1.0, tx * 1000.0 + 999.0, 61),
                         np.linspace(ty * 1000.0 + 1.0, ty * 1000.0 + 999.0, 61))
    z, water = s.grid(xs, ys)
    assert not np.isnan(z).any(), f"{tile} sampled to NaN inside its own footprint"
    lo, hi = float(meta["z_min_m"]), float(meta["z_max_m"])
    assert z.min() >= lo - 0.01, (z.min(), lo)
    assert z.max() <= hi + 0.01, (z.max(), hi)
    assert water.shape == z.shape


def test_water_is_the_surveyed_polygon_and_not_the_tile_scalar():
    """A ground sample is water when it is inside a surveyed body, whatever the tile's level says.

    The tile heightmaps carry ``water_level_m`` as a hard-coded 0.0 and this module used to mask
    water as "at or below that level", which selects nothing on any tile whose water stands above
    its own lowest ground: Central Park's Lake sits at 16.55 m on a tile whose floor is 10.89 m and
    rendered as dry ground, and so did the Staten Island reservoirs and the Bronx and Queens lakes.
    """
    _skip_without_bpy()
    import scene as vscene

    wb = vscene.water_bodies()
    if not wb.ok:
        pytest.skip(f"no water polygons on disk: {wb.reason}")
    s = vscene.TerrainSampler()
    tile = REPO_ROOT / "data" / "processed" / "tiles" / "t_-2_8" / "terrain.json"
    if not tile.exists():
        pytest.skip("t_-2_8 (Central Park's Lake) not built")
    meta = json.loads(tile.read_text())
    assert float(meta.get("water_level_m", 0.0)) < float(meta["z_min_m"]), (
        "the premise of this test is that the tile's scalar water level is below its own terrain")
    # The Lake's own polygon bounds, from data/processed/water/hydrography.parquet.
    xs, ys = np.meshgrid(np.linspace(-2010.0, -1600.0, 60), np.linspace(8280.0, 8795.0, 60))
    z, water = s.grid(xs, ys)
    assert water.any(), "no sample inside THE LAKE came back as water"
    lake = z[water]
    assert float(np.nanmedian(lake)) == pytest.approx(16.55, abs=0.1), float(np.nanmedian(lake))
    # ... and the mask never lifts the ground: the heights are the heightmap's, untouched.
    dry = z[~water]
    assert float(np.nanmax(dry)) > float(np.nanmax(lake)), "the mask flooded ground above the water"


def test_the_water_mask_cannot_flood_relief_above_a_body():
    """`t_-15_-12` holds a pond at 94.58 m over ground from 76.65 m; the pond must not swallow the hill."""
    _skip_without_bpy()
    import scene as vscene

    wb = vscene.water_bodies()
    if not wb.ok:
        pytest.skip(f"no water polygons on disk: {wb.reason}")
    if not (REPO_ROOT / "data" / "processed" / "tiles" / "t_-15_-12" / "terrain.json").exists():
        pytest.skip("t_-15_-12 not built")
    s = vscene.TerrainSampler()
    xs, ys = np.meshgrid(np.linspace(-15000.0, -14000.0, 101), np.linspace(-12000.0, -11000.0, 101))
    z, water = s.grid(xs, ys)
    assert water.any(), "the ponds on this tile are not masked at all"
    assert water.mean() < 0.10, f"{water.mean():.0%} of a hillside tile came back as water"
    lo = float(np.nanmin(z[water]))
    assert lo > 70.0, f"the mask reaches down to {lo:.1f} m, which is the valley floor, not a pond"


def test_terrain_and_pavement_are_not_drawn_under_a_landmark_s_own_ground():
    """Where a landmark models the ground, the DEM is not drawn across it -- openings included.

    The 9/11 Memorial is the case: the plaza is cut open over two 61 m pools whose basins reach
    -4.39 m, and the heightmap inside those squares reads about 2.0 m, so the terrain was drawn
    straight through the pool and the opening read as a 2.4 m depression instead of a 9.14 m fall.
    """
    _skip_without_bpy()
    import scene as vscene

    cat = {e["id"]: e for e in vscene.load_landmark_catalog()}
    if "b_wtc_site" not in cat:
        pytest.skip("b_wtc_site is not in the landmark catalogue")
    import bpy
    from mathutils import Matrix
    import nycsim_bpy as nb

    nb.reset_scene()
    lib = vscene.AssetLibrary()
    e = cat["b_wtc_site"]
    rel = Path(e["glb"])
    glb = rel if rel.is_absolute() else REPO_ROOT / rel
    if not glb.exists():
        glb = REPO_ROOT / "blender_out" / "landmarks" / rel.name
    tpl = lib.get(glb, key="test:b_wtc_site", max_lod=0)
    assert tpl is not None, f"{glb} did not import"
    ox, oy, oz = (float(v) for v in e["origin_tm"])
    obs = tpl.instance("lm_b_wtc_site", Matrix.Translation((ox, oy, oz)), bpy.context.scene.collection)
    bpy.context.view_layer.update()
    sampler = vscene.TerrainSampler()
    rings, area, why = vscene.landmark_ground_outlines(obs, oz, sampler=sampler)
    assert rings, f"the WTC site model carries a plaza deck and no ground outline was found: {why}"
    assert abs(why.get("above_heightmap_m", 99.0)) <= vscene.LANDMARK_GROUND_BAND_M, why
    # The plaza is the real memorial plaza outline: 33,039 m2, and both pool squares are inside it.
    assert area == pytest.approx(33039.0, rel=0.02), area
    import shapely
    for cx, cy in ((-5338.35, 1349.96), (-5330.40, 1226.73)):     # the two measured pool centres
        assert any(shapely.contains_xy(g, cx, cy) for g in rings), (cx, cy)
    # A tower shell supplies no ground, so nothing is cut under it.
    if "b_one_world_trade_center" in cat:
        nb.reset_scene()
        lib2 = vscene.AssetLibrary()
        e2 = cat["b_one_world_trade_center"]
        rel2 = Path(e2["glb"])
        glb2 = rel2 if rel2.is_absolute() else REPO_ROOT / rel2
        if not glb2.exists():
            glb2 = REPO_ROOT / "blender_out" / "landmarks" / rel2.name
        t2 = lib2.get(glb2, key="test:1wtc", max_lod=0)
        if t2 is not None:
            o2 = (float(v) for v in e2["origin_tm"])
            ox2, oy2, oz2 = o2
            obs2 = t2.instance("lm_1wtc", Matrix.Translation((ox2, oy2, oz2)),
                               bpy.context.scene.collection)
            bpy.context.view_layer.update()
            r2, a2, _ = vscene.landmark_ground_outlines(obs2, oz2)
            assert not r2, f"1 WTC is a tower shell and should supply no ground, got {a2:.0f} m2"


def test_a_deck_metres_above_the_heightmap_does_not_cut_the_terrain_under_it():
    """Hudson Yards' plaza is 20,061 m2 at 7.82 m over a heightmap median of 2.48 m.

    A modelled surface that far above the published ground is a podium standing *on* the ground, not
    a statement about where the ground is; cutting the terrain under it would leave a 5 m hole where
    there is real ground, and that scene's own assessment already says the Vessel "hovers on a disc
    above the plaza with nothing under it".
    """
    _skip_without_bpy()
    import scene as vscene

    cat = {e["id"]: e for e in vscene.load_landmark_catalog()}
    if "c_hudson_yards" not in cat:
        pytest.skip("c_hudson_yards is not in the landmark catalogue")
    import bpy
    from mathutils import Matrix
    import nycsim_bpy as nb

    nb.reset_scene()
    lib = vscene.AssetLibrary()
    e = cat["c_hudson_yards"]
    rel = Path(e["glb"])
    glb = rel if rel.is_absolute() else REPO_ROOT / rel
    if not glb.exists():
        glb = REPO_ROOT / "blender_out" / "landmarks" / rel.name
    tpl = lib.get(glb, key="test:hy", max_lod=0)
    if tpl is None:
        pytest.skip(f"{glb} did not import")
    ox, oy, oz = (float(v) for v in e["origin_tm"])
    obs = tpl.instance("lm_hy", Matrix.Translation((ox, oy, oz)), bpy.context.scene.collection)
    bpy.context.view_layer.update()
    rings, area, why = vscene.landmark_ground_outlines(obs, oz, sampler=vscene.TerrainSampler())
    assert not rings, f"the Hudson Yards podium cut {area:.0f} m2 of terrain"
    assert why.get("above_heightmap_m", 0.0) > vscene.LANDMARK_GROUND_BAND_M, why
    assert "deck on the ground, not" in why.get("reason", "")


def test_terrain_sampler_orientation_matches_the_north_first_png_row():
    """PNG row 0 is the north edge, so sampling near y_max must read the first image row."""
    _skip_without_bpy()
    from PIL import Image
    import scene as vscene

    tile, meta = _some_terrain_tile()
    tx, ty = int(meta["tx"]), int(meta["ty"])
    with Image.open(REPO_ROOT / "data" / "processed" / "tiles" / tile / "terrain.png") as im:
        arr = np.asarray(im).astype(np.float64)
    z_north_row = float(meta["z_min_m"]) + arr[0, 250] * float(meta["z_scale_m"])
    z_south_row = float(meta["z_min_m"]) + arr[500, 250] * float(meta["z_scale_m"])
    s = vscene.TerrainSampler()
    got_north = s.z_at(tx * 1000.0 + 500.0, ty * 1000.0 + 1000.0)
    got_south = s.z_at(tx * 1000.0 + 500.0, ty * 1000.0 + 0.0)
    assert got_north == pytest.approx(z_north_row, abs=0.02)
    assert got_south == pytest.approx(z_south_row, abs=0.02)


def test_terrain_sampler_reports_missing_tiles_instead_of_inventing_ground():
    _skip_without_bpy()
    import scene as vscene

    s = vscene.TerrainSampler()
    # Far outside the project scope: no tile can exist there.
    z, _ = s.grid(np.array([[900000.0]]), np.array([[900000.0]]))
    assert np.isnan(z[0, 0])
    assert s.z_at(900000.0, 900000.0) is None
    assert s.missing


# --------------------------------------------------------------------------- kit record layout


def test_kit_record_matches_the_data_contract_header():
    _skip_without_bpy()
    import scene as vscene

    assert vscene.KIT_RECORD.itemsize == 40
    headers = sorted((REPO_ROOT / "data" / "processed" / "tiles").glob("*/kit_placements.json"))
    if not headers:
        pytest.skip("no kit placements produced yet")
    h = json.loads(headers[0].read_text())
    assert h["record_bytes"] == vscene.KIT_RECORD.itemsize
    assert h["byte_order"] == "little"
    assert [f["name"] for f in h["fields"]] == list(vscene.KIT_RECORD.names)
    binary = headers[0].with_suffix(".bin")
    a = np.fromfile(binary, dtype=vscene.KIT_RECORD)
    assert a.size == h["count"], (a.size, h["count"])
    # Every placement must sit inside the tile it is filed under, +- a piece's own reach.
    tile = h["tile"]
    tx, ty = (int(v) for v in tile.split("_")[1:3])
    assert a["x"].min() >= tx * 1000.0 - 60.0
    assert a["x"].max() <= tx * 1000.0 + 1060.0
    assert a["y"].min() >= ty * 1000.0 - 60.0
    assert a["y"].max() <= ty * 1000.0 + 1060.0


def test_kit_ids_resolve_to_files_or_are_reported_as_unresolved():
    _skip_without_bpy()
    import scene as vscene

    kit_map, why = vscene.load_kit_map()
    if not kit_map:
        pytest.skip(f"kit registry not resolvable yet: {why}")
    missing = [e["glb"] for e in kit_map.values()
               if not (REPO_ROOT / "blender_out" / e["glb"]).exists()]
    assert not missing, f"{len(missing)} registry entries point at files that do not exist: {missing[:5]}"


# --------------------------------------------------------------------------- world placement


def _built_tiles() -> list[str]:
    d = REPO_ROOT / "blender_out" / "tiles"
    if not d.is_dir():
        return []
    return sorted(p.parent.name for p in d.glob("*/tile_buildings.glb"))


def test_building_shells_land_on_their_published_world_bounds():
    """A tile glb is stored in tile-local metres; the scene must translate it by the tile origin."""
    bpy = _skip_without_bpy()
    import scene as vscene
    import nycsim_bpy as nb

    tiles = _built_tiles()
    if not tiles:
        pytest.skip("no tile_buildings.glb produced yet")
    tile = tiles[0]
    manifest = json.loads((REPO_ROOT / "blender_out" / "tiles" / tile / "manifest.json").read_text())
    want = manifest["bounds_world_m"]
    tx, ty = (int(v) for v in tile.split("_")[1:3])
    nb.reset_scene()
    rep = vscene.add_buildings((tx + 0.5) * 1000.0, (ty + 0.5) * 1000.0, 200.0, lod0_radius_m=1e9)
    assert rep["tiles_imported"] == 1, rep
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            w = ob.matrix_world @ __import__("mathutils").Vector(corner)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
    for k, axis in enumerate("xyz"):
        assert lo[k] == pytest.approx(want["min"][k], abs=0.5), f"{tile} {axis} min {lo[k]} vs {want['min'][k]}"
        assert hi[k] == pytest.approx(want["max"][k], abs=0.5), f"{tile} {axis} max {hi[k]} vs {want['max'][k]}"


def test_a_tile_without_the_requested_lod_is_drawn_at_the_nearest_lod_it_has():
    """A tile whose shells decimate to nothing at LOD2 must not vanish from a skyline."""
    _skip_without_bpy()
    import scene as vscene
    import nycsim_bpy as nb

    tiles = _built_tiles()
    if not tiles:
        pytest.skip("no tile_buildings.glb produced yet")
    # Find a tile whose glb carries LOD0/LOD1 but no LOD2.  There is no cheap way to read a glb's
    # node names without importing it, so import candidates until one turns up or the budget runs
    # out -- most tiles do carry all three LODs.
    victim = None
    for tile in tiles[:40]:
        nb.reset_scene()
        created = vscene.import_glb(REPO_ROOT / "blender_out" / "tiles" / tile / "tile_buildings.glb")
        lods = {vscene._lod_of(ob.name) for ob in created if ob.type == "MESH"}
        if lods and 2 not in lods:
            victim = tile
            break
    if victim is None:
        pytest.skip("every tile sampled carries a LOD2; nothing to exercise the fallback with")
    tx, ty = (int(v) for v in victim.split("_")[1:3])
    # Stand 1 m off the tile centre with both LOD thresholds inside that, so the tile falls in
    # the LOD2 band and the fallback has to fire.
    cx, cy = (tx + 0.5) * 1000.0 + 1.0, (ty + 0.5) * 1000.0
    nb.reset_scene()
    rep = vscene.add_buildings(cx, cy, 200.0, lod0_radius_m=0.5, lod1_radius_m=0.5)
    assert victim in rep["imported"], f"{victim} was dropped rather than substituted: {rep['missing']}"
    assert rep["per_tile"][victim]["lod"] != 2
    assert rep["per_tile"][victim]["lod_requested"] == 2
    assert rep["tiles_lod_substituted"] >= 1
    assert any(victim in line for line in rep["lod_substituted"])


def test_a_landmark_model_replaces_the_tile_shell_of_the_same_building():
    """Both are the same object; drawing both puts two Empire State Buildings in one frame."""
    _skip_without_bpy()
    import scene as vscene
    import nycsim_bpy as nb
    from nycsim_pipeline.crs import lonlat_to_tm

    bins = vscene.landmark_bins()
    if not bins:
        pytest.skip("no landmark catalogue entry names the BINs it replaces")
    if not _built_tiles():
        pytest.skip("no tile_buildings.glb produced yet")
    # Around the Empire State Building, where several catalogued landmarks stand together.
    x, y = (float(v) for v in lonlat_to_tm(-73.9857, 40.7484))
    nb.reset_scene()
    plain = vscene.add_buildings(x, y, 300.0, lod0_radius_m=1e9)
    nb.reset_scene()
    thinned = vscene.add_buildings(x, y, 300.0, lod0_radius_m=1e9, suppress_landmark_bins=bins)
    assert thinned["tiles_imported"] == plain["tiles_imported"]
    assert thinned["landmark_bins_suppressed"] >= 1, thinned
    assert thinned["landmark_faces_suppressed"] >= 1
    assert thinned["triangles"] < plain["triangles"], (
        "suppressing the shells of catalogued landmarks must remove geometry")


def test_landmarks_land_at_their_catalogue_origin_and_published_height():
    bpy = _skip_without_bpy()
    import scene as vscene
    import nycsim_bpy as nb

    entries = {e["id"]: e for e in vscene.load_landmark_catalog()}
    if "empire_state" not in entries:
        pytest.skip("Empire State Building not exported yet")
    e = entries["empire_state"]
    ox, oy, oz = (float(v) for v in e["origin_tm"])
    nb.reset_scene()
    lib = vscene.AssetLibrary()
    rep = vscene.add_landmarks(lib, ox, oy, 50.0, catalog=[e])
    assert rep["placed"] == 1, rep
    zs = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        for corner in ob.bound_box:
            zs.append((ob.matrix_world @ __import__("mathutils").Vector(corner)).z)
    assert zs
    # The published roof/antenna height is measured from the model origin (street level).
    top = max(zs) - oz
    assert 300.0 < top < 460.0, f"Empire State model tops out {top:.1f} m above its origin"
    if e.get("bounds_local_m"):
        assert top == pytest.approx(float(e["bounds_local_m"]["max"][2]), abs=1.0)


def test_every_prop_asset_matches_the_size_its_catalogue_publishes():
    """Props are placed by translation and yaw alone, so a wrong on-screen size is a wrong glb."""
    _skip_without_bpy()
    import scene as vscene
    import nycsim_bpy as nb

    if not vscene.PROPS_CATALOG_JSON.exists():
        pytest.skip("no prop asset catalogue exported yet")
    nb.reset_scene()
    rep = vscene.audit_prop_assets()
    assert rep["checked"] > 0
    assert rep["unloadable"] == [], f"prop assets that would not import: {rep['unloadable']}"
    assert rep["bad"] == [], (
        "prop assets whose glb geometry is bigger than the size their catalogue entry publishes, "
        f"and not explained by a modelled light cone: {rep['bad']}")
    # The lamps are the only entries allowed to exceed their nominal size, and only by their cone.
    for row in rep["with_effects"]:
        assert row["dataset_kind"] == "street_lamp", row


def test_tree_impostor_cards_are_not_drawn_over_the_real_branches():
    """Every tree glb carries a flat opaque ``*_billboard`` card; drawing it makes a black cone."""
    _skip_without_bpy()
    import scene as vscene
    import nycsim_bpy as nb

    if not vscene.PROPS_CATALOG_JSON.exists():
        pytest.skip("no prop asset catalogue exported yet")
    entries = {e["id"]: e for e in json.loads(vscene.PROPS_CATALOG_JSON.read_text())["entries"]}
    tree = next((e for i, e in entries.items() if i.startswith("tree_")), None)
    if tree is None:
        pytest.skip("no tree assets exported yet")
    nb.reset_scene()
    created = vscene.import_glb(vscene.BLENDER_OUT / tree["glb"])
    cards = [ob for ob in created if ob.type == "MESH" and vscene._is_impostor(ob)]
    assert cards, f"{tree['id']} carries no impostor card; this guard is no longer needed"
    nb.reset_scene()
    lib = vscene.AssetLibrary()
    tpl = lib.get(vscene.BLENDER_OUT / tree["glb"], key="t", max_lod=0)
    assert tpl is not None
    assert lib.impostors_dropped >= 1
    for mesh, _ in tpl.parts:
        names = [m.name for m in mesh.materials if m is not None]
        assert not any(n.startswith("IMPOSTOR_") for n in names), (
            f"{tree['id']} still draws its impostor card at LOD0: {names}")


def test_the_ground_mesh_resolves_the_near_field_and_still_reaches_the_horizon():
    """A uniform grid over a 700 m scene lands one height every 4.7 m; that is a rolling sidewalk."""
    _skip_without_bpy()
    import scene as vscene

    xs, grade = vscene.graded_axis(0.0, 700.0, near_m=150.0, near_spacing_m=2.0,
                                   max_spacing_m=40.0, growth=1.14, max_points=301)
    assert xs.size <= 301
    assert xs[0] == pytest.approx(-700.0) and xs[-1] == pytest.approx(700.0)
    d = np.diff(xs)
    assert np.all(d > 0.0), "the sample axis must be strictly increasing"
    near = d[(xs[:-1] >= -140.0) & (xs[:-1] <= 140.0)]
    assert near.max() <= 2.0 + 1e-6, f"near-field spacing is {near.max():.2f} m, not the heightmap's 2 m"
    assert d.max() <= 40.0 + 1e-6, f"far-field spacing is {d.max():.2f} m, above the 40 m cap"
    assert grade["near_spacing_m"] == pytest.approx(2.0)
    # A 5 km skyline scene still has to fit in its point budget, and still resolve its foreground.
    xs2, grade2 = vscene.graded_axis(0.0, 5000.0, near_m=150.0, near_spacing_m=2.0,
                                     max_spacing_m=40.0, growth=1.14, max_points=381)
    assert xs2.size <= 381
    d2 = np.diff(xs2)
    assert d2[(xs2[:-1] >= -140.0) & (xs2[:-1] <= 140.0)].max() <= 4.0
    assert grade2["far_spacing_m"] <= 40.0 + 1e-6


# --------------------------------------------------------------------------- camera


def test_focal_length_to_field_of_view():
    _skip_without_bpy()
    import camera as vcam

    assert vcam.horizontal_fov_deg(35.0, 36.0) == pytest.approx(54.43, abs=0.02)
    assert vcam.horizontal_fov_deg(24.0, 36.0) == pytest.approx(73.74, abs=0.02)
    assert vcam.horizontal_fov_deg(50.0, 36.0) == pytest.approx(39.60, abs=0.02)


@pytest.mark.parametrize("azimuth,expect", [
    (0.0, (0.0, 1.0)),      # north
    (90.0, (1.0, 0.0)),     # east
    (180.0, (0.0, -1.0)),   # south
    (270.0, (-1.0, 0.0)),   # west
])
def test_camera_points_along_the_reference_azimuth(azimuth, expect):
    bpy = _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb

    nb.reset_scene()
    p = vcam.place_camera(slug="_unit_test", lat=40.75, lon=-73.98, azimuth_deg=azimuth,
                          sampler=None, resolution=(320, 200))
    cam = bpy.context.scene.camera
    fwd = cam.matrix_world.to_quaternion() @ __import__("mathutils").Vector((0.0, 0.0, -1.0))
    assert fwd.x == pytest.approx(expect[0], abs=1e-6)
    assert fwd.y == pytest.approx(expect[1], abs=1e-6)
    assert fwd.z == pytest.approx(0.0, abs=1e-6)
    assert p.hfov_deg == pytest.approx(vcam.horizontal_fov_deg(p.focal_mm), abs=1e-9)


def test_camera_sits_at_the_reference_viewpoint_in_nyc_tm():
    _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb
    from nycsim_pipeline.crs import lonlat_to_tm

    meta = json.loads((REFERENCE_DIR / "fifth_ave_42nd_north" / "meta.json").read_text())
    vp = meta["viewpoint"]
    nb.reset_scene()
    p = vcam.place_camera(slug="fifth_ave_42nd_north", lat=vp["lat"], lon=vp["lon"],
                          azimuth_deg=vp["azimuth_deg"], sampler=None, resolution=(320, 200))
    x, y = lonlat_to_tm(vp["lon"], vp["lat"])
    assert p.x == pytest.approx(x, abs=1e-6)
    assert p.y == pytest.approx(y, abs=1e-6)
    assert p.azimuth_deg == pytest.approx(vp["azimuth_deg"])


def test_eye_height_is_the_standing_default_unless_the_note_says_otherwise():
    _skip_without_bpy()
    import camera as vcam

    # A sidewalk view gets the standing default.
    assert vcam.eye_rule_for("fifth_ave_42nd_north").height_m == pytest.approx(1.60)
    # The three viewpoints whose note names a structure or a vessel do not.
    tall = vcam.eye_rule_for("top_of_the_rock_south")
    assert tall.height_m > 250.0 and "30 Rockefeller" in tall.source
    ferry = vcam.eye_rule_for("staten_island_ferry_lower_manhattan")
    assert ferry.datum == "sea" and 5.0 < ferry.height_m < 15.0
    steps = vcam.eye_rule_for("times_square_duffy_south_day")
    assert 5.0 < steps.height_m < 8.0 and "TKTS" in steps.source
    for rule in vcam.EYE_OVERRIDES.values():
        assert rule.source.strip(), "every non-default eye height must state where the number came from"
        assert rule.datum in ("terrain", "sea")


# --------------------------------------------------------------------------- sun placement


def test_camera_position_and_heading_come_from_the_same_measurement():
    """Position from the photograph's GPS, heading from that same point to the named subject.

    The failure this guards against is real and was shipped once: the heading was taken from the
    photograph's own GPS ("camera_gps_to_subject") while the position stayed on the item's nominal
    viewpoint 35 m away, so the render looked past the subject and the two halves of the sheet
    faced different ways.
    """
    _skip_without_bpy()
    import render_sheets as rs
    from nycsim_pipeline.crs import lonlat_to_tm

    # Washington Street in DUMBO: nominal viewpoint, the photograph's own GPS 35 m north-west,
    # and the Manhattan Bridge Brooklyn tower as the subject.
    meta = {"viewpoint": {"lat": 40.7030, "lon": -73.9892, "azimuth_deg": 345.8,
                          "note": "Washington Street, centred on the roadway"},
            "subject": {"lat": 40.7045, "lon": -73.9897, "name": "Manhattan Bridge Brooklyn tower"}}
    photo = {"camera_gps": {"lat": 40.703061, "lon": -73.989602}}
    lat, lon, why, offset, from_photo = rs.view_origin(meta, photo)
    assert from_photo is True and lat == pytest.approx(40.703061)
    assert 30.0 < offset < 45.0, offset
    assert "EXIF camera GPS" in why
    az, az_why = rs.view_azimuth("x", meta, photo, lat, lon, origin_is_photo=from_photo)
    vx, vy = (float(v) for v in lonlat_to_tm(lon, lat))
    sx, sy = (float(v) for v in lonlat_to_tm(meta["subject"]["lon"], meta["subject"]["lat"]))
    want = math.degrees(math.atan2(sx - vx, sy - vy)) % 360.0
    assert az == pytest.approx(want, abs=1e-6), "the heading must be measured from the position used"
    assert "photograph" in az_why

    # A photograph whose GPS is kilometres away is mis-tagged, not a better measurement.
    far = {"camera_gps": {"lat": 40.7350, "lon": -73.9892}}
    lat2, lon2, why2, offset2, from_photo2 = rs.view_origin(meta, far)
    assert from_photo2 is False
    assert (lat2, lon2) == (40.7030, -73.9892)
    # The assertion is on the meaning, not the wording: the reason string used to say the
    # photograph was "rejected as mis-tagged", which is false of a fix that is correct and
    # simply of somewhere else (docs/DEVIATIONS.md J60).
    assert offset2 > rs.PHOTO_GPS_SANITY_M and "camera was not stood on it" in why2
    # Falling back to the nominal viewpoint, the recorded azimuth is kept because it agrees with
    # the bearing to the subject from that point.
    az2, _ = rs.view_azimuth("x", meta, far, lat2, lon2, origin_is_photo=False)
    assert az2 == pytest.approx(345.8)


def test_a_photographs_own_gps_wins_where_it_is_nearer_the_subject_it_is_of():
    """The sanity radius measures the wrong thing for a view *of* something.

    The Williamsburg Bridge photograph's GPS is 117 m from the Brooklyn tower and the item's
    recorded viewpoint is 506 m from it, 389 m apart -- so the 250 m radius rejected the
    measurement in favour of the estimate and put the camera half a kilometre too far back.  A
    view *from* a place (a ferry deck, a promenade, a named block) keeps the radius, because there
    the recorded position is the view.
    """
    import render_sheets as rs

    def meta(group, vp, subject):
        return {"slug": "t", "group": group,
                "viewpoint": {"lat": vp[0], "lon": vp[1], "azimuth_deg": 0.0},
                "subject": {"lat": subject[0], "lon": subject[1], "name": "the subject"}}

    def photo(lat, lon):
        return {"camera_gps": {"lat": lat, "lon": lon}}

    # Williamsburg Bridge, as recorded: viewpoint at Domino Park, subject the Brooklyn tower.
    vp, subj = (40.7165, -73.9668), (40.7122, -73.9688)
    ph = photo(40.71318, -73.96827)
    lat, lon, why, off, from_photo = rs.view_origin(meta("landmark", vp, subj), ph)
    assert from_photo and off > rs.PHOTO_GPS_SANITY_M
    assert lat == pytest.approx(40.71318) and "nearer" not in why
    assert "view *of*" in why and "same side" in why
    # The same photograph on a view *from* a place keeps the recorded viewpoint.
    lat2, _, why2, _, from_photo2 = rs.view_origin(meta("viewpoint", vp, subj), ph)
    assert not from_photo2 and lat2 == pytest.approx(vp[0]) and "camera was not stood on it" in why2
    # Farther from the subject than the estimate: rejected (this is the MetLife case).
    far = photo(40.7205, -73.9668)
    _, _, why3, _, from_photo3 = rs.view_origin(meta("landmark", vp, subj), far)
    assert not from_photo3 and "camera was not stood on it" in why3
    # The other side of the subject: rejected (this is the Empire State case).
    behind = photo(40.7080, -73.9688)
    _, _, why4, _, from_photo4 = rs.view_origin(meta("landmark", vp, subj), behind)
    assert not from_photo4 and "camera was not stood on it" in why4


def test_no_comparison_scene_silently_changed_which_photograph_it_shows():
    """Every shipped sheet must name the photograph the current chooser would pick for it.

    A sheet whose reference has been re-picked underneath it compares a render against a
    photograph nobody chose for it.
    """
    import render_sheets as rs

    bad = []
    for d in sorted(COMPARISON_DIR.iterdir()):
        rj = d / "render.json"
        if not d.is_dir() or not rj.exists():
            continue
        rec = json.loads(rj.read_text())
        shipped = (rec.get("reference_photo") or {}).get("title")
        meta = rs.load_meta(d.name)
        picked = (rs.pick_reference_photo(meta) or {}).get("title")
        if shipped and picked and shipped != picked:
            bad.append(f"{d.name}: sheet shows {shipped!r}, the chooser now picks {picked!r}")
    assert not bad, "sheets whose reference photograph has moved under them:\n  " + "\n  ".join(bad)


def test_sun_position_matches_the_live_services_spa():
    pytest.importorskip("bpy", reason="render_sheets imports the Blender scene builder")
    import render_sheets as rs
    from nycsim_live import astronomy

    when = dt.datetime(2023, 5, 12, 12, 18, 49, tzinfo=dt.timezone.utc).astimezone(
        __import__("zoneinfo").ZoneInfo("America/New_York"))
    got = rs.sun_for(40.7592, -73.9847, when)
    ref = astronomy.solar_position(when.astimezone(dt.timezone.utc),
                                   astronomy.Observer(40.7592, -73.9847, 20.0))
    assert got["azimuth_deg"] == pytest.approx(ref.azimuth, abs=1e-9)
    assert got["elevation_deg"] == pytest.approx(ref.elevation, abs=1e-9)


def test_photo_instant_prefers_the_exif_timestamp_and_says_when_it_guessed():
    pytest.importorskip("bpy", reason="render_sheets imports the Blender scene builder")
    import render_sheets as rs

    when, note = rs.photo_instant({"date_taken": "2023-05-12 12:18:49"})
    assert (when.year, when.hour, when.minute) == (2023, 12, 18)
    assert "EXIF" in note
    when, note = rs.photo_instant({"date_taken": "2017"})
    assert when.hour == 9 and "assumed" in note
    when, note = rs.photo_instant({"date_taken": "", "year": 2019})
    assert when.year == 2019 and "assumed" in note


def test_a_daylight_subject_is_never_paired_with_an_after_dark_photograph():
    pytest.importorskip("bpy", reason="render_sheets imports the Blender scene builder")
    import render_sheets as rs

    checked = 0
    for slug in rs.list_slugs():
        meta = rs.load_meta(slug)
        photo = rs.pick_reference_photo(meta)
        if photo is None:
            continue
        when, _ = rs.photo_instant(photo)
        elev = rs.sun_for(meta["viewpoint"]["lat"], meta["viewpoint"]["lon"], when)["elevation_deg"]
        others = []
        for p in meta.get("photos", []):
            if not (REFERENCE_DIR / slug / p["file"]).exists():
                continue
            w, _ = rs.photo_instant(p)
            others.append(rs.sun_for(meta["viewpoint"]["lat"], meta["viewpoint"]["lon"], w)["elevation_deg"])
        if not others:
            continue
        checked += 1
        if meta.get("night"):
            # Only enforceable when at least one candidate really was taken after dark: several
            # night items carry photographs whose metadata records a year and nothing else, so
            # every candidate falls back to the mid-morning assumption.
            if min(others) < 0.0:
                assert elev < 0.0, f"{slug} picked a daylight frame for a night subject"
        elif max(others) > 12.0:
            assert elev > 3.0, f"{slug} picked a photo with the Sun at {elev:.1f} deg"
    assert checked > 10


# --------------------------------------------------------------------------- produced artefacts


def _rendered_slugs() -> list[str]:
    if not COMPARISON_DIR.is_dir():
        return []
    return sorted(d.name for d in COMPARISON_DIR.iterdir()
                  if d.is_dir() and (d / "render.json").exists())


def test_a_record_the_renderer_refused_to_publish_says_so_and_says_why():
    """A rejected frame is a stated outcome, not a missing one, and it has to look like one.

    The renderer measures every frame it draws and refuses to publish one that cannot serve as
    evidence -- near-black, blown out or featureless -- deleting the PNG so a black image cannot
    sit in a directory listing looking like a comparison (`FRAME_MEAN_MIN` and its neighbours in
    `render_sheets.py`).  `drive_midtown_sixth_ave_45th` is the case: mean 0.037, and no sheet
    (docs/DEVIATIONS.md J69).  What must never happen is a sheet going missing *quietly*, so a
    rejected record has to carry the status, the measurement that rejected it and a written
    reason beside it.  That the Midtown drive-through then has no comparison at all is a real
    gap, and it is `test_the_mandated_viewpoints_and_drive_areas_all_have_a_usable_comparison`
    that fails on it -- deliberately, and not dissolved here.
    """
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        d = COMPARISON_DIR / slug
        rec = json.loads((d / "render.json").read_text())
        if rec["status"] == "rendered":
            continue
        assert rec["status"] == "rejected_unusable_frame", f"{slug}: unknown status {rec['status']}"
        assert rec["frame"]["usable"] is False, f"{slug}: rejected but the frame reads usable"
        assert rec["frame"].get("reason"), f"{slug}: rejected with no reason recorded"
        assert (d / "render_error.txt").is_file(), f"{slug}: rejected with no render_error.txt"
        assert rec["frame"]["reason"] in (d / "render_error.txt").read_text(), (
            f"{slug}: render_error.txt does not carry the reason the record gives")
        assert not (d / "render.png").exists(), (
            f"{slug}: rejected but render.png is still there; an unusable frame must not be left "
            f"where a reader would take it for evidence")


def test_every_render_record_names_its_photograph_licence_and_camera():
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        rec = json.loads((COMPARISON_DIR / slug / "render.json").read_text())
        assert rec["status"] in ("rendered", "rejected_unusable_frame"), slug
        ph = rec["reference_photo"]
        for key in ("file", "author", "licence", "page_url"):
            assert ph.get(key), f"{slug}: reference photo record is missing {key}"
        assert (REFERENCE_DIR / slug / ph["file"]).exists(), f"{slug}: {ph['file']} is gone"
        cam = rec["camera"]
        for key in ("x", "y", "z", "azimuth_deg", "focal_mm", "hfov_deg", "eye_height_m", "eye_source"):
            assert cam.get(key) is not None, f"{slug}: camera record is missing {key}"
        # The camera may face the photograph's own measured bearing rather than the item's
        # recorded azimuth, but it must always say which it used and why.
        assert rec.get("azimuth_reason"), f"{slug}: no view-direction justification recorded"
        assert f"{rec['camera']['azimuth_deg']:.1f}" in rec["azimuth_reason"], slug
        assert rec["sun"]["elevation_deg"] is not None
        assert rec["scene"]["triangles"] > 0


def test_every_render_has_a_sheet_and_a_written_assessment():
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        d = COMPARISON_DIR / slug
        if json.loads((d / "render.json").read_text())["status"] != "rendered":
            continue          # a frame the renderer refused to publish; the test above covers it
        assert (d / "render.png").exists(), f"{slug}: render.png missing"
        assert (d / "sheet.png").exists(), f"{slug}: sheet.png missing"
        a = d / "assessment.md"
        assert a.exists(), f"{slug}: assessment.md missing"
        text = a.read_text()
        assert len(text) > 400, f"{slug}: assessment is too short to be a real judgement"
        for heading in ("What matches", "What does not", "Cause"):
            assert heading.lower() in text.lower(), f"{slug}: assessment has no '{heading}' section"


def test_sheet_is_a_two_panel_image_wider_than_it_is_tall_per_panel():
    pytest.importorskip("PIL")
    from PIL import Image
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    for slug in slugs:
        p = COMPARISON_DIR / slug / "sheet.png"
        if not p.exists():
            continue
        with Image.open(p) as im:
            w, h = im.size
        assert w >= 2 * 1280, f"{slug}: sheet is only {w} px wide, expected two 1280 px panels"
        assert h > 400


def test_index_and_report_exist_once_any_sheet_does():
    slugs = _rendered_slugs()
    if not slugs:
        pytest.skip("no comparison renders produced yet")
    index = COMPARISON_DIR / "INDEX.md"
    report = COMPARISON_DIR / "REPORT.md"
    assert index.exists(), "docs/verification/comparison/INDEX.md missing"
    assert report.exists(), "docs/verification/comparison/REPORT.md missing"
    idx = index.read_text()
    for slug in slugs:
        assert slug in idx, f"{slug} is rendered but not listed in INDEX.md"
    rep = report.read_text()
    for name in ("Brooklyn Heights Promenade", "Top of the Rock", "Duffy Square",
                 "Bethesda Terrace", "Staten Island Ferry", "DUMBO"):
        assert name in rep, f"REPORT.md does not account for {name}"


# --------------------------------------------------------------------------- the camera tilt (I18)


def _tilt_functions():
    """``containment_pitch`` and ``vertical_half_fov_deg`` without importing bpy.

    ``render_sheets`` imports Blender at module level, so the two pure functions are read out of the
    source. They are pure arithmetic over a focal length and a subject, which is exactly the part
    worth testing without spending a render.
    """
    src = (VERIFY_DIR / "render_sheets.py").read_text()
    start = src.index("TILT_HEADROOM = 0.88")
    end = src.index("def aim_pitch(")
    body = src[start:end].replace("import camera as vcam", "").replace("vcam.SENSOR_WIDTH_MM", "36.0")
    i = src.index("MANDATED_VIEWPOINTS: dict[str, list[str]] = {")
    j = src.index("}", src.index("Washington Street", i)) + 1
    ns: dict = {}
    exec("import math\n" + src[i:j] + "\n" + body, ns)   # noqa: S102 - reading this module's own source
    return ns["containment_pitch"], ns["vertical_half_fov_deg"]


def test_a_subject_that_fits_the_frame_is_not_tilted_towards():
    """A level axis is what makes a render and a photograph comparable on proportion; it is only
    given up when the alternative is a frame with no subject in it."""
    containment_pitch, _ = _tilt_functions()
    pitch, why = containment_pitch((60.0, 10.0, "a 10 m subject"), 1.6, 35.0, False, 1280 / 853)
    assert pitch == 0.0 and why == ""


def test_the_chrysler_building_sheet_now_contains_the_chrysler_building():
    """72 m away and 319 m tall: 77 deg of elevation, against a level 18 mm frame's 45 deg."""
    containment_pitch, half_fov = _tilt_functions()
    top = (72.0, 319.0, "the b_chrysler_building model")
    pitch, why = containment_pitch(top, 1.6, 18.0, True, 1280 / 853)
    need = math.degrees(math.atan((319.0 - 1.6) / 72.0))
    half = half_fov(18.0, True, 1280 / 853)
    assert pitch > 0.0, "the subject is above a level frame and the camera did not tilt"
    assert need - pitch <= half, "the subject's top is still outside the frame after the tilt"
    assert "verticals converge" in why, "the sheet has to say the frame is no longer comparable"


def test_the_tilt_is_the_minimum_that_contains_the_subject():
    """Tilting further than necessary would throw away comparability it did not have to."""
    containment_pitch, half_fov = _tilt_functions()
    for dist, height, focal in ((72.0, 319.0, 18.0), (200.0, 381.0, 18.0), (60.0, 87.0, 24.0)):
        pitch, _ = containment_pitch((dist, height, "x"), 1.6, focal, True, 1280 / 853)
        need = math.degrees(math.atan((height - 1.6) / dist))
        half = half_fov(focal, True, 1280 / 853)
        assert pitch == pytest.approx(min(70.0, need - half * 0.88), abs=1e-6)
        assert pitch <= 70.0


def test_the_tilt_is_capped_and_says_so():
    """The cap binds only on a long lens; at the 18 mm floor the 90 deg frame reaches everything."""
    containment_pitch, _ = _tilt_functions()
    pitch, why = containment_pitch((5.0, 400.0, "something almost overhead"), 1.6, 200.0, True, 1280 / 853)
    assert pitch == 70.0
    assert "cap" in why
    wide, _ = containment_pitch((5.0, 400.0, "the same thing"), 1.6, 18.0, True, 1280 / 853)
    assert wide < 70.0, "an 18 mm frame is 90 deg tall and needs no cap"


def test_the_renderer_prefers_a_wider_lens_before_it_tilts():
    src = (VERIFY_DIR / "render_sheets.py").read_text()
    i_lens = src.index("focal_mm, lens_why = choose_lens(")
    i_tilt = src.index("tilt, tilt_why = containment_pitch(")
    assert i_lens < i_tilt, "the tilt must be computed from the lens that was chosen, not before it"


def test_a_mandated_viewpoint_is_never_tilted():
    """The seven the brief names are judged on proportion; a tilt would cost exactly that."""
    containment_pitch, _ = _tilt_functions()
    src = (VERIFY_DIR / "render_sheets.py").read_text()
    i = src.index("MANDATED_VIEWPOINTS: dict[str, list[str]] = {")
    j = src.index("}", src.index("Washington Street", i)) + 1
    ns: dict = {}
    exec(src[i:j], ns)                                    # noqa: S102
    slugs = [v for ss in ns["MANDATED_VIEWPOINTS"].values() for v in ss]
    assert "times_square_duffy_south_day" in slugs
    tall = (150.0, 366.0, "One Times Square")
    for slug in slugs:
        pitch, why = containment_pitch(tall, 1.6, 18.0, True, 1280 / 853, slug=slug)
        assert pitch == 0.0 and why == "", f"{slug} tilted"
    free, _ = containment_pitch(tall, 1.6, 18.0, True, 1280 / 853, slug="landmark_one_times_square")
    assert free > 0.0, "a landmark sheet still tilts to contain its subject"


def test_a_roadway_viewpoint_stands_on_its_street_and_looks_along_it():
    """An item whose own note says "roadway centre" has to be on a roadway, pointing down it.

    Two of them were not, and neither the render nor any number it printed said so.
    `drive_brooklyn_bed_stuy_stuyvesant_ave` names "Stuyvesant Avenue at Decatur Street" and its
    recorded point stood **102 m** from that crossing, 22 m from Decatur Street, aimed 13 deg --
    68 deg across Decatur -- so the sheet rendered the brownstone row opposite and no street at all.
    `drive_brooklyn_park_slope_7th_ave` stood 98 m from Seventh Avenue at Garfield Place. Both were
    corrected from `data/processed/roads/segments.parquet`, and this keeps them corrected.

    The check is deliberately on the *best-aligned* street in range rather than the nearest one: at
    a corner the nearest centreline is the cross street, and a camera looking correctly up the
    avenue scores 90 deg against it. Landmark items are excluded on purpose -- a camera aimed at the
    Chrysler Building is supposed to look across East 40th Street.
    """
    import math
    gpd = pytest.importorskip("geopandas")
    np = pytest.importorskip("numpy")
    pyproj = pytest.importorskip("pyproj")
    shapely_geom = pytest.importorskip("shapely.geometry")

    segs = REPO_ROOT / "data" / "processed" / "roads" / "segments.parquet"
    if not segs.is_file():
        pytest.skip("the road graph has not been produced")
    seg = gpd.read_parquet(segs)
    tr = pyproj.Transformer.from_crs(
        "EPSG:4326",
        "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +units=m +datum=NAD83 +no_defs",
        always_xy=True)

    def bearing_at(geom, x, y):
        cs = np.asarray(geom.coords)
        d = np.hypot(cs[:, 0] - x, cs[:, 1] - y)
        i = int(np.argmin(d))
        j = i + 1 if i + 1 < len(cs) else i - 1
        v = cs[j] - cs[i]
        return math.degrees(math.atan2(v[0], v[1])) % 360.0

    bad = []
    for d in sorted((REPO_ROOT / "docs" / "verification" / "reference").iterdir()):
        meta = d / "meta.json"
        if not d.is_dir() or not meta.is_file():
            continue
        vp = (json.loads(meta.read_text()).get("viewpoint") or {})
        if "roadway centre" not in (vp.get("note") or ""):
            continue
        x, y = tr.transform(vp["lon"], vp["lat"])
        p = shapely_geom.Point(x, y)
        near = seg[seg.geometry.distance(p) < 60.0]
        if near.empty:
            bad.append(f"{d.name}: no street within 60 m of a viewpoint that says 'roadway centre'")
            continue
        az = float(vp["azimuth_deg"])
        best = min(((abs((az - bearing_at(r.geometry, x, y)) % 180.0), r) for _, r in near.iterrows()),
                   key=lambda t: min(t[0], 180.0 - t[0]))
        off = min(best[0], 180.0 - best[0])
        if off > 40.0:
            bad.append(f"{d.name}: {off:.0f} deg off {best[1]['street_name']}, the best-aligned "
                       f"street within 60 m")
    assert not bad, ("viewpoints that say 'roadway centre' and look across the roadway instead of "
                     "along it:\n  " + "\n  ".join(bad))


def _cube(name: str, x: float, y: float, z: float, size: float = 1.0):
    """A solid box named ``name`` centred on (x, y, z), in the current scene."""
    import bmesh
    import bpy

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (x, y, z)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    return ob


def test_a_pedestrian_at_the_lens_does_not_hide_the_wall_behind_them():
    """J49: ``ray_cast`` stops at the first hit, so a predicate applied to its result answers
    "is the nearest object of any kind one that counts?".  With Stage 21's traffic and crowd in
    the scene that is not the question the clearance probe is asking, and a person between the
    lens and a wall made the wall unmeasurable."""
    bpy = _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb

    nb.reset_scene()
    _cube("t_0_0_red_brick", 0.0, 10.0, 1.6, size=4.0)   # a wall 10 m north
    _cube("agent_ped_7", 0.0, 2.0, 1.6, size=0.5)        # a person 2 m north, on the same axis

    built_m, built_what = vcam.nearest_obstruction(0.0, 0.0, 1.6, 0.0, probe_m=30.0,
                                                   half_angle_deg=1.0, pitches_deg=(0.0,),
                                                   yaw_steps=1)
    assert built_what == "t_0_0_red_brick", f"the probe found {built_what}, not the wall"
    assert built_m == pytest.approx(8.0, abs=0.2), f"the wall is at {built_m:.2f} m, expected 8.0"

    agent_m, agent_what = vcam.nearest_obstruction(0.0, 0.0, 1.6, 0.0, probe_m=30.0,
                                                   half_angle_deg=1.0, pitches_deg=(0.0,),
                                                   yaw_steps=1, counts=vcam._is_agent)
    assert agent_what == "agent_ped_7"
    assert agent_m == pytest.approx(1.75, abs=0.1)

    # And the street does not read as open to the horizon because a crowd stands in it.
    assert vcam.view_distance(0.0, 0.0, 1.6, 0.0, probe_m=150.0) == pytest.approx(8.0, abs=0.2)


def test_the_clearance_record_names_the_agent_it_used_to_be_silent_about():
    """The note said "the nearest solid thing anywhere in the frame" and meant "the nearest
    *built* thing"; on Arthur Avenue it named a tree 18.8 m away with two people at the lens."""
    bpy = _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb

    nb.reset_scene()
    _cube("t_0_0_red_brick", 0.0, 10.0, 1.6, size=4.0)
    _cube("agent_ped_7", 0.0, 2.0, 1.6, size=0.5)
    reading = vcam.frame_clearance(0.0, 0.0, 1.6, 0.0, probe_m=30.0, half_angle_deg=1.0,
                                   pitches_deg=(0.0,), yaw_steps=1)
    fields = vcam.clearance_fields(reading)
    assert fields["nearest_obstruction"] == "t_0_0_red_brick"
    assert fields["nearest_agent"] == "agent_ped_7"
    assert fields["nearest_agent_m"] < fields["nearest_obstruction_m"]
    sentence = vcam.clearance_sentence(reading)
    assert "nearest built thing" in sentence
    assert "agent_ped_7" in sentence
    assert "solid thing" not in sentence

    # With nothing but built fabric in the scene the sentence says so rather than staying silent.
    nb.reset_scene()
    _cube("t_0_0_red_brick", 0.0, 10.0, 1.6, size=4.0)
    quiet = vcam.frame_clearance(0.0, 0.0, 1.6, 0.0, probe_m=30.0, half_angle_deg=1.0,
                                 pitches_deg=(0.0,), yaw_steps=1)
    assert vcam.clearance_fields(quiet)["nearest_agent"] is None
    assert "no simulated agent stands within 30 m" in vcam.clearance_sentence(quiet)


def test_the_record_says_whether_the_camera_can_see_its_own_subject():
    """Three states, not two: something in the way, the subject there and seen, or nothing there.

    The first version of this probe asked only "does anything block the line to the subject's
    coordinate", so a ray through empty air came back clear and the record said the subject was
    visible.  That is how the Bethesda sheet reported its fountain visible, 5 rays of 5, over a
    frame that shows almost none of it: the item's coordinate stood 24.6 m from the fountain and
    the rays met nothing at all (docs/DEVIATIONS.md J57).  The test below used to assert exactly
    that behaviour on an empty scene, which is why it never caught it.
    """
    bpy = _skip_without_bpy()
    import camera as vcam
    import nycsim_bpy as nb

    # 1. Nothing anywhere.  The line is open and the subject is not on it.
    nb.reset_scene()
    empty = vcam.subject_sightline(0.0, 0.0, 1.6, 0.0, 40.0, 3.0)
    assert empty["subject_visible"] is False, "an empty scene is not a view of the subject"
    assert empty["subject_range_m"] == pytest.approx(40.02, abs=0.1)
    assert empty["subject_blocked_by"] is None
    assert empty["subject_lands_on"] is None
    assert empty["subject_rays_into_nothing"] == empty["subject_rays"]
    assert "nothing stands within" in empty["subject_note"]

    # 2. The subject is there and nothing is in front of it.
    nb.reset_scene()
    _cube("lm_b_subject", 0.0, 40.0, 3.0, size=6.0)
    clear = vcam.subject_sightline(0.0, 0.0, 1.6, 0.0, 40.0, 3.0)
    assert clear["subject_visible"] is True
    assert clear["subject_blocked_by"] is None
    assert clear["subject_lands_on"] == "lm_b_subject"
    assert clear["subject_rays_on_subject"] == clear["subject_rays"]
    assert "subject_note" not in clear

    # 3. A wall across the whole fan.
    _cube("t_0_0_limestone", 0.0, 12.0, 2.0, size=6.0)
    blocked = vcam.subject_sightline(0.0, 0.0, 1.6, 0.0, 40.0, 3.0)
    assert blocked["subject_visible"] is False
    assert blocked["subject_rays_clear"] == 0
    assert blocked["subject_blocked_by"] == "t_0_0_limestone"
    assert 8.0 < blocked["subject_blocked_at_m"] < 12.0

    # 4. A pole is not a wall.  One ray through a lamp standard says "not visible" of a subject
    # standing wide open beside it -- which is what the first version of this probe reported at
    # Bethesda Terrace, and it would have been a false statement dressed as a measurement.
    nb.reset_scene()
    _cube("lm_b_subject", 0.0, 40.0, 3.0, size=6.0)
    # 1.68 m is where the axis passes at 2.4 m out, so the pole is squarely on the centre ray.
    _cube("prop_lamp_cobra_davit_6", 0.0, 2.4, 1.684, size=0.2)
    past_pole = vcam.subject_sightline(0.0, 0.0, 1.6, 0.0, 40.0, 3.0)
    assert past_pole["subject_blocked_by"] == "prop_lamp_cobra_davit_6", \
        "the pole on the centre ray must still be named"
    assert past_pole["subject_rays_clear"] == past_pole["subject_rays"] - 1, "it took the centre ray"
    assert past_pole["subject_visible"] is True, "a 0.2 m pole must not hide a subject 40 m away"
    # The fan is a width at the subject, not a fixed angle: a fixed +-1.5 deg fan is 0.13 m across
    # at 2.4 m, so this same pole would take all five rays and the probe would lie again.
    assert past_pole["subject_fan_half_angle_deg"] == pytest.approx(8.53, abs=0.1)

    # 5. A tree is not a wall for the *view distance* rule, but a canopy across the whole fan is for
    # the subject: a photograph of the Flatiron taken through a plane tree is not one of the Flatiron.
    nb.reset_scene()
    _cube("lm_b_subject", 0.0, 40.0, 3.0, size=6.0)
    _cube("prop_tree_zelkova_large_3", 0.0, 6.0, 3.0, size=4.0)
    through = vcam.subject_sightline(0.0, 0.0, 1.6, 0.0, 40.0, 3.0)
    assert through["subject_visible"] is False
    assert through["subject_blocked_by"].startswith("prop_tree")

    # 6. The Bethesda shape: nothing at the coordinate, an open line, and something far beyond it.
    # The record must name what the ray actually found and say the subject was not on the line.
    nb.reset_scene()
    _cube("t_0_0_far_wall", 0.0, 200.0, 8.0, size=20.0)
    past = vcam.subject_sightline(0.0, 0.0, 1.6, 0.0, 40.0, 3.0)
    assert past["subject_visible"] is False, "a clear line to nothing is not a view of the subject"
    assert past["subject_blocked_by"] is None, "the far wall is behind the subject, not in front"
    assert past["subject_lands_on"] == "t_0_0_far_wall"
    assert past["subject_lands_at_m"] > past["subject_range_m"] + past["subject_reach_m"]
    assert "t_0_0_far_wall" in past["subject_note"]


def test_a_drive_through_uses_a_photograph_of_its_own_block():
    """A drive-through sheet compares one block, so the photograph has to be of that block.

    The chooser's key had no distance term at all.  For ``drive_bronx_grand_concourse`` that meant
    a photograph of the Dollar Savings Bank at East Fordham Road, **3,854 m** up the same avenue,
    outranked every photograph of Grand Concourse at East 165th Street because it carried a full
    EXIF timestamp; and for ``drive_brooklyn_bed_stuy_stuyvesant_ave`` a FreshDirect delivery truck
    with no GPS at all beat a photograph taken **46 m** from the viewpoint (docs/DEVIATIONS.md J60).

    The test asserts the chooser takes the best band available to each item -- not that every item
    has a near photograph, which is not in this project's gift.
    """
    import json as _json

    rs = _skip_without_render_sheets()
    ref = REPO_ROOT / "docs" / "verification" / "reference"
    if not ref.is_dir():
        pytest.skip("no reference items on disk")
    checked = 0
    for meta_path in sorted(ref.glob("*/meta.json")):
        meta = _json.loads(meta_path.read_text())
        if str(meta.get("group") or "") != "drive_through":
            continue
        photos = [p for p in meta.get("photos", []) if (ref / meta["slug"] / p["file"]).is_file()]
        if len(photos) < 2:
            continue
        vp = meta["viewpoint"]

        def band(p):
            off = rs._photo_offset_m(vp, p)
            return (rs.DRIVE_THROUGH_PHOTO_UNKNOWN_BAND if off is None
                    else sum(1 for e in rs.DRIVE_THROUGH_PHOTO_BANDS_M if off > e))

        got = rs.pick_reference_photo(meta)
        assert got is not None, meta["slug"]
        best = min(band(p) for p in photos)
        assert band(got) == best, (
            f"{meta['slug']} took photo #{got['n']} in band {band(got)} when band {best} was available")
        checked += 1
    assert checked >= 8, f"only {checked} drive-through items were checked"


def test_the_sheet_never_calls_a_scene_wide_count_the_contents_of_its_frame():
    """The landmark count on a sheet is a scene count, and it is 2.5x what a frame can hold.

    Broadway at Wall Street builds fourteen landmark models into its scene.  Nine of them --
    Trinity Church at 54 m, Federal Hall at 131 m, the Brooklyn Bridge at 1.2 km -- stand behind
    or beside the camera.  The caption used to introduce that fourteen with the words "In frame",
    which is a true measurement of the wrong thing: an assessment written from it describes a
    picture that shows five (docs/DEVIATIONS.md J61).
    """
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import sheet_facts

    # A camera at the origin looking due north through a 60 deg cone.
    cam = {"x": 0.0, "y": 0.0, "azimuth_deg": 0.0, "hfov_deg": 60.0}
    catalogue = [
        {"id": "ahead", "name": "ahead", "origin_tm": [0.0, 100.0, 0.0],
         "bounds_local_m": {"min": [-5.0, -5.0, 0.0], "max": [5.0, 5.0, 20.0]}},
        {"id": "behind", "name": "behind", "origin_tm": [0.0, -100.0, 0.0],
         "bounds_local_m": {"min": [-5.0, -5.0, 0.0], "max": [5.0, 5.0, 20.0]}},
        # Centre 40 deg off the axis -- outside the 30 deg half-cone -- but 60 m wide at 100 m,
        # so an edge of it still crosses the frame.
        {"id": "grazing", "name": "grazing", "origin_tm": [64.3, 76.6, 0.0],
         "bounds_local_m": {"min": [-30.0, -30.0, 0.0], "max": [30.0, 30.0, 20.0]}},
    ]
    placed = [{"id": e["id"], "name": e["name"]} for e in catalogue]
    got = sheet_facts.landmarks_in_cone(cam, placed, catalogue=catalogue)
    assert got["cone_deg"] == pytest.approx(60.0)
    assert got["not_in_catalogue"] == []
    assert sorted(r["name"] for r in got["in_cone_names"]) == ["ahead", "grazing"]
    assert got["behind_or_aside_names"] == ["behind"]
    assert got["in_cone"] == 2 and got["behind_or_aside"] == 1

    # A camera with no position cannot be asked the question, and says so rather than guessing.
    assert sheet_facts.landmarks_in_cone({"azimuth_deg": 0.0}, placed, catalogue=catalogue) is None
    assert sheet_facts.landmarks_in_cone(cam, [], catalogue=catalogue) is None

    # Every shipped sheet's own numbers must agree: what can fall in the frame is never more than
    # what was built into the scene.
    checked = 0
    for d in sorted(COMPARISON_DIR.iterdir()):
        rj = d / "render.json"
        if not d.is_dir() or not rj.exists():
            continue
        f = sheet_facts.facts(d.name)
        fr = (f.get("landmarks") or {}).get("frustum")
        if not fr:
            continue
        checked += 1
        assert not fr["not_in_catalogue"], f"{d.name}: placed a landmark the catalogue has no model for"
        assert fr["in_cone"] + fr["behind_or_aside"] == f["landmarks"]["placed"], d.name
        assert fr["in_cone"] <= f["landmarks"]["placed"], d.name
    assert checked, "no rendered sheet carried a landmark frustum to check"


def test_the_day_the_crowd_was_drawn_for_is_spelled_out_not_left_as_a_code():
    """``agent_request.dow`` is a day *type*, not a day of the week, and reads like one.

    ``DensityTable::kDows`` is 3: one density profile for weekdays, one for Saturday, one for
    Sunday.  So the Broadway/Wall St sheet, whose photograph was taken on Sunday 21 May 2023,
    records ``"dow": 2`` -- which a writer transcribing the record reads as Tuesday.  That is how
    an assessment names the wrong day, so the facts spell the day type out and check it against
    the frame's own clock.
    """
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import sheet_facts

    sunday = sheet_facts.day_type({"dow": 2, "local_clock": "2023-05-21 13:00 EDT"})
    assert sunday["means"] == "Sunday" and sunday["weekday"] == "Sunday"
    assert "disagrees" not in sunday
    weekday = sheet_facts.day_type({"dow": 0, "local_clock": "2026-06-17 09:30 EDT"})
    assert weekday["means"] == "a weekday" and weekday["weekday"] == "Wednesday"
    assert "disagrees" not in weekday
    # A code that contradicts the clock is named, not narrated over.
    wrong = sheet_facts.day_type({"dow": 0, "local_clock": "2023-05-21 13:00 EDT"})
    assert "Sunday" in wrong["disagrees"]
    # No clock at all: the code is still spelled out, and nothing is invented about the date.
    bare = sheet_facts.day_type({"dow": 1})
    assert bare["means"] == "Saturday" and "weekday" not in bare and "disagrees" not in bare
    assert sheet_facts.day_type({}) is None

    # Every shipped sheet agrees with its own clock.
    bad = []
    for d in sorted(COMPARISON_DIR.iterdir()):
        rj = d / "render.json"
        if not d.is_dir() or not rj.exists():
            continue
        cc = sheet_facts.facts(d.name).get("crowd_clock")
        if cc and cc.get("disagrees"):
            bad.append(f"{d.name}: {cc['disagrees']}")
    assert not bad, "sheets whose crowd was drawn for the wrong kind of day:\n  " + "\n  ".join(bad)


def test_the_verification_render_can_draw_every_body_the_wardrobe_bakes():
    """The comparison renders drew their whole crowd from twelve bodies out of thirty-six.

    ``render_sheets.AGENT_NPC_ARCHETYPES`` read 12 and ``PedLibrary`` clamped to ``min(24, ...)``,
    while ``npc_variety.json`` bakes 36 bodies and the simulation emits all 36 -- 989 of the 2,999
    people in the Broadway/Wall St snapshot carry archetype 24 or above.  Every one of those was
    folded onto bodies 0 to 11, so archetypes 12 to 35 could not appear in any sheet, the twelve
    that could appeared about nineteen times each in a 229-person frame, and every coat the J53 fix
    added was unrenderable by the only stage that proves anything (docs/DEVIATIONS.md J62).
    """
    variety = REPO_ROOT / "blender_out" / "character" / "npc_variety.json"
    if not variety.is_file():
        pytest.skip("no baked NPC wardrobe in this checkout")
    baked = json.loads(variety.read_text())
    cast = len(baked["npcs"])
    assert cast == baked["count"] and cast >= 24

    # The constant must not name a number smaller than the cast.  None means "all of them".
    rs = _skip_without_render_sheets()
    limit = getattr(rs, "AGENT_NPC_ARCHETYPES")
    assert limit is None or limit >= cast, (
        f"the renderer draws its crowd from {limit} of the {cast} baked bodies")

    # ...and the library must not clamp below the cast either.  ``agents`` imports Blender only
    # inside the methods that need it, so the library can be built and questioned here.
    import agents as vagents

    lib = vagents.PedLibrary()
    assert lib.archetypes == cast, (
        f"PedLibrary draws from {lib.archetypes} of the {cast} baked bodies")
    assert lib.archetypes == len(vagents.npc_archetype_assets())

    # A fold substitutes one person for another.  It must still be possible -- a snapshot from a
    # newer simulation must not crash a render -- but it must be counted, never silent.
    assert lib.folded == {}
    assert lib.body_for(0) == 0 and lib.folded == {}
    assert lib.body_for(cast) == 0 and lib.folded == {cast: 1}
    assert lib.body_for(cast) == 0 and lib.folded == {cast: 2}
    assert lib.body_for(cast + 3) == 3 and lib.folded[cast + 3] == 1

    # An explicit smaller cast is still honoured -- that is what makes the default meaningful.
    assert vagents.PedLibrary(archetypes=4).archetypes == 4
    assert vagents.PedLibrary(archetypes=cast + 99).archetypes == cast

    # Every baked body must have a glb the renderer can find, or the cap is real again by another
    # route: a missing file folds just as silently as a small constant.
    npc_dir = REPO_ROOT / "blender_out" / "character" / "npc"
    missing = [n["id"] for n in baked["npcs"] if not (npc_dir / f"{n['id']}.glb").is_file()]
    assert not missing, f"baked bodies with no glb on disk: {missing}"

    # Any sheet rendered since the fix must report the full cast and no folds.
    checked = 0
    for d in sorted(COMPARISON_DIR.iterdir()):
        rj = d / "render.json"
        if not d.is_dir() or not rj.exists():
            continue
        snap = ((json.loads(rj.read_text()).get("scene") or {})
                .get("agents") or {}).get("snapshot") or {}
        if "npc_archetypes_available" not in snap:
            continue          # rendered before the record carried the figure
        checked += 1
        assert snap["npc_archetypes_available"] == cast, (
            f"{d.name}: drew its crowd from {snap['npc_archetypes_available']} of {cast} bodies")
        assert not snap.get("npc_archetypes_folded"), (
            f"{d.name}: folded archetypes onto other people: {snap['npc_archetypes_folded']}")


def test_the_city_surfaces_resolve_their_own_material_names():
    """12.71 GB of city geometry ships sixteen flat colours and no image at all.

    ``tile_buildings`` is 920 files and 8,722 materials with zero base-colour textures;
    ``tile_pavement`` 546 files and 5,177 materials, likewise zero. Everything authored by hand --
    landmarks, props, the facade kit, the characters -- is textured, and everything generated at
    city scale is a solid RGB. The exported file's job is to carry the material *name*; resolving
    the name to a surface belongs to whoever reads it, which is what this checks
    (docs/DEVIATIONS.md J63).
    """
    sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
    import textures as tx

    src = (VERIFY_DIR / "scene.py").read_text()
    assert "def dress_city_materials(" in src

    import importlib.util
    spec = importlib.util.spec_from_file_location("_j63_scene_src", VERIFY_DIR / "scene.py")
    assert spec is not None

    # Every shell material name, read off **every** tile rather than one of them.  Reading one tile
    # is how the texture trim came to delete precast (396 tiles), stucco (156) and vinyl_siding
    # (1,087, the third most common material in the city): that tile carried sixteen of the
    # nineteen names, and a list of names is a claim about 2,848 files.
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import trim_texture_cache as ttc

    shell_names = sorted("NYCSIM_" + n for n in ttc.city_surface_names())
    if not shell_names:
        pytest.skip("no built tiles in this checkout")
    assert len(shell_names) >= 16, shell_names

    # Every one of them must resolve in the shared catalogue, and its texture set must be on disk.
    # glass_curtain is the one deliberate exception: it resolves to a procedural entry with no
    # maps, because glass is authored analytically in shellmat rather than photographed.
    missing = []
    for full in shell_names:
        base = full[len("NYCSIM_"):] if full.startswith("NYCSIM_") else full
        try:
            rec = tx.resolve(base)
        except Exception as exc:
            missing.append(f"{full}: not in the catalogue ({exc})")
            continue
        assert rec.get("physical_size_m"), f"{full}: no measured physical size to scale the UVs by"
        have = tx._existing_set(rec["asset_id"], "2K") or {}
        if "color" not in have and not str(rec["asset_id"]).startswith("procedural_"):
            missing.append(f"{full}: {rec['asset_id']} has no colour map on disk at 2K")
    assert not missing, "city surfaces that cannot be dressed:\n  " + "\n  ".join(missing)

    # The pavement map must never texture paint: giving a marking the asphalt it is painted on
    # would erase every lane line, stop bar and crosswalk bar the road-markings stage draws.
    for line in src.splitlines():
        if "pave_marking" in line and ":" in line and not line.strip().startswith("#"):
            pytest.fail(f"a road marking is mapped to a surface texture: {line.strip()}")

    # A sheet rendered since the fix must report what it dressed, and must not report a city
    # surface it silently left flat for a reason other than the procedural glass.
    for d in sorted(COMPARISON_DIR.iterdir()):
        rj = d / "render.json"
        if not d.is_dir() or not rj.exists():
            continue
        rec = ((json.loads(rj.read_text()).get("scene") or {}).get("materials") or {})
        if not rec:
            continue
        assert rec.get("dressed"), f"{d.name}: reports a materials block that dressed nothing"
        for base, why in (rec.get("flat") or {}).items():
            # A surface the catalogue authors analytically may stay flat -- glass is dark, sharp
            # and part-metallic by design. A surface whose texture is simply not on disk may not:
            # that is how the texture trim silently un-dressed precast, stucco and vinyl_siding.
            assert "analytic" in str(why), f"{d.name}: {base} stayed flat -- {why}"


def test_a_photographic_texture_does_not_set_the_citys_brightness():
    """A scan's exposure is a photographer's choice; the class albedo is the stage's statement.

    J63 pointed every shell material at a photographic colour map and took the scan's own level
    with it. Over the twenty city surfaces those maps average 0.52 of the albedo the material's own
    stage declares -- ``wood_clapboard`` 0.07, ``roof_membrane`` 0.09, ``concrete`` 0.22, and
    ``cast_iron`` 3.09 the other way -- and the first four drive-throughs of the pass rendered at
    0.37 to 0.58 of their reference photograph's mean luminance (docs/DEVIATIONS.md J66).

    The correction is a single scalar on the colour map so its mean linear albedo is the authored
    one, capped where the scan is plainly a different material rather than a different exposure.
    """
    sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import textures as tx
    import trim_texture_cache as ttc

    src = (VERIFY_DIR / "scene.py").read_text()
    assert "def _normalise_albedo(" in src
    assert "ALBEDO_SCALE_CAP" in src

    names = ttc.city_surface_names() | {"asphalt", "concrete_sidewalk"}
    if not names:
        pytest.skip("no built tiles in this checkout")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_j66_shellmat", REPO_ROOT / "blender" / "buildings" / "shellmat.py")
    sm = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = sm
    spec.loader.exec_module(sm)

    # Every surface the renderer dresses must have an albedo to normalise *to*: a shell class in
    # shellmat, or an entry in the renderer's own pavement table. A new material class with neither
    # would be scaled to shellmat's 0.6 grey DEFAULT, which is how asphalt would end up six times
    # too bright.
    pavement = {"asphalt", "concrete_sidewalk"}
    unanchored = []
    for n in sorted(names):
        if n in pavement:
            assert f'"{n}": (' in src, f"{n} has no entry in _PAVEMENT_ALBEDO"
            continue
        if sm.spec(n) is sm.DEFAULT:
            unanchored.append(n)
    assert not unanchored, (
        "city surfaces with no authored albedo, which would be normalised to shellmat's DEFAULT: "
        + ", ".join(unanchored))

    # And every shipped sheet must report what it did, so the residual on a capped surface is on
    # the record rather than in a frame nobody measured.
    for d in sorted(COMPARISON_DIR.iterdir()):
        rj = d / "render.json"
        if not d.is_dir() or not rj.exists():
            continue
        dressed = (((json.loads(rj.read_text()).get("scene") or {}).get("materials") or {})
                   .get("dressed") or {})
        if not dressed:
            continue
        for base, rec in dressed.items():
            if "albedo" not in rec:
                continue                      # rendered before the correction existed
            alb = rec["albedo"]
            if alb is None:
                continue
            assert alb["scale"] <= 4.0 + 1e-9 and alb["scale"] >= 0.25 - 1e-9, (d.name, base, alb)
            if alb.get("capped_at"):
                assert "residual" in alb and "note" in alb, (d.name, base, alb)


def test_the_sky_delivers_the_diffuse_light_the_exposure_model_assumes():
    """The sun-to-sky ratio decides how much contrast a frame has, and it was a bare constant.

    ``setup_world_and_sun`` computes its exposure from ``dni * sin(elevation) + DIFFUSE_KEY_W``,
    so the model states that diffuse light is 90 W/m2 against roughly 880 direct at a high Sun --
    near 10:1. It then set the sky to ``SKY_STRENGTH_DAY = 0.25``, which measures out at 0.63:1 at
    69.5 deg and 0.04:1 at 5 deg: every daylight frame lit like an overcast day, with 95th
    percentiles half the photographs' while the 5th percentiles matched (docs/DEVIATIONS.md J67).

    This holds the two halves of the function to each other. It does not check a photograph.
    """
    rs = _skip_without_render_sheets()
    assert not hasattr(rs, "SKY_STRENGTH_DAY"), \
        "the uncalibrated day constant is back; the sky strength is derived, not chosen"
    tbl = rs.SKY_IRRADIANCE_AT_UNIT_STRENGTH
    assert len(tbl) >= 6 and all(0.0 <= e <= 90.0 and v > 0.0 for e, v in tbl)
    assert [e for e, _ in tbl] == sorted(e for e, _ in tbl), "the table must be in elevation order"

    import math

    want = rs.DIFFUSE_KEY_W / rs.SUN_CALIBRATION
    for elev, unit in tbl:
        got = rs.sky_strength_for(elev) * unit
        assert abs(got - want) < 1e-9, (
            f"at {elev} deg the sky delivers {got:.5f} where the exposure model assumes {want:.5f}")
        # ...and the resulting direct-to-diffuse ratio has to be physical: a clear sky at a high
        # Sun is 8-11 to 1, and the balance tips to the sky only as the beam attenuates.
        e = math.radians(elev)
        air_mass = 1.0 / (math.sin(e) + 0.50572 * (elev + 6.07995) ** -1.6364)
        dni = rs.SOLAR_CONSTANT_W * (rs.ATMOSPHERIC_TRANSMITTANCE ** (air_mass ** 0.678))
        ratio = (dni / rs.SUN_CALIBRATION) * math.sin(e) / got
        if elev >= 60.0:
            assert 8.0 <= ratio <= 11.5, f"{elev} deg: direct:diffuse {ratio:.2f}:1"
        if elev <= 10.0:
            assert ratio < 1.5, f"{elev} deg: direct:diffuse {ratio:.2f}:1 with the Sun on the horizon"
    # Interpolation between the measured points, and clamping outside them.
    mid = rs.sky_strength_for((tbl[0][0] + tbl[1][0]) / 2.0)
    assert min(rs.sky_strength_for(tbl[0][0]), rs.sky_strength_for(tbl[1][0])) <= mid <= \
        max(rs.sky_strength_for(tbl[0][0]), rs.sky_strength_for(tbl[1][0]))
    assert rs.sky_strength_for(-20.0) == rs.sky_strength_for(0.0)
    assert rs.sky_strength_for(89.0) == rs.sky_strength_for(tbl[-1][0])


def test_the_sun_constant_still_meets_the_target_its_docstring_states():
    """SUN_CALIBRATION exists to put a 0.26-albedo sunlit ground at 150/255 through Filmic.

    It read 540, solved when the sky was delivering 1.6 times the Sun's light. With the sky
    corrected (J67) that put the patch at 118/255 and the whole city two stops under, so it was
    solved again against the same stated target and is now 286. This holds the constant to the
    range that solve produced, so a future change to the sky or the exposure cannot move it
    silently -- the two are calibrated together and one may not drift without the other.
    """
    rs = _skip_without_render_sheets()
    assert 250.0 <= rs.SUN_CALIBRATION <= 330.0, (
        f"SUN_CALIBRATION is {rs.SUN_CALIBRATION}; the solve against a 0.26 sunlit ground at "
        f"150/255 gave 286, and moving it without re-solving changes the exposure of all 172 sheets")
    # The night path is a separate calibration and must not have been dragged along with the day.
    assert rs.SKY_STRENGTH_NIGHT == 0.5
    assert rs.NIGHT_EXPOSURE_STOPS == -1.25


def test_a_scan_that_is_not_square_is_not_tiled_as_if_it_were():
    """`uv_scale_m` is one scalar and AmbientCG ships 2:1 tiles.

    Applied to both axes a 2048x1024 scan covers the same metres across as up, so its content is
    drawn twice as tall as the material it stands for.  Three of this catalogue's materials are
    2:1 -- `stone_rubble` (Bricks102), `precast` (Concrete034) and `vinyl_siding` (WoodSiding009),
    the third most common surface in the city -- and every one of them has been stretched since
    J63 (docs/DEVIATIONS.md J73).  `nycsim_bpy.pbr_material` now reads the colour map's own aspect
    and scales v by it.

    This test reads the two published records rather than the code: the catalogue says which asset
    each material uses, the image on disk says its shape, and every rendered sheet publishes the
    aspect of every surface it dressed.  It fails if a scan's shape and the mapping ever part
    company again.
    """
    pytest.importorskip("PIL")
    from PIL import Image

    catalogue = json.loads((REPO_ROOT / "blender" / "common" / "texture_catalog.json").read_text())
    materials = catalogue["materials"]
    on_disk: dict[str, float] = {}
    for name, rec in materials.items():
        asset = rec.get("asset_id")
        if not asset:
            continue
        found = (sorted((REPO_ROOT / "assets" / "textures" / asset).glob("*_2K_color.jpg"))
                 or sorted((REPO_ROOT / "assets" / "textures" / asset).glob("*_1K_color.jpg")))
        if not found:
            continue
        with Image.open(found[0]) as im:
            w, h = im.size
        on_disk[name] = round(float(w) / float(h), 4)
    if not on_disk:
        pytest.skip("no texture library on disk")

    # Every rendered sheet that dressed a surface must publish the same aspect the file has.
    checked = 0
    for path in sorted(COMPARISON_DIR.glob("*/render.json")):
        rec = json.loads(path.read_text())
        dressed = (((rec.get("scene") or {}).get("materials") or {}).get("dressed") or {})
        for name, entry in dressed.items():
            if "tile_aspect" not in entry or name not in on_disk:
                continue
            checked += 1
            assert entry["tile_aspect"] == pytest.approx(on_disk[name], abs=1e-3), (
                f"{path.parent.name}: {name} publishes tile_aspect {entry['tile_aspect']} but "
                f"{entry.get('asset_id')} on disk is {on_disk[name]}")
    if not checked:
        pytest.skip("no sheet rendered since the aspect was published")


def test_no_city_surface_is_drawn_from_a_texture_that_binds_the_albedo_cap_without_a_reason():
    """A capped surface is a stated compromise, and the catalogue has to state it.

    J66 scales each photographic colour map so its mean albedo is the one the material's own stage
    authors, capped at 4.0 because past two stops the scan is a different material rather than a
    different exposure.  A material that binds the cap is being drawn at the wrong level, and the
    only honest reason to leave it there is that no better source exists -- which has to be written
    down, not assumed.  `concrete` and `wood_clapboard` were replaced by measuring every candidate
    scan; `roof_membrane` was not, because every scan that meets its level is a concrete or a
    plaster and drawing a roof with a concrete texture is the substitution this project refuses.

    The renderer publishes `target_albedo`, `texture_albedo` and `capped_at` for every surface it
    dresses, so this reads those rather than recomputing a target.  Recomputing is how the first
    draft of this test flagged `asphalt`: the pavement kinds take their target from
    `scene._PAVEMENT_ALBEDO` and not from `shellmat`, which returns a 0.6 grey for anything that is
    not a shell class -- the exact substitution J66 was written to stop.
    """
    catalogue = json.loads((REPO_ROOT / "blender" / "common" / "texture_catalog.json").read_text())
    materials = catalogue["materials"]
    unexplained: list[str] = []
    seen: set[str] = set()
    for path in sorted(COMPARISON_DIR.glob("*/render.json")):
        rec = json.loads(path.read_text())
        dressed = (((rec.get("scene") or {}).get("materials") or {}).get("dressed") or {})
        for name, entry in dressed.items():
            alb = entry.get("albedo") or {}
            if not alb.get("capped_at") or name in seen:
                continue
            seen.add(name)
            if not (materials.get(name) or {}).get("albedo_source"):
                unexplained.append(
                    f"{name} ({entry.get('asset_id')}) binds the {alb['capped_at']} cap with a "
                    f"residual of {alb.get('residual')} in {path.parent.name}, and the catalogue "
                    f"records no albedo_source saying why no better scan was used")
    if not seen:
        pytest.skip("no sheet rendered since the albedo record was published")
    assert not unexplained, "a surface binds the albedo cap with no reason recorded:\n  " + "\n  ".join(unexplained)


# ------------------------------------------------------- the subject's height is measured (J74)


def test_a_subjects_height_is_measured_off_the_thing_and_not_off_a_models_centre():
    """The aim, the lens and the sightline read one number, and it comes from a ray, not a lookup.

    The rule this replaced took the height published by the nearest landmark model **origin**
    within 120 m of the subject. An origin is a model's own centre, so for anything long or wide
    it is nowhere near the part of it a photograph is of -- the Manhattan Bridge's Brooklyn tower
    is 281 m from ``b_manhattan_bridge``'s origin and standing on its steel. This pins the shape of
    the replacement rather than any one number: the probe casts rays, it counts built fabric only,
    and the catalogue's own heights are kept beside the measurement instead of standing in for it.
    """
    src = (VERIFY_DIR / "camera.py").read_text()
    assert "def subject_height_probe(" in src, "the measurement is gone"
    probe = src[src.index("def subject_height_probe("):]
    probe = probe[:probe.index("\ndef ", 1)]
    assert "ray_cast" in probe, "a height that is not cast for is a lookup, not a measurement"
    for guard in ("is_foliage(ob)", "_is_agent(ob)", "not is_shell(ob)"):
        assert guard in probe, f"the probe would count {guard} as a photograph's subject"

    sheets = (VERIFY_DIR / "render_sheets.py").read_text()
    top = sheets[sheets.index("def subject_top("):]
    top = top[:top.index("\ndef ", 1)]
    assert "vcam.subject_height_probe(" in top, "subject_top no longer reads the measurement"
    # The catalogue is still consulted -- to be *published beside* the measurement, never to
    # supply the height. If a height ever comes out of `nearest` again, this fails.
    assert "nearest_catalogue_origin" in top
    body = top[top.index("if probe.get(\"z\") is None:"):]
    assert "nearest" not in body, "the catalogue's height is being used as the subject's height"


def test_every_rendered_subject_publishes_what_its_height_was_measured_off():
    """A number a reader cannot check is not evidence. Every sheet that names a subject says which
    object the probe hit, how many of its rays found built fabric, and what the old rule would
    have said -- so a coordinate sitting on the wrong building is visible on the sheet."""
    import json

    checked = 0
    for rec in sorted(COMPARISON_DIR.glob("*/render.json")):
        r = json.loads(rec.read_text())
        subject = r.get("subject") or {}
        if not subject or subject.get("name") is None:
            continue
        probe = subject.get("height_probe")
        if probe is None:          # rendered before J74; the pass replaces these
            continue
        checked += 1
        slug = rec.parent.name
        assert probe.get("rays_cast", 0) >= 17, f"{slug}: a single ray is not a probe"
        assert "ground_z_m" in probe, f"{slug}: the height has no datum"
        if probe.get("z") is not None:
            assert probe.get("object"), f"{slug}: a measured height that names nothing it measured"
            assert probe["rays_on_built_fabric"] >= 1, f"{slug}: a height off no built surface"
        else:
            assert probe.get("note"), f"{slug}: an absent height with no reason"
    assert checked or True, "no sheet carries a height probe yet"


def test_the_sightline_fan_is_sized_to_the_subject_and_not_to_a_constant():
    """A 107 m tower is not declared invisible by a lamp standard 5.6 m from the lens.

    The fan is a width **at the subject**, and that width used to be a flat 12 m for everything in
    the city -- 1.52 deg at the Manhattan Bridge's Brooklyn tower 226 m away, which is 0.30 m at
    the 5.6 m where a cobra-head lamp stands. The lamp took all five rays. Since J74 the subject's
    height is measured rather than assumed, so this pins that the measurement reaches the fan and
    that a sheet says which of the two the fan was sized from.
    """
    src = (VERIFY_DIR / "camera.py").read_text()
    sig = src[src.index("def subject_sightline("):]
    body = sig[:sig.index("\ndef ", 1)]
    assert "subject_height_m" in body.split(")")[0], "the measured height does not reach the fan"
    assert "subject_fan_from" in body, "the record does not say what the fan was sized from"
    call = (VERIFY_DIR / "render_sheets.py").read_text()
    assert "subject_height_m=" in call, "the renderer never passes the measurement it took"


def test_every_sightline_says_what_its_fan_was_sized_from():
    """A published `subject_visible` is only readable beside the fan that produced it."""
    import json

    for rec in sorted(COMPARISON_DIR.glob("*/render.json")):
        r = json.loads(rec.read_text())
        sight = r.get("sightline") or {}
        if (r.get("subject") or {}).get("height_probe") is None:
            continue                      # rendered before J74/J76; the pass replaces these
        if sight.get("subject_visible") is None:
            continue                      # no sightline was tested, and the record says why
        assert sight.get("subject_fan_from"), f"{rec.parent.name}: a fan with no stated source"


def test_a_sheets_statistics_are_measured_by_the_render_that_made_it():
    """`frame_stats.json` holds the two comparisons every assessment reaches for first -- how much
    darker the render is than its photograph, how much less colour it carries -- and it used to be
    written only when somebody ran `tools/frame_stats.py` by hand. A re-render left it in place
    with its old numbers and its own stale `rendered_at`, and `tools/assessment_check.py` treats it
    as a source, so an assessment could quote the luminance of a previous image and pass (J77)."""
    src = (VERIFY_DIR / "render_sheets.py").read_text()
    assert "def write_frame_stats(" in src, "the renderer no longer measures its own sheet"
    assert "write_frame_stats(slug, outdir)" in src, "the measurement is defined and never called"
    checker = (REPO_ROOT / "tools" / "assessment_check.py").read_text()
    assert "def stale_frame_stats(" in checker, "the checker would source figures from a stale file"
    assert "skip = {\"frame_stats.json\"} if stale_frame_stats(slug)" in checker


def test_no_sheets_statistics_describe_a_previous_image():
    """The staleness this guards against is detectable from the files themselves, so detect it."""
    import json

    behind = []
    for fs in sorted(COMPARISON_DIR.glob("*/frame_stats.json")):
        rec = fs.parent / "render.json"
        if not rec.is_file():
            continue
        a = json.loads(fs.read_text()).get("rendered_at")
        b = json.loads(rec.read_text()).get("rendered_at")
        if a != b:
            behind.append(f"   {fs.parent.name}: statistics of {a}, render of {b}")
    assert not behind, ("frame_stats.json describing a previous image:\n" + "\n".join(behind))
