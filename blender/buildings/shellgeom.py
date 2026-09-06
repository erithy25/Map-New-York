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
  edge whose outward normal best matches ``primary_facade_heading``), ``v = z - ground_z``.
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
DOME_BANDS = 6
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


@dataclass
class TriBuf:
    """Welded triangle accumulator for a single building (positions welded at 1 mm)."""

    pos: list[tuple[float, float, float]] = field(default_factory=list)
    tris: list[tuple[int, int, int]] = field(default_factory=list)
    uvs: list[tuple[float, float, float, float, float, float]] = field(default_factory=list)
    mats: list[int] = field(default_factory=list)
    _index: dict[tuple[int, int, int], int] = field(default_factory=dict)

    def vid(self, x: float, y: float, z: float) -> int:
        key = (int(round(x / WELD_M)), int(round(y / WELD_M)), int(round(z / WELD_M)))
        i = self._index.get(key)
        if i is None:
            i = len(self.pos)
            self._index[key] = i
            self.pos.append((x, y, z))
        return i

    def tri(self, a: Sequence[float], b: Sequence[float], c: Sequence[float],
            uva: Sequence[float], uvb: Sequence[float], uvc: Sequence[float], mat: int) -> None:
        ia, ib, ic = self.vid(*a), self.vid(*b), self.vid(*c)
        if ia == ib or ib == ic or ia == ic:
            return  # degenerate after welding
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
    ext = np.asarray(poly.exterior.coords, dtype=np.float64)[:-1]
    holes = [np.asarray(r.coords, dtype=np.float64)[:-1] for r in poly.interiors]
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
    d = np.roll(ring, -1, axis=0) - ring
    seg = np.hypot(d[:, 0], d[:, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        nx, ny = d[:, 1] / seg, -d[:, 0] / seg          # outward normal for a CCW ring
    want = math.radians(90.0 - float(heading_deg))       # compass -> math angle
    score = nx * math.cos(want) + ny * math.sin(want)
    score = np.where(seg > 0.5, score, -2.0)             # ignore stub edges
    return int(np.argmax(score))


def _cumulative_u(ring: np.ndarray, start: int) -> np.ndarray:
    """Arc length at each ring vertex, measured from vertex ``start`` going forward."""
    n = len(ring)
    order = (np.arange(n) - start) % n
    d = np.roll(ring, -1, axis=0) - ring
    seg = np.hypot(d[:, 0], d[:, 1])
    seg_ordered = seg[(np.arange(n) + start) % n]
    cum_ordered = np.concatenate([[0.0], np.cumsum(seg_ordered)[:-1]])
    u = np.empty(n)
    u[(np.arange(n) + start) % n] = cum_ordered
    _ = order
    return u


# --------------------------------------------------------------------------- wall emission
def _emit_wall_ring(buf: TriBuf, ring: np.ndarray, z0: float, ztop, u0_index: int, mat: int) -> None:
    """Vertical wall around one ring.  ``ztop`` is a scalar or a per-vertex array."""
    n = len(ring)
    if n < 3:
        return
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
        buf.tri(b0, b1, t1, (ui, 0.0), (uj, 0.0), (uj, zj - z0), mat)
        buf.tri(b0, t1, t0, (ui, 0.0), (uj, zj - z0), (ui, zi - z0), mat)


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
    """One planar roof region: ``z = a*x + b*y + d`` over ``poly``."""

    poly: Polygon
    a: float
    b: float
    d: float

    def z_at(self, pts: np.ndarray) -> np.ndarray:
        return self.a * pts[:, 0] + self.b * pts[:, 1] + self.d

    def z_pt(self, x: float, y: float) -> float:
        return self.a * x + self.b * y + self.d


def _plane_from_local(c: np.ndarray, axis: np.ndarray, k: float, z_at_zero: float) -> tuple[float, float, float]:
    """Plane with z = z_at_zero - k * ((p - c) · axis)."""
    a = -k * axis[0]
    b = -k * axis[1]
    d = z_at_zero + k * float(np.dot(c, axis))
    return a, b, d


def roof_pieces(poly: Polygon, roof: RoofSpec, z_eave: float, z_top: float) -> tuple[list[RoofPiece], list[tuple[np.ndarray, np.ndarray, float, float]]]:
    """Decompose a pitched roof into planar regions clipped to the footprint.

    Returns ``(pieces, risers)`` where each riser is ``(p, q, z_lo, z_hi)`` — a vertical quad used
    by the sawtooth profile.  The union of the pieces is the whole footprint, so the resulting
    surface is a continuous height field and the shell closes.
    """
    c, ea, eb, a, b = obb_frame(poly)
    rise = z_top - z_eave
    big = 4.0 * (a + b) + 50.0
    pieces: list[RoofPiece] = []
    risers: list[tuple[np.ndarray, np.ndarray, float, float]] = []
    kind = roof.kind

    def clip(region: Polygon) -> list[Polygon]:
        try:
            inter = poly.intersection(region)
        except Exception:
            return []
        return [p for p in _iter_polygons(inter) if p.area > 1e-4]

    if kind == ROOF_GABLE:
        k = rise / b
        for sign in (1.0, -1.0):
            reg = _wedge(c, ea, eb, [(-big, 0.0), (big, 0.0), (big, sign * big), (-big, sign * big)])
            if sign < 0:
                reg = Polygon(list(reg.exterior.coords)[::-1])
            pa, pb_, pd = _plane_from_local(c, eb * sign, k, z_top)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd))

    elif kind == ROOF_HIP:
        k = rise / b
        r = max(a - b, 0.0)
        # four regions of z = z_top - k * max(|v|, |u| - (a - b), 0)
        quads = {
            "N": [(-r, 0.0), (r, 0.0), (r + big, big), (-r - big, big)],
            "S": [(r, 0.0), (-r, 0.0), (-r - big, -big), (r + big, -big)],
            "E": [(r, 0.0), (r + big, big), (r + big, -big)],
            "W": [(-r, 0.0), (-r - big, -big), (-r - big, big)],
        }
        axes = {"N": eb, "S": -eb, "E": ea, "W": -ea}
        for key, corners in quads.items():
            reg = _wedge(c, ea, eb, corners)
            if not reg.is_valid:
                reg = shapely.make_valid(reg)
            axis = axes[key]
            z0_axis = z_top if key in ("N", "S") else z_top + k * r
            pa, pb_, pd = _plane_from_local(c, axis, k, z0_axis)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd))

    elif kind == ROOF_MANSARD:
        f = MANSARD_DECK_FRAC
        r = max(a - b, 0.0)
        deck = _wedge(c, ea, eb, [(-r - f * b, -f * b), (r + f * b, -f * b), (r + f * b, f * b), (-r - f * b, f * b)])
        for q in clip(deck):
            pieces.append(RoofPiece(q, 0.0, 0.0, z_top))
        k = rise / max(b * (1.0 - f), 1e-6)
        quads = {
            "N": [(-r, f * b), (r, f * b), (r + big, big), (-r - big, big)],
            "S": [(r, -f * b), (-r, -f * b), (-r - big, -big), (r + big, -big)],
            "E": [(r + f * b, -f * b), (r + f * b, f * b), (r + big, big), (r + big, -big)],
            "W": [(-r - f * b, f * b), (-r - f * b, -f * b), (-r - big, -big), (-r - big, big)],
        }
        axes = {"N": eb, "S": -eb, "E": ea, "W": -ea}
        offs = {"N": f * b, "S": f * b, "E": r + f * b, "W": r + f * b}
        for key, corners in quads.items():
            reg = _wedge(c, ea, eb, corners)
            if not reg.is_valid:
                reg = shapely.make_valid(reg)
            base = deck.buffer(0)
            try:
                reg = reg.difference(base)
            except Exception:
                pass
            axis = axes[key]
            pa, pb_, pd = _plane_from_local(c, axis, k, z_top + k * offs[key])
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd))

    elif kind == ROOF_SHED:
        k = rise / (2.0 * b)
        pa, pb_, pd = _plane_from_local(c, -eb, k, z_top - k * b)
        pieces.append(RoofPiece(poly, pa, pb_, pd))

    elif kind == ROOF_SAWTOOTH:
        period = max(SAWTOOTH_PERIOD_M, 2.0 * b / 12.0)
        n_band = max(1, int(math.ceil(2.0 * b / period)))
        period = 2.0 * b / n_band
        k = rise / period
        for i in range(n_band):
            v0 = -b + i * period
            v1 = v0 + period
            reg = _wedge(c, ea, eb, [(-big, v0), (big, v0), (big, v1), (-big, v1)])
            pa, pb_, pd = _plane_from_local(c, -eb, k, z_eave - k * v0)
            for q in clip(reg):
                pieces.append(RoofPiece(q, pa, pb_, pd))
            if i < n_band - 1:
                line = shapely.LineString([tuple(c + (-big) * ea + v1 * eb), tuple(c + big * ea + v1 * eb)])
                inter = poly.intersection(line)
                for seg in _iter_lines(inter):
                    coords = np.asarray(seg.coords, dtype=np.float64)
                    for s in range(len(coords) - 1):
                        risers.append((coords[s], coords[s + 1], z_eave, z_top))

    elif kind in (ROOF_DOME, ROOF_BARREL):
        if kind == ROOF_DOME:
            rmax = max(a, b)
            n = DOME_BANDS
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                z0b = z_eave + rise * math.sqrt(max(0.0, 1.0 - t1 * t1))
                z1b = z_eave + rise * math.sqrt(max(0.0, 1.0 - t0 * t0))
                inner = poly.centroid.buffer(t0 * rmax, quad_segs=8) if t0 > 0 else None
                outer = poly.centroid.buffer(t1 * rmax, quad_segs=8)
                reg = outer if inner is None else outer.difference(inner)
                kk = (z1b - z0b) / max((t1 - t0) * rmax, 1e-6)
                cc = np.asarray(poly.centroid.coords[0])
                # radial band approximated by a plane through the band's mean gradient along +x
                pa, pb_, pd = 0.0, 0.0, (z0b + z1b) / 2.0
                _ = kk, cc
                for q in clip(reg):
                    pieces.append(RoofPiece(q, pa, pb_, pd))
        else:
            n = BARREL_BANDS
            for i in range(n):
                v0 = -b + 2.0 * b * i / n
                v1 = -b + 2.0 * b * (i + 1) / n
                z0b = z_eave + rise * math.sqrt(max(0.0, 1.0 - (v0 / b) ** 2))
                z1b = z_eave + rise * math.sqrt(max(0.0, 1.0 - (v1 / b) ** 2))
                k = (z0b - z1b) / (v1 - v0)
                reg = _wedge(c, ea, eb, [(-big, v0), (big, v0), (big, v1), (-big, v1)])
                pa, pb_, pd = _plane_from_local(c, eb, k, z0b + k * v0)
                for q in clip(reg):
                    pieces.append(RoofPiece(q, pa, pb_, pd))
    else:
        pieces.append(RoofPiece(poly, 0.0, 0.0, z_top))
    if not pieces:
        pieces.append(RoofPiece(poly, 0.0, 0.0, z_top))
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
        segs_p, segs_d, segs_u, segs_len, segs_ring = [], [], [], [], []
        for ri, ring in enumerate(rings):
            if len(ring) < 3:
                continue
            u = _cumulative_u(ring, u_origin[ri])
            nxt = np.roll(ring, -1, axis=0)
            d = nxt - ring
            segs_p.append(ring)
            segs_d.append(d)
            segs_u.append(u)
            segs_len.append(np.hypot(d[:, 0], d[:, 1]))
            segs_ring.append(np.full(len(ring), ri))
        self.p = np.vstack(segs_p) if segs_p else np.zeros((0, 2))
        self.d = np.vstack(segs_d) if segs_d else np.zeros((0, 2))
        self.u = np.concatenate(segs_u) if segs_u else np.zeros(0)
        self.len = np.concatenate(segs_len) if segs_len else np.zeros(0)
        self.ring = np.concatenate(segs_ring) if segs_ring else np.zeros(0, dtype=int)
        self.len2 = np.maximum(self.len ** 2, 1e-18)

    def locate(self, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """For each query point: (distance to the boundary, arc length u, matched segment index)."""
        if len(self.p) == 0:
            return np.full(len(pts), 1e9), np.zeros(len(pts)), np.zeros(len(pts), dtype=int)
        w = pts[:, None, :] - self.p[None, :, :]
        t = (w[:, :, 0] * self.d[None, :, 0] + w[:, :, 1] * self.d[None, :, 1]) / self.len2[None, :]
        t = np.clip(t, 0.0, 1.0)
        proj = self.p[None, :, :] + t[:, :, None] * self.d[None, :, :]
        dist = np.hypot(pts[:, None, 0] - proj[:, :, 0], pts[:, None, 1] - proj[:, :, 1])
        k = np.argmin(dist, axis=1)
        rows = np.arange(len(pts))
        return dist[rows, k], self.u[k] + t[rows, k] * self.len[k], k


# --------------------------------------------------------------------------- the builder
def build_shell(spec: BuildingSpec, lod: int = 0) -> TriBuf:
    """Closed shell for one building at the requested LOD."""
    buf = TriBuf()
    if lod >= 2:
        _build_massing(buf, spec)
        return buf
    poly = spec.polygon
    if lod == 1:
        poly = _simplify_for_lod1(poly)
        if poly is None:
            _build_massing(buf, spec)
            return buf
    z0 = float(spec.ground_z)
    z1 = float(spec.roof_z)
    if z1 - z0 < 0.05:
        z1 = z0 + 0.05
    kind = spec.roof.kind
    if kind in (ROOF_FLAT, ROOF_COMPLEX):
        _build_flat(buf, spec, poly, z0, z1, lod)
    else:
        _build_pitched(buf, spec, poly, z0, z1, lod)
    return buf


def _simplify_for_lod1(poly: Polygon, tol: float = 0.25) -> Polygon | None:
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
    holes = [r for r in p.interiors if abs(Polygon(r).area) >= 20.0]
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
        _emit_wall_ring(buf, ie[::-1].copy(), z_deck, z1, 0, spec.mat_wall)
        for h in ih:
            _emit_wall_ring(buf, h[::-1].copy(), z_deck, z1, 0, spec.mat_wall)
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
    h = z1 - z0
    rise = min(natural, MAX_RISE_FRAC * h, max(h - MIN_WALL_H_M, 0.25 * h))
    rise = max(rise, 0.35)
    z_eave = z1 - rise
    if z_eave <= z0 + 0.3:
        z_eave = z0 + 0.3 * h
    pieces, risers = roof_pieces(poly, spec.roof, z_eave, z1)
    if lod >= 1 and len(pieces) > 4:
        pieces = pieces[:4] if spec.roof.kind not in (ROOF_SAWTOOTH,) else pieces[::2] or pieces[:1]
    _ = c, ea, eb, a
    return z_eave, pieces, risers


def _build_pitched(buf: TriBuf, spec: BuildingSpec, poly: Polygon, z0: float, z1: float, lod: int) -> None:
    z_eave, pieces, risers = _pitched_geometry(spec, poly, z0, z1, lod)
    ext, holes = ring_coords(poly)
    rings = [ext] + holes
    u_origin = [ring_uv_origin(ext, spec.facade_heading)] + [0] * len(holes)
    bidx = _BoundaryIndex(rings, u_origin)

    covered_area = 0.0
    for piece in pieces:
        pe, ph = ring_coords(shapely.geometry.polygon.orient(piece.poly, 1.0))
        covered_area += piece.poly.area
        _emit_cap(buf, [pe] + ph, piece.z_at, spec.mat_roof, up=True)
        for ring in [pe] + ph:
            _emit_piece_walls(buf, ring, piece, bidx, z0, spec.mat_wall)
    if covered_area < 0.98 * poly.area:
        # numerical shortfall: cover the remainder flat at the eave so the shell still closes
        try:
            rest = poly.difference(shapely.union_all([p.poly for p in pieces]))
        except Exception:
            rest = None
        if rest is not None and not rest.is_empty:
            for rp in _iter_polygons(rest):
                if rp.area < 1e-3:
                    continue
                rp = shapely.geometry.polygon.orient(rp, 1.0)
                re_, rh = ring_coords(rp)
                piece = RoofPiece(rp, 0.0, 0.0, z_eave)
                _emit_cap(buf, [re_] + rh, piece.z_at, spec.mat_roof, up=True)
                for ring in [re_] + rh:
                    _emit_piece_walls(buf, ring, piece, bidx, z0, spec.mat_wall)
    for p, q, zl, zh in risers:
        _emit_riser(buf, p, q, zl, zh, spec.mat_roof)
    _emit_cap(buf, rings, z0, spec.mat_wall, up=False)


def _emit_piece_walls(buf: TriBuf, ring: np.ndarray, piece: RoofPiece, bidx: _BoundaryIndex,
                      z0: float, mat: int) -> None:
    """Emit the vertical wall under every edge of a roof piece that lies on the footprint boundary."""
    n = len(ring)
    if n < 3:
        return
    nxt = np.roll(ring, -1, axis=0)
    mids = 0.5 * (ring + nxt)
    dist_m, _, k = bidx.locate(mids)
    on = dist_m < 2e-3
    if not on.any():
        return
    dist_v, u_v, _ = bidx.locate(ring)
    for i in np.nonzero(on)[0]:
        j = (i + 1) % n
        p, q = ring[i], nxt[i]
        seg = math.hypot(q[0] - p[0], q[1] - p[1])
        if seg < WELD_M:
            continue
        if dist_v[i] > 2e-3 or dist_v[j] > 2e-3:
            continue
        fd = bidx.d[k[i]]
        forward = (q[0] - p[0]) * fd[0] + (q[1] - p[1]) * fd[1] >= 0.0
        ui, uj = u_v[i], u_v[j]
        zi, zj = piece.z_pt(p[0], p[1]), piece.z_pt(q[0], q[1])
        if zi <= z0 + WELD_M and zj <= z0 + WELD_M:
            continue
        b0 = (p[0], p[1], z0)
        b1 = (q[0], q[1], z0)
        t1 = (q[0], q[1], zj)
        t0 = (p[0], p[1], zi)
        if forward:
            buf.tri(b0, b1, t1, (ui, 0.0), (uj, 0.0), (uj, zj - z0), mat)
            buf.tri(b0, t1, t0, (ui, 0.0), (uj, zj - z0), (ui, zi - z0), mat)
        else:
            buf.tri(b1, b0, t0, (uj, 0.0), (ui, 0.0), (ui, zi - z0), mat)
            buf.tri(b1, t0, t1, (uj, 0.0), (ui, zi - z0), (uj, zj - z0), mat)


def _emit_riser(buf: TriBuf, p: np.ndarray, q: np.ndarray, z_lo: float, z_hi: float, mat: int) -> None:
    seg = math.hypot(q[0] - p[0], q[1] - p[1])
    if seg < WELD_M or z_hi - z_lo < WELD_M:
        return
    a = (p[0], p[1], z_lo)
    b = (q[0], q[1], z_lo)
    c = (q[0], q[1], z_hi)
    d = (p[0], p[1], z_hi)
    buf.tri(a, b, c, (0.0, 0.0), (seg, 0.0), (seg, z_hi - z_lo), mat)
    buf.tri(a, c, d, (0.0, 0.0), (seg, z_hi - z_lo), (0.0, z_hi - z_lo), mat)
    buf.tri(a, c, b, (0.0, 0.0), (seg, z_hi - z_lo), (seg, 0.0), mat)
    buf.tri(a, d, c, (0.0, 0.0), (0.0, z_hi - z_lo), (seg, z_hi - z_lo), mat)


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
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


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
