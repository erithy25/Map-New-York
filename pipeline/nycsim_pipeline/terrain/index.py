"""``data/processed/tiles/index.parquet`` (DATA_CONTRACTS §2), written under a file lock.

The terrain stage owns the geometric and terrain columns — ``tile, tx, ty, x0, y0, borough_codes,
has_terrain, has_water, has_land, z_min, z_max`` — and creates the file. The content counts
(``n_buildings, n_road_segments, n_props, n_trees``) belong to the buildings / roads / furniture stages:
this writer creates them as 0 and **never overwrites a non-zero value another stage has already put
there**. Agents run concurrently, so the read-modify-write is serialised with ``fcntl.flock`` on
``tiles/index.lock``.

``borough_codes`` uses the contract enumeration 1 MN, 2 BX, 3 BK, 4 QN, 5 SI, 6 NJ, 0 water plus one
documented extension, **7 = New York State land outside the five boroughs** (the Nassau County and lower
Westchester strips that the scope rectangle clips). The enumeration is stored in the parquet metadata key
``nycsim.borough_codes`` so a consumer never has to guess.

    python -m nycsim_pipeline.terrain.index
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely

from . import manifest_safe as manifest
from ..crs import NYC_TM
from ..paths import PROCESSED, RAW
from ..tiling import Tile, scope_tiles

log = logging.getLogger("nycsim.terrain.index")

INDEX_PARQUET = PROCESSED / "tiles" / "index.parquet"
LOCK_PATH = PROCESSED / "tiles" / "index.lock"
BOROUGH_LAND = RAW / "nyc_opendata" / "borough_boundaries.geojson"
BOROUGH_WATER = RAW / "nyc_opendata" / "borough_boundaries_water.geojson"
SCHEMA = "tiles.index/1"
CODE_ENUM = {0: "water", 1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island",
             6: "New Jersey", 7: "New York State outside NYC (extension)"}
CODE_NJ = 6
CODE_OTHER_NY = 7
CODE_WATER = 0
MIN_TILE_OVERLAP_M2 = 100.0   # a borough must own at least this much of a tile to be listed
MIN_OUTSIDE_NYC_M2 = 10_000.0  # ... and this much of a tile must fall outside the city before 6/7 is added

COUNT_COLS = ("n_buildings", "n_road_segments", "n_props", "n_trees")
TERRAIN_COLS = ("tile", "tx", "ty", "x0", "y0", "borough_codes", "has_terrain", "has_water", "has_land", "z_min", "z_max")


@contextmanager
def index_lock(timeout_s: float = 300.0):
    """Exclusive advisory lock shared by every agent that writes tiles/index.parquet."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
    t0 = time.time()
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - t0 > timeout_s:
                    raise TimeoutError(f"could not lock {LOCK_PATH} within {timeout_s}s")
                time.sleep(0.2)
        os.write(fd, f"{os.getpid()} terrain.index {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n".encode())
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _boroughs():
    g = pyogrio.read_dataframe(BOROUGH_LAND).to_crs(NYC_TM)
    col = next(c for c in g.columns if c.lower() in ("borocode", "boro_code"))
    geoms = {int(r[col]): shapely.make_valid(r.geometry) for _, r in g.iterrows()}
    w = pyogrio.read_dataframe(BOROUGH_WATER).to_crs(NYC_TM)
    nyc_all = shapely.union_all([shapely.make_valid(x) for x in w.geometry.values])
    return geoms, nyc_all


def _state_line_x(nyc_all) -> tuple[np.ndarray, np.ndarray]:
    """Sampled NY/NJ state line: for a set of y values, the westernmost x of NYC jurisdiction.

    NYC's water boundary runs to the state line in the Hudson, Kill Van Kull and Arthur Kill, so its
    western envelope *is* the NY/NJ border across the whole scope latitude band. Land west of it inside
    the scope (which stops well south of 41 deg N, where the border leaves the river) is New Jersey.
    """
    ymin, ymax = nyc_all.bounds[1], nyc_all.bounds[3]
    ys = np.arange(np.floor(ymin / 100.0) * 100.0, ymax + 100.0, 100.0)
    xs = np.full(ys.size, np.nan)
    x0, x1 = nyc_all.bounds[0] - 1000.0, nyc_all.bounds[2] + 1000.0
    for i, y in enumerate(ys):
        line = shapely.LineString([(x0, y), (x1, y)])
        inter = nyc_all.intersection(line)
        if inter.is_empty:
            continue
        xs[i] = inter.bounds[0]
    ok = np.isfinite(xs)
    return ys[ok], xs[ok]


def tile_borough_codes(tiles: list[Tile], has_land: dict[str, bool], has_water: dict[str, bool]) -> dict[str, list[int]]:
    geoms, nyc_all = _boroughs()
    ys, xs = _state_line_x(nyc_all)
    keys = sorted(geoms)
    tree = shapely.STRtree([geoms[k] for k in keys])
    out: dict[str, list[int]] = {}
    for t in tiles:
        b = shapely.box(*t.bounds)
        codes: list[int] = []
        if has_water.get(t.name, False):
            codes.append(CODE_WATER)
        claimed = 0.0
        for j in tree.query(b, predicate="intersects"):
            a = geoms[keys[j]].intersection(b).area
            if a >= MIN_TILE_OVERLAP_M2:
                codes.append(keys[j])
                claimed += a
        # Land outside the city limits (the NYC boundary *including water* is the city's jurisdiction, so
        # a harbour tile is inside it): only then is the tile New Jersey or New York State outside NYC.
        if has_land.get(t.name, False):
            outside = b.difference(nyc_all).area
            if outside >= MIN_OUTSIDE_NYC_M2:
                cy = t.y0 + 500.0
                k = int(np.argmin(np.abs(ys - cy)))
                line_x = float(xs[k]) if xs.size else 0.0
                codes.append(CODE_NJ if (t.x0 + 500.0) < line_x else CODE_OTHER_NY)
        out[t.name] = sorted(set(codes))
    return out


