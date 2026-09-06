"""Build a MakeHuman/MPFB2 character headless: body, face blendshapes, eyes, hair, teeth, skin.

Every asset used here is CC0 (MakeHuman system assets and community CC0 packs; see
``docs/verification/character/REPORT.md`` for the per-pack licence table).  MPFB2 itself is GPL-3.0 add-on
code and is only *used*, never redistributed, by this pipeline.

The body pipeline is:

1. ``HumanService.deserialize_from_dict`` - base mesh with the macro targets applied (gender/age/muscle/
   weight/height/proportions/ethnicity), then the ``game_engine`` rig fitted to the resulting body, then the
   body parts (eyes, eyebrows, eyelashes, teeth, tongue, hair) and MakeHuman clothes fitted to it.
2. :func:`bake_and_load_face_units` - bake the macro shape keys into the mesh so they do not leak into the
   glTF morph targets, then load the 52 ARKit face-unit targets (``faceunits01`` functional pack) as the only
   remaining shape keys.
3. :func:`strip_helper_geometry` - delete the MakeHuman helper geometry (hair/skirt/tights/eye/teeth/tongue
   proxies and the joint cubes) that only exists to fit assets and place bones.
4. :func:`split_eyes` - separate the high-poly eye mesh into eyeball and cornea objects and tag the iris faces
   with their own material slot.
5. :func:`setup_skin` / :func:`setup_eye_materials` - subsurface skin and a refractive cornea for Cycles; the
   parameters are also written into the glb extras so the UE material can be built from them.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

import chenv

log = logging.getLogger("nycsim.character.mh")

FACEUNITS_DIR = chenv.MH_DATA / "faceunits_pack" / "targets" / "faceunits"
FACEUNITS_PACK_JSON = chenv.MH_DATA / "faceunits_pack" / "packs" / "faceunits01.json"

#: The 52 ARKit blendshape names, in Apple's canonical order.
ARKIT_52 = (
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
    "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight",
    "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight",
    "tongueOut",
)

#: MakeHuman body-part assets used for the player and every NPC (all CC0).
EYES_ASSET = "high-poly"
TEETH_ASSET = "teeth_base"
TONGUE_ASSET = "tongue01"

HAIR_ASSETS = ("short01", "short02", "short03", "short04", "bob01", "bob02",
               "long01", "ponytail01", "braid01", "afro01")
EYEBROW_ASSETS = tuple(f"eyebrow{n:03d}" for n in range(1, 13))
EYELASH_ASSETS = ("eyelashes01", "eyelashes02", "eyelashes03", "eyelashes04")

#: MakeHuman skin materials, indexed by (ethnicity, age band, sex).
SKIN_MATERIALS = (
    "young_caucasian_male", "young_caucasian_female", "young_african_male", "young_african_female",
    "young_asian_male", "young_asian_female", "middleage_caucasian_male", "middleage_caucasian_female",
    "middleage_african_male", "middleage_african_female", "middleage_asian_male", "middleage_asian_female",
    "old_caucasian_male", "old_caucasian_female", "old_african_male", "old_african_female",
    "old_asian_male", "old_asian_female",
)

#: Subsurface parameters written to the Principled BSDF and to the glb extras. Radii are in metres and follow
#: the classic 1 mm/0.4 mm/0.25 mm R/G/B skin scattering profile.
SKIN_SSS = {"weight": 0.18, "radius": (0.0100, 0.0040, 0.0025), "scale": 1.0, "ior": 1.4,
            "roughness": 0.52, "specular": 0.42}
CORNEA_IOR = 1.376


@dataclass
class HumanSpec:
    """Everything that defines one character before clothing."""

    name: str
    gender: float = 0.5              # 0 = female, 1 = male
    age: float = 0.5                 # 0 = 1 year, 0.5 = 25 years, 1 = 90 years
    muscle: float = 0.5
    weight: float = 0.5
    height: float = 0.5
    proportions: float = 0.5
    cupsize: float = 0.5
    firmness: float = 0.5
    african: float = 0.34
    asian: float = 0.33
    caucasian: float = 0.33
    skin: str = "young_caucasian_male"
    eyes_material: str = "brown"
    hair: str | None = "short01"
    eyebrows: str | None = "eyebrow001"
    eyelashes: str | None = "eyelashes01"
    teeth: str | None = TEETH_ASSET
    tongue: str | None = TONGUE_ASSET
    clothes: tuple[str, ...] = ()
    rig: str = "game_engine"

    def phenotype(self) -> dict:
        total = max(self.african + self.asian + self.caucasian, 1e-6)
        return {"gender": self.gender, "age": self.age, "muscle": self.muscle, "weight": self.weight,
                "proportions": self.proportions, "height": self.height, "cupsize": self.cupsize,
                "firmness": self.firmness,
                "race": {"african": self.african / total, "asian": self.asian / total,
                         "caucasian": self.caucasian / total}}


@dataclass
class BuiltHuman:
    """The objects that make up one built character."""

    spec: HumanSpec
    basemesh: bpy.types.Object
    armature: bpy.types.Object
    bodyparts: dict[str, bpy.types.Object] = field(default_factory=dict)
    clothes: dict[str, bpy.types.Object] = field(default_factory=dict)
    face_units: list[str] = field(default_factory=list)

    def meshes(self) -> list[bpy.types.Object]:
        out = [self.basemesh, *self.bodyparts.values(), *self.clothes.values()]
        return [o for o in out if o and o.type == "MESH"]


# --------------------------------------------------------------------------------------------- construction
def _mpfb():
    chenv.enable_mpfb()
    from bl_ext.user_default.mpfb.services.assetservice import AssetService  # noqa: PLC0415
    from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: PLC0415
    from bl_ext.user_default.mpfb.services.objectservice import ObjectService  # noqa: PLC0415
    from bl_ext.user_default.mpfb.services.targetservice import TargetService  # noqa: PLC0415
    return HumanService, TargetService, AssetService, ObjectService


def _asset_fragment(asset_service, subdir: str, wanted: str) -> str:
    """Resolve a MakeHuman asset directory name (e.g. ``short01``) to MPFB's ``dir/file.mhclo`` fragment."""
    kind = "proxy" if subdir == "proxymeshes" else "mhclo"
    assets = asset_service.get_asset_list(subdir, kind)
    for name, info in assets.items():
        frag = str(info.get("fragment", ""))
        if frag.split("/", 1)[0] == wanted or name.lower().replace(" ", "") == wanted.lower().replace("_", ""):
            return frag
    raise KeyError(f"MakeHuman asset {wanted!r} not found in {subdir} (have {sorted(assets)})")


