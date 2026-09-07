"""1 km tile grid over NYC_TM (ARCHITECTURE §3, DATA_CONTRACTS §2)."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterator

import numpy as np

from .crs import TILE_SIZE_M, SCOPE_XMIN, SCOPE_XMAX, SCOPE_YMIN, SCOPE_YMAX

_TILE_RE = re.compile(r"^t_(-?\d+)_(-?\d+)$")


@dataclass(frozen=True)
class Tile:
    tx: int
    ty: int

    @property
    def name(self) -> str:
        return f"t_{self.tx}_{self.ty}"

    @property
    def x0(self) -> float:
        return self.tx * TILE_SIZE_M

    @property
    def y0(self) -> float:
        return self.ty * TILE_SIZE_M

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x0 + TILE_SIZE_M, self.y0 + TILE_SIZE_M)

    @staticmethod
    def parse(name: str) -> "Tile":
        m = _TILE_RE.match(name)
        if not m:
            raise ValueError(f"not a tile name: {name!r}")
        return Tile(int(m.group(1)), int(m.group(2)))


def tile_of(x: float, y: float) -> Tile:
    return Tile(math.floor(x / TILE_SIZE_M), math.floor(y / TILE_SIZE_M))


def tile_index_arrays(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.floor(np.asarray(x) / TILE_SIZE_M).astype(np.int32), np.floor(np.asarray(y) / TILE_SIZE_M).astype(np.int32)


def tiles_in_bbox(xmin: float, ymin: float, xmax: float, ymax: float) -> Iterator[Tile]:
    tx0, ty0 = math.floor(xmin / TILE_SIZE_M), math.floor(ymin / TILE_SIZE_M)
    tx1, ty1 = math.floor(max(xmax - 1e-9, xmin) / TILE_SIZE_M), math.floor(max(ymax - 1e-9, ymin) / TILE_SIZE_M)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            yield Tile(tx, ty)


def scope_tiles() -> list[Tile]:
    return list(tiles_in_bbox(SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX))


def parent_tile(tile: Tile, level: int) -> tuple[int, int]:
    """Coarser LOD tile index: level 1 = 4 km, level 2 = 16 km."""
    f = 4 ** level
    return (math.floor(tile.tx / f), math.floor(tile.ty / f))
