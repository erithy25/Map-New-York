#!/usr/bin/env python3
"""Which built tiles the 172 comparison viewpoints can reach, and which they cannot.

The v16 pass ran the container's writable allowance out at sheet 59, and 259 ``tile_pavement.glb``
files were deleted to finish it -- under the rule that they lay *"further than 3 km from every
viewpoint still to be rendered"*. That is the right test for finishing a run and the wrong one for
a repository: the sheets already rendered keep their evidence, and a re-render of any of them now
builds a scene whose roadway is absent. 113 of the 289 pavement tiles a viewpoint's loader can
reach went missing that way, 71 of them named in a published record's own ``tiles_read``
(docs/DEVIATIONS.md J118).

So the rule is written down here instead of re-derived at the next squeeze:

* a tile may be deleted only when **no** catalogued viewpoint's loader for that class can reach it,
* measured against **each viewpoint's own radius**, not one flat number for the whole catalogue,
* and using **that class's** radius -- pavement and park ground are read within
  ``min(scene_radius, 900 m)`` however far the scene reaches, so the two 5 km views read four and
  six pavement tiles each,
* the class's source data has to be present, so the deletion is reversible,
* and the names go in a rebuild list that says what has to be rebuilt before a package is cut.

    python3 tools/tile_reach.py                      report every class
    python3 tools/tile_reach.py --missing pavement   the reachable tiles that are absent
    python3 tools/tile_reach.py --delete pavement    delete the unreachable ones, list them
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "pipeline"))

from nycsim_pipeline.crs import TILE_SIZE_M, lonlat_to_tm  # noqa: E402

TILES = REPO / "blender_out" / "tiles"
REFERENCE = REPO / "docs" / "verification" / "reference"
COMPARISON = REPO / "docs" / "verification" / "comparison"

#: The camera walk moves an eye point up to 80 m and ``pavement_candidates`` looks 70 m for a paved
#: surface, so a tile just outside a loader's radius can still be read after a correction. 200 m is
#: more than twice that and costs a handful of tiles.
WALK_MARGIN_M = 200.0

#: Per class: the artefact on disk, how its load radius is derived from the scene radius, the
#: source the rebuild reads, and the command that rebuilds one.  ``radius`` is a callable so a
#: class whose loader clamps the scene radius says so rather than having the number copied.
CLASSES: dict[str, dict] = {
    "pavement": {
        "artefact": "tile_pavement.glb",
        "extra": ("pavement_manifest.json",),
        # scene.py: add_pavement(cx, cy, min(radius_m, pavement_radius_m=900.0), ...)
        "radius": lambda r: min(r, 900.0),
        "source": REPO / "data" / "processed" / "roads" / "pavement",
        "source_glob": "{tile}.parquet",
        "rebuild": "python3 blender/roads/build_pavement.py --tiles {tiles} --workers 2",
        "rebuild_list": REPO / "docs" / "verification" / "pavement_rebuild_needed.txt",
    },
    "parkground": {
        "artefact": "tile_parkground.glb",
        "extra": (),
        # the park ground is gathered over the pavement's radius: the two are one surface
        "radius": lambda r: min(r, 900.0),
        "source": REPO / "data" / "processed" / "parks",
        "source_glob": None,
        "rebuild": "python3 blender/parks/build_parkground.py --tiles {tiles}",
        "rebuild_list": REPO / "docs" / "verification" / "parkground_rebuild_needed.txt",
    },
    "structures": {
        "artefact": "tile_structures.glb",
        "extra": ("structures_manifest.json",),
        "radius": lambda r: r,
        "source": REPO / "data" / "processed" / "runtime",
        "source_glob": None,
        "rebuild": "python3 blender/structures/build_structures.py --tiles {tiles}",
        "rebuild_list": REPO / "docs" / "verification" / "structures_rebuild_needed.txt",
    },
    "buildings": {
        "artefact": "tile_buildings.glb",
        "extra": ("manifest.json",),
        "radius": lambda r: r,
        "source": REPO / "data" / "processed" / "tiles",
        "source_glob": None,
        "rebuild": "python3 blender/buildings/build_tile.py --tiles {tiles}",
        "rebuild_list": REPO / "docs" / "verification" / "buildings_rebuild_needed.txt",
    },
    "buildings_nj": {
        "artefact": "tile_buildings_nj.glb",
        "extra": ("manifest_nj.json",),
        "radius": lambda r: r,
        "source": REPO / "data" / "processed" / "buildings_nj",
        "source_glob": None,
        "rebuild": "python3 blender/buildings/build_tile.py --new-jersey --tiles {tiles}",
        "rebuild_list": REPO / "docs" / "verification" / "buildings_nj_rebuild_needed.txt",
    },
}


def viewpoints() -> list[tuple[str, float, float, float]]:
    """``(slug, x, y, scene_radius_m)`` for every catalogued item with a photograph on disk.

    The radius is the one ``render_sheets`` will use, read from that module so the two cannot
    drift: ``RADIUS_OVERRIDES`` puts two items at 5,000 and 5,500 m, which is exactly the case a
    flat threshold got wrong.
    """
    import importlib.util
    import types

    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    for extra in (REPO / "blender" / "verify", REPO / "tools", REPO / "blender" / "common",
                  REPO / "services", REPO):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    spec = importlib.util.spec_from_file_location(
        "render_sheets_for_reach", REPO / "blender" / "verify" / "render_sheets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    overrides = getattr(mod, "RADIUS_OVERRIDES", {})

    out: list[tuple[str, float, float, float]] = []
    for d in sorted(REFERENCE.iterdir()):
        meta_path = d / "meta.json"
        if not d.is_dir() or not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        if not any((d / (p.get("file") or "")).is_file() for p in meta.get("photos", [])):
            continue
        vp = meta.get("viewpoint") or {}
        if vp.get("lat") is None or vp.get("lon") is None:
            continue
        vx, vy = (float(v) for v in lonlat_to_tm(vp["lon"], vp["lat"]))
        sub = meta.get("subject") or {}
        subj_dist = None
        if sub.get("lat") is not None and sub.get("lon") is not None:
            sx, sy = (float(v) for v in lonlat_to_tm(sub["lon"], sub["lat"]))
            subj_dist = math.hypot(sx - vx, sy - vy)
        if d.name in overrides:
            radius = float(overrides[d.name][0])
        else:
            radius = max(500.0, min(3000.0, (subj_dist or 200.0) * 1.6 + 400.0))
        out.append((d.name, vx, vy, radius))
    return out


def _tile_xy(name: str) -> tuple[int, int]:
    tx, ty = name[2:].split("_")
    return int(tx), int(ty)


def reach(name: str, views, radius_of) -> tuple[bool, float]:
    """Can any viewpoint's loader for this class reach tile ``name``?  Also the nearest distance."""
    tx, ty = _tile_xy(name)
    x0, x1 = tx * TILE_SIZE_M, (tx + 1) * TILE_SIZE_M
    y0, y1 = ty * TILE_SIZE_M, (ty + 1) * TILE_SIZE_M
    best = math.inf
    hit = False
    for _slug, vx, vy, scene_r in views:
        dx = max(x0 - vx, 0.0, vx - x1)
        dy = max(y0 - vy, 0.0, vy - y1)
        d = math.hypot(dx, dy)
        best = min(best, d)
        if d <= radius_of(scene_r) + WALK_MARGIN_M:
            hit = True
    return hit, best


