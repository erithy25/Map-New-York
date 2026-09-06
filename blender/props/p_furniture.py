"""NYC sidewalk furniture: hydrant, litter baskets, mailbox, standpipe, LinkNYC, bollard, planter, bench,
tree-pit guard and grate, vent grate, manhole covers, steam stacks, Muni-Meter, fire alarm box, refuse piles
and the three food carts.

Reference dimensions are the published or measured standards named in each ``PropSpec.notes``: DSNY basket and
Better Bin, USPS collection box, LinkNYC Link1.0 (9 ft 6 in), NYC Parks World's Fair bench, DOT tree-pit guard,
24 in manhole cover, Con Edison steam vent tube, Parkeon Strada Muni-Meter.
"""
from __future__ import annotations

import math
import random

import _core as C
import _legends as L
import _palette as P

IN = 0.0254


def _wire_ring(name, radius, z, *, minor=0.005, segments=28, material=None):
    return C.torus(name, radius, minor, segments, 5, origin=(0, 0, z), material=material)


def umbrella(name: str, radius: float, z_top: float, droop: float, n_gores: int, mats: list) -> list:
    """Vendor-cart umbrella: alternating coloured gores on a radial frame (Sabrett-style hot-dog cart canopy)."""
    bm, uv = C._new_bm()
    apex = bm.verts.new((0.0, 0.0, z_top))
    rim = [bm.verts.new((radius * math.cos(C.TAU * k / n_gores), radius * math.sin(C.TAU * k / n_gores), z_top - droop))
           for k in range(n_gores)]
    mid = [bm.verts.new((radius * 0.52 * math.cos(C.TAU * (k + 0.5) / n_gores), radius * 0.52 * math.sin(C.TAU * (k + 0.5) / n_gores),
                         z_top - droop * 0.22)) for k in range(n_gores)]
    for k in range(n_gores):
        k2 = (k + 1) % n_gores
        for tri, uvs in (((apex, rim[k], mid[k]), ((0.5, 1.0), (0.0, 0.0), (0.5, 0.3))),
                         ((apex, mid[k], rim[k2]), ((0.5, 1.0), (0.5, 0.3), (1.0, 0.0)))):
            f = bm.faces.new(tri)
            f.material_index = k % len(mats)
            f.smooth = True
            for loop, t in zip(f.loops, uvs):
                loop[uv].uv = t
    bm.normal_update()
    canopy = C.bm_object(name, bm, mats)
    for m in canopy.data.materials:
        m.use_backface_culling = False
    return [canopy]


# ------------------------------------------------------------------------------------------------- builders
def build_hydrant() -> C.Built:
    """FDNY/DEP fire hydrant ("johnny pump"): 0.75 m above grade, 4.5 in steamer facing the street, two 2.5 in
    side outlets, pentagon operating nut."""
    red = P.fdny_red()
    brass = P.brass()
    flange = C.lathe("flange", [(0.150, 0.0), (0.150, 0.045), (0.118, 0.065), (0.112, 0.10)], 20, material=red)
    barrel = C.lathe("barrel", [(0.098, 0.10), (0.092, 0.44), (0.104, 0.47)], 20, material=red, smooth=True)
    bonnet = C.lathe("bonnet", [(0.104, 0.47), (0.124, 0.50), (0.120, 0.56), (0.100, 0.63), (0.062, 0.685), (0.030, 0.705)],
                     20, material=red, smooth=True)
    nut = C.lathe("operating_nut", [(0.0, 0.0), (0.032, 0.004), (0.032, 0.042), (0.0, 0.046)], 5, material=red, origin=(0, 0, 0.705))
    parts = [flange, barrel, bonnet, nut]
    # 4.5 in steamer facing +Y, two 2.5 in outlets on the sides
    parts.append(C.lathe("steamer", [(0.086, 0.0), (0.086, 0.030), (0.072, 0.038), (0.070, 0.075)], 16,
                         material=red, axis="Y", origin=(0.0, 0.086, 0.415)))
    parts.append(C.lathe("steamer_cap", [(0.070, 0.0), (0.072, 0.012), (0.062, 0.040), (0.030, 0.050)], 16,
                         material=brass, axis="Y", origin=(0.0, 0.158, 0.415)))
    for sgn in (-1.0, 1.0):
        parts.append(C.lathe(f"outlet{int(sgn)}", [(0.060, 0.0), (0.060, 0.026), (0.050, 0.034), (0.048, 0.062)], 14,
                             material=red, axis="X" if sgn > 0 else "-X", origin=(sgn * 0.082, 0.0, 0.345)))
        parts.append(C.lathe(f"outlet_cap{int(sgn)}", [(0.048, 0.0), (0.050, 0.010), (0.042, 0.032), (0.020, 0.040)], 14,
                             material=brass, axis="X" if sgn > 0 else "-X", origin=(sgn * 0.142, 0.0, 0.345)))
    return C.Built(lod0=parts, extra={"key_dims_m": {"height_above_grade": 0.75, "barrel_dia": 0.196,
                                                     "steamer_outlet_in": 4.5, "side_outlets_in": 2.5},
                                      "paint_variants": ["FDNY red (modelled)", "DEP silver with a coloured bonnet"]})


def build_wire_basket() -> C.Built:
    """DSNY green wire-mesh litter basket: 24 in dia x 31 in, rolled rim, 24 vertical wires on five hoops."""
    green = P.green_paint()
    r_top, r_bot, h = 0.305, 0.262, 0.787
    parts = [_wire_ring("rim", r_top, h, minor=0.010, material=green)]
    for k, z in enumerate((0.06, 0.24, 0.42, 0.60)):
        t = z / h
        parts.append(_wire_ring(f"hoop{k}", r_bot + (r_top - r_bot) * t, z, material=green))
    n = 24
    for k in range(n):
        a = C.TAU * k / n
        parts.append(C.tube(f"wire{k}", [(r_bot * math.cos(a), r_bot * math.sin(a), 0.03),
                                         (r_top * math.cos(a), r_top * math.sin(a), h)], 0.0045, 5, material=green))
    parts.append(C.cyl("bottom", r_bot, 0.012, 24, origin=(0, 0, 0.018), material=green))
    for k in range(3):
        a = C.TAU * k / 3 + 0.4
        parts.append(C.cyl(f"foot{k}", 0.012, 0.03, 6, origin=(r_bot * 0.8 * math.cos(a), r_bot * 0.8 * math.sin(a), 0.0), material=green))
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"top_dia": 0.610, "height": 0.787, "wires": n}})


