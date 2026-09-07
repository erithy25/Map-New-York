"""Pose evaluation and analytic IK for the UE5 skeleton.

Blender's own pose evaluation is reproduced here in closed form so that a pose can be solved without a
dependency-graph update per bone (a full clip is thousands of poses).  For a bone with an inheriting parent:

``world(b) = world(parent) @ rest(parent)^-1 @ rest(b) @ basis(b)``

where ``rest(b)`` is ``bone.matrix_local`` (armature space), ``basis(b)`` is ``pose_bone.matrix_basis`` and
``world(b)`` is ``pose_bone.matrix``.  MPFB's rigs use ``use_inherit_rotation = True``, ``inherit_scale =
'FULL'`` and ``use_local_location = True`` on every bone, which is exactly the case this formula covers;
:meth:`Rig.check_inheritance` asserts it.

On top of that, :func:`two_bone_ik` gives the classic circle-intersection solution for a shoulder/elbow/wrist
or hip/knee/ankle chain, so poses can be authored as *hand and foot targets in world space* ("left hand on the
wheel rim at nine o'clock") instead of hand-guessed Euler angles.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import bpy
from mathutils import Matrix, Quaternion, Vector

import ue5_skeleton as ue5


@dataclass
class Rig:
    """Cached rest data for one armature plus the closed-form pose evaluator."""

    armature: bpy.types.Object
    order: list[str] = field(default_factory=list)
    parent: dict[str, str | None] = field(default_factory=dict)
    rest: dict[str, Matrix] = field(default_factory=dict)
    rest_inv: dict[str, Matrix] = field(default_factory=dict)
    length: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        bones = self.armature.data.bones
        self.order = [b.name for b in bones]           # bpy keeps parents before children
        for bone in bones:
            self.parent[bone.name] = bone.parent.name if bone.parent else None
            self.rest[bone.name] = bone.matrix_local.copy()
            self.rest_inv[bone.name] = bone.matrix_local.inverted()
            self.length[bone.name] = bone.length

    def check_inheritance(self) -> list[str]:
        bad = []
        for bone in self.armature.data.bones:
            if not bone.use_inherit_rotation or bone.inherit_scale != "FULL" or not bone.use_local_location:
                bad.append(bone.name)
        return bad

    # ---------------------------------------------------------------------------------- evaluation
    def base_matrix(self, name: str, world: dict[str, Matrix]) -> Matrix:
        """The bone's armature-space matrix with an identity basis, given already-solved parents."""
        par = self.parent[name]
        if par is None:
            return self.rest[name].copy()
        return world[par] @ self.rest_inv[par] @ self.rest[name]

    def evaluate(self, basis: dict[str, Matrix]) -> dict[str, Matrix]:
        """Armature-space matrix of every bone for the given ``matrix_basis`` map."""
        world: dict[str, Matrix] = {}
        identity = Matrix.Identity(4)
        for name in self.order:
            world[name] = self.base_matrix(name, world) @ basis.get(name, identity)
        return world

    def basis_for_world(self, name: str, world_matrix: Matrix, world: dict[str, Matrix]) -> Matrix:
        """The ``matrix_basis`` that puts bone ``name`` at ``world_matrix`` given solved parents."""
        return self.base_matrix(name, world).inverted() @ world_matrix

    def rest_world(self) -> dict[str, Matrix]:
        return {name: self.rest[name].copy() for name in self.order}

    def apply(self, basis: dict[str, Matrix]) -> None:
        """Write a basis map onto the armature's pose bones."""
        identity = Matrix.Identity(4)
        for name in self.order:
            pose_bone = self.armature.pose.bones.get(name)
            if pose_bone is None:
                continue
            pose_bone.rotation_mode = "QUATERNION"
            pose_bone.matrix_basis = basis.get(name, identity)


# ------------------------------------------------------------------------------------------ rotation tools
def swing_to(rest_dir: Vector, target_dir: Vector) -> Quaternion:
    """Shortest-arc rotation taking ``rest_dir`` onto ``target_dir``."""
    a, b = rest_dir.normalized(), target_dir.normalized()
    dot = max(-1.0, min(1.0, a.dot(b)))
    if dot > 1.0 - 1e-9:
        return Quaternion((1.0, 0.0, 0.0, 0.0))
    if dot < -1.0 + 1e-9:
        axis = a.orthogonal().normalized()
        return Quaternion(axis, math.pi)
    axis = a.cross(b).normalized()
    return Quaternion(axis, math.acos(dot))


