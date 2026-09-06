"""TLC trip records → for-hire vehicle-km and observed journey speeds per taxi zone, hour and day type.

Inputs (May 2025, the reference month — see ``sources_extra``):

* ``yellow_tripdata_2025-05.parquet``  4,591,845 medallion (yellow) taxi trips
* ``green_tripdata_2025-05.parquet``      55,399 street-hail livery (green/boro) taxi trips
* ``fhvhv_tripdata_2025-05.cols.parquet`` 21,091,193 high-volume FHV (Uber/Lyft) trips

Two products, both keyed by ``(location_id, hour, dow)`` where ``dow`` is 0 weekday / 1 Saturday /
2 Sunday and ``hour`` is the pickup hour (local time, as recorded by TLC):

``vkm``    revenue vehicle-km attributed to the zone.  A trip's kilometres are spread along the
           **corridor** between its pick-up and drop-off zones — the straight line between the two
           zone centroids, cut by the NTA boundaries it crosses, so a Greenpoint-to-Midtown trip
           leaves most of its distance in Williamsburg, on the bridge and in Manhattan instead of
           crediting it all to Greenpoint.  Trips that start and end in the same zone are spread
           over that zone's own NTAs by area.  (Splitting half to each endpoint instead put 72 % of
           Greenpoint's midnight traffic down as for-hire; the corridor allocation removes that.)
           Non-revenue (deadhead / cruising) kilometres are added by ``shares`` using the published
           occupancy ratios, because the trip records only contain occupied trips.
``speed``  distance-weighted mean journey speed (km/h) over *short* trips (<= 3 km) that start in the
           zone.  A door-to-door speed already contains signal, queueing and kerb-manoeuvre delay —
           exactly the space-mean speed the density conversion needs — and the 3 km cap keeps the
           trip on the surface streets around the pick-up zone instead of letting a run to an airport
           over the expressways inflate the local speed.  (Midtown zones, weekday: 22.5 km/h at 00:00
           and 12.0 km/h at 16:00 with no cap; 16.4 and 8.9 km/h with it — the latter matches the
           NYC DOT Mobility Report's 4-5 mph Midtown core travel speeds.)
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
# A trip longer than this is assumed to leave the pick-up zone's street network (expressway, bridge).
LOCAL_TRIP_MAX_KM = 3.0

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
        v = (lf.group_by(["pu", "do", "hour", "dow"])
             .agg(pl.col("km").sum().alias("vkm"), pl.len().alias("trips"))
             .with_columns(pl.lit(svc).alias("service")).collect(engine="streaming"))
        n_used[svc] = int(round(float(v["trips"].sum())))
        vkm_parts.append(v)
        s = (lf.filter(pl.col("km") <= LOCAL_TRIP_MAX_KM).group_by(["pu", "hour", "dow"])
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
    wd = vkm.filter(pl.col("dow") == 0)
    log.info("TLC totals: %s trips per average weekday, %.0f revenue veh-km per average weekday; day counts %s; "
             "citywide mean local (<= %.0f km) journey speed %.1f km/h",
             {k: round(float(wd.filter(pl.col("service") == k)["trips_per_day"].sum())) for k in services},
             float(wd["vkm_per_day"].sum()), day_counts, LOCAL_TRIP_MAX_KM,
             float(spd["trip_km"].sum() / spd["trip_h"].sum()))
    return TlcAggregate(vkm, spd, day_counts, n_read, n_used)


def corridor_weights(zones, nta, pairs: list[tuple[int, int]],
                     zone_area_weights: dict[int, list[tuple[int, float]]]) -> dict[tuple[int, int], list[tuple[int, float]]]:
    """For each (pick-up zone, drop-off zone) pair: the share of the trip corridor inside each NTA.

    The corridor is the straight line between the two zone centroids, cut by the NTA polygons.  For
    an intra-zone pair (or a pair whose line misses every NTA) the zone's own area weights are used.
    """
    import shapely
    from shapely.strtree import STRtree

    cent = {int(l): shapely.centroid(g) for l, g in zip(zones.location_ids, zones.geoms)}
    lines: list = []
    keys: list[tuple[int, int]] = []
    out: dict[tuple[int, int], list[tuple[int, float]]] = {}
    for pu, do in pairs:
        if pu == do or pu not in cent or do not in cent:
            w = zone_area_weights.get(pu) or zone_area_weights.get(do)
            if w:
                out[(pu, do)] = w
            continue
        a, b = cent[pu], cent[do]
        lines.append(shapely.linestrings([[shapely.get_x(a), shapely.get_y(a)],
                                          [shapely.get_x(b), shapely.get_y(b)]]))
        keys.append((pu, do))
    if lines:
        arr = np.array(lines, dtype=object)
        total = shapely.length(arr)
        tree = STRtree(nta.geoms)
        li, gi = tree.query(arr, predicate="intersects")
        seg_len = shapely.length(shapely.intersection(arr[li], nta.geoms[gi]))
        acc: dict[int, list[tuple[int, float]]] = {}
        for i, g, L in zip(li.tolist(), gi.tolist(), seg_len.tolist()):
            if L > 0:
                acc.setdefault(i, []).append((g, L))
        for i, lst in acc.items():
            tot = sum(L for _, L in lst)
            if tot <= 0:
                continue
            out[keys[i]] = [(g, L / tot) for g, L in lst]
        for i, k in enumerate(keys):
            if k not in out:
                w = zone_area_weights.get(k[0]) or zone_area_weights.get(k[1])
                if w:
                    out[k] = w
        del acc
    log.info("TLC corridors: %d zone pairs, %d resolved to NTA shares (mean %.1f NTAs per corridor)",
             len(pairs), len(out), float(np.mean([len(v) for v in out.values()])) if out else 0.0)
    return out


def zone_to_nta(vkm: pl.DataFrame, weights: dict[tuple[int, int], list[tuple[int, float]]], n_nta: int,
                nta_traffic: np.ndarray, *, services: tuple[str, ...] = ("yellow", "green", "fhvhv"),
                chunk: int = 400_000) -> dict[str, np.ndarray]:
    """Spread pair-level vehicle-km over the NTAs each corridor crosses → ``{service: (n_nta, 24, 3)}`` km/day.

    Within a corridor the kilometres are split not by bare length but by *length x that NTA's own
    traffic*: a for-hire trip drives where the traffic drives, so the straight line crossing a
    cemetery or a park hands its kilometres to the neighbouring streets instead of to the cemetery.
    The consequence is that every NTA on a corridor sees the same for-hire *fraction* of its traffic
    from that corridor, which is the behaviour the share is supposed to have.
    """
    if nta_traffic.shape != (n_nta,):
        raise ValueError(f"nta_traffic shape {nta_traffic.shape} != {(n_nta,)}")
    t = np.maximum(np.asarray(nta_traffic, dtype=np.float64), 1e-6)
    pairs = sorted(weights)
    pair_index = {p: i for i, p in enumerate(pairs)}
    counts = np.zeros(len(pairs), dtype=np.int64)
    flat_nta: list[int] = []
    flat_w: list[float] = []
    for i, p in enumerate(pairs):
        lst = weights[p]
        ws = np.array([f for _, f in lst]) * t[[g for g, _ in lst]]
        tot = ws.sum()
        if tot <= 0:
            ws = np.array([f for _, f in lst])
            tot = ws.sum()
        counts[i] = len(lst)
        flat_nta.extend(g for g, _ in lst)
        flat_w.extend((ws / tot).tolist())
    offsets = np.concatenate([[0], np.cumsum(counts)])
    fn = np.asarray(flat_nta, dtype=np.int64)
    fw = np.asarray(flat_w, dtype=np.float64)

    out = {s: np.zeros((n_nta, 24, 3)) for s in services}
    lost = 0.0
    lut = pl.DataFrame({"pu": [p[0] for p in pairs], "do": [p[1] for p in pairs],
                        "pair": np.arange(len(pairs), dtype=np.int64)},
                       schema_overrides={"pu": vkm.schema["pu"], "do": vkm.schema["do"]})
    for svc in services:
        sub = vkm.filter(pl.col("service") == svc).join(lut, on=["pu", "do"], how="left")
        miss = sub.filter(pl.col("pair").is_null())
        if miss.height:
            lost += float(miss["vkm_per_day"].sum())
        sub = sub.filter(pl.col("pair").is_not_null())
        pi = sub["pair"].to_numpy()
        hh = sub["hour"].to_numpy().astype(np.int64)
        dd = sub["dow"].to_numpy().astype(np.int64)
        vv = sub["vkm_per_day"].to_numpy()
        arr = out[svc]
        for start in range(0, len(pi), chunk):
            sl = slice(start, start + chunk)
            c = counts[pi[sl]]
            rep = np.repeat(np.arange(len(c)), c)
            pos = np.arange(c.sum()) - np.repeat(np.concatenate([[0], np.cumsum(c)[:-1]]), c)
            k = offsets[pi[sl]][rep] + pos
            np.add.at(arr, (fn[k], hh[sl][rep], dd[sl][rep]), vv[sl][rep] * fw[k])
    total = sum(float(a.sum()) for a in out.values())
    log.info("TLC → NTA: %.0f veh-km/day placed, %.0f (%.1f %%) on corridors with no NTA overlap "
             "(EWR, Governors Island)", total, lost, 100 * lost / max(total + lost, 1.0))
    return out


def pair_list(vkm: pl.DataFrame) -> list[tuple[int, int]]:
    u = vkm.select(["pu", "do"]).unique()
    return [(int(a), int(b)) for a, b in zip(u["pu"].to_list(), u["do"].to_list())]


def trips_by_zone_hour(vkm: pl.DataFrame) -> pl.DataFrame:
    """Pick-ups per zone, hour and day type (the pedestrian model's activity shape)."""
    return (vkm.group_by(["pu", "hour", "dow"]).agg(pl.col("trips_per_day").sum())
            .rename({"pu": "location_id"}))


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
