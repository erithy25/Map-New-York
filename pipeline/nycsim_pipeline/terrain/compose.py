"""Priority composition of the lattice-aligned per-source intermediates into arbitrary windows.

``DemStack.read`` fills a requested lattice window from the best available source at every sample
(1 m LiDAR > 1/9" > 1/3"), returning the elevations and a per-sample source code (0 void, 1 = 1 m,
2 = 1/9", 3 = 1/3"). Because every intermediate shares the global 2 m lattice, this is a pixel copy —
no resampling happens here, so a sample's value is identical whichever tile window requests it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window

from ..paths import REPO_ROOT
from .grid import NODATA, bounds_of, pixel_offset

KIND_CODE = {"1m": 1, "19": 2, "13": 3}
CODE_NAME = {0: "void", 1: "3dep_1m", 2: "3dep_19", 3: "3dep_13"}
MAX_OPEN = 48


@dataclass(frozen=True)
class Layer:
    id: str
    path: Path
    priority: int
    kind: str
    transform: Affine
    width: int
    height: int
    bounds: tuple[float, float, float, float]


class DemStack:
    def __init__(self, index_path: Path):
        with open(index_path) as f:
            doc = json.load(f)
        layers = []
        for key, e in doc["entries"].items():
            t = e["transform"]
            layers.append(Layer(key, REPO_ROOT / e["path"], int(e["priority"]), e["kind"],
                                Affine(t[0], t[1], t[2], t[3], t[4], t[5]), int(e["width"]), int(e["height"]),
                                tuple(bounds_of(Affine(*t), int(e["width"]), int(e["height"])))))
        self.layers = sorted(layers, key=lambda l: (l.priority, l.id))
        self._open: dict[str, rasterio.DatasetReader] = {}

    def close(self) -> None:
        for ds in self._open.values():
            ds.close()
        self._open.clear()

    def __enter__(self) -> "DemStack":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _ds(self, layer: Layer) -> rasterio.DatasetReader:
        ds = self._open.get(layer.id)
        if ds is None:
            if len(self._open) >= MAX_OPEN:
                self.close()
            ds = rasterio.open(layer.path)
            self._open[layer.id] = ds
        return ds

    @staticmethod
    def _intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    def read(self, transform: Affine, width: int, height: int, max_priority: int | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Compose a lattice window. Returns (z float32 with NODATA voids, source code uint8)."""
        z = np.full((height, width), NODATA, dtype=np.float32)
        code = np.zeros((height, width), dtype=np.uint8)
        req = bounds_of(transform, width, height)
        for layer in self.layers:
            if max_priority is not None and layer.priority > max_priority:
                break
            if not self._intersects(layer.bounds, req):
                continue
            col_off, row_off = pixel_offset(layer.transform, transform)
            c0, r0 = max(0, -col_off), max(0, -row_off)
            c1, r1 = min(width, layer.width - col_off), min(height, layer.height - row_off)
            if c1 <= c0 or r1 <= r0:
                continue
            sub = z[r0:r1, c0:c1]
            need = sub == NODATA
            if not need.any():
                continue
            data = self._ds(layer).read(1, window=Window(col_off + c0, row_off + r0, c1 - c0, r1 - r0))
            fill = need & (data != NODATA) & np.isfinite(data)
            sub[fill] = data[fill]
            code[r0:r1, c0:c1][fill] = KIND_CODE[layer.kind]
            if not (z == NODATA).any():
                break
        return z, code

    def coverage(self, transform: Affine, width: int, height: int, max_priority: int | None = None) -> float:
        z, _ = self.read(transform, width, height, max_priority)
        return float((z != NODATA).mean())
