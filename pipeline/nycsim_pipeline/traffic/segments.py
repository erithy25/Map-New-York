"""CSCL centerline -> per-segment lane-km, road class, posted speed and NTA (ADR-006: CSCL is the road authority)."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import pyogrio
import shapely
from shapely.strtree import STRtree

from ..crs import NYC_TM
from ..paths import RAW
from .geo import NtaTable

log = logging.getLogger("nycsim.traffic.segments")

CENTERLINE_PATH = RAW / "nyc_opendata" / "centerline.geojson"
COLUMNS = ["physicalid", "rw_type", "number_travel_lanes", "number_total_lanes", "number_park_lanes", "posted_speed",
           "trafdir", "streetwidth", "full_street_name", "bike_lane", "truck_route_type", "boroughcode", "status"]

# rw_type codes carrying general vehicle traffic (DATA_CONTRACTS §7)
VEHICULAR_RW_TYPES = {1: "street", 2: "highway", 3: "bridge", 4: "tunnel", 9: "ramp", 10: "alley"}
MPH_TO_KMH = 1.609344

# Defaults used only where CSCL has no value (flagged lanes_source / speed_source = 1)
DEFAULT_SPEED_MPH = {1: 25, 2: 50, 3: 35, 4: 35, 9: 30, 10: 15}
DEFAULT_LANES = {2: 3, 3: 2, 4: 2, 9: 1, 10: 1}

_ABBR = {
    "AVENUE": "AV", "AVE": "AV", "STREET": "ST", "ROAD": "RD", "BOULEVARD": "BLVD", "PARKWAY": "PKWY", "PLACE": "PL",
    "EXPRESSWAY": "EXPWY", "EXPY": "EXPWY", "EXWY": "EXPWY", "DRIVE": "DR", "LANE": "LN", "COURT": "CT", "TERRACE": "TER",
    "HIGHWAY": "HWY", "BRIDGE": "BR", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "SAINT": "ST",
}
_ORD = re.compile(r"^(\d+)(ST|ND|RD|TH)$")


def normalize_street(name: str | None) -> str:
    """Canonical token form for street-name comparison ('EAST 34TH STREET' -> 'E 34 ST')."""
    if not name:
        return ""
    toks = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper()).split()
    out = []
    for t in toks:
        m = _ORD.match(t)
        if m:
            t = m.group(1)
        out.append(_ABBR.get(t, t))
    return " ".join(out)


@dataclass
class SegmentTable:
    df: pl.DataFrame               # one row per vehicular CSCL segment
    geoms: np.ndarray              # shapely LineStrings (NYC_TM), aligned with df rows
    tree: STRtree
    phys_index: dict[int, int]     # physicalid -> row

    def __len__(self) -> int:
        return self.df.height

    def nearest(self, x: np.ndarray, y: np.ndarray, *, max_dist: float = 40.0) -> tuple[np.ndarray, np.ndarray]:
        """Nearest segment row for each point (-1 if none within ``max_dist``) and its distance."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        rows = np.full(len(x), -1, dtype=np.int64)
        dist = np.full(len(x), np.inf)
        if len(x) == 0:
            return rows, dist
        pts = shapely.points(x, y)
        pi, gi = self.tree.query_nearest(pts, max_distance=max_dist, return_distance=False, all_matches=False)
        rows[pi] = gi
        dist[pi] = shapely.distance(pts[pi], self.geoms[gi])
        return rows, dist


def _to_int(s: pl.Expr, default: int | None = None) -> pl.Expr:
    e = s.cast(pl.Utf8).str.strip_chars().cast(pl.Int32, strict=False)
    return e if default is None else e.fill_null(default)


