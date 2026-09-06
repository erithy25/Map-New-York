"""Machine-readable form of docs/DATA_CONTRACTS.md: required columns and types per artefact, plus validators.

Usage:
    from nycsim_pipeline.contracts import validate_parquet
    problems = validate_parquet("buildings", path)   # [] when conformant

Types are checked by pyarrow type *family* (int, float, string, bool, list, binary) so that int32 vs int64
storage choices do not fail validation; nullability of required columns is enforced (no nulls allowed).
"""
from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# family -> predicate on pa.DataType
def _is_string(t) -> bool:
    """Arrow has three string encodings; a contract that says "str" means any of them."""
    return (pa.types.is_string(t) or pa.types.is_large_string(t)
            or (pa.types.is_dictionary(t) and pa.types.is_string(t.value_type)))


def _is_list(t) -> bool:
    return pa.types.is_list(t) or pa.types.is_large_list(t) or pa.types.is_fixed_size_list(t)


def _is_binary(t) -> bool:
    return pa.types.is_binary(t) or pa.types.is_large_binary(t) or pa.types.is_fixed_size_binary(t)


_FAMILY = {
    "int": pa.types.is_integer,
    "float": pa.types.is_floating,
    "str": _is_string,
    "bool": pa.types.is_boolean,
    "list": _is_list,
    "bin": _is_binary,
    "geom": _is_binary,
    "any": lambda t: True,
}

# artefact -> {column: (family, required_non_null)}
CONTRACTS: dict[str, dict[str, tuple[str, bool]]] = {
    "tiles_index": {"tile": ("str", True), "tx": ("int", True), "ty": ("int", True), "x0": ("float", True), "y0": ("float", True),
                    "borough_codes": ("list", False), "n_buildings": ("int", True), "n_road_segments": ("int", True), "n_props": ("int", True),
                    "n_trees": ("int", True), "has_terrain": ("bool", True), "has_water": ("bool", True), "has_land": ("bool", True),
                    "z_min": ("float", False), "z_max": ("float", False)},
    "buildings": {"bin": ("int", True), "bbl": ("int", False), "borough": ("int", True), "footprint": ("geom", True), "ground_z": ("float", True),
                  "roof_z": ("float", True), "height": ("float", True), "floors": ("int", True), "floor_height": ("float", True),
                  "ground_floor_height": ("float", True), "year_built": ("int", True), "bldg_class": ("str", False), "land_use": ("int", False),
                  "roof_type": ("int", True), "roof_mesh_ref": ("str", False), "facade_class": ("int", True), "material_primary": ("int", True),
                  "material_secondary": ("int", True), "window_type": ("int", True), "window_cols": ("int", True), "window_rows": ("int", True),
                  "has_fire_escape": ("bool", True), "has_stoop": ("bool", True), "has_cornice": ("bool", True), "has_storefront": ("bool", True),
                  "storefront_names": ("list", False), "storefront_kinds": ("list", False), "has_water_tower": ("bool", True),
                  "rooftop_units": ("int", True), "has_scaffold": ("bool", True), "awning_text": ("str", False), "landmark_id": ("str", False),
                  "landmark_model": ("str", False), "osm_id": ("int", True), "name": ("str", False), "lit_seed": ("int", True),
                  "fidelity": ("int", True), "primary_facade_heading": ("float", True), "street_segment_id": ("int", False), "address": ("str", False)},
    "buildings_base": {"bin": ("int", True), "borough": ("int", True), "footprint": ("geom", True), "ground_z": ("float", True), "roof_z": ("float", True),
                       "height": ("float", True), "floors": ("int", True), "year_built": ("int", True), "fidelity": ("int", True),
                       "primary_facade_heading": ("float", True), "tile": ("str", True), "lit_seed": ("int", True)},
    "road_segments": {"segment_id": ("int", True), "from_node": ("int", True), "to_node": ("int", True), "geometry": ("geom", True), "street_name": ("str", False),
                      "rw_type": ("int", True), "traffic_dir": ("int", True), "travel_lanes": ("int", True), "park_lanes": ("int", True),
                      "total_lanes": ("int", True), "width_m": ("float", True), "posted_speed_mph": ("int", True), "bike_lane": ("int", True),
                      "bus_lane": ("bool", True), "truck_route": ("int", True), "level_from": ("int", True), "level_to": ("int", True),
                      "surface": ("int", True), "borough": ("int", True), "speed_source": ("int", True), "lanes_source": ("int", True)},
    "road_nodes": {"node_id": ("int", True), "x": ("float", True), "y": ("float", True), "z": ("float", True), "is_signalized": ("bool", True),
                   "signal_source": ("int", True), "has_stop_sign": ("bool", True), "has_all_way_stop": ("bool", True), "control": ("int", True)},
    "lanes": {"lane_id": ("int", True), "segment_id": ("int", True), "index_from_center": ("int", True), "direction": ("int", True), "width_m": ("float", True),
              "kind": ("int", True), "geometry": ("geom", True), "speed_mps": ("float", True), "successors": ("list", False), "predecessors": ("list", False)},
    "junction_lanes": {"from_lane": ("int", True), "to_lane": ("int", True), "turn": ("int", True), "signal_group": ("int", True), "yield_to": ("list", False), "geometry": ("geom", True)},
    "signals": {"node_id": ("int", True), "controller_id": ("int", True), "cycle_s": ("float", True), "offset_s": ("float", True), "phases": ("list", True)},
    "signs": {"sign_id": ("int", True), "x": ("float", True), "y": ("float", True), "z": ("float", True), "facing_heading": ("float", True), "mutcd_code": ("str", False),
              "text": ("str", False), "arrow": ("int", True), "sign_w_m": ("float", True), "sign_h_m": ("float", True), "support": ("int", True), "source": ("int", True)},
    "props": {"prop_id": ("int", True), "kind": ("int", True), "x": ("float", True), "y": ("float", True), "z": ("float", True), "heading": ("float", True),
              "variant": ("int", True), "text": ("str", False), "source": ("int", True), "dataset_id": ("str", False)},
    "bus_routes": {"route_id": ("str", True), "short_name": ("str", True), "long_name": ("str", False), "geometry": ("geom", True)},
    "bus_stops": {"stop_id": ("str", True), "x": ("float", True), "y": ("float", True), "z": ("float", True), "name": ("str", True), "has_shelter": ("bool", True)},
    "hydrography": {"water_id": ("int", True), "kind": ("str", True), "name": ("str", False), "tidal": ("bool", True), "geometry": ("geom", True)},
    "density": {"nta_code": ("str", True), "hour": ("int", True), "dow": ("int", True), "veh_per_km_lane": ("float", True), "ped_per_m2_sidewalk": ("float", True),
                "taxi_share": ("float", True), "truck_share": ("float", True), "bus_share": ("float", True), "bike_share": ("float", True), "source": ("any", False)},
}


