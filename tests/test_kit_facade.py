"""Acceptance tests for the Blender facade kit (``blender_out/kit/facade/*.glb`` + ``blender_out/kit/catalog/*.json``).

Everything here is checked against the exported artefacts, not against the generator: the glb is opened with
pygltflib, its accessors are read for the real bounding box and triangle counts, and the catalog entry must agree.

Run:  python3 -m pytest tests/test_kit_facade.py -q
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys
from pathlib import Path

import pytest

pygltflib = pytest.importorskip("pygltflib")

REPO = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[1]))
KIT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO / "blender_out")) / "kit"
GLB_DIR = KIT / "facade"
CATALOG_DIR = KIT / "catalog"
TEXTURE_ROOT = REPO / "assets" / "textures"
sys.path.insert(0, str(REPO / "blender" / "common"))

MIN_PIECES = 120
# Budgets fixed by the kit brief; every other category is bounded by the per-entry budget in the catalog.
# The window cap was raised from the brief's 400 to 900 on an explicit instruction from the orchestrator after the
# first verification pass: at 400 the sashes read flat because there was no geometry left for the reveal jamb, the
# sill drip and the sealed interior box. The deviation is recorded in docs/verification/kit/REPORT.md.
BRIEF_BUDGETS = {"window": 900, "storefront": 6000, "fire_escape": 3000, "water_tower": 4000}
# A sash in a New York masonry opening sits 100-200 mm behind the wall face. Anything shallower reads as a decal.
MIN_GLAZING_SETBACK_M = 0.10
MAX_GLAZING_SETBACK_M = 0.25
VALID_ANCHORS = {"wall_bottom_centre", "wall_sill_centre", "wall_head_centre", "wall_platform_centre",
                 "wall_corner_bottom", "wall_corner_platform", "wall_bay_frame", "ground_bottom_centre",
                 "ground_corner_bottom"}
CENTRED_ON_X = {"wall_bottom_centre", "wall_sill_centre", "wall_head_centre", "wall_platform_centre",
                "wall_bay_frame", "ground_bottom_centre"}


def _entries() -> list[dict]:
    if not CATALOG_DIR.is_dir():
        pytest.skip(f"kit not built: {CATALOG_DIR} missing (run blender/kit/facade/build_kit.py)")
    out = [json.loads(p.read_text()) for p in sorted(CATALOG_DIR.glob("*.json"))]
    if not out:
        pytest.skip("kit catalog empty")
    return out


ENTRIES = _entries()
IDS = [e["id"] for e in ENTRIES]
_GLTF_CACHE: dict[str, object] = {}


def _gltf(pid: str):
    if pid not in _GLTF_CACHE:
        _GLTF_CACHE[pid] = pygltflib.GLTF2().load(str(GLB_DIR / f"{pid}.glb"))
    return _GLTF_CACHE[pid]


def _blob(g) -> bytes:
    return g.binary_blob()


def _accessor_minmax(g, acc_idx: int) -> tuple[list[float], list[float]]:
    a = g.accessors[acc_idx]
    if a.min and a.max:
        return list(a.min), list(a.max)
    raise AssertionError("POSITION accessor without min/max")


def _mesh_triangles(g, mesh) -> int:
    n = 0
    for prim in mesh.primitives:
        mode = 4 if prim.mode is None else prim.mode
        assert mode == 4, "kit meshes must be plain triangles"
        if prim.indices is not None:
            n += g.accessors[prim.indices].count // 3
        else:
            n += g.accessors[prim.attributes.POSITION].count // 3
    return n


def _mesh_bounds_blender(g, mesh) -> tuple[list[float], list[float]]:
    """Bounding box of a glTF mesh converted back to Blender Z-up metres (export used export_yup=True:
    glTF (x, y, z) == Blender (x, -z, y))."""
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for prim in mesh.primitives:
        mn, mx = _accessor_minmax(g, prim.attributes.POSITION)
        for a, b in ((mn, mx),):
            for i in range(3):
                lo[i] = min(lo[i], a[i], b[i])
                hi[i] = max(hi[i], a[i], b[i])
    blo = [lo[0], -hi[2], lo[1]]
    bhi = [hi[0], -lo[2], hi[1]]
    return blo, bhi


def _lod_meshes(g, pid: str):
    lod0 = [m for m in g.meshes if m.name == pid]
    lod1 = [m for m in g.meshes if m.name == f"{pid}_LOD1"]
    return (lod0[0] if lod0 else None), (lod1[0] if lod1 else None)


# --------------------------------------------------------------------------- catalog-level
def test_kit_has_enough_pieces():
    assert len(ENTRIES) >= MIN_PIECES, f"only {len(ENTRIES)} kit pieces, the brief requires >= {MIN_PIECES}"


def test_ids_unique_and_match_filenames():
    assert len(set(IDS)) == len(IDS)
    for e in ENTRIES:
        assert e["glb"] == f"kit/facade/{e['id']}.glb"


def test_categories_and_anchors_are_known():
    import facade_params as fp
    for e in ENTRIES:
        assert e["category"] in fp.KIT_CATEGORIES, f"{e['id']}: bad category {e['category']}"
        assert e["anchor"]["origin"] in VALID_ANCHORS, f"{e['id']}: bad anchor {e['anchor']['origin']}"
        assert e["anchor"]["into_building"] == "+Y" and e["anchor"]["up"] == "+Z" and e["anchor"]["units"] == "m"


def test_brief_coverage():
    """The kit must cover every window type, storefront bay width, gate state and interior kind in facade_params."""
    import facade_params as fp
    cats: dict[str, list[str]] = {}
    for e in ENTRIES:
        cats.setdefault(e["category"], []).append(e["id"])
    # the pipeline writes window_type as an int; the kit piece for index i is win_<WINDOW_TYPE_NAMES[i]>
    for name in fp.WINDOW_TYPE_NAMES:
        assert f"win_{name}" in IDS, f"no kit piece for window type {name}"
    assert len(cats.get("window", [])) >= len(fp.WINDOW_TYPES)
    for w in fp.STOREFRONT_BAY_WIDTHS_M:
        key = f"{w:.1f}".replace(".", "")
        assert f"storefront_bay_{key}" in IDS
        for st in fp.STOREFRONT_GATE_STATES:
            assert f"storefront_gate_{key}_{st}" in IDS
    for k in fp.STOREFRONT_INTERIOR_KINDS:
        assert f"storefront_interior_{k}" in IDS
    for need in ("fire_escape_floor_unit", "fire_escape_corner_return", "fire_escape_drop_ladder", "fire_escape_top_hook",
                 "water_tower_small", "water_tower_large", "billboard_rooftop", "sidewalk_shed_module",
                 "entry_stoop_tenement_4", "entry_stoop_brownstone_10", "cornice_pressed_metal_a",
                 "cornice_pressed_metal_b", "cornice_pressed_metal_c", "cornice_brick_corbel", "cornice_stone"):
        assert need in IDS, f"kit is missing required piece {need}"


# --------------------------------------------------------------------------- per-piece
@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_glb_exists_and_loads(entry):
    p = GLB_DIR / f"{entry['id']}.glb"
    assert p.is_file(), f"{entry['id']}: {p} missing"
    assert p.stat().st_size > 512
    g = _gltf(entry["id"])
    assert g.asset.version == "2.0"
    assert g.meshes, f"{entry['id']}: no meshes"


@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_lod1_present_and_within_quarter(entry):
    pid = entry["id"]
    g = _gltf(pid)
    lod0, lod1 = _lod_meshes(g, pid)
    assert lod0 is not None, f"{pid}: no mesh named {pid}"
    assert lod1 is not None, f"{pid}: no mesh named {pid}_LOD1"
    t0 = _mesh_triangles(g, lod0)
    t1 = _mesh_triangles(g, lod1)
    # a triangle mesh cannot go below 2 triangles, so the rule is lod1 <= max(2, 25 % of lod0)
    assert t1 <= max(2, math.ceil(0.25 * t0)), f"{pid}: LOD1 {t1} tris > 25 % of LOD0 {t0}"
    assert t1 >= 2
    assert t0 == entry["polycount"]["lod0_triangles"], f"{pid}: catalog LOD0 count disagrees with the glb"
    assert t1 == entry["polycount"]["lod1_triangles"], f"{pid}: catalog LOD1 count disagrees with the glb"


@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_triangle_budget(entry):
    pid = entry["id"]
    g = _gltf(pid)
    lod0, _ = _lod_meshes(g, pid)
    t0 = _mesh_triangles(g, lod0)
    budget = entry["polycount"]["budget"]
    assert t0 <= budget, f"{pid}: {t0} triangles over its {budget} budget"
    brief = BRIEF_BUDGETS.get(entry["category"])
    if brief is not None:
        assert t0 <= brief, f"{pid}: {t0} triangles over the brief budget {brief} for {entry['category']}"


@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_bounds_within_five_percent_of_nominal(entry):
    pid = entry["id"]
    g = _gltf(pid)
    lod0, _ = _lod_meshes(g, pid)
    lo, hi = _mesh_bounds_blender(g, lod0)
    size = [hi[i] - lo[i] for i in range(3)]
    nominal = entry["nominal_size_m"]
    for i, (s, n) in enumerate(zip(size, nominal)):
        assert n > 0, f"{pid}: nominal axis {i} is zero"
        assert abs(s - n) / n <= 0.05, f"{pid}: axis {i} measured {s:.3f} m vs nominal {n:.3f} m (> 5 %)"
    for i in range(3):
        assert abs(lo[i] - entry["bounds"]["min"][i]) < 0.02, f"{pid}: glb min axis {i} disagrees with the catalog"
        assert abs(hi[i] - entry["bounds"]["max"][i]) < 0.02, f"{pid}: glb max axis {i} disagrees with the catalog"


@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_anchor_origin_is_on_the_piece(entry):
    """The origin must sit on the datum its anchor names (see kitlib's module docstring)."""
    lo, hi = entry["bounds"]["min"], entry["bounds"]["max"]
    origin = entry["anchor"]["origin"]
    assert lo[0] <= 0.02 and hi[0] >= -0.02, f"{entry['id']}: origin is outside the piece in x"
    if origin in ("ground_bottom_centre", "ground_corner_bottom"):
        assert abs(lo[2]) <= 0.06, f"{entry['id']}: {origin} but the piece starts at z = {lo[2]:.3f}"
    if origin == "wall_bottom_centre":
        # sills, aprons and stoop nosings may hang below the opening datum, but never by more than half a metre
        assert -0.50 <= lo[2] <= 0.02, f"{entry['id']}: {origin} but the piece starts at z = {lo[2]:.3f}"
        assert hi[2] > 0.05, f"{entry['id']}: {origin} but nothing is above the datum"
    if origin.startswith("wall") and origin != "wall_bay_frame":
        assert hi[1] > 0.0 or lo[1] < 0.0, f"{entry['id']}: wall piece has no depth"
    if origin in CENTRED_ON_X:
        assert abs(lo[0] + hi[0]) <= 0.25 * max(hi[0] - lo[0], 1e-6) + 0.05, f"{entry['id']}: piece not centred on x"


@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_materials_reference_embedded_textures(entry):
    """Every glTF image must be embedded in the binary chunk (no external URIs), and any material that uses a
    catalogued texture set must carry a base-colour texture."""
    pid = entry["id"]
    g = _gltf(pid)
    assert g.materials, f"{pid}: no materials"
    for img in g.images:
        assert img.uri is None, f"{pid}: image {img.name} is external ({img.uri})"
        assert img.bufferView is not None, f"{pid}: image {img.name} has no bufferView"
        assert img.mimeType in ("image/jpeg", "image/png"), f"{pid}: image {img.name} mimeType {img.mimeType}"
    if entry["texture_assets"]:
        assert g.images, f"{pid}: uses texture assets {entry['texture_assets']} but embeds no image"
        assert g.textures and g.samplers is not None
        textured = [m for m in g.materials
                    if m.pbrMetallicRoughness is not None and m.pbrMetallicRoughness.baseColorTexture is not None]
        assert textured, f"{pid}: no material has a base-colour texture although {entry['texture_assets']} are listed"


@pytest.mark.parametrize("entry", ENTRIES, ids=IDS)
def test_texture_licences_present(entry):
    """Every texture set the piece names must have a CC0 licence record on disk."""
    for asset_id in entry["texture_assets"]:
        lic = TEXTURE_ROOT / asset_id / "LICENSE.json"
        assert lic.is_file(), f"{entry['id']}: no LICENSE.json for texture asset {asset_id}"
        rec = json.loads(lic.read_text())
        assert "CC0" in json.dumps(rec), f"{asset_id}: licence record is not CC0"


# tile size (metres) of the kit's generated, non-catalogued materials — see pieces_common.reg_generated_materials
GENERATED_TILE_M = {"interior_lit": 2.0, "interior_unlit": 2.0, "ivy_leaf": 0.55}


def _texture_scales(g) -> set[float]:
    """Every KHR_texture_transform scale emitted by the file, from any texture slot."""
    out: set[float] = set()
    for m in g.materials:
        infos = []
        pbr = m.pbrMetallicRoughness
        if pbr is not None:
            infos += [pbr.baseColorTexture, pbr.metallicRoughnessTexture]
        infos += [m.normalTexture, m.occlusionTexture, m.emissiveTexture]
        for info in infos:
            if info is None or not getattr(info, "extensions", None):
                continue
            t = info.extensions.get("KHR_texture_transform")
            if t and "scale" in t:
                out.add(round(float(t["scale"][0]), 4))
    return out


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e["texture_assets"]],
                         ids=[e["id"] for e in ENTRIES if e["texture_assets"]])
