#!/usr/bin/env python3
"""Package the world for a machine that has an Unreal editor and does not have this repository's data.

    python3 tools/package_content.py --tile-list tiles.txt --out dist/first-drive
    python3 tools/package_content.py --manifest data/processed/unreal_manifest.json --out dist/all

``data/processed/`` and ``blender_out/`` are gitignored -- deliberately, they are 40 GB of derived
artefacts -- so a clone of this repository has the code and none of the city. This writes the missing
half as a set of numbered ``.tar.gz`` parts small enough to travel through a git remote (GitHub
refuses a single file over 100 MB without LFS), plus an index that names every file and its SHA-256
and an ``UNPACK.md`` with the two commands that put it back.

**What goes in is decided by the manifest, not by a hand-written list.** ``unreal_manifest.json``
already names every asset the import needs and where it goes; this walks its entries, adds the
per-tile files the manifest references by path rather than as entries (the heightmaps, the props and
signs JSON the editor's Python reads because UE has no pyarrow, the kit placement records, the water
masks), adds the image files each ``.glb`` names in its ``sidecars`` list -- a ``.glb`` stopped being
self-contained when 2.61 GB of duplicate image data was moved out of the binary chunks into
``textures/`` directories -- and adds nothing else. If a file is not needed to import and run, it is not in the package,
and if the manifest gains an entry the package gains a file without anyone remembering to add it.

Parts are written one at a time and the caller may push and delete each one before the next is
built, so the whole package never has to exist at once -- which matters here, where the machine
building it has less free disk than the package it is building.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PART_BYTES = 90 * 1024 * 1024

#: Files a tile owns that the manifest names by path rather than listing as its own entry.
PER_TILE_FILES = ("terrain.png", "terrain.json", "props.json", "signs.json",
                  "kit_placements.bin", "water_mask.png", "lanes_debug.json")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(manifest_path: Path, tiles: set[str] | None) -> tuple[list[Path], dict]:
    """Every file the import needs, and a note of what was asked for and not found."""
    doc = json.loads(manifest_path.read_text())
    wanted: dict[str, Path] = {}
    missing: list[str] = []

    def add(rel: str) -> None:
        p = REPO_ROOT / rel
        if p.is_file():
            wanted[rel] = p
        else:
            missing.append(rel)

    add(str(manifest_path.resolve().relative_to(REPO_ROOT)))
    sidecars = 0
    for entry in doc.get("entries", []):
        tile = entry.get("tile")
        if tiles is not None and tile and tile not in tiles:
            continue
        add(entry["src"])
        # A .glb is no longer self-contained: since the duplicate images were moved out of the
        # binary chunks it names them as files in a textures/ directory beside it. Ship the .glb
        # without them and the import produces an untextured mesh and no error to say so.
        for rel in entry.get("sidecars") or ():
            add(rel)
            sidecars += 1
    for tile in sorted(doc.get("tiles", {})):
        if tiles is not None and tile not in tiles:
            continue
        for name in PER_TILE_FILES:
            p = REPO_ROOT / "data" / "processed" / "tiles" / tile / name
            if p.is_file():
                wanted[str(p.relative_to(REPO_ROOT))] = p
    # The station index the radio reads is a file path, not a content path, so it travels as itself.
    if tiles is not None:
        # Landmarks carry no tile in the manifest - they are placed from their own index - so a
        # region package would otherwise drag all 927 MB of them across the world. The index says
        # which tile each stands in; the ones outside the region are a second package's problem.
        index = REPO_ROOT / "data" / "processed" / "landmarks" / "landmarks.json"
        if index.is_file():
            doc_lm = json.loads(index.read_text())
            keep = {r["stem"] for r in doc_lm.get("landmarks", []) if r.get("tile") in tiles}
            dropped = 0
            for rel in list(wanted):
                if not rel.startswith("blender_out/landmarks/"):
                    continue
                stem = Path(rel).stem
                base = stem[:-5] if stem.endswith("_LOD1") else stem
                if base not in keep:
                    del wanted[rel]
                    dropped += 1
            note_landmarks = {"kept": len(keep), "dropped_files": dropped}
        else:
            note_landmarks = {"kept": None, "dropped_files": 0,
                              "reason": "no landmarks index; every landmark travels"}
    else:
        note_landmarks = {"kept": "all", "dropped_files": 0}

    for extra in ("data/processed/audio/stations.json", "data/processed/crs.json",
                  # The package now carries third-party CC0 texture files as files rather than as
                  # bytes inside a .glb, so it carries the record of where they came from too.
                  "docs/ASSET_LICENSES.md"):
        if (REPO_ROOT / extra).is_file():
            add(extra)

    files = [wanted[k] for k in sorted(wanted)]
    return files, {"missing": missing, "manifest_entries": len(doc.get("entries", [])),
                   "sidecar_references": sidecars,
                   "sidecar_files": len({k for k in wanted if "/textures/" in k}),
                   "landmarks": note_landmarks}


def write_parts(files: list[Path], out_dir: Path, part_bytes: int, *,
                on_part=None) -> list[dict]:
    """Write ``part_000.tar.gz``, ``part_001.tar.gz``, ... none larger than ``part_bytes`` uncompressed.

    ``on_part`` is called with each finished part's path, so a caller with less disk than the package
    can push it and delete it before the next one is built.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[dict] = []
    index = 0
    current: list[Path] = []
    size = 0

    def flush() -> None:
        nonlocal current, size, index
        if not current:
            return
        path = out_dir / f"part_{index:03d}.tar.gz"
        with tarfile.open(path, "w:gz", compresslevel=6) as tar:
            for f in current:
                tar.add(f, arcname=str(f.relative_to(REPO_ROOT)))
        rec = {"part": path.name, "files": len(current), "raw_bytes": size,
               "bytes": path.stat().st_size, "sha256": _sha256(path)}
        parts.append(rec)
        print(f"  {path.name}: {len(current)} files, {rec['bytes'] / 1e6:.1f} MB "
              f"({size / 1e6:.1f} MB raw)", flush=True)
        if on_part is not None:
            on_part(path)
        index += 1
        current = []
        size = 0

    for f in files:
        n = f.stat().st_size
        if current and size + n > part_bytes:
            flush()
        current.append(f)
        size += n
    flush()
    return parts


