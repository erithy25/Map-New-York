"""Work-zone devices, flags and the two static street animals.

MUTCD Part 6 gives the channelising-device dimensions (28 in cone, 36 in drum with 4-6 in retroreflective bands,
48 in W20-1 warning sign); the jersey barrier is the FHWA F-shape (24 in base, 32 in tall); the steel roadway
plate is the 8 x 12 ft x 1 in plate used over NYC utility cuts.  Flag proportions follow Executive Order 10834
(US) and the 1977 City of New York flag law.
"""
from __future__ import annotations

import math

import _core as C
import _legends as L
import _palette as P

IN = 0.0254


def build_jersey_barrier() -> C.Built:
    """FHWA F-shape precast concrete barrier: 10 ft (3.05 m) segment, 24 in base, 32 in tall, 6 in top."""
    conc = P.concrete_rough()
    steel = P.galv()
    # profile as (height z, depth y) for prism(axis="X")
    prof = [(0.000, 0.305), (0.076, 0.305), (0.254, 0.229), (0.813, 0.076),
            (0.813, -0.076), (0.254, -0.229), (0.076, -0.305), (0.000, -0.305)]
    body = C.prism("barrier", prof, -1.525, 1.525, material=conc, axis="X")
    loops = [C.torus(f"lift_loop{i}", 0.055, 0.010, 10, 5, origin=(x, 0.0, 0.813), material=steel, axis="X")
             for i, x in enumerate((-0.85, 0.85))]
    joint = C.box("joint_key", (0.03, 0.10, 0.42), origin=(1.525, 0.0, 0.20), material=conc, anchor="bottom")
    return C.Built(lod0=[body, joint] + loops,
                   extra={"key_dims_m": {"length": 3.05, "base_width": 0.61, "height": 0.813, "top_width": 0.152},
                          "tileable_axis": "X", "tile_pitch_m": 3.05})


def build_barrel() -> C.Built:
    """MUTCD Part 6 plastic drum: 36 in tall, 18 in wide, two orange and two white retroreflective bands,
    ballasted rubber base."""
    orange = P.safety_orange()
    white = C.mat_solid("retro_white_band", "#EDEDE8", 0.35)
    rubber = P.rubber()
    r = 0.229
    base = C.lathe("ballast_base", [(0.315, 0.0), (0.315, 0.035), (0.250, 0.055), (r + 0.01, 0.070)], 20, material=rubber)
    parts = [base]
    bands = ((0.070, 0.200, orange), (0.200, 0.320, white), (0.320, 0.450, orange), (0.450, 0.570, white),
             (0.570, 0.700, orange), (0.700, 0.820, white))
    for i, (z0, z1, mat) in enumerate(bands):
        rr = r * (1.0 - 0.06 * (z0 / 0.914))
        parts.append(C.lathe(f"band{i}", [(rr, z0), (rr * 0.995, z1)], 20, material=mat, cap=False, smooth=True))
    parts.append(C.lathe("top", [(r * 0.94, 0.820), (r * 0.90, 0.870), (0.075, 0.900), (0.075, 0.914), (0.0, 0.914)],
                         20, material=orange, smooth=False))
    for sgn in (-1.0, 1.0):
        parts.append(C.box(f"handle{int(sgn)}", (0.11, 0.02, 0.035), origin=(0.0, sgn * r * 0.92, 0.845), material=orange, anchor="center"))
    return C.Built(lod0=parts, extra={"key_dims_m": {"height": 0.914, "dia": 0.457, "bands": 6}})


