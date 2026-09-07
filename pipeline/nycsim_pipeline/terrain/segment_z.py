"""``sample_z(x, y)`` — the elevation service every other stage uses (roads, furniture, transit, props).

It reads the *published* terrain (``tiles/{tile}/terrain.png`` + ``terrain.json``), not the intermediate
rasters, so a consumer always gets exactly the surface the engine will load. Tiles are decoded on demand
and kept in an LRU cache (one tile = 501 x 501 float32 = 1.0 MB), so a road stage that walks the city
touches each tile's PNG once.

Interpolation is bilinear on the 2 m lattice. Tile edges are inclusive and shared, and neighbouring tiles
store bit-identical edge rows, so a point on a tile boundary returns the same elevation from either side
and a polyline crossing a seam has no step.

    from nycsim_pipeline.terrain.segment_z import sample_z, segment_z
    z  = sample_z(1234.5, -678.25)              # scalar
    zs = sample_z(xs, ys)                       # numpy arrays
    zs = segment_z(linestring)                  # elevation per vertex of a shapely line

    python -m nycsim_pipeline.terrain.segment_z 980 -3120 [...]   # CLI probe
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
from collections import OrderedDict
from pathlib import Path

import numpy as np
from PIL import Image

from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, TILE_SIZE_M
from ..paths import PROCESSED
from ..tiling import Tile
from .grid import SAMPLES, SPACING_M

log = logging.getLogger("nycsim.terrain.segment_z")

DEFAULT_CACHE_TILES = 64
MISSING_MODES = ("raise", "nan", "nearest")


class TerrainMissing(FileNotFoundError):
    """Raised when a queried point has no published terrain tile."""


class ZSampler:
    """Cached bilinear sampler over the published per-tile heightmaps."""

    def __init__(self, root: Path | None = None, cache_tiles: int = DEFAULT_CACHE_TILES, missing: str = "raise") -> None:
        if missing not in MISSING_MODES:
            raise ValueError(f"missing must be one of {MISSING_MODES}")
        self.root = Path(root) if root is not None else PROCESSED / "tiles"
        self.cache_tiles = int(cache_tiles)
        self.missing = missing
        self._cache: OrderedDict[str, np.ndarray | None] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------ tile loading
    def _load(self, name: str) -> np.ndarray | None:
        d = self.root / name
        png, meta = d / "terrain.png", d / "terrain.json"
        if not png.exists() or not meta.exists():
            return None
        with open(meta) as f:
            doc = json.load(f)
        if int(doc.get("samples", SAMPLES)) != SAMPLES:
            raise ValueError(f"{meta}: samples {doc.get('samples')} != {SAMPLES}")
        vals = np.asarray(Image.open(png))
        if vals.shape != (SAMPLES, SAMPLES):
            raise ValueError(f"{png}: shape {vals.shape} != ({SAMPLES}, {SAMPLES})")
        return (vals.astype(np.float32) * np.float32(doc["z_scale_m"])) + np.float32(doc["z_min_m"])

    def tile_array(self, tile: Tile) -> np.ndarray | None:
        name = tile.name
        with self._lock:
            if name in self._cache:
                self._cache.move_to_end(name)
                self.hits += 1
                return self._cache[name]
        arr = self._load(name)
        with self._lock:
            self.misses += 1
            self._cache[name] = arr
            self._cache.move_to_end(name)
            while len(self._cache) > self.cache_tiles:
                self._cache.popitem(last=False)
        return arr

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        return {"cached_tiles": len(self._cache), "hits": self.hits, "misses": self.misses}

    # ------------------------------------------------------------------ sampling
    def sample(self, x, y):
        xs = np.atleast_1d(np.asarray(x, dtype=np.float64))
        ys = np.atleast_1d(np.asarray(y, dtype=np.float64))
        if xs.shape != ys.shape:
            raise ValueError(f"x and y must have the same shape, got {xs.shape} and {ys.shape}")
        out = np.full(xs.shape, np.nan, dtype=np.float64)
        if self.missing == "nearest":
            xs = np.clip(xs, SCOPE_XMIN, SCOPE_XMAX - 1e-6)
            ys = np.clip(ys, SCOPE_YMIN, SCOPE_YMAX - 1e-6)
        flat_x, flat_y, flat_out = xs.ravel(), ys.ravel(), out.ravel()
        # bilinear needs the cell (i, j) *and* (i+1, j+1); those live in the same tile because the tile
        # stores its northern and eastern edge rows too (inclusive edges), except exactly on the far edge.
        tx = np.floor(flat_x / TILE_SIZE_M).astype(np.int64)
        ty = np.floor(flat_y / TILE_SIZE_M).astype(np.int64)
        key = tx * 1_000_000 + ty
        order = np.argsort(key, kind="stable")
        missing_tiles: set[str] = set()
        start = 0
        ks = key[order]
        while start < ks.size:
            end = start + int(np.searchsorted(ks[start:], ks[start], side="right"))
            sel = order[start:end]
            tile = Tile(int(tx[sel[0]]), int(ty[sel[0]]))
            arr = self.tile_array(tile)
            if arr is None:
                missing_tiles.add(tile.name)
                start = end
                continue
            u = (flat_x[sel] - tile.x0) / SPACING_M                  # 0 .. 500 column
            v = (tile.y0 + TILE_SIZE_M - flat_y[sel]) / SPACING_M    # 0 .. 500 row (north row first)
            u = np.clip(u, 0.0, SAMPLES - 1.0)
            v = np.clip(v, 0.0, SAMPLES - 1.0)
            c0 = np.clip(np.floor(u).astype(np.int64), 0, SAMPLES - 2)
            r0 = np.clip(np.floor(v).astype(np.int64), 0, SAMPLES - 2)
            fu = (u - c0).astype(np.float64)
            fv = (v - r0).astype(np.float64)
            z00 = arr[r0, c0].astype(np.float64)
            z01 = arr[r0, c0 + 1].astype(np.float64)
            z10 = arr[r0 + 1, c0].astype(np.float64)
            z11 = arr[r0 + 1, c0 + 1].astype(np.float64)
            flat_out[sel] = (z00 * (1 - fu) * (1 - fv) + z01 * fu * (1 - fv) + z10 * (1 - fu) * fv + z11 * fu * fv)
            start = end
        if missing_tiles and self.missing == "raise":
            raise TerrainMissing(f"no terrain for {len(missing_tiles)} tile(s): {sorted(missing_tiles)[:5]}")
        res = flat_out.reshape(np.shape(out))
        if np.isscalar(x) or (np.ndim(x) == 0):
            return float(res.reshape(-1)[0])
        return res


_DEFAULT: ZSampler | None = None
_DEFAULT_LOCK = threading.Lock()


def default_sampler() -> ZSampler:
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = ZSampler()
        return _DEFAULT


def sample_z(x, y):
    """Terrain elevation (metres NAVD88) at NYC_TM x/y. Scalars or numpy arrays."""
    return default_sampler().sample(x, y)


def segment_z(geometry_or_coords) -> np.ndarray:
    """Elevation at every vertex of a shapely line/points array — what the roads stage needs per segment."""
    if hasattr(geometry_or_coords, "coords"):
        xy = np.asarray(geometry_or_coords.coords, dtype=np.float64)
    else:
        xy = np.asarray(geometry_or_coords, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] < 2:
        raise ValueError("expected a shapely line or an (N, 2) coordinate array")
    return default_sampler().sample(xy[:, 0], xy[:, 1])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("coords", nargs="+", type=float, help="x1 y1 [x2 y2 ...] in NYC_TM metres")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(a.coords) % 2:
        ap.error("coordinates must come in x y pairs")
    xy = np.asarray(a.coords, dtype=np.float64).reshape(-1, 2)
    z = default_sampler().sample(xy[:, 0], xy[:, 1])
    print(json.dumps([{"x": float(p[0]), "y": float(p[1]), "z_m": float(v)} for p, v in zip(xy, np.atleast_1d(z))], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
