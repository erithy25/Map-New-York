"""Assemble a NYCSim verification scene in Blender around a world position.

The scene is built from the artefacts the other stages have already written, never from
invented geometry:

* terrain   -- ``data/processed/tiles/{tile}/terrain.png`` + ``terrain.json`` (16-bit,
               501x501 at 2 m, ``z = z_min_m + value * z_scale_m``) displaced onto a regular
               grid, with the water surface split off as its own material.
* buildings -- ``blender_out/tiles/{tile}/tile_buildings.glb``; the file carries LOD0/LOD1/LOD2
               as sibling objects (``_LOD1`` / ``_LOD2`` suffixes) so exactly one LOD per tile
               is kept and the others are dropped, otherwise every shell would be drawn twice.
* landmarks -- ``blender_out/landmarks/catalog/*.json``; each entry gives ``origin_tm``
               (the NYC_TM position of the model origin) and the model axes are already
               parallel to NYC_TM, so placement is a pure translation.
* props     -- ``data/processed/tiles/{tile}/props.parquet`` (DATA_CONTRACTS s8) instanced
               against ``blender_out/props/props_asset_catalog.json``.
* kit       -- ``data/processed/tiles/{tile}/kit_placements.bin`` (DATA_CONTRACTS s6)
               instanced against ``data/processed/facade/kit_catalog_map.json``.

Everything above a configurable triangle budget is dropped rather than drawn, and every drop
is recorded in the returned :class:`SceneReport` so a comparison sheet can state what was left
out instead of pretending the frame is complete.

Run standalone for a smoke test::

    python3 blender/verify/scene.py --lat 40.7526 --lon -73.9814 --radius 600 --json -
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

import nycsim_bpy as nb  # noqa: E402

LOG = logging.getLogger("nycsim.verify.scene")

PROCESSED = REPO_ROOT / "data" / "processed"
TILES_DATA = PROCESSED / "tiles"
BLENDER_OUT = REPO_ROOT / "blender_out"
TILES_GLB = BLENDER_OUT / "tiles"
LANDMARK_CATALOG = BLENDER_OUT / "landmarks" / "catalog"
PROPS_CATALOG_JSON = BLENDER_OUT / "props" / "props_asset_catalog.json"
KIT_MAP_JSON = PROCESSED / "facade" / "kit_catalog_map.json"
KIT_IDS_JSON = PROCESSED / "facade" / "kit_ids.json"
PROP_KINDS_JSON = PROCESSED / "furniture" / "props_catalog.json"

TILE_SIZE_M = 1000.0
TERRAIN_SAMPLES = 501
TERRAIN_SPACING_M = 2.0

_LOD_SUFFIX = re.compile(r"_LOD(\d+)$", re.IGNORECASE)

#: Prop ``kind`` name -> ``dataset_kind`` of the exported asset catalogue.  The two vocabularies
#: agree for most kinds; the entries here are the ones that do not spell the same.
PROP_KIND_ALIASES = {
    "waste_basket": "waste_basket",
    "street_lamp": "street_lamp",
    "bus_stop_sign": "road_sign",
    "rtpi_sign": "road_sign",
    "utility_pole": "sign_post",
    "billboard": None,          # no exported billboard prop asset
    "curb_ramp": None,          # modelled by the road stage, not a prop asset
    "artwork": None,
    "memorial": None,
    "drinking_fountain": None,
    "payphone": None,
    "vending_machine": None,
    "bike_shelter": "bus_shelter",
    "parks_comfort_station": None,
    "parks_recreation_center": None,
    "parks_building": None,
    "cooling_tower": None,
    "swimming_pool": None,
    "misc_structure": None,
    "subway_emergency_exit": "subway_vent_grate",
    "steam_vent": "steam_vent",
}

#: Street-tree species key used in the exported asset ids, keyed by the lower-cased Latin genus
#: or species found in ``props.parquet``.
TREE_SPECIES_KEYS = {
    "styphnolobium japonicum": "sophora",
    "sophora japonica": "sophora",
    "zelkova serrata": "zelkova",
    "gleditsia triacanthos": "honeylocust",
    "gleditsia triacanthos var. inermis": "honeylocust",
    "platanus x acerifolia": "planetree",
    "platanus acerifolia": "planetree",
    "pyrus calleryana": "callery_pear",
    "quercus palustris": "pin_oak",
    "acer platanoides": "norway_maple",
    "acer rubrum": "red_maple",
    "tilia cordata": "littleleaf_linden",
    "ginkgo biloba": "ginkgo",
}
#: Fallback when the census species has no modelled asset: the commonest NYC street tree.
TREE_FALLBACK_KEY = "honeylocust"


# --------------------------------------------------------------------------- terrain


def tile_name(tx: int, ty: int) -> str:
    return f"t_{tx}_{ty}"


def tiles_in_radius(cx: float, cy: float, radius_m: float) -> list[tuple[int, int]]:
    """Tile indices whose 1 km square intersects the disc of ``radius_m`` around (cx, cy)."""
    tx0 = math.floor((cx - radius_m) / TILE_SIZE_M)
    tx1 = math.floor((cx + radius_m) / TILE_SIZE_M)
    ty0 = math.floor((cy - radius_m) / TILE_SIZE_M)
    ty1 = math.floor((cy + radius_m) / TILE_SIZE_M)
    out: list[tuple[int, int]] = []
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            x0, y0 = tx * TILE_SIZE_M, ty * TILE_SIZE_M
            nx = min(max(cx, x0), x0 + TILE_SIZE_M)
            ny = min(max(cy, y0), y0 + TILE_SIZE_M)
            if math.hypot(nx - cx, ny - cy) <= radius_m:
                out.append((tx, ty))
    return out


class TerrainSampler:
    """Lazy reader for the per-tile heightmaps, with bilinear sampling in NYC_TM metres."""

    def __init__(self, root: Path = TILES_DATA) -> None:
        self.root = Path(root)
        self._cache: dict[tuple[int, int], tuple[np.ndarray, dict] | None] = {}
        self.missing: set[str] = set()

    def _load(self, tx: int, ty: int):
        key = (tx, ty)
        if key in self._cache:
            return self._cache[key]
        d = self.root / tile_name(tx, ty)
        png, js = d / "terrain.png", d / "terrain.json"
        if not (png.exists() and js.exists()):
            self.missing.add(tile_name(tx, ty))
            self._cache[key] = None
            return None
        try:
            from PIL import Image
            with Image.open(png) as im:
                arr = np.asarray(im).astype(np.float32)
            meta = json.loads(js.read_text())
        except Exception as exc:  # corrupt or half-written tile
            LOG.warning("terrain tile %s unreadable: %s", tile_name(tx, ty), exc)
            self.missing.add(tile_name(tx, ty))
            self._cache[key] = None
            return None
        if arr.ndim != 2 or arr.shape != (TERRAIN_SAMPLES, TERRAIN_SAMPLES):
            LOG.warning("terrain tile %s has shape %s, expected %dx%d",
                        tile_name(tx, ty), arr.shape, TERRAIN_SAMPLES, TERRAIN_SAMPLES)
            self.missing.add(tile_name(tx, ty))
            self._cache[key] = None
            return None
        z = float(meta.get("z_min_m", 0.0)) + arr * float(meta.get("z_scale_m", 0.0))
        # PNG row 0 is the north edge; flip so index 0 is the south edge (increasing y).
        z = np.flipud(z)
        self._cache[key] = (z, meta)
        return self._cache[key]

    def meta(self, tx: int, ty: int) -> dict | None:
        got = self._load(tx, ty)
        return None if got is None else got[1]

    def grid(self, xs: np.ndarray, ys: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Bilinear heights for meshgrid coordinates.

        Returns ``(z, water)`` where ``water`` is True for samples that sit on a tile's flattened
        water surface.  Samples on tiles with no heightmap come back as NaN so the caller can
        decide what to do with the hole.
        """
        z = np.full(xs.shape, np.nan, dtype=np.float64)
        water = np.zeros(xs.shape, dtype=bool)
        txs = np.floor(xs / TILE_SIZE_M).astype(int)
        tys = np.floor(ys / TILE_SIZE_M).astype(int)
        for tx, ty in {(int(a), int(b)) for a, b in zip(txs.ravel(), tys.ravel())}:
            got = self._load(tx, ty)
            sel = (txs == tx) & (tys == ty)
            if got is None:
                continue
            grid, meta = got
            u = (xs[sel] - tx * TILE_SIZE_M) / TERRAIN_SPACING_M
            v = (ys[sel] - ty * TILE_SIZE_M) / TERRAIN_SPACING_M
            u = np.clip(u, 0.0, TERRAIN_SAMPLES - 1.0001)
            v = np.clip(v, 0.0, TERRAIN_SAMPLES - 1.0001)
            i0, j0 = np.floor(v).astype(int), np.floor(u).astype(int)
            fu, fv = u - j0, v - i0
            i1, j1 = i0 + 1, j0 + 1
            g = grid
            zz = (g[i0, j0] * (1 - fu) * (1 - fv) + g[i0, j1] * fu * (1 - fv)
                  + g[i1, j0] * (1 - fu) * fv + g[i1, j1] * fu * fv)
            z[sel] = zz
            if meta.get("has_water"):
                wl = float(meta.get("water_level_m", 0.0))
                if not meta.get("has_land"):
                    water[sel] = True
                else:
                    water[sel] = zz <= wl + 0.05
        return z, water

    def z_at(self, x: float, y: float) -> float | None:
        z, _ = self.grid(np.array([[float(x)]]), np.array([[float(y)]]))
        v = float(z[0, 0])
        return None if math.isnan(v) else v


