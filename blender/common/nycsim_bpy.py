"""Shared helpers for every NYCSim Blender (bpy) script.

Conventions (docs/DATA_CONTRACTS.md §13): metres, Z-up in Blender, glTF exported Y-up with
``asset.extras.nycsim`` metadata. Import this module first in every script:

    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "common"))
    import nycsim_bpy as nb
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

import bpy
import bmesh
from mathutils import Vector

REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
BLENDER_OUT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO_ROOT / "blender_out"))
ASSETS = REPO_ROOT / "assets"
SCHEMA_VERSION = 1


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "uncommitted"


# --------------------------------------------------------------------------- scene
def reset_scene(unit_scale: float = 1.0) -> bpy.types.Scene:
    """Empty factory scene, metric units, metres."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = unit_scale
    sc.unit_settings.length_unit = "METERS"
    return sc


def collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def link(ob: bpy.types.Object, col: bpy.types.Collection | None = None) -> bpy.types.Object:
    (col or bpy.context.scene.collection).objects.link(ob)
    return ob


# --------------------------------------------------------------------------- mesh building
def mesh_object(name: str, verts: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], *, edges: Sequence[Sequence[int]] = (),
                col: bpy.types.Collection | None = None, materials: Iterable[bpy.types.Material] = (), smooth: bool = False,
                validate: bool = True) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [tuple(e) for e in edges], [tuple(f) for f in faces])
    if validate:
        me.validate(verbose=False, clean_customdata=False)
    me.update()
    for m in materials:
        me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    return link(ob, col)


def bmesh_to_object(name: str, bm: bmesh.types.BMesh, *, col=None, materials=(), free: bool = True) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    if free:
        bm.free()
    me.update()
    for m in materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    return link(ob, col)


def box(name: str, size: Sequence[float], origin: Sequence[float] = (0, 0, 0), *, col=None, material=None, anchor: str = "bottom") -> bpy.types.Object:
    """Axis-aligned box. anchor 'bottom' puts origin at the base centre, 'center' at the centroid."""
    sx, sy, sz = size
    ox, oy, oz = origin
    z0 = oz if anchor == "bottom" else oz - sz / 2
    verts = [(ox - sx / 2, oy - sy / 2, z0), (ox + sx / 2, oy - sy / 2, z0), (ox + sx / 2, oy + sy / 2, z0), (ox - sx / 2, oy + sy / 2, z0),
             (ox - sx / 2, oy - sy / 2, z0 + sz), (ox + sx / 2, oy - sy / 2, z0 + sz), (ox + sx / 2, oy + sy / 2, z0 + sz), (ox - sx / 2, oy + sy / 2, z0 + sz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh_object(name, verts, faces, col=col, materials=[material] if material else ())


def cylinder(name: str, radius: float, height: float, segments: int = 24, origin=(0, 0, 0), *, col=None, material=None, cap: bool = True) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=height)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((origin[0], origin[1], origin[2] + height / 2)))
    return bmesh_to_object(name, bm, col=col, materials=[material] if material else ())


