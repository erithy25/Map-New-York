"""Kings Theatre (Loew's Kings) — 1027 Flatbush Avenue, Brooklyn (BIN 3117845, LP-2213).
Rapp & Rapp with Harold W. Rambusch, 1929; restored by Martinez+Johnson, 2015.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (4,539 m2), 104.7 x 74.8 m: a narrow terracotta-faced entrance block on Flatbush
  Avenue and the much larger auditorium and stage house behind it.
* Height [OTI LiDAR; LP-2213]: 25.2 m at the fly tower over the stage; the Flatbush Avenue facade's cornice is at
  19.0 m and the auditorium roof at 21.0 m.
* Facade [LPC designation report LP-2213]: a French Baroque front of **glazed cream terracotta** over a
  cast-iron-and-glass ground floor, with a giant arched central window 9.0 m wide and 12.0 m high framed by paired
  pilasters, swags, cartouches and a broken segmental pediment; the vertical "KINGS" blade sign and the marquee
  were reconstructed in 2015 (marquee 14.0 m wide, projecting 3.6 m; blade sign 11.0 m tall).
* Auditorium [LP-2213]: 3,200 seats (3,676 as built) on an orchestra and one balcony; the stage house is the tallest
  volume.
* Material [LP-2213]: cream architectural terracotta, brick to the side and rear elevations.

Fidelity: real footprint; the 25.2 m fly tower, the 19.0 m terracotta facade with its giant arched window, paired
pilasters and broken pediment, and the reconstructed marquee and blade sign are modelled as geometry. Inferred
(stated): the split of the footprint between the entrance block, the auditorium and the stage house (cut at the
polygon's own vertices), and the storey heights. NOT modelled: the landmarked auditorium interior and its plaster
ornament, the terracotta's modelled swags and cartouches (flat panels), and the roof plant.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_kings_theatre"
BIN = 3117845
FLY_TOP = 25.2
FACADE_CORNICE = 19.0
AUDITORIUM_TOP = 21.0
ARCH_W, ARCH_H = 9.0, 12.0
MARQUEE_W, MARQUEE_D = 14.0, 3.6
BLADE_H = 11.0
SEATS = 3200


def build():
    C.reset()
    cc.materials(["terracotta_cream", "brick_red", "cast_iron", "glass_clear", "glass_dark", "roof_dark",
                  "emissive_warm", "flag_red", "steel_dark", "gold"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    x0, y0, x1, y1 = P.bounds
    objs: list = []
    # the Flatbush Avenue front is the short east edge of the polygon
    front = C._clean_polygon(P.intersection(C.rect_xy(x1 - 22.0, y0 - 1, x1 + 1, y1 + 1)).buffer(0))
    rest = C._clean_polygon(P.difference(front.buffer(0.05)).buffer(0))

    objs.append(C.plinth(f"{ID}_ground", P, 0.0, 5.4, C.M.cast_iron, material_top=C.M.roof_dark))
    objs.append(C.prism(f"{ID}_auditorium", rest, 5.4, AUDITORIUM_TOP, C.M.brick_red, material_top=C.M.roof_dark,
                        role="mass"))
    fly = C._clean_polygon(rest.intersection(C.rect_xy(x0 - 1, y0 - 1, x0 + 26.0, y1 + 1)).buffer(0))
    objs.append(C.prism(f"{ID}_flytower", fly, AUDITORIUM_TOP, FLY_TOP, C.M.brick_red, material_top=C.M.roof_dark,
                        role="mass"))
    objs.append(C.prism(f"{ID}_front_block", front, 5.4, FACADE_CORNICE - 1.6, C.M.terracotta_cream,
                        material_top=C.M.roof_dark, role="mass"))

    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(C.ring_coords(front), 0.0)
    mid = (p0 + p1) / 2
    # the cast-iron-and-glass ground floor
    for k in range(4):
        a = mid + t * (-L / 2 + L * k / 4 + 0.7)
        c = mid + t * (-L / 2 + L * (k + 1) / 4 - 0.7)
        C.window_punch(b, a, c, n, 0.5, 4.4, 0.4, C.M.cast_iron, C.M.glass_clear, sill=0.0)
    # the giant arched central window with paired pilasters
    C.arched_opening(b, mid - t * (ARCH_W / 2), mid + t * (ARCH_W / 2), n, 6.0, ARCH_H + 6.0 - ARCH_W / 2,
                     ARCH_W / 2, 1.2, C.M.terracotta_cream, C.M.glass_dark)
    for du in (-(ARCH_W / 2 + 1.6), (ARCH_W / 2 + 1.6)):
        for dd in (-0.75, 0.75):
            C.pilaster(b, mid + t * (du + dd - 0.45), mid + t * (du + dd + 0.45), n, 5.4, FACADE_CORNICE - 3.4, 0.75,
                       C.M.terracotta_cream)
    b.box_from_to(p0, p1, n, 0.9, FACADE_CORNICE - 3.4, FACADE_CORNICE - 1.6, C.M.terracotta_cream)
    # the broken segmental pediment over the arch
    for sgn in (-1.0, 1.0):
        a = mid + t * (sgn * ARCH_W / 2)
        c = mid + t * (sgn * 1.2)
        b.hull([(a[0], a[1], FACADE_CORNICE - 1.6), (c[0], c[1], FACADE_CORNICE - 1.6),
                (a[0] + n[0] * 1.2, a[1] + n[1] * 1.2, FACADE_CORNICE - 1.6),
                (c[0] + n[0] * 1.2, c[1] + n[1] * 1.2, FACADE_CORNICE - 1.6),
                (a[0], a[1], FACADE_CORNICE + 0.2), (c[0], c[1], FACADE_CORNICE + 1.8),
                (a[0] + n[0] * 1.2, a[1] + n[1] * 1.2, FACADE_CORNICE + 0.2),
                (c[0] + n[0] * 1.2, c[1] + n[1] * 1.2, FACADE_CORNICE + 1.8)], C.M.terracotta_cream)
    b.lathe([(1.1, 0.0), (0.7, 1.4), (0.9, 2.0), (0.0, 3.2)], 12, C.M.gold,
            origin=(mid[0] + n[0] * 0.6, mid[1] + n[1] * 0.6, FACADE_CORNICE))       # the central cartouche urn
    # the marquee and the vertical blade sign
    b.box_from_to(mid - t * (MARQUEE_W / 2), mid + t * (MARQUEE_W / 2), n, MARQUEE_D, 4.6, 6.6, C.M.steel_dark)
    b.box_from_to(mid - t * (MARQUEE_W / 2 - 0.25), mid + t * (MARQUEE_W / 2 - 0.25), n, MARQUEE_D - 0.2, 4.8, 6.4,
                  C.M.emissive_warm)
    b.box_from_to(mid - t * 1.6, mid + t * 1.6, n, 1.6, 6.6, 6.6 + BLADE_H, C.M.flag_red)
    for k in range(5):
        z = 7.2 + (BLADE_H - 1.6) * k / 5
        b.box_from_to(mid - t * 1.25, mid + t * 1.25, n, 1.66, z, z + 1.3, C.M.emissive_warm)
    objs.append(b.build(f"{ID}_facade"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the 25.2 m fly tower (OTI LiDAR); the 19.0 m glazed-terracotta "
                          "Flatbush Avenue front with its 9.0 x 12.0 m giant arched window, paired pilasters, broken "
                          "segmental pediment and cartouche urn; the cast-iron-and-glass ground floor; the 2015 "
                          "reconstructed 14.0 m marquee and 11.0 m blade sign. Inferred (stated): the split of the "
                          "footprint between entrance block, auditorium and stage house (cut at the polygon's own "
                          "vertices) and the storey heights. Not modelled: the landmarked auditorium interior and "
                          "its plaster ornament, the terracotta swags and cartouches in relief (flat panels), roof "
                          "plant."),
                      dimensions={"fly_tower_m": FLY_TOP, "facade_cornice_m": FACADE_CORNICE,
                                  "auditorium_top_m": AUDITORIUM_TOP, "arch_m": [ARCH_W, ARCH_H],
                                  "marquee_m": [MARQUEE_W, MARQUEE_D], "blade_sign_m": BLADE_H, "seats": SEATS})
    cc.render(ID, [
        {"view": "flatbush_avenue", "azimuth_deg": 90, "elevation_deg": "street", "distance": 90, "fov_deg": 52, "look_up_deg": 14},
        {"view": "aerial", "azimuth_deg": 110, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
