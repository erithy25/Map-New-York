"""Procedural NYC wardrobe: garments generated from the body mesh itself.

The MakeHuman CC0 clothes library has good tailored basics (t-shirts, polo, casual and business suits, wool
and cargo trousers, six pairs of shoes) but nothing that reads as New York: no puffer, no hoodie, no hi-vis,
no delivery vest, no scrubs, no hijab.  Rather than fake those with imported meshes of unclear provenance,
they are *tailored from the character's own skin*: the body vertices covered by a garment are copied, pushed
out along their normals by the fabric stand-off, solidified to the fabric thickness and given a hem, a collar
and, where the garment has them, quilt seams or a hood.

Two properties fall out of that construction and are the reason for it:

* the garment fits every body the NPC generator produces - a 1.52 m child and a 1.93 m adult get the same
  jacket pattern, correctly sized, because the pattern *is* their body;
* skin weights are exact.  Each garment vertex inherits the weights of the body vertex it was copied from,
  so a sleeve bends exactly like the arm inside it.

Materials are flat PBR (base colour + roughness), which is what the NYCSim runtime expects for cloth; fabric
detail is a UE-side material job (ADR-010).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Vector

import nycsim_bpy as nb

log = logging.getLogger("nycsim.character.wardrobe")

# --------------------------------------------------------------------------------------------- body regions
TORSO = ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "clavicle_l", "clavicle_r")
UPPERARM = ("upperarm_l", "upperarm_r")
FOREARM = ("lowerarm_l", "lowerarm_r")
HANDS = tuple(f"{f}_{n}_{s}" for f in ("thumb", "index", "middle", "ring", "pinky")
              for n in ("01", "02", "03") for s in ("l", "r")) + ("hand_l", "hand_r")
NECKHEAD = ("neck_01", "neck_02", "head")
HIPS = ("pelvis",)
THIGHS = ("thigh_l", "thigh_r")
CALVES = ("calf_l", "calf_r")
FEET = ("foot_l", "foot_r", "ball_l", "ball_r")

LAYER_BASE, LAYER_MID, LAYER_OUTER, LAYER_ACCESSORY = 0, 1, 2, 3

#: Minimum stand-off from the skin per layer, metres.  Each layer must clear the *outer* surface of the one
#: below it (stand-off + fabric thickness), otherwise two garments occupy the same shell and read as one
#: shapeless mass.  Outer surfaces land at 9.5 mm (base), 21 mm (mid) and 33 mm (outer) from the skin.
LAYER_MIN_OFFSET = {LAYER_BASE: 0.006, LAYER_MID: 0.013, LAYER_OUTER: 0.024, LAYER_ACCESSORY: 0.006}

#: How far into the garment (as a fraction of its z span) the hem and cuff cinch back towards the body.
HEM_FRACTION = 0.06
HEM_TIGHTNESS = 0.30


@dataclass
class Garment:
    """One wardrobe item: which body region it covers and how it is tailored."""

    item_id: str
    label: str
    slot: str                       # top | bottom | outerwear | shoes | hat | accessory
    bones: tuple[str, ...]
    z_lo: float = 0.0               # fraction of body height, 0 = ground, 1 = crown
    z_hi: float = 1.0
    offset: float = 0.008           # stand-off from the skin, metres
    thickness: float = 0.004
    colour: tuple[float, float, float] = (0.2, 0.2, 0.22)
    roughness: float = 0.75
    metallic: float = 0.0
    quilt_rows: int = 0             # horizontal puffer channels
    quilt_depth: float = 0.0
    hood: bool = False
    sole: float = 0.0               # sneaker/boot sole thickness, metres
    smooth_iters: int = 0           # Laplacian passes before the offset (shoes: merges the toes)
    layer: int = LAYER_BASE
    tags: tuple[str, ...] = ()
    notes: str = ""


def _smoothstep(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _c(hex_code: str) -> tuple[float, float, float]:
    """sRGB hex -> linear float triple."""
    def lin(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r = int(hex_code[0:2], 16) / 255.0
    g = int(hex_code[2:4], 16) / 255.0
    b = int(hex_code[4:6], 16) / 255.0
    return (lin(r), lin(g), lin(b))


#: 40 wardrobe items chosen to cover what is actually on a New York sidewalk: the winter puffer, the hoodie,
#: the finance suit, the hijab, the hospital scrubs from the Presbyterian/Bellevue blocks, the delivery
#: cyclist's insulated vest, DOT/Con-Ed hi-vis, the I-heart-NY tourist tee, and children's clothing.
WARDROBE: tuple[Garment, ...] = (
    # ---- tops (base layer)
    Garment("tee_white", "White crew tee", "top", TORSO + HIPS + UPPERARM, 0.44, 0.83, 0.007, 0.0035,
            _c("e8e6e1"), 0.82, tags=("tee",)),
    Garment("tee_black", "Black crew tee", "top", TORSO + HIPS + UPPERARM, 0.44, 0.83, 0.007, 0.0035,
            _c("1b1b1d"), 0.85, tags=("tee",)),
    Garment("tee_tourist", "I-heart-NY tourist tee", "top", TORSO + HIPS + UPPERARM, 0.43, 0.83, 0.008, 0.0035,
            _c("f2f2ee"), 0.86, tags=("tee", "tourist")),
    Garment("tee_yankees", "Navy team tee", "top", TORSO + HIPS + UPPERARM, 0.44, 0.83, 0.007, 0.0035,
            _c("162a4c"), 0.84, tags=("tee",)),
    Garment("polo_grey", "Grey polo", "top", TORSO + HIPS + UPPERARM, 0.44, 0.85, 0.008, 0.004,
            _c("6c6f74"), 0.78, tags=("polo",)),
    Garment("shirt_oxford", "Blue oxford shirt", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.43, 0.86, 0.010, 0.004,
            _c("9db6cf"), 0.68, tags=("shirt", "office")),
    Garment("shirt_flannel", "Red flannel shirt", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.41, 0.86, 0.012, 0.005,
            _c("7d2b26"), 0.83, tags=("shirt",)),
    Garment("sweater_knit", "Charcoal knit sweater", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.43, 0.87, 0.014,
            0.006, _c("3a3d42"), 0.88, tags=("knit",)),
    Garment("scrubs_top", "Hospital scrubs top", "top", TORSO + HIPS + UPPERARM, 0.42, 0.85, 0.011, 0.004,
            _c("2f6f6a"), 0.80, tags=("scrubs", "work")),
    Garment("blouse_cream", "Cream blouse", "top", TORSO + HIPS + UPPERARM, 0.44, 0.86, 0.009, 0.0035,
            _c("efe6d6"), 0.62, tags=("office",)),
    Garment("tank_grey", "Grey tank top", "top", TORSO + HIPS, 0.44, 0.82, 0.006, 0.003,
            _c("9a9a96"), 0.85, tags=("summer",)),
    Garment("kids_tee_stripe", "Kid's striped tee", "top", TORSO + HIPS + UPPERARM, 0.42, 0.84, 0.007, 0.0035,
            _c("d4552f"), 0.84, tags=("kids",)),

    # ---- mid layer
    Garment("hoodie_grey", "Grey pullover hoodie", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.41, 0.845, 0.013,
            0.006, _c("707277"), 0.87, hood=True, layer=LAYER_MID, tags=("hoodie",)),
    Garment("hoodie_black", "Black zip hoodie", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.41, 0.845, 0.013, 0.006,
            _c("232427"), 0.88, hood=True, layer=LAYER_MID, tags=("hoodie",)),
    Garment("hoodie_navy", "Navy hoodie", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.41, 0.845, 0.013, 0.006,
            _c("1e2b45"), 0.87, hood=True, layer=LAYER_MID, tags=("hoodie",)),
    Garment("kids_hoodie", "Kid's hoodie", "top", TORSO + HIPS + UPPERARM + FOREARM, 0.40, 0.845, 0.012, 0.006,
            _c("3f7bb5"), 0.87, hood=True, layer=LAYER_MID, tags=("kids", "hoodie")),

    # ---- outerwear
    Garment("puffer_black", "Black puffer jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.39, 0.845,
            0.028, 0.010, _c("161618"), 0.55, quilt_rows=7, quilt_depth=0.011, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("puffer_olive", "Olive puffer jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.39, 0.845,
            0.028, 0.010, _c("4a4f35"), 0.58, quilt_rows=7, quilt_depth=0.011, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("puffer_red_long", "Long red puffer", "outerwear", TORSO + UPPERARM + FOREARM + HIPS + THIGHS,
            0.28, 0.845, 0.030, 0.010, _c("8c2320"), 0.56, quilt_rows=11, quilt_depth=0.011,
            layer=LAYER_OUTER, tags=("puffer", "winter")),
    Garment("kids_puffer", "Kid's puffer", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.38, 0.845, 0.026,
            0.009, _c("2f5fa8"), 0.57, quilt_rows=6, quilt_depth=0.010, layer=LAYER_OUTER,
            tags=("kids", "puffer")),
    Garment("jacket_denim", "Denim jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.445, 0.835, 0.014,
            0.007, _c("3f5a78"), 0.80, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("jacket_leather", "Black leather jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.435, 0.835,
            0.013, 0.006, _c("18181a"), 0.38, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("jacket_bomber", "Olive bomber jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.445, 0.835,
            0.015, 0.007, _c("41452f"), 0.62, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("coat_wool", "Camel wool overcoat", "outerwear", TORSO + UPPERARM + FOREARM + HIPS + THIGHS,
            0.30, 0.845, 0.018, 0.008, _c("9a7a51"), 0.85, layer=LAYER_OUTER, tags=("coat", "winter")),
    Garment("coat_trench", "Beige trench coat", "outerwear", TORSO + UPPERARM + FOREARM + HIPS + THIGHS,
            0.32, 0.845, 0.016, 0.007, _c("b6a488"), 0.72, layer=LAYER_OUTER, tags=("coat", "rain")),
    Garment("suit_jacket_charcoal", "Charcoal suit jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM,
            0.40, 0.835, 0.014, 0.006, _c("35373c"), 0.66, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("suit_jacket_navy", "Navy suit jacket", "outerwear", TORSO + HIPS + UPPERARM + FOREARM, 0.40, 0.87,
            0.014, 0.006, _c("222c40"), 0.66, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("vest_hivis", "ANSI class-2 hi-vis vest", "outerwear", TORSO + HIPS, 0.44, 0.86, 0.020, 0.006,
            _c("d8f000"), 0.60, layer=LAYER_OUTER, tags=("hivis", "work"),
            notes="ANSI/ISEA 107 class 2 fluorescent yellow-green"),
    Garment("vest_delivery", "Insulated delivery vest", "outerwear", TORSO + HIPS, 0.42, 0.86, 0.026, 0.008,
            _c("1d1f22"), 0.62, quilt_rows=5, quilt_depth=0.009, layer=LAYER_OUTER,
            tags=("delivery", "work")),
    Garment("vest_conedison", "Con-Ed orange work vest", "outerwear", TORSO + HIPS, 0.44, 0.86, 0.020, 0.006,
            _c("e8630a"), 0.62, layer=LAYER_OUTER, tags=("hivis", "work")),

    # ---- bottoms
    Garment("jeans_indigo", "Indigo jeans", "bottom", HIPS + THIGHS + CALVES, 0.055, 0.58, 0.011, 0.005,
            _c("2f4260"), 0.80, tags=("jeans",)),
    Garment("jeans_black", "Black jeans", "bottom", HIPS + THIGHS + CALVES, 0.055, 0.58, 0.011, 0.005,
            _c("1c1c1e"), 0.82, tags=("jeans",)),
    Garment("chinos_khaki", "Khaki chinos", "bottom", HIPS + THIGHS + CALVES, 0.055, 0.58, 0.011, 0.005,
            _c("9c8a68"), 0.80, tags=("chinos",)),
    Garment("suit_trousers", "Charcoal suit trousers", "bottom", HIPS + THIGHS + CALVES, 0.05, 0.58, 0.012,
            0.005, _c("35373c"), 0.70, tags=("suit", "office")),
    Garment("scrubs_pants", "Hospital scrubs trousers", "bottom", HIPS + THIGHS + CALVES, 0.06, 0.58,
            0.014, 0.005, _c("2f6f6a"), 0.80, tags=("scrubs", "work")),
    Garment("joggers_grey", "Grey joggers", "bottom", HIPS + THIGHS + CALVES, 0.07, 0.58, 0.013, 0.005,
            _c("6a6c70"), 0.86, tags=("athleisure",)),
    Garment("skirt_pencil", "Black pencil skirt", "bottom", HIPS + THIGHS, 0.30, 0.58, 0.012, 0.005,
            _c("1e1e20"), 0.72, tags=("office",)),
    Garment("kids_jeans", "Kid's jeans", "bottom", HIPS + THIGHS + CALVES, 0.05, 0.58, 0.010, 0.0045,
            _c("39506f"), 0.80, tags=("kids", "jeans")),

    # ---- head and feet
    Garment("hijab_navy", "Navy hijab", "hat", NECKHEAD + TORSO, 0.78, 1.02, 0.016, 0.005,
            _c("222b3d"), 0.75, layer=LAYER_ACCESSORY, tags=("hijab",),
            notes="drapes from the crown over the shoulders; covers hair, neck and the upper chest"),
    Garment("sneakers_white", "White sneakers", "shoes", FEET, 0.0, 0.10, 0.015, 0.006,
            _c("e9e7e2"), 0.60, sole=0.028, layer=LAYER_ACCESSORY, tags=("sneakers",), smooth_iters=18),
    Garment("sneakers_black", "Black sneakers", "shoes", FEET, 0.0, 0.10, 0.015, 0.006,
            _c("1a1a1c"), 0.62, sole=0.028, layer=LAYER_ACCESSORY, tags=("sneakers",), smooth_iters=18),
    Garment("boots_work", "Tan work boots", "shoes", FEET + CALVES, 0.0, 0.155, 0.013, 0.007,
            _c("7a5228"), 0.66, sole=0.030, layer=LAYER_ACCESSORY, tags=("boots", "work"), smooth_iters=18),
    Garment("shoes_dress", "Black dress shoes", "shoes", FEET, 0.0, 0.085, 0.008, 0.005,
            _c("141416"), 0.35, sole=0.016, layer=LAYER_ACCESSORY, tags=("office",), smooth_iters=16),
)

WARDROBE_BY_ID = {g.item_id: g for g in WARDROBE}


# --------------------------------------------------------------------------------------------- construction
def dominant_bones(mesh_obj: bpy.types.Object, deform_names: set[str]) -> list[str]:
    """The strongest deform bone for every vertex of a mesh."""
    group_names = [g.name for g in mesh_obj.vertex_groups]
    out: list[str] = []
    for vert in mesh_obj.data.vertices:
        best, best_w = "", -1.0
        for entry in vert.groups:
            name = group_names[entry.group]
            if name in deform_names and entry.weight > best_w:
                best, best_w = name, entry.weight
        out.append(best)
    return out


def _region(mesh_obj: bpy.types.Object, dominant: list[str], garment: Garment,
            z_lo_m: float, z_hi_m: float) -> set[int]:
    accepted = set(garment.bones)
    matrix = mesh_obj.matrix_world
    out = set()
    for vert in mesh_obj.data.vertices:
        if dominant[vert.index] not in accepted:
            continue
        z = (matrix @ vert.co).z
        if z_lo_m <= z <= z_hi_m:
            out.add(vert.index)
    return out


def build_garment(garment: Garment, body: bpy.types.Object, armature: bpy.types.Object,
                  dominant: list[str], body_height: float, *, name_prefix: str = "") -> bpy.types.Object:
    """Tailor one garment onto ``body`` and return the new mesh object, skinned to ``armature``."""
    mesh = body.data
    z_lo = garment.z_lo * body_height
    z_hi = garment.z_hi * body_height
    region = _region(body, dominant, garment, z_lo, z_hi)
    if len(region) < 24:
        raise RuntimeError(f"garment {garment.item_id!r} covers only {len(region)} vertices - region is wrong")

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    keep_faces = {f for f in bm.faces if all(v.index in region for v in f.verts)}
    if not keep_faces:
        bm.free()
        raise RuntimeError(f"garment {garment.item_id!r} selected no complete faces")
    doomed = [f for f in bm.faces if f not in keep_faces]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.verts.ensure_lookup_table()
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    # drop the body's vertex-group data: the garment gets its own weights from _transfer_weights, and stale
    # group indices would point past the new object's (empty) vertex_groups collection.
    deform_layer = bm.verts.layers.deform.active
    if deform_layer is not None:
        bm.verts.layers.deform.remove(deform_layer)
    bm.normal_update()

    if garment.smooth_iters:
        # A shoe cut from the foot follows the toes; Laplacian smoothing merges them into a toe box.
        for _ in range(garment.smooth_iters):
            bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=0.55,
                                  use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.normal_update()

    offset = max(garment.offset, LAYER_MIN_OFFSET.get(garment.layer, garment.offset))
    for vert in bm.verts:
        z_norm = (vert.co.z - z_lo) / max(z_hi - z_lo, 1e-6)
        hem = min(z_norm, 1.0 - z_norm) / HEM_FRACTION
        taper = HEM_TIGHTNESS + (1.0 - HEM_TIGHTNESS) * _smoothstep(min(max(hem, 0.0), 1.0))
        push = offset * taper
        if garment.quilt_rows:
            push += garment.quilt_depth * 0.5 * taper * (
                1.0 + math.cos(2.0 * math.pi * garment.quilt_rows * z_norm))
        vert.co += vert.normal * push
    if garment.sole > 0.0:
        for vert in bm.verts:
            if vert.co.z < z_lo + 0.035:
                vert.co.z = min(vert.co.z, z_lo + 0.004) - garment.sole
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=-garment.thickness)
    bm.normal_update()

    new_mesh = bpy.data.meshes.new(f"{name_prefix}{garment.item_id}")
    bm.to_mesh(new_mesh)
    bm.free()
    new_mesh.update()

    obj = bpy.data.objects.new(f"{name_prefix}{garment.item_id}", new_mesh)
    body.users_collection[0].objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()

    _transfer_weights(body, obj)
    if garment.hood:
        _add_hood(obj, armature, garment, body_height)

    material = nb.pbr_material(f"cloth_{garment.item_id}",
                               base_color=(*garment.colour, 1.0), roughness=garment.roughness,
                               metallic=garment.metallic)
    new_mesh.materials.append(material)

    obj.parent = armature
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    return obj


def _transfer_weights(body: bpy.types.Object, garment_obj: bpy.types.Object) -> None:
    """Give every garment vertex the weights of its nearest body vertex.

    A garment vertex is at most ``offset + thickness`` (< 5 cm) from the skin vertex it was cut from, and
    ``bmesh.ops.solidify`` does not preserve vertex order, so the nearest-neighbour lookup is both exact in
    practice and independent of the topology operations above it.
    """
    from mathutils import kdtree  # noqa: PLC0415

    group_names = [g.name for g in body.vertex_groups]
    body_weights: list[list[tuple[str, float]]] = []
    for vert in body.data.vertices:
        body_weights.append([(group_names[g.group], g.weight) for g in vert.groups if g.weight > 0.0])

    tree = kdtree.KDTree(len(body.data.vertices))
    for vert in body.data.vertices:
        tree.insert(vert.co, vert.index)
    tree.balance()

    groups: dict[str, bpy.types.VertexGroup] = {}
    for vert in garment_obj.data.vertices:
        _co, src, _dist = tree.find(vert.co)
        for name, weight in body_weights[src]:
            group = groups.get(name)
            if group is None:
                group = groups[name] = garment_obj.vertex_groups.new(name=name)
            group.add([vert.index], weight, "REPLACE")


def _add_hood(obj: bpy.types.Object, armature: bpy.types.Object, garment: Garment, body_height: float) -> None:
    """A down hood: a half-ellipsoid behind and above the neck, weighted to ``spine_05``/``neck_01``."""
    bones = armature.data.bones
    neck = bones["neck_01"].head_local
    head = bones["head"].head_local
    forward = (bones["ball_l"].tail_local - bones["ball_l"].head_local)
    forward.z = 0.0
    forward = forward.normalized() if forward.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    centre = neck - forward * 0.105 + Vector((0.0, 0.0, (head.z - neck.z) * 0.18))
    radius = Vector((0.098, 0.112, 0.096))

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
    for vert in bm.verts:
        vert.co = Vector((vert.co.x * radius.x, vert.co.y * radius.y, vert.co.z * radius.z)) + centre
    verts = list(bm.verts)
    doomed = [v for v in verts if (v.co - centre).dot(forward) > 0.012]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.normal_update()
    hood_mesh = bpy.data.meshes.new(f"{obj.name}.hood")
    bm.to_mesh(hood_mesh)
    bm.free()

    offset = len(obj.data.vertices)
    obj.data = _join_meshes(obj.data, hood_mesh)
    for name, weight in (("neck_01", 0.55), ("spine_05", 0.45)):
        group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        group.add(list(range(offset, len(obj.data.vertices))), weight, "REPLACE")


def _join_meshes(a: bpy.types.Mesh, b: bpy.types.Mesh) -> bpy.types.Mesh:
    bm = bmesh.new()
    bm.from_mesh(a)
    bm.from_mesh(b)
    bm.to_mesh(a)
    bm.free()
    a.update()
    return a


def dress(built, item_ids: tuple[str, ...], *, name_prefix: str = "") -> dict[str, bpy.types.Object]:
    """Tailor a set of wardrobe items onto a built character. Returns ``{item_id: object}``."""
    body = built.basemesh
    armature = built.armature
    deform = {b.name for b in armature.data.bones if b.use_deform}
    dominant = dominant_bones(body, deform)
    height = max((body.matrix_world @ v.co).z for v in body.data.vertices)
    out: dict[str, bpy.types.Object] = {}
    for item_id in item_ids:
        garment = WARDROBE_BY_ID.get(item_id)
        if garment is None:
            raise KeyError(f"unknown wardrobe item {item_id!r}")
        obj = build_garment(garment, body, armature, dominant, height, name_prefix=name_prefix)
        out[item_id] = obj
        built.clothes[obj.name] = obj
    log.info("tailored %d garments onto %s", len(out), built.spec.name)
    return out


def build_watch(built, *, side: str = "l", name_prefix: str = "") -> bpy.types.Object:
    """A wristwatch: a 38 mm case and a strap ring around the forearm just above the wrist."""
    armature = built.armature
    bones = armature.data.bones
    lower = bones[f"lowerarm_{side}"]
    wrist = bones[f"hand_{side}"].head_local
    axis = (wrist - lower.head_local).normalized()
    centre = wrist - axis * 0.045

    # Radius of the forearm at that point, measured from the body vertices that actually belong to the
    # forearm - sampling every vertex in the plane would include the torso and produce a hoop.
    body = built.basemesh
    deform = {b.name for b in armature.data.bones if b.use_deform}
    dominant = dominant_bones(body, deform)
    forearm = {f"lowerarm_{side}", f"hand_{side}"}
    radial = []
    for vert in body.data.vertices:
        if dominant[vert.index] not in forearm:
            continue
        rel = (body.matrix_world @ vert.co) - centre
        along = rel.dot(axis)
        if abs(along) > 0.014:
            continue
        radial.append((rel - axis * along).length)
    radius = (sorted(radial)[int(len(radial) * 0.85)] + 0.003) if len(radial) >= 8 else 0.031

    up = axis.cross(Vector((0.0, 0.0, 1.0)))
    if up.length < 1e-4:
        up = axis.cross(Vector((1.0, 0.0, 0.0)))
    up.normalize()
    side_vec = axis.cross(up).normalized()

    bm = bmesh.new()
    strap = bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=radius, radius2=radius,
                                  depth=0.022)
    case = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.019, radius2=0.019, depth=0.011)
    case_verts = case["verts"]
    for vert in case_verts:
        vert.co += Vector((0.0, 0.0, radius + 0.004))
    rot = _basis_matrix(side_vec, up, axis)
    for vert in bm.verts:
        vert.co = rot @ vert.co + centre
    _ = strap
    mesh = bpy.data.meshes.new(f"{name_prefix}watch_{side}")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(nb.pbr_material("watch_steel", base_color=(0.62, 0.63, 0.65, 1.0),
                                          roughness=0.22, metallic=1.0))
    obj = bpy.data.objects.new(f"{name_prefix}watch_{side}", mesh)
    body.users_collection[0].objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    group = obj.vertex_groups.new(name=f"lowerarm_{side}")
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    obj.parent = armature
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    built.clothes[obj.name] = obj
    return obj


def _basis_matrix(x: Vector, y: Vector, z: Vector):
    from mathutils import Matrix  # noqa: PLC0415
    return Matrix(((x.x, y.x, z.x), (x.y, y.y, z.y), (x.z, y.z, z.z)))


HAIRSTYLES: tuple[tuple[str, str, str], ...] = (
    ("short01", "makehuman", "Short crop"),
    ("short02", "makehuman", "Short side-part"),
    ("short03", "makehuman", "Short textured"),
    ("short04", "makehuman", "Short curly"),
    ("bob01", "makehuman", "Bob"),
    ("bob02", "makehuman", "Long bob"),
    ("long01", "makehuman", "Long straight"),
    ("ponytail01", "makehuman", "Ponytail"),
    ("braid01", "makehuman", "Braid"),
    ("afro01", "makehuman", "Afro"),
    ("buzzcut", "procedural", "Buzz cut (scalp shell)"),
    ("topknot", "procedural", "Top knot (bob01 + procedural bun)"),
)


def build_procedural_hair(built, style: str, *, name_prefix: str = "") -> bpy.types.Object | None:
    """The two hairstyles the MakeHuman library does not have, tailored from the scalp."""
    if style not in ("buzzcut", "topknot"):
        return None
    body = built.basemesh
    armature = built.armature
    bones = armature.data.bones
    head = bones["head"]
    crown = head.tail_local
    deform = {b.name for b in armature.data.bones if b.use_deform}
    dominant = dominant_bones(body, deform)
    scalp = [v.index for v in body.data.vertices
             if dominant[v.index] == "head" and (body.matrix_world @ v.co).z > crown.z - 0.115]
    if len(scalp) < 40:
        return None
    garment = Garment(f"hair_{style}", style, "hat", ("head",), 0.0, 2.0, 0.004, 0.002,
                      _c("2a2118"), 0.55)
    height = max((body.matrix_world @ v.co).z for v in body.data.vertices)
    garment.z_lo = (crown.z - 0.115) / height
    obj = build_garment(garment, body, armature, dominant, height, name_prefix=name_prefix)
    if style == "topknot":
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.042)
        for vert in bm.verts:
            vert.co += crown + Vector((0.0, 0.0, 0.035))
        bun = bpy.data.meshes.new("bun")
        bm.to_mesh(bun)
        bm.free()
        offset = len(obj.data.vertices)
        obj.data = _join_meshes(obj.data, bun)
        group = obj.vertex_groups.get("head") or obj.vertex_groups.new(name="head")
        group.add(list(range(offset, len(obj.data.vertices))), 1.0, "REPLACE")
    return obj


# ------------------------------------------------------------------------------------ carried items / hats
#: Carried-item dimensions, metres. A NYC courier's insulated box is the standard 40 x 40 x 40 cm cube.
BAG_SPECS: dict[str, dict] = {
    "backpack": {"size": (0.30, 0.16, 0.42), "bone": "spine_04", "behind": 0.10, "up": 0.02,
                 "colour": _c("2b2f36"), "roughness": 0.72},
    "tote": {"size": (0.34, 0.12, 0.38), "bone": "lowerarm_l", "behind": 0.0, "up": -0.14,
             "colour": _c("bfae8c"), "roughness": 0.86},
    "shoulder_bag": {"size": (0.28, 0.11, 0.22), "bone": "spine_02", "behind": -0.02, "up": -0.06,
                     "side": 0.17, "colour": _c("4a3423"), "roughness": 0.55},
    "delivery_box": {"size": (0.40, 0.40, 0.40), "bone": "spine_04", "behind": 0.14, "up": 0.06,
                     "colour": _c("d43a2a"), "roughness": 0.60},
    "shopping_bags": {"size": (0.24, 0.12, 0.32), "bone": "hand_r", "behind": 0.0, "up": -0.20,
                      "colour": _c("d8d5cc"), "roughness": 0.88},
    "briefcase": {"size": (0.40, 0.09, 0.30), "bone": "hand_r", "behind": 0.0, "up": -0.22,
                  "colour": _c("21201f"), "roughness": 0.40},
}

HAT_SPECS: dict[str, dict] = {
    "cap_backwards": {"crown": 0.098, "brim": 0.075, "brim_back": True, "colour": _c("1f2a44")},
    "beanie_grey": {"crown": 0.100, "brim": 0.0, "brim_back": False, "colour": _c("55585d")},
}


def build_bag(built, kind: str, *, name_prefix: str = "") -> bpy.types.Object:
    """A carried item rigidly weighted to one bone (backpack to the chest, briefcase to the hand)."""
    spec = BAG_SPECS.get(kind)
    if spec is None:
        raise KeyError(f"unknown bag {kind!r}")
    armature = built.armature
    bones = armature.data.bones
    bone = bones[spec["bone"]]
    forward = bones["ball_l"].tail_local - bones["ball_l"].head_local
    forward.z = 0.0
    forward = forward.normalized() if forward.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    right = forward.cross(Vector((0.0, 0.0, 1.0))).normalized()
    centre = (bone.head_local + bone.tail_local) * 0.5
    centre = centre - forward * spec["behind"] + Vector((0.0, 0.0, spec["up"])) \
        + right * spec.get("side", 0.0)

    sx, sy, sz = spec["size"]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for vert in bm.verts:
        local = Vector((vert.co.x * sx, vert.co.y * sy, vert.co.z * sz))
        vert.co = right * local.x + forward * local.y + Vector((0.0, 0.0, local.z)) + centre
    bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), offset=0.012,
                    segments=2, affect="EDGES")
    mesh = bpy.data.meshes.new(f"{name_prefix}bag_{kind}")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(nb.pbr_material(f"bag_{kind}", base_color=(*spec["colour"], 1.0),
                                          roughness=spec["roughness"]))
    obj = bpy.data.objects.new(f"{name_prefix}bag_{kind}", mesh)
    built.basemesh.users_collection[0].objects.link(obj)
    obj.matrix_world = built.basemesh.matrix_world.copy()
    group = obj.vertex_groups.new(name=spec["bone"])
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    obj.parent = armature
    obj.modifiers.new("Armature", "ARMATURE").object = armature
    built.clothes[obj.name] = obj
    return obj


def build_hat(built, kind: str, *, name_prefix: str = "") -> bpy.types.Object | None:
    """Procedural cap or beanie sitting on the skull, weighted to ``head``."""
    spec = HAT_SPECS.get(kind)
    if spec is None:
        return None
    armature = built.armature
    bones = armature.data.bones
    head = bones["head"]
    forward = bones["ball_l"].tail_local - bones["ball_l"].head_local
    forward.z = 0.0
    forward = forward.normalized() if forward.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    right = forward.cross(Vector((0.0, 0.0, 1.0))).normalized()
    crown = head.head_local.lerp(head.tail_local, 0.62)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=spec["crown"])
    doomed = [v for v in bm.verts if v.co.z < -0.012]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    for vert in bm.verts:
        vert.co = vert.co + crown
    if spec["brim"] > 0.0:
        brim = bmesh.new()
        bmesh.ops.create_cone(brim, cap_ends=True, segments=20, radius1=spec["crown"] + spec["brim"],
                              radius2=spec["crown"] + spec["brim"], depth=0.008)
        direction = -forward if spec["brim_back"] else forward
        cut = [v for v in brim.verts if (v.co.x * direction.x + v.co.y * direction.y) < 0.004]
        bmesh.ops.delete(brim, geom=cut, context="VERTS")
        for vert in brim.verts:
            vert.co = vert.co + crown + Vector((0.0, 0.0, -0.012))
        tmp = bpy.data.meshes.new("brim")
        brim.to_mesh(tmp)
        brim.free()
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    mesh = bpy.data.meshes.new(f"{name_prefix}hat_{kind}")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(nb.pbr_material(f"hat_{kind}", base_color=(*spec["colour"], 1.0), roughness=0.78))
    obj = bpy.data.objects.new(f"{name_prefix}hat_{kind}", mesh)
    built.basemesh.users_collection[0].objects.link(obj)
    obj.matrix_world = built.basemesh.matrix_world.copy()
    group = obj.vertex_groups.new(name="head")
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    obj.parent = armature
    obj.modifiers.new("Armature", "ARMATURE").object = armature
    built.clothes[obj.name] = obj
    _ = right
    return obj
