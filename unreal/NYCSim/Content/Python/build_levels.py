"""NYCSim level construction: the persistent map, one streaming level per tile per tier, the skyline levels and
every actor that belongs in them (landscape, building shells, roofs, props, kit instances).

Level layout consumed by UNYCTileStreamingSubsystem (see Streaming/NYCTileStreamingSubsystem.h):

    /Game/NYCSim/Maps/NYC                     persistent level: sky, water, player start
    /Game/NYCSim/Tiles/{t_m3_7}/{t_m3_7}_L0   landscape + shells + roofs + props + kit  (tier L0)
    /Game/NYCSim/Tiles/{t_m3_7}/{t_m3_7}_L1   shells + roofs                            (tier L1)
    /Game/NYCSim/Skyline/S4_{sx}_{sy}         merged 4 km HLOD mesh                     (tier L2)
    /Game/NYCSim/Skyline/S16_{sx}_{sy}        merged 16 km HLOD mesh                    (tier L3)

Tile names carry '-' which is illegal in UE object names, so the level and folder names use the pipeline's
content-safe form ('t_-3_7' -> 't_m3_7', manifest.safe_asset_name / NYCGeo::TileAssetName).

Run headless:  UnrealEditor-Cmd NYCSim.uproject -run=NYCImport -stages=levels
Or in-editor:  import build_levels; build_levels.main([])
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
import time

import unreal

LOG = unreal.log
WARN = unreal.log_warning
ERROR = unreal.log_error

CONTENT_ROOT = "/Game/NYCSim"
MAPS_ROOT = f"{CONTENT_ROOT}/Maps"
TILES_ROOT = f"{CONTENT_ROOT}/Tiles"
SKYLINE_ROOT = f"{CONTENT_ROOT}/Skyline"
MATERIALS_ROOT = f"{CONTENT_ROOT}/Materials"

TILE_SIZE_M = 1000.0
METRES_TO_UE = 100.0
# uint32 kit_id; int64 bin; float x, y, z, yaw, scale; uint32 seed, flags  (DATA_CONTRACTS §6, 40 bytes)
KIT_PLACEMENT = struct.Struct("<IqfffffII")


# ------------------------------------------------------------------------------------------------ coordinates

def tile_asset_name(tile: str) -> str:
    return tile.replace("-", "m")


def parse_tile(tile: str):
    body = tile[2:] if tile.startswith("t_") else tile
    split = body.find("_", 1)
    return int(body[:split]), int(body[split + 1:])


def tile_origin_m(tile: str):
    tx, ty = parse_tile(tile)
    return tx * TILE_SIZE_M, ty * TILE_SIZE_M


def nyctm_to_ue(east_m: float, north_m: float, up_m: float) -> unreal.Vector:
    """ARCHITECTURE §2: UE.X = east*100, UE.Y = -north*100, UE.Z = up*100."""
    return unreal.Vector(east_m * METRES_TO_UE, -north_m * METRES_TO_UE, up_m * METRES_TO_UE)


def heading_to_yaw(heading_deg: float) -> float:
    return (heading_deg - 90.0 + 180.0) % 360.0 - 180.0


def math_angle_to_yaw(angle_deg: float) -> float:
    return (-angle_deg + 180.0) % 360.0 - 180.0


# ---------------------------------------------------------------------------------------------- level helpers

def level_editor():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def asset_exists(path: str) -> bool:
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def load_asset(path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(path)
    except Exception:  # noqa: BLE001
        return None


def new_level(package_path: str) -> bool:
    """Creates an empty level asset and makes it the current level. Returns False when it could not be created."""
    subsystem = level_editor()
    if subsystem is None:
        ERROR("LevelEditorSubsystem unavailable (is this an editor build?)")
        return False
    if asset_exists(package_path):
        return bool(subsystem.load_level(package_path))
    try:
        return bool(subsystem.new_level(package_path))
    except Exception as exc:  # noqa: BLE001
        ERROR(f"new_level({package_path}) failed: {exc}")
        return False


def save_current_level() -> bool:
    subsystem = level_editor()
    if subsystem is None:
        return False
    try:
        return bool(subsystem.save_current_level())
    except Exception as exc:  # noqa: BLE001
        WARN(f"save_current_level failed: {exc}")
        return False


def editor_world():
    """The world the editor currently has open (the level build_levels just made current)."""
    try:
        return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:  # noqa: BLE001 - older builds only expose the deprecated library
        return unreal.EditorLevelLibrary.get_editor_world()


def spawn_instances(mesh, transforms: list, label: str, collision_profile: str = "NoCollision",
                    cast_shadow: bool = True) -> int:
    """One ANYCInstancedMeshActor per (tile, mesh): the HISM component is a default subobject, so the instances
    serialise into the level (a component added to a bare AActor from Python would not)."""
    actors = actor_subsystem()
    if actors is None or mesh is None or not transforms:
        return 0
    actor = actors.spawn_actor_from_class(
        unreal.NYCInstancedMeshActor, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
    if actor is None:
        return 0
    try:
        actor.set_actor_label(label)
        return int(actor.setup_instances(mesh, transforms, unreal.Name(collision_profile), cast_shadow))
    except Exception as exc:  # noqa: BLE001
        WARN(f"{label}: instancing failed: {exc}")
        return 0


def spawn_mesh(mesh, location: unreal.Vector, rotation: unreal.Rotator, label: str, scale: float = 1.0):
    actors = actor_subsystem()
    if actors is None or mesh is None:
        return None
    actor = actors.spawn_actor_from_object(mesh, location, rotation)
    if actor is None:
        return None
    try:
        actor.set_actor_label(label)
        if scale != 1.0:
            actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        component = actor.get_editor_property("static_mesh_component")
        if component is not None:
            component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    except Exception as exc:  # noqa: BLE001
        WARN(f"{label}: {exc}")
    return actor


# ------------------------------------------------------------------------------------------------ tile levels

def tile_level_path(tile: str, tier: str) -> str:
    name = tile_asset_name(tile)
    return f"{TILES_ROOT}/{name}/{name}_{tier}"


def tile_content_dir(tile: str) -> str:
    return f"{TILES_ROOT}/{tile_asset_name(tile)}"


def place_shells(tile: str, tier: str) -> int:
    """Building shells and roofs: one static-mesh actor per imported mesh, at the tile origin (the pipeline exports
    tile-local geometry, DATA_CONTRACTS §13)."""
    placed = 0
    origin_x, origin_y = tile_origin_m(tile)
    location = nyctm_to_ue(origin_x, origin_y, 0.0)
    for suffix in ("SM_Shells", "SM_Roofs"):
        path = f"{tile_content_dir(tile)}/{suffix}"
        mesh = load_asset(path)
        if mesh is None:
            continue
        if spawn_mesh(mesh, location, unreal.Rotator(0.0, 0.0, 0.0), f"{tile}_{suffix}_{tier}") is not None:
            placed += 1
    return placed


def place_props(tile: str, processed_root: str) -> int:
    """Street furniture from tiles/{tile}/props.json (written by the pipeline for UE's Python, which has no pyarrow).
    Coordinates in that file are tile-local metres."""
    path = os.path.join(processed_root, "tiles", tile, "props.json")
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        WARN(f"{tile}: props.json unreadable: {exc}")
        return 0
    origin_x, origin_y = tile_origin_m(tile)
    by_kind: dict[str, list] = {}
    for row in document.get("rows", []):
        kind = str(row.get("kind") or "").strip()
        if not kind or row.get("x") is None or row.get("y") is None:
            continue
        by_kind.setdefault(kind, []).append(row)

    placed = 0
    for kind, rows in sorted(by_kind.items()):
        mesh = None
        for candidate in (f"{CONTENT_ROOT}/Props/Misc/SM_{kind}", f"{CONTENT_ROOT}/Props/{kind}/SM_{kind}",
                          f"{CONTENT_ROOT}/Trees/SM_{kind}"):
            mesh = load_asset(candidate)
            if mesh is not None:
                break
        if mesh is None:
            continue
        transforms = []
        for row in rows:
            x = origin_x + float(row["x"])
            y = origin_y + float(row["y"])
            z = float(row.get("z") or 0.0)
            yaw = heading_to_yaw(float(row.get("heading") or 0.0))
            transforms.append(unreal.Transform(
                nyctm_to_ue(x, y, z), unreal.Rotator(0.0, 0.0, yaw), unreal.Vector(1.0, 1.0, 1.0)))
        placed += spawn_instances(mesh, transforms, f"{tile}_props_{kind}", "NYCBuildingShell")
    return placed


def place_kit(tile: str, processed_root: str, catalog: dict) -> int:
    """Facade kit instances from tiles/{tile}/kit_placements.bin (§6): one HISM per kit id."""
    path = os.path.join(processed_root, "tiles", tile, "kit_placements.bin")
    if not os.path.isfile(path) or not catalog:
        return 0
    size = os.path.getsize(path)
    if size % KIT_PLACEMENT.size:
        WARN(f"{tile}: kit_placements.bin size {size} is not a multiple of {KIT_PLACEMENT.size}")
    origin_x, origin_y = tile_origin_m(tile)
    by_kit: dict[int, list] = {}
    with open(path, "rb") as handle:
        while True:
            record = handle.read(KIT_PLACEMENT.size)
            if len(record) < KIT_PLACEMENT.size:
                break
            kit_id, _bin, x, y, z, yaw, scale, _seed, _flags = KIT_PLACEMENT.unpack(record)
            by_kit.setdefault(kit_id, []).append((x, y, z, yaw, scale))

    placed = 0
    for kit_id, rows in sorted(by_kit.items()):
        entry = catalog.get(str(kit_id)) or catalog.get(kit_id)
        if not entry:
            continue
        stem = entry.get("id_str") or entry.get("name") or entry.get("id") or str(kit_id)
        category = entry.get("category") or "Misc"
        mesh = load_asset(f"{CONTENT_ROOT}/Kit/{category}/SM_{stem}")
        if mesh is None:
            continue
        transforms = []
        for (x, y, z, yaw, scale) in rows:
            factor = scale or 1.0
            transforms.append(unreal.Transform(
                nyctm_to_ue(origin_x + x, origin_y + y, z),
                unreal.Rotator(0.0, 0.0, math_angle_to_yaw(yaw)),
                unreal.Vector(factor, factor, factor)))
        # Kit pieces are decoration on the shell, which already carries the collision.
        placed += spawn_instances(mesh, transforms, f"{tile}_kit_{stem}", "NoCollision")
    return placed


def build_tile_level(tile: str, tier: str, processed_root: str, catalog: dict, terrain_material) -> dict:
    package = tile_level_path(tile, tier)
    if not new_level(package):
        return {"tile": tile, "tier": tier, "ok": False, "error": "level could not be created"}

    result = {"tile": tile, "tier": tier, "ok": True, "shells": 0, "props": 0, "kit": 0, "landscape": False}
    result["shells"] = place_shells(tile, tier)

    if tier == "L0":
        terrain_dir = os.path.join(processed_root, "tiles")
        if os.path.isfile(os.path.join(terrain_dir, tile, "terrain.png")):
            import_result = unreal.NYCTerrainImporter.import_tile_landscape(
                editor_world(), tile, terrain_dir, terrain_material, None)
            try:
                result["landscape"] = bool(import_result.b_success)
                if not result["landscape"]:
                    result["landscape_error"] = str(import_result.error)
                    WARN(f"{tile}: landscape import failed: {import_result.error}")
            except Exception as exc:  # noqa: BLE001
                result["landscape_error"] = str(exc)
                WARN(f"{tile}: landscape result unreadable: {exc}")
        result["props"] = place_props(tile, processed_root)
        result["kit"] = place_kit(tile, processed_root, catalog)

    save_current_level()
    return result


# --------------------------------------------------------------------------------------------- skyline levels

def build_skyline_level(cell_km: int, sx: int, sy: int, mesh_path: str) -> dict:
    def part(value: int) -> str:
        return f"m{-value}" if value < 0 else str(value)

    package = f"{SKYLINE_ROOT}/S{cell_km}_{part(sx)}_{part(sy)}"
    mesh = load_asset(mesh_path)
    if mesh is None:
        return {"level": package, "ok": False, "error": f"no merged mesh at {mesh_path}"}
    if not new_level(package):
        return {"level": package, "ok": False, "error": "level could not be created"}
    location = nyctm_to_ue(sx * cell_km * 1000.0, sy * cell_km * 1000.0, 0.0)
    actor = spawn_mesh(mesh, location, unreal.Rotator(0.0, 0.0, 0.0), f"Skyline_{cell_km}km_{sx}_{sy}")
    if actor is not None:
        try:
            component = actor.get_editor_property("static_mesh_component")
            if component is not None:
                component.set_collision_profile_name("NYCSkyline")
        except Exception as exc:  # noqa: BLE001
            WARN(f"{package}: collision profile: {exc}")
    save_current_level()
    return {"level": package, "ok": actor is not None}


# ------------------------------------------------------------------------------------------------- main map

def build_main_map(spawn_tile: str | None) -> dict:
    package = f"{MAPS_ROOT}/NYC"
    if not new_level(package):
        return {"map": package, "ok": False}
    actors = actor_subsystem()
    created = []

    # The sky, water and streaming subsystems create what they need at BeginPlay; the map only needs a place to
    # start from, so that opening it in the editor already gives a playable world.
    spawn_location = unreal.Vector(-418000.0, -172000.0, 2000.0)  # Times Square, NYC_TM (-4180, 1720) m
    if spawn_tile:
        origin_x, origin_y = tile_origin_m(spawn_tile)
        spawn_location = nyctm_to_ue(origin_x + 500.0, origin_y + 500.0, 20.0)
    start = actors.spawn_actor_from_class(unreal.PlayerStart, spawn_location, unreal.Rotator(0.0, 0.0, 30.0))
    if start is not None:
        start.set_actor_label("NYCPlayerStart")
        created.append("PlayerStart")

    save_current_level()
    return {"map": package, "ok": True, "actors": created}


# ------------------------------------------------------------------------------------------------------ main

def default_manifest_path() -> str:
    project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    return os.path.normpath(os.path.join(project, "..", "..", "data", "processed", "unreal_manifest.json"))


def load_catalog(processed_root: str) -> dict:
    for candidate in ("kit_catalog.json", os.path.join("kit", "kit_catalog.json")):
        path = os.path.join(processed_root, candidate)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    document = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                WARN(f"kit catalog {path} unreadable: {exc}")
                return {}
            entries = document.get("entries", document) if isinstance(document, dict) else document
            if isinstance(entries, list):
                return {str(e.get("kit_id", e.get("id"))): e for e in entries}
            if isinstance(entries, dict):
                return {str(k): v for k, v in entries.items()}
    return {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NYCSim level construction")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--tiles", default="")
    parser.add_argument("--max-tiles", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-map", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    manifest_path = args.manifest or default_manifest_path()
    if not os.path.isfile(manifest_path):
        ERROR(f"manifest not found: {manifest_path}")
        return 1
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    repo_root = manifest.get("repo_root") or os.path.dirname(os.path.dirname(os.path.dirname(manifest_path)))
    processed_root = os.path.join(repo_root, "data", "processed")

    requested = [t.strip() for t in args.tiles.split(",") if t.strip()]
    tiles = requested or sorted(manifest.get("tiles", {}).keys())
    if args.max_tiles:
        tiles = tiles[:args.max_tiles]

    terrain_material = load_asset(f"{MATERIALS_ROOT}/M_NYC_Terrain")
    if terrain_material is None:
        WARN("M_NYC_Terrain is missing; landscapes are imported with the default material "
             "(run import_assets.py first)")
    catalog = load_catalog(processed_root)

    started = time.time()
    summary = {"tiles": [], "skyline": [], "map": None, "manifest": manifest_path, "tile_count": len(tiles)}

    if args.dry_run:
        LOG(f"[dry run] would build {len(tiles)} tiles ({tiles[:5]}{'...' if len(tiles) > 5 else ''})")
        return 0

    if not args.skip_map:
        summary["map"] = build_main_map(tiles[0] if tiles else None)

    for tile in tiles:
        for tier in ("L0", "L1"):
            summary["tiles"].append(build_tile_level(tile, tier, processed_root, catalog, terrain_material))

    # Skyline levels: one per 4 km and 16 km parent cell that has a merged mesh in the content tree.
    cells4, cells16 = set(), set()
    for tile in tiles:
        tx, ty = parse_tile(tile)
        cells4.add((math.floor(tx / 4), math.floor(ty / 4)))
        cells16.add((math.floor(tx / 16), math.floor(ty / 16)))
    for (sx, sy) in sorted(cells4):
        mesh_path = f"{CONTENT_ROOT}/Skyline/SM_S4_{('m' + str(-sx)) if sx < 0 else sx}_{('m' + str(-sy)) if sy < 0 else sy}"
        if asset_exists(mesh_path):
            summary["skyline"].append(build_skyline_level(4, sx, sy, mesh_path))
    for (sx, sy) in sorted(cells16):
        mesh_path = f"{CONTENT_ROOT}/Skyline/SM_S16_{('m' + str(-sx)) if sx < 0 else sx}_{('m' + str(-sy)) if sy < 0 else sy}"
        if asset_exists(mesh_path):
            summary["skyline"].append(build_skyline_level(16, sx, sy, mesh_path))

    summary["seconds"] = round(time.time() - started, 1)
    failures = [t for t in summary["tiles"] if not t.get("ok")]
    summary["failed_levels"] = len(failures)
    LOG("build_levels: " + json.dumps({k: v for k, v in summary.items() if k != "tiles"}, indent=1))
    LOG(f"build_levels: {len(summary['tiles'])} levels, {len(failures)} failed")
    for failure in failures[:20]:
        WARN(f"  {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
