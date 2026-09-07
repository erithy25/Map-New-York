"""The rig, read out of the file that ships rather than out of the code that wrote it.

``fusion_hybrid.glb`` shipped for months with ``skins: 0`` and ``animations: 0`` while its catalogue
entry reported ``contract_profile: "full"`` and ``missing_nodes: []``.  Neither statement was a lie:
``rig.finalise`` checked that a *node* called ``Wheel_FL`` existed, and one did.  Chaos Vehicles
needs a *bone* called ``Wheel_FL`` on a ``USkeletalMesh``, and without a skin Unreal's glTF importer
produces a ``UStaticMesh`` -- so the player vehicle would have been an invisible physics body with
nothing to steer.  A correct measurement of something other than the thing it stands for is the most
expensive failure mode in this project, and it has now happened often enough to be worth a module.

So everything here reads the exported binary.  Nothing imports the build code.
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VEHICLES = REPO_ROOT / "blender_out" / "vehicles"
CATALOG = VEHICLES / "catalog"
CONTRACT_H = (REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime" / "Public" / "Vehicle"
              / "NYCVehicleContract.h")
CONTRACT_CPP = (REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime" / "Private" / "Vehicle"
                / "NYCVehicleContract.cpp")

#: The player's car. The fleet is checked separately and more loosely: a horse-drawn carriage has no
#: steering wheel, and the contract profiles say so.
PLAYER_ID = "fusion_hybrid"


def _glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    off, js, bins = 12, None, b""
    while off < len(data):
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        if ctype == b"JSON":
            js = json.loads(data[off + 8:off + 8 + clen])
        elif ctype == b"BIN\x00":
            bins = data[off + 8:off + 8 + clen]
        off += 8 + clen + (-clen % 4)
    assert js is not None, f"{path} has no JSON chunk"
    return js, bins


def _accessor(js: dict, bins: bytes, index: int) -> np.ndarray:
    a = js["accessors"][index]
    bv = js["bufferViews"][a["bufferView"]]
    counts = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    dtypes = {5120: "<i1", 5121: "<u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
    n = counts[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(bins, dtype=np.dtype(dtypes[a["componentType"]]),
                         count=a["count"] * n, offset=off).reshape(a["count"], n)


@pytest.fixture(scope="module")
def player():
    path = VEHICLES / f"{PLAYER_ID}.glb"
    if not path.is_file():
        pytest.skip(f"{path} has not been built")
    return _glb(path)


def _contract_names(namespace: str) -> dict[str, str]:
    if not CONTRACT_H.is_file():
        pytest.skip("NYCVehicleContract.h is not present")
    text = CONTRACT_H.read_text(encoding="utf-8", errors="replace")
    start = text.find(f"namespace {namespace}")
    if start < 0:
        return {}
    depth, i = 0, text.find("{", start)
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                body = text[i + 1:j]
                return dict(re.findall(
                    r'inline\s+const\s+TCHAR\*\s+const\s+(\w+)\s*=\s*TEXT\("([^"]+)"\)\s*;', body))
    return {}


def _required(fn: str) -> set[str]:
    names = _contract_names("NYCVehicleBones")
    text = CONTRACT_CPP.read_text(encoding="utf-8", errors="replace")
    body = re.search(rf"{fn}\(\)[^{{]*\{{(.*?)\n\}}", text, re.S)
    assert body is not None, f"NYCVehicleContract.cpp has no {fn}() body"
    return {names[i] for i in re.findall(r"NYCVehicleBones::(\w+)", body.group(1)) if i in names}


def _joints(js: dict) -> dict[str, int]:
    skins = js.get("skins", [])
    if not skins:
        return {}
    return {js["nodes"][j].get("name", f"node{j}"): j for j in skins[0]["joints"]}


def _world(js: dict) -> dict[int, np.ndarray]:
    def local(n):
        if "matrix" in n:
            return np.asarray(n["matrix"], dtype=np.float64).reshape(4, 4).T
        m = np.eye(4)
        x, y, z, w = n.get("rotation", [0.0, 0.0, 0.0, 1.0])
        m[:3, :3] = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        m[:3, :3] = m[:3, :3] @ np.diag(n.get("scale", [1.0, 1.0, 1.0]))
        m[:3, 3] = n.get("translation", [0.0, 0.0, 0.0])
        return m

    out: dict[int, np.ndarray] = {}

    def walk(i: int, parent: np.ndarray) -> None:
        m = parent @ local(js["nodes"][i])
        out[i] = m
        for c in js["nodes"][i].get("children", []):
            walk(c, m)

    kids = {c for n in js["nodes"] for c in n.get("children", [])}
    for r in sorted(set(range(len(js["nodes"]))) - kids):
        walk(r, np.eye(4))
    return out


# --------------------------------------------------------------------------- the skin


def test_the_player_vehicle_is_skinned_at_all(player):
    """Without a skin Unreal makes a StaticMesh and the pawn has no wheels."""
    js, _ = player
    skins = js.get("skins", [])
    assert len(skins) == 1, (
        f"{PLAYER_ID}.glb has {len(skins)} skins. Chaos Vehicles needs exactly one USkeletalMesh; "
        f"with none the glTF importer produces a UStaticMesh and AWheeledVehiclePawn has no "
        f"skeleton to find Wheel_FL on.")
    assert skins[0].get("joints"), "the skin has no joints"


def test_every_bone_the_engine_requires_is_in_the_skin(player):
    """``RequiredBones()`` read out of the engine source, looked up in the shipped file."""
    js, _ = player
    joints = set(_joints(js))
    missing = sorted(_required("RequiredBones") - joints)
    assert not missing, (
        f"{PLAYER_ID}.glb is missing required bone(s) {missing}. Present: {sorted(joints)}")


def test_every_socket_the_engine_looks_up_is_a_bone(player):
    """glTF has no socket concept and does not need one.

    ``USkeletalMeshComponent::DoesSocketExist`` and ``GetSocketTransform`` resolve bones as well as
    sockets, and every consumer in this project uses exactly those two calls, so a non-deforming leaf
    bone is a socket that survives the glTF round trip.
    """
    js, _ = player
    joints = set(_joints(js))
    names = _contract_names("NYCVehicleBones")
    sockets = {v for k, v in names.items() if v.startswith("SKT_")}
    assert sockets, "the contract declares no SKT_ names"
    missing = sorted(sockets - joints)
    assert not missing, (
        f"{len(missing)} socket(s) the engine looks up are neither a bone nor a socket on the mesh: "
        f"{missing}")


def test_every_vertex_is_weighted_to_exactly_one_bone(player):
    """Rigid skinning: every part is its own object on its own pivot, so a vertex belongs to one bone.

    A vertex whose weights do not sum to one is a vertex that collapses towards the origin when the
    skeleton is posed -- the classic symptom of a mesh exported with a skin it was never bound to.
    """
    js, bins = player
    checked = 0
    for mesh in js["meshes"]:
        for prim in mesh["primitives"]:
            attrs = prim["attributes"]
            if "WEIGHTS_0" not in attrs:
                continue
            w = _accessor(js, bins, attrs["WEIGHTS_0"]).astype(np.float64)
            sums = w.sum(axis=1)
            assert np.allclose(sums, 1.0, atol=1e-3), (
                f"{mesh.get('name')}: weights sum to between {sums.min():.4f} and {sums.max():.4f}")
            influences = (w > 1e-6).sum(axis=1)
            assert influences.max() <= 4, f"{mesh.get('name')}: up to {influences.max()} influences"
            checked += 1
    assert checked > 0, "no primitive in the file carries skin weights"


def test_every_rendered_primitive_is_skinned(player):
    """A primitive without JOINTS_0 is geometry the skeleton cannot move.

    Collision hulls are exempt: ``UCX_`` meshes are consumed by the importer and never rendered.
    """
    js, _ = player
    by_mesh: dict[int, str] = {}
    for n in js["nodes"]:
        if "mesh" in n:
            by_mesh.setdefault(n["mesh"], n.get("name", ""))
    unskinned = []
    for i, mesh in enumerate(js["meshes"]):
        name = by_mesh.get(i, mesh.get("name", f"mesh{i}"))
        if name.startswith("UCX_"):
            continue
        for prim in mesh["primitives"]:
            if "JOINTS_0" not in prim["attributes"]:
                unskinned.append(name)
                break
    assert not unskinned, f"{len(unskinned)} unskinned mesh(es): {sorted(set(unskinned))[:10]}"


# --------------------------------------------------------------------------- the rest pose


def test_the_pivot_bones_stand_where_the_catalogue_says_the_pivots_are(player):
    """The bone is the pivot now; the catalogue's ``wheel_pivots`` is the independent record of it."""
    js, _ = player
    entry = json.loads((CATALOG / f"{PLAYER_ID}.json").read_text())
    world = _world(js)
    joints = _joints(js)
    for name, pivot in entry["wheel_pivots"].items():
        assert name in joints, f"{name} is not a bone"
        t = world[joints[name]][:3, 3]
        got = np.array([t[0], -t[2], t[1]])          # glTF Y-up -> vehicle frame
        assert np.allclose(got, np.asarray(pivot, dtype=np.float64), atol=1e-3), (
            f"bone {name} is at {got}, the catalogue records the pivot at {pivot}")