def build_better_bin() -> C.Built:
    """DSNY "Better Bin" (2022 replacement basket): perforated steel body, sloped hood with a single throw opening."""
    body_mat = C.mat_solid("betterbin_grey", "#3D4A44", 0.5, 0.35)
    dark = P.black_matte()
    base = C.lathe("base", [(0.310, 0.0), (0.310, 0.035), (0.292, 0.055)], 24, material=body_mat)
    body = C.lathe("body", [(0.292, 0.055), (0.300, 0.14), (0.300, 0.70), (0.292, 0.76)], 24, material=body_mat, smooth=True)
    hood = C.lathe("hood", [(0.292, 0.76), (0.305, 0.79), (0.290, 0.86), (0.215, 0.925), (0.140, 0.945)], 24,
                   material=body_mat, smooth=True)
    lid = C.lathe("lid", [(0.140, 0.945), (0.120, 0.952)], 24, material=body_mat)
    mouth = C.box("throw_opening", (0.34, 0.16, 0.20), origin=(0.0, 0.235, 0.735), material=dark, anchor="bottom")
    lip = C.box("mouth_lip", (0.36, 0.05, 0.03), origin=(0.0, 0.245, 0.935), material=body_mat, anchor="center")
    # perforation band (the bin's visible pattern), modelled as three recessed rings
    rings = [C.torus(f"perf{k}", 0.302, 0.006, 26, 4, origin=(0, 0, 0.22 + 0.20 * k), material=dark) for k in range(3)]
    return C.Built(lod0=[base, body, hood, lid, mouth, lip] + rings,
                   extra={"key_dims_m": {"dia": 0.61, "height": 0.95, "opening_w": 0.34}})


def build_mailbox() -> C.Built:
    """USPS street collection box: 50 in tall, curved hood, pull-down hopper door, four legs."""
    blue = P.usps_blue()
    dark = P.dark_grey()
    w, d = 0.470, 0.500
    legs = [C.box(f"leg{i}", (0.055, 0.055, 0.25), origin=(sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), 0.0),
                  material=dark, anchor="bottom")
            for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1)))]
    skirt = C.box("skirt", (w, d, 0.06), origin=(0, 0, 0.22), material=blue, anchor="bottom")
    body = C.box("body", (w, d, 0.75), origin=(0, 0, 0.27), material=blue, anchor="bottom", bevel=0.02)
    hood = C.lathe("hood", [(0.0, -d / 2), (d * 0.30, -d * 0.42), (d * 0.46, -d * 0.16), (d * 0.50, 0.0),
                            (d * 0.46, d * 0.16), (d * 0.30, d * 0.42), (0.0, d / 2)], 16, material=blue,
                   axis="X", origin=(0.0, 0.0, 1.02), smooth=True)
    hood.data.transform(C.Matrix.Scale(w / d, 4, C.Vector((1, 0, 0))))
    door = C.box("hopper_door", (w * 0.80, 0.075, 0.31), origin=(0.0, d / 2 + 0.010, 0.72), material=blue, anchor="center", bevel=0.012)
    handle = C.cyl("handle", 0.016, w * 0.52, 10, origin=(-w * 0.26, d / 2 + 0.085, 0.615), material=dark, axis="X")
    plate = C.box("usps_plate", (w * 0.62, 0.006, 0.10), origin=(0.0, d / 2 + 0.004, 0.98), material=dark, anchor="center")
    return C.Built(lod0=legs + [skirt, body, hood, door, handle, plate],
                   extra={"key_dims_m": {"height": 1.27, "width": 0.470, "depth_with_hopper": 0.61}})


def build_standpipe() -> C.Built:
    """Fire-department siamese standpipe connection: two 2.5 in inlets with brass caps on a freestanding riser."""
    galv = P.galv()
    brass = P.brass()
    plate = C.box("floor_plate", (0.30, 0.24, 0.020), material=galv, anchor="bottom")
    riser = C.cyl("riser", 0.058, 0.66, 16, origin=(0, 0, 0.02), material=galv)
    body = C.lathe("wye_body", [(0.058, 0.0), (0.080, 0.05), (0.086, 0.16), (0.070, 0.22)], 16, material=galv, origin=(0, 0, 0.68))
    parts = [plate, riser, body]
    for sgn in (-1.0, 1.0):
        p0 = C.Vector((0.0, 0.0, 0.84))
        p1 = C.Vector((sgn * 0.085, 0.060, 0.905))
        p2 = C.Vector((sgn * 0.118, 0.135, 0.935))
        parts.append(C.tube(f"inlet{int(sgn)}", [p0, p1, p2], [0.052, 0.046, 0.044], 12, material=galv))
        parts.append(C.lathe(f"swivel{int(sgn)}", [(0.052, 0.0), (0.056, 0.018), (0.050, 0.030)], 12, material=brass,
                             origin=(sgn * 0.118, 0.135, 0.935)))
        cap = C.lathe(f"cap{int(sgn)}", [(0.050, 0.0), (0.052, 0.012), (0.044, 0.038), (0.020, 0.048)], 12, material=brass)
        C.rotate(cap, -45.0, "X")
        C.rotate(cap, -20.0 * sgn, "Z")
        C.move(cap, sgn * 0.126, 0.152, 0.948)
        parts.append(cap)
    parts.append(C.sign_blank("id_plate", "rect", 0.18, 0.075, thickness=0.003,
                              face_material=C.mat_solid("standpipe_plate", "#B08D57", 0.35, 1.0),
                              back_material=galv, center=(0.0, 0.062, 0.60)))
    return C.Built(lod0=parts, extra={"key_dims_m": {"inlet_size_in": 2.5, "inlet_height": 0.99, "riser_dia": 0.116}})


