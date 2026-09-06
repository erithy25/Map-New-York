"""bmesh geometry toolbox for the vehicle builders.

Everything works headless (no operators needing a UI context). Units are metres, Z up, +X forward.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

from . import env

nb = env.nb
log = env.log

Vec3 = Sequence[float]
TWO_PI = 2.0 * math.pi

FONT_SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_SERIF_BOLD_ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"
FONT_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


# --------------------------------------------------------------------------- scalar helpers
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def smoothstep(e0: float, e1: float, x: float) -> float:
    if e1 == e0:
        return 1.0 if x >= e1 else 0.0
    t = clamp((x - e0) / (e1 - e0))
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class PolyCurve:
    """Piecewise-linear function of x from documented key points ``(x, value)``; clamped outside the range.
    This is the numeric 'blueprint' form used for every body line (DATA in specs/blueprints is a list of these)."""

    def __init__(self, pts: Sequence[tuple[float, float]]):
        if len(pts) < 1:
            raise ValueError("PolyCurve needs at least one point")
        srt = sorted(pts, key=lambda p: p[0])
        self.xs = np.asarray([p[0] for p in srt], dtype=np.float64)
        self.vs = np.asarray([p[1] for p in srt], dtype=np.float64)

    def __call__(self, x: float) -> float:
        return float(np.interp(x, self.xs, self.vs))

    def offset(self, dv: float) -> "PolyCurve":
        return PolyCurve(list(zip(self.xs.tolist(), (self.vs + dv).tolist())))

    @property
    def x_min(self) -> float:
        return float(self.xs[0])

    @property
    def x_max(self) -> float:
        return float(self.xs[-1])


# --------------------------------------------------------------------------- bmesh primitives
def loft(stations: Sequence[Sequence[Vec3]], *, tag: Callable[[int, int], int] | None = None,
         close_loop: bool = False) -> tuple[bmesh.types.BMesh, list[list[bmesh.types.BMVert]]]:
    """Quad-loft consecutive stations (equal point counts). ``tag(i, j)`` gives the material index of the quad
    between station i/i+1 and points j/j+1. Returns the bmesh and the vertex grid."""
    n = len(stations[0])
    for k, st in enumerate(stations):
        if len(st) != n:
            raise ValueError(f"station {k} has {len(st)} points, expected {n}")
    bm = bmesh.new()
    rows = [[bm.verts.new(tuple(p)) for p in st] for st in stations]
    seg = n if close_loop else n - 1
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(seg):
            j2 = (j + 1) % n
            quad = (a[j], a[j2], b[j2], b[j])
            if len({id(v) for v in quad}) < 3:
                continue
            try:
                f = bm.faces.new(quad if len({id(v) for v in quad}) == 4 else tuple(dict.fromkeys(quad)))
            except ValueError:
                continue
            if tag is not None:
                f.material_index = tag(i, j)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, rows


def mirror_y(bm: bmesh.types.BMesh, remap: dict[int, int] | None = None, merge_dist: float = 1e-4) -> None:
    """Mirror across the XZ plane (Y=0) and merge the seam. Faces landing on y<0 get material indices remapped
    (left-hand panel ids -> right-hand ids)."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.mirror(bm, geom=geom, axis='Y', merge_dist=merge_dist)
    if remap:
        for f in bm.faces:
            c = f.calc_center_median()
            if c.y < -1e-6 and f.material_index in remap:
                f.material_index = remap[f.material_index]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def fill_holes(bm: bmesh.types.BMesh, material_index: int | None = None) -> None:
    before = set(f.index for f in bm.faces)
    bm.faces.ensure_lookup_table()
    res = bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)
    if material_index is not None:
        for f in res.get("faces", []):
            f.material_index = material_index
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    del before


def box_bm(size: Vec3, center: Vec3 = (0, 0, 0), material_index: int = 0) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    for f in bm.faces:
        f.material_index = material_index
    return bm


