"""TLC trip records → for-hire vehicle-km and observed journey speeds per taxi zone, hour and day type.

Inputs (May 2025, the reference month — see ``sources_extra``):

* ``yellow_tripdata_2025-05.parquet``  4,591,845 medallion (yellow) taxi trips
* ``green_tripdata_2025-05.parquet``      55,399 street-hail livery (green/boro) taxi trips
* ``fhvhv_tripdata_2025-05.cols.parquet`` 21,091,193 high-volume FHV (Uber/Lyft) trips

Two products, both keyed by ``(location_id, hour, dow)`` where ``dow`` is 0 weekday / 1 Saturday /
2 Sunday and ``hour`` is the pickup hour (local time, as recorded by TLC):

``vkm``    revenue vehicle-km attributed to the zone.  A trip's distance is split half to the
           pick-up zone and half to the drop-off zone (a trip's kilometres are spread over the
           corridor between them; with 260 zones covering the whole city the half/half split is the
           unbiased first-order allocation and is stated as an approximation in METHOD.md).
           Non-revenue (deadhead / cruising) kilometres are added by ``shares`` using the published
           occupancy ratios, because the trip records only contain occupied trips.
``speed``  distance-weighted mean journey speed (km/h) over trips that *start* in the zone.  This is
           a door-to-door speed and therefore already contains signal, queueing and kerb-manoeuvre
           delay: exactly the space-mean speed the density conversion needs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from ..paths import RAW

log = logging.getLogger("nycsim.traffic.tlc")

TLC_DIR = RAW / "tlc"
REFERENCE_MONTH = "2025-05"
MILE_KM = 1.609344

# Trip filters — TLC files contain GPS/meter faults (0-distance, negative durations, 700 mph trips).
MIN_KM, MAX_KM = 0.3, 60.0
MIN_MIN, MAX_MIN = 1.0, 180.0
MIN_KMH, MAX_KMH = 1.5, 110.0

SOURCES: dict[str, tuple[str, str, str, str, str, str]] = {
    # id: (file, pickup col, dropoff col, PU col, DO col, distance col [miles])
    "yellow": (f"yellow_tripdata_{REFERENCE_MONTH}.parquet", "tpep_pickup_datetime", "tpep_dropoff_datetime",
               "PULocationID", "DOLocationID", "trip_distance"),
    "green": (f"green_tripdata_{REFERENCE_MONTH}.parquet", "lpep_pickup_datetime", "lpep_dropoff_datetime",
              "PULocationID", "DOLocationID", "trip_distance"),
    "fhvhv": (f"fhvhv_tripdata_{REFERENCE_MONTH}.cols.parquet", "pickup_datetime", "dropoff_datetime",
              "PULocationID", "DOLocationID", "trip_miles"),
}


@dataclass
class TlcAggregate:
    vkm: pl.DataFrame       # service, location_id, hour, dow, vkm_per_day, trips_per_day
    speed: pl.DataFrame     # location_id, hour, dow, speed_kmh, trip_km, n_trips
    day_counts: dict[int, int]
    n_trips_read: dict[str, int]
    n_trips_used: dict[str, int]


def _scan(service: str, path: Path) -> pl.LazyFrame:
    f, pu_t, do_t, pu, do, dist = SOURCES[service]
    lf = pl.scan_parquet(path).select([
        pl.col(pu_t).cast(pl.Datetime("us")).alias("t0"),
        pl.col(do_t).cast(pl.Datetime("us")).alias("t1"),
        pl.col(pu).cast(pl.Int32, strict=False).alias("pu"),
        pl.col(do).cast(pl.Int32, strict=False).alias("do"),
        (pl.col(dist).cast(pl.Float64, strict=False) * MILE_KM).alias("km"),
    ])
    return lf.with_columns(
        pl.col("t0").dt.hour().cast(pl.Int8).alias("hour"),
        pl.col("t0").dt.date().alias("date"),
        ((pl.col("t1") - pl.col("t0")).dt.total_seconds() / 60.0).alias("minutes"),
    ).with_columns(
        pl.when(pl.col("t0").dt.weekday() <= 5).then(0)
         .when(pl.col("t0").dt.weekday() == 6).then(1).otherwise(2).cast(pl.Int8).alias("dow")
    ).filter(
        pl.col("pu").is_not_null() & pl.col("do").is_not_null()
        & pl.col("km").is_between(MIN_KM, MAX_KM) & pl.col("minutes").is_between(MIN_MIN, MAX_MIN)
        & pl.col("t0").dt.strftime("%Y-%m").eq(REFERENCE_MONTH)
    ).with_columns((pl.col("km") / (pl.col("minutes") / 60.0)).alias("kmh")).filter(
        pl.col("kmh").is_between(MIN_KMH, MAX_KMH)
    )


def _day_counts(lf: pl.LazyFrame) -> dict[int, int]:
    d = lf.group_by("dow").agg(pl.col("date").n_unique().alias("n_days")).collect(engine="streaming")
    return {int(r["dow"]): int(r["n_days"]) for r in d.iter_rows(named=True)}


def aggregate(dir_: Path = TLC_DIR, *, services: tuple[str, ...] = ("yellow", "green", "fhvhv")) -> TlcAggregate:
    """Aggregate the TLC trip records to zone × hour × day-type vehicle-km and journey speed."""
    vkm_parts: list[pl.DataFrame] = []
    spd_parts: list[pl.DataFrame] = []
    day_counts: dict[int, int] = {}
    n_read: dict[str, int] = {}
    n_used: dict[str, int] = {}
    for svc in services:
        path = dir_ / SOURCES[svc][0]
        if not path.exists():
            raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.traffic.fetch`")
        lf = _scan(svc, path)
        n_read[svc] = int(pl.scan_parquet(path).select(pl.len()).collect().item())
        dc = _day_counts(lf)
        for k, v in dc.items():
            day_counts[k] = max(day_counts.get(k, 0), v)
        pu = (lf.group_by(["pu", "hour", "dow"])
              .agg((pl.col("km").sum() * 0.5).alias("vkm"), (pl.len() * 0.5).alias("trips"))
              .rename({"pu": "location_id"}))
        do = (lf.group_by(["do", "hour", "dow"])
              .agg((pl.col("km").sum() * 0.5).alias("vkm"), (pl.len() * 0.5).alias("trips"))
              .rename({"do": "location_id"}))
        v = (pl.concat([pu, do]).group_by(["location_id", "hour", "dow"])
             .agg(pl.col("vkm").sum(), pl.col("trips").sum())
             .with_columns(pl.lit(svc).alias("service")).collect(engine="streaming"))
        n_used[svc] = int(round(float(v["trips"].sum())))
        vkm_parts.append(v)
        s = (lf.group_by(["pu", "hour", "dow"])
             .agg(pl.col("km").sum().alias("trip_km"), (pl.col("minutes").sum() / 60.0).alias("trip_h"),
                  pl.len().alias("n_trips"))
             .rename({"pu": "location_id"}).collect(engine="streaming"))
        spd_parts.append(s)
        log.info("TLC %s: %d rows, %d usable trips, %d zone-hour-daytype cells", svc, n_read[svc], n_used[svc], v.height)

    if not day_counts:
        raise ValueError("TLC aggregate: no trips survived the filters")
    for d in (0, 1, 2):
        day_counts.setdefault(d, 1)
    vkm = pl.concat(vkm_parts).with_columns(
        (pl.col("vkm") / pl.col("dow").replace_strict(day_counts, return_dtype=pl.Float64)).alias("vkm_per_day"),
        (pl.col("trips") / pl.col("dow").replace_strict(day_counts, return_dtype=pl.Float64)).alias("trips_per_day"),
    ).drop(["vkm", "trips"])
    spd = (pl.concat(spd_parts).group_by(["location_id", "hour", "dow"])
           .agg(pl.col("trip_km").sum(), pl.col("trip_h").sum(), pl.col("n_trips").sum())
           .with_columns((pl.col("trip_km") / pl.col("trip_h")).alias("speed_kmh"))
           .sort(["location_id", "dow", "hour"]))
    log.info("TLC totals: %s trips/day, %.0f revenue veh-km/day; day counts %s; citywide mean journey speed %.1f km/h",
             {k: round(float(vkm.filter(pl.col("service") == k)["trips_per_day"].sum())) for k in services},
             float(vkm["vkm_per_day"].sum()), day_counts,
             float(spd["trip_km"].sum() / spd["trip_h"].sum()))
    return TlcAggregate(vkm, spd, day_counts, n_read, n_used)


def zone_to_nta(vkm: pl.DataFrame, weights: dict[int, list[tuple[int, float]]], n_nta: int,
                *, services: tuple[str, ...] = ("yellow", "green", "fhvhv")) -> dict[str, np.ndarray]:
    """Spread zone-level vehicle-km over NTAs by area weights → ``{service: (n_nta, 24, 3)}`` km/day."""
    out = {s: np.zeros((n_nta, 24, 3)) for s in services}
    lost = 0.0
    for row in vkm.iter_rows(named=True):
        w = weights.get(int(row["location_id"]))
        if not w:
            lost += float(row["vkm_per_day"])
            continue
        arr = out[row["service"]]
        h, d, v = int(row["hour"]), int(row["dow"]), float(row["vkm_per_day"])
        for gi, frac in w:
            arr[gi, h, d] += v * frac
    total = sum(float(a.sum()) for a in out.values())
    log.info("TLC → NTA: %.0f veh-km/day placed, %.0f (%.1f %%) in zones with no NTA overlap (EWR, Governors Island)",
             total, lost, 100 * lost / max(total + lost, 1.0))
    return out


def zone_speed_to_nta(speed: pl.DataFrame, weights: dict[int, list[tuple[int, float]]], n_nta: int) -> tuple[np.ndarray, np.ndarray]:
    """Trip-km-weighted mean journey speed per NTA × hour × day type, and the trip-km behind it."""
    km = np.zeros((n_nta, 24, 3))
    hrs = np.zeros((n_nta, 24, 3))
    for row in speed.iter_rows(named=True):
        w = weights.get(int(row["location_id"]))
        if not w:
            continue
        h, d = int(row["hour"]), int(row["dow"])
        for gi, frac in w:
            km[gi, h, d] += float(row["trip_km"]) * frac
            hrs[gi, h, d] += float(row["trip_h"]) * frac
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.where(hrs > 0, km / hrs, np.nan)
    return v, km
