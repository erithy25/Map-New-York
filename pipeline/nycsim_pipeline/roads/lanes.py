"""lanes.parquet: per-segment cross-section (travel, parking, bike, centre-turn lanes) with offset geometry.

Frame: the CSCL digitisation direction is "forward"; offsets are signed, positive to the right of forward.
US right-hand traffic: on two-way streets forward lanes lie right of the centreline (direction +1), backward
lanes left (direction -1). On one-way streets every lane carries the single legal direction.

Lane width = (width_m - parking*2.4 - bike*1.5) / travel_lanes clamped to [2.7, 3.7] m. Slack is given to the
parking lanes (<= 3.0 m each) and the rest is kept as curb margin; an over-allocated stack (clamp at 2.7 m on
a narrow street) is compressed uniformly so the lanes always fit the real curb-to-curb width.

lane_id = segment_id * 32 + (index_from_center + 16); index_from_center in [-15, 15], 0 for a lane centred on
the centreline (odd lane counts on one-way streets, the centre-turn lane on odd two-way counts).
"""
from __future__ import annotations

import logging
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from ..crs import NYC_TM
from . import schema as S
from .geom import offset_vectors

log = logging.getLogger("nycsim.roads.lanes")

LANE_ID_STRIDE = 32
LANE_ID_BIAS = 16
PARKING_W = 2.4
PARKING_W_MAX = 3.0
BIKE_W = 1.5
LANE_MIN, LANE_MAX = 2.7, 3.7
BIKE_SPEED_MPS = 4.5
PARKING_SPEED_MPS = 2.0
MPH_TO_MPS = 0.44704


def lane_id(segment_id: int | np.ndarray, index_from_center: int | np.ndarray) -> int | np.ndarray:
    return segment_id * LANE_ID_STRIDE + (index_from_center + LANE_ID_BIAS)


