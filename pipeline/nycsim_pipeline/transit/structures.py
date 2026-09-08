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
    # Carry the fallback through to the absolute elevation. The loop above fills ``height`` from the
    # class median and stopped there, so 1,441 of the 3,986 elevated and viaduct structures -- 36 %
    # of them, and every one of the 1,308 that come from OSM rather than the planimetric survey --
    # had a deck height, a ground elevation, and no deck elevation at all. A consumer reading
    # ``deck_z`` lost every one of them, silently, because NaN is a number.
    fill = ~np.isfinite(deck_z) & np.isfinite(ground_z) & np.isfinite(height)
    deck_z[fill] = ground_z[fill] + height[fill]
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


# --------------------------------------------------------------------------------------- deck width
# The survey captures **one centreline per track**, so how wide a structure is, is measurable: the
# tracks that run parallel to each other within a corridor are the tracks the same deck carries, and
# the deck is as wide as they are apart plus the overhang either side. Measured over the whole
# elevated and viaduct network the lateral spread between outermost parallel centrelines has a
# median of 7.78 m over two to four distinct track offsets -- a three-track El at about 3.9 m track
# spacing -- which is what the Astoria, Jerome Avenue and Flushing lines are.
#
# The alternative was a constant, and a constant would have made the two-track Myrtle Avenue El and
# the four-track Broadway El the same width.

#: Half-width of the deck beyond the outermost track centre, metres. The steel El deck carries a
#: walkway and a railing outboard of the running rails; on the standard NYC Rapid Transit elevated
#: bent the deck stringers reach about 1.7 m past the outer track centre.
DECK_OVERHANG_M = 1.7

#: How far along its own direction a neighbouring track has to stay to count as running with this
#: one, and how far to the side it may be, in metres. 20 m sideways covers a four-track structure
#: (three 3.9 m gaps plus slack); beyond that is a different structure on the other side of a street.
DECK_NEIGHBOUR_LON_M = 6.0
DECK_NEIGHBOUR_LAT_M = 20.0

#: Direction agreement required of a neighbouring track: |cos| >= this, i.e. within about 10 degrees.
DECK_PARALLEL_COS = 0.985

#: Spacing of the points each centreline is sampled at when looking for its neighbours, in metres.
DECK_SAMPLE_M = 10.0

DECK_WIDTH_MEASURED = 0        # from parallel track centrelines
DECK_WIDTH_SINGLE_TRACK = 1    # no parallel neighbour found: one track, deck = gauge + overhangs

#: Deck width of a structure carrying a single track: the 1,435 mm standard gauge plus the overhang
#: either side, rounded to the centimetre.
SINGLE_TRACK_WIDTH_M = round(1.435 + 2 * DECK_OVERHANG_M, 2)


