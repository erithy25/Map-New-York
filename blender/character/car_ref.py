"""Driver-package reference points read from the vehicles lane's exported Ford Fusion Hybrid.

The car animations (open door, get in, sit, steer, shift, mirror check, get out) are authored against the
*actual* geometry the vehicles agent exported - ``blender_out/vehicles/fusion_hybrid.glb`` - rather than
against guessed numbers, so the hands land on the real steering wheel rim and the real shifter knob.  The glb
is parsed directly (no bpy import needed) and its node/mesh data converted from glTF Y-up back to Blender
Z-up: ``(x, y, z)_glTF -> (x, -z, y)_Blender``.

If the vehicle glb has not been built, :func:`driver_package` falls back to the published 2019 Fusion Hybrid
interior dimensions recorded in :data:`FALLBACK` and flags ``source = "published"`` so the report can say so.
"""
from __future__ import annotations

import json
import logging
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path

from mathutils import Quaternion, Vector

import chenv

log = logging.getLogger("nycsim.character.car")

VEHICLE_GLB = chenv.REPO_ROOT / "blender_out" / "vehicles" / "fusion_hybrid.glb"

#: Published/derived fallback in the vehicle's own frame (origin = ground under rear-axle centre, +X forward,
#: +Y left, +Z up).  Values from `blender_out/vehicles/catalog/fusion_hybrid.json` and the SAE driver package.
FALLBACK = {
    "wheel_centre": (2.28, 0.375, 0.865),
    "wheel_radius": 0.202,
    "wheel_normal": (-0.906, 0.0, 0.423),      # 25 deg column rake from the horizontal
    "shifter_knob": (2.20, 0.0, 0.665),
    "door_handle": (2.10, 0.902, 0.860),
    "hip_point": (1.80, 0.375, 0.615),
    "heel_point": (2.66, 0.42, 0.42),
    "roof_rail": (2.05, 0.86, 1.40),
    "sill": (1.90, 0.80, 0.44),
    "mirror_inner": (2.67, 0.0, 1.36),
    "mirror_left": (2.42, 0.98, 1.02),
}


@dataclass
class DriverPackage:
    """Everything the seated/entering/exiting poses need, in the *car's* frame (metres)."""

    wheel_centre: Vector
    wheel_radius: float
    wheel_normal: Vector
    wheel_up: Vector
    shifter_knob: Vector
    door_handle: Vector
    hip_point: Vector
    heel_point: Vector
    roof_rail: Vector
    sill: Vector
    mirror_inner: Vector
    mirror_left: Vector
    source: str = "published"
    notes: dict = field(default_factory=dict)

    def rim_point(self, clock_hours: float) -> Vector:
        """A point on the steering-wheel rim at a clock position (3 = driver's right, 9 = driver's left).

        The rim is parameterised in the wheel's own plane: ``up`` is the 12 o'clock direction and
        ``right = up x normal`` the 3 o'clock direction.
        """
        angle = (clock_hours / 12.0) * 2.0 * math.pi
        right = self.wheel_up.cross(self.wheel_normal).normalized()
        offset = (self.wheel_up * math.cos(angle) + right * math.sin(angle)) * self.wheel_radius
        return self.wheel_centre + offset

    def as_dict(self) -> dict:
        return {"source": self.source, "wheel_centre": list(self.wheel_centre),
                "wheel_radius": self.wheel_radius, "wheel_normal": list(self.wheel_normal),
                "shifter_knob": list(self.shifter_knob), "door_handle": list(self.door_handle),
                "hip_point": list(self.hip_point), "heel_point": list(self.heel_point),
                "roof_rail": list(self.roof_rail), "sill": list(self.sill),
                "mirror_inner": list(self.mirror_inner), "mirror_left": list(self.mirror_left),
                **self.notes}


def _gltf_to_blender_vec(v) -> Vector:
    return Vector((float(v[0]), -float(v[2]), float(v[1])))


def _gltf_to_blender_quat(q) -> Quaternion:
    x, y, z, w = (float(c) for c in q)
    return Quaternion((w, x, -z, y))


def _read_glb(path: Path) -> tuple[dict, bytes]:
    with open(path, "rb") as fh:
        magic, _version, _length = struct.unpack("<III", fh.read(12))
        if magic != 0x46546C67:
            raise ValueError(f"{path} is not a .glb")
        json_len, json_type = struct.unpack("<II", fh.read(8))
        if json_type != 0x4E4F534A:
            raise ValueError(f"{path}: first chunk is not JSON")
        doc = json.loads(fh.read(json_len).decode("utf-8"))
        bin_len, bin_type = struct.unpack("<II", fh.read(8))
        if bin_type != 0x004E4942:
            raise ValueError(f"{path}: second chunk is not BIN")
        blob = fh.read(bin_len)
    return doc, blob


def _positions(doc: dict, blob: bytes, node: dict) -> list[Vector]:
    out: list[Vector] = []
    if "mesh" not in node:
        return out
    for prim in doc["meshes"][node["mesh"]]["primitives"]:
        acc = doc["accessors"][prim["attributes"]["POSITION"]]
        view = doc["bufferViews"][acc["bufferView"]]
        offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride", 12)
        for i in range(acc["count"]):
            x, y, z = struct.unpack_from("<fff", blob, offset + i * stride)
            out.append(Vector((x, y, z)))
    return out


