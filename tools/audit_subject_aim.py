#!/usr/bin/env python3
"""Is each landmark viewpoint aimed at its own subject, and is the subject where the item says?

Two independent things can be wrong and neither shows up in any number a sheet prints.

* The **aim**: the item records an azimuth and a subject coordinate. If the bearing from the
  viewpoint to the subject differs from the recorded azimuth by more than the frame's half-angle,
  the subject is out of frame and the sheet compares two pictures of different things.
* The **subject coordinate itself**: `docs/verification/reference/<slug>/meta.json` gives a lat/lon
  for the subject, and `data/processed/landmarks/landmarks.json` gives the model's own origin. Where
  a slug names a landmark the build models, the two should agree. Washington Square Arch is the
  known case (I12): its recorded subject sits 15.0 m from the Arch model's origin, which at 39 m
  aims the render 15.8 deg off the thing it is a picture of.

Nothing here decides what is wrong. It says which items deserve a look, with the number that says why.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from pyproj import Transformer

REPO = Path("/home/user/Map-New-York")
REFERENCE = REPO / "docs" / "verification" / "reference"
CRS = "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +units=m +datum=NAD83 +no_defs"
#: half the horizontal frame of a default 35 mm landscape sheet, which is what most landmarks use
DEFAULT_HALF_FOV_DEG = 27.2


def main() -> int:
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    lm = json.loads((REPO / "data" / "processed" / "landmarks" / "landmarks.json").read_text())
    models = {r["name"].strip().lower(): r for r in (lm.get("landmarks") or lm) if r.get("name")}

    rows = []
    for d in sorted(REFERENCE.iterdir()):
        meta = d / "meta.json"
        if not d.is_dir() or not meta.is_file():
            continue
        j = json.loads(meta.read_text())
        vp, subj = j.get("viewpoint") or {}, j.get("subject")
        if not subj or vp.get("azimuth_deg") is None:
            continue
        vx, vy = tr.transform(vp["lon"], vp["lat"])
        sx, sy = tr.transform(subj["lon"], subj["lat"])
        dx, dy = sx - vx, sy - vy
        dist = math.hypot(dx, dy)
        bearing = math.degrees(math.atan2(dx, dy)) % 360.0
        off = abs((bearing - float(vp["azimuth_deg"]) + 180.0) % 360.0 - 180.0)
        m = models.get(str(subj.get("name", "")).strip().lower())
        model_gap = None
        if m and m.get("origin_tm"):
            ox, oy = m["origin_tm"][0], m["origin_tm"][1]
            model_gap = math.hypot(sx - ox, sy - oy)
        rows.append((d.name, dist, off, model_gap, subj.get("name")))

    rows.sort(key=lambda r: -r[2])
    print(f"{'slug':44s} {'dist_m':>7s} {'off_deg':>8s} {'model_m':>8s}  subject")
    for slug, dist, off, gap, name in rows:
        flag = "  <-- out of frame" if off > DEFAULT_HALF_FOV_DEG else ""
        g = f"{gap:8.1f}" if gap is not None else "       -"
        print(f"{slug:44s} {dist:7.0f} {off:8.1f} {g}  {str(name)[:30]}{flag}")

    out = [r for r in rows if r[2] > DEFAULT_HALF_FOV_DEG]
    print(f"\n{len(out)} of {len(rows)} subjects fall outside a default {2 * DEFAULT_HALF_FOV_DEG:.0f} deg frame")

    # A gap between the recorded subject and the model's origin only matters as an ANGLE at the
    # render distance: the azimuth is derived from the recorded coordinate, so the model lands that
    # far off the centre of the frame. Washington Square Arch is the known case (I12) at 15.8 deg.
    swing = []
    for slug, dist, off, gap, name in rows:
        if gap is None or dist <= 0:
            continue
        swing.append((math.degrees(math.atan2(gap, dist)), slug, dist, gap, name))
    swing.sort(reverse=True)
    print("\nhow far off the centre of its own frame each modelled subject lands:")
    print(f"{'slug':44s} {'off_ctr':>8s} {'dist_m':>7s} {'gap_m':>7s}  subject")
    for deg, slug, dist, gap, name in swing[:16]:
        mark = "  <-- outside the frame" if deg > DEFAULT_HALF_FOV_DEG else (
               "  <-- off centre" if deg > 12.0 else "")
        print(f"{slug:44s} {deg:8.1f} {dist:7.0f} {gap:7.0f}  {str(name)[:26]}{mark}")
    bad = [s for s in swing if s[0] > DEFAULT_HALF_FOV_DEG]
    mid = [s for s in swing if 12.0 < s[0] <= DEFAULT_HALF_FOV_DEG]
    print(f"\n{len(bad)} modelled subjects land outside the frame the item aims; "
          f"{len(mid)} more land more than 12 deg off its centre, of {len(swing)} with a model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
