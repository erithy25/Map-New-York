"""Real names for every water body (DATA_CONTRACTS §4 ``name``).

Three sources, in decreasing authority, each recorded in the extension column ``name_source``:

* ``planimetric`` — the NYC planimetric HYDROGRAPHY ``name`` field (Hudson River, East River, Harlem River,
  Gowanus Canal, Newtown Creek, Bronx River, Kill Van Kull, Arthur Kill, Jamaica Bay, The Lake, Harlem
  Meer, …). Authoritative inside the city (the city's water boundary runs to the state line, so it names
  the whole Hudson/East River/Upper Bay surface, not just a strip).
* ``osm`` — for a planimetric polygon whose ``name`` is empty, the name of the OpenStreetMap water polygon
  that covers most of it (≥ 50 % of the smaller area and ≥ 50 % of the planimetric polygon). This is what
  supplies e.g. "Jacqueline Kennedy Onassis Reservoir", "Turtle Pond", "Conservatory Water" in Central Park
  and the New Jersey / Nassau bodies.
* ``nearest_named_body`` — the coastline-derived sea outside the city line is one unnamed OSM polygon per
  connected face. It is split by nearest named neighbour: a 100 m label raster over the scope assigns every
  cell the nearest named open-water body, the label regions are polygonised and intersected with the sea.
  The NJ half of the Hudson therefore becomes "HUDSON RIVER", the water south of Rockaway "ATLANTIC OCEAN",
  and so on. Flagged, never presented as surveyed.

Rows keep ``name = ''`` and ``name_source = 'unnamed'`` when nothing names them (small unnamed ponds and
marshes, and sea pieces farther than ``MAX_NEAREST_M`` from any named body).
"""
from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from rasterio.features import rasterize, shapes
from rasterio.transform import Affine

from ..crs import NYC_TM, SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN

log = logging.getLogger("nycsim.water.names")

LABEL_RES_M = 100.0        # resolution of the nearest-named-body label raster
MAX_NEAREST_M = 12_000.0   # a sea cell farther than this from any named body stays unnamed
MIN_PIECE_M2 = 10_000.0    # sea pieces below this are merged back into the largest neighbouring piece
OSM_NAME_MIN_FRAC = 0.5    # overlap fraction required before an OSM name is adopted


def _osm_names(hydro: gpd.GeoDataFrame, osm_areas: gpd.GeoDataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(name, adopted) arrays: OSM names for planimetric polygons whose own name is empty."""
    names = hydro["name"].values.astype(object).copy()
    adopted = np.zeros(len(hydro), dtype=bool)
    named = osm_areas[osm_areas["name"].astype(str).str.len() > 0]
    if named.empty:
        return names, adopted
    tree = shapely.STRtree(named.geometry.values)
    targets = np.flatnonzero((hydro["source"].values == "nyc_planimetric") & (hydro["name"].values == ""))
    if targets.size == 0:
        return names, adopted
    hi, oi = tree.query(hydro.geometry.values[targets], predicate="intersects")
    if hi.size == 0:
        return names, adopted
    best: dict[int, tuple[float, str]] = {}
    for k in range(hi.size):
        t = int(targets[hi[k]])
        g = hydro.geometry.values[t]
        o = named.geometry.values[oi[k]]
        inter = g.intersection(o).area
        if inter <= 0:
            continue
        frac = inter / max(g.area, 1e-9)
        if frac < OSM_NAME_MIN_FRAC:
            continue
        nm = str(named["name"].values[oi[k]])
        if t not in best or frac > best[t][0]:
            best[t] = (frac, nm)
    for t, (_, nm) in best.items():
        names[t] = nm
        adopted[t] = True
    return names, adopted


def _label_raster(named: gpd.GeoDataFrame) -> tuple[np.ndarray, Affine]:
    """Nearest-named-body label id per ``LABEL_RES_M`` cell over the scope (0 = farther than MAX_NEAREST_M)."""
    w = int(np.ceil((SCOPE_XMAX - SCOPE_XMIN) / LABEL_RES_M))
    h = int(np.ceil((SCOPE_YMAX - SCOPE_YMIN) / LABEL_RES_M))
    tr = Affine(LABEL_RES_M, 0.0, SCOPE_XMIN, 0.0, -LABEL_RES_M, SCOPE_YMAX)
    cx = SCOPE_XMIN + LABEL_RES_M * (np.arange(w) + 0.5)
    cy = SCOPE_YMAX - LABEL_RES_M * (np.arange(h) + 0.5)
    gx, gy = np.meshgrid(cx, cy)
    pts = shapely.points(gx.ravel(), gy.ravel())
    tree = shapely.STRtree(named.geometry.values)
    idx = tree.nearest(pts)
    dist = shapely.distance(pts, named.geometry.values[idx])
    lab = (idx + 1).astype(np.int32)
    lab[dist > MAX_NEAREST_M] = 0
    return lab.reshape(h, w), tr


def _split_sea(hydro: gpd.GeoDataFrame, named: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Split every unnamed *open-water* polygon along nearest-named-body regions and name the pieces."""
    unnamed = hydro.index[(hydro["name"].values == "") & hydro["is_open_water"].values]
    if len(unnamed) == 0 or named.empty:
        return hydro
    lab, tr = _label_raster(named)
    regions: dict[int, list] = {}
    for geom, val in shapes(lab, mask=lab > 0, transform=tr, connectivity=4):
        regions.setdefault(int(val), []).append(shapely.geometry.shape(geom))
    region_geom = {k: shapely.union_all(v) for k, v in regions.items()}
    name_of = {i + 1: str(named["name"].values[i]) for i in range(len(named))}
    kind_of = {i + 1: str(named["kind"].values[i]) for i in range(len(named))}
    rows: list[dict] = []
    keep = np.ones(len(hydro), dtype=bool)
    for i in unnamed:
        g = hydro.geometry.values[i]
        base = hydro.iloc[i].to_dict()
        keep[i] = False
        produced = []
        for lid, rg in region_geom.items():
            if not g.intersects(rg):
                continue
            piece = g.intersection(rg)
            piece = shapely.union_all([p for p in getattr(piece, "geoms", [piece]) if p.geom_type in ("Polygon", "MultiPolygon")])
            if piece.is_empty or piece.area < MIN_PIECE_M2:
                continue
            r = dict(base)
            r["geometry"] = piece
            r["name"] = name_of[lid]
            r["kind"] = base["kind"] if base["kind"] in ("ocean", "canal", "basin") else kind_of[lid]
            r["name_source"] = "nearest_named_body"
            produced.append(r)
        covered = shapely.union_all([r["geometry"] for r in produced]) if produced else None
        rest = g.difference(covered) if covered is not None else g
        rest = shapely.union_all([p for p in getattr(rest, "geoms", [rest]) if p.geom_type in ("Polygon", "MultiPolygon")]) if not rest.is_empty else rest
        if not rest.is_empty and rest.area >= MIN_PIECE_M2:
            r = dict(base)
            r["geometry"] = rest
            r["name_source"] = "unnamed"
            produced.append(r)
        rows.extend(produced)
    out = pd.concat([hydro[keep], gpd.GeoDataFrame(rows, geometry="geometry", crs=NYC_TM)], ignore_index=True)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=NYC_TM)


