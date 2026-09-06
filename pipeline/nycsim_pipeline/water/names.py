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
MAX_NEAREST_M = 5_000.0    # a sea cell farther than this from any named body stays unnamed
MIN_PIECE_M2 = 1.0         # a split piece below this is a sliver of the polygonisation, not a water body
OSM_NAME_MIN_FRAC = 0.5    # overlap fraction required before an OSM name is adopted
MIN_LABEL_BODY_M2 = 1_000_000.0  # only bodies >= 1 km2 (after dissolving by name) may name the open sea
LABEL_KINDS = ("ocean", "bay", "river", "canal")  # a lake or a basin never names open sea
CLIP_STEP_M = 4_000.0      # boolean ops on the sea polygon run on 4 km clips, never on the whole thing


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


def canonical_names(hydro: gpd.GeoDataFrame) -> np.ndarray:
    """One spelling per water body: the planimetric spelling wins over OSM's for the same name."""
    names = hydro["name"].values.astype(object)
    src = hydro["name_source"].values.astype(object)
    preferred: dict[str, str] = {}
    for i, n in enumerate(names):
        if not n:
            continue
        k = n.upper()
        if k not in preferred or src[i] == "planimetric":
            preferred[k] = n
    return np.array([preferred.get(n.upper(), n) if n else "" for n in names], dtype=object)


