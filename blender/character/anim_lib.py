"""Baking pose sequences into Blender actions and exporting the character as a glTF binary.

Clips are baked straight into F-curves (``fcurves.new`` + ``keyframe_points.foreach_set``) rather than through
``keyframe_insert``: a 25-clip character is ~90 000 keyframes and the operator path takes minutes where this
takes under a second.  Quaternion tracks are sign-continuous so the exporter's linear key reduction and the
runtime's slerp never take the long way round.

Every clip is pushed onto its own muted NLA track, which is what makes Blender's glTF exporter emit one named
glTF animation per clip (``export_animation_mode='ACTIONS'``).
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import bpy
from mathutils import Matrix, Quaternion

import chenv
import nycsim_bpy as nb

log = logging.getLogger("nycsim.character.anim")

FPS = 30


@dataclass
class Clip:
    """One finished animation ready to bake."""

    name: str
    frames: list[dict[str, Matrix]]
    fps: float = float(FPS)
    method: str = "procedural"
    loop: bool = False
    additive: bool = False
    notes: str = ""
    speed_mps: float | None = None
    source: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        return (len(self.frames) - 1) / self.fps

    def metadata(self) -> dict:
        meta = {"name": self.name, "frames": len(self.frames), "fps": self.fps,
                "duration_s": round(self.duration_s, 4), "method": self.method, "loop": self.loop,
                "additive": self.additive}
        if self.speed_mps is not None:
            meta["speed_mps"] = round(self.speed_mps, 3)
        if self.source:
            meta["source"] = self.source
        if self.notes:
            meta["notes"] = self.notes
        meta.update(self.extra)
        return meta


# ------------------------------------------------------------------------------------------------- baking
def bake_action(armature: bpy.types.Object, clip: Clip) -> bpy.types.Action:
    """Bake a clip's basis matrices into a new action on ``armature``."""
    bone_names = [b.name for b in armature.pose.bones]
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"      # the glTF exporter refuses a mixed-mode armature
    n = len(clip.frames)
    if n < 1:
        raise ValueError(f"clip {clip.name!r} has no frames")

    quats: dict[str, list[Quaternion]] = {b: [] for b in bone_names}
    locs: dict[str, list[tuple[float, float, float]]] = {b: [] for b in bone_names}
    identity = Matrix.Identity(4)
    for frame in clip.frames:
        for name in bone_names:
            basis = frame.get(name, identity)
            quats[name].append(basis.to_quaternion())
            locs[name].append(tuple(basis.to_translation()))

    action = bpy.data.actions.new(clip.name)
    action.use_fake_user = True
    slot = None
    if hasattr(action, "slots"):                      # Blender 4.4+ slotted actions
        slot = action.slots.new(id_type="OBJECT", name="Object")
        layer = action.layers.new("Layer")
        strip = layer.strips.new(type="KEYFRAME")
        channelbag = strip.channelbag(slot, ensure=True)
        fcurve_owner = channelbag
    else:
        fcurve_owner = action

    times = [1.0 + i for i in range(n)]
    for name in bone_names:
        qs = quats[name]
        for i in range(1, n):                          # sign continuity
            if qs[i].dot(qs[i - 1]) < 0.0:
                qs[i] = Quaternion((-qs[i].w, -qs[i].x, -qs[i].y, -qs[i].z))
        path = f'pose.bones["{name}"].rotation_quaternion'
        for axis, comp in enumerate(("w", "x", "y", "z")):
            _make_curve(fcurve_owner, path, axis, times, [getattr(q, comp) for q in qs])
        ls = locs[name]
        if any(abs(v) > 1e-7 for triple in ls for v in triple):
            path = f'pose.bones["{name}"].location'
            for axis in range(3):
                _make_curve(fcurve_owner, path, axis, times, [t[axis] for t in ls])

    if slot is not None:
        action.slots.active = slot
    return action


def _make_curve(owner, data_path: str, index: int, times: Sequence[float], values: Sequence[float]) -> None:
    curve = owner.fcurves.new(data_path, index=index)
    points = curve.keyframe_points
    points.add(len(times))
    flat: list[float] = []
    for t, v in zip(times, values):
        flat.extend((t, v))
    points.foreach_set("co", flat)
    points.foreach_set("interpolation", [1] * len(times))       # 1 == LINEAR
    curve.update()


def push_clip(armature: bpy.types.Object, clip: Clip) -> bpy.types.Action:
    """Bake ``clip`` and park it on its own muted NLA track so the glTF exporter emits it as an animation."""
    action = bake_action(armature, clip)
    if armature.animation_data is None:
        armature.animation_data_create()
    track = armature.animation_data.nla_tracks.new()
    track.name = clip.name
    strip = track.strips.new(clip.name, 1, action)
    strip.name = clip.name
    track.mute = True
    return action


def set_active_clip(armature: bpy.types.Object, action: bpy.types.Action | None) -> None:
    if armature.animation_data is None:
        armature.animation_data_create()
    armature.animation_data.action = action
    if action is not None and hasattr(action, "slots") and len(action.slots):
        armature.animation_data.action_slot = action.slots[0]


