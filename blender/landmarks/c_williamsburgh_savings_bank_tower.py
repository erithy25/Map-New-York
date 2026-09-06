"""Williamsburgh Savings Bank Tower (One Hanson Place) — 1 Hanson Place, Brooklyn (BIN 3059183, LP-0973 exterior
and LP-1359 interior). Halsey, McCormack & Helmer, 1927-29.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (1,658 m2), 34.8 x 62.3 m at the junction of Hanson Place, Ashland Place and
  Flatbush Avenue Extension.
* Height [CTBUH; LPC designation report LP-0973]: **512 ft = 156.0 m**, 37 floors — the tallest building in
  Brooklyn until 2009. The OTI LiDAR height is 157.6 m, consistent to 1.0 %.
* Massing [LP-0973]: a four-storey banking-hall base, a shaft with setbacks at the 5th, 25th and 30th floors, a
  clock storey and a gilded dome with a lantern.
* Clock [LP-0973; Seth Thomas]: **four clock faces 27 ft = 8.2 m in diameter**, the largest four-sided clock in the
  world, set in the tower's four faces just below the dome.
* Elevation [LP-0973]: Ohio sandstone and buff brick with a limestone base and Byzantine-Romanesque terracotta
  ornament; the banking hall's arched windows are 12.0 m high.
* Storey heights derived so the clock storey lands at 128.0 m and the dome base at 138.0 m: base 22.0 m for four
  storeys, then 30 floors of 3.53 m.

Fidelity: real footprint; the 156.0 m height, the setback sequence, the four 8.2 m clock faces, the gilded dome and
lantern, the banking hall's 12.0 m arched windows and the brick-and-terracotta shaft are modelled as geometry.
Inferred (stated): the setback offsets and storey heights (derived from the published total, floor count and the
LiDAR height); the terracotta ornament is modelled as plain band courses. NOT modelled: the banking hall interior
(a separate interior landmark), the mosaic vault, and the clock movement.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_williamsburgh_savings_bank_tower"
BIN = 3059183
TOP = 156.0
BASE_TOP = 22.0
CLOCK_Z, CLOCK_D = 128.0, 8.2
DOME_BASE = 138.0


def build():
    C.reset()
    cc.materials(["brick_buff", "limestone", "terracotta_cream", "gold", "copper_green", "glass_dark", "roof_dark",
                  "granite_dark", "bronze", "marble_white"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    objs += cc.base_and_wall(f"{ID}_base", P, BASE_TOP, C.M.limestone, recess=0.9, material_top=C.M.roof_dark)
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):          # the banking hall's giant arched windows
        if L < 10.0:
            continue
        nbay = max(1, int(round(L / 8.5)))
        mod = L / nbay
        for k in range(nbay):
            a = p0 + t * (k * mod + 1.6)
            c = p0 + t * ((k + 1) * mod - 1.6)
            C.arched_opening(b, a, c, n, 4.0, 16.0, None, 0.85, C.M.limestone, C.M.glass_dark)
        b.box_from_to(p0, p1, n, 0.5, BASE_TOP - 1.6, BASE_TOP, C.M.terracotta_cream)
    objs.append(b.build(f"{ID}_banking_hall"))

    # ---- the shaft with its setbacks -------------------------------------------------------------------------------
    fen = C.Fenestration(floor_h=3.53, bay_w=3.1, window_frac=0.5, recess=0.45, spandrel_h=0.95, spandrel_proud=0.12,
                         pier="brick_buff", spandrel="brick_buff", glass="glass_dark", window_h=2.3)
    tiers = [(BASE_TOP, 92.0, -1.4), (92.0, 110.0, -3.6), (110.0, CLOCK_Z - 3.0, -5.8)]
    last = None
    for i, (za, zb, off) in enumerate(tiers):
        poly = C.offset_polygon(P, off)
        objs += C.tower_tier(f"{ID}_shaft{i}", poly, za, zb, fen, roof_material="roof_dark", parapet_h=1.2,
                             parapet_t=0.5)
        objs.append(C.cornice(f"{ID}_band{i}", poly, zb - 1.8, [(0.35, 0.0), (1.0, 0.9), (1.0, 1.4), (0.4, 1.8)],
                              C.M.terracotta_cream))
        last = poly
    # ---- the clock storey with its four 8.2 m faces -----------------------------------------------------------------
    clock = C.offset_polygon(P, -6.6)
    objs.append(C.prism(f"{ID}_clock_storey", clock, CLOCK_Z - 3.0, DOME_BASE, C.M.limestone,
                        material_top=C.M.roof_dark, role="mass"))
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(clock)):
        mid = (p0 + p1) / 2
        ang = math.degrees(math.atan2(t[1], t[0]))
        b.lathe([(0.0, 0.0), (CLOCK_D / 2, 0.0), (CLOCK_D / 2, 0.35), (0.0, 0.35)], 32, C.M.marble_white,
                origin=(mid[0] + n[0] * 0.3, mid[1] + n[1] * 0.3, CLOCK_Z))
        for k in range(12):                              # the twelve hour marks
            a = 2 * math.pi * k / 12
            q = (mid[0] + n[0] * 0.5 + t[0] * (CLOCK_D / 2 - 0.7) * math.cos(a),
                 mid[1] + n[1] * 0.5 + t[1] * (CLOCK_D / 2 - 0.7) * math.cos(a))
            b.box((q[0], q[1], CLOCK_Z + (CLOCK_D / 2 - 0.7) * math.sin(a)), (0.55, 0.3, 0.55), C.M.gold,
                  rot_deg=ang)
        for hl, ha in ((CLOCK_D / 2 - 1.4, 1.0), (CLOCK_D / 2 - 2.4, 2.4)):     # the hands
            q = (mid[0] + n[0] * 0.55 + t[0] * hl * math.cos(ha) / 2,
                 mid[1] + n[1] * 0.55 + t[1] * hl * math.cos(ha) / 2)
            b.box((q[0], q[1], CLOCK_Z + hl * math.sin(ha) / 2), (hl, 0.22, 0.3), C.M.bronze,
                  rot_deg=ang)
    objs.append(b.build(f"{ID}_clock"))

    # ---- the gilded dome and lantern --------------------------------------------------------------------------------
    b = C.MeshBuilder()
    ccx, ccy = clock.centroid.x, clock.centroid.y
    r = min(clock.bounds[2] - clock.bounds[0], clock.bounds[3] - clock.bounds[1]) / 2
    prof = [(r * math.cos(math.pi / 2 * k / 10), (TOP - 9.0 - DOME_BASE) * math.sin(math.pi / 2 * k / 10))
            for k in range(11)]
    b.lathe(prof, 32, C.M.gold, origin=(ccx, ccy, DOME_BASE), smooth=True)
    b.lathe([(1.9, 0.0), (1.9, 4.0), (1.4, 4.6), (0.9, 6.0), (0.0, 9.0)], 16, C.M.gold,
            origin=(ccx, ccy, TOP - 9.0), smooth=True)
    objs.append(C.tag(b.build(f"{ID}_dome"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; 512 ft = 156.0 m over 37 floors (CTBUH, LP-0973; LiDAR "
                          "157.6 m, 1.0 % agreement); the setback sequence; the four 27 ft = 8.2 m clock faces with "
                          "hour marks and hands on all four elevations; the gilded dome and lantern; the banking "
                          "hall's 12 m arched windows. Inferred (stated): the setback offsets and storey heights "
                          "(derived from the published total, floor count and the LiDAR height); the "
                          "Byzantine-Romanesque terracotta ornament is modelled as plain band courses. Not "
                          "modelled: the landmarked banking-hall interior, the mosaic vault, the clock movement."),
                      dimensions={"top_m": TOP, "floors": 37, "base_top_m": BASE_TOP, "clock_centre_z_m": CLOCK_Z,
                                  "clock_face_d_m": CLOCK_D, "dome_base_m": DOME_BASE})
    cc.render(ID, [
        {"view": "hanson_place", "azimuth_deg": 200, "elevation_deg": "street", "distance": 260, "fov_deg": 45, "look_up_deg": 33},
        {"view": "aerial", "azimuth_deg": 220, "elevation_deg": 26},
    ])
    return entry


if __name__ == "__main__":
    main()
