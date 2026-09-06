"""Offline derivation of the Manhattan street-grid azimuth from the DCP LION centrelines.

This is *not* part of the runtime service (the engine only needs the constant
:data:`nycsim_live.astronomy.MANHATTAN_STREET_SUNSET_AZIMUTH_DEG`); it is the reproducible derivation of
that constant from real data, run once and recorded in ``docs/verification/live/REPORT.md`` and
``docs/LIVE_ALGORITHMS.md`` §2.5. ``pyogrio``/``pyproj``/``shapely`` are imported lazily so importing the
live package never pulls in the geo stack.

Method
------
1. Read every LION segment with ``LBoro = '1'`` (Manhattan) and ``FeatureTyp = '0'`` (real street centreline,
   excluding shorelines, boundaries, rail and other non-street features).
2. Keep the numbered cross-streets of the regular Commissioners'-Plan grid: names matching
   ``(WEST|EAST) n STREET`` with 14 ≤ n ≤ 96 (below 14th the colonial street pattern takes over; above 96th
   the grid continues but the streets are broken by Morningside/Harlem topography and the park transverses).
3. Reproject each segment's end points EPSG:2263 → WGS84 and take the **geodesic** forward azimuth from the
   western to the eastern end (`pyproj.Geod(ellps="WGS84").inv`). Working in the projected plane instead
   would carry the State-Plane meridian convergence (≈ 0.013° here) into the answer.
4. Drop segments shorter than 60 m (kerb stubs and jug handles) and any bearing more than 12° from 119°
   (ramps, service roads and the Broadway diagonal crossing a numbered street's name).
5. Report the length-weighted mean, median and quantiles; the sunset azimuth is the median + 180°.

Run: ``python -m nycsim_live.grid_azimuth [--gdb PATH] [--json OUT]``
"""
from __future__ import annotations

import argparse
import collections
import json
import logging
import math
import re
from pathlib import Path
from typing import Any, Final

from .paths import REPO_ROOT

log = logging.getLogger("nycsim.live.grid_azimuth")

LION_GDB: Final = REPO_ROOT / "data" / "raw" / "lion" / "lion" / "lion.gdb"
STREET_RE: Final = re.compile(r"^(WEST|EAST)\s+(\d{1,3})\s+STREET$")
MIN_STREET: Final = 14
MAX_STREET: Final = 96
MIN_SEGMENT_M: Final = 60.0
NOMINAL_BEARING_DEG: Final = 119.0
BEARING_TOLERANCE_DEG: Final = 12.0
FAMOUS_STREETS: Final = (14, 23, 34, 42, 57, 79)


def _weighted_quantile(values: list[float], weights: list[float], q: float) -> float:
    pairs = sorted(zip(values, weights))
    total = sum(weights)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc / total >= q:
            return v
    return pairs[-1][0]


def segment_bearings(gdb: Path = LION_GDB) -> list[tuple[int, float, float]]:
    """[(street number, geodesic east-looking bearing in degrees true, segment length in metres)]."""
    import pyogrio  # noqa: PLC0415 - lazy: the geo stack is not a runtime dependency
    import pyproj  # noqa: PLC0415
    from shapely import get_coordinates  # noqa: PLC0415

    gdf = pyogrio.read_dataframe(str(gdb), layer="lion", columns=["Street", "FeatureTyp", "LBoro"], where="LBoro = '1' AND FeatureTyp = '0'")
    geod = pyproj.Geod(ellps="WGS84")
    to_wgs = pyproj.Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    out: list[tuple[int, float, float]] = []
    for name, geom in zip(gdf["Street"], gdf.geometry):
        if geom is None:
            continue
        m = STREET_RE.match((name or "").strip().upper())
        if not m:
            continue
        n = int(m.group(2))
        if not MIN_STREET <= n <= MAX_STREET:
            continue
        parts = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        for part in parts:
            c = get_coordinates(part)
            if len(c) < 2:
                continue
            x0, y0 = c[0]
            x1, y1 = c[-1]
            if x1 < x0:  # orient west -> east so the bearing is the east-looking one
                x0, y0, x1, y1 = x1, y1, x0, y0
            lon0, lat0 = to_wgs.transform(x0, y0)
            lon1, lat1 = to_wgs.transform(x1, y1)
            az, _, dist = geod.inv(lon0, lat0, lon1, lat1)
            if dist < MIN_SEGMENT_M:
                continue
            az %= 360.0
            if abs(az - NOMINAL_BEARING_DEG) > BEARING_TOLERANCE_DEG:
                continue
            out.append((n, az, dist))
    return out


def summarise(rows: list[tuple[int, float, float]]) -> dict[str, Any]:
    az = [r[1] for r in rows]
    w = [r[2] for r in rows]
    total = sum(w)
    mean = sum(a * ww for a, ww in zip(az, w)) / total
    doc: dict[str, Any] = {
        "source": "NYC DCP LION street centrelines (data/raw/lion/lion/lion.gdb, layer 'lion')",
        "selection": f"LBoro='1' AND FeatureTyp='0'; names (WEST|EAST) n STREET with {MIN_STREET} <= n <= {MAX_STREET}; segment >= {MIN_SEGMENT_M:.0f} m; |bearing-{NOMINAL_BEARING_DEG:.0f}| <= {BEARING_TOLERANCE_DEG:.0f} deg",
        "segments": len(rows),
        "total_length_km": round(total / 1000.0, 3),
        "bearing_mean_deg": round(mean, 4),
        "bearing_median_deg": round(_weighted_quantile(az, w, 0.5), 4),
        "bearing_q25_deg": round(_weighted_quantile(az, w, 0.25), 4),
        "bearing_q75_deg": round(_weighted_quantile(az, w, 0.75), 4),
        "bearing_p05_deg": round(_weighted_quantile(az, w, 0.05), 4),
        "bearing_p95_deg": round(_weighted_quantile(az, w, 0.95), 4),
    }
    doc["grid_rotation_east_of_north_deg"] = round(doc["bearing_median_deg"] - 90.0, 4)
    doc["sunset_azimuth_deg"] = round(doc["bearing_median_deg"] + 180.0, 4)
    per: dict[int, list[tuple[float, float]]] = collections.defaultdict(list)
    for n, a, d in rows:
        per[n].append((a, d))
    doc["per_street"] = {
        str(n): {
            "segments": len(per[n]),
            "length_km": round(sum(d for _, d in per[n]) / 1000.0, 3),
            "bearing_median_deg": round(_weighted_quantile([a for a, _ in per[n]], [d for _, d in per[n]], 0.5), 4),
        }
        for n in FAMOUS_STREETS
        if n in per
    }
    doc["circular_std_deg"] = round(math.degrees(math.sqrt(sum(ww * math.radians(a - mean) ** 2 for a, ww in zip(az, w)) / total)), 4)
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nycsim_live.grid_azimuth", description=__doc__)
    ap.add_argument("--gdb", type=Path, default=LION_GDB)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rows = segment_bearings(args.gdb)
    if not rows:
        log.error("no LION cross-street segments matched in %s", args.gdb)
        return 1
    doc = summarise(rows)
    print(json.dumps(doc, indent=1))
    if args.json:
        from .paths import write_json_atomic

        write_json_atomic(args.json, doc)
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
