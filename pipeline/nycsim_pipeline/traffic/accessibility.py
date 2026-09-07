"""Per-NTA accessibility features used by the volume and pedestrian models.

Everything here is derived from data already downloaded:

``subway_entrances``   MTA subway entrances (NYC Open Data ``i9wp-a4ja`` mirror ``subway_entrances.csv``)
                       — entrance count per NTA and the distance from the NTA centroid to the nearest
                       entrance.  Transit accessibility is the strongest single predictor of how much
                       of an NTA's travel is *not* by car.
``d_cbd_km``           straight-line distance from the NTA centroid to Times Square (the centre of the
                       Manhattan core), a proxy for through-traffic pressure.
``hw_lane_km_3km``     motorway/ramp lane-km whose midpoint lies within 3 km of the NTA centroid —
                       proximity to the expressway network, which brings non-local traffic onto the
                       adjoining surface streets.
``garage_per_unit``    PLUTO garage floor area per residential unit — the only citywide, lot-level
                       proxy for household car ownership.
"""
from __future__ import annotations

import logging

import numpy as np
import polars as pl
import shapely
from shapely.strtree import STRtree

from ..crs import lonlat_to_tm
from ..paths import RAW
from .geo import NtaTable
from .segments import SegmentTable

log = logging.getLogger("nycsim.traffic.accessibility")

SUBWAY_PATH = RAW / "nyc_opendata" / "subway_entrances.csv"
# Times Square (Broadway × 7th Av × 42nd St), the conventional centre of the Manhattan core.
CBD_CENTRE_LONLAT = (-73.9855, 40.7580)
HIGHWAY_RADIUS_M = 3000.0

FEATURE_COLUMNS = ["subway_entrances", "log_sub_density", "log_d_subway_km", "log_d_cbd_km",
                   "log_hw_lane_km_3km", "log_garage_per_unit"]


def _subway_points() -> tuple[np.ndarray, np.ndarray]:
    if not SUBWAY_PATH.exists():
        raise FileNotFoundError(f"{SUBWAY_PATH} missing — run `python -m nycsim_pipeline.download --id subway_entrances`")
    df = pl.read_csv(SUBWAY_PATH, infer_schema_length=0)
    lat_col = next((c for c in df.columns if c.lower().replace("_", " ") in ("entrance latitude", "latitude", "lat")), None)
    lon_col = next((c for c in df.columns if c.lower().replace("_", " ") in ("entrance longitude", "longitude", "lon", "long")), None)
    if lat_col is None or lon_col is None:
        raise ValueError(f"{SUBWAY_PATH}: no latitude/longitude columns in {df.columns}")
    lat = df[lat_col].cast(pl.Float64, strict=False).to_numpy()
    lon = df[lon_col].cast(pl.Float64, strict=False).to_numpy()
    ok = np.isfinite(lat) & np.isfinite(lon) & (lat > 40.4) & (lat < 41.0) & (lon > -74.3) & (lon < -73.6)
    if not ok.any():
        raise ValueError(f"{SUBWAY_PATH}: no usable coordinates")
    x, y = lonlat_to_tm(lon[ok], lat[ok])
    return x, y


def load_accessibility(nta: NtaTable, seg: SegmentTable, landuse: pl.DataFrame) -> pl.DataFrame:
    """One row per NTA with :data:`FEATURE_COLUMNS` (plus ``nta_idx``/``nta_code``)."""
    n = len(nta)
    sx, sy = _subway_points()
    idx = nta.assign_points(sx, sy, snap_m=120.0)
    n_ent = np.bincount(idx[idx >= 0], minlength=n).astype(np.float64)
    pts = shapely.points(sx, sy)
    tree = STRtree(pts)
    cent = shapely.points(nta.cx, nta.cy)
    _, near = tree.query_nearest(cent, all_matches=False, return_distance=False)
    d_sub_m = shapely.distance(cent, pts[near])

    cx0, cy0 = lonlat_to_tm(np.array([CBD_CENTRE_LONLAT[0]]), np.array([CBD_CENTRE_LONLAT[1]]))
    d_cbd_km = np.hypot(nta.cx - cx0[0], nta.cy - cy0[0]) / 1000.0

    hw = seg.df.filter(pl.col("is_highway") | (pl.col("rw_type") == 9))
    hx, hy = hw["x_mid"].to_numpy(), hw["y_mid"].to_numpy()
    hlk = hw["lane_km"].to_numpy()
    hw_near = np.zeros(n)
    if len(hx):
        htree = STRtree(shapely.points(hx, hy))
        for i in range(n):
            hit = htree.query(shapely.points(nta.cx[i], nta.cy[i]).buffer(HIGHWAY_RADIUS_M), predicate="intersects")
            hw_near[i] = float(hlk[hit].sum())

    lu = landuse.sort("nta_idx")
    garage_per_unit = lu["garage_m2"].to_numpy() / np.maximum(lu["units"].to_numpy(), 1.0)

    area = np.maximum(nta.area_km2, 0.05)
    out = pl.DataFrame({
        "nta_idx": np.arange(n, dtype=np.int32),
        "nta_code": nta.codes,
        "subway_entrances": n_ent,
        "log_sub_density": np.log1p(n_ent / area),
        "log_d_subway_km": np.log1p(d_sub_m / 1000.0),
        "log_d_cbd_km": np.log1p(d_cbd_km),
        "log_hw_lane_km_3km": np.log1p(hw_near),
        "log_garage_per_unit": np.log1p(garage_per_unit),
    })
    log.info("accessibility: %d subway entrances placed (%d outside every NTA); median centroid->entrance %.0f m; "
             "median highway lane-km within %.0f m %.1f", int(n_ent.sum()), int((idx < 0).sum()),
             float(np.median(d_sub_m)), HIGHWAY_RADIUS_M, float(np.median(hw_near)))
    return out
