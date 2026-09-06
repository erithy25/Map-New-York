"""Shared helpers for the *B* landmark scripts (bridges, WTC, Liberty, parks & monuments).

API mirrors the planned shared ``blender/landmarks/common.py`` (``load_footprint``, ``local_frame``, ``finish``,
``render_check``).  If that module exists and exposes compatible callables they are used for the footprint / export
steps (see :func:`_shared`); everything else here (materials, geometry primitives, catenaries, trusses, trees) is
B-lane code.

Frame convention (recorded in every glb's ``extras``): model X = east, Y = north (Blender Z-up), metres; model origin is
``origin_tm`` = (x, y, z) in NYC_TM / NAVD88 metres, i.e. a world point is ``origin_tm + local``.  Bridges use z = 0 at
NAVD88 0.0; published clearances quoted "above mean high water" are converted with MHW = NAVD88 + 0.70 m (NOAA
8518750 The Battery, MHW 4.53 ft vs NAVD88 2.24 ft above MLLW → 0.70 m).
"""
from __future__ import annotations

import fcntl
import inspect
import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

REPO = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
for _p in (REPO / "blender" / "common", REPO / "pipeline", REPO / "blender" / "landmarks"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import nycsim_bpy as nb  # noqa: E402
from nycsim_pipeline.crs import lonlat_to_tm, tm_to_lonlat  # noqa: E402,F401

log = logging.getLogger("landmarks.b")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

OUT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO / "blender_out")) / "landmarks"
CATALOG = OUT / "catalog"
VERIFY = REPO / "docs" / "verification" / "landmarks"
FOOTPRINTS = REPO / "data/processed/landmarks/candidate_footprints.parquet"
FOOTPRINTS_RAW = REPO / "data/processed/buildings/footprints_raw.parquet"
MHW_ABOVE_NAVD88_M = 0.70
FIDELITY_LANDMARK_MODEL = 1 << 7  # DATA_CONTRACTS §5.1 bit 7

# ----------------------------------------------------------------------------------------------- shared module bridge


