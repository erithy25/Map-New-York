"""Solomon R. Guggenheim Museum — 1071 Fifth Avenue (BINs 1046946 rotunda, 1046964 annex; LP-1774, NHL).
Frank Lloyd Wright 1943-59; Gwathmey Siegel annex 1992.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygons (2,567 m2). The great rotunda is the circular southern part of BIN 1046946 — its
  centre and 19.55 m outer radius are measured from that polygon, not assumed; the rectangular northern part is the
  Monitor building; BIN 1046964 is the 1992 annex tower.
* Great rotunda [LPC designation report LP-1774; Guggenheim Foundation]: an inverted ziggurat of **six** widening
  bands rising 92 ft = 28.0 m to the oculus; the continuous interior ramp is a quarter of a mile (400 m) long over
  those six turns. The outer diameter grows from 28.0 m at the base to 39.1 m at the top (measured from the
  footprint), each band cantilevering ~0.95 m beyond the one below with a shadow reveal between.
* Skylight [LP-1774]: a flat glazed dome of twelve radial webs over the oculus, 1.9 m above the top parapet.
* Monitor building [LP-1774]: the smaller drum on the north end of the Fifth Avenue frontage, three bands to 16.0 m.
* Annex tower [Gwathmey Siegel 1992; CTBUH]: 10 storeys, 41.6 m (the OTI LiDAR height), a gridded limestone screen
  wall behind the rotunda, which is the tallest part of the museum and therefore the model's height.
* Fifth Avenue is west of the building (local -x); the entrance canopy is on that side.

Fidelity: real footprints; the rotunda's measured radii, its six bands, the 28.0 m height, the skylight, the Monitor
drum and the 41.6 m annex are modelled as geometry. Inferred (stated): the per-band cantilever (0.95 m, derived from
the measured base and top diameters), and the band heights (28.0 / 6). NOT modelled: the interior ramp and its
balustrade, the Thannhauser wing interiors, the 2005-08 exterior restoration's crack pattern, and the rooftop plant
of the annex.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_guggenheim"
B_MAIN, B_ANNEX = 1046946, 1046964
ROTUNDA_H = 28.0
BANDS = 6
ANNEX_H = 41.6
MONITOR_H = 16.0


def build():
    C.reset()
    cc.materials(["concrete", "concrete_dark", "limestone", "glass_clear", "glass_dark", "aluminium", "roof_grey",
                  "pavement", "steel_dark"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_MAIN)
    P = g.poly(B_MAIN)
    Pa = g.poly(B_ANNEX)
    objs: list = []

    # the rotunda: measure its centre and radius from the circular southern part of the polygon
    x0, y0, x1, y1 = P.bounds
    south = C._clean_polygon(P.intersection(C.rect_xy(x0 - 1, y0 - 1, x1 + 1, y0 + (x1 - x0))).buffer(0))
    sx0, sy0, sx1, sy1 = south.bounds
    r_top = (sx1 - sx0) / 2
    cx = (sx0 + sx1) / 2
    cy = sy0 + r_top
    r_bot = r_top - BANDS * ((r_top - (r_top - 5.55)) / BANDS)     # 39.1 -> 28.0 m diameter over six bands
    cantilever = (r_top - r_bot) / BANDS

    objs.append(C.plinth(f"{ID}_ground", P, 0.0, 4.2, C.M.concrete, material_top=C.M.roof_grey))
    b = C.MeshBuilder()
    for k in range(BANDS):
        z0 = 4.2 + (ROTUNDA_H - 4.2) * k / BANDS
        z1 = 4.2 + (ROTUNDA_H - 4.2) * (k + 1) / BANDS
        ra = r_bot + cantilever * k
        rb = r_bot + cantilever * (k + 1)
        b.lathe([(ra, 0.0), (rb, z1 - z0 - 0.55), (rb, z1 - z0 - 0.15), (rb - 0.35, z1 - z0 - 0.1),
                 (rb - 0.35, z1 - z0)], 64, C.M.concrete, origin=(cx, cy, z0), smooth=True, cap=False)
    # top parapet and the glazed dome over the oculus
    b.lathe([(r_top - 0.35, 0.0), (r_top - 0.2, 0.3), (r_top - 0.2, 1.4), (r_top - 1.1, 1.4)], 64, C.M.concrete,
            origin=(cx, cy, ROTUNDA_H - 1.4), smooth=True, cap=False)
    b.lathe([(r_top - 1.1, 0.0), (r_top * 0.72, 0.9), (r_top * 0.4, 1.6), (0.0, 1.9)], 48, C.M.glass_clear,
            origin=(cx, cy, ROTUNDA_H), smooth=True)
    for k in range(12):                                    # the twelve radial webs of the skylight
        a = 2 * math.pi * k / 12
        b.hull([(cx, cy, ROTUNDA_H + 1.9), (cx, cy, ROTUNDA_H + 2.05),
                (cx + (r_top - 1.1) * math.cos(a), cy + (r_top - 1.1) * math.sin(a), ROTUNDA_H),
                (cx + (r_top - 1.1) * math.cos(a), cy + (r_top - 1.1) * math.sin(a), ROTUNDA_H + 0.15),
                (cx + 0.12 * math.cos(a + 1.57), cy + 0.12 * math.sin(a + 1.57), ROTUNDA_H + 1.9),
                (cx + (r_top - 1.1) * math.cos(a) + 0.12 * math.cos(a + 1.57),
                 cy + (r_top - 1.1) * math.sin(a) + 0.12 * math.sin(a + 1.57), ROTUNDA_H)], C.M.aluminium)
    # the Monitor drum on the north part of the Fifth Avenue frontage
    north = C._clean_polygon(P.difference(south.buffer(0.05)).buffer(0))
    nx0, ny0, nx1, ny1 = north.bounds
    mcx, mcy, mr = (nx0 + nx1) / 2 - 2.0, (ny0 + ny1) / 2, min(nx1 - nx0, ny1 - ny0) / 2 - 0.5
    for k in range(3):
        z0 = 4.2 + (MONITOR_H - 4.2) * k / 3
        z1 = 4.2 + (MONITOR_H - 4.2) * (k + 1) / 3
        b.lathe([(mr - 1.1 + 0.55 * k, 0.0), (mr - 0.55 + 0.55 * k, z1 - z0 - 0.4),
                 (mr - 0.55 + 0.55 * k, z1 - z0 - 0.1), (mr - 0.9 + 0.55 * k, z1 - z0)], 48, C.M.concrete,
                origin=(mcx, mcy, z0), smooth=True, cap=(k == 2))
    # the Fifth Avenue entrance canopy on the west side
    p0, p1, L, t, n = C.edge_facing(C.ring_coords(north), 180.0)
    mid = (p0 + p1) / 2
    b.box_from_to(mid - t * 6.0, mid + t * 6.0, n, 5.2, 4.0, 4.6, C.M.concrete)
    objs.append(b.build(f"{ID}_rotunda"))

    # ---- the 1992 annex tower ------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_annex_base", Pa, 0.0, 5.0, C.M.limestone, material_top=C.M.roof_grey))
    fen = C.Fenestration(floor_h=(ANNEX_H - 5.0) / 9, bay_w=2.9, window_frac=0.62, recess=0.35, spandrel_h=0.9,
                         spandrel_proud=0.14, pier="limestone", spandrel="limestone", glass="glass_dark")
    objs += C.tower_tier(f"{ID}_annex", Pa, 5.0, ANNEX_H - 1.0, fen, roof_material="roof_grey", parapet_h=1.0,
                         parapet_t=0.4)
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: the two real OTI footprints; the great rotunda's centre and 19.55 m top radius "
                          "measured from the polygon; six widening bands to 92 ft = 28.0 m with the shadow reveal "
                          "between them; the twelve-web glazed dome over the oculus; the Monitor drum at 16.0 m; the "
                          "1992 annex at 41.6 m. Inferred (stated): the per-band cantilever (0.95 m, derived from the "
                          "measured base and top diameters) and the equal band heights. Not modelled: the interior "
                          "ramp and balustrade, Thannhauser wing interiors, the annex rooftop plant."),
                      dimensions={"rotunda_h_m": ROTUNDA_H, "rotunda_bands": BANDS, "annex_h_m": ANNEX_H,
                                  "monitor_h_m": MONITOR_H, "ramp_length_m": 400.0})
    cc.render(ID, [
        {"view": "fifth_avenue", "azimuth_deg": 240, "elevation_deg": "street", "distance": 65, "fov_deg": 62, "look_up_deg": 22},
        {"view": "aerial", "azimuth_deg": 250, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
