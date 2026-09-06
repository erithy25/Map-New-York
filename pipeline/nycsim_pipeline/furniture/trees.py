"""2015 Street Tree Census (``uvpi-gqnh``) -> tree props.

The census is a full field inventory: every row is a real tree at real coordinates with the species identified and
the trunk diameter measured at breast height (``tree_dbh``, inches). It also records ``status`` (Alive / Dead /
Stump), ``health``, stewardship and damage observations.

Dead trees and stumps are **excluded** from the props table (a stump is not a street tree and a standing dead tree
has no canopy); the counts of both are reported by :func:`load_trees` and printed in the build summary.

Height is not in the census and is estimated per species and DBH by :mod:`.allometry` (``height_source = 1``).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from ..crs import transformer
from ..paths import RAW
from . import allometry

log = logging.getLogger("nycsim.furniture.trees")

CSV = RAW / "nyc_opendata" / "street_trees_2015.csv"
SOURCE_ID = "street_trees_2015"

COLUMNS = ["tree_id", "tree_dbh", "stump_diam", "status", "health", "spc_latin", "spc_common",
           "latitude", "longitude", "borocode", "curb_loc", "sidewalk", "nta", "address"]

HEALTH_VARIANT = {"Good": 0, "Fair": 1, "Poor": 2}
HEALTH_UNKNOWN = 3


@dataclass(frozen=True)
class TreeCensus:
    df: pl.DataFrame              # alive trees only, with x/y (NYC_TM), dbh_cm, height_m
    n_total: int
    n_alive: int
    n_dead: int
    n_stump: int
    n_status_blank: int
    n_no_coord: int
    n_no_species: int
    n_no_dbh: int
    species_counts: list[tuple[str, str, int]]   # (latin, common, count) sorted desc


def load_trees(path: Path = CSV) -> TreeCensus:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id {SOURCE_ID}")
    df = pl.read_csv(path, columns=COLUMNS, infer_schema_length=0)
    n_total = df.height
    status = df["status"].fill_null("").str.strip_chars()
    n_alive = int((status == "Alive").sum())
    n_dead = int((status == "Dead").sum())
    n_stump = int((status == "Stump").sum())
    n_blank = n_total - n_alive - n_dead - n_stump
    log.info("street trees: %d rows -> alive %d, dead %d, stump %d, other/blank %d", n_total, n_alive, n_dead, n_stump, n_blank)

    alive = df.filter(status == "Alive").with_columns([
        pl.col("latitude").cast(pl.Float64, strict=False),
        pl.col("longitude").cast(pl.Float64, strict=False),
        pl.col("tree_dbh").cast(pl.Float64, strict=False),
        pl.col("tree_id").cast(pl.Int64, strict=False),
        pl.col("spc_latin").fill_null("").str.strip_chars(),
        pl.col("spc_common").fill_null("").str.strip_chars(),
        pl.col("health").fill_null("").str.strip_chars(),
    ])
    good = alive["latitude"].is_finite() & alive["longitude"].is_finite()
    n_no_coord = int((~good).sum())
    if n_no_coord:
        log.warning("%d alive trees without usable coordinates dropped", n_no_coord)
    alive = alive.filter(good)

    lon = alive["longitude"].to_numpy()
    lat = alive["latitude"].to_numpy()
    x, y = transformer("WGS84", "NYC_TM").transform(lon, lat)

    dbh_in = alive["tree_dbh"].fill_null(0.0).to_numpy()
    dbh_cm = allometry.dbh_inches_to_cm(dbh_in)
    n_no_dbh = int((dbh_in <= 0).sum())
    species = alive["spc_latin"].to_list()
    n_no_species = sum(1 for s in species if not s)
    height = allometry.height_array(species, dbh_cm)

    health = alive["health"].to_list()
    variant = np.array([HEALTH_VARIANT.get(h, HEALTH_UNKNOWN) for h in health], dtype=np.int16)

    out = pl.DataFrame({
        "tree_id": alive["tree_id"].fill_null(0).cast(pl.Int64),
        "x": np.asarray(x, dtype=np.float64),
        "y": np.asarray(y, dtype=np.float64),
        "species": species,
        "common": alive["spc_common"].to_list(),
        "dbh_cm": dbh_cm.astype(np.float32),
        "height_m": height.astype(np.float32),
        "variant": variant,
        "borocode": alive["borocode"].fill_null("").to_list(),
        "curb_loc": alive["curb_loc"].fill_null("").to_list(),
        "sidewalk": alive["sidewalk"].fill_null("").to_list(),
        "nta": alive["nta"].fill_null("").to_list(),
    })

    sp = (alive.select([pl.col("spc_latin").alias("latin"), pl.col("spc_common").alias("common")])
          .group_by(["latin", "common"]).len().sort("len", descending=True))
    species_counts = [(r["latin"], r["common"], int(r["len"])) for r in sp.iter_rows(named=True)]

    return TreeCensus(out, n_total, n_alive, n_dead, n_stump, n_blank, n_no_coord, n_no_species, n_no_dbh, species_counts)
