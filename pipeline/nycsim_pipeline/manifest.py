"""Download/processed manifests with SHA-256 (docs/DATA_CONTRACTS.md preamble)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .paths import MANIFEST, REPO_ROOT

DOWNLOADS = MANIFEST / "downloads.json"
PROCESSED_MANIFEST = MANIFEST / "processed.json"


def sha256_of(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "uncommitted"


def _load(path: Path) -> dict[str, Any]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"schema_version": 1, "entries": {}}


def _save(path: Path, doc: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def record_download(source_id: str, path: Path, url: str, *, license: str, attribution: str, notes: str = "", extra: dict | None = None) -> dict:
    doc = _load(DOWNLOADS)
    entry = {
        "source_id": source_id,
        "url": url,
        "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(path.stat().st_mtime)),
        "license": license,
        "attribution": attribution,
        "notes": notes,
    }
    if extra:
        entry.update(extra)
    doc["entries"][source_id] = entry
    _save(DOWNLOADS, doc)
    return entry


def get_download(source_id: str) -> dict | None:
    return _load(DOWNLOADS)["entries"].get(source_id)


def record_processed(artifact_id: str, path: Path, *, stage: str, sources: list[str], rows: int | None = None, schema: str = "", extra: dict | None = None) -> dict:
    doc = _load(PROCESSED_MANIFEST)
    entry = {
        "artifact_id": artifact_id,
        "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path) if path.stat().st_size < (2 << 30) else "skipped(>2GiB)",
        "produced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stage": stage,
        "sources": sources,
        "rows": rows,
        "schema": schema,
        "git_commit": git_commit(),
    }
    if extra:
        entry.update(extra)
    doc["entries"][artifact_id] = entry
    _save(PROCESSED_MANIFEST, doc)
    return entry
