"""LION (DCP, Socrata 2v4z-66xt) file geodatabase: node topology and node street names.

CSCL ``physicalid`` == LION ``PhysicalID``; a CSCL segment corresponds to a chain of one or more LION
segments (LION splits at census-block boundaries). The chain's two extreme nodes are the CSCL segment's
``from_node``/``to_node``; they are picked by proximity to the CSCL segment's first/last vertex so the
result is independent of LION's digitisation direction.
"""
from __future__ import annotations

import logging
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from ..crs import NYC_TM
from .geom import PointSnapper
from .names import normalize

log = logging.getLogger("nycsim.roads.lion")

SYNTHETIC_NODE_BASE = 10_000_000
NODE_MATCH_TOL_M = 5.0          # CSCL end vertex vs LION node of the same physicalid
NODE_NEAREST_TOL_M = 3.0        # fallback: any LION node
SYNTH_MERGE_TOL_M = 0.5
NON_STREET_NAME_MARKERS = ("BOUNDARY", "SHORELINE", "CB ", "CENSUS", "BORO BNDY", "RAILROAD", "RAIL ROAD")


def ensure_extracted(zip_path: Path) -> Path:
    """Extract ``nyclion.zip`` next to itself (idempotent) and return the ``lion.gdb`` path."""
    root = zip_path.parent
    gdb = root / "lion" / "lion.gdb"
    if gdb.exists():
        return gdb
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    log.info("extracting %s", zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(root)
    if not gdb.exists():
        cands = list(root.rglob("*.gdb"))
        if not cands:
            raise FileNotFoundError(f"no .gdb inside {zip_path}")
        return cands[0]
    return gdb


def load_lion_nodes(gdb: Path) -> pd.DataFrame:
    t0 = time.time()
    nodes = pyogrio.read_dataframe(str(gdb), layer="node")
    nodes = nodes.to_crs(NYC_TM)
    xy = shapely.get_coordinates(nodes.geometry.values)
    out = pd.DataFrame({
        "node_id": nodes["NODEID"].astype(np.int64).to_numpy(),
        "x": xy[:, 0],
        "y": xy[:, 1],
        "vintersect": nodes["VIntersect"].fillna("").astype(str).str.strip().ne("").to_numpy(),
    })
    out = out.drop_duplicates("node_id").reset_index(drop=True)
    log.info("LION nodes: %d in %.1fs", len(out), time.time() - t0)
    return out


def load_lion_segments(gdb: Path) -> pd.DataFrame:
    t0 = time.time()
    cols = ["PhysicalID", "SegmentID", "NodeIDFrom", "NodeIDTo", "NodeLevelF", "NodeLevelT", "Street", "SegmentTyp", "RB_Layer", "TrafDir", "FeatureTyp", "StreetCode", "LBoro", "RBoro"]
    df = pyogrio.read_dataframe(str(gdb), layer="lion", read_geometry=False, columns=cols)
    df = df[df["PhysicalID"].notna()].copy()
    df["PhysicalID"] = df["PhysicalID"].astype(np.int64)
    df["NodeIDFrom"] = pd.to_numeric(df["NodeIDFrom"], errors="coerce").fillna(-1).astype(np.int64)
    df["NodeIDTo"] = pd.to_numeric(df["NodeIDTo"], errors="coerce").fillna(-1).astype(np.int64)
    df["SegmentID"] = pd.to_numeric(df["SegmentID"], errors="coerce").fillna(-1).astype(np.int64)
    df["Street"] = df["Street"].fillna("").astype(str).str.strip()
    log.info("LION segments with PhysicalID: %d rows, %d physical ids in %.1fs", len(df), df["PhysicalID"].nunique(), time.time() - t0)
    return df.reset_index(drop=True)


def load_node_names(gdb: Path) -> pd.DataFrame:
    """node_id -> list of real street names meeting there (boundary/shoreline pseudo-names removed)."""
    ns = pyogrio.read_dataframe(str(gdb), layer="node_stname", read_geometry=False)
    ns["STNAME"] = ns["STNAME"].fillna("").astype(str).str.strip()
    ok = ns["STNAME"].ne("")
    for m in NON_STREET_NAME_MARKERS:
        ok &= ~ns["STNAME"].str.contains(m, regex=False)
    ns = ns[ok]
    ns["norm"] = ns["STNAME"].map(normalize)
    grp = ns.groupby("NODEID")
    out = pd.DataFrame({
        "node_id": np.fromiter(grp.groups.keys(), dtype=np.int64),
        "names": grp["STNAME"].agg(lambda s: sorted(set(s))).to_numpy(),
        "names_norm": grp["norm"].agg(lambda s: sorted(set(x for x in s if x))).to_numpy(),
    })
    return out


def assign_nodes(cscl: gpd.GeoDataFrame, lion_segs: pd.DataFrame, lion_nodes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (assignment, nodes).

    assignment: segment_id, from_node, to_node, from_source, to_source (0 lion by physicalid, 1 nearest
    lion node, 2 synthetic), from_dist, to_dist.
    nodes: node_id, x, y, vintersect, synthetic — LION nodes plus synthetic ones created for CSCL ends
    that have no LION node within tolerance.
    """
    t0 = time.time()
    node_xy = {int(n): (float(x), float(y)) for n, x, y in zip(lion_nodes["node_id"], lion_nodes["x"], lion_nodes["y"])}
    cand: dict[int, np.ndarray] = {}
    ls = lion_segs[(lion_segs["NodeIDFrom"] >= 0) & (lion_segs["NodeIDTo"] >= 0)]
    both = pd.concat([
        pd.DataFrame({"pid": ls["PhysicalID"].to_numpy(), "node": ls["NodeIDFrom"].to_numpy()}),
        pd.DataFrame({"pid": ls["PhysicalID"].to_numpy(), "node": ls["NodeIDTo"].to_numpy()}),
    ]).drop_duplicates()
    for pid, grp in both.groupby("pid")["node"]:
        cand[int(pid)] = grp.to_numpy()

    snapper = PointSnapper(lion_nodes[["x", "y"]].to_numpy(), lion_nodes["node_id"].to_numpy())
    coords = shapely.get_coordinates(cscl.geometry.values)
    n_per = shapely.get_num_coordinates(cscl.geometry.values)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    first = coords[starts]
    last = coords[starts + n_per - 1]

    n = len(cscl)
    from_node = np.full(n, -1, dtype=np.int64)
    to_node = np.full(n, -1, dtype=np.int64)
    from_src = np.full(n, 2, dtype=np.int8)
    to_src = np.full(n, 2, dtype=np.int8)
    from_dist = np.full(n, np.nan)
    to_dist = np.full(n, np.nan)
    seg_ids = cscl["segment_id"].to_numpy()

    for i in range(n):
        c = cand.get(int(seg_ids[i]))
        if c is None or len(c) == 0:
            continue
        pts = np.array([node_xy[int(k)] for k in c if int(k) in node_xy])
        if len(pts) == 0:
            continue
        ids = np.array([int(k) for k in c if int(k) in node_xy])
        d0 = np.hypot(pts[:, 0] - first[i, 0], pts[:, 1] - first[i, 1])
        d1 = np.hypot(pts[:, 0] - last[i, 0], pts[:, 1] - last[i, 1])
        j0, j1 = int(np.argmin(d0)), int(np.argmin(d1))
        if d0[j0] <= NODE_MATCH_TOL_M:
            from_node[i], from_src[i], from_dist[i] = ids[j0], 0, d0[j0]
        if d1[j1] <= NODE_MATCH_TOL_M:
            to_node[i], to_src[i], to_dist[i] = ids[j1], 0, d1[j1]

    # fallback 1: nearest LION node of any physicalid
    for arr, src, dist, pts in ((from_node, from_src, from_dist, first), (to_node, to_src, to_dist, last)):
        miss = arr < 0
        if miss.any():
            ids, d = snapper.snap(pts[miss], NODE_NEAREST_TOL_M)
            ok = ids >= 0
            idx = np.flatnonzero(miss)[ok]
            arr[idx] = ids[ok]
            src[idx] = 1
            dist[idx] = d[ok]

    # fallback 2: synthetic nodes (merged when coincident)
    synth: dict[tuple[int, int], int] = {}
    synth_rows: list[tuple[int, float, float]] = []
    next_id = SYNTHETIC_NODE_BASE
    for arr, src, dist, pts in ((from_node, from_src, from_dist, first), (to_node, to_src, to_dist, last)):
        for i in np.flatnonzero(arr < 0):
            key = (int(round(pts[i, 0] / SYNTH_MERGE_TOL_M)), int(round(pts[i, 1] / SYNTH_MERGE_TOL_M)))
            nid = synth.get(key)
            if nid is None:
                nid = next_id
                next_id += 1
                synth[key] = nid
                synth_rows.append((nid, float(pts[i, 0]), float(pts[i, 1])))
            arr[i] = nid
            src[i] = 2
            dist[i] = 0.0

    assignment = pd.DataFrame({
        "segment_id": seg_ids, "from_node": from_node, "to_node": to_node,
        "from_source": from_src, "to_source": to_src, "from_dist": from_dist, "to_dist": to_dist,
    })
    nodes = lion_nodes[["node_id", "x", "y", "vintersect"]].copy()
    nodes["synthetic"] = False
    if synth_rows:
        s = pd.DataFrame(synth_rows, columns=["node_id", "x", "y"])
        s["vintersect"] = False
        s["synthetic"] = True
        nodes = pd.concat([nodes, s], ignore_index=True)
    log.info("node assignment: %d ends by physicalid, %d by nearest node, %d synthetic (%d synthetic nodes) in %.1fs",
             int((from_src == 0).sum() + (to_src == 0).sum()), int((from_src == 1).sum() + (to_src == 1).sum()),
             int((from_src == 2).sum() + (to_src == 2).sum()), len(synth_rows), time.time() - t0)
    return assignment, nodes.reset_index(drop=True)


def compute_datum_shift(cscl: gpd.GeoDataFrame, assignment: pd.DataFrame, nodes: pd.DataFrame) -> tuple[float, float, float]:
    """Median (dx, dy) of CSCL end vertex minus matched LION node, plus the residual RMS after the shift.

    CSCL reaches NYC_TM through Socrata's WGS84 export; LION/DOT/planimetric feet data reach it through
    EPSG:2263 (NAD83). The two realisations differ by a near-constant vector (~0.9 m) over the city; every
    EPSG:2263-sourced coordinate is shifted by this vector so all layers share the CSCL/footprint frame.
    """
    nx = nodes.set_index("node_id")
    coords = shapely.get_coordinates(cscl.geometry.values)
    n_per = shapely.get_num_coordinates(cscl.geometry.values)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    first = coords[starts]
    m = (assignment["from_source"] == 0).to_numpy()
    if m.sum() < 100:
        return 0.0, 0.0, float("nan")
    fx = nx.loc[assignment["from_node"].to_numpy()[m], "x"].to_numpy()
    fy = nx.loc[assignment["from_node"].to_numpy()[m], "y"].to_numpy()
    dx = first[m, 0] - fx
    dy = first[m, 1] - fy
    sx, sy = float(np.median(dx)), float(np.median(dy))
    resid = float(np.sqrt(np.mean((dx - sx) ** 2 + (dy - sy) ** 2)))
    log.info("datum shift CSCL - LION: dx=%.3f m dy=%.3f m (residual rms %.3f m over %d ends)", sx, sy, resid, int(m.sum()))
    return sx, sy, resid


def node_positions_from_cscl(cscl: gpd.GeoDataFrame, assignment: pd.DataFrame, nodes: pd.DataFrame, shift: tuple[float, float]) -> pd.DataFrame:
    """Node coordinates = mean of the CSCL end vertices incident to the node (exact CSCL frame).

    Nodes with no CSCL end (LION-only) keep their LION position plus the datum shift.
    """
    coords = shapely.get_coordinates(cscl.geometry.values)
    n_per = shapely.get_num_coordinates(cscl.geometry.values)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    first = coords[starts]
    last = coords[starts + n_per - 1]
    ends = pd.DataFrame({
        "node_id": np.concatenate([assignment["from_node"].to_numpy(), assignment["to_node"].to_numpy()]),
        "x": np.concatenate([first[:, 0], last[:, 0]]),
        "y": np.concatenate([first[:, 1], last[:, 1]]),
    })
    mean_xy = ends.groupby("node_id")[["x", "y"]].mean()
    out = nodes.copy()
    out["x"] = out["x"] + shift[0]
    out["y"] = out["y"] + shift[1]
    idx = out["node_id"].map(mean_xy.index.get_indexer_for) if False else None  # placeholder-free explicit join below
    j = out.set_index("node_id")
    common = j.index.intersection(mean_xy.index)
    j.loc[common, "x"] = mean_xy.loc[common, "x"]
    j.loc[common, "y"] = mean_xy.loc[common, "y"]
    return j.reset_index()
