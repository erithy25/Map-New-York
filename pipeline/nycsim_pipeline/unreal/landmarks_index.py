"""``data/processed/landmarks/landmarks.json``: where each landmark model stands.

``pipeline/nycsim_pipeline/unreal/manifest.py`` has looked for this file since Stage 12b and it has
never existed, so ``build_levels.py`` had nothing to place landmarks from -- and, having nothing, it
never grew a ``place_landmarks`` at all.  The result is that 93 landmark models totalling 927 MB
import into Unreal as ``SM_*`` assets that no actor ever spawns: the Empire State Building, the
Chrysler Building, Grand Central, the World Trade Center site, the Statue of Liberty, all present in
the content browser and none of them in the world.

The index is small on purpose -- UE 5.4's embedded Python has no pyarrow, which is why this module
exists at all rather than the editor reading the catalogue directly.

**There is no rotation.**  ``blender/landmarks/common.py`` states it in the exported extras of every
model: *"model axes parallel to NYC_TM (x east, y north, z up before glTF Y-up conversion); origin_tm
is the NYC_TM position of the model origin (ground); no rotation to apply on import"*.  ``finish()``
builds each landmark in a local frame aligned to its own footprint's principal axis and then rotates
it back to NYC_TM before export, so the orientation is already baked into the geometry.  The
catalogue's ``heading_deg`` is the compass heading of that principal axis -- provenance, a record of
how the model was built, not an instruction.  Applying it as an actor rotation would turn every
landmark in the city by its own facade angle.  The verification renderer, which is the only thing
that has ever placed these models, translates and does not rotate; so does the level builder.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from ..crs import TILE_SIZE_M
from ..manifest import git_commit
from ..paths import BLENDER_OUT, PROCESSED

log = logging.getLogger("nycsim.unreal.landmarks_index")

SCHEMA = "landmarks_index/1"


def _tile_of(x: float, y: float) -> str:
    import math

    return f"t_{int(math.floor(x / TILE_SIZE_M))}_{int(math.floor(y / TILE_SIZE_M))}"


def build_index(blender_out: Path = BLENDER_OUT, processed: Path = PROCESSED) -> dict[str, Any]:
    """Read ``blender_out/landmarks/catalog/*.json`` and return the index document."""
    catalog_dir = Path(blender_out) / "landmarks" / "catalog"
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    if catalog_dir.is_dir():
        for path in sorted(catalog_dir.glob("*.json")):
            try:
                entry = json.loads(path.read_text())
            except Exception as exc:
                skipped.append({"id": path.stem, "reason": f"unreadable: {exc}"})
                continue
            origin = entry.get("origin_tm")
            if not (isinstance(origin, (list, tuple)) and len(origin) == 3):
                skipped.append({"id": path.stem, "reason": "no origin_tm"})
                continue
            glb = entry.get("glb")
            if not glb and isinstance(entry.get("lods"), dict):
                glb = (entry["lods"].get("lod0") or {}).get("path")
            if not glb:
                skipped.append({"id": path.stem, "reason": "no glb path"})
                continue
            x, y, z = (float(v) for v in origin)
            bounds = entry.get("bounds_local_m") or {}
            rows.append({
                "id": str(entry.get("id", path.stem)),
                "name": str(entry.get("name", path.stem)),
                # The asset stem the manifest's landmark rule derives its content path from.
                "stem": Path(str(glb)).stem,
                "origin_tm": [round(x, 4), round(y, 4), round(z, 4)],
                "tile": _tile_of(x, y),
                "bounds_local_m": {"min": bounds.get("min"), "max": bounds.get("max")}
                                  if bounds else None,
                "height_m": entry.get("height_m"),
                # Recorded so a reader can see it and not use it; see this module's docstring.
                "heading_deg_not_a_rotation": entry.get("heading_deg"),
            })
    return {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": git_commit(),
        "generator": "pipeline/nycsim_pipeline/unreal/landmarks_index.py",
        "placement": ("translate the model to origin_tm; apply no rotation. The model axes are "
                      "already parallel to NYC_TM (blender/landmarks/common.py). heading_deg is the "
                      "compass heading of the footprint's principal axis, recorded as provenance."),
        "count": len(rows),
        "skipped": skipped,
        "landmarks": rows,
    }


def write_index(blender_out: Path = BLENDER_OUT, processed: Path = PROCESSED) -> Path | None:
    """Write the index, or return ``None`` when there is no catalogue to write one from.

    An index with zero landmarks is not an index; writing one anyway would make every consumer -- the
    manifest included -- report a file it should not have, which is how a checkout with no landmarks
    built ends up listing a landmark asset.
    """
    doc = build_index(blender_out, processed)
    out = Path(processed) / "landmarks" / "landmarks.json"
    if doc["count"] == 0:
        log.info("no landmark catalogue under %s; no index written", Path(blender_out) / "landmarks")
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    log.info("landmarks index: %d entries -> %s", doc["count"], out)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender-out", type=Path, default=BLENDER_OUT)
    ap.add_argument("--processed", type=Path, default=PROCESSED)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    out = write_index(args.blender_out, args.processed)
    if out is None:
        print("no landmark catalogue found; no index written")
        return 1
    doc = json.loads(out.read_text())
    print(f"{doc['count']} landmarks, {len(doc['skipped'])} skipped -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
