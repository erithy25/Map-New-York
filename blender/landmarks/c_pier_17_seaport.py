"""Pier 17, South Street Seaport — 89 South Street (BIN 1090548). SHoP Architects, 2018 (replacing the 1985
Benjamin Thompson festival marketplace).

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (6,062 m2) on the pier deck, 111.7 x 116.9 m; the East River is east and south,
  South Street and the FDR Drive west.
* Height [SHoP; OTI LiDAR]: **20.7 m** to the top of the rooftop parapet; four levels — retail on 1 and 2,
  restaurants on 3, and a 1.5-acre (6,070 m2) rooftop event lawn and stage on 4.
* Structure and skin [SHoP]: an exposed steel frame on a 9.1 m (30 ft) bay grid with full-height, low-iron glass
  between the columns; the frame is expressed outside the glass line, and the corners are cut back so the building
  reads as a pavilion.
* Roof [SHoP]: a projecting steel canopy 2.4 m deep on all four sides at 18.3 m, with the rooftop stage's fly
  structure at the north-east corner rising to the 20.7 m parapet.
* Pier deck [Seaport / Howard Hughes]: the pier apron around the building is 12 m wide on the river sides; it is
  modelled as ``role="pier"`` geometry outside the footprint.

Fidelity: real footprint; the 20.7 m height, the four levels, the 9.1 m expressed steel bay grid with full-height
glazing, the 2.4 m roof canopy and the rooftop stage structure are modelled as geometry. Inferred (stated): the
storey heights (four levels distributed over the LiDAR height) and the pier apron's width. NOT modelled: the
interiors, the rooftop lawn's turf and seating, the marina and the historic ships moored alongside.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_pier_17_seaport"
BIN = 1090548
TOP = 20.7
CANOPY_Z, CANOPY_D = 18.3, 2.4
BAY = 9.1
LEVELS = 4


def build():
    C.reset()
    cc.materials(["steel_dark", "glass_clear", "glass_blue", "concrete", "wood_dark", "roof_dark", "pavement",
                  "grass", "steel_nirosta"])
    g = cc.Group(ID)
    P = g.poly(BIN)
    coords = C.ring_coords(P)
    objs: list = []

    objs.append(C.plinth(f"{ID}_base", P, 0.0, 1.2, C.M.concrete, material_top=C.M.pavement))
    objs.append(C.tag(C.prism(f"{ID}_body", C.offset_polygon(P, -0.9), 1.2, CANOPY_Z, C.M.glass_clear,
                              material_top=C.M.roof_dark), "mass"))
    b = C.MeshBuilder()
    floors = [1.2 + (CANOPY_Z - 1.2) * k / LEVELS for k in range(LEVELS + 1)]
    for p0, p1, L, t, n in C.edges_of(coords):
        ncol = max(1, int(round(L / BAY)))
        for k in range(ncol + 1):                                # the expressed steel columns
            q0 = p0 + t * (min(L, k * (L / ncol)) - 0.3)
            q1 = q0 + t * 0.6
            b.box_from_to(q0, q1, n, 0.55, 0.0, CANOPY_Z, C.M.steel_dark)
        for z in floors[1:]:                                     # the floor bands
            b.box_from_to(p0, p1, n, 0.35, z - 0.55, z, C.M.steel_dark)
    objs.append(b.build(f"{ID}_frame"))
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):                   # the projecting roof canopy
        b.box_from_to(p0, p1, n, CANOPY_D, CANOPY_Z, CANOPY_Z + 0.7, C.M.steel_dark)
    b.prism(C.ring_coords(C.offset_polygon(P, -2.0)), CANOPY_Z + 0.7, CANOPY_Z + 0.8, C.M.grass)   # the roof lawn
    x0, y0, x1, y1 = P.bounds
    stage = C.rect_xy(x1 - 30.0, y1 - 22.0, x1 - 2.0, y1 - 2.0)
    b.prism(C.ring_coords(stage), CANOPY_Z + 0.8, TOP - 0.6, C.M.steel_dark, cap_top=False)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(stage)):     # the stage fly structure
        for k in range(int(L // 4.0) + 1):
            q = p0 + t * min(L, 4.0 * k)
            b.box((q[0], q[1], (CANOPY_Z + TOP) / 2), (0.35, 0.35, TOP - CANOPY_Z), C.M.steel_nirosta)
    b.box(((x1 - 16.0), (y1 - 12.0), TOP - 0.3), (28.0, 20.0, 0.6), C.M.steel_dark)
    objs.append(C.tag(b.build(f"{ID}_roof"), "mass"))
    # the pier apron
    b = C.MeshBuilder()
    b.prism(C.ring_coords(C.offset_polygon(P, 12.0)), -0.4, 0.0, C.M.wood_dark,
            holes=[C.ring_coords(P)])
    objs.append(C.tag(b.build(f"{ID}_pier_apron"), "pier"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint on the pier deck; 20.7 m (OTI LiDAR) over four levels; the "
                          "9.1 m expressed steel bay grid with full-height glazing between the columns; the 2.4 m "
                          "roof canopy at 18.3 m; the rooftop lawn and the north-east stage fly structure to the "
                          "20.7 m parapet; the pier apron. Inferred (stated): the storey heights (four levels "
                          "distributed over the LiDAR height) and the apron width. Not modelled: interiors, the "
                          "rooftop turf and seating, the marina and the historic ships."),
                      dimensions={"top_m": TOP, "levels": LEVELS, "bay_m": BAY, "canopy_z_m": CANOPY_Z,
                                  "canopy_depth_m": CANOPY_D, "roof_lawn_m2": 6070})
    cc.render(ID, [
        {"view": "east_river", "azimuth_deg": 100, "elevation_deg": "street", "distance": 175, "fov_deg": 52, "look_up_deg": 9},
        {"view": "aerial", "azimuth_deg": 120, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
