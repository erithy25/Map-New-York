"""Facade-kit library: geometry accumulator with metre UVs, PBR materials from ``textures.py``, LOD1 generation,
triangle counting, export and catalog entries.  Everything the piece modules need; no piece definitions here.

Conventions (docs/DATA_CONTRACTS.md §13 + kit brief):
* Blender Z-up metres.  Wall plane is the XZ plane at y = 0.  **+Y points into the building**; the street side is −Y.
* Wall pieces: origin at the bottom-centre of the piece on the wall plane (``anchor = "wall_bottom_centre"``).
* Free-standing roof / street pieces: origin at the bottom-centre of the footprint (``anchor = "ground_bottom_centre"``).
* UVs are in metres (u along the surface, v up); materials tile every ``physical_size_m`` through a Mapping node, which the
  glTF exporter writes as ``KHR_texture_transform``.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Callable, Iterable, Sequence

import bpy
import bmesh
from mathutils import Matrix, Vector

_HERE = Path(__file__).resolve().parent
_COMMON = _HERE.parents[1] / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))
import nycsim_bpy as nb  # noqa: E402
import textures as tx  # noqa: E402
import facade_params as fp  # noqa: E402

log = logging.getLogger("nycsim.kit.facade")

KIT_OUT = nb.BLENDER_OUT / "kit" / "facade"
CATALOG_DIR = nb.BLENDER_OUT / "kit" / "catalog"
GENERATED_TEX = nb.ASSETS / "textures" / "_generated_kit"
KIT_TEX_RES = 1024  # embedded texture resolution (px) — 1 mm/px at 1 m tiling
V3 = Vector

# --------------------------------------------------------------------------- registry
BUDGETS: dict[str, int] = {
    "window": 400, "window_accessory": 400, "door_entry": 3000, "cornice": 1200, "string_course": 200, "quoin": 300, "pilaster": 600,
    "trim": 200, "storefront": 6000, "storefront_interior": 6000, "fire_escape": 3000, "parapet": 200, "bulkhead": 800, "water_tower": 4000,
    "hvac": 1200, "antenna": 800, "billboard": 1500, "scaffold": 3000, "fence": 800, "vegetation": 1500,
}


class Piece:
    """A registered kit piece: id, category, nominal size, builder callable returning a ``Mesh``."""

    def __init__(self, pid: str, category: str, build: Callable[[], "Mesh"], *, nominal_size: Sequence[float], anchor: str,
                 description: str, variants: Sequence[str] = (), features: Sequence[str] = (), budget: int | None = None,
                 lod1: Callable[[], "Mesh"] | None = None, extra: dict | None = None):
        if category not in fp.KIT_CATEGORIES:
            raise ValueError(f"{pid}: unknown category {category}")
        self.id, self.category, self.build, self.lod1 = pid, category, build, lod1
        self.nominal_size = tuple(float(x) for x in nominal_size)
        self.anchor, self.description = anchor, description
        self.variants, self.features = list(variants), list(features)
        self.budget = budget if budget is not None else BUDGETS.get(category, 2000)
        self.extra = extra or {}


REGISTRY: dict[str, Piece] = {}


def register(pid: str, category: str, *, nominal_size, anchor: str = "wall_bottom_centre", description: str, variants=(), features=(),
             budget: int | None = None, lod1=None, extra=None):
    """Decorator registering a builder ``fn() -> Mesh`` as kit piece ``pid``."""
    def deco(fn):
        if pid in REGISTRY:
            raise ValueError(f"duplicate piece id {pid}")
        REGISTRY[pid] = Piece(pid, category, fn, nominal_size=nominal_size, anchor=anchor, description=description, variants=variants,
                              features=features, budget=budget, lod1=lod1, extra=extra)
        return fn
    return deco


# --------------------------------------------------------------------------- geometry accumulator
def _dominant_axis(n: Vector) -> int:
    ax = [abs(n.x), abs(n.y), abs(n.z)]
    return ax.index(max(ax))


def planar_uv(p: Vector, n: Vector) -> tuple[float, float]:
    """Metre UV from world position by the face's dominant normal axis (u along wall/x, v up)."""
    a = _dominant_axis(n)
    if a == 2:  # horizontal face: u = x, v = y
        return (p.x, p.y)
    if a == 1:  # faces the street / building: u = x, v = z
        return (p.x, p.z)
    return (p.y, p.z)  # faces ±x: u = y, v = z