def deck_widths(lines: np.ndarray, cls: np.ndarray,
                classes: tuple[str, ...] = ("elevated", "viaduct")) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(width_m, tracks, source)`` per structure, from how its parallel neighbours are spread.

    Each line of the named classes is sampled every :data:`DECK_SAMPLE_M`; at every sample the other
    samples that run parallel through the same place are collected and their perpendicular offsets
    measured. A structure's width is the **median** over its own samples, so one crossing that
    happens to run parallel for a few metres cannot widen a whole line. Classes not named keep NaN:
    an embankment and an open cut are earthworks whose width the terrain already carries.
    """
    n = len(lines)
    width = np.full(n, np.nan, dtype=np.float64)
    tracks = np.zeros(n, dtype=np.int16)
    source = np.full(n, DECK_WIDTH_SINGLE_TRACK, dtype=np.int8)
    sel = np.nonzero(np.isin(cls.astype(str), np.asarray(classes)))[0]
    if not len(sel):
        return width, tracks, source

    pts, dirs, owner = [], [], []
    for j in sel:
        g = lines[j]
        length = g.length
        if length < 1e-3:
            continue
        steps = max(2, int(length // DECK_SAMPLE_M) + 1)
        for k in range(steps):
            s = length * k / (steps - 1)
            a = g.interpolate(s)
            b = g.interpolate(min(length, s + 1.0))
            v = np.array([b.x - a.x, b.y - a.y])
            nn = float(np.hypot(*v))
            if nn < 1e-9:
                continue
            pts.append((a.x, a.y))
            dirs.append(v / nn)
            owner.append(j)
    if not pts:
        return width, tracks, source
    P = np.asarray(pts)
    D = np.asarray(dirs)
    owner = np.asarray(owner)
    tree = cKDTree(P)

    per_line: dict[int, list[tuple[float, int]]] = {}
    radius = float(np.hypot(DECK_NEIGHBOUR_LON_M, DECK_NEIGHBOUR_LAT_M))
    for i in range(len(P)):
        p, d = P[i], D[i]
        nb = tree.query_ball_point(p, radius)
        if not nb:
            continue
        nb = np.asarray(nb)
        q = P[nb] - p
        lon = q @ d
        lat = q @ np.array([-d[1], d[0]])
        keep = ((np.abs(D[nb] @ d) >= DECK_PARALLEL_COS)
                & (np.abs(lon) <= DECK_NEIGHBOUR_LON_M) & (np.abs(lat) <= DECK_NEIGHBOUR_LAT_M))
        if not keep.any():
            continue
        l = lat[keep]
        spread = float(l.max() - l.min())
        # distinct track offsets, at half the minimum NYC track spacing so two tracks never merge
        n_tracks = int(len(np.unique(np.round(l / 1.5))))
        per_line.setdefault(int(owner[i]), []).append((spread, n_tracks))

    for j in sel:
        obs = per_line.get(int(j))
        if not obs:
            width[j] = SINGLE_TRACK_WIDTH_M
            tracks[j] = 1
            source[j] = DECK_WIDTH_SINGLE_TRACK
            continue
        sp = np.asarray([o[0] for o in obs])
        tk = np.asarray([o[1] for o in obs])
        spread = float(np.median(sp))
        width[j] = max(SINGLE_TRACK_WIDTH_M, spread + 2 * DECK_OVERHANG_M)
        tracks[j] = int(np.median(tk))
        source[j] = DECK_WIDTH_MEASURED if spread > 0.5 else DECK_WIDTH_SINGLE_TRACK
    return width, tracks, source


# ------------------------------------------------------------------------------------ deck profile
# A deck elevation per structure is not a deck. Measured at shared endpoints across the elevated and
# viaduct network, **31.5 %** of the joints between two structures that meet end to end disagree by
# more than a metre about how high the deck is there, 20 % by more than two and 7 % by more than
# five: a railway built from those numbers as a constant per segment would be a staircase.
#
# The disagreement is honest -- one segment has a surveyed bridge elevation point beside it and its
# neighbour falls back to the class median -- so the fix is not to distrust the measurements but to
# make them agree at the joints. Every endpoint that two structures share gets one elevation, the
# weighted mean of what the structures meeting there say (a measured deck counts for
# :data:`PROFILE_MEASURED_WEIGHT` times a class-median one), and each structure's deck then ramps
# between its own two endpoints. Discontinuity becomes zero by construction rather than by tolerance.
#
# A few passes of grade limiting follow: rail cannot climb faster than about 4 % (the steepest
# revenue grade in the subway is the 4.5 % out of the 148th Street yard lead), and a joint whose two
# ends imply more than that is being pulled by one bad measurement.

#: How much more a deck elevation measured from a bridge elevation point counts than one taken from
#: the class median, when several structures meeting at a joint disagree.
PROFILE_MEASURED_WEIGHT = 4.0

#: Steepest deck grade allowed before the smoothing pulls the joint back, as a fraction.
PROFILE_MAX_GRADE = 0.04

#: Passes of grade limiting. Each pass moves the two ends of an over-steep structure a third of the
#: way towards each other. A joint held by three or four neighbours pulls back on each pass, so the
#: stubborn ones need many: measured over the whole network, 12 passes leave 62 structures above the
#: grade limit and one at 36 %, 120 leave 4, and 400 leave **none** -- the maximum grade in the
#: network is then exactly the limit. The cost of the extra passes is confined to those joints: the
#: median structure does not move at all and the 95th percentile move is 1.48 m either way.
PROFILE_PASSES = 400

#: Endpoints closer together than this are the same joint, in metres. The planimetric linework is
#: captured to the centimetre, so this only has to absorb the WKB round trip.
PROFILE_SNAP_M = 0.05


def deck_profile(lines: np.ndarray, cls: np.ndarray, deck_z: np.ndarray, hsource: np.ndarray,
                 classes: tuple[str, ...] = ("elevated", "viaduct")
                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(z_start, z_end, joints)`` -- one deck elevation per endpoint, shared where lines meet.

    ``joints`` is the number of structures that met at each row's busiest endpoint, so a caller can
    tell a genuine junction from a line that ends in mid air.
    """
    n = len(lines)
    z0 = np.full(n, np.nan)
    z1 = np.full(n, np.nan)
    joints = np.zeros(n, dtype=np.int16)
    sel = np.nonzero(np.isin(cls.astype(str), np.asarray(classes)) & np.isfinite(deck_z))[0]
    if not len(sel):
        return z0, z1, joints

    def key(p) -> tuple[int, int]:
        return (int(round(p[0] / PROFILE_SNAP_M)), int(round(p[1] / PROFILE_SNAP_M)))

    ends: dict[tuple[int, int], list[tuple[int, int]]] = {}
    coords: dict[int, np.ndarray] = {}
    length: dict[int, float] = {}
    for j in sel:
        c = np.asarray(lines[j].coords)[:, :2]
        coords[int(j)] = c
        length[int(j)] = float(lines[j].length)
        ends.setdefault(key(c[0]), []).append((int(j), 0))
        ends.setdefault(key(c[-1]), []).append((int(j), 1))

    node_z: dict[tuple[int, int], float] = {}
    for k, members in ends.items():
        num = den = 0.0
        for j, _ in members:
            w = PROFILE_MEASURED_WEIGHT if hsource[j] == DECK_SOURCE_MEASURED else 1.0
            num += w * float(deck_z[j])
            den += w
        node_z[k] = num / den if den else float("nan")

    node_of = {int(j): (key(coords[int(j)][0]), key(coords[int(j)][-1])) for j in sel}
    degree = {k: len(v) for k, v in ends.items()}
    for _ in range(PROFILE_PASSES):
        moved = False
        delta: dict[tuple[int, int], list[float]] = {}
        for j in sel:
            a, b = node_of[int(j)]
            L = max(length[int(j)], 1.0)
            gap = node_z[b] - node_z[a]
            allowed = PROFILE_MAX_GRADE * L
            if abs(gap) <= allowed:
                continue
            excess = (abs(gap) - allowed) * np.sign(gap) / 3.0
            delta.setdefault(a, []).append(+excess)
            delta.setdefault(b, []).append(-excess)
            moved = True
        for k, ds in delta.items():
            node_z[k] += float(np.mean(ds))
        if not moved:
            break

    for j in sel:
        a, b = node_of[int(j)]
        z0[j] = node_z[a]
        z1[j] = node_z[b]
        joints[j] = max(degree[a], degree[b])
    return z0, z1, joints


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
    width, tracks, wsource = deck_widths(lines_arr, cls_arr)
    z_start, z_end, joints = deck_profile(lines_arr, cls_arr, deck_z, hsource)
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
        "deck_width_m": pa.array(width[order].astype(np.float32)),
        "track_count": pa.array(tracks[order]),
        "deck_width_source": pa.array(wsource[order]),
        "deck_z_start": pa.array(z_start[order].astype(np.float32)),
        "deck_z_end": pa.array(z_end[order].astype(np.float32)),
        "deck_joints": pa.array(joints[order]),
    })
    return table
