"""Loaders for every street-furniture dataset -> the common prop column dict (:mod:`.schema`).

Every loader returns ``dict[str, np.ndarray | list]`` with the columns of ``props.parquet`` filled in for one
``kind`` (or, for OSM and the Parks structures, for several kinds). Coordinates are converted to NYC_TM here;
``z`` / ``z_source`` / ``prop_id`` / ``tile`` are filled centrally by :mod:`.build`.

Provenance rules:
* ``source`` is 0 (dataset) for everything in this module — nothing here is invented; :mod:`.rules` produces the
  ``source = 1`` rows.
* ``dataset_id`` is the manifest source id, so every prop can be traced back to ``data/manifest/downloads.json``.
* ``height_m`` is only set where the dataset publishes a per-instance height (Parks structures) or the catalog
  gives a published nominal size (``height_source`` 2); trees get the allometric estimate (``height_source`` 1).
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely

from ..crs import US_SURVEY_FOOT_M, transformer
from ..paths import PROCESSED, RAW
from . import allometry
from .catalog import HEIGHT_SOURCE, KIND_BY_NAME, KIND_ID, SOURCE_DATASET
from .schema import FIELDS, empty_columns
from .trees import CensusHeights
from .trees import HEALTH_UNKNOWN as TREE_HEALTH_UNKNOWN

log = logging.getLogger("nycsim.furniture.datasets")

OPEN = RAW / "nyc_opendata"
OSM_FURNITURE = PROCESSED / "osm" / "street_furniture_osm.parquet"
OSM_TREES = PROCESSED / "osm" / "trees.parquet"
CITIBIKE = RAW / "furniture" / "citibike_gbfs_stations.json"

INCH_M = 0.0254
_POINT_RE = re.compile(r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)", re.I)


# --------------------------------------------------------------------------------------- helpers

def _lonlat_to_tm(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x, y = transformer("WGS84", "NYC_TM").transform(np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64))
    return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)


def _wkt_point_lonlat(values: list[str | None]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parse ``POINT (lon lat)`` strings. Returns lon, lat, ok-mask."""
    lon = np.full(len(values), np.nan)
    lat = np.full(len(values), np.nan)
    for i, v in enumerate(values):
        if not v:
            continue
        m = _POINT_RE.search(v)
        if m:
            lon[i] = float(m.group(1))
            lat[i] = float(m.group(2))
    ok = np.isfinite(lon) & np.isfinite(lat)
    return lon, lat, ok


def _new(kind_name: str, n: int, dataset_id: str) -> dict:
    cols = empty_columns(n)
    cols["kind"] = np.full(n, KIND_ID[kind_name], dtype=np.int16)
    cols["source"] = np.full(n, SOURCE_DATASET, dtype=np.int8)
    cols["dataset_id"] = [dataset_id] * n
    k = KIND_BY_NAME[kind_name]
    if k.dims_m[2] > 0:
        cols["height_m"] = np.full(n, k.dims_m[2], dtype=np.float32)
        cols["height_source"] = np.full(n, HEIGHT_SOURCE["nominal"], dtype=np.int8)
    else:
        cols["height_source"] = np.full(n, HEIGHT_SOURCE["none"], dtype=np.int8)
    return cols


def _attrs(rows: list[dict]) -> list[str]:
    return [json.dumps({k: v for k, v in r.items() if v not in (None, "", [])}, separators=(",", ":")) for r in rows]


def _csv(path: Path, columns: list[str]) -> pl.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id {path.stem}")
    df = pl.read_csv(path, infer_schema_length=0, encoding="utf8-lossy")
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"{path.name}: missing columns {missing}; have {df.columns}")
    return df.select(columns)


def _str(df: pl.DataFrame, col: str) -> list[str]:
    return df[col].fill_null("").cast(pl.String).str.strip_chars().to_list()


def _polygon_layer(path: Path, columns: list[str], where: dict[str, tuple[str, ...]] | None = None,
                   batch_size: int = 100_000) -> tuple[np.ndarray, dict[str, list]]:
    """Stream a polygon GeoJSON with pyogrio, optionally filtering on string attribute values.

    Returns shapely geometries reprojected to NYC_TM and the requested attribute columns.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id {path.stem}")
    tr = transformer("WGS84", "NYC_TM")
    geoms: list[np.ndarray] = []
    attrs: dict[str, list] = {c: [] for c in columns}
    total = 0
    with pyogrio.open_arrow(path, columns=columns, batch_size=batch_size) as (_meta, stream):
        reader = pa.RecordBatchReader.from_stream(stream)
        for batch in reader:
            total += batch.num_rows
            data = {c: batch.column(c).to_pylist() for c in columns}
            keep = np.ones(batch.num_rows, dtype=bool)
            for col, allowed in (where or {}).items():
                keep &= np.isin(np.asarray(data[col], dtype=object), np.asarray(allowed, dtype=object))
            idx = np.flatnonzero(keep)
            if idx.size == 0:
                continue
            wkb = batch.column("wkb_geometry").to_pylist()
            g = shapely.from_wkb([wkb[i] for i in idx])
            geoms.append(g)
            for c in columns:
                attrs[c].extend(data[c][i] for i in idx)
    if not geoms:
        return np.empty(0, dtype=object), attrs
    g = np.concatenate(geoms)
    g = shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
    log.info("%s: %d of %d features kept", path.name, len(g), total)
    return g, attrs


def _footprint_metrics(geoms: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Centroid x/y, area, oriented bbox width/depth and compass heading of the long axis."""
    cent = shapely.centroid(geoms)
    cx = shapely.get_x(cent)
    cy = shapely.get_y(cent)
    area = shapely.area(geoms)
    rects = shapely.oriented_envelope(geoms)
    w = np.zeros(len(geoms))
    d = np.zeros(len(geoms))
    head = np.full(len(geoms), np.nan)
    coords = shapely.get_coordinates(rects)
    counts = shapely.get_num_coordinates(rects)
    off = 0
    for i, c in enumerate(counts):
        pts = coords[off:off + c]
        off += c
        if c < 4:
            continue
        e1 = pts[1] - pts[0]
        e2 = pts[2] - pts[1]
        l1 = float(np.hypot(*e1))
        l2 = float(np.hypot(*e2))
        long_e, lo, sh = (e1, l1, l2) if l1 >= l2 else (e2, l2, l1)
        w[i] = lo
        d[i] = sh
        head[i] = (np.degrees(np.arctan2(long_e[0], long_e[1]))) % 180.0
    return cx, cy, area, w, d, head


