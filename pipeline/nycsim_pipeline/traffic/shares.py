"""Modal shares of the road-user stream: taxi / for-hire, truck, bus and bicycle.

Definitions (DATA_CONTRACTS §10, made precise here and in METHOD.md §8):

* ``veh_per_km_lane`` counts **motor vehicles** on travel lanes — what DOT's automated counters
  measure.
* the four shares are fractions of the **road-user stream on those lanes**, i.e. motor vehicles plus
  bicycles.  The four categories are disjoint, so their sum is at most 1; the remainder is private
  cars, SUVs, motorcycles and emergency vehicles.

Sources
-------
``taxi_share``   TLC trip records (:mod:`tlc`).  Revenue vehicle-km per NTA, hour and day type are
                 divided by the published occupancy ratio to recover total (including deadhead and
                 cruising) for-hire vehicle-km, then divided by the vehicle-km the volume model puts
                 on that NTA's lanes in that hour.  "Taxi" here means *all* street-hail and app-hail
                 for-hire traffic — yellow medallion, green SHL and high-volume FHV — because that is
                 the whole population that behaves like a taxi in the simulation;
                 ``fleet_mix.json`` splits it into ``taxi`` / ``boro_taxi`` / ``black_car``.
``truck_share``  DOT Vehicle Classification Counts (``96ay-ea4r``): hourly volumes by class on 1,453
                 segments.  Classes ``Commercial (Vehicle)``, ``Medium Truck``, ``Heavy Truck`` and
                 ``Trucks`` are commercial vehicles (the simulation's ``van``, ``box_truck`` and
                 ``dsny_truck`` bodies).
``bus_share``    the same dataset, classes ``School Bus`` and ``Other Bus``.
``bike_share``   the classification counts contain no bicycle class, so bicycles come from the DOT
                 Bicycle and Pedestrian Counts (``ct66-47at``), 29 permanent counters with hourly
                 volumes since 2024, extrapolated over the network by a regression on bike-lane class
                 and local land use and divided by the modelled motor-vehicle flow.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl
from ..crs import lonlat_to_tm
from ..paths import RAW
from . import speed as speedmod
from .geo import NtaTable
from .model import Regression, VolumeResult, fit_regression
from .segments import SegmentTable

log = logging.getLogger("nycsim.traffic.shares")

CLASS_COUNTS_PATH = RAW / "nyc_opendata" / "dot_vehicle_class_counts.csv"
BIKE_HOURLY_PATH = RAW / "traffic" / "dot_bike_ped_hourly.csv"
BIKE_SENSORS_PATH = RAW / "nyc_opendata" / "dot_bike_ped_sensors.csv"

# Share of for-hire vehicle-km that carries a passenger.  Yellow/green: TLC Factbook and Schaller
# Consulting "The New Automobility" (2018) put medallion taxi occupied mileage at 58-62 % of total.
# High-volume FHV: the TLC's 2019 FHV congestion rulemaking measured 41 % of Manhattan CBD FHV
# mileage without a passenger; citywide utilisation is a little better.
OCCUPANCY = {"yellow": 0.60, "green": 0.60, "fhvhv": 0.62}

CLASS_GROUPS = {
    "auto": ("auto", "autos"),
    "taxi": ("taxi", "taxis"),
    "truck": ("commercial", "commercial vehicle", "medium truck", "heavy truck", "trucks"),
    "bus": ("school bus", "other bus"),
}
_HOUR_COL = re.compile(r"^\s*(\d{1,2}):00\s*-\s*(\d{1,2}):00\s*([AP]M)\s*$", re.I)
MIN_CLASS_SITES = 3
SHRINK_CLASS_SITES = 3.0
BIKE_RIDGE = 2.0
MAX_SUM_SHARE = 0.97          # leave at least 3 % of the stream for private cars everywhere
# NYC DOT "Cycling in the City" (2023): about 610,000 cycling trips a day citywide.
CYCLING_TRIPS_PER_DAY = 610_000.0
MEAN_BIKE_TRIP_KM = 3.0


# ----------------------------------------------------------------------------- classification counts
def _hour_of_column(col: str) -> int | None:
    m = _HOUR_COL.match(col.replace("12:00-1:00 AM", "12:00-1:00AM"))
    if not m:
        return None
    h = int(m.group(1)) % 12
    if m.group(3).upper() == "PM":
        h += 12
    return h


def load_class_counts(seg: SegmentTable, nta: NtaTable, atr_sites: pl.DataFrame | None = None,
                      path: Path = CLASS_COUNTS_PATH) -> pl.DataFrame:
    """Long table: seg_row, nta_idx, road_class, hour, dow, group, veh (recency-weighted mean per hour)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.traffic.fetch`")
    df = pl.read_csv(path, infer_schema_length=0)
    hour_cols = {c: _hour_of_column(c) for c in df.columns}
    hour_cols = {c: h for c, h in hour_cols.items() if h is not None}
    if len(hour_cols) != 24:
        raise ValueError(f"{path}: found {len(hour_cols)} hourly columns, expected 24")
    grp_of: dict[str, str] = {}
    for g, names in CLASS_GROUPS.items():
        for nm in names:
            grp_of[nm] = g
    d = df.with_columns(
        pl.col("SegmentID").cast(pl.Int64, strict=False).alias("segment_id"),
        pl.col("Date").str.strptime(pl.Date, "%m/%d/%Y", strict=False).alias("date"),
        pl.col("Veh Class Type").str.to_lowercase().str.replace_all(r"\s+", " ").str.strip_chars().alias("cls"),
    ).with_columns(pl.col("cls").replace_strict(grp_of, default=None).alias("group"))
    unknown = sorted(set(d.filter(pl.col("group").is_null())["cls"].unique().to_list()))
    if unknown:
        log.warning("classification counts: ignoring unmapped classes %s", unknown)
    d = d.filter(pl.col("group").is_not_null() & pl.col("segment_id").is_not_null() & pl.col("date").is_not_null())
    long = d.unpivot(index=["segment_id", "date", "group"], on=list(hour_cols), variable_name="hcol",
                     value_name="vol")
    long = (long.with_columns(pl.col("hcol").replace_strict(hour_cols, return_dtype=pl.Int32).alias("hour"),
                              pl.col("vol").cast(pl.Float64, strict=False))
            .filter(pl.col("vol").is_not_null() & (pl.col("vol") >= 0))
            .with_columns(pl.when(pl.col("date").dt.weekday() <= 5).then(0)
                          .when(pl.col("date").dt.weekday() == 6).then(1).otherwise(2).cast(pl.Int8).alias("dow"),
                          pl.col("date").dt.year().alias("year")))
    long = long.with_columns(
        pl.when(pl.col("year") >= 2023).then(1.0).when(pl.col("year") >= 2019).then(0.6)
        .when(pl.col("year") >= 2015).then(0.4).otherwise(0.25).alias("w"))
    agg = (long.group_by(["segment_id", "hour", "dow", "group"])
           .agg(((pl.col("vol") * pl.col("w")).sum() / pl.col("w").sum()).alias("veh"),
                pl.col("date").n_unique().alias("n_days"), pl.col("year").max().alias("latest_year")))

    # segment_id -> CSCL row: physicalid first, then the ATR site table (same DOT SegmentID space)
    rows: dict[int, int] = {}
    for sid in agg["segment_id"].unique().to_list():
        r = seg.phys_index.get(int(sid))
        if r is not None:
            rows[int(sid)] = r
    if atr_sites is not None and atr_sites.height:
        for sid, r in zip(atr_sites["segment_id"].to_list(), atr_sites["seg_row"].to_list()):
            rows.setdefault(int(sid), int(r))
    agg = agg.with_columns(pl.col("segment_id").replace_strict(rows, default=-1, return_dtype=pl.Int64).alias("seg_row"))
    n_seg_all = agg["segment_id"].n_unique()
    agg = agg.filter(pl.col("seg_row") >= 0)
    sd = seg.df
    r = agg["seg_row"].to_numpy()
    cls = speedmod.road_class(sd["rw_type"].to_numpy(), sd["travel_lanes"].to_numpy(),
                              np.asarray(sd["trafdir"].to_list()), sd["is_truck_route"].to_numpy())
    agg = agg.with_columns(pl.Series("nta_idx", sd["nta_idx"].to_numpy()[r]), pl.Series("road_class", cls[r]))
    agg = agg.filter(pl.col("nta_idx") >= 0)
    log.info("classification counts: %d segments in the file, %d matched to CSCL, %d segment-hour-class rows",
             n_seg_all, agg["segment_id"].n_unique(), agg.height)
    return agg


@dataclass
class ClassShares:
    by_class_hour: np.ndarray       # (5 road classes, 24, 3, 2) truck/bus share
    cluster_mult: dict[str, np.ndarray]   # cluster -> (2,) multiplier on truck/bus
    nta_mult: np.ndarray            # (n_nta, 2)
    n_sites: int
    n_nta_with_sites: int
    citywide: np.ndarray            # (24, 3, 2)


def class_shares(counts: pl.DataFrame, nta: NtaTable, clusters: np.ndarray) -> ClassShares:
    """Truck and bus share of motor vehicles by road class × hour × day type, with area multipliers."""
    wide = counts.pivot(on="group", index=["segment_id", "seg_row", "nta_idx", "road_class", "hour", "dow"],
                        values="veh", aggregate_function="sum").fill_null(0.0)
    for g in CLASS_GROUPS:
        if g not in wide.columns:
            wide = wide.with_columns(pl.lit(0.0).alias(g))
    wide = wide.with_columns((pl.col("auto") + pl.col("taxi") + pl.col("truck") + pl.col("bus")).alias("total"))
    wide = wide.filter(pl.col("total") > 0)
    if wide.height == 0:
        raise ValueError("classification counts produced no usable segment-hours")

    n_cls = len(speedmod.CLASS_NAMES)
    num = np.zeros((n_cls, 24, 3, 2))
    den = np.zeros((n_cls, 24, 3))
    rc = wide["road_class"].to_numpy().astype(int)
    hh = wide["hour"].to_numpy().astype(int)
    dd = wide["dow"].to_numpy().astype(int)
    tot = wide["total"].to_numpy()
    tr = wide["truck"].to_numpy()
    bu = wide["bus"].to_numpy()
    np.add.at(num, (rc, hh, dd, 0), tr)
    np.add.at(num, (rc, hh, dd, 1), bu)
    np.add.at(den, (rc, hh, dd), tot)
    city_num = num.sum(axis=0)
    city_den = den.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        citywide = np.where(city_den[..., None] > 0, city_num / city_den[..., None], np.nan)
    citywide = _fill_hours(citywide)
    table = np.empty((n_cls, 24, 3, 2))
    for c in range(n_cls):
        with np.errstate(invalid="ignore", divide="ignore"):
            t = np.where(den[c][..., None] > 20, num[c] / np.maximum(den[c][..., None], 1e-9), np.nan)
        table[c] = _fill_hours(t, fallback=citywide)
    n_by_dow = den.sum(axis=(0, 1))
    log.info("classification counts by day type (vehicles): weekday %.0f, Saturday %.0f, Sunday %.0f "
             "— day types without their own counts inherit the weekday shares", *n_by_dow)

    # area multipliers: observed / predicted-by-class, aggregated over the sites of a cluster or NTA
    pred = table[rc, hh, dd]
    obs = np.column_stack([tr, bu])
    exp_veh = pred * tot[:, None]
    ni = wide["nta_idx"].to_numpy().astype(int)
    cl = clusters[ni]
    cluster_mult: dict[str, np.ndarray] = {}
    for c in np.unique(cl):
        m = cl == c
        e = exp_veh[m].sum(axis=0)
        o = obs[m].sum(axis=0)
        cluster_mult[str(c)] = np.where(e > 0, np.clip(o / np.maximum(e, 1e-9), 0.3, 3.0), 1.0)
    n = len(nta)
    nta_mult = np.ones((n, 2))
    n_with = 0
    for i in np.unique(ni):
        m = ni == i
        if wide.filter(pl.Series(m))["segment_id"].n_unique() < MIN_CLASS_SITES:
            continue
        e = exp_veh[m].sum(axis=0)
        o = obs[m].sum(axis=0)
        k = m.sum() / (m.sum() + SHRINK_CLASS_SITES * 24)
        own = np.where(e > 0, np.clip(o / np.maximum(e, 1e-9), 0.3, 3.0), 1.0)
        nta_mult[i] = k * own + (1 - k) * cluster_mult.get(str(clusters[i]), np.ones(2))
        n_with += 1
    for i in range(n):
        if nta_mult[i, 0] == 1.0 and nta_mult[i, 1] == 1.0:
            nta_mult[i] = cluster_mult.get(str(clusters[i]), np.ones(2))
    log.info("class shares: %d segments, %d NTAs with >= %d own sites; citywide weekday truck share "
             "%.3f (peak %.3f at %02d:00), bus share %.3f; cluster multipliers %s",
             wide["segment_id"].n_unique(), n_with, MIN_CLASS_SITES, float(citywide[:, 0, 0].mean()),
             float(citywide[:, 0, 0].max()), int(np.argmax(citywide[:, 0, 0])), float(citywide[:, 0, 1].mean()),
             {k: np.round(v, 2).tolist() for k, v in cluster_mult.items()})
    return ClassShares(table, cluster_mult, nta_mult, int(wide["segment_id"].n_unique()), n_with, citywide)


def _fill_hours(a: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    """Fill missing (hour, day type) cells of a (24, 3, k) share table.

    Order of preference: the supplied ``fallback`` table (the citywide table when filling a single
    road class), then the same hour on a weekday, then the day type's own mean over the hours it
    does have, then the mean of everything present.  DOT's classification counts are taken almost
    exclusively on weekdays, so the weekday fallback is what fills Saturday and Sunday.
    """
    out = np.array(a, dtype=np.float64, copy=True)
    if fallback is not None:
        m = ~np.isfinite(out)
        out[m] = np.asarray(fallback, dtype=np.float64)[m]
    m = ~np.isfinite(out)
    if m.any():
        wd = np.broadcast_to(out[:, 0:1, :], out.shape)
        out[m] = wd[m]
    m = ~np.isfinite(out)
    if m.any():
        for d in range(out.shape[1]):
            col = out[:, d, :]
            for j in range(col.shape[1]):
                bad = ~np.isfinite(col[:, j])
                if bad.any() and np.isfinite(col[:, j]).any():
                    col[bad, j] = float(np.nanmean(col[:, j]))
            out[:, d, :] = col
    m = ~np.isfinite(out)
    if m.any():
        out[m] = float(np.nanmean(out)) if np.isfinite(out).any() else 0.0
    return out


# ----------------------------------------------------------------------------- bicycles
@dataclass
class BikeModel:
    regression: Regression
    flow: np.ndarray            # (n_seg,) bikes/h, mean over the counter-observed hours
    profile: np.ndarray         # (24, 3) normalised diurnal shape
    n_sensors: int
    trips_per_day_implied: float
    level_scale: float


def load_bike_counters(seg: SegmentTable, hourly: Path = BIKE_HOURLY_PATH,
                       sensors: Path = BIKE_SENSORS_PATH) -> tuple[pl.DataFrame, np.ndarray]:
    """Permanent DOT bicycle counters: per-sensor mean bikes/h and the citywide 24×3 shape."""
    for p in (hourly, sensors):
        if not p.exists():
            raise FileNotFoundError(f"{p} missing — run `python -m nycsim_pipeline.traffic.fetch`")
    h = pl.read_csv(hourly, infer_schema_length=0).filter(pl.col("travelmode") == "bike")
    if h.height == 0:
        raise ValueError(f"{hourly}: no bicycle rows")
    h = h.with_columns(pl.col("counts").cast(pl.Float64), pl.col("n").cast(pl.Float64),
                       pl.col("hh").cast(pl.Int32), pl.col("dow").cast(pl.Int32))
    h = h.filter((pl.col("n") > 0)).with_columns(
        (4.0 * pl.col("counts") / pl.col("n")).alias("bph"),
        pl.when(pl.col("dow") == 0).then(2).when(pl.col("dow") == 6).then(1).otherwise(0).cast(pl.Int8).alias("dt"))
    prof = np.zeros((24, 3))
    wsum = np.zeros((24, 3))
    for r in h.iter_rows(named=True):
        prof[int(r["hh"]), int(r["dt"])] += float(r["bph"]) * float(r["n"])
        wsum[int(r["hh"]), int(r["dt"])] += float(r["n"])
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = np.where(wsum > 0, prof / wsum, 0.0)
    m = prof[:, 0].mean()
    prof = prof / m if m > 0 else prof

    s = pl.read_csv(sensors, infer_schema_length=0).unique(subset=["id"])
    s = s.with_columns(pl.col("lat").cast(pl.Float64, strict=False), pl.col("lon").cast(pl.Float64, strict=False))
    lvl = (h.group_by("sensor_id")
           .agg(((pl.col("bph") * pl.col("n")).sum() / pl.col("n").sum()).alias("bph"))
           .join(s.select(["id", "lat", "lon"]).rename({"id": "sensor_id"}), on="sensor_id", how="inner")
           .filter(pl.col("lat").is_not_null() & pl.col("lon").is_not_null() & (pl.col("bph") > 0)))
    x, y = lonlat_to_tm(lvl["lon"].to_numpy(), lvl["lat"].to_numpy())
    rows, dist = seg.nearest(x, y, max_dist=120.0)
    lvl = lvl.with_columns(pl.Series("x", x), pl.Series("y", y), pl.Series("seg_row", rows),
                           pl.Series("dist_m", dist)).filter(pl.col("seg_row") >= 0)
    log.info("bike counters: %d sensors with hourly data, %d placed on a CSCL segment; mean %.1f bikes/h",
             h["sensor_id"].n_unique(), lvl.height, float(lvl["bph"].mean()))
    return lvl, prof


def fit_bike_model(lvl: pl.DataFrame, prof: np.ndarray, seg: SegmentTable, nta: NtaTable,
                   sample_generators) -> BikeModel:
    """Regress counter volumes on bike-lane class and local land use, then evaluate on every segment."""
    sd = seg.df
    r = lvl["seg_row"].to_numpy()

    def design(rows: np.ndarray, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, list[str]]:
        gen = sample_generators(x, y)
        nidx = sd["nta_idx"].to_numpy()[rows]
        f = {
            "has_protected_bike_lane": sd["has_protected_bike_lane"].to_numpy()[rows].astype(np.float64),
            "has_bike_lane": sd["has_bike_lane"].to_numpy()[rows].astype(np.float64),
            "log_com_800m": np.log1p(gen["com_m2"] / 1e3),
            "log_units_800m": np.log1p(gen["units"]),
            "is_cbd": np.where(nidx >= 0, nta.is_cbd[np.maximum(nidx, 0)], False).astype(np.float64),
            "is_manhattan": np.where(nidx >= 0, nta.borocode[np.maximum(nidx, 0)] == 1, False).astype(np.float64),
        }
        names = list(f)
        return np.column_stack([f[k] for k in names]), names

    X, names = design(r, lvl["x"].to_numpy(), lvl["y"].to_numpy())
    y = np.log(lvl["bph"].to_numpy())
    reg = fit_regression(X, y, np.ones(len(y)), names, ridge=BIKE_RIDGE)
    Xs, _ = design(np.arange(sd.height), sd["x_mid"].to_numpy(), sd["y_mid"].to_numpy())
    flow = np.exp(reg.predict(Xs))
    lo, hi = np.percentile(lvl["bph"].to_numpy(), [2, 98])
    flow = np.clip(flow, 0.05, hi * 1.5)
    # The 29 counters all sit on cycle routes, so the fitted level over-states the ordinary street.
    # The spatial pattern is kept and the absolute level is anchored on the published citywide
    # cycling volume: NYC DOT "Cycling in the City" ~610,000 daily trips at a 3.0 km mean length.
    km_raw = float((flow * sd["length_m"].to_numpy() / 1000.0 * 24.0).sum())
    target_km = CYCLING_TRIPS_PER_DAY * MEAN_BIKE_TRIP_KM
    scale = target_km / km_raw if km_raw > 0 else 1.0
    flow = flow * scale
    log.info("bike model: R²=%.3f LOO=%.3f on %d counters; raw model implies %.0f k bike-km/day, scaled by "
             "%.3f onto the published %.0f k trips/day x %.1f km = %.0f k bike-km/day",
             reg.r2, reg.r2_loo, reg.n, km_raw / 1e3, scale, CYCLING_TRIPS_PER_DAY / 1e3,
             MEAN_BIKE_TRIP_KM, target_km / 1e3)
    return BikeModel(reg, flow, prof, reg.n, float(CYCLING_TRIPS_PER_DAY), float(scale))


# ----------------------------------------------------------------------------- assembly
@dataclass
class ShareResult:
    taxi: np.ndarray
    truck: np.ndarray
    bus: np.ndarray
    bike: np.ndarray
    taxi_vkm: np.ndarray
    bike_flow_nta: np.ndarray
    class_shares: ClassShares
    bike_model: BikeModel
    stats: dict = field(default_factory=dict)


def build_shares(nta: NtaTable, seg: SegmentTable, vol: VolumeResult, tlc_vkm_by_service: dict[str, np.ndarray],
                 cs: ClassShares, bike: BikeModel) -> ShareResult:
    """Combine the three sources into the four contract shares, clipped and normalised."""
    n = len(nta)
    df = seg.df
    nidx = df["nta_idx"].to_numpy().astype(int)
    ok = nidx >= 0
    lane_km = df["lane_km"].to_numpy()
    length_km = df["length_m"].to_numpy() / 1000.0

    # --- taxi: total (revenue / occupancy) for-hire veh-km ÷ modelled veh-km in the same hour
    taxi_vkm = np.zeros((n, 24, 3))
    for svc, arr in tlc_vkm_by_service.items():
        taxi_vkm += arr / OCCUPANCY[svc]
    with np.errstate(invalid="ignore", divide="ignore"):
        taxi = np.where(vol.veh_km_h > 0, taxi_vkm / np.maximum(vol.veh_km_h, 1e-9), 0.0)
    taxi = np.clip(np.nan_to_num(taxi), 0.0, 0.75)

    # --- truck / bus: class-share table by road class, weighted by each segment's vehicle-km
    truck_num = np.zeros((n, 24, 3))
    bus_num = np.zeros((n, 24, 3))
    den = np.zeros((n, 24, 3))
    cls = vol.road_class
    prof_share = cs.by_class_hour                       # (5, 24, 3, 2)
    level = vol.segment_level
    # a segment's veh-km per hour is proportional to level × lane_km × profile; the profile cancels in
    # the ratio only if it is the same for all segments of an NTA, so weight by lane-km × level.
    w_seg = level * lane_km
    for c in range(prof_share.shape[0]):
        m = ok & (cls == c)
        if not m.any():
            continue
        idx = nidx[m]
        w = w_seg[m][:, None, None]
        np.add.at(truck_num, idx, w * prof_share[c, :, :, 0][None, :, :])
        np.add.at(bus_num, idx, w * prof_share[c, :, :, 1][None, :, :])
        np.add.at(den, idx, np.broadcast_to(w, (m.sum(), 24, 3)))
    with np.errstate(invalid="ignore", divide="ignore"):
        truck = np.where(den > 0, truck_num / np.maximum(den, 1e-9), 0.0) * cs.nta_mult[:, 0][:, None, None]
        bus = np.where(den > 0, bus_num / np.maximum(den, 1e-9), 0.0) * cs.nta_mult[:, 1][:, None, None]
    truck = np.clip(np.nan_to_num(truck), 0.0, 0.6)
    bus = np.clip(np.nan_to_num(bus), 0.0, 0.35)

    # --- bicycles: modelled bikes/h × street length, against the motor-vehicle flow
    bike_veh_h = np.zeros((n, 24, 3))
    np.add.at(bike_veh_h, nidx[ok], (bike.flow[ok] * length_km[ok])[:, None, None] * bike.profile[None, :, :])
    with np.errstate(invalid="ignore", divide="ignore"):
        bike_share = np.where(vol.veh_km_h + bike_veh_h > 0,
                              bike_veh_h / np.maximum(vol.veh_km_h + bike_veh_h, 1e-9), 0.0)
    bike_share = np.clip(np.nan_to_num(bike_share), 0.0, 0.5)

    # the motor-vehicle shares are fractions of motor vehicles; rescale onto the full stream
    motor = 1.0 - bike_share
    taxi, truck, bus = taxi * motor, truck * motor, bus * motor
    total = taxi + truck + bus + bike_share
    over = total > MAX_SUM_SHARE
    if over.any():
        scale = np.where(over, MAX_SUM_SHARE / np.maximum(total, 1e-9), 1.0)
        taxi, truck, bus, bike_share = taxi * scale, truck * scale, bus * scale, bike_share * scale
    stats = {
        "cells_rescaled": int(over.sum()),
        "taxi_p50": float(np.percentile(taxi, 50)), "taxi_max": float(taxi.max()),
        "truck_p50": float(np.percentile(truck, 50)), "truck_max": float(truck.max()),
        "bus_p50": float(np.percentile(bus, 50)), "bus_max": float(bus.max()),
        "bike_p50": float(np.percentile(bike_share, 50)), "bike_max": float(bike_share.max()),
        "max_sum": float((taxi + truck + bus + bike_share).max()),
    }
    log.info("shares: %s", {k: round(v, 4) if isinstance(v, float) else v for k, v in stats.items()})
    return ShareResult(taxi, truck, bus, bike_share, taxi_vkm, bike_veh_h, cs, bike, stats)