def build_human(spec: HumanSpec, *, subdiv: int = 0, load_clothes: bool = True) -> BuiltHuman:
    """Create one MPFB character in the current scene and return its objects."""
    HumanService, _TargetService, AssetService, ObjectService = _mpfb()

    info = HumanService._create_default_human_info_dict()
    info["name"] = spec.name
    info["phenotype"] = spec.phenotype()
    info["rig"] = spec.rig
    info["eyes"] = _asset_fragment(AssetService, "eyes", EYES_ASSET)
    for key, subdir, value in (("hair", "hair", spec.hair), ("eyebrows", "eyebrows", spec.eyebrows),
                               ("eyelashes", "eyelashes", spec.eyelashes), ("teeth", "teeth", spec.teeth),
                               ("tongue", "tongue", spec.tongue)):
        if value:
            info[key] = _asset_fragment(AssetService, subdir, value)
    if load_clothes and spec.clothes:
        info["clothes"] = [_asset_fragment(AssetService, "clothes", c) for c in spec.clothes]
    info["skin_material_type"] = "MAKESKIN"
    skin_path = _skin_path(spec.skin)
    if skin_path:
        info["skin_mhmat"] = str(skin_path)
    eye_mat = chenv.MH_DATA / "eyes" / "materials" / f"{spec.eyes_material}.mhmat"
    if eye_mat.exists():
        info["eyes_material_type"] = "MAKESKIN"
        info["eyes_mhmat"] = str(eye_mat)

    settings = HumanService.get_default_deserialization_settings()
    settings["subdiv_levels"] = subdiv
    settings["load_clothes"] = load_clothes
    settings["mask_helpers"] = True
    settings["detailed_helpers"] = True
    settings["feet_on_ground"] = True

    basemesh = HumanService.deserialize_from_dict(info, settings)
    armature = basemesh.parent
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"MPFB did not create an armature for rig {spec.rig!r}")

    # MPFB parents assets either to the basemesh or to the armature depending on the asset type, so collect
    # them by walking the whole armature family and asking MPFB what each object is.
    family = [o for o in bpy.data.objects
              if o.type == "MESH" and o is not basemesh
              and (o.parent is armature or o.parent is basemesh
                   or any(m.type == "ARMATURE" and m.object is armature for m in o.modifiers))]
    bodyparts: dict[str, bpy.types.Object] = {}
    clothes: dict[str, bpy.types.Object] = {}
    for child in family:
        key = str(ObjectService.get_object_type(child)).lower()
        if key in ("eyes", "eyebrows", "eyelashes", "teeth", "tongue", "hair", "proxymeshes"):
            bodyparts[key] = child
        elif key == "clothes":
            clothes[child.name] = child
        else:
            log.warning("unclassified mesh in character family: %s (mpfb type %r)", child.name, key)
    log.info("built %s: %d body verts, %d bodyparts, %d clothes", spec.name, len(basemesh.data.vertices),
             len(bodyparts), len(clothes))
    return BuiltHuman(spec=spec, basemesh=basemesh, armature=armature, bodyparts=bodyparts, clothes=clothes)


