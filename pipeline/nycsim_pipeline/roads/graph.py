"""Directed road graph over the produced segments: A* routing, connectivity analysis and the one-way /
dead-end audits that verify the network is really drivable.

The graph is node-to-node. A drivable segment contributes one arc per legal direction (``TW`` two, ``FT`` /
``TF`` one, ``NV`` none). Arc cost is free-flow travel time (length / posted speed); the A* heuristic is the
straight-line distance divided by the fastest posted speed in the graph, which is admissible, so the first
route A* settles on is the true minimum-time route for this cost model.
"""
from __future__ import annotations

import heapq
import logging
import math
import time
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from . import schema as S

log = logging.getLogger("nycsim.roads.graph")

MPH_TO_MPS = 0.44704
MIN_SPEED_MPS = 2.0


@dataclass
class Route:
    found: bool
    from_node: int
    to_node: int
    nodes: list[int] = field(default_factory=list)
    segments: list[int] = field(default_factory=list)
    street_names: list[str] = field(default_factory=list)
    distance_m: float = 0.0
    time_s: float = 0.0
    expanded: int = 0
    seconds: float = 0.0

    def summary(self) -> dict:
        return {"found": self.found, "from_node": self.from_node, "to_node": self.to_node,
                "n_segments": len(self.segments), "distance_km": round(self.distance_m / 1000.0, 3),
                "time_min": round(self.time_s / 60.0, 2), "nodes_expanded": self.expanded,
                "search_seconds": round(self.seconds, 3),
                "streets": _dedupe_consecutive(self.street_names)}


def _dedupe_consecutive(names: list[str]) -> list[str]:
    out: list[str] = []
    for n in names:
        if n and (not out or out[-1] != n):
            out.append(n)
    return out


