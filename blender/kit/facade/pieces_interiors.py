"""Storefront interior shells — one per entry of ``facade_params.STOREFRONT_INTERIOR_KINDS`` (11 pieces).

Each shell is 4.80 m wide, 2.50 m deep and 3.40 m high (to the storefront transom bar): floor, back and side walls,
ceiling, lighting and the fittings that identify the trade from the sidewalk. Origin: bottom-centre on the wall
plane, +Y into the shop, so a shell drops straight in behind any ``storefront_bay_*`` piece.

The eleven shells cover the twenty ``STOREFRONT_KINDS`` through ``facade_params.STOREFRONT_INTERIOR_FOR_KIND``.
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P
import facade_params as fp

WIDTH, DEPTH, HEIGHT = 4.800, 2.500, 3.400
X0, X1 = -WIDTH / 2, WIDTH / 2


def _shell(floor: str, wall: str, ceiling: str = "paint_white", *, lights: int = 3, warm: bool = False) -> K.Mesh:
    """Box shell open towards the street, with a lit ceiling."""
    m = K.Mesh()
    m.face([(X0, 0.0, 0.0), (X1, 0.0, 0.0), (X1, DEPTH, 0.0), (X0, DEPTH, 0.0)], floor)                      # floor
    m.face([(X0, DEPTH, 0.0), (X1, DEPTH, 0.0), (X1, DEPTH, HEIGHT), (X0, DEPTH, HEIGHT)], wall, flip=True)  # back wall
    m.face([(X0, 0.0, 0.0), (X0, 0.0, HEIGHT), (X0, DEPTH, HEIGHT), (X0, DEPTH, 0.0)], wall, flip=True)      # left wall
    m.face([(X1, DEPTH, 0.0), (X1, DEPTH, HEIGHT), (X1, 0.0, HEIGHT), (X1, 0.0, 0.0)], wall, flip=True)      # right wall
    m.face([(X0, 0.0, HEIGHT), (X1, 0.0, HEIGHT), (X1, DEPTH, HEIGHT), (X0, DEPTH, HEIGHT)], ceiling)        # ceiling
    lamp = "lamp_warm" if warm else "fluoro_white"
    for k in range(lights):
        y = DEPTH * (k + 0.5) / lights
        m.box((X0 + 0.45, y - 0.09, HEIGHT - 0.10), (X1 - 0.45, y + 0.09, HEIGHT - 0.055), lamp)
    return m


def _shelf_run(m: K.Mesh, x: float, y0: float, y1: float, z0: float, z1: float, shelves: int, mat: str,
               goods: tuple[str, ...] = ("paint_red", "paint_blue", "paint_yellow", "paint_cream"), depth: float = 0.36,
               facing: int = 1) -> None:
    """Gondola / wall shelving unit standing against a side wall, with blocks of stock on each shelf."""
    m.box((x, y0, z0), (x + facing * 0.030, y1, z1), mat)
    for k in range(shelves):
        z = z0 + (z1 - z0) * (k + 1) / (shelves + 1)
        m.box((x, y0, z - 0.020), (x + facing * depth, y1, z), mat)
        n = max(1, int((y1 - y0) / 0.30))
        for i in range(n):
            yy = y0 + (y1 - y0) * (i + 0.5) / n
            h = 0.16 + 0.06 * ((i * 7 + k * 3) % 3)
            m.box((x + facing * 0.05, yy - 0.11, z), (x + facing * (depth - 0.05), yy + 0.11, z + h), goods[(i + k) % len(goods)])


def _counter(m: K.Mesh, x0: float, x1: float, y: float, depth: float, h: float, top: str, body: str) -> None:
    m.box((x0, y, 0.0), (x1, y + depth, h - 0.035), body)
    m.box((x0 - 0.030, y - 0.030, h - 0.035), (x1 + 0.030, y + depth + 0.030, h), top)


def _stools(m: K.Mesh, x0: float, x1: float, y: float, n: int, h: float, mat: str) -> None:
    for k in range(n):
        x = x0 + (x1 - x0) * (k + 0.5) / n
        m.cylinder((x, y, 0.0), (x, y, h - 0.05), 0.030, P.GALV, segments=6)
        m.cylinder((x, y, h - 0.05), (x, y, h), 0.170, mat, segments=10)


def _chair(m: K.Mesh, x: float, y: float, mat: str, seat_h: float = 0.450) -> None:
    m.box((x - 0.22, y - 0.22, seat_h - 0.04), (x + 0.22, y + 0.22, seat_h), mat)
    m.box((x - 0.22, y + 0.16, seat_h), (x + 0.22, y + 0.22, seat_h + 0.44), mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((x + sx * 0.19 - 0.018, y + sy * 0.19 - 0.018, 0.0), (x + sx * 0.19 + 0.018, y + sy * 0.19 + 0.018, seat_h - 0.04), P.GALV)


def _reg(kind: str, desc: str, builder, budget: int = 6000):
    K.register(f"storefront_interior_{kind}", "storefront_interior", nominal_size=(WIDTH, DEPTH, HEIGHT),
               description=desc, features=["storefront"], budget=budget,
               extra={"interior_kind": kind, "shell_width_m": WIDTH, "shell_depth_m": DEPTH, "shell_height_m": HEIGHT,
                      # the shell is modelled at the middle bay width; for a 3.6 m bay it is wider than the opening,
                      # so the assembler either hides the overhang behind the brick piers or scales the shell in X
                      "may_scale_x": True,
                      "serves_storefront_kinds": sorted(k for k, v in fp.STOREFRONT_INTERIOR_FOR_KIND.items() if v == kind)})(builder)


# --------------------------------------------------------------------------- bodega
def _bodega():
    m = _shell("checker_tile", "interior_tile", lights=4)
    for s in (-1, 1):                                                       # gondola shelving down both side walls
        _shelf_run(m, s * (WIDTH / 2 - 0.03), 0.55, DEPTH - 0.12, 0.25, 2.05, 4, "metal_panel", facing=-s)
    for k in range(5):                                                      # glass-door beer coolers across the back
        x = X0 + 0.35 + k * 0.80
        m.box((x, DEPTH - 0.72, 0.0), (x + 0.76, DEPTH - 0.05, 2.05), "metal_panel")
        m.glass_pane(x + 0.045, x + 0.715, 0.16, 1.92, DEPTH - 0.715, P.GLASS)
        m.box((x + 0.045, DEPTH - 0.60, 0.20), (x + 0.715, DEPTH - 0.10, 1.85), "paint_blue")
        m.box((x, DEPTH - 0.74, 2.05), (x + 0.76, DEPTH - 0.05, 2.28), "fluoro_white")
    _counter(m, 0.65, 2.30, 0.28, 0.72, 1.05, "interior_wood_floor", "metal_panel")     # front counter
    m.box((0.65, 0.28, 1.05), (2.30, 0.34, 1.55), P.GLASS)                              # bullet-resistant screen
    m.box((0.90, 0.30, 1.06), (1.80, 0.68, 1.34), "paint_red")                          # cigarette rack behind the counter
    m.box((-2.20, 0.30, 0.0), (-1.20, 0.95, 1.10), "metal_panel")                       # newspaper / drinks island
    m.box((-2.20, 0.30, 1.10), (-1.20, 0.95, 1.16), "paint_yellow")
    return m


_reg("bodega", "Bodega interior: checkerboard floor, tile walls, gondola shelving down both sides, a five-door beer cooler wall, "
                "a screened counter with a cigarette rack and a drinks island.", _bodega)


# --------------------------------------------------------------------------- deli
def _deli():
    m = _shell("checker_tile", "subway_tile", lights=4)
    _counter(m, X0 + 0.30, 1.05, 0.55, 0.85, 1.10, "metal_panel", "metal_panel")        # refrigerated deli case
    m.face([(X0 + 0.30, 0.55, 0.95), (1.05, 0.55, 0.95), (1.05, 0.55, 1.065), (X0 + 0.30, 0.55, 1.065)], P.GLASS)
    for k in range(9):                                                                   # trays of meats and salads
        x = X0 + 0.42 + k * 0.28
        m.box((x, 0.68, 0.86), (x + 0.24, 1.30, 0.95), ("paint_red", "paint_cream", "paint_yellow")[k % 3])
    m.box((X0 + 0.30, DEPTH - 0.55, 0.0), (1.05, DEPTH - 0.05, 1.60), "metal_panel")     # back prep line
    m.box((X0 + 0.30, DEPTH - 0.58, 1.60), (1.05, DEPTH - 0.05, 2.30), "metal_panel")    # hood / shelf
    m.box((1.35, DEPTH - 0.75, 0.0), (2.30, DEPTH - 0.05, 0.95), "metal_panel")          # coffee station
    for k in range(3):
        m.cylinder((1.55 + k * 0.34, DEPTH - 0.40, 0.95), (1.55 + k * 0.34, DEPTH - 0.40, 1.42), 0.11, "metal_panel", segments=8)
    m.box((1.30, DEPTH - 0.10, 1.80), (2.35, DEPTH - 0.04, 2.70), "paint_red")           # menu board
    for k in range(6):
        m.box((1.36, DEPTH - 0.12, 1.90 + k * 0.13), (2.29, DEPTH - 0.10, 1.96 + k * 0.13), "paint_white")
    return m


_reg("deli", "Deli / coffee-shop interior: subway-tiled walls, a glass-fronted refrigerated deli case with trays, a stainless prep "
              "line and hood, a coffee station with urns and an illuminated menu board.", _deli)


# --------------------------------------------------------------------------- pharmacy
def _pharmacy():
    m = _shell("interior_tile", "paint_white", lights=4)
    for k in range(3):                                                                   # free-standing aisles
        x = X0 + 0.85 + k * 1.35
        _shelf_run(m, x, 0.45, DEPTH - 0.85, 0.20, 1.75, 4, "metal_panel", depth=0.30, facing=1)
        _shelf_run(m, x - 0.02, 0.45, DEPTH - 0.85, 0.20, 1.75, 4, "metal_panel", depth=0.30, facing=-1)
    m.box((X0 + 0.20, DEPTH - 0.80, 0.30), (X1 - 0.20, DEPTH - 0.72, 2.60), "metal_panel")   # raised pharmacy counter
    _counter(m, X0 + 0.20, X1 - 0.20, DEPTH - 0.72, 0.62, 1.25, "paint_white", "metal_panel")
    m.box((X0 + 0.30, DEPTH - 0.10, 2.20), (X1 - 0.30, DEPTH - 0.04, 2.80), "paint_blue")
    for s in (-1, 1):                                                                     # window advertising panels
        m.box((s * 1.80 - 0.45, 0.06, 1.10), (s * 1.80 + 0.45, 0.09, 2.10), "paint_red")
    return m


_reg("pharmacy", "Pharmacy interior: white tile floor, three double-sided aisles of stock, a raised dispensing counter across the "
                  "back wall and illuminated window advertising panels.", _pharmacy)


# --------------------------------------------------------------------------- restaurant
def _restaurant():
    m = _shell("interior_wood_floor", "paint_maroon", lights=3, warm=True)
    m.box((X0, 0.35, 0.0), (X0 + 0.62, DEPTH - 0.30, 1.15), "paint_maroon")               # banquette along the left wall
    m.box((X0, 0.35, 0.42), (X0 + 0.70, DEPTH - 0.30, 0.48), "interior_wood_floor")
    for k in range(3):                                                                     # tables
        y = 0.55 + k * 0.68
        m.cylinder((X0 + 1.10, y, 0.0), (X0 + 1.10, y, 0.72), 0.055, P.GALV, segments=6)
        m.cylinder((X0 + 1.10, y, 0.72), (X0 + 1.10, y, 0.755), 0.400, "interior_wood_floor", segments=12)
        _chair(m, X0 + 1.72, y, "paint_maroon")
    _counter(m, 0.60, X1 - 0.25, DEPTH - 1.00, 0.70, 1.05, "granite", "interior_wood_floor")   # service counter
    m.box((0.60, DEPTH - 0.20, 0.0), (X1 - 0.25, DEPTH - 0.05, 2.40), "metal_panel")           # back bar / kitchen pass
    m.box((0.70, DEPTH - 0.22, 1.35), (X1 - 0.35, DEPTH - 0.20, 2.20), "paint_black")          # chalk menu
    for k in range(3):
        cx = 0.75 + k * 0.72
        m.cylinder((cx, DEPTH - 1.30, 2.55), (cx, DEPTH - 1.30, 3.30), 0.010, P.BLACK, segments=4)
        m.lathe([(0.0, 2.38), (0.135, 2.55)], 10, "lamp_warm", center=(cx, DEPTH - 1.30), caps=(False, True))
    return m


_reg("restaurant", "Restaurant / pizzeria interior: wood floor, a banquette down one wall, three pedestal tables with chairs, a "
                    "granite-topped service counter, a stainless pass and pendant lights.", _restaurant)


# --------------------------------------------------------------------------- bar
def _bar():
    m = _shell("interior_wood_floor", "dark_brick", ceiling="paint_black", lights=2, warm=True)
    bar_y = 0.95
    _counter(m, X0 + 0.35, X1 - 0.90, bar_y, 0.62, 1.10, "interior_wood_floor", "interior_wood_floor")
    m.box((X0 + 0.35, bar_y - 0.10, 0.15), (X1 - 0.90, bar_y, 0.22), "metal_panel")            # foot rail
    _stools(m, X0 + 0.55, X1 - 1.10, bar_y - 0.42, 5, 0.760, "paint_maroon")
    m.box((X0 + 0.35, DEPTH - 0.42, 0.0), (X1 - 0.90, DEPTH - 0.10, 1.05), "interior_wood_floor")   # back bar base
    m.box((X0 + 0.35, DEPTH - 0.12, 1.05), (X1 - 0.90, DEPTH - 0.06, 2.90), "paint_black")           # mirror
    for k in range(3):                                                                                # bottle shelves
        z = 1.20 + k * 0.36
        m.box((X0 + 0.40, DEPTH - 0.40, z), (X1 - 0.95, DEPTH - 0.12, z + 0.030), "interior_wood_floor")
        for i in range(14):
            x = X0 + 0.48 + i * 0.21
            if x > X1 - 1.10:
                break
            m.cylinder((x, DEPTH - 0.26, z + 0.03), (x, DEPTH - 0.26, z + 0.29), 0.036,
                       ("paint_bottle_green", "paint_maroon", "paint_yellow")[(i + k) % 3], segments=6)
    m.box((X1 - 0.80, 0.30, 0.0), (X1 - 0.10, DEPTH - 0.50, 1.05), "interior_wood_floor")            # service end
    for k in range(2):
        m.cylinder((-0.60 + k * 1.40, bar_y - 0.35, 2.30), (-0.60 + k * 1.40, bar_y - 0.35, 3.30), 0.010, P.BLACK, segments=4)
        m.lathe([(0.0, 2.14), (0.150, 2.30)], 10, "lamp_warm", center=(-0.60 + k * 1.40, bar_y - 0.35), caps=(False, True))
    return m


_reg("bar", "Bar interior: dark brick, wood bar counter with foot rail and five stools, a mirrored back bar with three bottle "
             "shelves and low pendant lights.", _bar)


# --------------------------------------------------------------------------- nail / hair salon
def _nail_hair():
    m = _shell("interior_tile", "paint_white", lights=4)
    for k in range(4):                                                                     # manicure stations
        y = 0.50 + k * 0.52
        m.box((X0 + 0.20, y - 0.20, 0.66), (X0 + 1.20, y + 0.20, 0.72), "paint_white")
        _chair(m, X0 + 1.55, y, "paint_blue", 0.42)
        _chair(m, X0 + 0.32, y, "paint_white", 0.42)
    m.box((X1 - 0.06, 0.40, 0.90), (X1 - 0.03, DEPTH - 0.30, 2.30), "chrome")               # mirror wall
    for k in range(3):                                                                       # styling chairs
        y = 0.60 + k * 0.66
        m.cylinder((X1 - 0.95, y, 0.0), (X1 - 0.95, y, 0.10), 0.24, P.GALV, segments=10)
        m.cylinder((X1 - 0.95, y, 0.10), (X1 - 0.95, y, 0.48), 0.060, P.GALV, segments=8)
        m.box((X1 - 1.20, y - 0.26, 0.48), (X1 - 0.70, y + 0.26, 0.56), "paint_black")
        m.box((X1 - 0.72, y - 0.26, 0.56), (X1 - 0.62, y + 0.26, 1.10), "paint_black")
        m.box((X1 - 0.30, y - 0.30, 0.72), (X1 - 0.10, y + 0.30, 0.80), "paint_white")
    m.box((X0 + 0.40, DEPTH - 0.55, 0.0), (X0 + 1.90, DEPTH - 0.05, 0.95), "paint_white")    # reception desk
    m.box((X0 + 0.40, DEPTH - 0.10, 1.60), (X1 - 1.30, DEPTH - 0.05, 2.60), "paint_red")     # price board
    return m


_reg("nail_hair", "Nail salon / barber interior: tile floor, four manicure stations with client and technician chairs, a mirrored "
                   "wall with three styling chairs, a reception desk and a price board.", _nail_hair)


# --------------------------------------------------------------------------- laundromat
def _laundromat():
    m = _shell("interior_tile", "paint_white", lights=5)
    for k in range(6):                                                                       # front-load washers, left wall
        x = X0 + 0.15
        y = 0.35 + k * 0.34
        m.box((x, y, 0.0), (x + 0.70, y + 0.30, 0.92), "metal_panel")
        m.cylinder((x + 0.68, y + 0.15, 0.48), (x + 0.72, y + 0.15, 0.48), 0.115, P.GLASS, segments=10)
    for k in range(6):                                                                       # stacked dryers, right wall
        x = X1 - 0.85
        y = 0.35 + k * 0.34
        for z in (0.0, 1.00):
            m.box((x, y, z), (x + 0.70, y + 0.30, z + 0.95), "metal_panel")
            m.cylinder((x + 0.02, y + 0.15, z + 0.50), (x - 0.02, y + 0.15, z + 0.50), 0.120, P.GLASS, segments=10)
    m.box((-0.75, DEPTH - 1.20, 0.80), (0.75, DEPTH - 0.35, 0.88), "paint_white")             # folding table
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((sx * 0.68 - 0.025, DEPTH - 0.78 + sy * 0.38 - 0.025, 0.0), (sx * 0.68 + 0.025, DEPTH - 0.78 + sy * 0.38 + 0.025, 0.80), P.GALV)
    for k in range(4):                                                                        # plastic chairs
        _chair(m, -1.05 + k * 0.60, 0.42, "paint_blue", 0.42)
    m.box((0.95, DEPTH - 0.16, 0.60), (1.75, DEPTH - 0.06, 1.90), "metal_panel")              # change machine
    m.box((X0 + 0.30, DEPTH - 0.10, 2.20), (X1 - 0.30, DEPTH - 0.05, 2.80), "paint_yellow")   # price sign
    return m


_reg("laundromat", "Laundromat interior: six front-load washers down one wall, six stacked dryers down the other, a folding table "
                    "with chairs, a change machine and a price sign under bright fluorescents.", _laundromat)


# --------------------------------------------------------------------------- bank
def _bank():
    m = _shell("terrazzo", "limestone", lights=3)
    _counter(m, X0 + 0.35, X1 - 1.30, DEPTH - 0.95, 0.70, 1.10, "granite", "interior_wood_floor")   # teller line
    for k in range(3):                                                                                # teller screens and dividers
        x = X0 + 0.75 + k * 1.05
        m.box((x - 0.030, DEPTH - 0.95, 1.10), (x + 0.030, DEPTH - 0.25, 2.30), P.GLASS)
    m.box((X0 + 0.35, DEPTH - 1.00, 1.10), (X1 - 1.30, DEPTH - 0.96, 2.10), P.GLASS)                  # counter screen
    m.box((X0 + 0.35, DEPTH - 0.30, 0.0), (X1 - 1.30, DEPTH - 0.05, 2.60), "interior_wood_floor")     # back-office wall
    m.box((X1 - 1.15, DEPTH - 0.55, 0.0), (X1 - 0.15, DEPTH - 0.05, 2.20), "metal_panel")             # ATM surround
    m.box((X1 - 1.05, DEPTH - 0.58, 0.95), (X1 - 0.25, DEPTH - 0.54, 1.65), "paint_black")
    m.box((X1 - 0.95, DEPTH - 0.59, 1.30), (X1 - 0.35, DEPTH - 0.56, 1.60), "fluoro_white")
    for k in range(4):                                                                                 # queue stanchions
        x = X0 + 0.90 + k * 0.95
        m.cylinder((x, 0.85, 0.0), (x, 0.85, 0.98), 0.032, "chrome", segments=8)
        m.lathe([(0.145, 0.0), (0.145, 0.035)], 10, "chrome", center=(x, 0.85), caps=(False, True))
        if k:
            m.cylinder((x - 0.95, 0.85, 0.93), (x, 0.85, 0.93), 0.008, P.BLACK, segments=4)
    m.box((X0 + 0.60, 0.08, 1.30), (X1 - 1.60, 0.11, 2.30), "paint_blue")                              # window graphic
    return m


_reg("bank", "Bank branch interior: terrazzo floor, a granite teller line with glass screens, a back-office wall, an ATM alcove "
              "and a chrome queue barrier.", _bank)


# --------------------------------------------------------------------------- generic retail
def _generic_retail():
    m = _shell("interior_wood_floor", "paint_white", lights=4)
    for s in (-1, 1):
        _shelf_run(m, s * (WIDTH / 2 - 0.03), 0.40, DEPTH - 0.15, 0.30, 2.20, 5, "metal_panel", facing=-s)
    for k in range(2):                                                                        # centre display tables
        y = 0.75 + k * 0.90
        m.box((-0.75, y - 0.32, 0.0), (0.75, y + 0.32, 0.78), "interior_wood_floor")
        for i in range(4):
            m.box((-0.62 + i * 0.36, y - 0.22, 0.78), (-0.34 + i * 0.36, y + 0.22, 0.94),
                  ("paint_red", "paint_blue", "paint_cream", "paint_yellow")[i])
    _counter(m, 0.90, 2.20, DEPTH - 0.70, 0.60, 1.02, "interior_wood_floor", "paint_white")
    m.box((1.20, DEPTH - 0.60, 1.02), (1.55, DEPTH - 0.30, 1.30), "paint_black")               # till
    m.box((X0 + 0.40, DEPTH - 0.09, 1.90), (X1 - 1.40, DEPTH - 0.05, 2.70), "paint_black")     # brand board
    return m


_reg("generic_retail", "Generic retail interior: wall shelving both sides, two centre display tables with stock, a sales counter "
                        "with a till and a brand board.", _generic_retail)


# --------------------------------------------------------------------------- residential / office lobby
def _lobby():
    m = _shell("terrazzo", "limestone", lights=2, warm=True)
    m.box((X0 + 0.10, DEPTH - 0.14, 0.90), (X0 + 1.70, DEPTH - 0.06, 2.10), "bronze_anodized")     # mailboxes
    for r in range(5):
        for c in range(6):
            m.box((X0 + 0.14 + c * 0.255, DEPTH - 0.16, 0.94 + r * 0.23), (X0 + 0.36 + c * 0.255, DEPTH - 0.14, 1.14 + r * 0.23), "bronze_anodized")
    m.box((0.55, DEPTH - 0.16, 0.0), (2.15, DEPTH - 0.10, 2.55), "bronze_anodized")                 # elevator surround
    m.box((0.70, DEPTH - 0.20, 0.0), (2.00, DEPTH - 0.16, 2.30), "metal_panel")                     # elevator doors
    m.box((1.34, DEPTH - 0.21, 0.0), (1.36, DEPTH - 0.16, 2.30), "bronze_anodized")
    m.box((2.05, DEPTH - 0.20, 1.05), (2.14, DEPTH - 0.16, 1.35), "paint_black")                    # call panel
    m.box((X0 + 0.35, 0.55, 0.0), (X0 + 1.45, 1.15, 0.42), "paint_maroon")                          # bench
    m.box((X0 + 0.35, 1.09, 0.42), (X0 + 1.45, 1.15, 0.92), "paint_maroon")
    m.cylinder((-0.10, 0.85, 0.0), (-0.10, 0.85, 0.70), 0.28, "interior_wood_floor", segments=12)   # planter
    for k in range(9):
        a = 2 * math.pi * k / 9
        m.face([(-0.10, 0.85, 0.70), (-0.10 + 0.30 * math.cos(a), 0.85 + 0.30 * math.sin(a), 1.35),
                (-0.10 + 0.26 * math.cos(a + 0.7), 0.85 + 0.26 * math.sin(a + 0.7), 1.15)], "foliage_green")
    m.lathe([(0.0, 3.05), (0.34, 2.78), (0.30, 2.72)], 12, "lamp_warm", center=(0.0, DEPTH / 2), caps=(False, True))
    m.cylinder((0.0, DEPTH / 2, 3.05), (0.0, DEPTH / 2, HEIGHT), 0.012, P.BLACK, segments=4)
    return m


_reg("lobby", "Apartment / office lobby interior: terrazzo floor, limestone walls, a bronze mailbox bank, elevator doors with a "
               "call panel, a bench, a planter and a pendant fixture.", _lobby)


# --------------------------------------------------------------------------- vacant
def _vacant():
    m = _shell("concrete", "stucco", ceiling="concrete", lights=1)
    m.box((X0 + 0.60, DEPTH - 0.22, 0.0), (X0 + 1.35, DEPTH - 0.05, 2.05), "plywood_green")       # boarded rear door
    for k in range(4):                                                                             # abandoned shelving
        m.box((X1 - 0.55, 0.60, 0.30 + k * 0.42), (X1 - 0.06, DEPTH - 0.70, 0.34 + k * 0.42), "metal_panel")
    for s in (-1, 1):
        m.box((X1 - 0.55, 0.60 + (0 if s < 0 else DEPTH - 1.34), 0.0), (X1 - 0.50, 0.64 + (0 if s < 0 else DEPTH - 1.34), 2.05), "metal_panel")
    m.box((-1.85, 0.30, 0.0), (-1.20, 0.36, 2.40), "interior_wood_floor")                          # leaning ladder
    m.box((-1.30, 0.30, 0.0), (-1.24, 0.36, 2.40), "interior_wood_floor")
    for k in range(7):
        m.box((-1.85, 0.31, 0.20 + k * 0.32), (-1.24, 0.35, 0.24 + k * 0.32), "interior_wood_floor")
    rnd = P._lcg(99)
    for k in range(14):                                                                             # debris on the floor
        x = X0 + 0.4 + rnd() * (WIDTH - 0.8)
        y = 0.3 + rnd() * (DEPTH - 0.6)
        m.box((x, y, 0.0), (x + 0.10 + rnd() * 0.22, y + 0.08 + rnd() * 0.18, 0.02 + rnd() * 0.10), "paint_grey")
    m.box((X0 + 0.20, 0.05, 0.10), (X1 - 0.20, 0.08, 2.60), "plywood_green")                       # papered-over glass
    return m


_reg("vacant", "Vacant store interior: bare concrete, papered-over glass, a boarded rear door, abandoned shelving, a leaning "
                "ladder and floor debris.", _vacant)
