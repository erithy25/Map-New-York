"""Minimal AmbientCG texture fetcher used while the shared ``blender/common/textures.py`` cannot serve a request
(its ``texture_catalog.json`` was not present when this agent started; ``resolve()`` raises before accepting raw ids).

Same public signature as the shared helper::

    get_texture_set(name: str, resolution: str = "2K") -> dict[str, str]

and — deliberately — the **same on-disk layout and LICENSE.json schema** as the shared module, so whichever of the two
fetches an asset first, the other recognises it and never re-downloads:

    assets/textures/<AssetID>/<AssetID>_<RES>_<key>.<ext>      key in color|normal|roughness|ao|displacement|metalness|opacity|emission
    assets/textures/<AssetID>/LICENSE.json                      {"asset_id","provider","author","license","license_url","source_url","url",
                                                                 "sha256","bytes","fetched_at","resolution","files":{"2K":{key:filename}},...}

``name`` is either an AmbientCG asset id (``"Bark012"``) or one of the friendly names in ``PROPS_TEXTURE_NAMES``.
All AmbientCG content is CC0 1.0.  Runs without bpy so pytest can exercise it.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import requests

log = logging.getLogger("nycsim.props.textures")

REPO_ROOT = Path(os.environ.get("NYCSIM_REPO_ROOT", Path(__file__).resolve().parents[2]))
TEXTURE_ROOT = Path(os.environ.get("NYCSIM_TEXTURE_ROOT", REPO_ROOT / "assets" / "textures"))
GET = "https://ambientcg.com/get?file={asset}_{res}-JPG.zip"
VIEW = "https://ambientcg.com/view?id={asset}"
CC0 = {"license": "CC0 1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
AUTHOR = "ambientCG (Lennart Demes)"
USER_AGENT = "NYCSim-props/1.0 (+blender/props/_textures_fallback.py)"
RESOLUTIONS = ("1K", "2K", "4K", "8K")

# Friendly names used by the props scripts -> AmbientCG asset ids (all CC0, verified to exist 2026-09-05).
PROPS_TEXTURE_NAMES: dict[str, str] = {
    "bark_planetree": "Bark004",      # light, smooth, exfoliating plates
    "bark_honeylocust": "Bark007",    # light brown, long scaly ridges
    "bark_callery_pear": "Bark003",   # dark, smooth-ish with shallow furrows
    "bark_pin_oak": "Bark012",        # oak, ridged grey-brown
    "bark_norway_maple": "Bark006",   # dark brown, tight narrow ridges
    "bark_linden": "Bark014",         # grey-brown, interlacing ridges
    "bark_ginkgo": "Bark012",         # grey-brown, furrowed (shared with oak, tinted)
    "bark_zelkova": "Bark005",        # light, smooth, flaking patches
    "bark_sophora": "Bark010",        # brown, rough ridged
    "bark_red_maple": "Bark002",      # dark grey, smooth
    "metal_galvanized": "Metal032",   # grey smooth steel (poles, U-channel)
    "metal_black_powder": "Metal027", # black powder-coated steel (signal housings, Bishop's crook)
    "metal_brushed": "Metal009",      # brushed stainless (newsstand, LinkNYC)
    "metal_cast_iron_rust": "Metal041B",  # cast iron with rust (manhole covers)
    "metal_scratched_steel": "Metal038",  # scratched steel (roadway plate)
    "paint_green_rust": "PaintedMetal006",  # green painted, rusting (litter basket, railings)
    "concrete_smooth": "Concrete034",
    "concrete_rough": "Concrete037",
    "concrete_sidewalk": "Concrete016",
    "asphalt": "Asphalt033",
    "wood_planks": "Planks021",
}

_ACG_SUFFIX = {"Color": "color", "NormalGL": "normal", "Roughness": "roughness", "AmbientOcclusion": "ao",
               "Displacement": "displacement", "Metalness": "metalness", "Opacity": "opacity", "Emission": "emission"}
_ACG_ID_RE = re.compile(r"^[A-Z][A-Za-z0-9]+\d+[A-Z]?$")


class TextureError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_asset_id(name: str) -> str:
    key = name.strip()
    if key in PROPS_TEXTURE_NAMES:
        return PROPS_TEXTURE_NAMES[key]
    if _ACG_ID_RE.match(key):
        return key
    raise TextureError(f"unknown texture name {name!r}; known: {sorted(PROPS_TEXTURE_NAMES)} or an AmbientCG asset id")


def _stream(url: str, dest: Path, attempts: int = 4, timeout: int = 600) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    last: Exception | None = None
    for i in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}, allow_redirects=True) as r:
                if r.status_code >= 400:
                    raise TextureError(f"HTTP {r.status_code} for {url}")
                n = 0
                with open(part, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        if chunk:
                            f.write(chunk)
                            n += len(chunk)
                exp = r.headers.get("Content-Length")
                if exp and int(exp) != n:
                    raise TextureError(f"short read {n} != {exp} for {url}")
            if n < 1000:
                raise TextureError(f"suspiciously small body ({n} B) for {url}")
            os.replace(part, dest)
            return
        except (requests.RequestException, TextureError) as e:
            last = e
            log.warning("attempt %d/%d failed for %s: %s", i + 1, attempts, url, e)
            if part.exists():
                part.unlink()
            time.sleep(2 ** i)
    raise TextureError(f"giving up on {url}: {last}")


def _existing_set(asset_id: str, resolution: str) -> dict[str, str] | None:
    lic = TEXTURE_ROOT / asset_id / "LICENSE.json"
    if not lic.exists():
        return None
    try:
        doc = json.loads(lic.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    files = (doc.get("files") or {}).get(resolution)
    if not files or "color" not in files:
        return None
    out = {k: str(TEXTURE_ROOT / asset_id / v) for k, v in files.items()}
    return out if all(os.path.exists(p) for p in out.values()) else None


def _merge_license(asset_id: str, new: dict, resolution: str, files: dict[str, str]) -> None:
    lic = TEXTURE_ROOT / asset_id / "LICENSE.json"
    doc: dict = {}
    if lic.exists():
        try:
            doc = json.loads(lic.read_text())
        except (OSError, json.JSONDecodeError):
            doc = {}
    doc.update(new)
    doc.setdefault("files", {})[resolution] = files
    doc.setdefault("downloads", {})[resolution] = {k: new[k] for k in ("url", "sha256", "fetched_at", "bytes")}
    tmp = lic.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True))
    os.replace(tmp, lic)


def _fetch(asset_id: str, resolution: str) -> dict[str, str]:
    url = GET.format(asset=asset_id, res=resolution)
    adir = TEXTURE_ROOT / asset_id
    adir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    with tempfile.TemporaryDirectory(dir=adir, prefix=".dl_") as td:
        zpath = Path(td) / f"{asset_id}_{resolution}-JPG.zip"
        log.info("fetching AmbientCG %s %s <- %s", asset_id, resolution, url)
        _stream(url, zpath)
        sha, nbytes = _sha256(zpath), zpath.stat().st_size
        try:
            with zipfile.ZipFile(zpath) as z:
                for info in z.infolist():
                    base = os.path.basename(info.filename)
                    m = re.match(rf"^{re.escape(asset_id)}_{resolution}-JPG_([A-Za-z]+)\.(jpg|png)$", base)
                    if not m or m.group(1) not in _ACG_SUFFIX:
                        continue
                    key = _ACG_SUFFIX[m.group(1)]
                    out_name = f"{asset_id}_{resolution}_{key}.{m.group(2)}"
                    with z.open(info) as src, open(adir / out_name, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    files[key] = out_name
        except zipfile.BadZipFile as e:
            raise TextureError(f"{asset_id}: corrupt zip from {url}") from e
    if "color" not in files:
        raise TextureError(f"{asset_id}: no Color map in {resolution}-JPG zip (got {sorted(files)})")
    meta = {"asset_id": asset_id, "provider": "ambientcg", "author": AUTHOR, **CC0, "source_url": VIEW.format(asset=asset_id), "url": url,
            "sha256": sha, "bytes": nbytes, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "resolution": resolution,
            "normal_convention": "OpenGL (+Y up); DirectX map discarded", "fetched_by": "blender/props/_textures_fallback.py"}
    _merge_license(asset_id, meta, resolution, files)
    return {k: str(adir / v) for k, v in files.items()}


def get_texture_set(name: str, resolution: str = "2K") -> dict[str, str]:
    """Absolute paths of the PBR maps (``color`` always; ``normal``/``roughness``/... when shipped), downloading once."""
    if resolution not in RESOLUTIONS:
        raise TextureError(f"resolution must be one of {RESOLUTIONS}, got {resolution!r}")
    asset_id = resolve_asset_id(name)
    have = _existing_set(asset_id, resolution)
    if have:
        return have
    TEXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    with open(TEXTURE_ROOT / f".{asset_id}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            have = _existing_set(asset_id, resolution)
            return have if have else _fetch(asset_id, resolution)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def prefetch(names: list[str] | None = None, resolution: str = "2K") -> dict[str, dict[str, str]]:
    """Download every texture the props scripts use (idempotent). Returns name -> texture set; raises after trying all."""
    out, errors = {}, []
    for n in names or sorted(PROPS_TEXTURE_NAMES):
        try:
            out[n] = get_texture_set(n, resolution)
            log.info("ready %-22s %s", n, out[n]["color"])
        except TextureError as e:
            log.error("%s: %s", n, e)
            errors.append(f"{n}: {e}")
    if errors:
        raise TextureError("texture fetch failures:\n  " + "\n  ".join(errors))
    return out


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    res = prefetch(sys.argv[1:] or None)
    print(json.dumps({k: os.path.basename(v["color"]) for k, v in res.items()}, indent=1))
