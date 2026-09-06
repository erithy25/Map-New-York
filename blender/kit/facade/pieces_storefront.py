"""Storefront pieces: infill bays in the three NYC bay widths, roll-down gates in three states, scissor security
grilles, awnings and a projecting sign (19 pieces).

Ground-floor geometry follows normal New York shopfront practice: 0.55 m bulkhead, 2.35 m plate glass, a transom
bar at 2.90 m, 0.50 m transom lights and a 0.80 m sign fascia, all inside a 4.20 m storey.  The glass line is
recessed 0.25 m behind the pilaster face (y = 0 is the building face, +Y into the shop).

Bays are hollow: pair each with a ``storefront_interior_*`` shell (2.50 m deep) from ``pieces_interiors``.
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P
import facade_params as fp

H_TOTAL = 4.200
Z_BULK = 0.550          # top of the bulkhead / bottom of the plate glass
Z_TRANSOM = 2.900       # transom bar
Z_SIGN = 3.400          # bottom of the sign fascia
GLASS_Y = 0.250         # glass line behind the pilaster face
PIL_W = 0.220           # storefront pilaster width
PIL_P = 0.150           # pilaster projection past the glass line (towards the street)
DOOR_W = 0.965
RECESS = 0.380          # depth of the recessed entrance vestibule


def _bay(width: float, *, door_side: int = 1) -> K.Mesh:
    """One storefront bay: pilasters, bulkhead, plate glass, recessed entrance, transom and sign fascia."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    gy = GLASS_Y
    # --- flanking pilasters (cast iron), full storey height
    for s in (-1, 1):
        xc = s * (width / 2 - PIL_W / 2)
        m.box((xc - PIL_W / 2, -PIL_P, 0.0), (xc + PIL_W / 2, gy + 0.05, H_TOTAL), P.IRON)
        m.box((xc - PIL_W / 2 - 0.030, -PIL_P - 0.030, 0.0), (xc + PIL_W / 2 + 0.030, gy, 0.230), P.IRON)          # plinth
        m.box((xc - PIL_W / 2 - 0.030, -PIL_P - 0.030, Z_SIGN - 0.12), (xc + PIL_W / 2 + 0.030, gy, Z_SIGN), P.IRON)  # capital
    ix0, ix1 = x0 + PIL_W, x1 - PIL_W        # clear opening between pilasters
    # --- entrance recess (door bay pushed back), placed at one end of the bay
    dx_c = door_side * (ix1 - PIL_W / 2 - DOOR_W / 2 - 0.10) if door_side > 0 else door_side * (abs(ix0) - PIL_W / 2 - DOOR_W / 2 - 0.10)
    dx0, dx1 = dx_c - DOOR_W / 2 - 0.11, dx_c + DOOR_W / 2 + 0.11
    ry = gy + RECESS
    m.face([(dx0, ry, 0.0), (dx1, ry, 0.0), (dx1, ry, 0.06), (dx0, ry, 0.06)], "granite")
    m.box((dx0, gy, 0.0), (dx1, ry, 0.030), "granite")                                                   # recess floor
    m.box((dx0 - 0.02, gy, Z_TRANSOM), (dx1 + 0.02, ry, Z_TRANSOM + 0.10), P.ALU)                        # recess head
    for s, xr in ((-1, dx0), (1, dx1)):                                                                   # recess returns
        m.face([(xr, gy, 0.0), (xr, ry, 0.0), (xr, ry, Z_TRANSOM), (xr, gy, Z_TRANSOM)], "granite", flip=(s > 0))
    # door in the recess
    m.frame(dx_c - DOOR_W / 2, dx_c + DOOR_W / 2, 0.0, 2.180, ry - 0.055, ry, 0.058, P.ALU)
    m.glass_pane(dx_c - DOOR_W / 2 + 0.058, dx_c + DOOR_W / 2 - 0.058, 0.058, 2.122, ry - 0.028, P.GLASS)
    m.cylinder((dx_c + DOOR_W / 2 - 0.13, ry - 0.085, 0.90), (dx_c + DOOR_W / 2 - 0.13, ry - 0.085, 1.35), 0.018, "chrome", segments=8)
    m.box((dx_c - DOOR_W / 2, ry - 0.058, 2.180), (dx_c + DOOR_W / 2, ry, Z_TRANSOM), P.ALU, faces="yYxX")
    m.glass_pane(dx_c - DOOR_W / 2 + 0.03, dx_c + DOOR_W / 2 - 0.03, 2.240, Z_TRANSOM - 0.05, ry - 0.028, P.GLASS)
    # --- display windows either side of the recess
    spans = [(ix0, dx0), (dx1, ix1)]
    for (sx0, sx1) in spans:
        if sx1 - sx0 < 0.30:
            continue
        m.box((sx0, gy - 0.045, 0.0), (sx1, gy + 0.045, Z_BULK), "interior_wood_floor")                   # bulkhead
        m.box((sx0, gy - 0.060, Z_BULK - 0.045), (sx1, gy + 0.060, Z_BULK), P.ALU)                        # bulkhead cap
        panels = max(1, int(round((sx1 - sx0) / 1.50)))
        for k in range(panels + 1):                                                                       # mullions
            xm = sx0 + (sx1 - sx0) * k / panels
            w = 0.045 if 0 < k < panels else 0.055
            m.box((xm - w / 2, gy - 0.035, Z_BULK), (xm + w / 2, gy + 0.035, Z_TRANSOM + 0.10), P.ALU)
        m.glass_pane(sx0, sx1, Z_BULK, Z_TRANSOM, gy, P.GLASS, 0.010)
        m.box((sx0, gy - 0.035, Z_TRANSOM), (sx1, gy + 0.035, Z_TRANSOM + 0.10), P.ALU)                   # transom bar
        m.glass_pane(sx0, sx1, Z_TRANSOM + 0.10, Z_SIGN - 0.02, gy, P.GLASS, 0.010)
    # --- sign fascia and its lintel
    m.box((x0, -0.075, Z_SIGN), (x1, gy + 0.10, H_TOTAL - 0.10), "metal_panel")
    m.box((x0 - 0.03, -0.115, H_TOTAL - 0.10), (x1 + 0.03, gy + 0.10, H_TOTAL), "metal_panel")            # fascia cap
    m.box((x0 + 0.03, -0.090, Z_SIGN + 0.08), (x1 - 0.03, -0.076, H_TOTAL - 0.18), "paint_darkgreen")      # sign panel
    for k in range(max(2, int(width / 1.4))):                                                              # gooseneck sign lights
        cx = x0 + width * (k + 0.5) / max(2, int(width / 1.4))
        m.cylinder((cx, -0.09, H_TOTAL - 0.06), (cx, -0.34, H_TOTAL - 0.06), 0.016, P.BLACK, segments=6)
        m.cylinder((cx, -0.34, H_TOTAL - 0.06), (cx, -0.34, H_TOTAL - 0.20), 0.016, P.BLACK, segments=6)
        m.lathe([(0.0, H_TOTAL - 0.30), (0.105, H_TOTAL - 0.20)], 8, P.BLACK, center=(cx, -0.34), caps=(False, True))
    # --- steel lintel over the whole opening
    m.box((x0, -0.115, H_TOTAL), (x1, gy + 0.10, H_TOTAL + 0.14), P.GALV)
    return m


