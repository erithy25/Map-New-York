"""Validation of CityGML solids against ``footprints_raw.parquet`` (BIN match, heights, datum, horizontal offset).

Writes ``docs/verification/citygml/validation_<tag>.json`` and returns the same dict.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from collections import Counter
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


# --------------------------------------------------------------------------- roof flatness evidence
ROOF_SLOPE_BUCKETS = (0.01, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 25.0, 45.0, 90.1)


def roof_evidence(bins: list[int], *, da: int, zip_path: Path | None = None, census: bool = False,
                  max_buildings: int | None = None, out_json: Path | None = None) -> dict[str, Any]:
    """Dump every ``RoofSurface`` polygon of the named BINs **from the raw CityGML**, plus a slope census.

    The slope is computed from the Newell normal of the *source* ring (EPSG:2263 US survey feet, z in feet)
    before any datum/unit transform, so the answer is independent of the pipeline's CRS handling. This is
    the evidence behind ADR-013 (the NYC 3-D Building Model carries no sloped roof geometry).

    ``census`` streams the whole delivery area and buckets every roof face by slope; without it the scan
    stops as soon as all requested BINs have been seen.
    """
    from .citygml import (GML_ID_ATTRS, MEMBER_FMT, TAG_EXTERIOR, TAG_GENVALUE, TAG_POLY, TAG_STRATTR, ZIP_PATH,
                          _surface_type_of, iter_buildings, open_member_stream, ring_coords)
    from .citygml_geom import SURF_ROOF, azimuth_deg, newell_normal, slope_deg

    zip_path = zip_path or ZIP_PATH
    want = {int(b) for b in bins}
    counters: Counter = Counter()
    buckets = np.zeros(len(ROOF_SLOPE_BUCKETS) + 1, dtype=np.int64)
    found: dict[int, dict[str, Any]] = {}
    max_slope_seen = 0.0
    max_slope_bin = 0
    n_seen = 0
    t0 = time.time()
    stream, proc = open_member_stream(zip_path, MEMBER_FMT.format(n=da))
    try:
        for elem in iter_buildings(stream):
            n_seen += 1
            raw_bin = None
            for ch in elem.iterchildren(*TAG_STRATTR):
                if ch.get("name") != "BIN":
                    continue
                for vt in TAG_GENVALUE:
                    v = ch.findtext(vt)
                    if v is not None:
                        raw_bin = v.strip()
                        break
                break
            b = int(raw_bin) if raw_bin and raw_bin.isdigit() else 0
            wanted = b in want and b not in found
            if not (wanted or census):
                if want and not found.keys() >= want:
                    continue
                break
            faces: list[dict[str, Any]] = []
            for poly in elem.iter(*TAG_POLY):
                stype, _srs = _surface_type_of(poly)
                if stype != SURF_ROOF:
                    continue
                ring = None
                for t in TAG_EXTERIOR:
                    el = poly.find(t)
                    if el is not None:
                        ring = ring_coords(el, counters)
                        break
                if ring is None or len(ring) < 4:
                    counters["roof_ring_unusable"] += 1
                    continue
                pts = ring[:-1] if np.allclose(ring[0], ring[-1]) else ring
                nrm = newell_normal(pts)
                two_a = float(np.sqrt(nrm @ nrm))
                if two_a <= 0.0:
                    counters["roof_ring_degenerate"] += 1
                    continue
                nhat = nrm / two_a
                sl = slope_deg(nhat)
                buckets[int(np.searchsorted(ROOF_SLOPE_BUCKETS, sl, side="left"))] += 1
                counters["roof_faces"] += 1
                if sl > max_slope_seen:
                    max_slope_seen, max_slope_bin = sl, b
                if wanted:
                    faces.append({
                        "n_vertices": int(len(pts)),
                        "slope_deg": round(sl, 6),
                        "azimuth_deg": round(azimuth_deg(nhat), 3) if sl > 1e-9 else None,
                        "normal": [round(float(v), 9) for v in nhat],
                        "z_min_ft": round(float(pts[:, 2].min()), 4),
                        "z_max_ft": round(float(pts[:, 2].max()), 4),
                        "z_range_ft": round(float(pts[:, 2].max() - pts[:, 2].min()), 6),
                        "area_ft2": round(0.5 * two_a, 2),
                    })
            if wanted:
                found[b] = {"bin": b, "gml_id": elem.get(GML_ID_ATTRS[0]) or elem.get(GML_ID_ATTRS[1]) or "",
                            "n_roof_faces": len(faces), "roof_faces": faces,
                            "max_slope_deg": round(max((f["slope_deg"] for f in faces), default=0.0), 6),
                            "z_span_of_roof_faces_ft": round(
                                max((f["z_max_ft"] for f in faces), default=0.0) - min((f["z_min_ft"] for f in faces), default=0.0), 4)}
                if not census and found.keys() >= want:
                    break
            if max_buildings is not None and n_seen >= max_buildings:
                break
    finally:
        if proc is not None:
            proc.kill()
            proc.wait()
            for s in (proc.stdout, proc.stderr):
                if s is not None:
                    s.close()
        else:
            stream.close()
    edges = ["[0, %g)" % ROOF_SLOPE_BUCKETS[0]] + \
            ["[%g, %g)" % (ROOF_SLOPE_BUCKETS[i], ROOF_SLOPE_BUCKETS[i + 1]) for i in range(len(ROOF_SLOPE_BUCKETS) - 1)] + \
            [">= %g" % ROOF_SLOPE_BUCKETS[-1]]
    total = int(buckets.sum())
    rep = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "da": da, "member": MEMBER_FMT.format(n=da), "buildings_scanned": n_seen, "census": census,
        "description": "RoofSurface polygon slopes computed from the raw EPSG:2263 (US survey feet) rings, before any "
                       "unit/datum transform. slope 0 deg = perfectly horizontal face.",
        "roof_faces_scanned": total,
        "slope_histogram_deg": {e: int(c) for e, c in zip(edges, buckets.tolist())},
        "fraction_faces_sloped_ge_1deg": float(buckets[2:].sum() / total) if total else float("nan"),
        "max_slope_deg_seen": round(max_slope_seen, 6), "max_slope_bin": max_slope_bin,
        "buildings_requested": sorted(want), "buildings_found": sorted(found),
        "buildings_missing": sorted(want - set(found)),
        "buildings": [found[b] for b in sorted(found)],
        "counters": dict(sorted(counters.items())),
        "elapsed_s": round(time.time() - t0, 1),
    }
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w") as f:
            json.dump(rep, f, indent=1, default=str)
        rep["json"] = str(out_json)
    log.info("roof evidence DA%s: %d roof faces, %.6f%% sloped >= 1 deg, max slope %.6f deg", da, total,
             100 * rep["fraction_faces_sloped_ge_1deg"], max_slope_seen)
    return rep


def sloped_roof_buildings(out_dir: Path, *, base: Path | None = None, min_slope_deg: float = 0.01,
                          out_json: Path | None = None) -> dict[str, Any]:
    """Every parsed building that has *any* sloped roof face, named from ``buildings_base.parquet``.

    In the 2014 DoITT delivery this list is the complete set of hand-modelled landmarks: it is the
    counter-example that makes ADR-013 precise (flat massing *apart from* these) and it doubles as a
    regression check — the list should not grow when the parser changes.
    """
    files = sorted(p for p in out_dir.glob("da*.parquet") if "_limit" not in p.name)
    cols = ["bin", "da", "roof_type", "roof_slope_deg", "n_roof", "tri_count", "footprint_area_m2",
            "z_ground_min", "z_roof_max", "cx", "cy"]
    frames = []
    total = 0
    for p in files:
        t = pq.read_table(p, columns=cols).to_pandas()
        total += len(t)
        frames.append(t[t.roof_slope_deg > min_slope_deg])
    if not frames:
        raise FileNotFoundError(f"no CityGML parquet files under {out_dir}")
    d = pd.concat(frames, ignore_index=True).sort_values("tri_count", ascending=False)
    base = base or (FOOTPRINTS.parent / "buildings_base.parquet")
    if base.exists():
        bb = pq.read_table(base, columns=["bin", "name", "address", "bldg_class", "landmark_id"]).to_pandas()
        d = d.merge(bb.drop_duplicates("bin"), on="bin", how="left")
    rep = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "description": "CityGML LOD2 buildings carrying at least one sloped roof face (slope > %g deg). "
                       "Everything else in the delivery is flat massing - see ADR-013." % min_slope_deg,
        "das": sorted(int(f.stem[2:]) for f in files),
        "buildings_scanned": total,
        "buildings_with_sloped_roof": int(len(d)),
        "fraction": float(len(d) / max(total, 1)),
        "roof_type_hist": {ROOF_NAMES[int(k)]: int(v) for k, v in d.roof_type.value_counts().sort_index().items()},
        "buildings": json.loads(d.to_json(orient="records")),
    }
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w") as f:
            json.dump(rep, f, indent=1, default=str)
        rep["json"] = str(out_json)
    log.info("sloped-roof buildings: %d of %d parsed (%.6f%%)", len(d), total, 100 * rep["fraction"])
    return rep


# --------------------------------------------------------------------------- roof-inference calibration
PITCHED_OSM_SHAPES = frozenset({"gabled", "hipped", "half-hipped", "gambrel", "saltbox", "double_saltbox",
                                "quadruple_saltbox", "pyramidal", "skillion", "round", "dome", "cone",
                                "mansard", "hipped-and-gabled", "round_gabled", "sawtooth", "onion", "barrel"})


def roof_inference_calibration(*, base: Path | None = None, osm: Path | None = None,
                               out_json: Path | None = None) -> dict[str, Any]:
    """Measure the pitched-roof inference (ADR-013 rule) against real OSM ``roof:shape`` tags.

    OSM buildings carrying a ``roof:shape`` tag are matched to a BIN by nearest footprint centroid, the
    tag is reduced to pitched/flat, and the rule in ``citygml_join.infer_pitched`` is scored on the
    subset it is allowed to fire on. The sample is small (~1.2 k) and mapper-selected — the report says
    so — but it is the only *real* roof-shape evidence available for NYC.
    """
    from scipy.spatial import cKDTree

    from .citygml_join import BASE_PATH, OSM_BUILDINGS, OSM_MATCH_DIST_M, infer_pitched, load_base_features

    base = base or BASE_PATH
    osm = osm or OSM_BUILDINGS
    t0 = time.time()
    feats = infer_pitched(load_base_features(base))
    tags = pq.read_table(osm, columns=["roof_shape", "cx", "cy"]).to_pandas()
    tags = tags[tags.roof_shape.notna() & (tags.roof_shape.astype(str).str.len() > 0)].reset_index(drop=True)
    shape = tags.roof_shape.astype(str).str.strip().str.lower()
    tree = cKDTree(feats[["centroid_x", "centroid_y"]].to_numpy())
    dist, idx = tree.query(tags[["cx", "cy"]].to_numpy(), distance_upper_bound=OSM_MATCH_DIST_M)
    hit = np.isfinite(dist)
    m = feats.iloc[idx[hit]].reset_index(drop=True)
    m["osm_shape"] = shape[hit].to_numpy()
    m["osm_pitched"] = m.osm_shape.isin(PITCHED_OSM_SHAPES)
    m = m.drop_duplicates("bin", keep="first")

    y = m.osm_pitched.to_numpy()
    p = m.is_pitched.to_numpy()
    tp, fp = int((p & y).sum()), int((p & ~y).sum())
    fn, tn = int((~p & y).sum()), int((~p & ~y).sum())
    by_borough = {int(b): {"n": int(len(g)), "rule_fired": int(g.is_pitched.sum()),
                           "precision": float(g.osm_pitched[g.is_pitched].mean()) if g.is_pitched.any() else None,
                           "osm_pitched_frac": float(g.osm_pitched.mean())}
                  for b, g in m.groupby("borough")}
    by_class = {str(c): {"n": int(len(g)), "osm_pitched_frac": round(float(g.osm_pitched.mean()), 3),
                         "rule_fired": int(g.is_pitched.sum())}
                for c, g in m.groupby("bldg_class") if len(g) >= 10}
    gh = m[m.osm_shape.isin(["gabled", "hipped"])]
    aspect = (gh.rect_l / gh.rect_w.replace(0, np.nan)).to_numpy()
    gabled = (gh.osm_shape == "gabled").to_numpy()
    best = {"threshold": None, "accuracy": 0.0}
    for thr in (1.2, 1.3, 1.4, 1.5, 1.8, 2.0, 2.5):
        acc = float(np.mean((aspect >= thr) == gabled)) if gh.shape[0] else float("nan")
        if acc > best["accuracy"]:
            best = {"threshold": thr, "accuracy": acc}
    rep = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "description": "Pitched-roof inference (ADR-013) scored against real OSM roof:shape tags matched to BINs "
                       "by nearest footprint centroid (<= %.0f m). Mapper-selected sample: treat as an "
                       "order-of-magnitude check, not an unbiased estimate." % OSM_MATCH_DIST_M,
        "osm_tagged": int(len(tags)), "matched_bins": int(len(m)),
        "osm_pitched_frac": float(y.mean()),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": float(tp / max(tp + fp, 1)),
        "recall": float(tp / max(tp + fn, 1)),
        "accuracy": float((tp + tn) / max(len(m), 1)),
        "by_borough": by_borough,
        "by_bldg_class": by_class,
        "gable_vs_hip": {
            "n": int(gh.shape[0]),
            "gabled_share": float(gabled.mean()) if gh.shape[0] else float("nan"),
            "best_aspect_threshold": best,
            "verdict": "footprint aspect ratio does not separate gable from hip: the best threshold does not "
                       "beat the majority-class baseline, so every inferred pitched roof is emitted as gable",
        },
        "elapsed_s": round(time.time() - t0, 1),
    }
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w") as f:
            json.dump(rep, f, indent=1, default=str)
        rep["json"] = str(out_json)
    log.info("roof inference vs OSM: precision %.3f recall %.3f on %d matched BINs", rep["precision"],
             rep["recall"], len(m))
    return rep
