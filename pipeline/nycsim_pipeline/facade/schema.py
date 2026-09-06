"""Schema of the facade stage outputs.

The stage **extends** every ``tiles/{tile}/buildings.parquet`` written by the buildings stage: the buildings columns
(DATA_CONTRACTS §5 subset + §5.2 extension) are kept byte-for-byte, the sixteen §5 columns the buildings stage deferred
are filled, and a documented §5.4 block of facade-provenance columns is appended.  The parquet metadata keys
``nycsim.schema`` (``buildings/1``), ``nycsim.tile`` and the GeoParquet ``geo`` block are preserved so the buildings
stage's own tests keep passing; the facade stage adds its own ``nycsim.facade.*`` keys.

## DATA_CONTRACTS §5.4 — facade stage extension columns (appended section)

| column | type | meaning |
|---|---|---|
| facade_rule | int16 | 0-based index into `facade.rules.RULES` of the rule that classified the building |
| material_source | int8 | 0 OSM `building:material`, 1 OSM `building:colour`, 2 LPC `MATERIAL1`, 3 rule |
| frontage_source | int8 | 0 primary footprint run, 1 PLUTO `bldgfront`, 2 PLUTO `lotfront`, 3 sqrt(area) |
| facade_frontage_m | float32 | frontage used for `window_cols` |
| bay_width_m | float32 | centre-to-centre window bay spacing of the class's window family |
| water_tower_kind | int8 | 0 none, 1 wood 10,000 gal, 2 wood 20,000 gal, 3 steel |
| attached | int16 | party-wall runs (0 = free-standing); real footprint adjacency |
| n_free_runs | int16 | non-party-wall facade runs >= 1.2 m |
| is_corner | bool | two free runs >= 4 m whose outward normals differ by 60-120 deg |
| free_perimeter_m | float32 | total length of non-party-wall facade |
| street_frontage_m | float32 | total length of street-facing facade |
| storefront_kind_primary | int8 | storefront kind used for the ground-floor treatment (§5 `storefront_kinds` enum) |
| awning_real | bool | `awning_text` is a real business name (else generic wording for the kind) |
| osm_iou | float32 | intersection-over-union of the matched OSM building (0 when unmatched) |
| n_placements | int32 | kit placement records written for this building in `kit_placements.bin` |
"""
from __future__ import annotations

import pyarrow as pa

FACADE_SCHEMA_ID = "facade/1"
FACADE_SCHEMA_VERSION = 1

#: The DATA_CONTRACTS §5 columns the buildings stage deferred and this stage fills, in contract order.
CONTRACT_FILLED: list[tuple[str, pa.DataType]] = [
    ("roof_type", pa.int8()),
    ("roof_mesh_ref", pa.string()),
    ("facade_class", pa.int16()),
    ("material_primary", pa.int8()),
    ("material_secondary", pa.int8()),
    ("window_type", pa.int8()),
    ("window_cols", pa.int16()),
    ("window_rows", pa.int16()),
    ("has_fire_escape", pa.bool_()),
    ("has_stoop", pa.bool_()),
    ("has_cornice", pa.bool_()),
    ("has_water_tower", pa.bool_()),
    ("rooftop_units", pa.int8()),
    ("awning_text", pa.string()),
    ("landmark_model", pa.string()),
    ("street_segment_id", pa.int64()),
]

#: DATA_CONTRACTS §5.4 — facade provenance columns appended by this stage.
EXTENSION: list[tuple[str, pa.DataType]] = [
    ("facade_rule", pa.int16()),
    ("material_source", pa.int8()),
    ("frontage_source", pa.int8()),
    ("facade_frontage_m", pa.float32()),
    ("bay_width_m", pa.float32()),
    ("water_tower_kind", pa.int8()),
    ("attached", pa.int16()),
    ("n_free_runs", pa.int16()),
    ("is_corner", pa.bool_()),
    ("free_perimeter_m", pa.float32()),
    ("street_frontage_m", pa.float32()),
    ("storefront_kind_primary", pa.int8()),
    ("awning_real", pa.bool_()),
    ("osm_iou", pa.float32()),
    ("n_placements", pa.int32()),
]

#: Columns of the buildings stage this stage overwrites in place (never dropped).
OVERWRITTEN: list[str] = ["osm_id", "fidelity"]

ADDED_COLUMNS: list[tuple[str, pa.DataType]] = CONTRACT_FILLED + EXTENSION
ADDED_NAMES: list[str] = [c for c, _ in ADDED_COLUMNS]

#: Columns of ``facade_attrs.parquet`` (the whole-city intermediate joined onto the tiles by ``bin``).
ATTRS_COLUMNS: list[tuple[str, pa.DataType]] = [
    ("tile", pa.string()), ("row", pa.int32()), ("bin", pa.int64()),
] + ADDED_COLUMNS + [
    ("osm_id", pa.int64()),
    ("fidelity", pa.uint16()),
]
#: Join key of every facade intermediate. ``bin`` is *almost* unique (8 rows share the three borough-placeholder
#: BINs 2000000/3000000/4000000), so the exact key is the row's position inside its tile file — both the buildings
#: stage and this stage sort by ``(tile, bin, part_index)``, so the position is stable.
JOIN_KEY: list[str] = ["tile", "row"]


def attrs_schema(extra_meta: dict[str, str] | None = None) -> pa.Schema:
    meta = {b"nycsim.schema": b"facade_attrs/1", b"nycsim.schema_version": b"1"}
    if extra_meta:
        meta.update({k.encode(): v.encode() for k, v in extra_meta.items()})
    return pa.schema([pa.field(n, t, nullable=False) for n, t in ATTRS_COLUMNS], metadata=meta)


#: Columns of ``geom_attrs.parquet`` (the whole-city footprint geometry summary).
GEOM_COLUMNS: list[tuple[str, pa.DataType]] = [
    ("tile", pa.string()), ("row", pa.int32()), ("bin", pa.int64()),
    ("attached", pa.int16()),
    ("n_free_runs", pa.int16()),
    ("free_perimeter_m", pa.float32()),
    ("primary_run_len_m", pa.float32()),
    ("street_frontage_m", pa.float32()),
    ("is_corner", pa.bool_()),
    ("street_segment_id", pa.int64()),
]


def geom_schema(extra_meta: dict[str, str] | None = None) -> pa.Schema:
    meta = {b"nycsim.schema": b"facade_geom/1", b"nycsim.schema_version": b"1"}
    if extra_meta:
        meta.update({k.encode(): v.encode() for k, v in extra_meta.items()})
    return pa.schema([pa.field(n, t, nullable=False) for n, t in GEOM_COLUMNS], metadata=meta)


#: Columns of the cached per-run edge files ``facade/edges/{group}.parquet`` (deleted after the emit pass).
EDGE_COLUMNS: list[tuple[str, pa.DataType]] = [
    ("tile", pa.string()), ("row", pa.int32()), ("bin", pa.int64()),
    ("x0", pa.float64()), ("y0", pa.float64()), ("x1", pa.float64()), ("y1", pa.float64()),
    ("length", pa.float32()), ("nx", pa.float32()), ("ny", pa.float32()), ("heading", pa.float32()),
    ("is_party", pa.bool_()), ("is_street", pa.bool_()), ("street_segment_id", pa.int64()),
]


def edge_schema() -> pa.Schema:
    return pa.schema([pa.field(n, t, nullable=False) for n, t in EDGE_COLUMNS],
                     metadata={b"nycsim.schema": b"facade_edges/1"})
