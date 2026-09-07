"""Pedestrian density per m² of sidewalk, by NTA and hour.

The DOT **Bi-Annual Pedestrian Counts** (``cqsj-cfgu``) are reachable and are the calibration
target: 114 screenline locations counted twice a year since 2007, weekdays in three windows —
AM 07:00-09:00, MD 12:00-14:00, PM 16:00-19:00.  They give a real *flow* (pedestrians past a
screenline per hour) at 100 street locations (the 14 East-/Harlem-River bridge sites are excluded,
they are not sidewalks) but only at those 100 points, so the model has three parts:

1. **Level (where).**  ``log(pedestrians/h)`` at a count site is regressed on the *local* land-use
   generators — retail, office, commercial and residential floor area, dwellings and subway
   entrances within an 800 m box around the site, from MapPLUTO and the MTA entrance list — plus
   the CBD flag.  R² is reported.  The fitted model is then evaluated at the midpoint of every one
   of the 112,395 CSCL segments, which is what makes the NTA average an average over quiet blocks
   as well as busy ones.
2. **Shape (when).**  The three DOT windows do not give a 24-hour curve, and the eight permanent
   DOT pedestrian counters are all on greenways and bridges (Willis Ave, High Bridge, Emmons Ave,
   Concrete Plant Park), so their shape is recreational, not a sidewalk shape.  The hourly shape is
   therefore taken from the TLC pick-up counts per taxi zone, hour and day type — a real, citywide,
   hourly measure of street-level activity — and then corrected once, city-wide, by the factor that
   makes it reproduce the AM:MD:PM ratios the DOT counts actually show.  The correction is anchored
   at 08:00 / 13:00 / 17:30 and interpolated smoothly (periodically) over the other hours.
3. **Density (how many per m²).**  Little's law: a screenline flow ``F`` (ped/h, both directions and
   both sidewalks) on a block of length ``L`` means ``F x L / v_walk`` pedestrians are on that
   block's sidewalks at any instant.  ``v_walk`` = 1.34 m/s (Fruin/HCM free-flow walking speed for a
   mixed urban population), inflated by :data:`STATIONARY_FACTOR` for the time pedestrians spend
   standing at kerbs and signals.  Dividing the NTA's total by its walkable sidewalk area
   (:mod:`sidewalks`) gives ``ped_per_m2_sidewalk``.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from scipy import ndimage

from ..crs import lonlat_to_tm
from ..paths import RAW
from .geo import NtaTable
from .landuse import SQFT_TO_M2
from .model import Regression, fit_regression
from .segments import SegmentTable

log = logging.getLogger("nycsim.traffic.pedestrians")

PED_COUNTS_PATH = RAW / "nyc_opendata" / "dot_ped_counts_biannual.csv"
PED_HOURLY_PATH = RAW / "traffic" / "dot_bike_ped_hourly.csv"

# DOT count windows (weekday), hours are [start, end)
PERIODS: dict[str, tuple[int, int]] = {"AM": (7, 9), "MD": (12, 14), "PM": (16, 19)}
PERIOD_ANCHOR = {"AM": 8.0, "MD": 13.0, "PM": 17.5}
N_SEASONS = 6                       # most recent seasons averaged (3 years of spring+autumn counts)
BRIDGE_BOROUGHS = ("East River Bridges", "Harlem River Bridges")

WALK_SPEED_MPS = 1.34               # Fruin (1971) / HCM 7th ed. free-flow walking speed
STATIONARY_FACTOR = 1.15            # +15 % dwell: waiting at signals, kerbs, shopfronts
GRID_M = 100.0                      # generator raster cell
GRID_BOX = 9                        # 9 x 9 cells = 900 m box around the query point
MIN_TLC_TRIPS = 40.0                # trips/day needed before an NTA's own TLC shape is trusted
PED_RIDGE = 2.0

_POINT = re.compile(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)")


@dataclass
class GeneratorRaster:
    """Land-use generators summed over a 900 m box, on a 100 m raster."""
    x0: float
    y0: float
    nx: int
    ny: int
    layers: dict[str, np.ndarray]

    def sample(self, x: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
        ix = np.clip(((np.asarray(x) - self.x0) / GRID_M).astype(int), 0, self.nx - 1)
        iy = np.clip(((np.asarray(y) - self.y0) / GRID_M).astype(int), 0, self.ny - 1)
        return {k: v[iy, ix] for k, v in self.layers.items()}


def build_generator_raster(lots: pl.DataFrame, subway_xy: tuple[np.ndarray, np.ndarray]) -> GeneratorRaster:
    """Raster of local trip generators (floor area m², dwellings, subway entrances within 900 m)."""
    lx = lots["x"].to_numpy()
    ly = lots["y"].to_numpy()
    sx, sy = subway_xy
    allx = np.concatenate([lx, sx])
    ally = np.concatenate([ly, sy])
    x0 = float(np.floor(allx.min() / GRID_M) * GRID_M) - GRID_M * GRID_BOX
    y0 = float(np.floor(ally.min() / GRID_M) * GRID_M) - GRID_M * GRID_BOX
    nx = int(np.ceil((allx.max() - x0) / GRID_M)) + GRID_BOX + 1
    ny = int(np.ceil((ally.max() - y0) / GRID_M)) + GRID_BOX + 1
    ix = ((lx - x0) / GRID_M).astype(int)
    iy = ((ly - y0) / GRID_M).astype(int)
    vals = {
        "retail_m2": lots["retailarea"].to_numpy() * SQFT_TO_M2,
        "office_m2": lots["officearea"].to_numpy() * SQFT_TO_M2,
        "com_m2": lots["comarea"].to_numpy() * SQFT_TO_M2,
        "res_m2": lots["resarea"].to_numpy() * SQFT_TO_M2,
        "units": lots["unitsres"].to_numpy().astype(np.float64),
    }
    layers: dict[str, np.ndarray] = {}
    for k, v in vals.items():
        g = np.zeros((ny, nx))
        np.add.at(g, (iy, ix), v)
        layers[k] = ndimage.uniform_filter(g, size=GRID_BOX, mode="constant") * (GRID_BOX ** 2)
    gs = np.zeros((ny, nx))
    np.add.at(gs, (((sy - y0) / GRID_M).astype(int), ((sx - x0) / GRID_M).astype(int)), 1.0)
    layers["subway"] = ndimage.uniform_filter(gs, size=GRID_BOX, mode="constant") * (GRID_BOX ** 2)
    log.info("generator raster %d x %d cells (%.0f m), %d lots, %d subway entrances", nx, ny, GRID_M,
             len(lx), len(sx))
    return GeneratorRaster(x0, y0, nx, ny, layers)


def load_ped_count_sites(nta: NtaTable, path: Path = PED_COUNTS_PATH) -> pl.DataFrame:
    """DOT bi-annual pedestrian counts → one row per street site with AM/MD/PM pedestrians per hour."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run `python -m nycsim_pipeline.traffic.fetch`")
    df = pl.read_csv(path, infer_schema_length=0)
    season_cols: dict[str, list[str]] = {p: [] for p in PERIODS}
    for c in df.columns:
        m = re.match(r"^([A-Za-z]+)(\d{2})_([A-Za-z]{2})$", c)
        if not m:
            continue
        per = m.group(3).upper()
        if per in season_cols:
            season_cols[per].append(c)
    if not all(season_cols.values()):
        raise ValueError(f"{path}: could not find AM/MD/PM season columns in {df.columns[:12]}")

    def _order(col: str) -> tuple[int, int]:
        m = re.match(r"^([A-Za-z]+)(\d{2})_", col)
        month = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7,
                 "jul": 7, "aug": 8, "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        return (int(m.group(2)), month.get(m.group(1).lower(), 6))

    xs, ys = [], []
    for g in df["the_geom"].to_list():
        mm = _POINT.search(g or "")
        if mm:
            xs.append(float(mm.group(1)))
            ys.append(float(mm.group(2)))
        else:
            xs.append(np.nan)
            ys.append(np.nan)
    lon = np.array(xs)
    lat = np.array(ys)
    ok = np.isfinite(lon) & np.isfinite(lat)
    tx = np.full(len(lon), np.nan)
    ty = np.full(len(lon), np.nan)
    tx[ok], ty[ok] = lonlat_to_tm(lon[ok], lat[ok])

    out = {"x": tx, "y": ty, "borough": df["Borough"].to_list(),
           "street": df["Street_Nam"].to_list() if "Street_Nam" in df.columns else [""] * df.height}
    used: dict[str, list[str]] = {}
    for per, cols in season_cols.items():
        cols = sorted(cols, key=_order)[-N_SEASONS:]
        used[per] = cols
        arr = np.vstack([df[c].cast(pl.Float64, strict=False).to_numpy() for c in cols])
        good = np.isfinite(arr) & (arr > 0)                 # a season a site was not counted in is blank
        n_good = good.sum(axis=0)
        mean = np.where(n_good > 0, np.where(good, arr, 0.0).sum(axis=0) / np.maximum(n_good, 1), np.nan)
        hours = PERIODS[per][1] - PERIODS[per][0]
        out[f"{per}_ph"] = mean / hours
    s = pl.DataFrame(out)
    hrs = np.array([PERIODS[p][1] - PERIODS[p][0] for p in PERIODS], dtype=np.float64)
    per_arr = np.vstack([s[f"{p}_ph"].to_numpy() for p in PERIODS])
    ok_p = np.isfinite(per_arr)
    wsum = np.where(ok_p, hrs[:, None], 0.0).sum(axis=0)
    level = np.where(wsum > 0, np.where(ok_p, per_arr * hrs[:, None], 0.0).sum(axis=0) / np.maximum(wsum, 1e-9), np.nan)
    s = s.with_columns(pl.Series("level_ph", level))
    s = s.with_columns(pl.Series("nta_idx", nta.assign_points(s["x"].to_numpy(), s["y"].to_numpy(), snap_m=300.0)))
    n_all = s.height
    s = s.filter(~pl.col("borough").is_in(list(BRIDGE_BOROUGHS)) & (pl.col("nta_idx") >= 0)
                 & pl.col("level_ph").is_finite() & (pl.col("level_ph") > 0))
    log.info("DOT pedestrian counts: %d locations, %d street sites usable (seasons %s); "
             "level p10/median/p90 = %.0f/%.0f/%.0f ped/h", n_all, s.height,
             {k: v[-1] for k, v in used.items()}, *np.percentile(s["level_ph"].to_numpy(), [10, 50, 90]))
    return s