def driver_package(path: str | Path | None = None) -> DriverPackage:
    """Read the driver package from the vehicle glb, or fall back to published dimensions."""
    path = Path(path) if path else VEHICLE_GLB
    if not path.exists():
        log.warning("vehicle glb %s not found - using published Fusion interior dimensions", path)
        return _fallback()
    try:
        doc, blob = _read_glb(path)
    except (OSError, ValueError) as exc:
        log.warning("cannot read %s (%s) - using published Fusion interior dimensions", path, exc)
        return _fallback()

    nodes = {node.get("name", ""): node for node in doc.get("nodes", [])}
    needed = ("SteeringWheel", "Shifter", "Handles", "Seat_FL", "Pedals", "Interior_Mirror")
    if any(n not in nodes for n in needed):
        log.warning("%s lacks nodes %s - using published dimensions", path,
                    [n for n in needed if n not in nodes])
        return _fallback()

    wheel_node = nodes["SteeringWheel"]
    centre = _gltf_to_blender_vec(wheel_node.get("translation", (0.0, 0.0, 0.0)))
    rot = _gltf_to_blender_quat(wheel_node.get("rotation", (0.0, 0.0, 0.0, 1.0)))
    local = _positions(doc, blob, wheel_node)
    radius = max((Vector((p.x, p.y, 0.0)).length for p in
                  (_gltf_to_blender_vec(q) for q in local)), default=FALLBACK["wheel_radius"])
    normal = (rot @ Vector((0.0, 0.0, 1.0))).normalized()
    up = (rot @ Vector((0.0, 1.0, 0.0))).normalized()
    if normal.z < 0.0:            # point the axis up-and-back, towards the driver's chest
        normal = -normal

    shifter = _bbox_centre(doc, blob, nodes["Shifter"])
    handles = [_gltf_to_blender_vec(p) for p in _positions(doc, blob, nodes["Handles"])]
    driver_handle = _cluster_centre(handles, lambda p: p.y > 0.5 and p.x > 1.6)
    seat_lo, seat_hi = _bbox(doc, blob, nodes["Seat_FL"])
    pedals_lo, pedals_hi = _bbox(doc, blob, nodes["Pedals"])
    mirror = _bbox_centre(doc, blob, nodes["Interior_Mirror"])

    # SAE H-point: 0.10 m above the cushion top at 40 % of the cushion depth from its rear edge
    cushion_z = seat_lo.z + 0.30 * (seat_hi.z - seat_lo.z)
    hip = Vector((seat_lo.x + 0.42 * (seat_hi.x - seat_lo.x), 0.5 * (seat_lo.y + seat_hi.y),
                  cushion_z + 0.10))
    heel = Vector((pedals_hi.x - 0.05, 0.5 * (pedals_lo.y + pedals_hi.y), pedals_lo.z - 0.06))

    package = DriverPackage(
        wheel_centre=centre, wheel_radius=float(radius), wheel_normal=normal, wheel_up=up,
        shifter_knob=shifter + Vector((0.0, 0.0, 0.012)), door_handle=driver_handle, hip_point=hip,
        heel_point=heel,
        roof_rail=Vector((driver_handle.x, driver_handle.y - 0.04, 1.40)),
        sill=Vector((hip.x + 0.10, seat_hi.y + 0.16, seat_lo.z + 0.01)),
        mirror_inner=mirror, mirror_left=Vector((2.42, 0.98, 1.02)),
        source=str(path.relative_to(chenv.REPO_ROOT)),
        notes={"seat_bbox": [list(seat_lo), list(seat_hi)]})
    log.info("driver package from %s: wheel %s r=%.3f, shifter %s, handle %s, H-point %s", path.name,
             [round(v, 3) for v in centre], radius, [round(v, 3) for v in shifter],
             [round(v, 3) for v in driver_handle], [round(v, 3) for v in hip])
    return package


def _fallback() -> DriverPackage:
    normal = Vector(FALLBACK["wheel_normal"]).normalized()
    up = Vector((0.0, 0.0, 1.0)) - normal * normal.z
    up = up.normalized() if up.length > 1e-6 else Vector((0.0, 1.0, 0.0))
    return DriverPackage(wheel_centre=Vector(FALLBACK["wheel_centre"]),
                         wheel_radius=FALLBACK["wheel_radius"], wheel_normal=normal, wheel_up=up,
                         shifter_knob=Vector(FALLBACK["shifter_knob"]),
                         door_handle=Vector(FALLBACK["door_handle"]),
                         hip_point=Vector(FALLBACK["hip_point"]),
                         heel_point=Vector(FALLBACK["heel_point"]),
                         roof_rail=Vector(FALLBACK["roof_rail"]), sill=Vector(FALLBACK["sill"]),
                         mirror_inner=Vector(FALLBACK["mirror_inner"]),
                         mirror_left=Vector(FALLBACK["mirror_left"]), source="published")


def _bbox(doc: dict, blob: bytes, node: dict) -> tuple[Vector, Vector]:
    pts = [_gltf_to_blender_vec(p) for p in _positions(doc, blob, node)]
    if not pts:
        return Vector(), Vector()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _bbox_centre(doc: dict, blob: bytes, node: dict) -> Vector:
    lo, hi = _bbox(doc, blob, node)
    return (lo + hi) * 0.5


def _cluster_centre(points: list[Vector], predicate) -> Vector:
    chosen = [p for p in points if predicate(p)]
    if not chosen:
        return Vector(FALLBACK["door_handle"])
    return sum(chosen, Vector()) / len(chosen)
