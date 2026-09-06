"""Survey-grade ground points used to densify the 3DEP surface (ARCHITECTURE §5).

Two real sources, no synthetic points:

* **NYC planimetric spot elevations** (`plan_elevation_points.geojson`, feature code 3000 / sub code
  300000). Photogrammetric points on the centre of every roadbed and on interior sidewalks, at every
  intersection and every 200 ft along a block, in US survey feet above NAVD88 ("ASPRS 1in=100ft Class 2"
  vertical accuracy). Sub code 300020 (bridge elevations) is **excluded** — those points sit on bridge
  decks, not on the ground — and feature code 3020 (building elevation) is a *roof* elevation and is
  excluded as well.
* **Building ground elevations** (`buildings/footprints_raw.parquet`, columns ``cx, cy, ground_z``): the
  LiDAR-derived ground elevation of each of the 1,083,026 footprints, already in metres NAVD88.

The two are concatenated into one cache (`data/processed/terrain/ground_points.parquet`), sorted by
``(y, x)`` so that every consumer sees the same order, and bucketed into 1 km cells so a tile can gather
its neighbourhood in O(points in 9 cells). The global order is what makes the tile pass reproducible:
the densification sums contributions in ascending global point index, so two tiles sharing an edge add
the same numbers in the same order and their shared samples are bit-identical.

    python -m nycsim_pipeline.terrain.points [--force]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio

from .. import manifest
from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, TILE_SIZE_M, US_SURVEY_FOOT_M, transformer
from ..paths import PROCESSED, RAW

log = logging.getLogger("nycsim.terrain.points")

CACHE = PROCESSED / "terrain" / "ground_points.parquet"
RAW_ELEV = RAW / "nyc_opendata" / "plan_elevation_points.geojson"
BUILDINGS = PROCESSED / "buildings" / "footprints_raw.parquet"
SCHEMA = "terrain.ground_points/1"

KIND_SPOT = 0
KIND_BUILDING = 1
KIND_NAME = {KIND_SPOT: "spot_elev", KIND_BUILDING: "bldg_ground"}
Z_VALID = (-60.0, 400.0)  # NAVD88 metres; anything outside is a bad record in this region


class PointError(RuntimeError):
    pass


def _read_spot_elevations() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x, y, z) of planimetric ground spot elevations in NYC_TM metres."""
    if not RAW_ELEV.exists():
        raise PointError(f"missing input {RAW_ELEV}")
    g = pyogrio.read_dataframe(RAW_ELEV, where="feat_code = '3000' AND sub_code = '300000'",
                               columns=["elevation", "feat_code", "sub_code"], use_arrow=False)
    if len(g) == 0:
        raise PointError(f"{RAW_ELEV}: no rows with feat_code 3000 / sub_code 300000")
    z_ft = np.asarray(g["elevation"], dtype=np.float64)
    lon = np.asarray([p.x for p in g.geometry.values], dtype=np.float64)
    lat = np.asarray([p.y for p in g.geometry.values], dtype=np.float64)
    x, y = transformer(g.crs, "NYC_TM").transform(lon, lat)
    z = z_ft * US_SURVEY_FOOT_M
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z) & (z > Z_VALID[0]) & (z < Z_VALID[1])
    log.info("spot elevations: %d rows, %d usable (%d rejected as non-finite/out of range)", len(g), int(ok.sum()), int((~ok).sum()))
    return x[ok], y[ok], z[ok]


def _read_building_grounds() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not BUILDINGS.exists():
        raise PointError(f"missing input {BUILDINGS}")
    t = pq.read_table(BUILDINGS, columns=["cx", "cy", "ground_z"])
    x = t.column("cx").to_numpy(zero_copy_only=False).astype(np.float64)
    y = t.column("cy").to_numpy(zero_copy_only=False).astype(np.float64)
    z = t.column("ground_z").to_numpy(zero_copy_only=False).astype(np.float64)
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z) & (z > Z_VALID[0]) & (z < Z_VALID[1])
    log.info("building grounds: %d rows, %d usable", len(z), int(ok.sum()))
    return x[ok], y[ok], z[ok]


