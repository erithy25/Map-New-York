"""Output locations and manifest hooks for the live services.

Uses the pipeline foundation (``nycsim_pipeline.paths`` / ``manifest``) when importable so every path
and manifest entry agrees with the rest of the repository; falls back to the same relative layout if the
pipeline package is not on the path (e.g. the service deployed alone next to the engine).
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("nycsim.live.paths")

REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
_pipeline_dir = REPO_ROOT / "pipeline"
if _pipeline_dir.is_dir() and str(_pipeline_dir) not in sys.path:
    sys.path.insert(0, str(_pipeline_dir))

try:
    from nycsim_pipeline import manifest as _manifest  # type: ignore
    from nycsim_pipeline.paths import PROCESSED as _PROCESSED  # type: ignore

    PROCESSED = Path(_PROCESSED)
    HAVE_PIPELINE = True
except Exception as e:  # pragma: no cover - only when deployed without the pipeline package
    _manifest = None
    PROCESSED = Path(os.environ.get("NYCSIM_DATA_DIR", REPO_ROOT / "data")) / "processed"
    HAVE_PIPELINE = False
    log.warning("nycsim_pipeline not importable (%s); using fallback paths under %s", e, PROCESSED)

LIVE_DIR = Path(os.environ.get("NYCSIM_LIVE_DIR", PROCESSED / "live"))
WEATHER_JSON = LIVE_DIR / "weather.json"
ESB_LIGHTS_JSON = LIVE_DIR / "esb_lights.json"
TIDES_JSON = LIVE_DIR / "tides.json"
OVERLAY_TXT = LIVE_DIR / "overlay.txt"
SNOW_STATE_JSON = LIVE_DIR / "snow_state.json"
WORLD_STATE_JSON = LIVE_DIR / "world_state.json"


def write_json_atomic(path: Path, doc: dict[str, Any]) -> None:
    """Write JSON via a temp file + rename so readers never see a partial snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=False, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log.warning("unreadable JSON %s: %s", path, e)
        return None


def record_snapshot(artifact_id: str, path: Path, sources: list[str], schema: str, extra: dict | None = None) -> dict | None:
    """Record a live snapshot in data/manifest/processed.json (stage 'live'). Used for verification runs
    (``--once``); the 60 s polling loop does not spam the manifest."""
    if _manifest is None:
        return None
    try:
        return _manifest.record_processed(artifact_id, path, stage="live", sources=sources, rows=1, schema=schema, extra=extra)
    except Exception as e:  # noqa: BLE001 - manifest problems must never take the live service down
        log.warning("manifest record failed for %s: %s", artifact_id, e)
        return None


def utc_iso(unix_s: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(unix_s))
