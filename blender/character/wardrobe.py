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
#: otherwise interpenetrate.  Applied by :func:`push_along_normals`, which tapers it to zero at the hem,
#: the cuffs and the collar - an outer layer stands off across the panels and is pinned at its edges,
#: which is both what a garment does and what stops the boundary loops turning into a saw-tooth.
LAYER_MH_PUSH = {LAYER_BASE: 0.0, LAYER_MID: 0.004, LAYER_OUTER: 0.011, LAYER_ACCESSORY: 0.0}

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
    includes_shirt: bool = False     # the mesh already contains the shirt worn under it (the suit jackets)
    push: float | None = None        # makehuman: override the layer's stand-off (a puffer is padded)
    flat_colour: bool = False        # ignore the asset's diffuse map: it carries a pattern we do not want
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
    # Both button shirts come off `male_casualsuit03`, whose shirt separates cleanly from its jeans by
    # connected component.  `male_casualsuit01` was tried first and abandoned: it welds its shirt and its
    # jeans into one shell, so the shirt can only be taken off it with a height cut, and the raw cut edge
    # lands above the waistband on a short wearer and tears a gap across the midriff.
    Garment("shirt_oxford", "Oxford button-down", "top", "makehuman", "male_casualsuit03", keep="upper",
            colour=_c("8d9aa8"), roughness=0.72, tags=("shirt", "office")),
    Garment("shirt_stripe", "Striped button shirt", "top", "makehuman", "male_casualsuit03", keep="upper",
            colour=_c("b9724f"), roughness=0.74, tags=("shirt",)),
    Garment("longsleeve_navy", "Navy long-sleeve tee", "top", "makehuman", "male_casualsuit02",
            keep="upper", colour=_c("2c3c56"), roughness=0.83, tags=("tee",)),
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

    # ---------- outerwear: MakeHuman jackets (the outermost shell of a one-mesh suit) -------------------
    # `keep="outer"` takes the jacket shell only - right for the field jacket, which is always worn over a
    # wardrobe top.  The suit jackets keep `"upper"`, because their shirt and tie are modelled as part of
    # the same upper assembly and a suit jacket with the shirt cut out of it opens onto nothing.
    # MakeHuman's CC0 packs contain exactly one casual jacket (`male_casualsuit05`, a four-pocket field
    # jacket) and four tailored suit jackets.  `jacket_field`, `jacket_denim` and `jacket_leather` are
    # therefore the same field-jacket mesh in three fabrics - stated here rather than implied.
    Garment("jacket_field", "Olive field jacket", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", colour=_c("4a4e39"), roughness=0.74, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("jacket_denim", "Denim jacket", "outerwear", "makehuman", "male_casualsuit05", keep="outer",
            colour=_c("3f5a78"), roughness=0.80, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("jacket_leather", "Black leather jacket", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", colour=_c("18181a"), roughness=0.34, layer=LAYER_OUTER, tags=("jacket",)),
    Garment("suit_jacket_charcoal", "Charcoal suit jacket", "outerwear", "makehuman", "male_elegantsuit01",
            keep="upper", colour=_c("35373c"), roughness=0.66, includes_shirt=True, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("suit_jacket_navy", "Navy suit jacket", "outerwear", "makehuman", "toigo_male_suit_3",
            keep="upper", colour=_c("222c40"), roughness=0.66, includes_shirt=True, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("suit_jacket_db", "Double-breasted suit jacket", "outerwear", "makehuman",
            "toigo_male_double-breasted_suit", keep="upper", colour=_c("2b3138"), roughness=0.66,
            includes_shirt=True, layer=LAYER_OUTER, tags=("suit", "office")),
    Garment("suit_jacket_womens", "Women's suit jacket", "outerwear", "makehuman", "toigo_female_suit_2",
            keep="upper", colour=_c("3a3644"), roughness=0.66, includes_shirt=True, layer=LAYER_OUTER, tags=("suit", "office")),

    # ---------- outerwear: procedural, offset from the top layer ---------------------------------------
    # MakeHuman's CC0 packs contain no puffer and no long coat, and an offset of the *skin* does not read as
    # one - cut from the body with sleeves and a hem it comes out as a painted-on body-suit, and cut from the
    # tee underneath it comes out as a t-shirt.  Both were built and rejected on the render.  So these five
    # are the field-jacket mesh in five fabrics, standing off further (`push`) where the garment is padded.
    # Stated, not implied: a "long" coat is therefore hip-length, and that is a fidelity gap (section 12).
    Garment("puffer_black", "Black puffer jacket", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", push=0.019, colour=_c("161618"), roughness=0.55, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("puffer_olive", "Olive puffer jacket", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", push=0.019, colour=_c("4a4f35"), roughness=0.58, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("puffer_red_long", "Long red puffer", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", push=0.022, colour=_c("8c2320"), roughness=0.56, layer=LAYER_OUTER,
            tags=("puffer", "winter")),
    Garment("coat_wool", "Camel wool overcoat", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", push=0.014, colour=_c("9a7a51"), roughness=0.85, layer=LAYER_OUTER,
            tags=("coat", "winter")),
    Garment("coat_trench", "Beige trench coat", "outerwear", "makehuman", "male_casualsuit05",
            keep="outer", push=0.013, colour=_c("b6a488"), roughness=0.72, layer=LAYER_OUTER,
            tags=("coat", "rain")),
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
    # `toigo_harem_pants` carries a large floral print in its diffuse map, and the tint keeps luminance
    # detail, so tinting it grey produced floral pyjamas.  Joggers are a flat fabric: the map is dropped.
    Garment("joggers_grey", "Grey joggers", "bottom", "makehuman", "toigo_harem_pants", flat_colour=True,
            colour=_c("6a6c70"), roughness=0.86, tags=("athleisure",)),
    Garment("cargo_olive", "Olive cargo trousers", "bottom", "makehuman", "cortu_cargo_pants",
            colour=_c("5a5d44"), roughness=0.84, tags=("cargo", "work")),
    Garment("kids_jeans", "Kid's jeans", "bottom", "makehuman", "toigo_wool_pants",
            colour=_c("39506f"), roughness=0.80, tags=("kids", "jeans")),
    Garment("shorts_denim", "Denim shorts", "bottom", "makehuman", "cortu_jeans_shorts",
            colour=_c("41618a"), roughness=0.80, tags=("shorts", "summer")),

    # ---------- shoes: real MakeHuman meshes ------------------------------------------------------------
    # What each `shoesNN` asset actually is was checked by fitting all six and rendering the foot, not taken
    # from the file name: 01 is a slip-on dress shoe, 02 and 06 are trainers, 03 is a chunky slip-on work
    # shoe, 04 is a lace-up oxford, 05 is a trainer.  Every one comes with its own sock.
    Garment("sneakers_white", "White trainers", "shoes", "makehuman", "shoes05",
            colour=_c("e9e7e2"), roughness=0.60, layer=LAYER_ACCESSORY, tags=("sneakers",)),
    Garment("sneakers_black", "Black trainers", "shoes", "makehuman", "shoes05",
            colour=_c("1a1a1c"), roughness=0.62, layer=LAYER_ACCESSORY, tags=("sneakers",)),
    Garment("sneakers_running", "Running shoes", "shoes", "makehuman", "shoes06",
            colour=_c("2f4a72"), roughness=0.58, layer=LAYER_ACCESSORY, tags=("sneakers",)),
    Garment("shoes_dress", "Black oxfords", "shoes", "makehuman", "shoes04",
            colour=_c("141416"), roughness=0.35, layer=LAYER_ACCESSORY, tags=("office", "dress")),
    Garment("shoes_loafer", "Brown loafers", "shoes", "makehuman", "shoes01",
            colour=_c("53341d"), roughness=0.42, layer=LAYER_ACCESSORY, tags=("office", "dress")),
    Garment("shoes_work", "Slip-on work shoes", "shoes", "makehuman", "shoes03",
            colour=_c("2a2622"), roughness=0.66, layer=LAYER_ACCESSORY, tags=("work",)),

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
                  dominant: list[str], body_height: float, *, name_prefix: str = "",
                  colour: tuple[float, float, float] | None = None) -> bpy.types.Object:
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
    # Clean the cut before offsetting it.  A procedural layer is cut from whatever is outermost on the body,
    # which is usually a MakeHuman garment, and those CC0 meshes carry coincident vertices, degenerate faces
    # and inconsistent winding.  `bmesh.ops.solidify` on that fans out spikes: the hi-vis vest cut from a
    # fitted sweater came out 2.3 m tall and 4.0 m deep and made a 2.51 m "pedestrian".
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=2e-5, edges=list(bm.edges))
    bm.verts.ensure_lookup_table()
    stray = [v for v in bm.verts if not v.link_faces]
    if stray:
        bmesh.ops.delete(bm, geom=stray, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    if not bm.faces:
        bm.free()
        raise RuntimeError(f"garment {garment.item_id!r} has no faces left after cleaning the cut")

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

    shell = _bounds_of(bm)
    single_sided = bpy.data.meshes.new(f"{name_prefix}{garment.item_id}.shell")
    bm.to_mesh(single_sided)                       # keep the un-thickened shell to fall back to
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=-garment.thickness)
    bm.normal_update()
    thick = _bounds_of(bm)
    slack = 8.0 * garment.thickness + 1e-4
    grew = max(max(a - b for a, b in zip(shell[0], thick[0])),
               max(b - a for a, b in zip(shell[1], thick[1])))
    if grew > slack:
        log.warning("%s: solidify grew the garment by %.0f mm (limit %.0f mm) - shipping the single-sided "
                    "shell instead", garment.item_id, grew * 1000.0, slack * 1000.0)
        bm.clear()
        bm.from_mesh(single_sided)
        bm.normal_update()
    bpy.data.meshes.remove(single_sided)

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
                               base_color=(*(colour or garment.colour), 1.0), roughness=garment.roughness,
                               metallic=garment.metallic)
    new_mesh.materials.append(material)

    obj.parent = armature
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    return obj


def _bounds_of(bm) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """(min, max) corner of a bmesh, for the sanity check around ``bmesh.ops.solidify``."""
    xs = [v.co for v in bm.verts]
    if not xs:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    return ((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)),
            (max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))


def _transfer_weights(body: bpy.types.Object, garment_obj: bpy.types.Object) -> None:
    """Give every garment vertex the weights of its nearest body vertex.

    A garment vertex is at most ``offset + thickness`` (< 5 cm) from the skin vertex it was cut from, and
    ``bmesh.ops.solidify`` does not preserve vertex order, so the nearest-neighbour lookup is both exact in
    practice and independent of the topology operations above it.

    Every vertex group already on the garment is **removed first**.  A MakeHuman garment arrives from MPFB
    carrying its own proximity-fitted groups under the very names this function is about to write, and
    ``vertex_groups.new`` does not overwrite: it would create ``spine_05.001`` beside ``spine_05``, so the
    correct weights would land in groups no bone matches and the armature would keep deforming the garment
    with MPFB's proximity weights.  That is exactly the bug that put ``hand_*`` and ``foot_*`` influences on
    a jacket.  Clearing first also drops MakeHuman's bookkeeping groups (``Delete.*``, ``Left``/``Mid``/
    ``Right``, ``body``), which are meaningless on a garment and would otherwise propagate to any
    procedural layer cut from it.
    """
    from mathutils import kdtree  # noqa: PLC0415

    for stale in list(garment_obj.vertex_groups):
        garment_obj.vertex_groups.remove(stale)

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


def push_along_normals(obj: bpy.types.Object, distance: float, *, taper_rings: int = 3,
                       smooth_passes: int = 2) -> None:
    """Stand a fitted garment off the layer below it, without wrecking its hem, cuffs or collar.

    MakeHuman fits every garment at its own designed stand-off, so a jacket and a sweater fitted to the same
    body interpenetrate; an outer layer has to be pushed out.  A naive ``vert.co += vert.normal * d`` does
    two damaging things:

    * on an **open boundary** - the neck hole, the cuffs, the hem - a vertex normal is the average of the
      few faces on one side only, so consecutive boundary vertices tilt in alternating directions and the
      edge comes out as a saw-tooth.  That is the "jagged polygon fragments around the collar" this build
      used to show;
    * it inflates the garment uniformly, so a jacket balloons instead of draping.

    Here the push is a *field*: raw vertex normals are Laplacian-smoothed over the edge graph, and the
    amount is tapered to zero across ``taper_rings`` rings of the open boundary, so the hem, the cuffs and
    the collar stay exactly where the tailor put them and only the panels in between stand off.
    """
    if distance <= 0.0 or not len(obj.data.vertices):
        return
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.index_update()
    bm.normal_update()

    normals = [v.normal.copy() for v in bm.verts]
    for _ in range(max(smooth_passes, 0)):
        nxt: list[Vector] = []
        for vert in bm.verts:
            acc = normals[vert.index].copy()
            for edge in vert.link_edges:
                acc += normals[edge.other_vert(vert).index]
            nxt.append(acc.normalized() if acc.length > 1e-9 else normals[vert.index])
        normals = nxt

    far = taper_rings + 1
    ring = [far] * len(bm.verts)
    frontier = []
    for vert in bm.verts:
        if not vert.link_faces or any(len(e.link_faces) < 2 for e in vert.link_edges):
            ring[vert.index] = 0
            frontier.append(vert)
    depth = 0
    while frontier and depth < taper_rings:
        depth += 1
        nxt_verts = []
        for vert in frontier:
            for edge in vert.link_edges:
                other = edge.other_vert(vert)
                if ring[other.index] > depth:
                    ring[other.index] = depth
                    nxt_verts.append(other)
        frontier = nxt_verts

    for vert in bm.verts:
        taper = _smoothstep(min(ring[vert.index], taper_rings) / float(max(taper_rings, 1)))
        if taper > 0.0:
            vert.co += normals[vert.index] * (distance * taper)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def _add_hood(obj: bpy.types.Object, armature: bpy.types.Object, garment: Garment,
              body_height: float) -> None:
    """A hood lying *down*: a thick roll of the same cloth around the back of the collar.

    Down, a hood is not a dome behind the head - it is a bunched cylinder of fabric that follows the collar
    round the back of the neck and tapers out towards the collarbones.  Two earlier shapes were built and
    rejected on the render before this one:

    * a half-ellipsoid placed from the neck joint - most of it ends up inside the sweater, because the back
      panel of a knitted sweater is 100-140 mm behind the neck joint and by a distance that depends on the
      body, so what showed was a few fragments;
    * the same ellipsoid projected outwards onto the garment surface - projecting every vertex flattens the
      volume away and leaves a crumpled skin.

    So the roll is *swept along the garment itself*: the collar line is found by asking the garment for the
    closest surface point on a ring of directions around the neck axis, and a tube is swept along those
    points, standing off along each point's own surface normal.  That puts it on the sweater whatever shape
    the sweater is, and keeps its volume.  Each ring is UV-mapped from the nearest garment vertex, so the
    hood is shaded by the same knit texture, and it is weighted 55/45 to ``neck_01``/``spine_05``.
    """
    from mathutils import kdtree  # noqa: PLC0415

    bones = armature.data.bones
    neck = bones["neck_01"].head_local
    forward = (bones["ball_l"].tail_local - bones["ball_l"].head_local)
    forward.z = 0.0
    forward = forward.normalized() if forward.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    back = -forward
    right = forward.cross(Vector((0.0, 0.0, 1.0))).normalized()
    scale = body_height / 1.75

    span = math.radians(86.0)                       # from straight back round towards the collarbones
    segments = 13
    centre = neck + Vector((0.0, 0.0, -0.028 * scale))
    path: list[tuple[Vector, Vector]] = []          # (surface point, outward normal)
    for i in range(segments):
        t = -1.0 + 2.0 * i / (segments - 1)
        angle = t * span
        direction = (back * math.cos(angle) + right * math.sin(angle)).normalized()
        # Ray-cast horizontally *inwards* at the collar height rather than asking for the nearest surface
        # point: from a probe out at the side the nearest point is the top of the shoulder, and the roll
        # then spans the shoulders like a yoke instead of following the collar.
        origin = centre + direction * (0.45 * scale)
        hit, location, normal, _index = obj.ray_cast(origin, -direction, distance=0.45 * scale)
        if not hit:
            continue
        if normal.dot(direction) < 0.0:
            normal = -normal
        path.append((location, normal.normalized()))
    if len(path) < 4:
        log.warning("%s: could not trace a collar line for the hood", obj.name)
        return

    ring_count = 8
    bm = bmesh.new()
    rings: list[list] = []
    for i, (point, normal) in enumerate(path):
        t = -1.0 + 2.0 * i / (len(path) - 1)
        thickness = (0.044 - 0.020 * t * t) * scale          # thickest at the nape, tapering to the front
        nxt = path[min(i + 1, len(path) - 1)][0]
        prv = path[max(i - 1, 0)][0]
        tangent = (nxt - prv)
        tangent = tangent.normalized() if tangent.length > 1e-6 else right.copy()
        side = tangent.cross(normal).normalized()
        hub = point + normal * (thickness * 0.85)
        ring = []
        for k in range(ring_count):
            a = 2.0 * math.pi * k / ring_count
            offset = normal * (math.cos(a) * thickness) + side * (math.sin(a) * thickness * 0.78)
            ring.append(bm.verts.new(hub + offset))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        for k in range(ring_count):
            a, b = rings[i][k], rings[i][(k + 1) % ring_count]
            c, d = rings[i + 1][(k + 1) % ring_count], rings[i + 1][k]
            bm.faces.new((a, b, c, d))
    for ring in (rings[0], rings[-1]):               # cap the two open ends
        bm.faces.new(ring if ring is rings[0] else list(reversed(ring)))
    bm.normal_update()
    hood_mesh = bpy.data.meshes.new(f"{obj.name}.hood")
    bm.to_mesh(hood_mesh)
    bm.free()

    uv_layer = obj.data.uv_layers.active
    source_uv: list[tuple[float, float]] = [(0.0, 0.0)] * len(obj.data.vertices)
    if uv_layer is not None:
        for loop in obj.data.loops:
            source_uv[loop.vertex_index] = tuple(uv_layer.data[loop.index].uv)
    tree = kdtree.KDTree(len(obj.data.vertices))
    for vert in obj.data.vertices:
        tree.insert(vert.co, vert.index)
    tree.balance()

    vertex_offset = len(obj.data.vertices)
    face_offset = len(obj.data.polygons)
    obj.data = _join_meshes(obj.data, hood_mesh)

    uv_layer = obj.data.uv_layers.active
    for polygon in obj.data.polygons[face_offset:]:
        polygon.use_smooth = True
        polygon.material_index = 0
        if uv_layer is None:
            continue
        for loop_index in polygon.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[loop_index].vertex_index]
            _co, nearest, _distance = tree.find(vertex.co)
            uv_layer.data[loop_index].uv = source_uv[nearest]

    for name, weight in (("neck_01", 0.55), ("spine_05", 0.45)):
        group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        group.add(list(range(vertex_offset, len(obj.data.vertices))), weight, "REPLACE")
    log.info("%s: hood added - %d-point collar roll, %d vertices", obj.name, len(path),
             len(obj.data.vertices) - vertex_offset)


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
    """Keep only some of the loose shells of ``obj``; return the number of vertices removed.

    Several MakeHuman "casual suit" assets are a single mesh holding several shells - a jacket, the shirt
    under it and a pair of trousers.  Splitting by connected component gives a real tailored garment
    instead of an inseparable suit:

    ``"all"``      keep everything (a t-shirt, a pair of trousers, a shoe pair);
    ``"upper"``    keep every shell whose centroid is above ``split_z`` (jacket *and* the shirt under it);
    ``"lower"``    keep every shell whose centroid is below it (the trousers);
    ``"outer"``    keep only the *outermost* upper shell - the jacket without the shirt inside it.  The
                   outermost shell is the one with the largest horizontal footprint: a jacket encloses the
                   shirt, so its bounding box in x/y is strictly the larger of the two.  Shells smaller
                   than a tenth of the largest are ignored as trim (collars, cuffs, buttons) so a stray
                   scrap of geometry cannot win the comparison.
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

    want_upper = keep in ("upper", "outer")
    upper: list[list] = []
    doomed = []
    for verts in groups.values():
        centre = sum((v.co.z for v in verts), 0.0) / len(verts)
        world_z = (obj.matrix_world @ Vector((0.0, 0.0, centre))).z
        above = world_z >= split_z
        if want_upper != above:
            doomed.extend(verts)
        else:
            upper.append(verts)

    if keep == "outer" and len(upper) > 1:
        def footprint(verts) -> float:
            xs = [v.co.x for v in verts]
            ys = [v.co.y for v in verts]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))

        biggest = max(len(v) for v in upper)
        candidates = [v for v in upper if len(v) >= 0.10 * biggest]
        winner = max(candidates, key=footprint)
        for verts in upper:
            if verts is not winner:
                doomed.extend(verts)
        log.info("%s: 'outer' split kept the %d-vertex shell with footprint %.4f m2 of %d candidates",
                 obj.name, len(winner), footprint(winner), len(candidates))
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
         metallic: float = 0.0, name: str = "", flat: bool = False) -> None:
    """Recolour a MakeHuman garment, keeping its texture only as light-and-shade fabric detail.

    The garment's own diffuse map already carries the asset author's colour, so multiplying the wardrobe
    colour into it gives muddy hues.  Instead the map is reduced to luminance, remapped into a 0.55-1.35
    shading band and multiplied by the wardrobe colour - baked into a new image, so the colour survives the
    glTF export.  A garment with no texture just gets a flat base colour.

    ``flat`` drops the map entirely.  Luminance detail is fabric detail only when the map *is* fabric
    detail: `toigo_harem_pants` carries a large floral print, and keeping its luminance turned grey joggers
    into floral pyjamas.
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
        if flat:
            texture = None
        if texture is not None and texture.image is not None:
            texture.image = _tinted_image(texture.image, colour)
            for link in list(base.links):
                tree.links.remove(link)
            tree.links.new(texture.outputs["Color"], base)     # texture straight into base colour
        else:
            for link in list(base.links):
                tree.links.remove(link)
            base.default_value = (*colour, 1.0)


