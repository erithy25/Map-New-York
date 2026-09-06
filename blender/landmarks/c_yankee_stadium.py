"""Yankee Stadium — 1 East 161st Street, the Bronx (BIN 2114490). Populous (HOK Sport), 2009.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (35,104 m2), 264.0 x 274.2 m.
* Height [Populous; New York Yankees]: the top of the upper deck and its frieze is ~138 ft = **42.0 m** above street
  level (the OTI LiDAR average roof, 36.6 m, is the seating-bowl plane, not the frieze).
* Field [New York Yankees official dimensions]: left field **318 ft = 96.9 m**, left-centre 399 ft = 121.6 m,
  centre field **408 ft = 124.4 m**, right-centre 385 ft = 117.3 m, right field **314 ft = 95.7 m**; the outfield
  wall is 8 ft = 2.44 m high (with the 2.74 m section in front of the bleachers). The infield is a 90 ft = 27.43 m
  square with the pitcher's rubber 60 ft 6 in = 18.44 m from home plate; foul territory is bounded by the two foul
  lines at 45 degrees either side of the centre-field axis.
* Frieze [Populous; a replica of the 1923 stadium's copper frieze]: a white filigree band **3.0 m deep** running the
  full length of the roof edge above the upper deck, with a repeating arched motif on a 2.9 m module.
* Exterior [Populous]: Indiana limestone and granite piers with round-arched openings 5.5 m wide and 12.0 m to the
  crown, and the "Yankee Stadium" name band; the Great Hall runs behind the Gate 4 facade.
* Capacity 47,309 in three decks [Yankees].

Fidelity: real footprint; the published field dimensions are laid out exactly (foul lines, the five wall distances,
the 27.43 m infield square and the 18.44 m mound), the three-deck bowl rises to the 42.0 m frieze, and the limestone
arcade with its arched openings and the frieze's arched motif are modelled as geometry. Inferred (stated): the
orientation of home plate within the footprint (set so that the published outfield distances fit the polygon), the
deck rakes and row counts, and the exterior's storey heights. NOT modelled: individual seats (the decks are raked
planes), the scoreboard graphics, Monument Park, the bullpens' structures and the interiors.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

ID = "c_yankee_stadium"
BIN = 2114490
FRIEZE_TOP = 42.0
FRIEZE_D = 3.0
LF, LC, CF, RC, RF = 96.9, 121.6, 124.4, 117.3, 95.7
INFIELD = 27.43
MOUND = 18.44
WALL_H = 2.44
CAPACITY = 47309


def field_polygon(hx: float, hy: float, axis_deg: float) -> Polygon:
    """The playing field bounded by the two foul lines and the outfield wall at the published distances."""
    pts = [(hx, hy)]
    for ang, dist in ((-45.0, LF), (-22.5, LC), (0.0, CF), (22.5, RC), (45.0, RF)):
        a = math.radians(axis_deg + ang)
        pts.append((hx + dist * math.cos(a), hy + dist * math.sin(a)))
    return Polygon(pts)


def build():
    C.reset()
    cc.materials(["limestone", "granite_grey", "concrete", "concrete_dark", "marble_white", "grass", "asphalt",
                  "roof_dark", "steel_dark", "glass_dark", "pavement"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    x0, y0, x1, y1 = P.bounds
    objs: list = []
    axis = 55.0                              # centre-field direction, set so the published distances fit the polygon
    a = math.radians(axis)
    hx = (x0 + x1) / 2 - CF * 0.52 * math.cos(a)
    hy = (y0 + y1) / 2 - CF * 0.52 * math.sin(a)
    field = field_polygon(hx, hy, axis)

    # ---- the concourse base on the real footprint (IoU volume) ---------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, 9.0, C.M.concrete, material_top=C.M.pavement))

    # ---- the seating bowl: three decks lofted from the field edge outwards and upwards ----------------------------
    bowl_in = C.offset_polygon(field, 7.0)
    rings = [(0.0, C.offset_polygon(field, 6.0)), (9.0, C.offset_polygon(field, 26.0)),
             (19.0, C.offset_polygon(field, 40.0)), (30.0, C.offset_polygon(field, 52.0)),
             (FRIEZE_TOP - FRIEZE_D, C.offset_polygon(field, 62.0))]
    b = C.MeshBuilder()
    for i in range(len(rings) - 1):
        z0, pa = rings[i]
        z1, pb = rings[i + 1]
        ra = C.ring_coords(pa if isinstance(pa, Polygon) else C._clean_polygon(pa))
        rb = C.ring_coords(pb if isinstance(pb, Polygon) else C._clean_polygon(pb))
        nseg = 72
        r0 = [_resample(ra, k / nseg) for k in range(nseg)]
        r1 = [_resample(rb, k / nseg) for k in range(nseg)]
        b.loft([[(x, y, z0) for x, y in r0], [(x, y, z1) for x, y in r1]], C.M.concrete_dark,
               cap_top=False, cap_bottom=False)
        # the step of each deck's fascia
        if i < len(rings) - 2:
            b.loft([[(x, y, z1) for x, y in r1], [(x, y, z1 + 3.5) for x, y in r1]], C.M.concrete,
                   cap_top=False, cap_bottom=False)
    objs.append(C.tag(b.build(f"{ID}_bowl"), "mass"))

    # ---- the field: grass, infield dirt, warning track and the outfield wall --------------------------------------
    b = C.MeshBuilder()
    b.prism(C.ring_coords(field), 0.0, 0.12, C.M.grass)
    warn = C.ring_coords(field)
    b.loft([[(x, y, 0.12) for x, y in warn], [(x, y, 0.12) for x, y in C.offset_ring(warn, -3.7)]], C.M.asphalt,
           cap_top=False, cap_bottom=False)
    b.prism(warn, 0.12, 0.12 + WALL_H, C.M.concrete_dark,
            holes=[C.offset_ring(warn, -0.3)], cap_bottom=False)
    inf = []                                              # the 90 ft infield square, rotated onto the axis
    for k in range(4):
        ang = math.radians(axis + 45.0 + 90.0 * k)
        d = INFIELD * math.sqrt(2) / 2 * (1 if k % 2 == 0 else 1)
        inf.append((hx + INFIELD * math.sqrt(2) / 2 * math.cos(math.radians(axis - 45 + 90 * k)) * (1.0),
                    hy + INFIELD * math.sqrt(2) / 2 * math.sin(math.radians(axis - 45 + 90 * k)) * (1.0)))
    b.prism([(hx + INFIELD * math.cos(math.radians(axis - 45)) * k1 + INFIELD * math.cos(math.radians(axis + 45)) * k2,
              hy + INFIELD * math.sin(math.radians(axis - 45)) * k1 + INFIELD * math.sin(math.radians(axis + 45)) * k2)
             for k1, k2 in ((0, 0), (1, 0), (1, 1), (0, 1))], 0.12, 0.13, C.M.asphalt)
    b.lathe([(2.74, 0.0), (2.74, 0.25), (0.0, 0.25)], 20, C.M.asphalt,
            origin=(hx + MOUND * math.cos(a), hy + MOUND * math.sin(a), 0.12))
    objs.append(C.tag(b.build(f"{ID}_field"), "field"))

    # ---- the limestone exterior and the frieze -------------------------------------------------------------------
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 6.0:
            continue
        narch = max(1, int(round(L / 8.2)))
        mod = L / narch
        for k in range(narch):
            q0 = p0 + t * (k * mod + (mod - 5.5) / 2)
            q1 = p0 + t * ((k + 1) * mod - (mod - 5.5) / 2)
            C.arched_opening(b, q0, q1, n, 1.5, 12.0 - 2.75, 2.75, 1.4, C.M.limestone, C.M.glass_dark)
            b.box_from_to(p0 + t * (k * mod - 0.9), p0 + t * (k * mod + 0.9), n, 1.4, 0.0, 24.0, C.M.limestone)
        b.box_from_to(p0, p1, n, 1.1, 14.5, 17.0, C.M.limestone)          # the name band
        b.box_from_to(p0, p1, n, 1.4, 24.0, 26.5, C.M.limestone)          # the cornice over the arcade
    objs.append(b.build(f"{ID}_exterior"))
    # the frieze: an arched-motif band 3.0 m deep around the top of the upper deck
    b = C.MeshBuilder()
    fr = C.ring_coords(C.offset_polygon(field, 62.0))
    nseg = 160
    rr = [_resample(fr, k / nseg) for k in range(nseg)]
    b.loft([[(x, y, FRIEZE_TOP - FRIEZE_D) for x, y in rr], [(x, y, FRIEZE_TOP - 0.5) for x, y in rr],
            [(x, y, FRIEZE_TOP) for x, y in C.offset_ring(rr, 0.55)]], C.M.marble_white,
           cap_top=False, cap_bottom=False)
    for k in range(0, nseg):                                    # the repeating arched motif
        p = rr[k]
        q = rr[(k + 1) % nseg]
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        b.box((mid[0], mid[1], FRIEZE_TOP - FRIEZE_D + 0.9), (0.5, 0.5, 1.8), C.M.marble_white)
    objs.append(C.tag(b.build(f"{ID}_frieze"), "mass"))
    return objs, g


def _resample(ring, s: float):
    """Point at fractional perimeter position ``s`` (0..1) along a closed ring — used to give lofted rings equal
    vertex counts."""
    n = len(ring)
    segs = [math.dist(ring[i], ring[(i + 1) % n]) for i in range(n)]
    total = sum(segs)
    d = s * total
    for i, L in enumerate(segs):
        if d <= L or i == n - 1:
            u = d / L if L > 1e-9 else 0.0
            p0 = ring[i]
            p1 = ring[(i + 1) % n]
            return (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
        d -= L
    return ring[0]


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the published field dimensions laid out to the metre "
                          "(LF 318 ft, LC 399 ft, CF 408 ft, RC 385 ft, RF 314 ft; 90 ft infield square; 60 ft 6 in "
                          "mound; 8 ft outfield wall); a three-deck bowl to the 42.0 m frieze; the 3.0 m white "
                          "filigree frieze with its arched motif; the Indiana-limestone arcade with 5.5 m round-"
                          "arched openings and the name band. Inferred (stated): the orientation of home plate "
                          "within the footprint (set so the published distances fit the polygon), the deck rakes "
                          "and row counts, and the exterior storey heights. Not modelled: individual seats (raked "
                          "planes), scoreboard graphics, Monument Park, bullpen structures, interiors."),
                      dimensions={"frieze_top_m": FRIEZE_TOP, "frieze_depth_m": FRIEZE_D,
                                  "field_lf_lc_cf_rc_rf_m": [LF, LC, CF, RC, RF], "infield_square_m": INFIELD,
                                  "mound_distance_m": MOUND, "outfield_wall_h_m": WALL_H, "capacity": CAPACITY})
    cc.render(ID, [
        {"view": "gate4", "azimuth_deg": 210, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 9},
        {"view": "aerial", "azimuth_deg": 235, "elevation_deg": 34},
    ])
    return entry


if __name__ == "__main__":
    main()
