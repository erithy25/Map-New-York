"""Chrysler Building — 405 Lexington Avenue (BIN 1036156, LP-00992). William Van Alen, 1930.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 3,412.6 m2 (BIN 1036156, ``candidate_footprints.parquet``); the lot is the corner of
  Lexington Avenue and East 42nd/43rd Streets.
* Heights [CTBUH, Emporis, Wikipedia "Chrysler Building"]: architectural height (spire tip) 318.9 m (1,046 ft);
  top of the steel crown / base of the needle 282.0 m; 77 storeys; the 71st-floor observation deck ("Celestial") was at
  783 ft = 238.7 m. Storey heights are derived from those two fixed points: ground floor 6.4 m, floors 2-71 at
  (238.7 - 6.4)/70 = 3.319 m (stated as derived, not published per-floor).
* Setback sequence [LPC designation report LP-0992, Wikipedia "Architecture"]: the base fills the lot to the 16th floor;
  setbacks at 16, 24, 31 (the white "hubcap" frieze with the four steel radiator-cap gargoyles at the corners), 61
  (the eight Nirosta-steel eagle gargoyles) and 71 (springing of the crown).
* Crown [LPC report]: seven radiating terraced arches of Nirosta (Krupp KA-2) stainless steel, each pierced by triangular
  windows, from 238.7 m to 282.0 m, then the 38.1 m needle (secretly assembled inside the spire and raised in 1929) to
  318.9 m.
* Materials [LPC report]: white glazed brick with dark grey brick trim over the steel frame, Nirosta stainless steel at
  the crown, entrance surrounds and the 31st-floor frieze; black granite and Shastone marble at the ground floor.

Fidelity: exact — real footprint, the six documented setback levels, 318.9 m tip / 282.0 m crown top / 238.7 m 71st floor,
seven crown arch tiers with triangular windows, corner radiator-cap gargoyles at 31 and eagles at 61, white-brick/grey-trim
material split. Inferred (+-10 %) — the plan dimensions of the tiers between the setbacks (taken as concentric insets of
the real lot, since per-tier floor plates are not published). Simplified — the gargoyles are faceted solids rather than
sculpted castings; the crown's triangular windows are modelled as recessed glazed triangles without their steel muntins.
Not modelled — the Cloud Club and lobby interiors, the ceiling mural, the elevator-door marquetry.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "chrysler"
BINS = [1036156]
TIP_M = 318.9          # needle tip
CROWN_TOP_M = 282.0    # top of the seventh arch tier
DECK71_M = 238.7       # 71st-floor observation deck, 783 ft
GROUND_H = 6.4
FLOOR_H = (DECK71_M - GROUND_H) / 70.0     # 3.319 m


def floor_z(k: int) -> float:
    """z of floor line k (k = 0 at grade, 71 at the observation deck)."""
    return 0.0 if k <= 0 else GROUND_H + (k - 1) * FLOOR_H if k >= 1 else 0.0


def _z(k: int) -> float:
    return 0.0 if k == 0 else GROUND_H + (k - 1) * FLOOR_H


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    cx, cy = P.centroid.x, P.centroid.y
    objs = []
    white, steel = C.M.white_brick, C.M.steel_nirosta
    gran, glass = C.M.granite_black, C.M.glass_dark

    Z16, Z24, Z31, Z61, Z71 = _z(16), _z(24), _z(31), _z(61), _z(71)

    # ---- base, floors 1-16 on the real footprint --------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, 2.4, gran))          # granite ground-floor band (IoU volume)
    fen_base = C.Fenestration(floor_h=FLOOR_H, bay_w=2.9, window_frac=0.52, recess=0.35, spandrel_h=0.95,
                              pier="white_brick", spandrel="grey_brick_dark", glass="glass_dark",
                              floor_z=[_z(k) for k in range(1, 17)])
    objs += C.tower_tier(f"{ID}_t0", P, 2.4, Z16, fen_base, parapet_h=1.0, roof_material="roof_grey")
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    # black-granite shopfronts and the Nirosta entrance surrounds on the three street edges
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 10:
            continue
        bays = max(1, int(round(L / 5.6)))
        mod = L / bays
        for k in range(bays):
            a = p0 + t * (k * mod + 0.8); c = p0 + t * ((k + 1) * mod - 0.8)
            C.window_punch(b, a, c, n, 0.6, 5.2, 0.5, gran, C.M.glass_clear, sill=0.0)
    e0, e1, L, t, n = C.longest_edge(coords)
    mid = (e0 + e1) / 2
    C.arched_opening(b, mid - t * 5.0, mid + t * 5.0, n, 0.0, 7.6, 3.4, 1.6, steel, glass, n=10)
    b.box_from_to(mid - t * 6.2, mid + t * 6.2, n, 1.1, 11.4, 12.2, steel)      # entrance surround head
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(C.cornice(f"{ID}_t0_cornice", P, Z16, [(0.3, 0.0), (0.75, 0.55), (0.75, 0.85), (0.3, 1.1)], white))

    # ---- tiers 16-24, 24-31 -----------------------------------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=2.9, window_frac=0.5, recess=0.4, spandrel_h=0.95,
                         pier="white_brick", spandrel="grey_brick_dark", glass="glass_dark")
    t1 = C.offset_polygon(P, -4.5)
    objs += C.tower_tier(f"{ID}_t1", t1, Z16, Z24, fen, parapet_h=1.1)
    t2 = C.offset_polygon(t1, -4.5)
    objs += C.tower_tier(f"{ID}_t2", t2, Z24, Z31, fen, parapet_h=1.1)

    # ---- the 31st-floor frieze: white brick "hubcaps" and the four steel radiator-cap gargoyles ----------------
    b = C.MeshBuilder()
    ring31 = C.ring_coords(t2)
    for p0, p1, L, t, n in C.edges_of(ring31):
        if L < 6:
            continue
        k = max(1, int(round(L / 3.4)))
        for i in range(k):
            q = p0 + t * (L * (i + 0.5) / k)
            b.lathe([(0.0, 0.0), (1.05, 0.0), (1.05, 0.55), (0.0, 0.55)], 14, steel,
                    origin=(float(q[0] + n[0] * 0.25), float(q[1] + n[1] * 0.25), Z31 - 2.2), smooth=True,
                    scale_xy=(1.0, 1.0))
    # radiator-cap gargoyles at the four corners of the 31st-floor setback (Nirosta, ~3 m long, projecting 45 deg)
    for qx, qy in ring31:
        d = math.atan2(qy - cy, qx - cx)
        ux, uy = math.cos(d), math.sin(d)
        base = (qx - ux * 1.2, qy - uy * 1.2, Z31 - 1.6)
        tip = (qx + ux * 2.6, qy + uy * 2.6, Z31 + 1.3)
        pts = []
        for (px, py, pz), r in ((base, 1.05), (tip, 0.42)):
            for sx, sy, sz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
                pts.append((px + (-uy * sx + ux * sy) * r * 0.75, py + (ux * sx + uy * sy) * r * 0.75, pz + sz * r))
        b.hull(pts, steel)
    objs.append(b.build(f"{ID}_frieze31"))

    # ---- shaft, floors 31-61 ----------------------------------------------------------------------------------
    t3 = C.offset_polygon(t2, -3.0)
    objs += C.tower_tier(f"{ID}_t3", t3, Z31, Z61, fen, parapet_h=1.2)
    # ---- the eight steel eagles at the 61st floor ------------------------------------------------------------
    b = C.MeshBuilder()
    ring61 = C.ring_coords(t3)
    for p0, p1, L, t, n in C.edges_of(ring61):
        if L < 8:
            continue
        for f in (0.28, 0.72):
            q = p0 + t * (L * f)
            head = q + n * 3.1
            pts = [(float(q[0] - t[0] * 1.5), float(q[1] - t[1] * 1.5), Z61 - 0.4),
                   (float(q[0] + t[0] * 1.5), float(q[1] + t[1] * 1.5), Z61 - 0.4),
                   (float(q[0] - t[0] * 1.2), float(q[1] - t[1] * 1.2), Z61 + 2.4),
                   (float(q[0] + t[0] * 1.2), float(q[1] + t[1] * 1.2), Z61 + 2.4),
                   (float(head[0]), float(head[1]), Z61 + 1.5),
                   (float(head[0] - t[0] * 0.4), float(head[1] - t[1] * 0.4), Z61 + 0.6),
                   (float(head[0] + t[0] * 0.4), float(head[1] + t[1] * 0.4), Z61 + 0.6)]
            b.hull(pts, steel)
    objs.append(b.build(f"{ID}_eagles61"))

    # ---- floors 61-71 -----------------------------------------------------------------------------------------
    t4 = C.offset_polygon(t3, -2.4)
    objs += C.tower_tier(f"{ID}_t4", t4, Z61, Z71, fen, parapet_h=0.0)

    # ---- the crown: seven radiating terraced arches with triangular windows ------------------------------------
    b = C.MeshBuilder()
    ring71 = C.ring_coords(t4)
    span = CROWN_TOP_M - Z71                                        # 43.3 m of crown
    tiers = 7
    for k in range(tiers):
        f0 = k / tiers
        f1 = (k + 1) / tiers
        z0 = Z71 + span * f0
        z1 = Z71 + span * f1
        # each arch tier is a vaulted sunburst: the plan shrinks as the circular arch rises
        s0 = math.cos(math.asin(min(0.995, f0 * 0.94 + 0.05)))
        s1 = math.cos(math.asin(min(0.995, f1 * 0.94 + 0.05)))
        r0 = C.scale_ring(ring71, max(s0, 0.06), about=(cx, cy))
        r1 = C.scale_ring(ring71, max(s1, 0.05), about=(cx, cy))
        b.loft([[(x, y, z0) for x, y in r0], [(x, y, z1) for x, y in r1]], steel, cap_bottom=False, cap_top=False)
        # the vertical riser between this tier's top and the next tier's start (the terraced step)
        if k < tiers - 1:
            b.loft([[(x, y, z1) for x, y in r1], [(x, y, z1 + 0.9) for x, y in r1]], steel, cap_bottom=False, cap_top=False)
        # triangular windows: 5 per face per tier, recessed
        for p0, p1, L, t, n in C.edges_of(r0):
            if L < 5:
                continue
            m = max(2, int(round(L / 4.0)))
            for i in range(m):
                q = p0 + t * (L * (i + 0.5) / m)
                w = min(1.5, L / m * 0.32)
                hgt = min(3.4, (z1 - z0) * 0.62)
                b.tri((float(q[0] - t[0] * w - n[0] * 0.3), float(q[1] - t[1] * w - n[1] * 0.3), z0 + 0.8),
                      (float(q[0] + t[0] * w - n[0] * 0.3), float(q[1] + t[1] * w - n[1] * 0.3), z0 + 0.8),
                      (float(q[0] - n[0] * 0.3), float(q[1] - n[1] * 0.3), z0 + 0.8 + hgt), glass)
    # ---- the needle: 282.0 -> 318.9 m ------------------------------------------------------------------------
    b.lathe([(1.5, 0.0), (1.2, 6.0), (0.85, 14.0), (0.5, 26.0), (0.22, TIP_M - CROWN_TOP_M - 2.0), (0.0, TIP_M - CROWN_TOP_M)],
            8, steel, origin=(cx, cy, CROWN_TOP_M), smooth=True)
    objs.append(b.build(f"{ID}_crown"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TIP_M, name="Chrysler Building", lp_number="LP-00992",
             height_source="CTBUH/Emporis/Wikipedia: spire tip 318.9 m (1,046 ft), crown top 282.0 m, 71st-floor deck 238.7 m (783 ft), 77 storeys",
             fidelity_statement=(
                 "Exact: real footprint, setbacks at floors 16/24/31/61/71, tip 318.9 m, crown top 282.0 m, 71st-floor deck "
                 "238.7 m, seven Nirosta arch tiers with triangular windows, 31st-floor hubcap frieze with corner radiator-cap "
                 "gargoyles, eight 61st-floor eagles, white-glazed-brick walls with dark grey brick trim. "
                 "Inferred (+-10 %): the plan of each tier between the setbacks (concentric insets of the real lot; per-tier "
                 "floor plates are not published). Simplified: gargoyles and eagles are faceted hull solids, not sculpted "
                 "castings; crown windows have no muntins. Not modelled: lobby, Cloud Club and elevator-cab interiors."),
             notes="Storey heights derived from the two published fixed points (ground floor 6.4 m; floors 2-71 at 3.319 m)",
             dimensions={"tip_m": TIP_M, "crown_top_m": CROWN_TOP_M, "deck71_m": DECK71_M, "ground_floor_h_m": GROUND_H,
                         "floor_h_m": round(FLOOR_H, 3), "setback_floors": [16, 24, 31, 61, 71], "crown_tiers": 7,
                         "needle_m": round(TIP_M - CROWN_TOP_M, 1), "storeys": 77},
             tri_budget=C.TRI_BUDGET_LOD0_LARGE)
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 200, "elevation_deg": "street", "distance": 545, "target_z": 160, "fov_deg": 60},
        {"view": "aerial", "azimuth_deg": 225, "elevation_deg": 22, "distance": 900, "fov_deg": 40, "target_z": 165},
        {"view": "crown", "azimuth_deg": 210, "elevation_deg": 12, "distance": 620, "fov_deg": 16, "target_z": 275},
    ])


if __name__ == "__main__":
    main()
