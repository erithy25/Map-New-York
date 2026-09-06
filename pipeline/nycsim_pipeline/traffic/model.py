"""Vehicle volume model: ATR counts + CSCL + PLUTO → flow per lane on every segment, hour and day type.

The model is hierarchical, because the data is: DOT's Automated Traffic Volume Counts give a very
precise picture of ~2,400 individual blocks and nothing at all about the other 110,000.

1. **Site matching.** Each count site is attached to a CSCL centerline segment by ``SegmentID`` ==
   ``physicalid`` where that lands within 150 m of the recorded point, else to the nearest segment
   within 60 m whose street name matches, else to the nearest segment within 25 m.
2. **Site level and profile.** For each matched site the hourly flow per travel lane gives a *level*
   (mean over the weekday hours, veh/h/lane) and a *profile* (the 24 x 3 flows divided by that level).
3. **Profiles** are pooled by area cluster (CBD, rest of Manhattan, commercial, industrial,
   residential, special) for surface streets and city-wide for freeways/ramps, which is the level at
   which the diurnal shape is stable.
4. **Level, stage 1 — road class.** ``log(level)`` is regressed on the *segment's own* attributes
   (travel lanes, road type, posted speed, kerb-to-kerb width, truck route, one-way, avenue/boulevard
   name).  This is the part of a block's traffic that comes from what kind of road it is.
5. **Level, stage 2 — the neighbourhood.** The stage-1 residuals are averaged per NTA into an *NTA
   effect* and that effect is regressed on land use (PLUTO floor areas and lot-use mix) and
   accessibility (subway entrances, distance to the Manhattan core, expressway proximity, PLUTO
   garage area per dwelling).  This is the regression that fills in NTAs with no counts, and its
   R² / leave-one-out R² are reported.
6. **Blending.** An NTA with its own sites keeps its observed effect, shrunk toward the regression
   prediction by ``W / (W + k0)`` where ``W`` is the total weight of its sites and ``k0`` the median
   weight of one site.  An NTA with no sites uses the prediction outright.
7. **Assembly.** Every segment gets ``level = exp(stage1(x_segment) + effect(NTA))``; the hourly flow
   is ``level x profile``; :mod:`speed` turns that into a density; and the NTA value is the lane-km
   weighted mean over its segments — the vehicles standing on all of the NTA's travel lanes divided
   by the length of those lanes, exactly what ``veh_per_km_lane`` means in DATA_CONTRACTS §10.

Recency: sites last counted in 2023-2026 carry full weight, older ones 0.6, and the flows themselves
are already recency-weighted inside :mod:`counts`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import polars as pl
import shapely

from . import speed as speedmod
from .counts import CountData
from .geo import NtaTable
from .segments import MPH_TO_KMH, SegmentTable, normalize_street

log = logging.getLogger("nycsim.traffic.model")

CLUSTERS = ("cbd", "manhattan", "commercial", "industrial", "residential", "special")
CLUSTER_FALLBACK = {"cbd": "manhattan", "manhattan": "commercial", "commercial": "residential",
                    "industrial": "residential", "residential": "all", "special": "residential", "all": None}
MIN_SITES_FOR_PROFILE = 8
MIN_HOURS_FOR_PROFILE = 18
SHRINK_SITES = 1.0              # pseudo-sites of regression evidence blended into an observed NTA effect
DENSITY_FLOOR = 0.02            # veh/km/lane — an NTA with roads is never perfectly empty
SEGMENT_CHUNK = 20000

# Stage-2 features, chosen by forward selection on the leave-one-out R² over the candidate list in
# :func:`nta_feature_matrix` (see docs/verification/traffic_density/METHOD.md §5).
STAGE2_FEATURES = ("log_office_far", "log_garage_per_unit", "truck_route_share", "log_d_cbd_km",
                   "arterial_lane_share", "highway_lane_share")
STAGE1_RIDGE = 2.0
STAGE2_RIDGE = 4.0


# ----------------------------------------------------------------------------- clusters
def cluster_of(nta: NtaTable, landuse: pl.DataFrame) -> np.ndarray:
    """Area-type cluster per NTA, used to pool diurnal profiles."""
    lu = landuse.sort("nta_idx")
    res = lu["res_m2"].to_numpy()
    com = lu["com_m2"].to_numpy() + lu["office_m2"].to_numpy() + lu["retail_m2"].to_numpy()
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
    df: pl.DataFrame
    n_by_match: dict[str, int] = field(default_factory=dict)


def match_sites(cd: CountData, seg: SegmentTable) -> MatchedSites:
    """Attach every ATR site to a CSCL segment and copy that segment's attributes onto the site."""
    sites = cd.sites.filter(pl.col("x").is_not_null() & pl.col("y").is_not_null()
                            & pl.col("x").is_finite() & pl.col("y").is_finite())
    x, y = sites["x"].to_numpy(), sites["y"].to_numpy()
    seg_ids = sites["segment_id"].to_numpy()
    streets = [normalize_street(s) for s in sites["street"].to_list()]
    seg_norm = seg.df["street_norm"].to_list()
    rows = np.full(len(sites), -1, dtype=np.int64)
    dist = np.full(len(sites), np.nan)
    match = np.array(["none"] * len(sites), dtype=object)
    pts = shapely.points(x, y)
    for i, sid in enumerate(seg_ids.tolist()):
        r = seg.phys_index.get(int(sid))
        if r is not None:
            d = float(shapely.distance(pts[i], seg.geoms[r]))
            if d <= 150.0:
                rows[i], dist[i], match[i] = r, d, "physicalid"
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
            chosen: tuple[float, int, str] | None = None
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
    out = sites.with_columns(pl.Series("seg_row", rows), pl.Series("dist_m", dist),
                             pl.Series("match", match)).filter(pl.Series(ok))
    r = out["seg_row"].to_numpy()
    out = out.with_columns(
        pl.Series("physicalid", sd["physicalid"].to_numpy()[r]),
        pl.Series("nta_idx", sd["nta_idx"].to_numpy()[r]),
        pl.Series("travel_lanes", sd["travel_lanes"].to_numpy()[r]),
        pl.Series("trafdir", np.asarray(sd["trafdir"].to_list(), dtype=object)[r].tolist()),
        pl.Series("lane_km", sd["lane_km"].to_numpy()[r]),
        pl.Series("posted_speed_mph", sd["posted_speed_mph"].to_numpy()[r]),
        pl.Series("rw_type", sd["rw_type"].to_numpy()[r]),
        pl.Series("is_truck_route", sd["is_truck_route"].to_numpy()[r]),
        pl.Series("streetwidth_ft", sd["streetwidth_ft"].to_numpy()[r]),
        pl.Series("street_norm", np.asarray(sd["street_norm"].to_list(), dtype=object)[r].tolist()),
    )
    out = out.with_columns(pl.Series("road_class", speedmod.road_class(
        out["rw_type"].to_numpy(), out["travel_lanes"].to_numpy(),
        np.asarray(out["trafdir"].to_list()), out["is_truck_route"].to_numpy())))
    out = out.filter(pl.col("nta_idx") >= 0)
    counts = {str(k): int(v) for k, v in zip(*np.unique(match, return_counts=True))}
    counts["unmatched"] = int((~ok).sum())
    log.info("site matching: %s (%d sites usable, median offset %.0f m)", counts, out.height,
             float(np.nanmedian(out["dist_m"].to_numpy())) if out.height else float("nan"))
    return MatchedSites(out, counts)


