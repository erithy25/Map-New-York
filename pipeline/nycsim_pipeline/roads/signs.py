"""signs.parquet (DATA_CONTRACTS §7): every real DOT sign plus the regulatory and street-name signs that
NYC posts by law but does not publish as a point dataset.

Sources
* ``dot_signs`` (DOT Parking Regulation Locations and Signs, ``nfid-uabd``) — 440,540 *current* signs with a real
  State Plane position, the real NYC sign code, the real legend text, the real sheet size, the real arrow
  direction and the real support type. This dataset covers **parking/standing/stopping regulation and
  information signs only**: it contains no STOP, ONE WAY, DO NOT ENTER or SPEED LIMIT records (verified: 0 rows
  whose description matches ``ONE WAY``/``DO NOT ENTER``/``YIELD``; the 21,467 rows matching ``STOP`` are all
  "NO STOPPING"/"BUS STOP"). Those four regulatory families are therefore generated from the road network and
  the OSM sign nodes and carry ``source = 2`` (inferred position, real control).
* Street-name blades (``source = 1``) are generated at every intersection from the two real LION street names.

Sign face orientation: NYC parking regulation signs are mounted with the sign face parallel to the curb, so the
face normal points across the sidewalk into the roadway. ``facing_heading`` is therefore the compass heading
from the sign towards its projection on the centreline. Generated regulatory signs face oncoming traffic
(back along the approach); street-name blades face across the street they name.

Sheet size: the DOT ``sign_size`` string is ``HEIGHT X WIDTH`` in inches (anchor: the standard NYC parking sign
PS-1G "NO STANDING ANYTIME" is published as ``018 X 012`` and is really 12 in wide by 18 in high), or
``NN DIAMETER`` for round bus-stop signs.
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from ..crs import stateplane_ft_to_tm
from . import schema as S
from .geom import angle_diff, heading_math, math_to_compass
from .names import display

log = logging.getLogger("nycsim.roads.signs")

FT_M = 0.3048006096012192
INCH_M = 0.0254
SNAP_SEGMENT_M = 40.0
SNAP_NODE_M = 60.0
POLE_BOTTOM_M = 2.13          # MUTCD urban minimum mounting height (7 ft) to the bottom of the lowest sign
SIGN_GAP_M = 0.05
MAX_MOUNT_M = 4.20
CURB_OFFSET_M = 1.20          # sign pole set back from the curb line
BLADE_Z_M = 3.05              # street-name blade centre height
_SIZE_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(?:X|x)\s*([0-9]*\.?[0-9]+)\s*$")
_DIAM_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*DIAMETER\s*$", re.I)
_SUPERSEDES = re.compile(r"\s*\(SUPERSEDES[^)]*\)?\s*$", re.I)

SUPPORT_MAP = {
    "DR": S.SUPPORT_POLE, "SAME": S.SUPPORT_POLE, "POLE": S.SUPPORT_POLE, "BUSPOLE": S.SUPPORT_POLE,
    "BIDPOLE": S.SUPPORT_POLE, "WP": S.SUPPORT_POLE, "SNP": S.SUPPORT_POLE, "PS": S.SUPPORT_POLE,
    "S1A": S.SUPPORT_POLE, "PIG": S.SUPPORT_POLE, "NOTE": S.SUPPORT_POLE,
    "LP": S.SUPPORT_LAMP, "ELCOL": S.SUPPORT_LAMP,
    "TS": S.SUPPORT_SIGNAL_MAST, "VAB": S.SUPPORT_SIGNAL_MAST,
    "WALL": S.SUPPORT_WALL, "FENCE": S.SUPPORT_WALL, "BRIDG": S.SUPPORT_WALL, "COL": S.SUPPORT_WALL,
    "VENT": S.SUPPORT_WALL,
}
COMPASS = {"NORTH": 0.0, "EAST": 90.0, "SOUTH": 180.0, "WEST": 270.0}

# MUTCD family of a NYC DOT sign, decided from the code prefix and the legend text.
def mutcd_family(code: str, text: str) -> str:
    c = (code or "").upper()
    t = (text or "").upper()
    if c.startswith(("R1-", "R2-", "R3-", "R4-", "R5-", "R6-", "R7-", "R8-")):
        return c.split("-")[0]
    if c.startswith(("W1", "W2", "W3", "W4", "W8", "W13", "W14")):
        return "W"
    if c.startswith("SI"):
        return "I"
    if c.startswith(("PS", "SP", "SR", "SC", "SW", "S-", "SPECIAL", "INSERT", "RIDER", "NC")):
        if "BUS STOP" in t:
            return "R8"
        if "NO STANDING" in t or "NO STOPPING" in t or "NO PARKING" in t or "HMP" in t or "METER" in t or "PARKING" in t:
            return "R7"
        if "TRUCK" in t or "LOADING" in t or "TAXI" in t:
            return "R7"
        return "R7"
    if c.startswith("B"):
        return "B"
    if c.startswith("M"):
        return "M"
    return "other"


def parse_size(s: str) -> tuple[float, float]:
    """DOT ``sign_size`` -> (width_m, height_m). Returns (0, 0) for an unparseable/blank value."""
    if not s:
        return 0.0, 0.0
    m = _DIAM_RE.match(s)
    if m:
        d = float(m.group(1)) * INCH_M
        return d, d
    m = _SIZE_RE.match(s)
    if m:
        h = float(m.group(1)) * INCH_M
        w = float(m.group(2)) * INCH_M
        return w, h
    return 0.0, 0.0


def _clean_text(s: str) -> str:
    return _SUPERSEDES.sub("", str(s or "").strip()).strip()


class _SegmentFrame:
    """Vectorised access to segment geometry for snapping and end-of-segment placement."""

    def __init__(self, seg: gpd.GeoDataFrame) -> None:
        self.seg = seg
        self.geoms = seg.geometry.values
        self.tree = shapely.STRtree(self.geoms)
        self.coords = shapely.get_coordinates(self.geoms, include_z=True)
        self.n_per = shapely.get_num_coordinates(self.geoms)
        self.starts = np.concatenate([[0], np.cumsum(self.n_per)[:-1]])
        self.first = self.coords[self.starts]
        self.last = self.coords[self.starts + self.n_per - 1]

    def project(self, pts: np.ndarray, max_dist: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Nearest segment index, projected 3-D point, distance. index = -1 beyond ``max_dist``."""
        p = shapely.points(pts)
        idx = self.tree.nearest(p)
        idx = np.asarray(idx, dtype=np.int64)
        dist = shapely.distance(p, self.geoms[idx])
        s = shapely.line_locate_point(self.geoms[idx], p)
        proj = shapely.get_coordinates(shapely.line_interpolate_point(self.geoms[idx], s), include_z=True)
        idx = np.where(dist <= max_dist, idx, -1)
        return idx, proj, dist