def build_traffic_cone() -> C.Built:
    """MUTCD 28 in traffic cone with two white retroreflective collars on a 14 in ballasted base."""
    orange = P.safety_orange()
    white = C.mat_solid("cone_collar", "#F0F0EA", 0.4)
    h = 0.711
    base = C.box("cone_base", (0.356, 0.356, 0.030), material=P.rubber(), anchor="bottom", bevel=0.010)
    skirt = C.lathe("skirt", [(0.165, 0.030), (0.115, 0.070)], 16, material=orange, smooth=True)
    seg = [(0.115, 0.070), (0.098, 0.300), (0.088, 0.395), (0.074, 0.470), (0.064, 0.545), (0.050, 0.620), (0.030, h)]
    parts = [base, skirt]
    for i in range(len(seg) - 1):
        mat = white if i in (1, 3) else orange
        parts.append(C.lathe(f"cone{i}", [seg[i], seg[i + 1]], 16, material=mat, cap=False, smooth=True))
    parts.append(C.lathe("cone_tip", [(0.030, h), (0.0, h + 0.012)], 16, material=orange, smooth=True))
    return C.Built(lod0=parts, extra={"key_dims_m": {"height": 0.711, "base": 0.356, "collars": 2}})


def build_roadway_plate() -> C.Built:
    """Steel roadway plate over a utility cut: 8 x 12 ft x 1 in plate with cold-patch asphalt ramps on all edges."""
    steel = P.steel_plate()
    asphalt = P.asphalt()
    w, l, t = 2.44, 3.66, 0.025
    plate = C.box("plate", (w, l, t), material=steel, anchor="bottom")
    ramps = []
    ramp_w = 0.40
    for i, (sx, sy) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
        if sx:
            ob = C.prism(f"ramp{i}", [(0.0, -l / 2 - ramp_w), (0.0, l / 2 + ramp_w), (t, l / 2), (t, -l / 2)],
                         w / 2, w / 2 + ramp_w, material=asphalt, axis="X")
            if sx < 0:
                C.mirror_x(ob)
        else:
            ob = C.prism(f"ramp{i}", [(-w / 2 - ramp_w, 0.0), (w / 2 + ramp_w, 0.0), (w / 2, t), (-w / 2, t)],
                         l / 2, l / 2 + ramp_w, material=asphalt, axis="Y")
            if sy < 0:
                ob.data.transform(C.Matrix.Scale(-1.0, 4, C.Vector((0, 1, 0))))
                ob.data.flip_normals()
        ramps.append(ob)
    lugs = [C.cyl(f"lug{i}", 0.030, 0.006, 8, origin=(sx * (w / 2 - 0.12), sy * (l / 2 - 0.12), t), material=steel)
            for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1)))]
    return C.Built(lod0=[plate] + ramps + lugs,
                   extra={"key_dims_m": {"plate": [w, l], "thickness": t, "ramp_width": ramp_w}})


def build_roadwork_sign() -> C.Built:
    """MUTCD W20-1 ROAD WORK AHEAD on a folding portable stand: 48 in orange diamond, bottom of sign at 0.55 m."""
    orange_frame = P.dot_orange()
    steel = P.galv()
    diag = 1.219 * math.sqrt(2.0)
    z0 = 0.55
    zc = z0 + diag / 2
    blank = C.sign_blank("w20_1", "diamond", diag, diag, thickness=0.004,
                         face_material=C.mat_sign_face(L.road_work_w20_1()), back_material=orange_frame,
                         center=(0.0, 0.0, zc))
    mast = C.box("mast", (0.06, 0.05, zc), origin=(0.0, -0.04, 0.0), material=steel, anchor="bottom")
    legs = []
    for i, (dx, dy) in enumerate(((-0.55, -0.40), (0.55, -0.40), (0.0, 0.62))):
        legs.append(C.tube(f"leg{i}", [(0.0, -0.04, 0.55), (dx, dy - 0.04, 0.0)], 0.020, 6, material=steel))
        legs.append(C.box(f"foot{i}", (0.14, 0.14, 0.020), origin=(dx, dy - 0.04, 0.0), material=steel, anchor="bottom"))
    brace = C.tube("brace", [(-0.30, -0.04, 0.30), (0.30, -0.04, 0.30)], 0.014, 6, material=steel)
    flags = [C.sign_blank(f"warning_flag{i}", "rect", 0.46, 0.46, thickness=0.002,
                          face_material=C.mat_solid("fluor_orange_flag", "#FF6A13", 0.6), back_material=orange_frame,
                          center=(sgn * 0.40, 0.0, zc + 0.44))
             for i, sgn in enumerate((-1.0, 1.0))]
    return C.Built(lod0=[blank, mast, brace] + legs + flags,
                   extra={"key_dims_m": {"sign_size_in": 48, "diagonal": round(diag, 3), "sign_bottom": z0},
                          "sign_face_uv": "0..1 over the diamond bounding box"})


