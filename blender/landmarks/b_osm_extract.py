"""Extract real alignments of bridges, tunnels, aerialways and named structures from the BBBike NYC OSM extract.

Output (Blender landmarks agent B lane): ``blender_out/landmarks/b_osm/structures.geojson`` (WGS84, one feature per
OSM way/node/relation-member with its tags) plus ``LICENSE.json`` (ODbL attribution + source sha256 from the download
manifest). Bridge scripts use these geometries to align spans to the real deck centreline; published tower/span
dimensions come from each script's docstring.

Usage: nice -n 10 python3 blender/landmarks/b_osm_extract.py [pbf_path]
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path

import osmium

REPO = Path(__file__).resolve().parents[2]
PBF = REPO / "data/raw/osm/NewYork.osm.pbf"
OUT_DIR = REPO / "blender_out/landmarks/b_osm"
log = logging.getLogger("b_osm_extract")

NAME_RE = re.compile(
    r"brooklyn bridge|manhattan bridge|williamsburg bridge|queensboro|george washington bridge|verrazz|robert f\.? kennedy|"
    r"triborough|throgs neck|whitestone bridge|hell gate|high bridge|pulaski bridge|kosciuszko|roosevelt island tram|"
    r"lincoln tunnel|holland tunnel|midtown tunnel|carey tunnel|brooklyn.battery tunnel|bow bridge|cyclone|wonder wheel|"
    r"parachute jump|unisphere|statue of liberty|washington square arch|soldiers.{0,3}and sailors|grant.s tomb|"
    r"general grant|castle williams|fort jay|bethesda|belvedere castle|oculus|world trade center|september 11|"
    r"ellis island|luna park|nathan.s|columbus circle|maine monument|deutsche bank center|time warner center|"
    r"riegelmann|steeplechase|randall|wards island|harlem river lift|bronx kill|liberty island|fort wood|"
    r"tunnel ventilation|ventilation (building|shaft|tower)|vent (building|shaft)|toll plaza",
    re.I,
)
TAG_KEYS_ANY = ("aerialway", "attraction", "roller_coaster", "bridge:support", "bridge:structure")


def _tags(o) -> dict[str, str]:
    return {t.k: t.v for t in o.tags}


def _way_matches(tags: dict[str, str]) -> bool:
    name = tags.get("name", "") + " " + tags.get("alt_name", "") + " " + tags.get("official_name", "")
    if tags.get("man_made") == "bridge":
        return True
    if any(k in tags for k in TAG_KEYS_ANY):
        return True
    if NAME_RE.search(name):
        return True
    return False


def _node_matches(tags: dict[str, str]) -> bool:
    if not tags:
        return False
    if "bridge:support" in tags or tags.get("man_made") in ("tower", "ventilation_shaft", "lighthouse", "flagpole"):
        return NAME_RE.search(tags.get("name", "")) is not None or "bridge:support" in tags
    if tags.get("aerialway") or tags.get("attraction"):
        return True
    return NAME_RE.search(tags.get("name", "")) is not None


def main(pbf: Path = PBF) -> Path:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not pbf.exists():
        raise FileNotFoundError(pbf)
    t0 = time.time()
    # pass 1: relations whose tags match -> member way ids (multipolygon bridge outlines, route relations for tunnels)
    rel_member_ways: dict[int, list[dict]] = {}
    n_rel = 0
    for rel in osmium.FileProcessor(str(pbf), osmium.osm.RELATION):
        tags = _tags(rel)
        if not _way_matches(tags):
            continue
        n_rel += 1
        for m in rel.members:
            if m.type == "w":
                rel_member_ways.setdefault(m.ref, []).append({"relation_id": rel.id, "role": m.role, "relation_tags": tags})
    log.info("pass 1: %d matching relations, %d member ways (%.0f s)", n_rel, len(rel_member_ways), time.time() - t0)

    features: list[dict] = []
    n_ways = n_nodes = 0
    for o in osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY).with_locations():
        if o.is_node():
            tags = _tags(o)
            if _node_matches(tags):
                n_nodes += 1
                features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [o.location.lon, o.location.lat]},
                                 "properties": {"osm_type": "node", "osm_id": o.id, "tags": tags}})
        else:
            tags = _tags(o)
            members = rel_member_ways.get(o.id)
            if not (members or _way_matches(tags)):
                continue
            coords = []
            for n in o.nodes:
                if n.location.valid():
                    coords.append([n.location.lon, n.location.lat])
            if len(coords) < 2:
                continue
            closed = len(coords) >= 4 and coords[0] == coords[-1] and (tags.get("area") == "yes" or "building" in tags or tags.get("man_made") == "bridge"
                                                                     or any(m["role"] in ("outer", "inner") for m in (members or [])))
            geom = {"type": "Polygon", "coordinates": [coords]} if closed else {"type": "LineString", "coordinates": coords}
            props = {"osm_type": "way", "osm_id": o.id, "tags": tags}
            if members:
                props["relations"] = members
            features.append({"type": "Feature", "geometry": geom, "properties": props})
            n_ways += 1
    log.info("pass 2: %d ways, %d nodes kept (%.0f s)", n_ways, n_nodes, time.time() - t0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "structures.geojson"
    with open(out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features,
                   "properties": {"schema_version": 1, "crs": "EPSG:4326", "source": "BBBike NewYork.osm.pbf", "n_features": len(features)}}, f)
    # licence record next to the file (AGENT_BRIEF: url, licence, author, sha256)
    sha = ""
    man = REPO / "data/manifest/downloads.json"
    if man.exists():
        try:
            entries = json.load(open(man))["entries"]
            for e in entries.values():
                if e["path"].endswith("NewYork.osm.pbf"):
                    sha = e["sha256"]
                    src_url = e["url"]
                    break
            else:
                src_url = "https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf"
        except Exception:  # manifest unreadable -> still record what we know
            src_url = "https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf"
    else:
        src_url = "https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf"
    with open(OUT_DIR / "LICENSE.json", "w") as f:
        json.dump({"file": "structures.geojson", "url": src_url, "license": "ODbL 1.0", "author": "OpenStreetMap contributors",
                   "attribution": "© OpenStreetMap contributors, ODbL", "source_sha256": sha, "extracted_by": "blender/landmarks/b_osm_extract.py"}, f, indent=1)
    log.info("wrote %s (%d features)", out, len(features))
    return out


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else PBF)
