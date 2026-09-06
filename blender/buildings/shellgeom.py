"""Pure-geometry building shell generator (no ``bpy``) for NYCSim.

Turns a cleaned real footprint ring + real ``ground_z``/``roof_z`` into a closed, watertight
triangle soup with metre UVs, per DATA_CONTRACTS §5 / ARCHITECTURE §4.3.

Conventions
-----------
* Coordinates are metres, NYC_TM, Z-up (Blender convention).  ``build_tile.py`` shifts X/Y to
  tile-local coordinates *before* calling this module; Z stays absolute NAVD88 metres.
* Every solid spans exactly ``[ground_z, roof_z]``: for flat roofs ``roof_z`` is the top of the
  parapet, for pitched roofs it is the ridge/apex.  The LiDAR ``height_roof`` field this comes
  from is the highest roof return, which is the parapet/ridge — so the mesh height equals the
  ``height`` column to float precision.
* Wall UVs are in metres: ``u`` runs along the facade (arc length around the ring, origin at the
  edge whose outward normal best matches ``primary_facade_heading``), ``v = z - ground_z`` on every
  vertical face of the shell — including the inner parapet face.  Note that glTF flips V on export
  (top-left origin), so a glTF/Unreal consumer reads the height as ``1 - V``.  Horizontal faces
  (floor slab, parapet coping, roof deck) carry planar XY metre UVs instead.
* Triangle winding is CCW seen from outside, so face normals point out of the solid.  Nothing
  relies on Blender's normal recalculation.

This module is deliberately free of ``bpy`` so that ``tests/test_building_shells.py`` and the
merged-LOD builder can use it without starting Blender.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
import shapely
from shapely.geometry import Polygon

try:
    import mapbox_earcut as _earcut
except ImportError as exc:  # pragma: no cover - environment guarantee
    raise RuntimeError("mapbox_earcut is required by blender/buildings/shellgeom.py") from exc

# --------------------------------------------------------------------------- roof enum (DATA_CONTRACTS §5 roof_type)
ROOF_FLAT = 0
ROOF_GABLE = 1
ROOF_HIP = 2
ROOF_MANSARD = 3
ROOF_SHED = 4
ROOF_SAWTOOTH = 5
ROOF_COMPLEX = 6
ROOF_DOME = 7
ROOF_BARREL = 8
ROOF_NAMES = ("flat", "gable", "hip", "mansard", "shed", "sawtooth", "complex", "dome", "barrel")

# --------------------------------------------------------------------------- tunables (all real-world NYC values)
SNAP_M = 0.02                 # 2 cm footprint snap (brief + ARCHITECTURE §4.3)
WELD_M = 1e-3                 # 1 mm vertex weld inside one building
MIN_PART_AREA_M2 = 1.0        # drop snap-rounding slivers
MIN_HOLE_AREA_M2 = 0.5        # drop courtyard slivers
PARAPET_H_M = 0.60            # NYC parapet above the roof deck (ARCHITECTURE §4.3)
PARAPET_T_M = 0.30            # parapet wall thickness (12 in masonry)
PARAPET_MIN_H_M = 6.0         # buildings shorter than this get no parapet (garages, sheds)
PARAPET_MIN_AREA_M2 = 40.0
PARAPET_MIN_FLOORS = 2
GABLE_SLOPE_DEG = 32.0        # NYC frame house roof pitch (7:12 ≈ 30°, 8:12 ≈ 34°)
STEEP_SLOPE_DEG = 45.0
SHED_SLOPE_DEG = 12.0
MANSARD_DECK_FRAC = 0.35      # deck half-width as a fraction of the short half-axis
SAWTOOTH_PERIOD_M = 6.0
BARREL_BANDS = 8
MAX_RISE_FRAC = 0.55          # a pitched roof never eats more than this fraction of the height
MIN_WALL_H_M = 2.2            # eaves never drop below this above ground


@dataclass(frozen=True)
class RoofSpec:
    """Resolved roof description for one building."""

    kind: int = ROOF_FLAT
    slope_deg: float = GABLE_SLOPE_DEG
    parapet_h: float = PARAPET_H_M
    source: str = "default"
    rise_m: float = 0.0     # explicit ridge-minus-eave rise (ADR-013 §5); 0 = derive from the pitch


@dataclass
class BuildingSpec:
    """Everything the geometry stage needs about one building."""

    bin: int
    polygon: Polygon                 # cleaned, oriented (exterior CCW, holes CW), tile-local XY
    ground_z: float
    roof_z: float
    roof: RoofSpec
    mat_wall: int                    # index into facade_params.MATERIALS
    mat_roof: int
    facade_heading: float = 0.0      # compass degrees, 0 = north, clockwise
    attrs: dict[str, float] = field(default_factory=dict)
    floors: int = 1
    area: float = 0.0
    roof_steps: list[tuple[Polygon, float]] | None = None   # (region, z) tiling `polygon` exactly


# Fast integer quantisation for the weld grid: `int(v * _Q + _OFF + 0.5) - _OFF` rounds a double
# without the ~3 us cost of builtins.round(), and the offset keeps the truncation of int() equal to
# a floor for the negative half.  Valid for |coordinate| < 4 km, which every tile-local shell is.
_Q = 1.0 / WELD_M
_OFF = 4_000_000

_NEIGHBOURS: tuple[tuple[int, int, int], ...] = tuple(
    (dx, dy, dz) for dz in (0, -1, 1) for dy in (0, -1, 1) for dx in (0, -1, 1) if (dx, dy, dz) != (0, 0, 0))


@dataclass
class TriBuf:
    """Welded triangle accumulator for a single building (positions welded at 1 mm)."""

    pos: list[tuple[float, float, float]] = field(default_factory=list)
    tris: list[tuple[int, int, int]] = field(default_factory=list)
    uvs: list[tuple[float, float, float, float, float, float]] = field(default_factory=list)
    mats: list[int] = field(default_factory=list)
    fallback: str = ""
    tolerant: bool = False
    _index: dict[tuple[int, int, int], int] = field(default_factory=dict)

    def vid(self, x: float, y: float, z: float) -> int:
        """Index of the welded vertex at (x, y, z).

        The 26-cell probe matters: a roof ridge point is reached from two different plane
        equations, so the two z values can straddle a grid boundary by one ULP.  A plain grid hash
        would then hand out two indices and leave a 1 mm crack in an otherwise closed solid.
        """
        idx = self._index
        kx = int(x * _Q + 4_000_000.5) - _OFF
        ky = int(y * _Q + 4_000_000.5) - _OFF
        kz = int(z * _Q + 4_000_000.5) - _OFF
        key = (kx, ky, kz)
        i = idx.get(key)
        if i is not None:
            return i
        if not self.tolerant:
            i = len(self.pos)
            idx[key] = i
            self.pos.append((x, y, z))
            return i
        for dx, dy, dz in _NEIGHBOURS:
            j = idx.get((kx + dx, ky + dy, kz + dz))
            if j is not None:
                px, py, pz = self.pos[j]
                if abs(px - x) <= WELD_M and abs(py - y) <= WELD_M and abs(pz - z) <= WELD_M:
                    idx[key] = j
                    return j
        i = len(self.pos)
        idx[key] = i
        self.pos.append((x, y, z))
        return i

    def tri(self, a: Sequence[float], b: Sequence[float], c: Sequence[float],
            uva: Sequence[float], uvb: Sequence[float], uvc: Sequence[float], mat: int) -> None:
        ia, ib, ic = self.vid(*a), self.vid(*b), self.vid(*c)
        if ia == ib or ib == ic or ia == ic:
            return  # degenerate after welding
        ax, ay, az = self.pos[ia]
        ux, uy, uz = self.pos[ib][0] - ax, self.pos[ib][1] - ay, self.pos[ib][2] - az
        vx, vy, vz = self.pos[ic][0] - ax, self.pos[ic][1] - ay, self.pos[ic][2] - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        if nx * nx + ny * ny + nz * nz < 4e-18:
            return  # three collinear points: zero area, contributes nothing but broken edges
        self.tris.append((ia, ib, ic))
        self.uvs.append((uva[0], uva[1], uvb[0], uvb[1], uvc[0], uvc[1]))
        self.mats.append(mat)

    @property
    def n_tris(self) -> int:
        return len(self.tris)


# --------------------------------------------------------------------------- footprint cleaning
def clean_footprints(geoms, *, snap: float = SNAP_M, min_area: float = MIN_PART_AREA_M2,
                     min_hole_area: float = MIN_HOLE_AREA_M2, simplify: bool = True) -> list[list[Polygon]]:
    """Clean an array of footprint geometries (vectorised shapely 2).

    2 cm snap-rounding, validity repair, collinear-vertex removal inside the snap tolerance,
    correct winding (exterior CCW, holes CW), sliver parts and sliver holes dropped.
    Returns, per input geometry, the list of solid polygons to extrude (usually exactly one).
    """
    arr = np.asarray(geoms, dtype=object)
    g = shapely.force_2d(arr)
    bad = ~shapely.is_valid(g)
    if bad.any():
        g[bad] = shapely.make_valid(g[bad])
    g = shapely.set_precision(g, snap, mode="valid_output")
    bad = ~shapely.is_valid(g)
    if bad.any():
        g[bad] = shapely.make_valid(g[bad])
    if simplify:
        # Douglas–Peucker inside the snap tolerance: drops collinear runs without moving any
        # vertex further than `snap` from the real ring.
        g = shapely.simplify(g, snap, preserve_topology=True)
        bad = ~shapely.is_valid(g)
        if bad.any():
            g[bad] = shapely.make_valid(g[bad])

    out: list[list[Polygon]] = []
    for geom in g:
        polys: list[Polygon] = []
        if geom is None or geom.is_empty:
            out.append(polys)
            continue
        for part in _iter_polygons(geom):
            if part.is_empty or part.area < min_area:
                continue
            holes = [r for r in part.interiors if abs(shapely.Polygon(r).area) >= min_hole_area]
            p = Polygon(part.exterior, holes) if len(holes) != len(part.interiors) else part
            if not p.is_valid:
                p = shapely.make_valid(p)
                if p.geom_type not in ("Polygon", "MultiPolygon"):
                    continue
                cand = [q for q in _iter_polygons(p) if q.area >= min_area]
                if not cand:
                    continue
                p = max(cand, key=lambda q: q.area)
            polys.append(shapely.geometry.polygon.orient(p, 1.0))  # exterior CCW, holes CW
        out.append(polys)
    return out


def _iter_polygons(geom) -> Iterable[Polygon]:
    t = geom.geom_type
    if t == "Polygon":
        yield geom
    elif t in ("MultiPolygon", "GeometryCollection"):
        for sub in geom.geoms:
            yield from _iter_polygons(sub)


def ring_coords(poly: Polygon) -> tuple[np.ndarray, list[np.ndarray]]:
    """Open coordinate arrays (no repeated last point): exterior CCW, holes CW."""
    ext = shapely.get_coordinates(poly.exterior)[:-1]
    holes = [shapely.get_coordinates(r)[:-1] for r in poly.interiors]
    return ext, holes


# --------------------------------------------------------------------------- triangulation
def earcut(rings: Sequence[np.ndarray]) -> np.ndarray:
    """Triangulate a polygon given as [exterior, hole, hole, ...] open rings.

    Returns an (m, 3) int array of indices into ``np.vstack(rings)``.  Triangles are returned
    with positive (CCW) 2-D winding so the caller can emit an up-facing cap directly.
    """
    pts = np.vstack(rings) if len(rings) > 1 else np.asarray(rings[0], dtype=np.float64)
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    idx = _earcut.triangulate_float64(np.ascontiguousarray(pts, dtype=np.float64), ends)
    if len(idx) == 0:
        return np.zeros((0, 3), dtype=np.int64)
    tri = np.asarray(idx, dtype=np.int64).reshape(-1, 3)
    a, b, c = pts[tri[:, 0]], pts[tri[:, 1]], pts[tri[:, 2]]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    keep = np.abs(cross) > 1e-12
    tri, cross = tri[keep], cross[keep]
    flip = cross < 0
    if flip.any():
        tri[flip] = tri[flip][:, ::-1]
    return tri


# --------------------------------------------------------------------------- UV helper
def ring_uv_origin(ring: np.ndarray, heading_deg: float) -> int:
    """Index of the ring vertex where ``u = 0``: the start of the edge whose outward normal is
    closest to ``heading_deg`` (compass degrees).  Keeps the primary facade's window grid phase
    stable between LODs and between runs."""
    if len(ring) < 3:
        return 0
    d = _edge_vectors(ring)
    seg = np.hypot(d[:, 0], d[:, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        nx, ny = d[:, 1] / seg, -d[:, 0] / seg          # outward normal for a CCW ring
    want = math.radians(90.0 - float(heading_deg))       # compass -> math angle
    score = nx * math.cos(want) + ny * math.sin(want)
    score = np.where(seg > 0.5, score, -2.0)             # ignore stub edges
    return int(np.argmax(score))


def _edge_vectors(ring: np.ndarray) -> np.ndarray:
    """``ring[i+1] - ring[i]`` with wraparound (np.roll is ~4x slower on these small rings)."""
    d = np.empty_like(ring)
    d[:-1] = ring[1:] - ring[:-1]
    d[-1] = ring[0] - ring[-1]
    return d


def _cumulative_u(ring: np.ndarray, start: int) -> np.ndarray:
    """Arc length at each ring vertex, measured from vertex ``start`` going forward."""
    n = len(ring)
    d = _edge_vectors(ring)
    seg = np.hypot(d[:, 0], d[:, 1])
    roll = (np.arange(n) + start) % n
    cum_ordered = np.empty(n)
    cum_ordered[0] = 0.0
    np.cumsum(seg[roll][:-1], out=cum_ordered[1:])
    u = np.empty(n)
    u[roll] = cum_ordered
    return u


# --------------------------------------------------------------------------- wall emission
def _emit_wall_ring(buf: TriBuf, ring: np.ndarray, z0: float, ztop, u0_index: int, mat: int,
                    v_ref: float | None = None) -> None:
    """Vertical wall around one ring.  ``ztop`` is a scalar or a per-vertex array.

    ``v_ref`` is the height the UV ``v`` is measured from; it defaults to the wall's own base but is
    passed explicitly for the inner parapet face so that ``v`` is the height above the building's
    ``ground_z`` on every vertical surface of the shell.
    """
    n = len(ring)
    if n < 3:
        return
    vz = z0 if v_ref is None else v_ref
    u = _cumulative_u(ring, u0_index)
    zt = np.full(n, float(ztop)) if np.isscalar(ztop) else np.asarray(ztop, dtype=np.float64)
    for i in range(n):
        j = (i + 1) % n
        p, q = ring[i], ring[j]
        seg = math.hypot(q[0] - p[0], q[1] - p[1])
        if seg < WELD_M:
            continue
        ui, uj = u[i], u[i] + seg
        zi, zj = zt[i], zt[j]
        if zi <= z0 + WELD_M and zj <= z0 + WELD_M:
            continue
        b0 = (p[0], p[1], z0)
        b1 = (q[0], q[1], z0)
        t1 = (q[0], q[1], zj)
        t0 = (p[0], p[1], zi)
        buf.tri(b0, b1, t1, (ui, z0 - vz), (uj, z0 - vz), (uj, zj - vz), mat)
        buf.tri(b0, t1, t0, (ui, z0 - vz), (uj, zj - vz), (ui, zi - vz), mat)


def _emit_cap(buf: TriBuf, rings: Sequence[np.ndarray], z, mat: int, up: bool) -> None:
    """Horizontal (``z`` scalar) or planar (``z`` callable of (x, y)) cap over a polygon."""
    if not rings or len(rings[0]) < 3:
        return
    tri = earcut(rings)
    if len(tri) == 0:
        return
    pts = np.vstack(rings) if len(rings) > 1 else rings[0]
    zs = np.full(len(pts), float(z)) if np.isscalar(z) else z(pts)
    for a, b, c in tri:
        pa = (pts[a, 0], pts[a, 1], zs[a])
        pb = (pts[b, 0], pts[b, 1], zs[b])
        pc = (pts[c, 0], pts[c, 1], zs[c])
        ua = (pts[a, 0], pts[a, 1])
        ub = (pts[b, 0], pts[b, 1])
        uc = (pts[c, 0], pts[c, 1])
        if up:
            buf.tri(pa, pb, pc, ua, ub, uc, mat)
        else:
            buf.tri(pa, pc, pb, ua, uc, ub, mat)


# --------------------------------------------------------------------------- OBB
def obb_frame(poly: Polygon) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Oriented bounding box: (centre, long axis unit, short axis unit, half-long a, half-short b)."""
    rect = shapely.oriented_envelope(poly)
    if rect.geom_type != "Polygon" or rect.is_empty:
        xmin, ymin, xmax, ymax = poly.bounds
        c = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2])
        return c, np.array([1.0, 0.0]), np.array([0.0, 1.0]), max((xmax - xmin) / 2, 1e-3), max((ymax - ymin) / 2, 1e-3)
    pc = np.asarray(rect.exterior.coords, dtype=np.float64)[:-1]
    if len(pc) < 4:
        xmin, ymin, xmax, ymax = poly.bounds
        c = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2])
        return c, np.array([1.0, 0.0]), np.array([0.0, 1.0]), max((xmax - xmin) / 2, 1e-3), max((ymax - ymin) / 2, 1e-3)
    c = pc.mean(axis=0)
    e0 = pc[1] - pc[0]
    e1 = pc[2] - pc[1]
    l0, l1 = float(np.hypot(*e0)), float(np.hypot(*e1))
    if l0 >= l1:
        ea, a, eb, b = e0 / max(l0, 1e-9), l0 / 2, e1 / max(l1, 1e-9), l1 / 2
    else:
        ea, a, eb, b = e1 / max(l1, 1e-9), l1 / 2, e0 / max(l0, 1e-9), l0 / 2
    return c, ea, eb, max(a, 1e-3), max(b, 1e-3)


