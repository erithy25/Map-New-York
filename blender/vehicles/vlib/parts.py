"""Reusable exterior parts: wheels, wheel wells, lamps, mirrors, wipers, handles, exhausts, plates, badges,
roof boxes, light bars and destination signs.

Every function returns bpy objects already named with their **engine binding name** where the contract defines
one (``Wheel_FL``, ``LIGHT_TAIL_R``, ``Plate_F`` …) and with the matching material slot name, so the glb node
list and the glb material list are both binding tables.  Geometry is authored in the vehicle frame
(origin on the ground under the rear-axle centre, +X forward, +Y left, +Z up) except for wheels, which are
authored around their own hub so the object origin is the hub centre.
"""
from __future__ import annotations

import math
from typing import Sequence

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import env, geom as g, materials as M, textures as TX
from .blueprint import Blueprint, Dimensions

log = env.log
TAU = 2.0 * math.pi


# --------------------------------------------------------------------------- wheels
def wheel(name: str, dims: Dimensions, lib: M.Library, *, style: str = "alloy10", segments: int = 48,
          spokes: int = 10, sidewall_texture=None, disc: bool = True, dual: bool = False,
          rim_material=None) -> object:
    """One wheel authored around its own hub centre (axle along ±Y).  ``style``:
    ``alloy5`` / ``alloy10`` (passenger alloys), ``steel`` (hubcap-less steel), ``truck`` (10-stud hub-piloted).

    The rolling radius is ``dims.wheel_radius`` exactly, so the pivot sits at the hub centre and the tyre
    touches z = 0 when the object is placed at ``(x, y, dims.wheel_radius)``.
    """
    R = dims.wheel_radius
    W = dims.tyre_width * (2.05 if dual else 1.0)
    Rr = dims.rim_radius
    tyre_mat = lib.tyre(sidewall_texture)
    rim_mat = rim_material or (lib.steel_wheel() if style == "steel" else
                               lib.alloy("WHEEL_HUB_STEEL") if style == "truck" else lib.alloy())
    mats = [tyre_mat, rim_mat, lib.brake_disc(), lib.caliper(), lib.black_plastic()]
    parts: list[bmesh.types.BMesh] = []

    # --- tyre carcass: revolve a (radius, axial) profile about Y
    hw = W / 2.0
    bead = Rr + 0.004
    prof = [(bead, -hw * 0.86), (Rr + 0.020, -hw * 0.96), (R * 0.935, -hw * 1.00), (R * 0.985, -hw * 0.88),
            (R, -hw * 0.74), (R, hw * 0.74), (R * 0.985, hw * 0.88), (R * 0.935, hw * 1.00),
            (Rr + 0.020, hw * 0.96), (bead, hw * 0.86)]
    parts.append(g.set_material_bm(g.revolve_bm(prof, axis="Y", segments=segments, close=False), 0))

    # --- tread blocks: a shallow ribbed band so the contact patch is not a smooth cylinder
    nb = max(24, segments)
    for k in range(nb):
        a0 = TAU * k / nb
        if k % 2:
            continue
        # the block's outer face sits exactly on the rolling radius: anything beyond it would make the tyre
        # larger than the published size and push the vehicle's measured height over the published value
        b = g.box_bm((R * 0.012, W * 0.62, R * 0.012), (0, 0, 0), material_index=0)
        g.transform_bm(b, Matrix.Rotation(a0, 4, "Y") @ Matrix.Translation(Vector((R * 0.994, 0, 0))))
        parts.append(b)

    # --- rim barrel
    rim_prof = [(Rr, -hw * 0.84), (Rr * 0.96, -hw * 0.55), (Rr * 0.60, -hw * 0.30), (Rr * 0.55, hw * 0.10),
                (Rr * 0.62, hw * 0.42), (Rr * 0.98, hw * 0.66), (Rr, hw * 0.84)]
    parts.append(g.set_material_bm(g.revolve_bm(rim_prof, axis="Y", segments=segments, close=False), 1))
    # outer lip
    parts.append(g.set_material_bm(g.torus_bm(Rr - 0.012, 0.014, axis="Y", center=(0, hw * 0.82, 0),
                                              segments=segments, ring_segments=8), 1))

    # --- face: hub, spokes
    hub_r = Rr * 0.30
    parts.append(g.set_material_bm(g.cylinder_bm(hub_r, 0.05, axis="Y", center=(0, hw * 0.62, 0), segments=24), 1))
    n_sp = 5 if style == "alloy5" else 10 if style == "alloy10" else 8 if style == "truck" else 6
    n_sp = spokes if style.startswith("alloy") and spokes else n_sp
    if style == "steel":
        # pressed-steel disc with ventilation holes cut as an annulus of gaps
        parts.append(g.set_material_bm(g.revolve_bm([(hub_r, hw * 0.60), (Rr * 0.55, hw * 0.66),
                                                     (Rr * 0.88, hw * 0.72), (Rr * 0.99, hw * 0.80)],
                                                    axis="Y", segments=segments), 1))
        for k in range(8):
            a = TAU * k / 8
            h = g.cylinder_bm(Rr * 0.10, 0.02, axis="Y", center=(0, hw * 0.70, 0), segments=10)
            g.transform_bm(h, Matrix.Rotation(a, 4, "Y") @ Matrix.Translation(Vector((Rr * 0.62, 0, 0))))
            parts.append(g.set_material_bm(h, 4))
    else:
        for k in range(n_sp):
            a = TAU * k / n_sp
            length = Rr * 0.72
            sp = g.loft([
                [(hub_r * 0.95, hw * 0.50, -0.030), (hub_r * 0.95, hw * 0.66, -0.026),
                 (hub_r * 0.95, hw * 0.66, 0.030), (hub_r * 0.95, hw * 0.50, 0.034)],
                [(hub_r + length * 0.55, hw * 0.60, -0.024), (hub_r + length * 0.55, hw * 0.74, -0.020),
                 (hub_r + length * 0.55, hw * 0.74, 0.024), (hub_r + length * 0.55, hw * 0.60, 0.028)],
                [(Rr * 0.995, hw * 0.66, -0.017), (Rr * 0.995, hw * 0.80, -0.014),
                 (Rr * 0.995, hw * 0.80, 0.017), (Rr * 0.995, hw * 0.66, 0.020)],
            ], close_loop=True)[0]
            g.fill_holes(sp, material_index=1)
            g.set_material_bm(sp, 1)
            # the loft above is authored in (x=radius, y=axial, z=tangential); rotate it around Y
            g.transform_bm(sp, Matrix.Rotation(a, 4, "Y"))
            parts.append(sp)
        # lug bolts
        for k in range(5 if style != "truck" else 10):
            a = TAU * k / (5 if style != "truck" else 10)
            lb = g.cylinder_bm(0.010, 0.016, axis="Y", center=(0, hw * 0.66, 0), segments=8)
            g.transform_bm(lb, Matrix.Rotation(a, 4, "Y") @ Matrix.Translation(Vector((hub_r * 0.62, 0, 0))))
            parts.append(g.set_material_bm(lb, 1))

    # --- brake disc + caliper, visible through the spokes
    if disc:
        dr = Rr * 0.86
        parts.append(g.set_material_bm(g.cylinder_bm(dr, 0.026, axis="Y", center=(0, -hw * 0.05, 0), segments=36), 2))
        parts.append(g.set_material_bm(g.cylinder_bm(dr * 0.42, 0.06, axis="Y", center=(0, -hw * 0.18, 0), segments=24), 2))
        cal = g.rounded_box_bm((0.055, 0.10, 0.16), 0.012, center=(-dr * 0.55, -hw * 0.05, dr * 0.55), material_index=3)
        g.rotate_bm(cal, "Y", -35.0)
        parts.append(cal)

    bm = g.merge_bm(parts)
    ob = g.to_object(name, bm, mats, smooth=True, sharp_angle_deg=38.0)
    # UV: u around the wheel, v across the tyre profile (so sidewall lettering lands upright)
    g.uv_project(ob, lambda co, n: (((math.atan2(co.z, co.x) / TAU) % 1.0) * 4.0,
                                    0.5 + co.y / max(1e-6, W)))
    return ob


