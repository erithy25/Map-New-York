"""Lincoln Center for the Performing Arts — Josie Robertson Plaza (BINs 1081022 Metropolitan Opera House,
1081023 David Geffen Hall, 1028831 David H. Koch Theater). Wallace K. Harrison (Met Opera, 1966),
Max Abramovitz (Philharmonic Hall / Geffen Hall, 1962), Philip Johnson (New York State Theater / Koch Theater, 1964);
Diller Scofidio + Renfro public-realm remake, 2010.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the three real OTI polygons (16,949 m2). The plaza is the open ground between them: the Met Opera is
  west (local -x), Geffen Hall north-east, the Koch Theater south-east.
* Metropolitan Opera House [Harrison; Lincoln Center]: **five travertine arches 96 ft = 29.3 m high** across the
  east front, each 15.5 m wide, glazed full height so the Chagall murals and the lobby's grand stair are visible;
  the fly tower behind reaches 37.7 m (OTI LiDAR), which is the height of the whole complex.
* David Geffen Hall [Abramovitz]: a travertine colonnade of **44 tapering piers** 24.4 m tall around a glazed
  lobby; roof 27.4 m (OTI LiDAR).
* David H. Koch Theater [Johnson]: a four-storey travertine loggia over the plaza with square-headed openings on a
  6.1 m module; roof 31.7 m (OTI LiDAR).
* Plaza [DS+R 2010; Lincoln Center]: the Revson Fountain is 11.0 m in diameter at the centre of the plaza, and the
  plaza is paved in travertine-toned granite; the model includes the fountain basin and the plaza paving as
  ``role="plaza"`` geometry outside the footprints.

Fidelity: three real footprints; the Met Opera's five 29.3 m arches, the Geffen colonnade, the Koch loggia, the
published roof heights and the Revson Fountain are modelled as geometry. Inferred (stated): the arch widths
(measured off the Met Opera footprint's east edge divided into five bays), the pier count of the Geffen colonnade
(published 44, distributed evenly around the polygon) and the storey heights. NOT modelled: the auditoria and
interiors, the Chagall murals (the arch glazing is plain), the Henry Moore reclining figure in the north pool, and
the underground garage.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_lincoln_center"
B_MET, B_GEFFEN, B_KOCH = 1081022, 1081023, 1028831
MET_ARCH_H, MET_ARCHES, MET_TOP = 29.3, 5, 37.7
GEFFEN_TOP, GEFFEN_PIERS, GEFFEN_PIER_H = 27.4, 44, 24.4
KOCH_TOP = 31.7
FOUNTAIN_D = 11.0


def build():
    C.reset()
    cc.materials(["marble_white", "limestone_warm", "glass_clear", "glass_dark", "granite_grey", "roof_grey",
                  "roof_dark", "water_dark", "pavement", "bronze"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_MET)
    Pmet, Pgef, Pkoch = g.poly(B_MET), g.poly(B_GEFFEN), g.poly(B_KOCH)
    objs: list = []
    trav = C.M.marble_white

    # ---- the plaza (outside the footprints, so excluded from the IoU base volume) --------------------------------
    b = C.MeshBuilder()
    plaza = C.rect_xy(2.0, -24.0, 26.0, 25.0)
    b.prism(C.ring_coords(plaza), -0.02, 0.35, C.M.granite_grey)
    fcx, fcy = 14.0, 0.5
    b.lathe([(FOUNTAIN_D / 2, 0.0), (FOUNTAIN_D / 2, 0.95), (FOUNTAIN_D / 2 - 0.45, 0.95),
             (FOUNTAIN_D / 2 - 0.45, 0.35)], 40, C.M.granite_grey, origin=(fcx, fcy, 0.35), smooth=True, cap=False)
    b.lathe([(0.0, 0.0), (FOUNTAIN_D / 2 - 0.5, 0.0)], 40, C.M.water_dark, origin=(fcx, fcy, 1.05))
    objs.append(C.tag(b.build(f"{ID}_plaza"), "plaza"))

    # ---- Metropolitan Opera House ---------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_met_base", Pmet, 0.0, 3.0, trav, material_top=C.M.roof_grey))
    objs.append(C.prism(f"{ID}_met_body", C.offset_polygon(Pmet, -0.6), 3.0, MET_TOP - 4.0, trav,
                        material_top=C.M.roof_grey, role="mass"))
    objs.append(C.prism(f"{ID}_met_flytower", C.offset_polygon(Pmet, -22.0), MET_TOP - 4.0, MET_TOP, trav,
                        material_top=C.M.roof_dark, role="mass"))
    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(C.ring_coords(Pmet), 0.0)          # the east front onto the plaza
    aw = L / MET_ARCHES
    for k in range(MET_ARCHES):
        a = p0 + t * (k * aw + 1.1)
        c = p0 + t * ((k + 1) * aw - 1.1)
        C.arched_opening(b, a, c, n, 3.0, MET_ARCH_H - (aw - 2.2) / 2, (aw - 2.2) / 2, 4.5, trav, C.M.glass_clear)
        b.box_from_to(a - t * 1.1, a, n, 4.5, 0.0, MET_ARCH_H + 2.6, trav)     # the travertine piers between arches
    b.box_from_to(p1 - t * 1.1, p1, n, 4.5, 0.0, MET_ARCH_H + 2.6, trav)
    b.box_from_to(p0, p1, n, 4.8, MET_ARCH_H + 2.6, MET_ARCH_H + 4.4, trav)    # the entablature over the arcade
    objs.append(b.build(f"{ID}_met_arches"))

    # ---- David Geffen Hall -----------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_geffen_base", Pgef, 0.0, 2.4, trav, material_top=C.M.roof_grey))
    objs.append(C.prism(f"{ID}_geffen_body", C.offset_polygon(Pgef, -5.5), 2.4, GEFFEN_TOP - 3.0, C.M.glass_clear,
                        material_top=C.M.roof_grey, role="mass"))
    b = C.MeshBuilder()
    ring = C.ring_coords(Pgef)
    per = sum(e[2] for e in C.edges_of(ring))
    spacing = per / GEFFEN_PIERS
    placed = 0
    for p0, p1, L, t, n in C.edges_of(ring):
        k = 0
        while k * spacing < L and placed < GEFFEN_PIERS:
            q = p0 + t * (k * spacing + spacing / 2)
            b.hull([(q[0] - 0.85, q[1] - 0.85, 2.4), (q[0] + 0.85, q[1] - 0.85, 2.4),
                    (q[0] + 0.85, q[1] + 0.85, 2.4), (q[0] - 0.85, q[1] + 0.85, 2.4),
                    (q[0] - 0.45, q[1] - 0.45, 2.4 + GEFFEN_PIER_H), (q[0] + 0.45, q[1] - 0.45, 2.4 + GEFFEN_PIER_H),
                    (q[0] + 0.45, q[1] + 0.45, 2.4 + GEFFEN_PIER_H), (q[0] - 0.45, q[1] + 0.45, 2.4 + GEFFEN_PIER_H)],
                   trav)
            placed += 1
            k += 1
    b.prism(ring, 2.4 + GEFFEN_PIER_H, GEFFEN_TOP, trav,
            holes=[C.ring_coords(C.offset_polygon(Pgef, -2.6))], cap_bottom=True)
    objs.append(b.build(f"{ID}_geffen_colonnade"))

    # ---- David H. Koch Theater -------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_koch_base", Pkoch, 0.0, 2.4, trav, material_top=C.M.roof_grey))
    fen_k = C.Fenestration(floor_h=(KOCH_TOP - 2.4) / 4, bay_w=6.1, window_frac=0.68, recess=1.6, spandrel_h=1.4,
                           spandrel_proud=0.2, pier="marble_white", spandrel="marble_white", glass="glass_dark")
    objs += C.tower_tier(f"{ID}_koch", Pkoch, 2.4, KOCH_TOP, fen_k, roof_material="roof_grey", parapet_h=1.2,
                         parapet_t=0.7)
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: three real OTI footprints; the Met Opera's five travertine arches at "
                          "96 ft = 29.3 m over a plaza front and its 37.7 m fly tower; Geffen Hall's 44 tapering "
                          "travertine piers 24.4 m tall around a glazed lobby, roof 27.4 m; the Koch Theater's "
                          "four-storey loggia on a 6.1 m module, roof 31.7 m; the 11.0 m Revson Fountain. Inferred "
                          "(stated): the arch widths (the Met's east edge divided into five bays), the even "
                          "distribution of the published 44 Geffen piers, and the storey heights. Not modelled: the "
                          "auditoria and interiors, the Chagall murals, the Henry Moore figure in the north pool, "
                          "the underground garage."),
                      dimensions={"met_arch_h_m": MET_ARCH_H, "met_arches": MET_ARCHES, "met_top_m": MET_TOP,
                                  "geffen_top_m": GEFFEN_TOP, "geffen_piers": GEFFEN_PIERS,
                                  "geffen_pier_h_m": GEFFEN_PIER_H, "koch_top_m": KOCH_TOP,
                                  "revson_fountain_d_m": FOUNTAIN_D})
    cc.render(ID, [
        {"view": "plaza", "azimuth_deg": 90, "elevation_deg": "street", "distance": 120, "fov_deg": 66, "look_up_deg": 18},
        {"view": "aerial", "azimuth_deg": 100, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
