"""Brooklyn Museum — 200 Eastern Parkway (BIN 3029667, LP-0057). McKim, Mead & White, 1893-1927;
Polshek Partnership glass entrance pavilion, 2004.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (7,760 m2), 159.4 x 117.2 m; Eastern Parkway is north (local +y).
* Height [OTI LiDAR / OSM]: 50.0 m to the top of the dome over the central pavilion; the main cornice of the
  Beaux-Arts block is at 27.0 m over five storeys.
* Eastern Parkway front [LPC designation report LP-0057]: a central pavilion with a hexastyle Ionic portico of
  **six columns 12.5 m tall** carrying a pediment, flanked by long wings whose upper storey is an **engaged Ionic
  colonnade**; the parapet above carries **30 allegorical figures by Daniel Chester French and others** (their
  pedestals are modelled; the figures are not).
* Entrance [Polshek 2004]: the original grand stair was removed in 1934 and replaced in 2004 by a fan-shaped glass
  pavilion 34.0 m wide and 12.0 m high with a stepped plaza and fountain in front.
* Material [LP-0057]: Indiana limestone over a granite base.

Fidelity: real footprint; the 50.0 m dome, the 27.0 m cornice, the hexastyle Ionic portico with its pediment, the
engaged colonnade of the wings, the parapet pedestals and the 2004 glass entrance pavilion are modelled as geometry.
Inferred (stated): the storey heights (from the LiDAR cornice height and five published storeys), the column
spacing of the wing colonnade, and the dome profile (from photographs). NOT modelled: the 30 allegorical figures
(their pedestals only), the carved pediment sculpture, the interiors and the sculpture garden.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_brooklyn_museum"
BIN = 3029667
DOME_TOP = 50.0
CORNICE = 27.0
BASE_TOP = 5.5
COLUMN_H = 12.5
PAVILION_W, PAVILION_H = 34.0, 12.0


def build():
    C.reset()
    cc.materials(["limestone", "granite_grey", "glass_clear", "glass_dark", "roof_grey", "roof_dark", "copper_green",
                  "pavement", "steel_dark"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_TOP, C.M.granite_grey, material_top=C.M.roof_dark))
    fl = [BASE_TOP + (CORNICE - 2.2 - BASE_TOP) * k / 4 for k in range(5)]
    fen = C.Fenestration(bay_w=4.6, window_frac=0.5, recess=0.5, spandrel_h=1.0, spandrel_proud=0.14,
                         pier="limestone", spandrel="limestone", glass="glass_dark", floor_z=fl, window_h=3.2)
    objs += C.tower_tier(f"{ID}_body", P, BASE_TOP, CORNICE - 2.2, fen, roof_material="roof_grey", parapet_h=0.0)
    objs.append(C.cornice(f"{ID}_cornice", P, CORNICE - 2.2,
                          [(0.6, 0.0), (2.0, 1.2), (2.0, 1.8), (0.7, 2.2)], C.M.limestone))

    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(coords, 90.0)        # the Eastern Parkway (north) front
    mid = (p0 + p1) / 2
    # the hexastyle Ionic portico
    for k in range(6):
        u = -12.5 + 5.0 * k
        q = mid + t * u + n * 4.2
        C.column(b, q[0], q[1], BASE_TOP, COLUMN_H, 0.72, C.M.limestone, order="ionic", segments=16)
    zc = BASE_TOP + COLUMN_H
    b.box_from_to(mid - t * 16.0, mid + t * 16.0, n, 5.4, zc, zc + 2.4, C.M.limestone)
    C.pediment(b, mid - t * 16.0, mid + t * 16.0, n, zc + 2.4, 4.6, 4.8, C.M.limestone, cornice_t=0.5, overhang=0.8)
    # the engaged Ionic colonnade of the wings, and the parapet pedestals
    for side in (-1.0, 1.0):
        for k in range(9):
            u = side * (20.0 + 5.0 * k)
            if abs(u) > L / 2 - 4.0:
                continue
            q = mid + t * u + n * 0.6
            C.column(b, q[0], q[1], BASE_TOP + 9.0, COLUMN_H, 0.6, C.M.limestone, order="ionic", segments=12,
                     abacus=False)
    for pa, pb, LL, tt, nn in C.edges_of(coords):
        npad = max(2, int(round(LL / 8.0)))
        for k in range(npad):
            q = pa + tt * (LL * (k + 0.5) / npad)
            b.box((q[0] - nn[0] * 0.6, q[1] - nn[1] * 0.6, CORNICE + 1.4), (2.2, 2.2, 2.8), C.M.limestone,
                  rot_deg=math.degrees(math.atan2(tt[1], tt[0])))
    objs.append(b.build(f"{ID}_order"))

    # ---- the dome over the central pavilion ----------------------------------------------------------------------
    b = C.MeshBuilder()
    dcx, dcy = P.centroid.x, P.centroid.y
    b.lathe([(17.0, 0.0), (17.0, 4.0), (15.5, 5.0)], 32, C.M.limestone, origin=(dcx, dcy, CORNICE), smooth=False)
    prof = [(15.5 * math.cos(math.pi / 2 * k / 12), 15.5 * math.sin(math.pi / 2 * k / 12) * 0.92) for k in range(13)]
    b.lathe(prof, 32, C.M.copper_green, origin=(dcx, dcy, CORNICE + 5.0), smooth=True)
    b.lathe([(2.6, 0.0), (2.6, 2.4), (1.2, 3.2), (0.0, 4.2)], 16, C.M.copper_green,
            origin=(dcx, dcy, DOME_TOP - 4.2), smooth=True)
    objs.append(C.tag(b.build(f"{ID}_dome"), "mass"))

    # ---- the 2004 glass entrance pavilion ------------------------------------------------------------------------
    b = C.MeshBuilder()
    rings = []
    for k in range(5):
        f = k / 4.0
        depth = 18.0 * (1.0 - f)
        halfw = PAVILION_W / 2 * (1.0 - 0.25 * f)
        rings.append([(mid[0] + t[0] * (-halfw) + n[0] * depth, mid[1] + t[1] * (-halfw) + n[1] * depth,
                       PAVILION_H * f),
                      (mid[0] + t[0] * halfw + n[0] * depth, mid[1] + t[1] * halfw + n[1] * depth, PAVILION_H * f),
                      (mid[0] + t[0] * halfw + n[0] * (depth - 3.0), mid[1] + t[1] * halfw + n[1] * (depth - 3.0),
                       PAVILION_H * f),
                      (mid[0] + t[0] * (-halfw) + n[0] * (depth - 3.0),
                       mid[1] + t[1] * (-halfw) + n[1] * (depth - 3.0), PAVILION_H * f)])
    b.loft(rings, C.M.glass_clear, cap_top=False, cap_bottom=False)
    for k in range(9):                                    # the stepped plaza in front
        z = 1.6 * (k + 1) / 9
        d = 22.0 + 1.2 * (9 - k)
        b.box_from_to(mid - t * 22.0, mid + t * 22.0, n, d, 0.0, z, C.M.granite_grey)
    objs.append(b.build(f"{ID}_entrance_pavilion"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint; the 50.0 m dome and the 27.0 m cornice (OTI LiDAR / OSM); the "
                          "hexastyle Ionic portico of six 12.5 m columns with its pediment; the engaged Ionic "
                          "colonnade of the wings; the parapet pedestals; the 2004 Polshek glass entrance pavilion "
                          "34.0 x 12.0 m over a stepped plaza. Inferred (stated): the storey heights, the wing "
                          "colonnade's spacing and the dome profile (from photographs). Not modelled: the 30 "
                          "allegorical figures (pedestals only), the pediment sculpture, interiors, the sculpture "
                          "garden."),
                      dimensions={"dome_top_m": DOME_TOP, "cornice_m": CORNICE, "portico_columns": 6,
                                  "portico_column_h_m": COLUMN_H, "entrance_pavilion_m": [PAVILION_W, PAVILION_H]})
    cc.render(ID, [
        {"view": "eastern_parkway", "azimuth_deg": 0, "elevation_deg": "street", "distance": 130, "fov_deg": 62, "look_up_deg": 18},
        {"view": "aerial", "azimuth_deg": 20, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
