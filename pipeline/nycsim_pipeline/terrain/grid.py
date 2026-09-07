"""The 2 m sample lattice shared by every terrain artefact (DATA_CONTRACTS §3).

Samples live at *even metre* NYC_TM coordinates: ``x = 2 i``, ``y = 2 j``. A 1 km tile therefore holds
501 x 501 samples with its edge rows/columns shared with the neighbours (inclusive edges), which is what
makes tile seams exact. Every raster produced here (per-source intermediates, tiles, overview) is
aligned so that *pixel centres* fall on lattice points; pixel (col, row) of a raster whose top-left
corner is (X0, Y1) is centred at (X0 + 2 col + 1, Y1 - 2 row - 1).
"""
from __future__ import annotations

import math

import numpy as np
from rasterio.transform import Affine

from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, TILE_SIZE_M
from ..tiling import Tile

SPACING_M = 2.0
SAMPLES = int(round(TILE_SIZE_M / SPACING_M)) + 1  # 501, inclusive edges
MARGIN = 64  # samples of context on each side while processing a tile (128 m)
NODATA = -9999.0
Z_SCALE_M = 0.0025  # 16-bit PNG quantum (2.5 mm); DATA_CONTRACTS §3 example value
PNG_MAX = 65535


def snap_down(v: float) -> float:
    return SPACING_M * math.floor(v / SPACING_M + 1e-9)


def snap_up(v: float) -> float:
    return SPACING_M * math.ceil(v / SPACING_M - 1e-9)


def tile_transform(tile: Tile, margin: int = 0) -> Affine:
    """Affine of the (optionally padded) tile raster; pixel centres on the lattice."""
    x0 = tile.x0 - SPACING_M / 2 - margin * SPACING_M
    y1 = tile.y0 + TILE_SIZE_M + SPACING_M / 2 + margin * SPACING_M
    return Affine(SPACING_M, 0.0, x0, 0.0, -SPACING_M, y1)


def tile_shape(margin: int = 0) -> tuple[int, int]:
    n = SAMPLES + 2 * margin
    return (n, n)


def sample_axes(tile: Tile, margin: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """1-D sample coordinates: ``xs`` ascending (west->east), ``ys`` descending (north row first)."""
    k = np.arange(-margin, SAMPLES + margin, dtype=np.float64)
    xs = tile.x0 + SPACING_M * k
    ys = tile.y0 + TILE_SIZE_M - SPACING_M * k
    return xs, ys


def lattice_grid(xmin: float, ymin: float, xmax: float, ymax: float) -> tuple[Affine, int, int]:
    """Smallest lattice-aligned raster (transform, width, height) containing the bbox (inclusive points)."""
    x_lo, x_hi = snap_down(xmin), snap_up(xmax)
    y_lo, y_hi = snap_down(ymin), snap_up(ymax)
    if x_hi <= x_lo or y_hi <= y_lo:
        raise ValueError(f"degenerate bbox {(xmin, ymin, xmax, ymax)}")
    width = int(round((x_hi - x_lo) / SPACING_M)) + 1
    height = int(round((y_hi - y_lo) / SPACING_M)) + 1
    return Affine(SPACING_M, 0.0, x_lo - SPACING_M / 2, 0.0, -SPACING_M, y_hi + SPACING_M / 2), width, height


def scope_grid() -> tuple[Affine, int, int]:
    return lattice_grid(SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX)


def bounds_of(transform: Affine, width: int, height: int) -> tuple[float, float, float, float]:
    """Outer bounds (pixel edges) of a raster."""
    x0, y1 = transform.c, transform.f
    return (x0, y1 - height * SPACING_M, x0 + width * SPACING_M, y1)


def pixel_offset(src: Affine, dst: Affine) -> tuple[int, int]:
    """(col_off, row_off) of ``dst``'s top-left pixel inside a lattice-aligned raster with transform ``src``."""
    dc = (dst.c - src.c) / SPACING_M
    dr = (src.f - dst.f) / SPACING_M
    col, row = int(round(dc)), int(round(dr))
    if abs(dc - col) > 1e-6 or abs(dr - row) > 1e-6:
        raise ValueError(f"rasters are not lattice aligned: {src} vs {dst}")
    return col, row


def quantize(z: np.ndarray) -> np.ndarray:
    """Snap elevations to the global 2.5 mm grid so that neighbouring tiles decode to identical edges."""
    return np.round(np.asarray(z, dtype=np.float64) / Z_SCALE_M) * Z_SCALE_M


def encode_png_values(z_q: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Return (uint16 values, z_min_m, z_scale_m) for a quantized elevation array without NaN/void.

    ``z_scale_m`` is 2.5 mm unless the tile spans more than 163.8 m, in which case it doubles until it fits
    (still a multiple of the global quantum, so shared edges stay bit-identical between neighbours).
    """
    if z_q.size == 0 or not np.all(np.isfinite(z_q)):
        raise ValueError("encode_png_values: array contains NaN/inf or is empty")
    z_min = float(np.round(z_q.min() / Z_SCALE_M) * Z_SCALE_M)
    scale = Z_SCALE_M
    while (z_q.max() - z_min) / scale > PNG_MAX:
        scale *= 2.0
    vals = np.round((z_q - z_min) / scale)
    if vals.min() < 0 or vals.max() > PNG_MAX:
        raise ValueError("encode_png_values: value out of 16-bit range")
    return vals.astype(np.uint16), z_min, scale