def test_the_ordinary_bones_are_built_in_the_vehicle_frame(player):
    """The design that removes the Blender-roll -> glTF -> Unreal conversion from the problem.

    Every bone that has no reason to differ is built with its local frame equal to the vehicle's own,
    which is the identity rotation, so its glTF node carries a translation and nothing else and its
    Unreal reference-pose axes are the component's. Read against ``NYCVehicleContract.h``'s table
    that satisfies the wheels, the doors, the bonnet and boot, the wipers, the windows and the
    mirrors at once. The three bones the contract turns about local X are the exceptions.
    """
    js, _ = player
    world = _world(js)
    joints = _joints(js)
    exceptions = {"SteeringWheel", "GearSelector", "SKT_Screen", "SKT_Cluster",
                  "Needle_Speed", "Needle_RPM", "Needle_Fuel", "Needle_Temp"}
    # glTF is Y-up: the vehicle frame's X, Y, Z appear as (1,0,0), (0,0,-1), (0,1,0).
    want = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]]).T
    off = []
    for name, index in sorted(joints.items()):
        if name in exceptions:
            continue
        rot = world[index][:3, :3]
        rot = rot / np.linalg.norm(rot, axis=0, keepdims=True)
        if not np.allclose(rot, want, atol=1e-3):
            off.append(name)
    assert not off, f"{len(off)} bone(s) are not in the vehicle frame: {off}"


