"""The engine binding contract: node names, pivots, damage regions, collision proxies, LODs, export, catalog.

Every vehicle glb produced by this lane satisfies a *contract profile*.  The profile is recorded in the
catalog entry so the importer and ``tests/test_vehicles.py`` check the same list:

``full``      enclosed cabin with hinged doors — cars, SUVs, vans, trucks, buses, emergency vehicles
``cab``       enclosed cabin, no opening boot/bonnet panels of its own (buses, box bodies) — same list minus
              ``Trunk`` where the body has none, stated per vehicle in ``contract_waivers``
``open``      open vehicles (bicycle, e-bike, moped, pedicab, horse carriage): no doors, no windows, no wipers,
              no cabin.  The waived names are listed explicitly in the catalog entry — nothing is faked.

Pivots (DATA_CONTRACTS §13): the file origin is on the ground under the rear-axle centre, +X forward, +Y left,
+Z up, metres.  ``Wheel_*`` origins are the hub centres, ``Door_*`` origins are on the hinge axis, ``Hood`` and
``Trunk`` origins are on their hinge lines, ``Wiper_*`` origins are the spindles, ``SteeringWheel`` origin is on
the column axis with local +Z along it.

**Door pivot convention, including doors that are not side-hinged.**  A ``Door_*`` node's origin always sits on
the *forward vertical edge of its own aperture*, and its local +X points rearward along the leaf.  For a
conventional side-hinged car door that edge is the hinge and the engine simply rotates the node about its local
Z.  Buses, coaches and school buses use **bifold** or **outward-swinging plug** leaves; those are exported as a
single node covering the whole doorway, whose origin is on the same forward frame edge — which is the outer
leaf's hinge — so the engine has a well-defined axis either way.  ``catalog["door_kind"]`` names the mechanism
per door (``hinged`` / ``sliding`` / ``bifold`` / ``rear cargo door``) so the engine can pick the right
animation: rotate about the origin for ``hinged`` and ``bifold``, translate along -X for ``sliding``.

Damage regions are exported as glTF custom vertex attributes ``_DMG_FRONT/REAR/LEFT/RIGHT/ROOF`` (float per
vertex, 0..1) **and** as Blender vertex groups of the same name without the underscore, so the data survives
both the glb and a .blend round trip.
"""
from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import env, geom as g, materials as M
from .blueprint import Dimensions

nb = env.nb
log = env.log

SCHEMA_VERSION = 1

#: DATA_CONTRACTS §13 pivot convention, stamped into ``asset.extras.nycsim.pivot`` and the catalog entry
PIVOT_CONVENTION = "ground under rear-axle centre, +X forward, +Y left, +Z up (DATA_CONTRACTS §13)"

LIGHT_SLOTS_FULL = (
    "LIGHT_HEAD_L", "LIGHT_HEAD_R", "LIGHT_LOW", "LIGHT_HIGH", "LIGHT_TAIL_L", "LIGHT_TAIL_R",
    "LIGHT_BRAKE_L", "LIGHT_BRAKE_R", "LIGHT_TURN_FL", "LIGHT_TURN_FR", "LIGHT_TURN_RL", "LIGHT_TURN_RR",
    "LIGHT_REVERSE_L", "LIGHT_REVERSE_R", "LIGHT_PLATE", "LIGHT_DRL",
)

CONTRACT_FULL = (
    "Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR",
    "Door_FL", "Door_FR", "Door_RL", "Door_RR",
    "SteeringWheel", "Hood", "Trunk", "Wiper_L", "Wiper_R",
    "Window_WS", "Window_BACK", "Window_FL", "Window_FR", "Window_RL", "Window_RR",
    "Mirror_L", "Mirror_R", "Interior_Dash", "Shifter", "Pedals", "Plate_F", "Plate_R",
) + LIGHT_SLOTS_FULL

MATERIAL_SLOTS_FULL = ("MIRROR_GLASS", "GAUGE_SPEED", "GAUGE_RPM", "SCREEN_CENTER", "PLATE_FACE") + LIGHT_SLOTS_FULL

