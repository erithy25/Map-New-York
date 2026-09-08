"""Drop the 2K maps of every texture the *renders* do not read.

The renders read ``assets/textures`` for exactly one thing: the eighteen city surfaces the tile
material names resolve to (DEVIATIONS J63).  Every other entry is a *build-time* input for the
props, kit, landmark and vehicle stages, and those stages have already written their own copies
into a ``textures/`` directory beside each .glb (J50), so nothing at render time opens them.

They are re-downloadable in seconds -- 17 materials at 1K took 16 s -- and the container has 1.8 GB
of writable disk against a render pass that needs about 1.7 GB.  Reversible with
``python3 blender/common/textures.py --fetch-all --resolution 2K``.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "blender/common")
import textures as tx

CITY = ["red_brick", "brown_brick", "tan_brick", "white_glazed_brick", "brownstone", "limestone",
        "terracotta", "cast_iron", "glass_curtain", "concrete", "wood_clapboard", "stone_rubble",
        "metal_panel", "granite", "roof_membrane", "tar_roof", "asphalt", "concrete_sidewalk"]
keep = {tx.resolve(n)["asset_id"] for n in CITY}
root = Path("assets/textures")
freed = 0
dropped = 0
kept_dirs = 0
apply = "--apply" in sys.argv
for d in sorted(root.iterdir()):
    if not d.is_dir():
        continue
    if d.name in keep:
        kept_dirs += 1
        continue
    for f in sorted(d.glob("*_2K_*")):
        freed += f.stat().st_size
        dropped += 1
        if apply:
            f.unlink()
print(f"{kept_dirs} city-surface directories kept whole; "
      f"{dropped} 2K files in the other directories {'deleted' if apply else 'would free'} "
      f"{freed / 1e6:.1f} MB")
