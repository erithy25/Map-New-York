#!/usr/bin/env python3
"""Build the elevated railways and the waterfront structures of one tile as glTF 2.0.

    python3 blender/structures/build_structures.py --tile t_-4_4
    python3 blender/structures/build_structures.py --all --workers 2

Output per tile:

* ``blender_out/tiles/{tile}/tile_structures.glb`` -- one mesh per part (elevated steel, viaduct
  concrete, pier deck, pier piles, seawall, jetty), tile-local in X/Y and absolute NAVD88 in Z, the
  same convention as ``tile_buildings.glb`` and ``tile_pavement.glb``.
* ``blender_out/tiles/{tile}/structures_manifest.json`` -- what was built, from which rows, with the
  measured dimensions it was built from.

Why this stage exists
---------------------
``data/processed/transit/rail_structures.parquet`` holds 986 km of surveyed rail structure and
``data/processed/water/structures.parquet`` 166 ha of pier, seawall and jetty. Neither had a single
consumer that produced geometry: the elevated railways of Queens, Brooklyn and the Bronx -- the most
recognisable street-level structures in the outer boroughs, and the thing a driver on Roosevelt
Avenue or Jerome Avenue is under for kilometres at a time -- were not in the world at all, and
neither were the piers the Hudson and East River waterfronts are made of.

What it does *not* build, and why
---------------------------------
Sampling the landscape the engine will build, perpendicular to 200 structures of each class:

* an **embankment** stands 3.69 m above its flanks in the terrain already (92 % of them over 1 m),
* an **open cut** runs 3.32 m below (81 % of them over 1 m down),
* an **elevated** structure has terrain 0.10 m *below* the flanks -- that is, flat, as it should be.

So the earthworks are already in the DEM and building them again would put a berm on a berm and a
trench in a trench. This stage builds what stands in the air: 505 km of elevated and viaduct
structure, and the waterfront, whose decks stand over water the terrain has as a flat plane.

Dimensions
----------
Every dimension is measured or published, and ``stlib`` says which for each. The deck **width** is
measured from the survey's own linework: it captures one centreline per track, so the tracks running
parallel through a place are the tracks one deck carries, and the width is their lateral spread plus
the overhang. That gives 11.3 m and three tracks for the Jerome Avenue, Flushing, White Plains Road
and Jamaica elevateds, 12.0 m for the Culver Viaduct and 18.0 m over four tracks for the LIRR Main
Line, which is what those structures are.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "blender" / "structures"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import stlib  # noqa: E402

LOG = logging.getLogger("nycsim.structures")

PROCESSED = REPO_ROOT / "data" / "processed"
RAIL = PROCESSED / "transit" / "rail_structures.parquet"
WATER = PROCESSED / "water" / "structures.parquet"
STATIONS = PROCESSED / "transit" / "stations.parquet"
TILES_DATA = PROCESSED / "tiles"
OUT_ROOT = REPO_ROOT / "blender_out" / "tiles"
GLB_NAME = "tile_structures.glb"
MANIFEST_NAME = "structures_manifest.json"
SCHEMA_VERSION = 1
TILE_SIZE_M = 1000.0

#: Rail classes this stage builds. The other two are earthworks the terrain already carries.
BUILT_RAIL_KINDS = ("elevated", "viaduct")

#: Water classes this stage builds, and the part name each becomes.
WATER_PARTS = {"pier": "pier_deck", "seawall": "seawall", "jetty": "jetty"}

#: The landmark index, whose entries own the geometry inside their own plan bounds.
#:
#: Two of the seven modelled bridges carry subway tracks -- the Manhattan Bridge (B, D, N, Q) and
#: the Williamsburg (J, M, Z) -- and OSM tags those crossings ``bridge=yes``, so the rail structure
#: table has them as 883 m and 600 m of elevated railway 39 m above the East River. They are real
#: and correctly measured, and they are also already modelled, by the landmark. Building a second
#: deck through a landmark is the same mistake as drawing pavement through one (DEVIATIONS I11b), so
#: a structure inside a landmark's plan bounds is the landmark's to draw.
LANDMARKS_INDEX = PROCESSED / "landmarks" / "landmarks.json"


def tile_origin(tile: str) -> tuple[float, float]:
    _, tx, ty = tile.split("_", 2)
    return float(int(tx)) * TILE_SIZE_M, float(int(ty)) * TILE_SIZE_M


def landmark_boxes(index_path: Path = LANDMARKS_INDEX, *, rail_only: bool = True):
    """Plan bounds of the landmarks that model railway tracks of their own, in NYC_TM metres.

    ``build_levels.py`` spawns landmarks with a zero rotator, so ``bounds_local_m`` is already in the
    world's axes and the box is the origin plus the bounds.

    ``rail_only`` keeps the three bridges whose catalogues declare tracks -- the Manhattan, the
    Williamsburg and the Hell Gate. Ceding to *every* landmark would be wrong: these are axis-aligned
    boxes around structures that run diagonally, so the Manhattan Bridge's box alone covers 854 x
    1830 m of Chinatown and DUMBO, and an El passing through that box is not on the bridge.
    """
    import shapely

    if not index_path.is_file():
        return [], []
    doc = json.loads(index_path.read_text())
    boxes, names = [], []
    for rec in doc.get("landmarks", []):
        if rail_only and not rec.get("rail_tracks"):
            continue
        o = rec.get("origin_tm")
        b = rec.get("bounds_local_m") or {}
        lo, hi = b.get("min"), b.get("max")
        if not (o and lo and hi):
            continue
        boxes.append(shapely.box(o[0] + lo[0], o[1] + lo[1], o[0] + hi[0], o[1] + hi[1]))
        names.append(rec.get("stem") or rec.get("id") or "?")
    return boxes, names


def _clip_lines(geom, box):
    """The parts of a line inside the tile, as arrays of 2-D coordinates."""
    import shapely

    piece = shapely.intersection(geom, box)
    if piece.is_empty:
        return []
    out = []
    for g in shapely.get_parts(shapely.geometrycollections([piece]) if piece.geom_type == "GeometryCollection" else piece) \
            if piece.geom_type in ("MultiLineString", "GeometryCollection") else [piece]:
        if g.geom_type != "LineString" or g.length < 0.5:
            continue
        out.append(np.asarray(g.coords)[:, :2])
    return out


def _clip_rings(geom, box):
    """The exterior rings of a polygon clipped to the tile, each as an (N,2) array."""
    import shapely

    piece = shapely.intersection(geom, box)
    if piece.is_empty:
        return []
    rings = []
    parts = shapely.get_parts(piece) if piece.geom_type.startswith("Multi") or piece.geom_type == "GeometryCollection" else [piece]
    for g in parts:
        if g.geom_type != "Polygon" or g.area < 1.0:
            continue
        r = np.asarray(g.exterior.coords)[:-1, :2]
        if len(r) >= 3:
            rings.append(r)
    return rings


def build_tile(tile: str, *, out_root: Path = OUT_ROOT, rail_path: Path = RAIL,
               water_path: Path = WATER, station_path: Path = STATIONS,
               ground_from_terrain: bool = True) -> dict:
    import pyarrow.parquet as pq
    import shapely

    from nycsim_pipeline.terrain.landscape_grid import LandscapeSampler

    t0 = time.perf_counter()
    x0, y0 = tile_origin(tile)
    box = shapely.box(x0, y0, x0 + TILE_SIZE_M, y0 + TILE_SIZE_M)
    sampler = LandscapeSampler(TILES_DATA) if ground_from_terrain else None
    lm_boxes, lm_names = landmark_boxes()
    lm_tree = shapely.STRtree(lm_boxes) if lm_boxes else None
    ceded: dict[str, int] = {}

    def owned_by_a_landmark(geom) -> str | None:
        """The landmark whose plan bounds contain most of ``geom``, if one does."""
        if lm_tree is None:
            return None
        for h in lm_tree.query(geom, predicate="intersects"):
            box_ = lm_boxes[int(h)]
            if shapely.intersection(geom, box_).length >= 0.5 * max(geom.length, 1e-9):
                return lm_names[int(h)]
        return None

    def ground(xs, ys):
        """Terrain under a column, in absolute NYC_TM. Falls back to the row's own median ground."""
        if sampler is None:
            return np.full(len(np.atleast_1d(xs)), np.nan)
        return sampler.height(np.asarray(xs, dtype=np.float64) + x0, np.asarray(ys, dtype=np.float64) + y0)

    bufs: dict[str, stlib.MeshBuffer] = {}
    #: (x_local, y_local, soffit_z) along every deck built, for the clearance check below.
    deck_probes: list[tuple[float, float, float]] = []

    def buf(part: str) -> stlib.MeshBuffer:
        return bufs.setdefault(part, stlib.MeshBuffer(part=part))

    # ---- rail structures -----------------------------------------------------------------------
    rail_rows = 0
    rail_km = 0.0
    columns = 0
    by_kind: dict[str, int] = {}
    dropped: dict[str, int] = {}
    if rail_path.is_file():
        table = pq.read_table(rail_path)
        kinds = np.asarray(table.column("kind").to_pylist(), dtype=object)
        keep = np.isin(kinds, np.asarray(BUILT_RAIL_KINDS, dtype=object))
        idx = np.nonzero(keep)[0]
        geoms = np.asarray(shapely.from_wkb(table.column("geometry").to_pylist()), dtype=object)
        hit = shapely.STRtree(geoms[idx]).query(box, predicate="intersects")
        cols = {n: table.column(n).to_pylist() for n in
                ("deck_width_m", "deck_z", "deck_z_start", "deck_z_end", "ground_z",
                 "deck_height_source", "deck_width_source", "track_count", "name", "structure_id")}
        for h in hit:
            j = int(idx[int(h)])
            kind = str(kinds[j])
            width = cols["deck_width_m"][j]
            za, zb = cols["deck_z_start"][j], cols["deck_z_end"][j]
            if za is None or zb is None or not math.isfinite(za) or not math.isfinite(zb):
                za = zb = cols["deck_z"][j]
            if width is None or not math.isfinite(width) or za is None or not math.isfinite(za):
                dropped["no width or deck elevation"] = dropped.get("no width or deck elevation", 0) + 1
                continue
            thickness = stlib.DECK_THICKNESS_M[kind]
            part = "el_steel" if kind == "elevated" else "viaduct_concrete"
            whole = geoms[j]
            owner = owned_by_a_landmark(whole)
            if owner is not None:
                ceded[owner] = ceded.get(owner, 0) + 1
                continue
            total_len = max(whole.length, 1e-6)
            start = np.asarray(whole.coords)[0, :2]
            for coords in _clip_lines(whole, box):
                local = coords - np.array([x0, y0])
                # The deck ramps between the structure's two joined endpoints; a clipped piece takes
                # the elevations of its own ends along that ramp, so the tile seam is continuous.
                s0 = float(np.hypot(*(coords[0] - start)))
                s1 = float(np.hypot(*(coords[-1] - start)))
                z_start = za + (zb - za) * min(1.0, s0 / total_len)
                z_end = za + (zb - za) * min(1.0, s1 / total_len)
                added = _deck_with_grade(buf(part), local, float(width), z_start, z_end, thickness)
                if not added:
                    continue
                probe, _ = stlib.resample(local, 10.0)
                if len(probe) > 1:
                    seg = np.linalg.norm(np.diff(probe, axis=0), axis=1)
                    frac = np.concatenate([[0.0], np.cumsum(seg)])
                    frac = frac / (frac[-1] or 1.0)
                    for (px, py), f in zip(probe, frac):
                        deck_probes.append((float(px), float(py),
                                            z_start + (z_end - z_start) * float(f) - thickness))
                columns += stlib.bents(
                    buf(part), local, float(width), min(z_start, z_end) - thickness,
                    ground if sampler is not None else float(cols["ground_z"][j] or 0.0),
                    stlib.BENT_SPACING_M[kind], stlib.COLUMN_SIDE_M[kind],
                    stlib.COLUMN_INSET_M[kind], stlib.CAP_DEPTH_M[kind])
                rail_km += float(np.sum(np.linalg.norm(np.diff(coords, axis=0), axis=1))) / 1000.0
            rail_rows += 1
            by_kind[kind] = by_kind.get(kind, 0) + 1

    clearance = _clearance(deck_probes, sampler, x0, y0)

    # ---- waterfront ----------------------------------------------------------------------------
    water_rows = 0
    piles = 0
    water_by_kind: dict[str, int] = {}
    if water_path.is_file():
        table = pq.read_table(water_path)
        kinds = np.asarray(table.column("kind").to_pylist(), dtype=object)
        geoms = np.asarray(shapely.from_wkb(table.column("geometry").to_pylist()), dtype=object)
        deck = table.column("deck_z_m").to_pylist()
        hit = shapely.STRtree(geoms).query(box, predicate="intersects")
        for h in hit:
            j = int(h)
            kind = str(kinds[j])
            part = WATER_PARTS.get(kind)
            if part is None:
                continue
            z_top = deck[j]
            if z_top is None or not math.isfinite(z_top):
                dropped["no deck elevation"] = dropped.get("no deck elevation", 0) + 1
                continue
            z_bottom = stlib.WATER_Z_M - stlib.UNDERWATER_M
            built = False
            for ring in _clip_rings(geoms[j], box):
                local = ring - np.array([x0, y0])
                tris = stlib.ear_clip(local)
                if not len(tris):
                    continue
                if kind == "pier":
                    buf(part).add_prism(local, z_top - stlib.PIER_DECK_THICKNESS_M, z_top, tris)
                    for px, py in stlib.pile_grid(local, stlib.PILE_SPACING_M):
                        buf("pier_pile").add_box(px, py, z_bottom,
                                                 z_top - stlib.PIER_DECK_THICKNESS_M,
                                                 stlib.PILE_DIAMETER_M, stlib.PILE_DIAMETER_M)
                        piles += 1
                else:
                    buf(part).add_prism(local, z_bottom, z_top, tris)
                buf(part).pieces += 1
                built = True
            if built:
                water_rows += 1
                water_by_kind[kind] = water_by_kind.get(kind, 0) + 1

    # ---- stations ------------------------------------------------------------------------------
    # 972 elevated stations and 313 at grade, surveyed as roof outlines and modelled by nothing. The
    # 150 that fall inside a building footprint are the buildings stage's, not this one's.
    station_rows = 0
    station_columns = 0
    station_by_kind: dict[str, int] = {}
    if station_path.is_file():
        table = pq.read_table(station_path)
        kinds = np.asarray(table.column("kind").to_pylist(), dtype=object)
        geoms = np.asarray(shapely.from_wkb(table.column("geometry").to_pylist()), dtype=object)
        base = table.column("base_z").to_pylist()
        roof = table.column("roof_z").to_pylist()
        covered = np.asarray(table.column("in_a_building_footprint"), dtype=bool)
        hit = shapely.STRtree(geoms).query(box, predicate="intersects")
        for h in hit:
            j = int(h)
            if covered[j]:
                dropped["already a building"] = dropped.get("already a building", 0) + 1
                continue
            b, r = base[j], roof[j]
            if b is None or r is None or not (math.isfinite(b) and math.isfinite(r)) or r <= b:
                dropped["no station elevation"] = dropped.get("no station elevation", 0) + 1
                continue
            built = False
            for ring in _clip_rings(geoms[j], box):
                local = ring - np.array([x0, y0])
                if str(kinds[j]) == "elevated_station":
                    station_columns += stlib.station(buf("platform"), buf("canopy"), local, b, r)
                    built = True
                elif stlib.station_house(buf("station_house"), local, b, r):
                    built = True
            if built:
                station_rows += 1
                station_by_kind[str(kinds[j])] = station_by_kind.get(str(kinds[j]), 0) + 1

    # ---- Blender assembly ----------------------------------------------------------------------
    import nycsim_bpy as nb

    nb.reset_scene()
    objects = []
    mesh_stats = []
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for part, b in sorted(bufs.items()):
        if not b.faces:
            continue
        pos = np.asarray(b.verts, dtype=np.float64)
        tri = np.asarray(b.faces, dtype=np.int64)
        name = f"{tile}_struct_{part}"
        # The material name, not the mesh name, is what survives the glTF import as the slot name,
        # and import_assets.py hangs the UPhysicalMaterial on it by that name. So it carries no tile:
        # struct_el_steel is the same slot in all 1,402 tiles.
        slot = f"struct_{part}"
        ob = nb.mesh_object(name, pos, tri, materials=[_material(slot, part)])
        objects.append(ob)
        lo = np.minimum(lo, pos.min(axis=0))
        hi = np.maximum(hi, pos.max(axis=0))
        mesh_stats.append({"mesh": name, "part": part, "material": slot,
                           "texture": stlib.MATERIALS[part],
                           "surface_class": stlib.SURFACE_CLASS[part],
                           "pieces": b.pieces, "vertices": len(pos), "triangles": len(tri)})

    out_dir = Path(out_root) / tile
    glb = out_dir / GLB_NAME
    if objects:
        out_dir.mkdir(parents=True, exist_ok=True)
        nb.export_glb(glb, objects=objects, apply_modifiers=False, texcoords=False, tangents=False,
                      export_extras=True, export_normals=True, export_animations=False, extras={
                          "stage": "structures", "tile": tile,
                          "origin_m": [x0, y0, 0.0], "crs": "NYC_TM",
                          "vertical_datum": "NAVD88 metres",
                          "sources": ["data/processed/transit/rail_structures.parquet",
                                      "data/processed/water/structures.parquet",
                                      "data/processed/transit/stations.parquet"],
                          "built_rail_kinds": list(BUILT_RAIL_KINDS),
                          "not_built": {"embankment": "the terrain already carries the berm "
                                                      "(+3.69 m at the centreline, measured)",
                                        "open_cut": "the terrain already carries the cutting "
                                                    "(-3.32 m at the centreline, measured)"},
                          "surface_class": {m["material"]: m["surface_class"] for m in mesh_stats},
                      })
    elif glb.exists():
        glb.unlink()

    size = glb.stat().st_size if glb.exists() else 0
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "structures",
        "tile": tile,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": nb.git_commit(),
        "generator": "blender/structures/build_structures.py",
        "sources": [str(rail_path.relative_to(REPO_ROOT)), str(water_path.relative_to(REPO_ROOT)),
                    str(station_path.relative_to(REPO_ROOT))],
        "rail": {"rows": rail_rows, "km": round(rail_km, 3), "by_kind": by_kind, "columns": columns},
        "water": {"rows": water_rows, "by_kind": water_by_kind, "piles": piles},
        "stations": {"rows": station_rows, "by_kind": station_by_kind, "columns": station_columns},
        "not_built": {"embankment": "terrain carries the berm", "open_cut": "terrain carries the cutting"},
        "dropped": dropped,
        "ceded_to_landmarks": ceded,
        "soffit_clearance_m": clearance,
        "meshes": mesh_stats,
        "triangles": sum(m["triangles"] for m in mesh_stats),
        "vertices": sum(m["vertices"] for m in mesh_stats),
        "bounds_local_m": {"min": _fin(lo), "max": _fin(hi)},
        "origin_m": [x0, y0, 0.0],
        "dimensions_m": {
            "deck_thickness": stlib.DECK_THICKNESS_M, "bent_spacing": stlib.BENT_SPACING_M,
            "column_side": stlib.COLUMN_SIDE_M, "column_inset": stlib.COLUMN_INSET_M,
            "cap_depth": stlib.CAP_DEPTH_M, "pier_deck_thickness": stlib.PIER_DECK_THICKNESS_M,
            "pile_spacing": stlib.PILE_SPACING_M, "pile_diameter": stlib.PILE_DIAMETER_M,
            "underwater_cut": stlib.UNDERWATER_M,
            "platform_thickness": stlib.PLATFORM_THICKNESS_M,
            "canopy_thickness": stlib.CANOPY_THICKNESS_M,
            "canopy_column_spacing": stlib.CANOPY_COLUMN_SPACING_M,
        },
        "terrain_tiles_missing": sorted(sampler.missing) if sampler is not None else [],
        "glb": {"path": _rel(glb) if glb.exists() else "", "bytes": size,
                "sha256": _sha256(glb) if glb.exists() else ""},
        "seconds": {"total": round(time.perf_counter() - t0, 3)},
    }
    if objects:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