def build_terrain(sampler: TerrainSampler, cx: float, cy: float, radius_m: float, *,
                  max_side: int = 300, min_spacing_m: float = 3.0,
                  col: bpy.types.Collection | None = None) -> dict:
    """Displaced grid over the square of half-width ``radius_m`` centred on (cx, cy)."""
    side = 2.0 * radius_m
    spacing = max(min_spacing_m, side / max_side)
    n = int(round(side / spacing)) + 1
    n = max(2, min(n, max_side + 1))
    xs1 = np.linspace(cx - radius_m, cx + radius_m, n)
    ys1 = np.linspace(cy - radius_m, cy + radius_m, n)
    xs, ys = np.meshgrid(xs1, ys1)
    z, water = sampler.grid(xs, ys)
    holes = int(np.isnan(z).sum())
    if holes == z.size:
        LOG.warning("no terrain heightmap covers the scene; ground omitted")
        return {"built": False, "reason": "no terrain tiles on disk for this area",
                "samples": 0, "spacing_m": spacing, "holes": holes}
    fill = float(np.nanmedian(z))
    z = np.where(np.isnan(z), fill, z)

    verts = [(float(xs[i, j]), float(ys[i, j]), float(z[i, j])) for i in range(n) for j in range(n)]
    faces, mats = [], []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            faces.append((a, a + 1, a + n + 1, a + n))
            quad_water = water[i, j] and water[i, j + 1] and water[i + 1, j] and water[i + 1, j + 1]
            mats.append(1 if quad_water else 0)
    ground = nb.pbr_material("verify_ground", base_color=(0.26, 0.25, 0.23, 1.0), roughness=0.92)
    sea = nb.pbr_material("verify_water", base_color=(0.045, 0.075, 0.10, 1.0), roughness=0.06, metallic=0.0)
    ob = nb.mesh_object("verify_terrain", verts, faces, col=col, materials=(ground, sea), smooth=False)
    for poly, m in zip(ob.data.polygons, mats):
        poly.material_index = m
    return {"built": True, "samples": n, "spacing_m": round(spacing, 3),
            "triangles": 2 * (n - 1) * (n - 1), "holes": holes,
            "water_quads": int(sum(1 for m in mats if m == 1)),
            "z_min_m": round(float(z.min()), 2), "z_max_m": round(float(z.max()), 2)}


