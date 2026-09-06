"""OpenStreetMap extraction (pyosmium) for the roads stage.

Produces three Parquet caches (NYC_TM coordinates):
  osm_nodes.parquet        highway=* nodes (traffic_signals, stop, give_way, crossing, ...) with direction tags
  osm_ways.parquet         vehicular highway ways with oneway/lanes/turn:lanes/maxspeed/bridge/tunnel/surface/name,
                           node id list and LineString geometry
  osm_restrictions.parquet type=restriction relations with from/via/to (via node coordinates resolved)

The raw extract is first clipped to the project scope and filtered with the ``osmium`` CLI (C++), which
is ~50x faster than doing it in Python; the clipped file is cached next to the outputs.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmium
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from ..crs import NYC_TM, lonlat_to_tm

log = logging.getLogger("nycsim.roads.osm")

SCOPE_BBOX_LONLAT = (-74.30, 40.457, -73.66, 40.943)
NODE_HIGHWAY_KEEP = {"traffic_signals", "stop", "give_way", "crossing", "motorway_junction", "mini_roundabout", "turning_circle", "turning_loop", "priority", "traffic_signals;crossing", "stop;crossing"}
WAY_HIGHWAY_DROP = {"footway", "steps", "path", "pedestrian", "corridor", "elevator", "platform", "bridleway", "track", "proposed", "construction", "raceway", "cycleway", "rest_area", "services", "abandoned", "razed"}
RESTRICTION_KEYS = ("restriction", "restriction:motorcar", "restriction:motor_vehicle", "restriction:vehicle", "restriction:hgv", "restriction:bus", "restriction:conditional")


class OsmExtractError(RuntimeError):
    pass


def prefilter(pbf: Path, out_dir: Path, force: bool = False) -> Path:
    """Clip to scope and keep highway objects + restriction relations with the osmium CLI."""
    out_dir.mkdir(parents=True, exist_ok=True)
    clipped = out_dir / "osm_scope.osm.pbf"
    roads = out_dir / "osm_roads.osm.pbf"
    if roads.exists() and not force and roads.stat().st_mtime >= pbf.stat().st_mtime:
        return roads
    exe = shutil.which("osmium")
    if exe is None:
        raise OsmExtractError("osmium CLI not found")
    b = ",".join(f"{v:.4f}" for v in SCOPE_BBOX_LONLAT)
    t0 = time.time()
    subprocess.run([exe, "extract", "-b", b, "--strategy", "complete_ways", "--overwrite", "-o", str(clipped), str(pbf)], check=True, capture_output=True)
    subprocess.run([exe, "tags-filter", "--overwrite", "-o", str(roads), str(clipped), "w/highway", "n/highway", "r/type=restriction"], check=True, capture_output=True)
    clipped.unlink(missing_ok=True)
    log.info("osmium prefilter -> %s (%.1f MB) in %.1fs", roads, roads.stat().st_size / 1e6, time.time() - t0)
    return roads


def _tag(o, k: str) -> str | None:
    v = o.tags.get(k)
    return v if v else None


def extract(pbf: Path, cache_dir: Path, force: bool = False) -> dict[str, Path]:
    """Run the extraction (or reuse caches). Returns paths of the three parquet files."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = {k: cache_dir / f"osm_{k}.parquet" for k in ("nodes", "ways", "restrictions")}
    if all(p.exists() for p in paths.values()) and not force:
        log.info("OSM caches present in %s", cache_dir)
        return paths
    roads_pbf = prefilter(pbf, cache_dir, force=force)
    t0 = time.time()

    node_ids: list[int] = []
    node_lon: list[float] = []
    node_lat: list[float] = []
    tagged: list[tuple] = []
    ways: list[tuple] = []
    way_nodes: list[np.ndarray] = []
    way_xy: list[np.ndarray] = []
    rels: list[tuple] = []

    fp = osmium.FileProcessor(str(roads_pbf)).with_locations()
    for o in fp:
        if o.is_node():
            node_ids.append(o.id)
            node_lon.append(o.location.lon)
            node_lat.append(o.location.lat)
            h = _tag(o, "highway")
            if h and (h in NODE_HIGHWAY_KEEP or h.startswith("traffic_signals") or h.startswith("stop")):
                tagged.append((o.id, o.location.lon, o.location.lat, h, _tag(o, "direction"), _tag(o, "stop"),
                               _tag(o, "traffic_signals:direction"), _tag(o, "crossing"), _tag(o, "traffic_signals")))
        elif o.is_way():
            h = _tag(o, "highway")
            if not h or h in WAY_HIGHWAY_DROP:
                continue
            refs = []
            lon = []
            lat = []
            for nd in o.nodes:
                refs.append(nd.ref)
                if nd.location.valid():
                    lon.append(nd.location.lon)
                    lat.append(nd.location.lat)
            if len(lon) < 2:
                continue
            ways.append((o.id, h, _tag(o, "name"), _tag(o, "oneway"), _tag(o, "lanes"), _tag(o, "lanes:forward"), _tag(o, "lanes:backward"),
                         _tag(o, "turn:lanes"), _tag(o, "turn:lanes:forward"), _tag(o, "turn:lanes:backward"), _tag(o, "maxspeed"),
                         _tag(o, "bridge"), _tag(o, "tunnel"), _tag(o, "layer"), _tag(o, "ref"), _tag(o, "surface"), _tag(o, "junction")))
            way_nodes.append(np.asarray(refs, dtype=np.int64))
            way_xy.append(np.column_stack([lon, lat]))
        elif o.is_relation():
            if _tag(o, "type") != "restriction":
                continue
            r = None
            for k in RESTRICTION_KEYS:
                r = _tag(o, k)
                if r:
                    break
            if not r:
                continue
            frm = [m.ref for m in o.members if m.role == "from" and m.type == "w"]
            to = [m.ref for m in o.members if m.role == "to" and m.type == "w"]
            via_n = [m.ref for m in o.members if m.role == "via" and m.type == "n"]
            via_w = [m.ref for m in o.members if m.role == "via" and m.type == "w"]
            rels.append((o.id, r, frm, to, via_n, via_w, _tag(o, "except"), bool(_tag(o, "restriction:conditional")) and not _tag(o, "restriction")))
    log.info("OSM pass: %d nodes, %d tagged nodes, %d ways, %d restrictions in %.1fs", len(node_ids), len(tagged), len(ways), len(rels), time.time() - t0)

    ids_arr = np.asarray(node_ids, dtype=np.int64)
    order = np.argsort(ids_arr)
    ids_sorted = ids_arr[order]
    lon_sorted = np.asarray(node_lon)[order]
    lat_sorted = np.asarray(node_lat)[order]

    def loc_of(nid: int) -> tuple[float, float] | None:
        i = int(np.searchsorted(ids_sorted, nid))
        if i < len(ids_sorted) and ids_sorted[i] == nid:
            return float(lon_sorted[i]), float(lat_sorted[i])
        return None

    # nodes
    nd = pd.DataFrame(tagged, columns=["id", "lon", "lat", "highway", "direction", "stop", "ts_direction", "crossing", "ts_kind"])
    x, y = lonlat_to_tm(nd["lon"].to_numpy(), nd["lat"].to_numpy()) if len(nd) else (np.array([]), np.array([]))
    nd["x"] = np.asarray(x, dtype=np.float64)
    nd["y"] = np.asarray(y, dtype=np.float64)
    pq.write_table(pa.Table.from_pandas(nd, preserve_index=False), paths["nodes"], compression="snappy")

    # ways
    wd = pd.DataFrame(ways, columns=["id", "highway", "name", "oneway", "lanes", "lanes_forward", "lanes_backward", "turn_lanes", "turn_lanes_forward", "turn_lanes_backward", "maxspeed", "bridge", "tunnel", "layer", "ref", "surface", "junction"])
    geoms = []
    for xy in way_xy:
        tx, ty = lonlat_to_tm(xy[:, 0], xy[:, 1])
        geoms.append(shapely.LineString(np.column_stack([tx, ty])))
    wd["node_ids"] = way_nodes
    wgdf = gpd.GeoDataFrame(wd, geometry=geoms, crs=NYC_TM)
    wgdf.to_parquet(paths["ways"], compression="snappy")

    # restrictions (via-node coordinates resolved here so consumers need no node table)
    rows = []
    for rid, r, frm, to, via_n, via_w, exc, cond in rels:
        vx = vy = np.nan
        if len(via_n) == 1:
            loc = loc_of(via_n[0])
            if loc is not None:
                vx, vy = lonlat_to_tm(loc[0], loc[1])
        rows.append((rid, r, frm[0] if len(frm) == 1 else -1, to[0] if len(to) == 1 else -1, via_n[0] if len(via_n) == 1 else -1,
                     len(via_w), float(vx), float(vy), exc or "", cond, len(frm), len(to)))
    rd = pd.DataFrame(rows, columns=["rel_id", "restriction", "from_way", "to_way", "via_node", "n_via_ways", "via_x", "via_y", "except", "conditional_only", "n_from", "n_to"])
    pq.write_table(pa.Table.from_pandas(rd, preserve_index=False), paths["restrictions"], compression="snappy")
    log.info("OSM caches written: %d nodes, %d ways, %d restrictions", len(nd), len(wd), len(rd))
    return paths


def load(cache_dir: Path) -> tuple[pd.DataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    nodes = pd.read_parquet(cache_dir / "osm_nodes.parquet")
    ways = gpd.read_parquet(cache_dir / "osm_ways.parquet")
    rest = pd.read_parquet(cache_dir / "osm_restrictions.parquet")
    return nodes, ways, rest
