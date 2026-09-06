"""Lever House — 390 Park Avenue (BIN 1035732, LP-1277). Skidmore, Owings & Merrill (Gordon Bunshaft), 1952.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (2,851 m2), an L covering the block front between East 53rd and 54th Streets on the
  west side of Park Avenue (Park Avenue is +x east in the local frame; the notch is the neighbouring lot at the
  south-west corner).
* Height [CTBUH; LPC designation report LP-1277]: 307 ft = 94.0 m, 24 storeys counting the two-storey podium and the
  mechanical penthouse. Storeys derived to land the roof on 94.0 m: open ground floor 4.60 m clear, second-floor
  podium slab top 9.00 m, then 21 tower floors of 3.86 m (= 90.06 m) and a 3.94 m mechanical penthouse.
* Tower slab [LPC LP-1277; SOM project data]: 21 storeys, 175 x 53 ft = 53.3 x 16.2 m in plan, broad faces east and
  west so the Park Avenue elevation is the wide one; it occupies about a quarter of the site. Its position on the
  site is taken from the footprint's full-depth western zone (stated inference).
* Podium [LPC LP-1277]: one-storey slab lifted on stainless-steel-clad columns over an open, publicly accessible
  ground-floor plaza with a planted court; the slab oversails the columns.
* Curtain wall [LPC LP-1277]: the first sealed all-glass curtain wall in New York — blue-green heat-resistant glass
  with stainless-steel mullions on a 4 ft 6 in = 1.372 m module and stainless spandrel panels at each floor line.

Fidelity: real footprint; published height, storey heights, slab plan, 1.372 m curtain-wall module and stainless/
blue-green glass modelled as geometry. Inferred (stated): the tower slab's exact position on the site. NOT modelled:
the roof-mounted window-washing gantry track, the ground-floor lobby interior, the 2001-03 restoration's replacement
glass tints, and the courtyard planting.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_lever_house"
BIN = 1035732
ROOF_M = 94.0
GROUND_CLEAR = 4.60
PODIUM_TOP = 9.00
FLOOR_H = 3.86
TOWER_FLOORS = 21
MODULE_M = 1.372          # 4 ft 6 in
SLAB_W, SLAB_D = 53.3, 16.2


def build():
    C.reset()
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    objs: list = []

    # ---- ground floor: open plaza under the podium, structure = the column grid + service core -------------------
    b = C.MeshBuilder()
    core = C.rect(14.0, 6.0, 14.0, 16.0)          # lift/stair core, east side, glazed
    b.prism(C.ring_coords(core), 0.0, GROUND_CLEAR, C.M.granite_dark)
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        ncol = max(1, int(round(L / 8.5)))
        for k in range(ncol + 1):
            q = p0 + t * min(L, k * (L / ncol)) - n * 0.7
            b.lathe([(0.45, 0.0), (0.45, GROUND_CLEAR)], 12, C.M.aluminium, origin=(q[0], q[1], 0.0))
    for x in (-14.0, 0.0):                        # two interior column lines
        for y in (-18.0, 0.0, 18.0):
            b.lathe([(0.45, 0.0), (0.45, GROUND_CLEAR)], 12, C.M.aluminium, origin=(x, y, 0.0))
    b.prism(C.ring_coords(C.offset_polygon(P, -2.0)), 0.0, 0.12, C.M.granite_dark)   # plaza paving
    objs.append(C.tag(b.build(f"{ID}_ground"), "detail"))

    # ---- podium: the floating second-floor slab on the real footprint (IoU volume) -------------------------------
    fen_pod = C.Fenestration(bay_w=MODULE_M * 2, window_frac=0.86, recess=0.14, spandrel_h=0.75, spandrel_proud=0.10,
                             pier="aluminium", spandrel="aluminium", glass="glass_blue",
                             floor_z=[GROUND_CLEAR, PODIUM_TOP])
    objs.append(C.plinth(f"{ID}_podium", P, GROUND_CLEAR, PODIUM_TOP - 0.55, C.M.glass_blue))
    objs.append(C.facade_grid(f"{ID}_podium_skin", P, GROUND_CLEAR, PODIUM_TOP - 0.55, fen_pod))
    objs.append(C.cornice(f"{ID}_podium_fascia", P, PODIUM_TOP - 0.55, [(0.45, 0.0), (0.45, 0.55)], C.M.aluminium))
    # the podium slab is the base volume for the IoU test — it is flush with the real footprint
    objs.append(C.tag(C.prism(f"{ID}_base", P, 0.0, GROUND_CLEAR, C.M.glass_clear, inset=0.35), "base"))

    # ---- tower slab ----------------------------------------------------------------------------------------------
    slab = C.rect(-9.3, 0.4, SLAB_D, SLAB_W)      # 16.2 m east-west deep, 53.3 m north-south long
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=MODULE_M, window_frac=0.80, recess=0.12, spandrel_h=0.95,
                         spandrel_proud=0.09, pier="aluminium", spandrel="aluminium", glass="glass_blue")
    top = PODIUM_TOP + TOWER_FLOORS * FLOOR_H
    objs += C.tower_tier(f"{ID}_tower", slab, PODIUM_TOP, top, fen, roof_material="roof_grey", parapet_h=0.0)
    mech = C.offset_polygon(slab, -1.6)
    objs.append(C.prism(f"{ID}_penthouse", mech, top, ROOF_M, C.M.aluminium, material_top=C.M.roof_grey, role="mass"))
    objs.append(C.cornice(f"{ID}_tower_cap", slab, top - 0.2, [(0.3, 0.0), (0.3, 0.2)], C.M.aluminium))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint, 94.0 m / 24 storeys (CTBUH, LP-1277), open ground-floor plaza "
                          "under a lifted one-storey podium slab, 53.3 x 16.2 m tower slab, 4 ft 6 in (1.372 m) "
                          "stainless curtain-wall module with blue-green glass. Inferred (stated): the tower slab's "
                          "position on the site, derived from the footprint's full-depth western zone. Not modelled: "
                          "the roof window-washing gantry, lobby interior, courtyard planting."),
                      dimensions={"roof_m": ROOF_M, "floors": 24, "tower_floors": TOWER_FLOORS,
                                  "ground_clear_m": GROUND_CLEAR, "podium_top_m": PODIUM_TOP, "floor_h_m": FLOOR_H,
                                  "slab_plan_m": [SLAB_W, SLAB_D], "curtain_module_m": MODULE_M})
    cc.render(ID, [
        {"view": "park_ave", "azimuth_deg": 119, "elevation_deg": "street", "distance": 150, "fov_deg": 50, "look_up_deg": 32},
        {"view": "aerial", "azimuth_deg": 130, "elevation_deg": 26},
    ])
    return entry


if __name__ == "__main__":
    main()
