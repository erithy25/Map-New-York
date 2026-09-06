"""Little Island (Pier 55) — Hudson River Park at West 13th Street (no BIN; outline from OSM).
Heatherwick Studio with MNLA and Arup, 2021.

Alignment source
----------------
Little Island is a pier, not a building, so it has no OTI footprint. The outline used is OSM way **833335529,
name "Little Island"** (leisure=park, 9,556 m2) from ``data/processed/osm/landuse_leisure.parquet``.

Dimensions used (source in brackets)
------------------------------------
* Area [Hudson River Park Trust]: **2.4 acres = 9,700 m2**; the OSM outline gives 9,556 m2, a 1.5 % agreement.
* Structure [Heatherwick Studio; Arup]: **132 precast concrete "tulip" pots** on **267 piles**; each pot is a
  hollow, tapering shaft that flares to a hexagonal or pentagonal head; head sizes vary from 4.6 to 13.7 m across.
  The pots stand in the river and carry the park deck between them.
* Levels [Heatherwick; MNLA]: the deck undulates from **15 ft = 4.6 m** above mean high water at the two entry
  bridges to **62 ft = 18.9 m** at the south-west high point, with two other hills at 12.0 m and 14.0 m; the
  amphitheatre (the Amph) seats 687 in the south-east bowl.
* Bridges [Heatherwick]: two steel access bridges from the Hudson River Park esplanade, 4.6 m above the water.

Fidelity: the deck follows the real OSM outline; **all 132 tulip pots** are modelled as tapering flared shafts with
their heads meeting the deck, the deck's four levels (4.6 / 12.0 / 14.0 / 18.9 m) are modelled as a lofted surface,
and the two access bridges and the amphitheatre bowl are modelled as geometry. Inferred (stated): the pot positions
are laid out on a hexagonal grid clipped to the outline (their surveyed positions are not published), the head sizes
are distributed across the published 4.6-13.7 m range by distance from the deck's high point, and the hill positions
are read from plan photographs. NOT modelled: the planting (114 trees, 66,000 bulbs), the 267 piles below the water
line, the railings' detail and the Amph's seating steps.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
import shapely  # noqa: E402
import shapely.ops  # noqa: E402
from shapely import wkb as _wkb  # noqa: E402
from shapely.geometry import MultiPolygon, Point, Polygon  # noqa: E402

ID = "c_little_island"
OSM_WAY = 833335529
POTS = 132
PILES = 267
DECK_LOW, DECK_HIGH = 4.6, 18.9
HEAD_MIN, HEAD_MAX = 4.6, 13.7
AREA_PUBLISHED = 9700.0


def load_outline() -> Polygon:
    import pyarrow.parquet as pq
    path = cc.REPO / "data" / "processed" / "osm" / "landuse_leisure.parquet"
    tbl = pq.read_table(path, columns=["osm_id", "name", "geometry", "area_m2"],
                        filters=[("osm_id", "=", OSM_WAY)])
    rows = tbl.to_pylist()
    if not rows:
        raise RuntimeError(f"OSM way {OSM_WAY} ('Little Island') not found in {path}")
    geom = _wkb.loads(rows[0]["geometry"])
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    return C._orient(geom.buffer(0), 1.0)


def build():
    C.reset()
    cc.materials(["concrete", "concrete_dark", "grass", "steel_dark", "aluminium", "pavement", "water_dark",
                  "wood_dark", "granite_grey"])
    outline = load_outline()
    c = outline.centroid
    frame = cc.frame_at(c.x, c.y, 0.0, cc.GRID_ANGLE)
    P = frame.local_polygon(outline)
    x0, y0, x1, y1 = P.bounds
    objs: list = []

    # the deck's height field: three hills plus the two low entry corners
    hills = [((x0 + (x1 - x0) * 0.22), (y0 + (y1 - y0) * 0.30), DECK_HIGH, 34.0),
             ((x0 + (x1 - x0) * 0.74), (y0 + (y1 - y0) * 0.72), 14.0, 30.0),
             ((x0 + (x1 - x0) * 0.66), (y0 + (y1 - y0) * 0.24), 12.0, 26.0)]

    def deck_z(px: float, py: float) -> float:
        z = DECK_LOW
        for hx, hy, hz, hr in hills:
            d = math.hypot(px - hx, py - hy)
            if d < hr:
                z = max(z, DECK_LOW + (hz - DECK_LOW) * math.cos(math.pi / 2 * d / hr) ** 2)
        return z

    # ---- the 132 tulip pots on a hexagonal grid clipped to the outline -------------------------------------------
    step = math.sqrt(outline.area / POTS) * 1.02
    candidates = []
    j = 0
    y = y0 + step * 0.4
    while y < y1:
        x = x0 + step * 0.4 + (step / 2 if j % 2 else 0.0)
        while x < x1:
            p = Point(x, y)
            if P.contains(p):
                candidates.append((x, y))
            x += step
        y += step * math.sqrt(3) / 2
        j += 1
    cx_hi, cy_hi = hills[0][0], hills[0][1]
    candidates.sort(key=lambda q: math.hypot(q[0] - cx_hi, q[1] - cy_hi))
    pots = candidates[:POTS]
    b = C.MeshBuilder()
    for k, (px, py) in enumerate(pots):
        z = deck_z(px, py)
        f = 1.0 - min(1.0, math.hypot(px - cx_hi, py - cy_hi) / max(1.0, math.hypot(x1 - x0, y1 - y0) / 2))
        head = HEAD_MIN + (HEAD_MAX - HEAD_MIN) * f
        sides = 6 if k % 3 else 5
        b.lathe([(head * 0.16, -3.0), (head * 0.16, z * 0.35), (head * 0.30, z * 0.72),
                 (head / 2, z - 1.9), (head / 2, z - 1.65)], sides, C.M.concrete,
                origin=(px, py, 0.0), smooth=False, phase_deg=(k * 37) % 60)
    objs.append(C.tag(b.build(f"{ID}_pots"), "pots"))

    # ---- the deck surface: a Delaunay mesh over the real outline, with z from the height field ----------------
    from scipy.spatial import Delaunay  # noqa: E402  (already a dependency of common.MeshBuilder.hull)
    b = C.MeshBuilder()
    ring = C.ring_coords(P)
    pts: list[tuple[float, float]] = []
    for k in range(len(ring)):                      # densify the outline so the boundary triangles stay small
        a0 = np.array(ring[k]); a1 = np.array(ring[(k + 1) % len(ring)])
        L = float(np.linalg.norm(a1 - a0))
        n = max(1, int(L // 5.0))
        for i in range(n):
            q = a0 + (a1 - a0) * (i / n)
            pts.append((float(q[0]), float(q[1])))
    step_g = 6.0
    yy = y0
    while yy <= y1:
        xx = x0
        while xx <= x1:
            if P.contains(Point(xx, yy).buffer(1.5)):
                pts.append((xx, yy))
            xx += step_g
        yy += step_g
    arr = np.asarray(pts, dtype=np.float64)
    tri = Delaunay(arr)
    for ia, ib, ic in tri.simplices:
        a = arr[ia]; bb = arr[ib]; c2 = arr[ic]
        cen = ((a[0] + bb[0] + c2[0]) / 3.0, (a[1] + bb[1] + c2[1]) / 3.0)
        if not P.contains(Point(cen)):
            continue
        b.tri((a[0], a[1], deck_z(a[0], a[1])), (bb[0], bb[1], deck_z(bb[0], bb[1])),
              (c2[0], c2[1], deck_z(c2[0], c2[1])), C.M.grass)
    for p0, p1, L, t, n in C.edges_of(ring):                       # the deck edge fascia and railing
        za = deck_z(p0[0], p0[1])
        zb = deck_z(p1[0], p1[1])
        b.quad((p0[0], p0[1], za - 1.6), (p1[0], p1[1], zb - 1.6), (p1[0], p1[1], zb), (p0[0], p0[1], za),
               C.M.concrete_dark)
        b.quad((p0[0], p0[1], za + 1.05), (p1[0], p1[1], zb + 1.05), (p1[0], p1[1], zb + 1.15),
               (p0[0], p0[1], za + 1.15), C.M.aluminium)
    objs.append(C.tag(b.build(f"{ID}_deck"), "base"))

    # ---- the two access bridges and the amphitheatre bowl -------------------------------------------------------
    b = C.MeshBuilder()
    for sgn in (-1.0, 1.0):
        ay = (y0 + y1) / 2 + sgn * (y1 - y0) * 0.28
        b.box((x0 - 14.0, ay, DECK_LOW - 0.4), (30.0, 5.2, 0.8), C.M.wood_dark)
        for k in range(4):
            b.box((x0 - 26.0 + 8.0 * k, ay, (DECK_LOW - 0.8) / 2), (0.6, 4.6, DECK_LOW - 0.8), C.M.steel_dark)
    ax, ay = (x0 + (x1 - x0) * 0.80), (y0 + (y1 - y0) * 0.30)
    for k in range(9):                                              # the Amph's stepped bowl
        r = 22.0 - 2.2 * k
        z = deck_z(ax, ay) - 0.55 * k
        b.lathe([(r, 0.0), (r, 0.55)], 28, C.M.concrete_dark, origin=(ax, ay, z), cap=False)
    objs.append(C.tag(b.build(f"{ID}_bridges_and_amph"), "detail"))
    return objs, frame, P, len(pots)


def main():
    objs, frame, P, npots = build()
    entry = cc.finish(objs, ID, frame, real_footprint=P, iou_min=0.90,
                      plan_polygon=P,
                      plan_polygon_note=("plan IoU of the model deck outline against OSM way 833335529; the deck is built "
                                         "directly from that polygon and undulates 4.6-18.9 m above the river, so no single "
                                         "horizontal section can measure it"),
                      footprint_source="OSM way 833335529 'Little Island' (leisure=park) via data/processed/osm/landuse_leisure.parquet",
                      fidelity_statement=(
                          f"Exact: the deck follows the real OSM outline ({P.area:.0f} m2 against the published "
                          f"2.4 acres = 9,700 m2, 1.5 % agreement); all {npots} tulip pots are modelled as tapering "
                          f"flared shafts with pentagonal and hexagonal heads spanning the published 4.6-13.7 m "
                          f"range; the deck undulates between the published 15 ft = 4.6 m entry level and the "
                          f"62 ft = 18.9 m high point with two further hills; the two access bridges and the Amph "
                          f"bowl are modelled. Inferred (stated): the pots are laid out on a hexagonal grid clipped "
                          f"to the outline (their surveyed positions are not published), head sizes are "
                          f"distributed by distance from the high point, and the hill positions are read from plan "
                          f"photographs. Not modelled: the 114 trees and 66,000 bulbs, the 267 piles below water, "
                          f"the railing detail and the Amph's seating steps."),
                      dimensions={"deck_low_m": DECK_LOW, "deck_high_m": DECK_HIGH, "pots": npots,
                                  "pots_published": POTS, "piles_published": PILES,
                                  "pot_head_range_m": [HEAD_MIN, HEAD_MAX], "area_m2": round(P.area, 1),
                                  "area_published_m2": AREA_PUBLISHED, "osm_way": OSM_WAY, "amph_seats": 687})
    cc.render(ID, [
        {"view": "hudson_river_park", "azimuth_deg": 80, "elevation_deg": "street", "distance": 175, "fov_deg": 55, "look_up_deg": 10},
        {"view": "aerial", "azimuth_deg": 100, "elevation_deg": 34},
    ])
    return entry


if __name__ == "__main__":
    main()
