"""Enum bridge between the pipeline and the Blender facade kit.

``blender/common/facade_params.py`` is the single source of truth for the integer enums of DATA_CONTRACTS §5
(``material_primary``, ``window_type``, ``storefront_kinds``, ``facade_class``) and ``facade_classes.json`` next to it
is the typology table.  ``blender/common`` is not an installable package, so it is loaded by file path here; the loaded
module is validated against the contract enum on import (the material list must start with the 17 §5 materials in the
documented order).

Everything else in this module is *facade-stage* data: the real bay spacing per window family, the mapping from OSM
``building:material`` / ``building:colour`` and from LPC designation-report material strings onto the §5 material enum,
and the deterministic hash used by every downstream random choice.
"""
from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from ..paths import REPO_ROOT

log = logging.getLogger("nycsim.facade.enums")

BLENDER_COMMON = Path(REPO_ROOT) / "blender" / "common"
FACADE_PARAMS_PATH = BLENDER_COMMON / "facade_params.py"
FACADE_CLASSES_PATH = BLENDER_COMMON / "facade_classes.json"

# DATA_CONTRACTS §5 ``material_primary`` enum, verbatim. facade_params.MATERIALS must start with exactly this.
CONTRACT_MATERIALS: tuple[str, ...] = (
    "red_brick", "brown_brick", "tan_brick", "white_glazed_brick", "brownstone", "limestone", "terracotta", "cast_iron",
    "glass_curtain", "concrete", "stucco", "vinyl_siding", "wood_clapboard", "stone_rubble", "metal_panel", "granite", "precast",
)
# DATA_CONTRACTS §5 ``storefront_kinds`` enum, verbatim.
CONTRACT_STOREFRONT_KINDS: tuple[str, ...] = (
    "bodega", "deli", "pharmacy", "restaurant", "bar", "nail_hair", "laundromat", "bank", "clothing", "electronics", "grocery",
    "hardware", "coffee", "pizza", "dry_cleaner", "generic_retail", "office_lobby", "residential_lobby", "garage_door", "vacant",
)