# --------------------------------------------------------------------------- glb import helpers


def _lod_of(name: str) -> int:
    m = _LOD_SUFFIX.search(name)
    return int(m.group(1)) if m else 0


def import_glb(path: Path) -> list[bpy.types.Object]:
    """Import a glb and return the objects it created (mesh objects and their empties)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [ob for ob in bpy.data.objects if ob not in before]


def _triangles(ob: bpy.types.Object) -> int:
    if ob.type != "MESH":
        return 0
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


@dataclass
class AssetTemplate:
    """One imported asset, reduced to (mesh datablock, local matrix) pairs ready to instance."""
    key: str
    parts: list[tuple[bpy.types.Mesh, Matrix]]
    triangles: int

    def instance(self, name: str, matrix: Matrix, col: bpy.types.Collection) -> list[bpy.types.Object]:
        out = []
        for k, (mesh, local) in enumerate(self.parts):
            ob = bpy.data.objects.new(f"{name}.{k}" if len(self.parts) > 1 else name, mesh)
            ob.matrix_world = matrix @ local
            col.objects.link(ob)
            out.append(ob)
        return out


class AssetLibrary:
    """Imports each glb once and hands out linked instances of its mesh datablocks."""

    def __init__(self) -> None:
        self.templates: dict[str, AssetTemplate] = {}
        self.failed: dict[str, str] = {}
        self._hidden = bpy.data.collections.new("verify_templates")
        bpy.context.scene.collection.children.link(self._hidden)
        lc = bpy.context.view_layer.layer_collection.children.get(self._hidden.name)
        if lc is not None:
            lc.exclude = True

    def get(self, path: Path, *, key: str | None = None, max_lod: int = 0) -> AssetTemplate | None:
        key = key or str(path)
        if key in self.templates:
            return self.templates[key]
        if key in self.failed:
            return None
        if not path.exists():
            self.failed[key] = f"missing file {path}"
            return None
        try:
            created = import_glb(path)
        except Exception as exc:
            self.failed[key] = f"import failed: {exc}"
            LOG.warning("import of %s failed: %s", path, exc)
            return None
        parts, tris = [], 0
        for ob in created:
            if ob.type == "MESH" and _lod_of(ob.name) <= max_lod:
                parts.append((ob.data, ob.matrix_world.copy()))
                tris += _triangles(ob)
        for ob in created:
            bpy.data.objects.remove(ob, do_unlink=True)
        if not parts:
            self.failed[key] = "no mesh at the requested LOD"
            return None
        tpl = AssetTemplate(key=key, parts=parts, triangles=tris)
        self.templates[key] = tpl
        return tpl


# --------------------------------------------------------------------------- buildings


def add_buildings(cx: float, cy: float, radius_m: float, *, lod0_radius_m: float = 1200.0,
                  col: bpy.types.Collection | None = None) -> dict:
    """Import every built tile shell within ``radius_m``; one LOD per tile, nearest gets LOD0."""
    wanted = tiles_in_radius(cx, cy, radius_m)
    imported, missing, tris, per_tile = [], [], 0, {}
    for tx, ty in wanted:
        name = tile_name(tx, ty)
        glb = TILES_GLB / name / "tile_buildings.glb"
        if not glb.exists():
            missing.append(name)
            continue
        centre = ((tx + 0.5) * TILE_SIZE_M, (ty + 0.5) * TILE_SIZE_M)
        dist = math.hypot(centre[0] - cx, centre[1] - cy)
        lod = 0 if dist <= lod0_radius_m else 1
        try:
            created = import_glb(glb)
        except Exception as exc:
            LOG.warning("tile %s failed to import: %s", name, exc)
            missing.append(f"{name} (import error)")
            continue
        origin = Vector((tx * TILE_SIZE_M, ty * TILE_SIZE_M, 0.0))
        kept = 0
        t = 0
        for ob in created:
            if ob.type != "MESH":
                bpy.data.objects.remove(ob, do_unlink=True)
                continue
            if _lod_of(ob.name) != lod:
                bpy.data.objects.remove(ob, do_unlink=True)
                continue
            ob.location = ob.location + origin
            if col is not None:
                for c in list(ob.users_collection):
                    c.objects.unlink(ob)
                col.objects.link(ob)
            kept += 1
            t += _triangles(ob)
        if kept == 0:
            # The glb has no object at this LOD; re-import at LOD0 rather than lose the tile.
            LOG.warning("tile %s has no LOD%d objects", name, lod)
            missing.append(f"{name} (no LOD{lod})")
            continue
        imported.append(name)
        per_tile[name] = {"lod": lod, "objects": kept, "triangles": t}
        tris += t
    return {"tiles_wanted": len(wanted), "tiles_imported": len(imported), "tiles_missing": len(missing),
            "imported": sorted(imported), "missing": sorted(missing), "triangles": tris,
            "per_tile": per_tile}


# --------------------------------------------------------------------------- landmarks


def load_landmark_catalog() -> list[dict]:
    """Normalise both landmark catalogue shapes into {id, name, origin_tm, glb, bounds_local_m}.

    The tower/building scripts write ``glb`` + ``bounds_local_m`` at the top level; the bridge
    and monument scripts write a ``lods`` map whose entries carry ``path`` and ``bounds``.  Both
    place the model by translating it to ``origin_tm`` -- the model axes are already parallel to
    NYC_TM (blender/landmarks/common.py: "no rotation to apply on import").
    """
    out: list[dict] = []
    if not LANDMARK_CATALOG.is_dir():
        return out
    for p in sorted(LANDMARK_CATALOG.glob("*.json")):
        try:
            e = json.loads(p.read_text())
        except Exception as exc:
            LOG.warning("landmark catalog %s unreadable: %s", p.name, exc)
            continue
        if "origin_tm" not in e:
            continue
        glb = e.get("glb")
        bounds = e.get("bounds_local_m")
        lods = e.get("lods") if isinstance(e.get("lods"), dict) else {}
        glb_lod1 = None
        if not glb and lods:
            lod0 = lods.get("lod0") or {}
            glb = lod0.get("path")
            bounds = lod0.get("bounds") or bounds
        if lods.get("lod1", {}).get("path"):
            glb_lod1 = lods["lod1"]["path"]
        if not glb:
            LOG.warning("landmark %s has no glb path in its catalogue entry", p.stem)
            continue
        out.append({"id": e.get("id", p.stem), "name": e.get("name", p.stem),
                    "origin_tm": e["origin_tm"], "glb": glb, "glb_lod1": glb_lod1,
                    "bounds_local_m": bounds, "height_m": e.get("height_m")})
    return out


def add_landmarks(lib: AssetLibrary, cx: float, cy: float, radius_m: float, *,
                  lod0_radius_m: float = 3000.0, col: bpy.types.Collection | None = None,
                  catalog: Sequence[dict] | None = None) -> dict:
    entries = list(catalog) if catalog is not None else load_landmark_catalog()
    placed, skipped, tris = [], [], 0
    for e in entries:
        ox, oy, oz = (float(v) for v in e["origin_tm"])
        # A landmark's mesh can reach far beyond its origin (bridges span kilometres); keep it
        # if the model's world bounding box touches the scene disc, not just its origin.
        b = e.get("bounds_local_m") or {}
        bmin = b.get("min", [0.0, 0.0, 0.0])
        bmax = b.get("max", [0.0, 0.0, 0.0])
        near_x = min(max(cx, ox + float(bmin[0])), ox + float(bmax[0]))
        near_y = min(max(cy, oy + float(bmin[1])), oy + float(bmax[1]))
        edge = math.hypot(near_x - cx, near_y - cy)
        dist = math.hypot(ox - cx, oy - cy)
        if edge > radius_m:
            continue

        def _resolve(rel: str) -> Path:
            p = Path(rel)
            q = p if p.is_absolute() else REPO_ROOT / p
            return q if q.exists() else BLENDER_OUT / "landmarks" / p.name

        lod = 0 if dist <= lod0_radius_m else 1
        tpl = None
        if lod == 1 and e.get("glb_lod1"):
            tpl = lib.get(_resolve(e["glb_lod1"]), key=f"landmark:{e['id']}:lod1file", max_lod=1)
        if tpl is None:
            tpl = lib.get(_resolve(e["glb"]), key=f"landmark:{e['id']}:lod{lod}", max_lod=lod)
        if tpl is None:
            tpl = lib.get(_resolve(e["glb"]), key=f"landmark:{e['id']}:lod0", max_lod=0)
        if tpl is None:
            skipped.append({"id": e.get("id"),
                            "reason": lib.failed.get(f"landmark:{e['id']}:lod0", "unavailable")})
            continue
        tpl.instance(f"lm_{e['id']}", Matrix.Translation((ox, oy, oz)), col or bpy.context.scene.collection)
        tris += tpl.triangles
        placed.append({"id": e.get("id"), "name": e.get("name"), "distance_m": round(dist, 1),
                       "lod": lod, "triangles": tpl.triangles})
    placed.sort(key=lambda d: d["distance_m"])
    return {"catalog_entries": len(entries), "placed": len(placed), "skipped": len(skipped),
            "triangles": tris, "landmarks": placed, "skipped_detail": skipped}


# --------------------------------------------------------------------------- props


def _load_prop_assets() -> tuple[dict[str, list[dict]], dict[str, dict]]:
    if not PROPS_CATALOG_JSON.exists():
        return {}, {}
    cat = json.loads(PROPS_CATALOG_JSON.read_text())
    by_kind: dict[str, list[dict]] = {}
    by_id: dict[str, dict] = {}
    for e in cat.get("entries", []):
        by_id[e["id"]] = e
        by_kind.setdefault(e.get("dataset_kind") or "", []).append(e)
    return by_kind, by_id


def _tree_asset_id(species: str, height_m: float) -> str:
    key = TREE_SPECIES_KEYS.get((species or "").strip().lower())
    exact = key is not None
    key = key or TREE_FALLBACK_KEY
    if height_m >= 12.0:
        size = "large"
    elif height_m >= 7.0:
        size = "medium"
    else:
        size = "small"
    return f"tree_{key}_{size}", exact


def add_props(lib: AssetLibrary, cx: float, cy: float, radius_m: float, *,
              sampler: TerrainSampler | None = None, triangle_budget: int = 900_000,
              max_instances: int = 40_000, col: bpy.types.Collection | None = None) -> dict:
    """Instance ``props.parquet`` rows inside ``radius_m``, nearest first, under a triangle cap."""
    try:
        import pyarrow.parquet as pq
    except Exception as exc:
        return {"placed": 0, "reason": f"pyarrow unavailable: {exc}"}
    by_kind, by_id = _load_prop_assets()
    if not by_id:
        return {"placed": 0, "reason": f"no prop asset catalogue at {PROPS_CATALOG_JSON}"}
    kinds = {}
    if PROP_KINDS_JSON.exists():
        kinds = {k["id"]: k["name"] for k in json.loads(PROP_KINDS_JSON.read_text()).get("kinds", [])}

    cols = ["kind", "x", "y", "z", "heading", "variant", "species", "height_m"]
    rows = []
    tiles_read, tiles_missing = [], []
    for tx, ty in tiles_in_radius(cx, cy, radius_m):
        p = TILES_DATA / tile_name(tx, ty) / "props.parquet"
        if not p.exists():
            tiles_missing.append(tile_name(tx, ty))
            continue
        try:
            t = pq.read_table(p, columns=cols)
        except Exception as exc:
            LOG.warning("props tile %s unreadable: %s", tile_name(tx, ty), exc)
            tiles_missing.append(tile_name(tx, ty))
            continue
        tiles_read.append(tile_name(tx, ty))
        rows.append(t.to_pydict())
    if not rows:
        return {"placed": 0, "reason": "no props.parquet in range", "tiles_missing": tiles_missing}

    merged = {c: [] for c in cols}
    for r in rows:
        for c in cols:
            merged[c].extend(r[c])
    n = len(merged["x"])
    xs = np.asarray(merged["x"], dtype=np.float64)
    ys = np.asarray(merged["y"], dtype=np.float64)
    d = np.hypot(xs - cx, ys - cy)
    order = np.argsort(d)
    order = order[d[order] <= radius_m]

    placed = 0
    tris = 0
    capped_reason = None
    per_kind: dict[str, int] = {}
    unmapped: dict[str, int] = {}
    species_substituted = 0
    for idx in order:
        if placed >= max_instances:
            capped_reason = f"instance cap {max_instances}"
            break
        if tris >= triangle_budget:
            capped_reason = f"triangle budget {triangle_budget}"
            break
        i = int(idx)
        kind_id = int(merged["kind"][i])
        kind_name = kinds.get(kind_id, str(kind_id))
        exact_species = True
        if kind_name == "tree":
            h = merged["height_m"][i]
            h = float(h) if h is not None and not (isinstance(h, float) and math.isnan(h)) else 8.0
            asset_id, exact_species = _tree_asset_id(merged["species"][i] or "", h)
            if not exact_species:
                species_substituted += 1
            entry = by_id.get(asset_id)
        else:
            alias = PROP_KIND_ALIASES.get(kind_name, kind_name)
            if alias is None:
                unmapped[kind_name] = unmapped.get(kind_name, 0) + 1
                continue
            choices = by_kind.get(alias) or []
            if not choices:
                unmapped[kind_name] = unmapped.get(kind_name, 0) + 1
                continue
            v = merged["variant"][i]
            v = int(v) if v is not None else 0
            entry = choices[v % len(choices)]
        if entry is None:
            unmapped[kind_name] = unmapped.get(kind_name, 0) + 1
            continue
        tpl = lib.get(BLENDER_OUT / entry["glb"], key=f"prop:{entry['id']}", max_lod=0)
        if tpl is None:
            unmapped[kind_name] = unmapped.get(kind_name, 0) + 1
            continue
        z = merged["z"][i]
        if z is None or (isinstance(z, float) and math.isnan(z)):
            z = sampler.z_at(xs[i], ys[i]) if sampler else None
            if z is None:
                continue
        head = merged["heading"][i]
        yaw = 0.0
        if head is not None and not (isinstance(head, float) and math.isnan(head)):
            # props.parquet heading is a compass bearing; scene yaw is counter-clockwise from +x.
            yaw = math.radians(90.0 - float(head))
        m = Matrix.Translation((float(xs[i]), float(ys[i]), float(z))) @ Euler((0.0, 0.0, yaw)).to_matrix().to_4x4()
        tpl.instance(f"prop_{entry['id']}_{placed}", m, col or bpy.context.scene.collection)
        placed += 1
        tris += tpl.triangles
        per_kind[kind_name] = per_kind.get(kind_name, 0) + 1
    return {"rows_in_range": int(order.size), "placed": placed, "triangles": tris,
            "capped": capped_reason, "per_kind": dict(sorted(per_kind.items(), key=lambda kv: -kv[1])),
            "unmapped_kinds": unmapped, "tree_species_substituted": species_substituted,
            "tiles_read": sorted(tiles_read), "tiles_missing": sorted(tiles_missing),
            "radius_m": radius_m}


# --------------------------------------------------------------------------- kit


KIT_RECORD = np.dtype([("kit_id", "<u4"), ("bin", "<i8"), ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                       ("yaw_deg", "<f4"), ("scale", "<f4"), ("variant_seed", "<u4"), ("flags", "<u4")])
assert KIT_RECORD.itemsize == 40, KIT_RECORD.itemsize


def load_kit_map() -> tuple[dict[int, dict], str]:
    """kit_id -> {glb, catalog_id, category} from the facade stage's numeric registry.

    Both ``kit_catalog_map.json`` and ``kit_ids.json`` are read (they carry the same list under
    ``pieces`` in schema 2 and under ``map`` in schema 1); the first one that resolves wins.
    Returns an empty map plus the reason when neither does.
    """
    reasons = []
    for path in (KIT_MAP_JSON, KIT_IDS_JSON):
        if not path.exists():
            reasons.append(f"{path.name} absent")
            continue
        try:
            d = json.loads(path.read_text())
        except Exception as exc:
            reasons.append(f"{path.name} unreadable: {exc}")
            continue
        entries = d.get("pieces") or d.get("map") or []
        m = {int(e["kit_id"]): e for e in entries if isinstance(e, dict) and e.get("glb")}
        if m:
            return m, ""
        reasons.append(f"{path.name} has no entry carrying a glb path")
    return {}, "; ".join(reasons) or "no kit id registry on disk"


def _tile_kit_header(tile: str) -> dict[int, dict]:
    """kit_id -> entry from a tile's ``kit_placements.json``; schema 2 carries the glb path."""
    p = TILES_DATA / tile / "kit_placements.json"
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text())
    except Exception:
        return {}
    return {int(e["kit_id"]): e for e in d.get("kit_id_counts", []) if isinstance(e, dict)}


