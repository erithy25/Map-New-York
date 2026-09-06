"""Pier 57 — 25 11th Avenue at West 15th Street (BIN 1012253, LP-2450). Emil H. Praeger for the Grace Line, 1954;
adaptive reuse by Handel Architects with !melk, 2022.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (12,411 m2), **260.7 x 117.7 m** — the published pier is 850 x 165 ft
  (259.1 x 50.3 m) for the shed with the apron either side, which the polygon matches to within 1.6 m on the long
  axis.
* Construction [LP-2450]: the pier is carried on **three hollow reinforced-concrete caissons** — the largest
  360 x 90 ft, the two others 240 x 90 ft — that were built in a Hudson River graving dock, floated into place and
  sunk; the model shows the caisson joints in the pier's flank.
* Height [OTI LiDAR; LP-2450]: **19.3 m** to the top of the roof structure; three levels above the caisson deck,
  the top one being the 2022 rooftop park.
* Elevation [LP-2450]: a Modernist shed of glass block and steel sash in a bold structural grid on a 7.6 m bay, with
  a continuous horizontal band at each floor line and the Grace Line's original bay rhythm retained.
* Rooftop park [!melk 2022]: 2.4 acres = 9,700 m2 of planted terrace with a perimeter guardrail 1.1 m high.

Fidelity: real footprint; the 19.3 m height, the three caissons expressed in the flank, the 7.6 m structural bay
with glass-block infill, and the rooftop park terrace are modelled as geometry. Inferred (stated): the storey
heights (three levels distributed over the LiDAR height) and the caisson joint positions (from the published
caisson lengths scaled onto the polygon). NOT modelled: the interiors and the Google office fit-out, the marine
piles below the caissons, and the park planting.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_pier_57"
BIN = 1012253
TOP = 19.3
DECK = 4.2
LEVELS = 3
BAY = 7.6
CAISSONS = (109.7, 73.2, 73.2)      # 360 ft, 240 ft, 240 ft


def build():
    C.reset()
    cc.materials(["concrete", "concrete_dark", "glass_clear", "glass_blue", "steel_dark", "aluminium", "roof_grey",
                  "roof_dark", "grass", "pavement", "water_dark"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    x0, y0, x1, y1 = P.bounds
    objs: list = []

    # ---- the three caissons and the pier deck ---------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_caissons", P, -6.0, DECK, C.M.concrete_dark, material_top=C.M.pavement))
    b = C.MeshBuilder()
    total = sum(CAISSONS)
    u = 0.0
    for L in CAISSONS[:-1]:
        u += L / total
        xj = x0 + (x1 - x0) * u
        b.box((xj, (y0 + y1) / 2, (DECK - 6.0) / 2), (0.6, y1 - y0 + 0.4, DECK + 6.0), C.M.concrete)
    objs.append(b.build(f"{ID}_caisson_joints"))

    # ---- the shed ----------------------------------------------------------------------------------------------
    shed = C.offset_polygon(P, -12.0)
    objs.append(C.tag(C.prism(f"{ID}_shed", shed, DECK, TOP - 1.6, C.M.glass_blue, material_top=C.M.roof_grey),
                      "mass"))
    b = C.MeshBuilder()
    floors = [DECK + (TOP - 1.6 - DECK) * k / LEVELS for k in range(LEVELS + 1)]
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(shed)):
        ncol = max(1, int(round(L / BAY)))
        for k in range(ncol + 1):
            q0 = p0 + t * (min(L, k * (L / ncol)) - 0.35)
            q1 = q0 + t * 0.7
            b.box_from_to(q0, q1, n, 0.5, DECK, TOP - 1.6, C.M.concrete)
        for z in floors[1:]:
            b.box_from_to(p0, p1, n, 0.4, z - 0.8, z, C.M.concrete)
        for k in range(ncol):                                   # glass-block infill panels
            a = p0 + t * (k * (L / ncol) + 0.9)
            c = p0 + t * ((k + 1) * (L / ncol) - 0.9)
            for fi in range(LEVELS):
                b.quad((a[0], a[1], floors[fi] + 0.9), (c[0], c[1], floors[fi] + 0.9),
                       (c[0], c[1], floors[fi + 1] - 1.0), (a[0], a[1], floors[fi + 1] - 1.0), C.M.glass_clear)
    objs.append(b.build(f"{ID}_shed_frame"))

    # ---- the rooftop park ---------------------------------------------------------------------------------------
    b = C.MeshBuilder()
    b.prism(C.ring_coords(shed), TOP - 1.6, TOP - 1.4, C.M.grass)
    cc.band_ring(b, C.ring_coords(shed), TOP - 1.4, TOP - 0.3, 0.1, C.M.aluminium)
    for k in range(9):                                          # the rooftop pavilions and stair bulkheads
        q = (x0 + (x1 - x0) * (0.1 + 0.1 * k), (y0 + y1) / 2 + (12.0 if k % 2 else -12.0))
        b.box((q[0], q[1], TOP - 0.9), (6.0, 5.0, 1.8), C.M.steel_dark)
    objs.append(C.tag(b.build(f"{ID}_rooftop_park"), "park"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint (260.7 m long, within 1.6 m of the published 850 ft); 19.3 m "
                          "(OTI LiDAR) over three levels; the three floating caissons expressed as joints in the "
                          "pier flank at the published 360 / 240 / 240 ft lengths; the 7.6 m structural bay with "
                          "glass-block infill and continuous floor bands; the 2022 rooftop park terrace with its "
                          "guardrail. Inferred (stated): the storey heights and the caisson joint positions "
                          "(published lengths scaled onto the polygon). Not modelled: interiors and the office "
                          "fit-out, the marine piles, the park planting."),
                      dimensions={"top_m": TOP, "deck_m": DECK, "levels": LEVELS, "bay_m": BAY,
                                  "caisson_lengths_m": list(CAISSONS), "rooftop_park_m2": 9700,
                                  "length_m": round(x1 - x0, 1)})
    cc.render(ID, [
        {"view": "hudson", "azimuth_deg": 270, "elevation_deg": "street", "fov_deg": 52, "look_up_deg": 7},
        {"view": "aerial", "azimuth_deg": 250, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
