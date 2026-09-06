"""Verification renders for the prop library.

``--sheets`` renders one Cycles CPU still per group of props (each laid out on a sidewalk strip beside a 1.75 m
human-height reference rod) and captions it with the prop id and its measured bounding box, so scale and
proportion errors are visible at a glance.  ``--curb`` renders the composed 30 m Manhattan curb scene.

    nice -n 10 python3 blender/props/contact_sheets.py --sheets
    nice -n 10 python3 blender/props/contact_sheets.py --curb
    nice -n 10 python3 blender/props/contact_sheets.py --sheet trees_large --samples 32
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[0] / "common"))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import _core as C  # noqa: E402
import _palette as P  # noqa: E402
import nycsim_bpy as nb  # noqa: E402

log = logging.getLogger("nycsim.props.render")
OUT = C.nb.REPO_ROOT / "docs" / "verification" / "props"
REF_HEIGHT = 1.75          # human-height reference rod beside every prop

SHEETS: dict[str, dict] = {
    # the davit/crook arms reach along +Y, so these sheets are shot nearly side-on to show the arm profile
    "lighting": {"ids": ["lamp_cobra_davit", "lamp_bishops_crook", "lamp_park_twin"], "pad": 2.4, "azimuth": 78.0},
    "lighting_night": {"ids": ["lamp_cobra_davit", "lamp_bishops_crook", "lamp_park_twin", "subway_globe_green",
                               "subway_globe_red"], "pad": 2.0, "night": True, "azimuth": 66.0},
    "lighting_highmast": {"ids": ["lamp_highmast"], "pad": 3.0, "azimuth": 40.0},
    "traffic_signals": {"ids": ["signal_mastarm_6m", "signal_mastarm_9m", "signal_spanwire"], "pad": 2.0},
    "traffic_pedestrian": {"ids": ["signal_pedestal", "signal_ped_countdown", "ped_pushbutton"], "pad": 0.9},
    "signs_regulatory": {"ids": ["sign_r1_1_stop", "sign_r1_2_yield", "sign_r6_1_oneway", "sign_r2_1_speed"],
                         "pad": 0.5, "lift": 1.6},
    "signs_nyc": {"ids": ["sign_nyc_parking_18", "sign_nyc_parking_24", "sign_street_name_blade",
                          "post_u_channel_3m", "post_u_channel_2m"], "pad": 0.5, "lift": 1.6},
    "furniture_a": {"ids": ["hydrant_fdny", "litter_basket_wire", "litter_basket_betterbin", "mailbox_usps",
                            "standpipe_siamese"], "pad": 0.6},
    "furniture_b": {"ids": ["bollard_steel", "planter_concrete", "bench_worlds_fair", "muni_meter",
                            "fire_alarm_box"], "pad": 0.6},
    "furniture_large": {"ids": ["linknyc_kiosk", "bus_shelter_cemusa", "newsstand_stainless", "bike_rack_cityrack"],
                        "pad": 1.0},
    "citibike": {"ids": ["citibike_kiosk", "citibike_dock_unit", "citibike_bike"], "pad": 0.7},
    "subway": {"ids": ["subway_entrance", "subway_globe_green", "subway_globe_red"], "pad": 1.2},
    "mta_bullets": {"ids": ["mta_line_bullets"], "pad": 0.4, "front": True},
    "street_surface": {"ids": ["tree_guard", "tree_grate", "vent_grate_sidewalk", "manhole_coned", "manhole_dep"],
                       "pad": 0.7},
    "steam_stacks": {"ids": ["steam_stack_3m", "steam_stack_6m"], "pad": 1.2},
    "refuse_carts": {"ids": ["trash_bags_small", "trash_bags_large", "cart_halal", "cart_hotdog", "cart_coffee"],
                     "pad": 1.0},
    "construction": {"ids": ["jersey_barrier", "barrel_orange", "traffic_cone", "roadway_plate",
                             "sign_roadwork_w20_1", "construction_fence"], "pad": 1.0},
    "flags_fauna": {"ids": ["flag_us_pole", "flag_nyc_pole", "pigeon", "rat"], "pad": 1.0},
}
TREE_SPECIES = ["planetree", "honeylocust", "callery_pear", "pin_oak", "norway_maple",
                "littleleaf_linden", "ginkgo", "zelkova", "sophora", "red_maple"]
for _cls in ("small", "medium", "large"):
    SHEETS[f"trees_{_cls}"] = {"ids": [f"tree_{s}_{_cls}" for s in TREE_SPECIES], "pad": 1.5, "tree": True}
    SHEETS[f"trees_{_cls}_bare"] = {"ids": [f"tree_{s}_{_cls}_bare" for s in TREE_SPECIES], "pad": 1.5, "tree": True}


# --------------------------------------------------------------------------------------------- scene helpers
def _light_cone_slots(ob) -> set[int]:
    """Material-slot indices of the night-only light-cone effect on an imported prop (the importer suffixes
    duplicate material names, so the comparison is on the stem)."""
    return {i for i, m in enumerate(ob.data.materials) if m and m.name.split(".")[0] == "LIGHT_CONE"}


def import_prop(prop_id: str, keep_light_cones: bool = False) -> list[bpy.types.Object]:
    """Import ``<id>.glb``; only the LOD0 node is in the glTF scene, so only LOD0 comes in.

    ``LIGHT_CONE`` planes are a night-only effect volume. On a daylight sheet their *faces* are deleted — not
    the object, which is the whole joined lamp — because they would otherwise blow the image out."""
    path = C.PROPS_OUT / f"{prop_id}.glb"
    if not path.exists():
        raise FileNotFoundError(path)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    # Blender's importer instantiates nodes that no scene references, so the MSFT_lod LOD1 subtree comes in too
    # and would render on top of LOD0. Drop it: every exported object carries nycsim_lod (0 or 1).
    lod1 = [o for o in new if o.get("nycsim_lod") == 1 or (o.type == "EMPTY" and o.name.split(".")[0] == "LOD1")]
    for o in lod1:
        me = o.data if o.type == "MESH" else None
        new.remove(o)
        bpy.data.objects.remove(o)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    if not keep_light_cones:
        for o in new:
            if o.type != "MESH":
                continue
            slots = _light_cone_slots(o)
            if not slots:
                continue
            bm = C.bmesh.new()
            bm.from_mesh(o.data)
            bm.faces.ensure_lookup_table()
            doomed = [f for f in bm.faces if f.material_index in slots]
            if doomed:
                C.bmesh.ops.delete(bm, geom=doomed, context="FACES")
            bm.to_mesh(o.data)
            bm.free()
            o.data.update()
    return new


def solid_bounds(objs) -> tuple[Vector, Vector]:
    """Bounds of the physical geometry: polygons carrying the light-cone effect material are ignored, so a
    caption never reports the size of a lamp's light pool."""
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    bpy.context.view_layer.update()
    for o in objs:
        if o.type != "MESH":
            continue
        skip = _light_cone_slots(o)
        me = o.data
        for poly in me.polygons:
            if poly.material_index in skip:
                continue
            for vi in poly.vertices:
                w = o.matrix_world @ me.vertices[vi].co
                lo = Vector(map(min, lo, w))
                hi = Vector(map(max, hi, w))
    if not all(map(math.isfinite, lo)):
        return world_bounds(objs)
    return lo, hi


