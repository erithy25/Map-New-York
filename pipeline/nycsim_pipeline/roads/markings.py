"""``roads/markings/{tile}.parquet`` (DATA_CONTRACTS §7.1): the paint on the carriageway.

Until this stage the city had **no road marking of any kind** -- no centre line, no lane line, no
stop bar, no bike-lane line, and crosswalks painted as one solid rectangle across the whole
carriageway rather than as the bars a New York crossing is made of (J52).  At eye level a street
was a flat grey plane between two kerbs, and a driver had no lane to follow and no line to stop at
over a simulation that is driving 381,971 lanes.

**Nothing here is drawn where a line looks right.**  Every position comes from the measured lane
cross-section: ``lanes.parquet`` carries each lane's signed ``offset_m`` from its segment's
centreline, its ``width_m``, its ``direction`` and its ``kind``, and the boundary between two lanes
is the line where one lane's edge meets the next one's.  Which boundary carries which marking is
the MUTCD's own rule, not a choice:

* two travel lanes running in **opposite** directions -> the centre line, double solid yellow
  (MUTCD 2009 §3B.02: "a double yellow line ... where crossing the centre line is prohibited");
* two travel lanes running in the **same** direction -> a broken white lane line (§3B.04);
* a travel lane against a **bike** lane -> a solid white line (§3B.04, §9C.04);
* a travel lane against a **two-way left-turn** lane -> a solid yellow line outside and a broken
  yellow line inside it (§3B.01), which is what marks a centre turn lane and nothing else does;
* a travel lane against a **parking** lane -> nothing.  New York does not paint that edge, and a
  line invented there would be the single most visible falsehood this module could tell.

The **widths and patterns** are the standard's, and where the standard gives a range the value
chosen inside it is stated here rather than presented as a measurement:

============================  ==================  ==========================================
quantity                      value               source
============================  ==================  ==========================================
line width                    0.102 m (4 in)      MUTCD §3A.06: "4 to 6 inches"; 4 in chosen
double-line separation        0.102 m (4 in)      MUTCD §3A.06: "approximately 4 inches"
broken line: paint / gap      3.048 / 9.144 m     MUTCD §3A.06: a 10 ft line and a 30 ft gap
stop line width               0.305 m (12 in)     MUTCD §3B.16: "12 to 24 inches"; 12 in chosen
stop line set back from the   1.219 m (4 ft)      MUTCD §3B.16: "no less than 4 ft" from the
crosswalk                                         crosswalk
crosswalk bar width           0.305 m (12 in)     MUTCD §3B.18: "12 to 24 inches"
crosswalk bar pitch           0.610 m (24 in)     §3B.18 allows a 12-60 in gap; a 12 in gap is
                                                  chosen, which is the pattern New York's
                                                  high-visibility crossings read as
============================  ==================  ==========================================

The crosswalk **bars are cut out of the crosswalk polygons that already exist** in
``roads/pavement/{tile}.parquet`` rather than derived a second time from the intersection geometry,
so the paint can never drift from the crossing it belongs to; the same is true of the stop line,
which is placed by the crosswalk rule in :mod:`pavement` -- imported from there, not restated.
The crossing area itself stops being painted at the same time: it is asphalt with bars on it.

A marking is a *polygon*, like every other paved surface in this project, so it drapes over the
terrain and takes a physical material like the rest.  Markings are lifted 15 mm above the roadbed
by the consumer, which is what a thermoplastic marking actually stands.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapely

from ..crs import NYC_TM
from . import schema as S
from .geom import offset_vectors
from .pavement import CROSSWALK_DEPTH_M, CROSSWALK_SETBACK_M, clip_to_tiles

log = logging.getLogger("nycsim.roads.markings")

#: ``kind`` in the markings table.
(MARK_LANE_LINE, MARK_CENTRE_LINE, MARK_BIKE_LANE_LINE,
 MARK_STOP_BAR, MARK_CROSSWALK_BAR, MARK_TWLTL_LINE) = range(6)

MARK_NAMES = {MARK_LANE_LINE: "lane_line", MARK_CENTRE_LINE: "centre_line",
              MARK_BIKE_LANE_LINE: "bike_lane_line", MARK_STOP_BAR: "stop_bar",
              MARK_CROSSWALK_BAR: "crosswalk_bar", MARK_TWLTL_LINE: "two_way_left_turn_line"}

#: ``colour``.  Yellow separates opposing directions; everything else is white (MUTCD §3A.05).
MARK_WHITE, MARK_YELLOW = 0, 1

LINE_W_M = 0.102              # 4 in
DOUBLE_GAP_M = 0.102          # 4 in between the two lines of a double centre line
DASH_PAINT_M = 3.048          # 10 ft
DASH_GAP_M = 9.144            # 30 ft
STOP_BAR_W_M = 0.305          # 12 in
STOP_BAR_SETBACK_M = 1.219    # 4 ft clear of the crosswalk
CROSSWALK_BAR_W_M = 0.305     # 12 in
CROSSWALK_BAR_PITCH_M = 0.610 # 12 in bar + 12 in gap

#: Below this the segment is too short to carry a marking that reads as one.
MIN_RUN_M = 2.0
#: A boundary this far off a straight line has been mitred past usefulness; drop it rather than
#: paint a spike.  (``offset_vectors`` already limits the mitre; this catches what survives.)
MAX_OFFSET_M = 30.0


def _dashes(coords: np.ndarray, paint_m: float, gap_m: float) -> list[np.ndarray]:
    """Split a polyline into painted runs of ``paint_m`` separated by ``gap_m``.

    The pattern starts half a gap in, so a boundary that ends at an intersection does not finish
    with a stub of paint hard against the crossing.
    """
    d = np.hypot(np.diff(coords[:, 0]), np.diff(coords[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(d)])
    total = float(s[-1])
    if total < paint_m:
        return []
    period = paint_m + gap_m
    out: list[np.ndarray] = []
    start = gap_m / 2.0
    while start + paint_m <= total:
        out.append(_slice(coords, s, start, start + paint_m))
        start += period
    return [c for c in out if len(c) >= 2]


def _slice(coords: np.ndarray, s: np.ndarray, a: float, b: float) -> np.ndarray:
    """The part of the polyline between arc lengths ``a`` and ``b``, with its ends interpolated."""
    pts = [_point_at(coords, s, a)]
    inner = np.flatnonzero((s > a) & (s < b))
    if inner.size:
        pts.extend(coords[i, :2] for i in inner)
    pts.append(_point_at(coords, s, b))
    return np.asarray(pts, dtype=np.float64)


def _point_at(coords: np.ndarray, s: np.ndarray, t: float) -> np.ndarray:
    i = int(np.clip(np.searchsorted(s, t) - 1, 0, len(s) - 2))
    span = s[i + 1] - s[i]
    f = 0.0 if span <= 0 else (t - s[i]) / span
    return coords[i, :2] + f * (coords[i + 1, :2] - coords[i, :2])


def _stripe(coords: np.ndarray, width_m: float):
    """A polyline thickened into a polygon, flat-ended and mitred like the curb faces."""
    if len(coords) < 2:
        return None
    line = shapely.LineString(coords[:, :2])
    if line.length < 1e-3:
        return None
    poly = shapely.buffer(line, width_m / 2.0, quad_segs=1, cap_style="flat", join_style="mitre")
    poly = shapely.make_valid(poly)
    return poly if not shapely.is_empty(poly) else None


@dataclass(frozen=True)
class Boundary:
    """One line to paint on a segment: where it sits and what kind of line it is.

    ``toward`` is +1 when the lane on the *increasing offset* side is the one the marking's
    asymmetric half faces -- the two-way left-turn line is the only kind that has one, and its
    broken half goes on the turn lane's side (MUTCD 2009 §3B.01).
    """

    offset_m: float
    kind: int
    colour: int
    toward: int = 0


def boundaries(lanes: pd.DataFrame) -> list[Boundary]:
    """The lines to paint across one segment's cross-section.

    The lanes arrive in any order and are sorted by offset here, so the pairs are the real
    neighbours across the section rather than the order the table happened to hold them in.
    """
    if len(lanes) < 2:
        return []
    rows = lanes.sort_values("offset_m")
    off = rows["offset_m"].to_numpy(dtype=np.float64)
    wid = rows["width_m"].to_numpy(dtype=np.float64)
    kind = rows["kind"].to_numpy(dtype=np.int64)
    direction = rows["direction"].to_numpy(dtype=np.int64)
    out: list[Boundary] = []
    for i in range(len(rows) - 1):
        a_edge = off[i] + wid[i] / 2.0
        b_edge = off[i + 1] - wid[i + 1] / 2.0
        boundary = (a_edge + b_edge) / 2.0
        if abs(boundary) > MAX_OFFSET_M:
            continue
        ka, kb = int(kind[i]), int(kind[i + 1])
        pair = {ka, kb}
        if ka == S.LANE_TRAVEL and kb == S.LANE_TRAVEL:
            if direction[i] != direction[i + 1]:
                out.append(Boundary(boundary, MARK_CENTRE_LINE, MARK_YELLOW))
            else:
                out.append(Boundary(boundary, MARK_LANE_LINE, MARK_WHITE))
        elif pair == {S.LANE_BIKE, S.LANE_TRAVEL}:
            out.append(Boundary(boundary, MARK_BIKE_LANE_LINE, MARK_WHITE))
        elif pair == {S.LANE_TURN, S.LANE_TRAVEL}:
            out.append(Boundary(boundary, MARK_TWLTL_LINE, MARK_YELLOW,
                                toward=1 if kb == S.LANE_TURN else -1))
        # travel against parking: New York paints nothing there, and neither does this.
    return out


def _at(coords: np.ndarray, vecs: np.ndarray, d: float) -> np.ndarray:
    line = coords.copy()
    line[:, :2] = coords[:, :2] + d * vecs
    return line


def _solid(coords: np.ndarray, vecs: np.ndarray, d: float) -> list:
    p = _stripe(_at(coords, vecs, d), LINE_W_M)
    return [p] if p is not None else []


def _broken(coords: np.ndarray, vecs: np.ndarray, d: float) -> list:
    return [p for p in (_stripe(c, LINE_W_M)
                        for c in _dashes(_at(coords, vecs, d), DASH_PAINT_M, DASH_GAP_M))
            if p is not None]


#: Half the distance between the two lines of a double marking, centre to centre.
_DOUBLE_HALF_M = (DOUBLE_GAP_M + LINE_W_M) / 2.0


def marking_polys(coords: np.ndarray, vecs: np.ndarray, b: Boundary) -> list:
    """The polygons one :class:`Boundary` paints on one segment."""
    if b.kind == MARK_CENTRE_LINE:
        # double solid yellow (MUTCD 3B.02)
        return (_solid(coords, vecs, b.offset_m - _DOUBLE_HALF_M)
                + _solid(coords, vecs, b.offset_m + _DOUBLE_HALF_M))
    if b.kind == MARK_TWLTL_LINE:
        # solid outside, broken on the turn lane's side (MUTCD 3B.01)
        return (_solid(coords, vecs, b.offset_m - b.toward * _DOUBLE_HALF_M)
                + _broken(coords, vecs, b.offset_m + b.toward * _DOUBLE_HALF_M))
    if b.kind == MARK_LANE_LINE:
        return _broken(coords, vecs, b.offset_m)
    return _solid(coords, vecs, b.offset_m)


def lane_markings(segments: gpd.GeoDataFrame, lanes: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """Every centre line, lane line and bike-lane line in the city."""
    by_segment: dict[int, pd.DataFrame] = dict(tuple(lanes.groupby("segment_id")))
    geoms: list = []
    kinds: list[int] = []
    colours: list[int] = []
    src: list[str] = []
    counts = {k: 0 for k in MARK_NAMES}
    seg_geom = segments.geometry.to_numpy()
    seg_id = segments["segment_id"].to_numpy()
    for i, sid in enumerate(seg_id):
        rows = by_segment.get(int(sid))
        if rows is None or len(rows) < 2:
            continue
        coords = shapely.get_coordinates(seg_geom[i])
        if len(coords) < 2:
            continue
        coords = np.asarray(coords, dtype=np.float64)
        if float(np.hypot(*np.diff(coords[:, :2], axis=0).T).sum()) < MIN_RUN_M:
            continue
        vecs = offset_vectors(coords)
        for b in boundaries(rows):
            polys = marking_polys(coords, vecs, b)
            for p in polys:
                geoms.append(p)
                kinds.append(b.kind)
                colours.append(b.colour)
                src.append(f"mk:{int(sid)}:{b.offset_m:+.2f}")
            counts[b.kind] += len(polys)
    return (np.asarray(geoms, dtype=object),
            {"kinds": np.asarray(kinds, dtype=np.int8), "colours": np.asarray(colours, dtype=np.int8),
             "src_id": np.asarray(src, dtype=object), "counts": counts})


def _rectangle_axes(poly) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None:
    """``(centre, long axis, short axis, long half-length, short half-length)`` of a rectangle."""
    rect = shapely.oriented_envelope(poly)
    ring = shapely.get_coordinates(rect)
    if len(ring) < 5:
        return None
    a, b, c = ring[0], ring[1], ring[2]
    e1, e2 = b - a, c - b
    l1, l2 = float(np.hypot(*e1)), float(np.hypot(*e2))
    if min(l1, l2) < 1e-6:
        return None
    if l1 >= l2:
        long_v, short_v, ll, sl = e1 / l1, e2 / l2, l1, l2
    else:
        long_v, short_v, ll, sl = e2 / l2, e1 / l1, l2, l1
    centre = ring[:4].mean(axis=0)
    return centre, long_v, short_v, ll / 2.0, sl / 2.0


def crosswalk_bars(crosswalks: np.ndarray, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Continental bars cut out of each crosswalk rectangle.

    The bars run **along** the direction of traffic, which for these rectangles is the short axis:
    :func:`pavement._crosswalks` builds each one ``CROSSWALK_DEPTH_M`` deep along the approach and
    as wide as the leg.  The pattern is centred on the crossing, so both kerbs get the same
    treatment and the crossing reads symmetrically.
    """
    polys: list = []
    out_ids: list[str] = []
    for poly, ident in zip(crosswalks, ids):
        axes = _rectangle_axes(poly)
        if axes is None:
            continue
        centre, long_v, short_v, half_long, half_short = axes
        n = int((2.0 * half_long + CROSSWALK_BAR_PITCH_M - CROSSWALK_BAR_W_M) // CROSSWALK_BAR_PITCH_M)
        if n < 2:
            continue
        span = (n - 1) * CROSSWALK_BAR_PITCH_M
        for i in range(n):
            t = -span / 2.0 + i * CROSSWALK_BAR_PITCH_M
            mid = centre + t * long_v
            hw = CROSSWALK_BAR_W_M / 2.0
            ring = [mid + hw * long_v + half_short * short_v,
                    mid - hw * long_v + half_short * short_v,
                    mid - hw * long_v - half_short * short_v,
                    mid + hw * long_v - half_short * short_v]
            bar = shapely.intersection(shapely.Polygon(ring), poly)
            bar = shapely.make_valid(bar)
            if shapely.is_empty(bar) or shapely.area(bar) < 1e-3:
                continue
            polys.append(bar)
            out_ids.append(f"{ident}:b{i}")
    return np.asarray(polys, dtype=object), np.asarray(out_ids, dtype=object)


def stop_bars(segments: gpd.GeoDataFrame, lanes: pd.DataFrame,
              nodes: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """A stop line across the approaching travel lanes at every controlled intersection.

    The set-back is the crosswalk's own rule, imported from :mod:`pavement` rather than restated:
    the crossing's far edge stands ``widest leg / 2 + CROSSWALK_SETBACK_M + CROSSWALK_DEPTH_M`` from
    the node, and the stop line stands ``STOP_BAR_SETBACK_M`` clear of that.  A node with no
    control or fewer than three drivable legs gets none, which is the same test the crosswalks use.
    """
    ctrl = nodes.set_index("node_id")["control"]
    deg = nodes.set_index("node_id")["degree_drivable"]
    widest: dict[int, float] = {}
    for a, b, w, drivable in zip(segments["from_node"].to_numpy(), segments["to_node"].to_numpy(),
                                 segments["width_m"].to_numpy(), segments["drivable"].to_numpy()):
        if not bool(drivable):
            continue
        for node in (int(a), int(b)):
            widest[node] = max(widest.get(node, 0.0), float(w))

    travel = lanes[lanes["kind"] == S.LANE_TRAVEL]
    by_segment: dict[int, pd.DataFrame] = dict(tuple(travel.groupby("segment_id")))
    polys: list = []
    ids: list[str] = []
    for sid, from_node, to_node, geom in zip(segments["segment_id"].to_numpy(),
                                             segments["from_node"].to_numpy(),
                                             segments["to_node"].to_numpy(),
                                             segments.geometry.to_numpy()):
        rows = by_segment.get(int(sid))
        if rows is None or len(rows) == 0:
            continue
        coords = np.asarray(shapely.get_coordinates(geom), dtype=np.float64)
        if len(coords) < 2:
            continue
        d = np.hypot(np.diff(coords[:, 0]), np.diff(coords[:, 1]))
        s = np.concatenate([[0.0], np.cumsum(d)])
        total = float(s[-1])
        vecs = offset_vectors(coords)
        for node, at_end in ((int(to_node), True), (int(from_node), False)):
            if int(ctrl.get(node, S.CTRL_NONE)) == S.CTRL_NONE or int(deg.get(node, 0)) < 3:
                continue
            # a lane approaches ``to_node`` if it runs with the digitisation direction
            approaching = rows[rows["direction"] == (1 if at_end else -1)]
            if len(approaching) == 0:
                continue
            back = (widest.get(node, 0.0) / 2.0 + CROSSWALK_SETBACK_M + CROSSWALK_DEPTH_M
                    + STOP_BAR_SETBACK_M + STOP_BAR_W_M / 2.0)
            t = total - back if at_end else back
            if not (0.0 < t < total):
                continue
            centre = _point_at(coords, s, t)
            i = int(np.clip(np.searchsorted(s, t) - 1, 0, len(coords) - 2))
            right = vecs[min(i, len(vecs) - 1)]
            lo = float((approaching["offset_m"] - approaching["width_m"] / 2.0).min())
            hi = float((approaching["offset_m"] + approaching["width_m"] / 2.0).max())
            tangent = coords[i + 1, :2] - coords[i, :2]
            tangent = tangent / max(float(np.hypot(*tangent)), 1e-9)
            hd = STOP_BAR_W_M / 2.0
            ring = [centre + lo * right + hd * tangent, centre + hi * right + hd * tangent,
                    centre + hi * right - hd * tangent, centre + lo * right - hd * tangent]
            poly = shapely.make_valid(shapely.Polygon(ring))
            if shapely.is_empty(poly) or shapely.area(poly) < 1e-3:
                continue
            polys.append(poly)
            ids.append(f"sb:{node}:{int(sid)}")
    return np.asarray(polys, dtype=object), np.asarray(ids, dtype=object)


def _read_crosswalks(pavement_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Every crosswalk polygon the pavement stage wrote, with its source id."""
    polys: list = []
    ids: list[str] = []
    for path in sorted(pavement_dir.glob("t_*.parquet")):
        table = pq.read_table(path, columns=["kind", "geometry", "source_id"])
        kind = np.asarray(table.column("kind").to_pylist())
        if not len(kind):
            continue
        sel = kind == S.PAV_CROSSWALK
        if not sel.any():
            continue
        wkb = np.asarray(table.column("geometry").to_pylist(), dtype=object)[sel]
        sid = np.asarray(table.column("source_id").to_pylist(), dtype=object)[sel]
        polys.extend(shapely.from_wkb(list(wkb)))
        ids.extend(sid)
    return np.asarray(polys, dtype=object), np.asarray(ids, dtype=object)


def build(segments: gpd.GeoDataFrame, lanes: pd.DataFrame, nodes: pd.DataFrame,
          pavement_dir: Path, out_dir: Path) -> dict:
    """Write ``out_dir/{tile}.parquet`` for every tile that carries paint.  Returns stats."""
    t0 = time.time()
    stats: dict = {"sources": {}}
    geoms: list = []
    kinds: list = []
    colours: list = []
    src: list = []

    ts = time.time()
    g, at = lane_markings(segments, lanes)
    if len(g):
        geoms.append(g)
        kinds.append(at["kinds"])
        colours.append(at["colours"])
        src.append(at["src_id"])
    stats["sources"]["lane_markings"] = {
        "pieces": int(len(g)), "seconds": round(time.time() - ts, 1),
        "by_kind": {MARK_NAMES[k]: int(v) for k, v in at["counts"].items() if v}}
    log.info("lane markings: %d pieces (%.1fs)", len(g), time.time() - ts)

    ts = time.time()
    xw, xw_ids = _read_crosswalks(pavement_dir)
    bars, bar_ids = crosswalk_bars(xw, xw_ids)
    if len(bars):
        geoms.append(bars)
        kinds.append(np.full(len(bars), MARK_CROSSWALK_BAR, dtype=np.int8))
        colours.append(np.full(len(bars), MARK_WHITE, dtype=np.int8))
        src.append(bar_ids)
    stats["sources"]["crosswalk_bars"] = {"crosswalks": int(len(xw)), "pieces": int(len(bars)),
                                          "seconds": round(time.time() - ts, 1)}
    log.info("crosswalk bars: %d crossings -> %d bars (%.1fs)", len(xw), len(bars), time.time() - ts)

    ts = time.time()
    sb, sb_ids = stop_bars(segments, lanes, nodes)
    if len(sb):
        geoms.append(sb)
        kinds.append(np.full(len(sb), MARK_STOP_BAR, dtype=np.int8))
        colours.append(np.full(len(sb), MARK_WHITE, dtype=np.int8))
        src.append(sb_ids)
    stats["sources"]["stop_bars"] = {"pieces": int(len(sb)), "seconds": round(time.time() - ts, 1)}
    log.info("stop bars: %d (%.1fs)", len(sb), time.time() - ts)

    if not geoms:
        stats["seconds"] = round(time.time() - t0, 1)
        stats["tiles"] = 0
        return stats

    all_g = np.concatenate(geoms)
    all_kind = np.concatenate(kinds).astype(np.int8)
    all_colour = np.concatenate(colours).astype(np.int8)
    all_src = np.concatenate(src).astype(object)
    g, at, tx, ty = clip_to_tiles(all_g, {"kind": all_kind, "colour": all_colour, "src_id": all_src})

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("t_*.parquet"):
        old.unlink()
    area = shapely.area(g)
    written: dict[str, int] = {}
    by_kind: dict[int, int] = {}
    tiles = pd.DataFrame({"tile": [f"t_{int(a)}_{int(b)}" for a, b in zip(tx, ty)]})
    for tile, idx in tiles.groupby("tile").groups.items():
        idx = np.asarray(idx)
        gdf = gpd.GeoDataFrame({"kind": at["kind"][idx], "colour": at["colour"][idx],
                                "area_m2": area[idx].astype(np.float32),
                                "source_id": at["src_id"][idx]},
                               geometry=g[idx], crs=NYC_TM)
        written[tile] = S.write_geoparquet(gdf, out_dir / f"{tile}.parquet",
                                           S.SCHEMAS["markings"], {"nycsim.tile": tile})
        for k, c in zip(*np.unique(at["kind"][idx], return_counts=True)):
            by_kind[int(k)] = by_kind.get(int(k), 0) + int(c)

    stats["tiles"] = len(written)
    stats["pieces"] = int(len(g))
    stats["by_kind"] = {MARK_NAMES[k]: v for k, v in sorted(by_kind.items())}
    stats["painted_m2"] = round(float(area.sum()), 1)
    stats["seconds"] = round(time.time() - t0, 1)
    log.info("markings: %d pieces over %d tiles, %.0f m2 of paint (%.1fs)",
             len(g), len(written), area.sum(), stats["seconds"])
    return stats
