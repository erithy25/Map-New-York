"""segments.parquet + node table (DATA_CONTRACTS §7) from CSCL attributes, LION topology and the
supplementary real datasets (VZV speed limits, bike routes, bus lanes, truck routes, OSM surface tags,
DOT permit pavement records). Everything inferred is flagged in ``*_source`` columns.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from ..crs import NYC_TM, US_SURVEY_FOOT_M, stateplane_ft_to_tm
from . import schema as S
from .geom import heading_math, angle_diff
from .names import normalize

log = logging.getLogger("nycsim.roads.segments")

MPH_TO_MPS = 0.44704
DEFAULT_SPEED_BY_RW = {S.RW_HIGHWAY: 50, S.RW_RAMP: 30, S.RW_BRIDGE: 25, S.RW_TUNNEL: 35, S.RW_STREET: 25, S.RW_ALLEY: 15, S.RW_DRIVEWAY: 10, S.RW_UTURN: 15}
DEFAULT_WIDTH_BY_RW = {S.RW_STREET: 9.144, S.RW_HIGHWAY: 11.0, S.RW_BRIDGE: 11.0, S.RW_TUNNEL: 7.3, S.RW_BOARDWALK: 6.0, S.RW_PATH: 3.0, S.RW_STEP_STREET: 3.0, S.RW_DRIVEWAY: 3.7, S.RW_RAMP: 5.5, S.RW_ALLEY: 4.6, S.RW_UNKNOWN: 6.0, S.RW_NONPHYSICAL: 0.0, S.RW_UTURN: 5.5, S.RW_FERRY: 0.0}
PARKING_LANE_M = 2.4
BIKE_LANE_M = 1.5
OSM_SURFACE_MAP = {"sett": S.SURF_COBBLE, "cobblestone": S.SURF_COBBLE, "unhewn_cobblestone": S.SURF_COBBLE, "paving_stones": S.SURF_COBBLE, "cobblestone:flattened": S.SURF_COBBLE,
                   "concrete": S.SURF_CONCRETE, "concrete:plates": S.SURF_CONCRETE, "concrete:lanes": S.SURF_CONCRETE,
                   "metal_grid": S.SURF_STEEL, "metal": S.SURF_STEEL,
                   "gravel": S.SURF_GRAVEL, "unpaved": S.SURF_GRAVEL, "dirt": S.SURF_GRAVEL, "sand": S.SURF_GRAVEL, "ground": S.SURF_GRAVEL, "compacted": S.SURF_GRAVEL, "fine_gravel": S.SURF_GRAVEL, "earth": S.SURF_GRAVEL,
                   "wood": S.SURF_BOARDWALK}


def _read_geo(path: Path, columns: list[str] | None = None) -> gpd.GeoDataFrame:
    g = pyogrio.read_dataframe(str(path), columns=columns)
    return g.to_crs(NYC_TM)


def _segmentid_to_physical(lion_segs: pd.DataFrame) -> dict[int, int]:
    d = lion_segs[["SegmentID", "PhysicalID"]].drop_duplicates("SegmentID")
    return dict(zip(d["SegmentID"].astype(int), d["PhysicalID"].astype(int)))


def _ids_from_segmentid(series: pd.Series, seg2phys: dict[int, int]) -> np.ndarray:
    vals = pd.to_numeric(series, errors="coerce").fillna(-1).astype(int)
    return np.array([seg2phys.get(int(v), -1) for v in vals], dtype=np.int64)


def _nearest_segment_match(seg: gpd.GeoDataFrame, lines: gpd.GeoDataFrame, max_dist: float, max_angle: float, name_col: str | None = None) -> np.ndarray:
    """For each line in ``lines`` return the index (into ``seg``) of the CSCL segment whose geometry is within
    ``max_dist`` of the line midpoint, roughly parallel (``max_angle`` deg) and (optionally) same normalised
    name; -1 when none."""
    tree = shapely.STRtree(seg.geometry.values)
    mids = shapely.line_interpolate_point(lines.geometry.values, 0.5, normalized=True)
    idx_pairs = tree.query(shapely.buffer(mids, max_dist), predicate="intersects")
    out = np.full(len(lines), -1, dtype=np.int64)
    best = np.full(len(lines), np.inf)
    if idx_pairs.size == 0:
        return out
    li, si = idx_pairs
    dist = shapely.distance(mids[li], seg.geometry.values[si])
    # heading of line at midpoint vs segment heading at nearest point
    lc = shapely.get_coordinates(lines.geometry.values)
    ln = shapely.get_num_coordinates(lines.geometry.values)
    ls = np.concatenate([[0], np.cumsum(ln)[:-1]])
    lh = heading_math(lc[ls + ln - 1, 0] - lc[ls, 0], lc[ls + ln - 1, 1] - lc[ls, 1])
    sc = shapely.get_coordinates(seg.geometry.values)
    sn = shapely.get_num_coordinates(seg.geometry.values)
    ss = np.concatenate([[0], np.cumsum(sn)[:-1]])
    sh = heading_math(sc[ss + sn - 1, 0] - sc[ss, 0], sc[ss + sn - 1, 1] - sc[ss, 1])
    da = np.abs(angle_diff(lh[li], sh[si]))
    da = np.minimum(da, 180.0 - da)
    ok = (dist <= max_dist) & (da <= max_angle)
    if name_col is not None:
        ln_norm = lines[name_col].to_numpy()
        sn_norm = seg["name_norm"].to_numpy()
        ok &= ln_norm[li] == sn_norm[si]
    for l_i, s_i, d in zip(li[ok], si[ok], dist[ok]):
        if d < best[l_i]:
            best[l_i] = d
            out[l_i] = s_i
    return out


def build(cscl: gpd.GeoDataFrame, assignment: pd.DataFrame, nodes: pd.DataFrame, lion_segs: pd.DataFrame,
          node_names: pd.DataFrame, inputs, osm_ways: gpd.GeoDataFrame | None, shift: tuple[float, float],
          cache_dir: Path) -> tuple[gpd.GeoDataFrame, pd.DataFrame, dict]:
    """Return (segments GeoDataFrame with 3-D geometry, nodes DataFrame, stats)."""
    t0 = time.time()
    stats: dict = {}
    seg = cscl.merge(assignment[["segment_id", "from_node", "to_node", "from_source", "to_source"]], on="segment_id", how="left")
    seg = gpd.GeoDataFrame(seg, geometry="geometry", crs=NYC_TM)
    n = len(seg)
    rw = seg["rw_type"].to_numpy()
    tdir = seg["traffic_dir"].to_numpy()
    status_ok = seg["status"].to_numpy() == 2
    drivable = np.isin(rw, list(S.DRIVABLE_RW)) & (tdir != S.DIR_NONE) & status_ok

    # ---- width ----
    width = seg["width_m"].to_numpy(dtype=np.float64).copy()
    width_source = np.zeros(n, dtype=np.int8)
    miss = ~np.isfinite(width)
    width_source[miss] = 1
    default_w = np.array([DEFAULT_WIDTH_BY_RW.get(int(r), 6.0) for r in rw])
    width[miss] = default_w[miss]

    # ---- parking lanes ----
    park = seg["park_lanes_raw"].to_numpy().astype(np.int16).copy()
    park_inferred = park < 0
    inf_park = np.where(rw == S.RW_STREET, np.where(width >= 9.0, 2, np.where(width >= 6.5, 1, 0)), 0)
    park[park_inferred] = inf_park[park_inferred]
    park[~drivable] = 0

    # ---- travel lanes ----
    travel = seg["travel_lanes_raw"].to_numpy().astype(np.int16).copy()
    lanes_source = np.zeros(n, dtype=np.int8)
    tmiss = travel < 0
    lanes_source[tmiss | park_inferred] = 1
    hw_like = np.isin(rw, [S.RW_HIGHWAY, S.RW_RAMP, S.RW_BRIDGE, S.RW_TUNNEL])
    inf_travel = np.where(hw_like, np.maximum(1, np.round(width / 3.66)), np.maximum(1, np.floor((width - park * PARKING_LANE_M) / 3.2)))
    inf_travel = np.minimum(inf_travel, 6).astype(np.int16)
    travel[tmiss] = inf_travel[tmiss]
    travel[~drivable] = 0
    # a drivable segment with a real "0 travel lanes" value (27 streets) is still drivable: one lane
    zero_fix = drivable & (travel == 0)
    travel[zero_fix] = 1
    lanes_source[zero_fix] = 1
    total = seg["total_lanes_raw"].to_numpy().astype(np.int16).copy()
    total[total < 0] = (travel + park)[total < 0]
    total = np.maximum(total, travel + park)

    # ---- speed: CSCL -> VZV -> default ----
    speed = seg["posted_speed_raw"].to_numpy().astype(np.int16).copy()
    speed_source = np.zeros(n, dtype=np.int8)
    smiss = speed <= 0
    n_vzv = 0
    if inputs.has("vzv_speed_limits") and smiss.any():
        vz = pd.read_csv(inputs["vzv_speed_limits"], usecols=["the_geom", "street", "postvz_sl"])
        vz = vz[pd.to_numeric(vz["postvz_sl"], errors="coerce").fillna(0) > 0]
        vg = gpd.GeoDataFrame(vz, geometry=gpd.GeoSeries.from_wkt(vz["the_geom"]), crs="EPSG:4326").to_crs(NYC_TM)
        vg["name_norm"] = vg["street"].map(normalize)
        vg = vg[vg.geometry.length > 1.0].reset_index(drop=True)
        m = _nearest_segment_match(seg, vg, max_dist=6.0, max_angle=20.0, name_col="name_norm")
        ok = m >= 0
        vz_speed = pd.Series(pd.to_numeric(vg["postvz_sl"], errors="coerce").to_numpy()[ok]).groupby(m[ok]).agg(lambda s: s.mode().iloc[0])
        idx = vz_speed.index.to_numpy()
        fill = smiss[idx]
        speed[idx[fill]] = vz_speed.to_numpy()[fill].astype(np.int16)
        n_vzv = int(fill.sum())
        smiss = speed <= 0
    speed_source[smiss] = 1
    speed[smiss] = np.array([DEFAULT_SPEED_BY_RW.get(int(r), 25) for r in rw[smiss]], dtype=np.int16)
    speed[~drivable] = 0
    stats["speed_from_vzv"] = n_vzv

    seg2phys = _segmentid_to_physical(lion_segs)
    sid_index = pd.Index(seg["segment_id"].to_numpy())

    # ---- bike lanes ----
    bike = np.array([S.CSCL_BIKE_MAP.get(int(b), S.BIKE_NONE) for b in seg["bike_lane_raw"].to_numpy()], dtype=np.int8)
    n_bike_fill = 0
    if inputs.has("bike_routes"):
        br = pyogrio.read_dataframe(str(inputs["bike_routes"]), read_geometry=False, columns=["segmentid", "facilitycl", "ft_facilit", "tf_facilit", "onoffst", "status", "grnwy"])
        br = br[(br["status"].fillna("Current") == "Current") & (br["onoffst"].fillna("ON") == "ON")]
        pid = _ids_from_segmentid(br["segmentid"], seg2phys)
        cls = br["facilitycl"].fillna("").astype(str).to_numpy()
        fac = (br["ft_facilit"].fillna("") + " " + br["tf_facilit"].fillna("")).str.upper().to_numpy()
        enum = np.where(np.char.find(fac.astype(str), "GREENWAY") >= 0, S.BIKE_GREENWAY,
               np.where(cls == "I", S.BIKE_PROTECTED, np.where(cls == "II", S.BIKE_STANDARD, np.where(cls == "III", S.BIKE_SHARROW, S.BIKE_NONE))))
        pos = sid_index.get_indexer(pid)
        ok = (pos >= 0) & (enum > 0)
        for p, e in zip(pos[ok], enum[ok]):
            if bike[p] == S.BIKE_NONE:
                bike[p] = e
                n_bike_fill += 1
    stats["bike_filled_from_bike_routes"] = n_bike_fill

    # ---- bus lanes ----
    bus = np.zeros(n, dtype=bool)
    if inputs.has("bus_lanes"):
        bl = pyogrio.read_dataframe(str(inputs["bus_lanes"]), read_geometry=True)
        pid = _ids_from_segmentid(bl["segmentid"], seg2phys) if "segmentid" in bl.columns else np.full(len(bl), -1)
        pos = sid_index.get_indexer(pid)
        bus[pos[pos >= 0]] = True
        # rows whose LION segment id is unknown: geometric match
        un = pos < 0
        if un.any():
            blg = bl[un].to_crs(NYC_TM).reset_index(drop=True)
            blg = blg[blg.geometry.length > 1.0].reset_index(drop=True)
            m = _nearest_segment_match(seg, blg, max_dist=8.0, max_angle=20.0)
            bus[m[m >= 0]] = True
    stats["bus_lane_segments"] = int(bus.sum())

    # ---- truck routes ----
    truck = np.where(seg["truck_route_raw"].to_numpy() > 0, S.TRUCK_UNRESOLVED, S.TRUCK_NONE).astype(np.int8)
    if inputs.has("truck_routes"):
        tr = pyogrio.read_dataframe(str(inputs["truck_routes"]), read_geometry=False, columns=["segmentid", "routetype"])
        pid = _ids_from_segmentid(tr["segmentid"], seg2phys)
        rt = tr["routetype"].fillna("").str.upper().to_numpy()
        pos = sid_index.get_indexer(pid)
        ok = pos >= 0
        for p, t in zip(pos[ok], rt[ok]):
            if t.startswith("THROUGH"):
                truck[p] = S.TRUCK_THROUGH
            elif t.startswith("LOCAL") or t.startswith("LIMITED"):
                truck[p] = max(truck[p], S.TRUCK_LOCAL) if truck[p] != S.TRUCK_THROUGH else truck[p]
    stats["truck_route_segments"] = {int(k): int(v) for k, v in zip(*np.unique(truck, return_counts=True))}

    # ---- surface ----
    surface = np.zeros(n, dtype=np.int8)
    surface[rw == S.RW_BOARDWALK] = S.SURF_BOARDWALK
    n_osm_surface = 0
    if osm_ways is not None and len(osm_ways):
        ow = osm_ways[osm_ways["surface"].isin(list(OSM_SURFACE_MAP))].reset_index(drop=True)
        ow = ow[ow.geometry.length > 1.0].reset_index(drop=True)
        m = _nearest_segment_match(seg, ow, max_dist=6.0, max_angle=20.0)
        ok = m >= 0
        for s_i, sv in zip(m[ok], ow["surface"].to_numpy()[ok]):
            surface[s_i] = OSM_SURFACE_MAP[sv]
            n_osm_surface += 1
    stats["surface_from_osm"] = n_osm_surface
    n_permit_cobble = 0
    permits_cache = cache_dir / "permits_plates_pavement.parquet"
    if permits_cache.exists():
        pm = pd.read_parquet(permits_cache)
        pm = pm[(pm["PavementShortDesc"] == "COBBLESTONE") & pm["WKT"].notna()]
        if len(pm):
            g = gpd.GeoSeries.from_wkt(pm["WKT"].to_numpy(), crs="EPSG:2263").to_crs(NYC_TM)
            g = g.translate(shift[0], shift[1])
            pg = gpd.GeoDataFrame({"name_norm": pm["OnStreetName"].map(normalize).to_numpy()}, geometry=g.values, crs=NYC_TM)
            pg = pg[pg.geometry.geom_type.isin(["LineString", "MultiLineString"]) & (pg.geometry.length > 1.0)].reset_index(drop=True)
            pg["geometry"] = shapely.line_merge(pg.geometry.values)
            pg = pg[pg.geometry.geom_type == "LineString"].reset_index(drop=True)
            m = _nearest_segment_match(seg, pg, max_dist=8.0, max_angle=25.0, name_col="name_norm")
            ok = m >= 0
            for s_i in np.unique(m[ok]):
                if surface[s_i] == S.SURF_ASPHALT:
                    surface[s_i] = S.SURF_COBBLE
                    n_permit_cobble += 1
    stats["surface_cobble_from_permits"] = n_permit_cobble

    # ---- z from level codes ----
    lf = seg["level_from"].to_numpy()
    lt = seg["level_to"].to_numpy()
    zf = S.level_to_z(lf)
    zt = S.level_to_z(lt)
    z_source = np.where((lf == S.LEVEL_AT_GRADE) & (lt == S.LEVEL_AT_GRADE), S.Z_AT_GRADE, np.where(lf == lt, S.Z_LEVEL_CONST, S.Z_LEVEL_RAMP)).astype(np.int8)
    coords = shapely.get_coordinates(seg.geometry.values)
    n_per = shapely.get_num_coordinates(seg.geometry.values)
    starts = np.concatenate([[0], np.cumsum(n_per)[:-1]])
    seg_of = np.repeat(np.arange(n), n_per)
    d = np.diff(coords, axis=0)
    step = np.hypot(d[:, 0], d[:, 1])
    step = np.concatenate([[0.0], step])
    step[starts] = 0.0
    chain = np.cumsum(step)
    chain = chain - np.repeat(chain[starts], n_per)
    total_len = np.repeat(chain[starts + n_per - 1], n_per)
    frac = np.where(total_len > 0, chain / np.where(total_len > 0, total_len, 1.0), 0.0)
    z = zf[seg_of] * (1 - frac) + zt[seg_of] * frac
    xyz = np.column_stack([coords, z])
    geoms3 = shapely.linestrings(xyz, indices=seg_of)

    out = gpd.GeoDataFrame({
        "segment_id": seg["segment_id"].to_numpy(),
        "from_node": seg["from_node"].to_numpy(),
        "to_node": seg["to_node"].to_numpy(),
        "street_name": seg["street_name"].to_numpy(),
        "rw_type": rw.astype(np.int8),
        "traffic_dir": tdir.astype(np.int8),
        "travel_lanes": travel.astype(np.int8),
        "park_lanes": park.astype(np.int8),
        "total_lanes": total.astype(np.int8),
        "width_m": width.astype(np.float32),
        "posted_speed_mph": speed.astype(np.int8),
        "bike_lane": bike,
        "bus_lane": bus,
        "truck_route": truck,
        "level_from": lf.astype(np.int8),
        "level_to": lt.astype(np.int8),
        "surface": surface,
        "borough": seg["borough"].to_numpy().astype(np.int8),
        "speed_source": speed_source,
        "lanes_source": lanes_source,
        # ---- extension columns (documented in docs/verification/roads/REPORT.md) ----
        "width_source": width_source,
        "z_source": z_source,
        "z_from": zf.astype(np.float32),
        "z_to": zt.astype(np.float32),
        "drivable": drivable,
        "length_m": seg["length_m"].to_numpy().astype(np.float32),
        "name_norm": seg["name_norm"].to_numpy(),
        "status": seg["status"].to_numpy().astype(np.int8),
        "nonped": seg["nonped"].to_numpy(),
        "bike_trafdir": seg["bike_trafdir"].to_numpy(),
        "node_source": np.maximum(seg["from_source"].to_numpy(), seg["to_source"].to_numpy()).astype(np.int8),
    }, geometry=geoms3, crs=NYC_TM)

    # ---- nodes ----
    ends = pd.DataFrame({
        "node_id": np.concatenate([out["from_node"].to_numpy(), out["to_node"].to_numpy()]),
        "z": np.concatenate([zf, zt]),
        "drivable": np.concatenate([drivable, drivable]),
        "seg": np.concatenate([np.arange(n), np.arange(n)]),
    })
    g = ends.groupby("node_id")
    nd = pd.DataFrame({"node_id": g.size().index.to_numpy(), "degree": g.size().to_numpy().astype(np.int16),
                       "degree_drivable": g["drivable"].sum().to_numpy().astype(np.int16), "z": g["z"].mean().to_numpy().astype(np.float32)})
    nd = nd.merge(nodes[["node_id", "x", "y", "vintersect", "synthetic"]], on="node_id", how="left")
    # names: LION node_stname, fallback to incident segment names
    nn = node_names.set_index("node_id")
    seg_names = ends.assign(name=out["street_name"].to_numpy()[ends["seg"].to_numpy()], norm=out["name_norm"].to_numpy()[ends["seg"].to_numpy()])
    seg_names = seg_names[seg_names["name"] != ""]
    sn = seg_names.groupby("node_id").agg(names=("name", lambda s: sorted(set(s))), norms=("norm", lambda s: sorted(set(x for x in s if x))))
    names_out: list[list[str]] = []
    norms_out: list[list[str]] = []
    for nid in nd["node_id"].to_numpy():
        if nid in nn.index:
            names_out.append(list(nn.at[nid, "names"]))
            norms_out.append(list(nn.at[nid, "names_norm"]))
        elif nid in sn.index:
            names_out.append(list(sn.at[nid, "names"]))
            norms_out.append(list(sn.at[nid, "norms"]))
        else:
            names_out.append([])
            norms_out.append([])
    nd["names"] = names_out
    nd["names_norm"] = norms_out
    nd["intersection_name"] = [" & ".join(v[:2]) if len(v) >= 2 else (v[0] if v else "") for v in names_out]
    nd["x"] = nd["x"].astype(np.float64)
    nd["y"] = nd["y"].astype(np.float64)
    nd["vintersect"] = nd["vintersect"].fillna(False).astype(bool)
    nd["synthetic"] = nd["synthetic"].fillna(False).astype(bool)

    stats.update({
        "segments": int(n), "drivable_segments": int(drivable.sum()),
        "width_inferred": int(width_source.sum()), "lanes_inferred": int(lanes_source.sum()), "speed_inferred": int(speed_source.sum()),
        "z_at_grade": int((z_source == 0).sum()), "z_level_const": int((z_source == 1).sum()), "z_level_ramp": int((z_source == 2).sum()),
        "nodes": int(len(nd)), "nodes_synthetic": int(nd["synthetic"].sum()),
        "km_by_rw_type": {S.RW_NAMES.get(int(k), str(k)): round(float(v) / 1000.0, 2) for k, v in out.groupby("rw_type")["length_m"].sum().items()},
        "km_by_borough": {S.BOROUGH_NAMES.get(int(k), str(k)): round(float(v) / 1000.0, 2) for k, v in out.groupby("borough")["length_m"].sum().items()},
        "km_drivable_by_borough": {S.BOROUGH_NAMES.get(int(k), str(k)): round(float(v) / 1000.0, 2) for k, v in out[out["drivable"]].groupby("borough")["length_m"].sum().items()},
        "surface_counts": {int(k): int(v) for k, v in zip(*np.unique(surface, return_counts=True))},
        "bike_lane_counts": {int(k): int(v) for k, v in zip(*np.unique(bike, return_counts=True))},
    })
    log.info("segments built: %d (%d drivable), %d nodes in %.1fs", n, int(drivable.sum()), len(nd), time.time() - t0)
    return out, nd, stats
