"""The Blender vehicle contract and the engine's vehicle contract must agree.

Three independent copies of the vehicle contract exist:

===========================  ===================================================================
Blender authority            ``blender/vehicles/vlib/rig.py`` -- ``CONTRACT_FULL``,
                             ``MATERIAL_SLOTS_FULL``, ``LIGHT_SLOTS_FULL``, ``PIVOT_CONVENTION``
Test authority               ``tests/test_vehicles.py::_full_contract`` -- a hardcoded third copy
Engine authority             ``unreal/.../Public/Vehicle/NYCVehicleContract.h`` + the list
                             functions in ``NYCVehicleContract.cpp``
===========================  ===================================================================

``rig.finalise()`` computes ``missing_nodes`` from the first; ``test_vehicles.py`` checks the first
against the second.  **Nothing had ever compared either to the third**, which is how
``blender_out/vehicles/catalog/fusion_hybrid.json`` came to report ``contract_profile: "full"`` and
``missing_nodes: []`` for a file that Unreal cannot import as a vehicle at all.  That is the same
failure mode as six others in ``docs/DEVIATIONS.md``: a correct measurement of something other than
the thing it stands for.

This module is the missing comparison.  It parses the engine headers as text -- there is no compiler
here, and the point is precisely to check the document that the code cannot -- and it is expected to
fail while the Blender side still ships the old names.  The failures are the deliverable; each one
is a name that would silently do nothing in the engine.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
UE_VEHICLE = REPO_ROOT / "unreal" / "NYCSim" / "Source" / "NYCSimRuntime"
CONTRACT_H = UE_VEHICLE / "Public" / "Vehicle" / "NYCVehicleContract.h"
CONTRACT_CPP = UE_VEHICLE / "Private" / "Vehicle" / "NYCVehicleContract.cpp"
MOVEMENT_CPP = UE_VEHICLE / "Private" / "Vehicle" / "NYCVehicleMovementComponent.cpp"
RIG_PY = REPO_ROOT / "blender" / "vehicles" / "vlib" / "rig.py"
SKEL_PY = REPO_ROOT / "blender" / "vehicles" / "vlib" / "skel.py"
CONTRACT_PY = REPO_ROOT / "blender" / "vehicles" / "vlib" / "contract.py"

_NAME_RE = re.compile(r'inline\s+const\s+TCHAR\*\s+const\s+(\w+)\s*=\s*TEXT\("([^"]+)"\)\s*;')
_PY_TUPLE_RE = re.compile(r"^(\w+)\s*=\s*\(", re.M)


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"{path.relative_to(REPO_ROOT)} is not present")
    return path.read_text(encoding="utf-8", errors="replace")


def namespace_names(text: str, namespace: str) -> dict[str, str]:
    """``{C++ identifier: string literal}`` for one ``namespace NYCVehicleX { ... }`` block."""
    start = text.find(f"namespace {namespace}")
    if start < 0:
        return {}
    depth, i, body_start = 0, text.find("{", start), None
    if i < 0:
        return {}
    body_start = i + 1
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return dict(_NAME_RE.findall(text[body_start:j]))
    return {}


def py_tuple(text: str, name: str) -> tuple[str, ...]:
    """The string literals of a top-level ``NAME = ( ... )`` tuple in a Python source file."""
    m = re.search(rf"^{re.escape(name)}\s*=\s*\(", text, re.M)
    if m is None:
        return ()
    depth, start = 0, m.end() - 1
    for j in range(start, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return tuple(re.findall(r'"([^"]+)"', text[start:j]))
    return ()


# --------------------------------------------------------------------------- the pivot


def test_the_engine_places_the_centre_of_mass_from_the_pivot_the_exporter_actually_uses():
    """``CenterOfMassOverride`` must be measured from the origin the Blender export contract defines.

    The exporter's ``PIVOT_CONVENTION`` is "ground under rear-axle centre";
    ``tests/test_vehicles.py::test_origin_is_ground_under_rear_axle`` enforces it, and
    ``fusion_hybrid.glb`` honours it (``Wheel_RL/RR`` at x = 0).  Measured from the rear axle the
    longitudinal CoG is ``frontMassShare * wheelbase``.  The engine had
    ``(frontMassShare - 0.5) * wheelbase``, which is the answer for an origin at the wheelbase
    midpoint -- 1.425 m too far back, level with the rear axle on a 58 %-front-weighted car.
    """
    text = _read(RIG_PY) + "\n" + _read(CONTRACT_PY)
    pivot = re.search(r'PIVOT_CONVENTION\s*=\s*"([^"]+)"', text)
    assert pivot is not None, "neither rig.py nor vlib/contract.py declares PIVOT_CONVENTION"
    assert "rear-axle" in pivot.group(1), (
        f"the exporter's pivot convention changed to {pivot.group(1)!r}; the engine's "
        f"CenterOfMassOverride in {MOVEMENT_CPP.name} is derived from the rear axle and must change with it")

    cpp = _read(MOVEMENT_CPP)
    expr = re.search(r"CenterOfMassOverride\s*=\s*\n?\s*FVector\(([^;]+)\);", cpp)
    assert expr is not None, "CenterOfMassOverride is no longer assigned from an FVector literal"
    longitudinal = expr.group(1).split(",")[0].strip()
    assert "0.5f" not in longitudinal, (
        f"{MOVEMENT_CPP.name} computes the longitudinal centre of mass as {longitudinal!r}. "
        f"Subtracting half a wheelbase measures from the wheelbase midpoint, but the mesh origin is "
        f"the rear-axle centre ({pivot.group(1)}), so this places the CoG half a wheelbase too far back.")
    assert re.search(r"S\.frontMassShare\s*\*\s*WheelbaseCm", longitudinal), (
        f"expected the longitudinal centre of mass to be frontMassShare * wheelbase from the rear "
        f"axle, found {longitudinal!r}")


# --------------------------------------------------------------------------- names


def test_every_bone_the_engine_requires_is_a_name_the_exporter_writes():
    """``RequiredBones()`` names must all be nodes the Blender contract emits.

    A bone the engine looks up and the exporter never writes is a component that silently does
    nothing: ``UNYCVehicleMovementComponent`` cannot find a wheel, ``UNYCVehicleDashboardComponent``
    cannot find a needle.
    """
    h, cpp, rig = _read(CONTRACT_H), _read(CONTRACT_CPP), _read(RIG_PY)
    bones = namespace_names(h, "NYCVehicleBones")
    assert bones, "NYCVehicleContract.h declares no NYCVehicleBones names"
    body = re.search(r"RequiredBones\(\)[^{]*\{(.*?)\n\}", cpp, re.S)
    assert body is not None, "NYCVehicleContract.cpp has no RequiredBones() body"
    required = {bones[i] for i in re.findall(r"NYCVehicleBones::(\w+)", body.group(1)) if i in bones}
    assert required, "RequiredBones() names no bones"
    emitted = (set(py_tuple(rig, "CONTRACT_FULL")) | set(_contract_tuple("CONTRACT_FULL"))
               | set(_contract_tuple("PART_NODES_FULL")))
    assert emitted, "neither rig.py nor vlib/contract.py declares the node contract"
    missing = sorted(required - emitted)
    assert not missing, (
        f"{len(missing)} bone(s) the engine requires are never written by the Blender exporter: "
        f"{missing}. Engine: {CONTRACT_CPP.relative_to(REPO_ROOT)}::RequiredBones(). "
        f"Exporter: {RIG_PY.relative_to(REPO_ROOT)}::CONTRACT_FULL.")


def test_every_light_slot_the_engine_drives_is_a_material_slot_the_exporter_writes():
    """``LightSlots()`` names must all exist as exporter material slots.

    ``UNYCVehicleLightsComponent`` finds its lamps by material-slot name.  A name only the engine
    knows is a lamp that never lights: indicators, brake lights and headlamps all fail this way.
    """
    h, cpp, rig = _read(CONTRACT_H), _read(CONTRACT_CPP), _read(RIG_PY)
    slots = namespace_names(h, "NYCVehicleSlots")
    assert slots, "NYCVehicleContract.h declares no NYCVehicleSlots names"
    body = re.search(r"LightSlots\(\)[^{]*\{(.*?)\n\}", cpp, re.S)
    assert body is not None, "NYCVehicleContract.cpp has no LightSlots() body"
    required = {slots[i] for i in re.findall(r"NYCVehicleSlots::(\w+)", body.group(1)) if i in slots}
    assert required, "LightSlots() names no slots"
    emitted = (set(py_tuple(rig, "MATERIAL_SLOTS_FULL")) | set(py_tuple(rig, "LIGHT_SLOTS_FULL"))
               | set(_contract_tuple("MATERIAL_SLOTS_FULL")) | set(_contract_tuple("LIGHT_SLOTS_FULL")))
    assert emitted, "neither rig.py nor vlib/contract.py declares the material slots"
    missing = sorted(required - emitted)
    assert not missing, (
        f"{len(missing)} lamp slot(s) the engine drives are never written by the Blender exporter: "
        f"{missing}. Engine: {CONTRACT_CPP.relative_to(REPO_ROOT)}::LightSlots(). "
        f"Exporter: {RIG_PY.relative_to(REPO_ROOT)}::LIGHT_SLOTS_FULL.")


def _optional_bones() -> set[str]:
    """The bone names ``OptionalBones()`` lists, resolved through ``NYCVehicleBones``."""
    h, cpp = _read(CONTRACT_H), _read(CONTRACT_CPP)
    bones = namespace_names(h, "NYCVehicleBones")
    assert bones, "NYCVehicleContract.h declares no NYCVehicleBones names"
    body = re.search(r"OptionalBones\(\)[^{]*\{(.*?)\n\}", cpp, re.S)
    assert body is not None, "NYCVehicleContract.cpp has no OptionalBones() body"
    optional = {bones[i] for i in re.findall(r"NYCVehicleBones::(\w+)", body.group(1)) if i in bones}
    assert optional, "OptionalBones() names no bones"
    return optional


def test_every_optional_bone_the_engine_looks_up_is_a_name_the_exporter_writes():
    """``OptionalBones()`` names the engine will look up on an imported mesh.

    A missing optional bone is not an import failure, which is exactly why it survives unnoticed:
    ``UNYCVehicleDashboardComponent`` asks for ``Needle_Speed`` every frame, gets ``INDEX_NONE``, and
    the speedometer needle simply never moves.

    **What this compares, and what it used to compare.** The exporter's *object* names and its *bone*
    names are not the same list -- ``skel.BONE_OF_OBJECT`` renames four of them on purpose, because
    the engine looks up ``Door_Hood`` where the Blender build has always written ``Hood`` -- and this
    test used to read the object tuples. So it reported ``Door_Hood`` missing while every exported
    rig had that exact bone, and it would equally have missed a bone that the map dropped. It reads
    the map now, which is the authority for what the rig actually writes: the same class of mistake
    as the one the module exists to catch, made inside the check itself.
    """
    missing = sorted(_optional_bones() - set(_bone_names()))
    assert not missing, (
        f"{len(missing)} optional bone(s) the engine looks up are never written by the Blender "
        f"exporter: {missing}. Engine: {CONTRACT_CPP.relative_to(REPO_ROOT)}::OptionalBones(). "
        f"Exporter: {SKEL_PY.relative_to(REPO_ROOT)}::BONE_OF_OBJECT.")


def test_every_needle_the_engine_drives_has_a_gauge_face_and_the_sweep_the_engine_uses():
    """A needle built for the wrong sweep is a gauge that reads wrong, which no other test sees.

    ``vlib/contract.py`` decides where each needle's rest peg goes -- half its sweep back from twelve
    o'clock -- so those four numbers have to be the engine's own. They are read out of
    ``NYCVehicleDashboardComponent.h``'s defaults here rather than trusted.
    """
    dash_h = _read(UE_VEHICLE / "Public" / "Vehicle" / "NYCVehicleDashboardComponent.h")
    engine = {}
    for prop, slot in (("SpeedoSweepDeg", "GAUGE_SPEED"), ("TachoSweepDeg", "GAUGE_RPM"),
                       ("SmallGaugeSweepDeg", "GAUGE_FUEL")):
        m = re.search(rf"\b{prop}\s*=\s*([0-9.]+)f?\s*;", dash_h)
        assert m is not None, f"{prop} has no default in NYCVehicleDashboardComponent.h"
        engine[slot] = float(m.group(1))
    engine["GAUGE_TEMP"] = engine["GAUGE_FUEL"]      # one small-gauge sweep drives both
    ours = _contract_mapping("GAUGE_SWEEP_DEG")
    assert {k: float(v) for k, v in ours.items()} == engine, (
        f"gauge sweeps disagree: exporter {ours}, engine {engine}. "
        f"The rest peg is half the sweep, so a mismatch puts every needle's zero in the wrong place.")

    # and every needle the engine drives must have a face to sweep over
    gauges = _contract_mapping("GAUGE_OF_NEEDLE")
    needles = {b for b in _optional_bones() if b.startswith("Needle_")}
    assert needles <= set(gauges), f"needles with no gauge face declared: {sorted(needles - set(gauges))}"
    slots = set(py_tuple(_read(RIG_PY), "MATERIAL_SLOTS_FULL")) | set(_contract_tuple("MATERIAL_SLOTS_FULL"))
    missing = sorted(set(gauges.values()) - slots)
    assert not missing, f"gauge faces named by GAUGE_OF_NEEDLE that no material slot writes: {missing}"


def test_every_instrument_slot_the_engine_drives_is_a_material_slot_the_exporter_writes():
    """``InstrumentSlots()`` names five surfaces the dashboard component writes to.

    ``UNYCVehicleDashboardComponent`` sets ``GaugeValue`` on ``GAUGE_SPEED`` / ``GAUGE_RPM`` /
    ``GAUGE_FUEL`` and renders to ``SCREEN_CENTER`` / ``SCREEN_CLUSTER``. The exporter had three of
    the five; the cluster's own strip display was piano-black trim and there was no fuel gauge face
    at all, so two of the dashboard's five outputs went nowhere.
    """
    h, cpp, rig = _read(CONTRACT_H), _read(CONTRACT_CPP), _read(RIG_PY)
    slots = namespace_names(h, "NYCVehicleSlots")
    body = re.search(r"InstrumentSlots\(\)[^{]*\{(.*?)\n\}", cpp, re.S)
    assert body is not None, "NYCVehicleContract.cpp has no InstrumentSlots() body"
    required = {slots[i] for i in re.findall(r"NYCVehicleSlots::(\w+)", body.group(1)) if i in slots}
    assert required, "InstrumentSlots() names no slots"
    emitted = set(py_tuple(rig, "MATERIAL_SLOTS_FULL")) | set(_contract_tuple("MATERIAL_SLOTS_FULL"))
    missing = sorted(required - emitted)
    assert not missing, (
        f"{len(missing)} instrument slot(s) the engine drives are never written by the Blender "
        f"exporter: {missing}.")


_PY_DICT_RE = re.compile(r'"([^"]+)"\s*:\s*("([^"]*)"|[0-9.]+)')


def _contract_mapping(name: str) -> dict[str, str]:
    """A top-level ``NAME = { "a": "b", ... }`` mapping in ``vlib/contract.py``, read as text."""
    text = _read(CONTRACT_PY)
    m = re.search(rf"^{re.escape(name)}\s*=\s*\{{", text, re.M)
    if m is None:
        return {}
    depth, start = 0, m.end() - 1
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                body = text[start + 1:j]
                return {k: (v3 if v3 is not None and v2.startswith('"') else v2)
                        for k, v2, v3 in _PY_DICT_RE.findall(body)}
    return {}


def _bone_names() -> tuple[str, ...]:
    """Every bone name the rig can write: the values of ``skel.BONE_OF_OBJECT``.

    ``skel.py`` imports ``bpy``, so this reads it as text like the rest of this module. It is the
    authority the engine actually meets -- the objects keep the names the Blender build has always
    used and the *bone* carries the engine's name -- so it, and not the object tuples, is what an
    ``OptionalBones()`` entry has to appear in.
    """
    text = _read(SKEL_PY)
    m = re.search(r"^BONE_OF_OBJECT\s*:?[^=]*=\s*\{", text, re.M)
    if m is None:
        return ()
    depth, start = 0, m.end() - 1
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return tuple(v for _k, v in re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"',
                                                       text[start + 1:j]))
    return ()


def _contract_tuple(name: str) -> tuple[str, ...]:
    """The same list read from the bpy-free ``vlib/contract.py``, which is where it now lives."""
    path = REPO_ROOT / "blender" / "vehicles" / "vlib" / "contract.py"
    if not path.is_file():
        return ()
    return py_tuple(path.read_text(encoding="utf-8", errors="replace"), name)