# --------------------------------------------------------------------------------------- point datasets

def load_hydrants(path: Path = OPEN / "hydrants.geojson") -> dict:
    """DEP citywide fire hydrants (``5bgh-vtsn``). Coordinates come from the feature geometry."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id hydrants")
    tr = transformer("WGS84", "NYC_TM")
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    unit: list[str] = []
    boro: list[str] = []
    with pyogrio.open_arrow(path, columns=["unitid", "boro"], batch_size=100_000) as (_meta, stream):
        reader = pa.RecordBatchReader.from_stream(stream)
        for batch in reader:
            wkb = batch.column("wkb_geometry").to_pylist()
            good = [i for i, b in enumerate(wkb) if b is not None and len(b) >= 21]
            if not good:
                continue
            buf = np.frombuffer(b"".join(wkb[i][5:21] for i in good), dtype="<f8").reshape(-1, 2)
            x, y = tr.transform(buf[:, 0], buf[:, 1])
            xs.append(np.asarray(x))
            ys.append(np.asarray(y))
            u = batch.column("unitid").to_pylist()
            b_ = batch.column("boro").to_pylist()
            unit.extend(str(u[i] or "") for i in good)
            boro.extend(str(b_[i] or "") for i in good)
    x = np.concatenate(xs) if xs else np.empty(0)
    y = np.concatenate(ys) if ys else np.empty(0)
    cols = _new("hydrant", len(x), "hydrants")
    cols["x"], cols["y"] = x, y
    cols["text"] = unit
    cols["attrs"] = _attrs([{"unitid": u, "boro": b} for u, b in zip(unit, boro)])
    log.info("hydrants: %d", len(x))
    return cols


def load_bus_shelters(path: Path = OPEN / "bus_stop_shelters.csv") -> dict:
    df = _csv(path, ["Shelter_ID", "Corner", "On_Street", "Cross_Stre", "Longitude", "Latitude", "BoroName"])
    lon = df["Longitude"].cast(pl.Float64, strict=False).to_numpy()
    lat = df["Latitude"].cast(pl.Float64, strict=False).to_numpy()
    ok = np.isfinite(lon) & np.isfinite(lat)
    df = df.filter(ok)
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    cols = _new("bus_shelter", len(x), "bus_stop_shelters")
    cols["x"], cols["y"] = x, y
    on, cross, corner, sid = _str(df, "On_Street"), _str(df, "Cross_Stre"), _str(df, "Corner"), _str(df, "Shelter_ID")
    cols["text"] = [f"{a} / {b}".strip(" /") for a, b in zip(on, cross)]
    cols["attrs"] = _attrs([{"shelter_id": s, "corner": c, "on_street": a, "cross_street": b, "boro": bo}
                            for s, c, a, b, bo in zip(sid, corner, on, cross, _str(df, "BoroName"))])
    log.info("bus shelters: %d", len(x))
    return cols


def load_linknyc(path: Path = OPEN / "linknyc.csv") -> dict:
    """LinkNYC kiosks (``s4kf-3yrf``). ``Planned Kiosk Type`` drives the variant; 4 legacy payphone sites become kind 19."""
    df = _csv(path, ["Site ID", "Planned Kiosk Type", "Installation Status", "Street Address", "Latitude", "Longitude", "Borough"])
    lon = df["Longitude"].cast(pl.Float64, strict=False).to_numpy()
    lat = df["Latitude"].cast(pl.Float64, strict=False).to_numpy()
    ok = np.isfinite(lon) & np.isfinite(lat)
    df = df.filter(ok)
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    kind_type = [t.strip() for t in _str(df, "Planned Kiosk Type")]
    is_phone = np.array([t.lower() == "public payphones" for t in kind_type])
    variant_map = {"link1.0": 0, "link5g_ad": 1, "link5g_nonad": 2}
    out = []
    for name, mask in (("linknyc", ~is_phone), ("payphone", is_phone)):
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            continue
        cols = _new(name, idx.size, "linknyc")
        cols["x"], cols["y"] = x[idx], y[idx]
        sid = _str(df, "Site ID")
        addr = _str(df, "Street Address")
        status = _str(df, "Installation Status")
        cols["text"] = [sid[i] for i in idx]
        if name == "linknyc":
            cols["variant"] = np.array([variant_map.get(kind_type[i].lower(), 0) for i in idx], dtype=np.int16)
            # Link5G is a 32 ft (9.75 m) pole; Link1.0 is the 9 ft 6 in kiosk.
            cols["height_m"] = np.where(cols["variant"] > 0, 9.75, 2.9).astype(np.float32)
        cols["attrs"] = _attrs([{"site_id": sid[i], "kiosk_type": kind_type[i], "status": status[i], "address": addr[i]}
                                for i in idx])
        out.append(cols)
        log.info("linknyc %s: %d", name, idx.size)
    return _concat(out)


def load_newsstands(path: Path = OPEN / "newsstands.csv") -> dict:
    df = _csv(path, ["the_geom", "NewsStand_", "Street_on", "Built_Date", "BoroName"])
    lon, lat, ok = _wkt_point_lonlat(_str(df, "the_geom"))
    df = df.filter(ok)
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    cols = _new("newsstand", len(x), "newsstands")
    cols["x"], cols["y"] = x, y
    cols["text"] = _str(df, "Street_on")
    cols["attrs"] = _attrs([{"newsstand_id": i, "street": s, "built": b, "boro": bo}
                            for i, s, b, bo in zip(_str(df, "NewsStand_"), _str(df, "Street_on"),
                                                   _str(df, "Built_Date"), _str(df, "BoroName"))])
    log.info("newsstands: %d", len(x))
    return cols


def load_bike_shelters(path: Path = OPEN / "bike_shelters.csv") -> dict:
    df = _csv(path, ["the_geom", "shelter_id", "location", "street", "Build_date", "BoroName"])
    lon, lat, ok = _wkt_point_lonlat(_str(df, "the_geom"))
    df = df.filter(ok)
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    cols = _new("bike_shelter", len(x), "bike_shelters")
    cols["x"], cols["y"] = x, y
    cols["text"] = _str(df, "location")
    cols["attrs"] = _attrs([{"shelter_id": i, "location": l, "street": s, "built": b}
                            for i, l, s, b in zip(_str(df, "shelter_id"), _str(df, "location"),
                                                  _str(df, "street"), _str(df, "Build_date"))])
    log.info("bike shelters: %d", len(x))
    return cols


def load_pedestrian_ramps(path: Path = OPEN / "pedestrian_ramps.csv") -> dict:
    """DOT pedestrian ramps (``ufzp-rrqu``). ``RAMP_WIDTH``/``RAMP_LENGTH`` are published in inches."""
    df = _csv(path, ["the_geom", "CornerID", "RampID", "Ramp_OnStreet", "StName1", "StName2",
                     "DWS_CONDITIONS", "RAMP_WIDTH", "RAMP_LENGTH", "RAMP_RUNNING_SLOPE_TOTAL", "Borough"])
    lon, lat, ok = _wkt_point_lonlat(_str(df, "the_geom"))
    df = df.filter(ok)
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    cols = _new("curb_ramp", len(x), "pedestrian_ramps")
    cols["x"], cols["y"] = x, y
    dws = _str(df, "DWS_CONDITIONS")
    # variant 1 = a detectable warning surface (truncated domes) is present and assessed, 0 = none recorded
    cols["variant"] = np.array([0 if (d == "" or d.lower().startswith("no ") or d.lower() == "none") else 1 for d in dws],
                               dtype=np.int16)
    width_in = df["RAMP_WIDTH"].cast(pl.Float64, strict=False).fill_null(0.0).to_numpy()
    length_in = df["RAMP_LENGTH"].cast(pl.Float64, strict=False).fill_null(0.0).to_numpy()
    slope = df["RAMP_RUNNING_SLOPE_TOTAL"].cast(pl.Float64, strict=False).fill_null(float("nan")).to_numpy()
    st1, st2 = _str(df, "StName1"), _str(df, "StName2")
    cols["text"] = [f"{a} / {b}".strip(" /") for a, b in zip(st1, st2)]
    cols["attrs"] = _attrs([{"corner_id": c, "ramp_id": r, "on_street": o, "dws": d,
                             "width_m": round(float(w) * INCH_M, 3) if w > 0 else None,
                             "length_m": round(float(l) * INCH_M, 3) if l > 0 else None,
                             "running_slope_pct": None if not np.isfinite(s) else round(float(s), 2)}
                            for c, r, o, d, w, l, s in zip(_str(df, "CornerID"), _str(df, "RampID"),
                                                           _str(df, "Ramp_OnStreet"), dws, width_in, length_in, slope)])
    log.info("pedestrian ramps: %d", len(x))
    return cols


def load_rtpi_signs(path: Path = OPEN / "rtpi_signs.csv") -> dict:
    df = _csv(path, ["StopName", "Corner", "BusStopID", "Routes", "Direction", "Latitude", "Longitude", "RTPI Complete"])
    lon = df["Longitude"].cast(pl.Float64, strict=False).to_numpy()
    lat = df["Latitude"].cast(pl.Float64, strict=False).to_numpy()
    ok = np.isfinite(lon) & np.isfinite(lat)
    df = df.filter(ok)
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    cols = _new("rtpi_sign", len(x), "rtpi_signs")
    cols["x"], cols["y"] = x, y
    routes = _str(df, "Routes")
    cols["text"] = routes
    cols["attrs"] = _attrs([{"stop_name": s, "corner": c, "bus_stop_id": b, "routes": r, "direction": d, "completed": k}
                            for s, c, b, r, d, k in zip(_str(df, "StopName"), _str(df, "Corner"), _str(df, "BusStopID"),
                                                        routes, _str(df, "Direction"), _str(df, "RTPI Complete"))])
    log.info("rtpi signs: %d", len(x))
    return cols


def load_citibike(path: Path = CITIBIKE) -> dict:
    """Citi Bike stations from the GBFS ``station_information`` snapshot; ``capacity`` is the real dock count."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id citibike_gbfs_stations")
    doc = json.loads(path.read_text())
    stations = doc["data"]["stations"]
    lon = np.array([s.get("lon", np.nan) for s in stations], dtype=np.float64)
    lat = np.array([s.get("lat", np.nan) for s in stations], dtype=np.float64)
    ok = np.isfinite(lon) & np.isfinite(lat)
    stations = [s for s, k in zip(stations, ok) if k]
    x, y = _lonlat_to_tm(lon[ok], lat[ok])
    cols = _new("citibike_dock", len(x), "citibike_gbfs_stations")
    cols["x"], cols["y"] = x, y
    cols["text"] = [str(s.get("name", "")) for s in stations]
    cols["capacity"] = np.array([int(s.get("capacity", 0) or 0) for s in stations], dtype=np.int16)
    cols["attrs"] = _attrs([{"station_id": s.get("station_id", ""), "short_name": s.get("short_name", ""),
                             "region_id": s.get("region_id", ""), "capacity": int(s.get("capacity", 0) or 0)}
                            for s in stations])
    log.info("citi bike stations: %d (last_updated %s)", len(x), doc.get("last_updated"))
    return cols