def place_wheels(dims: Dimensions, lib: M.Library, *, style: str = "alloy10", spokes: int = 10,
                 sidewall_texture=None, disc: bool = True, dual_rear: bool = False,
                 x_front: float | None = None, x_rear: float = 0.0,
                 rim_material=None) -> dict[str, object]:
    """The four contract wheels ``Wheel_FL/FR/RL/RR``, pivots exactly at the hub centres."""
    xf = dims.x_axle_front if x_front is None else x_front
    out: dict[str, object] = {}
    for tag, x, y, dual in (("FL", xf, dims.y_track_front, False), ("FR", xf, -dims.y_track_front, False),
                            ("RL", x_rear, dims.y_track_rear, dual_rear), ("RR", x_rear, -dims.y_track_rear, dual_rear)):
        ob = wheel(f"Wheel_{tag}", dims, lib, style=style, spokes=spokes, sidewall_texture=sidewall_texture,
                   disc=disc, dual=dual, rim_material=rim_material)
        if y < 0:                      # right-hand wheels: face the rim design outboard
            ob.data.transform(Matrix.Rotation(math.pi, 4, "Z"))
            ob.data.update()
        ob.location = (x, y, dims.wheel_radius)
        out[f"Wheel_{tag}"] = ob
    return out


def wheel_well(name: str, bp: Blueprint, hub_x: float, *, y_out: float, y_in: float, lib: M.Library,
               segments: int = 20, side: int = 1) -> object:
    """Inner arch liner: a swept arc from the arch lip inboard, closed by a wall, both sides of the car."""
    r = bp.arch_radius_f if hub_x > 1e-6 else bp.arch_radius_r
    hz = bp.hub_z
    a0, a1 = math.radians(-8.0), math.radians(188.0)
    arc = [(hub_x + r * math.cos(a0 + (a1 - a0) * k / segments), 0.0,
            hz + r * math.sin(a0 + (a1 - a0) * k / segments)) for k in range(segments + 1)]
    yo, yi = side * y_out, side * y_in
    bm, _ = g.loft([[(p[0], yo, p[2]) for p in arc], [(p[0], yi, p[2]) for p in arc]])
    wall = g.ngon_bm([(p[0], yi, p[2]) for p in arc] + [(hub_x + r, yi, hz - 0.02), (hub_x - r, yi, hz - 0.02)],
                     flip=side < 0)
    bm = g.merge_bm([bm, wall])
    g.set_material_bm(bm, 0)
    return g.to_object(name, bm, [lib.black_plastic()], smooth=False)


