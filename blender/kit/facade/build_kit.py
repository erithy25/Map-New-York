#!/usr/bin/env python3
"""Build the NYCSim facade kit: every registered piece -> ``blender_out/kit/facade/<id>.glb`` + a catalog JSON.

    python3 blender/kit/facade/build_kit.py                 # all pieces
    python3 blender/kit/facade/build_kit.py --only win_ --dry-run
    python3 blender/kit/facade/build_kit.py --slice 0/4     # shard 0 of 4 (one Blender process per shard)

Runs headless through the ``bpy`` module (Blender 4.5 LTS). Objects are removed between pieces; materials, images and
the 1K texture cache are shared for the life of the process.
"""
from __future__ import annotations

import argparse
import json
import math
import logging
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import kitlib as K            # noqa: E402
import pieces_common as P     # noqa: E402
import facade_params as fp    # noqa: E402

log = logging.getLogger("nycsim.kit.facade.build")

PIECE_MODULES = ("pieces_windows", "pieces_accessories", "pieces_entries", "pieces_trim",
                 "pieces_storefront", "pieces_interiors", "pieces_roof", "pieces_street")


def load_pieces() -> None:
    import importlib
    for mod in PIECE_MODULES:
        importlib.import_module(mod)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=None, help="only pieces whose id starts with one of these prefixes")
    ap.add_argument("--slice", default=None, help="I/N — build shard I of N (deterministic by sorted id)")
    ap.add_argument("--dry-run", action="store_true", help="build geometry and report counts, do not export")
    ap.add_argument("--log", default="INFO")
    a = ap.parse_args(argv)
    logging.basicConfig(level=getattr(logging, a.log.upper()), format="%(levelname)s %(name)s: %(message)s")

    P.reg_flats()
    P.reg_generated_materials()
    load_pieces()
    ids = sorted(K.REGISTRY)
    if a.only:
        ids = [i for i in ids if any(i.startswith(p) for p in a.only)]
    if a.slice:
        i, n = (int(v) for v in a.slice.split("/"))
        ids = [x for k, x in enumerate(ids) if k % n == i]
    log.info("building %d pieces", len(ids))

    K.KIT_OUT.mkdir(parents=True, exist_ok=True)
    K.CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    rows, t0 = [], time.time()
    for n, pid in enumerate(ids, 1):
        piece = K.REGISTRY[pid]
        try:
            e = K.build_piece(piece, export=not a.dry_run)
        except Exception:
            log.exception("piece %s failed", pid)
            raise
        rows.append(e)
        pc = e["polycount"]
        flag = "" if pc["within_budget"] else "  ** OVER BUDGET **"
        dev = max((abs(m - nm) / nm if nm > 0 else 0.0) for m, nm in zip(e["measured_size_m"], e["nominal_size_m"]))
        log.info("[%3d/%3d] %-34s %-20s tris %5d/%5d  lod1 %4d (%.0f%%)  size %s dev %.1f%%%s", n, len(ids), pid,
                 e["category"], pc["lod0_triangles"], pc["budget"], pc["lod1_triangles"], 100 * pc["lod1_ratio"],
                 "x".join(f"{v:.2f}" for v in e["measured_size_m"]), 100 * dev, flag)
        K.unlink_all_pieces()

    over = [r for r in rows if not r["polycount"]["within_budget"]]
    # a mesh of n triangles cannot have an LOD below 2 triangles, so the ratio rule is
    # lod1 <= max(2, 25 % of LOD0) — binding for every piece above 8 triangles.
    bad_lod = [r for r in rows if r["polycount"]["lod1_triangles"] > max(2, math.ceil(0.25 * r["polycount"]["lod0_triangles"]))]
    bad_size = [r for r in rows if max((abs(m - nm) / nm if nm > 0 else 0.0)
                                       for m, nm in zip(r["measured_size_m"], r["nominal_size_m"])) > 0.05]
    src = "as exported (glb)" if not a.dry_run else "as modelled (Blender polygons; the exporter drops degenerate faces)"
    print(f"\n{len(rows)} pieces in {time.time() - t0:.0f} s"
          f"\n  triangles LOD0 total {sum(r['polycount']['lod0_triangles'] for r in rows)} ({src})"
          f"\n  over budget : {[r['id'] for r in over]}"
          f"\n  LOD1 > 25 % : {[r['id'] for r in bad_lod]}"
          f"\n  size dev>5 %: {[(r['id'], r['nominal_size_m'], r['measured_size_m']) for r in bad_size]}")
    if not a.dry_run:
        (K.CATALOG_DIR.parent / "facade_params.json").write_text(json.dumps(fp.as_contract_dict(), indent=1))
    return 1 if (over or bad_lod or bad_size) else 0


if __name__ == "__main__":
    sys.exit(main())
