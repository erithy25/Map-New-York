"""NYCSim asset import: every entry of ``data/processed/unreal_manifest.json`` (DATA_CONTRACTS §14) plus the
material parameter collection and the base materials the runtime binds to by path.

Run headless through the commandlet::

    UnrealEditor-Cmd NYCSim.uproject -run=NYCImport -stages=validate,stage,assets

or from the editor's Python console::

    import import_assets; import_assets.main(["--manifest", "/repo/data/processed/unreal_manifest.json"])

What it creates, if it is not already there (nothing is overwritten unless --force is given):

    /Game/NYCSim/Materials/MPC_Weather        the parameter collection the weather and sky subsystems write
    /Game/NYCSim/Materials/M_NYC_Master       opaque PBR master for shells, kit, props and roads
    /Game/NYCSim/Materials/M_NYC_Foliage      two-sided masked master for trees
    /Game/NYCSim/Materials/M_NYC_Terrain      landscape material (weather-driven wetness and snow)
    /Game/NYCSim/Materials/M_NYC_Water        water surface (see ANYCWaterActor for the parameter contract)
    /Game/NYCSim/Materials/M_NYC_StarMap      unlit two-sided star sphere

and imports every glb / png / otf listed in the manifest to the content path the manifest names, applying the
manifest's import-settings block (nanite, collision, LOD chain, sRGB, compression, address mode).

The script never invents content: an entry whose source file is missing is reported and skipped, and the exit
summary lists every skip with its reason.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import unreal

LOG = unreal.log
WARN = unreal.log_warning
ERROR = unreal.log_error

CONTENT_ROOT = "/Game/NYCSim"
MATERIALS_ROOT = f"{CONTENT_ROOT}/Materials"

# Scalar parameters of MPC_Weather. Written by UNYCWeatherSubsystem (weather) and UNYCSkyTimeSubsystem (sky).
MPC_SCALARS = [
    ("Wetness", 0.0), ("Puddles", 0.0), ("SnowCover", 0.0), ("SnowDepthM", 0.0), ("IceRisk", 0.0),
    ("FogDensity", 0.0), ("WindSpeedMps", 0.0), ("WindGustMps", 0.0), ("WindHeadingDeg", 0.0),
    ("FlagSway", 0.0), ("Overcast", 0.0), ("RainRateMmph", 0.0), ("SnowRateCmph", 0.0),
    ("TemperatureC", 15.0), ("Thunder", 0.0), ("Stale", 0.0),
    ("StreetLightsOn", 0.0), ("SunElevationDeg", 0.0), ("SunAzimuthDeg", 0.0),
    ("MoonIllumination", 0.0), ("LocalTimeHours", 12.0), ("ESBColorCount", 1.0),
]
MPC_VECTORS = [
    ("WindVector", (0.0, 0.0, 0.0, 0.0)),
    ("SunDirection", (0.0, 0.0, 1.0, 0.0)),
    ("ESBCrownColor", (1.0, 1.0, 1.0, 1.0)),
    ("ESBCrownColor2", (1.0, 1.0, 1.0, 1.0)),
    ("ESBCrownColor3", (1.0, 1.0, 1.0, 1.0)),
]

ENGINE_NOISE_TEXTURE = "/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq.Good64x64TilingNoiseHighFreq"
ENGINE_FLAT_NORMAL = "/Engine/EngineMaterials/DefaultNormal.DefaultNormal"
ENGINE_GREY_TEXTURE = "/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture"


# --------------------------------------------------------------------------------------------- small helpers

def asset_exists(path: str) -> bool:
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def load_asset(path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(path)
    except Exception as exc:  # noqa: BLE001 - the editor raises plain Exceptions for missing assets
        WARN(f"cannot load {path}: {exc}")
        return None


def split_content_path(dst: str):
    """'/Game/NYCSim/Kit/Windows/SM_win_a' -> ('/Game/NYCSim/Kit/Windows', 'SM_win_a')."""
    dst = dst.rstrip("/")
    head, _, name = dst.rpartition("/")
    return head, name


def save_asset(path: str) -> bool:
    try:
        return bool(unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False))
    except Exception as exc:  # noqa: BLE001
        WARN(f"save {path} failed: {exc}")
        return False


# ------------------------------------------------------------------------------------------ material helpers

class MaterialBuilder:
    """Thin wrapper over unreal.MaterialEditingLibrary with node placement and failure isolation."""

    def __init__(self, material):
        self.material = material
        self.lib = unreal.MaterialEditingLibrary
        self.failures: list[str] = []

    def expr(self, cls, x: int, y: int, **properties):
        try:
            node = self.lib.create_material_expression(self.material, cls, x, y)
        except Exception as exc:  # noqa: BLE001
            self.failures.append(f"create {cls}: {exc}")
            return None
        for key, value in properties.items():
            try:
                node.set_editor_property(key, value)
            except Exception as exc:  # noqa: BLE001
                self.failures.append(f"{cls}.{key}: {exc}")
        return node

    def connect(self, from_node, from_pin: str, to_node, to_pin: str) -> bool:
        if from_node is None or to_node is None:
            return False
        try:
            return bool(self.lib.connect_material_expressions(from_node, from_pin, to_node, to_pin))
        except Exception as exc:  # noqa: BLE001
            self.failures.append(f"connect {from_pin} -> {to_pin}: {exc}")
            return False

    def to_property(self, node, pin: str, prop) -> bool:
        if node is None:
            return False
        try:
            return bool(self.lib.connect_material_property(node, pin, prop))
        except Exception as exc:  # noqa: BLE001
            self.failures.append(f"connect to {prop}: {exc}")
            return False

    def finish(self, name: str) -> None:
        try:
            self.lib.layout_material_expressions(self.material)
            self.lib.recompile_material(self.material)
        except Exception as exc:  # noqa: BLE001
            self.failures.append(f"recompile: {exc}")
        if self.failures:
            WARN(f"{name}: {len(self.failures)} graph operations failed:")
            for failure in self.failures:
                WARN(f"    {failure}")


def create_material(name: str, folder: str = MATERIALS_ROOT):
    path = f"{folder}/{name}"
    if asset_exists(path):
        return load_asset(path), False
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        ERROR(f"could not create material {path}")
    return material, True


# ------------------------------------------------------------------------------------------------- physical materials

#: nycsim_gameplay::SurfaceClass index -> (asset name, EPhysicalSurface enum member). The index is the
#: EPhysicalSurface index too: DefaultEngine.ini declares SurfaceType1=Asphalt ... SurfaceType13=Ice in
#: exactly this order and UNYCVehicleMovementComponent::ToSurfaceClass casts one straight to the other.
#: Without these assets on the mesh slots every contact resolves to SurfaceClass::Default and the whole
#: friction table collapses to dry asphalt -- cobblestone, steel plate and painted crosswalk included.
PHYSICAL_SURFACES = {
    1: ("PM_NYC_Asphalt", "SURFACE_TYPE1"),
    2: ("PM_NYC_Concrete", "SURFACE_TYPE2"),
    3: ("PM_NYC_Cobble", "SURFACE_TYPE3"),
    4: ("PM_NYC_SteelPlate", "SURFACE_TYPE4"),
    5: ("PM_NYC_PaintedMarking", "SURFACE_TYPE5"),
    6: ("PM_NYC_Gravel", "SURFACE_TYPE6"),
    7: ("PM_NYC_Boardwalk", "SURFACE_TYPE7"),
    8: ("PM_NYC_Grass", "SURFACE_TYPE8"),
    9: ("PM_NYC_Sidewalk", "SURFACE_TYPE9"),
    10: ("PM_NYC_Water", "SURFACE_TYPE10"),
    11: ("PM_NYC_Metal", "SURFACE_TYPE11"),
    12: ("PM_NYC_Snow", "SURFACE_TYPE12"),
    13: ("PM_NYC_Ice", "SURFACE_TYPE13"),
}
PHYSICS_ROOT = f"{CONTENT_ROOT}/Physics"


def ensure_physical_materials(force: bool = False) -> dict:
    """Create one ``UPhysicalMaterial`` per declared surface, tagged with its ``EPhysicalSurface``."""
    made = {}
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for index, (name, enum_member) in sorted(PHYSICAL_SURFACES.items()):
        path = f"{PHYSICS_ROOT}/{name}"
        asset = load_asset(path) if asset_exists(path) else None
        if asset is not None and not force:
            made[name] = False
            continue
        if asset is None:
            asset = tools.create_asset(name, PHYSICS_ROOT, unreal.PhysicalMaterial,
                                       unreal.PhysicalMaterialFactoryNew())
        if asset is None:
            ERROR(f"could not create physical material {path}")
            continue
        try:
            asset.set_editor_property("surface_type", getattr(unreal.PhysicalSurface, enum_member))
        except Exception as exc:  # noqa: BLE001
            WARN(f"{path}: surface_type {enum_member} not settable: {exc}")
        save_asset(path)
        made[name] = True
    return made


def assign_physical_materials(asset_path: str, by_material: dict) -> int:
    """Hang the right ``UPhysicalMaterial`` on every slot of an imported pavement mesh.

    ``by_material`` maps the glTF material name (``pave_roadbed_asphalt``) to a ``SurfaceClass``
    index. The imported slot keeps that name, so the mapping is a lookup rather than a guess. A slot
    whose name is not in the map keeps whatever it had and is reported, because a silently
    unassigned slot is a stretch of road that behaves like dry asphalt in the rain.
    """
    mesh = load_asset(asset_path)
    if mesh is None or not isinstance(mesh, unreal.StaticMesh):
        return 0
    assigned = 0
    try:
        slots = list(mesh.get_editor_property("static_materials") or [])
    except Exception as exc:  # noqa: BLE001
        WARN(f"{asset_path}: material slots unreadable: {exc}")
        return 0
    for slot in slots:
        try:
            slot_name = str(slot.get_editor_property("material_slot_name"))
            material = slot.get_editor_property("material_interface")
        except Exception:  # noqa: BLE001
            continue
        index = by_material.get(slot_name)
        if index is None:
            # The importer may prefix or suffix the slot name; fall back to a containment match.
            for key, value in by_material.items():
                if key and key in slot_name:
                    index = value
                    break
        if index is None:
            WARN(f"{asset_path}: slot {slot_name!r} has no surface class; it will behave as Default")
            continue
        entry = PHYSICAL_SURFACES.get(int(index))
        if entry is None or material is None:
            continue
        pm = load_asset(f"{PHYSICS_ROOT}/{entry[0]}")
        if pm is None:
            continue
        try:
            material.set_editor_property("phys_material", pm)
            save_asset(material.get_path_name().split(".")[0])
            assigned += 1
        except Exception as exc:  # noqa: BLE001
            WARN(f"{asset_path}: slot {slot_name!r} physical material failed: {exc}")
    if assigned:
        save_asset(asset_path)
    return assigned


def make_parameter_collection(force: bool = False):
    path = f"{MATERIALS_ROOT}/MPC_Weather"
    if asset_exists(path) and not force:
        return load_asset(path), False
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    collection = tools.create_asset(
        "MPC_Weather", MATERIALS_ROOT, unreal.MaterialParameterCollection,
        unreal.MaterialParameterCollectionFactoryNew())
    if collection is None:
        ERROR("could not create MPC_Weather")
        return None, False
    scalars = []
    for pname, default in MPC_SCALARS:
        entry = unreal.CollectionScalarParameter()
        entry.set_editor_property("parameter_name", pname)
        entry.set_editor_property("default_value", float(default))
        scalars.append(entry)
    vectors = []
    for pname, default in MPC_VECTORS:
        entry = unreal.CollectionVectorParameter()
        entry.set_editor_property("parameter_name", pname)
        entry.set_editor_property("default_value", unreal.LinearColor(*default))
        vectors.append(entry)
    collection.set_editor_property("scalar_parameters", scalars)
    collection.set_editor_property("vector_parameters", vectors)
    save_asset(path)
    LOG(f"created {path} with {len(scalars)} scalar and {len(vectors)} vector parameters")
    return collection, True


def collection_scalar(builder: MaterialBuilder, collection, parameter: str, x: int, y: int):
    node = builder.expr(unreal.MaterialExpressionCollectionParameter, x, y)
    if node is None:
        return None
    try:
        node.set_editor_property("collection", collection)
        node.set_editor_property("parameter_name", parameter)
    except Exception as exc:  # noqa: BLE001
        builder.failures.append(f"collection parameter {parameter}: {exc}")
    return node


def build_master_material(collection, force: bool = False) -> bool:
    """Opaque PBR master: base colour / roughness / metallic / normal parameters, darkened and smoothed by the
    live wetness and covered by snow from MPC_Weather."""
    material, created = create_material("M_NYC_Master")
    if material is None or (not created and not force):
        return created
    b = MaterialBuilder(material)
    base = b.expr(unreal.MaterialExpressionVectorParameter, -900, -300,
                  parameter_name="BaseColor", default_value=unreal.LinearColor(0.55, 0.53, 0.5, 1.0))
    rough = b.expr(unreal.MaterialExpressionScalarParameter, -900, 100, parameter_name="Roughness", default_value=0.75)
    metal = b.expr(unreal.MaterialExpressionScalarParameter, -900, 200, parameter_name="Metallic", default_value=0.0)
    snow_colour = b.expr(unreal.MaterialExpressionConstant3Vector, -900, -100,
                         constant=unreal.LinearColor(0.86, 0.88, 0.92, 1.0))
    wetness = collection_scalar(b, collection, "Wetness", -900, 300)
    snow_cover = collection_scalar(b, collection, "SnowCover", -900, 400)

    # Wet surfaces are darker and smoother (Fresnel does the rest); snow covers everything on top.
    wet_dark = b.expr(unreal.MaterialExpressionLinearInterpolate, -600, -300, const_a=1.0, const_b=0.55)
    b.connect(wetness, "", wet_dark, "Alpha")
    darkened = b.expr(unreal.MaterialExpressionMultiply, -400, -300)
    b.connect(base, "", darkened, "A")
    b.connect(wet_dark, "", darkened, "B")
    colour = b.expr(unreal.MaterialExpressionLinearInterpolate, -200, -300)
    b.connect(darkened, "", colour, "A")
    b.connect(snow_colour, "", colour, "B")
    b.connect(snow_cover, "", colour, "Alpha")

    wet_rough = b.expr(unreal.MaterialExpressionLinearInterpolate, -400, 100, const_b=0.12)
    b.connect(rough, "", wet_rough, "A")
    b.connect(wetness, "", wet_rough, "Alpha")
    snow_rough = b.expr(unreal.MaterialExpressionLinearInterpolate, -200, 100, const_b=0.55)
    b.connect(wet_rough, "", snow_rough, "A")
    b.connect(snow_cover, "", snow_rough, "Alpha")

    b.to_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    b.to_property(snow_rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    b.to_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    b.finish("M_NYC_Master")
    save_asset(f"{MATERIALS_ROOT}/M_NYC_Master")
    return True


def build_foliage_material(collection, force: bool = False) -> bool:
    material, created = create_material("M_NYC_Foliage")
    if material is None or (not created and not force):
        return created
    try:
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property("two_sided", True)
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    except Exception as exc:  # noqa: BLE001
        WARN(f"M_NYC_Foliage properties: {exc}")
    b = MaterialBuilder(material)
    tex = b.expr(unreal.MaterialExpressionTextureSampleParameter2D, -800, -200, parameter_name="Leaf")
    if tex is not None:
        default = load_asset(ENGINE_GREY_TEXTURE)
        if default is not None:
            try:
                tex.set_editor_property("texture", default)
            except Exception as exc:  # noqa: BLE001
                b.failures.append(f"leaf texture: {exc}")
    tint = b.expr(unreal.MaterialExpressionVectorParameter, -800, 60, parameter_name="Tint",
                  default_value=unreal.LinearColor(0.22, 0.35, 0.14, 1.0))
    colour = b.expr(unreal.MaterialExpressionMultiply, -500, -100)
    b.connect(tex, "RGB", colour, "A")
    b.connect(tint, "", colour, "B")
    b.to_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    b.to_property(tex, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    rough = b.expr(unreal.MaterialExpressionScalarParameter, -500, 200, parameter_name="Roughness", default_value=0.65)
    b.to_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    b.finish("M_NYC_Foliage")
    save_asset(f"{MATERIALS_ROOT}/M_NYC_Foliage")
    return True


def build_terrain_material(collection, force: bool = False) -> bool:
    """Landscape material: a plain graded ground that reacts to wetness and snow. Landscape layer blending is not
    used (the pipeline paints no weight maps; pavement, parks and beaches are separate meshes)."""
    material, created = create_material("M_NYC_Terrain")
    if material is None or (not created and not force):
        return created
    try:
        material.set_editor_property("used_with_landscape", True)
    except Exception as exc:  # noqa: BLE001
        WARN(f"M_NYC_Terrain used_with_landscape: {exc}")
    b = MaterialBuilder(material)
    ground = b.expr(unreal.MaterialExpressionVectorParameter, -900, -200, parameter_name="GroundColor",
                    default_value=unreal.LinearColor(0.13, 0.12, 0.10, 1.0))
    snow_colour = b.expr(unreal.MaterialExpressionConstant3Vector, -900, -60,
                         constant=unreal.LinearColor(0.86, 0.88, 0.92, 1.0))
    wetness = collection_scalar(b, collection, "Wetness", -900, 120)
    snow_cover = collection_scalar(b, collection, "SnowCover", -900, 220)

    wet_dark = b.expr(unreal.MaterialExpressionLinearInterpolate, -650, 0, const_a=1.0, const_b=0.6)
    b.connect(wetness, "", wet_dark, "Alpha")
    darkened = b.expr(unreal.MaterialExpressionMultiply, -450, -150)
    b.connect(ground, "", darkened, "A")
    b.connect(wet_dark, "", darkened, "B")
    colour = b.expr(unreal.MaterialExpressionLinearInterpolate, -250, -150)
    b.connect(darkened, "", colour, "A")
    b.connect(snow_colour, "", colour, "B")
    b.connect(snow_cover, "", colour, "Alpha")
    rough = b.expr(unreal.MaterialExpressionLinearInterpolate, -250, 120, const_a=0.9, const_b=0.2)
    b.connect(wetness, "", rough, "Alpha")
    b.to_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    b.to_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    b.finish("M_NYC_Terrain")
    save_asset(f"{MATERIALS_ROOT}/M_NYC_Terrain")
    return True


def build_water_material(collection, force: bool = False) -> bool:
    """Water surface. Parameter contract (ANYCWaterActor):
       Texture2D WaterMask, Scalar HasMask, Vector TileOriginUE, Vector FlowVector, Scalar WaterLevelCm,
       Scalar Tidal, Scalar KindIndex — plus Texture2D WaterNormal, which defaults to the engine's flat normal so a
       tiling water normal map can be dropped in without touching the graph."""
    material, created = create_material("M_NYC_Water")
    if material is None or (not created and not force):
        return created
    try:
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property("opacity_mask_clip_value", 0.5)
        material.set_editor_property("two_sided", False)
    except Exception as exc:  # noqa: BLE001
        WARN(f"M_NYC_Water properties: {exc}")
    b = MaterialBuilder(material)

    # UV = (worldXY - tile north-west corner) / tile size, so the mask lines up with the pipeline's raster exactly.
    world = b.expr(unreal.MaterialExpressionWorldPosition, -1500, 0)
    world_xy = b.expr(unreal.MaterialExpressionComponentMask, -1300, 0, r=True, g=True, b=False, a=False)
    b.connect(world, "", world_xy, "")
    origin = b.expr(unreal.MaterialExpressionVectorParameter, -1500, 160, parameter_name="TileOriginUE",
                    default_value=unreal.LinearColor(0.0, 0.0, 100000.0, 0.0))
    origin_xy = b.expr(unreal.MaterialExpressionComponentMask, -1300, 160, r=True, g=True, b=False, a=False)
    b.connect(origin, "", origin_xy, "")
    tile_size = b.expr(unreal.MaterialExpressionComponentMask, -1300, 240, r=False, g=False, b=True, a=False)
    b.connect(origin, "", tile_size, "")
    local = b.expr(unreal.MaterialExpressionSubtract, -1100, 60)
    b.connect(world_xy, "", local, "A")
    b.connect(origin_xy, "", local, "B")
    uv = b.expr(unreal.MaterialExpressionDivide, -900, 60)
    b.connect(local, "", uv, "A")
    b.connect(tile_size, "", uv, "B")
    # UE Y grows south and the mask's row 0 is the north edge, so V already runs the right way after the flip below.
    flip = b.expr(unreal.MaterialExpressionMultiply, -740, 60, const_b=1.0)
    b.connect(uv, "", flip, "A")

    mask = b.expr(unreal.MaterialExpressionTextureSampleParameter2D, -520, 60, parameter_name="WaterMask")
    if mask is not None:
        default = load_asset(ENGINE_GREY_TEXTURE)
        if default is not None:
            try:
                mask.set_editor_property("texture", default)
                mask.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GREYSCALE)
            except Exception as exc:  # noqa: BLE001
                b.failures.append(f"water mask default: {exc}")
    b.connect(flip, "", mask, "UVs")
    has_mask = b.expr(unreal.MaterialExpressionScalarParameter, -520, 260, parameter_name="HasMask", default_value=0.0)
    coverage = b.expr(unreal.MaterialExpressionLinearInterpolate, -260, 160, const_a=1.0)
    b.connect(mask, "R", coverage, "B")
    b.connect(has_mask, "", coverage, "Alpha")
    b.to_property(coverage, "", unreal.MaterialProperty.MP_OPACITY_MASK)

    # Flow: the tide moves the ripple field; FlowVector is (dirX, dirY, speed m/s, 0) in UE space.
    flow = b.expr(unreal.MaterialExpressionVectorParameter, -1500, 400, parameter_name="FlowVector",
                  default_value=unreal.LinearColor(1.0, 0.0, 0.0, 0.0))
    flow_dir = b.expr(unreal.MaterialExpressionComponentMask, -1300, 400, r=True, g=True, b=False, a=False)
    b.connect(flow, "", flow_dir, "")
    flow_speed = b.expr(unreal.MaterialExpressionComponentMask, -1300, 480, r=False, g=False, b=True, a=False)
    b.connect(flow, "", flow_speed, "")
    time_node = b.expr(unreal.MaterialExpressionTime, -1300, 560)
    drift = b.expr(unreal.MaterialExpressionMultiply, -1100, 440)
    b.connect(flow_dir, "", drift, "A")
    b.connect(flow_speed, "", drift, "B")
    drift_t = b.expr(unreal.MaterialExpressionMultiply, -940, 440)
    b.connect(drift, "", drift_t, "A")
    b.connect(time_node, "", drift_t, "B")

    ripple_scale = b.expr(unreal.MaterialExpressionScalarParameter, -1100, 620, parameter_name="RippleTiling",
                          default_value=0.00035)  # 1 / ~28 m
    ripple_uv_base = b.expr(unreal.MaterialExpressionMultiply, -900, 620)
    b.connect(world_xy, "", ripple_uv_base, "A")
    b.connect(ripple_scale, "", ripple_uv_base, "B")
    ripple_uv = b.expr(unreal.MaterialExpressionAdd, -740, 620)
    b.connect(ripple_uv_base, "", ripple_uv, "A")
    b.connect(drift_t, "", ripple_uv, "B")

    normal = b.expr(unreal.MaterialExpressionTextureSampleParameter2D, -520, 620, parameter_name="WaterNormal")
    if normal is not None:
        flat = load_asset(ENGINE_FLAT_NORMAL)
        if flat is not None:
            try:
                normal.set_editor_property("texture", flat)
                normal.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            except Exception as exc:  # noqa: BLE001
                b.failures.append(f"water normal default: {exc}")
    b.connect(ripple_uv, "", normal, "UVs")
    b.to_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)

    noise = b.expr(unreal.MaterialExpressionTextureSampleParameter2D, -520, 820, parameter_name="RippleNoise")
    if noise is not None:
        noise_texture = load_asset(ENGINE_NOISE_TEXTURE)
        if noise_texture is not None:
            try:
                noise.set_editor_property("texture", noise_texture)
                noise.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GREYSCALE)
            except Exception as exc:  # noqa: BLE001
                b.failures.append(f"ripple noise default: {exc}")
    b.connect(ripple_uv, "", noise, "UVs")
    rough = b.expr(unreal.MaterialExpressionLinearInterpolate, -260, 820, const_a=0.02, const_b=0.12)
    b.connect(noise, "R", rough, "Alpha")
    b.to_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    # Colour: the Hudson and the East River carry sediment; the open Atlantic is darker and bluer.
    kind = b.expr(unreal.MaterialExpressionScalarParameter, -900, 940, parameter_name="KindIndex", default_value=2.0)
    river = b.expr(unreal.MaterialExpressionConstant3Vector, -900, 1020,
                   constant=unreal.LinearColor(0.030, 0.042, 0.038, 1.0))
    ocean = b.expr(unreal.MaterialExpressionConstant3Vector, -900, 1100,
                   constant=unreal.LinearColor(0.008, 0.020, 0.035, 1.0))
    kind_t = b.expr(unreal.MaterialExpressionDivide, -740, 940, const_b=2.0)
    b.connect(kind, "", kind_t, "A")
    kind_c = b.expr(unreal.MaterialExpressionClamp, -600, 940, min_default=0.0, max_default=1.0)
    b.connect(kind_t, "", kind_c, "")
    colour = b.expr(unreal.MaterialExpressionLinearInterpolate, -400, 1020)
    b.connect(river, "", colour, "A")
    b.connect(ocean, "", colour, "B")
    b.connect(kind_c, "", colour, "Alpha")
    b.to_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    spec = b.expr(unreal.MaterialExpressionConstant, -400, 1180, r=1.0)
    b.to_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    b.finish("M_NYC_Water")
    save_asset(f"{MATERIALS_ROOT}/M_NYC_Water")
    return True


def build_starmap_material(force: bool = False) -> bool:
    material, created = create_material("M_NYC_StarMap")
    if material is None or (not created and not force):
        return created
    try:
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property("two_sided", True)
    except Exception as exc:  # noqa: BLE001
        WARN(f"M_NYC_StarMap properties: {exc}")
    b = MaterialBuilder(material)
    stars = b.expr(unreal.MaterialExpressionTextureSampleParameter2D, -800, 0, parameter_name="StarMap")
    if stars is not None:
        default = load_asset(ENGINE_GREY_TEXTURE)
        if default is not None:
            try:
                stars.set_editor_property("texture", default)
            except Exception as exc:  # noqa: BLE001
                b.failures.append(f"star map default: {exc}")
    visibility = b.expr(unreal.MaterialExpressionScalarParameter, -800, 220, parameter_name="StarVisibility",
                        default_value=0.0)
    brightness = b.expr(unreal.MaterialExpressionScalarParameter, -800, 300, parameter_name="StarBrightness",
                        default_value=0.35)
    scaled = b.expr(unreal.MaterialExpressionMultiply, -520, 100)
    b.connect(stars, "RGB", scaled, "A")
    b.connect(visibility, "", scaled, "B")
    final = b.expr(unreal.MaterialExpressionMultiply, -300, 100)
    b.connect(scaled, "", final, "A")
    b.connect(brightness, "", final, "B")
    b.to_property(final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    b.finish("M_NYC_StarMap")
    save_asset(f"{MATERIALS_ROOT}/M_NYC_StarMap")
    return True


def ensure_materials(force: bool = False) -> dict:
    collection, _ = make_parameter_collection(force)
    result = {
        "MPC_Weather": collection is not None,
        "M_NYC_Master": build_master_material(collection, force),
        "M_NYC_Foliage": build_foliage_material(collection, force),
        "M_NYC_Terrain": build_terrain_material(collection, force),
        "M_NYC_Water": build_water_material(collection, force),
        "M_NYC_StarMap": build_starmap_material(force),
    }
    result["physical_materials"] = ensure_physical_materials(force)
    return result


# ------------------------------------------------------------------------------------------------- importing

def import_task(filename: str, destination_path: str, destination_name: str, replace: bool):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filename)
    task.set_editor_property("destination_path", destination_path)
    task.set_editor_property("destination_name", destination_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", replace)
    task.set_editor_property("save", True)
    return task


def run_tasks(tasks) -> list:
    if not tasks:
        return []
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    imported = []
    for task in tasks:
        try:
            paths = list(task.get_editor_property("imported_object_paths") or [])
        except Exception:  # noqa: BLE001
            paths = []
        imported.extend(paths)
    return imported


def apply_mesh_settings(asset_path: str, settings: dict) -> None:
    mesh = load_asset(asset_path)
    if mesh is None or not isinstance(mesh, unreal.StaticMesh):
        return
    changed = False
    if settings.get("nanite"):
        try:
            nanite = unreal.MeshNaniteSettings()
            nanite.set_editor_property("enabled", True)
            mesh.set_editor_property("nanite_settings", nanite)
            changed = True
        except Exception as exc:  # noqa: BLE001
            WARN(f"{asset_path}: nanite settings failed: {exc}")
    collision = settings.get("collision", "")
    try:
        body = mesh.get_editor_property("body_setup")
        if body is not None:
            if collision == "complex_as_simple":
                body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                changed = True
            elif collision in ("simple_box", "simple_capsule"):
                body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
                changed = True
    except Exception as exc:  # noqa: BLE001
        WARN(f"{asset_path}: collision settings failed: {exc}")
    if changed:
        save_asset(asset_path)


def apply_texture_settings(asset_path: str, settings: dict) -> None:
    texture = load_asset(asset_path)
    if texture is None or not isinstance(texture, unreal.Texture2D):
        return
    try:
        texture.set_editor_property("srgb", bool(settings.get("srgb", False)))
        compression = settings.get("compression", "")
        if compression == "Grayscale":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
        if settings.get("mip_gen") == "NoMipmaps":
            texture.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        if settings.get("address") == "Clamp":
            texture.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
            texture.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
        save_asset(asset_path)
    except Exception as exc:  # noqa: BLE001
        WARN(f"{asset_path}: texture settings failed: {exc}")


# Kinds this script imports as UE assets. The rest of the manifest is handled elsewhere by design:
#   crs / runtime_nycb / live_json / catalog / landmarks_index / water  -> copied verbatim into Content/NYCSim
#       by the commandlet's `stage` step (import_world.stage_files does the same when run standalone), because the
#       runtime reads those files directly, not through the asset registry;
#   terrain (terrain.png + terrain.json)                                -> read by UNYCTerrainImporter in
#       build_levels.py, which turns them into ALandscape actors rather than textures.
IMPORTABLE_KINDS = {
    "shells", "roofs", "tile_mesh", "pavement", "kit", "prop", "tree", "landmark", "vehicle",
    "character", "water_mask", "font",
}


def import_entries(manifest: dict, repo_root: str, tiles: set | None, max_tiles: int, force: bool,
                   dry_run: bool) -> dict:
    settings_by_id = manifest.get("import_settings", {})
    entries = {e["id"]: e for e in manifest.get("entries", [])}
    order = manifest.get("import_order") or list(entries.keys())

    seen_tiles: list[str] = []
    imported, skipped, failed = 0, 0, 0
    reasons: list[str] = []
    batch = []
    batch_meta = []

    def flush():
        nonlocal imported, failed
        if not batch:
            return
        paths = run_tasks(batch)
        imported += len(paths)
        if len(paths) < len(batch):
            failed += len(batch) - len(paths)
        for meta, task in zip(batch_meta, batch):
            try:
                object_paths = list(task.get_editor_property("imported_object_paths") or [])
            except Exception:  # noqa: BLE001
                object_paths = []
            for object_path in object_paths:
                asset_path = object_path.split(".")[0]
                if meta["settings"].get("texture"):
                    apply_texture_settings(asset_path, meta["settings"])
                else:
                    apply_mesh_settings(asset_path, meta["settings"])
                    if meta["settings"].get("physical_materials"):
                        by_material = (meta.get("entry") or {}).get("physical_materials") or {}
                        if by_material:
                            assign_physical_materials(asset_path, by_material)
                        else:
                            WARN(f"{asset_path}: pavement imported with no material -> surface class "
                                 f"map; every wheel contact on it resolves to Default")
        batch.clear()
        batch_meta.clear()

    for entry_id in order:
        entry = entries.get(entry_id)
        if entry is None:
            continue
        kind = entry.get("kind", "")
        if kind not in IMPORTABLE_KINDS:
            continue
        tile = entry.get("tile")
        if tile:
            if tiles is not None and tile not in tiles:
                continue
            if tile not in seen_tiles:
                if max_tiles and len(seen_tiles) >= max_tiles:
                    continue
                seen_tiles.append(tile)
        source = entry["src"]
        if not os.path.isabs(source):
            source = os.path.join(repo_root, source)
        if not os.path.isfile(source):
            skipped += 1
            reasons.append(f"{entry_id}: source missing ({source})")
            continue
        destination_path, destination_name = split_content_path(entry["dst"])
        full = f"{destination_path}/{destination_name}"
        if asset_exists(full) and not force:
            skipped += 1
            continue
        if dry_run:
            LOG(f"[dry run] import {source} -> {full}")
            imported += 1
            continue
        batch.append(import_task(source, destination_path, destination_name, force))
        batch_meta.append({"settings": settings_by_id.get(entry.get("import_settings", ""), {}),
                           "id": entry_id,
                           "entry": {"physical_materials": entry.get("physical_materials") or {}}})
        if len(batch) >= 32:
            flush()
    flush()
    return {
        "imported": imported, "skipped": skipped, "failed": failed,
        "tiles": len(seen_tiles), "reasons": reasons[:50],
    }


# ------------------------------------------------------------------------------------------------------ main

def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def default_manifest_path() -> str:
    project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    return os.path.normpath(os.path.join(project, "..", "..", "data", "processed", "unreal_manifest.json"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NYCSim asset import")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--tiles", default="", help="comma-separated tile names to restrict the import to")
    parser.add_argument("--max-tiles", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="re-import assets that already exist")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-materials", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    manifest_path = args.manifest or default_manifest_path()
    if not os.path.isfile(manifest_path):
        ERROR(f"manifest not found: {manifest_path}")
        return 1
    manifest = load_manifest(manifest_path)
    if manifest.get("schema") != "unreal_manifest/1":
        ERROR(f"unsupported manifest schema {manifest.get('schema')!r}")
        return 1
    repo_root = manifest.get("repo_root") or os.path.dirname(os.path.dirname(os.path.dirname(manifest_path)))

    started = time.time()
    materials = {} if args.skip_materials else ensure_materials(args.force)
    tiles = {t.strip() for t in args.tiles.split(",") if t.strip()} or None
    result = import_entries(manifest, repo_root, tiles, args.max_tiles, args.force, args.dry_run)
    result["materials"] = materials
    result["seconds"] = round(time.time() - started, 1)
    result["manifest"] = manifest_path
    LOG("import_assets: " + json.dumps(result, indent=1))
    for reason in result["reasons"]:
        WARN(f"  skipped {reason}")
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
