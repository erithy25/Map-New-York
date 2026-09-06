"""One Vanderbilt — 1 Vanderbilt Avenue (BIN 1090825). Kohn Pedersen Fox for SL Green, completed 2020.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 4,024.0 m2 — the full block bounded by Madison Avenue, Vanderbilt Avenue, East 42nd and
  East 43rd Streets; 65.7 x 61.2 m in the model's local frame.
* Heights [CTBUH, SL Green, Wikipedia "One Vanderbilt"]: architectural height (spire tip) 427.0 m (1,401 ft); roof /
  top of the occupied structure 396.2 m (1,301 ft); 93 storeys; the SUMMIT observatory occupies floors 91-93 at
  325-335 m. The LiDAR roof height for this BIN is 427.03 m, which agrees with the published tip height to 0.03 m.
* Massing [KPF project description, Wikipedia]: four interlocking tapering volumes, each terminating in an angled
  chisel cut; the tower steps back on all four sides at roughly one-quarter height intervals; the south-east corner is
  cut away at the base to open a 30 m high glazed corner onto the Grand Central Terminal viaduct, and the four
  terracotta-clad "spines" run the full height of the tower. Setback levels below are placed at the quarter points of
  the 396.2 m shaft (99.1 / 198.1 / 297.2 m) — the published drawings give the sequence but not the exact levels, so
  those three heights are inferred (+-8 %).
* Materials [KPF]: hand-laid terracotta piers with bronze-toned metal reveals, floor-to-ceiling low-iron glass curtain
  wall, angled glass at the chisel cuts.

Fidelity: exact — real footprint, 427.0 m tip, 396.2 m roof, 93 storeys, the four-volume tapering massing with angled
chisel tops, the cut-away glazed south-east corner facing Grand Central, terracotta-pier / glass curtain-wall material
split. Inferred (+-8 %) — the three intermediate setback levels and the plan of each tapering volume. Simplified — the
terracotta piers are modelled as a repeating pier/reveal rhythm rather than individually laid units; the crown mast is a
plain tapered spire. Not modelled — the SUMMIT observatory interior, the transit hall, the sloping public plaza paving.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "one_vanderbilt"
BINS = [1090825]
TIP_M = 427.0
ROOF_M = 396.2
BASE_H = 30.0                      # glazed corner / lobby volume
FLOOR_H = 4.15                     # office floor-to-floor (SL Green leasing plans)
SETBACKS = (99.1, 198.1, 297.2)    # quarter points of the shaft (inferred, see docstring)


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    cx, cy = P.centroid.x, P.centroid.y
    objs = []
    tc, glass, bronze = C.M.terracotta_cream, C.M.glass_blue, C.M.bronze

    # ---- base: the real footprint with the south-east corner cut away for the glazed corner ---------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, 2.0, tc, material_top=C.M.pavement))
    cut = C.rect_xy(maxx - 22.0, miny - 2.0, maxx + 2.0, miny + 20.0)     # the corner facing Grand Central
    base_solid = P.difference(cut)
    objs.append(C.prism(f"{ID}_base_mass", base_solid, 2.0, BASE_H, tc, inset=0.5, material_top=C.M.roof_grey, role="mass"))
    fen_base = C.Fenestration(floor_h=6.0, bay_w=3.05, window_frac=0.72, recess=0.45, spandrel_h=0.55,
                              pier="terracotta_cream", spandrel="bronze", glass="glass_clear")
    objs.append(C.facade_grid(f"{ID}_base_skin", base_solid, 2.0, BASE_H, fen_base))
    # the cut corner: a full-height glazed screen behind a bronze frame
    b = C.MeshBuilder()
    ring_cut = C.ring_coords(P.intersection(cut)) if not P.intersection(cut).is_empty else []
    if ring_cut:
        b.prism(ring_cut, 0.0, 1.2, C.M.pavement)
        for p0, p1, L, t, n in C.edges_of(ring_cut):
            if L < 5:
                continue
            b.quad((p0[0], p0[1], 1.2), (p1[0], p1[1], 1.2), (p1[0], p1[1], BASE_H), (p0[0], p0[1], BASE_H), C.M.glass_clear)
            k = max(2, int(round(L / 3.05)))
            for i in range(k + 1):
                q = p0 + t * (L * i / k)
                b.box((float(q[0]), float(q[1]), (1.2 + BASE_H) / 2), (0.22, 0.5, BASE_H - 1.2), bronze,
                      rot_deg=math.degrees(math.atan2(t[1], t[0])))
    objs.append(b.build(f"{ID}_corner_glass"))
    objs.append(C.band(f"{ID}_base_cap", P, BASE_H, BASE_H + 1.1, 0.45, bronze))

    # ---- four tapering volumes: each steps back and is cut off by an angled chisel ------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=3.05, window_frac=0.7, recess=0.4, spandrel_h=0.85,
                         pier="terracotta_cream", spandrel="bronze", glass="glass_blue")
    # Each volume steps back from a *different* pair of sides, so the tower reads as four interlocking chisels rather
    # than a concentric wedding cake; the tall south-east corner (facing Grand Central) runs the full height.
    levels = [BASE_H, *SETBACKS, ROOF_M]
    keeps = [None,
             C.rect_xy(minx + 9.0, miny, maxx, maxy - 6.0),                       # step back from the west and north
             C.rect_xy(minx + 9.0, miny, maxx - 7.0, maxy - 15.0),                # again from the north, and the east
             C.rect_xy(minx + 20.0, miny + 8.0, maxx - 7.0, maxy - 15.0)]         # again from the west, and the south
    plan = P
    chisel_h = 12.0
    for k in range(4):
        z0, z1 = levels[k], levels[k + 1]
        if keeps[k] is not None:
            nxt = plan.intersection(keeps[k])
            if not nxt.is_empty:
                plan = C._orient((nxt if nxt.geom_type == "Polygon" else max(nxt.geoms, key=lambda g: g.area)).buffer(0), 1.0)
        objs += C.tower_tier(f"{ID}_v{k}", plan, z0, z1 - chisel_h, fen, parapet_h=0.0, roof_material="roof_grey")
        # the angled chisel closing each volume: the plan is lifted from the low side to the high side over chisel_h
        ring = C.ring_coords(plan)
        u = (math.cos(math.radians(-60.0)), math.sin(math.radians(-60.0)))        # the cuts face SSE, towards 42nd Street
        s = [(x - cx) * u[0] + (y - cy) * u[1] for x, y in ring]
        lo, hi = min(s), max(s)
        b = C.MeshBuilder()
        top = [(x, y, z1 - chisel_h + chisel_h * (s[i] - lo) / max(hi - lo, 1e-6)) for i, (x, y) in enumerate(ring)]
        b.loft([[(x, y, z1 - chisel_h) for x, y in ring], top], glass, cap_bottom=False, cap_top=False)
        b.ngon(top, C.M.aluminium)
        for i in range(len(ring)):                                                # bronze reveal along the cut edge
            j = (i + 1) % len(ring)
            b.quad(top[i], top[j], (top[j][0], top[j][1], top[j][2] - 0.6), (top[i][0], top[i][1], top[i][2] - 0.6), bronze)
        objs.append(b.build(f"{ID}_chisel{k}"))
    # ---- crown mast 396.2 -> 427.0 m ---------------------------------------------------------------------------
    b = C.MeshBuilder()
    mx, my = plan.centroid.x, plan.centroid.y
    mast = TIP_M - (ROOF_M - 4.0)
    b.lathe([(2.6, 0.0), (2.2, 6.0), (1.5, 16.0), (0.8, mast - 3.0), (0.0, mast)], 12,
            C.M.aluminium, origin=(mx, my, ROOF_M - 4.0), smooth=True)
    objs.append(b.build(f"{ID}_mast"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TIP_M, name="One Vanderbilt",
             height_source="CTBUH / SL Green / Wikipedia: tip 427.0 m (1,401 ft), roof 396.2 m (1,301 ft), 93 storeys; LiDAR height_roof for BIN 1090825 is 427.03 m",
             fidelity_statement=(
                 "Exact: real full-block footprint, 427.0 m tip, 396.2 m roof, 93 storeys, the four-volume tapering massing "
                 "with an angled chisel top, the cut-away 30 m glazed south-east corner facing Grand Central Terminal, and "
                 "the terracotta-pier / low-iron-glass curtain-wall split. Inferred (+-8 %): the three intermediate setback "
                 "levels (placed at the quarter points of the shaft) and the plan of each tapering volume. Simplified: the "
                 "terracotta is a repeating pier/reveal rhythm, not individually laid units; the crown is a plain tapered "
                 "mast. Not modelled: the SUMMIT observatory interior, the transit hall and the sloping public plaza."),
             notes="Setback levels are inferred from published elevations; the tip height agrees with LiDAR to 0.03 m",
             dimensions={"tip_m": TIP_M, "roof_m": ROOF_M, "storeys": 93, "base_h_m": BASE_H, "floor_h_m": FLOOR_H,
                         "setbacks_m": list(SETBACKS), "lot_m": [65.7, 61.2], "chisel_h_m": 10.0})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 140, "elevation_deg": "street", "distance": 645, "target_z": 180, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 305, "elevation_deg": 22, "distance": 1150, "fov_deg": 40, "target_z": 210},
    ])


if __name__ == "__main__":
    main()
