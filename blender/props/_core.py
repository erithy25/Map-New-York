"""Shared machinery for the NYCSim street-prop generators (stage 4 assets).

Conventions (docs/DATA_CONTRACTS.md §13 + this stage):
* Blender: metres, Z-up, **origin = ground-contact point**, **+Y = facing direction** (the side a pedestrian on the
  sidewalk sees; lenses/sign faces/screens have their normals along +Y).  glTF export is Y-up, so in the .glb the
  facing axis is −Z and up is +Y (the exporter's (X, Y, Z) → (X, Z, −Y)).
* One glb per prop id.  Node ``LOD0`` holds the full mesh; node ``LOD1`` (decimated mesh or billboard cross) is
  referenced from LOD0 via the ``MSFT_lod`` extension and is *not* in the scene's root node list, so viewers
  without MSFT_lod support show only LOD0.
* Material slot names that are part of the runtime contract: ``SIGN_FACE`` (runtime-rendered texture, UV 0..1 covers
  the face exactly, u increases to the reader's right, v upwards), ``LAMP_EMISSIVE`` (night light source),
  ``LIGHT_CONE`` (alpha light-cone planes), ``SCREEN_EMISSIVE`` (LinkNYC / ad panels), ``MTA_<line>`` (bullets).
"""
from __future__ import annotations

import json
import logging
import math
import os
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[0] / "common"))
sys.path.insert(0, str(_HERE))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import nycsim_bpy as nb  # noqa: E402

log = logging.getLogger("nycsim.props")

PROPS_OUT = nb.BLENDER_OUT / "props"
CATALOG_DIR = PROPS_OUT / "catalog"
TEX_OUT = PROPS_OUT / "textures"           # procedurally generated PNGs (leaf atlases, sign legends, gradients)
FONT_DIR = nb.ASSETS / "fonts" / "Overpass"
FONT_BOLD = FONT_DIR / "overpass-bold.otf"
FONT_SEMIBOLD = FONT_DIR / "overpass-semibold.otf"
TAU = 2.0 * math.pi
# Embedded texture resolution: 1K for hard-surface props (texel density >= 2 px/mm on a 0.5 m tile), 2K for tree bark.
PROP_TEX_RES = os.environ.get("NYCSIM_PROPS_TEX_RES", "1K")
BARK_TEX_RES = os.environ.get("NYCSIM_BARK_TEX_RES", "2K")
# Every prop glb embeds its own copy of each texture, so the source 1K/2K JPEGs (0.7-8 MB each) are re-encoded
# once into a shared cache at the pixel size a hand-held-scale object actually needs.
PROP_TEX_PX = int(os.environ.get("NYCSIM_PROPS_TEX_PX", "512"))
BARK_TEX_PX = int(os.environ.get("NYCSIM_BARK_TEX_PX", "1024"))
TEX_RESIZED = TEX_OUT / "resized"

# ----------------------------------------------------------------------------- texture provider (shared -> fallback)
_TEX_SOURCE = "unresolved"


def texture_set(name: str, resolution: str = "2K") -> dict[str, str]:
    """Texture maps by kind. Prefers the shared ``blender/common/textures.py``; falls back to this lane's fetcher (same disk layout)."""
    global _TEX_SOURCE
    import _textures_fallback as fb
    asset_id = fb.resolve_asset_id(name)
    try:
        import textures as shared  # blender/common/textures.py
        maps = shared.get_texture_set(asset_id, resolution)
        _TEX_SOURCE = "blender/common/textures.py"
        return maps
    except ImportError:
        pass
    except Exception as e:  # shared helper present but cannot serve (e.g. its catalog file is absent) -> fallback, same layout
        log.debug("shared texture helper declined %s (%s); using fallback", asset_id, e)
    maps = fb.get_texture_set(asset_id, resolution)
    _TEX_SOURCE = "blender/props/_textures_fallback.py"
    return maps


def texture_source() -> str:
    return _TEX_SOURCE


def _resized_map(src: str, max_px: int) -> str:
    """Cache a max_px-wide JPEG copy of one PBR map next to the generated prop textures. Idempotent."""
    from PIL import Image
    src_p = Path(src)
    asset = src_p.parent.name
    out = TEX_RESIZED / f"{asset}_{max_px}_{src_p.stem.split('_')[-1]}.jpg"
    if out.exists() and out.stat().st_mtime >= src_p.stat().st_mtime:
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_p) as im:
        im = im.convert("RGB")
        if max(im.size) > max_px:
            w, h = im.size
            f = max_px / float(max(w, h))
            im = im.resize((max(1, round(w * f)), max(1, round(h * f))), Image.LANCZOS)
        tmp = out.with_suffix(".tmp.jpg")
        im.save(tmp, "JPEG", quality=88, optimize=True, subsampling=1)
    os.replace(tmp, out)
    return str(out)


def texture_set_small(name: str, max_px: int, resolution: str = PROP_TEX_RES) -> dict[str, str]:
    """Texture maps for ``name`` re-encoded to at most ``max_px`` on the long edge (see PROP_TEX_PX)."""
    maps = texture_set(name, resolution)
    return {k: _resized_map(v, max_px) for k, v in maps.items() if k in ("color", "normal", "roughness", "metalness")}


def texture_license(name: str) -> dict:
    import _textures_fallback as fb
    aid = fb.resolve_asset_id(name)
    lic = fb.TEXTURE_ROOT / aid / "LICENSE.json"
    doc = json.loads(lic.read_text()) if lic.exists() else {}
    return {"asset_id": aid, "license": doc.get("license", "CC0 1.0"), "source_url": doc.get("source_url", f"https://ambientcg.com/view?id={aid}"),
            "sha256": doc.get("sha256")}