def rounded_box_bm(size: Vec3, radius: float, *, segments: int = 3, center: Vec3 = (0, 0, 0), material_index: int = 0,
                   axes: str = "xyz") -> bmesh.types.BMesh:
    """Box with bevelled edges. ``axes`` restricts bevelling to edges parallel to those axes (e.g. "z" for a
    cushion rounded only in plan)."""
    bm = box_bm(size, center, material_index)
    r = min(radius, 0.499 * min(size))
    if r <= 0:
        return bm
    edges = []
    for e in bm.edges:
        d = (e.verts[0].co - e.verts[1].co).normalized()
        if ("x" in axes and abs(d.x) > 0.9) or ("y" in axes and abs(d.y) > 0.9) or ("z" in axes and abs(d.z) > 0.9):
            edges.append(e)
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=r, offset_type='OFFSET', segments=segments, profile=0.5, affect='EDGES',
                        clamp_overlap=True, material=material_index)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def _axis_matrix(axis: str | Vec3) -> Matrix:
    """Rotation taking +Z to the requested axis."""
    if isinstance(axis, str):
        d = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1)), "-X": Vector((-1, 0, 0)),
             "-Y": Vector((0, -1, 0)), "-Z": Vector((0, 0, -1))}[axis.upper()]
    else:
        d = Vector(axis).normalized()
    return d.to_track_quat('Z', 'Y').to_matrix().to_4x4()


