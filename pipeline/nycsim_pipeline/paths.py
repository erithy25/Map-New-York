"""Canonical repository paths. Every stage imports from here; nothing is hard-coded elsewhere."""
from __future__ import annotations
import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
DATA = Path(os.environ.get("NYCSIM_DATA_DIR", REPO_ROOT / "data"))
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
MANIFEST = DATA / "manifest"
BLENDER_OUT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO_ROOT / "blender_out"))
DOCS = REPO_ROOT / "docs"
VERIFICATION = DOCS / "verification"

for _p in (RAW, PROCESSED, MANIFEST):
    _p.mkdir(parents=True, exist_ok=True)


def tile_dir(tile: str, create: bool = True) -> Path:
    p = PROCESSED / "tiles" / tile
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p
