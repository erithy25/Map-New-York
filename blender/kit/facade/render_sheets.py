#!/usr/bin/env python3
"""Cycles verification renders for the facade kit.

    python3 blender/kit/facade/render_sheets.py --sheet windows      # one contact sheet
    python3 blender/kit/facade/render_sheets.py --list               # sheet names
    python3 blender/kit/facade/render_sheets.py --tenement           # the assembled 5-floor test building

Contact sheets lay every registered piece of a group out on a grid in front of a brick backdrop, label each with its
id and triangle count, and render one near-orthographic Cycles CPU still to
``docs/verification/kit/facade_sheet_<group>.png``. One sheet per process (one heavy job at a time).
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import bpy                     # noqa: E402
from mathutils import Vector   # noqa: E402

import kitlib as K             # noqa: E402
import pieces_common as P      # noqa: E402
import build_kit               # noqa: E402

log = logging.getLogger("nycsim.kit.facade.render")
OUT = K.nb.REPO_ROOT / "docs" / "verification" / "kit"
FONT_PATH = K.nb.ASSETS / "fonts" / "Overpass" / "overpass-semibold.otf"

SHEETS: dict[str, tuple[str, ...]] = {
    "windows": ("window",),
    "accessories": ("window_accessory",),
    "entries": ("door_entry",),
    "trim": ("cornice", "string_course", "quoin", "pilaster", "trim"),
    "storefront": ("storefront",),
    "interiors": ("storefront_interior",),
    "roof": ("fire_escape", "parapet", "bulkhead", "water_tower"),
    "rooftop_equipment": ("hvac", "antenna", "billboard"),
    "street": ("scaffold", "fence", "vegetation"),
}


# --------------------------------------------------------------------------- scene helpers
def _clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def _label(text: str, loc, size: float, mat_name: str = "paint_black") -> bpy.types.Object:
    cu = bpy.data.curves.new(f"lbl_{text}", type="FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "TOP"
    cu.extrude = 0.0
    if FONT_PATH.exists():
        cu.font = bpy.data.fonts.load(str(FONT_PATH), check_existing=True)
    ob = bpy.data.objects.new(f"lbl_{text}", cu)
    K.nb.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    ob.data.materials.append(K.material(mat_name))
    return ob


def _backdrop(x0: float, x1: float, z0: float, z1: float, y: float, mat: str = "precast") -> None:
    """Neutral wall *behind* every piece. It must not sit on the wall plane (y = 0): the kit's wall pieces put their
    sashes, reveals and interior cards at positive y, i.e. inside the masonry, and a backdrop at y = 0 would hide
    exactly the parts the sheet is meant to show."""
    m = K.Mesh()
    m.face([(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)], mat,
           uvs=[(x0, z0), (x0, z1), (x1, z1), (x1, z0)])
    m.to_object("backdrop")


def _ground(x0: float, x1: float, y0: float, y1: float, mat: str = "concrete_sidewalk") -> None:
    m = K.Mesh()
    m.face([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)], mat)
    m.to_object("ground")


def _render(path: Path, *, centre, half_w: float, half_h: float, samples: int, res_x: int,
            sun_az: float = 205.0, sun_el: float = 42.0) -> None:
    """Near-orthographic Cycles still: the camera is pulled back 240 m with a matching narrow FOV."""
    dist = 240.0
    fov = 2.0 * math.degrees(math.atan(half_w / dist))
    res_y = max(360, int(res_x * half_h / half_w))
    K.nb.quick_render(path, camera_location=(centre[0], centre[1] - dist, centre[2]), camera_target=centre,
                      fov_deg=fov, size=(res_x, res_y), samples=samples, sun_azimuth_deg=sun_az,
                      sun_elevation_deg=sun_el, sun_strength=3.2)


# --------------------------------------------------------------------------- contact sheets
def sheet(group: str, *, samples: int, res_x: int, only: set[str] | None = None) -> Path:
    """Greedy row-packed elevation of every piece in the group; free-standing pieces are turned 28 deg so their
    depth reads, wall pieces face the camera square-on."""
    cats = SHEETS[group]
    ids = [pid for pid in sorted(K.REGISTRY) if K.REGISTRY[pid].category in cats]
    if only:
        ids = [pid for pid in ids if pid in only]
    if not ids:
        raise SystemExit(f"no pieces for sheet {group}")
    built = []
    for pid in ids:
        piece = K.REGISTRY[pid]
        m = piece.build()
        tris = m.triangles()
        if piece.anchor.startswith("ground"):
            turned = K.Mesh()
            turned.merge(m, rot_z_deg=28.0)
            m.free()
            m = turned
        lo, hi = m.bounds()
        ob = m.to_object(pid)
        m.free()
        built.append([piece, ob, lo, hi, tris])

    gap_x, gap_z, label_band = 0.55, 0.55, 0.62
    target_w = max(9.0, math.sqrt(sum((hi.x - lo.x + gap_x) * (hi.z - lo.z + gap_z + label_band)
                                      for _, _, lo, hi, _ in built) * 1.55))
    rows, cur, cur_w = [], [], 0.0
    for item in built:
        w = item[3].x - item[2].x + gap_x
        if cur and cur_w + w > target_w:
            rows.append(cur)
            cur, cur_w = [], 0.0
        cur.append(item)
        cur_w += w
    if cur:
        rows.append(cur)
    row_h = [max(it[3].z - it[2].z for it in r) + gap_z + label_band for r in rows]
    total_h = sum(row_h)
    total_w = max(sum(it[3].x - it[2].x + gap_x for it in r) for r in rows)

    z_top = total_h
    for r, row in enumerate(rows):
        z_top -= row_h[r]
        x = -total_w / 2 + (total_w - sum(it[3].x - it[2].x + gap_x for it in row)) / 2
        for piece, ob, lo, hi, tris in row:
            w = hi.x - lo.x
            cx = x + gap_x / 2 + w / 2
            ob.location = Vector((cx - (lo.x + hi.x) / 2, 0.0, z_top + label_band - lo.z))
            _label(f"{piece.id}\n{tris} tris   {w:.2f} x {hi.y - lo.y:.2f} x {hi.z - lo.z:.2f} m",
                   (cx, -2.2, z_top + label_band - 0.10), 0.185)
            x += w + gap_x
    back_y = max(0.8, max(it[3].y for it in built) + 0.7)
    front_y = min(-2.6, min(it[2].y for it in built) - 0.8)
    _backdrop(-total_w / 2 - 0.5, total_w / 2 + 0.5, -0.3, total_h + 0.7, back_y)
    _ground(-total_w / 2 - 0.5, total_w / 2 + 0.5, front_y, back_y)
    path = OUT / f"facade_sheet_{group}.png"
    _render(path, centre=(0.0, 0.0, total_h / 2 + 0.2), half_w=total_w / 2 + 0.7,
            half_h=total_h / 2 + 0.7, samples=samples, res_x=res_x)
    return path


# --------------------------------------------------------------------------- assembled tenement
def _place(pid: str, loc, *, mesh_cache: dict = {}) -> bpy.types.Object:
    """Instance a kit piece at ``loc`` (linked duplicate after the first use)."""
    if pid not in mesh_cache:
        m = K.REGISTRY[pid].build()
        ob = m.to_object(pid)
        m.free()
        mesh_cache[pid] = ob.data
        ob.location = Vector(loc)
        return ob
    ob = bpy.data.objects.new(pid, mesh_cache[pid])
    K.nb.link(ob)
    ob.location = Vector(loc)
    return ob


def tenement(*, samples: int, res_x: int) -> Path:
    """A 25 ft (7.62 m) wide, five-storey, 18 m New Law tenement assembled entirely from kit pieces."""
    W = 7.620
    GROUND = 4.200
    FLOOR = 3.200
    ROOF = GROUND + 4 * FLOOR                      # 17.00 m to the roof deck
    WALL_T = 0.400
    win_x = (-2.44, 0.0, 2.44)                     # three window bays
    win_w, win_h = 1.06, 1.994                     # the soldier-lintel window piece
    sill_from_floor = 0.95

    m = K.Mesh()
    openings: list[tuple[float, float, float, float]] = []
    for f in range(4):                             # storeys 2-5
        z0 = GROUND + f * FLOOR + sill_from_floor
        for x in win_x:
            openings.append((x - win_w / 2, x + win_w / 2, z0, z0 + win_h))
    # ground floor: storefront bay (left) and entrance (right)
    bay_w, bay_cx = 3.66, -W / 2 + 0.22 + 3.66 / 2
    openings.append((bay_cx - bay_w / 2, bay_cx + bay_w / 2, 0.0, GROUND))
    openings.append((1.52, 1.52 + 1.52, 0.0, 2.90))

    # brick front wall built as spandrels and piers around the openings
    xs = sorted({-W / 2, W / 2} | {v for o in openings for v in o[:2]})
    zs = sorted({0.0, ROOF} | {v for o in openings for v in o[2:]})
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
            cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
            if any(a < cx < b and c < cz < d for a, b, c, d in openings):
                continue
            m.box((x0, 0.0, z0), (x1, WALL_T, z1), "red_brick", faces="yY")
    for a, b, c, d in openings:                    # reveals round every hole
        m.box((a, 0.0, c), (b, WALL_T, d), "red_brick", faces="xXzZ")
    m.box((-W / 2, 0.0, 0.0), (-W / 2 + 0.001, WALL_T, ROOF), "red_brick", faces="x")
    m.box((W / 2 - 0.001, 0.0, 0.0), (W / 2, WALL_T, ROOF), "red_brick", faces="X")
    m.box((-W / 2, 0.0, ROOF), (W / 2, WALL_T, ROOF + 0.02), "red_brick", faces="Z")
    m.box((-W / 2, WALL_T, 0.0), (W / 2, WALL_T + 9.0, ROOF), "red_brick", faces="xXZ")   # party walls / roof deck
    m.to_object("tenement_wall")

    _ground(-14.0, 14.0, -12.0, 0.0)
    kerb = K.Mesh()
    kerb.box((-14.0, -9.2, -0.16), (14.0, -9.0, 0.0), "granite")
    kerb.face([(-14.0, -12.0, -0.16), (14.0, -12.0, -0.16), (14.0, -9.2, -0.16), (-14.0, -9.2, -0.16)], "asphalt")
    kerb.to_object("kerb")

    # --- windows, storefront, entrance, fire escape, cornice, roof
    for f in range(4):
        z = GROUND + f * FLOOR + sill_from_floor
        for x in win_x:
            _place("win_double_hung_1_1_soldier", (x, 0.0, z))
        _place("acc_ac_window_small", (win_x[0], 0.0, z))
        if f in (0, 2):
            _place("acc_window_guard_child", (win_x[2], 0.0, z))
        if f == 1:
            _place("acc_flower_box", (win_x[2], 0.0, z))
    _place("storefront_bay_36", (bay_cx, 0.0, 0.0))
    _place("storefront_interior_bodega", (bay_cx, 0.25, 0.0))
    _place("storefront_awning_36", (bay_cx, 0.0, 0.0))
    _place("storefront_gate_36_open", (bay_cx, 0.0, 0.0))
    _place("entry_stoop_tenement_4", (2.28, 0.0, 0.0))
    for k in range(8):                                       # stone belt course at the storefront lintel line
        _place("string_course_stone_belt", (-W / 2 + 0.5 + k, 0.0, GROUND - 0.30))
    # fire escape on the centre bay: one unit per upper storey, top balcony, drop ladder, roof hook
    for f in range(3):
        _place("fire_escape_floor_unit", (0.0, 0.0, GROUND + (f + 1) * FLOOR + 0.75))
    _place("fire_escape_balcony_top", (0.0, 0.0, GROUND + 0.75))
    _place("fire_escape_drop_ladder", (0.0, 0.0, GROUND + 0.75 - 3.20))
    _place("fire_escape_top_hook", (0.0, 0.0, GROUND + 4 * FLOOR + 0.75 - 2.16 + 0.10))
    for k in range(8):                                       # cornice run + returns
        _place("cornice_pressed_metal_a", (-W / 2 + 0.5 + k, 0.0, ROOF - 0.92))
    _place("cornice_return_end", (-W / 2 - 0.21, 0.0, ROOF - 0.92))
    ret = _place("cornice_return_end", (W / 2 + 0.21, 0.0, ROOF - 0.92))
    ret.scale = (-1.0, 1.0, 1.0)
    for k in range(9):                                       # parapet behind the cornice
        _place("parapet_wall_brick", (-W / 2 + 0.5 + k, 0.55, ROOF))
    _place("water_tower_small", (1.60, 4.30, ROOF), )
    _place("bulkhead_stair_brick", (-2.10, 5.40, ROOF))
    _place("hvac_vent_pipe_cluster", (-0.20, 2.60, ROOF))
    _place("antenna_tv_yagi", (2.90, 2.30, ROOF))
    _place("ivy_panel_sparse", (W / 2 - 1.05, 0.0, 0.25))
    _place("acc_satellite_dish", (0.92, 0.0, GROUND + 2 * FLOOR + 0.80))
    _place("hvac_rooftop_unit_small", (-2.60, 2.10, ROOF))

    path = OUT / "tenement_test.png"
    K.nb.quick_render(path, camera_location=(-10.5, -29.0, 7.0), camera_target=(0.0, 1.5, 10.0),
                      fov_deg=42.0, size=(res_x, int(res_x * 1.70)), samples=samples,
                      sun_azimuth_deg=196.0, sun_elevation_deg=48.0, sun_strength=3.4)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet")
    ap.add_argument("--ids", help="debug: render only these piece ids (comma separated) on the given --sheet")
    ap.add_argument("--tenement", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--res", type=int, default=1500)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.list:
        print("\n".join(SHEETS))
        return 0
    P.reg_flats()
    P.reg_generated_materials()
    build_kit.load_pieces()
    OUT.mkdir(parents=True, exist_ok=True)
    _clear()
    if a.tenement:
        p = tenement(samples=a.samples, res_x=a.res)
    elif a.sheet:
        p = sheet(a.sheet, samples=a.samples, res_x=a.res, only=set(a.ids.split(",")) if a.ids else None)
    else:
        ap.error("give --sheet NAME, --tenement or --list")
    print(f"wrote {p} ({p.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