#: How far apart the deck is cut along a graded structure, metres. A deck that ramps has to be
#: broken into steps somewhere; 20 m keeps the vertical error of a straight chord under a millimetre
#: at the 4 % maximum grade and costs two triangles per step.
GRADE_STEP_M = 20.0


def _deck_with_grade(buf: stlib.MeshBuffer, local: np.ndarray, width: float,
                     z_start: float, z_end: float, thickness: float) -> int:
    """The deck of one clipped piece, ramping linearly from ``z_start`` to ``z_end``."""
    if abs(z_end - z_start) < 1e-3:
        return stlib.deck_ribbon(buf, local, width, z_start, thickness)
    pts, _ = stlib.resample(local, GRADE_STEP_M)
    if len(pts) < 2:
        return 0
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(s[-1]) or 1.0
    added = 0
    for i in range(len(pts) - 1):
        za = z_start + (z_end - z_start) * s[i] / total
        zb = z_start + (z_end - z_start) * s[i + 1] / total
        added += stlib.deck_ribbon(buf, pts[i:i + 2], width, (za + zb) / 2.0, thickness)
    return added


_LOOK = {
    "el_steel": ((0.29, 0.33, 0.30, 1.0), 0.62, 0.75),
    "platform": ((0.66, 0.65, 0.63, 1.0), 0.90, 0.0),
    "canopy": ((0.42, 0.44, 0.45, 1.0), 0.55, 0.60),
    "station_house": ((0.60, 0.52, 0.42, 1.0), 0.88, 0.0),
    "viaduct_concrete": ((0.62, 0.61, 0.58, 1.0), 0.85, 0.0),
    "pier_deck": ((0.60, 0.58, 0.55, 1.0), 0.88, 0.0),
    "pier_pile": ((0.48, 0.46, 0.43, 1.0), 0.90, 0.0),
    "seawall": ((0.58, 0.57, 0.55, 1.0), 0.88, 0.0),
    "jetty": ((0.46, 0.45, 0.43, 1.0), 0.95, 0.0),
}


