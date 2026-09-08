#!/usr/bin/env python3
"""For every reference viewpoint, is it on a street and does it look along one?

A drive-through sheet exists to compare a street. If the camera stands on a street and looks 68 deg
across it, the render is a picture of the buildings opposite and the sheet compares nothing --
`drive_brooklyn_bed_stuy_stuyvesant_ave` is that case, and no number the sheet printed said so. Both
halves of the question are answerable from the shipped road graph without rendering anything:

* how far the recorded viewpoint is from the nearest road centreline, and
* the angle between the item's own azimuth and that road's bearing, folded into 0-90 deg.

A viewpoint on a street looking along it scores a small angle. A viewpoint looking across one scores
near 90. Nothing here decides what is wrong -- an item may name a plaza, a bridge or a park on
purpose -- it only says which ones deserve a look.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point

REPO = Path("/home/user/Map-New-York")
REFERENCE = REPO / "docs" / "verification" / "reference"
CRS = "+proj=tmerc +lat_0=40.7 +lon_0=-73.95 +k=1 +units=m +datum=NAD83 +no_defs"
SEARCH_M = 60.0


def bearing_of(geom, at: Point) -> float:
    """Bearing of the two centreline vertices nearest ``at``, in degrees clockwise from north."""
    cs = np.asarray(geom.coords)
    if len(cs) < 2:
        return float("nan")
    d = np.hypot(cs[:, 0] - at.x, cs[:, 1] - at.y)
    i = int(np.argmin(d))
    j = i + 1 if i + 1 < len(cs) else i - 1
    v = cs[j] - cs[i]
    return math.degrees(math.atan2(v[0], v[1])) % 360.0


def fold(a: float, b: float) -> float:
    """Angle between two bearings, ignoring which way each points: 0-90 deg."""
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)


def main() -> int:
    seg = gpd.read_parquet(REPO / "data" / "processed" / "roads" / "segments.parquet")
    tr = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    rows = []
    for d in sorted(REFERENCE.iterdir()):
        meta = d / "meta.json"
        if not d.is_dir() or not meta.is_file():
            continue
        m = json.loads(meta.read_text())
        vp = m.get("viewpoint") or {}
        if vp.get("lat") is None or vp.get("azimuth_deg") is None:
            continue
        x, y = tr.transform(vp["lon"], vp["lat"])
        p = Point(x, y)
        near = seg[seg.geometry.distance(p) < SEARCH_M].copy()
        if near.empty:
            rows.append((d.name, None, None, None, None, vp.get("note", "")))
            continue
        # The street a camera is *aimed along* is not always the one it is standing closest to: at a
        # corner the nearest centreline is usually the cross street, and an item looking up the
        # avenue then scores 90 deg against it. Take the best-aligned street in range instead, and
        # report how far away that one is.
        az = float(vp["azimuth_deg"])
        best = None
        for _, r in near.iterrows():
            br = bearing_of(r.geometry, p)
            off = fold(az, br)
            dist = float(r.geometry.distance(p))
            if best is None or off < best[3]:
                best = (dist, str(r["street_name"]), br, off)
        rows.append((d.name, best[0], best[1], best[2], best[3], vp.get("note", "")))
    rows.sort(key=lambda t: (-(t[4] if t[4] is not None else -1)))
    print(f"{'slug':46s} {'road_m':>7s} {'street':22s} {'brg':>6s} {'off':>5s}")
    for slug, dist, name, br, off, note in rows:
        if dist is None:
            print(f"{slug:46s} {'  >120':>7s} {'(no road in range)':22s}")
            continue
        print(f"{slug:46s} {dist:7.1f} {name[:22]:22s} {br:6.1f} {off:5.1f}")
    bad = [r for r in rows if r[4] is not None and r[4] > 40.0]
    print(f"\n{len(bad)} of {len(rows)} viewpoints look more than 40 deg across their nearest street")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
