"""Footprint edge geometry: merged facade runs, party walls, street-facing classification.

A kit piece may only be placed where the real facade is.  Three geometric facts drive that:

1. **Runs.** A digitised footprint splits one physical facade into several nearly collinear segments; consecutive
   edges whose direction differs by less than :data:`ANGLE_TOL_DEG` are merged into one run (including across the
   ring's start vertex).  Same construction as ``buildings.facade_heading``, but the per-run result is kept.
2. **Party walls.** A run is a party wall when a probe point :data:`PROBE_OFFSET_M` outside its midpoint lies within
   :data:`NEAR_M` of another footprint.  Party walls carry no window, no stoop, no storefront and no fire escape —
   in NYC they are literally shared masonry.
3. **Street-facing.** With ``roads/segments.parquet`` present, a run is street-facing when its outward probe point is
   within :data:`STREET_NEAR_M` of a road centreline of a street-like ``rw_type``, and the nearest such segment id is
   recorded as ``street_segment_id``.  Without it, a run is street-facing when it is free and its outward normal is
   within :data:`HEADING_TOL_DEG` of the building's real ``primary_facade_heading``.

Outputs one row per run, plus a per-building summary (free run count, primary run, corner flag, street frontage).
"""
from __future__ import annotations

import logging

import numpy as np
import shapely

log = logging.getLogger("nycsim.facade.edges")

ANGLE_TOL_DEG = 8.0
MIN_RUN_M = 1.2            # a run shorter than this cannot carry a kit piece
PROBE_OFFSET_M = 0.35      # outward probe distance for the party-wall test
NEAR_M = 0.5               # neighbour distance that makes a run a party wall
STREET_NEAR_M = 20.0       # centreline distance that makes a run street-facing (half a 100 ft ROW + a front yard)
HEADING_TOL_DEG = 55.0     # tolerance around primary_facade_heading when no road geometry exists
CORNER_MIN_M = 4.0         # a corner needs two free runs at least this long
CORNER_ANGLE_LO, CORNER_ANGLE_HI = 60.0, 120.0
QUERY_CHUNK = 400_000

# roads/segments.parquet rw_type values that are real streets a facade can face
STREET_RW_TYPES = (1, 3, 5, 10)


class EdgeRuns:
    """Merged facade runs for a batch of footprints, aligned by ``bidx`` (index into the input geometry array)."""

    __slots__ = ("bidx", "x0", "y0", "x1", "y1", "length", "nx", "ny", "heading", "is_party", "is_street",
                 "street_segment_id", "n_buildings", "stats")

    def __init__(self, **kw) -> None:
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __len__(self) -> int:
        return len(self.bidx)


def _wrap(a: np.ndarray) -> np.ndarray:
    return (a + np.pi) % (2 * np.pi) - np.pi


