"""Enumerations and Parquet writers for the roads contracts (DATA_CONTRACTS §7)."""
from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from geopandas.io.arrow import _geopandas_to_arrow

from ..crs import NYC_TM

log = logging.getLogger("nycsim.roads.schema")

SCHEMA_VERSION = 1

# rw_type (CSCL codes, kept verbatim)
RW_STREET, RW_HIGHWAY, RW_BRIDGE, RW_TUNNEL, RW_BOARDWALK, RW_PATH, RW_STEP_STREET, RW_DRIVEWAY, RW_RAMP, RW_ALLEY, RW_UNKNOWN, RW_NONPHYSICAL, RW_UTURN, RW_FERRY = range(1, 15)
RW_NAMES = {1: "street", 2: "highway", 3: "bridge", 4: "tunnel", 5: "boardwalk", 6: "path", 7: "step street", 8: "driveway", 9: "ramp", 10: "alley", 11: "unknown", 12: "non-physical", 13: "U-turn", 14: "ferry"}
# rw_types that carry motor vehicles when trafdir != NV
DRIVABLE_RW = {RW_STREET, RW_HIGHWAY, RW_BRIDGE, RW_TUNNEL, RW_DRIVEWAY, RW_RAMP, RW_ALLEY, RW_UTURN}
# rw_types that may carry a signalised/stop-controlled intersection or street-name signs
STREET_LIKE_RW = {RW_STREET, RW_BRIDGE, RW_TUNNEL, RW_ALLEY}

# traffic_dir
DIR_TWO_WAY, DIR_FORWARD, DIR_BACKWARD, DIR_NONE = 0, 1, 2, 3
TRAFDIR_MAP = {"TW": DIR_TWO_WAY, "FT": DIR_FORWARD, "TF": DIR_BACKWARD, "NV": DIR_NONE}

# lanes.kind
LANE_TRAVEL, LANE_PARKING, LANE_BIKE, LANE_BUS, LANE_TURN, LANE_SHOULDER = range(6)

# junction turn
TURN_STRAIGHT, TURN_LEFT, TURN_RIGHT, TURN_UTURN = range(4)

# nodes.control
CTRL_NONE, CTRL_SIGNAL, CTRL_STOP, CTRL_ALLWAY, CTRL_YIELD = range(5)

# nodes.signal_source
SIG_OSM, SIG_DOT_LPI, SIG_DOT_BARNES, SIG_DOT_RETIMING, SIG_INFERRED, SIG_NONE = 0, 1, 2, 3, 4, 255
SIG_SOURCE_NAMES = {0: "osm", 1: "dot_lpi", 2: "dot_barnes", 3: "dot_retiming", 4: "inferred"}
# bitmask (extension column signal_sources_mask)
SIGBIT_OSM, SIGBIT_LPI, SIGBIT_BARNES, SIGBIT_RETIMING, SIGBIT_INFERRED = 1, 2, 4, 8, 16

# surface
SURF_ASPHALT, SURF_CONCRETE, SURF_COBBLE, SURF_STEEL, SURF_GRAVEL, SURF_BOARDWALK = range(6)

# bike_lane
BIKE_NONE, BIKE_PROTECTED, BIKE_STANDARD, BIKE_SHARROW, BIKE_GREENWAY = range(5)
# CSCL BIKE_LANE domain -> contract enum (mixed classes map to the higher-protection class present)
CSCL_BIKE_MAP = {1: BIKE_PROTECTED, 2: BIKE_STANDARD, 3: BIKE_SHARROW, 4: BIKE_GREENWAY, 5: BIKE_PROTECTED, 6: BIKE_STANDARD, 7: BIKE_NONE, 8: BIKE_PROTECTED, 9: BIKE_PROTECTED, 10: BIKE_PROTECTED, 11: BIKE_PROTECTED}

# truck_route (extension semantics, see REPORT): 0 none, 1 local, 2 through, 3 flagged in CSCL, type unresolved
TRUCK_NONE, TRUCK_LOCAL, TRUCK_THROUGH, TRUCK_UNRESOLVED = range(4)

# signs.source / arrow / support
SIGN_SRC_DOT, SIGN_SRC_STREETNAME, SIGN_SRC_INFERRED = 0, 1, 2
ARROW_NONE, ARROW_LEFT, ARROW_RIGHT, ARROW_BOTH = range(4)
SUPPORT_POLE, SUPPORT_LAMP, SUPPORT_SIGNAL_MAST, SUPPORT_WALL = range(4)

# pavement.kind
PAV_ROADBED, PAV_SIDEWALK, PAV_MEDIAN, PAV_PLAZA, PAV_CURB, PAV_CROSSWALK, PAV_PARKING_LOT, PAV_DRIVEWAY = range(8)

