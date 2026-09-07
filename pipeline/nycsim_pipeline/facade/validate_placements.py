"""Validate ``tiles/{tile}/kit_placements.bin`` and reconcile its kit ids with the Blender kit catalog.

    python -m nycsim_pipeline.facade.validate_placements [--tiles t_x_y ...] [--limit N]

Two jobs:

1. **Structural and geometric validation of every tile.** File size is a whole number of 40-byte records; the ``.json``
   header's ``count``, ``bytes`` and ``sha256`` match the file; every ``bin`` in the file exists in that tile's
   ``buildings.parquet``; every placement sits inside its own building's footprint bounding box plus
   :data:`BBOX_MARGIN_M`; ``z`` lies between the building's ground and roof plus the tallest roof piece; ``yaw_deg``
   and ``scale`` are finite and in range; every ``kit_id`` is registered in :mod:`nycsim_pipeline.facade.kit_ids`; and
   a tile that holds buildings holds placements.

2. **Reconciliation with ``blender_out/kit/catalog/*.json``.** The numeric ids come *from* that catalog
   (:mod:`nycsim_pipeline.facade.kit_ids`), so the reconciliation is a check that every id a placement uses is a real
   exported asset, plus the ``kit_id -> catalog_id -> .glb`` map the UE importer needs, written to
   ``data/processed/facade/kit_catalog_map.json``.  Catalog entries the placer never emits, and placement roles the kit
   does not export a piece for, are both listed rather than hidden.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import shapely

from ..paths import BLENDER_OUT, PROCESSED, VERIFICATION
from . import kit_ids as K
from .placements import PLACEMENT_DTYPE, RECORD_BYTES

log = logging.getLogger("nycsim.facade.validate")

TILES_ROOT = PROCESSED / "tiles"
CATALOG_DIR = BLENDER_OUT / "kit" / "catalog"
OUT_MAP = PROCESSED / "facade" / "kit_catalog_map.json"
REPORT = VERIFICATION / "facade" / "placement_validation.json"

BBOX_MARGIN_M = 2.0        # a stoop, a fire escape and a sidewalk shed project beyond the footprint
Z_ABOVE_ROOF_M = 16.0      # the tallest roof piece is a 20,000 gal wooden tank on its stand
Z_BELOW_GROUND_M = 1.5
MAX_SCALE = 16.0           # run pieces are split into segments so no instance is stretched further than this

def catalog_map() -> dict:
    """``kit_id`` -> exported catalog entry, straight out of the registry the kit catalog defines."""
    reg = K.registry()
    return {
        "schema_version": 2,
        "kit_catalog_dir": str(CATALOG_DIR),
        "catalog_entries": reg["catalog_entries"],
        "id_formula": reg["id_formula"],
        "pieces": reg["pieces"],
        "roles_without_a_kit_piece": reg["roles_without_a_kit_piece"],
    }


def validate_tile(tile_dir: Path) -> dict:
    """Structural and geometric checks for one tile."""
    name = tile_dir.name
    res: dict = {"tile": name, "problems": [], "placements": 0, "bytes": 0, "buildings": 0}
    bin_p = tile_dir / "kit_placements.bin"
    json_p = tile_dir / "kit_placements.json"
    b_p = tile_dir / "buildings.parquet"
    if not b_p.exists():
        res["problems"].append("buildings.parquet missing")
        return res
    n_buildings = pq.ParquetFile(b_p).metadata.num_rows
    res["buildings"] = n_buildings
    if not bin_p.exists() or not json_p.exists():
        res["problems"].append("kit_placements.bin/.json missing")
        return res
    raw = bin_p.read_bytes()
    res["bytes"] = len(raw)
    if len(raw) % RECORD_BYTES:
        res["problems"].append(f"{len(raw)} bytes is not a multiple of {RECORD_BYTES}")
        return res
    rec = np.frombuffer(raw, dtype=PLACEMENT_DTYPE)
    res["placements"] = int(len(rec))
    hdr = json.load(open(json_p))
    if hdr.get("count") != len(rec):
        res["problems"].append(f"header count {hdr.get('count')} != {len(rec)} records")
    if hdr.get("bytes") != len(raw):
        res["problems"].append(f"header bytes {hdr.get('bytes')} != {len(raw)}")
    if hdr.get("record_bytes") != RECORD_BYTES:
        res["problems"].append(f"header record_bytes {hdr.get('record_bytes')} != {RECORD_BYTES}")
    if hdr.get("sha256") != hashlib.sha256(raw).hexdigest():
        res["problems"].append("header sha256 does not match the file")
    if n_buildings and len(rec) == 0:
        res["problems"].append(f"{n_buildings} buildings but no placements")
        return res
    if len(rec) == 0:
        return res

    registered = {p["kit_id"] for p in K.registry()["pieces"]}
    unknown = sorted({int(k) for k in np.unique(rec["kit_id"])} - registered)
    if unknown:
        res["problems"].append(f"kit ids absent from the catalog-derived registry: {unknown[:10]}")
    if not np.isfinite(rec["x"]).all() or not np.isfinite(rec["y"]).all() or not np.isfinite(rec["z"]).all():
        res["problems"].append("non-finite coordinates")
    if not np.isfinite(rec["yaw_deg"]).all() or np.abs(rec["yaw_deg"]).max() > 360.001:
        res["problems"].append("yaw_deg outside [-360, 360]")
    if not np.isfinite(rec["scale"]).all() or rec["scale"].min() <= 0 or rec["scale"].max() > MAX_SCALE:
        res["problems"].append(f"scale out of range [{rec['scale'].min()}, {rec['scale'].max()}]")
    if (rec["flags"] & ~np.uint32(0b111)).any():
        res["problems"].append("flags outside the three documented bits")

    tb = pq.read_table(b_p, columns=["bin", "footprint", "ground_z", "roof_z", "has_storefront", "window_rows",
                                     "floors", "n_placements"])
    bins = tb["bin"].to_numpy()
    order = np.argsort(bins, kind="stable")
    sb = bins[order]
    pos = np.searchsorted(sb, rec["bin"])
    ok = (pos < len(sb)) & (sb[np.minimum(pos, len(sb) - 1)] == rec["bin"])
    if not ok.all():
        res["problems"].append(f"{int((~ok).sum())} placements reference a bin absent from the tile")
    idx = order[np.minimum(pos, len(sb) - 1)]
    g = shapely.from_wkb(np.asarray(tb["footprint"].to_pylist(), dtype=object))
    xmin, ymin, xmax, ymax = shapely.bounds(g).T
    gz = tb["ground_z"].to_numpy(zero_copy_only=False)
    rz = tb["roof_z"].to_numpy(zero_copy_only=False)
    sel = ok
    outside = ((rec["x"][sel] < xmin[idx[sel]] - BBOX_MARGIN_M) | (rec["x"][sel] > xmax[idx[sel]] + BBOX_MARGIN_M)
               | (rec["y"][sel] < ymin[idx[sel]] - BBOX_MARGIN_M) | (rec["y"][sel] > ymax[idx[sel]] + BBOX_MARGIN_M))
    if outside.any():
        res["problems"].append(f"{int(outside.sum())} placements outside their footprint bbox + {BBOX_MARGIN_M} m")
    badz = ((rec["z"][sel] < gz[idx[sel]] - Z_BELOW_GROUND_M) | (rec["z"][sel] > rz[idx[sel]] + Z_ABOVE_ROOF_M))
    if badz.any():
        res["problems"].append(f"{int(badz.sum())} placements with z outside the building's vertical extent")

    wr = tb["window_rows"].to_numpy()
    fl = tb["floors"].to_numpy()
    if (wr > fl).any():
        res["problems"].append("window_rows exceeds floors")
    # storefront pieces only on buildings the data says have a storefront
    sf_ids = {p["kit_id"] for p in K.registry()["pieces"]
              if p["category"] in ("storefront", "storefront_interior")
              and not p["catalog_id"].startswith("entry_")}
    has_sf = tb["has_storefront"].to_numpy(zero_copy_only=False)
    is_sf = np.isin(rec["kit_id"], list(sf_ids)) & sel
    if is_sf.any() and not has_sf[idx[is_sf]].all():
        res["problems"].append(f"{int((~has_sf[idx[is_sf]]).sum())} storefront pieces on buildings without a storefront")
    npl = tb["n_placements"].to_numpy()
    if int(npl.sum()) != len(rec):
        res["problems"].append(f"n_placements column sums to {int(npl.sum())} but the file holds {len(rec)}")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nycsim_pipeline.facade.validate_placements",
                                 description="Validate kit placements and reconcile them with the Blender kit catalog")
    ap.add_argument("--tiles", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None, help="validate only the first N tiles")
    ap.add_argument("--tiles-root", default=str(TILES_ROOT))
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    root = Path(a.tiles_root)
    tiles = ([root / t for t in a.tiles] if a.tiles
             else sorted(p.parent for p in root.glob("*/kit_placements.bin")))
    if a.limit:
        tiles = tiles[: a.limit]
    if not tiles:
        print(json.dumps({"error": f"no tiles with kit_placements.bin under {root}"}, indent=1))
        return 1

    cmap = catalog_map()
    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_MAP, "w") as f:
        json.dump(cmap, f, indent=1)

    results = [validate_tile(t) for t in tiles]
    bad = [r for r in results if r["problems"]]
    used = set()
    for t in tiles:
        p = t / "kit_placements.json"
        if p.exists():
            used |= {int(k) for k in json.load(open(p)).get("kit_ids", [])}
    registered = {p["kit_id"]: p for p in cmap["pieces"]}
    summary = {
        "schema_version": 2,
        "tiles_checked": len(results),
        "tiles_with_problems": len(bad),
        "problems": bad[:40],
        "placements": sum(r["placements"] for r in results),
        "bytes": sum(r["bytes"] for r in results),
        "buildings": sum(r["buildings"] for r in results),
        "distinct_kit_ids_used": len(used),
        "kit_ids_used_without_a_catalog_piece": sorted(kid for kid in used if kid not in registered),
        "kit_pieces_used": sorted(registered[k]["catalog_id"] for k in used if k in registered),
        "catalog": {"entries": cmap["catalog_entries"],
                    "catalog_entries_never_placed": sorted(
                        p["catalog_id"] for p in cmap["pieces"] if p["kit_id"] not in used),
                    "roles_without_a_kit_piece": cmap["roles_without_a_kit_piece"]},
        "kit_catalog_map": str(OUT_MAP),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "problems"}, indent=1))
    if bad:
        print(json.dumps({"first_problems": bad[:5]}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
