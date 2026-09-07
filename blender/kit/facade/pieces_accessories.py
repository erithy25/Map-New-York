"""Window accessories: through-the-window air conditioners and their brackets, HPD child window guards, security
grilles, flower boxes, curtains, blinds, roller shades, interior cards and a wall satellite dish (15 pieces).

Origin: bottom-centre of the accessory on the wall plane (y = 0). Accessories that hang outside the wall occupy
negative y; the ones that sit behind the glass occupy positive y and are placed by the facade assembler at the
window's sash depth.
"""
from __future__ import annotations

import math

import kitlib as K
import pieces_common as P

# real through-the-window AC cabinet sizes (W x D x H, metres) from 5 000 / 8 000 / 18 000 BTU units
AC_SIZES = {
    "small":  (0.470, 0.400, 0.355, 0.265),    # 5 000 BTU; last value = projection past the wall face
    "medium": (0.560, 0.525, 0.400, 0.345),    # 8 000 BTU
    "large":  (0.660, 0.640, 0.430, 0.435),    # 18 000-24 000 BTU
}


def _ac(m: K.Mesh, size: str, *, bracket: bool = True) -> None:
    w, d, h, out = AC_SIZES[size]
    x0, x1 = -w / 2, w / 2
    y0, y1 = -out, d - out
    m.box((x0, y0, 0.0), (x1, y1, h), P.ALU, mats={"y": P.ALU})
    # louvred condenser face and side vents
    for k in range(7):
        z = 0.030 + k * (h - 0.070) / 7
        m.box((x0 + 0.020, y0 - 0.008, z), (x1 - 0.020, y0 + 0.004, z + (h - 0.070) / 7 * 0.55), P.BLACK)
    for s in (-1, 1):
        for k in range(4):
            z = 0.050 + k * (h - 0.110) / 4
            m.box((s * (w / 2) - 0.006 * s, y0 + 0.05, z), (s * (w / 2) + 0.004 * s, y0 + d * 0.45, z + 0.030), P.BLACK)
    m.box((x0 + 0.03, y0 + 0.02, h), (x1 - 0.03, y1 - 0.02, h + 0.012), P.ALU)      # top pan lip
    if bracket:
        _ac_bracket(m, w, out)


def _ac_bracket(m: K.Mesh, w: float, out: float) -> None:
    """Steel window-AC support bracket: two angle arms and a diagonal strut back to the wall."""
    for s in (-1, 1):
        x = s * (w / 2 - 0.055)
        m.box((x - 0.018, -out - 0.02, -0.048), (x + 0.018, 0.02, -0.012), P.GALV)              # arm
        P._bar(m, K.Vector((x, -out + 0.02, -0.040)), K.Vector((x, 0.03, -0.330)),
               K.Vector((1.0, 0.0, 0.0)), 0.030, 0.014, P.GALV)                                  # diagonal strut
        m.box((x - 0.030, 0.0, -0.360), (x + 0.030, 0.030, -0.300), P.GALV)                      # wall plate


@K.register("acc_ac_window_small", "window_accessory", anchor="wall_sill_centre", nominal_size=(0.478, 0.42, 0.727),
            description="5 000 BTU through-the-window air conditioner (0.47 x 0.40 x 0.355 m) with its steel support bracket.",
            features=["ac_units"])
def _acc_ac_small():
    m = K.Mesh()
    _ac(m, "small")
    return m


@K.register("acc_ac_window_medium", "window_accessory", anchor="wall_sill_centre", nominal_size=(0.568, 0.545, 0.772),
            description="8 000 BTU through-the-window air conditioner (0.56 x 0.525 x 0.40 m) with its steel support bracket.",
            features=["ac_units"])
def _acc_ac_medium():
    m = K.Mesh()
    _ac(m, "medium")
    return m


@K.register("acc_ac_window_large", "window_accessory", anchor="wall_sill_centre", nominal_size=(0.668, 0.66, 0.802),
            description="18 000-24 000 BTU through-the-window air conditioner (0.66 x 0.64 x 0.43 m) with its steel support bracket.",
            features=["ac_units"])
def _acc_ac_large():
    m = K.Mesh()
    _ac(m, "large")
    return m


@K.register("acc_ac_bracket", "window_accessory", anchor="wall_sill_centre", nominal_size=(0.51, 0.405, 0.348),
            description="Galvanised window-AC support bracket on its own (two angle arms, diagonal struts and wall plates).",
            features=["ac_units"])