def build_linknyc() -> C.Built:
    """LinkNYC Link1.0 kiosk: 9 ft 6 in (2.90 m) x 31 in (0.79 m) x 11 in (0.28 m) slab with a portrait 55 in
    display on each broad face, a tablet, and the vented head."""
    shell = P.brushed()
    dark = P.black_matte()
    screen = C.mat_image("SCREEN_EMISSIVE", L.linknyc_screen(), emission_strength=3.5, roughness=0.25)
    w, d, h = 0.790, 0.285, 2.90
    plinth = C.box("plinth", (w + 0.03, d + 0.03, 0.075), material=dark, anchor="bottom")
    body = C.box("body", (w, d, h - 0.075), origin=(0, 0, 0.075), material=shell, anchor="bottom", bevel=0.03)
    head = C.box("head_vents", (w * 0.96, d * 0.9, 0.30), origin=(0, 0, h - 0.34), material=dark, anchor="bottom")
    parts = [plinth, body, head]
    sw, sh = 0.685, 1.218
    for sgn, facing in ((1.0, "+Y"), (-1.0, "-Y")):
        bezel = C.box(f"bezel{int(sgn)}", (sw + 0.045, 0.012, sh + 0.045), origin=(0.0, sgn * (d / 2 + 0.004), 1.75),
                      material=dark, anchor="center")
        panel = C.sign_blank(f"screen{int(sgn)}", "rect", sw, sh, thickness=0.004, face_material=screen,
                             back_material=dark, center=(0.0, sgn * (d / 2 + 0.012), 1.75), facing=facing)
        parts += [bezel, panel]
    tablet = C.box("tablet", (0.235, 0.030, 0.320), origin=(0.0, d / 2 + 0.012, 1.02), material=dark, anchor="center", bevel=0.006)
    glassm = C.mat_emissive("SCREEN_TABLET", "#5A7FB0", 1.5, base="#141820")
    tablet_face = C.box("tablet_face", (0.205, 0.008, 0.285), origin=(0.0, d / 2 + 0.030, 1.02), material=glassm, anchor="center")
    keypad = C.box("keypad", (0.16, 0.022, 0.10), origin=(0.0, d / 2 + 0.010, 0.79), material=dark, anchor="center")
    port = C.box("usb_ports", (0.12, 0.018, 0.05), origin=(0.0, d / 2 + 0.008, 0.66), material=dark, anchor="center")
    return C.Built(lod0=parts + [tablet, tablet_face, keypad, port],
                   extra={"key_dims_m": {"height": 2.90, "width": 0.790, "depth": 0.285,
                                         "display_in": 55, "display_size": [sw, sh]},
                          "screen_slots": ["SCREEN_EMISSIVE"]})


def build_bollard() -> C.Built:
    """Sidewalk security bollard: 8 in (0.219 m) schedule-40 steel pipe, 0.90 m above grade, domed cap."""
    steel = P.black_steel()
    collar = C.lathe("collar", [(0.140, 0.0), (0.140, 0.035), (0.112, 0.055)], 20, material=steel)
    pipe = C.lathe("pipe", [(0.1095, 0.05), (0.1095, 0.845), (0.104, 0.875), (0.078, 0.90), (0.0, 0.918)], 20,
                   material=steel, smooth=True)
    band = C.torus("reflective_band", 0.112, 0.006, 20, 4, origin=(0, 0, 0.78), material=P.white_paint())
    return C.Built(lod0=[collar, pipe, band], extra={"key_dims_m": {"height": 0.90, "pipe_od": 0.219}})


def build_planter() -> C.Built:
    """Cast concrete street planter (BID / DOT plaza type): 1.05 m top diameter, 0.75 m tall, soil at 0.62 m."""
    conc = P.concrete_rough()
    soil = P.soil()
    outer = C.lathe("outer", [(0.425, 0.0), (0.440, 0.05), (0.470, 0.60), (0.525, 0.70), (0.525, 0.75)], 28,
                    material=conc, smooth=False)
    lip = C.lathe("inner", [(0.470, 0.75), (0.462, 0.70), (0.420, 0.62)], 28, material=conc)
    fill = C.cyl("soil", 0.424, 0.02, 28, origin=(0, 0, 0.60), material=soil)
    return C.Built(lod0=[outer, lip, fill], extra={"key_dims_m": {"top_dia": 1.05, "height": 0.75, "soil_level": 0.62}})


def build_bench() -> C.Built:
    """NYC Parks "World's Fair" bench (1939/1964 design): cast-iron end frames, 6 ft (1.83 m) long, seat 0.43 m,
    back 0.86 m, depth 0.66 m, hardwood slats."""
    iron = P.cast_iron()
    wood = P.wood()
    # end-frame profile given as (height z, depth y); prism(axis="X") extrudes it along X
    prof = [(0.00, 0.30), (0.06, 0.30), (0.10, 0.17), (0.40, 0.14), (0.43, 0.33), (0.50, 0.33), (0.52, 0.10),
            (0.56, -0.06), (0.62, -0.16), (0.86, -0.24), (0.86, -0.32), (0.60, -0.25), (0.52, -0.18),
            (0.46, -0.16), (0.42, -0.18), (0.10, -0.26), (0.06, -0.34), (0.00, -0.34)]
    frames = [C.prism("frame_l", prof, 0.86, 0.915, material=iron, axis="X"),
              C.prism("frame_r", prof, -0.915, -0.86, material=iron, axis="X")]
    slats = []
    for i, y in enumerate((0.28, 0.175, 0.07, -0.035, -0.14)):
        slats.append(C.box(f"seat_slat{i}", (1.83, 0.085, 0.032), origin=(0.0, y, 0.445), material=wood, anchor="center", bevel=0.006))
    for i, (z, y) in enumerate(((0.585, -0.175), (0.665, -0.196), (0.745, -0.216), (0.825, -0.237))):
        sl = C.box(f"back_slat{i}", (1.83, 0.085, 0.028), origin=(0.0, y, z), material=wood, anchor="center", bevel=0.006)
        C.rotate(sl, -14.0, "X", pivot=(0.0, y, z))
        slats.append(sl)
    rails = [C.box("rail_front", (1.74, 0.045, 0.045), origin=(0.0, 0.27, 0.395), material=iron, anchor="center"),
             C.box("rail_back", (1.74, 0.045, 0.045), origin=(0.0, -0.13, 0.395), material=iron, anchor="center")]
    return C.Built(lod0=frames + slats + rails,
                   extra={"key_dims_m": {"length": 1.83, "seat_height": 0.43, "back_height": 0.86, "depth": 0.66}})


