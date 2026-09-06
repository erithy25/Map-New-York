"""Plain-numpy geometry helpers (headings, offsets, connectors, snapping). Angles in degrees.

``math`` headings: 0 = east, counter-clockwise. ``compass`` headings: 0 = north, clockwise.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

MITER_LIMIT = 2.0


def heading_math(dx: np.ndarray | float, dy: np.ndarray | float) -> np.ndarray | float:
    return np.degrees(np.arctan2(dy, dx)) % 360.0


def math_to_compass(deg: np.ndarray | float) -> np.ndarray | float:
    return (90.0 - np.asarray(deg, dtype=np.float64)) % 360.0


def compass_to_math(deg: np.ndarray | float) -> np.ndarray | float:
    return (90.0 - np.asarray(deg, dtype=np.float64)) % 360.0


def angle_diff(a: np.ndarray | float, b: np.ndarray | float) -> np.ndarray | float:
    """Signed difference b - a wrapped to (-180, 180]."""
    d = (np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64) + 180.0) % 360.0 - 180.0
    return np.where(d == -180.0, 180.0, d) if np.ndim(d) else (180.0 if d == -180.0 else float(d))


def seg_lengths(coords: np.ndarray) -> np.ndarray:
    d = np.diff(coords[:, :2], axis=0)
    return np.hypot(d[:, 0], d[:, 1])


def cum_lengths(coords: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(seg_lengths(coords))])


def polyline_length(coords: np.ndarray) -> float:
    return float(seg_lengths(coords).sum())


def dedupe_vertices(coords: np.ndarray, tol: float = 1e-3) -> np.ndarray:
    """Remove consecutive duplicate vertices (keeps first and last)."""
    if len(coords) < 2:
        return coords
    d = seg_lengths(coords)
    keep = np.concatenate([[True], d > tol])
    out = coords[keep]
    if len(out) < 2:
        out = coords[[0, -1]]
    return out


def end_heading(coords: np.ndarray, at_end: bool, lookback_m: float = 8.0) -> float:
    """Math heading of the polyline arriving at its last vertex (``at_end``) or leaving its first vertex.

    Uses the vertex ``lookback_m`` back along the line (or the adjacent vertex if shorter) so a tiny
    terminal jog does not swing the heading.
    """
    c = coords[:, :2]
    if len(c) < 2:
        return 0.0
    if at_end:
        cl = cum_lengths(c)
        target = cl[-1] - lookback_m
        i = int(np.searchsorted(cl, target, side="right")) - 1
        i = max(0, min(i, len(c) - 2))
        p = _interp_at(c, cl, max(target, 0.0)) if cl[-1] > lookback_m else c[0]
        v = c[-1] - p
    else:
        cl = cum_lengths(c)
        target = lookback_m
        p = _interp_at(c, cl, min(target, cl[-1])) if cl[-1] > lookback_m else c[-1]
        v = p - c[0]
    if not np.any(v):
        v = (c[-1] - c[-2]) if at_end else (c[1] - c[0])
    return float(heading_math(v[0], v[1]))


def _interp_at(c: np.ndarray, cl: np.ndarray, s: float) -> np.ndarray:
    i = int(np.searchsorted(cl, s, side="right")) - 1
    i = max(0, min(i, len(c) - 2))
    seg = cl[i + 1] - cl[i]
    t = 0.0 if seg <= 0 else (s - cl[i]) / seg
    return c[i] + t * (c[i + 1] - c[i])


def point_along(coords: np.ndarray, s: float) -> np.ndarray:
    """Point (x, y, z) at chainage ``s`` metres from the first vertex (clamped)."""
    cl = cum_lengths(coords)
    s = min(max(s, 0.0), cl[-1])
    i = int(np.searchsorted(cl, s, side="right")) - 1
    i = max(0, min(i, len(coords) - 2))
    seg = cl[i + 1] - cl[i]
    t = 0.0 if seg <= 0 else (s - cl[i]) / seg
    return coords[i] + t * (coords[i + 1] - coords[i])


def unit_tangents(coords: np.ndarray) -> np.ndarray:
    d = np.diff(coords[:, :2], axis=0)
    n = np.hypot(d[:, 0], d[:, 1])
    n[n == 0] = 1.0
    return d / n[:, None]


def offset_vectors(coords: np.ndarray) -> np.ndarray:
    """Per-vertex right-hand offset vectors for a unit offset (miter joins, limited).

    ``coords[:, :2] + d * offset_vectors(coords)`` is the polyline offset by ``d`` metres to the right of
    the direction of digitisation (d < 0 -> left).
    """
    t = unit_tangents(coords)
    right = np.stack([t[:, 1], -t[:, 0]], axis=1)          # right-hand normal of each edge
    n = len(coords)
    out = np.empty((n, 2), dtype=np.float64)
    out[0] = right[0]
    out[-1] = right[-1]
    if n > 2:
        a = right[:-1]
        b = right[1:]
        m = a + b
        mn = np.hypot(m[:, 0], m[:, 1])
        cos_half = mn / 2.0                                   # |a+b|/2 = cos(theta/2)
        scale = np.where(cos_half > 1e-6, 1.0 / np.maximum(cos_half, 1.0 / MITER_LIMIT), 1.0)
        mn[mn == 0] = 1.0
        out[1:-1] = m / mn[:, None] * scale[:, None]
        # fully reversed edges (u-turn in the polyline): fall back to the incoming normal
        rev = cos_half <= 1e-6
        if rev.any():
            out[1:-1][rev] = a[rev]
    return out


def offset_polyline(coords: np.ndarray, d: float, vecs: np.ndarray | None = None) -> np.ndarray:
    v = offset_vectors(coords) if vecs is None else vecs
    out = coords.copy()
    out[:, :2] = coords[:, :2] + d * v
    return out


def bezier_connector(p0: np.ndarray, h0: float, p3: np.ndarray, h3: float, n: int = 6) -> np.ndarray:
    """Cubic Bezier from p0 (leaving with math heading h0) to p3 (arriving with heading h3), 3-D.

    Control distance = |p3-p0| / 3, which gives a smooth turn for 90 degree connectors and a straight
    line when the two headings are parallel and aligned.
    """
    p0 = np.asarray(p0, dtype=np.float64)
    p3 = np.asarray(p3, dtype=np.float64)
    d = float(np.hypot(*(p3[:2] - p0[:2])))
    if d < 0.05:
        return np.stack([p0, p3])
    k = d / 3.0
    t0 = np.array([np.cos(np.radians(h0)), np.sin(np.radians(h0))])
    t3 = np.array([np.cos(np.radians(h3)), np.sin(np.radians(h3))])
    c1 = p0[:2] + t0 * k
    c2 = p3[:2] - t3 * k
    s = np.linspace(0.0, 1.0, n)[:, None]
    xy = (1 - s) ** 3 * p0[:2] + 3 * (1 - s) ** 2 * s * c1 + 3 * (1 - s) * s**2 * c2 + s**3 * p3[:2]
    z = (1 - s[:, 0]) * p0[2] + s[:, 0] * p3[2]
    return np.column_stack([xy, z])


class PointSnapper:
    """KD-tree over 2-D points with ids; ``snap`` returns (ids, distances) with -1 for misses."""

    def __init__(self, xy: np.ndarray, ids: np.ndarray) -> None:
        self.xy = np.asarray(xy, dtype=np.float64)
        self.ids = np.asarray(ids)
        self.tree = cKDTree(self.xy) if len(self.xy) else None

    def snap(self, pts: np.ndarray, max_dist: float) -> tuple[np.ndarray, np.ndarray]:
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        if self.tree is None or len(pts) == 0:
            return np.full(len(pts), -1, dtype=np.int64), np.full(len(pts), np.inf)
        dist, idx = self.tree.query(pts, k=1, distance_upper_bound=max_dist)
        ok = np.isfinite(dist)
        out = np.full(len(pts), -1, dtype=np.int64)
        out[ok] = self.ids[idx[ok]]
        return out, dist

    def query_ball(self, pt: np.ndarray, r: float) -> np.ndarray:
        if self.tree is None:
            return np.empty(0, dtype=np.int64)
        return np.asarray(self.tree.query_ball_point(np.asarray(pt, dtype=np.float64), r), dtype=np.int64)


def side_of_line(a: np.ndarray, b: np.ndarray, p: np.ndarray) -> float:
    """> 0 if p is left of the directed line a->b, < 0 if right (2-D)."""
    return float((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]))


def fit_line_pca(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares line through points: returns (centroid, unit direction)."""
    c = xy.mean(axis=0)
    u, s, vt = np.linalg.svd(xy - c, full_matrices=False)
    return c, vt[0]
