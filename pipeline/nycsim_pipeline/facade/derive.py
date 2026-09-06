"""Per-building facade attributes derived from the classified ``facade_class`` and the real attributes.

Everything here is vectorised over the whole borough chunk with numpy.  The class table supplies the *typology*
(materials, window family, features, storey heights); the real per-building attributes supply the *quantities*
(frontage -> window columns, floors -> window rows, first-floor offset -> stoop, roof area -> rooftop plant).

Material precedence (ADR-004): OSM ``building:material`` > OSM ``building:colour`` > LPC designation-report
``MATERIAL1`` > the rule-derived class default.  The first three set ``MATERIAL_REAL`` (fidelity bit 5); everything
else leaves it clear and therefore sets ``FACADE_INFERRED`` (bit 10, defined by DATA_CONTRACTS §5.1 as "set whenever
bit 5 is clear").
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from . import enums as E

log = logging.getLogger("nycsim.facade.derive")

# --- material source codes (§5.3 extension column ``material_source``) -------------------------------------------------
MAT_SRC_OSM_MATERIAL = 0
MAT_SRC_OSM_COLOUR = 1
MAT_SRC_LPC = 2
MAT_SRC_RULE = 3

RED_BRICK_ID = E.RED_BRICK
CONCRETE_ID = E.CONCRETE
VINYL_SIDING_ID = E.VINYL_SIDING
WOOD_CLAPBOARD_ID = E.WOOD_CLAPBOARD
METAL_PANEL_ID = E.METAL_PANEL

# --- frontage source codes (§5.3 extension column ``frontage_source``) --------------------------------------------------
FRONT_SRC_GEOMETRY = 0     # length of the primary (street-facing, non party-wall) footprint run
FRONT_SRC_PLUTO = 1        # MapPLUTO ``bldgfront``
FRONT_SRC_LOT = 2          # MapPLUTO ``lotfront``
FRONT_SRC_AREA = 3         # sqrt(footprint area) — last resort

# --- water tower kinds -------------------------------------------------------------------------------------------------
TANK_NONE, TANK_WOOD_10K, TANK_WOOD_20K, TANK_STEEL = 0, 1, 2, 3
TANK_PIECE = {TANK_WOOD_10K: "water_tower_wood_10k", TANK_WOOD_20K: "water_tower_wood_20k", TANK_STEEL: "water_tower_steel"}

#: A gravity tank needs a roof that can carry the stand. 150 m^2 is a 25 x 65 ft roof — the smallest that does.
TANK_MIN_ROOF_AREA_M2 = 150.0
#: NYC street mains reach roughly the sixth floor; taller buildings need a tank (or a booster).
TANK_MIN_FLOORS = 6
#: Wooden gravity tanks are the pre-1950 norm; 1950-1989 buildings use enclosed steel tanks or basement boosters.
TANK_WOOD_MAX_YEAR = 1949
TANK_MAX_YEAR = 1989
#: A tank over 4,000 m^2 of roof is the 20,000 gal size.
TANK_LARGE_ROOF_AREA_M2 = 1200.0
#: facade classes that never carry a rooftop tank (no habitable water demand or an all-mechanical crown).
NO_TANK_CLASSES = frozenset({16, 17, 18, 19, 22, 38, 41, 42, 46, 47, 48, 55})

#: The 1968 NYC Building Code replaced the fire escape with two enclosed means of egress for new construction.
FIRE_ESCAPE_MAX_YEAR = 1968
FIRE_ESCAPE_MIN_FLOORS = 3

#: A raised first floor of this height or more implies real front steps (Building Elevation & Subgrade z_floor-z_grade).
STOOP_MIN_OFFSET_M = 0.75
#: Above this height the entrance is a lobby, not a stoop.
STOOP_MAX_FLOORS = 8

#: Generic NYC awning wording per storefront kind, used only when no real business name is attached
#: (buildings with a real name already carry SIGNAGE_REAL, fidelity bit 6).
GENERIC_AWNING: dict[int, str] = {
    E.SK_BODEGA: "GROCERY - DELI - BEER",
    E.SK_DELI: "DELI GROCERY",
    E.SK_PHARMACY: "PHARMACY",
    E.SK_RESTAURANT: "RESTAURANT",
    E.SK_BAR: "BAR",
    E.SK_NAIL_HAIR: "NAILS & SPA",
    E.SK_LAUNDROMAT: "LAUNDROMAT",
    E.SK_BANK: "BANK",
    E.SK_CLOTHING: "CLOTHING",
    E.SK_ELECTRONICS: "ELECTRONICS",
    E.SK_GROCERY: "SUPERMARKET",
    E.SK_HARDWARE: "HARDWARE",
    E.SK_COFFEE: "COFFEE",
    E.SK_PIZZA: "PIZZA",
    E.SK_DRY_CLEANER: "DRY CLEANERS",
    E.SK_GENERIC_RETAIL: "OPEN",
    E.SK_OFFICE_LOBBY: "",
    E.SK_RESIDENTIAL_LOBBY: "",
    E.SK_GARAGE_DOOR: "",
    E.SK_VACANT: "",
}

# Salts for the deterministic per-building streams (never reuse a salt for two different decisions).
SALT_TANK_SIZE = 101
SALT_ANTENNA = 102
SALT_HVAC = 103
SALT_STOREFRONT_KIND = 104
SALT_GATE = 105
SALT_AC_UNIT = 106
SALT_WINDOW_LIT = 107
SALT_STOREFRONT_BAY = 108
SALT_VARIANT = 109
SALT_AWNING = 110
SALT_INTERIOR = 111


@dataclass(frozen=True)
class ClassTable:
    """Per-``facade_class`` lookup arrays, indexed by ``facade_class`` (index 0 unused)."""
    n: int
    material_primary: np.ndarray      # int8
    material_secondary: np.ndarray    # int8
    window_type: np.ndarray           # int8
    bay_width: np.ndarray             # float32
    floor_height: np.ndarray          # float32
    ground_floor_height: np.ndarray   # float32
    has_cornice: np.ndarray           # bool
    cornice_style: np.ndarray         # int8 index into kit_ids.CORNICE_STYLES
    has_fire_escape: np.ndarray       # bool (class feature)
    has_stoop: np.ndarray             # bool (class feature)
    has_storefront: np.ndarray        # bool (class feature)
    has_water_tower: np.ndarray       # bool (class feature)
    has_rooftop_hvac: np.ndarray      # bool
    has_bulkhead: np.ndarray          # bool
    has_cell_antennas: np.ndarray     # bool
    has_balconies: np.ndarray         # bool
    has_roll_gate: np.ndarray         # bool
    has_awning: np.ndarray            # bool
    has_ac_units: np.ndarray          # bool
    has_through_wall_ac: np.ndarray   # bool
    has_areaway: np.ndarray           # bool
    has_setbacks: np.ndarray          # bool
    has_billboard: np.ndarray         # bool
    has_loading_dock: np.ndarray      # bool
    has_garage: np.ndarray            # bool
    has_ivy: np.ndarray               # bool
    roof_shape: np.ndarray            # int8 roof_type enum implied by the class
    ids: list[str]
    storefront_kinds: list[list[int]]


def class_table() -> ClassTable:
    """Build the per-class lookup arrays from ``facade_classes.json``."""
    from .kit_ids import CORNICE_STYLES
    classes = E.load_classes()
    n = max(c["facade_class"] for c in classes) + 1

    def z(dtype, fill=0):
        return np.full(n, fill, dtype=dtype)

    t = {
        "material_primary": z(np.int8), "material_secondary": z(np.int8), "window_type": z(np.int8),
        "bay_width": z(np.float32, 2.0), "floor_height": z(np.float32, 3.0), "ground_floor_height": z(np.float32, 3.4),
        "cornice_style": z(np.int8), "roof_shape": z(np.int8),
    }
    flags = {k: np.zeros(n, dtype=bool) for k in (
        "has_cornice", "has_fire_escape", "has_stoop", "has_storefront", "has_water_tower", "has_rooftop_hvac",
        "has_bulkhead", "has_cell_antennas", "has_balconies", "has_roll_gate", "has_awning", "has_ac_units",
        "has_through_wall_ac", "has_areaway", "has_setbacks", "has_billboard", "has_loading_dock", "has_garage",
        "has_ivy")}
    ids = [""] * n
    sf_kinds: list[list[int]] = [[] for _ in range(n)]
    feature_flag = {
        "cornice": "has_cornice", "fire_escape": "has_fire_escape", "stoop": "has_stoop", "storefront": "has_storefront",
        "water_tower": "has_water_tower", "rooftop_hvac": "has_rooftop_hvac", "bulkhead": "has_bulkhead",
        "cell_antennas": "has_cell_antennas", "balconies": "has_balconies", "roll_gate": "has_roll_gate",
        "awning": "has_awning", "ac_units": "has_ac_units", "through_wall_ac": "has_through_wall_ac",
        "areaway_railing": "has_areaway", "setbacks": "has_setbacks", "billboard": "has_billboard",
        "loading_dock": "has_loading_dock", "garage": "has_garage", "ivy": "has_ivy",
    }
    for c in classes:
        i = int(c["facade_class"])
        ids[i] = c["id"]
        mats = c["materials"]
        t["material_primary"][i] = E.MATERIAL_INDEX[mats[0]]
        t["material_secondary"][i] = E.MATERIAL_INDEX[mats[1] if len(mats) > 1 else mats[0]]
        wt = c["window_type"]
        t["window_type"][i] = E.WINDOW_TYPE_INDEX[wt]
        t["bay_width"][i] = E.BAY_WIDTH_M[wt]
        t["floor_height"][i] = float(c["floor_height_m"])
        t["ground_floor_height"][i] = float(c["ground_floor_height_m"])
        cs = c.get("cornice_style", "none_parapet")
        t["cornice_style"][i] = CORNICE_STYLES.index(cs) if cs in CORNICE_STYLES else 0
        t["roof_shape"][i] = E.CLASS_ROOF_SHAPE.get(c.get("roof", "flat_parapet"), (E.ROOF_FLAT, 0.0))[0]
        for f in c.get("features", []):
            k = feature_flag.get(f)
            if k:
                flags[k][i] = True
        sf_kinds[i] = [E.STOREFRONT_KIND_INDEX[k] for k in c.get("storefront_kinds_typical", [])]
    return ClassTable(n=n, ids=ids, storefront_kinds=sf_kinds, **t, **flags)


CLASS = class_table()


# ----------------------------------------------------------------------------------------------------------------------
#: An accessory garage (OTI feature code 5110) is not a concrete parking deck: it is a small outbuilding whose
#: material follows its lot. MapPLUTO says so directly — class B2 is a *frame* two-family, B1 a *brick* one — and the
#: pre-1946 outbuilding stock is masonry. These are the only three materials NYC backyard garages are built of.
def garage_material(bldg_class: np.ndarray, nta: np.ndarray, year: np.ndarray, frame_belt: tuple[str, ...]
                    ) -> tuple[np.ndarray, np.ndarray]:
    """``(primary, secondary)`` for an accessory garage, from its lot's real class, era and neighbourhood."""
    cls = np.asarray(bldg_class)
    letter = np.asarray([c[:1] if c else "" for c in cls])
    frame_lot = (cls == "B2") | ((np.isin(nta, list(frame_belt))) & np.isin(letter, ["A", "B", "C"]))
    prewar = (year > 0) & (year <= 1945)
    prim = np.where(frame_lot, np.int8(VINYL_SIDING_ID), np.where(prewar, np.int8(RED_BRICK_ID), np.int8(CONCRETE_ID)))
    sec = np.where(frame_lot, np.int8(WOOD_CLAPBOARD_ID), np.where(prewar, np.int8(CONCRETE_ID), np.int8(METAL_PANEL_ID)))
    return prim.astype(np.int8), sec.astype(np.int8)