# z_source (extension column on segments)
Z_AT_GRADE, Z_LEVEL_CONST, Z_LEVEL_RAMP = 0, 1, 2
LEVEL_AT_GRADE = 13          # CSCL level code 'M'
CODES_PER_LEVEL = 4          # observed quantum of CSCL level codes: 13 -> 17 -> 21 -> 25 (M, Q, U, Y)
Z_PER_LEVEL_M = 5.5

BOROUGH_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}

SCHEMAS = {
    "segments": f"roads.segments.v{SCHEMA_VERSION}",
    "nodes": f"roads.nodes.v{SCHEMA_VERSION}",
    "lanes": f"roads.lanes.v{SCHEMA_VERSION}",
    "junction_lanes": f"roads.junction_lanes.v{SCHEMA_VERSION}",
    "signals": f"roads.signals.v{SCHEMA_VERSION}",
    "signs": f"roads.signs.v{SCHEMA_VERSION}",
    "pavement": f"roads.pavement.v{SCHEMA_VERSION}",
}


def _shrink_type(t: pa.DataType) -> pa.DataType:
    """Map pandas-3 large_* Arrow types back to the 32-bit offset types the contracts validator expects."""
    if pa.types.is_large_string(t):
        return pa.string()
    if pa.types.is_large_binary(t):
        return pa.binary()
    if pa.types.is_large_list(t) or pa.types.is_list(t):
        return pa.list_(_shrink_type(t.value_type))
    if pa.types.is_struct(t):
        return pa.struct([pa.field(f.name, _shrink_type(f.type), f.nullable) for f in t])
    return t


def normalize_string_types(table: pa.Table) -> pa.Table:
    """Cast every large_string/large_binary/large_list column to its 32-bit counterpart, metadata preserved."""
    fields = [pa.field(f.name, _shrink_type(f.type), f.nullable, f.metadata) for f in table.schema]
    target = pa.schema(fields, metadata=table.schema.metadata)
    if target.equals(table.schema):
        return table
    return table.cast(target)


def write_geoparquet(gdf: gpd.GeoDataFrame, path: Path, schema: str, extra_meta: dict[str, str] | None = None) -> int:
    """GeoParquet (WKB, snappy) with ``nycsim.schema`` metadata. Returns the row count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if gdf.crs is None:
        gdf = gdf.set_crs(NYC_TM)
    table = _geopandas_to_arrow(gdf, index=False, geometry_encoding="WKB", schema_version="1.1.0", write_covering_bbox=False)
    table = normalize_string_types(table)
    meta = {**(table.schema.metadata or {}), b"nycsim.schema": schema.encode(), b"nycsim.schema_version": str(SCHEMA_VERSION).encode()}
    for k, v in (extra_meta or {}).items():
        meta[k.encode()] = str(v).encode()
    table = table.replace_schema_metadata(meta)
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp, compression="snappy", row_group_size=200_000)
    tmp.replace(path)
    log.info("wrote %s (%d rows)", path, table.num_rows)
    return table.num_rows


def write_parquet(df: pd.DataFrame, path: Path, schema: str, extra_meta: dict[str, str] | None = None) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = normalize_string_types(pa.Table.from_pandas(df, preserve_index=False))
    meta = {**(table.schema.metadata or {}), b"nycsim.schema": schema.encode(), b"nycsim.schema_version": str(SCHEMA_VERSION).encode()}
    for k, v in (extra_meta or {}).items():
        meta[k.encode()] = str(v).encode()
    table = table.replace_schema_metadata(meta)
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp, compression="snappy", row_group_size=200_000)
    tmp.replace(path)
    log.info("wrote %s (%d rows)", path, table.num_rows)
    return table.num_rows


def read_schema_tag(path: Path) -> str:
    meta = pq.read_schema(path).metadata or {}
    tag = meta.get(b"nycsim.schema")
    if tag is None:
        raise ValueError(f"{path}: missing nycsim.schema metadata")
    return tag.decode()


def require_schema(path: Path, expected: str) -> None:
    tag = read_schema_tag(path)
    if tag != expected:
        raise ValueError(f"{path}: schema {tag!r} != expected {expected!r}")


def level_to_z(level: np.ndarray | int) -> np.ndarray | float:
    """CSCL/LION level code -> vertical offset from ground (m). 13 = at grade; 4 codes = one grade level = 5.5 m."""
    lv = np.asarray(level, dtype=np.float64)
    lv = np.where((lv < 1) | (lv > 26), LEVEL_AT_GRADE, lv)
    return (lv - LEVEL_AT_GRADE) / CODES_PER_LEVEL * Z_PER_LEVEL_M