# --------------------------------------------------------------------------- lamps
def _lens(points_xyz: Sequence[Sequence[float]], depth: float, mat_index: int = 0) -> bmesh.types.BMesh:
    """A lens tile: a quad pushed ``depth`` along -X (or its own normal for side lamps)."""
    return g.quad_uv01_bm(points_xyz, material_index=mat_index)


def lamp_panel(name: str, mat, corners: Sequence[Sequence[float]], *, thickness: float = 0.03,
               inward: Sequence[float] = (-1, 0, 0)) -> object:
    """A lamp as a shallow lens box: the outer face carries the emissive slot material, the box gives it depth."""
    c = [Vector(p) for p in corners]
    n = Vector(inward).normalized() * thickness
    bm = g.quad_uv01_bm([tuple(p) for p in c])
    back = g.quad_uv01_bm([tuple(p + n) for p in reversed(c)])
    side_bms = [bm, back]
    for i in range(4):
        a, b = c[i], c[(i + 1) % 4]
        side_bms.append(g.quad_uv01_bm([tuple(a), tuple(b), tuple(b + n), tuple(a + n)]))
    out = g.merge_bm(side_bms)
    g.set_material_bm(out, 0)
    ob = g.to_object(name, out, [mat], smooth=False)
    g.set_origin(ob, tuple(sum(c, Vector((0, 0, 0))) / 4.0 + n * 0.5))
    return ob


