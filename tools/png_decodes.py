#!/usr/bin/env python3
"""Every changed PNG in the working tree decodes, before any of it is staged.

    python3 tools/png_decodes.py

The render pass writes concurrently with everything else, so a PNG can be half written at the
moment ``git add`` reads it.  A truncated sheet looks like a sheet in the index and is only found
when someone opens it, which is the worst time.

**A file still being written is not a broken one, and the difference has to be measured rather than
assumed.**  The first version of this guard called every PNG that would not decode a truncation and
told the caller to look at it by hand; on the v17 pass that stopped a tick over a `sheet.png` the
renderer was midway through, and a second later it decoded perfectly.  Blocking on a normal
concurrent write is a false alarm that costs a batch of finished sheets their commit.  So a failure
is retried: if the file's size is still changing, or it starts decoding, it was in flight; if the
size has settled and it still will not decode, it is truncated.  The two get different exit codes,
because the right answer to one is "wait for the next tick" and to the other is "stop".

A **deleted** PNG is neither and is counted separately: when the frame gate refuses a render as
unusable the renderer removes that item's stale ``render.png`` and ``sheet.png``, so the files are
meant to be gone and a guard that called that a truncation would block the very commit that records
the refusal.

Exit codes: 0 every changed PNG decodes; 1 at least one is truncated and settled; 2 at least one is
still being written and nothing is truncated.
"""
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

#: How many times a failure is retried, and how long between tries.  A sheet is about 3 MB and is
#: written in well under a second; six tries over three seconds is far more than one write needs and
#: still returns before a caller notices.
RETRIES = 6
WAIT_S = 0.5

ROOT = Path(__file__).resolve().parents[1]


def decodes(path: Path) -> bool:
    try:
        im = Image.open(path)
        im.load()
        return True
    except Exception:
        return False


out = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                     capture_output=True, text=True, check=True).stdout
changed, gone = [], 0
for line in out.splitlines():
    status, path = line[:2], line[3:].strip().strip('"')
    if not path.endswith(".png"):
        continue
    if "D" in status:
        # A deletion is not a truncation.  The renderer removes a stale sheet when it refuses to
        # publish a new frame, so the file is *meant* to be gone.
        gone += 1
        continue
    changed.append(path)

ok, bad, in_flight = 0, [], []
for rel in changed:
    p = ROOT / rel
    if decodes(p):
        ok += 1
        continue
    # It did not decode.  Watch it: a file being written changes size, and one being finished starts
    # decoding.  Either way it is not this guard's business to stop the pass over it.
    size = p.stat().st_size if p.exists() else -1
    moved = False
    for _ in range(RETRIES):
        time.sleep(WAIT_S)
        now = p.stat().st_size if p.exists() else -1
        if now != size:
            moved, size = True, now
        if decodes(p):
            ok += 1
            break
    else:
        (in_flight if moved else bad).append(rel)

for rel in bad:
    print(f"TRUNCATED {rel}: settled at {(ROOT / rel).stat().st_size} bytes and will not decode")
for rel in in_flight:
    print(f"IN FLIGHT {rel}: still growing after {RETRIES * WAIT_S:.0f}s, so a render is writing it")
print(f"{ok} changed PNGs decode, {len(bad)} do not, {len(in_flight)} still being written, "
      f"{gone} deleted on purpose")
sys.exit(1 if bad else (2 if in_flight else 0))
