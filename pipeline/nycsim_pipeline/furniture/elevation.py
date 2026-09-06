"""Ground elevation for props (NAVD88 metres) from real survey points, not from the terrain grid.

The per-tile terrain rasters (``tiles/{tile}/terrain.png``, DATA_CONTRACTS §3) do not exist yet, so props are
placed on a ground model built directly from the two *measured* elevation sources the city publishes:

* **Planimetric spot elevations** (``plan_elevation_points``, OTI 2022 photogrammetry, ``sub_code`` 300000):
  376,133 points captured in the centre of the roadbed and on interior sidewalks at every intersection and every
  200 ft. Vertical accuracy ASPRS 1"=100' Class 2. This is exactly where street furniture stands.
* **Building ground elevations** (``buildings/buildings_base.parquet``, LiDAR-derived ``ground_z`` at the footprint
  centroid, 1,083,026 points) fill the block interiors, parks and rail yards where no spot elevation was captured.

``sample`` returns inverse-distance-weighted elevation over the ``k`` nearest reference points and a ``z_source``
code (``catalog.Z_SOURCE``): ``spot_elev`` (3) when the nearest reference point is within ``NEAR_M`` metres,
``spot_elev_far`` (4) when it is further (open water, the middle of a runway, an offshore pier) — those are
extrapolations and are flagged as such in the props table.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
from scipy.spatial import cKDTree

from ..crs import US_SURVEY_FOOT_M, transformer
from ..paths import PROCESSED, RAW
from .catalog import Z_SOURCE

log = logging.getLogger("nycsim.furniture.elevation")

ELEVATION_POINTS = RAW / "nyc_opendata" / "plan_elevation_points.geojson"
BUILDINGS_BASE = PROCESSED / "buildings" / "buildings_base.parquet"

SUB_SPOT = "300000"      # Spot Elevation (roadbed / interior sidewalk)
SUB_BRIDGE = "300020"    # Bridge Elevation (a subset of spot elevations, on bridge decks)
SUB_WATER = "301000"     # Water Elevation (standing water surface)
SUB_BUILDING = "302000"  # Building Elevation (top of roof — never used as ground)

NEAR_M = 80.0            # nearest reference point further than this -> z_source = spot_elev_far
IDW_K = 4
IDW_EPS_M = 0.5          # softening distance so a prop sitting on a reference point does not divide by zero


@dataclass(frozen=True)
class ElevationPoints:
    """Planimetric elevation points of one sub-code, already in NYC_TM metres / NAVD88 metres."""

    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    sub_code: np.ndarray

    def __len__(self) -> int:
        return int(self.x.size)

    def select(self, sub_code: str) -> "ElevationPoints":
        m = self.sub_code == sub_code
        return ElevationPoints(self.x[m], self.y[m], self.z[m], self.sub_code[m])


def load_elevation_points(path: Path = ELEVATION_POINTS, sub_codes: tuple[str, ...] = (SUB_SPOT, SUB_BRIDGE),
                          batch_size: int = 200_000) -> ElevationPoints:
    """Stream ``plan_elevation_points.geojson`` (330 MB, one line) and keep the requested sub-codes.

    Streaming through pyogrio/GDAL keeps peak RSS around 450 MB; the whole file never exists as Python objects.
    Elevations are published in feet (US survey foot) and are converted to metres here.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id plan_elevation_points")
    tr = transformer("WGS84", "NYC_TM")
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    zs: list[np.ndarray] = []
    cs: list[np.ndarray] = []
    kept = total = 0
    with pyogrio.open_arrow(path, columns=["elevation", "sub_code"], batch_size=batch_size) as (_meta, stream):
        reader = pa.RecordBatchReader.from_stream(stream)
        for batch in reader:
            total += batch.num_rows
            sub = np.asarray(batch.column("sub_code").to_pylist(), dtype=object)
            keep = np.isin(sub, np.asarray(sub_codes, dtype=object))
            if not keep.any():
                continue
            elev = np.array([float(v) if v not in (None, "") else np.nan
                             for v in batch.column("elevation").to_pylist()], dtype=np.float64)
            wkb = batch.column("wkb_geometry").to_pylist()
            # Point WKB: 1 byte order + 4 type + 8 x + 8 y  (little-endian from GDAL)
            idx = np.flatnonzero(keep & np.isfinite(elev))
            if idx.size == 0:
                continue
            buf = np.frombuffer(b"".join(wkb[i][5:21] for i in idx), dtype="<f8").reshape(-1, 2)
            x, y = tr.transform(buf[:, 0], buf[:, 1])
            xs.append(np.asarray(x))
            ys.append(np.asarray(y))
            zs.append(elev[idx] * US_SURVEY_FOOT_M)
            cs.append(sub[idx].astype("U6"))
            kept += idx.size
    pts = ElevationPoints(np.concatenate(xs), np.concatenate(ys), np.concatenate(zs), np.concatenate(cs))
    log.info("elevation points: %d of %d features kept (sub_codes %s)", kept, total, ",".join(sub_codes))
    return pts


