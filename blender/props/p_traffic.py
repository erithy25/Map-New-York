"""Traffic-control props: 12-inch three-section vehicle signals (mast-arm, pedestal, span-wire), the countdown
pedestrian signal and the accessible push-button station.

Dimensions follow the ITE/MUTCD polycarbonate signal section (12 in lens, 13.75 x 15.5 x 8 in body, 9.5 in tunnel
visor) and NYC DOT practice (dark-green housings, black louvred backplate with a retroreflective yellow border,
5.5 m signal standard carrying 6.1 m and 9.1 m mast arms).  MUTCD minimum vertical clearance to the bottom of a
head over a roadway is 15 ft (4.57 m); over a sidewalk a pedestal head sits at 8 ft (2.44 m).
"""
from __future__ import annotations

import math

import _core as C
import _legends as L
import _palette as P

IN = 0.0254
SEC_W, SEC_H, SEC_D = 13.75 * IN, 15.5 * IN, 8.0 * IN      # 0.349 x 0.394 x 0.203 m
LENS_D = 12.0 * IN                                          # 0.305 m
VISOR_L = 9.5 * IN                                          # 0.241 m
BACKPLATE_BORDER = 5.0 * IN                                 # 0.127 m
HEAD_H = 3 * SEC_H                                          # 1.181 m
LENS_COLORS = (("RED", "#D8342B"), ("YELLOW", "#F2B01E"), ("GREEN", "#1FA84A"))


def _visor(name: str, cx: float, cz: float, y_front: float, *, r: float = 0.168, length: float = VISOR_L,
           material=None, segments: int = 16) -> "C.bpy.types.Object":
    """Tunnel visor: an open-bottomed cylindrical hood in front of one lens, drooping 30 mm at the open end."""
    bm, uv = C._new_bm()
    a0, a1 = math.radians(-18.0), math.radians(198.0)
    ring_back, ring_front = [], []
    for i in range(segments + 1):
        a = a0 + (a1 - a0) * i / segments
        x, z = cx + r * math.cos(a), cz + r * math.sin(a)
        ring_back.append(bm.verts.new((x, y_front, z)))
        ring_front.append(bm.verts.new((x, y_front + length, z - 0.030)))
    for i in range(segments):
        f = bm.faces.new((ring_back[i], ring_back[i + 1], ring_front[i + 1], ring_front[i]))
        f.smooth = True
        for loop, t in zip(f.loops, ((i / segments, 0.0), ((i + 1) / segments, 0.0), ((i + 1) / segments, 1.0), (i / segments, 1.0))):
            loop[uv].uv = t
    bm.normal_update()
    ob = C.bm_object(name, bm, [material] if material else ())
    ob.data.materials[0].use_backface_culling = False
    return ob