def _wedge(c: np.ndarray, ea: np.ndarray, eb: np.ndarray, corners_uv: Sequence[Sequence[float]]) -> Polygon:
    """Polygon from OBB-local (u, v) corners."""
    pts = [c + u * ea + v * eb for u, v in corners_uv]
    return Polygon(pts)


# --------------------------------------------------------------------------- roof region model
@dataclass
class RoofPiece:
    """One planar roof region: ``z = a*x + b*y + d`` over ``poly``, clamped to [zmin, zmax].

    The clamp is what keeps the solid inside ``[ground_z, roof_z]``: after the 1 mm snap a ridge
    vertex can land a fraction of a millimetre on the wrong side of the ridge line, and the plane
    would then evaluate just above the measured roof height.  Both neighbouring pieces clamp to the
    same value, so continuity (and watertightness) is preserved.
    """

    poly: Polygon
    a: float
    b: float
    d: float
    zmin: float = -math.inf
    zmax: float = math.inf

    def z_at(self, pts: np.ndarray) -> np.ndarray:
        return np.clip(self.a * pts[:, 0] + self.b * pts[:, 1] + self.d, self.zmin, self.zmax)

    def z_pt(self, x: float, y: float) -> float:
        z = self.a * x + self.b * y + self.d
        return self.zmin if z < self.zmin else (self.zmax if z > self.zmax else z)


