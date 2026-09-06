"""GTFS reader for the MTA / NYC DOT feeds in ``data/raw/gtfs`` (DATA_CONTRACTS §9).

Only the tables the world needs are read: ``agency``, ``routes``, ``trips``, ``stops``, ``shapes``, ``calendar``,
``calendar_dates`` and — the expensive one — ``stop_times``. ``stop_times.txt`` is up to 155 MB per feed, so it is
extracted to a scratch file and scanned lazily by polars with only the four columns that matter; nothing larger
than one feed's stop table is ever materialised.

**Service day.** Headways are the *weekday* headways the contract asks for. A representative weekday is chosen by
:func:`pick_service_date` (the next Wednesday for which the feed actually has active services, searched forward
from a start date), and the active ``service_id`` set for that date is resolved the GTFS way: ``calendar.txt``
day-of-week flags inside ``start_date``/``end_date``, minus ``calendar_dates`` removals (exception 2), plus
additions (exception 1). Feeds without ``calendar.txt`` (LIRR, Metro-North) are resolved from ``calendar_dates``
alone.

**Headway definition.** For route *r* and hour *h*, ``headway_min[h] = round(60 * D / T)`` where *T* is the number
of trips of *r* whose **first departure** falls in hour *h* on the service day and *D* is the number of distinct
``direction_id`` values among them (1 or 2). That is the mean time between consecutive departures in one
direction. ``0`` means no scheduled trip starts in that hour. Trips departing after midnight of the service day
(GTFS times ``24:00:00``+) are folded onto the hour they fall in, modulo 24.
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from ..paths import RAW

log = logging.getLogger("nycsim.transit.gtfs")

GTFS_DIR = RAW / "gtfs"

# feed id -> (zip name, agency label, borough code 1..5 or 0, mode)
BUS_FEEDS: dict[str, tuple[str, str, int]] = {
    "gtfs_bus_manhattan": ("gtfs_bus_manhattan.zip", "MTA New York City Transit", 1),
    "gtfs_bus_bronx": ("gtfs_bus_bronx.zip", "MTA New York City Transit", 2),
    "gtfs_bus_brooklyn": ("gtfs_bus_brooklyn.zip", "MTA New York City Transit", 3),
    "gtfs_bus_queens": ("gtfs_bus_queens.zip", "MTA New York City Transit", 4),
    "gtfs_bus_staten_island": ("gtfs_bus_staten_island.zip", "MTA New York City Transit", 5),
    "gtfs_bus_company": ("gtfs_bus_company.zip", "MTA Bus Company", 0),
}
SUBWAY_FEED = ("gtfs_subway", "gtfs_subway.zip", "MTA New York City Transit")
RAIL_FEEDS: dict[str, tuple[str, str]] = {
    "gtfs_lirr": ("gtfs_lirr.zip", "Long Island Rail Road"),
    "gtfs_mnr": ("gtfs_mnr.zip", "Metro-North Railroad"),
}

ROUTE_TYPE_TRAM = 0
ROUTE_TYPE_SUBWAY = 1
ROUTE_TYPE_RAIL = 2
ROUTE_TYPE_BUS = 3
ROUTE_TYPE_FERRY = 4

DEFAULT_SERVICE_START = date(2026, 9, 9)   # the Wednesday after the feeds were downloaded (2026-09-05)


class GtfsError(RuntimeError):
    pass


@dataclass
class Feed:
    """One GTFS zip. Tables are read on demand and cached."""

    feed_id: str
    path: Path
    agency: str = ""
    borough: int = 0

    def __post_init__(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} missing; run: python -m nycsim_pipeline.download --id {self.feed_id}")
        self._cache: dict[str, pl.DataFrame] = {}
        with zipfile.ZipFile(self.path) as z:
            self._members = {n.rsplit("/", 1)[-1] for n in z.namelist()}

    def has(self, table: str) -> bool:
        return f"{table}.txt" in self._members

    def table(self, name: str, columns: list[str] | None = None) -> pl.DataFrame:
        key = f"{name}:{','.join(columns or [])}"
        if key in self._cache:
            return self._cache[key]
        if not self.has(name):
            raise GtfsError(f"{self.path.name}: no {name}.txt")
        with zipfile.ZipFile(self.path) as z:
            raw = z.read(f"{name}.txt")
        df = pl.read_csv(io.BytesIO(raw), infer_schema_length=0, encoding="utf8-lossy")
        df.columns = [c.strip().lstrip("﻿") for c in df.columns]
        if columns:
            have = [c for c in columns if c in df.columns]
            df = df.select(have)
        self._cache[key] = df
        return df

    def extract(self, name: str, dest_dir: Path) -> Path:
        """Extract one member to ``dest_dir`` (used for ``stop_times.txt``, which is too big to hold twice)."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / f"{self.feed_id}_{name}.txt"
        with zipfile.ZipFile(self.path) as z, open(out, "wb") as f:
            with z.open(f"{name}.txt") as src:
                while True:
                    b = src.read(1 << 22)
                    if not b:
                        break
                    f.write(b)
        return out

    def license_note(self) -> dict:
        ag = self.table("agency") if self.has("agency") else pl.DataFrame()
        name = str(ag["agency_name"][0]).strip() if ag.height and "agency_name" in ag.columns else self.agency
        info = {}
        if self.has("feed_info"):
            fi = self.table("feed_info")
            if fi.height:
                info = {c: str(fi[c][0]) for c in fi.columns}
        return {"feed_id": self.feed_id, "agency": name, "feed_info": info}


