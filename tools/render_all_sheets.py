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

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path("/home/user/Map-New-York")
COMPARISON = REPO / "docs" / "verification" / "comparison"
REFERENCE = REPO / "docs" / "verification" / "reference"
#: Where the run remembers what it has already done, so a restart resumes instead of re-rendering.
#: Outside the repository by default (``blender_out`` is not tracked) because it changes on every
#: sheet; ``NYCSIM_PASS_STATE`` overrides it. A snapshot of it lives in
#: ``docs/verification/RENDER_PASS.md`` so a fresh container can be told where the pass stood.
LOG = Path(os.environ.get("NYCSIM_PASS_STATE") or (REPO / "blender_out" / "render_all_state.json"))

#: Stop before the disk is gone. A sheet is about 5 MB, a scene build needs room for its temporaries,
#: and a container with no free bytes cannot even be tidied up.
#:
#: **Measured, and lowered from 700 MB.** The 700 was sized for a pavement rebuild running beside
#: this pass; that job is long finished. What a render actually needs above the sheet it overwrites
#: is one linear EXR for the metering pass (`develop_and_meter` writes it, reads it back and
#: unlinks it in a `finally`): the largest frame in the catalogue is 1208x906, so half-float RGB is
#: 6.3 MB uncompressed and less under ZIP, and two workers hold at most one each. Peak scratch is
#: therefore about 13 MB, and a re-render overwrites its sheet in place rather than growing. 300 MB
#: is a 23x margin on that and still refuses to start a pass that would fill the disk.
#:
#: It is a margin against an abort mid-write, not a correctness check: `tools/pass_tick.sh` runs
#: `tools/png_decodes.py` over every changed sheet and refuses to commit one that does not decode,
#: which is what actually catches a truncated PNG.
FLOOR_BYTES = 300 * 1024 * 1024
#: A sheet takes about twelve minutes; three times the p90 is a hang, not a slow frame.
TIMEOUT_S = 3600


sys.path.insert(0, str(REPO / "blender" / "verify"))
#: The generation of record this renderer writes.  Imported rather than restated so the runner's
#: idea of what counts as finished cannot drift from what the renderer actually stamps; the module
#: imports without Blender because its `bpy` imports are all inside functions.
from render_sheets import RECORD_SHAPE  # noqa: E402


def free_bytes() -> int:
    return shutil.disk_usage("/home/user").free


def _now() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _record_shape(slug: str) -> int:
    """What generation wrote this slug's record, or -1 if there is no readable record.

    An unstamped record is generation 0 -- every record written before the stamp existed, which is
    every record of the passes this one supersedes.
    """
    try:
        rec = json.loads((COMPARISON / slug / "render.json").read_text())
    except (OSError, ValueError):
        return -1
    return int(rec.get("record_shape", 0))


