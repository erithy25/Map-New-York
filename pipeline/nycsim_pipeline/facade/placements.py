"""Deterministic kit placements per tile (DATA_CONTRACTS §6).

Record layout, little-endian, 40 bytes, exactly as the contract states::

    uint32 kit_id; int64 bin; float32 x, y, z; float32 yaw_deg; float32 scale; uint32 variant_seed; uint32 flags

Conventions used (stated in the ``.json`` header of every tile so consumers never have to guess):

* ``x, y`` NYC_TM metres of the piece's contact point — the wall face for facade pieces, the roof deck for roof
  pieces, the sidewalk for stoops, sheds and storefronts (DATA_CONTRACTS §13: "origin at ground contact / wall
  contact point").
* ``z`` NAVD88 metres, absolute, consistent with ``ground_z`` / ``roof_z``.
* ``yaw_deg`` the direction the piece faces, in the contract's default angle convention (0 = east, counter-clockwise;
  the name does not end in ``_heading``).  For a facade piece it is the outward normal of the wall run.
* ``scale`` uniform scale for point pieces; for **run pieces** (cornice, parapet, string course, sign band, sidewalk
  shed, roll gate, awning) it is the along-run stretch/repeat factor relative to the piece's nominal width, so one
  record covers a whole run instead of N repeated records.
* ``variant_seed`` a deterministic uint32 derived from ``lit_seed`` and the piece's address on the building
  (run, bay, floor) — the kit picks its material weathering / glass tint / gate state from it.
* ``flags`` bit0 lit at night, bit1 animated (roll gates, shed lights), bit2 interior-visible (shop interiors).

Everything is derived from ``lit_seed``, so the same input always produces byte-identical output.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely

from . import enums as E
from .derive import CLASS, SALT_AC_UNIT, SALT_GATE, SALT_STOREFRONT_BAY, SALT_VARIANT, SALT_WINDOW_LIT, TANK_PIECE
from .kit_ids import FLAG_ANIMATED, FLAG_INTERIOR, FLAG_LIT, kit_id

log = logging.getLogger("nycsim.facade.placements")

PLACEMENT_DTYPE = np.dtype([
    ("kit_id", "<u4"), ("bin", "<i8"), ("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
    ("yaw_deg", "<f4"), ("scale", "<f4"), ("variant_seed", "<u4"), ("flags", "<u4"),
])
assert PLACEMENT_DTYPE.itemsize == 40, PLACEMENT_DTYPE.itemsize

RECORD_BYTES = 40
PLACEMENTS_SCHEMA = "kit_placements/1"

# --- placement policy constants (all real dimensions or stated shares) -------------------------------------------------
MIN_WINDOW_RUN_M = 2.2        # a facade run shorter than this carries no window
MIN_GROUND_RUN_M = 2.6        # a run shorter than this carries no ground-floor treatment
MAX_BAYS_PER_RUN = 32
MAX_WINDOW_FLOORS = 110
SILL_ABOVE_FLOOR_M = 0.85     # residential sill height above the finished floor
SILL_OFFICE_M = 0.75
GROUND_SILL_M = 0.95          # ground-floor sill sits higher (areaway / privacy)
CORNICE_NOMINAL_W_M = 2.0
PARAPET_NOMINAL_W_M = 2.0
SHED_BAY_M = 2.4              # DOB sidewalk shed bay
MAX_SHED_BAYS = 24
STOREFRONT_TARGET_BAY_M = 4.8
MAX_STOREFRONT_BAYS = 12
AC_UNIT_SHARE = 0.18          # share of residential upper-floor windows carrying a window AC unit
ROLL_GATE_SHARE = 0.55        # share of storefront bays with a roll-down gate
AWNING_SHARE = 0.60
LIT_SHARE_RESIDENTIAL = 0.32
LIT_SHARE_OFFICE = 0.18
LIT_SHARE_RETAIL = 0.55
MAX_PLACEMENTS_PER_BUILDING = 2500
ROOF_INSET_FRACTION = 0.28    # roof equipment sits this fraction of sqrt(area) from the roof anchor
MAX_RUN_SCALE = 12.0          # a run piece is split into segments rather than stretched further than this

_CURTAIN_WALL = E.WINDOW_TYPE_INDEX["curtain_wall_module"]
_THROUGH_WALL = E.WINDOW_TYPE_INDEX["through_wall_ac_sleeve"]


@dataclass
class Accum:
    """Growable placement buffer."""
    parts: list[np.ndarray]

    def __init__(self) -> None:
        self.parts = []

    def add(self, kid: np.ndarray | int, bin_: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray,
            yaw: np.ndarray, scale: np.ndarray | float, seed: np.ndarray, flags: np.ndarray | int) -> None:
        n = len(bin_)
        if n == 0:
            return
        rec = np.empty(n, dtype=PLACEMENT_DTYPE)
        rec["kit_id"] = kid
        rec["bin"] = bin_
        rec["x"] = x
        rec["y"] = y
        rec["z"] = z
        rec["yaw_deg"] = yaw
        rec["scale"] = scale
        rec["variant_seed"] = seed
        rec["flags"] = flags
        self.parts.append(rec)

    def result(self) -> np.ndarray:
        if not self.parts:
            return np.empty(0, dtype=PLACEMENT_DTYPE)
        return np.concatenate(self.parts)


def _yaw(nx: np.ndarray, ny: np.ndarray) -> np.ndarray:
    """Outward normal -> yaw in the contract's default angle convention (0 = east, counter-clockwise)."""
    return np.degrees(np.arctan2(ny, nx)).astype(np.float32)


def _cumstart(counts: np.ndarray) -> np.ndarray:
    c = np.zeros(len(counts) + 1, dtype=np.int64)
    np.cumsum(counts, out=c[1:])
    return c[:-1]