def _design(gen: dict[str, np.ndarray], is_cbd: np.ndarray) -> tuple[np.ndarray, list[str]]:
    f = {
        "log_retail_800m": np.log1p(gen["retail_m2"] / 1e3),
        "log_office_800m": np.log1p(gen["office_m2"] / 1e3),
        "log_com_800m": np.log1p(gen["com_m2"] / 1e3),
        "log_res_800m": np.log1p(gen["res_m2"] / 1e3),
        "log_units_800m": np.log1p(gen["units"]),
        "log_subway_800m": np.log1p(gen["subway"]),
        "is_cbd": np.asarray(is_cbd, dtype=np.float64),
    }
    names = list(f)
    return np.column_stack([f[k] for k in names]), names


def fit_ped_level_model(sites: pl.DataFrame, raster: GeneratorRaster, nta: NtaTable) -> Regression:
    """Regress the DOT screenline level on the local generators; ridge, LOO-validated."""
    gen = raster.sample(sites["x"].to_numpy(), sites["y"].to_numpy())
    is_cbd = nta.is_cbd[sites["nta_idx"].to_numpy()]
    X, names = _design(gen, is_cbd)
    y = np.log(sites["level_ph"].to_numpy())
    w = np.ones(len(y))
    reg = fit_regression(X, y, w, names, ridge=PED_RIDGE)
    log.info("pedestrian level model: R²=%.3f LOO=%.3f on %d sites, rmse(log)=%.3f; betas %s",
             reg.r2, reg.r2_loo, reg.n, reg.rmse,
             {n: round(float(b), 3) for n, b in zip(["intercept"] + names, reg.beta)})
    return reg


