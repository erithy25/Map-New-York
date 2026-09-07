"""Rail structures: elevated / viaduct / embankment / open-cut track with measured deck heights.

Two real sources are combined:

* **NYC planimetric Railroad Line** (``anc7-97cy``, OTI 2022 photogrammetry). Its ``feat_code`` *is* the structure
  class — 2400 at grade, 2410 elevated, 2420 embankment, 2430 viaduct centreline, 2440 open-cut depression,
  2450 railway fence, 2465 abandoned (NYC Planimetrics *Capture Rules*, RAILROAD section). This is the authority
  for where the structure is.
* **OSM rail** (``osm/rail.parquet``, ODbL) supplies the operator, the line name and the mode (``railway=subway |
  rail | light_rail | tram``) for each structure, matched by proximity, and adds bridge/embankment/cutting
  segments the planimetric layer does not carry.

**Deck height** is measured, not assumed, wherever the city surveyed it: planimetric *Bridge Elevation* points
(``plan_elevation_points``, ``sub_code`` 300020 — captured at the start, middle and end of every visible bridge
and overpass, in feet) give the deck elevation, and the ground model (spot elevations + LiDAR building grades,
:mod:`..furniture.elevation`) gives the ground under it. ``deck_height_m = deck_z − ground_z``. Structures with no
bridge elevation point within :data:`DECK_SEARCH_M` fall back to the **median measured deck height of the same
structure class** (never to a guessed constant) and are flagged ``deck_height_source = 1``. Open-cut track is
below grade, so a deck height is not defined for it: those rows carry ``deck_height_source = 2`` and a NaN height.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely
from scipy.spatial import cKDTree

from ..crs import transformer
from ..paths import PROCESSED, RAW
from ..furniture.elevation import SUB_BRIDGE, GroundModel, load_elevation_points

log = logging.getLogger("nycsim.transit.structures")

RAIL_LINE = RAW / "nyc_opendata" / "plan_railroad_line.geojson"
OSM_RAIL = PROCESSED / "osm" / "rail.parquet"

FEAT_CLASS: dict[str, str] = {
    "2400": "at_grade", "2410": "elevated", "2420": "embankment", "2430": "viaduct",
    "2440": "open_cut", "2450": "fence", "2465": "abandoned",
}
STRUCTURE_CLASSES = ("elevated", "viaduct", "embankment", "open_cut")
# Classes whose deck is above grade, so that a nearby Bridge Elevation point is the elevation of *this* deck.
# ``open_cut`` is excluded on purpose: the track runs below grade there and the bridge elevation points around an
# open cut belong to the road bridges crossing over it, so a "deck height" measured from them would be wrong.
DECK_CLASSES = ("elevated", "viaduct", "embankment")
DECK_SOURCE_MEASURED = 0
DECK_SOURCE_CLASS_MEDIAN = 1
DECK_SOURCE_NOT_APPLICABLE = 2

# Plausibility band per class, metres above the ground beneath. A "measured" deck height outside its band means
# the bridge elevation points inside DECK_SEARCH_M belong to a different structure (a road bridge over or under the
# track), so the measurement is rejected and the class median is used instead. Upper bounds are set from the real
# extremes of the network: Smith-9th St on the Culver Viaduct is the highest rapid-transit station in the world at
# about 27.5 m, and the Hell Gate approach viaducts are higher still.
DECK_HEIGHT_BOUNDS_M: dict[str, tuple[float, float]] = {
    "elevated": (1.0, 40.0), "viaduct": (1.0, 60.0), "embankment": (0.5, 25.0),
}

DECK_SEARCH_M = 25.0      # radius around a structure in which a bridge elevation point is taken as its deck
GROUND_STEP_M = 20.0      # spacing of the ground samples taken along a structure
OSM_MATCH_M = 30.0        # radius for attaching OSM name/operator/mode to a planimetric structure
OSM_EXTRA_M = 40.0        # an OSM structure further than this from any planimetric structure is added on its own


def load_planimetric_rail(path: Path = RAIL_LINE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (LineString geometries in NYC_TM, feature class name, railroad name) for every railroad line part."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline.download --id plan_railroad_line")
    tr = transformer("WGS84", "NYC_TM")
    geoms: list[np.ndarray] = []
    codes: list[list[str]] = []
    names: list[list[str]] = []
    with pyogrio.open_arrow(path, columns=["feat_code", "name"], batch_size=50_000) as (_meta, stream):
        reader = pa.RecordBatchReader.from_stream(stream)
        for batch in reader:
            g = shapely.from_wkb(batch.column("wkb_geometry").to_pylist())
            geoms.append(g)
            codes.append([str(v or "") for v in batch.column("feat_code").to_pylist()])
            names.append([str(v or "") for v in batch.column("name").to_pylist()])
    g = np.concatenate(geoms)
    code = np.concatenate([np.asarray(c, dtype=object) for c in codes])
    name = np.concatenate([np.asarray(n, dtype=object) for n in names])
    g = shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))
    parts, index = shapely.get_parts(g, return_index=True)   # MultiLineString -> LineString
    cls = np.array([FEAT_CLASS.get(c, "unknown") for c in code[index]], dtype=object)
    log.info("planimetric railroad line: %d features -> %d line parts", len(g), len(parts))
    return parts, cls, name[index]


def load_osm_rail(path: Path = OSM_RAIL) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run: python -m nycsim_pipeline osm")
    t = pq.read_table(path)
    geoms = shapely.from_wkb(t.column("geometry").to_pylist())
    d = {c: t.column(c).to_pylist() for c in ("railway", "name", "operator", "service", "usage", "bridge", "tunnel")}
    return {
        "geometry": np.asarray(geoms, dtype=object),
        "osm_id": t.column("osm_id").to_numpy(zero_copy_only=False).astype(np.int64),
        "is_elevated": t.column("is_elevated").to_numpy(zero_copy_only=False).astype(bool),
        "embankment": t.column("embankment").to_numpy(zero_copy_only=False).astype(bool),
        "cutting": t.column("cutting").to_numpy(zero_copy_only=False).astype(bool),
        "railway": [str(v or "") for v in d["railway"]],
        "name": [str(v or "") for v in d["name"]],
        "operator": [str(v or "") for v in d["operator"]],
        "service": [str(v or "") for v in d["service"]],
        "usage": [str(v or "") for v in d["usage"]],
        "tunnel": [str(v or "") for v in d["tunnel"]],
    }


def _sample_points(line, step: float) -> np.ndarray:
    length = float(shapely.length(line))
    if length <= 0:
        return shapely.get_coordinates(line)[:, :2]
    d = np.arange(0.0, length + step, step)
    d[-1] = min(d[-1], length)
    return shapely.get_coordinates(shapely.line_interpolate_point(line, d))[:, :2]


def deck_heights(lines: np.ndarray, cls: np.ndarray, ground: GroundModel,
                 bridge_pts) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Measured deck elevation, ground elevation, deck height, source flag and supporting point count."""
    n = len(lines)
    deck_z = np.full(n, np.nan)
    ground_z = np.full(n, np.nan)
    n_pts = np.zeros(n, dtype=np.int32)
    tree = cKDTree(np.column_stack([bridge_pts.x, bridge_pts.y])) if len(bridge_pts) else None
    for i, line in enumerate(lines):
        pts = _sample_points(line, GROUND_STEP_M)
        if pts.size == 0:
            continue
        gz, _src = ground.sample(pts[:, 0], pts[:, 1])
        ground_z[i] = float(np.median(gz))
        if tree is None or cls[i] not in DECK_CLASSES:
            continue
        hits = tree.query_ball_point(pts, DECK_SEARCH_M)
        found = sorted({j for h in hits for j in h})
        if found:
            deck_z[i] = float(np.median(bridge_pts.z[np.asarray(found)]))
            n_pts[i] = len(found)
    height = deck_z - ground_z
    rejected = 0
    for c, (lo, hi) in DECK_HEIGHT_BOUNDS_M.items():
        m = (cls == c) & np.isfinite(height) & ((height < lo) | (height > hi))
        rejected += int(m.sum())
        height[m] = np.nan
        deck_z[m] = np.nan
        n_pts[m] = 0
    if rejected:
        log.info("deck height: %d measurements rejected as implausible for their class (bridge elevation points "
                 "belonging to a crossing road structure)", rejected)
    source = np.where(np.isfinite(height), DECK_SOURCE_MEASURED, DECK_SOURCE_CLASS_MEDIAN).astype(np.int8)
    source[~np.isin(cls, np.asarray(DECK_CLASSES, dtype=object))] = DECK_SOURCE_NOT_APPLICABLE
    # class fallback: the median of the heights actually measured for the same structure class
    for c in DECK_CLASSES:
        m = (cls == c)
        measured = m & np.isfinite(height)
        if not m.any():
            continue
        if measured.any():
            med = float(np.median(height[measured]))
            height[m & ~np.isfinite(height)] = med
            log.info("deck height %-10s: %d measured (median %.2f m), %d filled from the class median",
                     c, int(measured.sum()), med, int((m & (source == DECK_SOURCE_CLASS_MEDIAN)).sum()))
        else:
            log.warning("deck height %-10s: no bridge elevation point within %.0f m of any of the %d structures — "
                        "height left NaN", c, DECK_SEARCH_M, int(m.sum()))
    na = source == DECK_SOURCE_NOT_APPLICABLE
    height[na] = np.nan
    deck_z[na] = np.nan
    log.info("deck height: %d structures are open cut (track below grade) — deck height not applicable", int(na.sum()))
    return deck_z, ground_z, height, source, n_pts