def ground(size_x: float, size_y: float, center_x: float = 0.0, material=None) -> bpy.types.Object:
    """Plain neutral pad under the row: a contact sheet is about the prop, and an untextured ground samples
    far faster than a tiling concrete material."""
    return C.box("ground", (size_x, size_y, 0.10), origin=(center_x, 0.0, -0.10),
                 material=material or C.mat_solid("sheet_ground", "#8E9297", 0.85))


def reference_rod(x: float, y: float, name: str) -> list[bpy.types.Object]:
    """1.75 m grey rod with a 1 m white band — the human-height scale reference in every sheet."""
    grey = C.mat_solid("ref_rod", "#9AA0A6", 0.6)
    white = C.mat_solid("ref_band", "#F2F2F2", 0.5)
    rod = C.cyl(f"{name}_rod", 0.024, REF_HEIGHT, 10, origin=(x, y, 0.0), material=grey)
    band = C.cyl(f"{name}_band", 0.027, 0.05, 10, origin=(x, y, 1.00), material=white)
    foot = C.cyl(f"{name}_foot", 0.10, 0.012, 12, origin=(x, y, 0.0), material=grey)
    return [rod, band, foot]


def layout(ids: list[str], pad: float, lift: float = 0.0, night: bool = False) -> tuple[list[dict], float, float]:
    """Import each prop, place it in a row along X with its own reference rod. Returns placements and row extent."""
    placed = []
    cursor = 0.0
    top = 0.0
    for pid in ids:
        objs = import_prop(pid, keep_light_cones=night)
        lo, hi = solid_bounds(objs)           # the caption is the prop's physical size, never its light pool
        w = max(hi.x - lo.x, 0.05)
        cx = (hi.x + lo.x) / 2.0
        x = cursor + pad * 0.5 + w / 2.0
        for o in objs:
            if o.parent is None:
                o.location.x += x - cx
                o.location.z += lift
        placed.append({"id": pid, "x": x, "w": w, "size": [round(hi[i] - lo[i], 3) for i in range(3)],
                       "top": hi.z + lift})
        top = max(top, hi.z + lift)
        reference_rod(x + w / 2.0 + pad * 0.30, 0.0, f"ref_{pid}")
        cursor = x + w / 2.0 + pad
    return placed, cursor, top


