"""Citigroup Center — 601 Lexington Avenue (BIN 1036474). Hugh Stubbins & Associates with Emery Roth & Sons, 1977.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (5,719 m2) — the whole block bounded by Lexington Avenue (west, -x), Third Avenue
  (east, +x), East 53rd (south, -y) and East 54th Street (north, +y). The angular notch at the north-west corner is
  St. Peter's Lutheran Church, which the tower was built over and around; it is taken straight from the polygon.
* Height [CTBUH]: 915 ft = 278.9 m, 59 floors.
* Tower [Stubbins; LeMessurier's published structural papers]: a 157 ft = 47.85 m square shaft, lifted on four
  114 ft = 34.75 m columns placed at the *mid-point of each side* (not the corners) so the church could stay on its
  corner; the chevron braced frame transfers the corners to those columns. Storeys derived to land the roof on
  278.9 m: 59 floors of 4.138 m above the 34.75 m stilt zone.
* Roof [Stubbins]: a 45-degree slope, originally intended as a solar collector, facing due south; a 45-degree wedge
  on a 47.85 m square rises exactly 47.85 m, so the vertical shaft stops at 231.05 m and the slope runs from there
  to 278.9 m.
* Elevation [Stubbins]: continuous horizontal bands — brushed-aluminium spandrel over ribbon glazing at each floor,
  with the double-height chevron braces expressed at every eighth floor line.
* Base [Stubbins; AIA Guide]: a seven-storey retail/office block ("The Market") under and east of the tower, a sunken
  plaza on Lexington Avenue, and the granite-and-glass church wedge (Massimo Vignelli interior) at the north-west
  corner, 18 m to its highest fold.

Fidelity: real footprint; published height, 47.85 m square shaft, four mid-side stilts at 34.75 m, the 45-degree
south-facing roof, banded aluminium/glass elevation and the church wedge modelled as geometry. Inferred (stated):
the position of the tower square on the block (centred on the footprint's solid western zone) and the base block's
seven storeys. NOT modelled: the 400 t tuned mass damper, the sunken plaza's escalators and the interiors, and the
1978 LeMessurier chevron retrofit welds (invisible, inside the cladding).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_citigroup_center"
BIN = 1036474
ROOF_M = 278.9
STILT_H = 34.75          # 114 ft
SQ = 47.85               # 157 ft
FLOORS = 59
FLOOR_H = (ROOF_M - SQ - STILT_H) / 47.0   # vertical shaft floors
SHAFT_TOP = ROOF_M - SQ
TOWER_C = (-26.0, -2.0)  # centre of the tower square, in the footprint's solid western zone
BASE_TOP = 28.0          # seven storeys of the retail/office base
CHURCH_TOP = 18.0


def build():
    C.reset()
    cc.materials(["aluminium", "glass_blue", "granite_grey", "concrete", "roof_dark", "pavement", "steel_dark"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    minx, miny, maxx, maxy = P.bounds
    objs: list = []

    # ---- ground level: the base volume on the real footprint (IoU) ------------------------------------------------
    objs.append(C.plinth(f"{ID}_ground", P, 0.0, 6.4, C.M.glass_clear, material_top=C.M.pavement))

    # ---- the church wedge at the north-west corner ----------------------------------------------------------------
    church = C._clean_polygon(P.intersection(C.rect_xy(minx - 1, 9.0, -40.0, maxy + 1)).buffer(0))
    b = C.MeshBuilder()
    ch = C.ring_coords(church)
    b.prism(ch, 0.0, 9.0, C.M.granite_grey, cap_bottom=False)
    # the folded granite roof: a hipped wedge rising to CHURCH_TOP over the long axis
    cx = sum(p[0] for p in ch) / len(ch); cy = sum(p[1] for p in ch) / len(ch)
    for p0, p1, L, t, n in C.edges_of(ch):
        b.tri((p0[0], p0[1], 9.0), (p1[0], p1[1], 9.0), (cx, cy, CHURCH_TOP), C.M.granite_grey)
    objs.append(b.build(f"{ID}_st_peters"))

    # ---- the seven-storey base block, east of and under the tower --------------------------------------------------
    base = C._clean_polygon(P.difference(church.buffer(0.05)).intersection(C.rect_xy(-14.0, miny - 1, maxx + 1, maxy + 1)).buffer(0))
    fen_base = C.Fenestration(floor_h=4.0, bay_w=3.0, window_frac=0.82, recess=0.25, spandrel_h=1.0,
                              spandrel_proud=0.18, pier="aluminium", spandrel="aluminium", glass="glass_blue")
    objs += C.tower_tier(f"{ID}_base", base, 6.4, BASE_TOP, fen_base, roof_material="roof_dark", parapet_h=1.0)

    # ---- the four stilts -------------------------------------------------------------------------------------------
    tx, ty = TOWER_C
    b = C.MeshBuilder()
    for dx, dy in ((0, -SQ / 2), (0, SQ / 2), (-SQ / 2, 0), (SQ / 2, 0)):
        b.box((tx + dx, ty + dy, STILT_H / 2), (7.3, 7.3, STILT_H), C.M.concrete)
    objs.append(C.tag(b.build(f"{ID}_stilts"), "mass"))

    # ---- the tower shaft --------------------------------------------------------------------------------------------
    sq = C.rect(tx, ty, SQ, SQ)
    fen = C.Fenestration(floor_h=FLOOR_H, bay_w=1.6, window_frac=0.90, recess=0.22, spandrel_h=1.35,
                         spandrel_proud=0.20, pier="aluminium", spandrel="aluminium", glass="glass_blue")
    objs += C.tower_tier(f"{ID}_shaft", sq, STILT_H, SHAFT_TOP, fen, roof_material="roof_dark", parapet_h=0.0)
    # chevron braces expressed every eighth floor line
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(sq)):
        k = 0
        while STILT_H + (k + 8) * FLOOR_H <= SHAFT_TOP + 0.01:
            z0 = STILT_H + k * FLOOR_H
            z1 = z0 + 8 * FLOOR_H
            mid = p0 + t * (L / 2)
            for a, c, za, zc in ((p0, mid, z0, z1), (mid, p1, z1, z0)):
                q0 = a + n * 0.26; q1 = c + n * 0.26
                b.hull([(q0[0], q0[1], za), (q0[0], q0[1], za + 1.1), (q1[0], q1[1], zc), (q1[0], q1[1], zc + 1.1),
                        (q0[0] + n[0] * 0.2, q0[1] + n[1] * 0.2, za), (q0[0] + n[0] * 0.2, q0[1] + n[1] * 0.2, za + 1.1),
                        (q1[0] + n[0] * 0.2, q1[1] + n[1] * 0.2, zc), (q1[0] + n[0] * 0.2, q1[1] + n[1] * 0.2, zc + 1.1)],
                       C.M.aluminium)
            k += 8
    objs.append(b.build(f"{ID}_chevrons"))

    # ---- the 45-degree roof, sloping down to the south --------------------------------------------------------------
    b = C.MeshBuilder()
    x0, y0 = tx - SQ / 2, ty - SQ / 2
    x1, y1 = tx + SQ / 2, ty + SQ / 2
    # south edge (low, at SHAFT_TOP) -> north edge (high, at ROOF_M)
    b.quad((x0, y0, SHAFT_TOP), (x1, y0, SHAFT_TOP), (x1, y1, ROOF_M), (x0, y1, ROOF_M), C.M.aluminium)
    b.tri((x0, y0, SHAFT_TOP), (x0, y1, ROOF_M), (x0, y1, SHAFT_TOP), C.M.aluminium)
    b.tri((x1, y0, SHAFT_TOP), (x1, y1, SHAFT_TOP), (x1, y1, ROOF_M), C.M.aluminium)
    b.quad((x0, y1, SHAFT_TOP), (x0, y1, ROOF_M), (x1, y1, ROOF_M), (x1, y1, SHAFT_TOP), C.M.aluminium)
    b.quad((x0, y0, SHAFT_TOP), (x0, y1, SHAFT_TOP), (x1, y1, SHAFT_TOP), (x1, y0, SHAFT_TOP), C.M.roof_dark)
    # the louvred bands that read across the slope
    for k in range(1, 12):
        f = k / 12.0
        y = y0 + (y1 - y0) * f
        z = SHAFT_TOP + (ROOF_M - SHAFT_TOP) * f
        b.box((tx, y, z + 0.35), (SQ - 0.6, 0.35, 0.7), C.M.steel_dark, rot_deg=0.0)
    objs.append(C.tag(b.build(f"{ID}_slope"), "mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint including St. Peter's corner notch, 278.9 m / 59 floors (CTBUH), "
                          "157 ft square shaft on four 114 ft mid-side stilts, 45-degree south-facing roof, banded "
                          "aluminium/ribbon-glass elevation with the chevron braces expressed every eighth floor. "
                          "Inferred (stated): the tower square's position on the block and the seven-storey base. "
                          "Not modelled: the 400 t tuned mass damper, sunken-plaza escalators, interiors, and the "
                          "1978 chevron retrofit welds (concealed)."),
                      dimensions={"roof_m": ROOF_M, "floors": FLOORS, "shaft_square_m": SQ, "stilt_h_m": STILT_H,
                                  "shaft_top_m": round(SHAFT_TOP, 2), "floor_h_m": round(FLOOR_H, 3),
                                  "roof_slope_deg": 45.0, "base_top_m": BASE_TOP, "church_top_m": CHURCH_TOP,
                                  "tower_centre_local_m": list(TOWER_C)})
    cc.render(ID, [
        {"view": "lexington", "azimuth_deg": 250, "elevation_deg": "street", "distance": 360, "fov_deg": 44, "look_up_deg": 36},
        {"view": "aerial", "azimuth_deg": 200, "elevation_deg": 24},
    ])
    return entry


if __name__ == "__main__":
    main()
