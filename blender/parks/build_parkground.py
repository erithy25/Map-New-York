#!/usr/bin/env python3
"""Build the ground under the city's open space for one tile as glTF 2.0.

    python3 blender/parks/build_parkground.py --tile t_-3_7
    python3 blender/parks/build_parkground.py --all --workers 2

Output per tile:

* ``blender_out/tiles/{tile}/tile_parkground.glb`` -- one mesh per (kind, surface), tile-local in
  X/Y and absolute NAVD88 in Z, the same convention as the shells, the pavement and the structures.
* ``blender_out/tiles/{tile}/parkground_manifest.json``.

Why this stage exists
---------------------
``data/processed/parks/surfaces.parquet`` holds 27,493 surveyed open-space polygons -- 130 km² of
park boundary, greenstreet, court, ball field, pool, running track, skating rink, cemetery and
vacant ground -- and until it existed the terrain was the only thing under a park. Central Park,
Prospect Park, every schoolyard court and every ball field was drawn as the same material as a
vacant lot.

It also fills three entries of the friction model that nothing could reach. ``SurfaceClass``
declares ``Grass``, ``Water`` and ``Ice``; before this stage **no surface in the world produced any
of them**, so three rows of the tyre model were unreachable. A lawn, a pool and a skating rink are
what reach them.

Where the pavement already draws
--------------------------------
A park path is a planimetric sidewalk or plaza polygon, and the pavement stage draws it at +0.25 m.
Park ground at +0.03 m under the same place would put a 22 cm kerb around every path in every park,
which no park has. So the tile's own pavement is subtracted from the park polygons first: one
surface per place, and the one that stays is the one the pavement survey traced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "roads"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import pvlib  # noqa: E402

LOG = logging.getLogger("nycsim.parks")

PROCESSED = REPO_ROOT / "data" / "processed"
SURFACES = PROCESSED / "parks" / "surfaces.parquet"
PAVEMENT_DIR = PROCESSED / "roads" / "pavement"
TILES_DATA = PROCESSED / "tiles"
OUT_ROOT = REPO_ROOT / "blender_out" / "tiles"
GLB_NAME = "tile_parkground.glb"
MANIFEST_NAME = "parkground_manifest.json"
SCHEMA_VERSION = 1
TILE_SIZE_M = 1000.0

#: Grid cell each kind is cut on, metres. A lawn is flat and huge; a court is small and its edge is
#: the thing you see. Chosen per kind rather than globally because a 2.5 m cell over 8,471 ha of
#: park ground would be 13 million quads for a surface with nothing on it.
CELL_M = {0: 12.0, 1: 3.0, 2: 2.5, 3: 3.0, 4: 5.0, 5: 12.0, 6: 2.0, 7: 2.0, 8: 2.0, 9: 12.0,
          10: 8.0, 11: 8.0}

#: Longest triangle edge, metres, per kind. Same reasoning.
MAX_EDGE_M = {0: 30.0, 1: 8.0, 2: 6.0, 3: 8.0, 4: 12.0, 5: 30.0, 6: 5.0, 7: 5.0, 8: 5.0, 9: 30.0,
              10: 18.0, 11: 18.0}

#: Draping tolerance, metres, per kind. The ground under a park bends more than a street does and
#: nothing there has a kerb to measure against, so a lawn is draped far looser than a court: at
#: 0.08 m Central Park's own hills subdivided one tile's grass into 286,627 triangles for 60 ha of
#: surface nobody measures to the centimetre. A court, a track and a rink are poured flat and their
#: edge is the thing you look at, so they keep a tight tolerance.
TOL_M = {0: 0.15, 1: 0.10, 2: 0.05, 3: 0.06, 4: 0.10, 5: 0.15, 6: 0.04, 7: 0.05, 8: 0.04,
         9: 0.15, 10: 0.12, 11: 0.09}

MIN_EDGE_M = 1.0
SIMPLIFY_M = 0.05


def parse_tile(tile: str) -> tuple[int, int]:
    _, tx, ty = tile.split("_", 2)
    return int(tx), int(ty)


def _kind_meta():
    from nycsim_pipeline.parks.surfaces import KINDS

    return KINDS


def material_name(kind: int) -> str:
    k = _kind_meta()[int(kind)]
    return f"park_{k['name']}_{k['surface']}"


HYDROGRAPHY = PROCESSED / "water" / "hydrography.parquet"


def load_open_water_union(box):
    """The open-water polygons that reach into this tile, as one geometry, or None.

    A park property polygon is a jurisdiction boundary: Central Park's contains the Lake, the
    Reservoir and the Pond whole, and Prospect Park's its Lake.  Drawn as a ground surface it laid
    lawn over the terrain's water plane, so the Lake behind Bethesda Terrace rendered as grass
    (Stage 55's render sceptic).  The water is subtracted the way the pavement is: one surface per
    place, and the one that stays is the one the hydrography survey traced.
    """
    import pyarrow.parquet as pq
    import shapely

    if not HYDROGRAPHY.is_file():
        return None
    try:
        t = pq.read_table(HYDROGRAPHY, columns=["is_open_water", "geometry"])
    except Exception as exc:  # noqa: BLE001
        LOG.warning("hydrography unreadable: %s", exc)
        return None
    ow = np.asarray(t.column("is_open_water").to_pylist(), dtype=bool)
    geoms = np.asarray(shapely.from_wkb(t.column("geometry").to_pylist()), dtype=object)[ow]
    if geoms.size == 0:
        return None
    hit = shapely.STRtree(geoms).query(box, predicate="intersects")
    if hit.size == 0:
        return None
    return shapely.intersection(shapely.union_all(geoms[hit]), box)


def load_pavement_union(tile: str, box):
    """The tile's own paved polygons, as one geometry, or None."""
    import pyarrow.parquet as pq
    import shapely

    p = PAVEMENT_DIR / f"{tile}.parquet"
    if not p.is_file():
        return None
    try:
        t = pq.read_table(p, columns=["geometry"])
    except Exception as exc:  # noqa: BLE001
        LOG.warning("%s: pavement unreadable: %s", tile, exc)
        return None
    geoms = []
    for blob in t.column("geometry").to_pylist():
        try:
            g = shapely.from_wkb(blob)
        except Exception:  # noqa: BLE001
            continue
        geoms.extend(list(g.geoms) if g.geom_type == "MultiPolygon" else ([g] if g.geom_type == "Polygon" else []))
    if not geoms:
        return None
    return shapely.intersection(shapely.union_all(geoms), box)


def build_tile(tile: str, *, out_root: Path = OUT_ROOT, surfaces: Path = SURFACES,
               cut_pavement: bool = True) -> dict:
    import pyarrow.parquet as pq
    import shapely

    from nycsim_pipeline.terrain.landscape_grid import LandscapeSampler

    t0 = time.perf_counter()
    tx, ty = parse_tile(tile)
    x0, y0 = tx * TILE_SIZE_M, ty * TILE_SIZE_M
    box = shapely.box(x0, y0, x0 + TILE_SIZE_M, y0 + TILE_SIZE_M)
    if not surfaces.is_file():
        raise FileNotFoundError(surfaces)

    table = pq.read_table(surfaces, columns=["kind", "geometry", "area_m2"])
    kinds = np.asarray(table.column("kind"), dtype=np.int16)
    geoms = np.asarray(shapely.from_wkb(table.column("geometry").to_pylist()), dtype=object)
    hit = shapely.STRtree(geoms).query(box, predicate="intersects")

    sampler = LandscapeSampler(TILES_DATA)
    paved = load_pavement_union(tile, box) if cut_pavement else None
    water = load_open_water_union(box)
    meta = _kind_meta()

    slabs: dict[int, pvlib.SlabBuffer] = {}
    per_kind: dict[str, int] = {}
    dropped = {"no_triangulation": 0, "no_terrain": 0, "all_paved": 0, "all_water": 0, "degenerate": 0}
    paved_area = 0.0
    water_area = 0.0
    for h in hit:
        j = int(h)
        k = int(kinds[j])
        g = shapely.intersection(geoms[j], box)
        if g.is_empty:
            continue
        if paved is not None:
            before = g.area
            g = shapely.difference(g, paved)
            paved_area += before - g.area
            if g.is_empty or g.area < 1.0:
                dropped["all_paved"] += 1
                continue
        if water is not None:
            before = g.area
            g = shapely.difference(g, water)
            water_area += before - g.area
            if g.is_empty or g.area < 1.0:
                dropped["all_water"] += 1
                continue
        if SIMPLIFY_M > 0:
            g = shapely.simplify(g, SIMPLIFY_M, preserve_topology=True)
        parts = shapely.get_parts(g) if g.geom_type.startswith("Multi") else [g]
        for poly in parts:
            if poly.geom_type != "Polygon" or poly.area < 1.0 or len(poly.exterior.coords) < 4:
                dropped["degenerate"] += 1
                continue
            pts, tris = pvlib.grid_triangulate(poly, CELL_M[k])
            if len(tris) == 0:
                dropped["no_triangulation"] += 1
                continue
            pts, tris = pvlib.refine_to_terrain(pts, tris, sampler.height, tol_m=TOL_M[k],
                                                min_edge_m=MIN_EDGE_M, max_edge_m=MAX_EDGE_M[k])
            z = sampler.height(pts[:, 0], pts[:, 1])
            if np.isnan(z).all():
                dropped["no_terrain"] += 1
                continue
            if np.isnan(z).any():
                z = np.where(np.isnan(z), float(np.nanmedian(z)), z)
            buf = slabs.setdefault(k, pvlib.SlabBuffer(kind=k, surface=meta[k]["surface_class"]))
            buf.add_polygon(pts - np.array([x0, y0]), z + meta[k]["lift_m"], tris,
                            meta[k]["skirt_m"], road_line=-1)
            per_kind[meta[k]["name"]] = per_kind.get(meta[k]["name"], 0) + 1

    import nycsim_bpy as nb

    nb.reset_scene()
    objects, mesh_stats = [], []
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for k, b in sorted(slabs.items()):
        if not b.faces:
            continue
        pos = np.asarray(b.verts, dtype=np.float64)
        tri = np.asarray(b.faces, dtype=np.int64)
        slot = material_name(k)
        ob = _make_object(f"{tile}_{slot}", pos, tri, np.asarray(b.is_top, dtype=bool),
                          slot, k, meta[k])
        objects.append(ob)
        lo = np.minimum(lo, pos.min(axis=0))
        hi = np.maximum(hi, pos.max(axis=0))
        mesh_stats.append({"mesh": ob.name, "material": slot, "kind": k,
                           "kind_name": meta[k]["name"], "surface": meta[k]["surface"],
                           "surface_class": meta[k]["surface_class"], "polygons": b.polygons,
                           "vertices": len(pos), "triangles": len(tri)})

    out_dir = Path(out_root) / tile
    glb = out_dir / GLB_NAME
    if objects:
        out_dir.mkdir(parents=True, exist_ok=True)
        nb.export_glb(glb, objects=objects, apply_modifiers=False, texcoords=True, tangents=False,
                      export_extras=True, export_normals=False, export_animations=False, extras={
                          "stage": "parks_ground", "tile": tile,
                          "origin_m": [x0, y0, 0.0], "crs": "NYC_TM",
                          "vertical_datum": "NAVD88 metres",
                          "source": "data/processed/parks/surfaces.parquet",
                          "draped_on": "UE landscape grid (505 samples, NYCTerrainImport.cpp)",
                          "pavement_subtracted": bool(paved is not None),
                          "open_water_subtracted": bool(water is not None),
                          "uv": "metres, planar XY in NYC_TM (u = east, v = north)",
                          "surface_class": {m["material"]: m["surface_class"] for m in mesh_stats},
                      })
    elif glb.exists():
        glb.unlink()

    residual = _residual(objects, sampler, x0, y0, meta)
    size = glb.stat().st_size if glb.exists() else 0
    manifest = {
        "schema_version": SCHEMA_VERSION, "stage": "parks_ground", "tile": tile,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": nb.git_commit(), "generator": "blender/parks/build_parkground.py",
        "source": str(surfaces.relative_to(REPO_ROOT)),
        "polygons_in": int(len(hit)), "by_kind": per_kind, "dropped": dropped,
        "pavement_subtracted_m2": round(paved_area, 1),
        "open_water_subtracted_m2": round(water_area, 1),
        "meshes": mesh_stats,
        "triangles": sum(m["triangles"] for m in mesh_stats),
        "vertices": sum(m["vertices"] for m in mesh_stats),
        "bounds_local_m": {"min": _fin(lo), "max": _fin(hi)},
        "origin_m": [x0, y0, 0.0],
        "cell_m": CELL_M, "max_edge_m": MAX_EDGE_M, "tol_m": TOL_M,
        "drape_residual_m": residual,
        "terrain_tiles_missing": sorted(sampler.missing),
        "glb": {"path": _rel(glb) if glb.exists() else "", "bytes": size,
                "sha256": _sha256(glb) if glb.exists() else ""},
        "seconds": {"total": round(time.perf_counter() - t0, 3)},
    }
    if objects:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


#: How many points the draping residual is measured at per tile.
RESIDUAL_SAMPLES = 4000


def _residual(objects, sampler, x0: float, y0: float, meta) -> dict:
    """Two numbers per tile: how well each slab is draped, and whether it stands over the ground.

    They are not the same question and conflating them is easy. The **drape error** is how far the
    triangulated surface sits from the landscape it was interpolated against, and an unbiased
    interpolation is below it half the time by definition. The **clearance** is the shipped top
    minus that landscape, which is what decides whether bare terrain shows through a lawn -- and it
    is the lift that has to cover the drape error for the answer to be no.

    Measuring only the first and calling its sign "pierced" reports 50 % on a surface that is
    perfectly draped, which is what this function did before it was read carefully.

    Sampled on the top faces only; a skirt is vertical by construction. The two kinds that are below
    grade on purpose -- a pool's water surface under its coping, a sunken rink -- are named rather
    than counted.
    """
    import numpy as _np

    xs, ys, tops, lifts, below = [], [], [], [], []
    rng = _np.random.default_rng(0x5041524B)
    for ob in objects:
        me = ob.data
        n = len(me.polygons)
        if n == 0:
            continue
        if ob.get("below_grade"):
            below.append(str(ob.get("kind_name") or ob.name))
            continue
        flags = _np.empty(n, dtype=bool)
        me.attributes["is_top"].data.foreach_get("value", flags)
        idx_top = _np.nonzero(flags)[0]
        if idx_top.size == 0:
            continue
        take = min(idx_top.size, max(1, RESIDUAL_SAMPLES // max(1, len(objects))))
        idx = rng.choice(idx_top, size=take, replace=False)
        nv = len(me.vertices)
        co = _np.empty(nv * 3, dtype=_np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(nv, 3).astype(_np.float64)
        loops = _np.empty(len(me.loops), dtype=_np.int32)
        me.loops.foreach_get("vertex_index", loops)
        tri = loops.reshape(-1, 3)[idx]
        w = rng.random((take, 3))
        w /= w.sum(axis=1, keepdims=True)
        p = (co[tri] * w[:, :, None]).sum(axis=1)
        xs.append(p[:, 0] + x0)
        ys.append(p[:, 1] + y0)
        tops.append(p[:, 2])
        lifts.append(_np.full(take, float(ob.get("lift_m") or 0.0)))
    if not xs:
        return {"below_grade_by_design": sorted(set(below))}
    x = _np.concatenate(xs)
    y = _np.concatenate(ys)
    top = _np.concatenate(tops)
    lift = _np.concatenate(lifts)
    ground = sampler.height(x, y)
    ok = _np.isfinite(ground)
    if not ok.any():
        return {"samples": 0, "below_grade_by_design": sorted(set(below))}
    clearance = top[ok] - ground[ok]
    drape = clearance - lift[ok]
    return {"samples": int(ok.sum()),
            "drape_abs_p99_mm": round(float(_np.percentile(_np.abs(drape), 99)) * 1000.0, 2),
            "drape_median_mm": round(float(_np.median(drape)) * 1000.0, 2),
            "clearance_median_mm": round(float(_np.median(clearance)) * 1000.0, 2),
            "clearance_p01_mm": round(float(_np.percentile(clearance, 1)) * 1000.0, 2),
            "pierced_fraction": round(float(_np.mean(clearance < 0.0)), 5),
            "below_grade_by_design": sorted(set(below))}


def _make_object(name: str, pos: np.ndarray, tri: np.ndarray, is_top: np.ndarray,
                 slot: str, kind: int, meta: dict):
    """Mesh from flat arrays, UVs in metres, one material, an is_top face flag for the residual."""
    import bpy

    import nycsim_bpy as nb

    nv, nt = len(pos), len(tri)
    me = bpy.data.meshes.new(name)
    me.vertices.add(nv)
    me.vertices.foreach_set("co", np.ascontiguousarray(pos, dtype=np.float32).ravel())
    me.loops.add(nt * 3)
    me.loops.foreach_set("vertex_index", np.ascontiguousarray(tri, dtype=np.int32).ravel())
    me.polygons.add(nt)
    me.polygons.foreach_set("loop_start", np.arange(nt, dtype=np.int32) * 3)
    me.polygons.foreach_set("use_smooth", np.ones(nt, dtype=bool))
    me.update()
    uv = pos[tri][:, :, :2].reshape(-1, 2)
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", np.ascontiguousarray(uv, dtype=np.float32).ravel())
    attr = me.attributes.new("is_top", "BOOLEAN", "FACE")
    attr.data.foreach_set("value", np.ascontiguousarray(is_top, dtype=bool))
    me.materials.append(_material(slot, kind))
    ob = bpy.data.objects.new(name, me)
    ob["lift_m"] = meta["lift_m"]
    ob["surface_class"] = meta["surface_class"]
    ob["kind_name"] = meta["name"]
    if meta.get("below_grade"):
        ob["below_grade"] = True
    nb.link(ob)
    return ob


#: Base colour and roughness per kind. Flat colours: these are ground materials the texture library
#: has no entry for yet, and a wrong texture reads worse than an honest colour (DEVIATIONS J38).
_LOOK = {
    0: ((0.19, 0.28, 0.13, 1.0), 0.93),      # park grass
    1: ((0.21, 0.30, 0.15, 1.0), 0.93),      # greenstreet
    2: ((0.20, 0.33, 0.30, 1.0), 0.80),      # hard court, the green/blue acrylic NYC uses
    3: ((0.45, 0.32, 0.22, 1.0), 0.95),      # infield dirt
    4: ((0.20, 0.31, 0.14, 1.0), 0.93),      # grass field
    5: ((0.22, 0.33, 0.15, 1.0), 0.92),      # golf
    6: ((0.10, 0.35, 0.48, 1.0), 0.12),      # pool water
    7: ((0.46, 0.18, 0.14, 1.0), 0.85),      # running track
    8: ((0.72, 0.78, 0.82, 1.0), 0.10),      # ice
    9: ((0.22, 0.29, 0.16, 1.0), 0.93),      # cemetery lawn
    10: ((0.21, 0.29, 0.16, 1.0), 0.92),     # recreation ground
    11: ((0.33, 0.31, 0.26, 1.0), 0.95),     # bare ground
}


def _material(name: str, kind: int):
    import nycsim_bpy as nb

    colour, rough = _LOOK[int(kind)]
    return nb.pbr_material(name, base_color=colour, roughness=rough)


def _fin(v: np.ndarray) -> list:
    return [round(float(x), 4) if math.isfinite(float(x)) else None for x in v]


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
    import bpy

    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)


def available_tiles() -> list[str]:
    import pyarrow.parquet as pq

    if not SURFACES.is_file():
        return []
    t = pq.read_table(SURFACES, columns=["tile"])
    return sorted(set(t.column("tile").to_pylist()),
                  key=lambda s: tuple(int(v) for v in s.split("_")[1:]))


def run_serial(tiles: list[str], args) -> int:
    ok = 0
    for i, tile in enumerate(tiles, 1):
        out = Path(args.out) / tile / GLB_NAME
        if args.skip_existing and out.exists() and (out.parent / MANIFEST_NAME).exists():
            ok += 1
            continue
        try:
            m = build_tile(tile, out_root=Path(args.out), cut_pavement=not args.no_pavement_cut)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("tile %s failed", tile)
            print(f"[{i}/{len(tiles)}] {tile} FAILED: {exc}", flush=True)
            continue
        finally:
            _purge()
        ok += 1
        print(f"[{i}/{len(tiles)}] {tile} polys={m['polygons_in']} tris={m['triangles']} "
              f"bytes={m['glb']['bytes']} paved_cut={m['pavement_subtracted_m2']:.0f}m2 "
              f"t={m['seconds']['total']}s", flush=True)
    return 0 if ok == len(tiles) else 1


def run_parallel(tiles: list[str], args) -> int:
    n = max(1, min(args.workers, 2))
    logdir = Path(args.out) / "_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    procs = []
    for i in range(n):
        chunk = tiles[i::n]
        if not chunk:
            continue
        listfile = logdir / f"parkground_worker{i}.tiles"
        listfile.write_text("\n".join(chunk))
        cmd = ["nice", "-n", str(args.nice), sys.executable, str(Path(__file__).resolve()),
               "--tile-list", str(listfile), "--out", str(args.out)]
        if args.skip_existing:
            cmd.append("--skip-existing")
        if args.no_pavement_cut:
            cmd.append("--no-pavement-cut")
        log = open(logdir / f"parkground_worker{i}.log", "w")
        procs.append((subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT), log))
        print(f"worker {i}: {len(chunk)} tiles -> {logdir / f'parkground_worker{i}.log'}", flush=True)
    rc = 0
    for p, log in procs:
        rc |= p.wait()
        log.close()
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tile")
    g.add_argument("--tiles")
    g.add_argument("--tile-list")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=str(OUT_ROOT))
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--nice", type=int, default=10)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--no-pavement-cut", action="store_true",
                    help="draw park ground under the pavement as well")
    ap.add_argument("--limit", type=int, default=0)
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
        tiles = available_tiles()
    if args.limit:
        tiles = tiles[: args.limit]
    if not tiles:
        print("no tiles", file=sys.stderr)
        return 1
    print(f"{len(tiles)} tile(s)", flush=True)
    return run_parallel(tiles, args) if args.workers > 1 else run_serial(tiles, args)


if __name__ == "__main__":
    sys.exit(main())