def _plane_from_local(c: np.ndarray, axis: np.ndarray, k: float, z_at_zero: float) -> tuple[float, float, float]:
    """Plane with z = z_at_zero - k * ((p - c) · axis)."""
    a = -k * axis[0]
    b = -k * axis[1]
    d = z_at_zero + k * float(np.dot(c, axis))
    return a, b, d


def roof_pieces(poly: Polygon, roof: RoofSpec, z_eave: float, z_top: float,
                band_scale: float = 1.0) -> tuple[list[RoofPiece], list[tuple[np.ndarray, np.ndarray, float, float, np.ndarray]]]:
    """Decompose a pitched roof into planar regions clipped to the footprint.

    Returns ``(pieces, risers)``.  Each riser is ``(p, q, z_lo, z_hi, outward_normal_xy)`` — the
    vertical glazing face of a sawtooth profile.  The pieces tile the whole footprint and agree on
    every shared boundary, so the surface is a continuous height field and the shell closes.

    ``band_scale`` < 1 halves the number of bands for the sawtooth / barrel profiles (LOD1).
    ``ROOF_DOME`` is generated as a four-sided faceted pyramid (see module docs / REPORT): true
    domes belong to the hand-scripted landmark models of ARCHITECTURE §4.6, not to the mass shells.
    """
    c, ea, eb, a, b = obb_frame(poly)
    rise = z_top - z_eave
    big = 4.0 * (a + b) + 50.0
    pieces: list[RoofPiece] = []
    risers: list[tuple[np.ndarray, np.ndarray, float, float, np.ndarray]] = []
    kind = roof.kind
    z_lo, z_hi = min(z_eave, z_top), max(z_eave, z_top)
    if kind == ROOF_DOME:
        kind = ROOF_HIP

    def clip(region: Polygon) -> list[Polygon]:
        """Footprint ∩ region, snapped to the 1 mm weld grid.

        The snap is what makes the pieces stitch: after it, two pieces that share a boundary carry
        bit-identical coordinates on the grid the vertex welder uses, and zero-width slivers
        (a clip line grazing a footprint edge) collapse and are dropped instead of emitting a
        degenerate cap plus a duplicate wall over the same footprint edge.
        """
        try:
            inter = poly.intersection(region)
            inter = shapely.set_precision(inter, WELD_M, mode="valid_output")
        except Exception:
            return []
        return [p for p in _iter_polygons(inter) if p.is_valid and p.area > 1e-4]

    def hip_like(v_off: float, u_off: float, k: float) -> None:
        """Four slopes falling away from the rectangle |v| <= v_off, |u| <= u_off at ``z_top``."""
        quads = {
            "N": [(-u_off, v_off), (u_off, v_off), (u_off + big, v_off + big), (-u_off - big, v_off + big)],
            "S": [(u_off, -v_off), (-u_off, -v_off), (-u_off - big, -v_off - big), (u_off + big, -v_off - big)],
            "E": [(u_off, v_off), (u_off + big, v_off + big), (u_off + big, -v_off - big), (u_off, -v_off)],
            "W": [(-u_off, -v_off), (-u_off - big, -v_off - big), (-u_off - big, v_off + big), (-u_off, v_off)],
        }
        axes = {"N": eb, "S": -eb, "E": ea, "W": -ea}
        offs = {"N": v_off, "S": v_off, "E": u_off, "W": u_off}
        for key, corners in quads.items():
            reg = _wedge(c, ea, eb, corners)
            if not reg.is_valid:
                reg = shapely.make_valid(reg)
                if reg.geom_type not in ("Polygon", "MultiPolygon"):
                    continue
            pa, pb_, pd = _plane_from_local(c, axes[key], k, z_top + k * offs[key])
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd, z_lo, z_hi))

    if kind == ROOF_GABLE:
        k = rise / b
        for sign in (1.0, -1.0):
            reg = _wedge(c, ea, eb, [(-big, 0.0), (big, 0.0), (big, sign * big), (-big, sign * big)])
            pa, pb_, pd = _plane_from_local(c, eb * sign, k, z_top)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd, z_lo, z_hi))

    elif kind == ROOF_HIP:
        hip_like(0.0, max(a - b, 0.0), rise / b)

    elif kind == ROOF_MANSARD:
        f = MANSARD_DECK_FRAC
        r = max(a - b, 0.0)
        v_off, u_off = f * b, r + f * b
        deck = _wedge(c, ea, eb, [(-u_off, -v_off), (u_off, -v_off), (u_off, v_off), (-u_off, v_off)])
        for q in clip(deck):
            pieces.append(RoofPiece(q, 0.0, 0.0, z_top, z_lo, z_hi))
        hip_like(v_off, u_off, rise / max(b * (1.0 - f), 1e-6))

    elif kind == ROOF_SHED:
        k = rise / (2.0 * b)
        pa, pb_, pd = _plane_from_local(c, -eb, k, z_top - k * b)
        pieces.append(RoofPiece(poly, pa, pb_, pd, z_lo, z_hi))

    elif kind == ROOF_SAWTOOTH:
        # North-light sawtooth: a long monitor slope followed by a short, steep glazing face.
        # The glazing face is modelled as an 8 %-of-period slope (≈ 80° for a typical tooth)
        # rather than a true vertical, which keeps the roof a continuous height field — the
        # property the wall/cap stitching relies on.  At any viewing distance it reads vertical.
        glaze = 0.08
        period = max(SAWTOOTH_PERIOD_M / max(band_scale, 1e-3), 2.0 * b / 12.0)
        n_band = max(1, int(math.ceil(2.0 * b / period)))
        period = 2.0 * b / n_band
        k_up = rise / (period * (1.0 - glaze))
        k_dn = rise / (period * glaze)
        for i in range(n_band):
            v0 = -b + i * period
            v1 = v0 + period
            if i == n_band - 1:
                # last tooth runs all the way to the wall so the ridge lands exactly on z_top
                reg = _wedge(c, ea, eb, [(-big, v0), (big, v0), (big, big), (-big, big)])
                pa, pb_, pd = _plane_from_local(c, -eb, rise / period, z_eave - (rise / period) * v0)
                for q in clip(reg):
                    pieces.append(RoofPiece(q, pa, pb_, pd, z_lo, z_hi))
                continue
            vm = v0 + period * (1.0 - glaze)
            reg = _wedge(c, ea, eb, [(-big, v0), (big, v0), (big, vm), (-big, vm)])
            pa, pb_, pd = _plane_from_local(c, -eb, k_up, z_eave - k_up * v0)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd, z_lo, z_hi))
            reg = _wedge(c, ea, eb, [(-big, vm), (big, vm), (big, v1), (-big, v1)])
            pa, pb_, pd = _plane_from_local(c, eb, k_dn, z_top + k_dn * vm)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd, z_lo, z_hi))

    elif kind == ROOF_BARREL:
        n = max(2, int(round(BARREL_BANDS * band_scale)))
        for i in range(n):
            v0 = -b + 2.0 * b * i / n
            v1 = -b + 2.0 * b * (i + 1) / n
            z0b = z_eave + rise * math.sqrt(max(0.0, 1.0 - (v0 / b) ** 2))
            z1b = z_eave + rise * math.sqrt(max(0.0, 1.0 - (v1 / b) ** 2))
            k = (z0b - z1b) / (v1 - v0)
            reg = _wedge(c, ea, eb, [(-big, v0), (big, v0), (big, v1), (-big, v1)])
            pa, pb_, pd = _plane_from_local(c, eb, k, z0b + k * v0)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd, z_lo, z_hi))
    else:
        pieces.append(RoofPiece(poly, 0.0, 0.0, z_top, z_lo, z_hi))
    if not pieces:
        pieces.append(RoofPiece(poly, 0.0, 0.0, z_top, z_lo, z_hi))
    return pieces, risers


