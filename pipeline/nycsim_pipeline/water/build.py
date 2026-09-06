"""Water stage: ``water/hydrography.parquet``, ``water/shoreline.parquet``, ``water/structures.parquet``,
``water/water_tiles.parquet`` (DATA_CONTRACTS §4).

Two phases:

1. ``build_geometry()`` — planimetric hydrography/structures/shoreline (NYC OTI, 2022) + OSM water outside the
   NYC boundary; ``kind`` classification; a *provisional* ``tidal`` flag from connectivity to the ocean.
2. ``finalize_levels(stack)`` — run by the terrain stage once the DEM intermediates exist: per-body DEM
   statistics, surveyed water-elevation points (planimetric 3010), final ``tidal``/``water_z_m``/``level_mode``,
   and the DEM-slope shoreline classification (bulkhead vs natural).

Schema extensions beyond §4 (all documented in docs/verification/terrain/REPORT.md):
hydrography: ``source`` (nyc_planimetric|osm), ``feat_code``, ``osm_id``, ``level_mode`` (tidal|constant|dem),
``water_z_m`` (NaN when level_mode == dem), ``level_source``, ``z_dem_median/p10/p90``, ``n_dem_samples``,
``is_open_water``; kind ``marsh`` added. structures: ``deck_z_m``, ``elevation_ft``, ``sub_code``, ``struct_id``.
shoreline: ``shore_id``, ``kind_source``.

    python -m nycsim_pipeline water [--no-osm] [--skip-finalize]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely
from shapely.geometry import box
from shapely.ops import unary_union

from .. import manifest
from ..crs import NYC_TM, SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN, US_SURVEY_FOOT_M
from ..paths import PROCESSED, RAW, REPO_ROOT
from ..tiling import scope_tiles
from .classify import FEAT_CODE_KIND, STRUCT_CODE_KIND, clean_name, is_open_water, kind_from_planimetric
from .names import assign_names

log = logging.getLogger("nycsim.water")

OUT = PROCESSED / "water"
HYDRO_PATH = OUT / "hydrography.parquet"
SHORE_PATH = OUT / "shoreline.parquet"
STRUCT_PATH = OUT / "structures.parquet"
WTILES_PATH = OUT / "water_tiles.parquet"
SUMMARY_PATH = OUT / "water_summary.json"
SCHEMAS = {"hydrography": "water.hydrography/1", "shoreline": "water.shoreline/1", "structures": "water.structures/1", "water_tiles": "water.water_tiles/1"}

RAW_HYDRO = RAW / "nyc_opendata" / "plan_hydrography.geojson"
RAW_STRUCT = RAW / "nyc_opendata" / "plan_hydro_structures.geojson"
RAW_SHORE = RAW / "nyc_opendata" / "plan_shoreline.geojson"
RAW_BORO_WATER = RAW / "nyc_opendata" / "borough_boundaries_water.geojson"
RAW_ELEV = RAW / "nyc_opendata" / "plan_elevation_points.geojson"
RAW_OSM = RAW / "osm" / "NewYork.osm.pbf"

CONNECT_DIST_M = 25.0      # polygons closer than this are one hydraulic system (bridges split them)
TIDAL_MAX_ABS_Z = 1.0      # a connected body whose DEM surface sits within +-1 m of NAVD88 zero is tidal
FLAT_RANGE_M = 0.75        # p90-p10 of the DEM inside a body below this -> one constant level
OSM_INSET_M = 10.0         # OSM water is cut this far inside the NYC boundary so the two sources overlap
MIN_OSM_AREA_M2 = 100.0
OSM_ID_BASE = 10_000_000
SCOPE_BOX = box(SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX)


class WaterError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- io helpers
def write_geoparquet(gdf: gpd.GeoDataFrame, path: Path, schema: str, artifact_id: str, sources: list[str], extra: dict | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.parquet")
    gdf.to_parquet(tmp, index=False, compression="snappy")
    t = pq.read_table(tmp)
    # pandas hands pyarrow large_string; DATA_CONTRACTS expects plain string columns
    fields = [f.with_type(pa.string()) if pa.types.is_large_string(f.type) else f for f in t.schema]
    t = t.cast(pa.schema(fields, metadata=t.schema.metadata))
    meta = dict(t.schema.metadata or {})
    meta[b"nycsim.schema"] = schema.encode()
    pq.write_table(t.replace_schema_metadata(meta), tmp, compression="snappy")
    os.replace(tmp, path)
    manifest.record_processed(artifact_id, path, stage="water", sources=sources, rows=len(gdf), schema=schema, extra=extra)


def read_geoparquet(path: Path, expect_schema: str) -> gpd.GeoDataFrame:
    meta = pq.read_schema(path).metadata or {}
    got = meta.get(b"nycsim.schema", b"").decode()
    if got != expect_schema:
        raise WaterError(f"{path}: schema {got!r} != {expect_schema!r}")
    return gpd.read_parquet(path)


def _read_plan(path: Path) -> gpd.GeoDataFrame:
    if not path.exists():
        raise WaterError(f"missing input {path} (run the downloader)")
    g = pyogrio.read_dataframe(path)
    if g.crs is None:
        raise WaterError(f"{path}: no CRS")
    return g.to_crs(NYC_TM)


def nyc_boundary_water():
    """(GeoDataFrame boroughs-with-water in NYC_TM, union polygon)."""
    b = _read_plan(RAW_BORO_WATER)
    code_col = next((c for c in b.columns if c.lower() in ("boro_code", "borocode")), None)
    if code_col is None:
        raise WaterError(f"{RAW_BORO_WATER}: no borough code column in {list(b.columns)}")
    b["boro_code"] = pd.to_numeric(b[code_col], errors="coerce").astype("int8")
    b["geometry"] = shapely.make_valid(b.geometry.values)
    return b, unary_union(b.geometry.values)


# ----------------------------------------------------------------------------- connectivity
def _components(geoms: np.ndarray, dist: float) -> np.ndarray:
    """Union-find components over polygons within ``dist`` of each other."""
    n = len(geoms)
    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    tree = shapely.STRtree(geoms)
    a, b = tree.query(geoms, predicate="dwithin", distance=dist)
    for i, j in zip(a.tolist(), b.tolist()):
        if i < j:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj
    return np.array([find(i) for i in range(n)])


def provisional_tidal(h: gpd.GeoDataFrame) -> np.ndarray:
    """Connected (within 25 m) to the component holding the ocean / largest bay polygons."""
    comp = _components(h.geometry.values, CONNECT_DIST_M)
    seeds = h.index[(h["kind"] == "ocean") | ((h["kind"] == "bay") & (h.geometry.area > 5e6))]
    if len(seeds) == 0:
        raise WaterError("no ocean/bay seed polygon found for tidal connectivity")
    seed_comps = set(comp[h.index.get_indexer(seeds)].tolist())
    return np.isin(comp, list(seed_comps))


# ----------------------------------------------------------------------------- phase 1
def build_hydrography(use_osm: bool = True) -> tuple[gpd.GeoDataFrame, dict]:
    stats: dict = {}
    osm_areas: gpd.GeoDataFrame | None = None
    h = _read_plan(RAW_HYDRO)
    h["feat_code"] = pd.to_numeric(h["feat_code"], errors="coerce").astype("Int64")
    if h["feat_code"].isna().any():
        raise WaterError("hydrography rows without feat_code")
    h["feat_code"] = h["feat_code"].astype("int32")
    unknown = set(h["feat_code"].unique()) - set(FEAT_CODE_KIND)
    if unknown:
        raise WaterError(f"unknown hydrography feature codes {sorted(unknown)}")
    h["name"] = h["name"].map(clean_name)
    h["kind"] = [kind_from_planimetric(fc, nm) for fc, nm in zip(h["feat_code"], h["name"])]
    n_beach = int((h["kind"] == "beach").sum())
    h = h[h["kind"] != "beach"].copy()  # beaches are land: the DEM carries them
    h["geometry"] = shapely.make_valid(h.geometry.values)
    h = h[~h.geometry.is_empty & h.geometry.intersects(SCOPE_BOX)].copy()
    h["source"] = "nyc_planimetric"
    h["osm_id"] = np.int64(0)
    h["plan_source_id"] = h["source_id"].astype(str)
    h = h.sort_values(["feat_code", "name", "plan_source_id"], kind="stable").reset_index(drop=True)
    h["water_id"] = np.arange(1, len(h) + 1, dtype=np.int64)
    stats.update({"planimetric_polygons": len(h), "beach_polygons_dropped": n_beach,
                  "planimetric_area_km2": float(h.geometry.area.sum() / 1e6)})
    frames = [h[["water_id", "kind", "name", "source", "feat_code", "osm_id", "plan_source_id", "geometry"]]]
    if use_osm:
        from .osm_water import extract
        boro, nyc_union = nyc_boundary_water()
        inside = nyc_union.buffer(-OSM_INSET_M)
        osm = extract(RAW_OSM, (SCOPE_XMIN, SCOPE_YMIN, SCOPE_XMAX, SCOPE_YMAX))
        osm_areas = osm.areas
        stats["osm"] = osm.stats
        rows = []
        sea_out = osm.sea.intersection(SCOPE_BOX).difference(inside)
        # name the sea by the labelled OSM bay/strait/river polygons it falls in; the rest stays an unnamed bay
        labels = osm.areas[(osm.areas["name"] != "") & osm.areas["tags"].str.contains("natural=bay|natural=strait|water=river", regex=True)]
        remainder = sea_out
        for _, r in labels.sort_values("name").iterrows():
            piece = sea_out.intersection(r.geometry)
            if piece.is_empty or piece.area < MIN_OSM_AREA_M2:
                continue
            rows.append({"kind": r["kind"] if r["kind"] in ("bay", "river", "canal") else "bay", "name": r["name"], "osm_id": int(r["osm_id"]), "geometry": piece})
            remainder = remainder.difference(r.geometry)
        for part in getattr(remainder, "geoms", [remainder]):
            if not part.is_empty and part.area >= MIN_OSM_AREA_M2:
                rows.append({"kind": "bay", "name": "", "osm_id": 0, "geometry": part})
        # inland OSM water outside the city (NJ, Nassau, Westchester): lakes, reservoirs, rivers
        a_out = osm.areas.copy()
        a_out["geometry"] = [g.intersection(SCOPE_BOX).difference(inside) for g in a_out.geometry.values]
        a_out = a_out[~a_out.geometry.is_empty]
        a_out = a_out[a_out.geometry.area >= MIN_OSM_AREA_M2]
        a_out = a_out[~a_out["tags"].str.contains("natural=bay|natural=strait", regex=True)]  # label polygons: already used
        for _, r in a_out.iterrows():
            g = r.geometry.difference(sea_out) if r.geometry.intersects(sea_out) else r.geometry
            if g.is_empty or g.area < MIN_OSM_AREA_M2:
                continue
            rows.append({"kind": r["kind"], "name": r["name"], "osm_id": int(r["osm_id"]), "geometry": g})
        o = gpd.GeoDataFrame(rows, geometry="geometry", crs=NYC_TM)
        o["geometry"] = shapely.make_valid(o.geometry.values)
        o = o[~o.geometry.is_empty].reset_index(drop=True)
        o["source"] = "osm"
        o["feat_code"] = np.int32(0)
        o["plan_source_id"] = ""
        o["water_id"] = OSM_ID_BASE + np.arange(1, len(o) + 1, dtype=np.int64)
        stats.update({"osm_polygons": len(o), "osm_area_km2": float(o.geometry.area.sum() / 1e6)})
        frames.append(o[["water_id", "kind", "name", "source", "feat_code", "osm_id", "plan_source_id", "geometry"]])
    hydro = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=NYC_TM)
    # polygons only (make_valid can emit GeometryCollections with line slivers)
    hydro["geometry"] = [shapely.union_all([p for p in getattr(g, "geoms", [g]) if p.geom_type in ("Polygon", "MultiPolygon")]) if g.geom_type == "GeometryCollection" else g for g in hydro.geometry.values]
    hydro = hydro[~hydro.geometry.is_empty].reset_index(drop=True)
    hydro["is_open_water"] = hydro["kind"].map(is_open_water)
    hydro, name_stats = assign_names(hydro, osm_areas, OSM_ID_BASE)
    hydro["is_open_water"] = hydro["kind"].map(is_open_water)  # _split_sea may retype a piece from its neighbour
    stats["names"] = name_stats
    hydro["tidal"] = provisional_tidal(hydro)
    hydro["level_mode"] = np.where(hydro["tidal"] & hydro["is_open_water"], "tidal", np.where(hydro["kind"] == "marsh", "dem", "constant"))
    hydro["water_z_m"] = np.where(hydro["level_mode"] == "tidal", 0.0, np.nan).astype("float32")
    hydro["level_source"] = np.where(hydro["level_mode"] == "tidal", "tidal_datum", "pending_dem")
    for c in ("z_dem_median", "z_dem_p10", "z_dem_p90"):
        hydro[c] = np.float32(np.nan)
    hydro["n_dem_samples"] = np.int32(0)
    hydro["area_m2"] = hydro.geometry.area.astype("float64")
    stats.update({"polygons": len(hydro), "area_km2": float(hydro["area_m2"].sum() / 1e6),
                  "kinds": hydro["kind"].value_counts().to_dict(), "tidal_provisional": int(hydro["tidal"].sum())})
    return hydro, stats


def build_structures() -> gpd.GeoDataFrame:
    s = _read_plan(RAW_STRUCT)
    s["feat_code"] = pd.to_numeric(s["feat_code"], errors="coerce").astype("int32")
    unknown = set(s["feat_code"].unique()) - set(STRUCT_CODE_KIND)
    if unknown:
        raise WaterError(f"unknown hydro-structure feature codes {sorted(unknown)}")
    s["kind"] = s["feat_code"].map(STRUCT_CODE_KIND)
    s["sub_code"] = pd.to_numeric(s["sub_code"], errors="coerce").fillna(0).astype("int32")
    s["elevation_ft"] = pd.to_numeric(s["elevation"], errors="coerce").astype("float32")
    s["deck_z_m"] = (s["elevation_ft"] * US_SURVEY_FOOT_M).astype("float32")
    s["geometry"] = shapely.make_valid(s.geometry.values)
    s = s[~s.geometry.is_empty & s.geometry.intersects(SCOPE_BOX)].copy()
    s["plan_source_id"] = s["source_id"].astype(str)
    s = s.sort_values(["feat_code", "plan_source_id"], kind="stable").reset_index(drop=True)
    s["struct_id"] = np.arange(1, len(s) + 1, dtype=np.int64)
    s["source"] = "nyc_planimetric"
    s["area_m2"] = s.geometry.area.astype("float64")
    return gpd.GeoDataFrame(s[["struct_id", "kind", "feat_code", "sub_code", "elevation_ft", "deck_z_m", "source", "plan_source_id", "area_m2", "geometry"]], geometry="geometry", crs=NYC_TM)


def build_shoreline(structures: gpd.GeoDataFrame, hydro: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Planimetric shoreline lines, exploded to simple parts, with a first (structure/marsh based) kind."""
    sl = _read_plan(RAW_SHORE).explode(index_parts=False).reset_index(drop=True)
    sl = sl[sl.geometry.geom_type == "LineString"].copy()
    sl = sl[sl.geometry.intersects(SCOPE_BOX)].reset_index(drop=True)
    sl["shore_id"] = np.arange(1, len(sl) + 1, dtype=np.int64)
    kinds = np.array(["natural"] * len(sl), dtype=object)
    src = np.array(["default"] * len(sl), dtype=object)
    # structures decide first: a shoreline running along a pier is 'pier', along a seawall 'bulkhead'
    for skind, out in (("seawall", "bulkhead"), ("pier", "pier"), ("jetty", "pier")):
        geoms = structures.loc[structures["kind"] == skind, "geometry"].values
        if len(geoms) == 0:
            continue
        tree = shapely.STRtree(geoms)
        li, si = tree.query(sl.geometry.values, predicate="dwithin", distance=3.0)
        if li.size == 0:
            continue
        # fraction of each line within 3 m of the structure(s)
        for i in np.unique(li):
            line = sl.geometry.values[i]
            near = unary_union(geoms[si[li == i]]).buffer(3.0)
            frac = line.intersection(near).length / max(line.length, 1e-9)
            if frac >= 0.5 and (kinds[i] == "natural"):
                kinds[i], src[i] = out, "structure"
    marsh = hydro.loc[hydro["kind"] == "marsh", "geometry"].values
    if len(marsh):
        tree = shapely.STRtree(marsh)
        li, _ = tree.query(sl.geometry.values, predicate="dwithin", distance=3.0)
        for i in np.unique(li):
            if src[i] == "default":
                kinds[i], src[i] = "natural", "marsh"
    sl["kind"] = kinds
    sl["kind_source"] = src
    sl["length_m"] = sl.geometry.length.astype("float64")
    sl["source"] = "nyc_planimetric"
    return gpd.GeoDataFrame(sl[["shore_id", "kind", "kind_source", "length_m", "source", "geometry"]], geometry="geometry", crs=NYC_TM)