def _shared(name: str, params: Sequence[str]) -> Callable | None:
    """Return ``common.<name>`` if blender/landmarks/common.py exists and its signature starts with ``params``."""
    try:
        import common as shared  # type: ignore
    except Exception:
        return None
    fn = getattr(shared, name, None)
    if not callable(fn):
        return None
    try:
        sig = list(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return None
    if sig[: len(params)] != list(params):
        log.info("shared common.%s has signature %s, using B implementation", name, sig)
        return None
    return fn


# ----------------------------------------------------------------------------------------------- footprints


@dataclass
class Footprint:
    bin: int
    name: str
    height: float
    ground_z: float
    cx: float
    cy: float
    geometry: object  # shapely (Multi)Polygon in NYC_TM
    source: str = "candidate_footprints.parquet"

    @property
    def ring(self) -> list[tuple[float, float]]:
        """Exterior ring of the largest polygon, CCW, closing point removed."""
        from shapely.geometry import MultiPolygon, Polygon
        from shapely.geometry.polygon import orient
        g = self.geometry
        if isinstance(g, MultiPolygon):
            g = max(g.geoms, key=lambda p: p.area)
        if not isinstance(g, Polygon):
            raise ValueError(f"footprint {self.bin} is not polygonal")
        g = orient(g, sign=1.0)
        return [(float(x), float(y)) for x, y in list(g.exterior.coords)[:-1]]


def load_footprint(bin_: int) -> Footprint:
    """Real OTI footprint for a BIN (NYC_TM polygon, LiDAR height/ground). Candidate set first, full set second."""
    fn = _shared("load_footprint", ("bin_",)) or _shared("load_footprint", ("bin",))
    if fn is not None:
        fp = fn(bin_)
        if isinstance(fp, Footprint):
            return fp
        if isinstance(fp, dict) and "geometry" in fp:
            return Footprint(int(fp["bin"]), str(fp.get("name") or ""), float(fp["height"]), float(fp["ground_z"]),
                             float(fp["cx"]), float(fp["cy"]), fp["geometry"], source="common.load_footprint")
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from shapely import wkb
    cols = ["bin", "name", "height", "ground_z", "cx", "cy", "geometry"]
    for path in (FOOTPRINTS, FOOTPRINTS_RAW):
        if not path.exists():
            continue
        t = pq.read_table(path, columns=cols, filters=[("bin", "==", int(bin_))])
        if t.num_rows == 0:
            continue
        r = t.slice(0, 1).to_pylist()[0]
        geom = wkb.loads(r["geometry"])
        gz = r["ground_z"]
        if gz is None or (isinstance(gz, float) and math.isnan(gz)):
            gz = 0.0
        return Footprint(int(r["bin"]), r["name"] or "", float(r["height"] or 0.0), float(gz), float(r["cx"]), float(r["cy"]), geom, source=path.name)
    raise KeyError(f"BIN {bin_} not found in {FOOTPRINTS.name} or {FOOTPRINTS_RAW.name}")


def footprint_heading(fp: Footprint) -> float:
    """Compass heading (deg, 0 = north, clockwise) of the longest edge of the footprint's minimum rotated rectangle."""
    mrr = fp.geometry.minimum_rotated_rectangle
    pts = list(mrr.exterior.coords)
    best = None
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if best is None or L > best[0]:
            best = (L, math.degrees(math.atan2(x1 - x0, y1 - y0)) % 180.0)
    return best[1] if best else 0.0


# ----------------------------------------------------------------------------------------------- local frame


@dataclass
class LocalFrame:
    """Model-local frame: origin in NYC_TM (x, y) and NAVD88 z; axes east/north/up (no rotation)."""
    x0: float
    y0: float
    z0: float = 0.0
    heading_deg: float = 0.0  # informational (principal axis of the landmark), the frame itself is not rotated

    def to_local(self, x: float, y: float, z: float = 0.0) -> tuple[float, float, float]:
        return (x - self.x0, y - self.y0, z - self.z0)

    def from_lonlat(self, lon: float, lat: float, z: float = 0.0) -> tuple[float, float, float]:
        x, y = lonlat_to_tm(lon, lat)
        return self.to_local(float(x), float(y), z)

    def to_world(self, lx: float, ly: float, lz: float = 0.0) -> tuple[float, float, float]:
        return (lx + self.x0, ly + self.y0, lz + self.z0)

    @property
    def origin_tm(self) -> list[float]:
        return [self.x0, self.y0, self.z0]


def local_frame(origin_xy: Sequence[float] | Footprint, z0: float | None = None, heading_deg: float | None = None) -> LocalFrame:
    """Frame from a footprint (centroid + LiDAR ground) or an explicit (x, y) in NYC_TM."""
    fn = _shared("local_frame", ("origin_xy",))
    if fn is not None:
        lf = fn(origin_xy, z0, heading_deg) if heading_deg is not None else fn(origin_xy, z0)
        if isinstance(lf, LocalFrame):
            return lf
    if isinstance(origin_xy, Footprint):
        return LocalFrame(origin_xy.cx, origin_xy.cy, origin_xy.ground_z if z0 is None else z0,
                          footprint_heading(origin_xy) if heading_deg is None else heading_deg)
    x, y = float(origin_xy[0]), float(origin_xy[1])
    return LocalFrame(x, y, 0.0 if z0 is None else z0, heading_deg or 0.0)


def frame_from_lonlat(lon: float, lat: float, z0: float = 0.0, heading_deg: float = 0.0) -> LocalFrame:
    x, y = lonlat_to_tm(lon, lat)
    return LocalFrame(float(x), float(y), z0, heading_deg)


# ----------------------------------------------------------------------------------------------- materials

# Documented Principled colours (linear RGB). No textures module exists in blender/common at the time of writing;
# every material below records the real-world reference it approximates.
MATERIALS: dict[str, dict] = {
    # masonry
    "granite_gray": dict(base_color=(0.44, 0.42, 0.39, 1), roughness=0.85, ref="Maine/Rockland granite, Brooklyn Bridge towers"),
    "granite_dark": dict(base_color=(0.36, 0.35, 0.33, 1), roughness=0.85, ref="Stony Creek/quarry-faced granite, Grant's Tomb base, forts"),
    "granite_pink": dict(base_color=(0.62, 0.52, 0.47, 1), roughness=0.8, ref="Stony Creek pink granite, Statue of Liberty pedestal"),
    "limestone": dict(base_color=(0.70, 0.66, 0.57, 1), roughness=0.8, ref="Indiana limestone"),
    "marble_white": dict(base_color=(0.86, 0.85, 0.80, 1), roughness=0.55, ref="Tuckahoe marble, Washington Square Arch"),
    "brownstone": dict(base_color=(0.42, 0.27, 0.19, 1), roughness=0.9, ref="Central Park perimeter wall brownstone"),
    "schist": dict(base_color=(0.45, 0.43, 0.38, 1), roughness=0.95, ref="Manhattan schist (Belvedere Castle, park walls)"),
    "sandstone_red": dict(base_color=(0.55, 0.30, 0.22, 1), roughness=0.9, ref="New Brunswick sandstone, Bethesda Terrace"),
    "brick_red": dict(base_color=(0.48, 0.22, 0.16, 1), roughness=0.9, ref="Red brick (Ellis Island, Castle Williams interior)"),
    "concrete": dict(base_color=(0.55, 0.54, 0.51, 1), roughness=0.9, ref="Cast concrete piers/anchorages"),
    "concrete_dark": dict(base_color=(0.42, 0.42, 0.41, 1), roughness=0.95, ref="Weathered concrete"),
    # metals
    "steel_gray": dict(base_color=(0.55, 0.56, 0.58, 1), roughness=0.55, metallic=0.6, ref="Aluminium-gray painted steel (Williamsburg, GWB, Verrazzano)"),
    "steel_silver": dict(base_color=(0.70, 0.71, 0.72, 1), roughness=0.4, metallic=0.8, ref="Galvanised/painted cable wrap (Brooklyn Bridge cables)"),
    "steel_blue": dict(base_color=(0.28, 0.40, 0.58, 1), roughness=0.55, metallic=0.5, ref="Manhattan Bridge blue"),
    "steel_tan": dict(base_color=(0.62, 0.55, 0.42, 1), roughness=0.6, metallic=0.4, ref="Queensboro Bridge tan"),
    "steel_red": dict(base_color=(0.45, 0.14, 0.11, 1), roughness=0.6, metallic=0.4, ref="Hell Gate red / Pulaski maroon"),
    "steel_white": dict(base_color=(0.85, 0.86, 0.87, 1), roughness=0.5, metallic=0.4, ref="Kosciuszko Bridge white towers/stays"),
    "steel_black": dict(base_color=(0.05, 0.05, 0.05, 1), roughness=0.5, metallic=0.5, ref="Black-painted ironwork (railings, lamps)"),
    "steel_green": dict(base_color=(0.18, 0.32, 0.26, 1), roughness=0.6, metallic=0.4, ref="Park-green painted steel (High Bridge, Bow Bridge)"),
    "stainless": dict(base_color=(0.80, 0.81, 0.82, 1), roughness=0.25, metallic=1.0, ref="Stainless steel (Unisphere, One WTC spire)"),
    "copper_patina": dict(base_color=(0.30, 0.55, 0.48, 1), roughness=0.7, metallic=0.1, ref="Verdigris copper (Statue of Liberty, Ellis Island domes)"),
    "copper_new": dict(base_color=(0.72, 0.45, 0.20, 1), roughness=0.4, metallic=1.0, ref="Bright copper"),
    "gold_leaf": dict(base_color=(1.0, 0.78, 0.25, 1), roughness=0.3, metallic=1.0, emission=(1.0, 0.75, 0.2, 1), emission_strength=6.0, ref="Gold-leafed torch flame (emissive)"),
    "bronze": dict(base_color=(0.42, 0.30, 0.16, 1), roughness=0.45, metallic=0.9, ref="Bronze (memorial parapets, statues)"),
    "bronze_green": dict(base_color=(0.36, 0.42, 0.30, 1), roughness=0.6, metallic=0.4, ref="Patinated bronze (Angel of the Waters, Columbus)"),
    # surfaces
    "asphalt": dict(base_color=(0.09, 0.09, 0.09, 1), roughness=0.95, ref="Roadway asphalt"),
    "asphalt_light": dict(base_color=(0.16, 0.16, 0.16, 1), roughness=0.95, ref="Worn asphalt / concrete deck"),
    "lane_white": dict(base_color=(0.85, 0.85, 0.82, 1), roughness=0.7, ref="Thermoplastic lane marking"),
    "lane_yellow": dict(base_color=(0.85, 0.65, 0.10, 1), roughness=0.7, ref="Yellow centre line"),
    "sidewalk": dict(base_color=(0.62, 0.61, 0.58, 1), roughness=0.95, ref="Concrete sidewalk"),
    "wood_deck": dict(base_color=(0.45, 0.33, 0.20, 1), roughness=0.8, ref="Ipe/pine boardwalk & promenade planks"),
    "wood_pale": dict(base_color=(0.62, 0.52, 0.36, 1), roughness=0.8, ref="Unpainted pine (Cyclone structure)"),
    "tile_white": dict(base_color=(0.88, 0.88, 0.86, 1), roughness=0.25, ref="Glazed tunnel wall tile"),
    "tile_dark": dict(base_color=(0.10, 0.12, 0.10, 1), roughness=0.4, ref="Dark tunnel tile band / ceiling"),
    "glass": dict(base_color=(0.55, 0.65, 0.72, 1), roughness=0.05, metallic=0.4, ref="Insulated low-iron glazing (blue-gray reflective)"),
    "glass_clear": dict(base_color=(0.75, 0.80, 0.84, 1), roughness=0.05, metallic=0.2, alpha=0.5, ref="Clear glass (Oculus, canopies)"),
    "glass_dark": dict(base_color=(0.12, 0.16, 0.20, 1), roughness=0.08, metallic=0.5, ref="Dark curtain wall (2 WTC stub, 7 WTC)"),
    "water": dict(base_color=(0.10, 0.20, 0.25, 1), roughness=0.05, metallic=0.2, ref="Memorial pool water"),
    "water_dark": dict(base_color=(0.05, 0.10, 0.14, 1), roughness=0.05, metallic=0.2, ref="Harbour water (render context only)"),
    "grass": dict(base_color=(0.15, 0.30, 0.10, 1), roughness=1.0, ref="Lawn"),
    "foliage": dict(base_color=(0.12, 0.28, 0.08, 1), roughness=0.9, ref="Swamp white oak / London plane canopy"),
    "bark": dict(base_color=(0.30, 0.24, 0.18, 1), roughness=0.95, ref="Tree bark"),
    "paint_white": dict(base_color=(0.85, 0.85, 0.83, 1), roughness=0.5, ref="White-painted timber/steel"),
    "paint_red": dict(base_color=(0.65, 0.10, 0.08, 1), roughness=0.5, ref="Coney Island red (Wonder Wheel cars, Nathan's)"),
    "paint_yellow": dict(base_color=(0.95, 0.75, 0.10, 1), roughness=0.5, ref="Coney Island yellow (Nathan's sign, Cyclone cars)"),
    "paint_green": dict(base_color=(0.10, 0.45, 0.20, 1), roughness=0.5, ref="Painted green"),
    "paint_blue": dict(base_color=(0.10, 0.25, 0.60, 1), roughness=0.5, ref="Painted blue (Wonder Wheel cars)"),
    "light_warm": dict(base_color=(1.0, 0.9, 0.7, 1), emission=(1.0, 0.85, 0.6, 1), emission_strength=8.0, roughness=0.3, ref="Sodium/LED luminaire (emissive)"),
    "light_cool": dict(base_color=(0.9, 0.95, 1.0, 1), emission=(0.85, 0.92, 1.0, 1), emission_strength=6.0, roughness=0.3, ref="Fluorescent/LED tunnel light (emissive)"),
    "memorial_names": dict(base_color=(0.35, 0.25, 0.14, 1), roughness=0.5, metallic=0.8, ref="Texture slot MEMORIAL_NAMES: bronze parapet with incised names (UE material slot)"),
    "minton_tile": dict(base_color=(0.55, 0.40, 0.25, 1), roughness=0.4, emission=(0.6, 0.45, 0.3, 1), emission_strength=0.6, ref="Texture slot MINTON_TILE: Bethesda arcade encaustic tile ceiling (lit)"),
    "cabin_red": dict(base_color=(0.70, 0.12, 0.10, 1), roughness=0.45, metallic=0.3, ref="Roosevelt Island tram cabin red"),
}


def mat(name: str) -> bpy.types.Material:
    """Principled material from the documented table (created once per scene)."""
    spec = MATERIALS[name]
    m = bpy.data.materials.get(f"b_{name}")
    if m is not None:
        return m
    kw = {k: v for k, v in spec.items() if k != "ref"}
    m = nb.pbr_material(f"b_{name}", **kw)
    m["nycsim_ref"] = spec["ref"]
    return m


# ----------------------------------------------------------------------------------------------- geometry primitives


def rot_z(deg: float) -> Matrix:
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def heading_to_math_deg(heading_deg: float) -> float:
    """Compass heading (0 = north, CW) -> mathematical angle (0 = east, CCW)."""
    return (90.0 - heading_deg) % 360.0


def transform(ob: bpy.types.Object, m: Matrix) -> bpy.types.Object:
    """Bake a matrix into the mesh data (keeps object transform identity)."""
    ob.data.transform(m)
    ob.data.update()
    return ob


def join(objects: Sequence[bpy.types.Object], name: str) -> bpy.types.Object:
    """Join meshes into one object (materials merged), returning the joined object. Empty lists raise."""
    objects = [o for o in objects if o is not None and o.type == "MESH"]
    if not objects:
        raise ValueError(f"join({name}): nothing to join")
    if len(objects) == 1:
        objects[0].name = name
        return objects[0]
    bm = bmesh.new()
    me = bpy.data.meshes.new(name)
    mats: list[bpy.types.Material] = []
    for o in objects:
        base = len(mats)
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
        remap = {i: mats.index(m) for i, m in enumerate(o.data.materials)}
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        tmp.transform(o.matrix_world)
        for f in tmp.faces:
            f.material_index = remap.get(f.material_index, 0)
        tmp_me = bpy.data.meshes.new("_tmp")
        tmp.to_mesh(tmp_me)
        tmp.free()
        bm.from_mesh(tmp_me)
        bpy.data.meshes.remove(tmp_me)
        _ = base
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    me.update()
    ob = bpy.data.objects.new(name, me)
    nb.link(ob)
    for o in objects:
        old = o.data
        bpy.data.objects.remove(o)
        if old.users == 0:
            bpy.data.meshes.remove(old)
    return ob


def tri_count(objects: Iterable[bpy.types.Object]) -> int:
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in objects:
        if o.type != "MESH":
            continue
        me = o.evaluated_get(dg).to_mesh() if o.modifiers else o.data
        n += sum(max(len(p.vertices) - 2, 0) for p in me.polygons)
    return n


def box(name: str, size, origin=(0, 0, 0), material: str | None = None, anchor: str = "bottom") -> bpy.types.Object:
    return nb.box(name, size, origin, material=mat(material) if material else None, anchor=anchor)


def box_between(name: str, p0, p1, w: float, h: float, material: str, roll_up=(0, 0, 1)) -> bpy.types.Object:
    """Rectangular bar (w across, h up) whose axis runs from p0 to p1 (3-D). Used for truss members, cables, rails."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        raise ValueError(f"box_between({name}): zero length")
    ob = nb.box(name, (L, w, h), (L / 2, 0, 0), material=mat(material), anchor="center")
    axis = d.normalized()
    up = Vector(roll_up)
    if abs(axis.dot(up)) > 0.999:
        up = Vector((0, 1, 0))
    side = axis.cross(up).normalized()
    up2 = side.cross(axis).normalized()
    m = Matrix((axis, side, up2)).transposed().to_4x4()
    m.translation = p0
    return transform(ob, m)


def cylinder_between(name: str, p0, p1, r: float, material: str, segments: int = 8, cap: bool = False) -> bpy.types.Object:
    """Cylinder from p0 to p1 (3-D)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        raise ValueError(f"cylinder_between({name}): zero length")
    ob = nb.cylinder(name, r, L, segments, (0, 0, 0), material=mat(material), cap=cap)
    q = d.normalized().to_track_quat("Z", "Y")
    m = q.to_matrix().to_4x4()
    m.translation = p0
    return transform(ob, m)


def tube_along(name: str, points: Sequence[Sequence[float]], radius: float, material: str, segments: int = 8, cap: bool = True) -> bpy.types.Object:
    """Continuous tube following a 3-D polyline (rings joined; no gaps at bends). Cables, pipes, rails, coaster track."""
    pts = [Vector(p) for p in points]
    if len(pts) < 2:
        raise ValueError(f"tube_along({name}): need >= 2 points")
    bm = bmesh.new()
    rings = []
    prev_side = None
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1:
            t = (pts[-1] - pts[-2]).normalized()
        else:
            t = ((pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized())
            t = t.normalized() if t.length > 1e-9 else (pts[i + 1] - pts[i]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.99 else Vector((0, 1, 0))
        side = t.cross(up).normalized()
        if prev_side is not None and side.dot(prev_side) < 0:
            side = -side
        prev_side = side
        up2 = side.cross(t).normalized()
        ring = []
        for k in range(segments):
            a = 2 * math.pi * k / segments
            ring.append(bm.verts.new(p + radius * (math.cos(a) * side + math.sin(a) * up2)))
        rings.append(ring)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for k in range(segments):
            k1 = (k + 1) % segments
            bm.faces.new((r0[k], r0[k1], r1[k1], r1[k]))
    if cap:
        bm.faces.new(tuple(reversed(rings[0])))
        bm.faces.new(tuple(rings[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = nb.bmesh_to_object(name, bm, materials=[mat(material)])
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def prism(name: str, ring: Sequence[Sequence[float]], z0: float, z1: float, material: str, holes=(), cap_bottom: bool = True) -> bpy.types.Object:
    """Vertical prism from a CCW 2-D ring (nb.extrude_polygon with metre UVs)."""
    if z1 <= z0:
        raise ValueError(f"prism({name}): z1 must exceed z0 ({z0}, {z1})")
    return nb.extrude_polygon(name, ring, z0, z1, holes, material=mat(material), cap_bottom=cap_bottom)


def profile_extrude(name: str, ring_uv: Sequence[Sequence[float]], thickness: float, material: str, holes=(), matrix: Matrix | None = None,
                    plane: str = "xz") -> bpy.types.Object:
    """Extrude a 2-D profile drawn in a vertical plane. ``plane='xz'``: u = X, v = Z, extruded along +Y by ``thickness``
    (centred: Y in [-t/2, t/2]); ``plane='yz'``: u = Y, v = Z, extruded along X.  Optional ``matrix`` applied after."""
    ob = nb.extrude_polygon(name, ring_uv, -thickness / 2, thickness / 2, holes, material=mat(material))
    if plane == "xz":
        m = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # (u, v, w) -> (u, -w, v)
    elif plane == "yz":
        m = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # (u, v, w) -> (w, u, v)
    else:
        raise ValueError(plane)
    transform(ob, m)
    if matrix is not None:
        transform(ob, matrix)
    return ob


def regular_polygon(n: int, r: float, cx: float = 0.0, cy: float = 0.0, phase: float = 0.0) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(phase + 2 * math.pi * i / n), cy + r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]


def rect(w: float, d: float, cx: float = 0.0, cy: float = 0.0) -> list[tuple[float, float]]:
    return [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]


def pointed_arch(width: float, height: float, cx: float = 0.0, z0: float = 0.0, n: int = 12) -> list[tuple[float, float]]:
    """Equilateral-ish Gothic pointed arch outline (u, v), CCW: two circular arcs meeting at the apex."""
    r = width  # two-centred arch, centres at the opposite springing points -> equilateral
    apex_rise = math.sqrt(r * r - (width / 2) ** 2)
    spring = height - apex_rise
    if spring < 0:
        # shallower arch: use radius from apex geometry
        spring = 0.0
        r = (width ** 2 / 4 + height ** 2) / (2 * height) if height > 0 else width / 2
        apex_rise = height
    pts = [(cx - width / 2, z0), (cx + width / 2, z0), (cx + width / 2, z0 + spring)]
    # right arc: centre at left springing point
    c_r = (cx - width / 2 + (width - r) if spring == 0.0 else cx - width / 2, z0 + spring)
    if spring > 0:
        a0 = 0.0
        a1 = math.atan2(apex_rise, width / 2)
        for i in range(1, n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((c_r[0] + r * math.cos(a), c_r[1] + r * math.sin(a)))
        c_l = (cx + width / 2, z0 + spring)
        a0 = math.pi - math.atan2(apex_rise, width / 2)
        a1 = math.pi
        for i in range(1, n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((c_l[0] + r * math.cos(a), c_l[1] + r * math.sin(a)))
    else:
        # single segmental arch through the three points
        cz = z0 + height - r
        a_end = math.atan2(height - (height - r), width / 2)
        a0 = math.atan2(z0 - cz, width / 2)
        a1 = math.pi - a0
        for i in range(1, 2 * n):
            a = a0 + (a1 - a0) * i / (2 * n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
        _ = a_end
    pts.append((cx - width / 2, z0 + spring))
    # remove consecutive duplicates
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    if math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    return out


def round_arch(width: float, height: float, cx: float = 0.0, z0: float = 0.0, n: int = 16) -> list[tuple[float, float]]:
    """Semicircular (or segmental if height < width/2 … or stilted if taller) arch outline, CCW."""
    r = width / 2
    spring = max(height - r, 0.0)
    pts = [(cx - r, z0), (cx + r, z0), (cx + r, z0 + spring)]
    for i in range(1, n):
        a = math.pi * i / n
        pts.append((cx + r * math.cos(a), z0 + spring + r * math.sin(a)))
    pts.append((cx - r, z0 + spring))
    return pts


def catenary_points(x0: float, z0: float, x1: float, z1: float, sag: float, n: int = 48) -> list[tuple[float, float]]:
    """True catenary z = a·cosh((x−xm)/a) + c through (x0,z0),(x1,z1) with the given mid-sag below the chord midpoint.
    Solved by bisection on ``a`` for the symmetric case and Newton on the offset for unequal ends.  Returns (x, z)."""
    if x1 <= x0:
        raise ValueError("catenary: x1 must exceed x0")
    if sag <= 0:
        raise ValueError("catenary: sag must be positive")
    L = x1 - x0
    # symmetric catenary with span L and sag s: s = a (cosh(L/2a) - 1)  -> solve for a
    lo, hi = 1e-3, 1e7
    for _ in range(200):
        a = math.sqrt(lo * hi)
        s = a * (math.cosh(L / (2 * a)) - 1)
        if s > sag:
            lo = a
        else:
            hi = a
    a = math.sqrt(lo * hi)
    # unequal ends: shift the vertex so both end points lie on the curve (same a -> same horizontal tension)
    # z(x) = a cosh((x - xm)/a) + c ; z1 - z0 = a[cosh((x1-xm)/a) - cosh((x0-xm)/a)] monotonic in xm
    dz = z1 - z0
    lo_m, hi_m = x0 - 2 * L, x1 + 2 * L
    for _ in range(200):
        xm = 0.5 * (lo_m + hi_m)
        f = a * (math.cosh((x1 - xm) / a) - math.cosh((x0 - xm) / a)) - dz
        if f > 0:
            lo_m = xm
        else:
            hi_m = xm
    xm = 0.5 * (lo_m + hi_m)
    c = z0 - a * math.cosh((x0 - xm) / a)
    return [(x0 + L * i / n, a * math.cosh((x0 + L * i / n - xm) / a) + c) for i in range(n + 1)]


def catenary_z(pts: Sequence[tuple[float, float]], x: float) -> float:
    """Linear interpolation of a catenary polyline at x."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    lo, hi = 0, len(pts) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pts[mid][0] <= x:
            lo = mid
        else:
            hi = mid
    (xa, za), (xb, zb) = pts[lo], pts[hi]
    return za + (zb - za) * (x - xa) / (xb - xa)


def lattice_column(name: str, base, top, w0: float, w1: float, material: str, panels: int, member: float = 0.35, x_brace: bool = True) -> bpy.types.Object:
    """Steel lattice column: 4 corner chords tapering from width w0 (base) to w1 (top), horizontal struts and X-bracing
    on all four faces. base/top are the axis end points (3-D)."""
    base, top = Vector(base), Vector(top)
    axis = (top - base)
    H = axis.length
    n = axis.normalized()
    side = n.cross(Vector((0, 0, 1))).normalized() if abs(n.z) < 0.99 else Vector((1, 0, 0))
    fwd = side.cross(n).normalized()
    parts = []

    def corner(t, i):
        w = w0 + (w1 - w0) * t
        sx, sy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[i]
        return base + n * (H * t) + side * (sx * w / 2) + fwd * (sy * w / 2)

    for i in range(4):
        parts.append(box_between(f"{name}_chord{i}", corner(0, i), corner(1, i), member, member, material))
    for k in range(panels + 1):
        t = k / panels
        for i in range(4):
            parts.append(box_between(f"{name}_strut{k}_{i}", corner(t, i), corner(t, (i + 1) % 4), member * 0.7, member * 0.7, material))
    if x_brace:
        for k in range(panels):
            t0, t1 = k / panels, (k + 1) / panels
            for i in range(4):
                j = (i + 1) % 4
                parts.append(box_between(f"{name}_xa{k}_{i}", corner(t0, i), corner(t1, j), member * 0.5, member * 0.5, material))
                parts.append(box_between(f"{name}_xb{k}_{i}", corner(t0, j), corner(t1, i), member * 0.5, member * 0.5, material))
    return join(parts, name)


def truss_girder(name: str, p0, p1, depth: float, width: float, panel: float, material: str, chord: float = 0.6, web: float = 0.35,
                 kind: str = "warren") -> bpy.types.Object:
    """Through/deck truss between p0 and p1 (axis at the bottom chord centre). Two vertical truss planes ``width`` apart,
    top/bottom chords, verticals and diagonals (Warren or Pratt), top and bottom lateral bracing."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1.0:
        raise ValueError(f"truss_girder({name}): length {L:.2f} m is degenerate")
    ax = d.normalized()
    side = ax.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    n = max(int(round(L / panel)), 1)
    parts = []
    for s in (-1, 1):
        off = side * (s * width / 2)
        parts.append(box_between(f"{name}_bc{s}", p0 + off, p1 + off, chord, chord, material))
        parts.append(box_between(f"{name}_tc{s}", p0 + off + up * depth, p1 + off + up * depth, chord, chord, material))
        for k in range(n + 1):
            a = p0 + ax * (L * k / n) + off
            if kind == "pratt" or k in (0, n):
                parts.append(box_between(f"{name}_v{s}_{k}", a, a + up * depth, web, web, material))
        for k in range(n):
            a = p0 + ax * (L * k / n) + off
            b = p0 + ax * (L * (k + 1) / n) + off
            if kind == "warren":
                if k % 2 == 0:
                    parts.append(box_between(f"{name}_d{s}_{k}", a, b + up * depth, web, web, material))
                else:
                    parts.append(box_between(f"{name}_d{s}_{k}", a + up * depth, b, web, web, material))
            else:  # pratt: diagonals slope towards mid-span
                if k < n / 2:
                    parts.append(box_between(f"{name}_d{s}_{k}", a + up * depth, b, web, web, material))
                else:
                    parts.append(box_between(f"{name}_d{s}_{k}", a, b + up * depth, web, web, material))
    for k in range(n + 1):
        a = p0 + ax * (L * k / n)
        parts.append(box_between(f"{name}_lb{k}", a - side * width / 2, a + side * width / 2, web, web, material))
        parts.append(box_between(f"{name}_lt{k}", a - side * width / 2 + up * depth, a + side * width / 2 + up * depth, web, web, material))
    return join(parts, name)


def railing(name: str, p0, p1, height: float = 1.1, post_spacing: float = 2.5, material: str = "steel_black", rails: int = 3) -> bpy.types.Object:
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    ax = (p1 - p0).normalized()
    parts = []
    n = max(int(L / post_spacing), 1)
    for k in range(n + 1):
        a = p0 + ax * (L * k / n)
        parts.append(box_between(f"{name}_p{k}", a, a + Vector((0, 0, height)), 0.06, 0.06, material))
    for r in range(1, rails + 1):
        z = height * r / rails
        parts.append(box_between(f"{name}_r{r}", p0 + Vector((0, 0, z)), p1 + Vector((0, 0, z)), 0.05, 0.05, material))
    return join(parts, name)


def lamp_post(name: str, base, height: float = 9.0, arm: float = 1.8, heading_math_deg: float = 0.0, material: str = "steel_black") -> bpy.types.Object:
    b = Vector(base)
    parts = [nb.cylinder(f"{name}_pole", 0.09, height, 8, b, material=mat(material))]
    d = Vector((math.cos(math.radians(heading_math_deg)), math.sin(math.radians(heading_math_deg)), 0))
    top = b + Vector((0, 0, height))
    parts.append(cylinder_between(f"{name}_arm", top, top + d * arm + Vector((0, 0, 0.3)), 0.05, material, 6))
    parts.append(box(f"{name}_lum", (0.6, 0.3, 0.2), top + d * arm + Vector((0, 0, 0.2)), "light_warm", anchor="center"))
    return join(parts, name)


def simple_tree(name: str, base, height: float = 9.0, crown_r: float = 3.5, trunk_r: float = 0.22) -> bpy.types.Object:
    """Low-poly deciduous tree (trunk + 3 ellipsoid crown lobes), ~250 tris. Used where no prop library exists."""
    b = Vector(base)
    parts = [nb.cylinder(f"{name}_trunk", trunk_r, height * 0.45, 7, b, material=mat("bark"))]
    import random
    rng = random.Random(hash(name) & 0xFFFF)
    for i in range(3):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=crown_r * (0.75 + 0.25 * rng.random()))
        off = Vector((rng.uniform(-0.4, 0.4) * crown_r, rng.uniform(-0.4, 0.4) * crown_r, height * 0.45 + crown_r * (0.6 + 0.5 * i / 2)))
        bmesh.ops.scale(bm, verts=bm.verts, vec=Vector((1.0, 1.0, 0.8)))
        bmesh.ops.translate(bm, verts=bm.verts, vec=b + off)
        parts.append(nb.bmesh_to_object(f"{name}_crown{i}", bm, materials=[mat("foliage")]))
    ob = join(parts, name)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def ground_plane(name: str, size: float, z: float, material: str, center=(0, 0)) -> bpy.types.Object:
    return nb.mesh_object(name, [(center[0] - size, center[1] - size, z), (center[0] + size, center[1] - size, z),
                                 (center[0] + size, center[1] + size, z), (center[0] - size, center[1] + size, z)], [(0, 1, 2, 3)],
                          materials=[mat(material)])


def lane_markings(name: str, p0, p1, lane_w: float, n_lanes: int, z: float, material_edge: str = "lane_white", centre_yellow: bool = True,
                  dash: float = 3.0, gap: float = 9.0, offset_t: float = 0.0) -> bpy.types.Object | None:
    """Lane lines along axis p0->p1 (2-D or 3-D points): NYC standard 10 ft dash / 30 ft gap white lane lines, solid
    edge lines, double yellow at the centre when two-way. ``offset_t`` shifts the roadway centre across the axis."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0)
    L = ax.length
    ax.normalize()
    side = ax.cross(Vector((0, 0, 1))).normalized()
    half = lane_w * n_lanes / 2
    parts = []
    for i in range(n_lanes + 1):
        t = -half + i * lane_w + offset_t
        a = p0 + side * t + Vector((0, 0, z))
        b = p1 + side * t + Vector((0, 0, z))
        if i in (0, n_lanes):
            parts.append(box_between(f"{name}_e{i}", a, b, 0.15, 0.01, material_edge))
        elif centre_yellow and n_lanes % 2 == 0 and i == n_lanes // 2:
            parts.append(box_between(f"{name}_y0", a + side * 0.15, b + side * 0.15, 0.12, 0.01, "lane_yellow"))
            parts.append(box_between(f"{name}_y1", a - side * 0.15, b - side * 0.15, 0.12, 0.01, "lane_yellow"))
        else:
            s = 0.0
            k = 0
            while s < L:
                e = min(s + dash, L)
                parts.append(box_between(f"{name}_d{i}_{k}", a + ax * s, a + ax * e, 0.12, 0.01, material_edge))
                s += dash + gap
                k += 1
    return join(parts, name) if parts else None


# ----------------------------------------------------------------------------------------------- scene / export


def new_scene() -> None:
    nb.reset_scene()


def all_mesh_objects() -> list[bpy.types.Object]:
    return [o for o in bpy.data.objects if o.type == "MESH"]


def _record_processed(artifact_id: str, path: Path, sources: list[str], extra: dict) -> None:
    """manifest.record_processed under an advisory lock (shared JSON; other agents may write concurrently)."""
    try:
        from nycsim_pipeline import manifest
        lock = manifest.MANIFEST / ".processed.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with open(lock, "w") as lf:
            # non-blocking with a bounded retry: other agents write the same shared manifest and a stuck holder
            # must never wedge a landmark build
            deadline = time.time() + 30.0
            got = False
            while time.time() < deadline:
                try:
                    fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    got = True
                    break
                except BlockingIOError:
                    time.sleep(0.4)
            if not got:
                log.warning("manifest lock busy for 30 s; skipping record_processed(%s)", artifact_id)
                return
            try:
                manifest.record_processed(artifact_id, path, stage="landmarks_b", sources=sources, rows=None, schema="glb", extra=extra)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception as e:  # manifest is shared infrastructure; never fail an export because of it
        log.warning("record_processed(%s) failed: %s", artifact_id, e)


def finish(objects: Sequence[bpy.types.Object], landmark_id: str, bins: Sequence[int], extras: dict, *, lod: int = 0,
           budget_tris: int | None = None) -> dict:
    """Export ``objects`` as ``blender_out/landmarks/<id>.glb`` (LOD1: ``<id>_lod1.glb``) and merge the catalog entry
    ``blender_out/landmarks/catalog/<id>.json``.  ``extras`` must carry origin_tm, heading_deg, height_m,
    fidelity_statement (DATA_CONTRACTS §13 + brief).  Returns the LOD record (path, tris, bytes, bounds)."""
    fn = _shared("finish", ("objects", "landmark_id", "bins", "extras"))
    required = ("origin_tm", "heading_deg", "height_m", "fidelity_statement")
    missing = [k for k in required if k not in extras]
    if missing:
        raise ValueError(f"finish({landmark_id}): extras missing {missing}")
    objects = [o for o in objects if o is not None and o.type == "MESH"]
    if not objects:
        raise ValueError(f"finish({landmark_id}): no mesh objects")
    tris = tri_count(objects)
    if budget_tris is not None and tris > budget_tris:
        raise RuntimeError(f"{landmark_id} LOD{lod}: {tris} triangles exceeds budget {budget_tris}")
    bounds = nb.bounds_of(objects)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (f"{landmark_id}.glb" if lod == 0 else f"{landmark_id}_lod{lod}.glb")
    glb_extras = {"landmark_id": landmark_id, "bins": [int(b) for b in bins], "lod": lod, "triangles": tris, "bounds": bounds,
                  "fidelity_bits": FIDELITY_LANDMARK_MODEL, **extras}
    if fn is not None and lod == 0:
        try:
            fn(objects, landmark_id, list(bins), glb_extras)
        except Exception as e:
            log.warning("shared common.finish failed (%s); falling back to B export", e)
            nb.export_glb(path, objects=objects, extras=glb_extras)
    else:
        nb.export_glb(path, objects=objects, extras=glb_extras)
    if not path.exists():
        # shared finish may have chosen its own name; make sure our contract path exists too
        nb.export_glb(path, objects=objects, extras=glb_extras)
    from nycsim_pipeline.manifest import sha256_of
    rec = {"path": str(path.relative_to(REPO)), "triangles": tris, "bytes": path.stat().st_size, "bounds": bounds, "sha256": sha256_of(path),
           "objects": len(objects)}
    CATALOG.mkdir(parents=True, exist_ok=True)
    cpath = CATALOG / f"{landmark_id}.json"
    entry = json.load(open(cpath)) if cpath.exists() else {"id": landmark_id, "schema_version": 1}
    entry.update({"id": landmark_id, "bins": [int(b) for b in bins], "script": f"blender/landmarks/{landmark_id}.py", "agent": "B",
                  "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    for k, v in extras.items():
        entry[k] = v
    entry.setdefault("lods", {})[f"lod{lod}"] = rec
    nb.write_catalog_entry(CATALOG, entry)
    _record_processed(f"landmark_{landmark_id}_lod{lod}", path, extras.get("sources_ids", ["building_footprints", "osm_bbbike"]),
                      {"landmark_id": landmark_id, "lod": lod, "triangles": tris})
    log.info("%s LOD%d: %d tris, %d objects, %.1f MB -> %s", landmark_id, lod, tris, len(objects), path.stat().st_size / 1e6, path)
    return rec


def render_check(landmark_id: str, view: str, camera_location, camera_target, *, fov_deg: float = 50.0, size=(960, 540), samples: int = 64,
                 sun_azimuth_deg: float = 220.0, sun_elevation_deg: float = 35.0, sun_strength: float = 2.0, exposure: float = -1.6,
                 max_bounces: int = 6, context_planes: Sequence[Sequence] = ()) -> Path:
    """Cycles CPU verification render into docs/verification/landmarks/<id>/<view>.png.

    ``context_planes`` adds ``(material, z, half_size)`` or ``(material, z, half_size, (cx, cy))`` ground/water planes so
    that a bridge or a monument is not floating in the void; they are removed afterwards.  ``sun_strength`` (W/m2) and
    ``exposure`` (EV, applied to the AgX view transform) keep the exposure sane — Blender's 4 W/m2 default blows the
    highlights out to white through AgX and hides every material.
    """
    fn = _shared("render_check", ("landmark_id", "view"))
    out_dir = VERIFY / landmark_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{view}.png"
    tmp = []
    for i, spec in enumerate(context_planes):
        m, z, half = spec[0], spec[1], spec[2]
        centre = spec[3] if len(spec) > 3 else (0.0, 0.0)
        tmp.append(ground_plane(f"_ctx_{i}", half, z, m, centre))
    bpy.context.scene.view_settings.exposure = exposure
    cyc = bpy.context.scene.cycles
    cyc.max_bounces = max_bounces
    cyc.diffuse_bounces = max_bounces
    cyc.glossy_bounces = max_bounces
    cyc.transmission_bounces = max_bounces
    cyc.transparent_max_bounces = max_bounces
    try:
        if fn is not None:
            res = fn(landmark_id, view, camera_location, camera_target, fov_deg=fov_deg, size=size, samples=samples)
            if isinstance(res, (str, Path)) and Path(res).exists():
                return Path(res)
        nb.quick_render(path, camera_location=camera_location, camera_target=camera_target, fov_deg=fov_deg, size=size, samples=samples,
                        sun_azimuth_deg=sun_azimuth_deg, sun_elevation_deg=sun_elevation_deg, sun_strength=sun_strength)
    finally:
        for o in tmp:
            bpy.data.objects.remove(o)
        for name in ("verify_cam", "verify_sun"):
            o = bpy.data.objects.get(name)
            if o is not None:
                bpy.data.objects.remove(o)
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"render failed: {path}")
    log.info("render %s -> %s", view, path)
    return path


def camera_from_lonlat(frame: LocalFrame, lon: float, lat: float, z: float) -> tuple[float, float, float]:
    return frame.from_lonlat(lon, lat, z)


def write_report(landmark_id: str, title: str, sections: dict[str, str], lods: dict, renders: Sequence[Path]) -> Path:
    """Per-landmark REPORT.md under docs/verification/landmarks/<id>/."""
    d = VERIFY / landmark_id
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", f"Script: `blender/landmarks/{landmark_id}.py` · agent B · generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", ""]
    for h, body in sections.items():
        lines += [f"## {h}", "", body.strip(), ""]
    lines += ["## Polycounts / outputs", ""]
    for k, v in sorted(lods.items()):
        lines.append(f"* `{v['path']}` — {v['triangles']:,} triangles, {v['bytes'] / 1e6:.2f} MB, bounds min {['%.1f' % c for c in v['bounds']['min']]} max {['%.1f' % c for c in v['bounds']['max']]}")
    lines.append("")
    if renders:
        lines += ["## Verification renders (Cycles CPU, 64 spp)", ""]
        for r in renders:
            lines.append(f"![{r.stem}]({r.name})")
        lines.append("")
    p = d / "REPORT.md"
    p.write_text("\n".join(lines))
    return p


def cli_args(argv: Sequence[str] | None = None) -> dict:
    """Common CLI: --no-render, --lod0-only, --samples N."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--lod0-only", action="store_true")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--views", default="", help="comma-separated subset of verification views to render")
    a, _ = ap.parse_known_args(argv if argv is not None else sys.argv[1:])
    d = vars(a)
    d["views"] = [v for v in d["views"].split(",") if v]
    return d


# ----------------------------------------------------------------------------------------------- OSM alignments


_OSM_CACHE: dict | None = None


def osm_features() -> list[dict]:
    """Features extracted by b_osm_extract.py (WGS84). Empty list if the extract has not been produced."""
    global _OSM_CACHE
    if _OSM_CACHE is None:
        p = OUT / "b_osm" / "structures.geojson"
        _OSM_CACHE = json.load(open(p)) if p.exists() else {"features": []}
    return _OSM_CACHE["features"]


def osm_ways_named(pattern: str, geom_types=("LineString",), tag_filter: Callable[[dict], bool] | None = None) -> list[dict]:
    import re
    rx = re.compile(pattern, re.I)
    out = []
    for f in osm_features():
        if f["geometry"]["type"] not in geom_types:
            continue
        tags = f["properties"].get("tags", {})
        name = " ".join(tags.get(k, "") for k in ("name", "alt_name", "official_name"))
        rel_names = " ".join(r["relation_tags"].get("name", "") for r in f["properties"].get("relations", []))
        if rx.search(name) or rx.search(rel_names):
            if tag_filter is None or tag_filter(tags):
                out.append(f)
    return out


def osm_axis_fit(features: Sequence[dict], frame: LocalFrame) -> tuple[Vector, Vector, float] | None:
    """Least-squares principal axis through all vertices of the given ways (local frame): (centroid, unit dir, length)."""
    import numpy as np
    pts = []
    for f in features:
        g = f["geometry"]
        coords = g["coordinates"] if g["type"] == "LineString" else g["coordinates"][0]
        for lon, lat in coords:
            x, y, _ = frame.from_lonlat(lon, lat)
            pts.append((x, y))
    if len(pts) < 2:
        return None
    a = np.asarray(pts)
    c = a.mean(axis=0)
    u, s, vt = np.linalg.svd(a - c, full_matrices=False)
    d = vt[0]
    proj = (a - c) @ d
    return Vector((c[0], c[1], 0.0)), Vector((d[0], d[1], 0.0)), float(proj.max() - proj.min())