def cylinder_bm(radius: float, length: float, *, axis: str | Vec3 = "Z", center: Vec3 = (0, 0, 0), segments: int = 24,
                cap: bool = True, radius2: float | None = None, material_index: int = 0) -> bmesh.types.BMesh:
    """Cylinder (or cone when radius2 differs) centred on ``center`` along ``axis``."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segments, radius1=radius,
                          radius2=radius if radius2 is None else radius2, depth=length)
    m = Matrix.Translation(Vector(center)) @ _axis_matrix(axis)
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    for f in bm.faces:
        f.material_index = material_index
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sphere_bm(radius: float | Vec3, *, center: Vec3 = (0, 0, 0), segments: int = 24, rings: int = 12,
              material_index: int = 0) -> bmesh.types.BMesh:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    r = Vector((radius, radius, radius)) if isinstance(radius, (int, float)) else Vector(radius)
    bmesh.ops.scale(bm, vec=r, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    for f in bm.faces:
        f.material_index = material_index
    return bm


def torus_bm(major: float, minor: float, *, axis: str | Vec3 = "Z", center: Vec3 = (0, 0, 0), segments: int = 48,
             ring_segments: int = 12, material_index: int = 0, arc: tuple[float, float] | None = None) -> bmesh.types.BMesh:
    """Torus around ``axis``; ``arc=(a0,a1)`` in radians gives a partial ring (open tube)."""
    bm = bmesh.new()
    a0, a1 = arc if arc else (0.0, TWO_PI)
    full = arc is None
    steps = segments if full else max(2, segments)
    rings = []
    for i in range(steps if full else steps + 1):
        t = a0 + (a1 - a0) * (i / steps)
        c, s = math.cos(t), math.sin(t)
        ring = []
        for k in range(ring_segments):
            p = TWO_PI * k / ring_segments
            rr = major + minor * math.cos(p)
            ring.append(bm.verts.new((rr * c, rr * s, minor * math.sin(p))))
        rings.append(ring)
    n = len(rings)
    for i in range(n if full else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(ring_segments):
            k2 = (k + 1) % ring_segments
            f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
            f.material_index = material_index
    if not full:
        for ring in (rings[0], rings[-1]):
            f = bm.faces.new(ring)
            f.material_index = material_index
    m = Matrix.Translation(Vector(center)) @ _axis_matrix(axis)
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def revolve_bm(profile: Sequence[tuple[float, float]], *, axis: str = "Y", segments: int = 48, close: bool = False,
               material_index: int = 0, uv: bool = True, mat_by_segment: Callable[[int], int] | None = None) -> bmesh.types.BMesh:
    """Revolve a (radius, axial) profile around ``axis`` through the origin. UVs: u around (0..1), v = normalised
    arc length along the profile (0 at the first point). ``mat_by_segment(k)`` assigns per profile segment."""
    bm = bmesh.new()
    if axis.upper() == "Y":
        pts = [Vector((r, a, 0.0)) for r, a in profile]
        ax = Vector((0, 1, 0))
    elif axis.upper() == "Z":
        pts = [Vector((r, 0.0, a)) for r, a in profile]
        ax = Vector((0, 0, 1))
    else:
        pts = [Vector((0.0, r, a)) for r, a in profile]
        ax = Vector((1, 0, 0))
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)
    total = cum[-1] or 1.0
    vparam = [c / total for c in cum]
    # the segment tag layer must exist before any edge is created: adding a custom-data layer
    # reallocates the edge customdata block and invalidates BMEdge references taken before it.
    lay = bm.edges.layers.int.new("seg")
    verts = [bm.verts.new(p) for p in pts]
    edges = []
    for i in range(len(verts) - 1):
        e = bm.edges.new((verts[i], verts[i + 1]))
        e[lay] = i + 1
        edges.append(e)
    if close:
        e = bm.edges.new((verts[-1], verts[0]))
        e[lay] = len(edges) + 1
        edges.append(e)
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=ax, dvec=(0, 0, 0), angle=TWO_PI, steps=segments,
                   use_merge=True, use_normal_flip=False, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # per-face segment = max seg tag of its edges (profile-direction edges carry the tag after spin)
    for f in bm.faces:
        k = 0
        for e in f.edges:
            k = max(k, e[lay])
        f.material_index = mat_by_segment(k - 1) if (mat_by_segment and k) else material_index
    if uv:
        uv_layer = bm.loops.layers.uv.new("UVMap")
        # v from axial/radial position: nearest profile point
        prof_arr = np.asarray([[p.x, p.y, p.z] for p in pts])
        def vcoord(co: Vector) -> float:
            if axis.upper() == "Y":
                key = np.asarray([math.hypot(co.x, co.z), co.y, 0.0])
            elif axis.upper() == "Z":
                key = np.asarray([math.hypot(co.x, co.y), 0.0, co.z])
            else:
                key = np.asarray([0.0, math.hypot(co.y, co.z), co.x])
            d = np.linalg.norm(prof_arr - key, axis=1)
            return vparam[int(np.argmin(d))]
        for f in bm.faces:
            us = []
            for lp in f.loops:
                co = lp.vert.co
                if axis.upper() == "Y":
                    ang = math.atan2(co.z, co.x)
                elif axis.upper() == "Z":
                    ang = math.atan2(co.y, co.x)
                else:
                    ang = math.atan2(co.z, co.y)
                us.append((ang / TWO_PI) % 1.0)
            if max(us) - min(us) > 0.5:
                us = [u + 1.0 if u < 0.5 else u for u in us]
            for lp, u in zip(f.loops, us):
                lp[uv_layer].uv = (u, vcoord(lp.vert.co))
    bm.edges.layers.int.remove(lay)
    return bm


def tube_bm(path: Sequence[Vec3], radius: float | Sequence[float], *, segments: int = 12, cap: bool = True,
            material_index: int = 0, closed_path: bool = False) -> bmesh.types.BMesh:
    """Sweep a circle along a polyline with parallel-transport frames (pipes, frames, wiper arms, stalks)."""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        raise ValueError("tube needs >= 2 path points")
    n = len(pts)
    radii = [radius] * n if isinstance(radius, (int, float)) else list(radius)
    if len(radii) != n:
        raise ValueError("radius list must match path length")
    tangents = []
    for i in range(n):
        if closed_path:
            t = pts[(i + 1) % n] - pts[i - 1]
        elif i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        tangents.append(t.normalized() if t.length > 1e-9 else Vector((1, 0, 0)))
    # initial normal: any perpendicular
    t0 = tangents[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nrm = (ref - t0 * ref.dot(t0)).normalized()
    bm = bmesh.new()
    rings = []
    for i in range(n):
        t = tangents[i]
        if i > 0:
            # parallel transport: rotate previous normal by the rotation between tangents
            prev = tangents[i - 1]
            axis = prev.cross(t)
            if axis.length > 1e-9:
                ang = math.acos(clamp(prev.dot(t), -1.0, 1.0))
                nrm = Quaternion(axis.normalized(), ang) @ nrm
            nrm = (nrm - t * nrm.dot(t)).normalized()
        bnorm = t.cross(nrm).normalized()
        ring = []
        for k in range(segments):
            a = TWO_PI * k / segments
            ring.append(bm.verts.new(pts[i] + (nrm * math.cos(a) + bnorm * math.sin(a)) * radii[i]))
        rings.append(ring)
    m = n if closed_path else n - 1
    for i in range(m):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(segments):
            k2 = (k + 1) % segments
            f = bm.faces.new((a[k], b[k], b[k2], a[k2]))
            f.material_index = material_index
    if cap and not closed_path:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = material_index
        f = bm.faces.new(rings[-1])
        f.material_index = material_index
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def ribbon_bm(path: Sequence[Vec3], width: float, up: Vec3 = (0, 0, 1), *, material_index: int = 0,
              thickness: float = 0.0) -> bmesh.types.BMesh:
    """Flat strip along a polyline (seat belts, trim strips). ``up`` is the strip's face normal hint."""
    pts = [Vector(p) for p in path]
    upv = Vector(up).normalized()
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(upv).normalized() * (width / 2)
        rows.append((bm.verts.new(p - side), bm.verts.new(p + side)))
    for (a0, a1), (b0, b1) in zip(rows, rows[1:]):
        f = bm.faces.new((a0, a1, b1, b0))
        f.material_index = material_index
    if thickness > 0:
        res = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness)
        for f in bm.faces:
            f.material_index = material_index
        del res
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def quad_uv01_bm(corners: Sequence[Vec3], *, material_index: int = 0, double_sided: bool = False) -> bmesh.types.BMesh:
    """One quad with UVs exactly (0,0),(1,0),(1,1),(0,1) at the given corners (gauges, plates, mirror glass, signs).
    Corner order: bottom-left, bottom-right, top-right, top-left as seen by the viewer of the face."""
    if len(corners) != 4:
        raise ValueError("quad needs 4 corners")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(tuple(c)) for c in corners]
    f = bm.faces.new(vs)
    f.material_index = material_index
    for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uv_layer].uv = uv
    if double_sided:
        f2 = bm.faces.new(list(reversed(vs)))
        f2.material_index = material_index
        for lp, uv in zip(f2.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
            lp[uv_layer].uv = uv
    return bm


def ngon_bm(points: Sequence[Vec3], material_index: int = 0, flip: bool = False) -> bmesh.types.BMesh:
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(p)) for p in points]
    if flip:
        vs.reverse()
    f = bm.faces.new(vs)
    f.material_index = material_index
    return bm


