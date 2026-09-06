"""Manhattan Municipal Building (David N. Dinkins Municipal Building) — 1 Centre Street (BIN 1001394, LP-00079).
McKim, Mead & White (William M. Kendall), 1914.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 4,360.0 m2, 118.6 x 54.2 m in the model's local frame — the C-shaped plan whose arms
  embrace the head of Chambers Street.
* Heights [Emporis, Wikipedia "Manhattan Municipal Building", LPC LP-0079]: 581 ft = 177.1 m to the top of Adolph
  Weinman's gilded copper *Civic Fame*, which is itself 25 ft (7.6 m) tall — the largest statue in Manhattan after the
  Statue of Liberty; 40 storeys; the main block is 25 storeys. Storey heights derived: ground floor 8.5 m, floors
  2-25 at 4.0 m, so the main-block roof lands at 104.5 m.
* Massing [LPC LP-0079, Wikipedia]: a three-storey rusticated granite base pierced by a triumphal central arch over
  the (former) course of Chambers Street, flanked by a screen of free-standing Corinthian columns; a C-shaped
  25-storey block; then a square tower that rises through a colonnaded tempietto and a sequence of diminishing
  colonnaded tiers to the statue. The tower stages used here (shaft to 132 m, tempietto 132-149 m, upper tiers to
  169.5 m, statue 169.5-177.1 m) reproduce the published silhouette; their exact levels are inferred (+-3 m).
* Materials [LPC LP-0079]: Maine granite at the base, buff brick and terracotta above, gilded copper for Civic Fame,
  Guastavino tile in the vault of the arch (not modelled).

Fidelity: exact — real C-shaped footprint, 177.1 m to the top of Civic Fame, the 7.6 m statue, 40 storeys, the
three-storey rusticated base with its central triumphal arch and free-standing Corinthian colonnade, and the wedding-cake
tower of diminishing colonnaded tiers. Inferred (+-3 m) — the tower stage levels and the plan of each stage.
Simplified — Civic Fame is a gilded massing figure, not a modelled sculpture; the colonnades use the shared Corinthian
lathe profile; the sculptural panels by Weinman on the base are omitted. Not modelled — the Guastavino vault of the
arch, the subway entrance and all interiors.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "municipal_building"
BINS = [1001394]
TOP_M = 177.1
STATUE_H = 7.6
BASE_H = 8.5
FLOOR_H = 4.0
BLOCK_TOP_M = BASE_H + 24 * FLOOR_H          # 104.5 m, the 25-storey C-block roof
SHAFT_TOP_M = 132.0
TEMPIETTO_TOP_M = 149.0
TIERS_TOP_M = TOP_M - STATUE_H               # 169.5 m


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    cx, cy = P.centroid.x, P.centroid.y
    south = fr.local_cardinal(180.0)
    objs = []
    gran, tc, gold = C.M.granite_rusticated, C.M.terracotta_cream, C.M.gold
    glass = C.M.glass_dark

    # ---- rusticated granite base, storeys 1-3, on the real footprint --------------------------------------------
    z3 = BASE_H + 2 * FLOOR_H
    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_H, gran, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for q, t, n, s in C.ring_stations(coords, 6.0):
        C.arched_opening(b, q - t * 1.9, q + t * 1.9, n, 1.1, 5.2, None, 1.0, gran, glass, n=10)
    # the free-standing Corinthian colonnade screen and the triumphal arch on the Chambers Street front
    runs = sorted(C.wall_runs(coords, south, tol_deg=50.0), key=lambda r: -r[1])
    pts, Lf = runs[0]
    mid, mt, mn = C.polyline_at(pts, Lf / 2)
    C.arched_opening(b, mid - mt * 6.5, mid + mt * 6.5, mn, 0.0, 8.0, None, 3.2, gran, C.M.granite_dark, n=16)
    ncol = max(4, int((Lf - 20.0) // 5.0))
    C.colonnade(b, pts[0], pts[-1], mn, BASE_H, 13.0, 0.85, ncol, tc, order="corinthian", stand_off=2.6, segments=14)
    C.entablature(b, mid - mt * (Lf / 2 - 2.0), mid + mt * (Lf / 2 - 2.0), mn, BASE_H + 13.0, 3.2, 3.0, tc, overhang=0.6)
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(C.prism(f"{ID}_base_mass", P, BASE_H, z3, gran, inset=0.5, material_top=C.M.roof_grey, role="mass"))

    # ---- the C-shaped block, storeys 4-25 ----------------------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=3.4, window_frac=0.52, recess=0.45, spandrel_h=1.0,
                         pier="brick_buff", spandrel="terracotta_cream", glass="glass_dark", window_h=2.6)
    objs += C.tower_tier(f"{ID}_block", P, z3, BLOCK_TOP_M, fen, parapet_h=1.5, parapet_t=0.55)
    objs.append(C.cornice(f"{ID}_block_cornice", P, BLOCK_TOP_M, [(0.4, 0.0), (1.5, 1.0), (1.8, 1.7), (0.6, 2.4)], tc))

    # ---- the tower: shaft, tempietto and the diminishing colonnaded tiers ---------------------------------------
    tw = 26.0
    tower = C.rect(cx, cy, tw, tw).intersection(P.buffer(1.0))
    tower = C._orient((tower if tower.geom_type == "Polygon" else max(tower.geoms, key=lambda g: g.area)).buffer(0), 1.0)
    objs += C.tower_tier(f"{ID}_shaft", tower, BLOCK_TOP_M, SHAFT_TOP_M, fen, parapet_h=0.0)
    b = C.MeshBuilder()
    # tempietto: a colonnaded drum on the shaft
    r1 = tw * 0.42
    b.prism(C.ring_coords(C.regular_polygon(cx, cy, r1, 16)), SHAFT_TOP_M, SHAFT_TOP_M + 1.2, tc)
    for k in range(16):
        a = 2 * math.pi * k / 16
        C.column(b, cx + r1 * math.cos(a), cy + r1 * math.sin(a), SHAFT_TOP_M + 1.2, 11.0, 0.7, tc,
                 order="corinthian", segments=12, abacus=False)
    b.prism(C.ring_coords(C.regular_polygon(cx, cy, r1 + 0.9, 16)), SHAFT_TOP_M + 12.2, TEMPIETTO_TOP_M, tc)
    b.prism(C.ring_coords(C.regular_polygon(cx, cy, r1 * 0.72, 16)), SHAFT_TOP_M + 1.2, SHAFT_TOP_M + 12.2, tc)
    # two diminishing colonnaded tiers above it
    z = TEMPIETTO_TOP_M
    for tier, (rr, hh, nc) in enumerate(((r1 * 0.78, 9.0, 12), (r1 * 0.52, 7.5, 10))):
        b.prism(C.ring_coords(C.regular_polygon(cx, cy, rr + 0.8, nc)), z, z + 1.0, tc)
        for k in range(nc):
            a = 2 * math.pi * k / nc
            C.column(b, cx + rr * math.cos(a), cy + rr * math.sin(a), z + 1.0, hh - 2.2, 0.55, tc,
                     order="corinthian", segments=10, abacus=False)
        b.prism(C.ring_coords(C.regular_polygon(cx, cy, rr * 0.62, nc)), z + 1.0, z + hh - 1.2, tc)
        b.prism(C.ring_coords(C.regular_polygon(cx, cy, rr + 1.0, nc)), z + hh - 1.2, z + hh, tc)
        z += hh
    C.dome(b, cx, cy, z, r1 * 0.42, TIERS_TOP_M - z, tc, kind="ogee", segments=20)
    # Civic Fame: 7.6 m gilded copper figure with an outstretched arm
    zs = TIERS_TOP_M
    b.hull([(cx - 1.1, cy - 1.1, zs), (cx + 1.1, cy - 1.1, zs), (cx + 1.1, cy + 1.1, zs), (cx - 1.1, cy + 1.1, zs),
            (cx - 0.7, cy - 0.7, zs + STATUE_H * 0.62), (cx + 0.7, cy - 0.7, zs + STATUE_H * 0.62),
            (cx + 0.7, cy + 0.7, zs + STATUE_H * 0.62), (cx - 0.7, cy + 0.7, zs + STATUE_H * 0.62),
            (cx - 0.3, cy, zs + STATUE_H * 0.9), (cx + 0.3, cy, zs + STATUE_H * 0.9),
            (cx, cy, zs + STATUE_H)], gold)
    b.box((cx + 1.4, cy, zs + STATUE_H * 0.78), (2.6, 0.28, 0.28), gold)
    objs.append(b.build(f"{ID}_tower"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TOP_M, name="Manhattan Municipal Building", lp_number="LP-00079",
             height_source="Emporis / Wikipedia / LPC LP-0079: 581 ft = 177.1 m to the top of Civic Fame; the statue is 25 ft = 7.6 m; 40 storeys",
             fidelity_statement=(
                 "Exact: real C-shaped footprint, 177.1 m to the top of Civic Fame, the 7.6 m gilded statue, 40 storeys "
                 "with a 25-storey main block, the three-storey rusticated granite base with its central triumphal arch "
                 "and free-standing Corinthian colonnade, and the wedding-cake tower of a colonnaded tempietto and two "
                 "diminishing colonnaded tiers under an ogee cupola. Inferred (+-3 m): the tower stage levels (shaft to "
                 "132 m, tempietto to 149 m, tiers to 169.5 m) and the plan of each stage. Simplified: Civic Fame is a "
                 "gilded massing figure with an outstretched arm, not a modelled sculpture; the colonnades use the shared "
                 "Corinthian lathe profile; Weinman's relief panels on the base are omitted. Not modelled: the Guastavino "
                 "vault of the arch, the subway entrance and all interiors."),
             notes="Storey heights derived from the published 25-storey block and 40-storey total",
             dimensions={"top_m": TOP_M, "statue_h_m": STATUE_H, "block_top_m": BLOCK_TOP_M, "shaft_top_m": SHAFT_TOP_M,
                         "tempietto_top_m": TEMPIETTO_TOP_M, "tiers_top_m": TIERS_TOP_M, "storeys": 40,
                         "ground_floor_h_m": BASE_H, "floor_h_m": FLOOR_H, "tower_plan_m": 26.0,
                         "tempietto_columns": 16})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 190, "elevation_deg": "street", "distance": 270, "target_z": 75, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 205, "elevation_deg": 24, "distance": 600, "fov_deg": 40, "target_z": 95},
    ])


if __name__ == "__main__":
    main()
