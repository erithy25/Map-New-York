"""NYC street-lighting props: cobra-head davit, Bishop's Crook, Central Park twin lamp, highway high-mast.

Dimensions come from the NYC DOT street-lighting standards (30 ft mounting height / 12 ft davit arm on the
standard octagonal tapered pole), the DOT/LPC historic replica poles (24 ft Bishop's Crook, cast-iron fluted
shaft with a pendant teardrop luminaire) and AASHTO high-mast practice (100 ft shaft, luminaire ring).
Every luminaire carries a ``LAMP_EMISSIVE`` lens and a ``LIGHT_CONE`` night plane pair.
"""
from __future__ import annotations

import math

import _core as C
import _palette as P

FT = 0.3048


# --------------------------------------------------------------------------------------------- shared parts
def cobra_luminaire(y: float, z: float, *, length: float = 0.76, width: float = 0.36, name: str = "luminaire") -> list:
    """LED cobra head (Leotek/GE M-400 class): wedge housing, flat lens underneath, slip-fitter collar."""
    galv = P.aluminium()
    dark = P.dark_grey()
    lens = P.lamp()
    body = C.box(f"{name}_body", (width, length, 0.115), origin=(0.0, y, z + 0.02), material=galv, anchor="bottom", bevel=0.02)
    hood = C.box(f"{name}_hood", (width * 0.78, length * 0.72, 0.06), origin=(0.0, y + 0.02, z + 0.125), material=galv, anchor="bottom", bevel=0.015)
    lensob = C.box(f"{name}_lens", (width * 0.80, length * 0.80, 0.012), origin=(0.0, y, z + 0.012), material=lens, anchor="center")
    collar = C.cyl(f"{name}_collar", 0.061, 0.16, 12, origin=(0.0, y - length * 0.46, z + 0.055), material=dark, axis="-Y")
    return [body, hood, lensob, collar]


def teardrop_luminaire(y: float, z_top: float, *, dia: float = 0.34, height: float = 0.62, name: str = "teardrop") -> list:
    """Pendant teardrop luminaire of the historic poles: acorn-shaped acrylic globe under a cast finial cap."""
    glass = P.lamp_warm()
    iron = P.cast_iron()
    prof = [(0.0, 0.0), (dia * 0.16, 0.02), (dia * 0.34, 0.10), (dia * 0.47, 0.24), (dia * 0.50, 0.38),
            (dia * 0.44, 0.52), (dia * 0.30, 0.62), (dia * 0.20, 0.68), (dia * 0.20, 0.74)]
    globe = C.lathe(f"{name}_globe", [(r, height * (h / 0.74)) for r, h in prof], 20, material=glass)
    C.move(globe, 0.0, y, z_top - height)
    cap = C.lathe(f"{name}_cap", [(dia * 0.20, 0.0), (dia * 0.34, 0.03), (dia * 0.30, 0.09), (dia * 0.10, 0.15), (0.0, 0.19)],
                  20, material=iron)
    C.move(cap, 0.0, y, z_top - height * 0.08)
    return [globe, cap]


def park_lantern(x: float, z_base: float, *, name: str = "lantern") -> list:
    """Cast-iron park lantern: six-sided tapered glass housing, vented cap, ball finial."""
    iron = P.cast_iron()
    glass = P.lamp_warm()
    hex_lo = C.regular_polygon(6, 0.175, math.radians(30))
    glassob = C.sweep(f"{name}_glass", hex_lo, [(0.0, 1.0), (0.44, 0.714)], material=glass, origin=(x, 0.0, z_base))
    skirt = C.lathe(f"{name}_skirt", [(0.10, 0.0), (0.20, 0.06), (0.19, 0.09)], 6, material=iron, origin=(x, 0.0, z_base - 0.09))
    capprof = [(0.135, 0.0), (0.20, 0.03), (0.175, 0.11), (0.085, 0.19), (0.055, 0.21)]
    cap = C.lathe(f"{name}_cap", capprof, 6, material=iron, origin=(x, 0.0, z_base + 0.44))
    finial = C.lathe(f"{name}_finial", [(0.0, 0.0), (0.045, 0.035), (0.055, 0.075), (0.030, 0.115), (0.012, 0.145), (0.0, 0.155)],
                     10, material=iron, origin=(x, 0.0, z_base + 0.65))
    return [glassob, skirt, cap, finial]


