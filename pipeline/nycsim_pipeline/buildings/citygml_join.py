"""CityGML -> buildings join: ``data/processed/buildings/roof_attrs.parquet`` (DATA_CONTRACTS §5 roof columns).

This stage turns the per-BIN CityGML LOD2 index (``buildings/citygml/index.parquet``) into the single
table ``buildings/build.py`` consumes to fill the §5 roof columns and the ``ROOF_REAL`` fidelity bit:

    python -m nycsim_pipeline citygml --join            # writes data/processed/buildings/roof_attrs.parquet

Why ``roof_type`` is not simply the CityGML value
-------------------------------------------------
The NYC 3-D Building Model (DoITT, 2014 LiDAR) carries **no sloped roof geometry at all**: every
``bldg:RoofSurface`` polygon in the 13.8 GB delivery is exactly horizontal (normal (0,0,1), zero z-range)
in the source EPSG:2263 feet, in every borough. It is a multi-level *flat-massing* model, not a
roof-shape model — see ``docs/verification/citygml/roof_evidence_da4_queens.json`` and ADR-013.
Therefore:

* ``citygml_match``/``roof_mesh_ref``/``n_roof_levels``/``z_roof_max`` are **real measured** values and
  drive ``ROOF_REAL`` — the LOD2 massing (real roof outline, real stepped levels, real height) is real.
* ``roof_type`` is *not* measurable from CityGML. It is resolved in this order and always stamped in
  ``roof_type_source``:
    0 ``citygml``  — CityGML reported a non-flat form (never happens with the 2014 delivery; kept so the
                     code stays correct if DoITT ever publishes sloped LOD2)
    1 ``osm``      — a real ``roof:shape`` tag on the OSM building whose centroid matches the footprint
    2 ``inferred`` — PLUTO building class + footprint/lot shape say this is detached 1–2-family stock,
                     which in NYC is pitched (rule and measured precision below)
    3 ``default``  — no evidence: flat (the overwhelming majority of NYC roofs really are flat)
  ``roof_inferred`` is True for sources 2 and 3.

Inference rule (source 2), calibrated against the 1,174 OSM-``roof:shape``-tagged buildings that match a
NYC footprint (``docs/verification/citygml/REPORT.md``):

    bldg_class in PITCHED_CLASSES (one- and two-family dwellings + 1-family condos)
    and bldg_frontage / lot_frontage < 0.80      (a gap beside the house: detached, not a party wall)
    and short side of the minimum rotated rectangle <= 14 m   (a span a domestic roof can cover)
    and floors <= 3 and footprint area <= 400 m^2

Measured on that sample: precision 0.831, recall 0.431 (conservative on purpose — a false pitched roof is
more visible than a missed one). Gable vs hip is **not** decidable from the available attributes
(footprint aspect ratio separates OSM ``gabled`` from ``hipped`` at 0.55 accuracy vs a 0.556 majority
baseline), so every inferred pitched roof is reported as ``gable`` with its ridge along the long axis of
the minimum rotated rectangle, and that limitation is stated in the report.

Geometry of an inferred roof: the LiDAR-derived flat plane at ``z_roof_max`` is the best-fit plane of the
real roof surface, i.e. approximately the mean of eave and ridge. The inferred roof therefore keeps that
mean: eave at ``z_roof_max + roof_eave_dz_m`` (negative), ridge at ``z_roof_max + roof_ridge_dz_m``
(positive), pitch ``roof_pitch_deg`` (30° nominal, the common 7:12 NYC domestic pitch), rise clamped to
[0.9, 3.0] m with the pitch recomputed when the clamp bites.

Output schema ``buildings_roof_attrs_v1`` (one row per BIN in ``buildings_base.parquet``)
----------------------------------------------------------------------------------------
Required by DATA_CONTRACTS §5 / the buildings stage:
  bin int64, roof_type int8 (0..8 §5 enum), n_roof_levels int16, z_roof_max float32 (m NAVD88),
  roof_mesh_ref string, citygml_match bool, dz_vs_footprint_m float32
Appended (documented extension, see DATA_CONTRACTS §5.3 note in the report):
  roof_type_source int8, roof_inferred bool, roof_type_conf float32, roof_pitch_deg float32,
  roof_ridge_deg float32 (compass heading of the ridge line, NaN when not pitched),
  roof_eave_dz_m float32, roof_ridge_dz_m float32, z_ground_min float32, n_roof_faces int32,
  tri_count int32, citygml_da int8, citygml_flags uint16
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from ..manifest import record_processed
from ..paths import PROCESSED, VERIFICATION
from .citygml_roof import ROOF_BARREL, ROOF_COMPLEX, ROOF_DOME, ROOF_FLAT, ROOF_GABLE, ROOF_HIP, ROOF_MANSARD, \
    ROOF_NAMES, ROOF_SAWTOOTH, ROOF_SHED

log = logging.getLogger("nycsim.citygml.join")

CITYGML_DIR = PROCESSED / "buildings" / "citygml"
INDEX_PATH = CITYGML_DIR / "index.parquet"
BASE_PATH = PROCESSED / "buildings" / "buildings_base.parquet"
OSM_BUILDINGS = PROCESSED / "osm" / "buildings.parquet"
OUT_PATH = PROCESSED / "buildings" / "roof_attrs.parquet"
SCHEMA_ID = "buildings_roof_attrs_v1"

SRC_CITYGML, SRC_OSM, SRC_INFERRED, SRC_DEFAULT = 0, 1, 2, 3
SOURCE_NAMES = ("citygml", "osm", "inferred", "default")

# --- inference parameters (calibrated, see module docstring) ---------------------------------------
PITCHED_CLASSES = frozenset({
    "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9",   # one-family dwellings
    "B1", "B2", "B3", "B9",                                        # two-family dwellings
    "R1", "R3",                                                    # condominium one-family houses
})
FRONT_RATIO_MAX = 0.80        # bldg_frontage / lot_frontage below this = a side yard exists = detached
MAX_SPAN_M = 14.0             # short side of the minimum rotated rectangle a domestic roof can span
MAX_FLOORS = 3
MAX_FOOTPRINT_M2 = 400.0
INFER_PRECISION = 0.831       # measured against the OSM roof:shape sample (n = 1174)
OSM_CONF = 1.0
PITCH_DEG = 30.0              # 7:12, the common NYC one/two-family pitch
RISE_MIN_M = 0.9
RISE_MAX_M = 3.0
OSM_MATCH_DIST_M = 6.0
BASE_BATCH = 100_000

OSM_ROOF_SHAPE_TO_TYPE = {
    "flat": ROOF_FLAT,
    "gabled": ROOF_GABLE, "gambrel": ROOF_GABLE, "saltbox": ROOF_GABLE, "double_saltbox": ROOF_GABLE,
    "quadruple_saltbox": ROOF_GABLE, "round_gabled": ROOF_GABLE, "crosspitched": ROOF_GABLE,
    "hipped": ROOF_HIP, "half-hipped": ROOF_HIP, "hipped-and-gabled": ROOF_HIP, "pyramidal": ROOF_HIP,
    "side_hipped": ROOF_HIP,
    "mansard": ROOF_MANSARD,
    "skillion": ROOF_SHED, "shed": ROOF_SHED, "lean_to": ROOF_SHED,
    "sawtooth": ROOF_SAWTOOTH,
    "dome": ROOF_DOME, "onion": ROOF_DOME, "cone": ROOF_DOME, "conical": ROOF_DOME, "spherical": ROOF_DOME,
    "round": ROOF_BARREL, "barrel": ROOF_BARREL, "arched": ROOF_BARREL, "quonset": ROOF_BARREL,
    "many": ROOF_COMPLEX, "complex": ROOF_COMPLEX, "multi": ROOF_COMPLEX,
}

BASE_COLUMNS = ["bin", "bldg_class", "borough", "floors", "height", "ground_z", "footprint_area",
                "lot_frontage", "bldg_frontage", "tx", "ty", "footprint", "centroid_x", "centroid_y"]
INDEX_COLUMNS = ["bin", "bin_ok", "da", "roof_type", "n_roof_levels", "z_ground_min", "z_roof_max",
                 "tri_count", "flags", "tx", "ty"]

SCHEMA = pa.schema([
    ("bin", pa.int64()),
    ("roof_type", pa.int8()),
    ("n_roof_levels", pa.int16()),
    ("z_roof_max", pa.float32()),
    ("roof_mesh_ref", pa.string()),
    ("citygml_match", pa.bool_()),
    ("dz_vs_footprint_m", pa.float32()),
    ("roof_type_source", pa.int8()),
    ("roof_inferred", pa.bool_()),
    ("roof_type_conf", pa.float32()),
    ("roof_pitch_deg", pa.float32()),
    ("roof_ridge_deg", pa.float32()),
    ("roof_eave_dz_m", pa.float32()),
    ("roof_ridge_dz_m", pa.float32()),
    ("z_ground_min", pa.float32()),
    ("tri_count", pa.int32()),
    ("citygml_da", pa.int8()),
    ("citygml_flags", pa.uint16()),
])


def _schema_doc(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = {
        "schema_version": 1,
        "schema": SCHEMA_ID,
        "crs": "z metres NAVD88; ridge azimuth in compass degrees (0 = north, clockwise)",
        "roof_type": dict(enumerate(ROOF_NAMES)),
        "roof_type_source": dict(enumerate(SOURCE_NAMES)),
        "roof_mesh_ref": "'t_{tx}_{ty}/roofs.glb#bin_{bin}' when a CityGML LOD2 solid exists, else ''",
        "inference_rule": {
            "classes": sorted(PITCHED_CLASSES), "front_ratio_max": FRONT_RATIO_MAX, "max_span_m": MAX_SPAN_M,
            "max_floors": MAX_FLOORS, "max_footprint_m2": MAX_FOOTPRINT_M2, "pitch_deg": PITCH_DEG,
            "rise_clamp_m": [RISE_MIN_M, RISE_MAX_M], "measured_precision": INFER_PRECISION,
            "gable_vs_hip": "not decidable from available attributes; every inferred pitched roof is reported as gable",
        },
        "source": "doitt_3d_citygml + mappluto (via buildings_base) + osm roof:shape",
    }
    if extra:
        doc.update(extra)
    return doc


# --------------------------------------------------------------------------- footprint shape features
def rect_features(geoms: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Short side, long side and long-axis compass heading of each footprint's minimum rotated rectangle.

    Degenerate geometries (empty, a point, a line) yield ``(0, 0, nan)`` instead of raising.
    Returns ``(width_m, length_m, long_axis_heading_deg)`` with the heading in [0, 180).
    """
    n = len(geoms)
    w = np.zeros(n, dtype=np.float64)
    ln = np.zeros(n, dtype=np.float64)
    head = np.full(n, np.nan, dtype=np.float64)
    if n == 0:
        return w, ln, head
    mrr = shapely.minimum_rotated_rectangle(geoms)
    npts = shapely.get_num_coordinates(mrr)
    good = np.nonzero(npts == 5)[0]
    if good.size == 0:
        return w, ln, head
    co = shapely.get_coordinates(mrr[good]).reshape(-1, 5, 2)
    d = co[:, 1:4] - co[:, 0:3]                       # three consecutive edges; the first two are the sides
    e = np.hypot(d[:, :, 0], d[:, :, 1])
    e0, e1 = e[:, 0], e[:, 1]
    short = np.minimum(e0, e1)
    long_ = np.maximum(e0, e1)
    take0 = e0 >= e1
    vx = np.where(take0, d[:, 0, 0], d[:, 1, 0])
    vy = np.where(take0, d[:, 0, 1], d[:, 1, 1])
    hd = np.degrees(np.arctan2(vx, vy)) % 180.0       # compass heading of the long axis, folded to [0, 180)
    w[good] = short
    ln[good] = long_
    head[good] = hd
    return w, ln, head