def build_water_tiles(hydro: gpd.GeoDataFrame) -> pd.DataFrame:
    """Per scope tile: open-water area and flag (marsh excluded from both)."""
    open_w = hydro[hydro["is_open_water"]]
    tree = shapely.STRtree(open_w.geometry.values)
    rows = []
    for t in scope_tiles():
        b = box(*t.bounds)
        idx = tree.query(b, predicate="intersects")
        area = 0.0
        if idx.size:
            area = float(sum(g.intersection(b).area for g in open_w.geometry.values[idx]))
        rows.append({"tile": t.name, "tx": np.int32(t.tx), "ty": np.int32(t.ty), "water_area_m2": area, "has_open_water": area > 0.0})
    return pd.DataFrame(rows)


def build_geometry(use_osm: bool = True) -> dict:
    t0 = time.time()
    hydro, stats = build_hydrography(use_osm)
    structures = build_structures()
    shoreline = build_shoreline(structures, hydro)
    wt = build_water_tiles(hydro)
    src_ids = ["plan_hydrography", "plan_hydro_structures", "plan_shoreline", "borough_boundaries_water"] + (["osm_newyork_pbf"] if use_osm else [])
    write_geoparquet(hydro, HYDRO_PATH, SCHEMAS["hydrography"], "water_hydrography", src_ids, extra={"kinds": stats["kinds"]})
    write_geoparquet(structures, STRUCT_PATH, SCHEMAS["structures"], "water_structures", ["plan_hydro_structures"])
    write_geoparquet(shoreline, SHORE_PATH, SCHEMAS["shoreline"], "water_shoreline", ["plan_shoreline", "plan_hydro_structures"])
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = WTILES_PATH.with_suffix(".tmp.parquet")
    tbl = pa.Table.from_pandas(wt, preserve_index=False)
    pq.write_table(tbl.replace_schema_metadata({**(tbl.schema.metadata or {}), b"nycsim.schema": SCHEMAS["water_tiles"].encode()}), tmp, compression="snappy")
    os.replace(tmp, WTILES_PATH)
    manifest.record_processed("water_tiles", WTILES_PATH, stage="water", sources=["plan_hydrography"], rows=len(wt), schema=SCHEMAS["water_tiles"])
    stats.update({"structures": len(structures), "structure_kinds": structures["kind"].value_counts().to_dict(),
                  "shoreline_parts": len(shoreline), "shoreline_km": float(shoreline["length_m"].sum() / 1e3),
                  "shoreline_kinds": shoreline["kind"].value_counts().to_dict(),
                  "tiles_with_open_water": int(wt["has_open_water"].sum()), "geometry_seconds": round(time.time() - t0, 1)})
    _save_summary({"geometry": stats})
    log.info("water geometry: %d polygons (%.1f km2), %d structures, %d shoreline parts, %d tiles with open water, %.1fs",
             len(hydro), stats["area_km2"], len(structures), len(shoreline), stats["tiles_with_open_water"], stats["geometry_seconds"])
    return stats


