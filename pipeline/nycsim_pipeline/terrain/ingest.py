"""Warp every DEM source onto the global 2 m NYC_TM lattice.

Output: ``data/processed/terrain/src2m/*.tif`` (Float32, deflate, nodata -9999) + ``index.json``.
Each intermediate is lattice-aligned (grid.py), so tile composition later is a pure pixel copy with no
second resampling. Sources finer than 2 m (1 m LiDAR) are box-averaged (anti-aliased), coarser ones
(1/9", 1/3") are bilinearly interpolated, as ARCHITECTURE §5 prescribes for the base DEM.

* 1 m tiles (priority 0) become one intermediate each (~5.1k x 5.1k samples).
* 1/9" and 1/3" sources (priority 1, 2) are warped in 8 km lattice-aligned chunks; a chunk that is already
  fully covered by higher-priority data is not written at all (they are fallback layers).

Vertical: all 3DEP sources are metres above NAVD88 (product metadata verified, see REPORT.md); no vertical
transform is applied. Horizontal: NAD83 -> NYC_TM(WGS84) goes through PROJ's null NAD83->WGS84 step, the
same path Socrata's "EPSG:4326" (NAD83-derived) data takes in ``crs.py``; the layers therefore coincide.

Raw 1 m tiles (up to 525 MB each, 3.43 GB in total) are deleted after their intermediate is verified so the
retained raw footprint stays under the 3 GB budget; the download manifest keeps url/sha256/bytes and is
annotated ``purged_after_ingest``.

    python -m nycsim_pipeline.terrain.ingest [--kinds 1m,19,13] [--only ID] [--overwrite] [--keep-raw]
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

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window

from .. import manifest
from ..crs import NYC_TM, SCOPE_XMAX, SCOPE_XMIN, SCOPE_YMAX, SCOPE_YMIN
from ..paths import PROCESSED, REPO_ROOT
from .compose import DemStack
from .grid import MARGIN, NODATA, SPACING_M, bounds_of, lattice_grid
from .sources_3dep import DemSource, discover, fetch, local_path

log = logging.getLogger("nycsim.terrain.ingest")

SRC2M = PROCESSED / "terrain" / "src2m"
INDEX_PATH = SRC2M / "index.json"
SCHEMA = "terrain.src2m/1"
Z_VALID = (-100.0, 1000.0)  # anything outside is a void/garbage value in this region
SCOPE_PAD_M = (MARGIN + 2) * SPACING_M  # keep data slightly beyond the scope for edge-tile padding
CHUNK_M = 8000.0


class IngestError(RuntimeError):
    pass


def load_index() -> dict:
    if INDEX_PATH.exists():
        with open(INDEX_PATH) as f:
            return json.load(f)
    return {"schema_version": 1, "schema": SCHEMA, "entries": {}}


def _save_index(doc: dict) -> None:
    SRC2M.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    os.replace(tmp, INDEX_PATH)


def entries_for(source_id: str) -> dict[str, dict]:
    return {k: e for k, e in load_index()["entries"].items() if e["source_id"] == source_id}


def _source_res_m(ds: rasterio.DatasetReader) -> float:
    rx, ry = ds.res
    if ds.crs.is_geographic:
        lat = 0.5 * (ds.bounds.bottom + ds.bounds.top)
        return float(min(rx * 111320.0 * math.cos(math.radians(lat)), ry * 110574.0))
    return float(min(rx, ry))


def _valid_window(ds: rasterio.DatasetReader) -> Window | None:
    """Exact pixel window enclosing all valid data (strip scan, ~64 MB per strip)."""
    rows_any = np.zeros(ds.height, dtype=bool)
    cols_any = np.zeros(ds.width, dtype=bool)
    nodata = ds.nodata if ds.nodata is not None and np.isfinite(ds.nodata) else None
    step = max(1, (1 << 26) // max(1, ds.width * 4))
    for r0 in range(0, ds.height, step):
        n = min(step, ds.height - r0)
        a = ds.read(1, window=Window(0, r0, ds.width, n))
        valid = np.isfinite(a) & (a > Z_VALID[0]) & (a < Z_VALID[1])
        if nodata is not None:
            valid &= a != nodata
        rows_any[r0:r0 + n] = valid.any(axis=1)
        cols_any |= valid.any(axis=0)
    if not rows_any.any():
        return None
    rows, cols = np.flatnonzero(rows_any), np.flatnonzero(cols_any)
    r0, r1 = max(0, rows[0] - 1), min(ds.height, rows[-1] + 2)
    c0, c1 = max(0, cols[0] - 1), min(ds.width, cols[-1] + 2)
    return Window(c0, r0, c1 - c0, r1 - r0)


def _target_bbox(ds: rasterio.DatasetReader, win: Window) -> tuple[float, float, float, float] | None:
    tb = transform_bounds(ds.crs, NYC_TM, *rasterio.windows.bounds(win, ds.transform), densify_pts=21)
    xmin, ymin = max(tb[0], SCOPE_XMIN - SCOPE_PAD_M), max(tb[1], SCOPE_YMIN - SCOPE_PAD_M)
    xmax, ymax = min(tb[2], SCOPE_XMAX + SCOPE_PAD_M), min(tb[3], SCOPE_YMAX + SCOPE_PAD_M)
    if xmax - xmin < 2 * SPACING_M or ymax - ymin < 2 * SPACING_M:
        return None
    return (xmin, ymin, xmax, ymax)


def _chunks(bbox: tuple[float, float, float, float]):
    """Lattice-aligned 8 km chunk bboxes (inclusive edges) covering ``bbox``."""
    cx0, cx1 = math.floor(bbox[0] / CHUNK_M), math.floor((bbox[2] - 1e-6) / CHUNK_M)
    cy0, cy1 = math.floor(bbox[1] / CHUNK_M), math.floor((bbox[3] - 1e-6) / CHUNK_M)
    for cy in range(cy0, cy1 + 1):
        for cx in range(cx0, cx1 + 1):
            yield (cx, cy), (max(bbox[0], cx * CHUNK_M), max(bbox[1], cy * CHUNK_M),
                             min(bbox[2], (cx + 1) * CHUNK_M), min(bbox[3], (cy + 1) * CHUNK_M))


def _warp(ds: rasterio.DatasetReader, transform: Affine, width: int, height: int, resampling: Resampling) -> np.ndarray:
    dst = np.full((height, width), NODATA, dtype=np.float32)
    src_nodata = ds.nodata if ds.nodata is not None else -3.4028235e38
    reproject(source=rasterio.band(ds, 1), destination=dst, src_nodata=src_nodata,
              dst_transform=transform, dst_crs=NYC_TM, dst_nodata=NODATA, resampling=resampling,
              num_threads=2, warp_mem_limit=768, init_dest_nodata=True)
    garbage = np.isfinite(dst) & (dst != NODATA) & ((dst <= Z_VALID[0]) | (dst >= Z_VALID[1]))
    dst[garbage | ~np.isfinite(dst)] = NODATA
    return dst


def _write(out: Path, dst: np.ndarray, transform: Affine, dem: DemSource, resampling: Resampling) -> None:
    height, width = dst.shape
    tmp = out.with_suffix(".tmp.tif")
    profile = dict(driver="GTiff", dtype="float32", count=1, width=width, height=height, crs=NYC_TM,
                   transform=transform, nodata=NODATA, tiled=True, blockxsize=512, blockysize=512,
                   compress="deflate", predictor=3, zlevel=6, BIGTIFF="IF_SAFER")
    with rasterio.open(tmp, "w", **profile) as w:
        w.write(dst, 1)
        w.update_tags(**{"nycsim.schema": SCHEMA, "source_id": dem.id, "source_url": dem.source.url,
                         "resampling": resampling.name, "vertical_datum": "NAVD88 metres", "AREA_OR_POINT": "Point"})
    os.replace(tmp, out)
    with rasterio.open(out) as chk:
        if (chk.width, chk.height) != (width, height) or chk.transform != transform:
            raise IngestError(f"{out}: read-back mismatch")
        n_back = int((chk.read(1) != NODATA).sum())
    n_valid = int((dst != NODATA).sum())
    if n_back != n_valid:
        raise IngestError(f"{out}: valid-pixel count changed on write ({n_valid} -> {n_back})")


def _entry(key: str, out: Path, dst: np.ndarray, transform: Affine, dem: DemSource, resampling: Resampling,
           res_m: float, src_crs: str, seconds: float) -> dict:
    height, width = dst.shape
    valid = dst != NODATA
    dl_entry = manifest.get_download(dem.id) or {}
    return {
        "path": str(out.relative_to(REPO_ROOT)), "priority": dem.priority, "kind": dem.kind, "title": dem.title,
        "transform": list(transform)[:6], "width": width, "height": height, "bounds": list(bounds_of(transform, width, height)),
        "valid_px": int(valid.sum()), "valid_fraction": float(valid.mean()),
        "z_min": float(dst[valid].min()), "z_max": float(dst[valid].max()), "resampling": resampling.name,
        "src_res_m": res_m, "src_crs": src_crs, "source_id": dem.id, "source_url": dem.source.url,
        "source_sha256": dl_entry.get("sha256", ""), "source_bytes": dl_entry.get("bytes", 0),
        "seconds": round(seconds, 1), "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def ingest(dem: DemSource, raw_path: Path, overwrite: bool = False) -> dict:
    """Warp one source to lattice-aligned intermediate(s). Returns a per-source summary."""
    existing = entries_for(dem.id)
    if existing and not overwrite and all((REPO_ROOT / e["path"]).exists() for e in existing.values()):
        log.info("present %s (%d file(s))", dem.id, len(existing))
        return _summarize(dem, existing, 0)
    if overwrite or existing:
        doc = load_index()
        for k, e in existing.items():
            (REPO_ROOT / e["path"]).unlink(missing_ok=True)
            doc["entries"].pop(k, None)
        _save_index(doc)
    t0 = time.time()
    written: dict[str, dict] = {}
    skipped_covered = 0
    with rasterio.Env(GDAL_CACHEMAX=512), rasterio.open(dem.raster_uri(raw_path)) as ds:
        if ds.count != 1:
            raise IngestError(f"{dem.id}: expected 1 band, got {ds.count}")
        win = _valid_window(ds)
        if win is None:
            raise IngestError(f"{dem.id}: no valid data")
        bbox = _target_bbox(ds, win)
        if bbox is None:
            raise IngestError(f"{dem.id}: valid data does not reach the scope")
        res_m = _source_res_m(ds)
        resampling = Resampling.average if res_m <= 0.75 * SPACING_M else Resampling.bilinear
        src_crs = ds.crs.to_string()
        SRC2M.mkdir(parents=True, exist_ok=True)
        pieces = [((0, 0), bbox)] if dem.priority == 0 else list(_chunks(bbox))
        stack = DemStack(INDEX_PATH) if dem.priority > 0 and INDEX_PATH.exists() else None
        try:
            for (cx, cy), piece in pieces:
                transform, width, height = lattice_grid(*piece)
                key = dem.id if dem.priority == 0 else f"{dem.id}__{cx}_{cy}"
                if stack is not None and stack.coverage(transform, width, height, max_priority=dem.priority - 1) >= 1.0:
                    skipped_covered += 1
                    continue
                t1 = time.time()
                dst = _warp(ds, transform, width, height, resampling)
                if not (dst != NODATA).any():
                    continue
                out = SRC2M / f"{key}.tif"
                _write(out, dst, transform, dem, resampling)
                written[key] = _entry(key, out, dst, transform, dem, resampling, res_m, src_crs, time.time() - t1)
                log.info("  %s: %dx%d, %.1f%% valid, z %.2f..%.2f, %.1fs", key, width, height, 100 * written[key]["valid_fraction"],
                         written[key]["z_min"], written[key]["z_max"], written[key]["seconds"])
                del dst
        finally:
            if stack is not None:
                stack.close()
    if not written:
        raise IngestError(f"{dem.id}: nothing to write (no valid data inside scope or fully covered)")
    doc = load_index()
    doc["entries"].update(written)
    _save_index(doc)
    for key, e in written.items():
        manifest.record_processed(f"terrain_src2m_{key}", REPO_ROOT / e["path"], stage="terrain", sources=[dem.id], schema=SCHEMA,
                                  extra={"valid_px": e["valid_px"], "z_min": e["z_min"], "z_max": e["z_max"], "resampling": e["resampling"]})
    s = _summarize(dem, written, skipped_covered)
    s["seconds"] = round(time.time() - t0, 1)
    log.info("ingested %s: %d file(s), %d chunk(s) skipped as covered, %d valid px, z %.2f..%.2f, %.1fs",
             dem.id, len(written), skipped_covered, s["valid_px"], s["z_min"], s["z_max"], s["seconds"])
    return s


def _summarize(dem: DemSource, entries: dict[str, dict], skipped: int) -> dict:
    vals = list(entries.values())
    return {"id": dem.id, "kind": dem.kind, "priority": dem.priority, "title": dem.title, "files": len(vals),
            "chunks_skipped_covered": skipped, "valid_px": int(sum(e["valid_px"] for e in vals)),
            "z_min": float(min(e["z_min"] for e in vals)), "z_max": float(max(e["z_max"] for e in vals)),
            "seconds": float(sum(e["seconds"] for e in vals)), "source_bytes": int(vals[0]["source_bytes"]) if vals else 0,
            "resampling": vals[0]["resampling"] if vals else ""}


def purge_raw(dem: DemSource, raw_path: Path) -> None:
    """Delete a raw DEM whose intermediate exists and annotate the download manifest (url/sha256 are kept)."""
    if not raw_path.exists():
        return
    doc = manifest._load(manifest.DOWNLOADS)  # noqa: SLF001 — annotate an existing entry in place
    if doc["entries"].get(dem.id) is None:
        manifest.record_download(dem.id, raw_path, dem.source.url, license=dem.source.license,
                                 attribution=dem.source.attribution, notes=dem.source.description)
        doc = manifest._load(manifest.DOWNLOADS)  # noqa: SLF001
    raw_path.unlink()
    doc["entries"][dem.id].update({"purged_after_ingest": True, "purged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                   "derived_artifact": f"terrain_src2m_{dem.id}"})
    manifest._save(manifest.DOWNLOADS, doc)  # noqa: SLF001
    log.info("purged raw %s (%s)", dem.id, raw_path.name)


def ingest_all(kinds: tuple[str, ...], only: str | None = None, overwrite: bool = False, keep_raw: bool = False) -> dict:
    dems = discover(kinds)
    if only:
        dems = [d for d in dems if d.id == only]
        if not dems:
            raise IngestError(f"unknown DEM source {only}")
    summary = {"sources": [], "retained_raw_bytes": 0, "peak_raw_bytes": 0, "downloaded_bytes": 0, "seconds": 0.0, "failures": []}
    t0 = time.time()
    retained = 0
    for dem in dems:
        try:
            raw = local_path(dem)
            have = entries_for(dem.id)
            if have and not overwrite and all((REPO_ROOT / e["path"]).exists() for e in have.values()):
                s = _summarize(dem, have, 0)
            else:
                raw = fetch(dem)
                size = raw.stat().st_size
                summary["downloaded_bytes"] += size
                summary["peak_raw_bytes"] = max(summary["peak_raw_bytes"], retained + size)
                s = ingest(dem, raw, overwrite=overwrite)
            if dem.purge_after_ingest and not keep_raw and raw.exists():
                purge_raw(dem, raw)
            if raw.exists():
                retained += raw.stat().st_size
            s["raw_retained"] = raw.exists()
            summary["sources"].append(s)
        except IngestError as e:
            if "does not reach the scope" in str(e):
                # product cell intersects the scope bbox but its valid data lies outside (e.g. CT / Westchester slivers)
                log.info("skipped %s: valid data outside scope", dem.id)
                summary.setdefault("skipped_outside_scope", []).append(dem.id)
            else:
                log.error("FAILED %s: %s", dem.id, e)
                summary["failures"].append({"id": dem.id, "error": str(e)})
        except Exception as e:  # noqa: BLE001 — continue with the other sources, report all failures
            log.error("FAILED %s: %s", dem.id, e)
            summary["failures"].append({"id": dem.id, "error": str(e)})
    summary["retained_raw_bytes"] = retained
    summary["seconds"] = round(time.time() - t0, 1)
    SRC2M.mkdir(parents=True, exist_ok=True)
    with open(SRC2M / "ingest_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kinds", default="1m,19,13")
    ap.add_argument("--only")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--keep-raw", action="store_true", help="do not delete raw 1 m tiles after ingest")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    s = ingest_all(tuple(k for k in a.kinds.split(",") if k), a.only, a.overwrite, a.keep_raw)
    print(json.dumps({k: v for k, v in s.items() if k != "sources"}, indent=1))
    print(f"{len(s['sources'])} sources ingested, {len(s['failures'])} failed")
    return 1 if s["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