#: Facade class 22 (``warehouse_concrete_1950``) spans 1935-1985. Before about 1940 the NYC industrial shed is
#: load-bearing brick, not concrete: its two class materials are simply swapped for the pre-war rows.
PREWAR_INDUSTRIAL_CLASS = 22
PREWAR_INDUSTRIAL_MAX_YEAR = 1940


def resolve_material(fc: np.ndarray, osm_material: np.ndarray, osm_colour_material: np.ndarray,
                     lpc_material: np.ndarray, base_primary: np.ndarray | None = None,
                     base_secondary: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Material precedence per ADR-004.

    All inputs are int8 arrays with −1 meaning "no evidence"; ``base_primary``/``base_secondary`` override the class
    default before the real-evidence sources are applied (used for accessory garages).  Returns
    ``(material_primary, material_secondary, material_source, material_real)``.
    """
    prim = (CLASS.material_primary[fc] if base_primary is None else base_primary).astype(np.int8)
    sec = (CLASS.material_secondary[fc] if base_secondary is None else base_secondary).astype(np.int8)
    src = np.full(len(fc), MAT_SRC_RULE, dtype=np.int8)

    # An OSM ``building:colour`` is a statement about *shade*, not about material family, so it only refines a
    # masonry wall that the rule or the LPC report already settled on; an explicit ``building:material`` tag and an
    # LPC designation-report material are statements about the family and override it.
    take = lpc_material >= 0
    prim = np.where(take, lpc_material, prim).astype(np.int8)
    src = np.where(take, MAT_SRC_LPC, src).astype(np.int8)

    brick_family = np.isin(prim, [E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK, E.WHITE_GLAZED_BRICK])
    take = (osm_colour_material >= 0) & brick_family & np.isin(
        osm_colour_material, [E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK, E.WHITE_GLAZED_BRICK])
    prim = np.where(take, osm_colour_material, prim).astype(np.int8)
    src = np.where(take, MAT_SRC_OSM_COLOUR, src).astype(np.int8)

    take = osm_material >= 0
    prim = np.where(take, osm_material, prim).astype(np.int8)
    src = np.where(take, MAT_SRC_OSM_MATERIAL, src).astype(np.int8)

    # a trim material equal to the wall material reads as no trim: fall back to the class default, then to limestone
    same = sec == prim
    sec = np.where(same, (CLASS.material_secondary[fc] if base_secondary is None else base_secondary).astype(np.int8),
                   sec).astype(np.int8)
    still = sec == prim
    fallback = np.where(np.isin(prim, [E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK, E.WHITE_GLAZED_BRICK]),
                        np.int8(E.LIMESTONE), np.int8(E.CONCRETE))
    sec = np.where(still, fallback, sec).astype(np.int8)
    return prim, sec, src, (src != MAT_SRC_RULE)


def resolve_frontage(primary_run_len: np.ndarray, bldg_frontage: np.ndarray, lot_frontage: np.ndarray,
                     footprint_area: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Facade frontage in metres and its source code.

    MapPLUTO ``bldgfront`` is the **surveyed frontage of the building** and is exactly what DATA_CONTRACTS §5 means by
    "windows across primary facade", so it is preferred (available for 1,060,165 of 1,083,026 footprints).  The longest
    street-facing footprint run backs it up: it is the right value where PLUTO has none, but on its own it
    under-counts a facade that a projecting bay or a step has split into several short runs.  The *placements* always
    use the real per-run geometry regardless, so a 1.9 m run still gets one bay on the ground.
    """
    n = len(primary_run_len)
    front = np.zeros(n, dtype=np.float32)
    src = np.full(n, FRONT_SRC_AREA, dtype=np.int8)

    ok = np.isfinite(bldg_frontage) & (bldg_frontage >= 2.0) & (bldg_frontage <= 250.0)
    front = np.where(ok, bldg_frontage, front).astype(np.float32)
    src = np.where(ok, FRONT_SRC_PLUTO, src).astype(np.int8)

    need = ~ok
    ok2 = need & np.isfinite(primary_run_len) & (primary_run_len >= 2.0)
    front = np.where(ok2, primary_run_len, front).astype(np.float32)
    src = np.where(ok2, FRONT_SRC_GEOMETRY, src).astype(np.int8)

    need = need & ~ok2
    ok3 = need & np.isfinite(lot_frontage) & (lot_frontage >= 2.0) & (lot_frontage <= 250.0)
    front = np.where(ok3, lot_frontage, front).astype(np.float32)
    src = np.where(ok3, FRONT_SRC_LOT, src).astype(np.int8)

    need = need & ~ok3
    front = np.where(need, np.sqrt(np.maximum(footprint_area, 1.0)), front).astype(np.float32)
    return front, src


def window_grid(fc: np.ndarray, frontage: np.ndarray, floors: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(window_cols, window_rows, bay_width_m)``.

    Columns come from real geometry: ``round(frontage / bay width of the class's window family)``, at least one bay and
    never more bays than the frontage can carry.  Rows are ``floors − 1``: the ground floor is consumed by the ground
    floor treatment (storefront, stoop and entrance, garage or lobby), which is placed separately.
    """
    bay = CLASS.bay_width[fc].astype(np.float32)
    cols = np.rint(frontage / np.maximum(bay, 0.5)).astype(np.int32)
    cols = np.clip(cols, 1, 200)
    cols = np.minimum(cols, np.maximum(np.floor(frontage / np.maximum(bay, 0.5) + 0.5), 1).astype(np.int32))
    rows = np.maximum(floors.astype(np.int32) - 1, 0)
    return cols.astype(np.int16), rows.astype(np.int16), bay


def water_towers(fc: np.ndarray, floors: np.ndarray, year: np.ndarray, roof_area: np.ndarray,
                 feature_code: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(has_water_tower, water_tower_kind)``.

    NYC street mains pressurise roughly six storeys, so buildings of six floors and up need a tank.  Gravity tanks
    are wooden through about 1950 (the population the published 10,000-17,000 figure counts) and enclosed steel or
    basement-boosted afterwards.  Classes with no habitable water demand or an all-mechanical crown are excluded.
    """
    eligible = ((floors >= TANK_MIN_FLOORS) & (year > 1850) & (year <= TANK_MAX_YEAR)
                & (roof_area >= TANK_MIN_ROOF_AREA_M2) & (feature_code != 5110)
                & ~np.isin(fc, list(NO_TANK_CLASSES)))
    kind = np.zeros(len(fc), dtype=np.int8)
    wood = eligible & (year <= TANK_WOOD_MAX_YEAR)
    large = wood & (roof_area >= TANK_LARGE_ROOF_AREA_M2)
    kind[wood] = TANK_WOOD_10K
    kind[large] = TANK_WOOD_20K
    kind[eligible & ~wood] = TANK_STEEL
    return eligible, kind


def fire_escapes(fc: np.ndarray, floors: np.ndarray, year: np.ndarray, borough: np.ndarray,
                 bldg_class1: np.ndarray, n_free_runs: np.ndarray) -> np.ndarray:
    """Fire escapes on the buildings that really carry them.

    The 1867 Tenement House Act made an exterior means of egress compulsory for multiple dwellings; the 1968 Building
    Code replaced it with two enclosed stairs, so nothing built after 1968 has one.  The class table already carries
    ``fire_escape`` for the tenement, loft, cast-iron and frame-tenement typologies; this adds the real per-building
    conditions: at least three storeys, at least one free (non party-wall) facade to hang it on, never a one- or
    two-family house, and never Staten Island below five storeys (its walk-up stock is frame houses, not tenements).
    """
    base = CLASS.has_fire_escape[fc] & (floors >= FIRE_ESCAPE_MIN_FLOORS) & (n_free_runs >= 1)
    base &= (year <= FIRE_ESCAPE_MAX_YEAR) & (year > 1800)
    base &= ~np.isin(bldg_class1, [b"A", b"B"])
    base &= ~((borough == 5) & (floors < 5))
    base &= ~((borough == 4) & (floors < 4) & np.isin(bldg_class1, [b"S"]))
    return base


def stoops(fc: np.ndarray, floors: np.ndarray, has_storefront: np.ndarray, first_floor_offset: np.ndarray,
           bldg_class1: np.ndarray, n_free_runs: np.ndarray) -> np.ndarray:
    """Stoops: real evidence first.

    ``first_floor_offset`` is the surveyed first-floor elevation minus grade (NYC Building Elevation & Subgrade,
    bsin-59hv).  An offset of 0.75 m or more means the entrance is physically reached by steps.  The class feature
    covers the rowhouse typologies whose stoop is part of the type even where the survey has no record.
    """
    residential = np.isin(bldg_class1, [b"A", b"B", b"C", b"S", b"R"])
    raised = np.isfinite(first_floor_offset) & (first_floor_offset >= STOOP_MIN_OFFSET_M)
    return ((CLASS.has_stoop[fc] | (residential & raised)) & (floors >= 1) & (floors <= STOOP_MAX_FLOORS)
            & ~has_storefront & (n_free_runs >= 1))


def rooftop_unit_count(fc: np.ndarray, floors: np.ndarray, roof_area: np.ndarray, seed: np.ndarray,
                       bldg_class1: np.ndarray) -> np.ndarray:
    """Number of rooftop kit items (bulkheads, HVAC, antennas, vents), DATA_CONTRACTS §5 ``rooftop_units`` (int8)."""
    n = len(fc)
    units = np.zeros(n, dtype=np.int32)
    units += (CLASS.has_bulkhead[fc] & (floors >= 5)).astype(np.int32)          # stair bulkhead
    units += (floors >= 8).astype(np.int32)                                     # elevator machine room
    hvac = CLASS.has_rooftop_hvac[fc]
    units += np.where(hvac, np.clip(np.rint(roof_area / 500.0), 1, 10), 0).astype(np.int32)
    antenna = CLASS.has_cell_antennas[fc] & (floors >= 6) & (E.rand_unit(seed, SALT_ANTENNA) < 0.35)
    units += np.where(antenna, 3, 0).astype(np.int32)
    residential = np.isin(bldg_class1, [b"A", b"B", b"C", b"D", b"S", b"R"])
    units += ((floors >= 3) & residential).astype(np.int32)                     # soil stack / exhaust
    units += ((roof_area >= 800.0) & (floors >= 3)).astype(np.int32)
    return np.clip(units, 0, 60).astype(np.int8)


def awning_texts(has_storefront: np.ndarray, storefront_names: list[list[str]], kinds: list[list[int]],
                 fc: np.ndarray, seed: np.ndarray) -> tuple[list[str], np.ndarray]:
    """``awning_text`` and a flag saying whether it is a real business name.

    A real DCWP/DOHMH/OSM business name is used verbatim (those buildings already carry SIGNAGE_REAL).  Buildings with
    PLUTO retail evidence but no name get the standard generic NYC awning wording for their storefront kind, which is
    part of the inferred facade.
    """
    n = len(fc)
    out: list[str] = [""] * n
    real = np.zeros(n, dtype=bool)
    pick = E.rand_choice(seed, SALT_AWNING, 64)
    for i in range(n):
        if not has_storefront[i]:
            continue
        names = storefront_names[i]
        if names:
            nm = str(names[0]).strip()
            if nm:
                out[i] = nm[:96]
                real[i] = True
                continue
        ks = kinds[i]
        if ks:
            k = int(ks[0])
        else:
            typ = CLASS.storefront_kinds[int(fc[i])]
            k = typ[int(pick[i]) % len(typ)] if typ else E.SK_GENERIC_RETAIL
        out[i] = GENERIC_AWNING.get(k, "")
    return out, real


def storefront_kind_for_placement(fc: np.ndarray, kinds: list[list[int]], seed: np.ndarray,
                                  is_corner: np.ndarray) -> np.ndarray:
    """One storefront kind per building for the ground-floor treatment.

    Real kinds from DCWP licences / DOHMH restaurant permits / OSM shop tags win.  Where PLUTO says there is retail
    but no licence matched, the kind comes from the class's typical mix; a corner lot biases towards the bodega/deli
    that really occupies NYC corners.
    """
    n = len(fc)
    out = np.full(n, E.SK_GENERIC_RETAIL, dtype=np.int8)
    pick = E.rand_choice(seed, SALT_STOREFRONT_KIND, 4096)
    for i in range(n):
        ks = kinds[i]
        if ks:
            out[i] = np.int8(ks[0])
            continue
        typ = CLASS.storefront_kinds[int(fc[i])]
        if not typ:
            out[i] = E.SK_GENERIC_RETAIL
        elif is_corner[i] and (E.SK_BODEGA in typ or E.SK_DELI in typ):
            out[i] = np.int8(E.SK_BODEGA if E.SK_BODEGA in typ else E.SK_DELI)
        else:
            out[i] = np.int8(typ[int(pick[i]) % len(typ)])
    return out