def render_still(path: Path, *, center: Vector, ortho_scale: float, size: tuple[int, int], samples: int,
                 azimuth_deg: float = 26.0, elevation_deg: float = 11.0, sun_azimuth_deg: float = 214.0,
                 sun_elevation_deg: float = 46.0, sun_strength: float = 3.0, night: bool = False) -> Path:
    """Orthographic Cycles CPU still. Orthographic keeps every prop on the sheet at the same metres-per-pixel,
    which is the whole point of a contact sheet: a wrong size cannot hide behind perspective."""
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("sheet_cam")
    cam.type = "ORTHO"
    cam.ortho_scale = ortho_scale
    cam.clip_start, cam.clip_end = 0.1, 4000.0
    camob = bpy.data.objects.new("sheet_cam", cam)
    nb.link(camob)
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    # +Y is the props' facing direction (docs: _core module header), so the camera stands on the +Y side
    back = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    camob.location = center + back * (ortho_scale * 2.0 + 60.0)
    camob.rotation_euler = (-back).to_track_quat("-Z", "Y").to_euler()
    sc.camera = camob
    sun = bpy.data.lights.new("sheet_sun", "SUN")
    sun.energy = 0.02 if night else sun_strength
    sun.angle = math.radians(1.6)
    sunob = bpy.data.objects.new("sheet_sun", sun)
    nb.link(sunob)
    sunob.rotation_euler = (math.radians(90 - sun_elevation_deg), 0.0, math.radians(sun_azimuth_deg))
    fill = bpy.data.lights.new("sheet_fill", "SUN")
    fill.energy = 0.0 if night else sun_strength * 0.25
    fillob = bpy.data.objects.new("sheet_fill", fill)
    nb.link(fillob)
    fillob.rotation_euler = (math.radians(60.0), 0.0, math.radians(-sun_azimuth_deg + 150.0))
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    # a brighter sky keeps galvanised and stainless props from reading black: with no environment to reflect,
    # a metallic BSDF has nothing to return
    bg.inputs["Color"].default_value = (0.020, 0.030, 0.060, 1.0) if night else (0.44, 0.52, 0.64, 1.0)
    bg.inputs["Strength"].default_value = 0.6 if night else 1.5
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.cycles.transparent_max_bounces = 12
    sc.view_settings.view_transform = "Standard"       # verification renders must show the authored colours
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return path


def render_sheet(name: str, spec: dict, samples: int, width: int) -> Path:
    C.nb.reset_scene()
    for cache in (bpy.data.materials, bpy.data.images, bpy.data.meshes):
        for it in list(cache):
            cache.remove(it)
    night = bool(spec.get("night"))
    placed, row_len, top = layout(spec["ids"], spec.get("pad", 1.0), spec.get("lift", 0.0), night=night)
    # the pad runs far past the frame in Y so its far edge never crosses the picture
    ground(row_len * 2.0 + 400.0, 400.0, row_len / 2.0)
    ortho = row_len * 1.04
    height_px = max(220, min(1400, int(width * (top + 0.9) / ortho)))
    out = OUT / f"sheet_{name}.png"
    render_still(out, center=Vector((row_len / 2.0, 0.0, (top + 0.9) / 2.0 - 0.35)), ortho_scale=ortho,
                 size=(width, height_px), samples=samples * (2 if night else 1), night=night,
                 azimuth_deg=spec.get("azimuth", 0.0 if spec.get("front") else 26.0),
                 elevation_deg=spec.get("elevation", 4.0 if spec.get("front") else 11.0))
    annotate(out, placed, width, height_px)
    return out


