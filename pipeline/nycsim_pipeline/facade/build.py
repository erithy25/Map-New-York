"""Facade stage driver: ``python -m nycsim_pipeline facade <pass> [options]``.

Passes (each idempotent, each runnable on a subset with ``--tiles`` / ``--limit-groups``):

``geom``   footprint edge runs -> ``facade/edges/{group}.parquet`` + ``facade/geom_attrs.parquet``
``rules``  rule table + OSM/LPC material evidence -> ``facade/facade_attrs.parquet`` + ``rules_table.md``
``emit``   extend ``tiles/{tile}/buildings.parquet`` to the complete §5 schema and write ``kit_placements.bin``/``.json``
``all``    the three in order

Memory plan: the footprint WKB of all 1,083,026 buildings is held once as raw bytes (~0.3 GB) and decoded to shapely
geometry only for the tile block being processed, so peak RSS stays well under the 5 GB budget while the party-wall
test still sees every neighbour (each block is processed together with its eight neighbouring tile rows).
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from .. import manifest
from ..contracts import validate_parquet
from ..paths import PROCESSED, VERIFICATION
from ..tiling import Tile
from . import derive as D
from . import edges as EG
from . import enums as E
from . import osm_match
from . import placements as P
from . import roofs as RF
from . import rules as R
from . import schema as FS
from .kit_ids import write_registry

log = logging.getLogger("nycsim.facade.build")

BASE = PROCESSED / "buildings" / "buildings_base.parquet"
TILES_ROOT = PROCESSED / "tiles"
FACADE_DIR = PROCESSED / "facade"
EDGES_DIR = FACADE_DIR / "edges"
GEOM_ATTRS = FACADE_DIR / "geom_attrs.parquet"
FACADE_ATTRS = FACADE_DIR / "facade_attrs.parquet"
ROOF_ATTRS = PROCESSED / "buildings" / "roof_attrs.parquet"
ROADS = PROCESSED / "roads" / "segments.parquet"
REPORT_DIR = VERIFICATION / "facade"

BLOCK_TILES = 4          # 4 x 4 km blocks: compact bbox, ~10-45 k buildings each
FIDELITY_MATERIAL_REAL = 1 << 5
FIDELITY_ROOF_REAL = 1 << 2
FIDELITY_FACADE_INFERRED = 1 << 10

GEOM_COLS = ["tile", "bin", "footprint", "primary_facade_heading", "centroid_x", "centroid_y"]
ATTR_COLS = ["tile", "bin", "borough", "bldg_class", "year_built", "floors", "height", "footprint_area", "land_use",
             "lot_frontage", "bldg_frontage", "nta", "hist_district", "landmark_id", "lpc_style", "lpc_material",
             "has_storefront", "storefront_names", "storefront_kinds", "feature_code", "n_bldgs_on_lot",
             "is_primary_on_lot", "first_floor_offset", "lit_seed", "fidelity", "centroid_x", "centroid_y",
             "floor_height", "ground_floor_height", "ground_z", "roof_z"]


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


class Timer:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.last = self.t0
        self.steps: dict[str, float] = {}

    def lap(self, name: str) -> None:
        now = time.perf_counter()
        self.steps[name] = round(now - self.last, 2)
        self.last = now
        log.info("[%7.1fs] %s (%.1fs, rss %.0f MB)", now - self.t0, name, self.steps[name], _rss_mb())

    @property
    def total(self) -> float:
        return round(time.perf_counter() - self.t0, 2)


# ----------------------------------------------------------------------------------------------------------------------
def group_of(tile: str) -> str:
    t = Tile.parse(tile)
    return f"g_{math.floor(t.tx / BLOCK_TILES)}_{math.floor(t.ty / BLOCK_TILES)}"


def tile_groups(tiles: list[str]) -> dict[str, list[str]]:
    """Deterministic spatial grouping of tiles into 4 x 4 km blocks (identical in every pass)."""
    out: dict[str, list[str]] = {}
    for t in sorted(set(tiles)):
        out.setdefault(group_of(t), []).append(t)
    return dict(sorted(out.items()))


def neighbour_tiles(tiles: list[str]) -> set[str]:
    """The tiles themselves plus their eight neighbours (party walls cross tile boundaries)."""
    out: set[str] = set()
    for t in tiles:
        tt = Tile.parse(t)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.add(Tile(tt.tx + dx, tt.ty + dy).name)
    return out


def row_within_tile(tiles: np.ndarray) -> np.ndarray:
    """Row index inside each tile, given rows already sorted by tile (as buildings_base is)."""
    n = len(tiles)
    if n == 0:
        return np.zeros(0, dtype=np.int32)
    starts = np.flatnonzero(np.concatenate([[True], tiles[1:] != tiles[:-1]]))
    counts = np.diff(np.append(starts, n))
    return (np.arange(n, dtype=np.int64) - np.repeat(starts, counts)).astype(np.int32)


def _load_roads():
    """(STRtree, segment ids) over street centrelines, or (None, None) when the roads stage has not run."""
    if not ROADS.exists():
        return None, None
    try:
        df = pl.read_parquet(ROADS, columns=["segment_id", "geometry", "rw_type"])
    except Exception as exc:                       # pragma: no cover - defensive: a partial file from another stage
        log.warning("roads/segments.parquet unreadable (%s); falling back to primary_facade_heading", exc)
        return None, None
    df = df.filter(pl.col("rw_type").is_in(list(EG.STREET_RW_TYPES)))
    if df.height == 0:
        return None, None
    geom = shapely.from_wkb(df["geometry"].to_numpy())
    log.info("roads: %d street centrelines for street-facing classification", len(geom))
    return shapely.STRtree(geom), df["segment_id"].to_numpy().astype(np.int64)


# ----------------------------------------------------------------------------------------------------------------------
def pass_geom(only_tiles: set[str] | None, limit_groups: int | None, out_dir: Path) -> dict:
    """Merged facade runs, party walls and street-facing flags for every footprint."""
    t = Timer()
    tbl = pq.read_table(BASE, columns=GEOM_COLS)
    tiles = np.asarray(tbl["tile"].to_pylist())
    bins = tbl["bin"].to_numpy()
    heading = tbl["primary_facade_heading"].to_numpy(zero_copy_only=False).astype(np.float64)
    cx = tbl["centroid_x"].to_numpy(zero_copy_only=False)
    cy = tbl["centroid_y"].to_numpy(zero_copy_only=False)
    wkb = np.asarray(tbl["footprint"].to_pylist(), dtype=object)
    del tbl
    rows = row_within_tile(tiles)
    t.lap(f"load footprints ({len(bins):,} rows)")

    road_tree, road_ids = _load_roads()
    by_tile: dict[str, np.ndarray] = {}
    order = np.argsort(tiles, kind="stable")
    ut, ustart = np.unique(tiles[order], return_index=True)
    uend = np.append(ustart[1:], len(order))
    for name, s, e in zip(ut, ustart, uend):
        by_tile[str(name)] = order[s:e]

    all_tiles = sorted(by_tile)
    groups = tile_groups([t2 for t2 in all_tiles if only_tiles is None or t2 in only_tiles])
    if limit_groups:
        groups = dict(list(groups.items())[:limit_groups])
    edges_dir = out_dir / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)

    summary_parts: list[pl.DataFrame] = []
    stats = {"runs": 0, "runs_usable": 0, "runs_party_wall": 0, "runs_street_facing": 0, "runs_road_matched": 0}
    n_done = 0
    for gi, (gname, gtiles) in enumerate(groups.items()):
        emit_idx = np.concatenate([by_tile[t2] for t2 in gtiles if t2 in by_tile]) if gtiles else np.zeros(0, np.int64)
        if len(emit_idx) == 0:
            continue
        ctx_names = [t2 for t2 in neighbour_tiles(gtiles) if t2 in by_tile]
        ctx_idx = np.concatenate([by_tile[t2] for t2 in ctx_names])
        # local array: emitted rows first, then the neighbour-only rows
        extra = np.setdiff1d(ctx_idx, emit_idx, assume_unique=False)
        local = np.concatenate([emit_idx, extra])
        geoms_all = shapely.from_wkb(wkb[local])
        valid = shapely.is_valid(geoms_all)
        if not valid.all():
            geoms_all = np.where(valid, geoms_all, shapely.make_valid(geoms_all))
        tree = shapely.STRtree(geoms_all)
        tree_index = np.concatenate([np.arange(len(emit_idx), dtype=np.int64),
                                     np.full(len(extra), -1, dtype=np.int64)])
        geoms = geoms_all[: len(emit_idx)]

        rt, rid = None, None
        if road_tree is not None:
            xmin, ymin, xmax, ymax = shapely.total_bounds(geoms)
            box = shapely.box(xmin - EG.STREET_NEAR_M, ymin - EG.STREET_NEAR_M,
                              xmax + EG.STREET_NEAR_M, ymax + EG.STREET_NEAR_M)
            sel = road_tree.query(box, predicate="intersects")
            if len(sel):
                rt = shapely.STRtree(road_tree.geometries.take(sel))
                rid = road_ids[sel]

        runs = EG.compute_runs(geoms, heading[emit_idx], tree, tree_index, rt, rid)
        for k, v in runs.stats.items():
            stats[k] = stats.get(k, 0) + v
        summ = EG.building_summary(runs, len(emit_idx))
        mrr_short, mrr_long, mrr_head = RF.mrr_axes(geoms)

        edge_tbl = pa.Table.from_arrays([
            pa.array(tiles[emit_idx][runs.bidx]), pa.array(rows[emit_idx][runs.bidx], type=pa.int32()),
            pa.array(bins[emit_idx][runs.bidx], type=pa.int64()),
            pa.array(runs.x0), pa.array(runs.y0), pa.array(runs.x1), pa.array(runs.y1),
            pa.array(runs.length.astype(np.float32)), pa.array(runs.nx.astype(np.float32)),
            pa.array(runs.ny.astype(np.float32)), pa.array(runs.heading.astype(np.float32)),
            pa.array(runs.is_party), pa.array(runs.is_street), pa.array(runs.street_segment_id),
        ], schema=FS.edge_schema())
        pq.write_table(edge_tbl, edges_dir / f"{gname}.parquet", compression="snappy")

        summary_parts.append(pl.DataFrame({
            "tile": tiles[emit_idx], "row": rows[emit_idx], "bin": bins[emit_idx],
            "attached": summ["attached"], "n_free_runs": summ["n_free_runs"],
            "free_perimeter_m": summ["free_perimeter_m"], "primary_run_len_m": summ["primary_run_len_m"],
            "street_frontage_m": summ["street_frontage_m"], "is_corner": summ["is_corner"],
            "street_segment_id": summ["street_segment_id"],
            "mrr_short_m": mrr_short, "mrr_long_m": mrr_long, "mrr_heading": mrr_head,
        }))
        n_done += len(emit_idx)
        if (gi + 1) % 10 == 0 or gi + 1 == len(groups):
            log.info("geom %d/%d groups, %d buildings, rss %.0f MB", gi + 1, len(groups), n_done, _rss_mb())
    t.lap("edge runs")

    summary = pl.concat(summary_parts, how="vertical") if summary_parts else pl.DataFrame()
    summary = summary.sort(["tile", "row"])
    out_dir.mkdir(parents=True, exist_ok=True)
    gtbl = summary.to_arrow().cast(FS.geom_schema({"nycsim.stage": "facade_geom", "nycsim.rows": str(summary.height)}))
    pq.write_table(gtbl, out_dir / "geom_attrs.parquet", compression="snappy", row_group_size=262144)
    t.lap("geom_attrs.parquet")

    res = {"buildings": int(summary.height), "groups": len(groups), "elapsed_s": t.total, "max_rss_mb": round(_rss_mb(), 1),
           "roads_used": road_tree is not None, "runs": stats,
           "attached_buildings": int((summary["attached"] > 0).sum()) if summary.height else 0,
           "corner_buildings": int(summary["is_corner"].sum()) if summary.height else 0,
           "buildings_without_free_run": int((summary["n_free_runs"] == 0).sum()) if summary.height else 0,
           "steps_s": t.steps}
    log.info("geom pass: %s", json.dumps({k: v for k, v in res.items() if k != "steps_s"}))
    return res


# ----------------------------------------------------------------------------------------------------------------------
def pass_rules(out_dir: Path, limit_groups: int | None = None) -> dict:
    """Classify every building and derive all facade columns."""
    t = Timer()
    geom_path = out_dir / "geom_attrs.parquet"
    if not geom_path.exists():
        raise FileNotFoundError(f"{geom_path} missing: run the `geom` pass first")
    tbl = pq.read_table(BASE, columns=ATTR_COLS)
    df = pl.from_arrow(tbl)
    del tbl
    df = df.with_columns([pl.Series("row", row_within_tile(df["tile"].to_numpy()), dtype=pl.Int32),
                          pl.Series("base_row", np.arange(df.height, dtype=np.int64), dtype=pl.Int64)])
    g = pl.read_parquet(geom_path)
    gt = set(g["tile"].unique().to_list())
    if len(gt) < df["tile"].n_unique():
        # development run: the geom pass covered only part of the city, so classify exactly that part
        df = df.filter(pl.col("tile").is_in(sorted(gt)))
        log.info("subset run: %d tiles / %d buildings (geom_attrs covers %d tiles)", df["tile"].n_unique(),
                 df.height, len(gt))
    df = df.join(g, on=["tile", "row"], how="left", suffix="_g")
    for c, fill in (("attached", 0), ("n_free_runs", 0), ("free_perimeter_m", 0.0), ("primary_run_len_m", 0.0),
                    ("street_frontage_m", 0.0), ("street_segment_id", -1), ("mrr_short_m", 0.0),
                    ("mrr_long_m", 0.0), ("mrr_heading", 0.0)):
        df = df.with_columns(pl.col(c).fill_null(fill))
    df = df.with_columns(pl.col("is_corner").fill_null(False))
    t.lap(f"load attributes + geometry summary ({df.height:,} rows)")

    # ---- OSM match (real material / colour / roof / name evidence) ---------------------------------------------------
    m = _osm_matches(df, limit_groups)
    df = df.join(m, on=["tile", "row"], how="left")
    df = df.with_columns([
        pl.col("osm_id").fill_null(0).cast(pl.Int64),
        pl.col("osm_iou").fill_null(0.0).cast(pl.Float32),
        pl.col("osm_material").fill_null(-1).cast(pl.Int8),
        pl.col("osm_colour_material").fill_null(-1).cast(pl.Int8),
    ])
    t.lap(f"OSM footprint match ({m.height:,} matched)")

    # ---- LPC designation-report material -----------------------------------------------------------------------------
    lpc_vals = df["lpc_material"].to_list()
    cache: dict[str, int] = {}
    lpc_enum = np.empty(len(lpc_vals), dtype=np.int8)
    for i, v in enumerate(lpc_vals):
        if v not in cache:
            r = E.lpc_material_to_enum(v)
            cache[v] = -1 if r is None else int(r)
        lpc_enum[i] = cache[v]
    df = df.with_columns(pl.Series("lpc_material_enum", lpc_enum, dtype=pl.Int8))
    t.lap(f"LPC material mapping ({int((lpc_enum >= 0).sum()):,} rows with real material)")

    # ---- classify -----------------------------------------------------------------------------------------------------
    fc_s, rule_s, hits = R.classify(df)
    df = df.with_columns([fc_s, rule_s])
    t.lap("rule table")

    # ---- derive --------------------------------------------------------------------------------------------------------
    n = df.height
    fc = fc_s.to_numpy().astype(np.int64)
    floors = df["floors"].to_numpy().astype(np.int32)
    year = df["year_built"].to_numpy().astype(np.int32)
    area = df["footprint_area"].to_numpy().astype(np.float64)
    borough = df["borough"].to_numpy().astype(np.int8)
    seed = df["lit_seed"].to_numpy().astype(np.uint32)
    feature_code = df["feature_code"].to_numpy().astype(np.int32)
    cls1 = np.asarray([c[:1].encode() if c else b"" for c in df["bldg_class"].to_list()], dtype="S1")
    n_free = df["n_free_runs"].to_numpy().astype(np.int32)
    has_sf = df["has_storefront"].to_numpy().astype(bool)
    ffo = df["first_floor_offset"].to_numpy().astype(np.float64)

    base_prim = D.CLASS.material_primary[fc].astype(np.int8)
    base_sec = D.CLASS.material_secondary[fc].astype(np.int8)
    swap = (fc == D.PREWAR_INDUSTRIAL_CLASS) & (year > 0) & (year <= D.PREWAR_INDUSTRIAL_MAX_YEAR)
    if swap.any():
        base_prim[swap], base_sec[swap] = base_sec[swap].copy(), base_prim[swap].copy()
    gar = feature_code == 5110
    if gar.any():
        gp, gs = D.garage_material(np.asarray(df["bldg_class"].to_list(), dtype=object)[gar],
                                   np.asarray(df["nta"].to_list(), dtype=object)[gar], year[gar], R.FRAME_BELT_NTA)
        base_prim[gar] = gp
        base_sec[gar] = gs
    prim, sec, msrc, mreal = D.resolve_material(fc, df["osm_material"].to_numpy().astype(np.int8),
                                                df["osm_colour_material"].to_numpy().astype(np.int8), lpc_enum,
                                                base_prim, base_sec)
    front, fsrc = D.resolve_frontage(df["primary_run_len_m"].to_numpy().astype(np.float64),
                                     df["bldg_frontage"].to_numpy().astype(np.float64),
                                     df["lot_frontage"].to_numpy().astype(np.float64), area)
    cols, rws, bay = D.window_grid(fc, front, floors)
    tank, tank_kind = D.water_towers(fc, floors, year, area, feature_code)
    fesc = D.fire_escapes(fc, floors, year, borough, cls1, n_free)
    stoop = D.stoops(fc, floors, has_sf, ffo, cls1, n_free)
    corn = D.CLASS.has_cornice[fc] & (n_free > 0)
    units = D.rooftop_unit_count(fc, floors, area, seed, cls1)
    kinds = [[int(k) for k in (v or [])] for v in df["storefront_kinds"].to_list()]
    names = [[str(s) for s in (v or [])] for v in df["storefront_names"].to_list()]
    awn, awn_real = D.awning_texts(has_sf, names, kinds, fc, seed)
    sf_kind = D.storefront_kind_for_placement(fc, kinds, seed, df["is_corner"].to_numpy().astype(bool))
    t.lap("derive facade attributes")

    # ---- roof: measured massing from CityGML, shape from the ADR-013 rule -------------------------------------------
    roof_type = np.zeros(n, dtype=np.int8)
    roof_ref = np.array([""] * n, dtype=object)
    roof_real = np.zeros(n, dtype=bool)
    roof_src = np.full(n, RF.ROOF_SRC_DEFAULT_FLAT, dtype=np.int8)
    roof_state = "absent"
    if ROOF_ATTRS.exists():
        roof_type, roof_ref, roof_real, roof_src, roof_state = _apply_roof_attrs(df["bin"].to_numpy())
    gz_arr = df["ground_z"].to_numpy().astype(np.float64)
    rz_arr = df["roof_z"].to_numpy().astype(np.float64)
    r_type, r_pitch, r_ridge, r_eave, r_applied = RF.infer(
        np.asarray(df["bldg_class"].to_list(), dtype=object), feature_code, year, floors, area,
        df["attached"].to_numpy().astype(np.int32), df["mrr_short_m"].to_numpy().astype(np.float64),
        df["mrr_long_m"].to_numpy().astype(np.float64), df["mrr_heading"].to_numpy().astype(np.float64),
        df["lpc_style"].to_list(), gz_arr, rz_arr, D.CLASS.roof_shape[fc],
        np.asarray([E.load_classes()[i - 1].get("roof") == "pitched_tile" if 1 <= i <= len(E.load_classes()) else False
                    for i in range(D.CLASS.n)], dtype=bool)[fc])
    # a real source (CityGML mesh or an OSM roof:shape tag) always wins over the rule
    real_src = np.isin(roof_src, [RF.ROOF_SRC_CITYGML, RF.ROOF_SRC_OSM])
    use_rule = r_applied & ~real_src
    roof_type = np.where(use_rule, r_type, roof_type).astype(np.int8)
    roof_src = np.where(use_rule, RF.ROOF_SRC_FACADE_RULE, roof_src).astype(np.int8)
    roof_pitch = np.where(use_rule, r_pitch, 0.0).astype(np.float32)
    roof_ridge = np.where(use_rule, r_ridge, 0.0).astype(np.float32)
    roof_eave = np.where(use_rule, r_eave, rz_arr).astype(np.float32)
    log.info("roof: %s; shape inferred by rule on %d buildings, ROOF_REAL on %d", roof_state,
             int(use_rule.sum()), int(roof_real.sum()))

    # ---- fidelity --------------------------------------------------------------------------------------------------------
    fid = df["fidelity"].to_numpy().astype(np.uint32)
    fid &= np.uint32(~(FIDELITY_MATERIAL_REAL | FIDELITY_FACADE_INFERRED | FIDELITY_ROOF_REAL))
    fid |= np.where(mreal, FIDELITY_MATERIAL_REAL, 0).astype(np.uint32)
    fid |= np.where(mreal, 0, FIDELITY_FACADE_INFERRED).astype(np.uint32)   # §5.1: bit 10 set whenever bit 5 is clear
    fid |= np.where(roof_real, FIDELITY_ROOF_REAL, 0).astype(np.uint32)
    fid &= np.uint32(~RF.FIDELITY_ROOF_INFERRED)
    fid |= np.where(use_rule, RF.FIDELITY_ROOF_INFERRED, 0).astype(np.uint32)
    fid = fid.astype(np.uint16)

    attrs = pl.DataFrame({
        "tile": df["tile"], "row": df["row"], "bin": df["bin"],
        "roof_type": pl.Series(roof_type, dtype=pl.Int8),
        "roof_mesh_ref": pl.Series([str(x) for x in roof_ref], dtype=pl.Utf8),
        "facade_class": fc_s, "material_primary": pl.Series(prim, dtype=pl.Int8),
        "material_secondary": pl.Series(sec, dtype=pl.Int8),
        "window_type": pl.Series(D.CLASS.window_type[fc], dtype=pl.Int8),
        "window_cols": pl.Series(cols, dtype=pl.Int16), "window_rows": pl.Series(rws, dtype=pl.Int16),
        "has_fire_escape": pl.Series(fesc, dtype=pl.Boolean), "has_stoop": pl.Series(stoop, dtype=pl.Boolean),
        "has_cornice": pl.Series(corn, dtype=pl.Boolean), "has_water_tower": pl.Series(tank, dtype=pl.Boolean),
        "rooftop_units": pl.Series(units, dtype=pl.Int8), "awning_text": pl.Series(awn, dtype=pl.Utf8),
        "landmark_model": pl.Series([""] * n, dtype=pl.Utf8),
        "street_segment_id": df["street_segment_id"].cast(pl.Int64),
        "facade_rule": rule_s, "material_source": pl.Series(msrc, dtype=pl.Int8),
        "frontage_source": pl.Series(fsrc, dtype=pl.Int8),
        "facade_frontage_m": pl.Series(front, dtype=pl.Float32), "bay_width_m": pl.Series(bay, dtype=pl.Float32),
        "water_tower_kind": pl.Series(tank_kind, dtype=pl.Int8), "attached": df["attached"].cast(pl.Int16),
        "n_free_runs": df["n_free_runs"].cast(pl.Int16), "is_corner": df["is_corner"].cast(pl.Boolean),
        "free_perimeter_m": df["free_perimeter_m"].cast(pl.Float32),
        "street_frontage_m": df["street_frontage_m"].cast(pl.Float32),
        "storefront_kind_primary": pl.Series(sf_kind, dtype=pl.Int8),
        "awning_real": pl.Series(awn_real, dtype=pl.Boolean), "osm_iou": df["osm_iou"].cast(pl.Float32),
        "n_placements": pl.Series(np.zeros(n, dtype=np.int32), dtype=pl.Int32),
        "roof_source": pl.Series(roof_src, dtype=pl.Int8), "roof_pitch_deg": pl.Series(roof_pitch, dtype=pl.Float32),
        "roof_ridge_heading": pl.Series(roof_ridge, dtype=pl.Float32),
        "roof_eave_z": pl.Series(roof_eave, dtype=pl.Float32),
        "osm_id": df["osm_id"].cast(pl.Int64), "fidelity": pl.Series(fid, dtype=pl.UInt16),
    }).select([c for c, _ in FS.ATTRS_COLUMNS]).sort(["tile", "row"])

    out_dir.mkdir(parents=True, exist_ok=True)
    atbl = attrs.to_arrow().cast(FS.attrs_schema({
        "nycsim.stage": "facade_rules", "nycsim.rows": str(attrs.height),
        "nycsim.facade.rules_version": R.RULES_VERSION,
    }))
    pq.write_table(atbl, out_dir / "facade_attrs.parquet", compression="snappy", row_group_size=262144)
    t.lap("facade_attrs.parquet")

    summary = _rules_summary(df, attrs, hits, mreal, roof_state)
    summary["elapsed_s"] = t.total
    summary["max_rss_mb"] = round(_rss_mb(), 1)
    summary["steps_s"] = t.steps
    with open(out_dir / "rules_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_DIR / "rules_table.md", "w") as f:
        f.write(R.rules_table_markdown(hits, attrs.height))
    log.info("rules pass: %d buildings, %d classes used, MATERIAL_REAL %d",
             attrs.height, attrs["facade_class"].n_unique(), int(mreal.sum()))
    return summary


def _osm_matches(df: pl.DataFrame, limit_groups: int | None) -> pl.DataFrame:
    """Footprint-overlap match of OSM buildings, processed block by block."""
    if not osm_match.OSM_BUILDINGS.exists():
        log.warning("%s missing: no OSM material evidence", osm_match.OSM_BUILDINGS)
        return pl.DataFrame(schema={"tile": pl.Utf8, "row": pl.Int32, "osm_id": pl.Int64, "osm_iou": pl.Float32,
                                    "osm_material": pl.Int8, "osm_colour_material": pl.Int8})
    tiles = df["tile"].to_numpy()
    rowi = df["row"].to_numpy()
    bins = df["bin"].to_numpy()
    cx = df["centroid_x"].to_numpy()
    cy = df["centroid_y"].to_numpy()
    base_row = df["base_row"].to_numpy()
    # ``df`` may be a subset of buildings_base (development run), so index the footprint column by its base row
    wkb = np.asarray(pq.read_table(BASE, columns=["footprint"])["footprint"].to_pylist(), dtype=object)[base_row]
    groups = tile_groups(list(np.unique(tiles)))
    if limit_groups:
        groups = dict(list(groups.items())[:limit_groups])
    idx_by_group: dict[str, list[int]] = {}
    gnames = np.asarray([group_of(str(t)) for t in tiles])
    order = np.argsort(gnames, kind="stable")
    ug, us = np.unique(gnames[order], return_index=True)
    ue = np.append(us[1:], len(order))
    for gname, s, e in zip(ug, us, ue):
        idx_by_group[str(gname)] = order[s:e]

    parts: list[pl.DataFrame] = []
    for gi, gname in enumerate(groups):
        idx = idx_by_group.get(gname)
        if idx is None or len(idx) == 0:
            continue
        geoms = shapely.from_wkb(wkb[idx])
        valid = shapely.is_valid(geoms)
        if not valid.all():
            geoms = np.where(valid, geoms, shapely.make_valid(geoms))
        m = osm_match.match_window(bins[idx], geoms, cx[idx], cy[idx])
        if m.height:
            m = osm_match.encode_materials(m)
            pos = {int(b): i for i, b in enumerate(bins[idx])}
            sel = np.asarray([pos[int(b)] for b in m["bin"].to_list()], dtype=np.int64)
            m = m.with_columns([pl.Series("tile", tiles[idx][sel]), pl.Series("row", rowi[idx][sel], dtype=pl.Int32)])
            parts.append(m.select(["tile", "row", "osm_id", "osm_iou", "osm_material", "osm_colour_material"]))
        if (gi + 1) % 20 == 0:
            log.info("osm match %d/%d groups, rss %.0f MB", gi + 1, len(groups), _rss_mb())
    if not parts:
        return pl.DataFrame(schema={"tile": pl.Utf8, "row": pl.Int32, "osm_id": pl.Int64, "osm_iou": pl.Float32,
                                    "osm_material": pl.Int8, "osm_colour_material": pl.Int8})
    return pl.concat(parts, how="vertical").unique(subset=["tile", "row"], keep="first")


def _apply_roof_attrs(bins: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """Join ``buildings/roof_attrs.parquet`` (DATA_CONTRACTS §5.3, ADR-013).

    Returns ``(roof_type, roof_mesh_ref, roof_real, roof_source, state)``.  ``roof_source`` follows the §5.3
    ``roof_type_source`` codes; rows the CityGML stage marked inferred or default are handed back as "default flat"
    so the facade rule (which owns the house stock's roof shape, ADR-013) can claim them.
    """
    n = len(bins)
    cols = pq.ParquetFile(ROOF_ATTRS).schema_arrow.names
    need = [c for c in ("bin", "roof_type", "roof_mesh_ref", "citygml_match", "roof_type_source") if c in cols]
    if "bin" not in need or "roof_type" not in need:
        return (np.zeros(n, np.int8), np.array([""] * n, dtype=object), np.zeros(n, bool),
                np.full(n, RF.ROOF_SRC_DEFAULT_FLAT, np.int8),
                "present but missing bin/roof_type columns: ignored")
    ra = pl.read_parquet(ROOF_ATTRS, columns=need).unique(subset=["bin"], keep="first")
    left = pl.DataFrame({"bin": bins.astype(np.int64), "_i": np.arange(n, dtype=np.int64)})
    j = left.join(ra, on="bin", how="left").sort("_i")
    rt = j["roof_type"].fill_null(0).cast(pl.Int8).to_numpy().astype(np.int8)
    ref = (np.asarray(j["roof_mesh_ref"].fill_null("").to_list(), dtype=object) if "roof_mesh_ref" in need
           else np.array([""] * n, dtype=object))
    real = (j["citygml_match"].fill_null(False).to_numpy().astype(bool) if "citygml_match" in need
            else np.zeros(n, bool))
    src = (j["roof_type_source"].fill_null(RF.ROOF_SRC_DEFAULT_FLAT).cast(pl.Int8).to_numpy().astype(np.int8)
           if "roof_type_source" in need else np.where(real, RF.ROOF_SRC_CITYGML, RF.ROOF_SRC_DEFAULT_FLAT).astype(np.int8))
    # sources 2 (the CityGML stage's own inference) and 3 (default flat) are handed back as "default flat": ADR-013
    # gives the house stock's roof *shape* to the facade rule, so only the two real sources are carried through.
    from_real_source = np.isin(src, [RF.ROOF_SRC_CITYGML, RF.ROOF_SRC_OSM])
    rt = np.where(from_real_source, rt, 0).astype(np.int8)
    src = np.where(from_real_source, src, RF.ROOF_SRC_DEFAULT_FLAT).astype(np.int8)
    return rt, ref, real, src, f"joined {int(real.sum()):,} CityGML matches from {ROOF_ATTRS.name}"


def _rules_summary(df: pl.DataFrame, attrs: pl.DataFrame, hits: dict[str, int], mreal: np.ndarray,
                   roof_state: str) -> dict:
    total = attrs.height
    classes = E.load_classes()
    cname = {c["facade_class"]: c["id"] for c in classes}
    dist = attrs.group_by("facade_class").len().sort("len", descending=True)
    per_boro = (attrs.select(["facade_class"]).with_columns(df["borough"])
                .group_by(["borough", "facade_class"]).len().sort(["borough", "len"], descending=[False, True]))
    mat = attrs.group_by("material_primary").len().sort("len", descending=True)
    return {
        "schema_version": 1,
        "rules_version": R.RULES_VERSION,
        "buildings": total,
        "rules": len(R.RULES),
        "rule_hits": hits,
        "rules_with_no_hits": [k for k, v in hits.items() if v == 0],
        "classes_used": int(attrs["facade_class"].n_unique()),
        "classes_unused": sorted(set(cname) - set(attrs["facade_class"].unique().to_list())),
        "class_distribution": [{"facade_class": int(r[0]), "id": cname.get(int(r[0]), "?"), "count": int(r[1]),
                                "share": round(100.0 * int(r[1]) / total, 4)} for r in dist.iter_rows()],
        "class_distribution_by_borough": [{"borough": int(r[0]), "facade_class": int(r[1]),
                                           "id": cname.get(int(r[1]), "?"), "count": int(r[2])}
                                          for r in per_boro.iter_rows()],
        "material_distribution": [{"material": int(r[0]), "name": E.MATERIALS[int(r[0])], "count": int(r[1]),
                                   "share": round(100.0 * int(r[1]) / total, 4)} for r in mat.iter_rows()],
        "material_source_counts": {str(k): int(v) for k, v in
                                   attrs.group_by("material_source").len().sort("material_source").iter_rows()},
        "material_real": int(mreal.sum()),
        "material_real_share": round(100.0 * float(mreal.sum()) / total, 4),
        "facade_inferred": int(total - mreal.sum()),
        "osm_matched": int((attrs["osm_id"] != 0).sum()),
        "water_towers": int(attrs["has_water_tower"].sum()),
        "water_tower_kinds": {str(k): int(v) for k, v in
                              attrs.group_by("water_tower_kind").len().sort("water_tower_kind").iter_rows()},
        "fire_escapes": int(attrs["has_fire_escape"].sum()),
        "stoops": int(attrs["has_stoop"].sum()),
        "cornices": int(attrs["has_cornice"].sum()),
        "storefronts": int(df["has_storefront"].sum()),
        "awning_real": int(attrs["awning_real"].sum()),
        "rooftop_units_total": int(attrs["rooftop_units"].cast(pl.Int32).sum()),
        "window_cols_median": float(attrs["window_cols"].median()),
        "window_rows_median": float(attrs["window_rows"].median()),
        "frontage_source_counts": {str(k): int(v) for k, v in
                                   attrs.group_by("frontage_source").len().sort("frontage_source").iter_rows()},
        "corner_buildings": int(attrs["is_corner"].sum()),
        "attached_buildings": int((attrs["attached"] > 0).sum()),
        "roof_attrs": roof_state,
        "roof_real": int((attrs["fidelity"].cast(pl.UInt32) & FIDELITY_ROOF_REAL != 0).sum()),
        "roof_inferred": int((attrs["fidelity"].cast(pl.UInt32) & RF.FIDELITY_ROOF_INFERRED != 0).sum()),
        "roof_type_distribution": {str(k): int(v) for k, v in
                                   attrs.group_by("roof_type").len().sort("roof_type").iter_rows()},
        "roof_source_counts": {str(k): int(v) for k, v in
                               attrs.group_by("roof_source").len().sort("roof_source").iter_rows()},
    }


# ----------------------------------------------------------------------------------------------------------------------
#: A building with at least one free facade run must produce placements. Below this many records per building the
#: emit pass has silently produced nothing useful and must fail rather than write empty files.
MIN_PLACEMENTS_PER_BUILDING = 4.0


def pass_emit(only_tiles: set[str] | None, limit_groups: int | None, out_dir: Path, tiles_root: Path,
              validate_every: int = 25) -> dict:
    """Extend the per-tile buildings files and write the kit placements."""
    t = Timer()
    attrs_path = out_dir / "facade_attrs.parquet"
    if not attrs_path.exists():
        raise FileNotFoundError(f"{attrs_path} missing: run the `rules` pass first")
    attrs = pl.read_parquet(attrs_path)
    edges_dir = out_dir / "edges"
    if not edges_dir.exists() or not any(edges_dir.glob("*.parquet")):
        # the edge cache is a derived intermediate the emit pass deletes when it finishes a full run; rebuild it
        # rather than writing empty placement files
        log.warning("%s holds no edge runs; rebuilding it with the geom pass", edges_dir)
        pass_geom(only_tiles, limit_groups, out_dir)
    groups = tile_groups(attrs["tile"].unique().to_list() if only_tiles is None
                         else [t2 for t2 in attrs["tile"].unique().to_list() if t2 in only_tiles])
    if limit_groups:
        groups = dict(list(groups.items())[:limit_groups])
    attrs_by_tile = attrs.partition_by("tile", as_dict=True)
    attrs_by_tile = {k[0] if isinstance(k, tuple) else k: v for k, v in attrs_by_tile.items()}
    t.lap(f"load facade_attrs ({attrs.height:,} rows, {len(groups)} groups)")

    tot: dict = {"tiles": 0, "buildings": 0, "placements": 0, "bytes": 0, "validated": 0, "problems": [],
                 "_empty_tiles": []}
    kit_counts: dict[int, int] = {}
    n_place_by_key: dict[tuple[str, int], int] = {}
    ti = 0
    for gi, (gname, gtiles) in enumerate(groups.items()):
        epath = edges_dir / f"{gname}.parquet"
        edges = pl.read_parquet(epath) if epath.exists() else None
        if edges is None:
            raise FileNotFoundError(f"{epath} missing: the edge cache is incomplete, re-run the `geom` pass")
        edges_by_tile = {}
        if edges is not None and edges.height:
            parts = edges.partition_by("tile", as_dict=True)
            edges_by_tile = {k[0] if isinstance(k, tuple) else k: v for k, v in parts.items()}
        for tile in gtiles:
            a = attrs_by_tile.get(tile)
            if a is None:
                continue
            tdir = tiles_root / tile
            bpath = tdir / "buildings.parquet"
            if not bpath.exists():
                log.warning("%s missing: skipped", bpath)
                continue
            base_tbl = pq.read_table(bpath)
            a = a.sort("row")
            base_cols = [n for n in base_tbl.schema.names if n not in set(FS.ADDED_NAMES)]
            if base_tbl.num_rows != a.height:
                raise RuntimeError(f"{tile}: tile has {base_tbl.num_rows} rows, facade_attrs has {a.height}")
            if not np.array_equal(base_tbl["bin"].to_numpy(), a["bin"].to_numpy()):
                raise RuntimeError(f"{tile}: bin order differs between the tile file and facade_attrs")

            rec = np.empty(0, dtype=P.PLACEMENT_DTYPE)
            e = edges_by_tile.get(tile)
            if e is not None and e.height:
                rec = _placements_for_tile(base_tbl, a, e)
            n_by_bin = _count_by_row(rec, base_tbl["bin"].to_numpy())
            a = a.with_columns(pl.Series("n_placements", n_by_bin, dtype=pl.Int32))
            hdr = P.write_tile(rec, tile, tdir, extra={"rules_version": R.RULES_VERSION})
            for k in hdr["kit_id_counts"]:
                kit_counts[int(k["kit_id"])] = kit_counts.get(int(k["kit_id"]), 0) + int(k["count"])

            out_tbl = _extend_table(base_tbl, a)
            tmp = bpath.with_suffix(".tmp")
            pq.write_table(out_tbl, tmp, compression="snappy")
            tmp.replace(bpath)

            tot["tiles"] += 1
            tot["buildings"] += out_tbl.num_rows
            if out_tbl.num_rows and len(rec) == 0:
                tot["_empty_tiles"].append(tile)
            tot["placements"] += int(len(rec))
            tot["bytes"] += hdr["bytes"]
            ti += 1
            # schema conformance on every tile; the (much slower) null check on a sample
            probs = validate_parquet("buildings", bpath, check_nulls=(ti % validate_every == 1))
            tot["validated"] += 1
            if probs:
                tot["problems"].append({"tile": tile, "problems": probs})
        if (gi + 1) % 10 == 0 or gi + 1 == len(groups):
            log.info("emit %d/%d groups, %d tiles, %s placements, %.1f MB, rss %.0f MB",
                     gi + 1, len(groups), tot["tiles"], f"{tot['placements']:,}", tot["bytes"] / 1e6, _rss_mb())
    t.lap("emit tiles")
    from .kit_ids import piece_info
    tot["kit_id_counts"] = [{**piece_info(int(k)), "count": int(v)}
                            for k, v in sorted(kit_counts.items(), key=lambda kv: -kv[1])]
    tot["placements_per_building"] = round(tot["placements"] / max(tot["buildings"], 1), 2)
    # a tile that holds buildings but no placements is a failure, not a silent success
    empty = [e for e in tot.pop("_empty_tiles", []) ]
    if empty:
        tot["problems"].append({"empty_tiles": empty[:50], "n_empty_tiles": len(empty),
                                "problems": ["tile holds buildings but kit_placements.bin is empty"]})
    if tot["buildings"] and tot["placements_per_building"] < MIN_PLACEMENTS_PER_BUILDING:
        tot["problems"].append({"problems": [
            f"placements per building {tot['placements_per_building']} is below the {MIN_PLACEMENTS_PER_BUILDING} "
            f"floor: the placement generator produced nothing usable"]})
    tot["elapsed_s"] = t.total
    tot["max_rss_mb"] = round(_rss_mb(), 1)
    with open(out_dir / "emit_summary.json", "w") as f:
        json.dump(tot, f, indent=1)
    log.info("emit pass: %d tiles, %s placements, %.2f GB", tot["tiles"], f"{tot['placements']:,}", tot["bytes"] / 1e9)
    return tot


def _count_by_row(rec: np.ndarray, bins: np.ndarray) -> np.ndarray:
    out = np.zeros(len(bins), dtype=np.int32)
    if len(rec) == 0:
        return out
    order = np.argsort(bins, kind="stable")
    sb = bins[order]
    ub, cnt = np.unique(rec["bin"], return_counts=True)
    pos = np.searchsorted(sb, ub)
    ok = (pos < len(sb)) & (sb[np.minimum(pos, len(sb) - 1)] == ub)
    # a bin can appear on several rows (multi-part footprints): attribute the count to the first row
    out[order[pos[ok]]] = cnt[ok]
    return out


def _placements_for_tile(base_tbl: pa.Table, a: pl.DataFrame, e: pl.DataFrame) -> np.ndarray:
    """Assemble the per-building arrays and the run arrays, then generate the placements."""
    n = base_tbl.num_rows
    geoms = shapely.from_wkb(np.asarray(base_tbl["footprint"].to_pylist(), dtype=object))
    valid = shapely.is_valid(geoms)
    if not valid.all():
        geoms = np.where(valid, geoms, shapely.make_valid(geoms))
    cls = base_tbl["bldg_class"].to_pylist()
    b = {
        "bin": base_tbl["bin"].to_numpy(),
        "ground_z": base_tbl["ground_z"].to_numpy(zero_copy_only=False).astype(np.float64),
        "roof_z": base_tbl["roof_z"].to_numpy(zero_copy_only=False).astype(np.float64),
        "floors": base_tbl["floors"].to_numpy(zero_copy_only=False).astype(np.int32),
        "floor_height": base_tbl["floor_height"].to_numpy(zero_copy_only=False).astype(np.float64),
        "ground_floor_height": base_tbl["ground_floor_height"].to_numpy(zero_copy_only=False).astype(np.float64),
        "footprint_area": base_tbl["footprint_area"].to_numpy(zero_copy_only=False).astype(np.float64),
        "feature_code": base_tbl["feature_code"].to_numpy(zero_copy_only=False).astype(np.int32),
        "first_floor_offset": base_tbl["first_floor_offset"].to_numpy(zero_copy_only=False).astype(np.float64),
        "lit_seed": base_tbl["lit_seed"].to_numpy(zero_copy_only=False).astype(np.uint32),
        "has_storefront": base_tbl["has_storefront"].to_numpy(zero_copy_only=False).astype(bool),
        "has_scaffold": base_tbl["has_scaffold"].to_numpy(zero_copy_only=False).astype(bool),
        "bldg_class1": np.asarray([c[:1].encode() if c else b"" for c in cls], dtype="S1"),
        "facade_class": a["facade_class"].to_numpy().astype(np.int64),
        "window_type": a["window_type"].to_numpy().astype(np.int64),
        "window_rows": a["window_rows"].to_numpy().astype(np.int32),
        "bay_width_m": a["bay_width_m"].to_numpy().astype(np.float64),
        "material_primary": a["material_primary"].to_numpy().astype(np.int64),
        "has_fire_escape": a["has_fire_escape"].to_numpy().astype(bool),
        "has_stoop": a["has_stoop"].to_numpy().astype(bool),
        "has_cornice": a["has_cornice"].to_numpy().astype(bool),
        "has_water_tower": a["has_water_tower"].to_numpy().astype(bool),
        "water_tower_kind": a["water_tower_kind"].to_numpy().astype(np.int64),
        "rooftop_units": a["rooftop_units"].to_numpy().astype(np.int32),
        "storefront_kind_primary": a["storefront_kind_primary"].to_numpy().astype(np.int64),
    }
    runs = {
        "bidx": e["row"].to_numpy().astype(np.int64),
        "x0": e["x0"].to_numpy(), "y0": e["y0"].to_numpy(), "x1": e["x1"].to_numpy(), "y1": e["y1"].to_numpy(),
        "length": e["length"].to_numpy(), "nx": e["nx"].to_numpy(), "ny": e["ny"].to_numpy(),
        "is_party": e["is_party"].to_numpy(), "is_street": e["is_street"].to_numpy(),
    }
    if runs["bidx"].size and (runs["bidx"].max() >= n or runs["bidx"].min() < 0):
        raise RuntimeError("edge run row index outside the tile")
    return P.build_placements(b, runs, geoms)


def _extend_table(base_tbl: pa.Table, a: pl.DataFrame) -> pa.Table:
    """Append the facade columns to the buildings table, overwriting ``osm_id`` and ``fidelity`` in place.

    Idempotent: a tile already carrying facade columns from an earlier run keeps only its buildings-stage columns,
    which are then re-extended, so re-running the pass never duplicates a column.
    """
    added = set(FS.ADDED_NAMES)
    keep = [i for i, n in enumerate(base_tbl.schema.names) if n not in added]
    arrays = [base_tbl.column(i) for i in keep]
    fields = [base_tbl.schema.field(i) for i in keep]
    names = [f.name for f in fields]
    for col in FS.OVERWRITTEN:
        i = names.index(col)
        arrays[i] = a[col].to_arrow().cast(fields[i].type)
    for name, typ in FS.ADDED_COLUMNS:
        arrays.append(a[name].to_arrow().cast(typ))
        fields.append(pa.field(name, typ, nullable=False))
    meta = dict(base_tbl.schema.metadata or {})
    meta[b"nycsim.facade.schema"] = FS.FACADE_SCHEMA_ID.encode()
    meta[b"nycsim.facade.rules_version"] = R.RULES_VERSION.encode()
    meta[b"nycsim.facade.stage"] = b"facade"
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields, metadata=meta))


# ----------------------------------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nycsim_pipeline facade",
                                 description="Facade classification and kit placement (ADR-004)")
    ap.add_argument("stage", choices=["geom", "rules", "emit", "all"])
    ap.add_argument("--tiles", nargs="*", default=None, help="restrict to these tiles (development runs)")
    ap.add_argument("--limit-groups", type=int, default=None, help="process only the first N 4 km blocks")
    ap.add_argument("--out-dir", default=str(FACADE_DIR))
    ap.add_argument("--tiles-root", default=str(TILES_ROOT))
    ap.add_argument("--keep-edges", action="store_true", help="keep facade/edges/*.parquet after the emit pass")
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        os.nice(10)
    except OSError:
        pass
    out_dir = Path(a.out_dir)
    tiles_root = Path(a.tiles_root)
    only = set(a.tiles) if a.tiles else None
    subset = bool(only or a.limit_groups)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_registry(out_dir / "kit_ids.json")

    result: dict = {"stage": a.stage, "subset": subset}
    if a.stage in ("geom", "all"):
        result["geom"] = pass_geom(only, a.limit_groups, out_dir)
    if a.stage in ("rules", "all"):
        result["rules"] = pass_rules(out_dir, a.limit_groups if subset else None)
    if a.stage in ("emit", "all"):
        result["emit"] = pass_emit(only, a.limit_groups, out_dir, tiles_root)
        if not a.keep_edges and not subset and not result["emit"].get("problems"):
            shutil.rmtree(out_dir / "edges", ignore_errors=True)
            log.info("removed the edge cache (%s); the emit pass rebuilds it when it is needed again",
                     out_dir / "edges")
        if result["emit"].get("problems"):
            log.error("emit finished with %d problem groups: %s", len(result["emit"]["problems"]),
                      json.dumps(result["emit"]["problems"])[:2000])
            return 1

    if not subset and not a.no_manifest:
        for aid, p, schema in (("facade_geom_attrs", out_dir / "geom_attrs.parquet", "facade_geom/1"),
                               ("facade_attrs", out_dir / "facade_attrs.parquet", "facade_attrs/1"),
                               ("facade_kit_ids", out_dir / "kit_ids.json", "kit_ids/1")):
            if p.exists():
                rows = pq.ParquetFile(p).metadata.num_rows if p.suffix == ".parquet" else None
                manifest.record_processed(aid, p, stage="facade", rows=rows, schema=schema,
                                          sources=["building_footprints", "pluto", "lpc_building_db", "osm_newyork_pbf",
                                                   "building_elevation_subgrade"])
    with open(out_dir / "run_summary.json", "w") as f:
        json.dump(result, f, indent=1, default=str)
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items()
                                                            if kk not in ("rule_hits", "class_distribution",
                                                                          "class_distribution_by_borough",
                                                                          "material_distribution", "kit_id_counts",
                                                                          "rules_with_no_hits", "steps_s")})
                      for k, v in result.items()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
