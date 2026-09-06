"""Window kit pieces — one per entry of ``facade_params.WINDOW_TYPES`` (18 pieces).

Origin: bottom-centre of the *masonry opening* on the wall plane (y = 0, +Y into the building). The piece therefore
spans x = ±opening/2, z = 0..opening_h, and its trim (lintels, sills, bays, dormers) reaches outside that box, which
is why ``nominal_size`` is the full bounding box, not the opening.

Every window carries an interior card 24 cm behind the glass so it never reads as a hole.
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P
import facade_params as fp

W = {w[0]: (w[1], w[2]) for w in fp.WINDOW_TYPES}
BUD = 400


def _op(name: str):
    ow, oh = W[name]
    return -ow / 2, ow / 2, 0.0, oh


# --------------------------------------------------------------------------- 1  plain 1/1
@K.register("win_double_hung_1_1", "window", nominal_size=(0.99, 0.29, 1.755),
            description="One-over-one double-hung sash in a plain brick opening (post-1930 tenement replacement sash).",
            features=["sills"], variants=["lit", "unlit"])
def _win_1_1():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("double_hung_1_1")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "red_brick")
    P.double_hung(m, x0, x1, z0, z1, lit=False)
    m.box((x0 - 0.02, -0.020, z0 - 0.055), (x1 + 0.02, P.WYTHE, z0), "precast")   # flush cast-stone sill
    return m


# --------------------------------------------------------------------------- 2  1/1 with stone lintel + sill
@K.register("win_double_hung_1_1_stone", "window", nominal_size=(1.18, 0.335, 1.95),
            description="One-over-one with a projecting limestone lintel and washed stone sill (brownstone / limestone-trimmed brick).",
            features=["lintels", "sills"], variants=["limestone", "brownstone"])
def _win_1_1_stone():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("double_hung_1_1_stone")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "red_brick")
    P.double_hung(m, x0, x1, z0, z1, lit=False)
    P.stone_lintel(m, x0, x1, z1, "limestone")
    P.stone_sill(m, x0, x1, z0 - P.SILL_H, "limestone")
    return m


# --------------------------------------------------------------------------- 3  1/1 with brick soldier lintel
@K.register("win_double_hung_1_1_soldier", "window", nominal_size=(1.06, 0.32, 1.994),
            description="One-over-one with a brick soldier-course lintel and cast-stone sill (New Law tenement, 1901-1929).",
            features=["lintels", "sills"])
def _win_1_1_soldier():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("double_hung_1_1_soldier")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "red_brick")
    P.double_hung(m, x0, x1, z0, z1, lit=False)
    P.soldier_lintel(m, x0, x1, z1, "red_brick")
    P.stone_sill(m, x0, x1, z0 - P.SILL_H, "precast", ear=0.055, proj=0.050)
    return m


# --------------------------------------------------------------------------- 4  2/2
@K.register("win_double_hung_2_2", "window", nominal_size=(1.18, 0.335, 2.05),
            description="Two-over-two double-hung with a vertical muntin per sash and brownstone lintel/sill (Italianate rowhouse 1860-1890).",
            features=["lintels", "sills"])
def _win_2_2():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("double_hung_2_2")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "brownstone")
    P.double_hung(m, x0, x1, z0, z1, lights_x=2, lit=False)
    P.stone_lintel(m, x0, x1, z1, "brownstone")
    P.stone_sill(m, x0, x1, z0 - P.SILL_H, "brownstone")
    return m


# --------------------------------------------------------------------------- 5  6/6
@K.register("win_double_hung_6_6", "window", nominal_size=(1.01, 0.335, 1.894),
            description="Six-over-six true-divided-light double-hung with a splayed brick flat arch (Federal / Greek Revival rowhouse).",
            features=["lintels", "sills"])
def _win_6_6():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("double_hung_6_6")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "red_brick")
    P.double_hung(m, x0, x1, z0, z1, lights_x=3, lights_z=2, lit=False)
    m.box((x0 - 0.055, -0.012, z1), (x1 + 0.055, P.WYTHE, z1 + P.BRICK_LEN), "red_brick")   # flat gauged arch
    P.stone_sill(m, x0, x1, z0 - P.SILL_H, "brownstone", ear=0.055)
    return m


# --------------------------------------------------------------------------- 6  casement pair
@K.register("win_casement_pair", "window", nominal_size=(1.21, 0.335, 1.7),
            description="Pair of side-hinged steel casements with a three-light grid each and a cast-stone sill (prewar apartment 1920-1940).",
            features=["sills"])
def _win_casement():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("casement_pair")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "tan_brick")
    m.frame(x0, x1, z0, z1, P.REVEAL - 0.012, P.REVEAL + 0.062, 0.050, P.BLACK)
    fx0, fx1, fz0, fz1 = x0 + 0.050, x1 - 0.050, z0 + 0.050, z1 - 0.050
    mid = (fx0 + fx1) / 2
    P.sash(m, fx0, mid - 0.012, fz0, fz1, P.REVEAL, lights_z=3, frame_mat=P.BLACK, stile=0.032, thick=0.035)
    P.sash(m, mid + 0.012, fx1, fz0, fz1, P.REVEAL, lights_z=3, frame_mat=P.BLACK, stile=0.032, thick=0.035)
    m.box((mid - 0.016, P.REVEAL - 0.010, fz0), (mid + 0.016, P.REVEAL + 0.045, fz1), P.BLACK)   # mullion
    P.interior_card(m, fx0, fx1, fz0, fz1, P.REVEAL + 0.155, False)
    P.stone_sill(m, x0, x1, z0 - P.SILL_H, "precast", ear=0.055)
    return m


# --------------------------------------------------------------------------- 7  steel industrial
@K.register("win_steel_industrial_4x5", "window", nominal_size=(1.62, 0.315, 2.44),
            description="Steel-sash industrial window, 4 x 5 lights with a centre-pivot vent, in a loft opening with a steel lintel angle.",
            features=["lintels"])
def _win_steel():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("steel_industrial_4x5")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.08, "red_brick")
    y = P.REVEAL
    m.frame(x0, x1, z0, z1, y, y + 0.040, 0.038, P.BLACK)
    gx0, gx1, gz0, gz1 = x0 + 0.038, x1 - 0.038, z0 + 0.038, z1 - 0.038
    for i in range(1, 4):
        x = gx0 + (gx1 - gx0) * i / 4
        m.box((x - 0.012, y + 0.006, gz0), (x + 0.012, y + 0.034, gz1), P.BLACK)
    for j in range(1, 5):
        z = gz0 + (gz1 - gz0) * j / 5
        w = 0.020 if j == 2 else 0.012                    # heavier bar at the pivot vent head
        m.box((gx0, y + 0.006, z - w / 2), (gx1, y + 0.034, z + w / 2), P.BLACK)
    m.glass_pane(gx0, gx1, gz0, gz1, y + 0.020, P.GLASS)
    P.interior_card(m, gx0, gx1, gz0, gz1, y + 0.155, False)
    m.box((x0 - 0.06, -0.030, z1), (x1 + 0.06, 0.010, z1 + 0.090), P.GALV)          # lintel angle
    m.box((x0 - 0.02, -0.045, z0 - 0.050), (x1 + 0.02, P.WYTHE, z0), "precast")     # sill
    return m


# --------------------------------------------------------------------------- 8  punched office
@K.register("win_punched_office", "window", nominal_size=(1.62, 0.325, 2.29),
            description="Aluminium punched office window, fixed light over a hopper vent, in a precast surround (1960-1990 office / hospital).",
            features=["sills"])
def _win_punched():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("punched_office")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.08, "precast")
    y = P.REVEAL
    m.frame(x0, x1, z0, z1, y, y + 0.060, 0.055, P.ALU)
    gx0, gx1, gz0, gz1 = x0 + 0.055, x1 - 0.055, z0 + 0.055, z1 - 0.055
    split = gz0 + (gz1 - gz0) * 0.30
    m.box((gx0, y + 0.004, split - 0.030), (gx1, y + 0.056, split + 0.030), P.ALU)    # transom bar
    m.box(((gx0 + gx1) / 2 - 0.026, y + 0.004, split + 0.030), ((gx0 + gx1) / 2 + 0.026, y + 0.056, gz1), P.ALU)
    m.glass_pane(gx0, gx1, gz0, split - 0.030, y + 0.030, "glass_curtain")
    m.glass_pane(gx0, gx1, split + 0.030, gz1, y + 0.030, "glass_curtain")
    P.interior_card(m, gx0, gx1, gz0, gz1, y + 0.155, False)
    m.box((x0 - 0.06, -0.055, z0 - 0.090), (x1 + 0.06, P.WYTHE, z0), "precast")
    return m


# --------------------------------------------------------------------------- 9  curtain-wall module
@K.register("win_curtain_wall_module", "window", nominal_size=(1.5, 0.29, 3.9), anchor="wall_bottom_centre",
            description="Unitised curtain-wall module 1.5 m wide x 3.9 m floor-to-floor: vision glass, shadow-box spandrel, "
                        "snap-on mullion covers and a slab-edge anchor.",
            features=["curtain_wall"], budget=500)
def _win_curtain():
    m = K.Mesh()
    w, h = W["curtain_wall_module"]
    x0, x1 = -w / 2, w / 2
    vision_bot, vision_top = 0.90, 3.20        # 900 mm spandrel, 2.30 m vision glass, 700 mm head spandrel
    y = 0.0
    m.box((x0, y, 0.0), (x0 + 0.075, y + 0.180, h), P.ALU)                 # left mullion
    m.box((x1 - 0.075, y, 0.0), (x1, y + 0.180, h), P.ALU)                 # right mullion
    for z in (0.0, vision_bot, vision_top, h - 0.050):
        m.box((x0 + 0.075, y, z), (x1 - 0.075, y + 0.150, z + 0.050), P.ALU)   # transoms
    m.box((x0 + 0.030, y - 0.030, 0.0), (x0 + 0.045, y, h), P.ALU)             # snap-on cover caps
    m.box((x1 - 0.045, y - 0.030, 0.0), (x1 - 0.030, y, h), P.ALU)
    m.glass_pane(x0 + 0.075, x1 - 0.075, vision_bot + 0.050, vision_top, y + 0.075, "glass_curtain", 0.024)
    m.glass_pane(x0 + 0.075, x1 - 0.075, 0.050, vision_bot, y + 0.075, "glass_curtain", 0.024)          # spandrel
    m.glass_pane(x0 + 0.075, x1 - 0.075, vision_top + 0.050, h - 0.050, y + 0.075, "glass_curtain", 0.024)
    m.box((x0 + 0.075, y + 0.100, 0.050), (x1 - 0.075, y + 0.130, vision_bot), "metal_panel")           # shadow box back pan
    m.box((x0, y + 0.180, 0.050), (x1, y + 0.260, 0.420), "concrete")                                   # slab edge
    P.interior_card(m, x0 + 0.08, x1 - 0.08, vision_bot, vision_top, y + 0.20, False)
    return m


# --------------------------------------------------------------------------- 10  bay window
@K.register("win_bay_window", "window", nominal_size=(2.488, 0.68, 2.62),
            description="Three-sided projecting bay, 2.40 m wide x 0.62 m deep, with three 1/1 sashes, a panelled brownstone apron, "
                        "moulded sill and head bands and a lead-clad roof (Brooklyn / Queens rowhouse).",
            features=["bay_windows"], budget=900)
def _win_bay():
    m = K.Mesh()
    w, h = W["bay_window"]
    x0, x1 = -w / 2, w / 2
    proj = 0.62                       # 2 ft projection past the wall face (rowhouse bay)
    cx0, cx1 = x0 + 0.46, x1 - 0.46   # 45 deg canted returns
    apron, head = 0.30, 0.30 + h      # sill at 0.30, head at 2.40
    top = head + 0.22
    plan = [(x0, 0.0), (cx0, -proj), (cx1, -proj), (x1, 0.0)]

    def facet(i):
        (ax, ay), (bx, by) = plan[i], plan[i + 1]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        return (ax, ay), (bx, by), (ux, uy), (uy, -ux), L      # outward normal is (uy, -ux)

    for i in range(3):
        (ax, ay), (bx, by), (ux, uy), (nx, ny), L = facet(i)
        e = 0.055                                              # projection of the sill / head bands
        # apron below the sill
        m.face([(ax, ay, 0.0), (bx, by, 0.0), (bx, by, apron), (ax, ay, apron)], "brownstone")
        # recessed apron panel
        m.face([(ax + ux * 0.14 + nx * 0.008, ay + uy * 0.14 + ny * 0.008, 0.09),
                (bx - ux * 0.14 + nx * 0.008, by - uy * 0.14 + ny * 0.008, 0.09),
                (bx - ux * 0.14 + nx * 0.008, by - uy * 0.14 + ny * 0.008, apron - 0.07),
                (ax + ux * 0.14 + nx * 0.008, ay + uy * 0.14 + ny * 0.008, apron - 0.07)], "brownstone")
        # moulded sill band and head band (project e outwards, 0.10 / 0.14 deep)
        for (zb, zt) in ((apron - 0.06, apron + 0.04), (head - 0.05, head + 0.13)):
            A = (ax, ay, zb); B = (bx, by, zb)
            An = (ax + nx * e, ay + ny * e, zb); Bn = (bx + nx * e, by + ny * e, zb)
            At = (ax + nx * e, ay + ny * e, zt); Bt = (bx + nx * e, by + ny * e, zt)
            m.face([An, Bn, Bt, At], "brownstone")                                  # band face
            m.face([A, B, Bn, An], "brownstone", flip=True)                         # underside
            m.face([At, Bt, (bx, by, zt), (ax, ay, zt)], "brownstone")              # top wash
        # pier faces beside the glazing
        m.face([(ax, ay, apron), (ax + ux * 0.13, ay + uy * 0.13, apron),
                (ax + ux * 0.13, ay + uy * 0.13, head), (ax, ay, head)], "brownstone")
        m.face([(bx - ux * 0.13, by - uy * 0.13, apron), (bx, by, apron),
                (bx, by, head), (bx - ux * 0.13, by - uy * 0.13, head)], "brownstone")
        # reveal + sash + glass, set 0.10 m back from the facet
        px0, py0 = ax + ux * 0.13, ay + uy * 0.13
        px1, py1 = bx - ux * 0.13, by - uy * 0.13
        rx0, ry0 = px0 - nx * 0.10, py0 - ny * 0.10
        rx1, ry1 = px1 - nx * 0.10, py1 - ny * 0.10
        m.face([(px0, py0, apron), (rx0, ry0, apron), (rx0, ry0, head), (px0, py0, head)], "brownstone", flip=True)
        m.face([(px1, py1, apron), (px1, py1, head), (rx1, ry1, head), (rx1, ry1, apron)], "brownstone", flip=True)
        m.face([(px0, py0, head), (rx0, ry0, head), (rx1, ry1, head), (px1, py1, head)], "brownstone", flip=True)
        m.face([(px0, py0, apron), (px1, py1, apron), (rx1, ry1, apron), (rx0, ry0, apron)], "brownstone", flip=True)
        m.face([(rx0, ry0, apron + 0.02), (rx1, ry1, apron + 0.02), (rx1, ry1, head - 0.02), (rx0, ry0, head - 0.02)], P.GLASS)
        m.face([(rx0 + nx * 0.16, ry0 + ny * 0.16, apron), (rx0 + nx * 0.16, ry0 + ny * 0.16, head),
                (rx1 + nx * 0.16, ry1 + ny * 0.16, head), (rx1 + nx * 0.16, ry1 + ny * 0.16, apron)],
               "interior_unlit", uvs=[(0, 0), (0, 2), (2, 2), (2, 0)])
        for t, ww in ((0.0, 0.055), (1.0, 0.055)):             # sash stiles
            sx = rx0 + (rx1 - rx0) * t
            sy = ry0 + (ry1 - ry0) * t
            m.face([(sx - ux * ww + nx * 0.012, sy - uy * ww + ny * 0.012, apron),
                    (sx + ux * ww + nx * 0.012, sy + uy * ww + ny * 0.012, apron),
                    (sx + ux * ww + nx * 0.012, sy + uy * ww + ny * 0.012, head),
                    (sx - ux * ww + nx * 0.012, sy - uy * ww + ny * 0.012, head)], P.SASH_WHITE)
        zm = (apron + head) / 2                                # meeting rail
        m.face([(rx0 + nx * 0.012, ry0 + ny * 0.012, zm - 0.032), (rx1 + nx * 0.012, ry1 + ny * 0.012, zm - 0.032),
                (rx1 + nx * 0.012, ry1 + ny * 0.012, zm + 0.032), (rx0 + nx * 0.012, ry0 + ny * 0.012, zm + 0.032)], P.SASH_WHITE)
    # roof: a shallow lead-clad hip from the head band up to the wall
    rp = [(x + (0.0 if abs(abs(x) - w / 2) < 1e-6 else 0.0), y) for x, y in plan]
    for i in range(3):
        (ax, ay), (bx, by) = rp[i], rp[i + 1]
        m.face([(ax, ay, head + 0.13), (bx, by, head + 0.13), (bx * 0.86, by * 0.5, top), (ax * 0.86, ay * 0.5, top)], "metal_panel")
    m.face([(x * 0.86, y * 0.5, top) for x, y in rp], "metal_panel")
    m.face([(x, y, 0.0) for x, y in reversed(plan)], "brownstone")               # soffit under the bay
    return m


# --------------------------------------------------------------------------- 11  arched tenement
@K.register("win_arched_tenement", "window", nominal_size=(1.133, 0.335, 2.361),
            description="Segmental-arched brick-headed opening with a 1/1 sash and a bluestone sill (Old Law tenement, pre-1901).",
            features=["arched_windows", "sills"])
def _win_arched():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("arched_tenement")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "red_brick")
    P.double_hung(m, x0, x1, z0, z1, lit=False)
    P.segmental_arch(m, x0, x1, z1, (x1 - x0) / 8.0, "red_brick")
    P.stone_sill(m, x0, x1, z0 - P.SILL_H, "granite", ear=0.055)
    return m


# --------------------------------------------------------------------------- 12  dormer
@K.register("win_dormer", "window", nominal_size=(1.64, 1.09, 2.03), anchor="wall_bottom_centre",
            description="Gable dormer with a 6/6 sash, clapboard cheeks and a slate-pitched roof; sits on a 30 deg mansard/roof plane.",
            features=["dormers"], budget=700)
def _win_dormer():
    m = K.Mesh()
    ow, oh = W["dormer"]
    x0, x1 = -0.73, 0.73
    depth = 1.00
    wall_h = 1.55
    ridge = 1.98
    m.box((x0, 0.0, 0.0), (x1, depth, wall_h), P.SASH_WHITE, faces="yxX")           # cheeks + face
    m.face([(x0, 0.0, wall_h), (x1, 0.0, wall_h), (0.0, 0.0, ridge)], P.SASH_WHITE)  # gable tympanum
    m.face([(x0, depth, wall_h), (0.0, depth, ridge), (x1, depth, wall_h)], P.SASH_WHITE)
    for s in (-1, 1):                                                                # roof planes with 90 mm overhang
        m.face([(0.0, -0.09, ridge + 0.05), (s * (x1 + 0.09), -0.09, wall_h + 0.02),
                (s * (x1 + 0.09), depth, wall_h + 0.02), (0.0, depth, ridge + 0.05)], "metal_panel", flip=(s < 0))
    P.reveal(m, -ow / 2, ow / 2, 0.28, 0.28 + oh, 0.10, P.SASH_WHITE)
    P.double_hung(m, -ow / 2, ow / 2, 0.28, 0.28 + oh, lights_x=3, lights_z=2, reveal_depth=0.10, lit=False)
    m.box((-ow / 2 - 0.07, -0.045, 0.22), (ow / 2 + 0.07, 0.09, 0.28), P.SASH_WHITE)  # sill
    return m


# --------------------------------------------------------------------------- 13  aluminium slider
@K.register("win_aluminum_slider", "window", nominal_size=(1.31, 0.32, 1.475),
            description="Post-war aluminium horizontal slider with a fixed and a sliding light, in a white-glazed-brick opening (NYCHA / 1960s infill).",
            features=["sills"])
def _win_slider():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("aluminum_slider")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.08, "white_glazed_brick")
    y = P.REVEAL
    m.frame(x0, x1, z0, z1, y, y + 0.055, 0.048, P.ALU)
    gx0, gx1, gz0, gz1 = x0 + 0.048, x1 - 0.048, z0 + 0.048, z1 - 0.048
    mid = (gx0 + gx1) / 2
    m.frame(gx0, mid + 0.020, gz0, gz1, y + 0.004, y + 0.026, 0.032, P.ALU)      # fixed light
    m.frame(mid - 0.020, gx1, gz0, gz1, y + 0.028, y + 0.050, 0.032, P.ALU)      # sliding light (outboard track)
    m.glass_pane(gx0 + 0.032, mid - 0.012, gz0 + 0.032, gz1 - 0.032, y + 0.015, P.GLASS)
    m.glass_pane(mid + 0.012, gx1 - 0.032, gz0 + 0.032, gz1 - 0.032, y + 0.039, P.GLASS)
    P.interior_card(m, gx0, gx1, gz0, gz1, y + 0.155, False)
    m.box((x0 - 0.055, -0.050, z0 - 0.075), (x1 + 0.055, P.WYTHE, z0), "precast")
    return m


# --------------------------------------------------------------------------- 14  picture window
@K.register("win_picture_window", "window", nominal_size=(1.92, 0.325, 1.46),
            description="1950s picture window: a wide fixed centre light with narrow double-hung flankers and an aluminium sill "
                        "(Queens / Staten Island detached house).",
            features=["sills"])
def _win_picture():
    m = K.Mesh()
    x0, x1, z0, z1 = _op("picture_window")
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.08, "vinyl_siding")
    y = P.REVEAL
    m.frame(x0, x1, z0, z1, y, y + 0.055, 0.050, P.SASH_WHITE)
    fx0, fx1, fz0, fz1 = x0 + 0.050, x1 - 0.050, z0 + 0.050, z1 - 0.050
    a, b = fx0 + 0.40, fx1 - 0.40
    for xm in (a, b):
        m.box((xm - 0.028, y + 0.002, fz0), (xm + 0.028, y + 0.053, fz1), P.SASH_WHITE)
    m.glass_pane(a + 0.028, b - 0.028, fz0, fz1, y + 0.028, P.GLASS)
    P.sash(m, fx0, a - 0.028, fz0, fz1, y + 0.006, frame_mat=P.SASH_WHITE, stile=0.036, thick=0.040)
    P.sash(m, b + 0.028, fx1, fz0, fz1, y + 0.006, frame_mat=P.SASH_WHITE, stile=0.036, thick=0.040)
    P.interior_card(m, fx0, fx1, fz0, fz1, y + 0.155, False)
    m.box((x0 - 0.06, -0.055, z0 - 0.060), (x1 + 0.06, P.WYTHE, z0), P.ALU)
    return m


# --------------------------------------------------------------------------- 15  gothic arched (church)
@K.register("win_gothic_arched", "window", nominal_size=(1.35, 0.27, 3.665),
            description="Pointed-arch traceried church window: equilateral two-centred limestone arch with a hood mould, Y-tracery "
                        "mullions, saddle bars and leaded glass.",
            features=["arched_windows"], budget=1000)
def _win_gothic():
    m = K.Mesh()
    ow, oh = W["gothic_arched"]
    x0, x1 = -ow / 2, ow / 2
    y = P.REVEAL
    spring = oh - ow * 0.92          # springing line of a two-centred (equilateral) arch, R = the span
    R = ow
    seg = 10

    def arch_z(x: float) -> float:
        """Equilateral pointed arch: the left half is struck from the right springing point and vice versa."""
        cxx = x1 if x <= 0.0 else x0
        return spring + math.sqrt(max(R * R - (x - cxx) ** 2, 0.0))

    P.reveal(m, x0, x1, 0.0, spring, y + 0.10, "limestone", head=False)
    m.glass_pane(x0 + 0.02, x1 - 0.02, 0.10, spring, y, "glass_curtain")
    prev = None
    for i in range(seg + 1):
        x = x0 + (x1 - x0) * i / seg
        z = arch_z(x)
        if prev is not None:
            px, pz = prev
            m.face([(px, 0.0, pz), (x, 0.0, z), (x, y + 0.10, z), (px, y + 0.10, pz)], "limestone", flip=True)         # soffit
            m.face([(px, -0.045, pz), (px, -0.045, pz + 0.13), (x, -0.045, z + 0.13), (x, -0.045, z)], "limestone")    # hood face
            m.face([(px, -0.045, pz + 0.13), (px, P.WYTHE, pz + 0.13), (x, P.WYTHE, z + 0.13), (x, -0.045, z + 0.13)], "limestone")
            m.face([(px, y, spring), (x, y, spring), (x, y, z), (px, y, pz)], "glass_curtain")                          # arch-head glazing
        prev = (x, z)
    for t in (1 / 3, 2 / 3):                                                       # Y-tracery mullions into the head
        xm = x0 + (x1 - x0) * t
        m.box((xm - 0.045, y - 0.030, 0.10), (xm + 0.045, y + 0.070, spring + (arch_z(xm) - spring) * 0.55), "limestone")
    for zz in (0.95, 1.85, 2.75):                                                  # wrought-iron saddle bars
        m.box((x0, y - 0.014, zz - 0.014), (x1, y + 0.040, zz + 0.014), P.BLACK)
    m.box((x0 - 0.075, -0.055, 0.0), (x1 + 0.075, P.WYTHE, 0.10), "limestone")     # stone sill block
    return m


# --------------------------------------------------------------------------- 16  ribbon strip
@K.register("win_ribbon_strip", "window", nominal_size=(3.1, 0.33, 1.6),
            description="Continuous horizontal ribbon window band, 3 m long, aluminium frame with four fixed lights and hopper vents "
                        "(1960s school / garage / modern infill).",
            features=[])
def _win_ribbon():
    m = K.Mesh()
    ow, oh = W["ribbon_strip"]
    x0, x1, z0, z1 = -ow / 2, ow / 2, 0.0, oh
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.07, "concrete")
    y = P.REVEAL
    m.frame(x0, x1, z0, z1, y, y + 0.055, 0.050, P.ALU)
    gx0, gx1, gz0, gz1 = x0 + 0.050, x1 - 0.050, z0 + 0.050, z1 - 0.050
    for i in range(1, 4):
        xm = gx0 + (gx1 - gx0) * i / 4
        m.box((xm - 0.030, y + 0.002, gz0), (xm + 0.030, y + 0.053, gz1), P.ALU)
    zt = gz0 + (gz1 - gz0) * 0.72
    m.box((gx0, y + 0.002, zt - 0.028), (gx1, y + 0.053, zt + 0.028), P.ALU)
    m.glass_pane(gx0, gx1, gz0, zt, y + 0.028, "glass_curtain")
    m.glass_pane(gx0, gx1, zt, gz1, y + 0.028, "glass_curtain")
    P.interior_card(m, gx0, gx1, gz0, gz1, y + 0.155, False)
    m.box((x0 - 0.05, -0.060, z0 - 0.100), (x1 + 0.05, P.WYTHE, z0), "precast")
    return m


# --------------------------------------------------------------------------- 17  Chicago tripartite
@K.register("win_chicago_tripartite", "window", nominal_size=(2.6, 0.335, 2.49),
            description="Chicago window: a wide fixed centre light between narrow 1/1 double-hung flankers, cast-stone lintel and sill "
                        "(1895-1915 loft / early office).",
            features=["lintels", "sills"], budget=550)
def _win_chicago():
    m = K.Mesh()
    ow, oh = W["chicago_tripartite"]
    x0, x1, z0, z1 = -ow / 2, ow / 2, 0.0, oh
    P.reveal(m, x0, x1, z0, z1, P.REVEAL + 0.10, "red_brick")
    y = P.REVEAL
    m.frame(x0, x1, z0, z1, y - 0.012, y + 0.070, 0.055, P.SASH_WHITE)
    fx0, fx1, fz0, fz1 = x0 + 0.055, x1 - 0.055, z0 + 0.055, z1 - 0.055
    a, b = fx0 + 0.60, fx1 - 0.60
    for xm in (a, b):
        m.box((xm - 0.040, y - 0.010, fz0), (xm + 0.040, y + 0.068, fz1), P.SASH_WHITE)
    m.glass_pane(a + 0.040, b - 0.040, fz0, fz1, y + 0.030, P.GLASS)
    for (sx0, sx1) in ((fx0, a - 0.040), (b + 0.040, fx1)):
        mid = (fz0 + fz1) / 2
        P.sash(m, sx0, sx1, mid, fz1, y + 0.030, frame_mat=P.SASH_WHITE, stile=0.038, thick=0.038)
        P.sash(m, sx0, sx1, fz0, mid, y - 0.008, frame_mat=P.SASH_WHITE, stile=0.038, thick=0.038)
    P.interior_card(m, fx0, fx1, fz0, fz1, y + 0.155, False)
    P.stone_lintel(m, x0, x1, z1, "precast", h=0.180, ear=0.100)
    P.stone_sill(m, x0, x1, z0 - 0.110, "precast", h=0.110, ear=0.075)
    return m


# --------------------------------------------------------------------------- 18  through-wall AC sleeve
@K.register("win_through_wall_ac_sleeve", "window", nominal_size=(0.81, 0.335, 0.59),
            description="Through-wall air-conditioner sleeve opening ('Fedders special'): steel sleeve, aluminium grille and cast-stone lintel.",
            features=["through_wall_ac"], budget=250)
def _win_ac_sleeve():
    m = K.Mesh()
    ow, oh = W["through_wall_ac_sleeve"]
    x0, x1, z0, z1 = -ow / 2, ow / 2, 0.0, oh
    P.reveal(m, x0, x1, z0, z1, 0.29, "tan_brick")
    m.box((x0 + 0.010, 0.010, z0 + 0.010), (x1 - 0.010, 0.270, z1 - 0.010), P.GALV, faces="xXzZY")
    m.box((x0 + 0.020, 0.020, z0 + 0.020), (x1 - 0.020, 0.055, z1 - 0.020), P.ALU)          # louvre face
    for k in range(6):
        z = z0 + 0.045 + k * 0.062
        m.box((x0 + 0.030, 0.008, z), (x1 - 0.030, 0.030, z + 0.030), P.ALU)
    m.box((x0 - 0.075, -0.020, z1), (x1 + 0.075, P.WYTHE, z1 + 0.100), "precast")
    m.box((x0 - 0.075, -0.045, z0 - 0.070), (x1 + 0.075, P.WYTHE, z0), "precast")
    return m
