"""Acceptance tests for the character stage.

Everything is checked against the *exported* artefacts - ``blender_out/character/player.glb``, its catalog
entry and the NPC manifest - not against the generator, plus pure-Python unit tests of the CMU ASF/AMC parser
and forward-kinematics solver that need neither Blender nor the exported assets.

Run:  python3 -m pytest tests/test_character.py -q
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHAR_DIR = REPO_ROOT / "blender" / "character"
sys.path.insert(0, str(CHAR_DIR))

import asf_amc  # noqa: E402
import ue5_skeleton as ue5  # noqa: E402
import variety  # noqa: E402

PLAYER_GLB = REPO_ROOT / "blender_out" / "character" / "player.glb"
CATALOG = REPO_ROOT / "blender_out" / "character" / "catalog" / "player.json"
NPC_MANIFEST = REPO_ROOT / "blender_out" / "character" / "npc_variety.json"
MOCAP = REPO_ROOT / "assets" / "character" / "cmu_mocap"

#: Every animation the character brief requires, by name.
REQUIRED_CLIPS = (
    "idle", "idle_phone", "walk", "jog", "run", "turn_left_90", "turn_right_90", "stairs_up", "stairs_down",
    "open_car_door", "enter_car", "sit_drive_idle", "drive_steer_left", "drive_steer_right", "drive_shift",
    "drive_shoulder_check_left", "drive_shoulder_check_right", "drive_mirror_check", "exit_car",
    "close_door", "lean_on_car", "hail_cab", "look_around",
)
NPC_CLIPS = ("umbrella_hold", "phone_walk")

ARKIT_52 = (
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff",
    "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft",
    "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight", "mouthFunnel", "mouthLeft", "mouthLowerDownLeft",
    "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight", "mouthPucker", "mouthRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft",
    "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight", "tongueOut",
)


# --------------------------------------------------------------------------------------------- glb reading
class Glb:
    """Minimal glTF-binary reader: JSON chunk plus typed accessor access."""

    _COMPONENT = {5120: "<i1", 5121: "<u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
    _COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

    def __init__(self, path: Path) -> None:
        with open(path, "rb") as fh:
            magic, self.version, _length = struct.unpack("<III", fh.read(12))
            assert magic == 0x46546C67, f"{path} is not a .glb"
            json_len, json_type = struct.unpack("<II", fh.read(8))
            assert json_type == 0x4E4F534A
            self.doc = json.loads(fh.read(json_len).decode("utf-8"))
            bin_len, bin_type = struct.unpack("<II", fh.read(8))
            assert bin_type == 0x004E4942
            self.blob = fh.read(bin_len)

    def accessor(self, index: int) -> np.ndarray:
        """Read accessor ``index`` as an (count, ncomp) array, dense or sparse.

        glTF lets an accessor omit ``bufferView`` entirely: the base data is then all zeros and the real
        values live in an optional ``sparse`` block of (indices, values) pairs.  Blender writes every morph
        target that way - a face blendshape moves a few hundred of 14 517 vertices, so the sparse form is
        about fifty times smaller - which is why a reader that assumes ``bufferView`` raises ``KeyError``
        on this file's morph targets rather than reading them.
        """
        acc = self.doc["accessors"][index]
        ncomp = self._COUNT[acc["type"]]
        dtype = np.dtype(self._COMPONENT[acc["componentType"]])
        if "bufferView" in acc:
            out = self._read(acc["bufferView"], acc.get("byteOffset", 0), dtype, ncomp, acc["count"])
        else:
            out = np.zeros((acc["count"], ncomp), dtype=dtype)
        sparse = acc.get("sparse")
        if sparse:
            out = out.copy()
            indices_spec = sparse["indices"]
            values_spec = sparse["values"]
            idx_dtype = np.dtype(self._COMPONENT[indices_spec["componentType"]])
            indices = self._read(indices_spec["bufferView"], indices_spec.get("byteOffset", 0),
                                 idx_dtype, 1, sparse["count"]).ravel().astype(np.int64)
            values = self._read(values_spec["bufferView"], values_spec.get("byteOffset", 0),
                                dtype, ncomp, sparse["count"])
            out[indices] = values
        return out

    def _read(self, view_index: int, byte_offset: int, dtype: np.dtype, ncomp: int,
              count: int) -> np.ndarray:
        view = self.doc["bufferViews"][view_index]
        offset = view.get("byteOffset", 0) + byte_offset
        stride = view.get("byteStride")
        if stride and stride != ncomp * dtype.itemsize:
            rows = [np.frombuffer(self.blob, dtype=dtype, count=ncomp, offset=offset + i * stride)
                    for i in range(count)]
            return np.vstack(rows)
        flat = np.frombuffer(self.blob, dtype=dtype, count=count * ncomp, offset=offset)
        return flat.reshape(count, ncomp)


@pytest.fixture(scope="module")
def glb() -> Glb:
    if not PLAYER_GLB.exists():
        pytest.skip(f"{PLAYER_GLB} not built (run blender/character/build_character.py)")
    return Glb(PLAYER_GLB)


@pytest.fixture(scope="module")
def catalog() -> dict:
    if not CATALOG.exists():
        pytest.skip(f"{CATALOG} not built")
    with open(CATALOG, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------------------------------------- skeleton
def test_ue5_bone_set_is_self_consistent() -> None:
    """The skeleton definition itself: every bone has a parent that exists, and the roots are right."""
    names = ue5.ue5_bone_names()
    parents = ue5.ue5_parents()
    assert len(names) == len(set(names)), "duplicate bone names"
    assert set(names) == set(parents)
    assert parents["root"] is None
    for name in names:
        parent = parents[name]
        assert parent is None or parent in names, f"{name} has unknown parent {parent}"
        if parent is not None:
            assert names.index(parent) < names.index(name), f"{name} is listed before its parent"
    assert len(names) == 71, f"expected the 71-bone UE5 mannequin set, got {len(names)}"


def test_glb_skeleton_bone_names(glb: Glb) -> None:
    """The exported skin's joints are exactly the UE5-Mannequin bone set, with the right hierarchy."""
    assert glb.doc.get("skins"), "no skin in the glb"
    skin = glb.doc["skins"][0]
    nodes = glb.doc["nodes"]
    joint_names = [nodes[i].get("name") for i in skin["joints"]]
    expected = ue5.ue5_bone_names()
    assert set(joint_names) == set(expected), (
        f"missing {sorted(set(expected) - set(joint_names))}, "
        f"unexpected {sorted(set(joint_names) - set(expected))}")

    parent_of = {}
    for index, node in enumerate(nodes):
        for child in node.get("children", []):
            parent_of[child] = index
    expected_parents = ue5.ue5_parents()
    for joint in skin["joints"]:
        name = nodes[joint].get("name")
        parent_index = parent_of.get(joint)
        got = nodes[parent_index].get("name") if parent_index is not None else None
        want = expected_parents[name]
        if want is None:
            continue                      # the armature object node sits above `root`
        assert got == want, f"{name}: parent {got!r}, expected {want!r}"


