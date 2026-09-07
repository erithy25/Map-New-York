#!/usr/bin/env python3
"""Export, once, the plan outline of the ground every landmark model supplies itself.

    python3 blender/landmarks/export_ground_outlines.py
    python3 blender/landmarks/export_ground_outlines.py --ids b_wtc_site,b_hudson_yards

Output ``data/processed/landmarks/ground_outlines.parquet``:

===================  ==========================================================================
``landmark_id``      catalogue id, e.g. ``b_wtc_site``
``name``             catalogue name
``ground_z_m``       the elevation the catalogue declares for the model, NAVD88 metres
``area_m2``          plan area of this outline
``geometry``         WKB polygon in NYC_TM, openings **filled** (see below)
===================  ==========================================================================

Why this file exists
--------------------
:func:`blender.verify.scene.landmark_ground_outlines` already answers "which ground does this
landmark supply itself", and the verification renderer already refuses to draw terrain or pavement
inside the answer.  But it answers it *from loaded Blender objects*, so every consumer that wants
the same answer has to load the same 93 glTF files first.  The road-surface export
(``blender/roads/build_pavement.py``) runs over 972 tiles in parallel worker processes and cannot
pay that; neither can a test.  So the answer is computed once, here, and stored.

The openings are filled on purpose.  A hole cut in a landmark's own ground plane -- the 9/11
Memorial's two 61 m pools are the case -- is a modelled hole *in the ground*, and drawing the city's
1 m DEM across it would hide the very thing the opening exists to show.  The rule, its evidence and
its two exceptions (a deck more than a metre above the heightmap is a podium standing on the ground,
not a statement about where the ground is) all live in that function's docstring; this script only
carries its result across a process boundary.

The outlines are in **world** NYC_TM: each model is translated to its catalogue ``origin_tm`` before
the faces are read, exactly as the renderer places it (the landmark model axes are already parallel
to NYC_TM -- ``blender/landmarks/common.py``: "no rotation to apply on import").
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "verify"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

LOG = logging.getLogger("nycsim.landmarks.ground_outlines")

OUT_PARQUET = REPO_ROOT / "data" / "processed" / "landmarks" / "ground_outlines.parquet"
SCHEMA = "landmarks.ground_outlines.v1"


def _import_glb(path: Path) -> list:
    """Import one glTF and return the objects it created (and only those)."""
    import bpy

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [ob for ob in bpy.data.objects if ob not in before]


def outlines_for_entry(entry: dict, sampler) -> tuple[list, dict]:
    """``([shapely.Polygon, ...], detail)`` for one catalogue entry, in world NYC_TM.

    ``sampler`` is required, not optional.  It is what separates a landmark's *ground* from a
    landmark's *deck*: a modelled surface standing more than a metre from the heightmap beneath it
    is a podium or a portal, it is not a statement about where the ground is, and cutting there
    would leave a hole where there is real ground.  Called without one, this function would emit
    Hudson Yards' plaza (+5.34 m) and the Lincoln Tunnel portals (-9.68 m) as ground.
    """
    import bpy
    from mathutils import Matrix

    import scene as vs

    ox, oy, oz = (float(v) for v in entry["origin_tm"])
    rel = Path(entry["glb"])
    glb = rel if rel.is_absolute() else REPO_ROOT / rel
    if not glb.exists():
        glb = REPO_ROOT / "blender_out" / "landmarks" / rel.name
    if not glb.exists():
        return [], {"reason": f"glb not found: {entry['glb']}"}

    objects = _import_glb(glb)
    for ob in objects:
        if ob.parent is None:
            ob.matrix_world = Matrix.Translation((ox, oy, oz)) @ ob.matrix_world
    bpy.context.view_layer.update()
    try:
        rings, area, detail = vs.landmark_ground_outlines(objects, oz, sampler=sampler)
    finally:
        for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images):
            for item in list(coll):
                coll.remove(item, do_unlink=True)
    detail = dict(detail or {})
    detail["area_m2"] = round(float(area), 1)
    return rings, detail


def build(ids: list[str] | None = None, out: Path = OUT_PARQUET) -> dict:
    import nycsim_bpy as nb
    import pyarrow as pa
    import pyarrow.parquet as pq
    import shapely

    import scene as vs

    t0 = time.perf_counter()
    nb.reset_scene()
    sampler = vs.TerrainSampler()
    entries = vs.load_landmark_catalog()
    if ids:
        wanted = set(ids)
        entries = [e for e in entries if e["id"] in wanted]
    rows: list[dict] = []
    detail_by_id: dict[str, dict] = {}
    for i, e in enumerate(entries, 1):
        try:
            rings, detail = outlines_for_entry(e, sampler)
        except Exception as exc:  # one unreadable model must not lose the other 92
            LOG.exception("landmark %s failed", e.get("id"))
            detail_by_id[str(e.get("id"))] = {"error": str(exc)}
            continue
        detail_by_id[str(e.get("id"))] = detail
        for g in rings:
            rows.append({"landmark_id": str(e.get("id")), "name": str(e.get("name") or e.get("id")),
                         "ground_z_m": float(e["origin_tm"][2]), "area_m2": float(g.area),
                         "geometry": shapely.to_wkb(g)})
        note = detail.get("reason", "")
        print(f"[{i}/{len(entries)}] {e.get('id')}: {len(rings)} outline(s), "
              f"{detail.get('area_m2', 0.0)} m2"
              + (f"  [{note}]" if note and not rings else ""), flush=True)

    table = pa.table({
        "landmark_id": pa.array([r["landmark_id"] for r in rows], pa.string()),
        "name": pa.array([r["name"] for r in rows], pa.string()),
        "ground_z_m": pa.array([r["ground_z_m"] for r in rows], pa.float64()),
        "area_m2": pa.array([r["area_m2"] for r in rows], pa.float64()),
        "geometry": pa.array([r["geometry"] for r in rows], pa.binary()),
    }, metadata={b"nycsim.schema": SCHEMA.encode(),
                 b"nycsim.crs": b"NYC_TM",
                 b"nycsim.generator": b"blender/landmarks/export_ground_outlines.py",
                 b"nycsim.git_commit": nb.git_commit().encode()})
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out, compression="zstd")

    with_ground = sorted({r["landmark_id"] for r in rows})
    summary = {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": nb.git_commit(),
        "catalogue_entries": len(entries),
        "entries_with_own_ground": len(with_ground),
        "entries_rejected_as_deck": sorted(k for k, v in detail_by_id.items()
                                           if v.get("reason", "").startswith("the model's ground stands")),
        "outlines": len(rows),
        "total_area_m2": round(sum(r["area_m2"] for r in rows), 1),
        "parquet": str(out.relative_to(REPO_ROOT)),
        "ids_with_ground": with_ground,
        "detail": detail_by_id,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out.parent / "ground_outlines.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma separated landmark ids (default: the whole catalogue)")
    ap.add_argument("--out", type=Path, default=OUT_PARQUET)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ids = [s for s in (args.ids or "").split(",") if s] or None
    summary = build(ids, args.out)
    print(f"{summary['entries_with_own_ground']}/{summary['catalogue_entries']} landmarks supply "
          f"their own ground: {summary['outlines']} outlines, "
          f"{summary['total_area_m2']} m2 -> {summary['parquet']} "
          f"({summary['seconds']}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
