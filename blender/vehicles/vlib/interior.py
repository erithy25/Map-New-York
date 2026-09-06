"""Cabin interiors.

One parametric interior serves every enclosed vehicle: the caller supplies an :class:`InteriorSpec` (cabin
extents in the vehicle frame, seat rows, wheel position, detail level) and gets back the contract objects

    Interior_Dash        with the GAUGE_SPEED, GAUGE_RPM and SCREEN_CENTER slots (UV exactly 0..1 per face)
    SteeringWheel        origin on the column axis, local +Z along the column
    Seat_FL / Seat_FR / Seat_R<n>
    Shifter, Pedals, Interior_Console, Interior_Carpet, Interior_Headliner,
    Interior_DoorCard_FL/FR/RL/RR, Interior_Belts, Interior_Mirror, Interior_Visor_L/R

``detail='full'`` is the player-car interior (seams, piping, vents, switch pods, sun visors, grab handles);
``detail='mid'`` is the AI-fleet interior (same objects, coarser sections, no piping); ``detail='cab'`` is the
**driver station only** — dash with the gauge and screen slots, steering wheel and column, driver's seat,
shifter and pedals — which is what a bus, a coach, a fire truck or a box truck actually has behind the
windscreen (their saloon or body is furnished separately by the vehicle's ``extras`` hook).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import env, geom as g, materials as M, textures as TX

log = env.log
TAU = 2.0 * math.pi


@dataclass
class SeatSpot:
    x: float          # x of the seat H-point (hip point)
    y: float
    z: float          # z of the H-point
    name: str
    back_deg: float = 24.0
    width: float = 0.52
    bench: float = 0.0        # >0: a bench of this total width centred on y


@dataclass
class InteriorSpec:
    x_dash: float             # x of the dash face (rearmost point of the dash top pad)
    x_cowl: float             # x of the windshield base (front of the dash top)
    x_rear: float             # x of the rear bulkhead / boot bulkhead
    z_floor: float            # cabin floor height
    z_roof: float             # inner roof height at the centreline
    y_cabin: float            # inner half width at the beltline
    z_belt: float             # inner beltline height
    seats: Sequence[SeatSpot]
    wheel_center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    wheel_radius: float = 0.185
    column_deg: float = 25.0            # column axis below horizontal
    detail: str = "full"
    #: x of the windshield header.  The headliner, the sun visors and the interior mirror all hang from the
    #: roof, so they must start here and not at the cowl — starting at the cowl pushes them out through the
    #: raked windshield (seen in docs/verification/vehicles render 1).
    x_roof_front: float | None = None
    #: inner roof height as a function of x; a constant ``z_roof`` is used when this is not given.
    roof_line: Callable[[float], float] | None = None
    console: bool = True
    shifter: str = "rotary"             # rotary | lever | column | stalk
    doors_x: Sequence[tuple[float, float]] = ()   # door cut spans, front to rear
    gauge_images: tuple = ()            # (speed, rpm, centre screen) image paths
    plate_seed: int = 0
    headliner: bool = True
    left_hand_drive: bool = True

    @property
    def y_driver(self) -> float:
        return abs(self.seats[0].y) if self.seats else 0.38


# --------------------------------------------------------------------------- dash
def build_dash(sp: InteriorSpec, lib: M.Library) -> object:
    """The dash moulding plus the instrument binnacle, the centre stack and the vents, as one object whose
    material slots include ``GAUGE_SPEED``, ``GAUGE_RPM`` and ``SCREEN_CENTER``."""
    speed_img, rpm_img, screen_img = (sp.gauge_images + (None, None, None))[:3]
    mats = [lib.dash_soft(), lib.piano_black(), lib.dash_trim(),
            lib.screen("GAUGE_SPEED", speed_img) if speed_img else M.basic("GAUGE_SPEED", (0.02, 0.02, 0.02), roughness=0.2),
            lib.screen("GAUGE_RPM", rpm_img) if rpm_img else M.basic("GAUGE_RPM", (0.02, 0.02, 0.02), roughness=0.2),
            lib.screen("SCREEN_CENTER", screen_img) if screen_img else M.basic("SCREEN_CENTER", (0.02, 0.02, 0.02), roughness=0.2),
            lib.black_plastic()]
    IDX_SOFT, IDX_PIANO, IDX_TRIM, IDX_SPEED, IDX_RPM, IDX_SCREEN, IDX_PLASTIC = range(7)
    xd, xc, zf, zb = sp.x_dash, sp.x_cowl, sp.z_floor, sp.z_belt
    yc = sp.y_cabin
    # the dash top pad sits just below the cowl, ~105 mm above the beltline; everything mounted on the
    # dash (binnacle, vents, screen) must stay below it or it pokes through the top surface.
    z_top = zb + 0.105
    # side profile of the dash moulding, from the windshield base rearwards and down into the footwell
    prof = [(xc + 0.02, z_top - 0.02), (xc - 0.10, z_top), (xd + 0.05, z_top - 0.005), (xd, z_top - 0.075),
            (xd + 0.015, zb - 0.055), (xd - 0.02, zb - 0.16), (xd + 0.02, zb - 0.28),
            (xc - 0.02, zf + 0.10), (xc + 0.05, zf + 0.06), (xc + 0.05, z_top - 0.10)]
    body = g.extrude_profile_bm(prof, -yc * 0.985, yc * 0.985, material_index=IDX_SOFT, cap=True)
    parts = [body]

    ydrv = sp.y_driver if sp.left_hand_drive else -sp.y_driver
    sgn = 1.0 if sp.left_hand_drive else -1.0

    # --- instrument binnacle: hood + two round gauges + a strip LCD, facing the driver
    bz = zb + 0.040
    bx = xd - 0.005
    hood = g.rounded_box_bm((0.20, 0.44, 0.135), 0.030, segments=2, center=(bx - 0.06, ydrv, bz + 0.02), material_index=IDX_SOFT)
    parts.append(hood)
    face_n = (-1.0, 0.0, 0.22)
    for k, (slot, idx) in enumerate((("GAUGE_SPEED", IDX_SPEED), ("GAUGE_RPM", IDX_RPM))):
        gy = ydrv + (0.105 if k == 0 else -0.105) * sgn
        r = 0.072
        c = Vector((bx - 0.108, gy, bz + 0.012))
        n = Vector(face_n).normalized()
        up = Vector((0, 0, 1)); up = (up - n * up.dot(n)).normalized()
        rt = up.cross(n).normalized()
        quad = [c - rt * r - up * r, c + rt * r - up * r, c + rt * r + up * r, c - rt * r + up * r]
        parts.append(g.quad_uv01_bm([tuple(p) for p in quad], material_index=idx))
        ring = g.torus_bm(r * 1.06, 0.006, axis="X", center=tuple(c + n * 0.004), segments=28, ring_segments=6,
                          material_index=IDX_TRIM)
        parts.append(ring)
    lcd_c = Vector((bx - 0.107, ydrv, bz + 0.012))
    n = Vector(face_n).normalized(); up = Vector((0, 0, 1)); up = (up - n * up.dot(n)).normalized(); rt = up.cross(n).normalized()
    parts.append(g.quad_uv01_bm([tuple(lcd_c - rt * 0.055 - up * 0.048), tuple(lcd_c + rt * 0.055 - up * 0.048),
                                 tuple(lcd_c + rt * 0.055 + up * 0.048), tuple(lcd_c - rt * 0.055 + up * 0.048)],
                                material_index=IDX_PIANO))

    # --- centre stack: screen, HVAC panel, vents
    sx = xd - 0.02
    sc = Vector((sx - 0.055, 0.0, zb + 0.020))
    n = Vector((-1.0, 0.0, 0.16)).normalized(); up = Vector((0, 0, 1)); up = (up - n * up.dot(n)).normalized()
    rt = up.cross(n).normalized()
    sw, sh = 0.205, 0.118
    parts.append(g.quad_uv01_bm([tuple(sc - rt * sw - up * sh), tuple(sc + rt * sw - up * sh),
                                 tuple(sc + rt * sw + up * sh), tuple(sc - rt * sw + up * sh)],
                                material_index=IDX_SCREEN))
    parts.append(g.rounded_box_bm((0.055, sw * 2 + 0.035, sh * 2 + 0.035), 0.012, segments=2,
                                  center=(sx - 0.012, 0.0, zb + 0.020), material_index=IDX_PIANO))
    parts.append(g.rounded_box_bm((0.10, 0.36, 0.115), 0.018, segments=2, center=(sx - 0.03, 0, zb - 0.150),
                                  material_index=IDX_PIANO))
    for k in range(3):                                    # HVAC rotaries
        parts.append(g.cylinder_bm(0.026, 0.024, axis="X", center=(sx - 0.075, (k - 1) * 0.115, zb - 0.150),
                                   segments=16, material_index=IDX_TRIM))
    # vents (outer pair + centre pair) with slats
    for vy, vw in ((yc * 0.86, 0.115), (-yc * 0.86, 0.115), (0.125, 0.10), (-0.125, 0.10)):
        parts.append(g.rounded_box_bm((0.055, vw, 0.062), 0.010, segments=1, center=(sx - 0.028, vy, zb + 0.062),
                                      material_index=IDX_PIANO))
        if sp.detail == "full":
            for s in range(3):
                parts.append(g.box_bm((0.030, vw * 0.9, 0.005), (sx - 0.048, vy, zb + 0.062 + (s - 1) * 0.017),
                                      material_index=IDX_PLASTIC))
    # trim strip across the dash face
    parts.append(g.box_bm((0.030, yc * 1.72, 0.028), (sx - 0.014, 0, zb - 0.035), material_index=IDX_TRIM))
    # glovebox seam
    parts.append(g.rounded_box_bm((0.045, 0.44, 0.20), 0.014, segments=1,
                                  center=(sx - 0.020, -ydrv * 0.95, zb - 0.170), material_index=IDX_SOFT))

    ob = g.to_object("Interior_Dash", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=34.0)
    return ob


# --------------------------------------------------------------------------- steering wheel
def build_steering_wheel(sp: InteriorSpec, lib: M.Library) -> object:
    """3-spoke wheel with an airbag boss; origin on the column axis, local +Z along the column."""
    r = sp.wheel_radius
    mats = [lib.leather(name="LEATHER_WHEEL"), lib.piano_black(), lib.dash_trim()]
    parts = [g.set_material_bm(g.torus_bm(r, 0.0165, axis="Z", segments=44, ring_segments=12), 0)]
    for a in (90.0, 210.0, 330.0):
        rad = math.radians(a)
        sp_bm = g.box_bm((r * 0.86, 0.030, 0.016), (r * 0.43, 0, -0.012), material_index=1)
        g.rotate_bm(sp_bm, "Z", a)
        parts.append(sp_bm)
    parts.append(g.set_material_bm(g.rounded_box_bm((0.135, 0.135, 0.055), 0.030, segments=3, center=(0, 0, -0.020)), 1))
    for s in (1, -1):
        parts.append(g.set_material_bm(g.rounded_box_bm((0.052, 0.030, 0.012), 0.004,
                                                        center=(-0.012, s * 0.088, -0.030)), 2))
    bm = g.merge_bm(parts)
    ob = g.to_object("SteeringWheel", bm, mats, smooth=True, sharp_angle_deg=36.0)
    ob.matrix_world = Matrix.Translation(Vector(sp.wheel_center)) @ column_basis(sp.column_deg)
    return ob


def column_basis(column_deg: float) -> Matrix:
    """Rotation whose **local +Z is the steering-column axis** (forward and down by ``column_deg``) and whose
    local +Y is the vehicle's left.  ``Vector.to_track_quat`` does not guarantee which axis lands where, so
    the basis is written out explicitly."""
    zc = Vector((math.cos(math.radians(column_deg)), 0.0, -math.sin(math.radians(column_deg)))).normalized()
    yc = Vector((0.0, 1.0, 0.0))
    xc = yc.cross(zc).normalized()
    yc = zc.cross(xc).normalized()
    return Matrix(((xc.x, yc.x, zc.x, 0.0), (xc.y, yc.y, zc.y, 0.0), (xc.z, yc.z, zc.z, 0.0), (0.0, 0.0, 0.0, 1.0)))


def build_column(sp: InteriorSpec, lib: M.Library) -> object:
    axis = Vector(column_basis(sp.column_deg).col[2][:3]).normalized()
    c = Vector(sp.wheel_center)
    bm = g.cylinder_bm(0.042, 0.30, axis=tuple(axis), center=tuple(c + axis * 0.19), segments=16)
    stalks = [bm]
    for s in (1, -1):
        st = g.tube_bm([tuple(c + axis * 0.075), tuple(c + axis * 0.075 + Vector((0, s * 0.115, -0.012)))], 0.010,
                       segments=8)
        stalks.append(st)
    return g.to_object("Interior_Column", g.merge_bm(stalks), [lib.black_plastic()], smooth=True, sharp_angle_deg=40.0)


# --------------------------------------------------------------------------- seats
def build_seat(spot: SeatSpot, lib: M.Library, *, detail: str = "full", seam_texture=None,
               headrest: bool = True) -> object:
    """A seat (or bench) built from a cushion, a squab and a headrest, with piped seams at ``detail='full'``."""
    mats = [lib.leather(texture=seam_texture), lib.black_plastic(), lib.dash_trim()]
    w = spot.bench if spot.bench > 0 else spot.width
    depth = 0.50
    parts: list[bmesh.types.BMesh] = []
    # cushion: rounded slab with a bolster on each side
    parts.append(g.rounded_box_bm((depth, w, 0.115), 0.045, segments=3 if detail == "full" else 1,
                                  center=(spot.x + 0.06, spot.y, spot.z + 0.02), material_index=0))
    if detail == "full" and spot.bench <= 0:
        for s in (1, -1):
            parts.append(g.rounded_box_bm((depth * 0.92, w * 0.20, 0.10), 0.040, segments=3,
                                          center=(spot.x + 0.05, spot.y + s * (w * 0.42), spot.z + 0.055),
                                          material_index=0))
    # squab
    back_h = 0.60 if spot.bench <= 0 else 0.52
    ang = math.radians(spot.back_deg)
    bx = spot.x - 0.15
    bz = spot.z + 0.06
    squab = g.rounded_box_bm((0.135, w, back_h), 0.050, segments=3 if detail == "full" else 1,
                             center=(bx, spot.y, bz + back_h / 2), material_index=0)
    g.rotate_bm(squab, "Y", -math.degrees(ang), center=(bx, spot.y, bz))
    parts.append(squab)
    if detail == "full" and spot.bench <= 0:
        for s in (1, -1):
            bol = g.rounded_box_bm((0.145, w * 0.19, back_h * 0.86), 0.045, segments=3,
                                   center=(bx + 0.012, spot.y + s * w * 0.41, bz + back_h * 0.48), material_index=0)
            g.rotate_bm(bol, "Y", -math.degrees(ang), center=(bx, spot.y, bz))
            parts.append(bol)
    if headrest:
        for hy in ([spot.y] if spot.bench <= 0 else [spot.y - w * 0.30, spot.y + w * 0.30]):
            hx = bx - math.sin(ang) * (back_h + 0.10)
            hz = bz + math.cos(ang) * (back_h + 0.10)
            hr = g.rounded_box_bm((0.115, 0.26, 0.16), 0.050, segments=2, center=(hx, hy, hz), material_index=0)
            g.rotate_bm(hr, "Y", -math.degrees(ang), center=(hx, hy, hz))
            parts.append(hr)
            for s in (1, -1):
                parts.append(g.cylinder_bm(0.008, 0.09, axis="Z", center=(hx + 0.02, hy + s * 0.055, hz - 0.12),
                                           segments=8, material_index=2))
    # seams: piping along the cushion and squab centre panels
    if detail == "full":
        for sy in ([-w * 0.18, w * 0.18] if spot.bench <= 0 else [-w * 0.34, -w * 0.11, w * 0.11, w * 0.34]):
            parts.append(g.tube_bm([(spot.x + 0.06 - depth * 0.44, spot.y + sy, spot.z + 0.078),
                                    (spot.x + 0.06 + depth * 0.44, spot.y + sy, spot.z + 0.078)], 0.0035,
                                   segments=6, material_index=2))
            p0 = Vector((bx + 0.068, spot.y + sy, bz + 0.03))
            p1 = p0 + Vector((-math.sin(ang), 0, math.cos(ang))) * (back_h - 0.06)
            parts.append(g.tube_bm([tuple(p0), tuple(p1)], 0.0035, segments=6, material_index=2))
    # seat base / rails
    parts.append(g.box_bm((depth * 0.80, w * 0.86, 0.055), (spot.x + 0.05, spot.y, spot.z - 0.055), material_index=1))
    if spot.bench <= 0:
        for s in (1, -1):
            parts.append(g.box_bm((depth * 0.90, 0.035, 0.030), (spot.x + 0.05, spot.y + s * w * 0.34, spot.z - 0.10),
                                  material_index=2))
    return g.to_object(spot.name, g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=42.0)


# --------------------------------------------------------------------------- console, shifter, pedals
def build_console(sp: InteriorSpec, lib: M.Library) -> object:
    xf = sp.x_dash - 0.05
    xr = sp.seats[0].x - 0.02 if sp.seats else sp.x_rear
    zt = sp.z_floor + 0.29
    mats = [lib.piano_black(), lib.leather(name="LEATHER_CONSOLE"), lib.dash_trim()]
    prof = [(xf, sp.z_floor + 0.02), (xf, zt), (xr - 0.42, zt), (xr - 0.42, zt + 0.055), (xr, zt + 0.055),
            (xr, sp.z_floor + 0.02)]
    body = g.extrude_profile_bm(prof, -0.145, 0.145, material_index=0)
    parts = [body]
    parts.append(g.rounded_box_bm((0.40, 0.30, 0.055), 0.020, segments=2, center=((xr - 0.21), 0, zt + 0.075),
                                  material_index=1))
    for k, cx in enumerate((xf + 0.32, xf + 0.46)):
        parts.append(g.cylinder_bm(0.042, 0.045, axis="Z", center=(cx, 0.0, zt - 0.020), segments=16, material_index=2))
    return g.to_object("Interior_Console", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=40.0)


def build_shifter(sp: InteriorSpec, lib: M.Library) -> object:
    """``Shifter``: rotary dial (Fusion), floor lever, or column stalk. Origin at the shift axis."""
    mats = [lib.dash_trim(), lib.piano_black(), lib.leather(name="LEATHER_SHIFT")]
    x = sp.x_dash - 0.20
    z = sp.z_floor + 0.30
    if sp.shifter == "rotary":
        parts = [g.cylinder_bm(0.052, 0.030, axis="Z", center=(x, 0, z + 0.012), segments=28, material_index=0),
                 g.cylinder_bm(0.058, 0.010, axis="Z", center=(x, 0, z - 0.004), segments=28, material_index=1)]
        for k in range(24):
            a = TAU * k / 24
            parts.append(g.box_bm((0.006, 0.006, 0.030), (x + 0.050 * math.cos(a), 0.050 * math.sin(a), z + 0.012),
                                  material_index=0))
        origin = (x, 0.0, z)
    elif sp.shifter == "lever":
        parts = [g.cylinder_bm(0.017, 0.185, axis="Z", center=(x, 0, z + 0.09), segments=14, material_index=1),
                 g.sphere_bm((0.032, 0.028, 0.040), center=(x, 0, z + 0.20), segments=18, rings=10, material_index=2),
                 g.rounded_box_bm((0.16, 0.09, 0.02), 0.008, center=(x, 0, z), material_index=1)]
        origin = (x, 0.0, z)
    else:                                            # column stalk
        ax = Vector(column_basis(sp.column_deg).col[2][:3]).normalized()
        c = Vector(sp.wheel_center) + ax * 0.10
        parts = [g.tube_bm([tuple(c), tuple(c + Vector((0.02, -0.16, -0.03)))], 0.012, segments=8, material_index=1)]
        origin = tuple(c)
    return g.to_object("Shifter", g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=40.0)


def build_pedals(sp: InteriorSpec, lib: M.Library, *, three: bool = False) -> object:
    """``Pedals``: brake (and clutch) hanging pedals plus an organ-type accelerator."""
    mats = [lib.pedal_rubber(), lib.dash_trim(), lib.black_plastic()]
    y0 = sp.y_driver
    x = sp.x_dash + 0.30
    z = sp.z_floor
    parts = []
    lay = [("accel", y0 - 0.075, 0.055, 0.155), ("brake", y0 + 0.045, 0.095, 0.135)]
    if three:
        lay.append(("clutch", y0 + 0.175, 0.085, 0.135))
    for nm, py, pw, ph in lay:
        pad = g.box_bm((0.016, pw, ph), (x - 0.02, py, z + 0.085), material_index=0)
        g.rotate_bm(pad, "Y", 18.0, center=(x - 0.02, py, z + 0.085))
        parts.append(pad)
        parts.append(g.tube_bm([(x - 0.01, py, z + 0.15), (x + 0.09, py, z + 0.30)], 0.010, segments=8, material_index=1))
    parts.append(g.box_bm((0.10, 0.10, 0.014), (x + 0.14, y0 + 0.20, z + 0.02), material_index=2))   # dead pedal
    return g.to_object("Pedals", g.merge_bm(parts), mats, smooth=False)


# --------------------------------------------------------------------------- trim surfaces
def build_carpet(sp: InteriorSpec, lib: M.Library) -> object:
    x0, x1 = sp.x_rear, sp.x_dash + 0.34
    y = sp.y_cabin * 0.97
    prof = [(x0, sp.z_floor + 0.16), (x0 + 0.10, sp.z_floor), (x1 - 0.28, sp.z_floor),
            (x1, sp.z_floor + 0.22)]
    bm = g.extrude_profile_bm(prof, -y, y, material_index=0, cap=False)
    return g.to_object("Interior_Carpet", bm, [lib.carpet()], smooth=False)


def build_headliner(sp: InteriorSpec, lib: M.Library, *, x_front: float, x_rear: float, y_half: float,
                    z: float, crown: float = 0.03) -> object:
    """Roof lining between the header and the rear header.  ``sp.roof_line`` (if given) supplies the outer roof
    height at each station and the liner hangs 60 mm below it, so it can never poke through the glass."""
    stations = []
    n = 7
    for k in range(9):
        x = g.lerp(x_front, x_rear, k / 8)
        zx = min(z, sp.roof_line(x) - 0.060) if sp.roof_line else z
        ring = []
        for j in range(n):
            t = j / (n - 1)
            yy = -y_half + 2 * y_half * t
            ring.append((x, yy, zx - crown * (1.0 - (2 * t - 1) ** 2)))
        stations.append(ring)
    bm, _ = g.loft(stations)
    g.flip_bm(bm)
    return g.to_object("Interior_Headliner", bm, [lib.fabric()], smooth=True, sharp_angle_deg=60.0)


def build_door_card(name: str, sp: InteriorSpec, lib: M.Library, *, x0: float, x1: float, y: float,
                    detail: str = "full") -> object:
    """Inner door trim: card, armrest, pull cup, speaker grille and (front doors) the switch pod."""
    s = 1 if y > 0 else -1
    mats = [lib.dash_soft(), lib.leather(name="LEATHER_DOORCARD"), lib.dash_trim(), lib.black_plastic()]
    zb, zf = sp.z_belt, sp.z_floor
    card = g.loft([[(x0, y, zf - 0.02), (x0, y - s * 0.030, zf + 0.28), (x0, y - s * 0.055, zb - 0.10), (x0, y - s * 0.020, zb)],
                   [(g.lerp(x0, x1, 0.5), y + s * 0.008, zf - 0.02), (g.lerp(x0, x1, 0.5), y - s * 0.038, zf + 0.28),
                    (g.lerp(x0, x1, 0.5), y - s * 0.068, zb - 0.10), (g.lerp(x0, x1, 0.5), y - s * 0.020, zb)],
                   [(x1, y, zf - 0.02), (x1, y - s * 0.030, zf + 0.28), (x1, y - s * 0.055, zb - 0.10), (x1, y - s * 0.020, zb)]])[0]
    if s < 0:
        g.flip_bm(card)
    parts = [card]
    xm = 0.5 * (x0 + x1)
    parts.append(g.rounded_box_bm((abs(x1 - x0) * 0.52, 0.075, 0.075), 0.022, segments=2,
                                  center=(xm - abs(x1 - x0) * 0.06, y - s * 0.055, zb - 0.155), material_index=1))
    parts.append(g.cylinder_bm(0.075, 0.020, axis="Y", center=(xm + abs(x1 - x0) * 0.24, y - s * 0.030, zf + 0.14),
                               segments=20, material_index=3))
    parts.append(g.rounded_box_bm((0.135, 0.045, 0.030), 0.010, segments=1,
                                  center=(xm - abs(x1 - x0) * 0.22, y - s * 0.075, zb - 0.115), material_index=2))
    if detail == "full":
        for k in range(2):
            parts.append(g.box_bm((0.036, 0.020, 0.010), (xm - abs(x1 - x0) * 0.24 + k * 0.045, y - s * 0.088, zb - 0.10),
                                  material_index=3))
        parts.append(g.rounded_box_bm((0.10, 0.030, 0.022), 0.008, center=(xm + abs(x1 - x0) * 0.30, y - s * 0.045, zb - 0.045),
                                      material_index=2))
    return g.to_object(name, g.merge_bm(parts), mats, smooth=True, sharp_angle_deg=40.0)


def build_belts(sp: InteriorSpec, lib: M.Library, *, x_pillar: float, y_half: float) -> object:
    mats = [lib.seatbelt(), lib.black_plastic()]
    parts = []
    for s in (1, -1):
        y = s * (y_half - 0.03)
        top = Vector((x_pillar, y, sp.z_belt + 0.16))
        bot = Vector((x_pillar - 0.16, y - s * 0.06, sp.z_floor + 0.10))
        parts.append(g.ribbon_bm([tuple(top), tuple(top + (bot - top) * 0.5), tuple(bot)], 0.047,
                                 up=(0, s * 1.0, 0), material_index=0))
        parts.append(g.box_bm((0.030, 0.020, 0.075), (x_pillar, y, sp.z_belt + 0.16), material_index=1))
    for spot in sp.seats:
        parts.append(g.box_bm((0.055, 0.030, 0.115), (spot.x + 0.02, spot.y - 0.24, spot.z + 0.02), material_index=1))
    return g.to_object("Interior_Belts", g.merge_bm(parts), mats, smooth=False)


def build_rear_view_mirror(sp: InteriorSpec, lib: M.Library, *, x: float, z: float) -> object:
    mats = [lib.black_plastic(), lib.mirror_glass()]
    body = g.rounded_box_bm((0.045, 0.265, 0.070), 0.014, segments=2, center=(x, 0, z), material_index=0)
    glass = g.quad_uv01_bm([(x - 0.024, -0.125, z - 0.030), (x - 0.024, 0.125, z - 0.030),
                            (x - 0.024, 0.125, z + 0.030), (x - 0.024, -0.125, z + 0.030)], material_index=1)
    stalk = g.cylinder_bm(0.012, 0.075, axis=(0.4, 0, 1), center=(x + 0.02, 0, z + 0.05), segments=10, material_index=0)
    return g.to_object("Interior_Mirror", g.merge_bm([body, glass, stalk]), mats, smooth=True, sharp_angle_deg=40.0)


def build_visors(sp: InteriorSpec, lib: M.Library, *, x: float, z: float, y_half: float) -> list[object]:
    out = []
    for s, tag in ((1, "L"), (-1, "R")):
        bm = g.rounded_box_bm((0.135, 0.30, 0.014), 0.010, segments=1, center=(x, s * y_half * 0.52, z), material_index=0)
        g.rotate_bm(bm, "Y", -14.0, center=(x, s * y_half * 0.52, z))
        out.append(g.to_object(f"Interior_Visor_{tag}", bm, [lib.fabric(name="FABRIC_VISOR")], smooth=False))
    return out


# --------------------------------------------------------------------------- assembly
def build_interior(sp: InteriorSpec, lib: M.Library, *, seam_texture=None, three_pedals: bool = False,
                   x_bpillar: float | None = None) -> dict[str, object]:
    """Build the whole cabin; returns ``{object_name: object}``."""
    out: dict[str, object] = {}
    out["Interior_Dash"] = build_dash(sp, lib)
    out["SteeringWheel"] = build_steering_wheel(sp, lib)
    out["Interior_Column"] = build_column(sp, lib)
    for spot in sp.seats:
        out[spot.name] = build_seat(spot, lib, detail=sp.detail, seam_texture=seam_texture,
                                    headrest=True)
    out["Shifter"] = build_shifter(sp, lib)
    out["Pedals"] = build_pedals(sp, lib, three=three_pedals)
    if sp.detail == "cab":
        return out
    if sp.console:
        out["Interior_Console"] = build_console(sp, lib)
    out["Interior_Carpet"] = build_carpet(sp, lib)
    x_header = sp.x_roof_front if sp.x_roof_front is not None else sp.x_cowl - 0.08
    if sp.headliner:
        out["Interior_Headliner"] = build_headliner(sp, lib, x_front=x_header, x_rear=sp.x_rear,
                                                    y_half=sp.y_cabin * 0.92, z=sp.z_roof)
    tags = ("FL", "FR", "RL", "RR")
    for k, (x0, x1) in enumerate(sp.doors_x[:2]):
        for s, side in ((1, "L"), (-1, "R")):
            nm = f"Interior_DoorCard_{'F' if k == 0 else 'R'}{side}"
            out[nm] = build_door_card(nm, sp, lib, x0=x1, x1=x0, y=s * sp.y_cabin, detail=sp.detail)
    xb = x_bpillar if x_bpillar is not None else (sp.doors_x[0][1] if sp.doors_x else sp.x_dash - 0.9)
    out["Interior_Belts"] = build_belts(sp, lib, x_pillar=xb, y_half=sp.y_cabin)
    if sp.detail == "full":
        z_header = (sp.roof_line(x_header) - 0.075) if sp.roof_line else (sp.z_roof - 0.055)
        out["Interior_Mirror"] = build_rear_view_mirror(sp, lib, x=x_header + 0.10, z=z_header - 0.02)
        for v in build_visors(sp, lib, x=x_header + 0.08, z=z_header, y_half=sp.y_cabin):
            out[v.name] = v
    return out