def _save_summary(update: dict) -> None:
    doc = {}
    if SUMMARY_PATH.exists():
        with open(SUMMARY_PATH) as f:
            doc = json.load(f)
    doc.update(update)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w") as f:
        json.dump(doc, f, indent=1, default=str)


# ----------------------------------------------------------------------------- phase 2 (needs DEM)
def load_water_elevation_points() -> gpd.GeoDataFrame:
    """Planimetric 3010 'Water Elevation' points (surveyed standing-water levels, ft) in NYC_TM."""
    g = pyogrio.read_dataframe(RAW_ELEV, where="feat_code = '3010'", columns=["elevation", "feat_code", "sub_code"])
    g = g.to_crs(NYC_TM)
    g["z_m"] = (pd.to_numeric(g["elevation"], errors="coerce") * US_SURVEY_FOOT_M).astype("float32")
    return g[np.isfinite(g["z_m"])].reset_index(drop=True)


STAT_BLOCK_M = 2000.0        # DEM statistics are gathered in 2 km lattice blocks (1001 x 1001 samples, 4 MB)
STAT_MAX_BLOCKS = 24         # ... and from at most this many blocks, spread evenly over a large body
STAT_MAX_SAMPLES = 400_000   # ... keeping at most this many samples in total


def _blocks_over(geom, block_m: float, max_blocks: int) -> list[tuple[float, float, float, float]]:
    """Deterministic, evenly spread list of lattice-aligned block bboxes covering ``geom``."""
    minx, miny, maxx, maxy = geom.bounds
    cx0, cx1 = int(np.floor(minx / block_m)), int(np.floor((maxx - 1e-6) / block_m))
    cy0, cy1 = int(np.floor(miny / block_m)), int(np.floor((maxy - 1e-6) / block_m))
    cells = [(cx, cy) for cy in range(cy0, cy1 + 1) for cx in range(cx0, cx1 + 1)]
    if len(cells) > max_blocks:
        step = len(cells) / max_blocks
        cells = [cells[int(i * step)] for i in range(max_blocks)]
    return [(cx * block_m, cy * block_m, (cx + 1) * block_m, (cy + 1) * block_m) for cx, cy in cells]


