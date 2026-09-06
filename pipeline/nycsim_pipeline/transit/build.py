"""Transit stage: GTFS + planimetrics + OSM -> ``data/processed/transit/*.parquet`` and ``runtime/transit.nycb``.

    python -m nycsim_pipeline transit [--out-dir DIR] [--skip-ferry-download] [--no-nycb] [--scratch DIR]

Outputs (DATA_CONTRACTS §9):
    ``transit/bus_routes.parquet``      route_id, short_name, long_name, borough, geometry, headway_min[24]
    ``transit/bus_stops.parquet``       stop_id, x, y, z, name, routes, has_shelter
    ``transit/subway_entrances.parquet`` entrance_id, x, y, z, lines, kind, has_globe
    ``transit/rail_structures.parquet`` elevated / viaduct / embankment / open-cut track with deck heights
    ``transit/ferry_routes.parquet``    Staten Island Ferry + NYC Ferry routes with shapes and headways
Appended, clearly-marked extensions (reported, not silently added to the contract):
    ``transit/ferry_terminals.parquet`` ferry landings (the §9 table has no place for them)
    ``transit/rail_routes.parquet``     subway / LIRR / Metro-North routes with shapes and weekday headways
    ``transit/rail_stops.parquet``      subway / LIRR / Metro-North stations
    ``runtime/transit.nycb``            DATA_CONTRACTS §15 binary for ``core/``
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from scipy.spatial import cKDTree

from .. import manifest
from ..crs import NYC_TM, transformer
from ..paths import PROCESSED, RAW
from ..furniture.elevation import GroundModel
from ..runtime import nycb
from . import ferry as ferry_mod
from . import gtfs as G
from . import structures as struct_mod
from .entrances import KIND_ENUM, load_subway_entrances

log = logging.getLogger("nycsim.transit.build")

OUT = PROCESSED / "transit"
RUNTIME = PROCESSED / "runtime"
SHELTERS_CSV = RAW / "nyc_opendata" / "bus_stop_shelters.csv"
SHELTER_JOIN_M = 15.0     # DATA_CONTRACTS §9: "stops joined to shelters within 15 m"

BUS_STOP_SYNTH_ID_BASE = 1_000_000_000


def geo_meta(bbox, geometry_types=("MultiLineString",), column: str = "geometry") -> dict:
    col = {"encoding": "WKB", "geometry_types": list(geometry_types), "crs": NYC_TM.to_json_dict(), "edges": "planar"}
    if bbox is not None and all(np.isfinite(bbox)):
        col["bbox"] = [float(v) for v in bbox]
    return {"version": "1.1.0", "primary_column": column, "columns": {column: col}}


def _write(table: pa.Table, path: Path, schema_id: str, extra: dict | None = None) -> Path:
    meta = {b"nycsim.schema": schema_id.encode(), b"nycsim.schema_version": b"1"}
    if extra:
        meta.update({k.encode(): v.encode() for k, v in extra.items()})
    if table.schema.metadata:
        meta = {**table.schema.metadata, **meta}
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table.replace_schema_metadata(meta), path, compression="snappy")
    log.info("wrote %s (%d rows, %d bytes)", path, table.num_rows, path.stat().st_size)
    return path


# --------------------------------------------------------------------------------- GTFS aggregation

class FeedResult:
    """Everything one GTFS feed contributes."""

    def __init__(self, feed: G.Feed, service_date, services: set[str]) -> None:
        self.feed = feed
        self.service_date = service_date
        self.services = services
        self.trips = pl.DataFrame()
        self.route_hours = pl.DataFrame()
        self.route_stops = pl.DataFrame()
        self.stops = pl.DataFrame()
        self.routes = pl.DataFrame()
        self.shapes: dict[str, np.ndarray] = {}
        self.route_shapes: dict[str, list[str]] = {}


def read_feed(feed: G.Feed, scratch: Path) -> FeedResult:
    day, services = G.pick_service_date(feed)
    trips = feed.table("trips", ["route_id", "service_id", "trip_id", "direction_id", "shape_id"])
    for c in ("route_id", "service_id", "trip_id"):
        trips = trips.with_columns(pl.col(c).str.strip_chars())
    if "direction_id" not in trips.columns:
        trips = trips.with_columns(pl.lit("0").alias("direction_id"))
    if "shape_id" not in trips.columns:
        trips = trips.with_columns(pl.lit("").alias("shape_id"))
    trips = trips.with_columns([pl.col("direction_id").fill_null("").str.strip_chars(),
                                pl.col("shape_id").fill_null("").str.strip_chars()])
    trips = trips.filter(pl.col("service_id").is_in(list(services)))
    # GTFS direction_id is optional. The Staten Island Ferry feed leaves it empty and separates the two
    # directions by shape_id instead, so fall back to shape_id when the whole feed has no direction_id.
    if trips.height and (trips["direction_id"] == "").all():
        log.info("%s: direction_id is empty in this feed — using shape_id as the direction key", feed.feed_id)
        trips = trips.with_columns(pl.col("shape_id").alias("direction_id"))
    trips = trips.with_columns(pl.when(pl.col("direction_id") == "").then(pl.lit("0"))
                               .otherwise(pl.col("direction_id")).alias("direction_id"))
    res = FeedResult(feed, day, services)
    res.trips = trips
    log.info("%s: service day %s, %d services, %d weekday trips", feed.feed_id, day, len(services), trips.height)

    facts = G.scan_stop_times(feed, trips, scratch)
    res.route_stops = facts.route_stops
    joined = trips.select(["trip_id", "route_id", "direction_id"]).join(facts.trip_start, on="trip_id", how="inner")
    res.route_hours = (joined.with_columns(((pl.col("start_s") // 3600) % 24).alias("hour"))
                       .select(["route_id", "direction_id", "hour"]))

    routes = feed.table("routes", ["route_id", "route_short_name", "route_long_name", "route_type", "route_color"])
    routes = routes.with_columns([pl.col(c).fill_null("").str.strip_chars()
                                  for c in routes.columns]).filter(pl.col("route_id").is_in(trips["route_id"].unique().to_list()))
    res.routes = routes

    stops = feed.table("stops", ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"])
    if "location_type" not in stops.columns:
        stops = stops.with_columns(pl.lit("0").alias("location_type"))
    if "parent_station" not in stops.columns:
        stops = stops.with_columns(pl.lit("").alias("parent_station"))
    stops = stops.with_columns([
        pl.col("stop_id").str.strip_chars(), pl.col("stop_name").fill_null("").str.strip_chars(),
        pl.col("stop_lat").str.strip_chars().cast(pl.Float64, strict=False),
        pl.col("stop_lon").str.strip_chars().cast(pl.Float64, strict=False),
        pl.col("location_type").fill_null("0").str.strip_chars(), pl.col("parent_station").fill_null("").str.strip_chars(),
    ]).filter(pl.col("stop_lat").is_finite() & pl.col("stop_lon").is_finite())
    res.stops = stops

    used = set(trips["shape_id"].unique().to_list()) - {""}
    res.shapes = G.shape_lines(feed, used)
    rs: dict[str, set[str]] = defaultdict(set)
    for r, s in trips.select(["route_id", "shape_id"]).unique().iter_rows():
        if s:
            rs[r].add(s)
    res.route_shapes = {k: sorted(v) for k, v in rs.items()}
    return res


def headway_table(route_hours: pl.DataFrame) -> dict[str, list[int]]:
    if route_hours.height == 0:
        return {}
    g = route_hours.group_by(["route_id", "hour"]).agg(
        [pl.len().alias("trips"), pl.col("direction_id").n_unique().alias("dirs")])
    out: dict[str, list[int]] = {}
    for row in g.iter_rows(named=True):
        if row["hour"] is None:
            continue
        arr = out.setdefault(row["route_id"], [0] * 24)
        t = int(row["trips"])
        d = max(int(row["dirs"] or 1), 1)
        arr[int(row["hour"])] = int(min(32767, round(60.0 * d / t))) if t else 0
    return out


def _lines_to_tm(shape_ids: list[str], shapes: dict[str, np.ndarray]):
    tr = transformer("WGS84", "NYC_TM")
    parts = []
    for sid in shape_ids:
        pts = shapes.get(sid)
        if pts is None or len(pts) < 2:
            continue
        x, y = tr.transform(pts[:, 0], pts[:, 1])
        parts.append(shapely.linestrings(np.column_stack([x, y])))
    if not parts:
        return None
    return shapely.multilinestrings(parts) if len(parts) > 1 else shapely.multilinestrings([parts[0]])


def route_table(results: list[FeedResult], route_types: tuple[int, ...], borough_of: dict[str, int],
                agency_of: dict[str, str]) -> tuple[pa.Table, dict[str, list[str]], dict[str, np.ndarray]]:
    """Merge routes of the given ``route_type`` across feeds into one row per route_id."""
    frames = []
    for r in results:
        if r.route_hours.height:
            frames.append(r.route_hours.with_columns(
                (pl.lit((r.feed.agency or "") + ":") + pl.col("route_id")).alias("route_uid")))
    all_hours = pl.concat(frames, how="vertical") if frames else \
        pl.DataFrame({"route_id": [], "direction_id": [], "hour": [], "route_uid": []},
                     schema={"route_id": pl.String, "direction_id": pl.String, "hour": pl.Int64, "route_uid": pl.String})
    headways = headway_table(all_hours.select([pl.col("route_uid").alias("route_id"), "direction_id", "hour"]))

    merged: dict[str, dict] = {}
    shapes: dict[str, np.ndarray] = {}
    route_shape_ids: dict[str, list[str]] = defaultdict(list)
    for res in results:
        rt = res.routes
        if rt.height == 0:
            continue
        agency = res.feed.agency or agency_of.get("", "")
        keep = rt.filter(pl.col("route_type").cast(pl.Int32, strict=False).is_in(list(route_types)))
        for row in keep.iter_rows(named=True):
            rid = row["route_id"]
            uid = f"{agency}:{rid}"          # LIRR route "1" and subway route "1" are different routes
            m = merged.setdefault(uid, {"route_uid": uid, "route_id": rid, "agency": agency,
                                        "short_name": row.get("route_short_name", ""),
                                        "long_name": row.get("route_long_name", ""),
                                        "route_type": int(row["route_type"]), "color": row.get("route_color", ""),
                                        "borough": res.feed.borough, "feeds": []})
            if not m["short_name"]:
                m["short_name"] = row.get("route_short_name", "")
            if not m["long_name"]:
                m["long_name"] = row.get("route_long_name", "")
            m["feeds"].append(res.feed.feed_id)
            for sid in res.route_shapes.get(rid, []):
                key = f"{res.feed.feed_id}:{sid}"
                if key not in shapes and sid in res.shapes:
                    shapes[key] = res.shapes[sid]
                    route_shape_ids[uid].append(key)

    rows = sorted(merged.values(), key=lambda r: (r["route_type"], r["agency"], r["route_id"]))
    geoms = []
    for r in rows:
        g = _lines_to_tm(route_shape_ids.get(r["route_uid"], []), shapes)
        geoms.append(g)
    keep = [i for i, g in enumerate(geoms) if g is not None]
    if len(keep) != len(rows):
        dropped = [rows[i]["route_uid"] for i in range(len(rows)) if i not in set(keep)]
        log.warning("%d routes have no usable shape and are dropped: %s", len(rows) - len(keep), dropped[:20])
    rows = [rows[i] for i in keep]
    geoms = [geoms[i] for i in keep]

    wkb = [shapely.to_wkb(g) for g in geoms]
    bbox = shapely.total_bounds(np.asarray(geoms, dtype=object)) if geoms else (np.nan,) * 4
    trips_by_uid = dict(all_hours.group_by("route_uid").len().iter_rows()) if all_hours.height else {}
    longest = [max((float(shapely.length(p)) for p in shapely.get_parts(g)), default=0.0) for g in geoms]
    table = pa.table({
        "route_id": pa.array([r["route_id"] for r in rows]),
        "route_uid": pa.array([r["route_uid"] for r in rows]),
        "short_name": pa.array([r["short_name"] or r["route_id"] for r in rows]),
        "long_name": pa.array([r["long_name"] for r in rows]),
        "borough": pa.array([np.int8(borough_of.get(r["route_id"], r["borough"])) for r in rows], type=pa.int8()),
        "agency": pa.array([r["agency"] or agency_of.get(r["route_id"], "") for r in rows]),
        "route_type": pa.array([np.int8(r["route_type"]) for r in rows], type=pa.int8()),
        "color": pa.array([r["color"] for r in rows]),
        "feeds": pa.array([sorted(set(r["feeds"])) for r in rows], type=pa.list_(pa.string())),
        "geometry": pa.array(wkb, type=pa.binary()),
        "shape_count": pa.array([len(route_shape_ids.get(r["route_uid"], [])) for r in rows], type=pa.int32()),
        "length_m": pa.array(np.asarray(longest, dtype=np.float32), type=pa.float32()),
        "total_shape_length_m": pa.array([np.float32(shapely.length(g)) for g in geoms], type=pa.float32()),
        "headway_min": pa.array([[np.int16(v) for v in headways.get(r["route_uid"], [0] * 24)] for r in rows],
                                type=pa.list_(pa.int16())),
        "trips_weekday": pa.array([int(trips_by_uid.get(r["route_uid"], 0)) for r in rows], type=pa.int32()),
    })
    table = table.replace_schema_metadata({b"geo": json.dumps(geo_meta(bbox)).encode()})
    return table, {r["route_id"]: route_shape_ids.get(r["route_id"], []) for r in rows}, shapes


def stop_table(results: list[FeedResult], ground: GroundModel, shelters_xy: np.ndarray | None,
               location_types: tuple[str, ...] = ("0", "")) -> pa.Table:
    """Merge stops across feeds; ``routes`` is the union of the routes calling there on the service day."""
    tr = transformer("WGS84", "NYC_TM")
    info: dict[str, dict] = {}
    for res in results:
        routes_by_stop: dict[str, set[str]] = defaultdict(set)
        for rid, sid in res.route_stops.iter_rows():
            routes_by_stop[sid].add(rid)
        for row in res.stops.iter_rows(named=True):
            sid = row["stop_id"]
            if row["location_type"] not in location_types:
                continue
            if sid not in routes_by_stop:
                continue
            e = info.setdefault(sid, {"stop_id": sid, "name": row["stop_name"], "lat": row["stop_lat"],
                                      "lon": row["stop_lon"], "routes": set(), "feeds": set(),
                                      "parent": row["parent_station"]})
            e["routes"].update(routes_by_stop[sid])
            e["feeds"].add(res.feed.feed_id)
            if not e["name"]:
                e["name"] = row["stop_name"]
    rows = sorted(info.values(), key=lambda r: r["stop_id"])
    if not rows:
        raise RuntimeError("no stops found in any feed")
    lon = np.array([r["lon"] for r in rows])
    lat = np.array([r["lat"] for r in rows])
    x, y = tr.transform(lon, lat)
    x = np.asarray(x)
    y = np.asarray(y)
    z, z_src = ground.sample(x, y)
    if shelters_xy is not None and len(shelters_xy):
        d, _ = cKDTree(shelters_xy).query(np.column_stack([x, y]), k=1, workers=1)
        has_shelter = d <= SHELTER_JOIN_M
        shelter_dist = np.where(has_shelter, d, np.nan)
        log.info("bus stops: %d of %d have a DOT shelter within %.0f m", int(has_shelter.sum()), len(rows), SHELTER_JOIN_M)
    else:
        has_shelter = np.zeros(len(rows), dtype=bool)
        shelter_dist = np.full(len(rows), np.nan)
    return pa.table({
        "stop_id": pa.array([r["stop_id"] for r in rows]),
        "x": pa.array(x.astype(np.float64)),
        "y": pa.array(y.astype(np.float64)),
        "z": pa.array(z.astype(np.float32)),
        "z_source": pa.array(z_src.astype(np.int8), type=pa.int8()),
        "name": pa.array([r["name"] for r in rows]),
        "routes": pa.array([sorted(r["routes"]) for r in rows], type=pa.list_(pa.string())),
        "has_shelter": pa.array(has_shelter),
        "shelter_dist_m": pa.array(shelter_dist.astype(np.float32)),
        "parent_station": pa.array([r["parent"] for r in rows]),
        "feeds": pa.array([sorted(r["feeds"]) for r in rows], type=pa.list_(pa.string())),
    })


def load_shelter_points() -> np.ndarray:
    if not SHELTERS_CSV.exists():
        log.warning("%s missing — has_shelter will be False everywhere", SHELTERS_CSV)
        return np.empty((0, 2))
    df = pl.read_csv(SHELTERS_CSV, infer_schema_length=0)
    df.columns = [c.strip() for c in df.columns]
    lon = df["Longitude"].cast(pl.Float64, strict=False).to_numpy()
    lat = df["Latitude"].cast(pl.Float64, strict=False).to_numpy()
    ok = np.isfinite(lon) & np.isfinite(lat)
    x, y = transformer("WGS84", "NYC_TM").transform(lon[ok], lat[ok])
    log.info("bus shelters: %d points", int(ok.sum()))
    return np.column_stack([np.asarray(x), np.asarray(y)])


# --------------------------------------------------------------------------------- subway entrances

def subway_entrance_table(ground: GroundModel) -> pa.Table:
    df = load_subway_entrances()
    x = df["x"].to_numpy().astype(np.float64)
    y = df["y"].to_numpy().astype(np.float64)
    z, z_src = ground.sample(x, y)
    return pa.table({
        "entrance_id": pa.array(df["entrance_id"].to_numpy().astype(np.int64)),
        "x": pa.array(x), "y": pa.array(y),
        "z": pa.array(z.astype(np.float32)),
        "z_source": pa.array(z_src.astype(np.int8), type=pa.int8()),
        "lines": pa.array([list(v) for v in df["lines"]], type=pa.list_(pa.string())),
        "kind": pa.array([str(v) for v in df["kind"]]),
        "kind_code": pa.array([np.int8(KIND_ENUM.get(str(v), 0)) for v in df["kind"]], type=pa.int8()),
        "has_globe": pa.array(np.asarray(df["has_globe"], dtype=np.int8), type=pa.int8()),
        "entrance_type": pa.array([str(v) for v in df["entrance_type"]]),
        "station_id": pa.array(np.asarray(df["station_id"], dtype=np.int64)),
        "complex_id": pa.array(np.asarray(df["complex_id"], dtype=np.int64)),
        "gtfs_stop_id": pa.array([str(v) for v in df["gtfs_stop_id"]]),
        "stop_name": pa.array([str(v) for v in df["stop_name"]]),
        "division": pa.array([str(v) for v in df["division"]]),
        "line": pa.array([str(v) for v in df["line"]]),
        "borough": pa.array(np.asarray(df["borough"], dtype=np.int8), type=pa.int8()),
        "entry_allowed": pa.array(np.asarray(df["entry_allowed"], dtype=bool)),
        "exit_allowed": pa.array(np.asarray(df["exit_allowed"], dtype=bool)),
    })


# --------------------------------------------------------------------------------- ferries

def build_ferries(ground: GroundModel, scratch: Path, download_feeds: bool = True) -> tuple[pa.Table, pa.Table, list[dict]]:
    paths = ferry_mod.fetch_feeds() if download_feeds else {
        fid: G.GTFS_DIR / src.local_name for fid, src in ferry_mod.FERRY_SOURCES.items()}
    results: list[FeedResult] = []
    licences = []
    for fid, p in paths.items():
        label = "NYC DOT — Staten Island Ferry" if "staten" in fid else "NYC Ferry (NYCEDC/Hornblower)"
        feed = G.Feed(fid, Path(p), label, 0)
        results.append(read_feed(feed, scratch))
        licences.append({**feed.license_note(), "license": ferry_mod.FERRY_SOURCES[fid].license,
                         "attribution": ferry_mod.FERRY_SOURCES[fid].attribution, "url": ferry_mod.FERRY_SOURCES[fid].url})
    agency = {}
    for res in results:
        label = "NYC DOT — Staten Island Ferry" if "staten" in res.feed.feed_id else "NYC Ferry (NYCEDC/Hornblower)"
        for rid in res.routes["route_id"].to_list():
            agency[rid] = label
    routes, _shape_ids, _shapes = route_table(results, (G.ROUTE_TYPE_FERRY,), {}, agency)

    ferry_route_ids = set(routes.column("route_id").to_pylist())
    tr = transformer("WGS84", "NYC_TM")
    rows: list[dict] = []
    for res in results:
        routes_by_stop: dict[str, set[str]] = defaultdict(set)
        for rid, sid in res.route_stops.iter_rows():
            if rid in ferry_route_ids:
                routes_by_stop[sid].add(rid)
        for row in res.stops.iter_rows(named=True):
            if row["stop_id"] not in routes_by_stop:
                continue
            x, y = tr.transform(row["stop_lon"], row["stop_lat"])
            rows.append({"stop_id": row["stop_id"], "name": row["stop_name"], "x": float(x), "y": float(y),
                         "routes": sorted(routes_by_stop[row["stop_id"]]), "feed": res.feed.feed_id})
    berths = ferry_mod.dedupe_terminals(rows)
    bx = np.array([b["x"] for b in berths])
    by = np.array([b["y"] for b in berths])
    bz, bzs = ground.sample(bx, by) if len(berths) else (np.empty(0), np.empty(0, dtype=np.int8))
    terminals = pa.table({
        "terminal_id": pa.array(np.arange(len(berths), dtype=np.int64)),
        "name": pa.array([b["name"] for b in berths]),
        "x": pa.array(bx), "y": pa.array(by),
        "z": pa.array(bz.astype(np.float32)),
        "z_source": pa.array(bzs.astype(np.int8), type=pa.int8()),
        "routes": pa.array([b["routes"] for b in berths], type=pa.list_(pa.string())),
        "stop_ids": pa.array([b["stop_ids"] for b in berths], type=pa.list_(pa.string())),
    })
    return routes, terminals, licences


# --------------------------------------------------------------------------------- runtime binary

def _stop_int_id(stop_id: str, index: int) -> int:
    s = stop_id.strip()
    return int(s) if s.isdigit() else BUS_STOP_SYNTH_ID_BASE + index


BUS_ROUTE_DTYPE = nycb.aligned_dtype([("name_str", "<u4"), ("first_vertex", "<u4"), ("vertex_count", "<u4"),
                                      ("first_stop", "<u4"), ("stop_count", "<u4"), ("headway_min", "<u2", (24,))])
BUS_STOP_DTYPE = nycb.aligned_dtype([("id", "<i8"), ("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("name_str", "<u4")])
ROUTE_STOP_DTYPE = nycb.aligned_dtype([("stop_id", "<i8")])
VERTEX_DTYPE = nycb.aligned_dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4")])


def export_nycb(routes: pa.Table, stops: pa.Table, path: Path) -> dict:
    """DATA_CONTRACTS §15 ``runtime/transit.nycb``.

    ``bus_routes.first_vertex/vertex_count`` reference the **longest single shape** of the route (the primary
    alignment); the other shape variants live in the Parquet geometry. ``route_stops`` lists the integer stop ids
    of the route in ``stop_id`` order.
    """
    w = nycb.NycbWriter()
    stop_ids = stops.column("stop_id").to_pylist()
    sx = stops.column("x").to_numpy(zero_copy_only=False)
    sy = stops.column("y").to_numpy(zero_copy_only=False)
    sz = stops.column("z").to_numpy(zero_copy_only=False)
    snames = stops.column("name").to_pylist()
    sroutes = stops.column("routes").to_pylist()
    int_ids = np.array([_stop_int_id(s, i) for i, s in enumerate(stop_ids)], dtype=np.int64)

    stop_arr = np.zeros(len(stop_ids), dtype=BUS_STOP_DTYPE)
    stop_arr["id"] = int_ids
    stop_arr["x"] = sx.astype(np.float32)
    stop_arr["y"] = sy.astype(np.float32)
    stop_arr["z"] = np.nan_to_num(sz.astype(np.float32), nan=0.0)
    stop_arr["name_str"] = w.strings.add_many(snames)

    by_route: dict[str, list[int]] = defaultdict(list)
    for i, rl in enumerate(sroutes):
        for r in rl:
            by_route[r].append(i)

    rids = routes.column("route_id").to_pylist()
    short = routes.column("short_name").to_pylist()
    headways = routes.column("headway_min").to_pylist()
    geoms = shapely.from_wkb(routes.column("geometry").to_pylist())

    verts: list[np.ndarray] = []
    route_stop_ids: list[np.ndarray] = []
    route_arr = np.zeros(len(rids), dtype=BUS_ROUTE_DTYPE)
    v_off = 0
    s_off = 0
    for i, rid in enumerate(rids):
        parts = shapely.get_parts(geoms[i])
        best = max(parts, key=lambda g: shapely.length(g)) if len(parts) else None
        c = shapely.get_coordinates(best)[:, :2] if best is not None else np.empty((0, 2))
        v = np.zeros(len(c), dtype=VERTEX_DTYPE)
        if len(c):
            v["x"] = c[:, 0].astype(np.float32)
            v["y"] = c[:, 1].astype(np.float32)
        verts.append(v)
        ids = int_ids[np.asarray(by_route.get(rid, []), dtype=np.int64)] if by_route.get(rid) else np.empty(0, np.int64)
        rs = np.zeros(len(ids), dtype=ROUTE_STOP_DTYPE)
        rs["stop_id"] = ids
        route_stop_ids.append(rs)
        route_arr[i]["name_str"] = w.strings.add(short[i] or rid)
        route_arr[i]["first_vertex"] = v_off
        route_arr[i]["vertex_count"] = len(v)
        route_arr[i]["first_stop"] = s_off
        route_arr[i]["stop_count"] = len(rs)
        route_arr[i]["headway_min"] = np.clip(np.asarray(headways[i], dtype=np.int64), 0, 65535).astype(np.uint16)
        v_off += len(v)
        s_off += len(rs)

    w.add_array("bus_routes", route_arr)
    w.add_array("bus_stops", stop_arr)
    w.add_array("route_stops", np.concatenate(route_stop_ids) if route_stop_ids else np.zeros(0, ROUTE_STOP_DTYPE))
    w.add_array("vertices", np.concatenate(verts) if verts else np.zeros(0, VERTEX_DTYPE))
    w.add_strtab()
    w.write(path)
    layout_path = path.with_suffix(".layout.json")
    nycb.write_layout(layout_path, {"bus_routes": BUS_ROUTE_DTYPE, "bus_stops": BUS_STOP_DTYPE,
                                    "route_stops": ROUTE_STOP_DTYPE, "vertices": VERTEX_DTYPE})
    return {"path": str(path), "bytes": path.stat().st_size, "bus_routes": len(route_arr), "bus_stops": len(stop_arr),
            "route_stops": int(s_off), "vertices": int(v_off), "layout": str(layout_path)}


# --------------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--scratch", default="", help="scratch directory for stop_times extraction (default: out-dir/_scratch)")
    ap.add_argument("--skip-ferry-download", action="store_true", help="use the ferry zips already on disk")
    ap.add_argument("--no-nycb", action="store_true")
    ap.add_argument("--no-manifest", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    t0 = time.perf_counter()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scratch = Path(a.scratch) if a.scratch else out / "_scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    summary: dict = {"schema_version": 1, "stage": "transit", "outputs": {}, "licences": [], "timings_s": {}}

    try:
        log.info("building the ground elevation model")
        ground = GroundModel.build()
        summary["ground_model"] = {"reference_points": ground.n_points, "spot_elevations": ground.n_spot,
                                   "building_grades": ground.n_points - ground.n_spot}
        summary["timings_s"]["ground_model"] = round(time.perf_counter() - t0, 1)

        # ---- buses -------------------------------------------------------------------------------
        t = time.perf_counter()
        bus_results: list[FeedResult] = []
        borough_of: dict[str, int] = {}
        agency_of: dict[str, str] = {}
        for fid, (zn, ag, boro) in G.BUS_FEEDS.items():
            feed = G.Feed(fid, G.GTFS_DIR / zn, ag, boro)
            res = read_feed(feed, scratch)
            bus_results.append(res)
            for rid in res.routes["route_id"].to_list():
                borough_of.setdefault(rid, boro)
                agency_of.setdefault(rid, ag)
            summary["licences"].append({**feed.license_note(), "license": "MTA Developer Data Terms"})
        bus_routes, _sid, _sh = route_table(bus_results, (G.ROUTE_TYPE_BUS,), borough_of, agency_of)
        shelters = load_shelter_points()
        bus_stops = stop_table(bus_results, ground, shelters)
        _write(bus_routes, out / "bus_routes.parquet", "transit_bus_routes/1")
        _write(bus_stops, out / "bus_stops.parquet", "transit_bus_stops/1")
        summary["outputs"]["bus_routes"] = {"rows": bus_routes.num_rows,
                                            "service_dates": sorted({str(r.service_date) for r in bus_results})}
        summary["outputs"]["bus_stops"] = {"rows": bus_stops.num_rows,
                                           "with_shelter": int(np.asarray(bus_stops.column("has_shelter").to_pylist()).sum())}
        summary["timings_s"]["bus"] = round(time.perf_counter() - t, 1)
        del bus_results

        # ---- subway / commuter rail --------------------------------------------------------------
        t = time.perf_counter()
        rail_results: list[FeedResult] = []
        rail_agency: dict[str, str] = {}
        rail_feed_specs = [G.SUBWAY_FEED] + [(k, v[0], v[1]) for k, v in G.RAIL_FEEDS.items()]
        for fid, zn, ag in rail_feed_specs:
            feed = G.Feed(fid, G.GTFS_DIR / zn, ag, 0)
            res = read_feed(feed, scratch)
            rail_results.append(res)
            for rid in res.routes["route_id"].to_list():
                rail_agency.setdefault(rid, ag)
            summary["licences"].append({**feed.license_note(), "license": "MTA Developer Data Terms"})
        rail_routes, _s2, _sh2 = route_table(rail_results, (G.ROUTE_TYPE_SUBWAY, G.ROUTE_TYPE_RAIL, G.ROUTE_TYPE_TRAM),
                                             {}, rail_agency)
        rail_stops = stop_table(rail_results, ground, None)
        _write(rail_routes, out / "rail_routes.parquet", "transit_rail_routes/1")
        _write(rail_stops, out / "rail_stops.parquet", "transit_rail_stops/1")
        summary["outputs"]["rail_routes"] = {"rows": rail_routes.num_rows}
        summary["outputs"]["rail_stops"] = {"rows": rail_stops.num_rows}
        summary["timings_s"]["rail_gtfs"] = round(time.perf_counter() - t, 1)
        del rail_results

        # ---- subway entrances --------------------------------------------------------------------
        t = time.perf_counter()
        ent = subway_entrance_table(ground)
        _write(ent, out / "subway_entrances.parquet", "transit_subway_entrances/1")
        globes = np.asarray(ent.column("has_globe").to_pylist())
        summary["outputs"]["subway_entrances"] = {
            "rows": ent.num_rows, "globe_green": int((globes == 1).sum()), "globe_red": int((globes == 2).sum()),
            "globe_none": int((globes == 0).sum()),
            "by_kind": {k: int(v) for k, v in zip(*np.unique(np.asarray(ent.column("kind").to_pylist()), return_counts=True))}}
        summary["licences"].append({"feed_id": "subway_entrances", "agency": "Metropolitan Transportation Authority",
                                    "license": "NY State Open Data Terms (data.ny.gov i9wp-a4ja)"})
        summary["timings_s"]["subway_entrances"] = round(time.perf_counter() - t, 1)

        # ---- rail structures ---------------------------------------------------------------------
        t = time.perf_counter()
        rs = struct_mod.build(ground)
        bbox = shapely.total_bounds(np.asarray(shapely.from_wkb(rs.column("geometry").to_pylist()), dtype=object))
        rs = rs.replace_schema_metadata({b"geo": json.dumps(geo_meta(bbox, ("LineString",))).encode()})
        _write(rs, out / "rail_structures.parquet", "transit_rail_structures/1")
        kinds = np.asarray(rs.column("kind").to_pylist())
        lengths = np.asarray(rs.column("length_m").to_pylist(), dtype=float)
        hsrc = np.asarray(rs.column("deck_height_source").to_pylist(), dtype=int)
        heights = np.asarray(rs.column("deck_height_m").to_pylist(), dtype=float)
        summary["outputs"]["rail_structures"] = {
            "rows": rs.num_rows,
            "by_kind": {k: {"rows": int((kinds == k).sum()), "km": round(float(lengths[kinds == k].sum()) / 1000.0, 3),
                            "deck_height_measured": int(((kinds == k) & (hsrc == 0)).sum()),
                            "deck_height_median_m": (round(float(np.nanmedian(heights[kinds == k])), 2)
                                                     if np.isfinite(heights[kinds == k]).any() else None)}
                        for k in sorted(set(kinds.tolist()))},
            "total_km": round(float(lengths.sum()) / 1000.0, 3)}
        summary["licences"].append({"feed_id": "plan_railroad_line", "agency": "NYC Office of Technology and Innovation",
                                    "license": "NYC Open Data Terms of Use"})
        summary["licences"].append({"feed_id": "osm_newyork_pbf", "agency": "OpenStreetMap contributors",
                                    "license": "ODbL 1.0"})
        summary["timings_s"]["rail_structures"] = round(time.perf_counter() - t, 1)

        # ---- ferries -----------------------------------------------------------------------------
        t = time.perf_counter()
        fr, ft, flic = build_ferries(ground, scratch, download_feeds=not a.skip_ferry_download)
        _write(fr, out / "ferry_routes.parquet", "transit_ferry_routes/1")
        _write(ft, out / "ferry_terminals.parquet", "transit_ferry_terminals/1")
        summary["outputs"]["ferry_routes"] = {"rows": fr.num_rows, "routes": fr.column("route_id").to_pylist()}
        summary["outputs"]["ferry_terminals"] = {"rows": ft.num_rows, "names": ft.column("name").to_pylist()}
        summary["licences"].extend(flic)
        summary["timings_s"]["ferry"] = round(time.perf_counter() - t, 1)

        # ---- runtime binary ----------------------------------------------------------------------
        if not a.no_nycb:
            t = time.perf_counter()
            RUNTIME.mkdir(parents=True, exist_ok=True)
            summary["outputs"]["transit_nycb"] = export_nycb(bus_routes, bus_stops, RUNTIME / "transit.nycb")
            summary["timings_s"]["nycb"] = round(time.perf_counter() - t, 1)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    summary["timings_s"]["total"] = round(time.perf_counter() - t0, 1)
    (out / "build_summary.json").write_text(json.dumps(summary, indent=1))
    log.info("transit stage done in %.1f s", summary["timings_s"]["total"])

    if not a.no_manifest and Path(a.out_dir) == OUT:
        srcs = sorted(G.BUS_FEEDS) + [G.SUBWAY_FEED[0]] + sorted(G.RAIL_FEEDS) + \
            ["subway_entrances", "plan_railroad_line", "plan_elevation_points", "osm_newyork_pbf",
             "bus_stop_shelters", "gtfs_ferry_staten_island", "gtfs_ferry_nyc"]
        for aid, p, schema in [("transit_bus_routes", out / "bus_routes.parquet", "transit_bus_routes/1"),
                               ("transit_bus_stops", out / "bus_stops.parquet", "transit_bus_stops/1"),
                               ("transit_subway_entrances", out / "subway_entrances.parquet", "transit_subway_entrances/1"),
                               ("transit_rail_structures", out / "rail_structures.parquet", "transit_rail_structures/1"),
                               ("transit_ferry_routes", out / "ferry_routes.parquet", "transit_ferry_routes/1"),
                               ("transit_ferry_terminals", out / "ferry_terminals.parquet", "transit_ferry_terminals/1"),
                               ("transit_rail_routes", out / "rail_routes.parquet", "transit_rail_routes/1"),
                               ("transit_rail_stops", out / "rail_stops.parquet", "transit_rail_stops/1")]:
            if p.exists():
                manifest.record_processed(aid, p, stage="transit", sources=srcs,
                                          rows=pq.ParquetFile(p).metadata.num_rows, schema=schema)
        if (RUNTIME / "transit.nycb").exists():
            manifest.record_processed("runtime_transit_nycb", RUNTIME / "transit.nycb", stage="transit",
                                      sources=srcs, schema="nycb/1")
        manifest.record_processed("transit_build_summary", out / "build_summary.json", stage="transit",
                                  sources=srcs, schema="transit_build_summary/1")

    print(json.dumps({k: summary[k] for k in ("outputs", "timings_s")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
