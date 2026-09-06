"""Environment bootstrap for every vehicle script.

Puts ``blender/common`` (foundation ``nycsim_bpy``) and ``pipeline`` (manifest) on ``sys.path``, defines the
output directories of this lane and provides the optional hook to the shared texture library
``blender/common/textures.py`` (written by another agent; used when present, Principled fallbacks otherwise).
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
VEHICLES_DIR = HERE.parents[1]  # blender/vehicles
BLENDER_DIR = VEHICLES_DIR.parent  # blender
REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", BLENDER_DIR.parent))
for _p in (BLENDER_DIR / "common", REPO_ROOT / "pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import bpy  # noqa: E402
import nycsim_bpy as nb  # noqa: E402

OUT_DIR = nb.BLENDER_OUT / "vehicles"
TEX_DIR = OUT_DIR / "textures"
CATALOG_DIR = OUT_DIR / "catalog"
VERIFY_DIR = REPO_ROOT / "docs" / "verification" / "vehicles"

log = logging.getLogger("nycsim.vehicles")


def setup_logging(level: int = logging.INFO) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    logging.getLogger().setLevel(level)


def ensure_dirs() -> None:
    for d in (OUT_DIR, TEX_DIR, CATALOG_DIR, VERIFY_DIR):
        d.mkdir(parents=True, exist_ok=True)


def finish(code: int = 0) -> None:
    """Flush and hard-exit. The ``bpy`` module was observed once to hang at interpreter teardown after a glTF
    export with morph targets (blender/vehicles scratch probe, 2026-09-05); every output is written explicitly
    before this call, so skipping Python finalisers loses nothing."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


class Timer:
    """Wall-clock section timer used for the build-timings report."""

    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.marks: dict[str, float] = {}

    def mark(self, name: str) -> float:
        now = time.perf_counter()
        self.marks[name] = round(now - self.t0, 3)
        self.t0 = now
        return self.marks[name]

    def total(self) -> float:
        return round(sum(self.marks.values()), 3)


# ------------------------------------------------------------------ shared texture library (optional)
_TEXSET_CACHE: dict[tuple[str, str], dict[str, str] | None] = {}


def shared_texture_set(name: str, resolution: str = "2K") -> dict[str, str] | None:
    """Return ``{'color': path, 'roughness': path, 'normal': path, ...}`` from ``blender/common/textures.py``
    (``get_texture_set(name, resolution)``) if that module exists and returns usable files, else ``None``.

    The other agent's return type is not fixed yet: a ``dict`` of kind -> path, an object with those attributes,
    or a ``dict`` with a ``maps`` sub-dict are all accepted. Anything else (or a missing file) logs a warning and
    falls back to Principled values documented in ``materials.py``."""
    key = (name, resolution)
    if key in _TEXSET_CACHE:
        return _TEXSET_CACHE[key]
    result: dict[str, str] | None = None
    try:
        import textures as shared  # type: ignore  # blender/common/textures.py
    except ImportError:
        _TEXSET_CACHE[key] = None
        return None
    getter = getattr(shared, "get_texture_set", None)
    if getter is None:
        log.warning("blender/common/textures.py present but has no get_texture_set(); using Principled fallbacks")
        _TEXSET_CACHE[key] = None
        return None
    try:
        raw: Any = getter(name, resolution=resolution)
    except Exception as exc:  # the shared module is outside this lane; never let it break a build
        log.warning("get_texture_set(%r, %r) failed: %s; using Principled fallback", name, resolution, exc)
        _TEXSET_CACHE[key] = None
        return None
    candidate: dict[str, Any] = {}
    if isinstance(raw, dict):
        candidate = dict(raw.get("maps", raw))
    elif raw is not None:
        for kind in ("color", "roughness", "normal", "metallic", "ao", "displacement"):
            val = getattr(raw, kind, None)
            if val:
                candidate[kind] = val
    cleaned: dict[str, str] = {}
    for kind, val in candidate.items():
        if kind in ("color", "roughness", "normal", "metallic", "ao") and val and Path(str(val)).exists():
            cleaned[kind] = str(val)
    if "color" not in cleaned and "normal" not in cleaned and "roughness" not in cleaned:
        log.warning("shared texture set %r/%s has no usable maps (%s); using Principled fallback", name, resolution, sorted(candidate))
        result = None
    else:
        result = cleaned
        log.info("using shared texture set %r/%s: %s", name, resolution, sorted(cleaned))
    _TEXSET_CACHE[key] = result
    return result
