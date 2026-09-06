"""Federal Hall National Memorial — 26 Wall Street (BIN 1001020). Town & Davis with John Frazee, completed 1842 as the
United States Custom House, later the Sub-Treasury.

Dimensions used (source in brackets)
------------------------------------
* Footprint: real OTI polygon, 1,584.6 m2 — a rectangle 55.6 x 28.5 m in the model's local frame. The published
  dimensions of the Custom House are 200 x 90 ft (61.0 x 27.4 m) [National Park Service, Wikipedia "Federal Hall"];
  the OTI polygon matches the short dimension to 1.1 m and is 5.4 m shorter on the long one, which the model follows
  because the footprint is the measured fabric. The Wall Street front, with the portico, faces south.
* Composition [NPS, Wikipedia, HABS NY-5688]: a Greek Revival temple modelled on the Parthenon — an **octastyle**
  (eight-column) Doric portico on the Wall Street front over a broad flight of steps, a matching portico on the Pine
  Street front, a full Doric entablature and a plain pediment, and a shallow interior rotunda dome (not visible on the
  skyline). John Quincy Adams Ward's 1883 bronze *George Washington* stands on the steps: the figure is about 3.8 m
  tall on a granite pedestal of about 2.4 m.
* Heights: the LiDAR ``height_roof`` for the BIN is 19.31 m, which is the height this model is verified against. Within
  that, the stylobate is at 4.6 m (the top of the entrance stair), the Doric columns are 9.8 m tall, the entablature is
  2.6 m and the pediment rises 2.3 m — a Parthenon-derived proportion set that reproduces the published photographs;
  the individual levels are not published, so they are stated as inferred (+-0.8 m).
* Materials [NPS]: Tuckahoe marble throughout, granite steps, bronze statue.

Fidelity: exact — real footprint, 19.3 m overall height, the octastyle Doric porticoes on both the Wall Street and the
Pine Street fronts over broad granite stairs, the full Doric entablature and pediment, and the Washington statue at
3.8 m on a 2.4 m pedestal, in Tuckahoe marble. Inferred (+-0.8 m) — the stylobate, column, entablature and pediment
heights. Simplified — the Doric capitals use the shared lathe profile without flutes cut as geometry; the statue is a
bronze massing figure. Not modelled — the interior rotunda with its Corinthian colonnade and coffered dome (which is
not visible from outside), and the Wall Street subway entrance.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

ID = "federal_hall"
BINS = [1001020]
TOP_M = 19.3
STYLOBATE_M = 4.6
COLUMN_H = 9.8
ENTAB_H = 2.6
PEDIMENT_RISE = 2.3
COLUMNS = 8
STATUE_H = 3.8
PEDESTAL_H = 2.4


def build():
    C.reset()
    fp = C.load_footprint(ID)
    fr = C.local_frame(fp.polygon, fp.ground_z)
    P = fr.local_polygon(fp.polygon)
    minx, miny, maxx, maxy = P.bounds
    objs = []
    marble, gran, bronze = C.M.marble_white, C.M.granite_grey, C.M.bronze

    # ---- the cella: the whole footprint up to the entablature (the IoU volume) ----------------------------------
    cella_top = STYLOBATE_M + COLUMN_H
    objs.append(C.plinth(f"{ID}_base", P, 0.0, STYLOBATE_M, gran, material_top=marble))
    objs.append(C.prism(f"{ID}_cella", P, STYLOBATE_M, cella_top, marble, inset=0.0,
                        material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    for q, t, n, s in C.ring_stations(coords, 4.6):     # tall windows in the flanks
        C.window_punch(b, q - t * 1.1, q + t * 1.1, n, STYLOBATE_M + 1.4, STYLOBATE_M + 6.4, 0.5, marble,
                       C.M.glass_dark, sill=0.12)
    # the Doric entablature and the roof block right round the building
    objs.append(C.cornice(f"{ID}_entablature", P, cella_top,
                          [(0.25, 0.0), (0.25, ENTAB_H * 0.55), (0.75, ENTAB_H * 0.62), (0.9, ENTAB_H * 0.85),
                           (0.35, ENTAB_H)], marble))
    objs.append(C.prism(f"{ID}_roof", P, cella_top + ENTAB_H, TOP_M, marble, inset=0.9, material_top=C.M.roof_grey))

    # ---- the two octastyle porticoes (Wall Street and Pine Street fronts) ---------------------------------------
    for compass, statue in ((180.0, True), (0.0, False)):
        d = fr.local_cardinal(compass)
        runs = sorted(C.wall_runs(coords, d, tol_deg=45.0), key=lambda r: -r[1])
        if not runs:
            continue
        pts, Lf = runs[0]
        mid, mt, mn = C.polyline_at(pts, Lf / 2)
        pw = min(Lf - 1.0, 24.0)
        C.steps(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, STYLOBATE_M, 14, STYLOBATE_M / 14, 0.42, gran,
                z_bottom=0.0)
        C.colonnade(b, mid - mt * (pw / 2 - 1.6), mid + mt * (pw / 2 - 1.6), mn, STYLOBATE_M, COLUMN_H, 0.72,
                    COLUMNS, marble, order="doric", stand_off=4.4, segments=16)
        C.entablature(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, cella_top, ENTAB_H, 5.4, marble, overhang=0.5)
        C.pediment(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, cella_top + ENTAB_H, PEDIMENT_RISE, 5.0, marble,
                   tympanum=marble, cornice_t=0.42, overhang=0.4)
        if statue:
            q = mid + mn * 8.5
            b.box((float(q[0]), float(q[1]), PEDESTAL_H / 2), (2.0, 2.0, PEDESTAL_H), gran,
                  rot_deg=math.degrees(math.atan2(mt[1], mt[0])))
            zs = PEDESTAL_H
            b.hull([(float(q[0] - mt[0] * 0.55 - mn[0] * 0.4), float(q[1] - mt[1] * 0.55 - mn[1] * 0.4), zs),
                    (float(q[0] + mt[0] * 0.55 - mn[0] * 0.4), float(q[1] + mt[1] * 0.55 - mn[1] * 0.4), zs),
                    (float(q[0] - mt[0] * 0.55 + mn[0] * 0.5), float(q[1] - mt[1] * 0.55 + mn[1] * 0.5), zs),
                    (float(q[0] + mt[0] * 0.55 + mn[0] * 0.5), float(q[1] + mt[1] * 0.55 + mn[1] * 0.5), zs),
                    (float(q[0] - mt[0] * 0.36), float(q[1] - mt[1] * 0.36), zs + STATUE_H * 0.72),
                    (float(q[0] + mt[0] * 0.36), float(q[1] + mt[1] * 0.36), zs + STATUE_H * 0.72),
                    (float(q[0] + mn[0] * 0.7), float(q[1] + mn[1] * 0.7), zs + STATUE_H * 0.55),
                    (float(q[0]), float(q[1]), zs + STATUE_H)], bronze)
    objs.append(b.build(f"{ID}_porticoes"))
    return objs, fr, fp


def main():
    objs, fr, fp = build()
    C.finish(objs, ID, BINS, fr, height_m=TOP_M, name="Federal Hall National Memorial",
             height_source="LiDAR height_roof for BIN 1001020 = 19.31 m; published plan 200 x 90 ft = 61.0 x 27.4 m [NPS / Wikipedia]",
             fidelity_statement=(
                 "Exact: real footprint, 19.3 m overall height, octastyle Doric porticoes on both the Wall Street and the "
                 "Pine Street fronts over broad granite stairs, a full Doric entablature and pediment, and J. Q. A. Ward's "
                 "Washington at 3.8 m on a 2.4 m pedestal, in Tuckahoe marble. Inferred (+-0.8 m): the stylobate (4.6 m), "
                 "column (9.8 m), entablature (2.6 m) and pediment (2.3 m) heights, which are not published individually. "
                 "Simplified: Doric capitals use the shared lathe profile and the shafts are not fluted as geometry; the "
                 "statue is a bronze massing figure. Not modelled: the interior rotunda with its Corinthian colonnade and "
                 "coffered dome (not visible from outside) and the subway entrance."),
             notes="The OTI footprint is 5.4 m shorter than the published 200 ft; the model follows the measured footprint",
             dimensions={"top_m": TOP_M, "stylobate_m": STYLOBATE_M, "column_h_m": COLUMN_H, "entablature_h_m": ENTAB_H,
                         "pediment_rise_m": PEDIMENT_RISE, "portico_columns": COLUMNS, "porticoes": 2,
                         "statue_h_m": STATUE_H, "statue_pedestal_h_m": PEDESTAL_H,
                         "published_plan_m": [61.0, 27.4], "footprint_plan_m": [55.6, 28.5]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 180, "elevation_deg": "street", "distance": 68, "target_z": 12, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 200, "elevation_deg": 26, "distance": 105, "fov_deg": 48, "target_z": 11},
    ])


if __name__ == "__main__":
    main()
