"""Schema of the buildings stage outputs (DATA_CONTRACTS §5 + the appended §5.2 extension columns).

The Arrow schema built here is the single source of truth for ``buildings_base.parquet`` and every
``tiles/{tile}/buildings.parquet``; tests compare the written files against it.
"""
from __future__ import annotations

import json
from enum import IntEnum
from typing import Iterable

import numpy as np
import pyarrow as pa

from ..crs import NYC_TM

SCHEMA_ID = "buildings/1"          # Parquet metadata key ``nycsim.schema`` (consumers fail loudly on mismatch)
SCHEMA_VERSION = 1
GEOMETRY_COLUMN = "footprint"       # DATA_CONTRACTS §5 names the polygon column ``footprint``


class Fidelity(IntEnum):
    """DATA_CONTRACTS §5.1 bit positions."""
    FOOTPRINT_REAL = 0
    HEIGHT_REAL = 1
    ROOF_REAL = 2
    FLOORS_REAL = 3
    YEAR_REAL = 4
    MATERIAL_REAL = 5
    SIGNAGE_REAL = 6
    LANDMARK_MODEL = 7
    SCAFFOLD_REAL = 8
    GROUND_REAL = 9
    FACADE_INFERRED = 10
    HEIGHT_INFERRED = 11
    FLOORS_INFERRED = 12

    @property
    def mask(self) -> int:
        return 1 << int(self)


# Bits this stage is allowed to set. ROOF_REAL (citygml stage), MATERIAL_REAL / FACADE_INFERRED (facade rules),
# LANDMARK_MODEL (landmark scripts) are owned by later stages.
STAGE_BITS = (
    Fidelity.FOOTPRINT_REAL, Fidelity.HEIGHT_REAL, Fidelity.FLOORS_REAL, Fidelity.YEAR_REAL, Fidelity.SIGNAGE_REAL,
    Fidelity.SCAFFOLD_REAL, Fidelity.GROUND_REAL, Fidelity.HEIGHT_INFERRED, Fidelity.FLOORS_INFERRED,
)


class StorefrontKind(IntEnum):
    """DATA_CONTRACTS §5 ``storefront_kinds`` enum."""
    BODEGA = 0
    DELI = 1
    PHARMACY = 2
    RESTAURANT = 3
    BAR = 4
    NAIL_HAIR = 5
    LAUNDROMAT = 6
    BANK = 7
    CLOTHING = 8
    ELECTRONICS = 9
    GROCERY = 10
    HARDWARE = 11
    COFFEE = 12
    PIZZA = 13
    DRY_CLEANER = 14
    GENERIC_RETAIL = 15
    OFFICE_LOBBY = 16
    RESIDENTIAL_LOBBY = 17
    GARAGE_DOOR = 18
    VACANT = 19


# Source codes for the *_source extension columns.
SRC_LIDAR = 0            # height / ground from the OTI footprint LiDAR fields
SRC_PLUTO = 1            # floors / year from PLUTO; height from PLUTO floors x class floor height
SRC_NEIGHBOURS = 2       # median of the 10 nearest buildings with a real value
SRC_FOOTPRINT_YEAR = 0   # year from footprint construction_year
SRC_HEIGHT_TO_FLOORS = 2 # floors from height / class floor height
SRC_BSIN = 3             # ground from Building Elevation & Subgrade z_grade
SRC_NONE = -1

# Facade heading methods.
HEADING_FREE_EDGE_LOT = 0     # longest free (non party-wall) merged edge, tie-broken by lot position
HEADING_FREE_EDGE = 1         # longest free merged edge (no lot centroid available)
HEADING_LONGEST_EDGE = 2      # no free edge >= 2 m: longest merged edge of the ring

# ---- Arrow schema ---------------------------------------------------------------------------------------------------
# (name, type, contract?)  contract=True: DATA_CONTRACTS §5 column; False: §5.2 extension column of this stage.
COLUMNS: list[tuple[str, pa.DataType, bool]] = [
    ("bin", pa.int64(), True),
    ("bbl", pa.int64(), True),
    ("borough", pa.int8(), True),
    (GEOMETRY_COLUMN, pa.binary(), True),
    ("ground_z", pa.float32(), True),
    ("roof_z", pa.float32(), True),
    ("height", pa.float32(), True),
    ("floors", pa.int16(), True),
    ("floor_height", pa.float32(), True),
    ("ground_floor_height", pa.float32(), True),
    ("year_built", pa.int16(), True),
    ("bldg_class", pa.string(), True),
    ("land_use", pa.int8(), True),
    ("has_storefront", pa.bool_(), True),
    ("storefront_names", pa.list_(pa.string()), True),
    ("storefront_kinds", pa.list_(pa.int8()), True),
    ("has_scaffold", pa.bool_(), True),
    ("landmark_id", pa.string(), True),
    ("osm_id", pa.int64(), True),
    ("name", pa.string(), True),
    ("lit_seed", pa.uint32(), True),
    ("fidelity", pa.uint16(), True),
    ("primary_facade_heading", pa.float32(), True),
    ("address", pa.string(), True),
    # tile assignment (DATA_CONTRACTS §2 types)
    ("tile", pa.string(), True),
    ("tx", pa.int32(), True),
    ("ty", pa.int32(), True),
    # ---- §5.2 extension columns (buildings ingest) ----
    ("feature_code", pa.int16(), False),
    ("footprint_area", pa.float32(), False),
    ("centroid_x", pa.float64(), False),
    ("centroid_y", pa.float64(), False),
    ("pluto_joined", pa.bool_(), False),
    ("n_bldgs_on_lot", pa.int16(), False),
    ("is_primary_on_lot", pa.bool_(), False),
    ("height_source", pa.int8(), False),
    ("floors_source", pa.int8(), False),
    ("year_source", pa.int8(), False),
    ("ground_source", pa.int8(), False),
    ("facade_heading_method", pa.int8(), False),
    ("first_floor_offset", pa.float32(), False),
    ("has_subgrade", pa.int8(), False),
    ("lot_frontage", pa.float32(), False),
    ("bldg_frontage", pa.float32(), False),
    ("bldg_depth", pa.float32(), False),
    ("nta", pa.string(), False),
    ("hist_district", pa.string(), False),
    ("hist_district_id", pa.string(), False),
    ("lpc_style", pa.string(), False),
    ("lpc_material", pa.string(), False),
    ("storefront_sources", pa.list_(pa.int8()), False),
]

