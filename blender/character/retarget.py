"""Retarget CMU ASF/AMC motion capture onto the NYCSim UE5 skeleton.

The two skeletons share nothing but topology, so the retarget works in *world rotation deltas*:

``delta_i(f) = A . (R_src_i(f) . R_src_i(rest)^-1) . A^-1``   and   ``R_tgt_i(f) = delta_i(f) . R_tgt_i(rest)``

where ``A`` is a yaw that aligns the source subject's travel direction with the target's forward axis (+X in
Blender for this lane).  Because only the *change* from each skeleton's own rest pose is transferred, the
difference in limb proportions, shoulder width and A-pose angle between the CMU subject and the MakeHuman body
never leaks into the result.

On top of the rotation transfer:

* the pelvis height above the ground is transferred as a **ratio of leg length**, so a 0.81 m-legged CMU
  subject drives a 0.88 m-legged character without the feet floating or sinking;
* horizontal travel is removed (game locomotion is authored in place, with the measured ground speed recorded
  in the clip metadata) while the lateral sway and the vertical bob are kept;
* the clip is cut to a whole gait cycle at a left heel strike and resampled to 30 fps so that the last frame
  equals the first;
* playback rate is chosen so the character's ground speed matches the clip's spec (1.4 / 2.8 / 5.0 m/s).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from mathutils import Matrix, Quaternion, Vector

import asf_amc
import pose_solver
import ue5_skeleton as ue5

log = logging.getLogger("nycsim.character.retarget")

SOURCE_FPS = 120.0            # every CMU trial in this set is captured at 120 Hz
OUTPUT_FPS = 30.0


def _to_blender_rotation(matrix: np.ndarray) -> Quaternion:
    """ASF-frame rotation matrix -> Blender-frame quaternion."""
    b = asf_amc.BASIS_ASF_TO_BLENDER
    m = b @ matrix @ b.T
    return Matrix(((m[0][0], m[0][1], m[0][2]), (m[1][0], m[1][1], m[1][2]),
                   (m[2][0], m[2][1], m[2][2]))).to_quaternion()


@dataclass
class SourceClip:
    """A parsed CMU clip with the derived quantities the retargeter needs."""

    name: str
    asf: Path
    amc: Path
    skeleton: asf_amc.Skeleton
    frames: list[dict[str, list[float]]]
    rotations: list[dict[str, Quaternion]]
    rest_rotations: dict[str, Quaternion]
    positions: dict[str, np.ndarray]          # (n_frames, 3) metres, Blender axes
    speed_mps: float
    travel_yaw_rad: float
    leg_length_m: float

    @property
    def n_frames(self) -> int:
        return len(self.frames)


def load_source(asf_path: str | Path, amc_path: str | Path) -> SourceClip:
    asf_path, amc_path = Path(asf_path), Path(amc_path)
    skeleton = asf_amc.parse_asf(asf_path)
    frames = asf_amc.parse_amc(amc_path)
    scale = skeleton.unit_to_m()

    rest = skeleton.rest_rotations()
    rest_q = {name: _to_blender_rotation(rest[name]) for name in rest}

    rotations: list[dict[str, Quaternion]] = []
    positions: dict[str, list[np.ndarray]] = {name: [] for name in skeleton.order}
    for frame in frames:
        pos, rot = skeleton.fk(frame)
        rotations.append({name: _to_blender_rotation(rot[name]) for name in rot})
        for name in skeleton.order:
            positions[name].append(asf_amc.asf_to_blender(pos[name]) * scale)
    pos_arr = {k: np.asarray(v) for k, v in positions.items()}

    root = pos_arr["root"]
    delta = root[-1, :2] - root[0, :2]
    travel_yaw = math.atan2(float(delta[1]), float(delta[0])) if np.linalg.norm(delta) > 1e-6 else 0.0
    speed = asf_amc.root_speed_mps(skeleton, frames, fps=SOURCE_FPS)
    return SourceClip(name=amc_path.stem, asf=asf_path, amc=amc_path, skeleton=skeleton, frames=frames,
                      rotations=rotations, rest_rotations=rest_q, positions=pos_arr, speed_mps=speed,
                      travel_yaw_rad=travel_yaw,
                      leg_length_m=skeleton.chain_length_m(ue5.CMU_LEG_CHAIN))


# ------------------------------------------------------------------------------------------- gait analysis
def heel_strikes(clip: SourceClip, foot: str = "lfoot") -> list[int]:
    """Frame indices of heel strikes for one foot: local minima of the foot's height above the floor."""
    z = clip.positions[foot][:, 2]
    floor = float(np.percentile(z, 2.0))
    height = z - floor
    strikes: list[int] = []
    window = max(int(SOURCE_FPS * 0.15), 3)
    for i in range(window, len(height) - window):
        local = height[i - window:i + window + 1]
        if height[i] <= local.min() + 1e-6 and height[i] < 0.05:
            if not strikes or i - strikes[-1] > window:
                strikes.append(i)
    return strikes


