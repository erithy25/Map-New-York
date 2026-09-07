"""Water polygons outside the NYC boundary from the OpenStreetMap extract (``data/raw/osm/NewYork.osm.pbf``).

Two sources are combined:

* ``natural=water`` / ``waterway=riverbank|dock`` / ``landuse=reservoir|basin`` / ``natural=bay|strait``
  areas (ways and multipolygon relations) — inland water and the labelled bays.
* ``natural=coastline`` ways, turned into sea polygons with the OSM convention *land on the left, water on
  the right*: the coastline chains are clipped to the scope rectangle, polygonised together with the
  rectangle boundary, and every face is voted water/land by the side on which it lies relative to the
  coastline segments on its boundary. The Hudson, Upper/Lower Bay, Newark Bay, Arthur Kill, Raritan Bay,
  Long Island Sound and the Atlantic are all coastline-bounded in OSM, so this is the only way to get them.

Everything is returned in NYC_TM. The caller clips away the interior of the NYC boundary, where the
planimetric hydrography is authoritative.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import osmium
import shapely
from shapely import wkb
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import linemerge, polygonize, transform, unary_union

from ..crs import NYC_TM, transformer
from .classify import kind_from_osm

log = logging.getLogger("nycsim.water.osm")

WATER_NATURAL = {"water", "bay", "strait"}
WATER_WATERWAY = {"riverbank", "dock"}
WATER_LANDUSE = {"reservoir", "basin"}
SEA_MARGIN_M = 400.0  # polygonise a little beyond the scope so scope-edge faces are closed properly


class _Collector(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.fab = osmium.geom.WKBFactory()
        self.coast: list[bytes] = []
        self.areas: list[tuple[int, bool, dict[str, str], bytes]] = []
        self.bad = 0

    def way(self, w: osmium.osm.Way) -> None:
        if w.tags.get("natural") == "coastline" and len(w.nodes) >= 2:
            try:
                self.coast.append(bytes.fromhex(self.fab.create_linestring(w)))
            except (RuntimeError, ValueError):
                self.bad += 1

    def area(self, a: osmium.osm.Area) -> None:
        t = a.tags
        if not (t.get("natural") in WATER_NATURAL or t.get("waterway") in WATER_WATERWAY or t.get("landuse") in WATER_LANDUSE):
            return
        if t.get("natural") == "water" and t.get("water") in ("wastewater",):
            return  # treatment tanks are not terrain water
        try:
            self.areas.append((a.orig_id(), a.from_way(), dict(t), bytes.fromhex(self.fab.create_multipolygon(a))))
        except (RuntimeError, ValueError):
            self.bad += 1


@dataclass
class OsmWater:
    areas: gpd.GeoDataFrame
    sea: MultiPolygon | Polygon
    stats: dict = field(default_factory=dict)


def _to_tm(geom):
    tr = transformer("WGS84", "NYC_TM")
    return transform(lambda x, y, z=None: tr.transform(x, y), geom)


def _sea_from_coastline(coast_tm: list[LineString], region: Polygon) -> tuple[MultiPolygon | Polygon, dict]:
    """Polygonise coastline chains inside ``region`` and keep the faces on the water (right-hand) side."""
    merged = linemerge(unary_union(coast_tm))
    chains = list(merged.geoms) if merged.geom_type == "MultiLineString" else [merged]
    clipped = []
    for c in chains:
        g = c.intersection(region)
        if g.is_empty:
            continue
        clipped.extend(list(g.geoms) if g.geom_type == "MultiLineString" else [g] if g.geom_type == "LineString" else [])
    if not clipped:
        return MultiPolygon(), {"coast_chains": 0, "faces": 0}
    noded = unary_union([unary_union(clipped), region.exterior])
    faces = list(polygonize(noded))
    if not faces:
        raise RuntimeError("coastline polygonisation produced no faces")
    tree = shapely.STRtree(faces)
    votes_water = np.zeros(len(faces), dtype=np.int64)
    votes_land = np.zeros(len(faces), dtype=np.int64)
    for line in clipped:
        xy = np.asarray(line.coords)
        if len(xy) < 2:
            continue
        p0, p1 = xy[:-1], xy[1:]
        mid = 0.5 * (p0 + p1)
        d = p1 - p0
        n = np.hypot(d[:, 0], d[:, 1])
        ok = n > 1e-6
        if not ok.any():
            continue
        d, mid, n = d[ok], mid[ok], n[ok]
        right = np.column_stack([d[:, 1], -d[:, 0]]) / n[:, None] * 0.25  # 25 cm to the right
        for pts, votes in ((mid + right, votes_water), (mid - right, votes_land)):
            geoms = shapely.points(pts)
            q = tree.query(geoms, predicate="within")
            if q.size:
                np.add.at(votes, q[1], 1)
    water = votes_water > votes_land
    conflicts = int(((votes_water > 0) & (votes_land > 0)).sum())
    unvoted = int(((votes_water == 0) & (votes_land == 0)).sum())
    if unvoted:
        # a face with no coastline on its boundary can only be bounded by other faces + the region edge:
        # inherit the classification of the neighbouring face it shares the longest edge with
        for i in np.flatnonzero((votes_water == 0) & (votes_land == 0)):
            nb = [j for j in tree.query(faces[i], predicate="touches") if j != i and (votes_water[j] or votes_land[j])]
            if nb:
                best = max(nb, key=lambda j: faces[i].boundary.intersection(faces[j].boundary).length)
                water[i] = bool(votes_water[best] > votes_land[best])
    sea = unary_union([f for f, w in zip(faces, water) if w])
    stats = {"coast_chains": len(chains), "coast_pieces": len(clipped), "faces": len(faces), "water_faces": int(water.sum()),
             "conflict_faces": conflicts, "unvoted_faces": unvoted}
    return sea, stats


def extract(pbf_path, scope_bounds: tuple[float, float, float, float]) -> OsmWater:
    """Read the PBF once; return OSM water areas (GeoDataFrame, NYC_TM) and the coastline-derived sea polygon."""
    t0 = time.time()
    col = _Collector()
    col.apply_file(str(pbf_path), locations=True, idx="flex_mem")
    log.info("osm: %d coastline ways, %d water areas, %d unbuildable geometries, %.1fs", len(col.coast), len(col.areas), col.bad, time.time() - t0)
    region = box(scope_bounds[0] - SEA_MARGIN_M, scope_bounds[1] - SEA_MARGIN_M, scope_bounds[2] + SEA_MARGIN_M, scope_bounds[3] + SEA_MARGIN_M)
    coast_tm = [_to_tm(wkb.loads(b)) for b in col.coast]
    coast_tm = [c for c in coast_tm if c.intersects(region)]
    sea, stats = _sea_from_coastline(coast_tm, region)
    stats["sea_area_km2"] = float(sea.area / 1e6)
    rows = []
    for osm_id, from_way, tags, b in col.areas:
        g = _to_tm(shapely.make_valid(wkb.loads(b)))
        if g.is_empty or not g.intersects(region):
            continue
        g = g.intersection(region)
        if g.is_empty:
            continue
        rows.append({"osm_id": int(osm_id), "osm_type": "way" if from_way else "relation", "name": tags.get("name", ""),
                     "kind": kind_from_osm(tags), "tags": ";".join(f"{k}={v}" for k, v in sorted(tags.items()) if k in ("natural", "water", "waterway", "landuse", "intermittent", "tidal", "salt")),
                     "geometry": g})
    areas = gpd.GeoDataFrame(rows, geometry="geometry", crs=NYC_TM) if rows else gpd.GeoDataFrame(
        {"osm_id": [], "osm_type": [], "name": [], "kind": [], "tags": [], "geometry": []}, geometry="geometry", crs=NYC_TM)
    stats["areas_in_region"] = len(areas)
    stats["seconds"] = round(time.time() - t0, 1)
    log.info("osm sea: %s", stats)
    return OsmWater(areas, sea, stats)
