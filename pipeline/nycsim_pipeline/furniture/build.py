"""Furniture stage: every street prop and street tree -> ``tiles/{tile}/props.parquet`` + ``props_catalog.json``.

    python -m nycsim_pipeline furniture [--out-dir DIR] [--tiles-root DIR] [--no-rules] [--no-manifest]
                                        [--bbox X0 Y0 X1 Y1]   # dev subset, refuses to write the real tiles

Pipeline:
 1. load every dataset (:mod:`.datasets`, :mod:`.trees`) and the MTA subway entrances (:mod:`..transit.entrances`);
    trees come from two sources — the 2015 Street Tree Census and the ``natural=tree`` nodes of the OSM extract
    (:mod:`..osm.trees`), which are the only park trees in the build;
 2. add the rule-based fill against the real road geometry (:mod:`.rules`), skipped with a recorded reason when
    ``roads/segments.parquet`` does not exist yet;
 3. de-duplicate across datasets within 1.5 m, plus the measured cross-source radii (:mod:`.dedupe`);
 3b. expand every Citi Bike station row into its kiosk, its dock units and -- only from a ``station_status``
    snapshot -- its bikes (:mod:`.citibike`). After dedupe on purpose: the 0.9 m dock pitch is inside the
    1.5 m bike_parking radius and dedupe would delete every other dock;
 3c. give the six dataset-placed kerb-side kinds (bus shelter, LinkNYC, newsstand, bike shelter, bike rack,
    bus stop sign) the kerb's heading from the nearest roadway centreline and the side of it they stand on
    (:mod:`.kerb`); a heading the loader already carried (an OSM ``direction``) is kept;
 4. sample the ground elevation from surveyed points (:mod:`.elevation`);
 5. assign ``prop_id = kind * 10^10 + rank within kind (sorted by x, y)`` and the tile, and write one
    ``props.parquet`` per tile plus ``furniture/props_catalog.json`` and ``furniture/build_summary.json``.

Everything written here is either a real record from a published dataset (``source = 0``, ``dataset_id`` naming
the manifest source) or a rule placement (``source = 1``, ``dataset_id`` naming the rule).
"""
from __future__ import annotations

import argparse
import json
import os
import logging
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .. import manifest
from ..paths import PROCESSED
from ..tiling import TILE_SIZE_M
from ..transit.entrances import load_subway_entrances
from . import datasets as D
from . import dedupe as dd
from . import rules as R
from . import trees as T
from .catalog import HEIGHT_SOURCE, KINDS, KIND_BY_NAME, catalog_json
from . import citibike
from . import kerb
from . import park_lamps
from . import rooftop
from .elevation import GroundModel
from .schema import arrow_schema, empty_columns

log = logging.getLogger("nycsim.furniture.build")

OUT = PROCESSED / "furniture"
TILES = PROCESSED / "tiles"
BUS_STOPS = PROCESSED / "transit" / "bus_stops.parquet"

KIND_NAME_BY_ID = {k.id: k.name for k in KINDS}
PROP_ID_STRIDE = 10_000_000_000


def tree_props(tc: T.TreeCensus) -> dict:
    df = tc.df
    n = df.height
    cols = empty_columns(n)
    cols["kind"] = np.full(n, KIND_BY_NAME["tree"].id, dtype=np.int16)
    cols["source"] = np.zeros(n, dtype=np.int8)
    cols["dataset_id"] = ["street_trees_2015"] * n
    cols["x"] = df["x"].to_numpy().astype(np.float64)
    cols["y"] = df["y"].to_numpy().astype(np.float64)
    cols["species"] = df["species"].to_list()
    cols["dbh_cm"] = df["dbh_cm"].to_numpy().astype(np.float32)
    cols["height_m"] = df["height_m"].to_numpy().astype(np.float32)
    cols["height_source"] = np.ones(n, dtype=np.int8)          # 1 = allometry
    cols["variant"] = df["variant"].to_numpy().astype(np.int16)
    cols["text"] = df["common"].to_list()
    tree_id = df["tree_id"].to_numpy()
    curb = df["curb_loc"].to_list()
    walk = df["sidewalk"].to_list()
    nta = df["nta"].to_list()
    cols["attrs"] = D._attrs([{"tree_id": int(t), "curb_loc": c, "sidewalk": s, "nta": a}
                              for t, c, s, a in zip(tree_id, curb, walk, nta)])
    return cols