def merge_runs(geoms: np.ndarray) -> tuple[np.ndarray, ...]:
    """Merge collinear consecutive exterior-ring edges into straight runs.

    Returns ``(bidx, x0, y0, x1, y1, length, nx, ny)`` where ``(nx, ny)`` is the outward unit normal of the run
    (footprints are oriented counter-clockwise, so the right-hand normal points out).
    """
    polys = shapely.orient_polygons(np.asarray(geoms))
    rings = shapely.get_exterior_ring(polys)
    coords, ridx = shapely.get_coordinates(rings, return_index=True)
    if len(coords) == 0:
        z = np.zeros(0)
        return (np.zeros(0, dtype=np.int64), z, z, z, z, z, z, z)
    same = ridx[1:] == ridx[:-1]
    e_ring = ridx[:-1][same]
    p0 = np.nonzero(same)[0]
    ex = (coords[1:, 0] - coords[:-1, 0])[same]
    ey = (coords[1:, 1] - coords[:-1, 1])[same]
    L = np.hypot(ex, ey)
    nz = L > 1e-9
    e_ring, p0, ex, ey = e_ring[nz], p0[nz], ex[nz], ey[nz]
    if len(e_ring) == 0:
        z = np.zeros(0)
        return (np.zeros(0, dtype=np.int64), z, z, z, z, z, z, z)
    ang = np.arctan2(ey, ex)
    tol = np.deg2rad(ANGLE_TOL_DEG)

    brk = (e_ring[1:] != e_ring[:-1]) | (np.abs(_wrap(ang[1:] - ang[:-1])) > tol)
    first = np.concatenate([[0], np.nonzero(brk)[0] + 1])
    last = np.concatenate([first[1:] - 1, [len(e_ring) - 1]])
    nrun = len(first)
    run_of_edge = np.repeat(np.arange(nrun), last - first + 1)
    rx = np.bincount(run_of_edge, ex, nrun)
    ry = np.bincount(run_of_edge, ey, nrun)
    r_ring = e_ring[first]
    r_start = p0[first]
    r_end = p0[last] + 1
    alive = np.ones(nrun, dtype=bool)

    # wrap-around: merge a ring's last run into its first when collinear
    ring_first_idx = np.unique(r_ring, return_index=True)[1]
    ring_last_idx = np.concatenate([ring_first_idx[1:] - 1, [nrun - 1]])
    multi = ring_last_idx != ring_first_idx
    fi, la = ring_first_idx[multi], ring_last_idx[multi]
    if len(fi):
        merge = np.abs(_wrap(np.arctan2(ry[fi], rx[fi]) - np.arctan2(ry[la], rx[la]))) <= tol
        fi, la = fi[merge], la[merge]
        rx[fi] += rx[la]
        ry[fi] += ry[la]
        r_start[fi] = r_start[la]
        alive[la] = False

    r_len = np.hypot(rx, ry)
    keep = alive & (r_len > 1e-6)
    r_ring, r_start, r_end, rx, ry, r_len = r_ring[keep], r_start[keep], r_end[keep], rx[keep], ry[keep], r_len[keep]
    x0, y0 = coords[r_start, 0], coords[r_start, 1]
    x1, y1 = coords[r_end, 0], coords[r_end, 1]
    nx = ry / r_len
    ny = -rx / r_len
    return r_ring.astype(np.int64), x0, y0, x1, y1, r_len, nx, ny


def compute_runs(geoms: np.ndarray, headings: np.ndarray, tree: shapely.STRtree, tree_index: np.ndarray,
                 road_tree: shapely.STRtree | None = None, road_ids: np.ndarray | None = None) -> EdgeRuns:
    """Merged runs with party-wall and street-facing flags.

    ``tree`` indexes *all* footprints in the working window (including neighbours outside the emitted set);
    ``tree_index[i]`` is the index into ``geoms`` of tree item ``i``, or −1 when the item is a neighbour only.
    """
    bidx, x0, y0, x1, y1, length, nx, ny = merge_runs(geoms)
    n = len(bidx)
    heading = np.degrees(np.arctan2(nx, ny)) % 360.0          # compass bearing of the outward normal
    is_party = np.zeros(n, dtype=bool)
    is_street = np.zeros(n, dtype=bool)
    seg_id = np.full(n, -1, dtype=np.int64)

    cand = np.nonzero(length >= MIN_RUN_M)[0]
    mx = 0.5 * (x0 + x1)
    my = 0.5 * (y0 + y1)
    if len(cand):
        px = mx[cand] + nx[cand] * PROBE_OFFSET_M
        py = my[cand] + ny[cand] * PROBE_OFFSET_M
        own = bidx[cand]
        for s in range(0, len(cand), QUERY_CHUNK):
            sl = slice(s, s + QUERY_CHUNK)
            pts = shapely.points(px[sl], py[sl])
            q, t = tree.query(pts, predicate="dwithin", distance=NEAR_M)
            hit = tree_index[t] != own[sl][q]
            if hit.any():
                is_party[cand[sl][q[hit]]] = True

        free = cand[~is_party[cand]]
        if road_tree is not None and road_ids is not None and len(free):
            fx = mx[free] + nx[free] * PROBE_OFFSET_M
            fy = my[free] + ny[free] * PROBE_OFFSET_M
            pts = shapely.points(fx, fy)
            nearest = road_tree.query_nearest(pts, max_distance=STREET_NEAR_M, return_distance=False,
                                              all_matches=False, exclusive=False)
            # query_nearest with all_matches=False returns a (2, k) array of (input index, tree index)
            if nearest.size:
                ii, tt = nearest[0], nearest[1]
                is_street[free[ii]] = True
                seg_id[free[ii]] = road_ids[tt]
        elif len(free):
            d = np.abs(_wrap(np.deg2rad(heading[free] - headings[bidx[free]])))
            is_street[free[d <= np.deg2rad(HEADING_TOL_DEG)]] = True

    stats = {
        "runs": int(n),
        "runs_usable": int(len(cand)),
        "runs_party_wall": int(is_party.sum()),
        "runs_street_facing": int(is_street.sum()),
        "runs_road_matched": int((seg_id >= 0).sum()),
    }
    return EdgeRuns(bidx=bidx, x0=x0, y0=y0, x1=x1, y1=y1, length=length, nx=nx, ny=ny, heading=heading,
                    is_party=is_party, is_street=is_street, street_segment_id=seg_id, n_buildings=len(geoms),
                    stats=stats)


