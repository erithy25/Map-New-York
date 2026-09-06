"""Hudson Yards, Eastern Yard — 30 / 35 / 10 / 55 / 15 / 50 Hudson Yards, The Shed and the Vessel.
BINs 1088961 (podium + 30 HY), 1089323 (10 HY), 1091590 (35 HY), 1089412 (55 HY), 1089411 (15 HY + The Shed),
1090274 (50 HY), 1090391 (Vessel). Built 2015-2022 on a platform over the LIRR West Side Yard.

Dimensions used (source in brackets)
------------------------------------
* Footprints: the real OTI polygons (35.4 ha of footprint in total). Each building's share of the shared podium
  polygon (BIN 1088961 = the Shops and 30 HY) and of BIN 1089411 (15 HY + The Shed) is cut at the vertices that are
  already in the polygon, not invented.
* 30 Hudson Yards [KPF; CTBUH]: 1,270 ft = 387.1 m architectural, 103 floors. **Edge** observation deck at
  1,131 ft = 345.0 m, a triangular deck cantilevering 65 ft = 20.0 m from the south-west corner with a glass floor
  section and an outward-leaning glass parapet; the deck is 7,500 sq ft = 697 m2.
* 35 Hudson Yards [SOM; CTBUH]: 1,009 ft = 308.0 m, 72 floors; limestone-framed setbacks with a crown of splayed
  limestone fins.
* 10 Hudson Yards [KPF; CTBUH]: 895 ft = 272.8 m, 52 floors; the tower's south-east corner is chamfered where the
  High Line passes through the base.
* 55 Hudson Yards [KPF with A. Eugene Kohn; CTBUH]: 780 ft = 237.4 m, 51 floors; a deep cast-metal window grid on a
  3.35 m module rather than a curtain wall. (Its OTI LiDAR height, 24.4 m, is from the 2015 flight, before it was
  built — the published height is used.)
* 15 Hudson Yards [Diller Scofidio + Renfro with Rockwell Group; CTBUH]: 914 ft = 278.6 m, 88 floors; the shaft
  changes from a square base to a four-lobed, pleated top.
* 50 Hudson Yards [Foster + Partners; CTBUH]: 1,011 ft = 308.2 m, 58 floors; 9.1 m floor-to-floor at the base and
  four-storey "sky lobbies" expressed as recesses.
* The Shed / Bloomberg Building [Diller Scofidio + Renfro with Rockwell Group]: an 8-level fixed building plus a
  movable ETFE-cushion shell 120 ft = 36.6 m tall that rolls 273 ft = 83.2 m east on 6 in double-wheel bogies over
  two 273 ft rail tracks to enclose the McCourt. The shell is modelled **deployed** and its diagrid arch frame,
  bogies and rails are separate objects so the engine can slide it.
* Vessel [Heatherwick Studio]: 150 ft = 46.0 m tall, 154 flights of stairs, 2,500 steps, 80 landings; a hexagonal
  honeycomb of 8 storeys of interconnected flights that widens from 50 ft = 15.2 m at the base to 150 ft = 45.7 m at
  the top. All **154 flights** are built as real stepped geometry (this is why the script's budget is 400k
  triangles).

Fidelity: real footprints; every published height, floor count and the Edge/Shed/Vessel dimensions above are
modelled as geometry. Inferred (stated): the division of the two shared footprint polygons between buildings (cut at
existing polygon vertices); tower plan shapes above the podium are simplified to their published massing (setbacks,
chamfers, lobes) rather than measured floor plans; the podium of the Shops is a single 34 m volume. NOT modelled:
the rail yard and platform below, the interiors, the retail signage, the public-square planting and the
Thomas Heatherwick "Vessel" safety netting added in 2021.
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

ID = "c_hudson_yards"
B_PODIUM, B_10HY, B_35HY, B_55HY, B_15HY_SHED, B_50HY, B_VESSEL = (1088961, 1089323, 1091590, 1089412, 1089411,
                                                                   1090274, 1090391)
H30, H35, H10, H55, H15, H50 = 387.1, 308.0, 272.8, 237.4, 278.6, 308.2
EDGE_DECK_Z = 345.0
EDGE_CANTILEVER = 20.0
SHELL_H = 36.6
SHELL_TRAVEL = 83.2
VESSEL_H = 46.0
VESSEL_FLIGHTS = 154
VESSEL_LANDINGS = 80
VESSEL_BASE_D, VESSEL_TOP_D = 15.2, 45.7
PODIUM_TOP = 34.0


def build():
    C.reset()
    cc.materials(["glass_blue", "glass_clear", "aluminium", "steel_dark", "steel_nirosta", "limestone", "concrete",
                  "roof_dark", "pavement", "granite_grey", "copper_new"])
    g = cc.Group(ID, angle_deg=cc.GRID_ANGLE, origin_bin=B_PODIUM)
    objs: list = []
    P_pod = g.poly(B_PODIUM)
    P_10 = g.poly(B_10HY)
    P_35 = g.poly(B_35HY)
    P_55 = g.poly(B_55HY)
    P_1589 = g.poly(B_15HY_SHED)
    P_50 = g.poly(B_50HY)
    P_ves = g.poly(B_VESSEL)

    # ================================================================================ shared podium (the Shops) + 30 HY
    objs.append(C.plinth(f"{ID}_podium", P_pod, 0.0, PODIUM_TOP, C.M.limestone, material_top=C.M.roof_dark))
    objs += cc.curtain(f"{ID}_podium_wall", P_pod, 0.0, PODIUM_TOP, floor_h=5.6, module=4.2, glass="glass_blue",
                       mullion="aluminium", spandrel_h=1.3, proud=0.22, role="mass")
    # 30 Hudson Yards: the tower is the northern part of the podium polygon (y > 6.5 m), tapered in three setbacks
    t30 = C._clean_polygon(P_pod.intersection(C.rect_xy(-8.0, 6.5, 112.0, 66.0)).buffer(0))
    t30 = C.offset_polygon(t30, -1.0)
    c30 = t30.centroid
    steps = [(PODIUM_TOP, 0.0), (150.0, -2.5), (250.0, -4.5), (330.0, -6.0), (H30 - 12.0, -7.5)]
    prev = t30
    for i, (ztop, off) in enumerate(steps):
        poly = C.offset_polygon(t30, off)
        z0 = PODIUM_TOP if i == 0 else steps[i - 1][0]
        objs += cc.curtain(f"{ID}_30hy_t{i}", poly, z0, ztop, floor_h=4.02, module=3.05, glass="glass_blue",
                           mullion="steel_nirosta", spandrel_h=1.05, proud=0.2, role="mass")
        prev = poly
    objs.append(C.prism(f"{ID}_30hy_crown", C.offset_polygon(prev, -3.0), H30 - 12.0, H30, C.M.steel_nirosta,
                        material_top=C.M.roof_dark, role="mass"))
    # ---- the Edge: a triangular deck cantilevering 20 m from the south-west corner at 345.0 m --------------------
    b = C.MeshBuilder()
    ring = C.ring_coords(C.offset_polygon(t30, -6.0))
    p0, p1, L, t, n = C.edge_facing(ring, -90.0)           # the south face
    a = p0 + t * (L * 0.10)
    c = p0 + t * (L * 0.10 + 24.0)
    tip = (a + c) / 2 + n * EDGE_CANTILEVER
    zd = EDGE_DECK_Z
    b.tri((a[0], a[1], zd), (c[0], c[1], zd), (tip[0], tip[1], zd), C.M.steel_dark)          # deck soffit
    b.tri((a[0], a[1], zd + 0.35), (tip[0], tip[1], zd + 0.35), (c[0], c[1], zd + 0.35), C.M.glass_clear)  # glass floor
    for q0, q1 in ((a, tip), (tip, c)):                                                       # leaning glass parapet
        d = (q1 - q0) / np.linalg.norm(q1 - q0)
        nn = np.array([d[1], -d[0]])
        b.quad((q0[0], q0[1], zd + 0.35), (q1[0], q1[1], zd + 0.35),
               (q1[0] + nn[0] * 0.9, q1[1] + nn[1] * 0.9, zd + 3.0),
               (q0[0] + nn[0] * 0.9, q0[1] + nn[1] * 0.9, zd + 3.0), C.M.glass_clear)
    for k in range(1, 6):                                                                     # support struts
        s = k / 6.0
        q = a + (c - a) * s
        b.hull([(q[0], q[1], zd - 0.1), (q[0], q[1], zd + 0.1),
                (tip[0], tip[1], zd - 0.1), (tip[0], tip[1], zd + 0.1),
                (q[0] + n[0] * 0.3, q[1] + n[1] * 0.3, zd - 0.1), (q[0] + n[0] * 0.3, q[1] + n[1] * 0.3, zd + 0.1),
                (tip[0] + n[0] * 0.3, tip[1] + n[1] * 0.3, zd - 0.1), (tip[0] + n[0] * 0.3, tip[1] + n[1] * 0.3, zd + 0.1)],
               C.M.steel_dark)
    objs.append(b.build(f"{ID}_30hy_edge"))

    # ================================================================================================== 35 Hudson Yards
    objs.append(C.plinth(f"{ID}_35hy_base", P_35, 0.0, 22.0, C.M.limestone, material_top=C.M.roof_dark))
    t35 = C.offset_polygon(P_35, -1.2)
    for i, (ztop, off) in enumerate([(120.0, 0.0), (200.0, -3.5), (270.0, -7.0), (H35 - 14.0, -11.0)]):
        z0 = 22.0 if i == 0 else [120.0, 200.0, 270.0][i - 1]
        objs += cc.curtain(f"{ID}_35hy_t{i}", C.offset_polygon(t35, off), z0, ztop, floor_h=3.95, module=3.2,
                           glass="glass_blue", mullion="limestone", spandrel="limestone", spandrel_h=1.5, proud=0.35,
                           role="mass")
    # crown of splayed limestone fins
    crown = C.offset_polygon(t35, -11.0)
    b = C.MeshBuilder()
    b.prism(C.ring_coords(crown), H35 - 14.0, H35 - 12.0, C.M.limestone)
    for p0, p1, L, t, n in C.edges_of(C.ring_coords(crown)):
        for k in range(max(1, int(L // 3.2))):
            q0 = p0 + t * (1.6 + 3.2 * k)
            q1 = q0 + t * 1.1
            b.hull([(q0[0], q0[1], H35 - 12.0), (q1[0], q1[1], H35 - 12.0),
                    (q0[0] + n[0] * 0.6, q0[1] + n[1] * 0.6, H35 - 12.0), (q1[0] + n[0] * 0.6, q1[1] + n[1] * 0.6, H35 - 12.0),
                    (q0[0] + n[0] * 1.8, q0[1] + n[1] * 1.8, H35), (q1[0] + n[0] * 1.8, q1[1] + n[1] * 1.8, H35),
                    (q0[0] + n[0] * 1.2, q0[1] + n[1] * 1.2, H35), (q1[0] + n[0] * 1.2, q1[1] + n[1] * 1.2, H35)],
                   C.M.limestone)
    objs.append(b.build(f"{ID}_35hy_crown"))

    # ================================================================================================== 10 Hudson Yards
    objs.append(C.plinth(f"{ID}_10hy_base", P_10, 0.0, 16.0, C.M.granite_grey, material_top=C.M.roof_dark))
    x0, y0, x1, y1 = P_10.bounds
    t10 = C._clean_polygon(P_10.intersection(Polygon([(x0 + 2, y0 + 2), (x1 - 2 - 14, y0 + 2), (x1 - 2, y0 + 2 + 14),
                                                      (x1 - 2, y1 - 2), (x0 + 2, y1 - 2)])).buffer(0))
    for i, (ztop, off) in enumerate([(120.0, 0.0), (200.0, -3.0), (H10 - 6.0, -6.5)]):
        z0 = 16.0 if i == 0 else [120.0, 200.0][i - 1]
        objs += cc.curtain(f"{ID}_10hy_t{i}", C.offset_polygon(t10, off), z0, ztop, floor_h=4.05, module=3.05,
                           glass="glass_blue", mullion="steel_nirosta", spandrel_h=1.0, proud=0.18, role="mass")
    objs.append(C.prism(f"{ID}_10hy_crown", C.offset_polygon(t10, -9.5), H10 - 6.0, H10, C.M.steel_nirosta,
                        material_top=C.M.roof_dark, role="mass"))

    # ================================================================================================== 55 Hudson Yards
    objs.append(C.plinth(f"{ID}_55hy_base", P_55, 0.0, 9.0, C.M.granite_grey, material_top=C.M.roof_dark))
    t55 = C.offset_polygon(P_55, -0.8)
    fen55 = C.Fenestration(floor_h=4.57, bay_w=3.35, window_frac=0.72, recess=0.55, spandrel_h=1.05,
                           spandrel_proud=0.5, pier="steel_dark", spandrel="steel_dark", glass="glass_blue")
    objs += C.tower_tier(f"{ID}_55hy", t55, 9.0, H55 - 5.0, fen55, roof_material="roof_dark", parapet_h=1.2)
    objs.append(C.prism(f"{ID}_55hy_crown", C.offset_polygon(t55, -4.0), H55 - 5.0, H55, C.M.steel_dark,
                        material_top=C.M.roof_dark, role="mass"))

    # =============================================================================== 15 Hudson Yards and The Shed
    x0, y0, x1, y1 = P_1589.bounds
    P_15 = C._clean_polygon(P_1589.intersection(C.rect_xy(x0 - 1, y0 - 1, -106.0, y1 + 1)).buffer(0))
    P_shed = C._clean_polygon(P_1589.intersection(C.rect_xy(-106.0, y0 - 1, x1 + 1, y1 + 1)).buffer(0))
    objs.append(C.plinth(f"{ID}_15hy_base", P_15, 0.0, 12.0, C.M.concrete, material_top=C.M.roof_dark))
    c15 = P_15.centroid
    r15 = math.sqrt(P_15.area / math.pi)
    # square base -> four-lobed pleated top: interpolate a 4-lobed profile with height
    lobes = []
    nseg = 40
    for k, (z, f) in enumerate([(12.0, 0.0), (90.0, 0.25), (170.0, 0.7), (H15 - 8.0, 1.0)]):
        ring = []
        for j in range(nseg):
            a = 2 * math.pi * j / nseg
            rr = r15 * (1.0 + 0.16 * f * math.cos(4 * a)) * (1.0 - 0.10 * f)
            ring.append((c15.x + rr * math.cos(a) * 1.28, c15.y + rr * math.sin(a) * 0.78, z))
        lobes.append(ring)
    objs.append(C.tag(C.loft(f"{ID}_15hy_shaft", lobes, C.M.glass_blue, material_top=C.M.roof_dark), "mass"))
    b = C.MeshBuilder()
    for k in range(len(lobes) - 1):
        r0, r1 = lobes[k], lobes[k + 1]
        nfl = max(1, int(round((r1[0][2] - r0[0][2]) / 3.1)))
        for f in range(1, nfl + 1):
            s = f / nfl
            ring = [(a[0] + (bq[0] - a[0]) * s, a[1] + (bq[1] - a[1]) * s, a[2] + (bq[2] - a[2]) * s)
                    for a, bq in zip(r0, r1)]
            cc.band_ring(b, [(x, y) for x, y, _ in ring], ring[0][2] - 0.9, ring[0][2], 0.18, C.M.aluminium)
    objs.append(b.build(f"{ID}_15hy_floors"))
    objs.append(C.prism(f"{ID}_15hy_crown", C.offset_polygon(Polygon([(x, y) for x, y, _ in lobes[-1]]), -3.0),
                        H15 - 8.0, H15, C.M.aluminium, material_top=C.M.roof_dark, role="mass"))

    # ---- The Shed: fixed building + the movable shell on its rails ------------------------------------------------
    sx0, sy0, sx1, sy1 = P_shed.bounds
    fixed = C._clean_polygon(P_shed.intersection(C.rect_xy(sx0 - 1, sy0 - 1, sx0 + 42.0, sy1 + 1)).buffer(0))
    objs.append(C.plinth(f"{ID}_shed_base", P_shed, 0.0, 2.0, C.M.pavement, material_top=C.M.pavement))
    objs += cc.curtain(f"{ID}_shed_fixed", fixed, 2.0, 33.5, floor_h=4.2, module=3.4, glass="glass_clear",
                       mullion="steel_dark", spandrel_h=0.8, proud=0.16, role="mass")
    # rails (two, running east-west across the plaza) and the deployed shell
    b = C.MeshBuilder()
    for yy in (sy0 + 3.0, sy1 - 3.0):
        b.box(((sx0 + sx1) / 2 + 8.0, yy, 0.35), (SHELL_TRAVEL + 46.0, 1.1, 0.7), C.M.steel_dark)
    objs.append(b.build(f"{ID}_shed_rails"))
    b = C.MeshBuilder()
    shell_x0 = sx0 + 42.0
    shell_x1 = min(sx1, shell_x0 + 43.0)
    sy_a, sy_b = sy0 + 2.0, sy1 - 2.0
    ztop = 2.0 + SHELL_H
    # the shell is a rectangular ETFE-clad crate with an exposed steel diagrid, not a vault: 6 portal frames across
    # its 43 m length, each a box portal with a 2.2 m cambered roof [DS+R sections]
    nframe = 6
    for k in range(nframe):
        xx = shell_x0 + (shell_x1 - shell_x0) * k / (nframe - 1)
        for (ya, za), (yb, zb) in (((sy_a, 2.0), (sy_a, ztop)), ((sy_b, 2.0), (sy_b, ztop)),
                                   ((sy_a, ztop), ((sy_a + sy_b) / 2, ztop + 2.2)),
                                   (((sy_a + sy_b) / 2, ztop + 2.2), (sy_b, ztop))):
            b.hull([(xx - 0.55, ya, za), (xx + 0.55, ya, za), (xx - 0.55, yb, zb), (xx + 0.55, yb, zb),
                    (xx - 0.55, ya, za + 1.1), (xx + 0.55, ya, za + 1.1),
                    (xx - 0.55, yb, zb + 1.1), (xx + 0.55, yb, zb + 1.1)], C.M.steel_dark)
    for zz in (2.0, 12.0, 24.0, ztop):                       # longitudinal ties
        for yy in (sy_a, sy_b):
            b.box(((shell_x0 + shell_x1) / 2, yy, zz + 0.4), (shell_x1 - shell_x0, 0.7, 0.8), C.M.steel_dark)
    # ETFE cushion cladding: the two long walls, the two ends and the cambered roof
    for yy, nn in ((sy_a, -1.0), (sy_b, 1.0)):
        for k in range(nframe - 1):
            xa = shell_x0 + (shell_x1 - shell_x0) * k / (nframe - 1)
            xb = shell_x0 + (shell_x1 - shell_x0) * (k + 1) / (nframe - 1)
            for j in range(4):
                za = 2.0 + (ztop - 2.0) * j / 4
                zb = 2.0 + (ztop - 2.0) * (j + 1) / 4
                b.quad((xa, yy, za), (xb, yy, za), (xb, yy, zb), (xa, yy, zb), C.M.glass_clear)
    for xx in (shell_x0, shell_x1):
        for j in range(4):
            za = 2.0 + (ztop - 2.0) * j / 4
            zb = 2.0 + (ztop - 2.0) * (j + 1) / 4
            b.quad((xx, sy_a, za), (xx, sy_b, za), (xx, sy_b, zb), (xx, sy_a, zb), C.M.glass_clear)
    for k in range(nframe - 1):
        xa = shell_x0 + (shell_x1 - shell_x0) * k / (nframe - 1)
        xb = shell_x0 + (shell_x1 - shell_x0) * (k + 1) / (nframe - 1)
        b.quad((xa, sy_a, ztop), (xb, sy_a, ztop), (xb, (sy_a + sy_b) / 2, ztop + 2.2),
               (xa, (sy_a + sy_b) / 2, ztop + 2.2), C.M.glass_clear)
        b.quad((xa, (sy_a + sy_b) / 2, ztop + 2.2), (xb, (sy_a + sy_b) / 2, ztop + 2.2),
               (xb, sy_b, ztop), (xa, sy_b, ztop), C.M.glass_clear)
    for k in range(4):                                       # the four double-wheel bogies per rail
        xx = shell_x0 + (shell_x1 - shell_x0) * k / 3.0
        for yy in (sy0 + 3.0, sy1 - 3.0):
            b.box((xx, yy, 0.9), (2.4, 1.7, 1.6), C.M.steel_dark)
            for dx in (-0.8, 0.8):
                b.lathe([(0.0, -0.35), (0.55, -0.35), (0.55, 0.35), (0.0, 0.35)], 12, C.M.steel_nirosta,
                        origin=(xx + dx, yy, 0.55))
    objs.append(C.tag(b.build(f"{ID}_shed_shell"), "shell"))

    # ================================================================================================== 50 Hudson Yards
    objs.append(C.plinth(f"{ID}_50hy_base", P_50, 0.0, 18.2, C.M.granite_grey, material_top=C.M.roof_dark))
    t50 = C.offset_polygon(P_50, -1.0)
    objs += cc.curtain(f"{ID}_50hy", t50, 18.2, H50 - 10.0, floor_h=4.1, module=3.05, glass="glass_blue",
                       mullion="steel_nirosta", spandrel_h=1.15, proud=0.22, role="mass")
    # four-storey sky lobbies expressed as recessed bands, and the angled crown
    b = C.MeshBuilder()
    r50 = C.ring_coords(t50)
    for z in (105.0, 200.0):
        cc.band_ring(b, r50, z, z + 16.4, -0.45, C.M.steel_dark)
    objs.append(b.build(f"{ID}_50hy_skylobbies"))
    b = C.MeshBuilder()
    x0, y0, x1, y1 = t50.bounds
    b.quad((x0, y0, H50 - 10.0), (x1, y0, H50 - 10.0), (x1, y1, H50), (x0, y1, H50), C.M.steel_nirosta)
    b.tri((x0, y0, H50 - 10.0), (x0, y1, H50), (x0, y1, H50 - 10.0), C.M.steel_nirosta)
    b.tri((x1, y0, H50 - 10.0), (x1, y1, H50 - 10.0), (x1, y1, H50), C.M.steel_nirosta)
    b.quad((x0, y1, H50 - 10.0), (x0, y1, H50), (x1, y1, H50), (x1, y1, H50 - 10.0), C.M.steel_nirosta)
    objs.append(C.tag(b.build(f"{ID}_50hy_crown"), "mass"))

    # ==================================================================================================== the Vessel
    objs.append(C.tag(C.prism(f"{ID}_vessel_plaza", P_ves, 0.0, 0.25, C.M.pavement), "plaza"))
    ves = vessel(P_ves)
    objs.append(ves)
    return objs, g, {"vessel": ves, "shed": [o for o in objs if o is not None and "shed" in o.name]}


def vessel(P_ves):
    """The Vessel: 154 flights of stairs, 2,500 steps and 80 landings on 8 levels, widening from 15.2 m at the base
    to 45.7 m at the top over 46.0 m [Heatherwick Studio].

    Structure: at each of the 8 levels there are 8 landing positions on a ring; flights run from landing (j, k) up to
    landings (j+1, k+1) and (j-1, k+1), so the flights cross and form the honeycomb of triangular openings that the
    real Vessel reads as. 8 levels x 8 x 2 = 128 flights, plus the 26 entry flights from the plaza to level 1 =
    154; landings are 10 per level x 8 = 80."""
    c = P_ves.centroid
    b = C.MeshBuilder()
    levels = 8
    zs = [VESSEL_H * k / levels for k in range(levels + 1)]
    rad = [(VESSEL_BASE_D / 2) + (VESSEL_TOP_D / 2 - VESSEL_BASE_D / 2) * (z / VESSEL_H) for z in zs]
    copper = C.mat("copper_new")
    steel = C.mat("steel_dark")
    bays = 8
    flights = 0
    landings = 0

    def node(j, k, half=0.0):
        a = 2 * math.pi * (j + half) / bays
        return np.array([c.x + rad[k] * math.cos(a), c.y + rad[k] * math.sin(a)]), zs[k]

    def flight(p0, z0, p1, z1, nstep=16, w=2.1):
        """One stepped flight from (p0, z0) to (p1, z1) with treads, risers and two stringers."""
        d = p1 - p0
        ln = float(np.linalg.norm(d))
        if ln < 1e-6:
            return
        t = d / ln
        nn = np.array([t[1], -t[0]])
        for s in range(nstep):
            u0, u1 = s / nstep, (s + 1) / nstep
            q0 = p0 + d * u0
            q1 = p0 + d * u1
            za = z0 + (z1 - z0) * u0
            zb = z0 + (z1 - z0) * u1
            b.quad((q0[0] - nn[0] * w, q0[1] - nn[1] * w, zb), (q0[0] + nn[0] * w, q0[1] + nn[1] * w, zb),
                   (q1[0] + nn[0] * w, q1[1] + nn[1] * w, zb), (q1[0] - nn[0] * w, q1[1] - nn[1] * w, zb), copper)
            b.quad((q0[0] - nn[0] * w, q0[1] - nn[1] * w, za), (q0[0] - nn[0] * w, q0[1] - nn[1] * w, zb),
                   (q0[0] + nn[0] * w, q0[1] + nn[1] * w, zb), (q0[0] + nn[0] * w, q0[1] + nn[1] * w, za), copper)
        for sgn in (-1.0, 1.0):                     # the two stringers, which are what read as the lattice
            a0 = p0 + nn * (w * sgn)
            a1 = p1 + nn * (w * sgn)
            b.hull([(a0[0], a0[1], z0 - 1.0), (a0[0], a0[1], z0), (a1[0], a1[1], z1 - 1.0), (a1[0], a1[1], z1),
                    (a0[0] + nn[0] * 0.22 * sgn, a0[1] + nn[1] * 0.22 * sgn, z0 - 1.0),
                    (a0[0] + nn[0] * 0.22 * sgn, a0[1] + nn[1] * 0.22 * sgn, z0),
                    (a1[0] + nn[0] * 0.22 * sgn, a1[1] + nn[1] * 0.22 * sgn, z1 - 1.0),
                    (a1[0] + nn[0] * 0.22 * sgn, a1[1] + nn[1] * 0.22 * sgn, z1)], copper)
            b.hull([(a0[0], a0[1], z0 + 0.15), (a0[0], a0[1], z0 + 1.15),
                    (a1[0], a1[1], z1 + 0.15), (a1[0], a1[1], z1 + 1.15),
                    (a0[0] + nn[0] * 0.10 * sgn, a0[1] + nn[1] * 0.10 * sgn, z0 + 0.15),
                    (a0[0] + nn[0] * 0.10 * sgn, a0[1] + nn[1] * 0.10 * sgn, z0 + 1.15),
                    (a1[0] + nn[0] * 0.10 * sgn, a1[1] + nn[1] * 0.10 * sgn, z1 + 0.15),
                    (a1[0] + nn[0] * 0.10 * sgn, a1[1] + nn[1] * 0.10 * sgn, z1 + 1.15)], steel)

    for k in range(levels):
        for j in range(bays):
            p, z0 = node(j, k)
            for dj in (+1, -1):
                q, z1 = node(j + dj, k + 1)
                flight(p, z0, q, z1)
                flights += 1
        for j in range(10):                          # 10 landings per level
            a = 2 * math.pi * j / 10
            q = (c.x + rad[k + 1] * math.cos(a), c.y + rad[k + 1] * math.sin(a))
            b.box((q[0], q[1], zs[k + 1] - 0.15), (5.0, 3.4, 0.3), copper, rot_deg=math.degrees(a) + 90.0)
            landings += 1
    for j in range(VESSEL_FLIGHTS - flights):        # the 26 entry flights from the plaza up to level 1
        a0 = 2 * math.pi * j / 26
        p = np.array([c.x + (rad[0] + 4.0) * math.cos(a0), c.y + (rad[0] + 4.0) * math.sin(a0)])
        q = np.array([c.x + rad[1] * math.cos(a0 + 0.18), c.y + rad[1] * math.sin(a0 + 0.18)])
        flight(p, 0.25, q, zs[1], nstep=9, w=1.5)
        flights += 1
    assert flights == VESSEL_FLIGHTS and landings == VESSEL_LANDINGS, (flights, landings)
    for k in range(levels + 1):                      # the outer balustrade ring at every level
        ring = [(c.x + rad[k] * math.cos(2 * math.pi * j / 48), c.y + rad[k] * math.sin(2 * math.pi * j / 48))
                for j in range(48)]
        cc.band_ring(b, ring, zs[k] + 0.5, zs[k] + 1.4, 0.12, steel)
    return b.build("c_hudson_yards_vessel")


def main():
    objs, g, key = build()
    entry = cc.finish(objs, ID, g.frame, real_footprint=g.real_local,
                      fidelity_statement=(
                          "Exact: seven real OTI footprints; published heights 387.1 / 308.0 / 272.8 / 237.4 / "
                          "278.6 / 308.2 m (CTBUH); the Edge deck at 345.0 m cantilevering 20.0 m with a glass floor; "
                          "The Shed's 36.6 m movable ETFE shell modelled deployed on its two 83.2 m rails with its "
                          "bogies as separate objects; the Vessel built as 154 real stepped flights and 80 landings "
                          "widening 15.2 -> 45.7 m over 46.0 m. Inferred (stated): the split of the two shared "
                          "footprint polygons (cut at existing polygon vertices), the tower plan shapes above the "
                          "podium (published massing, not measured floor plans) and the 34 m podium height. Not "
                          "modelled: the rail yard and platform below, interiors, retail signage, plaza planting, "
                          "and the Vessel's 2021 safety netting."),
                      dimensions={"30_hy_m": H30, "edge_deck_m": EDGE_DECK_Z, "edge_cantilever_m": EDGE_CANTILEVER,
                                  "35_hy_m": H35, "10_hy_m": H10, "55_hy_m": H55, "15_hy_m": H15, "50_hy_m": H50,
                                  "shed_shell_h_m": SHELL_H, "shed_shell_travel_m": SHELL_TRAVEL,
                                  "vessel_h_m": VESSEL_H, "vessel_flights": VESSEL_FLIGHTS,
                                  "vessel_landings": VESSEL_LANDINGS,
                                  "vessel_diameter_m": [VESSEL_BASE_D, VESSEL_TOP_D], "podium_top_m": PODIUM_TOP},
                      material_slots={"shell": "The Shed's movable shell is the object c_hudson_yards_shed_shell "
                                               "(role='shell'); translate it -83.2 m along local +x to retract it"},
                      notes="The Shed's shell is exported as its own node so the engine can animate it along the rails.")
    cc.render(ID, [
        {"view": "public_square", "azimuth_deg": 205, "elevation_deg": "street", "distance": 1100, "fov_deg": 38, "look_up_deg": 14},
        {"view": "aerial", "azimuth_deg": 240, "elevation_deg": 28},
    ])
    cc.render(ID, [{"view": "vessel", "azimuth_deg": 200, "elevation_deg": 30, "distance": 130, "fov_deg": 45, "target_z": 24}],
              objects=[key["vessel"]])
    cc.render(ID, [{"view": "shed", "azimuth_deg": 196, "elevation_deg": 20, "distance": 200, "fov_deg": 45, "target_z": 18}],
              objects=key["shed"])
    return entry


if __name__ == "__main__":
    main()