def _acc_ac_bracket():
    m = K.Mesh()
    _ac_bracket(m, 0.560, 0.345)
    return m


@K.register("acc_through_wall_ac_unit", "window_accessory", nominal_size=(0.654, 0.314, 0.417),
            description="Outdoor half of a through-wall 'Fedders' AC in its sleeve: stamped aluminium grille and drip lip.",
            features=["through_wall_ac"])
def _acc_thru_ac():
    m = K.Mesh()
    w, h, out = 0.630, 0.395, 0.280
    m.box((-w / 2, -out, 0.0), (w / 2, 0.02, h), P.ALU)
    for k in range(8):
        z = 0.025 + k * (h - 0.050) / 8
        m.box((-w / 2 + 0.025, -out - 0.010, z), (w / 2 - 0.025, -out + 0.004, z + (h - 0.050) / 8 * 0.6), P.BLACK)
    m.box((-w / 2 - 0.012, -out - 0.014, -0.022), (w / 2 + 0.012, -out + 0.10, 0.0), P.ALU)     # drip lip
    return m


@K.register("acc_window_guard_child", "window_accessory", nominal_size=(1.03, 0.079, 0.66),
            description="HPD-mandated child window guard: 0.66 m high steel frame with horizontal bars at 4.5 in and jamb brackets.",
            features=[])
def _acc_guard_child():
    m = K.Mesh()
    w, h = 0.990, 0.660
    x0, x1 = -w / 2, w / 2
    y = -0.055
    m.frame(x0, x1, 0.0, h, y - 0.012, y + 0.012, 0.024, P.BLACK)
    for k in range(1, 6):                                              # 114 mm (4.5 in) bar spacing
        z = h * k / 6
        m.box((x0, y - 0.008, z - 0.008), (x1, y + 0.008, z + 0.008), P.BLACK)
    for xx in (x0, x1):                                                # jamb mounting plates
        m.box((xx - 0.020, y - 0.014, 0.05), (xx + 0.020, 0.010, 0.13), P.BLACK)
        m.box((xx - 0.020, y - 0.014, h - 0.13), (xx + 0.020, 0.010, h - 0.05), P.BLACK)
    return m


@K.register("acc_window_guard_security", "window_accessory", nominal_size=(1.01, 0.044, 1.76),
            description="Full-height welded security grille over a 0.95 x 1.70 m opening: 12 mm square bars on 150 mm centres "
                        "with a hinged egress leaf.",
            features=[])
def _acc_guard_security():
    m = K.Mesh()
    w, h = 1.010, 1.760
    x0, x1 = -w / 2, w / 2
    y = -0.070
    m.frame(x0, x1, 0.0, h, y - 0.016, y + 0.016, 0.032, P.BLACK)
    m.bar_grid(x0 + 0.032, x1 - 0.032, 0.032, h - 0.032, y, 5, 10, 0.014, 0.014, P.BLACK)
    for zz in (0.30, h - 0.30):                                        # hinge barrels of the egress leaf
        m.cylinder((x0 + 0.02, y, zz - 0.05), (x0 + 0.02, y, zz + 0.05), 0.018, P.BLACK, segments=6)
    m.box((x1 - 0.16, y - 0.028, h / 2 - 0.06), (x1 - 0.05, y + 0.010, h / 2 + 0.06), P.BLACK)   # latch box
    return m


@K.register("acc_flower_box", "window_accessory", anchor="wall_sill_centre", nominal_size=(1.003, 0.373, 0.594),
            description="Painted-wood window flower box on brackets with soil and planting (geranium / ivy mass).",
            features=[])