def build_tree_guard() -> C.Built:
    """NYC tree-pit guard: 18 in (0.46 m) tall green steel picket fence around a 4 x 4 ft (1.22 m) pit,
    hinged gate on the sidewalk side."""
    green = P.parks_green()
    half, h, pitch = 0.61, 0.46, 0.098
    parts = []
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        parts.append(C.box(f"corner{i}", (0.045, 0.045, h + 0.05), origin=(sx * half, sy * half, 0.0), material=green, anchor="bottom"))
        parts.append(C.lathe(f"finial{i}", [(0.030, 0.0), (0.022, 0.03), (0.0, 0.055)], 8, material=green,
                             origin=(sx * half, sy * half, h + 0.05)))
    for side in range(4):
        ang = math.radians(90 * side)
        ca, sa = math.cos(ang), math.sin(ang)

        def place(u, v, w, dpt, hh, zc, name):
            ob = C.box(name, (w, dpt, hh), origin=(u * ca - v * sa, u * sa + v * ca, zc), material=green, anchor="center")
            C.rotate(ob, 90 * side, "Z", pivot=(u * ca - v * sa, u * sa + v * ca, zc))
            return ob

        parts.append(place(0.0, half, 1.18, 0.030, 0.038, h - 0.019, f"toprail{side}"))
        parts.append(place(0.0, half, 1.18, 0.026, 0.030, 0.075, f"botrail{side}"))
        n = int(1.16 / pitch)
        for k in range(n):
            u = -0.58 + pitch * (k + 0.5)
            parts.append(place(u, half, 0.016, 0.016, h - 0.02, h / 2 - 0.01, f"picket{side}_{k}"))
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"pit": 1.22, "height": 0.46, "picket_pitch": pitch}})


def build_tree_grate() -> C.Built:
    """Cast-iron tree grate: 4 x 4 ft (1.22 m) square frame with a 0.48 m trunk opening and sector slots."""
    iron = P.cast_iron()
    half, r_open = 0.61, 0.24
    ring = [(-half, -half), (half, -half), (half, half), (-half, half)]
    holes = [C.regular_polygon(28, r_open)]
    for band, (r0, r1) in enumerate(((0.275, 0.375), (0.410, 0.510))):
        n = 16
        for k in range(n):
            a0 = C.TAU * k / n + math.radians(2.5)
            a1 = C.TAU * (k + 1) / n - math.radians(2.5)
            arc = [(r1 * math.cos(a), r1 * math.sin(a)) for a in [a0 + (a1 - a0) * i / 4 for i in range(5)]]
            arc += [(r0 * math.cos(a), r0 * math.sin(a)) for a in [a1 + (a0 - a1) * i / 4 for i in range(5)]]
            holes.append(arc)
    plate = C.extrude_grate("tree_grate", ring, holes, 0.0, 0.042, material=iron)
    frame = C.sweep("frame", [(-half - 0.05, -half - 0.05), (half + 0.05, -half - 0.05), (half + 0.05, half + 0.05),
                              (-half - 0.05, half + 0.05)], [(-0.02, 1.0), (0.012, 1.0)], material=iron)
    return C.Built(lod0=[plate, frame],
                   extra={"key_dims_m": {"size": 1.22, "trunk_opening_dia": 0.48, "thickness": 0.042}})


def build_vent_grate() -> C.Built:
    """Subway ventilation grating in the sidewalk: 4 x 8 ft (1.22 x 2.44 m) cast frame with 22 bearing bars."""
    iron = P.cast_iron()
    w, l, h = 1.22, 2.44, 0.05
    parts = [C.box("frame_l", (0.07, l, h), origin=(-(w / 2 - 0.035), 0, 0.0), material=iron, anchor="bottom"),
             C.box("frame_r", (0.07, l, h), origin=(w / 2 - 0.035, 0, 0.0), material=iron, anchor="bottom"),
             C.box("frame_f", (w, 0.07, h), origin=(0, l / 2 - 0.035, 0.0), material=iron, anchor="bottom"),
             C.box("frame_b", (w, 0.07, h), origin=(0, -(l / 2 - 0.035), 0.0), material=iron, anchor="bottom")]
    n = 21
    for k in range(n):
        x = -w / 2 + (w / (n + 1)) * (k + 1)
        parts.append(C.box(f"bar{k}", (0.024, l - 0.14, 0.044), origin=(x, 0.0, 0.003), material=iron, anchor="bottom"))
    for k in range(5):
        y = -l / 2 + (l / 6) * (k + 1)
        parts.append(C.box(f"tie{k}", (w - 0.14, 0.016, 0.020), origin=(0.0, y, 0.006), material=iron, anchor="bottom"))
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"width": w, "length": l, "proud_of_sidewalk": h}})


def _manhole(name: str, legend: tuple[str, ...], utility_hex: str) -> C.Built:
    """24 in cast-iron cover in its frame, raised concentric ribs, pick holes and cast lettering."""
    iron = C.mat_textured(f"cast_iron_{name}", "metal_cast_iron_rust", 0.8, tint=utility_hex, roughness=0.78, metallic=0.6)
    r = 0.305
    frame = C.lathe("frame", [(r + 0.075, -0.06), (r + 0.075, 0.005), (r + 0.010, 0.010), (r + 0.010, -0.06)], 32, material=iron)
    cover = C.lathe("cover", [(0.0, 0.0), (r - 0.004, 0.0), (r, 0.012), (r - 0.006, 0.040), (0.0, 0.040)], 32,
                    material=iron)
    parts = [frame, cover]
    for k, rr in enumerate((0.115, 0.185, 0.255)):
        parts.append(C.torus(f"rib{k}", rr, 0.007, 28, 5, origin=(0, 0, 0.040), material=iron))
    for k in range(24):
        a = C.TAU * k / 24
        parts.append(C.box(f"lug{k}", (0.035, 0.016, 0.010), origin=(0.222 * math.cos(a), 0.222 * math.sin(a), 0.040),
                           material=iron, anchor="bottom"))
    for sgn in (-1, 1):
        parts.append(C.box(f"pick_hole{sgn}", (0.055, 0.022, 0.012), origin=(sgn * 0.245, 0.0, 0.034), material=P.black_matte(), anchor="bottom"))
    for i, line in enumerate(legend):
        t = C.text_mesh(f"legend{i}", line, 0.052, material=iron, depth=0.008,
                        center=(0.0, 0.0, 0.0))
        C.rotate(t, -90.0, "X")
        C.move(t, 0.0, 0.052 * 1.7 * (len(legend) - 1) / 2 - 0.052 * 1.7 * i, 0.046)
        parts.append(t)
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"cover_dia": 0.61, "frame_dia": 0.76, "proud": 0.04}, "legend": list(legend)})


def build_manhole_coned() -> C.Built:
    return _manhole("coned", ("CON EDISON", "ELECTRIC"), "#8A7E70")


def build_manhole_dep() -> C.Built:
    return _manhole("dep", ("NYC", "SEWER"), "#7C7468")