def _clearance(probes, sampler, x0: float, y0: float) -> dict:
    """How far every deck's soffit stands above the terrain the engine will build.

    A deck is only a deck if it is over the ground. This measures the thing that would go wrong --
    a structure whose surveyed deck elevation is below the hill it crosses, which is what a bad
    class-median fallback looks like -- rather than asserting it did not.
    """
    if not probes or sampler is None:
        return {"samples": 0}
    p = np.asarray(probes, dtype=np.float64)
    ground = sampler.height(p[:, 0] + x0, p[:, 1] + y0)
    ok = np.isfinite(ground)
    if not ok.any():
        return {"samples": int(len(p)), "terrain_missing": int(len(p))}
    d = p[ok, 2] - ground[ok]
    return {
        "samples": int(ok.sum()),
        "terrain_missing": int((~ok).sum()),
        "min_m": round(float(d.min()), 3),
        "p01_m": round(float(np.percentile(d, 1)), 3),
        "median_m": round(float(np.median(d)), 3),
        "p99_m": round(float(np.percentile(d, 99)), 3),
        "max_m": round(float(d.max()), 3),
        "below_ground_fraction": round(float(np.mean(d < 0.0)), 5),
        "under_3m_fraction": round(float(np.mean(d < 3.0)), 5),
    }