def collect_terrain(tiles: list[Tile]) -> dict[str, dict]:
    """Read every tile's terrain.json (written by ``tiles.py``)."""
    rows: dict[str, dict] = {}
    for t in tiles:
        p = PROCESSED / "tiles" / t.name / "terrain.json"
        if not p.exists():
            continue
        with open(p) as f:
            d = json.load(f)
        rows[t.name] = {"z_min": float(d["z_min_m"]), "z_max": float(d["z_max_m"]),
                        "has_water": bool(d["has_water"]), "has_land": bool(d["has_land"])}
    return rows


def build_table(tiles: list[Tile], terrain: dict[str, dict], previous: pa.Table | None) -> pa.Table:
    prev = {}
    if previous is not None:
        pdct = previous.to_pydict()
        for i, name in enumerate(pdct["tile"]):
            prev[name] = {c: pdct[c][i] for c in previous.schema.names}
    has_land = {k: v["has_land"] for k, v in terrain.items()}
    has_water = {k: v["has_water"] for k, v in terrain.items()}
    codes = tile_borough_codes(tiles, has_land, has_water)
    names, tx, ty, x0, y0, bc, hterr, hwat, hland, zmin, zmax = [], [], [], [], [], [], [], [], [], [], []
    counts = {c: [] for c in COUNT_COLS}
    for t in tiles:
        te = terrain.get(t.name)
        names.append(t.name)
        tx.append(np.int32(t.tx))
        ty.append(np.int32(t.ty))
        x0.append(float(t.x0))
        y0.append(float(t.y0))
        bc.append([np.int8(c) for c in codes.get(t.name, [])])
        hterr.append(te is not None)
        hwat.append(bool(te["has_water"]) if te else False)
        hland.append(bool(te["has_land"]) if te else False)
        zmin.append(np.float32(te["z_min"]) if te else None)
        zmax.append(np.float32(te["z_max"]) if te else None)
        p = prev.get(t.name, {})
        for c in COUNT_COLS:
            counts[c].append(np.int32(p.get(c) or 0))
    tbl = pa.table({
        "tile": pa.array(names, pa.string()), "tx": pa.array(tx, pa.int32()), "ty": pa.array(ty, pa.int32()),
        "x0": pa.array(x0, pa.float64()), "y0": pa.array(y0, pa.float64()),
        "borough_codes": pa.array(bc, pa.list_(pa.int8())),
        **{c: pa.array(counts[c], pa.int32()) for c in COUNT_COLS},
        "has_terrain": pa.array(hterr, pa.bool_()), "has_water": pa.array(hwat, pa.bool_()),
        "has_land": pa.array(hland, pa.bool_()),
        "z_min": pa.array(zmin, pa.float32()), "z_max": pa.array(zmax, pa.float32()),
    })
    # never drop a column another stage added: carry extras across, aligned by tile
    if previous is not None:
        extras = [c for c in previous.schema.names if c not in tbl.schema.names]
        for c in extras:
            vals = [prev.get(n, {}).get(c) for n in names]
            tbl = tbl.append_column(c, pa.array(vals, previous.schema.field(c).type))
    return tbl.replace_schema_metadata({b"nycsim.schema": SCHEMA.encode(),
                                        b"nycsim.borough_codes": json.dumps(CODE_ENUM).encode(),
                                        b"nycsim.terrain_columns": json.dumps(list(TERRAIN_COLS)).encode()})


def write_index(tiles: list[Tile] | None = None) -> dict:
    tiles = tiles or scope_tiles()
    terrain = collect_terrain(tiles)
    with index_lock():
        previous = pq.read_table(INDEX_PARQUET) if INDEX_PARQUET.exists() else None
        tbl = build_table(tiles, terrain, previous)
        INDEX_PARQUET.parent.mkdir(parents=True, exist_ok=True)
        tmp = INDEX_PARQUET.with_suffix(".tmp.parquet")
        pq.write_table(tbl, tmp, compression="snappy")
        os.replace(tmp, INDEX_PARQUET)
    kept = 0
    if previous is not None:
        kept = int(sum(1 for c in COUNT_COLS for v in previous.column(c).to_pylist() if v))
    summary = {"rows": tbl.num_rows, "with_terrain": int(sum(tbl.column("has_terrain").to_pylist())),
               "with_land": int(sum(tbl.column("has_land").to_pylist())),
               "with_water": int(sum(tbl.column("has_water").to_pylist())),
               "preserved_content_counts": kept, "path": str(INDEX_PARQUET)}
    manifest.record_processed("tiles_index", INDEX_PARQUET, stage="terrain",
                              sources=["usgs_3dep", "plan_hydrography", "borough_boundaries"],
                              rows=tbl.num_rows, schema=SCHEMA, extra={"terrain_columns": list(TERRAIN_COLS)})
    log.info("tiles/index.parquet: %s", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(write_index(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