def load_subway_entrance_props(entrances) -> dict:
    """Prop rows for the MTA subway entrances already normalised by :mod:`..transit.entrances`."""
    n = entrances.height if hasattr(entrances, "height") else len(entrances)
    cols = _new("subway_entrance", n, "subway_entrances")
    cols["x"] = entrances["x"].to_numpy().astype(np.float64)
    cols["y"] = entrances["y"].to_numpy().astype(np.float64)
    kind_variant = {"stair": 0, "escalator": 1, "elevator": 2}
    ent_kind = list(entrances["kind"])
    ent_type = list(entrances["entrance_type"])
    globe = np.asarray(entrances["has_globe"], dtype=np.int8)
    lines = [list(v) for v in entrances["lines"]]
    names = list(entrances["stop_name"])
    variant = np.array([kind_variant.get(k, 0) for k in ent_kind], dtype=np.int16)
    # station house / easement entrances are indoors: variant 3, no globe
    variant[np.array([t.startswith("Easement") or t == "Station House" for t in ent_type])] = 3
    cols["variant"] = variant
    cols["text"] = [f"{nm} — {' '.join(ln)}".strip(" —") for nm, ln in zip(names, lines)]
    cols["attrs"] = _attrs([{"entrance_id": int(i), "station_id": int(s), "complex_id": int(c), "gtfs_stop_id": g,
                             "lines": ln, "entrance_type": t, "has_globe": int(gl), "entry": bool(en), "exit": bool(ex),
                             "division": dv, "line": li}
                            for i, s, c, g, ln, t, gl, en, ex, dv, li in zip(
                                entrances["entrance_id"], entrances["station_id"], entrances["complex_id"],
                                entrances["gtfs_stop_id"], lines, ent_type, globe, entrances["entry_allowed"],
                                entrances["exit_allowed"], entrances["division"], entrances["line"])])
    log.info("subway entrances: %d (globes: %d green, %d red)", n, int((globe == 1).sum()), int((globe == 2).sum()))
    return cols


