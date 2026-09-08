"""Repoint ``roof_mesh_ref`` at the file that holds the roof geometry.

DATA_CONTRACTS §5 specified ``roof_mesh_ref = "t_{tx}_{ty}/roofs.glb#bin_{bin}"`` and a later Blender
stage that would turn the CityGML LOD2 solids into ``tiles/{tile}/roofs.glb``. That stage was never
written, for a reason that only became clear once the solids were opened: **every CityGML roof
triangle is horizontal**. The NYC 3-D Building Model is flat multi-level massing, not roof pitch, so
a ``roofs.glb`` would carry level outlines and nothing else -- and ``blender/buildings/roofsteps.py``
already recovers exactly those outlines from the same triangles and builds them into the tile shells
(Stage 16). The geometry is in the world; the file is not, and never should be.

What was left was 1,033,416 buildings -- 95.42 % of the city -- carrying a reference to a file that
does not exist and will not be written. That is a placeholder in the data, so this removes it: the
reference now names the parquet shard that really holds the building's LOD2 triangles, which is what
``roofsteps.py`` opens, so a reader following it arrives at the geometry instead of at nothing.

    python -m nycsim_pipeline.buildings.roof_ref [--dry-run]

Idempotent: a reference already pointing at a shard is left alone.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from ..paths import PROCESSED

log = logging.getLogger("nycsim.buildings.roof_ref")

BUILDINGS = PROCESSED / "buildings" / "buildings_base.parquet"
CITYGML = PROCESSED / "buildings" / "citygml"

#: The reference the contract used to specify, kept here so the repair can recognise what it fixes.
OLD_REF = re.compile(r"^t_-?\d+_-?\d+/roofs\.glb#bin_(?P<bin>\d+)$")

#: The reference it writes instead, relative to ``data/processed``.
NEW_REF = "buildings/citygml/{shard}#bin_{bin}"


def shard_of_bin(citygml: Path = CITYGML) -> dict[int, str]:
    """``bin -> shard file name`` over the CityGML LOD2 shards."""
    out: dict[int, str] = {}
    for p in sorted(Path(citygml).glob("da*.parquet")):
        try:
            bins = pq.read_table(p, columns=["bin"]).column("bin").to_numpy(zero_copy_only=False)
        except (OSError, KeyError) as exc:
            log.warning("%s unreadable: %s", p.name, exc)
            continue
        for b in bins.tolist():
            out[int(b)] = p.name
    return out


def repair(buildings: Path = BUILDINGS, citygml: Path = CITYGML, *, dry_run: bool = False) -> dict:
    table = pq.read_table(buildings)
    refs = table.column("roof_mesh_ref").to_pylist()
    shard = shard_of_bin(citygml)
    log.info("citygml shards index %d bins", len(shard))

    out: list[str] = []
    stats = {"rows": len(refs), "empty": 0, "already_pointing_at_a_shard": 0,
             "repointed": 0, "no_shard_for_the_bin": 0, "unrecognised": 0}
    for r in refs:
        if not r:
            stats["empty"] += 1
            out.append("")
            continue
        if r.startswith("buildings/citygml/"):
            stats["already_pointing_at_a_shard"] += 1
            out.append(r)
            continue
        m = OLD_REF.match(r)
        if not m:
            stats["unrecognised"] += 1
            out.append(r)
            continue
        b = int(m.group("bin"))
        s = shard.get(b)
        if s is None:
            # A row that claims a CityGML solid whose shard does not hold it: the reference was
            # wrong in a second way and there is nothing true to point it at.
            stats["no_shard_for_the_bin"] += 1
            out.append("")
            continue
        stats["repointed"] += 1
        out.append(NEW_REF.format(shard=s, bin=b))

    if dry_run:
        return stats
    cols = {n: table.column(n) for n in table.schema.names}
    cols["roof_mesh_ref"] = pa.array(out, type=pa.string())
    new = pa.table(cols, schema=table.schema)
    tmp = buildings.with_suffix(".parquet.tmp")
    pq.write_table(new, tmp, compression="zstd")
    tmp.replace(buildings)
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--buildings", type=Path, default=BUILDINGS)
    ap.add_argument("--citygml", type=Path, default=CITYGML)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(json.dumps(repair(args.buildings, args.citygml, dry_run=args.dry_run), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
