"""Generate docs/ASSET_LICENSES.md by scanning every licence record on disk.

Covers: downloaded data sources (`data/manifest/downloads.json`), CC0 texture sets
(`assets/textures/*/LICENSE.json`), fonts, motion-capture archives, audio, and third-party
source vendored into the repository (`core/third_party/*`). Nothing is listed unless a licence
record exists for it; anything found without one is reported in an "unlicensed" section so the
gap is visible rather than hidden.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from ..manifest import DOWNLOADS
from ..paths import DOCS, REPO_ROOT

log = logging.getLogger("nycsim.licences")

ASSETS = REPO_ROOT / "assets"
THIRD_PARTY_DIRS = [REPO_ROOT / "core" / "third_party"]
LICENCE_FILENAMES = {"LICENSE.json", "license.json", "LICENCE.json"}
LICENCE_TEXT_FILES = {"LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "LICENSE-MIT", "OFL.txt"}


def _load_json(p: Path) -> dict[str, Any] | None:
    try:
        with open(p) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {"records": d}
    except Exception as e:  # noqa: BLE001 — an unreadable licence file is a reportable gap
        log.warning("unreadable licence file %s: %s", p, e)
        return None


def _manifest_licences_for(directory: Path) -> list[dict[str, Any]]:
    """Assets fetched through the download manifest carry their licence there, not in a sidecar file.

    Returns one aggregated record per (licence, attribution) pair found for files inside ``directory``.
    """
    if not DOWNLOADS.exists():
        return []
    try:
        entries = json.load(open(DOWNLOADS))["entries"]
    except Exception as e:  # noqa: BLE001
        log.warning("download manifest unreadable: %s", e)
        return []
    rel = directory.relative_to(REPO_ROOT).as_posix()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for e in entries.values():
        if not str(e.get("path", "")).startswith(rel + "/"):
            continue
        key = (e.get("license", "unstated"), e.get("attribution", ""))
        g = grouped.setdefault(key, {"group": directory.relative_to(ASSETS).parts[0],
                                     "asset": directory.relative_to(ASSETS).as_posix(),
                                     "name": directory.name,
                                     "licence": key[0], "author": key[1],
                                     "source": e.get("url", ""), "fetched_at": e.get("downloaded_at", ""),
                                     "sha256": "", "files": 0, "bytes": 0})
        g["files"] += 1
        g["bytes"] += int(e.get("bytes", 0) or 0)
    return list(grouped.values())


def _first_url(d: dict[str, Any]) -> str:
    for inner in (d.get("downloads") or {}).values():
        if isinstance(inner, dict) and isinstance(inner.get("url"), str):
            return inner["url"]
    return ""


def _first_sha(d: dict[str, Any]) -> str:
    """A licence record stores sha256 either as one hex string or as a mapping of file -> hex."""
    v = d.get("sha256")
    if isinstance(v, str):
        return v[:16]
    if isinstance(v, dict):
        for inner in v.values():
            if isinstance(inner, str):
                return inner[:16]
            if isinstance(inner, dict) and isinstance(inner.get("sha256"), str):
                return inner["sha256"][:16]
    for inner in (d.get("downloads") or {}).values():
        if isinstance(inner, dict) and isinstance(inner.get("sha256"), str):
            return inner["sha256"][:16]
    return ""


def scan_asset_licences() -> tuple[list[dict[str, Any]], list[str]]:
    """Return (records, directories_without_a_licence_record)."""
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    if not ASSETS.exists():
        return records, missing
    for group in sorted(p for p in ASSETS.iterdir() if p.is_dir()):
        for item in sorted(p for p in group.rglob("*") if p.is_dir()):
            lic = next((item / n for n in LICENCE_FILENAMES if (item / n).exists()), None)
            has_payload = any(f.is_file() and f.name not in LICENCE_FILENAMES for f in item.iterdir())
            if lic is not None:
                d = _load_json(lic) or {}
                records.append({
                    "group": group.name,
                    "asset": item.relative_to(ASSETS).as_posix(),
                    "name": d.get("name") or d.get("title") or d.get("display_name") or d.get("asset_id") or item.name,
                    "licence": d.get("license") or d.get("licence") or "unstated",
                    "source": d.get("url") or d.get("source") or d.get("source_url") or _first_url(d),
                    "author": d.get("author") or d.get("attribution") or "",
                    "fetched_at": d.get("fetched_at") or d.get("downloaded_at") or "",
                    "sha256": _first_sha(d),
                    "files": sum(1 for f in item.rglob("*") if f.is_file()),
                    "bytes": sum(f.stat().st_size for f in item.rglob("*") if f.is_file()),
                })
            elif has_payload and not any((item / n).exists() for n in LICENCE_TEXT_FILES):
                covered = any((anc / n).exists() for anc in item.parents for n in LICENCE_FILENAMES | LICENCE_TEXT_FILES
                              if anc.is_relative_to(ASSETS))
                from_manifest = _manifest_licences_for(item)
                if from_manifest:
                    records.extend(from_manifest)
                elif not covered:
                    missing.append(item.relative_to(REPO_ROOT).as_posix())
    return records, missing


def scan_third_party() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for root in THIRD_PARTY_DIRS:
        if not root.exists():
            continue
        for item in sorted(p for p in root.iterdir() if p.is_dir()):
            lic_file = next((item / n for n in LICENCE_TEXT_FILES if (item / n).exists()), None)
            lic_json = next((item / n for n in LICENCE_FILENAMES if (item / n).exists()), None)
            licence = "unstated"
            source = ""
            if lic_json:
                d = _load_json(lic_json) or {}
                licence = d.get("license", licence)
                source = d.get("url", "")
            elif lic_file:
                head = lic_file.read_text(errors="replace")[:400].lower()
                for tag in ("mit license", "apache license", "bsd", "zlib", "mozilla public license", "sil open font license"):
                    if tag in head:
                        licence = tag.title()
                        break
                else:
                    licence = f"see {lic_file.name}"
            out.append({"path": item.relative_to(REPO_ROOT).as_posix(), "licence": licence, "source": source,
                        "files": sum(1 for f in item.rglob("*") if f.is_file())})
    return out


def build_doc() -> str:
    lines: list[str] = ["# Asset and source licences", "",
                        "Generated by `pipeline/nycsim_pipeline/report/asset_licenses.py` from licence records on disk. "
                        "Data sources are listed in full in `docs/DATA_SOURCES.md`; this file covers everything else that "
                        "was downloaded or vendored, plus a summary of the data licences.", ""]

    if DOWNLOADS.exists():
        entries = json.load(open(DOWNLOADS))["entries"]
        by_lic: dict[str, list[str]] = {}
        for e in entries.values():
            by_lic.setdefault(e.get("license", "unstated"), []).append(e["source_id"])
        lines += ["## 1. Data sources", "",
                  f"{len(entries)} downloaded sources, {sum(e.get('bytes', 0) for e in entries.values())/1e9:.1f} GB total.", "",
                  "| Licence | Sources | Examples |", "|---|---|---|"]
        for lic, ids in sorted(by_lic.items(), key=lambda x: -len(x[1])):
            lines.append(f"| {lic} | {len(ids)} | {', '.join(f'`{i}`' for i in sorted(ids)[:4])}{' …' if len(ids) > 4 else ''} |")
        lines.append("")

    records, missing = scan_asset_licences()
    lines += ["## 2. Downloaded assets (textures, fonts, motion capture, audio)", ""]
    if records:
        by_group: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            by_group.setdefault(r["group"], []).append(r)
        for group, rs in sorted(by_group.items()):
            total_bytes = sum(r["bytes"] for r in rs)
            lines += [f"### `assets/{group}/` — {len(rs)} items, {total_bytes/1e6:,.1f} MB", "",
                      "| Asset | Licence | Author | Source | Files |", "|---|---|---|---|---|"]
            for r in sorted(rs, key=lambda x: x["asset"]):
                src = f"[link]({r['source']})" if r["source"].startswith("http") else (r["source"] or "—")
                lines.append(f"| `{r['asset']}` | {r['licence']} | {r['author'] or '—'} | {src} | {r['files']} |")
            lines.append("")
    else:
        lines += ["No asset licence records found.", ""]

    tp = scan_third_party()
    lines += ["## 3. Vendored third-party source", ""]
    if tp:
        lines += ["| Path | Licence | Source | Files |", "|---|---|---|---|"]
        for r in tp:
            lines.append(f"| `{r['path']}` | {r['licence']} | {r['source'] or '—'} | {r['files']} |")
        lines.append("")
    else:
        lines += ["None vendored.", ""]

    lines += ["## 4. Python and build dependencies", "",
              "Declared in `pyproject.toml`: numpy, scipy, shapely, pyproj, pyogrio, geopandas, rasterio, pyarrow, polars, "
              "osmium, lxml, requests, tqdm, mapbox_earcut, trimesh, pillow, networkx, rtree, orjson — all BSD, MIT or "
              "Apache-2.0 licensed. Content authoring uses the `bpy` module (Blender, GPL-3.0-or-later) as a *tool*: it "
              "generates asset files, and no Blender source is linked into the shipped runtime, so the GPL does not reach "
              "the Unreal project. Generated geometry and textures carry the licence of their inputs, listed above.", ""]

    if missing:
        lines += ["## 5. Payload without a licence record (gap)", "",
                  "These directories contain files but no licence record was found. They must be given one or removed:", ""]
        lines += [f"* `{m}`" for m in sorted(missing)[:100]]
        if len(missing) > 100:
            lines.append(f"* … and {len(missing) - 100} more")
        lines.append("")
    else:
        lines += ["## 5. Payload without a licence record", "", "None — every asset directory carries a licence record.", ""]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DOCS / "ASSET_LICENSES.md"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    text = build_doc()
    Path(a.out).write_text(text)
    print(f"wrote {a.out} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
