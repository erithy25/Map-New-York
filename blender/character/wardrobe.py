"""NYC wardrobe: MakeHuman CC0 tailored garments, recoloured, plus procedural NYC-specific outerwear.

Two kinds of item live in :data:`WARDROBE`:

``source="makehuman"``
    A real tailored CC0 garment from the MakeHuman community packs - a t-shirt with a hem, a collar, sleeve
    seams and an armpit, or a pair of trousers with a waistband and a fly.  MPFB fits it to the body through
    the MakeClothes vertex correspondences, so it follows every macro target.  Some packs ship a suit as one
    mesh containing a jacket shell and a trouser shell; :func:`split_loose_parts` keeps the half we want.
    The garment keeps its own texture and is tinted to the wardrobe colour.

``source="procedural"``
    The items MakeHuman has none of: puffers, the long coats, the hi-vis and delivery vests, the hijab.
    These are built as an offset of a **garment that is already on the body** (the tee or sweater), not of
    the bare skin - so they inherit that garment's real sleeves, armpit gap and hem instead of fusing the
    arms to the torso, which is what offsetting the skin produced.  Only if no base garment is present do
    they fall back to the body.

Skin weights are exact either way: MakeHuman garments are weighted by MPFB from the base mesh, and a
procedural garment takes each vertex's weights from its nearest vertex on the mesh it was cut from.
"""
from __future__ import annotations

import logging
import math
import re
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
HANDS = ("hand_l", "hand_r")
NECKHEAD = ("neck_01", "neck_02", "head")
HIPS = ("pelvis",)
THIGHS = ("thigh_l", "thigh_r")
CALVES = ("calf_l", "calf_r")
FEET = ("foot_l", "foot_r", "ball_l", "ball_r")

LAYER_BASE, LAYER_MID, LAYER_OUTER, LAYER_ACCESSORY = 0, 1, 2, 3

#: Minimum stand-off from whatever the garment is cut from, per layer, in metres.
LAYER_MIN_OFFSET = {LAYER_BASE: 0.006, LAYER_MID: 0.010, LAYER_OUTER: 0.016, LAYER_ACCESSORY: 0.006}

#: How far a fitted MakeHuman garment is pushed out along its normals so an outer layer clears the one
#: below it.  MakeHuman fits every garment at its own designed stand-off, so a jacket and a sweater
#: otherwise interpenetrate.
LAYER_MH_PUSH = {LAYER_BASE: 0.0, LAYER_MID: 0.004, LAYER_OUTER: 0.024, LAYER_ACCESSORY: 0.0}

#: How far into the garment (as a fraction of its z span) the hem and cuff cinch back towards the body.
HEM_FRACTION = 0.06
HEM_TIGHTNESS = 0.30


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


@dataclass
class Garment:
    """One wardrobe item."""

    item_id: str
    label: str
    slot: str                        # top | bottom | outerwear | shoes | hat | accessory
    source: str = "procedural"       # "makehuman" | "procedural"
    mhclo: str = ""                  # MakeHuman asset directory, for source == "makehuman"
    keep: str = "all"                # "all" | "upper" | "lower" - which half of a one-mesh suit to keep
    split_z: float = 0.55            # the split plane, as a fraction of body height
    bones: tuple[str, ...] = ()      # procedural: which body region the pattern is cut from
    z_lo: float = 0.0                # procedural: fraction of body height, 0 = ground, 1 = crown
    z_hi: float = 1.0
    offset: float = 0.008            # procedural: stand-off from the source surface, metres
    thickness: float = 0.004
    colour: tuple[float, float, float] = (0.2, 0.2, 0.22)
    roughness: float = 0.75
    metallic: float = 0.0
    quilt_rows: int = 0              # horizontal puffer channels
    quilt_depth: float = 0.0
    hood: bool = False               # attach a procedural hood at the neck
    front_cut: float | None = None   # drop head vertices this far in front of the head joint (hijab)
    layer: int = LAYER_BASE
    tags: tuple[str, ...] = ()
    notes: str = ""

    @property
    def is_makehuman(self) -> bool:
        return self.source == "makehuman"


