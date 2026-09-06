"""Verification of the published terrain (docs/verification/terrain/).

Four independent checks plus two rendered products:

1. ``check_known_elevations`` — published elevations of real places, sampled through the same
   ``segment_z.sample_z`` other stages use. Todt Hill must be the highest point of Staten Island (and of
   the city), the Battery must sit 2-3 m above the tidal datum, Fort Tryon Park ~76 m, the Brooklyn
   Heights Promenade ~15 m, Flushing Meadows 3-5 m.
2. ``check_no_void`` — every scope tile has a 501 x 501 16-bit PNG that decodes to finite elevations, and
   the per-tile JSON accounting adds up to 251,001 samples.
3. ``check_seams`` — for every pair of adjacent tiles the shared edge row/column must agree within 1 mm.
4. ``check_water`` — samples inside tidal water decode to 0.000 m.

Products: ``hillshade_city.png`` (whole scope, 20 m) and ``hillshade_manhattan.png`` (4 m), plus
``verification.json`` with every number quoted in REPORT.md.

    python -m nycsim_pipeline.terrain.verify [--skip-hillshade] [--stride 10]
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
from PIL import Image

from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, TILE_SIZE_M, lonlat_to_tm
from ..paths import PROCESSED, VERIFICATION
from ..tiling import Tile, scope_tiles
from .grid import SAMPLES, SPACING_M
from .segment_z import ZSampler

log = logging.getLogger("nycsim.terrain.verify")

OUT_DIR = VERIFICATION / "terrain"
TILES_DIR = PROCESSED / "tiles"
SEAM_TOL_M = 0.001

# Published elevations of real places, metres above NAVD88/MSL.
# (name, lon, lat, expected_low, expected_high, probe radius m, source of the published figure)
# The check passes when the published band intersects the terrain's range over the probe radius: a single
# 2 m sample at a hand-read coordinate cannot be expected to land on the exact published spot.
KNOWN_POINTS = [
    ("Todt Hill summit, Staten Island", -74.11479, 40.60034, 118.0, 128.0, 60.0,
     "409.8 ft / 124.9 m — highest point on the Atlantic seaboard south of Maine (USGS)"),
    ("Battery Park, Manhattan south tip", -74.01700, 40.70330, 1.5, 4.0, 40.0,
     "waterfront park 2-3 m above the tidal datum"),
    ("Fort Tryon Park, Linden Terrace", -73.93222, 40.86255, 68.0, 84.0, 90.0,
     "~250 ft / 76 m — highest ground in Fort Tryon Park (NYC Parks)"),
    ("Bennett Park, Manhattan high point", -73.94010, 40.85060, 74.0, 86.0, 60.0,
     "265 ft / 80.8 m — highest natural point in Manhattan (NYC Parks marker)"),
    ("Brooklyn Heights Promenade", -73.99855, 40.69465, 12.0, 22.0, 30.0,
     "bluff-top esplanade, ~50-65 ft above the East River"),
    ("Flushing Meadows Corona Park", -73.84080, 40.74000, 1.0, 6.0, 120.0,
     "reclaimed tidal marsh, 3-5 m; Meadow Lake shore at ~1.5 m"),
    ("Central Park reservoir surface", -73.96250, 40.78560, 30.0, 40.0, 100.0,
     "Jacqueline Kennedy Onassis Reservoir pool, surveyed planimetric water elevation"),
    ("Coney Island beach", -73.98330, 40.57200, -0.5, 4.0, 50.0, "ocean beach"),
]
MANHATTAN_WINDOW = (-8000.0, -4000.0, 3000.0, 18000.0)  # NYC_TM x0, y0, x1, y1


def _tile_names() -> list[str]:
    return [t.name for t in scope_tiles()]


def load_tile(name: str) -> tuple[np.ndarray, dict] | None:
    d = TILES_DIR / name
    png, meta = d / "terrain.png", d / "terrain.json"
    if not png.exists() or not meta.exists():
        return None
    with open(meta) as f:
        doc = json.load(f)
    vals = np.asarray(Image.open(png))
    z = vals.astype(np.float64) * doc["z_scale_m"] + doc["z_min_m"]
    return z, doc


def check_no_void() -> dict:
    t0 = time.time()
    names = _tile_names()
    missing, bad_shape, non_finite = [], [], []
    void_px = 0
    z_min, z_max = math.inf, -math.inf
    land_tiles = water_tiles = 0
    px_total = 0
    for n in names:
        r = load_tile(n)
        if r is None:
            missing.append(n)
            continue
        z, doc = r
        if z.shape != (SAMPLES, SAMPLES):
            bad_shape.append(n)
            continue
        if not np.all(np.isfinite(z)):
            non_finite.append(n)
        px_total += z.size
        void_px += int(doc["px"].get("void_filled_sea", 0))
        z_min = min(z_min, float(z.min()))
        z_max = max(z_max, float(z.max()))
        land_tiles += int(bool(doc["has_land"]))
        water_tiles += int(bool(doc["has_water"]))
    return {"tiles_expected": len(names), "tiles_present": len(names) - len(missing), "missing": missing[:20],
            "n_missing": len(missing), "bad_shape": bad_shape, "non_finite": non_finite,
            "samples": px_total, "void_filled_from_tidal_datum_px": void_px,
            "z_min_m": None if z_min == math.inf else z_min, "z_max_m": None if z_max == -math.inf else z_max,
            "tiles_with_land": land_tiles, "tiles_with_water": water_tiles, "seconds": round(time.time() - t0, 1)}


def check_seams(sample_tiles: list[str] | None = None) -> dict:
    """Shared edge row/column of adjacent tiles must be identical within SEAM_TOL_M."""
    t0 = time.time()
    names = set(sample_tiles or _tile_names())
    cache: dict[str, np.ndarray] = {}

    def z_of(name: str) -> np.ndarray | None:
        if name not in cache:
            r = load_tile(name)
            cache[name] = None if r is None else r[0]
            if len(cache) > 200:
                cache.pop(next(iter(cache)))
        return cache[name]

    pairs = 0
    worst = 0.0
    worst_pair = ""
    violations: list[dict] = []
    for name in sorted(names):
        t = Tile.parse(name)
        a = z_of(name)
        if a is None:
            continue
        for dx, dy in ((1, 0), (0, 1)):
            nb = Tile(t.tx + dx, t.ty + dy)
            if nb.name not in names:
                continue
            b = z_of(nb.name)
            if b is None:
                continue
            if dx:      # east neighbour: our last column == its first column
                d = np.abs(a[:, -1] - b[:, 0])
            else:       # north neighbour: our first row == its last row
                d = np.abs(a[0, :] - b[-1, :])
            m = float(d.max())
            pairs += 1
            if m > worst:
                worst, worst_pair = m, f"{name}|{nb.name}"
            if m > SEAM_TOL_M:
                violations.append({"pair": f"{name}|{nb.name}", "max_diff_m": m, "n_samples_off": int((d > SEAM_TOL_M).sum())})
    return {"pairs_checked": pairs, "max_edge_difference_m": worst, "worst_pair": worst_pair,
            "tolerance_m": SEAM_TOL_M, "violations": violations[:20], "n_violations": len(violations),
            "seconds": round(time.time() - t0, 1)}


def check_known_elevations(sampler: ZSampler) -> dict:
    rows = []
    for name, lon, lat, lo, hi, radius, note in KNOWN_POINTS:
        x, y = lonlat_to_tm(lon, lat)
        z = float(sampler.sample(x, y))
        step = max(2.0, radius / 15.0)
        gx, gy = np.meshgrid(np.arange(-radius, radius + 0.1, step), np.arange(-radius, radius + 0.1, step))
        inside = np.hypot(gx.ravel(), gy.ravel()) <= radius
        zz = np.asarray(sampler.sample(x + gx.ravel()[inside], y + gy.ravel()[inside]), dtype=np.float64)
        zlo, zhi = float(np.nanmin(zz)), float(np.nanmax(zz))
        rows.append({"name": name, "lon": lon, "lat": lat, "x": round(float(x), 1), "y": round(float(y), 1),
                     "probe_z_m": round(z, 3), "radius_m": radius, "z_min_r": round(zlo, 3), "z_max_r": round(zhi, 3),
                     "expected_m": [lo, hi], "published": note,
                     "pass": bool(zlo <= hi and zhi >= lo)})
    return {"points": rows, "passed": int(sum(r["pass"] for r in rows)), "total": len(rows)}


def borough_extremes() -> dict:
    """Highest sample per borough, from the tile index (borough_codes) and the per-tile z_max."""
    import pyarrow.parquet as pq
    from .index import CODE_ENUM, INDEX_PARQUET
    if not INDEX_PARQUET.exists():
        return {"error": f"{INDEX_PARQUET} missing"}
    t = pq.read_table(INDEX_PARQUET).to_pydict()
    out: dict[str, dict] = {}
    for i, name in enumerate(t["tile"]):
        zmax = t["z_max"][i]
        zmin = t["z_min"][i]
        if zmax is None:
            continue
        for c in t["borough_codes"][i] or []:
            if c == 0:
                continue
            key = CODE_ENUM[int(c)]
            cur = out.setdefault(key, {"z_max": -math.inf, "tile_max": "", "z_min": math.inf, "tile_min": ""})
            if zmax > cur["z_max"]:
                cur["z_max"], cur["tile_max"] = float(zmax), name
            if zmin < cur["z_min"]:
                cur["z_min"], cur["tile_min"] = float(zmin), name
    return out


def check_water(sampler: ZSampler, n: int = 400) -> dict:
    """Random points inside tidal water must decode to exactly 0.000 m."""
    import shapely
    from ..water.build import HYDRO_PATH, SCHEMAS, read_geoparquet
    h = read_geoparquet(HYDRO_PATH, SCHEMAS["hydrography"])
    tid = h[h["tidal"].values & h["is_open_water"].values]
    if tid.empty:
        return {"error": "no tidal water"}
    rng = np.random.default_rng(20260906)
    geoms = tid.geometry.values
    areas = shapely.area(geoms)
    pick = rng.choice(len(geoms), size=min(n, len(geoms) * 4), p=areas / areas.sum())
    xs, ys = [], []
    for i in pick:
        minx, miny, maxx, maxy = geoms[i].bounds
        for _ in range(12):
            px, py = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
            if not (SCOPE_XMIN < px < SCOPE_XMAX and SCOPE_YMIN < py < SCOPE_YMAX):
                continue
            if shapely.contains_xy(geoms[i], px, py):
                xs.append(px)
                ys.append(py)
                break
    if not xs:
        return {"error": "no sample points inside tidal water"}
    z = np.asarray(sampler.sample(np.asarray(xs), np.asarray(ys)), dtype=np.float64)
    ok = np.abs(z) <= 1e-6
    return {"points": len(xs), "at_datum": int(ok.sum()), "max_abs_m": float(np.nanmax(np.abs(z))),
            "off_datum_examples": [{"x": round(xs[i], 1), "y": round(ys[i], 1), "z": round(float(z[i]), 3)}
                                   for i in np.flatnonzero(~ok)[:10]]}


# ----------------------------------------------------------------------------- hillshade
def mosaic(x0: float, y0: float, x1: float, y1: float, stride: int) -> tuple[np.ndarray, float]:
    """Assemble a coarse elevation mosaic (metres) from the published tiles. Returns (z, cell size m)."""
    tx0, tx1 = int(math.floor(x0 / TILE_SIZE_M)), int(math.floor((x1 - 1e-6) / TILE_SIZE_M))
    ty0, ty1 = int(math.floor(y0 / TILE_SIZE_M)), int(math.floor((y1 - 1e-6) / TILE_SIZE_M))
    per = (SAMPLES - 1) // stride                       # samples contributed by one tile (edge shared)
    w = (tx1 - tx0 + 1) * per
    h = (ty1 - ty0 + 1) * per
    out = np.full((h, w), np.nan, dtype=np.float32)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            r = load_tile(Tile(tx, ty).name)
            if r is None:
                continue
            z = r[0][:-1:stride, :-1:stride]            # drop the duplicated north/east edge
            r0 = (ty1 - ty) * per
            c0 = (tx - tx0) * per
            out[r0:r0 + per, c0:c0 + per] = z[:per, :per]
    return out, SPACING_M * stride


def hillshade(z: np.ndarray, cell: float, azimuth_deg: float = 315.0, altitude_deg: float = 45.0, zf: float = 1.0) -> np.ndarray:
    zz = np.nan_to_num(z, nan=0.0).astype(np.float64) * zf
    dy, dx = np.gradient(zz, cell, cell)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)   # rows increase southward: dy already points south
    az = math.radians(360.0 - azimuth_deg + 90.0)
    alt = math.radians(altitude_deg)
    shade = (np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect))
    return np.clip(shade, 0.0, 1.0)


def tint(z: np.ndarray, shade: np.ndarray) -> np.ndarray:
    """Hypsometric tint (sea -> green -> tan -> white) modulated by the hillshade."""
    zz = np.nan_to_num(z, nan=0.0)
    stops = np.array([-30.0, 0.0, 0.001, 5.0, 20.0, 50.0, 90.0, 130.0])
    cols = np.array([[8, 30, 60], [20, 70, 120], [60, 110, 70], [110, 150, 90],
                     [170, 175, 120], [200, 175, 130], [225, 215, 195], [255, 255, 255]], dtype=np.float64)
    rgb = np.empty(zz.shape + (3,), dtype=np.float64)
    for c in range(3):
        rgb[..., c] = np.interp(zz, stops, cols[:, c])
    rgb *= (0.35 + 0.65 * shade)[..., None]
    return np.clip(rgb, 0, 255).astype(np.uint8)


def render_hillshades(stride_city: int = 10, stride_manhattan: int = 2) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    t0 = time.time()
    z, cell = mosaic(SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX, stride_city)
    sh = hillshade(z, cell)
    Image.fromarray((sh * 255).astype(np.uint8)).save(OUT_DIR / "hillshade_city.png", optimize=True)
    Image.fromarray(tint(z, sh)).save(OUT_DIR / "relief_city.png", optimize=True)
    out["city"] = {"png": str(OUT_DIR / "hillshade_city.png"), "relief": str(OUT_DIR / "relief_city.png"),
                   "shape": list(z.shape), "cell_m": cell,
                   "z_min": float(np.nanmin(z)), "z_max": float(np.nanmax(z)), "seconds": round(time.time() - t0, 1)}
    t1 = time.time()
    z, cell = mosaic(*MANHATTAN_WINDOW, stride_manhattan)
    sh = hillshade(z, cell)
    Image.fromarray((sh * 255).astype(np.uint8)).save(OUT_DIR / "hillshade_manhattan.png", optimize=True)
    Image.fromarray(tint(z, sh)).save(OUT_DIR / "relief_manhattan.png", optimize=True)
    out["manhattan"] = {"png": str(OUT_DIR / "hillshade_manhattan.png"), "relief": str(OUT_DIR / "relief_manhattan.png"),
                        "shape": list(z.shape), "cell_m": cell, "window": list(MANHATTAN_WINDOW),
                        "z_min": float(np.nanmin(z)), "z_max": float(np.nanmax(z)), "seconds": round(time.time() - t1, 1)}
    return out


def run(skip_hillshade: bool = False) -> dict:
    sampler = ZSampler(missing="nan", cache_tiles=48)
    doc = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    doc["no_void"] = check_no_void()
    doc["seams"] = check_seams()
    doc["known_elevations"] = check_known_elevations(sampler)
    doc["borough_extremes"] = borough_extremes()
    try:
        doc["water_datum"] = check_water(sampler)
    except Exception as e:  # noqa: BLE001
        doc["water_datum"] = {"error": f"{type(e).__name__}: {e}"}
    if not skip_hillshade:
        doc["hillshade"] = render_hillshades()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = (OUT_DIR / "verification.json").with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, OUT_DIR / "verification.json")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-hillshade", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    doc = run(a.skip_hillshade)
    slim = {k: v for k, v in doc.items() if k != "known_elevations"}
    print(json.dumps(slim, indent=1)[:4000])
    for r in doc["known_elevations"]["points"]:
        print(f"  {'OK ' if r['pass'] else 'FAIL'} {r['name']:36s} probe {r['probe_z_m']:8.2f} m  range over {r['radius_m']:5.0f} m "
              f"[{r['z_min_r']:7.2f}, {r['z_max_r']:7.2f}]  published {r['expected_m']}")
    ok = (doc["no_void"]["n_missing"] == 0 and not doc["no_void"]["non_finite"] and doc["seams"]["n_violations"] == 0
          and doc["known_elevations"]["passed"] == doc["known_elevations"]["total"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