def _tlc_pickup_shape(trips: pl.DataFrame, weights: dict[int, list[tuple[int, float]]], n_nta: int,
                      borough: np.ndarray) -> np.ndarray:
    """(n_nta, 24, 3) normalised hourly shape of TLC pick-ups; thin NTAs fall back to their borough."""
    arr = np.zeros((n_nta, 24, 3))
    for row in trips.iter_rows(named=True):
        w = weights.get(int(row["location_id"]))
        if not w:
            continue
        h, d, v = int(row["hour"]), int(row["dow"]), float(row["trips_per_day"])
        for gi, frac in w:
            arr[gi, h, d] += v * frac
    city = arr.sum(axis=0)
    boro_shape = {}
    for b in np.unique(borough):
        boro_shape[int(b)] = arr[borough == b].sum(axis=0)
    out = np.empty_like(arr)
    n_own = 0
    for i in range(n_nta):
        for d in range(3):
            tot = arr[i, :, d].sum()
            if tot >= MIN_TLC_TRIPS:
                out[i, :, d] = arr[i, :, d] / tot
                n_own += 1
                continue
            bs = boro_shape[int(borough[i])][:, d]
            src = bs if bs.sum() > 0 else city[:, d]
            out[i, :, d] = src / src.sum()
    log.info("pedestrian hourly shape: %d of %d NTA-daytypes from their own TLC pick-ups, rest pooled by borough",
             n_own, n_nta * 3)
    return out


