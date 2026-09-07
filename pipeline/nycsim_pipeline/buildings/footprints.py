"""Load and clean the OTI footprints (``data/processed/buildings/footprints_raw.parquet``).

Cleaning rules (all counted and reported):
* invalid polygons -> ``shapely.make_valid``; only the polygonal parts of the result are kept;
* multipolygons (from the source or from make_valid) are exploded into one row per part, same BIN, ``part_index`` 0..n;
* parts with area < 1 m^2 are dropped (true degenerate geometry);
* centroid, area, tile are recomputed from the cleaned geometry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow.parquet as pq
import shapely

from ..tiling import tile_index_arrays

log = logging.getLogger("nycsim.buildings.footprints")

MIN_PART_AREA_M2 = 1.0

RAW_COLUMNS = ["bin", "doitt_id", "base_bbl", "mappluto_bbl", "name", "construction_year", "feature_code",
               "height_roof", "ground_elevation", "ground_z", "height", "borough", "geometry"]


@dataclass
class Footprints:
    attrs: pl.DataFrame
    geoms: np.ndarray
    stats: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return self.attrs.height


def _polygonal_parts(geom) -> list:
    """Return the Polygon parts of any geometry (drops points/lines produced by make_valid)."""
    if geom is None or geom.is_empty:
        return []
    t = geom.geom_type
    if t == "Polygon":
        return [geom]
    if t == "MultiPolygon":
        return list(geom.geoms)
    if t == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(_polygonal_parts(g))
        return out
    return []


def load_footprints(path: Path, boroughs: list[int] | None = None, limit: int | None = None) -> Footprints:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"footprints parquet missing or empty: {path}")
    table = pq.read_table(path, columns=RAW_COLUMNS)
    df = pl.from_arrow(table.drop(["geometry"]))
    wkb = table["geometry"].to_numpy(zero_copy_only=False)
    if boroughs:
        mask = df["borough"].is_in(boroughs).to_numpy()
        df = df.filter(pl.Series(mask))
        wkb = wkb[mask]
    if limit:
        df = df.head(limit)
        wkb = wkb[:limit]
    n_in = df.height
    log.info("footprints: %d rows read", n_in)
    geoms = shapely.from_wkb(wkb)
    del wkb, table

    stats: dict = {"rows_in": n_in}
    valid = shapely.is_valid(geoms)
    n_invalid = int((~valid).sum())
    stats["invalid_fixed"] = n_invalid
    if n_invalid:
        fixed = shapely.make_valid(geoms[~valid])
        geoms[~valid] = fixed
        log.info("footprints: make_valid applied to %d invalid polygons", n_invalid)

    # the OTI export wraps every footprint in a single-part MultiPolygon: unwrap those vectorised
    type_id = shapely.get_type_id(geoms)
    n_parts = shapely.get_num_geometries(geoms)
    wrapper = (type_id == 6) & (n_parts == 1)
    stats["single_part_multipolygon_unwrapped"] = int(wrapper.sum())
    if wrapper.any():
        geoms[wrapper] = shapely.get_geometry(geoms[wrapper], 0)
        type_id = shapely.get_type_id(geoms)
    # explode genuine multipolygons / collections into polygon parts
    is_poly = type_id == 3
    n_multi = int((~is_poly).sum())
    stats["multipart_rows"] = n_multi
    part_index = np.zeros(len(geoms), dtype=np.int16)
    if n_multi:
        idx_multi = np.nonzero(~is_poly)[0]
        keep_rows: list[int] = []
        new_geoms: list = []
        new_parts: list[int] = []
        for i in idx_multi:
            parts = _polygonal_parts(geoms[i])
            for k, p in enumerate(parts):
                keep_rows.append(int(i))
                new_geoms.append(p)
                new_parts.append(k)
        stats["multipart_parts"] = len(new_geoms)
        single_idx = np.nonzero(is_poly)[0]
        row_order = np.concatenate([single_idx, np.asarray(keep_rows, dtype=np.int64)])
        geoms = np.concatenate([geoms[single_idx], np.asarray(new_geoms, dtype=object)])
        part_index = np.concatenate([np.zeros(len(single_idx), dtype=np.int16), np.asarray(new_parts, dtype=np.int16)])
        df = df[pl.Series(row_order)]
        log.info("footprints: exploded %d multipart rows into %d polygon parts", n_multi, len(new_geoms))
    else:
        stats["multipart_parts"] = 0

    area = shapely.area(geoms)
    tiny = area < MIN_PART_AREA_M2
    stats["dropped_degenerate_lt_1m2"] = int(tiny.sum())
    if tiny.any():
        log.info("footprints: dropping %d degenerate parts (< %.1f m^2)", int(tiny.sum()), MIN_PART_AREA_M2)
        keep = ~tiny
        geoms = geoms[keep]
        area = area[keep]
        part_index = part_index[keep]
        df = df.filter(pl.Series(keep))

    cent = shapely.centroid(geoms)
    cx = shapely.get_x(cent)
    cy = shapely.get_y(cent)
    tx, ty = tile_index_arrays(cx, cy)
    tile = np.char.add(np.char.add(np.char.add("t_", tx.astype(str)), "_"), ty.astype(str))

    df = df.with_columns([
        pl.Series("part_index", part_index),
        pl.Series("footprint_area", area.astype(np.float32)),
        pl.Series("centroid_x", cx),
        pl.Series("centroid_y", cy),
        pl.Series("tx", tx),
        pl.Series("ty", ty),
        pl.Series("tile", tile),
        pl.col("bin").cast(pl.Int64),
        pl.col("doitt_id").fill_null(0).cast(pl.Int64),
        pl.col("borough").cast(pl.Int8),
        pl.col("feature_code").fill_null(0).cast(pl.Int16),
        pl.col("construction_year").cast(pl.Int32),
        pl.col("height").cast(pl.Float32),
        pl.col("ground_z").cast(pl.Float32),
    ])
    stats["rows_out"] = df.height
    stats["placeholder_bins"] = int((df["bin"] % 1_000_000 == 0).sum())
    stats["duplicate_bins"] = int(df.height - df["bin"].n_unique())
    log.info("footprints: %d rows after cleaning (%d placeholder BINs, %d duplicate BIN rows)", df.height,
             stats["placeholder_bins"], stats["duplicate_bins"])
    return Footprints(df, geoms, stats)
