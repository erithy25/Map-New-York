"""Shared PBR texture provider for every NYCSim Blender script (owned by the facade-kit agent).

Public API (stable — other Blender agents import this):

    from textures import get_texture_set, get_texture_meta, list_materials
    maps = get_texture_set("red_brick")            # -> {"color": "/abs/....jpg", "normal": ..., "roughness": ..., "ao": ..., "displacement": ...}
    maps = get_texture_set("Bricks075A")           # raw AmbientCG asset id also accepted
    meta = get_texture_meta("red_brick")           # -> {"asset_id", "provider", "physical_size_m", "license", "roughness_bias", ...}

* ``get_texture_set(name, resolution="2K")`` returns **absolute file paths** only (values are ``str``), keys drawn from
  ``color, normal, roughness, ao, displacement, metalness, opacity, emission`` — ``color`` is always present; the others
  only when the source asset ships them.  Normal maps are OpenGL convention (+Y up), which is what Blender and glTF expect.
* Materials are looked up in ``blender/common/texture_catalog.json`` (NYCSim material enum names from
  ``docs/DATA_CONTRACTS.md`` §5 ``material_primary`` plus kit-specific surfaces) → provider asset id.  Unknown names that
  look like an AmbientCG asset id (``Bricks075A``) or Poly Haven slug (``brick_wall_001``, with ``polyhaven:`` prefix) are
  fetched directly.
* Sources are downloaded once into ``assets/textures/<AssetID>/`` next to a ``LICENSE.json`` (CC0 1.0, url, sha256,
  fetched_at, author).  Idempotent and safe under concurrent callers (per-asset ``fcntl`` lock).  Zips are deleted after
  extraction; only the PBR maps are kept.
* Providers: AmbientCG (``https://ambientcg.com/api/v2/full_json`` → ``https://ambientcg.com/get?file=<ID>_<RES>-JPG.zip``)
  and Poly Haven (``https://api.polyhaven.com/files/<id>`` → direct ``dl.polyhaven.org`` URLs).  Both are CC0 1.0.

CLI:  ``python3 blender/common/textures.py --fetch-all [--resolution 2K]`` | ``--fetch red_brick limestone`` | ``--verify`` | ``--list``
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

log = logging.getLogger("nycsim.textures")

REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
TEXTURE_ROOT = Path(os.environ.get("NYCSIM_TEXTURE_ROOT", REPO_ROOT / "assets" / "textures"))
CATALOG_PATH = Path(__file__).resolve().parent / "texture_catalog.json"

AMBIENTCG_API = "https://ambientcg.com/api/v2/full_json"
AMBIENTCG_GET = "https://ambientcg.com/get?file={asset_id}_{res}-JPG.zip"
AMBIENTCG_VIEW = "https://ambientcg.com/view?id={asset_id}"
POLYHAVEN_FILES = "https://api.polyhaven.com/files/{asset_id}"
POLYHAVEN_INFO = "https://api.polyhaven.com/info/{asset_id}"
CC0 = {"license": "CC0 1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
USER_AGENT = "NYCSim-textures/1.0 (+blender/common/textures.py)"
RESOLUTIONS = ("1K", "2K", "4K", "8K")

# AmbientCG file suffix -> canonical map key. NormalDX is intentionally skipped (glTF/Blender use OpenGL +Y).
_ACG_SUFFIX = {
    "Color": "color", "NormalGL": "normal", "Roughness": "roughness", "AmbientOcclusion": "ao",
    "Displacement": "displacement", "Metalness": "metalness", "Opacity": "opacity", "Emission": "emission",
}
# Poly Haven map key -> canonical key
_PH_MAP = {"Diffuse": "color", "nor_gl": "normal", "Rough": "roughness", "AO": "ao", "Displacement": "displacement", "Metal": "metalness"}

_ACG_ID_RE = re.compile(r"^[A-Z][A-Za-z0-9]+\d+[A-Z]?$")  # Bricks075A, Concrete034, MetalPlates006
_PH_ID_RE = re.compile(r"^[a-z0-9_]+$")


class TextureError(RuntimeError):
    """Raised when a texture set cannot be resolved or downloaded. Message names the asset and the cause."""


# --------------------------------------------------------------------------- catalog
def _load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        raise TextureError(f"texture catalog missing: {CATALOG_PATH}")
    with open(CATALOG_PATH) as f:
        doc = json.load(f)
    if doc.get("schema_version") != 1 or "materials" not in doc:
        raise TextureError(f"texture catalog schema mismatch: {CATALOG_PATH}")
    return doc


def list_materials() -> list[str]:
    """All NYCSim material names known to the catalog (sorted)."""
    return sorted(_load_catalog()["materials"].keys())


def resolve(name: str) -> dict[str, Any]:
    """Resolve a NYCSim material name / alias / raw asset id to a provider record
    ``{"provider": "ambientcg"|"polyhaven", "asset_id": str, "physical_size_m": float, ...catalog fields}``."""
    cat = _load_catalog()
    mats = cat["materials"]
    aliases = cat.get("aliases", {})
    key = name.strip()
    if key in aliases:
        key = aliases[key]
    if key in mats:
        rec = dict(mats[key])
        rec["name"] = key
        rec.setdefault("provider", "ambientcg")
        return rec
    if key.startswith("polyhaven:"):
        aid = key.split(":", 1)[1]
        if not _PH_ID_RE.match(aid):
            raise TextureError(f"invalid Poly Haven id {aid!r}")
        return {"name": key, "provider": "polyhaven", "asset_id": aid, "physical_size_m": 1.0}
    if _ACG_ID_RE.match(key):
        return {"name": key, "provider": "ambientcg", "asset_id": key, "physical_size_m": 1.0}
    raise TextureError(f"unknown material {name!r}; known: {', '.join(sorted(mats))}")


def get_texture_meta(name: str) -> dict[str, Any]:
    """Catalog metadata for a material: asset_id, provider, physical_size_m (metres covered by one tile), roughness_bias,
    tint (RGB multiplier or null), notes, license (once downloaded also sha256/fetched_at)."""
    rec = resolve(name)
    rec.update(CC0)
    lic = TEXTURE_ROOT / rec["asset_id"] / "LICENSE.json"
    if lic.exists():
        with open(lic) as f:
            rec["download"] = json.load(f)
    return rec


# --------------------------------------------------------------------------- helpers
def _requests():
    try:
        import requests  # noqa: WPS433 (lazy so the module imports inside bpy without network deps at import time)
    except ImportError as e:  # pragma: no cover
        raise TextureError("the 'requests' package is required to download textures") from e
    return requests


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _stream(url: str, dest: Path, *, attempts: int = 4, timeout: int = 600) -> None:
    requests = _requests()
    part = dest.with_suffix(dest.suffix + ".part")
    last: Exception | None = None
    for i in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}, allow_redirects=True) as r:
                if r.status_code >= 400:
                    raise TextureError(f"HTTP {r.status_code} for {url}")
                n = 0
                with open(part, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
                            n += len(chunk)
                exp = r.headers.get("Content-Length")
                if exp and int(exp) != n:
                    raise TextureError(f"short read {n} != {exp} for {url}")
            if n == 0:
                raise TextureError(f"empty body for {url}")
            os.replace(part, dest)
            return
        except (requests.RequestException, TextureError) as e:  # type: ignore[union-attr]
            last = e
            log.warning("download attempt %d/%d failed for %s: %s", i + 1, attempts, url, e)
            if part.exists():
                part.unlink()
            time.sleep(2 ** i)
    raise TextureError(f"giving up on {url}: {last}")


def _asset_dir(asset_id: str) -> Path:
    return TEXTURE_ROOT / asset_id


def _license_path(asset_id: str) -> Path:
    return _asset_dir(asset_id) / "LICENSE.json"


def _existing_set(asset_id: str, resolution: str) -> dict[str, str] | None:
    """Return the already-downloaded map set if LICENSE.json lists this resolution and every file is present."""
    lic = _license_path(asset_id)
    if not lic.exists():
        return None
    try:
        with open(lic) as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    files = (doc.get("files") or {}).get(resolution)
    if not files or "color" not in files:
        return None
    out = {k: str(_asset_dir(asset_id) / v) for k, v in files.items()}
    if all(os.path.exists(p) for p in out.values()):
        return out
    return None


def _write_license(asset_id: str, doc: dict[str, Any]) -> None:
    lic = _license_path(asset_id)
    lic.parent.mkdir(parents=True, exist_ok=True)
    tmp = lic.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    os.replace(tmp, lic)


def _merge_license(asset_id: str, new: dict[str, Any], resolution: str, files: dict[str, str]) -> dict[str, Any]:
    lic = _license_path(asset_id)
    doc: dict[str, Any] = {}
    if lic.exists():
        try:
            with open(lic) as f:
                doc = json.load(f)
        except (OSError, json.JSONDecodeError):
            doc = {}
    doc.update(new)
    doc.setdefault("files", {})
    doc["files"][resolution] = files
    doc.setdefault("downloads", {})
    doc["downloads"][resolution] = {k: new[k] for k in ("url", "sha256", "fetched_at", "bytes") if k in new}
    _write_license(asset_id, doc)
    return doc


# --------------------------------------------------------------------------- AmbientCG
def _acg_lookup(asset_id: str) -> dict[str, Any] | None:
    """Fetch the API record for one asset (exact id match) or None when the API is unreachable/unknown."""
    requests = _requests()
    try:
        r = requests.get(AMBIENTCG_API, params={"type": "Material", "q": asset_id, "include": "downloadData,imageData", "limit": 50},
                         timeout=60, headers={"User-Agent": USER_AGENT})
        if r.status_code >= 400:
            log.warning("AmbientCG API HTTP %s for %s", r.status_code, asset_id)
            return None
        for a in r.json().get("foundAssets", []):
            if a.get("assetId") == asset_id:
                return a
    except (requests.RequestException, ValueError) as e:  # type: ignore[union-attr]
        log.warning("AmbientCG API failed for %s: %s", asset_id, e)
    return None


def _acg_download_link(record: dict[str, Any] | None, asset_id: str, resolution: str) -> tuple[str, int | None]:
    attr = f"{resolution}-JPG"
    if record:
        folders = record.get("downloadFolders")
        if isinstance(folders, dict):
            for fv in folders.values():
                cats = fv.get("downloadFiletypeCategories") if isinstance(fv, dict) else None
                dls = ((cats or {}).get("zip") or {}).get("downloads") or []
                for dl in dls:
                    if dl.get("attribute") == attr and dl.get("downloadLink"):
                        return dl["downloadLink"], dl.get("size")
    return AMBIENTCG_GET.format(asset_id=asset_id, res=resolution), None


def _fetch_ambientcg(asset_id: str, resolution: str) -> dict[str, str]:
    record = _acg_lookup(asset_id)
    url, expected_size = _acg_download_link(record, asset_id, resolution)
    adir = _asset_dir(asset_id)
    adir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=adir, prefix=".dl_") as td:
        zpath = Path(td) / f"{asset_id}_{resolution}-JPG.zip"
        log.info("fetching AmbientCG %s %s <- %s", asset_id, resolution, url)
        _stream(url, zpath)
        if expected_size and zpath.stat().st_size != expected_size:
            raise TextureError(f"{asset_id}: zip size {zpath.stat().st_size} != API size {expected_size}")
        sha = _sha256(zpath)
        nbytes = zpath.stat().st_size
        files: dict[str, str] = {}
        try:
            with zipfile.ZipFile(zpath) as z:
                for info in z.infolist():
                    base = os.path.basename(info.filename)
                    m = re.match(rf"^{re.escape(asset_id)}_{resolution}-JPG_([A-Za-z]+)\.(jpg|png)$", base)
                    if not m:
                        continue
                    key = _ACG_SUFFIX.get(m.group(1))
                    if key is None:
                        continue
                    out_name = f"{asset_id}_{resolution}_{key}.{m.group(2)}"
                    with z.open(info) as src, open(adir / out_name, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    files[key] = out_name
        except zipfile.BadZipFile as e:
            raise TextureError(f"{asset_id}: corrupt zip from {url}") from e
    if "color" not in files:
        raise TextureError(f"{asset_id}: no Color map found in {resolution}-JPG zip (files: {sorted(files)})")
    meta = {
        "asset_id": asset_id, "provider": "ambientcg", "author": "ambientCG (Lennart Demes)", **CC0,
        "source_url": AMBIENTCG_VIEW.format(asset_id=asset_id), "url": url, "sha256": sha, "bytes": nbytes,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "resolution": resolution,
        "display_name": (record or {}).get("displayName"), "tags": (record or {}).get("tags"),
        "normal_convention": "OpenGL (+Y up); DirectX map discarded",
    }
    _merge_license(asset_id, meta, resolution, files)
    return {k: str(adir / v) for k, v in files.items()}


# --------------------------------------------------------------------------- Poly Haven
def _fetch_polyhaven(asset_id: str, resolution: str) -> dict[str, str]:
    requests = _requests()
    res = resolution.lower()
    try:
        r = requests.get(POLYHAVEN_FILES.format(asset_id=asset_id), timeout=60, headers={"User-Agent": USER_AGENT})
        if r.status_code >= 400:
            raise TextureError(f"Poly Haven API HTTP {r.status_code} for {asset_id}")
        files_doc = r.json()
        info = requests.get(POLYHAVEN_INFO.format(asset_id=asset_id), timeout=60, headers={"User-Agent": USER_AGENT})
        info_doc = info.json() if info.status_code < 400 else {}
    except (requests.RequestException, ValueError) as e:  # type: ignore[union-attr]
        raise TextureError(f"Poly Haven API failed for {asset_id}: {e}") from e
    adir = _asset_dir(asset_id)
    adir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    shas: dict[str, str] = {}
    urls: dict[str, str] = {}
    total = 0
    for ph_key, key in _PH_MAP.items():
        entry = ((files_doc.get(ph_key) or {}).get(res) or {})
        variant = entry.get("jpg") or entry.get("png")
        if not variant or not variant.get("url"):
            continue
        ext = "jpg" if entry.get("jpg") else "png"
        out = adir / f"{asset_id}_{resolution}_{key}.{ext}"
        log.info("fetching Poly Haven %s %s %s", asset_id, resolution, ph_key)
        _stream(variant["url"], out)
        files[key] = out.name
        shas[key] = _sha256(out)
        urls[key] = variant["url"]
        total += out.stat().st_size
    if "color" not in files:
        raise TextureError(f"{asset_id}: Poly Haven asset has no Diffuse map at {res}")
    authors = info_doc.get("authors") or {}
    meta = {
        "asset_id": asset_id, "provider": "polyhaven", "author": ", ".join(authors) if isinstance(authors, dict) else str(authors), **CC0,
        "source_url": f"https://polyhaven.com/a/{asset_id}", "url": urls.get("color"), "urls": urls, "sha256": shas.get("color"),
        "sha256_by_map": shas, "bytes": total, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "resolution": resolution,
        "display_name": info_doc.get("name"), "tags": info_doc.get("tags"), "normal_convention": "OpenGL (+Y up)",
    }
    _merge_license(asset_id, meta, resolution, files)
    return {k: str(adir / v) for k, v in files.items()}


# --------------------------------------------------------------------------- public
def get_texture_set(name: str, resolution: str = "2K") -> dict[str, str]:
    """Absolute paths of the PBR maps for a NYCSim material (or raw asset id), downloading once if needed.

    Keys: ``color`` (always), ``normal``, ``roughness``, ``ao``, ``displacement``, ``metalness``, ``opacity``, ``emission``
    when the asset provides them. Raises ``TextureError`` on unknown names or failed downloads (never returns placeholders).
    """
    if resolution not in RESOLUTIONS:
        raise TextureError(f"resolution must be one of {RESOLUTIONS}, got {resolution!r}")
    rec = resolve(name)
    asset_id = rec["asset_id"]
    provider = rec.get("provider", "ambientcg")
    have = _existing_set(asset_id, resolution)
    if have:
        return have
    TEXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = TEXTURE_ROOT / f".{asset_id}.lock"
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # other Blender agents may fetch the same asset concurrently
        try:
            have = _existing_set(asset_id, resolution)
            if have:
                return have
            if provider == "ambientcg":
                return _fetch_ambientcg(asset_id, resolution)
            if provider == "polyhaven":
                return _fetch_polyhaven(asset_id, resolution)
            raise TextureError(f"unknown provider {provider!r} for {name}")
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def fetch_all(resolution: str = "2K", names: list[str] | None = None) -> dict[str, dict[str, str]]:
    """Download every catalog material (or the given names). Returns name -> map paths; raises on the first failure
    after attempting all (errors are logged and collected)."""
    out: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for n in names or list_materials():
        try:
            out[n] = get_texture_set(n, resolution)
        except TextureError as e:
            log.error("%s: %s", n, e)
            errors.append(f"{n}: {e}")
    if errors:
        raise TextureError("texture fetch failures:\n  " + "\n  ".join(errors))
    return out


def verify(resolution: str = "2K") -> list[str]:
    """Check every catalog entry has its files and LICENSE.json on disk; returns a list of problems (empty = OK)."""
    problems: list[str] = []
    for n in list_materials():
        rec = resolve(n)
        aid = rec["asset_id"]
        lic = _license_path(aid)
        if not lic.exists():
            problems.append(f"{n} ({aid}): LICENSE.json missing")
            continue
        with open(lic) as f:
            doc = json.load(f)
        for k in ("license", "url", "sha256", "fetched_at"):
            if not doc.get(k):
                problems.append(f"{n} ({aid}): LICENSE.json lacks {k}")
        if _existing_set(aid, resolution) is None:
            problems.append(f"{n} ({aid}): {resolution} maps incomplete")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch-all", action="store_true")
    ap.add_argument("--fetch", nargs="*", default=None, help="material names or asset ids")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--resolution", default="2K", choices=RESOLUTIONS)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.list:
        for n in list_materials():
            rec = resolve(n)
            print(f"{n:24s} {rec['provider']:10s} {rec['asset_id']:22s} tile={rec.get('physical_size_m', 1.0)} m  {rec.get('notes', '')}")
        return 0
    if a.fetch_all or a.fetch is not None:
        t0 = time.time()
        res = fetch_all(a.resolution, a.fetch if a.fetch else None)
        total = sum(os.path.getsize(p) for maps in res.values() for p in maps.values())
        print(json.dumps({"materials": len(res), "bytes": total, "seconds": round(time.time() - t0, 1)}))
    if a.verify:
        problems = verify(a.resolution)
        for p in problems:
            print("PROBLEM", p)
        print(f"verify: {len(problems)} problem(s) over {len(list_materials())} materials")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