# --------------------------------------------------------------------------------------------- builders
def build_cobra_davit() -> C.Built:
    """NYC DOT standard: octagonal tapered pole, 30 ft (9.14 m) mounting height, 12 ft (3.66 m) davit arm."""
    galv = P.galv()
    conc = P.concrete()
    sec = C.octagon_section(0.216)
    base = C.cyl("base_collar", 0.19, 0.16, 16, material=conc)
    shaft = C.sweep("shaft", sec, [(0.10, 1.0), (0.55, 0.985), (7.50, 0.648)], material=galv, uv_scale=1.0)
    handhole = C.box("handhole", (0.10, 0.19, 0.30), origin=(0.0, -0.095, 0.75), material=P.dark_grey(), anchor="bottom")
    arm_pts = C.bezier_points([(0.0, 0.0, 7.35), (0.0, 0.06, 9.28), (0.0, 1.85, 9.56), (0.0, 3.66, 9.24)], 16)
    radii = [0.070 - 0.022 * (i / 15) for i in range(16)]
    arm = C.tube("davit_arm", arm_pts, radii, 12, material=galv)
    lum = cobra_luminaire(3.90, 9.14)
    cone = C.light_cone("light_cone", (0.0, 3.90, 9.10), 9.10, 0.45, 5.6, material=C.mat_light_cone())
    return C.Built(lod0=[base, shaft, handhole, arm] + lum + [cone],
                   extra={"key_dims_m": {"mounting_height": 9.14, "arm_reach": 3.66, "pole_across_flats_base": 0.216,
                                         "luminaire_length": 0.76}})


def build_bishops_crook() -> C.Built:
    """1892 Bishop's Crook replica (DOT/LPC historic districts): fluted cast-iron shaft, 24 ft (7.32 m) mounting height."""
    iron = P.cast_iron()
    base_prof = [(0.21, 0.0), (0.21, 0.10), (0.175, 0.14), (0.165, 0.30), (0.20, 0.36), (0.20, 0.42),
                 (0.145, 0.50), (0.128, 0.70), (0.118, 0.80)]
    base = C.lathe("base", base_prof, 16, material=iron)
    flute = C.fluted_section(0.098, flutes=16, depth=0.11, per_flute=3)
    shaft = C.sweep("shaft", flute, [(0.78, 1.0), (3.2, 0.83), (6.15, 0.62)], material=iron, uv_scale=1.0, smooth=True)
    collar = C.lathe("collar", [(0.075, 0.0), (0.098, 0.025), (0.098, 0.075), (0.070, 0.10)], 16, material=iron, origin=(0, 0, 6.10))
    crook_pts = C.bezier_points([(0.0, 0.0, 6.18), (0.0, 0.10, 7.62), (0.0, 1.12, 8.08), (0.0, 1.55, 7.60)], 18)
    crook = C.tube("crook", crook_pts, [0.062 - 0.020 * (i / 17) for i in range(18)], 12, material=iron)
    # the two scroll volutes that brace the crook where it leaves the shaft
    scrolls = []
    for k, (y0, z0, r0) in enumerate(((0.16, 6.62, 0.20), (0.52, 7.34, 0.15))):
        pts = [(0.0, y0 + r0 * math.cos(a) * 0.9, z0 + r0 * math.sin(a) - r0 * 0.15 * (a / math.tau))
               for a in [math.tau * (0.15 + 0.85 * i / 11) for i in range(12)]]
        scrolls.append(C.tube(f"scroll{k}", pts, 0.022, 8, material=iron))
    lum = teardrop_luminaire(1.55, 7.62)
    cone = C.light_cone("light_cone", (0.0, 1.55, 7.05), 7.05, 0.30, 4.2, material=C.mat_light_cone())
    return C.Built(lod0=[base, shaft, collar, crook] + scrolls + lum + [cone],
                   extra={"key_dims_m": {"mounting_height": 7.32, "crook_reach": 1.55, "shaft_dia_base": 0.196}})


def build_park_twin() -> C.Built:
    """NYC Parks / Central Park twin-lamp post: fluted cast-iron shaft, two lanterns on scrolled arms."""
    iron = P.cast_iron()
    base = C.lathe("base", [(0.235, 0.0), (0.235, 0.09), (0.19, 0.13), (0.178, 0.32), (0.215, 0.38), (0.215, 0.44),
                            (0.150, 0.52), (0.132, 0.62)], 16, material=iron)
    flute = C.fluted_section(0.112, flutes=16, depth=0.11, per_flute=3)
    shaft = C.sweep("shaft", flute, [(0.60, 1.0), (1.8, 0.86), (3.05, 0.70)], material=iron, uv_scale=1.0, smooth=True)
    cap = C.lathe("shaft_cap", [(0.078, 0.0), (0.115, 0.03), (0.108, 0.09), (0.062, 0.15)], 16, material=iron, origin=(0, 0, 3.02))
    arms = []
    for sgn in (-1.0, 1.0):
        pts = C.bezier_points([(0.0, 0.0, 3.10), (sgn * 0.22, 0.0, 3.52), (sgn * 0.62, 0.0, 3.60), (sgn * 0.62, 0.0, 3.32)], 12)
        arms.append(C.tube(f"arm{int(sgn)}", pts, [0.040 - 0.010 * (i / 11) for i in range(12)], 10, material=iron))
        arms.append(C.lathe(f"arm_boss{int(sgn)}", [(0.055, 0.0), (0.085, 0.03), (0.080, 0.08), (0.045, 0.12)], 12,
                            material=iron, origin=(sgn * 0.62, 0.0, 3.30)))
    lanterns = park_lantern(-0.62, 3.42) + park_lantern(0.62, 3.42)
    cones = [C.light_cone("light_cone_l", (-0.62, 0.0, 3.50), 3.50, 0.28, 2.6, material=C.mat_light_cone()),
             C.light_cone("light_cone_r", (0.62, 0.0, 3.50), 3.50, 0.28, 2.6, material=C.mat_light_cone())]
    return C.Built(lod0=[base, shaft, cap] + arms + lanterns + cones,
                   extra={"key_dims_m": {"lantern_centre_height": 3.64, "lantern_spacing": 1.24, "overall_height": 4.22}})