def _label_bodies(hydro: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Named open-water bodies dissolved by name — the candidates that may name a piece of open sea.

    Dissolving matters: the planimetric database splits the East River into 60 polygons, none of which
    would clear the area threshold on its own.
    """
    sel = hydro[(hydro["name"].values != "") & hydro["is_open_water"].values
                & np.isin(hydro["kind"].values, LABEL_KINDS)]
    if sel.empty:
        return gpd.GeoDataFrame({"name": [], "kind": [], "geometry": []}, geometry="geometry", crs=NYC_TM)
    rows = []
    for name, grp in sel.groupby("name", sort=True):
        g = shapely.union_all(grp.geometry.values)
        if g.area < MIN_LABEL_BODY_M2:
            continue
        rows.append({"name": name, "kind": grp["kind"].mode().iloc[0], "geometry": g})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=NYC_TM)


def _label_raster(named: gpd.GeoDataFrame) -> tuple[np.ndarray, Affine]:
    """Nearest-named-body label id per ``LABEL_RES_M`` cell over the scope (0 = farther than MAX_NEAREST_M).

    The bodies are rasterised (largest first, so a small body wins its own cells) and the nearest label is
    then propagated with a Euclidean distance transform. Computing exact point-to-polygon distances instead
    would be O(cells x polygon vertices) — hours for the dissolved Atlantic/Sound polygons.
    """
    from scipy.ndimage import distance_transform_edt

    w = int(np.ceil((SCOPE_XMAX - SCOPE_XMIN) / LABEL_RES_M))
    h = int(np.ceil((SCOPE_YMAX - SCOPE_YMIN) / LABEL_RES_M))
    tr = Affine(LABEL_RES_M, 0.0, SCOPE_XMIN, 0.0, -LABEL_RES_M, SCOPE_YMAX)
    order = np.argsort(-shapely.area(named.geometry.values), kind="stable")
    seed = np.zeros((h, w), dtype=np.int32)
    rasterize(((named.geometry.values[i], int(i) + 1) for i in order), out=seed, transform=tr, all_touched=True)
    if not seed.any():
        return seed, tr
    dist, ind = distance_transform_edt(seed == 0, sampling=(LABEL_RES_M, LABEL_RES_M), return_indices=True)
    lab = seed[ind[0], ind[1]]
    lab[dist > MAX_NEAREST_M] = 0
    return lab.astype(np.int32), tr


def _polygons_only(g):
    """Keep only the polygonal parts of a geometry (clipping can emit lines/points)."""
    if g is None or g.is_empty:
        return g
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [p for p in getattr(g, "geoms", [g]) if p.geom_type in ("Polygon", "MultiPolygon")]
    return shapely.union_all(parts) if parts else shapely.Polygon()


def _clip_cells(bounds: tuple[float, float, float, float], step: float):
    """Lattice-aligned clipping rectangles covering ``bounds`` — keeps every boolean op small."""
    x0 = np.floor(bounds[0] / step) * step
    y0 = np.floor(bounds[1] / step) * step
    for yy in np.arange(y0, bounds[3] + step, step):
        for xx in np.arange(x0, bounds[2] + step, step):
            yield float(xx), float(yy), float(xx + step), float(yy + step)


def _split_sea(hydro: gpd.GeoDataFrame, named: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Split the unnamed coastline-derived sea into nearest-named-body regions and name the pieces.

    Only the OSM sea faces (``source == 'osm'`` with no OSM id, i.e. produced by polygonising the
    coastline) are split. Named bodies, every planimetric polygon and every identified OSM water area are
    left exactly as they are — an unnamed pond in a park must never inherit the name of the harbour.

    The sea polygon has ~10^5 vertices and spans the whole scope, so it is clipped into ``CLIP_STEP_M``
    squares before any boolean operation: every intersection then runs on a small piece, and the pieces of
    one name are unioned back together at the end. Same result, bounded cost.
    """
    unnamed = hydro.index[(hydro["name"].values == "") & hydro["is_open_water"].values
                          & (hydro["source"].values == "osm") & (hydro["osm_id"].values == 0)]
    if len(unnamed) == 0 or named.empty:
        return hydro
    lab, tr = _label_raster(named)
    regions: dict[int, list] = {}
    for geom, val in shapes(lab, mask=lab > 0, transform=tr, connectivity=4):
        regions.setdefault(int(val), []).append(shapely.geometry.shape(geom))
    labels = sorted(regions)
    region_geom = [shapely.union_all(regions[k]) for k in labels]
    region_tree = shapely.STRtree(region_geom)
    name_of = {i + 1: str(named["name"].values[i]) for i in range(len(named))}
    kind_of = {i + 1: str(named["kind"].values[i]) for i in range(len(named))}
    rows: list[dict] = []
    keep = np.ones(len(hydro), dtype=bool)
    for i in unnamed:
        g = hydro.geometry.values[i]
        base = hydro.iloc[i].to_dict()
        keep[i] = False
        by_label: dict[int, list] = {}
        rest_parts: list = []
        for x0, y0, x1, y1 in _clip_cells(g.bounds, CLIP_STEP_M):
            sub = _polygons_only(shapely.make_valid(shapely.clip_by_rect(g, x0, y0, x1, y1)))
            if sub.is_empty:
                continue
            covered = []
            for j in region_tree.query(sub, predicate="intersects"):
                piece = _polygons_only(shapely.intersection(sub, region_geom[j]))
                if piece.is_empty or piece.area < MIN_PIECE_M2:
                    continue
                by_label.setdefault(int(j), []).append(piece)
                covered.append(piece)
            rest = _polygons_only(shapely.difference(sub, shapely.union_all(covered))) if covered else sub
            if not rest.is_empty and rest.area >= MIN_PIECE_M2:
                rest_parts.append(rest)
        for j, parts in sorted(by_label.items()):
            lid = labels[j]
            r = dict(base)
            r["geometry"] = shapely.union_all(parts)
            r["name"] = name_of[lid]
            r["kind"] = base["kind"] if base["kind"] in ("ocean", "canal", "basin") else kind_of[lid]
            r["name_source"] = "nearest_named_body"
            rows.append(r)
        if rest_parts:
            r = dict(base)
            r["geometry"] = shapely.union_all(rest_parts)
            r["name_source"] = "unnamed"
            rows.append(r)
    out = pd.concat([hydro[keep], gpd.GeoDataFrame(rows, geometry="geometry", crs=NYC_TM)], ignore_index=True)
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=NYC_TM)
    a0, a1 = float(hydro.geometry.area.sum()), float(out.geometry.area.sum())
    if abs(a1 - a0) > 1e-3 * max(a0, 1.0):
        raise ValueError(f"sea split lost area: {a0/1e6:.3f} km2 -> {a1/1e6:.3f} km2")
    return out


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
    hydro["name"] = canonical_names(hydro)
    named = _label_bodies(hydro)
    stats["label_bodies"] = len(named)
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
