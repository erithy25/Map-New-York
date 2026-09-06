"""Kit piece identifiers for ``tiles/{tile}/kit_placements.bin`` (DATA_CONTRACTS §6).

The record carries ``uint32 kit_id``; the engine has to resolve it to a real ``.glb``.  **The exported Blender kit
catalog is the authority on what exists**, so the numbering is derived *from* ``blender_out/kit/catalog/*.json``:

    kit_id = (index of the piece's category in facade_params.KIT_CATEGORIES + 1) * 200
             + index of the catalog id inside that category, catalog ids sorted lexicographically

so every id names an asset that has actually been exported.  With 20 categories and at most 200 pieces each the ids
stay inside 200..4199.  The registry is written to ``data/processed/facade/kit_ids.json`` with, for every piece, its
``kit_id``, ``category``, ``catalog_id`` (verbatim from the catalog) and ``glb`` (the path the catalog records).

The placement code refers to pieces by a **semantic role** — "the piece that models a high brownstone stoop" — not by
a catalog id, so a rename on the kit side is a one-line change here.  :data:`ROLE_TO_CATALOG` is that reviewed mapping.
A role whose catalog entry does not exist is a real gap: :func:`kit_id` raises, :func:`has_piece` reports it, and the
placer skips those placements rather than emitting an id that resolves to nothing.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from ..paths import BLENDER_OUT
from .enums import KIT_CATEGORIES

CATALOG_DIR = BLENDER_OUT / "kit" / "catalog"
KIT_ID_STRIDE = 200
KIT_ID_MAX = (len(KIT_CATEGORIES) + 1) * KIT_ID_STRIDE

#: Cornice styles named by ``facade_classes.json`` (``cornice_style``), in a fixed order; the placer indexes this list.
CORNICE_STYLES: tuple[str, ...] = (
    "none_parapet", "pressed_metal_brackets", "pressed_metal_dentil", "stone_modillion", "brick_corbel",
    "wood_dentil", "wood_simple", "cast_iron_pediment",
)

#: Semantic role -> the exported catalog id that models it.  Reviewed against ``blender_out/kit/catalog`` by hand.
#: A window role maps to ``win_<window family>``; the rest are the nearest modelled piece, named explicitly so the
#: substitution is visible rather than implied.
ROLE_TO_CATALOG: dict[tuple[str, str], str] = {
    **{("window", n): f"win_{n}" for n in
       ("double_hung_1_1", "double_hung_1_1_stone", "double_hung_1_1_soldier", "double_hung_2_2", "double_hung_6_6",
        "casement_pair", "steel_industrial_4x5", "punched_office", "curtain_wall_module", "bay_window",
        "arched_tenement", "dormer", "aluminum_slider", "picture_window", "gothic_arched", "ribbon_strip",
        "chicago_tripartite", "through_wall_ac_sleeve")},
    ("window_accessory", "ac_unit_window"): "acc_ac_window_medium",
    ("window_accessory", "ac_unit_window_small"): "acc_ac_window_small",
    ("window_accessory", "ac_unit_window_large"): "acc_ac_window_large",
    ("window_accessory", "ac_sleeve_through_wall"): "acc_through_wall_ac_unit",
    ("window_accessory", "ac_bracket"): "acc_ac_bracket",
    ("window_accessory", "window_guard"): "acc_window_guard_security",
    ("window_accessory", "window_guard_child"): "acc_window_guard_child",
    ("window_accessory", "flower_box"): "acc_flower_box",
    ("window_accessory", "blinds_half"): "acc_blinds_half",
    ("window_accessory", "curtains_open"): "acc_curtains_open",
    ("window_accessory", "curtains_closed"): "acc_curtains_closed",
    ("window_accessory", "roller_shade"): "acc_roller_shade",
    ("window_accessory", "interior_card_lit"): "acc_interior_card_lit",
    ("window_accessory", "interior_card_unlit"): "acc_interior_card_unlit",
    ("door_entry", "stoop_high_brownstone"): "entry_stoop_brownstone_10",
    ("door_entry", "stoop_low_brick"): "entry_stoop_tenement_4",
    ("door_entry", "stoop_wood"): "entry_stoop_tenement_4",
    ("door_entry", "brownstone_door_surround"): "entry_brownstone_door_surround",
    ("door_entry", "areaway_gate"): "entry_areaway_railing",
    ("door_entry", "door_residential"): "entry_door_single_panel",
    ("door_entry", "door_residential_lobby"): "entry_apartment_lobby_glass",
    ("door_entry", "door_office_lobby"): "entry_double_doors",
    ("door_entry", "door_church"): "entry_church_doors",
    ("door_entry", "door_service"): "entry_service_door_steel",
    ("door_entry", "garage_door_residential"): "entry_garage_door",
    ("door_entry", "garage_door_commercial"): "entry_loft_roll_gate",
    ("door_entry", "canopy_entry"): "entry_lobby_canopy",
    ("door_entry", "cellar_hatch"): "entry_cellar_hatch",
    ("cornice", "none_parapet"): "parapet_cap_metal_coping",
    ("cornice", "pressed_metal_brackets"): "cornice_pressed_metal_a",
    ("cornice", "pressed_metal_dentil"): "cornice_pressed_metal_b",
    ("cornice", "stone_modillion"): "cornice_stone",
    ("cornice", "brick_corbel"): "cornice_brick_corbel",
    ("cornice", "wood_dentil"): "cornice_pressed_metal_c",
    ("cornice", "wood_simple"): "cornice_pressed_metal_c",
    ("cornice", "cast_iron_pediment"): "cornice_pressed_metal_a",
    ("cornice", "cornice_return_end"): "cornice_return_end",
    ("cornice", "cornice_bracket"): "cornice_bracket",
    ("string_course", "string_course_stone"): "string_course_stone_belt",
    ("string_course", "string_course_brick"): "string_course_brick_soldier",
    ("string_course", "belt_course_terracotta"): "string_course_terracotta_band",
    ("string_course", "dentil_course"): "string_course_dentil",
    ("quoin", "quoin_limestone"): "quoin_limestone",
    ("quoin", "quoin_brownstone"): "quoin_brownstone",
    ("quoin", "quoin_brick"): "quoin_brick_rusticated",
    ("pilaster", "pilaster_brick"): "pilaster_brick",
    ("pilaster", "pilaster_stone"): "pilaster_stone_fluted",
    ("pilaster", "pilaster_cast_iron"): "pilaster_cast_iron",
    ("pilaster", "column_stone"): "pilaster_storefront_column",
    ("storefront", "storefront_bay_3_6"): "storefront_bay_36",
    ("storefront", "storefront_bay_4_8"): "storefront_bay_48",
    ("storefront", "storefront_bay_6_0"): "storefront_bay_60",
    ("storefront", "storefront_door"): "entry_double_doors",
    ("storefront", "roll_gate_closed_3_6"): "storefront_gate_36_closed",
    ("storefront", "roll_gate_closed_4_8"): "storefront_gate_48_closed",
    ("storefront", "roll_gate_closed_6_0"): "storefront_gate_60_closed",
    ("storefront", "roll_gate_half_3_6"): "storefront_gate_36_half",
    ("storefront", "roll_gate_half_4_8"): "storefront_gate_48_half",
    ("storefront", "roll_gate_half_6_0"): "storefront_gate_60_half",
    ("storefront", "roll_gate_open_3_6"): "storefront_gate_36_open",
    ("storefront", "roll_gate_open_4_8"): "storefront_gate_48_open",
    ("storefront", "roll_gate_open_6_0"): "storefront_gate_60_open",
    ("storefront", "grille_3_6"): "storefront_grille_36",
    ("storefront", "grille_4_8"): "storefront_grille_48",
    ("storefront", "grille_6_0"): "storefront_grille_60",
    ("storefront", "awning_3_6"): "storefront_awning_36",
    ("storefront", "awning_4_8"): "storefront_awning_48",
    ("storefront", "awning_6_0"): "storefront_awning_60",
    ("storefront", "sign_band"): "storefront_sign_projecting",
    ("storefront", "loading_dock_door"): "entry_loft_roll_gate",
    **{("storefront_interior", n): f"storefront_interior_{n}" for n in
       ("bodega", "deli", "pharmacy", "restaurant", "bar", "nail_hair", "laundromat", "bank", "generic_retail",
        "lobby", "vacant")},
    ("fire_escape", "fire_escape_balcony"): "fire_escape_floor_unit",
    ("fire_escape", "fire_escape_balcony_wide"): "fire_escape_floor_unit_wide",
    ("fire_escape", "fire_escape_balcony_top"): "fire_escape_balcony_top",
    ("fire_escape", "fire_escape_corner_return"): "fire_escape_corner_return",
    ("fire_escape", "fire_escape_drop_ladder"): "fire_escape_drop_ladder",
    ("fire_escape", "fire_escape_roof_ladder"): "fire_escape_top_hook",
    ("parapet", "parapet_brick"): "parapet_wall_brick",
    ("parapet", "parapet_stone"): "parapet_cap_stone",
    ("parapet", "parapet_concrete"): "parapet_cap_metal_coping",
    ("parapet", "parapet_terracotta"): "parapet_cap_terracotta",
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
    ("hvac", "condenser_bank"): "hvac_condenser_bank",
    ("hvac", "exhaust_fan"): "hvac_exhaust_fan",
    ("hvac", "vent_pipe"): "hvac_vent_pipe_cluster",
    ("hvac", "chimney_brick"): "hvac_chimney_brick",
    ("hvac", "satellite_dish"): "acc_satellite_dish",
    ("antenna", "cell_antenna_panel"): "antenna_cell_panel_array",
    ("antenna", "cell_antenna_mast"): "antenna_whip_mast",
    ("antenna", "roof_antenna_yagi"): "antenna_tv_yagi",
    ("antenna", "roof_satellite_dish"): "antenna_satellite_dish_roof",
    ("billboard", "billboard_wall"): "billboard_wall_mounted",
    ("billboard", "billboard_roof"): "billboard_rooftop",
    ("scaffold", "sidewalk_shed_bay"): "sidewalk_shed_module",
    ("scaffold", "sidewalk_shed_end"): "sidewalk_shed_corner",
    ("scaffold", "pipe_scaffold_bay"): "scaffold_pipe_bay",
    ("fence", "areaway_railing"): "fence_iron_areaway",
    ("fence", "stoop_railing"): "fence_iron_areaway",
    ("fence", "roof_railing"): "fence_iron_areaway",
    ("fence", "chain_link_panel"): "construction_fence_chainlink",
    ("fence", "plywood_panel"): "construction_fence_plywood",
    ("vegetation", "ivy_panel"): "ivy_panel_dense",
    ("vegetation", "ivy_panel_sparse"): "ivy_panel_sparse",
    ("vegetation", "roof_planter"): "roof_weeds_patch",
    ("vegetation", "window_planter"): "acc_flower_box",
    ("trim", "lintel_stone"): "trim_lintel_stone",
    ("trim", "sill_stone"): "trim_sill_cast_stone",
    ("trim", "keystone"): "trim_keystone",
    ("trim", "water_table"): "trim_water_table",
    ("trim", "corner_bead_brick"): "trim_corner_bead_brick",
    ("trim", "datestone_plaque"): "trim_datestone_plaque",
    ("trim", "dormer_gabled"): "win_dormer",
    ("trim", "bay_window_3sided"): "win_bay_window",
}


class KitCatalogMissing(FileNotFoundError):
    """Raised when the exported Blender kit catalog is not on disk."""


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    """``catalog_id -> catalog entry`` from ``blender_out/kit/catalog/*.json``."""
    if not CATALOG_DIR.exists():
        raise KitCatalogMissing(
            f"{CATALOG_DIR} missing: the Blender kit agent exports it; the facade stage numbers its kit ids from it")
    out: dict[str, dict] = {}
    for p in sorted(CATALOG_DIR.glob("*.json")):
        with open(p) as f:
            d = json.load(f)
        cid = str(d.get("id") or p.stem)
        cat = str(d.get("category") or "")
        if cat not in KIT_CATEGORIES:
            raise ValueError(f"catalog entry {cid!r} has category {cat!r}, not one of facade_params.KIT_CATEGORIES")
        out[cid] = d
    if not out:
        raise KitCatalogMissing(f"{CATALOG_DIR} holds no catalog entries")
    return out


@lru_cache(maxsize=1)
def _numbering() -> tuple[dict[str, int], dict[int, str]]:
    """``catalog_id -> kit_id`` and its inverse, derived from the exported catalog."""
    cat = catalog()
    by_category: dict[str, list[str]] = {}
    for cid, entry in cat.items():
        by_category.setdefault(str(entry["category"]), []).append(cid)
    fwd: dict[str, int] = {}
    rev: dict[int, str] = {}
    for category, ids in by_category.items():
        base = (KIT_CATEGORIES.index(category) + 1) * KIT_ID_STRIDE
        ids = sorted(ids)
        if len(ids) > KIT_ID_STRIDE:
            raise ValueError(f"category {category} exports {len(ids)} pieces, more than the {KIT_ID_STRIDE} stride")
        for i, cid in enumerate(ids):
            fwd[cid] = base + i
            rev[base + i] = cid
    return fwd, rev


def kit_id_of_catalog(catalog_id: str) -> int:
    return _numbering()[0][catalog_id]


def catalog_of_kit_id(kid: int) -> str:
    return _numbering()[1][int(kid)]


def kit_id(category: str, role: str) -> int:
    """Numeric kit id for a semantic role, raising when the kit does not export a piece for it."""
    cid = ROLE_TO_CATALOG.get((category, role))
    if not cid:
        raise KeyError(f"no kit piece is mapped to the role {category}/{role}")
    fwd = _numbering()[0]
    if cid not in fwd:
        raise KeyError(f"role {category}/{role} maps to catalog id {cid!r}, which the kit has not exported")
    return fwd[cid]


def has_piece(category: str, role: str) -> bool:
    try:
        kit_id(category, role)
        return True
    except (KeyError, KitCatalogMissing):
        return False


def piece_size(kid: int) -> tuple[float, float, float]:
    """Nominal size of a piece, metres (width, depth, height), as the exporting catalog measured it."""
    entry = catalog()[catalog_of_kit_id(kid)]
    s = entry.get("nominal_size_m") or entry.get("measured_size_m") or [0.0, 0.0, 0.0]
    return float(s[0]), float(s[1]), float(s[2])


def piece_info(kid: int) -> dict:
    cid = catalog_of_kit_id(int(kid))
    e = catalog()[cid]
    return {"kit_id": int(kid), "catalog_id": cid, "category": e.get("category", ""), "glb": e.get("glb", "")}


def unmapped_roles() -> list[dict]:
    """Roles the placer may need for which the kit exports nothing — a real gap, reported not hidden."""
    fwd = _numbering()[0]
    out = []
    for (cat, role), cid in sorted(ROLE_TO_CATALOG.items()):
        if not cid or cid not in fwd:
            out.append({"category": cat, "role": role, "catalog_id": cid})
    return out


def registry() -> dict:
    """The machine-readable registry written to ``data/processed/facade/kit_ids.json``."""
    cat = catalog()
    fwd = _numbering()[0]
    roles: dict[str, list[str]] = {}
    for (c, role), cid in ROLE_TO_CATALOG.items():
        if cid in fwd:
            roles.setdefault(cid, []).append(f"{c}/{role}")
    pieces = []
    for cid, kid in sorted(fwd.items(), key=lambda kv: kv[1]):
        e = cat[cid]
        pieces.append({
            "kit_id": kid,
            "category": e.get("category", ""),
            "catalog_id": cid,
            "name": cid,
            "glb": e.get("glb", ""),
            "nominal_size_m": list(e.get("nominal_size_m") or e.get("measured_size_m") or [0.0, 0.0, 0.0]),
            "roles": sorted(roles.get(cid, [])),
        })
    return {
        "schema_version": 2,
        "source": "blender_out/kit/catalog/*.json (the exported kit is the authority on what exists)",
        "id_formula": "kit_id = (index of category in facade_params.KIT_CATEGORIES + 1) * 200 "
                      "+ index of the catalog id inside that category, catalog ids sorted lexicographically",
        "id_stride": KIT_ID_STRIDE,
        "categories": list(KIT_CATEGORIES),
        "catalog_entries": len(cat),
        "pieces": pieces,
        "roles_without_a_kit_piece": unmapped_roles(),
    }


def write_registry(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(registry(), f, indent=1)
    tmp.replace(path)
    return path


def names_of(ids: Iterable[int]) -> list[str]:
    rev = _numbering()[1]
    return [rev.get(int(i), f"unknown:{int(i)}") for i in ids]


# --- placement flags (DATA_CONTRACTS §6) --------------------------------------------------------------------------------
FLAG_LIT = 1 << 0
FLAG_ANIMATED = 1 << 1
FLAG_INTERIOR = 1 << 2