#: LOD size bands ``blender/verify/scene.py::_tree_asset_id`` picks a tree asset with. Reported (never applied)
#: here so the build summary says what the height rule does to the thing a reader will actually look at.
SCENE_TREE_BANDS_M = (12.0, 7.0)


def osm_tree_report(cols: dict) -> dict:
    """What the OSM tree layer actually carries, counted off the rows about to be placed.

    The point of ``with_species`` and ``height_from_osm_tag`` is that they are small: OSM tags a tree's height
    on 1.6 % of nodes and its species on 0.8 %, and a trunk diameter on none, so almost every one of these
    trees has its height drawn from the census population instead. That is a real limit of the source, and the
    counts here are what makes it visible rather than absorbed.
    """
    n = len(cols["x"])
    from_taxon = cols.pop("_height_from_taxon_pool", None)      # side channel from the loader, not a column
    hs = np.asarray(cols["height_source"], dtype=np.int8)
    h = np.asarray(cols["height_m"], dtype=np.float32)
    species = list(cols["species"])
    rep: dict = {
        "rows": n,
        "height_from_osm_tag": int((hs == HEIGHT_SOURCE["measured"]).sum()),
        "height_drawn_from_census_distribution": int((hs == HEIGHT_SOURCE["census_distribution"]).sum()),
        "with_species": sum(1 for s in species if s),
        "dbh_known": int((np.asarray(cols["dbh_cm"], dtype=np.float32) > 0).sum()),
    }
    if from_taxon is not None and n:
        ft = np.asarray(from_taxon, dtype=bool)
        rep["drawn_from_a_taxon_pool"] = int(ft.sum())
        rep["drawn_from_the_whole_population"] = int(rep["height_drawn_from_census_distribution"] - ft.sum())
    if n:
        rep["height_m_percentiles"] = {str(q): round(float(np.percentile(h, q)), 2)
                                       for q in (5, 10, 25, 50, 75, 90, 95)}
        big, mid = SCENE_TREE_BANDS_M
        rep["scene_size_bands"] = {"thresholds_m": [big, mid], "large": int((h >= big).sum()),
                                   "medium": int(((h >= mid) & (h < big)).sum()), "small": int((h < mid).sum())}
        tagged = h[hs == HEIGHT_SOURCE["measured"]]
        if tagged.size:
            rep["tagged_height_m_median"] = round(float(np.median(tagged)), 2)
    summary = PROCESSED / "osm" / "tree_extract_summary.json"
    if summary.exists():
        doc = json.loads(summary.read_text())
        rep["extract"] = {"counts": doc.get("counts", {}), "layers": doc.get("layers", {}),
                          "tag_coverage_of_tree_nodes": doc.get("tag_coverage_of_tree_nodes", {})}
        rep["tree_rows_not_placed"] = doc.get("layers", {}).get("tree_rows", 0)
    return rep


def clip(cols: dict, bbox: tuple[float, float, float, float] | None) -> dict:
    """Keep only the rows inside an NYC_TM box. Used by ``--bbox`` to develop on a handful of tiles."""
    if bbox is None:
        return cols
    x = np.asarray(cols["x"], dtype=np.float64)
    y = np.asarray(cols["y"], dtype=np.float64)
    idx = np.flatnonzero((x >= bbox[0]) & (x <= bbox[2]) & (y >= bbox[1]) & (y <= bbox[3]))
    return {k: ([v[i] for i in idx] if isinstance(v, list) else np.asarray(v)[idx]) for k, v in cols.items()}


