"""Sign blanks and their supports.

Every blank carries the runtime-swappable ``SIGN_FACE`` material on its front face **only**, with the UV of that
face spanning exactly (0,0)-(1,1) over the face's bounding box, u to the reader's right and v upwards, so the
engine can render the real legend from ``roads/signs.parquet`` (mutcd_code, text, arrow) straight onto it.  The
default texture baked in by ``_legends`` is the published MUTCD / NYC DOT layout of that sign.

Anchor exception: a blank has no ground contact, so its origin is the **centre of the sign face** and the catalog
entry records ``anchor.origin = "sign_face_center"``.  The U-channel posts and the street-name blade bracket are
the ground-contact / pole-contact parts these blanks bolt to.
"""
from __future__ import annotations

import _core as C
import _legends as L
import _palette as P

IN = 0.0254
BLANK_T = 0.0020            # 0.080 in aluminium blank
FACE_ANCHOR = {"origin": "sign_face_center", "up_blender": "+Z", "facing_blender": "+Y", "up_gltf": "+Y", "facing_gltf": "-Z"}


def _blank(name: str, shape: str, w: float, h: float, image, *, two_sided: bool = False, thickness: float = BLANK_T) -> C.Built:
    face = C.mat_sign_face(image)
    ob = C.sign_blank(name, shape, w, h, thickness=thickness, face_material=face,
                      back_material=P.aluminium(), two_sided=two_sided)
    return C.Built(lod0=[ob], lod1=[C.duplicate(ob, name + "_LOD1")], lod1_kind="identical_flat",
                   extra={"anchor": FACE_ANCHOR, "sign_face_uv": "0..1 over the face bounding box",
                          "key_dims_m": {"face_w": w, "face_h": h, "thickness": thickness}})


def build_one_way() -> C.Built:
    return _blank("sign_r6_1", "rect", 0.914, 0.305, L.one_way_r6_1())


def build_stop() -> C.Built:
    return _blank("sign_r1_1", "octagon", 0.762, 0.762, L.stop_r1_1())


def build_yield() -> C.Built:
    return _blank("sign_r1_2", "triangle_down", 0.914, 0.792, L.yield_r1_2())


def build_speed_limit() -> C.Built:
    return _blank("sign_r2_1", "rect", 0.610, 0.762, L.speed_limit_r2_1(25))


def build_parking_18() -> C.Built:
    return _blank("sign_nyc_p18", "rect", 0.305, 0.457, L.generate_all()["parking_no_standing"])


def build_parking_24() -> C.Built:
    return _blank("sign_nyc_p24", "rect", 0.305, 0.610, L.generate_all()["parking_alt_side"])


def build_street_name_blade() -> C.Built:
    """NYC street-name blade with its pole bracket. Origin sits on the pole axis where the bracket clamps, so the
    engine can place the blade directly against a lamp post or signal standard."""
    face = C.mat_sign_face(L.street_name_blade())
    steel = P.galv()
    w, h = 0.762, 0.152
    blade = C.sign_blank("blade", "rect", w, h, thickness=0.0025, face_material=face, back_material=face,
                         two_sided=True, center=(w / 2 + 0.115, 0.0, 0.0))
    band = C.torus("clamp_band", 0.085, 0.010, 16, 6, material=steel, axis="Z")
    arm = C.box("bracket_arm", (0.115, 0.030, 0.055), origin=(0.085 + 0.0575, 0.0, 0.0), material=steel, anchor="center")
    plate = C.box("bracket_plate", (0.030, 0.036, 0.135), origin=(0.128, 0.0, 0.0), material=steel, anchor="center")
    return C.Built(lod0=[blade, band, arm, plate],
                   extra={"anchor": {"origin": "bracket_pole_axis", "up_blender": "+Z", "facing_blender": "+Y",
                                     "up_gltf": "+Y", "facing_gltf": "-Z"},
                          "sign_face_uv": "0..1 over each face; the back face is mirrored so the legend reads from both sides",
                          "key_dims_m": {"blade_w": w, "blade_h": h, "bracket_clamp_dia": 0.17}})


def _u_channel(name: str, length: float) -> C.Built:
    """Galvanised 3 lb/ft U-channel sign post with the standard 1 in punched holes on 1 in centres."""
    steel = P.galv()
    sec = C.u_channel_section()
    post = C.sweep(name, sec, [(0.0, 1.0), (length, 1.0)], material=steel, uv_scale=1.0)
    holes = []
    z = length - 0.10
    while z > length * 0.45:
        holes.append(C.cyl(f"{name}_hole{len(holes)}", 0.0125, 0.010, 8, origin=(0.0, -0.005, z), material=P.dark_grey(), axis="Y"))
        z -= 0.0254
    return C.Built(lod0=[post] + holes,
                   extra={"key_dims_m": {"length": length, "flange_width": 0.070, "depth": 0.038, "weight_class": "3 lb/ft"}})