def add_kit(lib: AssetLibrary, cx: float, cy: float, radius_m: float, *,
            triangle_budget: int = 1_200_000, max_instances: int = 120_000,
            col: bpy.types.Collection | None = None) -> dict:
    """Instance facade kit placements inside ``radius_m``, nearest first, under a triangle cap."""
    kit_map, why = load_kit_map()
    recs = []
    tiles_read, tiles_missing = [], []
    stale, header_only = {}, {}
    for tx, ty in tiles_in_radius(cx, cy, radius_m):
        tname = tile_name(tx, ty)
        p = TILES_DATA / tname / "kit_placements.bin"
        if not p.exists():
            tiles_missing.append(tname)
            continue
        try:
            a = np.fromfile(p, dtype=KIT_RECORD)
        except Exception as exc:
            LOG.warning("kit tile %s unreadable: %s", tname, exc)
            tiles_missing.append(tname)
            continue
        # The registry is regenerated independently of the placements, so a numeric id can be
        # left pointing at a different piece.  The tile header records the id -> piece mapping
        # the placements were written with; any id where the two disagree is dropped rather
        # than drawn as the wrong piece.
        for kid, e in _tile_kit_header(tname).items():
            reg = kit_map.get(kid)
            if e.get("glb") and (reg is None or reg.get("glb") == e.get("glb")):
                header_only[kid] = e
            elif reg is not None and e.get("glb") and reg.get("glb") != e.get("glb"):
                stale[kid] = f"header {e.get('catalog_id')} vs registry {reg.get('catalog_id')}"
        sel = (np.hypot(a["x"].astype(np.float64) - cx, a["y"].astype(np.float64) - cy) <= radius_m)
        if sel.any():
            recs.append(a[sel])
        tiles_read.append(tname)
    if header_only:
        kit_map = {**kit_map, **header_only}
    if not kit_map:
        return {"placed": 0, "reason": why, "tiles_missing": sorted(tiles_missing)}
    if not recs:
        return {"placed": 0, "reason": "no kit_placements.bin in range",
                "tiles_missing": sorted(tiles_missing)}
    a = np.concatenate(recs)
    d = np.hypot(a["x"].astype(np.float64) - cx, a["y"].astype(np.float64) - cy)
    order = np.argsort(d)

    placed, tris, capped = 0, 0, None
    unresolved: dict[int, int] = {}
    per_cat: dict[str, int] = {}
    for idx in order:
        if placed >= max_instances:
            capped = f"instance cap {max_instances}"
            break
        if tris >= triangle_budget:
            capped = f"triangle budget {triangle_budget}"
            break
        r = a[int(idx)]
        kid = int(r["kit_id"])
        e = kit_map.get(kid)
        if e is None:
            unresolved[kid] = unresolved.get(kid, 0) + 1
            continue
        tpl = lib.get(BLENDER_OUT / e["glb"], key=f"kit:{kid}", max_lod=0)
        if tpl is None:
            unresolved[kid] = unresolved.get(kid, 0) + 1
            continue
        s = float(r["scale"]) or 1.0
        m = (Matrix.Translation((float(r["x"]), float(r["y"]), float(r["z"])))
             @ Euler((0.0, 0.0, math.radians(float(r["yaw_deg"])))).to_matrix().to_4x4()
             @ Matrix.Scale(s, 4))
        tpl.instance(f"kit_{kid}_{placed}", m, col or bpy.context.scene.collection)
        placed += 1
        tris += tpl.triangles
        cat = e.get("category", "?")
        per_cat[cat] = per_cat.get(cat, 0) + 1
    return {"records_in_range": int(a.size), "placed": placed, "triangles": tris, "capped": capped,
            "per_category": dict(sorted(per_cat.items(), key=lambda kv: -kv[1])),
            "unresolved_ids": {str(k): v for k, v in sorted(unresolved.items())},
            "stale_registry_ids": {str(k): v for k, v in sorted(stale.items())},
            "tiles_read": sorted(tiles_read), "tiles_missing": sorted(tiles_missing),
            "radius_m": radius_m}


