"""NYC Street Centerline (CSCL, Socrata inkn-q76z) loader -> typed GeoDataFrame in NYC_TM."""
from __future__ import annotations

import logging
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from ..crs import NYC_TM, US_SURVEY_FOOT_M
from . import schema as S
from .names import display, normalize

log = logging.getLogger("nycsim.roads.cscl")

CSCL_COLUMNS = [
    "physicalid", "rw_type", "trafdir", "number_travel_lanes", "number_park_lanes", "number_total_lanes",
    "streetwidth", "posted_speed", "bike_lane", "bike_trafdir", "from_level_code", "to_level_code",
    "full_street_name", "boroughcode", "status", "nonped", "truck_route_type", "l_low_hn", "l_high_hn",
    "r_low_hn", "r_high_hn", "segmentlength",
]


def _int_col(s: pd.Series, fill: int) -> np.ndarray:
    v = pd.to_numeric(s, errors="coerce")
    return v.fillna(fill).astype(np.int64).to_numpy()


def load_cscl(path: Path, borough: int | None = None) -> gpd.GeoDataFrame:
    """Read CSCL GeoJSON, merge multipart arcs, reproject to NYC_TM, type the attributes.

    Output columns: segment_id, street_name, name_norm, rw_type, traffic_dir, travel_lanes_raw (-1 = null),
    park_lanes_raw, total_lanes_raw, width_m (NaN = null/0), posted_speed_raw (-1 = null), bike_lane_raw,
    bike_trafdir, level_from, level_to, borough, status, nonped, truck_route_raw, length_m, geometry (2-D).
    """
    t0 = time.time()
    gdf = pyogrio.read_dataframe(str(path), columns=CSCL_COLUMNS)
    log.info("CSCL read: %d features in %.1fs", len(gdf), time.time() - t0)
    if borough is not None:
        gdf = gdf[pd.to_numeric(gdf["boroughcode"], errors="coerce") == borough].copy()
        log.info("CSCL borough %d subset: %d features", borough, len(gdf))
    gdf = gdf[~gdf.geometry.isna() & ~gdf.geometry.is_empty].copy()
    gdf = gdf.to_crs(NYC_TM)

    geoms = gdf.geometry.values
    multi = shapely.get_num_geometries(geoms) > 1
    n_multi = int(multi.sum())
    if n_multi:
        merged = shapely.line_merge(geoms[multi])
        still = shapely.get_num_geometries(merged) > 1
        if still.any():
            # disjoint parts: keep the longest part (real data has a handful of these; counted in the report)
            fixed = []
            for g in merged[still]:
                parts = list(g.geoms)
                fixed.append(max(parts, key=lambda p: p.length))
            merged[still] = np.asarray(fixed, dtype=object)
        geoms = geoms.copy()
        geoms[multi] = merged
    single = shapely.get_num_geometries(geoms) == 1
    geoms = np.where(single, geoms, shapely.get_geometry(geoms, 0))
    # unwrap MultiLineString(1 part) -> LineString
    is_multi_type = shapely.get_type_id(geoms) == shapely.GeometryType.MULTILINESTRING
    geoms[is_multi_type] = shapely.get_geometry(geoms[is_multi_type], 0)
    gdf = gdf.set_geometry(gpd.GeoSeries(geoms, index=gdf.index, crs=NYC_TM))
    n_disjoint = int(shapely.get_num_geometries(merged).__gt__(1).sum()) if n_multi else 0

    out = pd.DataFrame(index=gdf.index)
    out["segment_id"] = _int_col(gdf["physicalid"], -1)
    out["street_name"] = gdf["full_street_name"].map(display).astype(str)
    out["name_norm"] = gdf["full_street_name"].map(normalize).astype(str)
    out["rw_type"] = _int_col(gdf["rw_type"], S.RW_UNKNOWN).astype(np.int8)
    out["traffic_dir"] = gdf["trafdir"].map(S.TRAFDIR_MAP).fillna(S.DIR_NONE).astype(np.int8).to_numpy()
    out["travel_lanes_raw"] = _int_col(gdf["number_travel_lanes"], -1).astype(np.int16)
    out["park_lanes_raw"] = _int_col(gdf["number_park_lanes"], -1).astype(np.int16)
    out["total_lanes_raw"] = _int_col(gdf["number_total_lanes"], -1).astype(np.int16)
    width_ft = pd.to_numeric(gdf["streetwidth"], errors="coerce").to_numpy(dtype=np.float64)
    width_m = width_ft * US_SURVEY_FOOT_M
    width_m[~(width_m > 0.5)] = np.nan
    out["width_m"] = width_m.astype(np.float32)
    out["posted_speed_raw"] = _int_col(gdf["posted_speed"], -1).astype(np.int16)
    out["bike_lane_raw"] = _int_col(gdf["bike_lane"], 0).astype(np.int8)
    out["bike_trafdir"] = gdf["bike_trafdir"].fillna("").astype(str).to_numpy()
    lf = _int_col(gdf["from_level_code"], S.LEVEL_AT_GRADE)
    lt = _int_col(gdf["to_level_code"], S.LEVEL_AT_GRADE)
    lf = np.where((lf < 1) | (lf > 26), S.LEVEL_AT_GRADE, lf)
    lt = np.where((lt < 1) | (lt > 26), S.LEVEL_AT_GRADE, lt)
    out["level_from"] = lf.astype(np.int8)
    out["level_to"] = lt.astype(np.int8)
    out["borough"] = _int_col(gdf["boroughcode"], 0).astype(np.int8)
    out["status"] = _int_col(gdf["status"], 2).astype(np.int8)
    out["nonped"] = gdf["nonped"].fillna("").astype(str).to_numpy()
    out["truck_route_raw"] = _int_col(gdf["truck_route_type"], 0).astype(np.int8)
    out["length_m"] = shapely.length(gdf.geometry.values).astype(np.float32)
    res = gpd.GeoDataFrame(out, geometry=gdf.geometry, crs=NYC_TM)

    # physicalid is the primary key: keep the longest geometry for the few duplicated ids
    dup = res["segment_id"].duplicated(keep=False)
    n_dup = int(dup.sum())
    if n_dup:
        res = res.sort_values(["segment_id", "length_m"], ascending=[True, False])
        res = res[~res["segment_id"].duplicated(keep="first")]
    res = res[res["segment_id"] >= 0].sort_values("segment_id").reset_index(drop=True)
    res.attrs["n_multipart_merged"] = n_multi
    res.attrs["n_disjoint_longest_kept"] = n_disjoint
    res.attrs["n_duplicate_physicalid_rows"] = n_dup
    log.info("CSCL typed: %d segments (%d multipart merged, %d disjoint -> longest part, %d duplicate id rows dropped) in %.1fs",
             len(res), n_multi, n_disjoint, n_dup, time.time() - t0)
    return res