def tiles_read_by_published_sheets() -> dict[str, set[str]]:
    """``class -> {tile}`` over every record's ``scene.<class>.tiles_read``."""
    out: dict[str, set[str]] = {k: set() for k in CLASSES}
    if not COMPARISON.is_dir():
        return out
    for d in sorted(COMPARISON.iterdir()):
        p = d / "render.json"
        if not p.is_file():
            continue
        try:
            rec = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        scene = rec.get("scene") or {}
        for cls in CLASSES:
            for tile in ((scene.get(cls) or {}).get("tiles_read") or []):
                out[cls].add(str(tile))
    return out


def survey(cls: str, views, read: set[str]) -> dict:
    spec = CLASSES[cls]
    radius_of = spec["radius"]
    present, absent = {}, []
    for d in sorted(TILES.iterdir()):
        if not d.is_dir() or not d.name.startswith("t_"):
            continue
        f = d / spec["artefact"]
        if f.is_file():
            present[d.name] = sum((d / n).stat().st_size
                                  for n in (spec["artefact"], *spec["extra"]) if (d / n).is_file())
    candidates = set(present)
    src = spec["source"]
    if spec["source_glob"] and src.is_dir():
        # A class whose source is one file per tile knows every tile that could have the artefact,
        # so a reachable tile that is absent can be named rather than merely missed.
        for p in src.glob(spec["source_glob"].format(tile="t_*")):
            candidates.add(p.stem)
    candidates |= read
    keep, drop, missing = [], [], []
    keep_b = drop_b = 0
    for name in sorted(candidates):
        try:
            _tile_xy(name)
        except (ValueError, IndexError):
            continue
        hit, _nearest = reach(name, views, radius_of)
        if name not in present:
            if hit:
                missing.append(name)
            continue
        if hit:
            keep.append(name)
            keep_b += present[name]
        else:
            drop.append(name)
            drop_b += present[name]
    return {"class": cls, "artefact": spec["artefact"], "keep": keep, "drop": drop,
            "missing": missing, "keep_bytes": keep_b, "drop_bytes": drop_b,
            "read_but_absent": sorted(t for t in read if t not in present)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--missing", metavar="CLASS", help="print the reachable tiles that are absent")
    ap.add_argument("--delete", metavar="CLASS",
                    help="delete the unreachable tiles of this class and add them to its rebuild list")
    ap.add_argument("--limit-mb", type=float, default=None,
                    help="with --delete, stop once this many MB have been freed (largest first), so "
                         "only the room actually needed is taken")
    a = ap.parse_args(argv)
    if not TILES.is_dir():
        print(f"no built tiles at {TILES}", file=sys.stderr)
        return 2
    for name in (a.missing, a.delete):
        if name is not None and name not in CLASSES:
            print(f"unknown class {name!r}; known: {', '.join(sorted(CLASSES))}", file=sys.stderr)
            return 2

    views = viewpoints()
    read = tiles_read_by_published_sheets()
    print(f"{len(views)} catalogued viewpoints, radii {min(v[3] for v in views):.0f} to "
          f"{max(v[3] for v in views):.0f} m, walk margin {WALK_MARGIN_M:.0f} m")

    if a.missing:
        s = survey(a.missing, views, read[a.missing])
        print(f"\n{a.missing}: {len(s['missing'])} reachable tile(s) absent from disk, "
              f"{len(s['read_but_absent'])} of them named in a published record's tiles_read")
        for name in s["missing"]:
            print(name)
        return 0

    if a.delete:
        s = survey(a.delete, views, read[a.delete])
        spec = CLASSES[a.delete]
        order = sorted(s["drop"],
                       key=lambda n: -sum((TILES / n / x).stat().st_size
                                          for x in (spec["artefact"], *spec["extra"])
                                          if (TILES / n / x).is_file()))
        freed = 0
        done: list[str] = []
        for name in order:
            if a.limit_mb is not None and freed >= a.limit_mb * 1e6:
                break
            for x in (spec["artefact"], *spec["extra"]):
                f = TILES / name / x
                if f.is_file():
                    freed += f.stat().st_size
                    f.unlink()
            done.append(name)
        listing = spec["rebuild_list"]
        was = set()
        if listing.is_file():
            was = {l.strip() for l in listing.read_text().split() if l.strip()}
        listing.write_text("\n".join(sorted(was | set(done))) + "\n")
        print(f"\n{a.delete}: deleted {len(done)} unreachable tile(s), freed {freed / 1e6:.0f} MB")
        print(f"rebuild list now {len(was | set(done))} tile(s): "
              f"{listing.relative_to(REPO)}")
        print("rebuild with:\n  " + spec["rebuild"].format(
            tiles=f"$(paste -sd, {listing.relative_to(REPO)})"))
        return 0

    total_drop = 0
    for cls in CLASSES:
        s = survey(cls, views, read[cls])
        total_drop += s["drop_bytes"]
        print(f"\n{cls:<14} {s['artefact']}")
        print(f"  reachable   {len(s['keep']):5d} tile(s) {s['keep_bytes'] / 1e6:9.0f} MB")
        print(f"  unreachable {len(s['drop']):5d} tile(s) {s['drop_bytes'] / 1e6:9.0f} MB  "
              f"(deletable, source at {CLASSES[cls]['source'].relative_to(REPO)})")
        if s["missing"]:
            print(f"  ABSENT      {len(s['missing']):5d} reachable tile(s) are not on disk, "
                  f"{len(s['read_but_absent'])} of them read by a published sheet (J118)")
    print(f"\ntotal unreachable across all classes: {total_drop / 1e6:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