def load_bus_stop_signs(stops_parquet: Path) -> dict:
    """One MTA bus-stop sign pole per GTFS stop, from ``transit/bus_stops.parquet`` (produced by the transit stage)."""
    if not stops_parquet.exists():
        raise FileNotFoundError(f"{stops_parquet} missing; run `python -m nycsim_pipeline transit` before furniture")
    t = pq.read_table(stops_parquet, columns=["stop_id", "x", "y", "name", "routes", "has_shelter", "feeds"])
    n = t.num_rows
    cols = _new("bus_stop_sign", n, "gtfs_bus")
    cols["x"] = t.column("x").to_numpy(zero_copy_only=False).astype(np.float64)
    cols["y"] = t.column("y").to_numpy(zero_copy_only=False).astype(np.float64)
    names = t.column("name").to_pylist()
    routes = t.column("routes").to_pylist()
    cols["text"] = [str(v or "") for v in names]
    cols["attrs"] = _attrs([{"stop_id": s, "routes": r, "has_shelter": bool(h), "feeds": f}
                            for s, r, h, f in zip(t.column("stop_id").to_pylist(), routes,
                                                  t.column("has_shelter").to_pylist(), t.column("feeds").to_pylist())])
    log.info("bus stop signs: %d", n)
    return cols


# --------------------------------------------------------------------------------------- OSM