def lamp_disc(name: str, mat, center: Sequence[float], radius: float, *, axis: str = "X", depth: float = 0.04,
              segments: int = 20) -> object:
    bm = g.cylinder_bm(radius, depth, axis=axis, center=tuple(center), segments=segments)
    g.set_material_bm(bm, 0)
    ob = g.to_object(name, bm, [mat], smooth=True, sharp_angle_deg=50.0)
    g.set_origin(ob, tuple(center))
    return ob


def headlamp_unit(prefix: str, side: int, lib: M.Library, *, x: float, y: float, z: float, w: float, h: float,
                  rake: float = 0.0, projector_r: float = 0.045) -> dict[str, object]:
    """One headlamp: the outer lens (``LIGHT_HEAD_L/R``), the low- and high-beam projectors and the DRL bar.
    Returns the objects keyed by their contract names; the ``LIGHT_LOW``/``LIGHT_HIGH``/``LIGHT_DRL`` pieces are
    returned per side and joined by the caller into the single contract objects."""
    s = 1 if side > 0 else -1
    tag = "L" if s > 0 else "R"
    dx = math.tan(math.radians(rake))
    corners = [(x - dx * h / 2, y - s * w / 2, z - h / 2), (x - dx * h / 2, y + s * w / 2, z - h / 2),
               (x + dx * h / 2, y + s * w / 2, z + h / 2), (x + dx * h / 2, y - s * w / 2, z + h / 2)]
    out = {f"LIGHT_HEAD_{tag}": lamp_panel(f"LIGHT_HEAD_{tag}", lib.light(f"LIGHT_HEAD_{tag}", (0.90, 0.92, 0.98), alpha=0.55),
                                           corners, thickness=0.075)}
    yl = y + s * w * 0.20
    yh = y - s * w * 0.16
    out[f"_low_{tag}"] = lamp_disc(f"LIGHT_LOW_{tag}", lib.light_white("LIGHT_LOW"), (x + 0.006, yl, z + h * 0.02),
                                   projector_r, axis="X", depth=0.035)
    out[f"_high_{tag}"] = lamp_disc(f"LIGHT_HIGH_{tag}", lib.light_white("LIGHT_HIGH"), (x + 0.006, yh, z - h * 0.10),
                                    projector_r * 0.80, axis="X", depth=0.032)
    drl = [(x + 0.008, y - s * w * 0.46, z + h * 0.30), (x + 0.008, y + s * w * 0.46, z + h * 0.30),
           (x + 0.008, y + s * w * 0.46, z + h * 0.42), (x + 0.008, y - s * w * 0.46, z + h * 0.42)]
    out[f"_drl_{tag}"] = lamp_panel(f"LIGHT_DRL_{tag}", lib.light_white("LIGHT_DRL"), drl, thickness=0.012)
    turn = [(x + 0.006, y + s * w * 0.16, z - h * 0.44), (x + 0.006, y + s * w * 0.48, z - h * 0.44),
            (x + 0.006, y + s * w * 0.48, z - h * 0.28), (x + 0.006, y + s * w * 0.16, z - h * 0.28)]
    out[f"LIGHT_TURN_F{tag}"] = lamp_panel(f"LIGHT_TURN_F{tag}", lib.light_amber(f"LIGHT_TURN_F{tag}"), turn, thickness=0.02)
    return out


