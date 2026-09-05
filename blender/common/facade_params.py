"""Kit parameter enums shared between the pipeline facade classifier, the Blender facade kit and the UE placement code.

This module is the single source of truth for the *names* behind the integer enums in ``docs/DATA_CONTRACTS.md`` §5
(``material_primary``, ``window_type``, ``storefront_kinds``, ``facade_class``).  The pipeline writes the integers; the kit
names its pieces after the strings here; the UE importer reads ``blender_out/kit/catalog`` where the strings appear again.

Everything here is data — no bpy import — so it can be imported by the pipeline (``PYTHONPATH=blender/common``) and by
Blender scripts alike.  ``facade_classes.json`` next to this file is the self-describing typology table (≥ 40 NYC classes);
``load_facade_classes()`` validates it against these enums on load.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
_HERE = Path(__file__).resolve().parent
FACADE_CLASSES_PATH = _HERE / "facade_classes.json"

# --------------------------------------------------------------------------- materials (DATA_CONTRACTS §5 material_primary)
# Index == the int8 stored in buildings.parquet.  Indices 0–16 are the contract enum; 17+ are kit-only surfaces used by
# props on the same buildings (never written to material_primary).
MATERIALS: tuple[str, ...] = (
    "red_brick", "brown_brick", "tan_brick", "white_glazed_brick", "brownstone", "limestone", "terracotta", "cast_iron",
    "glass_curtain", "concrete", "stucco", "vinyl_siding", "wood_clapboard", "stone_rubble", "metal_panel", "granite", "precast",
    # kit-only surfaces (17+)
    "asphalt", "concrete_sidewalk", "roof_membrane", "tar_roof", "corrugated_metal", "painted_metal_green", "painted_metal_black",
    "rust", "cedar_wood", "glass_clear", "fabric_awning", "painted_wood_white", "dark_brick", "plywood_green", "steel_galvanized",
    "aluminum_anodized", "bronze_anodized", "canvas_striped", "interior_tile", "interior_wood_floor",
)
MATERIAL_INDEX: dict[str, int] = {n: i for i, n in enumerate(MATERIALS)}
CONTRACT_MATERIAL_COUNT = 17  # 0..16 are the §5 enum


# --------------------------------------------------------------------------- window types (DATA_CONTRACTS §5 window_type "kit enum")
# Each entry: (name, opening width m, opening height m, description). Openings are the masonry rough opening the kit piece
# fills; the piece's nominal_size_m in the catalog equals (width, depth, height) of its bounds.
WINDOW_TYPES: tuple[tuple[str, float, float, str], ...] = (
    ("double_hung_1_1", 0.95, 1.70, "one-over-one double-hung wood/vinyl sash, plain brick opening"),
    ("double_hung_1_1_stone", 0.95, 1.70, "one-over-one with projecting stone lintel and sill (brownstone/limestone)"),
    ("double_hung_1_1_soldier", 0.95, 1.70, "one-over-one with brick soldier-course lintel and cast-stone sill"),
    ("double_hung_2_2", 0.95, 1.80, "two-over-two double-hung (Italianate brownstone / 1860–1890 tenement)"),
    ("double_hung_6_6", 0.90, 1.60, "six-over-six divided-light double-hung (Federal / Greek Revival / colonial revival)"),
    ("casement_pair", 1.10, 1.60, "pair of steel or wood casements (prewar apartment 1920–1940)"),
    ("steel_industrial_4x5", 1.50, 2.30, "steel-sash industrial window 4 × 5 lights with pivot centre (loft / factory)"),
    ("punched_office", 1.50, 2.20, "aluminium punched office window 1.5 × 2.2 m in masonry (1950–1990 office / hospital)"),
    ("curtain_wall_module", 1.50, 3.90, "unitised curtain-wall module 1.5 m wide × 3.9 m floor-to-floor with mullions and spandrel"),
    ("bay_window", 2.40, 2.10, "three-sided projecting bay with three sashes (rowhouse / Queens 2-family)"),
    ("arched_tenement", 0.95, 1.95, "segmental-arched brick-headed opening with 1/1 sash (Old Law tenement)"),
    ("dormer", 1.00, 1.40, "gabled dormer with 6/6 sash on a pitched roof (Federal rowhouse / Tudor)"),
    ("aluminum_slider", 1.20, 1.40, "post-war aluminium horizontal slider in white glazed brick / NYCHA openings"),
    ("picture_window", 1.80, 1.40, "1950s picture window with flanking sashes (Queens / Staten Island detached)"),
    ("gothic_arched", 1.20, 3.60, "pointed-arch traceried church window"),
    ("ribbon_strip", 3.00, 1.50, "continuous horizontal ribbon window band (1960s school / garage / modern)"),
    ("chicago_tripartite", 2.40, 2.20, "wide fixed centre light with narrow double-hung flankers (early office / loft 1895–1915)"),
    ("through_wall_ac_sleeve", 0.66, 0.42, "through-wall AC sleeve opening below window ('Fedders special', 2000s infill)"),
)
WINDOW_TYPE_NAMES: tuple[str, ...] = tuple(w[0] for w in WINDOW_TYPES)
WINDOW_TYPE_INDEX: dict[str, int] = {n: i for i, n in enumerate(WINDOW_TYPE_NAMES)}


# --------------------------------------------------------------------------- storefront kinds (DATA_CONTRACTS §5 storefront_kinds)
STOREFRONT_KINDS: tuple[str, ...] = (
    "bodega", "deli", "pharmacy", "restaurant", "bar", "nail_hair", "laundromat", "bank", "clothing", "electronics", "grocery",
    "hardware", "coffee", "pizza", "dry_cleaner", "generic_retail", "office_lobby", "residential_lobby", "garage_door", "vacant",
)
STOREFRONT_KIND_INDEX: dict[str, int] = {n: i for i, n in enumerate(STOREFRONT_KINDS)}
# Interior shell kit piece used for each kind (8 modelled interiors; the rest reuse the nearest one — stated in the kit report).
STOREFRONT_INTERIOR_FOR_KIND: dict[str, str] = {
    "bodega": "bodega", "deli": "deli", "pharmacy": "pharmacy", "restaurant": "restaurant", "bar": "bar", "nail_hair": "nail_hair",
    "laundromat": "laundromat", "bank": "bank", "clothing": "generic_retail", "electronics": "generic_retail", "grocery": "bodega",
    "hardware": "generic_retail", "coffee": "deli", "pizza": "restaurant", "dry_cleaner": "laundromat", "generic_retail": "generic_retail",
    "office_lobby": "lobby", "residential_lobby": "lobby", "garage_door": "", "vacant": "vacant",
}
STOREFRONT_INTERIOR_KINDS: tuple[str, ...] = ("bodega", "deli", "pharmacy", "restaurant", "bar", "nail_hair", "laundromat", "bank", "generic_retail", "lobby", "vacant")
STOREFRONT_BAY_WIDTHS_M: tuple[float, ...] = (3.6, 4.8, 6.0)
STOREFRONT_GATE_STATES: tuple[str, ...] = ("closed", "half", "open")


# --------------------------------------------------------------------------- features / eras / boroughs
FEATURES: tuple[str, ...] = (
    "fire_escape", "cornice", "stoop", "storefront", "water_tower", "setbacks", "areaway_railing", "canopy", "parapet", "bulkhead",
    "balconies", "quoins", "pilasters", "string_course", "bay_windows", "dormers", "arched_windows", "corner_windows", "roll_gate",
    "awning", "ac_units", "through_wall_ac", "loading_dock", "columns", "spire", "rooftop_hvac", "billboard", "cell_antennas",
    "sidewalk_shed", "ivy", "lintels", "sills", "rustication", "mansard", "pitched_roof", "garage", "plaza", "curtain_wall",
)
BOROUGHS: dict[str, int] = {"MN": 1, "BX": 2, "BK": 3, "QN": 4, "SI": 5}
KIT_CATEGORIES: tuple[str, ...] = (
    "window", "window_accessory", "door_entry", "cornice", "string_course", "quoin", "pilaster", "storefront", "storefront_interior",
    "fire_escape", "parapet", "bulkhead", "water_tower", "hvac", "antenna", "billboard", "scaffold", "fence", "vegetation", "trim",
)


# --------------------------------------------------------------------------- facade classes
def load_facade_classes(path: Path | str = FACADE_CLASSES_PATH) -> list[dict[str, Any]]:
    """Load and validate ``facade_classes.json``. Returns the class list ordered by ``facade_class`` id (1-based, contiguous)."""
    with open(path) as f:
        doc = json.load(f)
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"facade_classes.json schema_version {doc.get('schema_version')} != {SCHEMA_VERSION}")
    classes = doc["classes"]
    problems = validate_facade_classes(classes)
    if problems:
        raise ValueError("facade_classes.json invalid:\n  " + "\n  ".join(problems))
    return sorted(classes, key=lambda c: c["facade_class"])


def validate_facade_classes(classes: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    ids = [c.get("facade_class") for c in classes]
    if sorted(ids) != list(range(1, len(classes) + 1)):
        problems.append(f"facade_class ids must be 1..{len(classes)} contiguous, got {sorted(ids)[:5]}...")
    seen: set[str] = set()
    req = ("id", "name", "era", "materials", "window_type", "floors_typical", "features", "boroughs_typical", "floor_height_m",
           "ground_floor_height_m", "pluto_classes_typical", "description")
    for c in classes:
        cid = c.get("id", "?")
        for k in req:
            if k not in c:
                problems.append(f"{cid}: missing {k}")
        if cid in seen:
            problems.append(f"duplicate id {cid}")
        seen.add(cid)
        for m in c.get("materials", []):
            if m not in MATERIAL_INDEX or MATERIAL_INDEX[m] >= CONTRACT_MATERIAL_COUNT:
                problems.append(f"{cid}: material {m!r} not in DATA_CONTRACTS §5 enum")
        if c.get("window_type") not in WINDOW_TYPE_INDEX:
            problems.append(f"{cid}: window_type {c.get('window_type')!r} unknown")
        for f_ in c.get("features", []):
            if f_ not in FEATURES:
                problems.append(f"{cid}: feature {f_!r} unknown")
        for b in c.get("boroughs_typical", []):
            if b not in BOROUGHS:
                problems.append(f"{cid}: borough {b!r} unknown")
        ft = c.get("floors_typical", [])
        if not (isinstance(ft, list) and len(ft) == 2 and 1 <= ft[0] <= ft[1] <= 120):
            problems.append(f"{cid}: floors_typical must be [min,max]")
        era = c.get("era", [])
        if not (isinstance(era, list) and len(era) == 2 and 1600 <= era[0] <= era[1] <= 2100):
            problems.append(f"{cid}: era must be [year_from, year_to]")
        for k in ("storefront_kinds_typical",):
            for s in c.get(k, []):
                if s not in STOREFRONT_KIND_INDEX:
                    problems.append(f"{cid}: storefront kind {s!r} unknown")
    return problems


def facade_class_index(classes: list[dict[str, Any]] | None = None) -> dict[str, int]:
    """id string -> facade_class int16."""
    classes = classes or load_facade_classes()
    return {c["id"]: int(c["facade_class"]) for c in classes}


def as_contract_dict() -> dict[str, Any]:
    """Machine-readable dump of every enum (written next to the kit catalog for UE / pipeline consumers)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "materials": list(MATERIALS), "contract_material_count": CONTRACT_MATERIAL_COUNT,
        "window_types": [{"index": i, "name": w[0], "opening_w_m": w[1], "opening_h_m": w[2], "description": w[3]} for i, w in enumerate(WINDOW_TYPES)],
        "storefront_kinds": list(STOREFRONT_KINDS), "storefront_interior_for_kind": STOREFRONT_INTERIOR_FOR_KIND,
        "storefront_bay_widths_m": list(STOREFRONT_BAY_WIDTHS_M), "storefront_gate_states": list(STOREFRONT_GATE_STATES),
        "features": list(FEATURES), "boroughs": BOROUGHS, "kit_categories": list(KIT_CATEGORIES),
    }


if __name__ == "__main__":  # quick self-check
    cls = load_facade_classes()
    print(f"{len(cls)} facade classes OK; {len(WINDOW_TYPES)} window types; {len(MATERIALS)} materials; {len(STOREFRONT_KINDS)} storefront kinds")
