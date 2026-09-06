"""New York State Pavilion and the Queens Museum — Flushing Meadows Corona Park (BINs 4464054 Tent of Tomorrow,
4541449 Observation Towers, 4464056 Theaterama / Queens Theatre, 4458851 Queens Museum; LP-2318).
Philip Johnson & Richard Foster with Lev Zetlin, 1964 World's Fair; the museum is the 1939 New York City Building
(Aymar Embury II), remodelled by Grimshaw in 2013.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the four real OTI polygons (14,788 m2).
* Tent of Tomorrow [LPC designation report LP-2318; Johnson/Zetlin]: an ellipse **350 x 250 ft = 106.7 x 76.2 m**
  ringed by **16 concrete columns 100 ft = 30.5 m tall** carrying a cable-suspended roof; the terrazzo floor was a
  Texaco road map of New York State. The roof's coloured plastic panels are gone; the model shows the ring beam and
  the radial cable net, which is what stands today.
* Observation Towers [LP-2318]: three towers of **60, 150 and 226 ft = 18.3, 45.7 and 68.9 m**, each a slender
  concrete shaft with a circular observation platform on top; the tallest is the height of the model. Platform
  diameters 15.2 / 12.2 / 9.1 m from the tallest down.
* Theaterama / Queens Theatre [LP-2318]: a 27.4 m diameter concrete drum, 17.7 m high (OTI LiDAR), with the 1993
  glazed lobby addition.
* Queens Museum [Aymar Embury II 1939; Grimshaw 2013]: a 7,294 m2 rectangular block, 15.3 m high (OTI LiDAR), with
  a full-height glazed west facade and a limestone-clad body; it housed the UN General Assembly 1946-50 and holds
  the 870 m2 Panorama of the City of New York.

Fidelity: four real footprints; the Tent's 16 columns at 30.5 m on the measured ellipse with its ring beam and
cable net, the three towers at 18.3 / 45.7 / 68.9 m with their platforms, the Theaterama drum and the Queens Museum
are modelled as geometry. Inferred (stated): the platform diameters and shaft taper of the towers (from
photographs), the cable-net density, and the museum's storey heights. NOT modelled: the terrazzo map floor, the
Panorama, the remains of the roof's plastic panels, and the interiors.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c_common as cc  # noqa: E402
import common as C  # noqa: E402

ID = "c_flushing_meadows"
B_TENT, B_TOWERS, B_THEATERAMA, B_MUSEUM = 4464054, 4541449, 4464056, 4458851
TENT_A, TENT_B = 106.7, 76.2
TENT_COLUMNS, TENT_COLUMN_H = 16, 30.5
TOWERS = ((68.9, 9.1), (45.7, 12.2), (18.3, 15.2))
THEATERAMA_H, THEATERAMA_D = 17.7, 27.4
MUSEUM_H = 15.3


def build():
    C.reset()
    cc.materials(["concrete", "concrete_dark", "limestone", "glass_clear", "glass_dark", "steel_dark", "roof_grey",
                  "roof_dark", "pavement", "grass", "aluminium"])
    g = cc.Group(ID, origin_bin=B_TENT)
    Pt, Ptw, Pth, Pm = g.poly(B_TENT), g.poly(B_TOWERS), g.poly(B_THEATERAMA), g.poly(B_MUSEUM)
    objs: list = []

    # ---- Tent of Tomorrow --------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_tent_floor", Pt, 0.0, 0.9, C.M.concrete, material_top=C.M.pavement))
    tcx, tcy = Pt.centroid.x, Pt.centroid.y
    b = C.MeshBuilder()
    ring = []
    for k in range(TENT_COLUMNS):
        a = 2 * math.pi * k / TENT_COLUMNS
        qx = tcx + (TENT_A / 2 - 1.6) * math.cos(a)
        qy = tcy + (TENT_B / 2 - 1.6) * math.sin(a)
        ring.append((qx, qy))
        b.box((qx, qy, TENT_COLUMN_H / 2), (2.6, 2.6, TENT_COLUMN_H), C.M.concrete,
              rot_deg=math.degrees(a))
    cc.band_ring(b, ring, TENT_COLUMN_H - 3.2, TENT_COLUMN_H, 1.1, C.M.concrete)       # the ring beam
    for k in range(TENT_COLUMNS * 3):                                                   # the radial cable net
        a = 2 * math.pi * k / (TENT_COLUMNS * 3)
        q0 = (tcx + (TENT_A / 2 - 2.2) * math.cos(a), tcy + (TENT_B / 2 - 2.2) * math.sin(a))
        q1 = (tcx + 4.0 * math.cos(a), tcy + 4.0 * math.sin(a))
        b.hull([(q0[0] - 0.09, q0[1] - 0.09, TENT_COLUMN_H - 2.4), (q0[0] + 0.09, q0[1] + 0.09, TENT_COLUMN_H - 2.4),
                (q0[0] - 0.09, q0[1] + 0.09, TENT_COLUMN_H - 2.4), (q0[0] + 0.09, q0[1] - 0.09, TENT_COLUMN_H - 2.4),
                (q1[0] - 0.09, q1[1] - 0.09, TENT_COLUMN_H - 7.6), (q1[0] + 0.09, q1[1] + 0.09, TENT_COLUMN_H - 7.6),
                (q1[0] - 0.09, q1[1] + 0.09, TENT_COLUMN_H - 7.6), (q1[0] + 0.09, q1[1] - 0.09, TENT_COLUMN_H - 7.6)],
               C.M.steel_dark)
    for k in range(6):                                                                  # the inner tension ring
        pass
    cc.band_ring(b, [(tcx + 4.0 * math.cos(2 * math.pi * k / 24), tcy + 4.0 * math.sin(2 * math.pi * k / 24))
                     for k in range(24)], TENT_COLUMN_H - 8.0, TENT_COLUMN_H - 7.2, 0.5, C.M.steel_dark)
    objs.append(b.build(f"{ID}_tent"))

    # ---- the three Observation Towers ------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_towers_base", Ptw, 0.0, 1.2, C.M.concrete, material_top=C.M.pavement))
    wx0, wy0, wx1, wy1 = Ptw.bounds
    b = C.MeshBuilder()
    for i, (h, dia) in enumerate(TOWERS):
        qx = wx0 + (wx1 - wx0) * (0.28 + 0.24 * i)
        qy = wy0 + (wy1 - wy0) * (0.30 + 0.22 * i)
        b.lathe([(3.0, 0.0), (2.4, h * 0.25), (1.9, h - 6.0), (1.9, h - 5.0)], 16, C.M.concrete,
                origin=(qx, qy, 1.2), smooth=True)
        b.lathe([(0.0, 0.0), (dia / 2, 1.2), (dia / 2, 3.0), (dia / 2 - 1.2, 3.6), (0.0, 3.6)], 24, C.M.concrete,
                origin=(qx, qy, h - 4.8), smooth=False)
        cc.band_ring(b, [(qx + (dia / 2) * math.cos(2 * math.pi * k / 24), qy + (dia / 2) * math.sin(2 * math.pi * k / 24))
                         for k in range(24)], h - 1.2, h, 0.12, C.M.steel_dark)
    objs.append(C.tag(b.build(f"{ID}_towers"), "mass"))

    # ---- Theaterama --------------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_theaterama_base", Pth, 0.0, 1.0, C.M.concrete, material_top=C.M.pavement))
    hcx, hcy = Pth.centroid.x, Pth.centroid.y
    b = C.MeshBuilder()
    b.lathe([(THEATERAMA_D / 2, 0.0), (THEATERAMA_D / 2, THEATERAMA_H - 1.2), (THEATERAMA_D / 2 - 0.6, THEATERAMA_H),
             (0.0, THEATERAMA_H)], 32, C.M.concrete, origin=(hcx, hcy, 1.0), smooth=False)
    b.prism(C.ring_coords(C.offset_polygon(Pth, -0.5)), 1.0, 6.5, C.M.glass_clear, cap_top=False, cap_bottom=False)
    objs.append(C.tag(b.build(f"{ID}_theaterama"), "mass"))

    # ---- the Queens Museum ---------------------------------------------------------------------------------------
    objs.append(C.plinth(f"{ID}_museum_base", Pm, 0.0, 2.0, C.M.limestone, material_top=C.M.roof_grey))
    fen = C.Fenestration(floor_h=(MUSEUM_H - 2.0) / 3, bay_w=3.6, window_frac=0.55, recess=0.4, spandrel_h=1.0,
                         spandrel_proud=0.12, pier="limestone", spandrel="limestone", glass="glass_dark")
    objs += C.tower_tier(f"{ID}_museum", Pm, 2.0, MUSEUM_H - 1.0, fen, roof_material="roof_grey", parapet_h=1.0,
                         parapet_t=0.5)
    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(C.ring_coords(Pm), 180.0)      # the Grimshaw glazed west facade
    b.box_from_to(p0, p1, n, 0.5, 2.0, MUSEUM_H - 2.0, C.M.glass_clear)
    for k in range(int(L // 3.0) + 1):
        q = p0 + t * min(L, 3.0 * k)
        b.box((q[0] + n[0] * 0.55, q[1] + n[1] * 0.55, (MUSEUM_H + 2.0) / 2), (0.22, 0.5, MUSEUM_H - 4.0),
              C.M.aluminium, rot_deg=math.degrees(math.atan2(t[1], t[0])))
    objs.append(b.build(f"{ID}_museum_facade"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local, iou_z=0.5,
                      plan_polygon_note=("model section at z = 0.5 m: the Tent of Tomorrow's terrazzo floor and the "
                                         "tower and Theaterama plinths are at grade, so the standard 1.5 m slice would "
                                         "sit above them"),
                      fidelity_statement=(
                          "Exact: four real OTI footprints; the Tent of Tomorrow's 16 concrete columns at "
                          "100 ft = 30.5 m on the measured 106.7 x 76.2 m ellipse with its ring beam and radial "
                          "cable net (the lost plastic roof panels are correctly absent); the three Observation "
                          "Towers at 60 / 150 / 226 ft = 18.3 / 45.7 / 68.9 m with their platforms; the 27.4 m "
                          "Theaterama drum at 17.7 m with its 1993 glazed lobby; the Queens Museum at 15.3 m with "
                          "the Grimshaw glazed west facade. Inferred (stated): the tower platform diameters and "
                          "shaft taper (from photographs), the cable-net density, the museum's storey heights. Not "
                          "modelled: the terrazzo Texaco map floor, the Panorama of the City of New York, "
                          "interiors."),
                      dimensions={"tent_ellipse_m": [TENT_A, TENT_B], "tent_columns": TENT_COLUMNS,
                                  "tent_column_h_m": TENT_COLUMN_H,
                                  "tower_heights_m": [h for h, _ in TOWERS],
                                  "tower_platform_d_m": [d for _, d in TOWERS],
                                  "theaterama_m": [THEATERAMA_D, THEATERAMA_H], "queens_museum_m": MUSEUM_H})
    cc.render(ID, [
        {"view": "grand_central_parkway", "azimuth_deg": 200, "elevation_deg": "street", "fov_deg": 50, "look_up_deg": 10},
        {"view": "aerial", "azimuth_deg": 230, "elevation_deg": 28},
    ])
    return entry


if __name__ == "__main__":
    main()
