"""Kit piece identifiers for ``tiles/{tile}/kit_placements.bin`` (DATA_CONTRACTS §6).

The record carries ``uint32 kit_id``; ``kit_catalog.json`` maps it to a glb path, category and bounds.  The Blender kit
agent generates the glbs; this module fixes the **numbering** so that both sides can be written independently and
reconciled:

    kit_id = (category_index + 1) * 1000 + piece_index

``category_index`` is the position in ``facade_params.KIT_CATEGORIES``; ``piece_index`` is the position of the piece
name in the tuple for that category below.  Piece names are exactly the vocabulary of ``facade_params`` (window types,
storefront kinds/gate states, cornice styles, features) so the mapping is by *name*, never by ordinal luck.

The registry is written to ``data/processed/facade/kit_ids.json`` on every run and reconciled with
``blender_out/kit/catalog/*.json`` by :mod:`nycsim_pipeline.facade.validate_placements` once the catalog exists.
``nominal_size_m`` is the published real size of the piece (metres, width x depth x height); the placement writer uses
it to keep pieces inside the footprint and the validator uses it to bound-check.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .enums import KIT_CATEGORIES, STOREFRONT_GATE_STATES, STOREFRONT_INTERIOR_KINDS, WINDOW_OPENING, WINDOW_TYPE_NAMES

#: Cornice styles named by ``facade_classes.json`` (``cornice_style``), in a fixed order.
CORNICE_STYLES: tuple[str, ...] = (
    "none_parapet", "pressed_metal_brackets", "pressed_metal_dentil", "stone_modillion", "brick_corbel",
    "wood_dentil", "wood_simple", "cast_iron_pediment",
)

#: category name -> ordered piece names. Sizes below are real published dimensions (see ``PIECE_SIZE``).
PIECES: dict[str, tuple[str, ...]] = {
    "window": WINDOW_TYPE_NAMES,
    "window_accessory": ("ac_unit_window", "ac_sleeve_through_wall", "window_guard", "flower_box", "shutter_pair",
                         "window_lit_curtain"),
    "door_entry": ("stoop_high_brownstone", "stoop_low_brick", "stoop_wood", "areaway_gate", "door_residential",
                   "door_residential_lobby", "door_office_lobby", "door_service", "garage_door_residential",
                   "garage_door_commercial", "canopy_entry"),
    "cornice": CORNICE_STYLES,
    "string_course": ("string_course_stone", "string_course_brick", "belt_course_terracotta"),
    "quoin": ("quoin_limestone", "quoin_brick"),
    "pilaster": ("pilaster_brick", "pilaster_stone", "pilaster_cast_iron", "column_stone"),
    "storefront": ("storefront_bay_3_6", "storefront_bay_4_8", "storefront_bay_6_0", "storefront_door",
                   "roll_gate_closed", "roll_gate_half", "roll_gate_open", "awning_fabric", "sign_band",
                   "sidewalk_cellar_door", "loading_dock_door"),
    "storefront_interior": STOREFRONT_INTERIOR_KINDS,
    "fire_escape": ("fire_escape_balcony", "fire_escape_stair", "fire_escape_drop_ladder", "fire_escape_roof_ladder"),
    "parapet": ("parapet_brick", "parapet_stone", "parapet_concrete", "setback_terrace"),
    "bulkhead": ("bulkhead_stair", "bulkhead_elevator", "bulkhead_mechanical"),
    "water_tower": ("water_tower_wood_10k", "water_tower_wood_20k", "water_tower_steel"),
    "hvac": ("rooftop_ac_small", "rooftop_ac_large", "cooling_tower", "exhaust_fan", "vent_pipe", "satellite_dish",
             "roof_hatch"),
    "antenna": ("cell_antenna_panel", "cell_antenna_mast", "roof_antenna_mast"),
    "billboard": ("billboard_wall", "billboard_roof", "sign_vertical_blade"),
    "scaffold": ("sidewalk_shed_bay", "sidewalk_shed_end", "shed_light", "pipe_scaffold_bay"),
    "fence": ("areaway_railing", "stoop_railing", "roof_railing", "chain_link_panel"),
    "vegetation": ("ivy_panel", "roof_planter", "window_planter"),
    "trim": ("lintel_stone", "sill_stone", "lintel_soldier_brick", "cornice_bracket", "balcony_slab",
             "balcony_juliet", "dormer_gabled", "bay_window_3sided"),
}

#: Real nominal sizes, metres (width, depth, height). Window pieces take their opening from ``facade_params``.
PIECE_SIZE: dict[str, tuple[float, float, float]] = {
    "ac_unit_window": (0.66, 0.55, 0.42),           # a standard 5,000 BTU window unit
    "ac_sleeve_through_wall": (0.66, 0.45, 0.42),
    "window_guard": (0.95, 0.10, 0.70),
    "flower_box": (0.90, 0.25, 0.25),
    "shutter_pair": (1.10, 0.06, 1.70),
    "window_lit_curtain": (0.95, 0.05, 1.70),
    "stoop_high_brownstone": (1.60, 4.20, 2.60),    # 20 ft lot: stoop projects ~14 ft to the areaway
    "stoop_low_brick": (1.50, 1.80, 0.80),
    "stoop_wood": (1.40, 1.60, 0.70),
    "areaway_gate": (1.10, 0.08, 1.20),
    "door_residential": (0.95, 0.12, 2.10),
    "door_residential_lobby": (1.90, 0.30, 2.60),
    "door_office_lobby": (3.00, 0.40, 3.20),
    "door_service": (0.90, 0.12, 2.10),
    "garage_door_residential": (2.75, 0.20, 2.20),  # single-car residential overhead door
    "garage_door_commercial": (3.60, 0.25, 3.60),
    "canopy_entry": (3.60, 3.00, 0.60),
    "none_parapet": (2.00, 0.35, 0.90),
    "pressed_metal_brackets": (2.00, 0.55, 0.80),
    "pressed_metal_dentil": (2.00, 0.45, 0.65),
    "stone_modillion": (2.00, 0.70, 1.00),
    "brick_corbel": (2.00, 0.30, 0.55),
    "wood_dentil": (2.00, 0.40, 0.50),
    "wood_simple": (2.00, 0.25, 0.35),
    "cast_iron_pediment": (2.00, 0.60, 1.20),
    "string_course_stone": (2.00, 0.12, 0.25),
    "string_course_brick": (2.00, 0.08, 0.20),
    "belt_course_terracotta": (2.00, 0.14, 0.30),
    "quoin_limestone": (0.45, 0.10, 0.60),
    "quoin_brick": (0.40, 0.08, 0.55),
    "pilaster_brick": (0.50, 0.15, 3.00),
    "pilaster_stone": (0.60, 0.20, 3.00),
    "pilaster_cast_iron": (0.35, 0.20, 3.60),
    "column_stone": (0.90, 0.90, 6.00),
    "storefront_bay_3_6": (3.60, 0.30, 3.20),
    "storefront_bay_4_8": (4.80, 0.30, 3.20),
    "storefront_bay_6_0": (6.00, 0.30, 3.20),
    "storefront_door": (1.10, 0.15, 2.30),
    "roll_gate_closed": (3.60, 0.18, 3.00),
    "roll_gate_half": (3.60, 0.18, 3.00),
    "roll_gate_open": (3.60, 0.22, 0.45),
    "awning_fabric": (3.60, 1.40, 0.70),
    "sign_band": (3.60, 0.15, 0.75),
    "sidewalk_cellar_door": (1.50, 1.20, 0.20),
    "loading_dock_door": (3.00, 0.25, 3.00),
    "fire_escape_balcony": (2.40, 1.10, 2.90),      # NYC iron balcony: 3 ft 6 in deep, one storey tall
    "fire_escape_stair": (0.75, 1.10, 3.00),
    "fire_escape_drop_ladder": (0.60, 0.25, 3.60),
    "fire_escape_roof_ladder": (0.60, 0.30, 2.40),
    "parapet_brick": (2.00, 0.35, 1.10),
    "parapet_stone": (2.00, 0.40, 1.10),
    "parapet_concrete": (2.00, 0.25, 1.10),
    "setback_terrace": (3.00, 3.00, 1.10),
    "bulkhead_stair": (3.20, 3.60, 2.60),
    "bulkhead_elevator": (3.60, 3.60, 4.20),
    "bulkhead_mechanical": (4.50, 4.50, 3.00),
    "water_tower_wood_10k": (3.40, 3.40, 8.50),     # 10,000 gal redwood/cedar tank on a steel stand
    "water_tower_wood_20k": (4.30, 4.30, 10.50),
    "water_tower_steel": (4.00, 4.00, 9.00),
    "rooftop_ac_small": (1.20, 0.90, 0.90),
    "rooftop_ac_large": (3.00, 2.20, 1.80),
    "cooling_tower": (3.60, 2.40, 3.00),
    "exhaust_fan": (0.90, 0.90, 0.70),
    "vent_pipe": (0.25, 0.25, 1.20),
    "satellite_dish": (0.80, 0.80, 0.90),
    "roof_hatch": (1.00, 1.20, 0.30),
    "cell_antenna_panel": (0.30, 0.20, 1.90),
    "cell_antenna_mast": (0.60, 0.60, 4.00),
    "roof_antenna_mast": (0.40, 0.40, 6.00),
    "billboard_wall": (12.00, 0.40, 6.00),
    "billboard_roof": (14.00, 0.60, 7.00),
    "sign_vertical_blade": (0.90, 0.25, 3.00),
    "sidewalk_shed_bay": (2.40, 1.80, 3.60),        # DOB sidewalk shed: 8 ft bay, 6 ft deep, 12 ft clear
    "sidewalk_shed_end": (0.20, 1.80, 3.60),
    "shed_light": (0.35, 0.35, 0.25),
    "pipe_scaffold_bay": (2.40, 0.90, 2.00),
    "areaway_railing": (2.00, 0.08, 1.05),
    "stoop_railing": (1.60, 0.08, 0.95),
    "roof_railing": (2.00, 0.08, 1.10),
    "chain_link_panel": (3.00, 0.06, 1.80),
    "ivy_panel": (2.00, 0.15, 3.00),
    "roof_planter": (1.20, 0.60, 0.60),
    "window_planter": (0.90, 0.30, 0.30),
    "lintel_stone": (1.35, 0.12, 0.22),
    "sill_stone": (1.25, 0.18, 0.12),
    "lintel_soldier_brick": (1.20, 0.10, 0.20),
    "cornice_bracket": (0.30, 0.45, 0.60),
    "balcony_slab": (3.00, 1.60, 1.10),
    "balcony_juliet": (1.20, 0.30, 1.05),
    "dormer_gabled": (1.40, 1.20, 1.80),
    "bay_window_3sided": (2.40, 0.80, 2.10),
}

# storefront interior shells: a full shop-depth box behind the glass
for _k in STOREFRONT_INTERIOR_KINDS:
    PIECE_SIZE.setdefault(_k, (4.80, 8.00, 3.20))
# window pieces: opening size from facade_params (depth is the reveal)
for _w, (_ow, _oh) in WINDOW_OPENING.items():
    PIECE_SIZE.setdefault(_w, (_ow, 0.30, _oh))
assert set(STOREFRONT_GATE_STATES) <= {"closed", "half", "open"}


def _build_ids() -> tuple[dict[tuple[str, str], int], dict[int, tuple[str, str]]]:
    fwd: dict[tuple[str, str], int] = {}
    rev: dict[int, tuple[str, str]] = {}
    for cat, names in PIECES.items():
        if cat not in KIT_CATEGORIES:
            raise ValueError(f"kit category {cat!r} is not in facade_params.KIT_CATEGORIES")
        base = (KIT_CATEGORIES.index(cat) + 1) * 1000
        for i, nm in enumerate(names):
            if i >= 1000:
                raise ValueError(f"category {cat} exceeds 1000 pieces")
            kid = base + i
            fwd[(cat, nm)] = kid
            rev[kid] = (cat, nm)
    return fwd, rev


KIT_ID, KIT_PIECE = _build_ids()


def kit_id(category: str, name: str) -> int:
    """Kit id for a piece, raising when the pair is not registered (never returns a silent default)."""
    try:
        return KIT_ID[(category, name)]
    except KeyError as exc:
        raise KeyError(f"unregistered kit piece {category}/{name}") from exc


def window_kit_ids() -> list[int]:
    return [kit_id("window", n) for n in WINDOW_TYPE_NAMES]


def registry() -> dict:
    """Machine-readable registry written next to the processed data and reconciled with the Blender catalog."""
    return {
        "schema_version": 1,
        "id_formula": "kit_id = (index of category in facade_params.KIT_CATEGORIES + 1) * 1000 + index of piece name",
        "categories": list(KIT_CATEGORIES),
        "pieces": [
            {"kit_id": kid, "category": cat, "name": nm, "nominal_size_m": list(PIECE_SIZE[nm])}
            for (cat, nm), kid in sorted(KIT_ID.items(), key=lambda kv: kv[1])
        ],
    }


def write_registry(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(registry(), f, indent=1, sort_keys=False)
    tmp.replace(path)
    return path


def names_of(ids: Iterable[int]) -> list[str]:
    return [f"{KIT_PIECE[i][0]}/{KIT_PIECE[i][1]}" if i in KIT_PIECE else f"unknown:{i}" for i in ids]


# --- placement flags (DATA_CONTRACTS §6) --------------------------------------------------------------------------------
FLAG_LIT = 1 << 0
FLAG_ANIMATED = 1 << 1
FLAG_INTERIOR = 1 << 2