def _iter_lines(geom):
    t = geom.geom_type
    if t == "LineString":
        yield geom
    elif t in ("MultiLineString", "GeometryCollection"):
        for sub in geom.geoms:
            yield from _iter_lines(sub)


# --------------------------------------------------------------------------- boundary matching for pitched walls
class _BoundaryIndex:
    """Maps a point on the footprint boundary back to (ring, edge, arc length, direction)."""

    def __init__(self, rings: Sequence[np.ndarray], u_origin: Sequence[int]) -> None:
        segs_p, segs_d, segs_u, segs_len, segs_ring, segs_edge = [], [], [], [], [], []
        for ri, ring in enumerate(rings):
            if len(ring) < 3:
                continue
            u = _cumulative_u(ring, u_origin[ri])
            d = _edge_vectors(ring)
            segs_p.append(ring)
            segs_d.append(d)
            segs_u.append(u)
            segs_len.append(np.hypot(d[:, 0], d[:, 1]))
            segs_ring.append(np.full(len(ring), ri))
            segs_edge.append(np.arange(len(ring)))
        self.p = np.vstack(segs_p) if segs_p else np.zeros((0, 2))
        self.d = np.vstack(segs_d) if segs_d else np.zeros((0, 2))
        self.u = np.concatenate(segs_u) if segs_u else np.zeros(0)
        self.len = np.concatenate(segs_len) if segs_len else np.zeros(0)
        self.ring = np.concatenate(segs_ring) if segs_ring else np.zeros(0, dtype=int)
        self.edge = np.concatenate(segs_edge) if segs_edge else np.zeros(0, dtype=int)
        self.len2 = np.maximum(self.len ** 2, 1e-18)

    def locate(self, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """For each query point: (distance, arc length u, matched segment index, position along it)."""
        if len(self.p) == 0:
            z = np.zeros(len(pts))
            return np.full(len(pts), 1e9), z, np.zeros(len(pts), dtype=int), z
        w = pts[:, None, :] - self.p[None, :, :]
        t = (w[:, :, 0] * self.d[None, :, 0] + w[:, :, 1] * self.d[None, :, 1]) / self.len2[None, :]
        t = np.clip(t, 0.0, 1.0)
        proj = self.p[None, :, :] + t[:, :, None] * self.d[None, :, :]
        dist = np.hypot(pts[:, None, 0] - proj[:, :, 0], pts[:, None, 1] - proj[:, :, 1])
        k = np.argmin(dist, axis=1)
        rows = np.arange(len(pts))
        return dist[rows, k], self.u[k] + t[rows, k] * self.len[k], k, t[rows, k]


# --------------------------------------------------------------------------- the builder
def is_closed(n_verts: int, tris: Sequence[Sequence[int]]) -> bool:
    """Edge-manifold test on an already-welded index buffer (fast; used on every building)."""
    if not len(tris):
        return False
    t = np.asarray(tris, dtype=np.int64)
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]], axis=0)
    lo = np.minimum(e[:, 0], e[:, 1])
    hi = np.maximum(e[:, 0], e[:, 1])
    key = lo * np.int64(n_verts) + hi
    if len(key) % 2:
        return False
    key.sort()
    a, b = key[0::2], key[1::2]
    if not np.array_equal(a, b):
        return False
    return bool(len(a) < 2 or np.all(b[:-1] != a[1:]))