def _period_correction(shape: np.ndarray, sites: pl.DataFrame) -> np.ndarray:
    """Smooth 24-h multiplicative correction that makes the TLC shape match the DOT AM:MD:PM ratios."""
    idx = sites["nta_idx"].to_numpy()
    obs = np.array([float(np.mean(sites[f"{p}_ph"].drop_nulls().drop_nans().to_numpy())) for p in PERIODS])
    mod = []
    for p in PERIODS:
        h0, h1 = PERIODS[p]
        mod.append(float(np.mean(shape[idx, h0:h1, 0])))
    mod = np.array(mod)
    obs = obs / obs.mean()
    mod = mod / mod.mean()
    c = np.log(obs / mod)
    anchors = np.array([PERIOD_ANCHOR[p] for p in PERIODS])
    hours = np.arange(24, dtype=np.float64)
    # periodic linear interpolation of log-correction over the three anchors (24 h period)
    ax = np.concatenate([anchors - 24.0, anchors, anchors + 24.0])
    ay = np.concatenate([c, c, c])
    corr = np.exp(np.interp(hours, ax, ay))
    log.info("pedestrian period correction (AM/MD/PM): observed shares %s, TLC shares %s, factors %s",
             np.round(obs, 3).tolist(), np.round(mod, 3).tolist(), np.round(np.exp(c), 3).tolist())
    return corr


@dataclass
class PedestrianResult:
    density: np.ndarray            # (n_nta, 24, 3) pedestrians per m² of walkable sidewalk
    present: np.ndarray            # (n_nta, 24, 3) pedestrians on the NTA's sidewalks
    flow_mean: np.ndarray          # (n_nta, 24, 3) lane-weighted mean screenline flow, ped/h
    walkable_m2: np.ndarray        # (n_nta,)
    regression: Regression
    shape: np.ndarray              # (n_nta, 24, 3) normalised hourly shape after correction
    correction: np.ndarray         # (24,)
    n_sites: int
    counter_check: dict