def _bay_lod(width: float) -> K.Mesh:
    """Explicit LOD1 for a bay: the five horizontal bands and two pilasters as flat quads (collapse decimation cannot
    reduce a mesh of separate closed boxes below four triangles each)."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    gy = GLASS_Y
    for s in (-1, 1):
        xc = s * (width / 2 - PIL_W / 2)
        m.box((xc - PIL_W / 2, -PIL_P, 0.0), (xc + PIL_W / 2, gy, H_TOTAL), P.IRON, faces="yxX")
    ix0, ix1 = x0 + PIL_W, x1 - PIL_W
    m.box((ix0, gy - 0.045, 0.0), (ix1, gy + 0.045, Z_BULK), "interior_wood_floor", faces="yZ")
    m.glass_pane(ix0, ix1, Z_BULK, Z_TRANSOM, gy, P.GLASS)
    m.box((ix0, gy - 0.035, Z_TRANSOM), (ix1, gy + 0.035, Z_TRANSOM + 0.10), P.ALU, faces="yY")
    m.glass_pane(ix0, ix1, Z_TRANSOM + 0.10, Z_SIGN, gy, P.GLASS)
    m.box((x0, -0.075, Z_SIGN), (x1, gy + 0.10, H_TOTAL), "metal_panel", faces="yZ")
    return m


def _reg_bay(width: float) -> None:
    key = f"{width:.1f}".replace(".", "")
    tag = f"{width:.1f} m"

    @K.register(f"storefront_bay_{key}", "storefront", nominal_size=(width + 0.06, 1.075, 4.34),
                description=f"{tag} storefront bay: cast-iron pilasters, wood bulkhead, plate glass, recessed entrance with a "
                            f"glazed aluminium door, transom lights, sign fascia with gooseneck lights and a steel lintel. "
                            f"Pair with a storefront_interior_* shell.",
                features=["storefront"], budget=6000,
                lod1=lambda _w=width: _bay_lod(_w),
                extra={"bay_width_m": width, "interior_depth_m": 2.5, "glass_line_y_m": GLASS_Y,
                       "band_heights_m": {"bulkhead": Z_BULK, "transom": Z_TRANSOM, "sign": Z_SIGN, "total": H_TOTAL}})
    def _b(_w=width):
        return _bay(_w)


for _w in fp.STOREFRONT_BAY_WIDTHS_M:
    _reg_bay(_w)


# --------------------------------------------------------------------------- roll-down gates
def _roll_gate(width: float, state: str) -> K.Mesh:
    """Corrugated roll-down security gate in front of a bay: guides, hood box and the curtain at three drops."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    gy = -0.055                    # the gate hangs just outside the pilaster face
    top = Z_SIGN - 0.02
    drop = {"closed": 0.0, "half": 1.75, "open": top - 0.10}[state]
    for s in (-1, 1):              # guide channels
        xc = s * (width / 2 - 0.055)
        m.box((xc - 0.045, gy - 0.075, 0.0), (xc + 0.045, gy + 0.055, top + 0.10), P.GALV)
    if drop < top - 0.15:
        m.box((x0 + 0.055, gy - 0.030, drop + 0.075), (x1 - 0.055, gy + 0.010, top), "corrugated_metal")
        n = max(1, int((top - drop) / 0.075))
        for k in range(n):
            z = drop + 0.075 + k * 0.075
            m.box((x0 + 0.055, gy - 0.042, z - 0.006), (x1 - 0.055, gy - 0.028, z + 0.006), P.GALV)
        m.box((x0 + 0.045, gy - 0.048, drop), (x1 - 0.045, gy + 0.018, drop + 0.075), P.BLACK)   # bottom bar
        for s in (-1, 1):                                                                        # lock hasps
            m.box((s * (width / 2 - 0.30) - 0.045, gy - 0.070, drop + 0.010), (s * (width / 2 - 0.30) + 0.045, gy - 0.040, drop + 0.065), P.BLACK)
    coil_r = 0.115 + 0.115 * (1.0 - (top - drop) / max(top, 1e-3))
    m.box((x0 - 0.03, gy - 0.28, top), (x1 + 0.03, gy + 0.075, top + 0.42), P.GALV)               # hood box
    m.cylinder((x0 + 0.06, gy - 0.10, top + 0.21), (x1 - 0.06, gy - 0.10, top + 0.21), coil_r, P.GALV, segments=10)
    return m