# --------------------------------------------------------------------------- assembly


@dataclass
class SceneReport:
    centre_tm: tuple[float, float]
    radius_m: float
    terrain: dict = field(default_factory=dict)
    buildings: dict = field(default_factory=dict)
    landmarks: dict = field(default_factory=dict)
    props: dict = field(default_factory=dict)
    kit: dict = field(default_factory=dict)
    triangles: int = 0
    seconds: float = 0.0

    def as_dict(self) -> dict:
        return {"centre_tm": [round(self.centre_tm[0], 2), round(self.centre_tm[1], 2)],
                "radius_m": self.radius_m, "triangles": self.triangles,
                "seconds": round(self.seconds, 2), "terrain": self.terrain,
                "buildings": self.buildings, "landmarks": self.landmarks,
                "props": self.props, "kit": self.kit}


def build_scene(cx: float, cy: float, radius_m: float, *, prop_radius_m: float | None = None,
                kit_radius_m: float | None = None, triangle_budget: int = 3_000_000,
                terrain_max_side: int = 420, lod0_radius_m: float = 1200.0,
                with_props: bool = True, with_kit: bool = True) -> tuple[SceneReport, TerrainSampler]:
    """Reset the scene and populate it from every artefact available around (cx, cy)."""
    import time
    t0 = time.time()
    nb.reset_scene()
    scene_col = bpy.context.scene.collection
    c_terrain = nb.collection("terrain", scene_col)
    c_build = nb.collection("buildings", scene_col)
    c_landmark = nb.collection("landmarks", scene_col)
    c_props = nb.collection("props", scene_col)
    c_kit = nb.collection("kit", scene_col)

    sampler = TerrainSampler()
    rep = SceneReport(centre_tm=(cx, cy), radius_m=radius_m)
    rep.terrain = build_terrain(sampler, cx, cy, radius_m, max_side=terrain_max_side, col=c_terrain)
    rep.buildings = add_buildings(cx, cy, radius_m, lod0_radius_m=lod0_radius_m, col=c_build)

    lib = AssetLibrary()
    rep.landmarks = add_landmarks(lib, cx, cy, radius_m, col=c_landmark)

    used = int(rep.terrain.get("triangles", 0)) + rep.buildings["triangles"] + rep.landmarks["triangles"]
    left = max(0, triangle_budget - used)
    if with_props:
        rep.props = add_props(lib, cx, cy, prop_radius_m if prop_radius_m is not None else min(radius_m, 400.0),
                              sampler=sampler, triangle_budget=int(left * 0.45), col=c_props)
    else:
        rep.props = {"placed": 0, "reason": "disabled"}
    left = max(0, left - int(rep.props.get("triangles", 0)))
    if with_kit:
        rep.kit = add_kit(lib, cx, cy, kit_radius_m if kit_radius_m is not None else min(radius_m, 200.0),
                          triangle_budget=left, col=c_kit)
    else:
        rep.kit = {"placed": 0, "reason": "disabled"}

    rep.triangles = (int(rep.terrain.get("triangles", 0)) + rep.buildings["triangles"]
                     + rep.landmarks["triangles"] + int(rep.props.get("triangles", 0))
                     + int(rep.kit.get("triangles", 0)))
    rep.seconds = time.time() - t0
    LOG.info("scene built: %d triangles in %.1f s (%d tiles, %d landmarks, %d props, %d kit)",
             rep.triangles, rep.seconds, rep.buildings["tiles_imported"], rep.landmarks["placed"],
             rep.props.get("placed", 0), rep.kit.get("placed", 0))
    return rep, sampler


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--radius", type=float, default=600.0)
    ap.add_argument("--prop-radius", type=float, default=None)
    ap.add_argument("--kit-radius", type=float, default=None)
    ap.add_argument("--triangle-budget", type=int, default=3_000_000)
    ap.add_argument("--no-props", action="store_true")
    ap.add_argument("--no-kit", action="store_true")
    ap.add_argument("--json", default=None, help="write the scene report here ('-' for stdout)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    from nycsim_pipeline.crs import lonlat_to_tm
    x, y = lonlat_to_tm(a.lon, a.lat)
    rep, _ = build_scene(x, y, a.radius, prop_radius_m=a.prop_radius, kit_radius_m=a.kit_radius,
                         triangle_budget=a.triangle_budget, with_props=not a.no_props,
                         with_kit=not a.no_kit)
    text = json.dumps(rep.as_dict(), indent=1, sort_keys=True)
    if a.json == "-" or a.json is None:
        print(text)
    else:
        Path(a.json).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