def extrude_profile_bm(profile_xz: Sequence[tuple[float, float]], y0: float, y1: float, *, material_index: int = 0,
                       close: bool = True, cap: bool = True) -> bmesh.types.BMesh:
    """Sweep a closed 2-D (x, z) profile along Y from y0 to y1 (dash bodies, bumpers, sills)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in profile_xz]
    b = [bm.verts.new((x, y1, z)) for x, z in profile_xz]
    n = len(a)
    rng = n if close else n - 1
    for i in range(rng):
        j = (i + 1) % n
        f = bm.faces.new((a[i], a[j], b[j], b[i]))
        f.material_index = material_index
    if cap and close:
        for ring in (list(reversed(a)), b):
            try:
                f = bm.faces.new(ring)
                f.material_index = material_index
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def prism_bm(polygon_xy: Sequence[tuple[float, float]], z0: float, z1: float, material_index: int = 0) -> bmesh.types.BMesh:
    """Vertical prism from a 2-D outline (light boxes, signs, cart bodies)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in polygon_xy]
    b = [bm.verts.new((x, y, z1)) for x, y in polygon_xy]
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((a[i], a[j], b[j], b[i]))
        f.material_index = material_index
    for ring in (list(reversed(a)), b):
        f = bm.faces.new(ring)
        f.material_index = material_index
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# --------------------------------------------------------------------------- bmesh transforms / merging
def transform_bm(bm: bmesh.types.BMesh, matrix: Matrix) -> bmesh.types.BMesh:
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def translate_bm(bm: bmesh.types.BMesh, vec: Vec3) -> bmesh.types.BMesh:
    bmesh.ops.translate(bm, vec=Vector(vec), verts=bm.verts)
    return bm


