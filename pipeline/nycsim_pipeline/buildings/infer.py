"""Height / floors / ground inference with per-class floor heights (ARCHITECTURE §4.1 fallbacks).

Class floor-height table (metres), keyed by the first letter of the PLUTO ``bldgclass``:

| class | typology | floor height | ground floor |
|---|---|---|---|
| A, B | 1–2 family | 2.9 | 2.9 |
| C, D, R, S, N (pre-1945 or year unknown) | prewar multi-family / tenement / mixed | 3.3 | 3.6 (4.2 with storefront) |
| C, D, R, S, N (1945+) | postwar residential | 3.0 | 3.2 (4.2 with storefront) |
| H | hotel | 3.3 | 4.5 |
| L | loft | 3.9 | 4.5 |
| O | office | 3.9 | 5.0 |
| K | store building | 3.9 | 4.5 |
| E, F, T, U | warehouse / factory / transport / utility | 4.5 | 4.5 |
| G, V | garage / vacant-lot structure | 3.5 | 3.5 |
| I, W, Y, P, M, J, Q, Z | institutional / assembly | 3.9 | 4.5 |
| (no PLUTO) | generic residential | 3.0 | 3.3 |
| footprint feature_code 5110 | detached garage (overrides class) | 3.0 | 3.0 |

Inference rules:
* height missing or <= 0 -> PLUTO numfloors (primary building on lot) x class floor height, else median of the 10 nearest
  buildings with a LiDAR height -> ``HEIGHT_INFERRED``.
* floors: PLUTO numfloors (rounded half-up) when the footprint is the lot's primary building and consistent with the
  height (implied floor height within [2.2, 6.5] m; a 1-floor building must be <= 15 m), else
  ``1 + round((height - ground_floor_height) / floor_height)`` -> ``FLOORS_INFERRED``.
* ground_z: LiDAR ``ground_elevation`` -> bsin ``z_grade`` -> median of the 10 nearest buildings with a LiDAR ground.
"""
from __future__ import annotations

import logging

import numpy as np
import polars as pl
from scipy.spatial import cKDTree

from . import schema as S

log = logging.getLogger("nycsim.buildings.infer")

K_NEIGHBOURS = 10
PREWAR_YEAR = 1945
FLOOR_H_MIN, FLOOR_H_MAX = 2.2, 6.5
FLOOR_H_MIN_HOUSE = 2.0            # A/B classes: low ceilings in old frame houses
PITCH_TYPICAL_M = 1.5              # typical ridge height above the top storey for pitched-roof houses
PITCH_MAX_M = 3.5                  # maximum ridge allowance accepted in the floors consistency check
ONE_FLOOR_MAX_HEIGHT = 15.0
MAX_PLAUSIBLE_HEIGHT = 600.0

_LETTER_TABLE: dict[str, tuple[float, float]] = {
    "A": (2.9, 2.9), "B": (2.9, 2.9),
    "H": (3.3, 4.5), "L": (3.9, 4.5), "O": (3.9, 5.0), "K": (3.9, 4.5),
    "E": (4.5, 4.5), "F": (4.5, 4.5), "T": (4.5, 4.5), "U": (4.5, 4.5),
    "G": (3.5, 3.5), "V": (3.5, 3.5),
    "I": (3.9, 4.5), "W": (3.9, 4.5), "Y": (3.9, 4.5), "P": (3.9, 4.5), "M": (3.9, 4.5), "J": (3.9, 4.5),
    "Q": (3.9, 4.5), "Z": (3.9, 4.5),
}
_RESIDENTIAL = ("C", "D", "R", "S", "N")