def test_glb_has_the_ik_bones(glb: Glb) -> None:
    joint_names = {glb.doc["nodes"][i].get("name") for i in glb.doc["skins"][0]["joints"]}
    for name, _parent in ue5.IK_BONES:
        assert name in joint_names, f"IK bone {name} missing"


def test_glb_has_the_full_finger_chain(glb: Glb) -> None:
    joint_names = {glb.doc["nodes"][i].get("name") for i in glb.doc["skins"][0]["joints"]}
    for side in ("l", "r"):
        for bone in ue5.finger_bones(side):
            assert bone in joint_names, f"finger bone {bone} missing"


# ------------------------------------------------------------------------------------------------ the glb
def test_glb_loads_and_has_content(glb: Glb) -> None:
    assert glb.version == 2
    assert glb.doc["asset"]["version"].startswith("2.")
    assert len(glb.doc.get("meshes", [])) >= 6, "body, eyes, cornea, teeth, tongue, hair and clothing"
    assert len(glb.doc.get("materials", [])) >= 6
    assert len(glb.blob) > 1_000_000


def test_glb_carries_the_nycsim_asset_extras(glb: Glb) -> None:
    extras = glb.doc["asset"].get("extras", {}).get("nycsim")
    assert extras, "DATA_CONTRACTS §13 requires asset.extras.nycsim"
    assert extras["schema_version"] == 1
    assert extras["units"] == "metres"
    assert extras["skeleton"] == "UE5_Mannequin"
    assert extras["bone_count"] == 71
    assert extras["fps"] == 30
    assert extras["max_bone_influences"] == 4


def test_glb_is_loadable_by_pygltflib() -> None:
    pygltflib = pytest.importorskip("pygltflib")
    if not PLAYER_GLB.exists():
        pytest.skip("player.glb not built")
    model = pygltflib.GLTF2().load(str(PLAYER_GLB))
    assert model.skins and model.animations and model.meshes
    assert len(model.animations) >= len(REQUIRED_CLIPS)


