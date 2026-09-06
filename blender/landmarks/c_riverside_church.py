"""Riverside Church — 490 Riverside Drive (BINs 1081792 tower and nave, 1081791 the parish house; LP-2037).
Allen & Collens with Henry C. Pelton, 1927-30; south wing 1955.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the two real OTI polygons (4,905 m2). Riverside Drive is west (local -x); the tower stands over the
  narthex at the north end and the nave runs south from it.
* Height [Riverside Church; OSM]: the tower is **392 ft = 119.5 m** to the top of its parapet and 120.1 m to the
  lantern; 22 usable storeys. OTI LiDAR gives 118.0 m for the tower footprint, consistent to 1.7 %.
* Tower [Allen & Collens; modelled on the 13th-century tower of Chartres]: a square Gothic shaft with corner
  buttresses that set back three times, a belfry stage with tall two-light openings, and an open octagonal lantern
  above; it carries the **Laura Spelman Rockefeller Memorial Carillon of 74 bells**, the largest in the world, whose
  20-tonne bourdon hangs in the belfry.
* Nave [LP-2037]: seven bays, vault ridge at 30.0 m, aisle roofs at 20.0 m, with flying buttresses and traceried
  windows; the parish house east of it is 41.0 m (OTI LiDAR).
* West front [LP-2037]: a deeply recessed portal modelled on Chartres' Portail Royal, 9.0 m wide and 14.0 m high,
  with five orders of moulding.
* Material [LP-2037]: Indiana limestone over a steel frame.

Fidelity: two real footprints; the 120.1 m tower with its three buttress setbacks, belfry openings and octagonal
lantern, the seven-bay nave with flying buttresses and traceried windows, and the recessed west portal are modelled
as geometry. Inferred (stated): the setback heights of the tower buttresses and the bay rhythm (nave length divided
by the published seven bays); the belfry's bells are not modelled individually. NOT modelled: the interiors, the
carved figures of the portal, the stained glass patterns, and the 1955 south wing's later alterations.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_riverside_church"
B_TOWER, B_PARISH = 1081792, 1081791
TOWER_TOP = 120.1
PARAPET = 119.5
NAVE_RIDGE = 30.0
AISLE_TOP = 20.0
PARISH_TOP = 41.0
NAVE_BAYS = 7
BELLS = 74


def build():
    C.reset()
    cc.materials(["limestone", "limestone_dark", "granite_grey", "glass_dark", "glass_clear", "slate", "roof_dark",
                  "bronze", "copper_green"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_TOWER)
    Pt = g.poly(B_TOWER)
    Pp = g.poly(B_PARISH)
    objs: list = []
    tx0, ty0, tx1, ty1 = Pt.bounds

    objs.append(C.plinth(f"{ID}_tower_base", Pt, 0.0, AISLE_TOP, C.M.limestone, material_top=C.M.slate))
    objs.append(C.plinth(f"{ID}_parish_base", Pp, 0.0, 6.0, C.M.limestone, material_top=C.M.slate))
    fen_p = C.Fenestration(floor_h=(PARISH_TOP - 6.0) / 9, bay_w=3.2, window_frac=0.5, recess=0.45, spandrel_h=0.9,
                           spandrel_proud=0.12, pier="limestone", spandrel="limestone", glass="glass_dark",
                           window_h=2.3)
    objs += C.tower_tier(f"{ID}_parish", Pp, 6.0, PARISH_TOP - 1.4, fen_p, roof_material="slate", parapet_h=1.4,
                         parapet_t=0.5)

    # ---- the nave: the southern part of the tower polygon --------------------------------------------------------
    nave = C._clean_polygon(Pt.intersection(C.rect_xy(tx0 - 1, ty0 - 1, tx1 + 1, ty0 + 46.0)).buffer(0))
    objs.append(C.prism(f"{ID}_nave", C.offset_polygon(nave, -7.0), AISLE_TOP, NAVE_RIDGE - 5.0, C.M.limestone,
                        material_top=C.M.slate, role="mass"))
    b = C.MeshBuilder()
    nr = C.ring_coords(C.offset_polygon(nave, -7.0))
    b.loft([[(x, y, NAVE_RIDGE - 5.0) for x, y in nr], [(x, y, NAVE_RIDGE) for x, y in C.offset_ring(nr, -4.0)]],
           C.M.slate, cap_top=True, cap_bottom=False, material_top=C.M.slate)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(nave)):
        if L < 16.0:
            continue
        for k in range(NAVE_BAYS):
            q = p0 + t * (L * (k + 0.5) / NAVE_BAYS)
            a = q - t * 2.1
            c = q + t * 2.1
            C.arched_opening(b, a, c, n, 6.5, 15.0, 2.1, 0.9, C.M.limestone, C.M.glass_dark, pointed=True)
            b.box_from_to(q - t * 1.0, q + t * 1.0, n, 1.5, 0.0, AISLE_TOP + 1.5, C.M.limestone)     # buttress
            b.lathe([(1.2, 0.0), (0.0, 3.4)], 8, C.M.limestone, origin=(q[0] + n[0] * 0.9, q[1] + n[1] * 0.9,
                                                                        AISLE_TOP + 1.5))
    objs.append(b.build(f"{ID}_nave_detail"))

    # ---- the tower --------------------------------------------------------------------------------------------
    shaft = C._clean_polygon(Pt.intersection(C.rect_xy(tx0 - 1, ty1 - 33.0, tx1 + 1, ty1 + 1)).buffer(0))
    stages = [(AISLE_TOP, 0.0), (52.0, -0.9), (80.0, -1.8), (PARAPET - 14.0, -2.7)]
    b = C.MeshBuilder()
    for i, (ztop, off) in enumerate(stages):
        z0 = AISLE_TOP if i == 0 else stages[i - 1][0]
        poly = C.offset_polygon(shaft, off)
        b.prism(C.ring_coords(poly), z0, ztop, C.M.limestone, cap_bottom=False,
                cap_top=(i == len(stages) - 1), material_top=C.M.slate)
        for p0, p1, L, t, nn in C.edges_of(C.ring_coords(poly)):     # traceried two-light openings per stage
            for k in range(2):
                q = p0 + t * (L * (k + 0.5) / 2)
                a = q - t * 1.7
                c = q + t * 1.7
                C.arched_opening(b, a, c, nn, z0 + (ztop - z0) * 0.35, ztop - 3.0, 1.7, 0.7, C.M.limestone,
                                 C.M.glass_dark, pointed=True)
        for cxy in ((poly.bounds[0], poly.bounds[1]), (poly.bounds[2], poly.bounds[1]),
                    (poly.bounds[0], poly.bounds[3]), (poly.bounds[2], poly.bounds[3])):    # corner buttresses
            b.box((cxy[0], cxy[1], (z0 + ztop) / 2), (3.2, 3.2, ztop - z0), C.M.limestone)
    # the belfry stage and the open octagonal lantern
    top = C.offset_polygon(shaft, -2.7)
    tcx, tcy = top.centroid.x, top.centroid.y
    b.prism(C.ring_coords(top), PARAPET - 14.0, PARAPET, C.M.limestone, cap_bottom=False, cap_top=False)
    for p0, p1, L, t, nn in C.edges_of(C.ring_coords(top)):
        for k in range(3):
            q = p0 + t * (L * (k + 0.5) / 3)
            C.arched_opening(b, q - t * 1.4, q + t * 1.4, nn, PARAPET - 12.5, PARAPET - 2.5, 1.4, 0.8,
                             C.M.limestone, C.M.bronze, pointed=True)
    r = min(top.bounds[2] - top.bounds[0], top.bounds[3] - top.bounds[1]) / 2 - 1.5
    b.lathe([(r, 0.0), (r, 0.6), (r - 0.9, 0.6), (r - 0.9, 0.0)], 8, C.M.limestone, origin=(tcx, tcy, PARAPET),
            phase_deg=22.5, cap=False)
    b.lathe([(r - 0.5, 0.6), (r - 0.5, TOWER_TOP - PARAPET - 0.4), (0.0, TOWER_TOP - PARAPET)], 8, C.M.copper_green,
            origin=(tcx, tcy, PARAPET), phase_deg=22.5)
    # the west portal, modelled on the Portail Royal: five recessed orders
    p0, p1, L, t, nn = C.edge_facing(C.ring_coords(shaft), 180.0)
    mid = (p0 + p1) / 2
    for k in range(5):
        w = 9.0 - k * 1.1
        C.arched_opening(b, mid - t * (w / 2), mid + t * (w / 2), nn, 0.0, 14.0 - k * 1.4 - w / 2, w / 2,
                         0.9 + k * 0.55, C.M.limestone, C.M.bronze, pointed=True)
    objs.append(C.tag(b.build(f"{ID}_tower"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: two real OTI footprints; the 392 ft = 119.5 m tower parapet and the 120.1 m "
                          "lantern; three buttress setbacks; the belfry stage with pointed two-light openings; the "
                          "open octagonal lantern; the seven-bay nave with a 30.0 m ridge, flying buttresses and "
                          "traceried windows; the five-order recessed west portal; the 41.0 m parish house. "
                          "Inferred (stated): the tower's setback heights and the bay rhythm (nave length / seven "
                          "published bays). Not modelled: the 74 carillon bells individually, interiors, the carved "
                          "portal figures, the stained-glass patterns."),
                      dimensions={"tower_top_m": TOWER_TOP, "tower_parapet_m": PARAPET, "nave_ridge_m": NAVE_RIDGE,
                                  "aisle_top_m": AISLE_TOP, "parish_house_m": PARISH_TOP, "nave_bays": NAVE_BAYS,
                                  "carillon_bells": BELLS})
    cc.render(ID, [
        {"view": "riverside_drive", "azimuth_deg": 250, "elevation_deg": "street", "distance": 180, "fov_deg": 55, "look_up_deg": 30},
        {"view": "aerial", "azimuth_deg": 230, "elevation_deg": 26},
    ])
    return entry


if __name__ == "__main__":
    main()