def test_the_steering_bone_turns_about_the_real_column(player):
    """The contract puts the steering wheel's rotation on its bone's local X, so that is the column."""
    js, _ = player
    world = _world(js)
    joints = _joints(js)
    assert "SteeringWheel" in joints
    axis = world[joints["SteeringWheel"]][:3, 0]
    axis = axis / np.linalg.norm(axis)
    assert axis[0] > 0.1, f"the column's local X {axis} does not point forward"
    assert axis[1] < -0.1, f"the column's local X {axis} does not rake downward"
    tilt = np.degrees(np.arctan2(-axis[1], axis[0]))
    assert 15.0 <= tilt <= 35.0, f"a car's column rakes 20-25 degrees; this one is {tilt:.1f}"


def test_all_three_lods_share_one_skeleton():
    """Different skeletons across LODs give three USkeleton assets and a chain that will not bind."""
    base = _joints(_glb(VEHICLES / f"{PLAYER_ID}.glb")[0]) if (VEHICLES / f"{PLAYER_ID}.glb").is_file() else None
    if base is None:
        pytest.skip("the player vehicle has not been built")
    for level in (1, 2):
        path = VEHICLES / f"{PLAYER_ID}_LOD{level}.glb"
        if not path.is_file():
            continue
        js, _ = _glb(path)
        joints = _joints(js)
        assert set(joints) == set(base), (
            f"LOD{level} has a different skeleton: "
            f"missing {sorted(set(base) - set(joints))}, extra {sorted(set(joints) - set(base))}")


def test_the_catalogue_reports_the_rig_that_shipped(player):
    """The entry that once said ``full`` for an unrigged file now has to name what it rigged."""
    entry = json.loads((CATALOG / f"{PLAYER_ID}.json").read_text())
    rig = entry.get("rig")
    assert rig, "the catalogue entry carries no rig record"
    js, _ = player
    assert set(rig["bones"]) == set(_joints(js)), (
        "the catalogue's bone list disagrees with the skin's joints: "
        f"{sorted(set(rig['bones']) ^ set(_joints(js)))}")
    assert rig["skinning"]["skinned"] > 0
    assert rig["socket_bones"], "no socket bones recorded"
