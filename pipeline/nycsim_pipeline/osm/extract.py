"""OSM extraction (stage ``osm``): BBBike New York ``.osm.pbf`` -> ``data/processed/osm/*.parquet``.

Layers (all coordinates NYC_TM metres, geometry as WKB, GeoParquet metadata, ``nycsim.schema`` key):

* ``buildings.parquet``          building areas (closed ways + multipolygon relations) east of the NY–NJ state line
* ``buildings_nj.parquet``       the same west of the state line (New Jersey side, skyline only)
* ``pois.parquet``               shop / amenity / tourism / office / craft / healthcare / leisure points (nodes and area centroids)
* ``signals_stops.parquet``      highway=traffic_signals / stop / give_way / crossing nodes with all tags
* ``restrictions.parquet``       type=restriction relations with from/via/to ids and approach/exit coordinates
* ``rail.parquet``               railway lines (rail, subway, light_rail, tram, monorail, narrow_gauge) with ``is_elevated``
* ``water_nj.parquet``           water areas that touch the New Jersey side (Hudson, Upper Bay, Newark Bay, Hackensack, ...)
* ``landuse_leisure.parquet``    parks, playgrounds, pitches, gardens, cemeteries, woods, grass ...
* ``street_furniture_osm.parquet`` benches, waste baskets, post boxes, bicycle parking, street lamps, bus stops, manholes, ...

``osm_id`` convention: positive = way / node id, negative = relation id (osm2pgsql convention) so one int64 is
unique per layer; ``osm_type`` is also stored. Data © OpenStreetMap contributors, ODbL 1.0.

Run: ``python -m nycsim_pipeline osm [--pbf PATH] [--out DIR] [--bbox LON0 LAT0 LON1 LAT1]``
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import osmium
import pyarrow as pa
import shapely
from shapely.geometry import Polygon

from ..crs import SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, lonlat_to_tm, tm_to_lonlat
from ..manifest import record_processed
from ..paths import PROCESSED, RAW
from .geoparquet import ParquetBatchWriter

log = logging.getLogger("nycsim.osm")

PBF_DEFAULT = RAW / "osm" / "NewYork.osm.pbf"
OUT_DEFAULT = PROCESSED / "osm"
SOURCE_ID = "osm_newyork_pbf"
LICENSE = "ODbL 1.0, © OpenStreetMap contributors"
BATCH = 50_000

# --------------------------------------------------------------------------- NY / NJ state line
# The BBBike extract carries no admin boundaries (only one admin_level=4 way, offshore), so the NY–NJ line is
# digitised here as the mid-channel of the Hudson River, Upper Bay, Kill Van Kull, Arthur Kill and Raritan Bay
# (north -> south, WGS84 lon/lat). Validation against the extract's own ``addr:state`` tags (see ``extract_summary.json``):
# 20,337 / 20,341 addr:state=NJ nodes fall west of the line, 0 / 88,144 addr:state=NY nodes fall west of it.
# Liberty Island and Ellis Island (NY exclaves inside NJ waters under the 1834 compact) are carved out as NY.
NY_NJ_STATE_LINE_LONLAT: tuple[tuple[float, float], ...] = (
    (-73.895, 41.00), (-73.900, 40.99), (-73.913, 40.94), (-73.937, 40.89), (-73.957, 40.851), (-73.968, 40.82),
    (-73.990, 40.795), (-74.001, 40.78), (-74.011, 40.76), (-74.018, 40.748), (-74.021, 40.73), (-74.025, 40.712),
    (-74.030, 40.70), (-74.035, 40.69), (-74.050, 40.67), (-74.057, 40.655), (-74.075, 40.649), (-74.090, 40.647),
    (-74.120, 40.6445), (-74.140, 40.6415), (-74.158, 40.642), (-74.168, 40.640), (-74.178, 40.636), (-74.190, 40.625),
    (-74.200, 40.61), (-74.212, 40.59), (-74.222, 40.575), (-74.235, 40.555), (-74.245, 40.535), (-74.250, 40.522),
    (-74.255, 40.505), (-74.220, 40.49), (-74.150, 40.47), (-74.050, 40.455), (-73.980, 40.45), (-73.950, 40.44),
)
NY_EXCLAVES_LONLAT = {
    "Liberty Island": (-74.049, 40.6865, -74.040, 40.6925),
    "Ellis Island": (-74.0445, 40.6965, -74.036, 40.7015),
}


def nj_region_lonlat() -> Polygon:
    """Polygon (WGS84) covering everything west of the NY–NJ state line inside the extract."""
    poly = Polygon(list(NY_NJ_STATE_LINE_LONLAT) + [(-75.0, 40.44), (-75.0, 41.0)])
    for box in NY_EXCLAVES_LONLAT.values():
        poly = poly.difference(shapely.box(*box))
    if not poly.is_valid:
        raise RuntimeError("NJ region polygon invalid")
    return poly


def scope_lonlat_bbox(margin_deg: float = 0.003) -> tuple[float, float, float, float]:
    """Generous lon/lat envelope of the NYC_TM scope box (exact filtering happens in TM later)."""
    xs = np.array([SCOPE_XMIN, SCOPE_XMAX, SCOPE_XMIN, SCOPE_XMAX, 0.0, 0.0, SCOPE_XMIN, SCOPE_XMAX])
    ys = np.array([SCOPE_YMIN, SCOPE_YMIN, SCOPE_YMAX, SCOPE_YMAX, SCOPE_YMIN, SCOPE_YMAX, 0.0, 0.0])
    lon, lat = tm_to_lonlat(xs, ys)
    return float(lon.min() - margin_deg), float(lat.min() - margin_deg), float(lon.max() + margin_deg), float(lat.max() + margin_deg)


# --------------------------------------------------------------------------- tag parsing
_NUM = r"(-?\d+(?:[.,]\d+)?)"
_RE_M = re.compile(rf"^\s*{_NUM}\s*(?:m|meters?|metres?)?\s*$", re.I)
_RE_FT = re.compile(rf"^\s*{_NUM}\s*(?:ft|feet|foot|')\s*(?:{_NUM}\s*(?:in|\"|''))?\s*$", re.I)
_RE_IN = re.compile(rf"^\s*{_NUM}\s*(?:in|\")\s*$", re.I)


def parse_length_m(value: str | None) -> float:
    """'25', '25 m', '80 ft', "80'6\"" -> metres; NaN when absent or unparsable."""
    if not value:
        return math.nan
    v = value.strip().replace(",", ".")
    m = _RE_M.match(v)
    if m:
        return float(m.group(1))
    m = _RE_FT.match(v)
    if m:
        ft = float(m.group(1))
        inch = float(m.group(2)) if m.group(2) else 0.0
        return (ft + inch / 12.0) * 0.3048
    m = _RE_IN.match(v)
    if m:
        return float(m.group(1)) * 0.0254
    return math.nan


def parse_float(value: str | None) -> float:
    if not value:
        return math.nan
    v = value.strip().replace(",", ".")
    try:
        return float(v)
    except ValueError:
        m = re.match(_NUM, v)
        return float(m.group(1)) if m else math.nan


def parse_int(value: str | None, default: int = 0) -> int:
    if not value:
        return default
    try:
        return int(float(value.strip().replace(",", ".").split(";")[0]))
    except ValueError:
        return default


def parse_direction_deg(value: str | None) -> float:
    """Compass heading from OSM ``direction`` (degrees or cardinal like 'NE'); NaN if absent."""
    if not value:
        return math.nan
    v = value.strip().upper().split(";")[0]
    cardinal = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180,
                "SSW": 202.5, "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}
    if v in cardinal:
        return float(cardinal[v])
    try:
        return float(v) % 360.0
    except ValueError:
        return math.nan


def truthy(value: str | None) -> bool:
    return bool(value) and value.strip().lower() not in ("no", "false", "0", "none")


# --------------------------------------------------------------------------- tag sets
RAIL_KINDS = frozenset({"rail", "subway", "light_rail", "tram", "monorail", "narrow_gauge"})
ELEVATED_RAIL = frozenset({"subway", "rail", "light_rail"})
SIGNAL_KINDS = frozenset({"traffic_signals", "stop", "give_way", "crossing"})
POI_KEYS = ("shop", "amenity", "tourism", "office", "craft", "healthcare", "leisure")
FURNITURE_TAGS: dict[str, frozenset[str]] = {
    "amenity": frozenset({"bench", "waste_basket", "post_box", "telephone", "bicycle_parking", "drinking_water", "vending_machine"}),
    "highway": frozenset({"street_lamp", "bus_stop"}),
    "man_made": frozenset({"manhole", "utility_pole", "flagpole"}),
    "tourism": frozenset({"artwork"}),
    "historic": frozenset({"memorial"}),
    "advertising": frozenset({"billboard"}),
}
FURNITURE_SUBTYPE_KEY = {"bicycle_parking": "bicycle_parking", "artwork": "artwork_type", "memorial": "memorial",
                         "street_lamp": "lamp_type", "manhole": "manhole", "vending_machine": "vending",
                         "post_box": "post_box:type", "bench": "bench:type", "bus_stop": "shelter", "waste_basket": "waste",
                         "billboard": "billboard:type", "flagpole": "flag:type", "utility_pole": "utility", "telephone": "telephone_kind",
                         "drinking_water": "fountain"}
POI_EXCLUDE_AMENITY = FURNITURE_TAGS["amenity"] | {"parking_space"}
LANDUSE_LEISURE: dict[str, frozenset[str]] = {
    "leisure": frozenset({"park", "playground", "pitch", "garden", "dog_park", "golf_course", "nature_reserve", "track",
                          "recreation_ground", "common", "sports_centre", "stadium", "swimming_pool", "marina", "beach_resort",
                          "miniature_golf", "picnic_table", "outdoor_seating", "bleachers", "fitness_station", "water_park"}),
    "landuse": frozenset({"cemetery", "grass", "recreation_ground", "forest", "village_green", "meadow", "allotments", "greenfield",
                          "flowerbed", "plant_nursery", "orchard", "farmland"}),
    "natural": frozenset({"wood", "scrub", "grassland", "wetland", "beach", "sand", "heath", "shrubbery", "tree_row"}),
}
WATER_TAGS: dict[str, frozenset[str] | None] = {"natural": frozenset({"water", "bay", "strait"}), "waterway": frozenset({"riverbank", "dock", "boatyard"}),
                                                 "landuse": frozenset({"reservoir", "basin", "salt_pond"})}

# --------------------------------------------------------------------------- schemas
S = pa.string()
F32, F64, I64, I32, I8, B = pa.float32(), pa.float64(), pa.int64(), pa.int32(), pa.int8(), pa.bool_()

BUILDING_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("geometry", pa.binary()), ("name", S), ("building", S),
                             ("material", S), ("colour", S), ("levels", F32), ("height", F32), ("min_height", F32), ("roof_shape", S),
                             ("roof_material", S), ("roof_colour", S), ("roof_levels", F32), ("amenity", S), ("shop", S),
                             ("addr_housenumber", S), ("addr_street", S), ("addr_state", S), ("start_date", S), ("cx", F64), ("cy", F64)])
POI_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("x", F64), ("y", F64), ("name", S), ("kind", S), ("value", S), ("brand", S),
                        ("opening_hours", S), ("level", S), ("cuisine", S), ("addr_housenumber", S), ("addr_street", S), ("operator", S)])
SIGNAL_SCHEMA = pa.schema([("node_id", I64), ("x", F64), ("y", F64), ("kind", S), ("tags", S)])
RESTRICTION_SCHEMA = pa.schema([("relation_id", I64), ("from_way", I64), ("via_node", I64), ("via_way", I64), ("to_way", I64),
                                ("restriction", S), ("restriction_key", S), ("except", S), ("via_x", F64), ("via_y", F64),
                                ("from_x", F64), ("from_y", F64), ("to_x", F64), ("to_y", F64), ("valid", B)])
RAIL_SCHEMA = pa.schema([("osm_id", I64), ("geometry", pa.binary()), ("railway", S), ("bridge", S), ("tunnel", S), ("layer", I8),
                         ("name", S), ("service", S), ("operator", S), ("is_elevated", B), ("embankment", B), ("cutting", B),
                         ("usage", S), ("gauge", S), ("electrified", S), ("tracks", I8), ("length_m", F32)])
WATER_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("geometry", pa.binary()), ("kind", S), ("value", S), ("name", S),
                          ("water", S), ("tidal", B), ("intermittent", B), ("area_m2", F64)])
LANDUSE_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("geometry", pa.binary()), ("kind", S), ("value", S), ("name", S),
                            ("surface", S), ("sport", S), ("operator", S), ("access", S), ("leaf_type", S), ("area_m2", F64)])
FURNITURE_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("x", F64), ("y", F64), ("kind", S), ("value", S), ("name", S),
                              ("direction", F32), ("capacity", I32), ("subtype", S), ("material", S), ("colour", S), ("operator", S),
                              ("ref", S), ("backrest", S), ("support", S), ("height_m", F32), ("tags", S)])

_TO_TM = None


def _to_tm(coords: np.ndarray) -> np.ndarray:
    x, y = lonlat_to_tm(coords[:, 0], coords[:, 1])
    return np.column_stack([x, y])


def _in_scope_tm(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return (x >= SCOPE_XMIN) & (x <= SCOPE_XMAX) & (y >= SCOPE_YMIN) & (y <= SCOPE_YMAX)


# --------------------------------------------------------------------------- buffered layers
@dataclass
class Buffer:
    """Column buffer for one layer; ``flush`` transforms geometry and hands rows to the writer."""
    name: str
    schema: pa.Schema
    finalize: Callable[["Buffer", dict[str, list]], dict[str, list] | None]
    writers: dict[str, ParquetBatchWriter]
    cols: dict[str, list] = field(default_factory=dict)
    n: int = 0
    dropped: int = 0

    def __post_init__(self) -> None:
        self.cols = {k: [] for k in self.schema.names}
        self.cols["_lon"] = []
        self.cols["_lat"] = []

    def add(self, row: dict[str, Any], lon: float, lat: float) -> None:
        for k in self.schema.names:
            self.cols[k].append(row.get(k))
        self.cols["_lon"].append(lon)
        self.cols["_lat"].append(lat)
        self.n += 1
        if self.n >= BATCH:
            self.flush()

    def flush(self) -> None:
        if not self.n:
            return
        cols = self.cols
        self.cols = {k: [] for k in cols}
        self.n = 0
        before = len(cols["_lon"])
        out = self.finalize(self, cols)
        if out is None:
            self.dropped += before
            return
        written = 0
        for target, c in out.items():
            written += self.writers[target].write(c)
        self.dropped += before - written


def _select(cols: dict[str, list], keep: np.ndarray, names: list[str]) -> dict[str, Any]:
    idx = np.nonzero(keep)[0]
    return {k: [cols[k][i] for i in idx] for k in names}


class Extractor:
    def __init__(self, pbf: Path, out: Path, bbox_lonlat: tuple[float, float, float, float] | None = None) -> None:
        self.pbf = Path(pbf)
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.bbox = bbox_lonlat or scope_lonlat_bbox()
        self.nj_poly = nj_region_lonlat()
        shapely.prepare(self.nj_poly)
        self.wkbf = osmium.geom.WKBFactory()
        self.counts: dict[str, int] = {}
        self.geom_errors = 0
        self.state_check = {"nj_tagged": 0, "nj_tagged_west": 0, "ny_tagged": 0, "ny_tagged_west": 0}
        self.timings: dict[str, float] = {}
        # restriction bookkeeping
        self.restrictions: list[dict[str, Any]] = []
        self.needed_ways: set[int] = set()
        self.way_nodes: dict[int, list[int]] = {}
        self.node_store = None
        self.writers: dict[str, ParquetBatchWriter] = {}
        self.buffers: dict[str, Buffer] = {}
        self._make_layers()

    # ---- layers
    def _writer(self, name: str, schema: pa.Schema, geometry: str | None) -> ParquetBatchWriter:
        w = ParquetBatchWriter(self.out / f"{name}.parquet", schema, schema_name=f"nycsim.osm.{name}.v1", geometry_column=geometry,
                               extra_metadata={"nycsim.license": LICENSE, "nycsim.source": SOURCE_ID})
        self.writers[name] = w
        return w

    def _make_layers(self) -> None:
        for name, schema, geom in [("buildings", BUILDING_SCHEMA, "geometry"), ("buildings_nj", BUILDING_SCHEMA, "geometry"),
                                   ("pois", POI_SCHEMA, None), ("signals_stops", SIGNAL_SCHEMA, None),
                                   ("restrictions", RESTRICTION_SCHEMA, None), ("rail", RAIL_SCHEMA, "geometry"),
                                   ("water_nj", WATER_SCHEMA, "geometry"), ("landuse_leisure", LANDUSE_SCHEMA, "geometry"),
                                   ("street_furniture_osm", FURNITURE_SCHEMA, None)]:
            self._writer(name, schema, geom)
        self.buffers["buildings"] = Buffer("buildings", BUILDING_SCHEMA, self._fin_buildings, self.writers)
        self.buffers["pois"] = Buffer("pois", POI_SCHEMA, self._fin_points("pois"), self.writers)
        self.buffers["signals_stops"] = Buffer("signals_stops", SIGNAL_SCHEMA, self._fin_points("signals_stops"), self.writers)
        self.buffers["rail"] = Buffer("rail", RAIL_SCHEMA, self._fin_lines, self.writers)
        self.buffers["water_nj"] = Buffer("water_nj", WATER_SCHEMA, self._fin_water, self.writers)
        self.buffers["landuse_leisure"] = Buffer("landuse_leisure", LANDUSE_SCHEMA, self._fin_areas("landuse_leisure"), self.writers)
        self.buffers["street_furniture_osm"] = Buffer("street_furniture_osm", FURNITURE_SCHEMA, self._fin_points("street_furniture_osm"), self.writers)

    # ---- finalizers (batch geometry transform + scope filter)
    def _fin_points(self, target: str) -> Callable:
        def fin(buf: Buffer, cols: dict[str, list]) -> dict[str, dict] | None:
            x, y = lonlat_to_tm(np.asarray(cols["_lon"], dtype=float), np.asarray(cols["_lat"], dtype=float))
            keep = _in_scope_tm(x, y)
            if not keep.any():
                return None
            out = _select(cols, keep, [n for n in buf.schema.names if n not in ("x", "y")])
            out["x"] = x[keep]
            out["y"] = y[keep]
            return {target: out}
        return fin

    def _geoms_tm(self, cols: dict[str, list]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        g_ll = shapely.from_wkb(cols["geometry"], on_invalid="ignore")
        ok = ~shapely.is_missing(g_ll) & ~shapely.is_empty(g_ll)
        g_ll = np.where(ok, g_ll, shapely.from_wkt("POINT EMPTY"))
        g_tm = shapely.transform(g_ll, _to_tm)
        c = shapely.centroid(g_tm)
        cx, cy = shapely.get_x(c), shapely.get_y(c)
        keep = ok & np.isfinite(cx) & _in_scope_tm(np.nan_to_num(cx, nan=1e12), np.nan_to_num(cy, nan=1e12))
        return g_ll, g_tm, keep

    def _fin_areas(self, target: str) -> Callable:
        def fin(buf: Buffer, cols: dict[str, list]) -> dict[str, dict] | None:
            _, g_tm, keep = self._geoms_tm(cols)
            if not keep.any():
                return None
            out = _select(cols, keep, [n for n in buf.schema.names if n not in ("geometry", "area_m2")])
            out["geometry"] = shapely.to_wkb(g_tm[keep])
            out["area_m2"] = shapely.area(g_tm[keep])
            return {target: out}
        return fin

    def _fin_lines(self, buf: Buffer, cols: dict[str, list]) -> dict[str, dict] | None:
        _, g_tm, keep = self._geoms_tm(cols)
        if not keep.any():
            return None
        out = _select(cols, keep, [n for n in buf.schema.names if n not in ("geometry", "length_m")])
        out["geometry"] = shapely.to_wkb(g_tm[keep])
        out["length_m"] = shapely.length(g_tm[keep]).astype(np.float32)
        return {"rail": out}

    def _fin_buildings(self, buf: Buffer, cols: dict[str, list]) -> dict[str, dict] | None:
        g_ll, g_tm, keep = self._geoms_tm(cols)
        if not keep.any():
            return None
        c_ll = shapely.centroid(g_ll)
        is_nj = shapely.contains_xy(self.nj_poly, np.nan_to_num(shapely.get_x(c_ll), nan=0.0), np.nan_to_num(shapely.get_y(c_ll), nan=0.0))
        c_tm = shapely.centroid(g_tm)
        res: dict[str, dict] = {}
        for target, mask in (("buildings", keep & ~is_nj), ("buildings_nj", keep & is_nj)):
            if not mask.any():
                continue
            out = _select(cols, mask, [n for n in buf.schema.names if n not in ("geometry", "cx", "cy")])
            out["geometry"] = shapely.to_wkb(g_tm[mask])
            out["cx"] = shapely.get_x(c_tm[mask])
            out["cy"] = shapely.get_y(c_tm[mask])
            res[target] = out
        return res

    def _fin_water(self, buf: Buffer, cols: dict[str, list]) -> dict[str, dict] | None:
        g_ll, g_tm, keep = self._geoms_tm(cols)
        # water that touches the NJ side (Hudson, bays, kills, NJ inland water); anything purely NY is covered by planimetrics
        touches_nj = shapely.intersects(self.nj_poly, g_ll)
        # whole-extent geometries (the Hudson multipolygon) have their centroid possibly out of scope: keep if they intersect scope
        scope_ll = shapely.box(*self.bbox)
        keep = ~shapely.is_empty(g_ll) & touches_nj & shapely.intersects(scope_ll, g_ll)
        if not keep.any():
            return None
        out = _select(cols, keep, [n for n in buf.schema.names if n not in ("geometry", "area_m2")])
        out["geometry"] = shapely.to_wkb(g_tm[keep])
        out["area_m2"] = shapely.area(g_tm[keep])
        return {"water_nj": out}

    # ---- helpers
    def _in_bbox(self, lon: float, lat: float) -> bool:
        b = self.bbox
        return b[0] <= lon <= b[2] and b[1] <= lat <= b[3]

    def _count(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    @staticmethod
    def _tags_json(tags) -> str:
        return json.dumps({t.k: t.v for t in tags}, ensure_ascii=False, separators=(",", ":"))

    # ---- pass 0: restriction relations (relations only; fast) to know which ways we need node lists for
    def prepass_restrictions(self) -> None:
        t0 = time.time()
        fp = osmium.FileProcessor(str(self.pbf), osmium.osm.RELATION).with_filter(osmium.filter.EmptyTagFilter())
        for r in fp:
            tg = r.tags
            if tg.get("type") != "restriction":
                continue
            rk, rv = None, None
            for t in tg:
                if t.k == "restriction" or t.k.startswith("restriction:"):
                    rk, rv = t.k, t.v
                    if t.k == "restriction":
                        break
            if rv is None:
                continue
            rec: dict[str, Any] = {"relation_id": r.id, "from_way": 0, "via_node": 0, "via_way": 0, "to_way": 0, "restriction": rv,
                                   "restriction_key": rk, "except": tg.get("except", "")}
            for m in r.members:
                if m.role == "from" and m.type == "w" and rec["from_way"] == 0:
                    rec["from_way"] = m.ref
                elif m.role == "to" and m.type == "w" and rec["to_way"] == 0:
                    rec["to_way"] = m.ref
                elif m.role == "via":
                    if m.type == "n" and rec["via_node"] == 0:
                        rec["via_node"] = m.ref
                    elif m.type == "w" and rec["via_way"] == 0:
                        rec["via_way"] = m.ref
            self.restrictions.append(rec)
            for k in ("from_way", "to_way", "via_way"):
                if rec[k]:
                    self.needed_ways.add(rec[k])
        self.timings["prepass_restrictions_s"] = round(time.time() - t0, 1)
        log.info("restriction relations: %d (need %d ways)", len(self.restrictions), len(self.needed_ways))

    # ---- main pass
    def run(self) -> dict[str, Any]:
        t_all = time.time()
        self.prepass_restrictions()
        t0 = time.time()
        fp = (osmium.FileProcessor(str(self.pbf)).with_locations("flex_mem").with_areas().with_filter(osmium.filter.EmptyTagFilter()))
        n_obj = 0
        for o in fp:
            n_obj += 1
            if o.is_node():
                self.on_node(o)
            elif o.is_way():
                self.on_way(o)
            elif o.is_area():
                self.on_area(o)
            elif o.is_relation():
                pass  # restrictions handled in the prepass; multipolygons arrive as areas
        self.node_store = fp.node_location_storage
        self.timings["main_pass_s"] = round(time.time() - t0, 1)
        log.info("main pass done: %d tagged objects in %.0f s", n_obj, time.time() - t0)
        for b in self.buffers.values():
            b.flush()
        self.write_restrictions()
        summary = self.close(t_all)
        return summary

    # ---- callbacks
    def on_node(self, n) -> None:
        try:
            lon, lat = n.location.lon, n.location.lat
        except Exception:
            return
        if not self._in_bbox(lon, lat):
            return
        tg = n.tags
        st = tg.get("addr:state")
        if st:
            s = st.strip().upper()
            if s in ("NJ", "NEW JERSEY", "NY", "NEW YORK"):
                west = self.nj_poly.contains(shapely.Point(lon, lat))
                key = "nj" if s.startswith("N") and "J" in s else "ny"
                self.state_check[f"{key}_tagged"] += 1
                if west:
                    self.state_check[f"{key}_tagged_west"] += 1
        hw = tg.get("highway")
        if hw in SIGNAL_KINDS:
            self.buffers["signals_stops"].add({"node_id": n.id, "kind": hw, "tags": self._tags_json(tg)}, lon, lat)
        self._maybe_furniture(n.id, "node", tg, lon, lat)
        self._maybe_poi(n.id, "node", tg, lon, lat)

    def on_way(self, w) -> None:
        tg = w.tags
        if w.id in self.needed_ways:
            self.way_nodes[w.id] = [nd.ref for nd in w.nodes]
        rw = tg.get("railway")
        if rw in RAIL_KINDS:
            try:
                first = w.nodes[0]
                lon, lat = first.lon, first.lat
            except Exception:
                self.geom_errors += 1
                return
            if not self._in_bbox(lon, lat):
                last = w.nodes[-1]
                try:
                    if not self._in_bbox(last.lon, last.lat):
                        return
                except Exception:
                    return
            try:
                wkb = self.wkbf.create_linestring(w)
            except Exception:
                self.geom_errors += 1
                return
            layer = parse_int(tg.get("layer"), 0)
            bridge = tg.get("bridge", "")
            tunnel = tg.get("tunnel", "")
            is_elev = truthy(bridge) or (layer > 0 and rw in ELEVATED_RAIL and not truthy(tunnel))
            self.buffers["rail"].add({
                "osm_id": w.id, "geometry": wkb, "railway": rw, "bridge": bridge, "tunnel": tunnel, "layer": max(-128, min(127, layer)),
                "name": tg.get("name", ""), "service": tg.get("service", ""), "operator": tg.get("operator", ""), "is_elevated": bool(is_elev),
                "embankment": truthy(tg.get("embankment")), "cutting": truthy(tg.get("cutting")), "usage": tg.get("usage", ""),
                "gauge": tg.get("gauge", ""), "electrified": tg.get("electrified", ""), "tracks": max(0, min(127, parse_int(tg.get("tracks"), 1))),
            }, lon, lat)

    def _area_anchor(self, a) -> tuple[float, float] | None:
        try:
            for ring in a.outer_rings():
                for nd in ring:
                    return nd.lon, nd.lat
        except Exception:
            return None
        return None

    def on_area(self, a) -> None:
        tg = a.tags
        anchor = self._area_anchor(a)
        if anchor is None or not self._in_bbox(*anchor):
            # large water bodies can start outside the box; still test them
            if not (("natural" in tg and tg.get("natural") in WATER_TAGS["natural"]) or "waterway" in tg):
                return
            if anchor is None:
                return
        lon, lat = anchor
        oid = a.orig_id() if a.from_way() else -a.orig_id()
        otype = "way" if a.from_way() else "relation"
        bld = tg.get("building")
        kind_ll = None
        for key, vals in LANDUSE_LEISURE.items():
            if key in tg and tg[key] in vals:
                kind_ll = key
                break
        water_kind = None
        for key, vals in WATER_TAGS.items():
            if key in tg and (vals is None or tg[key] in vals):
                water_kind = key
                break
        is_poi = any(k in tg for k in POI_KEYS)
        is_furn = any(k in tg and tg[k] in v for k, v in FURNITURE_TAGS.items())
        if not (bld or kind_ll or water_kind or is_poi or is_furn):
            return
        wkb = None
        if bld or kind_ll or water_kind:
            try:
                wkb = self.wkbf.create_multipolygon(a)
            except Exception:
                self.geom_errors += 1
                return
        if bld and bld != "no":
            self.buffers["buildings"].add({
                "osm_id": oid, "osm_type": otype, "geometry": wkb, "name": tg.get("name", ""), "building": bld,
                "material": tg.get("building:material", ""), "colour": tg.get("building:colour", ""),
                "levels": parse_float(tg.get("building:levels")), "height": parse_length_m(tg.get("height")),
                "min_height": parse_length_m(tg.get("min_height")), "roof_shape": tg.get("roof:shape", ""),
                "roof_material": tg.get("roof:material", ""), "roof_colour": tg.get("roof:colour", ""),
                "roof_levels": parse_float(tg.get("roof:levels")), "amenity": tg.get("amenity", ""), "shop": tg.get("shop", ""),
                "addr_housenumber": tg.get("addr:housenumber", ""), "addr_street": tg.get("addr:street", ""),
                "addr_state": tg.get("addr:state", ""), "start_date": tg.get("start_date", ""),
            }, lon, lat)
        if kind_ll:
            self.buffers["landuse_leisure"].add({
                "osm_id": oid, "osm_type": otype, "geometry": wkb, "kind": kind_ll, "value": tg[kind_ll], "name": tg.get("name", ""),
                "surface": tg.get("surface", ""), "sport": tg.get("sport", ""), "operator": tg.get("operator", ""),
                "access": tg.get("access", ""), "leaf_type": tg.get("leaf_type", ""),
            }, lon, lat)
        if water_kind:
            self.buffers["water_nj"].add({
                "osm_id": oid, "osm_type": otype, "geometry": wkb, "kind": water_kind, "value": tg[water_kind], "name": tg.get("name", ""),
                "water": tg.get("water", ""), "tidal": truthy(tg.get("tidal")), "intermittent": truthy(tg.get("intermittent")),
            }, lon, lat)
        if is_poi or is_furn:
            # centroid of the area in lon/lat for POI / furniture placement
            try:
                g = shapely.from_wkb(wkb) if wkb else shapely.from_wkb(self.wkbf.create_multipolygon(a))
                c = g.centroid
                clon, clat = c.x, c.y
            except Exception:
                self.geom_errors += 1
                return
            if is_furn:
                self._maybe_furniture(oid, otype, tg, clon, clat)
            if is_poi:
                self._maybe_poi(oid, otype, tg, clon, clat)

    def _maybe_poi(self, oid: int, otype: str, tg, lon: float, lat: float) -> None:
        for key in POI_KEYS:
            if key in tg:
                val = tg[key]
                if key == "amenity" and val in POI_EXCLUDE_AMENITY:
                    continue
                if key == "leisure" and otype != "node":
                    continue  # leisure areas live in landuse_leisure
                self.buffers["pois"].add({
                    "osm_id": oid, "osm_type": otype, "name": tg.get("name", ""), "kind": key, "value": val, "brand": tg.get("brand", ""),
                    "opening_hours": tg.get("opening_hours", ""), "level": tg.get("level", ""), "cuisine": tg.get("cuisine", ""),
                    "addr_housenumber": tg.get("addr:housenumber", ""), "addr_street": tg.get("addr:street", ""), "operator": tg.get("operator", ""),
                }, lon, lat)
                return

    def _maybe_furniture(self, oid: int, otype: str, tg, lon: float, lat: float) -> None:
        for key, vals in FURNITURE_TAGS.items():
            if key in tg and tg[key] in vals:
                val = tg[key]
                sub_key = FURNITURE_SUBTYPE_KEY.get(val, "")
                cap = parse_int(tg.get("capacity"), 0)
                self.buffers["street_furniture_osm"].add({
                    "osm_id": oid, "osm_type": otype, "kind": key, "value": val, "name": tg.get("name", ""),
                    "direction": parse_direction_deg(tg.get("direction")), "capacity": max(0, min(cap, 2**31 - 1)),
                    "subtype": tg.get(sub_key, "") if sub_key else "", "material": tg.get("material", ""), "colour": tg.get("colour", ""),
                    "operator": tg.get("operator", ""), "ref": tg.get("ref", ""), "backrest": tg.get("backrest", ""),
                    "support": tg.get("support", ""), "height_m": parse_length_m(tg.get("height")), "tags": self._tags_json(tg),
                }, lon, lat)
                return

    # ---- restrictions: resolve coordinates after the main pass
    def _loc(self, node_id: int) -> tuple[float, float] | None:
        if not node_id or self.node_store is None:
            return None
        try:
            loc = self.node_store.get(node_id)
        except Exception:
            return None
        if not loc.valid():
            return None
        return loc.lon, loc.lat

    def _adjacent(self, way_id: int, via_node: int) -> tuple[float, float] | None:
        nodes = self.way_nodes.get(way_id)
        if not nodes or len(nodes) < 2:
            return None
        if via_node in nodes:
            i = nodes.index(via_node)
            j = i + 1 if i == 0 else (i - 1 if i == len(nodes) - 1 else i - 1)
            return self._loc(nodes[j])
        return None

    def write_restrictions(self) -> None:
        t0 = time.time()
        cols: dict[str, list] = {k: [] for k in RESTRICTION_SCHEMA.names}
        lonlat: list[tuple[float, float, float, float, float, float]] = []
        n_out = 0
        for rec in self.restrictions:
            via = None
            from_pt = to_pt = None
            if rec["via_node"]:
                via = self._loc(rec["via_node"])
                from_pt = self._adjacent(rec["from_way"], rec["via_node"])
                to_pt = self._adjacent(rec["to_way"], rec["via_node"])
            elif rec["via_way"]:
                nodes = self.way_nodes.get(rec["via_way"])
                if nodes:
                    pts = [p for p in (self._loc(nid) for nid in nodes) if p]
                    if pts:
                        via = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
                    # approach/exit: the via-way's end nodes shared with from/to
                    fn = self.way_nodes.get(rec["from_way"]) or []
                    tn = self.way_nodes.get(rec["to_way"]) or []
                    for end in (nodes[0], nodes[-1]):
                        if end in fn and from_pt is None:
                            from_pt = self._adjacent(rec["from_way"], end)
                        if end in tn and to_pt is None:
                            to_pt = self._adjacent(rec["to_way"], end)
            if via is None or not self._in_bbox(*via):
                n_out += 1
                continue
            nan = (math.nan, math.nan)
            lonlat.append((via[0], via[1], *(from_pt or nan), *(to_pt or nan)))
            for k in ("relation_id", "from_way", "via_node", "via_way", "to_way", "restriction", "restriction_key", "except"):
                cols[k].append(rec[k])
            cols["valid"].append(bool(from_pt and to_pt and rec["from_way"] and rec["to_way"]))
        if lonlat:
            arr = np.array(lonlat, dtype=float)
            vx, vy = lonlat_to_tm(arr[:, 0], arr[:, 1])
            fx, fy = lonlat_to_tm(arr[:, 2], arr[:, 3])
            tx, ty = lonlat_to_tm(arr[:, 4], arr[:, 5])
            keep = _in_scope_tm(vx, vy)
            out = {k: [cols[k][i] for i in np.nonzero(keep)[0]] for k in ("relation_id", "from_way", "via_node", "via_way", "to_way",
                                                                          "restriction", "restriction_key", "except", "valid")}
            out.update({"via_x": vx[keep], "via_y": vy[keep], "from_x": fx[keep], "from_y": fy[keep], "to_x": tx[keep], "to_y": ty[keep]})
            self.writers["restrictions"].write(out)
        self.counts["restrictions_out_of_scope"] = n_out
        self.timings["restrictions_s"] = round(time.time() - t0, 1)

    # ---- finish
    def close(self, t_all: float) -> dict[str, Any]:
        layer_rows: dict[str, int] = {}
        layer_bbox: dict[str, list[float] | None] = {}
        for name, w in self.writers.items():
            path = w.close()
            layer_rows[name] = w.rows
            layer_bbox[name] = [round(float(v), 1) for v in w.bbox] if (w.rows and w.geometry_column) else None
            record_processed(f"osm/{name}", path, stage="osm", sources=[SOURCE_ID], rows=w.rows, schema=w.schema_name,
                             extra={"license": LICENSE})
            log.info("wrote %s: %d rows", path.name, w.rows)
        self.timings["total_s"] = round(time.time() - t_all, 1)
        summary = {
            "schema_version": 1, "pbf": str(self.pbf), "layers": layer_rows, "bbox_tm": layer_bbox,
            "dropped_out_of_scope": {b.name: b.dropped for b in self.buffers.values()},
            "geometry_errors": self.geom_errors, "restrictions_total": len(self.restrictions),
            "state_line_validation": self.state_check, "timings": self.timings, "license": LICENSE,
            "osm_id_convention": "positive = way/node id, negative = relation id; see osm_type",
            "scope_lonlat_bbox": list(self.bbox),
        }
        with open(self.out / "extract_summary.json", "w") as f:
            json.dump(summary, f, indent=1)
        return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pbf", type=Path, default=PBF_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("LON0", "LAT0", "LON1", "LAT1"), help="restrict to a lon/lat box (dev subset)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not a.pbf.exists():
        log.error("PBF not found: %s (run: python -m nycsim_pipeline download --id osm_newyork_pbf)", a.pbf)
        return 2
    ex = Extractor(a.pbf, a.out, tuple(a.bbox) if a.bbox else None)
    summary = ex.run()
    print(json.dumps({"layers": summary["layers"], "timings": summary["timings"], "state_line_validation": summary["state_line_validation"],
                      "geometry_errors": summary["geometry_errors"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
