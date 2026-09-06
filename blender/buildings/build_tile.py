#!/usr/bin/env python3
"""Generate the NYCSim building shells for one tile (or the whole city) as glTF 2.0.

    python3 blender/buildings/build_tile.py --tile t_-4_5
    python3 blender/buildings/build_tile.py --all --workers 2 --lod 0,1,2

Output per tile (DATA_CONTRACTS §13, ARCHITECTURE §4.3):

* ``blender_out/tiles/{tile}/tile_buildings.glb`` — one mesh per (LOD, material class) so the draw
  call count per tile is bounded by the number of materials actually used, not by the number of
  buildings.  Walls are extruded from the real ``ground_z`` to the real ``roof_z`` out of the real
  cleaned footprint ring (2 cm snap, exterior CCW, interior rings kept as holes), wall UVs are in
  metres (u along the facade, v = height above grade), and every vertex carries the per-building
  attributes listed in ``ATTR_NAMES`` below.
* ``blender_out/tiles/{tile}/manifest.json`` — counts, triangles, bounds, materials, provenance
  of every inferred attribute, and generation time.

Reading the attributes in Unreal
--------------------------------
Blender exports a mesh attribute whose name starts with ``_`` as a glTF custom vertex attribute
with the name upper-cased, always as ``componentType 5126`` (FLOAT), ``type SCALAR``:

    ``_bin`` -> ``_BIN``, ``_floors`` -> ``_FLOORS``, ...

In UE 5.4 the Interchange glTF pipeline keeps unknown vertex attributes when
``Interchange > glTF > Import Vertex Attributes`` is on; they arrive as float vertex streams named
exactly as above and are read in a material or a Niagara/Nanite custom data slot.  ``_BIN`` is
exact (every NYC BIN < 2^24, so float32 is lossless).  ``lit_seed`` is a uint32 and does *not* fit
a float32 exactly, so it ships as two exact halves:
``lit_seed = _LIT_SEED_HI * 65536 + _LIT_SEED_LO``.
``_FACADE_CLASS == 0`` means "not classified yet" (the facade stage had not written the column when
this tile was built); the engine then falls back to the material-driven shader defaults.
The mesh/node name carries the LOD (``..._LOD1`` / ``..._LOD2``, no suffix = LOD0) and each node
also carries ``extras = {tile, lod, material, material_index, origin_m}``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(_HERE))

import shellgeom as sg  # noqa: E402
import tiledata as td  # noqa: E402

LOG = logging.getLogger("nycsim.buildings.build_tile")

OUT_ROOT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO_ROOT / "blender_out")) / "tiles"
SCHEMA_VERSION = 1

ATTR_NAMES = ("_bin", "_facade_class", "_floors", "_floor_height", "_ground_floor_height",
              "_is_storefront", "_lit_seed_hi", "_lit_seed_lo")
ATTR_MIN = ("_bin",)
# Per-LOD attribute sets.  LOD0 (0-600 m) carries everything the facade kit and shader need; LOD1
# (600-2,500 m) keeps only what the window-grid shader still resolves; LOD2 (2.5-12 km) keeps only
# what the lit-window shader needs.  Measured saving on t_-4_5: 517 KiB of 4,695 KiB.
ATTR_BY_LOD = {
    0: ATTR_NAMES,
    1: ("_bin", "_floors", "_floor_height", "_ground_floor_height", "_lit_seed_hi", "_lit_seed_lo"),
    2: ("_bin", "_lit_seed_hi", "_lit_seed_lo"),
}

# Base colours for the shell materials.  These are *shell* materials: flat PBR, no textures, so the
# .glb stays at shell size (ADR-003).  The engine swaps in the facade master material by name; the
# Cycles verification renders in render_verify.py bind the real AmbientCG PBR sets by the same name.
MAT_COLOR: dict[str, tuple[float, float, float]] = {
    "red_brick": (0.42, 0.16, 0.12), "brown_brick": (0.31, 0.20, 0.15), "tan_brick": (0.62, 0.51, 0.37),
    "white_glazed_brick": (0.80, 0.79, 0.74), "brownstone": (0.34, 0.22, 0.15), "limestone": (0.72, 0.68, 0.58),
    "terracotta": (0.60, 0.33, 0.22), "cast_iron": (0.16, 0.17, 0.17), "glass_curtain": (0.16, 0.22, 0.27),
    "concrete": (0.55, 0.54, 0.51), "stucco": (0.72, 0.68, 0.60), "vinyl_siding": (0.70, 0.70, 0.66),
    "wood_clapboard": (0.60, 0.56, 0.48), "stone_rubble": (0.45, 0.43, 0.39), "metal_panel": (0.48, 0.50, 0.52),
    "granite": (0.40, 0.39, 0.38), "precast": (0.63, 0.62, 0.59), "roof_membrane": (0.30, 0.30, 0.31),
    "tar_roof": (0.13, 0.13, 0.13), "corrugated_metal": (0.45, 0.46, 0.47),
}
MAT_ROUGH: dict[str, float] = {"glass_curtain": 0.12, "cast_iron": 0.45, "metal_panel": 0.38,
                               "corrugated_metal": 0.45, "granite": 0.40, "limestone": 0.65}
MAT_METAL: dict[str, float] = {"glass_curtain": 0.0, "cast_iron": 0.85, "metal_panel": 0.8,
                               "corrugated_metal": 0.8}


# --------------------------------------------------------------------------- geometry accumulation
class Bucket:
    """Per (lod, material) vertex/triangle/uv/attribute accumulator for one tile."""

    __slots__ = ("pos", "tri", "uv", "att", "nv", "nt")

    def __init__(self) -> None:
        self.pos: list[np.ndarray] = []
        self.tri: list[np.ndarray] = []
        self.uv: list[np.ndarray] = []
        self.att: list[np.ndarray] = []
        self.nv = 0
        self.nt = 0

    def add(self, pos: np.ndarray, tri: np.ndarray, uv: np.ndarray, attr_row: np.ndarray) -> None:
        self.pos.append(pos)
        self.tri.append(tri + self.nv)
        self.uv.append(uv)
        self.att.append(np.broadcast_to(attr_row, (len(pos), len(attr_row))))
        self.nv += len(pos)
        self.nt += len(tri)

    def finish(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        return (np.concatenate(self.pos), np.concatenate(self.tri),
                np.concatenate(self.uv), np.concatenate(self.att))


def accumulate(specs, lods, attrs_by_lod) -> tuple[dict[tuple[int, int], Bucket], dict[str, int]]:
    """Build every LOD of every building and sort the triangles into (lod, material) buckets."""
    buckets: dict[tuple[int, int], Bucket] = {}
    stats = {"fallback_flat_cap": 0, "fallback_massing": 0, "open_shells": 0, "buildings": 0}
    for spec in specs:
        rows = {lod: np.array([spec.attrs.get(a[1:], 0.0) for a in attrs_by_lod[lod]], dtype=np.float32)
                for lod in lods}
        stats["buildings"] += 1
        for lod in lods:
            buf = sg.build_shell(spec, lod)
            if buf.fallback == "flat_cap":
                stats["fallback_flat_cap"] += 1
            elif buf.fallback == "massing":
                stats["fallback_massing"] += 1
            if not buf.tris:
                continue
            pos = np.asarray(buf.pos, dtype=np.float64)
            tris = np.asarray(buf.tris, dtype=np.int64)
            uvs = np.asarray(buf.uvs, dtype=np.float32).reshape(-1, 3, 2)
            mats = np.asarray(buf.mats, dtype=np.int32)
            if lod == 0 and not sg.is_closed(len(pos), tris):
                stats["open_shells"] += 1
            for m in np.unique(mats):
                sel = mats == m
                t = tris[sel]
                uniq, inv = np.unique(t, return_inverse=True)
                buckets.setdefault((lod, int(m)), Bucket()).add(
                    pos[uniq], inv.reshape(-1, 3).astype(np.int64), uvs[sel], rows[lod])
    return buckets, stats


# --------------------------------------------------------------------------- Blender assembly
def _material(name: str):
    import bpy

    key = f"NYCSIM_{name}"
    mat = bpy.data.materials.get(key)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    r, g, b = MAT_COLOR.get(name, (0.6, 0.6, 0.6))
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = MAT_ROUGH.get(name, 0.72)
    bsdf.inputs["Metallic"].default_value = MAT_METAL.get(name, 0.0)
    return mat


def _make_object(name: str, pos: np.ndarray, tri: np.ndarray, uv: np.ndarray, att: np.ndarray,
                 attr_names, material_name: str, props: dict):
    import bpy

    nv, nt = len(pos), len(tri)
    me = bpy.data.meshes.new(name)
    me.vertices.add(nv)
    me.vertices.foreach_set("co", np.ascontiguousarray(pos, dtype=np.float32).ravel())
    me.loops.add(nt * 3)
    me.loops.foreach_set("vertex_index", np.ascontiguousarray(tri, dtype=np.int32).ravel())
    me.polygons.add(nt)
    me.polygons.foreach_set("loop_start", (np.arange(nt, dtype=np.int32) * 3))
    # Smooth shading only suppresses the exporter's per-face vertex split; NORMAL is not exported,
    # so the glTF client computes flat normals from the winding (glTF 2.0 spec, 3.7.2.1).
    me.polygons.foreach_set("use_smooth", np.ones(nt, dtype=bool))
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", np.ascontiguousarray(uv, dtype=np.float32).ravel())
    for j, aname in enumerate(attr_names):
        a = me.attributes.new(name=aname, type="FLOAT", domain="POINT")
        a.data.foreach_set("value", np.ascontiguousarray(att[:, j], dtype=np.float32))
    me.materials.append(_material(material_name))
    ob = bpy.data.objects.new(name, me)
    for k, v in props.items():
        ob[k] = v
    bpy.context.scene.collection.objects.link(ob)
    return ob


def export_glb(path: Path, objects, extras: dict, *, export_normals: bool = False) -> Path:
    """glTF export with custom vertex attributes enabled.

    ``blender/common/nycsim_bpy.export_glb`` (owned by the kit agent) does not pass
    ``export_attributes``, which this stage requires, so the export call is repeated here with the
    identical ``asset.extras.nycsim`` contract of DATA_CONTRACTS §13.  See REPORT.md: the requested
    foundation change is a single ``export_attributes: bool = False`` passthrough.
    """
    import bpy
    import nycsim_bpy as nb

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"schema_version": nb.SCHEMA_VERSION, "generator_script": "blender/buildings/build_tile.py",
            "git_commit": nb.git_commit(), "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "units": "metres", "up_axis_blender": "Z"}
    meta.update(extras)
    bpy.context.scene["nycsim"] = json.dumps(meta)
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
        export_apply=False, export_texcoords=True, export_normals=export_normals, export_tangents=False,
        export_materials="EXPORT", export_image_format="NONE", export_attributes=True,
        export_animations=False, export_extras=True, export_skins=False, export_morph=False,
        export_cameras=False, export_lights=False)
    if not path.exists() or path.stat().st_size < 100:
        raise RuntimeError(f"glTF export produced nothing: {path}")
    return path


# --------------------------------------------------------------------------- per-tile driver
def build_tile(tile: str, *, out_root: Path = OUT_ROOT, lods=(0, 1, 2), attrs_mode: str = "full",
               ridge_mode: str = "clamp", roof_attrs=None) -> dict:
    import bpy
    import nycsim_bpy as nb

    t0 = time.perf_counter()
    if attrs_mode == "full":
        attrs_by_lod = {lod: list(ATTR_BY_LOD[lod]) for lod in lods}
    else:
        attrs_by_lod = {lod: list(ATTR_MIN) for lod in lods}
    attr_names = attrs_by_lod[0]
    load = td.load_tile(tile, roof_attrs=roof_attrs, ridge_mode=ridge_mode)
    t_load = time.perf_counter() - t0

    t1 = time.perf_counter()
    buckets, stats = accumulate(load.specs, lods, attrs_by_lod)
    t_geom = time.perf_counter() - t1

    t2 = time.perf_counter()
    nb.reset_scene()
    objects = []
    mat_stats: dict[str, dict] = {}
    lod_tris = {lod: 0 for lod in lods}
    lod_verts = {lod: 0 for lod in lods}
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for (lod, m), bucket in sorted(buckets.items()):
        pos, tri, uv, att = bucket.finish()
        mname = td.material_name(m)
        name = f"{tile}_{mname}" + ("" if lod == 0 else f"_LOD{lod}")
        ob = _make_object(name, pos, tri, uv, att, attrs_by_lod[lod], mname,
                          {"tile": tile, "lod": lod, "material": mname, "material_index": int(m),
                           "origin_m": [load.x0, load.y0, 0.0]})
        objects.append(ob)
        lod_tris[lod] += len(tri)
        lod_verts[lod] += len(pos)
        if lod == 0:
            lo = np.minimum(lo, pos.min(axis=0))
            hi = np.maximum(hi, pos.max(axis=0))
            rec = mat_stats.setdefault(mname, {"index": int(m), "triangles": 0, "vertices": 0, "objects": 0})
            rec["triangles"] += len(tri)
            rec["vertices"] += len(pos)
            rec["objects"] += 1
    t_mesh = time.perf_counter() - t2

    out_dir = Path(out_root) / tile
    glb = out_dir / "tile_buildings.glb"
    t3 = time.perf_counter()
    if objects:
        export_glb(glb, objects, {
            "stage": "buildings", "tile": tile, "origin_m": [load.x0, load.y0, 0.0],
            "crs": "NYC_TM", "vertical_datum": "NAVD88 metres",
            "lods": sorted(lods), "lod_suffix": {"0": "", "1": "_LOD1", "2": "_LOD2"},
            "attributes": {str(k): v for k, v in attrs_by_lod.items()},
            "attribute_notes": {
                "_BIN": "float32, exact (BIN < 2^24)",
                "_LIT_SEED": "lit_seed = _LIT_SEED_HI * 65536 + _LIT_SEED_LO (uint32 does not fit float32)",
                "_FACADE_CLASS": "0 = not classified yet; use the material fallback",
                "uv": "metres; u = arc length along the facade from the primary-facade edge, v = height above ground_z",
            },
            "ridge_mode": ridge_mode,
        })
    elif glb.exists():
        glb.unlink()
    t_export = time.perf_counter() - t3

    size = glb.stat().st_size if glb.exists() else 0
    sha = _sha256(glb) if glb.exists() else ""
    total = time.perf_counter() - t0
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "buildings_mesh",
        "tile": tile,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": nb.git_commit(),
        "generator": "blender/buildings/build_tile.py",
        "buildings": {"rows_in": load.rows_in, "solids": len(load.specs),
                      "dropped_empty_footprint": load.dropped,
                      "fallback_flat_cap": stats["fallback_flat_cap"],
                      "fallback_massing": stats["fallback_massing"],
                      "open_shells_lod0": stats["open_shells"]},
        "triangles": {f"lod{lod}": int(lod_tris[lod]) for lod in sorted(lods)},
        "vertices": {f"lod{lod}": int(lod_verts[lod]) for lod in sorted(lods)},
        "lod_ratio": {f"lod{lod}": (round(lod_tris[lod] / lod_tris[0], 4) if lod_tris.get(0) else None)
                      for lod in sorted(lods) if lod != 0},
        "bounds_local_m": {"min": _fin(lo), "max": _fin(hi)},
        "bounds_world_m": {"min": _shift(lo, load.x0, load.y0), "max": _shift(hi, load.x0, load.y0)},
        "origin_m": [load.x0, load.y0, 0.0],
        "materials": mat_stats,
        "sources": load.sources,
        "ridge_mode": ridge_mode,
        "attributes": {str(k): v for k, v in attrs_by_lod.items()},
        "glb": {"path": _rel(glb) if glb.exists() else "",
                "bytes": size, "sha256": sha,
                "bytes_per_building": round(size / max(len(load.specs), 1), 1)},
        "seconds": {"total": round(total, 3), "load": round(t_load, 3), "geometry": round(t_geom, 3),
                    "mesh": round(t_mesh, 3), "export": round(t_export, 3)},
    }
    td.write_json(out_dir / "manifest.json", manifest)
    return manifest


def _fin(v: np.ndarray) -> list[float]:
    return [round(float(x), 4) if math.isfinite(float(x)) else None for x in v]


def _shift(v: np.ndarray, x0: float, y0: float) -> list[float]:
    if not math.isfinite(float(v[0])):
        return [None, None, None]
    return [round(float(v[0]) + x0, 4), round(float(v[1]) + y0, 4), round(float(v[2]), 4)]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _purge() -> None:
    """Free the Blender data-blocks of the tile that was just exported (bounded RSS over 920 tiles)."""
    import bpy

    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)


# --------------------------------------------------------------------------- CLI
def _parse_lods(s: str) -> tuple[int, ...]:
    out = sorted({int(x) for x in s.replace(" ", "").split(",") if x != ""})
    for v in out:
        if v not in (0, 1, 2):
            raise argparse.ArgumentTypeError(f"unknown LOD {v} (expected 0, 1 or 2)")
    if 0 not in out:
        raise argparse.ArgumentTypeError("LOD 0 is required (LOD1/LOD2 ratios are measured against it)")
    return tuple(out)


def run_serial(tiles: list[str], args) -> int:
    roof_attrs = td.load_roof_attrs()
    ok = 0
    for i, tile in enumerate(tiles, 1):
        out = Path(args.out) / tile / "tile_buildings.glb"
        if args.skip_existing and out.exists() and (out.parent / "manifest.json").exists():
            print(f"[{i}/{len(tiles)}] {tile} skipped (exists)", flush=True)
            ok += 1
            continue
        try:
            m = build_tile(tile, out_root=Path(args.out), lods=args.lod, attrs_mode=args.attrs,
                           ridge_mode=args.ridge_mode, roof_attrs=roof_attrs)
        except Exception as exc:
            LOG.exception("tile %s failed", tile)
            print(f"[{i}/{len(tiles)}] {tile} FAILED: {exc}", flush=True)
            continue
        finally:
            _purge()
        ok += 1
        print(f"[{i}/{len(tiles)}] {tile} buildings={m['buildings']['solids']} "
              f"tris={m['triangles'].get('lod0', 0)} bytes={m['glb']['bytes']} "
              f"t={m['seconds']['total']}s", flush=True)
    return 0 if ok == len(tiles) else 1


def run_parallel(tiles: list[str], args) -> int:
    n = max(1, min(args.workers, 2))          # resource etiquette: 4 vCPU shared, never more than 2
    chunks: list[list[str]] = [tiles[i::n] for i in range(n)]
    procs = []
    logdir = Path(args.out).parent / "_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue
        listfile = logdir / f"worker{i}.tiles"
        listfile.write_text("\n".join(chunk))
        cmd = ["nice", "-n", str(args.nice), sys.executable, str(Path(__file__).resolve()),
               "--tile-list", str(listfile), "--out", str(args.out),
               "--lod", ",".join(str(v) for v in args.lod), "--attrs", args.attrs,
               "--ridge-mode", args.ridge_mode]
        if args.skip_existing:
            cmd.append("--skip-existing")
        log = open(logdir / f"worker{i}.log", "w")
        procs.append((i, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT), log))
        print(f"worker {i}: {len(chunk)} tiles -> {logdir / f'worker{i}.log'}", flush=True)
    rc = 0
    for i, p, log in procs:
        rc |= p.wait()
        log.close()
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tile", help="single tile name, e.g. t_-4_5")
    g.add_argument("--tiles", help="comma separated tile names")
    g.add_argument("--tile-list", help="file with one tile name per line")
    g.add_argument("--all", action="store_true", help="every tile under data/processed/tiles")
    ap.add_argument("--out", default=str(OUT_ROOT), help="output root (default blender_out/tiles)")
    ap.add_argument("--lod", type=_parse_lods, default=(0, 1, 2), help="LODs to emit, default 0,1,2")
    ap.add_argument("--workers", type=int, default=1, help="parallel Blender processes (max 2)")
    ap.add_argument("--nice", type=int, default=10)
    ap.add_argument("--attrs", choices=("full", "min"), default="full",
                    help="full = all 8 per-building vertex attributes, min = _bin only")
    ap.add_argument("--ridge-mode", choices=("clamp", "adr013"), default="clamp",
                    help="clamp: pitched ridge at roof_z (mesh height == height column). "
                         "adr013: ridge above the LiDAR plane per ADR-013 §5")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="process at most N tiles (debugging)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.tile:
        tiles = [args.tile]
    elif args.tiles:
        tiles = [t for t in args.tiles.split(",") if t]
    elif args.tile_list:
        tiles = [t.strip() for t in Path(args.tile_list).read_text().split("\n") if t.strip()]
    else:
        tiles = td.available_tiles()
    if args.limit:
        tiles = tiles[: args.limit]
    if not tiles:
        print("no tiles to build", file=sys.stderr)
        return 2

    if args.workers > 1 and len(tiles) > 1:
        return run_parallel(tiles, args)
    if args.nice and args.tile_list:
        try:
            os.nice(0)
        except OSError:
            pass
    return run_serial(tiles, args)


if __name__ == "__main__":
    raise SystemExit(main())