def load_base_features(base_path: Path = BASE_PATH, batch_size: int = BASE_BATCH) -> pd.DataFrame:
    """Per-BIN attributes and footprint shape features from ``buildings_base.parquet`` (bounded memory).

    The footprint WKB is decoded one row group at a time and only the derived scalars are kept, so peak
    memory stays around one batch of polygons rather than 1.08 M shapely objects.
    """
    pf = pq.ParquetFile(base_path)
    out: list[pd.DataFrame] = []
    for batch in pf.iter_batches(batch_size=batch_size, columns=BASE_COLUMNS):
        d = batch.to_pandas()
        geoms = shapely.from_wkb(d.pop("footprint").to_numpy())
        w, ln, hd = rect_features(geoms)
        d["rect_w"] = w
        d["rect_l"] = ln
        d["rect_heading"] = hd
        out.append(d)
    if not out:
        raise ValueError(f"{base_path} has no rows")
    df = pd.concat(out, ignore_index=True)
    log.info("buildings_base: %d rows, footprint shape features computed", len(df))
    return df


# --------------------------------------------------------------------------- OSM roof:shape (real tags)
def load_osm_roof_shapes(base: pd.DataFrame, osm_path: Path = OSM_BUILDINGS,
                         max_dist_m: float = OSM_MATCH_DIST_M) -> tuple[pd.Series, dict[str, Any]]:
    """Map real OSM ``roof:shape`` tags onto BINs by nearest footprint centroid.

    Returns ``(Series roof_type indexed by bin, stats)``. Missing/unreadable OSM data is not an error:
    the stage simply has no OSM evidence and says so in the summary.
    """
    stats: dict[str, Any] = {"available": False, "tagged": 0, "matched": 0, "used": 0, "max_dist_m": max_dist_m}
    if not osm_path.exists():
        log.warning("no OSM buildings at %s: roof:shape evidence skipped", osm_path)
        return pd.Series(dtype=np.int8), stats
    try:
        from scipy.spatial import cKDTree
    except ImportError:  # pragma: no cover - scipy is a pipeline dependency
        log.warning("scipy unavailable: OSM roof:shape evidence skipped")
        return pd.Series(dtype=np.int8), stats
    osm = pq.read_table(osm_path, columns=["roof_shape", "cx", "cy"]).to_pandas()
    osm = osm[osm.roof_shape.notna() & (osm.roof_shape.astype(str).str.len() > 0)]
    stats["available"] = True
    stats["tagged"] = int(len(osm))
    if osm.empty:
        return pd.Series(dtype=np.int8), stats
    shape = osm.roof_shape.astype(str).str.strip().str.lower()
    code = shape.map(OSM_ROOF_SHAPE_TO_TYPE)
    keep = code.notna() & np.isfinite(osm.cx) & np.isfinite(osm.cy)
    osm = osm[keep]
    code = code[keep].astype(np.int8)
    stats["recognised_tags"] = int(len(osm))
    stats["unrecognised_tags"] = sorted(set(shape[~shape.isin(OSM_ROOF_SHAPE_TO_TYPE)].unique()))[:20]
    tree = cKDTree(base[["centroid_x", "centroid_y"]].to_numpy())
    dist, idx = tree.query(osm[["cx", "cy"]].to_numpy(), distance_upper_bound=max_dist_m)
    hit = np.isfinite(dist)
    stats["matched"] = int(hit.sum())
    if not hit.any():
        return pd.Series(dtype=np.int8), stats
    bins = base.bin.to_numpy()[idx[hit]]
    s = pd.Series(code.to_numpy()[hit], index=bins)
    # a BIN matched by several OSM ways keeps the non-flat tag (a mapper who bothered with a shape is
    # more informative than a default 'flat'), then the first
    s = s.groupby(level=0).agg(lambda v: int(v[v != ROOF_FLAT].iloc[0]) if (v != ROOF_FLAT).any() else int(v.iloc[0]))
    stats["used"] = int(len(s))
    stats["hist"] = {ROOF_NAMES[int(k)]: int(v) for k, v in s.value_counts().sort_index().items()}
    log.info("OSM roof:shape: %d tagged, %d matched within %.0f m, %d BINs used", stats["tagged"], stats["matched"],
             max_dist_m, stats["used"])
    return s, stats