def _acc_flower_box():
    m = K.Mesh()
    w, d, h = 0.900, 0.230, 0.210
    x0, x1 = -w / 2, w / 2
    y0, y1 = -d, -0.010
    m.box((x0, y0, 0.0), (x1, y1, h), P.SASH_WHITE, faces="yxXz")
    m.box((x0 + 0.018, y0 + 0.018, h - 0.030), (x1 - 0.018, y1 - 0.018, h - 0.012), "soil")
    for s in (-1, 1):                                                        # brackets
        x = s * (w / 2 - 0.09)
        P._bar(m, K.Vector((x, y0 + 0.03, -0.005)), K.Vector((x, -0.005, -0.185)), K.Vector((1.0, 0.0, 0.0)), 0.030, 0.014, P.BLACK)
    rnd = P._lcg(7)
    for k in range(26):                                                       # foliage: crossed leaf cards
        cx = x0 + 0.05 + rnd() * (w - 0.10)
        cy = y0 + 0.04 + rnd() * (d - 0.08)
        r = 0.070 + rnd() * 0.070
        a = rnd() * math.pi
        for aa in (a, a + math.pi / 2):
            dx, dy = r * math.cos(aa), r * math.sin(aa)
            m.face([(cx - dx, cy - dy, h - 0.02), (cx + dx, cy + dy, h - 0.02),
                    (cx + dx, cy + dy, h - 0.02 + r * 1.5), (cx - dx, cy - dy, h - 0.02 + r * 1.5)],
                   "foliage_green" if k % 5 else "paint_red")
    return m


def _curtain(m: K.Mesh, w: float, h: float, y: float, mat: str, folds: int, amp: float, open_frac: float) -> None:
    """Gathered curtain panel(s) hanging on a rod: a corrugated strip per panel."""
    m.cylinder((-w / 2 - 0.03, y, h + 0.03), (w / 2 + 0.03, y, h + 0.03), 0.010, P.ALU, segments=6)
    panels = [(-w / 2, -w / 2 + w * open_frac / 2), (w / 2 - w * open_frac / 2, w / 2)] if open_frac < 1.0 else [(-w / 2, w / 2)]
    for (a, b) in panels:
        n = max(2, int(folds * (b - a) / w))
        for i in range(n):
            xa = a + (b - a) * i / n
            xb = a + (b - a) * (i + 1) / n
            ya = y + amp * (1 if i % 2 else -1)
            yb = y + amp * (1 if (i + 1) % 2 else -1)
            m.face([(xa, ya, 0.0), (xb, yb, 0.0), (xb, yb, h), (xa, ya, h)], mat, uvs=[(0, 0), (0.3, 0), (0.3, h), (0, h)])
            m.face([(xa, ya, 0.0), (xa, ya, h), (xb, yb, h), (xb, yb, 0.0)], mat, uvs=[(0, 0), (0, h), (0.3, h), (0.3, 0)])


@K.register("acc_curtains_open", "window_accessory", nominal_size=(0.96, 0.044, 1.539),
            description="Pair of gathered curtains drawn open to the jambs, hanging behind the sash on a rod.",
            features=[])
def _acc_curtains_open():
    m = K.Mesh()
    _curtain(m, 0.900, 1.500, 0.040, "paint_cream", 14, 0.022, 0.34)
    return m


@K.register("acc_curtains_closed", "window_accessory", nominal_size=(0.96, 0.04, 1.539),
            description="Curtains drawn closed across the whole opening (blocks the interior card).",
            features=[])
def _acc_curtains_closed():
    m = K.Mesh()
    _curtain(m, 0.900, 1.500, 0.040, "paint_cream", 18, 0.020, 1.0)
    return m


@K.register("acc_blinds_half", "window_accessory", anchor="wall_head_centre", nominal_size=(0.89, 0.045, 0.731),
            description="Venetian blind at half drop, hung from the window head: 25 mm aluminium slats, head rail, bottom rail and cords.",
            features=[])
def _acc_blinds_half():
    m = K.Mesh()
    w = 0.890
    x0, x1 = -w / 2, w / 2
    m.box((x0, 0.010, -0.045), (x1, 0.055, 0.0), P.ALU)                   # head rail at the opening head
    n = 22
    for k in range(n):
        z = -0.060 - k * 0.031
        m.box((x0 + 0.005, 0.014, z - 0.004), (x1 - 0.005, 0.050, z + 0.004), P.ALU)
    z_bot = -0.060 - (n - 1) * 0.031
    m.box((x0 + 0.005, 0.012, z_bot - 0.020), (x1 - 0.005, 0.052, z_bot - 0.004), P.ALU)   # bottom rail
    for s in (-1, 1):
        m.cylinder((s * (w / 2 - 0.09), 0.032, z_bot - 0.02), (s * (w / 2 - 0.09), 0.032, -0.045), 0.003, "paint_cream", segments=4)
    return m


