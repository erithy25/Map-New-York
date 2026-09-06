"""Vehicle volume -> density model.

1. Count sites are matched to CSCL segments (physicalid, else nearest segment with a street-name check).
2. Each site's hourly flow per travel lane is expressed as a *level* (weekday daily mean, veh/h/lane)
   and a normalised *profile* (hour × day type).
3. Segments are stratified by road class (highway/ramp, arterial >= 3 lanes, two-way street, one-way
   local). Profiles are pooled by area cluster (CBD, Manhattan, outer commercial, industrial,
   residential, special) with highways pooled separately; stratum level ratios are pooled by cluster.
4. NTA level per stratum: observed sites where available, else the NTA's reference level × cluster
   stratum ratio. Reference level of NTAs without any site is regressed on land use (PLUTO floor-area
   densities, lot-use mix) and road mix; the fit (R², leave-one-out R²) is reported.
5. NTA × hour × day type flow = lane-km weighted sum over strata; density from Greenshields with the
   stratum's lane-km weighted posted speed as free-flow speed and jam density 130 veh/km/lane.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import polars as pl

from .counts import CountData
from .geo import NtaTable
from .segments import MPH_TO_KMH, SegmentTable, normalize_street

log = logging.getLogger("nycsim.traffic.model")

JAM_DENSITY = 130.0             # veh/km/lane (7.7 m average headway at standstill, NYC mixed fleet)
STRATA = {0: "highway_ramp", 1: "arterial", 2: "two_way_street", 3: "one_way_local"}
CLUSTERS = ("cbd", "manhattan", "commercial", "industrial", "residential", "special")
CLUSTER_FALLBACK = {"cbd": "manhattan", "manhattan": "commercial", "commercial": "residential", "industrial": "residential",
                    "residential": "all", "special": "residential", "all": None}
MIN_SITES_FOR_PROFILE = 8
MIN_HOURS_FOR_PROFILE = 18
SHRINK_K = 1.0                  # pseudo-sites given to the regression estimate when blending with observed levels
DENSITY_FLOOR = 0.02            # veh/km/lane: never emit a perfectly empty NTA that has roads


# ----------------------------------------------------------------------------- Greenshields
def greenshields_density(q_veh_h_lane: np.ndarray, free_flow_kmh: np.ndarray | float, jam_density: float = JAM_DENSITY) -> np.ndarray:
    """Uncongested-branch density (veh/km/lane) for flow ``q`` under Greenshields v = vf (1 - k/kj).

    q = vf k (1 - k/kj)  =>  k = kj/2 (1 - sqrt(1 - q/qmax)),  qmax = vf kj / 4.  Flows above capacity
    are capped at capacity (k = kj/2)."""
    q = np.asarray(q_veh_h_lane, dtype=np.float64)
    vf = np.asarray(free_flow_kmh, dtype=np.float64)
    qmax = vf * jam_density / 4.0
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(qmax > 0, q / qmax, 0.0)
    r = np.clip(r, 0.0, 1.0)
    return jam_density / 2.0 * (1.0 - np.sqrt(1.0 - r))


def greenshields_speed(density: np.ndarray, free_flow_kmh: np.ndarray | float, jam_density: float = JAM_DENSITY) -> np.ndarray:
    k = np.clip(np.asarray(density, dtype=np.float64), 0, jam_density)
    return np.asarray(free_flow_kmh, dtype=np.float64) * (1.0 - k / jam_density)


# ----------------------------------------------------------------------------- strata / clusters
def stratum_of(rw_type: np.ndarray, travel_lanes: np.ndarray, trafdir: np.ndarray) -> np.ndarray:
    rw = np.asarray(rw_type)
    ln = np.asarray(travel_lanes)
    two_way = np.asarray(trafdir) == "TW"
    s = np.full(len(rw), 2, dtype=np.int8)
    s[(rw == 2) | (rw == 9)] = 0
    art = (s != 0) & (ln >= 3)
    s[art] = 1
    one = (s == 2) & (~two_way) & (ln <= 2)
    s[one] = 3
    return s


def cluster_of(nta: NtaTable, landuse: pl.DataFrame) -> np.ndarray:
    """Area-type cluster per NTA (see module docstring)."""
    lu = landuse.sort("nta_idx")
    res = lu["res_m2"].to_numpy()
    com = (lu["com_m2"].to_numpy() + lu["office_m2"].to_numpy() + lu["retail_m2"].to_numpy())
    ind_share = lu["lot_share_ind"].to_numpy()
    com_ratio = com / np.maximum(res + com, 1.0)
    out = np.array(["residential"] * len(nta), dtype=object)
    out[com_ratio >= 0.35] = "commercial"
    out[(ind_share >= 0.25) & (com_ratio < 0.35)] = "industrial"
    out[nta.borocode == 1] = "manhattan"
    out[nta.is_cbd] = "cbd"
    out[nta.is_special] = "special"
    return out


# ----------------------------------------------------------------------------- site matching
@dataclass
class MatchedSites:
    df: pl.DataFrame            # segment_id, seg_row, physicalid, nta_idx, stratum, travel_lanes, trafdir, lane_km, free_flow_kmh, match, dist_m
    n_by_match: dict[str, int] = field(default_factory=dict)


def match_sites(cd: CountData, seg: SegmentTable) -> MatchedSites:
    sites = cd.sites.filter(pl.col("x").is_not_null() & pl.col("y").is_not_null())
    x, y = sites["x"].to_numpy(), sites["y"].to_numpy()
    seg_ids = sites["segment_id"].to_numpy()
    streets = [normalize_street(s) for s in sites["street"].to_list()]
    seg_norm = seg.df["street_norm"].to_list()
    rows = np.full(len(sites), -1, dtype=np.int64)
    dist = np.full(len(sites), np.nan)
    match = np.array(["none"] * len(sites), dtype=object)
    import shapely
    pts = shapely.points(x, y)
    # 1) physicalid match, validated by proximity (ATR points are placed on the counted block)
    for i, sid in enumerate(seg_ids.tolist()):
        r = seg.phys_index.get(int(sid))
        if r is not None:
            d = float(shapely.distance(pts[i], seg.geoms[r]))
            if d <= 150.0:
                rows[i], dist[i], match[i] = r, d, "physicalid"
    # 2) spatial: nearest few segments within 60 m, prefer same street name
    todo = np.flatnonzero(rows < 0)
    if len(todo):
        cand_i, cand_g = seg.tree.query(pts[todo], predicate="dwithin", distance=60.0)
        cand_d = shapely.distance(pts[todo][cand_i], seg.geoms[cand_g])
        by_site: dict[int, list[tuple[float, int]]] = {}
        for ci, cg, cdst in zip(cand_i.tolist(), cand_g.tolist(), cand_d.tolist()):
            by_site.setdefault(ci, []).append((cdst, cg))
        for ci, lst in by_site.items():
            i = int(todo[ci])
            lst.sort()
            name = streets[i]
            chosen = None
            for cdst, cg in lst:
                sn = seg_norm[cg]
                if name and sn and (name == sn or name in sn or sn in name):
                    chosen = (cdst, cg, "spatial_name")
                    break
            if chosen is None and lst[0][0] <= 25.0:
                chosen = (lst[0][0], lst[0][1], "spatial_nearest")
            if chosen is not None:
                dist[i], rows[i], match[i] = chosen
    ok = rows >= 0
    sd = seg.df
    out = sites.with_columns(pl.Series("seg_row", rows), pl.Series("dist_m", dist), pl.Series("match", match)).filter(pl.Series(ok))
    r = out["seg_row"].to_numpy()
    out = out.with_columns(
        pl.Series("physicalid", sd["physicalid"].to_numpy()[r]),
        pl.Series("nta_idx", sd["nta_idx"].to_numpy()[r]),
        pl.Series("travel_lanes", sd["travel_lanes"].to_numpy()[r]),
        pl.Series("trafdir", np.asarray(sd["trafdir"].to_list(), dtype=object)[r].tolist()),
        pl.Series("lane_km", sd["lane_km"].to_numpy()[r]),
        pl.Series("free_flow_kmh", sd["free_flow_kmh"].to_numpy()[r]),
        pl.Series("rw_type", sd["rw_type"].to_numpy()[r]),
    )
    out = out.with_columns(pl.Series("stratum", stratum_of(out["rw_type"].to_numpy(), out["travel_lanes"].to_numpy(), np.asarray(out["trafdir"].to_list()))))
    out = out.filter(pl.col("nta_idx") >= 0)
    counts = {k: int(v) for k, v in zip(*np.unique(match, return_counts=True))}
    counts["none"] = int((~ok).sum())
    log.info("site matching: %s (%d sites usable)", counts, out.height)
    return MatchedSites(out, counts)


# ----------------------------------------------------------------------------- site levels & profiles
@dataclass
class SiteModel:
    sites: pl.DataFrame                 # matched sites + level (veh/h/lane weekday daily mean) + n_hours_wd
    q: np.ndarray                       # (n_sites, 24, 3) flow per lane, NaN where unobserved
    n_days: np.ndarray                  # (n_sites, 24, 3)
    profiles: dict[str, np.ndarray]     # key -> (24, 3) normalised (weekday daily mean = 1)
    profile_n: dict[str, int]
    stratum_ratio: dict[str, np.ndarray]  # cluster -> ratio per stratum vs two-way street level
    dir_doubled: int


def _weighted_profile(qn: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted mean of normalised site profiles ignoring NaNs; returns (24, 3)."""
    ww = np.where(np.isfinite(qn), w[:, None, None], 0.0)
    num = np.nansum(qn * ww, axis=0)
    den = ww.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def _fill_profile(p: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    out = p.copy()
    bad = ~np.isfinite(out)
    out[bad] = fallback[bad]
    return out


def build_site_model(cd: CountData, ms: MatchedSites, clusters: np.ndarray) -> SiteModel:
    sites = ms.df
    sid_to_row = {int(s): i for i, s in enumerate(sites["segment_id"].to_list())}
    n = sites.height
    q = np.full((n, 24, 3), np.nan)
    nd = np.zeros((n, 24, 3), dtype=np.int32)
    lanes = sites["travel_lanes"].to_numpy().astype(np.float64)
    two_way = np.asarray(sites["trafdir"].to_list()) == "TW"
    fl = cd.flows.filter(pl.col("segment_id").is_in(list(sid_to_row)))
    rows = np.array([sid_to_row[int(s)] for s in fl["segment_id"].to_list()], dtype=np.int64)
    hh = fl["hour"].to_numpy().astype(int)
    dd = fl["dow"].to_numpy().astype(int)
    veh = fl["veh_h"].to_numpy().astype(np.float64)
    ndir = fl["n_dir"].to_numpy().astype(int)
    # a two-way segment counted in one direction only: assume directional symmetry (flagged)
    dbl = two_way[rows] & (ndir == 1)
    veh = np.where(dbl, veh * 2.0, veh)
    q[rows, hh, dd] = veh / lanes[rows]
    nd[rows, hh, dd] = fl["n_days"].to_numpy()
    # weekday level & normalised profile
    wd = q[:, :, 0]
    n_hours_wd = np.isfinite(wd).sum(axis=1)
    level = np.where(n_hours_wd >= MIN_HOURS_FOR_PROFILE, np.nanmean(wd, axis=1), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        qn = q / level[:, None, None]
    stratum = sites["stratum"].to_numpy()
    site_cluster = clusters[sites["nta_idx"].to_numpy()]
    w = np.sqrt(np.maximum(nd[:, :, 0].sum(axis=1), 1.0)) * sites["weight"].to_numpy() if "weight" in sites.columns else np.ones(n)
    # profiles: 'all', 'highway', and per cluster (non-highway sites)
    valid = np.isfinite(level)
    profiles: dict[str, np.ndarray] = {}
    profile_n: dict[str, int] = {}
    sel_all = valid & (stratum != 0)
    p_all = _weighted_profile(qn[sel_all], w[sel_all])
    p_all = np.where(np.isfinite(p_all), p_all, 1.0)
    profiles["all"], profile_n["all"] = p_all, int(sel_all.sum())
    sel_h = valid & (stratum == 0)
    if sel_h.sum() >= MIN_SITES_FOR_PROFILE:
        profiles["highway"] = _fill_profile(_weighted_profile(qn[sel_h], w[sel_h]), p_all)
    else:
        profiles["highway"] = p_all
    profile_n["highway"] = int(sel_h.sum())
    for c in CLUSTERS:
        sel = valid & (stratum != 0) & (site_cluster == c)
        profile_n[c] = int(sel.sum())
    for c in CLUSTERS:
        sel = valid & (stratum != 0) & (site_cluster == c)
        if sel.sum() >= MIN_SITES_FOR_PROFILE:
            profiles[c] = _fill_profile(_weighted_profile(qn[sel], w[sel]), p_all)
        else:
            fb = CLUSTER_FALLBACK[c]
            while fb is not None and fb not in profiles and profile_n.get(fb, 0) < MIN_SITES_FOR_PROFILE:
                fb = CLUSTER_FALLBACK[fb]
            if fb is None or fb == "all":
                profiles[c] = p_all
            else:
                selfb = valid & (stratum != 0) & (site_cluster == fb)
                profiles[c] = _fill_profile(_weighted_profile(qn[selfb], w[selfb]), p_all)
            log.info("profile for cluster %s pooled from %s (%d own sites)", c, fb or "all", int(sel.sum()))
    # renormalise so that the weekday daily mean is exactly 1
    for k, p in profiles.items():
        m = np.nanmean(p[:, 0])
        profiles[k] = p / m if m > 0 else p
    # stratum level ratios per cluster (vs two-way street stratum), lane-km weighted means of site levels
    ratio: dict[str, np.ndarray] = {}
    lane_w = sites["lane_km"].to_numpy()

    def _lvl(sel: np.ndarray) -> float:
        ww = lane_w[sel] * w[sel]
        return float(np.sum(level[sel] * ww) / np.sum(ww)) if sel.any() and ww.sum() > 0 else np.nan

    glob = np.array([_lvl(valid & (stratum == s)) for s in range(4)])
    glob_ref = glob[2] if np.isfinite(glob[2]) else np.nanmean(glob)
    glob_ratio = np.where(np.isfinite(glob), glob / glob_ref, 1.0)
    for c in CLUSTERS + ("all",):
        sel_c = valid if c == "all" else valid & (site_cluster == c)
        lv = np.array([_lvl(sel_c & (stratum == s)) for s in range(4)])
        cnt = np.array([int((sel_c & (stratum == s)).sum()) for s in range(4)])
        ref = lv[2] if (np.isfinite(lv[2]) and cnt[2] >= 5) else np.nan
        r = np.full(4, np.nan)
        if np.isfinite(ref):
            for s in range(4):
                if cnt[s] >= 5 and np.isfinite(lv[s]):
                    r[s] = lv[s] / ref
        r = np.where(np.isfinite(r), r, glob_ratio)
        r[2] = 1.0
        ratio[c] = r
    sites = sites.with_columns(pl.Series("level", level), pl.Series("n_hours_wd", n_hours_wd.astype(np.int32)),
                               pl.Series("cluster", site_cluster.tolist()))
    log.info("site model: %d sites, %d with a weekday level; %d segment-hours direction-doubled; profile sites %s; stratum ratios(all)=%s",
             n, int(valid.sum()), int(dbl.sum()), profile_n, np.round(ratio["all"], 2).tolist())
    return SiteModel(sites, q, nd, profiles, profile_n, ratio, int(dbl.sum()))


# ----------------------------------------------------------------------------- land-use regression
@dataclass
class Regression:
    feature_names: list[str]
    beta: np.ndarray
    mu: np.ndarray
    sd: np.ndarray
    r2: float
    r2_loo: float
    n: int
    rmse_log: float
    ridge: float

    def predict(self, X: np.ndarray) -> np.ndarray:
        Z = (X - self.mu) / self.sd
        return np.column_stack([np.ones(len(Z)), Z]) @ self.beta


def design_matrix(nta: NtaTable, landuse: pl.DataFrame, roads: pl.DataFrame) -> tuple[np.ndarray, list[str]]:
    lu = landuse.sort("nta_idx")
    rd = roads.sort("nta_idx")
    area = np.maximum(nta.area_km2, 0.05)
    land_m2 = area * 1e6
    f = {
        "log_res_far": np.log1p(lu["res_m2"].to_numpy() / land_m2 * 10),
        "log_com_far": np.log1p(lu["com_m2"].to_numpy() / land_m2 * 10),
        "log_office_far": np.log1p(lu["office_m2"].to_numpy() / land_m2 * 10),
        "log_retail_far": np.log1p(lu["retail_m2"].to_numpy() / land_m2 * 100),
        "log_ind_far": np.log1p(lu["ind_m2"].to_numpy() / land_m2 * 100),
        "log_units_km2": np.log1p(lu["units"].to_numpy() / area / 100),
        "lot_share_open": lu["lot_share_open"].to_numpy(),
        "lot_share_vacant_parking": lu["lot_share_vacant"].to_numpy() + lu["lot_share_parking"].to_numpy(),
        "log_lane_km_density": np.log1p(rd["lane_km_density"].to_numpy()),
        "highway_lane_share": rd["highway_lane_share"].to_numpy(),
        "arterial_lane_share": rd["arterial_lane_share"].to_numpy(),
        "truck_route_share": rd["truck_route_share"].to_numpy(),
        "is_manhattan": (nta.borocode == 1).astype(np.float64),
        "is_staten_island": (nta.borocode == 5).astype(np.float64),
    }
    names = list(f)
    return np.column_stack([f[k] for k in names]), names


def fit_regression(X: np.ndarray, y: np.ndarray, w: np.ndarray, names: list[str], ridge: float = 1.0) -> Regression:
    """Weighted ridge regression on standardised features with leave-one-out R²."""
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    p = Z.shape[1]
    R = np.eye(p) * ridge
    R[0, 0] = 0.0
    W = np.sqrt(w)[:, None]
    A = (Z * W).T @ (Z * W) + R
    b = (Z * W).T @ (y * W[:, 0])
    beta = np.linalg.solve(A, b)
    yhat = Z @ beta
    ybar = np.average(y, weights=w)
    ss_tot = np.sum(w * (y - ybar) ** 2)
    ss_res = np.sum(w * (y - yhat) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    # leave-one-out via the hat matrix of the weighted ridge problem
    Ainv = np.linalg.inv(A)
    h = np.einsum("ij,jk,ik->i", Z * W, Ainv, Z * W)
    loo_res = (y - yhat) / np.maximum(1.0 - h, 1e-6)
    r2_loo = 1.0 - np.sum(w * loo_res ** 2) / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(np.sum(w * (y - yhat) ** 2) / np.sum(w)))
    return Regression(names, beta, mu, sd, float(r2), float(r2_loo), int(len(y)), rmse, ridge)


# ----------------------------------------------------------------------------- NTA assembly
@dataclass
class VolumeResult:
    q_lane: np.ndarray            # (n_nta, 24, 3) flow veh/h/lane, lane-km weighted over strata
    density: np.ndarray           # (n_nta, 24, 3) veh/km/lane
    level_ref: np.ndarray         # (n_nta,) reference-stratum weekday level used
    level_ref_obs: np.ndarray     # (n_nta,) observed reference level (NaN when no site)
    level_ref_pred: np.ndarray    # (n_nta,) regression prediction
    n_sites: np.ndarray           # (n_nta,)
    n_sites_recent: np.ndarray
    source: np.ndarray            # (n_nta,) object str
    clusters: np.ndarray
    regression: Regression
    lane_km_strata: np.ndarray    # (n_nta, 4)
    vf_strata: np.ndarray         # (n_nta, 4) km/h
    veh_km_h: np.ndarray          # (n_nta, 24, 3) vehicle-km per hour in the NTA (flow × lane-km)


def nta_strata(seg: SegmentTable, nta: NtaTable) -> tuple[np.ndarray, np.ndarray]:
    d = seg.df.filter(pl.col("nta_idx") >= 0)
    s = stratum_of(d["rw_type"].to_numpy(), d["travel_lanes"].to_numpy(), np.asarray(d["trafdir"].to_list()))
    idx = d["nta_idx"].to_numpy().astype(int)
    lk = d["lane_km"].to_numpy()
    vf = d["free_flow_kmh"].to_numpy()
    lane_km = np.zeros((len(nta), 4))
    vfw = np.zeros((len(nta), 4))
    np.add.at(lane_km, (idx, s), lk)
    np.add.at(vfw, (idx, s), lk * vf)
    with np.errstate(invalid="ignore", divide="ignore"):
        vf_s = np.where(lane_km > 0, vfw / lane_km, 25 * MPH_TO_KMH)
    return lane_km, vf_s


def assemble_volumes(nta: NtaTable, seg: SegmentTable, sm: SiteModel, landuse: pl.DataFrame, roads: pl.DataFrame,
                     clusters: np.ndarray) -> VolumeResult:
    n = len(nta)
    lane_km, vf_s = nta_strata(seg, nta)
    sites = sm.sites.filter(pl.col("level").is_not_null() & pl.col("level").is_finite())
    s_nta = sites["nta_idx"].to_numpy().astype(int)
    s_str = sites["stratum"].to_numpy().astype(int)
    s_lvl = sites["level"].to_numpy()
    s_w = sites["lane_km"].to_numpy() * np.where(sites["tier"].to_numpy() == "recent", 1.0, 0.6) * np.sqrt(np.maximum(sites["n_hours_wd"].to_numpy(), 1))
    s_recent = sites["tier"].to_numpy() == "recent"
    # observed level per NTA × stratum, and reference level (normalised to stratum 2 via cluster ratios)
    lvl_obs = np.full((n, 4), np.nan)
    num = np.zeros((n, 4))
    den = np.zeros((n, 4))
    np.add.at(num, (s_nta, s_str), s_lvl * s_w)
    np.add.at(den, (s_nta, s_str), s_w)
    with np.errstate(invalid="ignore", divide="ignore"):
        lvl_obs = np.where(den > 0, num / den, np.nan)
    ref_num = np.zeros(n)
    ref_den = np.zeros(n)
    for i in range(len(sites)):
        r = sm.stratum_ratio.get(clusters[s_nta[i]], sm.stratum_ratio["all"])[s_str[i]]
        ref_num[s_nta[i]] += s_lvl[i] / max(r, 1e-3) * s_w[i]
        ref_den[s_nta[i]] += s_w[i]
    with np.errstate(invalid="ignore", divide="ignore"):
        level_ref_obs = np.where(ref_den > 0, ref_num / ref_den, np.nan)
    n_sites = np.bincount(s_nta, minlength=n)
    n_sites_recent = np.bincount(s_nta[s_recent], minlength=n)
    # regression on NTAs with observed reference level and roads
    X, names = design_matrix(nta, landuse, roads)
    obs = np.isfinite(level_ref_obs) & (level_ref_obs > 0) & (lane_km.sum(axis=1) > 0)
    w = np.sqrt(n_sites[obs].astype(np.float64))
    reg = fit_regression(X[obs], np.log(level_ref_obs[obs]), w, names)
    level_ref_pred = np.exp(reg.predict(X))
    lo, hi = np.percentile(level_ref_obs[obs], [2, 98])
    level_ref_pred = np.clip(level_ref_pred, lo * 0.5, hi * 1.2)
    log.info("regression: n=%d R²=%.3f LOO-R²=%.3f rmse(log)=%.3f", reg.n, reg.r2, reg.r2_loo, reg.rmse_log)
    # blended reference level (shrink few-site NTAs toward the regression)
    ns = n_sites.astype(np.float64)
    level_ref = np.where(obs, (ns * np.nan_to_num(level_ref_obs) + SHRINK_K * level_ref_pred) / (ns + SHRINK_K), level_ref_pred)
    # per-stratum level: observed where the NTA has sites in that stratum (blended), else reference × ratio
    lvl = np.zeros((n, 4))
    for i in range(n):
        ratio = sm.stratum_ratio.get(clusters[i], sm.stratum_ratio["all"])
        for s in range(4):
            model_s = level_ref[i] * ratio[s]
            if np.isfinite(lvl_obs[i, s]) and den[i, s] > 0:
                k = den[i, s] / (den[i, s] + np.median(s_w) * SHRINK_K)
                lvl[i, s] = k * lvl_obs[i, s] + (1 - k) * model_s
            else:
                lvl[i, s] = model_s
    # hourly flows and densities per stratum, lane-km weighted
    q = np.zeros((n, 24, 3))
    dens = np.zeros((n, 24, 3))
    vkm = np.zeros((n, 24, 3))
    for i in range(n):
        tot = lane_km[i].sum()
        if tot <= 0:
            continue
        for s in range(4):
            if lane_km[i, s] <= 0:
                continue
            prof = sm.profiles["highway"] if s == 0 else sm.profiles.get(clusters[i], sm.profiles["all"])
            qs = lvl[i, s] * prof
            ks = greenshields_density(qs, vf_s[i, s])
            q[i] += qs * lane_km[i, s] / tot
            dens[i] += ks * lane_km[i, s] / tot
            vkm[i] += qs * lane_km[i, s]
    has_roads = lane_km.sum(axis=1) > 0
    dens[has_roads] = np.maximum(dens[has_roads], DENSITY_FLOOR)
    source = np.array(["landuse_model"] * n, dtype=object)
    source[(n_sites >= 1) & (n_sites_recent == 0)] = "atr_older"
    source[(n_sites_recent >= 1)] = "atr_recent"
    source[(n_sites >= 1) & (n_sites_recent >= 1) & (n_sites > n_sites_recent)] = "atr_mixed"
    source[~has_roads] = "no_roads"
    log.info("NTA volume sources: %s", {k: int(v) for k, v in zip(*np.unique(source, return_counts=True))})
    return VolumeResult(q, dens, level_ref, level_ref_obs, level_ref_pred, n_sites, n_sites_recent, source, clusters, reg, lane_km, vf_s, vkm)