def _material(name: str, part: str):
    import nycsim_bpy as nb

    colour, rough, metal = _LOOK[part]
    return nb.pbr_material(name, base_color=colour, roughness=rough, metallic=metal)


def _fin(v: np.ndarray) -> list:
    return [round(float(x), 4) if math.isfinite(float(x)) else None for x in v]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _purge() -> None:
    import bpy

    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)


def available_tiles() -> list[str]:
    """Tiles any structure reaches into, from the two source tables' own bounds."""
    import pyarrow.parquet as pq
    import shapely

    tiles: set[str] = set()
    for path, kinds in ((RAIL, BUILT_RAIL_KINDS), (WATER, tuple(WATER_PARTS)),
                        (STATIONS, ("elevated_station", "station"))):
        if not path.is_file():
            continue
        t = pq.read_table(path, columns=["kind", "geometry"])
        k = np.asarray(t.column("kind").to_pylist(), dtype=object)
        g = np.asarray(shapely.from_wkb(t.column("geometry").to_pylist()), dtype=object)
        sel = np.isin(k, np.asarray(kinds, dtype=object))
        for geom in g[sel]:
            minx, miny, maxx, maxy = geom.bounds
            for tx in range(int(math.floor(minx / TILE_SIZE_M)), int(math.floor(maxx / TILE_SIZE_M)) + 1):
                for ty in range(int(math.floor(miny / TILE_SIZE_M)), int(math.floor(maxy / TILE_SIZE_M)) + 1):
                    tiles.add(f"t_{tx}_{ty}")
    return sorted(tiles, key=lambda s: tuple(int(v) for v in s.split("_")[1:]))


