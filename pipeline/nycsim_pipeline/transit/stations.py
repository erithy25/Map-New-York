"""Station structures: the 1,137 surveyed subway and railway stations that nothing modelled.

``plan_railroad_structure.geojson`` (OTI planimetric, NYC Open Data ``anc7-97cy``) carries five
feature classes, and the furniture stage consumed two of them -- ventilation grates and emergency
exits -- as point props. The other three are structures:

===== =============================== ====== ==========================================
code  class                           rows   what it is
===== =============================== ====== ==========================================
2140  Elevated Subway/Train Station      974  the roof outline of an elevated station **and its
                                              platforms**, "delineated to include any underlying
                                              stairways" (Capture Rules, RAILROAD STRUCTURE)
2160  Subway/Train Station               313  the same for a stand-alone station at or below grade
2485  Transit Entrance                 2,005  street-level entrances; already placed as props from
                                              the MTA's own entrance dataset, so not built here
===== =============================== ====== ==========================================

50.7 ha of elevated station roof and 15.2 ha of station roof, and only 74 and 76 of them
respectively are inside a building footprint the buildings stage would have modelled. Every station
on the Astoria, Flushing, Jamaica, Jerome Avenue, White Plains Road, Brighton and West End elevateds
was missing -- sitting, now, on top of 490 km of elevated structure that this build does have.

An elevated station's elevation comes from the railway under it: the nearest built rail structure's
own deck profile, which ``deck_geometry`` has already reconciled at the joints and rebased on the
landscape. A ground-level station's comes from the landscape.

    python -m nycsim_pipeline.transit.stations
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from ..crs import transformer
from ..paths import PROCESSED, RAW
from ..terrain.landscape_grid import LandscapeSampler

log = logging.getLogger("nycsim.transit.stations")

SOURCE = RAW / "nyc_opendata" / "plan_railroad_structure.geojson"
RAIL = PROCESSED / "transit" / "rail_structures.parquet"
BUILDINGS = PROCESSED / "buildings" / "buildings_base.parquet"
TILES = PROCESSED / "tiles"
OUT = PROCESSED / "transit" / "stations.parquet"
SCHEMA = "transit_stations/1"

#: Planimetric feature code -> the kind this writes. 2485 is deliberately absent: the MTA's own
#: entrance dataset already places those as props (furniture kind 8) and two datasets for one
#: object is two objects in the world.
KINDS = {2140: "elevated_station", 2160: "station"}

#: How much of a station's roof outline has to fall inside a building footprint before the buildings
#: stage is taken to have modelled it already.
COVERED_FRACTION = 0.3

#: Height of a subway platform above the top of rail, metres. The R-series car floor is 1,143 mm
#: (45 in) above the rail head and the platform is level with it.
PLATFORM_ABOVE_RAIL_M = 1.143

#: Clear height of a platform canopy above the platform, metres. NYCT elevated station canopies run
#: about 4 m clear; the roof outline this stage extrudes is the canopy, not a room.
CANOPY_CLEAR_M = 4.0

#: Height of a stand-alone station house above its ground, metres. Nominal: these are one-storey
#: structures and the survey publishes no height for them. Flagged ``height_source = 1``.
STATION_HOUSE_H_M = 4.5

HEIGHT_MEASURED_DECK = 0    # sits on a rail deck this build measured
HEIGHT_NOMINAL = 1          # one-storey nominal, no published height
HEIGHT_CLASS_MEDIAN_DECK = 2   # elevated, but no built structure under it: the class median height

#: Median measured deck height of the elevated class, metres, from ``rail_structures.parquet``.
#: Used for the 42 elevated stations with no built structure within :data:`DECK_SEARCH_M` -- putting
#: those on the ground would be worse than putting them at the height every other one of them is at.
ELEVATED_CLASS_HEIGHT_M = 6.79

#: How far from a station roof outline a rail structure may be and still be the one under it.
DECK_SEARCH_M = 60.0


def load_source(path: Path = SOURCE) -> tuple[list, np.ndarray]:
    """The station polygons in NYC_TM, with their feature codes."""
    doc = json.loads(Path(path).read_text())
    tr = transformer("EPSG:4326", "NYC_TM")

    def to_tm(g):
        return shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))

    geoms, codes, sub, src_ids = [], [], [], []
    for f in doc["features"]:
        try:
            code = int(f["properties"].get("feat_code"))
        except (TypeError, ValueError):
            continue
        if code not in KINDS:
            continue
        g = to_tm(shapely.from_geojson(json.dumps(f["geometry"])))
        if g.is_empty or g.area < 4.0:
            continue
        geoms.append(g)
        codes.append(code)
        sub.append(int(f["properties"].get("sub_code") or 0))
        src_ids.append(str(f["properties"].get("source_id") or ""))
    return geoms, np.asarray(codes, dtype=np.int32), np.asarray(sub, dtype=np.int32), src_ids


def build(source: Path = SOURCE, rail: Path = RAIL, buildings: Path = BUILDINGS,
          tiles: Path = TILES) -> pa.Table:
    geoms, codes, sub, src_ids = load_source(source)
    log.info("station outlines: %s", {KINDS[c]: int((codes == c).sum()) for c in KINDS})

    # already a building?
    covered = np.zeros(len(geoms), dtype=bool)
    if Path(buildings).is_file():
        bt = pq.read_table(buildings, columns=["footprint"])
        fp = np.asarray(shapely.from_wkb(bt.column("footprint").to_pylist()), dtype=object)
        tree = shapely.STRtree(fp)
        for i, g in enumerate(geoms):
            idx = tree.query(g, predicate="intersects")
            if len(idx) and max(shapely.intersection(g, fp[j]).area for j in idx) > COVERED_FRACTION * g.area:
                covered[i] = True
        log.info("%d station outlines are already inside a building footprint", int(covered.sum()))

    # the deck under an elevated station
    deck_z = np.full(len(geoms), np.nan)
    rail_id = np.full(len(geoms), -1, dtype=np.int64)
    if Path(rail).is_file():
        rt = pq.read_table(rail)
        rk = np.asarray(rt.column("kind").to_pylist(), dtype=object)
        built = np.isin(rk, np.asarray(["elevated", "viaduct"], dtype=object))
        rg = np.asarray(shapely.from_wkb(rt.column("geometry").to_pylist()), dtype=object)[built]
        rz0 = np.asarray(rt.column("deck_z_start"), dtype=float)[built]
        rz1 = np.asarray(rt.column("deck_z_end"), dtype=float)[built]
        rid = np.asarray(rt.column("structure_id"), dtype=np.int64)[built]
        rtree = shapely.STRtree(rg)
        for i, g in enumerate(geoms):
            if codes[i] != 2140:
                continue
            c = g.centroid
            hit = rtree.query(g, predicate="intersects")
            if not len(hit):
                hit = rtree.query(shapely.buffer(c, DECK_SEARCH_M), predicate="intersects")
            if not len(hit):
                continue
            j = int(min(hit, key=lambda k: shapely.distance(c, rg[int(k)])))
            line = rg[j]
            s = line.project(c)
            frac = s / max(line.length, 1e-9)
            deck_z[i] = rz0[j] + (rz1[j] - rz0[j]) * min(1.0, max(0.0, frac))
            rail_id[i] = rid[j]

    sampler = LandscapeSampler(tiles)
    ground_z = np.full(len(geoms), np.nan)
    for i, g in enumerate(geoms):
        c = g.centroid
        z = sampler.height(np.array([c.x]), np.array([c.y]))
        ground_z[i] = float(z[0])

    elevated = codes == 2140
    orphan = elevated & ~np.isfinite(deck_z)
    deck_z = np.where(orphan, ground_z + ELEVATED_CLASS_HEIGHT_M, deck_z)
    base_z = np.where(np.isfinite(deck_z), deck_z + PLATFORM_ABOVE_RAIL_M, ground_z)
    roof_z = np.where(np.isfinite(deck_z), base_z + CANOPY_CLEAR_M, ground_z + STATION_HOUSE_H_M)
    hsource = np.where(orphan, HEIGHT_CLASS_MEDIAN_DECK,
                       np.where(np.isfinite(deck_z), HEIGHT_MEASURED_DECK, HEIGHT_NOMINAL)).astype(np.int8)
    if orphan.any():
        log.info("%d elevated stations have no built rail structure within %.0f m; placed at the "
                 "class median deck height", int(orphan.sum()), DECK_SEARCH_M)

    order = np.lexsort((np.arange(len(geoms)), codes))
    table = pa.table({
        "station_id": pa.array(np.arange(len(geoms), dtype=np.int64)[order]),
        "kind": pa.array([KINDS[int(codes[i])] for i in order]),
        "feat_code": pa.array(codes[order]),
        "sub_code": pa.array(sub[order]),
        "plan_source_id": pa.array([src_ids[i] for i in order]),
        "geometry": pa.array([shapely.to_wkb(geoms[i]) for i in order], type=pa.binary()),
        "area_m2": pa.array(np.array([geoms[i].area for i in order], dtype=np.float64)),
        "rail_structure_id": pa.array(rail_id[order]),
        "deck_z": pa.array(deck_z[order].astype(np.float32)),
        "ground_z": pa.array(ground_z[order].astype(np.float32)),
        "base_z": pa.array(base_z[order].astype(np.float32)),
        "roof_z": pa.array(roof_z[order].astype(np.float32)),
        "height_source": pa.array(hsource[order]),
        "in_a_building_footprint": pa.array(covered[order]),
    })
    return table.replace_schema_metadata({b"nycsim.schema": SCHEMA.encode(),
                                          b"nycsim.schema_version": b"1"})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    t0 = time.perf_counter()
    table = build(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, args.out, compression="zstd")
    kind = np.asarray(table.column("kind").to_pylist(), dtype=object)
    area = np.asarray(table.column("area_m2"), dtype=float)
    cov = np.asarray(table.column("in_a_building_footprint"), dtype=bool)
    hs = np.asarray(table.column("height_source"), dtype=np.int8)
    print(json.dumps({
        "rows": table.num_rows,
        "by_kind": {k: {"rows": int((kind == k).sum()),
                        "hectares": round(float(area[kind == k].sum()) / 1e4, 2),
                        "already_a_building": int((cov & (kind == k)).sum()),
                        "on_a_measured_deck": int(((hs == HEIGHT_MEASURED_DECK) & (kind == k)).sum()),
                        "on_the_class_median_deck": int(((hs == HEIGHT_CLASS_MEDIAN_DECK) & (kind == k)).sum()),
                        "nominal_height": int(((hs == HEIGHT_NOMINAL) & (kind == k)).sum())}
                    for k in sorted(set(kind.tolist()))},
        "seconds": round(time.perf_counter() - t0, 1),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