def taillamp_unit(side: int, lib: M.Library, *, x: float, y: float, z: float, w: float, h: float,
                  reverse: bool = True) -> dict[str, object]:
    """One tail lamp cluster: tail, brake, indicator and (optionally) reverse slots."""
    s = 1 if side > 0 else -1
    tag = "L" if s > 0 else "R"
    def band(z0, z1, y0, y1, nm, mat):
        return lamp_panel(nm, mat, [(x, y + s * y0, z + z0), (x, y + s * y1, z + z0),
                                    (x, y + s * y1, z + z1), (x, y + s * y0, z + z1)],
                          thickness=0.055, inward=(1, 0, 0))
    out = {
        f"LIGHT_TAIL_{tag}": band(-h * 0.5, h * 0.5, -w * 0.5, w * 0.5, f"LIGHT_TAIL_{tag}",
                                  lib.light(f"LIGHT_TAIL_{tag}", (0.55, 0.02, 0.02), alpha=0.7)),
        f"LIGHT_BRAKE_{tag}": band(h * 0.10, h * 0.44, -w * 0.44, w * 0.20, f"LIGHT_BRAKE_{tag}",
                                   lib.light_red(f"LIGHT_BRAKE_{tag}")),
        f"LIGHT_TURN_R{tag}": band(-h * 0.44, -h * 0.06, -w * 0.44, w * 0.02, f"LIGHT_TURN_R{tag}",
                                   lib.light_amber(f"LIGHT_TURN_R{tag}")),
    }
    if reverse:
        out[f"_rev_{tag}"] = band(-h * 0.44, -h * 0.10, w * 0.10, w * 0.42, f"LIGHT_REVERSE_{tag}",
                                  lib.light_white(f"LIGHT_REVERSE_{tag}"))
    return out


def plate_light(lib: M.Library, x: float, z: float, y: float = 0.0, w: float = 0.10) -> object:
    return lamp_panel("LIGHT_PLATE", lib.light_white("LIGHT_PLATE"),
                      [(x, y - w / 2, z), (x, y + w / 2, z), (x, y + w / 2, z + 0.016), (x, y - w / 2, z + 0.016)],
                      thickness=0.014, inward=(1, 0, 0))


# --------------------------------------------------------------------------- mirrors, wipers, handles
def mirror(side: int, lib: M.Library, *, x: float, y: float, z: float, w: float = 0.185, h: float = 0.105,
           d: float = 0.085, repeater: bool = True, arm: float = 0.07) -> object:
    """Door mirror ``Mirror_L``/``Mirror_R`` with a ``MIRROR_GLASS`` slot and (optionally) a turn repeater."""
    s = 1 if side > 0 else -1
    tag = "L" if s > 0 else "R"
    mats = [lib.black_plastic(), lib.mirror_glass(), lib.light_amber(f"LIGHT_TURN_F{tag}")]
    yo = y + s * (arm + d / 2)
    shell = g.rounded_box_bm((0.135, d, h * 1.05), 0.028, segments=3, center=(x, yo, z), material_index=0)
    g.transform_bm(shell, Matrix.Translation(Vector((x, yo, z))) @ Matrix.Rotation(math.radians(-6 * s), 4, "X")
                   @ Matrix.Translation(Vector((-x, -yo, -z))))
    stalk = g.rounded_box_bm((0.055, arm + 0.03, 0.045), 0.014, center=(x - 0.01, y + s * (arm / 2), z - 0.012), material_index=0)
    glass = g.quad_uv01_bm([(x - 0.055, yo - s * (d / 2 - 0.004), z - h / 2), (x - 0.055, yo - s * (d / 2 - 0.004), z + h / 2),
                            (x + 0.048, yo - s * (d / 2 - 0.004), z + h / 2 - 0.004), (x + 0.048, yo - s * (d / 2 - 0.004), z - h / 2 + 0.004)],
                           material_index=1, double_sided=False)
    if s < 0:
        g.flip_bm(glass)
    parts = [shell, stalk, glass]
    if repeater:
        rep = g.box_bm((0.07, 0.012, 0.016), (x + 0.03, yo + s * (d / 2 - 0.002), z + 0.018), material_index=2)
        parts.append(rep)
    ob = g.to_object(f"Mirror_{tag}", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=38.0)
    g.set_origin(ob, (x - 0.01, y, z))       # pivot on the mirror base (power-fold axis)
    return ob