# --------------------------------------------------------------------------------------------- animations
def test_all_required_animations_are_present(glb: Glb) -> None:
    names = {a.get("name") for a in glb.doc.get("animations", [])}
    missing = [c for c in REQUIRED_CLIPS if c not in names]
    assert not missing, f"missing animations: {missing}"


def test_npc_poses_are_in_the_shared_set(glb: Glb) -> None:
    names = {a.get("name") for a in glb.doc.get("animations", [])}
    missing = [c for c in NPC_CLIPS if c not in names]
    assert not missing, f"missing NPC animations: {missing}"


def test_animations_are_30fps_and_non_trivial(glb: Glb, catalog: dict) -> None:
    meta = {c["name"]: c for c in catalog["animations"]}
    for animation in glb.doc["animations"]:
        name = animation["name"]
        assert name in meta, f"{name} has no catalog metadata"
        assert meta[name]["fps"] == 30 or abs(meta[name]["fps"] - 30) < 12, \
            f"{name} is {meta[name]['fps']} fps"
        inputs = {s["input"] for s in animation["samplers"]}
        times = np.concatenate([glb.accessor(i).ravel() for i in inputs])
        assert times.size > 0
        if meta[name]["frames"] > 2:
            deltas = np.diff(np.unique(np.round(times, 6)))
            assert deltas.size, f"{name} has a single keyframe time"
            assert abs(float(np.median(deltas)) - 1.0 / 30.0) < 1e-3, \
                f"{name} key spacing is {float(np.median(deltas)):.5f} s, expected 1/30"


def test_locomotion_clips_carry_their_ground_speed(catalog: dict) -> None:
    speeds = {c["name"]: c.get("speed_mps") for c in catalog["animations"]}
    assert speeds["walk"] == pytest.approx(1.4, abs=0.001)
    assert speeds["jog"] == pytest.approx(2.8, abs=0.001)
    assert speeds["run"] == pytest.approx(5.0, abs=0.001)


def test_locomotion_clips_are_retargeted_mocap(catalog: dict) -> None:
    methods = {c["name"]: c["method"] for c in catalog["animations"]}
    for clip in ("walk", "jog", "run"):
        assert methods[clip] == "cmu-mocap-retarget", f"{clip} is {methods[clip]}"
    assert "mocap" in methods["idle"], "the idle posture must come from mocap"


def test_every_clip_declares_its_method(catalog: dict) -> None:
    for clip in catalog["animations"]:
        assert clip.get("method"), f"{clip['name']} has no method recorded"
        assert clip.get("frames", 0) >= 2, f"{clip['name']} has {clip.get('frames')} frames"


def test_additive_steering_poses_are_marked(catalog: dict) -> None:
    additive = {c["name"] for c in catalog["animations"] if c.get("additive")}
    assert {"drive_steer_left", "drive_steer_right"} <= additive


def test_loop_clips_start_and_end_on_the_same_pose(glb: Glb, catalog: dict) -> None:
    """A looping clip whose first and last keys differ pops every cycle."""
    looping = {c["name"] for c in catalog["animations"] if c.get("loop")}
    for animation in glb.doc["animations"]:
        if animation["name"] not in looping:
            continue
        for channel in animation["channels"]:
            sampler = animation["samplers"][channel["sampler"]]
            values = glb.accessor(sampler["output"])
            if values.shape[0] < 3:
                continue
            first, last = values[0], values[-1]
            delta = float(np.abs(first - last).max())
            assert delta < 2e-3, (f"{animation['name']}: {channel['target']['path']} on node "
                                  f"{channel['target']['node']} differs by {delta:.4f} between the first "
                                  f"and last key")


# --------------------------------------------------------------------------------------------- blendshapes
def test_blendshape_count_and_names(glb: Glb) -> None:
    body = None
    for mesh in glb.doc["meshes"]:
        names = mesh.get("extras", {}).get("targetNames", [])
        if len(names) >= 40:
            body = (mesh, names)
            break
    assert body is not None, "no mesh with a full blendshape set"
    mesh, names = body
    assert len(names) == 52, f"{len(names)} morph targets, expected the 52 ARKit face units"
    assert set(names) == set(ARKIT_52), (f"missing {sorted(set(ARKIT_52) - set(names))}, "
                                         f"extra {sorted(set(names) - set(ARKIT_52))}")
    for primitive in mesh["primitives"]:
        assert len(primitive.get("targets", [])) == 52


