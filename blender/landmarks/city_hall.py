"""New York City Hall — City Hall Park (BIN 1079147, LP-01437; also a National Historic Landmark).
Joseph-François Mangin and John McComb Jr., completed 1812.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 1,988.8 m2, 66.4 x 35.8 m in the model's local frame — the published dimensions are
  216 x 105 ft (65.8 x 32.0 m) [Wikipedia "New York City Hall", LPC LP-1437], which the OTI polygon matches to within
  0.6 m on the long axis; the extra depth is the projecting central portico and the rear wing. The main facade faces
  south, towards Broadway and Park Row.
* Heights: the LiDAR ``height_roof`` for the BIN is 36.57 m, which is the top of the cupola and the statue of Justice
  and the height the model is verified against. Within that: the rusticated basement is 1.6 m, the first storey rises
  to 9.4 m, the second to 16.4 m, the balustraded attic to 20.6 m, the cupola drum to 27.0 m, its colonnade to 31.0 m
  and the dome to 34.4 m, leaving 2.2 m for the copper figure of Justice. No published per-element height schedule
  exists, so every level between grade and 36.6 m is stated as inferred (+-1.5 m).
* Composition [LPC LP-1437]: a French-Renaissance / Federal composition — an arcaded and rusticated ground storey, a
  piano nobile with pilasters and round-arched windows, a balustraded roof line, a projecting central portico of
  paired columns over the entrance stair, and a central cupola.
* Materials [LPC LP-1437]: originally Massachusetts marble on the three public fronts with Newark brownstone at the
  rear; refaced in Alabama limestone in 1954-1956 and again in Georgia marble in 1998-2006 — the model uses the
  present white marble on all elevations, which is the current condition.

Fidelity: exact — real footprint (matching the published 216 x 105 ft), 36.6 m to the top of Justice, the two-storey
composition over a rusticated basement, the arcaded ground storey, the projecting central portico with paired columns
over a raised entrance stair, the balustraded roof line and the colonnaded cupola with a dome and figure. Inferred
(+-1.5 m) — every intermediate level (storey heights, attic, cupola stages). Simplified — the figure of Justice is a
massing solid; the pediment and cupola ornament are omitted. Not modelled — the Governor's Room, the rotunda and the
double cantilevered stair (designated interiors), and City Hall Park.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "city_hall"
BINS = [1079147]
TOP_M = 36.6
BASEMENT_M = 1.6
FLOOR1_M = 9.4
FLOOR2_M = 16.4
ATTIC_M = 20.6
DRUM_M = 27.0
COLONNADE_M = 31.0
DOME_M = 34.4


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    cx, cy = P.centroid.x, P.centroid.y
    south = fr.local_cardinal(180.0)
    objs = []
    marble, gran, cop = C.M.marble_white, C.M.granite_grey, C.M.copper_green

    # ---- rusticated basement and the two main storeys on the real footprint -------------------------------------
    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASEMENT_M, gran, material_top=C.M.pavement))
    objs.append(C.prism(f"{ID}_body", P, BASEMENT_M, ATTIC_M, marble, inset=0.55, material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    BAY = 4.35                                     # the bay module, measured along the wall
    for q, t, n, s in C.ring_stations(coords, BAY):
        # ground storey: rusticated arcade
        C.arched_opening(b, q - t * (BAY * 0.32), q + t * (BAY * 0.32), n, BASEMENT_M + 0.6, FLOOR1_M - 3.0, None,
                         0.75, C.M.limestone_rusticated, C.M.glass_dark, n=10)
        # piano nobile: round-arched windows between pilasters
        C.arched_opening(b, q - t * (BAY * 0.26), q + t * (BAY * 0.26), n, FLOOR1_M + 1.0, FLOOR2_M - 2.6, None,
                         0.6, marble, C.M.glass_dark, n=10)
        C.pilaster(b, q + t * (BAY * 0.44), q + t * (BAY * 0.5), n, FLOOR1_M, FLOOR2_M + 1.4, 0.35, marble, cap_h=0.6)
    b.prism(coords, BASEMENT_M, BASEMENT_M + 0.3, C.M.limestone_rusticated, cap_bottom=False)
    objs.append(C.cornice(f"{ID}_belt", P, FLOOR1_M, [(0.3, 0.0), (0.55, 0.35), (0.3, 0.6)], marble))
    objs.append(C.cornice(f"{ID}_cornice", P, FLOOR2_M + 1.4, [(0.4, 0.0), (1.15, 0.75), (1.35, 1.25), (0.5, 1.9)], marble))
    C.balustrade(b, C.ring_coords(C.offset_polygon(P, -0.9)), ATTIC_M - 1.7, 1.7, marble, spacing=0.72,
                 baluster_r=0.1, rail_t=0.28)
    objs.append(b.build(f"{ID}_skin"))

    # ---- the projecting south portico over the entrance stair --------------------------------------------------
    b = C.MeshBuilder()
    runs = sorted(C.wall_runs(coords, south, tol_deg=50.0), key=lambda r: -r[1])
    pts, Lf = runs[0]
    mid, mt, mn = C.polyline_at(pts, Lf / 2)
    pw = 15.0
    C.steps(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, FLOOR1_M - 5.6, 12, (FLOOR1_M - 5.6) / 12, 0.4, gran,
            z_bottom=0.0)
    C.colonnade(b, mid - mt * (pw / 2 - 1.2), mid + mt * (pw / 2 - 1.2), mn, FLOOR1_M - 5.6, 10.6, 0.6, 6, marble,
                order="corinthian", stand_off=3.2, segments=12)
    C.entablature(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, FLOOR1_M + 5.0, 2.4, 4.2, marble, overhang=0.5)
    C.pediment(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, FLOOR1_M + 7.4, 3.4, 3.4, marble, tympanum=marble,
               cornice_t=0.4, overhang=0.4)
    objs.append(b.build(f"{ID}_portico"))

    # ---- the cupola: drum, colonnade, dome and the figure of Justice --------------------------------------------
    b = C.MeshBuilder()
    r = 5.2
    b.prism(C.ring_coords(C.rect(cx, cy, r * 2.4, r * 2.4)), ATTIC_M - 1.0, ATTIC_M + 1.6, marble)
    b.lathe([(r, 0.0), (r, DRUM_M - ATTIC_M - 1.6)], 16, marble, origin=(cx, cy, ATTIC_M + 1.6), smooth=True, cap=False)
    for k in range(12):                            # the colonnade around the lantern
        a = 2 * math.pi * k / 12
        C.column(b, cx + r * 0.92 * math.cos(a), cy + r * 0.92 * math.sin(a), DRUM_M, COLONNADE_M - DRUM_M - 0.8, 0.32,
                 marble, order="corinthian", segments=10, abacus=False)
    b.lathe([(r * 0.7, 0.0), (r * 0.7, COLONNADE_M - DRUM_M - 0.8)], 16, C.M.glass_dark, origin=(cx, cy, DRUM_M),
            smooth=True, cap=False)
    b.lathe([(r * 1.02, 0.0), (r * 1.02, 0.8)], 16, marble, origin=(cx, cy, COLONNADE_M - 0.8), smooth=True)
    C.dome(b, cx, cy, COLONNADE_M, r * 0.92, DOME_M - COLONNADE_M, cop, kind="ogee", segments=20)
    b.hull([(cx - 0.45, cy - 0.45, DOME_M), (cx + 0.45, cy - 0.45, DOME_M), (cx + 0.45, cy + 0.45, DOME_M),
            (cx - 0.45, cy + 0.45, DOME_M), (cx - 0.22, cy, TOP_M - 0.4), (cx + 0.22, cy, TOP_M - 0.4),
            (cx, cy, TOP_M)], cop)
    objs.append(b.build(f"{ID}_cupola"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TOP_M, name="New York City Hall", lp_number="LP-01437",
             height_source="LiDAR height_roof for BIN 1079147 = 36.57 m (top of the cupola and the figure of Justice); plan 216 x 105 ft = 65.8 x 32.0 m [Wikipedia / LPC LP-1437]",
             fidelity_statement=(
                 "Exact: real footprint (matching the published 216 x 105 ft to within 0.6 m), 36.6 m to the top of "
                 "Justice, the arcaded rusticated ground storey, the piano nobile with pilasters and round-arched "
                 "windows, the balustraded roof line, the projecting south portico with a raised stair, colonnade, "
                 "entablature and pediment, and the colonnaded cupola with an ogee dome. Inferred (+-1.5 m): every "
                 "intermediate level — storey heights, attic and the three cupola stages — since no per-element height "
                 "schedule is published. Simplified: the figure of Justice is a massing solid and the cupola and pediment "
                 "ornament are omitted. Materials are the present white marble on all four elevations (the 1812 building "
                 "had brownstone at the rear). Not modelled: the rotunda, the Governor's Room and the double cantilevered "
                 "stair (designated interiors), and City Hall Park."),
             notes="BIN 1079146 on the same site is the Tweed Courthouse, not City Hall; the landmark parquet resolves 'city_hall' to that BIN, which this model deliberately does not use",
             dimensions={"top_m": TOP_M, "basement_m": BASEMENT_M, "floor1_m": FLOOR1_M, "floor2_m": FLOOR2_M,
                         "attic_m": ATTIC_M, "cupola_drum_m": DRUM_M, "cupola_colonnade_m": COLONNADE_M,
                         "dome_m": DOME_M, "published_plan_m": [65.8, 32.0], "portico_columns": 6})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 180, "elevation_deg": "street", "distance": 92, "target_z": 20, "fov_deg": 64},
        {"view": "aerial", "azimuth_deg": 200, "elevation_deg": 26, "distance": 175, "fov_deg": 48, "target_z": 18},
    ])


if __name__ == "__main__":
    main()