def _skin_path(skin: str) -> Path | None:
    p = chenv.MH_DATA / "skins" / skin / f"{skin}.mhmat"
    if p.exists():
        return p
    for candidate in sorted((chenv.MH_DATA / "skins" / skin).glob("*.mhmat")) if (chenv.MH_DATA / "skins" / skin).is_dir() else []:
        return candidate
    log.warning("skin %r not found under %s", skin, chenv.MH_DATA / "skins")
    return None


# ------------------------------------------------------------------------------------------- face blendshapes
def available_face_units() -> list[str]:
    """ARKit face units present in the downloaded ``faceunits01`` pack, in Apple's canonical order."""
    if not FACEUNITS_DIR.is_dir():
        raise FileNotFoundError(f"face unit targets not found at {FACEUNITS_DIR}")
    have = {p.stem for p in FACEUNITS_DIR.glob("*.target")}
    ordered = [n for n in ARKIT_52 if n in have]
    extra = sorted(have - set(ARKIT_52))
    if extra:
        log.warning("face unit pack contains %d non-ARKit targets: %s", len(extra), extra)
    return ordered


def bake_and_load_face_units(built: BuiltHuman) -> list[str]:
    """Bake the macro/detail targets into the mesh, then add the ARKit face units as shape keys.

    MPFB keeps every macro target as a live shape key so the character stays editable.  For an exported asset
    that is wrong: the glTF morph targets must be the 52 expression channels and nothing else.
    """
    _HumanService, TargetService, _AssetService, _ObjectService = _mpfb()
    basemesh = built.basemesh
    if basemesh.data.shape_keys:
        TargetService.bake_targets(basemesh)
    names = available_face_units()
    for name in names:
        TargetService.load_target(basemesh, str(FACEUNITS_DIR / f"{name}.target"), weight=0.0, name=name)
    keys = [k.name for k in basemesh.data.shape_keys.key_blocks] if basemesh.data.shape_keys else []
    unexpected = [k for k in keys[1:] if k not in names]
    if unexpected:
        raise RuntimeError(f"unexpected shape keys after face-unit load: {unexpected}")
    built.face_units = names
    log.info("%s: %d ARKit face units loaded as shape keys", basemesh.name, len(names))
    return names


# --------------------------------------------------------------------------------------- helper geometry
def strip_helper_geometry(built: BuiltHuman) -> int:
    """Delete every vertex that is not in the ``body`` group; return the number removed.

    Uses an edit-mode delete so shape keys, vertex groups and UVs are all remapped by Blender.
    """
    basemesh = built.basemesh
    group = basemesh.vertex_groups.get("body")
    if group is None:
        raise RuntimeError("basemesh has no 'body' vertex group - cannot identify helper geometry")
    body_index = group.index
    doomed = []
    for vert in basemesh.data.vertices:
        if not any(g.group == body_index and g.weight > 0.0 for g in vert.groups):
            doomed.append(vert.index)
    if not doomed:
        return 0
    for vert in basemesh.data.vertices:
        vert.select = False
    for idx in doomed:
        basemesh.data.vertices[idx].select = True
    view_layer = bpy.context.view_layer
    for ob in bpy.data.objects:
        ob.select_set(False)
    view_layer.objects.active = basemesh
    basemesh.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for modifier in list(basemesh.modifiers):
        if modifier.type == "MASK":
            basemesh.modifiers.remove(modifier)
    log.info("%s: stripped %d helper vertices, %d remain", basemesh.name, len(doomed),
             len(basemesh.data.vertices))
    return len(doomed)