def _morph_reach(glb: Glb) -> dict[str, dict[str, float]]:
    """{blendshape name: {mesh name: largest vertex displacement in metres}} over the whole file."""
    reach: dict[str, dict[str, float]] = {}
    for mesh in glb.doc["meshes"]:
        names = mesh.get("extras", {}).get("targetNames", [])
        if not names:
            continue
        for primitive in mesh["primitives"]:
            for name, target in zip(names, primitive.get("targets", [])):
                if "POSITION" not in target:
                    continue
                delta = glb.accessor(target["POSITION"])
                per_mesh = reach.setdefault(name, {})
                mesh_name = mesh.get("name", "?")
                per_mesh[mesh_name] = max(per_mesh.get(mesh_name, 0.0), float(np.abs(delta).max()))
    return reach


def test_blendshapes_actually_move_vertices(glb: Glb) -> None:
    """Every ARKit channel must displace at least one vertex *somewhere* in the file.

    An all-zero morph is a silent failure, and one of the 52 is not on the body: MakeHuman's ``tongueOut``
    target displaces the helper tongue, which is proxy geometry the build deletes, so the channel is carried
    by the separate tongue mesh instead (``mh_build.transfer_tongue_morph``).  The check is therefore over
    the union of the file's meshes, plus an explicit assertion that the tongue really does move - this file
    used to ship a dead ``tongueOut`` and no test caught it, because the reader could not decode a sparse
    accessor and raised before it got there.
    """
    reach = _morph_reach(glb)
    missing = [name for name in ARKIT_52 if name not in reach]
    assert not missing, f"blendshapes absent from the glb: {missing}"
    dead = [name for name in ARKIT_52 if max(reach[name].values()) <= 1e-5]
    assert not dead, f"blendshapes that move nothing anywhere in the file: {dead}"

    tongue = reach["tongueOut"]
    on_tongue = {mesh: value for mesh, value in tongue.items() if value > 1e-5}
    assert on_tongue, f"tongueOut moves nothing; per-mesh reach {tongue}"
    assert max(on_tongue.values()) > 1e-3, (
        f"tongueOut moves only {max(on_tongue.values()) * 1000:.2f} mm - the tongue does not come out")


def test_body_mesh_carries_the_full_arkit_channel_list(glb: Glb) -> None:
    """The body must still name all 52 channels, so the runtime can drive one morph set."""
    for mesh in glb.doc["meshes"]:
        names = mesh.get("extras", {}).get("targetNames", [])
        if len(names) == 52:
            assert list(names) == list(ARKIT_52), "the 52 targets are not the ARKit set in ARKit order"
            return
    pytest.fail("no 52-target mesh found")


# ------------------------------------------------------------------------------------------------ weights
def test_vertex_weights_sum_to_one(glb: Glb) -> None:
    checked = 0
    for mesh in glb.doc["meshes"]:
        for primitive in mesh["primitives"]:
            attrs = primitive["attributes"]
            if "WEIGHTS_0" not in attrs:
                continue
            weights = glb.accessor(attrs["WEIGHTS_0"]).astype(np.float64)
            if "WEIGHTS_1" in attrs:
                weights = np.hstack([weights, glb.accessor(attrs["WEIGHTS_1"]).astype(np.float64)])
            sums = weights.sum(axis=1)
            assert sums.min() > 0.999, (f"{mesh.get('name')}: {int((sums <= 0.999).sum())} vertices sum to "
                                        f"{sums.min():.5f}")
            assert sums.max() < 1.001, f"{mesh.get('name')}: max weight sum {sums.max():.5f}"
            checked += weights.shape[0]
    assert checked > 10000, f"only {checked} skinned vertices checked"


def test_weights_reference_valid_joints(glb: Glb) -> None:
    n_joints = len(glb.doc["skins"][0]["joints"])
    for mesh in glb.doc["meshes"]:
        for primitive in mesh["primitives"]:
            attrs = primitive["attributes"]
            if "JOINTS_0" not in attrs:
                continue
            joints = glb.accessor(attrs["JOINTS_0"])
            weights = glb.accessor(attrs["WEIGHTS_0"]).astype(np.float64)
            assert int(joints.max()) < n_joints
            assert (weights[joints >= n_joints] == 0).all()


def test_no_more_than_four_influences(glb: Glb) -> None:
    """The lane limits influences in Blender so the authored and exported weights are the same numbers."""
    for mesh in glb.doc["meshes"]:
        for primitive in mesh["primitives"]:
            assert "WEIGHTS_1" not in primitive["attributes"], \
                f"{mesh.get('name')} exported more than four influences"


# --------------------------------------------------------------------------------------------- measurements
def test_player_is_an_adult_sized_human(catalog: dict) -> None:
    m = catalog["measurements_m"]
    assert 1.55 <= m["height_m"] <= 2.05, m
    assert 0.30 <= m["shoulder_width_m"] <= 0.55, m
    assert 0.70 <= m["leg_length_m"] <= 1.05, m


