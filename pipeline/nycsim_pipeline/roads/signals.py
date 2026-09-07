"""Signalised and stop-controlled intersections (ADR-007) and DOT-standard phasing.

Sources, in provenance priority: DOT LPI points (1) > DOT Barnes-Dance/exclusive-ped points (2) > OSM
``highway=traffic_signals`` (0) > DOT 25-mph retiming corridors (3) > inferred (4). Every source that hits a
node is kept in the extension bitmask ``signal_sources_mask`` so overlaps can be audited.

The retiming list names a corridor, not its individual signals, so on its own it would flag every intersection
the corridor passes. A retiming-only node is therefore kept only where the crossing street is a real through
street (its name is on at least two legs and it carries at least two travel lanes); the minor side streets the
corridor also passes are dropped. Nodes that another source already flagged are unaffected.

Inference (ADR-007, refined): a node is inferred signalised only when it is unsignalised in every source,
no OSM stop/yield sign is snapped to it, at least two distinct streets meet, and at least two of them
carry >= 2 travel lanes *per direction* (one-way: travel_lanes >= 2; two-way: travel_lanes >= 4). This is the
"multi-lane arterial meets multi-lane arterial" case, which is signalised throughout NYC.

Phasing: two vehicle phases (main street group 0, cross street group 1; a third group for 5+ leg nodes);
cycle 90 s in the Manhattan CBD (south of the real 60th Street line), 60 s elsewhere, escalated to 90/120 s
only when the pedestrian minimums do not fit; yellow 3 s, all-red 2 s; pedestrian WALK 7 s + flashing
(crossing width / 1.1 m/s); LPI 7 s where DOT lists one; Barnes Dance exclusive pedestrian phase where DOT
lists one. Offsets progress along one-way streets at 25 mph (11.18 m/s).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from ..crs import NYC_TM, lonlat_to_tm
from . import schema as S
from .geom import PointSnapper, angle_diff, end_heading, fit_line_pca
from .names import normalize, core_tokens

log = logging.getLogger("nycsim.roads.signals")

SNAP_INTERSECTION_M = 25.0
SNAP_MIDBLOCK_M = 10.0
SNAP_DOT_M = 30.0
SNAP_STOP_M = 30.0
RETIMING_BUFFER_M = 12.0
YELLOW_S, ALLRED_S = 3.0, 2.0
PED_WALK_S = 7.0
PED_SPEED_MPS = 1.1
LPI_S = 7.0
MIN_GREEN_S = 10.0
CYCLE_CBD_S, CYCLE_STD_S = 90.0, 60.0
CYCLE_ESCALATION = (90.0, 120.0)
PROGRESSION_MPS = 25 * 0.44704
CLUSTER_RADIUS_M = 40.0
ESB_LONLAT = (-73.9857, 40.7484)


@dataclass
class Leg:
    segment_id: int
    name_norm: str
    heading_out: float     # math heading leaving the node along the leg
    lanes_in: int          # travel lanes arriving at the node
    lanes_out: int         # travel lanes leaving the node
    width: float
    rw_type: int
    traffic_dir: int


@dataclass
class SignalResult:
    nodes: pd.DataFrame
    signals: pd.DataFrame
    node_groups: dict[int, dict[int, int]] = field(default_factory=dict)
    stop_approaches: dict[int, set[int]] = field(default_factory=dict)
    yield_approaches: dict[int, set[int]] = field(default_factory=dict)
    stats: dict = field(default_factory=dict)


def _cbd_test(seg: gpd.GeoDataFrame):
    """Return f(x, y, borough) -> bool for 'Manhattan south of 60th Street' from the real 60th St segments."""
    m = (seg["borough"] == 1) & seg["name_norm"].isin(["W 60 ST", "E 60 ST"]) & (seg["rw_type"] == S.RW_STREET)
    if m.sum() < 2:
        log.warning("60th Street segments not found; CBD test disabled")
        return lambda x, y, b: np.zeros_like(np.asarray(x), dtype=bool)
    xy = shapely.get_coordinates(seg.loc[m, "geometry"].values)
    c, d = fit_line_pca(xy)
    ex, ey = lonlat_to_tm(*ESB_LONLAT)
    ref = np.sign(d[0] * (ey - c[1]) - d[1] * (ex - c[0]))

    def f(x, y, b):
        s = np.sign(d[0] * (np.asarray(y) - c[1]) - d[1] * (np.asarray(x) - c[0]))
        return (s == ref) & (np.asarray(b) == 1)
    return f


def _legs_by_node(seg: gpd.GeoDataFrame) -> dict[int, list[Leg]]:
    """Drivable legs at every node with heading, lanes in/out and width."""
    out: dict[int, list[Leg]] = {}
    d = seg[seg["drivable"]]
    coords = shapely.get_coordinates(d.geometry.values)
    n_per = shapely.get_num_coordinates(d.geometry.values)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    sid = d["segment_id"].to_numpy(); fn = d["from_node"].to_numpy(); tn = d["to_node"].to_numpy()
    nm = d["name_norm"].to_numpy(); tl = d["travel_lanes"].to_numpy(); td = d["traffic_dir"].to_numpy()
    w = d["width_m"].to_numpy(); rw = d["rw_type"].to_numpy()
    for i in range(len(d)):
        c = coords[starts[i]: starts[i] + n_per[i]]
        if len(c) < 2:
            continue
        h_from = end_heading(c, at_end=False)
        h_to = (end_heading(c, at_end=True) + 180.0) % 360.0
        t = int(tl[i]); dirc = int(td[i])
        if dirc == S.DIR_TWO_WAY:
            each = max(1, t // 2)
            fwd_in, fwd_out = each, each
        elif dirc == S.DIR_FORWARD:
            fwd_in, fwd_out = t, 0
        else:
            fwd_in, fwd_out = 0, t
        # at the from-node: lanes leaving along forward = fwd_in... (forward direction leaves from_node)
        out.setdefault(int(fn[i]), []).append(Leg(int(sid[i]), nm[i], h_from, lanes_in=fwd_out, lanes_out=fwd_in, width=float(w[i]), rw_type=int(rw[i]), traffic_dir=dirc))
        out.setdefault(int(tn[i]), []).append(Leg(int(sid[i]), nm[i], h_to, lanes_in=fwd_in, lanes_out=fwd_out, width=float(w[i]), rw_type=int(rw[i]), traffic_dir=dirc))
    return out


def _group_legs(legs: list[Leg]) -> dict[int, int]:
    """segment_id -> phase group (0 main, 1 cross, 2 third). Legs are grouped by street name, then merged by
    anti-parallel heading until at most 2 groups remain (3 when the node has >= 5 legs)."""
    groups: list[list[Leg]] = []
    by_name: dict[str, list[Leg]] = {}
    for l in legs:
        by_name.setdefault(l.name_norm or f"#{l.segment_id}", []).append(l)
    groups = list(by_name.values())
    max_groups = 3 if len(legs) >= 5 else 2

    def axis(g: list[Leg]) -> float:
        # mean heading modulo 180 (doubled-angle mean)
        a = np.radians(np.array([l.heading_out for l in g]) * 2.0)
        return float(np.degrees(np.arctan2(np.sin(a).mean(), np.cos(a).mean())) / 2.0) % 180.0

    # split a same-name group whose legs are not anti-parallel (a street turning a corner into itself is fine)
    while len(groups) > max_groups:
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                da = abs(angle_diff(axis(groups[i]) * 2.0, axis(groups[j]) * 2.0)) / 2.0
                if best is None or da < best[0]:
                    best = (da, i, j)
        _, i, j = best
        groups[i] = groups[i] + groups[j]
        del groups[j]

    def weight(g: list[Leg]) -> tuple:
        return (sum(l.lanes_in + l.lanes_out for l in g), sum(l.width for l in g))
    groups.sort(key=weight, reverse=True)
    return {l.segment_id: gi for gi, g in enumerate(groups) for l in g}


def _phases(legs: list[Leg], groups: dict[int, int], cycle: float, lpi: bool, barnes: bool) -> tuple[float, list[dict], bool]:
    """Return (cycle_s, phases, escalated_or_scaled)."""
    n_groups = max(groups.values()) + 1 if groups else 1
    group_legs = [[l for l in legs if groups.get(l.segment_id, 0) == g] for g in range(n_groups)]
    widest = max((l.width for l in legs), default=9.0)
    # crossing width for pedestrians moving parallel to group g = widest leg not in g
    cross_w = []
    for g in range(n_groups):
        others = [l.width for l in legs if groups.get(l.segment_id, 0) != g]
        cross_w.append(max(others) if others else widest)
    flash = [max(4.0, w / PED_SPEED_MPS) for w in cross_w]
    lpi_s = LPI_S if lpi else 0.0
    mins = [lpi_s + max(MIN_GREEN_S, PED_WALK_S + f) for f in flash]
    barnes_time = (PED_WALK_S + max(4.0, widest / PED_SPEED_MPS)) if barnes else 0.0
    fixed = n_groups * (YELLOW_S + ALLRED_S) + barnes_time
    changed = False
    c = cycle
    for cand in (cycle,) + tuple(x for x in CYCLE_ESCALATION if x > cycle):
        c = cand
        if sum(mins) + fixed <= c + 1e-6:
            break
    if sum(mins) + fixed > c + 1e-6:
        # cannot fit even at 120 s: scale the pedestrian flashing intervals (flagged)
        avail = c - fixed - n_groups * lpi_s
        scale = max(0.1, avail / sum(max(MIN_GREEN_S, PED_WALK_S + f) for f in flash))
        flash = [max(2.0, f * scale) for f in flash]
        mins = [lpi_s + max(MIN_GREEN_S * scale, PED_WALK_S + f) for f in flash]
        changed = True
    if c != cycle:
        changed = True
    spare = c - fixed - sum(mins)
    weights = np.array([max(1, sum(l.lanes_in + l.lanes_out for l in g)) for g in group_legs], dtype=np.float64)
    weights /= weights.sum()
    phases = []
    for g in range(n_groups):
        green = mins[g] - lpi_s + spare * weights[g]
        phases.append({"group": g, "green_s": round(float(green), 2), "yellow_s": YELLOW_S, "allred_s": ALLRED_S,
                       "ped_walk_s": PED_WALK_S, "ped_flash_s": round(float(flash[g]), 2), "lpi_s": lpi_s})
    if barnes:
        phases.append({"group": -1, "green_s": 0.0, "yellow_s": 0.0, "allred_s": 0.0, "ped_walk_s": PED_WALK_S,
                       "ped_flash_s": round(float(max(4.0, widest / PED_SPEED_MPS)), 2), "lpi_s": 0.0})
    # exact cycle closure: absorb rounding into the main phase green
    total = sum(p["lpi_s"] + p["green_s"] + p["yellow_s"] + p["allred_s"] for p in phases if p["group"] >= 0) + (barnes_time if barnes else 0.0)
    phases[0]["green_s"] = round(phases[0]["green_s"] + (c - total), 2)
    return c, phases, changed


def _read_points_wkt(path: Path, wkt_col: str) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, dtype=str)
    g = gpd.GeoSeries.from_wkt(df[wkt_col].fillna("POINT EMPTY"), crs="EPSG:4326").to_crs(NYC_TM)
    gdf = gpd.GeoDataFrame(df, geometry=g, crs=NYC_TM)
    return gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].reset_index(drop=True)


def build(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, inputs, osm_nodes: pd.DataFrame) -> SignalResult:
    t0 = time.time()
    st: dict = {}
    nd = nodes.copy()
    n = len(nd)
    nid = nd["node_id"].to_numpy()
    names_norm = nd["names_norm"].to_numpy()
    n_names = np.array([len(v) for v in names_norm])
    legs = _legs_by_node(seg)
    deg_dr = nd["degree_drivable"].to_numpy()
    is_intersection = (deg_dr >= 3) | ((deg_dr == 2) & (n_names >= 2))
    inter = PointSnapper(nd.loc[is_intersection, ["x", "y"]].to_numpy(), nid[is_intersection])
    midblock = PointSnapper(nd.loc[deg_dr == 2, ["x", "y"]].to_numpy(), nid[deg_dr == 2])
    pos_of = pd.Series(np.arange(n), index=nid)
    mask = np.zeros(n, dtype=np.uint8)
    lpi_flag = np.zeros(n, dtype=bool)
    barnes_excl = np.zeros(n, dtype=bool)

    def snap_pts(xy: np.ndarray, d_inter: float, d_mid: float = 0.0) -> np.ndarray:
        ids, _ = inter.snap(xy, d_inter)
        if d_mid > 0:
            miss = ids < 0
            if miss.any():
                ids2, _ = midblock.snap(xy[miss], d_mid)
                ids[miss] = ids2
        return ids

    # ---- OSM signals ----
    osig = osm_nodes[osm_nodes["highway"].astype(str).str.startswith("traffic_signals")]
    ids = snap_pts(osig[["x", "y"]].to_numpy(), SNAP_INTERSECTION_M, SNAP_MIDBLOCK_M)
    hit = ids[ids >= 0]
    mask[pos_of.loc[hit].to_numpy()] |= S.SIGBIT_OSM
    st["osm_signal_nodes"] = int(len(osig)); st["osm_signal_nodes_snapped"] = int((ids >= 0).sum())

    # ---- DOT LPI ----
    if inputs.has("vzv_lpi_signals"):
        lp = pd.read_csv(inputs["vzv_lpi_signals"], dtype=str)
        x, y = lonlat_to_tm(pd.to_numeric(lp["LONG"], errors="coerce").to_numpy(), pd.to_numeric(lp["LAT"], errors="coerce").to_numpy())
        xy = np.column_stack([x, y])
        ok = np.isfinite(xy).all(axis=1)
        ids = np.full(len(lp), -1, dtype=np.int64)
        ids[ok] = snap_pts(xy[ok], SNAP_DOT_M)
        main = lp["MainStreet"].map(normalize).to_numpy(); cross = lp["CrossStree"].map(normalize).to_numpy()
        verified = 0
        for i in np.flatnonzero(ids >= 0):
            p = pos_of.at[ids[i]]
            nn = set(names_norm[p]) | {core_tokens(v) for v in names_norm[p]}
            if (main[i] in nn or core_tokens(main[i]) in nn) and (cross[i] in nn or core_tokens(cross[i]) in nn):
                verified += 1
        hit = ids[ids >= 0]
        mask[pos_of.loc[hit].to_numpy()] |= S.SIGBIT_LPI
        lpi_flag[pos_of.loc[hit].to_numpy()] = True
        st["lpi_rows"] = int(len(lp)); st["lpi_snapped"] = int((ids >= 0).sum()); st["lpi_name_verified"] = verified

    # ---- DOT Barnes / exclusive pedestrian ----
    if inputs.has("barnes_dance"):
        bd = _read_points_wkt(inputs["barnes_dance"], "the_geom")
        xy = shapely.get_coordinates(bd.geometry.values)
        ids = snap_pts(xy, SNAP_DOT_M)
        excl = (bd["Barnes Dance"].fillna("").str.strip() != "") | (bd["Modified Barnes Dance"].fillna("").str.strip() != "")
        hit = ids >= 0
        mask[pos_of.loc[ids[hit]].to_numpy()] |= S.SIGBIT_BARNES
        barnes_excl[pos_of.loc[ids[hit & excl.to_numpy()]].to_numpy()] = True
        st["barnes_rows"] = int(len(bd)); st["barnes_snapped"] = int(hit.sum()); st["barnes_exclusive_nodes"] = int(barnes_excl.sum())

    # ---- DOT retiming corridors ----
    if inputs.has("signal_retiming"):
        rt = pd.read_csv(inputs["signal_retiming"], dtype=str)
        g = gpd.GeoSeries.from_wkt(rt["the_geom"], crs="EPSG:4326").to_crs(NYC_TM)
        on = rt["OnStreet"].map(normalize).to_numpy()
        pts = shapely.points(nd.loc[is_intersection, ["x", "y"]].to_numpy())
        tree = shapely.STRtree(pts)
        inter_pos = np.flatnonzero(is_intersection)
        corridor_of: dict[int, str] = {}
        for gi, geom in enumerate(g.values):
            if geom is None or geom.is_empty:
                continue
            idx = tree.query(geom.buffer(RETIMING_BUFFER_M), predicate="intersects")
            want = on[gi]; want_core = core_tokens(want)
            for k in idx:
                p = int(inter_pos[k])
                nn = names_norm[p]
                if any(v == want or core_tokens(v) == want_core for v in nn):
                    mask[p] |= S.SIGBIT_RETIMING
                    corridor_of.setdefault(p, want)
        on_corridor = int((mask & S.SIGBIT_RETIMING > 0).sum())
        # A retiming project names the corridor, not which of its intersections carry a signal: an arterial is
        # retimed end to end but only its through crossings are signalised. Keep the bit where the crossing is a
        # real through street (the cross name appears on >= 2 legs and carries >= 2 travel lanes); drop it at the
        # minor side streets and driveways the corridor also passes. Nodes another source already flagged keep
        # their signal regardless.
        dropped = 0
        for p in np.flatnonzero(mask & S.SIGBIT_RETIMING > 0):
            L = legs.get(int(nid[p]), [])
            corridor = corridor_of.get(int(p), "")
            cross = [l for l in L if l.name_norm and l.name_norm != corridor]
            cross_names = {l.name_norm for l in cross}
            keep = False
            for cn in cross_names:
                legs_cn = [l for l in cross if l.name_norm == cn]
                lanes_cn = max((l.lanes_in + l.lanes_out) for l in legs_cn)
                if len(legs_cn) >= 2 and lanes_cn >= 2:
                    keep = True
                    break
            if not keep:
                mask[p] &= ~S.SIGBIT_RETIMING
                dropped += 1
        st["retiming_corridors"] = int(len(rt))
        st["retiming_nodes_on_corridor"] = on_corridor
        st["retiming_nodes_dropped_not_a_through_crossing"] = dropped
        st["retiming_nodes"] = int((mask & S.SIGBIT_RETIMING > 0).sum())

    # ---- OSM stop / yield signs (needed before inference) ----
    stop_approaches: dict[int, set[int]] = {}
    yield_approaches: dict[int, set[int]] = {}
    allway_nodes: set[int] = set()
    seg_dr = seg[seg["drivable"]]
    seg_tree = shapely.STRtree(seg_dr.geometry.values)
    seg_sid = seg_dr["segment_id"].to_numpy(); seg_fn = seg_dr["from_node"].to_numpy(); seg_tn = seg_dr["to_node"].to_numpy()
    for kind, store in (("stop", stop_approaches), ("give_way", yield_approaches)):
        sub = osm_nodes[osm_nodes["highway"].astype(str).str.startswith(kind)]
        xy = sub[["x", "y"]].to_numpy()
        ids = snap_pts(xy, SNAP_STOP_M)
        stop_all = sub["stop"].astype(str).eq("all").to_numpy() if kind == "stop" else np.zeros(len(sub), dtype=bool)
        for i in np.flatnonzero(ids >= 0):
            node = int(ids[i])
            # controlled approach = incident drivable segment nearest to the sign
            near = seg_tree.query(shapely.Point(xy[i]).buffer(SNAP_STOP_M + 5), predicate="intersects")
            best = None
            for k in near:
                if seg_fn[k] == node or seg_tn[k] == node:
                    dd = shapely.distance(seg_dr.geometry.values[k], shapely.Point(xy[i]))
                    if best is None or dd < best[0]:
                        best = (dd, int(seg_sid[k]))
            if best is not None:
                store.setdefault(node, set()).add(best[1])
            if stop_all[i]:
                allway_nodes.add(node)
        st[f"osm_{kind}_nodes"] = int(len(sub)); st[f"osm_{kind}_snapped"] = int((ids >= 0).sum())

    # ---- inference (ADR-007) ----
    has_sign_control = np.zeros(n, dtype=bool)
    for node in list(stop_approaches) + list(yield_approaches):
        has_sign_control[pos_of.at[node]] = True
    inferred = 0
    for p in np.flatnonzero(is_intersection & (mask == 0) & ~has_sign_control):
        L = legs.get(int(nid[p]), [])
        if len(L) < 3:
            continue
        if all(l.rw_type in (S.RW_HIGHWAY, S.RW_RAMP) for l in L):
            continue
        per_dir: dict[str, int] = {}
        for l in L:
            pd_lanes = max(l.lanes_in, l.lanes_out)
            per_dir[l.name_norm] = max(per_dir.get(l.name_norm, 0), pd_lanes)
        if len(per_dir) >= 2 and sum(1 for v in per_dir.values() if v >= 2) >= 2:
            mask[p] |= S.SIGBIT_INFERRED
            inferred += 1
    st["inferred_signal_nodes"] = inferred

    # ---- signal_source (priority) and control ----
    signal_source = np.full(n, S.SIG_NONE, dtype=np.uint8)
    for bit, code in ((S.SIGBIT_LPI, S.SIG_DOT_LPI), (S.SIGBIT_BARNES, S.SIG_DOT_BARNES), (S.SIGBIT_OSM, S.SIG_OSM), (S.SIGBIT_RETIMING, S.SIG_DOT_RETIMING), (S.SIGBIT_INFERRED, S.SIG_INFERRED)):
        sel = (signal_source == S.SIG_NONE) & (mask & bit > 0)
        signal_source[sel] = code
    is_sig = signal_source != S.SIG_NONE
    has_stop = np.zeros(n, dtype=bool); has_allway = np.zeros(n, dtype=bool); has_yield = np.zeros(n, dtype=bool)
    for node, segs in stop_approaches.items():
        p = pos_of.at[node]
        if is_sig[p]:
            continue
        has_stop[p] = True
        if node in allway_nodes or len(segs) >= max(3, deg_dr[p]):
            has_allway[p] = True
    for node in yield_approaches:
        p = pos_of.at[node]
        if not is_sig[p]:
            has_yield[p] = True
    control = np.where(is_sig, S.CTRL_SIGNAL, np.where(has_allway, S.CTRL_ALLWAY, np.where(has_stop, S.CTRL_STOP, np.where(has_yield, S.CTRL_YIELD, S.CTRL_NONE)))).astype(np.int8)
    # drop stop approaches at signalised nodes so downstream never places a stop sign there
    stop_approaches = {k: v for k, v in stop_approaches.items() if not is_sig[pos_of.at[k]]}
    yield_approaches = {k: v for k, v in yield_approaches.items() if not is_sig[pos_of.at[k]]}

    # ---- node borough + CBD ----
    nb = pd.concat([pd.DataFrame({"node": seg["from_node"], "b": seg["borough"]}), pd.DataFrame({"node": seg["to_node"], "b": seg["borough"]})])
    node_boro = nb.groupby("node")["b"].agg(lambda s: s.mode().iloc[0])
    boro = node_boro.reindex(nid).fillna(0).to_numpy().astype(np.int8)
    cbd_f = _cbd_test(seg)
    cbd = cbd_f(nd["x"].to_numpy(), nd["y"].to_numpy(), boro)

    # ---- phasing ----
    node_groups: dict[int, dict[int, int]] = {}
    rows = []
    escalated = 0
    controller = 0
    for p in np.flatnonzero(is_sig):
        node = int(nid[p])
        L = legs.get(node, [])
        if not L:
            continue
        groups = _group_legs(L)
        node_groups[node] = groups
        cyc0 = CYCLE_CBD_S if cbd[p] else CYCLE_STD_S
        cyc, phases, changed = _phases(L, groups, cyc0, bool(lpi_flag[p]), bool(barnes_excl[p]))
        escalated += int(changed)
        controller += 1
        rows.append((node, controller, float(cyc), 0.0, phases))
    sig = pd.DataFrame(rows, columns=["node_id", "controller_id", "cycle_s", "offset_s", "phases"])

    # ---- progressive offsets along one-way streets ----
    if len(sig):
        ow = seg[seg["drivable"] & seg["traffic_dir"].isin([S.DIR_FORWARD, S.DIR_BACKWARD]) & (seg["rw_type"] == S.RW_STREET)]
        node_xy = nd[["x", "y"]].to_numpy()
        best_lanes = np.zeros(len(sig), dtype=np.int16)
        sig_index = pd.Series(np.arange(len(sig)), index=sig["node_id"].to_numpy())
        n_prog = 0
        for (name, b), grp in ow.groupby(["name_norm", "borough"]):
            if len(grp) < 3 or name == "":
                continue
            snodes = np.unique(np.concatenate([grp["from_node"].to_numpy(), grp["to_node"].to_numpy()]))
            snodes = snodes[np.isin(snodes, sig["node_id"].to_numpy())]
            if len(snodes) < 3:
                continue
            xy = shapely.get_coordinates(grp.geometry.values)
            c, d = fit_line_pca(xy)
            # travel direction along the axis: forward segments' mean direction
            coords = shapely.get_coordinates(grp.geometry.values)
            n_per = shapely.get_num_coordinates(grp.geometry.values)
            starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
            vec = coords[starts + n_per - 1] - coords[starts]
            sign = np.where(grp["traffic_dir"].to_numpy() == S.DIR_FORWARD, 1.0, -1.0)
            travel = (vec * sign[:, None]).sum(axis=0)
            if np.dot(travel, d) < 0:
                d = -d
            proj = (node_xy[pos_of.loc[snodes].to_numpy()] - c) @ d
            if proj.max() - proj.min() < 300.0:
                continue
            lanes_here = int(grp["travel_lanes"].max())
            base = proj.min()
            for node, pr in zip(snodes, proj):
                si = sig_index.at[node]
                if lanes_here > best_lanes[si]:
                    best_lanes[si] = lanes_here
                    sig.at[si, "offset_s"] = float(((pr - base) / PROGRESSION_MPS) % sig.at[si, "cycle_s"])
                    n_prog += 1
        st["signals_with_progression_offset"] = int((best_lanes > 0).sum())

    nd["is_signalized"] = is_sig
    nd["signal_source"] = signal_source
    nd["has_stop_sign"] = has_stop
    nd["has_all_way_stop"] = has_allway
    nd["control"] = control
    nd["signal_sources_mask"] = mask
    nd["barnes_exclusive"] = barnes_excl
    nd["lpi"] = lpi_flag
    nd["cbd"] = cbd
    nd["borough"] = boro
    # One real intersection can be several nodes (divided roadways, service roads, medians): report both the node
    # count and the number of distinct intersection clusters (single-link at CLUSTER_RADIUS_M) so the figure can be
    # compared with DOT's published count of signalised intersections.
    n_clusters = 0
    if int(is_sig.sum()):
        sig_xy = nd.loc[is_sig, ["x", "y"]].to_numpy()
        tree_s = cKDTree(sig_xy)
        pairs = np.asarray(list(tree_s.query_pairs(CLUSTER_RADIUS_M)), dtype=np.int64).reshape(-1, 2)
        m = len(sig_xy)
        adj = coo_matrix((np.ones(len(pairs), dtype=np.int8), (pairs[:, 0], pairs[:, 1])), shape=(m, m))
        n_clusters = int(connected_components(adj, directed=False)[0])
    st.update({
        "signalized_nodes": int(is_sig.sum()),
        "signalized_intersection_clusters": n_clusters,
        "signalized_by_source": {S.SIG_SOURCE_NAMES[int(k)]: int(v) for k, v in zip(*np.unique(signal_source[is_sig], return_counts=True))},
        "signalized_source_mask_counts": {int(k): int(v) for k, v in zip(*np.unique(mask[is_sig], return_counts=True))},
        "stop_nodes": int(has_stop.sum()), "all_way_stop_nodes": int(has_allway.sum()), "yield_nodes": int(has_yield.sum()),
        "control_counts": {int(k): int(v) for k, v in zip(*np.unique(control, return_counts=True))},
        "cbd_signals": int((is_sig & cbd).sum()), "cycle_escalated_or_scaled": escalated,
        "cycle_counts": {float(k): int(v) for k, v in sig["cycle_s"].value_counts().items()} if len(sig) else {},
    })
    log.info("signals: %d signalised nodes (%s), %d stop, %d all-way in %.1fs", int(is_sig.sum()), st["signalized_by_source"], int(has_stop.sum()), int(has_allway.sum()), time.time() - t0)
    return SignalResult(nodes=nd, signals=sig, node_groups=node_groups, stop_approaches=stop_approaches, yield_approaches=yield_approaches, stats=st)