CONTRACT_COLUMNS = [c for c, _, k in COLUMNS if k]
EXTENSION_COLUMNS = [c for c, _, k in COLUMNS if not k]
# Columns of DATA_CONTRACTS §5 that later stages fill (not produced here).
DEFERRED_CONTRACT_COLUMNS = [
    "roof_type", "roof_mesh_ref", "facade_class", "material_primary", "material_secondary", "window_type",
    "window_cols", "window_rows", "has_fire_escape", "has_stoop", "has_cornice", "has_water_tower", "rooftop_units",
    "awning_text", "landmark_model", "street_segment_id",
]

# Columns that must never contain a null / NaN.
REQUIRED_NO_NULL = [c for c in CONTRACT_COLUMNS] + [
    "feature_code", "footprint_area", "centroid_x", "centroid_y", "pluto_joined", "n_bldgs_on_lot", "is_primary_on_lot",
    "height_source", "floors_source", "year_source", "ground_source", "facade_heading_method", "has_subgrade",
    "nta", "hist_district", "hist_district_id", "lpc_style", "lpc_material", "storefront_sources",
]
# float columns where NaN means "unknown" by design
NAN_ALLOWED = {"first_floor_offset", "lot_frontage", "bldg_frontage", "bldg_depth"}


def arrow_schema(bbox: Iterable[float] | None = None, extra_meta: dict[str, str] | None = None) -> pa.Schema:
    """Arrow schema with GeoParquet 1.1 ``geo`` metadata and the ``nycsim.schema`` key."""
    fields = [pa.field(n, t, nullable=(n in NAN_ALLOWED)) for n, t, _ in COLUMNS]
    meta = {
        b"geo": json.dumps(geo_metadata(bbox)).encode(),
        b"nycsim.schema": SCHEMA_ID.encode(),
        b"nycsim.schema_version": str(SCHEMA_VERSION).encode(),
    }
    if extra_meta:
        meta.update({k.encode(): v.encode() for k, v in extra_meta.items()})
    return pa.schema(fields, metadata=meta)


def geo_metadata(bbox: Iterable[float] | None = None, column: str = GEOMETRY_COLUMN,
                 geometry_types: tuple[str, ...] = ("Polygon",)) -> dict:
    col = {
        "encoding": "WKB",
        "geometry_types": list(geometry_types),
        "crs": NYC_TM.to_json_dict(),
        "edges": "planar",
    }
    if bbox is not None:
        b = [float(v) for v in bbox]
        if len(b) == 4 and all(np.isfinite(b)):
            col["bbox"] = b
    return {"version": "1.1.0", "primary_column": column, "columns": {column: col}}


def landmark_arrow_schema(bbox: Iterable[float] | None = None) -> pa.Schema:
    """Schema of ``landmark_footprints.parquet``."""
    meta = geo_metadata(bbox, "geometry", ("MultiPolygon",))
    meta["columns"]["centroid"] = {"encoding": "WKB", "geometry_types": ["Point"], "crs": NYC_TM.to_json_dict()}
    return pa.schema([
        pa.field("landmark_id", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("bins", pa.list_(pa.int64()), nullable=False),
        pa.field("geometry", pa.binary(), nullable=False),
        pa.field("height_m", pa.float32(), nullable=False),
        pa.field("ground_z", pa.float32(), nullable=False),
        pa.field("roof_z", pa.float32(), nullable=False),
        pa.field("centroid", pa.binary(), nullable=False),
        pa.field("centroid_x", pa.float64(), nullable=False),
        pa.field("centroid_y", pa.float64(), nullable=False),
        pa.field("lon", pa.float64(), nullable=False),
        pa.field("lat", pa.float64(), nullable=False),
        pa.field("match_method", pa.string(), nullable=False),
        pa.field("n_footprints", pa.int16(), nullable=False),
        pa.field("footprint_area", pa.float32(), nullable=False),
        pa.field("lp_number", pa.string(), nullable=False),
        pa.field("expected_height_m", pa.float32(), nullable=True),
        pa.field("height_dev_m", pa.float32(), nullable=True),
        pa.field("tile", pa.string(), nullable=False),
    ], metadata={
        b"geo": json.dumps(meta).encode(),
        b"nycsim.schema": b"landmark_footprints/1",
        b"nycsim.schema_version": b"1",
    })


def lit_seed(bin_: np.ndarray, doitt_id: np.ndarray) -> np.ndarray:
    """Deterministic uint32 window-lighting seed per footprint (splitmix64 finaliser over bin and doitt_id)."""
    x = (bin_.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)) ^ (doitt_id.astype(np.uint64) * np.uint64(0xBF58476D1CE4E5B9))
    x = x ^ (x >> np.uint64(30))
    x = x * np.uint64(0xBF58476D1CE4E5B9)
    x = x ^ (x >> np.uint64(27))
    x = x * np.uint64(0x94D049BB133111EB)
    x = x ^ (x >> np.uint64(31))
    return (x & np.uint64(0xFFFFFFFF)).astype(np.uint32)
