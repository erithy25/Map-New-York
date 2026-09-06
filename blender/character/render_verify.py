"""Cycles CPU verification renders for the character lane (ADR-012).

Produces, into ``docs/verification/character/``:

``face_closeup.png``     head-and-shoulders three-quarter portrait - checks the face targets, the split
                         eyes (eyeball + refractive cornea + tagged iris), lashes, brows, teeth and the
                         subsurface skin;
``full_body.png``        the finished player in his clothes, front and back;
``walk_strip.png``       eight evenly spaced frames of one retargeted walk cycle;
``bend_test.png``        elbow and knee flexed 0/45/90/120 degrees with the skin shaded flat, so that
                         collapsing or candy-wrapping weights are visible;
``npc_lineup.png``       twelve generated pedestrians side by side;
``blendshapes.png``      a contact sheet of representative ARKit face units at full weight.

Run::

    nice -n 10 python3 blender/character/render_verify.py --all
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from pathlib import Path

import chenv

chenv.setup_logging()

import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

import anim_lib  # noqa: E402
import nycsim_bpy as nb  # noqa: E402

log = logging.getLogger("nycsim.character.render")

SAMPLES = 64


# --------------------------------------------------------------------------------------------- scene setup
def studio_lighting(*, key_energy: float = 900.0, backdrop: bool = True, size: float = 6.0) -> None:
    """Three-point area lighting on a neutral backdrop - the standard character-review setup."""
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.045, 0.048, 0.055, 1.0)
    background.inputs["Strength"].default_value = 1.0

    def area(name: str, location, rotation, energy: float, dimension: float, colour) -> None:
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy
        light.size = dimension
        light.color = colour
        obj = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = rotation

    area("key", (1.9, -2.4, 2.5), (math.radians(52), 0.0, math.radians(38)), key_energy, 1.6,
         (1.0, 0.96, 0.92))
    area("fill", (-2.4, -1.7, 1.5), (math.radians(74), 0.0, math.radians(-52)), key_energy * 0.28, 2.4,
         (0.86, 0.90, 1.0))
    area("rim", (-0.9, 2.6, 2.2), (math.radians(120), 0.0, math.radians(-165)), key_energy * 0.55, 1.2,
         (0.92, 0.95, 1.0))

    if backdrop:
        mesh = bpy.data.meshes.new("backdrop")
        s = size
        mesh.from_pydata([(-s, 2.2, -0.02), (s, 2.2, -0.02), (s, 2.2, s), (-s, 2.2, s),
                          (-s, 2.2, -0.02), (s, 2.2, -0.02), (s, -s, -0.02), (-s, -s, -0.02)],
                         [], [(0, 1, 2, 3), (4, 5, 6, 7)])
        mesh.update()
        mesh.materials.append(nb.pbr_material("backdrop", base_color=(0.16, 0.17, 0.19, 1.0),
                                              roughness=0.9))
        obj = bpy.data.objects.new("backdrop", mesh)
        bpy.context.scene.collection.objects.link(obj)


def render(path: Path, *, location, target, fov_deg: float, size, samples: int = SAMPLES,
           transparent: bool = False) -> Path:
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(fov_deg)
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = Vector(location)
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 4
    scene.cycles.volume_bounces = 0
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.cycles.blur_glossy = 1.0
    scene.cycles.use_fast_gi = True
    scene.render.film_transparent = transparent
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    log.info("%s rendered in %.0f s", path.name, time.time() - t0)
    return path


def load_player() -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    blend = chenv.OUT_DIR / "player.blend"
    if not blend.exists():
        raise FileNotFoundError(f"{blend} not found - run blender/character/build_character.py first")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    armature = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    return armature, meshes


def _bounds(objects) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            world = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, world))
            hi = Vector(map(max, hi, world))
    return lo, hi


def _forward(armature: bpy.types.Object) -> Vector:
    """Mean toe direction of both feet - the body facing axis (matches anim_procedural.BodyRef)."""
    total = Vector((0.0, 0.0, 0.0))
    for side in ("l", "r"):
        ball = armature.data.bones[f"ball_{side}"]
        v = armature.matrix_world.to_3x3() @ (ball.tail_local - ball.head_local)
        v.z = 0.0
        total += v
    return total.normalized()


def set_pose(armature: bpy.types.Object, action_name: str, frame: int) -> None:
    action = bpy.data.actions.get(action_name)
    if action is None:
        raise KeyError(f"no action {action_name!r} in the scene ({sorted(a.name for a in bpy.data.actions)})")
    anim_lib.set_active_clip(armature, action)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


# ------------------------------------------------------------------------------------------------ renders
def _face_focus(armature: bpy.types.Object, meshes) -> tuple[Vector, Vector]:
    """(focus point just inside the face, forward axis). Found from the nose tip, not from a bone offset."""
    forward = _forward(armature)
    body = next(o for o in meshes if o.name.endswith(".body"))
    head_bone = armature.data.bones["head"]
    z_lo = head_bone.head_local.z
    group = body.vertex_groups.get("head")
    names = [g.name for g in body.vertex_groups]
    best, best_d = None, -math.inf
    for vert in body.data.vertices:
        if group is not None:
            weight = next((g.weight for g in vert.groups if names[g.group] == "head"), 0.0)
            if weight < 0.5:
                continue
        world = body.matrix_world @ vert.co
        if world.z < z_lo:
            continue
        d = world.dot(forward)
        if d > best_d:
            best, best_d = world, d
    if best is None:
        best = armature.matrix_world @ head_bone.head_local
    return best - forward * 0.06, forward


def face_closeup(out: Path) -> Path:
    armature, meshes = load_player()
    studio_lighting(key_energy=300.0, size=3.0)
    set_pose(armature, "idle", 1)
    focus, forward = _face_focus(armature, meshes)
    right = forward.cross(Vector((0.0, 0.0, 1.0)))
    cam = focus + forward * 0.50 + right * 0.26 + Vector((0.0, 0.0, 0.035))
    return render(out, location=cam, target=focus, fov_deg=30.0, size=(680, 840), samples=SAMPLES)


def full_body(out: Path) -> Path:
    armature, meshes = load_player()
    studio_lighting(key_energy=1400.0, size=7.0)
    set_pose(armature, "idle", 1)
    lo, hi = _bounds(meshes)
    centre = (lo + hi) * 0.5
    forward = _forward(armature)
    height = hi.z - lo.z
    front = centre + forward * (height * 1.5)
    back = centre - forward * (height * 1.5) + forward.cross(Vector((0, 0, 1))) * 0.1
    left = render(out.with_name("full_body_front.png"), location=front, target=centre, fov_deg=40.0,
                  size=(480, 960))
    right = render(out.with_name("full_body_back.png"), location=back, target=centre, fov_deg=40.0,
                   size=(480, 960))
    return stitch([left, right], out, gap=12)


def walk_strip(out: Path, action: str = "walk", count: int = 8) -> Path:
    armature, meshes = load_player()
    studio_lighting(key_energy=1400.0, size=7.0)
    action_data = bpy.data.actions.get(action)
    if action_data is None:
        raise KeyError(f"no action {action!r}")
    start, end = (int(v) for v in action_data.frame_range)
    lo, hi = _bounds(meshes)
    centre = (lo + hi) * 0.5
    forward = _forward(armature)
    side = forward.cross(Vector((0.0, 0.0, 1.0)))
    height = hi.z - lo.z
    cam = centre + side * (height * 1.45) + forward * (height * 0.25)
    tiles = []
    for i in range(count):
        frame = start + round((end - start) * i / count)
        set_pose(armature, action, frame)
        tiles.append(render(chenv.VERIFY_DIR / f"_strip_{action}_{i}.png", location=cam, target=centre,
                            fov_deg=34.0, size=(260, 540), samples=32))
    result = stitch(tiles, out, gap=4)
    for tile in tiles:
        tile.unlink(missing_ok=True)
    return result


def bend_test(out: Path) -> Path:
    """Elbow and knee flexed through 0/45/90/120 degrees, matcap-flat, to expose bad weights."""
    armature, meshes = load_player()
    studio_lighting(key_energy=1100.0, size=5.0)
    # hide the clothing so the skin deformation itself is visible
    body = next(o for o in meshes if o.name.endswith(".body"))
    for obj in meshes:
        obj.hide_render = obj is not body
    _flat_shade(body)

    anim_lib.set_active_clip(armature, None)
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

    angles = (0.0, 45.0, 90.0, 120.0)
    lo, hi = _bounds([body])
    elbow_tiles, knee_tiles = [], []
    for angle in angles:
        _set_local_rotation(armature, "lowerarm_l", (-angle, 0.0, 0.0))
        _set_local_rotation(armature, "calf_l", (angle, 0.0, 0.0))
        bpy.context.view_layer.update()
        elbow = armature.matrix_world @ armature.data.bones["lowerarm_l"].head_local
        knee = armature.matrix_world @ armature.data.bones["calf_l"].head_local
        forward = _forward(armature)
        side = forward.cross(Vector((0.0, 0.0, 1.0)))
        elbow_tiles.append(render(chenv.VERIFY_DIR / f"_elbow_{int(angle)}.png",
                                  location=elbow + side * 0.42 + forward * 0.05 + Vector((0, 0, 0.04)),
                                  target=elbow, fov_deg=34.0, size=(340, 340), samples=48))
        knee_tiles.append(render(chenv.VERIFY_DIR / f"_knee_{int(angle)}.png",
                                 location=knee + side * 0.50 + forward * 0.08,
                                 target=knee, fov_deg=34.0, size=(340, 340), samples=48))
    row_a = stitch(elbow_tiles, chenv.VERIFY_DIR / "_row_elbow.png", gap=4)
    row_b = stitch(knee_tiles, chenv.VERIFY_DIR / "_row_knee.png", gap=4)
    result = stitch([row_a, row_b], out, gap=6, vertical=True)
    for tile in [*elbow_tiles, *knee_tiles, row_a, row_b]:
        tile.unlink(missing_ok=True)
    _ = lo, hi
    return result


def _flat_shade(obj: bpy.types.Object) -> None:
    material = nb.pbr_material("bend_test_clay", base_color=(0.72, 0.70, 0.68, 1.0), roughness=0.55)
    obj.data.materials.clear()
    obj.data.materials.append(material)


def _set_local_rotation(armature: bpy.types.Object, bone: str, degrees) -> None:
    pose_bone = armature.pose.bones[bone]
    pose_bone.rotation_mode = "QUATERNION"
    pose_bone.matrix_basis = Euler((math.radians(degrees[0]), math.radians(degrees[1]),
                                    math.radians(degrees[2])), "XYZ").to_matrix().to_4x4()


def blendshape_sheet(out: Path, names=("jawOpen", "mouthSmileLeft", "eyeBlinkLeft", "browInnerUp",
                                       "mouthPucker", "cheekPuff")) -> Path:
    armature, meshes = load_player()
    studio_lighting(key_energy=260.0, size=3.0)
    set_pose(armature, "idle", 1)
    body = next(o for o in meshes if o.name.endswith(".body"))
    keys = body.data.shape_keys.key_blocks
    eye, forward = _face_focus(armature, meshes)
    cam = eye + forward * 0.42 + Vector((0.0, 0.0, 0.02))
    tiles = []
    for name in names:
        if name not in keys:
            continue
        keys[name].value = 1.0
        bpy.context.view_layer.update()
        tiles.append(render(chenv.VERIFY_DIR / f"_bs_{name}.png", location=cam, target=eye, fov_deg=22.0,
                            size=(230, 260), samples=32))
        keys[name].value = 0.0
    half = (len(tiles) + 1) // 2
    row_a = stitch(tiles[:half], chenv.VERIFY_DIR / "_bs_row_a.png", gap=4)
    row_b = stitch(tiles[half:], chenv.VERIFY_DIR / "_bs_row_b.png", gap=4)
    result = stitch([row_a, row_b], out, gap=6, vertical=True)
    for tile in [*tiles, row_a, row_b]:
        tile.unlink(missing_ok=True)
    return result


def npc_lineup(out: Path, count: int = 12) -> Path:
    """Load each exported NPC glb into one scene and photograph the line-up."""
    from npc_generator import NPC_DIR  # noqa: PLC0415

    files = sorted(NPC_DIR.glob("npc_*.glb"))[:count]
    if not files:
        raise FileNotFoundError(f"no NPC glb files in {NPC_DIR} - run npc_generator.py first")
    nb.reset_scene()
    studio_lighting(key_energy=2600.0, size=14.0)
    spacing = 0.72
    imported = []
    for i, path in enumerate(files):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        new = [o for o in bpy.data.objects if o not in before]
        roots = [o for o in new if o.parent is None]
        offset = Vector(((i - (len(files) - 1) / 2.0) * spacing, 0.0, 0.0))
        for root in roots:
            root.location = root.location + offset
            root.rotation_euler = (math.radians(90.0), 0.0, 0.0)   # glTF Y-up back to Blender Z-up
        imported.extend(new)
    bpy.context.view_layer.update()
    lo, hi = _bounds(imported)
    centre = Vector(((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5, (lo.z + hi.z) * 0.5))
    width = hi.x - lo.x
    cam = centre + Vector((0.0, -width * 1.05, 0.25))
    return render(out, location=cam, target=centre, fov_deg=46.0, size=(1500, 560), samples=32)


# --------------------------------------------------------------------------------------------- compositing
def stitch(paths, out: Path, *, gap: int = 8, vertical: bool = False,
           background=(24, 25, 28)) -> Path:
    from PIL import Image  # noqa: PLC0415

    images = [Image.open(p).convert("RGB") for p in paths]
    if vertical:
        width = max(im.width for im in images)
        height = sum(im.height for im in images) + gap * (len(images) - 1)
    else:
        width = sum(im.width for im in images) + gap * (len(images) - 1)
        height = max(im.height for im in images)
    sheet = Image.new("RGB", (width, height), background)
    cursor = 0
    for im in images:
        if vertical:
            sheet.paste(im, ((width - im.width) // 2, cursor))
            cursor += im.height + gap
        else:
            sheet.paste(im, (cursor, (height - im.height) // 2))
            cursor += im.width + gap
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


# --------------------------------------------------------------------------------------------------- CLI
RENDERS = {
    "face": ("face_closeup.png", face_closeup),
    "body": ("full_body.png", full_body),
    "walk": ("walk_strip.png", walk_strip),
    "bend": ("bend_test.png", bend_test),
    "blendshapes": ("blendshapes.png", blendshape_sheet),
    "npc": ("npc_lineup.png", npc_lineup),
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("which", nargs="*", choices=sorted(RENDERS) + ["all"], default=["all"])
    args = parser.parse_args(argv)
    wanted = sorted(RENDERS) if "all" in args.which else args.which
    chenv.VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    for key in wanted:
        filename, function = RENDERS[key]
        path = function(chenv.VERIFY_DIR / filename)
        log.info("wrote %s (%.0f kB)", path, path.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main(sys.argv[1:])
    except Exception:
        logging.exception("render failed")
    chenv.hard_exit(code)
