"""Add the measured deck width and the joined deck profile to ``transit/rail_structures.parquet``.

:func:`nycsim_pipeline.transit.structures.build` computes both during a full transit rebuild;
this runs the same two functions over a table already on disk, so the 986 km of rail structure
written before they existed does not have to be rebuilt from the raw survey to gain them.

    python -m nycsim_pipeline.transit.deck_geometry [--dry-run]

Idempotent: the width depends only on the geometry and the profile only on the geometry and the
measured deck elevations, neither of which this writes.
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
import shapely

from ..paths import PROCESSED
from ..terrain.landscape_grid import LandscapeSampler
from .structures import (DECK_SOURCE_CLASS_MEDIAN, DECK_WIDTH_MEASURED, deck_profile,
                         deck_widths)

log = logging.getLogger("nycsim.transit.deck_geometry")

TABLE = PROCESSED / "transit" / "rail_structures.parquet"
TILES = PROCESSED / "tiles"
SCHEMA = "transit_rail_structures/2"

#: Classes whose deck this rebases on the terrain. The earthworks are the terrain.
BUILT = ("elevated", "viaduct")

#: How far a structure's own ``ground_z`` may sit from the landscape before the deck is rebased.
GROUND_DISAGREEMENT_M = 2.0

#: ``deck_z_source``: where each row's absolute deck elevation ends up coming from.
DECK_Z_SURVEYED = 0        # a planimetric bridge elevation point, kept as measured
DECK_Z_REBASED = 1         # terrain + this row's class-median deck height
DECK_Z_LIFTED = 2          # surveyed, but it put the soffit under the terrain; lifted to clear it

#: Samples taken along each structure when reading the terrain under it.
TERRAIN_SAMPLES = 9


def terrain_under(lines: np.ndarray, sampler: LandscapeSampler) -> np.ndarray:
    """Median landscape elevation along each line, NaN where no tile covers it."""
    out = np.full(len(lines), np.nan)
    for i, g in enumerate(lines):
        try:
            length = float(g.length)
        except Exception:  # noqa: BLE001
            continue
        if length <= 0:
            continue
        s = np.linspace(0.0, length, TERRAIN_SAMPLES)
        pts = np.array([[g.interpolate(v).x, g.interpolate(v).y] for v in s])
        z = sampler.height(pts[:, 0], pts[:, 1])
        if np.isfinite(z).any():
            out[i] = float(np.nanmedian(z))
    return out


def patch(path: Path = TABLE, *, dry_run: bool = False) -> dict:
    table = pq.read_table(path)
    lines = np.asarray(shapely.from_wkb(table.column("geometry").to_pylist()), dtype=object)
    cls = np.asarray(table.column("kind").to_pylist(), dtype=object)
    width, tracks, source = deck_widths(lines, cls)
    deck_z = np.asarray(table.column("deck_z"), dtype=np.float64)
    hsource = np.asarray(table.column("deck_height_source"), dtype=np.int8)
    # deck_heights() filled the class-median fallback into deck_height_m and never into deck_z, so a
    # third of the elevated network had a height above a ground it never got added to. Same fix as
    # in structures.py; applied here too so a table already on disk gains it without a rebuild.
    ground_z = np.asarray(table.column("ground_z"), dtype=np.float64)
    height = np.asarray(table.column("deck_height_m"), dtype=np.float64)
    fill = ~np.isfinite(deck_z) & np.isfinite(ground_z) & np.isfinite(height)
    deck_z = deck_z.copy()
    deck_z[fill] = ground_z[fill] + height[fill]

    # Rebase the deck on the landscape the engine will actually build.
    #
    # ``structures.build`` runs before the per-tile terrain rasters exist -- that is why it samples a
    # ground model of survey points at all -- and that model has no reference points in New Jersey.
    # Measured against the landscape along all 3,986 built structures, 834 of them (21 %) have a
    # ``ground_z`` more than 5 m from the ground under them, two thirds of those west of x = -15 km,
    # and the deck rides that error: whole lines in the Jersey highlands ended up 45-50 m *under* the
    # hillside they cross. A class-median deck height is a height above the ground and nothing more,
    # so where the two grounds disagree the landscape is the one that will be there.
    #
    # A surveyed deck elevation is a measurement of the deck itself and is kept even where it
    # disagrees -- over the East River the DEM is not a river bed and the bridge is right -- unless
    # keeping it would bury the soffit, in which case it is lifted just clear and flagged.
    built = np.isin(cls.astype(str), np.asarray(BUILT))
    terrain = terrain_under(lines, LandscapeSampler(TILES))
    z_source = np.where(hsource == DECK_SOURCE_CLASS_MEDIAN, DECK_Z_REBASED, DECK_Z_SURVEYED).astype(np.int8)
    rebase = (built & np.isfinite(terrain) & np.isfinite(height)
              & (hsource == DECK_SOURCE_CLASS_MEDIAN)
              & (np.abs(ground_z - terrain) > GROUND_DISAGREEMENT_M))
    deck_z[rebase] = terrain[rebase] + height[rebase]
    lift = (built & np.isfinite(terrain) & np.isfinite(height) & ~rebase
            & (deck_z - height < terrain))
    deck_z[lift] = terrain[lift] + height[lift]
    z_source[lift] = DECK_Z_LIFTED
    z_source[~built] = DECK_Z_SURVEYED
    # Keep the flag across re-runs. A lifted deck sits exactly on the terrain plus its height, so the
    # test that lifted it is false the second time and the row would go back to reading "surveyed" --
    # which would be the record losing the one thing it is for.
    if "deck_z_source" in table.schema.names:
        was = np.asarray(table.column("deck_z_source"), dtype=np.int8)
        z_source[built & (was == DECK_Z_LIFTED) & (z_source == DECK_Z_SURVEYED)] = DECK_Z_LIFTED
    z_start, z_end, joints = deck_profile(lines, cls, deck_z, hsource)

    measured = source == DECK_WIDTH_MEASURED
    have = np.isfinite(width)
    stats = {
        "rows": int(table.num_rows),
        "with_a_width": int(have.sum()),
        "measured_from_parallel_tracks": int((measured & have).sum()),
        "single_track": int((~measured & have).sum()),
        "deck_z_filled_from_class_median_height": int(fill.sum()),
        "deck_z_rebased_on_the_landscape": int(rebase.sum()),
        "deck_z_lifted_clear_of_the_landscape": int(lift.sum()),
        "no_terrain_under_them": int((built & ~np.isfinite(terrain)).sum()),
        "width_m": {
            "min": float(np.nanmin(width)) if have.any() else None,
            "median": float(np.nanmedian(width)) if have.any() else None,
            "p90": float(np.nanpercentile(width[have], 90)) if have.any() else None,
            "max": float(np.nanmax(width)) if have.any() else None,
        },
        "track_count": {int(k): int(v) for k, v in zip(*np.unique(tracks[have], return_counts=True))} if have.any() else {},
    }
    prof = np.isfinite(z_start) & np.isfinite(z_end)
    if prof.any():
        L = np.asarray(table.column("length_m"), dtype=np.float64)[prof]
        grade = np.abs(z_end[prof] - z_start[prof]) / np.maximum(L, 1.0)
        before = np.abs(deck_z[prof] - (z_start[prof] + z_end[prof]) / 2.0)
        stats["profile"] = {
            "rows": int(prof.sum()),
            "joints": int(np.sum(joints[prof] > 1)),
            "grade": {"median": float(np.median(grade)), "p99": float(np.percentile(grade, 99)),
                      "max": float(grade.max()),
                      "over_4_pct": int((grade > 0.0401).sum())},
            "moved_from_segment_deck_z_m": {"median": float(np.median(before)),
                                            "p95": float(np.percentile(before, 95)),
                                            "max": float(before.max())},
        }
    if dry_run:
        return stats

    cols = {n: table.column(n) for n in table.schema.names}
    cols["deck_width_m"] = pa.array(width.astype(np.float32))
    cols["track_count"] = pa.array(tracks)
    cols["deck_width_source"] = pa.array(source)
    cols["deck_z"] = pa.array(deck_z.astype(np.float32))
    cols["deck_z_source"] = pa.array(z_source)
    cols["terrain_z"] = pa.array(terrain.astype(np.float32))
    cols["deck_z_start"] = pa.array(z_start.astype(np.float32))
    cols["deck_z_end"] = pa.array(z_end.astype(np.float32))
    cols["deck_joints"] = pa.array(joints)
    meta = dict(table.schema.metadata or {})
    meta[b"nycsim.schema"] = SCHEMA.encode()
    out = pa.table(cols).replace_schema_metadata(meta)
    tmp = path.with_suffix(".parquet.tmp")
    pq.write_table(out, tmp, compression="zstd")
    tmp.replace(path)
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", type=Path, default=TABLE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(json.dumps(patch(args.table, dry_run=args.dry_run), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