def wiper(side: int, lib: M.Library, *, pivot: Sequence[float], length: float, blade: float,
          park_deg: float = 8.0, arc_deg: float = -32.0, glass_slope: float = 0.46) -> object:
    """``Wiper_L``/``Wiper_R``: arm + blade lying **up the windshield**, i.e. towards -X and +Z (+X is forward,
    so the glass is behind the cowl).  ``glass_slope`` is dz/|dx| of the windshield.  The object origin is
    exactly on the spindle so the engine rotates the whole assembly about its local Z."""
    s = 1 if side > 0 else -1
    tag = "L" if s > 0 else "R"
    px, py, pz = pivot
    mats = [lib.black_plastic(), lib.rubber()]
    a = math.radians(park_deg * s + arc_deg * 0)
    arm_path = [(0.0, 0.0, 0.0),
                (-length * 0.45, s * length * 0.10, length * 0.45 * glass_slope),
                (-length * 0.80, s * length * 0.16, length * 0.80 * glass_slope)]
    arm = g.tube_bm(arm_path, [0.011, 0.008, 0.007], segments=8, material_index=0)
    spindle = g.cylinder_bm(0.014, 0.05, axis="Z", center=(0, 0, -0.012), segments=12, material_index=0)
    bx = -length * 0.80
    by = s * length * 0.16
    bz = length * 0.80 * glass_slope
    # the blade box is built along +Y (tangential); rotating it by the arm's polar angle keeps it
    # perpendicular to the arm, which is how a wiper blade sits.
    swing = math.degrees(math.atan2(by, bx))
    blade_bm = g.box_bm((0.012, blade, 0.020), (bx, by, bz + 0.016), material_index=0)
    g.rotate_bm(blade_bm, "Z", swing, center=(bx, by, bz + 0.016))
    rub = g.box_bm((0.006, blade * 0.98, 0.011), (bx, by, bz + 0.003), material_index=1)
    g.rotate_bm(rub, "Z", swing, center=(bx, by, bz + 0.003))
    bm = g.merge_bm([arm, spindle, blade_bm, rub])
    g.rotate_bm(bm, "Z", math.degrees(a))
    ob = g.to_object(f"Wiper_{tag}", bm, mats, smooth=True, sharp_angle_deg=40.0)
    ob.location = (px, py, pz)
    return ob


def door_handle(lib: M.Library, x: float, y: float, z: float, *, length: float = 0.155, chrome: bool = False) -> bmesh.types.BMesh:
    # ``y`` is the door skin surface; the grab bar protrudes 20 mm, which is what keeps a slab-sided van
    # inside its published width (published width excludes mirrors but includes door handles).
    s = 1 if y > 0 else -1
    bar = g.rounded_box_bm((length, 0.024, 0.028), 0.010, center=(x, y + s * 0.008, z), material_index=0)
    rec = g.box_bm((length + 0.03, 0.020, 0.048), (x, y - s * 0.008, z), material_index=0)
    return g.merge_bm([bar, rec])


def exhaust(lib: M.Library, *, x_tip: float, y: float, z: float, r: float = 0.032, length: float = 0.9,
            tips: int = 1, spacing: float = 0.14, chrome_tip: bool = True) -> object:
    mats = [lib.steel_painted((0.28, 0.28, 0.29), "EXHAUST_STEEL"), lib.chrome()]
    parts = []
    for k in range(tips):
        yy = y + (k - (tips - 1) / 2.0) * spacing
        parts.append(g.set_material_bm(g.cylinder_bm(r * 0.8, length, axis="X", center=(x_tip + length / 2, yy, z), segments=14), 0))
        parts.append(g.set_material_bm(g.cylinder_bm(r, 0.10, axis="X", center=(x_tip + 0.05, yy, z), segments=18), 1 if chrome_tip else 0))
    box = g.rounded_box_bm((0.42, 0.30, 0.14), 0.04, center=(x_tip + length * 0.85, y, z + 0.02), material_index=0)
    parts.append(box)
    return g.to_object("Exhaust", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=40.0)