def test_uv_tiling_is_in_metres(entry):
    """UVs are metres: every KHR_texture_transform the file emits must equal 1 / physical_size_m of one of the
    piece's own materials, and a material whose tile is not 1 m must actually carry one. (A 1 m tile is the
    identity transform and the exporter omits it.)"""
    import textures as tx
    g = _gltf(entry["id"])
    wanted = set()
    for name in entry["materials"]:
        if name in GENERATED_TILE_M:
            wanted.add(round(1.0 / GENERATED_TILE_M[name], 4))
            continue
        try:
            rec = tx.resolve(name)
        except tx.TextureError:
            continue
        if rec.get("provider") != "procedural":
            wanted.add(round(1.0 / float(rec.get("physical_size_m", 1.0)), 4))
    seen = _texture_scales(g)
    assert seen <= wanted, f"{entry['id']}: texture scales {sorted(seen - wanted)} match no declared tile size"
    if wanted - {1.0}:
        assert "KHR_texture_transform" in (g.extensionsUsed or []), f"{entry['id']}: no KHR_texture_transform"
        assert seen & (wanted - {1.0}), f"{entry['id']}: no non-unit tiling emitted although {sorted(wanted)} are declared"


# Windows whose glazing is legitimately not set back in a masonry reveal.
NOT_RECESSED = {
    "win_bay_window": "a bay projects in front of the wall, so its glazing is ahead of the wall plane",
    "win_curtain_wall_module": "curtain-wall glazing sits in the facade plane by construction",
    "win_dormer": "a dormer stands out of the roof slope, not in a masonry reveal",
}
_RECESSED = [e for e in ENTRIES
             if e["category"] == "window" and "glazing_setback_m" in e and e["id"] not in NOT_RECESSED]


