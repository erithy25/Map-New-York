"""Procedurally authored animation clips for the NYCSim character.

Everything that the CMU set cannot supply is authored here.  Two authoring styles are used and each clip's
metadata says which:

``procedural-keyposed``
    Key poses at named times, solved through :mod:`pose_solver` (analytic two-bone IK for the limbs) and
    interpolated with quaternion slerp and a smoothstep ease.  Hand and foot positions are given as world
    targets - "left hand on the steering-wheel rim at nine o'clock" is literally that, using the rim radius
    read out of the vehicles lane's exported Ford Fusion Hybrid.

``procedural-on-mocap-gait``
    Clips whose *timing* has to be a real gait (stairs, the 90-degree turns, walking while on the phone) are
    built by overlaying procedural targets on the retargeted CMU walk cycle, so the stride period, the
    double-support fraction and the pelvis bob stay the ones measured from the capture.

All angles are degrees, all positions metres, all clips 30 fps.  Poses are expressed in the character's own
frame: origin on the ground between the feet, ``BodyRef.forward`` the facing direction.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from mathutils import Matrix, Quaternion, Vector

import anim_lib
import car_ref
import pose_solver
from anim_lib import Clip
from pose_solver import PoseSpec, Rig

log = logging.getLogger("nycsim.character.proc")

UP = Vector((0.0, 0.0, 1.0))


# --------------------------------------------------------------------------------------------- body frame
@dataclass
class BodyRef:
    """Anatomical reference points of one character, in armature space."""

    rig: Rig
    forward: Vector = field(default_factory=lambda: Vector((0.0, -1.0, 0.0)))
    right: Vector = field(default_factory=lambda: Vector((1.0, 0.0, 0.0)))

    def __post_init__(self) -> None:
        # The toe bones splay outwards symmetrically, so the body's forward axis is their *mean*: using
        # ball_l on its own biases the facing by 3.4 degrees, which would make the character walk crabwise.
        bones = self.rig.armature.data.bones
        toe = Vector((0.0, 0.0, 0.0))
        for side in ("l", "r"):
            ball = bones[f"ball_{side}"]
            v = ball.tail_local - ball.head_local
            v.z = 0.0
            toe += v
        if toe.length < 1e-6:
            toe = Vector((0.0, -1.0, 0.0))
        self.forward = toe.normalized()
        self.right = self.forward.cross(UP).normalized()

    def head_of(self, bone: str) -> Vector:
        return self.rig.rest[bone].translation.copy()

    @property
    def arm_length(self) -> float:
        return self.rig.length["upperarm_l"] + self.rig.length["lowerarm_l"]

    @property
    def leg_length(self) -> float:
        return self.rig.length["thigh_l"] + self.rig.length["calf_l"]

    @property
    def hip(self) -> Vector:
        return self.head_of("pelvis")

    @property
    def chest(self) -> Vector:
        return self.head_of("spine_05")

    @property
    def neck(self) -> Vector:
        return self.head_of("neck_01")

    @property
    def eye_height(self) -> float:
        return self.head_of("head").z + 0.09

    def shoulder(self, side: str) -> Vector:
        return self.head_of(f"upperarm_{side}")

    def foot(self, side: str) -> Vector:
        return self.head_of(f"foot_{side}")

    def elbow_pole(self, side: str) -> Vector:
        """Where the elbow is pushed: behind and below the shoulder, slightly outboard."""
        sign = 1.0 if side == "l" else -1.0
        return (self.shoulder(side) - self.forward * 0.55 - UP * 0.35
                - self.right * (0.20 * sign))

    def knee_pole(self, side: str) -> Vector:
        sign = 1.0 if side == "l" else -1.0
        return self.head_of(f"thigh_{side}") + self.forward * 0.9 - self.right * (0.05 * sign)

    def hand_rotation(self, side: str, finger_dir: Vector, back_dir: Vector) -> Quaternion:
        rest = self.rig.rest[f"hand_{side}"].to_quaternion()
        return pose_solver.orient(rest, finger_dir, back_dir)

    def foot_rotation(self, side: str, toe_dir: Vector, sole_normal: Vector = UP) -> Quaternion:
        rest = self.rig.rest[f"foot_{side}"].to_quaternion()
        return pose_solver.orient(rest, toe_dir, sole_normal)


# ---------------------------------------------------------------------------------- key-pose interpolation
@dataclass
class KeyPose:
    time_s: float
    spec: PoseSpec
    ease: str = "smooth"


def bake_keyposes(rig: Rig, keys: list[KeyPose], *, base: dict[str, Matrix], fps: float = 30.0,
                  loop: bool = False) -> list[dict[str, Matrix]]:
    """Solve each key pose, then sample the sequence at ``fps`` with slerp + easing between keys."""
    if len(keys) < 2:
        raise ValueError("need at least two key poses")
    solved = [(k.time_s, pose_solver.solve_pose(rig, k.spec, base), k.ease) for k in keys]
    duration = solved[-1][0] - solved[0][0]
    n = max(int(round(duration * fps)), 1)
    frames: list[dict[str, Matrix]] = []
    identity = Matrix.Identity(4)
    for i in range(n + 1):
        t = solved[0][0] + duration * i / n
        j = 0
        while j < len(solved) - 2 and t > solved[j + 1][0]:
            j += 1
        t0, basis0, _ = solved[j]
        t1, basis1, ease_kind = solved[j + 1]
        span = max(t1 - t0, 1e-9)
        u = anim_lib.ease(min(max((t - t0) / span, 0.0), 1.0), ease_kind)
        frame: dict[str, Matrix] = {}
        for name in rig.order:
            a = basis0.get(name, identity)
            b = basis1.get(name, identity)
            frame[name] = _blend_basis(a, b, u)
        pose_solver.bake_ik_bones(rig, frame)
        frames.append(frame)
    if loop:
        frames[-1] = {k: v.copy() for k, v in frames[0].items()}
    return frames


def _blend_basis(a: Matrix, b: Matrix, u: float) -> Matrix:
    if u <= 0.0:
        return a.copy()
    if u >= 1.0:
        return b.copy()
    qa, qb = a.to_quaternion(), b.to_quaternion()
    rot = qa.slerp(qb, u).to_matrix().to_4x4()
    loc = a.to_translation().lerp(b.to_translation(), u)
    return Matrix.Translation(loc) @ rot


def blend_frames(a: list[dict[str, Matrix]], b: list[dict[str, Matrix]], bones: set[str],
                 weight: float = 1.0) -> list[dict[str, Matrix]]:
    """Overlay ``b``'s named bones onto ``a``, resampling ``b`` so both cycles complete together.

    Both inputs are single cycles, so ``b`` is stretched onto ``a``'s length rather than indexed modulo its
    own length - otherwise the overlay would end mid-cycle and the result would pop when it loops.
    """
    out: list[dict[str, Matrix]] = []
    identity = Matrix.Identity(4)
    span = max(len(a) - 1, 1)
    for i, frame in enumerate(a):
        other = b[min(round(i * (len(b) - 1) / span), len(b) - 1)]
        merged = {k: v.copy() for k, v in frame.items()}
        for name in bones:
            merged[name] = _blend_basis(frame.get(name, identity), other.get(name, identity), weight)
        out.append(merged)
    return out


# --------------------------------------------------------------------------------------------- car frame
def car_to_body(body: BodyRef, package: car_ref.DriverPackage, point: Vector) -> Vector:
    """Map a point in the car's frame to the character's frame for the seated/entering clips.

    The character's origin sits on the car floor plane directly under the SAE H-point, facing the car's +X.
    """
    rel = point - Vector((package.hip_point.x, package.hip_point.y, 0.0))
    left = -body.right
    return body.forward * rel.x + left * rel.y + UP * rel.z


def car_dir_to_body(body: BodyRef, direction: Vector) -> Vector:
    left = -body.right
    return (body.forward * direction.x + left * direction.y + UP * direction.z).normalized()


# ------------------------------------------------------------------------------------------ pose helpers
def hand_ik(body: BodyRef, side: str, target: Vector, *, finger_dir: Vector | None = None,
            back_dir: Vector | None = None, pole: Vector | None = None) -> dict:
    spec = {"target": target, "pole": pole if pole is not None else body.elbow_pole(side)}
    if finger_dir is not None:
        spec["rotation"] = body.hand_rotation(side, finger_dir, back_dir if back_dir is not None else UP)
    return spec


def foot_ik(body: BodyRef, side: str, target: Vector, *, toe_dir: Vector | None = None,
            sole_normal: Vector = UP, pole: Vector | None = None) -> dict:
    spec = {"target": target, "pole": pole if pole is not None else body.knee_pole(side)}
    spec["rotation"] = body.foot_rotation(side, toe_dir if toe_dir is not None else body.forward, sole_normal)
    return spec


def planted_feet(body: BodyRef, *, stance: float = 0.0, toe_out_deg: float = 7.0) -> dict[str, dict]:
    """Both feet flat on the ground under the hips - what makes a standing clip stand.

    ``stance`` widens the feet beyond their rest separation; ``toe_out_deg`` is the natural outward splay.
    """
    out = {}
    for side in ("l", "r"):
        sign = 1.0 if side == "l" else -1.0
        rest = body.foot(side)
        target = rest - body.right * (stance * 0.5 * sign)
        toe = body.forward.copy()
        toe.rotate(Matrix.Rotation(math.radians(toe_out_deg * sign), 4, "Z"))
        out[f"foot_{side}"] = foot_ik(body, side, target, toe_dir=toe,
                                      pole=body.head_of(f"thigh_{side}") + body.forward * 1.1
                                      - body.right * (0.06 * sign))
    return out


def relaxed_arms(body: BodyRef) -> dict[str, dict]:
    """Arms hanging naturally at the sides, used when a clip does not otherwise place them."""
    out = {}
    for side in ("l", "r"):
        sign = 1.0 if side == "l" else -1.0
        target = (body.shoulder(side) - UP * (body.arm_length * 0.92)
                  + body.right * (0.055 * sign) + body.forward * 0.06)
        out[f"hand_{side}"] = hand_ik(body, side, target,
                                      finger_dir=(-UP * 0.94 + body.forward * 0.34).normalized(),
                                      back_dir=(body.right * -sign))
    return out


# ------------------------------------------------------------------------------------------------ clips
class ProceduralClips:
    """Builds every non-mocap clip for one character."""

    def __init__(self, rig: Rig, body: BodyRef, package: car_ref.DriverPackage,
                 standing: dict[str, Matrix], walk_frames: list[dict[str, Matrix]] | None = None,
                 fps: float = 30.0) -> None:
        self.rig = rig
        self.body = body
        self.car = package
        self.standing = standing
        self.walk = walk_frames or []
        self.fps = fps

    # ------------------------------------------------------------------ standing
    def idle(self) -> Clip:
        body, rig = self.body, self.rig
        n = int(round(4.0 * self.fps))
        frames: list[dict[str, Matrix]] = []
        for i in range(n + 1):
            phase = 2.0 * math.pi * i / n
            breathe = 1.1 * math.sin(phase * 3.0)          # 3 breaths per 4 s cycle = 45 /min
            sway = math.sin(phase)
            spec = PoseSpec(rot={
                "spine_02": (0.35 * breathe, 0.0, 0.0),
                "spine_04": (0.45 * breathe, 0.0, 0.9 * sway),
                "spine_05": (0.30 * breathe, 0.0, 0.6 * sway),
                "neck_01": (-0.3 * breathe, 0.0, -0.5 * sway),
                "head": (0.0, 1.6 * math.sin(phase * 0.5 + 1.1), -1.2 * sway),
                "clavicle_l": (0.0, 0.0, 0.8 * breathe),
                "clavicle_r": (0.0, 0.0, -0.8 * breathe),
            })
            spec.ik = {**relaxed_arms(body), **planted_feet(body)}
            offset = body.right * (0.011 * sway) - UP * (0.004 * abs(sway))
            basis = self._resolve_standing(spec, offset)
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        frames[-1] = {k: v.copy() for k, v in frames[0].items()}
        return Clip(name="idle", frames=frames, fps=self.fps, loop=True,
                    method="hybrid: mocap standing posture + procedural breathing/weight-shift",
                    notes="posture is the mean double-support pose of the retargeted CMU 07_01 walk; "
                          "no idle trial exists in the downloaded CMU set",
                    speed_mps=0.0)

    def idle_phone(self) -> Clip:
        body, rig = self.body, self.rig
        n = int(round(4.0 * self.fps))
        phone = (body.chest + body.forward * 0.30 + UP * 0.06 - body.right * 0.04)
        frames = []
        for i in range(n + 1):
            phase = 2.0 * math.pi * i / n
            breathe = 1.0 * math.sin(phase * 3.0)
            scroll = 0.012 * math.sin(phase * 2.0)
            spec = PoseSpec(rot={
                "spine_02": (0.3 * breathe, 0.0, 0.0),
                "spine_04": (2.5 + 0.4 * breathe, 0.0, 0.0),
                "spine_05": (3.0, 0.0, 0.0),
                "neck_01": (14.0, 0.0, 0.0),
                "neck_02": (8.0, 0.0, 0.0),
                "head": (6.0, 0.0, 1.2 * math.sin(phase * 0.5)),
            })
            spec.ik = {
                "hand_r": hand_ik(body, "r", phone + UP * scroll - body.right * 0.02,
                                  finger_dir=(body.forward * 0.25 + UP * 0.10 - body.right * 0.96).normalized(),
                                  back_dir=(body.forward * -0.2 + UP * 0.95).normalized()),
                "hand_l": hand_ik(body, "l", phone - body.right * 0.10 - UP * 0.05,
                                  finger_dir=(body.forward * 0.20 + body.right * 0.94 + UP * 0.24).normalized(),
                                  back_dir=(body.forward * -0.3 + UP * 0.9).normalized()),
                **planted_feet(body),
            }
            basis = pose_solver.solve_pose(rig, spec, self.standing)
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        frames[-1] = {k: v.copy() for k, v in frames[0].items()}
        return Clip(name="idle_phone", frames=frames, fps=self.fps, loop=True,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="right hand holds the phone 0.30 m in front of the sternum, head pitched 28 deg down")

    def look_around(self) -> Clip:
        body, rig = self.body, self.rig
        keys = []
        sweep = [(0.0, 0.0, 0.0), (0.9, -48.0, -12.0), (1.6, -48.0, -12.0), (2.6, 40.0, 10.0),
                 (3.3, 40.0, 10.0), (4.2, -8.0, -3.0), (5.0, 0.0, 0.0)]
        for t, head_yaw, spine_yaw in sweep:
            spec = PoseSpec(rot={
                "head": (0.0, 0.0, head_yaw * 0.55),
                "neck_02": (0.0, 0.0, head_yaw * 0.28),
                "neck_01": (0.0, 0.0, head_yaw * 0.17),
                "spine_05": (0.0, 0.0, spine_yaw * 0.5),
                "spine_04": (0.0, 0.0, spine_yaw * 0.3),
            })
            spec.ik = {**relaxed_arms(body), **planted_feet(body)}
            keys.append(KeyPose(t, spec, "sine"))
        frames = bake_keyposes(rig, keys, base=self.standing, fps=self.fps, loop=True)
        return Clip(name="look_around", frames=frames, fps=self.fps, loop=True,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="head yaw -48 to +40 deg with 55/28/17 % neck distribution and a torso follow")

    def hail_cab(self) -> Clip:
        body, rig = self.body, self.rig
        raised = (body.shoulder("r") + UP * (body.arm_length * 0.86)
                  + body.forward * (body.arm_length * 0.34) - body.right * 0.16)
        rest_spec = PoseSpec(rot={"head": (0.0, 0.0, -18.0), "neck_01": (0.0, 0.0, -8.0)})
        rest_spec.ik = {**relaxed_arms(body), **planted_feet(body)}
        up_spec = PoseSpec(rot={"spine_04": (-3.0, 0.0, -4.0), "spine_05": (-4.0, 0.0, -6.0),
                                "clavicle_r": (0.0, 0.0, -14.0),
                                "head": (-4.0, 0.0, -22.0), "neck_01": (0.0, 0.0, -10.0)})
        up_spec.ik = {**relaxed_arms(body), **planted_feet(body)}
        up_spec.ik["hand_r"] = hand_ik(body, "r", raised,
                                       finger_dir=(UP * 0.93 + body.forward * 0.3).normalized(),
                                       back_dir=body.forward,
                                       pole=body.shoulder("r") - body.forward * 0.35 - body.right * 0.5)
        wave = up_spec.copy()
        wave.ik["hand_r"] = hand_ik(body, "r", raised + body.right * -0.10 + UP * 0.03,
                                    finger_dir=(UP * 0.9 + body.forward * 0.35 - body.right * 0.25).normalized(),
                                    back_dir=body.forward,
                                    pole=body.shoulder("r") - body.forward * 0.35 - body.right * 0.5)
        keys = [KeyPose(0.0, rest_spec), KeyPose(0.55, up_spec, "out"), KeyPose(1.05, wave, "sine"),
                KeyPose(1.55, up_spec, "sine"), KeyPose(2.05, wave, "sine"),
                KeyPose(2.6, rest_spec, "in")]
        frames = bake_keyposes(rig, keys, base=self.standing, fps=self.fps, loop=True)
        return Clip(name="hail_cab", frames=frames, fps=self.fps, loop=True, method="procedural-keyposed",
                    speed_mps=0.0, notes="right arm to 86 % of arm length above the shoulder, two waves")

    def lean_on_car(self) -> Clip:
        body, rig = self.body, self.rig
        # the car is on the character's left; hip contact at 0.86 m, elbow resting on the belt line
        contact = body.hip + body.right * -0.16 + UP * 0.02
        n = int(round(4.0 * self.fps))
        frames = []
        for i in range(n + 1):
            phase = 2.0 * math.pi * i / n
            breathe = math.sin(phase * 2.5)
            spec = PoseSpec(rot={
                "spine_01": (0.0, 4.0, 0.0), "spine_02": (0.2 * breathe, 4.5, 0.0),
                "spine_03": (0.3 * breathe, 3.0, 0.0), "spine_04": (0.3 * breathe, 1.5, 0.0),
                "spine_05": (0.0, 0.5, 0.0),
                "head": (0.0, -2.0, 6.0 + 1.0 * math.sin(phase * 0.5)),
                "thigh_l": (0.0, -4.0, 0.0), "thigh_r": (-6.0, 3.0, 0.0), "calf_r": (10.0, 0.0, 0.0),
            })
            spec.ik = {
                "hand_l": hand_ik(body, "l", contact - body.right * 0.06 + UP * 0.10 + body.forward * 0.10,
                                  finger_dir=(body.forward * 0.55 - body.right * 0.83).normalized(),
                                  back_dir=UP),
                "hand_r": hand_ik(body, "r", body.chest + body.forward * 0.16 - UP * 0.24 - body.right * 0.03,
                                  finger_dir=(-body.right * 0.9 + body.forward * 0.2 + UP * 0.1).normalized(),
                                  back_dir=body.forward),
            }
            spec.ik.update(planted_feet(body, stance=0.10))
            basis = self._resolve_standing(spec, body.right * -0.055 - UP * 0.035)
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        frames[-1] = {k: v.copy() for k, v in frames[0].items()}
        return Clip(name="lean_on_car", frames=frames, fps=self.fps, loop=True,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="hip against the car's belt line on the character's left, arms folded, weight on "
                          "the left leg")

    def umbrella_hold(self) -> Clip:
        body, rig = self.body, self.rig
        grip = body.shoulder("r") + UP * 0.18 + body.forward * 0.16 - body.right * 0.10
        n = int(round(3.0 * self.fps))
        frames = []
        for i in range(n + 1):
            phase = 2.0 * math.pi * i / n
            spec = PoseSpec(rot={"spine_04": (0.4 * math.sin(phase * 3.0), 0.0, 0.0),
                                 "head": (2.0, 0.0, 2.0 * math.sin(phase * 0.5))})
            spec.ik = {**relaxed_arms(body), **planted_feet(body)}
            spec.ik["hand_r"] = hand_ik(body, "r", grip + UP * (0.008 * math.sin(phase)),
                                        finger_dir=(-body.right * 0.35 + body.forward * 0.3 - UP * 0.88).normalized(),
                                        back_dir=body.forward)
            basis = pose_solver.solve_pose(rig, spec, self.standing)
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        frames[-1] = {k: v.copy() for k, v in frames[0].items()}
        return Clip(name="umbrella_hold", frames=frames, fps=self.fps, loop=True,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="NPC pose: vertical grip 0.18 m above the right shoulder")

    # ------------------------------------------------------------------ gait-derived
    def _walk_base(self) -> list[dict[str, Matrix]]:
        if not self.walk:
            raise RuntimeError("gait-derived clips need the retargeted walk cycle")
        return self.walk

    def turn_90(self, direction: str) -> Clip:
        """A 90-degree pivot: a walk half-cycle with the root yawing and the torso leading."""
        rig, body = self.rig, self.body
        sign = 1.0 if direction == "left" else -1.0
        walk = self._walk_base()
        span = max(len(walk), 2)   # a 90 deg pivot takes one full stride, not a half step
        frames: list[dict[str, Matrix]] = []
        for i in range(span + 1):
            u = i / span
            src = walk[i % len(walk)]
            basis = {k: v.copy() for k, v in src.items()}
            yaw = sign * 90.0 * anim_lib.ease(u, "smooth")
            lead = sign * 16.0 * math.sin(math.pi * u)
            basis["root"] = Matrix.Rotation(math.radians(yaw), 4, "Z")
            for bone, share in (("spine_03", 0.25), ("spine_05", 0.35), ("neck_01", 0.2), ("head", 0.35)):
                extra = Matrix.Rotation(math.radians(lead * share), 4, "Z")
                basis[bone] = basis.get(bone, Matrix.Identity(4)) @ extra
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        return Clip(name=f"turn_{direction}_90", frames=frames, fps=self.fps, loop=False,
                    method="procedural-on-mocap-gait", speed_mps=0.0,
                    notes=f"root yaws {int(sign * 90)} deg over one full walk cycle "
                          f"({span / self.fps:.2f} s) with a 16 deg torso lead")

    def stairs(self, direction: str) -> Clip:
        """Stair cycle: the retargeted walk gait with the swing foot lifted onto a real NYC riser.

        NYC Building Code (2014) §1009.4.2 for interior stairs: riser 4"-7 3/4" (0.197 m max), tread minimum
        11" (0.279 m).  A typical Astoria walk-up stair is 0.18 m x 0.28 m, which is what is used here.
        """
        rig, body = self.rig, self.body
        riser, tread = 0.18, 0.28
        walk = self._walk_base()
        n = len(walk)
        up = direction == "up"
        lean = 9.0 if up else -5.0
        frames: list[dict[str, Matrix]] = []
        for i in range(n):
            basis = {k: v.copy() for k, v in walk[i].items()}
            world = rig.evaluate(basis)
            phase = i / (n - 1) if n > 1 else 0.0
            spec_ik = {}
            for side, offset in (("l", 0.0), ("r", 0.5)):
                p = (phase + offset) % 1.0
                lift = max(math.sin(math.pi * min(p / 0.45, 1.0)), 0.0) if p < 0.45 else 0.0
                base_pos = world[f"foot_{side}"].translation.copy()
                target = base_pos + UP * (riser * lift * (1.0 if up else -0.35)) \
                    + body.forward * (tread * 0.25 * lift)
                toe = (body.forward + UP * (0.30 if up else -0.22)).normalized()
                spec_ik[f"foot_{side}"] = foot_ik(body, side, target, toe_dir=toe)
            spec = PoseSpec(rot={"spine_01": (lean * 0.3, 0.0, 0.0), "spine_03": (lean * 0.4, 0.0, 0.0),
                                 "spine_05": (lean * 0.3, 0.0, 0.0),
                                 "neck_01": (-lean * 0.35, 0.0, 0.0), "head": (-lean * 0.3, 0.0, 0.0)},
                            ik=spec_ik)
            merged = pose_solver.solve_pose(rig, spec, basis)
            pose_solver.bake_ik_bones(rig, merged)
            frames.append(merged)
        frames.append({k: v.copy() for k, v in frames[0].items()})
        return Clip(name=f"stairs_{direction}", frames=frames, fps=self.fps, loop=True,
                    method="procedural-on-mocap-gait", speed_mps=0.0,
                    notes=f"0.18 m riser / 0.28 m tread (NYC BC §1009.4.2 limits 0.197 / 0.279); "
                          f"torso pitched {lean:+.0f} deg")

    def phone_walk(self) -> Clip:
        """Walk with the phone-holding upper body: the NPC's most common Manhattan pose."""
        walk = self._walk_base()
        phone = self.idle_phone()
        upper = {"spine_04", "spine_05", "neck_01", "neck_02", "head",
                 "clavicle_l", "clavicle_r", "upperarm_l", "lowerarm_l", "hand_l",
                 "upperarm_r", "lowerarm_r", "hand_r"}
        frames = blend_frames(walk, phone.frames, upper, weight=0.88)
        frames.append({k: v.copy() for k, v in frames[0].items()})
        for frame in frames:
            pose_solver.bake_ik_bones(self.rig, frame)
        return Clip(name="phone_walk", frames=frames, fps=self.fps, loop=True,
                    method="procedural-on-mocap-gait", speed_mps=1.25,
                    notes="upper body from idle_phone blended 88 % onto the retargeted walk; measured NYC "
                          "phone-walking speed is ~10 % below the free walk speed")

    # ------------------------------------------------------------------ the car
    def _seated_base(self) -> PoseSpec:
        """Legs and pelvis of a driver seated at the SAE H-point with the feet on the pedals."""
        body, car = self.body, self.car
        heel = car_to_body(body, car, car.heel_point)
        pedal_l = heel + body.forward * 0.02 - body.right * -0.10
        pedal_r = heel - body.right * 0.08
        spec = PoseSpec(rot={
            "spine_01": (-6.0, 0.0, 0.0), "spine_02": (-4.0, 0.0, 0.0), "spine_03": (-3.0, 0.0, 0.0),
            "spine_04": (-2.0, 0.0, 0.0), "spine_05": (-1.0, 0.0, 0.0),
            "neck_01": (4.0, 0.0, 0.0), "head": (2.0, 0.0, 0.0),
        })
        spec.ik = {
            "foot_l": foot_ik(body, "l", pedal_l, toe_dir=(body.forward * 0.86 - UP * 0.51).normalized(),
                              pole=body.head_of("thigh_l") + body.forward * 0.55 + UP * 0.30),
            "foot_r": foot_ik(body, "r", pedal_r, toe_dir=(body.forward * 0.86 - UP * 0.51).normalized(),
                              pole=body.head_of("thigh_r") + body.forward * 0.55 + UP * 0.30),
        }
        return spec

    def _seat_pelvis_offset(self) -> Vector:
        """Where the pelvis must move so its bone head lands on the car's H-point."""
        body, car = self.body, self.car
        return car_to_body(body, car, car.hip_point) - body.hip

    def _wheel_hands(self, rotation_deg: float = 0.0, hours: tuple[float, float] = (9.0, 3.0)) -> dict:
        """Hands on the rim at the given clock positions, rotated by ``rotation_deg`` about the column."""
        body, car = self.body, self.car
        axis = car_dir_to_body(body, car.wheel_normal)
        out = {}
        for side, hour in (("l", hours[0]), ("r", hours[1])):
            point = car.rim_point(hour)
            target = car_to_body(body, car, point)
            centre = car_to_body(body, car, car.wheel_centre)
            if abs(rotation_deg) > 1e-6:
                rot = Matrix.Rotation(math.radians(rotation_deg), 4, axis)
                target = centre + rot @ (target - centre)
            radial = (target - centre).normalized()
            tangent = axis.cross(radial).normalized()
            finger = tangent if side == "l" else -tangent
            out[f"hand_{side}"] = hand_ik(body, side, target - radial * 0.012,
                                          finger_dir=finger, back_dir=-radial,
                                          pole=body.shoulder(side) - body.forward * 0.15
                                          - body.right * (0.42 if side == "l" else -0.42) - UP * 0.30)
        return out

    def sit_drive_idle(self) -> Clip:
        rig, body = self.rig, self.body
        offset = self._seat_pelvis_offset()
        n = int(round(3.0 * self.fps))
        frames = []
        for i in range(n + 1):
            phase = 2.0 * math.pi * i / n
            breathe = math.sin(phase * 3.0)
            micro = 2.2 * math.sin(phase)
            spec = self._seated_base()
            spec.rot["spine_04"] = (spec.rot["spine_04"][0] + 0.4 * breathe, 0.0, 0.0)
            spec.rot["head"] = (spec.rot["head"][0], 0.0, 1.2 * math.sin(phase * 0.5))
            spec.ik.update(self._wheel_hands(rotation_deg=micro))
            basis = self._resolve_seated(spec, offset)
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        frames[-1] = {k: v.copy() for k, v in frames[0].items()}
        return Clip(name="sit_drive_idle", frames=frames, fps=self.fps, loop=True,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes=f"hands at nine and three on the {self.car.wheel_radius * 2:.3f} m rim of the "
                          f"exported Fusion Hybrid steering wheel ({self.car.source}); "
                          f"+/-2.2 deg micro-correction")

    def _resolve_standing(self, spec: PoseSpec, offset: Vector) -> dict[str, Matrix]:
        """Solve a standing pose with the pelvis displaced first, so the IK targets stay world-anchored."""
        rig = self.rig
        basis = pose_solver.solve_pose(rig, PoseSpec(rot=dict(spec.rot)), self.standing)
        if offset.length > 0.0:
            _translate_pelvis(rig, basis, offset)
        return pose_solver.solve_pose(rig, PoseSpec(ik=spec.ik), basis)

    def _resolve_seated(self, spec: PoseSpec, offset: Vector) -> dict[str, Matrix]:
        """Solve a seated pose: pelvis is displaced first so the IK targets are reached from the seat."""
        rig = self.rig
        pelvis_only = PoseSpec(rot=dict(spec.rot))
        basis = pose_solver.solve_pose(rig, pelvis_only, self.standing)
        _translate_pelvis(rig, basis, offset)
        limb_spec = PoseSpec(ik=spec.ik)
        return pose_solver.solve_pose(rig, limb_spec, basis)

    def drive_steer(self, direction: str) -> Clip:
        """Additive steering pose: rest -> full lock, exported as a two-key clip."""
        rig, body = self.rig, self.body
        sign = 1.0 if direction == "left" else -1.0
        offset = self._seat_pelvis_offset()
        frames = []
        for amount in (0.0, 1.0):
            spec = self._seated_base()
            spec.ik.update(self._wheel_hands(rotation_deg=sign * 110.0 * amount))
            spec.rot["spine_04"] = (spec.rot["spine_04"][0], 0.0, sign * 4.0 * amount)
            spec.rot["spine_05"] = (spec.rot["spine_05"][0], 0.0, sign * 5.0 * amount)
            spec.rot["clavicle_l"] = (0.0, 0.0, -3.0 * sign * amount)
            spec.rot["clavicle_r"] = (0.0, 0.0, -3.0 * sign * amount)
            basis = self._resolve_seated(spec, offset)
            pose_solver.bake_ik_bones(rig, basis)
            frames.append(basis)
        return Clip(name=f"drive_steer_{direction}", frames=frames, fps=self.fps, loop=False, additive=True,
                    method="procedural-keyposed (additive)", speed_mps=0.0,
                    notes=f"frame 0 = neutral reference, frame 1 = {int(sign * 110)} deg of rim rotation; "
                          f"the runtime blends it additively against sit_drive_idle")

    def drive_shift(self) -> Clip:
        rig, body, car = self.rig, self.body, self.car
        offset = self._seat_pelvis_offset()
        knob = car_to_body(body, car, car.shifter_knob)
        neutral = self._seated_base()
        neutral.ik.update(self._wheel_hands())
        grip = self._seated_base()
        grip.ik.update(self._wheel_hands())
        grip.ik["hand_r"] = hand_ik(body, "r", knob + UP * 0.02,
                                    finger_dir=(body.forward * 0.25 - UP * 0.94 - body.right * 0.23).normalized(),
                                    back_dir=(body.forward * 0.9 + UP * 0.3).normalized(),
                                    pole=body.shoulder("r") - body.forward * 0.1 + body.right * 0.45 - UP * 0.3)
        grip.rot["spine_05"] = (grip.rot["spine_05"][0], 0.0, -6.0)
        pulled = grip.copy()
        pulled.ik["hand_r"] = hand_ik(body, "r", knob + UP * 0.02 - body.forward * 0.075,
                                      finger_dir=(body.forward * 0.25 - UP * 0.94 - body.right * 0.23).normalized(),
                                      back_dir=(body.forward * 0.9 + UP * 0.3).normalized(),
                                      pole=body.shoulder("r") - body.forward * 0.1 + body.right * 0.45 - UP * 0.3)
        keys = [(0.0, neutral), (0.38, grip), (0.62, pulled), (1.05, neutral)]
        frames = []
        solved = [(t, self._resolve_seated(s, offset)) for t, s in keys]
        total = solved[-1][0]
        n = int(round(total * self.fps))
        for i in range(n + 1):
            t = total * i / n
            j = 0
            while j < len(solved) - 2 and t > solved[j + 1][0]:
                j += 1
            t0, b0 = solved[j]
            t1, b1 = solved[j + 1]
            u = anim_lib.ease((t - t0) / max(t1 - t0, 1e-9), "smooth")
            frame = {k: _blend_basis(b0.get(k, Matrix.Identity(4)), b1.get(k, Matrix.Identity(4)), u)
                     for k in rig.order}
            pose_solver.bake_ik_bones(rig, frame)
            frames.append(frame)
        return Clip(name="drive_shift", frames=frames, fps=self.fps, loop=False,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="right hand leaves the rim for the console shifter knob at "
                          f"{tuple(round(v, 3) for v in car.shifter_knob)} in the car frame and returns")

    def drive_look(self, name: str, head_yaw: float, head_pitch: float, torso: float,
                   duration: float = 1.2) -> Clip:
        rig = self.rig
        offset = self._seat_pelvis_offset()
        neutral = self._seated_base()
        neutral.ik.update(self._wheel_hands())
        turned = self._seated_base()
        turned.ik.update(self._wheel_hands())
        turned.rot["head"] = (head_pitch, 0.0, head_yaw * 0.45)
        turned.rot["neck_02"] = (head_pitch * 0.3, 0.0, head_yaw * 0.28)
        turned.rot["neck_01"] = (head_pitch * 0.2, 0.0, head_yaw * 0.17)
        turned.rot["spine_05"] = (turned.rot["spine_05"][0], 0.0, torso * 0.55)
        turned.rot["spine_04"] = (turned.rot["spine_04"][0], 0.0, torso * 0.30)
        turned.rot["spine_03"] = (turned.rot["spine_03"][0], 0.0, torso * 0.15)
        solved = [(0.0, self._resolve_seated(neutral, offset)),
                  (duration * 0.35, self._resolve_seated(turned, offset)),
                  (duration * 0.65, self._resolve_seated(turned, offset)),
                  (duration, self._resolve_seated(neutral, offset))]
        n = int(round(duration * self.fps))
        frames = []
        for i in range(n + 1):
            t = duration * i / n
            j = 0
            while j < len(solved) - 2 and t > solved[j + 1][0]:
                j += 1
            t0, b0 = solved[j]
            t1, b1 = solved[j + 1]
            u = anim_lib.ease((t - t0) / max(t1 - t0, 1e-9), "sine")
            frame = {k: _blend_basis(b0.get(k, Matrix.Identity(4)), b1.get(k, Matrix.Identity(4)), u)
                     for k in rig.order}
            pose_solver.bake_ik_bones(rig, frame)
            frames.append(frame)
        return Clip(name=name, frames=frames, fps=self.fps, loop=False, method="procedural-keyposed",
                    speed_mps=0.0,
                    notes=f"head yaw {head_yaw:+.0f} deg (45/28/17 % across head/neck_02/neck_01), "
                          f"torso {torso:+.0f} deg")

    # ------------------------------------------------------------------ door / entry / exit
    def open_car_door(self) -> Clip:
        rig, body, car = self.rig, self.body, self.car
        # the character faces the car: the handle is to the character's front-left at hip-plus height
        handle = body.hip + body.forward * 0.46 + UP * (car.door_handle.z - car.hip_point.z + 0.10)
        stand = PoseSpec()
        stand.ik = {**relaxed_arms(body), **planted_feet(body)}
        reach = PoseSpec(rot={"spine_03": (5.0, 0.0, -6.0), "spine_05": (4.0, 0.0, -8.0),
                              "clavicle_r": (0.0, 0.0, -10.0), "head": (4.0, 0.0, -6.0)})
        reach.ik = {**relaxed_arms(body), **planted_feet(body)}
        reach.ik["hand_r"] = hand_ik(body, "r", handle,
                                     finger_dir=body.forward,
                                     back_dir=UP,
                                     pole=body.shoulder("r") - body.forward * 0.2 + body.right * 0.45 - UP * 0.4)
        pull = reach.copy()
        pull.rot = dict(reach.rot)
        pull.rot["spine_03"] = (2.0, 0.0, 4.0)
        pull.rot["spine_05"] = (1.0, 0.0, 6.0)
        pull.ik["hand_r"] = hand_ik(body, "r", handle - body.forward * 0.30 + body.right * 0.10,
                                    finger_dir=body.forward, back_dir=UP,
                                    pole=body.shoulder("r") - body.forward * 0.2 + body.right * 0.45 - UP * 0.4)
        back = PoseSpec(rot={"spine_03": (0.0, 0.0, 3.0)})
        back.ik = {**relaxed_arms(body), **planted_feet(body)}
        keys = [KeyPose(0.0, stand), KeyPose(0.55, reach, "out"), KeyPose(1.05, pull, "smooth"),
                KeyPose(1.75, back, "in")]
        frames = bake_keyposes(rig, keys, base=self.standing, fps=self.fps)
        # step back with the right foot while pulling
        for i, frame in enumerate(frames):
            u = anim_lib.ease(min(max((i / self.fps - 0.6) / 0.7, 0.0), 1.0), "smooth")
            _translate_pelvis(rig, frame, -body.forward * (0.14 * u) + body.right * (0.06 * u))
            pose_solver.bake_ik_bones(rig, frame)
        return Clip(name="open_car_door", frames=frames, fps=self.fps, loop=False,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes=f"right hand to the exported door handle height "
                          f"({car.door_handle.z:.2f} m above the car floor), 0.30 m pull, 0.14 m step back")

    def close_door(self) -> Clip:
        rig, body, car = self.rig, self.body, self.car
        edge = body.hip + body.forward * 0.30 + body.right * -0.16 + UP * 0.20
        stand = PoseSpec()
        stand.ik = {**relaxed_arms(body), **planted_feet(body)}
        grab = PoseSpec(rot={"spine_03": (3.0, 0.0, 5.0), "spine_05": (3.0, 0.0, 7.0),
                             "clavicle_l": (0.0, 0.0, 9.0), "head": (3.0, 0.0, 8.0)})
        grab.ik = {**relaxed_arms(body), **planted_feet(body)}
        grab.ik["hand_l"] = hand_ik(body, "l", edge,
                                    finger_dir=(body.forward * 0.4 - body.right * 0.9).normalized(),
                                    back_dir=UP,
                                    pole=body.shoulder("l") - body.forward * 0.25 - body.right * 0.45 - UP * 0.35)
        push = grab.copy()
        push.rot = dict(grab.rot)
        push.rot["spine_03"] = (0.0, 0.0, -3.0)
        push.rot["spine_05"] = (0.0, 0.0, -4.0)
        push.ik["hand_l"] = hand_ik(body, "l", edge + body.forward * 0.06 + body.right * -0.30,
                                    finger_dir=(body.forward * 0.4 - body.right * 0.9).normalized(),
                                    back_dir=UP,
                                    pole=body.shoulder("l") - body.forward * 0.25 - body.right * 0.45 - UP * 0.35)
        keys = [KeyPose(0.0, stand), KeyPose(0.45, grab, "out"), KeyPose(0.85, push, "in"),
                KeyPose(1.40, stand, "smooth")]
        frames = bake_keyposes(rig, keys, base=self.standing, fps=self.fps)
        return Clip(name="close_door", frames=frames, fps=self.fps, loop=False,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="left hand takes the inner door edge and swings it 0.30 m shut")

    def _entry_keys(self) -> tuple[list[KeyPose], Vector]:
        rig, body, car = self.rig, self.body, self.car
        seat_offset = self._seat_pelvis_offset()
        roof = body.hip + body.forward * 0.40 + UP * (car.roof_rail.z - car.hip_point.z)
        sill_side = body.hip + body.forward * 0.28 + body.right * -0.10

        stand = PoseSpec()
        stand.ik = {**relaxed_arms(body), **planted_feet(body)}

        brace = PoseSpec(rot={"spine_03": (10.0, 0.0, -5.0), "spine_05": (8.0, 0.0, -8.0),
                              "neck_01": (-6.0, 0.0, 0.0), "head": (-4.0, 0.0, -8.0)})
        brace.ik = {**relaxed_arms(body), **planted_feet(body)}
        brace.ik["hand_l"] = hand_ik(body, "l", roof,
                                     finger_dir=(body.forward * 0.75 + UP * 0.66).normalized(), back_dir=UP,
                                     pole=body.shoulder("l") - body.forward * 0.2 - body.right * 0.5 - UP * 0.4)
        brace.ik["hand_r"] = hand_ik(body, "r", sill_side + UP * 0.16,
                                     finger_dir=body.forward, back_dir=UP)

        step_in = brace.copy()
        step_in.rot = dict(brace.rot)
        step_in.rot["spine_01"] = (14.0, 0.0, 0.0)
        step_in.ik = dict(brace.ik)
        step_in.ik["foot_r"] = foot_ik(body, "r",
                                       car_to_body(body, car, car.heel_point) + UP * 0.10,
                                       toe_dir=(body.forward * 0.94 - UP * 0.34).normalized(),
                                       pole=body.head_of("thigh_r") + body.forward * 0.7 + UP * 0.4)

        seated = self._seated_base()
        seated.ik.update(self._wheel_hands())
        return [KeyPose(0.0, stand), KeyPose(0.55, brace, "out"), KeyPose(1.25, step_in, "smooth"),
                KeyPose(2.05, seated, "smooth"), KeyPose(2.60, seated, "smooth")], seat_offset

    def enter_car(self) -> Clip:
        rig, body = self.rig, self.body
        keys, seat_offset = self._entry_keys()
        frames = self._bake_transition(keys, seat_offset, forward=True)
        return Clip(name="enter_car", frames=frames, fps=self.fps, loop=False,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="left hand on the roof rail, right hand on the sill, right foot into the footwell, "
                          "hips lowered onto the SAE H-point read from the exported Fusion")

    def exit_car(self) -> Clip:
        keys, seat_offset = self._entry_keys()
        frames = self._bake_transition(keys, seat_offset, forward=False)
        return Clip(name="exit_car", frames=frames, fps=self.fps, loop=False,
                    method="procedural-keyposed", speed_mps=0.0,
                    notes="time-reverse of enter_car with a 15 % faster rise (measured ingress/egress "
                          "asymmetry); the hands leave the wheel first")

    def _bake_transition(self, keys: list[KeyPose], seat_offset: Vector, *, forward: bool
                         ) -> list[dict[str, Matrix]]:
        rig = self.rig
        total = keys[-1].time_s
        solved = []
        for key in keys:
            u = min(max(key.time_s / total, 0.0), 1.0)
            weight = anim_lib.ease(min(u / 0.8, 1.0), "smooth")
            basis = pose_solver.solve_pose(rig, PoseSpec(rot=dict(key.spec.rot)), self.standing)
            _translate_pelvis(rig, basis, seat_offset * weight)
            basis = pose_solver.solve_pose(rig, PoseSpec(ik=key.spec.ik), basis)
            solved.append((key.time_s, basis, key.ease))
        n = int(round(total * self.fps))
        frames = []
        for i in range(n + 1):
            t = total * i / n
            j = 0
            while j < len(solved) - 2 and t > solved[j + 1][0]:
                j += 1
            t0, b0, _ = solved[j]
            t1, b1, ease_kind = solved[j + 1]
            u = anim_lib.ease((t - t0) / max(t1 - t0, 1e-9), ease_kind)
            frame = {k: _blend_basis(b0.get(k, Matrix.Identity(4)), b1.get(k, Matrix.Identity(4)), u)
                     for k in rig.order}
            pose_solver.bake_ik_bones(rig, frame)
            frames.append(frame)
        if not forward:
            frames.reverse()
            # egress is measurably quicker than ingress: resample to 87 % of the duration
            step = max(int(round(len(frames) * 0.87)), 2)
            frames = [frames[round(i * (len(frames) - 1) / (step - 1))] for i in range(step)]
        return frames

    # ------------------------------------------------------------------ everything
    def build_all(self) -> list[Clip]:
        clips = [self.idle(), self.idle_phone(), self.look_around(), self.hail_cab(), self.lean_on_car(),
                 self.umbrella_hold(), self.turn_90("left"), self.turn_90("right"),
                 self.stairs("up"), self.stairs("down"), self.phone_walk(),
                 self.open_car_door(), self.enter_car(), self.sit_drive_idle(),
                 self.drive_steer("left"), self.drive_steer("right"), self.drive_shift(),
                 self.drive_look("drive_shoulder_check_left", 78.0, -2.0, 26.0),
                 self.drive_look("drive_shoulder_check_right", -78.0, -2.0, -26.0),
                 self.drive_look("drive_mirror_check", -20.0, -5.0, -5.0, duration=1.0),
                 self.exit_car(), self.close_door()]
        return clips


def _translate_pelvis(rig: Rig, basis: dict[str, Matrix], offset: Vector) -> None:
    """Move the pelvis by ``offset`` in armature space, keeping its rotation."""
    world = rig.evaluate(basis)
    desired = Matrix.Translation(offset) @ world["pelvis"]
    basis["pelvis"] = rig.base_matrix("pelvis", world).inverted() @ desired
