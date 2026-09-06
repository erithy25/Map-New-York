#!/usr/bin/env python3
"""Cycles CPU verification renders of the exported building shells (ADR-012).

    python3 blender/buildings/render_verify.py --views all
    python3 blender/buildings/render_verify.py --views midtown_aerial --samples 24

Every view **imports the exported ``.glb`` back into Blender** rather than rebuilding the geometry,
so what is rendered is exactly the file the engine will import.  LOD1/LOD2 objects are hidden, the
flat shell materials are swapped for the real AmbientCG PBR sets by material name
(``blender/common/textures.py``), and a ground surface is interpolated from the buildings' own
LiDAR ``ground_z`` values so that "floating" or "sunk" buildings show up immediately.

Views (written to ``docs/verification/buildings_mesh/``):

* ``midtown_aerial``     — oblique aerial over the Empire State Building tile.
* ``midtown_avenue``     — street level looking north up Sixth Avenue between 33rd and 38th.
* ``park_slope_block``   — street level on a Park Slope brownstone block.
* ``queens_houses``      — street level on a Bayside one/two-family block (roof shapes).
* ``skyline_brooklyn``   — the Manhattan skyline from the Brooklyn Heights Promenade, built from
  the merged L2 cells so the whole island is in frame.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import shapely

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
sys.path.insert(0, str(_HERE))

import tiledata as td  # noqa: E402

LOG = logging.getLogger("nycsim.buildings.render")

OUT_DIR = REPO_ROOT / "docs" / "verification" / "buildings_mesh"
_FETCH_TEXTURES = os.environ.get("NYCSIM_TEXTURES_FETCH", "0") == "1"
TILES_OUT = REPO_ROOT / "blender_out" / "tiles"

# Views in NYC_TM metres (x east, y north).  ``cam_agl`` / ``target_agl`` are heights above the
# local grade, resolved from the nearest real building ``ground_z`` (LiDAR) at render time, because
# NAVD88 grade in these places ranges from 3 m (Brooklyn waterfront) to 25 m (Bayside).
VIEWS: dict[str, dict] = {
    "midtown_aerial": {
        "tiles": ["t_-4_5", "t_-4_4", "t_-3_5", "t_-3_4", "t_-4_6", "t_-3_6"],
        "cam": (-3620.0, 4260.0), "cam_z": 640.0,
        "target": (-3011.6, 5379.8), "target_z": 170.0,
        "fov": 44.0, "sun_az": 155.0, "sun_el": 44.0, "size": (1600, 900),
        "title": "Midtown aerial over the Empire State Building (t_-4_5 and neighbours)",
    },
    "midtown_avenue": {
        "tiles": ["t_-4_5", "t_-3_5", "t_-4_6", "t_-3_6"],
        "cam": (-3209.3, 5375.4), "cam_agl": 1.7, "cam_open": 70.0,   # Sixth Ave at West 33rd St
        "target": (-2960.0, 5810.0), "target_agl": 150.0, "target_open": 70.0,  # ~500 m up the avenue
        "fov": 60.0, "sun_az": 195.0, "sun_el": 34.0, "size": (1600, 900),
        "title": "Sixth Avenue looking north from West 33rd Street",
    },
    "park_slope_block": {
        "tiles": ["t_-3_-4", "t_-3_-3", "t_-2_-4"],
        "cam": (-2400.0, -2960.0), "cam_agl": 26.0,    # above Carroll St near Seventh Avenue
        "target": (-2646.5, -3153.3), "target_agl": 6.0,   # towards Eighth Avenue
        "fov": 52.0, "sun_az": 210.0, "sun_el": 36.0, "size": (1600, 900),
        "title": "Park Slope brownstone rows, Carroll Street towards Eighth Avenue (low oblique)",
    },
    "queens_houses": {
        "tiles": ["t_14_6"],
        "cam": (14960.0, 6620.0), "cam_agl": 48.0,     # low oblique over the Bayside blocks
        "target": (14600.0, 6900.0), "target_agl": 4.0,
        "fov": 52.0, "sun_az": 200.0, "sun_el": 44.0, "size": (1600, 900),
        "title": "Bayside one- and two-family houses: gable, hip and shed roofs (t_14_6)",
    },
    "skyline_brooklyn": {
        "merged": {"level": 2, "cells": [(-2, 0), (-2, 1), (-1, 0), (-1, 1), (-2, -1), (-1, -1)]},
        "cam": (-4183.8, -431.9), "cam_z": 22.0,      # Brooklyn Heights Promenade deck
        "target": (-5154.9, 823.5), "target_z": 150.0,     # Lower Manhattan, Wall Street
        "water": True,                                      # the East River really is in this shot
        "fov": 46.0, "sun_az": 240.0, "sun_el": 22.0, "size": (1600, 900),
        "title": "Manhattan skyline from the Brooklyn Heights Promenade (merged L2 cells)",
    },
}


def _ground_z_at(x: float, y: float) -> float:
    """Local grade from the nearest real building ``ground_z`` (LiDAR) in the tile containing (x, y)."""
    import pandas as pd
    from nycsim_pipeline.tiling import tile_of

    best = (math.inf, 0.0)
    for dx in (0.0, -400.0, 400.0):
        for dy in (0.0, -400.0, 400.0):
            tile = tile_of(x + dx, y + dy).name
            p = td.tile_path(tile)
            if not p.exists():
                continue
            df = pd.read_parquet(p, columns=["centroid_x", "centroid_y", "ground_z"])
            d = np.hypot(df["centroid_x"].to_numpy() - x, df["centroid_y"].to_numpy() - y)
            k = int(d.argmin())
            if d[k] < best[0]:
                best = (float(d[k]), float(df["ground_z"].to_numpy()[k]))
    if not math.isfinite(best[0]):
        raise RuntimeError(f"no building near ({x:.0f}, {y:.0f}) to sample the grade from")
    return best[1]


def _open_point(x: float, y: float, radius: float = 70.0, step: float = 4.0) -> tuple[float, float]:
    """Most open point within ``radius`` of (x, y): the roadway, not the inside of a building.

    Street-level cameras have to stand in the street.  Placing them from a hand-typed latitude and
    longitude puts them inside a building often enough that it is worth solving properly: sample a
    grid, measure the distance to the nearest real footprint with an STRtree, and take the maximum
    (ties broken towards the requested point).
    """
    import pandas as pd
    from nycsim_pipeline.tiling import tiles_in_bbox

    polys = []
    for tile in tiles_in_bbox(x - radius - 60, y - radius - 60, x + radius + 60, y + radius + 60):
        p = td.tile_path(tile.name)
        if p.exists():
            df = pd.read_parquet(p, columns=["footprint"])
            polys.append(shapely.from_wkb(df["footprint"].to_numpy()))
    if not polys:
        return x, y
    geoms = np.concatenate(polys)
    tree = shapely.STRtree(geoms)
    gx = np.arange(x - radius, x + radius + step, step)
    gy = np.arange(y - radius, y + radius + step, step)
    gxx, gyy = np.meshgrid(gx, gy)
    cand = np.column_stack([gxx.ravel(), gyy.ravel()])
    keep = np.hypot(cand[:, 0] - x, cand[:, 1] - y) <= radius
    cand = cand[keep]
    pts = shapely.points(cand)
    dist = shapely.distance(pts, geoms[tree.nearest(pts)])
    score = dist - 0.02 * np.hypot(cand[:, 0] - x, cand[:, 1] - y)
    k = int(np.argmax(score))
    return float(cand[k, 0]), float(cand[k, 1])


def _resolve_z(spec: dict, key: str) -> tuple[float, float, float]:
    x, y = spec[key]
    if spec.get(f"{key}_open"):
        x, y = _open_point(x, y, float(spec[f"{key}_open"]))
    if f"{key}_z" in spec:
        return x, y, float(spec[f"{key}_z"])
    return x, y, _ground_z_at(x, y) + float(spec[f"{key}_agl"])


# --------------------------------------------------------------------------- scene helpers
def _import_glb(path: Path) -> list:
    import bpy

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def _place(objects, origin_m) -> None:
    """glTF is exported Y-up in tile-local metres; put the imported objects back in world NYC_TM."""
    from mathutils import Matrix

    x0, y0 = float(origin_m[0]), float(origin_m[1])
    for ob in objects:
        if ob.parent is None:
            ob.matrix_world = Matrix.Translation((x0, y0, 0.0)) @ ob.matrix_world


def _textured_material(name: str, resolution: str = "2K"):
    """Rebuild the shell material with the real CC0 PBR set of the same name, if available."""
    import bpy
    import nycsim_bpy as nb
    import textures as tx

    key = f"VERIFY_{name}"
    mat = bpy.data.materials.get(key)
    if mat is not None:
        return mat
    tex = None
    uv_scale = 3.0
    try:
        rec = tx.resolve(name)
        uv_scale = float(rec.get("physical_size_m") or 3.0)
        have = tx._existing_set(rec["asset_id"], resolution)
        if have:
            tex = have
        elif _FETCH_TEXTURES:
            tex = tx.get_texture_set(name, resolution)
        else:
            LOG.info("texture set for %s not on disk; using flat colour "
                     "(set NYCSIM_TEXTURES_FETCH=1 to download)", name)
    except Exception as exc:
        LOG.info("no texture set for %s (%s); using flat colour", name, exc)
    import build_tile as bt

    r, g, b = bt.MAT_COLOR.get(name, (0.6, 0.6, 0.6))
    keep = {k: v for k, v in (tex or {}).items() if k in ("color", "roughness", "normal", "metallic")}
    return nb.pbr_material(key, base_color=(r, g, b, 1.0), roughness=bt.MAT_ROUGH.get(name, 0.72),
                           metallic=bt.MAT_METAL.get(name, 0.0), textures=keep or None,
                           uv_scale_m=uv_scale)


def _swap_materials(objects, textured: bool) -> list[str]:
    used = []
    for ob in objects:
        if ob.type != "MESH":
            continue
        for slot in ob.material_slots:
            if slot.material is None:
                continue
            name = slot.material.name.replace("NYCSIM_", "").split(".")[0]
            used.append(name)
            if textured:
                slot.material = _textured_material(name)
    return sorted(set(used))


def _hide_lods(objects, keep_lod: int = 0) -> None:
    for ob in objects:
        lod = 0
        if ob.name.endswith("_LOD1") or "_LOD1" in ob.name:
            lod = 1
        elif ob.name.endswith("_LOD2") or "_LOD2" in ob.name:
            lod = 2
        if lod != keep_lod:
            ob.hide_render = True
            ob.hide_viewport = True


def _water_plane(level_m: float = 0.0, half_size: float = 30000.0):
    """Flat water at 0.0 m NAVD88 for the harbour views (DATA_CONTRACTS §4 water_level_m).

    The water stage has not produced ``water/hydrography.parquet`` geometry yet; this is a plain
    plane used only inside the verification renders, never exported.
    """
    import bpy
    import nycsim_bpy as nb

    me = bpy.data.meshes.new("verify_water")
    me.from_pydata([(-half_size, -half_size, level_m), (half_size, -half_size, level_m),
                    (half_size, half_size, level_m), (-half_size, half_size, level_m)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("verify_water", me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(nb.pbr_material("VERIFY_water", base_color=(0.03, 0.06, 0.09, 1.0),
                                        roughness=0.16, metallic=0.0))
    return ob


def _ground_mesh(tiles: list[str], pad: float = 250.0, step: float = 12.0):
    """Approximate terrain from the buildings' own LiDAR ground elevations.

    The terrain stage has not written ``tiles/{tile}/terrain.png`` yet, and rendering the shells
    over a single flat plane would fake the very defect these renders exist to catch.  Nearest
    building ``ground_z`` (a real LiDAR measurement per footprint) reproduces the local grade to
    well under a metre in built-up areas, so a building sitting proud of or sunk into this surface
    is a real geometry bug.
    """
    import bpy
    import pandas as pd

    xs, ys, zs = [], [], []
    for t in tiles:
        p = td.tile_path(t)
        if not p.exists():
            continue
        df = pd.read_parquet(p, columns=["centroid_x", "centroid_y", "ground_z"])
        xs.append(df["centroid_x"].to_numpy())
        ys.append(df["centroid_y"].to_numpy())
        zs.append(df["ground_z"].to_numpy())
    if not xs:
        return None
    px = np.concatenate(xs)
    py = np.concatenate(ys)
    pz = np.concatenate(zs).astype(np.float64)
    x0, x1 = px.min() - pad, px.max() + pad
    y0, y1 = py.min() - pad, py.max() + pad
    nx = max(2, int((x1 - x0) / step) + 1)
    ny = max(2, int((y1 - y0) / step) + 1)
    gx = np.linspace(x0, x1, nx)
    gy = np.linspace(y0, y1, ny)
    from scipy.spatial import cKDTree

    tree = cKDTree(np.column_stack([px, py]))
    grid = np.column_stack([np.repeat(gx, ny), np.tile(gy, nx)])
    dist, idx = tree.query(grid, k=min(6, len(px)))
    if dist.ndim == 1:
        z = pz[idx]
    else:
        w = 1.0 / np.maximum(dist, 0.5) ** 2
        z = (pz[idx] * w).sum(axis=1) / w.sum(axis=1)
    verts = np.column_stack([grid[:, 0], grid[:, 1], z])
    faces = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a = i * ny + j
            faces.append((a, a + ny, a + ny + 1, a + 1))
    me = bpy.data.meshes.new("verify_ground")
    me.from_pydata(verts.tolist(), [], faces)
    me.update()
    ob = bpy.data.objects.new("verify_ground", me)
    bpy.context.scene.collection.objects.link(ob)
    import nycsim_bpy as nb

    ob.data.materials.append(nb.pbr_material("VERIFY_ground", base_color=(0.20, 0.20, 0.21, 1.0), roughness=0.9))
    return ob


def render_view(key: str, *, samples: int = 32, textured: bool = True, out_dir: Path = OUT_DIR,
                tiles_out: Path = TILES_OUT, size=None) -> dict:
    import bpy
    import nycsim_bpy as nb

    spec = VIEWS[key]
    t0 = time.perf_counter()
    nb.reset_scene()
    imported: list = []
    sources: list[str] = []
    if "merged" in spec:
        level = spec["merged"]["level"]
        for cx, cy in spec["merged"]["cells"]:
            p = REPO_ROOT / "blender_out" / "tiles" / "_merged" / f"l{level}" / f"L{level}_{cx}_{cy}.glb"
            if not p.exists():
                LOG.warning("missing merged cell %s", p)
                continue
            objs = _import_glb(p)
            size_m = 4000.0 if level == 2 else 16000.0
            _place(objs, (cx * size_m, cy * size_m))
            imported += objs
            sources.append(str(p.relative_to(REPO_ROOT)))
        ground_tiles = []
    else:
        for t in spec["tiles"]:
            p = tiles_out / t / "tile_buildings.glb"
            if not p.exists():
                raise FileNotFoundError(f"{p} — run build_tile.py for {t} first")
            objs = _import_glb(p)
            _place(objs, td.tile_origin(t))
            imported += objs
            try:
                sources.append(str(p.relative_to(REPO_ROOT)))
            except ValueError:
                sources.append(str(p))
        ground_tiles = spec["tiles"]
    _hide_lods(imported, keep_lod=0)
    if spec.get("water"):
        _water_plane()
    mats = _swap_materials([o for o in imported if not o.hide_render], textured)
    if ground_tiles:
        _ground_mesh(ground_tiles)

    cam = _resolve_z(spec, "cam")
    tgt = _resolve_z(spec, "target")
    sc = bpy.context.scene
    # Factory settings render these light-coloured masonry shells badly overexposed; AgX with a
    # little negative exposure is what the kit and landmark stages use for their sheets too.
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = float(spec.get("exposure", -0.6))
    out = out_dir / f"{key}.png"
    nb.quick_render(out, camera_location=cam, camera_target=tgt,
                    fov_deg=spec["fov"], size=tuple(size or spec["size"]), samples=samples,
                    sun_azimuth_deg=spec["sun_az"], sun_elevation_deg=spec["sun_el"],
                    sun_strength=float(spec.get("sun_strength", 2.6)))
    try:
        png_rel = str(out.relative_to(REPO_ROOT))
    except ValueError:
        png_rel = str(out)
    info = {"view": key, "title": spec["title"], "png": png_rel,
            "sources": sources, "materials": mats, "samples": samples,
            "camera_m": [round(v, 2) for v in cam], "target_m": [round(v, 2) for v in tgt],
            "seconds": round(time.perf_counter() - t0, 1)}
    LOG.info("%s -> %s (%.1fs)", key, out, info["seconds"])
    return info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", default="all", help="comma separated view names or 'all'")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--width", type=int, default=0)
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--flat", action="store_true", help="skip the PBR texture swap")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--tiles-root", default=str(TILES_OUT), help="where tile_buildings.glb files live")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    names = list(VIEWS) if args.views == "all" else [v for v in args.views.split(",") if v]
    for n in names:
        if n not in VIEWS:
            print(f"unknown view {n}; known: {', '.join(VIEWS)}", file=sys.stderr)
            return 2
    size = (args.width, args.height) if args.width and args.height else None
    out_dir = Path(args.out)
    infos = []
    for n in names:
        infos.append(render_view(n, samples=args.samples, textured=not args.flat, out_dir=out_dir,
                                 tiles_out=Path(args.tiles_root), size=size))
        print(f"{n}: {infos[-1]['png']} ({infos[-1]['seconds']}s)", flush=True)
    idx = out_dir / "renders.json"
    existing = {}
    if idx.exists():
        try:
            existing = {r["view"]: r for r in json.loads(idx.read_text()).get("renders", [])}
        except Exception:
            existing = {}
    for i in infos:
        existing[i["view"]] = i
    td.write_json(idx, {"schema_version": 1, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "engine": "CYCLES CPU", "renders": [existing[k] for k in sorted(existing)]})
    print(f"index -> {idx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
