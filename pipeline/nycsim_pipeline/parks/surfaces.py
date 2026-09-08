"""Open-space ground surfaces: what a park is made of, from the survey that measured it.

Two planimetric layers were downloaded at the start of this build and read by nothing since:

===== ====================================== ======= ==============================================
code  class                                    rows  the ground it is
===== ====================================== ======= ==============================================
4980  Park Boundary                            4,241  grass / planted park ground
4985  Greenstreets                             3,339  the planted traffic islands and medians
4910  Court (basketball, handball, tennis,     4,626  a hard court surface -- asphalt or acrylic
      hockey, volleyball, multipurpose)
4900  Baseball/Softball Field                    623  infield dirt and outfield grass
4920  Football Field                              66  grass
4930  Soccer Field                                97  grass
4940  Golf Course                                 21  mown grass
4950  Pool                                       107  water
4960  Running Track                                68  polyurethane track
4970  Skating Rink                                17  ice
2500  Cemetery Outline                           111  grass
2510  Recreational Area                        5,358  grass
2520  Vacant Area                              8,900  bare ground
===== ====================================== ======= ==============================================

27,574 polygons, and until now the terrain was the only thing under a park: Central Park, Prospect
Park, every schoolyard court and every ball field was drawn as the same material as a vacant lot,
and a tyre on any of them resolved to whatever the landscape's default physical material is.

It matters twice. Visually, 181.3 km² of the city is green space drawn in one colour. And in the
friction model: ``SurfaceClass`` declares ``Grass``, ``Water`` and ``Ice`` and **nothing in the
world produced any of them** -- three entries in the tyre model that could not be reached. A pool,
a skating rink and a lawn are exactly what reaches them.

    python -m nycsim_pipeline.parks.surfaces
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from ..crs import TILE_SIZE_M, transformer
from ..paths import PROCESSED, RAW

log = logging.getLogger("nycsim.parks.surfaces")

PARKS = RAW / "nyc_opendata" / "plan_open_space_parks.geojson"
OTHER = RAW / "nyc_opendata" / "plan_open_space_other.geojson"
OUT = PROCESSED / "parks" / "surfaces.parquet"
SCHEMA = "parks_surfaces/1"

#: ``kind`` enum, and what each is made of. ``surface`` is the material family the Blender stage
#: draws it with; ``surface_class`` is ``nycsim_gameplay::SurfaceClass``, which is also the
#: ``EPhysicalSurface`` index ``DefaultEngine.ini`` declares.
#:
#: ``lift_m`` is how far the slab stands above the terrain, on the same scale the pavement uses
#: (roadbed 0.10, sidewalk 0.25). Park ground is *the* ground, so it sits barely above it; a court
#: is a poured slab and stands a little proud of the grass around it; a pool surface is water at the
#: coping, which is where the survey traced it.
#: ``lift_m`` has to be at least the drape tolerance the Blender stage uses for that kind, or the
#: terrain shows through: a lawn draped to 0.20 m of tolerance and lifted 0.03 m is under the ground
#: over half its area, which was measured before these numbers were set. The lifts below are the
#: ones that keep each surface above the landscape *and* say something true about it -- a lawn is
#: turf and topsoil over the bare-earth DEM and stands about 0.20 m proud of it, which also puts it
#: 0.05 m below the sidewalk at 0.25 m, where a lawn beside a kerb is.
#:
#: ``below_grade`` marks the two that are *supposed* to be under the ground around them: a pool's
#: water surface sits below its coping, and a sunken rink below its surround. Their draping residual
#: is reported separately, because "pierced the terrain" is what they are.
KINDS: dict[int, dict] = {
    0: {"name": "park_ground", "surface": "grass", "surface_class": 8, "lift_m": 0.20, "skirt_m": 0.35},
    1: {"name": "greenstreet", "surface": "grass", "surface_class": 8, "lift_m": 0.20, "skirt_m": 0.35},
    2: {"name": "court", "surface": "sport_hard", "surface_class": 1, "lift_m": 0.10, "skirt_m": 0.25},
    3: {"name": "ballfield", "surface": "ball_dirt", "surface_class": 6, "lift_m": 0.12, "skirt_m": 0.25},
    4: {"name": "grass_field", "surface": "grass", "surface_class": 8, "lift_m": 0.18, "skirt_m": 0.30},
    5: {"name": "golf", "surface": "grass", "surface_class": 8, "lift_m": 0.20, "skirt_m": 0.35},
    6: {"name": "pool", "surface": "water", "surface_class": 10, "lift_m": -0.30, "skirt_m": 0.60,
        "below_grade": True},
    7: {"name": "track", "surface": "track", "surface_class": 1, "lift_m": 0.10, "skirt_m": 0.25},
    8: {"name": "skating_rink", "surface": "ice", "surface_class": 13, "lift_m": 0.08, "skirt_m": 0.25},
    9: {"name": "cemetery", "surface": "grass", "surface_class": 8, "lift_m": 0.20, "skirt_m": 0.35},
    10: {"name": "recreation", "surface": "grass", "surface_class": 8, "lift_m": 0.20, "skirt_m": 0.35},
    11: {"name": "vacant", "surface": "bare", "surface_class": 6, "lift_m": 0.12, "skirt_m": 0.25},
}

#: Planimetric feature code -> ``kind``. The codes are the Capture Rules' own (OPEN SPACE and
#: OPEN SPACE (PARKS) sections); nothing here is inferred from a name.
FEAT_TO_KIND: dict[int, int] = {
    4980: 0, 4985: 1, 4910: 2, 4900: 3, 4920: 4, 4930: 4, 4940: 5,
    4950: 6, 4960: 7, 4970: 8, 2500: 9, 2510: 10, 2520: 11,
}

#: Polygons smaller than this are dropped: below a couple of square metres the survey is recording a
#: sliver of a boundary rather than a surface anything stands on.
MIN_AREA_M2 = 2.0


def _to_tm(g, tr):
    return shapely.transform(g, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))


def load(path: Path, code_key: str, sub_key: str, name_key: str) -> list[dict]:
    if not path.is_file():
        log.warning("%s absent", path)
        return []
    doc = json.loads(path.read_text())
    tr = transformer("EPSG:4326", "NYC_TM")
    out = []
    for f in doc["features"]:
        pr = f["properties"]
        try:
            code = int(pr.get(code_key))
        except (TypeError, ValueError):
            continue
        kind = FEAT_TO_KIND.get(code)
        if kind is None:
            continue
        g = _to_tm(shapely.from_geojson(json.dumps(f["geometry"])), tr)
        if g.is_empty:
            continue
        for part in (shapely.get_parts(g) if g.geom_type.startswith("Multi") else [g]):
            if part.geom_type != "Polygon" or part.area < MIN_AREA_M2:
                continue
            out.append({"kind": kind, "feat_code": code,
                        "sub_code": int(pr.get(sub_key) or 0) if str(pr.get(sub_key) or "").isdigit() else 0,
                        "name": str(pr.get(name_key) or ""),
                        "plan_source_id": str(pr.get("source_id") or ""),
                        "geometry": part})
    return out


def build(parks: Path = PARKS, other: Path = OTHER) -> pa.Table:
    rows = load(parks, "feat_code", "sub_code", "park_name") + load(other, "feature_co", "sub_featur", "name")
    log.info("open space polygons: %d", len(rows))
    if not rows:
        return pa.table({})

    # A court, a ball field or a pool is drawn *inside* a park boundary, and two slabs at different
    # heights over the same ground fight. The boundary yields: every park-ground polygon has the
    # facilities inside it cut out, which is what the survey means by drawing them separately.
    facilities = [r["geometry"] for r in rows if r["kind"] not in (0, 9, 10, 11)]
    cut = shapely.union_all(facilities) if facilities else None
    cut_count = 0
    final = []
    for r in rows:
        g = r["geometry"]
        if cut is not None and r["kind"] in (0, 9, 10, 11):
            g2 = shapely.difference(g, cut)
            if g2.area < g.area - 1e-9:
                cut_count += 1
            g = g2
        for part in (shapely.get_parts(g) if g.geom_type.startswith("Multi") else [g]):
            if part.geom_type != "Polygon" or part.area < MIN_AREA_M2:
                continue
            final.append(dict(r, geometry=part))
    log.info("%d ground polygons had a facility cut out of them; %d polygons after", cut_count, len(final))

    kinds = np.array([r["kind"] for r in final], dtype=np.int16)
    geoms = np.asarray([r["geometry"] for r in final], dtype=object)
    cent = shapely.centroid(geoms)
    tx = np.floor(shapely.get_x(cent) / TILE_SIZE_M).astype(np.int32)
    ty = np.floor(shapely.get_y(cent) / TILE_SIZE_M).astype(np.int32)
    order = np.lexsort((np.arange(len(final)), kinds, ty, tx))
    table = pa.table({
        "surface_id": pa.array(np.arange(len(final), dtype=np.int64)[order]),
        "kind": pa.array(kinds[order]),
        "kind_name": pa.array([KINDS[int(kinds[i])]["name"] for i in order]),
        "surface_class": pa.array(np.array([KINDS[int(kinds[i])]["surface_class"] for i in order], dtype=np.int16)),
        "feat_code": pa.array(np.array([final[i]["feat_code"] for i in order], dtype=np.int32)),
        "sub_code": pa.array(np.array([final[i]["sub_code"] for i in order], dtype=np.int32)),
        "name": pa.array([final[i]["name"] for i in order]),
        "plan_source_id": pa.array([final[i]["plan_source_id"] for i in order]),
        "area_m2": pa.array(np.array([final[i]["geometry"].area for i in order], dtype=np.float64)),
        "tx": pa.array(tx[order]), "ty": pa.array(ty[order]),
        "tile": pa.array([f"t_{tx[i]}_{ty[i]}" for i in order]),
        "geometry": pa.array([shapely.to_wkb(final[i]["geometry"]) for i in order], type=pa.binary()),
    })
    return table.replace_schema_metadata({b"nycsim.schema": SCHEMA.encode(),
                                          b"nycsim.schema_version": b"1"})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parks", type=Path, default=PARKS)
    ap.add_argument("--other", type=Path, default=OTHER)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    t0 = time.perf_counter()
    table = build(args.parks, args.other)
    if not table.num_columns:
        print(json.dumps({"rows": 0, "reason": "no open space source on disk"}))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, args.out, compression="zstd")
    kind = np.asarray(table.column("kind_name").to_pylist(), dtype=object)
    area = np.asarray(table.column("area_m2"), dtype=float)
    print(json.dumps({
        "rows": table.num_rows,
        "hectares": round(float(area.sum()) / 1e4, 1),
        "by_kind": {k: {"rows": int((kind == k).sum()),
                        "hectares": round(float(area[kind == k].sum()) / 1e4, 2),
                        "surface_class": KINDS[[i for i, v in KINDS.items() if v["name"] == k][0]]["surface_class"]}
                    for k in sorted(set(kind.tolist()))},
        "tiles": int(len(set(table.column("tile").to_pylist()))),
        "seconds": round(time.perf_counter() - t0, 1),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