# --------------------------------------------------------------------------------- service calendar

def _yyyymmdd(d: date) -> str:
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


def active_services(feed: Feed, day: date) -> set[str]:
    """Service ids running on ``day`` per calendar.txt + calendar_dates.txt."""
    ds = _yyyymmdd(day)
    dow = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][day.weekday()]
    active: set[str] = set()
    if feed.has("calendar"):
        cal = feed.table("calendar")
        for row in cal.iter_rows(named=True):
            if row.get(dow, "0").strip() == "1" and row["start_date"].strip() <= ds <= row["end_date"].strip():
                active.add(row["service_id"].strip())
    if feed.has("calendar_dates"):
        cd = feed.table("calendar_dates")
        for row in cd.iter_rows(named=True):
            if row["date"].strip() != ds:
                continue
            sid = row["service_id"].strip()
            if row["exception_type"].strip() == "1":
                active.add(sid)
            else:
                active.discard(sid)
    return active


def pick_service_date(feed: Feed, start: date = DEFAULT_SERVICE_START, max_days: int = 28) -> tuple[date, set[str]]:
    """First Wednesday on or after ``start`` on which this feed has active services."""
    d = start + timedelta(days=(2 - start.weekday()) % 7)
    for _ in range(max_days // 7 + 1):
        svc = active_services(feed, d)
        if svc:
            return d, svc
        d += timedelta(days=7)
    raise GtfsError(f"{feed.path.name}: no weekday service found in {max_days} days from {start}")


# --------------------------------------------------------------------------------- stop_times

def _seconds(times: pl.Series) -> pl.Series:
    parts = times.str.strip_chars().str.split(":")
    return (parts.list.get(0).cast(pl.Int32, strict=False) * 3600
            + parts.list.get(1).cast(pl.Int32, strict=False) * 60
            + parts.list.get(2).cast(pl.Int32, strict=False))


@dataclass
class StopTimeFacts:
    """What one pass over ``stop_times.txt`` yields: route<->stop pairs and each trip's first departure."""

    route_stops: pl.DataFrame      # route_id, stop_id
    trip_start: pl.DataFrame       # trip_id, start_s


def scan_stop_times(feed: Feed, trips: pl.DataFrame, scratch: Path) -> StopTimeFacts:
    """One lazy pass over ``stop_times.txt`` restricted to ``trips`` (already filtered to the service day)."""
    path = feed.extract("stop_times", scratch)
    try:
        lf = pl.scan_csv(path, infer_schema_length=0, encoding="utf8-lossy").select(
            [pl.col("trip_id").str.strip_chars(), pl.col("stop_id").str.strip_chars(),
             pl.col("stop_sequence").cast(pl.Int32, strict=False), pl.col("departure_time")])
        keep = trips.select(pl.col("trip_id")).unique()
        st = lf.join(keep.lazy(), on="trip_id", how="semi").collect()
        route_stops = (st.select("trip_id", "stop_id")
                       .unique()
                       .join(trips.select("trip_id", "route_id"), on="trip_id", how="inner")
                       .select("route_id", "stop_id").unique())
        first = (st.sort(["trip_id", "stop_sequence"])
                 .group_by("trip_id", maintain_order=True)
                 .first()
                 .select(["trip_id", "departure_time"]))
        first = first.with_columns(_seconds(first["departure_time"]).alias("start_s")).drop("departure_time")
        log.info("%s: %d stop_times rows for %d service-day trips -> %d route/stop pairs",
                 feed.feed_id, st.height, keep.height, route_stops.height)
        return StopTimeFacts(route_stops, first)
    finally:
        path.unlink(missing_ok=True)


# --------------------------------------------------------------------------------- headways

def headways_by_hour(trips: pl.DataFrame, trip_start: pl.DataFrame) -> dict[str, list[int]]:
    """route_id -> 24 headways in minutes (0 = no scheduled departure in that hour). See the module docstring."""
    df = trips.select(["trip_id", "route_id", "direction_id"]).join(trip_start, on="trip_id", how="inner")
    if df.height == 0:
        return {}
    df = df.with_columns(((pl.col("start_s") // 3600) % 24).alias("hour"))
    g = df.group_by(["route_id", "hour"]).agg([pl.len().alias("trips"), pl.col("direction_id").n_unique().alias("dirs")])
    out: dict[str, list[int]] = {}
    for row in g.iter_rows(named=True):
        h = row["hour"]
        if h is None:
            continue
        arr = out.setdefault(row["route_id"], [0] * 24)
        t = int(row["trips"])
        d = max(int(row["dirs"] or 1), 1)
        arr[int(h)] = int(min(32767, round(60.0 * d / t))) if t else 0
    return out


# --------------------------------------------------------------------------------- shapes

def shape_lines(feed: Feed, shape_ids: set[str]) -> dict[str, np.ndarray]:
    """shape_id -> (N,2) lon/lat array, ordered by ``shape_pt_sequence``."""
    if not feed.has("shapes"):
        return {}
    df = feed.table("shapes", ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"])
    df = df.with_columns([
        pl.col("shape_id").str.strip_chars(),
        pl.col("shape_pt_lat").str.strip_chars().cast(pl.Float64, strict=False),
        pl.col("shape_pt_lon").str.strip_chars().cast(pl.Float64, strict=False),
        pl.col("shape_pt_sequence").str.strip_chars().cast(pl.Int64, strict=False),
    ]).filter(pl.col("shape_id").is_in(list(shape_ids)) & pl.col("shape_pt_lat").is_finite()
              & pl.col("shape_pt_lon").is_finite())
    df = df.sort(["shape_id", "shape_pt_sequence"])
    out: dict[str, np.ndarray] = {}
    for sid, part in df.group_by("shape_id", maintain_order=True):
        key = sid[0] if isinstance(sid, tuple) else sid
        out[str(key)] = np.column_stack([part["shape_pt_lon"].to_numpy(), part["shape_pt_lat"].to_numpy()])
    return out


def clean_csv_field(v: str | None) -> str:
    return "" if v is None else str(v).strip().strip('"')


def sniff_columns(path: Path, table: str) -> list[str]:
    """Header of one member without reading the body (used by the tests)."""
    with zipfile.ZipFile(path) as z, z.open(f"{table}.txt") as f:
        line = f.readline().decode("utf-8-sig", "replace")
    return next(csv.reader([line]))