def signal_head(z_bottom: float, *, x: float = 0.0, y: float = 0.0, name: str = "head", backplate: bool = True,
                lens_on: int | None = None) -> list:
    """Three-section 12 in vehicle signal facing +Y: dark-green housing, tunnel visors, louvred backplate with a
    retroreflective yellow border. ``lens_on`` (0 red, 1 yellow, 2 green) lights one lens for the verification render."""
    green = P.signal_green()
    black = P.black_matte()
    yellow = C.mat_solid("retro_yellow_border", C.MUTCD["yellow"], 0.35)
    parts = []
    for i, (cname, hexc) in enumerate(LENS_COLORS):
        zc = z_bottom + HEAD_H - SEC_H * (i + 0.5)          # red on top
        body = C.box(f"{name}_sec{i}", (SEC_W, SEC_D, SEC_H), origin=(x, y, zc), material=green, anchor="center", bevel=0.012)
        door = C.box(f"{name}_door{i}", (SEC_W * 0.92, 0.022, SEC_H * 0.90), origin=(x, y + SEC_D / 2, zc), material=green, anchor="center")
        strength = 9.0 if (lens_on is not None and lens_on == i) else 0.25
        lens_mat = C.mat_emissive(f"LED_{cname}", hexc, strength, base=hexc)
        lens = C.lathe(f"{name}_lens{i}", [(0.0, 0.0), (LENS_D * 0.30, 0.004), (LENS_D * 0.46, 0.011), (LENS_D * 0.50, 0.016)],
                       20, material=lens_mat, axis="Y", origin=(x, y + SEC_D / 2 + 0.010, zc))
        parts += [body, door, lens, _visor(f"{name}_visor{i}", x, zc, y + SEC_D / 2 + 0.012, material=black)]
    if backplate:
        bw, bh = SEC_W + 2 * BACKPLATE_BORDER, HEAD_H + 2 * BACKPLATE_BORDER
        zc = z_bottom + HEAD_H / 2
        yb = y + SEC_D / 2 + 0.014
        for sx, sz, w, h in ((0, (HEAD_H + BACKPLATE_BORDER) / 2, bw, BACKPLATE_BORDER),
                             (0, -(HEAD_H + BACKPLATE_BORDER) / 2, bw, BACKPLATE_BORDER),
                             ((SEC_W + BACKPLATE_BORDER) / 2, 0, BACKPLATE_BORDER, HEAD_H),
                             (-(SEC_W + BACKPLATE_BORDER) / 2, 0, BACKPLATE_BORDER, HEAD_H)):
            parts.append(C.box(f"{name}_bp{sx:.2f}{sz:.2f}", (w, 0.006, h), origin=(x + sx, yb, zc + sz), material=black, anchor="center"))
        strip = 0.055
        for sx, sz, w, h in ((0, bh / 2 - strip / 2, bw, strip), (0, -(bh / 2 - strip / 2), bw, strip),
                             (bw / 2 - strip / 2, 0, strip, bh), (-(bw / 2 - strip / 2), 0, strip, bh)):
            parts.append(C.box(f"{name}_bpy{sx:.2f}{sz:.2f}", (w, 0.004, h), origin=(x + sx, yb + 0.005, zc + sz),
                               material=yellow, anchor="center"))
    return parts


def _signal_pole(height: float, *, dia_base: float = 0.244, dia_top: float = 0.168, material=None) -> list:
    """NYC signal standard: tapered round steel shaft on a bolted base with a cast shroud and a hand hole."""
    galv = material or P.black_steel()
    shroud = C.lathe("pole_shroud", [(0.235, 0.0), (0.235, 0.10), (0.185, 0.18), (0.150, 0.34)], 20, material=galv)
    shaft = C.lathe("pole", [(dia_base / 2, 0.30), (dia_top / 2, height)], 20, material=galv, smooth=True)
    hand = C.box("pole_handhole", (0.10, 0.11, 0.28), origin=(0.0, -0.075, 0.85), material=P.dark_grey(), anchor="bottom")
    cap = C.lathe("pole_cap", [(dia_top / 2 + 0.008, 0.0), (dia_top / 2 + 0.008, 0.02), (dia_top / 2 * 0.6, 0.055), (0.0, 0.07)],
                  20, material=galv, origin=(0, 0, height))
    return [shroud, shaft, hand, cap]


# ------------------------------------------------------------------------------------------------- builders
def _mast_arm(length: float, n_heads: int) -> C.Built:
    steel = P.black_steel()
    parts = _signal_pole(5.50, material=steel)
    # the arm leaves the 5.5 m standard just under its cap and rises over the span so the lowest head keeps the
    # MUTCD 15 ft (4.57 m) clearance over the roadway
    z0, z1 = 5.45, 6.30
    pts = C.bezier_points([(0.10, 0.0, z0), (length * 0.45, 0.0, z1 + 0.16), (length, 0.0, z1)], 14)
    radii = [0.105 - 0.042 * (i / 13) for i in range(14)]
    parts.append(C.tube("mast_arm", pts, radii, 14, material=steel))
    parts.append(C.box("arm_flange", (0.05, 0.30, 0.42), origin=(0.13, 0.0, z0), material=steel, anchor="center"))
    heads_x = [length * f for f in ((0.46, 0.88) if n_heads == 2 else (0.34, 0.62, 0.90))][:n_heads]
    for i, hx in enumerate(heads_x):
        t = hx / length
        za = z0 + (z1 - z0) * (3 * t ** 2 - 2 * t ** 3) + 0.16 * 4 * t * (1 - t)
        parts.append(C.box(f"hanger{i}", (0.09, 0.09, 0.07), origin=(hx, 0.0, za - 0.07), material=steel, anchor="bottom"))
        parts += signal_head(za - 0.07 - HEAD_H, x=hx, name=f"head{i}", lens_on=(0 if i == 0 else None))
    return C.Built(lod0=parts, extra={"key_dims_m": {"pole_height": 5.50, "arm_length": length, "heads": n_heads,
                                                     "lowest_head_bottom": round(min(
                                                         z0 + (z1 - z0) * (3 * (hx / length) ** 2 - 2 * (hx / length) ** 3)
                                                         + 0.16 * 4 * (hx / length) * (1 - hx / length) - 0.07 - HEAD_H
                                                         for hx in heads_x), 2),
                                                     "mutcd_min_clearance": 4.57},
                                      "arm_direction_blender": "+X", "facing_blender": "+Y"})


