"""junction_lanes.parquet: lane-to-lane connectors through every node, with turn classification, NYC rules,
OSM turn restrictions, ramp rules and yield relations; also fills lanes.successors/predecessors.

Rules applied
* Only travel/turn lanes connect to travel/turn lanes; bike lanes connect to bike lanes; parking never connects.
* One-way and NV segments are respected automatically (a lane exists only for legal directions).
* Turn classification by heading change: |d| <= 30 straight, 30 < d <= 150 left (CCW), -150 <= d < -30 right,
  |d| > 150 U-turn. At degree-2 nodes the single continuation is always "straight".
* Left turns leave from the leftmost lane (or the centre-turn lane), right turns from the rightmost lane,
  straight lanes map proportionally; the target lanes fan out when the receiving street has more lanes.
* U-turns: never at signalised nodes (NYC Traffic Rules 4-07(b)), never on one-way streets, otherwise only
  where the node has >= 3 legs and the two-way street is at least as wide as the fleet's worst curb-to-curb
  turning circle (11.6 m, the real 2019 Ford Fusion figure from ADR-009), so a connector exists only where a
  car can physically complete the manoeuvre in one movement. A turnaround connector is added at real
  cul-de-sacs (degree-1 node, two-way street) so traffic can leave; they are counted separately.
* Ramps: at a node where a ramp meets a highway, street <-> highway connections are forbidden (traffic must use
  the ramp); ramp <-> highway merges use the outer lane on the ramp's side.
* OSM ``type=restriction`` relations (via node) are mapped onto (node, from_segment, to_segment) pairs by
  heading; no_* removes the pair, only_* removes every other pair from that approach.
* yield_to: left/U-turn yields to opposing straight/right movements; at unsignalised nodes a stop/yield-controlled
  or minor approach (fewer lanes / narrower street) yields to every movement of the major approaches.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from ..crs import NYC_TM
from . import schema as S
from .geom import PointSnapper, angle_diff, bezier_connector, end_heading

log = logging.getLogger("nycsim.roads.junctions")

STRAIGHT_DEG = 30.0
UTURN_DEG = 150.0
UTURN_MIN_WIDTH_M = 11.6   # 2019 Ford Fusion curb-to-curb turning circle (ADR-009): the fleet's U-turn width
RESTRICTION_SNAP_M = 15.0
RESTRICTION_HEADING_TOL = 35.0
CONNECTOR_POINTS = 6
STREET_RW = {S.RW_STREET, S.RW_ALLEY, S.RW_DRIVEWAY}


@dataclass
class Approach:
    segment_id: int
    node_id: int
    incoming: bool
    heading: float                  # math heading: incoming = direction of travel arriving; outgoing = leaving
    lanes: list[int]                # lane row indices, ordered left -> right in the travel frame
    kinds: list[int]
    pts: np.ndarray                 # (k, 3) lane end/start points aligned with lanes
    rw_type: int
    traffic_dir: int
    width: float
    name_norm: str
    lanes_total: int

    @property
    def travel_idx(self) -> list[int]:
        return [i for i, k in enumerate(self.kinds) if k in (S.LANE_TRAVEL, S.LANE_TURN)]

    @property
    def bike_idx(self) -> list[int]:
        return [i for i, k in enumerate(self.kinds) if k == S.LANE_BIKE]


def _classify(d: float) -> int:
    if abs(d) <= STRAIGHT_DEG:
        return S.TURN_STRAIGHT
    if abs(d) > UTURN_DEG:
        return S.TURN_UTURN
    return S.TURN_LEFT if d > 0 else S.TURN_RIGHT


def _map_restrictions(nodes: pd.DataFrame, approaches: dict[int, list[Approach]], osm_rest: pd.DataFrame, osm_ways: gpd.GeoDataFrame) -> tuple[set[tuple[int, int, int]], dict[tuple[int, int], set[int]], dict]:
    """Return (forbidden pairs {(node, from_seg, to_seg)}, only-allowed {(node, from_seg): {to_seg}}, stats)."""
    st = {"restrictions": int(len(osm_rest)), "via_node": 0, "node_snapped": 0, "mapped": 0, "conditional_skipped": 0, "via_way_skipped": 0}
    forbidden: set[tuple[int, int, int]] = set()
    only: dict[tuple[int, int], set[int]] = {}
    if len(osm_rest) == 0 or len(osm_ways) == 0:
        return forbidden, only, st
    inter_nodes = nodes[nodes["degree_drivable"] >= 3]
    snapper = PointSnapper(inter_nodes[["x", "y"]].to_numpy(), inter_nodes["node_id"].to_numpy())
    way_index = pd.Series(np.arange(len(osm_ways)), index=osm_ways["id"].to_numpy())
    way_nodes = osm_ways["node_ids"].to_numpy()
    way_coords = [shapely.get_coordinates(g) for g in osm_ways.geometry.values]

    def dir_point(way_id: int, via: int, before: bool) -> np.ndarray | None:
        if way_id not in way_index.index:
            return None
        wi = way_index.at[way_id]
        refs = np.asarray(way_nodes[wi])
        c = way_coords[wi]
        if len(refs) != len(c):
            return None
        pos = np.flatnonzero(refs == via)
        if len(pos) == 0:
            return None
        i = int(pos[0])
        if before:
            j = i - 1 if i > 0 else (1 if len(c) > 1 else None)
        else:
            j = i + 1 if i < len(c) - 1 else (i - 1 if i > 0 else None)
        return None if j is None else c[j]

    for r in osm_rest.itertuples(index=False):
        if r.n_via_ways > 0 and r.via_node < 0:
            st["via_way_skipped"] += 1
            continue
        if r.via_node < 0 or not np.isfinite(r.via_x):
            continue
        st["via_node"] += 1
        kind = str(r.restriction)
        if "@" in kind or r.conditional_only:
            st["conditional_skipped"] += 1
            continue
        ids, _ = snapper.snap(np.array([[r.via_x, r.via_y]]), RESTRICTION_SNAP_M)
        node = int(ids[0])
        if node < 0:
            continue
        st["node_snapped"] += 1
        pf = dir_point(int(r.from_way), int(r.via_node), before=True)
        pt = dir_point(int(r.to_way), int(r.via_node), before=False)
        if pf is None or pt is None:
            continue
        via = np.array([r.via_x, r.via_y])
        hf = np.degrees(np.arctan2(pf[1] - via[1], pf[0] - via[0])) % 360.0     # from via toward the from-way
        ht = np.degrees(np.arctan2(pt[1] - via[1], pt[0] - via[0])) % 360.0     # from via toward the to-way
        apps = approaches.get(node, [])
        best_from = best_to = None
        for a in apps:
            # heading of the leg pointing away from the node
            out_h = (a.heading + 180.0) % 360.0 if a.incoming else a.heading
            df = abs(angle_diff(out_h, hf)); dt = abs(angle_diff(out_h, ht))
            if a.incoming and df <= RESTRICTION_HEADING_TOL and (best_from is None or df < best_from[0]):
                best_from = (df, a.segment_id)
            if (not a.incoming) and dt <= RESTRICTION_HEADING_TOL and (best_to is None or dt < best_to[0]):
                best_to = (dt, a.segment_id)
        if best_from is None or best_to is None:
            continue
        st["mapped"] += 1
        if kind.startswith("no_"):
            forbidden.add((node, best_from[1], best_to[1]))
        elif kind.startswith("only_"):
            only.setdefault((node, best_from[1]), set()).add(best_to[1])
    return forbidden, only, st


def _build_approaches(seg: gpd.GeoDataFrame, lanes: gpd.GeoDataFrame) -> dict[int, list[Approach]]:
    """Every (segment end, direction) as an Approach; incoming and outgoing per node."""
    out: dict[int, list[Approach]] = {}
    coords = shapely.get_coordinates(seg.geometry.values)
    n_per = shapely.get_num_coordinates(seg.geometry.values)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    h_leave = np.zeros(len(seg)); h_arrive = np.zeros(len(seg))
    for i in range(len(seg)):
        c = coords[starts[i]: starts[i] + n_per[i]]
        if len(c) >= 2:
            h_leave[i] = end_heading(c, at_end=False)
            h_arrive[i] = end_heading(c, at_end=True)
    seg_pos = pd.Series(np.arange(len(seg)), index=seg["segment_id"].to_numpy())

    lc = shapely.get_coordinates(lanes.geometry.values, include_z=True)
    ln = shapely.get_num_coordinates(lanes.geometry.values)
    ls = np.concatenate([[0], np.cumsum(ln)[:-1]])
    first = lc[ls]; last = lc[ls + ln - 1]
    lane_seg = lanes["segment_id"].to_numpy(); lane_dir = lanes["direction"].to_numpy(); lane_kind = lanes["kind"].to_numpy(); lane_off = lanes["offset_m"].to_numpy()
    order = np.argsort(lane_seg, kind="stable")
    bounds = np.searchsorted(lane_seg[order], np.unique(lane_seg[order]))
    uniq = np.unique(lane_seg)
    bounds = np.append(bounds, len(order))
    fn = seg["from_node"].to_numpy(); tn = seg["to_node"].to_numpy(); rw = seg["rw_type"].to_numpy(); td = seg["traffic_dir"].to_numpy(); wd = seg["width_m"].to_numpy(); nm = seg["name_norm"].to_numpy(); tl = seg["travel_lanes"].to_numpy()
    for k in range(len(uniq)):
        sid = int(uniq[k])
        rows = order[bounds[k]: bounds[k + 1]]
        si = seg_pos.at[sid]
        for d in (1, -1):
            r = rows[lane_dir[rows] == d]
            r = r[np.isin(lane_kind[r], [S.LANE_TRAVEL, S.LANE_TURN, S.LANE_BIKE])]
            if len(r) == 0:
                continue
            # left -> right in the travel frame: +1 travel: ascending offset; -1: descending
            r = r[np.argsort(lane_off[r] * d)]
            if d == 1:
                # forward: leaves from_node, arrives at to_node
                out.setdefault(int(fn[si]), []).append(Approach(sid, int(fn[si]), False, h_leave[si], list(r), list(lane_kind[r]), first[r], int(rw[si]), int(td[si]), float(wd[si]), nm[si], int(tl[si])))
                out.setdefault(int(tn[si]), []).append(Approach(sid, int(tn[si]), True, h_arrive[si], list(r), list(lane_kind[r]), last[r], int(rw[si]), int(td[si]), float(wd[si]), nm[si], int(tl[si])))
            else:
                # backward: leaves to_node (heading = reverse of arrive), arrives at from_node (heading = reverse of leave)
                out.setdefault(int(tn[si]), []).append(Approach(sid, int(tn[si]), False, (h_arrive[si] + 180.0) % 360.0, list(r), list(lane_kind[r]), last[r], int(rw[si]), int(td[si]), float(wd[si]), nm[si], int(tl[si])))
                out.setdefault(int(fn[si]), []).append(Approach(sid, int(fn[si]), True, (h_leave[si] + 180.0) % 360.0, list(r), list(lane_kind[r]), first[r], int(rw[si]), int(td[si]), float(wd[si]), nm[si], int(tl[si])))
    return out


def _pair_lanes(a: Approach, b: Approach, turn: int, a_idx: list[int], b_idx: list[int], side_only: int = 0) -> list[tuple[int, int]]:
    """Lane index pairs (into a.lanes, b.lanes) for the movement. ``side_only`` (+1 right / -1 left) restricts
    the receiving lanes to the outer lane on that side (ramp merges)."""
    if not a_idx or not b_idx:
        return []
    if side_only:
        b_idx = [b_idx[-1]] if side_only > 0 else [b_idx[0]]
    if turn == S.TURN_STRAIGHT:
        n, m = len(a_idx), len(b_idx)
        if n == 1:
            return [(a_idx[0], j) for j in b_idx]
        if m == 1:
            return [(i, b_idx[0]) for i in a_idx]
        pairs = set()
        for k, i in enumerate(a_idx):
            j = int(round(k * (m - 1) / (n - 1)))
            pairs.add((i, b_idx[j]))
        # make sure every receiving lane is fed when the receiver is wider
        for k, j in enumerate(b_idx):
            i = int(round(k * (n - 1) / (m - 1)))
            pairs.add((a_idx[i], j))
        return sorted(pairs)
    if turn == S.TURN_LEFT or turn == S.TURN_UTURN:
        src = a_idx[0]
        return [(src, j) for j in b_idx[: max(1, min(2, len(b_idx)))]] if turn == S.TURN_LEFT else [(src, b_idx[0])]
    # right
    src = a_idx[-1]
    return [(src, j) for j in b_idx[-max(1, min(2, len(b_idx))):]]


def build(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, lanes: gpd.GeoDataFrame, node_groups: dict[int, dict[int, int]],
          stop_approaches: dict[int, set[int]], yield_approaches: dict[int, set[int]], osm_rest: pd.DataFrame, osm_ways: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict]:
    t0 = time.time()
    st: dict = {}
    approaches = _build_approaches(seg, lanes)
    forbidden, only, rst = _map_restrictions(nodes, approaches, osm_rest, osm_ways)
    st["osm_restrictions"] = rst
    control = pd.Series(nodes["control"].to_numpy(), index=nodes["node_id"].to_numpy())
    degree = pd.Series(nodes["degree_drivable"].to_numpy(), index=nodes["node_id"].to_numpy())
    lane_ids = lanes["lane_id"].to_numpy()

    jl_id: list[int] = []; jl_from: list[int] = []; jl_to: list[int] = []; jl_turn: list[int] = []; jl_group: list[int] = []
    jl_node: list[int] = []; jl_fseg: list[int] = []; jl_tseg: list[int] = []; jl_yield: list[list[int]] = []
    geoms: list[np.ndarray] = []
    succ: dict[int, list[int]] = {}
    pred: dict[int, list[int]] = {}
    next_id = 1
    n_uturn = n_culdesac = n_forbidden = n_only = n_ramp_block = 0
    turn_counts = {0: 0, 1: 0, 2: 0, 3: 0}

    for node, apps in approaches.items():
        inc = [a for a in apps if a.incoming]
        outg = [a for a in apps if not a.incoming]
        if not inc or not outg:
            continue
        ctrl = int(control.get(node, S.CTRL_NONE))
        deg = int(degree.get(node, len({a.segment_id for a in apps})))
        groups = node_groups.get(node, {})
        signalized = ctrl == S.CTRL_SIGNAL
        has_ramp = any(a.rw_type == S.RW_RAMP for a in apps)
        has_hw = any(a.rw_type == S.RW_HIGHWAY for a in apps)
        stops = stop_approaches.get(node, set()) | yield_approaches.get(node, set())
        # major street for priority at uncontrolled nodes
        max_lanes = max((a.lanes_total for a in inc), default=0)
        node_rows: list[tuple[int, int, int, int]] = []     # (row index, from approach idx, turn, to approach idx)
        for ai, a in enumerate(inc):
            a_travel = a.travel_idx
            a_bike = a.bike_idx
            allowed_only = only.get((node, a.segment_id))
            single_continuation = (deg == 2 and len(outg) <= 2)
            for bi, b in enumerate(outg):
                reverse = (b.segment_id == a.segment_id) and abs(angle_diff(a.heading, b.heading)) > UTURN_DEG
                d = angle_diff(a.heading, b.heading)
                turn = _classify(d)
                if reverse or (turn == S.TURN_UTURN and b.segment_id == a.segment_id):
                    turn = S.TURN_UTURN
                if turn == S.TURN_UTURN:
                    if deg <= 1 and a.traffic_dir == S.DIR_TWO_WAY:
                        n_culdesac += 1           # turnaround at a cul-de-sac
                    elif signalized or a.traffic_dir != S.DIR_TWO_WAY or a.width < UTURN_MIN_WIDTH_M or deg < 3 or b.segment_id != a.segment_id:
                        continue
                    else:
                        n_uturn += 1
                elif single_continuation and b.segment_id != a.segment_id:
                    turn = S.TURN_STRAIGHT
                if (node, a.segment_id, b.segment_id) in forbidden:
                    n_forbidden += 1
                    continue
                if allowed_only is not None and b.segment_id not in allowed_only and b.segment_id != a.segment_id:
                    n_only += 1
                    continue
                if has_ramp and has_hw:
                    if (a.rw_type in STREET_RW and b.rw_type == S.RW_HIGHWAY) or (a.rw_type == S.RW_HIGHWAY and b.rw_type in STREET_RW):
                        n_ramp_block += 1
                        continue
                side_only = 0
                if a.rw_type == S.RW_RAMP and b.rw_type == S.RW_HIGHWAY and turn == S.TURN_STRAIGHT:
                    # ramp merging: which side of the highway does the ramp come from?
                    side_only = 1 if d < 0 else -1 if d > 0 else 1
                pairs = _pair_lanes(a, b, turn, a_travel, b.travel_idx, side_only)
                if a.rw_type == S.RW_HIGHWAY and b.rw_type == S.RW_RAMP and turn == S.TURN_STRAIGHT and len(a_travel) > 1:
                    src = a_travel[-1] if d <= 0 else a_travel[0]
                    pairs = [(src, j) for j in b.travel_idx]
                pairs += _pair_lanes(a, b, turn, a_bike, b.bike_idx)
                if not pairs:
                    continue
                grp = groups.get(a.segment_id, -1) if signalized else -1
                for i, j in pairs:
                    p0 = a.pts[i]; p1 = b.pts[j]
                    g = bezier_connector(p0, a.heading, p1, b.heading, CONNECTOR_POINTS)
                    row = len(jl_id)
                    jl_id.append(next_id); next_id += 1
                    jl_from.append(int(lane_ids[a.lanes[i]])); jl_to.append(int(lane_ids[b.lanes[j]]))
                    jl_turn.append(turn); jl_group.append(grp); jl_node.append(node); jl_fseg.append(a.segment_id); jl_tseg.append(b.segment_id)
                    geoms.append(g)
                    node_rows.append((row, ai, turn, bi))
                    succ.setdefault(a.lanes[i], []).append(int(lane_ids[b.lanes[j]]))
                    pred.setdefault(b.lanes[j], []).append(int(lane_ids[a.lanes[i]]))
                    turn_counts[turn] += 1
        # ---- yield relations ----
        for row, ai, turn, bi in node_rows:
            a = inc[ai]
            y: list[int] = []
            if signalized or ctrl == S.CTRL_ALLWAY:
                if turn in (S.TURN_LEFT, S.TURN_UTURN):
                    for row2, ai2, turn2, _ in node_rows:
                        if ai2 != ai and turn2 in (S.TURN_STRAIGHT, S.TURN_RIGHT) and abs(angle_diff(a.heading, inc[ai2].heading)) > 120.0:
                            y.append(jl_id[row2])
            else:
                minor = (a.segment_id in stops) or (ctrl == S.CTRL_NONE and a.lanes_total < max_lanes)
                for row2, ai2, turn2, _ in node_rows:
                    if ai2 == ai:
                        continue
                    b2 = inc[ai2]
                    major2 = (b2.segment_id not in stops) and (ctrl != S.CTRL_NONE or b2.lanes_total >= max_lanes)
                    if minor and major2:
                        y.append(jl_id[row2])
                    elif turn in (S.TURN_LEFT, S.TURN_UTURN) and turn2 in (S.TURN_STRAIGHT, S.TURN_RIGHT) and abs(angle_diff(a.heading, b2.heading)) > 120.0 and not (b2.segment_id in stops and a.segment_id not in stops):
                        y.append(jl_id[row2])
            jl_yield.append(sorted(set(y)))

    counts = np.array([len(g) for g in geoms], dtype=np.int64)
    allc = np.concatenate(geoms) if geoms else np.zeros((0, 3))
    idx = np.repeat(np.arange(len(geoms)), counts)
    geom = shapely.linestrings(allc, indices=idx) if geoms else np.array([], dtype=object)
    jl = gpd.GeoDataFrame({
        "junction_lane_id": np.asarray(jl_id, dtype=np.int64),
        "from_lane": np.asarray(jl_from, dtype=np.int64), "to_lane": np.asarray(jl_to, dtype=np.int64),
        "turn": np.asarray(jl_turn, dtype=np.int8), "signal_group": np.asarray(jl_group, dtype=np.int32),
        "yield_to": jl_yield,
        "node_id": np.asarray(jl_node, dtype=np.int64), "from_segment": np.asarray(jl_fseg, dtype=np.int64), "to_segment": np.asarray(jl_tseg, dtype=np.int64),
    }, geometry=geom, crs=NYC_TM)
    lanes = lanes.copy()
    lanes["successors"] = [sorted(set(succ.get(i, []))) for i in range(len(lanes))]
    lanes["predecessors"] = [sorted(set(pred.get(i, []))) for i in range(len(lanes))]
    st.update({
        "junction_lanes": int(len(jl)), "turn_counts": {["straight", "left", "right", "uturn"][k]: v for k, v in turn_counts.items()},
        "uturns_allowed": n_uturn, "culdesac_turnarounds": n_culdesac, "restricted_pairs_removed": n_forbidden, "only_restriction_pairs_removed": n_only,
        "street_highway_pairs_blocked_by_ramp_rule": n_ramp_block,
        "yield_links": int(sum(len(y) for y in jl_yield)),
    })
    log.info("junction lanes: %d (%s) in %.1fs", len(jl), st["turn_counts"], time.time() - t0)
    return jl, lanes, st
