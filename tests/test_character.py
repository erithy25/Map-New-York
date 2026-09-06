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
        acc = self.doc["accessors"][index]
        view = self.doc["bufferViews"][acc["bufferView"]]
        ncomp = self._COUNT[acc["type"]]
        dtype = np.dtype(self._COMPONENT[acc["componentType"]])
        offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride")
        if stride and stride != ncomp * dtype.itemsize:
            rows = [np.frombuffer(self.blob, dtype=dtype, count=ncomp, offset=offset + i * stride)
                    for i in range(acc["count"])]
            return np.vstack(rows)
        flat = np.frombuffer(self.blob, dtype=dtype, count=acc["count"] * ncomp, offset=offset)
        return flat.reshape(acc["count"], ncomp)


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


def test_blendshapes_actually_move_vertices(glb: Glb) -> None:
    """Every target must displace at least one vertex - an all-zero morph is a silent failure."""
    for mesh in glb.doc["meshes"]:
        names = mesh.get("extras", {}).get("targetNames", [])
        if len(names) != 52:
            continue
        for primitive in mesh["primitives"]:
            for name, target in zip(names, primitive["targets"]):
                delta = glb.accessor(target["POSITION"])
                assert float(np.abs(delta).max()) > 1e-5, f"blendshape {name} moves nothing"
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


def test_npc_variety_contract_is_twelve_dimensional(npcs: dict) -> None:
    contract = npcs["variety_contract"]
    assert len(contract["dimensions"]) == 12
    assert contract["dimensions"] == ["body_preset", "skin_tone", "hair", "top", "bottom", "shoes",
                                      "outerwear", "bag", "hat", "glasses", "height_scale", "walk_style"]
    assert len(contract["tables"]["body_preset"]) == 24
    assert len(contract["tables"]["hair"]) == 12


def test_wardrobe_has_forty_items(npcs: dict) -> None:
    assert len(npcs["wardrobe"]) == 40, f"{len(npcs['wardrobe'])} wardrobe items"
    tags = {t for item in npcs["wardrobe"] for t in item["tags"]}
    for required in ("puffer", "hoodie", "suit", "hijab", "scrubs", "delivery", "hivis", "tourist",
                     "kids", "sneakers", "jeans"):
        assert required in tags, f"no wardrobe item tagged {required!r}"


def test_all_24_base_bodies_are_generated(npcs: dict) -> None:
    bodies = {n["resolved"]["body_preset"] for n in npcs["npcs"]}
    assert len(bodies) == 24, f"{len(bodies)} distinct base bodies"


def test_npcs_share_one_skeleton_and_the_same_clips(npcs: dict) -> None:
    clip_sets = {tuple(sorted(n["animations"])) for n in npcs["npcs"]}
    assert len(clip_sets) == 1, "NPCs do not share one animation set"
    clips = set(clip_sets.pop())
    for required in (*REQUIRED_CLIPS, *NPC_CLIPS):
        assert required in clips, f"NPC set is missing {required}"
    assert {n["bone_count"] for n in npcs["npcs"]} == {71}
    assert {n["blendshapes"] for n in npcs["npcs"]} == {52}


def test_npc_variety_vectors_are_twelve_bytes(npcs: dict) -> None:
    for npc in npcs["npcs"]:
        assert len(npc["variety_bytes"]) == 12
        assert all(0 <= b <= 255 for b in npc["variety_bytes"])


def test_npc_heights_span_a_real_population(npcs: dict) -> None:
    heights = sorted(n["measurements_m"]["height_m"] for n in npcs["npcs"])
    assert heights[0] < 1.60, f"shortest NPC is {heights[0]:.2f} m - no children or short adults"
    assert heights[-1] > 1.80, f"tallest NPC is {heights[-1]:.2f} m"


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