def build_mastarm_6m() -> C.Built:
    return _mast_arm(6.10, 2)


def build_mastarm_9m() -> C.Built:
    return _mast_arm(9.14, 3)


def build_pedestal() -> C.Built:
    """Pedestal-mounted vehicle signal on a sidewalk: 4.5 in pipe on a cast base, head bottom at 8 ft (2.44 m)."""
    steel = P.black_steel()
    base = C.lathe("ped_base", [(0.175, 0.0), (0.175, 0.09), (0.140, 0.16), (0.100, 0.30), (0.075, 0.36)], 20, material=steel)
    shaft = C.cyl("shaft", 0.0572, 2.55, 16, origin=(0, 0, 0.34), material=steel)
    z_bottom = 2.60
    head = signal_head(z_bottom, name="head", lens_on=2)
    cap = C.box("head_mount", (0.10, 0.13, 0.16), origin=(0.0, -SEC_D / 2 - 0.05, z_bottom + HEAD_H - 0.05), material=steel, anchor="center")
    return C.Built(lod0=[base, shaft, cap] + head,
                   extra={"key_dims_m": {"head_bottom": z_bottom, "head_top": round(z_bottom + HEAD_H, 3), "shaft_dia": 0.114}})


def build_spanwire() -> C.Built:
    """Span-wire installation: one 8.2 m pole, the catenary and tether wires and a suspended three-section head.
    The wire stubs are 6.5 m long so the engine can chain identical assemblies across an intersection."""
    steel = P.black_steel()
    wire = C.mat_solid("span_wire", "#4A4C4E", 0.5, 0.7)
    parts = _signal_pole(8.20, dia_base=0.290, dia_top=0.180, material=steel)
    span = 6.50
    cat = [(0.14 + (span - 0.14) * t, 0.0, 7.55 - 0.50 * t - 0.55 * 4 * t * (1 - t)) for t in [i / 11 for i in range(12)]]
    tet = [(0.14 + (span - 0.14) * t, 0.0, 5.55 - 0.35 * t - 0.30 * 4 * t * (1 - t)) for t in [i / 11 for i in range(12)]]
    parts.append(C.tube("catenary", cat, 0.011, 6, material=wire))
    parts.append(C.tube("tether", tet, 0.008, 6, material=wire))
    for z in (7.55, 5.55):
        parts.append(C.box("wire_clamp%d" % int(z * 10), (0.10, 0.10, 0.10), origin=(0.10, 0.0, z), material=steel, anchor="center"))
    hx = 4.30
    t = (hx - 0.14) / (span - 0.14)
    z_cat = 7.55 - 0.50 * t - 0.55 * 4 * t * (1 - t)
    z_top = z_cat - 0.42
    parts.append(C.tube("hanger", [(hx, 0.0, z_cat), (hx, 0.0, z_top)], 0.020, 8, material=steel))
    parts.append(C.lathe("balance_adjuster", [(0.055, 0.0), (0.075, 0.04), (0.075, 0.14), (0.050, 0.18)], 12,
                         material=steel, origin=(hx, 0.0, z_top - 0.18)))
    parts += signal_head(z_top - 0.18 - HEAD_H, x=hx, name="head", lens_on=0)
    return C.Built(lod0=parts, extra={"key_dims_m": {"pole_height": 8.20, "span_stub": span,
                                                     "head_bottom": round(z_top - 0.18 - HEAD_H, 2)},
                                      "wire_direction_blender": "+X"})


