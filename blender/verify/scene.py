"""Assemble a NYCSim verification scene in Blender around a world position.

The scene is built from the artefacts the other stages have already written, never from
invented geometry:

* terrain   -- ``data/processed/tiles/{tile}/terrain.png`` + ``terrain.json`` (16-bit,
               501x501 at 2 m, ``z = z_min_m + value * z_scale_m``) displaced onto a regular
               grid, with the water surface split off as its own material.
* buildings -- ``blender_out/tiles/{tile}/tile_buildings.glb`` and, where the tile reaches into
               New Jersey, ``tile_buildings_nj.glb`` beside it; each file carries LOD0/LOD1/LOD2
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
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

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
#: Per-tile shell files, in import order: the New York City shells and, where the tile reaches into
#: New Jersey, the New Jersey ones beside them.  Named here rather than inline so a verification run
#: can import one dataset on its own -- which is how the before/after pair for the New Jersey stage
#: was made.
TILE_GLB_FILES = ("tile_buildings.glb", "tile_buildings_nj.glb")
LANDMARK_CATALOG = BLENDER_OUT / "landmarks" / "catalog"
PROPS_CATALOG_JSON = BLENDER_OUT / "props" / "props_asset_catalog.json"
KIT_MAP_JSON = PROCESSED / "facade" / "kit_catalog_map.json"
KIT_IDS_JSON = PROCESSED / "facade" / "kit_ids.json"
PROP_KINDS_JSON = PROCESSED / "furniture" / "props_catalog.json"

TILE_SIZE_M = 1000.0
TERRAIN_SAMPLES = 501
TERRAIN_SPACING_M = 2.0

_LOD_SUFFIX = re.compile(r"_LOD(\d+)$", re.IGNORECASE)

#: Camera-facing impostor cards exported alongside the real geometry of an asset.  Blender's glTF
#: importer suffixes duplicate names with ".001", so the trailing index has to be tolerated.
_IMPOSTOR_NAME = re.compile(r"_billboard(\.\d+)?$", re.IGNORECASE)

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

    def ground_z(self, x: float, y: float, *, mode: str = "local", radius_m: float = 5.0,
                 percentile: float = 10.0) -> tuple[float | None, dict]:
        """Ground height under a viewpoint, read from a neighbourhood rather than one sample.

        ``mode="local"`` takes the height **at the point itself** -- right for a viewpoint that
        names the surface it stands on (a promenade, a terrace, an observation deck), where the
        raised structure *is* the ground.  Bethesda Terrace is why: its upper level stands 5.4 m
        above the fountain plaza, the two are 4 m apart in plan, and the median inside 5 m put the
        camera 3.8 m *below* the terrace it was standing on, which rendered a black frame from
        inside the bank.  The neighbourhood is still measured and reported so the sheet can show
        how much relief there is.  ``mode="street"`` takes a low percentile inside ``radius_m``
        instead: the 1 m heightmap carries building grades and raised plinths, and a camera
        recorded as standing on a sidewalk must not be lifted onto the terrace next to it.
        Returns ``(z, detail)``; ``z`` is None when no heightmap covers the point.
        """
        n = max(3, int(round(2 * radius_m / TERRAIN_SPACING_M)) + 1)
        xs, ys = np.meshgrid(np.linspace(x - radius_m, x + radius_m, n),
                             np.linspace(y - radius_m, y + radius_m, n))
        d = np.hypot(xs - x, ys - y)
        z, _ = self.grid(xs, ys)
        ok = (~np.isnan(z)) & (d <= radius_m)
        if not ok.any():
            return None, {"mode": mode, "samples": 0}
        vals = z[ok]
        point = self.z_at(x, y)
        if mode == "street":
            zz = float(np.percentile(vals, percentile))
        elif point is not None:
            zz = float(point)
        else:
            zz = float(np.median(vals))
        return zz, {"mode": mode, "radius_m": radius_m, "samples": int(ok.sum()),
                    "min_m": round(float(vals.min()), 2), "max_m": round(float(vals.max()), 2),
                    "median_m": round(float(np.median(vals)), 2),
                    "point_m": None if point is None else round(float(point), 2),
                    "percentile": percentile if mode == "street" else None,
                    "chosen_m": round(zz, 2)}


def _graded_offsets(radius_m: float, near_m: float, near_spacing_m: float,
                    max_spacing_m: float, growth: float) -> list[float]:
    """Distances 0 .. radius_m: ``near_spacing_m`` apart out to ``near_m``, then coarsening."""
    offs = [0.0]
    step = float(near_spacing_m)
    d = 0.0
    while d < radius_m:
        d = min(d + step, radius_m)
        offs.append(d)
        if d >= near_m:
            step = min(step * growth, max_spacing_m)
    return offs


def graded_axis(centre: float, radius_m: float, *, near_m: float, near_spacing_m: float,
                max_spacing_m: float, growth: float, max_points: int) -> tuple[np.ndarray, dict]:
    """A sample axis that is dense under the camera and coarse at the horizon.

    A uniform grid over a street-level scene is the wrong shape: at a 700 m radius and a 300-sample
    cap it lands one height every 4.7 m, which turns a flat sidewalk 10 m from the lens into a
    rolling mound and is the single most visible defect in a foreground.  The same 300 samples
    graded -- 2 m out to ``near_m``, then growing geometrically to ``max_spacing_m`` -- resolve the
    kerb the camera is standing on while still reaching the horizon.  ``growth`` (and then the near
    spacing) is relaxed until the axis fits inside ``max_points``.
    """
    ns, g = max(0.25, float(near_spacing_m)), max(1.001, float(growth))
    offs = _graded_offsets(radius_m, near_m, ns, max_spacing_m, g)
    for _ in range(60):
        if 2 * len(offs) - 1 <= max_points:
            break
        if g < 1.5:
            g = min(1.5, g * 1.06)
        else:
            ns *= 1.25
        offs = _graded_offsets(radius_m, near_m, ns, max_spacing_m, g)
    xs = np.asarray([-o for o in reversed(offs[1:])] + offs, dtype=np.float64) + float(centre)
    steps = np.diff(np.asarray(offs))
    return xs, {"near_spacing_m": round(float(ns), 3), "growth": round(float(g), 3),
                "points": int(xs.size),
                "far_spacing_m": round(float(steps.max()) if steps.size else 0.0, 2)}


def build_terrain(sampler: TerrainSampler, cx: float, cy: float, radius_m: float, *,
                  max_side: int = 300, near_m: float = 150.0,
                  near_spacing_m: float = TERRAIN_SPACING_M, max_spacing_m: float = 40.0,
                  growth: float = 1.14, col: bpy.types.Collection | None = None) -> dict:
    """Displaced grid over the square of half-width ``radius_m`` centred on (cx, cy).

    The grid is graded rather than uniform (see :func:`graded_axis`): the heightmap's own 2 m
    spacing within ``near_m`` of the centre, coarsening to at most ``max_spacing_m`` at the edge.
    The camera can be moved up to 80 m out of a building shell or walked as far as 250 m to a
    parapet after the terrain is built, so ``near_m`` has to cover that displacement too.
    """
    xs1, grade = graded_axis(cx, radius_m, near_m=near_m, near_spacing_m=near_spacing_m,
                             max_spacing_m=max_spacing_m, growth=growth, max_points=max_side + 1)
    ys1, _ = graded_axis(cy, radius_m, near_m=near_m, near_spacing_m=near_spacing_m,
                         max_spacing_m=max_spacing_m, growth=growth, max_points=max_side + 1)
    n = int(xs1.size)
    xs, ys = np.meshgrid(xs1, ys1)
    z, water = sampler.grid(xs, ys)
    holes = int(np.isnan(z).sum())
    if holes == z.size:
        LOG.warning("no terrain heightmap covers the scene; ground omitted")
        return {"built": False, "reason": "no terrain tiles on disk for this area",
                "samples": 0, "spacing_m": grade["near_spacing_m"], "holes": holes}
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
    return {"built": True, "samples": n, "spacing_m": grade["near_spacing_m"],
            "near_spacing_m": grade["near_spacing_m"], "near_m": round(float(near_m), 1),
            "far_spacing_m": grade["far_spacing_m"], "grading_growth": grade["growth"],
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


def _is_impostor(ob: bpy.types.Object) -> bool:
    """Is this mesh a camera-facing impostor card rather than the asset's real geometry?"""
    if _IMPOSTOR_NAME.search(ob.name):
        return True
    mats = [m.name for m in ob.data.materials if m is not None]
    return bool(mats) and all(m.startswith("IMPOSTOR_") for m in mats)


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
        self.impostors_dropped = 0
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
                if _is_impostor(ob):
                    # Every tree asset carries a six-polygon ``<species>_billboard`` card with an
                    # ``IMPOSTOR_*`` material.  It is meant to stand in for the crown at distance,
                    # but the exported material is an opaque flat colour with no alpha texture, so
                    # drawn at LOD0 over the real branches it turns every street tree into a solid
                    # cone -- which is exactly what the first street-level sheets showed.  The card
                    # is dropped here and counted, and the real geometry is used at every distance.
                    self.impostors_dropped += 1
                    continue
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


