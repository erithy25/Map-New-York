"""Match OSM buildings to BINs by footprint overlap, for the real material / colour / roof / name evidence.

``data/processed/osm/buildings.parquet`` holds 1,247,724 OSM building ways and relations in NYC_TM.  The join to the
1,083,026 OTI footprints is by **largest intersection-over-union**: candidate pairs come from an STRtree intersection
query, the IoU is computed on the real polygons, pairs below :data:`MIN_IOU` are dropped, and each side keeps at most
one partner (greedy by descending IoU, so the match is one-to-one and order-independent).

Only the OSM columns that carry facade evidence are read: ``material`` (``building:material``), ``colour``
(``building:colour``), ``roof_shape``, ``levels`` and ``name``.  ADR-004 makes ``building:material`` /
``building:colour`` the only OSM source that sets ``MATERIAL_REAL``.

Licence of the OSM input: ODbL 1.0, (c) OpenStreetMap contributors (recorded in the parquet metadata).
"""
from __future__ import annotations

import logging

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import shapely

from ..paths import PROCESSED
from . import enums as E

log = logging.getLogger("nycsim.facade.osm")

OSM_BUILDINGS = PROCESSED / "osm" / "buildings.parquet"
MIN_IOU = 0.30
BBOX_MARGIN_M = 60.0
OSM_COLUMNS = ["osm_id", "geometry", "material", "colour", "roof_shape", "levels", "name", "cx", "cy"]


def _read_osm_window(xmin: float, ymin: float, xmax: float, ymax: float) -> pl.DataFrame:
    """OSM buildings whose centroid falls in the window (row-group filtered, columns projected)."""
    pf = pq.ParquetFile(OSM_BUILDINGS)
    frames: list[pl.DataFrame] = []
    for rg in range(pf.metadata.num_row_groups):
        tbl = pf.read_row_group(rg, columns=OSM_COLUMNS)
        df = pl.from_arrow(tbl)
        df = df.filter((pl.col("cx") >= xmin) & (pl.col("cx") <= xmax) & (pl.col("cy") >= ymin) & (pl.col("cy") <= ymax))
        if df.height:
            frames.append(df)
    if not frames:
        return pl.DataFrame(schema={c: pl.Utf8 for c in OSM_COLUMNS})
    return pl.concat(frames, how="vertical")


def match_window(bins: np.ndarray, geoms: np.ndarray, cx: np.ndarray, cy: np.ndarray) -> pl.DataFrame:
    """Match the given footprints against the OSM buildings in their bounding window.

    Returns one row per matched BIN: ``bin, osm_id, iou, osm_material, osm_colour, osm_roof_shape, osm_levels,
    osm_name``.
    """
    if len(geoms) == 0:
        return _empty_matches()
    xmin, xmax = float(np.min(cx)) - BBOX_MARGIN_M, float(np.max(cx)) + BBOX_MARGIN_M
    ymin, ymax = float(np.min(cy)) - BBOX_MARGIN_M, float(np.max(cy)) + BBOX_MARGIN_M
    osm = _read_osm_window(xmin, ymin, xmax, ymax)
    if osm.height == 0:
        return _empty_matches()

    og = shapely.from_wkb(osm["geometry"].to_numpy())
    valid = shapely.is_valid(og)
    if not valid.all():
        og = np.where(valid, og, shapely.make_valid(og))
    tree = shapely.STRtree(og)
    qi, ti = tree.query(geoms, predicate="intersects")
    if len(qi) == 0:
        return _empty_matches()

    a = geoms[qi]
    b = og[ti]
    inter = shapely.area(shapely.intersection(a, b))
    union = shapely.area(a) + shapely.area(b) - inter
    with np.errstate(invalid="ignore", divide="ignore"):
        iou = np.where(union > 0, inter / union, 0.0)
    keep = iou >= MIN_IOU
    qi, ti, iou = qi[keep], ti[keep], iou[keep]
    if len(qi) == 0:
        return _empty_matches()

    # greedy one-to-one by descending IoU (deterministic: ties broken by (bin, osm_id))
    osm_ids = osm["osm_id"].to_numpy()
    order = np.lexsort((osm_ids[ti], bins[qi], -iou))
    qi, ti, iou = qi[order], ti[order], iou[order]
    seen_b = np.zeros(len(bins), dtype=bool)
    seen_o = np.zeros(len(og), dtype=bool)
    sel = np.zeros(len(qi), dtype=bool)
    for k in range(len(qi)):
        if seen_b[qi[k]] or seen_o[ti[k]]:
            continue
        seen_b[qi[k]] = True
        seen_o[ti[k]] = True
        sel[k] = True
    qi, ti, iou = qi[sel], ti[sel], iou[sel]

    def col(name: str) -> np.ndarray:
        return osm[name].fill_null("").to_numpy()[ti]

    lv = osm["levels"].to_numpy()[ti]
    return pl.DataFrame({
        "bin": bins[qi].astype(np.int64),
        "osm_id": osm_ids[ti].astype(np.int64),
        "osm_iou": iou.astype(np.float32),
        "osm_material_str": col("material"),
        "osm_colour_str": col("colour"),
        "osm_roof_shape": col("roof_shape"),
        "osm_levels": np.nan_to_num(lv.astype(np.float64), nan=0.0).astype(np.int16),
        "osm_name": col("name"),
    })


def _empty_matches() -> pl.DataFrame:
    return pl.DataFrame(schema={
        "bin": pl.Int64, "osm_id": pl.Int64, "osm_iou": pl.Float32, "osm_material_str": pl.Utf8,
        "osm_colour_str": pl.Utf8, "osm_roof_shape": pl.Utf8, "osm_levels": pl.Int16, "osm_name": pl.Utf8,
    })


def encode_materials(matches: pl.DataFrame) -> pl.DataFrame:
    """Add the §5 material enum columns derived from the OSM tags (−1 = the tag carries no usable material)."""
    if matches.height == 0:
        return matches.with_columns(pl.lit(-1, dtype=pl.Int8).alias("osm_material"),
                                    pl.lit(-1, dtype=pl.Int8).alias("osm_colour_material"))
    mats = matches["osm_material_str"].to_list()
    cols = matches["osm_colour_str"].to_list()
    m = np.array([E.osm_material_to_enum(v) if v else None for v in mats], dtype=object)
    m = np.array([-1 if v is None else int(v) for v in m], dtype=np.int8)
    c: list[int] = []
    for v in cols:
        rgb = E.parse_colour(v) if v else None
        mat = E.colour_to_masonry_material(rgb) if rgb is not None else None
        c.append(-1 if mat is None else int(mat))
    return matches.with_columns(pl.Series("osm_material", m, dtype=pl.Int8),
                                pl.Series("osm_colour_material", np.array(c, dtype=np.int8), dtype=pl.Int8))