class Mesh:
    """bmesh accumulator with named material slots and metre UVs."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mats: list[str] = []
        self.smooth_faces: list = []

    # -- materials
    def slot(self, name: str) -> int:
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    # -- primitives
    def face(self, pts: Sequence[Sequence[float]], mat: str, uvs: Sequence[Sequence[float]] | None = None, *, flip: bool = False,
             smooth: bool = False, uv_rot: int = 0):
        """Planar polygon (CCW seen from the side the normal points to). UVs default to planar metres."""
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        if flip:
            vs.reverse()
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.slot(mat)
        f.smooth = smooth
        if uvs is None:
            n = f.normal if f.normal.length > 0 else Vector((0, -1, 0))
            f.normal_update()
            n = f.normal
            uvs = [planar_uv(v.co, n) for v in vs]
            if uv_rot:
                uvs = [(vv, -uu) for uu, vv in uvs] if uv_rot == 1 else [(vv, uu) for uu, vv in uvs]
        elif flip:
            uvs = list(reversed(uvs))
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    def quad(self, a, b, c, d, mat: str, **kw):
        return self.face([a, b, c, d], mat, **kw)

    def box(self, lo: Sequence[float], hi: Sequence[float], mat: str, *, faces: str = "xyzXYZ", mats: dict[str, str] | None = None,
            uv_rot: int = 0):
        """Axis-aligned box between corners lo and hi. ``faces`` selects which sides to emit (x=-X, X=+X ...);
        ``mats`` may override the material per side letter."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        P = lambda x, y, z: Vector((x, y, z))  # noqa: E731
        m = lambda k: (mats or {}).get(k, mat)  # noqa: E731
        if "y" in faces:  # -Y (street-facing)
            self.face([P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)], m("y"), uv_rot=uv_rot)
        if "Y" in faces:
            self.face([P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)], m("Y"), uv_rot=uv_rot)
        if "x" in faces:
            self.face([P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)], m("x"), uv_rot=uv_rot)
        if "X" in faces:
            self.face([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], m("X"), uv_rot=uv_rot)
        if "Z" in faces:
            self.face([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], m("Z"), uv_rot=uv_rot)
        if "z" in faces:
            self.face([P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0)], m("z"), uv_rot=uv_rot)

    def box_c(self, center: Sequence[float], size: Sequence[float], mat: str, **kw):
        c, s = Vector(center), Vector(size)
        self.box(c - s / 2, c + s / 2, mat, **kw)

    def frame(self, x0: float, x1: float, z0: float, z1: float, y0: float, y1: float, w: float, mat: str, *, inner_faces: bool = True):
        """Rectangular frame (4 bars of width w) in the XZ plane between depths y0 (street) and y1 (inside)."""
        self.box((x0, y0, z0), (x1, y0 + (y1 - y0), z0 + w), mat)             # bottom rail
        self.box((x0, y0, z1 - w), (x1, y1, z1), mat)                          # top rail
        self.box((x0, y0, z0 + w), (x0 + w, y1, z1 - w), mat)                  # left stile
        self.box((x1 - w, y0, z0 + w), (x1, y1, z1 - w), mat)                  # right stile

    def extrude_profile(self, profile: Sequence[Sequence[float]], x0: float, x1: float, mat: str, *, closed: bool = False,
                        caps: bool = True, smooth: bool = False, y_off: float = 0.0, z_off: float = 0.0, flip: bool = False):
        """Sweep a 2-D profile (list of (y, z), street side is −y) along X from x0 to x1 (a moulding / cornice run).
        Profile winding: walk the *outer* surface from bottom to top for outward-facing normals."""
        pts = [Vector((0.0, y + y_off, z + z_off)) for y, z in profile]
        n = len(pts)
        rng = range(n) if closed else range(n - 1)
        v = 0.0
        for i in rng:
            j = (i + 1) % n
            a, b = pts[i], pts[j]
            seg = (b - a).length
            A = Vector((x0, a.y, a.z)); B = Vector((x0, b.y, b.z)); C = Vector((x1, b.y, b.z)); D = Vector((x1, a.y, a.z))
            uvs = [(x0, v), (x0, v + seg), (x1, v + seg), (x1, v)]
            self.face([A, B, C, D] if not flip else [A, D, C, B], mat, uvs=uvs, smooth=smooth)
            v += seg
        if caps and closed and n >= 3:
            self.face([Vector((x0, p.y, p.z)) for p in pts], mat, flip=not flip)
            self.face([Vector((x1, p.y, p.z)) for p in pts], mat, flip=flip)

    def lathe(self, profile: Sequence[Sequence[float]], segments: int, mat: str, *, center=(0.0, 0.0), z_off: float = 0.0,
              start_deg: float = 0.0, end_deg: float = 360.0, smooth: bool = True, caps: tuple[bool, bool] = (False, False)):
        """Revolve a (radius, z) profile around a vertical axis at ``center``. UV: u = arc length, v = profile length."""
        cx, cy = center
        full = abs(end_deg - start_deg) >= 359.9
        nseg = segments
        ang = [math.radians(start_deg + (end_deg - start_deg) * i / nseg) for i in range(nseg + (0 if full else 1))]
        rings = []
        for r, z in profile:
            rings.append([Vector((cx + r * math.cos(a), cy + r * math.sin(a), z + z_off)) for a in ang])
        v = 0.0
        for i in range(len(profile) - 1):
            (r0, z0), (r1, z1) = profile[i], profile[i + 1]
            seg = math.hypot(r1 - r0, z1 - z0)
            rmean = max((r0 + r1) / 2, 1e-4)
            for k in range(nseg):
                k2 = (k + 1) % len(ang) if full else k + 1
                a, b, c, d = rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]
                u0 = rmean * 2 * math.pi * k / nseg
                u1 = rmean * 2 * math.pi * (k + 1) / nseg
                self.face([a, b, c, d], mat, uvs=[(u0, v), (u1, v), (u1, v + seg), (u0, v + seg)], smooth=smooth)
            v += seg
        if caps[0] and full:
            self.face(list(reversed(rings[0])), mat)
        if caps[1] and full:
            self.face(rings[-1], mat)

    def cylinder(self, p0: Sequence[float], p1: Sequence[float], radius: float, mat: str, *, segments: int = 8, caps: bool = True,
                 smooth: bool = True, radius1: float | None = None):
        """Cylinder (or cone) from p0 to p1."""
        a, b = Vector(p0), Vector(p1)
        axis = b - a
        L = axis.length
        if L < 1e-6:
            return
        r1 = radius if radius1 is None else radius1
        q = axis.normalized().to_track_quat("Z", "Y")
        ring0, ring1 = [], []
        for k in range(segments):
            t = 2 * math.pi * k / segments
            d = q @ Vector((math.cos(t), math.sin(t), 0.0))
            ring0.append(a + d * radius)
            ring1.append(b + d * r1)
        for k in range(segments):
            k2 = (k + 1) % segments
            u0 = radius * 2 * math.pi * k / segments
            u1 = radius * 2 * math.pi * (k + 1) / segments
            self.face([ring0[k], ring0[k2], ring1[k2], ring1[k]], mat, uvs=[(u0, 0), (u1, 0), (u1, L), (u0, L)], smooth=smooth)
        if caps:
            self.face(list(reversed(ring0)), mat)
            self.face(ring1, mat)

    def tube(self, path: Sequence[Sequence[float]], radius: float, mat: str, *, segments: int = 6, caps: bool = True):
        """Polyline pipe (railings, ladders, scaffold tubes)."""
        pts = [Vector(p) for p in path]
        for i in range(len(pts) - 1):
            self.cylinder(pts[i], pts[i + 1], radius, mat, segments=segments, caps=caps)

    def bar_grid(self, x0, x1, z0, z1, y, nx: int, nz: int, w: float, d: float, mat: str, *, outer: bool = False):
        """Grid of vertical (nx) and horizontal (nz) bars centred on plane y (window guards, muntins, grilles)."""
        for i in range(nx):
            x = x0 + (x1 - x0) * (i + 1) / (nx + 1)
            self.box((x - w / 2, y - d / 2, z0), (x + w / 2, y + d / 2, z1), mat)
        for j in range(nz):
            z = z0 + (z1 - z0) * (j + 1) / (nz + 1)
            self.box((x0, y - d / 2, z - w / 2), (x1, y + d / 2, z + w / 2), mat)
        if outer:
            self.frame(x0, x1, z0, z1, y - d / 2, y + d / 2, w, mat)

    def glass_pane(self, x0, x1, z0, z1, y, mat: str = "glass_clear", thickness: float = 0.006):
        """Thin glass slab (both faces for correct transmission)."""
        self.box((x0, y - thickness / 2, z0), (x1, y + thickness / 2, z1), mat, faces="yY")

    def merge(self, other: "Mesh", offset: Sequence[float] = (0, 0, 0), rot_z_deg: float = 0.0, scale: Sequence[float] = (1, 1, 1)):
        """Append another Mesh (its material slots are re-mapped by name)."""
        M = Matrix.Translation(Vector(offset)) @ Matrix.Rotation(math.radians(rot_z_deg), 4, "Z") @ Matrix.Diagonal((*scale, 1.0))
        other.bm.verts.ensure_lookup_table()
        remap = {}
        for f in other.bm.faces:
            vs = []
            for v in f.verts:
                key = v.index
                if key not in remap:
                    remap[key] = self.bm.verts.new(M @ v.co)
                vs.append(remap[key])
            try:
                nf = self.bm.faces.new(vs)
            except ValueError:
                continue
            nf.material_index = self.slot(other.mats[f.material_index])
            nf.smooth = f.smooth
            for lo, lo2 in zip(nf.loops, f.loops):
                lo[self.uv].uv = lo2[other.uv].uv

    def mirror_x(self, other: "Mesh"):
        """Append a copy of ``other`` mirrored in X (winding fixed)."""
        other.bm.verts.ensure_lookup_table()
        remap = {}
        for f in other.bm.faces:
            vs = []
            for v in f.verts:
                if v.index not in remap:
                    remap[v.index] = self.bm.verts.new(Vector((-v.co.x, v.co.y, v.co.z)))
                vs.append(remap[v.index])
            vs.reverse()
            try:
                nf = self.bm.faces.new(vs)
            except ValueError:
                continue
            nf.material_index = self.slot(other.mats[f.material_index])
            nf.smooth = f.smooth
            for lo, lo2 in zip(nf.loops, reversed(list(f.loops))):
                lo[self.uv].uv = lo2[other.uv].uv

    # -- stats / conversion
    def triangles(self) -> int:
        return sum(max(len(f.verts) - 2, 0) for f in self.bm.faces)

    def bounds(self) -> tuple[Vector, Vector]:
        lo = Vector((math.inf,) * 3); hi = Vector((-math.inf,) * 3)
        for v in self.bm.verts:
            lo = Vector(map(min, lo, v.co)); hi = Vector(map(max, hi, v.co))
        return lo, hi

    def to_object(self, name: str, col=None) -> bpy.types.Object:
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        me.update()
        for m in self.mats:
            me.materials.append(material(m))
        ob = bpy.data.objects.new(name, me)
        nb.link(ob, col)
        return ob

    def free(self):
        self.bm.free()