def collect(use_rules: bool, segments_path: Path, bbox: tuple[float, float, float, float] | None = None) -> tuple[dict, dict]:
    """Load every source into one column dict. Returns (columns, per-source report).

    ``bbox`` (NYC_TM x0 y0 x1 y1) clips each source as it is loaded, so a subset run never has to hold the
    whole city in memory. It is a development aid: the artefacts it writes cover only those tiles.
    """
    report: dict = {"sources": [], "rules": {}}
    parts: list[dict] = []
    if bbox is not None:
        report["bbox_tm"] = list(bbox)

    tc = T.load_trees()
    parts.append(clip(tree_props(tc), bbox))
    report["trees"] = {
        "rows_in_census": tc.n_total, "alive_placed": tc.n_alive, "dead_excluded": tc.n_dead,
        "stumps_excluded": tc.n_stump, "status_other_excluded": tc.n_status_blank,
        "alive_without_coordinates_dropped": tc.n_no_coord, "alive_without_species": tc.n_no_species,
        "alive_without_dbh_treated_as_5cm": tc.n_no_dbh,
        "top_species": [{"latin": a, "common": b, "count": c} for a, b, c in tc.species_counts[:10]],
        "distinct_species": len(tc.species_counts),
    }

    heights = T.CensusHeights.from_census(tc)
    report["trees"]["height_distribution_pool"] = heights.report()
    osm_trees = clip(D.load_osm_trees(heights=heights), bbox)
    report["osm_trees"] = osm_tree_report(osm_trees)
    parts.append(osm_trees)

    loaders = [
        ("hydrants", D.load_hydrants), ("bus_stop_shelters", D.load_bus_shelters), ("linknyc", D.load_linknyc),
        ("newsstands", D.load_newsstands), ("bike_shelters", D.load_bike_shelters),
        ("pedestrian_ramps", D.load_pedestrian_ramps), ("rtpi_signs", D.load_rtpi_signs),
        ("citibike_gbfs_stations", D.load_citibike), ("parks_structures", D.load_parks_structures),
        ("plan_railroad_structure", D.load_subway_vent_structures), ("plan_misc_structures", D.load_misc_structures),
        ("plan_swimming_pools", D.load_swimming_pools), ("plan_cooling_towers", D.load_cooling_towers),
        ("osm_newyork_pbf", D.load_osm_furniture),
    ]
    for source_id, fn in loaders:
        t = time.perf_counter()
        cols = clip(fn(), bbox)
        parts.append(cols)
        report["sources"].append({"source_id": source_id, "rows": int(len(cols["x"])),
                                  "seconds": round(time.perf_counter() - t, 1)})

    ent = load_subway_entrances()
    parts.append(clip(D.load_subway_entrance_props(ent), bbox))
    report["sources"].append({"source_id": "subway_entrances", "rows": int(len(ent))})

    if BUS_STOPS.exists():
        cols = clip(D.load_bus_stop_signs(BUS_STOPS), bbox)
        parts.append(cols)
        report["sources"].append({"source_id": "gtfs_bus", "rows": int(len(cols["x"]))})
    else:
        report["sources"].append({"source_id": "gtfs_bus", "rows": 0,
                                  "skipped": f"{BUS_STOPS} missing — run the transit stage first"})
        log.error("%s missing: bus stop sign props (kind 24) are NOT written", BUS_STOPS)

    cols = D.concat(parts)
    if use_rules:
        existing = {}
        kind_arr = np.asarray(cols["kind"])
        for name in ("street_lamp", "manhole"):
            m = kind_arr == KIND_BY_NAME[name].id
            existing[name] = np.column_stack([np.asarray(cols["x"])[m], np.asarray(cols["y"])[m]])
        rule_parts, rule_report = R.build_rule_props(existing, segments_path)
        report["rules"] = rule_report
        if rule_parts:
            cols = D.concat([cols] + [clip(p, bbox) for p in rule_parts])
    else:
        report["rules"] = {"skipped": True, "reason": "--no-rules"}
    return cols, report


