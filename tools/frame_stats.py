#!/usr/bin/env python3
"""Luminance and chroma of a comparison sheet's two halves, written beside them.

An assessment that says the render is "too pale" has to say pale *against what*, with a number
somebody else can re-derive.  ``render.json`` carries the render's own frame mean and standard
deviation because the renderer measured them; it carries nothing about the photograph, and nothing
about colour.  Those are the two comparisons an assessment reaches for first, so they are measured
here, once, into ``frame_stats.json`` beside the sheet -- which makes them part of the record that
``tools/assessment_check.py`` checks a quotation against, instead of a number somebody typed.

    python3 tools/frame_stats.py bethesda_terrace_fountain
    python3 tools/frame_stats.py --all

**Chroma** is the mean over pixels of ``max(R,G,B) - min(R,G,B)`` on the 0..1 display values: zero
for any grey, and it separates "this frame is dark" from "this frame has no colour in it", which
luminance alone cannot.  It is a property of the *encoded image*, not a colorimetric measurement of
the scene, and is used only to compare the two halves of one sheet with each other.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path("/home/user/Map-New-York")
COMPARISON = REPO / "docs" / "verification" / "comparison"
REFERENCE = REPO / "docs" / "verification" / "reference"

#: Long side the images are reduced to before measuring.  The statistics are means over millions of
#: pixels and do not move at this scale, and it keeps a 172-sheet sweep to seconds.
SAMPLE_PX = 900


def _stats(path: Path) -> dict | None:
    try:
        from PIL import Image
        import numpy as np
    except ImportError:                                   # pragma: no cover
        return None
    try:
        im = Image.open(path).convert("RGB")
    except (OSError, ValueError):
        return None
    w, h = im.size
    im.thumbnail((SAMPLE_PX, SAMPLE_PX))
    a = np.asarray(im, dtype=np.float64) / 255.0
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return {"width": w, "height": h,
            "mean": round(float(lum.mean()), 4),
            "sd": round(float(lum.std()), 4),
            "p05": round(float(np.percentile(lum, 5)), 4),
            "p95": round(float(np.percentile(lum, 95)), 4),
            "chroma": round(float((a.max(axis=2) - a.min(axis=2)).mean()), 4)}


def measure(slug: str) -> dict:
    d = COMPARISON / slug
    rec = d / "render.json"
    if not rec.is_file():
        return {"slug": slug, "error": "no render.json"}
    doc = json.loads(rec.read_text())
    ref_file = (doc.get("reference_photo") or {}).get("file") or ""
    out = {"slug": slug, "rendered_at": doc.get("rendered_at"),
           "reference_file": ref_file, "sample_long_side_px": SAMPLE_PX,
           "chroma_note": "mean of max(R,G,B) - min(R,G,B) over the display values; 0 for any grey"}
    r = _stats(d / "render.png")
    p = _stats(REFERENCE / slug / ref_file) if ref_file else None
    if r:
        out["render"] = r
    if p:
        out["reference"] = p
    if r and p:
        out["render_over_reference"] = {
            "mean": round(r["mean"] / p["mean"], 3) if p["mean"] else None,
            "sd": round(r["sd"] / p["sd"], 3) if p["sd"] else None,
            "chroma": round(r["chroma"] / p["chroma"], 3) if p["chroma"] else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    slugs = a.slug or (sorted(p.name for p in COMPARISON.iterdir()
                              if p.is_dir() and (p / "render.json").is_file()) if a.all else [])
    if not slugs:
        ap.error("name a slug or pass --all")
    wrote = 0
    for s in slugs:
        doc = measure(s)
        if "error" in doc:
            print(f"{s}: {doc['error']}", file=sys.stderr)
            continue
        (COMPARISON / s / "frame_stats.json").write_text(json.dumps(doc, indent=1) + "\n")
        wrote += 1
        if not a.quiet:
            print(json.dumps(doc, indent=1))
    if a.quiet:
        print(f"{wrote} frame_stats.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