def finish_makehuman(built, item_ids: tuple[str, ...], *, name_prefix: str = "",
                     colours: dict[str, tuple[float, float, float]] | None = None
                     ) -> dict[str, bpy.types.Object]:
    """Split, tint and rename the MakeHuman garments MPFB has already fitted. Returns ``{item_id: object}``.

    Called after ``mh_build.build_human`` and before the helper strip.  ``colours`` overrides the wardrobe
    catalogue colour per item id - that is how the pedestrian variety vector's twelve top colours and twelve
    bottom colours reach the mesh, without needing twelve copies of every garment in the catalogue.
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
        push = garment.push if garment.push is not None else LAYER_MH_PUSH.get(garment.layer, 0.0)
        push_along_normals(obj, push)
        colour = (colours or {}).get(item_id, garment.colour)
        tint(obj, colour, garment.roughness, garment.metallic, name=f"cloth_{item_id}",
             flat=garment.flat_colour)
        old = obj.name
        obj.name = obj.data.name = f"{name_prefix}{item_id}"
        built.clothes.pop(old, None)
        built.clothes[obj.name] = obj
        out[item_id] = obj
        log.info("%s: MakeHuman %s, %d verts%s", item_id, garment.mhclo, len(obj.data.vertices),
                 f", {removed} removed by the {garment.keep} split" if removed else "")
    return out


def verify_outfit(built, item_ids: tuple[str, ...], *, name_prefix: str = "",
                  margin: float = 0.30) -> list[str]:
    """Check every garment on the character is where a garment can be. Returns a list of problems.

    A procedural cut that goes wrong does not fail loudly - it produces a mesh with a few vertices thrown to
    infinity, which then quietly widens the exported bounding box and, because stature is measured from the
    scene, reports a 2.5 m pedestrian.  So every finished garment is checked against the body's own bounding
    box grown by ``margin``: nothing a person wears is a third of a metre away from them, and anything that
    is, is broken.  Also catches non-finite coordinates, which a degenerate normal can produce.
    """
    body = built.basemesh
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for vert in body.data.vertices:
        world = body.matrix_world @ vert.co
        lo = Vector(map(min, lo, world))
        hi = Vector(map(max, hi, world))
    lo -= Vector((margin,) * 3)
    hi += Vector((margin,) * 3)

    problems: list[str] = []
    for item_id in item_ids:
        obj = built.clothes.get(f"{name_prefix}{item_id}")
        if obj is None or not len(obj.data.vertices):
            problems.append(f"{item_id}: not on the character")
            continue
        bad = 0
        worst = 0.0
        for vert in obj.data.vertices:
            world = obj.matrix_world @ vert.co
            if not all(math.isfinite(c) for c in world):
                problems.append(f"{item_id}: non-finite vertex coordinate")
                bad = -1
                break
            over = max(max(lo[i] - world[i] for i in range(3)), max(world[i] - hi[i] for i in range(3)))
            if over > 0.0:
                bad += 1
                worst = max(worst, over)
        if bad > 0:
            problems.append(f"{item_id}: {bad} of {len(obj.data.vertices)} vertices up to "
                            f"{worst * 1000:.0f} mm outside the body's bounding box + {margin * 1000:.0f} mm")
    return problems


def hide_covered_garments(built, item_ids: tuple[str, ...], *, name_prefix: str = "",
                          reach: float = 0.045) -> int:
    """Delete the parts of an inner garment that another garment completely covers.  Returns faces removed.

    A base layer worn under a fitted sweater has to satisfy two constraints at once - outside the skin and
    inside the sweater - and where the sweater hugs the body there is simply no room between them.  Resolving
    the two against each other then trades one artefact for another: pull the tee in and scraps of skin show
    through the trousers, push it out and white specks of tee show through the knit.

    The way out is that the covered part of the tee is not needed at all.  Nobody sees it, the engine does not
    need it, and MakeHuman's own delete groups do exactly this for the skin.  So every inner-garment vertex
    whose own normal points into an outer garment within ``reach`` is marked, and a face is deleted when all
    of its vertices are marked - which keeps the collar, the cuffs and the hem, the parts that actually show,
    and removes the sandwiched middle.  It also takes several thousand vertices out of the export.
    """
    ordered: list[tuple[int, str, bpy.types.Object]] = []
    for item_id in item_ids:
        garment = WARDROBE_BY_ID.get(item_id)
        obj = built.clothes.get(f"{name_prefix}{item_id}")
        if garment is None or obj is None or garment.slot == "shoes":
            continue
        ordered.append((_layer_key(garment), item_id, obj))
    if len(ordered) < 2:
        return 0
    ordered.sort(key=lambda t: t[0])

    removed = 0
    for i, (key_in, item_id, inner) in enumerate(ordered):
        outers = [o for k, _i, o in ordered[i + 1:] if k > key_in and len(o.data.vertices)]
        if not outers:
            continue
        covered = set()
        for vert in inner.data.vertices:
            origin = vert.co + vert.normal * 0.0005
            for outer in outers:
                hit, _location, _normal, _index = outer.ray_cast(origin, vert.normal, distance=reach)
                if hit:
                    covered.add(vert.index)
                    break
        if not covered:
            continue
        bm = bmesh.new()
        bm.from_mesh(inner.data)
        bm.verts.ensure_lookup_table()
        doomed = [f for f in bm.faces if all(v.index in covered for v in f.verts)]
        if not doomed or len(doomed) == len(bm.faces):
            bm.free()
            continue
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bm.verts.ensure_lookup_table()
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        count = len(doomed)
        bm.to_mesh(inner.data)
        bm.free()
        inner.data.update()
        removed += count
        log.info("%s: %d covered faces removed, %d vertices remain", item_id, count,
                 len(inner.data.vertices))
    return removed


def _layer_key(garment: Garment) -> int:
    """Sort key for what is worn over what.

    Two garments with the same :attr:`Garment.layer` still have an order: the base top goes *inside* the
    waistband and the trousers close over it, while a sweater or a jacket hangs outside them.  So a bottom
    ranks one step above a base-layer top and below everything above that.  Without the distinction the tee
    hem and the jeans waistband simply interpenetrate, and the overlap renders as white scraps of tee
    sticking through the seat of the trousers.
    """
    return garment.layer * 2 + (1 if garment.slot == "bottom" else 0)


def resolve_layers(built, item_ids: tuple[str, ...], *, name_prefix: str = "",
                   clearance: float = 0.006, passes: int = 5) -> int:
    """Pull every inner garment back inside the garment layered over it.  Returns vertices moved.

    Two garments fitted independently to the same body do not know about each other: MakeHuman gives each
    its own designed stand-off, so a tee's shoulder seam can sit *outside* a sweater's shoulder and shows as
    a white patch through it.  Pushing the outer layer out (:func:`push_along_normals`) fixes the average
    case but not the tight spots, because the clearance needed is not constant over a garment.

    So the outer layer gets the last word.  For every vertex of an inner garment the *closest point on the
    outer garment's surface* is taken (``closest_point_on_mesh``, i.e. against the real triangles and their
    face normals, not against the nearest vertex - a coarse outer mesh has vertices whose normals point
    nowhere near the surface the inner vertex is poking through).  If the inner vertex is outside that
    surface, or within ``clearance`` of it, it is moved back along the face normal until it is ``clearance``
    inside.  Vertices further than ``reach`` from the outer garment - a tee hem below a jacket, a collar
    above it - are left exactly where the tailor put them, so this never shrink-wraps.
    """
    ordered: list[tuple[int, str, bpy.types.Object]] = []
    shoes: list[bpy.types.Object] = []
    bottoms: list[bpy.types.Object] = []
    for item_id in item_ids:
        garment = WARDROBE_BY_ID.get(item_id)
        obj = built.clothes.get(f"{name_prefix}{item_id}")
        if garment is None or obj is None:
            continue
        if garment.slot == "shoes":
            shoes.append(obj)
            continue
        if garment.slot == "bottom":
            bottoms.append(obj)
        ordered.append((_layer_key(garment), item_id, obj))
    ordered.sort(key=lambda t: t[0])

    reach = 0.05
    moved = 0

    # Two constraints, alternated to convergence, because they fight each other: no garment may be inside
    # the skin, and no inner garment may be outside the layer over it.  Pulling the tee inside the trousers
    # can push it inside the body; pushing it back out of the body can push it outside the trousers.  Doing
    # each once, in either order, leaves scraps of skin showing through the seat of the trousers in every
    # frame of the walk cycle - which is what the first version did.
    body = built.basemesh
    for _ in range(max(passes, 1)):
        pass_moved = 0
        for _key, _item_id, garment_obj in ordered:
            pass_moved += _move_outside(garment_obj, body, clearance, reach=0.035)
        for i, (key_in, _id_in, inner) in enumerate(ordered):
            for key_out, _id_out, outer in ordered[i + 1:]:
                if key_out <= key_in or not len(outer.data.vertices):
                    continue
                pass_moved += _move_inside(inner, outer, clearance, reach)
        moved += pass_moved
        if pass_moved == 0:
            break
    for _key, _item_id, garment_obj in ordered:            # the skin gets the last word
        moved += _move_outside(garment_obj, body, clearance, reach=0.035)

    # Shoes are the one pair the rule above cannot express: a trouser leg drapes *over* the shoe, but the
    # shoe is a rigid object that must not be dented to make room, so it is the trouser that moves - outward,
    # out of the shoe - instead of the inner layer moving in.
    for shoe in shoes:
        for bottom in bottoms:
            moved += _move_outside(bottom, shoe, clearance, reach=0.04)
    if moved:
        log.info("layer resolve: moved %d garment vertices to keep each layer inside the one over it", moved)
    return moved


def _move_inside(inner: bpy.types.Object, outer: bpy.types.Object, clearance: float,
                 reach: float) -> int:
    """Pull ``inner``'s vertices to at least ``clearance`` behind ``outer``'s surface."""
    moved = 0
    for vert in inner.data.vertices:
        hit, location, normal, _index = outer.closest_point_on_mesh(vert.co, distance=reach)
        if not hit:
            continue
        depth = (vert.co - location).dot(normal)
        if depth > -clearance:
            vert.co = vert.co - normal * (depth + clearance)
            moved += 1
    inner.data.update()
    return moved


def _move_outside(garment: bpy.types.Object, solid: bpy.types.Object, clearance: float,
                  reach: float) -> int:
    """Push ``garment``'s vertices to at least ``clearance`` outside ``solid``'s surface."""
    moved = 0
    for vert in garment.data.vertices:
        hit, location, normal, _index = solid.closest_point_on_mesh(vert.co, distance=reach)
        if not hit:
            continue
        depth = (vert.co - location).dot(normal)
        if depth < clearance:
            vert.co = vert.co + normal * (clearance - depth)
            moved += 1
    garment.data.update()
    return moved


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


def dress(built, item_ids: tuple[str, ...], *, name_prefix: str = "",
          colours: dict[str, tuple[float, float, float]] | None = None) -> dict[str, bpy.types.Object]:
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
    torso_only = set(TORSO) | set(HIPS)
    for item_id in procedural_items(item_ids):
        garment = WARDROBE_BY_ID[item_id]
        # A procedural layer can only be as long and as sleeved as the surface it is cut from.  A vest covers
        # nothing but the torso, so cutting it from the garment already on the body is right and keeps that
        # garment's armpit.  A puffer or a long coat has sleeves to the wrist and a hem at the thigh, and
        # cutting *those* from a short-sleeved tee produced a beige t-shirt labelled "trench coat" - so
        # anything reaching past the torso is cut from the body, which has arms and legs.
        covers_torso_only = bool(garment.bones) and set(garment.bones) <= torso_only
        source = base if (base is not None and garment.slot == "outerwear" and covers_torso_only) \
            else built.basemesh
        dominant = dominant_bones(source, deform)
        obj = build_garment(garment, source, armature, dominant, height, name_prefix=name_prefix,
                            colour=(colours or {}).get(item_id))
        out[item_id] = obj
        built.clothes[obj.name] = obj
        log.info("%s: procedural, cut from %s, %d verts", item_id, source.name, len(obj.data.vertices))
    if out:
        log.info("tailored %d procedural garments onto %s", len(out), built.spec.name)
    return out


def _base_layer(built, name_prefix: str) -> bpy.types.Object | None:
    """The outermost torso garment already on the character, for procedural outerwear to be cut from.

    Outerwear counts as well as tops: a hi-vis vest worn over a suit jacket has to be cut from the jacket,
    not from the shirt underneath it, or it ends up inside the jacket.
    """
    best, best_layer = None, -1
    for obj in built.clothes.values():
        item_id = obj.name[len(name_prefix):] if obj.name.startswith(name_prefix) else obj.name
        garment = WARDROBE_BY_ID.get(item_id)
        if garment is None or garment.slot not in ("top", "outerwear") or not garment.is_makehuman:
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
    "shoulder_bag": {"size": (0.24, 0.10, 0.20), "bone": "spine_02", "behind": -0.02, "up": -0.09,
                     "side": 1.0, "colour": _c("4a3423"), "roughness": 0.55},
    "delivery_box": {"size": (0.34, 0.32, 0.34), "bone": "spine_04", "behind": 0.14, "up": 0.06,
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
    """A carried item, rigidly weighted to one bone and placed against the body it is carried on.

    Two things a naive placement gets wrong, both of which showed in the first NPC line-up:

    * **it does not scale.** A 0.40 m courier box is placed 0.14 m behind an adult's chest bone and clears
      the chest; on an eight-year-old the same box reaches 0.06 m out of the *front* of the torso. Every
      dimension and offset here is scaled by the character's own stature.
    * **it does not know where the body's surface is.** So a torso bag is now placed by ray-casting
      backwards from the bone through the outermost garment and putting the bag's front face 12 mm behind
      the surface it finds - the bag sits on the back whatever the wearer's build and whatever they are
      wearing.

    A bag carried in the hand or on the forearm is built in the **bone's own frame**, not in world axes: in
    the MakeHuman rest pose the arm points sideways, and a bag authored "below the hand" in world Z ends up
    horizontal as soon as the arm hangs. Along the bone's axis it hangs correctly in any pose, because the
    bone axis is what points downwards once the arm is down.
    """
    spec = BAG_SPECS.get(kind)
    if spec is None:
        raise KeyError(f"unknown bag {kind!r}")
    armature = built.armature
    bones = armature.data.bones
    bone = bones[spec["bone"]]
    body = built.basemesh
    height = max((body.matrix_world @ v.co).z for v in body.data.vertices)
    scale = height / 1.75

    forward = bones["ball_l"].tail_local - bones["ball_l"].head_local
    forward.z = 0.0
    forward = forward.normalized() if forward.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    right = forward.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = Vector((0.0, 0.0, 1.0))

    sx, sy, sz = (v * scale for v in spec["size"])
    on_arm = spec["bone"].startswith(("hand_", "lowerarm_", "upperarm_"))
    if on_arm:
        # the bone's own frame: its axis is "down" once the arm hangs
        axis = (bone.tail_local - bone.head_local).normalized()
        side = axis.cross(forward)
        side = side.normalized() if side.length > 1e-6 else right.copy()
        depth = side.cross(axis).normalized()
        centre = bone.head_local + axis * (abs(spec["up"]) * scale + sz * 0.5)
        ex, ey, ez = side, depth, axis
    else:
        centre = (bone.head_local + bone.tail_local) * 0.5 + up * (spec["up"] * scale)
        outer = _outermost_torso_mesh(built, name_prefix) or body
        side_offset = spec.get("side", 0.0)
        if side_offset:
            # a shoulder bag hangs against the *side* of the body, so find that surface rather than
            # trusting a fixed 170 mm, which floats clear of a slim wearer and buries itself in a wide one
            direction = right if side_offset > 0 else -right
            probe = centre + direction * (0.60 * scale)
            flank = _first_surface(centre, direction, 0.60 * scale, outer, body)
            flank = flank if flank is not None else centre + direction * (0.16 * scale)
            centre = flank + direction * (sx * 0.5 + 0.010 * scale)
        back = _first_surface(centre, -forward, 0.60 * scale, outer, body)
        back = back if back is not None else centre - forward * (0.10 * scale)
        if side_offset:
            centre = centre - forward * (sy * 0.5)          # a side bag sits level with the body, not behind
        else:
            centre = back - forward * (sy * 0.5 + 0.012 * scale)
        ex, ey, ez = right, forward, up

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for vert in bm.verts:
        local = Vector((vert.co.x * sx, vert.co.y * sy, vert.co.z * sz))
        vert.co = ex * local.x + ey * local.y + ez * local.z + centre
    bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                    offset=0.012 * scale, segments=2, affect="EDGES")
    mesh = bpy.data.meshes.new(f"{name_prefix}bag_{kind}")
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(nb.pbr_material(f"bag_{kind}", base_color=(*spec["colour"], 1.0),
                                          roughness=spec["roughness"]))
    obj = bpy.data.objects.new(f"{name_prefix}bag_{kind}", mesh)
    body.users_collection[0].objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    group = obj.vertex_groups.new(name=spec["bone"])
    group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    obj.parent = armature
    obj.modifiers.new("Armature", "ARMATURE").object = armature
    built.clothes[obj.name] = obj
    log.info("%s: %s bag on %s, %.0f x %.0f x %.0f mm", built.spec.name, kind, spec["bone"],
             sx * 1000, sy * 1000, sz * 1000)
    return obj


def _first_surface(origin: Vector, direction: Vector, reach: float, *candidates):
    """Cast inwards from ``reach`` out along ``direction`` and return the first surface hit, or None.

    Tries each candidate mesh in turn: a bag placed against a garment must fall back to the skin, because
    a tank top has no fabric at hip height and a ray that misses would otherwise leave the bag floating a
    hand's width clear of the body.
    """
    start = origin + direction * reach
    for mesh in candidates:
        if mesh is None:
            continue
        hit, location, _normal, _index = mesh.ray_cast(start, -direction, distance=reach)
        if hit:
            return location
    return None


def _outermost_torso_mesh(built, name_prefix: str):
    """The garment a torso-mounted bag rests against, or None if the character is not dressed there."""
    best, best_layer = None, -1
    for obj in built.clothes.values():
        item_id = obj.name[len(name_prefix):] if obj.name.startswith(name_prefix) else obj.name
        garment = WARDROBE_BY_ID.get(item_id)
        if garment is None or garment.slot not in ("top", "outerwear"):
            continue
        if garment.layer > best_layer:
            best, best_layer = obj, garment.layer
    return best


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