def _steam_stack(height: float, name: str) -> C.Built:
    """Con Edison street steam vent: orange/white banded fibreglass tube over a manhole, with a mesh top."""
    orange = P.dot_orange()
    white = P.white_paint()
    r = 0.45
    band = 0.50
    parts = [C.lathe("skirt", [(0.60, 0.0), (0.60, 0.06), (r + 0.03, 0.12), (r + 0.02, 0.20)], 24, material=orange)]
    n = max(2, int(round(height / band)))
    for k in range(n):
        z0, z1 = 0.18 + k * band, 0.18 + min((k + 1) * band, height - 0.18)
        if z1 <= z0:
            break
        parts.append(C.lathe(f"band{k}", [(r, z0), (r, z1)], 24, material=orange if k % 2 == 0 else white, cap=False, smooth=True))
    parts.append(C.lathe("rim", [(r, height - 0.02), (r + 0.035, height + 0.01), (r + 0.035, height + 0.05), (r - 0.02, height + 0.05)],
                         24, material=orange, smooth=False))
    parts.append(C.cyl("mesh", r - 0.02, 0.012, 24, origin=(0, 0, height + 0.038), material=P.dark_grey()))
    return C.Built(lod0=parts, extra={"key_dims_m": {"height": height, "dia": 0.90, "band_height": band}})


def build_steam_stack_3m() -> C.Built:
    return _steam_stack(3.0, "steam3")


def build_steam_stack_6m() -> C.Built:
    return _steam_stack(6.0, "steam6")


