#!/usr/bin/env python3
"""Every number in an assessment must be traceable to the render record or the item's metadata.

    python3 tools/assessment_check.py                 # every assessment that exists
    python3 tools/assessment_check.py <slug> [<slug>] # named ones
    python3 tools/assessment_check.py --context       # print the line each unsourced number is on

An assessment is prose written about a picture, which is exactly the kind of document that fills up
with figures nobody can check.  An adversarial pass over the first seven of them found between one
and six unsupported claims each and one plain factual error -- a sheet described as "Monday" that
was a Saturday.  So the numbers are checked mechanically against the artefacts they are supposed to
come from: ``render.json``, the fact sheet ``tools/sheet_facts.py`` builds from it, and the
reference item's own ``meta.json``.

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


def facts(slug: str) -> str:
    r = subprocess.run([sys.executable, str(REPO / "tools" / "sheet_facts.py"), slug],
                       capture_output=True, text=True)
    return r.stdout or ""


def haystack(slug: str) -> str:
    parts = [facts(slug)]
    for p in (COMPARISON / slug / "render.json", REFERENCE / slug / "meta.json"):
        if p.is_file():
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


def unsourced(slug: str) -> list[tuple[str, str]]:
    md = COMPARISON / slug / "assessment.md"
    if not md.is_file():
        return []
    text = md.read_text()
    hay = haystack(slug)
    pool = hay_numbers(hay)
    out = []
    for n in sorted(set(re.findall(r"(?<![\w.])(\d[\d,]*\.?\d*)", text)), key=len, reverse=True):
        if BOILERPLATE.match(n.replace(",", "")):
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
    bad = stale = 0
    for slug in slugs:
        md = COMPARISON / slug / "assessment.md"
        rec = COMPARISON / slug / "render.json"
        if md.is_file() and rec.is_file() and md.stat().st_mtime < rec.stat().st_mtime:
            stale += 1
            print(f"STALE {slug}: the assessment is older than the render it describes")
            continue
        rows = unsourced(slug)
        if not rows:
            print(f"ok    {slug}")
            continue
        bad += 1
        print(f"CHECK {slug}: {len(rows)} figure(s) not in the record")
        for n, line in rows:
            print(f"        {n}" + (f"   {line[:120]}" if a.context else ""))
    print(f"\n{len(slugs)} assessments, {stale} older than their own render, "
          f"{bad} with figures that need a source in the prose")
    return 1 if (bad or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