def _stack_z(base_z: np.ndarray, heights: np.ndarray, group: np.ndarray) -> np.ndarray:
    """Vertical centre of each sign when several share a pole: stacked upwards from ``POLE_BOTTOM_M``."""
    order = np.lexsort((np.arange(len(group)), group))
    z = np.empty(len(group), dtype=np.float64)
    cur_group = -1
    cum = 0.0
    for i in order:
        if group[i] != cur_group:
            cur_group = group[i]
            cum = 0.0
        h = float(heights[i]) if heights[i] > 0 else 0.45
        centre = POLE_BOTTOM_M + cum + h / 2.0
        z[i] = base_z[i] + min(centre, MAX_MOUNT_M)
        cum += h + SIGN_GAP_M
    return z


def load_dot_signs(path: Path, shift: tuple[float, float]) -> pd.DataFrame:
    cols = ["order_number", "record_type", "borough", "on_street", "from_street", "to_street", "side_of_street",
            "sign_code", "sign_description", "sign_size", "sign_design_voided_on_date", "distance_from_intersection",
            "arrow_direction", "facing_direction", "support", "sign_x_coord", "sign_y_coord"]
    t0 = time.time()
    df = pd.read_csv(path, dtype=str, usecols=cols)
    n_all = len(df)
    df = df[df["record_type"].fillna("") == "Current"]
    x_ft = pd.to_numeric(df["sign_x_coord"], errors="coerce").to_numpy(dtype=np.float64)
    y_ft = pd.to_numeric(df["sign_y_coord"], errors="coerce").to_numpy(dtype=np.float64)
    ok = np.isfinite(x_ft) & np.isfinite(y_ft) & (x_ft > 800_000) & (y_ft > 100_000)
    df = df[ok].reset_index(drop=True)
    x, y = stateplane_ft_to_tm(x_ft[ok], y_ft[ok])
    df["x"] = np.asarray(x, dtype=np.float64) + shift[0]
    df["y"] = np.asarray(y, dtype=np.float64) + shift[1]
    df.attrs["rows_read"] = n_all
    df.attrs["rows_current_with_coords"] = len(df)
    log.info("DOT signs: %d rows, %d current with usable coordinates (%.1fs)", n_all, len(df), time.time() - t0)
    return df