#: 40 wardrobe items covering what is actually on a New York sidewalk.  Every base layer, bottom and shoe is
#: a real tailored MakeHuman CC0 mesh; the puffers, long coats, work vests and the hijab are procedural
#: because MakeHuman has none of them.
WARDROBE: tuple[Garment, ...] = (
    # ---------- tops: real tailored MakeHuman meshes, tinted ------------------------------------------
    Garment("tee_white", "White crew tee", "top", "makehuman", "elvs_crude_t-shirt_male",
            colour=_c("e8e6e1"), roughness=0.82, tags=("tee",)),
    Garment("tee_black", "Black crew tee", "top", "makehuman", "elvs_crude_t-shirt_male",
            colour=_c("1b1b1d"), roughness=0.85, tags=("tee",)),
    Garment("tee_tourist", "I-heart-NY tourist tee", "top", "makehuman", "elvs_crude_t-shirt_male",
            colour=_c("f2f2ee"), roughness=0.86, tags=("tee", "tourist")),
    Garment("tee_womens_sage", "Women's sage tee", "top", "makehuman", "joepal_crude_t-shirt_female",
            colour=_c("7f8a6d"), roughness=0.84, tags=("tee",)),
    Garment("polo_grey", "Grey polo", "top", "makehuman", "namuhekam_male_polo_shirt",
            colour=_c("6c6f74"), roughness=0.78, tags=("polo",)),
    Garment("shirt_tucked_blue", "Blue tucked shirt", "top", "makehuman", "toigo_basic_tucked_t-shirt",
            colour=_c("9db6cf"), roughness=0.68, tags=("shirt", "office")),
    Garment("sweater_knit", "Charcoal knit sweater", "top", "makehuman", "toigo_fisherman_sweater",
            colour=_c("3a3d42"), roughness=0.88, tags=("knit",)),
    Garment("scrubs_top", "Hospital scrubs top", "top", "makehuman", "toigo_basic_tucked_t-shirt",
            colour=_c("2f6f6a"), roughness=0.80, tags=("scrubs", "work")),
    Garment("tank_grey", "Grey tank top", "top", "makehuman", "toigo_keyhole_tank_top",
            colour=_c("9a9a96"), roughness=0.85, tags=("summer",)),
    Garment("kids_tee_stripe", "Kid's tee", "top", "makehuman", "elvs_crude_t-shirt_male",
            colour=_c("d4552f"), roughness=0.84, tags=("kids", "tee")),

    # ---------- mid layer: the sweater mesh plus a procedural hood --------------------------------------
    Garment("hoodie_grey", "Grey pullover hoodie", "top", "makehuman", "toigo_fisherman_sweater",
            colour=_c("707277"), roughness=0.87, hood=True, layer=LAYER_MID, tags=("hoodie",)),
    Garment("hoodie_black", "Black hoodie", "top", "makehuman", "toigo_fisherman_sweater",
            colour=_c("232427"), roughness=0.88, hood=True, layer=LAYER_MID, tags=("hoodie",)),
    Garment("kids_hoodie", "Kid's hoodie", "top", "makehuman", "toigo_fisherman_sweater",
            colour=_c("3f7bb5"), roughness=0.87, hood=True, layer=LAYER_MID, tags=("kids", "hoodie")),

    # ---------- outerwear: MakeHuman suit jackets (upper half of a one-mesh suit) -----------------------
    Garment("jacket_denim", "Denim jacket", "outerwear", "makehuman", "male_casualsuit01", keep="upper",
            colour=_c("3f5a78"), roughness=0.80, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("jacket_leather", "Black leather jacket", "outerwear", "makehuman", "male_casualsuit04",
            keep="upper", colour=_c("18181a"), roughness=0.38, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("jacket_bomber", "Olive bomber jacket", "outerwear", "makehuman", "male_casualsuit02",
            keep="upper", colour=_c("41452f"), roughness=0.62, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("suit_jacket_charcoal", "Charcoal suit jacket", "outerwear", "makehuman", "male_elegantsuit01",
            keep="upper", colour=_c("35373c"), roughness=0.66, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("suit_jacket_navy", "Navy suit jacket", "outerwear", "makehuman", "toigo_male_suit_3",
            keep="upper", colour=_c("222c40"), roughness=0.66, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("suit_jacket_womens", "Women's suit jacket", "outerwear", "makehuman", "toigo_female_suit_2",
            keep="upper", colour=_c("3a3644"), roughness=0.66, layer=LAYER_OUTER, tags=("suit", "office")),

    # ---------- outerwear: procedural, offset from the top layer ---------------------------------------
    Garment("puffer_black", "Black puffer jacket", "outerwear", "procedural",
            bones=TORSO + HIPS + UPPERARM + FOREARM, z_lo=0.40, z_hi=0.90, offset=0.026, thickness=0.010,
            colour=_c("161618"), roughness=0.55, quilt_rows=7, quilt_depth=0.010, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("puffer_olive", "Olive puffer jacket", "outerwear", "procedural",
            bones=TORSO + HIPS + UPPERARM + FOREARM, z_lo=0.40, z_hi=0.90, offset=0.026, thickness=0.010,
            colour=_c("4a4f35"), roughness=0.58, quilt_rows=7, quilt_depth=0.010, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("puffer_red_long", "Long red puffer", "outerwear", "procedural",
            bones=TORSO + HIPS + UPPERARM + FOREARM + THIGHS, z_lo=0.30, z_hi=0.90, offset=0.028,
            thickness=0.010, colour=_c("8c2320"), roughness=0.56, quilt_rows=11, quilt_depth=0.010,
            layer=LAYER_OUTER, tags=("puffer", "winter")),
    Garment("coat_wool", "Camel wool overcoat", "outerwear", "procedural",
            bones=TORSO + HIPS + UPPERARM + FOREARM + THIGHS, z_lo=0.32, z_hi=0.90, offset=0.018,
            thickness=0.008, colour=_c("9a7a51"), roughness=0.85, layer=LAYER_OUTER,
            tags=("coat", "winter")),
    Garment("coat_trench", "Beige trench coat", "outerwear", "procedural",
            bones=TORSO + HIPS + UPPERARM + FOREARM + THIGHS, z_lo=0.34, z_hi=0.90, offset=0.016,
            thickness=0.007, colour=_c("b6a488"), roughness=0.72, layer=LAYER_OUTER, tags=("coat", "rain")),
    Garment("vest_hivis", "ANSI class-2 hi-vis vest", "outerwear", "procedural", bones=TORSO + HIPS,
            z_lo=0.44, z_hi=0.855, offset=0.016, thickness=0.005, colour=_c("d8f000"), roughness=0.60,
            layer=LAYER_OUTER, tags=("hivis", "work"),
            notes="ANSI/ISEA 107 class 2 fluorescent yellow-green, torso only"),
    Garment("vest_delivery", "Insulated delivery vest", "outerwear", "procedural", bones=TORSO + HIPS,
            z_lo=0.42, z_hi=0.86, offset=0.022, thickness=0.008, colour=_c("1d1f22"), roughness=0.62,
            quilt_rows=5, quilt_depth=0.008, layer=LAYER_OUTER, tags=("delivery", "work")),
    Garment("vest_conedison", "Con-Ed orange work vest", "outerwear", "procedural", bones=TORSO + HIPS,
            z_lo=0.44, z_hi=0.855, offset=0.016, thickness=0.005, colour=_c("e8630a"), roughness=0.62,
            layer=LAYER_OUTER, tags=("hivis", "work")),

    # ---------- bottoms: real tailored MakeHuman meshes -------------------------------------------------
    Garment("jeans_indigo", "Indigo jeans", "bottom", "makehuman", "toigo_wool_pants",
            colour=_c("2f4260"), roughness=0.80, tags=("jeans",)),
    Garment("jeans_black", "Black jeans", "bottom", "makehuman", "toigo_wool_pants",
            colour=_c("1c1c1e"), roughness=0.82, tags=("jeans",)),
    Garment("chinos_khaki", "Khaki chinos", "bottom", "makehuman", "toigo_wool_pants",
            colour=_c("9c8a68"), roughness=0.80, tags=("chinos",)),
    Garment("suit_trousers", "Charcoal suit trousers", "bottom", "makehuman", "male_elegantsuit01",
            keep="lower", colour=_c("35373c"), roughness=0.70, tags=("suit", "office")),
    Garment("scrubs_pants", "Hospital scrubs trousers", "bottom", "makehuman", "toigo_wool_pants",
            colour=_c("2f6f6a"), roughness=0.80, tags=("scrubs", "work")),
    Garment("joggers_grey", "Grey joggers", "bottom", "makehuman", "toigo_harem_pants",
            colour=_c("6a6c70"), roughness=0.86, tags=("athleisure",)),
    Garment("cargo_olive", "Olive cargo trousers", "bottom", "makehuman", "cortu_cargo_pants",
            colour=_c("5a5d44"), roughness=0.84, tags=("cargo", "work")),
    Garment("kids_jeans", "Kid's jeans", "bottom", "makehuman", "toigo_wool_pants",
            colour=_c("39506f"), roughness=0.80, tags=("kids", "jeans")),

    # ---------- shoes: real MakeHuman meshes ------------------------------------------------------------
    Garment("sneakers_white", "White sneakers", "shoes", "makehuman", "shoes05",
            colour=_c("e9e7e2"), roughness=0.60, layer=LAYER_ACCESSORY, tags=("sneakers",)),
    Garment("sneakers_black", "Black sneakers", "shoes", "makehuman", "shoes05",
            colour=_c("1a1a1c"), roughness=0.62, layer=LAYER_ACCESSORY, tags=("sneakers",)),
    Garment("boots_work", "Tan work boots", "shoes", "makehuman", "shoes03",
            colour=_c("7a5228"), roughness=0.66, layer=LAYER_ACCESSORY, tags=("boots", "work")),
    Garment("shoes_dress", "Black dress shoes", "shoes", "makehuman", "shoes01",
            colour=_c("141416"), roughness=0.35, layer=LAYER_ACCESSORY, tags=("office",)),

    # ---------- head ------------------------------------------------------------------------------------
    Garment("hijab_navy", "Navy hijab", "hat", "procedural", bones=NECKHEAD + TORSO, z_lo=0.78, z_hi=1.02,
            offset=0.014, thickness=0.005, colour=_c("222b3d"), roughness=0.75, layer=LAYER_ACCESSORY,
            front_cut=0.035, tags=("hijab",),
            notes="drapes from the crown over the shoulders; covers hair, neck and the upper chest"),
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
            z_lo_m: float, z_hi_m: float, armature: bpy.types.Object | None = None) -> set[int]:
    accepted = set(garment.bones)
    matrix = mesh_obj.matrix_world
    face_plane = None
    if garment.front_cut is not None and armature is not None:
        bones = armature.data.bones
        forward = bones["ball_l"].tail_local - bones["ball_l"].head_local
        forward += bones["ball_r"].tail_local - bones["ball_r"].head_local
        forward.z = 0.0
        forward = forward.normalized()
        face_plane = (bones["head"].head_local, forward)
    out = set()
    for vert in mesh_obj.data.vertices:
        if dominant[vert.index] not in accepted:
            continue
        world = matrix @ vert.co
        if not (z_lo_m <= world.z <= z_hi_m):
            continue
        if face_plane is not None and dominant[vert.index] == "head":
            origin, forward = face_plane
            if (world - origin).dot(forward) > garment.front_cut:
                continue                       # leave the face open
        out.add(vert.index)
    return out


def build_garment(garment: Garment, body: bpy.types.Object, armature: bpy.types.Object,
                  dominant: list[str], body_height: float, *, name_prefix: str = "") -> bpy.types.Object:
    """Cut one procedural garment out of ``body`` (which may itself be a garment) and skin it.

    Cutting an outer layer from the garment already on the body is what keeps the sleeves, the armpit gap
    and the hem: offsetting the bare skin instead fuses the arms into the torso volume.
    """
    mesh = body.data
    z_lo = garment.z_lo * body_height
    z_hi = garment.z_hi * body_height
    region = _region(body, dominant, garment, z_lo, z_hi, armature)
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
    centre = neck - forward * 0.090 - Vector((0.0, 0.0, 0.030))
    radius = Vector((0.084, 0.100, 0.072))

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


def makehuman_assets(item_ids: tuple[str, ...]) -> tuple[str, ...]:
    """The MakeHuman ``.mhclo`` directories a wardrobe selection needs, in load order.

    These must be passed to ``mh_build.build_human`` because MakeClothes fits a garment through vertex
    correspondences into the *full* hm08 index space, which only exists before the helper geometry is
    stripped.
    """
    out: list[str] = []
    for item_id in item_ids:
        garment = WARDROBE_BY_ID.get(item_id)
        if garment is None:
            raise KeyError(f"unknown wardrobe item {item_id!r}")
        if garment.is_makehuman:
            out.append(garment.mhclo)          # one load per item: a suit can be worn as jacket *and*
    return tuple(out)                          # trousers, which needs two copies of the same asset


def procedural_items(item_ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(i for i in item_ids if not WARDROBE_BY_ID[i].is_makehuman)


def split_loose_parts(obj: bpy.types.Object, keep: str, split_z: float) -> int:
    """Keep only the loose shells of ``obj`` above (``keep="upper"``) or below (``"lower"``) ``split_z``.

    Several MakeHuman "casual suit" assets are a single mesh holding a jacket shell and a trouser shell.
    Splitting by connected component and comparing each component's centroid height gives a real tailored
    jacket or a real pair of trousers rather than an inseparable suit.
    """
    if keep == "all":
        return 0
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    parent = list(range(len(bm.verts)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for edge in bm.edges:
        ra, rb = find(edge.verts[0].index), find(edge.verts[1].index)
        if ra != rb:
            parent[ra] = rb
    groups: dict[int, list] = {}
    for vert in bm.verts:
        groups.setdefault(find(vert.index), []).append(vert)

    doomed = []
    for verts in groups.values():
        centre = sum((v.co.z for v in verts), 0.0) / len(verts)
        world_z = (obj.matrix_world @ Vector((0.0, 0.0, centre))).z
        above = world_z >= split_z
        if (keep == "upper") != above:
            doomed.extend(verts)
    if not doomed or len(doomed) == len(bm.verts):
        bm.free()
        return 0
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    removed = len(doomed)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return removed


_TINT_CACHE: dict[tuple[str, tuple[float, float, float]], bpy.types.Image] = {}


def _srgb_to_linear(values):
    import numpy as np  # noqa: PLC0415
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(values):
    import numpy as np  # noqa: PLC0415
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1.0 / 2.4) - 0.055)


def _tinted_image(image: bpy.types.Image, colour: tuple[float, float, float]) -> bpy.types.Image:
    """A copy of ``image`` reduced to luminance and multiplied by ``colour``.

    The tint is baked into the pixels rather than expressed as shader nodes, because glTF carries only a
    base-colour texture and a base-colour factor: a Mix/MapRange chain would be dropped on export and the
    garment would arrive in the engine wearing the asset author's original colour.
    """
    key = (image.name, tuple(round(c, 5) for c in colour))
    cached = _TINT_CACHE.get(key)
    if cached is not None:
        try:
            _ = cached.size[0]        # a datablock from a previous scene has been freed
            return cached
        except ReferenceError:
            _TINT_CACHE.pop(key, None)
    import numpy as np  # noqa: PLC0415

    width, height = image.size
    if width == 0 or height == 0:
        return image
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    pixels = buffer.reshape(-1, 4).astype(np.float64)
    srgb = image.colorspace_settings.name == "sRGB"
    rgb = _srgb_to_linear(pixels[:, :3]) if srgb else pixels[:, :3]
    luma = rgb[:, 0] * 0.2126 + rgb[:, 1] * 0.7152 + rgb[:, 2] * 0.0722
    # normalise the map's own brightness away so a dark asset texture does not darken the wardrobe colour
    mean = float(np.clip(luma.mean(), 1e-4, 1.0))
    band = np.clip(0.55 + 0.75 * (luma / mean), 0.25, 1.6)
    linear = np.empty_like(rgb)
    for channel in range(3):
        linear[:, channel] = np.clip(band * colour[channel], 0.0, 1.0)
    out = np.empty_like(pixels)
    out[:, :3] = _linear_to_srgb(linear) if srgb else linear
    out[:, 3] = pixels[:, 3]
    tinted = bpy.data.images.new(f"{image.name}.tint", width, height, alpha=True,
                                 float_buffer=image.is_float)
    tinted.colorspace_settings.name = image.colorspace_settings.name
    tinted.pixels.foreach_set(out.reshape(-1).astype(np.float32))
    tinted.pack()
    _TINT_CACHE[key] = tinted
    return tinted


def _texture_node(socket) -> bpy.types.Node | None:
    """Walk upstream from a shader socket to the first image texture node."""
    seen = set()
    stack = [socket]
    while stack:
        current = stack.pop()
        if not current.is_linked:
            continue
        node = current.links[0].from_node
        if node.name in seen:
            continue
        seen.add(node.name)
        if node.type == "TEX_IMAGE":
            return node
        stack.extend(node.inputs)
    return None


def thicken(obj: bpy.types.Object, thickness: float = 0.003) -> None:
    """Solidify a garment shell inwards.

    Not used on the shipped characters: the MakeHuman garments contain loose edges and coincident vertices
    that make ``bmesh.ops.solidify`` fan out spikes at the shoulder and hip.  Kept because it is the right
    operation for a clean shell, and because the procedural garments rely on the same bmesh call inside
    :func:`build_garment`, where the geometry is cut from the body and is manifold.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if not bm.faces:
        bm.free()
        return
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=-thickness)
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def tint(obj: bpy.types.Object, colour: tuple[float, float, float], roughness: float,
         metallic: float = 0.0, name: str = "") -> None:
    """Recolour a MakeHuman garment, keeping its texture only as light-and-shade fabric detail.

    The garment's own diffuse map already carries the asset author's colour, so multiplying the wardrobe
    colour into it gives muddy hues.  Instead the map is reduced to luminance, remapped into a 0.55-1.35
    shading band and multiplied by the wardrobe colour - baked into a new image, so the colour survives the
    glTF export.  A garment with no texture just gets a flat base colour.
    """
    for slot in obj.material_slots:
        material = slot.material
        if material is None or not material.use_nodes:
            continue
        material = material.copy()
        if name:
            material.name = name
        slot.material = material
        tree = material.node_tree
        bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        base = bsdf.inputs["Base Color"]
        texture = _texture_node(base)
        if texture is not None and texture.image is not None:
            texture.image = _tinted_image(texture.image, colour)
            for link in list(base.links):
                tree.links.remove(link)
            tree.links.new(texture.outputs["Color"], base)     # texture straight into base colour
        else:
            for link in list(base.links):
                tree.links.remove(link)
            base.default_value = (*colour, 1.0)


def finish_makehuman(built, item_ids: tuple[str, ...], *, name_prefix: str = "") -> dict[str, bpy.types.Object]:
    """Split, tint and rename the MakeHuman garments MPFB has already fitted. Returns ``{item_id: object}``.

    Called after ``mh_build.build_human`` and before the helper strip.
    """
    body = built.basemesh
    height = max((body.matrix_world @ v.co).z for v in body.data.vertices)
    by_asset: dict[str, list[bpy.types.Object]] = {}
    for obj in built.clothes.values():
        key = re.sub(r"\.\d{3}$", "", obj.name).split(".")[-1]
        by_asset.setdefault(key, []).append(obj)

    out: dict[str, bpy.types.Object] = {}
    for item_id in item_ids:
        garment = WARDROBE_BY_ID[item_id]
        if not garment.is_makehuman:
            continue
        pool = by_asset.get(garment.mhclo) or by_asset.get(garment.mhclo.replace("-", "_")) or []
        obj = next((o for o in pool if o.name not in {v.name for v in out.values()}), None)
        if obj is None:
            raise RuntimeError(f"MakeHuman asset {garment.mhclo!r} for {item_id!r} was not fitted "
                               f"(have {sorted(by_asset)})")
        removed = split_loose_parts(obj, garment.keep, garment.split_z * height)
        push = LAYER_MH_PUSH.get(garment.layer, 0.0)
        if push > 0.0:
            obj.data.calc_normals_split() if hasattr(obj.data, "calc_normals_split") else None
            for vert in obj.data.vertices:
                vert.co = vert.co + vert.normal * push
            obj.data.update()
        tint(obj, garment.colour, garment.roughness, garment.metallic, name=f"cloth_{item_id}")
        old = obj.name
        obj.name = obj.data.name = f"{name_prefix}{item_id}"
        built.clothes.pop(old, None)
        built.clothes[obj.name] = obj
        out[item_id] = obj
        log.info("%s: MakeHuman %s, %d verts%s", item_id, garment.mhclo, len(obj.data.vertices),
                 f", {removed} removed by the {garment.keep} split" if removed else "")
    return out


def reweight_from_body(built, item_ids: tuple[str, ...], *, name_prefix: str = "") -> list[str]:
    """Give every MakeHuman garment the body's own skin weights, by nearest vertex.

    MPFB weights a fitted garment by proximity to the base mesh, which is wrong wherever two body parts are
    close together: in the MakeHuman rest pose the hands hang beside the thighs, so trouser vertices pick up
    ``hand_*`` and finger weights and the hand tears a hand-shaped hole through the trouser leg as soon as
    it moves.  Taking each garment vertex's weights from its nearest *body* vertex uses MakeHuman's own
    anatomically-correct weighting instead, and inherits the 4-influence / sum-to-1 normalisation that
    ``rig_ue5.convert_to_ue5`` has just applied to the body.
    """
    done: list[str] = []
    for item_id in item_ids:
        garment = WARDROBE_BY_ID.get(item_id)
        if garment is None or not garment.is_makehuman:
            continue
        obj = built.clothes.get(f"{name_prefix}{item_id}")
        if obj is None:
            continue
        _transfer_weights(built.basemesh, obj)
        done.append(item_id)
    log.info("re-weighted %d MakeHuman garments from the body", len(done))
    return done


def dress(built, item_ids: tuple[str, ...], *, name_prefix: str = "") -> dict[str, bpy.types.Object]:
    """Cut the *procedural* wardrobe items and attach the hoods. Returns ``{item_id: object}``.

    Each procedural item is cut from the outermost garment already on the body that covers its region -
    normally the tee or the sweater - so it inherits real sleeves and a real armpit.
    """
    armature = built.armature
    deform = {b.name for b in armature.data.bones if b.use_deform}
    height = max((built.basemesh.matrix_world @ v.co).z for v in built.basemesh.data.vertices)
    out: dict[str, bpy.types.Object] = {}

    # hoods first: they belong to a MakeHuman sweater that is already on the body
    for item_id in item_ids:
        garment = WARDROBE_BY_ID[item_id]
        if garment.hood and garment.is_makehuman:
            obj = built.clothes.get(f"{name_prefix}{item_id}")
            if obj is not None:
                _add_hood(obj, armature, garment, height)

    base = _base_layer(built, name_prefix)
    for item_id in procedural_items(item_ids):
        garment = WARDROBE_BY_ID[item_id]
        source = base if (base is not None and garment.slot == "outerwear") else built.basemesh
        dominant = dominant_bones(source, deform)
        obj = build_garment(garment, source, armature, dominant, height, name_prefix=name_prefix)
        out[item_id] = obj
        built.clothes[obj.name] = obj
        log.info("%s: procedural, cut from %s, %d verts", item_id, source.name, len(obj.data.vertices))
    if out:
        log.info("tailored %d procedural garments onto %s", len(out), built.spec.name)
    return out


def _base_layer(built, name_prefix: str) -> bpy.types.Object | None:
    """The outermost torso garment already on the character, for procedural outerwear to be cut from."""
    best, best_layer = None, -1
    for obj in built.clothes.values():
        item_id = obj.name[len(name_prefix):] if obj.name.startswith(name_prefix) else obj.name
        garment = WARDROBE_BY_ID.get(item_id)
        if garment is None or garment.slot not in ("top",) or not garment.is_makehuman:
            continue
        if garment.layer > best_layer:
            best, best_layer = obj, garment.layer
    return best


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
    garment = Garment(f"hair_{style}", style, "hat", source="procedural", bones=("head",),
                      z_lo=0.0, z_hi=2.0, offset=0.004, thickness=0.002, colour=_c("2a2118"),
                      roughness=0.55)
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