UNPACK = """# Unpacking the NYCSim content

`data/processed/` and `blender_out/` are gitignored, so a clone of this repository has the code and
none of the city. These parts are the city.

    git fetch origin {branch}
    git checkout {branch} -- {rel}
    cat {rel}/part_*.tar.gz | tar -xzvf - -i -C .

Git for Windows ships `tar`, so nothing else needs installing. The `-i` matters: `cat` of several
gzip members is a valid stream, and `tar` needs telling to read past the first end-of-archive marker.

To check what arrived:

    python3 tools/package_content.py --verify {rel}

Then, from the repository root:

    python3 unreal/tools/gen_core_unity.py --check     # already committed; this only re-checks
    <UnrealEditor-Cmd> NYCSim.uproject -run=NYCImport -stages=validate,stage,assets,levels
    <UnrealEditor> NYCSim.uproject                     # open /Game/NYCSim/Maps/NYC and press Play

`unreal/README.md` has the long version, including the one manual step the editor's Python cannot do.
"""


def verify(out_dir: Path) -> int:
    index_path = out_dir / "index.json"
    if not index_path.is_file():
        print(f"no index at {index_path}")
        return 2
    doc = json.loads(index_path.read_text())
    bad = 0
    for rec in doc["parts"]:
        p = out_dir / rec["part"]
        if not p.is_file():
            print(f"MISSING {rec['part']}")
            bad += 1
            continue
        got = _sha256(p)
        if got != rec["sha256"]:
            print(f"CORRUPT {rec['part']}: {got[:16]} != {rec['sha256'][:16]}")
            bad += 1
    print(f"{len(doc['parts']) - bad}/{len(doc['parts'])} parts verified, "
          f"{doc['files']} files, {doc['raw_bytes'] / 1e9:.2f} GB")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path,
                    default=REPO_ROOT / "data" / "processed" / "unreal_manifest.json")
    ap.add_argument("--tile-list", type=Path, default=None,
                    help="one tile per line; without it every tile in the manifest travels")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "dist" / "content")
    ap.add_argument("--part-mb", type=int, default=DEFAULT_PART_BYTES // (1024 * 1024))
    ap.add_argument("--branch", default="dist/first-drive", help="branch named in UNPACK.md")
    ap.add_argument("--dry-run", action="store_true", help="report the file set and stop")
    ap.add_argument("--verify", type=Path, default=None, help="check an existing package's hashes")
    a = ap.parse_args(argv)

    if a.verify is not None:
        return verify(a.verify)

    tiles = None
    if a.tile_list:
        tiles = {t.strip() for t in a.tile_list.read_text().split("\n") if t.strip()}
    files, note = collect(a.manifest, tiles)
    raw = sum(f.stat().st_size for f in files)
    print(f"{len(files)} files, {raw / 1e9:.2f} GB raw"
          + (f", {len(tiles)} tiles" if tiles else ", every tile"))
    lm = note.get("landmarks") or {}
    if lm.get("dropped_files"):
        print(f"  landmarks: {lm['kept']} inside the region, {lm['dropped_files']} files left out")
    if note["missing"]:
        print(f"  {len(note['missing'])} manifest entries have no file: {note['missing'][:4]}")
    if a.dry_run:
        by_top: dict[str, int] = {}
        for f in files:
            key = "/".join(str(f.relative_to(REPO_ROOT)).split("/")[:2])
            by_top[key] = by_top.get(key, 0) + f.stat().st_size
        for k, v in sorted(by_top.items(), key=lambda kv: -kv[1])[:12]:
            print(f"  {v / 1e6:9.1f} MB  {k}")
        return 0

    parts = write_parts(files, a.out, a.part_mb * 1024 * 1024)
    index = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": len(files),
        "raw_bytes": raw,
        "tiles": sorted(tiles) if tiles else "all",
        "parts": parts,
        "manifest": str(a.manifest.relative_to(REPO_ROOT)),
        "missing_from_manifest": note["missing"],
    }
    (a.out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    # ``--out`` may sit outside the repository -- a sparse worktree of the delivery branch, which is
    # how a package is cut when the disk cannot hold both the old parts and the new ones.  A path
    # that is not under the root has no repository-relative name, so the branch-relative one it will
    # be checked out under is used instead, and the unpacking notes are still written.
    try:
        rel = a.out.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        parts = a.out.resolve().as_posix().split("/")
        rel = "/".join(parts[parts.index("dist"):]) if "dist" in parts else a.out.name
    (a.out / "UNPACK.md").write_text(UNPACK.format(branch=a.branch, rel=rel))
    print(f"{len(parts)} parts, {sum(p['bytes'] for p in parts) / 1e9:.2f} GB packed -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