# --------------------------------------------------------------------------- materials
_MAT_CACHE: dict[str, bpy.types.Material] = {}


def _kit_maps(name: str) -> dict[str, str]:
    """1K JPEG copies of a material's maps for embedding (colour with AO baked, normal, ORM packed G=rough B=metal)."""
    meta = tx.resolve(name)
    maps = tx.get_texture_set(name)
    if not maps:
        return {}
    from PIL import Image
    adir = Path(maps["color"]).parent / f"kit{KIT_TEX_RES}"
    adir.mkdir(exist_ok=True)
    aid = meta["asset_id"]
    out = {"color": adir / f"{aid}_{KIT_TEX_RES}_color.jpg", "normal": adir / f"{aid}_{KIT_TEX_RES}_normal.jpg", "orm": adir / f"{aid}_{KIT_TEX_RES}_orm.jpg"}
    if all(p.exists() for p in out.values()):
        return {k: str(v) for k, v in out.items()}
    R = (KIT_TEX_RES, KIT_TEX_RES)
    col = Image.open(maps["color"]).convert("RGB").resize(R, Image.LANCZOS)
    if "ao" in maps:
        ao = Image.open(maps["ao"]).convert("L").resize(R, Image.LANCZOS)
        # bake half-strength AO into albedo (standard for kit assets; glTF occlusion left unused)
        ao_mix = Image.eval(ao, lambda v: 128 + v // 2)
        col = Image.composite(col, Image.new("RGB", R, (0, 0, 0)), Image.new("L", R, 255))
        from PIL import ImageChops
        col = ImageChops.multiply(col, Image.merge("RGB", (ao_mix, ao_mix, ao_mix)))
    col.save(out["color"], quality=88, optimize=True)
    if "normal" in maps:
        Image.open(maps["normal"]).convert("RGB").resize(R, Image.LANCZOS).save(out["normal"], quality=90, optimize=True)
    else:
        Image.new("RGB", R, (128, 128, 255)).save(out["normal"], quality=90)
    rough = Image.open(maps["roughness"]).convert("L").resize(R, Image.LANCZOS) if "roughness" in maps else Image.new("L", R, 150)
    metal = Image.open(maps["metalness"]).convert("L").resize(R, Image.LANCZOS) if "metalness" in maps else Image.new("L", R, 0)
    Image.merge("RGB", (Image.new("L", R, 255), rough, metal)).save(out["orm"], quality=90, optimize=True)
    return {k: str(v) for k, v in out.items()}


def _load_image(path: str, non_color: bool) -> bpy.types.Image:
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def material(name: str) -> bpy.types.Material:
    """PBR material for a catalog name (texture set embedded at 1K) or a kit-generated material (``gen:`` prefix handled by
    ``generated_material``). Cached per session."""
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    if name.startswith("emit:") or name.startswith("flat:"):
        raise ValueError(f"use generated_material() for {name}")
    meta = tx.get_texture_meta(name)
    mat = bpy.data.materials.new(f"kit_{name}")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    out = nt.nodes["Material Output"]
    if meta.get("provider") == "procedural":
        p = meta["procedural"]
        bsdf.inputs["Base Color"].default_value = tuple(p.get("base_color", (0.8, 0.8, 0.8, 1.0)))
        bsdf.inputs["Roughness"].default_value = p.get("roughness", 0.1)
        bsdf.inputs["Metallic"].default_value = p.get("metallic", 0.0)
        if p.get("transmission"):
            bsdf.inputs["Transmission Weight"].default_value = p["transmission"]
            bsdf.inputs["IOR"].default_value = p.get("ior", 1.5)
        if p.get("alpha", 1.0) < 1.0:
            bsdf.inputs["Alpha"].default_value = p["alpha"]
            mat.blend_method = "BLEND"
            mat.use_backface_culling = False
        _MAT_CACHE[name] = mat
        return mat
    maps = _kit_maps(name)
    scale = 1.0 / float(meta.get("physical_size_m", 1.0))
    texco = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(texco.outputs["UV"], mapping.inputs["Vector"])
    # colour
    if meta.get("color_override"):
        c = meta["color_override"]
        bsdf.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
    else:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = _load_image(maps["color"], False)
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        if meta.get("tint"):
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            t = meta["tint"]
            mix.inputs[7].default_value = (t[0], t[1], t[2], 1.0)  # B (RGBA)
            nt.links.new(tex.outputs["Color"], mix.inputs[6])     # A (RGBA)
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    # roughness / metallic
    if meta.get("roughness_override") is not None:
        bsdf.inputs["Roughness"].default_value = float(meta["roughness_override"])
        bsdf.inputs["Metallic"].default_value = float(meta.get("metallic", 0.0))
    else:
        orm = nt.nodes.new("ShaderNodeTexImage")
        orm.image = _load_image(maps["orm"], True)
        nt.links.new(mapping.outputs["Vector"], orm.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        if meta.get("roughness_scale"):
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = float(meta["roughness_scale"])
            nt.links.new(sep.outputs["Green"], mul.inputs[0])
            nt.links.new(mul.outputs[0], bsdf.inputs["Roughness"])
        else:
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    # normal
    nrm = nt.nodes.new("ShaderNodeTexImage")
    nrm.image = _load_image(maps["normal"], True)
    nt.links.new(mapping.outputs["Vector"], nrm.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = float(meta.get("normal_strength", 1.0))
    nt.links.new(nrm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    _MAT_CACHE[name] = mat
    return mat


def generated_material(name: str, *, image: str | None = None, base_color=(0.8, 0.8, 0.8, 1.0), roughness: float = 0.6, metallic: float = 0.0,
                       emission: Sequence[float] | None = None, emission_strength: float = 0.0, alpha_from_image: bool = False,
                       double_sided: bool = True, uv_scale_m: float | None = None) -> bpy.types.Material:
    """Material for kit-generated textures (signs, interior cards, curtains) or flat/emissive colours. Registered under
    ``name`` so Mesh slots can reference it."""
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    mat = bpy.data.materials.new(f"kit_{name}")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = tuple(base_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = _load_image(image, False)
        if uv_scale_m:
            texco = nt.nodes.new("ShaderNodeTexCoord")
            mapping = nt.nodes.new("ShaderNodeMapping")
            s = 1.0 / uv_scale_m
            mapping.inputs["Scale"].default_value = (s, s, s)
            nt.links.new(texco.outputs["UV"], mapping.inputs["Vector"])
            nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if emission is not None:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emission_strength
        if alpha_from_image:
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.blend_method = "BLEND"
    elif emission is not None:
        bsdf.inputs["Emission Color"].default_value = tuple(emission) if len(emission) == 4 else (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.use_backface_culling = not double_sided
    _MAT_CACHE[name] = mat
    return mat


def flat(name: str, rgb: Sequence[float], roughness: float = 0.5, metallic: float = 0.0) -> str:
    """Register a flat-colour material and return its slot name."""
    generated_material(name, base_color=(*rgb, 1.0), roughness=roughness, metallic=metallic)
    return name


def emissive(name: str, rgb: Sequence[float], strength: float, roughness: float = 0.4) -> str:
    generated_material(name, base_color=(*rgb, 1.0), roughness=roughness, emission=rgb, emission_strength=strength)
    return name


# --------------------------------------------------------------------------- LOD, export, catalog
def evaluated_tris(ob: bpy.types.Object) -> int:
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ob.evaluated_get(dg).to_mesh_clear()
    return n


def _name_data(ob: bpy.types.Object) -> bpy.types.Object:
    """Give the mesh datablock the object's name so the exported glTF mesh carries it too."""
    ob.data.name = ob.name
    return ob


def make_lod1(ob: bpy.types.Object, pid: str, lod_mesh: Mesh | None = None) -> bpy.types.Object:
    """LOD1 object named ``<id>_LOD1`` with ≤ 25 % of LOD0 triangles: explicit low-poly builder, else decimate, else a
    front-facing quad proxy carrying the dominant material."""
    tris0 = evaluated_tris(ob)
    target = max(2, int(tris0 * 0.25))
    if lod_mesh is not None:
        lod = lod_mesh.to_object(f"{pid}_LOD1")
        if evaluated_tris(lod) <= target:
            return _name_data(lod)
        bpy.data.objects.remove(lod, do_unlink=True)
    # decimate a copy
    me = ob.data.copy()
    lod = bpy.data.objects.new(f"{pid}_LOD1", me)
    nb.link(lod)
    mod = lod.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = min(0.22, target / max(tris0, 1))
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    if evaluated_tris(lod) <= target and evaluated_tris(lod) >= 2:
        # apply so the export sees a plain mesh
        dg = bpy.context.evaluated_depsgraph_get()
        ev = lod.evaluated_get(dg).to_mesh()
        new = bpy.data.meshes.new_from_object(lod.evaluated_get(dg))
        lod.evaluated_get(dg).to_mesh_clear()
        lod.modifiers.clear()
        lod.data = new
        for m in me.materials:
            if m.name not in [x.name for x in new.materials]:
                new.materials.append(m)
        bpy.data.meshes.remove(me)
        return _name_data(lod)
    bpy.data.objects.remove(lod, do_unlink=True)
    bpy.data.meshes.remove(me)
    # proxy quad(s): street-facing quad of the bounding box
    b = nb.bounds_of([ob])
    lo, hi = Vector(b["min"]), Vector(b["max"])
    dom = _dominant_material(ob)
    pm = Mesh()
    pm.face([(lo.x, lo.y, lo.z), (hi.x, lo.y, lo.z), (hi.x, lo.y, hi.z), (lo.x, lo.y, hi.z)], dom)
    if tris0 >= 24:  # room for a top face too
        pm.face([(lo.x, lo.y, hi.z), (hi.x, lo.y, hi.z), (hi.x, hi.y, hi.z), (lo.x, hi.y, hi.z)], dom)
    return _name_data(pm.to_object(f"{pid}_LOD1"))


def _dominant_material(ob: bpy.types.Object) -> str:
    counts: dict[int, float] = {}
    for p in ob.data.polygons:
        counts[p.material_index] = counts.get(p.material_index, 0.0) + p.area
    idx = max(counts, key=counts.get) if counts else 0
    name = ob.data.materials[idx].name if ob.data.materials else "kit_precast"
    return name[4:] if name.startswith("kit_") else name


def build_piece(piece: Piece, *, export: bool = True) -> dict:
    """Build LOD0 + LOD1 objects for a piece, export the glb, write the catalog entry. Returns the catalog entry."""
    t0 = time.time()
    m = piece.build()
    tris = m.triangles()
    lo, hi = m.bounds()
    ob = _name_data(m.to_object(piece.id))
    m.free()
    lod_mesh = piece.lod1() if piece.lod1 else None
    lod = make_lod1(ob, piece.id, lod_mesh)
    tris1 = evaluated_tris(lod)
    size = (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
    mats = [mm.name[4:] if mm.name.startswith("kit_") else mm.name for mm in ob.data.materials]
    tex_assets = sorted({tx.resolve(mm)["asset_id"] for mm in mats if _is_catalog_material(mm)})
    entry = {
        "id": piece.id, "category": piece.category, "glb": f"kit/facade/{piece.id}.glb",
        "bounds": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
        "anchor": {"origin": piece.anchor, "wall_plane": "y=0", "into_building": "+Y", "up": "+Z", "units": "m"},
        "materials": mats, "texture_assets": tex_assets,
        "polycount": {"lod0_triangles": tris, "lod1_triangles": tris1, "lod0_vertices": len(ob.data.vertices), "budget": piece.budget,
                      "within_budget": tris <= piece.budget, "lod1_ratio": round(tris1 / max(tris, 1), 3)},
        "nominal_size_m": list(piece.nominal_size), "measured_size_m": [round(v, 4) for v in size],
        "variants": piece.variants, "features": piece.features, "description": piece.description,
        "lod1_mesh": f"{piece.id}_LOD1", "schema_version": nb.SCHEMA_VERSION,
    }
    entry.update(piece.extra)
    if export:
        path = KIT_OUT / f"{piece.id}.glb"
        nb.export_glb(path, objects=[ob, lod], extras={"kit_id": piece.id, "category": piece.category, "bounds": entry["bounds"],
                                                       "anchor": entry["anchor"], "nominal_size_m": entry["nominal_size_m"]})
        entry["glb_bytes"] = path.stat().st_size
        nb.write_catalog_entry(CATALOG_DIR, entry)
    entry["build_seconds"] = round(time.time() - t0, 2)
    if tris > piece.budget:
        log.warning("%s: %d triangles exceeds budget %d", piece.id, tris, piece.budget)
    for i, (n, s) in enumerate(zip(piece.nominal_size, size)):
        if n > 0 and abs(s - n) / n > 0.05:
            log.warning("%s: axis %d measured %.3f vs nominal %.3f (> 5 %%)", piece.id, i, s, n)
    return entry


def _is_catalog_material(name: str) -> bool:
    try:
        rec = tx.resolve(name)
        return rec.get("provider") != "procedural"
    except tx.TextureError:
        return False


def unlink_all_pieces():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


# --------------------------------------------------------------------------- small helpers shared by pieces
def lerp(a, b, t):
    return a + (b - a) * t


def steps_profile(n: int, rise: float, run: float, nosing: float = 0.03) -> list[tuple[float, float]]:
    """(y, z) profile for a stair seen from the side: starts at street (−y) bottom, climbs toward the wall (+y)."""
    pts = [(-(n * run), 0.0)]
    for i in range(n):
        y = -(n - i) * run
        z = i * rise
        pts.append((y - nosing, z + rise))
        pts.append((y + run, z + rise))
    return pts
