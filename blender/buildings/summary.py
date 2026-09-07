#!/usr/bin/env python3
"""Aggregate every per-tile manifest into one stage summary.

    python3 blender/buildings/summary.py                     # -> docs/verification/buildings_mesh/summary.json

Also extrapolates the whole-city cost from the tiles actually built, using the real per-tile row
counts in ``data/processed/buildings/tiles_index.json``, so the projection is a measured
buildings-per-second and bytes-per-building rate rather than a guess.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE))

import tiledata as td  # noqa: E402

OUT = REPO_ROOT / "docs" / "verification" / "buildings_mesh" / "summary.json"
TILES_INDEX = REPO_ROOT / "data" / "processed" / "buildings" / "tiles_index.json"


def collect(tiles_root: Path) -> dict:
    mans = sorted(tiles_root.glob("*/manifest.json"))
    tot = Counter()
    seconds = Counter()
    materials = Counter()
    roof_src = Counter()
    mat_src = Counter()
    steps = Counter()
    per_tile = []
    for p in mans:
        m = json.loads(p.read_text())
        b = m["buildings"]
        tot["tiles"] += 1
        tot["rows_in"] += b.get("rows_in", 0)
        tot["solids"] += b["solids"]
        tot["dropped"] += b.get("dropped_empty_footprint", 0)
        tot["fallback_flat_cap"] += b.get("fallback_flat_cap", 0)
        tot["fallback_massing"] += b.get("fallback_massing", 0)
        tot["lod1_uses_massing"] += b.get("lod1_uses_massing", 0)
        tot["open_shells"] += b.get("open_shells_lod0", 0)
        for k in ("lod0", "lod1", "lod2"):
            tot[k] += m["triangles"].get(k, 0)
            tot["v_" + k] += m["vertices"].get(k, 0)
        tot["bytes"] += m["glb"]["bytes"]
        for k, v in m["seconds"].items():
            seconds[k] += v
        for name, rec in m["materials"].items():
            materials[name] += rec["triangles"]
        roof_src.update(m["sources"]["roof"])
        mat_src.update(m["sources"]["material"])
        rs = m.get("roof_steps") or {}
        for k, v in rs.items():
            if isinstance(v, int):
                steps[k] += v
        if rs.get("shipped", 0) > 0:
            steps["tiles_with_stepped_buildings"] += 1
        per_tile.append({"tile": m["tile"], "buildings": b["solids"],
                         "lod0": m["triangles"]["lod0"], "lod1": m["triangles"].get("lod1", 0),
                         "lod2": m["triangles"].get("lod2", 0), "bytes": m["glb"]["bytes"],
                         "seconds": m["seconds"]["total"],
                         "bounds_world_m": m["bounds_world_m"]})
    return {"totals": dict(tot), "seconds": dict(seconds), "materials": dict(materials.most_common()),
            "roof_sources": dict(roof_src.most_common()), "material_sources": dict(mat_src.most_common()),
            # `shipped` is the delivery: a stepped solid that would not close is rebuilt flat and
            # counted in `lost_would_not_close`, not here
            "roof_steps": dict(sorted(steps.items())), "per_tile": per_tile}


def project_city(summary: dict) -> dict:
    t = summary["totals"]
    if not t.get("solids"):
        return {}
    city_rows = 0
    city_tiles = 0
    if TILES_INDEX.exists():
        idx = json.loads(TILES_INDEX.read_text())["tiles"]
        city_tiles = len(idx)
        city_rows = sum(v["rows"] for v in idx.values())
    else:
        city_tiles = len(td.available_tiles())
    scale = city_rows / t["solids"] if city_rows else 0.0
    total_s = summary["seconds"].get("total", 0.0)
    return {
        "city_tiles": city_tiles,
        "city_buildings": city_rows,
        "sample_tiles": t["tiles"],
        "sample_buildings": t["solids"],
        "sample_fraction": round(t["solids"] / city_rows, 4) if city_rows else None,
        "measured_bytes_per_building": round(t["bytes"] / t["solids"], 1),
        "measured_seconds_per_building": round(total_s / t["solids"], 5),
        "measured_triangles_per_building_lod0": round(t["lod0"] / t["solids"], 2),
        "projected_city_bytes": int(t["bytes"] * scale),
        "projected_city_gb": round(t["bytes"] * scale / 1e9, 2),
        "projected_city_cpu_hours": round(total_s * scale / 3600, 2),
        "projected_city_wallclock_hours_2_workers": round(total_s * scale / 3600 / 2, 2),
        "projected_city_triangles_lod0": int(t["lod0"] * scale),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles-root", default=str(REPO_ROOT / "blender_out" / "tiles"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    s = collect(Path(args.tiles_root))
    s["projection"] = project_city(s)
    s["schema_version"] = 1
    s["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    s["tiles_root"] = args.tiles_root
    td.write_json(Path(args.out), s)
    t = s["totals"]
    print(f"tiles={t.get('tiles', 0)} buildings={t.get('solids', 0)} "
          f"lod0={t.get('lod0', 0)} lod1={t.get('lod1', 0)} lod2={t.get('lod2', 0)} "
          f"bytes={t.get('bytes', 0)} open_shells={t.get('open_shells', 0)}")
    if s["projection"]:
        p = s["projection"]
        print(f"city projection: {p['projected_city_gb']} GB, {p['projected_city_cpu_hours']} CPU-hours, "
              f"{p['measured_bytes_per_building']} B/building")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
