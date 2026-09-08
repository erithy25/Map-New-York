"""Generate ``data/processed/unreal_manifest.json`` (DATA_CONTRACTS §14) and the UE-readable per-tile exports.

UE 5.4's embedded Python has no pyarrow, so every tabular input the editor scripts need is re-exported here:

* ``tiles/{tile}/props.json``      <- tiles/{tile}/props.parquet            (§8)
* ``tiles/{tile}/signs.json``      <- roads/signs.parquet binned by tile     (§7)
* ``tiles/{tile}/lanes_debug.json``<- roads/lanes.parquet binned by tile     (§7, ``--with-lanes`` only)
* ``tiles/{tile}/water_mask.png``  <- water/hydrography.parquet rasterised   (§4, 501x501 8-bit, 2 m, matches terrain.png)
* ``unreal_water.json``            <- hydrography + shoreline + structures + live/tides.json (defined in §14.1 below)
* ``tiles/{tile}/kit_placements.bin`` is referenced as-is (raw little-endian records, §6; UE Python reads it with ``struct``)

and every ``blender_out/**/*.glb`` / ``terrain.png`` / ``runtime/*.nycb`` / ``live/*.json`` is listed with its target
content path, import-settings id and dependency order. Consumed by ``unreal/NYCSim/Content/Python/import_world.py``.

§14.1 ``unreal_water.json`` (appended contract, this module is its producer)::

    {"schema_version": 1, "generated_at": ..., "water_level_m": 0.0,
     "bodies": [{"water_id", "kind", "name", "tidal", "area_m2", "tiles": [tile,...]}],
     "flow": {"station", "current_speed_mps", "current_dir_deg", "water_level_m", "predicted_at"} | null,
     "tiles": {tile: {"water_fraction": 0..1, "mask_png": "tiles/{tile}/water_mask.png", "bodies": [water_id,...],
                      "dominant_kind": str, "tidal": bool, "shoreline_m": float, "structures": int}}}

Run: ``python -m nycsim_pipeline.unreal.manifest [--processed DIR] [--blender-out DIR] [--out FILE] [--with-lanes] [--no-hash]``
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import re
from urllib.parse import unquote
import struct
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from .. import SCHEMA_VERSION
from ..crs import TILE_SIZE_M
from ..manifest import git_commit, record_processed
from ..paths import BLENDER_OUT, PROCESSED, REPO_ROOT
from ..tiling import Tile, tile_of
from .glb import GlbError, glb_summary

log = logging.getLogger("nycsim.unreal.manifest")

MANIFEST_SCHEMA = "unreal_manifest/1"
CONTENT_ROOT = "/Game/NYCSim"
TERRAIN_SAMPLES = 501
KIT_PLACEMENT_STRUCT = struct.Struct("<IqfffffII")  # uint32 kit_id; int64 bin; float x,y,z,yaw,scale; uint32 seed, flags
assert KIT_PLACEMENT_STRUCT.size == 40, KIT_PLACEMENT_STRUCT.size

# Import-settings ids understood by import_assets.py. Kept here so the pipeline and the editor agree on the vocabulary.
IMPORT_SETTINGS: dict[str, dict[str, Any]] = {
    "shell_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static", "notes": "per-tile building shells; one static mesh per (tile, material class) mesh in the glb"},
    # The road surfaces (blender/roads/build_pavement.py). Nanite for the same reason the shells use
    # it, complex-as-simple collision because the wheels line-trace against the actual triangles and
    # a convex hull of a kilometre of asphalt is meaningless, and physical materials because
    # UNYCVehicleMovementComponent resolves an EPhysicalSurface per wheel contact and feeds it to the
    # tyre friction table -- without them every surface in the city is SurfaceClass::Default and
    # cobblestone, steel plate and painted crosswalk all grip like dry asphalt.
    "pavement_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static", "physical_materials": True, "notes": "per-tile road surfaces; one static mesh per (kind, surface) in the glb, each carrying the SurfaceClass its material maps to"},
    # The merged distant skyline (blender/buildings/build_lod_merged.py): one mesh per 4 km cell at
    # level 2 and per 16 km cell at level 3. No collision - you never touch it, it is what the city
    # looks like from a mile away - and Nanite, which is what makes 838 MB of it affordable.
    "parkground_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static", "physical_materials": True, "notes": "per-tile open-space ground; one static mesh per kind, each carrying the SurfaceClass its material maps to (Grass, Water and Ice are produced here and nowhere else)"},
    "structure_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static", "physical_materials": True, "notes": "per-tile elevated railway and waterfront structures; one static mesh per part, each carrying the SurfaceClass its material maps to"},
    "skyline_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "none", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static", "notes": "merged skyline cell; build_levels.py spawns one actor per cell in its own level"},
    "roof_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static"},
    "kit_nanite_lod": {"nanite": True, "lods_from_suffix": True, "collision": "simple_box", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Master", "mobility": "static", "instanced": True},
    "landmark_nanite": {"nanite": True, "lods_from_suffix": True, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Master", "mobility": "static"},
    "prop_lod": {"nanite": False, "lods_from_suffix": True, "collision": "simple_box", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Master", "mobility": "static", "instanced": True},
    "tree_lod": {"nanite": False, "lods_from_suffix": True, "collision": "simple_capsule", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Foliage", "mobility": "static", "instanced": True},
    "vehicle_skeletal": {"skeletal": True, "nanite": False, "import_animations": False, "material_master": "M_NYC_Vehicle", "physics_asset": True},
    "character_skeletal": {"skeletal": True, "nanite": False, "import_animations": True, "import_morph_targets": True, "material_master": "M_NYC_Character", "physics_asset": True},
    # ADR-015: Landscape only accepts component sizes 7/15/31/63/127/255 quads, so the importer
    # resamples the 501-sample 2 m grid to 505 samples (8 components of 63 quads at 198.412698 cm).
    "terrain_heightmap": {"landscape": True, "samples": TERRAIN_SAMPLES, "spacing_m": 2.0,
                          "component_size_quads": 63, "components_per_side": 8, "sections_per_component": 1,
                          "import_samples": 505, "import_spacing_cm": 198.412698,
                          "notes": "pipeline emits 501 samples at 2.0 m; UNYCTerrainImporter resamples to 505 samples of 198.412698 cm, still exactly 1000 m wide with borders unchanged (ADR-015)"},
    "texture_mask": {"texture": True, "srgb": False, "compression": "Grayscale", "mip_gen": "NoMipmaps", "address": "Clamp", "notes": "8-bit water/shoreline mask, 1 texel = 2 m"},
    "raw_copy": {"copy": True, "notes": "copied verbatim under Content/NYCSim/Runtime (staged as UFS)"},
    "json_copy": {"copy": True, "notes": "small JSON copied verbatim"},
    # 74 licensed .ogg files - 7 radio stations and the vehicle/world SFX - had no import rule at
    # all, so the manifest never listed them and the car had no radio and no sound effects. Ogg
    # Vorbis imports to USoundWave; streaming is on for the radio because a station's tracks are
    # minutes long and there is no reason to hold them resident.
    "sound_wave": {"sound": True, "streaming": False, "compression_quality": 70, "looping": False,
                   "notes": "ogg -> USoundWave"},
    "sound_wave_stream": {"sound": True, "streaming": True, "compression_quality": 60, "looping": False,
                          "notes": "ogg -> USoundWave, streamed; radio tracks run for minutes"},
    "font": {"font": True, "hinting": "Default", "loading_policy": "LazyLoad", "notes": "OTF -> UFont (offline cache 64/128 px) for UCanvasRenderTarget2D sign text"},
}

# blender_out subdirectory -> (import settings id, content path template). {stem} = glb file stem, {tile} = tile name.
GLB_RULES: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/tile_buildings\.glb$"), "shell_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_Shells", "shells"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/roofs\.glb$"), "roof_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_Roofs", "roofs"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/tile_pavement\.glb$"), "pavement_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_Pavement", "pavement"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/tile_structures\.glb$"), "structure_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_Structures", "structure"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/tile_parkground\.glb$"), "parkground_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_ParkGround", "parkground"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/(?P<stem>[^/]+)\.glb$"), "shell_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_{{stem}}", "tile_mesh"),
    # The merged skyline. build_levels.build_skyline_level looks for SM_S4_<x>_<y> (4 km cells) and
    # SM_S16_<x>_<y> (16 km), with a negative index written as 'm<n>' -- which is exactly what
    # safe_asset_name produces. 90 of these files had no rule at all, so the manifest skipped all
    # 838 MB of them with a warning and the city had nothing beyond the streamed tiles.
    (re.compile(r"^tiles/_merged/l2/L2_(?P<sx>-?\d+)_(?P<sy>-?\d+)\.glb$"), "skyline_nanite", f"{CONTENT_ROOT}/Skyline/SM_S4_{{sx}}_{{sy}}", "skyline"),
    (re.compile(r"^tiles/_merged/l3/L3_(?P<sx>-?\d+)_(?P<sy>-?\d+)\.glb$"), "skyline_nanite", f"{CONTENT_ROOT}/Skyline/SM_S16_{{sx}}_{{sy}}", "skyline"),
    (re.compile(r"^kit/(?P<stem>[^/]+)\.glb$"), "kit_nanite_lod", f"{CONTENT_ROOT}/Kit/{{category}}/SM_{{stem}}", "kit"),
    (re.compile(r"^kit/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "kit_nanite_lod", f"{CONTENT_ROOT}/Kit/{{category}}/SM_{{stem}}", "kit"),
    (re.compile(r"^landmarks/(?P<stem>[^/]+)\.glb$"), "landmark_nanite", f"{CONTENT_ROOT}/Landmarks/SM_{{stem}}", "landmark"),
    (re.compile(r"^landmarks/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "landmark_nanite", f"{CONTENT_ROOT}/Landmarks/{{category}}/SM_{{stem}}", "landmark"),
    (re.compile(r"^props/trees?/(?P<stem>[^/]+)\.glb$"), "tree_lod", f"{CONTENT_ROOT}/Trees/SM_{{stem}}", "tree"),
    (re.compile(r"^props/(?P<stem>[^/]+)\.glb$"), "prop_lod", f"{CONTENT_ROOT}/Props/{{category}}/SM_{{stem}}", "prop"),
    (re.compile(r"^props/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "prop_lod", f"{CONTENT_ROOT}/Props/{{category}}/SM_{{stem}}", "prop"),
    # The four content paths below are the ones the ENGINE names, not the ones this file found
    # convenient. UNYCGameplaySettings hardcodes /Game/NYCSim/Vehicles/Player/SK_FusionHybrid,
    # /Game/NYCSim/Vehicles/Fleet, /Game/NYCSim/Characters/Player/SK_Player and
    # /Game/NYCSim/Characters/Crowd -- note Characters, plural. The manifest used to write
    # Vehicles/fusion_hybrid/SK_fusion_hybrid and Character/npc/SK_npc_00_*, so the player's car,
    # the player's body, the traffic fleet and the crowd would each have imported to a path nothing
    # ever looks in. The specific rules must precede the generic ones.
    (re.compile(r"^vehicles/fusion_hybrid\.glb$"), "vehicle_skeletal", f"{CONTENT_ROOT}/Vehicles/Player/SK_FusionHybrid", "vehicle"),
    (re.compile(r"^vehicles/(?P<stem>[^/]+)\.glb$"), "vehicle_skeletal", f"{CONTENT_ROOT}/Vehicles/Fleet/SK_{{stem}}", "vehicle"),
    (re.compile(r"^vehicles/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "vehicle_skeletal", f"{CONTENT_ROOT}/Vehicles/Fleet/SK_{{stem}}", "vehicle"),
    (re.compile(r"^character/player\.glb$"), "character_skeletal", f"{CONTENT_ROOT}/Characters/Player/SK_Player", "character"),
    (re.compile(r"^character/npc/(?P<stem>[^/]+)\.glb$"), "character_skeletal", f"{CONTENT_ROOT}/Characters/Crowd/SK_{{stem}}", "character"),
    (re.compile(r"^character/(?P<stem>[^/]+)\.glb$"), "character_skeletal", f"{CONTENT_ROOT}/Characters/{{stem}}/SK_{{stem}}", "character"),
    (re.compile(r"^character/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "character_skeletal", f"{CONTENT_ROOT}/Characters/{{category}}/SK_{{stem}}", "character"),
]

_ASSET_NAME_RE = re.compile(r"[^A-Za-z0-9_]")


def safe_asset_name(s: str) -> str:
    """UE asset names: letters, digits, underscore; must not start with a digit."""
    s = _ASSET_NAME_RE.sub("_", s.replace("-", "m"))  # tile names carry '-' -> 'm' keeps t_-3_7 -> t_m3_7 unambiguous
    if not s or s[0].isdigit():
        s = "_" + s
    return s


#: Template fields that are already asset-safe and must be passed through verbatim. A tile name and a
#: skyline cell index both carry their own convention for a negative number ('m1', not '-1'), and
#: safe_asset_name would additionally put an underscore in front of a positive one because it starts
#: with a digit -- turning SM_S16_0_1 into SM_S16__0__1, which is not the asset build_levels.py loads.
_LITERAL_FIELDS = ("tile", "sx", "sy")


def cell_part(value: int | str) -> str:
    """A skyline cell index the way ``build_levels.build_skyline_level`` writes it: ``-1`` -> ``m1``."""
    v = int(value)
    return f"m{-v}" if v < 0 else str(v)


def content_path(template: str, **kw: str) -> str:
    kw = {k: (v if k in _LITERAL_FIELDS else safe_asset_name(v)) for k, v in kw.items()}
    kw.setdefault("category", "Misc")
    if "tile" in kw:
        kw["tile"] = safe_asset_name(kw["tile"])
    return template.format(**kw)


def resolve_glb(rel: str, *, category: str | None = None, stem: str | None = None):
    """``(content path, import-settings id, kind)`` for a ``blender_out``-relative glb path.

    The single place that turns a rule into a destination. It exists because the test that checks the
    engine and the pipeline agree about where an asset lands must not reimplement the rule it is
    checking -- that is how a check ends up passing against its own copy of the bug.
    """
    rule = next(((rx, st, tpl, kind) for rx, st, tpl, kind in GLB_RULES if rx.match(rel)), None)
    if rule is None:
        return None
    rx, settings, tpl, kind = rule
    gd = rx.match(rel).groupdict()
    fields = {k: (v or "") for k, v in gd.items()}
    for axis in ("sx", "sy"):
        if fields.get(axis):
            fields[axis] = cell_part(fields[axis])
    fields.update(tile=gd.get("tile", ""),
                  stem=stem or gd.get("stem") or Path(rel).stem,
                  category=category or gd.get("category") or "Misc")
    return content_path(tpl, **fields), settings, kind


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


class ManifestBuilder:
    def __init__(self, processed: Path, blender_out: Path, repo_root: Path = REPO_ROOT, *,
                 hash_files: bool = True, with_lanes: bool = False, tiles: set[str] | None = None):
        self.processed = Path(processed)
        self.blender_out = Path(blender_out)
        self.repo_root = Path(repo_root)
        self.hash_files = hash_files
        self.with_lanes = with_lanes
        #: When given, only these tiles are listed and only their per-tile files are written. A full
        #: run writes a water_mask.png and a props.json for each of 2,916 tiles, which is both slow
        #: and, on a machine with a few gigabytes free, impossible. Everything that is not per-tile -
        #: the vehicles, the character, the kit, the props, the landmarks, the runtime, the audio -
        #: is listed regardless, because none of it is a tile's to own.
        self.tiles_filter = set(tiles) if tiles else None
        self.entries: list[dict[str, Any]] = []
        self.tiles: dict[str, dict[str, Any]] = {}
        self.warnings: list[str] = []
        self._ids: set[str] = set()
        self.kit_catalog: dict[int, dict[str, Any]] = {}
        self.props_catalog: dict[int, dict[str, Any]] = {}
        #: Prop kinds whose rows resolve to no exported asset, and how many rows that is. Filled by
        #: ``add_tiles``; reported in the manifest so the gap is counted rather than assumed empty.
        self.prop_kinds_without_an_asset: dict[str, int] = {}
        #: Prop kinds with no asset **on purpose**, because another stage builds them, and how many
        #: rows that is. Kept apart from the gap count above so neither number lies about the other.
        self.prop_kinds_built_elsewhere: dict[str, int] = {}

    # ------------------------------------------------------------------ helpers
    def _add(self, id_: str, kind: str, src: Path, dst: str, settings: str, *, deps: Iterable[str] = (), tile: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        if id_ in self._ids:
            raise ValueError(f"duplicate manifest id {id_}")
        if settings not in IMPORT_SETTINGS:
            raise ValueError(f"unknown import settings id {settings}")
        if not src.exists():
            raise FileNotFoundError(src)
        self._ids.add(id_)
        e: dict[str, Any] = {
            "id": id_, "kind": kind, "src": _rel(src, self.repo_root), "dst": dst, "import_settings": settings,
            "bytes": src.stat().st_size, "deps": sorted(set(deps)),
        }
        if tile:
            e["tile"] = tile
            self.tiles.setdefault(tile, {"assets": []})["assets"].append(id_)
        if self.hash_files:
            e["sha256"] = _sha256(src)
        if extra:
            e.update(extra)
        self.entries.append(e)
        return e

    def _sidecars(self, glb: Path, uris: Iterable[str]) -> tuple[list[str], list[str]]:
        """``(repo-relative files that must travel with this glb, the ones that are missing)``.

        A ``.glb`` used to be self-contained.  Since ``blender/common/glb_textures`` moved each
        distinct image out of the binary chunk -- 2.61 GB of the 2.95 GB embedded across this
        project's files was a byte-for-byte duplicate, and Unreal makes one ``UTexture2D`` per
        reference -- it names its images as relative files instead.  A package that shipped only the
        entries' ``src`` paths would deliver meshes with no textures on them and no error to say so,
        which is why the missing ones are a warning here and a test failure in the packager.

        The URIs this project writes are plain descending paths, but a glTF URI is percent-encoded
        by specification, so they are decoded before they become paths, and a path that climbs out
        of the ``.glb``'s own directory is refused rather than followed.
        """
        found: list[str] = []
        absent: list[str] = []
        for uri in uris:
            rel_uri = unquote(uri)
            target = (glb.parent / rel_uri).resolve()
            try:
                target.relative_to(glb.parent.resolve())
            except ValueError:
                absent.append(uri)
                continue
            (found if target.is_file() else absent).append(
                _rel(target, self.repo_root) if target.is_file() else uri)
        return sorted(set(found)), sorted(set(absent))

    def _warn(self, msg: str) -> None:
        log.warning(msg)
        self.warnings.append(msg)

    def _tile_dir(self, tile: str) -> Path:
        return self.processed / "tiles" / tile

    # ------------------------------------------------------------------ catalogs
    def load_catalogs(self) -> None:
        self.kit_catalog = self._load_kit_catalog()
        self.props_catalog = self._load_catalog(["props_catalog.json", "props/props_catalog.json"], "props/catalog", "kind")

    def _load_kit_catalog(self) -> dict[int, dict[str, Any]]:
        """The facade kit keyed by the integer ``kit_id`` that ``kit_placements.bin`` stores.

        ``blender_out/kit/catalog/*.json`` -- what this used to read -- carries a **string** ``id``
        (``win_aluminum_slider``) and no ``kit_id`` at all, so every entry was hashed into the uint32
        space and no placement could ever match one: all 5,713,269 kit instances of the first-drive
        region were reported missing from the catalogue, and every kit glb lost its category and was
        filed under ``Misc``.  ``data/processed/facade/kit_ids.json`` is the file that holds the
        mapping -- it is written from the same catalogue by the facade stage and states the id
        formula -- and until now nothing read it.
        """
        p = self.processed / "facade" / "kit_ids.json"
        if p.is_file():
            doc = json.loads(p.read_text())
            pieces = doc.get("pieces") or []
            out: dict[int, dict[str, Any]] = {}
            for piece in pieces:
                try:
                    out[int(piece["kit_id"])] = piece
                except (KeyError, TypeError, ValueError):
                    self._warn(f"{p}: piece without a usable kit_id: {piece.get('catalog_id')}")
            log.info("catalog %s: %d entries", p, len(out))
            return out
        return self._load_catalog(["kit_catalog.json", "kit/kit_catalog.json"], "kit/catalog", "kit_id")

    def _load_catalog(self, merged_candidates: list[str], entries_dir: str, key: str) -> dict[int, dict[str, Any]]:
        for cand in merged_candidates:
            for base in (self.processed, self.blender_out):
                p = base / cand
                if p.exists():
                    doc = json.loads(p.read_text())
                    ents = doc["entries"] if isinstance(doc, dict) and "entries" in doc else doc
                    if isinstance(ents, dict):
                        ents = [dict(v, id=k) if isinstance(v, dict) else {"id": k, "glb": v} for k, v in ents.items()]
                    return self._index_catalog(ents, key, p)
        d = self.blender_out / entries_dir
        if d.is_dir():
            ents = []
            for p in sorted(d.glob("*.json")):
                try:
                    ents.append(json.loads(p.read_text()))
                except json.JSONDecodeError as e:
                    self._warn(f"catalog entry {p} unreadable: {e}")
            return self._index_catalog(ents, key, d)
        return {}

    def _index_catalog(self, ents: list[dict[str, Any]], key: str, src: Path) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        for e in ents:
            k = e.get(key, e.get("id"))
            try:
                ki = int(k)
            except (TypeError, ValueError):
                # string ids: hash deterministically into the uint32 space the placements use, keep the string too
                ki = int(hashlib.sha256(str(k).encode()).hexdigest()[:8], 16)
                e = dict(e, id_str=str(k))
            if ki in out:
                self._warn(f"catalog {src}: duplicate {key} {k}")
            out[ki] = e
        log.info("catalog %s: %d entries", src, len(out))
        return out

    # ------------------------------------------------------------------ glbs
    def add_glbs(self) -> int:
        n = 0
        if not self.blender_out.is_dir():
            self._warn(f"blender_out missing: {self.blender_out}")
            return 0
        for glb in sorted(self.blender_out.rglob("*.glb")):
            rel = glb.relative_to(self.blender_out).as_posix()
            rule = next(((rx, s, tpl, kind) for rx, s, tpl, kind in GLB_RULES if rx.match(rel)), None)
            if rule is None:
                self._warn(f"no import rule for {rel}; skipped")
                continue
            rx, settings, tpl, kind = rule
            m = rx.match(rel)
            assert m is not None
            gd = m.groupdict()
            if self.tiles_filter is not None and gd.get("tile") and gd["tile"] not in self.tiles_filter:
                continue
            try:
                summary = glb_summary(glb)
            except GlbError as e:
                self._warn(str(e))
                continue
            extras = summary.get("extras") or {}
            category = gd.get("category") or str(extras.get("category") or "").strip() or None
            stem = gd.get("stem") or glb.stem
            if kind == "kit" and not category:
                cat = self.kit_catalog.get(_kit_id_from(extras, stem))
                category = (cat or {}).get("category")
            if kind == "prop" and not category:
                cat = self.props_catalog.get(_kit_id_from(extras, stem))
                category = (cat or {}).get("category")
            resolved = resolve_glb(rel, category=category, stem=stem)
            assert resolved is not None      # the rule matched above
            dst = resolved[0]
            if kind == "tree":
                settings = "tree_lod"
            if kind in ("kit", "prop") and summary["has_lod1"] is False and settings.endswith("_lod"):
                pass  # LOD chain absent: importer builds one LOD; recorded below for the report
            extra = {
                "glb": {k: v for k, v in summary.items() if k != "extras"},
                "nycsim": extras,
                "category": category or "Misc",
            }
            if kind in ("pavement", "structure", "parkground"):
                # Lift the material -> SurfaceClass map out of the glb's asset extras and onto the
                # entry itself, so import_assets.py can hang the right UPhysicalMaterial on each
                # slot without reopening the file. The index is nycsim_gameplay::SurfaceClass, which
                # is also the EPhysicalSurface index DefaultEngine.ini declares.
                by_material = extras.get("surface_class") or {}
                if isinstance(by_material, dict) and by_material:
                    extra["physical_materials"] = {str(k): int(v) for k, v in sorted(by_material.items())}
                else:
                    self._warn(f"{rel}: no surface_class map in the glb extras; "
                               f"every wheel contact there will resolve to SurfaceClass::Default")
            sidecars, absent = self._sidecars(glb, summary.get("image_uris") or [])
            if absent:
                self._warn(f"{rel}: names {len(absent)} image file(s) that are not on disk "
                           f"({', '.join(absent[:3])}); the import would produce an untextured mesh")
            if sidecars:
                extra["sidecars"] = sidecars
            id_ = f"glb:{rel}"
            deps: list[str] = []
            self._add(id_, kind, glb, dst, settings, deps=deps, tile=gd.get("tile"), extra=extra)
            n += 1
        log.info("glbs: %d", n)
        return n

    # ------------------------------------------------------------------ resolved catalogues
    def resolve_catalogs(self) -> int:
        """Write the two id -> content path tables the editor's Python needs, from the entries above.

        ``kit_placements.bin`` stores an integer ``kit_id`` and ``props.parquet`` an int16 ``kind``.
        Neither is the name of an asset, and ``build_levels.py`` was rebuilding one anyway --
        ``/Game/NYCSim/Kit/{piece category}/SM_{stem}`` for the kit, ``/Game/NYCSim/Props/{kind}/SM_{kind}``
        for the props -- from vocabularies the import does not use.  The kit imports under the glb's
        folder (``Kit/facade/``), not the piece's category (``window``), and a prop's ``kind`` is the
        integer 14, not ``street_lamp`` and not ``lamp_cobra_davit``.  So nothing resolved and nothing
        was placed.

        The path an asset imports to is decided here, in ``add_glbs``, so this joins on it directly:
        no name is reconstructed anywhere, and a rule change in ``GLB_RULES`` moves both tables with
        it.  Props are resolved per row in ``add_tiles`` against the same index.
        """
        by_src = {e["src"]: e for e in self.entries if e["kind"] in ("kit", "prop", "tree")}
        pieces, missing = [], []
        for kit_id, piece in sorted(self.kit_catalog.items()):
            glb = piece.get("glb")
            entry = by_src.get(_rel(self.blender_out / glb, self.repo_root)) if glb else None
            if entry is None:
                missing.append({"kit_id": kit_id, "catalog_id": piece.get("catalog_id"), "glb": glb})
                continue
            pieces.append({"kit_id": kit_id, "catalog_id": piece.get("catalog_id"),
                           "category": piece.get("category"), "glb": glb,
                           "content_path": entry["dst"]})
        if missing and self.kit_catalog:
            self._warn(f"{len(missing)} kit pieces have no imported mesh "
                       f"(first: {[m['catalog_id'] for m in missing[:5]]}); their placements cannot be spawned")
        if not pieces:
            # No kit in this world: writing an empty catalogue would put a file in the package that
            # tells the editor there is nothing to place, which is not the same as not shipping one.
            return 0
        doc = {"schema_version": SCHEMA_VERSION, "generated_at": _now(),
               "source": "data/processed/facade/kit_ids.json + this manifest's kit entries",
               "content_root": CONTENT_ROOT, "count": len(pieces), "entries": pieces,
               "without_a_mesh": missing}
        out = self.processed / "kit_catalog.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=1))
        self._add("catalog:kit_catalog.json", "catalog", out, f"{CONTENT_ROOT}/Runtime/kit_catalog.json", "json_copy")
        return len(pieces)

    def _prop_asset_index(self) -> tuple[Any, dict[str, str]]:
        """The prop resolver and the ``blender_out``-relative glb -> content path map it feeds."""
        from ..furniture import assets as prop_assets
        by_src = {e["src"]: e["dst"] for e in self.entries}
        paths = {}
        for rel, dst in ((k[len("blender_out/"):], v) for k, v in by_src.items()
                         if k.startswith("blender_out/")):
            paths[rel] = dst
        return prop_assets.load(self.processed, self.blender_out), paths

    # ------------------------------------------------------------------ tiles
    def add_tiles(self) -> int:
        tiles_dir = self.processed / "tiles"
        if not tiles_dir.is_dir():
            self._warn(f"no tiles directory {tiles_dir}")
            return 0
        n = 0
        index_rows = self._read_tile_index()
        prop_assets, asset_paths = self._prop_asset_index()
        unmapped: dict[str, int] = {}
        for td in sorted(p for p in tiles_dir.iterdir() if p.is_dir() and _TILE_RE.match(p.name)):
            tile = td.name
            if self.tiles_filter is not None and tile not in self.tiles_filter:
                continue
            t = Tile.parse(tile)
            info = self.tiles.setdefault(tile, {"assets": []})
            info.update({"tx": t.tx, "ty": t.ty, "x0": t.x0, "y0": t.y0, "size_m": TILE_SIZE_M})
            if tile in index_rows:
                info["index"] = index_rows[tile]
            terrain_png, terrain_json = td / "terrain.png", td / "terrain.json"
            if terrain_png.exists() and terrain_json.exists():
                meta = json.loads(terrain_json.read_text())
                if int(meta.get("samples", 0)) != TERRAIN_SAMPLES:
                    self._warn(f"{tile}: terrain.json samples={meta.get('samples')} != {TERRAIN_SAMPLES}")
                self._add(f"terrain:{tile}", "terrain", terrain_png, f"{CONTENT_ROOT}/Maps/NYC/Landscape/{safe_asset_name(tile)}", "terrain_heightmap", tile=tile,
                          extra={"terrain": {k: meta.get(k) for k in ("z_min_m", "z_scale_m", "samples", "spacing_m", "water_level_m", "sources", "schema_version")}, "json": _rel(terrain_json, self.repo_root)})
                info["terrain"] = _rel(terrain_json, self.repo_root)
                n += 1
            elif terrain_png.exists() != terrain_json.exists():
                self._warn(f"{tile}: terrain.png/terrain.json pair incomplete")
            kp = td / "kit_placements.bin"
            if kp.exists():
                count, kit_ids = self._scan_placements(kp)
                info["kit_placements"] = {"path": _rel(kp, self.repo_root), "count": count, "kit_ids": sorted(kit_ids)}
                missing = [k for k in kit_ids if self.kit_catalog and k not in self.kit_catalog]
                if missing:
                    self._warn(f"{tile}: {len(missing)} kit_ids in placements missing from kit catalog (first: {missing[:5]})")
            pp = td / "props.parquet"
            if pp.exists():
                out = td / "props.json"
                cnt, tile_unmapped = _parquet_to_json(
                    pp, out, PROPS_COLUMNS, tile_origin=(t.x0, t.y0),
                    prop_assets=prop_assets, asset_paths=asset_paths)
                for k, v in tile_unmapped.items():
                    unmapped[k] = unmapped.get(k, 0) + v
                info["props"] = {"path": _rel(out, self.repo_root), "count": cnt}
            bp = td / "buildings.parquet"
            if bp.exists():
                info["buildings"] = {"path": _rel(bp, self.repo_root), "count": _parquet_rows(bp)}
        if unmapped:
            # Two different things used to be one number. A kind another stage builds -- a curb ramp
            # is cut into the pavement mesh -- is a division of labour, and a kind with no asset
            # anywhere is a gap. Counting them together meant the gap figure moved when the pavement
            # stage took work over, which is the opposite of what a gap figure is for. They are split
            # here; both are reported, and neither is a failure.
            gaps = {k: v for k, v in unmapped.items() if not _built_elsewhere_key(k)}
            elsewhere: dict[str, int] = {}
            for k, v in unmapped.items():
                if _built_elsewhere_key(k):
                    elsewhere[k.split(":", 1)[1]] = elsewhere.get(k.split(":", 1)[1], 0) + v
            self.prop_kinds_without_an_asset = dict(sorted(gaps.items(), key=lambda kv: -kv[1]))
            self.prop_kinds_built_elsewhere = dict(sorted(elsewhere.items(), key=lambda kv: -kv[1]))
            log.info("props: %d rows in %d kinds have no exported asset (%s); %d rows in %d kinds "
                     "are built by another stage (%s)",
                     sum(gaps.values()), len(gaps),
                     ", ".join(f"{k}={v}" for k, v in list(self.prop_kinds_without_an_asset.items())[:6]),
                     sum(elsewhere.values()), len(elsewhere),
                     ", ".join(f"{k}={v}" for k, v in self.prop_kinds_built_elsewhere.items()))
        # per-tile signs / lanes from the borough-wide road tables
        self._export_signs()
        if self.with_lanes:
            self._export_lanes()
        return n

    def _read_tile_index(self) -> dict[str, dict[str, Any]]:
        p = self.processed / "tiles" / "index.parquet"
        if not p.exists():
            return {}
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self._warn("pyarrow not available: tile index not embedded")
            return {}
        tbl = pq.read_table(p)
        rows = tbl.to_pylist()
        return {r["tile"]: {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in r.items() if k != "tile"} for r in rows}

    def _scan_placements(self, path: Path) -> tuple[int, set[int]]:
        size = path.stat().st_size
        if size % KIT_PLACEMENT_STRUCT.size:
            self._warn(f"{path}: size {size} is not a multiple of {KIT_PLACEMENT_STRUCT.size}")
        kit_ids: set[int] = set()
        count = 0
        with open(path, "rb") as f:
            while rec := f.read(KIT_PLACEMENT_STRUCT.size):
                if len(rec) < KIT_PLACEMENT_STRUCT.size:
                    break
                kit_ids.add(KIT_PLACEMENT_STRUCT.unpack(rec)[0])
                count += 1
        return count, kit_ids

    def _export_signs(self) -> None:
        p = self.processed / "roads" / "signs.parquet"
        if not p.exists():
            return
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self._warn("pyarrow not available: signs not exported")
            return
        cols = [c for c in SIGN_COLUMNS if c in pq.read_schema(p).names]
        tbl = pq.read_table(p, columns=cols)
        per_tile: dict[str, list[dict[str, Any]]] = {}
        for r in tbl.to_pylist():
            if r.get("x") is None or r.get("y") is None:
                continue
            t = tile_of(float(r["x"]), float(r["y"]))
            r["x"], r["y"] = float(r["x"]) - t.x0, float(r["y"]) - t.y0  # tile-local
            per_tile.setdefault(t.name, []).append(_jsonable(r))
        for tile, rows in per_tile.items():
            if self.tiles_filter is not None and tile not in self.tiles_filter:
                continue
            td = self._tile_dir(tile)
            if not td.is_dir():
                continue
            out = td / "signs.json"
            out.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "tile": tile, "origin_local": True, "count": len(rows), "signs": rows}, separators=(",", ":")))
            self.tiles.setdefault(tile, {"assets": []})["signs"] = {"path": _rel(out, self.repo_root), "count": len(rows)}
        log.info("signs: %d tiles", len(per_tile))

    def _export_lanes(self) -> None:
        p = self.processed / "roads" / "lanes.parquet"
        if not p.exists():
            return
        try:
            import pyarrow.parquet as pq
            from shapely import wkb
        except ImportError:
            self._warn("pyarrow/shapely not available: lanes not exported")
            return
        tbl = pq.read_table(p, columns=[c for c in ("lane_id", "segment_id", "kind", "direction", "width_m", "speed_mps", "geometry") if c in pq.read_schema(p).names])
        per_tile: dict[str, list[dict[str, Any]]] = {}
        for r in tbl.to_pylist():
            g = r.pop("geometry", None)
            if g is None:
                continue
            line = wkb.loads(g)
            coords = [list(c) for c in line.coords]
            if not coords:
                continue
            t = tile_of(coords[0][0], coords[0][1])
            r["pts"] = [[round(c[0] - t.x0, 3), round(c[1] - t.y0, 3), round(c[2] if len(c) > 2 else 0.0, 3)] for c in coords]
            per_tile.setdefault(t.name, []).append(_jsonable(r))
        for tile, rows in per_tile.items():
            if self.tiles_filter is not None and tile not in self.tiles_filter:
                continue
            td = self._tile_dir(tile)
            if not td.is_dir():
                continue
            out = td / "lanes_debug.json"
            out.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "tile": tile, "origin_local": True, "count": len(rows), "lanes": rows}, separators=(",", ":")))
            self.tiles.setdefault(tile, {"assets": []})["lanes_debug"] = {"path": _rel(out, self.repo_root), "count": len(rows)}

    # ------------------------------------------------------------------ water
    def add_water(self) -> Path | None:
        hydro = self.processed / "water" / "hydrography.parquet"
        out = self.processed / "unreal_water.json"
        doc: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "generated_at": _now(), "water_level_m": 0.0, "bodies": [], "flow": None, "tiles": {}}
        tides = self.processed / "live" / "tides.json"
        if tides.exists():
            try:
                td = json.loads(tides.read_text())
                doc["flow"] = {k: td.get(k) for k in ("station", "current_speed_mps", "current_dir_deg", "water_level_m", "predicted_at")}
                if isinstance(td.get("water_level_m"), (int, float)):
                    doc["water_level_m"] = float(td["water_level_m"])
            except json.JSONDecodeError as e:
                self._warn(f"tides.json unreadable: {e}")
        if not hydro.exists():
            self._warn(f"no hydrography at {hydro}: unreal_water.json has no bodies")
            out.write_text(json.dumps(doc, indent=1))
            self._add("water:unreal_water", "water", out, f"{CONTENT_ROOT}/Runtime/unreal_water.json", "json_copy")
            return out
        try:
            import numpy as np
            import pyarrow.parquet as pq
            from PIL import Image, ImageDraw
            from shapely import wkb
            from shapely.geometry import box
            from shapely.ops import unary_union
        except ImportError as e:
            self._warn(f"water export needs pyarrow/shapely/PIL/numpy: {e}")
            out.write_text(json.dumps(doc, indent=1))
            self._add("water:unreal_water", "water", out, f"{CONTENT_ROOT}/Runtime/unreal_water.json", "json_copy")
            return out

        tbl = pq.read_table(hydro, columns=[c for c in ("water_id", "kind", "name", "tidal", "geometry") if c in pq.read_schema(hydro).names])
        bodies = []
        geoms = []
        for r in tbl.to_pylist():
            g = wkb.loads(r["geometry"]) if r.get("geometry") is not None else None
            if g is None or g.is_empty:
                continue
            if not g.is_valid:
                g = g.buffer(0)
            geoms.append((r, g))
            bodies.append({"water_id": int(r.get("water_id") or 0), "kind": str(r.get("kind") or ""), "name": str(r.get("name") or ""), "tidal": bool(r.get("tidal")), "area_m2": round(float(g.area), 1), "tiles": []})
        shoreline = self._load_lines(self.processed / "water" / "shoreline.parquet")
        structures = self._load_polys(self.processed / "water" / "structures.parquet")

        tiles_dir = self.processed / "tiles"
        tile_names = sorted(p.name for p in tiles_dir.iterdir() if p.is_dir() and _TILE_RE.match(p.name)) if tiles_dir.is_dir() else []
        if not tile_names:
            # no tile directories yet: derive tiles from the water extent so the ocean still gets masks
            xs = [g.bounds for _, g in geoms]
            if xs:
                from ..tiling import tiles_in_bbox
                xmin = min(b[0] for b in xs); ymin = min(b[1] for b in xs); xmax = max(b[2] for b in xs); ymax = max(b[3] for b in xs)
                tile_names = [t.name for t in tiles_in_bbox(xmin, ymin, xmax, ymax)]
        from shapely.strtree import STRtree
        tree = STRtree([g for _, g in geoms])
        struct_tree = STRtree(structures) if structures else None
        shore_tree = STRtree(shoreline) if shoreline else None
        px_per_m = (TERRAIN_SAMPLES - 1) / TILE_SIZE_M
        n_masks = 0
        if self.tiles_filter is not None:
            # Rasterising a 501x501 mask for every tile that touches water is 1,760 PNGs; on a subset
            # run those are 1,760 files nothing will import and, on a machine with a couple of
            # gigabytes free, the run itself does not fit.
            tile_names = [t for t in tile_names if t in self.tiles_filter]
        for tile in tile_names:
            t = Tile.parse(tile)
            tb = box(*t.bounds)
            idx = tree.query(tb)
            hits = [(geoms[i][0], geoms[i][1]) for i in idx if geoms[i][1].intersects(tb)]
            if not hits:
                continue
            clipped = [(r, g.intersection(tb)) for r, g in hits]
            clipped = [(r, g) for r, g in clipped if not g.is_empty]
            if not clipped:
                continue
            union = unary_union([g for _, g in clipped])
            frac = float(union.area) / (TILE_SIZE_M * TILE_SIZE_M)
            # raster mask: row 0 = north edge (matches terrain.png), 1 texel = 2 m, inclusive edges
            img = Image.new("L", (TERRAIN_SAMPLES, TERRAIN_SAMPLES), 0)
            draw = ImageDraw.Draw(img)
            for _, g in clipped:
                for poly in getattr(g, "geoms", [g]):
                    if poly.geom_type != "Polygon" or poly.is_empty:
                        continue
                    ext = [((x - t.x0) * px_per_m, (TERRAIN_SAMPLES - 1) - (y - t.y0) * px_per_m) for x, y in poly.exterior.coords]
                    draw.polygon(ext, fill=255)
                    for ring in poly.interiors:
                        draw.polygon([((x - t.x0) * px_per_m, (TERRAIN_SAMPLES - 1) - (y - t.y0) * px_per_m) for x, y in ring.coords], fill=0)
            td = self._tile_dir(tile)
            td.mkdir(parents=True, exist_ok=True)
            mask_path = td / "water_mask.png"
            img.save(mask_path, optimize=True)
            n_masks += 1
            kinds: dict[str, float] = {}
            for r, g in clipped:
                kinds[str(r.get("kind") or "")] = kinds.get(str(r.get("kind") or ""), 0.0) + float(g.area)
            dominant = max(kinds.items(), key=lambda kv: kv[1])[0] if kinds else ""
            body_ids = sorted({int(r.get("water_id") or 0) for r, _ in clipped})
            for b in bodies:
                if b["water_id"] in body_ids:
                    b["tiles"].append(tile)
            shore_len = 0.0
            if shore_tree is not None:
                for i in shore_tree.query(tb):
                    shore_len += float(shoreline[i].intersection(tb).length)
            n_struct = 0
            if struct_tree is not None:
                n_struct = sum(1 for i in struct_tree.query(tb) if structures[i].intersects(tb))
            doc["tiles"][tile] = {
                "water_fraction": round(frac, 5), "mask_png": _rel(mask_path, self.repo_root), "bodies": body_ids,
                "dominant_kind": dominant, "tidal": any(bool(r.get("tidal")) for r, _ in clipped),
                "shoreline_m": round(shore_len, 1), "structures": n_struct,
                "mean_mask": round(float(np.asarray(img, dtype=np.float32).mean() / 255.0), 5),
            }
            self._add(f"water_mask:{tile}", "water_mask", mask_path, f"{CONTENT_ROOT}/Tiles/{safe_asset_name(tile)}/T_WaterMask", "texture_mask", tile=tile)
            self.tiles.setdefault(tile, {"assets": []})["water"] = doc["tiles"][tile]
        doc["bodies"] = bodies
        out.write_text(json.dumps(doc, indent=1))
        self._add("water:unreal_water", "water", out, f"{CONTENT_ROOT}/Runtime/unreal_water.json", "json_copy")
        log.info("water: %d bodies, %d tile masks", len(bodies), n_masks)
        return out

    def _load_polys(self, p: Path) -> list[Any]:
        if not p.exists():
            return []
        import pyarrow.parquet as pq
        from shapely import wkb
        out = []
        for g in pq.read_table(p, columns=["geometry"]).column("geometry").to_pylist():
            if g is not None:
                s = wkb.loads(g)
                if not s.is_empty:
                    out.append(s if s.is_valid else s.buffer(0))
        return out

    def _load_lines(self, p: Path) -> list[Any]:
        return self._load_polys(p)

    # ------------------------------------------------------------------ runtime + live + misc
    def add_audio(self) -> int:
        """The radio stations, the sound effects and the index that names them.

        ``UNYCRadioSubsystem`` turns a track's ``file`` field into a content path by the rule its own
        source states -- ``"jazz/fluffy_ruffles_rag.ogg"`` becomes
        ``/Game/NYCSim/Audio/Radio/jazz/fluffy_ruffles_rag`` -- and ``UNYCGameplaySettings`` names
        ``/Game/NYCSim/Audio/Radio`` and ``/Game/NYCSim/Audio/SFX`` as the two roots. None of the 74
        files had a manifest rule, so none of them was ever listed, imported or cooked: no radio, no
        siren, no horn, no engine sample. The paths below are the engine's, derived from those two
        settings and that rule rather than chosen here.
        """
        audio = self.repo_root / "assets" / "audio"
        if not audio.is_dir():
            return 0
        n = 0
        radio = audio / "radio"
        for p in sorted(radio.rglob("*.ogg")):
            rel = p.relative_to(radio)
            if len(rel.parts) != 2:
                self._warn(f"radio track {rel.as_posix()} is not <genre>/<file>.ogg; skipped")
                continue
            genre, stem = rel.parts[0], p.stem
            self._add(f"audio:radio:{genre}/{stem}", "sound", p,
                      f"{CONTENT_ROOT}/Audio/Radio/{genre}/{safe_asset_name(stem)}",
                      "sound_wave_stream",
                      extra=self._licence_of(p))
            n += 1
        sfx = audio / "sfx"
        for p in sorted(sfx.glob("*.ogg")):
            self._add(f"audio:sfx:{p.stem}", "sound", p,
                      f"{CONTENT_ROOT}/Audio/SFX/{safe_asset_name(p.stem)}", "sound_wave",
                      extra=self._licence_of(p))
            n += 1
        stations = radio / "stations.json"
        if stations.is_file():
            # The index is rewritten with the content path this manifest actually assigned to each
            # track, rather than left for the engine to derive. UNYCRadioSubsystem derives
            # "<root>/<genre>/<stem>" from the file name; safe_asset_name puts an underscore in front
            # of a leading digit, because a UE asset name may not start with one. So a track called
            # 01_gunther_freischutz.ogg imports as _01_gunther_freischutz and the radio looks for
            # 01_gunther_freischutz and finds silence. Two derivations of the same string in two
            # languages will drift; one of them stating the answer will not.
            resolved = self._stations_with_paths(stations, radio)
            if resolved is not None:
                self._add("audio:stations", "audio_index", resolved,
                          "Content/NYCSim/Audio/stations.json", "json_copy",
                          extra={"note": "rewritten from assets/audio/radio/stations.json with the "
                                         "content path this manifest assigned to each track",
                                 "source": _rel(stations, self.repo_root)})
                n += 1
        elif n:
            self._warn("assets/audio/radio/stations.json is missing; the radio has tracks but no "
                       "station list and UNYCRadioSubsystem will find no stations")
        log.info("audio: %d", n)
        return n

    def _stations_with_paths(self, stations: Path, radio: Path) -> Path | None:
        """``data/processed/audio/stations.json``: the fetcher's index plus a ``sound_path`` per track."""
        try:
            doc = json.loads(stations.read_text())
        except Exception as exc:  # noqa: BLE001
            self._warn(f"stations.json unreadable: {exc}")
            return None
        by_src = {e["src"]: e["dst"] for e in self.entries if e["kind"] == "sound"}
        resolved, unresolved = 0, []
        for station in doc.get("stations", []):
            for track in station.get("tracks", []):
                rel = str(track.get("file", ""))
                src = _rel(radio / rel, self.repo_root)
                dst = by_src.get(src)
                if dst is None:
                    unresolved.append(rel)
                    continue
                track["sound_path"] = f"{dst}.{dst.rsplit('/', 1)[-1]}"
                resolved += 1
        if unresolved:
            self._warn(f"{len(unresolved)} radio track(s) named in stations.json have no imported "
                       f"asset: {unresolved[:5]}")
        doc["sound_path_note"] = ("sound_path is the exact content path this manifest assigned; "
                                  "prefer it over deriving one from `file`")
        doc["resolved_tracks"] = resolved
        out = self.processed / "audio" / "stations.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        return out

    @staticmethod
    def _licence_of(p: Path) -> dict[str, Any]:
        """The per-file licence record the fetcher wrote beside the track, carried into the manifest.

        Every one of these files was fetched with a machine-checked licence and the provenance is the
        reason they may ship at all; a manifest entry that drops it is a delivery with no receipt.
        """
        rec = p.with_suffix(p.suffix + ".license.json")
        if not rec.is_file():
            return {}
        try:
            doc = json.loads(rec.read_text())
        except Exception:
            return {}
        return {"licence": doc.get("licence") or doc.get("license"),
                "licence_url": doc.get("licence_url") or doc.get("license_url"),
                "source_url": doc.get("source_url"),
                "licence_record": _rel(rec, REPO_ROOT)}

    def add_runtime(self) -> int:
        n = 0
        crs = self.processed / "crs.json"
        if crs.exists():
            self._add("crs", "crs", crs, f"{CONTENT_ROOT}/Runtime/crs.json", "json_copy")
            n += 1
        else:
            self._warn("crs.json missing")
        rt = self.processed / "runtime"
        if rt.is_dir():
            for p in sorted(rt.glob("*.nycb")):
                hdr = _nycb_header(p)
                if hdr is None:
                    self._warn(f"{p}: not a valid NYCB container")
                    continue
                self._add(f"runtime:{p.name}", "runtime_nycb", p, f"{CONTENT_ROOT}/Runtime/{p.name}", "raw_copy", extra={"nycb": hdr})
                n += 1
        live = self.processed / "live"
        if live.is_dir():
            for p in sorted(live.glob("*.json")):
                self._add(f"live:{p.name}", "live_json", p, f"{CONTENT_ROOT}/Live/{p.name}", "json_copy")
                n += 1
        # Generated here rather than assumed: this file has been referenced since Stage 12b and
        # never produced, which is why build_levels.py had nothing to place landmarks from and
        # 927 MB of models imported into a world that never spawned one of them.
        try:
            from .landmarks_index import write_index
            write_index(self.blender_out, self.processed)
        except Exception as exc:  # noqa: BLE001
            self._warn(f"landmarks index could not be written: {exc}")
        lm = self.processed / "landmarks" / "landmarks.json"
        if lm.exists():
            self._add("landmarks:index", "landmarks_index", lm, f"{CONTENT_ROOT}/Runtime/landmarks.json", "json_copy")
            n += 1
        # kit_catalog.json is not copied here: resolve_catalogs writes it from this run's own kit
        # entries, after the glbs are known, and adds it itself. Copying a stale one from a previous
        # run would both duplicate the id and ship content paths that no longer exist.
        for name in ("props_catalog.json", "facade_classes.json"):
            for base in (self.processed, self.processed / "facade", self.processed / "furniture",
                         self.blender_out, self.blender_out / "kit", self.blender_out / "props"):
                p = base / name
                if p.exists():
                    self._add(f"catalog:{name}", "catalog", p, f"{CONTENT_ROOT}/Runtime/{name}", "json_copy")
                    n += 1
                    break
        fonts = self.repo_root / "unreal" / "assets" / "fonts" / "Overpass"
        if fonts.is_dir():
            # One UFont called F_Overpass with the three weights as typefaces, because that is the
            # asset the engine names: UNYCGameplaySettings::HudFont is
            # /Game/NYCSim/Fonts/F_Overpass.F_Overpass. Left to safe_asset_name, "overpass-bold"
            # became "overpass_mbold" (the '-' -> 'm' rule that keeps tile names unambiguous) and the
            # font landed at F_overpassmbold, so every piece of HUD text would have fallen back to
            # the engine default with nothing to notice.
            faces = {"regular": "Regular", "semibold": "SemiBold", "bold": "Bold"}
            sources = []
            for p in sorted(fonts.glob("*.otf")):
                weight = p.stem.split("-")[-1].lower()
                sources.append({"file": _rel(p, self.repo_root), "typeface": faces.get(weight, weight.title()),
                                "bytes": p.stat().st_size,
                                "sha256": _sha256(p) if self.hash_files else ""})
            if sources:
                primary = fonts / "overpass-regular.otf"
                if not primary.exists():
                    primary = Path(self.repo_root / sources[0]["file"])
                self._add("font:F_Overpass", "font", primary, f"{CONTENT_ROOT}/Fonts/F_Overpass", "font",
                          extra={"license": "SIL OFL 1.1 / LGPL 2.1",
                                 "license_record": _rel(fonts / "LICENSE_RECORD.json", self.repo_root),
                                 "typefaces": sources,
                                 "note": ("one UFont with three typefaces; the engine names "
                                          "F_Overpass and nothing else")})
                n += 1
        return n

    # ------------------------------------------------------------------ order + write
    def import_order(self) -> list[str]:
        rank = {"crs": 0, "font": 1, "catalog": 2, "runtime_nycb": 3, "live_json": 3, "landmarks_index": 3,
                "audio_index": 3, "water": 4, "sound": 5,
                "kit": 10, "prop": 11, "tree": 11, "landmark": 12, "vehicle": 13, "character": 13,
                "skyline": 33,
                "terrain": 20, "water_mask": 21, "shells": 30, "roofs": 31, "tile_mesh": 32}
        return [e["id"] for e in sorted(self.entries, key=lambda e: (rank.get(e["kind"], 99), e.get("tile") or "", e["id"]))]

    def build(self) -> dict[str, Any]:
        self.load_catalogs()
        self.add_runtime()
        self.add_audio()
        self.add_glbs()
        self.resolve_catalogs()
        self.add_tiles()
        self.add_water()
        by_kind: dict[str, int] = {}
        for e in self.entries:
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
        return {
            "schema_version": SCHEMA_VERSION,
            "schema": MANIFEST_SCHEMA,
            "generated_at": _now(),
            "git_commit": git_commit(),
            "repo_root": str(self.repo_root),
            "content_root": CONTENT_ROOT,
            "tile_size_m": TILE_SIZE_M,
            "terrain_samples": TERRAIN_SAMPLES,
            "import_settings": IMPORT_SETTINGS,
            "counts": {"entries": len(self.entries), "tiles": len(self.tiles), "by_kind": by_kind,
                       **_sidecar_counts(self.entries)},
            "kit_catalog_entries": len(self.kit_catalog),
            "props_catalog_entries": len(self.props_catalog),
            "prop_kinds_without_an_asset": self.prop_kinds_without_an_asset,
            "prop_kinds_built_elsewhere": self.prop_kinds_built_elsewhere,
            "tiles": self.tiles,
            "entries": self.entries,
            "import_order": self.import_order(),
            "warnings": self.warnings,
        }


# ------------------------------------------------------------------------------------------------- module helpers
def _sidecar_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    """How many image files travel with the glbs, and how many distinct ones they are.

    The gap between the two is the point of externalising them: 2,847 references to 486 files.
    """
    refs = 0
    distinct: set[str] = set()
    for e in entries:
        for rel in e.get("sidecars") or ():
            refs += 1
            distinct.add(rel)
    return {"sidecar_references": refs, "sidecar_files": len(distinct)}


_TILE_RE = re.compile(r"^t_-?\d+_-?\d+$")
PROPS_COLUMNS = ["prop_id", "kind", "x", "y", "z", "heading", "variant", "text", "source", "dataset_id", "species", "dbh_cm", "height_m"]
SIGN_COLUMNS = ["sign_id", "node_id", "segment_id", "x", "y", "z", "facing_heading", "mutcd_code", "text", "arrow", "sign_w_m", "sign_h_m", "support", "source"]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _kit_id_from(extras: dict[str, Any], stem: str) -> int:
    v = extras.get("kit_id", extras.get("id"))
    try:
        return int(v)
    except (TypeError, ValueError):
        m = re.search(r"(\d+)", stem)
        if m:
            return int(m.group(1))
        return int(hashlib.sha256(stem.encode()).hexdigest()[:8], 16)


def _jsonable(r: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in r.items():
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                v = None
            else:
                v = round(v, 4)
        elif isinstance(v, bytes):
            continue
        out[k] = v
    return out


def _parquet_rows(p: Path) -> int:
    try:
        import pyarrow.parquet as pq
        return int(pq.read_metadata(p).num_rows)
    except ImportError:
        return -1


def _built_elsewhere_key(key: str) -> bool:
    """Is this ``unresolved`` key a kind another stage builds rather than a missing asset?"""
    from ..furniture import assets as _assets
    return _assets.is_built_elsewhere(key)


def _parquet_to_json(src: Path, dst: Path, columns: list[str], *,
                     tile_origin: tuple[float, float] | None = None,
                     prop_assets: Any = None,
                     asset_paths: dict[str, str] | None = None) -> Any:
    """Re-export a parquet as the JSON the editor's Python can read (UE 5.4 has no pyarrow).

    With ``prop_assets`` this also resolves every row to the asset it is: ``props.parquet`` stores
    ``kind`` as an int16 code and ``build_levels.py`` cannot turn that into a mesh -- the vocabulary
    it needs (a tree's species and height, ``utility_pole`` being exported as ``sign_post``) lives in
    the pipeline. The paths go out as a deduplicated ``assets`` list with a per-row index, because
    writing the full path on each of the city's 2.6 M prop rows would be a hundred megabytes of the
    same forty strings.
    """
    import pyarrow.parquet as pq
    names = pq.read_schema(src).names
    cols = [c for c in columns if c in names]
    tbl = pq.read_table(src, columns=cols)
    rows = []
    assets: list[str] = []
    asset_index: dict[str, int] = {}
    unmapped: dict[str, int] = {}
    for r in tbl.to_pylist():
        if tile_origin is not None and r.get("x") is not None and r.get("y") is not None:
            r["x"] = float(r["x"]) - tile_origin[0]
            r["y"] = float(r["y"]) - tile_origin[1]
        if prop_assets is not None and r.get("kind") is not None:
            entry, why = prop_assets.resolve(r["kind"], variant=r.get("variant"),
                                             species=r.get("species") or "", height_m=r.get("height_m"))
            path = (asset_paths or {}).get((entry or {}).get("glb", ""))
            if path is None:
                key = why if entry is None else f"{why}:no imported mesh for {entry.get('id')}"
                unmapped[key] = unmapped.get(key, 0) + 1
            else:
                i = asset_index.get(path)
                if i is None:
                    i = asset_index[path] = len(assets)
                    assets.append(path)
                r["a"] = i
        rows.append(_jsonable(r))
    doc = {"schema_version": SCHEMA_VERSION, "source": src.name, "origin_local": tile_origin is not None,
           "columns": cols, "count": len(rows), "rows": rows}
    if prop_assets is not None:
        doc["assets"] = assets
        doc["asset_key"] = "a"
        doc["unresolved"] = dict(sorted(unmapped.items(), key=lambda kv: -kv[1]))
    dst.write_text(json.dumps(doc, separators=(",", ":")))
    if prop_assets is None:
        return len(rows)
    return len(rows), unmapped


#: DATA_CONTRACTS §15 header, laid out as a C++17 compiler lays it out: 4 bytes of padding after
#: ``section_count`` so ``index_offset`` is 8-aligned, giving ``sizeof == 24``. This reader used to
#: unpack it as ``"<IIQ"`` -- 20 bytes, no padding -- so it took ``index_offset`` from the padding and
#: the four bytes after it, seeked to nonsense, and declared every container invalid. All seven
#: runtime files were reported "not a valid NYCB container" and dropped from the manifest: the road
#: graph the traffic simulation drives on, the signals, the POIs the GPS searches, the tile index,
#: the transit, the density. 130 MB of the world, silently not shipped.
#:
#: ``pipeline/nycsim_pipeline/runtime/nycb.py`` is the writer and asserts ``itemsize == 24``; this is
#: the same layout, and ``tests/test_unreal_pipeline_paths.py`` now reads a real container through it.
_NYCB_HEADER = struct.Struct("<4sII4xQ")
assert _NYCB_HEADER.size == 24, _NYCB_HEADER.size


def _nycb_header(p: Path) -> dict[str, Any] | None:
    """DATA_CONTRACTS §15: header {magic[4]='NYCB'; u32 version; u32 section_count; u64 index_offset}; index entries
    {char name[16]; u64 offset; u64 size; u32 element_size; u32 element_count}."""
    try:
        with open(p, "rb") as f:
            head = f.read(_NYCB_HEADER.size)
            if len(head) < _NYCB_HEADER.size or head[:4] != b"NYCB":
                return None
            magic, version, section_count, index_offset = _NYCB_HEADER.unpack(head)
            f.seek(index_offset)
            sections = []
            entry = struct.Struct("<16sQQII")
            for _ in range(section_count):
                raw = f.read(entry.size)
                if len(raw) < entry.size:
                    return None
                name, off, size, esz, ecount = entry.unpack(raw)
                sections.append({"name": name.split(b"\0", 1)[0].decode("ascii", "replace"), "offset": off, "size": size, "element_size": esz, "element_count": ecount})
        return {"version": version, "sections": sections}
    except (OSError, struct.error):
        return None


def write_manifest(doc: dict[str, Any], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=False))
    os.replace(tmp, out)
    return out


def generate(processed: Path = PROCESSED, blender_out: Path = BLENDER_OUT, out: Path | None = None, *, repo_root: Path = REPO_ROOT, hash_files: bool = True, with_lanes: bool = False, record: bool = True, tiles: set[str] | None = None) -> tuple[Path, dict[str, Any]]:
    out = out or (Path(processed) / "unreal_manifest.json")
    b = ManifestBuilder(Path(processed), Path(blender_out), Path(repo_root), hash_files=hash_files, with_lanes=with_lanes, tiles=tiles)
    doc = b.build()
    write_manifest(doc, out)
    if record:
        try:
            record_processed("unreal_manifest", out, stage="unreal", sources=["blender_out", "tiles", "water", "runtime"], rows=len(doc["entries"]), schema=MANIFEST_SCHEMA)
        except Exception as e:  # noqa: BLE001 — the manifest itself is written; recording is bookkeeping
            log.warning("record_processed failed: %s", e)
    return out, doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processed", type=Path, default=PROCESSED)
    ap.add_argument("--blender-out", type=Path, default=BLENDER_OUT)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--with-lanes", action="store_true", help="also export per-tile lanes_debug.json")
    ap.add_argument("--no-hash", action="store_true", help="skip SHA-256 of every asset (faster)")
    ap.add_argument("--no-record", action="store_true", help="do not write data/manifest/processed.json")
    ap.add_argument("--tiles", default="", help="comma separated tile names; only these are listed "
                                                "and only their per-tile files are written")
    ap.add_argument("--tile-list", type=Path, default=None, help="file with one tile name per line")
    a = ap.parse_args(argv)
    tiles: set[str] | None = None
    if a.tile_list:
        tiles = {t.strip() for t in a.tile_list.read_text().split("\n") if t.strip()}
    elif a.tiles:
        tiles = {t.strip() for t in a.tiles.split(",") if t.strip()}
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out, doc = generate(a.processed, a.blender_out, a.out, hash_files=not a.no_hash, with_lanes=a.with_lanes, record=not a.no_record, tiles=tiles)
    print(json.dumps({"manifest": str(out), "counts": doc["counts"], "warnings": len(doc["warnings"])}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