# ----------------------------------------------------------------------------- colours (linear RGB)
def srgb(hexstr: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """'#RRGGBB' (sRGB) -> linear RGBA tuple for Blender material sockets."""
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [(v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return (lin[0], lin[1], lin[2], alpha)


# MTA subway line bullet colours (official MTA brand guidelines, sRGB hex)
MTA_LINE_COLORS: dict[str, str] = {
    **{k: "#EE352E" for k in "123"}, **{k: "#00933C" for k in "456"}, "7": "#B933AD",
    **{k: "#0039A6" for k in "ACE"}, **{k: "#FF6319" for k in "BDFM"}, "G": "#6CBE45",
    **{k: "#996633" for k in "JZ"}, "L": "#A7A9AC", **{k: "#FCCC0A" for k in "NQRW"}, "S": "#808183",
}
MTA_DARK_TEXT_LINES = set("NQRW")  # yellow bullets carry black glyphs; all others white

# MUTCD sign colours (FHWA Standard Highway Signs colour specs; Pantone -> sRGB approximations)
MUTCD = {"red": "#B01C2E", "green": "#006B54", "yellow": "#FFCD00", "orange": "#E87722", "blue": "#003F87",
         "brown": "#603311", "white": "#F2F2F2", "black": "#111111", "fluor_yellow_green": "#CCFF00"}
# NYC agency paints
NYC_SIGNAL_GREEN = "#173B2A"      # NYC DOT dark-green signal housings
NYC_PARKS_GREEN = "#2D5B3D"       # DOT/Parks green (litter baskets, park benches, tree guards)
MTA_RAILING_GREEN = "#0E4D35"     # subway entrance railings and sign frames
GALV = "#9CA0A3"
USPS_BLUE = "#004B87"
FDNY_RED = "#C8102E"
DOT_ORANGE = "#F26522"


# ----------------------------------------------------------------------------- materials
def mat_solid(name: str, hexcolor: str, roughness: float = 0.55, metallic: float = 0.0, *, alpha: float = 1.0,
              emission: str | None = None, emission_strength: float = 0.0) -> bpy.types.Material:
    return nb.pbr_material(name, base_color=srgb(hexcolor), roughness=roughness, metallic=metallic, alpha=alpha,
                           emission=srgb(emission) if emission else None, emission_strength=emission_strength)


def mat_emissive(name: str, hexcolor: str, strength: float = 8.0, base: str | None = None) -> bpy.types.Material:
    """Self-lit material (lamps, screens, LED lenses). glTF gets KHR_materials_emissive_strength via Blender's exporter."""
    return nb.pbr_material(name, base_color=srgb(base or hexcolor), roughness=0.4, emission=srgb(hexcolor), emission_strength=strength)


def mat_glass(name: str = "glass_clear", tint: str = "#DDEEF5", alpha: float = 0.25) -> bpy.types.Material:
    m = nb.pbr_material(name, base_color=srgb(tint, alpha), roughness=0.05, metallic=0.0, alpha=alpha)
    return m


def mat_textured(name: str, texname: str, uv_scale_m: float, *, tint: str | None = None, roughness: float = 0.6, metallic: float = 0.0,
                 use_roughness_map: bool = False, normal_strength: float = 1.0, resolution: str | None = None,
                 max_px: int | None = None) -> bpy.types.Material:
    """PBR material from an AmbientCG set: colour + normal (JPG kept as-is in the glb); roughness constant unless asked.
    ``tint`` multiplies the albedo (used to differentiate species sharing a bark set)."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    src = texture_set(texname, resolution or PROP_TEX_RES)
    asset_dir = src["color"].split(os.sep)[-2]
    maps = texture_set_small(texname, max_px or PROP_TEX_PX, resolution or PROP_TEX_RES)
    textures = {"color": maps["color"]}
    if "normal" in maps:
        textures["normal"] = maps["normal"]
    if use_roughness_map and "roughness" in maps:
        textures["roughness"] = maps["roughness"]
    m = nb.pbr_material(name, roughness=roughness, metallic=metallic, textures=textures, uv_scale_m=uv_scale_m, normal_strength=normal_strength)
    m["nycsim_texture_asset"] = asset_dir
    if tint:
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        link = next((l for l in nt.links if l.to_node == bsdf and l.to_socket.name == "Base Color"), None)
        if link is not None:
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            mix.inputs[7].default_value = srgb(tint)  # B (RGBA)
            nt.links.new(link.from_socket, mix.inputs[6])  # A
            nt.links.remove(link)
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return m


def mat_image(name: str, image_path: str | Path, *, roughness: float = 0.5, metallic: float = 0.0, alpha_clip: bool = False,
              alpha_blend: bool = False, emission_strength: float = 0.0, emission_from_image: bool = False, backface: bool = True,
              specular: float | None = None) -> bpy.types.Material:
    """Material driven by one RGBA image mapped straight through UV 0..1 (sign legends, leaf cards, light cones, screens)."""
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    image_path = str(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if specular is not None:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    img = bpy.data.images.load(image_path, check_existing=True)
    img.colorspace_settings.name = "sRGB"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha_clip or alpha_blend:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        m.blend_method = "CLIP" if alpha_clip else "BLEND"
        m.surface_render_method = "DITHERED" if alpha_clip else "BLENDED"
        m.use_backface_culling = not backface
    if emission_strength > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return m


def mat_sign_face(default_image: str | Path | None) -> bpy.types.Material:
    """The runtime-swappable sign face. Named exactly SIGN_FACE (contract); default legend baked for verification renders."""
    if default_image is None:
        return nb.pbr_material("SIGN_FACE", base_color=srgb(MUTCD["white"]), roughness=0.35)
    return mat_image("SIGN_FACE", default_image, roughness=0.35, specular=0.6)


# ----------------------------------------------------------------------------- bmesh helpers
def _new_bm() -> tuple[bmesh.types.BMesh, bmesh.types.BMLayerItem]:
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    return bm, uv


def cube_project_uv(bm: bmesh.types.BMesh, uv_layer, faces=None, scale: float = 1.0) -> None:
    """Box-projection UVs in metres (for anything textured with a tiling material that is not a lathe/tube)."""
    for f in (faces if faces is not None else bm.faces):
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            co = loop.vert.co
            if ax == 0:
                uv = (co.y * (1 if n.x > 0 else -1), co.z)
            elif ax == 1:
                uv = (co.x * (-1 if n.y > 0 else 1), co.z)
            else:
                uv = (co.x, co.y * (1 if n.z > 0 else -1))
            loop[uv_layer].uv = (uv[0] * scale, uv[1] * scale)


def bm_object(name: str, bm: bmesh.types.BMesh, materials: Sequence[bpy.types.Material] = (), *, smooth: bool = False,
              col=None) -> bpy.types.Object:
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    ob = nb.bmesh_to_object(name, bm, col=col, materials=materials)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def box(name: str, size: Sequence[float], origin: Sequence[float] = (0, 0, 0), *, material=None, anchor: str = "bottom",
        uv_scale: float = 1.0, bevel: float = 0.0) -> bpy.types.Object:
    """Axis-aligned box with cube-projected metre UVs. ``bevel`` > 0 adds a bevel modifier (applied at export)."""
    sx, sy, sz = size
    ox, oy, oz = origin
    z0 = oz if anchor == "bottom" else oz - sz / 2
    bm, uv = _new_bm()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector((ox, oy, z0 + sz / 2)), verts=bm.verts)
    bm.normal_update()
    cube_project_uv(bm, uv, scale=uv_scale)
    ob = bm_object(name, bm, [material] if material else ())
    if bevel > 0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return ob


def lathe(name: str, profile: Sequence[Sequence[float]], segments: int = 24, *, material=None, origin=(0, 0, 0), uv_tile_m: float = 1.0,
          smooth: bool = True, axis: str = "Z", cap: bool = True) -> bpy.types.Object:
    """Surface of revolution from a (radius, height) profile; radius 0 collapses to a pole vertex.
    UV: u = angle → metres around the largest circumference (rounded to whole tiles), v = arc length in metres."""
    bm, uv = _new_bm()
    rings: list[list[bmesh.types.BMVert] | bmesh.types.BMVert] = []
    circ = max(TAU * max(r for r, _ in profile), 1e-6)
    wraps = max(1, round(circ / uv_tile_m))
    vlen = [0.0]
    for i in range(1, len(profile)):
        vlen.append(vlen[-1] + math.dist(profile[i], profile[i - 1]))
    for (r, h) in profile:
        if r <= 1e-6:
            rings.append(bm.verts.new((0.0, 0.0, h)))
        else:
            rings.append([bm.verts.new((r * math.cos(TAU * k / segments), r * math.sin(TAU * k / segments), h)) for k in range(segments)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(segments):
            k2 = (k + 1) % segments
            u0, u1 = k / segments * wraps * uv_tile_m, (k + 1) / segments * wraps * uv_tile_m
            if isinstance(a, list) and isinstance(b, list):
                f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
                uvs = ((u0, vlen[i]), (u1, vlen[i]), (u1, vlen[i + 1]), (u0, vlen[i + 1]))
            elif isinstance(a, list):
                f = bm.faces.new((a[k], a[k2], b))
                uvs = ((u0, vlen[i]), (u1, vlen[i]), ((u0 + u1) / 2, vlen[i + 1]))
            elif isinstance(b, list):
                f = bm.faces.new((a, b[k2], b[k]))
                uvs = (((u0 + u1) / 2, vlen[i]), (u1, vlen[i + 1]), (u0, vlen[i + 1]))
            else:
                continue
            for loop, t in zip(f.loops, uvs):
                loop[uv_layer_of(bm)].uv = t
    if cap:
        for ring, up in ((rings[0], False), (rings[-1], True)):
            if isinstance(ring, list):
                f = bm.faces.new(ring if up else list(reversed(ring)))
                for loop in f.loops:
                    loop[uv_layer_of(bm)].uv = (loop.vert.co.x, loop.vert.co.y)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if axis != "Z":
        rot = {"X": Matrix.Rotation(math.radians(90), 4, "Y"), "Y": Matrix.Rotation(math.radians(-90), 4, "X"),
               "-Y": Matrix.Rotation(math.radians(90), 4, "X"), "-X": Matrix.Rotation(math.radians(-90), 4, "Y")}[axis]
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(origin), verts=bm.verts)
    return bm_object(name, bm, [material] if material else (), smooth=smooth)


def uv_layer_of(bm):
    return bm.loops.layers.uv.active or bm.loops.layers.uv[0]


def cyl(name: str, radius: float, height: float, segments: int = 16, origin=(0, 0, 0), *, material=None, axis: str = "Z", r_top=None,
        uv_tile_m: float = 1.0, smooth: bool = True) -> bpy.types.Object:
    """Cylinder/cone along ``axis`` starting at ``origin`` (base) — a lathe convenience."""
    rt = radius if r_top is None else r_top
    return lathe(name, [(radius, 0.0), (rt, height)], segments, material=material, origin=origin, uv_tile_m=uv_tile_m, smooth=smooth, axis=axis)


def _frames(points: Sequence[Vector]) -> list[tuple[Vector, Vector, Vector]]:
    """Parallel-transport frames (tangent, normal, binormal) along a polyline — no twisting between rings."""
    n = len(points)
    tangents = []
    for i in range(n):
        if i == 0:
            t = points[1] - points[0]
        elif i == n - 1:
            t = points[-1] - points[-2]
        else:
            t = (points[i + 1] - points[i]).normalized() + (points[i] - points[i - 1]).normalized()
        tangents.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    t0 = tangents[0]
    ref = Vector((1, 0, 0)) if abs(t0.x) < 0.9 else Vector((0, 1, 0))
    nrm = (ref - t0 * ref.dot(t0)).normalized()
    frames = []
    for i, t in enumerate(tangents):
        if i > 0:
            prev = tangents[i - 1]
            axis = prev.cross(t)
            if axis.length > 1e-9:
                ang = math.acos(max(-1.0, min(1.0, prev.dot(t))))
                nrm = Matrix.Rotation(ang, 3, axis.normalized()) @ nrm
            nrm = (nrm - t * nrm.dot(t)).normalized()
        frames.append((t, nrm, t.cross(nrm)))
    return frames


def tube_into_bm(bm, uv_layer, points: Sequence[Sequence[float]], radii: Sequence[float] | float, segments: int, mat_index: int = 0,
                 uv_tile_m: float = 1.0, cap_start: bool = False, cap_end: bool = True, v0: float = 0.0) -> float:
    """Sweep a circle along a polyline into an existing bmesh. Returns the running v (arc length) at the end."""
    pts = [Vector(p) for p in points]
    if len(pts) < 2:
        raise ValueError("tube needs >= 2 points")
    if isinstance(radii, (int, float)):
        radii = [float(radii)] * len(pts)
    if len(radii) != len(pts):
        raise ValueError("radii length must match points")
    frames = _frames(pts)
    circ = max(TAU * max(radii), 1e-6)
    wraps = max(1, round(circ / uv_tile_m))
    rings = []
    v = v0
    vs = []
    for i, (p, r, (t, nrm, bn)) in enumerate(zip(pts, radii, frames)):
        if i > 0:
            v += (pts[i] - pts[i - 1]).length
        vs.append(v)
        if r <= 1e-6:
            rings.append(bm.verts.new(p))
        else:
            rings.append([bm.verts.new(p + (nrm * math.cos(TAU * k / segments) + bn * math.sin(TAU * k / segments)) * r) for k in range(segments)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(segments):
            k2 = (k + 1) % segments
            u0, u1 = k / segments * wraps * uv_tile_m, (k + 1) / segments * wraps * uv_tile_m
            if isinstance(a, list) and isinstance(b, list):
                f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
                uvs = ((u0, vs[i]), (u1, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1]))
            elif isinstance(a, list):
                f = bm.faces.new((a[k], a[k2], b))
                uvs = ((u0, vs[i]), (u1, vs[i]), ((u0 + u1) / 2, vs[i + 1]))
            elif isinstance(b, list):
                f = bm.faces.new((a, b[k2], b[k]))
                uvs = (((u0 + u1) / 2, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1]))
            else:
                continue
            f.material_index = mat_index
            f.smooth = True
            for loop, tuv in zip(f.loops, uvs):
                loop[uv_layer].uv = tuv
    if cap_start and isinstance(rings[0], list):
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mat_index
    if cap_end and isinstance(rings[-1], list):
        f = bm.faces.new(rings[-1])
        f.material_index = mat_index
    return v


def tube(name: str, points: Sequence[Sequence[float]], radii: Sequence[float] | float, segments: int = 12, *, material=None,
         uv_tile_m: float = 1.0, cap_start: bool = True, cap_end: bool = True) -> bpy.types.Object:
    bm, uv = _new_bm()
    tube_into_bm(bm, uv, points, radii, segments, 0, uv_tile_m, cap_start, cap_end)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_object(name, bm, [material] if material else (), smooth=True)


def torus(name: str, major_r: float, minor_r: float, segments: int = 24, minor_segments: int = 8, origin=(0, 0, 0), *, material=None,
          axis: str = "Z", arc: float = TAU) -> bpy.types.Object:
    """(Partial) torus — hoops, bike racks, hand rails. ``arc`` in radians (TAU = closed ring)."""
    n = segments if arc >= TAU - 1e-6 else segments + 1
    pts = [(major_r * math.cos(arc * k / segments), major_r * math.sin(arc * k / segments), 0.0) for k in range(n)]
    if arc >= TAU - 1e-6:
        pts.append(pts[0])
    bm, uv = _new_bm()
    tube_into_bm(bm, uv, pts, minor_r, minor_segments, 0, 1.0, arc < TAU - 1e-6, arc < TAU - 1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if axis == "Y":
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(90), 4, "X"), verts=bm.verts)
    elif axis == "X":
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(90), 4, "Y"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(origin), verts=bm.verts)
    return bm_object(name, bm, [material] if material else (), smooth=True)


def prism(name: str, ring_xy: Sequence[Sequence[float]], z0: float, z1: float, *, material=None, origin=(0, 0, 0), uv_scale: float = 1.0,
          axis: str = "Z") -> bpy.types.Object:
    """Extruded 2-D polygon (CCW) with cube-projected UVs; ``axis`` 'Y' lays the profile in the XZ plane extruded along Y."""
    bm, uv = _new_bm()
    tris = nb.triangulate_2d(ring_xy)
    v0 = [bm.verts.new((x, y, z0)) for x, y in ring_xy]
    v1 = [bm.verts.new((x, y, z1)) for x, y in ring_xy]
    n = len(ring_xy)
    for i in range(n):
        bm.faces.new((v0[i], v0[(i + 1) % n], v1[(i + 1) % n], v1[i]))
    for a, b, c in tris:
        try:
            bm.faces.new((v1[a], v1[b], v1[c]))
            bm.faces.new((v0[c], v0[b], v0[a]))
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if axis == "Y":  # profile (x, z) extruded along +Y: rotate so local z -> -y ... i.e. (x, y, z) -> (x, -z, y)
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(90), 4, "X"), verts=bm.verts)
    elif axis == "X":
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.radians(-90), 4, "Y"), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(origin), verts=bm.verts)
    bm.normal_update()
    cube_project_uv(bm, uv, scale=uv_scale)
    return bm_object(name, bm, [material] if material else ())


def sweep(name: str, section_xy: Sequence[Sequence[float]], stations: Sequence[Sequence[float]], *, material=None,
          origin=(0.0, 0.0, 0.0), cap_start: bool = True, cap_end: bool = True, uv_scale: float = 1.0,
          smooth: bool = False, close: bool = True) -> bpy.types.Object:
    """Sweep a closed 2-D cross-section along +Z. ``stations`` are ``(z, scale)`` or ``(z, scale_x, scale_y)`` —
    tapered octagonal poles, fluted cast-iron shafts, U-channel posts, barrier profiles.
    UV: u = perimeter distance in metres at the widest station, v = z in metres."""
    bm, uv = _new_bm()
    sec = [tuple(p[:2]) for p in section_xy]
    n = len(sec)
    peri = [0.0]
    for i in range(1, n + 1):
        peri.append(peri[-1] + math.dist(sec[i % n], sec[i - 1]))
    rings = []
    for st in stations:
        z = st[0]
        sx = st[1]
        sy = st[2] if len(st) > 2 else st[1]
        rings.append([bm.verts.new((x * sx, y * sy, z)) for x, y in sec])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(n if close else n - 1):
            k2 = (k + 1) % n
            f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
            f.smooth = smooth
            for loop, t in zip(f.loops, ((peri[k], stations[i][0]), (peri[k + 1], stations[i][0]),
                                         (peri[k + 1], stations[i + 1][0]), (peri[k], stations[i + 1][0]))):
                loop[uv].uv = (t[0] * uv_scale, t[1] * uv_scale)
    tris = nb.triangulate_2d(sec)
    for ring, up in ((rings[0], False), (rings[-1], True)):
        if (up and not cap_end) or (not up and not cap_start):
            continue
        for a, b, c in tris:
            try:
                f = bm.faces.new((ring[a], ring[b], ring[c]) if up else (ring[c], ring[b], ring[a]))
            except ValueError:
                continue
            for loop in f.loops:
                loop[uv].uv = (loop.vert.co.x * uv_scale, loop.vert.co.y * uv_scale)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, vec=Vector(origin), verts=bm.verts)
    return bm_object(name, bm, [material] if material else ())


def fluted_section(radius: float, flutes: int = 16, depth: float = 0.10, per_flute: int = 4) -> list[tuple[float, float]]:
    """Cross-section of a classic fluted cast-iron shaft: ``flutes`` shallow concave grooves cut into a circle."""
    pts = []
    for i in range(flutes * per_flute):
        t = TAU * i / (flutes * per_flute)
        groove = math.sin(t * flutes) ** 2          # 0 at the fillet, 1 in the middle of a flute
        pts.append((radius * (1.0 - depth * groove) * math.cos(t), radius * (1.0 - depth * groove) * math.sin(t)))
    return pts


def octagon_section(across_flats: float) -> list[tuple[float, float]]:
    """NYC DOT street-light pole cross-section: regular octagon given its across-flats dimension."""
    r = across_flats / 2.0 / math.cos(math.pi / 8)
    return regular_polygon(8, r, math.pi / 8)


def u_channel_section(width: float = 0.070, depth: float = 0.038, web: float = 0.006) -> list[tuple[float, float]]:
    """Galvanised U-channel sign post (3 lb/ft: 2 3/4 in flange-to-flange, ~1 1/2 in deep), section in the XY plane."""
    w, d, t = width / 2.0, depth, web
    return [(-w, 0.0), (w, 0.0), (w - t * 0.7, d * 0.55), (w - t * 1.6, d), (-(w - t * 1.6), d), (-(w - t * 0.7), d * 0.55)]


def bezier_points(ctrl: Sequence[Sequence[float]], n: int = 16) -> list[tuple[float, float, float]]:
    """Uniform samples of a Bezier of any degree (de Casteljau) — davit arms, crook scrolls, bike frames."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        cur = [Vector(c) for c in ctrl]
        while len(cur) > 1:
            cur = [cur[j] * (1 - t) + cur[j + 1] * t for j in range(len(cur) - 1)]
        pts.append(tuple(cur[0]))
    return pts


def regular_polygon(n: int, radius: float, rotation: float = 0.0) -> list[tuple[float, float]]:
    return [(radius * math.cos(rotation + TAU * k / n), radius * math.sin(rotation + TAU * k / n)) for k in range(n)]


def sign_blank(name: str, shape: str, w: float, h: float, *, thickness: float = 0.002, face_material: bpy.types.Material,
               back_material: bpy.types.Material, center=(0.0, 0.0, 0.0), facing: str = "+Y",
               two_sided: bool = False) -> bpy.types.Object:
    """Flat sign blank whose front (+Y) face carries ``face_material`` with UV (0,0)-(1,1) spanning the face's bounding box
    exactly (u to the reader's right, v up). ``shape``: rect | octagon | triangle_down | diamond | pentagon | circle.
    ``center`` is the centre of the face; ``facing`` '+Y' (default) or '-Y' (second face of a two-sided assembly)."""
    if shape == "rect":
        ring = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    elif shape == "octagon":
        r = w / 2 / math.cos(math.pi / 8)
        ring = [(r * math.cos(math.pi / 8 + TAU * k / 8), r * math.sin(math.pi / 8 + TAU * k / 8)) for k in range(8)]
    elif shape == "triangle_down":  # yield: point down, side w, height h
        ring = [(0.0, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    elif shape == "diamond":
        ring = [(0.0, -h / 2), (w / 2, 0.0), (0.0, h / 2), (-w / 2, 0.0)]
    elif shape == "pentagon":  # school-crossing style: point up
        ring = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h * 0.1), (0.0, h / 2), (-w / 2, h * 0.1)]
    elif shape == "circle":
        ring = regular_polygon(32, w / 2)
    else:
        raise ValueError(f"unknown sign shape {shape}")
    # ring is (x_right, z_up) as read by the viewer; viewer's right is -X in world (viewer stands at +Y looking -Y)
    sgn = -1.0 if facing == "+Y" else 1.0
    bm, uv = _new_bm()
    yf, yb = (-thickness / 2, thickness / 2) if facing == "+Y" else (thickness / 2, -thickness / 2)
    front = [bm.verts.new((sgn * x, yf, z)) for x, z in ring]
    back = [bm.verts.new((sgn * x, yb, z)) for x, z in ring]
    n = len(ring)
    ff = bm.faces.new(front if facing == "-Y" else list(reversed(front)))
    ff.material_index = 0
    for loop in ff.loops:
        x = -sgn * loop.vert.co.x  # reader-space right
        z = loop.vert.co.z
        loop[uv].uv = ((x + w / 2) / w, (z + h / 2) / h)
    fb = bm.faces.new(back if facing == "+Y" else list(reversed(back)))
    fb.material_index = 0 if two_sided else 1
    for loop in fb.loops:
        # two-sided blades carry the same legend on both faces; the back is mirrored so it reads correctly from behind
        x = (sgn * loop.vert.co.x) if two_sided else loop.vert.co.x
        loop[uv].uv = ((x + w / 2) / w, (loop.vert.co.z + h / 2) / h)
    for i in range(n):
        f = bm.faces.new((front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]))
        f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # make sure the SIGN_FACE face points along `facing`
    want = Vector((0, 1, 0)) if facing == "+Y" else Vector((0, -1, 0))
    if ff.normal.dot(want) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    ob = bm_object(name, bm, [face_material, back_material])
    return ob


def text_mesh(name: str, text: str, size_m: float, *, material, depth: float = 0.003, font: Path | str = FONT_BOLD, align: str = "CENTER",
              center=(0.0, 0.0, 0.0), facing: str = "+Y", spacing: float = 1.0) -> bpy.types.Object:
    """3-D lettering (Overpass = open Highway Gothic derivative) as a mesh facing +Y with its baseline-centre at ``center``."""
    if not Path(font).exists():
        raise FileNotFoundError(f"font missing: {font}")
    cu = bpy.data.curves.new(name + "_curve", type="FONT")
    cu.body = text
    cu.font = bpy.data.fonts.load(str(font), check_existing=True)
    cu.size = size_m
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = depth / 2
    cu.space_character = spacing
    cu.resolution_u = 4
    tmp = bpy.data.objects.new(name + "_txt", cu)
    bpy.context.scene.collection.objects.link(tmp)
    dg = depsgraph()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    nb.link(ob)
    rot = Matrix.Rotation(math.radians(90), 4, "X")
    if facing == "+Y":
        rot = Matrix.Rotation(math.radians(180), 4, "Z") @ rot
    me.transform(rot)
    me.transform(Matrix.Translation(Vector(center)))
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    return ob


def light_cone(name: str, apex: Sequence[float], height: float, r_top: float, r_bottom: float, *, material) -> bpy.types.Object:
    """Two crossed vertical trapezoid planes fanning out below a luminaire; ``material`` is the LIGHT_CONE alpha gradient.
    UV: u across (0..1), v = 1 at the top (bright) → 0 at the bottom (transparent)."""
    ax, ay, az = apex
    bm, uv = _new_bm()
    for ang in (0.0, math.pi / 2):
        dx, dy = math.cos(ang), math.sin(ang)
        vs = [bm.verts.new((ax - dx * r_top, ay - dy * r_top, az)), bm.verts.new((ax + dx * r_top, ay + dy * r_top, az)),
              bm.verts.new((ax + dx * r_bottom, ay + dy * r_bottom, az - height)), bm.verts.new((ax - dx * r_bottom, ay - dy * r_bottom, az - height))]
        f = bm.faces.new(vs)
        for loop, t in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
            loop[uv].uv = t
    return bm_object(name, bm, [material])


def gradient_png(path: Path, size: int = 128) -> Path:
    """Radial-ish alpha gradient for LIGHT_CONE planes (bright at top, fading to zero at the bottom and at the sides)."""
    if path.exists():
        return path
    import numpy as np
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / (size - 1)
    v = 1.0 - ys                      # row 0 is the top of the image (= v 1 in Blender after flip) -> bright
    side = 1.0 - np.abs(xs - 0.5) * 2.0
    a = np.clip(v ** 1.6 * np.clip(side * 1.8, 0, 1) ** 0.8, 0, 1) * 0.55
    rgb = np.stack([np.full_like(a, 1.0), np.full_like(a, 0.93), np.full_like(a, 0.78), a], axis=-1)
    Image.fromarray((rgb * 255).astype(np.uint8), "RGBA").save(path)
    return path


def mat_light_cone() -> bpy.types.Material:
    png = gradient_png(TEX_OUT / "light_cone_gradient.png")
    m = mat_image("LIGHT_CONE", png, alpha_blend=True, emission_strength=3.0, roughness=1.0, specular=0.0)
    m.use_backface_culling = False
    m["nycsim_night_only"] = True
    return m


# ----------------------------------------------------------------------------- joining / transforms / LOD
def apply_transform(ob: bpy.types.Object) -> None:
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


def move(ob: bpy.types.Object, dx=0.0, dy=0.0, dz=0.0) -> bpy.types.Object:
    ob.data.transform(Matrix.Translation(Vector((dx, dy, dz))))
    return ob


def rotate(ob: bpy.types.Object, deg: float, axis: str = "Z", pivot=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    p = Vector(pivot)
    ob.data.transform(Matrix.Translation(p) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-p))
    return ob


def mirror_x(ob: bpy.types.Object) -> bpy.types.Object:
    ob.data.transform(Matrix.Scale(-1.0, 4, Vector((1, 0, 0))))
    ob.data.flip_normals()
    return ob


def duplicate(ob: bpy.types.Object, name: str) -> bpy.types.Object:
    me = ob.data.copy()
    me.name = name
    new = bpy.data.objects.new(name, me)
    new.matrix_world = ob.matrix_world.copy()
    for k in ob.keys():
        new[k] = ob[k]
    return nb.link(new)


def join(objects: Sequence[bpy.types.Object], name: str) -> bpy.types.Object:
    """Merge meshes into one object (materials de-duplicated by name, world transforms baked). Sources are removed."""
    objects = [o for o in objects if o is not None and o.type == "MESH"]
    if not objects:
        raise ValueError("join: nothing to join")
    dg = depsgraph()
    mats: list[bpy.types.Material] = []
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for ob in objects:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        remap = []
        # materials from the ORIGINAL datablock: evaluated meshes reference copy-on-write duplicates that dangle later
        for m in (ob.data.materials if len(ob.data.materials) else [None]):
            if m is None:
                remap.append(0)
                continue
            m = m.original if hasattr(m, "original") and m.original is not None else m
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        if not ob.data.materials:
            remap = [0]
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp_uv = tmp.loops.layers.uv.active
        bmesh.ops.transform(tmp, matrix=ob.matrix_world, verts=tmp.verts)
        offset = len(bm.verts)
        for v in tmp.verts:
            bm.verts.new(v.co)
        bm.verts.ensure_lookup_table()
        for f in tmp.faces:
            try:
                nf = bm.faces.new([bm.verts[offset + v.index] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = remap[min(f.material_index, len(remap) - 1)]
            nf.smooth = f.smooth
            if tmp_uv is not None:
                for l_new, l_old in zip(nf.loops, f.loops):
                    l_new[uv].uv = l_old[tmp_uv].uv
        tmp.free()
        ev.to_mesh_clear()
    for ob in objects:
        me = ob.data
        bpy.data.objects.remove(ob)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    bm.normal_update()
    out = nb.bmesh_to_object(name, bm, materials=mats)
    return out


def depsgraph():
    """Fresh, non-stale depsgraph (objects may have been created/removed since the last evaluation)."""
    bpy.context.view_layer.update()
    return bpy.context.evaluated_depsgraph_get()


def bounds_excluding(objects: Sequence[bpy.types.Object], exclude_materials: Sequence[str] = ("LIGHT_CONE",)) -> dict:
    """World-space bounds of the real geometry: polygons whose material is a night-only effect (light cones) are
    ignored so a prop's recorded size is its physical size, not the size of the light pool it throws."""
    ex = set(exclude_materials)
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for ob in objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        skip = {i for i, m in enumerate(me.materials) if m and m.name in ex}
        for poly in me.polygons:
            if poly.material_index in skip:
                continue
            for vi in poly.vertices:
                w = ob.matrix_world @ me.vertices[vi].co
                for k in range(3):
                    lo[k] = min(lo[k], w[k])
                    hi[k] = max(hi[k], w[k])
    if not all(map(math.isfinite, lo)):
        return nb.bounds_of(objects)
    return {"min": lo, "max": hi}


def tri_count(objects: Iterable[bpy.types.Object]) -> int:
    dg = depsgraph()
    n = 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        me = ob.evaluated_get(dg).to_mesh()
        n += sum(len(p.vertices) - 2 for p in me.polygons)
        ob.evaluated_get(dg).to_mesh_clear()
    return n


def decimated_copy(ob: bpy.types.Object, ratio: float, name: str) -> bpy.types.Object:
    """LOD1 for hard-surface props: collapse-decimated copy (modifier applied by the exporter)."""
    lod = duplicate(ob, name)
    mod = lod.modifiers.new("lod1", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = max(0.02, min(1.0, ratio))
    mod.use_collapse_triangulate = True
    return lod


# ----------------------------------------------------------------------------- GLB post-processing (MSFT_lod)
def _read_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"not a GLB2 file: {path}")
    off = 12
    js, bin_chunk = None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        off += 8 + clen
    if js is None:
        raise ValueError(f"GLB without JSON chunk: {path}")
    return js, bin_chunk


def _write_glb(path: Path, js: dict, bin_chunk: bytes) -> None:
    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    bb = bin_chunk + b"\0" * ((4 - len(bin_chunk) % 4) % 4)
    total = 12 + 8 + len(jb) + (8 + len(bb) if bb else 0)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(jb), 0x4E4F534A))
        f.write(jb)
        if bb:
            f.write(struct.pack("<II", len(bb), 0x004E4942))
            f.write(bb)


def add_msft_lod(path: Path, coverage=(0.5, 0.03)) -> dict:
    """Wire node LOD1 into node LOD0's MSFT_lod extension and drop LOD1 from the scene roots. Returns node info."""
    js, bin_chunk = _read_glb(path)
    nodes = js.get("nodes", [])
    idx = {n.get("name"): i for i, n in enumerate(nodes)}
    if "LOD0" not in idx or "LOD1" not in idx:
        raise ValueError(f"{path}: expected nodes LOD0 and LOD1, have {sorted(k for k in idx if k)}")
    lod0, lod1 = idx["LOD0"], idx["LOD1"]
    nodes[lod0].setdefault("extensions", {})["MSFT_lod"] = {"ids": [lod1]}
    nodes[lod0].setdefault("extras", {})["MSFT_screencoverage"] = list(coverage)
    for sc in js.get("scenes", []):
        sc["nodes"] = [n for n in sc.get("nodes", []) if n != lod1]
    used = set(js.get("extensionsUsed", []))
    used.add("MSFT_lod")
    js["extensionsUsed"] = sorted(used)
    _write_glb(path, js, bin_chunk)
    return {"lod0_node": lod0, "lod1_node": lod1}


def glb_json(path: Path) -> dict:
    return _read_glb(Path(path))[0]


# ----------------------------------------------------------------------------- prop spec / registry
@dataclass
class PropSpec:
    id: str
    category: str                 # lighting | traffic | signs | furniture | construction | vegetation
    dataset_kind: str             # DATA_CONTRACTS §8 kind name (see build_props.KINDS)
    build: Callable[[], "Built"]
    nominal: tuple[float, float, float]   # (x extent, y extent, z height) in metres per the published/reference dimension
    notes: str                    # reference description used for the model (published dimension source)
    variants: list[str] = field(default_factory=list)   # sibling ids of the same family
    variant_of: str | None = None
    tags: list[str] = field(default_factory=list)
    tolerance: float = 0.12       # allowed relative deviation of the built bounds from nominal (tests)
    lod1_ratio: float = 0.3


@dataclass
class Built:
    lod0: list[bpy.types.Object]
    lod1: list[bpy.types.Object] | None = None     # None -> decimated copy of LOD0
    lod1_kind: str = "decimated"
    extra: dict = field(default_factory=dict)
    keep_separate: bool = False   # do not join LOD0 objects (bullets, kits)


def _parent_under(objs: Sequence[bpy.types.Object], name: str) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    nb.link(empty)
    for o in objs:
        o.parent = empty
    return empty


def build_and_export(spec: PropSpec, *, out_dir: Path = PROPS_OUT, catalog_dir: Path = CATALOG_DIR) -> dict:
    """Run one builder in a fresh scene, export ``<id>.glb`` with LOD0 + MSFT_lod LOD1, write the catalog entry."""
    t0 = time.time()
    nb.reset_scene()
    for cache in (bpy.data.materials, bpy.data.images, bpy.data.meshes):
        for it in list(cache):
            cache.remove(it)
    built = spec.build()
    lod0 = built.lod0 if built.keep_separate else [join(built.lod0, spec.id)]
    if built.lod1 is None:
        lod1 = [decimated_copy(o, spec.lod1_ratio, o.name + "_LOD1") for o in lod0]
    else:
        lod1 = built.lod1
    n0, n1 = tri_count(lod0), tri_count(lod1)
    bounds = bounds_excluding(lod0)
    bounds_all = nb.bounds_of(lod0)
    for o in lod0:
        o["nycsim_lod"] = 0
    for o in lod1:
        o["nycsim_lod"] = 1
    root0 = _parent_under(lod0, "LOD0")
    root1 = _parent_under(lod1, "LOD1")
    mats = sorted({m.name for o in lod0 for m in o.data.materials if m})
    tex_assets = sorted({str(m["nycsim_texture_asset"]) for o in lod0 for m in o.data.materials if m and "nycsim_texture_asset" in m})
    size = [bounds["max"][i] - bounds["min"][i] for i in range(3)]
    glb = out_dir / f"{spec.id}.glb"
    extras = {"prop_id": spec.id, "category": spec.category, "dataset_kind": spec.dataset_kind, "bounds": bounds,
              "anchor": {"origin": "ground_contact", "facing_blender": "+Y", "facing_gltf": "-Z"}}
    nb.export_glb(glb, objects=lod0 + lod1 + [root0, root1], extras=extras)
    add_msft_lod(glb)
    entry = {
        "id": spec.id, "category": spec.category, "dataset_kind": spec.dataset_kind, "glb": str(glb.relative_to(nb.BLENDER_OUT)),
        "bounds": bounds, "bounds_with_effects": bounds_all, "size_m": [round(s, 4) for s in size],
        "nominal_size_m": list(spec.nominal),
        "anchor": {"origin": "ground_contact", "up_blender": "+Z", "facing_blender": "+Y", "up_gltf": "+Y", "facing_gltf": "-Z"},
        "polycount": {"lod0_tris": n0, "lod1_tris": n1}, "lod1": True, "lod1_kind": built.lod1_kind,
        "variants": list(spec.variants), "variant_of": spec.variant_of, "tags": list(spec.tags),
        "materials": mats, "sign_face": "SIGN_FACE" in mats, "emissive": any(m in ("LAMP_EMISSIVE", "SCREEN_EMISSIVE") or m.startswith("LED_") for m in mats),
        "light_cone": "LIGHT_CONE" in mats, "notes": spec.notes, "textures": [texture_license(a) for a in tex_assets],
        "glb_bytes": glb.stat().st_size, "build_seconds": round(time.time() - t0, 2), "generator": "blender/props/build_props.py",
        "schema_version": 1,
    }
    entry.update(built.extra)
    nb.write_catalog_entry(catalog_dir, entry)
    log.info("%-32s tris %6d / %5d  size %s  %.1fs", spec.id, n0, n1, [round(s, 2) for s in size], time.time() - t0)
    return entry