def _dot_signs(df: pd.DataFrame, sf: _SegmentFrame, nodes: pd.DataFrame, seg: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict]:
    st: dict = {"rows_read": df.attrs.get("rows_read", len(df)), "rows_current_with_coords": len(df)}
    pts = df[["x", "y"]].to_numpy()
    idx, proj, dist = sf.project(pts, SNAP_SEGMENT_M)
    st["snapped_to_segment"] = int((idx >= 0).sum())
    st["median_snap_distance_m"] = round(float(np.median(dist)), 2)

    node_xy = nodes[["x", "y"]].to_numpy()
    from .geom import PointSnapper
    ns = PointSnapper(node_xy, nodes["node_id"].to_numpy())
    node_id, node_dist = ns.snap(pts, SNAP_NODE_M)
    st["snapped_to_node"] = int((node_id >= 0).sum())

    # a sign more than SNAP_SEGMENT_M from every centreline cannot be placed against a street in the scene
    # (private roads, marinas, airport aprons); it is dropped and counted rather than written with no anchor.
    placeable = idx >= 0
    st["dropped_no_segment_within_%dm" % int(SNAP_SEGMENT_M)] = int((~placeable).sum())
    if not placeable.all():
        df = df[placeable].reset_index(drop=True)
        pts, idx, proj, dist = pts[placeable], idx[placeable], proj[placeable], dist[placeable]
        node_id, node_dist = node_id[placeable], node_dist[placeable]
    st["rows_written"] = int(len(df))

    seg_ids = seg["segment_id"].to_numpy()
    segment_id = seg_ids[idx]

    # facing: from the sign towards the roadway centreline
    v = proj[:, :2] - pts
    d = np.hypot(v[:, 0], v[:, 1])
    fallback = d < 0.5
    if fallback.any():
        # degenerate (sign sits on the centreline): use the segment normal
        k = np.maximum(idx, 0)
        tang = sf.last[k, :2] - sf.first[k, :2]
        v[fallback] = np.stack([tang[fallback, 1], -tang[fallback, 0]], axis=1)
    facing_math = heading_math(v[:, 0], v[:, 1])
    facing = math_to_compass(facing_math)

    # arrows
    desc = df["sign_description"].fillna("").astype(str).str.upper().to_numpy()
    both = np.char.find(desc.astype(str), "<->") >= 0
    both |= np.array(["<--" in t and "-->" in t for t in desc])
    arrow_dir = df["arrow_direction"].fillna("").str.upper().map(COMPASS).to_numpy(dtype=np.float64)
    arrow = np.zeros(len(df), dtype=np.int8)
    have = np.isfinite(arrow_dir)
    left_h = (facing - 90.0) % 360.0
    right_h = (facing + 90.0) % 360.0
    dl = np.abs(angle_diff(left_h[have], arrow_dir[have]))
    dr = np.abs(angle_diff(right_h[have], arrow_dir[have]))
    arrow[np.flatnonzero(have)] = np.where(dl <= dr, S.ARROW_LEFT, S.ARROW_RIGHT).astype(np.int8)
    no_arrow_txt = ~have & (np.char.find(desc.astype(str), "-->") >= 0)
    arrow[no_arrow_txt] = S.ARROW_RIGHT
    no_arrow_txt2 = ~have & (arrow == 0) & (np.char.find(desc.astype(str), "<--") >= 0)
    arrow[no_arrow_txt2] = S.ARROW_LEFT
    arrow[both] = S.ARROW_BOTH

    sizes = np.array([parse_size(s) for s in df["sign_size"].fillna("").astype(str)], dtype=np.float64)
    w = sizes[:, 0]
    h = sizes[:, 1]
    unknown = (w <= 0) | (h <= 0)
    w[unknown] = 0.305           # NYC standard blank: 12 in x 18 in
    h[unknown] = 0.457
    st["size_defaulted"] = int(unknown.sum())

    support = df["support"].fillna("").str.upper().map(SUPPORT_MAP).fillna(S.SUPPORT_POLE).to_numpy().astype(np.int8)

    base_z = np.where(idx >= 0, proj[:, 2], 0.0)
    key = (np.round(df["x"].to_numpy() * 20).astype(np.int64) << 24) ^ np.round(df["y"].to_numpy() * 20).astype(np.int64)
    _, group = np.unique(key, return_inverse=True)
    z = _stack_z(base_z, h, group)
    st["distinct_poles"] = int(len(np.unique(group)))

    code = df["sign_code"].fillna("").astype(str).to_numpy()
    text = np.array([_clean_text(t) for t in df["sign_description"].fillna("").astype(str)])
    fam = np.array([mutcd_family(c, t) for c, t in zip(code, text)])
    voided = df["sign_design_voided_on_date"].fillna("").astype(str).str.strip().ne("").to_numpy()

    out = pd.DataFrame({
        "node_id": node_id.astype(np.int64),
        "segment_id": segment_id.astype(np.int64),
        "x": df["x"].to_numpy(), "y": df["y"].to_numpy(), "z": z.astype(np.float32),
        "ground_z": base_z.astype(np.float32),
        "facing_heading": facing.astype(np.float32),
        "mutcd_code": code, "text": text, "arrow": arrow,
        "sign_w_m": w.astype(np.float32), "sign_h_m": h.astype(np.float32),
        "support": support, "source": np.full(len(df), S.SIGN_SRC_DOT, dtype=np.int8),
        "mutcd_family": fam,
        "on_street": df["on_street"].fillna("").astype(str).map(display).to_numpy(),
        "side_of_street": df["side_of_street"].fillna("").astype(str).to_numpy(),
        "dot_order_number": df["order_number"].fillna("").astype(str).to_numpy(),
        "dot_distance_ft": pd.to_numeric(df["distance_from_intersection"], errors="coerce").fillna(-1).to_numpy().astype(np.float32),
        "design_voided": voided,
    })
    st["design_voided"] = int(voided.sum())
    st["by_family"] = {k: int(v) for k, v in pd.Series(fam).value_counts().items()}
    st["by_arrow"] = {int(k): int(v) for k, v in pd.Series(arrow).value_counts().items()}
    st["by_support"] = {int(k): int(v) for k, v in pd.Series(support).value_counts().items()}
    return out, st


