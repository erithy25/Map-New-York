"""Primary facade heading from footprint geometry (DATA_CONTRACTS §5 ``primary_facade_heading``).

Method (fully vectorised over all rings):
1. exterior ring oriented counter-clockwise; consecutive edges whose direction differs by < 8 deg are merged into one
   straight *run* (digitised facades are often split into several collinear segments), including across the ring's
   start vertex;
2. a run is a *party wall* when a probe point 0.3 m outside its midpoint lies within 0.5 m of another footprint —
   such runs cannot be street-facing;
3. among the free runs >= 2 m long, the winner maximises ``length x (1 + 0.6 x max(0, cos(theta)))`` where theta is the
   angle between the run's outward normal and the direction from the PLUTO lot centroid to the building centroid
   (a building sits at the street side of its lot, so the street facade faces away from the lot centroid);
4. with no free run >= 2 m the longest run of the ring is used.

The heading is the compass bearing of the outward normal of the chosen run (0 = north, clockwise). The method code
per building is stored in ``facade_heading_method`` (§5.2). Without street geometry this is the best purely
geometric estimate; the roads stage can refine it with ``street_segment_id``.
"""
from __future__ import annotations

import logging

import numpy as np
import shapely

from . import schema as S

log = logging.getLogger("nycsim.buildings.facade")

ANGLE_TOL_DEG = 8.0
MIN_EDGE_M = 2.0
PROBE_OFFSET_M = 0.3
NEAR_M = 0.5
LOT_BIAS = 0.6
LOT_MIN_DIST_M = 1.5
QUERY_CHUNK = 500_000


def _wrap(a: np.ndarray) -> np.ndarray:
    return (a + np.pi) % (2 * np.pi) - np.pi