def build_shell(spec: BuildingSpec, lod: int = 0, *, ensure_closed: bool = True) -> TriBuf:
    """Closed shell for one building at the requested LOD.

    With ``ensure_closed`` (the default) the result is checked for edge-manifoldness and, if a
    pitched decomposition failed to close on a pathological footprint, the building is rebuilt as
    a flat-capped extrusion of the same real footprint between the same real ``ground_z`` and
    ``roof_z``.  ``TriBuf.fallback`` records what happened so the tile manifest can report it.
    """
    buf = _build_shell_once(spec, lod)
    if not ensure_closed or lod >= 2:
        return buf
    if is_closed(len(buf.pos), buf.tris):
        return buf
    # A ridge point reached from two plane equations can straddle the weld grid; retry with the
    # tolerant (26-neighbour) weld, which is ~50 % slower and therefore not the default path.
    buf_t = _build_shell_once(spec, lod, tolerant=True)
    if is_closed(len(buf_t.pos), buf_t.tris):
        return buf_t
    flat = BuildingSpec(bin=spec.bin, polygon=spec.polygon, ground_z=spec.ground_z, roof_z=spec.roof_z,
                        roof=RoofSpec(kind=ROOF_FLAT, parapet_h=0.0, source=spec.roof.source + "+unclosed"),
                        mat_wall=spec.mat_wall, mat_roof=spec.mat_roof, facade_heading=spec.facade_heading,
                        attrs=spec.attrs, floors=spec.floors, area=spec.area, roof_steps=None)
    buf2 = _build_shell_once(flat, lod, tolerant=True)
    buf2.fallback = "flat_cap"
    if is_closed(len(buf2.pos), buf2.tris):
        return buf2
    buf3 = TriBuf()
    _build_massing(buf3, spec)
    buf3.fallback = "massing"
    return buf3


def _build_shell_once(spec: BuildingSpec, lod: int, tolerant: bool = False) -> TriBuf:
    buf = TriBuf(tolerant=tolerant)
    if lod >= 2:
        _build_massing(buf, spec)
        return buf
    poly = spec.polygon
    if lod == 1 and not spec.roof_steps:
        # a stepped building keeps its exact ring: the level regions were cut from it, and the
        # steps are the silhouette this LOD exists to preserve
        poly = _simplify_for_lod1(poly)
        if poly is None:
            _build_massing(buf, spec)
            return buf
    z0 = float(spec.ground_z)
    z1 = float(spec.roof_z)
    if z1 - z0 < 0.05:
        z1 = z0 + 0.05
    kind = spec.roof.kind
    if spec.roof_steps and len(spec.roof_steps) >= 2 and lod <= 1:
        _build_stepped(buf, spec, poly, z0, z1, lod)
    elif kind in (ROOF_FLAT, ROOF_COMPLEX):
        _build_flat(buf, spec, poly, z0, z1, lod)
    else:
        _build_pitched(buf, spec, poly, z0, z1, lod)
    return buf


def _simplify_for_lod1(poly: Polygon, tol: float = 0.50) -> Polygon | None:
    try:
        s = poly.simplify(tol, preserve_topology=True)
    except Exception:
        return poly
    if s.is_empty or s.geom_type not in ("Polygon", "MultiPolygon"):
        return poly
    parts = [p for p in _iter_polygons(s) if p.area >= MIN_PART_AREA_M2]
    if not parts:
        return None
    p = max(parts, key=lambda q: q.area)
    holes = [r for r in p.interiors if abs(Polygon(r).area) >= 40.0]
    if len(holes) != len(p.interiors):
        p = Polygon(p.exterior, holes)
    if not p.is_valid:
        return poly
    return shapely.geometry.polygon.orient(p, 1.0)


def _parapet_wanted(spec: BuildingSpec, z0: float, z1: float, lod: int) -> bool:
    if lod >= 1:
        return False
    if spec.roof.parapet_h <= 0.0:
        return False
    return (z1 - z0) >= PARAPET_MIN_H_M and spec.area >= PARAPET_MIN_AREA_M2 and spec.floors >= PARAPET_MIN_FLOORS


