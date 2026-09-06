#!/usr/bin/env python3
"""Verification renders for the vehicle lane (ADR-012: Cycles CPU, 64 samples).

    python3 blender/vehicles/render_verify.py fusion      -> fusion_exterior.png, fusion_interior_driver_pov.png
    python3 blender/vehicles/render_verify.py fleet        -> fleet_lineup.png (imports every exported glb)
    python3 blender/vehicles/render_verify.py ortho        -> fusion_orthographic.png (side/front/top elevations)

All images land in ``docs/verification/vehicles/``.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vlib import env  # noqa: E402

env.setup_logging()

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from vlib import geom as g, materials as M  # noqa: E402

log = env.log
nb = env.nb


def ground(size: float = 120.0, rgb=(0.055, 0.055, 0.058)) -> bpy.types.Object:
    bm = g.box_bm((size, size, 0.04), (0, 0, -0.02))
    ob = g.to_object("Ground", bm, [M.basic("VERIFY_ASPHALT", rgb, roughness=0.88)], smooth=False)
    return ob


def world_sky(sun_elev_deg: float = 38.0, sun_rot_deg: float = 215.0, strength: float = 0.85) -> None:
    sc = bpy.context.scene
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    sky.sun_intensity = 0.0
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength


def sun(elev_deg: float = 38.0, azim_deg: float = 215.0, energy: float = 4.0) -> bpy.types.Object:
    li = bpy.data.lights.new("verify_sun", "SUN")
    li.energy = energy
    li.angle = math.radians(1.2)
    ob = bpy.data.objects.new("verify_sun", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90 - elev_deg), 0.0, math.radians(-azim_deg))
    return ob


def area_fill(loc, size: float, energy: float, target=(0, 0, 0)) -> bpy.types.Object:
    li = bpy.data.lights.new("fill", "AREA")
    li.energy = energy
    li.size = size
    ob = bpy.data.objects.new("fill", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


SIZE = (1600, 900)


def shoot(path: Path, *, loc, target, fov: float = 40.0, size=None, samples: int = 64,
          ortho_scale: float | None = None) -> Path:
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("cam")
    if ortho_scale:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    else:
        cam.lens_unit = "FOV"
        cam.angle = math.radians(fov)
    cam.clip_start = 0.02
    cam.clip_end = 400.0
    ob = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.camera = ob
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = size or SIZE
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.render.image_settings.file_format = "PNG"
    path.parent.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ob, do_unlink=True)
    log.info("rendered %s", path)
    return path


# --------------------------------------------------------------------------- fusion
def render_fusion(samples: int, which: str = "both") -> None:
    import build_fusion as BF
    v, ctx = BF.build()
    for o in list(bpy.data.objects):
        if o.name.startswith("UCX_"):
            g.remove_object(o)
    ground()
    world_sky()
    sun()
    if which in ("both", "exterior"):
        shoot(env.VERIFY_DIR / "fusion_exterior.png", loc=(9.4, 5.6, 2.35), target=(1.55, 0.0, 0.72),
              fov=30.0, samples=samples)
    if which in ("both", "interior"):
        # SAE eyellipse centroid for the driver: 0.09 m ahead of the H-point and 0.74 m above it, i.e.
        # (1.99, +0.375, 1.245) for the H-point at (1.90, +0.375, 0.505).
        eye = (1.99, 0.375, 1.245)
        area_fill((1.10, 0.0, 1.32), 1.1, 40.0, target=(2.7, 0.0, 0.85))
        area_fill((2.60, 0.90, 1.30), 0.8, 25.0, target=(2.2, 0.2, 0.90))
        shoot(env.VERIFY_DIR / "fusion_interior_driver_pov.png", loc=eye, target=(6.4, 0.10, 0.42),
              fov=64.0, samples=samples)


def render_ortho(samples: int) -> None:
    import build_fusion as BF
    v, ctx = BF.build()
    for o in list(bpy.data.objects):
        if o.name.startswith("UCX_"):
            g.remove_object(o)
    ground(rgb=(0.5, 0.5, 0.5))
    world_sky(sun_elev_deg=70.0, strength=1.6)
    sun(elev_deg=70.0, energy=2.5)
    shoot(env.VERIFY_DIR / "fusion_ortho_side.png", loc=(1.4, 30.0, 0.74), target=(1.4, 0.0, 0.74),
          ortho_scale=5.6, size=(SIZE[0], int(SIZE[0] * 0.44)), samples=max(24, samples // 2))


# --------------------------------------------------------------------------- fleet
def import_glb(path: Path, offset_y: float, yaw_deg: float = 0.0) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.location = (r.location.x, r.location.y + offset_y, r.location.z)
        r.rotation_euler = (r.rotation_euler.x, r.rotation_euler.y, r.rotation_euler.z + math.radians(yaw_deg))
    return new


def render_fleet(samples: int) -> None:
    nb.reset_scene()
    cat_dir = env.CATALOG_DIR
    entries = []
    for p in sorted(cat_dir.glob("*.json")):
        e = json.loads(p.read_text())
        if e.get("base_id"):
            continue                      # liveries share the base geometry; show one per body
        entries.append(e)
    if not entries:
        raise SystemExit("no catalog entries; run the builders first")
    entries.sort(key=lambda e: (e["class"], -e["published_dimensions_mm"]["length_mm"]))
    log.info("fleet lineup: %d vehicles", len(entries))
    ground(size=400.0)
    world_sky(sun_elev_deg=42.0, sun_rot_deg=200.0)
    sun(elev_deg=42.0, azim_deg=200.0)
    y = 0.0
    xs = []
    for e in entries:
        glb = nb.BLENDER_OUT.parent / e["glb"]
        if not glb.exists():
            log.warning("missing %s", glb)
            continue
        w = e["measured_m"]["width_over_mirrors_m"]
        y += w / 2 + 0.55
        import_glb(glb, offset_y=y)
        xs.append((e["id"], y))
        y += w / 2
    total = y
    cx = total / 2.0
    shoot(env.VERIFY_DIR / "fleet_lineup.png",
          loc=(46.0, cx - 6.0, 22.0), target=(1.0, cx, 1.1), fov=34.0, size=(SIZE[0] + 600, SIZE[1] + 200), samples=samples)
    (env.VERIFY_DIR / "fleet_lineup_order.json").write_text(json.dumps(
        {"order_left_to_right": [i for i, _ in xs], "y_offsets_m": {i: round(o, 3) for i, o in xs}}, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("what", choices=("fusion", "fusion_exterior", "fusion_interior", "fleet", "ortho"))
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--width", type=int, default=1600, help="render width; height follows 16:9")
    args = ap.parse_args()
    env.ensure_dirs()
    global SIZE
    SIZE = (args.width, int(round(args.width * 9 / 16)))
    if args.what == "fusion":
        render_fusion(args.samples)
    elif args.what == "fusion_exterior":
        render_fusion(args.samples, "exterior")
    elif args.what == "fusion_interior":
        render_fusion(args.samples, "interior")
    elif args.what == "ortho":
        render_ortho(args.samples)
    else:
        render_fleet(args.samples)
    return 0


if __name__ == "__main__":
    code = main()
    env.finish(code)