def finalise(cols: dict, ground: GroundModel) -> tuple[pa.Table, dict]:
    """Ground elevation, deterministic prop ids and tile assignment; returns the whole table sorted by tile."""
    x = np.asarray(cols["x"], dtype=np.float64)
    y = np.asarray(cols["y"], dtype=np.float64)
    z = np.asarray(cols["z"], dtype=np.float32)
    z_src = np.asarray(cols["z_source"], dtype=np.int8)
    need = ~np.isfinite(z)
    if need.any():
        zz, ss = ground.sample(x[need], y[need])
        z[need] = zz.astype(np.float32)
        z_src[need] = ss
    # The one kind the ground model gets wrong on purpose: a planimetric cooling tower is digitised
    # on a roof, so its surveyed ground elevation puts it inside the building. lift() joins the BIN
    # in its attrs against the measured roof.
    try:
        roof_stats = rooftop.lift(kind_of := np.asarray(cols["kind"], dtype=np.int16), z, z_src,
                                  list(cols["attrs"]), rooftop.roof_heights())
    except FileNotFoundError as exc:
        roof_stats = {"skipped": f"no buildings table: {exc}"}
    del kind_of
    cols["z"] = z
    cols["z_source"] = z_src

    kind = np.asarray(cols["kind"], dtype=np.int16)
    order = np.lexsort((y, x, kind))                     # per kind, ranked by x then y
    rank = np.empty(len(order), dtype=np.int64)
    rank[order] = np.arange(len(order), dtype=np.int64)
    kind_start = {}
    ks, kc = np.unique(kind[order], return_counts=True)
    off = 0
    for k, c in zip(ks, kc):
        kind_start[int(k)] = off
        off += int(c)
    base = np.array([kind_start[int(k)] for k in kind], dtype=np.int64)
    cols["prop_id"] = kind.astype(np.int64) * PROP_ID_STRIDE + (rank - base)

    tx = np.floor(x / TILE_SIZE_M).astype(np.int32)
    ty = np.floor(y / TILE_SIZE_M).astype(np.int32)
    cols["tx"] = tx
    cols["ty"] = ty
    cols["tile"] = [f"t_{a}_{b}" for a, b in zip(tx.tolist(), ty.tolist())]

    schema = arrow_schema()
    table = pa.table({f.name: pa.array(cols[f.name], type=f.type) for f in schema}, schema=schema)
    # group the rows of each tile into one contiguous run, ordered by prop_id inside the tile
    table = table.take(pa.array(np.lexsort((cols["prop_id"], ty, tx))))
    stats = {
        "rows": table.num_rows,
        "z_from_spot_elevation": int((z_src == 3).sum()),
        "z_extrapolated_far": int((z_src == 4).sum()),
        "z_from_dataset": int((z_src == 1).sum()),
        "z_missing": int((~np.isfinite(z)).sum()),
        "z_lifted_to_roof": roof_stats,
    }
    return table, stats