# --------------------------------------------------------------------------------------------- eyes
def split_eyes(built: BuiltHuman) -> dict[str, bpy.types.Object]:
    """Split the MakeHuman high-poly eye object into eyeball and cornea objects and tag the iris.

    The high-poly asset is four loose shells: left/right eyeball (sclera + iris, from the diffuse texture) and
    left/right cornea (the transparent bulge in front of the iris).  They are separated so the cornea can carry
    a refractive material and the eyeball a diffuse one, and so the runtime can move the two independently.
    The iris faces of each eyeball get their own material slot (``EYE_IRIS``) so pupil dilation can be driven.
    """
    eyes = built.bodyparts.get("eyes")
    if eyes is None:
        raise RuntimeError("no eyes object - build_human must be called with the high-poly eyes asset")

    mesh = eyes.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    shells = _loose_parts(bm)
    if len(shells) != 4:
        bm.free()
        raise RuntimeError(f"expected 4 eye shells (2 eyeballs + 2 corneas), found {len(shells)}")
    bm.free()

    # A cornea shell has fewer vertices than its eyeball and sits further forward (-Y in Blender).
    info = []
    for verts in shells:
        coords = [eyes.matrix_world @ mesh.vertices[i].co for i in verts]
        centre = sum(coords, Vector()) / len(coords)
        info.append({"verts": set(verts), "n": len(verts), "centre": centre,
                     "front": min(c.y for c in coords)})
    left = [s for s in info if s["centre"].x > 0]
    right = [s for s in info if s["centre"].x <= 0]
    parts: dict[str, set[int]] = {}
    for side, group in (("l", left), ("r", right)):
        if len(group) != 2:
            raise RuntimeError(f"eye side {side} has {len(group)} shells, expected 2")
        group.sort(key=lambda s: s["n"])
        parts[f"cornea_{side}"] = group[0]["verts"]
        parts[f"eyeball_{side}"] = group[1]["verts"]

    created = _separate_by_vertex_sets(eyes, parts, name_prefix=f"{built.spec.name}.")
    for key, obj in created.items():
        built.bodyparts[key] = obj
        if key.startswith("eyeball"):
            _tag_iris_faces(obj)
    built.bodyparts.pop("eyes", None)
    log.info("eyes split into %s", sorted(created))
    return created


