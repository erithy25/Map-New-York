"""Sidewalk sheds, pipe scaffold, construction fencing and facade vegetation (9 pieces).

Sidewalk sheds follow NYC DOB rules (1 RCNY 3300-01): 2.44 m (8 ft) minimum clear height under the deck, posts on
2.44 m centres, a deck the full sidewalk width and a 1.07 m (42 in) parapet of hunter-green plywood on the street
edge. Construction fences are 2.44 m (8 ft) high with viewing panels every 4.57 m (15 ft).

Origin: bottom-centre of the footprint at pavement level, +Y towards the building (the shed's building edge is at
y = 0, the street edge at −y).
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P

SHED_CLEAR = 2.440       # clear height under the deck
SHED_DECK = 0.300        # deck structure depth
SHED_PARAPET = 1.070     # parapet above the deck
SHED_DEPTH = 4.270       # 14 ft — a typical Manhattan sidewalk


def _shed_frame(m: K.Mesh, x0: float, x1: float, y0: float, y1: float) -> None:
    """Posts, headers, deck joists, plank deck and the green parapet of one sidewalk-shed bay."""
    zd = SHED_CLEAR
    zt = zd + SHED_DECK
    for x in (x0 + 0.11, x1 - 0.11):                                            # vertical posts, street and building lines
        for y in (y0 + 0.11, y1 - 0.11):
            m.box((x - 0.055, y - 0.055, 0.0), (x + 0.055, y + 0.055, zd), P.GREEN)
            m.box((x - 0.125, y - 0.125, 0.0), (x + 0.125, y + 0.125, 0.030), P.GALV)      # base plate
    for y in (y0 + 0.11, y1 - 0.11):                                            # longitudinal headers
        m.box((x0, y - 0.075, zd - 0.20), (x1, y + 0.075, zd), P.GREEN)
    for x in (x0 + 0.11, x1 - 0.11):                                            # cross beams
        m.box((x - 0.070, y0, zd - 0.20), (x + 0.070, y1, zd), P.GREEN)
    njoist = 7
    for k in range(njoist):                                                     # deck joists
        y = y0 + (y1 - y0) * (k + 0.5) / njoist
        m.box((x0, y - 0.045, zd), (x1, y + 0.045, zd + 0.140), "interior_wood_floor")
    m.box((x0, y0, zd + 0.140), (x1, y1, zt), "interior_wood_floor")            # plank deck
    m.box((x0, y0 - 0.020, zt), (x1, y0 + 0.030, zt + SHED_PARAPET), "plywood_green")     # street parapet
    m.box((x0, y0 - 0.045, zt + SHED_PARAPET - 0.055), (x1, y0 + 0.045, zt + SHED_PARAPET), P.GREEN)
    for sx, x in ((1, x0 + 0.11), (-1, x1 - 0.11)):                             # inward-facing knee braces
        for y in (y0 + 0.11, y1 - 0.11):
            P._bar(m, K.Vector((x + sx * 0.55, y, zd - 0.24)), K.Vector((x, y, zd - 0.80)),
                   K.Vector((0.0, 1.0, 0.0)), 0.055, 0.045, P.GREEN)
    for k in range(2):                                                           # under-deck lighting
        x = x0 + (x1 - x0) * (k + 0.5) / 2
        m.box((x - 0.55, -SHED_DEPTH / 2 + 0.9, zd - 0.10), (x + 0.55, -SHED_DEPTH / 2 + 1.05, zd - 0.055), "fluoro_white")


@K.register("sidewalk_shed_module", "scaffold", anchor="ground_bottom_centre", nominal_size=(3.08, 4.33, 3.81),
            description="Standard NYC sidewalk-shed bay: 3.05 m long x 4.27 m deep, 2.44 m clear height, timber deck on green "
                        "steel posts and headers, 1.07 m hunter-green plywood parapet and two under-deck lights.",
            features=["sidewalk_shed"], budget=3000)
def _shed_module():
    m = K.Mesh()
    _shed_frame(m, -1.525, 1.525, -SHED_DEPTH, 0.0)
    return m


@K.register("sidewalk_shed_corner", "scaffold", anchor="ground_corner_bottom", nominal_size=(4.33, 4.33, 3.81),
            description="Sidewalk-shed corner bay: the deck turned 90 deg round a building corner with parapets on both street "
                        "edges and a corner post cluster.",
            features=["sidewalk_shed"], budget=3000)
def _shed_corner():
    m = K.Mesh()
    a = SHED_DEPTH
    zd, zt = SHED_CLEAR, SHED_CLEAR + SHED_DECK
    for (px, py) in ((-a + 0.11, -a + 0.11), (-0.11, -a + 0.11), (-a + 0.11, -0.11), (-0.11, -0.11)):
        m.box((px - 0.055, py - 0.055, 0.0), (px + 0.055, py + 0.055, zd), P.GREEN)
        m.box((px - 0.125, py - 0.125, 0.0), (px + 0.125, py + 0.125, 0.030), P.GALV)
    for py in (-a + 0.11, -0.11):
        m.box((-a, py - 0.075, zd - 0.20), (0.0, py + 0.075, zd), P.GREEN)
    for px in (-a + 0.11, -0.11):
        m.box((px - 0.075, -a, zd - 0.20), (px + 0.075, 0.0, zd), P.GREEN)
    for k in range(9):
        y = -a + a * (k + 0.5) / 9
        m.box((-a, y - 0.045, zd), (0.0, y + 0.045, zd + 0.140), "interior_wood_floor")
    m.box((-a, -a, zd + 0.140), (0.0, 0.0, zt), "interior_wood_floor")
    m.box((-a, -a - 0.020, zt), (0.0, -a + 0.030, zt + SHED_PARAPET), "plywood_green")            # -Y parapet
    m.box((-a - 0.020, -a, zt), (-a + 0.030, 0.0, zt + SHED_PARAPET), "plywood_green")            # -X parapet
    m.box((-a, -a - 0.045, zt + SHED_PARAPET - 0.055), (0.0, -a + 0.045, zt + SHED_PARAPET), P.GREEN)
    m.box((-a - 0.045, -a, zt + SHED_PARAPET - 0.055), (-a + 0.045, 0.0, zt + SHED_PARAPET), P.GREEN)
    m.box((-1.75, -a + 0.10, zd - 0.10), (-0.60, -a + 0.25, zd - 0.055), "fluoro_white")
    return m


@K.register("scaffold_pipe_bay", "scaffold", anchor="ground_bottom_centre", nominal_size=(2.28, 1.06, 7.004),
            description="Tube-and-clamp pipe scaffold bay: 2.13 m long x 0.91 m wide x 6.10 m of three lifts, with plank "
                        "platforms, toe boards, guard rails, ledger bracing and screw jacks.",
            features=["sidewalk_shed"], budget=3000)
def _pipe_scaffold():
    m = K.Mesh()
    L, Wd = 2.130, 0.910
    lifts = (2.000, 4.000, 6.000)
    for x in (-L / 2, L / 2):
        for y in (-Wd, 0.0):
            m.cylinder((x, y, 0.10), (x, y, 6.100), 0.024, P.GALV, segments=8)
            m.box((x - 0.075, y - 0.075, 0.0), (x + 0.075, y + 0.075, 0.030), P.GALV)          # base plate
            m.cylinder((x, y, 0.030), (x, y, 0.10), 0.016, P.GALV, segments=6)                  # screw jack
    for z in lifts:
        for y in (-Wd, 0.0):
            m.cylinder((-L / 2, y, z), (L / 2, y, z), 0.024, P.GALV, segments=8)                # ledgers
            m.cylinder((-L / 2, y, z + 0.480), (L / 2, y, z + 0.480), 0.024, P.GALV, segments=8)  # mid rail
            m.cylinder((-L / 2, y, z + 0.980), (L / 2, y, z + 0.980), 0.024, P.GALV, segments=8)  # guard rail
        for x in (-L / 2, L / 2):
            m.cylinder((x, -Wd, z), (x, 0.0, z), 0.024, P.GALV, segments=8)                     # transoms
        for k in range(3):                                                                       # scaffold boards
            y = -Wd + 0.06 + k * 0.28
            m.box((-L / 2, y, z + 0.024), (L / 2, y + 0.245, z + 0.062), "interior_wood_floor")
        m.box((-L / 2, -Wd - 0.02, z + 0.062), (L / 2, -Wd + 0.02, z + 0.212), "interior_wood_floor")   # toe board
        P._bar(m, K.Vector((-L / 2, -Wd, z)), K.Vector((L / 2, -Wd, z + 0.980)), K.Vector((0.0, 1.0, 0.0)), 0.040, 0.024, P.GALV)
    return m


@K.register("construction_fence_plywood", "fence", anchor="ground_bottom_centre", nominal_size=(2.44, 0.14, 2.485),
            description="NYC construction fence bay: 2.44 m x 2.44 m of hunter-green plywood on 100 x 100 mm posts and rails, "
                        "with a 300 mm viewing port and a raked cap.",
            features=[], budget=800)
def _fence_plywood():
    m = K.Mesh()
    W, H = 2.440, 2.440
    m.box((-W / 2, -0.010, 0.0), (W / 2, 0.010, H), "plywood_green")                                  # sheathing
    for x in (-W / 2 + 0.05, 0.0, W / 2 - 0.05):                                                      # posts
        m.box((x - 0.050, 0.010, 0.0), (x + 0.050, 0.110, H), "interior_wood_floor")
    for z in (0.30, 1.20, H - 0.12):                                                                   # rails
        m.box((-W / 2, 0.010, z - 0.045), (W / 2, 0.070, z + 0.045), "interior_wood_floor")
    m.box((-W / 2, -0.030, H), (W / 2, 0.110, H + 0.045), "plywood_green")                             # cap
    m.box((-0.60, -0.020, 1.35), (-0.30, 0.020, 1.65), P.GLASS)                                        # viewing port
    m.box((-0.62, -0.030, 1.33), (-0.28, -0.014, 1.67), "paint_grey")
    m.box((0.30, -0.016, 0.90), (1.05, -0.012, 1.95), "paint_white")                                   # posted permit board
    return m


@K.register("construction_fence_chainlink", "fence", anchor="ground_bottom_centre", nominal_size=(3.31, 0.6, 1.863),
            description="Free-standing chain-link fence panel on concrete feet: 3.05 x 1.83 m frame with mesh cross-wires and "
                        "a green privacy scrim strip.",
            features=[], budget=800)
def _fence_chain():
    m = K.Mesh()
    W, H = 3.050, 1.830
    for x in (-W / 2, W / 2):
        m.cylinder((x, 0.0, 0.0), (x, 0.0, H), 0.024, P.GALV, segments=8)
    for z in (0.030, H):
        m.cylinder((-W / 2, 0.0, z), (W / 2, 0.0, z), 0.020, P.GALV, segments=8)
    n = 15
    for k in range(n + 1):                                                        # mesh as crossed wires
        t = k / n
        x = -W / 2 + W * t
        P._bar(m, K.Vector((x, 0.0, 0.03)), K.Vector((min(x + H, W / 2), 0.0, 0.03 + min(H, W / 2 - x))),
               K.Vector((0.0, 1.0, 0.0)), 0.008, 0.006, P.GALV)
        P._bar(m, K.Vector((x, 0.0, 0.03)), K.Vector((max(x - H, -W / 2), 0.0, 0.03 + min(H, x + W / 2))),
               K.Vector((0.0, 1.0, 0.0)), 0.008, 0.006, P.GALV)
    m.box((-W / 2, -0.006, 0.90), (W / 2, 0.006, 1.60), "plywood_green")           # privacy scrim
    for x in (-W / 2, W / 2):                                                       # concrete feet
        m.box((x - 0.13, -0.30, 0.0), (x + 0.13, 0.30, 0.115), "concrete")
    return m


@K.register("fence_iron_areaway", "fence", anchor="ground_bottom_centre", nominal_size=(2.487, 0.05, 1.2),
            description="Wrought-iron areaway / yard fence: 2.44 m run, 1.07 m high with 16 mm square pickets at 120 mm, two "
                        "rails and spear finials.",
            features=["areaway_railing"], budget=800)
def _fence_iron():
    m = K.Mesh()
    W, H = 2.440, 1.070
    P.railing(m, [(-W / 2, 0.0, 0.0), (W / 2, 0.0, 0.0)], H, P.IRON, pitch=0.135, rails=2, picket=0.016)
    n = int(W / 0.135)
    for k in range(n + 1):                                                          # spear finials
        x = -W / 2 + W * k / n
        m.lathe([(0.016, H + 0.03), (0.026, H + 0.055), (0.0, H + 0.130)], 5, P.IRON, center=(x, 0.0))
    return m


@K.register("ivy_panel_dense", "vegetation", nominal_size=(1.947, 0.185, 2.0),
            description="Dense Boston-ivy panel, 2 x 2 m: three depth layers of alpha-cut leaf cards clinging to a wall.",
            features=["ivy"], budget=1500)
def _ivy_dense():
    return _ivy(2.0, 2.0, 190, 0.20)


@K.register("ivy_panel_sparse", "vegetation", nominal_size=(1.947, 0.144, 2.0),
            description="Sparse ivy panel, 2 x 2 m: scattered leaf cards with bare wall between, for the edges of an ivy mass.",
            features=["ivy"], budget=1500)
def _ivy_sparse():
    return _ivy(2.0, 2.0, 70, 0.16)


def _ivy(w: float, h: float, n: int, depth: float) -> K.Mesh:
    m = K.Mesh()
    rnd = P._lcg(4242)
    for _ in range(n):
        r = 0.085 + rnd() * 0.095
        cx = -w / 2 + r + rnd() * (w - 2 * r)
        cz = r + rnd() * (h - 2 * r)
        cy = -depth * (0.25 + 0.75 * rnd())
        a = rnd() * math.pi
        ca, sa = math.cos(a), math.sin(a)
        m.face([(cx - r * ca, cy, cz - r * sa), (cx + r * ca, cy, cz - r * sa),
                (cx + r * ca, cy, cz + r * sa), (cx - r * ca, cy, cz + r * sa)], "ivy_leaf",
               uvs=[(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)])
    for k in range(5):                                                            # woody stems, ragged heights
        x = -w / 2 + w * (k + 0.5) / 5 + (rnd() - 0.5) * 0.10
        m.box((x - 0.008, -0.026, 0.0), (x + 0.008, -0.014, h * (0.55 + 0.45 * rnd())), "soil")
    return m


@K.register("roof_weeds_patch", "vegetation", anchor="ground_bottom_centre", nominal_size=(1.56, 1.56, 0.538),
            description="Self-seeded ailanthus and grass patch on a neglected roof or areaway: crossed foliage cards over a "
                        "gravel and soil mound.",
            features=["ivy"], budget=1500)
def _weeds():
    m = K.Mesh()
    rnd = P._lcg(777)
    m.lathe([(0.0, 0.055), (0.55, 0.035), (0.78, 0.0)], 12, "soil")
    for _ in range(46):
        cx = -0.70 + rnd() * 1.40
        cy = -0.70 + rnd() * 1.40
        if cx * cx + cy * cy > 0.55:
            continue
        hh = 0.16 + rnd() * 0.36
        r = 0.055 + rnd() * 0.075
        a = rnd() * math.pi
        mat = "foliage_green" if rnd() > 0.28 else "foliage_green_dry"
        for aa in (a, a + math.pi / 2):
            dx, dy = r * math.cos(aa), r * math.sin(aa)
            m.face([(cx - dx, cy - dy, 0.03), (cx + dx, cy + dy, 0.03),
                    (cx + dx, cy + dy, 0.03 + hh), (cx - dx, cy - dy, 0.03 + hh)], mat)
    return m