def build_construction_fence() -> C.Built:
    """NYC DOB construction fence: 8 ft painted plywood panel on 4x4 posts with a bottom rail and a rub rail,
    tileable along X at the 2.44 m sheet pitch."""
    ply = C.mat_solid("fence_plywood", "#2E6B4F", 0.75)
    lumber = C.mat_textured("fence_lumber", "wood_planks", 1.0, tint="#9C8055", roughness=0.75)
    w, h = 2.438, 2.438
    panel = C.box("panel", (w, 0.019, h), origin=(0.0, 0.0, 0.0), material=ply, anchor="bottom")
    posts = [C.box(f"post{i}", (0.089, 0.089, h + 0.05), origin=(sgn * (w / 2 - 0.045), -0.054, 0.0), material=lumber, anchor="bottom")
             for i, sgn in enumerate((-1.0, 1.0))]
    rails = [C.box(f"rail{i}", (w, 0.038, 0.089), origin=(0.0, -0.038, z), material=lumber, anchor="bottom")
             for i, z in enumerate((0.10, 1.15, 2.25))]
    braces = []
    for sgn in (-1.0, 1.0):
        x0, z0, x1, z1 = sgn * (w / 2 - 0.09), 0.12, sgn * (w / 2 - 0.85), 1.60
        mid = ((x0 + x1) / 2, -0.098, (z0 + z1) / 2)
        length = math.hypot(x1 - x0, z1 - z0)
        b = C.box(f"brace{int(sgn)}", (0.038, 0.089, length), origin=mid, material=lumber, anchor="center")
        C.rotate(b, math.degrees(math.atan2(x1 - x0, z1 - z0)), "Y", pivot=mid)
        braces.append(b)
    return C.Built(lod0=[panel] + posts + rails + braces,
                   extra={"key_dims_m": {"panel": [w, h], "post": 0.089, "thickness": 0.019},
                          "tileable_axis": "X", "tile_pitch_m": w})


def _flagpole(image, name: str, hoist: float = 0.914, fly: float = 1.524, pole_h: float = 6.10) -> C.Built:
    """20 ft satin-aluminium flagpole with a gold ball finial and a waving flag on a FLAG_FACE plane."""
    alu = P.aluminium()
    gold = P.brass()
    base = C.lathe("base_flange", [(0.145, 0.0), (0.145, 0.05), (0.105, 0.10), (0.075, 0.22)], 16, material=alu)
    pole = C.lathe("pole", [(0.058, 0.18), (0.038, pole_h)], 16, material=alu, smooth=True)
    ball = C.lathe("finial_ball", [(0.0, 0.0), (0.035, 0.018), (0.048, 0.055), (0.035, 0.092), (0.0, 0.110)], 12,
                   material=gold, origin=(0.0, 0.0, pole_h), smooth=True)
    halyard = C.tube("halyard", [(0.048, 0.0, pole_h - 0.02), (0.048, 0.0, 0.9)], 0.004, 4, material=P.white_paint())
    mat = C.mat_image("FLAG_FACE", image, roughness=0.75, backface=True)
    mat.use_backface_culling = False
    nu, nv = 14, 7
    z_bot = pole_h - 0.15 - hoist
    bm, uv = C._new_bm()
    verts = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            x = 0.040 + fly * u
            wave = math.sin(u * 6.2 + v * 1.1) * 0.085 * (u ** 1.4)
            z = z_bot + hoist * v + 0.05 * math.sin(u * 4.0) * u
            row.append(bm.verts.new((x, wave, z)))
        verts.append(row)
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            f.smooth = True
            for loop, t in zip(f.loops, ((i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv))):
                loop[uv].uv = t
    bm.normal_update()
    flag = C.bm_object(f"{name}_flag", bm, [mat])
    return C.Built(lod0=[base, pole, ball, halyard, flag],
                   extra={"key_dims_m": {"pole_height": pole_h, "flag_hoist": hoist, "flag_fly": fly},
                          "flag_face_uv": "0..1 over the flag; u from hoist to fly, v bottom to top",
                          "runtime_slot": "FLAG_FACE"})


