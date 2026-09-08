#!/usr/bin/env python3
"""Rebuild ``data/raw/character_assets/mh_data`` from the MakeHuman asset packs.

    python3 tools/unpack_character_assets.py            # fetch what is missing, then unpack
    python3 tools/unpack_character_assets.py --check    # say what is there, download nothing
    python3 tools/unpack_character_assets.py --keep-zips

**Why this file exists.** The character stage reads its clothes, hair, skins, eyes, teeth and poses
from ``data/raw/character_assets/mh_data``, and MPFB2's user-data directory is a set of symlinks into
it (``blender/character/chenv.py``).  That tree was built once, by hand, from fourteen MakeHuman
community asset packs -- and **the step that built it was never in the repository**.  So when the
packs and the unpacked tree were both deleted to free disk, the symlinks were left dangling and the
character stage could not be re-run at all: ``enable_mpfb`` fails with every asset directory missing,
and ``docs/SOURCE_ARTEFACTS.md`` still listed ``mh_data`` under *what was considered and not removed*
(docs/DEVIATIONS.md J58).

The packs were also absent from ``nycsim_pipeline.sources``, so ``python -m nycsim_pipeline.download
--id mh_bodyparts01`` answered "unknown source id": they were recorded in
``data/manifest/downloads.json`` after being fetched by some route that left no trace.  This script
reads that manifest -- the URL, the byte count and the SHA-256 it already holds for each pack -- so
the recovery is a runnable command against recorded hashes rather than a paragraph of instructions.

**The layout needs no mapping.** Each pack's zip is already rooted at the directory names MPFB
expects (``clothes/``, ``eyes/``, ``skins/``, ``packs/``, ...), so unpacking is a merge of all
fourteen archives into one tree.  That was measured, not assumed: ``bodyparts01_cc0.zip`` holds 26
entries under exactly two top-level names, ``clothes`` and ``packs``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "data" / "manifest" / "downloads.json"
ASSETS = REPO / "data" / "raw" / "character_assets"
MH_DATA = ASSETS / "mh_data"

#: The directories ``chenv.enable_mpfb`` requires; a rebuild that does not produce all of these has
#: not worked, whatever the archives contained.
REQUIRED = ("clothes", "eyes", "teeth", "tongue", "hair", "skins", "eyebrows", "eyelashes")

#: Packs that do **not** merge into the shared tree, and the subdirectory each gets instead.
#:
#: ``faceunits01`` is the only one.  Its archive is rooted at ``targets/faceunits`` and ``packs/``
#: like every other pack, so a plain merge puts 52 face-unit morph targets into the same
#: ``mh_data/targets`` directory MPFB reads body targets from.  The build keeps them apart --
#: ``mh_build.FACEUNITS_DIR`` is ``mh_data/faceunits_pack/targets/faceunits`` -- and that path is the
#: only surviving record of how the original tree was laid out, so it is reproduced here rather than
#: the code being bent to match a generic unpacker.
INTO_OWN_DIR = {"mh_faceunits01": "faceunits_pack"}

#: Paths a merge would create that belong to a pack in :data:`INTO_OWN_DIR`, cleaned up so a tree
#: unpacked by an earlier version of this script converges on the same result as a fresh one.
MERGED_BY_MISTAKE = ("targets/faceunits", "packs/faceunits01.json")


def packs() -> dict[str, dict]:
    """Manifest entries whose path is under ``character_assets``, by source id."""
    entries = json.loads(MANIFEST.read_text())["entries"]
    return {k: v for k, v in entries.items()
            if "character_assets" in str(v.get("path", "")) and str(v.get("path", "")).endswith(".zip")}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(entry: dict, dest: Path, *, timeout: float = 300.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(entry["url"], timeout=timeout) as r:
        body = r.read()
    got = hashlib.sha256(body).hexdigest()
    if entry.get("sha256") and got != entry["sha256"]:
        raise SystemExit(f"{dest.name}: sha256 {got} does not match the manifest's {entry['sha256']}")
    if entry.get("bytes") and len(body) != int(entry["bytes"]):
        raise SystemExit(f"{dest.name}: {len(body)} bytes, manifest says {entry['bytes']}")
    dest.write_bytes(body)


def unpack(zip_path: Path, into: Path) -> int:
    """Extract one pack into ``into``; returns how many files it wrote.

    ``ZipFile.extractall`` is not used: a member whose name climbs out of the tree would land
    anywhere on disk, and these archives come off the public internet.
    """
    into.mkdir(parents=True, exist_ok=True)
    written = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            target = (into / name).resolve()
            if not str(target).startswith(str(into.resolve()) + "/"):
                raise SystemExit(f"{zip_path.name}: member {name!r} escapes the target directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report what is present; download nothing")
    ap.add_argument("--keep-zips", action="store_true",
                    help="keep the archives after unpacking (they are 442 MB)")
    a = ap.parse_args(argv)

    got = packs()
    if not got:
        print("no character asset packs in the manifest", file=sys.stderr)
        return 2
    have_dirs = [d for d in REQUIRED if (MH_DATA / d).is_dir()]
    face = MH_DATA / INTO_OWN_DIR["mh_faceunits01"] / "targets" / "faceunits"
    print(f"faceunits targets: {len(list(face.glob('*.target'))) if face.is_dir() else 0} "
          f"(mh_build.FACEUNITS_DIR = {face})")
    print(f"{len(got)} packs in the manifest, "
          f"{sum(int(v.get('bytes') or 0) for v in got.values()) / 1e6:.1f} MB")
    print(f"mh_data has {len(have_dirs)} of {len(REQUIRED)} required directories: "
          f"{', '.join(have_dirs) or '(none)'}")
    for sid, e in sorted(got.items()):
        p = REPO / e["path"]
        state = "present" if p.is_file() else "absent"
        print(f"   {sid:20} {state:8} {int(e.get('bytes') or 0) / 1e6:7.1f} MB  {e['path']}")
    if a.check:
        return 0 if len(have_dirs) == len(REQUIRED) else 1

    total = 0
    for sid, e in sorted(got.items()):
        p = REPO / e["path"]
        if not p.is_file():
            print(f"fetching {sid} ...", flush=True)
            fetch(e, p)
        elif e.get("sha256") and sha256(p) != e["sha256"]:
            raise SystemExit(f"{p} is on disk but does not match the manifest's sha256")
        sub = INTO_OWN_DIR.get(sid)
        n = unpack(p, MH_DATA / sub if sub else MH_DATA)
        total += n
        print(f"   {sid:20} {n:5d} files", flush=True)
        if not a.keep_zips:
            p.unlink()
    for stray in MERGED_BY_MISTAKE:
        q = MH_DATA / stray
        if q.is_dir():
            shutil.rmtree(q)
            print(f"   removed {stray} (it belongs in faceunits_pack)")
        elif q.is_file():
            q.unlink()
            print(f"   removed {stray} (it belongs in faceunits_pack)")
    missing = [d for d in REQUIRED if not (MH_DATA / d).is_dir()]
    for sid, sub in INTO_OWN_DIR.items():
        if sid in got and not (MH_DATA / sub).is_dir():
            missing.append(sub)
    print(f"unpacked {total} files into {MH_DATA}")
    if missing:
        print(f"still missing: {', '.join(missing)}", file=sys.stderr)
        return 1
    print("every directory chenv.enable_mpfb requires is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
