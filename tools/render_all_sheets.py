#!/usr/bin/env python3
"""Render every comparison sheet there is a reference photograph for, one Blender process each.

Two things were true when this was written and neither was obvious from the task list. The 57 sheets
that exist are **all** stale, not the 27 the task named: they were rendered before the curb ramps
were cut into the region's pavement, before the open-space ground existed, before the elevated
structures and station platforms stood on measured ground, before the rooftop plant was lifted onto
its roofs and before the vehicles got their real materials. And there are **172** reference slugs
with a downloaded photograph, so 115 of them have never been rendered at all -- the comparison
evidence covers a third of the references that were licensed for it.

So this renders all 172, the stale ones first because they are the ones the written assessments
depend on. One process per slug: a crash costs one sheet rather than the run, and the memory of a
1.2 km scene goes back to the operating system between them.

The container's writable disk is nearly spent, and a render that runs out of it mid-write leaves a
truncated PNG that looks like a render. So free space is checked before each sheet and the run stops
cleanly while there is still room to stop in.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/user/Map-New-York")
COMPARISON = REPO / "docs" / "verification" / "comparison"
REFERENCE = REPO / "docs" / "verification" / "reference"
#: Where the run remembers what it has already done, so a restart resumes instead of re-rendering.
#: Outside the repository by default (``blender_out`` is not tracked) because it changes on every
#: sheet; ``NYCSIM_PASS_STATE`` overrides it. A snapshot of it lives in
#: ``docs/verification/RENDER_PASS_V15.md`` so a fresh container can be told where the pass stood.
LOG = Path(os.environ.get("NYCSIM_PASS_STATE") or (REPO / "blender_out" / "render_all_state.json"))

#: Stop before the disk is gone. A sheet is about 5 MB, a scene build needs room for its temporaries,
#: and a container with no free bytes cannot even be tidied up.
FLOOR_BYTES = 700 * 1024 * 1024   # the pavement rebuild is running beside this; leave it room
#: A sheet takes about twelve minutes; three times the p90 is a hang, not a slow frame.
TIMEOUT_S = 3600


def free_bytes() -> int:
    return shutil.disk_usage("/home/user").free


def slugs() -> list[str]:
    """Every reference slug with a photograph on disk, the already-rendered ones first."""
    out: list[tuple[int, str]] = []
    for d in sorted(REFERENCE.iterdir()):
        meta = d / "meta.json"
        if not d.is_dir() or not meta.is_file():
            continue
        try:
            doc = json.loads(meta.read_text())
        except (OSError, ValueError):
            continue
        if not any((d / (p.get("file") or "")).is_file() for p in doc.get("photos", [])):
            continue
        rendered = (COMPARISON / d.name / "render.png").is_file()
        out.append((0 if rendered else 1, d.name))
    return [s for _, s in sorted(out)]


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or None
    todo = [s for s in slugs() if not only or s in only]
    state = json.loads(LOG.read_text()) if LOG.is_file() else {"done": [], "failed": [], "skipped": []}
    print(f"{len(todo)} slugs, {len(state['done'])} already done this run; "
          f"{free_bytes() / 1e9:.2f} GB free", flush=True)
    for i, slug in enumerate(todo, 1):
        if slug in state["done"]:
            continue
        if free_bytes() < FLOOR_BYTES:
            print(f"stopping at {slug}: {free_bytes() / 1e6:.0f} MB free is below the floor",
                  flush=True)
            state["skipped"] = [s for s in todo if s not in state["done"] and s not in state["failed"]]
            LOG.write_text(json.dumps(state, indent=1))
            return 2
        t0 = time.time()
        r = subprocess.run([sys.executable, "blender/verify/render_sheets.py", "--slugs", slug],
                           cwd=str(REPO), capture_output=True, text=True, timeout=TIMEOUT_S)
        dt = time.time() - t0
        ok = r.returncode == 0 and (COMPARISON / slug / "render.png").is_file()
        (state["done"] if ok else state["failed"]).append(slug)
        LOG.write_text(json.dumps(state, indent=1))
        tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
        print(f"[{i}/{len(todo)}] {'ok  ' if ok else 'FAIL'} {slug} {dt / 60:.1f} min "
              f"{free_bytes() / 1e9:.2f} GB free" + ("" if ok else f" :: {tail[0][:160]}"), flush=True)
        if not ok:
            # One line of tail is the renderer's own summary, which says a sheet failed and not why.
            # The traceback above it is the only record of the cause and the process is gone once we
            # move on, so keep it beside the log rather than re-rendering later to find out.
            fail_log = LOG.with_name(f"fail_{slug}.log")
            fail_log.write_text(f"$ {sys.executable} blender/verify/render_sheets.py --slugs {slug}\n"
                                f"returncode {r.returncode} after {dt:.1f}s\n\n"
                                f"--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}\n")
            print(f"        cause written to {fail_log.name}", flush=True)
    print(json.dumps({"done": len(state["done"]), "failed": state["failed"]}, indent=1))
    return 1 if state["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
