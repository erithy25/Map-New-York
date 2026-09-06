"""New Jersey building footprints with heights for the Hudson-facing skyline (ARCHITECTURE §5, NJ side).

Primary source: FEMA / Oak Ridge National Laboratory **USA Structures** (public domain, ArcGIS REST, polygon
footprints with LiDAR-derived ``HEIGHT`` in metres, occupancy class, address). It is queried by bounding box in
2000-record pages (``resultOffset`` paging, ``f=geojson``) restricted to ``PROP_ST = 'New Jersey'``.

Why not NJGIN/NJDEP: the NJDEP statewide layer ``Features/Structures/MapServer/8`` (2.89 M polygons) answers
attribute queries but returns ``count = 0`` for every spatial filter we tried (envelope / polygon, SR 4326, 3857,
3424, with and without ``inSR``), and it carries no height attribute; NJOGIS' own hosted services list has no
building layer. Both facts are recorded in ``docs/verification/furniture/REPORT.md``.

Outputs
* ``data/raw/nj/usa_structures_nj_hudson.ndjson.gz`` — raw pages as fetched (manifest: ``record_download``)
* ``data/processed/nj/buildings_nj_usa_structures.parquet`` — GeoParquet, NYC_TM, one row per footprint

Run: ``python -m nycsim_pipeline.osm.nj_buildings [--bbox LON0 LAT0 LON1 LAT1] [--page 2000]``
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import requests
import shapely

from ..crs import lonlat_to_tm
from ..download import CA_BUNDLE
from ..manifest import record_download, record_processed
from ..paths import PROCESSED, RAW
from .geoparquet import ParquetBatchWriter

log = logging.getLogger("nycsim.nj_buildings")

SERVICE = "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/USA_Structures_View/FeatureServer/0/query"
SOURCE_ID = "usa_structures_nj_hudson"
LICENSE = "Public domain (US Government work: FEMA / ORNL USA Structures)"
ATTRIBUTION = "FEMA, Oak Ridge National Laboratory, USA Structures (via ArcGIS Online)"
FIELDS = ["BUILD_ID", "OCC_CLS", "PRIM_OCC", "SEC_OCC", "HEIGHT", "SQMETERS", "H_ADJ_ELEV", "L_ADJ_ELEV", "PROP_ADDR", "PROP_CITY",
          "PROP_CNTY", "PROP_ST", "SOURCE", "VAL_METHOD", "IMAGE_DATE", "FIPS"]
# Hudson County + the Bergen Palisades waterfront (Edgewater .. Alpine) + downtown Newark / Newark Bay shore.
DEFAULT_BBOX = (-74.19, 40.63, -73.95, 40.90)

RAW_DIR = RAW / "nj"
OUT_DIR = PROCESSED / "nj"

SCHEMA = pa.schema([("build_id", pa.int64()), ("geometry", pa.binary()), ("height_m", pa.float32()), ("height_source", pa.string()),
                    ("occ_class", pa.string()), ("prim_occ", pa.string()), ("sec_occ", pa.string()), ("area_m2", pa.float32()),
                    ("ground_elev_m", pa.float32()), ("roof_elev_m", pa.float32()), ("address", pa.string()), ("city", pa.string()),
                    ("county", pa.string()), ("state", pa.string()), ("source", pa.string()), ("val_method", pa.string()),
                    ("image_date", pa.string()), ("fips", pa.string()), ("cx", pa.float64()), ("cy", pa.float64()), ("borough", pa.int8())])


class FetchError(RuntimeError):
    pass


def _get(params: dict, attempts: int = 5, timeout: int = 180) -> dict:
    last: Exception | None = None
    for i in range(attempts):
        try:
            r = requests.get(SERVICE, params=params, timeout=timeout, verify=CA_BUNDLE, headers={"User-Agent": "NYCSim-pipeline/1.0"})
            if r.status_code != 200:
                raise FetchError(f"HTTP {r.status_code}: {r.text[:200]}")
            d = r.json()
            if "error" in d:
                raise FetchError(f"ArcGIS error: {d['error']}")
            return d
        except (requests.RequestException, ValueError, FetchError) as e:
            last = e
            log.warning("attempt %d/%d failed: %s", i + 1, attempts, e)
            time.sleep(min(60, 2 ** (i + 1)))
    raise FetchError(f"giving up: {last}")


def count(bbox: tuple[float, float, float, float], where: str = "PROP_ST = 'New Jersey'") -> int:
    d = _get({"where": where, "geometry": ",".join(f"{v}" for v in bbox), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
              "spatialRel": "esriSpatialRelIntersects", "returnCountOnly": "true", "f": "json"})
    return int(d["count"])


def fetch_pages(bbox: tuple[float, float, float, float], raw_path: Path, page: int = 2000, where: str = "PROP_ST = 'New Jersey'") -> int:
    """Page through the service and append every feature as one JSON line to ``raw_path`` (gzip). Returns feature count."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    total = count(bbox, where)
    log.info("USA Structures: %d features in bbox %s", total, bbox)
    n = 0
    offset = 0
    tmp = raw_path.with_suffix(raw_path.suffix + ".part")
    with gzip.open(tmp, "wt", encoding="utf-8") as out:
        while True:
            d = _get({"where": where, "geometry": ",".join(f"{v}" for v in bbox), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                      "spatialRel": "esriSpatialRelIntersects", "outFields": ",".join(FIELDS), "outSR": 4326,
                      "orderByFields": "OBJECTID", "resultOffset": offset, "resultRecordCount": page, "f": "geojson"})
            feats = d.get("features", [])
            for f in feats:
                out.write(json.dumps(f, separators=(",", ":")) + "\n")
            n += len(feats)
            offset += len(feats)
            exceeded = bool(d.get("properties", {}).get("exceededTransferLimit", False)) or len(feats) == page
            if n % (page * 10) == 0 or not exceeded:
                log.info("fetched %d / %d", n, total)
            if not feats or not exceeded:
                break
    tmp.replace(raw_path)
    if n < total * 0.98:
        raise FetchError(f"incomplete fetch: {n} of {total}")
    return n