def cross_section(width: float, travel: int, park: int, traffic_dir: int, bike: int, bike_trafdir: str) -> list[dict]:
    """Ordered list (left curb -> right curb) of lane dicts: kind, direction, width, offset."""
    if travel <= 0 or traffic_dir == S.DIR_NONE:
        return []
    two_way = traffic_dir == S.DIR_TWO_WAY
    fwd = S.DIR_BACKWARD != traffic_dir  # one-way TF -> everything backward
    one_dir = 1 if (traffic_dir == S.DIR_FORWARD) else (-1 if traffic_dir == S.DIR_BACKWARD else 0)

    bike_takes_width = bike in (S.BIKE_PROTECTED, S.BIKE_STANDARD)
    bike_sides: list[int] = []      # -1 left side, +1 right side (digitisation frame)
    if bike_takes_width:
        bd = (bike_trafdir or "").upper()
        if two_way:
            if bd in ("TW", ""):
                bike_sides = [-1, 1]
            elif bd == "FT":
                bike_sides = [1]
            elif bd == "TF":
                bike_sides = [-1]
        else:
            # one-way: on the right of the travel direction (documented simplification; NYC also uses left-side lanes)
            bike_sides = [1] if one_dir == 1 else [-1]
    n_bike = len(bike_sides)

    park_sides: list[int] = []
    if park >= 2:
        park_sides = [-1, 1] * (park // 2)
    elif park == 1:
        park_sides = [1] if (two_way or one_dir == 1) else [-1]
    n_park = len(park_sides)

    lane_w = (width - n_park * PARKING_W - n_bike * BIKE_W) / travel
    lane_w = min(max(lane_w, LANE_MIN), LANE_MAX)
    park_w = PARKING_W
    used = travel * lane_w + n_park * park_w + n_bike * BIKE_W
    slack = width - used
    if slack > 0 and n_park:
        park_w = min(PARKING_W_MAX, PARKING_W + slack / n_park)
        used = travel * lane_w + n_park * park_w + n_bike * BIKE_W
        slack = width - used
    scale = 1.0
    if used > width + 1e-6:
        scale = width / used
        slack = 0.0
    margin = max(slack, 0.0) / 2.0

    # travel lane assignment
    if two_way:
        back = travel // 2
        forw = travel // 2
        center_turn = travel - back - forw          # 1 for odd counts
        if travel == 1:
            back, forw, center_turn = 1, 1, 0       # narrow two-way street: one lane each way (flagged by width)
    else:
        back = travel if one_dir == -1 else 0
        forw = travel if one_dir == 1 else 0
        center_turn = 0

    left: list[dict] = []
    right: list[dict] = []
    # curb -> centre ordering for each side
    left_dir = -1 if two_way else one_dir
    right_dir = 1 if two_way else one_dir
    for side, store, tdir in ((-1, left, left_dir), (1, right, right_dir)):
        n_p = park_sides.count(side)
        has_bike = side in bike_sides
        curb_items: list[dict] = []
        if has_bike and bike == S.BIKE_PROTECTED:
            curb_items.append({"kind": S.LANE_BIKE, "direction": tdir, "width": BIKE_W})
            curb_items += [{"kind": S.LANE_PARKING, "direction": tdir, "width": park_w} for _ in range(n_p)]
        else:
            curb_items += [{"kind": S.LANE_PARKING, "direction": tdir, "width": park_w} for _ in range(n_p)]
            if has_bike:
                curb_items.append({"kind": S.LANE_BIKE, "direction": tdir, "width": BIKE_W})
        store.extend(curb_items)
    if two_way:
        left += [{"kind": S.LANE_TRAVEL, "direction": -1, "width": lane_w} for _ in range(back)]
        right += [{"kind": S.LANE_TRAVEL, "direction": 1, "width": lane_w} for _ in range(forw)]
        center = [{"kind": S.LANE_TURN, "direction": 1, "width": lane_w}] if center_turn else []
        stack = left + center + list(reversed(right))
    else:
        nl = travel // 2
        nr = travel - nl
        # split travel lanes across the centreline; odd count -> the extra lane straddles the centreline
        left += [{"kind": S.LANE_TRAVEL, "direction": one_dir, "width": lane_w} for _ in range(nl)]
        right += [{"kind": S.LANE_TRAVEL, "direction": one_dir, "width": lane_w} for _ in range(nr)]
        stack = left + list(reversed(right))

    total_w = sum(l["width"] for l in stack) * scale
    pos = -total_w / 2.0
    for l in stack:
        w = l["width"] * scale
        l["width"] = w
        l["offset"] = pos + w / 2.0
        pos += w
    # margin is symmetric so offsets stay centred; nothing to add
    return stack


def build(segments: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    t0 = time.time()
    seg = segments
    geoms = seg.geometry.values
    coords = shapely.get_coordinates(geoms, include_z=True)
    n_per = shapely.get_num_coordinates(geoms)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])

    rows: list[tuple] = []
    lane_coords: list[np.ndarray] = []
    drivable = seg["drivable"].to_numpy()
    width = seg["width_m"].to_numpy()
    travel = seg["travel_lanes"].to_numpy()
    park = seg["park_lanes"].to_numpy()
    tdir = seg["traffic_dir"].to_numpy()
    bike = seg["bike_lane"].to_numpy()
    btd = seg["bike_trafdir"].to_numpy()
    speed = seg["posted_speed_mph"].to_numpy()
    sid = seg["segment_id"].to_numpy()
    n_compressed = 0
    n_narrow_two_way = 0
    for i in range(len(seg)):
        if not drivable[i]:
            continue
        stack = cross_section(float(width[i]), int(travel[i]), int(park[i]), int(tdir[i]), int(bike[i]), str(btd[i]))
        if not stack:
            continue
        c = coords[starts[i]: starts[i] + n_per[i]]
        if len(c) < 2:
            continue
        vec = offset_vectors(c)
        # index assignment: rank by offset; 0 for a lane straddling the centreline
        offs = np.array([l["offset"] for l in stack])
        widths = np.array([l["width"] for l in stack])
        straddle = np.abs(offs) < widths / 2.0 - 1e-6
        idx = np.zeros(len(stack), dtype=np.int64)
        r = 1
        for j in np.argsort(offs):
            if offs[j] > 0 and not straddle[j]:
                idx[j] = r
                r += 1
        r = -1
        for j in np.argsort(-offs):
            if offs[j] < 0 and not straddle[j]:
                idx[j] = r
                r -= 1
        if int(tdir[i]) == S.DIR_TWO_WAY and int(travel[i]) == 1:
            n_narrow_two_way += 1
        if sum(widths) > float(width[i]) + 1e-3:
            n_compressed += 1
        base_speed = float(speed[i]) * MPH_TO_MPS if speed[i] > 0 else 25 * MPH_TO_MPS
        for j, l in enumerate(stack):
            lid = int(lane_id(int(sid[i]), int(idx[j])))
            sp = base_speed if l["kind"] in (S.LANE_TRAVEL, S.LANE_TURN) else (BIKE_SPEED_MPS if l["kind"] == S.LANE_BIKE else PARKING_SPEED_MPS)
            rows.append((lid, int(sid[i]), int(idx[j]), int(l["direction"]), float(l["width"]), int(l["kind"]), float(sp), float(l["offset"])))
            lc = c.copy()
            lc[:, :2] = c[:, :2] + l["offset"] * vec
            lane_coords.append(lc)
    df = pd.DataFrame(rows, columns=["lane_id", "segment_id", "index_from_center", "direction", "width_m", "kind", "speed_mps", "offset_m"])
    if len(df) and df["lane_id"].duplicated().any():
        dups = df[df["lane_id"].duplicated(keep=False)]
        raise RuntimeError(f"duplicate lane ids generated, e.g. {dups.head(3).to_dict('records')}")
    counts = np.array([len(c) for c in lane_coords], dtype=np.int64)
    all_c = np.concatenate(lane_coords) if lane_coords else np.zeros((0, 3))
    idx = np.repeat(np.arange(len(lane_coords)), counts)
    geom = shapely.linestrings(all_c, indices=idx) if len(lane_coords) else np.array([], dtype=object)
    out = gpd.GeoDataFrame(df, geometry=geom, crs=NYC_TM)
    out["lane_id"] = out["lane_id"].astype(np.int64)
    out["segment_id"] = out["segment_id"].astype(np.int64)
    out["index_from_center"] = out["index_from_center"].astype(np.int8)
    out["direction"] = out["direction"].astype(np.int8)
    out["width_m"] = out["width_m"].astype(np.float32)
    out["kind"] = out["kind"].astype(np.int8)
    out["speed_mps"] = out["speed_mps"].astype(np.float32)
    out["offset_m"] = out["offset_m"].astype(np.float32)
    out["successors"] = [[] for _ in range(len(out))]
    out["predecessors"] = [[] for _ in range(len(out))]
    stats = {
        "lanes": int(len(out)),
        "lanes_by_kind": {int(k): int(v) for k, v in out["kind"].value_counts().items()},
        "lane_km_travel": round(float(out.loc[out["kind"].isin([S.LANE_TRAVEL, S.LANE_TURN]), "geometry"].length.sum()) / 1000.0, 2),
        "segments_with_lanes": int(out["segment_id"].nunique()),
        "stacks_compressed_to_width": n_compressed,
        "narrow_two_way_single_lane_segments": n_narrow_two_way,
        "lane_width_mean_m": round(float(out.loc[out["kind"] == S.LANE_TRAVEL, "width_m"].mean()), 3) if len(out) else 0.0,
    }
    log.info("lanes built: %d in %.1fs", len(out), time.time() - t0)
    return out, stats