def build_flag_us() -> C.Built:
    return _flagpole(L.flag_us(), "us")


def build_flag_nyc() -> C.Built:
    return _flagpole(L.flag_nyc(), "nyc")


def build_pigeon() -> C.Built:
    """Rock dove (Columba livia) standing: 0.32 m nose to tail, 0.17 m tall — the static sidewalk pigeon."""
    body_mat = C.mat_solid("pigeon_grey", "#7C8288", 0.75)
    neck = C.mat_solid("pigeon_iridescent", "#3E6B62", 0.35, 0.4)
    beak = C.mat_solid("pigeon_beak", "#4A4744", 0.6)
    foot = C.mat_solid("pigeon_foot", "#B5544B", 0.6)
    body = C.lathe("body", [(0.0, 0.0), (0.038, 0.02), (0.058, 0.075), (0.060, 0.135), (0.045, 0.185), (0.022, 0.215), (0.0, 0.225)],
                   14, material=body_mat, axis="Y", smooth=True)
    body.data.transform(C.Matrix.Diagonal((0.86, 1.0, 1.05, 1.0)))
    C.move(body, 0.0, -0.105, 0.105)
    head = C.lathe("head", [(0.0, 0.0), (0.024, 0.012), (0.032, 0.038), (0.026, 0.062), (0.0, 0.074)], 12,
                   material=neck, axis="Y", smooth=True)
    C.move(head, 0.0, 0.088, 0.163)
    nk = C.tube("neck", [(0.0, 0.055, 0.135), (0.0, 0.085, 0.160)], [0.030, 0.024], 10, material=neck)
    bk = C.lathe("beak", [(0.0, 0.0), (0.008, 0.006), (0.006, 0.020), (0.0, 0.026)], 8, material=beak, axis="Y",
                 origin=(0.0, 0.158, 0.170), smooth=True)
    tail = C.box("tail", (0.052, 0.105, 0.010), origin=(0.0, -0.155, 0.108), material=body_mat, anchor="center")
    C.rotate(tail, 12.0, "X", pivot=(0.0, -0.155, 0.108))
    wings = [C.lathe(f"wing{int(sgn)}", [(0.0, 0.0), (0.030, 0.03), (0.036, 0.10), (0.020, 0.16), (0.0, 0.185)], 8,
                     material=body_mat, axis="Y", smooth=True) for sgn in (-1.0, 1.0)]
    for sgn, wg in zip((-1.0, 1.0), wings):
        wg.data.transform(C.Matrix.Diagonal((0.35, 1.0, 1.0, 1.0)))
        C.move(wg, sgn * 0.048, -0.095, 0.112)
    legs = []
    for sgn in (-1.0, 1.0):
        legs.append(C.tube(f"leg{int(sgn)}", [(sgn * 0.020, -0.055, 0.078), (sgn * 0.024, -0.045, 0.010)], 0.005, 5, material=foot))
        for k in range(3):
            a = math.radians(-30 + 30 * k)
            legs.append(C.tube(f"toe{int(sgn)}{k}", [(sgn * 0.024, -0.045, 0.006),
                                                     (sgn * 0.024 + 0.022 * math.sin(a), -0.045 + 0.026 * math.cos(a), 0.003)],
                               0.0028, 4, material=foot))
    parts = [body, head, nk, bk, tail] + wings + legs
    for o in parts:                       # bring the assembly to the published 0.34 m bill-to-tail length
        o.data.transform(C.Matrix.Diagonal((1.0, 0.87, 1.0, 1.0)))
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"length": 0.34, "height": 0.19, "species": "Columba livia"}})


