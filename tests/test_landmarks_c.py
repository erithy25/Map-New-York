"""Verification tests for landmark agent C's assets (Hudson Yards, Billionaires' Row, Times Square, museums,
cultural buildings, stadiums, outer-borough icons).

The tests read the exported artefacts, not the build scripts: every ``blender_out/landmarks/<id>.glb`` and its
catalog entry ``blender_out/landmarks/catalog/<id>.json``. They check the contract in ``docs/DATA_CONTRACTS.md``
Sections 11 and 13 plus the fidelity rules the brief sets for this lane:

* one script, one glb and one catalog entry per registry id;
* the glb's bounding-box height matches the published height in ``c_common.SCRIPTS`` within 1 %;
* the model sits on the real footprint: catalog ``footprint_iou`` >= 0.90;
* LOD0 within its triangle budget and a ``<id>_LOD1`` node at <= 20 % of LOD0;
* ``origin_tm`` is the NYC_TM position of the model origin and is inside New York City's bounds;
* every dimension in the docstring is sourced and the fidelity statement names what is *not* modelled;
* the Times Square screens are emissive ``TSQ_SCREEN_<n>`` materials whose faces carry exact 0..1 UVs.

Run: ``python3 -m pytest tests/test_landmarks_c.py -q``. Tests that need an artefact that has not been exported yet
are skipped with the missing path named, so the file is useful during the build as well as after it.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "blender" / "landmarks"))
sys.path.insert(0, str(REPO / "blender" / "common"))

OUT = REPO / "blender_out" / "landmarks"
CATALOG = OUT / "catalog"
VERIFY = REPO / "docs" / "verification" / "landmarks"

# NYC_TM working bounds (metres): the five boroughs plus the NJ waterfront, from docs/ARCHITECTURE.md Section 2.
TM_BOUNDS = (-32000.0, -30000.0, 22000.0, 32000.0)


def _registry() -> dict:
    """The lane-C registry, imported without bpy (c_common imports common, which imports bpy)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_c_common_registry", REPO / "blender" / "landmarks" / "c_common.py")
    try:
        import bpy  # noqa: F401
    except Exception:                                   # pragma: no cover - bpy is installed in this environment
        pytest.skip("bpy is not available, so c_common cannot be imported")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SCRIPTS


SCRIPTS = _registry()
IDS = sorted(SCRIPTS)


def _glb(path: Path) -> tuple[dict, bytes]:
    """Parse a .glb into (json chunk, binary chunk)."""
    data = path.read_bytes()
    magic, version, _length = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67, f"{path.name} is not a glb"
    assert version == 2, f"{path.name} is glTF {version}, expected 2"
    off = 12
    js: dict = {}
    bin_chunk = b""
    while off < len(data):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    assert js, f"{path.name} has no JSON chunk"
    return js, bin_chunk


def _exported(landmark_id: str) -> tuple[Path, Path]:
    glb = OUT / f"{landmark_id}.glb"
    cat = CATALOG / f"{landmark_id}.json"
    if not glb.exists() or not cat.exists():
        pytest.skip(f"not exported yet: {glb.relative_to(REPO)} / {cat.relative_to(REPO)}")
    return glb, cat


def _extras(js: dict) -> dict:
    meta = js.get("asset", {}).get("extras", {}).get("nycsim")
    if meta is None:
        sc = js.get("scenes", [{}])[0].get("extras", {})
        meta = sc.get("nycsim")
    if isinstance(meta, str):
        meta = json.loads(meta)
    return meta or {}


# ------------------------------------------------------------------------------------------------ registry itself
def test_registry_is_complete_and_consistent():
    assert len(SCRIPTS) == 39, f"expected 39 lane-C landmarks, got {len(SCRIPTS)}"
    for lid, meta in SCRIPTS.items():
        assert lid.startswith("c_"), lid
        assert meta["name"] and isinstance(meta["name"], str)
        assert meta["height_m"] > 0
        assert meta["height_source"], f"{lid} has no height source"
        assert isinstance(meta["bins"], list)
        assert meta["budget"] in (250_000, 400_000), (lid, meta["budget"])
        for part in meta["parts"]:
            assert part["height_m"] > 0 and part["height_source"], (lid, part["id"])


