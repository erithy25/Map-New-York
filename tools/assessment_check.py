#!/usr/bin/env python3
"""Every number in an assessment must be traceable to the render record or the item's metadata.

    python3 tools/assessment_check.py                 # every assessment that exists
    python3 tools/assessment_check.py <slug> [<slug>] # named ones
    python3 tools/assessment_check.py --context       # print the line each unsourced number is on

An assessment is prose written about a picture, which is exactly the kind of document that fills up
with figures nobody can check.  An adversarial pass over the first seven of them found between one
and six unsupported claims each and one plain factual error -- a sheet described as "Monday" that
was a Saturday.  So the numbers are checked mechanically against the artefacts they are supposed to
come from: ``render.json``, the fact sheet ``tools/sheet_facts.py`` builds from it, the frame statistics
``tools/frame_stats.py`` measures off both halves of the sheet, and the reference item's own
``meta.json``.

This does not check that a sentence is *true*.  It checks that every figure in it exists in the
record, which is the half a machine can do; the other half is reading the picture.  A number that is
arithmetic on two recorded ones (a difference, a percentage) is legitimately absent and has to be
declared in ``DERIVED`` or spelled out in the prose.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPARISON = REPO / "docs" / "verification" / "comparison"
REFERENCE = REPO / "docs" / "verification" / "reference"

#: Figures that are part of the writing rather than claims about the render: dates, image sizes,
#: sensor and focal lengths already spelled out elsewhere on the sheet, and the ordinals of prose.
BOILERPLATE = re.compile(r"^(19|20)\d\d$|^\d{1,2}$")

#: An assessment may cite a figure it measured itself -- off a glb, off a catalogue entry, off a
#: parquet -- which by definition is not in the render record.  Such a figure is declared in a
#: section under this heading, one table row per figure naming where it came from, and the checker
#: accepts it *and prints it*, so a measurement can be cited but never hidden.  Everything else
#: still has to be traceable to the record.
DECLARED_HEADING = re.compile(r"^#+\s*(measured for this assessment|derived)\s*$", re.I)


def facts(slug: str) -> str:
    r = subprocess.run([sys.executable, str(REPO / "tools" / "sheet_facts.py"), slug],
                       capture_output=True, text=True)
    return r.stdout or ""


def stale_frame_stats(slug: str) -> str | None:
    """Why this slug's ``frame_stats.json`` may not be quoted from, or ``None`` if it may.

    It carries its own ``rendered_at``, copied from the render it measured.  When that does not
    match the render sitting beside it, the file describes a **previous image** -- and because
    this checker treats it as a source, an assessment could quote the luminance of a picture that
    no longer exists and pass.  It went stale on every re-render for as long as it was written
    only by hand (docs/DEVIATIONS.md J77), so a mismatch is refused rather than trusted.
    """
    fs, rec = COMPARISON / slug / "frame_stats.json", COMPARISON / slug / "render.json"
    if not fs.is_file() or not rec.is_file():
        return None
    try:
        got, want = json.loads(fs.read_text()), json.loads(rec.read_text())
    except ValueError as exc:
        return f"frame_stats.json is unreadable ({exc})"
    a, b = got.get("rendered_at"), want.get("rendered_at")
    if a != b:
        return (f"frame_stats.json measures the render of {a}, and the render beside it is "
                f"from {b}: it describes a previous image")
    return None


def haystack(slug: str) -> str:
    parts = [facts(slug)]
    # ``frame_stats.json`` is part of the record too: the renderer measures its own frame and
    # nothing measures the photograph, so the two comparisons an assessment reaches for first --
    # how much darker, how much greyer -- had no source until tools/frame_stats.py wrote one.
    # It is left out when it is stale, so its numbers cannot silently source a quotation.
    skip = {"frame_stats.json"} if stale_frame_stats(slug) else set()
    for p in (COMPARISON / slug / "render.json", COMPARISON / slug / "frame_stats.json",
              REFERENCE / slug / "meta.json"):
        if p.is_file() and p.name not in skip:
            parts.append(p.read_text())
    return "\n".join(parts)


def hay_numbers(hay: str) -> list[float]:
    """Every number in the artefacts, so a rounded quotation can be matched against its source."""
    out = []
    for m in re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", hay):
        try:
            out.append(float(m))
        except ValueError:
            pass
    return out


def rounds_from(value: float, decimals: int, pool: list[float]) -> bool:
    """True when some recorded number rounds to ``value`` at the precision it was quoted to.

    Without this the checker flags every rounded figure -- a sun elevation quoted as 43.6 against a
    record holding 43.55941268305585 -- and 172 assessments of noise is a checker nobody reads.
    """
    return any(round(v, decimals) == value for v in pool)


def declared(text: str) -> tuple[set[str], list[tuple[str, str]]]:
    """Split off the declared-measurement section: its figures, and the rows that carry them.

    A row has to say where its figure comes from, so a row with nothing but a number in it is not
    a declaration and its figure stays unsourced.
    """
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if DECLARED_HEADING.match(l.strip())), None)
    if start is None:
        return set(), []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip().startswith("#"):
            end = i
            break
    figures: set[str] = set()
    rows: list[tuple[str, str]] = []
    for line in lines[start + 1:end]:
        found = re.findall(r"(?<![\w.])(\d[\d,]*\.?\d*)", line)
        if not found:
            continue
        # A declaration names a source as well as a number: a path, a file, or some prose.
        if len(re.sub(r"[\d,.|\s-]", "", line)) < 8:
            continue
        for n in found:
            figures.add(n)
            rows.append((n, line.strip()))
    return figures, rows


def unsourced(slug: str) -> list[tuple[str, str]]:
    md = COMPARISON / slug / "assessment.md"
    if not md.is_file():
        return []
    text = md.read_text()
    declared_figures, _ = declared(text)
    hay = haystack(slug)
    pool = hay_numbers(hay)
    out = []
    for n in sorted(set(re.findall(r"(?<![\w.])(\d[\d,]*\.?\d*)", text)), key=len, reverse=True):
        if BOILERPLATE.match(n.replace(",", "")):
            continue
        if n in declared_figures:
            continue
        plain = n.replace(",", "")
        trimmed = plain.rstrip("0").rstrip(".") if "." in plain else plain
        if plain in hay or n in hay or (trimmed and trimmed in hay):
            continue
        try:
            value = float(plain)
        except ValueError:
            value = None
        if value is not None:
            decimals = len(plain.split(".")[1]) if "." in plain else 0
            if rounds_from(value, decimals, pool):
                continue
        line = next((l.strip() for l in text.splitlines() if n in l), "")
        out.append((n, line))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--context", action="store_true")
    a = ap.parse_args(argv)
    slugs = a.slugs or sorted(p.parent.name for p in COMPARISON.glob("*/assessment.md"))
    bad = stale = measured_elsewhere = declarations = 0
    for slug in slugs:
        md = COMPARISON / slug / "assessment.md"
        rec = COMPARISON / slug / "render.json"
        why = stale_frame_stats(slug)
        if why:
            measured_elsewhere += 1
            print(f"STATS  {slug}: {why}; its figures are not a source until it is re-measured")
        if md.is_file() and rec.is_file() and md.stat().st_mtime < rec.stat().st_mtime:
            stale += 1
            print(f"STALE {slug}: the assessment is older than the render it describes")
            continue
        # A declared measurement is accepted and printed: citable, never invisible.
        _, declared_rows = declared(md.read_text()) if md.is_file() else (set(), [])
        if declared_rows:
            declarations += len(declared_rows)
            print(f"DECL  {slug}: {len(declared_rows)} figure(s) measured for this assessment")
            for n, line in declared_rows:
                print(f"        {n}   {line[:140]}")
        rows = unsourced(slug)
        if not rows:
            print(f"ok    {slug}")
            continue
        bad += 1
        print(f"CHECK {slug}: {len(rows)} figure(s) not in the record")
        for n, line in rows:
            print(f"        {n}" + (f"   {line[:120]}" if a.context else ""))
    print(f"\n{len(slugs)} assessments, {stale} older than their own render, "
          f"{bad} with figures that need a source in the prose, "
          f"{measured_elsewhere} whose frame_stats.json measures a previous image, "
          f"{declarations} figure(s) declared as measured for their assessment")
    return 1 if (bad or stale or measured_elsewhere) else 0


if __name__ == "__main__":
    raise SystemExit(main())
