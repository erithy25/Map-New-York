"""Parser and forward-kinematics solver for CMU Graphics Lab ASF/AMC motion capture.

The CMU database ships one ``<subject>.asf`` skeleton per subject and one ``<subject>_<trial>.amc`` per clip.
Nothing in the wild reads these for us, so this module is a complete implementation:

* :func:`parse_asf` - ``:units``, ``:root``, ``:bonedata`` (id/name/direction/length/axis/dof/limits) and
  ``:hierarchy``;
* :func:`parse_amc` - the per-frame channel values, honouring ``:DEGREES``/``:RADIANS``;
* :class:`Skeleton.fk` - world-space joint positions and bone rotation matrices per frame.

Conventions
-----------
ASF is Y-up and right-handed, lengths are in the file's own unit (CMU: ``length 0.45``, data authored in inches,
so one ASF unit is ``2.54 cm / 0.45``).  :data:`CMU_UNIT_TO_M` converts to metres and :func:`asf_to_blender`
rotates Y-up to Blender's Z-up: ``(x, y, z) -> (x, -z, y)``.

ASF bone transform (the standard formulation):  every bone carries a fixed local frame ``C`` built from its
``axis`` Euler triple, and the AMC channels give an Euler rotation ``R`` in that frame.  The bone's world
rotation is ``W_i = W_parent . C_i . R_i . C_i^-1`` and its distal joint sits at
``p_i = p_parent + length_i * W_i . direction_i``.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

#: metres per ASF length unit for the CMU database (``:units length 0.45``, source data in inches).
CMU_UNIT_TO_M = 2.54 / 100.0 / 0.45

_AXIS_ORDER_RE = re.compile(r"[XYZ]{3}")


def _rot(axis: str, angle_rad: float) -> np.ndarray:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    if axis == "X":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)
    if axis == "Y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)
    if axis == "Z":
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)
    raise ValueError(f"bad axis {axis!r}")


def euler_to_matrix(angles_rad: tuple[float, float, float] | np.ndarray, order: str = "XYZ") -> np.ndarray:
    """Rotation matrix for intrinsic Euler angles applied in ``order`` (first letter applied first).

    ``order='XYZ'`` therefore yields ``Rz @ Ry @ Rx`` - the same convention as Blender's ``Euler(..., 'XYZ')``.
    ``angles_rad`` is always indexed X, Y, Z regardless of ``order``.
    """
    idx = {"X": 0, "Y": 1, "Z": 2}
    m = np.eye(3, dtype=np.float64)
    for letter in order:                       # first letter applied first => pre-multiplied last
        m = _rot(letter, float(angles_rad[idx[letter]])) @ m
    return m


def asf_to_blender(v: np.ndarray) -> np.ndarray:
    """Y-up right-handed (ASF) -> Z-up right-handed (Blender): ``(x, y, z) -> (x, -z, y)``."""
    v = np.asarray(v, dtype=np.float64)
    out = np.empty_like(v)
    out[..., 0] = v[..., 0]
    out[..., 1] = -v[..., 2]
    out[..., 2] = v[..., 1]
    return out


#: Basis change matrix that maps an ASF-frame rotation to the Blender frame: ``R_blender = B @ R_asf @ B.T``.
BASIS_ASF_TO_BLENDER = np.array([[1.0, 0.0, 0.0],
                                 [0.0, 0.0, -1.0],
                                 [0.0, 1.0, 0.0]], dtype=np.float64)


@dataclass
class AsfBone:
    """One ``:bonedata`` entry."""

    name: str
    bone_id: int = -1
    direction: np.ndarray = field(default_factory=lambda: np.array([0.0, 1.0, 0.0]))
    length: float = 0.0
    axis: np.ndarray = field(default_factory=lambda: np.zeros(3))
    axis_order: str = "XYZ"
    dof: tuple[str, ...] = ()
    limits: tuple[tuple[float, float], ...] = ()
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    C: np.ndarray = field(default_factory=lambda: np.eye(3))
    Cinv: np.ndarray = field(default_factory=lambda: np.eye(3))

    def finalise(self) -> None:
        n = float(np.linalg.norm(self.direction))
        if n > 1e-12:
            self.direction = self.direction / n
        self.C = euler_to_matrix(np.deg2rad(self.axis), self.axis_order)
        self.Cinv = self.C.T


@dataclass
class Skeleton:
    """A parsed ASF skeleton."""

    name: str = "VICON"
    length_unit: float = 0.45
    angle_unit: str = "deg"
    mass_unit: float = 1.0
    root_order: tuple[str, ...] = ("TX", "TY", "TZ", "RX", "RY", "RZ")
    root_axis_order: str = "XYZ"
    root_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    root_orientation: np.ndarray = field(default_factory=lambda: np.zeros(3))
    bones: dict[str, AsfBone] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)          # topological, parents first, "root" is index 0

    # ---------------------------------------------------------------- geometry helpers
    def unit_to_m(self) -> float:
        """Metres per ASF length unit (CMU convention: inches divided by the file's ``length`` scale)."""
        return 2.54 / 100.0 / float(self.length_unit)

    def chain_length_m(self, names: tuple[str, ...]) -> float:
        return sum(self.bones[n].length for n in names) * self.unit_to_m()

    # ---------------------------------------------------------------- forward kinematics
    def fk(self, frame: dict[str, list[float]], *, apply_root_translation: bool = True
           ) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        """Solve one AMC frame.

        Returns ``(positions, rotations)`` in the **ASF** frame: ``positions[bone]`` is the bone's *distal*
        joint (its tail) in ASF length units, plus ``positions['root']`` for the pelvis; ``rotations[bone]``
        is the bone's world rotation matrix.
        """
        positions: dict[str, np.ndarray] = {}
        rotations: dict[str, np.ndarray] = {}
        deg = self.angle_unit.lower().startswith("deg")

        def to_rad(vals: np.ndarray) -> np.ndarray:
            return np.deg2rad(vals) if deg else vals

        root_vals = frame.get("root", [0.0] * 6)
        trans = np.zeros(3)
        rot = np.zeros(3)
        for value, channel in zip(root_vals, self.root_order):
            ch = channel.upper()
            if ch.startswith("T"):
                trans["XYZ".index(ch[1])] = value
            elif ch.startswith("R"):
                rot["XYZ".index(ch[1])] = value
        root_c = euler_to_matrix(np.deg2rad(self.root_orientation), self.root_axis_order)
        root_r = euler_to_matrix(to_rad(rot), self.root_axis_order)
        rotations["root"] = root_c @ root_r @ root_c.T
        base = np.asarray(self.root_position, dtype=np.float64)
        positions["root"] = base + trans if apply_root_translation else base

        for name in self.order:
            if name == "root":
                continue
            bone = self.bones[name]
            parent = bone.parent or "root"
            local = np.zeros(3)
            vals = frame.get(name)
            if vals:
                for value, dof in zip(vals, bone.dof):
                    axis = dof[-1].upper()
                    if axis in "XYZ":
                        local["XYZ".index(axis)] = value
            r_local = euler_to_matrix(to_rad(local), bone.axis_order)
            rotations[name] = rotations[parent] @ bone.C @ r_local @ bone.Cinv
            positions[name] = positions[parent] + bone.length * (rotations[name] @ bone.direction)
        return positions, rotations

    def rest_rotations(self) -> dict[str, np.ndarray]:
        """World rotation of every bone with all AMC channels zero (the ASF rest pose)."""
        _, rot = self.fk({}, apply_root_translation=False)
        return rot

    def rest_positions(self) -> dict[str, np.ndarray]:
        pos, _ = self.fk({}, apply_root_translation=False)
        return pos


# --------------------------------------------------------------------------------------------- ASF parsing
def _strip(line: str) -> str:
    return line.split("#", 1)[0].strip()


def parse_asf(path: str | Path) -> Skeleton:
    """Parse a CMU ``.asf`` skeleton file."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    skel = Skeleton()
    section: str | None = None
    bone: AsfBone | None = None
    pending_limits: list[tuple[float, float]] = []
    in_hierarchy = False

    for raw in text.splitlines():
        line = _strip(raw)
        if not line:
            continue
        if line.startswith(":"):
            head = line[1:].split()
            section = head[0].lower()
            if section == "name" and len(head) > 1:
                skel.name = head[1]
            in_hierarchy = section == "hierarchy"
            continue
        if section == "units":
            parts = line.split()
            if parts[0] == "mass":
                skel.mass_unit = float(parts[1])
            elif parts[0] == "length":
                skel.length_unit = float(parts[1])
            elif parts[0] == "angle":
                skel.angle_unit = parts[1]
            continue
        if section == "root":
            parts = line.split()
            key = parts[0].lower()
            if key == "order":
                skel.root_order = tuple(p.upper() for p in parts[1:])
            elif key == "axis":
                skel.root_axis_order = parts[1].upper()
            elif key == "position":
                skel.root_position = np.array([float(v) for v in parts[1:4]])
            elif key == "orientation":
                skel.root_orientation = np.array([float(v) for v in parts[1:4]])
            continue
        if section == "bonedata":
            if line == "begin":
                bone = AsfBone(name="")
                pending_limits = []
                continue
            if line == "end":
                if bone is None:
                    raise ValueError(f"{path}: 'end' without 'begin' in :bonedata")
                bone.limits = tuple(pending_limits)
                bone.finalise()
                skel.bones[bone.name] = bone
                bone = None
                continue
            if bone is None:
                continue
            parts = line.split()
            key = parts[0].lower()
            if key == "id":
                bone.bone_id = int(float(parts[1]))
            elif key == "name":
                bone.name = parts[1]
            elif key == "direction":
                bone.direction = np.array([float(v) for v in parts[1:4]])
            elif key == "length":
                bone.length = float(parts[1])
            elif key == "axis":
                bone.axis = np.array([float(v) for v in parts[1:4]])
                m = _AXIS_ORDER_RE.search(line)
                bone.axis_order = m.group(0) if m else "XYZ"
            elif key == "dof":
                bone.dof = tuple(p.lower() for p in parts[1:])
            elif key == "limits" or line.startswith("("):
                for lo, hi in re.findall(r"\(\s*(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s*\)", line):
                    pending_limits.append((float(lo), float(hi)))
            continue
        if in_hierarchy:
            if line in ("begin", "end"):
                continue
            parts = line.split()
            parent, children = parts[0], parts[1:]
            for child in children:
                if child not in skel.bones:
                    raise ValueError(f"{path}: hierarchy names unknown bone {child!r}")
                skel.bones[child].parent = parent
                if parent != "root":
                    skel.bones[parent].children.append(child)

    if not skel.bones:
        raise ValueError(f"{path}: no :bonedata found")

    # topological order, parents first
    order = ["root"]
    seen = {"root"}
    remaining = dict(skel.bones)
    while remaining:
        progressed = False
        for name in list(remaining):
            parent = remaining[name].parent or "root"
            if parent in seen:
                order.append(name)
                seen.add(name)
                del remaining[name]
                progressed = True
        if not progressed:
            raise ValueError(f"{path}: cycle or orphan bones in :hierarchy ({sorted(remaining)})")
    skel.order = order
    return skel


# --------------------------------------------------------------------------------------------- AMC parsing
def parse_amc(path: str | Path) -> list[dict[str, list[float]]]:
    """Parse a CMU ``.amc`` motion file into a list of ``{bone: [channel values]}`` frames."""
    path = Path(path)
    frames: list[dict[str, list[float]]] = []
    current: dict[str, list[float]] | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line.startswith(":"):
            continue
        parts = line.split()
        if len(parts) == 1 and parts[0].lstrip("-").isdigit():
            current = {}
            frames.append(current)
            continue
        if current is None:                       # values before the first frame number
            continue
        try:
            current[parts[0]] = [float(v) for v in parts[1:]]
        except ValueError as exc:
            raise ValueError(f"{path}: cannot parse channel line {line!r}") from exc
    if not frames:
        raise ValueError(f"{path}: no frames found")
    return frames


# --------------------------------------------------------------------------------------------- analysis
def root_speed_mps(skel: Skeleton, frames: list[dict[str, list[float]]], fps: float = 120.0,
                   trim: float = 0.1) -> float:
    """Mean horizontal speed of the root over the clip, in metres per second.

    ``trim`` drops that fraction of frames from each end (CMU clips start and end standing still).
    """
    n = len(frames)
    lo, hi = int(n * trim), max(int(n * (1.0 - trim)), int(n * trim) + 2)
    pts = []
    for f in frames[lo:hi]:
        pos, _ = skel.fk(f)
        pts.append(asf_to_blender(pos["root"]) * skel.unit_to_m())
    pts_arr = np.asarray(pts)
    step = np.linalg.norm(np.diff(pts_arr[:, :2], axis=0), axis=1)
    return float(step.sum() * fps / max(len(step), 1))


def joint_tracks(skel: Skeleton, frames: list[dict[str, list[float]]]) -> dict[str, np.ndarray]:
    """World position of every joint for every frame, in metres, Blender axes. ``(n_frames, 3)`` per bone."""
    tracks: dict[str, list[np.ndarray]] = {n: [] for n in skel.order}
    scale = skel.unit_to_m()
    for f in frames:
        pos, _ = skel.fk(f)
        for name in skel.order:
            tracks[name].append(asf_to_blender(pos[name]) * scale)
    return {k: np.asarray(v) for k, v in tracks.items()}
