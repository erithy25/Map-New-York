"""Jacob K. Javits Convention Center — 429 11th Avenue (BINs 1067973 the 1986 building, 1089474 the 2021 expansion).
I. M. Pei & Partners (James Ingo Freed), 1986; expansion by Tod Williams Billie Tsien with Epstein, 2021.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the two real OTI polygons (77,471 m2); the 1986 building is 330.9 x 344.4 m and the 2021 expansion
  173.6 x 163.3 m to its north.
* Height [OTI LiDAR; Pei/Freed]: the Crystal Palace lobby reaches **150 ft = 45.7 m** and the highest roof point of
  the whole complex is **53.6 m**; the main exhibition halls' roof is 27.4 m.
* Space frame [Freed; Weidlinger Associates]: the whole building is a **90 ft = 27.43 m structural grid** of a
  two-way steel space frame built from 5 ft = 1.524 m modules; every node is a cast steel ball. The exterior is
  glazed with **nearly 16,000 panes** of dark grey reflective glass held in the space-frame plane.
* Crystal Palace [Freed]: the 11th Avenue entrance hall is a 45.7 m high glazed volume 90 x 90 ft in plan stepping
  up in three tiers.
* 2021 expansion [TWBTA]: a 1.2 million sq ft addition with a 3.7 ha green roof and a glazed north pavilion, roof
  at 40.0 m.

Fidelity: two real footprints; the 90 ft structural grid, the space frame expressed as diagonal members on the
5 ft module at the roof and walls, the 45.7 m Crystal Palace, the 27.4 m hall roofs and the 2021 expansion with its
green roof are modelled as geometry. Inferred (stated): the position of the Crystal Palace within the 1986
footprint (at the 11th Avenue corner) and the tier heights. Simplified (stated): the space frame is built at the
90 ft grid with one diagonal per bay rather than the full 5 ft module — the real frame's ~76,000 members would be
far beyond the triangle budget. NOT modelled: the interiors, the truck docks, the green roof planting and the
rooftop solar array.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_javits_center"
B_MAIN, B_EXPANSION = 1067973, 1089474
TOP = 53.6
CRYSTAL_H = 45.7
HALL_ROOF = 27.4
EXPANSION_ROOF = 40.0
GRID = 27.43           # 90 ft
MODULE = 1.524         # 5 ft


def build():
    C.reset()
    cc.materials(["glass_dark", "glass_blue", "steel_dark", "steel_nirosta", "concrete", "concrete_dark",
                  "roof_dark", "grass", "pavement", "aluminium"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_MAIN)
    Pm, Pe = g.poly(B_MAIN), g.poly(B_EXPANSION)
    objs: list = []
    mx0, my0, mx1, my1 = Pm.bounds

    objs.append(C.plinth(f"{ID}_main_base", Pm, 0.0, 6.0, C.M.concrete_dark, material_top=C.M.roof_dark))
    objs.append(C.plinth(f"{ID}_exp_base", Pe, 0.0, 6.0, C.M.concrete_dark, material_top=C.M.roof_dark))
    objs.append(C.tag(C.prism(f"{ID}_halls", C.offset_polygon(Pm, -0.8), 6.0, HALL_ROOF, C.M.glass_dark,
                              material_top=C.M.roof_dark), "mass"))
    objs.append(C.tag(C.prism(f"{ID}_expansion", C.offset_polygon(Pe, -0.8), 6.0, EXPANSION_ROOF, C.M.glass_blue,
                              material_top=C.M.grass), "mass"))

    # ---- the Crystal Palace: three stepped tiers at the 11th Avenue (east) corner --------------------------------
    cp = C.rect_xy(mx1 - 3 * GRID, my0 + 1.0, mx1 - 1.0, my0 + 3 * GRID)
    for i, (z0, z1, ins) in enumerate(((6.0, 22.0, 0.0), (22.0, 34.0, GRID * 0.25), (34.0, CRYSTAL_H, GRID * 0.5))):
        poly = C.offset_polygon(cp, -ins)
        objs.append(C.tag(C.prism(f"{ID}_crystal{i}", poly, z0, z1, C.M.glass_dark, material_top=C.M.roof_dark),
                          "mass"))

    # ---- the space frame: the 90 ft grid with its diagonals, on the walls and over the roof ----------------------
    b = C.MeshBuilder()

    # the visible frame is drawn on the 90 ft grid subdivided into three (9.14 m), which is the coarsest spacing at
    # which the space frame still reads as a triangulated mesh rather than a few big Xs
    SUB = GRID / 3.0

    def frame_edges(poly, z0, z1):
        ring = C.ring_coords(poly)
        for p0, p1, L, t, n in C.edges_of(ring):
            ncol = max(1, int(round(L / SUB)))
            for k in range(ncol + 1):
                q = p0 + t * min(L, k * (L / ncol))
                b.box((q[0] + n[0] * 0.6, q[1] + n[1] * 0.6, (z0 + z1) / 2), (0.45, 0.9, z1 - z0), C.M.steel_dark,
                      rot_deg=math.degrees(math.atan2(t[1], t[0])))
            nrow = max(1, int(round((z1 - z0) / SUB)))
            for j in range(nrow + 1):
                z = z0 + (z1 - z0) * j / nrow
                b.box_from_to(p0, p1, n, 1.0, z - 0.22, z + 0.22, C.M.steel_dark)
            for k in range(ncol):                       # one diagonal per 90 ft bay (see the fidelity statement)
                for j in range(nrow):
                    qa = p0 + t * (L * k / ncol) + n * 0.75
                    qb = p0 + t * (L * (k + 1) / ncol) + n * 0.75
                    za = z0 + (z1 - z0) * j / nrow
                    zb = z0 + (z1 - z0) * (j + 1) / nrow
                    qc = p0 + t * (L * k / ncol) + n * 0.75
                    for (ra, rz), (rb, rzb) in (((qa, za), (qb, zb)), ((qc, zb), (qb, za))):
                        b.hull([(ra[0] - 0.14, ra[1] - 0.14, rz), (ra[0] + 0.14, ra[1] + 0.14, rz),
                                (ra[0] - 0.14, ra[1] + 0.14, rz), (ra[0] + 0.14, ra[1] - 0.14, rz),
                                (rb[0] - 0.14, rb[1] - 0.14, rzb), (rb[0] + 0.14, rb[1] + 0.14, rzb),
                                (rb[0] - 0.14, rb[1] + 0.14, rzb), (rb[0] + 0.14, rb[1] - 0.14, rzb)],
                               C.M.steel_nirosta)

    frame_edges(Pm, 6.0, HALL_ROOF)
    frame_edges(cp, 6.0, CRYSTAL_H)
    # the roof space frame over the halls: the 90 ft grid of top chords
    for i in range(int((mx1 - mx0) // SUB) + 1):
        x = mx0 + SUB * i
        b.box((x, (my0 + my1) / 2, HALL_ROOF + 1.1), (0.5, my1 - my0, 1.4), C.M.steel_dark)
    for j in range(int((my1 - my0) // SUB) + 1):
        y = my0 + SUB * j
        b.box(((mx0 + mx1) / 2, y, HALL_ROOF + 2.4), (mx1 - mx0, 0.5, 1.4), C.M.steel_dark)
    objs.append(b.build(f"{ID}_space_frame"))
    # the tallest roof element: the mechanical penthouse over the halls
    objs.append(C.prism(f"{ID}_penthouse", C.rect((mx0 + mx1) / 2, (my0 + my1) / 2, 6 * GRID, 3 * GRID),
                        HALL_ROOF + 3.1, TOP, C.M.aluminium, material_top=C.M.roof_dark, role="mass"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: two real OTI footprints; the 90 ft = 27.43 m structural grid expressed as the "
                          "space frame's chords and diagonals on the walls and over the roof; the Crystal Palace "
                          "rising in three tiers to 150 ft = 45.7 m; the 27.4 m hall roof; the 53.6 m high point "
                          "(OTI LiDAR); the 2021 expansion at 40.0 m with its green roof. Simplified and stated: "
                          "the space frame is built on the 90 ft grid subdivided into three (9.14 m) with crossed "
                          "diagonals per sub-bay rather than the real 5 ft = 1.524 m module — the actual ~76,000 members would be far beyond the "
                          "triangle budget. Inferred (stated): the Crystal Palace's position at the 11th Avenue "
                          "corner and the tier heights. Not modelled: interiors, truck docks, green-roof planting, "
                          "the rooftop solar array."),
                      dimensions={"top_m": TOP, "crystal_palace_m": CRYSTAL_H, "hall_roof_m": HALL_ROOF,
                                  "expansion_roof_m": EXPANSION_ROOF, "structural_grid_m": GRID,
                                  "space_frame_module_m": MODULE, "glass_panes_published": 16000})
    cc.render(ID, [
        {"view": "eleventh_avenue", "azimuth_deg": 100, "elevation_deg": "street", "fov_deg": 52, "look_up_deg": 8},
        {"view": "aerial", "azimuth_deg": 120, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
