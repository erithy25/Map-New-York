"""Fetch the extra traffic-stage inputs through the foundation downloader (idempotent, manifest-recorded).

    python -m nycsim_pipeline.traffic.fetch [--force]

The TLC high-volume FHV file (~0.5 GB/month) is not downloaded whole: :class:`HttpRangeFile` exposes
the remote parquet as a seekable file, pyarrow reads only the footer and the column chunks needed
(pickup/dropoff timestamps, zones, distance — ~30 % of the bytes), and the subset is written locally
and recorded in ``downloads.json`` with ``partial=true`` and the column list.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from ..download import CA_BUNDLE, DownloadError, _target, download
from ..manifest import get_download, record_download
from ..sources import Source
from .sources_extra import EXTRA_SOURCES

log = logging.getLogger("nycsim.traffic.fetch")

FHVHV_COLUMNS = ("pickup_datetime", "dropoff_datetime", "PULocationID", "DOLocationID", "trip_miles")
_UA = {"User-Agent": "NYCSim-pipeline/1.0"}


class HttpRangeFile:
    """Minimal seekable read-only file over HTTP ``Range`` requests (for ``pyarrow.PythonFile``)."""

    def __init__(self, url: str, *, timeout: int = 180, attempts: int = 5) -> None:
        self.url = url
        self.timeout = timeout
        self.attempts = attempts
        self.session = requests.Session()
        r = self.session.head(url, timeout=timeout, verify=CA_BUNDLE, headers=_UA, allow_redirects=True)
        if r.status_code >= 400:
            raise DownloadError(f"HTTP {r.status_code} for HEAD {url}")
        if "Content-Length" not in r.headers:
            raise DownloadError(f"no Content-Length for {url}")
        self._size = int(r.headers["Content-Length"])
        self._pos = 0
        self.bytes_read = 0
        self.requests_made = 0

    # -- file protocol -------------------------------------------------------------------------
    def size(self) -> int:
        return self._size

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            new = offset
        elif whence == 1:
            new = self._pos + offset
        elif whence == 2:
            new = self._size + offset
        else:
            raise ValueError(f"bad whence {whence}")
        if new < 0:
            raise ValueError("negative seek")
        self._pos = min(new, self._size)
        return self._pos

    def read(self, nbytes: int | None = -1) -> bytes:
        if nbytes is None or nbytes < 0:
            nbytes = self._size - self._pos
        if nbytes == 0 or self._pos >= self._size:
            return b""
        end = min(self._size, self._pos + nbytes) - 1
        hdr = dict(_UA, Range=f"bytes={self._pos}-{end}")
        last: Exception | None = None
        for i in range(self.attempts):
            try:
                r = self.session.get(self.url, headers=hdr, timeout=self.timeout, verify=CA_BUNDLE)
                self.requests_made += 1
                if r.status_code != 206:
                    raise DownloadError(f"HTTP {r.status_code} for range {hdr['Range']} of {self.url}")
                body = r.content
                if len(body) != end - self._pos + 1:
                    raise DownloadError(f"short range body {len(body)} != {end - self._pos + 1}")
                self._pos += len(body)
                self.bytes_read += len(body)
                return body
            except (requests.RequestException, DownloadError) as e:  # retry with back-off
                last = e
                log.warning("range read attempt %d/%d failed: %s", i + 1, self.attempts, e)
                time.sleep(min(30, 2 ** (i + 1)))
        raise DownloadError(f"giving up on range read of {self.url}: {last}")

    def close(self) -> None:
        self.session.close()

    @property
    def closed(self) -> bool:
        return False

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def flush(self) -> None:
        return None


def fetch_parquet_columns(src: Source, columns: tuple[str, ...], *, force: bool = False) -> Path:
    """Read ``columns`` of the remote parquet ``src`` by range requests and store them locally."""
    dest = _target(src)
    if dest.exists() and not force:
        if get_download(src.id) is None or get_download(src.id).get("bytes") != dest.stat().st_size:
            record_download(src.id, dest, src.url, license=src.license, attribution=src.attribution, notes=src.description,
                            extra={"partial": True, "columns": list(columns)})
        log.info("present %s (%d bytes)", src.id, dest.stat().st_size)
        return dest
    log.info("range-reading %s columns %s -> %s", src.id, columns, dest)
    rf = HttpRangeFile(src.url)
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        pf = pq.ParquetFile(pa.PythonFile(rf, mode="r"))
        missing = [c for c in columns if c not in pf.schema_arrow.names]
        if missing:
            raise DownloadError(f"{src.id}: columns {missing} not in remote schema {pf.schema_arrow.names}")
        writer: pq.ParquetWriter | None = None
        rows = 0
        for rg in range(pf.metadata.num_row_groups):
            tbl = pf.read_row_group(rg, columns=list(columns))
            if writer is None:
                writer = pq.ParquetWriter(part, tbl.schema, compression="zstd")
            writer.write_table(tbl)
            rows += tbl.num_rows
            log.info("  row group %d/%d: %d rows, %.1f MB fetched so far", rg + 1, pf.metadata.num_row_groups, rows, rf.bytes_read / 1e6)
        if writer is None:
            raise DownloadError(f"{src.id}: remote parquet has no row groups")
        writer.close()
        if rows != pf.metadata.num_rows:
            raise DownloadError(f"{src.id}: row count mismatch {rows} != {pf.metadata.num_rows}")
        os.replace(part, dest)
        record_download(src.id, dest, src.url, license=src.license, attribution=src.attribution, notes=src.description,
                        extra={"partial": True, "columns": list(columns), "remote_bytes": rf.size(), "remote_rows": pf.metadata.num_rows,
                               "bytes_fetched": rf.bytes_read})
        log.info("done %s: %d rows, %.1f of %.1f MB fetched", src.id, rows, rf.bytes_read / 1e6, rf.size() / 1e6)
        return dest
    finally:
        rf.close()
        if part.exists():
            part.unlink()


def fetch_all(*, force: bool = False, skip: tuple[str, ...] = ()) -> dict[str, Path]:
    """Fetch every extra source; returns id -> local path. Failures are logged and re-raised at the end."""
    out: dict[str, Path] = {}
    failures: list[tuple[str, str]] = []
    for sid, src in EXTRA_SOURCES.items():
        if sid in skip:
            continue
        try:
            if sid.startswith("tlc_fhvhv"):
                out[sid] = fetch_parquet_columns(src, FHVHV_COLUMNS, force=force)
            else:
                out[sid] = download(src, force=force)
        except Exception as e:  # noqa: BLE001 — collect every failure, then raise
            log.error("FAILED %s: %s", sid, e)
            failures.append((sid, str(e)))
    if failures:
        raise DownloadError("; ".join(f"{s}: {m}" for s, m in failures))
    return out


def local_path(source_id: str) -> Path:
    """Local path of an extra source (whether or not it has been fetched yet)."""
    return _target(EXTRA_SOURCES[source_id])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip", action="append", default=[])
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        paths = fetch_all(force=a.force, skip=tuple(a.skip))
    except DownloadError as e:
        log.error("%s", e)
        return 1
    for k, p in paths.items():
        print(f"{k}: {p} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
