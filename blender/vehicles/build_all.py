#!/usr/bin/env python3
"""Build the whole vehicle fleet, one Blender process, sequentially.

    nice -n 10 python3 blender/vehicles/build_all.py            # everything
    nice -n 10 python3 blender/vehicles/build_all.py --only camry_taxi_yellow,nova_lfs_mta
    nice -n 10 python3 blender/vehicles/build_all.py --list

Each vehicle is built in a fresh factory scene, exported to ``blender_out/vehicles/<id>.glb`` (plus
``<id>_LOD1.glb`` / ``<id>_LOD2.glb``) and given a catalog entry in ``blender_out/vehicles/catalog/<id>.json``.
The run prints a table of triangle counts and dimension deviations and writes
``blender_out/vehicles/catalog/_build_summary.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vlib import env  # noqa: E402

env.setup_logging()

import build_fusion as BF  # noqa: E402
import fleet_big as FB  # noqa: E402
import fleet_cars as FC  # noqa: E402
import fleet_small as FS  # noqa: E402
from vlib import fleetlib as F, geom as g  # noqa: E402

log = env.log

#: build order: the player car first (it is the reference for the shared library), then the fleet
FLEET = {
    **{k: ("cars", v) for k, v in FC.ALL.items()},
    **{k: ("big", v) for k, v in FB.ALL.items()},
    **{k: ("small", v) for k, v in FS.ALL.items()},
}


def build_player(liveries: str = "all") -> list[dict]:
    wanted = list(BF.LIVERIES) if liveries == "all" else liveries.split(",")
    v, ctx = BF.build()
    tris = g.tri_count_all([o for o in v.objects.values()
                            if o.type == "MESH" and not o.name.startswith("UCX_")])
    if tris > 350_000:
        raise RuntimeError(f"player car LOD0 {tris} tris over the 350000 budget")
    out = []
    for livery in wanted:
        BF.apply_livery(v, ctx, livery)
        out.append(BF.rig.finalise(v, lod_budgets=(60_000, 8_000),
                                   exterior_names=[n for n in BF.EXTERIOR if n in v.objects],
                                   extra_catalog={"build_timings_s": ctx["timings"]}))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="", help="comma-separated vehicle ids")
    ap.add_argument("--skip", default="", help="comma-separated vehicle ids to skip")
    ap.add_argument("--liveries", default="all")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--keep-going", action="store_true", help="log and continue when one vehicle fails")
    args = ap.parse_args()
    if args.list:
        print("fusion_hybrid (+ liveries: " + ", ".join(BF.LIVERIES) + ")")
        for k, (grp, _) in FLEET.items():
            print(f"{k}  [{grp}]")
        return 0
    env.ensure_dirs()
    only = {i.strip() for i in args.only.split(",") if i.strip()}
    skip = {i.strip() for i in args.skip.split(",") if i.strip()}
    entries: list[dict] = []
    failures: list[tuple[str, str]] = []
    t0 = time.perf_counter()

    if (not only or {"fusion_hybrid", *BF.LIVERIES} & only) and "fusion_hybrid" not in skip:
        try:
            entries += build_player(args.liveries)
        except Exception as exc:
            if not args.keep_going:
                raise
            failures.append(("fusion_hybrid", f"{exc}"))
            log.error("fusion build failed: %s\n%s", exc, traceback.format_exc())

    for vid, (grp, factory) in FLEET.items():
        if (only and vid not in only) or vid in skip:
            continue
        t = time.perf_counter()
        try:
            if grp == "small":
                entries.append(factory())
            else:
                entries.append(F.build_and_export(factory()))
            log.info("%s done in %.1f s", vid, time.perf_counter() - t)
        except Exception as exc:
            if not args.keep_going:
                raise
            failures.append((vid, f"{exc}"))
            log.error("%s failed: %s\n%s", vid, exc, traceback.format_exc())

    total = time.perf_counter() - t0
    print(f"\n{'id':<26s} {'class':<10s} {'LOD0':>8s} {'LOD1':>7s} {'LOD2':>6s}   dev L/W/H %")
    print("-" * 78)
    for e in sorted(entries, key=lambda e: (e["class"], e["id"])):
        d = e["dimension_deviation_pct"]
        print(f"{e['id']:<26s} {e['class']:<10s} {e['triangles']:>8d} {e['lods'][1]['triangles']:>7d} "
              f"{e['lods'][2]['triangles']:>6d}   {d['length_pct']:+.2f}/{d['width_pct']:+.2f}/{d['height_pct']:+.2f}")
    print("-" * 78)
    print(f"{len(entries)} vehicles, {sum(e['triangles'] for e in entries):,} LOD0 triangles, {total:.1f} s")
    if failures:
        print("\nFAILED:")
        for vid, msg in failures:
            print(f"  {vid}: {msg}")
    summary = {
        "schema_version": 1,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seconds": round(total, 1),
        "count": len(entries),
        "total_lod0_triangles": sum(e["triangles"] for e in entries),
        "vehicles": [{"id": e["id"], "class": e["class"], "triangles": e["triangles"],
                      "lod1": e["lods"][1]["triangles"], "lod2": e["lods"][2]["triangles"],
                      "deviation_pct": e["dimension_deviation_pct"],
                      "waivers": sorted(e.get("contract_waivers", {}))} for e in entries],
        "failures": [{"id": v, "error": m} for v, m in failures],
    }
    (env.CATALOG_DIR / "_build_summary.json").write_text(json.dumps(summary, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    code = main()
    env.finish(code)