class RoadGraph:
    """Directed graph in CSR form built from ``segments.parquet`` + ``nodes.parquet``."""

    def __init__(self, seg: gpd.GeoDataFrame, nodes: pd.DataFrame) -> None:
        t0 = time.time()
        self.nodes = nodes
        self.node_ids = nodes["node_id"].to_numpy()
        self.pos = pd.Series(np.arange(len(nodes)), index=self.node_ids)
        self.x = nodes["x"].to_numpy(dtype=np.float64)
        self.y = nodes["y"].to_numpy(dtype=np.float64)
        self.n = len(nodes)

        drivable = seg["drivable"].to_numpy()
        td = seg["traffic_dir"].to_numpy()
        f = self.pos.reindex(seg["from_node"].to_numpy()).to_numpy()
        t = self.pos.reindex(seg["to_node"].to_numpy()).to_numpy()
        length = seg["length_m"].to_numpy(dtype=np.float64)
        speed = np.maximum(seg["posted_speed_mph"].to_numpy(dtype=np.float64) * MPH_TO_MPS, MIN_SPEED_MPS)
        sid = seg["segment_id"].to_numpy()
        name = seg["street_name"].to_numpy()

        fwd = drivable & np.isin(td, [S.DIR_TWO_WAY, S.DIR_FORWARD])
        bwd = drivable & np.isin(td, [S.DIR_TWO_WAY, S.DIR_BACKWARD])
        src = np.concatenate([f[fwd], t[bwd]])
        dst = np.concatenate([t[fwd], f[bwd]])
        arc_seg = np.concatenate([np.flatnonzero(fwd), np.flatnonzero(bwd)])
        cost = np.concatenate([length[fwd] / speed[fwd], length[bwd] / speed[bwd]])
        dist = np.concatenate([length[fwd], length[bwd]])

        order = np.argsort(src, kind="stable")
        self.arc_dst = dst[order].astype(np.int64)
        self.arc_seg = arc_seg[order].astype(np.int64)
        self.arc_cost = cost[order]
        self.arc_dist = dist[order]
        self.offsets = np.searchsorted(src[order], np.arange(self.n + 1))
        self.segment_ids = sid
        self.segment_names = name
        self.max_speed_mps = float(max(speed.max(), MIN_SPEED_MPS)) if len(speed) else MIN_SPEED_MPS
        self.n_arcs = int(len(self.arc_dst))
        log.info("road graph: %d nodes, %d directed arcs in %.1fs", self.n, self.n_arcs, time.time() - t0)

    # ---------------------------------------------------------------- lookup
    def find_intersection(self, name_a: str, name_b: str, borough: int | None = None) -> int:
        """node_id of the intersection of two normalised street names (-1 when there is none)."""
        names = self.nodes["names_norm"].to_numpy()
        boro = self.nodes["borough"].to_numpy() if "borough" in self.nodes.columns else None
        deg = self.nodes["degree_drivable"].to_numpy()
        best = -1
        best_deg = -1
        for i in range(self.n):
            if borough is not None and boro is not None and int(boro[i]) != borough:
                continue
            nn = names[i]
            if nn is None or len(nn) < 2:
                continue
            s = set(nn)
            if name_a in s and name_b in s and int(deg[i]) > best_deg:
                best = int(self.node_ids[i])
                best_deg = int(deg[i])
        return best

    # ---------------------------------------------------------------- routing
    def astar(self, from_node: int, to_node: int, avoid_segments: set[int] | None = None) -> Route:
        t0 = time.time()
        try:
            s = int(self.pos.at[from_node])
            g = int(self.pos.at[to_node])
        except KeyError:
            return Route(False, int(from_node), int(to_node))
        inv = 1.0 / self.max_speed_mps
        gx, gy = self.x[g], self.y[g]
        gscore = np.full(self.n, np.inf)
        dscore = np.full(self.n, np.inf)
        prev_node = np.full(self.n, -1, dtype=np.int64)
        prev_arc = np.full(self.n, -1, dtype=np.int64)
        closed = np.zeros(self.n, dtype=bool)
        gscore[s] = 0.0
        dscore[s] = 0.0
        h0 = math.hypot(self.x[s] - gx, self.y[s] - gy) * inv
        heap = [(h0, s)]
        expanded = 0
        avoid = avoid_segments or set()
        while heap:
            _, u = heapq.heappop(heap)
            if closed[u]:
                continue
            closed[u] = True
            expanded += 1
            if u == g:
                break
            for a in range(self.offsets[u], self.offsets[u + 1]):
                if avoid and int(self.segment_ids[self.arc_seg[a]]) in avoid:
                    continue
                v = int(self.arc_dst[a])
                if closed[v]:
                    continue
                ng = gscore[u] + self.arc_cost[a]
                if ng < gscore[v]:
                    gscore[v] = ng
                    dscore[v] = dscore[u] + self.arc_dist[a]
                    prev_node[v] = u
                    prev_arc[v] = a
                    heapq.heappush(heap, (ng + math.hypot(self.x[v] - gx, self.y[v] - gy) * inv, v))
        if not np.isfinite(gscore[g]):
            return Route(False, int(from_node), int(to_node), expanded=expanded, seconds=time.time() - t0)
        path_nodes: list[int] = []
        path_segs: list[int] = []
        names: list[str] = []
        v = g
        while v != -1:
            path_nodes.append(int(self.node_ids[v]))
            a = prev_arc[v]
            if a >= 0:
                path_segs.append(int(self.segment_ids[self.arc_seg[a]]))
                names.append(str(self.segment_names[self.arc_seg[a]]))
            v = int(prev_node[v]) if prev_node[v] != -1 else -1
        path_nodes.reverse()
        path_segs.reverse()
        names.reverse()
        return Route(True, int(from_node), int(to_node), path_nodes, path_segs, names,
                     float(dscore[g]), float(gscore[g]), expanded, time.time() - t0)

    # ---------------------------------------------------------------- connectivity
    def components(self, connection: str = "weak") -> dict:
        rows = np.repeat(np.arange(self.n), np.diff(self.offsets))
        adj = coo_matrix((np.ones(self.n_arcs, dtype=np.int8), (rows, self.arc_dst)), shape=(self.n, self.n))
        ncomp, labels = connected_components(adj, directed=True, connection=connection)
        sizes = np.bincount(labels)
        order = np.argsort(-sizes)
        touched = int((np.diff(self.offsets) > 0).sum())
        return {"n_components": int(ncomp), "largest": int(sizes[order[0]]) if ncomp else 0,
                "largest_share_of_graph_nodes": round(float(sizes[order[0]]) / max(self.n, 1), 5) if ncomp else 0.0,
                "nodes_with_outgoing_arcs": touched,
                "largest_share_of_drivable_nodes": round(float(sizes[order[0]]) / max(touched, 1), 5) if ncomp else 0.0,
                "top_sizes": [int(v) for v in sizes[order[:5]]],
                "labels": labels}


def undirected_components(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, drivable_only: bool = False) -> dict:
    """Component statistics of the undirected segment graph (the shape the integration gate checks)."""
    pos = pd.Series(np.arange(len(nodes)), index=nodes["node_id"].to_numpy())
    m = seg["drivable"].to_numpy() if drivable_only else np.ones(len(seg), dtype=bool)
    f = pos.reindex(seg["from_node"].to_numpy()[m]).to_numpy()
    t = pos.reindex(seg["to_node"].to_numpy()[m]).to_numpy()
    n = len(nodes)
    rows = np.concatenate([f, t])
    cols = np.concatenate([t, f])
    adj = coo_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(n, n))
    ncomp, labels = connected_components(adj, directed=False)
    sizes = np.bincount(labels)
    order = np.argsort(-sizes)
    return {"n_components": int(ncomp), "largest": int(sizes[order[0]]),
            "share": round(float(sizes[order[0]]) / max(n, 1), 5),
            "top_sizes": [int(v) for v in sizes[order[:6]]], "labels": labels}


