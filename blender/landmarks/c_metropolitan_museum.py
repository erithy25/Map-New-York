"""The Metropolitan Museum of Art — 1000 Fifth Avenue (BIN 1083810, LP-0955 for the 1880 Vaux & Mould wing and the
Fifth Avenue facade). Richard Morris Hunt 1902 central pavilion; McKim, Mead & White 1911-26 wings; Roche Dinkeloo
1975-90 glass wings.

Dimensions used (source in brackets)
------------------------------------
* Footprint: the real OTI polygon (44,767 m2), 190.0 m east-west by 307.6 m north-south. Fifth Avenue is west
  (local -x); Central Park is east. The projecting bay in the middle of the west edge is Hunt's central pavilion.
* Height [Hunt's published elevation; LP-0955; OTI LiDAR]: the central pavilion reaches 138 ft = 42.0 m to the top
  of its attic; the flanking McKim wings' cornice is at 33.0 m; the later wings and the roof plane average 26.8 m
  (the LiDAR figure for the whole footprint).
* Hunt's Fifth Avenue front [LP-0955]: three giant round arches 12.2 m wide and 25.0 m to the crown, flanked by
  **paired Corinthian columns** 3.6 ft diameter on high pedestals, with uncarved stone blocks over each pair (the
  caryatid groups were never carved); a full attic and balustrade above.
* McKim wings [LP-0955]: a continuous Ionic colonnade of paired engaged columns over a rusticated base, cornice at
  33.0 m, running 90 m north and south of the pavilion.
* Grand stair [Met Museum]: the Fifth Avenue steps are 30.5 m wide and rise 4.6 m in 26 risers.
* Roche Dinkeloo glass wings [Met Museum]: the Sackler Wing (Temple of Dendur, north-east), the Lehman Wing (west
  apse) and the American Wing court are sloping glass walls; the Sackler Wing's north glass wall is 24.0 m high and
  leans back 12 degrees.
* Indiana limestone throughout the 1902-26 fabric [LP-0955]. Footprint from [NYC Building Footprints, OTI
  5zhs-2jue].

Fidelity: real footprint; the three giant arches, the paired Corinthian order, the attic and balustrade, the
33.0 m McKim colonnade wings, the 42.0 m central pavilion, the 30.5 m grand stair and the sloping glass wings are
modelled as geometry. Inferred (stated): the division of the footprint between the 1902-26 fabric and the later
wings (cut at x = -55 m, from the polygon's own step); the wing storey heights; the glass wings' extents. NOT
modelled: the sculpture and carving (the uncarved blocks are modelled as blocks, which is correct), the galleries
and interiors, the roof monitors of the later wings, and the David H. Koch Plaza fountains.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_metropolitan_museum"
BIN = 1083810
PAVILION_TOP = 42.0
WING_CORNICE = 33.0
REAR_TOP = 26.8
BASE_TOP = 9.0
ARCH_W, ARCH_CROWN = 12.2, 25.0
STAIR_W, STAIR_RISE, STAIR_RISERS = 30.5, 4.6, 26


def build():
    C.reset()
    cc.materials(["limestone", "limestone_dark", "granite_grey", "glass_clear", "glass_dark", "roof_grey",
                  "roof_dark", "copper_green", "pavement", "steel_dark"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE)
    P = g.poly(BIN)
    x0, y0, x1, y1 = P.bounds
    objs: list = []
    front = C._clean_polygon(P.intersection(C.rect_xy(x0 - 1, y0 - 1, -55.0, y1 + 1)).buffer(0))
    rear = C._clean_polygon(P.difference(front.buffer(0.05)).buffer(0))

    objs.append(C.plinth(f"{ID}_base", P, 0.0, BASE_TOP, C.M.limestone, material_top=C.M.roof_grey))
    # the later (Roche Dinkeloo) wings and the galleries behind the Fifth Avenue front
    objs.append(C.prism(f"{ID}_rear", rear, BASE_TOP, REAR_TOP, C.M.limestone, material_top=C.M.roof_grey,
                        role="mass"))
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(rear)):
        if L < 25.0 or float(n[0]) < 0.4:            # only the east (Central Park) faces get the glass slopes
            continue
        b.quad((p0[0], p0[1], BASE_TOP), (p1[0], p1[1], BASE_TOP),
               (p1[0] - n[0] * 5.0, p1[1] - n[1] * 5.0, BASE_TOP + 24.0),
               (p0[0] - n[0] * 5.0, p0[1] - n[1] * 5.0, BASE_TOP + 24.0), C.M.glass_clear)
        nmul = max(2, int(L // 3.0))
        for k in range(nmul + 1):
            q = p0 + t * (L * k / nmul)
            b.hull([(q[0] - 0.12, q[1] - 0.12, BASE_TOP), (q[0] + 0.12, q[1] + 0.12, BASE_TOP),
                    (q[0] - n[0] * 5.0 - 0.12, q[1] - n[1] * 5.0 - 0.12, BASE_TOP + 24.0),
                    (q[0] - n[0] * 5.0 + 0.12, q[1] - n[1] * 5.0 + 0.12, BASE_TOP + 24.0),
                    (q[0] + n[0] * 0.25, q[1] + n[1] * 0.25, BASE_TOP),
                    (q[0] - n[0] * 4.75, q[1] - n[1] * 4.75, BASE_TOP + 24.0)], C.M.steel_dark)
    objs.append(b.build(f"{ID}_glass_wings"))

    # ---- the McKim wings: cornice at 33 m with a paired-column Ionic colonnade -----------------------------------
    objs.append(C.prism(f"{ID}_wings", front, BASE_TOP, WING_CORNICE - 2.5, C.M.limestone,
                        material_top=C.M.roof_grey, role="mass"))
    coords = C.ring_coords(front)
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(coords):
        if float(n[0]) > -0.4 or L < 20.0:           # only the Fifth Avenue (west) elevation
            continue
        npair = max(2, int(round(L / 7.6)))
        for k in range(npair):
            u = L * (k + 0.5) / npair
            for du in (-1.15, 1.15):
                q = p0 + t * (u + du) + n * 1.05
                C.column(b, q[0], q[1], BASE_TOP, WING_CORNICE - BASE_TOP - 3.4, 0.55, C.M.limestone, order="ionic",
                         segments=14)
        C.punched_wall(b, p0, p1, n, BASE_TOP, WING_CORNICE - 3.4, [BASE_TOP + 8.0, BASE_TOP + 15.0], C.M.limestone,
                       C.M.glass_dark, bays=max(2, int(round(L / 7.6))), window_w=2.6, window_h=5.2, sill_h=1.5,
                       depth=0.6)
    objs.append(b.build(f"{ID}_colonnade"))
    objs.append(C.cornice(f"{ID}_wing_cornice", front, WING_CORNICE - 2.5,
                          [(0.6, 0.0), (2.0, 1.3), (2.0, 2.0), (0.7, 2.5)], C.M.limestone))

    # ---- Hunt's central pavilion ----------------------------------------------------------------------------------
    p0, p1, L, t, n = C.edge_facing(coords, 180.0)      # the projecting Fifth Avenue bay
    mid = (p0 + p1) / 2
    pav = C.rect((mid[0] + n[0] * -14.0), (mid[1] + n[1] * -14.0), 46.0, 34.0, angle_deg=0.0)
    pav = C.rect_xy(mid[0], mid[1] - 27.0, mid[0] + 34.0, mid[1] + 27.0)
    objs.append(C.prism(f"{ID}_pavilion", pav, BASE_TOP, PAVILION_TOP - 4.0, C.M.limestone,
                        material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    for k in (-1, 0, 1):                                # the three giant arches
        a = mid + t * (k * (ARCH_W + 6.5) - ARCH_W / 2)
        c = mid + t * (k * (ARCH_W + 6.5) + ARCH_W / 2)
        C.arched_opening(b, a, c, n, BASE_TOP - 4.0, ARCH_CROWN - ARCH_W / 2, ARCH_W / 2, 3.4, C.M.limestone,
                         C.M.glass_dark)
        for du in (-(ARCH_W / 2 + 2.4), (ARCH_W / 2 + 2.4)):     # the paired Corinthian columns between the arches
            for dd in (-1.1, 1.1):
                q = mid + t * (k * (ARCH_W + 6.5) + du + dd) + n * 1.6
                C.column(b, q[0], q[1], BASE_TOP - 4.0, 24.0, 0.55, C.M.limestone, order="corinthian", segments=16)
                b.box((q[0] + n[0] * 0.2, q[1] + n[1] * 0.2, BASE_TOP + 22.0), (2.4, 2.4, 4.0), C.M.limestone_dark)
    b.box_from_to(p0, p1, n, 1.9, ARCH_CROWN + 2.0, ARCH_CROWN + 5.0, C.M.limestone)     # entablature
    b.box_from_to(p0, p1, n, 1.2, ARCH_CROWN + 5.0, PAVILION_TOP - 1.6, C.M.limestone)   # attic
    for k in range(int(L // 1.6)):                                                       # attic balustrade
        q = p0 + t * (0.8 + 1.6 * k)
        b.lathe([(0.28, 0.0), (0.16, 0.5), (0.26, 1.1), (0.16, 1.6)], 8, C.M.limestone,
                origin=(q[0] + n[0] * 0.9, q[1] + n[1] * 0.9, PAVILION_TOP - 1.6))
    b.box_from_to(p0, p1, n, 1.3, PAVILION_TOP - 0.4, PAVILION_TOP, C.M.limestone)
    # the grand stair
    for k in range(STAIR_RISERS):
        z = STAIR_RISE * (k + 1) / STAIR_RISERS
        d = 0.42 * (STAIR_RISERS - k)
        b.box_from_to(mid - t * (STAIR_W / 2), mid + t * (STAIR_W / 2), n, d, 0.0, z, C.M.granite_grey)
    objs.append(b.build(f"{ID}_pavilion_front"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: real OTI footprint (190 x 308 m); Hunt's three 12.2 m giant arches to a 25.0 m "
                          "crown with paired Corinthian columns and the uncarved blocks above them; the attic and "
                          "balustrade to 42.0 m; the McKim wings' paired-Ionic colonnade to a 33.0 m cornice; the "
                          "30.5 m wide grand stair in 26 risers; the Roche Dinkeloo sloping glass wings on the "
                          "Central Park side. Inferred (stated): the cut between the 1902-26 fabric and the later "
                          "wings (at the polygon's own step, x = -55 m), the wing storey heights and the glass "
                          "wings' extents. Not modelled: sculpture and carving, galleries and interiors, roof "
                          "monitors, the Koch Plaza fountains."),
                      dimensions={"pavilion_top_m": PAVILION_TOP, "wing_cornice_m": WING_CORNICE,
                                  "rear_top_m": REAR_TOP, "arch_w_m": ARCH_W, "arch_crown_m": ARCH_CROWN,
                                  "grand_stair_m": [STAIR_W, STAIR_RISE], "grand_stair_risers": STAIR_RISERS})
    cc.render(ID, [
        {"view": "fifth_avenue", "azimuth_deg": 270, "elevation_deg": "street", "fov_deg": 55, "look_up_deg": 10},
        {"view": "aerial", "azimuth_deg": 250, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