@pytest.mark.parametrize("entry", _RECESSED, ids=[e["id"] for e in _RECESSED])
def test_window_glazing_is_recessed(entry):
    """The sash must sit back inside the masonry opening, not in the wall plane.

    This is the regression guard for the first verification pass, where every window read flat because the glazing
    was barely behind the brick face and the opening threw no shadow. Bays, dormers and curtain-wall modules are
    excluded by ``NOT_RECESSED``: their glazing really is at or in front of the facade plane."""
    d = entry["glazing_setback_m"]
    assert d >= MIN_GLAZING_SETBACK_M, (
        f"{entry['id']}: glazing only {d * 1000:.0f} mm behind the wall plane — a New York sash is set back "
        f"{MIN_GLAZING_SETBACK_M * 1000:.0f}-{MAX_GLAZING_SETBACK_M * 1000:.0f} mm and the reveal is what shades it")
    assert d <= MAX_GLAZING_SETBACK_M, f"{entry['id']}: glazing {d * 1000:.0f} mm back is deeper than any real reveal"


@pytest.mark.parametrize("entry", [e for e in ENTRIES if "glass_clear" in e["materials"]],
                         ids=[e["id"] for e in ENTRIES if "glass_clear" in e["materials"]])
def test_glass_is_translucent(entry):
    """Clear glazing must survive the export as see-through glass: either KHR_materials_transmission or an
    alpha-blended base colour. The catalogue picks which (alpha blending is what the UE translucent material
    uses); the export must not silently flatten it to an opaque slab."""
    g = _gltf(entry["id"])
    glass = [m for m in g.materials if m.name.endswith("glass_clear")]
    assert glass, f"{entry['id']}: no glass_clear material in the glb"
    for m in glass:
        transmissive = bool((m.extensions or {}).get("KHR_materials_transmission"))
        pbr = m.pbrMetallicRoughness
        alpha = pbr.baseColorFactor[3] if (pbr is not None and pbr.baseColorFactor) else 1.0
        blended = m.alphaMode == "BLEND" and alpha < 1.0
        assert transmissive or blended, (
            f"{entry['id']}: {m.name} is opaque — alphaMode {m.alphaMode}, alpha {alpha}, no transmission extension")