# OSM (kind, value) -> prop kind name. Everything the OSM extract carries is mapped; nothing is dropped silently.
OSM_KIND_MAP: dict[tuple[str, str], str] = {
    ("amenity", "bench"): "bench",
    ("amenity", "bicycle_parking"): "bike_rack",
    ("amenity", "waste_basket"): "waste_basket",
    ("amenity", "post_box"): "mailbox",
    ("amenity", "drinking_water"): "drinking_fountain",
    ("amenity", "vending_machine"): "vending_machine",
    ("amenity", "telephone"): "payphone",
    ("highway", "street_lamp"): "street_lamp",
    ("man_made", "flagpole"): "flagpole",
    ("man_made", "utility_pole"): "utility_pole",
    ("man_made", "manhole"): "manhole",
    ("tourism", "artwork"): "artwork",
    ("historic", "memorial"): "memorial",
    ("advertising", "billboard"): "billboard",
}
# ("highway", "bus_stop") is deliberately not mapped: bus stops come from GTFS (kind 24) with their route lists.

BIKE_PARKING_VARIANT = {"stands": 1, "bollard": 1, "wall_loops": 2, "rack": 2, "wide_stands": 1, "anchors": 1,
                        "shed": 3, "lockers": 3, "building": 3, "informal": 0}
#: What the last :func:`load_osm_furniture` call read out of the lamp nodes' tags, by tag,
#: so :mod:`.build` can put the fixture census in the build summary instead of only in a log line.
LAMP_FIXTURE_TALLY: "Counter[str]" = Counter()


def _tags(raw: str) -> dict:
    """One node's ``tags`` column as a dict; a malformed or absent value is an empty one."""
    try:
        t = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return t if isinstance(t, dict) else {}


#: OSM ``lamp_mount`` / ``light:mount`` value -> ``street_lamp`` variant code.
#:
#: This is the tag that says what the fixture *is*.  The lookup it replaces searched the ``support``
#: and ``subtype`` columns for the words "cobra", "bishop", "historic" and "pedestrian"; measured
#: against the extract, not one of those four strings occurs on any of the 16,971 OSM lamp nodes, so
#: every one of them fell through to 0 (docs/DEVIATIONS.md J56).  ``lamp_type`` was the wrong column
#: to read as well: its values are ``led`` / ``electric`` / ``fluorescent``, the light *source*, not
#: the mast.
#:
#: A mast arm of any bend is the DOT davit -- OSM has no tag anywhere in this extract that tells a
#: Bishop's Crook from a cobra head, so variant 2 is placed nowhere and that is recorded rather than
#: guessed at.
LAMP_MOUNT_VARIANT = {
    "bent_mast": 1, "straight_mast": 1, "angled_mast": 1, "mast_arm": 1, "mast": 1,
    "high_mast": 4,
    "lamppost": 3, "post_top": 3, "pole_top": 3,
}

#: ``lamp_mount`` values that name a fixture the prop catalogue has no mesh for: a light in the
#: ground, on a bollard, on a wall, hung from a catenary.  They are counted in the build summary and
#: left at variant 0, which the asset resolver turns into the kind's default pole -- a substitution,
#: recorded as one.
LAMP_MOUNT_NO_ASSET = ("ground", "grounded", "ground1", "ground_t", "bollard", "wall",
                       "suspended", "catenary", "ceiling", "bridge")

#: ``light_source`` value that implies a post-top lantern where no mount is tagged.
LAMP_SOURCE_VARIANT = {"lantern": 3}


def lamp_variant(tags: dict) -> tuple[int, str]:
    """``(variant code, the tag it came from)`` for one OSM ``highway=street_lamp`` node.

    ``""`` as the second element means nothing in the node's tags describes the fixture, and the
    row keeps variant 0 for the resolver's default to pick up.
    """
    for key in ("lamp_mount", "light:mount"):
        raw = str(tags.get(key) or "").strip().lower()
        if not raw:
            continue
        v = LAMP_MOUNT_VARIANT.get(raw)
        if v is not None:
            return v, f"{key}={raw}"
        if raw in LAMP_MOUNT_NO_ASSET:
            return 0, f"no_asset:{key}={raw}"
    src = str(tags.get("light_source") or "").strip().lower()
    v = LAMP_SOURCE_VARIANT.get(src)
    if v is not None:
        return v, f"light_source={src}"
    return 0, ""


