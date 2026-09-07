"""Pure-numpy geometry helpers for the CityGML stage (no XML here).

Every function is total: bad input yields a documented ``None``/empty result plus a
reason string that the caller counts, never an exception.

Conventions
-----------
* Coordinates are NYC_TM metres (x east, y north, z up NAVD88).
* A *polygon* is ``[exterior, hole1, hole2, ...]``, each ring an ``(n, 3)`` float64 array
  **without** the closing repeat of the first vertex.
* Triangles are returned as ``(m, 3, 3)`` arrays. Their winding is fixed so that the
  triangle normal equals the polygon's Newell normal (the winding of the source ring).

Performance note: ``numpy.cross``/``numpy.roll`` cost ~40 µs per call in Python overhead, which
dominated a first version (75k calls per 2000 buildings). The helpers below use explicit
component arithmetic and dot products of shifted slices instead.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

try:  # mapbox_earcut is a hard dependency of the pipeline (pyproject), guarded for a clear error
    import mapbox_earcut
except ImportError as _e:  # pragma: no cover
    raise ImportError("mapbox_earcut is required for nycsim_pipeline.buildings.citygml") from _e

SURF_GROUND = 0
SURF_WALL = 1
SURF_ROOF = 2

DUP_TOL_M = 1e-3            # consecutive vertices closer than this are one vertex
COLLINEAR_TOL_M = 1e-3      # a vertex closer than this to the line through its neighbours is removed
MIN_POLY_AREA_M2 = 1e-4     # polygons (3-D area) below this are slivers and are dropped
MIN_TRI_AREA_M2 = 1e-8      # float32 triangles below this (or facing the wrong way) are dropped
PLANARITY_TOL_M = 0.05      # max vertex distance from the best-fit plane before flagging NON_PLANAR


@dataclass
class PolyResult:
    """Triangulated planar polygon with the attributes the classifier needs."""
    tris: np.ndarray            # (m, 3, 3) float64, normal == nhat
    nhat: np.ndarray            # unit normal following the exterior ring winding
    area3d: float               # exterior area minus hole areas (m^2), in the plane
    area_xy: float              # horizontal projection of area3d (m^2)
    centroid: np.ndarray        # (3,) XY area centroid of the exterior ring, mean z
    z_min: float
    z_max: float
    z_mean: float
    max_plane_dev: float        # planarity deviation (m)
    n_holes: int


# --------------------------------------------------------------------------- fast vector helpers
def cross3(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise cross product of two (n, 3) arrays (or two (3,) vectors) without numpy.cross overhead."""
    if a.ndim == 1:
        return np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])
    out = np.empty_like(a)
    out[:, 0] = a[:, 1] * b[:, 2] - a[:, 2] * b[:, 1]
    out[:, 1] = a[:, 2] * b[:, 0] - a[:, 0] * b[:, 2]
    out[:, 2] = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return out


def _cyclic_dot(a: np.ndarray, b: np.ndarray) -> float:
    """sum_i a[i] * b[i+1] with cyclic wrap, as two dots (no roll)."""
    return float(a[:-1] @ b[1:]) + float(a[-1] * b[0])


def newell_normal(pts: np.ndarray) -> np.ndarray:
    """Newell's method: returns ``2 * area * unit_normal`` of a closed ring (any planarity)."""
    if len(pts) < 3:
        return np.zeros(3)
    p = pts - pts[0]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    nx = _cyclic_dot(y, z) - _cyclic_dot(z, y)
    ny = _cyclic_dot(z, x) - _cyclic_dot(x, z)
    nz = _cyclic_dot(x, y) - _cyclic_dot(y, x)
    return np.array([nx, ny, nz])


