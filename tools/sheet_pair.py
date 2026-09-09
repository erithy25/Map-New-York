#!/usr/bin/env python3
"""Both halves of a comparison sheet in one small image, for reading them side by side.

The sheet is already two halves side by side, but at 2624 px wide with a caption block that is
mostly small print.  This crops the caption away and scales what is left to something that can be
read in one look.
"""
import os
import sys

from PIL import Image

slug = sys.argv[1]
frac = float(sys.argv[2]) if len(sys.argv) > 2 else 0.62
out = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("SHEET_PAIR_OUT", "pair.png")
im = Image.open(f"docs/verification/comparison/{slug}/sheet.png")
im.load()
w, h = im.size
im = im.crop((0, 0, w, int(h * frac)))
im.thumbnail((1100, 700))
im.convert("RGB").save(out)
print(f"{slug}: {w}x{h} -> {im.size} at {out}")