# --------------------------------------------------------------------------- pitched-roof inference
def infer_pitched(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``is_pitched`` plus the pitched-roof geometry columns to a frame of base features.

    See the module docstring for the rule and its measured precision. Every column is finite; buildings
    that are not inferred pitched get ``roof_pitch_deg = 0``, ``roof_ridge_deg = nan`` and zero offsets.
    """
    front_ratio = np.where(df.lot_frontage.to_numpy() > 0.0,
                           df.bldg_frontage.to_numpy() / np.maximum(df.lot_frontage.to_numpy(), 1e-6), np.nan)
    detached = np.isfinite(front_ratio) & (front_ratio < FRONT_RATIO_MAX)
    is_pitched = (
        df.bldg_class.isin(PITCHED_CLASSES).to_numpy()
        & detached
        & (df.rect_w.to_numpy() <= MAX_SPAN_M) & (df.rect_w.to_numpy() > 0.0)
        & (df.floors.to_numpy() <= MAX_FLOORS)
        & (df.footprint_area.to_numpy() <= MAX_FOOTPRINT_M2)
    )
    span = np.where(is_pitched, df.rect_w.to_numpy(), 0.0)
    rise = 0.5 * span * math.tan(math.radians(PITCH_DEG))
    rise = np.clip(rise, RISE_MIN_M, RISE_MAX_M)
    rise = np.where(is_pitched, rise, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        pitch = np.degrees(np.arctan2(rise, np.maximum(0.5 * span, 1e-6)))
    pitch = np.where(is_pitched, pitch, 0.0)
    # ridge runs along the long axis of the minimum rotated rectangle
    ridge = np.where(is_pitched, df.rect_heading.to_numpy(), np.nan)
    return df.assign(is_pitched=is_pitched,
                     front_ratio=front_ratio,
                     roof_pitch_deg=pitch.astype(np.float32),
                     roof_ridge_deg=ridge.astype(np.float32),
                     roof_eave_dz_m=(-0.5 * rise).astype(np.float32),
                     roof_ridge_dz_m=(0.5 * rise).astype(np.float32))


# --------------------------------------------------------------------------- main build
def build_roof_attrs(*, index_path: Path = INDEX_PATH, base_path: Path = BASE_PATH, osm_path: Path = OSM_BUILDINGS,
                     out_path: Path = OUT_PATH, manifest: bool = True,
                     summary_json: Path | None = None) -> dict[str, Any]:
    """Build ``roof_attrs.parquet`` from the CityGML index, ``buildings_base`` and OSM roof tags."""
    t0 = time.time()
    if not index_path.exists():
        raise FileNotFoundError(f"{index_path} not found - run `python -m nycsim_pipeline citygml --build-index` first")
    base = load_base_features(base_path)
    idx = pq.read_table(index_path, columns=INDEX_COLUMNS).to_pandas()
    idx = idx[idx.bin_ok & (idx.bin > 0)].drop(columns=["bin_ok"])
    idx = idx.sort_values(["bin", "tri_count"], ascending=[True, False]).drop_duplicates("bin", keep="first")
    log.info("citygml index: %d rows with a usable BIN from %s", len(idx), index_path)

    df = base.merge(idx, on="bin", how="left", suffixes=("", "_cg"))
    match = df.tri_count.notna().to_numpy() & (df.tri_count.fillna(0).to_numpy() > 0)
    df = infer_pitched(df)

    osm_type, osm_stats = load_osm_roof_shapes(base, osm_path)
    osm_col = df.bin.map(osm_type) if len(osm_type) else pd.Series(np.nan, index=df.index)
    has_osm = osm_col.notna().to_numpy()

    cg_type = df.roof_type.fillna(ROOF_FLAT).to_numpy().astype(np.int8)
    cg_nonflat = match & (cg_type != ROOF_FLAT)

    roof_type = np.full(len(df), ROOF_FLAT, dtype=np.int8)
    source = np.full(len(df), SRC_DEFAULT, dtype=np.int8)
    conf = np.zeros(len(df), dtype=np.float32)

    inferred = df.is_pitched.to_numpy()
    roof_type[inferred] = ROOF_GABLE
    source[inferred] = SRC_INFERRED
    conf[inferred] = INFER_PRECISION

    roof_type[has_osm] = osm_col[has_osm].to_numpy().astype(np.int8)
    source[has_osm] = SRC_OSM
    conf[has_osm] = OSM_CONF

    roof_type[cg_nonflat] = cg_type[cg_nonflat]
    source[cg_nonflat] = SRC_CITYGML
    conf[cg_nonflat] = 1.0

    # geometry columns only make sense for an inferred pitched roof that survived the precedence above
    keep_pitch = inferred & (source == SRC_INFERRED)
    pitch = np.where(keep_pitch, df.roof_pitch_deg.to_numpy(), 0.0).astype(np.float32)
    ridge = np.where(keep_pitch, df.roof_ridge_deg.to_numpy(), np.nan).astype(np.float32)
    eave_dz = np.where(keep_pitch, df.roof_eave_dz_m.to_numpy(), 0.0).astype(np.float32)
    ridge_dz = np.where(keep_pitch, df.roof_ridge_dz_m.to_numpy(), 0.0).astype(np.float32)

    # the mesh lives in the tile the CityGML solid's own centroid falls in; fall back to the footprint tile
    tx = df.tx_cg.where(df.tx_cg.notna(), df.tx).fillna(0).to_numpy().astype(np.int64)
    ty = df.ty_cg.where(df.ty_cg.notna(), df.ty).fillna(0).to_numpy().astype(np.int64)
    bins_arr = df.bin.to_numpy().astype(np.int64)
    mesh_ref = [f"t_{tx[i]}_{ty[i]}/roofs.glb#bin_{bins_arr[i]}" if match[i] else "" for i in range(len(df))]
    z_roof_max = df.z_roof_max.to_numpy(dtype=np.float64)
    fp_roof = (df.ground_z.to_numpy(dtype=np.float64) + df.height.to_numpy(dtype=np.float64))
    dz = np.where(match, z_roof_max - fp_roof, np.nan)

    table = pa.Table.from_pydict({
        "bin": df.bin.to_numpy().astype(np.int64),
        "roof_type": roof_type,
        "n_roof_levels": df.n_roof_levels.fillna(0).to_numpy().astype(np.int16),
        "z_roof_max": np.where(match, z_roof_max, np.nan).astype(np.float32),
        "roof_mesh_ref": pa.array(mesh_ref, type=pa.string()),
        "citygml_match": match,
        "dz_vs_footprint_m": dz.astype(np.float32),
        "roof_type_source": source,
        "roof_inferred": source >= SRC_INFERRED,
        "roof_type_conf": conf,
        "roof_pitch_deg": pitch,
        "roof_ridge_deg": ridge,
        "roof_eave_dz_m": eave_dz,
        "roof_ridge_dz_m": ridge_dz,
        "z_ground_min": np.where(match, df.z_ground_min.to_numpy(dtype=np.float64), np.nan).astype(np.float32),
        "tri_count": df.tri_count.fillna(0).to_numpy().astype(np.int32),
        "citygml_da": df.da.fillna(0).to_numpy().astype(np.int8),
        "citygml_flags": df["flags"].fillna(0).to_numpy().astype(np.uint16),
    }, schema=SCHEMA)
    table = table.sort_by([("bin", "ascending")])

    dz_ok = dz[np.isfinite(dz)]
    summary: dict[str, Any] = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": int(table.num_rows),
        "citygml_match": int(match.sum()),
        "citygml_match_rate": float(match.mean()),
        "roof_type_hist": {ROOF_NAMES[i]: int((roof_type == i).sum()) for i in range(len(ROOF_NAMES))},
        "roof_type_source_hist": {SOURCE_NAMES[i]: int((source == i).sum()) for i in range(len(SOURCE_NAMES))},
        "roof_inferred_rows": int((source >= SRC_INFERRED).sum()),
        "pitched_rows": int((roof_type != ROOF_FLAT).sum()),
        "pitched_frac": float((roof_type != ROOF_FLAT).mean()),
        "dz_vs_footprint_m": {
            "n": int(dz_ok.size),
            "median_abs": float(np.median(np.abs(dz_ok))) if dz_ok.size else float("nan"),
            "mean": float(dz_ok.mean()) if dz_ok.size else float("nan"),
            "p99_abs": float(np.percentile(np.abs(dz_ok), 99)) if dz_ok.size else float("nan"),
            "frac_within_1m": float((np.abs(dz_ok) <= 1.0).mean()) if dz_ok.size else float("nan"),
        },
        "n_roof_levels_hist": {int(k): int(v) for k, v in
                               pd.Series(table.column("n_roof_levels").to_numpy()).value_counts().sort_index().items()},
        "osm": osm_stats,
        "inference_rule": _schema_doc()["inference_rule"],
        "elapsed_s": round(time.time() - t0, 1),
    }
    table = table.replace_schema_metadata({"nycsim.schema": SCHEMA_ID,
                                           "nycsim.roof_attrs": json.dumps(_schema_doc({"summary": summary}))})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".part")
    pq.write_table(table, tmp, compression="snappy")
    os.replace(tmp, out_path)
    summary["path"] = str(out_path)
    if manifest:
        record_processed("buildings_roof_attrs", out_path, stage="citygml", sources=["doitt_3d_citygml", "osm", "mappluto"],
                         rows=table.num_rows, schema=SCHEMA_ID,
                         extra={k: summary[k] for k in ("citygml_match", "citygml_match_rate", "roof_type_hist",
                                                        "roof_type_source_hist")})
    summary_json = summary_json or (VERIFICATION / "citygml" / "roof_attrs_summary.json")
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_json, "w") as f:
        json.dump(summary, f, indent=1, default=str)
    summary["summary_json"] = str(summary_json)
    log.info("roof_attrs: %d rows, %d with CityGML mesh (%.2f%%), %d pitched (%.2f%%) -> %s", table.num_rows,
             summary["citygml_match"], 100 * summary["citygml_match_rate"], summary["pitched_rows"],
             100 * summary["pitched_frac"], out_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nycsim_pipeline citygml --join", description=__doc__.split("\n\n")[0])
    ap.add_argument("--index", type=Path, default=INDEX_PATH)
    ap.add_argument("--base", type=Path, default=BASE_PATH)
    ap.add_argument("--osm", type=Path, default=OSM_BUILDINGS)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, stream=sys.stderr,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = build_roof_attrs(index_path=a.index, base_path=a.base, osm_path=a.osm, out_path=a.out,
                         manifest=not a.no_manifest)
    print(json.dumps(s, indent=1, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