def gait_cycle(clip: SourceClip) -> tuple[int, int]:
    """(start, end) source-frame indices spanning exactly one full stride (left heel strike to the next)."""
    strikes = heel_strikes(clip, "lfoot")
    if len(strikes) >= 2:
        # take the pair closest to the middle of the clip - the ends contain the acceleration phase
        mid = clip.n_frames // 2
        best = min(range(len(strikes) - 1), key=lambda i: abs((strikes[i] + strikes[i + 1]) // 2 - mid))
        return strikes[best], strikes[best + 1]
    # fall back on autocorrelation of the left/right foot separation along the travel direction
    dir_vec = np.array([math.cos(clip.travel_yaw_rad), math.sin(clip.travel_yaw_rad)])
    sep = (clip.positions["lfoot"][:, :2] - clip.positions["rfoot"][:, :2]) @ dir_vec
    sep = sep - sep.mean()
    n = len(sep)
    lo, hi = int(SOURCE_FPS * 0.3), int(SOURCE_FPS * 2.0)
    hi = min(hi, n - 2)
    if hi <= lo:
        return 0, n - 1
    scores = [float(np.dot(sep[:n - lag], sep[lag:]) / (n - lag)) for lag in range(lo, hi)]
    period = lo + int(np.argmax(scores))
    start = max((n - period) // 2, 0)
    return start, start + period


# -------------------------------------------------------------------------------------------- retargeting
@dataclass
class RetargetResult:
    """One finished clip: per-frame basis matrices ready to key onto the rig."""

    name: str
    frames: list[dict[str, Matrix]]
    fps: float
    source: str
    source_speed_mps: float
    equivalent_speed_mps: float
    target_speed_mps: float
    time_scale: float
    cycle_frames_source: int
    method: str


def retarget(clip: SourceClip, rig: pose_solver.Rig, *, name: str, target_speed_mps: float | None,
             forward_yaw_deg: float = 0.0, loop: bool = True, root_motion: bool = False) -> RetargetResult:
    """Retarget one CMU clip onto ``rig``.

    ``forward_yaw_deg`` is the yaw of the *target* character's forward axis in the Blender scene (this lane
    builds the character facing +X, so 0).  ``target_speed_mps`` of ``None`` keeps the natural speed.
    """
    align_yaw = forward_yaw_deg * math.pi / 180.0 - clip.travel_yaw_rad
    align = Quaternion(Vector((0.0, 0.0, 1.0)), align_yaw)
    align_inv = align.inverted()

    rest_world = rig.rest_world()
    tgt_rest_q = {name_: rest_world[name_].to_quaternion() for name_ in rig.order}
    leg_tgt = (rig.rest["thigh_l"].translation - rig.rest["foot_l"].translation).length
    leg_ratio = leg_tgt / max(clip.leg_length_m, 1e-6)
    equivalent_speed = clip.speed_mps * leg_ratio

    if target_speed_mps is None or equivalent_speed < 1e-3:
        time_scale = 1.0
        achieved = equivalent_speed
    else:
        time_scale = target_speed_mps / equivalent_speed
        achieved = target_speed_mps

    start, end = gait_cycle(clip) if loop else (0, clip.n_frames - 1)
    cycle_src = max(end - start, 1)
    duration_out = (cycle_src / SOURCE_FPS) / max(time_scale, 1e-6)
    n_out = max(int(round(duration_out * OUTPUT_FPS)), 2)

    floor = float(np.percentile(np.concatenate([clip.positions["lfoot"][:, 2],
                                                clip.positions["rfoot"][:, 2]]), 2.0))
    pelvis_rest_z = rest_world["pelvis"].translation.z
    root_track = clip.positions["root"]
    travel_dir = np.array([math.cos(clip.travel_yaw_rad), math.sin(clip.travel_yaw_rad)])
    lateral_dir = np.array([-travel_dir[1], travel_dir[0]])
    forward_offsets = root_track[:, :2] @ travel_dir
    lateral_offsets = root_track[:, :2] @ lateral_dir
    lateral_mid = float(lateral_offsets[start:end + 1].mean())

    frames_out: list[dict[str, Matrix]] = []
    for i in range(n_out):
        t = start + (cycle_src * i / n_out if loop else (clip.n_frames - 1) * i / max(n_out - 1, 1))
        basis = _retarget_frame(clip, rig, rest_world, tgt_rest_q, align, align_inv, t)
        # pelvis placement
        f0, f1, frac = _lerp_index(t, clip.n_frames)
        pelvis_z = (root_track[f0, 2] * (1 - frac) + root_track[f1, 2] * frac - floor) * leg_ratio
        lateral = (lateral_offsets[f0] * (1 - frac) + lateral_offsets[f1] * frac - lateral_mid) * leg_ratio
        forward = 0.0
        if root_motion:
            forward = float((forward_offsets[f0] * (1 - frac) + forward_offsets[f1] * frac
                             - forward_offsets[start]) * leg_ratio)
        world = rig.evaluate(basis)
        desired = Matrix.Translation(Vector((forward, lateral, pelvis_z))) @ world["pelvis"].to_3x3().to_4x4()
        basis["pelvis"] = rig.base_matrix("pelvis", world).inverted() @ desired
        pose_solver.bake_ik_bones(rig, basis)
        frames_out.append(basis)

    if loop:
        frames_out.append({k: v.copy() for k, v in frames_out[0].items()})

    log.info("%s: %s -> %d frames @%g fps, source %.2f m/s, equivalent %.2f m/s, time scale %.3f",
             name, clip.name, len(frames_out), OUTPUT_FPS, clip.speed_mps, equivalent_speed, time_scale)
    return RetargetResult(name=name, frames=frames_out, fps=OUTPUT_FPS, source=clip.amc.name,
                          source_speed_mps=clip.speed_mps, equivalent_speed_mps=equivalent_speed,
                          target_speed_mps=achieved, time_scale=time_scale, cycle_frames_source=cycle_src,
                          method="cmu-mocap-retarget")


def _lerp_index(t: float, n: int) -> tuple[int, int, float]:
    f0 = int(math.floor(t)) % n
    f1 = (f0 + 1) % n
    return f0, f1, t - math.floor(t)


def _retarget_frame(clip: SourceClip, rig: pose_solver.Rig, rest_world: dict[str, Matrix],
                    tgt_rest_q: dict[str, Quaternion], align: Quaternion, align_inv: Quaternion,
                    t: float) -> dict[str, Matrix]:
    f0, f1, frac = _lerp_index(t, clip.n_frames)
    src0, src1 = clip.rotations[f0], clip.rotations[f1]

    deltas: dict[str, Quaternion] = {}
    for src_name, tgt_name in ue5.CMU_TO_UE5.items():
        if src_name not in src0 or tgt_name not in tgt_rest_q:
            continue
        q = src0[src_name].slerp(src1[src_name], frac) if frac > 0.0 else src0[src_name].copy()
        delta = q @ clip.rest_rotations[src_name].inverted()
        deltas[tgt_name] = align @ delta @ align_inv
    for tgt_name, (a, b, blend) in ue5.CMU_SPINE_FANOUT.items():
        if a in deltas and b in deltas:
            deltas[tgt_name] = deltas[a].slerp(deltas[b], blend)

    basis: dict[str, Matrix] = {}
    world: dict[str, Matrix] = {}
    for name in rig.order:
        base = rig.base_matrix(name, world)
        if name in deltas:
            desired = (deltas[name] @ tgt_rest_q[name]).to_matrix().to_4x4()
            basis[name] = base.to_3x3().to_4x4().inverted() @ desired
        else:
            basis[name] = Matrix.Identity(4)
        world[name] = base @ basis[name]

    # fingers: CMU has a single curl channel per hand plus a two-axis thumb
    for src_name, (bones, gain) in ue5.CMU_FINGER_DRIVERS.items():
        vals0 = clip.frames[f0].get(src_name)
        vals1 = clip.frames[f1].get(src_name)
        if not vals0:
            continue
        vals = [v0 * (1 - frac) + (v1 if vals1 else v0) * frac for v0, v1 in zip(vals0, vals1 or vals0)]
        curl = math.radians(vals[0] * gain)
        spread = math.radians(vals[1] * gain) if len(vals) > 1 else 0.0
        for bone in bones:
            if bone not in rig.rest:
                continue
            rot = Matrix.Rotation(-curl, 4, "X")
            if spread and bone.endswith(("01_l", "01_r")):
                rot = rot @ Matrix.Rotation(spread, 4, "Z")
            basis[bone] = rot
    return basis


# ------------------------------------------------------------------------------- idle from locomotion mocap
def standing_pose_from_locomotion(clip: SourceClip, rig: pose_solver.Rig,
                                  forward_yaw_deg: float = 0.0) -> dict[str, Matrix]:
    """A standing posture derived from the double-support instants of a walk clip.

    The fourteen CMU files downloaded for this build contain no standing/idle trial (the slowest 0.25 s
    rolling root speed across all nine AMC clips is 1.03 m/s), so the idle's *posture* is taken from the real
    mocap and only its *motion* is authored procedurally.

    The posture is the circular mean of every bone's rotation over one whole gait cycle.  Averaging a full
    cycle - not just the double-support instants - is what makes it a *stance*: the forward and backward
    halves of each swing cancel, so the legs come under the hips and the arms hang, while the spine, neck and
    shoulder carriage that the subject actually held are preserved.
    """
    start, end = gait_cycle(clip)
    candidates = np.arange(start, end + 1)

    align = Quaternion(Vector((0.0, 0.0, 1.0)), forward_yaw_deg * math.pi / 180.0 - clip.travel_yaw_rad)
    align_inv = align.inverted()
    rest_world = rig.rest_world()
    tgt_rest_q = {n: rest_world[n].to_quaternion() for n in rig.order}

    accum: dict[str, list[Quaternion]] = {}
    for idx in candidates:
        src = clip.rotations[int(idx)]
        for src_name, tgt_name in ue5.CMU_TO_UE5.items():
            if src_name not in src or tgt_name not in tgt_rest_q:
                continue
            delta = align @ (src[src_name] @ clip.rest_rotations[src_name].inverted()) @ align_inv
            accum.setdefault(tgt_name, []).append(delta)

    deltas = {name: _average_quaternion(qs) for name, qs in accum.items()}
    for tgt_name, (a, b, blend) in ue5.CMU_SPINE_FANOUT.items():
        if a in deltas and b in deltas:
            deltas[tgt_name] = deltas[a].slerp(deltas[b], blend)

    basis: dict[str, Matrix] = {}
    world: dict[str, Matrix] = {}
    for name in rig.order:
        base = rig.base_matrix(name, world)
        if name in deltas:
            desired = (deltas[name] @ tgt_rest_q[name]).to_matrix().to_4x4()
            basis[name] = base.to_3x3().to_4x4().inverted() @ desired
        else:
            basis[name] = Matrix.Identity(4)
        world[name] = base @ basis[name]
    return basis


def _average_quaternion(quats: list[Quaternion]) -> Quaternion:
    """Chordal L2 mean of unit quaternions (sign-aligned accumulation, then normalise)."""
    if not quats:
        return Quaternion((1.0, 0.0, 0.0, 0.0))
    ref = quats[0]
    acc = np.zeros(4)
    for q in quats:
        vec = np.array([q.w, q.x, q.y, q.z])
        if np.dot(vec, np.array([ref.w, ref.x, ref.y, ref.z])) < 0:
            vec = -vec
        acc += vec
    acc /= max(np.linalg.norm(acc), 1e-12)
    return Quaternion((float(acc[0]), float(acc[1]), float(acc[2]), float(acc[3])))
