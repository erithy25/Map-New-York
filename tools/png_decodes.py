#!/usr/bin/env python3
"""Every changed PNG in the working tree decodes, before any of it is staged.

    python3 tools/png_decodes.py

The render pass writes concurrently with everything else, so a PNG can be half written at the
moment ``git add`` reads it.  A truncated sheet looks like a sheet in the index and is only found
when someone opens it, which is the worst time.

A **deleted** PNG is not a truncated one and is counted separately: when the frame gate refuses a
render as unusable the renderer removes that item's stale ``render.png`` and ``sheet.png``, so the
files are meant to be gone and a guard that called that a truncation would block the very commit
that records the refusal.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

out = subprocess.run(["git", "status", "--porcelain"], cwd=str(Path(__file__).resolve().parents[1]),
                     capture_output=True, text=True, check=True).stdout
bad, ok, gone = [], 0, 0
for line in out.splitlines():
    status, path = line[:2], line[3:].strip().strip('"')
    if not path.endswith(".png"):
        continue
    if "D" in status:
        # A deletion is not a truncation.  The renderer removes a stale sheet when it refuses to
        # publish a new frame, so the file is *meant* to be gone.
        gone += 1
        continue
    try:
        im = Image.open(Path(__file__).resolve().parents[1] / path)
        im.load()
        ok += 1
    except Exception as exc:
        bad.append((path, exc))
for p, e in bad:
    print(f"TRUNCATED {p}: {e}")
print(f"{ok} changed PNGs decode, {len(bad)} do not, {gone} deleted on purpose")
sys.exit(1 if bad else 0)
