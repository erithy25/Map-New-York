"""Generic fleet-vehicle builder.

Every AI vehicle is described by a :class:`FleetSpec`: published dimensions, a **numeric blueprint table**
(one row per longitudinal station), the feature stations that place the windshield / backlight / door cuts, the
lamp boxes, and an optional ``extras`` callback for whatever is unique to that vehicle (light bar, ladder,
destination signs, refuse body, box body …).  :func:`build` turns a spec into a contract-complete
:class:`vlib.rig.Vehicle`, and :func:`build_and_export` finalises it.

Budget: 120 000 triangles for LOD0 (brief), enforced in :func:`build_and_export`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import blueprint as B, env, geom as g, interior as I, materials as M, parts as P, rig, textures as TX
from .blueprint import Dimensions, R
from .rig import Vehicle

log = env.log
nb = env.nb


@dataclass
class LampBox:
    """Rectangular lamp cluster placement, in metres."""
    x: float
    y: float
    z: float
    w: float
    h: float
    rake: float = 0.0


@dataclass
class FleetSpec:
    id: str
    name: str
    vclass: str
    dims: Dimensions
    table: Sequence[Sequence[float]]
    x_cowl: float
    x_roof_front: float
    x_roof_rear: float
    x_deck: float
    x_bumper_f: float
    x_bumper_r: float
    door_cuts: Sequence[float]
    head: LampBox
    tail: LampBox
    paint: str = "#B7BABD"
    arch_r_f: float = 0.42
    arch_r_r: float = 0.42
    wheel_style: str = "alloy10"
    spokes: int = 10
    dual_rear: bool = False
    x_axle_rear_extra: Sequence[float] = ()      # additional (tag/drive) axles, x in metres
    tyre_text: str = ""
    glass_gap: float = 0.06
    pillar_a: float = 0.10
    n_stations: int = 96
    detail: str = "mid"
    shoulder_t: float = 0.58
    tumble: float = 0.50
    sliding_doors: bool = False
    doors_per_side: int = 2
    x_rear_door: float | None = None
    front_glass: tuple[float, float, float] | None = None
    rear_glass: tuple[float, float, float] | None = None
    side_glass_spans: Sequence[tuple[float, float, int]] = ()
    kerb_side_doors_only: bool = False
    # interior
    interior: str = "mid"                        # mid | cab | none
    #: driver station for ``interior="cab"``: (seat_x, seat_z, wheel_x, wheel_z, y_driver, column_deg)
    cab: tuple[float, float, float, float, float, float] | None = None
    seat_rows: Sequence[tuple[float, float]] = ()   # (x, z) of each row's H-point
    z_floor: float = 0.35
    y_cabin: float | None = None
    z_roof_inner: float | None = None
    shifter: str = "lever"
    column_deg: float = 22.0
    steering_x: float | None = None
    # trim
    mirror_x: float | None = None
    mirror_arm: float = 0.09
    mirror_size: tuple[float, float, float] = (0.185, 0.108, 0.085)
    wiper_len: float = 0.55
    wiper_blade: float = 0.60
    plate_front: bool = True
    exhaust: tuple[float, float, float] | None = None    # (x_tip, y, z)
    grille: tuple[float, float, float, float] | None = None   # (x, z0, z1, y_half)
    handles_x: Sequence[float] = ()
    roof_equipment: Callable[[Vehicle, M.Library, B.Blueprint], None] | None = None
    extras: Callable[[Vehicle, M.Library, B.Blueprint], None] | None = None
    waivers: dict = field(default_factory=dict)
    extra_slots: tuple[str, ...] = ()
    contract_profile: str = "full"
    sources: Sequence[str] = ()
    notes: dict = field(default_factory=dict)
    lod_budgets: tuple[int, int] = (40_000, 6_000)
    tri_budget: int = 120_000
    livery_paint: Callable[[str, Dimensions], tuple] | None = None


# --------------------------------------------------------------------------- table generators
def box_table(d: Dimensions, *, z_under: float, z_rocker: float, z_belt: float, z_top: float,
              y_rocker: float, y_max: float, y_belt: float, y_top: float, crown: float,
              x_cowl: float, nose_len: float = 0.35, tail_len: float = 0.25,
              nose_z_top: float | None = None, nose_z_belt: float | None = None,
              tail_z_top: float | None = None, nose_y: float = 0.55, tail_y: float = 0.72,
              y_top_front: float | None = None, front_lower: float = 0.0,
              skirt: float = 0.0) -> list[tuple]:
    """Blueprint table for a **box body** (van, straight truck, bus): a constant section over the body with a
    short taper at each end.  ``nose_len``/``tail_len`` are the lengths of those tapers, ``nose_y``/``tail_y``
    the fraction of the section width they close down to at the very end face, and ``x_cowl`` the station where
    the windshield meets the roof line.  All other arguments are the constant section itself.
    """
    xr, xf = d.x_rear, d.x_front
    ntz = z_top if nose_z_top is None else nose_z_top
    nbz = z_belt if nose_z_belt is None else nose_z_belt
    ttz = z_top if tail_z_top is None else tail_z_top
    ytf = y_top if y_top_front is None else y_top_front
    zu_f = z_under + front_lower
    def row(x, zu, zr, zb, zt, yr, ym, yb, yt, cr):
        return (x, zu, zr, zb, zt, yr, ym, yb, yt, cr)
    rows = [
        row(xr, z_under + 0.10, z_rocker + 0.12, z_belt, ttz, y_rocker * tail_y, y_max * tail_y,
            y_belt * tail_y, y_top * tail_y, crown),
        row(xr + tail_len, z_under, z_rocker, z_belt, z_top, y_rocker, y_max, y_belt, y_top, crown),
        row(xr + tail_len + 0.35, z_under, z_rocker - skirt, z_belt, z_top, y_rocker, y_max, y_belt, y_top, crown),
        row(0.0, z_under, z_rocker - skirt, z_belt, z_top, y_rocker, y_max, y_belt, y_top, crown),
        row((d.x_axle_front) * 0.5, z_under, z_rocker - skirt, z_belt, z_top, y_rocker, y_max, y_belt, y_top, crown),
        row(d.x_axle_front, z_under, z_rocker, z_belt, z_top, y_rocker, y_max, y_belt, y_top, crown),
        row(x_cowl, zu_f, z_rocker, z_belt, z_top, y_rocker, y_max, y_belt, ytf, crown),
        row(xf - nose_len, zu_f, z_rocker, nbz, ntz, y_rocker * 0.99, y_max * 0.99, y_belt * 0.99, ytf * 0.99, crown),
        row(xf, zu_f + 0.08, z_rocker + 0.06, nbz, ntz - 0.02, y_rocker * nose_y, y_max * nose_y,
            y_belt * nose_y, ytf * nose_y, crown),
    ]
    rows = [r for i, r in enumerate(rows) if i == 0 or r[0] > rows[i - 1][0] + 1e-4]
    return rows


def car_table(d: Dimensions, *, z_under: float, z_rocker: float, z_belt: float, z_roof: float,
              y_rocker: float, y_max: float, y_belt: float, y_roof: float,
              x_cowl: float, x_roof_front: float, x_roof_rear: float, x_deck: float,
              z_hood_front: float, z_nose: float, z_tail: float, z_deck: float,
              y_top_cowl: float, y_top_deck: float, crown_roof: float = 0.030,
              crown_glass: float = 0.070, crown_hood: float = 0.040,
              y_nose: float = 0.62, y_tail: float = 0.68, z_cowl: float | None = None) -> list[tuple]:
    """Blueprint table for a **three-box or two-box car** (sedan, SUV, wagon).  The rows are placed at the
    feature stations so the interpolated body lines pass exactly through them."""
    xr, xf = d.x_rear, d.x_front
    zc = z_cowl if z_cowl is not None else z_belt + 0.15
    hw = d.half_width
    rows = [
        (xr, z_under + 0.30, z_rocker + 0.26, z_belt - 0.01, z_tail, y_rocker * y_tail, y_max * y_tail,
         y_belt * y_tail, y_top_deck * 0.78, 0.016),
        (xr + 0.30, z_under + 0.16, z_rocker + 0.10, z_belt, z_tail + (z_deck - z_tail) * 0.55,
         y_rocker * 0.94, y_max * 0.955, y_belt * 0.95, y_top_deck * 0.95, 0.020),
        (x_deck, z_under, z_rocker, z_belt, z_deck, y_rocker, y_max * 0.99, y_belt * 0.99, y_top_deck, 0.045),
        (x_roof_rear, z_under, z_rocker, z_belt, z_roof, y_rocker, y_max, y_belt, y_roof, crown_glass * 0.8),
        (0.5 * (x_roof_front + x_roof_rear), z_under, z_rocker, z_belt, z_roof, y_rocker, y_max, y_belt,
         y_roof * 1.01, crown_roof),
        (x_roof_front, z_under, z_rocker, z_belt, z_roof - 0.008, y_rocker, y_max, y_belt, y_roof, crown_roof * 1.3),
        (x_cowl, z_under + 0.005, z_rocker + 0.02, z_belt, zc, y_rocker * 0.99, y_max * 0.995, y_belt * 0.99,
         y_top_cowl, crown_glass),
        (xf - 0.62, z_under + 0.02, z_rocker + 0.09, z_belt - 0.02, z_hood_front, y_rocker * 0.95, y_max * 0.97,
         y_belt * 0.95, y_top_cowl * 0.97, crown_hood),
        (xf - 0.20, z_under + 0.06, z_rocker + 0.18, z_belt - 0.06, z_nose + 0.05, y_rocker * 0.86,
         y_max * 0.90, y_belt * 0.86, y_top_cowl * 0.85, crown_hood),
        (xf, z_under + 0.28, z_rocker + 0.26, z_belt - 0.10, z_nose, y_rocker * y_nose, y_max * y_nose,
         y_belt * y_nose, y_top_cowl * y_nose, crown_hood + 0.01),
    ]
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: r[0]):
        if r[0] in seen:
            continue
        seen.add(r[0])
        out.append(tuple(float(c) for c in r))
    if max(r[6] for r in out) > hw:
        raise ValueError("car_table: y_max column exceeds half the published width")
    return out


SPLIT_FULL = {
    "Undertray": [int(R.UNDERBODY)],
    "Hood": [int(R.HOOD)],
    "Trunk": [int(R.TRUNK)],
    "Door_FL": [int(R.DOOR_FL)], "Door_FR": [int(R.DOOR_FR)],
    "Door_RL": [int(R.DOOR_RL)], "Door_RR": [int(R.DOOR_RR)],
    "Door_SL": [int(R.DOOR_SL)], "Door_SR": [int(R.DOOR_SR)],
    "Window_WS": [int(R.GLASS_WS)], "Window_BACK": [int(R.GLASS_BACK)],
    "Window_FL": [int(R.GLASS_FL)], "Window_FR": [int(R.GLASS_FR)],
    "Window_RL": [int(R.GLASS_RL)], "Window_RR": [int(R.GLASS_RR)],
}


def region_materials(lib: M.Library, paint, *, tinted_rear: bool = False, black_pillars: bool = True) -> list:
    glass = lib.glass()
    rear_glass = lib.glass_tinted() if tinted_rear else glass
    mats = [None] * int(R.N)
    for r in (R.BODY, R.ROOF, R.TRUNK, R.HOOD, R.SILL, R.BUMPER_F, R.BUMPER_R, R.QUARTER,
              R.DOOR_FL, R.DOOR_FR, R.DOOR_RL, R.DOOR_RR, R.DOOR_SL, R.DOOR_SR):
        mats[int(r)] = paint
    mats[int(R.UNDERBODY)] = lib.underside()
    mats[int(R.WELL)] = lib.black_plastic()
    mats[int(R.PILLAR)] = lib.gloss_black() if black_pillars else paint
    for r in (R.GLASS_WS, R.GLASS_FL, R.GLASS_FR):
        mats[int(r)] = glass
    for r in (R.GLASS_BACK, R.GLASS_RL, R.GLASS_RR, R.GLASS_QL, R.GLASS_QR):
        mats[int(r)] = rear_glass
    return mats


def make_blueprint(sp: FleetSpec) -> B.Blueprint:
    return B.from_table(
        sp.id, sp.dims, sp.table,
        x_cowl=sp.x_cowl, x_roof_front=sp.x_roof_front, x_roof_rear=sp.x_roof_rear, x_deck=sp.x_deck,
        x_hood_rear=sp.x_cowl, x_bumper_f=sp.x_bumper_f, x_bumper_r=sp.x_bumper_r,
        x_door_cuts=tuple(sp.door_cuts), arch_radius_f=sp.arch_r_f, arch_radius_r=sp.arch_r_r,
        glass_gap=sp.glass_gap, pillar_a=sp.pillar_a, n_stations=sp.n_stations,
        shoulder_t=B.const(sp.shoulder_t), tumble=B.const(sp.tumble), notes=dict(sp.notes),
        sliding_doors=sp.sliding_doors, doors_per_side=sp.doors_per_side, x_rear_door=sp.x_rear_door,
        front_glass=sp.front_glass, rear_glass=sp.rear_glass, side_glass_spans=tuple(sp.side_glass_spans),
    )


# --------------------------------------------------------------------------- extra axles
def extra_axle_wheels(v: Vehicle, sp: FleetSpec, lib: M.Library, sidewall) -> None:
    """Tag/drive axles beyond the contract four (buses, three-axle trucks, articulated buses)."""
    for k, ax in enumerate(sp.x_axle_rear_extra):
        for s, tag in ((1, "L"), (-1, "R")):
            ob = P.wheel(f"Wheel_X{k}{tag}", sp.dims, lib, style=sp.wheel_style, spokes=sp.spokes,
                         sidewall_texture=sidewall, disc=False, dual=sp.dual_rear)
            if s < 0:
                ob.data.transform(Matrix.Rotation(math.pi, 4, "Z"))
                ob.data.update()
            ob.location = (ax, s * sp.dims.y_track_rear, sp.dims.wheel_radius)
            v.add(ob)


# --------------------------------------------------------------------------- the builder
def build(sp: FleetSpec, lib: M.Library | None = None, *, reset: bool = True) -> tuple[Vehicle, dict]:
    lib = lib or M.Library()
    if reset:
        nb.reset_scene()
        lib = M.Library()
    t = env.Timer()
    bp = make_blueprint(sp)
    d = sp.dims
    sidewall = TX.tyre_sidewall(f"tyre_{sp.id}", size_text=sp.tyre_text or f"{int(d.tyre_width_mm)}/70R{int(d.rim_diameter_in)}")
    paint_mat = lib.paint(M.srgb_hex(sp.paint)[:3], f"BODY_PAINT_{sp.id}", metallic=0.22, roughness=0.32)
    shell = B.build_shell(bp, detail=sp.detail, materials=region_materials(lib, paint_mat,
                                                                          tinted_rear=sp.vclass in ("van", "suv", "truck")))
    body = shell.object
    split = {k: vv for k, vv in SPLIT_FULL.items()}
    parts = g.separate_by_material(body, split)
    body.name = "Body"

    z_belt_mid = bp.z_belt(0.5 * (sp.door_cuts[0] + sp.door_cuts[-1])) if sp.door_cuts else d.height * 0.6
    v = Vehicle(id=sp.id, display_name=sp.name, vclass=sp.vclass, dims=d, z_belt=z_belt_mid,
                contract_profile=sp.contract_profile, contract_waivers=dict(sp.waivers),
                sources=list(sp.sources), notes=dict(sp.notes), extra_slots=sp.extra_slots)
    if sp.kerb_side_doors_only:
        # NYC transit buses have passenger doors on the kerb (right) side only; the mirrored left-hand leaves
        # are welded back into the body rather than shipped as doors that do not exist on the real vehicle.
        merge = [body] + [parts.pop(n) for n in ("Door_FL", "Door_RL") if n in parts]
        body = g.join(merge, "Body", sharp_angle_deg=34.0)
    v.add(body)
    v.add_all(parts)
    t.mark("shell")

    # ---- panel gaps / pivots
    for nm in ("Door_FL", "Door_FR", "Door_RL", "Door_RR", "Door_SL", "Door_SR", "Hood", "Trunk"):
        if nm in parts:
            g.inset_gap(parts[nm], 0.005)
    cuts = list(sp.door_cuts)
    for nm, k, sgn in (("Door_FL", 0, 1), ("Door_FR", 0, -1), ("Door_RL", 1, 1), ("Door_RR", 1, -1)):
        if nm in parts and k < len(cuts):
            hx = cuts[k]
            rig.hinge_door(parts[nm], hx, sgn * bp.y_max(hx) * 0.92, z_belt_mid * 0.6)
    for nm, k, sgn in (("Door_SL", 1, 1), ("Door_SR", 1, -1)):
        if nm in parts and k < len(cuts):
            hx = cuts[min(k, len(cuts) - 1)]
            rig.hinge_door(parts[nm], hx, sgn * bp.y_max(hx) * 0.92, z_belt_mid * 0.6)
    if "Hood" in parts:
        rig.hinge_panel(parts["Hood"], sp.x_cowl - 0.02, bp.z_top(sp.x_cowl) - 0.03)
    if "Trunk" in parts:
        if sp.x_rear_door is not None:      # barn / lift-gate door on the rear face: hinge on the left pillar
            rig.hinge_door(parts["Trunk"], sp.x_rear_door, bp.y_max(sp.x_rear_door) * 0.90, z_belt_mid * 0.8)
        else:
            rig.hinge_panel(parts["Trunk"], sp.x_deck - 0.02, bp.z_top(sp.x_deck) - 0.03)
    for nm in list(parts):
        if nm.startswith("Window_"):
            _recess(parts[nm], 0.008)

    # ---- wheels
    wheels = P.place_wheels(d, lib, style=sp.wheel_style, spokes=sp.spokes, sidewall_texture=sidewall,
                            disc=sp.wheel_style not in ("steel", "truck"), dual_rear=sp.dual_rear)
    v.add_all(wheels)
    extra_axle_wheels(v, sp, lib, sidewall)
    for tag, hx, rr in (("F", d.x_axle_front, sp.arch_r_f), ("R", 0.0, sp.arch_r_r)):
        for s, sd in ((1, "L"), (-1, "R")):
            v.add(P.wheel_well(f"WheelWell_{tag}{sd}", bp, hx, y_out=bp.y_max(hx) - 0.01,
                               y_in=max(0.30, bp.y_max(hx) - 0.36), lib=lib, side=s))
    t.mark("wheels")

    # ---- lamps
    head = {}
    for s in (1, -1):
        head.update(P.headlamp_unit("head", s, lib, x=sp.head.x, y=s * sp.head.y, z=sp.head.z,
                                    w=sp.head.w, h=sp.head.h, rake=sp.head.rake,
                                    projector_r=min(0.05, sp.head.h * 0.28)))
    v.add(head["LIGHT_HEAD_L"]); v.add(head["LIGHT_HEAD_R"])
    v.add(head["LIGHT_TURN_FL"]); v.add(head["LIGHT_TURN_FR"])
    v.add(g.join([head["_low_L"], head["_low_R"]], "LIGHT_LOW", sharp_angle_deg=50.0))
    v.add(g.join([head["_high_L"], head["_high_R"]], "LIGHT_HIGH", sharp_angle_deg=50.0))
    v.add(g.join([head["_drl_L"], head["_drl_R"]], "LIGHT_DRL", sharp_angle_deg=50.0))
    tail = {}
    for s in (1, -1):
        tail.update(P.taillamp_unit(s, lib, x=sp.tail.x, y=s * sp.tail.y, z=sp.tail.z, w=sp.tail.w, h=sp.tail.h))
    for k in ("LIGHT_TAIL_L", "LIGHT_TAIL_R", "LIGHT_BRAKE_L", "LIGHT_BRAKE_R", "LIGHT_TURN_RL", "LIGHT_TURN_RR"):
        v.add(tail[k])
    tail["_rev_L"].name = "LIGHT_REVERSE_L"
    tail["_rev_R"].name = "LIGHT_REVERSE_R"
    v.add(tail["_rev_L"]); v.add(tail["_rev_R"])
    v.add(P.plate_light(lib, d.x_rear + 0.012, sp.tail.z - sp.tail.h * 0.75, 0.0, 0.12))
    t.mark("lamps")

    # ---- trim
    mx = sp.mirror_x if sp.mirror_x is not None else sp.door_cuts[0] - 0.10
    mw, mh, md = sp.mirror_size
    for s in (1, -1):
        v.add(P.mirror(s, lib, x=mx, y=s * (bp.y_belt(mx) - 0.005), z=bp.z_belt(mx) + 0.06,
                       w=mw, h=mh, d=md, arm=sp.mirror_arm))
    z_ws = bp.z_top(sp.x_cowl - 0.05) - 0.012
    dx = max(0.12, sp.x_cowl - sp.x_roof_front)
    slope = max(0.05, (bp.z_top(sp.x_roof_front) - bp.z_top(sp.x_cowl)) / dx)
    v.add(P.wiper(1, lib, pivot=(sp.x_cowl - 0.05, 0.30, z_ws), length=sp.wiper_len, blade=sp.wiper_blade,
                  park_deg=6.0, glass_slope=slope))
    v.add(P.wiper(-1, lib, pivot=(sp.x_cowl - 0.05, -0.38, z_ws), length=sp.wiper_len * 0.88,
                  blade=sp.wiper_blade * 0.88, park_deg=-6.0, glass_slope=slope))
    if sp.exhaust:
        v.add(P.exhaust(lib, x_tip=sp.exhaust[0], y=sp.exhaust[1], z=sp.exhaust[2], r=0.036, length=0.8, tips=1))
    if sp.grille:
        gx, gz0, gz1, gyh = sp.grille
        v.add(g.to_object("Grille", P.grille(lib, x=gx, z0=gz0, z1=gz1, y_half=gyh, bars=5, rake=0.08),
                          [lib.gloss_black()], smooth=True, sharp_angle_deg=40.0))
    if sp.handles_x:
        hs = []
        for hx in sp.handles_x:
            for s in (1, -1):
                hs.append(P.door_handle(lib, hx, s * bp.y_belt(hx), bp.z_belt(hx) - 0.115))
        v.add(g.to_object("Handles", g.merge_bm(hs), [lib.satin_alu()], smooth=True, sharp_angle_deg=40.0))

    plate_img = TX.plate_ny(f"plate_{sp.id}", _plate_number(sp.id), style="passenger")
    if sp.plate_front:
        v.add(P.plate("Plate_F", lib, plate_img, center=(d.x_front - 0.02, 0.0, min(0.75, sp.head.z - 0.22)),
                      normal=(1, 0, 0.08)))
    else:
        v.add(P.plate("Plate_F", lib, plate_img, center=(d.x_front - 0.02, 0.30, min(0.75, sp.head.z - 0.22)),
                      normal=(1, 0, 0.08)))
    v.add(P.plate("Plate_R", lib, plate_img, center=(d.x_rear + 0.020, 0.0, max(0.45, sp.tail.z - sp.tail.h * 1.4)),
                  normal=(-1, 0, -0.05)))
    t.mark("trim")

    # ---- interior
    if sp.interior == "cab":
        sx_, sz_, wx_, wz_, ydrv_, col_ = sp.cab
        isp = I.InteriorSpec(
            x_dash=wx_ + 0.22, x_cowl=sp.x_cowl, x_rear=sx_ - 0.60, z_floor=sp.z_floor,
            z_roof=bp.z_top(sp.x_cowl) - 0.10,
            # the cab dash spans the cabin, never wider than the body at the cowl
            y_cabin=min(bp.y_belt(sp.x_cowl) - 0.06, max(0.60, ydrv_ * 1.9)),
            z_belt=sz_ + 0.30, detail="cab", shifter=sp.shifter, column_deg=col_,
            seats=[I.SeatSpot(x=sx_, y=ydrv_, z=sz_, name="Seat_FL", width=0.52)],
            wheel_center=(wx_, ydrv_, wz_), wheel_radius=0.235,
            gauge_images=(TX.gauge_speedo("gauge_speedo_80mph", max_mph=80),
                          TX.gauge_tach("gauge_tach_3000rpm", max_rpm=3000, redline_rpm=2400),
                          TX.screen_home("screen_center_8in")),
        )
        v.add_all(I.build_interior(isp, lib))
    elif sp.interior != "none":
        y_cab = sp.y_cabin if sp.y_cabin is not None else bp.y_belt(sp.door_cuts[0] - 0.4) - 0.09
        z_roof_in = sp.z_roof_inner if sp.z_roof_inner is not None else bp.z_top(sp.x_roof_front - 0.3) - 0.075
        sx = sp.steering_x if sp.steering_x is not None else sp.x_cowl - 0.44
        rows = list(sp.seat_rows) or [(sp.door_cuts[0] - 0.55, sp.z_floor + 0.20)]
        seats = []
        for k, (rx, rz) in enumerate(rows):
            if k == 0:
                seats.append(I.SeatSpot(x=rx, y=y_cab * 0.48, z=rz, name="Seat_FL", width=0.52))
                seats.append(I.SeatSpot(x=rx, y=-y_cab * 0.48, z=rz, name="Seat_FR", width=0.52))
            else:
                seats.append(I.SeatSpot(x=rx, y=0.0, z=rz, name=f"Seat_R{k}", bench=y_cab * 1.72, back_deg=26.0))
        isp = I.InteriorSpec(
            x_dash=sx - 0.14, x_cowl=sp.x_cowl, x_rear=rows[-1][0] - 0.55, z_floor=sp.z_floor,
            z_roof=z_roof_in, y_cabin=y_cab, z_belt=bp.z_belt(sx) - 0.02, seats=seats,
            wheel_center=(sx, y_cab * 0.48, sp.z_floor + 0.52), wheel_radius=0.19,
            column_deg=sp.column_deg, detail="mid", console=sp.interior != "bench",
            x_roof_front=sp.x_roof_front, roof_line=bp.z_top,
            shifter=sp.shifter, doors_x=(tuple(cuts[0:2]), tuple(cuts[1:3])) if len(cuts) >= 3 else (tuple(cuts[0:2]),),
            gauge_images=(TX.gauge_speedo("gauge_speedo_120mph", max_mph=120),
                          TX.gauge_tach("gauge_tach_6000rpm", max_rpm=6000, redline_rpm=5000),
                          TX.screen_home("screen_center_8in")),
        )
        v.add_all(I.build_interior(isp, lib, x_bpillar=cuts[1] if len(cuts) > 1 else cuts[0] - 0.9))
    t.mark("interior")

    if sp.roof_equipment:
        sp.roof_equipment(v, lib, bp)
    if sp.extras:
        sp.extras(v, lib, bp)
    t.mark("extras")

    for nm in ("Body", "Hood", "Trunk", "Door_FL", "Door_FR", "Door_RL", "Door_RR", "Door_SL", "Door_SR"):
        if nm in v.objects:
            rig.add_damage_regions(v.objects[nm], d, z_belt=z_belt_mid)
    hull_src = [o for n, o in v.objects.items()
                if o.type == "MESH" and not n.startswith(("UCX_", "Wheel_", "Interior_", "Seat_", "Mirror_",
                                                          "Pedals", "Shifter", "SteeringWheel"))]
    v.add_all(rig.ucx_proxies("Body", hull_src, d, z_belt=z_belt_mid,
                              slices=max(4, int(round(d.length / 1.4))), cabin=True))
    t.mark("dmg+ucx")
    log.info("%s built: %s", sp.id, t.marks)
    return v, {"lib": lib, "bp": bp, "timings": dict(t.marks), "paint": paint_mat}


def _recess(ob, depth: float) -> None:
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


def _plate_number(vid: str) -> str:
    h = abs(hash(vid)) % 100000
    letters = "ABCDEFGHJKLMNPRSTUVWXYZ"
    return f"{letters[h % 23]}{letters[(h // 23) % 23]}{letters[(h // 529) % 23]} {h % 10000:04d}"


EXTERIOR_PREFIXES = ("Body", "Hood", "Trunk", "Door_", "Window_", "Wheel", "LIGHT_", "Mirror_", "Wiper_",
                     "Grille", "Handles", "Badges", "Plate_", "Undertray", "Exhaust", "Bumper", "Sign", "SIGN_",
                     "LightBar", "TAXI_ROOF", "Box", "Ladder", "Rack", "Step", "Tank", "Deck", "Frame", "Roof",
                     "Rail", "Fender", "Basket", "Canopy", "Horse", "Shaft", "Wheelchair", "Antenna", "Skirt",
                     "Pump", "Hose", "Bin", "Hopper", "Blade", "Cab", "Trailer", "Bell", "Cargo", "Bag", "Seatpost")


def build_and_export(sp: FleetSpec) -> dict:
    v, ctx = build(sp)
    body_objs = [o for o in v.objects.values() if o.type == "MESH" and not o.name.startswith("UCX_")]
    tris = g.tri_count_all(body_objs)
    if tris > sp.tri_budget:
        raise RuntimeError(f"{sp.id}: LOD0 {tris} tris over the {sp.tri_budget} budget")
    ext = [o.name for o in body_objs if o.name.startswith(EXTERIOR_PREFIXES)]
    return rig.finalise(v, lod_budgets=sp.lod_budgets, exterior_names=ext,
                        extra_catalog={"blueprint_table": [list(map(float, r)) for r in sp.table],
                                       "blueprint_table_columns": list(B.TABLE_COLUMNS),
                                       "feature_x": {"cowl": sp.x_cowl, "roof_front": sp.x_roof_front,
                                                     "roof_rear": sp.x_roof_rear, "deck": sp.x_deck,
                                                     "door_cuts": list(sp.door_cuts)},
                                       "door_kind": {"Door_RL": "sliding" if sp.sliding_doors else "hinged",
                                                     "Door_RR": "sliding" if sp.sliding_doors else "hinged",
                                                     "Trunk": "rear cargo door" if sp.x_rear_door is not None
                                                     else "boot lid / tailgate"},
                                       "build_timings_s": ctx["timings"]})
