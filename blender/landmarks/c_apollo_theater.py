"""Apollo Theater — 253 West 125th Street (BIN 1058654, LP-1268, NHL). George Keister, 1913-14 (Hurtig & Seamon's
New Burlesque Theater); Apollo from 1934.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (1,391 m2), an L: a 34.2 x 25.9 m front block on West 125th Street (the street is
  north of the building, local +y) with the stage house and fly tower extending 37 m south behind it.
* Height [OTI LiDAR; LP-1268]: 20.0 m to the top of the front block's cornice, which is also the highest point of
  the roof.
* Elevation [LPC designation report LP-1268]: a neo-Classical front of buff brick and terracotta over a
  cast-iron-and-glass ground floor; a giant order of four fluted Corinthian pilasters carrying a full entablature
  with a dentilled cornice; the second-storey windows are set in round-arched terracotta surrounds.
* Signage [LP-1268; Apollo Theater Foundation]: the 1940s vertical blade sign spells "APOLLO" and stands
  9.1 m tall and 1.8 m wide off the facade; the marquee below it is 12.2 m wide and projects 3.0 m.
* Auditorium [LP-1268]: 1,506 seats on two levels behind the front block; the fly tower over the stage is the
  taller rear volume.

Fidelity: real footprint; the 20.0 m cornice, the giant Corinthian order, the arched second-storey windows, the
cast-iron ground floor, the marquee and the vertical blade sign are modelled as geometry. Inferred (stated): the
storey heights (derived from the LiDAR height and the published two-storey front) and the fly-tower height. The
blade sign's lettering is a material slot, not modelled glyphs. NOT modelled: the auditorium interior, the neon
tube detail of the sign, and the rear stage-door alley structures.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_apollo_theater"
BIN = 1058654
CORNICE = 20.0
BLADE_H, BLADE_W = 9.1, 1.8
MARQUEE_W, MARQUEE_D = 12.2, 3.0


def build():
    C.reset()
    cc.materials(["brick_buff", "terracotta_cream", "cast_iron", "glass_clear", "glass_dark", "roof_dark",
                  "flag_red", "steel_dark", "emissive_warm"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []
    x0, y0, x1, y1 = P.bounds
    front = C._clean_polygon(P.intersection(C.rect_xy(x0 - 1, y1 - 26.0, x1 + 1, y1 + 1)).buffer(0))
    rear = C._clean_polygon(P.difference(front.buffer(0.05)).buffer(0))

    objs += cc.base_and_wall(f"{ID}_ground", P, 5.6, C.M.cast_iron, recess=0.5, material_top=C.M.roof_dark)
    objs.append(C.prism(f"{ID}_stagehouse", rear, 5.6, 17.5, C.M.brick_buff, material_top=C.M.roof_dark,
                        role="mass"))
    objs.append(C.prism(f"{ID}_flytower", C.offset_polygon(front, -3.0), 5.6, 18.6, C.M.brick_buff,
                        material_top=C.M.roof_dark, role="mass"))
    fen = C.Fenestration(bay_w=3.4, window_frac=0.55, recess=0.4, spandrel_h=0.9, spandrel_proud=0.12,
                         pier="brick_buff", spandrel="terracotta_cream", glass="glass_dark",
                         floor_z=[5.6, 11.0, 16.0], window_h=3.0)
    objs += C.tower_tier(f"{ID}_front", front, 5.6, CORNICE - 2.0, fen, roof_material="roof_dark", parapet_h=0.0)
    # (the cornice above tops out at exactly CORNICE; nothing on this building rises higher)

    b = C.MeshBuilder()
    e0, e1, L, t, n = C.edge_facing(C.ring_coords(front), 90.0)      # the West 125th Street facade
    # cast-iron-and-glass ground floor with the entrance doors
    nbay = 5
    for k in range(nbay):
        a = e0 + t * (L * k / nbay + 0.6)
        c = e0 + t * (L * (k + 1) / nbay - 0.6)
        C.window_punch(b, a, c, n, 1.7, 4.8, 0.45, C.M.cast_iron, C.M.glass_clear, sill=0.0)
    # giant order: four fluted Corinthian pilasters from 5.6 m to the entablature
    for k in range(4):
        u = L * (k + 0.5) / 4
        q = e0 + t * u
        C.column(b, q[0] + n[0] * 0.55, q[1] + n[1] * 0.55, 5.6, CORNICE - 4.6 - 5.6, 0.62, C.M.terracotta_cream,
                 order="corinthian", segments=14)
    # arched second-storey windows between the pilasters
    for k in range(3):
        u0 = L * (k + 1) / 4 - 1.9
        u1 = L * (k + 1) / 4 + 1.9
        a = e0 + t * u0
        c = e0 + t * u1
        C.arched_opening(b, a, c, n, 8.4, 12.4, None, 0.5, C.M.terracotta_cream, C.M.glass_dark)
    # entablature and dentilled cornice
    b.box_from_to(e0, e1, n, 0.55, CORNICE - 4.6, CORNICE - 2.6, C.M.terracotta_cream)
    for k in range(int(L // 0.85)):
        q = e0 + t * (0.42 + 0.85 * k)
        b.box_from_to(q, q + t * 0.42, n, 0.95, CORNICE - 2.6, CORNICE - 2.0, C.M.terracotta_cream)
    objs.append(b.build(f"{ID}_facade"))
    objs.append(C.cornice(f"{ID}_cornice", front, CORNICE - 2.0,
                          [(0.5, 0.0), (1.5, 0.9), (1.5, 1.5), (0.5, 1.85)], C.M.terracotta_cream))

    # ---- the marquee and the vertical blade sign ------------------------------------------------------------------
    b = C.MeshBuilder()
    mid = (e0 + e1) / 2
    b.box_from_to(mid - t * (MARQUEE_W / 2), mid + t * (MARQUEE_W / 2), n, MARQUEE_D, 4.8, 6.4, C.M.steel_dark)
    b.box_from_to(mid - t * (MARQUEE_W / 2 - 0.2), mid + t * (MARQUEE_W / 2 - 0.2), n, MARQUEE_D - 0.15, 5.0, 6.2,
                  C.M.emissive_warm)
    blade0 = mid - t * (BLADE_W / 2)
    blade1 = mid + t * (BLADE_W / 2)
    b.box_from_to(blade0, blade1, n, 1.4, 6.4, 6.4 + BLADE_H, C.M.flag_red)
    for side in (0.05, 1.35):                                        # the two illuminated sign faces
        for k in range(6):                                           # the six letters of APOLLO as lit panels
            z = 6.4 + BLADE_H * (0.06 + 0.15 * k)
            b.box_from_to(blade0 + t * 0.25, blade1 - t * 0.25, n, side + 0.02, z, z + BLADE_H * 0.12,
                          C.M.emissive_warm)
    objs.append(b.build(f"{ID}_marquee_and_blade"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the 20.0 m cornice (OTI LiDAR); the giant order of four fluted "
                          "Corinthian pilasters, the arched second-storey terracotta surrounds, the cast-iron-and-"
                          "glass ground floor, the dentilled entablature, the 12.2 m marquee and the 9.1 m vertical "
                          "blade sign. Inferred (stated): the storey heights and the fly-tower height, derived from "
                          "the LiDAR height and the published two-storey front. Simplified: the blade sign's "
                          "'APOLLO' lettering is six emissive panels, not modelled glyphs. Not modelled: the "
                          "1,506-seat auditorium interior, the neon tube detail, the stage-door alley structures."),
                      dimensions={"cornice_m": CORNICE, "blade_sign_m": [BLADE_W, BLADE_H],
                                  "marquee_m": [MARQUEE_W, MARQUEE_D], "seats": 1506})
    cc.render(ID, [
        {"view": "w125th", "azimuth_deg": 30, "elevation_deg": "street", "distance": 85, "fov_deg": 52, "look_up_deg": 14},
        {"view": "aerial", "azimuth_deg": 30, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
