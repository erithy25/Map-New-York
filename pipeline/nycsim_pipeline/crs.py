"""Coordinate reference systems (ADR-002).

World CRS ``NYC_TM``: Transverse Mercator, WGS84, lat_0=40.7, lon_0=-73.95, k=1, metres.
Scale distortion <= 1.2 cm/km inside the project scope.
Vertical: metres above NAVD88. Feet inputs use the US survey foot.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import numpy as np
from pyproj import CRS, Transformer

NYC_TM_PROJ4 = "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
NYC_TM = CRS.from_proj4(NYC_TM_PROJ4)
WGS84 = CRS.from_epsg(4326)
STATE_PLANE_LI_FT = CRS.from_epsg(2263)   # NAD83 / New York Long Island (ftUS)
NAD83 = CRS.from_epsg(4269)
UTM18N = CRS.from_epsg(32618)

US_SURVEY_FOOT_M = 0.3048006096012192
INTL_FOOT_M = 0.3048

TILE_SIZE_M = 1000.0

# Project scope bounding box in NYC_TM (metres), generous margin around the five boroughs + NJ shoreline.
SCOPE_XMIN, SCOPE_XMAX = -30000.0, 24000.0
SCOPE_YMIN, SCOPE_YMAX = -27000.0, 27000.0


@lru_cache(maxsize=None)
def transformer(src: str | int, dst: str | int = "NYC_TM") -> Transformer:
    """Cached pyproj Transformer. ``src``/``dst`` accept 'NYC_TM', 'WGS84', an EPSG int, or any CRS string."""
    def _crs(v):
        if isinstance(v, CRS):
            return v
        if v == "NYC_TM":
            return NYC_TM
        if v == "WGS84":
            return WGS84
        if isinstance(v, int):
            return CRS.from_epsg(v)
        return CRS.from_user_input(v)
    return Transformer.from_crs(_crs(src), _crs(dst), always_xy=True)


def lonlat_to_tm(lon, lat):
    """WGS84 lon/lat (deg) -> NYC_TM x/y (m). Accepts scalars or arrays."""
    return transformer("WGS84", "NYC_TM").transform(lon, lat)


def tm_to_lonlat(x, y):
    return transformer("NYC_TM", "WGS84").transform(x, y)


def stateplane_ft_to_tm(x_ft, y_ft):
    """EPSG:2263 (ftUS) -> NYC_TM (m). pyproj handles the foot unit of 2263 internally."""
    return transformer(2263, "NYC_TM").transform(x_ft, y_ft)


def ft_to_m(v):
    """US survey feet -> metres (works on numpy arrays)."""
    return np.asarray(v, dtype=np.float64) * US_SURVEY_FOOT_M if not np.isscalar(v) else float(v) * US_SURVEY_FOOT_M


def crs_json() -> dict:
    return {
        "schema_version": 1,
        "name": "NYC_TM",
        "proj4": NYC_TM_PROJ4,
        "wkt": NYC_TM.to_wkt(),
        "vertical_datum": "NAVD88 metres",
        "tile_size_m": TILE_SIZE_M,
        "tile_name_format": "t_{tx}_{ty}",
        "scope_bbox_m": [SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX],
        "ue_mapping": "UE.X=east*100, UE.Y=-north*100, UE.Z=up*100 (centimetres, left-handed Z-up)",
    }


def scale_distortion_ppm(lon: float, lat: float) -> float:
    """Return the map-scale distortion of NYC_TM at a point in parts per million (test helper)."""
    from pyproj import Proj
    p = Proj(NYC_TM_PROJ4)
    f = p.get_factors(lon, lat)
    return (f.meridional_scale - 1.0) * 1e6
