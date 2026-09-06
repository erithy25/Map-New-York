"""Seagram Building — 375 Park Avenue (BIN 1036465, LP-1664). Ludwig Mies van der Rohe with Philip Johnson, 1958.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (2,909 m2). It resolves into the 38-storey tower (west part, 43.3 m of Park Avenue
  frontage x 35.0 m deep) and the lower rear "bustle" (east part, 60.5 x 25.5 m) — both measured off the polygon.
* Height [CTBUH / LPC designation report LP-1664]: 515 ft = 157.0 m, 38 storeys. Storey heights derived so the roof
  lands at 157.0 m: ground-floor lobby 24 ft = 7.32 m [LPC], then 37 floors of 4.045 m.
* Set-back plaza [LPC LP-1664, Phyllis Lambert, *Building Seagram*]: 90 ft = 27.43 m deep across the full Park Avenue
  frontage, pink Vermont granite paving, with two 22 x 6 ft (6.7 x 1.8 m) raised pools flanking the entrance walk.
  The plaza is west of the footprint, so it is *not* part of the IoU base volume (tagged ``role="plaza"``).
* Curtain wall [LPC LP-1664]: 28 ft (8.53 m) structural bay, three window modules per bay -> 9 ft 4 in = 2.845 m
  module; bronze-toned extruded I-beam mullions 6 in (0.15 m) deep applied to the face; topaz-tinted glazing;
  bronze spandrel panels 1.10 m high at each floor line. Ground floor: 24 ft glass lobby set back 8.53 m (one bay)
  behind the perimeter line of bronze-clad columns.
* Rear bustle: 10 storeys [Lambert, *Building Seagram*] -> 7.32 + 9 x 4.045 = 43.7 m, flat roof with a 1.2 m parapet.

Fidelity: real footprint; published height, storey count, plaza depth, bay module and mullion rhythm modelled as
geometry. Inferred (stated): the split of the polygon into tower and bustle is measured from the footprint, not from
a published plan; the bustle's 10 storeys are taken from Lambert rather than a drawing. NOT modelled: the travertine
lobby and the Four Seasons Restaurant interiors, the rooftop cooling towers, the bronze entrance doors' detailing,
and the two sunken service courts on the side streets.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_seagram_building"
BIN = 1036465
ROOF_M = 157.0
LOBBY_H = 7.32          # 24 ft
FLOOR_H = (ROOF_M - LOBBY_H) / 37
BAY_M = 8.53            # 28 ft structural bay
MODULE_M = BAY_M / 3    # 9 ft 4 in window module
PLAZA_D = 27.43         # 90 ft
BUSTLE_FLOORS = 10


def build():
    C.reset()
    cc.use_textures([("granite_pink", "granite"), ("granite_dark", "granite"), ("bronze", "metal_panel")])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)     # +x east (Park Avenue is west), +y north
    P = g.poly(BIN)
    minx, miny, maxx, maxy = P.bounds
    objs: list = []

    # ---- split the footprint: tower = the part west of the bustle's west face ------------------------------------
    # the notch in the ring at x ~ +2.4 is the tower/bustle joint; take it from the polygon itself
    x_split = 2.4
    tower = C._clean_polygon(P.intersection(C.rect_xy(minx - 1, miny - 1, x_split, maxy + 1)).buffer(0))
    bustle = C._clean_polygon(P.intersection(C.rect_xy(x_split, miny - 1, maxx + 1, maxy + 1)).buffer(0))

    # ---- ground floor on the real footprint (IoU volume) ---------------------------------------------------------
    objs.append(C.plinth(f"{ID}_ground", P, 0.0, LOBBY_H, C.M.granite_dark, material_top=C.M.roof_dark))

    # ---- tower shaft: bronze I-beam curtain wall ------------------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=MODULE_M, window_frac=0.80, recess=0.18, spandrel_h=1.10,
                         spandrel_proud=0.16, mullions=0, pier="bronze", spandrel="bronze", glass="glass_dark")
    objs += C.tower_tier(f"{ID}_tower", tower, LOBBY_H, ROOF_M, fen, roof_material="roof_dark", parapet_h=1.1,
                         parapet_t=0.35)
    # the applied bronze I-beams: one per window module on every face, full height of the shaft
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(tower)):
        nmod = max(1, int(round(L / MODULE_M)))
        for k in range(nmod + 1):
            q0 = p0 + t * min(L, k * (L / nmod)) - t * 0.045
            q1 = q0 + t * 0.09
            b.box_from_to(q0, q1, n, 0.15, LOBBY_H, ROOF_M, C.M.bronze)          # web
            b.box_from_to(q0 - t * 0.055, q1 + t * 0.055, n, 0.04, LOBBY_H, ROOF_M, C.M.bronze)  # outer flange
    objs.append(b.build(f"{ID}_mullions"))

    # ---- rear bustle ----------------------------------------------------------------------------------------------
    bustle_top = LOBBY_H + (BUSTLE_FLOORS - 1) * FLOOR_H
    objs += C.tower_tier(f"{ID}_bustle", bustle, LOBBY_H, bustle_top, fen, roof_material="roof_dark", parapet_h=1.2,
                         parapet_t=0.4)

    # ---- ground floor: recessed lobby glass one bay behind the column line ----------------------------------------
    b = C.MeshBuilder()
    lobby = C.offset_polygon(tower, -BAY_M)
    if not lobby.is_empty:
        b.prism(C.ring_coords(lobby), 0.05, LOBBY_H - 0.35, C.M.glass_clear, cap_bottom=False, cap_top=False)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(tower)):
        nbay = max(1, int(round(L / BAY_M)))
        for k in range(nbay + 1):
            q = p0 + t * min(L, k * (L / nbay))
            b.box((q[0], q[1], LOBBY_H / 2), (0.75, 0.75, LOBBY_H), C.M.bronze, top=False, bottom=False)
    objs.append(b.build(f"{ID}_lobby"))

    # ---- plaza: 90 ft of pink granite with the two raised pools (west of the building line) -------------------------
    b = C.MeshBuilder()
    px0 = minx - PLAZA_D
    plaza = C.rect_xy(px0, miny, minx, maxy)
    b.prism(C.ring_coords(plaza), -0.02, 0.18, C.M.granite_pink)
    for cy in (-13.0, 13.0):                     # the two pools flank the central entrance walk
        pool = C.rect(px0 + 12.0, cy, 6.7, 12.0)
        b.prism(C.ring_coords(pool), 0.18, 0.95, C.M.granite_dark, cap_top=False)
        b.prism(C.ring_coords(C.offset_polygon(pool, -0.4)), 0.18, 0.80, C.M.water_dark)
        b.prism(C.ring_coords(pool), 0.95, 0.95, C.M.granite_dark, cap_bottom=False,
                holes=[C.ring_coords(C.offset_polygon(pool, -0.4))])
    for k in range(6):                            # the four flagpoles / lamp standards along the plaza edge
        b.lathe([(0.09, 0.0), (0.07, 7.0)], 8, C.M.bronze, origin=(px0 + 1.6, -25.0 + k * 10.0, 0.18))
    objs.append(C.tag(b.build(f"{ID}_plaza"), "plaza"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint, 157.0 m / 38 storeys (CTBUH, LP-1664), 24 ft lobby, 28 ft "
                          "structural bay with three 9 ft 4 in window modules, applied bronze I-beam mullions, "
                          "90 ft granite plaza with two raised pools. Inferred (stated): tower/bustle split measured "
                          "off the footprint polygon; bustle 10 storeys from Lambert, *Building Seagram*. Not "
                          "modelled: travertine lobby and Four Seasons interiors, rooftop cooling towers, bronze "
                          "door hardware, sunken service courts."),
                      dimensions={"roof_m": ROOF_M, "floors": 38, "lobby_h_m": LOBBY_H, "floor_h_m": round(FLOOR_H, 3),
                                  "structural_bay_m": BAY_M, "window_module_m": round(MODULE_M, 3),
                                  "plaza_depth_m": PLAZA_D, "bustle_floors": BUSTLE_FLOORS,
                                  "bustle_top_m": round(LOBBY_H + (BUSTLE_FLOORS - 1) * FLOOR_H, 2)},
                      notes="Plaza geometry is tagged role='plaza' and lies outside the footprint, so it is excluded from the IoU base volume.")
    cc.render(ID, [
        {"view": "plaza", "azimuth_deg": 285, "elevation_deg": "street", "distance": 70, "fov_deg": 62, "look_up_deg": 40},
        {"view": "aerial", "azimuth_deg": 300, "elevation_deg": 24},
    ])
    return entry


if __name__ == "__main__":
    main()