def rotation_basis(rig: Rig, name: str, world: dict[str, Matrix], rotation: Quaternion) -> Matrix:
    """``matrix_basis`` that applies ``rotation`` (armature space) on top of the bone's inherited rest pose."""
    base = rig.base_matrix(name, world)
    base_rot = base.to_quaternion()
    return (base_rot.inverted() @ rotation @ base_rot).to_matrix().to_4x4()


def aim_basis(rig: Rig, name: str, world: dict[str, Matrix], direction: Vector, *, twist_deg: float = 0.0) -> Matrix:
    """``matrix_basis`` that points the bone's +Y axis along ``direction``, with an optional twist about it."""
    base = rig.base_matrix(name, world)
    rest_dir = (base.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    rot = swing_to(rest_dir, direction)
    if abs(twist_deg) > 1e-9:
        rot = Quaternion(direction.normalized(), math.radians(twist_deg)) @ rot
    return rotation_basis(rig, name, world, rot)


# ------------------------------------------------------------------------------------------------- IK
def two_bone_ik(root: Vector, target: Vector, pole: Vector, l1: float, l2: float) -> tuple[Vector, Vector, Vector]:
    """Solve a two-bone chain. Returns ``(elbow, dir_upper, dir_lower)``.

    ``pole`` is a point the middle joint is pushed towards.  The target is clamped into the reachable
    annulus so the solution never becomes degenerate.
    """
    to_target = target - root
    dist = to_target.length
    lo, hi = abs(l1 - l2) + 1e-4, l1 + l2 - 1e-4
    dist = min(max(dist, lo), hi)
    if to_target.length < 1e-9:
        to_target = Vector((0.0, 0.0, -1.0))
    axis = to_target.normalized()
    reach = target if abs(to_target.length - dist) < 1e-9 else root + axis * dist

    a = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    h_sq = max(l1 * l1 - a * a, 0.0)
    h = math.sqrt(h_sq)
    pole_dir = pole - root
    pole_dir = pole_dir - axis * pole_dir.dot(axis)
    if pole_dir.length < 1e-6:
        pole_dir = axis.orthogonal()
    pole_dir.normalize()
    elbow = root + axis * a + pole_dir * h
    return elbow, (elbow - root).normalized(), (reach - elbow).normalized()


def solve_limb(rig: Rig, world: dict[str, Matrix], upper: str, lower: str, end: str, *,
               target: Vector, pole: Vector, end_rotation: Quaternion | None = None,
               upper_twist_deg: float = 0.0) -> dict[str, Matrix]:
    """IK one limb and return the basis matrices for ``upper``, ``lower`` and (optionally) ``end``.

    ``world`` must already contain the limb's parent chain; it is updated in place as the chain is solved.
    """
    root = rig.base_matrix(upper, world).translation.copy()
    l1, l2 = rig.length[upper], rig.length[lower]
    _elbow, dir_upper, dir_lower = two_bone_ik(root, target, pole, l1, l2)

    out: dict[str, Matrix] = {}
    out[upper] = aim_basis(rig, upper, world, dir_upper, twist_deg=upper_twist_deg)
    world[upper] = rig.base_matrix(upper, world) @ out[upper]
    out[lower] = aim_basis(rig, lower, world, dir_lower)
    world[lower] = rig.base_matrix(lower, world) @ out[lower]
    if end_rotation is not None:
        base = rig.base_matrix(end, world)
        out[end] = base.to_quaternion().inverted().to_matrix().to_4x4() @ end_rotation.to_matrix().to_4x4()
        world[end] = base @ out[end]
    return out


# --------------------------------------------------------------------------------------------- pose spec
@dataclass
class PoseSpec:
    """A single authored key pose.

    ``rot`` gives Euler XYZ degrees in each bone's own rest space (the same numbers a rigger types into
    Blender's N-panel).  ``ik`` gives world-space targets for the four limbs.  ``root`` and ``pelvis`` offsets
    move the whole character.
    """

    rot: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    ik: dict[str, dict] = field(default_factory=dict)
    root_loc: Vector = field(default_factory=lambda: Vector((0.0, 0.0, 0.0)))
    root_yaw_deg: float = 0.0
    pelvis_loc: Vector = field(default_factory=lambda: Vector((0.0, 0.0, 0.0)))

    def copy(self) -> "PoseSpec":
        return PoseSpec(rot=dict(self.rot), ik={k: dict(v) for k, v in self.ik.items()},
                        root_loc=self.root_loc.copy(), root_yaw_deg=self.root_yaw_deg,
                        pelvis_loc=self.pelvis_loc.copy())


#: Which bones each IK limb key drives, and the sign of the pole offset.
LIMB_CHAINS = {
    "hand_l": ("upperarm_l", "lowerarm_l", "hand_l"),
    "hand_r": ("upperarm_r", "lowerarm_r", "hand_r"),
    "foot_l": ("thigh_l", "calf_l", "foot_l"),
    "foot_r": ("thigh_r", "calf_r", "foot_r"),
}


def solve_pose(rig: Rig, spec: PoseSpec, base: dict[str, Matrix] | None = None) -> dict[str, Matrix]:
    """Evaluate a :class:`PoseSpec` into a full ``matrix_basis`` map.

    ``base`` is the pose the spec is layered on: every bone starts from ``base[bone]`` and the spec's Euler
    angles are applied *after* it in the bone's local space, so "turn the head another 30 degrees" composes
    with whatever the base pose already does.
    """
    basis: dict[str, Matrix] = {k: v.copy() for k, v in (base or {}).items()}
    for name, angles in spec.rot.items():
        if name not in rig.rest:
            raise KeyError(f"pose references unknown bone {name!r}")
        basis[name] = basis.get(name, Matrix.Identity(4)) @ _euler_basis(angles)
    if spec.root_loc.length > 0.0 or abs(spec.root_yaw_deg) > 0.0:
        rot = Matrix.Rotation(math.radians(spec.root_yaw_deg), 4, "Z")
        basis["root"] = Matrix.Translation(spec.root_loc) @ rot
    if spec.pelvis_loc.length > 0.0:
        existing = basis.get("pelvis", Matrix.Identity(4))
        basis["pelvis"] = Matrix.Translation(spec.pelvis_loc) @ existing

    world = rig.evaluate(basis)
    for limb, params in spec.ik.items():
        upper, lower, end = LIMB_CHAINS[limb]
        solved = solve_limb(rig, world, upper, lower, end,
                            target=Vector(params["target"]), pole=Vector(params["pole"]),
                            end_rotation=params.get("rotation"),
                            upper_twist_deg=float(params.get("twist_deg", 0.0)))
        basis.update(solved)
        world = rig.evaluate(basis)
    return basis


def _euler_basis(angles_deg: tuple[float, float, float]) -> Matrix:
    from mathutils import Euler  # noqa: PLC0415
    return Euler((math.radians(angles_deg[0]), math.radians(angles_deg[1]),
                  math.radians(angles_deg[2])), "XYZ").to_matrix().to_4x4()


def orient(rest_rotation: Quaternion, y_target: Vector, z_target: Vector) -> Quaternion:
    """World rotation that points a bone's +Y along ``y_target`` and twists its +Z towards ``z_target``.

    Used to place hands: +Y is the direction the fingers point, +Z the back of the hand.
    """
    y_target = y_target.normalized()
    swing = swing_to(rest_rotation @ Vector((0.0, 1.0, 0.0)), y_target)
    current_z = (swing @ rest_rotation) @ Vector((0.0, 0.0, 1.0))
    a = current_z - y_target * current_z.dot(y_target)
    b = z_target - y_target * z_target.dot(y_target)
    if a.length < 1e-6 or b.length < 1e-6:
        return swing @ rest_rotation
    a.normalize()
    b.normalize()
    angle = math.atan2(a.cross(b).dot(y_target), a.dot(b))
    return Quaternion(y_target, angle) @ swing @ rest_rotation


def bake_ik_bones(rig: Rig, basis: dict[str, Matrix]) -> None:
    """Set the seven UE5 IK bones so they track their FK counterparts (UE's own convention)."""
    world = rig.evaluate(basis)
    for name, follow in ue5.IK_FOLLOW.items():
        if name not in rig.rest:
            continue
        if follow is None:
            basis[name] = Matrix.Identity(4)
            continue
        source = "hand_r" if name in ("ik_hand_gun", "ik_hand_r") else follow
        if source not in world:
            continue
        basis[name] = rig.basis_for_world(name, world[source], world)
        world = rig.evaluate(basis)