DMG_REGIONS = ("FRONT", "REAR", "LEFT", "RIGHT", "ROOF")


# --------------------------------------------------------------------------- pivots
def hinge_door(ob: bpy.types.Object, hinge_x: float, y: float, z: float = 0.0) -> None:
    """Put a door's origin on its (vertical) hinge axis."""
    g.set_origin(ob, (hinge_x, y, z))


def hinge_panel(ob: bpy.types.Object, hinge_x: float, hinge_z: float) -> None:
    """Put a bonnet/boot origin on its transverse hinge line (rotation about local Y opens it)."""
    g.set_origin(ob, (hinge_x, 0.0, hinge_z))


# --------------------------------------------------------------------------- damage regions
def add_damage_regions(ob: bpy.types.Object, dims: Dimensions, *, z_belt: float, soft: float = 0.45) -> dict[str, float]:
    """Write ``_DMG_*`` float attributes and matching vertex groups. Weights are smooth ramps so a deformation
    driven by them does not tear at the region boundary. Returns the mean weight per region (for the report)."""
    g.sync()
    me = ob.data
    n = len(me.vertices)
    if n == 0:
        return {}
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.asarray(ob.matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    xf, xr = dims.x_front, dims.x_rear
    hw = dims.half_width

    def ramp(v, a, b):
        if abs(b - a) < 1e-6:
            return np.zeros_like(v)
        return np.clip((v - a) / (b - a), 0.0, 1.0)

    # the ramps are anchored on the *panel's own* extent as well as the vehicle envelope, so every region
    # reaches 1.0 somewhere on every panel it applies to (a door skin never reaches the vehicle's nose).
    x_hi, x_lo = min(xf, float(x.max())), max(xr, float(x.min()))
    y_hi, y_lo = min(hw, float(y.max())), max(-hw, float(y.min()))
    z_hi = float(z.max())
    front_a = min(dims.x_axle_front - soft, x_hi - 0.15)
    rear_a = max(soft, x_lo + 0.15)
    w = {
        "FRONT": ramp(x, front_a, x_hi),
        "REAR": ramp(-x, -rear_a, -x_lo),
        "LEFT": ramp(y, max(0.0, y_hi) * 0.15, max(0.02, y_hi)),
        "RIGHT": ramp(-y, max(0.0, -y_lo) * 0.15, max(0.02, -y_lo)),
        "ROOF": ramp(z, z_belt, max(z_belt + 0.05, min(z_hi, z_belt + 0.30))),
    }
    means = {}
    for name, vals in w.items():
        vals = vals.astype(np.float32)
        attr_name = f"_DMG_{name}"
        attr = me.attributes.get(attr_name)
        if attr is None:
            attr = me.attributes.new(attr_name, "FLOAT", "POINT")
        attr.data.foreach_set("value", vals)
        vg = ob.vertex_groups.get(f"DMG_{name}") or ob.vertex_groups.new(name=f"DMG_{name}")
        idx = np.nonzero(vals > 1e-4)[0]
        for i in idx.tolist():
            vg.add([i], float(vals[i]), "REPLACE")
        means[name] = float(vals.mean())
    me.update()
    return means


# --------------------------------------------------------------------------- collision proxies
def ucx_proxies(name_stem: str, sources: Sequence[bpy.types.Object], dims: Dimensions, *, z_belt: float,
                slices: int = 5, cabin: bool = True, lib: M.Library | None = None) -> list[bpy.types.Object]:
    """Convex ``UCX_<stem>_NN`` proxies: X-slabs of the lower body plus one hull for the greenhouse.
    Slabs of a convex-hull-per-slab decomposition are convex by construction — provided the hull is *not*
    planar-dissolved afterwards: dissolving merges nearly-coplanar hull faces into n-gons whose
    re-triangulation cuts inside the hull and makes the proxy fail a convexity test."""
    g.sync()
    pts = np.concatenate([g.mesh_points(o) for o in sources if o.type == "MESH" and len(o.data.vertices)])
    if len(pts) == 0:
        return []
    mat = M.basic("UCX_COLLISION", (0.1, 0.8, 0.2, 0.25), roughness=1.0, alpha=0.25)
    out: list[bpy.types.Object] = []
    low = pts[pts[:, 2] <= z_belt + 0.02]
    if len(low) < 8:
        low = pts
    # the proxies must reach the road: a hull built from body panels alone floats above it and lets a
    # wheel-height obstacle pass under the vehicle.
    ground = pts.copy()
    ground[:, 2] = 0.0
    pts = np.concatenate([pts, ground])
    low = np.concatenate([low, ground])
    x0, x1 = float(pts[:, 0].min()), float(pts[:, 0].max())
    for k in range(slices):
        a = x0 + (x1 - x0) * k / slices
        b = x0 + (x1 - x0) * (k + 1) / slices
        sel = low[(low[:, 0] >= a - 1e-4) & (low[:, 0] <= b + 1e-4)]
        if len(sel) < 8:
            continue
        bm = g.convex_hull_bm(sel, simplify_deg=0.0, max_points=1500)
        ob = g.to_object(f"UCX_{name_stem}_{len(out):02d}", bm, [mat], smooth=False)
        out.append(ob)
    if cabin:
        hi = pts[pts[:, 2] > z_belt - 0.02]
        if len(hi) >= 8:
            bm = g.convex_hull_bm(hi, simplify_deg=0.0, max_points=1500)
            ob = g.to_object(f"UCX_{name_stem}_{len(out):02d}", bm, [mat], smooth=False)
            out.append(ob)
    return out


def is_convex(ob: bpy.types.Object, tol: float = 1e-3) -> bool:
    me = ob.data
    if len(me.polygons) == 0:
        return False
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    for p in me.polygons:
        n = np.asarray(p.normal, dtype=np.float64)
        if np.linalg.norm(n) < 1e-9:
            continue
        n = n / np.linalg.norm(n)
        d = float(np.dot(np.asarray(p.center, dtype=np.float64), n))
        if (co @ n - d).max() > tol:
            return False
    return True


# --------------------------------------------------------------------------- export
def export_glb(path: str | Path, objects: Sequence[bpy.types.Object], *, extras: dict | None = None) -> Path:
    """Export a vehicle through the foundation helper ``nycsim_bpy.export_glb``.

    ``export_attributes=True`` carries the ``_DMG_*`` damage weights into the file, and the helper stamps the
    NYCSim metadata into the file's ``asset.extras`` block as DATA_CONTRACTS §13 requires.  The only
    vehicle-specific addition is the ``pivot`` string, which travels with the rest of the extras.
    """
    meta = {"pivot": PIVOT_CONVENTION}
    if extras:
        meta.update(extras)
    return nb.export_glb(path, objects=list(objects), extras=meta, draco=False, apply_modifiers=True,
                         export_animations=False, texcoords=True, tangents=False, export_extras=True,
                         export_attributes=True, export_normals=True)


def glb_json(path: Path) -> dict:
    data = path.read_bytes()
    off = 12
    while off < len(data):
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        if ctype == b"JSON":
            return json.loads(data[off + 8:off + 8 + clen])
        off += 8 + clen + (-clen % 4)
    raise RuntimeError(f"{path} has no JSON chunk")


def glb_triangles(path: Path, skip=("UCX_",)) -> int:
    """Rendered triangles actually present in an exported glb.  Counting in Blender over-reports slightly
    (the exporter drops degenerate faces), and the catalog must agree with the file."""
    js = glb_json(path)
    total = 0
    for n in js.get("nodes", []):
        if "mesh" not in n or n.get("name", "").startswith(tuple(skip)):
            continue
        for prim in js["meshes"][n["mesh"]]["primitives"]:
            acc = js["accessors"][prim["indices"]] if "indices" in prim else js["accessors"][prim["attributes"]["POSITION"]]
            total += acc["count"] // 3
    return total


# --------------------------------------------------------------------------- LODs
def _decimate_copy(objects: Sequence[bpy.types.Object], ratio: float, merge_name: str | None) -> list[bpy.types.Object]:
    copies: list[bpy.types.Object] = []
    for o in objects:
        if o.type != "MESH" or len(o.data.polygons) == 0:
            continue
        c = o.copy()
        c.data = o.data.copy()
        bpy.context.scene.collection.objects.link(c)
        copies.append(c)
    if merge_name is not None:
        merged = g.join(copies, merge_name, smooth=True, sharp_angle_deg=40.0)
        merged.data.validate(verbose=False, clean_customdata=False)
        merged.data.update()
        copies = [merged]
    for c in copies:
        if ratio < 0.999 and len(c.data.polygons) > 24:
            mod = c.modifiers.new("dec", "DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = max(0.005, ratio)
            mod.use_collapse_triangulate = True
            g.bake_modifiers(c)
    return copies


def export_lods(base_path: Path, lod0_objects: Sequence[bpy.types.Object], lod1_objects: Sequence[bpy.types.Object],
                budgets: tuple[int, int], extras: dict) -> list[dict]:
    """Write ``<id>_LOD1.glb`` (same node names, exterior only) and ``<id>_LOD2.glb`` (single merged ``Body``).

    LODs live in sibling files rather than inside the LOD0 glb: glTF has no LOD concept that Blender exports,
    and UE's static/skeletal mesh importer takes LODs from separate files.  The catalog lists all three.
    """
    out: list[dict] = []
    tri0 = g.tri_count_all(lod0_objects)
    for level, (srcs, budget, merge) in enumerate(((lod1_objects, budgets[0], None),
                                                   (lod1_objects, budgets[1], "Body")), start=1):
        cur = g.tri_count_all(srcs)
        # always coarser than the level above, and under budget (collapse-decimate overshoots a little)
        ratio = min(0.85, 0.97 * budget / max(1, cur))
        saved = {o: o.name for o in srcs}
        meshy = [o for o in srcs if o.type == "MESH" and len(o.data.polygons)]
        for o in srcs:
            o.name = "SRC__" + o.name
        copies = _decimate_copy(srcs, ratio, merge)
        if merge is None:
            for c, o in zip(copies, meshy):
                c.name = saved[o]
        else:
            copies[0].name = "Body"
        p = base_path.with_name(f"{base_path.stem}_LOD{level}.glb")
        export_glb(p, copies, extras={**extras, "lod": level})
        tris = glb_triangles(p)
        out.append({"level": level, "path": str(p.relative_to(nb.BLENDER_OUT.parent)), "triangles": tris,
                    "budget": budget, "nodes": sorted(c.name for c in copies)})
        for c in list(copies):
            g.remove_object(c)
        for o, nm in saved.items():
            o.name = nm
    out.insert(0, {"level": 0, "path": str(base_path.relative_to(nb.BLENDER_OUT.parent)),
                   "triangles": glb_triangles(base_path), "budget": None,
                   "nodes": sorted(o.name for o in lod0_objects)})
    return out


# --------------------------------------------------------------------------- the vehicle record
@dataclass
class Vehicle:
    id: str
    display_name: str
    vclass: str                       # sedan | suv | van | pickup | truck | bus | emergency | bike | moped | cart
    dims: Dimensions
    objects: dict[str, bpy.types.Object] = field(default_factory=dict)
    contract_profile: str = "full"
    contract_waivers: dict[str, str] = field(default_factory=dict)
    livery: str = "base"
    base_id: str | None = None
    z_belt: float = 1.0
    notes: dict = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    extra_slots: tuple[str, ...] = ()

    def add(self, ob: bpy.types.Object | None) -> None:
        if ob is None:
            return
        self.objects[ob.name] = ob

    def add_all(self, obs: Iterable[bpy.types.Object] | dict) -> None:
        it = obs.values() if isinstance(obs, dict) else obs
        for o in it:
            self.add(o)

    # ------------------------------------------------------------------ checks
    #: reduced node lists for vehicles that physically have no cabin.  Each waived contract name is listed
    #: explicitly in the catalog entry with a reason — nothing is faked to satisfy the list.
    OPEN_PROFILES = {
        "open": ("Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR"),
        "two_wheel": ("Body", "Wheel_F", "Wheel_R"),
        "trike": ("Body", "Wheel_F", "Wheel_RL", "Wheel_RR"),
    }

    def required_nodes(self) -> tuple[str, ...]:
        base = self.OPEN_PROFILES.get(self.contract_profile)
        if base is not None:
            return tuple(n for n in base if n not in self.contract_waivers)
        return tuple(n for n in CONTRACT_FULL if n not in self.contract_waivers)

    def required_materials(self) -> tuple[str, ...]:
        if self.contract_profile in self.OPEN_PROFILES:
            return tuple(s for s in ("LIGHT_HEAD_L", "LIGHT_TAIL_L")
                         if s not in self.contract_waivers) + self.extra_slots
        return tuple(s for s in MATERIAL_SLOTS_FULL if s not in self.contract_waivers) + self.extra_slots

    def missing(self) -> list[str]:
        return [n for n in self.required_nodes() if n not in self.objects]

    def material_names(self) -> set[str]:
        out: set[str] = set()
        for o in self.objects.values():
            if o.type != "MESH":
                continue
            for m in o.data.materials:
                if m is not None:
                    out.add(m.name)
        return out

    def missing_materials(self) -> list[str]:
        have = self.material_names()
        return [s for s in self.required_materials() if s not in have]

    #: parts that manufacturers exclude from the published length/width/height envelope
    ENVELOPE_EXCLUDE = ("UCX_", "Mirror_", "Antenna", "TAXI_ROOF", "LightBar", "SIGN_", "Ladder", "Pole",
                        "RoofRack", "Exhaust_Stack", "Mast", "PushBumper", "Bullbar", "Horse", "Shafts",
                        "CrossingGate", "StopArm", "Liftgate")

    def wheel_diameters(self) -> dict[str, float]:
        """Actual rolling diameter of each wheel in millimetres (a carriage's front wheels are smaller than
        its rear wheels, so a single published figure cannot describe every axle)."""
        out = {}
        for name, ob in self.objects.items():
            if not name.startswith("Wheel_") or ob.type != "MESH":
                continue
            pts = g.mesh_points(ob, world=False)
            out[name] = round(float(max(pts[:, 0].max() - pts[:, 0].min(), pts[:, 2].max() - pts[:, 2].min())) * 1000.0, 1)
        return out

    def measured(self) -> dict:
        g.sync()
        meshes = [o for o in self.objects.values() if o.type == "MESH"]
        env_meshes = [o for o in meshes if not o.name.startswith(self.ENVELOPE_EXCLUDE)]
        lo, hi = g.bounds(env_meshes)
        alo, ahi = g.bounds([o for o in meshes if not o.name.startswith("UCX_")])
        return {"length_m": float(hi.x - lo.x), "width_m": float(hi.y - lo.y), "height_m": float(hi.z - lo.z),
                "min": [float(v) for v in lo], "max": [float(v) for v in hi],
                "width_over_mirrors_m": float(ahi.y - alo.y),
                "height_over_roof_equipment_m": float(ahi.z - alo.z),
                "envelope_excludes": [o.name for o in meshes if o.name.startswith(self.ENVELOPE_EXCLUDE)
                                      and not o.name.startswith("UCX_")]}

    def wheel_pivots(self) -> dict[str, list[float]]:
        g.sync()
        out = {}
        for tag in ("FL", "FR", "RL", "RR", "F", "R"):
            ob = self.objects.get(f"Wheel_{tag}")
            if ob is not None:
                out[f"Wheel_{tag}"] = [float(v) for v in ob.matrix_world.translation]
        return out


def finalise(v: Vehicle, *, lod_budgets: tuple[int, int] = (60_000, 8_000),
             exterior_names: Sequence[str] | None = None, extra_catalog: dict | None = None,
             strict: bool = True) -> dict:
    """Validate the contract, export ``<id>.glb`` + LODs, write the catalog entry, return it."""
    env.ensure_dirs()
    g.sync()
    missing = v.missing()
    miss_mat = v.missing_materials()
    if missing and strict:
        raise RuntimeError(f"{v.id}: missing contract nodes {missing}")
    if miss_mat and strict:
        raise RuntimeError(f"{v.id}: missing contract material slots {miss_mat}")
    objs = [o for o in v.objects.values() if o.type == "MESH"]
    body_objs = [o for o in objs if not o.name.startswith("UCX_")]
    ucx = [o for o in objs if o.name.startswith("UCX_")]
    meas = v.measured()
    pub = v.dims.as_dict()
    dev = {
        "length_pct": 100.0 * (meas["length_m"] - pub["length_mm"] / 1000.0) / (pub["length_mm"] / 1000.0),
        "width_pct": 100.0 * (meas["width_m"] - pub["width_mm"] / 1000.0) / (pub["width_mm"] / 1000.0),
        "height_pct": 100.0 * (meas["height_m"] - pub["height_mm"] / 1000.0) / (pub["height_mm"] / 1000.0),
    }
    path = env.OUT_DIR / f"{v.id}.glb"
    extras = {"vehicle_id": v.id, "vehicle_class": v.vclass, "livery": v.livery,
              "contract_profile": v.contract_profile}
    export_glb(path, objs, extras=extras)
    ext_names = exterior_names or [o.name for o in body_objs
                                   if not o.name.startswith(("Interior_", "Seat_", "Pedals", "Shifter", "SteeringWheel"))]
    lod_src = [v.objects[n] for n in ext_names if n in v.objects and v.objects[n].type == "MESH"]
    lods = export_lods(path, body_objs, lod_src, lod_budgets, extras)
    tri_lod0 = lods[0]["triangles"]
    entry = {
        "schema_version": SCHEMA_VERSION,
        "id": v.id,
        "name": v.display_name,
        "class": v.vclass,
        "livery": v.livery,
        "base_id": v.base_id,
        "glb": str(path.relative_to(nb.BLENDER_OUT.parent)),
        "lods": lods,
        "triangles": tri_lod0,
        "published_dimensions_mm": pub,
        "measured_m": meas,
        "dimension_deviation_pct": {k: round(vv, 3) for k, vv in dev.items()},
        "pivot": PIVOT_CONVENTION,
        "wheel_pivots": v.wheel_pivots(),
        "wheel_diameter_mm": pub["wheel_diameter_mm"],
        "wheel_diameters_mm": v.wheel_diameters(),
        "nodes": sorted(o.name for o in objs),
        "materials": sorted(v.material_names()),
        "light_slots": sorted(s for s in v.material_names() if s.startswith("LIGHT_")),
        "collision_proxies": sorted(o.name for o in ucx),
        "collision_convex": all(is_convex(o) for o in ucx),
        "damage_regions": [f"DMG_{r}" for r in DMG_REGIONS],
        "contract_profile": v.contract_profile,
        "contract_waivers": v.contract_waivers,
        "missing_nodes": missing,
        "missing_material_slots": miss_mat,
        "notes": v.notes,
        "sources": v.sources,
    }
    if extra_catalog:
        entry.update(extra_catalog)
    nb.write_catalog_entry(env.CATALOG_DIR, entry)
    env.record_processed(entry)
    log.info("%s: %d tris LOD0 (%s), L/W/H %.3f/%.3f/%.3f m, dev %.2f/%.2f/%.2f %%",
             v.id, entry["triangles"], path.name, meas["length_m"], meas["width_m"], meas["height_m"],
             dev["length_pct"], dev["width_pct"], dev["height_pct"])
    return entry