# --------------------------------------------------------------------------- kit-wide invariants
def test_every_glb_has_a_catalog_entry():
    on_disk = {p.stem for p in GLB_DIR.glob("*.glb")}
    assert on_disk == set(IDS), f"glb/catalog mismatch: {sorted(on_disk ^ set(IDS))}"


def test_nycsim_extras_round_trip():
    for entry in ENTRIES[:12]:
        g = _gltf(entry["id"])
        # the exporter writes scene custom properties to the glTF scene's extras
        extras = dict(g.asset.extras or {})
        if "nycsim" not in extras and g.scenes:
            extras.update(g.scenes[g.scene or 0].extras or {})
        # DATA_CONTRACTS §13 asks for asset.extras.nycsim as a JSON object; nycsim_bpy writes it that way and leaves
        # the Blender scene custom property (a JSON string) in the scene extras. Accept either shape.
        raw = extras["nycsim"]
        meta = raw if isinstance(raw, dict) else json.loads(raw)
        assert meta["units"] == "metres" and meta["up_axis_blender"] == "Z"
        assert meta["kit_id"] == entry["id"]
        assert meta["schema_version"] == entry["schema_version"]


def test_facade_params_contract_written():
    p = KIT / "facade_params.json"
    assert p.is_file(), "blender_out/kit/facade_params.json missing"
    doc = json.loads(p.read_text())
    import facade_params as fp
    assert doc["materials"] == list(fp.MATERIALS)
    assert len(doc["window_types"]) == len(fp.WINDOW_TYPES)
