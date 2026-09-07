"""Rooftop props stand on the roof of the building the survey put them on.

``props.parquet`` samples every prop's ``z`` from the ground model, and for 33 of the 34 kinds that
is right: a hydrant, a bench and a street tree all stand on the pavement. The 34th is the DOITT
planimetric cooling tower, which stands on a roof. All 81,684 of them were written at street level --
``z_source = 3``, a surveyed spot elevation of the *ground* -- so every one of them was inside the
building it belongs on top of, and none was placed at all because nothing in the level builder could
resolve the kind to a mesh (see ``nycsim_pipeline.furniture.assets``).

The survey names the building: each row's ``attrs`` carries the ``bin`` the feature was digitised
against, and ``buildings/buildings_base.parquet`` has that BIN's measured ``roof_z`` in the same
NAVD88 datum. This joins the two.

Run as a stage to patch tiles already on disk::

    python -m nycsim_pipeline.furniture.rooftop            # every tile
    python -m nycsim_pipeline.furniture.rooftop --tiles t_-4_4,t_-4_5

``finalise`` in :mod:`.build` calls :func:`lift` for the same reason, so a full rebuild needs no
patch afterwards. Both are idempotent: the second run writes the same z it read.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from ..paths import PROCESSED

log = logging.getLogger("nycsim.furniture.rooftop")

#: Prop kinds the survey digitises on a roof rather than on the ground. Only one today; the constant
#: exists so a second one is a list entry rather than a second copy of this module.
ROOFTOP_KINDS = (28,)

#: ``z_source`` for a prop lifted onto its building's measured roof. The other codes are in
#: ``furniture/catalog.py::Z_SOURCE``; this extends that enum and ``props_catalog.json`` states it.
Z_SOURCE_ROOF = 5

BUILDINGS = PROCESSED / "buildings" / "buildings_base.parquet"


def roof_heights(buildings: Path = BUILDINGS) -> dict[int, float]:
    """``bin -> roof_z`` (metres, NAVD88) for every building with a measured roof."""
    if not buildings.is_file():
        raise FileNotFoundError(buildings)
    t = pq.read_table(buildings, columns=["bin", "roof_z"])
    bins = np.asarray(t.column("bin"), dtype=np.int64)
    rz = np.asarray(t.column("roof_z"), dtype=np.float64)
    ok = np.isfinite(rz)
    return {int(b): float(z) for b, z in zip(bins[ok], rz[ok])}


def _bin_of(attrs: str | None) -> int | None:
    if not attrs:
        return None
    try:
        v = json.loads(attrs).get("bin")
    except (json.JSONDecodeError, AttributeError):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def lift(kind: np.ndarray, z: np.ndarray, z_source: np.ndarray, attrs: list[str | None],
         roofs: dict[int, float]) -> dict:
    """Move rooftop-kind rows onto their building's roof, in place. Returns what it did.

    A row whose BIN is not in the buildings table keeps its ground z and its ground ``z_source``: a
    cooling tower on a demolished or never-modelled building is better left where the survey put it
    than lifted to a guess.
    """
    is_roof = np.isin(kind, np.asarray(ROOFTOP_KINDS, dtype=kind.dtype))
    idx = np.nonzero(is_roof)[0]
    lifted = 0
    unmatched: list[int] = []
    rises: list[float] = []
    for i in idx:
        b = _bin_of(attrs[i])
        if b is None:
            unmatched.append(-1)
            continue
        rz = roofs.get(b)
        if rz is None:
            unmatched.append(b)
            continue
        rises.append(float(rz) - float(z[i]))
        z[i] = np.float32(rz)
        z_source[i] = np.int8(Z_SOURCE_ROOF)
        lifted += 1
    out = {"rooftop_rows": int(len(idx)), "lifted": lifted, "unmatched": len(unmatched)}
    if rises:
        r = np.asarray(rises)
        out["rise_m"] = {"min": float(r.min()), "median": float(np.median(r)), "max": float(r.max())}
        out["below_ground"] = int((r < 0).sum())
    return out


def patch_tile(path: Path, roofs: dict[int, float]) -> dict:
    """Rewrite one ``props.parquet`` with its rooftop rows on their roofs."""
    table = pq.read_table(path)
    kind = np.asarray(table.column("kind"), dtype=np.int16)
    if not np.isin(kind, np.asarray(ROOFTOP_KINDS, dtype=np.int16)).any():
        return {"rooftop_rows": 0, "lifted": 0, "unmatched": 0}
    z = np.asarray(table.column("z"), dtype=np.float32).copy()
    z_source = np.asarray(table.column("z_source"), dtype=np.int8).copy()
    attrs = table.column("attrs").to_pylist()
    stats = lift(kind, z, z_source, attrs, roofs)
    if not stats["lifted"]:
        return stats
    cols = {n: table.column(n) for n in table.schema.names}
    cols["z"] = pa.array(z, type=table.schema.field("z").type)
    cols["z_source"] = pa.array(z_source, type=table.schema.field("z_source").type)
    out = pa.table(cols, schema=table.schema.remove_metadata().with_metadata(table.schema.metadata))
    tmp = path.with_suffix(".parquet.tmp")
    pq.write_table(out, tmp, compression="zstd")
    tmp.replace(path)
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles-root", type=Path, default=PROCESSED / "tiles")
    ap.add_argument("--buildings", type=Path, default=BUILDINGS)
    ap.add_argument("--tiles", default="", help="comma-separated tile names; default every tile")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    roofs = roof_heights(args.buildings)
    log.info("roof heights for %d buildings", len(roofs))
    wanted = {t.strip() for t in args.tiles.split(",") if t.strip()} or None
    total = {"tiles": 0, "rooftop_rows": 0, "lifted": 0, "unmatched": 0}
    rises: list[float] = []
    for td in sorted(p for p in args.tiles_root.iterdir() if p.is_dir()):
        if wanted is not None and td.name not in wanted:
            continue
        p = td / "props.parquet"
        if not p.is_file():
            continue
        if args.dry_run:
            table = pq.read_table(p, columns=["kind"])
            kind = np.asarray(table.column("kind"), dtype=np.int16)
            n = int(np.isin(kind, np.asarray(ROOFTOP_KINDS, dtype=np.int16)).sum())
            if n:
                total["tiles"] += 1
                total["rooftop_rows"] += n
            continue
        stats = patch_tile(p, roofs)
        if stats["rooftop_rows"]:
            total["tiles"] += 1
            for k in ("rooftop_rows", "lifted", "unmatched"):
                total[k] += stats[k]
            if "rise_m" in stats:
                rises.append(stats["rise_m"]["median"])
    if rises:
        total["median_of_tile_median_rise_m"] = float(np.median(rises))
    print(json.dumps(total, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
