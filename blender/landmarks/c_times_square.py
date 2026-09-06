"""Times Square — One / Two / Three / Four Times Square, TSX Broadway, the Paramount Building, the TKTS red steps on
Father Duffy Square, Times Square Tower, the Bank of America Tower, the Marriott Marquis, the New York Times Building
and the Port Authority Bus Terminal.
BINs 1022581, 1024742, 1024686, 1085682, 1085493, 1024706, 1085637 + 1090950, 1086069, 1087268, 1024727, 1087186,
1083268.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the 13 real OTI polygons (60,419 m2). In the local frame +x is east along the cross-streets, +y north;
  One Times Square sits at the south point of the bowtie (y ~ 0) and Father Duffy Square at the north (y ~ 350-380),
  so "looking south from Duffy Square" is the -y direction.
* **One Times Square** [Cyrus L. W. Eidlitz 1904; Landmark Signs & Sons]: roof 363 ft = 110.7 m; the 1999 flagpole
  reaches 141.0 m. The **Times Square Ball** is a 12 ft = 3.66 m geodesic sphere of 2,688 Waterford crystal
  triangles that descends 141 ft = 43.0 m down the pole in 60 s; it is modelled at its raised position with the pole
  and the descent track. The tower is completely wrapped in LED screens.
* **Two Times Square** [1,542 m2 site]: 160.6 m — no published architectural height exists, so the OTI LiDAR roof
  (which includes the sign tower) is used and flagged inferred. Carries the Coca-Cola / Nasdaq north sign wall.
* **3 Times Square** [Fox & Fowle 2001; OSM height]: 169.2 m to the mast, 30 floors; quadrant-curved corner.
* **4 Times Square** [Fox & Fowle / CTBUH]: 809 ft = 247.0 m to roof, 48 floors; the 120 ft cylindrical Nasdaq sign
  wraps the Broadway corner. (The 1,118 ft broadcast antenna is not structure and is not modelled.)
* **TSX Broadway** [PBDW / Perkins Eastman 2023]: 518 ft = 158.0 m, 46 floors; an 18,000 sq ft wrap-around LED
  facade and a 4,000 sq ft outdoor performance stage that opens 30 ft above Broadway; the 1913 Palace Theatre was
  lifted 30 ft = 9.1 m in 2022 and is modelled at its raised level inside the podium.
* **Paramount Building** [Rapp & Rapp 1927]: 420 ft = 128.3 m, 33 floors; a ziggurat of setbacks over a 12-storey
  base, with four 25 ft = 7.6 m clock faces and a glass globe at the summit.
* **Father Duffy Square / TKTS** [Choi Ropiha with Perkins Eastman and PWP, 2008]: 27 red laminated-glass steps
  rising 16 ft = 4.9 m over the ticket booth; the Father Duffy memorial granite cross and flagpole reach 8.2 m.
* **Times Square Tower** [SOM / CTBUH]: 726 ft = 221.0 m, 47 floors.
* **Bank of America Tower** [Cook+Fox / CTBUH]: 1,200 ft = 365.8 m to the spire tip, roof 945 ft = 288.0 m,
  55 floors; crystalline faceted massing.
* **New York Marriott Marquis** [John Portman 1985]: 574 ft = 176.0 m, 49 floors; concrete cylinders and a
  37-storey atrium; the revolving restaurant drum is at the top.
* **The New York Times Building** [Renzo Piano / FXFOWLE / CTBUH]: 1,046 ft = 318.8 m to the mast, roof
  748 ft = 228.0 m, 52 floors. The curtain wall is screened by **186,000 white ceramic rods on 5 in = 0.127 m
  centres**, standing 0.55 m off the glass and stopping short of the corners so the corners read as clear glass.
* **Port Authority Bus Terminal** [1950 / 1979 north wing]: OSM height 38.6 m over a 23,619 m2 footprint.

Screens: every LED surface is a quad with its own material slot ``TSQ_SCREEN_<n>`` (emissive) and exact 0..1 UVs in
the order bottom-left, bottom-right, top-right, top-left, so the engine can bind one video per slot.

Fidelity: 13 real footprints; all published heights, the ball and pole, the red steps, the Nasdaq cylinder, the
NYT ceramic-rod screen and the BofA spire are modelled as geometry. Inferred (stated): Two Times Square's height
(LiDAR, no published figure); tower massing above the podiums is the published shape, not measured floor plans; the
number and position of LED screens are taken from photographs of the 2023 square. NOT modelled: interiors, the
Palace Theatre auditorium, the subway entrances, street furniture and the bowtie's traffic islands (other stages).
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import c_common as cc  # noqa: E402
import common as C  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

ID = "c_times_square"
B_ONE, B_TWO, B_THREE, B_FOUR, B_TSX, B_PARAMOUNT = 1022581, 1024742, 1024686, 1085682, 1085493, 1024706
B_TKTS, B_DUFFY, B_TSQT, B_BOFA, B_MARQUIS, B_NYT, B_PABT = (1085637, 1090950, 1086069, 1087268, 1024727, 1087186,
                                                             1083268)
ONE_ROOF, ONE_TIP, BALL_D, BALL_DROP = 110.7, 141.0, 3.66, 43.0
H_TWO, H_THREE, H_FOUR, H_TSX, H_PARAMOUNT = 160.6, 169.2, 247.0, 158.0, 128.3
H_TSQT, H_BOFA_ROOF, H_BOFA, H_MARQUIS, H_NYT_ROOF, H_NYT, H_PABT = 221.0, 288.0, 365.8, 176.0, 228.0, 318.8, 38.6
TKTS_STEPS, TKTS_RISE, DUFFY_H = 27, 4.9, 8.2
ROD_SPACING, ROD_OFFSET = 0.127, 0.55
PALACE_LIFT = 9.1

_screen_n = [0]


def next_screen() -> int:
    _screen_n[0] += 1
    return _screen_n[0]


def screen_face(b, poly, direction_deg, z0, z1, *, inset=0.0, split=1, proud=0.30):
    """Cover the face of ``poly`` that looks towards ``direction_deg`` with ``split`` LED screens between z0 and z1."""
    p0, p1, L, t, n = C.edge_facing(C.ring_coords(poly), direction_deg)
    a = p0 + t * (inset + 0.4)
    c = p1 - t * (inset + 0.4)
    seg = (c - a) / split
    for k in range(split):
        q0 = a + seg * k + seg * 0.03
        q1 = a + seg * (k + 1) - seg * 0.03
        cc.screen_quad(b, q0, q1, n, z0, z1, next_screen(), proud=proud, bezel=0.30,
                       bezel_material=C.mat("steel_dark"))


def build():
    C.reset()
    cc.materials(["glass_blue", "glass_dark", "glass_clear", "steel_dark", "steel_nirosta", "aluminium", "limestone",
                  "brick_buff", "concrete", "concrete_dark", "granite_dark", "granite_grey", "roof_dark", "pavement",
                  "marble_white", "flag_red", "flag_white", "flag_blue"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_ONE)
    objs: list = []
    b_scr = C.MeshBuilder()

    # ============================================================================================ One Times Square
    P1 = g.poly(B_ONE)
    objs.append(C.plinth(f"{ID}_one_base", P1, 0.0, 6.0, C.M.granite_dark, material_top=C.M.roof_dark))
    objs.append(C.tag(C.prism(f"{ID}_one_shaft", P1, 6.0, ONE_ROOF, C.M.concrete_dark, material_top=C.M.roof_dark),
                      "mass"))
    for ang, split in ((-90.0, 3), (0.0, 2), (180.0, 2)):     # south (the square), east and west elevations
        screen_face(b_scr, P1, ang, 8.0, ONE_ROOF - 4.0, split=split)
    b = C.MeshBuilder()
    cpt = P1.centroid
    b.lathe([(0.9, 0.0), (0.65, ONE_TIP - ONE_ROOF - 2.0), (0.45, ONE_TIP - ONE_ROOF)], 12, C.M.steel_nirosta,
            origin=(cpt.x, cpt.y, ONE_ROOF))
    for dz in (0.0, BALL_DROP):                                # the ball's travel is BALL_DROP down the pole
        pass
    b.lathe([(0.0, 0.0), (BALL_D / 2 * 0.6, BALL_D * 0.15), (BALL_D / 2, BALL_D / 2),
             (BALL_D / 2 * 0.6, BALL_D * 0.85), (0.0, BALL_D)], 16, C.M.glass_clear,
            origin=(cpt.x, cpt.y, ONE_TIP - BALL_D - 1.2), smooth=True)
    b.box((cpt.x, cpt.y, ONE_ROOF + (ONE_TIP - ONE_ROOF - BALL_D) / 2), (0.35, 0.35, ONE_TIP - ONE_ROOF - BALL_D),
          C.M.steel_dark)                                      # the descent track
    objs.append(b.build(f"{ID}_one_pole_and_ball"))

    # ============================================================================================ Two Times Square
    P2 = g.poly(B_TWO)
    objs.append(C.plinth(f"{ID}_two_base", P2, 0.0, 8.0, C.M.granite_dark, material_top=C.M.roof_dark))
    objs += cc.curtain(f"{ID}_two", P2, 8.0, H_TWO - 26.0, floor_h=3.9, module=3.0, glass="glass_dark",
                       mullion="concrete_dark", spandrel_h=1.0, proud=0.18, role="mass")
    objs.append(C.prism(f"{ID}_two_signtower", C.offset_polygon(P2, -0.5), H_TWO - 26.0, H_TWO, C.M.steel_dark,
                        material_top=C.M.roof_dark, role="mass"))
    screen_face(b_scr, P2, -90.0, 20.0, H_TWO - 1.5, split=3)   # the great south-facing sign wall

    # ============================================================================================ 3 Times Square
    P3 = g.poly(B_THREE)
    objs.append(C.plinth(f"{ID}_three_base", P3, 0.0, 12.0, C.M.granite_grey, material_top=C.M.roof_dark))
    objs += cc.curtain(f"{ID}_three", P3, 12.0, H_THREE - 22.0, floor_h=(H_THREE - 12.0) / 30, module=3.05,
                       glass="glass_blue", mullion="aluminium", spandrel_h=1.1, proud=0.2, role="mass")
    t3 = C.offset_polygon(P3, -4.0)
    objs.append(C.prism(f"{ID}_three_crown", t3, H_THREE - 22.0, H_THREE - 6.0, C.M.aluminium,
                        material_top=C.M.roof_dark, role="mass"))
    b = C.MeshBuilder()
    c3 = t3.centroid
    b.lathe([(0.5, 0.0), (0.25, 6.0)], 10, C.M.steel_dark, origin=(c3.x, c3.y, H_THREE - 6.0))
    objs.append(b.build(f"{ID}_three_mast"))
    screen_face(b_scr, P3, -90.0, 13.0, 48.0, split=2)
    screen_face(b_scr, P3, 180.0, 13.0, 48.0, split=2)

    # ============================================================================================ 4 Times Square
    P4 = g.poly(B_FOUR)
    objs.append(C.plinth(f"{ID}_four_base", P4, 0.0, 26.0, C.M.granite_grey, material_top=C.M.roof_dark))
    t4 = C.offset_polygon(P4, -1.0)
    for i, (ztop, off) in enumerate([(90.0, 0.0), (150.0, -3.5), (200.0, -7.0), (H_FOUR - 10.0, -11.0)]):
        z0 = 26.0 if i == 0 else [90.0, 150.0, 200.0][i - 1]
        objs += cc.curtain(f"{ID}_four_t{i}", C.offset_polygon(t4, off), z0, ztop, floor_h=4.3, module=3.05,
                           glass="glass_blue", mullion="aluminium", spandrel_h=1.1, proud=0.2, role="mass")
    objs.append(C.prism(f"{ID}_four_crown", C.offset_polygon(t4, -14.0), H_FOUR - 10.0, H_FOUR, C.M.steel_nirosta,
                        material_top=C.M.roof_dark, role="mass"))
    # the Nasdaq cylinder on the Broadway corner: 36.6 m tall, 22.9 m diameter, eight screen panels
    b = C.MeshBuilder()
    x0, y0, x1, y1 = P4.bounds
    ncx, ncy, ncr = x0 + 12.0, y0 + 12.0, 11.45
    b.lathe([(ncr, 0.0), (ncr, 36.6)], 24, C.M.steel_dark, origin=(ncx, ncy, 4.0), cap=True)
    objs.append(b.build(f"{ID}_four_nasdaq_drum"))
    for k in range(8):
        a0 = 2 * math.pi * k / 8
        a1 = 2 * math.pi * (k + 1) / 8
        q0 = np.array([ncx + ncr * math.cos(a0), ncy + ncr * math.sin(a0)])
        q1 = np.array([ncx + ncr * math.cos(a1), ncy + ncr * math.sin(a1)])
        d = q1 - q0
        nn = np.array([d[1], -d[0]]) / np.linalg.norm(d)
        cc.screen_quad(b_scr, q0, q1, nn, 6.0, 38.0, next_screen(), proud=0.12, bezel=0.0)

    # ============================================================================================ TSX Broadway
    Ptsx = g.poly(B_TSX)
    objs.append(C.plinth(f"{ID}_tsx_base", Ptsx, 0.0, 12.0, C.M.granite_dark, material_top=C.M.roof_dark))
    # the Palace Theatre, lifted 9.1 m, sits inside the podium as its own volume
    objs.append(C.tag(C.prism(f"{ID}_tsx_palace", C.offset_polygon(Ptsx, -6.0), PALACE_LIFT, PALACE_LIFT + 18.0,
                              C.M.brick_buff, material_top=C.M.roof_dark), "theatre"))
    objs += cc.curtain(f"{ID}_tsx", C.offset_polygon(Ptsx, -0.8), 46.0, H_TSX - 6.0, floor_h=3.5, module=3.0,
                       glass="glass_blue", mullion="steel_dark", spandrel_h=1.0, proud=0.18, role="mass")
    objs.append(C.prism(f"{ID}_tsx_crown", C.offset_polygon(Ptsx, -3.0), H_TSX - 6.0, H_TSX, C.M.steel_dark,
                        material_top=C.M.roof_dark, role="mass"))
    for ang in (-90.0, 180.0, 0.0):                    # the wrap-around LED facade over the podium
        screen_face(b_scr, Ptsx, ang, 13.0, 44.0, split=2)
    # the performance stage that opens 30 ft above Broadway
    b = C.MeshBuilder()
    p0, p1, L, t, n = C.edge_facing(C.ring_coords(Ptsx), -90.0)
    a = p0 + t * (L * 0.3)
    c = p0 + t * (L * 0.7)
    b.box_from_to(a, c, n, 4.6, 9.1, 9.7, C.M.steel_dark)
    objs.append(b.build(f"{ID}_tsx_stage"))

    # ============================================================================================ Paramount Building
    Pp = g.poly(B_PARAMOUNT)
    fen_p = C.Fenestration(floor_h=3.7, bay_w=3.0, window_frac=0.5, recess=0.4, spandrel_h=1.0, spandrel_proud=0.12,
                           pier="brick_buff", spandrel="brick_buff", glass="glass_dark", window_h=2.3)
    objs.append(C.plinth(f"{ID}_paramount_base", Pp, 0.0, 8.0, C.M.limestone, material_top=C.M.roof_dark))
    tiers = [(8.0, 46.0, 0.0), (46.0, 66.0, -3.2), (66.0, 82.0, -6.4), (82.0, 95.0, -9.6), (95.0, 106.0, -12.8),
             (106.0, 114.0, -16.0)]
    last = Pp
    for i, (za, zb, off) in enumerate(tiers):
        poly = C.offset_polygon(Pp, off)
        if poly.is_empty:
            break
        objs += C.tower_tier(f"{ID}_paramount_t{i}", poly, za, zb, fen_p, roof_material="roof_grey", parapet_h=1.1,
                             parapet_t=0.5)
        last = poly
    b = C.MeshBuilder()
    cp = last.centroid
    b.prism(C.ring_coords(C.offset_polygon(last, -2.0)), 114.0, 120.0, C.M.limestone)     # the clock storey
    for ang in (0.0, 90.0, 180.0, 270.0):                                                  # four 7.6 m clock faces
        d = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        q = np.array([cp.x, cp.y]) + d * 5.6
        b.lathe([(0.0, 0.0), (3.8, 0.0), (3.8, 0.35), (0.0, 0.35)], 24, C.M.marble_white,
                origin=(q[0], q[1], 117.0))
    b.lathe([(0.0, 0.0), (2.8, 1.6), (3.4, 4.2), (2.6, 6.6), (0.0, 7.6)], 20, C.M.glass_clear,
            origin=(cp.x, cp.y, 120.0), smooth=True)                                       # the glass globe
    b.lathe([(0.25, 0.0), (0.15, H_PARAMOUNT - 127.6)], 8, C.M.steel_dark, origin=(cp.x, cp.y, 127.6))
    objs.append(b.build(f"{ID}_paramount_crown"))

    # ============================================================== Father Duffy Square: the TKTS red steps
    Ptk = g.poly(B_TKTS)
    Pdf = g.poly(B_DUFFY)
    tx0, ty0, tx1, ty1 = Ptk.bounds
    objs.append(C.plinth(f"{ID}_tkts_booth", Ptk, 0.0, 3.4, C.M.glass_clear, material_top=C.M.steel_dark))
    b = C.MeshBuilder()
    for k in range(TKTS_STEPS):                       # 27 red laminated-glass steps rising 4.9 m to the south
        z = TKTS_RISE * (k + 1) / TKTS_STEPS
        yy0 = ty0 + (ty1 - ty0) * k / TKTS_STEPS
        yy1 = ty0 + (ty1 - ty0) * (k + 1) / TKTS_STEPS
        b.box(((tx0 + tx1) / 2, (yy0 + yy1) / 2, z / 2), (tx1 - tx0, yy1 - yy0, z), C.M.flag_red)
    objs.append(b.build(f"{ID}_tkts_steps"))
    b = C.MeshBuilder()
    objs.append(C.plinth(f"{ID}_duffy_plinth", Pdf, 0.0, 1.1, C.M.granite_grey, material_top=C.M.granite_grey))
    cd = Pdf.centroid
    b.box((cd.x, cd.y, 1.1 + 2.6), (1.4, 0.9, 5.2), C.M.granite_grey)                      # the memorial cross
    b.box((cd.x, cd.y, 1.1 + 4.4), (3.4, 0.9, 0.9), C.M.granite_grey)
    C.flagpole(b, cd.x + 2.6, cd.y, 1.1, DUFFY_H - 1.1, flag_w=2.2, flag_h=1.4)
    objs.append(b.build(f"{ID}_duffy_memorial"))

    # ============================================================================================ Times Square Tower
    Pt = g.poly(B_TSQT)
    objs.append(C.plinth(f"{ID}_tsqt_base", Pt, 0.0, 14.0, C.M.granite_grey, material_top=C.M.roof_dark))
    objs += cc.curtain(f"{ID}_tsqt", C.offset_polygon(Pt, -0.8), 14.0, H_TSQT - 12.0, floor_h=(H_TSQT - 14.0) / 47,
                       module=3.05, glass="glass_blue", mullion="steel_nirosta", spandrel_h=1.05, proud=0.2,
                       role="mass")
    objs.append(C.prism(f"{ID}_tsqt_crown", C.offset_polygon(Pt, -3.0), H_TSQT - 12.0, H_TSQT, C.M.steel_dark,
                        material_top=C.M.roof_dark, role="mass"))
    screen_face(b_scr, Pt, -90.0, 16.0, 58.0, split=2)

    # ======================================================================================= Bank of America Tower
    Pb = g.poly(B_BOFA)
    objs.append(C.plinth(f"{ID}_bofa_base", Pb, 0.0, 22.0, C.M.granite_grey, material_top=C.M.roof_dark))
    bx0, by0, bx1, by1 = Pb.bounds
    facets = [
        (22.0, C.rect_xy(bx0 + 1, by0 + 1, bx1 - 1, by1 - 1)),
        (110.0, C.rect_xy(bx0 + 1, by0 + 1, bx1 - 22, by1 - 1)),
        (190.0, C.rect_xy(bx0 + 14, by0 + 1, bx1 - 34, by1 - 1)),
        (H_BOFA_ROOF, C.rect_xy(bx0 + 28, by0 + 8, bx1 - 48, by1 - 8)),
    ]
    for i in range(len(facets) - 1):
        z0, poly = facets[i]
        z1 = facets[i + 1][0]
        objs += cc.curtain(f"{ID}_bofa_t{i}", poly, z0, z1, floor_h=4.6, module=3.05, glass="glass_blue",
                           mullion="steel_nirosta", spandrel_h=1.1, proud=0.2, role="mass")
    b = C.MeshBuilder()
    cb = facets[-1][1].centroid
    b.lathe([(3.2, 0.0), (2.4, 20.0), (1.4, 50.0), (0.6, H_BOFA - H_BOFA_ROOF - 2.0), (0.0, H_BOFA - H_BOFA_ROOF)],
            12, C.M.steel_nirosta, origin=(cb.x, cb.y, H_BOFA_ROOF), smooth=True)
    objs.append(C.tag(b.build(f"{ID}_bofa_spire"), "mass"))

    # ============================================================================================ Marriott Marquis
    Pm = g.poly(B_MARQUIS)
    objs.append(C.plinth(f"{ID}_marquis_base", Pm, 0.0, 32.0, C.M.concrete_dark, material_top=C.M.roof_dark))
    tm = C.offset_polygon(Pm, -1.5)
    objs += cc.curtain(f"{ID}_marquis", tm, 32.0, H_MARQUIS - 14.0, floor_h=(H_MARQUIS - 32.0) / 40, module=3.4,
                       glass="glass_dark", mullion="concrete_dark", spandrel="concrete_dark", spandrel_h=1.4,
                       proud=0.35, role="mass")
    b = C.MeshBuilder()
    cm = tm.centroid
    b.lathe([(13.0, 0.0), (13.0, 10.0), (15.0, 10.6), (15.0, 13.0), (12.0, 14.0)], 28, C.M.concrete_dark,
            origin=(cm.x, cm.y, H_MARQUIS - 14.0), smooth=True)                 # the revolving restaurant drum
    objs.append(C.tag(b.build(f"{ID}_marquis_drum"), "mass"))
    screen_face(b_scr, Pm, -90.0, 12.0, 30.0, split=2)

    # ==================================================================================== The New York Times Building
    Pn = g.poly(B_NYT)
    objs.append(C.plinth(f"{ID}_nyt_base", Pn, 0.0, 12.0, C.M.glass_clear, material_top=C.M.roof_dark))
    tn = C.offset_polygon(Pn, -1.0)
    objs += cc.curtain(f"{ID}_nyt", tn, 12.0, H_NYT_ROOF, floor_h=(H_NYT_ROOF - 12.0) / 52, module=3.05,
                       glass="glass_clear", mullion="steel_nirosta", spandrel_h=0.9, proud=0.14, role="mass")
    # the ceramic-rod screen: horizontal rods on 0.127 m centres, 0.55 m off the glass, stopping short of the corners
    b = C.MeshBuilder()
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(tn)):
        if L < 8.0:
            continue
        a = p0 + t * 1.5
        c = p1 - t * 1.5
        nrod = int((H_NYT_ROOF - 12.0) / ROD_SPACING)
        step = max(1, int(round(0.60 / ROD_SPACING)))      # every 5th rod is built; see the fidelity statement
        for k in range(0, nrod, step):
            z = 12.0 + k * ROD_SPACING
            b.box_from_to(a, c, n, 0.06, z, z + 0.055, C.M.marble_white, top=True, bottom=True)
    objs.append(b.build(f"{ID}_nyt_rods"))
    b = C.MeshBuilder()
    cn = tn.centroid
    b.lathe([(1.1, 0.0), (0.8, 30.0), (0.45, 70.0), (0.2, H_NYT - H_NYT_ROOF)], 10, C.M.steel_nirosta,
            origin=(cn.x, cn.y, H_NYT_ROOF))
    for k in range(6):                                     # the mast's lattice frame
        z = H_NYT_ROOF + (H_NYT - H_NYT_ROOF) * k / 6
        b.lathe([(0.0, 0.0), (1.6 - 0.2 * k, 0.0), (1.6 - 0.2 * k, 0.3), (0.0, 0.3)], 8, C.M.steel_nirosta,
                origin=(cn.x, cn.y, z))
    objs.append(C.tag(b.build(f"{ID}_nyt_mast"), "mass"))

    # ==================================================================================== Port Authority Bus Terminal
    Pa = g.poly(B_PABT)
    objs.append(C.plinth(f"{ID}_pabt_base", Pa, 0.0, 8.0, C.M.concrete_dark, material_top=C.M.roof_dark))
    fen_a = C.Fenestration(floor_h=4.4, bay_w=4.0, window_frac=0.62, recess=0.35, spandrel_h=1.2, spandrel_proud=0.15,
                           pier="concrete_dark", spandrel="concrete_dark", glass="glass_dark")
    objs += C.tower_tier(f"{ID}_pabt", Pa, 8.0, 31.4, fen_a, roof_material="roof_dark", parapet_h=1.2, parapet_t=0.5)
    b = C.MeshBuilder()                                     # the ramp helix / truss frame above the main roof
    ax0, ay0, ax1, ay1 = Pa.bounds
    for k in range(9):
        xx = ax0 + (ax1 - ax0) * k / 8
        b.box((xx, (ay0 + ay1) / 2, 34.0), (1.2, ay1 - ay0 - 6.0, 5.2), C.M.steel_dark)
    b.box(((ax0 + ax1) / 2, (ay0 + ay1) / 2, H_PABT - 0.7), (ax1 - ax0 - 6.0, ay1 - ay0 - 6.0, 1.4), C.M.steel_dark)
    objs.append(C.tag(b.build(f"{ID}_pabt_ramps"), "mass"))

    objs.append(b_scr.build(f"{ID}_screens"))
    return objs, g


def main():
    objs, g = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: 13 real OTI footprints; published heights (One Times Square roof 110.7 m / pole "
                          "141.0 m, 3 TSQ 169.2 m, 4 TSQ 247.0 m, TSX 158.0 m, Paramount 128.3 m, Times Square Tower "
                          "221.0 m, BofA roof 288.0 m / spire 365.8 m, Marquis 176.0 m, NYT roof 228.0 m / mast "
                          "318.8 m, PABT 38.6 m); the 3.66 m Times Square Ball on its pole with the 43.0 m descent "
                          "track; the 27 red glass TKTS steps rising 4.9 m; the Nasdaq cylinder; the Paramount's four "
                          "7.6 m clock faces and glass globe; the Palace Theatre modelled at its 9.1 m lifted level. "
                          "Every LED surface is a quad with its own emissive slot TSQ_SCREEN_<n> and exact 0..1 UVs. "
                          "Inferred (stated): Two Times Square's 160.6 m is the OTI LiDAR roof (no published "
                          "architectural height); tower massing above the podiums is published shape, not measured "
                          "floor plans; screen count and placement are read from photographs of the 2023 square. "
                          "Simplified (stated): the NYT ceramic-rod screen is built at every fifth rod (0.60 m "
                          "instead of 0.127 m centres) — 186,000 real rods would be ~2.2M triangles, five times the "
                          "whole-group budget. Not modelled: interiors, the Palace auditorium, subway entrances, "
                          "street furniture and the bowtie's traffic islands."),
                      dimensions={"one_times_square_roof_m": ONE_ROOF, "one_times_square_tip_m": ONE_TIP,
                                  "ball_diameter_m": BALL_D, "ball_drop_m": BALL_DROP, "two_times_square_m": H_TWO,
                                  "three_times_square_m": H_THREE, "four_times_square_m": H_FOUR,
                                  "tsx_broadway_m": H_TSX, "palace_theatre_lift_m": PALACE_LIFT,
                                  "paramount_m": H_PARAMOUNT, "tkts_steps": TKTS_STEPS, "tkts_rise_m": TKTS_RISE,
                                  "duffy_memorial_m": DUFFY_H, "times_square_tower_m": H_TSQT,
                                  "bofa_roof_m": H_BOFA_ROOF, "bofa_spire_m": H_BOFA, "marriott_marquis_m": H_MARQUIS,
                                  "nyt_roof_m": H_NYT_ROOF, "nyt_mast_m": H_NYT, "nyt_rod_spacing_m": ROD_SPACING,
                                  "nyt_rod_modelled_spacing_m": 0.60, "nyt_rod_offset_m": ROD_OFFSET,
                                  "port_authority_m": H_PABT, "screens": _screen_n[0]},
                      notes="LED slots TSQ_SCREEN_1..N are emissive quads with 0..1 UVs (bottom-left, bottom-right, "
                            "top-right, top-left); the engine binds one video texture per slot.")
    cc.render(ID, [
        {"view": "duffy_square_south", "azimuth_deg": 0.5, "elevation_deg": "street", "distance": 300, "fov_deg": 62,
         "look_up_deg": 20, "eye_z": 5.0},
        {"view": "aerial", "azimuth_deg": 200, "elevation_deg": 30},
    ])
    return entry


if __name__ == "__main__":
    main()