def assign_names(hydro: gpd.GeoDataFrame, osm_areas: gpd.GeoDataFrame | None, osm_id_base: int) -> tuple[gpd.GeoDataFrame, dict]:
    """Fill ``name``/``name_source`` and split the unnamed sea into named pieces. Re-numbers ``water_id``."""
    hydro = hydro.copy()
    hydro["name"] = [("" if n is None or (isinstance(n, float) and np.isnan(n)) or str(n).strip().lower() in ("", "nan", "none", "null", "<null>", "unset") else str(n).strip())
                     for n in hydro["name"].values]
    src = np.where(hydro["name"].values != "", np.where(hydro["source"].values == "osm", "osm", "planimetric"), "unnamed").astype(object)
    hydro["name_source"] = src
    stats = {"planimetric_named": int((src == "planimetric").sum()), "osm_named": int((src == "osm").sum())}
    if osm_areas is not None and len(osm_areas):
        names, adopted = _osm_names(hydro, osm_areas)
        hydro["name"] = names
        hydro.loc[adopted, "name_source"] = "osm"
        stats["osm_name_transfers"] = int(adopted.sum())
    named = hydro[(hydro["name"].values != "") & hydro["is_open_water"].values][["name", "kind", "geometry"]].reset_index(drop=True)
    before = len(hydro)
    hydro = _split_sea(hydro, named)
    stats["sea_pieces_created"] = len(hydro) - before
    hydro["area_m2"] = hydro.geometry.area.astype("float64")
    hydro = hydro.sort_values(["source", "kind", "name", "plan_source_id"], kind="stable").reset_index(drop=True)
    is_plan = hydro["source"].values == "nyc_planimetric"
    wid = np.zeros(len(hydro), dtype=np.int64)
    wid[is_plan] = np.arange(1, int(is_plan.sum()) + 1, dtype=np.int64)
    wid[~is_plan] = osm_id_base + np.arange(1, int((~is_plan).sum()) + 1, dtype=np.int64)
    hydro["water_id"] = wid
    stats["named_polygons"] = int((hydro["name"].values != "").sum())
    stats["named_area_km2"] = float(hydro.loc[hydro["name"].values != "", "area_m2"].sum() / 1e6)
    stats["unnamed_area_km2"] = float(hydro.loc[hydro["name"].values == "", "area_m2"].sum() / 1e6)
    stats["distinct_names"] = int(pd.Series(hydro["name"].values).replace("", np.nan).nunique())
    log.info("water names: %s", stats)
    return hydro, stats