def attach_osm(lines: np.ndarray, osm: dict) -> tuple[list[str], list[str], list[str], np.ndarray]:
    """Nearest OSM rail way within ``OSM_MATCH_M`` -> (railway mode, name, operator, osm_id)."""
    tree = shapely.STRtree(osm["geometry"])
    railway, name, operator = [], [], []
    osm_id = np.zeros(len(lines), dtype=np.int64)
    nearest = tree.query_nearest(lines, max_distance=OSM_MATCH_M, all_matches=False)
    match = {int(a): int(b) for a, b in zip(nearest[0], nearest[1])} if nearest.size else {}
    for i in range(len(lines)):
        j = match.get(i, -1)
        railway.append(osm["railway"][j] if j >= 0 else "")
        name.append(osm["name"][j] if j >= 0 else "")
        operator.append(osm["operator"][j] if j >= 0 else "")
        osm_id[i] = osm["osm_id"][j] if j >= 0 else 0
    log.info("osm attach: %d of %d planimetric structures matched an OSM rail way within %.0f m",
             len(match), len(lines), OSM_MATCH_M)
    return railway, name, operator, osm_id


def osm_only_structures(osm: dict, planimetric: np.ndarray) -> np.ndarray:
    """Indices of OSM bridge/embankment/cutting rail ways with no planimetric structure nearby."""
    flag = osm["is_elevated"] | osm["embankment"] | osm["cutting"]
    cand = np.flatnonzero(flag)
    if cand.size == 0 or len(planimetric) == 0:
        return cand
    tree = shapely.STRtree(planimetric)
    near = tree.query(osm["geometry"][cand], predicate="dwithin", distance=OSM_EXTRA_M)
    covered = set(int(v) for v in near[0]) if near.size else set()
    extra = np.array([c for k, c in enumerate(cand) if k not in covered], dtype=np.int64)
    log.info("osm-only structures: %d of %d OSM bridge/embankment/cutting ways are not covered by the "
             "planimetric layer", len(extra), len(cand))
    return extra