@K.register("acc_roller_shade", "window_accessory", anchor="wall_head_centre", nominal_size=(0.92, 0.056, 1.003),
            description="Spring roller shade pulled two-thirds down, hung from the window head, with roller, hem bar and ring pull.",
            features=[])
def _acc_roller_shade():
    m = K.Mesh()
    w, drop = 0.880, 0.930
    x0, x1 = -w / 2, w / 2
    m.cylinder((x0 - 0.02, 0.038, -0.030), (x1 + 0.02, 0.038, -0.030), 0.028, "paint_cream", segments=8)
    m.box((x0, 0.030, -drop), (x1, 0.034, -0.030), "paint_cream", faces="yY")
    m.box((x0, 0.024, -drop - 0.022), (x1, 0.042, -drop), "paint_cream")            # hem bar
    m.cylinder((0.0, 0.033, -drop - 0.075), (0.0, 0.033, -drop - 0.022), 0.004, "paint_cream", segments=4)
    return m


@K.register("acc_interior_card_lit", "window_accessory", nominal_size=(1.3, 0.31, 2.0),
            description="Lit interior room box (emissive room image on the back wall, dark returns) for use behind any window opening up to 1.3 x 2.0 m; 0.30 m deep so the pane gets parallax and no daylight leaks in from behind the shell.",
            features=[], budget=40)
def _acc_card_lit():
    m = K.Mesh()
    P.interior_card(m, -0.65, 0.65, 0.0, 2.00, 0.010, True)
    m.face([(-0.65, 0.0, 0.0), (-0.65, 0.0, 2.00), (0.65, 0.0, 2.00), (0.65, 0.0, 0.0)], "paint_black")
    return m


@K.register("acc_interior_card_unlit", "window_accessory", nominal_size=(1.3, 0.31, 2.0),
            description="Unlit interior room box (dim room image on the back wall, dark returns) for use behind any window opening up to 1.3 x 2.0 m; 0.30 m deep so the pane gets parallax and no daylight leaks in from behind the shell.",
            features=[], budget=40)
def _acc_card_unlit():
    m = K.Mesh()
    P.interior_card(m, -0.65, 0.65, 0.0, 2.00, 0.010, False)
    m.face([(-0.65, 0.0, 0.0), (-0.65, 0.0, 2.00), (0.65, 0.0, 2.00), (0.65, 0.0, 0.0)], "paint_black")
    return m


@K.register("acc_satellite_dish", "window_accessory", nominal_size=(0.46, 0.595, 0.85),
            description="0.46 m Ku-band satellite dish on a J-mount lag-bolted to the jamb or fire-escape rail; "
                        "offset-fed dish facing the street.",
            features=[])
def _acc_satellite_dish():
    m = K.Mesh()
    R, depth = 0.230, 0.085
    cz = 0.62                                    # dish centre height above the wall plate
    rings, spokes = 4, 12

    def pt(ir: int, ia: int):
        r = R * ir / rings
        a = 2 * math.pi * ia / spokes
        return (r * math.cos(a), depth * (r / R) ** 2, cz + r * math.sin(a))

    for ir in range(rings):
        for ia in range(spokes):
            a0, a1 = ia, (ia + 1) % spokes
            if ir == 0:
                m.face([pt(0, 0), pt(1, a1), pt(1, a0)], P.ALU, smooth=True)              # centre fan
            else:
                m.face([pt(ir, a0), pt(ir, a1), pt(ir + 1, a1), pt(ir + 1, a0)], P.ALU, smooth=True)
    m.box((-0.040, depth, cz - 0.040), (0.040, depth + 0.055, cz + 0.040), P.BLACK)       # hub casting
    P._bar(m, K.Vector((0.0, depth + 0.05, cz)), K.Vector((0.0, 0.31, 0.30)), K.Vector((1.0, 0.0, 0.0)), 0.034, 0.026, P.BLACK)
    m.box((-0.022, 0.29, 0.030), (0.022, 0.334, 0.32), P.BLACK)                            # mast
    m.box((-0.060, 0.27, 0.0), (0.060, 0.36, 0.030), P.BLACK)                              # wall plate
    m.cylinder((0.0, -0.20, cz - 0.19), (0.0, -0.055, cz - 0.075), 0.024, P.ALU, segments=8)   # feed arm + LNB
    m.box((-0.030, -0.235, cz - 0.235), (0.030, -0.175, cz - 0.155), P.ALU)
    return m
