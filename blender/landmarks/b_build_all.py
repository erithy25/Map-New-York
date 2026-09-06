"""Build every B landmark, one Blender process at a time (the machine is shared: 4 vCPU, ``nice -n 10``).

Usage
-----
    nice -n 10 python3 blender/landmarks/b_build_all.py                 # LOD0 + LOD1, no renders
    nice -n 10 python3 blender/landmarks/b_build_all.py --render        # also render every verification view
    nice -n 10 python3 blender/landmarks/b_build_all.py --only b_brooklyn_bridge b_wtc_site

Each landmark runs in its own subprocess so a failure in one cannot leave a half-built scene behind, and so that peak
memory stays at one model.  A summary table (triangles, bytes, wall time, exit status) is printed at the end and
written to ``docs/verification/landmarks/build_summary.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VERIFY = REPO / "docs" / "verification" / "landmarks"

LANDMARKS = [
    # bridges
    "b_brooklyn_bridge", "b_manhattan_bridge", "b_williamsburg_bridge", "b_queensboro_bridge",
    "b_george_washington_bridge", "b_verrazzano_narrows", "b_rfk_triborough", "b_throgs_neck",
    "b_bronx_whitestone", "b_hell_gate", "b_high_bridge", "b_pulaski", "b_kosciuszko",
    "b_roosevelt_island_tram",
    # tunnels
    "b_lincoln_tunnel_portals", "b_holland_tunnel_portals", "b_queens_midtown_portals", "b_hugh_carey_portals",
    # World Trade Center
    "b_one_world_trade_center", "b_wtc_site",
    # harbour
    "b_statue_of_liberty", "b_ellis_island_main", "b_governors_island",
    # parks and monuments
    "b_washington_square_arch", "b_bethesda_terrace", "b_bow_bridge", "b_belvedere_castle",
    "b_central_park_walls_gates", "b_unisphere", "b_grants_tomb", "b_columbus_circle_monument",
    "b_soldiers_sailors_arch", "b_prospect_park_boathouse",
    # Coney Island
    "b_coney_island",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="also produce the Cycles verification renders")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--lod0-only", action="store_true")
    ap.add_argument("--timeout", type=int, default=2400)
    a = ap.parse_args()
    todo = a.only or LANDMARKS
    results = []
    for name in todo:
        script = HERE / f"{name}.py"
        if not script.exists():
            results.append({"id": name, "status": "missing script"})
            print(f"!! {name}: no script", flush=True)
            continue
        cmd = [sys.executable, str(script), f"--samples={a.samples}"]
        if not a.render:
            cmd.append("--no-render")
        if a.lod0_only:
            cmd.append("--lod0-only")
        t0 = time.time()
        try:
            env = dict(os.environ, NYCSIM_LANDMARK_HARD_EXIT="1")
            p = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=a.timeout, env=env)
            rc = p.returncode
            tail = "\n".join((p.stderr or "").strip().splitlines()[-4:])
        except subprocess.TimeoutExpired:
            rc, tail = -1, f"timed out after {a.timeout} s"
        dt = time.time() - t0
        cat = REPO / "blender_out" / "landmarks" / "catalog" / f"{name}.json"
        lods = {}
        if cat.exists():
            try:
                lods = {k: {"triangles": v["triangles"], "bytes": v["bytes"]}
                        for k, v in json.load(open(cat)).get("lods", {}).items()}
            except (OSError, json.JSONDecodeError, KeyError):
                lods = {}
        results.append({"id": name, "returncode": rc, "seconds": round(dt, 1), "lods": lods,
                        "stderr_tail": "" if rc == 0 else tail})
        status = "ok " if rc == 0 else "FAIL"
        tris = " ".join(f"{k}={v['triangles']}" for k, v in sorted(lods.items()))
        print(f"{status} {name:<34} {dt:7.1f}s  {tris}", flush=True)
        if rc != 0:
            print(tail, flush=True)
    VERIFY.mkdir(parents=True, exist_ok=True)
    with open(VERIFY / "build_summary.json", "w") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "rendered": bool(a.render), "samples": a.samples, "results": results}, f, indent=1)
    bad = [r for r in results if r.get("returncode") not in (0,)]
    print(f"\n{len(results) - len(bad)}/{len(results)} landmarks built; summary -> "
          f"{(VERIFY / 'build_summary.json').relative_to(REPO)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