def test_every_registry_id_has_a_script():
    for lid in IDS:
        script = REPO / "blender" / "landmarks" / f"{lid}.py"
        assert script.exists(), f"missing build script {script.relative_to(REPO)}"


@pytest.mark.parametrize("lid", IDS)
def test_script_docstring_cites_sources_and_states_gaps(lid):
    """The brief's rule: every dimension cited to a source, and an explicit statement of what is not modelled."""
    text = (REPO / "blender" / "landmarks" / f"{lid}.py").read_text()
    doc = text.split('"""')[1]
    flat = " ".join(doc.split())                       # the docstrings are hard-wrapped, so collapse the newlines
    assert "Dimensions used" in flat or "Alignment source" in flat, lid
    assert doc.count("[") >= 3, f"{lid}: fewer than three bracketed source citations in the docstring"
    assert "NOT modelled" in flat or "not modelled" in flat, f"{lid}: no statement of what is not modelled"
    for banned in ("TODO", "FIXME", "XXX", "placeholder", "stub"):
        assert banned not in text, f"{lid}: contains {banned!r}"


# --------------------------------------------------------------------------------------------------- the exports
@pytest.mark.parametrize("lid", IDS)
def test_catalog_entry_matches_the_contract(lid):
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    meta = SCRIPTS[lid]
    for field in ("id", "name", "bins", "script", "footprint_source", "height_m", "height_source", "notes",
                  "fidelity_statement", "glb", "origin_tm", "heading_deg", "tris_lod0", "tris_lod1"):
        assert field in e, f"{lid}: catalog entry is missing {field!r}"
    assert e["id"] == lid
    assert e["name"] == meta["name"]
    assert abs(e["height_m"] - meta["height_m"]) < 1e-6
    assert e["height_source"] == meta["height_source"]
    assert len(e["fidelity_statement"]) > 120, f"{lid}: fidelity statement is too short to be meaningful"
    assert "Not modelled" in e["fidelity_statement"] or "not modelled" in e["fidelity_statement"]


@pytest.mark.parametrize("lid", IDS)
def test_height_within_one_percent_of_the_published_value(lid):
    glb, cat = _exported(lid)
    e = json.loads(cat.read_text())
    published = SCRIPTS[lid]["height_m"]
    modelled = e["model_height_m"]
    assert abs(modelled - published) <= 0.01 * published, \
        f"{lid}: model height {modelled} m vs published {published} m"
    js, _ = _glb(glb)
    ex = _extras(js)
    assert abs(ex["height_m"] - published) < 1e-6, f"{lid}: glb extras height {ex.get('height_m')}"


@pytest.mark.parametrize("lid", IDS)
def test_footprint_iou_above_0_9(lid):
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    iou = e["footprint_iou"]
    assert iou is not None, f"{lid}: no footprint IoU recorded"
    assert iou >= 0.90, f"{lid}: footprint IoU {iou} < 0.90"


ELEVATED = ("c_high_line", "c_little_island", "c_pier_17_seaport", "c_flushing_meadows")


@pytest.mark.parametrize("lid", ELEVATED)
def test_elevated_landmarks_say_how_their_iou_was_measured(lid):
    """A deck 9 m in the air cannot be checked by the standard 1.5 m section, so those four must say what they did."""
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    method = e.get("footprint_iou_method")
    assert method, f"{lid}: no footprint_iou_method recorded although it does not use the standard 1.5 m section"
    assert len(method) > 40, f"{lid}: footprint_iou_method is too terse to be an explanation"


@pytest.mark.parametrize("lid", IDS)
def test_triangle_budget_and_lod1(lid):
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    budget = SCRIPTS[lid]["budget"]
    assert e["tris_lod0"] <= budget, f"{lid}: {e['tris_lod0']} tris > budget {budget}"
    assert e["tris_lod1"] <= 0.20 * e["tris_lod0"], \
        f"{lid}: LOD1 {e['tris_lod1']} tris > 20 % of LOD0 {e['tris_lod0']}"
    assert e["tris_lod1"] > 0, f"{lid}: LOD1 is empty"


