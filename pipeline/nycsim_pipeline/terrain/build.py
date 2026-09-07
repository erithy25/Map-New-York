"""Terrain stage driver — ``python -m nycsim_pipeline terrain`` (ARCHITECTURE §5, DATA_CONTRACTS §2/§3).

Runs the whole stage in dependency order and reports what each step produced:

1. ``ingest``   — discover the USGS 3DEP products that intersect the scope through the TNM products API,
   download them through ``nycsim_pipeline.download`` (manifest + SHA-256), and warp each onto the global
   2 m NYC_TM lattice (``terrain/src2m/*.tif``). Vertical datum: metres NAVD88 in every product, verified
   from the product metadata and restated in each intermediate's ``vertical_datum`` tag.
2. ``points``   — cache the survey ground points that densify the surface: planimetric spot elevations
   (ft → m) and the 1.08 M footprint LiDAR ground elevations (``terrain/ground_points.parquet``).
3. ``water``    — the water stage's vectors (hydrography, shoreline, structures, per-tile water areas) and,
   with the composed DEM available, the real water level of every body (``water.build``).
4. ``coverage`` — audit the composed source grid per tile and per borough before any tile is written.
5. ``tiles``    — build ``tiles/{tile}/terrain.png`` + ``terrain.json`` for every scope tile.
6. ``index``    — create/update ``tiles/index.parquet`` (terrain columns only) under ``tiles/index.lock``.
7. ``verify``   — extremes, seams, voids, known elevations, water datum, and the hillshade renders in
   ``docs/verification/terrain/``.

Each step is skipped when its output is already present and ``--force``/``--from`` do not ask for it, so
the driver is idempotent and restartable. Steps are independent processes only in ``tiles`` (one process
per worker, two by default) — everything else runs in this process, peak RSS below 2.5 GB.

    python -m nycsim_pipeline terrain                       # everything that is not done yet
    python -m nycsim_pipeline terrain --from tiles          # rebuild tiles, index and verification
    python -m nycsim_pipeline terrain --only water          # one step
    python -m nycsim_pipeline terrain --workers 2 --force   # full rebuild
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from ..paths import PROCESSED, VERIFICATION
from ..tiling import Tile, scope_tiles

log = logging.getLogger("nycsim.terrain.build")

STEPS = ("ingest", "points", "water", "coverage", "tiles", "index", "verify")


def _done(step: str) -> bool:
    """Is the step's principal output already on disk?"""
    p = {
        "ingest": PROCESSED / "terrain" / "src2m" / "index.json",
        "points": PROCESSED / "terrain" / "ground_points.parquet",
        "water": PROCESSED / "water" / "hydrography.parquet",
        "coverage": PROCESSED / "terrain" / "coverage.json",
        "tiles": PROCESSED / "terrain" / "tile_summary.json",
        "index": PROCESSED / "tiles" / "index.parquet",
        "verify": VERIFICATION / "terrain" / "verification.json",
    }[step]
    return p.exists()