# ------------------------------------------------------------------------------------------------ export
def export_character(path: str | Path, objects: Sequence[bpy.types.Object], extras: dict) -> Path:
    """Export a rigged, animated, morph-target character to .glb with the NYCSim asset extras."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    meta = {"schema_version": nb.SCHEMA_VERSION,
            "generator_script": os.path.basename(sys.argv[0]) if sys.argv else "",
            "git_commit": nb.git_commit(),
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "units": "metres", "up_axis_blender": "Z"}
    meta.update(extras)
    scene["nycsim"] = json.dumps(meta)
    for ob in bpy.data.objects:
        ob.select_set(False)
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
        export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
        export_materials="EXPORT", export_image_format="AUTO",
        export_animations=True, export_animation_mode="ACTIONS", export_nla_strips=True,
        export_frame_range=False, export_force_sampling=False, export_bake_animation=False,
        export_optimize_animation_size=False, export_anim_single_armature=True,
        export_skins=True, export_morph=True, export_morph_normal=False,
        export_def_bones=False, export_rest_position_armature=True, export_extras=True,
        export_all_influences=False)
    if not path.exists() or path.stat().st_size < 1024:
        raise RuntimeError(f"glTF export failed or produced an empty file: {path}")
    patch_asset_extras(path, {"nycsim": meta})
    return path


def patch_asset_extras(path: Path, extras: dict) -> None:
    """Write ``extras`` into the glb's ``asset.extras`` (DATA_CONTRACTS §13).

    Blender's exporter can only put custom properties on scene and object nodes, so the JSON chunk is
    rewritten in place: the chunk keeps its 4-byte alignment by padding with spaces, and the file's total
    length field is corrected.
    """
    import struct  # noqa: PLC0415

    with open(path, "rb") as fh:
        blob = fh.read()
    magic, version, _length = struct.unpack_from("<III", blob, 0)
    if magic != 0x46546C67:
        raise ValueError(f"{path} is not a .glb")
    json_len, json_type = struct.unpack_from("<II", blob, 12)
    if json_type != 0x4E4F534A:
        raise ValueError(f"{path}: first chunk is not JSON")
    doc = json.loads(blob[20:20 + json_len].decode("utf-8"))
    doc.setdefault("asset", {}).setdefault("extras", {}).update(extras)
    rest = blob[20 + json_len:]
    new_json = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    new_json += b" " * ((4 - len(new_json) % 4) % 4)
    total = 12 + 8 + len(new_json) + len(rest)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", magic, version, total))
        fh.write(struct.pack("<II", len(new_json), json_type))
        fh.write(new_json)
        fh.write(rest)


def glb_summary(path: str | Path) -> dict:
    """Read back a .glb's JSON chunk: node/mesh/animation/morph-target counts and the animation names."""
    import struct  # noqa: PLC0415

    path = Path(path)
    with open(path, "rb") as fh:
        magic, _version, _length = struct.unpack("<III", fh.read(12))
        if magic != 0x46546C67:
            raise ValueError(f"{path} is not a .glb (magic {magic:#x})")
        chunk_len, chunk_type = struct.unpack("<II", fh.read(8))
        if chunk_type != 0x4E4F534A:
            raise ValueError(f"{path}: first chunk is not JSON")
        doc = json.loads(fh.read(chunk_len).decode("utf-8"))
    meshes = doc.get("meshes", [])
    morphs = 0
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            morphs = max(morphs, len(prim.get("targets", [])))
    skins = doc.get("skins", [])
    return {
        "bytes": path.stat().st_size,
        "nodes": len(doc.get("nodes", [])),
        "meshes": len(meshes),
        "materials": len(doc.get("materials", [])),
        "images": len(doc.get("images", [])),
        "animations": [a.get("name", "") for a in doc.get("animations", [])],
        "morph_targets": morphs,
        "morph_target_names": (meshes[0].get("extras", {}).get("targetNames", []) if meshes else []),
        "skin_joints": [len(s.get("joints", [])) for s in skins],
        "extras": doc.get("asset", {}).get("extras", {}),
    }


def write_catalog(entry: dict) -> Path:
    chenv.ensure_dirs()
    return nb.write_catalog_entry(chenv.CATALOG_DIR, entry)


def frame_at_rest(rig_order: Sequence[str]) -> dict[str, Matrix]:
    identity = Matrix.Identity(4)
    return {name: identity.copy() for name in rig_order}


def ease(t: float, kind: str = "smooth") -> float:
    """Normalised easing used by the procedural clips."""
    t = min(max(t, 0.0), 1.0)
    if kind == "linear":
        return t
    if kind == "smooth":
        return t * t * (3.0 - 2.0 * t)
    if kind == "in":
        return t * t
    if kind == "out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if kind == "sine":
        return 0.5 - 0.5 * math.cos(math.pi * t)
    raise ValueError(f"unknown easing {kind!r}")
