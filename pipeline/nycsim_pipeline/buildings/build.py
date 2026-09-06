"""Buildings ingest stage: footprints + PLUTO + LPC + DCWP/DOHMH + DOB sheds -> buildings_base.parquet (+ per-tile files).

    python -m nycsim_pipeline buildings [--borough N ...] [--limit N] [--out-dir DIR] [--no-tiles] [--today YYYY-MM-DD]

Subset runs (``--borough``/``--limit``) must name an ``--out-dir`` and are never recorded in the manifest.
Outputs (full run): ``data/processed/buildings/{buildings_base.parquet, landmark_footprints.parquet,
borough_summary.json, build_summary.json, tiles_index.json}`` and ``data/processed/tiles/{tile}/buildings.parquet``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from .. import manifest
from ..paths import PROCESSED, RAW
from . import schema as S
from .attributes import (hist_district_attributes, load_active_sheds, load_bsin, load_lpc_building_db, load_lpc_districts,
                         load_lpc_sites, load_nta, lpc_site_attributes, nta_attributes)
from .facade_heading import facade_headings
from .footprints import load_footprints
from .infer import infer_heights_floors
from .landmarks import build_landmark_footprints
from .pluto import join_pluto, load_pluto
from .storefronts import (has_storefront_rule, load_dcwp, load_dohmh, match_businesses, storefront_lists)

log = logging.getLogger("nycsim.buildings.build")

OPEN = RAW / "nyc_opendata"
INPUTS = {
    "footprints": PROCESSED / "buildings" / "footprints_raw.parquet",
    "pluto": OPEN / "pluto.csv",
    "bsin": OPEN / "building_elevation_subgrade.csv",
    "sheds": OPEN / "dob_sidewalk_sheds.csv",
    "lpc_sites": OPEN / "lpc_individual_landmarks.geojson",
    "lpc_districts": OPEN / "lpc_historic_districts.geojson",
    "lpc_bdb": OPEN / "lpc_building_db.csv",
    "dcwp": OPEN / "dcwp_licenses.csv",
    "dohmh": OPEN / "dohmh_restaurants.csv",
    "nta": OPEN / "nta_2020.geojson",
}
SOURCE_IDS = ["building_footprints", "pluto", "building_elevation_subgrade", "dob_sidewalk_sheds", "lpc_individual_landmarks",
              "lpc_historic_districts", "lpc_building_db", "dcwp_licenses", "dohmh_restaurants", "nta_2020"]


class Timer:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.last = self.t0
        self.steps: dict[str, float] = {}

    def lap(self, name: str) -> None:
        now = time.perf_counter()
        self.steps[name] = round(now - self.last, 2)
        self.last = now
        log.info("[%6.1fs] %s done (%.1fs)", now - self.t0, name, self.steps[name])

    @property
    def total(self) -> float:
        return round(time.perf_counter() - self.t0, 2)


def _ensure_inputs(required: list[str]) -> None:
    missing = [k for k in required if not INPUTS[k].exists() or INPUTS[k].stat().st_size == 0]
    if missing:
        raise FileNotFoundError("missing inputs: " + ", ".join(f"{k}={INPUTS[k]}" for k in missing))


def _resolve_name(attrs: pl.DataFrame) -> pl.Series:
    def nz(c: str) -> pl.Expr:
        v = pl.col(c).fill_null("").str.strip_chars()
        return pl.when(v == "").then(None).otherwise(v)
    return attrs.select(pl.coalesce([nz("name"), nz("lpc_site_name"), nz("lpc_lm_name"), nz("lpc_prop_name"), pl.lit("")]).alias("name"))["name"]


def assemble_table(attrs: pl.DataFrame, geoms: np.ndarray, names: list[list[str]], kinds: list[list[int]],
                   sources: list[list[int]]) -> pa.Table:
    """Sort by (tile, bin, part) and build the Arrow table in contract column order."""
    order = attrs.with_row_index("_i").sort(["tile", "bin", "part_index"])["_i"].to_numpy()
    a = attrs[order]
    g = geoms[order]
    names = [names[i] for i in order]
    kinds = [kinds[i] for i in order]
    sources = [sources[i] for i in order]
    wkb = shapely.to_wkb(g)
    bbox = shapely.total_bounds(g)
    n = a.height
    cols: dict[str, pa.Array] = {}
    for name, typ, _ in S.COLUMNS:
        if name == S.GEOMETRY_COLUMN:
            cols[name] = pa.array(wkb, type=pa.binary())
        elif name == "storefront_names":
            cols[name] = pa.array(names, type=pa.list_(pa.string()))
        elif name == "storefront_kinds":
            cols[name] = pa.array(kinds, type=pa.list_(pa.int8()))
        elif name == "storefront_sources":
            cols[name] = pa.array(sources, type=pa.list_(pa.int8()))
        elif name == "osm_id":
            cols[name] = pa.array(np.zeros(n, dtype=np.int64), type=pa.int64())
        else:
            s = a[name]
            arr = s.to_arrow()
            if name in S.NAN_ALLOWED:
                cols[name] = arr.cast(typ)
            else:
                if arr.null_count:
                    raise ValueError(f"column {name} has {arr.null_count} nulls")
                cols[name] = arr.cast(typ)
    schema = S.arrow_schema(bbox, {"nycsim.stage": "buildings", "nycsim.rows": str(n)})
    return pa.Table.from_arrays([cols[f.name] for f in schema], schema=schema), g


def write_tiles(table: pa.Table, geoms: np.ndarray, tiles_root: Path) -> dict:
    tiles = table["tile"].to_numpy()
    uniq, starts = np.unique(tiles, return_index=True)
    order = np.argsort(starts)
    uniq, starts = uniq[order], starts[order]
    ends = np.append(starts[1:], len(tiles))
    files: dict[str, dict] = {}
    base_meta = dict(table.schema.metadata)
    for t, s, e in zip(uniq, starts, ends):
        sl = table.slice(int(s), int(e - s))
        bbox = shapely.total_bounds(geoms[s:e])
        meta = dict(base_meta)
        meta[b"geo"] = json.dumps(S.geo_metadata(bbox)).encode()
        meta[b"nycsim.rows"] = str(sl.num_rows).encode()
        meta[b"nycsim.tile"] = str(t).encode()
        sl = sl.replace_schema_metadata(meta)
        d = tiles_root / str(t)
        d.mkdir(parents=True, exist_ok=True)
        p = d / "buildings.parquet"
        pq.write_table(sl, p, compression="snappy")
        files[str(t)] = {"rows": int(sl.num_rows), "bytes": p.stat().st_size, "path": str(p.relative_to(PROCESSED.parent.parent)) if p.is_relative_to(PROCESSED.parent.parent) else str(p)}
    return files


def borough_summary(table: pa.Table, has_names: np.ndarray) -> dict:
    df = pl.from_arrow(table.select(["borough", "height", "pluto_joined", "fidelity", "has_scaffold", "has_storefront",
                                     "landmark_id", "hist_district", "floors", "year_built", "ground_z"]))
    df = df.with_columns(pl.Series("has_names", has_names))
    fid = pl.col("fidelity")
    names = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}

    def summarise(d: pl.DataFrame) -> dict:
        n = d.height
        pct = lambda x: round(100.0 * float(x) / max(n, 1), 3)  # noqa: E731
        return {
            "buildings": n,
            "height_median_m": round(float(d["height"].median()), 2) if n else None,
            "height_p90_m": round(float(d["height"].quantile(0.9)), 2) if n else None,
            "height_max_m": round(float(d["height"].max()), 2) if n else None,
            "floors_median": float(d["floors"].median()) if n else None,
            "ground_z_min_m": round(float(d["ground_z"].min()), 2) if n else None,
            "ground_z_max_m": round(float(d["ground_z"].max()), 2) if n else None,
            "pct_pluto_joined": pct(d["pluto_joined"].sum()),
            "pct_height_real": pct(d.filter((fid & S.Fidelity.HEIGHT_REAL.mask) > 0).height),
            "pct_floors_real": pct(d.filter((fid & S.Fidelity.FLOORS_REAL.mask) > 0).height),
            "pct_year_real": pct(d.filter((fid & S.Fidelity.YEAR_REAL.mask) > 0).height),
            "pct_ground_real": pct(d.filter((fid & S.Fidelity.GROUND_REAL.mask) > 0).height),
            "pct_with_storefront_names": pct(d["has_names"].sum()),
            "n_with_storefront_names": int(d["has_names"].sum()),
            "n_has_storefront": int(d["has_storefront"].sum()),
            "n_scaffold": int(d["has_scaffold"].sum()),
            "n_landmark_id": int((d["landmark_id"] != "").sum()),
            "n_in_historic_district": int((d["hist_district"] != "").sum()),
            "year_median": float(d.filter(pl.col("year_built") > 0)["year_built"].median()) if n else None,
        }

    out = {"schema_version": 1, "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "boroughs": {}}
    for code, nm in names.items():
        d = df.filter(pl.col("borough") == code)
        if d.height:
            out["boroughs"][nm] = {"code": code, **summarise(d)}
    out["all"] = summarise(df)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--borough", type=int, action="append", default=[], help="restrict to borough code(s) 1-5 (dev subset)")
    ap.add_argument("--limit", type=int, default=None, help="restrict to the first N footprints (dev subset)")
    ap.add_argument("--out-dir", type=Path, default=None, help="output directory (required for subset runs)")
    ap.add_argument("--no-tiles", action="store_true", help="skip per-tile files")
    ap.add_argument("--today", type=str, default=None, help="reference date for permit/inspection recency (default: today)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    subset = bool(a.borough) or a.limit is not None
    if subset and a.out_dir is None:
        ap.error("--out-dir is required for subset runs (--borough/--limit)")
    out_dir = a.out_dir or (PROCESSED / "buildings")
    tiles_root = (out_dir / "tiles") if subset else (PROCESSED / "tiles")
    out_dir.mkdir(parents=True, exist_ok=True)
    _ensure_inputs([k for k in INPUTS if k != "nta"])

    T = Timer()
    stats: dict = {"today": today.isoformat(), "subset": subset, "boroughs": a.borough or [1, 2, 3, 4, 5]}

    fp = load_footprints(INPUTS["footprints"], a.borough or None, a.limit)
    stats["footprints"] = fp.stats
    attrs, geoms = fp.attrs, fp.geoms
    T.lap("load_footprints")

    pluto = load_pluto(INPUTS["pluto"])
    attrs, stats["pluto"] = join_pluto(attrs, pluto)
    del pluto
    T.lap("pluto_join")

    bsin = load_bsin(INPUTS["bsin"])
    attrs = attrs.join(bsin, on="bin", how="left", maintain_order="left")
    stats["bsin"] = {"rows": bsin.height, "footprints_matched": int(attrs["bsin_z_grade"].is_not_null().sum())}
    del bsin
    sheds, stats["sheds"] = load_active_sheds(INPUTS["sheds"], today)
    attrs = attrs.join(sheds, on="bin", how="left", maintain_order="left").with_columns(
        (pl.col("n_active_sheds").fill_null(0) > 0).alias("has_scaffold"))
    stats["sheds"]["footprints_with_scaffold"] = int(attrs["has_scaffold"].sum())
    T.lap("bsin_sheds")

    sites = load_lpc_sites(INPUTS["lpc_sites"])
    attrs, stats["lpc_sites"] = lpc_site_attributes(attrs, sites)
    districts = load_lpc_districts(INPUTS["lpc_districts"])
    attrs, stats["hist_districts"] = hist_district_attributes(attrs, districts)
    bdb = load_lpc_building_db(INPUTS["lpc_bdb"]).with_columns(pl.lit(True).alias("_bdb"))
    attrs = attrs.join(bdb, on="bin", how="left", maintain_order="left").with_columns([
        pl.col(c).fill_null("") for c in ("lpc_style", "lpc_material", "lpc_lm_name", "lpc_prop_name", "lpc_bdb_district")])
    stats["lpc_bdb"] = {"rows": bdb.height, "footprints_matched": int(attrs["_bdb"].fill_null(False).sum()),
                        "footprints_with_style": int((attrs["lpc_style"] != "").sum()),
                        "footprints_with_material": int((attrs["lpc_material"] != "").sum())}
    attrs = attrs.drop("_bdb")
    # PLUTO landmark flag without an LP number (report only)
    stats["lpc_sites"]["pluto_landmark_flag_without_lp"] = int(((attrs["pl_landmark"] != "") & (attrs["landmark_id"] == "")).sum())
    nta = load_nta(INPUTS["nta"])
    attrs, stats["nta"] = nta_attributes(attrs, nta)
    del bdb, districts, nta
    T.lap("lpc_nta")

    tree = shapely.STRtree(geoms)
    T.lap("strtree")

    dcwp, stats["dcwp"] = load_dcwp(INPUTS["dcwp"])
    dohmh, stats["dohmh"] = load_dohmh(INPUTS["dohmh"], today)
    biz = pl.concat([dcwp, dohmh], how="vertical")
    matches, stats["storefront_match"] = match_businesses(biz, attrs, tree)
    names, kinds, srcs, stats["storefront_lists"] = storefront_lists(matches, attrs.height)
    has_names = np.array([len(x) > 0 for x in names])
    rule, stats["has_storefront_rule"] = has_storefront_rule(attrs)
    has_sf = rule | has_names
    stats["has_storefront_rule"]["names_only"] = int((has_names & ~rule).sum())
    stats["has_storefront_rule"]["total"] = int(has_sf.sum())
    attrs = attrs.with_columns(pl.Series("has_storefront", has_sf))
    del dcwp, dohmh, biz, matches
    T.lap("storefronts")

    attrs, stats["infer"] = infer_heights_floors(attrs)
    T.lap("infer")

    heading, method, stats["facade_heading"] = facade_headings(
        geoms, attrs["centroid_x"].to_numpy(), attrs["centroid_y"].to_numpy(),
        attrs["lot_x"].to_numpy().astype(np.float64), attrs["lot_y"].to_numpy().astype(np.float64), tree)
    attrs = attrs.with_columns([pl.Series("primary_facade_heading", heading), pl.Series("facade_heading_method", method)])
    T.lap("facade_heading")

    # names, address, seeds, fidelity extras
    fid = attrs["fidelity"].to_numpy().astype(np.uint16)
    fid |= np.where(has_names, S.Fidelity.SIGNAGE_REAL.mask, 0).astype(np.uint16)
    fid |= np.where(attrs["has_scaffold"].to_numpy(), S.Fidelity.SCAFFOLD_REAL.mask, 0).astype(np.uint16)
    attrs = attrs.with_columns([
        pl.Series("fidelity", fid),
        _resolve_name(attrs),
        pl.coalesce([pl.when(pl.col("bsin_address").fill_null("") != "").then(pl.col("bsin_address")).otherwise(None),
                     pl.when(pl.col("pl_address").fill_null("") != "").then(pl.col("pl_address")).otherwise(None), pl.lit("")]).alias("address"),
        pl.Series("lit_seed", S.lit_seed(attrs["bin"].to_numpy(), attrs["doitt_id"].to_numpy())),
        pl.col("pl_bldgclass").alias("bldg_class"),
        pl.col("pl_landuse").alias("land_use"),
        pl.col("has_subgrade").fill_null(-1).cast(pl.Int8),
        pl.col("landmark_id").fill_null(""), pl.col("hist_district").fill_null(""), pl.col("hist_district_id").fill_null(""),
        pl.col("nta").fill_null(""),
    ])
    stats["names"] = {"footprint_name": int((attrs["name"] != "").sum()), "from_lpc": int(((attrs["name"] != "") & (fp.attrs["name"].fill_null("") == "")).sum()) if not subset else None}
    stats["address"] = {"from_bsin": int((attrs["bsin_address"].fill_null("") != "").sum()),
                        "from_pluto_only": int(((attrs["bsin_address"].fill_null("") == "") & (attrs["pl_address"] != "")).sum()),
                        "empty": int((attrs["address"] == "").sum())}

    # attribute rows and the geometry array must still be positionally aligned after every join
    rows = attrs["_row"].to_numpy()
    if len(rows) != len(geoms) or not np.array_equal(rows, np.arange(len(geoms))):
        raise RuntimeError("attribute/geometry misalignment after joins")
    table, geoms_sorted = assemble_table(attrs, geoms, names, kinds, srcs)
    has_names_sorted = np.array([len(x) > 0 for x in table["storefront_names"].to_pylist()])
    T.lap("assemble")

    base_path = out_dir / "buildings_base.parquet"
    pq.write_table(table, base_path, compression="snappy", row_group_size=131072)
    stats["output"] = {"rows": table.num_rows, "bytes": base_path.stat().st_size, "path": str(base_path)}
    T.lap("write_base")

    tile_files: dict = {}
    if not a.no_tiles:
        tile_files = write_tiles(table, geoms_sorted, tiles_root)
        stats["tiles"] = {"n_tiles": len(tile_files), "rows": int(sum(v["rows"] for v in tile_files.values()))}
        with open(out_dir / "tiles_index.json", "w") as f:
            json.dump({"schema_version": 1, "tiles": tile_files}, f, indent=1, sort_keys=True)
        T.lap("write_tiles")

    lm_table, lm_report = build_landmark_footprints(
        pl.from_arrow(table.select(["bin", "name", "height", "ground_z", "footprint_area", "feature_code", "centroid_x", "centroid_y", "landmark_id"])),
        geoms_sorted, shapely.STRtree(geoms_sorted), sites)
    lm_path = out_dir / "landmark_footprints.parquet"
    pq.write_table(lm_table, lm_path, compression="snappy")
    stats["landmarks"] = {"targets": len([r for r in lm_report]), "found": len([r for r in lm_report if r["method"] != "not_found"]),
                          "by_method": {m: len([r for r in lm_report if r["method"] == m]) for m in sorted({r["method"] for r in lm_report})},
                          "rows_written": lm_table.num_rows, "report": lm_report}
    T.lap("landmarks")

    summary = borough_summary(table, has_names_sorted)
    with open(out_dir / "borough_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    stats["borough_summary"] = summary
    stats["timings_s"] = {**T.steps, "total": T.total}
    with open(out_dir / "build_summary.json", "w") as f:
        json.dump(stats, f, indent=1, default=str)

    if not subset:
        srcs_present = [s for s in SOURCE_IDS if manifest.get_download(s) is not None]
        manifest.record_processed("buildings_base", base_path, stage="buildings", sources=srcs_present, rows=table.num_rows,
                                  schema=S.SCHEMA_ID, extra={"columns": [c for c, _, _ in S.COLUMNS], "timings_s": stats["timings_s"]})
        manifest.record_processed("landmark_footprints", lm_path, stage="buildings", sources=srcs_present, rows=lm_table.num_rows,
                                  schema="landmark_footprints/1")
        manifest.record_processed("buildings_borough_summary", out_dir / "borough_summary.json", stage="buildings", sources=srcs_present, schema="borough_summary/1")
        manifest.record_processed("buildings_build_summary", out_dir / "build_summary.json", stage="buildings", sources=srcs_present, schema="build_summary/1")
        if tile_files:
            for t, v in tile_files.items():
                v["sha256"] = manifest.sha256_of(tiles_root / t / "buildings.parquet")
            manifest.record_processed("buildings_tiles", out_dir / "tiles_index.json", stage="buildings", sources=srcs_present,
                                      rows=stats["tiles"]["rows"], schema=S.SCHEMA_ID,
                                      extra={"n_tiles": len(tile_files), "tile_root": str(tiles_root.relative_to(PROCESSED.parent.parent)), "files": tile_files})
        T.lap("manifest")

    stats["timings_s"]["total"] = T.total
    print(json.dumps({"rows": table.num_rows, "tiles": len(tile_files), "pluto_join_rate": stats["pluto"]["join_rate"],
                      "height_real": stats["infer"]["height_lidar"], "floors_real": stats["infer"]["floors_pluto"],
                      "landmarks_found": stats["landmarks"]["found"], "of": stats["landmarks"]["targets"],
                      "timings_s": stats["timings_s"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
