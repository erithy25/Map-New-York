"""Ferry routes and landings from published GTFS feeds.

Two feeds cover every scheduled passenger ferry inside the project scope, and both are real GTFS — no terminal
coordinate in this module is hand-typed:

* **Staten Island Ferry** — NYC DOT, published on NYC Open Data as a GTFS zip attachment
  (``b57i-ri22``, *Staten Island Ferry Schedule - General Transit Feed Specification*). Route ``SIF``,
  St. George ↔ Whitehall.
* **NYC Ferry** — Hornblower/NYC EDC operational feed at ``nycferry.connexionz.net`` (the feed the NYC Ferry app
  and Google Maps consume): the Astoria, East River, Governors Island, Rockaway, Rockaway‑Soundview,
  South Brooklyn and St. George routes plus their landings.

``https://www.nyc.gov/html/dot/downloads/misc/siferry-gtfs.zip`` (the URL printed in the dataset description)
is refused by nyc.gov's edge with HTTP 403 from this network, so the Socrata blob endpoint for the same file is
used instead; both serve the identical zip. Neither feed is in ``sources.py`` yet — the two :class:`Source`
records are defined here and registered through ``manifest.record_download`` exactly like every other download,
and the report asks for them to be folded into ``sources.py``.

Only ``route_type = 4`` (ferry) routes are written to ``ferry_routes.parquet``; the NYC Ferry feed also carries
``route_type = 3`` shuttle **buses** in the Rockaways, which belong to the bus tables, not to the ferry ones.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from ..download import download
from ..sources import SOURCES, Source

log = logging.getLogger("nycsim.transit.ferry")

SI_FERRY_BLOB = ("https://data.cityofnewyork.us/api/views/b57i-ri22/files/"
                 "7afb9c83-b214-4da7-8242-c178132e6d0f?download=true&filename=siferry-gtfs.zip")
NYC_FERRY_URL = "https://nycferry.connexionz.net/rtt/public/utility/gtfs.aspx"

# The two ferry feeds live in the foundation registry (pipeline/nycsim_pipeline/sources.py) so that
# `python -m nycsim_pipeline.download --tag transit` fetches them like every other source.
FERRY_SOURCES: dict[str, Source] = {k: SOURCES[k] for k in ("gtfs_ferry_staten_island", "gtfs_ferry_nyc")}


def fetch_feeds(force: bool = False) -> dict[str, Path]:
    """Download both ferry feeds through the standard downloader (records SHA-256 + licence in the manifest)."""
    out: dict[str, Path] = {}
    for fid, src in FERRY_SOURCES.items():
        out[fid] = download(src, force=force)
        log.info("ferry feed %s -> %s (%d bytes)", fid, out[fid], out[fid].stat().st_size)
    return out


def terminal_rows(stops, routes_by_stop: dict[str, list[str]]) -> list[dict]:
    """One row per ferry landing actually served by a ferry route on the service day."""
    rows = []
    for stop_id, name, x, y in stops:
        r = sorted(set(routes_by_stop.get(stop_id, [])))
        if not r:
            continue
        rows.append({"stop_id": stop_id, "name": name, "x": float(x), "y": float(y), "routes": r})
    return rows


def dedupe_terminals(rows: list[dict], radius_m: float = 60.0) -> list[dict]:
    """Merge landings that are the same berth published twice (NYC Ferry lists per-direction stop ids)."""
    if not rows:
        return rows
    from scipy.spatial import cKDTree

    xy = np.array([[r["x"], r["y"]] for r in rows])
    tree = cKDTree(xy)
    parent = list(range(len(rows)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in tree.query_pairs(radius_m):
        if rows[i]["name"].strip().lower() == rows[j]["name"].strip().lower():
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[max(ri, rj)] = min(ri, rj)
    merged: dict[int, dict] = {}
    for i, r in enumerate(rows):
        k = find(i)
        m = merged.setdefault(k, {"stop_id": r["stop_id"], "name": r["name"], "x": 0.0, "y": 0.0,
                                  "routes": set(), "stop_ids": []})
        m["routes"].update(r["routes"])
        m["stop_ids"].append(r["stop_id"])
    out = []
    for k, m in merged.items():
        members = [rows[i] for i in range(len(rows)) if find(i) == k]
        m["x"] = float(np.mean([p["x"] for p in members]))
        m["y"] = float(np.mean([p["y"] for p in members]))
        m["routes"] = sorted(m["routes"])
        m["stop_ids"] = sorted(m["stop_ids"])
        out.append(m)
    out.sort(key=lambda r: r["name"])
    log.info("ferry landings: %d stop records -> %d distinct berths", len(rows), len(out))
    return out