def annotate(path: Path, placed: list[dict], width: int, height: int) -> None:
    """Caption each prop with its id and measured bounding box, under the position it occupies in the frame."""
    from bpy_extras.object_utils import world_to_camera_view
    from PIL import Image, ImageDraw, ImageFont
    sc = bpy.context.scene
    cam = sc.camera
    labels = []
    for p in placed:
        co = world_to_camera_view(sc, cam, Vector((p["x"], 0.0, 0.0)))
        labels.append((max(0.0, min(1.0, co.x)) * width, p))
    im = Image.open(path).convert("RGB")
    strip = 62
    sheet = Image.new("RGB", (width, height + strip), (22, 24, 26))
    sheet.paste(im, (0, 0))
    d = ImageDraw.Draw(sheet)
    font_path = C.FONT_SEMIBOLD
    f1 = ImageFont.truetype(str(font_path), 14)
    f2 = ImageFont.truetype(str(font_path), 11)
    # captions are staggered over two bands so long ids on a crowded sheet cannot overlap
    labels.sort(key=lambda t: t[0])
    for k, (x, p) in enumerate(labels):
        band = (k % 2) * 30
        txt = p["id"]
        dims = "x".join(f"{v:g}" for v in p["size"]) + " m"
        w1 = d.textlength(txt, font=f1)
        w2 = d.textlength(dims, font=f2)
        x1 = max(2, min(width - w1 - 2, x - w1 / 2))
        x2 = max(2, min(width - w2 - 2, x - w2 / 2))
        d.line([(x, height), (x, height + 4 + band)], fill=(90, 96, 102))
        d.text((x1, height + 4 + band), txt, font=f1, fill=(236, 238, 240))
        d.text((x2, height + 19 + band), dims, font=f2, fill=(150, 200, 160))
    sheet.save(path)


# --------------------------------------------------------------------------------------------- curb scene
SIDEWALK_TOP = 0.15          # NYC curb reveal
CURB_PLACEMENT = [
    # (prop id, x along the curb (m), y from the curb line (+Y towards the buildings), heading deg, z)
    ("lamp_cobra_davit", 3.20, 0.55, 180.0, SIDEWALK_TOP),
    ("signal_mastarm_6m", 27.60, 0.60, 270.0, SIDEWALK_TOP),
    ("signal_ped_countdown", 26.10, 0.80, 180.0, SIDEWALK_TOP),
    ("hydrant_fdny", 8.60, 0.65, 180.0, SIDEWALK_TOP),
    ("litter_basket_wire", 1.20, 0.70, 180.0, SIDEWALK_TOP),
    ("tree_grate", 13.00, 1.45, 0.0, SIDEWALK_TOP - 0.06),
    ("tree_guard", 13.00, 1.45, 0.0, SIDEWALK_TOP),
    ("tree_callery_pear_medium", 13.00, 1.45, 0.0, SIDEWALK_TOP),
    ("linknyc_kiosk", 17.60, 1.10, 90.0, SIDEWALK_TOP),
    ("post_u_channel_3m", 21.30, 0.62, 0.0, SIDEWALK_TOP),
    ("sign_nyc_parking_24", 21.30, 0.585, 180.0, SIDEWALK_TOP + 2.05),
    ("subway_entrance", 6.30, 3.30, 90.0, SIDEWALK_TOP),
    ("subway_globe_green", 4.35, 2.20, 0.0, SIDEWALK_TOP),
    ("mailbox_usps", 24.10, 0.95, 180.0, SIDEWALK_TOP),
    ("bollard_steel", 10.60, 0.62, 0.0, SIDEWALK_TOP),
    ("bench_worlds_fair", 30.40, 1.10, 180.0, SIDEWALK_TOP),
    ("trash_bags_small", 22.80, 0.75, 0.0, SIDEWALK_TOP),
    ("manhole_coned", 19.00, -3.20, 0.0, 0.0),
    ("traffic_cone", 16.10, -1.20, 0.0, 0.0),
    ("pigeon", 9.60, 1.55, 40.0, SIDEWALK_TOP),
]
# the subway stair opening is cut out of the sidewalk slab (x0, x1, y0, y1)
SUBWAY_HOLE = (4.70, 7.90, 2.30, 4.32)


