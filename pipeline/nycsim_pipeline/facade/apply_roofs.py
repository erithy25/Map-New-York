"""Re-apply ``buildings/roof_attrs.parquet`` to the facade stage's output, without re-running the classifier.

    python -m nycsim_pipeline.facade.apply_roofs [--tiles t_x_y ...]

The CityGML stage produces ``roof_attrs.parquet`` (DATA_CONTRACTS §5.3) on its own schedule.  When the facade stage
runs before it, ``roof_type`` is 0, ``roof_mesh_ref`` is empty and ``ROOF_REAL`` is clear; this stage merges the real
values in afterwards.  It is idempotent and re-runnable, and it re-derives exactly the same precedence the ``rules``
pass uses (ADR-013):

1. a real source — CityGML LOD2 (``roof_type_source`` 0) or an OSM ``roof:shape`` tag (source 1) — wins;
2. otherwise the facade stage's own house-stock rule keeps its shape (``roof_source`` 2, ``ROOF_INFERRED`` set);
3. otherwise flat.

``ROOF_REAL`` (fidelity bit 2) is set from ``citygml_match`` independently of the shape: it means the measured LOD2
massing solid exists for that BIN.

The stage rewrites ``facade/facade_attrs.parquet`` and every ``tiles/{tile}/buildings.parquet`` in place, touching only
``roof_type``, ``roof_mesh_ref``, ``roof_source``, ``roof_pitch_deg``, ``roof_ridge_heading``, ``roof_eave_z`` and the
two fidelity bits.  Kit placements are unaffected — no placement depends on the roof shape.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from ..paths import PROCESSED
from . import roofs as RF
from .build import FACADE_ATTRS, FIDELITY_ROOF_REAL, ROOF_ATTRS, TILES_ROOT, _apply_roof_attrs

log = logging.getLogger("nycsim.facade.apply_roofs")

ROOF_COLUMNS = ("roof_type", "roof_mesh_ref", "roof_source", "roof_pitch_deg", "roof_ridge_heading", "roof_eave_z")


def merge(attrs_path: Path = FACADE_ATTRS) -> tuple[pl.DataFrame, dict]:
    """Recompute the roof columns and the two roof fidelity bits for the whole city."""
    if not ROOF_ATTRS.exists():
        raise FileNotFoundError(f"{ROOF_ATTRS} missing: the CityGML stage has not produced it yet")
    if not attrs_path.exists():
        raise FileNotFoundError(f"{attrs_path} missing: run `facade rules` first")
    attrs = pl.read_parquet(attrs_path)
    bins = attrs["bin"].to_numpy()
    rt, ref, roof_real, src, state = _apply_roof_attrs(bins)

    rule = attrs["roof_source"].to_numpy() == RF.ROOF_SRC_FACADE_RULE
    from_real_source = np.isin(src, [RF.ROOF_SRC_CITYGML, RF.ROOF_SRC_OSM])
    keep_rule = rule & ~from_real_source
    roof_type = np.where(from_real_source, rt, np.where(keep_rule, attrs["roof_type"].to_numpy(), 0)).astype(np.int8)
    roof_src = np.where(from_real_source, src,
                        np.where(keep_rule, RF.ROOF_SRC_FACADE_RULE, RF.ROOF_SRC_DEFAULT_FLAT)).astype(np.int8)
    pitch = np.where(keep_rule, attrs["roof_pitch_deg"].to_numpy(), 0.0).astype(np.float32)
    ridge = np.where(keep_rule, attrs["roof_ridge_heading"].to_numpy(), 0.0).astype(np.float32)
    eave = attrs["roof_eave_z"].to_numpy().astype(np.float32)

    fid = attrs["fidelity"].to_numpy().astype(np.uint32)
    fid &= np.uint32(~(FIDELITY_ROOF_REAL | RF.FIDELITY_ROOF_INFERRED))
    fid |= np.where(roof_real, FIDELITY_ROOF_REAL, 0).astype(np.uint32)
    fid |= np.where(keep_rule, RF.FIDELITY_ROOF_INFERRED, 0).astype(np.uint32)

    out = attrs.with_columns([
        pl.Series("roof_type", roof_type, dtype=pl.Int8),
        pl.Series("roof_mesh_ref", [str(x) for x in ref], dtype=pl.Utf8),
        pl.Series("roof_source", roof_src, dtype=pl.Int8),
        pl.Series("roof_pitch_deg", pitch, dtype=pl.Float32),
        pl.Series("roof_ridge_heading", ridge, dtype=pl.Float32),
        pl.Series("roof_eave_z", eave, dtype=pl.Float32),
        pl.Series("fidelity", fid.astype(np.uint16), dtype=pl.UInt16),
    ])
    stats = {
        "roof_attrs": state,
        "roof_real": int(roof_real.sum()),
        "roof_inferred": int(keep_rule.sum()),
        "roof_type_distribution": {str(int(k)): int(v) for k, v in
                                   zip(*np.unique(roof_type, return_counts=True))},
        "roof_source_counts": {str(int(k)): int(v) for k, v in zip(*np.unique(roof_src, return_counts=True))},
        "roof_mesh_refs": int(sum(1 for x in ref if x)),
    }
    return out, stats


def write_tiles(attrs: pl.DataFrame, tiles_root: Path, only: set[str] | None = None) -> dict:
    """Rewrite the roof columns and ``fidelity`` in every per-tile ``buildings.parquet``."""
    parts = attrs.partition_by("tile", as_dict=True)
    parts = {k[0] if isinstance(k, tuple) else k: v for k, v in parts.items()}
    n_tiles = 0
    n_rows = 0
    for tile, a in sorted(parts.items()):
        if only is not None and tile not in only:
            continue
        p = tiles_root / tile / "buildings.parquet"
        if not p.exists():
            continue
        tbl = pq.read_table(p)
        a = a.sort("row")
        if tbl.num_rows != a.height:
            raise RuntimeError(f"{tile}: {tbl.num_rows} rows in the tile, {a.height} in facade_attrs")
        if not np.array_equal(tbl["bin"].to_numpy(), a["bin"].to_numpy()):
            raise RuntimeError(f"{tile}: bin order differs between the tile file and facade_attrs")
        arrays = list(tbl.columns)
        names = tbl.schema.names
        for col in (*ROOF_COLUMNS, "fidelity"):
            if col not in names:
                raise RuntimeError(f"{tile}: column {col} missing — run `facade emit` first")
            i = names.index(col)
            arrays[i] = a[col].to_arrow().cast(tbl.schema.field(i).type)
        out = pa.Table.from_arrays(arrays, schema=tbl.schema)
        tmp = p.with_suffix(".tmp")
        pq.write_table(out, tmp, compression="snappy")
        tmp.replace(p)
        n_tiles += 1
        n_rows += out.num_rows
    return {"tiles": n_tiles, "rows": n_rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nycsim_pipeline.facade.apply_roofs",
                                 description="Merge buildings/roof_attrs.parquet into the facade stage output")
    ap.add_argument("--tiles", nargs="*", default=None)
    ap.add_argument("--attrs", default=str(FACADE_ATTRS))
    ap.add_argument("--tiles-root", default=str(TILES_ROOT))
    ap.add_argument("--dry-run", action="store_true", help="report what would change without writing")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    attrs_path = Path(a.attrs)
    out, stats = merge(attrs_path)
    if a.dry_run:
        print(json.dumps({"dry_run": True, **stats}, indent=1))
        return 0
    tbl = out.to_arrow().cast(pq.ParquetFile(attrs_path).schema_arrow)
    tmp = attrs_path.with_suffix(".tmp")
    pq.write_table(tbl, tmp, compression="snappy", row_group_size=262144)
    tmp.replace(attrs_path)
    written = write_tiles(out, Path(a.tiles_root), set(a.tiles) if a.tiles else None)
    summary = {"stage": "facade_apply_roofs", **stats, **written}
    with open(PROCESSED / "facade" / "apply_roofs_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