def badge(text: str, lib: M.Library, *, center: Sequence[float], normal: Sequence[float], size: float,
          material=None, font: str = g.FONT_SANS_BOLD) -> bmesh.types.BMesh:
    bm = g.text_on_surface_bm(text, size=size, depth=0.0018, center=tuple(center), normal=tuple(normal), font_path=font)
    return bm


def plate(name: str, lib: M.Library, image, *, center: Sequence[float], normal: Sequence[float],
          w: float = 0.305, h: float = 0.152, rake: float = 0.0) -> object:
    """``Plate_F`` / ``Plate_R``: a 12 × 6 in US plate with a ``PLATE_FACE`` slot, UV exactly 0..1."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    up = (up - n * up.dot(n)).normalized()
    r = up.cross(n).normalized()
    c = Vector(center)
    corners = [c - r * w / 2 - up * h / 2, c + r * w / 2 - up * h / 2, c + r * w / 2 + up * h / 2, c - r * w / 2 + up * h / 2]
    face = g.quad_uv01_bm([tuple(p) for p in corners], material_index=0)
    back = g.quad_uv01_bm([tuple(p - n * 0.006) for p in reversed(corners)], material_index=1)
    rim = []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        rim.append(g.quad_uv01_bm([tuple(a), tuple(b), tuple(b - n * 0.006), tuple(a - n * 0.006)], material_index=1))
    ob = g.to_object(name, g.merge_bm([face, back, *rim]), [lib.plate(image), lib.steel_painted((0.6, 0.6, 0.6), "PLATE_BACK")],
                     smooth=False)
    g.set_origin(ob, tuple(c))
    return ob


# --------------------------------------------------------------------------- roof furniture
def taxi_roof_light(lib: M.Library, *, x: float, z: float, medallion_image, w: float = 0.62, h: float = 0.115,
                    d: float = 0.20) -> object:
    """NYC medallion roof box: an illuminated number panel on both sides (``TAXI_ROOF`` slot)."""
    mats = [M.basic("TAXI_ROOF_BOX", (0.02, 0.02, 0.02), roughness=0.45),
            lib.decal("TAXI_ROOF", medallion_image, emissive=True, strength=1.4)]
    shell = g.rounded_box_bm((w, d, h), 0.018, segments=2, center=(x, 0, z + h / 2), material_index=0)
    faces = []
    for s in (1, -1):
        y = s * (d / 2 + 0.002)
        c = [(x - w * 0.46, y, z + h * 0.16), (x + w * 0.46, y, z + h * 0.16),
             (x + w * 0.46, y, z + h * 0.90), (x - w * 0.46, y, z + h * 0.90)]
        q = g.quad_uv01_bm(c if s > 0 else list(reversed(c)), material_index=1)
        faces.append(q)
    return g.to_object("TAXI_ROOF", g.merge_bm([shell, *faces]), mats, smooth=False)


def light_bar(lib: M.Library, *, x: float, z: float, w: float = 1.30, h: float = 0.115, d: float = 0.28,
              modules: int = 8) -> object:
    """Police light bar with ``LIGHT_EMERGENCY_R`` / ``LIGHT_EMERGENCY_B`` alternating modules."""
    mats = [M.basic("LIGHTBAR_BASE", (0.02, 0.02, 0.02), roughness=0.4),
            lib.light("LIGHT_EMERGENCY_R", (1.0, 0.03, 0.02), alpha=0.6),
            lib.light("LIGHT_EMERGENCY_B", (0.05, 0.2, 1.0), alpha=0.6),
            lib.light_white("LIGHT_EMERGENCY_W")]
    parts = [g.rounded_box_bm((w, d, h * 0.55), 0.02, segments=2, center=(x, 0, z + h * 0.28), material_index=0)]
    for k in range(modules):
        u = (k + 0.5) / modules - 0.5
        mi = 1 if (k < modules / 2) else 2
        parts.append(g.box_bm((w / modules * 0.86, d * 0.98, h * 0.42), (x + u * w, 0, z + h * 0.72), material_index=mi))
    for s in (1, -1):
        parts.append(g.box_bm((w * 0.035, d * 0.5, h * 0.42), (x + s * w * 0.487, 0, z + h * 0.72),
                              material_index=1 if s > 0 else 2))
    parts.append(g.box_bm((w * 0.10, d * 0.35, h * 0.30), (x, 0, z + h * 0.72), material_index=3))
    return g.to_object("LightBar", g.merge_bm(parts), mats, smooth=False)


def destination_sign(name: str, lib: M.Library, image, corners: Sequence[Sequence[float]]) -> object:
    """``SIGN_FRONT`` / ``SIGN_SIDE`` / ``SIGN_REAR`` LED destination panel, UV exactly 0..1."""
    bm = g.quad_uv01_bm([tuple(c) for c in corners], material_index=0)
    return g.to_object(name, bm, [lib.led_matrix(name, image)], smooth=False)


# --------------------------------------------------------------------------- misc structure
def grille(lib: M.Library, *, x: float, z0: float, z1: float, y_half: float, bars: int = 6, rake: float = 0.10,
           material=None) -> bmesh.types.BMesh:
    mats_idx = 0
    parts = []
    for k in range(bars):
        t = (k + 0.5) / bars
        z = z0 + (z1 - z0) * t
        parts.append(g.box_bm((0.03, y_half * 2 * (1.0 - 0.04 * abs(t - 0.5)), (z1 - z0) / bars * 0.55),
                              (x - rake * t, 0, z), material_index=mats_idx))
    parts.append(g.box_bm((0.05, y_half * 2 * 1.02, z1 - z0), (x - rake * 0.5 - 0.05, 0, (z0 + z1) / 2), material_index=mats_idx))
    return g.merge_bm(parts)


def grille_surround(x: float, z0: float, z1: float, y_half: float, *, bar: float = 0.022,
                    material_index: int = 0) -> bmesh.types.BMesh:
    """Rectangular chrome frame around a grille aperture (a torus surround wraps far outside the nose)."""
    zc, h = 0.5 * (z0 + z1), (z1 - z0)
    parts = [g.box_bm((0.030, y_half * 2 + 2 * bar, bar), (x, 0, z1 + bar / 2), material_index=material_index),
             g.box_bm((0.030, y_half * 2 + 2 * bar, bar), (x, 0, z0 - bar / 2), material_index=material_index)]
    for s in (1, -1):
        parts.append(g.box_bm((0.030, bar, h + 2 * bar), (x, s * (y_half + bar / 2), zc),
                              material_index=material_index))
    return g.merge_bm(parts)


def step_bar(lib: M.Library, *, x0: float, x1: float, y: float, z: float, r: float = 0.032) -> bmesh.types.BMesh:
    return g.tube_bm([(x0, y, z), (x1, y, z)], r, segments=10, material_index=0)


def ladder_rungs(x0: float, x1: float, y: float, z0: float, z1: float, n: int, r: float = 0.018,
                 material_index: int = 0) -> bmesh.types.BMesh:
    parts = [g.tube_bm([(x0, y - 0.18, z0), (x1, y - 0.18, z1)], r, segments=8, material_index=material_index),
             g.tube_bm([(x0, y + 0.18, z0), (x1, y + 0.18, z1)], r, segments=8, material_index=material_index)]
    for k in range(n):
        t = (k + 0.5) / n
        parts.append(g.tube_bm([(g.lerp(x0, x1, t), y - 0.18, g.lerp(z0, z1, t)),
                                (g.lerp(x0, x1, t), y + 0.18, g.lerp(z0, z1, t))], r * 0.8, segments=6,
                               material_index=material_index))
    return g.merge_bm(parts)