def load_osm_furniture(path: Path = OSM_FURNITURE) -> dict:
    """Street furniture nodes from the OSM extract (``street_furniture_osm.parquet``, ODbL)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline osm")
    t = pq.read_table(path)
    df = pl.from_arrow(t)
    key = list(zip(df["kind"].fill_null("").to_list(), df["value"].fill_null("").to_list()))
    mapped = np.array([OSM_KIND_MAP.get(k, "") for k in key], dtype=object)
    unmapped = sorted({k for k, m in zip(key, mapped) if not m})
    if unmapped:
        log.info("osm furniture: %d tag combinations not mapped to a prop kind: %s", len(unmapped), unmapped)
    out = []
    x_all = df["x"].to_numpy().astype(np.float64)
    y_all = df["y"].to_numpy().astype(np.float64)
    direction = df["direction"].to_numpy().astype(np.float64)
    capacity = df["capacity"].fill_null(0).to_numpy().astype(np.int32)
    height = df["height_m"].to_numpy().astype(np.float64)
    name = df["name"].fill_null("").to_list()
    subtype = df["subtype"].fill_null("").to_list()
    support = df["support"].fill_null("").to_list()
    backrest = df["backrest"].fill_null("").to_list()
    material = df["material"].fill_null("").to_list()
    operator = df["operator"].fill_null("").to_list()
    ref = df["ref"].fill_null("").to_list()
    raw_tags = df["tags"].fill_null("{}").to_list() if "tags" in df.columns else ["{}"] * len(df)
    osm_id = df["osm_id"].to_numpy()
    for kind_name in sorted(set(m for m in mapped if m)):
        idx = np.flatnonzero(mapped == kind_name)
        cols = _new(kind_name, idx.size, "osm_newyork_pbf")
        cols["x"], cols["y"] = x_all[idx], y_all[idx]
        d = direction[idx]
        cols["heading"] = np.where(np.isfinite(d) & (d >= 0) & (d <= 360), d, np.nan).astype(np.float32)
        h = height[idx]
        real_h = np.isfinite(h) & (h > 0)
        if real_h.any():
            hm = np.asarray(cols["height_m"], dtype=np.float32).copy()
            hs = np.asarray(cols["height_source"], dtype=np.int8).copy()
            hm[real_h] = h[real_h].astype(np.float32)
            hs[real_h] = HEIGHT_SOURCE["measured"]
            cols["height_m"], cols["height_source"] = hm, hs
        if kind_name == "bike_rack":
            cols["capacity"] = np.clip(capacity[idx], 0, 32767).astype(np.int16)
            cols["variant"] = np.array([BIKE_PARKING_VARIANT.get(subtype[i], 0) for i in idx], dtype=np.int16)
        elif kind_name == "street_lamp":
            got = [lamp_variant(_tags(raw_tags[i])) for i in idx]
            cols["variant"] = np.array([v for v, _ in got], dtype=np.int16)
            seen: Counter[str] = Counter(why or "untagged" for _, why in got)
            log.info("osm street_lamp fixtures: %s", dict(sorted(seen.items())))
            LAMP_FIXTURE_TALLY.clear()
            LAMP_FIXTURE_TALLY.update(seen)
        elif kind_name == "bench":
            cols["variant"] = np.array([1 if backrest[i] == "yes" else (2 if backrest[i] == "no" else 0) for i in idx],
                                       dtype=np.int16)
        cols["text"] = [name[i] or subtype[i] for i in idx]
        cols["attrs"] = _attrs([{"osm_id": int(osm_id[i]), "subtype": subtype[i], "operator": operator[i],
                                 "ref": ref[i], "material": material[i], "support": support[i]} for i in idx])
        out.append(cols)
        log.info("osm %s: %d", kind_name, idx.size)
    return _concat(out)


def load_osm_trees(path: Path = OSM_TREES, *, heights: "CensusHeights") -> dict:
    """``natural=tree`` nodes from the OSM extract (:mod:`..osm.trees`, ODbL) as tree props (kind 0).

    These are the park trees the 2015 census cannot have: it is a *street* inventory, so 1,756 of the city's
    1,916 green polygons of 2 ha or more hold no census tree at all (DEVIATIONS D10). They carry the same
    ``kind`` as the census trees and are told apart by ``dataset_id``; the duplicates the two sources share
    are removed by the cross-source rule in :mod:`.dedupe`, not here.

    What is taken from OSM and what is not:

    * ``species`` is set only from the ``species`` tag, or from ``taxon`` when that is a binomial. A ``genus``
      alone is not a species and is left out of the column (it goes to ``attrs`` and is used for the height
      curve, whose own lookup falls back to the genus).
    * ``height_m`` comes from the ``height`` tag where it parses (``height_source`` 0, measured/tagged). Where
      it does not — 98.4 % of nodes — it is a deterministic draw from the census's own height distribution,
      conditioned on the taxon wherever OSM names one and seeded by the tree's coordinates
      (``height_source`` 4; :class:`..furniture.trees.CensusHeights` argues the choice). The census's
      unknown-DBH sapling fallback is deliberately *not* reused: a missing DBH in the census usually means a
      newly planted tree, but a missing ``height`` tag in OSM means only that nobody measured one, so carrying
      the fallback across would assert "small" 49,000 times where the source says nothing.
    * ``dbh_cm`` is 0 — absent — for every row, and nothing is derived backwards from the drawn height. OSM
      has no DBH tag; see :mod:`..osm.trees` for why ``circumference`` and ``diameter`` are carried raw.
    * ``variant`` is 3, the catalog's "health unknown": OSM records no condition.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.osm.trees")
    t = pq.read_table(path, columns=["osm_id", "x", "y", "species", "genus", "taxon", "leaf_type", "leaf_cycle",
                                     "denotation", "name", "ref", "start_date", "operator", "height_m",
                                     "height_raw", "circumference_raw", "diameter_crown_raw", "diameter_raw"])
    df = pl.from_arrow(t)
    n = df.height
    cols = _new("tree", n, "osm_newyork_pbf")
    cols["x"] = df["x"].to_numpy().astype(np.float64)
    cols["y"] = df["y"].to_numpy().astype(np.float64)
    cols["dbh_cm"] = np.zeros(n, dtype=np.float32)          # 0 = the source records no trunk diameter
    cols["variant"] = np.full(n, TREE_HEALTH_UNKNOWN, dtype=np.int16)

    species = _str(df, "species")
    genus = _str(df, "genus")
    taxon = _str(df, "taxon")
    # a taxon that names a species (a binomial) is a species; a taxon that names only a genus is not
    species = [s or (tx if " " in tx else "") for s, tx in zip(species, taxon)]
    cols["species"] = species
    # the height curve may use the genus even where the species column stays empty
    lookup = [s or g for s, g in zip(species, genus)]

    tagged = df["height_m"].to_numpy().astype(np.float64) if n else np.zeros(0)
    ok = np.isfinite(tagged) & (tagged > 0)
    height, from_taxon = heights.draw(cols["x"], cols["y"], lookup)
    height[ok] = tagged[ok]
    cols["height_m"] = height.astype(np.float32)
    cols["height_source"] = np.where(ok, HEIGHT_SOURCE["measured"], HEIGHT_SOURCE["census_distribution"]).astype(np.int8)

    name = _str(df, "name")
    cols["text"] = name
    osm_id = df["osm_id"].to_numpy()
    height_raw = _str(df, "height_raw")
    cols["attrs"] = _attrs([{"osm_id": int(osm_id[i]), "genus": genus[i], "taxon": taxon[i],
                             "leaf_type": lt, "leaf_cycle": lc, "denotation": dn, "ref": rf, "operator": op,
                             "start_date": sd, "circumference": ci, "diameter_crown": dc, "diameter": di,
                             "height_tag_unparsed": ("" if (ok[i] or not height_raw[i]) else height_raw[i])}
                            for i, (lt, lc, dn, rf, op, sd, ci, dc, di) in enumerate(zip(
                                _str(df, "leaf_type"), _str(df, "leaf_cycle"), _str(df, "denotation"),
                                _str(df, "ref"), _str(df, "operator"), _str(df, "start_date"),
                                _str(df, "circumference_raw"), _str(df, "diameter_crown_raw"),
                                _str(df, "diameter_raw")))])
    log.info("osm trees: %d (%d with a usable height tag, %d with a species, %d drawn from a taxon-specific "
             "census pool, %d from the whole census population)", n, int(ok.sum()), sum(1 for s in species if s),
             int((from_taxon & ~ok).sum()), int((~from_taxon & ~ok).sum()))
    cols["_height_from_taxon_pool"] = from_taxon & ~ok
    return cols