def _build_flat(buf: TriBuf, spec: BuildingSpec, poly: Polygon, z0: float, z1: float, lod: int) -> None:
    ext, holes = ring_coords(poly)
    u0 = ring_uv_origin(ext, spec.facade_heading)
    _emit_wall_ring(buf, ext, z0, z1, u0, spec.mat_wall)
    for h in holes:
        _emit_wall_ring(buf, h, z0, z1, 0, spec.mat_wall)
    _emit_cap(buf, [ext] + holes, z0, spec.mat_wall, up=False)

    inner = None
    if _parapet_wanted(spec, z0, z1, lod):
        try:
            cand = poly.buffer(-PARAPET_T_M, join_style=2, mitre_limit=2.0)
        except Exception:
            cand = None
        if cand is not None and not cand.is_empty:
            parts = [p for p in _iter_polygons(cand) if p.area >= 4.0]
            if parts and sum(p.area for p in parts) >= 0.25 * poly.area:
                inner = parts
    if not inner:
        _emit_cap(buf, [ext] + holes, z1, spec.mat_roof, up=True)
        return

    z_deck = z1 - spec.roof.parapet_h
    try:
        band = poly.difference(shapely.union_all(inner))
    except Exception:
        band = None
    if band is None or band.is_empty:
        _emit_cap(buf, [ext] + holes, z1, spec.mat_roof, up=True)
        return
    for bp in _iter_polygons(band):
        if bp.area < 1e-4:
            continue
        bp = shapely.geometry.polygon.orient(bp, 1.0)
        be, bh = ring_coords(bp)
        _emit_cap(buf, [be] + bh, z1, spec.mat_wall, up=True)
    for ip in inner:
        ip = shapely.geometry.polygon.orient(ip, 1.0)
        ie, ih = ring_coords(ip)
        # inner parapet face: reversed ring so its normal points into the roof well
        _emit_wall_ring(buf, ie[::-1].copy(), z_deck, z1, 0, spec.mat_wall, v_ref=z0)
        for h in ih:
            _emit_wall_ring(buf, h[::-1].copy(), z_deck, z1, 0, spec.mat_wall, v_ref=z0)
        _emit_cap(buf, [ie] + ih, z_deck, spec.mat_roof, up=True)


def _pitched_geometry(spec: BuildingSpec, poly: Polygon, z0: float, z1: float, lod: int):
    """Eave height and roof pieces for a pitched building, honouring the height budget."""
    c, ea, eb, a, b = obb_frame(poly)
    slope = math.radians(max(3.0, min(70.0, spec.roof.slope_deg)))
    kind = spec.roof.kind
    if kind == ROOF_SHED:
        natural = 2.0 * b * math.tan(math.radians(min(spec.roof.slope_deg, SHED_SLOPE_DEG)))
    elif kind == ROOF_SAWTOOTH:
        natural = SAWTOOTH_PERIOD_M * math.tan(slope)
    elif kind in (ROOF_DOME, ROOF_BARREL):
        natural = b
    elif kind == ROOF_MANSARD:
        natural = b * (1.0 - MANSARD_DECK_FRAC) * math.tan(slope)
    else:
        natural = b * math.tan(slope)
    if spec.roof.rise_m > 0.0:
        natural = float(spec.roof.rise_m)
    h = z1 - z0
    rise = min(natural, MAX_RISE_FRAC * h, max(h - MIN_WALL_H_M, 0.25 * h))
    rise = max(rise, 0.35)
    z_eave = z1 - rise
    if z_eave <= z0 + 0.3:
        z_eave = z0 + 0.3 * h
    pieces, risers = roof_pieces(poly, spec.roof, z_eave, z1, band_scale=0.5 if lod >= 1 else 1.0)
    _ = c, ea, eb, a
    return z_eave, pieces, risers


def _build_pitched(buf: TriBuf, spec: BuildingSpec, poly: Polygon, z0: float, z1: float, lod: int) -> None:
    z_eave, pieces, risers = _pitched_geometry(spec, poly, z0, z1, lod)
    pieces = _cover_shortfall(pieces, poly, z_eave, z1)
    _build_from_pieces(buf, spec, poly, z0, pieces, pieces, risers)


def _cover_shortfall(pieces: list[RoofPiece], poly: Polygon, z_fill: float, z_hi: float) -> list[RoofPiece]:
    """Patch any part of the footprint the regions missed after the 1 mm snap, flat at ``z_fill``."""
    if sum(p.poly.area for p in pieces) >= 0.999 * poly.area:
        return pieces
    try:
        rest = poly.difference(shapely.union_all([p.poly for p in pieces]))
    except Exception:
        return pieces
    if rest is None or rest.is_empty:
        return pieces
    for rp in _iter_polygons(rest):
        if rp.area > 1e-4:
            pieces.append(RoofPiece(shapely.geometry.polygon.orient(rp, 1.0), 0.0, 0.0,
                                    z_fill, min(z_fill, z_hi), max(z_fill, z_hi)))
    return pieces


def _build_from_pieces(buf: TriBuf, spec: BuildingSpec, poly: Polygon, z0: float,
                       sample_pieces: Sequence[RoofPiece], cap_pieces: Sequence[RoofPiece],
                       risers: Sequence[tuple[np.ndarray, np.ndarray, float, float, np.ndarray]]) -> None:
    """Shared body for every non-trivial roof: caps, outer walls, step/riser faces, floor slab.

    ``sample_pieces`` are the planes that define the *outermost* top surface at each point — they
    drive the wall tops.  ``cap_pieces`` are the pieces whose cap geometry should be emitted here;
    they differ from ``sample_pieces`` for a level that has its own parapet, whose cap is emitted by
    the caller as a coping band plus a recessed deck.
    """
    ext, holes = ring_coords(poly)
    rings = [ext] + holes
    u_origin = [ring_uv_origin(ext, spec.facade_heading)] + [0] * len(holes)
    bidx = _BoundaryIndex(rings, u_origin)

    for piece in cap_pieces:
        pe, ph = ring_coords(shapely.geometry.polygon.orient(piece.poly, 1.0))
        _emit_cap(buf, [pe] + ph, piece.z_at, spec.mat_roof, up=True)

    # (ring index, edge index) -> [(t along the edge, x, y, z_roof)]
    samples: dict[tuple[int, int], list[tuple[float, float, float, float]]] = {}
    for piece in sample_pieces:
        pe, ph = ring_coords(shapely.geometry.polygon.orient(piece.poly, 1.0))
        for ring in [pe] + ph:
            if len(ring) < 3:
                continue
            dist, _, k, tt = bidx.locate(ring)
            for i in np.nonzero(dist < 2e-3)[0]:
                seg_i = int(k[i])
                ri = int(bidx.ring[seg_i])
                ei = int(bidx.edge[seg_i])
                x, y = float(ring[i, 0]), float(ring[i, 1])
                z = piece.z_pt(x, y)
                t = float(tt[i])
                n_edges = len(rings[ri])
                eps = WELD_M / max(float(bidx.len[seg_i]), 1e-9)
                samples.setdefault((ri, ei), []).append((t, x, y, z))
                # a vertex sitting on a ring corner belongs to both adjacent edges
                if t <= eps:
                    samples.setdefault((ri, (ei - 1) % n_edges), []).append((1.0, x, y, z))
                elif t >= 1.0 - eps:
                    samples.setdefault((ri, (ei + 1) % n_edges), []).append((0.0, x, y, z))

    for ri, ring in enumerate(rings):
        _emit_ring_walls(buf, ring, ri, u_origin[ri], samples, z0, spec.mat_wall)
    for r in risers:
        p, q, zl, zh, nrm = r[0], r[1], r[2], r[3], r[4]
        _emit_riser(buf, p, q, zl, zh, nrm, spec.mat_wall, v_ref=z0,
                    z_hi_q=(r[5] if len(r) > 5 else None))
    _emit_cap(buf, rings, z0, spec.mat_wall, up=False)