def render_curb(samples: int, width: int) -> Path:
    """30 m of Manhattan curb: roadway, curb stone, a sidewalk with the stair opening cut out of it, a blank
    building wall, and the props a real block carries."""
    C.nb.reset_scene()
    for cache in (bpy.data.materials, bpy.data.images, bpy.data.meshes):
        for it in list(cache):
            cache.remove(it)
    x0, x1 = -6.0, 38.0
    y_walk0, y_walk1 = 0.10, 4.90
    hx0, hx1, hy0, hy1 = SUBWAY_HOLE
    C.box("roadway", (x1 - x0, 12.0, 0.30), origin=((x0 + x1) / 2, -6.20, -0.30), material=P.asphalt(), anchor="bottom")
    C.box("curb_stone", (x1 - x0, 0.30, 0.32), origin=((x0 + x1) / 2, -0.05, -0.17), material=P.concrete(), anchor="bottom")
    walk = P.sidewalk()
    for i, (a, b, c, d) in enumerate((
            (x0, hx0, y_walk0, y_walk1), (hx1, x1, y_walk0, y_walk1),
            (hx0, hx1, y_walk0, hy0), (hx0, hx1, hy1, y_walk1))):
        C.box(f"sidewalk{i}", (b - a, d - c, SIDEWALK_TOP), origin=((a + b) / 2, (c + d) / 2, 0.0),
              material=walk, anchor="bottom")
    C.box("building_wall", (x1 - x0, 0.8, 16.0), origin=((x0 + x1) / 2, y_walk1 + 0.40, 0.0),
          material=P.concrete_rough(), anchor="bottom")
    C.box("lane_line", (x1 - x0, 0.12, 0.004), origin=((x0 + x1) / 2, -6.60, 0.0),
          material=C.mat_solid("lane_paint", "#E4E2D8", 0.7), anchor="bottom")
    from mathutils import Matrix
    for pid, x, y, heading, z in CURB_PLACEMENT:
        objs = import_prop(pid)
        place = Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(math.radians(heading), 4, "Z")
        for o in objs:
            if o.parent is None:
                o.matrix_world = place @ o.matrix_world
    out = OUT / "curb_test.png"
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("curb_cam")
    cam.lens_unit = "FOV"
    cam.angle = math.radians(64.0)
    cam.clip_end = 500.0
    camob = bpy.data.objects.new("curb_cam", cam)
    nb.link(camob)
    camob.location = Vector((-4.2, -6.8, 1.68))
    camob.rotation_euler = (Vector((18.0, 1.6, 3.05)) - camob.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = camob
    sun = bpy.data.lights.new("curb_sun", "SUN")
    sun.energy = 2.9
    sun.angle = math.radians(0.9)
    sunob = bpy.data.objects.new("curb_sun", sun)
    nb.link(sunob)
    sunob.rotation_euler = (math.radians(90 - 40.0), 0.0, math.radians(120.0))
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(40.0)
    sky.sun_rotation = math.radians(120.0)
    sky.sun_intensity = 0.0
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.32
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.transparent_max_bounces = 16
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x, sc.render.resolution_y = (width, int(width * 0.58))
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheets", action="store_true", help="render every contact sheet")
    ap.add_argument("--sheet", action="append", default=None, choices=sorted(SHEETS))
    ap.add_argument("--curb", action="store_true")
    ap.add_argument("--samples", type=int, default=20)
    ap.add_argument("--width", type=int, default=1200)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname).1s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    names = list(SHEETS) if args.sheets else (args.sheet or [])
    for n in names:
        p = render_sheet(n, SHEETS[n], args.samples, args.width)
        log.info("sheet %-22s -> %s (%d kB)", n, p, p.stat().st_size // 1024)
        made.append(str(p))
    if args.curb:
        p = render_curb(args.samples, max(args.width, 1400))
        log.info("curb scene -> %s (%d kB)", p, p.stat().st_size // 1024)
        made.append(str(p))
    if not names and not args.curb:
        ap.error("nothing to do: pass --sheets, --sheet NAME or --curb")
    print(json.dumps({"rendered": made}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