def pedestrian_density(nta: NtaTable, seg: SegmentTable, raster: GeneratorRaster, sites: pl.DataFrame,
                       reg: Regression, trips: pl.DataFrame, zone_weights: dict[int, list[tuple[int, float]]],
                       sidewalk: pl.DataFrame) -> PedestrianResult:
    """Pedestrians per m² of sidewalk for every NTA × hour × day type."""
    n = len(nta)
    df = seg.df
    inside = df["nta_idx"].to_numpy().astype(int)
    ok = inside >= 0
    gen = raster.sample(df["x_mid"].to_numpy(), df["y_mid"].to_numpy())
    X, _ = _design(gen, np.where(ok, nta.is_cbd[np.maximum(inside, 0)], False))
    flow_day = np.exp(reg.predict(X))                       # ped/h, mean over the counted hours
    length_m = df["length_m"].to_numpy()

    shape = _tlc_pickup_shape(trips, zone_weights, n, nta.borocode)
    corr = _period_correction(shape, sites)
    shape = shape * corr[None, :, None]
    shape /= shape.sum(axis=1, keepdims=True)
    # convert "share of the day" into "multiple of the mean over the DOT-counted hours"
    counted = np.zeros(24, dtype=bool)
    for h0, h1 in PERIODS.values():
        counted[h0:h1] = True
    base = shape[:, counted, :].mean(axis=1, keepdims=True)
    prof = shape / np.maximum(base, 1e-12)

    present = np.zeros((n, 24, 3))
    flow_num = np.zeros((n, 24, 3))
    len_tot = np.zeros(n)
    idx = inside[ok]
    f = flow_day[ok]
    L = length_m[ok]
    np.add.at(len_tot, idx, L)
    peds_seg = f * L / (WALK_SPEED_MPS * 3600.0) * STATIONARY_FACTOR
    np.add.at(present, idx, peds_seg[:, None, None] * prof[idx])
    np.add.at(flow_num, idx, (f * L)[:, None, None] * prof[idx])

    sw = sidewalk.sort("nta_idx")["walkable_m2"].to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        density = np.where(sw[:, None, None] > 0, present / np.maximum(sw[:, None, None], 1.0), 0.0)
        flow_mean = np.where(len_tot[:, None, None] > 0, flow_num / np.maximum(len_tot[:, None, None], 1e-9), 0.0)
    density = np.clip(np.nan_to_num(density), 0.0, 6.0)     # 6 ped/m² is Fruin LOS F (crush) — a hard cap

    counter_check = _counter_check(shape)
    log.info("pedestrian density: p50 %.4f, p95 %.4f, max %.4f ped/m²; %.0f k pedestrians citywide at 13:00 weekday",
             float(np.percentile(density, 50)), float(np.percentile(density, 95)), float(density.max()),
             present[:, 13, 0].sum() / 1e3)
    return PedestrianResult(density, present, flow_mean, sw, reg, shape, corr, sites.height, counter_check)


def _counter_check(shape: np.ndarray, path: Path = PED_HOURLY_PATH) -> dict:
    """Independent check of the modelled hourly shape against the DOT permanent pedestrian counters."""
    if not path.exists():
        return {"available": False, "reason": f"{path} not downloaded"}
    df = pl.read_csv(path, infer_schema_length=0).filter(pl.col("travelmode") == "pedestrian")
    if df.height == 0:
        return {"available": False, "reason": "no pedestrian rows"}
    d = df.with_columns(pl.col("hh").cast(pl.Int32), pl.col("dow").cast(pl.Int32),
                        pl.col("counts").cast(pl.Float64), pl.col("n").cast(pl.Float64))
    d = d.with_columns(pl.when(pl.col("dow") == 0).then(2).when(pl.col("dow") == 6).then(1).otherwise(0).alias("dt"))
    agg = d.group_by(["dt", "hh"]).agg((pl.col("counts").sum() / pl.col("n").sum()).alias("per_slot")).sort(["dt", "hh"])
    obs = np.zeros((24, 3))
    for r in agg.iter_rows(named=True):
        obs[int(r["hh"]), int(r["dt"])] = float(r["per_slot"])
    obs = obs / np.maximum(obs.sum(axis=0, keepdims=True), 1e-9)
    mod = shape.mean(axis=0)
    mod = mod / mod.sum(axis=0, keepdims=True)
    corr = [float(np.corrcoef(obs[:, d], mod[:, d])[0, 1]) for d in range(3)]
    return {"available": True, "sensors": int(df["sensor_id"].n_unique()),
            "hour_correlation_weekday_sat_sun": [round(c, 3) for c in corr],
            "note": "the permanent counters are greenway/bridge sites; a moderate correlation is expected",
            "observed_share": np.round(obs[:, 0], 4).tolist(), "modelled_share": np.round(mod[:, 0], 4).tolist()}
