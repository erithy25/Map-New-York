"""New York Public Library, Stephen A. Schwarzman Building — Fifth Avenue at 42nd Street (BIN 1034194, LP-00246).
Carrère & Hastings, opened 1911.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 9,844.2 m2, 118.8 x 88.5 m in the model's local frame. The Fifth Avenue front, with the
  portico, the terrace and the two lions, faces east.
* Dimensions [Wikipedia "New York Public Library Main Branch", LPC LP-0246 and the interior designation LP-1523]:
  the building measures 390 x 270 ft (118.9 x 82.3 m) — the OTI polygon agrees to 0.1 m on the long dimension; the
  Fifth Avenue portico has three round-arched entrance bays flanked by paired Corinthian columns; Edward Clark
  Potter's Tennessee-marble lions *Patience* and *Fortitude* (1911) are 11 ft (3.35 m) long on pedestals about 2.4 m
  high; the two fountains (Frederick MacMonnies, *Beauty* and *Truth*) flank the steps.
* Heights: the Fifth Avenue cornice is at 27.4 m, the balustraded attic at 31.4 m and the highest roof at 38.2 m
  (the LiDAR ``height_roof`` for the BIN, which is the tallest element of the building and the height the model is
  verified against). The published sources give the plan dimensions and the storey count but not a per-element height
  schedule, so the 27.4 m and 31.4 m levels are stated as inferred (+-1.5 m).
* Materials [LPC LP-0246]: Vermont Dorset white marble throughout, with a granite terrace, bronze doors and a copper
  roof over the Rose Reading Room.

Fidelity: exact — real footprint, 38.2 m highest roof, the Fifth Avenue terrace with its broad steps, the
three-arched portico with paired Corinthian columns and a full entablature, the flanking pavilions with their fountain
niches, the balustraded attic with pedestals, the two lions at 3.35 m on 2.4 m pedestals, and the white-marble /
granite / copper material split. Inferred (+-1.5 m) — the cornice and attic levels. Simplified — the lions are massing
solids, not carved figures; the attic sculpture groups (Paul Wayland Bartlett) and the pediment relief are omitted;
Corinthian capitals use the shared lathe profile. Not modelled — the Rose Main Reading Room and the other designated
interiors, and Bryant Park behind the building.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "new_york_public_library"
BINS = [1034194]
ROOF_M = 38.2
CORNICE_M = 27.4
ATTIC_M = 31.4
TERRACE_M = 2.6
LION_L = 3.35
PEDESTAL_H = 2.4


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    east = fr.local_cardinal(90.0)
    objs = []
    marble, gran, bronze, cop = C.M.marble_white, C.M.granite_grey, C.M.bronze, C.M.copper_green

    # ---- the block on the real footprint (IoU volume) ----------------------------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, TERRACE_M, gran, material_top=C.M.pavement))
    fen_g = C.Fenestration(floor_h=7.0, bay_w=5.2, window_frac=0.42, recess=0.6, spandrel_h=1.4, pier="marble_white",
                           spandrel="marble_white", glass="glass_dark", window_h=4.6, floor_z=[TERRACE_M, 11.0, 19.0])
    objs += C.tower_tier(f"{ID}_body", P, TERRACE_M, CORNICE_M, fen_g, parapet_h=0.0)
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE_M, [(0.5, 0.0), (1.8, 1.1), (2.1, 1.9), (1.6, 2.7), (0.6, 3.1)], marble))
    objs.append(C.prism(f"{ID}_attic", P, CORNICE_M + 3.1, ATTIC_M, marble, inset=1.6, material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    aring = C.ring_coords(C.offset_polygon(P, -1.6))
    C.balustrade(b, aring, ATTIC_M, 1.8, marble, spacing=0.85, baluster_r=0.11, rail_t=0.3)
    for q, t, n, s in C.ring_stations(aring, 14.0):                # attic pedestals between the balustrade runs
        b.box((float(q[0]), float(q[1]), ATTIC_M + 1.1), (2.2, 1.4, 2.2), marble,
              rot_deg=math.degrees(math.atan2(t[1], t[0])))
    # the copper roof over the reading room, the tallest element of the building
    inner = C.offset_polygon(P, -14.0)
    if inner.geom_type != "Polygon":
        inner = max(inner.geoms, key=lambda g: g.area)
    b.prism(C.ring_coords(inner), ATTIC_M, ROOF_M - 1.6, marble, cap_top=False)
    C.hip_roof(b, C.ring_coords(inner), ROOF_M - 1.6, 1.6, cop, inset=6.0)
    objs.append(b.build(f"{ID}_attic_detail"))

    # ---- the Fifth Avenue front: terrace, steps, portico, lions and fountains -----------------------------------
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    runs = sorted(C.wall_runs(coords, east, tol_deg=50.0), key=lambda r: -r[1])
    pts, Lf = runs[0]
    mid, mt, mn = C.polyline_at(pts, Lf / 2)
    terr_d = 14.0
    # the raised granite terrace in front of the building, with the broad flight of steps
    tp0 = mid - mt * 26.0; tp1 = mid + mt * 26.0
    b.box_from_to(tp0, tp1, mn, terr_d, 0.0, TERRACE_M, gran, top=True, bottom=True)
    C.steps(b, mid - mt * 16.0, mid + mt * 16.0, mn, TERRACE_M, 9, TERRACE_M / 9, 0.42, gran, z_bottom=0.0)
    b.box_from_to(mid - mt * 16.0 - mt * 3.4, mid - mt * 16.0, mn, terr_d * 0.55, 0.0, TERRACE_M + 0.6, gran, top=True)
    b.box_from_to(mid + mt * 16.0, mid + mt * 16.0 + mt * 3.4, mn, terr_d * 0.55, 0.0, TERRACE_M + 0.6, gran, top=True)
    # Patience and Fortitude on their pedestals, flanking the steps
    for sgn in (-1, 1):
        q = mid + mt * (sgn * 18.0) + mn * (terr_d * 0.62)
        b.box((float(q[0]), float(q[1]), TERRACE_M + PEDESTAL_H / 2 + 0.6), (2.0, 4.4, PEDESTAL_H), marble,
              rot_deg=math.degrees(math.atan2(mt[1], mt[0])))
        zl = TERRACE_M + 0.6 + PEDESTAL_H
        body = []
        for du, dv, dz, r in ((-LION_L / 2, 0.0, 0.0, 0.55), (LION_L / 2, 0.0, 0.0, 0.5),
                              (-LION_L / 2 + 0.4, 0.0, 1.05, 0.45), (LION_L / 2 - 0.3, 0.0, 1.3, 0.42)):
            for sx in (-1, 1):
                body.append((float(q[0] + mn[0] * du + mt[0] * (dv + sx * r)), float(q[1] + mn[1] * du + mt[1] * (dv + sx * r)), zl + dz + r))
                body.append((float(q[0] + mn[0] * du + mt[0] * dv), float(q[1] + mn[1] * du + mt[1] * dv), zl + dz + (0.0 if sx < 0 else 2 * r)))
        b.hull(body, marble)
    # the portico: three arched entrance bays with paired Corinthian columns and an entablature
    for k, dx in enumerate((-11.0, 0.0, 11.0)):
        a, t, n = C.polyline_at(pts, Lf / 2 + dx - 3.6)
        c, t2, n2 = C.polyline_at(pts, Lf / 2 + dx + 3.6)
        C.arched_opening(b, a, c, n, TERRACE_M, TERRACE_M + 7.0, None, 2.8, marble, bronze, n=14)
    for dx in (-16.6, -5.4, 5.4, 16.6):
        q, t, n = C.polyline_at(pts, Lf / 2 + dx)
        for dd in (-1.5, 1.5):
            C.column(b, float(q[0] + t[0] * dd + n[0] * 2.9), float(q[1] + t[1] * dd + n[1] * 2.9), TERRACE_M, 13.5, 0.85,
                     marble, order="corinthian", segments=14)
    C.entablature(b, mid - mt * 21.0, mid + mt * 21.0, mn, TERRACE_M + 13.5, 3.6, 3.6, marble, overhang=0.5)
    # the two fountain niches flanking the portico
    for sgn in (-1, 1):
        q, t, n = C.polyline_at(pts, Lf / 2 + sgn * 30.0)
        C.arched_opening(b, q - t * 2.6, q + t * 2.6, n, TERRACE_M, TERRACE_M + 5.4, None, 1.7, marble, C.M.water_dark, n=12)
        b.box_from_to(q - t * 3.4, q + t * 3.4, n, 2.2, 0.0, TERRACE_M + 0.9, gran, top=True)
    objs.append(b.build(f"{ID}_fifth_avenue_front"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=ROOF_M, name="New York Public Library, Stephen A. Schwarzman Building",
             lp_number="LP-00246",
             height_source="LiDAR height_roof for BIN 1034194 = 38.18 m (highest roof); plan 390 x 270 ft = 118.9 x 82.3 m [Wikipedia / LPC LP-0246]",
             fidelity_statement=(
                 "Exact: real footprint (118.8 m long, matching the published 390 ft to 0.1 m), 38.2 m highest roof, the "
                 "Fifth Avenue granite terrace with its broad steps, the three-arched portico with paired Corinthian "
                 "columns and a full entablature, the two flanking fountain niches, the balustraded attic with pedestals, "
                 "and Patience and Fortitude at their real 3.35 m length on 2.4 m pedestals, in Vermont marble. "
                 "Inferred (+-1.5 m): the cornice (27.4 m) and attic (31.4 m) levels, which are not published "
                 "individually. Simplified: the lions are massing solids, not carved figures; the Bartlett attic "
                 "sculpture groups and the pediment relief are omitted. Not modelled: the Rose Main Reading Room and the "
                 "other designated interiors, and Bryant Park behind the building."),
             notes="Height is verified against the LiDAR roof height; the cornice and attic levels are inferred",
             dimensions={"roof_m": ROOF_M, "cornice_m": CORNICE_M, "attic_m": ATTIC_M, "terrace_m": TERRACE_M,
                         "lion_length_m": LION_L, "lion_pedestal_h_m": PEDESTAL_H, "portico_bays": 3,
                         "published_plan_m": [118.9, 82.3]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 100, "elevation_deg": "street", "distance": 120, "target_z": 22, "fov_deg": 66},
        {"view": "aerial", "azimuth_deg": 115, "elevation_deg": 24, "distance": 285, "fov_deg": 48, "target_z": 20},
    ])


if __name__ == "__main__":
    main()