def write_tiles(table: pa.Table, tiles_root: Path) -> dict:
    """One ``props.parquet`` per tile. A tile whose bytes would not change is left alone, mtime included.

    The parquet writer is deterministic for the same table, so comparing the new bytes with the file on
    disk says exactly which tiles a run touched -- ``tiles_rewritten`` in the summary and
    ``furniture/tiles_changed.txt`` -- and "confined to one kind" becomes a measurable statement rather
    than a claim.
    """
    import io

    tiles = np.asarray(table.column("tile").to_pylist(), dtype=object)
    uniq, starts, counts = np.unique(tiles, return_index=True, return_counts=True)
    files: dict[str, int] = {}
    total_bytes = 0
    rewritten: list[str] = []
    unchanged = 0
    for name, s, c in zip(uniq, starts, counts):
        sl = table.slice(int(s), int(c))
        meta = dict(sl.schema.metadata or {})
        meta[b"nycsim.tile"] = str(name).encode()
        meta[b"nycsim.rows"] = str(sl.num_rows).encode()
        d = tiles_root / str(name)
        d.mkdir(parents=True, exist_ok=True)
        p = d / "props.parquet"
        buf = io.BytesIO()
        pq.write_table(sl.replace_schema_metadata(meta), buf, compression="snappy")
        data = buf.getvalue()
        if p.is_file() and p.stat().st_size == len(data) and p.read_bytes() == data:
            unchanged += 1
        else:
            # Written beside and renamed over: a comparison render or a tile reader that opens this
            # file while the stage runs sees the old bytes or the new ones, never a truncated file.
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, p)
            rewritten.append(str(name))
        files[str(name)] = int(sl.num_rows)
        total_bytes += len(data)
    log.info("wrote %d tile prop files (%.1f MB): %d rewritten, %d byte-identical and left alone",
             len(files), total_bytes / 1e6, len(rewritten), unchanged)
    return {"tiles": len(files), "bytes": total_bytes, "rows_per_tile": files,
            "tiles_rewritten": len(rewritten), "tiles_unchanged": unchanged, "rewritten": rewritten}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--tiles-root", default=str(TILES))
    ap.add_argument("--segments", default=str(R.SEGMENTS))
    ap.add_argument("--no-rules", action="store_true")
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"),
                    help="restrict to an NYC_TM box (dev subset: writes only the tiles it covers)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    t0 = time.perf_counter()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tiles_root = Path(a.tiles_root)

    bbox = tuple(a.bbox) if a.bbox else None
    if bbox is not None and (Path(a.tiles_root) == TILES or Path(a.out_dir) == OUT):
        log.error("--bbox writes a partial city; point --tiles-root and --out-dir somewhere other than %s / %s", TILES, OUT)
        return 2
    cols, report = collect(not a.no_rules, Path(a.segments), bbox)
    log.info("collected %d prop rows", len(cols["x"]))
    # What the OSM lamp nodes' own tags said about their fixture, so the census is in the summary
    # and not only in a log line (docs/DEVIATIONS.md J56).
    report["osm_lamp_fixtures"] = dict(sorted(D.LAMP_FIXTURE_TALLY.items(), key=lambda kv: -kv[1]))
    t = time.perf_counter()
    keep, dedupe_report = dd.dedupe(cols, KIND_NAME_BY_ID)
    idx = np.flatnonzero(keep)
    cols = {k: (np.asarray(v)[idx] if not isinstance(v, list) else [v[i] for i in idx]) for k, v in cols.items()}
    report["dedupe"] = dedupe_report
    report["timings_s"] = {"dedupe": round(time.perf_counter() - t, 1)}

    # After the dedupe, so a pole that loses to a surveyed one is not re-fixtured on its way out.
    t = time.perf_counter()
    hw, hw_unknown = park_lamps.highway_mask_from_attrs(list(cols["attrs"]))
    park_report = park_lamps.apply(cols, KIND_BY_NAME["street_lamp"].id, highway_mask=hw)
    park_report["road_class_unknown"] = int(hw_unknown)
    report["rules"] = dict(report.get("rules") or {})
    report["rules"]["park_post_lamp"] = park_report
    report["timings_s"]["park_lamps"] = round(time.perf_counter() - t, 1)

    # After dedupe, and only then: the 0.9 m dock pitch is inside dedupe's 1.5 m bike_parking radius,
    # so an expanded station going through dedupe loses every other dock (a unit test documents it).
    # The single station row that went through dedupe is also what the 4 OSM bike_rack drops were
    # decided against.
    t = time.perf_counter()
    segments = R.load_segments(Path(a.segments))          # read once for the two kerb passes
    cols, report["citibike"] = citibike.apply(cols, Path(a.segments), seg=segments)
    report["timings_s"]["citibike"] = round(time.perf_counter() - t, 1)

    # 3c. The six dataset-placed kerb-side kinds take the kerb's heading and the side of the centreline
    # (:mod:`.kerb`, docs/DEVIATIONS.md J84). After dedupe, so the rows that survive are the rows measured,
    # and before the ground sample; it writes heading and attrs of those kinds and nothing else.
    t = time.perf_counter()
    cols, report["kerb"] = kerb.apply(cols, Path(a.segments), seg=segments)
    report["timings_s"]["kerb"] = round(time.perf_counter() - t, 1)
    del segments

    t = time.perf_counter()
    ground = GroundModel.build()
    report["ground_model"] = {"reference_points": ground.n_points, "spot_elevations": ground.n_spot,
                              "building_grades": ground.n_points - ground.n_spot}
    report["timings_s"]["ground_model"] = round(time.perf_counter() - t, 1)

    t = time.perf_counter()
    table, stats = finalise(cols, ground)
    report["z"] = stats
    report["timings_s"]["finalise"] = round(time.perf_counter() - t, 1)

    t = time.perf_counter()
    report["tiles"] = write_tiles(table, tiles_root)
    report["timings_s"]["write_tiles"] = round(time.perf_counter() - t, 1)
    (out / "tiles_changed.txt").write_text("\n".join(report["tiles"]["rewritten"]) + "\n")

    kind_arr = np.asarray(table.column("kind").to_pylist())
    src_arr = np.asarray(table.column("source").to_pylist())
    counts = Counter()
    for k, c in zip(*np.unique(kind_arr, return_counts=True)):
        counts[KIND_NAME_BY_ID[int(k)]] = int(c)
    report["counts_by_kind"] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    report["counts_by_source"] = {"dataset": int((src_arr == 0).sum()), "rule": int((src_arr == 1).sum())}
    report["counts_by_dataset"] = dict(Counter(table.column("dataset_id").to_pylist()).most_common())

    cat = catalog_json(counts)
    cat["counts_by_source"] = report["counts_by_source"]
    (out / "props_catalog.json").write_text(json.dumps(cat, indent=1))
    report["timings_s"]["total"] = round(time.perf_counter() - t0, 1)
    (out / "build_summary.json").write_text(json.dumps(report, indent=1))
    log.info("furniture stage done in %.1f s: %d props over %d tiles",
             report["timings_s"]["total"], table.num_rows, report["tiles"]["tiles"])

    if not a.no_manifest and Path(a.out_dir) == OUT:
        srcs = [s["source_id"] for s in report["sources"]] + ["street_trees_2015", "plan_elevation_points"]
        if report.get("citibike", {}).get("status_snapshot_used"):
            srcs.append(citibike.STATUS_ID)
        manifest.record_processed("furniture_props_catalog", out / "props_catalog.json", stage="furniture",
                                  sources=srcs, rows=table.num_rows, schema="props_catalog/1")
        manifest.record_processed("furniture_build_summary", out / "build_summary.json", stage="furniture",
                                  sources=srcs, schema="furniture_build_summary/1")
        index = {"schema_version": 1, "stage": "furniture", "rows": table.num_rows,
                 "tiles": report["tiles"]["rows_per_tile"]}
        (out / "tiles_index.json").write_text(json.dumps(index, indent=1))
        manifest.record_processed("furniture_tiles", out / "tiles_index.json", stage="furniture",
                                  sources=srcs, rows=table.num_rows, schema="furniture_tiles_index/1")

    print(json.dumps({k: report[k] for k in ("counts_by_kind", "counts_by_source", "z", "timings_s")
                      if k in report}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
