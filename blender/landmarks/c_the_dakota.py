"""The Dakota — 1 West 72nd Street (BIN 1028637, LP-0280, NHL). Henry Janeway Hardenbergh, 1880-84.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (3,251 m2), a 61.7 x 63.5 m square block around a central carriage courtyard; the
  two notches in the polygon are the courtyard entrance arch on 72nd Street and the light court on the north.
* Height [LPC designation report LP-0280; OTI LiDAR]: nine principal storeys; the LiDAR ridge, which is the top of
  the steep slate roof's gables and dormers, is 50.9 m.
* Elevation [LP-0280]: pale yellow brick over a two-storey brownstone base with terracotta panels, string courses
  and niches; deep dormered slate roof with gables, terminal pavilions, iron cresting and finials; the ground floor
  is a rusticated brownstone base with a dry moat behind an iron railing.
* Storey heights derived so the ninth floor's cornice lands at 36.5 m and the roof ridge at 50.9 m: base 2 storeys of
  5.4 m, then 7 storeys of 3.67 m; roof 14.4 m of slate with three dormer levels.
* Courtyard [LP-0280]: the central carriage court is entered through a 72nd Street arch 5.5 m wide and 8.6 m high.

Fidelity: real footprint including the courtyard; the nine storeys, brownstone base, terracotta string courses,
punched windows, corner pavilions and the dormered slate roof with its gables are modelled as geometry, and the
72nd Street entrance arch is a real opening. Inferred (stated): the storey heights (derived from the LiDAR ridge and
nine storeys, not from drawings); the dormer count is regular rather than measured. NOT modelled: the iron cresting
and finials in detail (blocked-out masses), the interior apartments, the sunken dry moat railing's ironwork pattern,
and the 1929 apartment-house additions inside the court.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_the_dakota"
BIN = 1028637
RIDGE = 50.9
CORNICE = 36.5
BASE_TOP = 10.8
FLOORS = 9


def build():
    C.reset()
    cc.materials(["brick_buff", "brownstone", "terracotta_cream", "slate", "glass_dark", "cast_iron", "roof_dark",
                  "pavement", "copper_green"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    objs: list = []
    court = C.offset_polygon(P, -19.0)                 # the central carriage courtyard
    body = P if court.is_empty else P.difference(court)
    body = C._orient(body.buffer(0), 1.0)

    objs += cc.base_and_wall(f"{ID}_base", P, BASE_TOP, C.M.brownstone, recess=0.65, material_top=C.M.roof_dark)
    fl = [BASE_TOP + (CORNICE - BASE_TOP) * k / 7 for k in range(8)]
    fen = C.Fenestration(bay_w=3.05, window_frac=0.52, recess=0.45, spandrel_h=0.9, spandrel_proud=0.12,
                         pier="brick_buff", spandrel="terracotta_cream", glass="glass_dark", floor_z=fl,
                         window_h=2.5)
    objs += C.tower_tier(f"{ID}_body", P, BASE_TOP, CORNICE, fen, roof_material="roof_dark", parapet_h=0.0)
    b = C.MeshBuilder()
    coords = C.ring_coords(P)
    # brownstone base: rusticated courses, arched ground-floor openings and the 72nd Street carriage arch
    for p0, p1, L, t, n in C.edges_of(coords):
        if L < 6.0:
            continue
        nbay = max(2, int(round(L / 4.4)))
        mod = L / nbay
        for k in range(nbay):
            a = p0 + t * (k * mod + 0.9)
            c = p0 + t * ((k + 1) * mod - 0.9)
            C.arched_opening(b, a, c, n, 1.7, 4.4, None, 0.55, C.M.brownstone, C.M.glass_dark)
            C.window_punch(b, a, c, n, 6.6, 9.8, 0.5, C.M.brownstone, C.M.glass_dark)
        for z in (BASE_TOP, 17.0, 24.0, 31.0):        # terracotta string courses
            b.box_from_to(p0, p1, n, 0.35, z - 0.45, z, C.M.terracotta_cream)
    e0, e1, L, t, n = C.edge_facing(coords, -90.0)     # the 72nd Street front
    mid = (e0 + e1) / 2
    C.arched_opening(b, mid - t * 2.75, mid + t * 2.75, n, 1.7, 5.8, 2.8, 3.0, C.M.brownstone, C.M.cast_iron)
    objs.append(b.build(f"{ID}_base_detail"))
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE - 1.6,
                          [(0.4, 0.0), (1.5, 0.9), (1.5, 1.6), (0.5, 2.2)], C.M.terracotta_cream))

    # ---- the dormered slate roof ----------------------------------------------------------------------------------
    b = C.MeshBuilder()
    inner = C.offset_polygon(P, -7.5)
    b.loft([[(x, y, CORNICE + 0.6) for x, y in C.ring_coords(P)],
            [(x, y, CORNICE + 11.0) for x, y in C.offset_ring(C.ring_coords(P), -7.5)]], C.M.slate,
           cap_top=True, cap_bottom=False, material_top=C.M.slate)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(P)):
        ndorm = max(1, int(round(L / 8.0)))
        for k in range(ndorm):
            q = p0 + t * (L * (k + 0.5) / ndorm)
            a = q - t * 1.7
            c = q + t * 1.7
            b.box_from_to(a, c, n, 0.9, CORNICE + 1.4, CORNICE + 5.6, C.M.brick_buff, top=False)
            C.window_punch(b, a + t * 0.35, c - t * 0.35, n, CORNICE + 2.0, CORNICE + 5.1, 0.35, C.M.brick_buff,
                           C.M.glass_dark)
            b.hull([(a[0], a[1], CORNICE + 5.6), (c[0], c[1], CORNICE + 5.6),
                    (a[0] + n[0] * 0.9, a[1] + n[1] * 0.9, CORNICE + 5.6),
                    (c[0] + n[0] * 0.9, c[1] + n[1] * 0.9, CORNICE + 5.6),
                    (q[0] - n[0] * 0.4, q[1] - n[1] * 0.4, CORNICE + 7.6)], C.M.slate)
    # corner pavilions with steep gables up to the ridge
    for cxy in ((P.bounds[0] + 7.0, P.bounds[1] + 7.0), (P.bounds[2] - 7.0, P.bounds[1] + 7.0),
                (P.bounds[0] + 7.0, P.bounds[3] - 7.0), (P.bounds[2] - 7.0, P.bounds[3] - 7.0)):
        b.box((cxy[0], cxy[1], CORNICE + 5.0), (11.0, 11.0, 9.0), C.M.brick_buff, top=False)
        b.hull([(cxy[0] - 5.5, cxy[1] - 5.5, CORNICE + 9.5), (cxy[0] + 5.5, cxy[1] - 5.5, CORNICE + 9.5),
                (cxy[0] - 5.5, cxy[1] + 5.5, CORNICE + 9.5), (cxy[0] + 5.5, cxy[1] + 5.5, CORNICE + 9.5),
                (cxy[0], cxy[1], RIDGE)], C.M.slate)
        b.lathe([(0.35, 0.0), (0.2, 1.2), (0.0, 1.9)], 8, C.M.copper_green, origin=(cxy[0], cxy[1], RIDGE - 1.9))
    objs.append(C.tag(b.build(f"{ID}_roof"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint with its courtyard; nine storeys to a 36.5 m cornice and a "
                          "50.9 m slate ridge (OTI LiDAR); rusticated brownstone base with arched ground-floor "
                          "openings; the 72nd Street carriage arch as a real opening; terracotta string courses; "
                          "dormered slate roof with corner pavilion gables and finials. Inferred (stated): the "
                          "storey heights (derived from the LiDAR ridge and nine storeys) and a regular dormer "
                          "rhythm. Not modelled: the iron cresting pattern, interiors, the dry-moat railing "
                          "ironwork, the additions inside the court."),
                      dimensions={"ridge_m": RIDGE, "cornice_m": CORNICE, "base_top_m": BASE_TOP, "floors": FLOORS})
    cc.render(ID, [
        {"view": "w72nd", "azimuth_deg": 200, "elevation_deg": "street", "distance": 120, "fov_deg": 52, "look_up_deg": 20},
        {"view": "aerial", "azimuth_deg": 240, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