def _reg_gate(width: float, state: str) -> None:
    key = f"{width:.1f}".replace(".", "")
    label = {"closed": "fully closed", "half": "half raised (1.75 m)", "open": "rolled up in the hood"}[state]

    @K.register(f"storefront_gate_{key}_{state}", "storefront",
                nominal_size=(width + 0.06, 0.453 if state == "open" else 0.355, 3.806 if state == "open" else 3.80),
                description=f"Corrugated roll-down security gate for the {width:.1f} m storefront bay, {label}: steel guide "
                            f"channels, slat curtain, bottom bar with lock hasps and the coil hood.",
                features=["roll_gate"], budget=6000,
                extra={"bay_width_m": width, "gate_state": state})
    def _g(_w=width, _s=state):
        return _roll_gate(_w, _s)


for _w in fp.STOREFRONT_BAY_WIDTHS_M:
    for _s in fp.STOREFRONT_GATE_STATES:
        _reg_gate(_w, _s)


# --------------------------------------------------------------------------- scissor security grille
def _grille(width: float) -> K.Mesh:
    """Folding scissor gate across the display window: a pantograph lattice between top and bottom tracks."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    gy = -0.030
    z0, z1 = 0.030, Z_TRANSOM - 0.03
    m.box((x0, gy - 0.030, z1), (x1, gy + 0.030, z1 + 0.055), P.GALV)                 # head track
    m.box((x0, gy - 0.030, z0 - 0.045), (x1, gy + 0.030, z0), P.GALV)                 # floor track
    cells = max(4, int(round(width / 0.42)))
    pitch = (x1 - x0) / cells
    rows = 5
    dz = (z1 - z0) / rows
    for c in range(cells):
        for r in range(rows):
            ax, az = x0 + c * pitch, z0 + r * dz
            P._bar(m, K.Vector((ax, gy - 0.012, az)), K.Vector((ax + pitch, gy - 0.012, az + dz)),
                   K.Vector((0.0, 1.0, 0.0)), 0.024, 0.010, P.BLACK)
            P._bar(m, K.Vector((ax, gy + 0.012, az + dz)), K.Vector((ax + pitch, gy + 0.012, az)),
                   K.Vector((0.0, 1.0, 0.0)), 0.024, 0.010, P.BLACK)
    for c in range(cells + 1):                                                         # vertical stiles
        xm = x0 + c * pitch
        m.box((xm - 0.014, gy - 0.020, z0), (xm + 0.014, gy + 0.020, z1), P.BLACK)
    return m


def _grille_lod(width: float) -> K.Mesh:
    """Explicit LOD1 for the scissor grille: a coarse lattice of flat quads instead of solid bars."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    gy, z0, z1 = -0.030, 0.030, Z_TRANSOM - 0.03
    cells = max(2, int(round(width / 0.85)))
    pitch = (x1 - x0) / cells
    rows = 2
    dz = (z1 - z0) / rows
    for c in range(cells):
        for r in range(rows):
            ax, az = x0 + c * pitch, z0 + r * dz
            m.face([(ax, gy, az - 0.012), (ax + pitch, gy, az + dz - 0.012),
                    (ax + pitch, gy, az + dz + 0.012), (ax, gy, az + 0.012)], P.BLACK)
            m.face([(ax, gy, az + dz - 0.012), (ax, gy, az + dz + 0.012),
                    (ax + pitch, gy, az + 0.012), (ax + pitch, gy, az - 0.012)], P.BLACK)
    for c in range(cells + 1):
        xm = x0 + c * pitch
        m.face([(xm - 0.014, gy, z0), (xm + 0.014, gy, z0), (xm + 0.014, gy, z1), (xm - 0.014, gy, z1)], P.BLACK)
    return m