def rotate_bm(bm: bmesh.types.BMesh, axis: str | Vec3, angle_deg: float, center: Vec3 = (0, 0, 0)) -> bmesh.types.BMesh:
    ax = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}[axis.upper()] if isinstance(axis, str) else Vector(axis)
    m = Matrix.Rotation(math.radians(angle_deg), 4, ax)
    bmesh.ops.rotate(bm, cent=Vector(center), matrix=m.to_3x3(), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def mirror_copy_bm(bm: bmesh.types.BMesh, axis: str = "Y") -> bmesh.types.BMesh:
    """Return a mirrored copy (for right-hand parts built once on the left)."""
    out = bm.copy()
    s = Vector((1, 1, 1))
    setattr(s, axis.lower(), -1.0)
    bmesh.ops.scale(out, vec=s, verts=out.verts)
    for f in out.faces:
        f.normal_flip()
    bmesh.ops.recalc_face_normals(out, faces=out.faces)
    return out


def merge_bm(parts: Iterable[bmesh.types.BMesh], *, free: bool = True) -> bmesh.types.BMesh:
    """Merge bmeshes into one (material indices preserved; UV layer 'UVMap' preserved when present)."""
    out = bmesh.new()
    out_uv = out.loops.layers.uv.new("UVMap")
    for bm in parts:
        uv_src = bm.loops.layers.uv.get("UVMap")
        vmap = {v: out.verts.new(v.co) for v in bm.verts}
        for f in bm.faces:
            try:
                nf = out.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = f.material_index
            nf.smooth = f.smooth
            if uv_src is not None:
                for lp_src, lp_dst in zip(f.loops, nf.loops):
                    lp_dst[out_uv].uv = lp_src[uv_src].uv
        if free:
            bm.free()
    return out


def set_material_bm(bm: bmesh.types.BMesh, index: int) -> bmesh.types.BMesh:
    for f in bm.faces:
        f.material_index = index
    return bm


def flip_bm(bm: bmesh.types.BMesh) -> bmesh.types.BMesh:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


# --------------------------------------------------------------------------- objects
def to_object(name: str, bm: bmesh.types.BMesh, materials: Sequence[bpy.types.Material] = (), *, smooth: bool = True,
              sharp_angle_deg: float | None = 40.0, col: bpy.types.Collection | None = None) -> bpy.types.Object:
    ob = nb.bmesh_to_object(name, bm, col=col, materials=list(materials))
    shade(ob, smooth=smooth, sharp_angle_deg=sharp_angle_deg)
    return ob


def shade(ob: bpy.types.Object, *, smooth: bool = True, sharp_angle_deg: float | None = None) -> None:
    me = ob.data
    if smooth:
        if hasattr(me, "shade_smooth"):
            me.shade_smooth()
        else:  # pragma: no cover - older API
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        if sharp_angle_deg is not None and hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(sharp_angle_deg))
    else:
        if hasattr(me, "shade_flat"):
            me.shade_flat()
        else:  # pragma: no cover
            me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
    me.update()


def bake_modifiers(ob: bpy.types.Object) -> None:
    """Evaluate all modifiers into the mesh data (needed before shape keys and before export of morph targets)."""
    if not ob.modifiers:
        return
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    mats = list(old.materials)
    ob.modifiers.clear()
    ob.data = me
    if len(me.materials) < len(mats):
        me.materials.clear()
        for m in mats:
            me.materials.append(m)
    me.name = old.name
    bpy.data.meshes.remove(old)