def approach_frames(seg: gpd.GeoDataFrame) -> pd.DataFrame:
    """One row per (segment, end): node, point, outward math heading (pointing away from the node)."""
    from .geom import end_heading
    g = seg.geometry.values
    coords = shapely.get_coordinates(g, include_z=True)
    n_per = shapely.get_num_coordinates(g)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    n = len(seg)
    h_from = np.zeros(n)
    h_to = np.zeros(n)
    for i in range(n):
        c = coords[starts[i]: starts[i] + n_per[i]]
        if len(c) >= 2:
            h_from[i] = end_heading(c, at_end=False)                      # leaving the from_node
            h_to[i] = (end_heading(c, at_end=True) + 180.0) % 360.0       # leaving the to_node
    first = coords[starts]
    last = coords[starts + n_per - 1]
    base = {
        "segment_id": seg["segment_id"].to_numpy(), "width_m": seg["width_m"].to_numpy(),
        "traffic_dir": seg["traffic_dir"].to_numpy(), "rw_type": seg["rw_type"].to_numpy(),
        "street_name": seg["street_name"].to_numpy(), "name_norm": seg["name_norm"].to_numpy(),
        "posted_speed_mph": seg["posted_speed_mph"].to_numpy(), "speed_source": seg["speed_source"].to_numpy(),
        "drivable": seg["drivable"].to_numpy(),
    }
    a = pd.DataFrame({**base, "node_id": seg["from_node"].to_numpy(), "x": first[:, 0], "y": first[:, 1], "z": first[:, 2],
                      "heading_out": h_from, "at_from": True})
    b = pd.DataFrame({**base, "node_id": seg["to_node"].to_numpy(), "x": last[:, 0], "y": last[:, 1], "z": last[:, 2],
                      "heading_out": h_to, "at_from": False})
    return pd.concat([a, b], ignore_index=True)