def build_highmast() -> C.Built:
    """Highway high-mast tower: 100 ft (30.5 m) tapered steel shaft with a six-luminaire lowering ring."""
    galv = P.galv()
    dark = P.dark_grey()
    conc = P.concrete_rough()
    pad = C.box("foundation", (1.25, 1.25, 0.18), material=conc)
    plate = C.cyl("base_plate", 0.55, 0.06, 16, origin=(0, 0, 0.18), material=galv)
    shaft = C.sweep("shaft", C.regular_polygon(16, 0.30), [(0.24, 1.0), (12.0, 0.70), (24.0, 0.45), (30.20, 0.33)],
                    material=galv, uv_scale=1.0, smooth=True)
    door = C.box("access_door", (0.24, 0.06, 0.55), origin=(0.0, -0.28, 0.60), material=dark, anchor="bottom")
    head = C.cyl("mast_head", 0.125, 0.55, 12, origin=(0, 0, 30.20), material=galv)
    ring = C.torus("luminaire_ring", 0.85, 0.045, 24, 8, origin=(0, 0, 30.35), material=galv)
    parts = [pad, plate, shaft, door, head, ring]
    lens = P.lamp()
    for k in range(6):
        a = C.TAU * k / 6
        x, y = 0.85 * math.cos(a), 0.85 * math.sin(a)
        spoke = C.tube(f"spoke{k}", [(0.0, 0.0, 30.42), (x, y, 30.36)], 0.030, 8, material=galv)
        body = C.lathe(f"lum{k}", [(0.0, 0.0), (0.20, 0.03), (0.24, 0.10), (0.22, 0.20), (0.10, 0.26)], 14,
                       material=galv, origin=(x, y, 30.10))
        lensob = C.lathe(f"lumlens{k}", [(0.0, 0.0), (0.16, 0.01), (0.19, 0.055)], 14, material=lens, origin=(x, y, 30.05))
        parts += [spoke, body, lensob]
    parts.append(C.light_cone("light_cone", (0.0, 0.0, 30.0), 30.0, 1.4, 12.0, material=C.mat_light_cone()))
    return C.Built(lod0=parts, extra={"key_dims_m": {"mounting_height": 30.20, "ring_diameter": 1.70, "luminaires": 6}})


SPECS = [
    C.PropSpec("lamp_cobra_davit", "lighting", "street_lamp", build_cobra_davit, (0.38, 4.47, 9.40),
               "NYC DOT standard street light: octagonal tapered pole, 30 ft (9.14 m) mounting height, 12 ft (3.66 m) "
               "davit arm, LED cobra-head luminaire (Leotek/GE M-400 class housing 0.76 x 0.36 m). DOT Street Lighting "
               "standard drawings / Standard Highway Specifications.",
               variants=["lamp_bishops_crook", "lamp_park_twin", "lamp_highmast"], tags=["cobra", "variant:1"], tolerance=0.10),
    C.PropSpec("lamp_bishops_crook", "lighting", "street_lamp", build_bishops_crook, (0.42, 1.93, 7.83),
               "Bishop's Crook replica (1892 design, reinstalled by DOT in historic districts): fluted cast-iron shaft on "
               "an ornamental base, scrolled crook, pendant teardrop luminaire at 24 ft (7.32 m) mounting height.",
               variants=["lamp_cobra_davit", "lamp_park_twin"], tags=["historic", "variant:2"], tolerance=0.12),
    C.PropSpec("lamp_park_twin", "lighting", "street_lamp", build_park_twin, (1.64, 0.47, 4.22),
               "NYC Parks twin-lamp post (Central Park drives and park entrances): fluted cast-iron shaft, two scrolled "
               "arms 0.62 m either side carrying six-sided glass lanterns with ball finials, ~4.2 m overall.",
               variants=["lamp_cobra_davit", "lamp_bishops_crook"], tags=["park", "variant:3"], tolerance=0.12),
    C.PropSpec("lamp_highmast", "lighting", "street_lamp", build_highmast, (2.18, 1.94, 30.75),
               "Highway high-mast tower (expressway interchanges): 100 ft (30.5 m) tapered polygonal steel shaft on a "
               "bolted base plate, six luminaires on a 1.7 m lowering ring. AASHTO high-mast lighting practice.",
               variants=["lamp_cobra_davit"], tags=["highway", "variant:4"], tolerance=0.12, lod1_ratio=0.2),
]