def load_building_grades(path: Path = BUILDINGS_BASE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Footprint centroids + LiDAR ground elevation from the buildings stage (metres, NAVD88)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; the buildings stage must run before furniture")
    t = pq.read_table(path, columns=["centroid_x", "centroid_y", "ground_z"])
    x = t.column("centroid_x").to_numpy(zero_copy_only=False).astype(np.float64)
    y = t.column("centroid_y").to_numpy(zero_copy_only=False).astype(np.float64)
    z = t.column("ground_z").to_numpy(zero_copy_only=False).astype(np.float64)
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    log.info("building grades: %d of %d usable", int(ok.sum()), int(ok.size))
    return x[ok], y[ok], z[ok]


class GroundModel:
    """IDW ground elevation over spot elevations + building grades."""

    def __init__(self, x: np.ndarray, y: np.ndarray, z: np.ndarray, *, n_spot: int) -> None:
        if x.size == 0:
            raise ValueError("GroundModel needs at least one reference point")
        self.z = np.asarray(z, dtype=np.float64)
        self.n_spot = int(n_spot)
        self.n_points = int(x.size)
        self.tree = cKDTree(np.column_stack([np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)]))
        log.info("ground model: %d reference points (%d spot elevations, %d building grades)",
                 self.n_points, self.n_spot, self.n_points - self.n_spot)

    @classmethod
    def build(cls, elevation_path: Path = ELEVATION_POINTS, buildings_path: Path = BUILDINGS_BASE) -> "GroundModel":
        pts = load_elevation_points(elevation_path, sub_codes=(SUB_SPOT,))
        bx, by, bz = load_building_grades(buildings_path)
        return cls(np.concatenate([pts.x, bx]), np.concatenate([pts.y, by]), np.concatenate([pts.z, bz]), n_spot=len(pts))

    def sample(self, x: np.ndarray, y: np.ndarray, k: int = IDW_K, chunk: int = 200_000) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(z_m, z_source)`` for query points. Chunked so peak memory stays flat for millions of props."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        n = x.size
        out_z = np.empty(n, dtype=np.float64)
        out_s = np.empty(n, dtype=np.int8)
        kk = min(k, self.n_points)
        for s in range(0, n, chunk):
            e = min(s + chunk, n)
            d, i = self.tree.query(np.column_stack([x[s:e], y[s:e]]), k=kk, workers=1)
            if kk == 1:
                d = d[:, None]
                i = i[:, None]
            w = 1.0 / (d + IDW_EPS_M)
            out_z[s:e] = (w * self.z[i]).sum(axis=1) / w.sum(axis=1)
            out_s[s:e] = np.where(d[:, 0] <= NEAR_M, Z_SOURCE["spot_elev"], Z_SOURCE["spot_elev_far"]).astype(np.int8)
        return out_z, out_s