def test_catalog_records_the_home_address_and_it_is_residential() -> None:
    """The player's address must be a real residential footprint in the buildings dataset."""
    pq = pytest.importorskip("pyarrow.parquet")
    parquet = REPO_ROOT / "data" / "processed" / "buildings" / "buildings_base.parquet"
    if not parquet.exists():
        pytest.skip("buildings_base.parquet not built")
    if not CATALOG.exists():
        pytest.skip("player catalog not built")
    with open(CATALOG, encoding="utf-8") as fh:
        person = json.load(fh)["character"]
    table = pq.read_table(parquet, columns=["bin", "bbl", "address", "bldg_class", "land_use", "floors"],
                          filters=[("bin", "==", person["home_bin"])])
    assert table.num_rows == 1, f"BIN {person['home_bin']} not found in buildings_base.parquet"
    row = {k: v[0] for k, v in table.to_pydict().items()}
    assert row["bbl"] == person["home_bbl"]
    assert row["address"].upper().replace("ST ", "").startswith("23-22 31")
    # PLUTO residential building classes: A one-family, B two-family, C walk-up, D elevator, R condo,
    # S mixed residential/commercial
    assert row["bldg_class"][0] in "ABCDRS", f"class {row['bldg_class']} is not residential"
    assert row["land_use"] in (1, 2, 3, 4), f"land use {row['land_use']} is not residential"