def _load_facade_params() -> ModuleType:
    if not FACADE_PARAMS_PATH.exists():
        raise FileNotFoundError(f"{FACADE_PARAMS_PATH} missing: the Blender kit agent owns this file")
    name = "nycsim_blender_facade_params"
    mod = sys.modules.get(name)
    if mod is None:
        spec = importlib.util.spec_from_file_location(name, FACADE_PARAMS_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {FACADE_PARAMS_PATH}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    got = tuple(mod.MATERIALS[: len(CONTRACT_MATERIALS)])
    if got != CONTRACT_MATERIALS:
        raise ValueError(f"facade_params.MATERIALS does not start with the DATA_CONTRACTS §5 enum: {got}")
    if tuple(mod.STOREFRONT_KINDS) != CONTRACT_STOREFRONT_KINDS:
        raise ValueError("facade_params.STOREFRONT_KINDS differs from the DATA_CONTRACTS §5 enum")
    return mod


FP = _load_facade_params()

MATERIALS: tuple[str, ...] = tuple(FP.MATERIALS)
MATERIAL_INDEX: dict[str, int] = dict(FP.MATERIAL_INDEX)
WINDOW_TYPE_NAMES: tuple[str, ...] = tuple(FP.WINDOW_TYPE_NAMES)
WINDOW_TYPE_INDEX: dict[str, int] = dict(FP.WINDOW_TYPE_INDEX)
WINDOW_OPENING: dict[str, tuple[float, float]] = {w[0]: (float(w[1]), float(w[2])) for w in FP.WINDOW_TYPES}
STOREFRONT_KINDS: tuple[str, ...] = tuple(FP.STOREFRONT_KINDS)
STOREFRONT_KIND_INDEX: dict[str, int] = dict(FP.STOREFRONT_KIND_INDEX)
STOREFRONT_INTERIOR_KINDS: tuple[str, ...] = tuple(FP.STOREFRONT_INTERIOR_KINDS)
STOREFRONT_INTERIOR_FOR_KIND: dict[str, str] = dict(FP.STOREFRONT_INTERIOR_FOR_KIND)
STOREFRONT_BAY_WIDTHS_M: tuple[float, ...] = tuple(float(v) for v in FP.STOREFRONT_BAY_WIDTHS_M)
STOREFRONT_GATE_STATES: tuple[str, ...] = tuple(FP.STOREFRONT_GATE_STATES)
FEATURES: tuple[str, ...] = tuple(FP.FEATURES)
KIT_CATEGORIES: tuple[str, ...] = tuple(FP.KIT_CATEGORIES)
BOROUGH_ABBREV: dict[str, int] = dict(FP.BOROUGHS)
BOROUGH_OF_CODE: dict[int, str] = {v: k for k, v in BOROUGH_ABBREV.items()}


# --- material enum shorthands (DATA_CONTRACTS §5) ---------------------------------------------------------------------
RED_BRICK, BROWN_BRICK, TAN_BRICK, WHITE_GLAZED_BRICK = 0, 1, 2, 3
BROWNSTONE, LIMESTONE, TERRACOTTA, CAST_IRON = 4, 5, 6, 7
GLASS_CURTAIN, CONCRETE, STUCCO, VINYL_SIDING = 8, 9, 10, 11
WOOD_CLAPBOARD, STONE_RUBBLE, METAL_PANEL, GRANITE, PRECAST = 12, 13, 14, 15, 16
N_CONTRACT_MATERIALS = len(CONTRACT_MATERIALS)

# --- storefront kind shorthands ---------------------------------------------------------------------------------------
SK_BODEGA, SK_DELI, SK_PHARMACY, SK_RESTAURANT, SK_BAR = 0, 1, 2, 3, 4
SK_NAIL_HAIR, SK_LAUNDROMAT, SK_BANK, SK_CLOTHING, SK_ELECTRONICS = 5, 6, 7, 8, 9
SK_GROCERY, SK_HARDWARE, SK_COFFEE, SK_PIZZA, SK_DRY_CLEANER = 10, 11, 12, 13, 14
SK_GENERIC_RETAIL, SK_OFFICE_LOBBY, SK_RESIDENTIAL_LOBBY, SK_GARAGE_DOOR, SK_VACANT = 15, 16, 17, 18, 19

# --- roof_type enum (DATA_CONTRACTS §5) -------------------------------------------------------------------------------
ROOF_FLAT, ROOF_GABLE, ROOF_HIP, ROOF_MANSARD, ROOF_SHED = 0, 1, 2, 3, 4
ROOF_SAWTOOTH, ROOF_COMPLEX, ROOF_DOME, ROOF_BARREL = 5, 6, 7, 8
ROOF_SOURCE_CITYGML, ROOF_SOURCE_OSM, ROOF_SOURCE_CLASS_RULE = 0, 1, 2

# ``roof`` string in facade_classes.json -> (roof_type enum, pitch degrees used by the shell/kit).
CLASS_ROOF_SHAPE: dict[str, tuple[int, float]] = {
    "flat_parapet": (ROOF_FLAT, 0.0),
    "flat_cornice": (ROOF_FLAT, 0.0),
    "flat_deck": (ROOF_FLAT, 0.0),
    "flat_mechanical": (ROOF_FLAT, 0.0),
    "setback_crown": (ROOF_FLAT, 0.0),
    "pitched_low": (ROOF_GABLE, 20.0),
    "pitched_dormer": (ROOF_GABLE, 38.0),
    "pitched_steep": (ROOF_GABLE, 45.0),
    "pitched_tile": (ROOF_HIP, 25.0),
}

# OSM ``roof:shape`` -> roof_type enum (real values seen in data/processed/osm/buildings.parquet).
OSM_ROOF_SHAPE: dict[str, int] = {
    "flat": ROOF_FLAT, "gabled": ROOF_GABLE, "gambrel": ROOF_GABLE, "saltbox": ROOF_GABLE,
    "double_saltbox": ROOF_GABLE, "quadruple_saltbox": ROOF_GABLE, "round_gabled": ROOF_GABLE,
    "hipped": ROOF_HIP, "half-hipped": ROOF_HIP, "hipped-and-gabled": ROOF_HIP, "pyramidal": ROOF_HIP,
    "mansard": ROOF_MANSARD, "skillion": ROOF_SHED, "lean_to": ROOF_SHED, "sawtooth": ROOF_SAWTOOTH,
    "dome": ROOF_DOME, "onion": ROOF_DOME, "cone": ROOF_DOME, "round": ROOF_BARREL, "barrel": ROOF_BARREL,
    "arched": ROOF_BARREL, "many": ROOF_COMPLEX,
}


# --- bay spacing ------------------------------------------------------------------------------------------------------
# Real NYC bay spacing per window family, metres, centre-to-centre. Calibrated against the published lot modules:
# a 25 ft (7.62 m) tenement lot carries 4 window bays -> 1.90 m; a 20 ft (6.10 m) brownstone lot carries 3 bays -> 2.03 m;
# a unitised curtain wall uses the 5 ft (1.52 m) module; a 1920s prewar apartment casement bay is 8 ft (2.44 m).
BAY_WIDTH_M: dict[str, float] = {
    "double_hung_1_1": 1.90,
    "double_hung_1_1_stone": 1.90,
    "double_hung_1_1_soldier": 1.90,
    "double_hung_2_2": 2.03,
    "double_hung_6_6": 1.95,
    "casement_pair": 2.44,
    "steel_industrial_4x5": 2.60,
    "punched_office": 2.60,
    "curtain_wall_module": 1.52,
    "bay_window": 3.05,
    "arched_tenement": 1.90,
    "dormer": 2.20,
    "aluminum_slider": 2.30,
    "picture_window": 3.20,
    "gothic_arched": 3.60,
    "ribbon_strip": 3.20,
    "chicago_tripartite": 3.20,
    "through_wall_ac_sleeve": 2.40,
}

# --- OSM material -> §5 material enum ---------------------------------------------------------------------------------
OSM_MATERIAL: dict[str, int] = {
    "brick": RED_BRICK, "bricks": RED_BRICK, "brick_block": RED_BRICK, "masonry": RED_BRICK,
    "red_brick": RED_BRICK, "brownstone": BROWNSTONE, "sandstone": BROWNSTONE,
    "glass": GLASS_CURTAIN, "mirror": GLASS_CURTAIN, "glass_curtain": GLASS_CURTAIN,
    "plaster": STUCCO, "stucco": STUCCO, "render": STUCCO, "cement_render": STUCCO,
    "metal": METAL_PANEL, "metal_plates": METAL_PANEL, "aluminium": METAL_PANEL, "aluminum": METAL_PANEL,
    "steel": METAL_PANEL, "corrugated_metal": METAL_PANEL, "copper": METAL_PANEL, "zinc": METAL_PANEL,
    "concrete": CONCRETE, "cement_block": CONCRETE, "cement_blocks": CONCRETE, "concrete_block": CONCRETE,
    "reinforced_concrete": CONCRETE, "precast_concrete": PRECAST,
    "stone": STONE_RUBBLE, "rubble": STONE_RUBBLE, "fieldstone": STONE_RUBBLE, "schist": STONE_RUBBLE,
    "limestone": LIMESTONE, "marble": LIMESTONE, "travertine": LIMESTONE,
    "granite": GRANITE, "terracotta": TERRACOTTA, "terra_cotta": TERRACOTTA,
    "cast_iron": CAST_IRON, "iron": CAST_IRON,
    "wood": WOOD_CLAPBOARD, "timber": WOOD_CLAPBOARD, "timber_framing": WOOD_CLAPBOARD, "clapboard": WOOD_CLAPBOARD,
    "vinyl": VINYL_SIDING, "vinyl_siding": VINYL_SIDING, "plastic": VINYL_SIDING,
    "tiles": TERRACOTTA, "ceramic": TERRACOTTA,
}

# --- LPC designation-report MATERIAL1 -> §5 material enum ---------------------------------------------------------------
# Matched token-wise on the lower-cased string; the first entry whose key appears as a whole word wins, so
# "Rusticated Limestone" -> limestone and "Buff Brick" -> tan brick.  Order matters (longest / most specific first).
LPC_MATERIAL_PATTERNS: tuple[tuple[str, int], ...] = (
    ("cast iron", CAST_IRON), ("cast-iron", CAST_IRON),
    ("brownstone", BROWNSTONE), ("brown stone", BROWNSTONE), ("sandstone", BROWNSTONE),
    ("terra cotta", TERRACOTTA), ("terra-cotta", TERRACOTTA), ("terracotta", TERRACOTTA),
    ("white glazed brick", WHITE_GLAZED_BRICK), ("glazed brick", WHITE_GLAZED_BRICK), ("white brick", WHITE_GLAZED_BRICK),
    ("buff brick", TAN_BRICK), ("yellow brick", TAN_BRICK), ("tan brick", TAN_BRICK), ("beige brick", TAN_BRICK),
    ("cream brick", TAN_BRICK), ("roman brick", TAN_BRICK), ("blond brick", TAN_BRICK),
    ("brown brick", BROWN_BRICK), ("iron-spot brick", BROWN_BRICK), ("iron spot brick", BROWN_BRICK),
    ("orange brick", BROWN_BRICK), ("gray brick", BROWN_BRICK), ("grey brick", BROWN_BRICK),
    ("red brick", RED_BRICK), ("philadelphia brick", RED_BRICK), ("flemish-bond brick", RED_BRICK),
    ("flemish bond brick", RED_BRICK), ("common bond brick", RED_BRICK), ("brick", RED_BRICK),
    ("vinyl", VINYL_SIDING), ("aluminum siding", VINYL_SIDING), ("asbestos", VINYL_SIDING),
    ("wood frame", WOOD_CLAPBOARD), ("wood shingle", WOOD_CLAPBOARD), ("clapboard", WOOD_CLAPBOARD),
    ("shingle", WOOD_CLAPBOARD), ("frame", WOOD_CLAPBOARD), ("wood", WOOD_CLAPBOARD),
    ("stucco", STUCCO), ("cement stucco", STUCCO), ("plaster", STUCCO),
    ("limestone", LIMESTONE), ("marble", LIMESTONE), ("white stone", LIMESTONE),
    ("granite", GRANITE), ("bluestone", GRANITE),
    ("concrete", CONCRETE), ("cinder block", CONCRETE),
    ("glass", GLASS_CURTAIN), ("curtain wall", GLASS_CURTAIN),
    ("steel", METAL_PANEL), ("metal", METAL_PANEL), ("iron", CAST_IRON),
    ("rusticated stone", STONE_RUBBLE), ("fieldstone", STONE_RUBBLE), ("rubble", STONE_RUBBLE),
    ("schist", STONE_RUBBLE), ("stone", STONE_RUBBLE), ("masonry", RED_BRICK),
)

# Named CSS colours that appear in OSM ``building:colour``.
NAMED_COLOURS: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255), "black": (0, 0, 0), "grey": (128, 128, 128), "gray": (128, 128, 128),
    "silver": (192, 192, 192), "red": (178, 34, 34), "brown": (139, 69, 19), "maroon": (128, 0, 0),
    "beige": (245, 222, 179), "tan": (210, 180, 140), "yellow": (240, 220, 130), "cream": (255, 253, 208),
    "orange": (200, 110, 40), "blue": (70, 90, 140), "green": (70, 110, 70), "darkgray": (80, 80, 80),
    "darkgrey": (80, 80, 80), "lightgray": (200, 200, 200), "lightgrey": (200, 200, 200), "sandstone": (190, 150, 110),
    "buff": (220, 200, 160), "brick": (150, 70, 50),
}
_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def parse_colour(value: str) -> tuple[int, int, int] | None:
    """OSM ``building:colour`` -> RGB, or None when unparseable."""
    if not value:
        return None
    v = value.strip().lower()
    named = NAMED_COLOURS.get(v.replace(" ", "").replace("_", ""))
    if named is not None:
        return named
    m = _HEX_RE.match(v)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def colour_to_masonry_material(rgb: tuple[int, int, int]) -> int | None:
    """Classify a real ``building:colour`` into the masonry shades of the §5 enum.

    Uses HSV: NYC brick shades separate cleanly by value/hue — glazed white brick is a near-neutral value > 0.82,
    buff/tan brick sits at hue 25-55 deg with value >= 0.55, brown brick at hue < 30 deg with value < 0.45, and the
    remaining warm hues are red brick.  Near-neutral mid/dark colours are concrete.  Returns None when no shade
    applies (e.g. a saturated blue), leaving the rule-derived material in place.
    """
    r, g, b = (c / 255.0 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    s = 0.0 if mx <= 0 else (mx - mn) / mx
    if mx == mn:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / (mx - mn))) % 360
    elif mx == g:
        h = 60 * ((b - r) / (mx - mn)) + 120
    else:
        h = 60 * ((r - g) / (mx - mn)) + 240
    if s < 0.14:
        if v >= 0.82:
            return WHITE_GLAZED_BRICK
        return CONCRETE
    if h > 70 and h < 330:          # green / blue / purple: not a masonry shade
        return None
    if v >= 0.86 and s < 0.24:
        return WHITE_GLAZED_BRICK
    if 22 <= h <= 60 and v >= 0.55:
        return TAN_BRICK
    if v < 0.46:
        return BROWN_BRICK
    if h < 22 or h >= 330:
        return RED_BRICK
    return BROWN_BRICK


