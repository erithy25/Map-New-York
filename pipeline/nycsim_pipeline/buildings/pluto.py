"""MapPLUTO (64uk-42ks) loading and the BBL join to footprints.

Join order: ``mappluto_bbl`` first, then ``base_bbl`` for the rows that did not join. PLUTO attributes are lot-level;
the *primary* building on each lot (largest non-garage footprint) is the one that inherits ``numfloors``/``yearbuilt``
and the lot-level storefront evidence. Every footprint on the lot inherits ``bldgclass``/``landuse``/``address``.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import polars as pl

from ..crs import US_SURVEY_FOOT_M, stateplane_ft_to_tm

log = logging.getLogger("nycsim.buildings.pluto")

PLUTO_COLUMNS = ["BBL", "bldgclass", "landuse", "numfloors", "yearbuilt", "address", "retailarea", "comarea", "numbldgs",
                 "lotfront", "bldgfront", "bldgdepth", "landmark", "histdist", "xcoord", "ycoord"]

GARAGE_FEATURE_CODE = 5110


def load_pluto(path: Path) -> pl.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"PLUTO csv missing or empty: {path}")
    df = pl.scan_csv(path, infer_schema_length=0).select(PLUTO_COLUMNS).collect()
    n_raw = df.height
    f64 = lambda c: pl.col(c).cast(pl.Float64, strict=False)  # noqa: E731
    df = df.with_columns([
        pl.col("BBL").cast(pl.Int64, strict=False).alias("pl_bbl"),
        pl.col("bldgclass").fill_null("").str.strip_chars().str.to_uppercase().alias("pl_bldgclass"),
        pl.col("landuse").cast(pl.Int64, strict=False).fill_null(0).cast(pl.Int8).alias("pl_landuse"),
        f64("numfloors").alias("pl_numfloors"),
        pl.col("yearbuilt").cast(pl.Int64, strict=False).fill_null(0).cast(pl.Int32).alias("pl_yearbuilt"),
        pl.col("address").fill_null("").str.strip_chars().alias("pl_address"),
        f64("retailarea").fill_null(0.0).alias("pl_retailarea"),
        f64("comarea").fill_null(0.0).alias("pl_comarea"),
        pl.col("numbldgs").cast(pl.Int64, strict=False).fill_null(0).cast(pl.Int32).alias("pl_numbldgs"),
        (f64("lotfront") * US_SURVEY_FOOT_M).cast(pl.Float32).alias("lot_frontage"),
        (f64("bldgfront") * US_SURVEY_FOOT_M).cast(pl.Float32).alias("bldg_frontage"),
        (f64("bldgdepth") * US_SURVEY_FOOT_M).cast(pl.Float32).alias("bldg_depth"),
        pl.col("landmark").fill_null("").alias("pl_landmark"),
        pl.col("histdist").fill_null("").alias("pl_histdist"),
        f64("xcoord").alias("_x"),
        f64("ycoord").alias("_y"),
    ]).drop(PLUTO_COLUMNS)
    df = df.filter(pl.col("pl_bbl").is_not_null()).unique(subset=["pl_bbl"], keep="first")
    # lot centroid State Plane ft -> NYC_TM (m)
    x = df["_x"].to_numpy()
    y = df["_y"].to_numpy()
    ok = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    lx = np.full(len(x), np.nan)
    ly = np.full(len(y), np.nan)
    if ok.any():
        tx, ty = stateplane_ft_to_tm(x[ok], y[ok])
        lx[ok] = tx
        ly[ok] = ty
    df = df.with_columns([pl.Series("lot_x", lx), pl.Series("lot_y", ly)]).drop(["_x", "_y"])
    # zero frontage means unknown
    df = df.with_columns([
        pl.when(pl.col(c) > 0).then(pl.col(c)).otherwise(None).alias(c) for c in ("lot_frontage", "bldg_frontage", "bldg_depth")
    ])
    log.info("pluto: %d rows read, %d unique BBL, %d with lot centroid", n_raw, df.height, int(ok.sum()))
    return df


def join_pluto(attrs: pl.DataFrame, pluto: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """Left-join PLUTO by mappluto_bbl then base_bbl. Adds pl_* columns, ``bbl``, ``pluto_joined``, ``pluto_join_key``."""
    n = attrs.height
    attrs = attrs.with_columns([
        pl.col("mappluto_bbl").cast(pl.Int64, strict=False).alias("_mbbl"),
        pl.col("base_bbl").cast(pl.Int64, strict=False).alias("_bbbl"),
        pl.int_range(pl.len(), dtype=pl.Int64).alias("_row"),
    ])
    keys = set(pluto["pl_bbl"].to_list())
    m_ok = attrs["_mbbl"].is_in(list(keys)).to_numpy() & attrs["_mbbl"].is_not_null().to_numpy()
    b_ok = attrs["_bbbl"].is_in(list(keys)).to_numpy() & attrs["_bbbl"].is_not_null().to_numpy()
    use_base = (~m_ok) & b_ok
    joined = m_ok | b_ok
    join_bbl = np.where(m_ok, attrs["_mbbl"].fill_null(0).to_numpy(), np.where(use_base, attrs["_bbbl"].fill_null(0).to_numpy(), 0))
    attrs = attrs.with_columns([
        pl.Series("_jbbl", join_bbl),
        pl.Series("pluto_joined", joined),
        pl.Series("pluto_join_key", np.where(m_ok, 1, np.where(use_base, 2, 0)).astype(np.int8)),
    ])
    out = attrs.join(pluto, left_on="_jbbl", right_on="pl_bbl", how="left")
    out = out.sort("_row")
    # final bbl: the key that joined, else mappluto_bbl (falls back to base_bbl if mappluto is unparsable)
    out = out.with_columns([
        pl.when(pl.col("pluto_joined")).then(pl.col("_jbbl"))
          .otherwise(pl.coalesce([pl.col("_mbbl"), pl.col("_bbbl"), pl.lit(0)])).cast(pl.Int64).alias("bbl"),
        pl.col("pl_bldgclass").fill_null(""),
        pl.col("pl_landuse").fill_null(0).cast(pl.Int8),
        pl.col("pl_yearbuilt").fill_null(0).cast(pl.Int32),
        pl.col("pl_address").fill_null(""),
        pl.col("pl_retailarea").fill_null(0.0),
        pl.col("pl_comarea").fill_null(0.0),
        pl.col("pl_numbldgs").fill_null(0).cast(pl.Int32),
        pl.col("pl_landmark").fill_null(""),
        pl.col("pl_histdist").fill_null(""),
    ])
    # primary building per lot: largest footprint that is not a garage; garages only if nothing else on the lot
    out = out.with_columns([
        (pl.col("feature_code") == GARAGE_FEATURE_CODE).cast(pl.Int8).alias("_is_garage"),
        pl.len().over("bbl").cast(pl.Int16).alias("n_bldgs_on_lot"),
    ])
    rank = (
        out.select(["_row", "bbl", "_is_garage", "footprint_area"])
        .sort(["bbl", "_is_garage", "footprint_area"], descending=[False, False, True])
        .with_columns(pl.int_range(pl.len()).over("bbl").alias("_rank"))
        .select(["_row", "_rank"])
    )
    out = out.join(rank, on="_row", how="left").sort("_row")
    out = out.with_columns((pl.col("_rank") == 0).alias("is_primary_on_lot")).drop(["_rank", "_is_garage", "_jbbl", "_mbbl", "_bbbl"])
    stats = {
        "rows": n,
        "joined_mappluto_bbl": int(m_ok.sum()),
        "joined_base_bbl_fallback": int(use_base.sum()),
        "joined_total": int(joined.sum()),
        "join_rate": float(joined.sum() / max(n, 1)),
        "unjoined": int(n - joined.sum()),
        "unjoined_garages": int(((~joined) & (attrs["feature_code"].to_numpy() == GARAGE_FEATURE_CODE)).sum()),
        "lots_with_multiple_footprints": int(out.filter(pl.col("n_bldgs_on_lot") > 1)["bbl"].n_unique()),
        "primary_rows": int(out["is_primary_on_lot"].sum()),
    }
    log.info("pluto join: %d/%d (%.2f%%) — %d via mappluto_bbl, %d via base_bbl", stats["joined_total"], n,
             100 * stats["join_rate"], stats["joined_mappluto_bbl"], stats["joined_base_bbl_fallback"])
    return out, stats