def build_rat() -> C.Built:
    """Brown rat (Rattus norvegicus): 0.24 m body, 0.20 m tail, 0.09 m at the shoulder — the NYC subway rat."""
    fur = C.mat_solid("rat_fur", "#5A4B40", 0.85)
    skin = C.mat_solid("rat_skin", "#B58C86", 0.7)
    body = C.lathe("body", [(0.0, 0.0), (0.026, 0.02), (0.044, 0.07), (0.048, 0.14), (0.038, 0.20), (0.020, 0.235), (0.0, 0.245)],
                   12, material=fur, axis="Y", smooth=True)
    body.data.transform(C.Matrix.Diagonal((0.92, 1.0, 0.82, 1.0)))
    C.move(body, 0.0, -0.115, 0.045)
    head = C.lathe("head", [(0.020, 0.0), (0.028, 0.018), (0.022, 0.048), (0.012, 0.066), (0.0, 0.072)], 10,
                   material=fur, axis="Y", origin=(0.0, 0.126, 0.048), smooth=True)
    ears = [C.lathe(f"ear{int(sgn)}", [(0.0, 0.0), (0.013, 0.004), (0.011, 0.012)], 8, material=skin,
                    origin=(sgn * 0.020, 0.130, 0.066)) for sgn in (-1.0, 1.0)]
    tail_pts = [(0.0, -0.125 - 0.20 * t, 0.040 - 0.018 * t + 0.020 * math.sin(t * 3.0)) for t in [i / 8 for i in range(9)]]
    tail = C.tube("tail", tail_pts, [0.009 - 0.006 * (i / 8) for i in range(9)], 8, material=skin)
    legs = []
    for sgn in (-1.0, 1.0):
        for tag, y in (("front", 0.075), ("rear", -0.055)):
            legs.append(C.tube(f"leg_{tag}{int(sgn)}", [(sgn * 0.030, y, 0.042), (sgn * 0.034, y - 0.006, 0.004)], 0.007, 5, material=fur))
    whisk = [C.tube(f"whisker{i}", [(0.0, 0.192, 0.050), (s * 0.040, 0.222, 0.050 + dz)], 0.0012, 3, material=skin)
             for i, (s, dz) in enumerate(((-1, 0.010), (1, 0.010), (-1, -0.006), (1, -0.006)))]
    nose = C.lathe("nose", [(0.0, 0.0), (0.006, 0.004), (0.0, 0.008)], 6, material=skin, axis="Y", origin=(0.0, 0.194, 0.048))
    parts = [body, head, tail, nose] + ears + legs + whisk
    for o in parts:                       # bring the assembly to the published 0.44 m nose-to-tail-tip length
        o.data.transform(C.Matrix.Diagonal((1.0, 0.80, 1.0, 1.0)))
    return C.Built(lod0=parts,
                   extra={"key_dims_m": {"nose_to_tail_tip": 0.44, "body_length": 0.24, "shoulder_height": 0.085,
                                         "species": "Rattus norvegicus"}})