def plane_basis(nhat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Orthonormal in-plane axes ``(u, v)`` with ``u x v == nhat`` (right-handed)."""
    a = np.array([1.0, 0.0, 0.0]) if abs(nhat[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = cross3(a, nhat)
    u /= math.sqrt(float(u @ u))
    v = cross3(nhat, u)
    return u, v


def ring_area_xy(pts: np.ndarray) -> float:
    """Signed shoelace area of the XY projection (positive = counter-clockwise)."""
    if len(pts) < 3:
        return 0.0
    x = pts[:, 0] - pts[0, 0]
    y = pts[:, 1] - pts[0, 1]
    return 0.5 * (_cyclic_dot(x, y) - _cyclic_dot(y, x))


def ring_centroid_xy(pts: np.ndarray) -> tuple[float, float, float]:
    """(cx, cy, signed_area) of the XY projection of a ring; falls back to the vertex mean when degenerate."""
    x0, y0 = float(pts[0, 0]), float(pts[0, 1])
    x = pts[:, 0] - x0
    y = pts[:, 1] - y0
    x1 = np.concatenate((x[1:], x[:1]))
    y1 = np.concatenate((y[1:], y[:1]))
    cross = x * y1 - x1 * y
    a = 0.5 * float(cross.sum())
    if abs(a) < 1e-9:
        return float(pts[:, 0].mean()), float(pts[:, 1].mean()), 0.0
    cx = float(((x + x1) * cross).sum() / (6.0 * a)) + x0
    cy = float(((y + y1) * cross).sum() / (6.0 * a)) + y0
    return cx, cy, a


# --------------------------------------------------------------------------- ring cleaning
def clean_ring(pts: np.ndarray, tol: float = DUP_TOL_M) -> tuple[np.ndarray, int]:
    """Remove the closing vertex and consecutive (near-)duplicate vertices.

    Returns ``(ring, n_removed)``. The ring may end up with fewer than 3 vertices; the caller
    decides what to do with that.
    """
    pts = np.asarray(pts, dtype=np.float64)
    n0 = len(pts)
    if n0 == 0:
        return pts.reshape(0, 3), 0
    if n0 > 1:
        step = np.abs(pts[1:] - pts[:-1]).max(axis=1)
        keep = np.concatenate(([True], step > tol))
        pts = pts[keep]
    if len(pts) > 1 and np.abs(pts[0] - pts[-1]).max() <= tol:
        pts = pts[:-1]
    return pts, n0 - len(pts)


def remove_collinear(pts: np.ndarray, tol: float = COLLINEAR_TOL_M) -> tuple[np.ndarray, int]:
    """Drop vertices lying within ``tol`` of the line through their two neighbours (and zero-width spikes).

    Such vertices (LiDAR footprint edges carry intermediate points on straight runs) produce
    sliver triangles that flip orientation under float32 quantisation. A single pass; the ring
    keeps at least 3 vertices. Returns ``(ring, n_removed)``.
    """
    n = len(pts)
    if n <= 3:
        return pts, 0
    prev = np.concatenate((pts[-1:], pts[:-1]))
    nxt = np.concatenate((pts[1:], pts[:1]))
    d = nxt - prev
    e = pts - prev
    c = cross3(d, e)
    dlen = np.sqrt((d * d).sum(axis=1))
    dist = np.sqrt((c * c).sum(axis=1)) / np.maximum(dlen, 1e-12)
    drop = (dist < tol) | (dlen < tol)
    if not drop.any():
        return pts, 0
    keep = ~drop
    if keep.sum() < 3:
        return pts, 0
    return pts[keep], int(drop.sum())


# --------------------------------------------------------------------------- triangulation
def triangulate_polygon(rings: list[np.ndarray]) -> tuple[PolyResult | None, str]:
    """Triangulate one planar polygon (exterior + holes) with earcut on its best-fit plane.

    Returns ``(result, reason)``; ``result`` is ``None`` when the polygon was dropped and
    ``reason`` is one of ``degenerate`` (< 3 distinct vertices), ``sliver`` (area below
    ``MIN_POLY_AREA_M2``), ``earcut_empty`` (triangulator produced nothing), ``nonfinite``.
    Holes with < 3 vertices are ignored (reported through ``reason == 'ok:holes_dropped'``).
    """
    if not rings:
        return None, "degenerate"
    ext = rings[0]
    if len(ext) < 3:
        return None, "degenerate"
    if not np.isfinite(ext).all():
        return None, "nonfinite"
    normal = newell_normal(ext)
    twice_area = math.sqrt(float(normal @ normal))
    if twice_area * 0.5 < MIN_POLY_AREA_M2:
        return None, "sliver"
    nhat = normal / twice_area
    holes_dropped = 0
    holes: list[np.ndarray] = []
    hole_area2 = 0.0
    for h in rings[1:]:
        if len(h) < 3 or not np.isfinite(h).all():
            holes_dropped += 1
            continue
        hn = newell_normal(h)
        hole_area2 += math.sqrt(float(hn @ hn))
        holes.append(h)
    area3d = max(0.0, 0.5 * (twice_area - hole_area2))
    if area3d < MIN_POLY_AREA_M2:
        return None, "sliver"

    origin = ext[0]
    u, v = plane_basis(nhat)
    all_pts = ext if not holes else np.concatenate([ext] + holes, axis=0)
    rel = all_pts - origin
    uv = np.empty((len(rel), 2), dtype=np.float64)
    uv[:, 0] = rel @ u
    uv[:, 1] = rel @ v
    ends = np.cumsum([len(ext)] + [len(h) for h in holes]).astype(np.uint32)
    idx = mapbox_earcut.triangulate_float64(uv, ends)
    if idx.size < 3:
        return None, "earcut_empty"
    tris = all_pts[idx.astype(np.int64)].reshape(-1, 3, 3)
    # Fix winding so every triangle normal agrees with the ring's Newell normal.
    tn = cross3(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    flip = (tn @ nhat) < 0
    if flip.any():
        tris[flip] = tris[flip][:, [0, 2, 1]]
    dev = float(np.abs(rel @ nhat).max())
    cx, cy, _ = ring_centroid_xy(ext)
    z = ext[:, 2]
    zmean = float(z.mean())
    res = PolyResult(
        tris=tris, nhat=nhat, area3d=area3d, area_xy=area3d * abs(float(nhat[2])), centroid=np.array([cx, cy, zmean]),
        z_min=float(z.min()), z_max=float(z.max()), z_mean=zmean, max_plane_dev=dev, n_holes=len(holes),
    )
    return res, ("ok:holes_dropped" if holes_dropped else "ok")


def flip_triangles(tris: np.ndarray) -> np.ndarray:
    """Reverse the winding of every triangle (copy)."""
    return tris[:, [0, 2, 1]]


def finalize_triangles(tris: np.ndarray, nhat: np.ndarray) -> tuple[np.ndarray, int]:
    """Quantise to little-endian float32 and drop triangles that became degenerate or flipped.

    The stored coordinates are absolute NYC_TM metres in float32 (ulp 2-4 mm at |x| ~ 1e4 m); a
    sliver thinner than that can change orientation when rounded. Every triangle that leaves this
    function has a float32 normal agreeing with ``nhat`` and an area >= ``MIN_TRI_AREA_M2``.
    Returns ``(tris_f32, n_dropped)``.
    """
    t32 = tris.astype("<f4")
    t = t32.astype(np.float64)
    n = cross3(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ok = ((n @ nhat) > 0) & (0.5 * np.sqrt((n * n).sum(axis=1)) >= MIN_TRI_AREA_M2)
    if ok.all():
        return t32, 0
    return t32[ok], int((~ok).sum())


def slope_deg(nhat: np.ndarray) -> float:
    """Angle between the face normal and vertical, degrees (0 = horizontal face, 90 = vertical)."""
    return math.degrees(math.acos(min(1.0, abs(float(nhat[2])))))


def azimuth_deg(nhat: np.ndarray) -> float:
    """Direction the face *faces* (its down-slope direction) in degrees, 0 = east, CCW, in [0, 360)."""
    a = math.degrees(math.atan2(float(nhat[1]), float(nhat[0])))
    return a + 360.0 if a < 0 else a


# --------------------------------------------------------------------------- clustering helpers
def cluster_1d(values: np.ndarray, tol: float) -> list[np.ndarray]:
    """Gap clustering of scalar values: a new cluster starts where the sorted gap exceeds ``tol``.

    Returns index arrays into ``values``.
    """
    if values.size == 0:
        return []
    order = np.argsort(values, kind="stable")
    s = values[order]
    cuts = np.nonzero(np.diff(s) > tol)[0] + 1
    return [order[g] for g in np.split(np.arange(values.size), cuts)]


def cluster_circular(angles_deg: np.ndarray, tol: float) -> list[np.ndarray]:
    """Gap clustering on a circle (degrees). The first and last clusters merge if they wrap within ``tol``."""
    a = np.mod(angles_deg, 360.0)
    groups = cluster_1d(a, tol)
    if len(groups) > 1:
        lo = a[groups[0]].min()
        hi = a[groups[-1]].max()
        if lo + 360.0 - hi <= tol:
            groups = [np.concatenate([groups[-1], groups[0]])] + groups[1:-1]
    return groups


def circular_mean_deg(angles_deg: np.ndarray, weights: np.ndarray | None = None) -> float:
    r = np.radians(angles_deg)
    w = np.ones_like(r) if weights is None else np.asarray(weights, dtype=np.float64)
    m = math.degrees(math.atan2(float((w * np.sin(r)).sum()), float((w * np.cos(r)).sum())))
    return m + 360.0 if m < 0 else m


def angular_distance_deg(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return 360.0 - d if d > 180.0 else d


def weld_vertex_count(tri_xyz_f32: np.ndarray) -> int:
    """Number of distinct vertices after float32 quantisation (what a mesh importer would weld)."""
    if tri_xyz_f32.size == 0:
        return 0
    v = np.ascontiguousarray(tri_xyz_f32.reshape(-1, 3))
    packed = v.view(np.dtype((np.void, v.dtype.itemsize * 3))).ravel()
    return int(np.unique(packed).size)