def _dem_stats_for_polygon(stack, geom, max_samples: int = STAT_MAX_SAMPLES) -> tuple[int, float, float, float]:
    """(n, median, p10, p90) of the composed DEM at lattice samples whose centre lies inside ``geom``.

    Sampling is bounded: a body as large as the Atlantic polygon is read in at most ``STAT_MAX_BLOCKS``
    2 km blocks spread evenly over its bounding box, never as one scope-sized array.
    """
    from rasterio.features import rasterize

    from ..terrain.grid import NODATA, SPACING_M, lattice_grid
    parts: list[np.ndarray] = []
    kept = 0
    for bx0, by0, bx1, by1 in _blocks_over(geom, STAT_BLOCK_M, STAT_MAX_BLOCKS):
        piece = geom.intersection(box(bx0, by0, bx1, by1))
        if piece.is_empty:
            continue
        minx, miny, maxx, maxy = piece.bounds
        tr, w, h = lattice_grid(minx - SPACING_M, miny - SPACING_M, maxx + SPACING_M, maxy + SPACING_M)
        z, _ = stack.read(tr, w, h)
        mask = rasterize([(piece, 1)], out_shape=(h, w), transform=tr, fill=0, dtype="uint8", all_touched=False).astype(bool)
        vals = z[mask & (z != NODATA)]
        if vals.size == 0:
            continue
        if vals.size > max_samples // 4:
            vals = vals[:: int(np.ceil(vals.size / (max_samples // 4)))]
        parts.append(vals)
        kept += vals.size
        if kept >= max_samples:
            break
    if not parts:
        # tiny pond entirely between lattice points: use the nearest samples around the representative point
        p = geom.representative_point()
        tr2, w2, h2 = lattice_grid(p.x - 2 * SPACING_M, p.y - 2 * SPACING_M, p.x + 2 * SPACING_M, p.y + 2 * SPACING_M)
        z2, _ = stack.read(tr2, w2, h2)
        vals = z2[z2 != NODATA]
        if vals.size == 0:
            return 0, float("nan"), float("nan"), float("nan")
        parts = [vals]
    v = np.concatenate(parts)
    return int(v.size), float(np.median(v)), float(np.percentile(v, 10)), float(np.percentile(v, 90))


def finalize_levels(stack) -> dict:
    """Set tidal / water_z_m / level_mode from DEM statistics and surveyed water-elevation points."""
    t0 = time.time()
    hydro = read_geoparquet(HYDRO_PATH, SCHEMAS["hydrography"])
    connected = provisional_tidal(hydro)
    n = len(hydro)
    med = np.full(n, np.nan, dtype=np.float64)
    p10 = np.full(n, np.nan, dtype=np.float64)
    p90 = np.full(n, np.nan, dtype=np.float64)
    cnt = np.zeros(n, dtype=np.int32)
    for i, geom in enumerate(hydro.geometry.values):
        cnt[i], med[i], p10[i], p90[i] = _dem_stats_for_polygon(stack, geom)
    wpts = load_water_elevation_points()
    tree = shapely.STRtree(hydro.geometry.values)
    pi, hi = tree.query(wpts.geometry.values, predicate="within")
    surveyed = pd.Series(wpts["z_m"].values[pi]).groupby(hi).median() if pi.size else pd.Series(dtype=float)
    surveyed_n = pd.Series(np.ones(pi.size)).groupby(hi).size() if pi.size else pd.Series(dtype=int)
    kind = hydro["kind"].values
    open_w = hydro["is_open_water"].values
    tidal = connected & open_w & ((np.abs(med) <= TIDAL_MAX_ABS_Z) | np.isin(kind, ["ocean", "bay"]) | ~np.isfinite(med))
    mode = np.where(tidal, "tidal", "constant").astype(object)
    level = np.where(tidal, 0.0, np.nan)
    src = np.where(tidal, "tidal_datum", "").astype(object)
    for i in range(n):
        if tidal[i]:
            continue
        if kind[i] == "marsh":
            mode[i], src[i] = "dem", "marsh_follows_dem"
            continue
        if i in surveyed.index:
            level[i], mode[i], src[i] = float(surveyed.loc[i]), "constant", "plan_water_elev"
        elif np.isfinite(med[i]) and (p90[i] - p10[i]) <= FLAT_RANGE_M:
            level[i], mode[i], src[i] = med[i], "constant", "dem_median"
        elif np.isfinite(med[i]):
            mode[i], src[i] = "dem", "dem_sloped"
        else:
            mode[i], src[i] = "dem", "dem_no_samples"
    hydro["tidal"] = tidal
    hydro["level_mode"] = mode
    hydro["water_z_m"] = level.astype("float32")
    hydro["level_source"] = src
    hydro["z_dem_median"] = med.astype("float32")
    hydro["z_dem_p10"] = p10.astype("float32")
    hydro["z_dem_p90"] = p90.astype("float32")
    hydro["n_dem_samples"] = cnt
    write_geoparquet(hydro, HYDRO_PATH, SCHEMAS["hydrography"], "water_hydrography",
                     ["plan_hydrography", "plan_hydro_structures", "plan_shoreline", "borough_boundaries_water", "osm_newyork_pbf", "plan_elevation_points", "usgs_3dep"],
                     extra={"levels_finalized": True})
    stats = {"tidal": int(tidal.sum()), "tidal_area_km2": float(hydro.loc[tidal, "area_m2"].sum() / 1e6),
             "level_modes": pd.Series(mode).value_counts().to_dict(), "level_sources": pd.Series(src).value_counts().to_dict(),
             "water_elev_points_used": int(pi.size), "bodies_with_surveyed_level": int(len(surveyed)),
             "tidal_dem_median_m": float(np.nanmedian(med[tidal])) if tidal.any() else float("nan"),
             "seconds": round(time.time() - t0, 1)}
    _save_summary({"levels": stats})
    log.info("water levels: %s", stats)
    return stats


def classify_shoreline_by_dem(stack, rise_m: float = 1.0, reach_m: float = 6.0, step_m: float = 10.0) -> dict:
    """Refine 'natural' shoreline parts: a terrain rise >= ``rise_m`` within ``reach_m`` = vertical face = bulkhead.

    Every part is sampled every ``step_m`` along its length; the sample points are grouped into 500 m
    lattice blocks so that a 30 km coastline part costs the same per metre as a 50 m one and no part is
    ever skipped for being too long.
    """
    from ..terrain.grid import NODATA, SPACING_M, lattice_grid
    t0 = time.time()
    sl = read_geoparquet(SHORE_PATH, SCHEMAS["shoreline"])
    kinds = sl["kind"].values.astype(object)
    src = sl["kind_source"].values.astype(object)
    r = int(round(reach_m / SPACING_M))
    pad = (r + 2) * SPACING_M
    block = 500.0
    n_changed = 0
    n_sampled = 0
    for i, line in enumerate(sl.geometry.values):
        if src[i] != "default":
            continue
        d = np.arange(step_m / 2, max(line.length, step_m / 2 + 1e-6), step_m)
        if d.size == 0:
            continue
        xy = shapely.get_coordinates(shapely.line_interpolate_point(line, d))
        if xy.size == 0:
            continue
        bx = np.floor(xy[:, 0] / block).astype(np.int64)
        by = np.floor(xy[:, 1] / block).astype(np.int64)
        rises: list[float] = []
        for key in np.unique(bx * 1_000_000 + by):
            sel = (bx * 1_000_000 + by) == key
            pts = xy[sel]
            tr, w, h = lattice_grid(pts[:, 0].min() - pad, pts[:, 1].min() - pad, pts[:, 0].max() + pad, pts[:, 1].max() + pad)
            z, _ = stack.read(tr, w, h)
            cols = np.clip(np.rint((pts[:, 0] - (tr.c + SPACING_M / 2)) / SPACING_M).astype(int), 0, w - 1)
            rows = np.clip(np.rint(((tr.f - SPACING_M / 2) - pts[:, 1]) / SPACING_M).astype(int), 0, h - 1)
            for c0, r0 in zip(cols, rows):
                win = z[max(0, r0 - r):r0 + r + 1, max(0, c0 - r):c0 + r + 1]
                v = win[win != NODATA]
                if v.size >= 4:
                    rises.append(float(np.percentile(v, 90) - np.percentile(v, 10)))
        n_sampled += len(rises)
        if not rises:
            continue
        if float(np.median(rises)) >= rise_m:
            kinds[i], src[i] = "bulkhead", "dem_slope"
            n_changed += 1
        else:
            src[i] = "dem_slope"
    sl["kind"] = kinds
    sl["kind_source"] = src
    write_geoparquet(sl, SHORE_PATH, SCHEMAS["shoreline"], "water_shoreline", ["plan_shoreline", "plan_hydro_structures", "usgs_3dep"])
    stats = {"parts": len(sl), "kinds": pd.Series(kinds).value_counts().to_dict(), "kind_sources": pd.Series(src).value_counts().to_dict(),
             "bulkhead_by_dem": n_changed, "dem_probe_points": n_sampled, "seconds": round(time.time() - t0, 1)}
    _save_summary({"shoreline": stats})
    log.info("shoreline classification: %s", stats)
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-osm", action="store_true", help="planimetric water only (no NJ/Nassau water)")
    ap.add_argument("--skip-finalize", action="store_true", help="do not set levels even if DEM intermediates exist")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stats = build_geometry(use_osm=not a.no_osm)
    from ..terrain.ingest import INDEX_PATH
    if not a.skip_finalize and INDEX_PATH.exists():
        from ..terrain.compose import DemStack
        with DemStack(INDEX_PATH) as stack:
            stats["levels"] = finalize_levels(stack)
            stats["shoreline_dem"] = classify_shoreline_by_dem(stack)
    print(json.dumps(stats, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
