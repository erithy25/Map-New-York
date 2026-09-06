#!/usr/bin/env python3
"""Micromobility and the horse carriage (ADR-009): Citi Bike, Arrow delivery e-bike, moped, pedicab, carriage.

These vehicles have **no cabin**, so they use the reduced contract profiles declared in :mod:`vlib.rig`
(``two_wheel``, ``trike``, ``open``).  Every contract name that does not exist on the real vehicle is listed in
the catalog entry's ``contract_waivers`` with a reason — none of them is faked with an empty object.

Fidelity is stated per vehicle in ``notes["fidelity"]``.  In particular the **horse** is a procedural animal
built from tapered capsules and revolved sections: correct published withers height, body length and leg
proportions for a light draught horse, recognisable at street distance, but it is not an anatomically
sculpted or rigged animal and it has no mane/tail hair cards.

Run: ``nice -n 10 python3 blender/vehicles/fleet_small.py [--only citibike,...]``
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vlib import env  # noqa: E402

env.setup_logging()

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from vlib import geom as g, materials as M, parts as P, rig, textures as TX  # noqa: E402
from vlib.blueprint import Dimensions  # noqa: E402
from vlib.rig import Vehicle  # noqa: E402

log = env.log
nb = env.nb
TAU = 2.0 * math.pi


# --------------------------------------------------------------------------- shared bicycle parts
def spoked_wheel(name: str, *, radius: float, tyre: float, hub_w: float = 0.10, spokes: int = 32,
                 lib: M.Library, rim_material=None, tyre_material=None, disc_brake: bool = False) -> bpy.types.Object:
    """Wire-spoked wheel authored around its hub centre; ``radius`` is the rolling radius over the tyre."""
    mats = [tyre_material or lib.tyre(), rim_material or lib.satin_alu(), lib.brushed_metal()]
    rim_r = radius - tyre
    parts = [g.set_material_bm(g.torus_bm(radius - tyre / 2, tyre / 2, axis="Y", segments=40, ring_segments=10), 0),
             g.set_material_bm(g.torus_bm(rim_r - 0.010, 0.011, axis="Y", segments=40, ring_segments=6), 1),
             g.set_material_bm(g.cylinder_bm(0.022, hub_w, axis="Y", segments=14), 2)]
    for k in range(spokes):
        a = TAU * k / spokes
        y = hub_w * 0.42 * (1 if k % 2 else -1)
        p0 = Vector((0.020 * math.cos(a + 0.4), y, 0.020 * math.sin(a + 0.4)))
        p1 = Vector(((rim_r - 0.012) * math.cos(a), 0.0, (rim_r - 0.012) * math.sin(a)))
        parts.append(g.set_material_bm(g.tube_bm([tuple(p0), tuple(p1)], 0.0016, segments=4, cap=False), 2))
    if disc_brake:
        parts.append(g.set_material_bm(g.cylinder_bm(0.080, 0.004, axis="Y", center=(0, hub_w * 0.6, 0),
                                                     segments=24), 2))
    ob = g.to_object(name, g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=42.0)
    g.uv_project(ob, lambda co, n: (((math.atan2(co.z, co.x) / TAU) % 1.0) * 3.0, 0.5 + co.y / 0.08))
    return ob


def bike_frame(lib: M.Library, *, wb: float, bb_z: float, head_z: float, seat_z: float, rear_z: float,
               tube_r: float = 0.024, colour=(0.05, 0.24, 0.55), name: str = "BODY_PAINT_bike") -> bmesh.types.BMesh:
    """Step-through diamond frame between the bottom bracket, head tube, seat tube and rear dropouts.
    ``wb`` is the wheelbase (rear hub at x = 0, front hub at x = wb)."""
    bb = (wb * 0.42, 0.0, bb_z)
    head_lo = (wb * 0.90, 0.0, bb_z + 0.20)
    head_hi = (wb * 0.86, 0.0, head_z)
    seat_hi = (wb * 0.30, 0.0, seat_z)
    rear = (0.0, 0.0, rear_z)
    tubes = [
        g.tube_bm([bb, head_lo], tube_r, segments=10),                       # down tube
        g.tube_bm([head_lo, head_hi], tube_r * 1.1, segments=10),            # head tube
        g.tube_bm([head_hi, (wb * 0.52, 0.0, seat_z - 0.02), seat_hi], tube_r, segments=10),  # top tube (curved)
        g.tube_bm([bb, seat_hi], tube_r, segments=10),                       # seat tube
    ]
    for s in (1, -1):
        tubes.append(g.tube_bm([bb, (0.0, s * 0.055, rear_z)], tube_r * 0.7, segments=8))       # chainstay
        tubes.append(g.tube_bm([seat_hi, (0.0, s * 0.055, rear_z)], tube_r * 0.6, segments=8))  # seatstay
    return g.merge_bm(tubes)


def bike_drivetrain(lib: M.Library, *, bb, crank_r: float = 0.170, chainring_r: float = 0.095,
                    rear_r: float = 0.045) -> bmesh.types.BMesh:
    parts = [g.cylinder_bm(chainring_r, 0.006, axis="Y", center=bb, segments=32),
             g.cylinder_bm(rear_r, 0.006, axis="Y", center=(0.0, 0.03, bb[2] * 0.62), segments=20)]
    for s, ph in ((1, 0.0), (-1, math.pi)):
        arm = g.box_bm((crank_r, 0.018, 0.030), (crank_r / 2, s * 0.055, 0), material_index=0)
        g.rotate_bm(arm, "Y", math.degrees(ph) + 25.0, center=(0, s * 0.055, 0))
        g.translate_bm(arm, bb)
        parts.append(arm)
        ped = g.box_bm((0.090, 0.024, 0.070), (0, 0, 0), material_index=0)
        c = math.cos(ph + math.radians(25.0)), math.sin(ph + math.radians(25.0))
        g.translate_bm(ped, (bb[0] + crank_r * c[0], s * 0.095, bb[2] - crank_r * c[1]))
        parts.append(ped)
    # chain as two straight runs
    parts.append(g.box_bm((abs(bb[0]), 0.008, 0.010), (bb[0] / 2, 0.045, bb[2] * 0.80 + 0.02)))
    parts.append(g.box_bm((abs(bb[0]), 0.008, 0.010), (bb[0] / 2, 0.045, bb[2] * 0.62 - 0.02)))
    return g.merge_bm(parts)


def handlebar(lib: M.Library, *, x: float, z: float, width: float = 0.60, rise: float = 0.06,
              stem_from=None) -> bmesh.types.BMesh:
    pts = [(x + 0.06, -width / 2, z + rise), (x - 0.02, -width / 6, z), (x - 0.02, width / 6, z),
           (x + 0.06, width / 2, z + rise)]
    parts = [g.tube_bm(pts, 0.014, segments=8)]
    for s in (1, -1):
        parts.append(g.tube_bm([(x + 0.06, s * width / 2, z + rise),
                                (x + 0.055, s * (width / 2 - 0.11), z + rise * 0.95)], 0.017, segments=8))
    if stem_from:
        parts.append(g.tube_bm([stem_from, (x - 0.02, 0.0, z)], 0.018, segments=8))
    return g.merge_bm(parts)


def saddle(x: float, z: float, *, length: float = 0.26, width: float = 0.17) -> bmesh.types.BMesh:
    body = g.sphere_bm((length / 2, width / 2, 0.045), center=(x, 0, z), segments=20, rings=10)
    nose = g.sphere_bm((length * 0.34, width * 0.18, 0.035), center=(x + length * 0.42, 0, z - 0.004),
                       segments=14, rings=8)
    return g.merge_bm([body, nose])


def lamp_slot(name: str, mat, center, radius: float, axis: str = "X", depth: float = 0.03) -> bpy.types.Object:
    return P.lamp_disc(name, mat, center, radius, axis=axis, depth=depth, segments=16)


def small_plate(lib, name, number, center, normal, w=0.16, h=0.10, style="passenger") -> bpy.types.Object:
    img = TX.plate_ny(f"plate_{name}", number, w=512, h=320, style=style)
    return P.plate(name, lib, img, center=center, normal=normal, w=w, h=h)


def finish(v: Vehicle, *, lod_budgets=(12_000, 2_500), tri_budget=40_000, extra_catalog=None) -> dict:
    body_objs = [o for o in v.objects.values() if o.type == "MESH" and not o.name.startswith("UCX_")]
    tris = g.tri_count_all(body_objs)
    if tris > tri_budget:
        raise RuntimeError(f"{v.id}: {tris} tris over the {tri_budget} budget")
    return rig.finalise(v, lod_budgets=lod_budgets, exterior_names=[o.name for o in body_objs],
                        extra_catalog=extra_catalog)


def add_ucx(v: Vehicle, d: Dimensions, z_belt: float, slices: int = 3) -> None:
    srcs = [o for o in v.objects.values() if o.type == "MESH" and not o.name.startswith(("UCX_", "Wheel"))]
    v.add_all(rig.ucx_proxies("Body", srcs, d, z_belt=z_belt, slices=slices, cabin=False))


# --------------------------------------------------------------------------- Citi Bike
def citibike() -> dict:
    """**Citi Bike classic pedal bike (Lyft/Motivate)**.

    Published: length 1 900 mm, width 660 mm over the handlebar, height 1 120 mm, wheelbase 1 200 mm,
    26 in wheels with 50 mm tyres (overall diameter 690 mm), 3-speed internal hub, front basket.
    """
    d = Dimensions(length_mm=1900, width_mm=660, height_mm=1120, wheelbase_mm=1200,
                   track_front_mm=0.1, track_rear_mm=0.1, wheel_diameter_mm=690, tyre_width_mm=50,
                   front_overhang_mm=350, rear_overhang_mm=350, rim_diameter_in=26.0, tyre_spec="26 x 2.0",
                   ground_clearance_mm=250)
    nb.reset_scene()
    lib = M.Library()
    R = d.wheel_radius
    v = Vehicle(id="citibike_cruiser", display_name="Citi Bike classic cruiser", vclass="bicycle", dims=d,
                z_belt=0.75, contract_profile="two_wheel",
                contract_waivers={n: "a bicycle has no cabin, doors, glazing, wipers, mirrors or number plates"
                                  for n in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Hood", "Trunk",
                                            "Wiper_L", "Wiper_R", "Window_WS", "Window_BACK", "Window_FL",
                                            "Window_FR", "Window_RL", "Window_RR", "Mirror_L", "Mirror_R",
                                            "Interior_Dash", "Shifter", "Pedals", "Plate_F", "Plate_R",
                                            "SteeringWheel")},
                sources=["Citi Bike (Lyft) classic bike published dimensions"],
                notes={"role": "bike-share bicycle (ADR-009)",
                       "fidelity": "frame, fork, wire-spoked wheels, chainset, basket, dock hardware and both "
                                   "lamps are modelled; cabling and the internal hub gear are not"})
    blue = lib.paint((0.02, 0.16, 0.42), "BODY_PAINT_citibike", metallic=0.20, roughness=0.34)
    mats = [blue, lib.black_plastic(), lib.satin_alu(), lib.leather(name="LEATHER_SADDLE")]
    frame = g.set_material_bm(bike_frame(lib, wb=1.20, bb_z=0.285, head_z=0.930, seat_z=0.780, rear_z=R), 0)
    fork = g.merge_bm([g.tube_bm([(1.20 * 0.86, s * 0.045, 0.930), (1.20, s * 0.045, R)], 0.017, segments=8)
                       for s in (1, -1)])
    g.set_material_bm(fork, 0)
    bar = g.set_material_bm(handlebar(lib, x=1.03, z=1.073, width=0.658, rise=0.03,
                                      stem_from=(1.20 * 0.86, 0.0, 0.945)), 2)
    sad = g.set_material_bm(saddle(0.34, 0.930), 3)
    post = g.set_material_bm(g.tube_bm([(0.36, 0, 0.780), (0.345, 0, 0.925)], 0.014, segments=8), 2)
    dt = g.set_material_bm(bike_drivetrain(lib, bb=(1.20 * 0.42, 0.0, 0.285)), 1)
    # front basket on the fork crown
    basket = []
    basket.append(g.box_bm((0.30, 0.34, 0.014), (1.16, 0, 0.845), material_index=1))
    for k in range(9):
        u = -0.15 + 0.30 * k / 8
        basket.append(g.tube_bm([(1.16 + u, -0.17, 0.845), (1.16 + u, 0.17, 0.845),
                                 (1.16 + u, 0.17, 0.985)], 0.005, segments=5, material_index=1))
    basket.append(g.tube_bm([(1.01, -0.17, 0.985), (1.31, -0.17, 0.985), (1.31, 0.17, 0.985),
                             (1.01, 0.17, 0.985)], 0.006, segments=5, material_index=1))
    fenders = []
    for cx, sgn in ((0.0, 1), (1.20, 1)):
        arc = [(cx + R * 1.03 * math.cos(a), 0.0, R * 1.03 * math.sin(a))
               for a in [math.radians(t) for t in range(30, 151, 12)]]
        fenders.append(g.ribbon_bm(arc, 0.075, up=(0, 0, 1), material_index=0))
    body = g.to_object("Body", g.merge_bm([frame, fork, bar, sad, post, dt, *basket, *fenders]), mats,
                       smooth=True, sharp_angle_deg=42.0)
    v.add(body)
    for tag, x in (("F", 1.20), ("R", 0.0)):
        w = spoked_wheel(f"Wheel_{tag}", radius=R, tyre=0.050, lib=lib, spokes=32)
        w.location = (x, 0.0, R)
        v.add(w)
    v.add(lamp_slot("LIGHT_HEAD_L", lib.light_white("LIGHT_HEAD_L"), (1.245, 0.0, 0.900), 0.030))
    v.add(lamp_slot("LIGHT_TAIL_L", lib.light_red("LIGHT_TAIL_L"), (0.245, 0.0, 0.720), 0.024))
    rig.add_damage_regions(body, d, z_belt=0.75)
    add_ucx(v, d, 0.75, slices=3)
    return finish(v, lod_budgets=(9_000, 2_000), tri_budget=40_000,
                  extra_catalog={"contract_profile_reason": "bicycle: no cabin"})


# --------------------------------------------------------------------------- Arrow delivery e-bike
def arrow_ebike() -> dict:
    """**Arrow delivery e-bike** — the throttle e-bike used by NYC food-delivery workers, with an insulated bag.

    Published (Arrow 10/11 class): length 1 850 mm, width 660 mm over the bar, height 1 100 mm,
    wheelbase 1 190 mm, 26 in wheels with 50 mm tyres (overall diameter 690 mm), 48 V rear hub motor,
    down-tube battery.
    """
    d = Dimensions(length_mm=1850, width_mm=660, height_mm=1100, wheelbase_mm=1190,
                   track_front_mm=0.1, track_rear_mm=0.1, wheel_diameter_mm=690, tyre_width_mm=50,
                   front_overhang_mm=330, rear_overhang_mm=330, rim_diameter_in=26.0, tyre_spec="26 x 2.0",
                   ground_clearance_mm=245)
    nb.reset_scene()
    lib = M.Library()
    R = d.wheel_radius
    v = Vehicle(id="arrow_ebike", display_name="Arrow delivery e-bike with insulated bag", vclass="bicycle",
                dims=d, z_belt=0.74, contract_profile="two_wheel",
                contract_waivers={n: "an e-bike has no cabin, doors, glazing, wipers or number plates"
                                  for n in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Hood", "Trunk",
                                            "Wiper_L", "Wiper_R", "Window_WS", "Window_BACK", "Window_FL",
                                            "Window_FR", "Window_RL", "Window_RR", "Mirror_L", "Mirror_R",
                                            "Interior_Dash", "Shifter", "Pedals", "Plate_F", "Plate_R",
                                            "SteeringWheel")},
                sources=["Arrow class-2 delivery e-bike published specification"],
                notes={"role": "food-delivery e-bike (ADR-009)",
                       "fidelity": "frame, battery, hub motor, rack, insulated delivery bag and lamps are "
                                   "modelled; wiring and the controller are not"})
    black = lib.paint((0.02, 0.02, 0.025), "BODY_PAINT_ebike", metallic=0.25, roughness=0.36)
    mats = [black, lib.black_plastic(), lib.satin_alu(), lib.leather(name="LEATHER_SADDLE"),
            lib.canvas((0.55, 0.06, 0.06), "BAG_INSULATED")]
    frame = g.set_material_bm(bike_frame(lib, wb=1.19, bb_z=0.290, head_z=0.920, seat_z=0.770, rear_z=R,
                                         tube_r=0.028), 0)
    fork = g.merge_bm([g.tube_bm([(1.19 * 0.86, s * 0.048, 0.920), (1.19, s * 0.048, R)], 0.020, segments=8)
                       for s in (1, -1)])
    g.set_material_bm(fork, 0)
    battery = g.set_material_bm(g.rounded_box_bm((0.42, 0.09, 0.13), 0.020, segments=2,
                                                 center=(0.75, 0, 0.470)), 1)
    motor = g.set_material_bm(g.cylinder_bm(0.095, 0.115, axis="Y", center=(0.0, 0, R), segments=22), 2)
    bar = g.set_material_bm(handlebar(lib, x=1.02, z=1.020, width=0.658, rise=0.02,
                                      stem_from=(1.19 * 0.86, 0.0, 0.935)), 2)
    sad = g.set_material_bm(saddle(0.33, 0.915), 3)
    post = g.set_material_bm(g.tube_bm([(0.352, 0, 0.770), (0.335, 0, 0.910)], 0.015, segments=8), 2)
    dt = g.set_material_bm(bike_drivetrain(lib, bb=(1.19 * 0.42, 0.0, 0.290)), 1)
    rack = []
    for s in (1, -1):
        rack.append(g.tube_bm([(0.10, s * 0.10, R + 0.02), (0.10, s * 0.16, 0.720), (-0.16, s * 0.16, 0.720)],
                              0.008, segments=6, material_index=2))
    rack.append(g.box_bm((0.34, 0.30, 0.012), (-0.02, 0, 0.726), material_index=2))
    # insulated delivery bag (0.40 x 0.36 x 0.40 m, the common 60-litre cube)
    bag = g.rounded_box_bm((0.40, 0.36, 0.38), 0.030, segments=2, center=(-0.02, 0, 0.900), material_index=4)
    flap = g.box_bm((0.36, 0.32, 0.012), (-0.02, 0, 1.092), material_index=4)
    strap = g.box_bm((0.42, 0.05, 0.012), (-0.02, 0.10, 1.092), material_index=1)
    body = g.to_object("Body", g.merge_bm([frame, fork, battery, motor, bar, sad, post, dt, *rack, bag, flap, strap]),
                       mats, smooth=True, sharp_angle_deg=42.0)
    v.add(body)
    for tag, x in (("F", 1.19), ("R", 0.0)):
        w = spoked_wheel(f"Wheel_{tag}", radius=R, tyre=0.050, lib=lib, spokes=32, disc_brake=True)
        w.location = (x, 0.0, R)
        v.add(w)
    v.add(lamp_slot("LIGHT_HEAD_L", lib.light_white("LIGHT_HEAD_L"), (1.240, 0.0, 0.890), 0.034))
    v.add(lamp_slot("LIGHT_TAIL_L", lib.light_red("LIGHT_TAIL_L"), (-0.225, 0.0, 0.760), 0.026))
    rig.add_damage_regions(body, d, z_belt=0.74)
    add_ucx(v, d, 0.74, slices=3)
    return finish(v, lod_budgets=(9_000, 2_000), tri_budget=40_000)


# --------------------------------------------------------------------------- moped
def moped() -> dict:
    """**Vespa-class 150 cc scooter** (Piaggio Vespa Primavera 150 published figures).

    Published: length 1 860 mm, width 735 mm, height 1 140 mm (seat 780 mm), wheelbase 1 340 mm,
    110/70-12 front tyre (overall diameter 458.8 mm).
    """
    d = Dimensions(length_mm=1860, width_mm=735, height_mm=1140, wheelbase_mm=1340,
                   track_front_mm=0.1, track_rear_mm=0.1, wheel_diameter_mm=458.8, tyre_width_mm=110,
                   front_overhang_mm=250, rear_overhang_mm=270, rim_diameter_in=12.0, tyre_spec="110/70-12",
                   ground_clearance_mm=160)
    nb.reset_scene()
    lib = M.Library()
    R = d.wheel_radius
    v = Vehicle(id="moped_scooter", display_name="150 cc scooter (Vespa class)", vclass="moped", dims=d,
                z_belt=0.70, contract_profile="two_wheel",
                contract_waivers={n: "a scooter has no cabin, doors, glazing or wipers"
                                  for n in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Hood", "Trunk",
                                            "Wiper_L", "Wiper_R", "Window_WS", "Window_BACK", "Window_FL",
                                            "Window_FR", "Window_RL", "Window_RR", "Interior_Dash",
                                            "Shifter", "Pedals", "Plate_F", "SteeringWheel")},
                extra_slots=("PLATE_FACE",),
                sources=["Piaggio Vespa Primavera 150 published dimensions"],
                notes={"role": "moped / scooter (ADR-009)",
                       "fidelity": "monocoque body, legshield, floorboard, seat, bar, mirrors, both lamps, "
                                   "indicators and the rear plate are modelled; the engine/CVT is a mass block"})
    body_mat = lib.paint((0.75, 0.72, 0.58), "BODY_PAINT_moped", metallic=0.30, roughness=0.26)
    mats = [body_mat, lib.black_plastic(), lib.chrome(), lib.leather(name="LEATHER_SEAT")]
    # monocoque: legshield, floor, side panels, tail
    parts = [
        g.set_material_bm(g.rounded_box_bm((0.16, 0.68, 0.62), 0.10, segments=3, center=(1.16, 0, 0.700)), 0),
        g.set_material_bm(g.rounded_box_bm((0.52, 0.42, 0.09), 0.04, segments=2, center=(0.82, 0, 0.400)), 0),
        g.set_material_bm(g.rounded_box_bm((0.72, 0.66, 0.42), 0.14, segments=3, center=(0.30, 0, 0.640)), 0),
        g.set_material_bm(g.sphere_bm((0.20, 0.28, 0.20), center=(-0.07, 0, 0.660), segments=20, rings=10), 0),
        g.set_material_bm(g.cylinder_bm(0.115, 0.34, axis="Y", center=(0.10, 0, R + 0.02), segments=20), 1),
        g.set_material_bm(g.tube_bm([(1.14, 0, 0.980), (1.30, 0, R + 0.10), (1.34, 0, R)], 0.022, segments=8), 2),
        g.set_material_bm(saddle(0.42, 0.845, length=0.62, width=0.34), 3),
        g.set_material_bm(handlebar(lib, x=1.10, z=1.095, width=0.733, rise=0.01,
                                    stem_from=(1.14, 0.0, 0.985)), 2),
        g.set_material_bm(g.rounded_box_bm((0.14, 0.30, 0.14), 0.04, segments=2, center=(1.16, 0, 1.068)), 0),
        g.set_material_bm(g.cylinder_bm(0.030, 0.34, axis="X", center=(-0.10, 0.16, 0.42), segments=12), 2),
    ]
    body = g.to_object("Body", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=40.0)
    v.add(body)
    for tag, x in (("F", 1.34), ("R", 0.0)):
        w = spoked_wheel(f"Wheel_{tag}", radius=R, tyre=0.060, lib=lib, spokes=10,
                         rim_material=lib.alloy(), hub_w=0.13)
        w.location = (x, 0.0, R)
        v.add(w)
    for s, tag in ((1, "L"), (-1, "R")):
        v.add(P.mirror(s, lib, x=1.09, y=s * 0.16, z=1.190, w=0.115, h=0.075, d=0.05, repeater=False, arm=0.10))
    v.add(lamp_slot("LIGHT_HEAD_L", lib.light_white("LIGHT_HEAD_L"), (1.238, 0.0, 0.860), 0.075))
    v.add(lamp_slot("LIGHT_TAIL_L", lib.light_red("LIGHT_TAIL_L"), (-0.255, 0.0, 0.720), 0.045, depth=0.04))
    v.add(P.lamp_panel("LIGHT_BRAKE_L", lib.light_red("LIGHT_BRAKE_L"),
                       [(-0.258, -0.06, 0.760), (-0.258, 0.06, 0.760), (-0.258, 0.06, 0.800), (-0.258, -0.06, 0.800)],
                       thickness=0.02, inward=(1, 0, 0)))
    for s, tag in ((1, "L"), (-1, "R")):
        v.add(lamp_slot(f"LIGHT_TURN_F{tag}", lib.light_amber(f"LIGHT_TURN_F{tag}"),
                        (1.205, s * 0.30, 0.905), 0.026))
        v.add(lamp_slot(f"LIGHT_TURN_R{tag}", lib.light_amber(f"LIGHT_TURN_R{tag}"),
                        (-0.235, s * 0.20, 0.735), 0.024))
    v.add(small_plate(lib, "Plate_R", "5T29B", (-0.268, 0.0, 0.590), (-1, 0, -0.10), w=0.155, h=0.100))
    rig.add_damage_regions(body, d, z_belt=0.70)
    add_ucx(v, d, 0.70, slices=3)
    return finish(v, lod_budgets=(9_000, 2_000), tri_budget=40_000)


# --------------------------------------------------------------------------- pedicab
def pedicab() -> dict:
    """**NYC licensed pedicab** (three-wheel rear-bench rickshaw).

    Dimensions from the NYC Administrative Code §20-250 limits and a typical licensed vehicle:
    length 2 900 mm, width 1 250 mm (the code caps it at 55 in / 1 397 mm), height 1 750 mm over the canopy,
    wheelbase 1 850 mm, 26 in wheels with 50 mm tyres (overall diameter 690 mm), rear track 1 000 mm.
    """
    d = Dimensions(length_mm=2900, width_mm=1250, height_mm=1750, wheelbase_mm=1850,
                   track_front_mm=0.1, track_rear_mm=1000, wheel_diameter_mm=690, tyre_width_mm=50,
                   front_overhang_mm=400, rear_overhang_mm=650, rim_diameter_in=26.0, tyre_spec="26 x 2.0",
                   ground_clearance_mm=200)
    nb.reset_scene()
    lib = M.Library()
    R = d.wheel_radius
    v = Vehicle(id="pedicab", display_name="NYC pedicab", vclass="pedicab", dims=d, z_belt=0.85,
                contract_profile="trike",
                contract_waivers={n: "a pedicab has an open passenger bench, no cabin or glazing"
                                  for n in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Hood", "Trunk",
                                            "Wiper_L", "Wiper_R", "Window_WS", "Window_BACK", "Window_FL",
                                            "Window_FR", "Window_RL", "Window_RR", "Mirror_R",
                                            "Interior_Dash", "Shifter", "Pedals", "Plate_F", "SteeringWheel")},
                extra_slots=("PLATE_FACE",),
                sources=["NYC Administrative Code §20-250 pedicab dimensions; typical licensed vehicle"],
                notes={"role": "licensed pedicab (ADR-009)",
                       "fidelity": "frame, drivetrain, bench, canopy, rear body panel and lamps are modelled; "
                                   "no seat-belt or advertising-frame hardware"})
    frame_mat = lib.paint((0.75, 0.10, 0.10), "BODY_PAINT_pedicab", metallic=0.25, roughness=0.35)
    mats = [frame_mat, lib.black_plastic(), lib.satin_alu(), lib.leather(name="LEATHER_BENCH"),
            lib.canvas((0.85, 0.82, 0.10), "CANOPY_CANVAS")]
    wb = 1.85
    parts = [
        g.set_material_bm(g.tube_bm([(wb * 0.42, 0, 0.300), (wb * 0.90, 0, 0.560), (wb * 0.86, 0, 0.980)],
                                    0.026, segments=10), 0),
        g.set_material_bm(g.tube_bm([(wb * 0.42, 0, 0.300), (0.40, 0, 0.480)], 0.026, segments=10), 0),
        g.set_material_bm(handlebar(lib, x=wb * 0.78, z=1.060, width=0.62, rise=0.02,
                                    stem_from=(wb * 0.86, 0.0, 0.990)), 2),
        g.set_material_bm(saddle(wb * 0.52, 0.930, length=0.28, width=0.18), 3),
        g.set_material_bm(g.tube_bm([(wb * 0.52, 0, 0.720), (wb * 0.52, 0, 0.920)], 0.015, segments=8), 2),
        g.set_material_bm(bike_drivetrain(lib, bb=(wb * 0.42, 0.0, 0.300)), 1),
    ]
    # rear axle carrier and passenger tub
    for s in (1, -1):
        parts.append(g.set_material_bm(g.tube_bm([(0.40, 0, 0.480), (0.05, s * 0.50, R)], 0.022, segments=8), 0))
    parts.append(g.set_material_bm(g.rounded_box_bm((0.86, 1.08, 0.10), 0.05, segments=2,
                                                    center=(-0.10, 0, 0.640)), 0))
    parts.append(g.set_material_bm(g.rounded_box_bm((0.90, 1.24, 0.62), 0.10, segments=3,
                                                    center=(-0.30, 0, 0.860)), 0))
    parts.append(g.set_material_bm(g.rounded_box_bm((0.62, 1.00, 0.14), 0.05, segments=2,
                                                    center=(0.02, 0, 0.760)), 3))
    parts.append(g.set_material_bm(g.rounded_box_bm((0.12, 1.00, 0.52), 0.05, segments=2,
                                                    center=(-0.28, 0, 1.020)), 3))
    # canopy: four posts and a curved roof
    for sx, sy in ((0.30, 1), (0.30, -1), (-0.52, 1), (-0.52, -1)):
        parts.append(g.set_material_bm(g.tube_bm([(sx, sy * 0.58, 0.700), (sx, sy * 0.61, 1.640)], 0.014,
                                                 segments=6), 2))
    roof_pts = [(0.36, 0.0, 1.690), (0.0, 0.0, 1.745), (-0.58, 0.0, 1.705)]
    parts.append(g.set_material_bm(g.ribbon_bm(roof_pts, 1.16, up=(0, 0, 1), material_index=4), 4))
    parts.append(g.set_material_bm(g.box_bm((0.98, 1.24, 0.026), (-0.10, 0, 1.712)), 4))
    body = g.to_object("Body", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=42.0)
    v.add(body)
    w = spoked_wheel("Wheel_F", radius=R, tyre=0.050, lib=lib, spokes=32)
    w.location = (wb, 0.0, R)
    v.add(w)
    for tag, s in (("RL", 1), ("RR", -1)):
        w = spoked_wheel(f"Wheel_{tag}", radius=R, tyre=0.050, lib=lib, spokes=32)
        w.location = (0.0, s * d.y_track_rear, R)
        v.add(w)
    v.add(P.mirror(1, lib, x=wb * 0.80, y=0.30, z=1.120, w=0.10, h=0.070, d=0.045, repeater=False, arm=0.07))
    v.add(lamp_slot("LIGHT_HEAD_L", lib.light_white("LIGHT_HEAD_L"), (wb + 0.05, 0.0, 0.900), 0.034))
    for s, tag in ((1, "L"), (-1, "R")):
        v.add(lamp_slot(f"LIGHT_TAIL_{tag}", lib.light_red(f"LIGHT_TAIL_{tag}"),
                        (-0.648, s * 0.30, 0.860), 0.030, depth=0.03))
    v.add(small_plate(lib, "Plate_R", "PC 419", (-0.652, 0.0, 0.700), (-1, 0, 0), w=0.155, h=0.100))
    rig.add_damage_regions(body, d, z_belt=0.85)
    add_ucx(v, d, 0.85, slices=3)
    return finish(v, lod_budgets=(10_000, 2_200), tri_budget=45_000)


# --------------------------------------------------------------------------- horse carriage
def horse_carriage() -> dict:
    """**Central Park vis-à-vis carriage with one horse**.

    Carriage: length 3 600 mm, width 1 650 mm, height 2 200 mm over the raised hood, wheelbase 1 900 mm,
    rear wheels 1 200 mm diameter, front wheels 900 mm.  With the horse and shafts the whole rig is ~6.4 m
    long; the horse is placed ahead of the carriage in the same file and its extent is reported in
    ``measured_m`` under ``height_over_roof_equipment_m`` / the ``rig_length_m`` note.

    Fidelity (stated honestly): the horse is a **procedural animal**, built from tapered capsules and
    revolved sections at the published proportions of a light draught horse (withers 1.60 m, body length
    2.10 m, cannon 0.34 m).  It reads correctly in silhouette and at street distance; it is *not*
    anatomically sculpted, has no hair cards for mane/tail (they are solid tapered forms) and is not rigged
    or animated in this glb.
    """
    d = Dimensions(length_mm=3600, width_mm=1650, height_mm=2200, wheelbase_mm=1900,
                   track_front_mm=1360, track_rear_mm=1500, wheel_diameter_mm=1200, tyre_width_mm=60,
                   front_overhang_mm=800, rear_overhang_mm=900, rim_diameter_in=44.0, tyre_spec="steel tyre",
                   ground_clearance_mm=380)
    nb.reset_scene()
    lib = M.Library()
    R = d.wheel_radius            # 0.60 m rear
    Rf = 0.45                     # front wheels are smaller so they can turn under the body
    v = Vehicle(id="horse_carriage", display_name="Central Park horse carriage with horse", vclass="carriage",
                dims=d, z_belt=1.05, contract_profile="open",
                contract_waivers={n: "an open carriage has no cabin, doors, glazing, wipers or lamps of that kind"
                                  for n in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Hood", "Trunk",
                                            "Wiper_L", "Wiper_R", "Window_WS", "Window_BACK", "Window_FL",
                                            "Window_FR", "Window_RL", "Window_RR", "Mirror_L", "Mirror_R",
                                            "Interior_Dash", "Shifter", "Pedals", "Plate_F", "SteeringWheel")},
                extra_slots=("PLATE_FACE",),
                sources=["NYC DCWP horse-drawn cab rules; typical vis-a-vis carriage dimensions"],
                notes={"role": "Central Park carriage (ADR-009)"})
    v.notes["fidelity"] = ("horse is procedural: capsule/revolve anatomy at published light-draught "
                           "proportions, solid mane and tail, no rig and no hair cards")
    lac = lib.paint((0.02, 0.05, 0.10), "BODY_PAINT_carriage", metallic=0.15, roughness=0.22)
    mats = [lac, lib.wood(), lib.leather(name="LEATHER_CARRIAGE"), lib.brushed_metal(),
            lib.canvas((0.06, 0.06, 0.07), "CARRIAGE_HOOD"), lib.horse_coat(), lib.chrome()]
    IDX_LAC, IDX_WOOD, IDX_LEATHER, IDX_METAL, IDX_HOOD, IDX_HORSE, IDX_BRASS = range(7)
    parts = []
    # chassis: two side rails, a footboard, the body tub and two facing bench seats
    for s in (1, -1):
        parts.append(g.set_material_bm(g.box_bm((3.35, 0.07, 0.09), (0.90, s * 0.62, 0.86)), IDX_WOOD))
    parts.append(g.set_material_bm(g.rounded_box_bm((1.90, 1.30, 0.52), 0.10, segments=3,
                                                    center=(0.60, 0, 1.16)), IDX_LAC))
    parts.append(g.set_material_bm(g.box_bm((0.95, 1.20, 0.06), (2.10, 0, 1.00)), IDX_WOOD))
    for bx, back in ((0.05, -1), (1.15, 1)):
        parts.append(g.set_material_bm(g.rounded_box_bm((0.52, 1.16, 0.14), 0.05, segments=2,
                                                        center=(bx, 0, 1.40)), IDX_LEATHER))
        parts.append(g.set_material_bm(g.rounded_box_bm((0.12, 1.16, 0.50), 0.05, segments=2,
                                                        center=(bx + back * 0.30, 0, 1.66)), IDX_LEATHER))
    # driver's box
    parts.append(g.set_material_bm(g.rounded_box_bm((0.55, 1.10, 0.14), 0.05, segments=2,
                                                    center=(2.20, 0, 1.52)), IDX_LEATHER))
    parts.append(g.set_material_bm(g.box_bm((0.10, 1.10, 0.42), (1.92, 0, 1.78)), IDX_LEATHER))
    # folding hood over the rear bench
    for a in range(5):
        t = a / 4
        parts.append(g.set_material_bm(g.torus_bm(0.62, 0.020, axis="Y", center=(-0.10 + t * 0.55, 0, 1.56),
                                                  segments=26, ring_segments=6,
                                                  arc=(math.radians(5), math.radians(175))), IDX_METAL))
    parts.append(g.set_material_bm(g.ribbon_bm([(0.45, 0, 2.17), (0.05, 0, 2.19), (-0.42, 0, 1.95)], 1.24,
                                               up=(0, 0, 1)), IDX_HOOD))
    # lamps on the dash rail
    for s in (1, -1):
        parts.append(g.set_material_bm(g.box_bm((0.12, 0.12, 0.26), (2.62, s * 0.60, 1.74)), IDX_BRASS))
    body = g.to_object("Body", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=42.0)
    v.add(body)
    # the shafts and the horse stand ahead of the published carriage envelope, so they are separate objects
    # (rig.Vehicle.ENVELOPE_EXCLUDE) and the whole rig length is reported as ``rig_length_m``.
    shafts = []
    for s in (1, -1):
        shafts.append(g.set_material_bm(g.tube_bm([(2.35, s * 0.30, 1.00), (3.80, s * 0.34, 1.10),
                                                   (5.30, s * 0.34, 1.28)], 0.030, segments=8), 0))
    v.add(g.to_object("Shafts", g.merge_bm(shafts), [lib.wood()], smooth=True, sharp_angle_deg=44.0))
    for tag, x, rr, y in (("RL", 0.0, R, d.y_track_rear), ("RR", 0.0, R, -d.y_track_rear),
                          ("FL", 1.90, Rf, d.y_track_front), ("FR", 1.90, Rf, -d.y_track_front)):
        w = carriage_wheel(f"Wheel_{tag}", radius=rr, lib=lib, spokes=14)
        w.location = (x, y, rr)
        v.add(w)
    v.add(lamp_slot("LIGHT_HEAD_L", lib.light_white("LIGHT_HEAD_L"), (2.68, 0.60, 1.74), 0.036))
    v.add(lamp_slot("LIGHT_HEAD_R", lib.light_white("LIGHT_HEAD_R"), (2.68, -0.60, 1.74), 0.036))
    v.add(lamp_slot("LIGHT_TAIL_L", lib.light_red("LIGHT_TAIL_L"), (-0.898, 0.42, 1.10), 0.032))
    v.add(lamp_slot("LIGHT_TAIL_R", lib.light_red("LIGHT_TAIL_R"), (-0.898, -0.42, 1.10), 0.032))
    v.add(small_plate(lib, "Plate_R", "HDC 88", (-0.902, 0.0, 0.90), (-1, 0, 0), w=0.16, h=0.10))
    v.add(build_horse(lib, x0=3.35))
    rig.add_damage_regions(body, d, z_belt=1.05)
    add_ucx(v, d, 1.05, slices=3)
    return finish(v, lod_budgets=(16_000, 3_000), tri_budget=60_000,
                  extra_catalog={"rig_length_m": 7.28,
                                 "horse": {"withers_m": 1.60, "body_length_m": 2.10,
                                           "method": "procedural capsules + revolves; not sculpted, not rigged"}})


def carriage_wheel(name: str, *, radius: float, lib: M.Library, spokes: int = 14) -> bpy.types.Object:
    mats = [lib.wood(), lib.steel_painted((0.20, 0.20, 0.22), "TYRE_STEEL")]
    parts = [g.set_material_bm(g.torus_bm(radius - 0.018, 0.018, axis="Y", segments=44, ring_segments=8), 1),
             g.set_material_bm(g.torus_bm(radius - 0.055, 0.038, axis="Y", segments=40, ring_segments=8), 0),
             g.set_material_bm(g.cylinder_bm(0.055, 0.150, axis="Y", segments=16), 0)]
    for k in range(spokes):
        a = TAU * k / spokes
        p0 = (0.045 * math.cos(a), 0.0, 0.045 * math.sin(a))
        p1 = ((radius - 0.075) * math.cos(a), 0.0, (radius - 0.075) * math.sin(a))
        parts.append(g.set_material_bm(g.tube_bm([p0, p1], 0.016, segments=6), 0))
    return g.to_object(name, g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=44.0)


def build_horse(lib: M.Library, *, x0: float) -> bpy.types.Object:
    """Procedural light-draught horse: withers 1.60 m, body 2.10 m, cannon 0.34 m.  See the module docstring
    for the honest fidelity statement."""
    coat = lib.horse_coat()
    mats = [coat, lib.horse_coat((0.05, 0.03, 0.02)), lib.leather(name="LEATHER_HARNESS"), lib.brushed_metal()]
    W = 1.60
    parts = []
    # barrel: a lofted body from the chest to the croup
    stations = []
    prof = [(-0.05, 0.30, 1.02), (0.35, 0.36, 1.08), (0.95, 0.38, 1.12), (1.55, 0.34, 1.10), (2.05, 0.26, 1.05)]
    for px, py, pz in prof:
        ring = []
        for k in range(14):
            a = TAU * k / 14
            ring.append((x0 + px, py * math.cos(a), pz + 0.44 * math.sin(a) * (1.0 + 0.12 * math.cos(a))))
        stations.append(ring)
    barrel, _ = g.loft(stations, close_loop=True)
    g.fill_holes(barrel, material_index=0)
    g.set_material_bm(barrel, 0)
    parts.append(barrel)
    # neck and head
    parts.append(g.set_material_bm(g.tube_bm([(x0 + 1.95, 0, 1.42), (x0 + 2.35, 0, 1.66), (x0 + 2.62, 0, 1.72)],
                                             [0.20, 0.16, 0.11], segments=12), 0))
    head = g.sphere_bm((0.27, 0.11, 0.15), center=(x0 + 2.82, 0, 1.66), segments=18, rings=10, material_index=0)
    parts.append(head)
    parts.append(g.set_material_bm(g.sphere_bm((0.10, 0.075, 0.085), center=(x0 + 3.03, 0, 1.60),
                                               segments=14, rings=8), 0))
    for s in (1, -1):
        parts.append(g.set_material_bm(g.cylinder_bm(0.030, 0.11, axis=(0.2, s * 0.35, 1.0),
                                                     center=(x0 + 2.66, s * 0.085, 1.80), segments=8,
                                                     radius2=0.006), 0))
    # mane and tail (solid tapered forms, not hair cards)
    parts.append(g.set_material_bm(g.ribbon_bm([(x0 + 2.62, 0, 1.80), (x0 + 2.30, 0, 1.76), (x0 + 1.98, 0, 1.52)],
                                               0.075, up=(0, 1, 0)), 1))
    parts.append(g.set_material_bm(g.tube_bm([(x0 - 0.06, 0, 1.28), (x0 - 0.22, 0, 1.00), (x0 - 0.26, 0, 0.62)],
                                             [0.075, 0.060, 0.030], segments=8), 1))
    # legs: fore and hind, each shoulder -> knee -> cannon -> hoof
    def leg(bx: float, by: float, top_z: float, fore: bool):
        knee = (bx + (0.05 if fore else -0.06), by, 0.78)
        fet = (bx + (0.02 if fore else -0.02), by, 0.34)
        hoof = (bx, by, 0.055)
        out = [g.tube_bm([(bx + (0.02 if fore else -0.10), by, top_z), knee], [0.105, 0.058], segments=8,
                         material_index=0),
               g.tube_bm([knee, fet], [0.052, 0.034], segments=8, material_index=0),
               g.tube_bm([fet, hoof], [0.038, 0.052], segments=8, material_index=0),
               g.cylinder_bm(0.058, 0.11, axis="Z", center=(bx, by, 0.055), segments=12, material_index=1)]
        return out
    for s in (1, -1):
        parts += leg(x0 + 1.86, s * 0.19, 1.28, True)
        parts += leg(x0 + 0.16, s * 0.21, 1.26, False)
    # harness: collar, traces, bridle
    parts.append(g.set_material_bm(g.torus_bm(0.30, 0.045, axis=(1, 0, 0.55), center=(x0 + 2.12, 0, 1.44),
                                              segments=26, ring_segments=8), 2))
    for s in (1, -1):
        parts.append(g.set_material_bm(g.tube_bm([(x0 + 2.10, s * 0.30, 1.36), (x0 + 0.80, s * 0.36, 1.20),
                                                  (x0 - 0.20, s * 0.36, 1.10)], 0.022, segments=6), 2))
        parts.append(g.set_material_bm(g.tube_bm([(x0 + 2.66, s * 0.085, 1.74), (x0 + 2.92, s * 0.085, 1.62)],
                                                 0.014, segments=6), 2))
    ob = g.to_object("Horse", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=44.0)
    return ob


ALL = {
    "citibike_cruiser": citibike,
    "arrow_ebike": arrow_ebike,
    "moped_scooter": moped,
    "pedicab": pedicab,
    "horse_carriage": horse_carriage,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    env.ensure_dirs()
    ids = [i.strip() for i in args.only.split(",") if i.strip()] or list(ALL)
    for vid in ids:
        e = ALL[vid]()
        print(f"{e['id']:>26s}  {e['triangles']:>7d} tris  LOD1 {e['lods'][1]['triangles']:>6d}  "
              f"LOD2 {e['lods'][2]['triangles']:>5d}  dev L/W/H "
              f"{e['dimension_deviation_pct']['length_pct']:+.2f}/"
              f"{e['dimension_deviation_pct']['width_pct']:+.2f}/"
              f"{e['dimension_deviation_pct']['height_pct']:+.2f} %")
    return 0


if __name__ == "__main__":
    code = main()
    env.finish(code)