def run_serial(tiles: list[str], args) -> int:
    ok = 0
    for i, tile in enumerate(tiles, 1):
        out = Path(args.out) / tile / GLB_NAME
        if args.skip_existing and out.exists() and (out.parent / MANIFEST_NAME).exists():
            print(f"[{i}/{len(tiles)}] {tile} skipped (exists)", flush=True)
            ok += 1
            continue
        try:
            m = build_tile(tile, out_root=Path(args.out))
        except Exception as exc:  # noqa: BLE001
            LOG.exception("tile %s failed", tile)
            print(f"[{i}/{len(tiles)}] {tile} FAILED: {exc}", flush=True)
            continue
        finally:
            _purge()
        ok += 1
        print(f"[{i}/{len(tiles)}] {tile} rail={m['rail']['rows']} km={m['rail']['km']} "
              f"cols={m['rail']['columns']} water={m['water']['rows']} piles={m['water']['piles']} "
              f"stn={m['stations']['rows']} tris={m['triangles']} bytes={m['glb']['bytes']} "
              f"t={m['seconds']['total']}s", flush=True)
    return 0 if ok == len(tiles) else 1


def run_parallel(tiles: list[str], args) -> int:
    n = max(1, min(args.workers, 2))
    logdir = Path(args.out) / "_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    procs = []
    for i in range(n):
        chunk = tiles[i::n]
        if not chunk:
            continue
        listfile = logdir / f"structures_worker{i}.tiles"
        listfile.write_text("\n".join(chunk))
        cmd = ["nice", "-n", str(args.nice), sys.executable, str(Path(__file__).resolve()),
               "--tile-list", str(listfile), "--out", str(args.out)]
        if args.skip_existing:
            cmd.append("--skip-existing")
        log = open(logdir / f"structures_worker{i}.log", "w")
        procs.append((subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT), log))
        print(f"worker {i}: {len(chunk)} tiles -> {logdir / f'structures_worker{i}.log'}", flush=True)
    rc = 0
    for p, log in procs:
        rc |= p.wait()
        log.close()
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tile")
    g.add_argument("--tiles")
    g.add_argument("--tile-list")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=str(OUT_ROOT))
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--nice", type=int, default=10)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.tile:
        tiles = [args.tile]
    elif args.tiles:
        tiles = [t for t in args.tiles.split(",") if t]
    elif args.tile_list:
        tiles = [t.strip() for t in Path(args.tile_list).read_text().split("\n") if t.strip()]
    else:
        tiles = available_tiles()
    if args.limit:
        tiles = tiles[: args.limit]
    if not tiles:
        print("no tiles", file=sys.stderr)
        return 1
    print(f"{len(tiles)} tile(s)", flush=True)
    return run_parallel(tiles, args) if args.workers > 1 else run_serial(tiles, args)


if __name__ == "__main__":
    sys.exit(main())