def facade_headings(geoms: np.ndarray, cx: np.ndarray, cy: np.ndarray, lot_x: np.ndarray, lot_y: np.ndarray,
                    tree: shapely.STRtree) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (heading_deg float32, method int8, stats) aligned with ``geoms`` (Polygons)."""
    n = len(geoms)
    polys = shapely.orient_polygons(geoms)          # exterior CCW
    rings = shapely.get_exterior_ring(polys)
    coords, ridx = shapely.get_coordinates(rings, return_index=True)
    same = ridx[1:] == ridx[:-1]
    e_ring = ridx[:-1][same]
    p0 = np.nonzero(same)[0]
    ex = (coords[1:, 0] - coords[:-1, 0])[same]
    ey = (coords[1:, 1] - coords[:-1, 1])[same]
    L = np.hypot(ex, ey)
    nz = L > 1e-9
    e_ring, p0, ex, ey, L = e_ring[nz], p0[nz], ex[nz], ey[nz], L[nz]
    ang = np.arctan2(ey, ex)
    tol = np.deg2rad(ANGLE_TOL_DEG)

    # ---- merge collinear consecutive edges into runs ---------------------------------------------------------------
    brk = (e_ring[1:] != e_ring[:-1]) | (np.abs(_wrap(ang[1:] - ang[:-1])) > tol)
    first = np.concatenate([[0], np.nonzero(brk)[0] + 1])
    last = np.concatenate([first[1:] - 1, [len(e_ring) - 1]])
    run_of_edge = np.repeat(np.arange(len(first)), last - first + 1)
    nrun = len(first)
    rx = np.bincount(run_of_edge, ex, nrun)
    ry = np.bincount(run_of_edge, ey, nrun)
    r_ring = e_ring[first]
    r_start = p0[first]           # coordinate index of run start
    r_end = p0[last] + 1          # coordinate index of run end
    alive = np.ones(nrun, dtype=bool)

    # wrap-around: merge the last run of a ring into its first run when collinear
    ring_first_idx = np.unique(r_ring, return_index=True)[1]
    ring_last_idx = np.concatenate([ring_first_idx[1:] - 1, [nrun - 1]])
    multi = ring_last_idx != ring_first_idx
    fi, la = ring_first_idx[multi], ring_last_idx[multi]
    a_first = np.arctan2(ry[fi], rx[fi])
    a_last = np.arctan2(ry[la], rx[la])
    merge = np.abs(_wrap(a_first - a_last)) <= tol
    fi, la = fi[merge], la[merge]
    rx[fi] += rx[la]
    ry[fi] += ry[la]
    r_start[fi] = r_start[la]
    alive[la] = False
    r_len = np.hypot(rx, ry)
    r_len[~alive] = 0.0
    n_wrap_merged = int(merge.sum())

    mid = 0.5 * (coords[r_start] + coords[r_end])
    with np.errstate(invalid="ignore", divide="ignore"):
        nx = np.where(r_len > 0, ry / r_len, 0.0)
        ny = np.where(r_len > 0, -rx / r_len, 0.0)
    heading_run = np.degrees(np.arctan2(nx, ny)) % 360.0

    # ---- party-wall test on candidate runs ----------------------------------------------------------------------------
    cand = np.nonzero(alive & (r_len >= MIN_EDGE_M))[0]
    shared = np.zeros(nrun, dtype=bool)
    probe = mid[cand] + np.column_stack([nx[cand], ny[cand]]) * PROBE_OFFSET_M
    own = r_ring[cand]
    for s in range(0, len(cand), QUERY_CHUNK):
        sl = slice(s, s + QUERY_CHUNK)
        pts = shapely.points(probe[sl, 0], probe[sl, 1])
        q, t = tree.query(pts, predicate="dwithin", distance=NEAR_M)
        hit = t != own[sl][q]
        shared[cand[sl][q[hit]]] = True
    free = alive & (r_len >= MIN_EDGE_M) & ~shared

    # ---- scoring ---------------------------------------------------------------------------------------------------------
    vx = cx[r_ring] - lot_x[r_ring]
    vy = cy[r_ring] - lot_y[r_ring]
    vd = np.hypot(vx, vy)
    lot_ok = np.isfinite(vd) & (vd >= LOT_MIN_DIST_M)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos_t = np.where(lot_ok, (nx * vx + ny * vy) / np.where(vd > 0, vd, 1.0), 0.0)
    score = r_len * (1.0 + LOT_BIAS * np.maximum(cos_t, 0.0))

    heading = np.full(n, np.nan, dtype=np.float64)
    method = np.full(n, S.HEADING_LONGEST_EDGE, dtype=np.int8)

    def _pick(mask: np.ndarray, key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Per ring, run index maximising ``key`` among ``mask``."""
        idx = np.nonzero(mask)[0]
        order = np.lexsort((-key[idx], r_ring[idx]))
        idx = idx[order]
        rings_sorted = r_ring[idx]
        firsts = np.ones(len(idx), dtype=bool)
        firsts[1:] = rings_sorted[1:] != rings_sorted[:-1]
        return rings_sorted[firsts], idx[firsts]

    if free.any():
        rid, run = _pick(free, score)
        heading[rid] = heading_run[run]
        method[rid] = np.where(lot_ok[run], S.HEADING_FREE_EDGE_LOT, S.HEADING_FREE_EDGE)
    remaining = ~np.isfinite(heading)
    if remaining.any():
        m2 = alive & remaining[r_ring]
        if m2.any():
            rid, run = _pick(m2, r_len)
            heading[rid] = heading_run[run]
            method[rid] = S.HEADING_LONGEST_EDGE
    still = ~np.isfinite(heading)
    if still.any():      # degenerate ring with no usable run: use minimum rotated rectangle long side
        for i in np.nonzero(still)[0]:
            mrr = shapely.minimum_rotated_rectangle(polys[i])
            c = shapely.get_coordinates(mrr)
            if len(c) >= 3:
                d = c[1:] - c[:-1]
                k = int(np.argmax(np.hypot(d[:, 0], d[:, 1])))
                heading[i] = np.degrees(np.arctan2(d[k, 1], -d[k, 0])) % 360.0
            else:
                heading[i] = 0.0
            method[i] = S.HEADING_LONGEST_EDGE

    stats = {
        "edges": int(len(e_ring)), "runs": int(alive.sum()), "wraparound_merged": n_wrap_merged,
        "candidate_runs": int(len(cand)), "party_wall_runs": int(shared[cand].sum()),
        "buildings_free_edge_lot": int((method == S.HEADING_FREE_EDGE_LOT).sum()),
        "buildings_free_edge": int((method == S.HEADING_FREE_EDGE).sum()),
        "buildings_longest_edge": int((method == S.HEADING_LONGEST_EDGE).sum()),
    }
    log.info("facade heading: %s", stats)
    return heading.astype(np.float32), method, stats
