"""Convert MPFB2's ``game_engine`` rig into the UE5-Mannequin skeleton, weights included.

MPFB fits its ``game_engine`` armature to the *actual* body shape by reading the MakeHuman joint helper cubes,
so bone positions are correct for every macro-target combination.  What it does not give is the UE5 bone set:
five spine bones, two neck bones, finger metacarpals and the seven non-deforming IK bones.  This module adds
them and redistributes the MakeHuman skin weights across the new bones, then normalises every vertex to a
weight sum of exactly 1.

Everything is done through ``bpy.data`` (edit bones and vertex groups) rather than operators, so it runs
headless without a UI context.
"""
from __future__ import annotations

import logging

import bpy
from mathutils import Vector

import ue5_skeleton as ue5

log = logging.getLogger("nycsim.character.rig")

#: How wide, as a fraction of the parent bone, the blend between two halves of a split bone is.
_SPLIT_BLEND = 1.0
#: Radius (metres) around a metacarpal segment inside which palm weight is transferred to it.
_METACARPAL_RADIUS = 0.022


# --------------------------------------------------------------------------------------- weight bookkeeping
def snapshot_weights(obj: bpy.types.Object) -> dict[str, dict[int, float]]:
    """``{vertex_group_name: {vertex_index: weight}}`` for a mesh object."""
    names = [g.name for g in obj.vertex_groups]
    out: dict[str, dict[int, float]] = {n: {} for n in names}
    for vert in obj.data.vertices:
        for ge in vert.groups:
            if ge.weight > 0.0:
                out[names[ge.group]][vert.index] = float(ge.weight)
    return out


def apply_weights(obj: bpy.types.Object, weights: dict[str, dict[int, float]], *, keep: tuple[str, ...] = ()) -> None:
    """Replace the object's vertex groups with ``weights`` (groups in ``keep`` are preserved untouched)."""
    kept = {name: dict(data) for name, data in snapshot_weights(obj).items() if name in keep}
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    merged = dict(kept)
    merged.update(weights)
    for name, data in merged.items():
        group = obj.vertex_groups.new(name=name)
        for idx, w in data.items():
            if w > 0.0:
                group.add([idx], float(w), "REPLACE")


def normalise_weights(weights: dict[str, dict[int, float]], n_verts: int) -> dict[str, dict[int, float]]:
    """Scale every vertex's weights so they sum to 1. Vertices with no weight are left empty (reported)."""
    totals = [0.0] * n_verts
    for data in weights.values():
        for idx, w in data.items():
            totals[idx] += w
    out: dict[str, dict[int, float]] = {}
    for name, data in weights.items():
        newdata = {}
        for idx, w in data.items():
            total = totals[idx]
            if total > 1e-9:
                newdata[idx] = w / total
        out[name] = newdata
    return out


def unweighted_vertices(weights: dict[str, dict[int, float]], n_verts: int) -> list[int]:
    seen = set()
    for data in weights.values():
        seen.update(idx for idx, w in data.items() if w > 0.0)
    return [i for i in range(n_verts) if i not in seen]


# ------------------------------------------------------------------------------------------- bone surgery
def _split_edit_bone(arm: bpy.types.Object, name: str, new_names: list[str]) -> list[tuple[Vector, Vector]]:
    """Split edit bone ``name`` into ``len(new_names)`` collinear segments; return their (head, tail) pairs."""
    ebones = arm.data.edit_bones
    src = ebones[name]
    head, tail, roll = src.head.copy(), src.tail.copy(), src.roll
    parent, connected = src.parent, src.use_connect
    children = [b for b in ebones if b.parent == src]
    n = len(new_names)
    pts = [head.lerp(tail, i / n) for i in range(n + 1)]

    ebones.remove(src)
    created = []
    prev = None
    for i, new_name in enumerate(new_names):
        bone = ebones.new(new_name)
        bone.head, bone.tail, bone.roll = pts[i], pts[i + 1], roll
        bone.use_deform = True
        if i == 0:
            bone.parent = parent
            bone.use_connect = connected
        else:
            bone.parent = prev
            bone.use_connect = True
        created.append(bone)
        prev = bone
    for child in children:
        was_connected = child.use_connect
        child.parent = created[-1]
        child.use_connect = was_connected
    return [(b.head.copy(), b.tail.copy()) for b in created]