def build_ped_countdown() -> C.Built:
    """NYC countdown pedestrian signal: 16 x 18 in one-section head, hand/man module beside a two-digit countdown."""
    steel = P.black_steel()
    green = P.signal_green()
    black = P.black_matte()
    w, h, d = 16 * IN, 18 * IN, 8 * IN
    z_bottom = 2.44
    zc = z_bottom + h / 2
    base = C.lathe("ped_base", [(0.150, 0.0), (0.150, 0.08), (0.120, 0.15), (0.075, 0.28), (0.060, 0.32)], 16, material=steel)
    shaft = C.cyl("shaft", 0.0508, 2.63, 14, origin=(0, 0, 0.30), material=steel)
    body = C.box("head", (w, d, h), origin=(0.0, d / 2 + 0.055, zc), material=green, anchor="center", bevel=0.012)
    face = C.box("faceplate", (w * 0.94, 0.014, h * 0.92), origin=(0.0, d + 0.055, zc), material=black, anchor="center")
    yf = d + 0.055 + 0.010
    sym = C.mat_image("PED_SYMBOL", L.ped_symbol("hand"), emission_strength=6.0, roughness=0.6)
    cnt = C.mat_image("PED_COUNTDOWN", L.ped_countdown(12), emission_strength=6.0, roughness=0.6)
    sym_q = C.sign_blank("ped_symbol", "rect", w * 0.50, h * 0.66, face_material=sym, back_material=black,
                         center=(w * 0.20, yf, zc), thickness=0.004)
    cnt_q = C.sign_blank("ped_countdown", "rect", w * 0.30, h * 0.60, face_material=cnt, back_material=black,
                         center=(-w * 0.28, yf, zc), thickness=0.004)
    visor = C.box("ped_visor_top", (w, 0.20, 0.020), origin=(0.0, d + 0.14, zc + h / 2 - 0.01), material=black, anchor="center")
    side_l = C.box("ped_visor_l", (0.018, 0.20, h), origin=(-w / 2 + 0.009, d + 0.14, zc), material=black, anchor="center")
    side_r = C.box("ped_visor_r", (0.018, 0.20, h), origin=(w / 2 - 0.009, d + 0.14, zc), material=black, anchor="center")
    bracket = C.box("bracket", (0.10, 0.12, 0.22), origin=(0.0, 0.035, zc + h / 2 - 0.11), material=steel, anchor="center")
    cap = C.lathe("shaft_cap", [(0.058, 0.0), (0.058, 0.02), (0.030, 0.05), (0.0, 0.06)], 14, material=steel, origin=(0, 0, 2.93))
    return C.Built(lod0=[base, shaft, body, face, sym_q, cnt_q, visor, side_l, side_r, bracket, cap],
                   extra={"key_dims_m": {"head_bottom": z_bottom, "head_size": [round(w, 3), round(h, 3)],
                                         "symbol_slot": "PED_SYMBOL", "countdown_slot": "PED_COUNTDOWN"}})