def build_muni_meter() -> C.Built:
    """DOT Muni-Meter parking pay station (Parkeon Strada class): 1.55 m column, solar panel, keypad and printer."""
    grey = C.mat_solid("meter_grey", "#5B6166", 0.45, 0.3)
    dark = P.black_matte()
    green = P.parks_green()
    base = C.box("base", (0.30, 0.24, 0.09), material=grey, anchor="bottom", bevel=0.012)
    column = C.box("column", (0.235, 0.185, 1.05), origin=(0, 0, 0.09), material=grey, anchor="bottom", bevel=0.012)
    head = C.box("head", (0.335, 0.255, 0.40), origin=(0, 0, 1.14), material=grey, anchor="bottom", bevel=0.018)
    faceplate = C.box("faceplate", (0.285, 0.014, 0.34), origin=(0.0, 0.128, 1.34), material=dark, anchor="center")
    disp = C.box("display", (0.175, 0.008, 0.095), origin=(0.0, 0.138, 1.46), material=C.mat_emissive("SCREEN_METER", "#9FE0B0", 1.6, base="#101814"), anchor="center")
    keys = [C.box(f"key{i}", (0.028, 0.010, 0.024), origin=(-0.075 + 0.05 * (i % 4), 0.138, 1.35 - 0.038 * (i // 4)),
                  material=P.dark_grey(), anchor="center") for i in range(12)]
    slot = C.box("card_slot", (0.075, 0.012, 0.014), origin=(0.075, 0.138, 1.30), material=dark, anchor="center")
    printer = C.box("receipt", (0.115, 0.014, 0.020), origin=(0.0, 0.138, 1.185), material=dark, anchor="center")
    solar = C.box("solar_panel", (0.30, 0.20, 0.022), origin=(0.0, -0.02, 1.565), material=C.mat_solid("solar_cell", "#12203A", 0.25, 0.5), anchor="center")
    C.rotate(solar, 18.0, "X", pivot=(0.0, -0.02, 1.565))
    decal = C.box("dot_decal", (0.20, 0.006, 0.07), origin=(0.0, -0.130, 1.34), material=green, anchor="center")
    return C.Built(lod0=[base, column, head, faceplate, disp, slot, printer, solar, decal] + keys,
                   extra={"key_dims_m": {"height": 1.58, "head_w": 0.335, "display_height": 1.46}})


def build_fire_alarm_box() -> C.Built:
    """FDNY emergency reporting system box on its cast pedestal, with the red indicator globe on a gooseneck."""
    red = P.fdny_red()
    iron = P.cast_iron()
    ped = C.lathe("pedestal", [(0.145, 0.0), (0.145, 0.06), (0.115, 0.11), (0.100, 0.85), (0.120, 0.95), (0.115, 1.02)],
                  16, material=iron, smooth=False)
    box = C.box("box", (0.290, 0.235, 0.430), origin=(0.0, 0.0, 1.02), material=red, anchor="bottom", bevel=0.014)
    door = C.box("door", (0.235, 0.020, 0.350), origin=(0.0, 0.1225, 1.235), material=red, anchor="center")
    lever = C.box("pull_lever", (0.075, 0.030, 0.045), origin=(0.0, 0.140, 1.175), material=P.white_paint(), anchor="center")
    lid = C.lathe("lid", [(0.163, 0.0), (0.150, 0.035), (0.085, 0.070), (0.0, 0.085)], 12, material=red, origin=(0, 0, 1.45))
    goose = C.tube("gooseneck", C.bezier_points([(0.0, 0.0, 1.50), (0.0, 0.0, 1.72), (0.0, 0.10, 1.80), (0.0, 0.19, 1.76)], 10),
                   0.014, 8, material=iron)
    globe = C.lathe("globe", [(0.0, 0.0), (0.055, 0.02), (0.075, 0.075), (0.055, 0.130), (0.0, 0.150)], 14,
                    material=P.globe_red(), origin=(0.0, 0.19, 1.62), smooth=True)
    return C.Built(lod0=[ped, box, door, lever, lid, goose, globe],
                   extra={"key_dims_m": {"box_height": 1.45, "overall_height": 1.80, "box_size": [0.29, 0.235, 0.43]}})


def _trash_pile(n_bags: int, n_boxes: int, seed: int, spread: float) -> C.Built:
    """Bagged refuse set out for DSNY collection: 55-gallon black bags plus flattened cardboard."""
    bag_mat = P.bag_black()
    card = C.mat_solid("cardboard", "#8A6A44", 0.85)
    rng = random.Random(seed)
    parts = []
    prof = [(0.02, 0.0), (0.20, 0.05), (0.29, 0.16), (0.31, 0.30), (0.26, 0.44), (0.15, 0.55), (0.075, 0.60), (0.045, 0.66)]
    for i in range(n_bags):
        h = rng.uniform(0.55, 0.78)
        s = rng.uniform(0.85, 1.15)
        ob = C.lathe(f"bag{i}", [(r * s, z * h / 0.66) for r, z in prof], 12, material=bag_mat, smooth=True)
        knot = C.lathe(f"knot{i}", [(0.045 * s, 0.0), (0.055 * s, 0.02), (0.02 * s, 0.06)], 8, material=bag_mat,
                       origin=(0.0, 0.0, h))
        for o in (ob, knot):
            o.data.transform(C.Matrix.Diagonal((rng.uniform(0.88, 1.12), rng.uniform(0.88, 1.12), 1.0, 1.0)))
            C.rotate(o, rng.uniform(0, 360), "Z")
        tilt = rng.uniform(-16, 16)
        px, py = rng.uniform(-spread, spread), rng.uniform(-spread * 0.45, spread * 0.45)
        base_z = 0.0
        if i >= n_bags // 2 and n_bags > 3:
            base_z = rng.uniform(0.30, 0.45)          # bags stacked on the pile
            px, py = px * 0.55, py * 0.55
        for o in (ob, knot):
            C.rotate(o, tilt, "Y")
            C.move(o, px, py, base_z)
            parts.append(o)
    for i in range(n_boxes):
        bw, bd, bh = rng.uniform(0.35, 0.55), rng.uniform(0.25, 0.40), rng.uniform(0.20, 0.32)
        ob = C.box(f"box{i}", (bw, bd, bh), material=card, anchor="bottom")
        C.rotate(ob, rng.uniform(0, 360), "Z")
        C.move(ob, rng.uniform(-spread, spread), rng.uniform(-spread * 0.5, spread * 0.5), 0.0)
        parts.append(ob)
    # tilted bags would otherwise dip below the pavement: settle the whole pile onto z = 0
    drop = min(C.nb.bounds_of([o])["min"][2] for o in parts)
    if drop < 0.0:
        for o in parts:
            C.move(o, 0.0, 0.0, -drop)
    return C.Built(lod0=parts, extra={"key_dims_m": {"bags": n_bags, "boxes": n_boxes, "bag_capacity_gal": 55}})


def build_trash_small() -> C.Built:
    return _trash_pile(3, 1, 20250906, 0.32)


def build_trash_large() -> C.Built:
    return _trash_pile(8, 3, 4242, 0.62)


# ------------------------------------------------------------------------------------------------- food carts
def _cart_chassis(length: float, width: float, deck_h: float, wheel_r: float, *, wheels: int = 4) -> list:
    steel = P.brushed()
    tyre = P.rubber()
    body = C.box("cart_body", (length, width, deck_h - wheel_r * 0.55), origin=(0.0, 0.0, wheel_r * 0.55),
                 material=steel, anchor="bottom", bevel=0.02)
    parts = [body]
    xs = (-length * 0.34, length * 0.34) if wheels == 4 else (0.0,)
    for i, x in enumerate(xs):
        for sgn in (-1.0, 1.0):
            parts.append(C.torus(f"wheel{i}{int(sgn)}", wheel_r * 0.78, wheel_r * 0.22, 16, 8,
                                 origin=(x, sgn * (width / 2 + 0.03), wheel_r), material=tyre, axis="Y"))
            parts.append(C.cyl(f"hub{i}{int(sgn)}", wheel_r * 0.30, 0.03, 10,
                               origin=(x, sgn * (width / 2 + 0.02), wheel_r), material=steel, axis="Y"))
    parts.append(C.tube("handle", [(-length / 2 - 0.30, -width * 0.35, deck_h * 0.75), (-length / 2 - 0.30, width * 0.35, deck_h * 0.75)],
                        0.018, 8, material=steel))
    for sgn in (-1.0, 1.0):
        parts.append(C.tube(f"handle_arm{int(sgn)}", [(-length / 2 + 0.05, sgn * width * 0.35, deck_h * 0.55),
                                                      (-length / 2 - 0.30, sgn * width * 0.35, deck_h * 0.75)],
                            0.018, 8, material=steel))
    return parts


def build_cart_halal() -> C.Built:
    """NYC halal food cart: 2.4 m stainless body with a steam table, griddle hood, propane tanks and a menu board."""
    steel = P.brushed()
    dark = P.dark_grey()
    L_, W, H = 2.40, 1.05, 1.02
    parts = _cart_chassis(L_, W, H, 0.16)
    deck = C.box("steam_table", (L_ * 0.92, W * 0.92, 0.10), origin=(0.0, 0.0, H), material=steel, anchor="bottom")
    hood = C.box("griddle_hood", (L_ * 0.42, W * 0.80, 0.34), origin=(L_ * 0.20, 0.0, H + 0.10), material=steel, anchor="bottom", bevel=0.02)
    flue = C.cyl("flue", 0.075, 0.55, 10, origin=(L_ * 0.34, 0.0, H + 0.44), material=steel)
    pans = [C.box(f"pan{i}", (0.30, 0.44, 0.05), origin=(-L_ * 0.30 + 0.34 * i, 0.0, H + 0.10), material=dark, anchor="bottom")
            for i in range(3)]
    tanks = [C.lathe(f"propane{i}", [(0.0, 0.0), (0.15, 0.03), (0.16, 0.42), (0.10, 0.52), (0.05, 0.56)], 12,
                     material=P.silver_paint(), origin=(-L_ * 0.36 + 0.40 * i, -W * 0.62, 0.0), smooth=True) for i in range(2)]
    posts = [C.cyl(f"canopy_post{i}", 0.020, 1.20, 8, origin=(sx * L_ * 0.44, sy * (W * 0.52), H + 0.10), material=steel)
             for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1)))]
    awn_y = C.mat_solid("awning_yellow", "#F2C230", 0.6)
    awn_r = C.mat_solid("awning_red", "#C0392B", 0.6)
    canopy = []
    nstripe = 8
    for k in range(nstripe):
        x0 = -L_ * 0.56 + (L_ * 1.12 / nstripe) * k
        canopy.append(C.box(f"awning{k}", (L_ * 1.12 / nstripe, W * 1.30, 0.020),
                            origin=(x0 + L_ * 0.56 / nstripe, 0.0, H + 1.30), material=awn_y if k % 2 == 0 else awn_r, anchor="center"))
    menu = C.sign_blank("menu_board", "rect", 0.70, 0.50, thickness=0.010, face_material=C.mat_solid("menu_board", "#F4E9C8", 0.5),
                        back_material=steel, center=(0.55, W * 0.53, H + 0.62))
    return C.Built(lod0=parts + [deck, hood, flue, menu] + pans + tanks + posts + canopy,
                   extra={"key_dims_m": {"body_length": L_, "body_width": W, "counter_height": H, "canopy_height": 2.42}})


