"""Landmark footprint extraction -> ``data/processed/buildings/landmark_footprints.parquet``.

Match order per landmark (first that yields footprints wins, all footprints within 300 m of the given coordinates):
``name``   — OTI footprint ``name`` matches ``name_re``;
``lpc_site`` — an LPC individual landmark site whose ``lpc_name`` matches ``lpc_re``; every non-garage footprint whose
               centroid lies inside the site polygon;
``coords`` — footprints intersecting the search circle, filtered by height/area, chosen by ``pick``.
A BIN is assigned to at most one landmark (processing order = list order); group union rows are added afterwards.
"""
from __future__ import annotations

import logging
import re

import numpy as np
import polars as pl
import pyarrow as pa
import shapely

from ..crs import lonlat_to_tm, tm_to_lonlat
from ..tiling import tile_of
from .attributes import Layer
from .landmark_list import GROUP_NAMES, LANDMARKS, LandmarkSpec
from .schema import landmark_arrow_schema

log = logging.getLogger("nycsim.buildings.landmarks")

NAME_SANITY_RADIUS_M = 300.0


def _select(spec: LandmarkSpec, cand: np.ndarray, height: np.ndarray, area: np.ndarray, dist: np.ndarray) -> np.ndarray:
    if len(cand) == 0:
        return cand
    if spec.pick == "all":
        return cand
    if spec.pick == "tallest":
        return cand[[int(np.argmax(height[cand]))]]
    if spec.pick == "nearest":
        return cand[[int(np.argmin(dist[cand]))]]
    return cand[[int(np.argmax(area[cand]))]]


def build_landmark_footprints(attrs: pl.DataFrame, geoms: np.ndarray, tree: shapely.STRtree, sites: Layer) -> tuple[pa.Table, list[dict]]:
    bins = attrs["bin"].to_numpy()
    names = attrs["name"].fill_null("").to_numpy().astype(object)
    height = attrs["height"].to_numpy().astype(np.float64)
    ground = attrs["ground_z"].to_numpy().astype(np.float64)
    area = attrs["footprint_area"].to_numpy().astype(np.float64)
    fcode = attrs["feature_code"].to_numpy()
    cx = attrs["centroid_x"].to_numpy()
    cy = attrs["centroid_y"].to_numpy()
    landmark_lp = attrs["landmark_id"].fill_null("").to_numpy().astype(object)
    site_names = np.asarray(["" if v is None else str(v) for v in sites.fields["lpc_name"]], dtype=object)
    site_lp = np.asarray(["" if v is None else str(v) for v in sites.fields["lpc_lpnumb"]], dtype=object)
    site_tree = shapely.STRtree(sites.geoms)

    taken = np.zeros(len(bins), dtype=bool)
    rows: list[dict] = []
    report: list[dict] = []
    group_rows: dict[str, list[int]] = {}

    for spec in LANDMARKS:
        x, y = lonlat_to_tm(spec.lon, spec.lat)
        centre = shapely.points(x, y)
        near = np.asarray(tree.query(shapely.buffer(centre, NAME_SANITY_RADIUS_M), predicate="intersects"))
        near = near[~taken[near]]
        dist = np.full(len(bins), np.inf)
        if len(near):
            dist[near] = np.hypot(cx[near] - x, cy[near] - y)
        chosen = np.array([], dtype=np.int64)
        method = "not_found"
        lp = ""

        # 1. footprint name
        if spec.name_re and len(near):
            rx = re.compile(spec.name_re, re.I)
            m = np.array([bool(rx.search(str(n))) for n in names[near]])
            c = near[m]
            if len(c):
                chosen = _select(spec, c, height, area, dist) if spec.pick != "all" else c
                method = "name"
        # 2. LPC site polygon
        if len(chosen) == 0 and spec.lpc_re:
            rx = re.compile(spec.lpc_re, re.I)
            sidx = np.asarray(site_tree.query(shapely.buffer(centre, NAME_SANITY_RADIUS_M), predicate="intersects"))
            sidx = [int(i) for i in sidx if rx.search(site_names[i])]
            if sidx:
                poly = shapely.union_all(sites.geoms[sidx])
                inside = near[shapely.contains_xy(poly, cx[near], cy[near])] if len(near) else near
                inside = inside[(fcode[inside] != 5110) & (area[inside] >= max(spec.min_area, 1.0))]
                if len(inside):
                    chosen = inside if spec.pick == "all" else _select(spec, inside, height, area, dist)
                    method = "lpc_site"
                    lp = site_lp[sidx[0]]
        # 3. coordinates
        if len(chosen) == 0 and len(near):
            c = near[(dist[near] <= spec.radius) & (height[near] >= spec.min_h) & (height[near] <= spec.max_h)
                     & (area[near] >= spec.min_area) & (fcode[near] != 5110)]
            if len(c):
                chosen = _select(spec, c, height, area, dist)
                method = f"coords:{spec.pick}"

        if len(chosen) == 0:
            report.append({"id": spec.id, "name": spec.name, "method": "not_found", "bins": [], "height_m": None,
                           "expected_h": spec.expected_h, "dev_m": None, "n": 0, "lp": ""})
            log.warning("landmark %s: not found (radius %.0f m, min_h %.0f)", spec.id, spec.radius, spec.min_h)
            continue
        chosen = np.unique(chosen)
        taken[chosen] = True
        if not lp:
            lps = [s for s in landmark_lp[chosen] if s]
            lp = lps[0] if lps else ""
        row = _make_row(spec.id, spec.name, chosen, geoms, bins, height, ground, area, method, lp, spec.expected_h)
        rows.append(row)
        if spec.group:
            group_rows.setdefault(spec.group, []).extend(int(i) for i in chosen)
        report.append({"id": spec.id, "name": spec.name, "method": method, "bins": [int(b) for b in bins[chosen]],
                       "height_m": row["height_m"], "expected_h": spec.expected_h, "dev_m": row["height_dev_m"], "n": int(len(chosen)), "lp": lp})
        log.info("landmark %-28s %-14s bins=%s h=%.1f", spec.id, method, [int(b) for b in bins[chosen]][:6], row["height_m"])

    for gid, idxs in group_rows.items():
        idx = np.unique(np.asarray(idxs, dtype=np.int64))
        row = _make_row(gid, GROUP_NAMES.get(gid, gid), idx, geoms, bins, height, ground, area, "group_union", "", None)
        rows.append(row)

    table = pa.Table.from_pylist(rows, schema=landmark_arrow_schema(_bbox(rows)))
    return table, report


