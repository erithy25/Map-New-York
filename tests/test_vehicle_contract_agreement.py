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
    rig = _read(RIG_PY)
    pivot = re.search(r'PIVOT_CONVENTION\s*=\s*"([^"]+)"', rig)
    assert pivot is not None, "rig.py no longer declares PIVOT_CONVENTION"
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
    emitted = set(py_tuple(rig, "CONTRACT_FULL"))
    assert emitted, "rig.py declares no CONTRACT_FULL"
    missing = sorted(required - emitted)
    assert not missing, (
        f"{len(missing)} bone(s) the engine requires are never written by the Blender exporter: "
        f"{missing}. Engine: {CONTRACT_CPP.relative_to(REPO_ROOT)}::RequiredBones(). "
        f"Exporter: {RIG_PY.relative_to(REPO_ROOT)}::CONTRACT_FULL.")


@pytest.mark.xfail(strict=True, reason=(
    "Recorded, not fixed. 15 of the engine's lamp slots have no counterpart in the exporter: the "
    "exporter writes LIGHT_TURN_FL/FR/RL/RR where the engine drives LIGHT_IND_*, one LIGHT_HIGH and "
    "one LIGHT_DRL where the engine drives _L/_R pairs, LIGHT_BRAKE_CHMSL for LIGHT_BRAKE_C, and "
    "nothing at all for LIGHT_FOG_L/R, LIGHT_IND_SL/SR, LIGHT_INTERIOR and LIGHT_DASH. Until the "
    "exporter is renamed and rebuilt (task 'Stage 26'), UNYCVehicleLightsComponent finds none of "
    "them and every indicator, high beam and DRL on the car is dead. strict=True so that fixing the "
    "exporter fails this xfail and forces the marker off rather than letting the record go stale."))
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
    emitted = set(py_tuple(rig, "MATERIAL_SLOTS_FULL")) | set(py_tuple(rig, "LIGHT_SLOTS_FULL"))
    assert emitted, "rig.py declares no MATERIAL_SLOTS_FULL"
    missing = sorted(required - emitted)
    assert not missing, (
        f"{len(missing)} lamp slot(s) the engine drives are never written by the Blender exporter: "
        f"{missing}. Engine: {CONTRACT_CPP.relative_to(REPO_ROOT)}::LightSlots(). "
        f"Exporter: {RIG_PY.relative_to(REPO_ROOT)}::LIGHT_SLOTS_FULL.")


@pytest.mark.xfail(strict=True, reason=(
    "Recorded, not fixed. 12 of the engine's 22 optional bones are names the exporter never writes. "
    "Three are pure renames -- the exporter says Hood, Trunk, Shifter where the engine says "
    "Door_Hood, Door_Trunk, GearSelector -- and nine are geometry that does not exist yet: the four "
    "instrument needles, the interior mirror, both column stalks, the rear wiper and the fuel flap. "
    "Optional means the vehicle still imports; it does not mean the dashboard works. Fixed in task "
    "'Stage 26'. strict=True so the marker cannot outlive the defect."))
def test_every_optional_bone_the_engine_looks_up_is_a_name_the_exporter_writes():
    """``OptionalBones()`` names the engine will look up on an imported mesh.

    A missing optional bone is not an import failure, which is exactly why it survives unnoticed:
    ``UNYCVehicleDashboardComponent`` asks for ``Needle_Speed`` every frame, gets ``INDEX_NONE``, and
    the speedometer needle simply never moves.
    """
    h, cpp, rig = _read(CONTRACT_H), _read(CONTRACT_CPP), _read(RIG_PY)
    bones = namespace_names(h, "NYCVehicleBones")
    assert bones, "NYCVehicleContract.h declares no NYCVehicleBones names"
    body = re.search(r"OptionalBones\(\)[^{]*\{(.*?)\n\}", cpp, re.S)
    assert body is not None, "NYCVehicleContract.cpp has no OptionalBones() body"
    optional = {bones[i] for i in re.findall(r"NYCVehicleBones::(\w+)", body.group(1)) if i in bones}
    assert optional, "OptionalBones() names no bones"
    emitted = set(py_tuple(rig, "CONTRACT_FULL"))
    missing = sorted(optional - emitted)
    assert not missing, (
        f"{len(missing)} optional bone(s) the engine looks up are never written by the Blender "
        f"exporter: {missing}. Engine: {CONTRACT_CPP.relative_to(REPO_ROOT)}::OptionalBones(). "
        f"Exporter: {RIG_PY.relative_to(REPO_ROOT)}::CONTRACT_FULL.")
