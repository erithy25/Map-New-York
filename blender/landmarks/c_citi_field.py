"""Citi Field — 41 Seaver Way, Flushing, Queens (BIN 4536844). Populous (HOK Sport), 2009.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (34,907 m2), 266.4 x 312.6 m.
* Height [Populous; New York Mets]: the top of the upper-deck roof is ~128 ft = **39.0 m** (the OTI LiDAR average,
  24.3 m, is the seating plane).
* Field [New York Mets official dimensions, post-2015 walls]: left field **335 ft = 102.1 m**, left-centre
  379 ft = 115.5 m, centre field **408 ft = 124.4 m**, right-centre 383 ft = 116.7 m, right field
  **330 ft = 100.6 m**; the outfield wall is 8 ft = 2.44 m high. The infield is a 90 ft = 27.43 m square with the
  mound 60 ft 6 in = 18.44 m from home plate.
* Jackie Robinson Rotunda [Populous; Mets]: the main entrance is a 60 ft = **18.3 m** high arcade of eight
  round-arched openings in Ebbets Field-style red brick with limestone trim and a granite base, with a steel
  entrance bridge above; the rotunda drum behind it is 42.0 m across.
* Exterior [Populous]: red brick piers with cast-stone trim and exposed steel bridge trusses over the entrances.
* Capacity 41,922 [Mets].

Fidelity: real footprint; the published field dimensions laid out exactly, a three-deck bowl to the 39.0 m roof,
the eight-arch 18.3 m Jackie Robinson Rotunda and the brick-and-cast-stone exterior are modelled as geometry.
Inferred (stated): the orientation of home plate within the footprint (set so the published distances fit the
polygon), the deck rakes, and the exterior storey heights. NOT modelled: individual seats, the scoreboard graphics,
the Home Run Apple, the bullpens and the interiors.
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
from c_yankee_stadium import _resample, field_polygon  # noqa: E402  (shared bowl helpers)

ID = "c_citi_field"
BIN = 4536844
ROOF_TOP = 39.0
ROTUNDA_H = 18.3
ROTUNDA_D = 42.0
ROTUNDA_ARCHES = 8
WALL_H = 2.44
CAPACITY = 41922
import c_yankee_stadium as ys  # noqa: E402


def build():
    C.reset()
    cc.materials(["brick_red", "limestone", "granite_grey", "concrete", "concrete_dark", "grass", "asphalt",
                  "roof_dark", "steel_dark", "glass_dark", "pavement"])
    ys.LF, ys.LC, ys.CF, ys.RC, ys.RF = 102.1, 115.5, 124.4, 116.7, 100.6
    g = cc.Group(ID)
    P = g.poly(BIN)
    x0, y0, x1, y1 = P.bounds
    objs: list = []
    axis = 35.0
    a = math.radians(axis)
    hx = (x0 + x1) / 2 - ys.CF * 0.50 * math.cos(a)
    hy = (y0 + y1) / 2 - ys.CF * 0.50 * math.sin(a)
    field = field_polygon(hx, hy, axis)

    objs.append(C.plinth(f"{ID}_base", P, 0.0, 8.0, C.M.concrete, material_top=C.M.pavement))
    rings = [(0.0, C.offset_polygon(field, 6.0)), (8.0, C.offset_polygon(field, 24.0)),
             (17.0, C.offset_polygon(field, 38.0)), (28.0, C.offset_polygon(field, 50.0)),
             (ROOF_TOP - 3.0, C.offset_polygon(field, 58.0))]
    b = C.MeshBuilder()
    for i in range(len(rings) - 1):
        z0, pa = rings[i]
        z1, pb = rings[i + 1]
        ra = C.ring_coords(C._clean_polygon(pa))
        rb = C.ring_coords(C._clean_polygon(pb))
        nseg = 72
        r0 = [_resample(ra, k / nseg) for k in range(nseg)]
        r1 = [_resample(rb, k / nseg) for k in range(nseg)]
        b.loft([[(x, y, z0) for x, y in r0], [(x, y, z1) for x, y in r1]], C.M.concrete_dark,
               cap_top=False, cap_bottom=False)
        if i < len(rings) - 2:
            b.loft([[(x, y, z1) for x, y in r1], [(x, y, z1 + 3.2) for x, y in r1]], C.M.concrete,
                   cap_top=False, cap_bottom=False)
    # the upper-deck roof canopy
    rr = C.ring_coords(C._clean_polygon(C.offset_polygon(field, 58.0)))
    nseg = 72
    rt = [_resample(rr, k / nseg) for k in range(nseg)]
    b.loft([[(x, y, ROOF_TOP - 3.0) for x, y in rt], [(x, y, ROOF_TOP) for x, y in C.offset_ring(rt, -9.0)]],
           C.M.steel_dark, cap_top=False, cap_bottom=False)
    objs.append(C.tag(b.build(f"{ID}_bowl"), "mass"))

    b = C.MeshBuilder()
    b.prism(C.ring_coords(field), 0.0, 0.12, C.M.grass)
    warn = C.ring_coords(field)
    b.loft([[(x, y, 0.12) for x, y in warn], [(x, y, 0.12) for x, y in C.offset_ring(warn, -3.7)]], C.M.asphalt,
           cap_top=False, cap_bottom=False)
    b.prism(warn, 0.12, 0.12 + WALL_H, C.M.concrete_dark, holes=[C.offset_ring(warn, -0.3)], cap_bottom=False)
    b.prism([(hx + 27.43 * math.cos(math.radians(axis - 45)) * k1 + 27.43 * math.cos(math.radians(axis + 45)) * k2,
              hy + 27.43 * math.sin(math.radians(axis - 45)) * k1 + 27.43 * math.sin(math.radians(axis + 45)) * k2)
             for k1, k2 in ((0, 0), (1, 0), (1, 1), (0, 1))], 0.12, 0.13, C.M.asphalt)
    b.lathe([(2.74, 0.0), (2.74, 0.25), (0.0, 0.25)], 20, C.M.asphalt,
            origin=(hx + 18.44 * math.cos(a), hy + 18.44 * math.sin(a), 0.12))
    objs.append(C.tag(b.build(f"{ID}_field"), "field"))

    # ---- the brick exterior and the Jackie Robinson Rotunda -------------------------------------------------------
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 6.0:
            continue
        narch = max(1, int(round(L / 7.6)))
        mod = L / narch
        for k in range(narch):
            q0 = p0 + t * (k * mod + 1.1)
            q1 = p0 + t * ((k + 1) * mod - 1.1)
            C.arched_opening(b, q0, q1, n, 1.2, 9.0, None, 1.2, C.M.brick_red, C.M.glass_dark)
            b.box_from_to(p0 + t * (k * mod - 0.8), p0 + t * (k * mod + 0.8), n, 1.2, 0.0, 20.0, C.M.brick_red)
        b.box_from_to(p0, p1, n, 1.0, 0.0, 1.2, C.M.granite_grey)
        b.box_from_to(p0, p1, n, 1.3, 20.0, 21.6, C.M.limestone)
    objs.append(b.build(f"{ID}_exterior"))
    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(coords, -90.0)          # the rotunda front (home-plate side)
    mid = (p0 + p1) / 2
    aw = ROTUNDA_D / ROTUNDA_ARCHES
    for k in range(ROTUNDA_ARCHES):
        u = -ROTUNDA_D / 2 + aw * (k + 0.5)
        q0 = mid + t * (u - aw / 2 + 0.6)
        q1 = mid + t * (u + aw / 2 - 0.6)
        C.arched_opening(b, q0, q1, n, 0.6, ROTUNDA_H - aw / 2 - 2.0, aw / 2 - 0.6, 2.6, C.M.brick_red,
                         C.M.glass_dark)
    b.box_from_to(mid - t * (ROTUNDA_D / 2 + 1.5), mid + t * (ROTUNDA_D / 2 + 1.5), n, 3.0, ROTUNDA_H - 2.0,
                  ROTUNDA_H, C.M.limestone)
    for k in range(5):                                       # the steel entrance bridge trusses
        u = -ROTUNDA_D / 2 + ROTUNDA_D * k / 4
        q = mid + t * u
        b.box((q[0] + n[0] * 4.0, q[1] + n[1] * 4.0, ROTUNDA_H + 3.0), (1.0, 8.0, 4.5), C.M.steel_dark,
              rot_deg=math.degrees(math.atan2(t[1], t[0])))
    objs.append(b.build(f"{ID}_rotunda"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the published field dimensions laid out to the metre "
                          "(LF 335 ft, LC 379 ft, CF 408 ft, RC 383 ft, RF 330 ft; 90 ft infield; 60 ft 6 in mound; "
                          "8 ft wall); a three-deck bowl to a 39.0 m roof canopy; the eight-arch, 60 ft = 18.3 m "
                          "Jackie Robinson Rotunda with its steel entrance bridge; the red-brick and cast-stone "
                          "exterior on a granite base. Inferred (stated): the orientation of home plate within the "
                          "footprint, the deck rakes and the exterior storey heights. Not modelled: individual "
                          "seats, scoreboard graphics, the Home Run Apple, bullpens, interiors."),
                      dimensions={"roof_top_m": ROOF_TOP, "field_lf_lc_cf_rc_rf_m": [102.1, 115.5, 124.4, 116.7, 100.6],
                                  "infield_square_m": 27.43, "mound_distance_m": 18.44, "outfield_wall_h_m": WALL_H,
                                  "rotunda_h_m": ROTUNDA_H, "rotunda_d_m": ROTUNDA_D,
                                  "rotunda_arches": ROTUNDA_ARCHES, "capacity": CAPACITY})
    cc.render(ID, [
        {"view": "rotunda", "azimuth_deg": 180, "elevation_deg": "street", "distance": 210, "fov_deg": 60, "look_up_deg": 12},
        {"view": "aerial", "azimuth_deg": 215, "elevation_deg": 34},
    ])
    return entry


if __name__ == "__main__":
    main()
