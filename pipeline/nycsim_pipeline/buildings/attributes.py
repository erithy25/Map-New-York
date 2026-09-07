"""Auxiliary per-building attribute sources.

* Building Elevation & Subgrade (bsin-59hv): per-BIN grade / first-floor elevation (ft NAVD88), subgrade flag, address, NTA2020.
* DOB NOW sidewalk-shed permits (rbx6-tga4): active sheds by BIN.
* LPC individual landmark sites (buis-pvji), historic districts (skyk-mpzq), building database (gpmc-yuvp).
* NTA 2020 polygons (9nt8-h7nd) for footprints not covered by bsin.

Socrata "GeoJSON" exports of LPC/NTA layers carry EPSG:2263 coordinates without a ``crs`` member; the CRS is detected
from coordinate magnitude and every geometry is reprojected to NYC_TM.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import pyogrio
import shapely

from ..crs import US_SURVEY_FOOT_M, transformer

log = logging.getLogger("nycsim.buildings.attributes")


# ---- Building Elevation & Subgrade --------------------------------------------------------------------------------
def load_bsin(path: Path) -> pl.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"building elevation csv missing or empty: {path}")
    df = (pl.scan_csv(path, infer_schema_length=0)
          .select(["bin", "z_grade", "z_floor", "subgrade", "address", "NTA2020"]).collect())
    df = df.with_columns([
        pl.col("bin").cast(pl.Int64, strict=False),
        pl.col("z_grade").cast(pl.Float64, strict=False),
        pl.col("z_floor").cast(pl.Float64, strict=False),
    ]).filter(pl.col("bin").is_not_null() & (pl.col("bin") % 1_000_000 != 0))
    out = df.select([
        pl.col("bin"),
        (pl.col("z_grade") * US_SURVEY_FOOT_M).cast(pl.Float32).alias("bsin_z_grade"),
        ((pl.col("z_floor") - pl.col("z_grade")) * US_SURVEY_FOOT_M).cast(pl.Float32).alias("first_floor_offset"),
        pl.when(pl.col("subgrade").str.to_uppercase().str.starts_with("Y")).then(1)
          .when(pl.col("subgrade").str.to_uppercase().str.starts_with("N")).then(0)
          .otherwise(-1).cast(pl.Int8).alias("has_subgrade"),
        pl.col("address").fill_null("").str.strip_chars().alias("bsin_address"),
        pl.col("NTA2020").fill_null("").str.strip_chars().alias("bsin_nta"),
    ]).unique(subset=["bin"], keep="first")
    # implausible first-floor offsets (below grade by > 3 m or above by > 12 m) are measurement errors -> unknown
    out = out.with_columns(
        pl.when((pl.col("first_floor_offset") < -3.0) | (pl.col("first_floor_offset") > 12.0)).then(None)
          .otherwise(pl.col("first_floor_offset")).alias("first_floor_offset"))
    log.info("bsin: %d unique BINs", out.height)
    return out


# ---- DOB sidewalk sheds -------------------------------------------------------------------------------------------
def load_active_sheds(path: Path, today: dt.date) -> tuple[pl.DataFrame, dict]:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"sidewalk shed csv missing or empty: {path}")
    df = pl.read_csv(path, infer_schema_length=0)
    iso = today.isoformat()
    df = df.with_columns([
        pl.col("bin").cast(pl.Int64, strict=False),
        pl.col("issued_date").str.slice(0, 10).alias("_issued"),
        pl.col("expired_date").str.slice(0, 10).alias("_expired"),
    ])
    active = df.filter(
        (pl.col("permit_status") == "Permit Issued") & (pl.col("_expired") >= iso) & (pl.col("_issued") <= iso)
        & pl.col("bin").is_not_null() & (pl.col("bin") % 1_000_000 != 0))
    out = active.group_by("bin").agg([pl.len().cast(pl.Int16).alias("n_active_sheds"), pl.col("_expired").max().alias("shed_expires")])
    stats = {"permits_total": df.height, "permits_issued_status": int((df["permit_status"] == "Permit Issued").sum()),
             "permits_active": active.height, "bins_with_active_shed": out.height, "as_of": iso}
    log.info("sheds: %d active permits on %d BINs (as of %s)", active.height, out.height, iso)
    return out, stats


# ---- GeoJSON layers -----------------------------------------------------------------------------------------------
@dataclass
class Layer:
    geoms: np.ndarray            # shapely geometries in NYC_TM
    fields: dict[str, np.ndarray]
    source_crs: str

    def __len__(self) -> int:
        return len(self.geoms)


def _to_nyc_tm(geoms: np.ndarray) -> tuple[np.ndarray, str]:
    """Detect EPSG:2263 (ft) vs EPSG:4326 by coordinate magnitude and reproject to NYC_TM."""
    if len(geoms) == 0:
        return geoms, "empty"
    b = shapely.total_bounds(geoms)
    if abs(b[0]) > 1000 or abs(b[2]) > 1000:
        src = "EPSG:2263"
        tr = transformer(2263, "NYC_TM")
    else:
        src = "EPSG:4326"
        tr = transformer("WGS84", "NYC_TM")

    def f(c: np.ndarray) -> np.ndarray:
        x, y = tr.transform(c[:, 0], c[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geoms, f), src


def load_geojson_layer(path: Path, fields: list[str]) -> Layer:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"GeoJSON layer missing or empty: {path}")
    gdf = pyogrio.read_dataframe(path, columns=fields)
    geoms = np.asarray(gdf.geometry.values, dtype=object)
    geoms = shapely.make_valid(geoms)
    geoms, src = _to_nyc_tm(geoms)
    out_fields = {f: gdf[f].to_numpy() if f in gdf.columns else np.full(len(gdf), None, dtype=object) for f in fields}
    log.info("layer %s: %d features (%s -> NYC_TM)", path.name, len(geoms), src)
    return Layer(geoms, out_fields, src)


def load_lpc_sites(path: Path) -> Layer:
    lyr = load_geojson_layer(path, ["lpc_lpnumb", "lpc_name", "bbl", "lpc_sitest", "landmarkty"])
    status = np.asarray([str(s or "") for s in lyr.fields["lpc_sitest"]])
    keep = np.isin(status, ["Designated", "Amended", "Moved"])
    lyr = Layer(lyr.geoms[keep], {k: v[keep] for k, v in lyr.fields.items()}, lyr.source_crs)
    log.info("lpc sites: %d designated/amended/moved sites", len(lyr))
    return lyr


def load_lpc_districts(path: Path) -> Layer:
    lyr = load_geojson_layer(path, ["lp_number", "area_name", "status_of_", "current_"])
    status = np.asarray([str(s or "").upper() for s in lyr.fields["status_of_"]])
    keep = status == "DESIGNATED"
    lyr = Layer(lyr.geoms[keep], {k: v[keep] for k, v in lyr.fields.items()}, lyr.source_crs)
    log.info("lpc districts: %d designated districts", len(lyr))
    return lyr


def load_nta(path: Path) -> Layer | None:
    if not path.exists() or path.stat().st_size == 0:
        log.warning("NTA 2020 layer not available at %s — NTA for BINs outside bsin left empty", path)
        return None
    lyr = load_geojson_layer(path, ["nta2020", "ntaname"])
    return lyr


def load_lpc_building_db(path: Path) -> pl.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"LPC building db missing or empty: {path}")
    df = pl.scan_csv(path, infer_schema_length=0).select(["BIN", "STYLE1", "MATERIAL1", "LM_NAME", "PROP_NAME", "HIST_DISTRICT"]).collect()

    def clean(c: str) -> pl.Expr:
        v = pl.col(c).fill_null("").str.strip_chars()
        return pl.when(v.is_in(["0", "Not determined", "None", "N/A", "n/a"])).then(pl.lit("")).otherwise(v)

    out = df.with_columns([
        pl.col("BIN").cast(pl.Int64, strict=False).alias("bin"),
        clean("STYLE1").alias("lpc_style"),
        clean("MATERIAL1").alias("lpc_material"),
        clean("LM_NAME").alias("lpc_lm_name"),
        clean("PROP_NAME").alias("lpc_prop_name"),
        clean("HIST_DISTRICT").alias("lpc_bdb_district"),
    ]).drop(["BIN", "STYLE1", "MATERIAL1", "LM_NAME", "PROP_NAME", "HIST_DISTRICT"])
    out = out.filter(pl.col("bin").is_not_null() & (pl.col("bin") % 1_000_000 != 0))
    # one row per BIN: prefer rows with a style / material
    out = (out.with_columns(((pl.col("lpc_style") != "").cast(pl.Int8) + (pl.col("lpc_material") != "").cast(pl.Int8)).alias("_score"))
              .sort("_score", descending=True).unique(subset=["bin"], keep="first").drop("_score"))
    log.info("lpc building db: %d unique BINs", out.height)
    return out


# ---- spatial helpers ----------------------------------------------------------------------------------------------
def point_in_layer(xs: np.ndarray, ys: np.ndarray, layer: Layer, prefer_smallest: bool = True) -> np.ndarray:
    """Index of the layer polygon containing each point (-1 if none). Ties resolved by the smallest polygon."""
    idx = np.full(len(xs), -1, dtype=np.int64)
    if len(layer) == 0 or len(xs) == 0:
        return idx
    tree = shapely.STRtree(layer.geoms)
    pts = shapely.points(xs, ys)
    q, t = tree.query(pts, predicate="within")
    if len(q) == 0:
        return idx
    if prefer_smallest:
        area = shapely.area(layer.geoms)[t]
        order = np.lexsort((area, q))
        q, t = q[order], t[order]
    # first occurrence per point wins
    first = np.ones(len(q), dtype=bool)
    first[1:] = q[1:] != q[:-1]
    idx[q[first]] = t[first]
    return idx


def _str_field(layer: Layer, name: str, idx: np.ndarray, default: str = "") -> np.ndarray:
    vals = np.asarray(["" if v is None else str(v) for v in layer.fields[name]], dtype=object)
    out = np.full(len(idx), default, dtype=object)
    ok = idx >= 0
    out[ok] = vals[idx[ok]]
    return out


def lpc_site_attributes(attrs: pl.DataFrame, sites: Layer) -> tuple[pl.DataFrame, dict]:
    """landmark_id (LP number) + LPC site name per footprint: BBL match first, then centroid-in-site-polygon."""
    lp = np.asarray(["" if v is None else str(v) for v in sites.fields["lpc_lpnumb"]], dtype=object)
    nm = np.asarray(["" if v is None else str(v) for v in sites.fields["lpc_name"]], dtype=object)
    site_bbl = np.asarray([int(v) if v not in (None, "") and str(v).isdigit() else 0 for v in sites.fields["bbl"]], dtype=np.int64)
    bbl_to_site: dict[int, int] = {}
    for i, b in enumerate(site_bbl):
        if b > 0 and b not in bbl_to_site:
            bbl_to_site[b] = i
    bbl = attrs["bbl"].to_numpy()
    by_bbl = np.array([bbl_to_site.get(int(b), -1) for b in bbl], dtype=np.int64)
    by_pt = point_in_layer(attrs["centroid_x"].to_numpy(), attrs["centroid_y"].to_numpy(), sites)
    idx = np.where(by_bbl >= 0, by_bbl, by_pt)
    method = np.where(by_bbl >= 0, 1, np.where(by_pt >= 0, 2, 0)).astype(np.int8)
    out = attrs.with_columns([
        pl.Series("landmark_id", _str_field(sites, "lpc_lpnumb", idx)),
        pl.Series("lpc_site_name", _str_field(sites, "lpc_name", idx)),
        pl.Series("_lm_method", method),
    ])
    stats = {"sites": len(sites), "footprints_by_bbl": int((by_bbl >= 0).sum()), "footprints_by_centroid_only": int(((by_bbl < 0) & (by_pt >= 0)).sum()),
             "footprints_with_landmark_id": int((idx >= 0).sum()), "distinct_lp_numbers": int(len(set(lp[idx[idx >= 0]])))}
    log.info("lpc sites: %d footprints carry an LP number (%d distinct)", stats["footprints_with_landmark_id"], stats["distinct_lp_numbers"])
    _ = nm
    return out.drop("_lm_method"), stats


def hist_district_attributes(attrs: pl.DataFrame, districts: Layer) -> tuple[pl.DataFrame, dict]:
    idx = point_in_layer(attrs["centroid_x"].to_numpy(), attrs["centroid_y"].to_numpy(), districts)
    out = attrs.with_columns([
        pl.Series("hist_district", _str_field(districts, "area_name", idx)),
        pl.Series("hist_district_id", _str_field(districts, "lp_number", idx)),
    ])
    stats = {"districts": len(districts), "footprints_in_district": int((idx >= 0).sum())}
    log.info("historic districts: %d footprints inside a designated district", stats["footprints_in_district"])
    return out, stats


def nta_attributes(attrs: pl.DataFrame, nta: Layer | None) -> tuple[pl.DataFrame, dict]:
    """NTA2020 code: bsin per-BIN value first, else centroid-in-NTA-polygon."""
    have = attrs["bsin_nta"].fill_null("").to_numpy().astype(object)
    stats = {"from_bsin": int((have != "").sum())}
    if nta is not None:
        need = have == ""
        idx = np.full(len(have), -1, dtype=np.int64)
        if need.any():
            idx_need = point_in_layer(attrs["centroid_x"].to_numpy()[need], attrs["centroid_y"].to_numpy()[need], nta)
            idx[need] = idx_need
        filled = _str_field(nta, "nta2020", idx)
        have = np.where(have == "", filled, have)
        stats["from_polygon"] = int((idx >= 0).sum())
    else:
        stats["from_polygon"] = 0
    stats["empty"] = int((have == "").sum())
    return attrs.with_columns(pl.Series("nta", have.astype(str))), stats