@pytest.mark.parametrize("lid", IDS)
def test_glb_has_a_lod1_node_and_nycsim_extras(lid):
    glb, _ = _exported(lid)
    js, _ = _glb(glb)
    names = {n.get("name", "") for n in js.get("nodes", [])}
    assert f"{lid}_LOD1" in names, f"{lid}: no {lid}_LOD1 node in the glb (nodes: {sorted(names)[:8]})"
    ex = _extras(js)
    for field in ("landmark_id", "origin_tm", "bins", "heading_deg", "height_m", "fidelity_statement", "agent"):
        assert field in ex, f"{lid}: glb extras missing {field!r}"
    assert ex["landmark_id"] == lid
    assert ex["agent"] == "C"


@pytest.mark.parametrize("lid", IDS)
def test_origin_is_inside_new_york(lid):
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    x, y, z = e["origin_tm"]
    x0, y0, x1, y1 = TM_BOUNDS
    assert x0 <= x <= x1 and y0 <= y <= y1, f"{lid}: origin_tm {e['origin_tm']} is outside the NYC_TM working bounds"
    assert -10.0 <= z <= 90.0, f"{lid}: ground z {z} m is implausible for NAVD88 in NYC"


@pytest.mark.parametrize("lid", IDS)
def test_units_are_metres_and_the_model_is_plausibly_sized(lid):
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    lo = e["bounds_local_m"]["min"]
    hi = e["bounds_local_m"]["max"]
    assert hi[2] - lo[2] > 3.0, f"{lid}: model is only {hi[2] - lo[2]:.1f} m tall"
    assert lo[2] > -60.0, f"{lid}: model extends {lo[2]:.1f} m below ground"


# ------------------------------------------------------------------------------------- Times Square video screens
def test_times_square_screen_slots_are_emissive_with_0_1_uvs():
    lid = "c_times_square"
    glb, cat = _exported(lid)
    js, binary = _glb(glb)
    e = json.loads(cat.read_text())
    slots = [k for k in e["material_slots"] if k.startswith("TSQ_SCREEN_")]
    assert len(slots) >= 12, f"only {len(slots)} TSQ_SCREEN slots; the square needs a screen per LED surface"
    mats = {m["name"]: m for m in js.get("materials", []) if "name" in m}
    for slot in slots:
        assert slot in mats, f"{slot} is not a material in the glb"
        m = mats[slot]
        emissive = m.get("emissiveFactor") or [0, 0, 0]
        strength = (m.get("extensions", {}).get("KHR_materials_emissive_strength", {})
                    .get("emissiveStrength", 1.0))
        assert max(emissive) * strength > 0.5, f"{slot} is not emissive (factor {emissive}, strength {strength})"
    # the UVs of every screen face must be exactly the 0..1 island the engine expects
    accessors = js["accessors"]
    views = js["bufferViews"]

    def read_vec2(acc_idx: int) -> list[tuple[float, float]]:
        acc = accessors[acc_idx]
        bv = views[acc["bufferView"]]
        start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = bv.get("byteStride") or 8
        out = []
        for i in range(acc["count"]):
            o = start + i * stride
            out.append(struct.unpack_from("<ff", binary, o))
        return out

    mat_index = {m.get("name"): i for i, m in enumerate(js.get("materials", []))}
    checked = 0
    for mesh in js.get("meshes", []):
        for prim in mesh.get("primitives", []):
            mi = prim.get("material")
            if mi is None:
                continue
            name = js["materials"][mi].get("name", "")
            if not name.startswith("TSQ_SCREEN_"):
                continue
            uv_acc = prim.get("attributes", {}).get("TEXCOORD_0")
            assert uv_acc is not None, f"{name}: screen primitive has no TEXCOORD_0"
            uvs = read_vec2(uv_acc)
            us = sorted({round(u, 4) for u, _ in uvs})
            vs = sorted({round(v, 4) for _, v in uvs})
            assert us == [0.0, 1.0], f"{name}: u values {us} are not exactly 0 and 1"
            assert vs == [0.0, 1.0], f"{name}: v values {vs} are not exactly 0 and 1"
            checked += 1
    assert checked >= 12, f"only {checked} screen primitives carried 0..1 UVs"
    assert mat_index  # the material table was read