def run_step(step: str, args: argparse.Namespace) -> dict:
    t0 = time.time()
    if step == "ingest":
        from .ingest import ingest_all
        out = ingest_all(tuple(k for k in args.kinds.split(",") if k), overwrite=args.force, keep_raw=args.keep_raw)
        res = {"sources": len(out["sources"]), "failures": out["failures"],
               "skipped_outside_scope": out.get("skipped_outside_scope", []),
               "downloaded_bytes": out["downloaded_bytes"], "retained_raw_bytes": out["retained_raw_bytes"]}
    elif step == "points":
        from .points import build_cache
        res = build_cache(force=args.force)
    elif step == "water":
        from ..water import build as water_build
        res = {"geometry": water_build.build_geometry(use_osm=not args.no_osm)} if (args.force or not _done("water")) else {"geometry": "present"}
        from .compose import DemStack
        from .ingest import INDEX_PATH
        with DemStack(INDEX_PATH) as stack:
            res["levels"] = water_build.finalize_levels(stack)
            res["osm_dem_clip"] = water_build.refine_osm_geometry(stack)
            res["levels_after_clip"] = water_build.finalize_levels(stack)
            res["shoreline"] = water_build.classify_shoreline_by_dem(stack)
    elif step == "coverage":
        from .compose import DemStack
        from .coverage import load_water_union, save, scan
        from .ingest import INDEX_PATH
        with DemStack(INDEX_PATH) as stack:
            doc = scan(stack, load_water_union())
        save(doc)
        res = {"totals": doc["totals"], "boroughs": doc["boroughs"],
               "empty_tiles": len(doc["empty_tiles"]), "partial_tiles": len(doc["partial_tiles"])}
    elif step == "tiles":
        from .tiles import build_all
        tiles = [Tile.parse(t) for t in args.tiles.split(",")] if args.tiles else scope_tiles()
        out = build_all(tiles, workers=args.workers, overwrite=True)
        res = {k: v for k, v in out.items() if k not in ("failures", "slowest")}
        res["failures"] = out["failures"][:5]
    elif step == "index":
        from .index import write_index
        res = write_index()
    elif step == "verify":
        from .verify import run
        doc = run(skip_hillshade=args.skip_hillshade)
        res = {"extremes": doc["extremes"], "seams": {k: doc["seams"][k] for k in ("pairs_checked", "max_edge_difference_m", "n_violations")},
               "no_void": {k: doc["no_void"][k] for k in ("tiles_present", "n_missing", "non_finite", "z_min_m", "z_max_m")},
               "known_elevations": {"passed": doc["known_elevations"]["passed"], "total": doc["known_elevations"]["total"]},
               "water_datum": doc.get("water_datum", {})}
    else:  # pragma: no cover — argparse restricts the choices
        raise ValueError(step)
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nycsim_pipeline terrain", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="from_step", choices=STEPS, help="run this step and everything after it")
    ap.add_argument("--only", choices=STEPS, help="run exactly one step")
    ap.add_argument("--force", action="store_true", help="rerun steps whose output already exists")
    ap.add_argument("--workers", type=int, default=2, help="tile workers (one process each, ~700 MB RSS)")
    ap.add_argument("--tiles", help="comma separated tile names for the tile step (default: every scope tile)")
    ap.add_argument("--kinds", default="1m,19,13", help="3DEP product kinds to ingest, best first")
    ap.add_argument("--keep-raw", action="store_true", help="keep the raw 1 m GeoTIFFs after ingest (+3.2 GB)")
    ap.add_argument("--no-osm", action="store_true", help="water stage: planimetric polygons only")
    ap.add_argument("--skip-hillshade", action="store_true", help="verification without the rendered reliefs")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if a.only:
        steps = [a.only]
    elif a.from_step:
        steps = list(STEPS[STEPS.index(a.from_step):])
    else:
        steps = [s for s in STEPS if a.force or not _done(s)]
        if not steps:
            print("terrain: every artefact is present; use --force or --from to rebuild")
            return 0

    t0 = time.time()
    summary: dict[str, dict] = {}
    for step in steps:
        log.info("=== terrain step %s ===", step)
        try:
            summary[step] = run_step(step, a)
        except Exception as e:  # noqa: BLE001 — report the failing step and stop; later steps depend on it
            log.exception("terrain step %s failed", step)
            summary[step] = {"error": f"{type(e).__name__}: {e}"}
            print(json.dumps(summary, indent=1, default=str))
            return 1
        log.info("step %s: %s", step, json.dumps(summary[step], default=str)[:400])
    summary["total_seconds"] = round(time.time() - t0, 1)
    print(json.dumps(summary, indent=1, default=str))
    v = summary.get("verify", {})
    if v and (v.get("seams", {}).get("n_violations") or v.get("no_void", {}).get("n_missing")
              or not v.get("extremes", {}).get("pass", True)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
