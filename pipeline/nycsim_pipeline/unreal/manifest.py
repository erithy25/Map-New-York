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
    "roof_nanite": {"nanite": True, "lods_from_suffix": False, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": False, "material_master": "M_NYC_Master", "mobility": "static"},
    "kit_nanite_lod": {"nanite": True, "lods_from_suffix": True, "collision": "simple_box", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Master", "mobility": "static", "instanced": True},
    "landmark_nanite": {"nanite": True, "lods_from_suffix": True, "collision": "complex_as_simple", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Master", "mobility": "static"},
    "prop_lod": {"nanite": False, "lods_from_suffix": True, "collision": "simple_box", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Master", "mobility": "static", "instanced": True},
    "tree_lod": {"nanite": False, "lods_from_suffix": True, "collision": "simple_capsule", "generate_lightmap_uvs": False, "combine_meshes": True, "material_master": "M_NYC_Foliage", "mobility": "static", "instanced": True},
    "vehicle_skeletal": {"skeletal": True, "nanite": False, "import_animations": False, "material_master": "M_NYC_Vehicle", "physics_asset": True},
    "character_skeletal": {"skeletal": True, "nanite": False, "import_animations": True, "import_morph_targets": True, "material_master": "M_NYC_Character", "physics_asset": True},
    "terrain_heightmap": {"landscape": True, "samples": TERRAIN_SAMPLES, "spacing_m": 2.0, "component_size_quads": 125, "sections_per_component": 1, "components_per_tile": 4, "notes": "501 samples = 4 components x 125 quads + 1; imported by UNYCTerrainImporter"},
    "texture_mask": {"texture": True, "srgb": False, "compression": "Grayscale", "mip_gen": "NoMipmaps", "address": "Clamp", "notes": "8-bit water/shoreline mask, 1 texel = 2 m"},
    "raw_copy": {"copy": True, "notes": "copied verbatim under Content/NYCSim/Runtime (staged as UFS)"},
    "json_copy": {"copy": True, "notes": "small JSON copied verbatim"},
    "font": {"font": True, "hinting": "Default", "loading_policy": "LazyLoad", "notes": "OTF -> UFont (offline cache 64/128 px) for UCanvasRenderTarget2D sign text"},
}

# blender_out subdirectory -> (import settings id, content path template). {stem} = glb file stem, {tile} = tile name.
GLB_RULES: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/tile_buildings\.glb$"), "shell_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_Shells", "shells"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/roofs\.glb$"), "roof_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_Roofs", "roofs"),
    (re.compile(r"^tiles/(?P<tile>t_-?\d+_-?\d+)/(?P<stem>[^/]+)\.glb$"), "shell_nanite", f"{CONTENT_ROOT}/Tiles/{{tile}}/SM_{{stem}}", "tile_mesh"),
    (re.compile(r"^kit/(?P<stem>[^/]+)\.glb$"), "kit_nanite_lod", f"{CONTENT_ROOT}/Kit/{{category}}/SM_{{stem}}", "kit"),
    (re.compile(r"^kit/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "kit_nanite_lod", f"{CONTENT_ROOT}/Kit/{{category}}/SM_{{stem}}", "kit"),
    (re.compile(r"^landmarks/(?P<stem>[^/]+)\.glb$"), "landmark_nanite", f"{CONTENT_ROOT}/Landmarks/SM_{{stem}}", "landmark"),
    (re.compile(r"^landmarks/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "landmark_nanite", f"{CONTENT_ROOT}/Landmarks/{{category}}/SM_{{stem}}", "landmark"),
    (re.compile(r"^props/trees?/(?P<stem>[^/]+)\.glb$"), "tree_lod", f"{CONTENT_ROOT}/Trees/SM_{{stem}}", "tree"),
    (re.compile(r"^props/(?P<stem>[^/]+)\.glb$"), "prop_lod", f"{CONTENT_ROOT}/Props/{{category}}/SM_{{stem}}", "prop"),
    (re.compile(r"^props/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "prop_lod", f"{CONTENT_ROOT}/Props/{{category}}/SM_{{stem}}", "prop"),
    (re.compile(r"^vehicles/(?P<stem>[^/]+)\.glb$"), "vehicle_skeletal", f"{CONTENT_ROOT}/Vehicles/{{stem}}/SK_{{stem}}", "vehicle"),
    (re.compile(r"^vehicles/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "vehicle_skeletal", f"{CONTENT_ROOT}/Vehicles/{{category}}/SK_{{stem}}", "vehicle"),
    (re.compile(r"^character/(?P<stem>[^/]+)\.glb$"), "character_skeletal", f"{CONTENT_ROOT}/Character/{{stem}}/SK_{{stem}}", "character"),
    (re.compile(r"^character/(?P<category>[^/]+)/(?P<stem>[^/]+)\.glb$"), "character_skeletal", f"{CONTENT_ROOT}/Character/{{category}}/SK_{{stem}}", "character"),
]

_ASSET_NAME_RE = re.compile(r"[^A-Za-z0-9_]")


def safe_asset_name(s: str) -> str:
    """UE asset names: letters, digits, underscore; must not start with a digit."""
    s = _ASSET_NAME_RE.sub("_", s.replace("-", "m"))  # tile names carry '-' -> 'm' keeps t_-3_7 -> t_m3_7 unambiguous
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def content_path(template: str, **kw: str) -> str:
    kw = {k: (v if k == "tile" else safe_asset_name(v)) for k, v in kw.items()}
    kw.setdefault("category", "Misc")
    if "tile" in kw:
        kw["tile"] = safe_asset_name(kw["tile"])
    return template.format(**kw)


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
    def __init__(self, processed: Path, blender_out: Path, repo_root: Path = REPO_ROOT, *, hash_files: bool = True, with_lanes: bool = False):
        self.processed = Path(processed)
        self.blender_out = Path(blender_out)
        self.repo_root = Path(repo_root)
        self.hash_files = hash_files
        self.with_lanes = with_lanes
        self.entries: list[dict[str, Any]] = []
        self.tiles: dict[str, dict[str, Any]] = {}
        self.warnings: list[str] = []
        self._ids: set[str] = set()
        self.kit_catalog: dict[int, dict[str, Any]] = {}
        self.props_catalog: dict[int, dict[str, Any]] = {}

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

    def _warn(self, msg: str) -> None:
        log.warning(msg)
        self.warnings.append(msg)

    def _tile_dir(self, tile: str) -> Path:
        return self.processed / "tiles" / tile

    # ------------------------------------------------------------------ catalogs
    def load_catalogs(self) -> None:
        self.kit_catalog = self._load_catalog(["kit_catalog.json", "kit/kit_catalog.json"], "kit/catalog", "kit_id")
        self.props_catalog = self._load_catalog(["props_catalog.json", "props/props_catalog.json"], "props/catalog", "kind")

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
            dst = content_path(tpl, tile=gd.get("tile", ""), stem=stem, category=category or "Misc") if "{tile}" not in tpl else content_path(tpl, tile=gd["tile"], stem=stem, category=category or "Misc")
            if kind == "tree":
                settings = "tree_lod"
            if kind in ("kit", "prop") and summary["has_lod1"] is False and settings.endswith("_lod"):
                pass  # LOD chain absent: importer builds one LOD; recorded below for the report
            extra = {
                "glb": {k: v for k, v in summary.items() if k != "extras"},
                "nycsim": extras,
                "category": category or "Misc",
            }
            id_ = f"glb:{rel}"
            deps: list[str] = []
            self._add(id_, kind, glb, dst, settings, deps=deps, tile=gd.get("tile"), extra=extra)
            n += 1
        log.info("glbs: %d", n)
        return n

    # ------------------------------------------------------------------ tiles
    def add_tiles(self) -> int:
        tiles_dir = self.processed / "tiles"
        if not tiles_dir.is_dir():
            self._warn(f"no tiles directory {tiles_dir}")
            return 0
        n = 0
        index_rows = self._read_tile_index()
        for td in sorted(p for p in tiles_dir.iterdir() if p.is_dir() and _TILE_RE.match(p.name)):
            tile = td.name
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
                cnt = _parquet_to_json(pp, out, PROPS_COLUMNS, tile_origin=(t.x0, t.y0))
                info["props"] = {"path": _rel(out, self.repo_root), "count": cnt}
            bp = td / "buildings.parquet"
            if bp.exists():
                info["buildings"] = {"path": _rel(bp, self.repo_root), "count": _parquet_rows(bp)}
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
        lm = self.processed / "landmarks" / "landmarks.json"
        if lm.exists():
            self._add("landmarks:index", "landmarks_index", lm, f"{CONTENT_ROOT}/Runtime/landmarks.json", "json_copy")
            n += 1
        for name in ("kit_catalog.json", "props_catalog.json", "facade_classes.json"):
            for base in (self.processed, self.blender_out, self.blender_out / "kit", self.blender_out / "props"):
                p = base / name
                if p.exists():
                    self._add(f"catalog:{name}", "catalog", p, f"{CONTENT_ROOT}/Runtime/{name}", "json_copy")
                    n += 1
                    break
        fonts = self.repo_root / "unreal" / "assets" / "fonts" / "Overpass"
        if fonts.is_dir():
            for p in sorted(fonts.glob("*.otf")):
                self._add(f"font:{p.stem}", "font", p, f"{CONTENT_ROOT}/Fonts/F_{safe_asset_name(p.stem)}", "font",
                          extra={"license": "SIL OFL 1.1 / LGPL 2.1", "license_record": _rel(fonts / "LICENSE_RECORD.json", self.repo_root)})
                n += 1
        return n

    # ------------------------------------------------------------------ order + write
    def import_order(self) -> list[str]:
        rank = {"crs": 0, "font": 1, "catalog": 2, "runtime_nycb": 3, "live_json": 3, "landmarks_index": 3, "water": 4,
                "kit": 10, "prop": 11, "tree": 11, "landmark": 12, "vehicle": 13, "character": 13,
                "terrain": 20, "water_mask": 21, "shells": 30, "roofs": 31, "tile_mesh": 32}
        return [e["id"] for e in sorted(self.entries, key=lambda e: (rank.get(e["kind"], 99), e.get("tile") or "", e["id"]))]

    def build(self) -> dict[str, Any]:
        self.load_catalogs()
        self.add_runtime()
        self.add_glbs()
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
            "counts": {"entries": len(self.entries), "tiles": len(self.tiles), "by_kind": by_kind},
            "kit_catalog_entries": len(self.kit_catalog),
            "props_catalog_entries": len(self.props_catalog),
            "tiles": self.tiles,
            "entries": self.entries,
            "import_order": self.import_order(),
            "warnings": self.warnings,
        }


# ------------------------------------------------------------------------------------------------- module helpers
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


def _parquet_to_json(src: Path, dst: Path, columns: list[str], *, tile_origin: tuple[float, float] | None = None) -> int:
    import pyarrow.parquet as pq
    names = pq.read_schema(src).names
    cols = [c for c in columns if c in names]
    tbl = pq.read_table(src, columns=cols)
    rows = []
    for r in tbl.to_pylist():
        if tile_origin is not None and r.get("x") is not None and r.get("y") is not None:
            r["x"] = float(r["x"]) - tile_origin[0]
            r["y"] = float(r["y"]) - tile_origin[1]
        rows.append(_jsonable(r))
    dst.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "source": src.name, "origin_local": tile_origin is not None, "columns": cols, "count": len(rows), "rows": rows}, separators=(",", ":")))
    return len(rows)


def _nycb_header(p: Path) -> dict[str, Any] | None:
    """DATA_CONTRACTS §15: header {magic[4]='NYCB'; u32 version; u32 section_count; u64 index_offset}; index entries
    {char name[16]; u64 offset; u64 size; u32 element_size; u32 element_count}."""
    try:
        with open(p, "rb") as f:
            head = f.read(20)
            if len(head) < 20 or head[:4] != b"NYCB":
                return None
            version, section_count, index_offset = struct.unpack("<IIQ", head[4:20])
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


def generate(processed: Path = PROCESSED, blender_out: Path = BLENDER_OUT, out: Path | None = None, *, repo_root: Path = REPO_ROOT, hash_files: bool = True, with_lanes: bool = False, record: bool = True) -> tuple[Path, dict[str, Any]]:
    out = out or (Path(processed) / "unreal_manifest.json")
    b = ManifestBuilder(Path(processed), Path(blender_out), Path(repo_root), hash_files=hash_files, with_lanes=with_lanes)
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
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out, doc = generate(a.processed, a.blender_out, a.out, hash_files=not a.no_hash, with_lanes=a.with_lanes, record=not a.no_record)
    print(json.dumps({"manifest": str(out), "counts": doc["counts"], "warnings": len(doc["warnings"])}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