# --------------------------------------------------------------------------------- group scripts and their parts
@pytest.mark.parametrize("lid", [i for i in IDS if SCRIPTS[i]["parts"]])
def test_group_parts_are_recorded_in_the_catalog(lid):
    _, cat = _exported(lid)
    e = json.loads(cat.read_text())
    parts = e["dimensions"].get("parts")
    assert parts, f"{lid}: the catalog does not record the group's parts"
    for p in SCRIPTS[lid]["parts"]:
        assert p["id"] in parts, f"{lid}: part {p['id']} missing from the catalog"
        assert abs(parts[p["id"]]["height_m"] - p["height_m"]) < 1e-6
        assert parts[p["id"]]["height_source"] == p["height_source"]
    assert SCRIPTS[lid]["height_m"] == max(p["height_m"] for p in SCRIPTS[lid]["parts"]), \
        f"{lid}: the group height must be the tallest part"


# --------------------------------------------------------------------------------------------- specific fidelity
def test_vessel_has_its_154_flights_and_80_landings():
    _, cat = _exported("c_hudson_yards")
    d = json.loads(cat.read_text())["dimensions"]
    assert d["vessel_flights"] == 154
    assert d["vessel_landings"] == 80
    assert abs(d["vessel_h_m"] - 46.0) < 1e-6


def test_432_park_has_five_double_height_mechanical_voids():
    _, cat = _exported("c_billionaires_row")
    d = json.loads(cat.read_text())["dimensions"]
    assert d["432_void_floors"] == [12, 30, 48, 66, 84]
    assert abs(d["432_tube_m"] - 28.5) < 1e-6
    assert abs(d["432_window_m"] - 3.05) < 1e-6
    assert abs(6 * d["432_window_m"] + 7 * d["432_pier_m"] - d["432_tube_m"]) < 0.01, \
        "the six-by-six window grid must fill the 28.5 m tube exactly"


def test_central_park_tower_cantilever_starts_at_floor_30():
    _, cat = _exported("c_billionaires_row")
    d = json.loads(cat.read_text())["dimensions"]
    assert abs(d["cpt_cantilever_z_m"] - 91.0) < 1e-6
    assert abs(d["cpt_cantilever_m"] - 8.5) < 1e-6


def test_stadium_field_dimensions_are_the_published_ones():
    _, cat = _exported("c_yankee_stadium")
    d = json.loads(cat.read_text())["dimensions"]
    assert [round(v, 1) for v in d["field_lf_lc_cf_rc_rf_m"]] == [96.9, 121.6, 124.4, 117.3, 95.7]
    _, cat = _exported("c_citi_field")
    d = json.loads(cat.read_text())["dimensions"]
    assert [round(v, 1) for v in d["field_lf_lc_cf_rc_rf_m"]] == [102.1, 115.5, 124.4, 116.7, 100.6]


def test_high_line_length_matches_the_published_alignment():
    """Compare like with like: Friends of the High Line's 1.45 mi pre-dates the 2019 Spur, so the Spur's own length
    is measured separately and excluded before the comparison. The remaining 8 % is the mapped alignment's curve
    around the West Side Yard, which the round published figure does not follow — see the script's docstring, which
    also records that the polygon's ends were checked against Gansevoort Street and West 34th Street."""
    _, cat = _exported("c_high_line")
    d = json.loads(cat.read_text())["dimensions"]
    assert abs(d["deck_z_m"] - 9.14) < 1e-6
    assert d["columns"] > 200, "the 2.3 km viaduct needs its column line"
    assert 100.0 < d["spur_length_m"] < 200.0, \
        f"the 30th Street Spur measured {d['spur_length_m']} m, which is not a plausible branch length"
    like_for_like = d["measured_length_excl_spur_m"]
    assert abs(like_for_like - d["published_length_m"]) < 0.10 * d["published_length_m"], \
        (f"deck length excluding the Spur {like_for_like} m vs published {d['published_length_m']} m "
         f"({100 * (like_for_like - d['published_length_m']) / d['published_length_m']:.1f} %)")
    assert d["measured_length_m"] > like_for_like, "the whole-park length must include the Spur"


