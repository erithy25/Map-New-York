"""Lipstick Building — 885 Third Avenue (BIN 1038549). Philip Johnson and John Burgee, 1986.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (1,372 m2), a 30.2 x 58.1 m ellipse (61 vertices) — the plan is measured off the
  polygon, which is why the model's base is the ellipse itself rather than an idealised one.
* Height [CTBUH]: 453 ft = 138.0 m, 34 floors. Storeys derived to land the roof on 138.0 m: ground floor 6.00 m,
  33 floors of 4.00 m.
* Three telescoping elliptical tiers [Johnson/Burgee; AIA Guide to New York City]. The two setback levels are read
  from photographs as floors 20 and 29 (z = 82.0 m and 118.0 m) with a ~3 m inset each — flagged inferred, +-1 floor.
* Elevation [AIA Guide; Johnson/Burgee]: continuous horizontal bands — polished red Imperial granite piers and
  stainless-steel spandrels alternating with ribbon glazing; each floor band is 4.00 m with a 1.60 m glass ribbon.
* Ground floor [AIA Guide]: the shaft is lifted on a ring of columns over a recessed glazed lobby, so the ellipse
  oversails the ground floor by ~2.4 m.

Fidelity: real elliptical footprint, published height and floor count, three-tier telescoping massing, banded
granite/stainless/glass elevation and the lifted colonnaded ground floor modelled as geometry. Inferred (stated):
the two setback floors and their insets (from photographs, +-1 floor). NOT modelled: the lobby interior, the rooftop
mechanical enclosure's louvres, and the 3rd Avenue sidewalk canopy.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_lipstick_building"
BIN = 1038549
ROOF_M = 138.0
GROUND_H = 6.0
FLOOR_H = 4.0
SETBACK_FLOORS = (20, 29)
INSET_M = 3.0


def build():
    C.reset()
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    objs: list = []
    z1 = GROUND_H + (SETBACK_FLOORS[0] - 1) * FLOOR_H
    z2 = GROUND_H + (SETBACK_FLOORS[1] - 1) * FLOOR_H
    t2 = C.offset_polygon(P, -INSET_M)
    t3 = C.offset_polygon(t2, -INSET_M)

    # ---- ground floor: recessed glass lobby behind the perimeter columns (base volume for the IoU test) ----------
    objs.append(C.plinth(f"{ID}_ground", P, 0.0, GROUND_H, C.M.glass_clear, material_top=C.M.granite_dark))
    b = C.MeshBuilder()
    ring = C.ring_coords(P)
    b.prism(C.ring_coords(C.offset_polygon(P, -2.4)), 0.05, GROUND_H - 0.4, C.M.glass_clear, cap_bottom=False, cap_top=False)
    for i in range(0, len(ring), 3):
        x, y = ring[i]
        b.lathe([(0.55, 0.0), (0.55, GROUND_H)], 12, C.M.granite_pink, origin=(x, y, 0.0))
    objs.append(b.build(f"{ID}_colonnade"))

    # ---- the three telescoping elliptical tiers ------------------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=2.4, window_frac=1.0, recess=0.30, spandrel_h=2.40,
                         spandrel_proud=0.30, pier="granite_pink", spandrel="granite_pink", glass="glass_dark")
    for name, poly, za, zb in ((f"{ID}_t1", P, GROUND_H, z1), (f"{ID}_t2", t2, z1, z2), (f"{ID}_t3", t3, z2, ROOF_M)):
        objs += C.tower_tier(name, poly, za, zb, fen, roof_material="roof_dark", parapet_h=0.0)
        # stainless band at every floor line (the polished spandrel that reads as a stripe)
        bb = C.MeshBuilder()
        z = za
        while z < zb - 0.3:
            bb.prism(C.ring_coords(poly), z + FLOOR_H - 1.05, z + FLOOR_H - 0.35, C.M.steel_chrome,
                     holes=[C.ring_coords(C.offset_polygon(poly, -0.34))], cap_top=False, cap_bottom=False)
            z += FLOOR_H
        objs.append(bb.build(f"{name}_bands"))
    objs.append(C.prism(f"{ID}_mech", C.offset_polygon(t3, -3.0), ROOF_M - 3.6, ROOF_M, C.M.steel_chrome,
                        material_top=C.M.roof_dark, role="mass"))
    return objs, g, P, (z1, z2)


def main():
    objs, g, P, (z1, z2) = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real elliptical OTI footprint, 138.0 m / 34 floors (CTBUH), three telescoping "
                          "elliptical tiers, banded red-granite / stainless / ribbon-glass elevation, lifted "
                          "colonnaded ground floor. Inferred (stated, +-1 floor): the setback floors (20 and 29) and "
                          "their 3 m insets, read from photographs. Not modelled: lobby interior, rooftop louvres, "
                          "Third Avenue canopy."),
                      dimensions={"roof_m": ROOF_M, "floors": 34, "ground_h_m": GROUND_H, "floor_h_m": FLOOR_H,
                                  "setback_floors": list(SETBACK_FLOORS), "setback_z_m": [round(z1, 2), round(z2, 2)],
                                  "tier_inset_m": INSET_M,
                                  "ellipse_axes_m": [round(P.bounds[2] - P.bounds[0], 2), round(P.bounds[3] - P.bounds[1], 2)]})
    cc.render(ID, [
        {"view": "third_ave", "azimuth_deg": 100, "elevation_deg": "street", "distance": 60, "fov_deg": 62, "look_up_deg": 45},
        {"view": "aerial", "azimuth_deg": 120, "elevation_deg": 25},
    ])
    return entry


if __name__ == "__main__":
    main()
