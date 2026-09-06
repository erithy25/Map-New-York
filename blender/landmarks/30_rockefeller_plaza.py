"""30 Rockefeller Plaza (the RCA / GE / Comcast Building) with the Lower Plaza, rink and flag row.
BIN 1076262. Raymond Hood / Associated Architects, 1933.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 9,189.3 m2 — the block between West 49th and West 50th Streets, from Rockefeller Plaza
  west to Sixth Avenue; 162.8 m on the street axis by 59.9 m across in the model's local frame (the +x axis of the frame
  points ESE, i.e. towards Rockefeller Plaza and Fifth Avenue).
* Heights [CTBUH, Emporis, Wikipedia "30 Rockefeller Plaza"]: 850 ft = 259.1 m; 70 storeys; ground floor 7.4 m, typical
  floor 3.65 m (derived so that floor 70 lands at the roof slab).
* Massing [Wikipedia "Architecture", Krinsky, *Rockefeller Center*]: Hood set the slab's *depth* by the rule that no
  desk should be more than 27 ft (8.2 m) from a window, so the building steps back on its long north and south flanks
  every few floors while the east and west elevations stay a constant 59.9 m wide for the full 259.1 m. The six setback
  levels used here (floors 16/24/32/40/50/58) reproduce that profile; the published sources give the rule and the
  silhouette but not a floor-by-floor list, so the six levels are inferred (+-2 floors).
* Lower Plaza and rink [Rockefeller Center / Tishman Speyer, Wikipedia "Rockefeller Center"]: the sunken plaza is
  122 x 59 ft (37.2 x 18.0 m) and lies 20 ft (6.1 m) below the surrounding street level; the ice rink occupies its
  floor. Paul Manship's gilded bronze *Prometheus* (1934) is 18 ft (5.5 m) long and stands against the plaza's west
  wall over a granite fountain wall. The plaza is ringed by the flag row — the flags of the United Nations member
  states, about 100 poles of 8.5 m; the model places as many 8.5 m poles at the published 2.7 m spacing as the real
  parapet length allows and reports the count in ``dimensions``.
* Materials [LPC Rockefeller Center designation report LP-1446]: Indiana limestone piers (1.5 m) with matt cast-aluminium spandrels
  in continuous vertical window strips on a 2.9 m module; granite at the ground floor; gilded bronze for Prometheus.

Fidelity: exact — real footprint, 259.1 m / 70 storeys, the constant-width east and west elevations, the stepped north
and south flanks, the limestone-pier / aluminium-spandrel window-strip rhythm, the sunken plaza at -6.1 m with a
37.2 x 18.0 m rink, Prometheus at 5.5 m over the west fountain wall, and the flag row at its real spacing. Inferred
(+-2 floors) — the six setback levels. Simplified — Prometheus is a gilded massing solid, not a cast figure; the
Lee Lawrie limestone relief and the entrance screens over the doors are carried as recessed panels, not sculpture.
Not modelled — the Channel Gardens east of the plaza, the low buildings of the rest of Rockefeller Center, interiors.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "30_rockefeller_plaza"
BINS = [1076262]
ROOF_M = 259.1
GROUND_H = 7.4
FLOOR_H = (ROOF_M - 7.4) / 69.0        # 3.648 m
SETBACK_FLOORS = (16, 24, 32, 40, 50, 58)
RINK_L, RINK_W, PLAZA_DEPTH = 37.2, 18.0, 6.1
FLAG_H, FLAG_SPACING = 8.5, 2.7


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
    gran = C.M.granite_grey

    # ---- base on the real footprint ----------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, GROUND_H, gran, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for p0, p1, L, t, n in C.edges_of(coords):        # granite ground floor with tall shopfront bays
        if L < 8:
            continue
        k = max(1, int(round(L / 6.1)))
        for i in range(k):
            a = p0 + t * (L * i / k + 1.0); c = p0 + t * (L * (i + 1) / k - 1.0)
            C.window_punch(b, a, c, n, 0.7, GROUND_H - 1.2, 0.45, gran, C.M.glass_clear, sill=0.0)
    objs.append(b.build(f"{ID}_ground_detail"))

    # ---- the stepped slab --------------------------------------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=2.9, window_frac=0.48, recess=0.42, spandrel_h=1.0, strip=True,
                         pier="limestone", spandrel="aluminium_cast", glass="glass_dark")
    levels = [1, *SETBACK_FLOORS, 70]
    plan = P
    for k in range(len(levels) - 1):
        f0, f1 = levels[k], levels[k + 1]
        z0 = GROUND_H if k == 0 else fz(f0)
        z1 = fz(f1) if f1 < 70 else ROOF_M
        last = k == len(levels) - 2
        objs += C.tower_tier(f"{ID}_t{k}", plan, z0, z1 - (1.1 if last else 0.0), fen,
                             parapet_h=1.1, parapet_t=0.45, roof_material="roof_grey")
        # step back only on the long (north and south) flanks, keeping the east and west elevations full width
        if k < len(levels) - 2:
            step = 9.0 if k < 3 else 7.0
            nxt = plan.intersection(C.rect_xy(plan.bounds[0] + step, miny - 5, plan.bounds[2] - step, maxy + 5))
            plan = C._orient(nxt.buffer(0), 1.0) if not nxt.is_empty else plan
            if plan.geom_type != "Polygon":
                plan = max(plan.geoms, key=lambda g: g.area)
    objs.append(C.prism(f"{ID}_roof", plan, ROOF_M - 0.4, ROOF_M, C.M.roof_dark))

    # ---- Lower Plaza, rink, Prometheus and the flag row (east of the building, towards Fifth Avenue) ------------
    b = C.MeshBuilder()
    px0 = maxx + 4.0                                   # plaza starts 4 m east of the building line
    plaza = C.rect_xy(px0, cy - RINK_L / 2 - 6.0, px0 + RINK_W + 12.0, cy + RINK_L / 2 + 6.0)
    rink = C.rect_xy(px0 + 6.0, cy - RINK_L / 2, px0 + 6.0 + RINK_W, cy + RINK_L / 2)
    b.prism(C.ring_coords(plaza), -PLAZA_DEPTH - 0.4, 0.0, C.M.pavement,
            holes=[C.ring_coords(rink)], cap_top=True, cap_bottom=False)     # plaza deck with the well cut out
    b.prism(C.ring_coords(rink), -PLAZA_DEPTH - 0.4, -PLAZA_DEPTH, C.M.ice_white)   # rink floor (ice)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(rink)):                  # the well walls (granite)
        b.box_from_to(p0, p1, -n, 0.35, -PLAZA_DEPTH, 0.0, gran, top=True, bottom=False)
    # Prometheus: gilded bronze, 5.5 m long, on the west wall of the well
    pmx = px0 + 6.3
    b.hull([(pmx, cy - 2.75, -PLAZA_DEPTH + 1.2), (pmx, cy + 2.75, -PLAZA_DEPTH + 1.2),
            (pmx + 2.6, cy - 1.6, -PLAZA_DEPTH + 2.0), (pmx + 2.6, cy + 1.6, -PLAZA_DEPTH + 2.0),
            (pmx + 1.1, cy - 0.9, -PLAZA_DEPTH + 3.6), (pmx + 1.1, cy + 0.9, -PLAZA_DEPTH + 3.6),
            (pmx + 3.4, cy, -PLAZA_DEPTH + 2.6)], C.M.gold)
    b.box((pmx - 0.9, cy, -PLAZA_DEPTH + 2.2), (1.8, 12.0, 4.4), gran)       # fountain wall behind it
    # flag row: 8.5 m poles at 2.7 m centres around the plaza parapet
    ring = C.ring_coords(C.offset_polygon(plaza, -1.1))
    flags = 0
    for p0, p1, L, t, nn in C.edges_of(ring):
        k = int(L // FLAG_SPACING)
        for i in range(k):
            q = p0 + t * (FLAG_SPACING * (i + 0.5))
            cols = (("flag_red", "flag_white", "flag_blue"), ("flag_blue", "flag_white", "flag_red"),
                    ("flag_white", "flag_red", "flag_white"))[flags % 3]
            C.flagpole(b, float(q[0]), float(q[1]), 0.0, FLAG_H, flag=cols, flag_w=1.4, flag_h=0.95,
                       angle_deg=math.degrees(math.atan2(t[1], t[0])) + 90.0)
            flags += 1
    objs.append(b.build(f"{ID}_lower_plaza"))
    plaza_cam = {"eye": fr.to_export(px0 + RINK_W + 26.0, cy - 16.0, 3.2),
                 "target": fr.to_export(px0 + 3.0, cy, 26.0)}
    return objs, fr, fp, flags, plaza_cam


def main():
    objs, fr, fp, flags, plaza_cam = build()
    C.finish(objs, ID, BINS, fr, height_m=ROOF_M, name="30 Rockefeller Plaza", lp_number="LP-01446",
             height_source="CTBUH/Emporis/Wikipedia: 850 ft = 259.1 m, 70 storeys",
             fidelity_statement=(
                 "Exact: real footprint, 259.1 m / 70 storeys, constant-width east and west elevations with stepped north "
                 "and south flanks (Hood's 27 ft daylight rule), limestone-pier / cast-aluminium-spandrel window strips, "
                 "the Lower Plaza sunk 6.1 m with a 37.2 x 18.0 m rink, Prometheus 5.5 m long on the west fountain wall, "
                 f"and {flags} flagpoles of 8.5 m at the real 2.7 m spacing around the plaza parapet. "
                 "Inferred (+-2 floors): the six setback levels (16/24/32/40/50/58) — the sources give the rule and the "
                 "silhouette, not a floor-by-floor list. Simplified: Prometheus is a gilded massing solid, not a cast "
                 "figure; the Lee Lawrie entrance reliefs are recessed panels. Not modelled: the Channel Gardens, the "
                 "other Rockefeller Center buildings, and all interiors."),
             notes="The Lower Plaza, rink, Prometheus and flag row lie east of the building footprint and are exported with it",
             dimensions={"roof_m": ROOF_M, "storeys": 70, "ground_floor_h_m": GROUND_H, "floor_h_m": round(FLOOR_H, 3),
                         "setback_floors": list(SETBACK_FLOORS), "slab_width_m": 59.9, "slab_depth_base_m": 162.8,
                         "rink_m": [RINK_L, RINK_W], "plaza_depth_m": PLAZA_DEPTH, "prometheus_len_m": 5.5,
                         "flagpoles": flags, "flagpole_h_m": FLAG_H, "flag_spacing_m": FLAG_SPACING})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 105, "elevation_deg": "street", "distance": 395, "target_z": 110, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 158, "elevation_deg": 24, "distance": 830, "fov_deg": 42, "target_z": 130},
        {"view": "plaza", "fov_deg": 68, **plaza_cam},
    ])


if __name__ == "__main__":
    main()