def build_cache(force: bool = False) -> dict:
    """Write ``ground_points.parquet`` (x, y, z, kind), sorted by (y, x). Returns a summary."""
    if CACHE.exists() and not force:
        pf = pq.ParquetFile(CACHE)
        return {"path": str(CACHE), "rows": pf.metadata.num_rows, "reused": True}
    t0 = time.time()
    sx, sy, sz = _read_spot_elevations()
    bx, by, bz = _read_building_grounds()
    x = np.concatenate([sx, bx])
    y = np.concatenate([sy, by])
    z = np.concatenate([sz, bz])
    kind = np.concatenate([np.full(sx.size, KIND_SPOT, dtype=np.uint8), np.full(bx.size, KIND_BUILDING, dtype=np.uint8)])
    inside = (x >= SCOPE_XMIN) & (x <= SCOPE_XMAX) & (y >= SCOPE_YMIN) & (y <= SCOPE_YMAX)
    x, y, z, kind = x[inside], y[inside], z[inside], kind[inside]
    order = np.lexsort((x, y))  # y major, x minor: a stable, source-independent global order
    x, y, z, kind = x[order], y[order], z[order], kind[order]
    tbl = pa.table({"x": pa.array(x), "y": pa.array(y), "z": pa.array(z.astype(np.float32)), "kind": pa.array(kind)})
    tbl = tbl.replace_schema_metadata({b"nycsim.schema": SCHEMA.encode()})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp.parquet")
    pq.write_table(tbl, tmp, compression="snappy")
    os.replace(tmp, CACHE)
    summary = {"path": str(CACHE), "rows": int(x.size), "spot": int((kind == KIND_SPOT).sum()),
               "buildings": int((kind == KIND_BUILDING).sum()), "z_min": float(z.min()), "z_max": float(z.max()),
               "seconds": round(time.time() - t0, 1), "reused": False}
    manifest.record_processed("terrain_ground_points", CACHE, stage="terrain",
                              sources=["plan_elevation_points", "building_footprints"], rows=int(x.size), schema=SCHEMA,
                              extra={"spot": summary["spot"], "buildings": summary["buildings"]})
    log.info("ground points: %s", summary)
    return summary


@dataclass
class PointIndex:
    """Points in global order plus a 1 km cell bucket index."""
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    kind: np.ndarray
    cells: dict[tuple[int, int], np.ndarray]

    @property
    def n(self) -> int:
        return int(self.x.size)

    def query_bbox(self, xmin: float, ymin: float, xmax: float, ymax: float) -> np.ndarray:
        """Indices (ascending, i.e. global order) of the points inside the bbox."""
        cx0, cx1 = int(np.floor(xmin / TILE_SIZE_M)), int(np.floor(xmax / TILE_SIZE_M))
        cy0, cy1 = int(np.floor(ymin / TILE_SIZE_M)), int(np.floor(ymax / TILE_SIZE_M))
        parts = [self.cells[(cx, cy)] for cy in range(cy0, cy1 + 1) for cx in range(cx0, cx1 + 1) if (cx, cy) in self.cells]
        if not parts:
            return np.empty(0, dtype=np.int64)
        idx = np.sort(np.concatenate(parts))
        px, py = self.x[idx], self.y[idx]
        return idx[(px >= xmin) & (px <= xmax) & (py >= ymin) & (py <= ymax)]


def load_index(path: Path = CACHE) -> PointIndex:
    if not path.exists():
        raise PointError(f"{path} missing: run `python -m nycsim_pipeline.terrain.points` first")
    meta = pq.read_schema(path).metadata or {}
    got = meta.get(b"nycsim.schema", b"").decode()
    if got != SCHEMA:
        raise PointError(f"{path}: schema {got!r} != {SCHEMA!r}")
    t = pq.read_table(path)
    x = t.column("x").to_numpy(zero_copy_only=False)
    y = t.column("y").to_numpy(zero_copy_only=False)
    z = t.column("z").to_numpy(zero_copy_only=False)
    kind = t.column("kind").to_numpy(zero_copy_only=False)
    cx = np.floor(x / TILE_SIZE_M).astype(np.int32)
    cy = np.floor(y / TILE_SIZE_M).astype(np.int32)
    key = cx.astype(np.int64) * 100_000 + cy.astype(np.int64)
    order = np.argsort(key, kind="stable")
    key_s = key[order]
    bounds = np.flatnonzero(np.diff(key_s)) + 1
    cells: dict[tuple[int, int], np.ndarray] = {}
    for part in np.split(order, bounds):
        if part.size:
            cells[(int(cx[part[0]]), int(cy[part[0]]))] = np.sort(part)
    return PointIndex(x, y, z, kind, cells)


