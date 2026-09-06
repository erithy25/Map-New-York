#!/usr/bin/env python3
"""Merged skyline meshes for the L2 and L3 streaming tiers (ARCHITECTURE §3).

    python3 blender/buildings/build_lod_merged.py --all
    python3 blender/buildings/build_lod_merged.py --level 3 --cell 0_0

* **L2** (2.5–12 km): one mesh set per **4 km** cell — every building in the cell as a box-ish
  massing solid, split by material class.  ``blender_out/tiles/_merged/l2/L2_{px}_{py}.glb``.
* **L3** (12–40 km): one mesh set per **16 km** cell, **buildings ≥ 40 m only**, so the Manhattan
  skyline is complete and correct from Brooklyn Heights, the Staten Island Ferry and the George
  Washington Bridge.  ``blender_out/tiles/_merged/l3/L3_{px}_{py}.glb``.

Cell indices come from ``pipeline.nycsim_pipeline.tiling.parent_tile`` so the runtime scheduler and
these files agree.  Geometry is authored in cell-local metres (origin at the cell's south-west
corner, recorded in ``asset.extras.nycsim.origin_m``); Z stays absolute NAVD88 metres.  Each cell
also gets a ``manifest.json`` beside the ``.glb``.
"""
from __future__ import annotations

import argparse
import logging
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
sys.path.insert(0, str(_HERE))

import shellgeom as sg  # noqa: E402
import tiledata as td  # noqa: E402
import build_tile as bt  # noqa: E402
from nycsim_pipeline.tiling import Tile, parent_tile  # noqa: E402

LOG = logging.getLogger("nycsim.buildings.lod_merged")

MERGED_ROOT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO_ROOT / "blender_out")) / "tiles" / "_merged"
L3_MIN_HEIGHT_M = 40.0                     # ARCHITECTURE §3: L3 carries buildings >= 40 m only
CELL_SIZE_M = {2: 4000.0, 3: 16000.0}
LEVEL_TO_PARENT = {2: 1, 3: 2}
ATTRS = ("_bin", "_lit_seed_hi", "_lit_seed_lo")


def cell_of(tile: str, level: int) -> tuple[int, int]:
    return parent_tile(Tile.parse(tile), LEVEL_TO_PARENT[level])


def group_tiles(tiles: list[str], level: int) -> dict[tuple[int, int], list[str]]:
    groups: dict[tuple[int, int], list[str]] = defaultdict(list)
    for t in tiles:
        groups[cell_of(t, level)].append(t)
    return dict(sorted(groups.items()))