def _borough_from_lonlat(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    return np.full(len(lon), 6, dtype=np.int8)  # 6 = NJ (DATA_CONTRACTS §2)


def build_parquet(raw_path: Path, out_path: Path) -> dict:
    """Raw NDJSON pages -> GeoParquet in NYC_TM. Feet are never involved: the service reports HEIGHT in metres."""
    w = ParquetBatchWriter(out_path, SCHEMA, schema_name="nycsim.nj.buildings_usa_structures.v1",
                           extra_metadata={"nycsim.license": LICENSE, "nycsim.source": SOURCE_ID})
    cols: dict[str, list] = {k: [] for k in SCHEMA.names}
    stats = {"rows": 0, "with_height": 0, "invalid_geometry": 0, "dedup_dropped": 0}
    seen: set[int] = set()

    def flush() -> None:
        if not cols["build_id"]:
            return
        geoms = shapely.from_geojson([json.dumps(g) for g in cols["geometry"]], on_invalid="ignore")
        ok = ~shapely.is_missing(geoms)
        geoms = np.where(ok, geoms, shapely.from_wkt("POLYGON EMPTY"))
        geoms = shapely.make_valid(geoms)
        g_tm = shapely.transform(geoms, lambda c: np.column_stack(lonlat_to_tm(c[:, 0], c[:, 1])))
        c = shapely.centroid(g_tm)
        keep = ok & ~shapely.is_empty(g_tm)
        stats["invalid_geometry"] += int((~keep).sum())
        idx = np.nonzero(keep)[0]
        out = {k: [cols[k][i] for i in idx] for k in SCHEMA.names if k not in ("geometry", "cx", "cy", "area_m2", "borough")}
        out["geometry"] = shapely.to_wkb(g_tm[keep])
        out["cx"] = shapely.get_x(c[keep])
        out["cy"] = shapely.get_y(c[keep])
        out["area_m2"] = shapely.area(g_tm[keep]).astype(np.float32)
        out["borough"] = _borough_from_lonlat(out["cx"], out["cy"])
        w.write(out)
        for k in cols:
            cols[k].clear()

    with gzip.open(raw_path, "rt", encoding="utf-8") as f:
        for line in f:
            feat = json.loads(line)
            p = feat.get("properties", {})
            bid = p.get("BUILD_ID")
            if bid is None or bid in seen:
                stats["dedup_dropped"] += 1
                continue
            seen.add(bid)
            h = p.get("HEIGHT")
            h = float(h) if h is not None and h > 0 else float("nan")
            stats["rows"] += 1
            if not np.isnan(h):
                stats["with_height"] += 1
            hi, lo = p.get("H_ADJ_ELEV"), p.get("L_ADJ_ELEV")
            cols["build_id"].append(int(bid))
            cols["geometry"].append(feat["geometry"])
            cols["height_m"].append(h)
            cols["height_source"].append("usa_structures_lidar" if not np.isnan(h) else "")
            cols["occ_class"].append(p.get("OCC_CLS") or "")
            cols["prim_occ"].append(p.get("PRIM_OCC") or "")
            cols["sec_occ"].append(p.get("SEC_OCC") or "")
            cols["ground_elev_m"].append(float(lo) if lo is not None else float("nan"))
            cols["roof_elev_m"].append(float(hi) if hi is not None else float("nan"))
            cols["address"].append(p.get("PROP_ADDR") or "")
            cols["city"].append(p.get("PROP_CITY") or "")
            cols["county"].append(p.get("PROP_CNTY") or "")
            cols["state"].append(p.get("PROP_ST") or "")
            cols["source"].append(p.get("SOURCE") or "")
            cols["val_method"].append(p.get("VAL_METHOD") or "")
            d = p.get("IMAGE_DATE")
            cols["image_date"].append(time.strftime("%Y-%m-%d", time.gmtime(d / 1000)) if isinstance(d, (int, float)) else (d or ""))
            cols["fips"].append(p.get("FIPS") or "")
            for k in ("cx", "cy", "area_m2", "borough"):
                cols[k].append(None)
            if len(cols["build_id"]) >= 20000:
                flush()
    flush()
    w.close()
    stats["bbox_tm"] = [float(v) for v in w.bbox]
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", type=float, nargs=4, default=list(DEFAULT_BBOX), metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--page", type=int, default=2000)
    ap.add_argument("--force", action="store_true", help="re-download even if the raw file exists")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bbox = tuple(a.bbox)
    raw_path = RAW_DIR / "usa_structures_nj_hudson.ndjson.gz"
    out_path = OUT_DIR / "buildings_nj_usa_structures.parquet"
    t0 = time.time()
    if a.force or not raw_path.exists():
        n = fetch_pages(bbox, raw_path, a.page)
        log.info("fetched %d features in %.0f s", n, time.time() - t0)
    url = f"{SERVICE}?where=PROP_ST%3D%27New%20Jersey%27&geometry={','.join(str(v) for v in bbox)}&geometryType=esriGeometryEnvelope&inSR=4326&outFields={','.join(FIELDS)}&outSR=4326&f=geojson (paged, resultRecordCount={a.page})"
    record_download(SOURCE_ID, raw_path, url, license=LICENSE, attribution=ATTRIBUTION,
                    notes="USA Structures footprints with LiDAR heights, NJ side of the Hudson (Hudson County, Bergen waterfront, Newark shore)",
                    extra={"bbox_lonlat": list(bbox)})
    stats = build_parquet(raw_path, out_path)
    stats["seconds"] = round(time.time() - t0, 1)
    record_processed("nj/buildings_nj_usa_structures", out_path, stage="osm", sources=[SOURCE_ID], rows=stats["rows"],
                     schema="nycsim.nj.buildings_usa_structures.v1", extra={"license": LICENSE, "stats": {k: v for k, v in stats.items() if k != "bbox_tm"}})
    with open(OUT_DIR / "buildings_nj_summary.json", "w") as f:
        json.dump({"schema_version": 1, "source": SOURCE_ID, "bbox_lonlat": list(bbox), **stats}, f, indent=1)
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
