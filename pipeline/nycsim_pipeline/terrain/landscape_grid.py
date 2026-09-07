"""The surface Unreal's ``ALandscape`` actually has, as a Python sampler.

``data/processed/tiles/{tile}/terrain.png`` is 501 x 501 samples at 2 m (DATA_CONTRACTS §3), but
that is *not* the surface anything stands on in the engine.  A landscape component's quad count must
be ``SubsectionSizeQuads * NumSubsections`` with ``SubsectionSizeQuads`` in {7, 15, 31, 63, 127,
255}, and 500 quads is divisible by none of them, so ``UNYCTerrainImporter`` resamples the grid to
505 samples = 504 quads = 8 x 8 components of 63 quads at 100000/504 = 198.412698 cm, which still
covers exactly 1000 m (``unreal/NYCSim/Source/NYCSimRuntime/Public/World/NYCTerrainImport.h``).

Anything the pipeline drapes on the terrain has to be draped on *that* surface, not on the source
grid, or it sits at a different height than the ground it is supposed to lie on.  Measured over the
ring vertices of four pavement tiles, the landscape stands a mean **+0.005 m** above the source
heightmap (sd 0.011-0.028 m), and at 0.03-0.32 % of those vertices it is more than **0.10 m** above
it -- higher than the roadbed's own lift, so the terrain would poke through the asphalt.  Peak
observed deviation +0.90 m.  Draping on this grid removes that error at the source.

This module reproduces ``UNYCTerrainImporter::ResampleToLandscapeGrid``
(``Private/World/NYCTerrainImport.cpp:118``) exactly, including that it resamples the **uint16**
values and re-rounds to uint16 (``FMath::RoundToInt32``, half away from zero) -- the residual
quantisation is z_scale_m / 2, about 1.25 mm.

What it does **not** reproduce: a landscape quad is drawn and collided as two triangles, not as a
bilinear patch, so inside a quad the engine's surface differs from this sampler by up to the
bilinear-versus-planar gap of one 1.98 m quad.  On NYC's grades that is millimetres to low
centimetres, and it is why the pavement still carries a downward skirt rather than being a
zero-thickness sheet.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

#: Source heightmap, DATA_CONTRACTS §3.
SOURCE_SAMPLES = 501
SOURCE_SPACING_M = 2.0
#: ``UNYCTerrainImporter::LandscapeSamples`` / ``QuadSizeCm``.
LANDSCAPE_SAMPLES = 505
TILE_SIZE_M = 1000.0
LANDSCAPE_SPACING_M = TILE_SIZE_M / (LANDSCAPE_SAMPLES - 1)


def resample_to_landscape_grid(source: np.ndarray, source_samples: int = SOURCE_SAMPLES) -> np.ndarray:
    """501 x 501 uint16 -> 505 x 505 uint16, bilinear, edges bit-exact.

    A transcription of ``UNYCTerrainImporter::ResampleToLandscapeGrid``.  Row order is the PNG's:
    row 0 is the north edge, which is also the landscape's local +Y = south convention, so the two
    agree without a flip.
    """
    src = np.asarray(source)
    if src.shape != (source_samples, source_samples):
        raise ValueError(f"expected {source_samples}x{source_samples}, got {src.shape}")
    dst = LANDSCAPE_SAMPLES
    src_max = source_samples - 1
    ratio = src_max / (dst - 1)

    j = np.arange(dst, dtype=np.float64)
    s = np.minimum(j * ratio, float(src_max))
    i0 = np.floor(s).astype(np.int64)
    i0 = np.where(i0 >= src_max, max(0, src_max - 1), i0)
    w = s - i0
    i1 = np.minimum(i0 + 1, src_max)

    f = src.astype(np.float64)
    # Separable: columns first, then rows, exactly as the C++ nests them.
    cols = f[:, i0] * (1.0 - w) + f[:, i1] * w
    out = cols[i0, :] * (1.0 - w)[:, None] + cols[i1, :] * w[:, None]
    # FMath::RoundToInt32 is round-half-away-from-zero; heights are non-negative, so floor(v + 0.5).
    return np.clip(np.floor(out + 0.5), 0, 65535).astype(np.uint16)


class LandscapeSampler:
    """Bilinear heights, in NYC_TM metres, of the landscape Unreal builds from the tile heightmaps.

    Tiles are loaded lazily and cached; a tile with no heightmap yields NaN so the caller can decide
    what a hole means rather than being handed a silent zero.
    """

    def __init__(self, tiles_dir: Path) -> None:
        self.tiles_dir = Path(tiles_dir)
        self._cache: dict[tuple[int, int], tuple[np.ndarray, dict] | None] = {}
        self.missing: set[str] = set()

    @staticmethod
    def tile_name(tx: int, ty: int) -> str:
        return f"t_{tx}_{ty}"

    def _load(self, tx: int, ty: int):
        key = (tx, ty)
        if key in self._cache:
            return self._cache[key]
        d = self.tiles_dir / self.tile_name(tx, ty)
        png, js = d / "terrain.png", d / "terrain.json"
        if not (png.exists() and js.exists()):
            self.missing.add(self.tile_name(tx, ty))
            self._cache[key] = None
            return None
        try:
            from PIL import Image
            with Image.open(png) as im:
                raw = np.asarray(im)
            meta = json.loads(js.read_text())
        except Exception:
            self.missing.add(self.tile_name(tx, ty))
            self._cache[key] = None
            return None
        samples = int(meta.get("samples", SOURCE_SAMPLES))
        if raw.ndim != 2 or raw.shape != (samples, samples):
            self.missing.add(self.tile_name(tx, ty))
            self._cache[key] = None
            return None
        z_scale = float(meta.get("z_scale_m", 0.0))
        if z_scale > 0.0:
            grid = resample_to_landscape_grid(raw.astype(np.uint16), samples)
        else:
            # A flat tile: the affine mapping degenerates and the importer writes 32768 everywhere,
            # which through the actor transform is exactly z_min (NYCTerrainImport.cpp:242).
            grid = np.full((LANDSCAPE_SAMPLES, LANDSCAPE_SAMPLES), 32768, dtype=np.uint16)
        self._cache[key] = (grid, meta)
        return self._cache[key]

    def height(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Landscape elevation (metres NAVD88) at NYC_TM ``x``/``y``; NaN where a tile is missing."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        z = np.full(x.shape, np.nan, dtype=np.float64)
        txs = np.floor(x / TILE_SIZE_M).astype(np.int64)
        tys = np.floor(y / TILE_SIZE_M).astype(np.int64)
        for tx, ty in {(int(a), int(b)) for a, b in zip(np.atleast_1d(txs).ravel(), np.atleast_1d(tys).ravel())}:
            got = self._load(tx, ty)
            sel = (txs == tx) & (tys == ty)
            if got is None or not np.any(sel):
                continue
            grid, meta = got
            n = LANDSCAPE_SAMPLES
            # Landscape column 0 is the tile's west edge; row 0 is its north edge.
            col = (x[sel] - tx * TILE_SIZE_M) / LANDSCAPE_SPACING_M
            row = ((ty + 1) * TILE_SIZE_M - y[sel]) / LANDSCAPE_SPACING_M
            col = np.clip(col, 0.0, n - 1.0000001)
            row = np.clip(row, 0.0, n - 1.0000001)
            c0 = np.floor(col).astype(np.int64)
            r0 = np.floor(row).astype(np.int64)
            fc, fr = col - c0, row - r0
            c1, r1 = c0 + 1, r0 + 1
            g = grid.astype(np.float64)
            h = (g[r0, c0] * (1 - fc) * (1 - fr) + g[r0, c1] * fc * (1 - fr)
                 + g[r1, c0] * (1 - fc) * fr + g[r1, c1] * fc * fr)
            z[sel] = float(meta.get("z_min_m", 0.0)) + h * float(meta.get("z_scale_m", 0.0))
        return z
