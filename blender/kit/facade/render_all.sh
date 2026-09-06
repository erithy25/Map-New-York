#!/bin/sh
# All facade-kit verification renders, one Blender process at a time (4 shared vCPUs).
#   sh blender/kit/facade/render_all.sh [samples] [sheet_res]
set -e
cd "$(dirname "$0")/../../.."
S=${1:-64}
R=${2:-800}
nice -n 10 python3 blender/kit/facade/render_sheets.py --tenement --samples "$S" --res 800
nice -n 10 python3 blender/kit/facade/render_sheets.py --closeup --samples "$S" --res 900
for g in windows accessories entries trim storefront interiors roof rooftop_equipment street; do
  nice -n 10 python3 blender/kit/facade/render_sheets.py --sheet "$g" --samples "$S" --res "$R"
done