def _place(x: float, y: float, heading_out_math: float, along: float, right: float) -> tuple[float, float]:
    """Point ``along`` metres from the node in the outward direction and ``right`` metres to the right of it."""
    t = np.radians(heading_out_math)
    tx, ty = np.cos(t), np.sin(t)
    rx, ry = ty, -tx
    return x + along * tx + right * rx, y + along * ty + right * ry


def _generated(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, approaches: pd.DataFrame,
               stop_approaches: dict[int, set[int]], yield_approaches: dict[int, set[int]]) -> tuple[pd.DataFrame, dict]:
    st: dict = {}
    rows: list[dict] = []
    node_i = nodes.set_index("node_id")
    deg = node_i["degree_drivable"]
    node_z = node_i["z"]
    node_names = dict(zip(nodes["node_id"].to_numpy(), nodes["names"].to_numpy()))
    ap = approaches[approaches["drivable"]].reset_index(drop=True)
    ap_by_node: dict[int, list[int]] = {}
    for i, nd in enumerate(ap["node_id"].to_numpy()):
        ap_by_node.setdefault(int(nd), []).append(i)

    ax = ap["x"].to_numpy(); ay = ap["y"].to_numpy(); az = ap["z"].to_numpy()
    ah = ap["heading_out"].to_numpy(); aw = ap["width_m"].to_numpy()
    asid = ap["segment_id"].to_numpy(); atd = ap["traffic_dir"].to_numpy(); aat = ap["at_from"].to_numpy()
    aname = ap["street_name"].to_numpy(); anorm = ap["name_norm"].to_numpy()
    aspd = ap["posted_speed_mph"].to_numpy(); aspsrc = ap["speed_source"].to_numpy()
    arw = ap["rw_type"].to_numpy()

    def half_width_at(node: int) -> float:
        idxs = ap_by_node.get(node, [])
        return float(max([aw[i] for i in idxs], default=9.0)) / 2.0

    # --- 1. street-name blades (source 1) -------------------------------------------------
    n_blade = 0
    for node, names in node_names.items():
        if len(names) < 2 or int(deg.get(node, 0)) < 3:
            continue
        idxs = ap_by_node.get(int(node), [])
        if not idxs:
            continue
        chosen: dict[str, int] = {}
        for i in idxs:
            key = anorm[i]
            if key and key not in chosen:
                chosen[key] = i
        if len(chosen) < 2:
            continue
        hw = half_width_at(int(node))
        for k, (key, i) in enumerate(sorted(chosen.items())[:2]):
            txt = str(aname[i])
            if not txt:
                continue
            # blade mounted on the corner pole, face normal across its own street
            px, py = _place(ax[i], ay[i], ah[i], hw + 1.0, hw + CURB_OFFSET_M)
            face = math_to_compass((ah[i] + 90.0) % 360.0)
            w = min(2.40, max(0.60, 0.085 * len(txt) + 0.20))
            rows.append(dict(node_id=int(node), segment_id=int(asid[i]), x=px, y=py, z=float(node_z.get(node, 0.0)) + BLADE_Z_M,
                             ground_z=float(node_z.get(node, 0.0)),
                             facing_heading=float(face), mutcd_code="D3-1", text=txt, arrow=S.ARROW_NONE,
                             sign_w_m=w, sign_h_m=0.229, support=S.SUPPORT_POLE, source=S.SIGN_SRC_STREETNAME,
                             mutcd_family="D3", on_street=txt, side_of_street="", dot_order_number="",
                             dot_distance_ft=-1.0, design_voided=False))
            n_blade += 1
    st["street_name_blades"] = n_blade

    # --- 2. STOP / YIELD (source 2; control is real, position is derived) ------------------
    n_stop = n_yield = 0
    for store, code, fam, size, counter in ((stop_approaches, "R1-1", "R1", 0.762, "stop"), (yield_approaches, "R1-2", "R1", 0.914, "yield")):
        for node, sids in store.items():
            idxs = ap_by_node.get(int(node), [])
            hw = half_width_at(int(node))
            for i in idxs:
                if int(asid[i]) not in sids:
                    continue
                # sign faces the driver arriving at the node along this leg
                px, py = _place(ax[i], ay[i], ah[i], hw + 1.5, aw[i] / 2.0 + CURB_OFFSET_M)
                face = math_to_compass(ah[i])
                rows.append(dict(node_id=int(node), segment_id=int(asid[i]), x=px, y=py,
                                 z=float(az[i]) + POLE_BOTTOM_M + size / 2.0, ground_z=float(az[i]), facing_heading=float(face),
                                 mutcd_code=code, text="STOP" if code == "R1-1" else "YIELD", arrow=S.ARROW_NONE,
                                 sign_w_m=size, sign_h_m=size, support=S.SUPPORT_POLE, source=S.SIGN_SRC_INFERRED,
                                 mutcd_family=fam, on_street=str(aname[i]), side_of_street="R", dot_order_number="",
                                 dot_distance_ft=-1.0, design_voided=False))
                if counter == "stop":
                    n_stop += 1
                else:
                    n_yield += 1
    st["stop_signs"] = n_stop
    st["yield_signs"] = n_yield

    # --- 3. ONE WAY and DO NOT ENTER on one-way streets ------------------------------------
    n_ow = n_dne = 0
    one_way = np.isin(atd, [S.DIR_FORWARD, S.DIR_BACKWARD]) & np.isin(arw, [S.RW_STREET, S.RW_ALLEY])
    for i in np.flatnonzero(one_way):
        node = int(ap["node_id"].to_numpy()[i])
        if int(deg.get(node, 0)) < 3:
            continue
        leaves = (atd[i] == S.DIR_FORWARD and aat[i]) or (atd[i] == S.DIR_BACKWARD and not aat[i])
        hw = half_width_at(node)
        if leaves:
            # ONE WAY blade at the corner, arrow pointing along the street away from the node
            px, py = _place(ax[i], ay[i], ah[i], hw + 1.0, aw[i] / 2.0 + CURB_OFFSET_M)
            face = math_to_compass((ah[i] + 90.0) % 360.0)
            rows.append(dict(node_id=node, segment_id=int(asid[i]), x=px, y=py, z=float(az[i]) + 2.44,
                             ground_z=float(az[i]), facing_heading=float(face), mutcd_code="R6-1", text="ONE WAY", arrow=S.ARROW_LEFT,
                             sign_w_m=0.914, sign_h_m=0.305, support=S.SUPPORT_POLE, source=S.SIGN_SRC_INFERRED,
                             mutcd_family="R6", on_street=str(aname[i]), side_of_street="R", dot_order_number="",
                             dot_distance_ft=-1.0, design_voided=False))
            n_ow += 1
        else:
            # traffic may not enter here: DO NOT ENTER facing the driver who would turn in
            px, py = _place(ax[i], ay[i], ah[i], hw + 1.5, aw[i] / 2.0 + CURB_OFFSET_M)
            face = math_to_compass(ah[i])
            rows.append(dict(node_id=node, segment_id=int(asid[i]), x=px, y=py, z=float(az[i]) + POLE_BOTTOM_M + 0.381,
                             ground_z=float(az[i]), facing_heading=float(face), mutcd_code="R5-1", text="DO NOT ENTER", arrow=S.ARROW_NONE,
                             sign_w_m=0.762, sign_h_m=0.762, support=S.SUPPORT_POLE, source=S.SIGN_SRC_INFERRED,
                             mutcd_family="R5", on_street=str(aname[i]), side_of_street="R", dot_order_number="",
                             dot_distance_ft=-1.0, design_voided=False))
            n_dne += 1
    st["one_way_signs"] = n_ow
    st["do_not_enter_signs"] = n_dne

    # --- 4. SPEED LIMIT where the real posted limit changes --------------------------------
    speed_by_node: dict[int, set[int]] = {}
    for i in range(len(ap)):
        if aspsrc[i] == 0 and aspd[i] > 0:
            speed_by_node.setdefault(int(ap["node_id"].to_numpy()[i]), set()).add(int(aspd[i]))
    n_speed = 0
    for i in range(len(ap)):
        if aspsrc[i] != 0 or aspd[i] <= 0:
            continue
        node = int(ap["node_id"].to_numpy()[i])
        others = speed_by_node.get(node, set()) - {int(aspd[i])}
        if not others:
            continue
        enters = (atd[i] == S.DIR_FORWARD and aat[i]) or (atd[i] == S.DIR_BACKWARD and not aat[i]) or atd[i] == S.DIR_TWO_WAY
        if not enters:
            continue
        hw = half_width_at(node)
        px, py = _place(ax[i], ay[i], ah[i], hw + 8.0, aw[i] / 2.0 + CURB_OFFSET_M)
        face = math_to_compass((ah[i] + 180.0) % 360.0)
        rows.append(dict(node_id=node, segment_id=int(asid[i]), x=px, y=py, z=float(az[i]) + POLE_BOTTOM_M + 0.381,
                         ground_z=float(az[i]), facing_heading=float(face), mutcd_code="R2-1", text=f"SPEED LIMIT {int(aspd[i])}", arrow=S.ARROW_NONE,
                         sign_w_m=0.610, sign_h_m=0.762, support=S.SUPPORT_POLE, source=S.SIGN_SRC_INFERRED,
                         mutcd_family="R2", on_street=str(aname[i]), side_of_street="R", dot_order_number="",
                         dot_distance_ft=-1.0, design_voided=False))
        n_speed += 1
    st["speed_limit_signs"] = n_speed

    if not rows:
        return pd.DataFrame(columns=["node_id", "segment_id", "x", "y", "z", "ground_z", "facing_heading", "mutcd_code", "text",
                                     "arrow", "sign_w_m", "sign_h_m", "support", "source", "mutcd_family", "on_street",
                                     "side_of_street", "dot_order_number", "dot_distance_ft", "design_voided"]), st
    df = pd.DataFrame(rows)
    for c, t in (("node_id", np.int64), ("segment_id", np.int64), ("x", np.float64), ("y", np.float64), ("z", np.float32), ("ground_z", np.float32),
                 ("facing_heading", np.float32), ("arrow", np.int8), ("sign_w_m", np.float32), ("sign_h_m", np.float32),
                 ("support", np.int8), ("source", np.int8), ("dot_distance_ft", np.float32), ("design_voided", bool)):
        df[c] = df[c].astype(t)
    return df, st


