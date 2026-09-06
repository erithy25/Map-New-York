"""MapPLUTO -> per-NTA land-use features (floor-area densities, lot-use mix) and lot-level generators.

``load_lots`` reads the 857,347 MapPLUTO tax lots once (latitude/longitude, floor areas by use,
residential units, land-use class) and places each on an NTA; ``load_landuse`` aggregates that to the
per-NTA regression features and the pedestrian model uses the same lot table as its trip-generator
point cloud, so ``pluto.csv`` (334 MB) is scanned only once per build.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import polars as pl

from ..crs import lonlat_to_tm
from ..paths import RAW
from .geo import NtaTable

log = logging.getLogger("nycsim.traffic.landuse")

PLUTO_PATH = RAW / "nyc_opendata" / "pluto.csv"
SQFT_TO_M2 = 0.09290304
AREA_COLS = ["lotarea", "bldgarea", "comarea", "resarea", "officearea", "retailarea", "garagearea",
             "strgearea", "factryarea", "otherarea"]
# PLUTO landuse: 01-03 residential, 04 mixed res/com, 05 commercial/office, 06 industrial,
# 07 transport/utility, 08 public/institutional, 09 open space, 10 parking, 11 vacant
LANDUSE_GROUPS = {"res": (1, 2, 3), "mixed": (4,), "com": (5,), "ind": (6,), "transport": (7,),
                  "public": (8,), "open": (9,), "parking": (10,), "vacant": (11,)}
FEATURE_COLUMNS = ["res_m2", "com_m2", "office_m2", "retail_m2", "ind_m2", "garage_m2", "bldg_m2",
                   "lot_m2", "units", "n_lots"] + [f"lot_share_{g}" for g in LANDUSE_GROUPS]


def load_lots(nta: NtaTable, path: Path = PLUTO_PATH) -> pl.DataFrame:
    """Lot-level MapPLUTO table in NYC_TM with an ``nta_idx`` column (lots outside every NTA dropped)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.download --id pluto`")
    cols = ["landuse", "numfloors", "unitsres", "latitude", "longitude", *AREA_COLS]
    lf = pl.scan_csv(path, infer_schema_length=0).select(cols)
    df = (lf.with_columns([pl.col(c).cast(pl.Float64, strict=False) for c in cols if c != "landuse"] +
                          [pl.col("landuse").cast(pl.Int32, strict=False)])
          .filter(pl.col("latitude").is_between(40.4, 41.0) & pl.col("longitude").is_between(-74.3, -73.6))
          .collect(engine="streaming"))
    x, y = lonlat_to_tm(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    idx = nta.assign_points(x, y, snap_m=150.0)
    n_out = int((idx < 0).sum())
    df = (df.with_columns(pl.Series("x", x), pl.Series("y", y), pl.Series("nta_idx", idx.astype(np.int32)))
          .filter(pl.col("nta_idx") >= 0)
          .with_columns([pl.col(c).fill_null(0.0).clip(0.0, None) for c in AREA_COLS + ["unitsres", "numfloors"]]))
    log.info("PLUTO: %d lots read, %d outside every NTA, %d kept", df.height + n_out, n_out, df.height)
    return df


def load_landuse(nta: NtaTable, path: Path = PLUTO_PATH, lots: pl.DataFrame | None = None) -> pl.DataFrame:
    """One row per NTA (all of them) with summed floor areas (m²), residential units and lot-use shares."""
    df = load_lots(nta, path) if lots is None else lots
    aggs = [
        (pl.col("resarea").sum() * SQFT_TO_M2).alias("res_m2"),
        (pl.col("comarea").sum() * SQFT_TO_M2).alias("com_m2"),
        (pl.col("officearea").sum() * SQFT_TO_M2).alias("office_m2"),
        (pl.col("retailarea").sum() * SQFT_TO_M2).alias("retail_m2"),
        ((pl.col("factryarea") + pl.col("strgearea")).sum() * SQFT_TO_M2).alias("ind_m2"),
        (pl.col("garagearea").sum() * SQFT_TO_M2).alias("garage_m2"),
        (pl.col("bldgarea").sum() * SQFT_TO_M2).alias("bldg_m2"),
        (pl.col("lotarea").sum() * SQFT_TO_M2).alias("lot_m2"),
        pl.col("unitsres").sum().alias("units"),
        pl.len().cast(pl.Float64).alias("n_lots"),
    ]
    for g, codes in LANDUSE_GROUPS.items():
        aggs.append((pl.col("lotarea").filter(pl.col("landuse").is_in(list(codes))).sum() * SQFT_TO_M2).alias(f"_lot_{g}"))
    agg = df.group_by("nta_idx").agg(aggs).with_columns([pl.col(f"_lot_{g}").fill_null(0.0) for g in LANDUSE_GROUPS])
    for g in LANDUSE_GROUPS:
        agg = agg.with_columns(pl.when(pl.col("lot_m2") > 0).then(pl.col(f"_lot_{g}") / pl.col("lot_m2"))
                               .otherwise(0.0).alias(f"lot_share_{g}"))
    agg = agg.drop([f"_lot_{g}" for g in LANDUSE_GROUPS])
    base = pl.DataFrame({"nta_idx": np.arange(len(nta), dtype=np.int32), "nta_code": nta.codes})
    out = base.join(agg, on="nta_idx", how="left").with_columns([pl.col(c).fill_null(0.0) for c in FEATURE_COLUMNS])
    log.info("land use: %d NTAs with lots, %.1f M m² residential, %.1f M m² office, %.1f M m² retail floor area",
             agg.height, out["res_m2"].sum() / 1e6, out["office_m2"].sum() / 1e6, out["retail_m2"].sum() / 1e6)
    return out