def landmark_bins(catalog: Sequence[dict] | None = None) -> set[int]:
    """BINs that a landmark model replaces, from the catalogue's own ``bins`` list.

    67 of the 93 landmark catalogue entries name the building footprints they were built from --
    121 BINs in all -- and ``blender_out/tiles`` builds a shell for every one of them.  Drawing
    both puts two versions of the Empire State Building, the Flatiron and the Woolworth in the
    same frame, differing by a metre or two and z-fighting where they touch.
    """
    out: set[int] = set()
    entries = catalog if catalog is not None else _raw_landmark_entries()
    for e in entries:
        for b in (e.get("bins") or []):
            try:
                out.add(int(b))
            except (TypeError, ValueError):
                continue
    return out


def _raw_landmark_entries() -> list[dict]:
    out = []
    if not LANDMARK_CATALOG.is_dir():
        return out
    for p in sorted(LANDMARK_CATALOG.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception as exc:
            LOG.warning("landmark catalog %s unreadable: %s", p.name, exc)
    return out


def suppress_bins(objects: Sequence[bpy.types.Object], bins: set[int]) -> dict:
    """Delete the faces of imported shells whose ``_BIN`` vertex attribute is in ``bins``.

    The tile glb carries ``_BIN`` as a per-vertex float (NYC BINs are seven digits, well inside
    float32's exact integer range), so a shell can be removed from a merged per-material mesh
    without touching its neighbours.
    """
    if not bins:
        return {"meshes_edited": 0, "faces_removed": 0, "bins_removed": []}
    import bmesh
    wanted = np.fromiter(sorted(bins), dtype=np.int64)
    edited = 0
    removed_faces = 0
    removed_bins: set[int] = set()
    for ob in objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        attr = me.attributes.get("_BIN")
        if attr is None or attr.domain != "POINT":
            continue
        n = len(me.vertices)
        if n == 0:
            continue
        vals = np.empty(n, dtype=np.float32)
        attr.data.foreach_get("value", vals)
        ints = np.rint(vals).astype(np.int64)
        mask = np.isin(ints, wanted)
        if not mask.any():
            continue
        removed_bins.update(int(v) for v in np.unique(ints[mask]))
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        doomed = [v for i, v in enumerate(bm.verts) if mask[i]]
        faces = {f for v in doomed for f in v.link_faces}
        removed_faces += len(faces)
        # "VERTS" removes each vertex and every face that uses it in one pass, which is exactly
        # the semantics wanted here: a face belongs to a suppressed building if any of its
        # vertices carries that BIN.  Deleting the faces first invalidates the vertex handles.
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        bm.to_mesh(me)
        bm.free()
        me.update()
        edited += 1
    return {"meshes_edited": edited, "faces_removed": removed_faces,
            "bins_removed": sorted(removed_bins)}


def add_buildings(cx: float, cy: float, radius_m: float, *, lod0_radius_m: float = 1200.0,
                  lod1_radius_m: float = 2500.0, triangle_budget: int = 3_500_000,
                  col: bpy.types.Collection | None = None,
                  suppress_landmark_bins: set[int] | None = None) -> dict:
    """Import the built tile shells within ``radius_m``, nearest first, one LOD per tile.

    A 5 km skyline scene reaches 99 tiles; importing all of them at LOD0 would cost more triangles
    than the machine has memory for, so tiles are taken nearest-first, dropped down to LOD1 beyond
    ``lod0_radius_m`` and LOD2 beyond ``lod1_radius_m``, and the import stops when the budget is
    spent.  Whatever is dropped is named in the result so the sheet can say so.

    Not every tile glb carries every LOD -- a tile whose shells decimate to nothing at LOD2 is
    written with LOD0 and LOD1 only -- so a tile that has no mesh at the requested LOD falls back
    to the nearest LOD it does have rather than vanishing from the skyline.
    """
    wanted = tiles_in_radius(cx, cy, radius_m)
    wanted.sort(key=lambda t: math.hypot((t[0] + 0.5) * TILE_SIZE_M - cx,
                                         (t[1] + 0.5) * TILE_SIZE_M - cy))
    imported, missing, tris, per_tile = [], [], 0, {}
    with_nj: list[str] = []
    dropped_for_budget: list[str] = []
    lod_substituted: list[str] = []
    suppressed = {"meshes": 0, "faces": 0, "bins": set()}
    for tx, ty in wanted:
        name = tile_name(tx, ty)
        if tris >= triangle_budget:
            dropped_for_budget.append(name)
            continue
        # A tile can carry a New York shell file, a New Jersey one, or both: the Hudson bank and
        # Bayonne are inside the scope (ARCHITECTURE §3) and are built by the same stage into a
        # sibling glb.  Both are imported into the same tile bucket so the LOD choice, the triangle
        # budget and the report cover the whole tile.
        glbs = [q for q in (TILES_GLB / name / f for f in TILE_GLB_FILES) if q.exists()]
        if not glbs:
            missing.append(name)
            continue
        centre = ((tx + 0.5) * TILE_SIZE_M, (ty + 0.5) * TILE_SIZE_M)
        dist = math.hypot(centre[0] - cx, centre[1] - cy)
        lod = 0 if dist <= lod0_radius_m else (1 if dist <= lod1_radius_m else 2)
        created = []
        loaded = []
        for q in glbs:
            try:
                created.extend(import_glb(q))
            except Exception as exc:
                LOG.warning("tile %s: %s failed to import: %s", name, q.name, exc)
                continue
            loaded.append(q.name)
        if not created:
            missing.append(f"{name} (import error)")
            continue
        origin = Vector((tx * TILE_SIZE_M, ty * TILE_SIZE_M, 0.0))
        by_lod: dict[int, list] = {}
        for ob in created:
            if ob.type != "MESH":
                bpy.data.objects.remove(ob, do_unlink=True)
                continue
            by_lod.setdefault(_lod_of(ob.name), []).append(ob)
        if not by_lod:
            LOG.warning("tile %s glb carries no mesh", name)
            missing.append(f"{name} (no mesh in the glb)")
            continue
        # Not every tile carries every LOD: a tile whose shells decimate to nothing at LOD2 is
        # written with LOD0 and LOD1 only.  Dropping such a tile leaves a hole in the skyline, so
        # take the nearest LOD that exists instead -- preferring the coarser of two equally near
        # ones -- and record the substitution.
        use = min(by_lod, key=lambda l: (abs(l - lod), -l))
        for l, obs in by_lod.items():
            if l == use:
                continue
            for ob in obs:
                bpy.data.objects.remove(ob, do_unlink=True)
        if suppress_landmark_bins:
            # Only the New York shells: a New Jersey object's ``_bin`` is a USA Structures BUILD_ID,
            # not a BIN, and New Jersey has no hand-modelled landmark to make room for.
            rep = suppress_bins([ob for ob in by_lod[use] if "_nj_" not in ob.name],
                                suppress_landmark_bins)
            suppressed["meshes"] += rep["meshes_edited"]
            suppressed["faces"] += rep["faces_removed"]
            suppressed["bins"].update(rep["bins_removed"])
        kept = 0
        t = 0
        for ob in by_lod[use]:
            ob.location = ob.location + origin
            if col is not None:
                for c in list(ob.users_collection):
                    c.objects.unlink(ob)
                col.objects.link(ob)
            kept += 1
            t += _triangles(ob)
        imported.append(name)
        per_tile[name] = {"lod": use, "objects": kept, "triangles": t, "files": loaded}
        if "tile_buildings_nj.glb" in loaded:
            with_nj.append(name)
        if use != lod:
            per_tile[name]["lod_requested"] = lod
            per_tile[name]["lod_substituted"] = (
                f"the tile glb has no LOD{lod}; LOD{use} used instead")
            lod_substituted.append(f"{name} (LOD{lod} -> LOD{use})")
        tris += t
    # Object transforms are set directly, so the dependency graph has to be refreshed before
    # anything (a test, a bounds check, an exporter) reads matrix_world.
    bpy.context.view_layer.update()
    return {"tiles_wanted": len(wanted), "tiles_imported": len(imported), "tiles_missing": len(missing),
            "imported": sorted(imported), "missing": sorted(missing), "triangles": tris,
            "tiles_dropped_for_budget": len(dropped_for_budget),
            "dropped_for_budget": sorted(dropped_for_budget), "triangle_budget": triangle_budget,
            "tiles_lod_substituted": len(lod_substituted),
            "lod_substituted": sorted(lod_substituted),
            "tiles_with_new_jersey": len(with_nj), "new_jersey": sorted(with_nj),
            "landmark_bins_suppressed": len(suppressed["bins"]),
            "landmark_faces_suppressed": suppressed["faces"],
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
    bpy.context.view_layer.update()
    return {"catalog_entries": len(entries), "placed": len(placed), "skipped": len(skipped),
            "triangles": tris, "landmarks": placed, "skipped_detail": skipped}


# --------------------------------------------------------------------------- pavement


PAVEMENT_DIR = PROCESSED / "roads" / "pavement"

#: ``kind`` -> (name, lift above the terrain in metres, base colour, roughness).  The lift keeps the
#: pavement clear of the terrain grid it is draped on and reproduces the real 0.15 m curb reveal:
#: roadbed at +0.10, everything the pedestrian walks on at +0.25.
PAVEMENT_KINDS = {
    0: ("roadbed", 0.10, (0.055, 0.055, 0.058, 1.0), 0.85),
    1: ("sidewalk", 0.25, (0.34, 0.335, 0.32, 1.0), 0.88),
    2: ("median", 0.25, (0.30, 0.30, 0.29, 1.0), 0.88),
    3: ("plaza", 0.25, (0.33, 0.31, 0.30, 1.0), 0.80),
    4: ("curb", 0.25, (0.42, 0.42, 0.41, 1.0), 0.80),
    5: ("crosswalk", 0.115, (0.62, 0.62, 0.60, 1.0), 0.75),
    6: ("parking_lot", 0.10, (0.075, 0.075, 0.078, 1.0), 0.85),
}


def add_pavement(cx: float, cy: float, radius_m: float, sampler: TerrainSampler, *,
                 col: bpy.types.Collection | None = None,
                 triangle_budget: int = 900_000) -> dict:
    """Drape the real paved surfaces over the terrain.

    ``data/processed/roads/pavement/{tile}.parquet`` (DATA_CONTRACTS s7) holds the DoITT
    planimetric roadbed, sidewalk, median, plaza, curb and parking-lot polygons plus the derived
    crosswalks, clipped to the tile grid.  Without them a street-level frame is a single flat
    ground plane where the photograph has asphalt, a curb line, a sidewalk and a crosswalk, which
    is the largest single difference at eye level.  Each polygon is triangulated in plan and every
    vertex is lifted to the heightmap surface plus the kind's own offset, so the pavement follows
    the real grade and the curb reveal is the real 0.15 m.
    """
    try:
        import pyarrow.parquet as pq
        import shapely
    except Exception as exc:
        return {"placed": 0, "reason": f"pyarrow/shapely unavailable: {exc}"}
    if not PAVEMENT_DIR.is_dir():
        return {"placed": 0, "reason": f"no pavement directory at {PAVEMENT_DIR}"}

    mats = {k: nb.pbr_material(f"pave_{name}", base_color=colour, roughness=rough)
            for k, (name, _lift, colour, rough) in PAVEMENT_KINDS.items()}
    mat_list = [mats[k] for k in sorted(mats)]
    mat_index = {k: i for i, k in enumerate(sorted(mats))}

    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    face_kind: list[int] = []
    per_kind: dict[str, int] = {}
    tiles_read, tiles_missing, dropped = [], [], 0
    r2 = radius_m * radius_m
    for tx, ty in tiles_in_radius(cx, cy, radius_m):
        tname = tile_name(tx, ty)
        p = PAVEMENT_DIR / f"{tname}.parquet"
        if not p.exists():
            tiles_missing.append(tname)
            continue
        try:
            t = pq.read_table(p, columns=["kind", "geometry"])
        except Exception as exc:
            LOG.warning("pavement tile %s unreadable: %s", tname, exc)
            tiles_missing.append(tname)
            continue
        tiles_read.append(tname)
        kinds = t.column("kind").to_pylist()
        geoms = t.column("geometry").to_pylist()
        for kind, blob in zip(kinds, geoms):
            if len(faces) >= triangle_budget:
                dropped += 1
                continue
            k = int(kind)
            if k not in PAVEMENT_KINDS:
                dropped += 1
                continue
            try:
                g = shapely.from_wkb(blob)
            except Exception:
                dropped += 1
                continue
            polys = list(g.geoms) if g.geom_type == "MultiPolygon" else ([g] if g.geom_type == "Polygon" else [])
            for poly in polys:
                ex = list(poly.exterior.coords)[:-1]
                if len(ex) < 3:
                    continue
                # Cheap reject: skip a polygon whose bounding box misses the scene disc entirely.
                xs = [c[0] for c in ex]
                ys = [c[1] for c in ex]
                nx = min(max(cx, min(xs)), max(xs))
                ny = min(max(cy, min(ys)), max(ys))
                if (nx - cx) ** 2 + (ny - cy) ** 2 > r2:
                    continue
                holes = [list(r.coords)[:-1] for r in poly.interiors if len(r.coords) > 3]
                try:
                    tris = nb.triangulate_2d(ex, holes)
                except Exception:
                    dropped += 1
                    continue
                if not tris:
                    dropped += 1
                    continue
                ring = list(ex)
                for h in holes:
                    ring.extend(h)
                base = len(verts)
                ax = np.array([c[0] for c in ring], dtype=np.float64)
                ay = np.array([c[1] for c in ring], dtype=np.float64)
                z, _ = sampler.grid(ax.reshape(1, -1), ay.reshape(1, -1))
                z = z.ravel()
                if np.isnan(z).all():
                    dropped += 1
                    continue
                fill = float(np.nanmedian(z))
                z = np.where(np.isnan(z), fill, z) + PAVEMENT_KINDS[k][1]
                verts.extend((float(ax[i]), float(ay[i]), float(z[i])) for i in range(len(ring)))
                for a, b, c in tris:
                    faces.append((base + a, base + b, base + c))
                    face_kind.append(k)
                per_kind[PAVEMENT_KINDS[k][0]] = per_kind.get(PAVEMENT_KINDS[k][0], 0) + 1
    if not faces:
        return {"placed": 0, "reason": "no pavement polygons in range",
                "tiles_missing": sorted(tiles_missing)}
    ob = nb.mesh_object("verify_pavement", verts, faces, col=col, materials=mat_list, smooth=False)
    for poly, k in zip(ob.data.polygons, face_kind):
        poly.material_index = mat_index[k]
    bpy.context.view_layer.update()
    return {"placed": sum(per_kind.values()), "triangles": len(faces), "vertices": len(verts),
            "per_kind": dict(sorted(per_kind.items(), key=lambda kv: -kv[1])),
            "dropped_polygons": dropped, "tiles_read": sorted(tiles_read),
            "tiles_missing": sorted(tiles_missing), "radius_m": radius_m}


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


def _tree_asset_id(species: str, height_m: float, leaf_off: bool) -> tuple[str, bool]:
    key = TREE_SPECIES_KEYS.get((species or "").strip().lower())
    exact = key is not None
    key = key or TREE_FALLBACK_KEY
    if height_m >= 12.0:
        size = "large"
    elif height_m >= 7.0:
        size = "medium"
    else:
        size = "small"
    return f"tree_{key}_{size}{'_bare' if leaf_off else ''}", exact


def add_props(lib: AssetLibrary, cx: float, cy: float, radius_m: float, *,
              sampler: TerrainSampler | None = None, triangle_budget: int = 900_000,
              max_instances: int = 40_000, leaf_off: bool = False,
              col: bpy.types.Collection | None = None) -> dict:
    """Instance ``props.parquet`` rows inside ``radius_m``, nearest first, under a triangle cap.

    ``leaf_off`` picks the bare-canopy tree variants the props kit exports, for a reference
    photograph taken between mid-November and mid-April when NYC street trees carry no leaves.
    """
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
            asset_id, exact_species = _tree_asset_id(merged["species"][i] or "", h, leaf_off)
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
            # props.parquet ``heading`` is a compass bearing (0 = north, clockwise); every prop
            # asset is authored facing +Y (north) in Blender, so the scene yaw about +Z is the
            # negated bearing.
            yaw = math.radians(-float(head))
        m = Matrix.Translation((float(xs[i]), float(ys[i]), float(z))) @ Euler((0.0, 0.0, yaw)).to_matrix().to_4x4()
        tpl.instance(f"prop_{entry['id']}_{placed}", m, col or bpy.context.scene.collection)
        placed += 1
        tris += tpl.triangles
        per_kind[kind_name] = per_kind.get(kind_name, 0) + 1
    return {"rows_in_range": int(order.size), "placed": placed, "triangles": tris,
            "leaf_off": leaf_off, "impostor_cards_dropped": lib.impostors_dropped,
            "capped": capped_reason, "per_kind": dict(sorted(per_kind.items(), key=lambda kv: -kv[1])),
            "unmapped_kinds": unmapped, "tree_species_substituted": species_substituted,
            "tiles_read": sorted(tiles_read), "tiles_missing": sorted(tiles_missing),
            "radius_m": radius_m}


# --------------------------------------------------------------------------- prop scale audit


def audit_prop_assets(tolerance: float = 0.15) -> dict:
    """Check every exported prop against the size its own catalogue entry publishes.

    A prop is instanced by translation and yaw alone -- :func:`add_props` never scales one -- so a
    prop that renders at the wrong size in a frame can only be wrong in its glb.  This imports
    every asset the way the scene does (LOD0 meshes, the local matrices the glb carries) and
    measures the world-space bounding box against ``nominal_size_m``.

    A modelled light cone is part of the lamp's glb and legitimately reaches metres beyond the
    pole, so an entry whose oversize is explained by ``bounds_with_effects`` is reported as
    ``with_effects`` rather than as a fault: the daylight pass makes those cones transparent.
    Anything left in ``bad`` is a real scale error.
    """
    if not PROPS_CATALOG_JSON.exists():
        return {"checked": 0, "reason": f"no prop asset catalogue at {PROPS_CATALOG_JSON}"}
    entries = json.loads(PROPS_CATALOG_JSON.read_text()).get("entries", [])
    lib = AssetLibrary()
    bad, with_effects, unloadable = [], [], []
    for e in entries:
        tpl = lib.get(BLENDER_OUT / e["glb"], key=f"prop:{e['id']}", max_lod=0)
        if tpl is None:
            unloadable.append({"id": e["id"], "reason": lib.failed.get(f"prop:{e['id']}", "unknown")})
            continue
        lo = [math.inf] * 3
        hi = [-math.inf] * 3
        for mesh, local in tpl.parts:
            for v in mesh.vertices:
                w = local @ v.co
                for k in range(3):
                    lo[k] = min(lo[k], w[k])
                    hi[k] = max(hi[k], w[k])
        size = [hi[k] - lo[k] for k in range(3)]
        nominal = e.get("nominal_size_m") or size
        ratio = max((size[k] / nominal[k]) if nominal[k] > 1e-6 else 1.0 for k in range(3))
        if ratio <= 1.0 + tolerance:
            continue
        eff = e.get("bounds_with_effects") or {}
        eff_size = ([float(eff["max"][k]) - float(eff["min"][k]) for k in range(3)]
                    if eff.get("max") and eff.get("min") else None)
        row = {"id": e["id"], "dataset_kind": e.get("dataset_kind"),
               "imported_size_m": [round(v, 3) for v in size],
               "nominal_size_m": [round(float(v), 3) for v in nominal],
               "ratio": round(ratio, 2)}
        if eff_size and all(abs(size[k] - eff_size[k]) <= 0.05 for k in range(3)):
            row["explained_by"] = ("bounds_with_effects: the extra extent is the modelled light "
                                   "cone, which the daylight pass makes transparent")
            with_effects.append(row)
        else:
            bad.append(row)
    return {"checked": len(entries), "tolerance": tolerance,
            "bad": sorted(bad, key=lambda r: -r["ratio"]),
            "with_effects": sorted(with_effects, key=lambda r: -r["ratio"]),
            "unloadable": unloadable}


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
            col: bpy.types.Collection | None = None,
            suppress_bins_set: set[int] | None = None) -> dict:
    """Instance facade kit placements inside ``radius_m``, nearest first, under a triangle cap.

    ``suppress_bins_set`` drops the placements that belong to buildings a landmark model replaces.
    It has to be the same set the shell loader used: with the shell gone and its kit left behind,
    the frame shows a wall of windows and air-conditioners floating where the building was, which
    is exactly what the first Bethesda Terrace frame showed after shell suppression was added.
    """
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
    suppressed_kit = 0
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
        if suppress_bins_set and int(r["bin"]) in suppress_bins_set:
            suppressed_kit += 1
            continue
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
        # ``yaw_deg`` is the wall run's outward normal as an angle counter-clockwise from east
        # (pipeline/nycsim_pipeline/facade/placements.py::_yaw).  Every kit piece is authored
        # with its wall plane at y = 0 and ``into_building = +Y``, so its outward direction is
        # local -Y; aligning -Y with the normal is a rotation of yaw + 90 deg about Z.
        # ``scale`` is the along-run stretch relative to the piece's nominal width (1.0 for
        # point pieces), so it applies to local X only -- a uniform scale would make a stretched
        # cornice proportionally taller and thicker as well.
        m = (Matrix.Translation((float(r["x"]), float(r["y"]), float(r["z"])))
             @ Euler((0.0, 0.0, math.radians(float(r["yaw_deg"]) + 90.0))).to_matrix().to_4x4()
             @ Matrix.Diagonal((s, 1.0, 1.0, 1.0)))
        tpl.instance(f"kit_{kid}_{placed}", m, col or bpy.context.scene.collection)
        placed += 1
        tris += tpl.triangles
        cat = e.get("category", "?")
        per_cat[cat] = per_cat.get(cat, 0) + 1
    return {"records_in_range": int(a.size), "placed": placed, "triangles": tris, "capped": capped,
            "suppressed_with_landmark_shells": suppressed_kit,
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
    pavement: dict = field(default_factory=dict)
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
                "pavement": self.pavement, "buildings": self.buildings, "landmarks": self.landmarks,
                "props": self.props, "kit": self.kit}


def build_scene(cx: float, cy: float, radius_m: float, *, prop_radius_m: float | None = None,
                kit_radius_m: float | None = None, triangle_budget: int = 4_500_000,
                terrain_max_side: int = 420, lod0_radius_m: float = 1200.0,
                with_props: bool = True, with_kit: bool = True, pavement_radius_m: float = 900.0,
                leaf_off: bool = False) -> tuple[SceneReport, TerrainSampler]:
    """Reset the scene and populate it from every artefact available around (cx, cy)."""
    import time
    t0 = time.time()
    nb.reset_scene()
    scene_col = bpy.context.scene.collection
    c_terrain = nb.collection("terrain", scene_col)
    c_pave = nb.collection("pavement", scene_col)
    c_build = nb.collection("buildings", scene_col)
    c_landmark = nb.collection("landmarks", scene_col)
    c_props = nb.collection("props", scene_col)
    c_kit = nb.collection("kit", scene_col)

    sampler = TerrainSampler()
    rep = SceneReport(centre_tm=(cx, cy), radius_m=radius_m)
    rep.terrain = build_terrain(sampler, cx, cy, radius_m, max_side=terrain_max_side, col=c_terrain)
    rep.pavement = add_pavement(cx, cy, min(radius_m, pavement_radius_m), sampler, col=c_pave)
    # A landmark model and the tile shell of the same building are two versions of one object.
    # The catalogue names the BINs each model was built from, so those shells are removed from the
    # merged per-material meshes before anything else is placed.
    rep.buildings = add_buildings(cx, cy, radius_m, lod0_radius_m=lod0_radius_m,
                                  triangle_budget=int(triangle_budget * 0.78), col=c_build,
                                  suppress_landmark_bins=landmark_bins())

    lib = AssetLibrary()
    rep.landmarks = add_landmarks(lib, cx, cy, radius_m, col=c_landmark)

    used = (int(rep.terrain.get("triangles", 0)) + int(rep.pavement.get("triangles", 0))
            + rep.buildings["triangles"] + rep.landmarks["triangles"])
    left = max(0, triangle_budget - used)
    if with_props:
        rep.props = add_props(lib, cx, cy, prop_radius_m if prop_radius_m is not None else min(radius_m, 400.0),
                              sampler=sampler, triangle_budget=int(left * 0.35), leaf_off=leaf_off,
                              col=c_props)
    else:
        rep.props = {"placed": 0, "reason": "disabled"}
    left = max(0, left - int(rep.props.get("triangles", 0)))
    if with_kit:
        rep.kit = add_kit(lib, cx, cy, kit_radius_m if kit_radius_m is not None else min(radius_m, 200.0),
                          triangle_budget=left, col=c_kit, suppress_bins_set=landmark_bins())
    else:
        rep.kit = {"placed": 0, "reason": "disabled"}

    bpy.context.view_layer.update()
    rep.triangles = (int(rep.terrain.get("triangles", 0)) + int(rep.pavement.get("triangles", 0))
                     + rep.buildings["triangles"]
                     + rep.landmarks["triangles"] + int(rep.props.get("triangles", 0))
                     + int(rep.kit.get("triangles", 0)))
    rep.seconds = time.time() - t0
    LOG.info("scene built: %d triangles in %.1f s (%d tiles, %d landmarks, %d pavement polys, "
             "%d props, %d kit)", rep.triangles, rep.seconds, rep.buildings["tiles_imported"],
             rep.landmarks["placed"], rep.pavement.get("placed", 0), rep.props.get("placed", 0),
             rep.kit.get("placed", 0))
    return rep, sampler


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, default=40.7526)
    ap.add_argument("--lon", type=float, default=-73.9814)
    ap.add_argument("--radius", type=float, default=600.0)
    ap.add_argument("--prop-radius", type=float, default=None)
    ap.add_argument("--kit-radius", type=float, default=None)
    ap.add_argument("--triangle-budget", type=int, default=4_500_000)
    ap.add_argument("--no-props", action="store_true")
    ap.add_argument("--no-kit", action="store_true")
    ap.add_argument("--json", default=None, help="write the scene report here ('-' for stdout)")
    ap.add_argument("--audit-props", action="store_true",
                    help="measure every prop asset against its catalogue size and exit")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if a.audit_props:
        report = audit_prop_assets()
        print(json.dumps(report, indent=1, sort_keys=True))
        return 1 if report.get("bad") or report.get("unloadable") else 0
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
