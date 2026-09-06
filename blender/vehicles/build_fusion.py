#!/usr/bin/env python3
"""Player car: **2019 Ford Fusion Hybrid** (ADR-009), with the four NYC liveries.

Published dimensions (2019 Ford Fusion, Ford press kit / owner's manual):

===========================  ==============  =========================
quantity                     value           in this blueprint
===========================  ==============  =========================
length                       191.8 in        4 872 mm
width, body (excl. mirrors)   72.9 in        1 852 mm
height                        58.1 in        1 476 mm
wheelbase                    112.2 in        2 850 mm
track, front                  62.4 in        1 585 mm
track, rear                   62.6 in        1 590 mm
tyres                        235/45R18       overall diameter 668.7 mm
minimum ground clearance       5.1 in          130 mm
===========================  ==============  =========================

The two overhangs are not separately published; they are derived from the published length and wheelbase by
splitting the 2 022 mm of total overhang in the ratio the side elevation shows (front 990 mm, rear 1 032 mm),
which reproduces 990 + 2 850 + 1 032 = 4 872 mm exactly.  **Everything else in ``blueprint()`` below is a
control point of a body line**, listed as ``(x_metres, value_metres)`` in the vehicle frame (origin on the
ground under the rear-axle centre, +X forward, +Y left, +Z up).  Each curve is documented where it is defined;
the derivation rules are:

* ``z_top`` must reach exactly 1.476 m (published height) at its peak and nowhere exceed it;
* ``y_max`` must reach exactly 0.926 m (half the published width) and nowhere exceed it;
* the wheel arches are circles of radius 0.42 m about the hub centres (0.3344 m tyre radius + 86 mm gap);
* the windshield and backlight rakes follow from the ``z_top`` control points: 65.2° and 71.3° from the
  vertical respectively, both inside the 2015-2020 Fusion's published range for a "fastback" roofline.

Budgets (brief): LOD0 350 000 triangles including the interior, LOD1 60 000, LOD2 8 000.

Run: ``nice -n 10 python3 blender/vehicles/build_fusion.py [--liveries all] [--detail high]``
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vlib import env  # noqa: E402

env.setup_logging()

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from vlib import blueprint as bp_mod, geom as g, interior as I, materials as M, parts as P, rig, textures as TX  # noqa: E402
from vlib.blueprint import Blueprint, Dimensions, R, curve  # noqa: E402

log = env.log

DIMS = Dimensions(
    length_mm=4872.0, width_mm=1852.0, height_mm=1476.0, wheelbase_mm=2850.0,
    track_front_mm=1585.0, track_rear_mm=1590.0, wheel_diameter_mm=668.7, tyre_width_mm=235.0,
    front_overhang_mm=990.0, rear_overhang_mm=1032.0, rim_diameter_in=18.0, tyre_spec="235/45R18",
    ground_clearance_mm=130.0,
)

# feature stations, metres (rear-axle origin)
X_REAR, X_FRONT = DIMS.x_rear, DIMS.x_front          # -1.032 .. 3.840
X_AXLE_F = DIMS.x_axle_front                          # 2.850
X_COWL = 2.72          # windshield base
X_ROOF_F = 2.00        # header (windshield top)
X_ROOF_R = 0.78        # top of the backlight
X_DECK = 0.02          # base of the backlight = leading edge of the boot lid
X_BUMPER_F = 3.52
X_BUMPER_R = -0.78
DOOR_CUTS = (2.42, 1.34, 0.44)   # front cut, B-pillar cut, rear cut
ARCH_R = 0.42


def blueprint() -> Blueprint:
    """The numeric blueprint.  Every control point is ``(x, z)`` or ``(x, y)`` in metres."""
    return Blueprint(
        name="fusion",
        dims=DIMS,
        # ---- underbody centreline: flat pan over the wheelbase, valances rising at both ends
        z_under=curve((-1.032, 0.400), (-0.85, 0.330), (-0.55, 0.250), (-0.20, 0.190), (0.30, 0.175),
                      (1.20, 0.160), (2.20, 0.150), (2.80, 0.145), (3.25, 0.150), (3.55, 0.170),
                      (3.72, 0.200), (3.84, 0.290)),
        # ---- rocker: bottom edge of the visible side surface between the arches (0.195 m = published 130 mm
        #      clearance + 65 mm of sill section)
        z_rocker=curve((-1.032, 0.430), (-0.80, 0.320), (-0.50, 0.240), (-0.10, 0.205), (0.60, 0.195),
                       (2.00, 0.195), (2.55, 0.210), (3.05, 0.250), (3.45, 0.295), (3.70, 0.300),
                       (3.84, 0.340)),
        # ---- beltline: bottom of the daylight opening; rises 55 mm from the cowl to the boot shoulder
        z_belt=curve((-1.032, 1.010), (-0.60, 1.035), (0.00, 1.030), (0.80, 1.010), (1.40, 0.990),
                     (2.10, 0.975), (2.72, 0.980), (3.10, 0.985), (3.45, 0.960), (3.70, 0.900),
                     (3.84, 0.760)),
        # ---- top centreline: boot lid -> backlight -> roof (peak 1.476 = published height) -> windshield -> hood
        z_top=curve((-1.032, 1.078), (-0.70, 1.118), (-0.30, 1.170), (0.02, 1.205), (0.30, 1.310),
                    (0.55, 1.410), (0.78, 1.462), (1.10, 1.474), (1.40, 1.476), (1.75, 1.470),
                    (2.00, 1.462), (2.25, 1.352), (2.50, 1.230), (2.72, 1.130), (2.95, 1.098),
                    (3.25, 1.058), (3.55, 1.000), (3.72, 0.952), (3.84, 0.880)),
        # ---- half widths
        y_rocker=curve((-1.032, 0.700), (-0.85, 0.790), (-0.50, 0.830), (-0.10, 0.848), (1.00, 0.855),
                       (2.20, 0.855), (2.80, 0.845), (3.20, 0.815), (3.55, 0.780), (3.75, 0.700),
                       (3.84, 0.620)),
        y_max=curve((-1.032, 0.840), (-0.85, 0.885), (-0.50, 0.900), (-0.10, 0.910), (0.60, 0.922),
                    (1.30, 0.926), (2.10, 0.926), (2.70, 0.921), (3.10, 0.905), (3.45, 0.885),
                    (3.68, 0.830), (3.84, 0.720)),
        y_belt=curve((-1.032, 0.790), (-0.80, 0.845), (-0.40, 0.865), (0.10, 0.878), (1.00, 0.890),
                     (2.10, 0.890), (2.72, 0.878), (3.10, 0.890), (3.45, 0.868), (3.68, 0.800),
                     (3.84, 0.670)),
        y_top=curve((-1.032, 0.700), (-0.80, 0.762), (-0.35, 0.778), (0.02, 0.730), (0.35, 0.660),
                    (0.78, 0.618), (1.40, 0.628), (2.00, 0.606), (2.35, 0.690), (2.72, 0.790),
                    (3.05, 0.872), (3.40, 0.845), (3.68, 0.775), (3.84, 0.640)),
        crown=curve((-1.032, 0.018), (-0.50, 0.030), (0.02, 0.048), (0.40, 0.062), (0.78, 0.036),
                    (1.40, 0.028), (2.00, 0.040), (2.35, 0.075), (2.72, 0.070), (3.10, 0.080),
                    (3.50, 0.086), (3.84, 0.076)),
        shoulder_t=curve((-1.032, 0.50), (0.00, 0.60), (1.50, 0.63), (2.85, 0.58), (3.84, 0.50)),
        tumble=curve((-1.032, 0.40), (0.50, 0.55), (2.00, 0.55), (3.00, 0.45), (3.84, 0.40)),
        x_cowl=X_COWL, x_roof_front=X_ROOF_F, x_roof_rear=X_ROOF_R, x_deck=X_DECK, x_hood_rear=X_COWL,
        x_bumper_f=X_BUMPER_F, x_bumper_r=X_BUMPER_R, x_door_cuts=DOOR_CUTS,
        arch_radius_f=ARCH_R, arch_radius_r=ARCH_R, glass_gap=0.055, pillar_a=0.100, pillar_c=0.160,
        n_stations=176,
        notes={
            "overhangs": "front 990 / rear 1032 mm derived from published length 4872 and wheelbase 2850",
            "windshield_rake_deg_from_vertical": "65.2 (z_top 1.130 @ x=2.72 -> 1.462 @ x=2.00)",
            "backlight_rake_deg_from_vertical": "71.3 (z_top 1.205 @ x=0.02 -> 1.462 @ x=0.78)",
            "arch_radius_m": "0.42 = tyre radius 0.3344 + 86 mm arch gap",
            "roof_peak": "1.476 m at x=1.40 equals the published height exactly",
            "max_half_width": "0.926 m at x=1.30..2.10 equals half the published width exactly",
        },
    )


# --------------------------------------------------------------------------- livery definitions
LIVERIES = {
    "player_grey": dict(base="#5A5E63", accent="#2A2C2F", plate="JHK 7391", plate_style="passenger",
                        name="Ford Fusion Hybrid (player)", taxi=None),
    "yellow_taxi": dict(base="#F7B500", accent="#1A1A1A", plate="8B72", plate_style="taxi",
                        name="Ford Fusion Hybrid — NYC medallion taxi", taxi="yellow", medallion="8B72"),
    "black_car": dict(base="#0C0D0F", accent="#0C0D0F", plate="T726512C", plate_style="taxi",
                      name="Ford Fusion Hybrid — TLC black car", taxi=None),
    "green_boro_taxi": dict(base="#6CBE45", accent="#1A1A1A", plate="9C41", plate_style="taxi",
                            name="Ford Fusion Hybrid — Boro (green) taxi", taxi="boro", medallion="9C41"),
}


def paint_atlas(livery: str, spec: dict) -> tuple[TX.Atlas, Path]:
    """Body colour map for one livery, drawn in metres on the shared body atlas."""
    atlas = TX.Atlas(x_min=X_REAR - 0.05, x_max=X_FRONT + 0.05, z_max=1.55, half_width=0.94, size=(2048, 1024))
    base = TX.hex_rgb(spec["base"])
    p = TX.Painter(atlas, base)
    if livery in ("yellow_taxi", "green_boro_taxi"):
        black = (24, 24, 24)
        for region, xsign in (("side_l", 1), ("side_r", 1)):
            # the TLC "T&LC" medallion panel and the NYC roundel on the front doors
            p.text(region, 1.90, 0.72, "NYC", 0.115, black)
            p.text(region, 1.90, 0.60, "TAXI", 0.075, black)
            p.circle(region, 1.55, 0.66, 0.115, black)
            p.text(region, 1.55, 0.66, spec["medallion"], 0.075, TX.hex_rgb(spec["base"]))
            p.text(region, 0.95, 0.42, "NYC.GOV/TAXI  ·  311", 0.038, black)
        p.band(0.195, 0.255, black, sides=True, front=False, rear=False)          # rocker kick strip
        p.text("rear", 0.0, 0.62, "T&LC", 0.070, black)
    elif livery == "black_car":
        p.text("rear", 0.0, 0.55, "", 0.05, (0, 0, 0))
    img = p.save(f"fusion_livery_{livery}")
    return atlas, img


# --------------------------------------------------------------------------- build
def region_materials(lib: M.Library, paint) -> list:
    """One material per :class:`R` region id (indices must line up with the enum)."""
    glass = lib.glass()
    pillar = lib.gloss_black()
    mats = [None] * int(R.N)
    for r in (R.BODY, R.ROOF, R.TRUNK, R.HOOD, R.SILL, R.BUMPER_F, R.BUMPER_R, R.QUARTER,
              R.DOOR_FL, R.DOOR_FR, R.DOOR_RL, R.DOOR_RR, R.DOOR_SL, R.DOOR_SR):
        mats[int(r)] = paint
    mats[int(R.UNDERBODY)] = lib.underside()
    mats[int(R.WELL)] = lib.black_plastic()
    mats[int(R.PILLAR)] = pillar
    for r in bp_mod.GLASS_REGIONS:
        mats[int(r)] = glass
    return mats


SPLIT = {
    "Undertray": [int(R.UNDERBODY)],
    "Hood": [int(R.HOOD)],
    "Trunk": [int(R.TRUNK)],
    "Door_FL": [int(R.DOOR_FL)], "Door_FR": [int(R.DOOR_FR)],
    "Door_RL": [int(R.DOOR_RL)], "Door_RR": [int(R.DOOR_RR)],
    "Window_WS": [int(R.GLASS_WS)], "Window_BACK": [int(R.GLASS_BACK)],
    "Window_FL": [int(R.GLASS_FL)], "Window_FR": [int(R.GLASS_FR)],
    "Window_RL": [int(R.GLASS_RL)], "Window_RR": [int(R.GLASS_RR)],
}


def recess(ob, depth: float = 0.007) -> None:
    """Push a glazing panel inboard along its area-weighted normal (flush glazing reveal)."""
    me = ob.data
    if not me.polygons:
        return
    n = Vector((0, 0, 0))
    for p in me.polygons:
        n += Vector(p.normal) * p.area
    if n.length < 1e-9:
        return
    me.transform(Matrix.Translation(-n.normalized() * depth))
    me.update()


def pivot_bottom_centre(ob) -> None:
    pts = g.mesh_points(ob)
    g.set_origin(ob, (float(pts[:, 0].mean()), float(pts[:, 1].mean()), float(pts[:, 2].min())))


def build(detail: str = "high") -> tuple[rig.Vehicle, dict]:
    """Build the whole car once; livery variants are re-exports with a different paint material."""
    nb = env.nb
    nb.reset_scene()
    lib = M.Library()
    bp = blueprint()
    t = env.Timer()

    # ---------- textures
    sidewall = TX.tyre_sidewall("tyre_235_45R18", size_text="235/45 R18 94V")
    seams = TX.leather_seams("leather_black_seams", panels=7)
    g_speed = TX.gauge_speedo("gauge_speedo_160mph", max_mph=160)
    g_rpm = TX.gauge_tach("gauge_hybrid_power", hybrid=True)
    g_screen = TX.screen_home("screen_center_8in")
    atlas, atlas_img = paint_atlas("player_grey", LIVERIES["player_grey"])
    t.mark("textures")

    paint = lib.livery("BODY_PAINT_player_grey", atlas_img, metallic=0.35, roughness=0.28)
    shell = bp_mod.build_shell(bp, detail=detail, materials=region_materials(lib, paint))
    body = shell.object
    parts_by_name = g.separate_by_material(body, SPLIT)
    body.name = "Body"
    t.mark("shell")

    v = rig.Vehicle(id="fusion_hybrid", display_name=LIVERIES["player_grey"]["name"], vclass="sedan", dims=DIMS,
                    z_belt=0.99, livery="player_grey",
                    sources=["Ford 2019 Fusion published dimensions (ADR-009)"],
                    notes=dict(bp.notes))
    v.add(body)
    v.add_all(parts_by_name)

    # ---------- panel gaps and pivots
    for nm in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Hood", "Trunk"):
        if nm in parts_by_name:
            g.inset_gap(parts_by_name[nm], 0.0045)
    for nm, hx, sgn in (("Door_FL", DOOR_CUTS[0], 1), ("Door_FR", DOOR_CUTS[0], -1),
                        ("Door_RL", DOOR_CUTS[1], 1), ("Door_RR", DOOR_CUTS[1], -1)):
        rig.hinge_door(parts_by_name[nm], hx, sgn * bp.y_max(hx) * 0.92, 0.60)
    rig.hinge_panel(parts_by_name["Hood"], X_COWL - 0.02, bp.z_top(X_COWL) - 0.03)
    rig.hinge_panel(parts_by_name["Trunk"], X_DECK - 0.02, bp.z_top(X_DECK) - 0.03)
    for nm in ("Window_WS", "Window_BACK", "Window_FL", "Window_FR", "Window_RL", "Window_RR"):
        recess(parts_by_name[nm], 0.008)
        pivot_bottom_centre(parts_by_name[nm])
    t.mark("panels")

    # ---------- body UVs (livery atlas) on every painted panel
    painted = [body] + [parts_by_name[n] for n in ("Hood", "Trunk", "Door_FL", "Door_FR", "Door_RL", "Door_RR")]
    for ob in painted:
        g.uv_project(ob, atlas.uv)

    # ---------- wheels and wells
    wheels = P.place_wheels(DIMS, lib, style="alloy10", spokes=10, sidewall_texture=sidewall, disc=True)
    v.add_all(wheels)
    for tag, hx in (("F", X_AXLE_F), ("R", 0.0)):
        for s, sd in ((1, "L"), (-1, "R")):
            v.add(P.wheel_well(f"WheelWell_{tag}{sd}", bp, hx, y_out=bp.y_max(hx) - 0.01, y_in=0.60, lib=lib, side=s))
    t.mark("wheels")

    # ---------- lamps
    head = {}
    for s, tag in ((1, "L"), (-1, "R")):
        head.update(P.headlamp_unit("head", s, lib, x=3.700, y=s * 0.545, z=0.950, w=0.320, h=0.165, rake=-16.0))
    v.add(head["LIGHT_HEAD_L"]); v.add(head["LIGHT_HEAD_R"])
    v.add(head["LIGHT_TURN_FL"]); v.add(head["LIGHT_TURN_FR"])
    v.add(g.join([head["_low_L"], head["_low_R"]], "LIGHT_LOW", sharp_angle_deg=50.0))
    v.add(g.join([head["_high_L"], head["_high_R"]], "LIGHT_HIGH", sharp_angle_deg=50.0))
    v.add(g.join([head["_drl_L"], head["_drl_R"]], "LIGHT_DRL", sharp_angle_deg=50.0))
    tail = {}
    for s in (1, -1):
        tail.update(P.taillamp_unit(s, lib, x=X_REAR + 0.033, y=s * 0.575, z=1.005, w=0.360, h=0.155))
    for k in ("LIGHT_TAIL_L", "LIGHT_TAIL_R", "LIGHT_BRAKE_L", "LIGHT_BRAKE_R", "LIGHT_TURN_RL", "LIGHT_TURN_RR"):
        v.add(tail[k])
    tail["_rev_L"].name = "LIGHT_REVERSE_L"
    tail["_rev_R"].name = "LIGHT_REVERSE_R"
    v.add(tail["_rev_L"]); v.add(tail["_rev_R"])
    v.add(P.plate_light(lib, X_REAR + 0.040, 0.865, 0.0, 0.12))
    # high-mount stop lamp on the boot lid trailing edge
    chmsl = P.lamp_panel("LIGHT_BRAKE_CHMSL", lib.light_red("LIGHT_BRAKE_CHMSL"),
                         [(X_DECK + 0.10, -0.18, bp.z_top(X_DECK + 0.10) + 0.002),
                          (X_DECK + 0.10, 0.18, bp.z_top(X_DECK + 0.10) + 0.002),
                          (X_DECK - 0.02, 0.18, bp.z_top(X_DECK - 0.02) + 0.002),
                          (X_DECK - 0.02, -0.18, bp.z_top(X_DECK - 0.02) + 0.002)], thickness=0.012,
                         inward=(0, 0, -1))
    v.add(chmsl)
    t.mark("lamps")

    # ---------- mirrors, wipers, handles, exhaust, plates, grille, badges
    for s in (1, -1):
        v.add(P.mirror(s, lib, x=2.30, y=s * (bp.y_belt(2.30) - 0.005), z=1.040, w=0.185, h=0.108))
    ws_slope = (bp.z_top(X_ROOF_F) - bp.z_top(X_COWL)) / (X_COWL - X_ROOF_F)     # 0.461 => 65.2 deg rake
    v.add(P.wiper(1, lib, pivot=(X_COWL - 0.05, 0.34, bp.z_top(X_COWL - 0.05) - 0.010),
                  length=0.560, blade=0.600, park_deg=6.0, glass_slope=ws_slope))
    v.add(P.wiper(-1, lib, pivot=(X_COWL - 0.05, -0.42, bp.z_top(X_COWL - 0.05) - 0.010),
                  length=0.480, blade=0.520, park_deg=-6.0, glass_slope=ws_slope))
    v.add(P.exhaust(lib, x_tip=X_REAR + 0.02, y=0.36, z=0.360, r=0.036, length=0.85, tips=2, spacing=0.20))

    plate_img = TX.plate_ny("plate_ny_player", LIVERIES["player_grey"]["plate"])
    v.add(P.plate("Plate_F", lib, plate_img, center=(3.800, 0.0, 0.690), normal=(1, 0, 0.10)))
    v.add(P.plate("Plate_R", lib, plate_img, center=(X_REAR + 0.048, 0.0, 0.735), normal=(-1, 0, -0.05)))

    trim = [lib.gloss_black(), lib.chrome(), lib.black_plastic()]
    grille_bm = P.grille(lib, x=3.760, z0=0.760, z1=0.930, y_half=0.395, bars=5, rake=0.10)
    lower = P.grille(lib, x=3.740, z0=0.420, z1=0.610, y_half=0.480, bars=3, rake=0.06)
    surround = g.set_material_bm(P.grille_surround(3.782, 0.760, 0.930, 0.395, bar=0.026), 1)
    lower_sur = g.set_material_bm(P.grille_surround(3.762, 0.420, 0.610, 0.480, bar=0.020), 2)
    v.add(g.to_object("Grille", g.merge_bm([grille_bm, lower, surround, lower_sur]), trim,
                      smooth=True, sharp_angle_deg=40.0))

    handles = []
    for hx in (2.10, 1.02):
        for s in (1, -1):
            handles.append(P.door_handle(lib, hx, s * (bp.y_belt(hx) + 0.004), bp.z_belt(hx) - 0.115))
    v.add(g.to_object("Handles", g.merge_bm(handles), [lib.satin_alu()], smooth=True, sharp_angle_deg=40.0))

    badges = [P.badge("FUSION", lib, center=(X_REAR + 0.040, 0.42, 0.905), normal=(-1, 0, 0), size=0.038),
              P.badge("HYBRID", lib, center=(X_REAR + 0.040, -0.44, 0.905), normal=(-1, 0, 0), size=0.030),
              g.set_material_bm(g.sphere_bm((0.014, 0.075, 0.048), center=(X_REAR + 0.036, 0.0, 1.010),
                                            segments=18, rings=8), 0)]
    v.add(g.to_object("Badges", g.merge_bm(badges), [lib.chrome()], smooth=True, sharp_angle_deg=40.0))

    fin = g.set_material_bm(g.sphere_bm((0.105, 0.035, 0.062), center=(0.68, 0.0, bp.z_top(0.68) + 0.030),
                                        segments=16, rings=8), 0)
    v.add(g.to_object("Antenna", fin, [lib.paint((0.35, 0.36, 0.38), "ANTENNA_FIN")], smooth=True))
    t.mark("details")

    # ---------- interior
    isp = I.InteriorSpec(
        x_dash=2.40, x_cowl=X_COWL, x_rear=0.30, z_floor=0.345, z_roof=1.395, y_cabin=0.775, z_belt=0.985,
        seats=[I.SeatSpot(x=1.90, y=0.375, z=0.545, name="Seat_FL", back_deg=22.0, width=0.52),
               I.SeatSpot(x=1.90, y=-0.375, z=0.545, name="Seat_FR", back_deg=22.0, width=0.52),
               I.SeatSpot(x=0.98, y=0.0, z=0.585, name="Seat_R", back_deg=26.0, bench=1.34)],
        wheel_center=(2.28, 0.375, 0.865), wheel_radius=0.185, column_deg=25.0, detail="full",
        x_roof_front=X_ROOF_F, roof_line=bp.z_top,
        console=True, shifter="rotary", doors_x=(DOOR_CUTS[0:2], DOOR_CUTS[1:3]),
        gauge_images=(g_speed, g_rpm, g_screen),
    )
    cabin = I.build_interior(isp, lib, seam_texture=seams, x_bpillar=DOOR_CUTS[1])
    v.add_all(cabin)
    # parcel shelf + rear bulkhead so the boot is not visible through the backlight
    shelf = g.box_bm((0.52, 1.34, 0.020), (0.15, 0, 1.008), material_index=0)
    bulk = g.box_bm((0.030, 1.34, 0.48), (0.36, 0, 0.76), material_index=0)
    v.add(g.to_object("Interior_ParcelShelf", g.merge_bm([shelf, bulk]), [lib.fabric(name="FABRIC_SHELF")], smooth=False))
    t.mark("interior")

    # ---------- damage regions + collision
    for nm in ("Body", "Hood", "Trunk", "Door_FL", "Door_FR", "Door_RL", "Door_RR"):
        rig.add_damage_regions(v.objects[nm], DIMS, z_belt=0.99)
    ucx = rig.ucx_proxies("Body", [v.objects["Body"], *[v.objects[n] for n in
                                                        ("Hood", "Trunk", "Door_FL", "Door_FR", "Door_RL", "Door_RR")]],
                          DIMS, z_belt=0.99, slices=6, cabin=True)
    v.add_all(ucx)
    t.mark("dmg+ucx")
    log.info("fusion build timings: %s (total %.1f s)", t.marks, t.total())
    return v, {"atlas": atlas, "paint": paint, "lib": lib, "bp": bp, "timings": dict(t.marks)}


# --------------------------------------------------------------------------- liveries
def apply_livery(v: rig.Vehicle, ctx: dict, livery: str) -> None:
    """Swap the paint texture, plate and roof furniture for one livery, in place."""
    lib: M.Library = ctx["lib"]
    spec = LIVERIES[livery]
    atlas, img = paint_atlas(livery, spec)
    mat = lib.livery(f"BODY_PAINT_{livery}", img, metallic=0.20 if livery != "player_grey" else 0.35,
                     roughness=0.30)
    for ob in v.objects.values():
        if ob.type != "MESH":
            continue
        for i, m in enumerate(ob.data.materials):
            if m is not None and m.name.startswith("BODY_PAINT_"):
                ob.data.materials[i] = mat
    plate_img = TX.plate_ny(f"plate_ny_{livery}", spec["plate"], style=spec["plate_style"])
    pm = M.textured("PLATE_FACE", plate_img, roughness=0.35, coat=0.4)
    pm_img = bpy.data.images.load(str(plate_img), check_existing=True)
    for nm in ("Plate_F", "Plate_R"):
        ob = v.objects[nm]
        for node in ob.data.materials[0].node_tree.nodes:
            if node.type == "TEX_IMAGE":
                node.image = pm_img
    # roof furniture
    for nm in ("TAXI_ROOF",):
        if nm in v.objects:
            g.remove_object(v.objects.pop(nm))
    if spec["taxi"]:
        med = TX.taxi_roof_light(f"taxi_roof_{livery}", spec["medallion"], boro=spec["taxi"] == "boro")
        box = P.taxi_roof_light(lib, x=1.30, z=1.476, medallion_image=med, w=0.62, h=0.115, d=0.20)
        v.add(box)
    v.id = "fusion_hybrid" if livery == "player_grey" else f"fusion_{livery}"
    v.display_name = spec["name"]
    v.livery = livery
    v.base_id = None if livery == "player_grey" else "fusion_hybrid"
    v.extra_slots = ("TAXI_ROOF",) if spec["taxi"] else ()


EXTERIOR = [
    "Body", "Hood", "Trunk", "Door_FL", "Door_FR", "Door_RL", "Door_RR", "Undertray",
    "Window_WS", "Window_BACK", "Window_FL", "Window_FR", "Window_RL", "Window_RR",
    "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR", "WheelWell_FL", "WheelWell_FR", "WheelWell_RL", "WheelWell_RR",
    "LIGHT_HEAD_L", "LIGHT_HEAD_R", "LIGHT_LOW", "LIGHT_HIGH", "LIGHT_DRL", "LIGHT_TURN_FL", "LIGHT_TURN_FR",
    "LIGHT_TAIL_L", "LIGHT_TAIL_R", "LIGHT_BRAKE_L", "LIGHT_BRAKE_R", "LIGHT_TURN_RL", "LIGHT_TURN_RR",
    "LIGHT_REVERSE_L", "LIGHT_REVERSE_R", "LIGHT_PLATE", "LIGHT_BRAKE_CHMSL",
    "Mirror_L", "Mirror_R", "Wiper_L", "Wiper_R", "Grille", "Handles", "Badges", "Antenna", "Exhaust",
    "Plate_F", "Plate_R", "TAXI_ROOF",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--liveries", default="all", help="comma-separated livery ids, or 'all'")
    ap.add_argument("--detail", default="high", choices=("high", "mid", "low"))
    ap.add_argument("--keep-blend", default="", help="save the .blend here (debugging)")
    args = ap.parse_args()
    env.ensure_dirs()
    wanted = list(LIVERIES) if args.liveries == "all" else args.liveries.split(",")

    v, ctx = build(detail=args.detail)
    tris = g.tri_count_all([o for o in v.objects.values() if o.type == "MESH" and not o.name.startswith("UCX_")])
    log.info("LOD0 triangles = %d (budget 350000)", tris)
    if tris > 350_000:
        raise RuntimeError(f"LOD0 over budget: {tris} > 350000")

    entries = []
    for livery in wanted:
        apply_livery(v, ctx, livery)
        entries.append(rig.finalise(v, lod_budgets=(60_000, 8_000),
                                    exterior_names=[n for n in EXTERIOR if n in v.objects],
                                    extra_catalog={"blueprint_control_points": {
                                        "z_top": list(zip(ctx["bp"].z_top.xs.tolist(), ctx["bp"].z_top.vs.tolist())),
                                        "y_max": list(zip(ctx["bp"].y_max.xs.tolist(), ctx["bp"].y_max.vs.tolist())),
                                        "z_belt": list(zip(ctx["bp"].z_belt.xs.tolist(), ctx["bp"].z_belt.vs.tolist())),
                                        "door_cuts_x": list(DOOR_CUTS),
                                        "feature_x": {"cowl": X_COWL, "roof_front": X_ROOF_F, "roof_rear": X_ROOF_R,
                                                      "deck": X_DECK, "bumper_f": X_BUMPER_F, "bumper_r": X_BUMPER_R},
                                    }, "build_timings_s": ctx["timings"]}))
    if args.keep_blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.keep_blend)
    for e in entries:
        print(f"{e['id']:>26s}  {e['triangles']:>7d} tris  "
              f"LOD1 {e['lods'][1]['triangles']:>6d}  LOD2 {e['lods'][2]['triangles']:>5d}  "
              f"dev L/W/H {e['dimension_deviation_pct']['length_pct']:+.2f}/"
              f"{e['dimension_deviation_pct']['width_pct']:+.2f}/{e['dimension_deviation_pct']['height_pct']:+.2f} %")
    return 0


if __name__ == "__main__":
    code = main()
    env.finish(code)