def load_segments(nta: NtaTable, path: Path = CENTERLINE_PATH) -> SegmentTable:
    """Read CSCL, keep vehicular segments, derive lanes/speed/length/NTA. ~122k rows, ~1 minute."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.download --id centerline`")
    log.info("reading %s", path)
    gdf = pyogrio.read_dataframe(path, columns=COLUMNS)
    gdf = gdf.to_crs(NYC_TM)
    geoms = gdf.geometry.values
    # multi-part -> merged lines (CSCL multilinestrings are almost always single-part)
    geoms = np.array([shapely.line_merge(g) if g.geom_type == "MultiLineString" else g for g in geoms], dtype=object)
    df = pl.DataFrame({c: gdf[c].astype(object).where(gdf[c].notna(), None).tolist() for c in COLUMNS})
    df = df.with_columns(
        _to_int(pl.col("physicalid")).alias("physicalid"),
        _to_int(pl.col("rw_type")).alias("rw_type"),
        _to_int(pl.col("number_travel_lanes")).alias("travel_lanes_raw"),
        _to_int(pl.col("number_total_lanes")).alias("total_lanes_raw"),
        _to_int(pl.col("number_park_lanes")).alias("park_lanes_raw"),
        _to_int(pl.col("posted_speed")).alias("speed_raw"),
        pl.col("streetwidth").cast(pl.Utf8).cast(pl.Float64, strict=False).alias("streetwidth_ft"),
        _to_int(pl.col("bike_lane")).alias("bike_lane"),
        _to_int(pl.col("boroughcode")).alias("borough"),
        pl.col("trafdir").cast(pl.Utf8).fill_null("TW").alias("trafdir"),
        pl.col("full_street_name").cast(pl.Utf8).fill_null("").alias("street_name"),
        pl.col("truck_route_type").cast(pl.Utf8).alias("truck_route_type"),
        pl.Series("length_m", shapely.length(geoms)),
        pl.Series("row", np.arange(len(gdf), dtype=np.int64)),
    )
    keep = df.filter(pl.col("rw_type").is_in(list(VEHICULAR_RW_TYPES)) & (pl.col("trafdir") != "NV") & (pl.col("length_m") > 0.5)
                     & pl.col("physicalid").is_not_null())
    geoms = geoms[keep["row"].to_numpy()]
    n_drop = df.height - keep.height
    df = keep.drop("row")

    # lanes: CSCL value when present and > 0; else class default (streets: by width and direction)
    street_default = pl.when((pl.col("trafdir") == "TW") & (pl.col("streetwidth_ft").fill_null(30) >= 30)).then(2).otherwise(1)
    lane_default = pl.col("rw_type").replace_strict(DEFAULT_LANES, default=None, return_dtype=pl.Int32).fill_null(street_default)
    lanes_ok = pl.col("travel_lanes_raw").is_not_null() & (pl.col("travel_lanes_raw") > 0) & (pl.col("travel_lanes_raw") <= 12)
    speed_ok = pl.col("speed_raw").is_not_null() & (pl.col("speed_raw") >= 5) & (pl.col("speed_raw") <= 65)
    speed_default = pl.col("rw_type").replace_strict(DEFAULT_SPEED_MPH, default=25, return_dtype=pl.Int32)
    df = df.with_columns(
        pl.when(lanes_ok).then(pl.col("travel_lanes_raw")).otherwise(lane_default).cast(pl.Int8).alias("travel_lanes"),
        pl.when(lanes_ok).then(0).otherwise(1).cast(pl.Int8).alias("lanes_source"),
        pl.when(speed_ok).then(pl.col("speed_raw")).otherwise(speed_default).cast(pl.Int8).alias("posted_speed_mph"),
        pl.when(speed_ok).then(0).otherwise(1).cast(pl.Int8).alias("speed_source"),
        pl.col("park_lanes_raw").fill_null(0).clip(0, 4).cast(pl.Int8).alias("park_lanes"),
        (pl.col("rw_type") == 2).alias("is_highway"),
        pl.col("street_name").map_elements(normalize_street, return_dtype=pl.Utf8).alias("street_norm"),
    ).with_columns(
        (pl.col("length_m") / 1000.0 * pl.col("travel_lanes")).alias("lane_km"),
        (pl.col("posted_speed_mph") * MPH_TO_KMH).alias("free_flow_kmh"),
        pl.col("bike_lane").is_in([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]).fill_null(False).alias("has_bike_lane"),
        pl.col("bike_lane").is_in([1, 5, 8, 9, 10]).fill_null(False).alias("has_protected_bike_lane"),
        pl.col("truck_route_type").is_not_null().alias("is_truck_route"),
    )
    mids = shapely.line_interpolate_point(geoms, 0.5, normalized=True)
    mx, my = shapely.get_x(mids), shapely.get_y(mids)
    nta_idx = nta.assign_points(mx, my, snap_m=400.0)
    df = df.with_columns(pl.Series("x_mid", mx), pl.Series("y_mid", my), pl.Series("nta_idx", nta_idx.astype(np.int32)))
    n_no_nta = int((nta_idx < 0).sum())
    log.info("segments: %d vehicular kept, %d dropped (non-vehicular/empty), %d without NTA (%.1f km); lanes inferred %d, speed inferred %d",
             df.height, n_drop, n_no_nta, float(df.filter(pl.col("nta_idx") < 0)["length_m"].sum() / 1000),
             int(df["lanes_source"].sum()), int(df["speed_source"].sum()))
    phys_index: dict[int, int] = {}
    for i, p in enumerate(df["physicalid"].to_list()):
        phys_index.setdefault(int(p), i)
    return SegmentTable(df, geoms, STRtree(geoms), phys_index)


def nta_road_summary(seg: SegmentTable, nta: NtaTable) -> pl.DataFrame:
    """Per-NTA lane-km totals and class mix (one row for every NTA, zeros where no roads)."""
    d = seg.df.filter(pl.col("nta_idx") >= 0)
    agg = d.group_by("nta_idx").agg(
        pl.col("lane_km").sum().alias("lane_km"),
        (pl.col("length_m").sum() / 1000).alias("road_km"),
        pl.col("lane_km").filter(pl.col("is_highway")).sum().alias("lane_km_highway"),
        pl.col("lane_km").filter(pl.col("travel_lanes") >= 3).sum().alias("lane_km_arterial"),
        pl.col("length_m").filter(pl.col("has_bike_lane")).sum().alias("bike_lane_m"),
        pl.col("length_m").filter(pl.col("has_protected_bike_lane")).sum().alias("protected_bike_lane_m"),
        pl.col("length_m").filter(pl.col("is_truck_route")).sum().alias("truck_route_m"),
        (pl.col("free_flow_kmh") * pl.col("lane_km")).sum().alias("_vf_w"),
        pl.len().alias("n_segments"),
    )
    base = pl.DataFrame({"nta_idx": np.arange(len(nta), dtype=np.int32), "nta_code": nta.codes,
                         "area_km2": nta.area_km2, "borough": nta.borocode.astype(np.int8), "is_cbd": nta.is_cbd,
                         "is_special": nta.is_special})
    out = base.join(agg, on="nta_idx", how="left").fill_null(0)
    out = out.with_columns(
        pl.when(pl.col("lane_km") > 0).then(pl.col("_vf_w") / pl.col("lane_km")).otherwise(25 * MPH_TO_KMH).alias("free_flow_kmh"),
        (pl.col("lane_km") / pl.col("area_km2")).alias("lane_km_density"),
        pl.when(pl.col("lane_km") > 0).then(pl.col("lane_km_highway") / pl.col("lane_km")).otherwise(0.0).alias("highway_lane_share"),
        pl.when(pl.col("lane_km") > 0).then(pl.col("lane_km_arterial") / pl.col("lane_km")).otherwise(0.0).alias("arterial_lane_share"),
        pl.when(pl.col("road_km") > 0).then(pl.col("bike_lane_m") / 1000 / pl.col("road_km")).otherwise(0.0).alias("bike_lane_share"),
        pl.when(pl.col("road_km") > 0).then(pl.col("protected_bike_lane_m") / 1000 / pl.col("road_km")).otherwise(0.0).alias("protected_bike_share"),
        pl.when(pl.col("road_km") > 0).then(pl.col("truck_route_m") / 1000 / pl.col("road_km")).otherwise(0.0).alias("truck_route_share"),
    ).drop("_vf_w")
    return out
