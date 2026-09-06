#!/usr/bin/env python3
"""Fleet cars, SUVs and the taxi van (ADR-009).

Each entry lists its **published** dimensions in the docstring of its spec function and feeds them to
:class:`vlib.blueprint.Dimensions`, which refuses a set whose overhangs plus wheelbase do not add up to the
published length.  The body lines come from :func:`vlib.fleetlib.car_table` / ``box_table`` — the arguments to
those calls *are* the blueprint, in metres, in the vehicle frame.

Run: ``nice -n 10 python3 blender/vehicles/fleet_cars.py [--only camry,rav4,...]``
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
from vlib.blueprint import Dimensions  # noqa: E402
from vlib.fleetlib import FleetSpec, LampBox  # noqa: E402

log = env.log


# --------------------------------------------------------------------------- Toyota Camry
def camry(livery: str = "yellow_taxi") -> FleetSpec:
    """**Toyota Camry (XV70, 2018-2024)** — NYC medallion taxi / for-hire vehicle.

    Published: length 4 885 mm (192.1 in), width 1 840 mm (72.4 in), height 1 445 mm (56.9 in),
    wheelbase 2 825 mm (111.2 in), track 1 580 / 1 580 mm, tyres 215/55R17 (overall diameter 668.3 mm).
    Overhangs 1 000 / 1 060 mm split from the published 2 060 mm total.
    """
    d = Dimensions(length_mm=4885, width_mm=1840, height_mm=1445, wheelbase_mm=2825,
                   track_front_mm=1580, track_rear_mm=1580, wheel_diameter_mm=668.3, tyre_width_mm=215,
                   front_overhang_mm=1000, rear_overhang_mm=1060, rim_diameter_in=17.0, tyre_spec="215/55R17",
                   ground_clearance_mm=145)
    tbl = F.car_table(d, z_under=0.160, z_rocker=0.190, z_belt=0.965, z_roof=1.445,
                      y_rocker=0.845, y_max=0.920, y_belt=0.884, y_roof=0.615,
                      x_cowl=2.66, x_roof_front=1.94, x_roof_rear=0.74, x_deck=0.00,
                      z_hood_front=0.985, z_nose=0.855, z_tail=1.055, z_deck=1.180,
                      y_top_cowl=0.755, y_top_deck=0.690)
    paint = {"yellow_taxi": "#F7B500", "black_car": "#0C0D0F", "green_boro_taxi": "#6CBE45"}[livery]
    vid = {"yellow_taxi": "camry_taxi_yellow", "black_car": "camry_black_car",
           "green_boro_taxi": "camry_boro_taxi"}[livery]
    extras = None
    slots: tuple[str, ...] = ()
    if livery in ("yellow_taxi", "green_boro_taxi"):
        slots = ("TAXI_ROOF",)

        def extras(v, lib, bp, _l=livery):
            med = TX.taxi_roof_light(f"taxi_roof_{_l}", "7J31" if _l == "yellow_taxi" else "2G88",
                                     boro=_l == "green_boro_taxi")
            v.add(P.taxi_roof_light(lib, x=1.35, z=1.445, medallion_image=med, w=0.60, h=0.112, d=0.20))

    return FleetSpec(
        id=vid, name=f"Toyota Camry — {livery.replace('_', ' ')}", vclass="sedan", dims=d, table=tbl,
        x_cowl=2.66, x_roof_front=1.94, x_roof_rear=0.74, x_deck=0.00, x_bumper_f=3.50, x_bumper_r=-0.80,
        door_cuts=(2.38, 1.30, 0.42), head=LampBox(3.70, 0.605, 0.885, 0.335, 0.165, -15.0),
        tail=LampBox(-1.056, 0.630, 0.995, 0.395, 0.160), paint=paint, arch_r_f=0.42, arch_r_r=0.42,
        wheel_style="alloy5", spokes=5, tyre_text="215/55 R17 94V", n_stations=88, detail="mid",
        seat_rows=[(1.86, 0.535), (0.94, 0.575)], z_floor=0.340, shifter="lever", steering_x=2.24,
        mirror_x=2.26, exhaust=(-1.03, 0.42, 0.345), grille=(3.72, 0.62, 0.94, 0.42),
        handles_x=(2.06, 0.98), extras=extras, extra_slots=slots,
        sources=["Toyota Camry XV70 published dimensions"],
        notes={"livery": livery, "role": "NYC medallion taxi / FHV (ADR-009)"},
    )


# --------------------------------------------------------------------------- Toyota RAV4
def rav4() -> FleetSpec:
    """**Toyota RAV4 Hybrid (XA50, 2019-2025)** — for-hire vehicle / green-cab body.

    Published: length 4 600 mm (181.5 in), width 1 855 mm (73.0 in), height 1 685 mm (66.3 in),
    wheelbase 2 690 mm (105.9 in), track 1 570 / 1 580 mm, tyres 225/65R17 (overall diameter 724.3 mm).
    """
    d = Dimensions(length_mm=4600, width_mm=1855, height_mm=1685, wheelbase_mm=2690,
                   track_front_mm=1570, track_rear_mm=1580, wheel_diameter_mm=724.3, tyre_width_mm=225,
                   front_overhang_mm=1000, rear_overhang_mm=910, rim_diameter_in=17.0, tyre_spec="225/65R17",
                   ground_clearance_mm=203)
    tbl = F.car_table(d, z_under=0.230, z_rocker=0.290, z_belt=1.075, z_roof=1.685,
                      y_rocker=0.845, y_max=0.9275, y_belt=0.890, y_roof=0.660,
                      x_cowl=2.48, x_roof_front=1.90, x_roof_rear=-0.05, x_deck=-0.40,
                      z_hood_front=1.100, z_nose=0.960, z_tail=1.420, z_deck=1.560,
                      y_top_cowl=0.790, y_top_deck=0.720, crown_roof=0.026, crown_glass=0.060)
    return FleetSpec(
        id="rav4_fhv", name="Toyota RAV4 Hybrid — for-hire vehicle", vclass="suv", dims=d, table=tbl,
        x_cowl=2.48, x_roof_front=1.90, x_roof_rear=-0.05, x_deck=-0.40, x_bumper_f=3.32, x_bumper_r=-0.70,
        door_cuts=(2.26, 1.22, 0.36), head=LampBox(3.52, 0.635, 1.035, 0.330, 0.175, -12.0),
        tail=LampBox(-0.906, 0.660, 1.230, 0.300, 0.230), paint="#2E3134", arch_r_f=0.455, arch_r_r=0.455,
        wheel_style="alloy5", spokes=5, tyre_text="225/65 R17 102H", n_stations=88, detail="mid",
        seat_rows=[(1.80, 0.640), (0.90, 0.690)], z_floor=0.440, shifter="lever", steering_x=2.10,
        mirror_x=2.14, exhaust=(-0.90, 0.40, 0.400), grille=(3.46, 0.70, 1.06, 0.44),
        handles_x=(1.94, 0.86),
        sources=["Toyota RAV4 XA50 published dimensions"],
        notes={"role": "for-hire vehicle / green boro-taxi body (ADR-009)"},
    )


# --------------------------------------------------------------------------- Nissan NV200 taxi
def nv200() -> FleetSpec:
    """**Nissan NV200 Taxi (2014-2021)** — the 'Taxi of Tomorrow'.

    Published: length 4 760 mm (187.4 in), width 1 730 mm (68.1 in), height 1 872 mm (73.7 in),
    wheelbase 2 725 mm (107.3 in), track 1 470 / 1 490 mm, tyres 185/60R15 (overall diameter 603 mm).
    """
    d = Dimensions(length_mm=4760, width_mm=1730, height_mm=1872, wheelbase_mm=2725,
                   track_front_mm=1470, track_rear_mm=1490, wheel_diameter_mm=603.0, tyre_width_mm=185,
                   front_overhang_mm=900, rear_overhang_mm=1135, rim_diameter_in=15.0, tyre_spec="185/60R15",
                   ground_clearance_mm=155)
    tbl = F.box_table(d, z_under=0.200, z_rocker=0.290, z_belt=1.075, z_top=1.872,
                      y_rocker=0.790, y_max=0.865, y_belt=0.845, y_top=0.640, crown=0.040,
                      x_cowl=2.36, nose_len=0.42, tail_len=0.16, nose_z_top=1.230, nose_z_belt=0.960,
                      tail_z_top=1.760, nose_y=0.70, tail_y=0.86, y_top_front=0.760)

    def extras(v, lib, bp):
        med = TX.taxi_roof_light("taxi_roof_nv200", "5T14")
        v.add(P.taxi_roof_light(lib, x=1.55, z=1.872, medallion_image=med, w=0.58, h=0.110, d=0.19))
        # panoramic roof panel (the NV200 taxi's signature glass roof)
        q = g.quad_uv01_bm([(0.55, -0.44, 1.868), (0.55, 0.44, 1.868), (1.85, 0.44, 1.868), (1.85, -0.44, 1.868)])
        v.add(g.to_object("Window_RoofPanel", q, [lib.glass_tinted()], smooth=False))

    return FleetSpec(
        id="nv200_taxi", name="Nissan NV200 — NYC taxi", vclass="van", dims=d, table=tbl,
        x_cowl=2.36, x_roof_front=1.86, x_roof_rear=-0.55, x_deck=-1.00, x_bumper_f=3.40, x_bumper_r=-0.95,
        door_cuts=(2.20, 1.28, 0.10), head=LampBox(3.55, 0.575, 1.130, 0.290, 0.230, -8.0),
        tail=LampBox(-1.130, 0.610, 1.320, 0.180, 0.520), paint="#F7B500",
        arch_r_f=0.395, arch_r_r=0.395, wheel_style="steel", tyre_text="185/60 R15 84H",
        n_stations=86, detail="mid", sliding_doors=True, x_rear_door=-0.86,
        # the NV200's screen is raked over a stubby bonnet, so it is *ahead* of the roof line rather than
        # between ``x_roof_front`` and ``x_cowl``: name the glass band explicitly or the shell puts the
        # windscreen region on the roof panel (measured: a flat patch at z 1.824..1.864).
        front_glass=(2.42, 1.28, 1.84),
        seat_rows=[(1.72, 0.665), (0.72, 0.700)], z_floor=0.470, shifter="lever", steering_x=2.02,
        mirror_x=2.16, mirror_size=(0.20, 0.135, 0.09), exhaust=(-1.12, 0.34, 0.330),
        grille=(3.48, 0.85, 1.15, 0.38), handles_x=(1.90, 0.60),
        extras=extras, extra_slots=("TAXI_ROOF",),
        waivers={}, sources=["Nissan NV200 Taxi published dimensions (NYC TLC Taxi of Tomorrow)"],
        notes={"role": "NYC medallion taxi (ADR-009)", "doors": "Door_SL/SR are the sliding side doors"},
    )


# --------------------------------------------------------------------------- Ford Explorer NYPD
def explorer_nypd() -> FleetSpec:
    """**Ford Police Interceptor Utility (Explorer U625, 2020+)** — NYPD RMP.

    Published: length 5 049 mm (198.8 in), width 2 004 mm (78.9 in, body), height 1 775 mm (69.9 in),
    wheelbase 3 025 mm (119.1 in), track 1 697 / 1 697 mm, tyres 255/60R18 (overall diameter 763.2 mm).
    """
    d = Dimensions(length_mm=5049, width_mm=2004, height_mm=1775, wheelbase_mm=3025,
                   track_front_mm=1697, track_rear_mm=1697, wheel_diameter_mm=763.2, tyre_width_mm=255,
                   front_overhang_mm=1000, rear_overhang_mm=1024, rim_diameter_in=18.0, tyre_spec="255/60R18",
                   ground_clearance_mm=195)
    tbl = F.car_table(d, z_under=0.220, z_rocker=0.285, z_belt=1.110, z_roof=1.775,
                      y_rocker=0.910, y_max=1.002, y_belt=0.960, y_roof=0.690,
                      x_cowl=2.78, x_roof_front=2.16, x_roof_rear=-0.10, x_deck=-0.48,
                      z_hood_front=1.150, z_nose=1.000, z_tail=1.480, z_deck=1.640,
                      y_top_cowl=0.850, y_top_deck=0.770, crown_roof=0.028, crown_glass=0.062)

    def extras(v, lib, bp):
        v.add(P.light_bar(lib, x=1.55, z=1.775, w=1.34, h=0.115, d=0.30, modules=8))
        # push bumper
        mats = [lib.steel_painted((0.05, 0.05, 0.055), "PUSHBAR_STEEL")]
        bars = [g.box_bm((0.09, 1.30, 0.30), (4.05, 0.0, 0.62)),
                g.box_bm((0.09, 0.10, 0.55), (4.02, 0.52, 0.72)),
                g.box_bm((0.09, 0.10, 0.55), (4.02, -0.52, 0.72)),
                g.tube_bm([(3.70, 0.62, 0.50), (4.02, 0.62, 0.62)], 0.030, segments=8),
                g.tube_bm([(3.70, -0.62, 0.50), (4.02, -0.62, 0.62)], 0.030, segments=8)]
        v.add(g.to_object("PushBumper", g.merge_bm(bars), mats, smooth=True, sharp_angle_deg=40.0))
        # NYPD door decals and the roof number
        dec = TX.wordmark("nypd_door", "NYPD", w=1024, h=384, fg=(255, 255, 255))
        for s, tag in ((1, "L"), (-1, "R")):
            y = s * (bp.y_belt(1.90) + 0.004)
            q = g.quad_uv01_bm([(2.28, y, 0.62), (1.52, y, 0.62), (1.52, y, 0.92), (2.28, y, 0.92)]
                               if s > 0 else
                               [(1.52, y, 0.62), (2.28, y, 0.62), (2.28, y, 0.92), (1.52, y, 0.92)])
            v.add(g.to_object(f"Decal_NYPD_{tag}", q, [lib.decal("DECAL_NYPD", dec)], smooth=False))

    return FleetSpec(
        id="explorer_nypd", name="Ford Police Interceptor Utility — NYPD", vclass="emergency", dims=d, table=tbl,
        x_cowl=2.78, x_roof_front=2.16, x_roof_rear=-0.10, x_deck=-0.48, x_bumper_f=3.72, x_bumper_r=-0.80,
        door_cuts=(2.56, 1.42, 0.42), head=LampBox(3.90, 0.680, 1.075, 0.340, 0.185, -10.0),
        tail=LampBox(-1.020, 0.700, 1.290, 0.320, 0.240), paint="#111417",
        arch_r_f=0.475, arch_r_r=0.475, wheel_style="steel", tyre_text="255/60 R18 112V",
        n_stations=92, detail="mid",
        seat_rows=[(2.02, 0.660), (1.02, 0.700)], z_floor=0.450, shifter="rotary", steering_x=2.38,
        mirror_x=2.44, exhaust=(-1.00, 0.44, 0.400), grille=(3.84, 0.76, 1.12, 0.50),
        handles_x=(2.20, 1.06), extras=extras,
        extra_slots=("LIGHT_EMERGENCY_R", "LIGHT_EMERGENCY_B", "LIGHT_EMERGENCY_W"),
        sources=["Ford Explorer / Police Interceptor Utility 2020 published dimensions"],
        notes={"role": "NYPD radio motor patrol (ADR-009)",
               "light_bar": "LIGHT_EMERGENCY_R / _B alternate along the bar, _W is the centre takedown"},
    )


# --------------------------------------------------------------------------- Chevrolet Suburban
def suburban() -> FleetSpec:
    """**Chevrolet Suburban (GMT1YC, 2021+)** — TLC black car / livery SUV.

    Published: length 5 733 mm (225.7 in), width 2 059 mm (81.1 in), height 1 933 mm (76.1 in),
    wheelbase 3 407 mm (134.1 in), track 1 750 / 1 750 mm, tyres 275/60R20 (overall diameter 838 mm).
    """
    d = Dimensions(length_mm=5733, width_mm=2059, height_mm=1933, wheelbase_mm=3407,
                   track_front_mm=1750, track_rear_mm=1750, wheel_diameter_mm=838.0, tyre_width_mm=275,
                   front_overhang_mm=1000, rear_overhang_mm=1326, rim_diameter_in=20.0, tyre_spec="275/60R20",
                   ground_clearance_mm=203)
    tbl = F.car_table(d, z_under=0.250, z_rocker=0.320, z_belt=1.210, z_roof=1.933,
                      y_rocker=0.940, y_max=1.0295, y_belt=0.990, y_roof=0.740,
                      x_cowl=3.10, x_roof_front=2.46, x_roof_rear=-0.62, x_deck=-1.00,
                      z_hood_front=1.290, z_nose=1.130, z_tail=1.640, z_deck=1.800,
                      y_top_cowl=0.900, y_top_deck=0.820, crown_roof=0.026, crown_glass=0.058)
    return FleetSpec(
        id="suburban_black_car", name="Chevrolet Suburban — TLC black car", vclass="suv", dims=d, table=tbl,
        x_cowl=3.10, x_roof_front=2.46, x_roof_rear=-0.62, x_deck=-1.00, x_bumper_f=4.12, x_bumper_r=-1.06,
        door_cuts=(2.88, 1.72, 0.55), head=LampBox(4.34, 0.720, 1.190, 0.300, 0.230, -8.0),
        tail=LampBox(-1.322, 0.740, 1.400, 0.190, 0.480), paint="#08090B",
        arch_r_f=0.520, arch_r_r=0.520, wheel_style="alloy5", spokes=5, tyre_text="275/60 R20 115S",
        n_stations=96, detail="mid",
        seat_rows=[(2.32, 0.740), (1.28, 0.780), (0.28, 0.810)], z_floor=0.530, shifter="lever", steering_x=2.72,
        mirror_x=2.76, mirror_size=(0.215, 0.125, 0.095), exhaust=(-1.30, 0.52, 0.440),
        grille=(4.26, 0.88, 1.26, 0.56), handles_x=(2.50, 1.36, 0.20),
        sources=["Chevrolet Suburban 2021 published dimensions"],
        notes={"role": "TLC black car / airport livery (ADR-009)"},
    )


ALL = {
    "camry_taxi_yellow": lambda: camry("yellow_taxi"),
    "camry_black_car": lambda: camry("black_car"),
    "camry_boro_taxi": lambda: camry("green_boro_taxi"),
    "rav4_fhv": rav4,
    "nv200_taxi": nv200,
    "explorer_nypd": explorer_nypd,
    "suburban_black_car": suburban,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="", help="comma-separated ids")
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