def subdivide(ob: bpy.types.Object, levels: int, *, crease: Callable[[Vector, Vector], float] | None = None,
              boundary_smooth: str = "ALL") -> None:
    """Catmull-Clark via the Subdivision modifier, baked. ``crease(v0, v1)`` returns 0..1 per edge."""
    if levels <= 0:
        return
    me = ob.data
    if crease is not None:
        attr = me.attributes.get("crease_edge") or me.attributes.new("crease_edge", 'FLOAT', 'EDGE')
        vals = np.zeros(len(me.edges), dtype=np.float32)
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        ev = np.empty(len(me.edges) * 2, dtype=np.int32)
        me.edges.foreach_get("vertices", ev)
        ev = ev.reshape(-1, 2)
        for i, (a, b) in enumerate(ev):
            vals[i] = crease(Vector(co[a]), Vector(co[b]))
        attr.data.foreach_set("value", vals)
    mod = ob.modifiers.new("subsurf", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels
    mod.use_creases = True
    mod.boundary_smooth = boundary_smooth
    mod.uv_smooth = 'PRESERVE_BOUNDARIES'
    bake_modifiers(ob)


def boolean_cut(ob: bpy.types.Object, cutter: bpy.types.Object, *, operation: str = "DIFFERENCE",
                transfer_materials: bool = True, remove_cutter: bool = True) -> None:
    mod = ob.modifiers.new("bool", "BOOLEAN")
    mod.operation = operation
    mod.object = cutter
    mod.solver = 'EXACT'
    mod.material_mode = 'TRANSFER' if transfer_materials else 'INDEX'
    bake_modifiers(ob)
    if remove_cutter:
        me = cutter.data
        bpy.data.objects.remove(cutter, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)


def solidify(ob: bpy.types.Object, thickness: float, *, rim_only: bool = True, offset: float = -1.0) -> None:
    mod = ob.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_rim = True
    mod.use_rim_only = rim_only
    mod.use_even_offset = True
    bake_modifiers(ob)


def inset_gap(ob: bpy.types.Object, gap: float) -> None:
    """Shrink a panel by ``gap`` along its boundary (panel gaps between doors/hood/trunk and body)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if not bm.faces:
        bm.free()
        return
    res = bmesh.ops.inset_region(bm, faces=bm.faces[:], thickness=gap, depth=0.0, use_boundary=True, use_even_offset=True,
                                 use_interpolate=True, use_relative_offset=False, use_edge_rail=False, use_outset=False)
    bmesh.ops.delete(bm, geom=res["faces"], context='FACES')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def separate_by_material(ob: bpy.types.Object, groups: dict[str, Sequence[int]]) -> dict[str, bpy.types.Object]:
    """Move faces with the listed material indices into new objects (one per group name). The source keeps the rest.
    Groups with no faces are skipped (logged)."""
    me = ob.data
    src = bmesh.new()
    src.from_mesh(me)
    out: dict[str, bpy.types.Object] = {}
    all_idx: set[int] = set()
    for name, idxs in groups.items():
        idxset = set(idxs)
        all_idx |= idxset
        bm = src.copy()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in idxset], context='FACES')
        if not bm.faces:
            bm.free()
            log.warning("separate_by_material: no faces for %s", name)
            continue
        new_ob = to_object(name, bm, list(me.materials), smooth=True, sharp_angle_deg=40.0)
        new_ob.matrix_world = ob.matrix_world.copy()
        compact_materials(new_ob)
        out[name] = new_ob
    bmesh.ops.delete(src, geom=[f for f in src.faces if f.material_index in all_idx], context='FACES')
    src.to_mesh(me)
    src.free()
    me.update()
    compact_materials(ob)
    return out


def compact_materials(ob: bpy.types.Object) -> None:
    """Drop unused material slots and remap polygon indices (glTF exports only what is referenced anyway, but this
    keeps slot lists readable and the UE binding predictable)."""
    me = ob.data
    n = len(me.polygons)
    if n == 0 or len(me.materials) <= 1:
        return
    idx = np.empty(n, dtype=np.int32)
    me.polygons.foreach_get("material_index", idx)
    used = sorted(set(int(i) for i in np.unique(idx) if 0 <= i < len(me.materials)))
    if len(used) == len(me.materials):
        return
    mats = [me.materials[i] for i in used]
    remap = {old: new for new, old in enumerate(used)}
    new_idx = np.asarray([remap.get(int(i), 0) for i in idx], dtype=np.int32)
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", new_idx)
    me.update()


def set_origin(ob: bpy.types.Object, point: Vec3, rotation: Quaternion | Matrix | None = None) -> None:
    """Move the object's origin (pivot) to a world point (and optional orientation) without moving the geometry."""
    p = Vector(point)
    rot = Matrix.Identity(4)
    if rotation is not None:
        rot = rotation.to_matrix().to_4x4() if isinstance(rotation, Quaternion) else rotation.to_4x4()
    new_world = Matrix.Translation(p) @ rot
    delta = new_world.inverted() @ ob.matrix_world
    me = ob.data
    me.transform(delta)
    me.update()
    ob.matrix_world = new_world


def parent_to(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


def join(objects: Sequence[bpy.types.Object], name: str, *, smooth: bool = True, sharp_angle_deg: float | None = 40.0) -> bpy.types.Object:
    """Join mesh objects into one new object at the world origin, merging material slots by material identity."""
    mats: list[bpy.types.Material] = []
    out = bmesh.new()
    out_uv = out.loops.layers.uv.new("UVMap")
    for ob in objects:
        if ob.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.transform(bm, matrix=ob.matrix_world, verts=bm.verts)
        slot_map = []
        for m in ob.data.materials:
            if m not in mats:
                mats.append(m)
            slot_map.append(mats.index(m) if m is not None else 0)
        if not slot_map:
            slot_map = [0]
        uv_src = bm.loops.layers.uv.get("UVMap")
        vmap = {v: out.verts.new(v.co) for v in bm.verts}
        for f in bm.faces:
            try:
                nf = out.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = slot_map[min(f.material_index, len(slot_map) - 1)]
            nf.smooth = f.smooth
            if uv_src is not None:
                for a, b in zip(f.loops, nf.loops):
                    b[out_uv].uv = a[uv_src].uv
        bm.free()
    for ob in objects:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return to_object(name, out, mats, smooth=smooth, sharp_angle_deg=sharp_angle_deg)


def tri_count(ob: bpy.types.Object) -> int:
    if ob.type != "MESH":
        return 0
    me = ob.data
    n = len(me.polygons)
    if n == 0:
        return 0
    loops = np.empty(n, dtype=np.int32)
    me.polygons.foreach_get("loop_total", loops)
    return int((loops - 2).sum())


def tri_count_all(objects: Iterable[bpy.types.Object]) -> int:
    return sum(tri_count(o) for o in objects)


def bounds(objects: Iterable[bpy.types.Object]) -> tuple[Vector, Vector]:
    b = nb.bounds_of(list(objects))
    return Vector(b["min"]), Vector(b["max"])


def uv_project(ob: bpy.types.Object, fn: Callable[[Vector, Vector], tuple[float, float]]) -> None:
    """(Re)write the UV map from a per-loop function of (vertex position, face normal)."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers[0]
    n_loops = len(me.loops)
    if n_loops == 0:
        return
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lv = np.empty(n_loops, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    out = np.empty((n_loops, 2), dtype=np.float32)
    for poly in me.polygons:
        nrm = Vector(poly.normal)
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            out[li] = fn(Vector(co[lv[li]]), nrm)
    uv.data.foreach_set("uv", out.ravel())
    me.update()


def text_bm(text: str, *, size: float, depth: float = 0.001, font_path: str = FONT_SANS_BOLD, align: str = "CENTER",
            material_index: int = 0) -> bmesh.types.BMesh:
    """Text as a mesh in the XY plane (x right, y up, extruded +Z by depth). Caller transforms it into place."""
    font = bpy.data.fonts.get(font_path.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    if font is None:
        font = bpy.data.fonts.load(font_path, check_existing=True)
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = text
    cu.font = font
    cu.size = size
    cu.extrude = depth / 2 if depth > 0 else 0.0
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.fill_mode = 'BOTH'
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.curves.remove(cu)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces:
        f.material_index = material_index
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def text_on_surface_bm(text: str, *, size: float, depth: float, center: Vec3, normal: Vec3, up: Vec3 = (0, 0, 1),
                       font_path: str = FONT_SANS_BOLD, material_index: int = 0) -> bmesh.types.BMesh:
    """Text mesh placed at ``center`` facing ``normal`` with ``up`` as the text's up direction (badges, lettering)."""
    bm = text_bm(text, size=size, depth=depth, font_path=font_path, material_index=material_index)
    n = Vector(normal).normalized()
    u = Vector(up).normalized()
    u = (u - n * u.dot(n)).normalized()
    r = u.cross(n).normalized()  # text +X direction (reads left-to-right for a viewer facing -normal)
    m = Matrix(((r.x, u.x, n.x, center[0]), (r.y, u.y, n.y, center[1]), (r.z, u.z, n.z, center[2]), (0, 0, 0, 1)))
    return transform_bm(bm, m)


def convex_hull_bm(points: np.ndarray | Sequence[Vec3], *, simplify_deg: float = 4.0, max_points: int = 4000) -> bmesh.types.BMesh:
    """Convex hull of a point cloud as a closed triangle mesh (``UCX_`` collision proxies).

    Qhull (via ``scipy.spatial.ConvexHull``) is used when available because its output is exactly convex to
    floating-point precision; ``bmesh.ops.convex_hull`` leaves errors of up to ~10 mm on a car-sized cloud,
    which a strict plane-side convexity test rejects.  ``bmesh`` is the fallback.  ``simplify_deg`` > 0
    planar-dissolves the result, which is only safe when the caller does not need exact convexity.
    """
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    # weld coincident points first: qhull with "QJ" keeps duplicates as separate hull vertices, which yields
    # two co-located verts sharing hull faces and an edge-count that no longer reads as a closed manifold.
    pts = np.unique(np.round(pts, 6), axis=0)
    if len(pts) > max_points:
        rng = np.random.default_rng(7)
        pts = pts[rng.choice(len(pts), max_points, replace=False)]
    try:
        from scipy.spatial import ConvexHull, QhullError
    except ImportError:                                     # pragma: no cover - scipy is present here
        ConvexHull = None
    if len(pts) >= 4:
        # a slab of a thin part (a bicycle frame) can be coplanar; qhull refuses such input and bmesh
        # returns an open sheet, so inflate the cloud by 1 mm along its thinnest principal axis first.
        c = pts.mean(axis=0)
        try:
            _u, sv, vt = np.linalg.svd(pts - c, full_matrices=False)
            if sv[-1] < 2e-2 * max(1e-9, sv[0]):
                n = vt[-1]
                pts = np.concatenate([pts + n * 0.001, pts - n * 0.001])
        except np.linalg.LinAlgError:
            pass
    if ConvexHull is not None and len(pts) >= 4:
        try:
            # "QJ" joggles the input so every facet is simplicial: with the default "Qt" qhull merges
            # nearly-coplanar facets and the triangulated output can miss a face, leaving an open hull
            # (seen on the two-wheelers' rear slab).
            hull = ConvexHull(pts, qhull_options="QJ")
            bm = bmesh.new()
            verts = [bm.verts.new(tuple(p)) for p in pts]
            for tri, eq in zip(hull.simplices, hull.equations):
                a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
                n = np.cross(pts[b] - pts[a], pts[c] - pts[a])
                if np.dot(n, eq[:3]) < 0:                    # keep the winding outward
                    b, c = c, b
                try:
                    bm.faces.new((verts[a], verts[b], verts[c]))
                except ValueError:
                    continue
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            if any(len(e.link_faces) != 2 for e in bm.edges):
                raise RuntimeError("qhull produced an open hull")
            return bm
        except Exception as exc:                             # degenerate (coplanar) cloud
            log.warning("qhull failed (%s); falling back to bmesh.convex_hull", exc)
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    if simplify_deg > 0:
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(simplify_deg), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sync() -> None:
    """Flush pending object-transform edits into ``matrix_world``.

    ``ob.location = ...`` only writes the *local* transform; ``matrix_world`` keeps its stale value until the
    view layer is evaluated.  Every consumer of world positions (bounds, damage weights, convex hulls) must
    call this first or it silently measures wheels sitting at z = 0."""
    bpy.context.view_layer.update()


def mesh_points(ob: bpy.types.Object, world: bool = True) -> np.ndarray:
    me = ob.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    if world:
        m = np.asarray(ob.matrix_world)
        co = co @ m[:3, :3].T + m[:3, 3]
    return co


def mesh_normals(ob: bpy.types.Object) -> np.ndarray:
    me = ob.data
    n = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertex_normals.foreach_get("vector", n)
    return n.reshape(-1, 3)


def remove_object(ob: bpy.types.Object) -> None:
    me = ob.data if ob.type == "MESH" else None
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)