def _bbox(rows: list[dict]) -> list[float] | None:
    if not rows:
        return None
    g = shapely.from_wkb([r["geometry"] for r in rows])
    return [float(v) for v in shapely.total_bounds(g)]


def _make_row(lid: str, name: str, idx: np.ndarray, geoms: np.ndarray, bins: np.ndarray, height: np.ndarray,
              ground: np.ndarray, area: np.ndarray, method: str, lp: str, expected_h: float | None) -> dict:
    geom = shapely.union_all(geoms[idx])
    if geom.geom_type == "Polygon":
        geom = shapely.MultiPolygon([geom])
    elif geom.geom_type != "MultiPolygon":
        geom = shapely.MultiPolygon([g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"])
    cen = shapely.centroid(geom)
    lon, lat = tm_to_lonlat(cen.x, cen.y)
    h = float(np.max(height[idx]))
    gz = float(np.min(ground[idx]))
    rz = float(np.max(ground[idx] + height[idx]))
    return {
        "landmark_id": lid, "name": name, "bins": [int(b) for b in bins[idx]], "geometry": shapely.to_wkb(geom),
        "height_m": h, "ground_z": gz, "roof_z": rz, "centroid": shapely.to_wkb(cen),
        "centroid_x": float(cen.x), "centroid_y": float(cen.y), "lon": float(lon), "lat": float(lat),
        "match_method": method, "n_footprints": int(len(idx)), "footprint_area": float(np.sum(area[idx])),
        "lp_number": lp, "expected_height_m": expected_h, "height_dev_m": (h - expected_h) if expected_h is not None else None,
        "tile": tile_of(cen.x, cen.y).name,
    }
