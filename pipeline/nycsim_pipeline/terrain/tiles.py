"""Per-tile terrain: ``data/processed/tiles/{tile}/terrain.png`` + ``terrain.json`` (DATA_CONTRACTS §3).

One tile is built in four steps, all on the global 2 m lattice so that neighbouring tiles agree exactly on
their shared edge row/column:

1. **Compose** the best available 3DEP source at every sample (1 m LiDAR > 1/9" > 1/3"), read into a window
   padded by ``MARGIN`` samples so that step 2 has its full neighbourhood.
2. **Densify** with real survey points (`points.py`): planimetric spot elevations and the 1.08 M building
   ground elevations. Each point yields a correction ``dz = z_point - z_dem`` at its nearest lattice
   sample; a point whose ``|dz| >= IDW_MAX_DZ_M`` is rejected as an outlier (bridge deck, retaining wall,
   a footprint whose LiDAR ground fell on a roof) and counted. The accepted corrections are spread by
   inverse-distance weighting with Franke-Little taper ``w = ((R-d)/(R d))^2`` and blended into the DEM
   with ``alpha = min(1, sum (1 - d/R)^2)``: alpha is 1 at a survey point (the surface passes exactly
   through it) and 0 at 15 m from every point (the DEM is untouched), so the result is continuous, with
   no step at the search radius. Samples with no DEM value but with points inside the radius take the
   inverse-distance mean of the point elevations.
3. **Hydro-flatten** (`hydro.py`): open water to its real surface (0.0 m NAVD88 for everything tidal),
   pier/jetty decks to their surveyed deck elevation, seawall crests where the water mask would otherwise
   flood them. The planimetric shoreline is burned as a hard edge: a shoreline sample whose ground stands
   0.1-6 m above the water plane keeps its ground elevation, so the land/water transition is exactly one
   2 m sample wide instead of a ramp.
4. **Encode**: quantise to the global 2.5 mm grid, crop to 501 x 501 and write a 16-bit PNG (north row
   first) plus ``terrain.json``.

Determinism: every step at a given sample depends only on data within 15 m of it, and the survey points
are summed in ascending global point order, so the same sample computed from two different tiles produces
bit-identical output. This is asserted by ``verify.check_seams``.

    python -m nycsim_pipeline.terrain.tiles [--tiles t_-3_7,...] [--workers 2] [--overwrite] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from ..paths import PROCESSED, tile_dir
from ..tiling import Tile, scope_tiles
from .compose import CODE_NAME, DemStack
from .grid import NODATA, SAMPLES, SPACING_M, Z_SCALE_M, bounds_of, encode_png_values, quantize, tile_transform
from .hydro import HydroLayers
from .ingest import INDEX_PATH
from .points import KIND_BUILDING, KIND_SPOT, PointIndex, load_index

log = logging.getLogger("nycsim.terrain.tiles")

MARGIN = 16                 # samples of context (32 m) — twice the 15 m densification radius
IDW_RADIUS_M = 15.0
IDW_MAX_DZ_M = 3.0
IDW_MIN_D_M = 0.25          # a point closer than this to a sample is treated as being at that distance
SHORE_MIN_RISE_M = 0.10     # a shoreline sample must stand this far above the water plane to stay land
SHORE_MAX_RISE_M = 6.00     # ... and no more than this (above that it is a bridge/building artefact)
SCHEMA = "terrain.tile/1"
TILE_JSON_VERSION = 1
STAMP_K = int(math.ceil((IDW_RADIUS_M + SPACING_M) / SPACING_M))  # sample half-width of a point's stamp


class TileError(RuntimeError):
    pass


@dataclass
class TileResult:
    tile: str
    tx: int
    ty: int
    z_min: float
    z_max: float
    n_points: int
    n_rejected_spot: int
    n_rejected_bldg: int
    n_used_spot: int
    n_used_bldg: int
    n_no_basis: int
    px_1m: int
    px_19: int
    px_13: int
    px_water: int
    px_deck: int
    px_seawall: int
    px_shore_edge: int
    px_void_filled_sea: int
    px_from_points: int
    has_land: bool
    has_water: bool
    seconds: float
    png_bytes: int


def densify(z: np.ndarray, valid: np.ndarray, transform, shape: tuple[int, int], pts: PointIndex,
            bounds: tuple[float, float, float, float]) -> tuple[np.ndarray, dict]:
    """Apply the survey-point correction field in place-safe fashion. Returns (z, statistics)."""
    h, w = shape
    x0c = transform.c + SPACING_M / 2.0          # centre of column 0
    y0c = transform.f - SPACING_M / 2.0          # centre of row 0
    idx = pts.query_bbox(bounds[0] - IDW_RADIUS_M, bounds[1] - IDW_RADIUS_M, bounds[2] + IDW_RADIUS_M, bounds[3] + IDW_RADIUS_M)
    stats = {"n_points": int(idx.size), "rejected_spot": 0, "rejected_bldg": 0, "used_spot": 0, "used_bldg": 0,
             "no_basis": 0, "px_from_points": 0}
    if idx.size == 0:
        return z, stats
    px, py, pz, pk = pts.x[idx], pts.y[idx], pts.z[idx].astype(np.float64), pts.kind[idx]
    col = np.rint((px - x0c) / SPACING_M).astype(np.int64)
    row = np.rint((y0c - py) / SPACING_M).astype(np.int64)
    inside = (col >= 0) & (col < w) & (row >= 0) & (row < h)
    px, py, pz, pk, col, row = px[inside], py[inside], pz[inside], pk[inside], col[inside], row[inside]
    if px.size == 0:
        return z, stats
    basis_valid = valid[row, col]
    dz = np.where(basis_valid, pz - z[row, col], 0.0)
    keep = basis_valid & (np.abs(dz) < IDW_MAX_DZ_M)
    stats["rejected_spot"] = int((basis_valid & ~keep & (pk == KIND_SPOT)).sum())
    stats["rejected_bldg"] = int((basis_valid & ~keep & (pk == KIND_BUILDING)).sum())
    stats["no_basis"] = int((~basis_valid).sum())
    # points without a DEM basis still carry a real elevation: they fill voids (absolute IDW below)
    use = keep | ~basis_valid
    if not use.any():
        return z, stats
    px, py, pz, pk, col, row = px[use], py[use], pz[use], pk[use], col[use], row[use]
    dz = np.where(basis_valid[use], pz - z[row, col], 0.0)
    stats["used_spot"] = int((pk == KIND_SPOT).sum())
    stats["used_bldg"] = int((pk == KIND_BUILDING).sum())

    off = np.arange(-STAMP_K, STAMP_K + 1, dtype=np.int64)
    dcol, drow = np.meshgrid(off, off)
    dcol, drow = dcol.ravel(), drow.ravel()
    cc = col[:, None] + dcol[None, :]
    rr = row[:, None] + drow[None, :]
    ok = (cc >= 0) & (cc < w) & (rr >= 0) & (rr < h)
    sx = x0c + SPACING_M * cc
    sy = y0c - SPACING_M * rr
    d = np.hypot(sx - px[:, None], sy - py[:, None])
    ok &= d <= IDW_RADIUS_M
    if not ok.any():
        return z, stats
    dc = np.maximum(d, IDW_MIN_D_M)
    wgt = np.where(ok, ((IDW_RADIUS_M - dc) / (IDW_RADIUS_M * dc)) ** 2, 0.0)
    # partition-of-unity blend so a lone point does not leave a step at the radius: the correction is the
    # IDW mean of the accepted dz multiplied by alpha = min(1, sum (1 - d/R)^2), which is 1 at a survey
    # point and 0 at 15 m from every point.
    phi = np.where(ok, (1.0 - d / IDW_RADIUS_M) ** 2, 0.0)
    flat = (rr * w + cc)
    flat = np.where(ok, flat, 0)
    n = h * w
    wsum = np.bincount(flat.ravel(), weights=wgt.ravel(), minlength=n)
    dsum = np.bincount(flat.ravel(), weights=(wgt * dz[:, None]).ravel(), minlength=n)
    zsum = np.bincount(flat.ravel(), weights=(wgt * pz[:, None]).ravel(), minlength=n)
    asum = np.bincount(flat.ravel(), weights=phi.ravel(), minlength=n)
    wsum = wsum.reshape(h, w)
    alpha = np.minimum(1.0, asum.reshape(h, w))
    got = wsum > 0
    corr = np.zeros((h, w), dtype=np.float64)
    np.divide(dsum.reshape(h, w), wsum, out=corr, where=got)
    absz = np.zeros((h, w), dtype=np.float64)
    np.divide(zsum.reshape(h, w), wsum, out=absz, where=got)
    out = z.copy()
    apply_corr = got & valid
    out[apply_corr] += (alpha * corr)[apply_corr]
    fill = got & ~valid
    out[fill] = absz[fill]
    stats["px_from_points"] = int(fill.sum())
    valid |= fill
    return out, stats


def write_png(path: Path, values: np.ndarray) -> int:
    """16-bit grayscale PNG, north row first. Returns the file size in bytes."""
    if values.dtype != np.uint16 or values.shape != (SAMPLES, SAMPLES):
        raise TileError(f"{path}: expected uint16 {SAMPLES}x{SAMPLES}, got {values.dtype} {values.shape}")
    tmp = path.with_suffix(".tmp.png")
    Image.fromarray(values).save(tmp, format="PNG", optimize=True)  # uint16 -> mode "I;16"
    back = np.asarray(Image.open(tmp))
    if back.shape != values.shape or not np.array_equal(back.astype(np.uint16), values):
        raise TileError(f"{path}: 16-bit PNG round-trip mismatch")
    os.replace(tmp, path)
    return path.stat().st_size


def build_tile(tile: Tile, stack: DemStack, pts: PointIndex, hydro: HydroLayers, overwrite: bool = True) -> TileResult:
    t0 = time.time()
    d = tile_dir(tile.name)
    png_path, json_path = d / "terrain.png", d / "terrain.json"
    if not overwrite and png_path.exists() and json_path.exists():
        with open(json_path) as f:
            doc = json.load(f)
        return TileResult(tile.name, tile.tx, tile.ty, doc["z_min_m"], doc["z_max_m"], 0, 0, 0, 0, 0, 0,
                          *[doc["px"].get(k, 0) for k in ("3dep_1m", "3dep_19", "3dep_13", "water", "deck", "seawall", "shore_edge", "void_filled_sea", "from_points")],
                          doc["has_land"], doc["has_water"], 0.0, png_path.stat().st_size)

    n = SAMPLES + 2 * MARGIN
    tr = tile_transform(tile, MARGIN)
    bounds = bounds_of(tr, n, n)
    z32, code = stack.read(tr, n, n)
    valid = z32 != NODATA
    z = np.where(valid, z32.astype(np.float64), 0.0)

    z, dstats = densify(z, valid, tr, (n, n), pts, bounds)
    valid_dem = valid.copy()

    th = hydro.tile(tr, (n, n), bounds)
    z_land = z.copy()
    is_water = np.isfinite(th.water_z)
    z = np.where(is_water, th.water_z.astype(np.float64), z)
    valid |= is_water
    is_wall = np.isfinite(th.seawall_z) & is_water
    z = np.where(is_wall, th.seawall_z.astype(np.float64), z)
    # the planimetric shoreline is a hard edge: a shoreline sample that the DEM puts above the water plane
    # keeps its ground elevation, so the land/water transition is one 2 m sample wide instead of a ramp.
    is_shore = (th.shore_edge & is_water & valid_dem
                & (z_land > z + SHORE_MIN_RISE_M) & (z_land <= z + SHORE_MAX_RISE_M))
    z = np.where(is_shore, z_land, z)
    is_deck = np.isfinite(th.deck_z)
    z = np.where(is_deck, th.deck_z.astype(np.float64), z)
    valid |= is_deck

    void = ~valid
    n_void = int(void.sum())
    if n_void:
        z[void] = 0.0  # every remaining void in the scope is open Atlantic beyond the 3DEP tiles: tidal datum

    core = slice(MARGIN, MARGIN + SAMPLES)
    zc = quantize(z[core, core])
    if not np.all(np.isfinite(zc)):
        raise TileError(f"{tile.name}: non-finite elevation after composition")
    span = float(zc.max() - zc.min())
    if span / Z_SCALE_M > 65535:
        raise TileError(f"{tile.name}: elevation span {span:.1f} m exceeds the 16-bit range at {Z_SCALE_M} m")
    vals, z_min, z_scale = encode_png_values(zc)
    if z_scale != Z_SCALE_M:
        raise TileError(f"{tile.name}: z_scale {z_scale} != global quantum {Z_SCALE_M} (seams would not match)")
    png_bytes = write_png(png_path, vals)

    code_c = code[core, core]
    water_c = is_water[core, core]
    deck_c = is_deck[core, core]
    wall_c = is_wall[core, core]
    shore_c = is_shore[core, core]
    void_c = void[core, core]
    land_c = (~water_c | shore_c) & ~void_c  # a sample filled from the tidal datum is open Atlantic, not land
    px = {"3dep_1m": int((code_c == 1).sum()), "3dep_19": int((code_c == 2).sum()), "3dep_13": int((code_c == 3).sum()),
          "water": int(water_c.sum()), "deck": int(deck_c.sum()), "seawall": int(wall_c.sum()),
          "shore_edge": int(shore_c.sum()),
          "void_filled_sea": int(void_c.sum()), "from_points": int(dstats["px_from_points"])}
    sources = [CODE_NAME[c] for c in (1, 2, 3) if px[CODE_NAME[c]] > 0]
    if dstats["used_spot"]:
        sources.append("spot_elev")
    if dstats["used_bldg"]:
        sources.append("bldg_ground")
    if px["water"] or px["deck"]:
        sources.append("hydro_flatten")
    if px["void_filled_sea"]:
        sources.append("tidal_datum")
    doc = {
        "schema_version": TILE_JSON_VERSION, "schema": SCHEMA, "tile": tile.name, "tx": tile.tx, "ty": tile.ty,
        "x0": tile.x0, "y0": tile.y0,
        "z_min_m": float(z_min), "z_scale_m": float(z_scale), "z_max_m": float(z_min + float(vals.max()) * z_scale),
        "samples": SAMPLES, "spacing_m": SPACING_M, "sources": sources, "water_level_m": 0.0,
        "has_land": bool(land_c.any()), "has_water": bool(water_c.any() or deck_c.any()),
        "px": px,
        "points": {"in_range": dstats["n_points"], "used_spot": dstats["used_spot"], "used_bldg": dstats["used_bldg"],
                   "rejected_spot": dstats["rejected_spot"], "rejected_bldg": dstats["rejected_bldg"],
                   "no_dem_basis": dstats["no_basis"], "radius_m": IDW_RADIUS_M, "max_abs_dz_m": IDW_MAX_DZ_M},
    }
    tmp = json_path.with_suffix(".tmp.json")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    os.replace(tmp, json_path)
    return TileResult(tile.name, tile.tx, tile.ty, doc["z_min_m"], doc["z_max_m"], dstats["n_points"],
                      dstats["rejected_spot"], dstats["rejected_bldg"], dstats["used_spot"], dstats["used_bldg"],
                      dstats["no_basis"], px["3dep_1m"], px["3dep_19"], px["3dep_13"], px["water"], px["deck"],
                      px["seawall"], px["shore_edge"], px["void_filled_sea"], px["from_points"], doc["has_land"], doc["has_water"],
                      round(time.time() - t0, 3), png_bytes)


# ----------------------------------------------------------------------------- worker plumbing
_W: dict[str, object] = {}


def _init_worker() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    _W["stack"] = DemStack(INDEX_PATH)
    _W["pts"] = load_index()
    _W["hydro"] = HydroLayers()


def _run_one(args: tuple[int, int, bool]) -> dict:
    tx, ty, overwrite = args
    try:
        r = build_tile(Tile(tx, ty), _W["stack"], _W["pts"], _W["hydro"], overwrite)  # type: ignore[arg-type]
        return {"ok": True, **r.__dict__}
    except Exception as e:  # noqa: BLE001 — one bad tile must not kill the pass
        return {"ok": False, "tile": f"t_{tx}_{ty}", "tx": tx, "ty": ty, "error": f"{type(e).__name__}: {e}"}


def build_all(tiles: list[Tile], workers: int = 2, overwrite: bool = True, progress_every: int = 100) -> dict:
    t0 = time.time()
    jobs = [(t.tx, t.ty, overwrite) for t in tiles]
    results: list[dict] = []
    if workers <= 1:
        _init_worker()
        for j in jobs:
            results.append(_run_one(j))
            if len(results) % progress_every == 0:
                log.info("  %d/%d tiles (%.0fs)", len(results), len(jobs), time.time() - t0)
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as ex:
            for r in ex.map(_run_one, jobs, chunksize=8):
                results.append(r)
                if len(results) % progress_every == 0:
                    log.info("  %d/%d tiles (%.0fs)", len(results), len(jobs), time.time() - t0)
    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    summary = {
        "schema_version": 1, "tiles": len(results), "written": len(ok), "failed": len(bad), "failures": bad[:50],
        "seconds": round(time.time() - t0, 1),
        "z_min": min((r["z_min"] for r in ok), default=None), "z_max": max((r["z_max"] for r in ok), default=None),
        "px": {k: int(sum(r[k] for r in ok)) for k in ("px_1m", "px_19", "px_13", "px_water", "px_deck", "px_seawall", "px_shore_edge", "px_void_filled_sea", "px_from_points")},
        "points": {k: int(sum(r[k] for r in ok)) for k in ("n_used_spot", "n_used_bldg", "n_rejected_spot", "n_rejected_bldg", "n_no_basis")},
        "tiles_with_land": int(sum(1 for r in ok if r["has_land"])),
        "tiles_with_water": int(sum(1 for r in ok if r["has_water"])),
        "png_bytes": int(sum(r["png_bytes"] for r in ok)),
        "slowest": sorted(({"tile": r["tile"], "s": r["seconds"]} for r in ok), key=lambda d: -d["s"])[:10],
    }
    out = PROCESSED / "terrain" / "tile_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(summary, f, indent=1)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles", help="comma separated tile names (default: every scope tile)")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-overwrite", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tiles = [Tile.parse(t) for t in a.tiles.split(",")] if a.tiles else scope_tiles()
    if a.limit:
        tiles = tiles[:a.limit]
    s = build_all(tiles, workers=a.workers, overwrite=not a.no_overwrite)
    print(json.dumps({k: v for k, v in s.items() if k != "failures"}, indent=1))
    if s["failed"]:
        print(json.dumps(s["failures"][:10], indent=1))
    return 1 if s["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
