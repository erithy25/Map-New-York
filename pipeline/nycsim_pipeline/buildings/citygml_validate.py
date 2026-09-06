"""Validation of CityGML solids against ``footprints_raw.parquet`` (BIN match, heights, datum, horizontal offset).

Writes ``docs/verification/citygml/validation_<tag>.json`` and returns the same dict.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from ..paths import VERIFICATION
from .citygml_roof import ROOF_NAMES

log = logging.getLogger("nycsim.citygml.validate")

FOOTPRINTS = Path(__file__).resolve().parents[3] / "data" / "processed" / "buildings" / "footprints_raw.parquet"
CGML_COLS = ["bin", "bin_ok", "da", "doitt_id", "z_ground_min", "z_roof_max", "z_roof_main", "cx", "cy",
             "footprint_area_m2", "roof_type", "n_roof_levels", "tri_count", "flags"]
FP_COLS = ["bin", "doitt_id", "ground_z", "height", "cx", "cy", "construction_year", "last_status_type"]
AREA_BATCH = 100_000
UNCHANGED_YEAR_MAX = 2013   # LiDAR flown 2014: buildings built/altered later are legitimately different


def _q(x: pd.Series | np.ndarray, within: float | None = None) -> dict[str, Any]:
    x = pd.Series(np.asarray(x, dtype=np.float64)).dropna()
    if x.empty:
        return {"n": 0}
    d = {"n": int(x.size), "mean": float(x.mean()), "median": float(x.median()), "p10": float(x.quantile(0.10)),
         "p90": float(x.quantile(0.90)), "p99": float(x.quantile(0.99)), "std": float(x.std())}
    if within is not None:
        d[f"frac_abs_within_{within:g}m"] = float((x.abs() <= within).mean())
    return d


def footprint_areas(footprints: Path, bins: np.ndarray) -> pd.Series:
    """Planar area (m^2, NYC_TM) of the footprint WKB polygons for the given BINs, computed batch-wise (bounded memory).

    ``shape_area``/``shape_length`` in footprints_raw are Web-Mercator pseudo-units (ratio to true metres = cos(lat)),
    so the geometry itself is the only trustworthy area source.
    """
    want = np.unique(bins)
    pf = pq.ParquetFile(footprints)
    out_b: list[np.ndarray] = []
    out_a: list[np.ndarray] = []
    for batch in pf.iter_batches(batch_size=AREA_BATCH, columns=["bin", "geometry"]):
        b = batch.column("bin").to_numpy(zero_copy_only=False)
        sel = np.isin(b, want)
        if not sel.any():
            continue
        wkb = batch.column("geometry").filter(pa.array(sel)).to_numpy(zero_copy_only=False)
        out_b.append(b[sel])
        out_a.append(shapely.area(shapely.from_wkb(wkb)))
    if not out_b:
        return pd.Series(dtype=np.float64)
    return pd.Series(np.concatenate(out_a), index=np.concatenate(out_b)).groupby(level=0).first()


def load_solids(out_dir: Path, parquets: list[Path] | None = None) -> pd.DataFrame:
    files = parquets or sorted(p for p in out_dir.glob("da*.parquet") if "_limit" not in p.name)
    frames = [pq.read_table(p, columns=CGML_COLS).to_pandas() for p in files if p.exists()]
    if not frames:
        raise FileNotFoundError(f"no CityGML parquet files under {out_dir}")
    return pd.concat(frames, ignore_index=True)


def validate(out_dir: Path, *, parquets: list[Path] | None = None, footprints: Path = FOOTPRINTS,
             out_json: Path | None = None) -> dict[str, Any]:
    """Join solids to footprints by BIN and report match rate, vertical offsets and horizontal offsets."""
    t0 = time.time()
    cg = load_solids(out_dir, parquets)
    fp = pq.read_table(footprints, columns=FP_COLS).to_pandas()
    fp = fp.drop_duplicates("bin", keep="first")
    fp_by_doitt = set(fp.loc[fp.doitt_id > 0, "doitt_id"].astype(np.int64).tolist())

    das = sorted(int(d) for d in cg.da.unique())
    ok = cg[cg.bin_ok]
    m = ok.merge(fp, on="bin", how="inner", suffixes=("", "_fp"))
    m["roof_fp"] = m.ground_z + m.height
    unchanged = m[(m.construction_year <= UNCHANGED_YEAR_MAX) & (m.last_status_type == "Constructed")]

    per_da = {}
    for d, g in ok.groupby("da"):
        matched = g.bin.isin(fp.bin).sum()
        per_da[int(d)] = {"rows": int(len(g)), "bin_matched": int(matched), "match_rate": float(matched / max(len(g), 1))}

    with_doitt = ok[ok.doitt_id > 0]
    doitt_hit = with_doitt.doitt_id.isin(fp_by_doitt).mean() if len(with_doitt) else float("nan")
    doitt_consistent = float((m.doitt_id == m.doitt_id_fp)[m.doitt_id > 0].mean()) if len(m) else float("nan")

    dz_ground = m.z_ground_min - m.ground_z
    dz_roof_max = m.z_roof_max - m.roof_fp
    dz_roof_main = m.z_roof_main - m.roof_fp
    dx = m.cx - m.cx_fp
    dy = m.cy - m.cy_fp
    dist = np.hypot(dx, dy)
    fa = footprint_areas(footprints, m.bin.to_numpy())
    area_ratio = m.footprint_area_m2.to_numpy() / m.bin.map(fa).to_numpy()
    per_da_xy = {int(d): {"dx_median_m": float(g.dx.median()), "dy_median_m": float(g.dy.median()), "n": int(len(g))}
                 for d, g in m.assign(dx=dx, dy=dy).groupby("da")}

    rt = cg.roof_type.to_numpy()
    rep: dict[str, Any] = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "das": das,
        "rows": int(len(cg)),
        "rows_bin_ok": int(len(ok)),
        "rows_bin_missing_or_placeholder": int(len(cg) - len(ok)),
        "bin_matched": int(len(m)),
        "bin_match_rate": float(len(m) / max(len(ok), 1)),
        "doitt_id_present_rate": float((cg.doitt_id > 0).mean()),
        "doitt_id_hit_rate_in_footprints": float(doitt_hit),
        "doitt_id_consistent_with_bin_match": doitt_consistent,
        "per_da": per_da,
        "vertical_datum_check": {
            "description": "z_ground_min (CityGML z ft x 0.3048006 m) minus footprint ground_z (LiDAR ground elevation). ~0 => CityGML z is feet NAVD88.",
            "dz_ground_m": _q(dz_ground, within=0.5),
            "dz_ground_abs_m": _q(dz_ground.abs()),
        },
        "roof_height_check": {
            "description": "CityGML roof z minus footprint (ground_z + height). 'unchanged' = construction_year <= %d and status Constructed." % UNCHANGED_YEAR_MAX,
            "all": {
                "dz_roof_max_m": _q(dz_roof_max, within=1.0), "dz_roof_max_abs_m": _q(dz_roof_max.abs()),
                "dz_roof_main_m": _q(dz_roof_main, within=1.0), "dz_roof_main_abs_m": _q(dz_roof_main.abs()),
            },
            "unchanged": {
                "n": int(len(unchanged)),
                "dz_roof_max_abs_m": _q((unchanged.z_roof_max - unchanged.roof_fp).abs()),
                "dz_roof_main_abs_m": _q((unchanged.z_roof_main - unchanged.roof_fp).abs()),
                "frac_roof_max_within_1m": float(((unchanged.z_roof_max - unchanged.roof_fp).abs() <= 1.0).mean()) if len(unchanged) else float("nan"),
            },
        },
        "horizontal_check": {
            "description": "CityGML ground-surface centroid (EPSG:2263 -> NYC_TM, see summary['datum']) minus footprint cx/cy (Socrata WGS84 GeoJSON -> NYC_TM), metres.",
            "dx_m": _q(dx), "dy_m": _q(dy), "dist_m": _q(dist, within=1.0), "per_da": per_da_xy,
        },
        "footprint_area_ratio_citygml_over_footprint_geometry": _q(area_ratio),
        "roof_type_hist": {ROOF_NAMES[i]: int((rt == i).sum()) for i in range(len(ROOF_NAMES))},
        "roof_type_frac": {ROOF_NAMES[i]: float((rt == i).mean()) for i in range(len(ROOF_NAMES))},
        "n_roof_levels_hist": {int(k): int(v) for k, v in cg.n_roof_levels.value_counts().sort_index().items()},
        "tri_count_total": int(cg.tri_count.sum()),
        "tri_count_per_building": _q(cg.tri_count),
        "elapsed_s": round(time.time() - t0, 1),
    }
    tag = "da" + "_".join(str(d) for d in das) if len(das) <= 3 else "all"
    out_json = out_json or (VERIFICATION / "citygml" / f"validation_{tag}.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(rep, f, indent=1, default=str)
    rep["json"] = str(out_json)
    log.info("validation: %d/%d BIN matched (%.2f%%), median |dz_roof_max| %.3f m, dz_ground mean %.3f m -> %s", len(m), len(ok),
             100 * rep["bin_match_rate"], rep["roof_height_check"]["all"]["dz_roof_max_abs_m"].get("median", float("nan")),
             rep["vertical_datum_check"]["dz_ground_m"].get("mean", float("nan")), out_json)
    return rep