def build_cart_hotdog() -> C.Built:
    """Classic NYC hot-dog cart: two-wheel stainless cart with the striped vendor umbrella."""
    steel = P.brushed()
    L_, W, H = 1.35, 0.78, 0.95
    parts = _cart_chassis(L_, W, H, 0.20, wheels=2)
    deck = C.box("lid", (L_ * 0.94, W * 0.94, 0.09), origin=(0.0, 0.0, H), material=steel, anchor="bottom")
    wells = [C.lathe(f"well{i}", [(0.115, 0.0), (0.115, 0.055), (0.10, 0.075)], 14, material=P.dark_grey(),
                     origin=(-0.30 + 0.30 * i, 0.0, H + 0.09)) for i in range(3)]
    mast = C.cyl("umbrella_mast", 0.020, 1.30, 8, origin=(0.0, 0.0, H + 0.09), material=steel)
    yellow = C.mat_solid("umbrella_yellow", "#F5C518", 0.65)
    blue = C.mat_solid("umbrella_blue", "#1F4CA0", 0.65)
    canopy = umbrella("umbrella", 0.95, H + 1.39, 0.30, 12, [yellow, blue])
    ribs = [C.tube(f"rib{k}", [(0.0, 0.0, H + 1.36), (0.94 * math.cos(C.TAU * k / 12), 0.94 * math.sin(C.TAU * k / 12), H + 1.10)],
                   0.008, 5, material=steel) for k in range(12)]
    cond = C.box("condiment_shelf", (0.42, 0.22, 0.020), origin=(L_ * 0.42, W * 0.42, H + 0.02), material=steel, anchor="center")
    return C.Built(lod0=parts + [deck, mast, cond] + wells + canopy + ribs,
                   extra={"key_dims_m": {"body_length": L_, "counter_height": H, "umbrella_dia": 1.90,
                                         "overall_height": round(H + 1.39, 2)}})


def build_cart_coffee() -> C.Built:
    """Breakfast/coffee cart: 1.8 m body, flat canopy, serving window shelf and an urn bank."""
    steel = P.brushed()
    L_, W, H = 1.80, 0.95, 1.00
    parts = _cart_chassis(L_, W, H, 0.17)
    deck = C.box("counter", (L_ * 0.94, W * 0.94, 0.08), origin=(0.0, 0.0, H), material=steel, anchor="bottom")
    urns = [C.lathe(f"urn{i}", [(0.0, 0.0), (0.10, 0.02), (0.105, 0.36), (0.085, 0.42), (0.05, 0.45)], 12,
                    material=steel, origin=(-L_ * 0.30 + 0.26 * i, -W * 0.18, H + 0.08), smooth=True) for i in range(3)]
    case = C.box("display_case", (0.60, 0.42, 0.36), origin=(L_ * 0.24, 0.0, H + 0.08), material=P.glass(), anchor="bottom")
    frame = C.box("case_frame", (0.62, 0.44, 0.030), origin=(L_ * 0.24, 0.0, H + 0.44), material=steel, anchor="center")
    posts = [C.cyl(f"post{i}", 0.020, 1.00, 8, origin=(sx * L_ * 0.45, sy * W * 0.46, H + 0.08), material=steel)
             for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1)))]
    roof = C.box("canopy", (L_ * 1.05, W * 1.20, 0.045), origin=(0.0, 0.0, H + 1.08), material=C.mat_solid("canopy_white", "#E9EAE4", 0.6), anchor="bottom")
    shelf = C.box("serving_shelf", (L_ * 0.75, 0.24, 0.028), origin=(0.0, W * 0.60, H - 0.06), material=steel, anchor="center")
    sign = C.sign_blank("cart_sign", "rect", 0.90, 0.24, thickness=0.010, face_material=C.mat_solid("cart_sign_face", "#2A5AA8", 0.5),
                        back_material=steel, center=(0.0, W * 0.60, H + 0.96))
    return C.Built(lod0=parts + [deck, case, frame, roof, shelf, sign] + urns + posts,
                   extra={"key_dims_m": {"body_length": L_, "counter_height": H, "canopy_height": round(H + 1.125, 2)}})