def build(ground: GroundModel, rail_line_path: Path = RAIL_LINE, osm_path: Path = OSM_RAIL,
          elevation_path: Path | None = None) -> pa.Table:
    """Assemble ``transit/rail_structures.parquet``."""
    parts, cls, name = load_planimetric_rail(rail_line_path)
    keep = np.isin(cls, np.asarray(STRUCTURE_CLASSES, dtype=object))
    lines = parts[keep]
    cls_k = cls[keep]
    name_k = name[keep]
    log.info("planimetric structures kept: %s", {c: int((cls_k == c).sum()) for c in STRUCTURE_CLASSES})

    osm = load_osm_rail(osm_path)
    railway, osm_name, operator, osm_id = attach_osm(lines, osm)
    extra = osm_only_structures(osm, lines)

    all_lines = list(lines) + [osm["geometry"][i] for i in extra]
    all_cls = list(cls_k) + [("elevated" if osm["is_elevated"][i] else "embankment" if osm["embankment"][i] else "open_cut")
                             for i in extra]
    all_source = ["planimetric"] * len(lines) + ["osm"] * len(extra)
    all_railway = railway + [osm["railway"][i] for i in extra]
    all_name = [n or o for n, o in zip(name_k, osm_name)] + [osm["name"][i] for i in extra]
    all_operator = operator + [osm["operator"][i] for i in extra]
    all_osm_id = list(osm_id) + [int(osm["osm_id"][i]) for i in extra]

    bridge_pts = load_elevation_points(elevation_path or (RAW / "nyc_opendata" / "plan_elevation_points.geojson"),
                                       sub_codes=(SUB_BRIDGE,))
    lines_arr = np.asarray(all_lines, dtype=object)
    cls_arr = np.asarray(all_cls, dtype=object)
    deck_z, ground_z, height, hsource, n_pts = deck_heights(lines_arr, cls_arr, ground, bridge_pts)
    length = shapely.length(lines_arr).astype(np.float32)

    order = np.lexsort((np.arange(len(lines_arr)), cls_arr.astype(str)))
    table = pa.table({
        "structure_id": pa.array(np.arange(len(lines_arr), dtype=np.int64)[order]),
        "kind": pa.array([str(cls_arr[i]) for i in order]),
        "source": pa.array([all_source[i] for i in order]),
        "geometry": pa.array([shapely.to_wkb(lines_arr[i]) for i in order], type=pa.binary()),
        "name": pa.array([all_name[i] for i in order]),
        "railway": pa.array([all_railway[i] for i in order]),
        "operator": pa.array([all_operator[i] for i in order]),
        "osm_id": pa.array(np.asarray(all_osm_id, dtype=np.int64)[order]),
        "length_m": pa.array(length[order]),
        "deck_z": pa.array(deck_z[order].astype(np.float32)),
        "ground_z": pa.array(ground_z[order].astype(np.float32)),
        "deck_height_m": pa.array(height[order].astype(np.float32)),
        "deck_height_source": pa.array(hsource[order]),
        "deck_points": pa.array(n_pts[order]),
    })
    return table