def build(seg: gpd.GeoDataFrame, nodes: pd.DataFrame, inputs, shift: tuple[float, float],
          stop_approaches: dict[int, set[int]], yield_approaches: dict[int, set[int]]) -> tuple[pd.DataFrame, dict]:
    """Return (signs DataFrame conforming to §7, stats)."""
    t0 = time.time()
    stats: dict = {}
    sf = _SegmentFrame(seg)
    parts: list[pd.DataFrame] = []
    if inputs.has("dot_signs"):
        raw = load_dot_signs(inputs["dot_signs"], shift)
        dot, stats["dot"] = _dot_signs(raw, sf, nodes, seg)
        del raw
        parts.append(dot)
    else:
        stats["dot"] = {"rows_read": 0, "note": "dot_signs input missing"}
    approaches = approach_frames(seg)
    gen, stats["generated"] = _generated(seg, nodes, approaches, stop_approaches, yield_approaches)
    if len(gen):
        parts.append(gen)
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    out.insert(0, "sign_id", np.arange(1, len(out) + 1, dtype=np.int64))
    out["node_id"] = out["node_id"].astype(np.int64)
    out["segment_id"] = out["segment_id"].astype(np.int64)
    out["mutcd_code"] = out["mutcd_code"].astype(str)
    out["text"] = out["text"].astype(str)
    out["mutcd_family"] = out["mutcd_family"].astype(str)
    stats["signs"] = int(len(out))
    stats["by_source"] = {int(k): int(v) for k, v in out["source"].value_counts().items()}
    stats["by_mutcd_family"] = {str(k): int(v) for k, v in out["mutcd_family"].value_counts().items()}
    log.info("signs: %d (%s) in %.1fs", len(out), stats["by_source"], time.time() - t0)
    return out, stats
