"""Reject verification stills that cannot serve as evidence (agent C).

A render is evidence only if a person can see the subject in it. This applies the same test the project uses in
``tests/test_world_integration.py::test_verification_renders_can_actually_serve_as_evidence`` to lane C's own
output, so a black frame (camera inside geometry), a blown-out frame, or a featureless grey field (subject too far
away to resolve) is caught here rather than in the report.

Run: ``python3 docs/verification/landmarks/check_renders_c.py [--json]``
Exit status is 1 if any frame fails, so it can gate a build.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
MEAN_MIN = 0.06          # below this the frame is essentially black
MEAN_MAX = 0.94          # above this it is blown out ...
SD_MIN = 0.025           # ... and this little variation means nothing is resolved
BUSY_MIN = 0.030         # ... and this little *local* detail means the subject is not in the frame

# Why the third measure: a frame that is nothing but sky over ground still has a smooth vertical gradient, so its
# standard deviation can be 0.05 while it shows no building at all (that is exactly what the first attempt at the
# ferry-terminal renders looked like). "Busy" is the fraction of pixels whose 3x3 neighbourhood spans more than
# 0.02 in luminance — near zero for a gradient, and 0.36 or more for any frame with a building in it. Measured
# over this lane's 86 renders the six frames that showed nothing scored 0.0001-0.0196 and the worst legitimate one
# scored 0.0364, so the threshold sits at 0.030.


def check(path: Path) -> tuple[bool, str, float, float, float]:
    im = Image.open(path).convert("L")
    a = np.asarray(im, dtype=np.float32) / 255.0
    mean, sd = float(a.mean()), float(a.std())
    hi = np.asarray(im.filter(ImageFilter.MaxFilter(3)), dtype=np.float32) / 255.0
    lo = np.asarray(im.filter(ImageFilter.MinFilter(3)), dtype=np.float32) / 255.0
    busy = float(((hi - lo) > 0.02).mean())
    if mean < MEAN_MIN:
        return False, f"black (mean {mean:.3f})", mean, sd, busy
    if mean > MEAN_MAX and sd < SD_MIN:
        return False, f"blown out (mean {mean:.3f}, sd {sd:.3f})", mean, sd, busy
    if sd < SD_MIN:
        return False, f"featureless (sd {sd:.3f})", mean, sd, busy
    if busy < BUSY_MIN:
        return False, f"subject not in frame (only {busy * 100:.1f} % of pixels carry local detail)", mean, sd, busy
    return True, "ok", mean, sd, busy


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    rows = []
    bad = 0
    for p in sorted(HERE.glob("c_*.png")) + sorted(HERE.glob("canonical_*.png")):
        ok, why, mean, sd, busy = check(p)
        rows.append({"file": p.name, "ok": ok, "why": why, "mean": round(mean, 4), "sd": round(sd, 4),
                     "busy": round(busy, 4)})
        if not ok:
            bad += 1
    if "--json" in argv:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            if not r["ok"]:
                print(f"FAIL {r['file']}: {r['why']}")
        worst = sorted(rows, key=lambda r: r["busy"])[:5]
        print(f"{len(rows)} renders checked, {bad} unusable")
        print("least detail:", ", ".join(f"{r['file']} (busy {r['busy']:.3f}, sd {r['sd']:.3f})" for r in worst))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
