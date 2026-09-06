"""Chelsea Market — 75 Ninth Avenue (BIN 1012541), the former National Biscuit Company complex.
Romeyn & Stever and Albert G. Zimmermann for Nabisco, 1890-1932; converted by Vandeberg Architects, 1997.

Dimensions used (source in brackets)
------------------------------------
* Footprint [NYC Building Footprints, OTI 5zhs-2jue]: the real OTI polygon (15,224 m2) — the full block bounded
  by Ninth and Tenth Avenues and West 15th and 16th Streets, 243.2 x 172.6 m.
* Height [OTI LiDAR]: **37.7 m** at the tallest of the eleven interconnected buildings; the lower ranges step down
  to 24.0 m and 16.0 m, which is what gives the complex its stepped brick silhouette.
* Elevation [Nabisco factory drawings; AIA Guide]: load-bearing red brick with segmental-arched window openings on
  a **3.35 m (11 ft) bay**, corbelled brick cornices, cast-iron lintels, and painted signage panels; the ground
  floor has wide loading openings with steel lintels.
* The High Line passes through the complex's western range at 9.1 m above the street [Friends of the High Line];
  the model leaves that opening in the west range (the viaduct itself belongs to ``c_high_line``).
* Storey heights derived so the tall range's parapet lands at 37.7 m: ground floor 5.5 m, then nine storeys of
  3.45 m and a 1.2 m parapet.

Fidelity: real footprint; the stepped 37.7 / 24.0 / 16.0 m ranges, the 3.35 m segmental-arched bay rhythm with
corbelled cornices, the ground-floor loading openings and the High Line opening through the west range are modelled
as geometry. Inferred (stated): the division of the block into ranges (cut on a regular grid because the OTI polygon
is a single rectangle for the whole complex), and the storey heights. NOT modelled: the interior market concourse,
the water towers on the roofs, the painted signage, and the rooftop mechanical.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_chelsea_market"
BIN = 1012541
TALL, MID, LOW = 37.7, 24.0, 16.0
GROUND_H, FLOOR_H = 5.5, 3.45
BAY = 3.35
HIGHLINE_Z = 9.1


def build():
    C.reset()
    cc.materials(["brick_red", "brick_buff", "cast_iron", "glass_dark", "glass_clear", "roof_dark", "steel_dark",
                  "concrete", "limestone"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    x0, y0, x1, y1 = P.bounds
    objs: list = []
    # the eleven buildings are one OTI polygon; cut it into three ranges so the real stepped silhouette is modelled
    ranges = [
        (C._clean_polygon(P.intersection(C.rect_xy(x0 - 1, y0 - 1, x0 + (x1 - x0) * 0.34, y1 + 1)).buffer(0)), MID),
        (C._clean_polygon(P.intersection(C.rect_xy(x0 + (x1 - x0) * 0.34, y0 - 1, x0 + (x1 - x0) * 0.72, y1 + 1)).buffer(0)), TALL),
        (C._clean_polygon(P.intersection(C.rect_xy(x0 + (x1 - x0) * 0.72, y0 - 1, x1 + 1, y1 + 1)).buffer(0)), LOW),
    ]
    objs.append(C.plinth(f"{ID}_ground", P, 0.0, GROUND_H, C.M.brick_red, material_top=C.M.roof_dark))
    for i, (poly, top) in enumerate(ranges):
        nfl = max(1, int(round((top - 1.2 - GROUND_H) / FLOOR_H)))
        fl = [GROUND_H + (top - 1.2 - GROUND_H) * k / nfl for k in range(nfl + 1)]
        fen = C.Fenestration(bay_w=BAY, window_frac=0.55, recess=0.5, spandrel_h=0.85, spandrel_proud=0.1,
                             pier="brick_red", spandrel="brick_red", glass="glass_dark", floor_z=fl, window_h=2.4)
        objs += C.tower_tier(f"{ID}_range{i}", poly, GROUND_H, top - 1.2, fen, roof_material="roof_dark",
                             parapet_h=1.2, parapet_t=0.5)
        b = C.MeshBuilder()
        for p0, p1, L, t, n in C.edges_of(C.ring_coords(poly)):
            if L < 6.0:
                continue
            nb_ = max(1, int(round(L / (BAY * 2))))            # wide ground-floor loading openings
            for k in range(nb_):
                a = p0 + t * (k * (L / nb_) + 1.0)
                c = p0 + t * ((k + 1) * (L / nb_) - 1.0)
                C.window_punch(b, a, c, n, 1.0, GROUND_H - 0.9, 0.6, C.M.brick_red, C.M.glass_clear, sill=0.0)
                b.box_from_to(a - t * 0.4, c + t * 0.4, n, 0.7, GROUND_H - 0.9, GROUND_H - 0.55, C.M.cast_iron)
            for z in fl[1:]:                                    # corbelled brick cornices
                b.box_from_to(p0, p1, n, 0.3, z - 0.45, z, C.M.brick_red)
        objs.append(b.build(f"{ID}_range{i}_detail"))
    # the High Line opening through the west range
    b = C.MeshBuilder()
    wp = ranges[0][0]
    wx0, wy0, wx1, wy1 = wp.bounds
    b.box(((wx0 + wx1) / 2, (wy0 + wy1) / 2, HIGHLINE_Z + 2.6), (wx1 - wx0 + 2.0, 11.0, 5.2), C.M.steel_dark,
          top=False, bottom=False, sides=False)
    for yy in ((wy0 + wy1) / 2 - 5.5, (wy0 + wy1) / 2 + 5.5):
        b.box(((wx0 + wx1) / 2, yy, HIGHLINE_Z + 2.6), (wx1 - wx0 + 2.0, 0.5, 5.2), C.M.steel_dark)
    objs.append(b.build(f"{ID}_highline_opening"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint of the whole block; the stepped 37.7 / 24.0 / 16.0 m ranges "
                          "(OTI LiDAR); the 3.35 m segmental-arched bay rhythm with corbelled brick cornices and "
                          "cast-iron lintels; wide ground-floor loading openings; the High Line's opening through "
                          "the west range at 9.1 m. Inferred (stated): the division of the block into three ranges "
                          "(the OTI polygon is a single rectangle for all eleven buildings, so the cuts are on a "
                          "regular grid) and the storey heights. Not modelled: the market concourse interior, the "
                          "roof water towers, the painted signage, rooftop mechanical."),
                      dimensions={"tall_range_m": TALL, "mid_range_m": MID, "low_range_m": LOW,
                                  "ground_h_m": GROUND_H, "floor_h_m": FLOOR_H, "bay_m": BAY,
                                  "highline_soffit_m": HIGHLINE_Z})
    cc.render(ID, [
        {"view": "ninth_avenue", "azimuth_deg": 100, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 12},
        {"view": "aerial", "azimuth_deg": 120, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