def _index_within(counts: np.ndarray) -> np.ndarray:
    """For counts [2,3] -> [0,1,0,1,2]."""
    total = int(counts.sum())
    if total == 0:
        return np.zeros(0, dtype=np.int64)
    return np.arange(total, dtype=np.int64) - np.repeat(_cumstart(counts), counts)


def _split_run(run_idx: np.ndarray, length: np.ndarray, nominal_w: float
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split each run into segments no longer than ``MAX_RUN_SCALE x nominal_w``.

    Returns ``(run index per segment, centre offset along the run, segment length)``.  One record per segment keeps
    the along-run stretch factor bounded instead of asking the engine to stretch a 2 m cornice over half a kilometre.
    """
    seg_max = MAX_RUN_SCALE * nominal_w
    n_seg = np.maximum(np.ceil(length / seg_max).astype(np.int64), 1)
    rep = np.repeat(run_idx, n_seg)
    k = _index_within(n_seg)
    seg_len = np.repeat(length / n_seg, n_seg)
    t = (k + 0.5) * seg_len
    return rep, t, seg_len


def _seed_mix(base: np.ndarray, a: np.ndarray, b: np.ndarray = None, salt: int = 0) -> np.ndarray:
    """Deterministic per-piece variant seed from the building seed and the piece's address on the building."""
    x = np.asarray(base, dtype=np.uint64) ^ E.salt_key(salt)
    x = x * np.uint64(0x100000001B3) + np.asarray(a, dtype=np.uint64)
    if b is not None:
        x = x * np.uint64(0x100000001B3) + np.asarray(b, dtype=np.uint64)
    return (E.splitmix64(x) >> np.uint64(32)).astype(np.uint32)


def build_placements(b: dict[str, np.ndarray], runs: dict[str, np.ndarray], geoms: np.ndarray) -> np.ndarray:
    """Generate every kit placement for a batch of buildings.

    ``b`` holds the per-building arrays (keys named after the buildings/facade columns); ``runs`` holds the merged
    facade runs with ``bidx`` indexing into ``b``; ``geoms`` are the footprints (shapely polygons) for roof anchors.
    """
    acc = Accum()
    nb = len(b["bin"])
    if nb == 0:
        return acc.result()

    fc = b["facade_class"].astype(np.int64)
    floors = np.maximum(b["floors"].astype(np.int32), 1)
    fh = np.where(b["floor_height"] > 0.5, b["floor_height"], CLASS.floor_height[fc]).astype(np.float64)
    gfh = np.where(b["ground_floor_height"] > 0.5, b["ground_floor_height"], CLASS.ground_floor_height[fc]).astype(np.float64)
    gz = b["ground_z"].astype(np.float64)
    rz = b["roof_z"].astype(np.float64)
    seed = b["lit_seed"].astype(np.uint64)
    wt = b["window_type"].astype(np.int64)
    bay_w = np.maximum(b["bay_width_m"].astype(np.float64), 1.0)
    rows = np.clip(b["window_rows"].astype(np.int32), 0, MAX_WINDOW_FLOORS)
    is_garage = (b["feature_code"] == 5110) | np.isin(b["bldg_class1"], [b"G"])
    cls1 = b["bldg_class1"]
    residential = np.isin(cls1, [b"A", b"B", b"C", b"D", b"S", b"R"])
    office_like = np.isin(cls1, [b"O", b"K", b"I", b"W", b"H", b"L", b"F", b"E"])

    # ---- run geometry ------------------------------------------------------------------------------------------------
    r_b = runs["bidx"].astype(np.int64)
    r_len = runs["length"].astype(np.float64)
    r_x0, r_y0 = runs["x0"].astype(np.float64), runs["y0"].astype(np.float64)
    r_x1, r_y1 = runs["x1"].astype(np.float64), runs["y1"].astype(np.float64)
    r_nx, r_ny = runs["nx"].astype(np.float64), runs["ny"].astype(np.float64)
    r_party = runs["is_party"].astype(bool)
    r_street = runs["is_street"].astype(bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        r_ux = np.where(r_len > 0, (r_x1 - r_x0) / r_len, 1.0)
        r_uy = np.where(r_len > 0, (r_y1 - r_y0) / r_len, 0.0)
    r_yaw = _yaw(r_nx, r_ny)
    r_free = ~r_party
    r_idx = np.arange(len(r_b), dtype=np.int64)

    # the "primary" run of each building: longest street-facing free run, else longest free run
    prim = _primary_run(r_b, r_len, r_free, r_street, nb)

    # ---- upper-floor windows on every free run ------------------------------------------------------------------------
    win_runs = r_idx[r_free & (r_len >= MIN_WINDOW_RUN_M) & (rows[r_b] > 0) & ~is_garage[r_b]]
    if len(win_runs):
        nbay = np.clip(np.floor(r_len[win_runs] / bay_w[r_b[win_runs]]).astype(np.int64), 1, MAX_BAYS_PER_RUN)
        bay_run = np.repeat(win_runs, nbay)
        k = _index_within(nbay)
        step = r_len[bay_run] / np.repeat(nbay, nbay)
        t = (k + 0.5) * step
        bx = r_x0[bay_run] + r_ux[bay_run] * t
        by = r_y0[bay_run] + r_uy[bay_run] * t
        bb = r_b[bay_run]

        nrow = rows[bb].astype(np.int64)
        w_bay = np.repeat(np.arange(len(bay_run), dtype=np.int64), nrow)
        f = _index_within(nrow)                      # 0 -> first floor above ground
        wb = bb[w_bay]
        curtain = wt[wb] == _CURTAIN_WALL
        sill = np.where(curtain, 0.0, np.where(office_like[wb], SILL_OFFICE_M, SILL_ABOVE_FLOOR_M))
        wz = gz[wb] + gfh[wb] + f * fh[wb] + sill
        wyaw = r_yaw[bay_run][w_bay]
        wx, wy = bx[w_bay], by[w_bay]
        vseed = _seed_mix(seed[wb], bay_run[w_bay], f, salt=SALT_VARIANT)
        lit_p = np.where(residential[wb], LIT_SHARE_RESIDENTIAL, np.where(office_like[wb], LIT_SHARE_OFFICE, 0.15))
        lit = (E.rand_unit(vseed, SALT_WINDOW_LIT) < lit_p)
        # ``through_wall_ac_sleeve`` names the sleeve opening, not a window: the 2000s infill type really has a
        # normal one-over-one sash with the sleeve punched underneath, so place both.
        wt_place = np.where(wt[wb] == _THROUGH_WALL, E.WINDOW_TYPE_INDEX["double_hung_1_1"], wt[wb])
        kid = np.asarray([kit_id("window", n) for n in E.WINDOW_TYPE_NAMES], dtype=np.uint32)[wt_place]
        wscale = np.where(curtain, np.minimum(step[w_bay] / np.maximum(bay_w[wb], 0.5), 2.0), 1.0)
        acc.add(kid, b["bin"][wb], wx, wy, wz, wyaw, wscale.astype(np.float32), vseed,
                np.where(lit, FLAG_LIT, 0).astype(np.uint32))

        # window air-conditioners on a share of residential windows (never on curtain wall)
        ac_ok = residential[wb] & CLASS.has_ac_units[fc[wb]] & ~curtain
        ac = ac_ok & (E.rand_unit(vseed, SALT_AC_UNIT) < AC_UNIT_SHARE)
        if ac.any():
            acc.add(np.uint32(kit_id("window_accessory", "ac_unit_window")), b["bin"][wb][ac], wx[ac], wy[ac],
                    (wz[ac] + 0.05), wyaw[ac], np.float32(1.0), vseed[ac], np.uint32(0))
        # through-wall AC sleeves (the 'Fedders special' and post-war slabs) sit under the sill
        tw = CLASS.has_through_wall_ac[fc[wb]] & ~curtain
        if tw.any():
            acc.add(np.uint32(kit_id("window_accessory", "ac_sleeve_through_wall")), b["bin"][wb][tw], wx[tw], wy[tw],
                    (wz[tw] - 0.55), wyaw[tw], np.float32(1.0), vseed[tw], np.uint32(0))

    # ---- ground floor: storefront / stoop+door / lobby / garage --------------------------------------------------------
    _ground_floor(acc, b, nb, r_b, r_len, r_x0, r_y0, r_ux, r_uy, r_yaw, r_free, r_street, prim, gz, gfh, fh,
                  bay_w, wt, fc, seed, is_garage, residential, office_like, cls1)

    # ---- fire escapes ---------------------------------------------------------------------------------------------------
    fe = np.nonzero(b["has_fire_escape"] & (prim >= 0) & (rows > 0))[0]
    if len(fe):
        run = prim[fe]
        t = r_len[run] * 0.5
        fx = r_x0[run] + r_ux[run] * t
        fy = r_y0[run] + r_uy[run] * t
        nfl = rows[fe].astype(np.int64)
        rep = np.repeat(np.arange(len(fe), dtype=np.int64), nfl)
        f = _index_within(nfl)
        z = gz[fe][rep] + gfh[fe][rep] + f * fh[fe][rep]
        vs = _seed_mix(seed[fe][rep], run[rep], f, salt=SALT_VARIANT + 1)
        acc.add(np.uint32(kit_id("fire_escape", "fire_escape_balcony")), b["bin"][fe][rep], fx[rep], fy[rep], z,
                r_yaw[run][rep], np.float32(1.0), vs, np.uint32(0))
        # the drop ladder hangs from the lowest balcony, the roof ladder climbs off the top one
        low = f == 0
        acc.add(np.uint32(kit_id("fire_escape", "fire_escape_drop_ladder")), b["bin"][fe][rep][low], fx[rep][low],
                fy[rep][low], z[low], r_yaw[run][rep][low], np.float32(1.0), vs[low], np.uint32(0))
        top = f == (nfl[rep] - 1)
        acc.add(np.uint32(kit_id("fire_escape", "fire_escape_balcony_top")), b["bin"][fe][rep][top], fx[rep][top],
                fy[rep][top], z[top], r_yaw[run][rep][top], np.float32(1.0), vs[top], np.uint32(0))
        acc.add(np.uint32(kit_id("fire_escape", "fire_escape_roof_ladder")), b["bin"][fe][rep][top], fx[rep][top],
                fy[rep][top], (z[top] + fh[fe][rep][top]), r_yaw[run][rep][top], np.float32(1.0), vs[top],
                np.uint32(0))

    # ---- cornice / parapet at the roofline -------------------------------------------------------------------------------
    from .kit_ids import CORNICE_STYLES
    corn_runs = r_idx[r_free & (r_len >= 2.0) & b["has_cornice"][r_b] & (r_street | (r_idx == prim[r_b]))]
    if len(corn_runs):
        seg, t, seg_len = _split_run(corn_runs, r_len[corn_runs], CORNICE_NOMINAL_W_M)
        cb = r_b[seg]
        cx = r_x0[seg] + r_ux[seg] * t
        cy = r_y0[seg] + r_uy[seg] * t
        style = CLASS.cornice_style[fc[cb]]
        kid = np.asarray([kit_id("cornice", n) for n in CORNICE_STYLES], dtype=np.uint32)[style]
        acc.add(kid, b["bin"][cb], cx, cy, rz[cb], r_yaw[seg], (seg_len / CORNICE_NOMINAL_W_M).astype(np.float32),
                _seed_mix(seed[cb], seg, t.astype(np.int64), salt=SALT_VARIANT + 2), np.uint32(0))
    flat_roof = CLASS.roof_shape[fc] == E.ROOF_FLAT
    par_runs = r_idx[r_free & (r_len >= 2.0) & flat_roof[r_b] & ~b["has_cornice"][r_b] & ~is_garage[r_b]]
    if len(par_runs):
        seg, t, seg_len = _split_run(par_runs, r_len[par_runs], PARAPET_NOMINAL_W_M)
        pb = r_b[seg]
        px = r_x0[seg] + r_ux[seg] * t
        py = r_y0[seg] + r_uy[seg] * t
        mat = b["material_primary"][pb]
        piece = np.where(np.isin(mat, [E.CONCRETE, E.PRECAST, E.METAL_PANEL, E.GLASS_CURTAIN]), 2,
                         np.where(np.isin(mat, [E.LIMESTONE, E.GRANITE, E.BROWNSTONE, E.STONE_RUBBLE]), 1, 0))
        kid = np.asarray([kit_id("parapet", n) for n in ("parapet_brick", "parapet_stone", "parapet_concrete")],
                         dtype=np.uint32)[piece]
        acc.add(kid, b["bin"][pb], px, py, rz[pb], r_yaw[seg], (seg_len / PARAPET_NOMINAL_W_M).astype(np.float32),
                _seed_mix(seed[pb], seg, t.astype(np.int64), salt=SALT_VARIANT + 3), np.uint32(0))

    # ---- string courses, quoins, pilasters and columns on the street facade -------------------------------------------
    street_runs = r_idx[r_free & (r_len >= 3.0) & (r_street | (r_idx == prim[r_b]))]
    if len(street_runs):
        sb2 = r_b[street_runs]
        # a string course marks the top of the ground floor; it runs the length of the facade in bounded segments
        sc = street_runs[CLASS.has_string_course[fc[sb2]]]
        if len(sc):
            seg, t, seg_len = _split_run(sc, r_len[sc], 2.0)
            cb = r_b[seg]
            mat = b["material_primary"][cb]
            piece = np.where(np.isin(mat, [E.TERRACOTTA]), 2,
                             np.where(np.isin(mat, [E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK, E.WHITE_GLAZED_BRICK]), 1, 0))
            kid = np.asarray([kit_id("string_course", n) for n in
                              ("string_course_stone", "string_course_brick", "belt_course_terracotta")],
                             dtype=np.uint32)[piece]
            acc.add(kid, b["bin"][cb], r_x0[seg] + r_ux[seg] * t, r_y0[seg] + r_uy[seg] * t,
                    (gz[cb] + gfh[cb]), r_yaw[seg], (seg_len / 2.0).astype(np.float32),
                    _seed_mix(seed[cb], seg, t.astype(np.int64), salt=SALT_VARIANT + 8), np.uint32(0))
        # quoins and pilasters stand at both ends of the facade, full height
        for feat, cat, roles, salt in (
                (CLASS.has_quoins, "quoin", ("quoin_limestone", "quoin_brownstone", "quoin_brick"), 9),
                (CLASS.has_pilasters, "pilaster", ("pilaster_stone", "pilaster_brick", "pilaster_cast_iron"), 10),
                (CLASS.has_columns, "pilaster", ("column_stone", "column_stone", "column_stone"), 11)):
            sel = street_runs[feat[fc[r_b[street_runs]]]]
            if not len(sel):
                continue
            end = np.repeat(sel, 2)
            side = np.tile(np.array([0.35, -0.35]), len(sel))
            t = np.where(side > 0, side, r_len[end] + side)
            mat = b["material_primary"][r_b[end]]
            piece = np.where(np.isin(mat, [E.CAST_IRON]), 2,
                             np.where(np.isin(mat, [E.RED_BRICK, E.BROWN_BRICK, E.TAN_BRICK]), 1, 0))
            kid = np.asarray([kit_id(cat, n) for n in roles], dtype=np.uint32)[piece]
            eb = r_b[end]
            acc.add(kid, b["bin"][eb], r_x0[end] + r_ux[end] * t, r_y0[end] + r_uy[end] * t, gz[eb], r_yaw[end],
                    np.float32(1.0), _seed_mix(seed[eb], end, (side > 0).astype(np.int64), salt=SALT_VARIANT + salt),
                    np.uint32(0))
        # an entrance canopy over the door of the classes that really have one
        can = street_runs[CLASS.has_canopy[fc[r_b[street_runs]]] & (r_idx[street_runs] == prim[r_b[street_runs]])]
        if len(can):
            cb = r_b[can]
            t = r_len[can] * 0.5
            acc.add(np.uint32(kit_id("door_entry", "canopy_entry")), b["bin"][cb],
                    r_x0[can] + r_ux[can] * t, r_y0[can] + r_uy[can] * t, gz[cb], r_yaw[can], np.float32(1.0),
                    _seed_mix(seed[cb], can, salt=SALT_VARIANT + 12), np.uint32(FLAG_LIT))
        # ivy on the free facade of the classes whose typology carries it
        ivy = street_runs[CLASS.has_ivy[fc[r_b[street_runs]]]]
        if len(ivy):
            ib = r_b[ivy]
            t = r_len[ivy] * 0.5
            acc.add(np.uint32(kit_id("vegetation", "ivy_panel")), b["bin"][ib],
                    r_x0[ivy] + r_ux[ivy] * t, r_y0[ivy] + r_uy[ivy] * t, gz[ib], r_yaw[ivy],
                    np.minimum(r_len[ivy] / 2.0, MAX_RUN_SCALE).astype(np.float32),
                    _seed_mix(seed[ib], ivy, salt=SALT_VARIANT + 13), np.uint32(0))

    # ---- sidewalk sheds (real active DOB permits) ------------------------------------------------------------------------
    shed_runs = r_idx[r_free & (r_len >= 3.0) & b["has_scaffold"][r_b] & (r_street | (r_idx == prim[r_b]))]
    if len(shed_runs):
        n_bay = np.clip(np.ceil(r_len[shed_runs] / SHED_BAY_M).astype(np.int64), 1, MAX_SHED_BAYS)
        rep = np.repeat(shed_runs, n_bay)
        k = _index_within(n_bay)
        step = r_len[rep] / np.repeat(n_bay, n_bay)
        t = (k + 0.5) * step
        sx = r_x0[rep] + r_ux[rep] * t
        sy = r_y0[rep] + r_uy[rep] * t
        sb = r_b[rep]
        vs = _seed_mix(seed[sb], rep, k, salt=SALT_VARIANT + 4)
        acc.add(np.uint32(kit_id("scaffold", "sidewalk_shed_bay")), b["bin"][sb], sx, sy, gz[sb], r_yaw[rep],
                (step / SHED_BAY_M).astype(np.float32), vs, np.uint32(0))
        # the shed is capped at both ends by the corner module (the kit exports no separate shed light)
        ends = (k == 0) | (k == (np.repeat(n_bay, n_bay) - 1))
        acc.add(np.uint32(kit_id("scaffold", "sidewalk_shed_end")), b["bin"][sb][ends], sx[ends], sy[ends],
                gz[sb][ends], r_yaw[rep][ends], np.float32(1.0), vs[ends], np.uint32(FLAG_LIT))

    # ---- roof: water tower, bulkheads, HVAC, antennas -----------------------------------------------------------------
    _roof_equipment(acc, b, geoms, fc, floors, rz, seed, nb)

    # a brick chimney on the pitched-roof house stock (roof_type 1 gable, 2 hip, 3 mansard)
    chim = np.nonzero(np.isin(b["roof_type"], [1, 2, 3]) & (b["footprint_area"] >= 35.0))[0]
    if len(chim):
        anchor = shapely.get_coordinates(shapely.point_on_surface(geoms[chim]))
        off = 0.22 * np.sqrt(np.maximum(b["footprint_area"][chim], 1.0))
        ang = E.rand_unit(seed[chim], 640) * 2.0 * np.pi
        px = anchor[:, 0] + np.cos(ang) * off
        py = anchor[:, 1] + np.sin(ang) * off
        inside = shapely.contains_xy(geoms[chim], px, py)
        px = np.where(inside, px, anchor[:, 0])
        py = np.where(inside, py, anchor[:, 1])
        acc.add(np.uint32(kit_id("hvac", "chimney_brick")), b["bin"][chim], px, py, rz[chim],
                (E.rand_unit(seed[chim], 641) * 360.0 - 180.0).astype(np.float32), np.float32(1.0),
                _seed_mix(seed[chim], chim, salt=SALT_VARIANT + 14), np.uint32(0))

    rec = acc.result()
    return _cap_per_building(rec)


def _primary_run(r_b: np.ndarray, r_len: np.ndarray, r_free: np.ndarray, r_street: np.ndarray, nb: int) -> np.ndarray:
    """Index of each building's primary run (longest street-facing free run, else longest free run), −1 when none."""
    score = np.where(r_free & (r_len >= MIN_GROUND_RUN_M), r_len, -1.0) + np.where(r_street, 1e6, 0.0)
    prim = np.full(nb, -1, dtype=np.int64)
    if len(r_b) == 0:
        return prim
    order = np.lexsort((-score, r_b))
    bs = r_b[order]
    firsts = np.ones(len(order), dtype=bool)
    firsts[1:] = bs[1:] != bs[:-1]
    idx = order[firsts]
    ok = score[idx] > 0
    prim[bs[firsts][ok]] = idx[ok]
    return prim


def _ground_floor(acc: Accum, b, nb, r_b, r_len, r_x0, r_y0, r_ux, r_uy, r_yaw, r_free, r_street, prim,
                  gz, gfh, fh, bay_w, wt, fc, seed, is_garage, residential, office_like, cls1) -> None:
    """Ground-floor treatment: storefront bays, stoop and entrance, lobby door, garage door, ground windows."""
    r_idx = np.arange(len(r_b), dtype=np.int64)
    has_sf = b["has_storefront"].astype(bool)
    sf_kind = b["storefront_kind_primary"].astype(np.int64)
    first_off = b["first_floor_offset"].astype(np.float64)
    entry_z = gz + np.where(np.isfinite(first_off) & (first_off > 0.0) & (first_off < 4.0), first_off, 0.0)

    # ---- storefronts: street-facing free runs of buildings with real retail evidence --------------------------------
    sf_runs = r_idx[r_free & (r_len >= 3.2) & has_sf[r_b] & (r_street | (r_idx == prim[r_b]))]
    sf_bay_kids = np.asarray([kit_id("storefront", n) for n in
                              ("storefront_bay_3_6", "storefront_bay_4_8", "storefront_bay_6_0")], dtype=np.uint32)
    sf_bay_w = np.asarray(E.STOREFRONT_BAY_WIDTHS_M, dtype=np.float64)
    if len(sf_runs):
        n_bay = np.clip(np.rint(r_len[sf_runs] / STOREFRONT_TARGET_BAY_M).astype(np.int64), 1, MAX_STOREFRONT_BAYS)
        rep = np.repeat(sf_runs, n_bay)
        k = _index_within(n_bay)
        step = r_len[rep] / np.repeat(n_bay, n_bay)
        t = (k + 0.5) * step
        sx = r_x0[rep] + r_ux[rep] * t
        sy = r_y0[rep] + r_uy[rep] * t
        sb = r_b[rep]
        vs = _seed_mix(seed[sb], rep, k, salt=SALT_STOREFRONT_BAY)
        pick = np.argmin(np.abs(step[:, None] - sf_bay_w[None, :]), axis=1)
        acc.add(sf_bay_kids[pick], b["bin"][sb], sx, sy, gz[sb], r_yaw[rep], (step / sf_bay_w[pick]).astype(np.float32),
                vs, np.uint32(FLAG_LIT))
        # sign band above the glass: segments of at most MAX_RUN_SCALE nominal widths along the shopfront
        bseg, bt, blen = _split_run(sf_runs, r_len[sf_runs], 3.6)
        bb2 = r_b[bseg]
        acc.add(np.uint32(kit_id("storefront", "sign_band")), b["bin"][bb2],
                r_x0[bseg] + r_ux[bseg] * bt, r_y0[bseg] + r_uy[bseg] * bt,
                (gz[bb2] + np.minimum(gfh[bb2], 4.5) - 0.85), r_yaw[bseg], (blen / 3.6).astype(np.float32),
                _seed_mix(seed[bb2], bseg, bt.astype(np.int64), salt=SALT_STOREFRONT_BAY + 1), np.uint32(FLAG_LIT))
        # roll-down gate on a share of the bays (the runtime lowers them at night: FLAG_ANIMATED)
        gate_kids = np.asarray([kit_id("storefront", n) for n in
                                ("roll_gate_open_3_6", "roll_gate_open_4_8", "roll_gate_open_6_0")], dtype=np.uint32)
        gate = (E.rand_unit(vs, SALT_GATE) < ROLL_GATE_SHARE) & CLASS.has_roll_gate[fc[sb]]
        if gate.any():
            acc.add(gate_kids[pick[gate]], b["bin"][sb][gate], sx[gate], sy[gate],
                    gz[sb][gate], r_yaw[rep][gate], (step[gate] / sf_bay_w[pick[gate]]).astype(np.float32), vs[gate],
                    np.uint32(FLAG_ANIMATED))
        # fabric awning, in the same three bay widths the kit exports
        awn_kids = np.asarray([kit_id("storefront", n) for n in ("awning_3_6", "awning_4_8", "awning_6_0")],
                              dtype=np.uint32)
        awn = (E.rand_unit(vs, SALT_GATE + 1) < AWNING_SHARE) & CLASS.has_awning[fc[sb]]
        if awn.any():
            acc.add(awn_kids[pick[awn]], b["bin"][sb][awn], sx[awn], sy[awn],
                    (gz[sb][awn] + 2.85), r_yaw[rep][awn], (step[awn] / sf_bay_w[pick[awn]]).astype(np.float32),
                    vs[awn], np.uint32(0))
        # one entrance door and one interior shell per storefront run
        first_bay = k == 0
        acc.add(np.uint32(kit_id("storefront", "storefront_door")), b["bin"][sb][first_bay], sx[first_bay],
                sy[first_bay], gz[sb][first_bay], r_yaw[rep][first_bay], np.float32(1.0), vs[first_bay], np.uint32(0))
        interior_for = np.asarray([E.STOREFRONT_INTERIOR_KINDS.index(E.STOREFRONT_INTERIOR_FOR_KIND.get(k2, "vacant") or "vacant")
                                   for k2 in E.STOREFRONT_KINDS], dtype=np.int64)
        int_kids = np.asarray([kit_id("storefront_interior", n) for n in E.STOREFRONT_INTERIOR_KINDS], dtype=np.uint32)
        mid = k == (np.repeat(n_bay, n_bay) // 2)
        acc.add(int_kids[interior_for[sf_kind[sb][mid]]], b["bin"][sb][mid], sx[mid], sy[mid], gz[sb][mid],
                r_yaw[rep][mid], np.float32(1.0), vs[mid], np.uint32(FLAG_INTERIOR | FLAG_LIT))

    # ---- garage doors --------------------------------------------------------------------------------------------------
    gar = np.nonzero(is_garage & (prim >= 0))[0]
    if len(gar):
        run = prim[gar]
        t = r_len[run] * 0.5
        gx = r_x0[run] + r_ux[run] * t
        gy = r_y0[run] + r_uy[run] * t
        resid_garage = b["feature_code"][gar] == 5110
        kid = np.where(resid_garage, kit_id("door_entry", "garage_door_residential"),
                       kit_id("door_entry", "garage_door_commercial")).astype(np.uint32)
        acc.add(kid, b["bin"][gar], gx, gy, gz[gar], r_yaw[run], np.float32(1.0),
                _seed_mix(seed[gar], run, salt=SALT_VARIANT + 5), np.uint32(0))

    # ---- entrance, stoop and ground-floor windows for everything else ---------------------------------------------------
    ent = np.nonzero(~is_garage & ~has_sf & (prim >= 0))[0]
    if not len(ent):
        return
    run = prim[ent]
    L = r_len[run]
    nbay = np.clip(np.floor(L / bay_w[ent]).astype(np.int64), 1, MAX_BAYS_PER_RUN)
    # the entrance takes one bay: off-centre on a rowhouse (the stoop side), centred otherwise
    stoop = b["has_stoop"][ent].astype(bool)
    door_bay = np.where(stoop & (nbay >= 3), 0, nbay // 2)
    step = L / nbay
    dt = (door_bay + 0.5) * step
    dx = r_x0[run] + r_ux[run] * dt
    dy = r_y0[run] + r_uy[run] * dt
    dyaw = r_yaw[run]
    vs = _seed_mix(seed[ent], run, salt=SALT_VARIANT + 6)
    tall = b["floors"][ent] >= 8
    door_kid = np.where(tall & office_like[ent], kit_id("door_entry", "door_office_lobby"),
                        np.where(tall | (~residential[ent]), kit_id("door_entry", "door_residential_lobby"),
                                 kit_id("door_entry", "door_residential"))).astype(np.uint32)
    acc.add(door_kid, b["bin"][ent], dx, dy, entry_z[ent], dyaw, np.float32(1.0), vs, np.uint32(FLAG_LIT))

    st = stoop & (entry_z[ent] - gz[ent] >= 0.25)
    if st.any():
        high = (entry_z[ent] - gz[ent]) >= 1.6
        wood = np.isin(b["material_primary"][ent], [E.VINYL_SIDING, E.WOOD_CLAPBOARD])
        piece = np.where(high, kit_id("door_entry", "stoop_high_brownstone"),
                         np.where(wood, kit_id("door_entry", "stoop_wood"),
                                  kit_id("door_entry", "stoop_low_brick"))).astype(np.uint32)
        acc.add(piece[st], b["bin"][ent][st], dx[st], dy[st], gz[ent][st], dyaw[st], np.float32(1.0), vs[st],
                np.uint32(0))
        area = st & CLASS.has_areaway[fc[ent]]
        if area.any():
            acc.add(np.uint32(kit_id("fence", "areaway_railing")), b["bin"][ent][area], dx[area], dy[area],
                    gz[ent][area], dyaw[area], np.float32(1.0), vs[area], np.uint32(0))

    # ground-floor windows on the street run, skipping the entrance bay
    ok = (L >= MIN_GROUND_RUN_M) & (nbay >= 2)
    if ok.any():
        e2 = np.nonzero(ok)[0]
        cnt = nbay[e2] - 1
        rep = np.repeat(e2, cnt)
        k = _index_within(cnt)
        k = k + (k >= door_bay[rep])
        t = (k + 0.5) * step[rep]
        gx = r_x0[run[rep]] + r_ux[run[rep]] * t
        gy = r_y0[run[rep]] + r_uy[run[rep]] * t
        bi = ent[rep]
        curtain = wt[bi] == _CURTAIN_WALL
        z = np.where(curtain, gz[bi], gz[bi] + GROUND_SILL_M + np.maximum(entry_z[bi] - gz[bi] - 0.6, 0.0))
        vseed = _seed_mix(seed[bi], run[rep], k, salt=SALT_VARIANT + 7)
        kid = np.asarray([kit_id("window", n) for n in E.WINDOW_TYPE_NAMES], dtype=np.uint32)[wt[bi]]
        lit = E.rand_unit(vseed, SALT_WINDOW_LIT) < LIT_SHARE_RESIDENTIAL
        acc.add(kid, b["bin"][bi], gx, gy, z, r_yaw[run[rep]], np.float32(1.0), vseed,
                np.where(lit, FLAG_LIT, 0).astype(np.uint32))


def _roof_equipment(acc: Accum, b, geoms: np.ndarray, fc, floors, rz, seed, nb) -> None:
    """Water towers, bulkheads, HVAC and antennas, placed on real points inside the footprint."""
    anchor = shapely.get_coordinates(shapely.point_on_surface(geoms))
    ax, ay = anchor[:, 0], anchor[:, 1]
    area = np.maximum(b["footprint_area"].astype(np.float64), 1.0)
    r = ROOF_INSET_FRACTION * np.sqrt(area)

    def place_ring(sel: np.ndarray, count: np.ndarray, salt: int):
        """Deterministic points on a ring around the roof anchor, snapped back inside the footprint."""
        rep = np.repeat(sel, count)
        k = _index_within(count)
        n = np.repeat(count, count)
        ang = 2.0 * np.pi * (k / np.maximum(n, 1)) + E.rand_unit(seed[rep], salt) * 2.0 * np.pi
        rad = r[rep] * (0.55 + 0.35 * E.rand_unit(_seed_mix(seed[rep], k, salt=salt), salt + 1))
        px = ax[rep] + np.cos(ang) * rad
        py = ay[rep] + np.sin(ang) * rad
        inside = shapely.contains_xy(geoms[rep], px, py)
        px = np.where(inside, px, ax[rep])
        py = np.where(inside, py, ay[rep])
        return rep, k, px, py

    # water tower
    tank = np.nonzero(b["has_water_tower"].astype(bool))[0]
    if len(tank):
        kind = b["water_tower_kind"][tank].astype(np.int64)
        ang = E.rand_unit(seed[tank], 601) * 2.0 * np.pi
        rad = r[tank] * 0.55
        px = ax[tank] + np.cos(ang) * rad
        py = ay[tank] + np.sin(ang) * rad
        inside = shapely.contains_xy(geoms[tank], px, py)
        px = np.where(inside, px, ax[tank])
        py = np.where(inside, py, ay[tank])
        kid_by_kind = np.zeros(4, dtype=np.uint32)
        for kk, nm in TANK_PIECE.items():
            kid_by_kind[kk] = kit_id("water_tower", nm)
        yaw = (E.rand_unit(seed[tank], 602) * 360.0 - 180.0).astype(np.float32)
        acc.add(kid_by_kind[kind], b["bin"][tank], px, py, rz[tank], yaw, np.float32(1.0),
                _seed_mix(seed[tank], kind, salt=603), np.uint32(0))

    # bulkheads / HVAC / vents / antennas: ``rooftop_units`` pieces, kind chosen by class and building size
    units = b["rooftop_units"].astype(np.int64)
    sel = np.nonzero(units > 0)[0]
    if not len(sel):
        return
    cnt = units[sel]
    rep, k, px, py = place_ring(sel, cnt, 610)
    vs = _seed_mix(seed[rep], k, salt=611)
    big = area[rep] >= 900.0
    hvac_class = CLASS.has_rooftop_hvac[fc[rep]]
    tall = floors[rep] >= 8
    choice = np.where(k == 0, np.where(tall, 1, 0),                        # bulkhead_elevator / bulkhead_stair
                      np.where((k == 1) & tall, 2,                          # bulkhead_mechanical
                               np.where(hvac_class & big, 4,                # rooftop_ac_large
                                        np.where(hvac_class, 3,             # rooftop_ac_small
                                                 np.where(k % 3 == 0, 5, np.where(k % 3 == 1, 6, 7))))))
    names = ("bulkhead_stair", "bulkhead_elevator", "bulkhead_mechanical", "rooftop_ac_small", "rooftop_ac_large",
             "exhaust_fan", "vent_pipe", "satellite_dish")
    cats = ("bulkhead", "bulkhead", "bulkhead", "hvac", "hvac", "hvac", "hvac", "hvac")
    kid_tbl = np.asarray([kit_id(c, n) for c, n in zip(cats, names)], dtype=np.uint32)
    yaw = (E.rand_unit(vs, 612) * 360.0 - 180.0).astype(np.float32)
    acc.add(kid_tbl[choice], b["bin"][rep], px, py, rz[rep], yaw, np.float32(1.0), vs, np.uint32(0))

    ant = np.nonzero(CLASS.has_cell_antennas[fc] & (floors >= 6) & (units >= 4))[0]
    if len(ant):
        rep2, k2, px2, py2 = place_ring(ant, np.full(len(ant), 3, dtype=np.int64), 620)
        vs2 = _seed_mix(seed[rep2], k2, salt=621)
        acc.add(np.uint32(kit_id("antenna", "cell_antenna_panel")), b["bin"][rep2], px2, py2, (rz[rep2] + 1.2),
                (E.rand_unit(vs2, 622) * 360.0 - 180.0).astype(np.float32), np.float32(1.0), vs2, np.uint32(0))


def _cap_per_building(rec: np.ndarray) -> np.ndarray:
    """Bound the record count per building (only the tallest curtain-wall towers ever reach the cap)."""
    if len(rec) == 0:
        return rec
    order = np.argsort(rec["bin"], kind="stable")
    rec = rec[order]
    bins = rec["bin"]
    starts = np.flatnonzero(np.concatenate([[True], bins[1:] != bins[:-1]]))
    counts = np.diff(np.append(starts, len(bins)))
    if counts.max() <= MAX_PLACEMENTS_PER_BUILDING:
        return rec
    within = np.arange(len(bins), dtype=np.int64) - np.repeat(starts, counts)
    return rec[within < MAX_PLACEMENTS_PER_BUILDING]


# --- writing ------------------------------------------------------------------------------------------------------------
def write_tile(rec: np.ndarray, tile: str, out_dir: Path, extra: dict | None = None) -> dict:
    """Write ``kit_placements.bin`` + ``.json`` header for one tile and return the header."""
    out_dir.mkdir(parents=True, exist_ok=True)
    bin_path = out_dir / "kit_placements.bin"
    json_path = out_dir / "kit_placements.json"
    order = np.lexsort((rec["kit_id"], rec["bin"])) if len(rec) else np.zeros(0, dtype=np.int64)
    rec = rec[order]
    buf = rec.tobytes()
    tmp = bin_path.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        f.write(buf)
    tmp.replace(bin_path)

    kid, cnt = (np.unique(rec["kit_id"], return_counts=True) if len(rec) else (np.zeros(0, dtype=np.uint32), np.zeros(0, dtype=np.int64)))
    from .kit_ids import piece_info, registry
    # bounds check at the source: a placement may only name a piece the kit has actually exported
    registered = {p["kit_id"] for p in registry()["pieces"]}
    unknown = sorted({int(k) for k in kid} - registered)
    if unknown:
        raise ValueError(f"{tile}: placements name kit ids absent from the catalog-derived registry: {unknown} "
                         f"(the kit exports no piece for them)")
    header = {
        "schema_version": 1,
        "schema": PLACEMENTS_SCHEMA,
        "tile": tile,
        "record_bytes": RECORD_BYTES,
        "byte_order": "little",
        "count": int(len(rec)),
        "bytes": len(buf),
        "sha256": hashlib.sha256(buf).hexdigest(),
        "fields": [
            {"name": "kit_id", "type": "uint32"}, {"name": "bin", "type": "int64"},
            {"name": "x", "type": "float32", "unit": "m", "crs": "NYC_TM"},
            {"name": "y", "type": "float32", "unit": "m", "crs": "NYC_TM"},
            {"name": "z", "type": "float32", "unit": "m", "datum": "NAVD88"},
            {"name": "yaw_deg", "type": "float32", "convention": "0 = east, counter-clockwise (DATA_CONTRACTS default)"},
            {"name": "scale", "type": "float32",
             "note": "uniform scale; for run pieces (cornice, parapet, sign band, storefront bay, roll gate, awning, "
                     "sidewalk shed) it is the along-run stretch factor relative to the piece's nominal width"},
            {"name": "variant_seed", "type": "uint32"},
            {"name": "flags", "type": "uint32", "bits": {"0": "lit at night", "1": "animated", "2": "interior-visible"}},
        ],
        "sorted_by": ["bin", "kit_id"],
        # ``kit_ids`` is the plain id list the cross-stage catalog check reads; the breakdown sits next to it.
        "kit_ids": [int(k) for k in kid],
        "kit_id_counts": [{**piece_info(int(k)), "count": int(c)} for k, c in zip(kid, cnt)],
        "buildings": int(len(np.unique(rec["bin"]))) if len(rec) else 0,
    }
    if extra:
        header.update(extra)
    tmp = json_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(header, f, indent=1)
    tmp.replace(json_path)
    return header


def read_tile(tile_dir: Path) -> np.ndarray:
    """Read a tile's placements back as a structured array (used by the validator and the tests)."""
    p = Path(tile_dir) / "kit_placements.bin"
    if not p.exists():
        return np.empty(0, dtype=PLACEMENT_DTYPE)
    raw = np.fromfile(p, dtype=PLACEMENT_DTYPE)
    return raw
