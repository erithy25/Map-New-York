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

#: Surfaces the renderer resolves that are not named by a tile material: the road, which the
#: renderer maps from its own PAVEMENT_KINDS rather than from the glTF material name.
EXTRA = ["asphalt", "concrete_sidewalk"]


def city_surface_names() -> set[str]:
    """Every ``NYCSIM_*`` material name in every exported tile, read off the tiles.

    Written as a hand list first, from one tile, and it was wrong: that tile carried sixteen of the
    nineteen names and the trim deleted ``precast`` (396 tiles), ``stucco`` (156) and
    ``vinyl_siding`` (**1,087**, the third most common material in the city).  A list of names is a
    claim about 2,848 files and has to be read from them.
    """
    import json
    import struct

    names: set[str] = set()
    root = Path("blender_out/tiles")
    if not root.is_dir():
        return names
    for g in sorted(root.glob("**/*.glb")):
        try:
            with g.open("rb") as f:
                if f.read(4) != b"glTF":
                    continue
                struct.unpack("<II", f.read(8))
                ln, _ = struct.unpack("<II", f.read(8))
                doc = json.loads(f.read(ln))
        except (OSError, ValueError, struct.error):
            continue
        for m in doc.get("materials", []):
            n = str(m.get("name") or "")
            if n.startswith("NYCSIM_"):
                names.add(n[len("NYCSIM_"):])
    return names


def keep_asset_ids() -> tuple[list[str], set[str]]:
    """``(surface names, the provider asset ids behind them)`` -- what a trim must not touch."""
    names = sorted(city_surface_names() | set(EXTRA))
    ids = set()
    for n in names:
        try:
            ids.add(tx.resolve(n)["asset_id"])
        except Exception as exc:
            print(f"  !! {n}: not in the texture catalogue ({exc})")
    return names, ids


def main() -> int:
    CITY, keep = keep_asset_ids()
    if len(CITY) < 10:
        print(f"read only {len(CITY)} city surfaces off the tiles; refusing to trim blind")
        return 2
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
    print(f"{len(CITY)} city surfaces read off the tiles: {', '.join(CITY)}")
    print(f"{kept_dirs} city-surface directories kept whole; "
          f"{dropped} 2K files in the other directories {'deleted' if apply else 'would free'} "
          f"{freed / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
