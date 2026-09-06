"""Retrying wrapper around ``nycsim_pipeline.manifest.record_processed``.

``manifest._save`` writes ``data/manifest/processed.tmp`` and renames it onto ``processed.json``. The temp
file name is fixed, so two agents recording an artefact at the same moment race: one process's rename takes
the file the other is still writing, and the loser raises ``FileNotFoundError`` *after* its artefact is
already on disk. Observed on 2026-09-06 while the terrain and buildings stages ran concurrently.

The stages in this lane therefore record through ``record_processed`` below, which retries the manifest
write with a short randomised back-off and, if it still cannot get through, logs and returns ``None``
instead of destroying a finished pass — the artefact itself is complete either way and a later run records
it. The proper fix belongs to the foundation (``manifest._save`` should write ``processed.<pid>.tmp`` or
take an ``fcntl.flock``); it is reported to the orchestrator, not patched here, because ``manifest.py`` is
shared foundation code.
"""
from __future__ import annotations

import logging
import random
import time
from pathlib import Path

from .. import manifest

log = logging.getLogger("nycsim.terrain.manifest")

ATTEMPTS = 6


def record_processed(artifact_id: str, path: Path, **kw) -> dict | None:
    last: Exception | None = None
    for i in range(ATTEMPTS):
        try:
            return manifest.record_processed(artifact_id, path, **kw)
        except (FileNotFoundError, OSError, ValueError) as e:
            last = e
            time.sleep(0.2 * (i + 1) + random.random() * 0.3)
    log.warning("could not record %s in the processed manifest after %d attempts (%s); artefact is on disk at %s",
                artifact_id, ATTEMPTS, last, path)
    return None