# --------------------------------------------------------------------------------------- polygon datasets

def load_parks_structures(path: Path = OPEN / "parks_structures.csv") -> dict:
    """NYC Parks structures (``n8q6-i44s``): comfort stations, recreation centres and other Parks buildings.

    ``Height_Roof`` is the roof height above grade in feet and ``Ground_Elevation`` the grade in feet (the
    planimetric convention); both become metres. Only ``FeatureStatus = Active`` structures with no demolition
    year are placed.
    """
    df = _csv(path, ["multipolygon", "DESCRIPTION", "BIN", "BOROUGH", "Public Restroom", "Recreation_Center",
                     "Height_Roof", "Ground_Elevation", "Construction_Year", "FeatureStatus", "Demolition_Year",
                     "GISPROPNUM", "LOCATION", "SYSTEM"])
    status = np.asarray(_str(df, "FeatureStatus"))
    demo = np.asarray(_str(df, "Demolition_Year"))
    keep = (status == "Active") & (demo == "")
    log.info("parks structures: %d rows, %d active and not demolished", df.height, int(keep.sum()))
    df = df.filter(keep)
    geoms = shapely.from_wkt(_str(df, "multipolygon"))
    ok = np.array([g is not None and not g.is_empty for g in geoms])
    df = df.filter(ok)
    geoms = np.asarray([g for g, k in zip(geoms, ok) if k], dtype=object)
    tr = transformer("WGS84", "NYC_TM")
    geoms = shapely.transform(geoms, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
    cx, cy, area, w, d, head = _footprint_metrics(geoms)

    restroom = np.array([v.lower() == "true" for v in _str(df, "Public Restroom")])
    rec = np.array([v.lower() == "true" for v in _str(df, "Recreation_Center")])
    roof_ft = df["Height_Roof"].cast(pl.Float64, strict=False).to_numpy()
    grade_ft = df["Ground_Elevation"].cast(pl.Float64, strict=False).to_numpy()
    desc = _str(df, "DESCRIPTION")
    out = []
    for kind_name, mask in (("parks_comfort_station", restroom),
                            ("parks_recreation_center", rec & ~restroom),
                            ("parks_building", ~restroom & ~rec)):
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            continue
        cols = _new(kind_name, idx.size, "parks_structures")
        cols["x"], cols["y"] = cx[idx], cy[idx]
        cols["heading"] = head[idx].astype(np.float32)
        h = roof_ft[idx] * US_SURVEY_FOOT_M
        good_h = np.isfinite(h) & (h > 0)
        cols["height_m"] = np.where(good_h, h, np.nan).astype(np.float32)
        cols["height_source"] = np.where(good_h, HEIGHT_SOURCE["measured"], HEIGHT_SOURCE["none"]).astype(np.int8)
        gz = grade_ft[idx] * US_SURVEY_FOOT_M
        good_z = np.isfinite(gz)
        cols["z"] = np.where(good_z, gz, np.nan).astype(np.float32)
        cols["z_source"] = np.where(good_z, 1, 2).astype(np.int8)   # 1 = dataset elevation
        cols["text"] = [desc[i] for i in idx]
        cols["attrs"] = _attrs([{"bin": b, "gispropnum": g, "system": s, "location": l, "built": y,
                                 "area_m2": round(float(area[i]), 1), "footprint_w": round(float(w[i]), 2),
                                 "footprint_d": round(float(d[i]), 2)}
                                for i, b, g, s, l, y in zip(idx, [_str(df, "BIN")[i] for i in idx],
                                                            [_str(df, "GISPROPNUM")[i] for i in idx],
                                                            [_str(df, "SYSTEM")[i] for i in idx],
                                                            [_str(df, "LOCATION")[i] for i in idx],
                                                            [_str(df, "Construction_Year")[i] for i in idx])])
        out.append(cols)
        log.info("parks %s: %d", kind_name, idx.size)
    return _concat(out)


def _polygon_props(path: Path, kind_name: str, dataset_id: str, columns: list[str],
                   where: dict[str, tuple[str, ...]] | None = None, text_col: str | None = None,
                   height_m: float | None = None) -> dict:
    geoms, attrs = _polygon_layer(path, columns, where)
    if len(geoms) == 0:
        return _new(kind_name, 0, dataset_id)
    cx, cy, area, w, d, head = _footprint_metrics(geoms)
    cols = _new(kind_name, len(geoms), dataset_id)
    cols["x"], cols["y"] = cx, cy
    cols["heading"] = head.astype(np.float32)
    if height_m is not None:
        cols["height_m"] = np.full(len(geoms), height_m, dtype=np.float32)
        cols["height_source"] = np.full(len(geoms), HEIGHT_SOURCE["nominal"], dtype=np.int8)
    if text_col:
        cols["text"] = [str(v or "") for v in attrs[text_col]]
    cols["attrs"] = _attrs([{**{c: (str(attrs[c][i]) if attrs[c][i] is not None else "") for c in columns},
                             "area_m2": round(float(area[i]), 2), "footprint_w": round(float(w[i]), 2),
                             "footprint_d": round(float(d[i]), 2)} for i in range(len(geoms))])
    log.info("%s: %d", kind_name, len(geoms))
    return cols


def load_cooling_towers(path: Path = OPEN / "plan_cooling_towers.geojson") -> dict:
    """Planimetric cooling towers (``x748-37q7``); only units > 4 ft across were captured. ``sub_featur`` says
    roof level vs ground level and ``bin`` names the building underneath."""
    return _polygon_props(path, "cooling_tower", "plan_cooling_towers", ["feature_co", "sub_featur", "source_id", "bin"],
                          height_m=3.0)


def load_swimming_pools(path: Path = OPEN / "plan_swimming_pools.geojson") -> dict:
    return _polygon_props(path, "swimming_pool", "plan_swimming_pools", ["feat_code", "sub_code", "source_id"])


def load_misc_structures(path: Path = OPEN / "plan_misc_structures.geojson") -> dict:
    return _polygon_props(path, "misc_structure", "plan_misc_structures", ["feat_code", "sub_code", "source_id"],
                          text_col="sub_code")


def load_subway_vent_structures(path: Path = OPEN / "plan_railroad_structure.geojson") -> dict:
    """Ventilation grates (2470) and emergency exits (2480) from the planimetric Railroad Structure layer.

    Transit entrances (2485) in the same layer are *not* imported: they are the same physical objects as the MTA
    ``subway_entrances`` records (kind 8), which additionally carry the served lines and the globe colour.
    """
    out = []
    for code, kind_name in (("2470", "subway_vent_grate"), ("2480", "subway_emergency_exit")):
        cols = _polygon_props(path, kind_name, "plan_railroad_structure",
                              ["feat_code", "sub_code", "source_id"], where={"feat_code": (code,)}, height_m=0.05)
        out.append(cols)
    return _concat(out)


# --------------------------------------------------------------------------------------- concat

def _concat(parts: list[dict]) -> dict:
    parts = [p for p in parts if len(p["x"]) or len(p["kind"])]
    if not parts:
        return empty_columns(0)
    out: dict = {}
    for name, _t in FIELDS:
        vals = [p[name] for p in parts]
        if isinstance(vals[0], list):
            merged: list = []
            for v in vals:
                merged.extend(v)
            out[name] = merged
        else:
            out[name] = np.concatenate(vals)
    return out


def concat(parts: list[dict]) -> dict:
    """Concatenate prop column dicts produced by the loaders."""
    return _concat(parts)