def extrude_polygon(name: str, ring: Sequence[Sequence[float]], z0: float, z1: float, holes: Sequence[Sequence[Sequence[float]]] = (), *,
                    col=None, material=None, cap_bottom: bool = True, uv_metres: bool = True) -> bpy.types.Object:
    """Prism from a 2-D ring (CCW) between z0 and z1, with optional holes; wall UVs in metres (u along wall, v up)."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    def add_wall_ring(pts):
        n = len(pts)
        vs0 = [bm.verts.new((p[0], p[1], z0)) for p in pts]
        vs1 = [bm.verts.new((p[0], p[1], z1)) for p in pts]
        u = 0.0
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))
            seg = math.dist(pts[i][:2], pts[j][:2])
            if uv_metres:
                for loop, (uu, vv) in zip(f.loops, ((u, 0.0), (u + seg, 0.0), (u + seg, z1 - z0), (u, z1 - z0))):
                    loop[uv_layer].uv = (uu, vv)
            u += seg
        return vs0, vs1

    outer0, outer1 = add_wall_ring(ring)
    hole_rings1 = []
    hole_rings0 = []
    for h in holes:
        h0, h1 = add_wall_ring(list(reversed(h)))  # holes wind CW so walls face inwards
        hole_rings1.append(h1)
        hole_rings0.append(h0)
    # caps via triangulation (earcut on the 2-D polygon)
    tris = triangulate_2d(ring, holes)
    all1 = outer1 + [v for hr in hole_rings1 for v in reversed(hr)]
    all0 = outer0 + [v for hr in hole_rings0 for v in reversed(hr)]
    for a, b, c in tris:
        try:
            bm.faces.new((all1[a], all1[b], all1[c]))
            if cap_bottom:
                bm.faces.new((all0[c], all0[b], all0[a]))
        except ValueError:
            pass  # degenerate duplicate face
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bmesh_to_object(name, bm, col=col, materials=[material] if material else ())


def triangulate_2d(ring: Sequence[Sequence[float]], holes: Sequence[Sequence[Sequence[float]]] = ()) -> list[tuple[int, int, int]]:
    """Ear-clipping triangulation via mapbox_earcut (indices into ring + holes concatenated, holes in given order)."""
    import numpy as np
    try:
        import mapbox_earcut as earcut
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("mapbox_earcut is required (pip install mapbox_earcut)") from e
    pts = [tuple(p[:2]) for p in ring]
    rings = [len(pts)]
    for h in holes:
        pts.extend(tuple(p[:2]) for p in h)
        rings.append(len(pts))
    arr = np.asarray(pts, dtype=np.float64)
    idx = earcut.triangulate_float64(arr, np.asarray(rings, dtype=np.uint32))
    return [tuple(int(i) for i in idx[k:k + 3]) for k in range(0, len(idx), 3)]


# --------------------------------------------------------------------------- materials
def pbr_material(name: str, *, base_color=(0.8, 0.8, 0.8, 1.0), roughness: float = 0.6, metallic: float = 0.0,
                 textures: dict[str, str] | None = None, uv_scale_m: float = 1.0, normal_strength: float = 1.0,
                 emission=None, emission_strength: float = 0.0, alpha: float = 1.0) -> bpy.types.Material:
    """Principled BSDF material. ``textures`` maps 'color'|'roughness'|'normal'|'metallic'|'ao'|'displacement' -> image path.
    UVs are in metres; ``uv_scale_m`` is the physical size (m) one texture tile covers."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    if textures:
        mapping = nt.nodes.new("ShaderNodeMapping")
        texco = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(texco.outputs["UV"], mapping.inputs["Vector"])
        s = 1.0 / uv_scale_m
        mapping.inputs["Scale"].default_value = (s, s, s)
        for kind, path in textures.items():
            if not path or not os.path.exists(path):
                raise FileNotFoundError(f"texture missing for {name}/{kind}: {path}")
            img = bpy.data.images.load(path, check_existing=True)
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            tex.interpolation = "Linear"
            nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
            if kind == "color":
                img.colorspace_settings.name = "sRGB"
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            else:
                img.colorspace_settings.name = "Non-Color"
                if kind == "roughness":
                    nt.links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])
                elif kind == "metallic":
                    nt.links.new(tex.outputs["Color"], bsdf.inputs["Metallic"])
                elif kind == "normal":
                    nm = nt.nodes.new("ShaderNodeNormalMap")
                    nm.inputs["Strength"].default_value = normal_strength
                    nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
                    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
                elif kind == "ao":
                    pass  # baked into color at export for glTF; kept for Cycles preview via mix if needed
                elif kind == "displacement":
                    pass  # glTF has no displacement; used only for Cycles verification renders
    return mat