def _smoothstep(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _split_group_weights(weights: dict[str, dict[int, float]], src_name: str, new_names: list[str],
                         head: Vector, tail: Vector, coords: list[Vector]) -> None:
    """Redistribute ``src_name``'s weights over ``new_names`` by projection along the original bone axis."""
    data = weights.pop(src_name, {})
    axis = tail - head
    length = axis.length
    if length < 1e-9:
        weights[new_names[0]] = data
        for extra in new_names[1:]:
            weights.setdefault(extra, {})
        return
    axis = axis / length
    n = len(new_names)
    for name in new_names:
        weights.setdefault(name, {})
    for idx, w in data.items():
        s = (coords[idx] - head).dot(axis) / length
        # position along the chain in "segment index" units, blended with a smoothstep of width _SPLIT_BLEND
        pos = min(max(s, 0.0), 1.0) * n
        for i, name in enumerate(new_names):
            centre = i + 0.5
            share = 1.0 - _smoothstep(abs(pos - centre) / (0.5 + 0.5 * _SPLIT_BLEND))
            if share > 0.0:
                weights[name][idx] = weights[name].get(idx, 0.0) + w * share


def _rename_group(weights: dict[str, dict[int, float]], old: str, new: str) -> None:
    if old in weights:
        merged = weights.pop(old)
        if new in weights:
            for idx, w in merged.items():
                weights[new][idx] = weights[new].get(idx, 0.0) + w
        else:
            weights[new] = merged


# ------------------------------------------------------------------------------------------------ main API
def convert_to_ue5(armature: bpy.types.Object, meshes: list[bpy.types.Object]) -> dict:
    """Rewrite ``armature`` (an MPFB ``game_engine`` rig) in place as the UE5 mannequin skeleton.

    ``meshes`` are every skinned mesh bound to it (body, proxy, clothes, eyes, hair, ...).  Returns a report
    dict with the resulting bone list and weight statistics.
    """
    if armature.type != "ARMATURE":
        raise TypeError(f"{armature.name} is not an armature")

    snapshots = {m.name: snapshot_weights(m) for m in meshes}
    world_coords = {m.name: [m.matrix_world @ v.co for v in m.data.vertices] for m in meshes}

    view_layer = bpy.context.view_layer
    for ob in bpy.data.objects:
        ob.select_set(False)
    view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = armature.data.edit_bones

    for required in ("Root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head"):
        if required not in ebones:
            bpy.ops.object.mode_set(mode="OBJECT")
            raise RuntimeError(f"source rig is not MPFB game_engine: bone {required!r} missing")

    ebones["Root"].name = "root"
    for mesh_weights in snapshots.values():
        _rename_group(mesh_weights, "Root", "root")

    # --- spine 3 -> 5 and neck 1 -> 2, walking the plan from the chest downwards so names never collide
    plan = ue5.spine_split_plan() + ue5.neck_split_plan()
    for src_name, new_names in reversed(plan):
        head = ebones[src_name].head.copy()
        tail = ebones[src_name].tail.copy()
        _split_edit_bone(armature, src_name, new_names)
        for mesh in meshes:
            _split_group_weights(snapshots[mesh.name], src_name, new_names, head, tail, world_coords[mesh.name])

    # --- finger metacarpals: wrist -> knuckle, in front of every non-thumb proximal phalanx
    metacarpal_segments: list[tuple[str, Vector, Vector]] = []
    for side in ue5.SIDES:
        hand = ebones[f"hand_{side}"]
        for finger in ("index", "middle", "ring", "pinky"):
            prox = ebones[f"{finger}_01_{side}"]
            meta = ebones.new(f"{finger}_metacarpal_{side}")
            meta.head = hand.head.copy()
            meta.tail = prox.head.copy()
            meta.roll = prox.roll
            meta.parent = hand
            meta.use_connect = False
            meta.use_deform = True
            prox.parent = meta
            prox.use_connect = True
            metacarpal_segments.append((meta.name, meta.head.copy(), meta.tail.copy()))

    # --- IK bones: non-deforming, 15 cm markers, roots at the actor origin
    for name, parent_name in ue5.IK_BONES:
        bone = ebones.new(name)
        follow = ue5.IK_FOLLOW[name]
        if follow and follow in ebones:
            src = ebones[follow]
            bone.head, bone.tail, bone.roll = src.head.copy(), src.tail.copy(), src.roll
        else:
            bone.head = Vector((0.0, 0.0, 0.0))
            bone.tail = Vector((0.0, 0.0, 0.15))
        bone.parent = ebones[parent_name] if parent_name in ebones else None
        bone.use_connect = False
        bone.use_deform = False

    bone_names = [b.name for b in ebones]
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- metacarpal weight transfer out of the palm
    for mesh in meshes:
        weights = snapshots[mesh.name]
        coords = world_coords[mesh.name]
        for side in ue5.SIDES:
            palm = weights.get(f"hand_{side}")
            if not palm:
                continue
            for name, head, tail in metacarpal_segments:
                if not name.endswith(f"_{side}"):
                    continue
                axis = tail - head
                length = axis.length
                if length < 1e-9:
                    continue
                unit = axis / length
                target = weights.setdefault(name, {})
                for idx, w in list(palm.items()):
                    rel = coords[idx] - head
                    s = rel.dot(unit) / length
                    if s <= 0.0 or s >= 1.0:
                        continue
                    dist = (rel - unit * (s * length)).length
                    if dist > _METACARPAL_RADIUS:
                        continue
                    share = _smoothstep(s) * (1.0 - dist / _METACARPAL_RADIUS) * 0.6
                    if share <= 0.0:
                        continue
                    moved = w * share
                    target[idx] = target.get(idx, 0.0) + moved
                    palm[idx] = w - moved

    stats = {}
    for mesh in meshes:
        n = len(mesh.data.vertices)
        weights = snapshots[mesh.name]
        # keep only groups that name a bone; MakeHuman also stores non-deform helper groups on the basemesh
        deform = {k: v for k, v in weights.items() if k in bone_names}
        other = tuple(k for k in weights if k not in bone_names)
        missing = unweighted_vertices(deform, n)
        deform = normalise_weights(deform, n)
        apply_weights(mesh, deform, keep=other)
        stats[mesh.name] = {"vertices": n, "deform_groups": len(deform), "unweighted": len(missing)}
        if missing:
            log.warning("%s: %d vertices carry no armature weight", mesh.name, len(missing))

    log.info("UE5 skeleton: %d bones", len(bone_names))
    return {"bones": bone_names, "meshes": stats}


def verify_skeleton(armature: bpy.types.Object) -> list[str]:
    """Return the list of problems: missing UE5 bones, wrong parents, extra bones."""
    problems: list[str] = []
    have = {b.name: b for b in armature.data.bones}
    expected_parents = ue5.ue5_parents()
    for name in ue5.ue5_bone_names():
        if name not in have:
            problems.append(f"missing bone {name}")
            continue
        want = expected_parents[name]
        got = have[name].parent.name if have[name].parent else None
        if got != want:
            problems.append(f"{name}: parent is {got!r}, expected {want!r}")
    for name in have:
        if name not in expected_parents:
            problems.append(f"unexpected bone {name}")
    return problems
