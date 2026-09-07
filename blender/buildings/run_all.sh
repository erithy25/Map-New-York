#!/usr/bin/env bash
# Full-city building-shell build: every tile in data/processed/tiles, then the merged L2/L3 tiers.
#
#   bash blender/buildings/run_all.sh              # 2 workers, LOD 0,1,2, resumable
#   WORKERS=4 bash blender/buildings/run_all.sh    # on a machine that is not shared
#   LODS=0 bash blender/buildings/run_all.sh       # LOD0 only (about 55 % of the bytes)
#
# Measured cost, whole city with stepped massing (this container, 4 vCPU shared with other agents):
#   920 tiles / 1,083,026 buildings, 844 at --lod 0,1 and 76 at --lod 0,1,2
#   CPU        7,517 worker-seconds = 2.09 CPU-hours
#   Wall clock ~63 min with 2 workers
#   Disk       3.8 kB per building = 4.12 GB (the earlier 5.4 kB/building was measured on a
#              76-tile, LOD0+LOD1+LOD2, Manhattan-weighted subset; the city is mostly houses)
#   Merged     L2 (4 km cells) + L3 (16 km cells, >= 40 m) add ~18 min and ~844 MB
#   Steps      184,373 buildings ship real stepped massing; 0 open shells at LOD0
#
# The run is resumable: --skip-existing leaves any tile that already has both
# tile_buildings.glb and manifest.json alone, so re-running after an interruption continues.
set -euo pipefail

cd "$(dirname "$0")/../.."
WORKERS="${WORKERS:-2}"
LODS="${LODS:-0,1,2}"
NICE="${NICE:-10}"
OUT="${OUT:-blender_out/tiles}"
ATTRS="${ATTRS:-full}"
RIDGE="${RIDGE:-clamp}"

FREE_GB=$(df -BG --output=avail . | tail -1 | tr -dc '0-9')
echo "free disk: ${FREE_GB} GB (the full LOD0+LOD1+LOD2 city needs about 6 GB)"
if [ "${FREE_GB}" -lt 8 ]; then
  echo "WARNING: less than 8 GB free. Use LODS=0 (~3.2 GB) or free space first." >&2
fi

echo "=== per-tile shells: workers=${WORKERS} lods=${LODS} attrs=${ATTRS} ==="
nice -n "${NICE}" python3 blender/buildings/build_tile.py \
  --all --workers "${WORKERS}" --lod "${LODS}" --attrs "${ATTRS}" \
  --ridge-mode "${RIDGE}" --out "${OUT}" --skip-existing

echo "=== merged L2 (4 km) and L3 (16 km, buildings >= 40 m) ==="
nice -n "${NICE}" python3 blender/buildings/build_lod_merged.py --all --level 2,3

echo "=== summary ==="
python3 - <<'PY'
import json, glob, os
tot = {"tiles": 0, "buildings": 0, "lod0": 0, "lod1": 0, "lod2": 0, "bytes": 0, "open": 0, "seconds": 0.0}
for p in glob.glob("blender_out/tiles/*/manifest.json"):
    m = json.load(open(p))
    tot["tiles"] += 1
    tot["buildings"] += m["buildings"]["solids"]
    for k in ("lod0", "lod1", "lod2"):
        tot[k] += m["triangles"].get(k, 0)
    tot["bytes"] += m["glb"]["bytes"]
    tot["open"] += m["buildings"]["open_shells_lod0"]
    tot["seconds"] += m["seconds"]["total"]
print(json.dumps(tot, indent=1))
print("GB", round(tot["bytes"] / 1e9, 2), "| CPU hours", round(tot["seconds"] / 3600, 2),
      "| bytes/building", round(tot["bytes"] / max(tot["buildings"], 1)))
PY