def build_cell(level: int, cell: tuple[int, int], tiles: list[str], *, out_root: Path = MERGED_ROOT,
               roof_attrs=None) -> dict:
    import bpy
    import nycsim_bpy as nb

    t0 = time.perf_counter()
    size = CELL_SIZE_M[level]
    cx0, cy0 = cell[0] * size, cell[1] * size
    min_h = L3_MIN_HEIGHT_M if level == 3 else 0.0

    buckets: dict[int, bt.Bucket] = {}
    n_in = n_out = 0
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for tile in tiles:
        try:
            load = td.load_tile(tile, roof_attrs=roof_attrs)
        except FileNotFoundError:
            continue
        n_in += load.rows_in
        dx, dy = load.x0 - cx0, load.y0 - cy0
        for spec in load.specs:
            if spec.roof_z - spec.ground_z < min_h:
                continue
            buf = sg.build_shell(spec, 2)
            if not buf.tris:
                continue
            n_out += 1
            pos = np.asarray(buf.pos, dtype=np.float64)
            pos[:, 0] += dx
            pos[:, 1] += dy
            tris = np.asarray(buf.tris, dtype=np.int64)
            uvs = np.asarray(buf.uvs, dtype=np.float32).reshape(-1, 3, 2)
            mats = np.asarray(buf.mats, dtype=np.int32)
            row = np.array([spec.attrs.get(a[1:], 0.0) for a in ATTRS], dtype=np.float32)
            lo = np.minimum(lo, pos.min(axis=0))
            hi = np.maximum(hi, pos.max(axis=0))
            for m in np.unique(mats):
                sel = mats == m
                t = tris[sel]
                uniq, inv = np.unique(t, return_inverse=True)
                buckets.setdefault(int(m), bt.Bucket()).add(
                    pos[uniq], inv.reshape(-1, 3).astype(np.int64), uvs[sel], row)

    name = f"L{level}_{cell[0]}_{cell[1]}"
    out_dir = out_root / f"l{level}"
    glb = out_dir / f"{name}.glb"
    if not buckets:
        LOG.info("%s: no buildings", name)
        return {"cell": name, "buildings": 0, "triangles": 0, "glb": ""}

    nb.reset_scene()
    objects = []
    mat_stats: dict[str, dict] = {}
    n_tris = 0
    for m, bucket in sorted(buckets.items()):
        pos, tri, uv, att = bucket.finish()
        mname = td.material_name(m)
        obj = bt._make_object(f"{name}_{mname}", pos, tri, uv, att, list(ATTRS), mname,
                              {"cell": name, "level": level, "material": mname,
                               "material_index": int(m), "origin_m": [cx0, cy0, 0.0]})
        objects.append(obj)
        n_tris += len(tri)
        mat_stats[mname] = {"index": int(m), "triangles": int(len(tri)), "vertices": int(len(pos))}

    bt.export_glb(glb, objects, {
        "stage": "buildings_lod_merged", "cell": name, "level": level,
        "origin_m": [cx0, cy0, 0.0], "cell_size_m": size, "crs": "NYC_TM",
        "vertical_datum": "NAVD88 metres", "source_tiles": tiles,
        "min_height_m": min_h, "attributes": list(ATTRS),
        "attribute_notes": {"_LIT_SEED": "lit_seed = _LIT_SEED_HI * 65536 + _LIT_SEED_LO"},
    })
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)

    manifest = {
        "schema_version": 1,
        "stage": "buildings_lod_merged",
        "level": level,
        "cell": name,
        "cell_index": list(cell),
        "cell_size_m": size,
        "origin_m": [cx0, cy0, 0.0],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": nb.git_commit(),
        "generator": "blender/buildings/build_lod_merged.py",
        "source_tiles": tiles,
        "min_height_m": min_h,
        "buildings": {"rows_in": n_in, "emitted": n_out},
        "triangles": int(n_tris),
        "bounds_local_m": {"min": bt._fin(lo), "max": bt._fin(hi)},
        "bounds_world_m": {"min": bt._shift(lo, cx0, cy0), "max": bt._shift(hi, cx0, cy0)},
        "materials": mat_stats,
        "glb": {"path": bt._rel(glb), "bytes": glb.stat().st_size, "sha256": bt._sha256(glb)},
        "seconds": round(time.perf_counter() - t0, 3),
    }
    td.write_json(out_dir / f"{name}.manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", default="2,3", help="2 (4 km cells), 3 (16 km cells, >= 40 m only) or both")
    ap.add_argument("--cell", help="single cell index 'px_py' (with the given --level)")
    ap.add_argument("--tiles", help="restrict to these comma separated source tiles")
    ap.add_argument("--all", action="store_true", help="every cell covered by data/processed/tiles")
    ap.add_argument("--out", default=str(MERGED_ROOT))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    levels = [int(x) for x in args.level.replace(" ", "").split(",") if x]
    for lv in levels:
        if lv not in (2, 3):
            print(f"unknown level {lv}", file=sys.stderr)
            return 2
    tiles = [t for t in args.tiles.split(",") if t] if args.tiles else td.available_tiles()
    if not tiles:
        print("no source tiles", file=sys.stderr)
        return 2
    roof_attrs = td.load_roof_attrs()
    summary = []
    for level in levels:
        groups = group_tiles(tiles, level)
        if args.cell:
            want = tuple(int(v) for v in args.cell.split("_"))
            groups = {k: v for k, v in groups.items() if k == want}
        for i, (cell, cell_tiles) in enumerate(groups.items(), 1):
            m = build_cell(level, cell, cell_tiles, out_root=Path(args.out), roof_attrs=roof_attrs)
            summary.append(m)
            print(f"[L{level} {i}/{len(groups)}] {m.get('cell')} tiles={len(cell_tiles)} "
                  f"buildings={m['buildings']['emitted'] if isinstance(m.get('buildings'), dict) else 0} "
                  f"tris={m.get('triangles', 0)} bytes={m.get('glb', {}).get('bytes', 0) if isinstance(m.get('glb'), dict) else 0}",
                  flush=True)
    out = Path(args.out) / "merged_summary.json"
    td.write_json(out, {"schema_version": 1, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "cells": summary})
    print(f"summary -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
