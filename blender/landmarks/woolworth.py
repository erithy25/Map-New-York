"""Woolworth Building — 233 Broadway (BIN 1087167, LP-01273). Cass Gilbert, 1913.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 2,237.1 m2 — the Broadway / Park Place / Barclay Street lot, 58.7 x 43.9 m in the model's
  local frame.
* Heights [CTBUH, Emporis, Wikipedia "Woolworth Building", LPC LP-1273]: 792 ft = 241.4 m to the top of the finial;
  60 storeys; the observation deck on the 57th floor was at 730 ft = 222.5 m. Storey heights are derived from those two
  fixed points: ground floor 7.6 m, floors 2-57 at (222.5 - 7.6)/56 = 3.838 m.
* Massing [LPC LP-1273, Wikipedia "Architecture"]: a 30-storey U-shaped base filling the lot (with a light court open to
  the west), from which a 30-storey tower about 25 x 25 m rises on the Broadway front; the tower is set back at floor 30
  and again at floor 42 and 52, and is capped by a steep copper pyramidal roof with four corner tourelles, gabled
  dormers and a lantern with the finial at 241.4 m.
* Materials [LPC LP-1273]: limestone at the first three storeys, cream glazed architectural terracotta (Atlantic Terra
  Cotta) with Gothic mullions above, copper (now green) at the pyramidal roof and the tourelles.

Fidelity: exact — real footprint with the west light court, 241.4 m finial height, 60 storeys, the 57th-floor deck at
222.5 m, the base/tower division at floor 30, the copper pyramidal crown with four corner tourelles and a lantern, the
terracotta/limestone/copper material split, and the Gothic vertical-mullion rhythm. Inferred (+-2 floors) — the tower
setback levels at floors 42 and 52 and the tower's plan dimensions (about 25 x 25 m). Simplified — the Gothic ornament
(crockets, tracery, gargoyles, the pinnacles of the flying buttresses at the crown) is carried as mullion and pinnacle
geometry, not as modelled carving. Not modelled — the lobby with its mosaic vault and the caricature corbels.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "woolworth"
BINS = [1087167]
FINIAL_M = 241.4
DECK57_M = 222.5
GROUND_H = 7.6
FLOOR_H = (DECK57_M - GROUND_H) / 56.0        # 3.838 m


def fz(k: int) -> float:
    return 0.0 if k <= 0 else GROUND_H + (k - 1) * FLOOR_H


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    cy = (miny + maxy) / 2
    objs = []
    lime, tc, cop, glass = C.M.limestone, C.M.terracotta_cream, C.M.copper_green, C.M.glass_dark

    z3, z30, z42, z52, z57 = fz(3), fz(30), fz(42), fz(52), fz(57)

    # ---- limestone base, storeys 1-3, on the real footprint ----------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, GROUND_H, lime, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 8:
            continue
        k = max(1, int(round(L / 4.6)))
        for i in range(k):
            a = p0 + t * (L * i / k + 0.7); c = p0 + t * (L * (i + 1) / k - 0.7)
            C.arched_opening(b, a, c, n, 0.8, 4.4, None, 0.9, lime, C.M.glass_clear, pointed=True, n=8)
    # the Broadway entrance arch (the longest street wall)
    runs = sorted(C.wall_runs(coords, 0.0, tol_deg=60.0) + C.wall_runs(coords, 180.0, tol_deg=60.0),
                  key=lambda r: -r[1])
    if runs:
        pts, L = runs[0]
        a, t, n = C.polyline_at(pts, L / 2 - 6.0)
        c, t2, n2 = C.polyline_at(pts, L / 2 + 6.0)
        C.arched_opening(b, a, c, n, 0.0, 9.0, None, 2.4, lime, glass, pointed=True, n=12)
    objs.append(b.build(f"{ID}_base_detail"))
    fen_base = C.Fenestration(floor_h=FLOOR_H, bay_w=3.0, window_frac=0.55, recess=0.42, spandrel_h=1.0,
                              pier="limestone", spandrel="limestone", glass="glass_dark", floor_z=[fz(k) for k in range(1, 4)])
    objs += C.tower_tier(f"{ID}_t0", P, GROUND_H, z3, fen_base, parapet_h=0.0)

    # ---- terracotta shaft of the base block, storeys 4-30 ------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=3.0, window_frac=0.56, recess=0.5, spandrel_h=0.85, mullions=1,
                         pier="terracotta_cream", spandrel="terracotta_cream", glass="glass_dark", mullion="terracotta_cream")
    objs += C.tower_tier(f"{ID}_t1", P, z3, z30, fen, parapet_h=1.4, parapet_t=0.5)
    objs.append(C.cornice(f"{ID}_c30", P, z30, [(0.3, 0.0), (0.85, 0.7), (0.85, 1.1), (0.35, 1.5)], tc))

    # ---- the tower, storeys 30-57, on the Broadway (east) half of the lot --------------------------------------
    tw = 25.0
    tx = maxx - tw / 2 - 3.0
    tower = C.rect(tx, cy, tw, tw).intersection(P.buffer(0.6))
    tower = C._orient(tower.buffer(0) if tower.geom_type == "Polygon" else max(tower.geoms, key=lambda g: g.area).buffer(0), 1.0)
    objs += C.tower_tier(f"{ID}_t2", tower, z30, z42, fen, parapet_h=1.2, parapet_t=0.5)
    t3p = C.offset_polygon(tower, -1.6)
    objs += C.tower_tier(f"{ID}_t3", t3p, z42, z52, fen, parapet_h=1.2, parapet_t=0.5)
    t4p = C.offset_polygon(t3p, -1.6)
    objs += C.tower_tier(f"{ID}_t4", t4p, z52, z57, fen, parapet_h=0.0)

    # ---- the crown: corner tourelles, gabled dormers, copper pyramid and lantern -------------------------------
    b = C.MeshBuilder()
    ring = C.ring_coords(t4p)
    cxx = sum(p[0] for p in ring) / len(ring)
    cyy = sum(p[1] for p in ring) / len(ring)
    # buttress pinnacles at the corners of the 52nd-floor setback
    for qx, qy in C.ring_coords(t3p):
        b.lathe([(1.5, 0.0), (1.5, 4.0), (1.15, 4.6), (1.15, 9.0), (0.0, 14.5)], 8, tc, origin=(qx, qy, z52), smooth=False)
    # the four octagonal corner tourelles of the crown
    tour_h = 16.0
    for qx, qy in ring:
        dx, dy = qx - cxx, qy - cyy
        d = math.hypot(dx, dy) or 1.0
        ox, oy = cxx + dx / d * (d - 1.0), cyy + dy / d * (d - 1.0)
        b.lathe([(2.3, 0.0), (2.3, tour_h * 0.62), (2.7, tour_h * 0.66), (2.5, tour_h * 0.72), (0.0, tour_h)], 8, cop,
                origin=(ox, oy, z57), smooth=False)
    # gabled dormers on each face of the pyramid, then the pyramid itself
    zp0 = z57 + 2.0
    b.prism(ring, z57, zp0, tc, material_top=None, cap_top=False)
    apex_h = FINIAL_M - 9.0 - zp0
    C.pyramid_roof(b, ring, zp0, apex_h, cop)
    for p0, p1, L, t, n in C.edges_of(ring):
        q = (p0 + p1) / 2
        b.hull([(float(q[0] - t[0] * 2.2), float(q[1] - t[1] * 2.2), zp0),
                (float(q[0] + t[0] * 2.2), float(q[1] + t[1] * 2.2), zp0),
                (float(q[0] - t[0] * 2.2 - n[0] * 1.6), float(q[1] - t[1] * 2.2 - n[1] * 1.6), zp0),
                (float(q[0] + t[0] * 2.2 - n[0] * 1.6), float(q[1] + t[1] * 2.2 - n[1] * 1.6), zp0),
                (float(q[0] - n[0] * 1.2), float(q[1] - n[1] * 1.2), zp0 + 7.0)], cop)
    # lantern and finial
    b.lathe([(2.6, 0.0), (2.6, 4.0), (3.0, 4.4), (2.2, 5.0), (1.2, 7.4), (0.35, 8.4), (0.0, 9.0)], 8, cop,
            origin=(cxx, cyy, FINIAL_M - 9.0), smooth=False)
    objs.append(b.build(f"{ID}_crown"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=FINIAL_M, name="Woolworth Building", lp_number="LP-01273",
             height_source="CTBUH/Emporis/Wikipedia/LPC LP-1273: 792 ft = 241.4 m to the finial, 60 storeys, 57th-floor deck at 730 ft = 222.5 m",
             fidelity_statement=(
                 "Exact: real footprint with its west light court, 241.4 m finial, 60 storeys, 57th-floor deck at 222.5 m, "
                 "the 30-storey base / 30-storey tower division, the copper pyramidal crown with four octagonal corner "
                 "tourelles, gabled dormers and a lantern, and the limestone / cream-terracotta / copper material split "
                 "with Gothic vertical mullions. Inferred (+-2 floors): the tower setbacks at floors 42 and 52 and the "
                 "tower plan (about 25 x 25 m). Simplified: Gothic crockets, tracery and gargoyles are carried as mullion "
                 "and pinnacle geometry rather than modelled carving. Not modelled: the mosaic-vaulted lobby."),
             notes="Storey heights derived from the two published fixed points (241.4 m finial, 222.5 m 57th-floor deck)",
             dimensions={"finial_m": FINIAL_M, "deck57_m": DECK57_M, "storeys": 60, "ground_floor_h_m": GROUND_H,
                         "floor_h_m": round(FLOOR_H, 3), "base_top_floor": 30, "tower_plan_m": [25.0, 25.0],
                         "tourelles": 4, "tourelle_h_m": 16.0})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 120, "elevation_deg": "street", "distance": 185, "target_z": 88, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 130, "elevation_deg": 22, "distance": 720, "fov_deg": 38, "target_z": 130},
    ])


if __name__ == "__main__":
    main()
