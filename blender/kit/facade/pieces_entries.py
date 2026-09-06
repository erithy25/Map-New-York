"""Entrance pieces: tenement and brownstone stoops, areaway railing, lobby canopy, doors, roll gates, garage and
church doors, cellar hatch and a brownstone door surround (13 pieces).

Origin: bottom-centre of the piece where it meets the wall (y = 0) at sidewalk level (z = 0). Stoops project into
negative y (towards the street); the doorway itself is in the wall plane.
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P

DOOR_W, DOOR_H = 0.915, 2.130          # 3 ft x 7 ft leaf


def _panel_door(m: K.Mesh, x0: float, x1: float, z0: float, z1: float, y: float, mat: str, *, panels: int = 4,
                thick: float = 0.045, glazed_top: bool = False) -> None:
    """Panelled door leaf: stiles, rails, recessed panels (and an optional glazed upper light)."""
    w = x1 - x0
    stile = 0.115
    m.box((x0, y, z0), (x1, y + thick, z1), mat)
    inner_x0, inner_x1 = x0 + stile, x1 - stile
    rows = panels // 2 if panels >= 2 else 1
    top = z1 - 0.14
    bot = z0 + 0.22
    for r in range(rows):
        pz0 = bot + (top - bot) * r / rows + 0.045
        pz1 = bot + (top - bot) * (r + 1) / rows - 0.045
        if glazed_top and r == rows - 1:
            m.glass_pane(inner_x0, inner_x1, pz0, pz1, y + thick / 2, P.GLASS)
            m.face([(inner_x0, y + thick / 2 + 0.06, pz0), (inner_x0, y + thick / 2 + 0.06, pz1),
                    (inner_x1, y + thick / 2 + 0.06, pz1), (inner_x1, y + thick / 2 + 0.06, pz0)], "interior_unlit",
                   uvs=[(0, 0), (0, 1), (1, 1), (1, 0)])
            continue
        cx0, cx1 = inner_x0 + 0.045, inner_x1 - 0.045
        m.box((cx0, y - 0.010, pz0), (cx1, y + 0.002, pz1), mat)               # raised panel bolection
        m.box((cx0 + 0.030, y - 0.016, pz0 + 0.030), (cx1 - 0.030, y - 0.008, pz1 - 0.030), mat)
    m.cylinder((x1 - 0.10, y - 0.045, (z0 + z1) / 2), (x1 - 0.10, y + thick + 0.02, (z0 + z1) / 2), 0.022, "chrome", segments=8)


def _steps(m: K.Mesh, n: int, rise: float, run: float, x0: float, x1: float, mat: str, y_top: float = 0.0,
           z0: float = 0.0) -> tuple[float, float]:
    """``n`` steps climbing from the street (−y) to y_top. Returns (front y, top z)."""
    y_front = y_top - n * run
    for i in range(n):
        yb = y_front + i * run
        zb = z0 + i * rise
        m.box((x0, yb, z0), (x1, yb + run, zb + rise), mat, faces="yzZxX")
    return y_front, z0 + n * rise


def _cheek_wall(m: K.Mesh, x: float, w: float, n: int, rise: float, run: float, y_top: float, mat: str,
                z0: float = 0.0, wall_h: float = 0.62) -> None:
    """Solid stoop cheek wall with a stepped, ramped top (brownstone practice)."""
    y_front = y_top - n * run
    m.box((x - w / 2, y_front, z0), (x + w / 2, y_top, z0), mat, faces="z")
    prof = [(y_front, z0)]
    for i in range(n):
        prof.append((y_front + i * run, z0 + i * rise + wall_h))
        prof.append((y_front + (i + 1) * run, z0 + i * rise + wall_h))
    prof.append((y_top, z0))
    m.extrude_profile(prof, x - w / 2, x + w / 2, mat, closed=True, caps=True, flip=True)


# --------------------------------------------------------------------------- 1  tenement stoop, 4 risers
@K.register("entry_stoop_tenement_4", "door_entry", nominal_size=(1.83, 2.19, 3.05),
            description="Tenement entrance: 4-riser bluestone stoop (178 mm rise, 305 mm tread) with iron handrails, a recessed "
                        "doorway with transom and a moulded stone hood.",
            features=["stoop"], budget=2200)
def _stoop_tenement():
    m = K.Mesh()
    n, rise, run = 4, 0.178, 0.305
    w = 1.520
    x0, x1 = -w / 2, w / 2
    y_front, z_top = _steps(m, n, rise, run, x0, x1, "granite", y_top=-0.60)
    m.box((x0, -0.60, 0.0), (x1, 0.0, z_top), "granite", faces="zZxX")               # landing
    for s in (-1, 1):
        P.railing(m, [(s * (w / 2 - 0.06), y_front + 0.05, 0.05), (s * (w / 2 - 0.06), y_front + n * run, n * rise + 0.05),
                      (s * (w / 2 - 0.06), 0.0, n * rise + 0.05)], 0.82, P.BLACK, pitch=0.16, rails=2)
    # doorway
    dw, dh = 1.180, 2.290
    P.reveal(m, -dw / 2, dw / 2, z_top, z_top + dh, 0.32, "red_brick")
    _panel_door(m, -dw / 2 + 0.055, dw / 2 - 0.055, z_top + 0.03, z_top + 1.98, 0.24, "paint_darkgreen", panels=4, glazed_top=True)
    m.glass_pane(-dw / 2 + 0.075, dw / 2 - 0.075, z_top + 2.04, z_top + dh - 0.05, 0.26, P.GLASS)     # transom
    m.box((-dw / 2 + 0.055, 0.20, z_top + 1.98), (dw / 2 - 0.055, 0.30, z_top + 2.04), "paint_darkgreen")
    m.box((-dw / 2 - 0.10, -0.075, z_top + dh), (dw / 2 + 0.10, P.WYTHE, z_top + dh + 0.15), "limestone")   # hood
    P.corbel_bracket(m, -dw / 2 - 0.04, 0.0, z_top + dh - 0.50, z_top + dh, 0.13, "limestone", width=0.10)
    P.corbel_bracket(m, dw / 2 + 0.04, 0.0, z_top + dh - 0.50, z_top + dh, 0.13, "limestone", width=0.10)
    return m


# --------------------------------------------------------------------------- 2  brownstone stoop, 10 risers
@K.register("entry_stoop_brownstone_10", "door_entry", nominal_size=(2.60, 4.40, 4.60),
            description="Brownstone high stoop: 10 risers (190 mm rise, 279 mm tread), cheek walls with newel blocks, cast-iron "
                        "railings, an areaway rail across the front and a round-arched double doorway.",
            features=["stoop", "areaway_railing"], budget=3000)
def _stoop_brownstone():
    m = K.Mesh()
    n, rise, run = 10, 0.190, 0.279
    w = 1.560                       # 5 ft 1 in between cheek walls
    cheek = 0.300
    x0, x1 = -w / 2, w / 2
    y_top = -1.220                  # 4 ft landing in front of the door
    y_front, z_top = _steps(m, n, rise, run, x0, x1, "brownstone", y_top=y_top)
    m.box((x0, y_top, 0.0), (x1, 0.0, z_top), "brownstone", faces="zZxX")
    for s in (-1, 1):
        _cheek_wall(m, s * (w / 2 + cheek / 2), cheek, n, rise, run, y_top, "brownstone")
        m.box((s * (w / 2 + cheek / 2) - cheek / 2, y_top, 0.0), (s * (w / 2 + cheek / 2) + cheek / 2, 0.0, z_top + 0.62), "brownstone")
        # newel block at the foot of the cheek wall
        m.box((s * (w / 2 + cheek / 2) - 0.185, y_front - 0.30, 0.0), (s * (w / 2 + cheek / 2) + 0.185, y_front + 0.06, 0.98), "brownstone")
        m.box((s * (w / 2 + cheek / 2) - 0.210, y_front - 0.325, 0.98), (s * (w / 2 + cheek / 2) + 0.210, y_front + 0.085, 1.06), "brownstone")
        # cast-iron rail on the cheek wall
        P.railing(m, [(s * (w / 2 + cheek / 2), y_front + 0.10, 0.68), (s * (w / 2 + cheek / 2), y_top, z_top + 0.64),
                      (s * (w / 2 + cheek / 2), 0.0, z_top + 0.64)], 0.34, P.IRON, pitch=0.145, rails=2)
    # areaway railing returning across the front of the yard each side of the stoop (the long runs use
    # entry_areaway_railing, which butts against these returns)
    for s in (-1, 1):
        xa = s * (w / 2 + cheek + 0.02)
        xb = s * (w / 2 + cheek + 0.92)
        P.railing(m, [(xa, y_front - 0.30, 0.0), (xb, y_front - 0.30, 0.0)], 0.92, P.IRON, pitch=0.135, rails=2)
    # round-arched doorway with double doors
    dw, dh = 1.520, 2.740
    P.reveal(m, -dw / 2, dw / 2, z_top, z_top + dh - dw / 2, 0.34, "brownstone", head=False)
    for i in range(9):
        a0 = math.pi * i / 9
        a1 = math.pi * (i + 1) / 9
        r = dw / 2
        zc = z_top + dh - r
        p0 = (r * math.cos(a0), zc + r * math.sin(a0))
        p1 = (r * math.cos(a1), zc + r * math.sin(a1))
        m.face([(p0[0], 0.0, p0[1]), (p1[0], 0.0, p1[1]), (p1[0], 0.34, p1[1]), (p0[0], 0.34, p0[1])], "brownstone")
        q0 = ((r + 0.16) * math.cos(a0), zc + (r + 0.16) * math.sin(a0))
        q1 = ((r + 0.16) * math.cos(a1), zc + (r + 0.16) * math.sin(a1))
        m.face([(p0[0], -0.075, p0[1]), (p1[0], -0.075, p1[1]), (q1[0], -0.075, q1[1]), (q0[0], -0.075, q0[1])], "brownstone")
        m.face([(q0[0], -0.075, q0[1]), (q1[0], -0.075, q1[1]), (q1[0], P.WYTHE, q1[1]), (q0[0], P.WYTHE, q0[1])], "brownstone")
    for s, xa, xb in ((-1, -dw / 2 + 0.055, -0.010), (1, 0.010, dw / 2 - 0.055)):
        _panel_door(m, xa, xb, z_top + 0.03, z_top + 2.10, 0.26, "paint_darkgreen", panels=4, glazed_top=True)
    zc = z_top + dh - dw / 2
    for i in range(8):                                                   # fanlight over the doors
        a0 = math.pi * (i + 0.5) / 9
        a1 = math.pi * (i + 1.5) / 9
        r = dw / 2 - 0.05
        m.face([(0.0, 0.28, zc), (r * math.cos(a0), 0.28, zc + r * math.sin(a0)), (r * math.cos(a1), 0.28, zc + r * math.sin(a1))], P.GLASS)
    m.box((-dw / 2 + 0.055, 0.22, z_top + 2.10), (dw / 2 - 0.055, 0.32, z_top + 2.18), "paint_darkgreen")
    return m


# --------------------------------------------------------------------------- 3  areaway railing
@K.register("entry_areaway_railing", "door_entry", nominal_size=(3.05, 0.09, 1.05),
            description="Cast-iron areaway railing, 3.05 m run, 0.92 m high with 14 mm square pickets at 135 mm and a cast newel "
                        "at each end (brownstone / rowhouse front yard).",
            features=["areaway_railing"], budget=900)
def _areaway_rail():
    m = K.Mesh()
    P.railing(m, [(-1.525, 0.0, 0.0), (1.525, 0.0, 0.0)], 0.92, P.IRON, pitch=0.135, rails=2)
    for s in (-1, 1):
        m.box((s * 1.525 - 0.055, -0.055, 0.0), (s * 1.525 + 0.055, 0.055, 0.98), P.IRON)      # newel post
        m.box((s * 1.525 - 0.075, -0.075, 0.98), (s * 1.525 + 0.075, 0.075, 1.05), P.IRON)     # cap
    return m


# --------------------------------------------------------------------------- 4  lobby canopy
@K.register("entry_lobby_canopy", "door_entry", nominal_size=(2.44, 3.66, 3.20), anchor="wall_bottom_centre",
            description="Apartment-house lobby canopy: 2.44 x 3.66 m aluminium-framed canvas marquee on two sidewalk posts with "
                        "a valance and recessed downlights.",
            features=["canopy"], budget=2000)
def _lobby_canopy():
    m = K.Mesh()
    w, proj = 2.440, 3.660
    x0, x1 = -w / 2, w / 2
    z_deck, z_front = 3.05, 2.85           # slopes down towards the street
    m.face([(x0, 0.0, z_deck), (x0, -proj, z_front), (x1, -proj, z_front), (x1, 0.0, z_deck)], "canvas_striped",
           uvs=[(0, 0), (0, proj), (w, proj), (w, 0)])
    m.face([(x0, 0.0, z_deck - 0.10), (x1, 0.0, z_deck - 0.10), (x1, -proj, z_front - 0.10), (x0, -proj, z_front - 0.10)],
           "paint_white", uvs=[(0, 0), (w, 0), (w, proj), (0, proj)])
    for s in (-1, 1):                                                    # side fascias
        m.face([(s * w / 2, 0.0, z_deck - 0.10), (s * w / 2, -proj, z_front - 0.10),
                (s * w / 2, -proj, z_front), (s * w / 2, 0.0, z_deck)], "canvas_striped", flip=(s < 0))
    m.box((x0, -proj - 0.02, z_front - 0.42), (x1, -proj + 0.02, z_front), "canvas_striped")     # valance
    for s in (-1, 1):                                                    # posts
        x = s * (w / 2 - 0.10)
        m.cylinder((x, -proj + 0.14, 0.0), (x, -proj + 0.14, z_front - 0.10), 0.048, P.ALU, segments=10)
        m.box((x - 0.11, -proj + 0.03, 0.0), (x + 0.11, -proj + 0.25, 0.030), P.ALU)
        P._bar(m, K.Vector((x, 0.02, z_deck + 0.06)), K.Vector((x, -0.80, z_deck - 0.06)), K.Vector((0.0, 0.0, 1.0)), 0.030, 0.030, P.ALU)
    for k in range(4):                                                   # downlights in the soffit
        y = -0.5 - k * 0.85
        m.box((-0.12, y - 0.12, z_front - 0.115), (0.12, y + 0.12, z_front - 0.10), "fluoro_white")
    m.box((x0 - 0.03, -0.06, z_deck), (x1 + 0.03, 0.02, z_deck + 0.15), P.ALU)                    # wall flashing
    return m


# --------------------------------------------------------------------------- 5  double doors
@K.register("entry_double_doors", "door_entry", nominal_size=(1.98, 0.42, 3.05),
            description="Residential double entrance doors, 1.83 m opening: panelled leaves with glazed upper lights, a fixed "
                        "transom and a moulded wood surround.",
            features=[], budget=1600)
def _double_doors():
    m = K.Mesh()
    dw, dh = 1.830, 2.900
    P.reveal(m, -dw / 2, dw / 2, 0.0, dh, 0.34, "red_brick")
    m.frame(-dw / 2, dw / 2, 0.0, dh, 0.20, 0.32, 0.085, "paint_darkgreen")
    for xa, xb in ((-dw / 2 + 0.085, -0.010), (0.010, dw / 2 - 0.085)):
        _panel_door(m, xa, xb, 0.02, 2.180, 0.235, "paint_darkgreen", panels=4, glazed_top=True)
    m.box((-dw / 2 + 0.085, 0.20, 2.180), (dw / 2 - 0.085, 0.30, 2.250), "paint_darkgreen")
    m.glass_pane(-dw / 2 + 0.10, dw / 2 - 0.10, 2.260, dh - 0.09, 0.255, P.GLASS)
    m.box((-dw / 2 - 0.09, -0.055, dh), (dw / 2 + 0.09, P.WYTHE, dh + 0.15), "limestone")
    return m


# --------------------------------------------------------------------------- 6  single panel door
@K.register("entry_door_single_panel", "door_entry", nominal_size=(1.12, 0.42, 2.55),
            description="Single 3 ft x 7 ft panelled entrance door in a masonry opening with a fixed transom light.",
            features=[], budget=900)
def _single_door():
    m = K.Mesh()
    dw, dh = 1.020, 2.440
    P.reveal(m, -dw / 2, dw / 2, 0.0, dh, 0.34, "red_brick")
    m.frame(-dw / 2, dw / 2, 0.0, dh, 0.20, 0.32, 0.070, "paint_maroon")
    _panel_door(m, -DOOR_W / 2, DOOR_W / 2, 0.02, DOOR_H, 0.235, "paint_maroon", panels=6)
    m.box((-dw / 2 + 0.07, 0.20, DOOR_H), (dw / 2 - 0.07, 0.30, DOOR_H + 0.06), "paint_maroon")
    m.glass_pane(-dw / 2 + 0.09, dw / 2 - 0.09, DOOR_H + 0.07, dh - 0.075, 0.255, P.GLASS)
    m.box((-dw / 2 - 0.075, -0.045, dh), (dw / 2 + 0.075, P.WYTHE, dh + 0.13), "precast")
    return m


# --------------------------------------------------------------------------- 7  glass lobby entrance
@K.register("entry_apartment_lobby_glass", "door_entry", nominal_size=(2.44, 0.44, 3.05),
            description="Post-war apartment-house lobby entrance: aluminium-framed glass doors, sidelights, a transom and a "
                        "polished granite base.",
            features=[], budget=1600)
def _lobby_glass():
    m = K.Mesh()
    dw, dh = 2.300, 2.900
    P.reveal(m, -dw / 2, dw / 2, 0.0, dh, 0.36, "granite")
    y = 0.22
    m.frame(-dw / 2, dw / 2, 0.0, dh, y, y + 0.075, 0.060, P.ALU)
    side = 0.42
    for s in (-1, 1):                                                # sidelights and their inner mullions
        a, b = sorted((s * (dw / 2 - 0.060), s * (dw / 2 - 0.060 - side)))
        m.glass_pane(a, b, 0.060, dh - 0.55, y + 0.037, P.GLASS)
        xm = b if s < 0 else a
        m.box((xm - 0.028, y, 0.060), (xm + 0.028, y + 0.075, dh - 0.55), P.ALU)
    m.box((-dw / 2 + 0.060, y, dh - 0.61), (dw / 2 - 0.060, y + 0.075, dh - 0.55), P.ALU)     # transom bar
    m.glass_pane(-dw / 2 + 0.060, dw / 2 - 0.060, dh - 0.55, dh - 0.060, y + 0.037, P.GLASS)
    for s in (-1, 1):                                                # door leaves
        xa, xb = (-0.010, 0.900 - 0.010) if s > 0 else (-0.900 + 0.010, 0.010)
        m.frame(xa, xb, 0.030, 2.180, y - 0.020, y + 0.055, 0.055, P.ALU)
        m.glass_pane(xa + 0.055, xb - 0.055, 0.085, 2.125, y + 0.017, P.GLASS)
        xh = (xa + xb) / 2 + s * 0.34
        m.cylinder((xh, y - 0.075, 0.90), (xh, y - 0.075, 1.55), 0.018, "chrome", segments=8)     # pull handle
    m.face([(-dw / 2 + 0.06, y + 0.30, 0.06), (-dw / 2 + 0.06, y + 0.30, dh - 0.06),
            (dw / 2 - 0.06, y + 0.30, dh - 0.06), (dw / 2 - 0.06, y + 0.30, 0.06)], "interior_lit",
           uvs=[(0, 0), (0, 2), (2, 2), (2, 0)])
    m.box((-dw / 2 - 0.12, -0.055, dh), (dw / 2 + 0.12, P.WYTHE, dh + 0.15), "granite")
    return m


# --------------------------------------------------------------------------- 8  loft roll gate (entrance)
@K.register("entry_loft_roll_gate", "door_entry", nominal_size=(2.13, 0.36, 3.35),
            description="Loft-building freight entrance with a corrugated roll-down gate, steel guides and a hood box "
                        "(SoHo / Long Island City).",
            features=["roll_gate"], budget=1400)
def _loft_roll_gate():
    m = K.Mesh()
    w, h = 2.130, 3.050
    x0, x1 = -w / 2, w / 2
    P.reveal(m, x0, x1, 0.0, h, 0.30, "red_brick")
    m.box((x0 + 0.055, 0.10, 0.0), (x1 - 0.055, 0.16, h - 0.10), "corrugated_metal", uv_rot=0)
    for k in range(20):                                                     # slat shadow lines
        z = 0.06 + k * (h - 0.20) / 20
        m.box((x0 + 0.055, 0.086, z - 0.006), (x1 - 0.055, 0.10, z + 0.006), P.GALV)
    for s in (-1, 1):                                                       # guide channels
        m.box((s * (w / 2 - 0.055) - 0.035, 0.06, 0.0), (s * (w / 2 - 0.055) + 0.035, 0.20, h + 0.02), P.GALV)
    m.box((x0 - 0.06, -0.05, h - 0.10), (x1 + 0.06, 0.26, h + 0.30), P.GALV)   # hood box
    m.box((x0 + 0.055, 0.06, 0.0), (x1 - 0.055, 0.20, 0.055), P.BLACK)         # bottom bar
    return m


# --------------------------------------------------------------------------- 9  garage door
@K.register("entry_garage_door", "door_entry", nominal_size=(2.90, 0.32, 2.28),
            description="Sectional overhead garage door, 2.74 x 2.13 m, four panel courses with a row of lights and a painted "
                        "steel surround (rowhouse garage / small commercial).",
            features=["garage"], budget=1200)
def _garage_door():
    m = K.Mesh()
    w, h = 2.740, 2.130
    x0, x1 = -w / 2, w / 2
    P.reveal(m, x0, x1, 0.0, h, 0.28, "concrete")
    m.box((x0 + 0.02, 0.10, 0.0), (x1 - 0.02, 0.16, h - 0.01), "metal_panel")
    rows, cols = 4, 4
    for r in range(rows):
        z0 = 0.02 + (h - 0.05) * r / rows
        z1 = 0.02 + (h - 0.05) * (r + 1) / rows - 0.020
        for c in range(cols):
            cx0 = x0 + 0.06 + (w - 0.12) * c / cols + 0.025
            cx1 = x0 + 0.06 + (w - 0.12) * (c + 1) / cols - 0.025
            if r == rows - 1:
                m.glass_pane(cx0, cx1, z0 + 0.045, z1 - 0.045, 0.13, P.GLASS)
            else:
                m.box((cx0, 0.086, z0 + 0.030), (cx1, 0.102, z1 - 0.030), "metal_panel")
    m.box((x0 - 0.08, -0.020, 0.0), (x0 + 0.02, 0.18, h + 0.10), "paint_grey")
    m.box((x1 - 0.02, -0.020, 0.0), (x1 + 0.08, 0.18, h + 0.10), "paint_grey")
    m.box((x0 - 0.08, -0.020, h), (x1 + 0.08, 0.18, h + 0.15), "paint_grey")
    return m


# --------------------------------------------------------------------------- 10  church doors
@K.register("entry_church_doors", "door_entry", nominal_size=(2.72, 0.55, 4.30),
            description="Gothic church portal: pointed limestone arch with a moulded surround, twin oak plank doors with strap "
                        "hinges and a stone step.",
            features=[], budget=2600)
def _church_doors():
    m = K.Mesh()
    dw = 2.140
    x0, x1 = -dw / 2, dw / 2
    spring, R = 2.40, dw
    seg = 9

    def arch_z(x):
        cxx = x1 if x <= 0 else x0
        return spring + math.sqrt(max(R * R - (x - cxx) ** 2, 0.0))

    P.reveal(m, x0, x1, 0.0, spring, 0.42, "limestone", head=False)
    prev = None
    for i in range(seg + 1):
        x = x0 + dw * i / seg
        z = arch_z(x)
        if prev is not None:
            px, pz = prev
            m.face([(px, 0.0, pz), (x, 0.0, z), (x, 0.42, z), (px, 0.42, pz)], "limestone", flip=True)
            m.face([(px, -0.11, pz), (px, -0.11, pz + 0.22), (x, -0.11, z + 0.22), (x, -0.11, z)], "limestone")
            m.face([(px, -0.11, pz + 0.22), (px, P.WYTHE, pz + 0.22), (x, P.WYTHE, z + 0.22), (x, -0.11, z + 0.22)], "limestone")
            m.face([(px, -0.11, pz), (px, 0.0, pz), (x, 0.0, z), (x, -0.11, z)], "limestone", flip=True)
            m.face([(px, 0.30, spring), (x, 0.30, spring), (x, 0.30, z), (px, 0.30, pz)], "paint_darkgreen")   # tympanum
        prev = (x, z)
    for s in (-1, 1):                                                     # moulded jamb shafts
        m.box((s * (dw / 2) - 0.11 * s, -0.11, 0.0), (s * (dw / 2), P.WYTHE, spring + 0.10), "limestone")
        m.cylinder((s * (dw / 2 - 0.055), -0.055, 0.0), (s * (dw / 2 - 0.055), -0.055, spring), 0.055, "limestone", segments=8)
    for xa, xb in ((x0 + 0.11, -0.012), (0.012, x1 - 0.11)):
        m.box((xa, 0.26, 0.0), (xb, 0.32, spring - 0.10), "interior_wood_floor")
        for k in range(9):                                                # vertical plank lines
            xx = xa + (xb - xa) * (k + 1) / 10
            m.box((xx - 0.010, 0.244, 0.05), (xx + 0.010, 0.262, spring - 0.15), "interior_wood_floor")
        for zz in (0.55, 1.70):                                           # wrought strap hinges
            xh = xa if xa < 0 else xb
            sgn = 1 if xa < 0 else -1
            m.box((xh, 0.235, zz - 0.045), (xh + sgn * (xb - xa) * 0.55, 0.252, zz + 0.045), P.BLACK)
        m.cylinder(((xa + xb) / 2 + (0.30 if xa < 0 else -0.30), 0.20, 1.05),
                   ((xa + xb) / 2 + (0.30 if xa < 0 else -0.30), 0.27, 1.05), 0.045, P.BLACK, segments=8)
    m.box((x0 - 0.35, -0.55, 0.0), (x1 + 0.35, 0.0, 0.16), "granite")     # threshold step
    return m


# --------------------------------------------------------------------------- 11  steel service door
@K.register("entry_service_door_steel", "door_entry", nominal_size=(1.06, 0.30, 2.34),
            description="Hollow-metal service / cellar door: flush painted steel leaf, kick plate, louvre and a steel angle frame.",
            features=[], budget=500)
def _service_door():
    m = K.Mesh()
    dw, dh = 0.965, 2.180
    P.reveal(m, -dw / 2, dw / 2, 0.0, dh, 0.28, "red_brick")
    m.box((-dw / 2 + 0.05, 0.13, 0.0), (dw / 2 - 0.05, 0.175, dh - 0.03), "paint_grey")
    m.box((-dw / 2 + 0.08, 0.116, 0.03), (dw / 2 - 0.08, 0.132, 0.27), P.GALV)                 # kick plate
    for k in range(5):
        z = dh - 0.62 + k * 0.075
        m.box((-0.18, 0.114, z), (0.18, 0.132, z + 0.036), P.GALV)                              # louvre
    m.box((-dw / 2 + 0.05, 0.10, 0.0), (-dw / 2 + 0.08, 0.19, dh - 0.03), "paint_grey")
    m.cylinder((dw / 2 - 0.15, 0.075, 1.02), (dw / 2 - 0.15, 0.20, 1.02), 0.020, "chrome", segments=8)
    m.box((-dw / 2, -0.010, 0.0), (-dw / 2 + 0.05, 0.19, dh), P.GALV)
    m.box((dw / 2 - 0.05, -0.010, 0.0), (dw / 2, 0.19, dh), P.GALV)
    m.box((-dw / 2, -0.010, dh - 0.05), (dw / 2, 0.19, dh), P.GALV)
    return m


# --------------------------------------------------------------------------- 12  sidewalk cellar hatch
@K.register("entry_cellar_hatch", "door_entry", anchor="ground_bottom_centre", nominal_size=(1.52, 1.22, 0.24),
            description="Sidewalk cellar hatch: two diamond-plate steel leaves in a frame, flush with the pavement, with a hasp "
                        "and lift handles (bodega delivery hatch).",
            features=[], budget=400)
def _cellar_hatch():
    m = K.Mesh()
    w, d = 1.520, 1.220
    m.box((-w / 2, -d / 2, 0.0), (w / 2, d / 2, 0.030), P.GALV)                       # frame plate
    for s in (-1, 1):                                                                  # two leaves + lift handles
        ya, yb = sorted((s * 0.020, s * (d / 2 - 0.045)))
        m.box((-w / 2 + 0.045, ya, 0.030), (w / 2 - 0.045, yb, 0.055), P.GALV)
        m.cylinder((0.0, s * (d / 2 - 0.20), 0.055), (0.0, s * (d / 2 - 0.20), 0.075), 0.055, P.GALV, segments=8)
    m.box((-0.075, -0.030, 0.055), (0.075, 0.030, 0.115), P.BLACK)                     # hasp / padlock
    return m


# --------------------------------------------------------------------------- 13  brownstone door surround
@K.register("entry_brownstone_door_surround", "door_entry", nominal_size=(2.60, 0.32, 3.60),
            description="Italianate brownstone doorway enframement: moulded pilasters, scrolled console brackets and a projecting "
                        "pediment hood over a 1.52 m opening.",
            features=[], budget=1800)
def _door_surround():
    m = K.Mesh()
    dw, dh = 1.520, 2.740
    x0, x1 = -dw / 2, dw / 2
    for s in (-1, 1):                                                     # pilasters
        xc = s * (dw / 2 + 0.155)
        m.box((xc - 0.155, -0.095, 0.0), (xc + 0.155, P.WYTHE, dh), "brownstone")
        m.box((xc - 0.185, -0.125, 0.0), (xc + 0.185, P.WYTHE, 0.22), "brownstone")            # plinth
        m.box((xc - 0.185, -0.125, dh - 0.14), (xc + 0.185, P.WYTHE, dh), "brownstone")        # cap
        m.box((xc - 0.100, -0.135, 0.30), (xc + 0.100, -0.090, dh - 0.30), "brownstone")       # sunk panel
        P.corbel_bracket(m, xc, -0.095, dh, dh + 0.62, 0.30, "brownstone", width=0.24)
    m.box((x0 - 0.36, -0.42, dh + 0.62), (x1 + 0.36, P.WYTHE, dh + 0.76), "brownstone")        # cornice slab
    m.box((x0 - 0.40, -0.46, dh + 0.76), (x1 + 0.40, P.WYTHE, dh + 0.84), "brownstone")        # crown
    P.reveal(m, x0, x1, 0.0, dh, 0.30, "brownstone")
    m.box((x0 - 0.36, -0.42, dh + 0.50), (x1 + 0.36, -0.34, dh + 0.62), "brownstone")          # frieze band
    return m