SPECS = [
    C.PropSpec("hydrant_fdny", "furniture", "hydrant", build_hydrant, (0.36, 0.36, 0.75),
               "NYC fire hydrant: dry-barrel cast-iron pump 0.75 m above grade with a 4.5 in steamer outlet facing the "
               "street and two 2.5 in side outlets with brass caps; pentagon operating nut. Painted FDNY red "
               "(DEP also paints hydrants silver with a coded bonnet — a runtime tint variant).",
               tags=["dep", "fdny"], tolerance=0.10),
    C.PropSpec("litter_basket_wire", "furniture", "waste_basket", build_wire_basket, (0.61, 0.61, 0.79),
               "DSNY green wire-mesh litter basket: 24 in diameter x 31 in high, 24 vertical wires on five hoops with a "
               "rolled rim — the standard NYC corner basket.",
               variants=["litter_basket_betterbin"], tags=["dsny"], tolerance=0.08, lod1_ratio=0.18),
    C.PropSpec("litter_basket_betterbin", "furniture", "waste_basket", build_better_bin, (0.62, 0.65, 0.95),
               "DSNY 'Better Bin' (2022 basket replacement): perforated steel body 0.61 m diameter x 0.95 m with a "
               "sloped hood and a single throw opening.",
               variants=["litter_basket_wire"], tags=["dsny"], tolerance=0.10),
    C.PropSpec("mailbox_usps", "furniture", "mailbox", build_mailbox, (0.47, 0.61, 1.27),
               "USPS street collection box: 50 in (1.27 m) tall, 18.5 in wide, curved hood, pull-down hopper door with "
               "the pull handle, on four legs.", tags=["usps"], tolerance=0.10),
    C.PropSpec("standpipe_siamese", "furniture", "standpipe", build_standpipe, (0.36, 0.33, 1.02),
               "Fire-department siamese standpipe connection: freestanding galvanised riser with a wye body and two "
               "2.5 in inlets with brass caps at ~1.0 m — the sidewalk connection outside NYC buildings.",
               tags=["fdny"], tolerance=0.12),
    C.PropSpec("linknyc_kiosk", "furniture", "linknyc", build_linknyc, (0.82, 0.32, 2.90),
               "LinkNYC Link1.0 kiosk: 9 ft 6 in (2.90 m) x 31 in (0.79 m) x 11 in slab in brushed stainless with a "
               "portrait 55 in display (SCREEN_EMISSIVE) on each broad face, tablet, keypad and vented head.",
               tags=["linknyc"], tolerance=0.08),
    C.PropSpec("bollard_steel", "furniture", "bollard", build_bollard, (0.28, 0.28, 0.92),
               "Sidewalk security bollard: 8 in (0.219 m) schedule-40 steel pipe, 0.90 m above grade with a domed cap "
               "and a reflective band.", tags=["dot"], tolerance=0.10),
    C.PropSpec("planter_concrete", "furniture", "planter", build_planter, (1.05, 1.05, 0.75),
               "Cast concrete street planter of the BID/DOT plaza programme: 1.05 m top diameter, 0.75 m tall, soil "
               "filled to 0.62 m.", tags=["dot", "bid"], tolerance=0.08),
    C.PropSpec("bench_worlds_fair", "furniture", "bench", build_bench, (1.83, 0.66, 0.86),
               "NYC Parks 'World's Fair' bench (1939/1964 design, still the Parks standard): cast-iron end frames with "
               "hardwood slats, 6 ft long, 0.43 m seat height, 0.86 m back height, 0.66 m deep.",
               tags=["parks"], tolerance=0.08),
    C.PropSpec("tree_guard", "furniture", "tree_guard", build_tree_guard, (1.31, 1.31, 0.52),
               "NYC tree-pit guard: 18 in (0.46 m) green steel picket fence with finialled corner posts around a "
               "4 x 4 ft (1.22 m) pit.", variants=["tree_grate"], tags=["parks"], tolerance=0.10, lod1_ratio=0.15),
    C.PropSpec("tree_grate", "furniture", "tree_grate", build_tree_grate, (1.32, 1.32, 0.062),
               "Cast-iron tree grate: 4 x 4 ft square in a frame with a 0.48 m trunk opening and two rings of sector "
               "slots.", variants=["tree_guard"], tags=["parks", "dot"], tolerance=0.10, lod1_ratio=0.15),
    C.PropSpec("vent_grate_sidewalk", "furniture", "subway_vent_grate", build_vent_grate, (1.22, 2.44, 0.05),
               "Subway ventilation grating set in the sidewalk: 4 x 8 ft cast frame with 21 bearing bars and five "
               "cross ties, standing 0.05 m proud of the pavement.", tags=["mta"], tolerance=0.06, lod1_ratio=0.15),
    C.PropSpec("manhole_coned", "furniture", "manhole", build_manhole_coned, (0.76, 0.76, 0.10),
               "Con Edison electric service manhole cover: 24 in (0.61 m) cast-iron cover with concentric ribs, cast "
               "CON EDISON / ELECTRIC lettering and two pick holes, in a 30 in frame.",
               variants=["manhole_dep"], tags=["coned"], tolerance=0.10, lod1_ratio=0.12),
    C.PropSpec("manhole_dep", "furniture", "manhole", build_manhole_dep, (0.76, 0.76, 0.10),
               "NYC DEP sewer manhole cover: 24 in cast-iron cover with cast NYC / SEWER lettering.",
               variants=["manhole_coned"], tags=["dep"], tolerance=0.10, lod1_ratio=0.12),
    C.PropSpec("steam_stack_3m", "furniture", "steam_vent", build_steam_stack_3m, (1.20, 1.20, 3.05),
               "Con Edison street steam vent tube, 3 m: 0.90 m diameter fibreglass tube in alternating orange and white "
               "0.5 m bands over a manhole, with a mesh top and a skirt.",
               variants=["steam_stack_6m"], tags=["coned"], tolerance=0.08),
    C.PropSpec("steam_stack_6m", "furniture", "steam_vent", build_steam_stack_6m, (1.20, 1.20, 6.05),
               "Con Edison street steam vent tube, 6 m version used where the plume must clear traffic.",
               variants=["steam_stack_3m"], tags=["coned"], tolerance=0.08),
    C.PropSpec("muni_meter", "furniture", "muni_meter", build_muni_meter, (0.34, 0.29, 1.61),
               "DOT Muni-Meter parking pay station (Parkeon Strada class): 1.55 m column with a solar panel, LCD, "
               "keypad, card slot and receipt printer.", tags=["dot"], tolerance=0.10),
    C.PropSpec("fire_alarm_box", "furniture", "fire_alarm_box", build_fire_alarm_box, (0.33, 0.46, 1.80),
               "FDNY emergency reporting system street box: red pull box on a fluted cast pedestal with the red "
               "indicator globe on a gooseneck.", tags=["fdny"], tolerance=0.12),
    C.PropSpec("trash_bags_small", "furniture", "trash_pile", build_trash_small, (0.95, 0.75, 0.80),
               "Three 55-gallon black refuse bags and a carton set out at the curb for DSNY collection.",
               variants=["trash_bags_large"], tags=["dsny"], tolerance=0.20),
    C.PropSpec("trash_bags_large", "furniture", "trash_pile", build_trash_large, (1.45, 1.05, 1.18),
               "Eight-bag curbside refuse pile with flattened cartons — the standard NYC set-out outside an apartment "
               "house on a collection night.", variants=["trash_bags_small"], tags=["dsny"], tolerance=0.20),
    C.PropSpec("cart_halal", "furniture", "food_cart", build_cart_halal, (2.72, 1.37, 2.42),
               "NYC halal food cart: 2.4 m stainless body on four wheels with a steam table, griddle hood and flue, "
               "propane tanks, menu board and a striped canopy at 2.4 m.",
               variants=["cart_hotdog", "cart_coffee"], tags=["vendor"], tolerance=0.12),
    C.PropSpec("cart_hotdog", "furniture", "food_cart", build_cart_hotdog, (1.95, 1.90, 2.34),
               "Classic NYC hot-dog cart: two-wheel stainless cart with three boiler wells and the 1.9 m striped "
               "vendor umbrella.", variants=["cart_halal", "cart_coffee"], tags=["vendor"], tolerance=0.12),
    C.PropSpec("cart_coffee", "furniture", "food_cart", build_cart_coffee, (2.10, 1.20, 2.13),
               "Breakfast/coffee cart: 1.8 m body with three urns, a glazed display case, serving shelf and a flat "
               "canopy.", variants=["cart_halal", "cart_hotdog"], tags=["vendor"], tolerance=0.12),
]