def lpc_material_to_enum(value: str) -> int | None:
    """LPC building-database ``MATERIAL1`` -> §5 material enum, or None when the string carries no material."""
    if not value:
        return None
    v = " ".join(value.lower().replace("/", " ").replace(",", " ").split())
    for key, mat in LPC_MATERIAL_PATTERNS:
        if key in v:
            return mat
    return None


def osm_material_to_enum(value: str) -> int | None:
    """OSM ``building:material`` -> §5 material enum, or None when unmapped. Semicolon lists take the first value."""
    if not value:
        return None
    v = value.strip().lower().split(";")[0].strip().replace(" ", "_")
    return OSM_MATERIAL.get(v)


# --- deterministic hashing --------------------------------------------------------------------------------------------
_GOLD = np.uint64(0x9E3779B97F4A7C15)
_M1 = np.uint64(0xBF58476D1CE4E5B9)
_M2 = np.uint64(0x94D049BB133111EB)


def splitmix64(x: np.ndarray) -> np.ndarray:
    """splitmix64 finaliser (same construction as ``buildings.schema.lit_seed``)."""
    z = np.asarray(x, dtype=np.uint64) + _GOLD
    z = (z ^ (z >> np.uint64(30))) * _M1
    z = (z ^ (z >> np.uint64(27))) * _M2
    return z ^ (z >> np.uint64(31))