def _reg_grille(width: float) -> None:
    key = f"{width:.1f}".replace(".", "")

    @K.register(f"storefront_grille_{key}", "storefront", nominal_size=(width + 0.028, 0.06, 2.94),
                description=f"Folding scissor security grille for the {width:.1f} m storefront bay: pantograph lattice of 24 mm "
                            f"flat bar between head and floor tracks (drawn closed).",
                features=["roll_gate"], budget=6000, extra={"bay_width_m": width},
                lod1=lambda _w=width: _grille_lod(_w))
    def _gr(_w=width):
        return _grille(_w)


for _w in fp.STOREFRONT_BAY_WIDTHS_M:
    _reg_grille(_w)


# --------------------------------------------------------------------------- awnings
def _awning(width: float) -> K.Mesh:
    """Fixed canvas box awning over the transom: aluminium tube frame, sloped cover, valance and end cheeks."""
    m = K.Mesh()
    x0, x1 = -width / 2, width / 2
    proj = 1.220                       # 4 ft projection, the NYC DOT limit for a sidewalk awning
    z_back, z_front = Z_SIGN - 0.05, Z_TRANSOM - 0.10
    val = 0.300
    m.face([(x0, 0.0, z_back), (x0, -proj, z_front), (x1, -proj, z_front), (x1, 0.0, z_back)], "fabric_awning",
           uvs=[(0, 0), (0, proj), (width, proj), (width, 0)])
    m.face([(x0, 0.0, z_back - 0.02), (x1, 0.0, z_back - 0.02), (x1, -proj, z_front - 0.02), (x0, -proj, z_front - 0.02)],
           "fabric_awning", uvs=[(0, 0), (width, 0), (width, proj), (0, proj)])
    for s in (-1, 1):                  # end cheeks
        m.face([(s * width / 2, 0.0, z_back), (s * width / 2, -proj, z_front),
                (s * width / 2, -proj, z_front - val), (s * width / 2, 0.0, z_back - val)], "fabric_awning", flip=(s < 0))
    m.box((x0, -proj - 0.02, z_front - val), (x1, -proj + 0.02, z_front), "fabric_awning")     # scalloped valance
    for k in range(max(2, int(width / 0.75))):                                                  # scallop notches
        cx = x0 + width * (k + 0.5) / max(2, int(width / 0.75))
        m.box((cx - 0.055, -proj - 0.030, z_front - val - 0.075), (cx + 0.055, -proj + 0.030, z_front - val + 0.010), "fabric_awning")
    m.cylinder((x0, -proj + 0.02, z_front), (x1, -proj + 0.02, z_front), 0.020, P.ALU, segments=6)  # front tube
    for s in (-1, 1):                                                                               # side arms
        x = s * (width / 2 - 0.06)
        m.cylinder((x, 0.02, z_back), (x, -proj + 0.02, z_front), 0.018, P.ALU, segments=6)
        m.cylinder((x, 0.02, z_back - val), (x, -proj + 0.02, z_front - val), 0.014, P.ALU, segments=6)
    m.box((x0 - 0.02, -0.02, z_back - val - 0.02), (x1 + 0.02, 0.03, z_back + 0.04), P.ALU)         # wall angle
    return m


