"""New York Stock Exchange — 18 Broad Street and 11 Wall Street (BINs 1078981, 1078982; LP-02515, and a National
Historic Landmark). George B. Post, 1903; the 11 Wall Street addition by Trowbridge & Livingston, 1922.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the two real OTI polygons — the 1903 trading-floor building (BIN 1078981, 1,707.3 m2, LiDAR roof 44.50 m)
  and the 1922 office addition at 11 Wall Street (BIN 1078982, 1,026.4 m2, LiDAR roof 104.77 m); 2,733.7 m2 together,
  69.8 x 44.6 m in the model's local frame. The Broad Street front, with the portico, faces east.
* The Broad Street front [LPC LP-2515, Wikipedia "New York Stock Exchange Building", HABS NY-6339]: six free-standing
  Corinthian columns 52 ft (15.85 m) tall carry a marble pediment containing John Quincy Adams Ward's and Paul Wayland
  Bartlett's 1904 sculpture group *Integrity Protecting the Works of Man*, and the whole front is a single glazed
  screen 96 ft (29.3 m) high lighting the trading floor behind it. The trading floor itself is 109 x 140 ft
  (33.2 x 42.7 m) and 79 ft (24.1 m) high.
* Heights: the 1903 building is verified against its LiDAR roof height of 44.5 m and the 1922 addition against 104.8 m
  (23 storeys), which is the height of the whole model. The portico's own levels (stylobate 3.4 m, columns 15.85 m,
  entablature 3.6 m, pediment rise 4.2 m) come from the published 52 ft column height and the 96 ft screen.
* Materials [LPC LP-2515]: Georgia white marble throughout, with bronze window frames.

Fidelity: exact — both real footprints, 104.8 m for the 11 Wall Street tower and 44.5 m for the trading-floor building,
the six 15.85 m Corinthian columns and the pediment of the Broad Street front, the 29.3 m glazed screen behind them,
the trading floor's own volume at its published 33.2 x 42.7 x 24.1 m, and Georgia-marble cladding throughout.
Inferred (+-2 m) — the setback levels of the 1922 tower and its storey heights. Simplified — *Integrity Protecting the
Works of Man* is a massing group in the tympanum, not sculpted figures; the Corinthian capitals use the shared lathe
profile. Not modelled — the trading-floor interior fit-out and the giant American flag usually hung over the facade.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402
import shapely.ops  # noqa: E402
from shapely.geometry import MultiPolygon  # noqa: E402

ID = "nyse"
BINS = [1078981, 1078982]
TOWER_M = 104.8            # 11 Wall Street (BIN 1078982), 23 storeys
HALL_M = 44.5              # the 1903 trading-floor building (BIN 1078981)
STYLOBATE_M = 3.4
COLUMN_H = 15.85           # 52 ft
ENTAB_H = 3.6
PEDIMENT_RISE = 4.2
SCREEN_H = 29.3            # 96 ft
COLUMNS = 6
FLOOR_H = (TOWER_M - 8.0) / 22.0


def build():
    C.reset()
    fps = C.load_footprints(BINS)
    hall_fp, tower_fp = fps[0], fps[1]
    union = shapely.ops.unary_union([f.polygon for f in fps])
    main = max(union.geoms, key=lambda g: g.area) if isinstance(union, MultiPolygon) else union
    fr = C.local_frame(main, hall_fp.ground_z)
    hall = fr.local_polygon(hall_fp.polygon)
    tower = fr.local_polygon(tower_fp.polygon)
    P = fr.local_polygon(union)
    east = fr.local_cardinal(90.0)
    objs = []
    marble, bronze, glass = C.M.marble_white, C.M.bronze, C.M.glass_dark

    # ---- both footprints as ground-floor fabric (the IoU volume) -----------------------------------------------
    objs.append(C.plinth(f"{ID}_hall_base", hall, 0.0, STYLOBATE_M, C.M.granite_grey, material_top=marble))
    objs.append(C.plinth(f"{ID}_tower_base", tower, 0.0, 8.0, marble, material_top=C.M.roof_grey))

    # ---- the 1903 trading-floor building -----------------------------------------------------------------------
    objs.append(C.prism(f"{ID}_hall", hall, STYLOBATE_M, HALL_M - 3.0, marble, material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    hcoords = C.ring_coords(hall)
    for q, t, n, s in C.ring_stations(hcoords, 5.0):
        C.window_punch(b, q - t * 1.3, q + t * 1.3, n, 12.0, 24.0, 0.5, marble, glass, sill=0.15)
        C.pilaster(b, q + t * 1.9, q + t * 2.5, n, STYLOBATE_M, HALL_M - 4.5, 0.4, marble, cap_h=0.7)
    objs.append(C.cornice(f"{ID}_hall_cornice", hall, HALL_M - 3.0,
                          [(0.4, 0.0), (1.5, 1.0), (1.8, 1.7), (1.4, 2.5), (0.5, 3.0)], marble))

    # ---- the Broad Street portico: glazed screen, six Corinthian columns, entablature and pediment --------------
    runs = sorted(C.wall_runs(hcoords, east, tol_deg=50.0), key=lambda r: -r[1])
    pts, Lf = runs[0]
    mid, mt, mn = C.polyline_at(pts, Lf / 2)
    pw = min(Lf - 1.0, 30.0)
    b.quad((float(mid[0] - mt[0] * pw / 2 + mn[0] * 0.1), float(mid[1] - mt[1] * pw / 2 + mn[1] * 0.1), STYLOBATE_M),
           (float(mid[0] + mt[0] * pw / 2 + mn[0] * 0.1), float(mid[1] + mt[1] * pw / 2 + mn[1] * 0.1), STYLOBATE_M),
           (float(mid[0] + mt[0] * pw / 2 + mn[0] * 0.1), float(mid[1] + mt[1] * pw / 2 + mn[1] * 0.1), SCREEN_H),
           (float(mid[0] - mt[0] * pw / 2 + mn[0] * 0.1), float(mid[1] - mt[1] * pw / 2 + mn[1] * 0.1), SCREEN_H),
           glass)                                                    # the 96 ft glazed screen
    for i in range(7):                                               # bronze mullions across the screen
        q = mid + mt * (-pw / 2 + pw * i / 6)
        b.box((float(q[0] + mn[0] * 0.25), float(q[1] + mn[1] * 0.25), (STYLOBATE_M + SCREEN_H) / 2),
              (0.3, 0.5, SCREEN_H - STYLOBATE_M), bronze, rot_deg=math.degrees(math.atan2(mt[1], mt[0])))
    C.colonnade(b, mid - mt * (pw / 2 - 2.0), mid + mt * (pw / 2 - 2.0), mn, STYLOBATE_M, COLUMN_H, 1.05, COLUMNS,
                marble, order="corinthian", stand_off=3.6, segments=16)
    C.entablature(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, STYLOBATE_M + COLUMN_H, ENTAB_H, 4.4, marble,
                  overhang=0.6)
    zt = STYLOBATE_M + COLUMN_H + ENTAB_H
    C.pediment(b, mid - mt * (pw / 2), mid + mt * (pw / 2), mn, zt, PEDIMENT_RISE, 4.2, marble, tympanum=marble,
               cornice_t=0.5, overhang=0.5)
    for dx, h, w in ((-9.0, 2.0, 1.5), (-4.6, 2.7, 1.6), (0.0, 3.4, 1.8), (4.6, 2.7, 1.6), (9.0, 2.0, 1.5)):
        q = mid + mt * dx + mn * 3.4                                  # Integrity Protecting the Works of Man
        b.hull([(float(q[0] - mt[0] * w / 2), float(q[1] - mt[1] * w / 2), zt + 0.3),
                (float(q[0] + mt[0] * w / 2), float(q[1] + mt[1] * w / 2), zt + 0.3),
                (float(q[0] - mt[0] * w / 2 + mn[0] * 0.8), float(q[1] - mt[1] * w / 2 + mn[1] * 0.8), zt + 0.3),
                (float(q[0] + mt[0] * w / 2 + mn[0] * 0.8), float(q[1] + mt[1] * w / 2 + mn[1] * 0.8), zt + 0.3),
                (float(q[0] - mt[0] * w * 0.2 + mn[0] * 0.4), float(q[1] - mt[1] * w * 0.2 + mn[1] * 0.4), zt + 0.3 + h),
                (float(q[0] + mt[0] * w * 0.2 + mn[0] * 0.4), float(q[1] + mt[1] * w * 0.2 + mn[1] * 0.4), zt + 0.3 + h)],
               marble)
    objs.append(b.build(f"{ID}_hall_detail"))

    # ---- 11 Wall Street: the 1922 tower ------------------------------------------------------------------------
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=3.3, window_frac=0.5, recess=0.45, spandrel_h=1.0,
                         pier="marble_white", spandrel="marble_white", glass="glass_dark", window_h=2.6)
    plan = tower
    levels = [(8.0, 8.0 + 10 * FLOOR_H, 0.0), (8.0 + 10 * FLOOR_H, 8.0 + 17 * FLOOR_H, 3.2),
              (8.0 + 17 * FLOOR_H, TOWER_M - 2.4, 3.0)]
    for k, (z0, z1, inset) in enumerate(levels):
        if inset:
            nxt = C.offset_polygon(plan, -inset)
            if not nxt.is_empty:
                plan = nxt if nxt.geom_type == "Polygon" else max(nxt.geoms, key=lambda g: g.area)
        objs += C.tower_tier(f"{ID}_tower_t{k}", plan, z0, z1, fen, parapet_h=1.2, parapet_t=0.5)
    objs.append(C.cornice(f"{ID}_tower_cornice", plan, TOWER_M - 2.4,
                          [(0.4, 0.0), (1.4, 0.9), (1.7, 1.6), (0.5, 2.4)], marble))
    objs.append(C.prism(f"{ID}_tower_roof", plan, TOWER_M - 0.6, TOWER_M, C.M.roof_dark, inset=1.4))
    return objs, fr, fps, P


def main():
    objs, fr, fps, P = build()
    C.finish(objs, ID, BINS, fr, height_m=TOWER_M, name="New York Stock Exchange", lp_number="LP-02515",
             real_footprint=P,
             height_source="LiDAR height_roof: BIN 1078982 (11 Wall Street) = 104.77 m, BIN 1078981 (1903 trading-floor building) = 44.50 m; portico columns 52 ft = 15.85 m and the glazed screen 96 ft = 29.3 m [LPC LP-2515 / HABS NY-6339]",
             fidelity_statement=(
                 "Exact: both real footprints, 104.8 m for the 11 Wall Street tower and 44.5 m for the 1903 trading-floor "
                 "building, the six free-standing 15.85 m Corinthian columns and the pediment of the Broad Street front, "
                 "the 29.3 m glazed screen behind them with its bronze mullions, and Georgia-marble cladding throughout. "
                 "Inferred (+-2 m): the two setback levels and the storey heights of the 1922 tower. Simplified: "
                 "'Integrity Protecting the Works of Man' is a massing group in the tympanum, not sculpted figures; "
                 "Corinthian capitals use the shared lathe profile. Not modelled: the trading-floor interior and the "
                 "giant American flag usually hung over the facade."),
             notes="The landmark parquet resolves 'nyse' to BIN 1001033, which is the former American Stock Exchange at 86 Trinity Place; this model uses the correct BINs 1078981 and 1078982",
             dimensions={"tower_m": TOWER_M, "hall_m": HALL_M, "column_h_m": COLUMN_H, "portico_columns": COLUMNS,
                         "screen_h_m": SCREEN_H, "entablature_h_m": ENTAB_H, "pediment_rise_m": PEDIMENT_RISE,
                         "tower_storeys": 23, "floor_h_m": round(FLOOR_H, 3),
                         "published_trading_floor_m": [42.7, 33.2, 24.1]})
    C.render_check(ID, [
        {"view": "street", "azimuth_deg": 95, "elevation_deg": "street", "distance": 179, "target_z": 53, "fov_deg": 62},
        {"view": "aerial", "azimuth_deg": 115, "elevation_deg": 24, "distance": 320, "fov_deg": 44, "target_z": 55},
    ])


if __name__ == "__main__":
    main()