# ----------------------------------------------------------------------------- site levels & profiles
@dataclass
class SiteModel:
    sites: pl.DataFrame                 # matched sites + level (veh/h/lane) + n_hours_wd + cluster
    q: np.ndarray                       # (n_sites, 24, 3) flow per lane, NaN where unobserved
    n_days: np.ndarray                  # (n_sites, 24, 3)
    profiles: dict[str, np.ndarray]     # key -> (24, 3), weekday daily mean == 1
    profile_n: dict[str, int]
    dir_doubled: int


def _weighted_profile(qn: np.ndarray, w: np.ndarray) -> np.ndarray:
    ww = np.where(np.isfinite(qn), w[:, None, None], 0.0)
    num = np.nansum(np.where(np.isfinite(qn), qn, 0.0) * ww, axis=0)
    den = ww.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def _fill_profile(p: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    out = p.copy()
    bad = ~np.isfinite(out)
    out[bad] = fallback[bad]
    return out


def build_site_model(cd: CountData, ms: MatchedSites, clusters: np.ndarray) -> SiteModel:
    """Per-site level and the pooled diurnal profiles."""
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
    dbl = two_way[rows] & (ndir == 1)       # two-way street counted in one direction only
    veh = np.where(dbl, veh * 2.0, veh)
    q[rows, hh, dd] = veh / np.maximum(lanes[rows], 1.0)
    nd[rows, hh, dd] = fl["n_days"].to_numpy()

    wd = q[:, :, 0]
    n_hours_wd = np.isfinite(wd).sum(axis=1)
    enough = n_hours_wd >= MIN_HOURS_FOR_PROFILE
    level = np.full(n, np.nan)
    if enough.any():
        level[enough] = np.nanmean(wd[enough], axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        qn = q / level[:, None, None]
    cls = sites["road_class"].to_numpy()
    site_cluster = clusters[sites["nta_idx"].to_numpy()]
    w = np.sqrt(np.maximum(nd[:, :, 0].sum(axis=1), 1.0))
    valid = np.isfinite(level) & (level > 0)

    profiles: dict[str, np.ndarray] = {}
    profile_n: dict[str, int] = {}
    sel_all = valid & (cls >= 2)
    p_all = _weighted_profile(qn[sel_all], w[sel_all])
    p_all = np.where(np.isfinite(p_all), p_all, 1.0)
    profiles["all"], profile_n["all"] = p_all, int(sel_all.sum())
    sel_h = valid & (cls <= 1)
    profile_n["highway"] = int(sel_h.sum())
    profiles["highway"] = _fill_profile(_weighted_profile(qn[sel_h], w[sel_h]), p_all) \
        if sel_h.sum() >= MIN_SITES_FOR_PROFILE else p_all
    for c in CLUSTERS:
        profile_n[c] = int((valid & (cls >= 2) & (site_cluster == c)).sum())
    for c in CLUSTERS:
        sel = valid & (cls >= 2) & (site_cluster == c)
        if sel.sum() >= MIN_SITES_FOR_PROFILE:
            profiles[c] = _fill_profile(_weighted_profile(qn[sel], w[sel]), p_all)
            continue
        fb = CLUSTER_FALLBACK[c]
        while fb is not None and fb != "all" and profile_n.get(fb, 0) < MIN_SITES_FOR_PROFILE:
            fb = CLUSTER_FALLBACK[fb]
        if fb is None or fb == "all":
            profiles[c] = p_all
        else:
            selfb = valid & (cls >= 2) & (site_cluster == fb)
            profiles[c] = _fill_profile(_weighted_profile(qn[selfb], w[selfb]), p_all)
        log.info("profile for cluster %s pooled from %s (%d own sites)", c, fb or "all", int(sel.sum()))
    for k, p in profiles.items():
        m = float(np.nanmean(p[:, 0]))
        profiles[k] = p / m if m > 0 else p
        if not np.isfinite(profiles[k]).all():
            raise ValueError(f"profile {k} still has non-finite entries")

    sites = sites.with_columns(pl.Series("level", level), pl.Series("n_hours_wd", n_hours_wd.astype(np.int32)),
                               pl.Series("cluster", site_cluster.tolist()))
    log.info("site model: %d sites, %d with a weekday level; %d segment-hours direction-doubled; profile sites %s",
             n, int(valid.sum()), int(dbl.sum()), profile_n)
    return SiteModel(sites, q, nd, profiles, profile_n, int(dbl.sum()))


# ----------------------------------------------------------------------------- regression machinery
@dataclass
class Regression:
    feature_names: list[str]
    beta: np.ndarray
    mu: np.ndarray
    sd: np.ndarray
    r2: float
    r2_loo: float
    n: int
    rmse: float
    ridge: float

    def predict(self, X: np.ndarray) -> np.ndarray:
        Z = (np.asarray(X, dtype=np.float64) - self.mu) / self.sd
        return np.column_stack([np.ones(len(Z)), Z]) @ self.beta

    def as_dict(self) -> dict:
        return {"features": self.feature_names, "beta": [float(b) for b in self.beta],
                "r2": self.r2, "r2_loo": self.r2_loo, "n": self.n, "rmse_log": self.rmse, "ridge": self.ridge}


def fit_regression(X: np.ndarray, y: np.ndarray, w: np.ndarray, names: list[str], ridge: float = 1.0) -> Regression:
    """Weighted ridge regression on standardised features, with leave-one-out R² from the hat matrix."""
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[0] != len(y) or X.shape[1] != len(names):
        raise ValueError(f"design matrix {X.shape} does not match {len(y)} observations / {len(names)} names")
    if not np.isfinite(X).all() or not np.isfinite(y).all() or not np.isfinite(w).all():
        raise ValueError("regression inputs contain non-finite values")
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    R = np.eye(Z.shape[1]) * ridge
    R[0, 0] = 0.0
    W = np.sqrt(w)[:, None]
    A = (Z * W).T @ (Z * W) + R
    beta = np.linalg.solve(A, (Z * W).T @ (y * W[:, 0]))
    yhat = Z @ beta
    ybar = np.average(y, weights=w)
    ss_tot = float(np.sum(w * (y - ybar) ** 2))
    ss_res = float(np.sum(w * (y - yhat) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    Ainv = np.linalg.inv(A)
    h = np.einsum("ij,jk,ik->i", Z * W, Ainv, Z * W)
    loo_res = (y - yhat) / np.maximum(1.0 - h, 1e-6)
    r2_loo = 1.0 - float(np.sum(w * loo_res ** 2)) / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(ss_res / float(np.sum(w))))
    return Regression(list(names), beta, mu, sd, float(r2), float(r2_loo), int(len(y)), rmse, float(ridge))


# ----------------------------------------------------------------------------- feature matrices
def segment_features(rw_type: np.ndarray, travel_lanes: np.ndarray, trafdir: np.ndarray,
                     posted_mph: np.ndarray, width_ft: np.ndarray, truck_route: np.ndarray,
                     street_norm: list[str]) -> tuple[np.ndarray, list[str]]:
    """Stage-1 design matrix: what kind of road this block is."""
    rw = np.asarray(rw_type)
    ln = np.asarray(travel_lanes, dtype=np.float64)
    two_way = (np.asarray(trafdir) == "TW").astype(np.float64)
    width = np.nan_to_num(np.asarray(width_ft, dtype=np.float64), nan=30.0, posinf=30.0, neginf=30.0)
    av = np.array([bool(n) and (n.endswith(" AV") or n.endswith(" BLVD") or " AV " in n or " BLVD " in n)
                   for n in street_norm], dtype=np.float64)
    f = {
        "log_travel_lanes": np.log(np.maximum(ln, 1.0)),
        "is_highway": (rw == 2).astype(np.float64),
        "is_ramp": (rw == 9).astype(np.float64),
        "is_bridge_tunnel": ((rw == 3) | (rw == 4)).astype(np.float64),
        "posted_kmh": np.asarray(posted_mph, dtype=np.float64) * MPH_TO_KMH,
        "is_two_way": two_way,
        "is_truck_route": np.asarray(truck_route, dtype=np.float64),
        "log_width_ft": np.log(np.clip(width, 10.0, 200.0)),
        "is_avenue": av,
    }
    names = list(f)
    return np.column_stack([f[k] for k in names]), names


def nta_feature_matrix(nta: NtaTable, landuse: pl.DataFrame, roads: pl.DataFrame,
                       access: pl.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Stage-2 candidate features: land use, road supply and accessibility, one row per NTA."""
    lu = landuse.sort("nta_idx")
    rd = roads.sort("nta_idx")
    ac = access.sort("nta_idx")
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
        "log_sub_density": ac["log_sub_density"].to_numpy(),
        "log_d_subway_km": ac["log_d_subway_km"].to_numpy(),
        "log_d_cbd_km": ac["log_d_cbd_km"].to_numpy(),
        "log_hw_lane_km_3km": ac["log_hw_lane_km_3km"].to_numpy(),
        "log_garage_per_unit": ac["log_garage_per_unit"].to_numpy(),
    }
    names = list(f)
    X = np.column_stack([f[k] for k in names])
    if not np.isfinite(X).all():
        bad = [names[j] for j in range(X.shape[1]) if not np.isfinite(X[:, j]).all()]
        raise ValueError(f"non-finite NTA features: {bad}")
    return X, names


# ----------------------------------------------------------------------------- two-stage level model
@dataclass
class LevelModel:
    stage1: Regression
    stage2: Regression
    effect_obs: np.ndarray          # (n_nta,) observed NTA effect, NaN where no sites
    effect_pred: np.ndarray         # (n_nta,) regression prediction
    effect: np.ndarray              # (n_nta,) blended effect actually used
    site_weight: np.ndarray         # (n_nta,) total site weight
    n_sites: np.ndarray
    n_sites_recent: np.ndarray
    nta_r2_class_only: float
    nta_r2_with_landuse: float
    nta_n: int
    within_nta_sd: float
    stage2_selected: tuple[str, ...]


def fit_level_model(sm: SiteModel, nta: NtaTable, landuse: pl.DataFrame, roads: pl.DataFrame,
                    access: pl.DataFrame) -> LevelModel:
    s = sm.sites.filter(pl.col("level").is_not_null() & pl.col("level").is_finite() & (pl.col("level") > 0))
    if s.height < 50:
        raise ValueError(f"only {s.height} sites have a usable weekday level — refusing to fit the level model")
    ly = np.log(s["level"].to_numpy())
    ni = s["nta_idx"].to_numpy().astype(int)
    Xs, sn = segment_features(s["rw_type"].to_numpy(), s["travel_lanes"].to_numpy(),
                              np.asarray(s["trafdir"].to_list()), s["posted_speed_mph"].to_numpy(),
                              s["streetwidth_ft"].to_numpy(), s["is_truck_route"].to_numpy(),
                              s["street_norm"].to_list())
    w = np.sqrt(np.maximum(s["n_hours_wd"].to_numpy().astype(np.float64), 1.0)) * \
        np.where(np.asarray(s["tier"].to_list()) == "recent", 1.0, 0.6)
    stage1 = fit_regression(Xs, ly, w, sn, ridge=STAGE1_RIDGE)
    resid = ly - stage1.predict(Xs)

    n = len(nta)
    num = np.zeros(n)
    den = np.zeros(n)
    cnt = np.zeros(n)
    cnt_recent = np.zeros(n)
    np.add.at(num, ni, resid * w)
    np.add.at(den, ni, w)
    np.add.at(cnt, ni, 1.0)
    np.add.at(cnt_recent, ni[np.asarray(s["tier"].to_list()) == "recent"], 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        effect_obs = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)

    XA, na = nta_feature_matrix(nta, landuse, roads, access)
    missing = [f for f in STAGE2_FEATURES if f not in na]
    if missing:
        raise ValueError(f"stage-2 features not in the NTA feature matrix: {missing}")
    cols = [na.index(f) for f in STAGE2_FEATURES]
    obs = np.isfinite(effect_obs)
    stage2 = fit_regression(XA[obs][:, cols], effect_obs[obs], np.sqrt(cnt[obs]),
                            list(STAGE2_FEATURES), ridge=STAGE2_RIDGE)
    effect_pred = stage2.predict(XA[:, cols])
    lo, hi = np.percentile(effect_obs[obs], [2, 98])
    effect_pred = np.clip(effect_pred, lo, hi)

    k0 = float(np.median(w))
    effect = np.where(obs, (den * np.nan_to_num(effect_obs) + k0 * SHRINK_SITES * effect_pred) /
                      (den + k0 * SHRINK_SITES), effect_pred)

    # NTA-level goodness of fit: how well the model reproduces each NTA's observed mean log level.
    p1 = stage1.predict(Xs)
    o = np.zeros(n)
    a0 = np.zeros(n)
    a1 = np.zeros(n)
    np.add.at(o, ni, ly * w)
    np.add.at(a0, ni, p1 * w)
    np.add.at(a1, ni, (p1 + effect_pred[ni]) * w)
    m = den > 0
    obs_m, pr0, pr1, ww = o[m] / den[m], a0[m] / den[m], a1[m] / den[m], np.sqrt(cnt[m])

    def _r2(y: np.ndarray, p: np.ndarray) -> float:
        yb = np.average(y, weights=ww)
        return float(1.0 - np.sum(ww * (y - p) ** 2) / np.sum(ww * (y - yb) ** 2))

    groups = [resid[ni == i] for i in np.flatnonzero(cnt >= 4)]
    within_sd = float(np.median([np.std(g, ddof=1) for g in groups])) if groups else float("nan")
    log.info("level model stage 1 (road class): R²=%.3f LOO=%.3f on %d sites, rmse(log)=%.3f",
             stage1.r2, stage1.r2_loo, stage1.n, stage1.rmse)
    log.info("level model stage 2 (land use → NTA effect): R²=%.3f LOO=%.3f on %d NTAs, rmse(log)=%.3f",
             stage2.r2, stage2.r2_loo, stage2.n, stage2.rmse)
    log.info("NTA-level R² of the mean log level: road class only %.3f, + land-use effect %.3f (%d NTAs); "
             "median within-NTA residual sd %.3f", _r2(obs_m, pr0), _r2(obs_m, pr1), int(m.sum()), within_sd)
    return LevelModel(stage1, stage2, effect_obs, effect_pred, effect, den, cnt.astype(np.int32),
                      cnt_recent.astype(np.int32), _r2(obs_m, pr0), _r2(obs_m, pr1), int(m.sum()),
                      within_sd, STAGE2_FEATURES)


# ----------------------------------------------------------------------------- assembly
@dataclass
class VolumeResult:
    q_lane: np.ndarray            # (n_nta, 24, 3) lane-km weighted mean flow, veh/h/lane
    density: np.ndarray           # (n_nta, 24, 3) veh/km/lane
    speed_kmh: np.ndarray         # (n_nta, 24, 3) lane-km weighted harmonic-mean speed
    veh_km_h: np.ndarray          # (n_nta, 24, 3) vehicle-km driven per hour inside the NTA
    lane_km: np.ndarray           # (n_nta,)
    lane_km_class: np.ndarray     # (n_nta, 5)
    segment_level: np.ndarray     # (n_seg,) weekday mean flow per lane on every CSCL segment
    road_class: np.ndarray        # (n_seg,)
    source: np.ndarray            # (n_nta,) object str
    clusters: np.ndarray
    level_model: LevelModel
    calibration: speedmod.SurfaceCalibration


def _segment_matrices(seg: SegmentTable, lm: LevelModel) -> tuple[np.ndarray, np.ndarray]:
    df = seg.df
    X, _ = segment_features(df["rw_type"].to_numpy(), df["travel_lanes"].to_numpy(),
                            np.asarray(df["trafdir"].to_list()), df["posted_speed_mph"].to_numpy(),
                            df["streetwidth_ft"].to_numpy(), df["is_truck_route"].to_numpy(),
                            df["street_norm"].to_list())
    base = lm.stage1.predict(X)
    nidx = df["nta_idx"].to_numpy().astype(int)
    eff = np.where(nidx >= 0, lm.effect[np.maximum(nidx, 0)], 0.0)
    return np.exp(base + eff), nidx


def assemble(nta: NtaTable, seg: SegmentTable, sm: SiteModel, lm: LevelModel, clusters: np.ndarray,
             tlc_speed: np.ndarray, tlc_trip_km: np.ndarray) -> VolumeResult:
    """Flow, speed and density for every NTA × hour × day type."""
    df = seg.df
    n = len(nta)
    cls = speedmod.road_class(df["rw_type"].to_numpy(), df["travel_lanes"].to_numpy(),
                              np.asarray(df["trafdir"].to_list()), df["is_truck_route"].to_numpy())
    level, nidx = _segment_matrices(seg, lm)
    lane_km = df["lane_km"].to_numpy()
    posted_kmh = df["posted_speed_mph"].to_numpy().astype(np.float64) * MPH_TO_KMH
    v_free = speedmod.free_flow_kmh(cls, posted_kmh)
    q_cap = speedmod.capacity(cls)
    v_cap = speedmod.speed_at_capacity_kmh(cls, v_free)

    prof_key = np.array(["highway" if c <= 1 else (clusters[i] if i >= 0 else "residential")
                         for c, i in zip(cls.tolist(), nidx.tolist())], dtype=object)
    keys = sorted(set(prof_key.tolist()))
    prof = {k: sm.profiles[k] for k in keys}

    q_seg = np.empty((len(df), 24, 3))
    for k in keys:
        m = prof_key == k
        q_seg[m] = level[m][:, None, None] * prof[k][None, :, :]

    calib = speedmod.calibrate_surface(seg, cls, q_seg, n, nta.borocode, v_free, v_cap, q_cap,
                                       tlc_speed, tlc_trip_km)

    q_sum = np.zeros((n, 24, 3))
    k_sum = np.zeros((n, 24, 3))
    t_sum = np.zeros((n, 24, 3))
    vkm = np.zeros((n, 24, 3))
    lk_tot = np.zeros(n)
    lane_km_class = np.zeros((n, len(speedmod.CLASS_NAMES)))
    inside = nidx >= 0
    np.add.at(lk_tot, nidx[inside], lane_km[inside])
    np.add.at(lane_km_class, (nidx[inside], cls[inside]), lane_km[inside])

    for start in range(0, len(df), SEGMENT_CHUNK):
        sl = slice(start, start + SEGMENT_CHUNK)
        m = inside[sl]
        if not m.any():
            continue
        idx = nidx[sl][m]
        lk = lane_km[sl][m][:, None, None]
        q = q_seg[sl][m]
        vf = v_free[sl][m][:, None, None]
        vc = v_cap[sl][m][:, None, None]
        qc = q_cap[sl][m][:, None, None]
        surf = np.isin(cls[sl][m], speedmod.SURFACE_CLASSES)[:, None, None]
        v = speedmod.speed_of_flow(q, vf, vc, qc) * np.where(surf, calib.factor[idx], 1.0)
        v = np.maximum(v, 0.5)
        k = np.minimum(q / v, speedmod.K_JAM)
        np.add.at(q_sum, idx, q * lk)
        np.add.at(k_sum, idx, k * lk)
        np.add.at(t_sum, idx, lk / v)
        np.add.at(vkm, idx, q * lk)

    has = lk_tot > 0
    q_lane = np.zeros((n, 24, 3))
    dens = np.zeros((n, 24, 3))
    spd = np.zeros((n, 24, 3))
    q_lane[has] = q_sum[has] / lk_tot[has, None, None]
    dens[has] = np.maximum(k_sum[has] / lk_tot[has, None, None], DENSITY_FLOOR)
    spd[has] = lk_tot[has, None, None] / np.maximum(t_sum[has], 1e-9)

    source = np.array(["landuse_model"] * n, dtype=object)
    source[lm.n_sites >= 1] = "atr_older"
    source[(lm.n_sites >= 1) & (lm.n_sites_recent >= 1) & (lm.n_sites > lm.n_sites_recent)] = "atr_mixed"
    source[(lm.n_sites >= 1) & (lm.n_sites == lm.n_sites_recent)] = "atr_recent"
    source[~has] = "no_roads"
    log.info("NTA volume sources: %s", {str(k): int(v) for k, v in zip(*np.unique(source, return_counts=True))})
    log.info("density veh/km/lane: min %.2f p50 %.1f p95 %.1f max %.1f; citywide veh-km per weekday %.3g",
             dens.min(), float(np.percentile(dens, 50)), float(np.percentile(dens, 95)), dens.max(),
             float(vkm[:, :, 0].sum()))
    return VolumeResult(q_lane, dens, spd, vkm, lk_tot, lane_km_class, level, cls, source, clusters, lm, calib)