SPECS = [
    C.PropSpec("jersey_barrier", "construction", "work_zone_device", build_jersey_barrier, (3.08, 0.61, 0.87),
               "FHWA F-shape precast concrete barrier, 10 ft segment: 24 in base, 32 in tall, 6 in top, with lifting "
               "loops and an end shear key; tileable along X at 3.05 m.",
               variants=["barrel_orange", "traffic_cone", "construction_fence"], tags=["mutcd", "tileable"], tolerance=0.10),
    C.PropSpec("barrel_orange", "construction", "work_zone_device", build_barrel, (0.63, 0.63, 0.914),
               "MUTCD Part 6 channelising drum: 36 in tall, 18 in diameter, alternating orange and white "
               "retroreflective bands on a ballasted rubber base with two carrying handles.",
               variants=["traffic_cone", "jersey_barrier"], tags=["mutcd"], tolerance=0.10),
    C.PropSpec("traffic_cone", "construction", "work_zone_device", build_traffic_cone, (0.356, 0.356, 0.723),
               "MUTCD 28 in traffic cone with two white retroreflective collars on a 14 in ballasted base.",
               variants=["barrel_orange", "jersey_barrier"], tags=["mutcd"], tolerance=0.08),
    C.PropSpec("roadway_plate", "construction", "work_zone_device", build_roadway_plate, (3.24, 4.46, 0.031),
               "Steel roadway plate over a utility cut: 8 x 12 ft x 1 in plate with 0.40 m cold-patch asphalt ramps "
               "on all four edges and four lifting lugs.", tags=["dot"], tolerance=0.10),
    C.PropSpec("sign_roadwork_w20_1", "construction", "road_sign", build_roadwork_sign, (1.73, 1.16, 2.29),
               "MUTCD W20-1 ROAD WORK AHEAD, 48 in orange diamond with a black border and legend on a folding "
               "portable stand, sign bottom at 0.55 m, with two fluorescent warning flags. SIGN_FACE UV spans the "
               "diamond's bounding box.", tags=["mutcd:W20-1"], tolerance=0.10),
    C.PropSpec("construction_fence", "construction", "work_zone_device", build_construction_fence, (2.44, 0.16, 2.49),
               "NYC DOB sidewalk construction fence: 8 ft painted plywood sheet on 4x4 posts with three rails and "
               "angled braces; tileable along X at the 2.438 m sheet pitch.",
               variants=["jersey_barrier"], tags=["dob", "tileable"], tolerance=0.10),
    C.PropSpec("flag_us_pole", "construction", "flagpole", build_flag_us, (1.71, 0.30, 6.21),
               "US flag on a 20 ft satin-aluminium pole with a gold ball finial: 3 x 5 ft flag drawn to Executive "
               "Order 10834 proportions (hoist 1.0 : fly 1.9, union 0.5385 x 0.76, 50 stars in 9 rows of 6-5) on a "
               "waving FLAG_FACE plane.", variants=["flag_nyc_pole"], tags=["flag"], tolerance=0.10),
    C.PropSpec("flag_nyc_pole", "construction", "flagpole", build_flag_nyc, (1.71, 0.30, 6.21),
               "Flag of the City of New York on the same 20 ft pole: blue-white-orange vertical tricolour with the "
               "city seal in blue on the white bar. The seal is drawn as its principal charges (windmill sails "
               "saltire, two beavers, two flour barrels, the date 1625), not the full engraved arms — swap the "
               "FLAG_FACE texture for an exact seal.", variants=["flag_us_pole"], tags=["flag"], tolerance=0.10),
    C.PropSpec("pigeon", "furniture", "fauna", build_pigeon, (0.12, 0.34, 0.19),
               "Rock dove (Columba livia) standing: 0.34 m bill to tail tip (the species is 29-37 cm), 0.19 m tall, grey body with an iridescent "
               "neck and red feet. Static mesh; the engine animates it as a flock actor.",
               variants=["rat"], tags=["fauna"], tolerance=0.15),
    C.PropSpec("rat", "furniture", "fauna", build_rat, (0.09, 0.44, 0.085),
               "Brown rat (Rattus norvegicus): 0.44 m nose to tail tip (0.24 m body plus a 0.20 m tail), 0.085 m at the shoulder. Static mesh.",
               variants=["pigeon"], tags=["fauna"], tolerance=0.15),
]