def salt_key(salt: int) -> np.uint64:
    """Mix an integer salt into a full 64-bit key (Python modular arithmetic: no numpy overflow warning)."""
    return np.uint64(((int(salt) + 1) * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF)


def rand_u32(seed: np.ndarray, salt: int) -> np.ndarray:
    """Deterministic uint32 stream from ``lit_seed`` and an integer salt (one salt per decision)."""
    return (splitmix64(np.asarray(seed, dtype=np.uint64) ^ salt_key(salt)) >> np.uint64(32)).astype(np.uint32)


def rand_unit(seed: np.ndarray, salt: int) -> np.ndarray:
    """Deterministic float64 in [0, 1)."""
    return rand_u32(seed, salt).astype(np.float64) * (1.0 / 4294967296.0)


def rand_choice(seed: np.ndarray, salt: int, n: int) -> np.ndarray:
    """Deterministic integer in [0, n)."""
    if n <= 1:
        return np.zeros(len(np.atleast_1d(seed)), dtype=np.int64)
    return (rand_u32(seed, salt) % np.uint32(n)).astype(np.int64)


def load_classes() -> list[dict[str, Any]]:
    """Validated facade class table, ordered by ``facade_class`` (1..N contiguous)."""
    return FP.load_facade_classes(FACADE_CLASSES_PATH)
