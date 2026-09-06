"""Tests for the street-prop and vegetation library (stage 4 assets).

They assert on the exported artefacts, not on the generator's intentions: every ``blender_out/props/<id>.glb``
is parsed with :mod:`blender.props.glb_reader` and checked for a well-formed GLB container, the LOD0/LOD1 node
pair wired through ``MSFT_lod``, bounds against the published nominal dimension recorded in the catalog, the
``SIGN_FACE`` contract (present where required, UV exactly 0..1 over the face), the emissive and light-cone
slots on the lighting props, the triangle budget for vegetation, and the exact MTA route-bullet colours.

Run:  python3 -m pytest tests/test_props.py -q
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pytest

REPO = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[1]))
PROPS = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO / "blender_out")) / "props"
CATALOG = PROPS / "catalog"
sys.path.insert(0, str(REPO / "blender" / "props"))

from glb_reader import Glb, linear_to_srgb_hex  # noqa: E402

# MTA brand-guideline route colours (sRGB). Duplicated here on purpose: the test must fail if the generator's
# table drifts, so it cannot import the generator's own constants.
MTA_COLORS: dict[str, str] = {
    **{k: "#EE352E" for k in "123"}, **{k: "#00933C" for k in "456"}, "7": "#B933AD",
    **{k: "#0039A6" for k in "ACE"}, **{k: "#FF6319" for k in "BDFM"}, "G": "#6CBE45",
    **{k: "#996633" for k in "JZ"}, "L": "#A7A9AC", **{k: "#FCCC0A" for k in "NQRW"}, "S": "#808183",
}
# Categories/ids whose front face must carry the runtime-swappable SIGN_FACE slot.
SIGN_FACE_REQUIRED = {"signs", }
SIGN_FACE_EXTRA_IDS = {"sign_roadwork_w20_1", "ped_pushbutton"}
SIGN_FACE_EXEMPT_IDS = {"post_u_channel_3m", "post_u_channel_2m"}     # supports, not blanks
MAX_TREE_LOD0_TRIS = 12000
MIN_DIM_FOR_TOLERANCE = 0.02      # a 2 mm sign blank's thickness is not a meaningful ratio check


def _entries() -> list[dict]:
    if not CATALOG.is_dir():
        return []
    return [json.loads(p.read_text()) for p in sorted(CATALOG.glob("*.json"))]


ENTRIES = _entries()
IDS = [e["id"] for e in ENTRIES]
pytestmark = pytest.mark.skipif(
    not ENTRIES, reason=f"no prop catalog at {CATALOG}; run: python3 blender/props/build_props.py")


@pytest.fixture(scope="module")
def catalog() -> dict[str, dict]:
    return {e["id"]: e for e in ENTRIES}


@pytest.fixture(scope="module")
def glbs() -> dict[str, Glb]:
    return {e["id"]: Glb(PROPS / f"{e['id']}.glb") for e in ENTRIES}


# ----------------------------------------------------------------------------------- library level
def test_library_is_complete_and_unique(catalog):
    assert len(catalog) == len(ENTRIES), "duplicate ids in the catalog"
    glb_files = {p.stem for p in PROPS.glob("*.glb")}
    assert glb_files == set(catalog), (
        f"glb files and catalog entries disagree: only-glb={sorted(glb_files - set(catalog))} "
        f"only-catalog={sorted(set(catalog) - glb_files)}")
    assert "_smoke" not in glb_files, "the placeholder smoke glb must be deleted"


def test_every_family_is_represented(catalog):
    """The library must cover each group the stage is responsible for."""
    by_cat: dict[str, int] = {}
    for e in catalog.values():
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    for cat, least in (("lighting", 4), ("traffic", 6), ("signs", 9), ("furniture", 30),
                       ("construction", 8), ("vegetation", 60)):
        assert by_cat.get(cat, 0) >= least, f"category {cat}: {by_cat.get(cat, 0)} props, expected >= {least}"


def test_variants_and_kinds_resolve(catalog):
    for e in catalog.values():
        assert e["dataset_kind"], f"{e['id']}: no dataset_kind"
        assert e["notes"] and len(e["notes"]) > 40, f"{e['id']}: notes must name the real object and its source"
        for v in e["variants"]:
            assert v in catalog, f"{e['id']}: variant {v} is not in the library"
            assert v != e["id"], f"{e['id']}: lists itself as a variant"


# ----------------------------------------------------------------------------------- per-prop
@pytest.mark.parametrize("pid", IDS)
def test_glb_loads(pid, glbs):
    g = glbs[pid]
    assert g.json.get("asset", {}).get("version") == "2.0"
    assert g.json.get("meshes"), f"{pid}: no meshes"
    extras = g.asset_extras()
    assert extras.get("prop_id") == pid, f"{pid}: asset extras carry prop_id {extras.get('prop_id')!r}"
    assert extras.get("schema_version") == 1
    assert extras.get("units") == "metres"
    assert extras["anchor"]["facing_blender"] == "+Y"


@pytest.mark.parametrize("pid", IDS)
def test_lod1_present_and_wired(pid, glbs, catalog):
    g = glbs[pid]
    names = g.nodes_by_name()
    assert "LOD0" in names and "LOD1" in names, f"{pid}: nodes are {sorted(n for n in names)}"
    lod0, lod1 = names["LOD0"], names["LOD1"]
    ext = g.json["nodes"][lod0].get("extensions", {}).get("MSFT_lod")
    assert ext and ext.get("ids") == [lod1], f"{pid}: LOD0 does not reference LOD1 through MSFT_lod"
    assert "MSFT_lod" in g.json.get("extensionsUsed", []), f"{pid}: MSFT_lod not declared in extensionsUsed"
    assert lod1 not in g.scene_roots(), f"{pid}: LOD1 must not be a scene root"
    lod1_meshes = g.meshes_under(lod1)
    assert lod1_meshes, f"{pid}: LOD1 has no mesh"
    assert g.triangle_count(lod1_meshes) > 0
    assert catalog[pid]["lod1"] is True
    assert catalog[pid]["polycount"]["lod1_tris"] > 0


@pytest.mark.parametrize("pid", IDS)
def test_lod1_is_cheaper_than_lod0(pid, glbs, catalog):
    g = glbs[pid]
    names = g.nodes_by_name()
    n0 = g.triangle_count(g.meshes_under(names["LOD0"]))
    n1 = g.triangle_count(g.meshes_under(names["LOD1"]))
    assert n0 > 0
    # flat blanks are already minimal and their LOD1 is a copy; everything else must actually get cheaper
    if catalog[pid]["lod1_kind"] == "identical_flat":
        assert n1 == n0
    else:
        assert n1 <= n0 * 0.62, f"{pid}: LOD1 {n1} tris vs LOD0 {n0} — not a meaningful reduction"


@pytest.mark.parametrize("pid", IDS)
def test_bounds_match_nominal(pid, glbs, catalog):
    """Measured size against the published/reference dimension recorded with the prop (per-axis, in metres).

    glTF is Y-up: the exporter maps Blender (X, Y, Z) to glTF (X, Z, -Y), so the nominal (x, y, z) of the
    catalog compares against glTF (x, z, y)."""
    e = catalog[pid]
    g = glbs[pid]
    # LIGHT_CONE planes are a night effect volume, not part of the object's physical size
    lo, hi = g.node_bounds(g.nodes_by_name()["LOD0"], exclude_materials=("LIGHT_CONE",))
    gl = [hi[i] - lo[i] for i in range(3)]
    measured = [gl[0], gl[2], gl[1]]                     # back to Blender axis order
    nominal = e["nominal_size_m"]
    tol = e.get("tolerance", 0.12) if "tolerance" in e else 0.12
    for axis, (m, n) in enumerate(zip(measured, nominal)):
        if n < MIN_DIM_FOR_TOLERANCE:
            assert m <= max(0.05, n * 4 + 0.01), f"{pid}: axis {axis} {m:.4f} m, nominal {n} m"
            continue
        rel = abs(m - n) / n
        assert rel <= tol + 1e-6, (
            f"{pid}: axis {'xyz'[axis]} measured {m:.3f} m vs nominal {n} m ({rel * 100:.1f} % > {tol * 100:.0f} %)")
    # the catalog's own size record must agree with the file
    for axis in range(3):
        assert abs(e["size_m"][axis] - measured[axis]) < 0.02, f"{pid}: catalog size_m disagrees with the glb"


@pytest.mark.parametrize("pid", IDS)
def test_anchor_is_ground_contact(pid, glbs, catalog):
    """Ground-contact props must sit on z = 0 in Blender (glTF +Y). Blanks, decals and the below-grade parts of
    the sunk props declare a different anchor and are exempt."""
    e = catalog[pid]
    origin = e["anchor"]["origin"]
    if origin != "ground_contact":
        assert origin in ("sign_face_center", "bracket_pole_axis", "bullet_center"), f"{pid}: odd anchor {origin}"
        return
    g = glbs[pid]
    lo, hi = g.node_bounds(g.nodes_by_name()["LOD0"], exclude_materials=("LIGHT_CONE",))
    base = lo[1]                                          # glTF +Y is up
    below_grade_ok = {"manhole_coned": 0.07, "manhole_dep": 0.07, "subway_entrance": 2.5, "roadway_plate": 0.01,
                       "tree_grate": 0.03}
    limit = below_grade_ok.get(pid, 0.012)
    assert -limit - 1e-6 <= base <= 0.012, f"{pid}: LOD0 base at z = {base:.4f} m, expected ground contact"


# ----------------------------------------------------------------------------------- material contracts
def _sign_face_required(entry: dict) -> bool:
    if entry["id"] in SIGN_FACE_EXEMPT_IDS:
        return False
    return entry["category"] in SIGN_FACE_REQUIRED or entry["id"] in SIGN_FACE_EXTRA_IDS


@pytest.mark.parametrize("pid", IDS)
def test_sign_face_slot(pid, glbs, catalog):
    e = catalog[pid]
    g = glbs[pid]
    has = "SIGN_FACE" in g.material_names()
    if not _sign_face_required(e):
        return
    assert has, f"{pid}: no SIGN_FACE material slot (materials: {sorted(set(g.material_names()))})"
    assert e["sign_face"] is True, f"{pid}: catalog does not record the SIGN_FACE slot"
    prims = g.primitives_with_material("SIGN_FACE")
    assert prims, f"{pid}: SIGN_FACE material is not used by any primitive"
    for prim in prims:
        (u0, v0), (u1, v1) = g.uv_range(prim)
        assert abs(u0) < 1e-4 and abs(v0) < 1e-4 and abs(u1 - 1.0) < 1e-4 and abs(v1 - 1.0) < 1e-4, (
            f"{pid}: SIGN_FACE UV range ({u0:.4f},{v0:.4f})-({u1:.4f},{v1:.4f}), must be exactly 0..1")


def test_sign_blanks_cover_the_required_mutcd_set(catalog):
    want = {"sign_r6_1_oneway", "sign_r1_1_stop", "sign_r1_2_yield", "sign_r2_1_speed",
            "sign_nyc_parking_18", "sign_nyc_parking_24", "sign_street_name_blade"}
    assert want <= set(catalog), f"missing sign blanks: {sorted(want - set(catalog))}"
    sizes = {"sign_r6_1_oneway": (0.914, 0.305), "sign_r1_1_stop": (0.762, 0.762),
             "sign_r2_1_speed": (0.610, 0.762), "sign_nyc_parking_18": (0.305, 0.457),
             "sign_nyc_parking_24": (0.305, 0.610), "sign_street_name_blade": (0.762, 0.152)}
    for pid, (w, h) in sizes.items():
        kd = catalog[pid]["key_dims_m"]
        got = (kd.get("face_w") or kd.get("blade_w"), kd.get("face_h") or kd.get("blade_h"))
        assert got == pytest.approx((w, h), abs=1e-3), f"{pid}: face {got} m, published {w} x {h} m"


@pytest.mark.parametrize("pid", [e["id"] for e in ENTRIES if e["category"] == "lighting"])
def test_lighting_has_emissive_lamp_and_light_cone(pid, glbs, catalog):
    g = glbs[pid]
    mats = set(g.material_names())
    assert any(m.startswith("LAMP_") for m in mats), f"{pid}: no emissive lamp material ({sorted(mats)})"
    assert "LIGHT_CONE" in mats, f"{pid}: no night light-cone plane"
    assert catalog[pid]["emissive"] or any(m.startswith("LAMP_") for m in mats)
    assert catalog[pid]["light_cone"] is True
    lamp = next(m for m in g.json["materials"] if m.get("name", "").startswith("LAMP_"))
    assert lamp.get("emissiveFactor", [0, 0, 0]) != [0, 0, 0], f"{pid}: lamp material is not emissive"


def test_signal_heads_are_nyc_green_with_backplates(catalog, glbs):
    for pid in ("signal_mastarm_6m", "signal_mastarm_9m", "signal_pedestal", "signal_spanwire"):
        mats = set(glbs[pid].material_names())
        assert "nyc_signal_green" in mats, f"{pid}: signal housing is not the NYC dark green"
        assert "black_matte" in mats and "retro_yellow_border" in mats, f"{pid}: no backplate with a retro border"
        for lens in ("LED_RED", "LED_YELLOW", "LED_GREEN"):
            assert lens in mats, f"{pid}: missing {lens}"
        kd = catalog[pid]["key_dims_m"]
        assert kd.get("pole_height", 5.50) in (5.50, 8.20)


def test_pedestrian_signal_has_runtime_slots(catalog, glbs):
    mats = set(glbs["signal_ped_countdown"].material_names())
    assert {"PED_SYMBOL", "PED_COUNTDOWN"} <= mats
    kd = catalog["signal_ped_countdown"]["key_dims_m"]
    assert kd["head_bottom"] == pytest.approx(2.44, abs=0.01)


# ----------------------------------------------------------------------------------- MTA bullets
def test_mta_bullet_colours_are_exact(glbs, catalog):
    g = glbs["mta_line_bullets"]
    names = set(g.material_names())
    for line, want in MTA_COLORS.items():
        mat = g.material_by_name(f"MTA_{line}")
        assert mat is not None, f"bullet material MTA_{line} missing (have {sorted(names)})"
        factor = mat["pbrMetallicRoughness"].get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
        got = linear_to_srgb_hex(factor)
        assert got == want, f"MTA_{line}: exported {got}, official {want}"
    entry = catalog["mta_line_bullets"]
    assert entry["mta_colors"] == MTA_COLORS, "catalog colour table differs from the MTA brand guidelines"
    assert len(entry["node_names"]) == len(MTA_COLORS)
    for n in entry["node_names"]:
        assert n in g.nodes_by_name(), f"bullet node {n} not exported"


def test_mta_bullet_glyph_contrast(glbs):
    """Yellow bullets carry black glyphs; every other bullet carries white ones."""
    g = glbs["mta_line_bullets"]
    mats = set(g.material_names())
    assert "MTA_GLYPH_DARK" in mats and "MTA_GLYPH_LIGHT" in mats
    def factor(name):
        pbr = g.material_by_name(name)["pbrMetallicRoughness"]
        return linear_to_srgb_hex(pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0]))   # glTF default is white

    dark, light = factor("MTA_GLYPH_DARK"), factor("MTA_GLYPH_LIGHT")
    assert dark == "#111111" and light == "#FFFFFF"


def test_subway_globes_are_the_right_colours(glbs):
    for pid, mat_name in (("subway_globe_green", "LAMP_GLOBE_GREEN"), ("subway_globe_red", "LAMP_GLOBE_RED")):
        mats = set(glbs[pid].material_names())
        assert mat_name in mats, f"{pid}: {mat_name} missing"
        m = glbs[pid].material_by_name(mat_name)
        assert m.get("emissiveFactor", [0, 0, 0]) != [0, 0, 0], f"{pid}: globe is not emissive"


# ----------------------------------------------------------------------------------- vegetation
TREE_IDS = [e["id"] for e in ENTRIES if e["category"] == "vegetation"]


@pytest.mark.parametrize("pid", TREE_IDS)
def test_tree_budget_and_billboard(pid, glbs, catalog):
    g = glbs[pid]
    names = g.nodes_by_name()
    n0 = g.triangle_count(g.meshes_under(names["LOD0"]))
    assert n0 <= MAX_TREE_LOD0_TRIS, f"{pid}: LOD0 {n0} tris exceeds the {MAX_TREE_LOD0_TRIS} budget"
    assert catalog[pid]["lod1_kind"] == "crossed_billboards"
    n1 = g.triangle_count(g.meshes_under(names["LOD1"]))
    assert n1 == 6, f"{pid}: LOD1 is {n1} tris, expected three crossed quads (6)"


def test_tree_library_covers_the_census_top_ten(catalog):
    doc = json.loads((REPO / "blender" / "props" / "dbh_classes.json").read_text())
    latins = {sp["latin"] for sp in doc["species"]}
    assert len(latins) == 10, "dbh_classes.json must carry the ten commonest census species"
    seen = {e["species_latin"] for e in catalog.values() if e["category"] == "vegetation"}
    assert seen == latins, f"species mismatch: {sorted(seen ^ latins)}"
    for latin in latins:
        for cls in ("small", "medium", "large"):
            for bare in (False, True):
                match = [e for e in catalog.values()
                         if e.get("species_latin") == latin and e.get("size_class") == cls
                         and e.get("bare_winter") is bare]
                assert len(match) == 1, f"{latin} / {cls} / bare={bare}: {len(match)} assets"


@pytest.mark.parametrize("pid", TREE_IDS)
def test_tree_dimensions_follow_the_census_and_allometry(pid, catalog):
    doc = json.loads((REPO / "blender" / "props" / "dbh_classes.json").read_text())
    e = catalog[pid]
    sp = next(s for s in doc["species"] if s["latin"] == e["species_latin"])
    cls = next(c for c in sp["classes"] if c["class"] == e["size_class"])
    assert e["dbh_cm"] == cls["dbh_cm"]
    assert e["height_m"] == cls["height_m"]
    assert e["crown_m"] == cls["crown_m"]
    assert e["key_dims_m"]["trunk_radius"] == pytest.approx(cls["dbh_cm"] / 200.0, abs=1e-4)
    assert (e["leaf_cards"] == 0) is bool(e["bare_winter"]), f"{pid}: leaf cards vs bare_winter disagree"


def test_bare_and_leafed_trees_share_a_skeleton(catalog):
    """A winter tree is the same tree without leaves: same species, class and branch count."""
    for e in catalog.values():
        if e["category"] != "vegetation" or not e["bare_winter"]:
            continue
        leafed = catalog[e["id"][: -len("_bare")]]
        assert leafed["branches"] == e["branches"], f"{e['id']}: branch count differs from the leafed variant"
        assert leafed["height_m"] == e["height_m"] and leafed["crown_m"] == e["crown_m"]


# ----------------------------------------------------------------------------------- texture provenance
def test_textures_are_licensed(catalog):
    for e in catalog.values():
        for t in e.get("textures", []):
            assert t["license"] == "CC0 1.0", f"{e['id']}: texture {t['asset_id']} is {t['license']}"
            assert t["source_url"].startswith("https://"), f"{e['id']}: texture {t['asset_id']} has no source url"


def test_polycounts_are_recorded_and_sane(catalog):
    total = sum(e["polycount"]["lod0_tris"] for e in catalog.values())
    assert total > 0
    for e in catalog.values():
        assert e["polycount"]["lod0_tris"] > 0, f"{e['id']}: empty LOD0"
        assert e["glb_bytes"] > 500, f"{e['id']}: suspiciously small glb"
        assert math.isfinite(e["bounds"]["min"][0])
