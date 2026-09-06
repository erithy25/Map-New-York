"""Barclays Center — 620 Atlantic Avenue, Brooklyn (BIN 3398156). SHoP Architects with Ellerbe Becket / AECOM, 2012.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (18,607 m2), 181.8 x 166.6 m, on the wedge where Atlantic and Flatbush Avenues
  meet (the acute corner is the oculus end).
* Height [SHoP; OTI LiDAR]: **137 ft = 41.8 m**; the LiDAR roof is 42.1 m, which the model uses.
* Weathering-steel skin [SHoP; ASI Limited]: **12,000 pre-weathered steel panels** in **three horizontal bands**
  that wrap the building and peel away over the entrance; each panel is a parallelogram roughly 1.5 x 4.9 m, and
  the three bands are separated by continuous glazed slots.
* Oculus [SHoP]: the entrance canopy cantilevers **82 ft = 25.0 m** over the plaza and carries a 30 ft = 9.1 m
  diameter oval opening ringed by an LED display band; the canopy soffit is 9.5 m above the plaza.
* Arena bowl [Ellerbe Becket]: the seating bowl is sunk below street level so the concourse is at grade; capacity
  17,732 for basketball with the court 28.65 x 15.24 m.
* Plaza [SHoP]: the triangular public plaza at the Atlantic/Flatbush corner, under the oculus, with the subway
  entrance behind it.

Fidelity: real footprint; the 42.1 m height, the three weathering-steel bands with their glazed slots and panel
rhythm, the 25.0 m oculus cantilever with its 9.1 m opening and LED ring, the sunken bowl and the regulation court
are modelled as geometry. Inferred (stated): the band heights and panel size (from photographs and the published
panel count), the bowl's rake, and the plaza extent. NOT modelled: the individual twist of each of the 12,000
panels (they are modelled as flat panels on the band surface), the interiors, the green roof added in 2015, and the
subway entrance canopy.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_barclays_center"
BIN = 3398156
TOP = 42.1
BANDS = ((3.0, 15.0), (17.0, 28.0), (30.0, TOP - 0.6))
PANEL_W, PANEL_H = 4.9, 1.5
OCULUS_CANTILEVER = 25.0
OCULUS_D = 9.1
COURT = (28.65, 15.24)
CAPACITY = 17732


def build():
    C.reset()
    # weathering (Cor-Ten) steel: not in the shared palette, so its albedo is declared here
    C.custom_material("rust", (122, 74, 50), roughness=0.72, metallic=0.25,
                      note="pre-weathered / Cor-Ten steel [SHoP Barclays Center panels; High Line viaduct girders]")
    cc.materials(["rust", "steel_dark", "glass_clear", "glass_dark", "concrete", "concrete_dark", "pavement",
                  "roof_dark", "emissive_warm", "wood_dark"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    objs: list = []
    coords = C.ring_coords(P)

    objs.append(C.plinth(f"{ID}_base", P, 0.0, 3.0, C.M.concrete_dark, material_top=C.M.pavement))
    objs.append(C.tag(C.prism(f"{ID}_body", C.offset_polygon(P, -1.2), 3.0, TOP - 0.6, C.M.glass_dark,
                              material_top=C.M.roof_dark), "mass"))
    # the three weathering-steel bands, each a run of flat panels standing 1.2 m proud of the glazed slots
    b = C.MeshBuilder()
    for z0, z1 in BANDS:
        for p0, p1, L, t, n in C.edges_of(coords):
            npan = max(1, int(round(L / PANEL_W)))
            nrow = max(1, int(round((z1 - z0) / PANEL_H)))
            for i in range(npan):
                q0 = p0 + t * (L * i / npan)
                q1 = p0 + t * (L * (i + 1) / npan)
                for j in range(nrow):
                    za = z0 + (z1 - z0) * j / nrow
                    zb = z0 + (z1 - z0) * (j + 1) / nrow
                    skew = 0.55 * math.sin(math.pi * (i / npan) * 3.0 + j)
                    b.quad((q0[0] + n[0] * (1.2 + skew * 0.25), q0[1] + n[1] * (1.2 + skew * 0.25), za),
                           (q1[0] + n[0] * (1.2 - skew * 0.25), q1[1] + n[1] * (1.2 - skew * 0.25), za),
                           (q1[0] + n[0] * (1.2 - skew * 0.25), q1[1] + n[1] * (1.2 - skew * 0.25), zb),
                           (q0[0] + n[0] * (1.2 + skew * 0.25), q0[1] + n[1] * (1.2 + skew * 0.25), zb), C.M.rust)
            b.box_from_to(p0, p1, n, 1.35, z0 - 0.35, z0, C.M.steel_dark)
            b.box_from_to(p0, p1, n, 1.35, z1, z1 + 0.35, C.M.steel_dark)
    objs.append(b.build(f"{ID}_bands"))

    # ---- the oculus canopy over the Atlantic/Flatbush corner ------------------------------------------------------
    # the acute corner of the polygon is the entrance end: find the vertex with the smallest interior angle
    n_ = len(coords)
    best, best_ang = 0, 999.0
    for i in range(n_):
        a = np.array(coords[i - 1]) - np.array(coords[i])
        c = np.array(coords[(i + 1) % n_]) - np.array(coords[i])
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(a @ c) / (np.linalg.norm(a) * np.linalg.norm(c))))))
        if ang < best_ang:
            best, best_ang = i, ang
    corner = np.array(coords[best])
    cen = np.array([P.centroid.x, P.centroid.y])
    out = (corner - cen) / np.linalg.norm(corner - cen)
    side = np.array([-out[1], out[0]])
    b = C.MeshBuilder()
    tip = corner + out * OCULUS_CANTILEVER
    for z, mat_ in ((9.5, C.M.steel_dark), (12.5, C.M.rust)):
        b.ngon([(corner[0] + side[0] * 26.0, corner[1] + side[1] * 26.0, z),
                (tip[0] + side[0] * 7.0, tip[1] + side[1] * 7.0, z),
                (tip[0] - side[0] * 7.0, tip[1] - side[1] * 7.0, z),
                (corner[0] - side[0] * 26.0, corner[1] - side[1] * 26.0, z)], mat_, flip=(z < 10.0))
    for pa, pb in (((corner + side * 26.0), (tip + side * 7.0)), ((tip + side * 7.0), (tip - side * 7.0)),
                   ((tip - side * 7.0), (corner - side * 26.0))):
        b.quad((pa[0], pa[1], 9.5), (pb[0], pb[1], 9.5), (pb[0], pb[1], 12.5), (pa[0], pa[1], 12.5), C.M.rust)
    ocx = corner + out * (OCULUS_CANTILEVER * 0.58)
    b.lathe([(OCULUS_D / 2, 0.0), (OCULUS_D / 2, 3.0)], 28, C.M.emissive_warm, origin=(ocx[0], ocx[1], 9.5),
            cap=False, scale_xy=(1.55, 1.0))
    for k in range(4):                                    # the canopy's tapering steel struts
        u = -20.0 + 40.0 * k / 3
        q = corner + side * u
        b.hull([(q[0] - 0.4, q[1] - 0.4, 3.0), (q[0] + 0.4, q[1] + 0.4, 3.0),
                (q[0] - 0.4, q[1] + 0.4, 3.0), (q[0] + 0.4, q[1] - 0.4, 3.0),
                (q[0] - 0.3, q[1] - 0.3, 9.5), (q[0] + 0.3, q[1] + 0.3, 9.5)], C.M.steel_dark)
    objs.append(b.build(f"{ID}_oculus"))

    # ---- the sunken bowl and the court ---------------------------------------------------------------------------
    b = C.MeshBuilder()
    bowl = C.offset_polygon(P, -22.0)
    court = C.rect(P.centroid.x, P.centroid.y, COURT[0], COURT[1])
    if not bowl.is_empty:
        b.loft([[(x, y, 3.0) for x, y in C.ring_coords(bowl)],
                [(x, y, -9.0) for x, y in C.offset_ring(C.ring_coords(bowl), -18.0)]], C.M.concrete_dark,
               cap_top=False, cap_bottom=False)
    b.prism(C.ring_coords(court), -9.0, -8.9, C.M.wood_dark)
    objs.append(C.tag(b.build(f"{ID}_bowl"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint on the Atlantic/Flatbush wedge; 42.1 m high; three "
                          "weathering-steel bands of panels on a 4.9 x 1.5 m module with continuous glazed slots "
                          "between them; the oculus canopy cantilevering 82 ft = 25.0 m with a 9.1 m LED-ringed "
                          "opening and a 9.5 m soffit; the bowl sunk 12 m below the concourse with a regulation "
                          "28.65 x 15.24 m court. Inferred (stated): the band heights and panel size (from "
                          "photographs and the published 12,000-panel count), the bowl rake and the plaza extent. "
                          "Not modelled: the individual twist of each panel (flat panels on the band surface), "
                          "interiors, the 2015 green roof, the subway entrance canopy."),
                      dimensions={"top_m": TOP, "bands_z_m": [list(x) for x in BANDS], "panel_m": [PANEL_W, PANEL_H],
                                  "panels_published": 12000, "oculus_cantilever_m": OCULUS_CANTILEVER,
                                  "oculus_opening_m": OCULUS_D, "court_m": list(COURT), "capacity": CAPACITY})
    cc.render(ID, [
        {"view": "atlantic_flatbush", "azimuth_deg": 45, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 11},
        {"view": "aerial", "azimuth_deg": 45, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