def class_floor_heights(bldg_class: np.ndarray, year: np.ndarray, feature_code: np.ndarray,
                        has_storefront: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised (floor_height, ground_floor_height, pitched_roof_allowance) per building.

    The LiDAR ``height_roof`` is the highest roof point, so 1-2 family houses (A/B classes, pitched roofs) carry a
    typical 1.5 m ridge allowance (up to 3.5 m accepted) above the top storey; flat-roofed classes carry none.
    """
    letter = np.array([c[:1] if c else "" for c in bldg_class], dtype="<U1")
    fh = np.full(len(letter), 3.0)
    gfh = np.full(len(letter), 3.3)
    pitch = np.where(np.isin(letter, ("A", "B")), PITCH_TYPICAL_M, 0.0)
    for k, (f, g) in _LETTER_TABLE.items():
        m = letter == k
        fh[m] = f
        gfh[m] = g
    res = np.isin(letter, _RESIDENTIAL)
    prewar = res & ((year <= 0) | (year < PREWAR_YEAR))
    postwar = res & ~prewar
    fh[prewar], gfh[prewar] = 3.3, 3.6
    fh[postwar], gfh[postwar] = 3.0, 3.2
    sf = res & has_storefront
    gfh[sf] = 4.2
    garage = feature_code == 5110
    fh[garage], gfh[garage] = 3.0, 3.0
    pitch[garage] = 0.0
    return fh, gfh, pitch


def neighbour_median(cx: np.ndarray, cy: np.ndarray, values: np.ndarray, valid: np.ndarray, need: np.ndarray,
                     k: int = K_NEIGHBOURS) -> np.ndarray:
    """Median of the k nearest valid values for each row in ``need``. Returns array aligned with ``need`` rows."""
    out = np.full(int(need.sum()), np.nan)
    n_valid = int(valid.sum())
    if n_valid == 0 or not need.any():
        return out
    kk = min(k, n_valid)
    tree = cKDTree(np.column_stack([cx[valid], cy[valid]]))
    _, idx = tree.query(np.column_stack([cx[need], cy[need]]), k=kk)
    idx = np.atleast_2d(idx)
    if idx.shape[0] != int(need.sum()):
        idx = idx.T
    vals = values[valid][idx]
    return np.median(vals, axis=1)


def infer_heights_floors(attrs: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """Add ground_z, height, roof_z, floors, floor_height, ground_floor_height, year_built, *_source and fidelity."""
    n = attrs.height
    cx = attrs["centroid_x"].to_numpy()
    cy = attrs["centroid_y"].to_numpy()
    feature_code = attrs["feature_code"].to_numpy()
    is_primary = attrs["is_primary_on_lot"].to_numpy()
    n_on_lot = attrs["n_bldgs_on_lot"].to_numpy()
    has_sf = attrs["has_storefront"].to_numpy()
    bldg_class = attrs["pl_bldgclass"].fill_null("").to_numpy().astype(object)
    stats: dict = {}

    # ---- year -----------------------------------------------------------------------------------------------------
    fp_year = attrs["construction_year"].fill_null(0).to_numpy().astype(np.int64)
    pl_year = attrs["pl_yearbuilt"].fill_null(0).to_numpy().astype(np.int64)
    fp_ok = (fp_year >= 1600) & (fp_year <= 2100)
    pl_ok = (pl_year >= 1600) & (pl_year <= 2100) & (is_primary | (n_on_lot == 1))
    year = np.where(fp_ok, fp_year, np.where(pl_ok, pl_year, 0)).astype(np.int16)
    year_source = np.where(fp_ok, S.SRC_FOOTPRINT_YEAR, np.where(pl_ok, S.SRC_PLUTO, S.SRC_NONE)).astype(np.int8)
    year_real = year > 0
    stats["year_from_footprint"] = int(fp_ok.sum())
    stats["year_from_pluto"] = int((~fp_ok & pl_ok).sum())
    stats["year_unknown"] = int((~year_real).sum())

    fh, gfh_rule, pitch = class_floor_heights(bldg_class, year.astype(np.int64), feature_code, has_sf)
    pitch_max = np.where(pitch > 0, PITCH_MAX_M, 0.0)
    fh_min = np.where(pitch > 0, FLOOR_H_MIN_HOUSE, FLOOR_H_MIN)

    # ---- ground ---------------------------------------------------------------------------------------------------
    g_lidar = attrs["ground_z"].to_numpy().astype(np.float64)
    g_bsin = attrs["bsin_z_grade"].to_numpy().astype(np.float64)
    g_ok = np.isfinite(g_lidar) & (g_lidar > -30) & (g_lidar < 200)
    b_ok = ~g_ok & np.isfinite(g_bsin) & (g_bsin > -30) & (g_bsin < 200)
    ground = np.where(g_ok, g_lidar, np.where(b_ok, g_bsin, np.nan))
    ground_source = np.where(g_ok, S.SRC_LIDAR, np.where(b_ok, S.SRC_BSIN, S.SRC_NEIGHBOURS)).astype(np.int8)
    need = ~np.isfinite(ground)
    if need.any():
        ground[need] = neighbour_median(cx, cy, g_lidar, g_ok, need)
    stats["ground_lidar"] = int(g_ok.sum())
    stats["ground_bsin"] = int(b_ok.sum())
    stats["ground_neighbours"] = int(need.sum())
    # cross-check LiDAR ground vs surveyed bsin grade where both exist (report only)
    both = g_ok & np.isfinite(g_bsin)
    if both.any():
        d = g_lidar[both] - g_bsin[both]
        stats["ground_lidar_minus_bsin_median_m"] = float(np.median(d))
        stats["ground_lidar_minus_bsin_p90_abs_m"] = float(np.percentile(np.abs(d), 90))
        stats["ground_lidar_minus_bsin_n"] = int(both.sum())

    # ---- floors from PLUTO (candidate) ----------------------------------------------------------------------------
    numfloors = attrs["pl_numfloors"].to_numpy().astype(np.float64)
    fl_cand_ok = np.isfinite(numfloors) & (numfloors > 0) & is_primary
    fl_cand = np.where(fl_cand_ok, np.floor(numfloors + 0.5), 0).astype(np.int64)
    fl_cand = np.clip(fl_cand, 0, 200)
    fl_cand_ok &= fl_cand >= 1

    # ---- height ---------------------------------------------------------------------------------------------------
    h_lidar = attrs["height"].to_numpy().astype(np.float64)
    h_ok = np.isfinite(h_lidar) & (h_lidar > 0) & (h_lidar < MAX_PLAUSIBLE_HEIGHT)
    height = np.where(h_ok, h_lidar, np.nan)
    height_source = np.full(n, S.SRC_LIDAR, dtype=np.int8)
    from_floors = ~h_ok & fl_cand_ok
    height[from_floors] = gfh_rule[from_floors] + (fl_cand[from_floors] - 1) * fh[from_floors] + pitch[from_floors]
    height_source[from_floors] = S.SRC_PLUTO
    need = ~np.isfinite(height)
    if need.any():
        height[need] = neighbour_median(cx, cy, h_lidar, h_ok, need)
        height_source[need] = S.SRC_NEIGHBOURS
    # a neighbour median can still be NaN only if no LiDAR heights exist at all (subset runs); guard
    height = np.where(np.isfinite(height), height, 3.0)
    height = np.maximum(height, 1.0)
    stats["height_lidar"] = int(h_ok.sum())
    stats["height_from_pluto_floors"] = int(from_floors.sum())
    stats["height_from_neighbours"] = int(need.sum())
    stats["height_missing_or_nonpositive_in_source"] = int((~h_ok).sum())

    # ---- floors ---------------------------------------------------------------------------------------------------
    # consistency: the storeys above the ground floor must fit between fh_min and FLOOR_H_MAX each, allowing for a
    # pitched roof of up to pitch_max above the top storey; a 1-floor building must be <= 15 m
    with np.errstate(invalid="ignore", divide="ignore"):
        implied_lo = (height - gfh_rule - pitch_max) / np.maximum(fl_cand - 1, 1)
        implied_hi = (height - gfh_rule) / np.maximum(fl_cand - 1, 1)
    consistent = np.where(fl_cand > 1, (implied_hi >= fh_min) & (implied_lo <= FLOOR_H_MAX), height <= ONE_FLOOR_MAX_HEIGHT + pitch_max)
    fl_real = fl_cand_ok & (consistent | from_floors)
    h_eff = height - pitch     # storey stack height once the typical ridge allowance is removed
    floors_inf = np.where(h_eff <= gfh_rule + 0.5 * fh, 1, 1 + np.rint((h_eff - gfh_rule) / fh)).astype(np.int64)
    floors_inf = np.clip(floors_inf, 1, 200)
    floors = np.where(fl_real, fl_cand, floors_inf).astype(np.int16)
    floors_source = np.where(fl_real, S.SRC_PLUTO, S.SRC_HEIGHT_TO_FLOORS).astype(np.int8)
    stats["floors_pluto"] = int(fl_real.sum())
    stats["floors_pluto_rejected_inconsistent"] = int((fl_cand_ok & ~fl_real).sum())
    stats["floors_pluto_not_primary_or_missing"] = int((~fl_cand_ok).sum())
    stats["floors_inferred"] = int((~fl_real).sum())

    # ---- storey heights -------------------------------------------------------------------------------------------
    fl = floors.astype(np.float64)
    gfh = np.where(fl <= 1, height, np.minimum(gfh_rule, height - (fl - 1) * FLOOR_H_MIN))
    gfh = np.where(fl <= 1, height, np.maximum(gfh, FLOOR_H_MIN))
    # single-storey buildings: the contract formula is undefined (floors - 1 = 0); the class storey height is stored
    floor_height = np.where(fl > 1, (height - gfh) / np.maximum(fl - 1, 1), fh)
    roof_z = ground + height

    # ---- fidelity -------------------------------------------------------------------------------------------------
    fid = np.full(n, S.Fidelity.FOOTPRINT_REAL.mask, dtype=np.uint16)
    fid |= np.where(h_ok, S.Fidelity.HEIGHT_REAL.mask, S.Fidelity.HEIGHT_INFERRED.mask).astype(np.uint16)
    fid |= np.where(fl_real, S.Fidelity.FLOORS_REAL.mask, S.Fidelity.FLOORS_INFERRED.mask).astype(np.uint16)
    fid |= np.where(year_real, S.Fidelity.YEAR_REAL.mask, 0).astype(np.uint16)
    fid |= np.where(g_ok | b_ok, S.Fidelity.GROUND_REAL.mask, 0).astype(np.uint16)

    out = attrs.with_columns([
        pl.Series("ground_z", ground.astype(np.float32)),
        pl.Series("height", height.astype(np.float32)),
        pl.Series("roof_z", roof_z.astype(np.float32)),
        pl.Series("floors", floors),
        pl.Series("floor_height", floor_height.astype(np.float32)),
        pl.Series("ground_floor_height", gfh.astype(np.float32)),
        pl.Series("year_built", year),
        pl.Series("height_source", height_source),
        pl.Series("floors_source", floors_source),
        pl.Series("year_source", year_source),
        pl.Series("ground_source", ground_source),
        pl.Series("fidelity", fid),
    ])
    log.info("infer: height real %d / inferred %d; floors real %d / inferred %d; year real %d; ground real %d",
             stats["height_lidar"], n - stats["height_lidar"], stats["floors_pluto"], stats["floors_inferred"],
             n - stats["year_unknown"], stats["ground_lidar"] + stats["ground_bsin"])
    return out, stats
