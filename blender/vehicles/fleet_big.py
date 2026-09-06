#!/usr/bin/env python3
"""Buses, coaches, trucks, emergency and delivery vehicles (ADR-009).

Each spec function's docstring carries the published dimensions it is built from.  Bodies are box-section
lofts (:func:`vlib.fleetlib.box_table`); the glazing of a flat-front vehicle is placed with the blueprint's
``front_glass`` / ``rear_glass`` / ``side_glass_spans`` apertures rather than a car-style roof rake.

Run: ``nice -n 10 python3 blender/vehicles/fleet_big.py [--only nova_lfs,xd60,...]``
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vlib import env  # noqa: E402

env.setup_logging()

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from vlib import fleetlib as F, geom as g, materials as M, parts as P, rig, textures as TX  # noqa: E402
from vlib.blueprint import Dimensions, R  # noqa: E402
from vlib.fleetlib import FleetSpec, LampBox  # noqa: E402

log = env.log

MTA_BLUE = "#0039A6"
MTA_WHITE = "#E8EAEC"
SBS_BLUE = "#00558C"
FDNY_RED = "#B3001B"
DSNY_WHITE = "#D8DBDD"
CONED_BLUE = "#005CA9"
SCHOOL_YELLOW = "#F5C400"
USPS_WHITE = "#E5E7E9"


# --------------------------------------------------------------------------- helpers
def bus_signs(v, lib, *, front, side, rear, text_front, text_side, text_rear, route: str) -> None:
    """``SIGN_FRONT`` / ``SIGN_SIDE`` / ``SIGN_REAR`` LED destination panels (UV exactly 0..1)."""
    imgs = {
        "SIGN_FRONT": TX.led_sign(f"sign_front_{route}", text_front, w=1024, h=192, sub=route),
        "SIGN_SIDE": TX.led_sign(f"sign_side_{route}", text_side, w=1024, h=160),
        "SIGN_REAR": TX.led_sign(f"sign_rear_{route}", text_rear, w=512, h=256),
    }
    for name, corners in (("SIGN_FRONT", front), ("SIGN_SIDE", side), ("SIGN_REAR", rear)):
        if corners is not None:
            v.add(P.destination_sign(name, lib, imgs[name], corners))


def roof_hvac(v, lib, *, x0: float, x1: float, z: float, w: float = 1.55, h: float = 0.22) -> None:
    parts = [g.rounded_box_bm((x1 - x0, w, h), 0.05, segments=2, center=(0.5 * (x0 + x1), 0, z + h / 2))]
    for k in range(4):
        parts.append(g.box_bm(((x1 - x0) * 0.16, w * 0.9, 0.02), (x0 + (x1 - x0) * (0.2 + 0.2 * k), 0, z + h)))
    v.add(g.to_object("RoofHVAC", g.merge_bm(parts), [lib.steel_painted((0.62, 0.63, 0.64), "HVAC_SHROUD")],
                      smooth=False))


def stripe(v, lib, name: str, hexcol: str, x0: float, x1: float, z0: float, z1: float, y: float) -> None:
    mat = lib.paint(M.srgb_hex(hexcol)[:3], f"STRIPE_{name}", metallic=0.1, roughness=0.35)
    parts = []
    for s in (1, -1):
        c = [(x0, s * y, z0), (x1, s * y, z0), (x1, s * y, z1), (x0, s * y, z1)]
        parts.append(g.quad_uv01_bm(c if s > 0 else list(reversed(c))))
    v.add(g.to_object(f"Stripe_{name}", g.merge_bm(parts), [mat], smooth=False))


# --------------------------------------------------------------------------- Nova Bus LFS 40 ft
def nova_lfs() -> FleetSpec:
    """**Nova Bus LFS 40 ft** — MTA New York City Transit local bus.

    Published: length 12 192 mm (40 ft), width 2 591 mm (102 in), height 3 200 mm over the roof shroud,
    wheelbase 7 100 mm, tyres 305/70R22.5 (overall diameter 998.5 mm).  Overhangs 2 700 / 2 392 mm.
    """
    d = Dimensions(length_mm=12192, width_mm=2591, height_mm=3200, wheelbase_mm=7100,
                   track_front_mm=2100, track_rear_mm=1850, wheel_diameter_mm=998.5, tyre_width_mm=305,
                   front_overhang_mm=2700, rear_overhang_mm=2392, rim_diameter_in=22.5, tyre_spec="305/70R22.5",
                   ground_clearance_mm=180)
    tbl = F.box_table(d, z_under=0.290, z_rocker=0.330, z_belt=1.760, z_top=3.100,
                      y_rocker=1.240, y_max=1.2955, y_belt=1.280, y_top=1.120, crown=0.075,
                      x_cowl=9.30, nose_len=0.30, tail_len=0.28, nose_z_top=3.020, nose_z_belt=1.700,
                      tail_z_top=3.040, nose_y=0.88, tail_y=0.90, y_top_front=1.170, skirt=0.06)

    def extras(v, lib, bp):
        roof_hvac(v, lib, x0=-1.60, x1=3.20, z=3.100, w=1.90, h=0.10)
        bus_signs(v, lib,
                  front=[(9.79, -0.86, 2.70), (9.79, 0.86, 2.70), (9.79, 0.86, 2.94), (9.79, -0.86, 2.94)],
                  side=[(8.40, 1.298, 2.34), (6.60, 1.298, 2.34), (6.60, 1.298, 2.52), (8.40, 1.298, 2.52)],
                  rear=[(-2.396, 0.42, 2.62), (-2.396, -0.42, 2.62), (-2.396, -0.42, 2.86), (-2.396, 0.42, 2.86)],
                  text_front="14TH ST", text_side="M14A SELECT", text_rear="M14A", route="M14A")
        stripe(v, lib, "MTA", MTA_BLUE, -2.30, 9.30, 1.20, 1.62, 1.297)
        # kerb-side door leaves are the only ones that exist; add the step wells and grab poles inside
        poles = []
        for px in (7.90, 2.10):
            poles.append(g.tube_bm([(px, -1.05, 0.42), (px, -1.05, 2.90)], 0.022, segments=8))
            poles.append(g.tube_bm([(px, 1.05, 0.42), (px, 1.05, 2.90)], 0.022, segments=8))
        v.add(g.to_object("GrabPoles", g.merge_bm(poles), [lib.steel_painted((0.75, 0.76, 0.78), "POLE_STAINLESS")],
                          smooth=True, sharp_angle_deg=50.0))
        # bench seating along the saloon
        seat_mat = [lib.fabric((0.10, 0.13, 0.22), "FABRIC_TRANSIT_SEAT"), lib.black_plastic()]
        seats = []
        for k in range(9):
            sx = -1.90 + k * 0.72
            for s in (1, -1):
                seats.append(g.rounded_box_bm((0.46, 0.90, 0.075), 0.03, segments=1,
                                              center=(sx, s * 0.82, 1.02), material_index=0))
                seats.append(g.rounded_box_bm((0.075, 0.90, 0.52), 0.03, segments=1,
                                              center=(sx - 0.20, s * 0.82, 1.30), material_index=0))
        v.add(g.to_object("Seats_Transit", g.merge_bm(seats), seat_mat, smooth=False))

    return FleetSpec(
        id="nova_lfs_mta", name="Nova Bus LFS 40 ft — MTA New York City Transit", vclass="bus", dims=d, table=tbl,
        x_cowl=9.30, x_roof_front=9.55, x_roof_rear=-2.10, x_deck=-2.30, x_bumper_f=9.60, x_bumper_r=-2.30,
        door_cuts=(8.55, 7.35, 1.60), head=LampBox(9.76, 1.02, 0.95, 0.36, 0.30, 0.0),
        tail=LampBox(-2.386, 1.06, 1.20, 0.28, 0.62), paint=MTA_WHITE,
        arch_r_f=0.62, arch_r_r=0.62, wheel_style="truck", tyre_text="305/70 R22.5",
        n_stations=120, detail="mid", dual_rear=True,
        front_glass=(8.90, 1.80, 2.66), rear_glass=(-1.95, 1.90, 2.55),
        side_glass_spans=((6.90, 1.75, int(R.GLASS_FL)), (1.20, -1.95, int(R.GLASS_RL))),
        kerb_side_doors_only=True,
        waivers={"Trunk": "a transit bus has no boot lid or tailgate; the engine bay is reached through a hinged rear cap that is part of Body",
                 "Door_FL": "Nova LFS has passenger doors on the kerb (right) side only",
                 "Door_RL": "Nova LFS has passenger doors on the kerb (right) side only",
                 "Window_RL": "no left-side door glazing; the saloon glass is Window_RR/Window_FR",
                 "Window_FL": "no left-side door glazing; the saloon glass is Window_RR/Window_FR"},
        interior="cab", cab=(8.50, 1.00, 8.98, 1.52, 0.72, 68.0), z_floor=0.40, mirror_x=9.10, mirror_arm=0.26, mirror_size=(0.24, 0.42, 0.10),
        wiper_len=0.90, wiper_blade=1.05, plate_front=False,
        extras=extras, extra_slots=("SIGN_FRONT", "SIGN_SIDE", "SIGN_REAR"),
        lod_budgets=(40_000, 6_000),
        sources=["Nova Bus LFS published dimensions; MTA NYCT 40-foot bus fleet"],
        notes={"role": "MTA local bus (ADR-009)",
               "interior": "transit saloon: benches + stanchions, no cab dash (the driver's area is modelled "
                           "as part of the body; Interior_Dash is waived for this class)"},
    )


# --------------------------------------------------------------------------- New Flyer XD60
def xd60() -> FleetSpec:
    """**New Flyer Xcelsior XD60** — MTA articulated bus in Select Bus Service livery.

    Published: length 18 593 mm (60 ft 11 in), width 2 591 mm (102 in), height 3 200 mm,
    axle spread 13 691 mm (front to rear axle; middle axle 6 706 mm ahead of the rear),
    tyres 305/70R22.5.  Overhangs 2 650 / 2 252 mm.

    Fidelity note: the articulation joint is modelled as a bellows band in the body; the two halves are one
    rigid mesh (the engine articulates AI buses by swapping to a two-part actor, not by deforming this glb).
    """
    d = Dimensions(length_mm=18593, width_mm=2591, height_mm=3200, wheelbase_mm=13691,
                   track_front_mm=2100, track_rear_mm=1850, wheel_diameter_mm=998.5, tyre_width_mm=305,
                   front_overhang_mm=2650, rear_overhang_mm=2252, rim_diameter_in=22.5, tyre_spec="305/70R22.5",
                   ground_clearance_mm=180)
    tbl = F.box_table(d, z_under=0.290, z_rocker=0.330, z_belt=1.760, z_top=3.100,
                      y_rocker=1.240, y_max=1.2955, y_belt=1.280, y_top=1.120, crown=0.075,
                      x_cowl=15.90, nose_len=0.30, tail_len=0.28, nose_z_top=3.020, nose_z_belt=1.700,
                      tail_z_top=3.040, nose_y=0.88, tail_y=0.90, y_top_front=1.170, skirt=0.06)

    def extras(v, lib, bp):
        roof_hvac(v, lib, x0=1.20, x1=5.60, z=3.100, w=1.90, h=0.10)
        bus_signs(v, lib,
                  front=[(16.39, -0.86, 2.70), (16.39, 0.86, 2.70), (16.39, 0.86, 2.94), (16.39, -0.86, 2.94)],
                  side=[(15.0, 1.298, 2.34), (13.2, 1.298, 2.34), (13.2, 1.298, 2.52), (15.0, 1.298, 2.52)],
                  rear=[(-2.256, 0.42, 2.62), (-2.256, -0.42, 2.62), (-2.256, -0.42, 2.86), (-2.256, 0.42, 2.86)],
                  text_front="34 ST HUDSON YDS", text_side="+SelectBusService M34A", text_rear="M34A",
                  route="M34A-SBS")
        # SBS livery: dark-blue lower band with a light-blue flash
        stripe(v, lib, "SBS_LOWER", SBS_BLUE, -2.25, 16.0, 0.34, 1.35, 1.297)
        stripe(v, lib, "SBS_FLASH", "#8CC8E8", -2.25, 16.0, 1.35, 1.50, 1.297)
        # articulation bellows at the joint (x = 3.40, between the middle and rear axles)
        bel = []
        for k in range(9):
            bx = 3.40 + (k - 4) * 0.075
            r = 1.30 if k % 2 == 0 else 1.255
            bel.append(g.torus_bm(0.9, 0.055, axis="X", center=(bx, 0, 1.72), segments=28, ring_segments=6))
        v.add(g.to_object("Bellows", g.merge_bm(bel), [lib.rubber()], smooth=True, sharp_angle_deg=50.0))
        poles = []
        for px in (14.6, 9.0, 1.2):
            for s in (1, -1):
                poles.append(g.tube_bm([(px, s * 1.05, 0.42), (px, s * 1.05, 2.90)], 0.022, segments=8))
        v.add(g.to_object("GrabPoles", g.merge_bm(poles), [lib.steel_painted((0.75, 0.76, 0.78), "POLE_STAINLESS")],
                          smooth=True, sharp_angle_deg=50.0))

    return FleetSpec(
        id="xd60_sbs", name="New Flyer XD60 articulated — MTA Select Bus Service", vclass="bus", dims=d, table=tbl,
        x_cowl=15.90, x_roof_front=16.15, x_roof_rear=-2.05, x_deck=-2.20, x_bumper_f=16.20, x_bumper_r=-2.20,
        door_cuts=(15.15, 13.95, 8.20), head=LampBox(16.36, 1.02, 0.95, 0.36, 0.30, 0.0),
        tail=LampBox(-2.246, 1.06, 1.20, 0.28, 0.62), paint=MTA_WHITE,
        arch_r_f=0.62, arch_r_r=0.62, wheel_style="truck", tyre_text="305/70 R22.5",
        x_axle_rear_extra=(6.706,), n_stations=150, detail="mid", dual_rear=True,
        front_glass=(15.50, 1.80, 2.66), rear_glass=(-1.85, 1.90, 2.55),
        side_glass_spans=((13.50, 8.40, int(R.GLASS_FL)), (7.80, -1.90, int(R.GLASS_RL))),
        kerb_side_doors_only=True,
        waivers={"Trunk": "an articulated bus has no boot lid or tailgate",
                 "Door_FL": "XD60 has passenger doors on the kerb (right) side only",
                 "Door_RL": "XD60 has passenger doors on the kerb (right) side only",
                 "Window_FL": "no left-side door glazing", "Window_RL": "no left-side door glazing"},
        interior="cab", cab=(15.10, 1.00, 15.58, 1.52, 0.72, 68.0), z_floor=0.40, mirror_x=15.70, mirror_arm=0.26, mirror_size=(0.24, 0.42, 0.10),
        wiper_len=0.90, wiper_blade=1.05, plate_front=False,
        extras=extras, extra_slots=("SIGN_FRONT", "SIGN_SIDE", "SIGN_REAR"),
        lod_budgets=(40_000, 6_000),
        sources=["New Flyer Xcelsior XD60 published dimensions; MTA Select Bus Service livery"],
        notes={"articulation": "modelled as a rigid body with a bellows band; see the docstring",
               "role": "MTA SBS articulated bus (ADR-009)"},
    )


# --------------------------------------------------------------------------- MCI coach
def mci_coach() -> FleetSpec:
    """**MCI J4500 45 ft motorcoach** — intercity coach (Port Authority / charter).

    Published: length 13 716 mm (45 ft), width 2 591 mm (102 in), height 3 594 mm (141.5 in),
    front axle to drive axle 7 950 mm, tag axle 1 450 mm behind the drive axle, tyres 315/80R22.5
    (overall diameter 1 075.5 mm).  Origin is the rearmost (tag) axle per DATA_CONTRACTS §13.
    """
    d = Dimensions(length_mm=13716, width_mm=2591, height_mm=3594, wheelbase_mm=9400,
                   track_front_mm=2130, track_rear_mm=1860, wheel_diameter_mm=1075.5, tyre_width_mm=315,
                   front_overhang_mm=2050, rear_overhang_mm=2266, rim_diameter_in=22.5, tyre_spec="315/80R22.5",
                   ground_clearance_mm=280)
    tbl = F.box_table(d, z_under=0.420, z_rocker=0.480, z_belt=2.150, z_top=3.560,
                      y_rocker=1.230, y_max=1.2955, y_belt=1.285, y_top=1.100, crown=0.090,
                      x_cowl=10.80, nose_len=0.36, tail_len=0.30, nose_z_top=3.400, nose_z_belt=2.050,
                      tail_z_top=3.420, nose_y=0.86, tail_y=0.90, y_top_front=1.160, skirt=0.05)

    def extras(v, lib, bp):
        bus_signs(v, lib,
                  front=[(11.44, -0.80, 3.10), (11.44, 0.80, 3.10), (11.44, 0.80, 3.32), (11.44, -0.80, 3.32)],
                  side=None,
                  rear=[(-2.266, 0.40, 3.05), (-2.266, -0.40, 3.05), (-2.266, -0.40, 3.27), (-2.266, 0.40, 3.27)],
                  text_front="NEW YORK", text_side="", text_rear="NYC", route="COACH")
        # luggage-bay doors along the skirt
        bays = []
        for s in (1, -1):
            for k, bx in enumerate((7.6, 5.9, 2.2, 0.4)):
                bays.append(g.box_bm((1.45, 0.05, 0.72), (bx, s * 1.288, 1.12)))
        v.add(g.to_object("LuggageBays", g.merge_bm(bays), [lib.brushed_metal()], smooth=False))

    return FleetSpec(
        id="mci_j4500_coach", name="MCI J4500 45 ft motorcoach", vclass="bus", dims=d, table=tbl,
        x_cowl=10.80, x_roof_front=11.05, x_roof_rear=-2.00, x_deck=-2.20, x_bumper_f=11.20, x_bumper_r=-2.20,
        door_cuts=(10.20, 9.10, 8.40), head=LampBox(11.40, 1.05, 1.10, 0.40, 0.32, 0.0),
        tail=LampBox(-2.256, 1.08, 1.55, 0.30, 0.60), paint="#D9DCDF",
        arch_r_f=0.660, arch_r_r=0.660, wheel_style="truck", tyre_text="315/80 R22.5",
        x_axle_rear_extra=(1.45,), n_stations=130, detail="mid", dual_rear=True,
        front_glass=(10.40, 2.20, 3.06), rear_glass=(-1.90, 2.30, 3.00),
        side_glass_spans=((10.15, 9.15, int(R.GLASS_FL)), (8.20, -1.90, int(R.GLASS_RL))),
        kerb_side_doors_only=True,
        waivers={"Trunk": "a coach has luggage-bay doors (LuggageBays), not a boot lid",
                 "Door_FL": "coach entrance door is on the kerb (right) side only",
                 "Door_RL": "coach has a single entrance door", "Door_RR": "coach has a single entrance door",
                 "Window_FL": "no left-side door glazing", "Window_RL": "saloon glazing is Window_RR"},
        interior="cab", cab=(10.10, 1.86, 10.58, 2.36, 0.72, 66.0), z_floor=1.30, mirror_x=10.60, mirror_arm=0.28, mirror_size=(0.24, 0.44, 0.10),
        wiper_len=0.95, wiper_blade=1.15, plate_front=False,
        extras=extras, extra_slots=("SIGN_FRONT", "SIGN_REAR"),
        lod_budgets=(40_000, 6_000),
        sources=["MCI J4500 published dimensions"],
        notes={"role": "intercity coach (ADR-009)", "axles": "tag axle at the origin, drive axle +1.45 m"},
    )


# --------------------------------------------------------------------------- Seagrave pumper
def seagrave_engine() -> FleetSpec:
    """**Seagrave Marauder II pumper** — FDNY Engine company.

    Published (Seagrave Marauder II custom pumper on a 184 in wheelbase): length 9 750 mm (32 ft),
    width 2 591 mm (102 in), height 3 100 mm, wheelbase 4 674 mm, tyres 315/80R22.5.
    """
    d = Dimensions(length_mm=9750, width_mm=2591, height_mm=3100, wheelbase_mm=4674,
                   track_front_mm=2080, track_rear_mm=1860, wheel_diameter_mm=1075.5, tyre_width_mm=315,
                   front_overhang_mm=1900, rear_overhang_mm=3176, rim_diameter_in=22.5, tyre_spec="315/80R22.5",
                   ground_clearance_mm=250)
    tbl = F.box_table(d, z_under=0.420, z_rocker=0.520, z_belt=1.900, z_top=2.900,
                      y_rocker=1.220, y_max=1.2955, y_belt=1.280, y_top=1.140, crown=0.050,
                      x_cowl=5.60, nose_len=0.34, tail_len=0.26, nose_z_top=2.760, nose_z_belt=1.820,
                      tail_z_top=2.860, nose_y=0.90, tail_y=0.94, y_top_front=1.190)

    def extras(v, lib, bp):
        v.add(P.light_bar(lib, x=5.10, z=2.900, w=1.90, h=0.130, d=0.34, modules=10))
        alu = lib.diamond_plate()
        steel = lib.steel_painted((0.72, 0.73, 0.74), "PUMP_PANEL")
        parts = []
        # pump panel amidships, hose bed on top, compartment doors along the body
        parts.append(g.box_bm((1.05, 2.58, 0.95), (3.40, 0, 1.55)))
        for s in (1, -1):
            for bx in (1.90, 0.75, -0.45, -1.70):
                parts.append(g.box_bm((1.00, 0.055, 1.10), (bx, s * 1.292, 1.50)))
        v.add(g.to_object("BodyCompartments", g.merge_bm(parts), [steel], smooth=False))
        hose = [g.box_bm((3.10, 1.70, 0.55), (-0.60, 0, 2.70))]
        for k in range(10):
            hose.append(g.cylinder_bm(0.055, 1.60, axis="Y", center=(-2.00 + k * 0.30, 0, 3.03), segments=10))
        v.add(g.to_object("HoseBed", g.merge_bm(hose), [alu], smooth=False))
        v.add(g.to_object("Ladder", P.ladder_rungs(-2.10, 2.60, 1.20, 2.66, 2.66, 14),
                          [lib.brushed_metal()], smooth=False))
        # FDNY gold-leaf style lettering (generated, not traced artwork)
        dec = TX.wordmark("fdny_door", "FDNY", w=1024, h=320, fg=(240, 205, 110))
        num = TX.wordmark("fdny_engine", "ENGINE 54", w=1024, h=256, fg=(240, 205, 110))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.296
            c1 = [(5.30, y, 1.55), (4.15, y, 1.55), (4.15, y, 1.92), (5.30, y, 1.92)]
            c2 = [(2.40, y, 2.05), (0.30, y, 2.05), (0.30, y, 2.35), (2.40, y, 2.35)]
            v.add(g.to_object(f"Decal_FDNY_{tag}", g.quad_uv01_bm(c1 if s > 0 else list(reversed(c1))),
                              [lib.decal("DECAL_FDNY", dec)], smooth=False))
            v.add(g.to_object(f"Decal_Company_{tag}", g.quad_uv01_bm(c2 if s > 0 else list(reversed(c2))),
                              [lib.decal("DECAL_COMPANY", num)], smooth=False))

    return FleetSpec(
        id="seagrave_engine_fdny", name="Seagrave Marauder II pumper — FDNY Engine", vclass="emergency",
        dims=d, table=tbl,
        x_cowl=5.60, x_roof_front=5.85, x_roof_rear=4.30, x_deck=4.10, x_bumper_f=6.10, x_bumper_r=-3.10,
        door_cuts=(5.35, 4.30, 3.90), head=LampBox(6.42, 1.05, 1.20, 0.34, 0.30, 0.0),
        tail=LampBox(-3.166, 1.08, 1.35, 0.30, 0.55), paint=FDNY_RED,
        arch_r_f=0.660, arch_r_r=0.660, wheel_style="truck", tyre_text="315/80 R22.5",
        n_stations=110, detail="mid", dual_rear=True,
        front_glass=(5.75, 2.05, 2.74), rear_glass=None,
        side_glass_spans=((5.30, 4.35, int(R.GLASS_FL)),),
        interior="cab", cab=(5.15, 1.42, 5.52, 1.92, 0.60, 55.0), z_floor=0.95, mirror_x=5.55, mirror_arm=0.30, mirror_size=(0.24, 0.44, 0.10),
        wiper_len=0.80, wiper_blade=0.95, plate_front=False,
        extras=extras,
        extra_slots=("LIGHT_EMERGENCY_R", "LIGHT_EMERGENCY_B", "LIGHT_EMERGENCY_W"),
        waivers={"Door_RL": "pumper crew cab has one door per side", "Door_RR": "pumper crew cab has one door per side",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "no rear window: the body is a hose bed"},
        lod_budgets=(40_000, 6_000),
        sources=["Seagrave Marauder II published dimensions; FDNY engine company configuration"],
        notes={"role": "FDNY Engine (ADR-009)",
               "fidelity": "recognisable pumper silhouette with pump panel, hose bed, ladder and light bar; "
                           "no discharge/intake plumbing detail"},
    )


# --------------------------------------------------------------------------- Seagrave tower ladder
def seagrave_tower() -> FleetSpec:
    """**Seagrave Aerialscope 75 ft tower ladder** — FDNY Ladder company.

    Published: length 12 500 mm (41 ft), width 2 591 mm (102 in), height 3 350 mm travelling,
    front axle 6 350 mm ahead of the rear axle, tandem second axle 1 550 mm ahead of the rear axle,
    tyres 315/80R22.5.  Overhangs 2 050 / 4 100 mm.
    """
    d = Dimensions(length_mm=12500, width_mm=2591, height_mm=3350, wheelbase_mm=6350,
                   track_front_mm=2080, track_rear_mm=1860, wheel_diameter_mm=1075.5, tyre_width_mm=315,
                   front_overhang_mm=2050, rear_overhang_mm=4100, rim_diameter_in=22.5, tyre_spec="315/80R22.5",
                   ground_clearance_mm=250)
    tbl = F.box_table(d, z_under=0.420, z_rocker=0.520, z_belt=1.900, z_top=2.700,
                      y_rocker=1.220, y_max=1.2955, y_belt=1.280, y_top=1.150, crown=0.040,
                      x_cowl=7.30, nose_len=0.34, tail_len=0.26, nose_z_top=2.640, nose_z_belt=1.820,
                      tail_z_top=2.660, nose_y=0.90, tail_y=0.94, y_top_front=1.195)

    def extras(v, lib, bp):
        v.add(P.light_bar(lib, x=6.80, z=2.700, w=1.90, h=0.130, d=0.34, modules=10))
        alu = lib.diamond_plate()
        # turntable, boom (stowed) and the platform: a 75 ft (22.9 m) telescopic boom is stowed over the body
        parts = [g.cylinder_bm(0.85, 0.40, axis="Z", center=(1.40, 0, 2.72), segments=28)]
        boom = []
        for k, (ln, w, h, z) in enumerate(((8.6, 0.72, 0.62, 2.98), (7.4, 0.60, 0.52, 2.99), (6.4, 0.50, 0.44, 3.00))):
            boom.append(g.box_bm((ln, w, h), (1.40 - ln / 2 + k * 0.35, 0, z)))
        v.add(g.to_object("AerialBoom", g.merge_bm(boom), [lib.steel_painted((0.72, 0.73, 0.74), "BOOM_STEEL")],
                          smooth=False))
        parts.append(g.box_bm((1.10, 1.90, 0.95), (-3.10, 0, 2.82)))          # the bucket, stowed at the tail
        v.add(g.to_object("Turntable", g.merge_bm(parts), [alu], smooth=False))
        outr = []
        for s in (1, -1):
            outr.append(g.box_bm((0.55, 0.70, 0.34), (2.60, s * 0.90, 0.72)))
            outr.append(g.box_bm((0.55, 0.70, 0.34), (0.20, s * 0.90, 0.72)))
        v.add(g.to_object("Outriggers", g.merge_bm(outr), [alu], smooth=False))
        dec = TX.wordmark("fdny_ladder", "LADDER 4", w=1024, h=256, fg=(240, 205, 110))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.296
            c = [(6.90, y, 1.55), (4.90, y, 1.55), (4.90, y, 1.90), (6.90, y, 1.90)]
            v.add(g.to_object(f"Decal_Company_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_LADDER", dec)], smooth=False))

    return FleetSpec(
        id="seagrave_tower_fdny", name="Seagrave Aerialscope 75 ft tower ladder — FDNY", vclass="emergency",
        dims=d, table=tbl,
        x_cowl=7.30, x_roof_front=7.55, x_roof_rear=6.00, x_deck=5.80, x_bumper_f=7.80, x_bumper_r=-4.05,
        door_cuts=(7.05, 6.00, 5.60), head=LampBox(8.12, 1.05, 1.20, 0.34, 0.30, 0.0),
        tail=LampBox(-4.090, 1.08, 1.35, 0.30, 0.55), paint=FDNY_RED,
        arch_r_f=0.660, arch_r_r=0.660, wheel_style="truck", tyre_text="315/80 R22.5",
        x_axle_rear_extra=(1.55,), n_stations=120, detail="mid", dual_rear=True,
        front_glass=(7.45, 2.05, 2.56), rear_glass=None,
        side_glass_spans=((7.00, 6.05, int(R.GLASS_FL)),),
        interior="cab", cab=(6.85, 1.42, 7.22, 1.92, 0.60, 55.0), z_floor=0.95, mirror_x=7.25, mirror_arm=0.30, mirror_size=(0.24, 0.44, 0.10),
        wiper_len=0.80, wiper_blade=0.95, plate_front=False,
        extras=extras, extra_slots=("LIGHT_EMERGENCY_R", "LIGHT_EMERGENCY_B", "LIGHT_EMERGENCY_W"),
        waivers={"Door_RL": "one cab door per side", "Door_RR": "one cab door per side",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "no rear window on a tower-ladder body"},
        lod_budgets=(40_000, 6_000),
        sources=["Seagrave Aerialscope 75 ft published dimensions; FDNY ladder company configuration"],
        notes={"role": "FDNY Tower Ladder (ADR-009)",
               "fidelity": "boom modelled stowed as three telescoping box sections plus the bucket; it is not "
                           "riggable in this glb"},
    )


# --------------------------------------------------------------------------- Type I ambulance
def ambulance() -> FleetSpec:
    """**Type I ambulance on a Ford F-450 chassis** — FDNY EMS.

    Published (F-450 chassis cab 4x2, 169 in wheelbase, with a 168 in Type I module):
    length 7 160 mm (282 in), width 2 440 mm (96 in over the module), height 2 900 mm,
    wheelbase 4 240 mm, tyres 225/70R19.5 (overall diameter 810.3 mm).
    """
    d = Dimensions(length_mm=7160, width_mm=2440, height_mm=2900, wheelbase_mm=4240,
                   track_front_mm=1920, track_rear_mm=1750, wheel_diameter_mm=810.3, tyre_width_mm=225,
                   front_overhang_mm=1120, rear_overhang_mm=1800, rim_diameter_in=19.5, tyre_spec="225/70R19.5",
                   ground_clearance_mm=230)
    tbl = F.box_table(d, z_under=0.360, z_rocker=0.430, z_belt=1.680, z_top=2.870,
                      y_rocker=1.130, y_max=1.220, y_belt=1.210, y_top=1.080, crown=0.055,
                      x_cowl=3.55, nose_len=0.40, tail_len=0.22, nose_z_top=1.900, nose_z_belt=1.320,
                      tail_z_top=2.830, nose_y=0.80, tail_y=0.94, y_top_front=0.930)

    def extras(v, lib, bp):
        v.add(P.light_bar(lib, x=3.15, z=2.870, w=1.70, h=0.120, d=0.32, modules=8))
        # Star of Life + FDNY EMS lettering (generated)
        dec = TX.wordmark("ems_side", "AMBULANCE", w=1024, h=200, fg=(20, 40, 120))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.222
            c = [(2.30, y, 1.85), (-0.60, y, 1.85), (-0.60, y, 2.15), (2.30, y, 2.15)]
            v.add(g.to_object(f"Decal_EMS_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_EMS", dec)], smooth=False))
        chev = TX.wordmark("ems_rear", "911", w=512, h=256, fg=(200, 30, 30))
        v.add(g.to_object("Decal_Rear", g.quad_uv01_bm([(-1.796, 0.30, 2.30), (-1.796, -0.30, 2.30),
                                                        (-1.796, -0.30, 2.60), (-1.796, 0.30, 2.60)]),
                          [lib.decal("DECAL_911", chev)], smooth=False))
        steps = [g.box_bm((0.55, 1.30, 0.10), (-1.55, 0, 0.52))]
        v.add(g.to_object("StepBumper", g.merge_bm(steps), [lib.diamond_plate()], smooth=False))

    return FleetSpec(
        id="ambulance_type1_fdny", name="Type I ambulance (Ford F-450) — FDNY EMS", vclass="emergency",
        dims=d, table=tbl,
        x_cowl=3.55, x_roof_front=3.05, x_roof_rear=-1.55, x_deck=-1.70, x_bumper_f=4.10, x_bumper_r=-1.72,
        door_cuts=(3.30, 2.35, 2.00), head=LampBox(4.36, 0.95, 1.10, 0.32, 0.26, -6.0),
        tail=LampBox(-1.790, 1.02, 1.40, 0.26, 0.46), paint="#F2F4F6",
        arch_r_f=0.500, arch_r_r=0.500, wheel_style="truck", tyre_text="225/70 R19.5",
        n_stations=100, detail="mid", dual_rear=True, x_rear_door=-1.55,
        front_glass=(3.35, 1.75, 2.10), rear_glass=(-1.60, 1.90, 2.30),
        side_glass_spans=((3.28, 2.38, int(R.GLASS_FL)), (1.00, 0.20, int(R.GLASS_RL))),
        interior="cab", cab=(3.05, 1.28, 3.42, 1.70, 0.52, 45.0), z_floor=0.90, mirror_x=3.42, mirror_arm=0.24, mirror_size=(0.22, 0.40, 0.10),
        wiper_len=0.62, wiper_blade=0.68, plate_front=True,
        extras=extras, extra_slots=("LIGHT_EMERGENCY_R", "LIGHT_EMERGENCY_B", "LIGHT_EMERGENCY_W"),
        waivers={"Door_RL": "module has no left-side door", "Window_RL": "no left-side module glazing"},
        lod_budgets=(40_000, 6_000),
        sources=["Ford F-450 chassis cab published dimensions; Type I ambulance module 96 in wide"],
        notes={"role": "FDNY EMS ambulance (ADR-009)",
               "fidelity": "patient compartment interior is not modelled (Interior_* waived for this class)"},
    )


# --------------------------------------------------------------------------- Isuzu NPR box truck
def isuzu_npr() -> FleetSpec:
    """**Isuzu NPR-HD with a 16 ft dry-freight body**.

    Published: wheelbase 3 810 mm (150 in), body 16 ft, overall length 7 240 mm, width 2 130 mm over the body,
    height 3 200 mm, tyres 215/85R16 (overall diameter 771.9 mm).
    """
    d = Dimensions(length_mm=7240, width_mm=2130, height_mm=3200, wheelbase_mm=3810,
                   track_front_mm=1655, track_rear_mm=1650, wheel_diameter_mm=771.9, tyre_width_mm=215,
                   front_overhang_mm=1130, rear_overhang_mm=2300, rim_diameter_in=16.0, tyre_spec="215/85R16",
                   ground_clearance_mm=210)
    tbl = F.box_table(d, z_under=0.360, z_rocker=0.420, z_belt=1.800, z_top=3.180,
                      y_rocker=0.980, y_max=1.065, y_belt=1.055, y_top=0.960, crown=0.045,
                      x_cowl=3.90, nose_len=0.30, tail_len=0.14, nose_z_top=2.360, nose_z_belt=1.300,
                      tail_z_top=3.160, nose_y=0.86, tail_y=0.97, y_top_front=0.860)

    def extras(v, lib, bp):
        v.add(g.to_object("Liftgate", g.merge_bm([g.box_bm((0.10, 1.90, 1.20), (-2.36, 0, 1.10)),
                                                  g.box_bm((0.55, 1.90, 0.08), (-2.60, 0, 0.55))]),
                          [lib.diamond_plate()], smooth=False))
        dec = TX.wordmark("box_side", "NYC DELIVERY CO.", w=1024, h=200, fg=(30, 60, 130))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.067
            c = [(1.60, y, 1.95), (-1.60, y, 1.95), (-1.60, y, 2.35), (1.60, y, 2.35)]
            v.add(g.to_object(f"Decal_Box_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_BOX", dec)], smooth=False))

    return FleetSpec(
        id="isuzu_npr_box", name="Isuzu NPR-HD 16 ft box truck", vclass="truck", dims=d, table=tbl,
        x_cowl=3.90, x_roof_front=3.30, x_roof_rear=-2.10, x_deck=-2.25, x_bumper_f=4.05, x_bumper_r=-2.28,
        door_cuts=(3.62, 2.62, 2.30), head=LampBox(4.09, 0.86, 1.02, 0.30, 0.26, 0.0),
        tail=LampBox(-2.290, 0.90, 0.95, 0.24, 0.34), paint="#EDEFF1",
        arch_r_f=0.480, arch_r_r=0.480, wheel_style="truck", tyre_text="215/85 R16",
        n_stations=96, detail="mid", dual_rear=True, x_rear_door=-2.10,
        front_glass=(3.68, 1.86, 2.26), rear_glass=None,
        side_glass_spans=((3.60, 2.64, int(R.GLASS_FL)),),
        interior="cab", cab=(3.35, 1.42, 3.76, 1.86, 0.50, 55.0), z_floor=1.00, mirror_x=3.78, mirror_arm=0.24, mirror_size=(0.22, 0.42, 0.10),
        wiper_len=0.60, wiper_blade=0.70, plate_front=True,
        extras=extras,
        waivers={"Door_RL": "cab-over cab has one door per side", "Door_RR": "cab-over cab has one door per side",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "dry-freight body has no rear glazing"},
        lod_budgets=(32_000, 5_000),
        sources=["Isuzu NPR-HD published dimensions; 16 ft dry-freight body"],
        notes={"role": "urban freight (ADR-009)"},
    )


# --------------------------------------------------------------------------- Mack LR refuse
def mack_lr() -> FleetSpec:
    """**Mack LR with a rear-loader refuse body** — NYC Department of Sanitation.

    Published: length 10 060 mm (33 ft), width 2 591 mm (102 in), height 3 450 mm,
    wheelbase 5 120 mm (202 in), tyres 315/80R22.5.
    """
    d = Dimensions(length_mm=10060, width_mm=2591, height_mm=3450, wheelbase_mm=5120,
                   track_front_mm=2080, track_rear_mm=1860, wheel_diameter_mm=1075.5, tyre_width_mm=315,
                   front_overhang_mm=1600, rear_overhang_mm=3340, rim_diameter_in=22.5, tyre_spec="315/80R22.5",
                   ground_clearance_mm=260)
    tbl = F.box_table(d, z_under=0.430, z_rocker=0.560, z_belt=1.950, z_top=3.420,
                      y_rocker=1.210, y_max=1.2955, y_belt=1.280, y_top=1.170, crown=0.040,
                      x_cowl=6.10, nose_len=0.30, tail_len=0.24, nose_z_top=2.680, nose_z_belt=1.450,
                      tail_z_top=3.380, nose_y=0.88, tail_y=0.96, y_top_front=1.100)

    def extras(v, lib, bp):
        alu = lib.steel_painted((0.62, 0.63, 0.65), "REFUSE_STEEL")
        parts = [g.box_bm((1.45, 2.45, 1.85), (-2.42, 0, 1.55)),          # the hopper at the tail
                 g.box_bm((0.28, 2.35, 1.10), (-3.19, 0, 1.10)),          # the tailgate packer panel
                 g.box_bm((0.60, 1.60, 0.20), (-3.32, 0, 0.70))]          # the loading sill
        for k in range(6):
            parts.append(g.box_bm((0.05, 2.50, 0.10), (3.60 - k * 1.10, 0, 2.60)))
        v.add(g.to_object("RefuseBody", g.merge_bm(parts), [alu], smooth=False))
        v.add(P.light_bar(lib, x=5.60, z=3.320, w=1.20, h=0.100, d=0.24, modules=4))
        dec = TX.wordmark("dsny", "NEW YORK CITY SANITATION", w=1024, h=160, fg=(20, 60, 130))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.297
            c = [(2.60, y, 2.00), (-1.40, y, 2.00), (-1.40, y, 2.32), (2.60, y, 2.32)]
            v.add(g.to_object(f"Decal_DSNY_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_DSNY", dec)], smooth=False))

    return FleetSpec(
        id="mack_lr_dsny", name="Mack LR rear loader — NYC Sanitation", vclass="truck", dims=d, table=tbl,
        x_cowl=6.10, x_roof_front=5.55, x_roof_rear=4.30, x_deck=4.10, x_bumper_f=6.35, x_bumper_r=-3.30,
        door_cuts=(5.85, 4.80, 4.40), head=LampBox(6.42, 1.06, 1.15, 0.32, 0.30, 0.0),
        tail=LampBox(-3.330, 1.08, 1.20, 0.26, 0.42), paint=DSNY_WHITE,
        arch_r_f=0.660, arch_r_r=0.660, wheel_style="truck", tyre_text="315/80 R22.5",
        n_stations=105, detail="mid", dual_rear=True,
        front_glass=(5.95, 1.95, 2.62), rear_glass=None,
        side_glass_spans=((5.82, 4.85, int(R.GLASS_FL)),),
        interior="cab", cab=(5.55, 1.48, 5.96, 1.96, 0.58, 58.0), z_floor=1.05, mirror_x=6.02, mirror_arm=0.30, mirror_size=(0.24, 0.44, 0.10),
        wiper_len=0.78, wiper_blade=0.92, plate_front=True,
        extras=extras, extra_slots=("LIGHT_EMERGENCY_W",),
        waivers={"Door_RL": "cab-over cab has one door per side", "Door_RR": "cab-over cab has one door per side",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "refuse body has no rear glazing"},
        lod_budgets=(40_000, 6_000),
        sources=["Mack LR published dimensions; DSNY rear-loader configuration"],
        notes={"role": "DSNY collection truck (ADR-009)",
               "fidelity": "packer body is a static hopper + tailgate; the packing blade is not animated here"},
    )


# --------------------------------------------------------------------------- Sprinter / Transit / step van
def sprinter() -> FleetSpec:
    """**Mercedes-Benz Sprinter 2500, 144 in wheelbase, high roof** (2019+).

    Published: length 5 932 mm (233.5 in), width 2 020 mm (79.5 in, excl. mirrors), height 2 820 mm (111 in),
    wheelbase 3 665 mm (144.3 in), tyres 235/65R16 (overall diameter 711.9 mm).
    """
    d = Dimensions(length_mm=5932, width_mm=2020, height_mm=2820, wheelbase_mm=3665,
                   track_front_mm=1710, track_rear_mm=1700, wheel_diameter_mm=711.9, tyre_width_mm=235,
                   front_overhang_mm=990, rear_overhang_mm=1277, rim_diameter_in=16.0, tyre_spec="235/65R16",
                   ground_clearance_mm=180)
    tbl = F.box_table(d, z_under=0.290, z_rocker=0.350, z_belt=1.320, z_top=2.760,
                      y_rocker=0.930, y_max=1.010, y_belt=0.995, y_top=0.860, crown=0.075,
                      x_cowl=2.95, nose_len=0.42, tail_len=0.16, nose_z_top=1.760, nose_z_belt=1.080,
                      tail_z_top=2.720, nose_y=0.78, tail_y=0.94, y_top_front=0.930)

    def extras(v, lib, bp):
        dec = TX.wordmark("parcel", "EXPRESS PARCEL", w=1024, h=180, fg=(40, 60, 120))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.012
            c = [(1.40, y, 1.45), (-0.90, y, 1.45), (-0.90, y, 1.80), (1.40, y, 1.80)]
            v.add(g.to_object(f"Decal_Van_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_VAN", dec)], smooth=False))

    return FleetSpec(
        id="sprinter_van", name="Mercedes-Benz Sprinter 2500 high roof — delivery", vclass="van", dims=d, table=tbl,
        x_cowl=2.95, x_roof_front=2.40, x_roof_rear=-1.10, x_deck=-1.20, x_bumper_f=3.86, x_bumper_r=-1.24,
        door_cuts=(2.72, 1.72, 0.10), head=LampBox(4.32, 0.80, 1.16, 0.32, 0.34, -6.0),
        tail=LampBox(-1.267, 0.86, 1.42, 0.20, 0.62), paint="#EFF1F3",
        arch_r_f=0.455, arch_r_r=0.455, wheel_style="steel", tyre_text="235/65 R16C",
        n_stations=96, detail="mid", sliding_doors=True, x_rear_door=-1.10,
        front_glass=(2.78, 1.36, 1.98), rear_glass=(-1.15, 1.45, 2.00),
        side_glass_spans=((2.70, 1.76, int(R.GLASS_FL)),),
        interior="mid", seat_rows=[(2.05, 0.720)], z_floor=0.560, shifter="stalk", steering_x=2.52,
        mirror_x=2.82, mirror_arm=0.20, mirror_size=(0.22, 0.34, 0.10),
        wiper_len=0.62, wiper_blade=0.72, plate_front=True, handles_x=(2.40, 1.20),
        extras=extras,
        waivers={"Window_RL": "cargo body: no rear side glazing", "Window_RR": "cargo body: no rear side glazing"},
        lod_budgets=(36_000, 5_500),
        sources=["Mercedes-Benz Sprinter 2500 published dimensions"],
        notes={"role": "parcel delivery (ADR-009)"},
    )


def transit() -> FleetSpec:
    """**Ford Transit 250, 148 in wheelbase, medium roof** (2020+).

    Published: length 5 981 mm (235.5 in), width 2 059 mm (81.0 in, excl. mirrors), height 2 540 mm (100 in),
    wheelbase 3 750 mm (147.6 in), tyres 235/65R16 (overall diameter 711.9 mm).
    """
    d = Dimensions(length_mm=5981, width_mm=2059, height_mm=2540, wheelbase_mm=3750,
                   track_front_mm=1735, track_rear_mm=1720, wheel_diameter_mm=711.9, tyre_width_mm=235,
                   front_overhang_mm=960, rear_overhang_mm=1271, rim_diameter_in=16.0, tyre_spec="235/65R16",
                   ground_clearance_mm=180)
    tbl = F.box_table(d, z_under=0.290, z_rocker=0.350, z_belt=1.290, z_top=2.480,
                      y_rocker=0.950, y_max=1.0295, y_belt=1.015, y_top=0.880, crown=0.070,
                      x_cowl=2.98, nose_len=0.40, tail_len=0.16, nose_z_top=1.700, nose_z_belt=1.060,
                      tail_z_top=2.440, nose_y=0.78, tail_y=0.94, y_top_front=0.950)
    return FleetSpec(
        id="transit_van", name="Ford Transit 250 medium roof — delivery", vclass="van", dims=d, table=tbl,
        x_cowl=2.98, x_roof_front=2.42, x_roof_rear=-1.10, x_deck=-1.20, x_bumper_f=3.90, x_bumper_r=-1.24,
        door_cuts=(2.74, 1.74, 0.10), head=LampBox(4.36, 0.82, 1.14, 0.32, 0.32, -6.0),
        tail=LampBox(-1.261, 0.88, 1.36, 0.20, 0.58), paint="#F2F3F5",
        arch_r_f=0.455, arch_r_r=0.455, wheel_style="steel", tyre_text="235/65 R16C",
        n_stations=96, detail="mid", sliding_doors=True, x_rear_door=-1.10,
        front_glass=(2.80, 1.34, 1.92), rear_glass=(-1.15, 1.42, 1.94),
        side_glass_spans=((2.72, 1.78, int(R.GLASS_FL)),),
        interior="mid", seat_rows=[(2.08, 0.700)], z_floor=0.540, shifter="lever", steering_x=2.54,
        mirror_x=2.84, mirror_arm=0.20, mirror_size=(0.22, 0.34, 0.10),
        wiper_len=0.62, wiper_blade=0.72, plate_front=True, handles_x=(2.42, 1.20),
        waivers={"Window_RL": "cargo body: no rear side glazing", "Window_RR": "cargo body: no rear side glazing"},
        lod_budgets=(36_000, 5_500),
        sources=["Ford Transit 250 published dimensions"],
        notes={"role": "parcel delivery (ADR-009)"},
    )


def dollar_van() -> FleetSpec:
    """**Ford Transit 350 XLT 15-passenger, extended** — Brooklyn/Queens commuter ("dollar") van.

    Published: length 6 706 mm (264.0 in), width 2 059 mm (81.0 in), height 2 750 mm (medium roof),
    wheelbase 3 750 mm, tyres 235/65R16.
    """
    d = Dimensions(length_mm=6706, width_mm=2059, height_mm=2750, wheelbase_mm=3750,
                   track_front_mm=1735, track_rear_mm=1720, wheel_diameter_mm=711.9, tyre_width_mm=235,
                   front_overhang_mm=960, rear_overhang_mm=1996, rim_diameter_in=16.0, tyre_spec="235/65R16",
                   ground_clearance_mm=180)
    tbl = F.box_table(d, z_under=0.290, z_rocker=0.350, z_belt=1.290, z_top=2.690,
                      y_rocker=0.950, y_max=1.0295, y_belt=1.015, y_top=0.880, crown=0.070,
                      x_cowl=2.98, nose_len=0.40, tail_len=0.16, nose_z_top=1.700, nose_z_belt=1.060,
                      tail_z_top=2.650, nose_y=0.78, tail_y=0.94, y_top_front=0.950)

    def extras(v, lib, bp):
        dec = TX.wordmark("dollar_van", "FLATBUSH  ·  UTICA AV  ·  $2", w=1024, h=140, fg=(20, 20, 20))
        c = [(3.86, 0.45, 1.62), (3.86, -0.45, 1.62), (3.86, -0.45, 1.80), (3.86, 0.45, 1.80)]
        v.add(g.to_object("Sign_Route", g.quad_uv01_bm(c), [lib.decal("DECAL_DOLLARVAN", dec)], smooth=False))

    return FleetSpec(
        id="dollar_van", name="Commuter (dollar) van — Ford Transit 350 XLT", vclass="van", dims=d, table=tbl,
        x_cowl=2.98, x_roof_front=2.42, x_roof_rear=-1.80, x_deck=-1.92, x_bumper_f=3.90, x_bumper_r=-1.96,
        door_cuts=(2.74, 1.74, 0.00), head=LampBox(4.36, 0.82, 1.14, 0.32, 0.32, -6.0),
        tail=LampBox(-1.986, 0.88, 1.42, 0.20, 0.60), paint="#20304E",
        arch_r_f=0.455, arch_r_r=0.455, wheel_style="steel", tyre_text="235/65 R16C",
        n_stations=98, detail="mid", sliding_doors=True, x_rear_door=-1.80,
        front_glass=(2.80, 1.34, 1.92), rear_glass=(-1.86, 1.42, 2.10),
        side_glass_spans=((2.72, 1.78, int(R.GLASS_FL)), (1.62, -1.70, int(R.GLASS_RL))),
        interior="mid", seat_rows=[(2.08, 0.700), (1.10, 0.720), (0.10, 0.720), (-0.90, 0.720)],
        z_floor=0.540, shifter="lever", steering_x=2.54,
        mirror_x=2.84, mirror_arm=0.20, mirror_size=(0.22, 0.34, 0.10),
        wiper_len=0.62, wiper_blade=0.72, plate_front=True, handles_x=(2.42, 1.20),
        extras=extras, lod_budgets=(36_000, 5_500),
        sources=["Ford Transit 350 XLT 15-passenger published dimensions"],
        notes={"role": "commuter van (ADR-009)"},
    )


def step_van() -> FleetSpec:
    """**Freightliner MT55 walk-in step van** — parcel carrier.

    Published: length 7 620 mm (25 ft), width 2 440 mm (96 in), height 3 050 mm,
    wheelbase 4 140 mm (163 in), tyres 225/70R19.5 (overall diameter 810.3 mm).
    """
    d = Dimensions(length_mm=7620, width_mm=2440, height_mm=3050, wheelbase_mm=4140,
                   track_front_mm=1900, track_rear_mm=1740, wheel_diameter_mm=810.3, tyre_width_mm=225,
                   front_overhang_mm=1200, rear_overhang_mm=2280, rim_diameter_in=19.5, tyre_spec="225/70R19.5",
                   ground_clearance_mm=230)
    tbl = F.box_table(d, z_under=0.340, z_rocker=0.400, z_belt=1.620, z_top=3.020,
                      y_rocker=1.130, y_max=1.220, y_belt=1.205, y_top=1.060, crown=0.055,
                      x_cowl=4.35, nose_len=0.34, tail_len=0.16, nose_z_top=2.500, nose_z_belt=1.350,
                      tail_z_top=2.980, nose_y=0.84, tail_y=0.96, y_top_front=1.050)

    def extras(v, lib, bp):
        dec = TX.wordmark("stepvan", "PARCEL SERVICE", w=1024, h=180, fg=(70, 45, 20))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.222
            c = [(2.00, y, 1.80), (-1.40, y, 1.80), (-1.40, y, 2.20), (2.00, y, 2.20)]
            v.add(g.to_object(f"Decal_Step_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_STEPVAN", dec)], smooth=False))
        v.add(g.to_object("StepWell", g.merge_bm([g.box_bm((0.70, 0.12, 0.60), (3.30, 1.15, 0.62))]),
                          [lib.diamond_plate()], smooth=False))

    return FleetSpec(
        id="freightliner_stepvan", name="Freightliner MT55 step van — parcel", vclass="truck", dims=d, table=tbl,
        x_cowl=4.35, x_roof_front=3.85, x_roof_rear=-2.10, x_deck=-2.22, x_bumper_f=4.50, x_bumper_r=-2.26,
        door_cuts=(4.10, 3.10, 2.70), head=LampBox(4.72, 0.98, 0.98, 0.30, 0.28, 0.0),
        tail=LampBox(-2.270, 1.02, 1.05, 0.24, 0.36), paint="#8A6A3C",
        arch_r_f=0.500, arch_r_r=0.500, wheel_style="truck", tyre_text="225/70 R19.5",
        n_stations=96, detail="mid", dual_rear=True, x_rear_door=-2.10,
        front_glass=(4.14, 1.66, 2.44), rear_glass=None,
        side_glass_spans=((4.08, 3.12, int(R.GLASS_FL)),),
        interior="cab", cab=(3.85, 1.06, 4.24, 1.56, 0.52, 55.0), z_floor=0.72, mirror_x=4.26, mirror_arm=0.26, mirror_size=(0.22, 0.42, 0.10),
        wiper_len=0.70, wiper_blade=0.85, plate_front=True,
        extras=extras,
        waivers={"Door_RL": "walk-in van has one cab door per side",
                 "Door_RR": "walk-in van has one cab door per side",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "roll-up rear door has no glazing"},
        lod_budgets=(36_000, 5_500),
        sources=["Freightliner MT55 published dimensions; 25 ft walk-in body"],
        notes={"role": "parcel step van (ADR-009)"},
    )


def usps_llv() -> FleetSpec:
    """**Grumman LLV** — United States Postal Service long-life vehicle.

    Published: length 4 440 mm (175 in), width 1 870 mm (73.5 in), height 2 440 mm (96 in),
    wheelbase 2 690 mm (106 in), tyres 205/75R15 (overall diameter 688.5 mm).
    Right-hand drive (kerb-side steering) — the steering wheel is on the right in this model.
    """
    d = Dimensions(length_mm=4440, width_mm=1870, height_mm=2440, wheelbase_mm=2690,
                   track_front_mm=1520, track_rear_mm=1500, wheel_diameter_mm=688.5, tyre_width_mm=205,
                   front_overhang_mm=780, rear_overhang_mm=970, rim_diameter_in=15.0, tyre_spec="205/75R15",
                   ground_clearance_mm=175)
    tbl = F.box_table(d, z_under=0.270, z_rocker=0.330, z_belt=1.270, z_top=2.380,
                      y_rocker=0.860, y_max=0.935, y_belt=0.920, y_top=0.790, crown=0.060,
                      x_cowl=2.55, nose_len=0.30, tail_len=0.14, nose_z_top=1.640, nose_z_belt=1.000,
                      tail_z_top=2.340, nose_y=0.80, tail_y=0.94, y_top_front=0.860)

    def extras(v, lib, bp):
        dec = TX.wordmark("usps", "UNITED STATES POSTAL SERVICE", w=1024, h=140, fg=(20, 40, 110))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 0.937
            c = [(1.20, y, 1.42), (-0.70, y, 1.42), (-0.70, y, 1.66), (1.20, y, 1.66)]
            v.add(g.to_object(f"Decal_USPS_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_USPS", dec)], smooth=False))
        stripe(v, lib, "USPS_RED", "#C8102E", -0.90, 2.40, 1.10, 1.20, 0.937)
        stripe(v, lib, "USPS_BLUE", "#1B3D8F", -0.90, 2.40, 0.98, 1.10, 0.937)

    return FleetSpec(
        id="usps_llv", name="Grumman LLV — USPS", vclass="van", dims=d, table=tbl,
        x_cowl=2.55, x_roof_front=2.05, x_roof_rear=-0.80, x_deck=-0.90, x_bumper_f=3.28, x_bumper_r=-0.94,
        door_cuts=(2.34, 1.44, 0.30), head=LampBox(3.44, 0.74, 0.92, 0.26, 0.22, 0.0),
        tail=LampBox(-0.960, 0.78, 1.10, 0.20, 0.34), paint=USPS_WHITE,
        arch_r_f=0.435, arch_r_r=0.435, wheel_style="steel", tyre_text="205/75 R15",
        n_stations=88, detail="mid", x_rear_door=-0.80,
        front_glass=(2.38, 1.32, 1.86), rear_glass=None,
        side_glass_spans=((2.32, 1.46, int(R.GLASS_FL)),),
        interior="mid", seat_rows=[(1.72, 0.640)], z_floor=0.500, shifter="stalk", steering_x=2.16,
        mirror_x=2.44, mirror_arm=0.20, mirror_size=(0.20, 0.32, 0.09),
        wiper_len=0.52, wiper_blade=0.60, plate_front=True,
        extras=extras,
        waivers={"Door_RL": "LLV has one cab door per side plus a rear roll-up",
                 "Door_RR": "LLV has one cab door per side plus a rear roll-up",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "roll-up rear door has no glazing"},
        lod_budgets=(30_000, 5_000),
        sources=["Grumman LLV published dimensions"],
        notes={"role": "USPS mail delivery (ADR-009)",
               "drive_side": "right-hand drive; SteeringWheel/Pedals are mirrored to the kerb side"},
    )


def coned_truck() -> FleetSpec:
    """**Ford F-550 with a utility (line) body** — Con Edison.

    Published (F-550 chassis cab, 4x4, 169 in wheelbase, with an 11 ft utility body):
    length 7 340 mm, width 2 440 mm over the body, height 2 900 mm, wheelbase 4 320 mm (170 in),
    tyres 225/70R19.5 (overall diameter 810.3 mm).
    """
    d = Dimensions(length_mm=7340, width_mm=2440, height_mm=2900, wheelbase_mm=4320,
                   track_front_mm=1900, track_rear_mm=1750, wheel_diameter_mm=810.3, tyre_width_mm=225,
                   front_overhang_mm=1120, rear_overhang_mm=1900, rim_diameter_in=19.5, tyre_spec="225/70R19.5",
                   ground_clearance_mm=240)
    tbl = F.box_table(d, z_under=0.380, z_rocker=0.450, z_belt=1.500, z_top=2.220,
                      y_rocker=1.120, y_max=1.220, y_belt=1.200, y_top=1.020, crown=0.050,
                      x_cowl=3.80, nose_len=0.40, tail_len=0.18, nose_z_top=1.640, nose_z_belt=1.180,
                      tail_z_top=2.180, nose_y=0.80, tail_y=0.96, y_top_front=1.000)

    def extras(v, lib, bp):
        steel = lib.steel_painted((0.72, 0.74, 0.76), "UTILITY_BODY")
        parts = [g.box_bm((3.10, 2.40, 1.10), (-0.20, 0, 1.35))]
        for s in (1, -1):
            for bx in (0.85, -0.30, -1.35):
                parts.append(g.box_bm((0.95, 0.06, 0.85), (bx, s * 1.222, 1.35)))
        parts.append(g.box_bm((3.00, 2.30, 0.06), (-0.20, 0, 1.93)))
        v.add(g.to_object("UtilityBody", g.merge_bm(parts), [steel], smooth=False))
        boom = [g.cylinder_bm(0.28, 0.45, axis="Z", center=(1.05, 0, 2.10), segments=20),
                g.box_bm((0.34, 0.34, 0.60), (1.05, 0, 2.58)),
                g.box_bm((2.60, 0.36, 0.34), (-0.30, 0, 2.55)),
                g.box_bm((0.80, 0.62, 0.70), (-1.70, 0, 2.55))]
        v.add(g.to_object("Boom", g.merge_bm(boom), [lib.steel_painted((0.85, 0.72, 0.20), "BOOM_YELLOW")],
                          smooth=False))
        v.add(P.light_bar(lib, x=3.40, z=2.220, w=1.20, h=0.100, d=0.22, modules=4))
        dec = TX.wordmark("coned", "Con Edison", w=1024, h=200, fg=(255, 255, 255))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.223
            c = [(3.55, y, 1.10), (2.35, y, 1.10), (2.35, y, 1.36), (3.55, y, 1.36)]
            v.add(g.to_object(f"Decal_ConEd_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_CONED", dec)], smooth=False))

    return FleetSpec(
        id="coned_utility_truck", name="Ford F-550 utility truck — Con Edison", vclass="truck", dims=d, table=tbl,
        x_cowl=3.80, x_roof_front=3.10, x_roof_rear=1.90, x_deck=1.70, x_bumper_f=4.10, x_bumper_r=-1.86,
        door_cuts=(3.55, 2.55, 1.95), head=LampBox(4.36, 0.98, 1.02, 0.30, 0.26, -6.0),
        tail=LampBox(-1.890, 1.02, 1.05, 0.24, 0.34), paint=CONED_BLUE,
        arch_r_f=0.500, arch_r_r=0.500, wheel_style="truck", tyre_text="225/70 R19.5",
        n_stations=94, detail="mid", dual_rear=True,
        front_glass=(3.58, 1.55, 2.06), rear_glass=None,
        side_glass_spans=((3.52, 2.58, int(R.GLASS_FL)),),
        interior="mid", seat_rows=[(2.30, 0.900)], z_floor=0.740, shifter="lever", steering_x=3.36,
        mirror_x=3.64, mirror_arm=0.24, mirror_size=(0.22, 0.40, 0.10),
        wiper_len=0.60, wiper_blade=0.72, plate_front=True, handles_x=(3.20,),
        extras=extras, extra_slots=("LIGHT_EMERGENCY_W",),
        waivers={"Door_RL": "regular cab: one door per side", "Door_RR": "regular cab: one door per side",
                 "Window_RL": "single door glazing per side", "Window_RR": "single door glazing per side",
                 "Window_BACK": "utility body blocks the rear window"},
        lod_budgets=(36_000, 5_500),
        sources=["Ford F-550 chassis cab published dimensions; 11 ft utility body"],
        notes={"role": "Con Edison line truck (ADR-009)"},
    )


def school_bus() -> FleetSpec:
    """**Blue Bird Vision Type C school bus, 77 passenger**.

    Published: length 12 192 mm (40 ft), width 2 440 mm (96 in), height 3 100 mm,
    wheelbase 6 934 mm (273 in), front overhang 2 134 mm (84 in), rear overhang 3 124 mm (123 in),
    tyres 275/80R22.5 (overall diameter 1 011.5 mm).
    """
    d = Dimensions(length_mm=12192, width_mm=2440, height_mm=3100, wheelbase_mm=6934,
                   track_front_mm=2050, track_rear_mm=1830, wheel_diameter_mm=1011.5, tyre_width_mm=275,
                   front_overhang_mm=2134, rear_overhang_mm=3124, rim_diameter_in=22.5, tyre_spec="275/80R22.5",
                   ground_clearance_mm=280)
    tbl = F.box_table(d, z_under=0.440, z_rocker=0.560, z_belt=1.880, z_top=3.020,
                      y_rocker=1.150, y_max=1.220, y_belt=1.205, y_top=1.080, crown=0.055,
                      x_cowl=7.30, nose_len=1.40, tail_len=0.22, nose_z_top=1.560, nose_z_belt=1.180,
                      tail_z_top=2.980, nose_y=0.62, tail_y=0.96, y_top_front=0.700)

    def extras(v, lib, bp):
        # the conventional (Type C) bonnet ahead of the windshield
        hood = [g.rounded_box_bm((1.55, 1.55, 0.62), 0.12, segments=2, center=(8.05, 0, 1.55))]
        v.add(g.to_object("Hood_Conventional", g.merge_bm(hood),
                          [lib.paint(M.srgb_hex(SCHOOL_YELLOW)[:3], "BODY_PAINT_school_hood",
                                     metallic=0.12, roughness=0.38)], smooth=True, sharp_angle_deg=40.0))
        # stop arm and crossing gate
        arm = [g.box_bm((0.02, 0.46, 0.46), (2.60, 1.30, 1.70)),
               g.tube_bm([(2.60, 1.24, 1.70), (2.60, 1.10, 1.70)], 0.03, segments=8)]
        v.add(g.to_object("StopArm", g.merge_bm(arm), [M.basic("STOP_ARM_RED", (0.55, 0.02, 0.02), roughness=0.4)],
                          smooth=False))
        gate = [g.tube_bm([(8.70, 1.00, 0.72), (8.70, 1.00, 0.55)], 0.03, segments=8),
                g.tube_bm([(8.70, 1.00, 0.62), (8.70, -0.20, 0.62)], 0.025, segments=8)]
        v.add(g.to_object("CrossingGate", g.merge_bm(gate), [lib.steel_painted((0.05, 0.05, 0.05), "GATE_BLACK")],
                          smooth=False))
        # eight-lamp warning system
        lamps = []
        for s in (1, -1):
            for k, (lx, lz, red) in enumerate(((7.44, 2.86, True), (7.44, 2.86, False))):
                pass
        red_mat = lib.light("LIGHT_EMERGENCY_R", (1.0, 0.03, 0.02), alpha=0.7)
        amb_mat = lib.light_amber("LIGHT_EMERGENCY_A")
        for s in (1, -1):
            lamps.append(g.set_material_bm(g.cylinder_bm(0.09, 0.06, axis="X", center=(7.46, s * 0.75, 2.84),
                                                         segments=14), 0))
            lamps.append(g.set_material_bm(g.cylinder_bm(0.09, 0.06, axis="X", center=(7.46, s * 0.45, 2.84),
                                                         segments=14), 1))
        v.add(g.to_object("WarningLamps", g.merge_bm(lamps), [red_mat, amb_mat], smooth=True, sharp_angle_deg=50.0))
        dec = TX.wordmark("school_bus", "SCHOOL BUS", w=1024, h=200, fg=(20, 20, 20))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * 1.222
            c = [(2.40, y, 2.42), (-0.80, y, 2.42), (-0.80, y, 2.72), (2.40, y, 2.72)]
            v.add(g.to_object(f"Decal_School_{tag}", g.quad_uv01_bm(c if s > 0 else list(reversed(c))),
                              [lib.decal("DECAL_SCHOOL", dec)], smooth=False))
        stripe(v, lib, "SCHOOL_BLACK", "#141414", -3.10, 7.10, 1.72, 1.86, 1.222)

    return FleetSpec(
        id="school_bus_bluebird", name="Blue Bird Vision Type C school bus", vclass="bus", dims=d, table=tbl,
        x_cowl=7.30, x_roof_front=6.80, x_roof_rear=-2.90, x_deck=-3.05, x_bumper_f=8.60, x_bumper_r=-3.08,
        door_cuts=(6.95, 6.05, 5.70), head=LampBox(8.82, 0.86, 1.10, 0.26, 0.24, 0.0),
        tail=LampBox(-3.114, 1.02, 1.35, 0.24, 0.44), paint=SCHOOL_YELLOW,
        arch_r_f=0.630, arch_r_r=0.630, wheel_style="truck", tyre_text="275/80 R22.5",
        n_stations=115, detail="mid", dual_rear=True,
        front_glass=(6.90, 1.94, 2.72), rear_glass=(-2.70, 2.00, 2.60),
        side_glass_spans=((6.90, 6.10, int(R.GLASS_FL)), (5.60, -2.70, int(R.GLASS_RL))),
        kerb_side_doors_only=True,
        waivers={"Trunk": "a Type C school bus has an emergency rear door in the body, not an opening boot lid",
                 "Door_FL": "school bus service door is on the kerb (right) side only",
                 "Door_RL": "school bus has a single service door",
                 "Door_RR": "school bus has a single service door",
                 "Window_FL": "no left-side door glazing", "Window_RL": "saloon glazing is Window_RR"},
        interior="cab", cab=(6.75, 1.44, 7.16, 1.94, 0.62, 62.0), z_floor=1.00, mirror_x=7.20, mirror_arm=0.34, mirror_size=(0.22, 0.42, 0.10),
        wiper_len=0.80, wiper_blade=0.95, plate_front=True,
        extras=extras, extra_slots=("LIGHT_EMERGENCY_R", "LIGHT_EMERGENCY_A"),
        lod_budgets=(40_000, 6_000),
        sources=["Blue Bird Vision published dimensions; NY State Type C school bus configuration"],
        notes={"role": "school bus (ADR-009)"},
    )


ALL = {
    "nova_lfs_mta": nova_lfs,
    "xd60_sbs": xd60,
    "mci_j4500_coach": mci_coach,
    "seagrave_engine_fdny": seagrave_engine,
    "seagrave_tower_fdny": seagrave_tower,
    "ambulance_type1_fdny": ambulance,
    "isuzu_npr_box": isuzu_npr,
    "mack_lr_dsny": mack_lr,
    "sprinter_van": sprinter,
    "transit_van": transit,
    "dollar_van": dollar_van,
    "freightliner_stepvan": step_van,
    "usps_llv": usps_llv,
    "coned_utility_truck": coned_truck,
    "school_bus_bluebird": school_bus,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    env.ensure_dirs()
    ids = [i.strip() for i in args.only.split(",") if i.strip()] or list(ALL)
    for vid in ids:
        e = F.build_and_export(ALL[vid]())
        print(f"{e['id']:>26s}  {e['triangles']:>7d} tris  LOD1 {e['lods'][1]['triangles']:>6d}  "
              f"LOD2 {e['lods'][2]['triangles']:>5d}  dev L/W/H "
              f"{e['dimension_deviation_pct']['length_pct']:+.2f}/"
              f"{e['dimension_deviation_pct']['width_pct']:+.2f}/"
              f"{e['dimension_deviation_pct']['height_pct']:+.2f} %")
    return 0


if __name__ == "__main__":
    code = main()
    env.finish(code)
