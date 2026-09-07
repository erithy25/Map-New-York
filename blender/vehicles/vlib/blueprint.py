"""Numeric body blueprints and the lofted shell builder.

A *blueprint* is a set of documented control points (metres, in the vehicle frame of DATA_CONTRACTS §13:
origin on the ground under the rear-axle centre, **+X forward, +Y left, +Z up**) from which every body line is
interpolated with :class:`vlib.geom.PolyCurve`.  Nothing here is traced from CAD; every number is either a
published dimension (length / width / height / wheelbase / track / tyre size) or a proportion derived from one
and recorded in the blueprint's ``notes`` so it can be checked against a photograph.

The shell is a **longitudinal quad loft**: one closed section per station, each section built as a
Catmull-Rom spline through nine anchors with a *fixed* number of samples per anchor segment.  The fixed
allocation is what makes the surface usable: sample index ``j`` means the same feature (rocker, shoulder,
beltline, roof rail, crown) on every station, so regions can be classified from ``(station, j)`` alone and the
quads never shear across a feature line.

Section anchors, right-to-left half (``+Y``), bottom centre → top centre::

    A0 (0,            z_under)   underbody centreline
    A1 (0.60·y_low,   z_under)   flat floor pan / valance
    A2 (y_low,        z_sill)    outer bottom edge  (rocker between the arches, wheel-arch lip over them)
    A3 (y_max,        z_shoulder) widest point of the body side
    A4 (y_belt,       z_belt)    beltline = bottom of the daylight opening
    A5 (blend,        blend)     tumblehome midpoint of the greenhouse
    A6 (y_top,        z_top-crown) roof rail / fender crown line
    A7 (0.55·y_top,   z_top-0.28·crown)  crown shoulder
    A8 (0,            z_top)     top centreline (hood → windshield → roof → backlight → deck)

Because ``z_top`` is a curve of ``x``, the windshield and backlight are produced by the *rate of rise* of that
curve — a windshield raked 62° from the vertical is simply a 0.34 m rise over 0.64 m of ``x``.  Similarly the
wheel arches are produced by ``z_sill`` rising to ``hub_z + arch_radius`` over each hub, so no boolean
operation is needed anywhere on the shell (booleans destroy the quad grid and the region tags).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Sequence

import bmesh
import numpy as np
from mathutils import Vector

from . import env, geom as g

log = env.log

MM = 0.001


# --------------------------------------------------------------------------- published dimensions
@dataclass(frozen=True)
class Dimensions:
    """Published exterior dimensions in millimetres (as quoted by the manufacturer/operator)."""

    length_mm: float
    width_mm: float           # body width, excluding mirrors
    height_mm: float          # unladen roof height
    wheelbase_mm: float
    track_front_mm: float
    track_rear_mm: float
    wheel_diameter_mm: float  # overall rolling diameter of the fitted tyre
    tyre_width_mm: float
    front_overhang_mm: float
    rear_overhang_mm: float
    rim_diameter_in: float = 17.0
    tyre_spec: str = ""
    ground_clearance_mm: float = 140.0

    def __post_init__(self) -> None:
        span = self.front_overhang_mm + self.wheelbase_mm + self.rear_overhang_mm
        if abs(span - self.length_mm) > 25.0:
            raise ValueError(f"overhangs+wheelbase {span:.0f} mm != published length {self.length_mm:.0f} mm")

    # --- derived, in metres, in the vehicle frame (rear axle centre on the ground = origin)
    @property
    def x_rear(self) -> float:
        return -self.rear_overhang_mm * MM

    @property
    def x_front(self) -> float:
        return (self.wheelbase_mm + self.front_overhang_mm) * MM

    @property
    def x_axle_front(self) -> float:
        return self.wheelbase_mm * MM

    @property
    def half_width(self) -> float:
        return self.width_mm * MM / 2.0

    @property
    def height(self) -> float:
        return self.height_mm * MM

    @property
    def length(self) -> float:
        return self.length_mm * MM

    @property
    def wheel_radius(self) -> float:
        return self.wheel_diameter_mm * MM / 2.0

    @property
    def rim_radius(self) -> float:
        return self.rim_diameter_in * 0.0254 / 2.0

    @property
    def tyre_width(self) -> float:
        return self.tyre_width_mm * MM

    @property
    def y_track_front(self) -> float:
        return self.track_front_mm * MM / 2.0

    @property
    def y_track_rear(self) -> float:
        return self.track_rear_mm * MM / 2.0

    def as_dict(self) -> dict:
        return {
            "length_mm": self.length_mm, "width_mm": self.width_mm, "height_mm": self.height_mm,
            "wheelbase_mm": self.wheelbase_mm, "track_front_mm": self.track_front_mm,
            "track_rear_mm": self.track_rear_mm, "front_overhang_mm": self.front_overhang_mm,
            "rear_overhang_mm": self.rear_overhang_mm, "wheel_diameter_mm": self.wheel_diameter_mm,
            "tyre_width_mm": self.tyre_width_mm, "rim_diameter_in": self.rim_diameter_in,
            "tyre_spec": self.tyre_spec, "ground_clearance_mm": self.ground_clearance_mm,
        }


# --------------------------------------------------------------------------- regions
class R(IntEnum):
    """Region = material index on the lofted shell.  Left-hand ids are mirrored to right-hand ids by
    :func:`vlib.geom.mirror_y` through :data:`MIRROR_REMAP`."""

    BODY = 0
    UNDERBODY = 1
    ROOF = 2
    HOOD = 3
    TRUNK = 4
    SILL = 5
    BUMPER_F = 6
    BUMPER_R = 7
    PILLAR = 8
    GLASS_WS = 9
    GLASS_BACK = 10
    DOOR_FL = 11
    DOOR_RL = 12
    GLASS_FL = 13
    GLASS_RL = 14
    DOOR_FR = 15
    DOOR_RR = 16
    GLASS_FR = 17
    GLASS_RR = 18
    QUARTER = 19
    WELL = 20
    GLASS_QL = 21
    GLASS_QR = 22
    DOOR_SL = 23      # sliding door (vans) / bus door leaf, left
    DOOR_SR = 24
    N = 25


MIRROR_REMAP: dict[int, int] = {
    int(R.DOOR_FL): int(R.DOOR_FR), int(R.DOOR_RL): int(R.DOOR_RR),
    int(R.GLASS_FL): int(R.GLASS_FR), int(R.GLASS_RL): int(R.GLASS_RR),
    int(R.GLASS_QL): int(R.GLASS_QR), int(R.DOOR_SL): int(R.DOOR_SR),
}

GLASS_REGIONS = (R.GLASS_WS, R.GLASS_BACK, R.GLASS_FL, R.GLASS_RL, R.GLASS_FR, R.GLASS_RR, R.GLASS_QL, R.GLASS_QR)


# --------------------------------------------------------------------------- helpers for blueprint authors
def curve(*pts: tuple[float, float]) -> g.PolyCurve:
    return g.PolyCurve(list(pts))


def const(v: float) -> g.PolyCurve:
    return g.PolyCurve([(-100.0, v), (100.0, v)])


# --------------------------------------------------------------------------- section bands
#: number of spline samples allocated to each of the eight anchor segments, at three detail levels.
SEG_SAMPLES = {
    "high": (3, 6, 9, 9, 8, 8, 8, 5),
    "mid": (2, 3, 4, 4, 4, 4, 4, 3),
    "low": (1, 2, 2, 2, 2, 2, 2, 2),
}


def band_index(samples: Sequence[int]) -> dict[str, tuple[int, int]]:
    """Half-open ``j`` ranges of each named band for a given sample allocation."""
    cuts = [0]
    for s in samples:
        cuts.append(cuts[-1] + s)
    return {
        "floor": (cuts[0], cuts[2]),      # A0..A2  underbody
        "side": (cuts[2], cuts[4]),       # A2..A4  rocker + door skin + fenders
        "green": (cuts[4], cuts[6]),      # A4..A6  greenhouse side (pillars / side glass)
        "top": (cuts[6], cuts[8]),        # A6..A8  hood / windshield / roof / backlight / deck
    }


def _catmull_rom(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    t2, t3 = t * t, t * t * t
    def c(a, b, cc, d):
        return 0.5 * ((2 * b) + (-a + cc) * t + (2 * a - 5 * b + 4 * cc - d) * t2 + (-a + 3 * b - 3 * cc + d) * t3)
    return c(p0[0], p1[0], p2[0], p3[0]), c(p0[1], p1[1], p2[1], p3[1])


def spline_through(anchors: Sequence[tuple[float, float]], samples: Sequence[int]) -> list[tuple[float, float]]:
    """Catmull-Rom through ``anchors`` with ``samples[k]`` points on segment k (the segment's start point plus
    ``samples[k]-1`` interior points); the final anchor is appended, so ``len(out) == sum(samples) + 1``."""
    if len(anchors) != len(samples) + 1:
        raise ValueError(f"{len(anchors)} anchors need {len(anchors) - 1} sample counts, got {len(samples)}")
    ext = [anchors[0]] + list(anchors) + [anchors[-1]]
    out: list[tuple[float, float]] = []
    for k, n in enumerate(samples):
        p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
        for s in range(n):
            out.append(_catmull_rom(p0, p1, p2, p3, s / n))
    out.append(tuple(anchors[-1]))
    return out


# --------------------------------------------------------------------------- the blueprint
@dataclass
class Blueprint:
    """Numeric body blueprint.  All curves take ``x`` (metres, rear-axle origin) and return metres."""

    name: str
    dims: Dimensions
    z_under: g.PolyCurve
    z_rocker: g.PolyCurve          # bottom edge of the side surface between the arches
    z_belt: g.PolyCurve
    z_top: g.PolyCurve
    y_rocker: g.PolyCurve          # half width at the rocker
    y_max: g.PolyCurve             # widest half width of the body side
    y_belt: g.PolyCurve
    y_top: g.PolyCurve             # half width of the roof rail / fender crown line
    crown: g.PolyCurve             # drop of the top edge below the top centreline
    shoulder_t: g.PolyCurve        # 0..1 height of the widest point between rocker and beltline
    tumble: g.PolyCurve            # 0..1 tumblehome fullness of the greenhouse section

    # longitudinal feature stations (metres)
    x_cowl: float = 0.0            # base of the windshield
    x_roof_front: float = 0.0      # header (top of the windshield)
    x_roof_rear: float = 0.0       # top of the backlight
    x_deck: float = 0.0            # base of the backlight / front of the boot lid
    x_door_cuts: tuple[float, ...] = ()   # (front cut, mid cut, rear cut) — 2 or 3 values
    x_hood_rear: float = 0.0       # rear edge of the bonnet (= cowl unless there is a scuttle panel)
    x_bumper_f: float = 0.0        # rearmost x of the front bumper skin
    x_bumper_r: float = 0.0        # foremost x of the rear bumper skin
    arch_radius_f: float = 0.40
    arch_radius_r: float = 0.40
    glass_gap: float = 0.055       # x gap between daylight openings (B-pillar half width)
    pillar_a: float = 0.075        # x thickness of the A-pillar at the belt
    pillar_c: float = 0.16         # x thickness of the C-pillar
    #: vans/box bodies: everything at or behind this x on the side/greenhouse/top bands is the rear cargo
    #: door leaf, exported as ``Trunk`` (the contract's rear opening panel).
    x_rear_door: float | None = None
    #: flat-front vehicles (buses, cab-over trucks, vans): ``(x_from, z0, z1)`` marks the windscreen aperture
    #: on the front face, which no car-style ``z_top`` rake can describe.
    front_glass: tuple[float, float, float] | None = None
    #: ``(x_to, z0, z1)`` rear window aperture on a flat rear face.
    rear_glass: tuple[float, float, float] | None = None
    #: explicit side-glass spans ``(x_front, x_rear, region_id)`` for bodies whose glazing is not defined by
    #: door cuts (buses, box vans, coaches).
    side_glass_spans: Sequence[tuple[float, float, int]] = ()
    has_quarter_glass: bool = False
    x_quarter: tuple[float, float] = (0.0, 0.0)
    n_stations: int = 116
    notes: dict[str, str] = field(default_factory=dict)
    doors_per_side: int = 2
    sliding_doors: bool = False

    # ------------------------------------------------------------------ derived geometry
    @property
    def hub_z(self) -> float:
        return self.dims.wheel_radius

    def arch(self, x: float) -> float:
        """Height of the wheel-arch lip at ``x`` (``-inf`` where no arch)."""
        best = -1e9
        for hx, r in ((0.0, self.arch_radius_r), (self.dims.x_axle_front, self.arch_radius_f)):
            dx = abs(x - hx)
            if dx < r:
                best = max(best, self.hub_z + math.sqrt(max(0.0, r * r - dx * dx)))
        return best

    def archness(self, x: float) -> float:
        a = self.arch(x)
        r = self.z_rocker(x)
        if a <= r:
            return 0.0
        return g.clamp((a - r) / 0.12)

    def z_sill(self, x: float) -> float:
        return max(self.z_rocker(x), self.arch(x))

    def y_low(self, x: float) -> float:
        """Half width at the bottom edge: the rocker between the arches, the (wider) arch lip over them."""
        return g.lerp(self.y_rocker(x), self.y_max(x) - 0.006, self.archness(x))

    # ------------------------------------------------------------------ one section
    def anchors(self, x: float) -> list[tuple[float, float]]:
        zu, zs, zb, zt = self.z_under(x), self.z_sill(x), self.z_belt(x), self.z_top(x)
        zs = min(zs, zb - 0.02)
        zu = min(zu, zs - 0.005)
        yl, ym, yb, yt = self.y_low(x), self.y_max(x), self.y_belt(x), self.y_top(x)
        c = min(self.crown(x), max(0.004, (zt - zb) * 0.55 + 0.006))
        zte = zt - c
        if zte < zb + 0.004:                      # hood/deck: the "greenhouse" collapses into the crown
            zte = zb + 0.004
        sh = g.clamp(self.shoulder_t(x), 0.05, 0.95)
        tb = g.clamp(self.tumble(x), 0.0, 1.0)
        a5y = g.lerp(yb, yt, 0.34 + 0.28 * tb)
        a5z = g.lerp(zb, zte, 0.42)
        return [
            (0.0, zu),
            (0.60 * yl, zu),
            (yl, zs),
            (ym, g.lerp(zs, zb, sh)),
            (yb, zb),
            (a5y, a5z),
            (yt, zte),
            (0.55 * yt, zt - 0.28 * c),
            (0.0, zt),
        ]

    def section(self, x: float, samples: Sequence[int]) -> list[tuple[float, float]]:
        """Sampled section, clamped to the published envelope.  A Catmull-Rom spline overshoots between control
        points; without the clamp the shoulder bulges ~20 mm past ``y_max`` and the crown past ``z_top``, which
        would put the exported body over the published width and height."""
        ymax = self.y_max(x)
        ztop = self.z_top(x)
        zbot = min(self.z_under(x), self.z_sill(x)) - 1e-6
        pts = spline_through(self.anchors(x), samples)
        return [(min(max(p[0], 0.0), ymax), min(max(p[1], zbot), ztop)) for p in pts]

    # ------------------------------------------------------------------ region classification
    def _door_span(self, k: int) -> tuple[float, float]:
        cuts = self.x_door_cuts
        return cuts[k], cuts[k + 1]

    def region(self, x: float, band: str, y: float, z: float) -> int:
        """Material index of a quad whose centre is at ``x`` in band ``band`` at ``(y, z)`` (``y >= 0``: left)."""
        d = self.dims
        if band == "floor":
            return int(R.WELL) if self.archness(x) > 0.5 else int(R.UNDERBODY)
        yb = self.y_belt(x)
        if self.front_glass and x >= self.front_glass[0] and self.front_glass[1] <= z <= self.front_glass[2] \
                and abs(y) <= yb * 0.96:
            return int(R.GLASS_WS)
        if self.rear_glass and x <= self.rear_glass[0] and self.rear_glass[1] <= z <= self.rear_glass[2] \
                and abs(y) <= yb * 0.96:
            return int(R.GLASS_BACK)
        if self.x_rear_door is not None and x <= self.x_rear_door:
            return int(R.TRUNK)
        if self.side_glass_spans and band in ("green", "side"):
            for xa, xb, reg in self.side_glass_spans:
                if xb <= x <= xa and band == "green":
                    return int(reg)
            if band == "green":
                return int(R.PILLAR)
        if band == "top":
            if x >= self.x_hood_rear:
                return int(R.BUMPER_F) if x >= self.x_bumper_f else int(R.HOOD)
            if x >= self.x_roof_front:
                return int(R.GLASS_WS) if self._in_windshield(x, y) else int(R.PILLAR)
            if x >= self.x_roof_rear:
                return int(R.ROOF)
            if x >= self.x_deck:
                return int(R.GLASS_BACK) if self._in_backlight(x, y) else int(R.PILLAR)
            return int(R.BUMPER_R) if x <= self.x_bumper_r else int(R.TRUNK)
        # side / greenhouse bands
        if x >= self.x_bumper_f:
            return int(R.BUMPER_F)
        if x <= self.x_bumper_r:
            return int(R.BUMPER_R)
        if band == "side":
            if z < self.z_rocker(x) + 0.10 and self.archness(x) < 0.4 and self.x_door_cuts and \
                    self.x_door_cuts[0] <= x <= self.x_door_cuts[-1]:
                return int(R.SILL)
            k = self._door_of(x)
            # a sliding side door is still the rear-side door as far as the engine binding is concerned;
            # ``sliding_doors`` only records the mechanism in the catalog (``door_kind``).
            if k == 0:
                return int(R.DOOR_FL)
            if k >= 1:
                return int(R.DOOR_RL)
            return int(R.BODY)
        # greenhouse
        glass = self._side_glass(x)
        if glass is None:
            return int(R.PILLAR)
        return int(glass)

    def _door_of(self, x: float) -> int:
        cuts = self.x_door_cuts
        for k in range(len(cuts) - 1):
            if cuts[k + 1] <= x <= cuts[k]:
                return k
        return -1

    def _side_glass(self, x: float) -> int | None:
        """Daylight-opening id at ``x``, or ``None`` (pillar)."""
        cuts = self.x_door_cuts
        if not cuts:
            return None
        if x > cuts[0] - self.pillar_a or x < cuts[-1] + 0.02:
            if self.has_quarter_glass and self.x_quarter[1] <= x <= self.x_quarter[0]:
                return int(R.GLASS_QL)
            return None
        for k in range(len(cuts) - 1):
            x0, x1 = cuts[k], cuts[k + 1]
            if x1 + self.glass_gap * 0.5 <= x <= x0 - (self.pillar_a if k == 0 else self.glass_gap * 0.5):
                return int(R.GLASS_FL) if k == 0 else int(R.GLASS_RL)
        return None

    def _in_windshield(self, x: float, y: float) -> bool:
        t = g.clamp((x - self.x_roof_front) / max(1e-6, self.x_cowl - self.x_roof_front))
        return abs(y) <= self.y_top(x) * (0.99 - 0.10 * t)

    def _in_backlight(self, x: float, y: float) -> bool:
        return abs(y) <= self.y_top(x) * 0.95

    def station_xs(self, n: int | None = None) -> np.ndarray:
        """Stations, densified where the top line moves fastest (windshield, backlight, arches)."""
        n = n or self.n_stations
        d = self.dims
        x0, x1 = d.x_rear + CAP_INSET, d.x_front - CAP_INSET
        base = np.linspace(x0, x1, max(24, n))
        feats = [self.x_cowl, self.x_roof_front, self.x_roof_rear, self.x_deck, self.x_hood_rear,
                 self.x_bumper_f, self.x_bumper_r, *self.x_door_cuts]
        for hx, r in ((0.0, self.arch_radius_r), (d.x_axle_front, self.arch_radius_f)):
            feats += [hx - r + 1e-3, hx - r - 1e-3, hx + r - 1e-3, hx + r + 1e-3, hx]
        extra = [f for f in feats if x0 < f < x1]
        extra += [f + s for f in extra for s in (-0.018, 0.018)]
        xs = np.unique(np.concatenate([base, np.asarray([e for e in extra if x0 < e < x1])]))
        return xs


#: column order of a blueprint table row
TABLE_COLUMNS = ("x", "z_under", "z_rocker", "z_belt", "z_top", "y_rocker", "y_max", "y_belt", "y_top", "crown")


def from_table(name: str, dims: Dimensions, rows: Sequence[Sequence[float]], **kw) -> Blueprint:
    """Build a :class:`Blueprint` from a numeric table, one row per longitudinal control station::

        (x, z_under, z_rocker, z_belt, z_top, y_rocker, y_max, y_belt, y_top, crown)     all in metres

    This is the form every fleet vehicle is authored in: the table *is* the blueprint, readable next to a side
    elevation.  The first and last rows must be the published rear and front extremes.
    """
    arr = [tuple(float(c) for c in r) for r in rows]
    for r in arr:
        if len(r) != len(TABLE_COLUMNS):
            raise ValueError(f"{name}: table row needs {len(TABLE_COLUMNS)} numbers {TABLE_COLUMNS}, got {len(r)}")
    xs = [r[0] for r in arr]
    if abs(xs[0] - dims.x_rear) > 1e-6 or abs(xs[-1] - dims.x_front) > 1e-6:
        raise ValueError(f"{name}: table spans {xs[0]:.3f}..{xs[-1]:.3f} but the published body spans "
                         f"{dims.x_rear:.3f}..{dims.x_front:.3f}")
    if max(r[6] for r in arr) > dims.half_width + 1e-9:
        raise ValueError(f"{name}: y_max exceeds half the published width ({dims.half_width:.3f} m)")
    if max(r[4] for r in arr) > dims.height + 1e-9:
        raise ValueError(f"{name}: z_top exceeds the published height ({dims.height:.3f} m)")
    cols = {c: g.PolyCurve([(r[0], r[i]) for r in arr]) for i, c in enumerate(TABLE_COLUMNS) if i}
    kw.setdefault("shoulder_t", const(0.58))
    kw.setdefault("tumble", const(0.5))
    return Blueprint(name=name, dims=dims, z_under=cols["z_under"], z_rocker=cols["z_rocker"],
                     z_belt=cols["z_belt"], z_top=cols["z_top"], y_rocker=cols["y_rocker"], y_max=cols["y_max"],
                     y_belt=cols["y_belt"], y_top=cols["y_top"], crown=cols["crown"], **kw)


# --------------------------------------------------------------------------- shell
@dataclass
class Shell:
    object: object                      # bpy Object (the merged shell before separation)
    xs: np.ndarray
    bands: dict[str, tuple[int, int]]
    n_ring: int


#: how far inboard of the published extremes the last full station sits; the end caps then step back
#: out to exactly ``x_rear`` / ``x_front`` so the lofted body is exactly the published length.
CAP_INSET = 0.030


def build_shell(bp: Blueprint, *, detail: str = "high", cap_scales: Sequence[float] = (0.90, 0.66),
                materials: Sequence = ()) -> Shell:
    """Loft the closed body shell of ``bp`` and tag every quad with its :class:`R` region."""
    samples = SEG_SAMPLES[detail]
    bands = band_index(samples)
    xs = bp.station_xs()
    d = bp.dims
    sections: list[list[tuple[float, float]]] = [bp.section(float(x), samples) for x in xs]
    n_half = len(sections[0])

    # rounded end caps: shrink the extreme sections toward their own centre so the bumper ends are not flat slabs
    def shrink(sec, s):
        zc = 0.5 * (min(p[1] for p in sec) + max(p[1] for p in sec))
        zs_ = 0.45 + 0.55 * s
        return [(p[0] * s, zc + (p[1] - zc) * zs_) for p in sec]

    xs_l = list(map(float, xs))
    dx = CAP_INSET / max(1, len(cap_scales))
    for s in cap_scales:                       # outward, largest scale first
        sections.insert(0, shrink(sections[0], s))
        xs_l.insert(0, xs_l[0] - dx)
        sections.append(shrink(sections[-1], s))
        xs_l.append(xs_l[-1] + dx)
    xs = np.asarray(xs_l)

    stations = [[(x, p[0], p[1]) for p in sec] for x, sec in zip(xs_l, sections)]

    def band_of(j: int) -> str:
        for nm, (a, b) in bands.items():
            if a <= j < b:
                return nm
        return "top"

    def tag(i: int, j: int) -> int:
        xm = 0.5 * (xs_l[i] + xs_l[i + 1])
        a = stations[i][j]
        b = stations[i + 1][min(j + 1, n_half - 1)]
        return bp.region(xm, band_of(j), 0.5 * (a[1] + b[1]), 0.5 * (a[2] + b[2]))

    bm, _rows = g.loft(stations, tag=tag)
    g.mirror_y(bm, remap=MIRROR_REMAP)
    before = {f for f in bm.faces}
    g.fill_holes(bm)
    # the two end caps close the nose and the tail: they are bumper skin, never underbody (tagging them
    # UNDERBODY put the whole front and rear faces into the Undertray object)
    xmid = 0.5 * (xs_l[0] + xs_l[-1])
    for f in bm.faces:
        if f not in before:
            f.material_index = int(R.BUMPER_F) if f.calc_center_median().x > xmid else int(R.BUMPER_R)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = g.to_object(f"{bp.name}_shell", bm, list(materials), smooth=True, sharp_angle_deg=34.0)
    log.info("%s shell: %d stations x %d ring points -> %d tris", bp.name, len(xs_l), n_half * 2 - 2, g.tri_count(ob))
    return Shell(object=ob, xs=xs, bands=bands, n_ring=n_half)


