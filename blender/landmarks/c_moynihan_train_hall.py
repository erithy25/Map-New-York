"""Moynihan Train Hall in the James A. Farley Building — 421 Eighth Avenue (BIN 1084820, LP-0233).
McKim, Mead & White, 1912-13 (as the General Post Office); train hall by Skidmore, Owings & Merrill, 2021.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (26,037 m2) — the full two-block site between Eighth and Ninth Avenues and West
  31st and 33rd Streets, 255.9 x 211.6 m. Eighth Avenue is east (local +x).
* Height [OTI LiDAR; LP-0233]: **31.2 m** to the top of the attic over the Eighth Avenue colonnade; the cornice is
  at 24.0 m and the granite base at 8.5 m.
* Eighth Avenue colonnade [LPC designation report LP-0233]: **20 Corinthian columns 53 ft = 16.15 m tall** on a
  6.4 m module across a 100 m front, over a broad flight of granite steps rising 8.5 m; the entablature carries the
  inscription frieze ("Neither snow nor rain...") 1.5 m high.
* Train hall [SOM 2021]: the former mail sorting room is roofed by four steel-and-glass vaults springing from the
  original 1913 steel trusses; the skylight is **92 ft = 28.0 m** above the hall floor and the hall is
  approximately 45 x 55 m on plan.
* Material [LP-0233]: Milford pink granite throughout. Footprint from [NYC Building Footprints, OTI 5zhs-2jue];
  storey heights derived from the [OTI LiDAR] roof height and the published storey count.

Fidelity: real footprint; the 20-column, 16.15 m Corinthian colonnade with its entablature, inscription frieze and
granite steps; the 24.0 m cornice and 31.2 m attic; and SOM's four glazed vaults over the train hall reaching
28.0 m above the hall floor are modelled as geometry. Inferred (stated): the position and extent of the train hall
within the block (centred on the polygon, at the published approximate plan size) and the storey heights. NOT
modelled: the interiors and the concourse below, the carved eagles and the inscription lettering, the 1930s Ninth
Avenue annex's later alterations, and the rooftop plant.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_moynihan_train_hall"
BIN = 1084820
ATTIC = 31.2
CORNICE = 24.0
BASE_TOP = 8.5
COLUMNS, COLUMN_H, COLUMN_MODULE = 20, 16.15, 6.4
HALL_W, HALL_D, SKYLIGHT_Z = 45.0, 55.0, 28.0


def build():
    C.reset()
    cc.materials(["granite_pink", "granite_grey", "limestone", "glass_clear", "glass_dark", "steel_nirosta",
                  "roof_grey", "roof_dark", "bronze"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    x0, y0, x1, y1 = P.bounds
    objs: list = []

    # the train hall occupies the old mail-sorting courtyard, so it is a real void in the block above the base
    hcx, hcy = (x0 + x1) / 2, (y0 + y1) / 2
    hall = C.rect(hcx, hcy, HALL_W, HALL_D)
    P_body = C._orient(P.difference(hall), 1.0)
    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_TOP, C.M.granite_pink, material_top=C.M.roof_dark))
    fen = C.Fenestration(bay_w=COLUMN_MODULE, window_frac=0.45, recess=0.6, spandrel_h=1.1, spandrel_proud=0.14,
                         pier="granite_pink", spandrel="granite_pink", glass="glass_dark",
                         floor_z=[BASE_TOP, BASE_TOP + 7.0, BASE_TOP + 12.0, CORNICE - 2.4], window_h=4.6)
    objs += C.tower_tier(f"{ID}_body", P_body, BASE_TOP, CORNICE - 2.4, fen, roof_material="roof_grey", parapet_h=0.0)
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE - 2.4,
                          [(0.7, 0.0), (2.1, 1.4), (2.1, 2.0), (0.8, 2.4)], C.M.granite_pink))
    objs.append(C.prism(f"{ID}_attic", C._orient(C.offset_polygon(P, -1.2).difference(hall), 1.0), CORNICE,
                        ATTIC, C.M.granite_pink, material_top=C.M.roof_grey, role="mass"))

    # ---- the Eighth Avenue colonnade and steps -------------------------------------------------------------------
    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(coords, 0.0)
    mid = (p0 + p1) / 2
    span = COLUMN_MODULE * (COLUMNS - 1)
    for k in range(COLUMNS):
        u = -span / 2 + COLUMN_MODULE * k
        q = mid + t * u + n * 4.4
        C.column(b, q[0], q[1], BASE_TOP, COLUMN_H, 0.86, C.M.granite_pink, order="corinthian", segments=16)
    zc = BASE_TOP + COLUMN_H
    b.box_from_to(mid - t * (span / 2 + 3.0), mid + t * (span / 2 + 3.0), n, 5.6, zc, zc + 1.4, C.M.granite_pink)
    b.box_from_to(mid - t * (span / 2 + 3.0), mid + t * (span / 2 + 3.0), n, 5.4, zc + 1.4, zc + 2.9,
                  C.M.limestone)                                            # the inscription frieze
    b.box_from_to(mid - t * (span / 2 + 3.4), mid + t * (span / 2 + 3.4), n, 6.0, zc + 2.9, zc + 4.3,
                  C.M.granite_pink)
    for k in range(24):                                                     # the granite steps
        z = BASE_TOP * (k + 1) / 24
        d = 4.4 + 0.55 * (24 - k)
        b.box_from_to(mid - t * (span / 2 + 5.0), mid + t * (span / 2 + 5.0), n, d, 0.0, z, C.M.granite_grey)
    objs.append(b.build(f"{ID}_colonnade"))

    # ---- SOM's four glazed vaults over the train hall -------------------------------------------------------------
    b = C.MeshBuilder()
    b.prism(C.ring_coords(hall), 0.0, CORNICE + 0.6, C.M.granite_pink, cap_top=False, cap_bottom=False)
    for q in range(4):
        cxq = hcx - HALL_W / 2 + HALL_W * (q + 0.5) / 4
        w = HALL_W / 4
        prof = []
        for j in range(11):
            u = j / 10.0
            zz = SKYLIGHT_Z - 8.4 + 8.4 * math.sin(math.pi * u)     # the skylight crown lands on SKYLIGHT_Z
            prof.append((cxq - w / 2 + w * u, zz))
        for j in range(10):
            (xa, za), (xb, zb) = prof[j], prof[j + 1]
            b.quad((xa, hcy - HALL_D / 2, za), (xb, hcy - HALL_D / 2, zb),
                   (xb, hcy + HALL_D / 2, zb), (xa, hcy + HALL_D / 2, za), C.M.glass_clear)
            for yy in (hcy - HALL_D / 2, hcy + HALL_D / 2):
                b.hull([(xa - 0.16, yy, za), (xa + 0.16, yy, za), (xb - 0.16, yy, zb), (xb + 0.16, yy, zb),
                        (xa - 0.16, yy, za - 0.5), (xa + 0.16, yy, za - 0.5),
                        (xb - 0.16, yy, zb - 0.5), (xb + 0.16, yy, zb - 0.5)], C.M.steel_nirosta)
        for k in range(9):                                                  # the transverse trusses
            yy = hcy - HALL_D / 2 + HALL_D * k / 8
            for j in range(10):
                (xa, za), (xb, zb) = prof[j], prof[j + 1]
                b.hull([(xa - 0.12, yy - 0.12, za), (xa + 0.12, yy + 0.12, za),
                        (xb - 0.12, yy - 0.12, zb), (xb + 0.12, yy + 0.12, zb),
                        (xa - 0.12, yy + 0.12, za - 0.35), (xb + 0.12, yy - 0.12, zb - 0.35)], C.M.steel_nirosta)
    objs.append(C.tag(b.build(f"{ID}_train_hall_vaults"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint of the whole two-block site; the 20-column Corinthian "
                          "colonnade of 53 ft = 16.15 m columns on a 6.4 m module over granite steps rising 8.5 m; "
                          "the entablature and inscription frieze; the 24.0 m cornice and 31.2 m attic (OTI "
                          "LiDAR, LP-0233); SOM's four glazed vaults over the train hall reaching the published "
                          "92 ft = 28.0 m above the hall floor. Inferred (stated): the train hall's position and "
                          "45 x 55 m extent within the block (centred on the polygon at the published approximate "
                          "size) and the storey heights. Not modelled: interiors and the concourse below, the "
                          "carved eagles and inscription lettering, the Ninth Avenue annex's later alterations, "
                          "rooftop plant."),
                      dimensions={"attic_m": ATTIC, "cornice_m": CORNICE, "base_top_m": BASE_TOP,
                                  "colonnade_columns": COLUMNS, "column_h_m": COLUMN_H,
                                  "column_module_m": COLUMN_MODULE, "train_hall_plan_m": [HALL_W, HALL_D],
                                  "skylight_above_floor_m": SKYLIGHT_Z})
    cc.render(ID, [
        {"view": "eighth_avenue", "azimuth_deg": 100, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 10},
        {"view": "aerial", "azimuth_deg": 120, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