def _reg_awning(width: float) -> None:
    key = f"{width:.1f}".replace(".", "")

    @K.register(f"storefront_awning_{key}", "storefront", nominal_size=(width + 0.04, 1.28, 0.965),
                description=f"Fixed canvas box awning for the {width:.1f} m storefront bay: 1.22 m projection, aluminium tube "
                            f"frame, sloped cover and a 0.30 m scalloped valance. Shares the bay's sidewalk-level frame.",
                features=["awning"], budget=6000, extra={"bay_width_m": width, "projection_m": 1.22})
    def _aw(_w=width):
        mm = _awning(_w)
        return mm


for _w in fp.STOREFRONT_BAY_WIDTHS_M:
    _reg_awning(_w)


# --------------------------------------------------------------------------- projecting sign
@K.register("storefront_sign_projecting", "storefront", nominal_size=(0.11, 1.157, 0.95),
            description="Double-faced projecting shop sign on a wrought-iron bracket: 0.90 x 0.60 m panel, 1.05 m from the wall, "
                        "with a strip light over it.",
            features=["storefront"], budget=800)
def _proj_sign():
    m = K.Mesh()
    m.box((-0.030, -1.100, 0.170), (0.030, -0.140, 0.770), "paint_darkgreen")            # sign panel
    m.box((-0.040, -1.115, 0.150), (0.040, -0.125, 0.190), "metal_panel")                 # bottom rail
    m.box((-0.040, -1.115, 0.750), (0.040, -0.125, 0.790), "metal_panel")                 # top rail
    m.box((-0.045, -0.075, 0.0), (0.045, 0.030, 0.950), P.BLACK)                          # wall standard
    P._bar(m, K.Vector((0.0, -0.055, 0.900)), K.Vector((0.0, -1.120, 0.900)), K.Vector((1.0, 0.0, 0.0)), 0.040, 0.020, P.BLACK)
    P._bar(m, K.Vector((0.0, -0.055, 0.230)), K.Vector((0.0, -1.060, 0.870)), K.Vector((1.0, 0.0, 0.0)), 0.026, 0.016, P.BLACK)
    m.cylinder((0.0, -1.115, 0.900), (0.0, -1.115, 0.790), 0.014, P.BLACK, segments=6)     # hanger
    m.cylinder((0.0, -0.145, 0.900), (0.0, -0.145, 0.790), 0.014, P.BLACK, segments=6)
    m.box((-0.055, -0.980, 0.860), (0.055, -0.260, 0.900), "fluoro_white")                 # strip light
    return m
