"""MTA subway entrances/exits (data.ny.gov ``i9wp-a4ja``) -> normalised table shared by the furniture and transit stages."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..crs import lonlat_to_tm
from ..paths import RAW

log = logging.getLogger("nycsim.transit.entrances")

CSV = RAW / "nyc_opendata" / "subway_entrances.csv"
SOURCE_ID = "subway_entrances"

# DATA_CONTRACTS §9: kind(stair, escalator, elevator). The raw "Entrance Type" is kept in ``entrance_type``.
KIND_MAP = {
    "Stair": "stair", "Stair/Ramp": "stair", "Ramp": "stair", "Walkway": "stair", "Underpass": "stair", "Overpass": "stair",
    "Stair/Ramp/Walkway": "stair", "Escalator": "escalator", "Stair/Escalator": "escalator", "Elevator": "elevator",
    "Easement - Street": "stair", "Easement - Passage": "stair", "Station House": "stair",
}
# Entrance types that are outdoor stair-type openings and therefore carry globe lamps.
GLOBE_TYPES = {"Stair", "Stair/Ramp", "Ramp", "Stair/Ramp/Walkway", "Stair/Escalator", "Escalator", "Walkway"}
KIND_ENUM = {"stair": 0, "escalator": 1, "elevator": 2}


def load_subway_entrances(path: Path = CSV) -> pd.DataFrame:
    """Return one row per entrance with NYC_TM coordinates, lines list, kind, entrance_type, has_globe.

    ``has_globe``: 1 green (entry allowed = full-time entrance), 2 red (exit-only / no entry), 0 none (elevators,
    station houses, easements inside buildings). The dataset publishes no opening hours, so "Entry Allowed" is the
    proxy for the 24-h (green) vs restricted (red) globe rule; part-time entrances with entry allowed are therefore
    shown green — stated in the report.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline download --id {SOURCE_ID}")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    lat = pd.to_numeric(df["Entrance Latitude"], errors="coerce")
    lon = pd.to_numeric(df["Entrance Longitude"], errors="coerce")
    ok = lat.notna() & lon.notna()
    if (~ok).any():
        log.warning("%d entrances without coordinates dropped", int((~ok).sum()))
    df = df[ok].copy()
    x, y = lonlat_to_tm(lon[ok].to_numpy(), lat[ok].to_numpy())
    df["x"] = x
    df["y"] = y
    df["lines"] = df["Daytime Routes"].str.split().apply(lambda v: [s for s in v if s])
    df["entrance_type"] = df["Entrance Type"].str.strip()
    df["kind"] = df["entrance_type"].map(KIND_MAP).fillna("stair")
    entry = df["Entry Allowed"].str.upper().eq("YES")
    exit_ = df["Exit Allowed"].str.upper().eq("YES")
    globe_type = df["entrance_type"].isin(GLOBE_TYPES)
    df["has_globe"] = np.where(~globe_type, 0, np.where(entry, 1, np.where(exit_, 2, 0))).astype(np.int8)
    df["entry_allowed"] = entry
    df["exit_allowed"] = exit_
    df["station_id"] = pd.to_numeric(df["Station ID"], errors="coerce").fillna(0).astype(np.int64)
    df["complex_id"] = pd.to_numeric(df["Complex ID"], errors="coerce").fillna(0).astype(np.int64)
    df["gtfs_stop_id"] = df["GTFS Stop ID"]
    df["stop_name"] = df["Stop Name"]
    df["division"] = df["Division"]
    df["line"] = df["Line"]
    df["borough"] = df["Borough"].map({"M": 1, "Bx": 2, "Bk": 3, "Q": 4, "SI": 5}).fillna(0).astype(np.int8)
    # deterministic entrance id: station id * 1000 + rank within station (sorted by x, y)
    df = df.sort_values(["station_id", "x", "y"]).reset_index(drop=True)
    rank = df.groupby("station_id").cumcount()
    df["entrance_id"] = (df["station_id"] * 1000 + rank).astype(np.int64)
    return df[["entrance_id", "station_id", "complex_id", "gtfs_stop_id", "stop_name", "division", "line", "borough", "x", "y",
               "lines", "kind", "entrance_type", "has_globe", "entry_allowed", "exit_allowed"]]