# ------------------------------------------------------------------------------------------------- NPCs
@pytest.fixture(scope="module")
def npcs() -> dict:
    if not NPC_MANIFEST.exists():
        pytest.skip(f"{NPC_MANIFEST} not built (run blender/character/npc_generator.py)")
    with open(NPC_MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


#: The pedestrian appearance contract, copied here from `docs/verification/traffic/REPORT.md` section 7 so
#: the test fails if either side drifts, rather than reading the same table the generator wrote.
PED_CONTRACT = (
    ("age_band", 4), ("stature", 6), ("body_mass", 6), ("skin_tone", 8),
    ("hair_style", 10), ("hair_colour", 8), ("top_garment", 10), ("top_colour", 12),
    ("bottom_garment", 8), ("bottom_colour", 12), ("footwear", 6), ("accessory", 10),
)
PED_APPEARANCES = 63_700_992_000


def test_variety_module_implements_the_traffic_contract() -> None:
    """The generator's own tables must be the twelve dimensions the pedestrian simulation publishes."""
    assert variety.PED_DIMENSIONS == PED_CONTRACT
    assert variety.distinguishable_appearances() == PED_APPEARANCES
    for name, levels in PED_CONTRACT:
        table = variety._TABLES[name]
        assert len(table) == levels, f"{name} table has {len(table)} entries, contract says {levels}"
        assert len({e["id"] for e in table}) == levels, f"{name} table has duplicate ids"


def test_variety_quantisation_accepts_both_encodings() -> None:
    """floor(v*levels) must invert bin centres and endpoint-inclusive spacing alike."""
    for _name, levels in PED_CONTRACT:
        for level in range(levels):
            assert variety.quantise((level + 0.5) / levels, levels) == level
            assert variety.quantise(level / (levels - 1), levels) == level
    assert variety.quantise(0.0, 4) == 0
    assert variety.quantise(1.0, 4) == 3
    for bad in (-0.01, 1.01, float("nan")):
        with pytest.raises(ValueError):
            variety.quantise(bad, 4)


def test_variety_decode_is_deterministic_and_total() -> None:
    """Every level of every dimension must decode to a buildable appearance."""
    for index, (name, levels) in enumerate(PED_CONTRACT):
        for level in range(levels):
            vector = [0.5] * 12
            vector[index] = (level + 0.5) / levels
            appearance = variety.decode(vector)
            assert appearance.level(name) == level
            macros = appearance.macros()
            assert 0.0 <= macros["gender"] <= 1.0
            assert 0.0 <= macros["age"] <= 1.0
            outfit = appearance.outfit()
            assert len(outfit) == len(set(outfit)), f"{name}={level} wears an item twice: {outfit}"
            bottoms = {e["item"] for e in variety.BOTTOM_GARMENTS}
            shoes = {e["item"] for e in variety.FOOTWEAR}
            assert len(set(outfit) & bottoms) == 1, f"{name}={level} wears {outfit}"
            assert len(set(outfit) & shoes) == 1, f"{name}={level} wears {outfit}"
            for item in appearance.colours():
                assert item in outfit, f"colour override for {item!r} which is not worn"
            assert 0.6 < appearance.gait()["rate"] < 1.3


def test_variety_spread_covers_every_level_in_twelve_draws() -> None:
    vectors = variety.spread_vectors(12)
    for index, (name, levels) in enumerate(PED_CONTRACT):
        seen = {variety.quantise(v[index], levels) for v in vectors}
        assert len(seen) == min(levels, 12), f"{name}: 12 draws covered {sorted(seen)}"
    assert len({v for v in vectors}) == 12, "spread_vectors repeated a whole vector"


def test_npc_manifest_publishes_the_contract(npcs: dict) -> None:
    contract = npcs["variety_contract"]
    assert [(d["name"], d["levels"]) for d in contract["dimensions"]] == list(PED_CONTRACT)
    assert contract["distinguishable_appearances"] == PED_APPEARANCES
    for name, levels in PED_CONTRACT:
        assert len(contract["tables"][name]) == levels


def test_wardrobe_covers_the_city(npcs: dict) -> None:
    items = npcs["wardrobe"]
    assert len(items) >= 40, f"{len(items)} wardrobe items"
    tags = {t for item in items for t in item["tags"]}
    for required in ("puffer", "hoodie", "suit", "hijab", "scrubs", "delivery", "hivis", "tourist",
                     "kids", "sneakers", "jeans", "jacket", "dress", "work", "shorts"):
        assert required in tags, f"no wardrobe item tagged {required!r}"
    ids = {item["id"] for item in items}
    for item in npcs["variety_contract"]["wardrobe_items_reachable"]:
        assert item in ids, f"the contract can select {item!r}, which is not in the wardrobe"


def test_generated_cast_exercises_every_contract_level(npcs: dict) -> None:
    """A cast that never wears half the wardrobe is not evidence that the wardrobe works."""
    vectors = [n["variety_vector"] for n in npcs["npcs"]]
    for index, (name, levels) in enumerate(PED_CONTRACT):
        seen = {min(int(v[index] * levels), levels - 1) for v in vectors}
        assert len(seen) == min(levels, len(vectors)), \
            f"{name}: {len(vectors)} NPCs cover only levels {sorted(seen)} of {levels}"


def test_npc_vectors_are_twelve_floats_that_decode_to_what_was_built(npcs: dict) -> None:
    for npc in npcs["npcs"]:
        vector = npc["variety_vector"]
        assert len(vector) == 12
        assert all(0.0 <= v <= 1.0 for v in vector)
        appearance = variety.decode(vector)
        assert list(appearance.levels) == npc["variety_levels"], f"{npc['id']} does not re-decode"
        assert appearance.resolve()["outfit"] == npc["resolved"]["outfit"]


def test_npcs_share_one_skeleton_and_the_same_clips(npcs: dict) -> None:
    clip_sets = {tuple(sorted(n["animations"])) for n in npcs["npcs"]}
    assert len(clip_sets) == 1, "NPCs do not share one animation set"
    clips = set(clip_sets.pop())
    for required in (*REQUIRED_CLIPS, *NPC_CLIPS):
        assert required in clips, f"NPC set is missing {required}"
    assert {n["bone_count"] for n in npcs["npcs"]} == {71}
    assert {n["blendshapes"] for n in npcs["npcs"]} == {52}


def test_stature_follows_the_simulations_own_height_formula() -> None:
    """`core/include/nycsim/peds/Variety.h::heightMetres` is the definition; the mesh must match it."""
    for stature in (0.0, 0.25, 0.5, 0.75, 1.0):
        adult = [0.5, stature] + [0.5] * 10
        child = [0.1, stature] + [0.5] * 10
        assert variety.contract_height_m(adult) == pytest.approx(1.50 + stature * 0.45)
        assert variety.contract_height_m(child) == pytest.approx((1.50 + stature * 0.45) * 0.72)
        assert variety.decode(adult).target_height_m == pytest.approx(1.50 + stature * 0.45)
    # 1.50 m at v=0 and 1.95 m at v=1 for an adult; the child band is 0.72 of that
    assert variety.contract_height_m([0.5, 0.0] + [0.5] * 10) == pytest.approx(1.50)
    assert variety.contract_height_m([0.5, 1.0] + [0.5] * 10) == pytest.approx(1.95)


def test_npc_statures_hit_the_metres_the_contract_asked_for(npcs: dict) -> None:
    """The stature dimension is specified in metres and solved for, so it must be delivered in metres."""
    for npc in npcs["npcs"]:
        stature = npc["stature"]
        target = stature["target_m"]
        assert abs(stature["probe_m"] - target) <= 0.010, (
            f"{npc['id']}: rest stature {stature['probe_m']:.3f} m against a target of {target:.3f} m")
        # the shipped measurement is taken in the idle pose, which is a little shorter than the rest pose
        posed = npc["measurements_m"]["height_m"]
        assert target - 0.07 <= posed <= target + 0.04, (
            f"{npc['id']}: posed height {posed:.3f} m against a target of {target:.3f} m")


def test_npc_heights_span_a_real_population(npcs: dict) -> None:
    heights = sorted(n["measurements_m"]["height_m"] for n in npcs["npcs"])
    assert heights[0] < 1.45, f"shortest NPC is {heights[0]:.2f} m - no children"
    assert heights[-1] > 1.80, f"tallest NPC is {heights[-1]:.2f} m"
    adults = sorted(n["measurements_m"]["height_m"] for n in npcs["npcs"]
                    if n["resolved"]["age_band"] != "child")
    assert adults[0] > 1.40, f"shortest adult is {adults[0]:.2f} m - shorter than any adult human"
    assert adults[-1] < 2.00, f"tallest adult is {adults[-1]:.2f} m - taller than any adult human"


# --------------------------------------------------------------------- CMU ASF/AMC parser (no Blender needed)
@pytest.fixture(scope="module")
def skeleton() -> asf_amc.Skeleton:
    path = MOCAP / "07.asf"
    if not path.exists():
        pytest.skip("CMU mocap not downloaded")
    return asf_amc.parse_asf(path)


def test_asf_parses_the_cmu_skeleton(skeleton: asf_amc.Skeleton) -> None:
    assert len(skeleton.bones) == 30
    assert skeleton.order[0] == "root"
    assert skeleton.bones["lfemur"].parent == "lhipjoint"
    assert skeleton.bones["ltibia"].dof == ("rx",)
    assert skeleton.angle_unit.lower().startswith("deg")
    assert skeleton.unit_to_m() == pytest.approx(2.54 / 100.0 / 0.45)
    for name in skeleton.order[1:]:
        assert skeleton.bones[name].length > 0.0
        assert abs(np.linalg.norm(skeleton.bones[name].direction) - 1.0) < 1e-9


def test_asf_rest_pose_is_a_standing_human(skeleton: asf_amc.Skeleton) -> None:
    rest = skeleton.rest_positions()
    scale = skeleton.unit_to_m()
    head = asf_amc.asf_to_blender(rest["head"]) * scale
    foot = asf_amc.asf_to_blender(rest["lfoot"]) * scale
    hand = asf_amc.asf_to_blender(rest["lwrist"]) * scale
    assert head.item(2) > 0.4, "head is not above the pelvis"
    assert foot.item(2) < -0.7, "foot is not below the pelvis"
    assert 1.4 < head.item(2) - foot.item(2) < 1.9, "implausible pelvis-to-crown-plus-leg span"
    assert hand.item(0) > 0.05, "the left hand is not on the left"


def test_amc_parses_and_fk_preserves_bone_lengths() -> None:
    asf = MOCAP / "07.asf"
    amc = MOCAP / "07_01.amc"
    if not (asf.exists() and amc.exists()):
        pytest.skip("CMU mocap not downloaded")
    skeleton = asf_amc.parse_asf(asf)
    frames = asf_amc.parse_amc(amc)
    assert len(frames) > 100
    assert "root" in frames[0] and len(frames[0]["root"]) == 6
    for index in (0, len(frames) // 2, len(frames) - 1):
        positions, _rot = skeleton.fk(frames[index])
        for name in skeleton.order[1:]:
            bone = skeleton.bones[name]
            parent = positions[bone.parent or "root"]
            length = float(np.linalg.norm(positions[name] - parent))
            assert length == pytest.approx(bone.length, rel=1e-6), f"{name} stretched on frame {index}"


def test_measured_clip_speeds_match_the_documented_assignment() -> None:
    """The walk/jog/run source choice is data-driven: re-measure it here."""
    expected = {"07_01": (1.2, 1.6), "16_35": (2.5, 3.1), "09_01": (3.3, 4.0)}
    for trial, (lo, hi) in expected.items():
        asf = MOCAP / f"{trial.split('_')[0]}.asf"
        amc = MOCAP / f"{trial}.amc"
        if not (asf.exists() and amc.exists()):
            pytest.skip("CMU mocap not downloaded")
        skeleton = asf_amc.parse_asf(asf)
        frames = asf_amc.parse_amc(amc)
        speed = asf_amc.root_speed_mps(skeleton, frames)
        assert lo <= speed <= hi, f"{trial} measures {speed:.2f} m/s, expected {lo}-{hi}"


def test_euler_matrix_matches_the_blender_convention() -> None:
    """``euler_to_matrix(..., 'XYZ')`` must equal Rz @ Ry @ Rx, the convention Blender's Euler uses."""
    angles = (0.3, -0.7, 1.1)
    m = asf_amc.euler_to_matrix(angles, "XYZ")
    cx, sx = math.cos(angles[0]), math.sin(angles[0])
    cy, sy = math.cos(angles[1]), math.sin(angles[1])
    cz, sz = math.cos(angles[2]), math.sin(angles[2])
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    assert np.allclose(m, rz @ ry @ rx)
    assert np.allclose(m @ m.T, np.eye(3), atol=1e-12)


def test_asf_to_blender_is_a_right_handed_yup_to_zup_swap() -> None:
    v = np.array([1.0, 2.0, 3.0])
    assert np.allclose(asf_amc.asf_to_blender(v), [1.0, -3.0, 2.0])
    basis = asf_amc.BASIS_ASF_TO_BLENDER
    assert np.allclose(basis @ v, asf_amc.asf_to_blender(v))
    assert np.linalg.det(basis) == pytest.approx(1.0)


# ---------------------------------------------------------------------------------- verification artefacts
@pytest.mark.parametrize("name", ["face_closeup.png", "full_body.png", "walk_strip.png", "bend_test.png",
                                  "npc_lineup.png", "REPORT.md"])
def test_verification_artefacts_exist(name: str) -> None:
    path = REPO_ROOT / "docs" / "verification" / "character" / name
    assert path.exists(), f"{path} missing"
    assert path.stat().st_size > 2000, f"{path} is suspiciously small"


# --------------------------------------------------------------------------- wardrobe table (J53)
def test_the_generated_wardrobe_table_agrees_with_the_variety_contract():
    """``GameplayPedWardrobe.h`` is derived from ``npc_variety.json``; a stale header would dress
    the crowd from a cast that no longer exists."""
    import subprocess
    import sys as _sys

    repo = Path(__file__).resolve().parents[1]
    if not (repo / "blender_out" / "character" / "npc_variety.json").is_file():
        pytest.skip("npc_variety.json not generated in this checkout")
    got = subprocess.run([_sys.executable, str(repo / "unreal" / "tools" / "gen_ped_wardrobe.py"),
                          "--check"], capture_output=True, text=True)
    assert got.returncode == 0, (
        "GameplayPedWardrobe.h is out of date; run unreal/tools/gen_ped_wardrobe.py\n" + got.stderr)


def test_a_work_vest_is_not_warm_clothing():
    """The rule this table encodes, checked rather than assumed: a hi-vis or delivery vest goes over
    whatever the wearer already has on, so it says nothing about the temperature."""
    import json as _json
    import sys as _sys

    repo = Path(__file__).resolve().parents[1]
    variety = repo / "blender_out" / "character" / "npc_variety.json"
    if not variety.is_file():
        pytest.skip("npc_variety.json not generated in this checkout")
    _sys.path.insert(0, str(repo / "unreal" / "tools"))
    import gen_ped_wardrobe as gw

    doc = _json.loads(variety.read_text())
    info = gw.classify(doc)
    wardrobe = {g["id"]: g for g in doc["wardrobe"]}
    for row in info["detail"]:
        for gid in row["outerwear"]:
            tags = wardrobe[gid].get("tags") or []
            assert not any(t in gw.WORK_LAYERS for t in tags), (
                f"{row['id']} counts as warm because of {gid}, which is a work layer")
        assert not (row["warm"] and row["summer"]), f"{row['id']} is both warm and summer dress"
    assert info["count"] == len(info["detail"])
    assert info["warm"], "no body in the cast wears a coat, a puffer or a jacket"


def test_the_cold_weather_draw_is_wired_into_the_simulation():
    """The flag existed and nothing read it (J53).  This checks the link is there in the source the
    adapter actually compiles, not only in the generated table beside it."""
    repo = Path(__file__).resolve().parents[1]
    src = (repo / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime" / "Private" / "CoreAdapter"
           / "GameplayPedSim.cpp").read_text()
    assert "GameplayPedWardrobe.h" in src, "the adapter does not include the wardrobe table"
    assert "kPedWarmArchetypes" in src and "kPedSummerArchetypes" in src, \
        "assignAppearance does not consult the wardrobe table"
    assert "pickArchetype(" in src, "the body is still drawn uniformly over every archetype"