# --------------------------------------------------------------------------- export
def export_glb(path: str | Path, *, objects: Sequence[bpy.types.Object] | None = None, extras: dict | None = None,
               draco: bool = False, apply_modifiers: bool = True, export_animations: bool = False, texcoords: bool = True,
               tangents: bool = False, export_extras: bool = True, export_attributes: bool = False,
               export_normals: bool = True) -> Path:
    """Export selected (or all) objects to .glb with NYCSim asset extras (DATA_CONTRACTS §13).

    ``export_attributes`` carries custom mesh attributes into the file; the building shell stage needs
    it to ship per-building values such as ``bin`` and ``facade_class`` alongside the geometry. Note
    that glTF stores attributes as float32, so an integer wider than 24 bits must be split across two
    attributes by the caller. Custom attribute names must begin with an underscore and be upper case
    (``_BIN``, ``_FACADE_CLASS``) — that is the glTF convention for application-specific attributes,
    and Blender's exporter silently drops any custom attribute that does not follow it. ``export_normals`` is exposed so a stage that computes its own normals
    can turn Blender's off.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    meta = {"schema_version": SCHEMA_VERSION, "generator_script": os.path.basename(sys.argv[0]) if sys.argv else "", "git_commit": git_commit(),
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "units": "metres", "up_axis_blender": "Z"}
    if extras:
        meta.update(extras)
    sc["nycsim"] = json.dumps(meta)
    _pending_asset_extras.clear()
    _pending_asset_extras.update(meta)
    for o in bpy.data.objects:
        o.select_set(False)
    use_selection = objects is not None
    if use_selection:
        for o in objects:
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=use_selection, export_yup=True,
                              export_apply=apply_modifiers, export_texcoords=texcoords, export_normals=export_normals,
                              export_tangents=tangents, export_attributes=export_attributes,
                              export_materials="EXPORT", export_image_format="AUTO", export_draco_mesh_compression_enable=draco,
                              export_animations=export_animations, export_extras=export_extras, export_skins=export_animations,
                              export_morph=export_animations)
    if not path.exists() or path.stat().st_size < 100:
        raise RuntimeError(f"glTF export failed: {path}")
    _stamp_asset_extras(path, meta)
    return path


_pending_asset_extras: dict = {}


def _stamp_asset_extras(path: Path, meta: dict) -> None:
    """Write the NYCSim metadata into the file's ``asset.extras`` block (DATA_CONTRACTS §13).

    Blender's exporter puts scene custom properties on the scene node, not on ``asset``. Consumers
    read ``asset.extras.nycsim``, so the JSON chunk is patched in place after export. A failure here
    is logged and tolerated: the geometry is already valid and the scene-level copy still carries the
    same values.
    """
    import struct
    try:
        raw = path.read_bytes()
        magic, _version, _length = struct.unpack("<4sII", raw[:12])
        if magic != b"glTF":
            return
        off = 12
        json_off = json_len = None
        while off + 8 <= len(raw):
            clen, ctype = struct.unpack("<I4s", raw[off:off + 8])
            if ctype == b"JSON":
                json_off, json_len = off + 8, clen
                break
            off += 8 + clen + ((4 - clen % 4) % 4)
        if json_off is None:
            return
        doc = json.loads(raw[json_off:json_off + json_len].decode("utf-8"))
        doc.setdefault("asset", {}).setdefault("extras", {})["nycsim"] = meta
        new_json = json.dumps(doc, separators=(",", ":")).encode("utf-8")
        new_json += b" " * ((4 - len(new_json) % 4) % 4)
        out = bytearray(raw[:json_off - 8])
        out += struct.pack("<I4s", len(new_json), b"JSON") + new_json
        out += raw[json_off + json_len + ((4 - json_len % 4) % 4):]
        struct.pack_into("<I", out, 8, len(out))
        path.write_bytes(bytes(out))
    except Exception as e:  # noqa: BLE001 — metadata stamping must never lose valid geometry
        import logging
        logging.getLogger("nycsim.bpy").warning("could not stamp asset.extras on %s: %s", path, e)


def write_catalog_entry(catalog_dir: str | Path, entry: dict) -> Path:
    """Each generated asset writes its own JSON (no shared-file races); catalogs are merged by blender/common/merge_catalog.py."""
    catalog_dir = Path(catalog_dir)
    catalog_dir.mkdir(parents=True, exist_ok=True)
    p = catalog_dir / f"{entry['id']}.json"
    with open(p, "w") as f:
        json.dump(entry, f, indent=1, sort_keys=True)
    return p


def bounds_of(objects: Sequence[bpy.types.Object]) -> dict:
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for o in objects:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return {"min": list(lo), "max": list(hi)}


# --------------------------------------------------------------------------- rendering (verification)
def quick_render(path: str | Path, *, camera_location, camera_target, fov_deg: float = 60.0, size=(1280, 720), samples: int = 64,
                 sun_azimuth_deg: float = 220.0, sun_elevation_deg: float = 35.0, sun_strength: float = 4.0, sky: bool = True,
                 engine: str = "CYCLES") -> Path:
    """Cycles CPU still for verification sheets. Camera looks from location towards target."""
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("verify_cam")
    cam.lens_unit = "FOV"
    cam.angle = math.radians(fov_deg)
    cam.clip_end = 60000.0
    camob = bpy.data.objects.new("verify_cam", cam)
    link(camob)
    camob.location = Vector(camera_location)
    direction = Vector(camera_target) - camob.location
    camob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    sc.camera = camob
    sun = bpy.data.lights.new("verify_sun", "SUN")
    sun.energy = sun_strength
    sun.angle = math.radians(0.53)
    sunob = bpy.data.objects.new("verify_sun", sun)
    link(sunob)
    sunob.rotation_euler = (math.radians(90 - sun_elevation_deg), 0.0, math.radians(-sun_azimuth_deg))
    if sky:
        world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
        sc.world = world
        world.use_nodes = True
        nt = world.node_tree
        bg = nt.nodes.get("Background")
        skytex = nt.nodes.new("ShaderNodeTexSky")
        skytex.sky_type = "NISHITA"
        skytex.sun_elevation = math.radians(sun_elevation_deg)
        skytex.sun_rotation = math.radians(sun_azimuth_deg)
        skytex.sun_intensity = 0.0
        nt.links.new(skytex.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.6
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return Path(path)
