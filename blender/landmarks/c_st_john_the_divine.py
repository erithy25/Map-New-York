"""Cathedral Church of Saint John the Divine — 1047 Amsterdam Avenue (BIN 1082706, LP-2585). Heins & LaFarge
1892-1911 (Romanesque-Byzantine choir and crossing); Cram & Ferguson 1916-41 (Gothic nave and west front);
still unfinished.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (8,794 m2), **181.1 m long east-west** and up to 81.8 m across the transepts —
  which matches the published overall length of 601 ft = 183.2 m to within 2 m. Amsterdam Avenue is west (local -x),
  so the west front faces -x and the apse and chapels are at +x.
* Heights [Cathedral of St. John the Divine; LP-2585]: the nave vault is 124 ft = 37.8 m internally and the nave
  ridge 177 ft = 54.0 m; the unfinished crossing tower stands at 232 ft = **70.7 m**, which is the height of the
  model. The west front's two towers stop at 45.0 m (unfinished; the north tower is roofed over).
* Nave [Cathedral]: 8 bays with clustered piers; the west rose window is 12.2 m in diameter (the largest in the
  United States, 10,000 pieces of glass); the five west portals are recessed 4.5 m under pointed arches with the
  central portal 8.5 m wide.
* Apse [Heins & LaFarge]: a semicircular ambulatory of seven radiating chapels, roofed at 24.0 m.
* Material [LP-2585]: Mohegan granite and Indiana limestone.

Fidelity: real footprint; the 70.7 m crossing tower, the 54.0 m nave ridge, the eight-bay nave with flying
buttresses, the five recessed west portals, the 12.2 m rose window, the unfinished 45.0 m west towers and the seven
apse chapels are modelled as geometry. Inferred (stated): the bay rhythm is derived by dividing the nave length by
the published 8 bays; the buttress profile and the tower's unfinished top are from photographs. NOT modelled: the
interior vaults, the stained glass (the rose is a single glazed disc), the carved tympana and statuary of the west
front, and the temporary roof over the crossing.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_st_john_the_divine"
BIN = 1082706
CROSSING_TOP = 70.7
NAVE_RIDGE = 54.0
AISLE_TOP = 26.0
WEST_TOWER = 45.0
ROSE_D = 12.2
NAVE_BAYS = 8


def build():
    C.reset()
    cc.materials(["granite_grey", "limestone", "limestone_dark", "slate", "glass_dark", "glass_clear", "roof_dark",
                  "copper_green", "bronze"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    x0, y0, x1, y1 = P.bounds
    cy = (y0 + y1) / 2
    objs: list = []

    objs += cc.base_and_wall(f"{ID}_base", P, AISLE_TOP, C.M.granite_grey, recess=1.2, material_top=C.M.slate)
    # the nave: a tall clerestory box down the middle, with a pitched slate roof to the ridge
    nave = C.rect_xy(x0 + 2.0, cy - 14.5, x0 + 96.0, cy + 14.5)
    objs.append(C.prism(f"{ID}_nave", nave, AISLE_TOP, NAVE_RIDGE - 10.0, C.M.limestone, material_top=C.M.slate,
                        role="mass"))
    b = C.MeshBuilder()
    b.loft([[(x, y, NAVE_RIDGE - 10.0) for x, y in C.ring_coords(nave)],
            [(x, y, NAVE_RIDGE) for x, y in C.offset_ring(C.ring_coords(nave), -12.0)]], C.M.slate,
           cap_top=True, cap_bottom=False, material_top=C.M.slate)
    # clerestory windows and flying buttresses on both nave flanks
    for sgn in (-1.0, 1.0):
        yy = cy + sgn * 14.5
        for k in range(NAVE_BAYS):
            xx = x0 + 6.0 + (90.0 / NAVE_BAYS) * (k + 0.5)
            p0 = np.array([xx - 3.0, yy]); p1 = np.array([xx + 3.0, yy])
            n = np.array([0.0, sgn])
            C.arched_opening(b, p0, p1, n, AISLE_TOP + 3.0, NAVE_RIDGE - 15.0, 3.0, 0.9, C.M.limestone,
                             C.M.glass_dark, pointed=True)
            for by, bz in ((yy + sgn * 9.0, AISLE_TOP), (yy + sgn * 16.0, AISLE_TOP - 6.0)):
                b.hull([(xx - 0.9, yy, AISLE_TOP + 2.0), (xx + 0.9, yy, AISLE_TOP + 2.0),
                        (xx - 0.9, yy, NAVE_RIDGE - 13.0), (xx + 0.9, yy, NAVE_RIDGE - 13.0),
                        (xx - 0.9, by, bz), (xx + 0.9, by, bz)], C.M.limestone)
                b.box((xx, by, bz + 6.0), (2.4, 2.4, 12.0), C.M.limestone)      # the buttress pier
                b.lathe([(1.4, 0.0), (0.0, 5.0)], 8, C.M.limestone, origin=(xx, by, bz + 12.0))
    # the crossing tower
    cross = C.rect_xy(x0 + 96.0, cy - 16.0, x0 + 128.0, cy + 16.0)
    objs.append(C.prism(f"{ID}_crossing", cross, AISLE_TOP, CROSSING_TOP - 3.0, C.M.limestone,
                        material_top=C.M.slate, role="mass"))
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(cross)):
        for k in range(2):
            a = p0 + t * (L * (k + 0.5) / 2 - 3.2)
            c = p0 + t * (L * (k + 0.5) / 2 + 3.2)
            C.arched_opening(b, a, c, n, CROSSING_TOP - 26.0, CROSSING_TOP - 9.0, 3.2, 0.9, C.M.limestone,
                             C.M.glass_dark, pointed=True)
    b.prism(C.ring_coords(C.offset_polygon(cross, 1.2)), CROSSING_TOP - 3.0, CROSSING_TOP, C.M.limestone,
            material_top=C.M.slate)                                          # the unfinished tower's capping course
    # the apse: seven radiating chapels on a semicircle at the east end
    acx = x0 + 150.0
    for k in range(7):
        a = math.pi * (-0.5 + (k + 0.5) / 7)
        q = (acx + 22.0 * math.cos(a), cy + 22.0 * math.sin(a))
        b.lathe([(4.6, 0.0), (4.6, 12.0), (4.0, 14.0), (0.0, 20.0)], 12, C.M.granite_grey, origin=(q[0], q[1], 6.0))
    b.lathe([(23.0, 0.0), (23.0, 22.0), (20.0, 24.0), (0.0, 34.0)], 28, C.M.granite_grey,
            origin=(acx, cy, AISLE_TOP - 12.0), smooth=False)
    # the west front: five recessed portals, the rose window and the two unfinished towers
    for du, w in ((-16.0, 4.2), (-8.6, 4.2), (0.0, 8.5), (8.6, 4.2), (16.0, 4.2)):
        p0 = np.array([x0 + 2.0, cy + du - w / 2]); p1 = np.array([x0 + 2.0, cy + du + w / 2])
        C.arched_opening(b, p1, p0, np.array([-1.0, 0.0]), 0.0, w * 0.9, w * 1.3, 4.5, C.M.limestone, C.M.bronze,
                         pointed=True)
    b.lathe([(ROSE_D / 2, 0.0), (ROSE_D / 2, 0.6), (ROSE_D / 2 - 1.2, 0.6), (ROSE_D / 2 - 1.2, 0.0)], 32,
            C.M.limestone, origin=(x0 + 1.6, cy, 30.0), phase_deg=0.0, cap=False, smooth=True)
    b.lathe([(0.0, 0.3), (ROSE_D / 2 - 1.2, 0.3)], 32, C.M.glass_clear, origin=(x0 + 1.6, cy, 30.0))
    for k in range(16):                                                       # the rose's radiating tracery
        a = 2 * math.pi * k / 16
        b.box((x0 + 1.5, cy + (ROSE_D / 4) * math.cos(a), 30.0 + (ROSE_D / 4) * math.sin(a)),
              (0.5, 0.35, ROSE_D / 2 - 1.2), C.M.limestone, rot_deg=0.0)
    for sgn in (-1.0, 1.0):
        tw = C.rect_xy(x0 + 2.0, cy + sgn * 22.0 - 10.0, x0 + 22.0, cy + sgn * 22.0 + 10.0)
        b.prism(C.ring_coords(tw), AISLE_TOP, WEST_TOWER, C.M.limestone, material_top=C.M.slate)
        for p0, p1, L, t, n in C.edges_of(C.ring_coords(tw)):
            a = p0 + t * (L / 2 - 2.2)
            c = p0 + t * (L / 2 + 2.2)
            C.arched_opening(b, a, c, n, WEST_TOWER - 16.0, WEST_TOWER - 4.0, 2.2, 0.8, C.M.limestone,
                             C.M.glass_dark, pointed=True)
    objs.append(b.build(f"{ID}_fabric"))
    return objs, g, P


def main():
    objs, g, P = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint (181.1 m long, within 2 m of the published 601 ft); the "
                          "unfinished crossing tower at 232 ft = 70.7 m; the nave ridge at 177 ft = 54.0 m over "
                          "eight bays with clerestory windows and two tiers of flying buttresses; the five recessed "
                          "west portals; the 12.2 m rose window with radiating tracery; the two unfinished west "
                          "towers at 45.0 m; the seven radiating apse chapels. Inferred (stated): the bay rhythm "
                          "(nave length / published 8 bays), the buttress profile and the tower's unfinished top "
                          "(from photographs). Not modelled: interior vaults, the stained glass (the rose is one "
                          "glazed disc), the carved tympana and statuary, the temporary crossing roof."),
                      dimensions={"crossing_tower_m": CROSSING_TOP, "nave_ridge_m": NAVE_RIDGE,
                                  "aisle_top_m": AISLE_TOP, "west_towers_m": WEST_TOWER, "rose_window_d_m": ROSE_D,
                                  "nave_bays": NAVE_BAYS,
                                  "length_m": round(P.bounds[2] - P.bounds[0], 1)})
    cc.render(ID, [
        {"view": "amsterdam_avenue", "azimuth_deg": 260, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 16},
        {"view": "aerial", "azimuth_deg": 220, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
