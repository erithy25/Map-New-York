#!/bin/sh
# Rebuild and re-render every landmark of agent A's group (Midtown / Downtown towers, civic buildings, Grand Central).
#
# Each script is a self-contained Blender job: it loads its real footprint, builds the model, validates it
# (footprint IoU > 0.9, height within 1 %, triangle budget, LOD1 <= 20 %), exports
# blender_out/landmarks/<id>.glb + blender_out/landmarks/catalog/<id>.json, records the artefact in
# data/manifest/processed.json, and renders its verification stills into docs/verification/landmarks/.
#
# Runs one Blender process at a time, `nice`d, because the box has 4 vCPU shared with the other agents.
# The full pass does not fit in ~40 CPU-minutes: building all 20 models takes about 8 CPU-minutes, but the
# 44 Cycles stills at 64 samples / 1280x720 take 3-5 CPU-hours on a contended box. Environment overrides:
#
#   NYCSIM_LANDMARK_NO_RENDER=1   build, validate and export only — no stills (about 8 minutes for all 20)
#   NYCSIM_RENDER_FAST=1          16 samples at half size, for iterating on proportions
#   NYCSIM_LANDMARK_TEXTURES=0    flat documented Principled albedos instead of the CC0 PBR sets
#   NYCSIM_LANDMARK_TEXTURE_RES   texture resolution to pull from blender/common/textures.py (default 1K)
#
# Usage:  sh blender/landmarks/run_landmarks_a.sh [landmark_id ...]     (default: all of agent A's set)
set -e
cd "$(dirname "$0")/../.." || exit 1

ALL="empire_state chrysler flatiron one_vanderbilt 30_rockefeller_plaza st_patricks_cathedral \
grand_central_terminal new_york_public_library madison_square_garden woolworth municipal_building city_hall \
trinity_church nyse charging_bull federal_hall 40_wall_street one_wall_street equitable_building moma"

LIST="${*:-$ALL}"
fail=0
for id in $LIST; do
    script="blender/landmarks/$id.py"
    if [ ! -f "$script" ]; then
        echo "!! no such landmark script: $script" >&2
        fail=1
        continue
    fi
    echo "=== $id ==="
    if nice -n 10 python3 "$script"; then
        :
    else
        echo "!! $id FAILED" >&2
        fail=1
    fi
done
exit "$fail"