# --------------------------------------------------------------------------- stepped massing
def _build_stepped(buf: TriBuf, spec: BuildingSpec, poly: Polygon, z0: float, z1: float, lod: int) -> None:
    """Real stepped massing: one flat level per recovered CityGML roof level, plus step faces.

    ``spec.roof_steps`` holds ``(region, z)`` pairs that tile ``poly`` exactly (they were produced
    by successive GEOS differences of the same footprint), so adjacent regions share bit-identical
    boundaries and the vertical step face welds to both level caps.  The tallest level sits at
    ``roof_z``, so the building's overall height is still the measured one.
    """
    steps = [(r, z) for r, z in (spec.roof_steps or []) if r is not None and not r.is_empty]
    if len(steps) < 2:
        _build_flat(buf, spec, poly, z0, z1, lod)
        return

    sample_pieces: list[RoofPiece] = []
    cap_pieces: list[RoofPiece] = []
    risers: list = []
    region_pieces: list[tuple[int, RoofPiece]] = []

    for i, (region, z_top) in enumerate(steps):
        region = shapely.geometry.polygon.orient(region, 1.0)
        z_top = max(z_top, z0 + 0.05)
        flat_piece = RoofPiece(region, 0.0, 0.0, z_top, z_top, z_top)
        sample_pieces.append(flat_piece)
        region_pieces.append((i, flat_piece))
        if _parapet_wanted_for(region.area, z_top - z0, spec.floors, spec.roof.parapet_h, lod):
            if _emit_parapet(buf, spec, region, z0, z_top):
                continue                               # coping band + deck emitted, no plain cap
        cap_pieces.append(RoofPiece(region, 0.0, 0.0, z_top, z_top, z_top))

    risers.extend(_step_risers(steps, region_pieces))
    _build_from_pieces(buf, spec, poly, z0, sample_pieces, cap_pieces, risers)


def _step_risers(steps: Sequence[tuple[Polygon, float]], region_pieces: Sequence[tuple[int, RoofPiece]]
                 ) -> list[tuple[np.ndarray, np.ndarray, float, float, np.ndarray, float]]:
    """Vertical faces where a taller level abuts a shorter one.

    Walked from the taller side, over the *pieces* that define its top surface rather than over the
    region outline, so each riser's top edge carries the exact vertices and heights of the cap it
    has to weld to — flat for a flat level, sloping for a level whose main mass is pitched.  Each
    shared edge is visited once from each side and emitted only from the taller one.
    """
    out: list[tuple[np.ndarray, np.ndarray, float, float, np.ndarray, float]] = []
    for ridx, piece in region_pieces:
        ext, holes = ring_coords(shapely.geometry.polygon.orient(piece.poly, 1.0))
        for ring in [ext] + holes:
            if len(ring) < 3:
                continue
            nxt = ring + _edge_vectors(ring)
            for e in range(len(ring)):
                p, q = ring[e], nxt[e]
                dx, dy = q[0] - p[0], q[1] - p[1]
                seg = math.hypot(dx, dy)
                if seg < WELD_M:
                    continue
                nx, ny = dy / seg, -dx / seg           # outward normal of a CCW ring
                zp = piece.z_pt(p[0], p[1])
                zq = piece.z_pt(q[0], q[1])
                mx = (p[0] + q[0]) / 2 + nx * 0.02
                my = (p[1] + q[1]) / 2 + ny * 0.02
                probe = shapely.Point(mx, my)
                for j, (other, z_lo) in enumerate(steps):
                    if j == ridx or z_lo >= max(zp, zq) - WELD_M:
                        continue
                    if other.contains(probe):
                        out.append((p, q, z_lo, zp, np.array([nx, ny]), zq))
                        break
    return out


def _parapet_wanted_for(area: float, height: float, floors: int, parapet_h: float, lod: int) -> bool:
    if lod >= 1 or parapet_h <= 0.0:
        return False
    return height >= PARAPET_MIN_H_M and area >= PARAPET_MIN_AREA_M2 and floors >= PARAPET_MIN_FLOORS


def _emit_parapet(buf: TriBuf, spec: BuildingSpec, region: Polygon, z0: float, z_top: float) -> bool:
    """Coping band at ``z_top`` plus the inner face and the recessed deck.  False if it does not fit."""
    try:
        cand = region.buffer(-PARAPET_T_M, join_style=2, mitre_limit=2.0)
    except Exception:
        return False
    if cand is None or cand.is_empty:
        return False
    inner = [p for p in _iter_polygons(cand) if p.area >= 4.0]
    if not inner or sum(p.area for p in inner) < 0.25 * region.area:
        return False
    try:
        band = region.difference(shapely.union_all(inner))
    except Exception:
        return False
    if band is None or band.is_empty:
        return False
    z_deck = z_top - spec.roof.parapet_h
    for bp in _iter_polygons(band):
        if bp.area < 1e-4:
            continue
        be, bh = ring_coords(shapely.geometry.polygon.orient(bp, 1.0))
        _emit_cap(buf, [be] + bh, z_top, spec.mat_wall, up=True)
    for ip in inner:
        ip = shapely.geometry.polygon.orient(ip, 1.0)
        ie, ih = ring_coords(ip)
        _emit_wall_ring(buf, ie[::-1].copy(), z_deck, z_top, 0, spec.mat_wall, v_ref=z0)
        for h in ih:
            _emit_wall_ring(buf, h[::-1].copy(), z_deck, z_top, 0, spec.mat_wall, v_ref=z0)
        _emit_cap(buf, [ie] + ih, z_deck, spec.mat_roof, up=True)
    return True