def _loose_parts(bm: bmesh.types.BMesh) -> list[list[int]]:
    parent = list(range(len(bm.verts)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for edge in bm.edges:
        ra, rb = find(edge.verts[0].index), find(edge.verts[1].index)
        if ra != rb:
            parent[ra] = rb
    groups: dict[int, list[int]] = {}
    for i in range(len(bm.verts)):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=len, reverse=True)


def _separate_by_vertex_sets(obj: bpy.types.Object, parts: dict[str, set[int]], *,
                             name_prefix: str = "") -> dict[str, bpy.types.Object]:
    """Split ``obj`` into new mesh objects, one per named vertex set. ``obj`` itself is removed."""
    mesh = obj.data
    coords = [v.co.copy() for v in mesh.vertices]
    uv_layer = mesh.uv_layers.active
    group_names = [g.name for g in obj.vertex_groups]
    weights: dict[int, list[tuple[int, float]]] = {}
    for vert in mesh.vertices:
        weights[vert.index] = [(g.group, g.weight) for g in vert.groups]

    faces_by_part: dict[str, list[tuple[int, ...]]] = {k: [] for k in parts}
    loops_by_part: dict[str, list[tuple[tuple[float, float], ...]]] = {k: [] for k in parts}
    for poly in mesh.polygons:
        verts = tuple(mesh.loops[i].vertex_index for i in poly.loop_indices)
        for key, members in parts.items():
            if all(v in members for v in verts):
                faces_by_part[key].append(verts)
                if uv_layer:
                    loops_by_part[key].append(tuple(tuple(uv_layer.data[i].uv) for i in poly.loop_indices))
                break

    out: dict[str, bpy.types.Object] = {}
    for key, members in parts.items():
        index_map = {old: new for new, old in enumerate(sorted(members))}
        new_mesh = bpy.data.meshes.new(f"{name_prefix}{key}")
        verts = [coords[i] for i in sorted(members)]
        faces = [tuple(index_map[v] for v in f) for f in faces_by_part[key]]
        new_mesh.from_pydata(verts, [], faces)
        new_mesh.update()
        if uv_layer and loops_by_part[key]:
            layer = new_mesh.uv_layers.new(name=uv_layer.name)
            i = 0
            for face_uvs in loops_by_part[key]:
                for uv in face_uvs:
                    layer.data[i].uv = uv
                    i += 1
        for mat in mesh.materials:
            new_mesh.materials.append(mat)
        new_obj = bpy.data.objects.new(f"{name_prefix}{key}", new_mesh)
        obj.users_collection[0].objects.link(new_obj)
        new_obj.matrix_world = obj.matrix_world.copy()
        new_obj.parent = obj.parent
        groups = {name: new_obj.vertex_groups.new(name=name) for name in group_names}
        for old, new in index_map.items():
            for gidx, weight in weights[old]:
                groups[group_names[gidx]].add([new], weight, "REPLACE")
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                new_mod = new_obj.modifiers.new(modifier.name, "ARMATURE")
                new_mod.object = modifier.object
        out[key] = new_obj
    bpy.data.objects.remove(obj, do_unlink=True)
    return out


def _tag_iris_faces(eyeball: bpy.types.Object, iris_uv_radius: float = 0.22) -> int:
    """Give the iris faces of an eyeball their own material slot. Returns the number of faces tagged.

    MakeHuman's eye UV layout puts the iris in a disc centred on the texture; faces whose UV centroid lies
    inside ``iris_uv_radius`` of that centre are the iris.
    """
    mesh = eyeball.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return 0
    base_mat = mesh.materials[0] if mesh.materials else None
    # the iris starts as an exact copy of the eye material, so it renders identically until the runtime
    # drives it (pupil dilation); having it in its own slot is what makes that possible.
    if base_mat is not None:
        iris_mat = base_mat.copy()
        iris_mat.name = f"{eyeball.name}.EYE_IRIS"
    else:
        iris_mat = bpy.data.materials.new(f"{eyeball.name}.EYE_IRIS")
        iris_mat.use_nodes = True
    mesh.materials.append(iris_mat)
    iris_slot = len(mesh.materials) - 1
    centre = Vector((0.5, 0.5))
    tagged = 0
    for poly in mesh.polygons:
        uvs = [Vector(uv_layer.data[i].uv) for i in poly.loop_indices]
        mid = sum(uvs, Vector((0.0, 0.0))) / len(uvs)
        if (mid - centre).length <= iris_uv_radius:
            poly.material_index = iris_slot
            tagged += 1
    log.info("%s: tagged %d iris faces", eyeball.name, tagged)
    return tagged


# --------------------------------------------------------------------------------------------- materials
def _principled(material: bpy.types.Material) -> bpy.types.Node | None:
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def setup_skin(built: BuiltHuman) -> dict:
    """Turn the MakeSkin material on the body into a subsurface skin shader; return the parameters used."""
    applied = []
    for material_slot in built.basemesh.material_slots:
        node = _principled(material_slot.material)
        if node is None:
            continue
        node.inputs["Subsurface Weight"].default_value = SKIN_SSS["weight"]
        node.inputs["Subsurface Radius"].default_value = SKIN_SSS["radius"]
        node.inputs["Subsurface Scale"].default_value = SKIN_SSS["scale"]
        if "Subsurface IOR" in node.inputs:
            node.inputs["Subsurface IOR"].default_value = SKIN_SSS["ior"]
        node.inputs["Roughness"].default_value = SKIN_SSS["roughness"]
        node.inputs["Specular IOR Level"].default_value = SKIN_SSS["specular"]
        node.inputs["Metallic"].default_value = 0.0
        applied.append(material_slot.material.name)
    if not applied:
        raise RuntimeError(f"{built.basemesh.name} has no Principled skin material to configure")
    log.info("subsurface skin on %s", applied)
    return {"materials": applied, **{k: (list(v) if isinstance(v, tuple) else v) for k, v in SKIN_SSS.items()}}


def setup_eye_materials(built: BuiltHuman) -> dict:
    """Refractive cornea, glossy sclera. Returns the parameters for the glb extras."""
    out = {"cornea_ior": CORNEA_IOR, "objects": []}
    for key, obj in built.bodyparts.items():
        if key.startswith("cornea"):
            mat = bpy.data.materials.new(f"{obj.name}.CORNEA")
            mat.use_nodes = True
            node = _principled(mat)
            node.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
            node.inputs["Roughness"].default_value = 0.02
            node.inputs["IOR"].default_value = CORNEA_IOR
            node.inputs["Transmission Weight"].default_value = 1.0
            node.inputs["Alpha"].default_value = 0.08
            mat.blend_method = "BLEND"
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            out["objects"].append(obj.name)
        elif key.startswith("eyeball"):
            for slot in obj.material_slots:
                node = _principled(slot.material)
                if node is not None:
                    node.inputs["Roughness"].default_value = 0.18
                    node.inputs["Specular IOR Level"].default_value = 0.6
            out["objects"].append(obj.name)
    return out


def setup_alpha_materials(built: BuiltHuman) -> list[str]:
    """Wire the alpha channel of the card-hair, brow and lash textures into their materials.

    MakeHuman's hair, eyebrow and eyelash meshes are alpha-cut polygon cards.  MPFB's MakeSkin import leaves
    the image's alpha unconnected, so the cards render (and export) as opaque quads - which is what turned a
    braid into a white spike in the first NPC line-up.  Linking alpha and setting a clip threshold makes the
    glTF exporter emit ``alphaMode: MASK`` and the cards read as hair.
    """
    touched: list[str] = []
    for key in ("hair", "eyebrows", "eyelashes"):
        obj = built.bodyparts.get(key)
        if obj is None:
            continue
        for slot in obj.material_slots:
            material = slot.material
            if material is None or not material.use_nodes:
                continue
            tree = material.node_tree
            bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is None:
                continue
            texture = _upstream_image(bsdf.inputs["Base Color"])
            if texture is None or "Alpha" not in texture.outputs:
                continue
            alpha = bsdf.inputs["Alpha"]
            for link in list(alpha.links):
                tree.links.remove(link)
            tree.links.new(texture.outputs["Alpha"], alpha)
            if hasattr(material, "blend_method"):
                material.blend_method = "CLIP"
            if hasattr(material, "alpha_threshold"):
                material.alpha_threshold = 0.5
            if hasattr(material, "surface_render_method"):
                material.surface_render_method = "DITHERED"
            material.show_transparent_back = False
            touched.append(material.name)
    log.info("alpha-cut materials wired: %s", touched)
    return touched


def _upstream_image(socket) -> bpy.types.Node | None:
    seen: set[str] = set()
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


def face_unit_licences() -> dict:
    """Per-target licence/author record for the ARKit face units, read from the pack's own JSON."""
    if not FACEUNITS_PACK_JSON.exists():
        return {}
    with open(FACEUNITS_PACK_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    authors = {v.get("author", "") for v in data.values()}
    licences = {v.get("license", "") for v in data.values()}
    return {"targets": len(data), "authors": sorted(authors), "licenses": sorted(licences)}


def measure(built: BuiltHuman) -> dict:
    """Real body measurements of the built character, in metres (for the report and for the NPC line-up)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in built.meshes():
        # stature is the *body's* height: a hat, a hijab or a bag would otherwise be reported as growth
        include_top = obj is built.basemesh
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            world = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, world))
            if include_top:
                hi = Vector(map(max, hi, world))
    bones = built.armature.data.bones
    out = {"height_m": hi.z - lo.z, "shoulder_width_m": 0.0, "leg_length_m": 0.0}
    if "clavicle_l" in bones and "clavicle_r" in bones:
        out["shoulder_width_m"] = (bones["clavicle_l"].tail_local - bones["clavicle_r"].tail_local).length
    if "thigh_l" in bones and "foot_l" in bones:
        out["leg_length_m"] = (bones["thigh_l"].head_local - bones["foot_l"].head_local).length
    return out