def _decline_interior(slug: str) -> bool:
    """Write the declined record for an interior item and return True; False for anything else."""
    import datetime as dt
    meta_path = REFERENCE / slug / "meta.json"
    try:
        meta = json.loads(meta_path.read_text())
    except (OSError, ValueError):
        return False
    if not meta.get("interior"):
        return False
    outdir = COMPARISON / slug
    outdir.mkdir(parents=True, exist_ok=True)
    for name in ("render.png", "sheet.png", "frame_stats.json", "render_error.txt"):
        (outdir / name).unlink(missing_ok=True)
    vp = meta.get("viewpoint") or {}
    photos = [p for p in meta.get("photos", []) if (REFERENCE / slug / (p.get("file") or "")).is_file()]
    photo = photos[0] if photos else None
    rec = {"slug": slug, "name": meta.get("name"), "group": meta.get("group"),
           "record_shape": RECORD_SHAPE,
           "interior": True, "night": bool(meta.get("night")),
           "status": "not_renderable_interior",
           "reason": ("interior view: this build models no building interiors, so there is nothing to "
                      "render from a viewpoint inside one; the item is declined before a scene is built "
                      "rather than rendered black and refused"),
           "viewpoint": {"lat": vp.get("lat"), "lon": vp.get("lon"), "azimuth_deg": vp.get("azimuth_deg"),
                         "note": vp.get("note")},
           "reference_photo": None if photo is None else {
               "file": photo["file"], "author": photo.get("author"),
               "licence": (photo.get("license") or {}).get("short_name"),
               "licence_url": (photo.get("license") or {}).get("url"),
               "page_url": photo.get("page_url"), "title": photo.get("title")},
           "rendered_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    (outdir / "render.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    return True


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


def _parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="*", help="only these slugs (default: every slug with a photograph)")
    ap.add_argument("--last", nargs="*", default=[], metavar="SLUG",
                    help="render these slugs at the end of the queue, in this order.  A world fix that "
                         "is still being built (a canopy stage, a platform deck) only touches a few "
                         "sheets; those go last so the fix can land while the rest of the pass runs, "
                         "and they are rendered once, with it, instead of twice")
    ap.add_argument("--workers", type=int, default=1,
                    help="how many sheets to render at once.  Measured over the v15 pass a sheet spends "
                         "73 %% of its time in a single-threaded scene build and 27 %% in a render that "
                         "uses every core, so two or three workers overlap the builds without starving "
                         "the renders; each worker holds a 1.2 km scene in memory")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    a = _parse(argv)
    only = a.slugs or None
    todo = [s for s in slugs() if not only or s in only]
    deferred = [s for s in a.last if s in todo]
    todo = [s for s in todo if s not in deferred] + deferred
    state = json.loads(LOG.read_text()) if LOG.is_file() else {"done": [], "failed": [], "skipped": []}
    state.setdefault("declined", [])
    # A pass can outlive the code that started it.  Over one afternoon of this pass the sightline
    # fan was widened to the whole model, measured, reverted, and then the plan-extent fields were
    # renamed -- and the runner went on treating every slug in `done` as finished, because `done` is
    # a list of names and says nothing about what wrote the records.  32 of 48 finished sheets
    # carried a rule the finished pass would not carry.  Editing this file by hand to put them back
    # on the queue did nothing twice over: `pending` below is computed once from the state as it was
    # at startup, and `save()` used to write the in-memory dict straight over the file, so the edit
    # was first ignored and then erased by the next finished sheet.
    #
    # So the queue is decided by the records rather than by the list: a slug whose `render.json` is
    # missing, unreadable or stamped with a different `record_shape` than this renderer writes is
    # dropped from `done` here, at startup, where dropping it actually re-queues it.
    dropped = {s_ for s_ in state["done"] + state["declined"] + state["failed"]
               if _record_shape(s_) != RECORD_SHAPE}
    if dropped:
        for key in ("done", "failed", "declined"):
            state[key] = [s_ for s_ in state[key] if s_ not in dropped]
        print(f"{len(dropped)} slug(s) requeued: their record is missing or was written by another "
              f"generation of the renderer than shape {RECORD_SHAPE}", flush=True)
        for s_ in sorted(dropped):
            print(f"    requeued {s_} (shape {_record_shape(s_)})", flush=True)
    state["started_at"] = _now()
    state["record_shape"] = RECORD_SHAPE
    lock = threading.Lock()
    stop = threading.Event()
    #: Every transition this process has made, applied over whatever is on disk at save time.  The
    #: file is not this process's private memory: a tick script reads it, and a person may edit it
    #: between container lives.  Writing the in-memory dict over it discards anything they did.
    mine: dict[str, str] = {}

    def save() -> None:
        on_disk = json.loads(LOG.read_text()) if LOG.is_file() else {}
        for key in ("done", "failed", "declined", "skipped"):
            on_disk.setdefault(key, [])
        # The startup requeue has to reach the file, not just this process's memory: a container
        # that dies before the first sheet finishes would otherwise hand the next run the same
        # stale `done` list to drop again.  A dropped slug that this process has since finished is
        # in `mine` and goes back in below.
        for key in ("done", "failed", "declined"):
            on_disk[key] = [s_ for s_ in on_disk[key] if s_ not in dropped]
        for slug_, where in mine.items():
            for key in ("done", "failed", "declined"):
                if slug_ in on_disk[key] and key != where:
                    on_disk[key].remove(slug_)
            if slug_ not in on_disk[where]:
                on_disk[where].append(slug_)
        on_disk["started_at"] = state.get("started_at")
        on_disk["record_shape"] = RECORD_SHAPE
        if "note" in state:
            on_disk["note"] = state["note"]
        on_disk["skipped"] = state.get("skipped", on_disk["skipped"])
        # `done` on disk is the authority for slugs this process never touched, so a requeue made
        # between container lives survives; `state` keeps a live copy for the pending count.
        for key in ("done", "failed", "declined", "skipped"):
            state[key] = on_disk[key]
        LOG.write_text(json.dumps(on_disk, indent=1))

    # The requeue above is written before a single sheet starts, so a container that dies in the
    # first minute hands the next run a state file that already reflects it.
    save()
    print(f"{len(todo)} slugs, {len(state['done'])} already done this run; "
          f"{free_bytes() / 1e9:.2f} GB free; {max(1, a.workers)} worker(s)", flush=True)

    def one(i: int, slug: str) -> None:
        if stop.is_set():
            return
        if free_bytes() < FLOOR_BYTES:
            with lock:
                if not stop.is_set():
                    print(f"stopping at {slug}: {free_bytes() / 1e6:.0f} MB free is below the floor",
                          flush=True)
                    stop.set()
            return
        t0 = time.time()
        # An interior item is declined here, before a Blender process is even started: the record
        # it needs is a few fields from meta.json, and render_sheets.py keeps the same check as a
        # backstop for anyone who runs it directly.
        if _decline_interior(slug):
            with lock:
                mine[slug] = "declined"
                save()
                print(f"[{i}/{len(todo)}] decl {slug} 0.0 min -- interior view, no interiors are modelled",
                      flush=True)
            return
        r = subprocess.run([sys.executable, "blender/verify/render_sheets.py", "--slugs", slug],
                           cwd=str(REPO), capture_output=True, text=True, timeout=TIMEOUT_S)
        dt = time.time() - t0
        # A sheet counts as finished only if the record it left is of *this* generation.  A worker
        # started before a source change holds the module it imported, so a sheet that finishes
        # after the change can still have been built before it -- that is how a record stamped with
        # the previous generation reached `done` and stayed there.  The finish time is not evidence
        # about which code wrote the record; the stamp in the record is.
        ok = (r.returncode == 0 and (COMPARISON / slug / "render.png").is_file()
              and _record_shape(slug) == RECORD_SHAPE)
        # An interior item is declined before a scene is built and leaves a record saying so; it is
        # neither done nor failed, and it must not be retried as if it had crashed.
        status = None
        try:
            status = json.loads((COMPARISON / slug / "render.json").read_text()).get("status")
        except (OSError, ValueError):
            pass
        if not ok and r.returncode == -9 and slug not in killed_once:
            # The kernel's memory killer, not the renderer: a scene build that overlapped another
            # worker's render.  Once, and only once, the slug goes back on the queue behind the
            # others; a second kill is a real failure and is recorded as one.
            with lock:
                killed_once.add(slug)
                print(f"[{i}/{len(todo)}] KILL {slug} {dt / 60:.1f} min -- out of memory (returncode -9); "
                      f"queued once more", flush=True)
            pool.submit(one, i, slug)
            return
        with lock:
            if not ok and status == "not_renderable_interior":
                mine[slug] = "declined"
                save()
                print(f"[{i}/{len(todo)}] decl {slug} {dt / 60:.1f} min -- interior view, no interiors "
                      f"are modelled", flush=True)
                return
            mine[slug] = "done" if ok else "failed"
            save()
            tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
            print(f"[{i}/{len(todo)}] {'ok  ' if ok else 'FAIL'} {slug} {dt / 60:.1f} min "
                  f"{free_bytes() / 1e9:.2f} GB free" + ("" if ok else f" :: {tail[0][:160]}"), flush=True)
            if not ok:
                # One line of tail is the renderer's own summary, which says a sheet failed and not
                # why.  The traceback above it is the only record of the cause and the process is
                # gone once we move on, so keep it beside the log rather than re-rendering later to
                # find out.
                fail_log = LOG.with_name(f"fail_{slug}.log")
                fail_log.write_text(f"$ {sys.executable} blender/verify/render_sheets.py --slugs {slug}\n"
                                    f"returncode {r.returncode} after {dt:.1f}s\n\n"
                                    f"--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}\n")
                print(f"        cause written to {fail_log.name}", flush=True)

    pending = [(i, s_) for i, s_ in enumerate(todo, 1)
               if s_ not in state["done"] and s_ not in state["declined"]]
    killed_once: set = set()
    pool = ThreadPoolExecutor(max_workers=max(1, a.workers))
    with pool:
        for i, slug in pending:
            pool.submit(one, i, slug)
    if stop.is_set():
        state["skipped"] = [s_ for s_ in todo if s_ not in state["done"] and s_ not in state["failed"]
                            and s_ not in state["declined"]]
        save()
        return 2
    print(json.dumps({"done": len(state["done"]), "failed": state["failed"],
                      "declined": state["declined"]}, indent=1))
    return 1 if state["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
