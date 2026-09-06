"""Audit of the composed 3DEP source grid over the whole project scope.

Answers three questions that gate the tile pass:

1. Which scope tiles have *no* DEM sample at all, and which have partial voids?
2. Is every void inside water (ocean / bay / river), where the hydro-flattening step supplies 0.0 m,
   or is it a genuine land gap that has to be filled from another product?
3. What fraction of each borough's *land* area carries 1 m LiDAR, 1/9" and 1/3" data?

Output: ``data/processed/terrain/coverage.json`` (per tile + per borough + per source rollups).
The land masks come from the NYC borough boundaries (land-only file) and, for New Jersey, from the
scope box west of the Hudson minus the water polygons of the water stage.

    python -m nycsim_pipeline.terrain.coverage [--no-water] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pyogrio
import shapely
from rasterio.features import rasterize

from ..crs import NYC_TM
from ..paths import PROCESSED, RAW
from ..tiling import Tile, scope_tiles
from .compose import CODE_NAME, DemStack
from .grid import NODATA, SAMPLES, tile_transform

log = logging.getLogger("nycsim.terrain.coverage")

COVERAGE_PATH = PROCESSED / "terrain" / "coverage.json"
BOROUGH_LAND = RAW / "nyc_opendata" / "borough_boundaries.geojson"
BORO_NAME = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}
SCHEMA = "terrain.coverage/1"


def borough_land_polygons() -> dict[int, object]:
    """Borough code -> land polygon (NYC_TM). The 'water included' boundary file is *not* used here."""
    g = pyogrio.read_dataframe(BOROUGH_LAND).to_crs(NYC_TM)
    col = next((c for c in g.columns if c.lower() in ("borocode", "boro_code")), None)
    if col is None:
        raise RuntimeError(f"{BOROUGH_LAND}: no borough code column in {list(g.columns)}")
    out: dict[int, object] = {}
    for _, r in g.iterrows():
        out[int(r[col])] = shapely.make_valid(r.geometry)
    missing = set(BORO_NAME) - set(out)
    if missing:
        raise RuntimeError(f"{BOROUGH_LAND}: missing borough codes {sorted(missing)}")
    return out


def _tile_masks(tile: Tile, geoms: dict[int, object]) -> dict[int, np.ndarray]:
    """Rasterise the polygons that touch this tile onto its 501x501 lattice."""
    tr = tile_transform(tile)
    b = shapely.box(*tile.bounds)
    masks: dict[int, np.ndarray] = {}
    for key, geom in geoms.items():
        if geom is None or not geom.intersects(b):
            continue
        m = rasterize([(geom, 1)], out_shape=(SAMPLES, SAMPLES), transform=tr, fill=0, dtype="uint8", all_touched=False)
        if m.any():
            masks[key] = m.astype(bool)
    return masks


def scan(stack: DemStack, water_union=None) -> dict:
    """Per-tile composition statistics over every scope tile."""
    boro = borough_land_polygons()
    tiles = scope_tiles()
    per_tile: dict[str, dict] = {}
    boro_counts = {c: {"land_px": 0, "valid_px": 0, "px_1m": 0, "px_19": 0, "px_13": 0} for c in BORO_NAME}
    totals = {"tiles": 0, "px": 0, "valid_px": 0, "px_1m": 0, "px_19": 0, "px_13": 0,
              "void_px": 0, "void_px_in_water": 0, "void_px_land": 0, "tiles_empty": 0, "tiles_partial": 0}
    t0 = time.time()
    for n, t in enumerate(tiles, 1):
        tr = tile_transform(t)
        z, code = stack.read(tr, SAMPLES, SAMPLES)
        valid = z != NODATA
        nv = int(valid.sum())
        c1 = int((code == 1).sum())
        c2 = int((code == 2).sum())
        c3 = int((code == 3).sum())
        void = ~valid
        n_void = int(void.sum())
        void_water = 0
        if n_void and water_union is not None:
            wm = _tile_masks(t, {0: water_union}).get(0)
            if wm is not None:
                void_water = int((void & wm).sum())
        rec = {"valid_px": nv, "px_1m": c1, "px_19": c2, "px_13": c3, "void_px": n_void,
               "void_px_in_water": void_water,
               "z_min": float(z[valid].min()) if nv else None, "z_max": float(z[valid].max()) if nv else None}
        per_tile[t.name] = rec
        totals["tiles"] += 1
        totals["px"] += SAMPLES * SAMPLES
        totals["valid_px"] += nv
        totals["px_1m"] += c1
        totals["px_19"] += c2
        totals["px_13"] += c3
        totals["void_px"] += n_void
        totals["void_px_in_water"] += void_water
        totals["void_px_land"] += n_void - void_water
        totals["tiles_empty"] += int(nv == 0)
        totals["tiles_partial"] += int(0 < nv < SAMPLES * SAMPLES)
        for bcode, mask in _tile_masks(t, boro).items():
            bc = boro_counts[bcode]
            bc["land_px"] += int(mask.sum())
            bc["valid_px"] += int((mask & valid).sum())
            bc["px_1m"] += int((mask & (code == 1)).sum())
            bc["px_19"] += int((mask & (code == 2)).sum())
            bc["px_13"] += int((mask & (code == 3)).sum())
        if n % 250 == 0:
            log.info("  %d/%d tiles scanned (%.0fs)", n, len(tiles), time.time() - t0)
    boroughs = {}
    for c, v in boro_counts.items():
        land = max(1, v["land_px"])
        boroughs[BORO_NAME[c]] = {
            "borough_code": c, "land_km2": round(v["land_px"] * 4e-6, 3),
            "coverage_pct": round(100.0 * v["valid_px"] / land, 4),
            "pct_1m": round(100.0 * v["px_1m"] / land, 4),
            "pct_19": round(100.0 * v["px_19"] / land, 4),
            "pct_13": round(100.0 * v["px_13"] / land, 4),
            "void_px": v["land_px"] - v["valid_px"],
        }
    doc = {"schema_version": 1, "schema": SCHEMA, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "seconds": round(time.time() - t0, 1), "sources": {CODE_NAME[k]: v for k, v in
                                                              ((1, totals["px_1m"]), (2, totals["px_19"]), (3, totals["px_13"]), (0, totals["void_px"]))},
           "totals": totals, "boroughs": boroughs,
           "empty_tiles": sorted(k for k, v in per_tile.items() if v["valid_px"] == 0),
           "partial_tiles": sorted(k for k, v in per_tile.items() if 0 < v["valid_px"] < SAMPLES * SAMPLES),
           "tiles": per_tile}
    return doc


def load_water_union():
    """Union of the water stage's open-water polygons, or None when the water stage has not run."""
    from ..water.build import HYDRO_PATH, SCHEMAS, read_geoparquet
    if not HYDRO_PATH.exists():
        log.warning("%s absent: void-in-water classification skipped", HYDRO_PATH)
        return None
    h = read_geoparquet(HYDRO_PATH, SCHEMAS["hydrography"])
    return shapely.union_all(h.loc[h["is_open_water"], "geometry"].values)


def save(doc: dict, path: Path = COVERAGE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    os.replace(tmp, path)
    from . import manifest_safe as manifest
    manifest.record_processed("terrain_coverage", path, stage="terrain", sources=["usgs_3dep", "borough_boundaries", "plan_hydrography"],
                              rows=doc["totals"]["tiles"], schema=SCHEMA,
                              extra={"boroughs": doc["boroughs"], "void_px_land": doc["totals"]["void_px_land"]})
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-water", action="store_true", help="skip the void-inside-water classification")
    ap.add_argument("--out", default=str(COVERAGE_PATH))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from .ingest import INDEX_PATH
    water = None if a.no_water else load_water_union()
    with DemStack(INDEX_PATH) as stack:
        doc = scan(stack, water)
    save(doc, Path(a.out))
    print(json.dumps({"totals": doc["totals"], "boroughs": doc["boroughs"], "empty_tiles": len(doc["empty_tiles"]),
                      "partial_tiles": len(doc["partial_tiles"]), "seconds": doc["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
