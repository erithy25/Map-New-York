"""DOT Automated Traffic Volume Counts (7ym2-wayt) -> per-segment hourly flow by day type.

Rows are 15-minute (a few requests: 10-minute) directional counts keyed by RequestID / SegmentID.
Steps: window filter, holiday exclusion, hour completion (>= 75 % of the slots, scaled to a full hour),
direction sum per segment-hour, weighted mean over days (recency weights), day type 0/1/2.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from ..crs import stateplane_ft_to_tm
from ..paths import RAW

log = logging.getLogger("nycsim.traffic.counts")

ATR_PATH = RAW / "nyc_opendata" / "traffic_volume_auto.csv"
RECENT_YEARS = (2023, 2026)       # counts taken in the last four calendar years (build date 2026-09)
OLDER_YEARS = (2012, 2022)        # fallback window for segments not counted recently
# Recency weights: recent counts dominate, older ones still carry the spatial pattern.
YEAR_WEIGHT = {**{y: 1.0 for y in range(2023, 2027)}, **{y: 0.6 for y in range(2019, 2023)},
               **{y: 0.4 for y in range(2015, 2019)}, **{y: 0.25 for y in range(2012, 2015)}}
MAX_15MIN_VOL = 3000              # > 3000 veh / 15 min / direction is physically impossible on any NYC segment
_WKT = re.compile(r"POINT \(\s*([-\d.]+)\s+([-\d.]+)\s*\)")


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """n-th (1-based; -1 = last) given weekday (Mon=0) of a month."""
    if n > 0:
        d = dt.date(year, month, 1)
        off = (weekday - d.weekday()) % 7
        return d + dt.timedelta(days=off + 7 * (n - 1))
    d = dt.date(year + (month == 12), (month % 12) + 1, 1) - dt.timedelta(days=1)
    off = (d.weekday() - weekday) % 7
    return d - dt.timedelta(days=off)


def us_holidays(year: int) -> set[dt.date]:
    """Federal holidays (observed dates) plus Thanksgiving Friday, Dec 24 and Dec 31 — atypical traffic days."""
    def observed(d: dt.date) -> dt.date:
        if d.weekday() == 5:
            return d - dt.timedelta(days=1)
        if d.weekday() == 6:
            return d + dt.timedelta(days=1)
        return d
    tg = _nth_weekday(year, 11, 3, 4)
    hs = {
        observed(dt.date(year, 1, 1)), _nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3), _nth_weekday(year, 5, 0, -1),
        observed(dt.date(year, 7, 4)), _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 10, 0, 2), observed(dt.date(year, 11, 11)),
        tg, tg + dt.timedelta(days=1), observed(dt.date(year, 12, 25)), dt.date(year, 12, 24), dt.date(year, 12, 31),
    }
    if year >= 2021:
        hs.add(observed(dt.date(year, 6, 19)))
    return hs


@dataclass
class CountData:
    flows: pl.DataFrame     # segment_id, hour, dow, veh_h, n_days, n_dir, weight
    sites: pl.DataFrame     # segment_id, x, y, street, boro, latest_year, n_dir_max, tier, n_hours


def load_counts(path: Path = ATR_PATH, *, recent: tuple[int, int] = RECENT_YEARS, older: tuple[int, int] = OLDER_YEARS) -> CountData:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.download --id traffic_volume_auto`")
    y0, y1 = min(older[0], recent[0]), max(older[1], recent[1])
    hol = sorted({d for y in range(y0, y1 + 1) for d in us_holidays(y)})
    lf = pl.scan_csv(path, infer_schema_length=10000, schema_overrides={"Vol": pl.Float64, "SegmentID": pl.Int64, "RequestID": pl.Int64})
    lf = (lf.filter(pl.col("Yr").is_between(y0, y1) & pl.col("Vol").is_not_null() & (pl.col("Vol") >= 0) & (pl.col("Vol") <= MAX_15MIN_VOL)
                    & pl.col("SegmentID").is_not_null() & pl.col("HH").is_between(0, 23))
            .with_columns(pl.date(pl.col("Yr"), pl.col("M"), pl.col("D")).alias("date"))
            .filter(pl.col("date").is_not_null() & ~pl.col("date").is_in(hol))
            .with_columns(pl.col("date").dt.weekday().alias("wd")))
    # slot length per request from the distinct minute marks (4 -> 15 min, 6 -> 10 min)
    slots = lf.group_by("RequestID").agg(pl.col("MM").n_unique().alias("n_mm")).with_columns(
        pl.when(pl.col("n_mm") >= 6).then(6).when(pl.col("n_mm") >= 4).then(4).otherwise(pl.col("n_mm")).alias("slots_per_hour"))
    hourly = (lf.join(slots, on="RequestID")
              .group_by(["RequestID", "SegmentID", "Direction", "date", "wd", "HH", "slots_per_hour"])
              .agg(pl.col("Vol").sum().alias("vol"), pl.len().alias("n_slots"), pl.col("Yr").first())
              .filter(pl.col("n_slots") >= (pl.col("slots_per_hour") * 0.75))
              .with_columns((pl.col("vol") * pl.col("slots_per_hour") / pl.col("n_slots")).alias("vol_h")))
    # sum over the directions counted in that hour
    seg_hour = (hourly.group_by(["SegmentID", "date", "wd", "HH", "Yr"])
                .agg(pl.col("vol_h").sum().alias("veh_h"), pl.col("Direction").n_unique().alias("n_dir")))
    seg_hour = seg_hour.with_columns(
        pl.when(pl.col("wd") <= 5).then(0).when(pl.col("wd") == 6).then(1).otherwise(2).cast(pl.Int8).alias("dow"),
        pl.col("Yr").replace_strict(YEAR_WEIGHT, default=0.3, return_dtype=pl.Float64).alias("w"),
    )
    flows = (seg_hour.group_by(["SegmentID", "HH", "dow"])
             .agg(((pl.col("veh_h") * pl.col("w")).sum() / pl.col("w").sum()).alias("veh_h"),
                  pl.len().alias("n_days"), pl.col("n_dir").max().alias("n_dir"), pl.col("w").max().alias("weight"))
             .rename({"SegmentID": "segment_id", "HH": "hour"})
             .with_columns(pl.col("hour").cast(pl.Int8), pl.col("n_days").cast(pl.Int32), pl.col("n_dir").cast(pl.Int8))
             .collect(engine="streaming"))
    sites = (lf.group_by("SegmentID")
             .agg(pl.col("WktGeom").drop_nulls().first().alias("wkt"), pl.col("street").drop_nulls().first().alias("street"),
                  pl.col("Boro").drop_nulls().first().alias("boro"), pl.col("Yr").max().alias("latest_year"),
                  pl.col("Direction").n_unique().alias("n_dir_max"))
             .rename({"SegmentID": "segment_id"}).collect(engine="streaming"))
    xy = sites["wkt"].to_list()
    xs, ys = np.full(len(xy), np.nan), np.full(len(xy), np.nan)
    for i, w in enumerate(xy):
        m = _WKT.match(w or "")
        if m:
            xs[i], ys[i] = float(m.group(1)), float(m.group(2))
    ok = np.isfinite(xs) & np.isfinite(ys)
    tx, ty = np.full(len(xy), np.nan), np.full(len(xy), np.nan)
    if ok.any():
        tx[ok], ty[ok] = stateplane_ft_to_tm(xs[ok], ys[ok])
    n_hours = flows.group_by("segment_id").agg(pl.len().alias("n_hours"))
    sites = (sites.with_columns(pl.Series("x", tx), pl.Series("y", ty))
             .with_columns(pl.when(pl.col("latest_year") >= recent[0]).then(pl.lit("recent")).otherwise(pl.lit("older")).alias("tier"))
             .join(n_hours, on="segment_id", how="left").fill_null(0).drop("wkt"))
    log.info("counts: %d segment-hour-daytype flows from %d segments (%d recent %d-%d, %d older %d-%d); %d sites without geometry",
             flows.height, sites.height, int((sites["tier"] == "recent").sum()), recent[0], recent[1],
             int((sites["tier"] == "older").sum()), older[0], older[1], int((~ok).sum()))
    return CountData(flows, sites)