def _emit_ring_walls(buf: TriBuf, ring: np.ndarray, ri: int, u0: int,
                     samples: dict[tuple[int, int], list[tuple[float, float, float, float]]],
                     z0: float, mat: int) -> None:
    """One wall strip per *original* footprint edge, its top a polyline that follows the roof.

    Keeping the bottom edge un-split is what makes the shell close: the bottom cap is triangulated
    on the untouched ring, and every extra vertex the roof needs lives on the top polyline only.
    """
    n = len(ring)
    if n < 3:
        return
    u = _cumulative_u(ring, u0)
    for i in range(n):
        j = (i + 1) % n
        p, q = ring[i], ring[j]
        seg = math.hypot(q[0] - p[0], q[1] - p[1])
        if seg < WELD_M:
            continue
        pts = sorted(samples.get((ri, i), []), key=lambda r: r[0])
        if len(pts) < 2:
            continue
        # Group the samples by position along the edge.  Two samples at the same position with
        # different heights are a *step*: the facade has a vertical edge there, and both heights
        # must stay in the polyline or the jump is left open.  Within such a group the heights are
        # ordered so the polyline stays connected (nearest to the previous height first).
        groups: list[list[tuple[float, float, float, float]]] = []
        for rec in pts:
            if groups and abs(rec[0] - groups[-1][0][0]) * seg < WELD_M:
                groups[-1].append(rec)
            else:
                groups.append([rec])
        top: list[tuple[float, float, float, float]] = []
        prev_z: float | None = None
        for gi, grp in enumerate(groups):
            seen: list[tuple[float, float, float, float]] = []
            for rec in grp:
                if all(abs(rec[3] - s_[3]) > WELD_M for s_ in seen):
                    seen.append(rec)
            if len(seen) > 1:
                if prev_z is not None:
                    seen.sort(key=lambda r: abs(r[3] - prev_z))
                else:
                    nz = groups[gi + 1][0][3] if gi + 1 < len(groups) else seen[0][3]
                    seen.sort(key=lambda r: -abs(r[3] - nz))
            top.extend(seen)
            prev_z = top[-1][3]
        if len(top) < 2 or top[0][0] > 1e-6 or top[-1][0] < 1.0 - 1e-6:
            continue
        b0 = (p[0], p[1], z0)
        b1 = (q[0], q[1], z0)
        uv_b0 = (u[i], 0.0)
        uv_b1 = (u[i] + seg, 0.0)
        for m in range(len(top) - 1, 0, -1):
            ta, xa, ya, za = top[m]
            tb, xb, yb, zb = top[m - 1]
            if m == len(top) - 1:
                buf.tri(b0, b1, (xa, ya, za), uv_b0, uv_b1, (u[i] + ta * seg, za - z0), mat)
            buf.tri(b0, (xa, ya, za), (xb, yb, zb), uv_b0,
                    (u[i] + ta * seg, za - z0), (u[i] + tb * seg, zb - z0), mat)


def _emit_riser(buf: TriBuf, p: np.ndarray, q: np.ndarray, z_lo: float, z_hi: float,
                outward: np.ndarray, mat: int, v_ref: float | None = None,
                z_hi_q: float | None = None) -> None:
    """Single-sided vertical face from ``p`` to ``q`` whose normal points along ``outward``.

    ``z_hi`` is the top at ``p`` and ``z_hi_q`` the top at ``q`` (defaults to ``z_hi``); the two
    differ where a stepped building's taller level carries a pitched roof, so the step face is a
    trapezoid whose top edge follows that roof exactly and welds to its cap.
    """
    dx, dy = q[0] - p[0], q[1] - p[1]
    seg = math.hypot(dx, dy)
    zp, zq = float(z_hi), float(z_hi if z_hi_q is None else z_hi_q)
    if seg < WELD_M or (zp - z_lo < WELD_M and zq - z_lo < WELD_M):
        return
    if dy * outward[0] - dx * outward[1] < 0.0:   # normal of (p->q) is (dy, -dx)
        p, q, dx, dy = q, p, -dx, -dy
        zp, zq = zq, zp
    ref = z_lo if v_ref is None else v_ref
    a = (p[0], p[1], z_lo)
    b = (q[0], q[1], z_lo)
    c = (q[0], q[1], zq)
    d = (p[0], p[1], zp)
    buf.tri(a, b, c, (0.0, z_lo - ref), (seg, z_lo - ref), (seg, zq - ref), mat)
    buf.tri(a, c, d, (0.0, z_lo - ref), (seg, zq - ref), (0.0, zp - ref), mat)


def massing_ring(poly: Polygon, max_verts: int = 8) -> np.ndarray:
    """Box-ish massing outline for LOD2/L2/L3: convex hull simplified to ``max_verts`` corners."""
    hull = poly.convex_hull
    if hull.geom_type != "Polygon":
        hull = poly.envelope
    ring = np.asarray(hull.exterior.coords, dtype=np.float64)[:-1]
    if len(ring) <= max_verts:
        return ring
    diag = math.hypot(*(np.ptp(ring, axis=0)))
    tol = max(0.75, 0.02 * diag)
    for _ in range(12):
        s = hull.simplify(tol, preserve_topology=False)
        if s.geom_type == "Polygon" and not s.is_empty:
            r = np.asarray(s.exterior.coords, dtype=np.float64)[:-1]
            if 3 <= len(r) <= max_verts:
                return r
        tol *= 1.6
    rect = shapely.oriented_envelope(poly)
    if rect.geom_type == "Polygon":
        return np.asarray(rect.exterior.coords, dtype=np.float64)[:-1]
    return ring[:max_verts]


def _build_massing(buf: TriBuf, spec: BuildingSpec) -> None:
    ring = massing_ring(spec.polygon)
    if len(ring) < 3:
        return
    if _signed_area(ring) < 0:
        ring = ring[::-1].copy()
    z0, z1 = float(spec.ground_z), float(spec.roof_z)
    if z1 - z0 < 0.05:
        z1 = z0 + 0.05
    u0 = ring_uv_origin(ring, spec.facade_heading)
    _emit_wall_ring(buf, ring, z0, z1, u0, spec.mat_wall)
    _emit_cap(buf, [ring], z1, spec.mat_roof, up=True)
    _emit_cap(buf, [ring], z0, spec.mat_wall, up=False)


def _signed_area(ring: np.ndarray) -> float:
    x, y = ring[:, 0], ring[:, 1]
    xn = np.concatenate((x[1:], x[:1]))
    yn = np.concatenate((y[1:], y[:1]))
    return 0.5 * float(np.dot(x, yn) - np.dot(y, xn))


# --------------------------------------------------------------------------- watertightness (tests + QA)
def watertight_report(pos: np.ndarray, tris: np.ndarray, weld: float = WELD_M) -> dict:
    """Edge-manifold check on a welded triangle soup.

    Returns counts of boundary (1-face) and non-manifold (>2-face) edges plus the signed volume.
    A closed, outward-oriented solid has ``boundary_edges == 0`` and ``volume > 0``.
    """
    if len(tris) == 0:
        return {"triangles": 0, "boundary_edges": 0, "nonmanifold_edges": 0, "volume_m3": 0.0, "closed": False}
    key = np.round(pos / weld).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    t = inv[tris]
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]], axis=0)
    e_sorted = np.sort(e, axis=1)
    uniq, counts = np.unique(e_sorted, axis=0, return_counts=True)
    _ = uniq
    a, b, c = pos[tris[:, 0]], pos[tris[:, 1]], pos[tris[:, 2]]
    vol = float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0)
    return {
        "triangles": int(len(tris)),
        "boundary_edges": int(np.sum(counts == 1)),
        "nonmanifold_edges": int(np.sum(counts > 2)),
        "volume_m3": vol,
        "closed": bool(np.all(counts == 2)),
    }