def building_summary(runs: EdgeRuns, n_buildings: int) -> dict[str, np.ndarray]:
    """Per-building geometric attributes derived from the runs.

    ``attached``            number of party-wall runs (0 = free-standing);
    ``n_free_runs``         free runs at least ``MIN_RUN_M`` long;
    ``free_perimeter_m``    total length of free runs;
    ``primary_run_len_m``   length of the chosen street run (longest street-facing free run, else longest free run);
    ``primary_run``         index into ``runs`` of that run, −1 when the building has no free run;
    ``is_corner``           two free runs >= 4 m whose normals differ by 60-120 deg (a real corner lot);
    ``street_frontage_m``   total length of street-facing runs;
    ``street_segment_id``   segment id of the primary run (−1 when no road geometry matched).
    """
    usable = runs.length >= MIN_RUN_M
    free = usable & ~runs.is_party
    b = runs.bidx
    attached = np.bincount(b[usable & runs.is_party], minlength=n_buildings).astype(np.int16)
    n_free = np.bincount(b[free], minlength=n_buildings).astype(np.int16)
    free_per = np.bincount(b[free], runs.length[free], minlength=n_buildings).astype(np.float32)
    street_front = np.bincount(b[runs.is_street], runs.length[runs.is_street], minlength=n_buildings).astype(np.float32)

    # primary run: longest street-facing free run, else longest free run
    score = np.where(free, runs.length, -1.0) + np.where(runs.is_street, 1e6, 0.0)
    primary = np.full(n_buildings, -1, dtype=np.int64)
    if len(b):
        order = np.lexsort((-score, b))
        bs = b[order]
        firsts = np.ones(len(order), dtype=bool)
        firsts[1:] = bs[1:] != bs[:-1]
        idx = order[firsts]
        ok = score[idx] > 0
        primary[bs[firsts][ok]] = idx[ok]
    primary_len = np.where(primary >= 0, runs.length[np.maximum(primary, 0)], 0.0).astype(np.float32)
    primary_seg = np.where(primary >= 0, runs.street_segment_id[np.maximum(primary, 0)], -1).astype(np.int64)

    # corner: two *street-facing* free runs >= CORNER_MIN_M whose outward normals differ by 60..120 deg and, when
    # road geometry is available, whose nearest centrelines are two different streets — the real definition of a
    # corner lot, and the reason a corner bodega exists.
    is_corner = np.zeros(n_buildings, dtype=bool)
    big = np.nonzero(free & runs.is_street & (runs.length >= CORNER_MIN_M))[0]
    if len(big):
        bb = b[big]
        order = np.argsort(bb, kind="stable")
        big, bb = big[order], bb[order]
        starts = np.flatnonzero(np.concatenate([[True], bb[1:] != bb[:-1]]))
        ends = np.append(starts[1:], len(bb))
        have_segments = bool((runs.street_segment_id >= 0).any())
        for s, e in zip(starts, ends):
            if e - s < 2:
                continue
            h = runs.heading[big[s:e]]
            d = np.abs((h[:, None] - h[None, :] + 180.0) % 360.0 - 180.0)
            ok = (d >= CORNER_ANGLE_LO) & (d <= CORNER_ANGLE_HI)
            if have_segments:
                sid = runs.street_segment_id[big[s:e]]
                ok &= sid[:, None] != sid[None, :]
            if np.any(ok):
                is_corner[bb[s]] = True
    return {
        "attached": attached, "n_free_runs": n_free, "free_perimeter_m": free_per,
        "primary_run_len_m": primary_len, "primary_run": primary, "is_corner": is_corner,
        "street_frontage_m": street_front, "street_segment_id": primary_seg,
    }
