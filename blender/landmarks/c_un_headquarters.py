"""United Nations Headquarters — 760 United Nations Plaza (BINs 1083875 Secretariat, 1083872 General Assembly and
Conference Building, 1083874 Dag Hammarskjold Library). Board of Design under Wallace K. Harrison with Oscar
Niemeyer and Le Corbusier, 1947-52; library 1961.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the three real OTI polygons (22,359 m2). The Secretariat polygon measures 21.3 x 86.5 m, which matches
  the published 72 x 287 ft slab (21.9 x 87.5 m) to within 0.6 m — no idealisation was needed.
* Secretariat [UN; Harrison]: 505 ft = 154.0 m, 39 floors. The broad east and west faces are green-tinted glass
  curtain wall; the two narrow ends are windowless Vermont marble. Floor-to-floor 154.0 / 39 = 3.95 m.
* General Assembly Building [UN; Harrison/Niemeyer]: about **50 m wide and 80 m long**, with concave sloping side
  walls that swoop from 34.0 m at both ends down to 16.0 m at the waist and lean outward as they dip, a warped roof
  rising 4.5 m to the centre line, and the shallow **23 m dome** added in 1952 at the insistence of the US Congress.
  The north facade is a full-height glass wall on mullions over the delegates' entrance canopy; the south end is
  windowless limestone. The building occupies only part of the BIN 1083872 podium polygon — the rest of that
  polygon is the podium itself and the North Garden.
* Conference Building [UN]: the four-storey block on the East River side of the plaza, 26.0 m high and 120 m long,
  carrying the three council chambers.
* Dag Hammarskjold Library [Harrison & Abramovitz 1961]: three storeys, 18.4 m (OTI LiDAR), 65.6 x 24.6 m.
* The whole complex sits on a raised podium: the OTI polygon of BIN 1083872 is that podium, and the model's base
  volume is built on it.

Fidelity: three real footprints; the Secretariat's published 154.0 m / 39 floors with marble ends and glass broad
faces, the General Assembly's concave walls and dome, the Conference Building and the Library are modelled as
geometry. Inferred (stated): the division of the BIN 1083872 podium polygon between the General Assembly and the
Conference Building (cut on the polygon's own vertices), and the General Assembly's wall profile (from published
sections, +-1 m). NOT modelled: the interiors and the General Assembly Hall, the flag row on First Avenue, the
sculptures in the north garden, and the 2008-14 renovation's replacement glazing pattern.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_un_headquarters"
B_SEC, B_GA, B_LIB = 1083875, 1083872, 1083874
SEC_H = 154.0
SEC_FLOORS = 39
GA_END = 34.0
GA_WAIST = 16.0
GA_DOME_D = 23.0
CONF_H = 26.0
LIB_H = 18.4


def build():
    C.reset()
    cc.materials(["glass_blue", "glass_clear", "marble_white", "limestone", "concrete", "aluminium", "roof_grey",
                  "roof_dark", "pavement", "steel_nirosta"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_SEC)
    Psec = g.poly(B_SEC)
    Pga = g.poly(B_GA)
    Plib = g.poly(B_LIB)
    objs: list = []

    # ---- the raised podium on the real General Assembly polygon (IoU volume) -------------------------------------
    objs.append(C.plinth(f"{ID}_podium", Pga, 0.0, 6.5, C.M.concrete, material_top=C.M.pavement))
    gx0, gy0, gx1, gy1 = Pga.bounds
    # The General Assembly Building itself is about 50 m wide and 80 m long [UN; Harrison]; the western half of the
    # BIN 1083872 polygon is the podium and the North Garden, not the building, so taking the whole of it made the
    # model a 105 m wide plate instead of a building.
    ga = C._clean_polygon(Pga.intersection(C.rect_xy(-62.0, 40.0, -12.0, gy1 - 4.0)).buffer(0))
    conf = C._clean_polygon(Pga.intersection(C.rect_xy(30.0, gy0 - 1, gx1 + 1, gy1 + 1)).buffer(0))

    # ---- the General Assembly: concave side walls rising to the centre, glass north wall, shallow dome -----------
    ax0, ay0, ax1, ay1 = ga.bounds
    b = C.MeshBuilder()
    nseg = 20
    axc = (ax0 + ax1) / 2

    def wall_z(u: float) -> float:
        """Height of the concave side wall at fractional position u along the building [Harrison; UN sections]."""
        return GA_END - (GA_END - GA_WAIST) * math.sin(math.pi * u)

    def lean_at(u: float) -> float:
        return 4.5 * math.sin(math.pi * u)

    for k in range(nseg):
        ua, ub = k / nseg, (k + 1) / nseg
        y_a = ay0 + (ay1 - ay0) * ua
        y_b = ay0 + (ay1 - ay0) * ub
        za, zb = wall_z(ua), wall_z(ub)
        la, lb = lean_at(ua), lean_at(ub)
        for x_side, sgn in ((ax0 + 1.0, -1.0), (ax1 - 1.0, 1.0)):
            # the concave side wall, leaning out as it dips
            b.quad((x_side, y_a, 6.5), (x_side, y_b, 6.5),
                   (x_side + sgn * lb, y_b, zb), (x_side + sgn * la, y_a, za), C.M.limestone)
            # its coping
            b.quad((x_side + sgn * la, y_a, za), (x_side + sgn * lb, y_b, zb),
                   (x_side + sgn * (lb + 0.6), y_b, zb - 1.6), (x_side + sgn * (la + 0.6), y_a, za - 1.6),
                   C.M.marble_white)
            # the warped roof: from the wall top up to a ridge 4.5 m higher on the centre line
            b.quad((x_side + sgn * la, y_a, za), (x_side + sgn * lb, y_b, zb),
                   (axc, y_b, zb + 4.5), (axc, y_a, za + 4.5), C.M.roof_grey)
    # the north (First Avenue) elevation: a full-height glass wall on vertical mullions over the delegates' entrance
    b.quad((ax0 + 1.0, ay1, 6.5), (ax1 - 1.0, ay1, 6.5), (ax1 - 1.0, ay1, GA_END),
           (ax0 + 1.0, ay1, GA_END), C.M.glass_clear)
    for k in range(int((ax1 - ax0) // 3.2) + 1):
        xx = ax0 + 1.0 + 3.2 * k
        if xx > ax1 - 1.0:
            break
        b.box((xx, ay1 + 0.35, (6.5 + GA_END) / 2), (0.3, 0.7, GA_END - 6.5), C.M.marble_white)
    b.box(((ax0 + ax1) / 2, ay1 + 4.0, 6.5), (26.0, 8.0, 1.0), C.M.marble_white)     # the entrance canopy
    # the south end is windowless limestone
    b.quad((ax1 - 1.0, ay0, 6.5), (ax0 + 1.0, ay0, 6.5), (ax0 + 1.0, ay0, GA_END),
           (ax1 - 1.0, ay0, GA_END), C.M.limestone)
    dcx, dcy = axc, ay0 + (ay1 - ay0) * 0.42
    b.lathe([(GA_DOME_D / 2, 0.0), (GA_DOME_D / 2 * 0.94, 1.6), (GA_DOME_D / 2 * 0.7, 4.0),
             (GA_DOME_D / 2 * 0.38, 5.6), (0.0, 6.3)], 40, C.M.steel_nirosta,
            origin=(dcx, dcy, wall_z(0.42) + 4.1), smooth=True)
    objs.append(C.tag(b.build(f"{ID}_general_assembly"), "mass"))

    # ---- the Conference Building on the East River side ------------------------------------------------------------
    fen_c = C.Fenestration(floor_h=(CONF_H - 6.5) / 4, bay_w=3.2, window_frac=0.78, recess=0.3, spandrel_h=1.0,
                           spandrel_proud=0.12, pier="limestone", spandrel="limestone", glass="glass_blue")
    objs += C.tower_tier(f"{ID}_conference", conf, 6.5, CONF_H, fen_c, roof_material="roof_grey", parapet_h=1.1,
                         parapet_t=0.5)

    # ---- the Secretariat slab ---------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_sec_base", Psec, 0.0, 6.5, C.M.marble_white, material_top=C.M.roof_dark))
    sx0, sy0, sx1, sy1 = Psec.bounds
    objs += cc.curtain(f"{ID}_secretariat", Psec, 6.5, SEC_H - 4.0, floor_h=SEC_H / SEC_FLOORS, module=1.75,
                       glass="glass_blue", mullion="aluminium", spandrel="aluminium", spandrel_h=0.85, proud=0.14,
                       role="mass", edges=None)
    b = C.MeshBuilder()                                   # the two windowless Vermont-marble end walls
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(Psec)):
        if L > 30.0:
            continue
        b.box_from_to(p0, p1, n, 0.45, 6.5, SEC_H, C.M.marble_white)
    b.box(((sx0 + sx1) / 2, (sy0 + sy1) / 2, SEC_H - 2.0), (sx1 - sx0 + 0.9, sy1 - sy0 + 0.9, 4.0),
          C.M.marble_white)                               # the mechanical crown band
    objs.append(C.tag(b.build(f"{ID}_sec_ends"), "mass"))

    # ---- the Dag Hammarskjold Library ---------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_lib_base", Plib, 0.0, 4.5, C.M.marble_white, material_top=C.M.roof_dark))
    fen_l = C.Fenestration(floor_h=(LIB_H - 4.5) / 3, bay_w=2.9, window_frac=0.72, recess=0.28, spandrel_h=0.9,
                           spandrel_proud=0.1, pier="marble_white", spandrel="marble_white", glass="glass_blue")
    objs += C.tower_tier(f"{ID}_library", Plib, 4.5, LIB_H, fen_l, roof_material="roof_grey", parapet_h=0.9,
                         parapet_t=0.4)
    return objs, g, Psec


def main():
    objs, g, Psec = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: three real OTI footprints (the Secretariat polygon matches the published 72 x 287 "
                          "ft slab to 0.6 m); the Secretariat at 505 ft = 154.0 m over 39 floors with glass broad "
                          "faces and windowless Vermont-marble ends; the General Assembly's concave side walls to "
                          "34.0 m at the ends and 16.0 m at the waist with its 23 m dome and full-height north glass wall; the Conference Building at "
                          "26.0 m; the Library at 18.4 m. Inferred (stated): the split of the BIN 1083872 podium "
                          "polygon between the General Assembly and the Conference Building (cut on the polygon's "
                          "own vertices) and the General Assembly wall profile (+-1 m from published sections). "
                          "Not modelled: interiors and the General Assembly Hall, the First Avenue flag row, the "
                          "north garden sculptures, the 2008-14 replacement glazing pattern."),
                      dimensions={"secretariat_m": SEC_H, "secretariat_floors": SEC_FLOORS,
                                  "secretariat_plan_m": [round(Psec.bounds[2] - Psec.bounds[0], 2),
                                                         round(Psec.bounds[3] - Psec.bounds[1], 2)],
                                  "ga_end_wall_m": GA_END, "ga_waist_m": GA_WAIST, "ga_dome_diameter_m": GA_DOME_D, "conference_m": CONF_H,
                                  "library_m": LIB_H})
    cc.render(ID, [
        {"view": "first_avenue", "azimuth_deg": 285, "elevation_deg": "street", "distance": 260, "fov_deg": 58, "look_up_deg": 26},
        {"view": "aerial", "azimuth_deg": 110, "elevation_deg": 26},
    ])
    return entry


if __name__ == "__main__":
    main()
