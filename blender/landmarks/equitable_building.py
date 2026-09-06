"""Equitable Building — 120 Broadway (BIN 1001026, LP-0989). Ernest R. Graham (Graham, Anderson, Probst & White), 1915.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 3,734.1 m2 — the block bounded by Broadway, Cedar, Nassau and Pine Streets; 96.2 x 49.2 m
  in the model's local frame. The polygon carries the two light courts of the H plan.
* Heights [Emporis, Wikipedia "Equitable Building (Manhattan)", LPC LP-0989]: 540 ft = 164.6 m to the top of the
  cornice; 38 storeys. Storey heights derived from those fixed points: ground floor 8.0 m, floors 2-38 at
  (164.6 - 2.6 - 8.0)/37 = 4.17 m, plus a 2.6 m crowning cornice.
* Massing [LPC LP-0989, Wikipedia]: the building is notorious for rising *sheer from the lot line for its whole height* —
  it cast a seven-acre shadow and directly caused the 1916 Zoning Resolution. Its plan is an H: two 38-storey slabs
  joined by a central section, with light courts east and west. There are no setbacks: the only modelled steps are the
  three-storey rusticated base and the crowning cornice.
* Materials [LPC LP-0989]: granite at the first three storeys, buff limestone and matching terracotta above, with
  paired one-over-one windows in a strict grid and a heavy modillioned cornice.

Fidelity: exact — real footprint including both light courts, 164.6 m cornice height, 38 storeys, the sheer lot-line
rise with no setbacks (the whole point of the building), the three-storey rusticated base, the strict paired-window grid
and the heavy crowning cornice. Inferred — per-storey heights, derived from the published overall height and storey
count. Simplified — the terracotta ornament is carried as string courses, a modillioned cornice and spandrel panels
rather than modelled relief. Not modelled — the barrel-vaulted lobby arcade through the building, and the roof plant.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "equitable_building"
BINS = [1001026]
CORNICE_TOP_M = 164.6
CORNICE_H = 2.6
GROUND_H = 8.0
FLOOR_H = (CORNICE_TOP_M - CORNICE_H - GROUND_H) / 37.0


def fz(k: int) -> float:
    return 0.0 if k <= 0 else GROUND_H + (k - 1) * FLOOR_H


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    objs = []
    gran, lime, glass = C.M.granite_rusticated, C.M.limestone, C.M.glass_dark
    z3, ztop = fz(3), CORNICE_TOP_M - CORNICE_H

    # ---- rusticated granite base, storeys 1-3, on the real footprint --------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, GROUND_H, gran, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 8:
            continue
        k = max(1, int(round(L / 4.8)))
        for i in range(k):
            a = p0 + t * (L * i / k + 0.9); c = p0 + t * (L * (i + 1) / k - 0.9)
            C.arched_opening(b, a, c, n, 0.9, GROUND_H - 3.0, None, 0.8, gran, C.M.glass_clear, n=10)
    runs = sorted(C.wall_runs(coords, 0.0, tol_deg=55.0), key=lambda r: -r[1])
    if runs:                                       # the Broadway entrance arcade
        pts, L = runs[0]
        for f in (-1, 0, 1):
            a, t, n = C.polyline_at(pts, L / 2 + f * 6.5 - 2.4)
            c, t2, n2 = C.polyline_at(pts, L / 2 + f * 6.5 + 2.4)
            C.arched_opening(b, a, c, n, 0.0, 6.2, None, 1.9, gran, glass, n=12)
    objs.append(b.build(f"{ID}_base_detail"))
    fen_base = C.Fenestration(floor_h=FLOOR_H, bay_w=4.3, window_frac=0.5, recess=0.5, spandrel_h=1.15,
                              pier="granite_rusticated", spandrel="granite_rusticated", glass="glass_dark",
                              floor_z=[fz(k) for k in range(1, 4)], window_h=2.9)
    objs += C.tower_tier(f"{ID}_t0", P, GROUND_H, z3, fen_base, parapet_h=0.0)
    objs.append(C.band(f"{ID}_belt3", P, z3, z3 + 0.7, 0.45, lime))

    # ---- the sheer limestone shaft, storeys 4-38 (no setbacks — the 1916 zoning building) -----------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=4.3, window_frac=0.62, recess=0.42, spandrel_h=1.05, mullions=1,
                         pier="limestone", spandrel="limestone", glass="glass_dark", mullion="limestone",
                         floor_z=[fz(k) for k in range(3, 39)], window_h=2.7)
    objs += C.tower_tier(f"{ID}_shaft", P, z3, ztop, fen, parapet_h=0.0)
    objs.append(C.band(f"{ID}_belt34", P, fz(34), fz(34) + 0.6, 0.35, lime))

    # ---- crowning cornice --------------------------------------------------------------------------------------
    objs.append(C.cornice(f"{ID}_cornice", P, ztop, [(0.4, 0.0), (1.7, 1.0), (2.0, 1.7), (1.7, CORNICE_H - 0.4),
                                                     (0.6, CORNICE_H)], lime))
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):
        k = max(2, int(round(L / 1.7)))
        for i in range(k):
            q = p0 + t * (L * (i + 0.5) / k)
            b.box((float(q[0] + n[0] * 1.0), float(q[1] + n[1] * 1.0), ztop + 0.65), (1.0, 0.36, 0.9), lime,
                  rot_deg=math.degrees(math.atan2(t[1], t[0])))
    objs.append(b.build(f"{ID}_modillions"))
    objs.append(C.prism(f"{ID}_roof", P, ztop - 0.4, ztop + 0.5, C.M.roof_dark, inset=1.0))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=CORNICE_TOP_M, name="Equitable Building", lp_number="LP-00989",
             height_source="Emporis/Wikipedia/LPC LP-0989: 540 ft = 164.6 m to the top of the cornice, 38 storeys",
             fidelity_statement=(
                 "Exact: real footprint including both light courts of the H plan, 164.6 m cornice height, 38 storeys, the "
                 "sheer lot-line rise with no setbacks (the massing that produced the 1916 Zoning Resolution), the "
                 "three-storey rusticated granite base with its arcaded Broadway entrance, the strict paired-window grid "
                 "and the heavy modillioned cornice. Inferred: per-storey heights, derived from the published overall "
                 "height and storey count. Simplified: terracotta ornament is carried as string courses, modillions and "
                 "spandrel panels rather than modelled relief. Not modelled: the lobby arcade through the building."),
             notes="No setbacks by design — the model's silhouette is the real one",
             dimensions={"cornice_top_m": CORNICE_TOP_M, "cornice_h_m": CORNICE_H, "storeys": 38,
                         "ground_floor_h_m": GROUND_H, "floor_h_m": round(FLOOR_H, 3), "setbacks": 0,
                         "lot_m": [96.2, 49.2]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 200, "elevation_deg": "street", "distance": 165, "target_z": 62, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 215, "elevation_deg": 24, "distance": 560, "fov_deg": 42, "target_z": 88},
    ])


if __name__ == "__main__":
    main()
