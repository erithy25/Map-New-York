"""Speed model: hourly flow per lane → vehicles per km of lane.

Density is a *derived* quantity: ``k = q / v``.  The model therefore has to state a speed for every
(road class, flow) pair, and that speed must be a **space-mean journey speed** — i.e. it must already
contain signal, stop-sign, queue and kerb-manoeuvre delay — because the vehicles waiting at a red
light are physically present on the lane and belong in the density.

Per road class the speed falls linearly from a free-flow value to a speed-at-capacity value:

    v_c(q) = v_free_c - (v_free_c - v_cap_c) * min(q / q_cap_c, 1)
    k      = min(q / v_c(q), k_jam)

This is the classical linear (Greenshields) family written with the two anchors that are actually
published — free-flow speed and capacity — instead of the jam density, which is not observable.
Greenshields is the special case ``v_cap = v_free / 2``; the classes below are less symmetric than
that because signalised urban streets lose speed much faster than a freeway.

Class parameters
----------------
=====================  ==========================  ==============  ==============================
class                  v_free                      q_cap           v_cap  (implied k at capacity)
=====================  ==========================  ==============  ==============================
0 freeway/expressway   88.5 km/h (55 mph)          2100 veh/h/ln   46.7 km/h  (45 veh/km/ln)
1 ramp                 48.3 km/h (30 mph)          1800 veh/h/ln   26.6 km/h  (68 veh/km/ln)
2 arterial (signal.)   0.62 x posted               900 veh/h/ln    0.25 x posted (90 @ 25 mph)
3 two-way street       0.60 x posted               750 veh/h/ln    0.25 x posted (75 @ 25 mph)
4 one-way local        0.58 x posted               650 veh/h/ln    0.24 x posted (68 @ 25 mph)
=====================  ==========================  ==============  ==============================

Sources for the anchors
  * freeway: HCM 7th ed., basic freeway segment at FFS 55 mph — capacity 2250 pc/h/ln, density at
    capacity 45 pc/km/ln; derated to 2100 veh/h/ln for the NYC fleet (trucks, buses, heavy weaving).
  * ramp: HCM 7th ed. ramp roadways, one-lane ramp capacity 1900-2000 veh/h at 30 mph FFS; derated.
  * signalised streets: HCM 7th ed. urban street facilities — base saturation flow 1900 veh/h/ln,
    typical NYC through-movement g/C = 0.45-0.50 -> 855-950 veh/h/ln.  The free-flow *travel* speed
    factors (0.58-0.62 of the posted speed) and the speed-at-capacity factors (about a quarter of
    the posted speed) are the NYC-specific part and are re-calibrated per NTA and per hour against
    the TLC journey speeds by :func:`calibrate_surface`, which is what makes Midtown at 17:00 come
    out at 8-9 km/h and a Staten Island local street at 04:00 at 24 km/h.

``k_jam`` = 130 veh/km/lane: 7.7 m per vehicle at a standstill (4.9 m mean length over the NYC fleet
including vans/trucks/buses, plus a 2.8 m stopped gap).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import polars as pl

from .segments import MPH_TO_KMH, SegmentTable

log = logging.getLogger("nycsim.traffic.speed")

K_JAM = 130.0
CLASS_NAMES = {0: "freeway", 1: "ramp", 2: "arterial", 3: "two_way_street", 4: "one_way_local"}
SURFACE_CLASSES = (2, 3, 4)

# (absolute v_free km/h or 0 -> use factor, v_free factor of posted, q_cap veh/h/lane, v_cap factor of v_free)
CLASS_PARAMS: dict[int, tuple[float, float, float, float]] = {
    0: (88.5, 0.0, 2100.0, 0.528),   # 46.7 / 88.5
    1: (48.3, 0.0, 1800.0, 0.550),   # 26.6 / 48.3
    2: (0.0, 0.62, 900.0, 0.403),    # v_cap = 0.25 x posted = 0.403 x v_free
    3: (0.0, 0.60, 750.0, 0.417),
    4: (0.0, 0.58, 650.0, 0.414),
}

CALIB_MIN = 0.30
CALIB_MAX = 1.60
CALIB_MIN_TRIP_KM = 25.0     # TLC trip-km per average day in the cell needed to trust its speed


def road_class(rw_type: np.ndarray, travel_lanes: np.ndarray, trafdir: np.ndarray, truck_route: np.ndarray) -> np.ndarray:
    """Speed-model class per segment (see :data:`CLASS_NAMES`)."""
    rw = np.asarray(rw_type)
    ln = np.asarray(travel_lanes)
    two_way = np.asarray(trafdir) == "TW"
    tr = np.asarray(truck_route, dtype=bool)
    c = np.full(len(rw), 3, dtype=np.int8)            # default: two-way street
    c[(~two_way) & (ln <= 2)] = 4                     # one-way local
    c[(ln >= 3) | tr] = 2                             # arterial: 3+ travel lanes or a designated truck route
    c[rw == 9] = 1                                    # ramp
    c[rw == 2] = 0                                    # highway / expressway
    # bridges and tunnels inherit the class of what they carry: >= 3 lanes -> arterial, else two-way
    return c


def free_flow_kmh(cls: np.ndarray, posted_kmh: np.ndarray) -> np.ndarray:
    out = np.empty(len(cls), dtype=np.float64)
    for c, (v_abs, v_fac, _q, _vc) in CLASS_PARAMS.items():
        m = cls == c
        if m.any():
            out[m] = v_abs if v_abs > 0 else v_fac * posted_kmh[m]
    return out


def capacity(cls: np.ndarray) -> np.ndarray:
    return np.array([CLASS_PARAMS[int(c)][2] for c in cls], dtype=np.float64)


def speed_at_capacity_kmh(cls: np.ndarray, v_free: np.ndarray) -> np.ndarray:
    return np.array([CLASS_PARAMS[int(c)][3] for c in cls], dtype=np.float64) * v_free


def speed_of_flow(q: np.ndarray, v_free: np.ndarray, v_cap: np.ndarray, q_cap: np.ndarray) -> np.ndarray:
    """Space-mean speed (km/h) at flow ``q`` (veh/h/lane).  Broadcasting-friendly."""
    r = np.clip(np.asarray(q, dtype=np.float64) / np.maximum(q_cap, 1e-6), 0.0, 1.0)
    return np.maximum(v_free - (v_free - v_cap) * r, 0.5)


def density_of_flow(q: np.ndarray, v_free: np.ndarray, v_cap: np.ndarray, q_cap: np.ndarray,
                    k_jam: float = K_JAM) -> np.ndarray:
    """Vehicles per km of lane at flow ``q``."""
    v = speed_of_flow(q, v_free, v_cap, q_cap)
    return np.minimum(np.asarray(q, dtype=np.float64) / v, k_jam)


@dataclass
class SurfaceCalibration:
    factor: np.ndarray          # (n_nta, 24, 3) multiplier applied to surface-street speeds
    observed: np.ndarray        # (n_nta, 24, 3) TLC journey speed, NaN where not observed
    modelled: np.ndarray        # (n_nta, 24, 3) uncalibrated model speed
    n_direct: int               # cells calibrated from their own TLC speed
    n_borough: int              # cells filled from the borough-hour median
    n_default: int              # cells left at 1.0


def _harmonic_surface_speed(seg: SegmentTable, cls: np.ndarray, q_seg: np.ndarray, n_nta: int,
                            v_free: np.ndarray, v_cap: np.ndarray, q_cap: np.ndarray) -> np.ndarray:
    """(n_nta, 24, 3) lane-km-weighted harmonic-mean surface-street speed from the uncalibrated model."""
    df = seg.df
    nta_idx = df["nta_idx"].to_numpy().astype(int)
    lane_km = df["lane_km"].to_numpy()
    surf = np.isin(cls, SURFACE_CLASSES) & (nta_idx >= 0)
    num = np.zeros((n_nta, 24, 3))
    den = np.zeros((n_nta, 24, 3))
    idx = nta_idx[surf]
    lk = lane_km[surf]
    v = speed_of_flow(q_seg[surf], v_free[surf][:, None, None], v_cap[surf][:, None, None], q_cap[surf][:, None, None])
    np.add.at(num, idx, lk[:, None, None])
    np.add.at(den, idx, lk[:, None, None] / np.maximum(v, 0.5))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def calibrate_surface(seg: SegmentTable, cls: np.ndarray, q_seg: np.ndarray, n_nta: int, borough: np.ndarray,
                      v_free: np.ndarray, v_cap: np.ndarray, q_cap: np.ndarray,
                      tlc_speed: np.ndarray, tlc_trip_km: np.ndarray) -> SurfaceCalibration:
    """Per NTA × hour × day-type multiplier that brings the modelled surface speed onto the TLC speed.

    Cells with too little TLC evidence take the median multiplier of their borough for that hour and
    day type; boroughs with none at all keep 1.0 (the uncalibrated class model).
    """
    modelled = _harmonic_surface_speed(seg, cls, q_seg, n_nta, v_free, v_cap, q_cap)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = tlc_speed / modelled
    good = np.isfinite(raw) & (raw > 0) & (tlc_trip_km >= CALIB_MIN_TRIP_KM)
    factor = np.ones((n_nta, 24, 3))
    factor[good] = np.clip(raw[good], CALIB_MIN, CALIB_MAX)
    n_direct = int(good.sum())
    n_borough = 0
    for b in np.unique(borough):
        rows = np.flatnonzero(borough == b)
        for h in range(24):
            for d in range(3):
                sel = good[rows, h, d]
                if not sel.any():
                    continue
                med = float(np.median(factor[rows[sel], h, d]))
                fill = rows[~sel]
                if len(fill):
                    factor[fill, h, d] = med
                    n_borough += len(fill)
    n_default = n_nta * 24 * 3 - n_direct - n_borough
    log.info("surface speed calibration: %d cells from TLC directly, %d from the borough-hour median, %d left at 1.0; "
             "factor p05/median/p95 = %.2f/%.2f/%.2f", n_direct, n_borough, n_default,
             *np.percentile(factor, [5, 50, 95]))
    return SurfaceCalibration(factor, tlc_speed, modelled, n_direct, n_borough, n_default)


def free_flow_summary(seg: SegmentTable, cls: np.ndarray) -> pl.DataFrame:
    """Lane-km and assumed free-flow / capacity speeds per class — for the report."""
    df = seg.df
    posted = df["posted_speed_mph"].to_numpy().astype(float) * MPH_TO_KMH
    vf = free_flow_kmh(cls, posted)
    qc = capacity(cls)
    vc = speed_at_capacity_kmh(cls, vf)
    lk = df["lane_km"].to_numpy()
    rows = []
    for c, name in CLASS_NAMES.items():
        m = cls == c
        if not m.any():
            continue
        rows.append({
            "class": c, "name": name, "n_segments": int(m.sum()), "lane_km": float(lk[m].sum()),
            "posted_kmh_mean": float(np.average(posted[m], weights=lk[m])),
            "v_free_kmh": float(np.average(vf[m], weights=lk[m])),
            "v_cap_kmh": float(np.average(vc[m], weights=lk[m])),
            "q_cap_veh_h_lane": float(qc[m][0]),
            "k_at_capacity": float(np.average(qc[m] / np.maximum(vc[m], 0.5), weights=lk[m])),
        })
    return pl.DataFrame(rows)
