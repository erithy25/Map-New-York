"""Manifest-driven downloader. Idempotent: existing files are hashed and recorded, not re-fetched.

    python -m nycsim_pipeline.download [--tag TAG] [--id ID ...] [--force]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

from .manifest import record_download, get_download
from .paths import RAW
from .sources import SOURCES, Source, by_tag

log = logging.getLogger("nycsim.download")
CA_BUNDLE = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or True


class DownloadError(RuntimeError):
    pass


def _target(src: Source) -> Path:
    sub = {"socrata_geojson": "nyc_opendata", "socrata_csv": "nyc_opendata", "soda": "nyc_opendata"}.get(src.kind, src.tags[0] if src.tags else "misc")
    if src.id.startswith("gtfs"):
        sub = "gtfs"
    if src.id.startswith("usgs"):
        sub = "usgs"
    if src.id == "doitt_3d_citygml":
        sub = "doitt_3d"
    if src.id == "lion":
        sub = "lion"
    if src.id.startswith("osm"):
        sub = "osm"
    d = RAW / sub
    d.mkdir(parents=True, exist_ok=True)
    return d / src.local_name


def _stream(url: str, dest: Path, attempts: int = 4, timeout: int = 600) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=timeout, verify=CA_BUNDLE, headers={"User-Agent": "NYCSim-pipeline/1.0"}) as r:
                if r.status_code >= 400:
                    raise DownloadError(f"HTTP {r.status_code} for {url}")
                n = 0
                with open(part, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
                            n += len(chunk)
                expected = r.headers.get("Content-Length")
                if expected and int(expected) != n:
                    raise DownloadError(f"short read {n} != {expected} for {url}")
            if n == 0:
                raise DownloadError(f"empty body for {url}")
            os.replace(part, dest)
            return
        except (requests.RequestException, DownloadError) as e:
            last_err = e
            log.warning("attempt %d/%d failed for %s: %s", i + 1, attempts, url, e)
            if part.exists():
                part.unlink()
            time.sleep(2 ** (i + 1))
    raise DownloadError(f"giving up on {url}: {last_err}")


def _soda_paged(url: str, dest: Path, page: int = 50000) -> None:
    """Socrata SODA CSV with automatic $offset paging; header kept once."""
    base = url
    if "$limit" in base:
        # strip caller-provided $limit; we page ourselves
        import re
        base = re.sub(r"[&?]\$limit=\d+", "", base)
    sep = "&" if "?" in base else "?"
    part = dest.with_suffix(".part")
    with open(part, "wb") as out:
        offset = 0
        first = True
        while True:
            u = f"{base}{sep}$limit={page}&$offset={offset}&$order=:id"
            r = requests.get(u, timeout=600, verify=CA_BUNDLE, headers={"User-Agent": "NYCSim-pipeline/1.0"})
            if r.status_code >= 400:
                raise DownloadError(f"HTTP {r.status_code} {r.text[:200]} for {u}")
            lines = r.content.split(b"\n")
            body = [l for l in lines[1:] if l.strip()]
            if first:
                out.write(lines[0] + b"\n")
                first = False
            if not body:
                break
            out.write(b"\n".join(body) + b"\n")
            offset += page
            if len(body) < page:
                break
    os.replace(part, dest)


def download(src: Source, force: bool = False) -> Path:
    dest = _target(src)
    if dest.exists() and not force:
        if get_download(src.id) is None or get_download(src.id).get("bytes") != dest.stat().st_size:
            record_download(src.id, dest, src.url, license=src.license, attribution=src.attribution, notes=src.description)
        log.info("present %s (%d bytes)", src.id, dest.stat().st_size)
        return dest
    log.info("fetching %s -> %s", src.id, dest)
    if src.kind == "soda":
        _soda_paged(src.url, dest)
    else:
        _stream(src.url, dest)
    record_download(src.id, dest, src.url, license=src.license, attribution=src.attribution, notes=src.description)
    log.info("done %s (%d bytes)", src.id, dest.stat().st_size)
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--id", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sel: dict[str, Source] = {}
    for t in a.tag:
        for s in by_tag(t):
            sel[s.id] = s
    for i in a.id:
        if i not in SOURCES:
            log.error("unknown source id %s", i)
            return 2
        sel[i] = SOURCES[i]
    if a.all:
        sel = dict(SOURCES)
    if not sel:
        ap.print_help()
        return 2
    failures = []
    for s in sel.values():
        try:
            download(s, a.force)
        except Exception as e:  # noqa: BLE001 — report every failure, continue with the rest
            log.error("FAILED %s: %s", s.id, e)
            failures.append((s.id, str(e)))
    if failures:
        print(json.dumps({"failures": failures}, indent=1))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