def build_post_3m() -> C.Built:
    return _u_channel("post_u_channel_3m", 3.05)


def build_post_2m() -> C.Built:
    return _u_channel("post_u_channel_2m", 2.44)


SIGN_VARIANTS = ["sign_r6_1_oneway", "sign_r1_1_stop", "sign_r1_2_yield", "sign_r2_1_speed",
                 "sign_nyc_parking_18", "sign_nyc_parking_24", "sign_street_name_blade"]

SPECS = [
    C.PropSpec("sign_r6_1_oneway", "signs", "road_sign", build_one_way, (0.914, 0.002, 0.305),
               "MUTCD R6-1 ONE WAY, NYC size 36 x 12 in (0.914 x 0.305 m): black plaque, white border, white arrow and "
               "legend. Face is the SIGN_FACE slot; the engine picks the arrow direction from roads/signs.parquet.",
               variants=SIGN_VARIANTS, tags=["mutcd:R6-1"], tolerance=0.05),
    C.PropSpec("sign_r1_1_stop", "signs", "road_sign", build_stop, (0.762, 0.002, 0.762),
               "MUTCD R1-1 STOP, 30 in (0.762 m) across the flats — the NYC standard size on local streets. Regular "
               "octagon blank with a 0.75 in white border and 10 in legend.",
               variants=SIGN_VARIANTS, tags=["mutcd:R1-1"], tolerance=0.05),
    C.PropSpec("sign_r1_2_yield", "signs", "road_sign", build_yield, (0.914, 0.002, 0.792),
               "MUTCD R1-2 YIELD, 36 in equilateral triangle point down (0.914 m side, 0.792 m tall), red border on a "
               "white field.", variants=SIGN_VARIANTS, tags=["mutcd:R1-2"], tolerance=0.05),
    C.PropSpec("sign_r2_1_speed", "signs", "road_sign", build_speed_limit, (0.610, 0.002, 0.762),
               "MUTCD R2-1 SPEED LIMIT, 24 x 30 in (0.610 x 0.762 m); the baked legend is the NYC citywide default of "
               "25 mph, replaced per instance from roads/segments.parquet posted_speed_mph.",
               variants=SIGN_VARIANTS, tags=["mutcd:R2-1"], tolerance=0.05),
    C.PropSpec("sign_nyc_parking_18", "signs", "road_sign", build_parking_18, (0.305, 0.002, 0.457),
               "NYC DOT parking regulation sign, 12 x 18 in (0.305 x 0.457 m): white retroreflective plaque with a red "
               "legend and the double-headed regulation arrows (baked default NO STANDING ANYTIME).",
               variants=SIGN_VARIANTS, tags=["nyc_dot_parking"], tolerance=0.05),
    C.PropSpec("sign_nyc_parking_24", "signs", "road_sign", build_parking_24, (0.305, 0.002, 0.610),
               "NYC DOT parking regulation sign, 12 x 24 in (0.305 x 0.610 m); baked default is an alternate-side "
               "street-cleaning regulation with the broom pictogram.",
               variants=SIGN_VARIANTS, tags=["nyc_dot_parking"], tolerance=0.05),
    C.PropSpec("sign_street_name_blade", "signs", "street_name_sign", build_street_name_blade, (0.99, 0.17, 0.17),
               "NYC street-name blade, 6 x 30 in (0.152 x 0.762 m) reflective green with a white border and mixed-case "
               "legend, double sided, on its cast pole bracket with a 170 mm clamp band.",
               variants=SIGN_VARIANTS, tags=["nyc_dot_street_name"], tolerance=0.10),
    C.PropSpec("post_u_channel_3m", "signs", "sign_post", build_post_3m, (0.070, 0.038, 3.05),
               "Galvanised 3 lb/ft U-channel sign post, 10 ft (3.05 m), punched on 1 in centres — the NYC DOT standard "
               "support for regulatory and parking signs.",
               variants=["post_u_channel_2m"], tags=["support"], tolerance=0.05),
    C.PropSpec("post_u_channel_2m", "signs", "sign_post", build_post_2m, (0.070, 0.038, 2.44),
               "Galvanised 3 lb/ft U-channel sign post, 8 ft (2.44 m), for single small parking signs.",
               variants=["post_u_channel_3m"], tags=["support"], tolerance=0.05),
]