def build_pushbutton() -> C.Built:
    """Accessible pedestrian signal push-button station: 2 in button at 42 in (1.07 m), R10-3e instruction sign."""
    steel = P.black_steel()
    box_mat = P.dark_grey()
    pole = C.cyl("pole", 0.032, 1.62, 12, material=steel)
    base = C.lathe("base", [(0.075, 0.0), (0.075, 0.05), (0.045, 0.12)], 12, material=steel)
    housing = C.box("housing", (0.135, 0.105, 0.300), origin=(0.0, 0.062, 1.07), material=box_mat, anchor="center", bevel=0.008)
    face = C.box("faceplate", (0.115, 0.012, 0.270), origin=(0.0, 0.118, 1.07), material=P.black_matte(), anchor="center")
    btn = C.lathe("button", [(0.0, 0.0), (0.020, 0.004), (0.0254, 0.012), (0.0254, 0.018)], 16, material=P.silver_paint(),
                  axis="Y", origin=(0.0, 0.124, 1.10))
    led = C.lathe("locator_led", [(0.0, 0.0), (0.009, 0.004), (0.011, 0.008)], 10,
                  material=C.mat_emissive("LED_APS", "#F2B01E", 4.0), axis="Y", origin=(0.0, 0.126, 1.005))
    sign = C.sign_blank("r10_3e", "rect", 0.229, 0.305, face_material=C.mat_sign_face(L.push_button_r10_3e()),
                        back_material=P.aluminium(), center=(0.0, 0.045, 1.44), thickness=0.002)
    band = C.torus("sign_band", 0.038, 0.006, 12, 5, origin=(0.0, 0.0, 1.44), material=steel, axis="Z")
    return C.Built(lod0=[pole, base, housing, face, btn, led, sign, band],
                   extra={"key_dims_m": {"button_height": 1.07, "sign": "MUTCD R10-3e", "sign_size": [0.229, 0.305]}})


SPECS = [
    C.PropSpec("signal_mastarm_6m", "traffic", "traffic_signal", build_mastarm_6m, (6.34, 0.59, 6.37),
               "NYC DOT mast-arm traffic signal: 5.5 m tapered signal standard with a 20 ft (6.10 m) mast arm carrying "
               "two three-section 12 in heads in dark-green housings with tunnel visors and yellow-bordered backplates. "
               "ITE/MUTCD 12 in section 13.75 x 15.5 x 8 in; MUTCD 15 ft minimum clearance over the roadway.",
               variants=["signal_mastarm_9m", "signal_pedestal", "signal_spanwire"], tags=["mutcd", "mast_arm"], tolerance=0.10),
    C.PropSpec("signal_mastarm_9m", "traffic", "traffic_signal", build_mastarm_9m, (9.38, 0.59, 6.37),
               "As signal_mastarm_6m but with a 30 ft (9.14 m) mast arm carrying three heads — the NYC configuration for "
               "wide two-way avenues.",
               variants=["signal_mastarm_6m", "signal_pedestal", "signal_spanwire"], tags=["mutcd", "mast_arm"], tolerance=0.10),
    C.PropSpec("signal_pedestal", "traffic", "traffic_signal", build_pedestal, (0.60, 0.57, 3.91),
               "Pedestal-mounted three-section signal on a 4.5 in pipe standard with a cast base; head bottom at the "
               "8 ft (2.44 m) sidewalk clearance of the MUTCD.",
               variants=["signal_mastarm_6m", "signal_spanwire"], tags=["mutcd", "pedestal"], tolerance=0.10),
    C.PropSpec("signal_spanwire", "traffic", "traffic_signal", build_spanwire, (6.74, 0.59, 8.27),
               "Span-wire signal: 8.2 m pole with catenary and tether wires and one suspended three-section head on a "
               "balance adjuster — the older NYC intersection type still common outside Manhattan. 6.5 m wire stubs "
               "let the engine chain assemblies pole to pole.",
               variants=["signal_mastarm_6m", "signal_pedestal"], tags=["mutcd", "span_wire"], tolerance=0.10),
    C.PropSpec("signal_ped_countdown", "traffic", "pedestrian_signal", build_ped_countdown, (0.41, 0.59, 2.99),
               "NYC countdown pedestrian signal: one-section 16 x 18 in head with the MUTCD upraised-hand / walking-person "
               "module (PED_SYMBOL) beside a two-digit countdown (PED_COUNTDOWN), both runtime-swappable emissive slots; "
               "head bottom at the 8 ft (2.44 m) clearance.",
               variants=["ped_pushbutton"], tags=["mutcd", "countdown"], tolerance=0.10),
    C.PropSpec("ped_pushbutton", "traffic", "ped_pushbutton", build_pushbutton, (0.23, 0.22, 1.62),
               "Accessible pedestrian signal push-button station: 2 in button with a locator LED at the PROWAG 42 in "
               "(1.07 m) height and the MUTCD R10-3e instruction sign on a 1.6 m post.",
               variants=["signal_ped_countdown"], tags=["mutcd", "aps"], tolerance=0.12),
]