def test_little_island_has_all_132_pots():
    _, cat = _exported("c_little_island")
    d = json.loads(cat.read_text())["dimensions"]
    assert d["pots"] == d["pots_published"] == 132
    assert abs(d["area_m2"] - d["area_published_m2"]) < 0.10 * d["area_published_m2"]


def test_the_shed_shell_is_a_separate_movable_node():
    glb, cat = _exported("c_hudson_yards")
    js, _ = _glb(glb)
    names = {n.get("name", "") for n in js.get("nodes", [])}
    assert "c_hudson_yards_shed_shell" in names, "The Shed's movable shell must be its own node"
    e = json.loads(cat.read_text())
    assert "shell" in e["material_slots"], "the catalog must document how to move the shell"
    assert abs(e["dimensions"]["shed_shell_travel_m"] - 83.2) < 1e-6


# ------------------------------------------------------------------------------------------------------- renders
@pytest.mark.parametrize("lid", IDS)
def test_verification_renders_exist(lid):
    _exported(lid)
    pngs = sorted(VERIFY.glob(f"{lid}_*.png"))
    assert pngs, f"{lid}: no verification render in {VERIFY.relative_to(REPO)}"
    for p in pngs:
        assert p.stat().st_size > 5000, f"{p.name} is only {p.stat().st_size} bytes"


@pytest.mark.parametrize("lid", IDS)
def test_verification_renders_can_serve_as_evidence(lid):
    """A render only counts if the subject is visible in it.

    The first three thresholds are the project's own (see
    tests/test_world_integration.py::test_verification_renders_can_actually_serve_as_evidence): black, blown out,
    or no variation at all. The fourth catches the case those three miss — a frame of nothing but sky over ground
    has a smooth gradient, so its standard deviation can be 0.05 while it shows no building whatsoever. ``busy`` is
    the fraction of pixels whose 3x3 neighbourhood spans more than 0.02 in luminance: over this lane's 86 renders
    the six frames that showed nothing scored 0.0001-0.0196 and the worst legitimate frame scored 0.0364."""
    _exported(lid)
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image", reason="Pillow is needed to inspect the renders")
    from PIL import ImageFilter
    for p in sorted(VERIFY.glob(f"{lid}_*.png")):
        im = Image.open(p).convert("L")
        a = np.asarray(im, dtype=np.float32) / 255.0
        mean, sd = float(a.mean()), float(a.std())
        hi = np.asarray(im.filter(ImageFilter.MaxFilter(3)), dtype=np.float32) / 255.0
        lo = np.asarray(im.filter(ImageFilter.MinFilter(3)), dtype=np.float32) / 255.0
        busy = float(((hi - lo) > 0.02).mean())
        assert mean >= 0.06, f"{p.name} is black (mean luminance {mean:.3f}) — camera inside geometry?"
        assert not (mean > 0.94 and sd < 0.025), f"{p.name} is blown out (mean {mean:.3f}, sd {sd:.3f})"
        assert sd >= 0.025, f"{p.name} is featureless (sd {sd:.3f})"
        assert busy >= 0.030, (f"{p.name}: only {busy * 100:.1f} % of pixels carry local detail — the subject is "
                               f"not in the frame (sd {sd:.3f} comes from the sky gradient)")


def test_canonical_viewpoint_renders_exist():
    """The four viewpoints the brief names, produced by blender/landmarks/c_renders.py."""
    for name in ("canonical_times_square_from_duffy_square",
                 "canonical_billionaires_row_from_sheep_meadow",
                 "canonical_guggenheim_from_fifth_avenue",
                 "canonical_top_of_the_rock_south"):
        p = VERIFY / f"{name}.png"
        if not p.exists():
            pytest.skip(f"canonical render not produced yet: {p.relative_to(REPO)}")
        assert p.stat().st_size > 20000, f"{p.name} is only {p.stat().st_size} bytes"
