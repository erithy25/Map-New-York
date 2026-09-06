"""40 Wall Street — the Bank of Manhattan Trust / Trump Building (BIN 1001018). H. Craig Severance with
Yasuo Matsui, 1930.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 3,027.8 m2 — the Wall Street / Pine Street block front, 69.4 x 59.5 m in the model's
  local frame.
* Heights [CTBUH, Emporis, Wikipedia "40 Wall Street", LPC LP-2029]: architectural height 927 ft = 282.5 m to the top
  of the spire; the base of the spire (top of the copper pyramid's lantern) is at 268.0 m and the pyramid springs from
  the main roof parapet at 224.5 m; 70 storeys. Storey heights derived from that: ground floor 7.5 m, floors 2-63 at
  3.5 m, so floor 63 (the parapet) lands at 224.5 m; floors 64-70 are inside the pyramid.
* Massing [LPC LP-2029, Wikipedia]: a limestone base filling the lot to the fifth floor, setbacks at floors 5, 18, 26
  and 36 as the shaft narrows, then the tower, and above the parapet the steep green-copper pyramidal roof with four
  corner turrets and a lantern carrying the spire. The four setback floors are read off published elevations and are
  stated as inferred (+-2 floors).
* Materials [LPC LP-2029]: limestone at the base and lower shaft, buff brick with limestone trim on the upper shaft,
  copper (now green) at the pyramid, turrets and lantern.

Fidelity: exact — real footprint, 282.5 m spire tip, 268.0 m lantern top, 224.5 m parapet, 70 storeys, the steep copper
pyramidal crown with four corner turrets and a lantern, the limestone-base / buff-brick-shaft / copper-crown material
split. Inferred (+-2 floors) — the four setback levels and the plan of each tier. Simplified — the Gothic tracery of the
crown's dormers is carried as recessed panels; the spire is a plain tapered mast. Not modelled — the banking hall
interior; the 1998-1999 re-cladding of the entrance is not distinguished from the 1930 fabric.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "40_wall_street"
BINS = [1001018]
TIP_M = 282.5
LANTERN_TOP_M = 268.0
PARAPET_M = 224.5
GROUND_H = 7.5
FLOOR_H = (PARAPET_M - GROUND_H) / 62.0        # 3.5 m
SETBACK_FLOORS = (5, 18, 26, 36)


def fz(k: int) -> float:
    return 0.0 if k <= 0 else GROUND_H + (k - 1) * FLOOR_H


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    objs = []
    lime, cop, glass = C.M.limestone, C.M.copper_green, C.M.glass_dark

    # ---- limestone base on the real footprint ------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, GROUND_H, lime, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 9:
            continue
        k = max(1, int(round(L / 5.0)))
        for i in range(k):
            a = p0 + t * (L * i / k + 0.9); c = p0 + t * (L * (i + 1) / k - 0.9)
            C.window_punch(b, a, c, n, 0.9, GROUND_H - 1.4, 0.55, lime, C.M.glass_clear, sill=0.0)
    runs = sorted(C.wall_runs(coords, fr.local_cardinal(180.0), tol_deg=60.0), key=lambda r: -r[1])
    if runs:                                       # the Wall Street entrance: a three-storey arched portal
        pts, L = runs[0]
        a, t, n = C.polyline_at(pts, L / 2 - 5.0)
        c, t2, n2 = C.polyline_at(pts, L / 2 + 5.0)
        C.arched_opening(b, a, c, n, 0.0, 8.0, None, 2.2, lime, glass, n=12)
    objs.append(b.build(f"{ID}_base_detail"))

    # ---- shaft with the documented setbacks --------------------------------------------------------------------
    fen_lo = C.Fenestration(floor_h=FLOOR_H, bay_w=2.8, window_frac=0.5, recess=0.45, spandrel_h=1.0,
                            pier="limestone", spandrel="limestone", glass="glass_dark")
    fen_hi = C.Fenestration(floor_h=FLOOR_H, bay_w=2.8, window_frac=0.5, recess=0.45, spandrel_h=1.0,
                            pier="brick_buff", spandrel="limestone", glass="glass_dark")
    levels = [1, *SETBACK_FLOORS, 63]
    plan = P
    insets = (0.0, 4.0, 4.0, 3.5, 3.0)
    for k in range(len(levels) - 1):
        f0, f1 = levels[k], levels[k + 1]
        z0 = GROUND_H if k == 0 else fz(f0)
        z1 = fz(f1)
        if insets[k]:
            nxt = C.offset_polygon(plan, -insets[k])
            if not nxt.is_empty:
                plan = nxt if nxt.geom_type == "Polygon" else max(nxt.geoms, key=lambda g: g.area)
        last = k == len(levels) - 2
        objs += C.tower_tier(f"{ID}_t{k}", plan, z0, z1 - (1.4 if last else 0.0), fen_lo if k <= 1 else fen_hi,
                             parapet_h=1.4, parapet_t=0.5)

    # ---- the copper crown: pyramid, four corner turrets, lantern and spire -------------------------------------
    b = C.MeshBuilder()
    ring = C.ring_coords(plan)
    cxx = sum(p[0] for p in ring) / len(ring)
    cyy = sum(p[1] for p in ring) / len(ring)
    pyr_top = LANTERN_TOP_M - 12.0
    C.pyramid_roof(b, ring, PARAPET_M, pyr_top - PARAPET_M, cop)
    for p0, p1, L, t, n in C.edges_of(ring):       # Gothic dormers on each slope of the pyramid
        if L < 8:
            continue
        for f in (0.32, 0.68):
            q = p0 + t * (L * f)
            b.hull([(float(q[0] - t[0] * 1.6), float(q[1] - t[1] * 1.6), PARAPET_M),
                    (float(q[0] + t[0] * 1.6), float(q[1] + t[1] * 1.6), PARAPET_M),
                    (float(q[0] - t[0] * 1.6 - n[0] * 1.3), float(q[1] - t[1] * 1.6 - n[1] * 1.3), PARAPET_M),
                    (float(q[0] + t[0] * 1.6 - n[0] * 1.3), float(q[1] + t[1] * 1.6 - n[1] * 1.3), PARAPET_M),
                    (float(q[0] - n[0] * 1.0), float(q[1] - n[1] * 1.0), PARAPET_M + 6.5)], cop)
    for qx, qy in ring:                            # four corner turrets
        b.lathe([(2.0, 0.0), (2.0, 9.0), (2.4, 9.5), (2.1, 10.2), (0.0, 17.0)], 8, cop, origin=(qx, qy, PARAPET_M - 3.0))
    b.lathe([(3.4, 0.0), (3.4, 6.0), (3.9, 6.5), (2.6, 7.4), (1.5, 11.0), (0.9, 12.0)], 8, cop,
            origin=(cxx, cyy, pyr_top))            # the lantern
    b.lathe([(0.9, 0.0), (0.6, 6.0), (0.28, TIP_M - LANTERN_TOP_M - 1.5), (0.0, TIP_M - LANTERN_TOP_M)], 8,
            C.M.steel_dark, origin=(cxx, cyy, LANTERN_TOP_M), smooth=True)
    objs.append(b.build(f"{ID}_crown"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TIP_M, name="40 Wall Street (Trump Building)", lp_number="LP-02029",
             height_source="CTBUH/Emporis/Wikipedia: 927 ft = 282.5 m to the spire tip, 70 storeys; parapet 224.5 m, lantern top 268.0 m",
             fidelity_statement=(
                 "Exact: real footprint, 282.5 m spire tip, 268.0 m lantern top, 224.5 m main parapet, 70 storeys, the steep "
                 "green-copper pyramidal crown with four corner turrets, dormers and a lantern, and the limestone-base / "
                 "buff-brick-shaft / copper-crown material split. Inferred (+-2 floors): the four setback levels "
                 "(5/18/26/36) and the plan of each tier, taken as concentric insets of the real lot. Simplified: the "
                 "Gothic tracery of the crown dormers is recessed panelling, and the spire is a plain tapered mast. "
                 "Not modelled: the banking hall interior; the later entrance re-cladding is not distinguished."),
             notes="Storey heights derived from the published parapet height (224.5 m at floor 63)",
             dimensions={"tip_m": TIP_M, "lantern_top_m": LANTERN_TOP_M, "parapet_m": PARAPET_M, "storeys": 70,
                         "ground_floor_h_m": GROUND_H, "floor_h_m": round(FLOOR_H, 3),
                         "setback_floors": list(SETBACK_FLOORS), "turrets": 4})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 200, "elevation_deg": "street", "distance": 480, "target_z": 141, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 215, "elevation_deg": 22, "distance": 800, "fov_deg": 38, "target_z": 150},
    ])


if __name__ == "__main__":
    main()
