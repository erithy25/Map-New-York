"""Validate ``tiles/{tile}/kit_placements.bin`` and reconcile its kit ids with the Blender kit catalog.

    python -m nycsim_pipeline.facade.validate_placements [--tiles t_x_y ...] [--limit N]

Two jobs:

1. **Structural and geometric validation of every tile.** File size is a whole number of 40-byte records; the ``.json``
   header's ``count``, ``bytes`` and ``sha256`` match the file; every ``bin`` in the file exists in that tile's
   ``buildings.parquet``; every placement sits inside its own building's footprint bounding box plus
   :data:`BBOX_MARGIN_M`; ``z`` lies between the building's ground and roof plus the tallest roof piece; ``yaw_deg``
   and ``scale`` are finite and in range; every ``kit_id`` is registered in :mod:`nycsim_pipeline.facade.kit_ids`; and
   a tile that holds buildings holds placements.

2. **Reconciliation with ``blender_out/kit/catalog/*.json``.** The pipeline numbers kit pieces (DATA_CONTRACTS §6 takes
   a ``uint32``); the Blender kit names them.  :data:`CATALOG_ALIAS` is the explicit, reviewed mapping from a pipeline
   piece to the catalog entry that models it, and the result is written to ``data/processed/facade/kit_catalog_map.json``
   so the UE importer can resolve a ``kit_id`` to a ``.glb``.  Pipeline pieces the kit does not model yet, and catalog
   entries the placer never emits, are both listed rather than hidden.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import shapely

from ..paths import BLENDER_OUT, PROCESSED, VERIFICATION
from .kit_ids import KIT_ID, KIT_PIECE, PIECE_SIZE
from .placements import PLACEMENT_DTYPE, RECORD_BYTES

log = logging.getLogger("nycsim.facade.validate")

TILES_ROOT = PROCESSED / "tiles"
CATALOG_DIR = BLENDER_OUT / "kit" / "catalog"
OUT_MAP = PROCESSED / "facade" / "kit_catalog_map.json"
REPORT = VERIFICATION / "facade" / "placement_validation.json"

BBOX_MARGIN_M = 2.0        # a stoop, a fire escape and a sidewalk shed project beyond the footprint
Z_ABOVE_ROOF_M = 16.0      # the tallest roof piece is a 20,000 gal wooden tank on its stand
Z_BELOW_GROUND_M = 1.5

#: Explicit pipeline piece -> Blender kit catalog entry. Reviewed by hand; ``""`` means the kit does not model the
#: piece yet and the placement must fall back to the nearest piece named in the report.
CATALOG_ALIAS: dict[tuple[str, str], str] = {
    # window: the catalog names every window family win_<window_type>
    **{("window", n): f"win_{n}" for n in
       ("double_hung_1_1", "double_hung_1_1_stone", "double_hung_1_1_soldier", "double_hung_2_2", "double_hung_6_6",
        "casement_pair", "steel_industrial_4x5", "punched_office", "curtain_wall_module", "bay_window",
        "arched_tenement", "dormer", "aluminum_slider", "picture_window", "gothic_arched", "ribbon_strip",
        "chicago_tripartite", "through_wall_ac_sleeve")},
    ("window_accessory", "ac_unit_window"): "acc_ac_window_medium",
    ("window_accessory", "ac_sleeve_through_wall"): "acc_through_wall_ac_unit",
    ("window_accessory", "window_guard"): "acc_window_guard_security",
    ("window_accessory", "flower_box"): "acc_flower_box",
    ("window_accessory", "shutter_pair"): "",
    ("window_accessory", "window_lit_curtain"): "acc_curtains_closed",
    ("door_entry", "stoop_high_brownstone"): "entry_stoop_brownstone_10",
    ("door_entry", "stoop_low_brick"): "entry_stoop_tenement_4",
    ("door_entry", "stoop_wood"): "entry_stoop_tenement_4",
    ("door_entry", "areaway_gate"): "entry_areaway_railing",
    ("door_entry", "door_residential"): "entry_door_single_panel",
    ("door_entry", "door_residential_lobby"): "entry_apartment_lobby_glass",
    ("door_entry", "door_office_lobby"): "entry_double_doors",
    ("door_entry", "door_service"): "entry_service_door_steel",
    ("door_entry", "garage_door_residential"): "entry_garage_door",
    ("door_entry", "garage_door_commercial"): "entry_loft_roll_gate",
    ("door_entry", "canopy_entry"): "entry_lobby_canopy",
    ("cornice", "none_parapet"): "parapet_cap_metal_coping",
    ("cornice", "pressed_metal_brackets"): "cornice_pressed_metal_a",
    ("cornice", "pressed_metal_dentil"): "cornice_pressed_metal_b",
    ("cornice", "stone_modillion"): "cornice_stone",
    ("cornice", "brick_corbel"): "cornice_brick_corbel",
    ("cornice", "wood_dentil"): "cornice_pressed_metal_c",
    ("cornice", "wood_simple"): "cornice_pressed_metal_c",
    ("cornice", "cast_iron_pediment"): "cornice_pressed_metal_a",
    ("string_course", "string_course_stone"): "string_course_stone_belt",
    ("string_course", "string_course_brick"): "string_course_brick_soldier",
    ("string_course", "belt_course_terracotta"): "string_course_terracotta_band",
    ("quoin", "quoin_limestone"): "quoin_limestone",
    ("quoin", "quoin_brick"): "quoin_brick_rusticated",
    ("pilaster", "pilaster_brick"): "pilaster_brick",
    ("pilaster", "pilaster_stone"): "pilaster_stone_fluted",
    ("pilaster", "pilaster_cast_iron"): "pilaster_cast_iron",
    ("pilaster", "column_stone"): "pilaster_stone_fluted",
    ("storefront", "storefront_bay_3_6"): "storefront_bay_36",
    ("storefront", "storefront_bay_4_8"): "storefront_bay_48",
    ("storefront", "storefront_bay_6_0"): "storefront_bay_60",
    ("storefront", "storefront_door"): "entry_double_doors",
    ("storefront", "roll_gate_closed"): "storefront_gate_48_closed",
    ("storefront", "roll_gate_half"): "storefront_gate_48_half",
    ("storefront", "roll_gate_open"): "storefront_gate_48_open",
    ("storefront", "awning_fabric"): "storefront_awning_48",
    ("storefront", "sign_band"): "storefront_sign_projecting",
    ("storefront", "sidewalk_cellar_door"): "entry_cellar_hatch",
    ("storefront", "loading_dock_door"): "entry_loft_roll_gate",
    **{("storefront_interior", n): f"storefront_interior_{n}" for n in
       ("bodega", "deli", "pharmacy", "restaurant", "bar", "nail_hair", "laundromat", "bank", "generic_retail",
        "lobby", "vacant")},
    ("fire_escape", "fire_escape_balcony"): "fire_escape_floor_unit",
    ("fire_escape", "fire_escape_stair"): "fire_escape_floor_unit_wide",
    ("fire_escape", "fire_escape_drop_ladder"): "fire_escape_drop_ladder",
    ("fire_escape", "fire_escape_roof_ladder"): "fire_escape_top_hook",
    ("parapet", "parapet_brick"): "parapet_wall_brick",
    ("parapet", "parapet_stone"): "parapet_cap_stone",
    ("parapet", "parapet_concrete"): "parapet_cap_metal_coping",
    ("parapet", "setback_terrace"): "parapet_balustrade",
    ("bulkhead", "bulkhead_stair"): "bulkhead_stair_brick",
    ("bulkhead", "bulkhead_elevator"): "bulkhead_elevator_machine",
    ("bulkhead", "bulkhead_mechanical"): "bulkhead_stair_metal",
    ("water_tower", "water_tower_wood_10k"): "water_tower_small",
    ("water_tower", "water_tower_wood_20k"): "water_tower_large",
    ("water_tower", "water_tower_steel"): "water_tower_large",
    ("hvac", "rooftop_ac_small"): "hvac_rooftop_unit_small",
    ("hvac", "rooftop_ac_large"): "hvac_rooftop_unit_large",
    ("hvac", "cooling_tower"): "hvac_cooling_tower",
    ("hvac", "exhaust_fan"): "hvac_exhaust_fan",
    ("hvac", "vent_pipe"): "hvac_vent_pipe_cluster",
    ("hvac", "satellite_dish"): "acc_satellite_dish",
    ("hvac", "roof_hatch"): "",
    ("antenna", "cell_antenna_panel"): "antenna_cell_panel_array",
    ("antenna", "cell_antenna_mast"): "antenna_whip_mast",
    ("antenna", "roof_antenna_mast"): "antenna_whip_mast",
    ("billboard", "billboard_wall"): "billboard_wall_mounted",
    ("billboard", "billboard_roof"): "billboard_rooftop",
    ("billboard", "sign_vertical_blade"): "storefront_sign_projecting",
    ("scaffold", "sidewalk_shed_bay"): "sidewalk_shed_module",
    ("scaffold", "sidewalk_shed_end"): "sidewalk_shed_corner",
    ("scaffold", "shed_light"): "",
    ("scaffold", "pipe_scaffold_bay"): "scaffold_pipe_bay",
    ("fence", "areaway_railing"): "fence_iron_areaway",
    ("fence", "stoop_railing"): "fence_iron_areaway",
    ("fence", "roof_railing"): "fence_iron_areaway",
    ("fence", "chain_link_panel"): "construction_fence_chainlink",
    ("vegetation", "ivy_panel"): "ivy_panel_dense",
    ("vegetation", "roof_planter"): "roof_weeds_patch",
    ("vegetation", "window_planter"): "acc_flower_box",
    ("trim", "lintel_stone"): "trim_lintel_stone",
    ("trim", "sill_stone"): "trim_sill_cast_stone",
    ("trim", "lintel_soldier_brick"): "string_course_brick_soldier",
    ("trim", "cornice_bracket"): "cornice_bracket",
    ("trim", "balcony_slab"): "",
    ("trim", "balcony_juliet"): "",
    ("trim", "dormer_gabled"): "win_dormer",
    ("trim", "bay_window_3sided"): "win_bay_window",
}


def load_catalog() -> dict[str, dict]:
    if not CATALOG_DIR.exists():
        return {}
    out: dict[str, dict] = {}
    for p in sorted(CATALOG_DIR.glob("*.json")):
        try:
            d = json.load(open(p))
        except json.JSONDecodeError as exc:
            log.warning("catalog entry %s unreadable: %s", p.name, exc)
            continue
        cid = d.get("id") or p.stem
        out[str(cid)] = d
    return out


def catalog_map(catalog: dict[str, dict]) -> dict:
    """Numeric ``kit_id`` -> catalog entry, with the unresolved pieces listed."""
    entries = []
    missing = []
    for (cat, name), kid in sorted(KIT_ID.items(), key=lambda kv: kv[1]):
        alias = CATALOG_ALIAS.get((cat, name), "")
        entry = catalog.get(alias) if alias else None
        if alias and entry is None and catalog:
            missing.append({"kit_id": kid, "category": cat, "name": name, "alias": alias,
                            "reason": "alias not present in the catalog"})
            alias = ""
        if not alias:
            missing.append({"kit_id": kid, "category": cat, "name": name, "alias": "",
                            "reason": "no kit piece models this yet"})
        entries.append({
            "kit_id": kid, "category": cat, "name": name, "catalog_id": alias,
            "glb": (entry or {}).get("glb", ""),
            "nominal_size_m": (entry or {}).get("nominal_size_m", list(PIECE_SIZE.get(name, (0.0, 0.0, 0.0)))),
        })
    used_aliases = {e["catalog_id"] for e in entries if e["catalog_id"]}
    return {
        "schema_version": 1,
        "kit_catalog_dir": str(CATALOG_DIR),
        "catalog_entries": len(catalog),
        "pipeline_pieces": len(entries),
        "resolved": sum(1 for e in entries if e["catalog_id"]),
        "unresolved": [m for m in missing if not m["alias"]],
        "catalog_entries_never_placed": sorted(set(catalog) - used_aliases),
        "map": entries,
    }


def validate_tile(tile_dir: Path) -> dict:
    """Structural and geometric checks for one tile."""
    name = tile_dir.name
    res: dict = {"tile": name, "problems": [], "placements": 0, "bytes": 0, "buildings": 0}
    bin_p = tile_dir / "kit_placements.bin"
    json_p = tile_dir / "kit_placements.json"
    b_p = tile_dir / "buildings.parquet"
    if not b_p.exists():
        res["problems"].append("buildings.parquet missing")
        return res
    n_buildings = pq.ParquetFile(b_p).metadata.num_rows
    res["buildings"] = n_buildings
    if not bin_p.exists() or not json_p.exists():
        res["problems"].append("kit_placements.bin/.json missing")
        return res
    raw = bin_p.read_bytes()
    res["bytes"] = len(raw)
    if len(raw) % RECORD_BYTES:
        res["problems"].append(f"{len(raw)} bytes is not a multiple of {RECORD_BYTES}")
        return res
    rec = np.frombuffer(raw, dtype=PLACEMENT_DTYPE)
    res["placements"] = int(len(rec))
    hdr = json.load(open(json_p))
    if hdr.get("count") != len(rec):
        res["problems"].append(f"header count {hdr.get('count')} != {len(rec)} records")
    if hdr.get("bytes") != len(raw):
        res["problems"].append(f"header bytes {hdr.get('bytes')} != {len(raw)}")
    if hdr.get("record_bytes") != RECORD_BYTES:
        res["problems"].append(f"header record_bytes {hdr.get('record_bytes')} != {RECORD_BYTES}")
    if hdr.get("sha256") != hashlib.sha256(raw).hexdigest():
        res["problems"].append("header sha256 does not match the file")
    if n_buildings and len(rec) == 0:
        res["problems"].append(f"{n_buildings} buildings but no placements")
        return res
    if len(rec) == 0:
        return res

    unknown = sorted({int(k) for k in np.unique(rec["kit_id"])} - set(KIT_PIECE))
    if unknown:
        res["problems"].append(f"unregistered kit ids: {unknown[:10]}")
    if not np.isfinite(rec["x"]).all() or not np.isfinite(rec["y"]).all() or not np.isfinite(rec["z"]).all():
        res["problems"].append("non-finite coordinates")
    if not np.isfinite(rec["yaw_deg"]).all() or np.abs(rec["yaw_deg"]).max() > 360.001:
        res["problems"].append("yaw_deg outside [-360, 360]")
    if not np.isfinite(rec["scale"]).all() or rec["scale"].min() <= 0 or rec["scale"].max() > 200.0:
        res["problems"].append(f"scale out of range [{rec['scale'].min()}, {rec['scale'].max()}]")
    if (rec["flags"] & ~np.uint32(0b111)).any():
        res["problems"].append("flags outside the three documented bits")

    tb = pq.read_table(b_p, columns=["bin", "footprint", "ground_z", "roof_z", "has_storefront", "window_rows",
                                     "floors", "n_placements"])
    bins = tb["bin"].to_numpy()
    order = np.argsort(bins, kind="stable")
    sb = bins[order]
    pos = np.searchsorted(sb, rec["bin"])
    ok = (pos < len(sb)) & (sb[np.minimum(pos, len(sb) - 1)] == rec["bin"])
    if not ok.all():
        res["problems"].append(f"{int((~ok).sum())} placements reference a bin absent from the tile")
    idx = order[np.minimum(pos, len(sb) - 1)]
    g = shapely.from_wkb(np.asarray(tb["footprint"].to_pylist(), dtype=object))
    xmin, ymin, xmax, ymax = shapely.bounds(g).T
    gz = tb["ground_z"].to_numpy(zero_copy_only=False)
    rz = tb["roof_z"].to_numpy(zero_copy_only=False)
    sel = ok
    outside = ((rec["x"][sel] < xmin[idx[sel]] - BBOX_MARGIN_M) | (rec["x"][sel] > xmax[idx[sel]] + BBOX_MARGIN_M)
               | (rec["y"][sel] < ymin[idx[sel]] - BBOX_MARGIN_M) | (rec["y"][sel] > ymax[idx[sel]] + BBOX_MARGIN_M))
    if outside.any():
        res["problems"].append(f"{int(outside.sum())} placements outside their footprint bbox + {BBOX_MARGIN_M} m")
    badz = ((rec["z"][sel] < gz[idx[sel]] - Z_BELOW_GROUND_M) | (rec["z"][sel] > rz[idx[sel]] + Z_ABOVE_ROOF_M))
    if badz.any():
        res["problems"].append(f"{int(badz.sum())} placements with z outside the building's vertical extent")

    wr = tb["window_rows"].to_numpy()
    fl = tb["floors"].to_numpy()
    if (wr > fl).any():
        res["problems"].append("window_rows exceeds floors")
    # storefront pieces only on buildings the data says have a storefront
    sf_ids = {kid for (cat, _), kid in KIT_ID.items() if cat in ("storefront", "storefront_interior")}
    has_sf = tb["has_storefront"].to_numpy(zero_copy_only=False)
    is_sf = np.isin(rec["kit_id"], list(sf_ids)) & sel
    if is_sf.any() and not has_sf[idx[is_sf]].all():
        res["problems"].append(f"{int((~has_sf[idx[is_sf]]).sum())} storefront pieces on buildings without a storefront")
    npl = tb["n_placements"].to_numpy()
    if int(npl.sum()) != len(rec):
        res["problems"].append(f"n_placements column sums to {int(npl.sum())} but the file holds {len(rec)}")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nycsim_pipeline.facade.validate_placements",
                                 description="Validate kit placements and reconcile them with the Blender kit catalog")
    ap.add_argument("--tiles", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None, help="validate only the first N tiles")
    ap.add_argument("--tiles-root", default=str(TILES_ROOT))
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    root = Path(a.tiles_root)
    tiles = ([root / t for t in a.tiles] if a.tiles
             else sorted(p.parent for p in root.glob("*/kit_placements.bin")))
    if a.limit:
        tiles = tiles[: a.limit]
    if not tiles:
        print(json.dumps({"error": f"no tiles with kit_placements.bin under {root}"}, indent=1))
        return 1

    catalog = load_catalog()
    cmap = catalog_map(catalog)
    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_MAP, "w") as f:
        json.dump(cmap, f, indent=1)

    results = [validate_tile(t) for t in tiles]
    bad = [r for r in results if r["problems"]]
    used = set()
    for t in tiles:
        p = t / "kit_placements.json"
        if p.exists():
            used |= {int(k) for k in json.load(open(p)).get("kit_ids", [])}
    summary = {
        "schema_version": 1,
        "tiles_checked": len(results),
        "tiles_with_problems": len(bad),
        "problems": bad[:40],
        "placements": sum(r["placements"] for r in results),
        "bytes": sum(r["bytes"] for r in results),
        "buildings": sum(r["buildings"] for r in results),
        "distinct_kit_ids_used": len(used),
        "kit_ids_used_without_a_catalog_piece": sorted(
            kid for kid in used if not cmap["map"][[m["kit_id"] for m in cmap["map"]].index(kid)]["catalog_id"]),
        "catalog": {"entries": cmap["catalog_entries"], "resolved_pipeline_pieces": cmap["resolved"],
                    "pipeline_pieces": cmap["pipeline_pieces"],
                    "unresolved_pipeline_pieces": [m["name"] for m in cmap["unresolved"]],
                    "catalog_entries_never_placed": cmap["catalog_entries_never_placed"]},
        "kit_catalog_map": str(OUT_MAP),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "problems"}, indent=1))
    if bad:
        print(json.dumps({"first_problems": bad[:5]}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