AUDIT_PATH = PROCESSED / "terrain" / "point_audit.json"


def audit_against_dem() -> dict:
    """Compare every survey point with the composed 3DEP surface at its nearest lattice sample.

    This is the stage's accuracy statement *and* the global outlier count: unlike the per-tile numbers in
    ``terrain.json`` (which count a point once per tile whose padded window contains it), every point is
    counted exactly once here. dz = z_point - z_dem, metres.
    """
    import numpy as np

    from ..tiling import Tile, scope_tiles
    from .compose import DemStack
    from .grid import NODATA, SAMPLES, SPACING_M, tile_transform
    from .ingest import INDEX_PATH
    idx = load_index()
    t0 = time.time()
    out = {"n": 0, "no_dem": 0, "by_kind": {}, "dz": []}
    dz_all: list[np.ndarray] = []
    kind_all: list[np.ndarray] = []
    with DemStack(INDEX_PATH) as stack:
        for t in scope_tiles():
            sel = idx.query_bbox(t.x0, t.y0, t.x0 + 1000.0 - 1e-9, t.y0 + 1000.0 - 1e-9)
            if sel.size == 0:
                continue
            tr = tile_transform(t)
            z, _ = stack.read(tr, SAMPLES, SAMPLES)
            col = np.clip(np.rint((idx.x[sel] - t.x0) / SPACING_M).astype(int), 0, SAMPLES - 1)
            row = np.clip(np.rint(((t.y0 + 1000.0) - idx.y[sel]) / SPACING_M).astype(int), 0, SAMPLES - 1)
            zd = z[row, col]
            ok = zd != NODATA
            out["no_dem"] += int((~ok).sum())
            dz_all.append(idx.z[sel][ok].astype(np.float64) - zd[ok].astype(np.float64))
            kind_all.append(idx.kind[sel][ok])
    dz = np.concatenate(dz_all) if dz_all else np.zeros(0)
    kd = np.concatenate(kind_all) if kind_all else np.zeros(0, dtype=np.uint8)
    out["n"] = int(dz.size)
    for k, label in KIND_NAME.items():
        m = kd == k
        if not m.any():
            continue
        d = dz[m]
        out["by_kind"][label] = {
            "n": int(d.size), "mean_m": float(d.mean()), "median_m": float(np.median(d)),
            "rms_m": float(np.sqrt((d ** 2).mean())), "p05_m": float(np.percentile(d, 5)),
            "p95_m": float(np.percentile(d, 95)), "max_abs_m": float(np.abs(d).max()),
            "rejected_ge_3m": int((np.abs(d) >= 3.0).sum()),
            "rejected_pct": round(100.0 * float((np.abs(d) >= 3.0).mean()), 4),
            "rms_after_reject_m": float(np.sqrt((d[np.abs(d) < 3.0] ** 2).mean())),
        }
    keep = np.abs(dz) < 3.0
    out["all"] = {"n": int(dz.size), "mean_m": float(dz.mean()), "median_m": float(np.median(dz)),
                  "rms_m": float(np.sqrt((dz ** 2).mean())), "rejected_ge_3m": int((~keep).sum()),
                  "rejected_pct": round(100.0 * float((~keep).mean()), 4),
                  "rms_after_reject_m": float(np.sqrt((dz[keep] ** 2).mean())),
                  "p05_m": float(np.percentile(dz, 5)), "p95_m": float(np.percentile(dz, 95))}
    out.pop("dz")
    out["seconds"] = round(time.time() - t0, 1)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "w") as f:
        json.dump(out, f, indent=1)
    log.info("point audit: %s", out["all"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--audit", action="store_true", help="compare every point with the composed DEM and write point_audit.json")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(build_cache(a.force), indent=1))
    if a.audit:
        print(json.dumps(audit_against_dem(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
