"""OSM tree extraction: ``natural=tree`` nodes and ``natural=tree_row`` ways -> ``data/processed/osm/``.

The 2015 Street Tree Census (``uvpi-gqnh``) is a *street* inventory, so it holds no park interior: 1,756 of the
1,916 green polygons of 2 ha or more in this repository's own OSM landuse layer contain not one census tree
(DEVIATIONS D10). The BBBike New York extract already on disk carries a second, independent tree source that no
stage had read. This module reads it.

Layers (NYC_TM metres, ``nycsim.schema`` key, same conventions as :mod:`.extract`):

* ``trees.parquet``      one row per ``natural=tree`` node — the only layer the furniture stage places.
* ``tree_rows.parquet``  one row per ``natural=tree_row`` way, as a LineString. **Deliberately not placed.**
  A row is a line, not a set of trees: OSM publishes neither a count nor a spacing along it, so turning one into
  individual trunks would mean inventing positions. The layer is written so the geometry is on disk and the gap
  is countable, and :mod:`..furniture.datasets` ignores it.

Every tag each object carries is preserved verbatim in the ``tags`` JSON column (the convention
``signals_stops`` / ``street_furniture_osm`` already use); the named columns are the subset the placement stage
reads. Nothing is filled in: a tag that is absent stays absent, and ``height_m`` is NaN wherever ``height`` is
missing or unparsable rather than being replaced by a guess.

**Trunk diameter is deliberately not derived.** OSM's ``circumference`` is tagged on 17 of the 71,447 nodes in
twelve distinct spellings across at least four unit conventions ('5 cm', '26"', '1.91 m', '2.18', '55 inches'),
and ``diameter`` on 73 of which 35 read '10m' — a crown, not a trunk. Both are carried as raw strings and neither
is converted into a DBH; the placement stage leaves ``dbh_cm`` absent. Deriving one from that many spellings
would be a unit guess presented as a measurement.

Run: ``python -m nycsim_pipeline.osm.trees [--pbf PATH] [--out DIR]``
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import osmium
import pyarrow as pa
import shapely

from ..crs import lonlat_to_tm
from ..manifest import record_processed
from ..paths import PROCESSED, RAW
from .extract import LICENSE, SOURCE_ID, _in_scope_tm, parse_length_m, scope_lonlat_bbox
from .geoparquet import ParquetBatchWriter

log = logging.getLogger("nycsim.osm.trees")

PBF_DEFAULT = RAW / "osm" / "NewYork.osm.pbf"
OUT_DEFAULT = PROCESSED / "osm"
BATCH = 50_000

# Tags read into their own column. Everything else survives in the ``tags`` JSON.
# ``species``/``genus``/``taxon`` are the taxon triple, ``leaf_type``/``leaf_cycle``/``denotation`` the
# categorical describers, ``height`` the only dimension OSM states in a usable unit, and
# ``circumference``/``diameter_crown``/``diameter`` the dimensions it does not (kept raw, see the module docstring).
TREE_TAGS = ("species", "genus", "taxon", "leaf_type", "leaf_cycle", "denotation", "name", "ref",
             "start_date", "operator", "height", "circumference", "diameter_crown", "diameter")

S, F32, F64, I64 = pa.string(), pa.float32(), pa.float64(), pa.int64()

TREE_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("x", F64), ("y", F64), ("species", S), ("genus", S),
                         ("taxon", S), ("leaf_type", S), ("leaf_cycle", S), ("denotation", S), ("name", S),
                         ("ref", S), ("start_date", S), ("operator", S), ("height_m", F32), ("height_raw", S),
                         ("circumference_raw", S), ("diameter_crown_raw", S), ("diameter_raw", S), ("tags", S)])

TREE_ROW_SCHEMA = pa.schema([("osm_id", I64), ("osm_type", S), ("geometry", pa.binary()), ("species", S), ("genus", S),
                             ("taxon", S), ("leaf_type", S), ("leaf_cycle", S), ("denotation", S), ("name", S),
                             ("ref", S), ("start_date", S), ("operator", S), ("height_m", F32), ("height_raw", S),
                             ("circumference_raw", S), ("diameter_crown_raw", S), ("diameter_raw", S),
                             ("length_m", F32), ("n_nodes", pa.int32()), ("tags", S)])


def _tag_columns(tags) -> dict[str, Any]:
    """The named tag columns of one object; absent tags stay empty strings / NaN."""
    get = tags.get
    row: dict[str, Any] = {k: (get(k) or "") for k in TREE_TAGS if k not in ("height", "circumference", "diameter_crown", "diameter")}
    row["height_raw"] = get("height") or ""
    row["circumference_raw"] = get("circumference") or ""
    row["diameter_crown_raw"] = get("diameter_crown") or ""
    row["diameter_raw"] = get("diameter") or ""
    row["height_m"] = parse_length_m(row["height_raw"] or None)
    row["tags"] = json.dumps({t.k: t.v for t in tags}, ensure_ascii=False, separators=(",", ":"))
    return row


class TreeExtractor:
    """Two cheap passes over the PBF: tagged objects, then the node locations the tree rows need.

    ``extract.py``'s single pass carries a full node-location index (``with_locations('flex_mem')``) because it
    builds every area in the file. Nine thousand way nodes do not justify that much resident memory next to a
    render, so the way geometry is resolved with an ``IdFilter`` second pass instead.
    """

    def __init__(self, pbf: Path, out: Path, bbox_lonlat: tuple[float, float, float, float] | None = None) -> None:
        self.pbf = Path(pbf)
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.bbox = bbox_lonlat or scope_lonlat_bbox()
        self.counts: Counter = Counter()
        self.tag_coverage: Counter = Counter()
        self.timings: dict[str, float] = {}
        self.rows: list[dict[str, Any]] = []          # tree nodes, buffered then written in batches
        self.lonlat: list[tuple[float, float]] = []
        self.row_ways: list[dict[str, Any]] = []      # tree_row ways awaiting their node locations
        self.needed_nodes: set[int] = set()
        self.writers: dict[str, ParquetBatchWriter] = {}
        self.dropped_out_of_scope = Counter()

    def _writer(self, name: str, schema: pa.Schema, geometry: str | None) -> ParquetBatchWriter:
        w = ParquetBatchWriter(self.out / f"{name}.parquet", schema, schema_name=f"nycsim.osm.{name}.v1",
                               geometry_column=geometry,
                               extra_metadata={"nycsim.license": LICENSE, "nycsim.source": SOURCE_ID})
        self.writers[name] = w
        return w

    def _in_bbox(self, lon: float, lat: float) -> bool:
        b = self.bbox
        return b[0] <= lon <= b[2] and b[1] <= lat <= b[3]

    # ---- pass 1: tagged objects
    def pass_tagged(self) -> None:
        t0 = time.time()
        fp = osmium.FileProcessor(self.pbf).with_filter(osmium.filter.KeyFilter("natural"))
        for o in fp:
            v = o.tags.get("natural")
            if v == "tree" and o.is_node():
                self.counts["tree_nodes_in_file"] += 1
                for t in o.tags:
                    self.tag_coverage[t.k] += 1
                try:
                    lon, lat = o.location.lon, o.location.lat
                except Exception:
                    self.counts["tree_nodes_without_location"] += 1
                    continue
                if not self._in_bbox(lon, lat):
                    self.dropped_out_of_scope["trees"] += 1
                    continue
                row = _tag_columns(o.tags)
                row["osm_id"] = o.id
                row["osm_type"] = "node"
                self.rows.append(row)
                self.lonlat.append((lon, lat))
                if len(self.rows) >= BATCH:
                    self.flush_trees()
            elif v == "tree" and not o.is_node():
                self.counts["tree_non_node"] += 1
            elif v == "tree_row":
                if o.is_way():
                    self.counts["tree_row_ways_in_file"] += 1
                    refs = [nd.ref for nd in o.nodes]
                    row = _tag_columns(o.tags)
                    row["osm_id"] = o.id
                    row["osm_type"] = "way"
                    row["refs"] = refs
                    self.row_ways.append(row)
                    self.needed_nodes.update(refs)
                else:
                    self.counts["tree_row_non_way"] += 1
        self.flush_trees()
        self.timings["pass_tagged_s"] = round(time.time() - t0, 1)
        log.info("pass 1: %d natural=tree nodes, %d natural=tree_row ways (%d way nodes to resolve) in %.0f s",
                 self.counts["tree_nodes_in_file"], self.counts["tree_row_ways_in_file"], len(self.needed_nodes),
                 self.timings["pass_tagged_s"])

    def flush_trees(self) -> None:
        if not self.rows:
            return
        rows, lonlat = self.rows, self.lonlat
        self.rows, self.lonlat = [], []
        arr = np.array(lonlat, dtype=float)
        x, y = lonlat_to_tm(arr[:, 0], arr[:, 1])
        keep = _in_scope_tm(x, y)
        self.dropped_out_of_scope["trees"] += int((~keep).sum())
        idx = np.flatnonzero(keep)
        if idx.size == 0:
            return
        cols: dict[str, Any] = {k: [rows[i][k] for i in idx] for k in TREE_SCHEMA.names if k not in ("x", "y")}
        cols["x"] = x[keep]
        cols["y"] = y[keep]
        self.writers["trees"].write(cols)

    # ---- pass 2: the node locations the tree rows need
    def pass_row_nodes(self) -> None:
        if not self.row_ways:
            return
        t0 = time.time()
        loc: dict[int, tuple[float, float]] = {}
        needed = self.needed_nodes
        fp = osmium.FileProcessor(self.pbf, osmium.osm.NODE).with_filter(osmium.filter.IdFilter(sorted(needed)))
        for n in fp:
            try:
                loc[n.id] = (n.location.lon, n.location.lat)
            except Exception:
                continue
        self.timings["pass_row_nodes_s"] = round(time.time() - t0, 1)
        log.info("pass 2: resolved %d of %d tree_row way nodes in %.0f s", len(loc), len(needed),
                 self.timings["pass_row_nodes_s"])

        cols: dict[str, list] = {k: [] for k in TREE_ROW_SCHEMA.names}
        for row in self.row_ways:
            pts = [loc[r] for r in row["refs"] if r in loc]
            if len(pts) < 2:
                self.counts["tree_rows_without_geometry"] += 1
                continue
            arr = np.array(pts, dtype=float)
            x, y = lonlat_to_tm(arr[:, 0], arr[:, 1])
            if not _in_scope_tm(x, y).any():
                self.dropped_out_of_scope["tree_rows"] += 1
                continue
            line = shapely.linestrings(np.column_stack([x, y]))
            for k in TREE_ROW_SCHEMA.names:
                if k == "geometry":
                    cols[k].append(shapely.to_wkb(line))
                elif k == "length_m":
                    cols[k].append(float(shapely.length(line)))
                elif k == "n_nodes":
                    cols[k].append(len(pts))
                else:
                    cols[k].append(row[k])
        if cols["osm_id"]:
            self.writers["tree_rows"].write(cols)

    # ---- finish
    def run(self) -> dict[str, Any]:
        t_all = time.time()
        self._writer("trees", TREE_SCHEMA, None)
        self._writer("tree_rows", TREE_ROW_SCHEMA, "geometry")
        self.pass_tagged()
        self.pass_row_nodes()
        summary = self.close(t_all)
        return summary

    def close(self, t_all: float) -> dict[str, Any]:
        layer_rows: dict[str, int] = {}
        for name, w in self.writers.items():
            path = w.close()
            layer_rows[name] = w.rows
            record_processed(f"osm/{name}", path, stage="osm_trees", sources=[SOURCE_ID], rows=w.rows,
                             schema=w.schema_name, extra={"license": LICENSE})
            log.info("wrote %s: %d rows", path.name, w.rows)
        self.timings["total_s"] = round(time.time() - t_all, 1)
        n = max(1, self.counts["tree_nodes_in_file"])
        summary = {
            "schema_version": 1,
            "pbf": str(self.pbf),
            "layers": layer_rows,
            "counts": dict(self.counts),
            "dropped_out_of_scope": dict(self.dropped_out_of_scope),
            "tag_coverage_of_tree_nodes": {k: {"nodes": c, "pct": round(100.0 * c / n, 3)}
                                           for k, c in self.tag_coverage.most_common()},
            "timings": self.timings,
            "license": LICENSE,
            "not_placed": {
                "tree_rows": "natural=tree_row is a line with no published count or spacing; individual trunks "
                             "along it would be invented positions, so the layer is written and never placed.",
                "dbh": "no OSM tag gives a trunk diameter in a single unit convention; circumference and "
                       "diameter are carried raw and dbh_cm is left absent.",
            },
        }
        with open(self.out / "tree_extract_summary.json", "w") as f:
            json.dump(summary, f, indent=1)
        return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pbf", type=Path, default=PBF_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not a.pbf.exists():
        log.error("PBF not found: %s (run: python -m nycsim_pipeline download --id %s)", a.pbf, SOURCE_ID)
        return 2
    summary = TreeExtractor(a.pbf, a.out).run()
    print(json.dumps({"layers": summary["layers"], "counts": summary["counts"], "timings": summary["timings"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
