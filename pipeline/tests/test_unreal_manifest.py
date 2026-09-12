"""Tests for nycsim_pipeline.unreal.manifest: synthetic blender_out + processed tree -> unreal_manifest.json."""
from __future__ import annotations

import json
import tempfile
import struct
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from PIL import Image
from shapely.geometry import LineString, Polygon, box

from nycsim_pipeline.unreal import manifest as um
from nycsim_pipeline.unreal.glb import GlbError, glb_summary, read_glb_json


def _write_glb(path: Path, doc: dict) -> None:
    body = json.dumps(doc).encode()
    body += b" " * ((4 - len(body) % 4) % 4)
    total = 12 + 8 + len(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(body), 0x4E4F534A))
        f.write(body)


def _glb_doc(names: list[str], extras: dict | None = None, tris: int = 12) -> dict:
    return {
        "asset": {"version": "2.0", "extras": {"nycsim": json.dumps(extras or {})}},
        "nodes": [{"name": n, "mesh": i} for i, n in enumerate(names)],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]} for _ in names],
        "accessors": [{"count": tris * 3}, {"count": tris * 3}],
        "materials": [{"name": "brick"}],
    }


@pytest.fixture()
def world(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path
    processed = repo / "data" / "processed"
    blender_out = repo / "blender_out"
    tile = "t_-3_7"
    x0, y0 = -3000.0, 7000.0
    td = processed / "tiles" / tile
    td.mkdir(parents=True)
    (processed / "crs.json").write_text(json.dumps({"schema_version": 1, "name": "NYC_TM"}))
    # terrain
    arr = (np.linspace(0, 65535, 501 * 501).reshape(501, 501)).astype(np.uint16)
    Image.fromarray(arr, mode="I;16").save(td / "terrain.png")
    (td / "terrain.json").write_text(json.dumps({"schema_version": 1, "tile": tile, "z_min_m": -2.1, "z_scale_m": 0.0025, "samples": 501, "spacing_m": 2.0, "sources": ["3dep_19"], "water_level_m": 0.0}))
    # placements: 3 records, kit ids 7 and 9
    rec = struct.Struct("<IqfffffII")
    with open(td / "kit_placements.bin", "wb") as f:
        for kit_id, b in ((7, 1000001), (9, 1000002), (7, 1000003)):
            f.write(rec.pack(kit_id, b, 10.0, 20.0, 3.0, 90.0, 1.0, 42, 1))
    # props
    pq.write_table(pa.table({"prop_id": pa.array([1, 2], pa.int64()), "kind": pa.array([3, 40], pa.int16()), "x": [x0 + 5.0, x0 + 6.0], "y": [y0 + 5.0, y0 + 6.0], "z": [1.0, 1.5],
                             "heading": [0.0, 90.0], "variant": pa.array([0, 1], pa.int16()), "text": ["", "Acme Deli"], "source": pa.array([0, 1], pa.int8()),
                             "dataset_id": ["hydrants", "rule:bollard"], "species": ["", ""], "dbh_cm": [0.0, 0.0], "height_m": [0.0, 0.0]}), td / "props.parquet")
    # signs (borough-wide table, binned into the tile)
    (processed / "roads").mkdir()
    pq.write_table(pa.table({"sign_id": pa.array([11, 12], pa.int64()), "node_id": pa.array([1, 1], pa.int64()), "segment_id": pa.array([5, 5], pa.int64()),
                             "x": [x0 + 100.0, 50000.0], "y": [y0 + 100.0, 50000.0], "z": [2.4, 2.4], "facing_heading": [90.0, 0.0], "mutcd_code": ["R7-1", "R1-1"],
                             "text": ["NO PARKING ANYTIME", "STOP"], "arrow": pa.array([0, 0], pa.int8()), "sign_w_m": [0.3, 0.75], "sign_h_m": [0.45, 0.75],
                             "support": pa.array([0, 0], pa.int8()), "source": pa.array([0, 0], pa.int8())}), processed / "roads" / "signs.parquet")
    # water: east half of the tile is river
    (processed / "water").mkdir()
    river = box(x0 + 500.0, y0 - 100.0, x0 + 1200.0, y0 + 1100.0)
    pq.write_table(pa.table({"water_id": pa.array([1], pa.int64()), "kind": ["river"], "name": ["East River"], "tidal": [True], "geometry": [river.wkb]}), processed / "water" / "hydrography.parquet")
    pq.write_table(pa.table({"kind": ["bulkhead"], "geometry": [LineString([(x0 + 500.0, y0), (x0 + 500.0, y0 + 1000.0)]).wkb]}), processed / "water" / "shoreline.parquet")
    pq.write_table(pa.table({"kind": ["pier"], "geometry": [Polygon([(x0 + 500, y0 + 400), (x0 + 560, y0 + 400), (x0 + 560, y0 + 410), (x0 + 500, y0 + 410)]).wkb]}), processed / "water" / "structures.parquet")
    (processed / "live").mkdir()
    (processed / "live" / "tides.json").write_text(json.dumps({"station": "NYH1927", "current_speed_mps": 1.2, "current_dir_deg": 35.0, "water_level_m": 0.3, "predicted_at": "2026-09-05T18:00:00Z"}))
    # A runtime container with one section, written by the REAL writer.
    #
    # This fixture used to hand-assemble the bytes with struct.pack("<IIQ", ...) - a 20-byte header
    # with no padding - and the manifest's reader unpacked exactly the same 20 bytes, so the two
    # agreed with each other and with nothing else. The actual format (DATA_CONTRACTS 15,
    # runtime/nycb.py, which asserts it) has 4 bytes of padding before the 8-aligned index_offset and
    # is 24 bytes, so every real container in data/processed/runtime failed to parse and all seven
    # were dropped from the manifest with a warning nobody read. Building the fixture through the
    # writer means the format has one definition and this test cannot pass against a private copy.
    (processed / "runtime").mkdir()
    from nycsim_pipeline.runtime.nycb import NycbWriter

    tiles_dtype = np.dtype([("tx", "<i4"), ("ty", "<i4"), ("min_z_m", "<f4"), ("max_z_m", "<f4"),
                            ("n_buildings", "<u4"), ("n_road_segments", "<u4"),
                            ("borough", "u1"), ("flags", "u1")], align=True)
    rows = np.zeros(1, dtype=tiles_dtype)
    rows[0] = (-3, 7, -2.1, 61.0, 120, 800, 7, 1)
    writer = NycbWriter()
    writer.add_array("tiles", rows)
    writer.write(processed / "runtime" / "tiles.nycb")
    # blender outputs
    _write_glb(blender_out / "tiles" / tile / "tile_buildings.glb", _glb_doc(["shell_brick", "shell_glass"], {"tile": tile, "category": "shells"}, tris=5000))
    _write_glb(blender_out / "kit" / "window_dh_1over1.glb", _glb_doc(["window_dh_1over1", "window_dh_1over1_LOD1"], {"kit_id": 7, "category": "windows"}))
    _write_glb(blender_out / "kit" / "cornice_metal_a.glb", _glb_doc(["cornice_metal_a"], {"kit_id": 9, "category": "cornices"}))
    _write_glb(blender_out / "landmarks" / "empire_state.glb", _glb_doc(["esb", "esb_LOD1"], {"id": "empire_state", "bins": [1015862]}))
    _write_glb(blender_out / "props" / "trees" / "platanus_large.glb", _glb_doc(["tree", "tree_LOD1"], {"species": "Platanus x acerifolia"}))
    _write_glb(blender_out / "props" / "hydrant.glb", _glb_doc(["hydrant"], {"kind": 3, "category": "street"}))
    _write_glb(blender_out / "vehicles" / "fusion_hybrid_2019.glb", _glb_doc(["body"], {"id": "fusion_hybrid_2019"}))
    _write_glb(blender_out / "character" / "player.glb", {**_glb_doc(["root"], {"id": "player"}), "skins": [{}], "animations": [{}, {}]})
    (blender_out / "kit" / "catalog").mkdir()
    (blender_out / "kit" / "catalog" / "7.json").write_text(json.dumps({"id": 7, "kit_id": 7, "glb": "kit/window_dh_1over1.glb", "category": "windows", "bounds": {"min": [0, 0, 0], "max": [1, 0.2, 1.6]}}))
    (blender_out / "kit" / "catalog" / "9.json").write_text(json.dumps({"id": 9, "kit_id": 9, "glb": "kit/cornice_metal_a.glb", "category": "cornices"}))
    # junk glb that must be reported, not crash
    (blender_out / "kit" / "broken.glb").write_bytes(b"not a glb at all")
    return repo, processed, blender_out


def test_glb_reader(tmp_path: Path) -> None:
    p = tmp_path / "a.glb"
    _write_glb(p, _glb_doc(["m", "m_LOD1"], {"kit_id": 3}, tris=10))
    doc = read_glb_json(p)
    assert doc["asset"]["version"] == "2.0"
    s = glb_summary(p)
    assert s["has_lod1"] and s["triangles"] == 20 and s["extras"]["kit_id"] == 3
    (tmp_path / "bad.glb").write_bytes(b"\0" * 30)
    with pytest.raises(GlbError):
        read_glb_json(tmp_path / "bad.glb")


def test_manifest_end_to_end(world: tuple[Path, Path, Path]) -> None:
    repo, processed, blender_out = world
    out, doc = um.generate(processed, blender_out, repo_root=repo, record=False)
    assert out.exists()
    reloaded = json.loads(out.read_text())
    assert reloaded["schema"] == "unreal_manifest/1"
    ids = {e["id"]: e for e in reloaded["entries"]}
    # runtime + crs
    assert ids["crs"]["dst"] == "/Game/NYCSim/Runtime/crs.json"
    assert ids["runtime:tiles.nycb"]["nycb"]["sections"][0]["name"] == "tiles"
    assert ids["runtime:tiles.nycb"]["nycb"]["sections"][0]["element_count"] == 1
    # glbs
    assert ids["glb:kit/window_dh_1over1.glb"]["dst"] == "/Game/NYCSim/Kit/windows/SM_window_dh_1over1"
    assert ids["glb:kit/window_dh_1over1.glb"]["glb"]["has_lod1"] is True
    assert ids["glb:kit/cornice_metal_a.glb"]["category"] == "cornices"
    assert ids["glb:tiles/t_-3_7/tile_buildings.glb"]["dst"] == "/Game/NYCSim/Tiles/t_m3_7/SM_Shells"
    assert ids["glb:tiles/t_-3_7/tile_buildings.glb"]["import_settings"] == "shell_nanite"
    assert ids["glb:landmarks/empire_state.glb"]["import_settings"] == "landmark_nanite"
    assert ids["glb:props/trees/platanus_large.glb"]["import_settings"] == "tree_lod"
    assert ids["glb:props/hydrant.glb"]["dst"] == "/Game/NYCSim/Props/street/SM_hydrant"
    assert ids["glb:vehicles/fusion_hybrid_2019.glb"]["import_settings"] == "vehicle_skeletal"
    assert ids["glb:character/player.glb"]["glb"]["animations"] == 2
    assert "glb:kit/broken.glb" not in ids
    assert any("broken.glb" in w for w in reloaded["warnings"])
    # tile record
    t = reloaded["tiles"]["t_-3_7"]
    assert t["tx"] == -3 and t["ty"] == 7 and t["x0"] == -3000.0
    assert t["kit_placements"]["count"] == 3 and t["kit_placements"]["kit_ids"] == [7, 9]
    assert t["props"]["count"] == 2
    props = json.loads((repo / t["props"]["path"]).read_text())
    assert props["origin_local"] and props["rows"][0]["x"] == 5.0 and props["rows"][1]["text"] == "Acme Deli"
    assert t["signs"]["count"] == 1  # the second sign is in another tile that has no directory
    signs = json.loads((repo / t["signs"]["path"]).read_text())
    assert signs["signs"][0]["text"] == "NO PARKING ANYTIME" and signs["signs"][0]["x"] == 100.0
    assert ids["terrain:t_-3_7"]["terrain"]["z_scale_m"] == 0.0025
    # water
    water = json.loads((processed / "unreal_water.json").read_text())
    assert water["flow"]["current_dir_deg"] == 35.0 and water["water_level_m"] == 0.3
    assert water["bodies"][0]["name"] == "East River" and water["bodies"][0]["tiles"] == ["t_-3_7"]
    wt = water["tiles"]["t_-3_7"]
    assert abs(wt["water_fraction"] - 0.5) < 0.01
    assert abs(wt["mean_mask"] - 0.5) < 0.02
    assert wt["shoreline_m"] == 1000.0 and wt["structures"] == 1 and wt["tidal"] is True
    mask = np.asarray(Image.open(repo / wt["mask_png"]))
    assert mask.shape == (501, 501) and mask.dtype == np.uint8
    assert mask[250, 10] == 0 and mask[250, 490] == 255  # west land, east water
    assert ids["water_mask:t_-3_7"]["import_settings"] == "texture_mask"
    # order: crs first, tiles last
    order = reloaded["import_order"]
    assert order[0] == "crs"
    assert order.index("glb:kit/window_dh_1over1.glb") < order.index("terrain:t_-3_7") < order.index("glb:tiles/t_-3_7/tile_buildings.glb")
    assert reloaded["counts"]["entries"] == len(reloaded["entries"]) == len(set(order))
    for e in reloaded["entries"]:
        assert e["import_settings"] in reloaded["import_settings"]
        assert (repo / e["src"]).exists()
        assert e["sha256"] and len(e["sha256"]) == 64


def test_safe_asset_name() -> None:
    assert um.safe_asset_name("t_-3_7") == "t_m3_7"
    assert um.safe_asset_name("9lives") == "_9lives"
    assert um.safe_asset_name("a b.c") == "a_b_c"


def test_empty_world(tmp_path: Path) -> None:
    processed = tmp_path / "p"
    processed.mkdir()
    out, doc = um.generate(processed, tmp_path / "missing_blender_out", repo_root=tmp_path, record=False)
    assert doc["counts"]["entries"] == 1  # unreal_water.json with no bodies is still produced
    assert any("crs.json missing" in w for w in doc["warnings"])
    assert json.loads((processed / "unreal_water.json").read_text())["bodies"] == []


def test_a_manifest_never_carries_a_source_from_outside_the_root_it_was_given() -> None:
    """`generate(repo_root=...)` must describe that tree and no other.

    It did not.  `city_surfaces.build` reached its two Blender modules with `sys.path.insert` and a
    bare `import`, which resolves by *name* out of `sys.modules`: once any root had been loaded,
    every later call got that one back and the argument was ignored.  A manifest generated over an
    empty temporary tree came out with ten entries, nine of them absolute paths into the real
    repository's `assets/textures`.  It surfaced as a test that passed alone and failed after the
    Blender scene tests -- the manifest's content depended on what else had run in the process,
    which for the single list of what the import needs is not a small thing.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        processed = root / "processed"
        processed.mkdir()
        _, doc = um.generate(processed, root / "no_blender_out", repo_root=root, record=False)
        outside = [str(e.get("src")) for e in doc.get("entries", [])
                   if e.get("src") and not str(Path(str(e["src"]))).startswith(("processed", "no_blender_out"))
                   and not str(Path(str(e["src"])).resolve()).startswith(str(root.resolve()))]
        assert not outside, ("the manifest carries sources from outside the root it was given:\n   "
                             + "\n   ".join(outside[:10]))


def test_a_glb_that_names_its_images_carries_them_as_sidecars(world) -> None:
    """A ``.glb`` stopped being self-contained when the duplicate images were moved out of the
    binary chunks. The manifest is the only list of what the import needs, so it has to name the
    files too, or the package ships meshes with nothing on them and says nothing about it."""
    repo, processed, blender_out = world
    doc = _glb_doc(["Body"])
    doc["images"] = [{"name": "Leather026_2K_normal", "uri": "textures/Leather026_2K_normal-abc123def456.jpg"},
                     {"name": "gone", "uri": "textures/not_written.png"}]
    _write_glb(blender_out / "props" / "bench_wood.glb", doc)
    tex = blender_out / "props" / "textures"
    tex.mkdir(parents=True, exist_ok=True)
    (tex / "Leather026_2K_normal-abc123def456.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg")

    _out, doc_out = um.generate(processed, blender_out, repo_root=repo, record=False)
    entry = next(e for e in doc_out["entries"] if e["src"].endswith("props/bench_wood.glb"))
    assert entry["sidecars"] == ["blender_out/props/textures/Leather026_2K_normal-abc123def456.jpg"]
    assert any("not_written.png" in w for w in doc_out["warnings"]), \
        "an image the glb names and disk does not have must be a warning, not a silence"
    counts = doc_out["counts"]
    assert counts["sidecar_references"] >= 1 and counts["sidecar_files"] >= 1


def test_an_image_uri_may_not_climb_out_of_its_own_directory(world) -> None:
    """The URIs this project writes descend into ``textures/``; a ``../`` path would resolve
    against whatever the packager happened to have around it, so it is refused rather than
    followed."""
    repo, processed, blender_out = world
    doc = _glb_doc(["Body"])
    doc["images"] = [{"uri": "../../etc/passwd"}]
    _write_glb(blender_out / "props" / "bench_stone.glb", doc)
    _out, doc_out = um.generate(processed, blender_out, repo_root=repo, record=False)
    entry = next(e for e in doc_out["entries"] if e["src"].endswith("props/bench_stone.glb"))
    assert "sidecars" not in entry
    assert any("passwd" in w for w in doc_out["warnings"])


# --------------------------------------------------------- the city's own surfaces (J63, engine half)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _city_surfaces_module():
    from nycsim_pipeline.unreal import city_surfaces
    return city_surfaces


def test_the_engine_is_given_a_surface_for_every_name_the_tiles_carry():
    """The tiles name their materials and carry no images, and the consumer resolves the name.

    The comparison renderer has held up its half since J63. Unreal had nothing to resolve a name
    *to*: no material instance named a surface and the manifest carried no texture entry at all.
    This pins that every name a tile carries either resolves to a surface or is refused with a
    reason -- never silently left out, because an engine that guessed a pier deck's cladding would
    be inventing a survey.
    """
    cs = _city_surfaces_module()
    for name in cs.PAVEMENT_SURFACE:
        assert name not in cs.UNRESOLVED_REASON, f"{name} is both bound and refused"
    for name, why in cs.UNRESOLVED_REASON.items():
        assert len(why) > 20, f"{name}'s refusal is not a reason"
    # The two markings must stay refused: giving them the asphalt under them erases every lane
    # line and stop bar in the city (J52).
    for paint in ("pave_marking_white_asphalt", "pave_marking_yellow_asphalt"):
        assert paint in cs.UNRESOLVED_REASON and "paint" in cs.UNRESOLVED_REASON[paint]
        assert paint not in cs.PAVEMENT_SURFACE


def test_a_city_surface_instance_is_keyed_on_its_surface_class_as_well_as_its_surface():
    """Five pavement names resolve to `concrete_sidewalk` and they do not share a surface class:
    a curb ramp and a sidewalk are class 9, a median, a plaza and a curb are class 2. One instance
    per surface carries one `phys_material`, so it would have given one of those groups the other's
    tyre friction -- every curb ramp in the city gripping like a median."""
    cs = _city_surfaces_module()
    by_surface = {}
    for name, surface in cs.PAVEMENT_SURFACE.items():
        by_surface.setdefault(surface, set()).add(name)
    assert len(by_surface["concrete_sidewalk"]) >= 4, \
        "the case this test exists for has gone; check the mapping rather than deleting the test"

    surface_class = {"pave_curb_concrete": 2, "pave_median_concrete": 2, "pave_plaza_concrete": 2,
                     "pave_curb_ramp_concrete": 9, "pave_sidewalk_concrete": 9,
                     "pave_roadbed_asphalt": 1, "pave_crosswalk_asphalt": 1,
                     "pave_parking_lot_asphalt": 1, "pave_roadbed_concrete": 2}
    names = {f"NYCSIM_red_brick": 3, **{k: 1 for k in surface_class}}

    import types
    from pathlib import Path
    real = cs.tile_material_names
    cs.tile_material_names = lambda root: dict(names)          # noqa: ARG005
    try:
        block = cs.build(Path(__file__).resolve().parents[2], Path("/nonexistent"),
                         surface_class=surface_class)
    finally:
        cs.tile_material_names = real

    insts = block["instances"]
    assert "MI_NYC_concrete_sidewalk_sc2" in insts and "MI_NYC_concrete_sidewalk_sc9" in insts, \
        f"concrete_sidewalk did not split by surface class: {sorted(insts)}"
    assert set(insts["MI_NYC_concrete_sidewalk_sc9"]["from_material_names"]) == \
        {"pave_curb_ramp_concrete", "pave_sidewalk_concrete"}
    # A shell surface has no class and keeps a plain name.
    assert insts["MI_NYC_red_brick"]["surface_class"] is None


def test_a_city_surfaces_level_is_the_one_its_own_stage_authored():
    """A scan's exposure is a photographer's choice, not a measurement, and taking it whole is what
    made every daylight street render at half its photograph's brightness (J66). The engine gets
    the same scalar the renderer publishes, capped the same way with the residual stated."""
    cs = _city_surfaces_module()
    assert cs.ALBEDO_SCALE_CAP == 4.0
    # A scan twice as dark as the authored level is corrected by 2.0 and says so.
    got = cs.albedo_correction(0.10, (0.20, 0.20, 0.20))
    assert got["scale"] == pytest.approx(2.0, abs=1e-3) and "capped_at" not in got
    # A scan fourteen times too dark is the wrong material, not the wrong exposure: capped, and the
    # residual is published rather than hidden.
    got = cs.albedo_correction(0.02, (0.28, 0.28, 0.28))
    assert got["scale"] == cs.ALBEDO_SCALE_CAP
    assert got["residual"] == pytest.approx(0.28 / (0.02 * 4.0), abs=1e-3)
    assert "wrong material" in got["note"]
    # Already right: no correction, and no pretence of one.
    assert cs.albedo_correction(0.20, (0.20, 0.20, 0.20))["scale"] == 1.0


def test_the_master_material_still_draws_an_untextured_asset_exactly_as_before():
    """Hundreds of props, vehicles and kit pieces already use M_NYC_Master. Every city-surface
    parameter added to it defaults to the value that reproduces the old behaviour -- a white colour
    map, no texture strength, a flat normal -- so an instance that sets none of them is unchanged."""
    src = (REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "import_assets.py").read_text()
    body = src[src.index("def build_master_material("):]
    body = body[:body.index("\ndef ", 1)]
    for default in ('parameter_name="ColorTextureStrength", default_value=0.0',
                    'parameter_name="RoughnessFromTexture", default_value=0.0',
                    'parameter_name="AlbedoScale", default_value=1.0',
                    'parameter_name="SurfaceSizeM", default_value=1.0',
                    'parameter_name="TileAspect", default_value=1.0'):
        assert default in body, f"missing a neutral default: {default}"
    assert "ENGINE_WHITE_TEXTURE" in body, "the colour sampler has no white default"
    assert "MaterialProperty.MP_NORMAL" in body, "the normal map is never connected"


def test_an_unbound_slot_is_left_alone_and_counted_rather_than_guessed():
    """Markings, structures and park ground resolve to no surface. Giving them the nearest concrete
    would be inventing a survey, so the assignment pass must skip them and say how many."""
    src = (REPO_ROOT / "unreal" / "NYCSim" / "Content" / "Python" / "import_assets.py").read_text()
    body = src[src.index("def assign_city_surface_materials("):]
    body = body[:body.index("\ndef ", 1)]
    assert 'if not inst_name:' in body and 'unbound += 1' in body
    assert "material_interface" in body, "the pass never sets a slot's material"


def test_a_citibike_part_resolves_through_the_variant_its_asset_declares(tmp_path: Path) -> None:
    """A kind-7 row with ``variant`` 2 is a dock unit and must resolve to the asset tagged ``variant:2`` --
    not to whichever citibike asset sorts first by id, which is the bicycle (docs/DEVIATIONS.md J58)."""
    from nycsim_pipeline.furniture import assets as A

    processed = tmp_path / "processed"
    blender_out = tmp_path / "blender_out"
    (blender_out / "props").mkdir(parents=True)
    (processed / "furniture").mkdir(parents=True)
    (processed / "furniture" / "props_catalog.json").write_text(json.dumps({"kinds": [{"id": 7, "name": "citibike_dock"}]}))
    entries = [
        {"id": "citibike_bike", "dataset_kind": "citibike_dock", "glb": "props/citibike_bike.glb", "tags": ["citibike", "variant:3"]},
        {"id": "citibike_dock_unit", "dataset_kind": "citibike_dock", "glb": "props/citibike_dock_unit.glb", "tags": ["citibike", "variant:2"]},
        {"id": "citibike_kiosk", "dataset_kind": "citibike_dock", "glb": "props/citibike_kiosk.glb", "tags": ["citibike", "variant:1"]},
    ]
    (blender_out / "props" / "props_asset_catalog.json").write_text(json.dumps({"schema_version": 1, "count": 3, "entries": entries}))
    pa_ = A.load(processed, blender_out)
    assert pa_.variants_by_kind["citibike_dock"] == {1: "citibike_kiosk", 2: "citibike_dock_unit", 3: "citibike_bike"}
    for code, want in ((1, "citibike_kiosk"), (2, "citibike_dock_unit"), (3, "citibike_bike")):
        entry, why, scale = pa_.resolve_scaled(7, variant=code)
        assert entry["id"] == want and why == "ok" and scale == 1.0
    # a variant-0 row is never written after Stage 40; if one appears it is reported, not silently the bicycle
    entry, why, _ = pa_.resolve_scaled(7, variant=0)
    assert why == "variant_unmapped:0" and entry["id"] == "citibike_bike"