# ---------------------------------------------------------------------- one-way audit
def travel_bearings(seg: gpd.GeoDataFrame, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compass bearing of legal travel and length for every one-way segment selected by ``mask``."""
    sub = seg[mask]
    g = sub.geometry.values
    coords = shapely.get_coordinates(g)
    n_per = shapely.get_num_coordinates(g)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    v = coords[starts + n_per - 1] - coords[starts]
    sign = np.where(sub["traffic_dir"].to_numpy() == S.DIR_BACKWARD, -1.0, 1.0)
    v = v * sign[:, None]
    bearing = (90.0 - np.degrees(np.arctan2(v[:, 1], v[:, 0]))) % 360.0
    return bearing, sub["length_m"].to_numpy(dtype=np.float64)


def one_way_audit(seg: gpd.GeoDataFrame, name_norm: str, borough: int, expected_bearing: float | None,
                  y_max: float | None = None, y_min: float | None = None, tol_deg: float = 60.0) -> dict:
    """Length-weighted direction audit of one street. ``expected_bearing`` is a compass heading (0 = north)."""
    m = (seg["name_norm"].to_numpy() == name_norm) & (seg["borough"].to_numpy() == borough) & seg["drivable"].to_numpy()
    if y_max is not None or y_min is not None:
        mid = shapely.get_coordinates(shapely.line_interpolate_point(seg.geometry.values, 0.5, normalized=True))
        if y_max is not None:
            m &= mid[:, 1] <= y_max
        if y_min is not None:
            m &= mid[:, 1] >= y_min
    total_km = round(float(seg["length_m"].to_numpy()[m].sum()) / 1000.0, 3)
    ow = m & np.isin(seg["traffic_dir"].to_numpy(), [S.DIR_FORWARD, S.DIR_BACKWARD])
    tw = m & (seg["traffic_dir"].to_numpy() == S.DIR_TWO_WAY)
    out = {"street": name_norm, "borough": borough, "segments": int(m.sum()), "km": total_km,
           "one_way_segments": int(ow.sum()), "two_way_segments": int(tw.sum()),
           "one_way_km": round(float(seg["length_m"].to_numpy()[ow].sum()) / 1000.0, 3),
           "two_way_km": round(float(seg["length_m"].to_numpy()[tw].sum()) / 1000.0, 3)}
    if not ow.any():
        out.update({"mean_travel_bearing": None, "share_matching_expected": None, "expected_bearing": expected_bearing, "pass": None})
        return out
    b, L = travel_bearings(seg, ow)
    r = np.radians(b)
    mean_b = float((np.degrees(np.arctan2((np.sin(r) * L).sum(), (np.cos(r) * L).sum()))) % 360.0)
    out["mean_travel_bearing"] = round(mean_b, 1)
    for label, centre in (("north", 0.0), ("east", 90.0), ("south", 180.0), ("west", 270.0)):
        d = np.abs((b - centre + 180.0) % 360.0 - 180.0)
        out[f"km_{label}bound"] = round(float(L[d <= 45.0].sum()) / 1000.0, 3)
    out["north_south_share"] = round(float((out["km_northbound"] + out["km_southbound"]) * 1000.0 / L.sum()), 4)
    out["expected_bearing"] = expected_bearing
    if expected_bearing is None:
        out["share_matching_expected"] = None
        out["pass"] = None
        return out
    d = np.abs((b - expected_bearing + 180.0) % 360.0 - 180.0)
    share = float(L[d <= tol_deg].sum() / L.sum())
    out["share_matching_expected"] = round(share, 4)
    out["pass"] = bool(share >= 0.8)
    return out


def dead_end_lanes(lanes: gpd.GeoDataFrame) -> dict:
    """Travel/turn lanes with no successor (or no predecessor) once junction lanes are attached."""
    kind = lanes["kind"].to_numpy()
    travel = np.isin(kind, [S.LANE_TRAVEL, S.LANE_TURN])
    succ = np.array([len(v) for v in lanes["successors"].to_numpy()])
    pred = np.array([len(v) for v in lanes["predecessors"].to_numpy()])
    return {
        "travel_lanes": int(travel.sum()),
        "travel_lanes_without_successor": int((travel & (succ == 0)).sum()),
        "travel_lanes_without_predecessor": int((travel & (pred == 0)).sum()),
        "travel_lanes_isolated": int((travel & (succ == 0) & (pred == 0)).sum()),
        "bike_lanes_without_successor": int(((kind == S.LANE_BIKE) & (succ == 0)).sum()),
        "mean_successors_per_travel_lane": round(float(succ[travel].mean()), 3) if travel.any() else 0.0,
    }