def validate_schema(name: str, schema: pa.Schema, num_rows: int | None = None, table: pa.Table | None = None) -> list[str]:
    spec = CONTRACTS[name]
    problems: list[str] = []
    for col, (family, required) in spec.items():
        if col not in schema.names:
            problems.append(f"missing column {col!r}")
            continue
        t = schema.field(col).type
        if not _FAMILY[family](t):
            problems.append(f"column {col!r} has type {t}, expected family {family}")
        if required and table is not None:
            nulls = table.column(col).null_count
            if nulls:
                problems.append(f"column {col!r} has {nulls} nulls (required)")
    return problems


def validate_parquet(name: str, path: str | Path, check_nulls: bool = True) -> list[str]:
    path = Path(path)
    if not path.exists():
        return [f"file missing: {path}"]
    pf = pq.ParquetFile(path)
    table = pf.read(columns=[c for c in CONTRACTS[name] if c in pf.schema_arrow.names]) if check_nulls else None
    return validate_schema(name, pf.schema_arrow, pf.metadata.num_rows, table)


def main(argv: list[str] | None = None) -> int:
    import argparse, json
    ap = argparse.ArgumentParser(description="Validate a parquet artefact against DATA_CONTRACTS")
    ap.add_argument("name", choices=sorted(CONTRACTS))
    ap.add_argument("path")
    a = ap.parse_args(argv)
    problems = validate_parquet(a.name, a.path)
    print(json.dumps({"artefact": a.name, "path": a.path, "problems": problems}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
