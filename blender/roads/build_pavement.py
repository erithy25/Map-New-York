#!/usr/bin/env python3
"""Generate the NYCSim road surfaces for one tile (or the whole city) as glTF 2.0.

    python3 blender/roads/build_pavement.py --tile t_-4_4
    python3 blender/roads/build_pavement.py --all --workers 2

Output per tile:

* ``blender_out/tiles/{tile}/tile_pavement.glb`` -- one mesh per (kind, surface) pair, so Unreal
  gets one material slot per real surface and can hang the matching ``UPhysicalMaterial`` on it.
  Geometry is tile-local in X/Y and absolute NAVD88 in Z, exactly like ``tile_buildings.glb``, so
  the same actor placement at the tile origin serves both.
* ``blender_out/tiles/{tile}/pavement_manifest.json`` -- counts per kind, triangles, the draping
  residual measured against the surface it was draped on, bounds, and provenance.

Why this stage exists
---------------------
``data/processed/roads/pavement/{tile}.parquet`` (DATA_CONTRACTS §7) holds the real DoITT
planimetric roadbed, sidewalk, median, plaza, curb and parking-lot polygons plus the derived
crosswalks -- 972 tiles of them.  Until now the **only** consumer was the still-frame renderer
``blender/verify/scene.py``.  Nothing carried them into the engine, so the car would have driven on
the bare ``ALandscape`` built from the DEM: no asphalt, no curb, no crossings, and no surface for
``UNYCVehicleMovementComponent``'s friction model to resolve, which is built around exactly these
materials.

Three things this stage does that the renderer does not
-------------------------------------------------------
**It drapes on the surface the engine will actually have.**  ``UNYCTerrainImporter`` resamples the
501-sample 2 m heightmap to the 505 samples a landscape component size permits, so the landscape is
not the source grid.  Measured over the ring vertices of four tiles it stands a mean +0.005 m above
it, and above 0.10 m -- higher than the roadbed's own lift -- at 0.03-0.32 % of them, peaking at
+0.90 m.  Draping on ``nycsim_pipeline.terrain.landscape_grid.LandscapeSampler`` removes that error
rather than budgeting for it.

**It refines the triangulation.**  Ear clipping a planimetric polygon gives a median edge of 0.5 m
but a 99th percentile of 66 m and a longest edge of 306 m, and a triangle that big cannot follow the
ground: sampling inside them the mesh sat a median 2-6 mm from the terrain but a 99th percentile of
145-208 mm and an extreme of 4.0 m.  Every ring is segmentised and every triangle bisected until no
edge exceeds ``--max-edge`` (default 4 m), conforming, so the slab stays watertight.

**It gives the slabs thickness.**  Each polygon carries a downward skirt.  In the renders the
pavement is a zero-thickness sheet, so the 0.15 m curb reveal reads only as a silhouette; here it is
a real vertical concrete face, which is one of the most visible things at eye level from a car.  The
skirt also means that where the landscape's own two-triangle-per-quad surface rises above the draped
top -- the residual this stage cannot remove, measured and reported per tile -- the seam is a sliver
rather than a window into the void under the road.

Surfaces and friction
---------------------
Each mesh is named ``{tile}_pave_{kind}_{surface}`` and carries a material of the same stem.  Its
``extras.surface_class`` is the ``nycsim_gameplay::SurfaceClass`` index, which is also the
``EPhysicalSurface`` index ``DefaultEngine.ini`` declares and which
``UNYCVehicleMovementComponent::ToSurfaceClass`` casts straight across, so the importer can attach
the right ``UPhysicalMaterial`` from the mesh alone.  A crosswalk resolves to ``PaintedMarking`` and
a sidewalk to ``Sidewalk`` rather than to what they are made of, because what matters to a tyre
there is the paint and the kerbside, not the concrete underneath.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "blender" / "common"))
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
sys.path.insert(0, str(_HERE))

import pvlib  # noqa: E402
from nycsim_pipeline.terrain.landscape_grid import LandscapeSampler, TILE_SIZE_M  # noqa: E402

LOG = logging.getLogger("nycsim.roads.build_pavement")

PROCESSED = Path(os.environ.get("NYCSIM_PROCESSED", REPO_ROOT / "data" / "processed"))
PAVEMENT_DIR = PROCESSED / "roads" / "pavement"
MARKINGS_DIR = PROCESSED / "roads" / "markings"
SEGMENTS_PARQUET = PROCESSED / "roads" / "segments.parquet"
TILES_DATA = PROCESSED / "tiles"
LANDMARK_GROUND = PROCESSED / "landmarks" / "ground_outlines.parquet"
OUT_ROOT = Path(os.environ.get("NYCSIM_BLENDER_OUT", REPO_ROOT / "blender_out")) / "tiles"

SCHEMA_VERSION = 1
GLB_NAME = "tile_pavement.glb"
MANIFEST_NAME = "pavement_manifest.json"
#: A triangle is split while the ground at an edge's midpoint is further than the tolerance from the
#: straight line between its endpoints. The tolerance is not one number: it is a fraction of the
#: kind's own lift, because the lift is exactly the budget before the terrain shows through. Half of
#: it gives the roadbed 50 mm against its 0.10 m lift and the sidewalk 125 mm against its 0.25 m,
#: which is right - a 100 mm undulation under a kerb is invisible and under an asphalt lane is not.
#:
#: A single 50 mm tolerance for everything produced 3.4 GB of pavement for 47 tiles, 221 MB of it in
#: one Lower Manhattan tile, because it spent the sidewalk's whole subdivision budget resolving
#: detail nobody can see.
DEFAULT_TOL_FRACTION = 0.5
#: Explicit override; 0 means "use the fraction of the lift".
DEFAULT_TOL_M = 0.0
#: Refinement floor. The heightmap samples every 2 m (DATA_CONTRACTS 3), so an edge shorter than that
#: is being split to resolve interpolation rather than terrain: the midpoint error it is chasing is
#: an artefact of the bilinear read, not a feature of the ground. At 1 m the boundary of a
#: kilometre-long avenue sidewalk collected 1,700 vertices and, with a wall raised on each, half the
#: file.
DEFAULT_MIN_EDGE_M = 2.0
#: Grid cell the polygons are cut on before anything else. A little above the heightmap's own 2 m
#: sampling, so a cell spans about one terrain sample and the surface has somewhere to bend.
DEFAULT_CELL_M = 2.5
#: Douglas-Peucker tolerance applied to the source rings before anything else. The planimetric
#: polygons are digitised far finer than their own positional accuracy: one Midtown tile carries
#: 94,309 ring vertices, and simplifying at 2 cm - a fortieth of a paint stripe, and two orders below
#: the terrain's 0.384 m RMS - leaves 23,945 of them, a 3.9x cut for an error nothing can see.
DEFAULT_SIMPLIFY_M = 0.02
#: Which kinds carry a downward skirt. The curb is the one that must: its roadbed-facing side is the
#: real 0.15 m concrete face, one of the most visible things at eye level from a car, and without a
#: skirt it is a zero-thickness sheet that reads only as a silhouette. The raised pedestrian surfaces
#: get one too, so a free edge at a plaza or a park closes rather than showing its underside. The
#: roadbed, the crosswalk and the parking lots do not: they are the lowest surfaces in the stack and
#: their edges are covered by the curb that bounds them, so a skirt there is triangles nobody sees.
DEFAULT_SKIRT_KINDS = frozenset({1, 2, 3, 4})
#: Cap regardless of error: a triangle running along a contour can be arbitrarily long with almost no
#: midpoint error, and such a triangle shades badly and makes a poor skirt.
DEFAULT_MAX_EDGE_M = 25.0
#: How many interior points per tile the manifest's draping-residual check samples.
RESIDUAL_SAMPLES = 4000


def _parse_kinds(s: str) -> frozenset:
    return frozenset(int(v) for v in str(s).replace(" ", "").split(",") if v != "")


def parse_tile(tile: str) -> tuple[int, int]:
    body = tile[2:] if tile.startswith("t_") else tile
    split = body.find("_", 1)
    return int(body[:split]), int(body[split + 1:])


def available_tiles() -> list[str]:
    if not PAVEMENT_DIR.is_dir():
        return []
    return sorted(p.stem for p in PAVEMENT_DIR.glob("t_*.parquet"))


# --------------------------------------------------------------------------- landmark ground


def load_landmark_ground(bounds: tuple[float, float, float, float]):
    """Plan outlines of the ground the landmarks supply themselves, clipped to a tile's bounds.

    The city's pavement and a landmark's own deck are two statements about the same surface, and
    where the landmark models the ground its version is the one built from that place's own outline
    (``blender/verify/scene.py::landmark_ground_outlines``, DEVIATIONS I11b).  The renderer computes
    this from loaded glTF; here it is read from the file
    ``blender/landmarks/export_ground_outlines.py`` writes once, because 972 tiles across parallel
    workers cannot each load 93 models.
    """
    if not LANDMARK_GROUND.exists():
        return []
    try:
        import pyarrow.parquet as pq
        import shapely
    except Exception:
        return []
    try:
        t = pq.read_table(LANDMARK_GROUND, columns=["geometry"])
    except Exception as exc:
        LOG.warning("landmark ground outlines unreadable: %s", exc)
        return []
    box = None
    out = []
    for blob in t.column("geometry").to_pylist():
        try:
            g = shapely.from_wkb(blob)
        except Exception:
            continue
        if box is None:
            box = shapely.box(*bounds)
        if shapely.intersects(g, box):
            out.append(g)
    return out


def _outside(cut, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """True where the point is outside every cut outline."""
    import shapely

    keep = np.ones(xs.shape, dtype=bool)
    for g in cut:
        keep &= ~shapely.contains_xy(g, xs, ys)
    return keep


# --------------------------------------------------------------------------- one tile


# --------------------------------------------------------------------------- curb ramps

#: The props table, which is where the DOT pedestrian-ramp inventory lands (furniture kind 9).
PROPS_DIR = PROCESSED / "tiles"

#: Prop kind of a DOT pedestrian ramp.
RAMP_KIND = 9

#: How far outside the tile a ramp may sit and still be built into it: a ramp on the boundary has
#: half its rectangle in each tile, and drawing it twice is better than drawing half of it.
RAMP_MARGIN_M = 6.0

#: How far a ramp may be from a roadbed edge and still be given that edge's direction, metres.
#: A ramp is at a kerb by definition; one with no roadbed within this is in a plaza or a parking
#: lot the pavement survey did not connect, and it is dropped rather than pointed somewhere.
RAMP_ROADBED_SEARCH_M = 12.0


def load_ramps(tile: str, bounds: tuple[float, float, float, float]) -> list[dict]:
    """The surveyed pedestrian ramps of this tile and the strip of its neighbours around it.

    Each row carries the DOT inventory's own ``width_m`` and ``running_slope_pct``, which is what
    makes the ramp a measurement rather than a shape: the run is the kerb reveal divided by the
    measured slope, and the width is the measured width.
    """
    import pyarrow.parquet as pq

    x0, y0, x1, y1 = bounds
    out: list[dict] = []
    tx, ty = parse_tile(tile)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            path = PROPS_DIR / f"t_{tx + dx}_{ty + dy}" / "props.parquet"
            if not path.is_file():
                continue
            try:
                t = pq.read_table(path, columns=["kind", "x", "y", "attrs"])
            except Exception as exc:  # noqa: BLE001
                LOG.warning("%s: props unreadable: %s", path, exc)
                continue
            kind = np.asarray(t.column("kind").to_numpy(zero_copy_only=False))
            idx = np.nonzero(kind == RAMP_KIND)[0]
            if not len(idx):
                continue
            xs = np.asarray(t.column("x").to_numpy(zero_copy_only=False))
            ys = np.asarray(t.column("y").to_numpy(zero_copy_only=False))
            attrs = t.column("attrs").to_pylist()
            for i in idx:
                px, py = float(xs[i]), float(ys[i])
                if not (x0 - RAMP_MARGIN_M <= px <= x1 + RAMP_MARGIN_M
                        and y0 - RAMP_MARGIN_M <= py <= y1 + RAMP_MARGIN_M):
                    continue
                try:
                    a = json.loads(attrs[i] or "{}")
                except (TypeError, json.JSONDecodeError):
                    a = {}
                out.append({"x": px, "y": py,
                            "width_m": a.get("width_m"), "slope_pct": a.get("running_slope_pct"),
                            "ramp_id": a.get("ramp_id"), "dws": a.get("dws")})
    return out


def ramp_slabs(ramps, roadbeds, sampler, x0: float, y0: float, cell_m: float,
               min_edge_m: float, max_edge_m: float):
    """``(SlabBuffer, cut polygons, report)`` for the ramps of one tile.

    The direction a ramp descends is not in the inventory -- every row's ``heading`` is NaN -- so it
    is taken from the pavement itself: the nearest point on a roadbed polygon's boundary is where
    the kerb is, and the ramp runs at it. A ramp with no roadbed within
    :data:`RAMP_ROADBED_SEARCH_M` is dropped rather than pointed in a guessed direction.
    """
    import shapely

    buf = pvlib.SlabBuffer(kind=8, surface=1)
    rects = []
    rep = {"ramps": len(ramps), "built": 0, "no_roadbed": 0, "no_triangulation": 0,
           "no_terrain": 0, "width_clamped": 0, "slope_missing": 0}
    if not ramps or not roadbeds:
        rep["no_roadbed"] = len(ramps)
        return buf, rects, rep
    tree = shapely.STRtree(roadbeds)
    for r in ramps:
        pt = shapely.Point(r["x"], r["y"])
        near = tree.query(shapely.buffer(pt, RAMP_ROADBED_SEARCH_M), predicate="intersects")
        if not len(near):
            rep["no_roadbed"] += 1
            continue
        j = int(min(near, key=lambda k: shapely.distance(pt, roadbeds[int(k)])))
        edge = shapely.get_exterior_ring(roadbeds[j])
        q = shapely.line_interpolate_point(edge, shapely.line_locate_point(edge, pt))
        dx, dy = float(q.x - r["x"]), float(q.y - r["y"])
        if math.hypot(dx, dy) < 1e-6:
            rep["no_roadbed"] += 1
            continue
        w = r["width_m"]
        try:
            w = float(w)
        except (TypeError, ValueError):
            w = None
        if w is None or not math.isfinite(w):
            w = pvlib.RAMP_WIDTH_M[0]
        wc = min(pvlib.RAMP_WIDTH_M[1], max(pvlib.RAMP_WIDTH_M[0], w))
        if abs(wc - w) > 1e-6:
            rep["width_clamped"] += 1
        if r["slope_pct"] in (None, ""):
            rep["slope_missing"] += 1
        run = pvlib.ramp_run_m(r["slope_pct"])
        # Anchor the ramp on the kerb, not on the survey point: the point is a median 0.76 m back
        # from the roadbed edge, so a rectangle centred on it would sit that far up the sidewalk.
        n = math.hypot(dx, dy)
        ux0, uy0 = dx / n, dy / n
        cx = float(q.x) - ux0 * (run / 2.0 - pvlib.RAMP_TOE_M)
        cy = float(q.y) - uy0 * (run / 2.0 - pvlib.RAMP_TOE_M)
        ring, (ux, uy) = pvlib.ramp_rect(cx, cy, dx, dy, wc, run)
        if ring is None:
            rep["no_roadbed"] += 1
            continue
        poly = shapely.Polygon(ring)
        pts, tris = pvlib.grid_triangulate(poly, min(cell_m, 0.6))
        if len(tris) == 0:
            rep["no_triangulation"] += 1
            continue
        pts, tris = pvlib.refine_to_terrain(pts, tris, sampler.height, tol_m=0.02,
                                            min_edge_m=0.25, max_edge_m=min(max_edge_m, 1.5))
        z = sampler.height(pts[:, 0], pts[:, 1])
        if np.isnan(z).all():
            rep["no_terrain"] += 1
            continue
        if np.isnan(z).any():
            z = np.where(np.isnan(z), float(np.nanmedian(z)), z)
        lift = pvlib.ramp_lift(pts, cx, cy, ux, uy, run)
        buf.add_polygon(pts - np.array([x0, y0]), z + lift, tris,
                        pvlib.PAVEMENT_KINDS[8][2], road_line=-1)
        rects.append(poly)
        rep["built"] += 1
    return buf, rects, rep


def build_tile(tile: str, *, out_root: Path = OUT_ROOT, tol_m: float = DEFAULT_TOL_M,
               tol_fraction: float = DEFAULT_TOL_FRACTION, cell_m: float = DEFAULT_CELL_M,
               min_edge_m: float = DEFAULT_MIN_EDGE_M, max_edge_m: float = DEFAULT_MAX_EDGE_M,
               simplify_m: float = DEFAULT_SIMPLIFY_M, skirt_kinds=DEFAULT_SKIRT_KINDS,
               cut_landmark_ground: bool = True, road_z: bool = True,
               with_ramps: bool = True) -> dict:
    import mapbox_earcut as earcut
    import nycsim_bpy as nb
    import pyarrow.parquet as pq
    import shapely

    t0 = time.perf_counter()
    tx, ty = parse_tile(tile)
    x0, y0 = tx * TILE_SIZE_M, ty * TILE_SIZE_M
    src = PAVEMENT_DIR / f"{tile}.parquet"
    if not src.exists():
        raise FileNotFoundError(src)

    table = pq.read_table(src, columns=["kind", "surface", "roughness_seed", "geometry"])
    kinds = table.column("kind").to_pylist()
    surfaces = table.column("surface").to_pylist()
    seeds = table.column("roughness_seed").to_pylist()
    geoms = table.column("geometry").to_pylist()

    # The paint (J52).  A separate table because it is derived from the measured lane cross-section
    # rather than surveyed, and it is appended here rather than merged upstream so the planimetric
    # file stays exactly what DoITT published.  Its ``colour`` becomes a pavement kind; its surface
    # is the asphalt underneath, which is what ``surface_class`` needs to resolve PaintedMarking.
    n_markings = 0
    mk = MARKINGS_DIR / f"{tile}.parquet"
    if mk.exists():
        mt = pq.read_table(mk, columns=["colour", "geometry"])
        colours = mt.column("colour").to_pylist()
        mgeoms = mt.column("geometry").to_pylist()
        n_markings = len(colours)
        kinds = list(kinds) + [pvlib.MARKING_KIND_OF_COLOUR.get(int(c), 10) for c in colours]
        surfaces = list(surfaces) + [0] * n_markings
        seeds = list(seeds) + [0] * n_markings
        geoms = list(geoms) + list(mgeoms)

    sampler = LandscapeSampler(TILES_DATA)
    # The carriageway's own elevation, for the polygons the road network says are not at grade.
    roads = pvlib.RoadSurface(SEGMENTS_PARQUET, (x0, y0, x0 + TILE_SIZE_M, y0 + TILE_SIZE_M)) \
        if road_z and SEGMENTS_PARQUET.exists() else None
    cut = load_landmark_ground((x0, y0, x0 + TILE_SIZE_M, y0 + TILE_SIZE_M)) if cut_landmark_ground else []

    # The surveyed pedestrian ramps, and the roadbed polygons that say which way each one descends.
    # Built before the main loop because the kerb has to be cut where a ramp crosses it: a ramp that
    # runs down to a 0.15 m step at the bottom is not a ramp.
    ramps = load_ramps(tile, (x0, y0, x0 + TILE_SIZE_M, y0 + TILE_SIZE_M)) if with_ramps else []
    roadbeds = []
    if ramps:
        for kind, blob in zip(kinds, geoms):
            if int(kind) != 0:
                continue
            try:
                g = shapely.from_wkb(blob)
            except Exception:  # noqa: BLE001
                continue
            roadbeds.extend(list(g.geoms) if g.geom_type == "MultiPolygon"
                            else ([g] if g.geom_type == "Polygon" else []))
    ramp_buf, ramp_rects, ramp_report = ramp_slabs(
        ramps, roadbeds, sampler, x0, y0, cell_m, min_edge_m, max_edge_m) if ramps else (None, [], {})
    ramp_cut = shapely.union_all(ramp_rects) if ramp_rects else None

    t_load = time.perf_counter() - t0
    t1 = time.perf_counter()
    slabs: dict[tuple[int, int], pvlib.SlabBuffer] = {}
    seed_of: dict[tuple[int, int], list[float]] = {}
    per_kind: dict[str, int] = {}
    dropped = {"not_a_polygon": 0, "degenerate_ring": 0, "unknown_kind": 0,
               "no_triangulation": 0, "no_terrain": 0, "landmark_ground": 0}
    cut_polygons = 0
    elevated_polys = 0

    for kind, surface, seed, blob in zip(kinds, surfaces, seeds, geoms):
        k, s = int(kind), int(surface)
        if k not in pvlib.PAVEMENT_KINDS:
            dropped["unknown_kind"] += 1
            continue
        try:
            g = shapely.from_wkb(blob)
        except Exception:
            dropped["not_a_polygon"] += 1
            continue
        if simplify_m > 0.0:
            g = shapely.simplify(g, simplify_m, preserve_topology=True)
        if ramp_cut is not None and k == 4:
            # The kerb is the 0.15 m step; a ramp is the place there is no step. Cutting the kerb
            # polygon rather than drawing the ramp over it keeps the two from fighting over the same
            # surface, and leaves a real opening at the bottom of the ramp.
            g = shapely.difference(g, ramp_cut)
        parts = list(g.geoms) if g.geom_type == "MultiPolygon" else ([g] if g.geom_type == "Polygon" else [])
        if not parts:
            dropped["not_a_polygon"] += 1
            continue
        name, lift, skirt = pvlib.PAVEMENT_KINDS[k]
        # A roadbed or a crosswalk on a viaduct is drawn at the viaduct's height, not at the height
        # of the street it crosses. Everything a pedestrian stands on stays on the ground: a
        # planimetric kerb beside an elevated road belongs to the street below it, not to the deck.
        use_road = roads is not None and roads.ok and k in ROAD_Z_KINDS
        for poly in parts:
            if len(poly.exterior.coords) < 4:
                dropped["degenerate_ring"] += 1
                continue
            if cut and shapely.contains(shapely.union_all(cut), shapely.Point(poly.representative_point())):
                dropped["landmark_ground"] += 1
                cut_polygons += 1
                continue
            # Cut on a grid rather than ear-clipped: see pvlib.grid_triangulate for the measurement
            # that decided it. The cell is a little above the heightmap's own 2 m sampling, so the
            # refinement below has something left to do only where the ground genuinely bends.
            pts, tris = pvlib.grid_triangulate(poly, cell_m)
            if len(tris) == 0:
                dropped["no_triangulation"] += 1
                continue
            line = roads.line_for(poly) if use_road else None
            elevated = line is not None
            # The refinement must test against the same surface the drape uses, or it subdivides to
            # chase a cliff the road does not cross.
            height_fn = roads.height_on(line) if elevated else sampler.height
            pts, tris = pvlib.refine_to_terrain(pts, tris, height_fn,
                                                tol_m=tol_m if tol_m > 0.0 else lift * tol_fraction,
                                                min_edge_m=min_edge_m, max_edge_m=max_edge_m)
            if elevated:
                elevated_polys += 1
            z = height_fn(pts[:, 0], pts[:, 1])
            if np.isnan(z).all():
                dropped["no_terrain"] += 1
                continue
            if np.isnan(z).any():
                z = np.where(np.isnan(z), float(np.nanmedian(z)), z)
            buf = slabs.setdefault((k, s), pvlib.SlabBuffer(kind=k, surface=s))
            buf.add_polygon(pts - np.array([x0, y0]), z + lift, tris,
                            skirt if k in skirt_kinds else 0.0,
                            road_line=line if elevated else -1)
            seed_of.setdefault((k, s), []).append(float(int(seed) % 65536) / 65536.0)
            per_kind[name] = per_kind.get(name, 0) + 1
    if ramp_buf is not None and ramp_buf.faces:
        slabs[(8, 1)] = ramp_buf
        seed_of.setdefault((8, 1), []).append(0.5)
        per_kind["curb_ramp"] = ramp_report.get("built", 0)
    t_geom = time.perf_counter() - t1

    # ---- Blender assembly ----------------------------------------------------------------------
    t2 = time.perf_counter()
    nb.reset_scene()
    objects = []
    mesh_stats: list[dict] = []
    lo = np.array([math.inf] * 3)
    hi = np.array([-math.inf] * 3)
    for (k, s), buf in sorted(slabs.items()):
        if not buf.faces:
            continue
        name, lift, skirt = pvlib.PAVEMENT_KINDS[k]
        cls = pvlib.surface_class(k, s)
        mname = pvlib.material_name(k, s)
        pos = np.asarray(buf.verts, dtype=np.float64)
        tri = np.asarray(buf.faces, dtype=np.int64)
        ob = _make_object(f"{tile}_{mname}", pos, tri, np.asarray(buf.is_top, dtype=bool),
                          np.asarray(buf.road_line, dtype=np.int32), mname, {
            "tile": tile, "kind": k, "kind_name": name, "surface": s,
            "surface_name": pvlib.SURFACE_NAMES.get(s, str(s)),
            "surface_class": cls, "surface_class_name": pvlib.SURFACE_CLASS_NAMES.get(cls, str(cls)),
            "lift_m": lift, "skirt_m": skirt if k in skirt_kinds else 0.0,
            # A curb ramp's lift is not a constant -- it descends from the sidewalk's 0.25 m to the
            # roadbed's 0.10 m over its measured run -- so the draping residual, which subtracts one
            # lift per object, cannot read it. It is excluded there rather than reported as a
            # 150 mm error that is the ramp doing its job.
            "variable_lift": k == 8,
            "origin_m": [x0, y0, 0.0],
        })
        objects.append(ob)
        lo = np.minimum(lo, pos.min(axis=0))
        hi = np.maximum(hi, pos.max(axis=0))
        mesh_stats.append({"mesh": ob.name, "material": mname, "kind": k, "kind_name": name,
                           "surface": s, "surface_name": pvlib.SURFACE_NAMES.get(s, str(s)),
                           "surface_class": cls,
                           "surface_class_name": pvlib.SURFACE_CLASS_NAMES.get(cls, str(cls)),
                           "polygons": buf.polygons, "vertices": len(pos),
                           "triangles": len(tri), "top_triangles": buf.top_triangles,
                           "skirt_triangles": buf.skirt_triangles})
    t_mesh = time.perf_counter() - t2

    out_dir = Path(out_root) / tile
    glb = out_dir / GLB_NAME
    t3 = time.perf_counter()
    if objects:
        out_dir.mkdir(parents=True, exist_ok=True)
        nb.export_glb(glb, objects=objects, apply_modifiers=False, texcoords=True, tangents=False,
                      export_extras=True, export_attributes=True, export_normals=False,
                      export_animations=False, extras={
                          "stage": "roads_pavement", "tile": tile,
                          "origin_m": [x0, y0, 0.0], "crs": "NYC_TM",
                          "vertical_datum": "NAVD88 metres",
                          "source": "data/processed/roads/pavement/{tile}.parquet",
                          "draped_on": "UE landscape grid (505 samples, NYCTerrainImport.cpp)",
                          "refinement_tol_m": tol_m, "max_edge_m": max_edge_m,
                          "skirt_kinds": sorted(skirt_kinds),
                          "uv": "metres, planar XY in NYC_TM (u = east, v = north)",
                          "surface_class": {m["material"]: m["surface_class"] for m in mesh_stats},
                      })
    elif glb.exists():
        glb.unlink()
    t_export = time.perf_counter() - t3

    residual = _draping_residual(objects, sampler, roads, x0, y0) if objects else {}
    size = glb.stat().st_size if glb.exists() else 0
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "roads_pavement",
        "tile": tile,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": nb.git_commit(),
        "generator": "blender/roads/build_pavement.py",
        "source": str((PAVEMENT_DIR / f"{tile}.parquet").relative_to(REPO_ROOT)),
        "markings_source": (str((MARKINGS_DIR / f"{tile}.parquet").relative_to(REPO_ROOT))
                            if n_markings else None),
        "rows_in": len(kinds),
        "marking_rows_in": n_markings,
        "polygons_meshed": sum(b.polygons for b in slabs.values()),
        "polygons_dropped": {k: v for k, v in dropped.items() if v},
        "polygons_cut_for_landmark_ground": cut_polygons,
        "polygons_at_road_level": elevated_polys,
        "road_level_source": (str(SEGMENTS_PARQUET.relative_to(REPO_ROOT))
                              if roads is not None and roads.ok else
                              (roads.reason if roads is not None else "disabled")),
        "per_kind": dict(sorted(per_kind.items(), key=lambda kv: -kv[1])),
        "triangles": sum(len(b.faces) for b in slabs.values()),
        "top_triangles": sum(b.top_triangles for b in slabs.values()),
        "skirt_triangles": sum(b.skirt_triangles for b in slabs.values()),
        "vertices": sum(len(b.verts) for b in slabs.values()),
        "meshes": mesh_stats,
        "refinement": {"cell_m": cell_m, "tol_m": tol_m, "tol_fraction_of_lift": tol_fraction,
                       "tol_per_kind_m": {name: round(lift * tol_fraction, 4) if tol_m <= 0.0 else tol_m
                                          for _k, (name, lift, _s) in pvlib.PAVEMENT_KINDS.items()},
                       "min_edge_m": min_edge_m, "max_edge_m": max_edge_m,
                       "simplify_m": simplify_m},
        "skirt_kinds": sorted(skirt_kinds),
        "curb_ramps": ramp_report,
        "draping_residual_m": residual,
        "bounds_local_m": {"min": _fin(lo), "max": _fin(hi)},
        "origin_m": [x0, y0, 0.0],
        "terrain_tiles_missing": sorted(sampler.missing),
        "glb": {"path": _rel(glb) if glb.exists() else "", "bytes": size,
                "sha256": _sha256(glb) if glb.exists() else ""},
        "seconds": {"total": round(time.perf_counter() - t0, 3), "load": round(t_load, 3),
                    "geometry": round(t_geom, 3), "mesh": round(t_mesh, 3),
                    "export": round(t_export, 3)},
    }
    if objects:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


#: Kinds whose elevation comes from the road network when the network says the road is not at grade.
ROAD_Z_KINDS = frozenset({0, 5})


def _road_or_ground(roads, sampler):
    """Road elevation where the network has one, the ground where it does not.

    The fallback matters at the ends of a viaduct: the deck's own polygon runs past the last
    centreline vertex, and without it those vertices would be NaN and the whole polygon dropped.
    """
    def height(x, y):
        z = roads.height(x, y)
        missing = ~np.isfinite(z)
        if missing.any():
            ground = sampler.height(np.asarray(x)[missing], np.asarray(y)[missing])
            z = np.array(z, dtype=np.float64)
            z[missing] = ground
        return z

    return height


def _draping_residual(objects, sampler: LandscapeSampler, roads, x0: float, y0: float) -> dict:
    """How far the shipped top surface sits from the ground it was draped on, sampled inside faces.

    Draping only the corners is the defect this stage's refinement exists to remove, so the stage
    measures what it left behind rather than asserting it is gone.  The residual that survives is the
    difference between this sampler's bilinear read of the landscape and the two-triangles-per-quad
    surface the engine actually collides, which no amount of refinement here can close.
    """
    import bmesh
    import bpy

    xs, ys, zs, lifts, on_road = [], [], [], [], []
    rng = np.random.default_rng(0x4E5943)
    excluded = []
    for ob in objects:
        if ob.get("variable_lift"):
            excluded.append(ob.name)
            continue
        me = ob.data
        n = len(me.polygons)
        if n == 0:
            continue
        flags = np.empty(n, dtype=bool)
        me.attributes["is_top"].data.foreach_get("value", flags)
        road_flags = np.empty(n, dtype=np.int32)
        me.attributes["road_line"].data.foreach_get("value", road_flags)
        tops = np.nonzero(flags)[0]
        if tops.size == 0:
            continue
        take = min(tops.size, max(1, RESIDUAL_SAMPLES // max(1, len(objects))))
        idx = rng.choice(tops, size=take, replace=False)
        nv = len(me.vertices)
        co = np.empty(nv * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(nv, 3).astype(np.float64)
        loops = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", loops)
        tri = loops.reshape(-1, 3)[idx]
        w = rng.random((take, 3))
        w /= w.sum(axis=1, keepdims=True)
        p = (co[tri] * w[:, :, None]).sum(axis=1)
        lift = float(ob.get("lift_m") or 0.0)
        xs.append(p[:, 0] + x0)
        ys.append(p[:, 1] + y0)
        zs.append(p[:, 2] - lift)
        lifts.append(np.full(take, lift))
        on_road.append(road_flags[idx])
    if not xs:
        return {"excluded_variable_lift": excluded}
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    z = np.concatenate(zs)
    # Each face is measured against the surface it was draped on, not against the ground: a
    # carriageway on a viaduct is 17 m above the street and that is the point of it being there.
    ground = sampler.height(x, y)
    road_face = np.concatenate(on_road)
    if roads is not None and roads.ok:
        # Each road face against its own centreline. Grouped by line so one interpolate call serves
        # every face that shares one.
        for j in np.unique(road_face[road_face >= 0]):
            sel = np.nonzero(road_face == j)[0]
            z_line = roads.height_on(int(j))(x[sel], y[sel])
            good = np.isfinite(z_line)
            ground[sel[good]] = z_line[good]
    ok = ~np.isnan(ground)
    if not ok.any():
        return {}
    lift = np.concatenate(lifts)[ok]
    # Signed, and signed the way it matters: the surface is at ``ground_at_ring + lift`` and the
    # engine's ground under it is ``ground``. Positive means the landscape stands above the paved
    # surface, which is the only case anyone sees -- a patch of bare terrain rising through the road.
    # A negative residual is pavement sitting a little proud of the ground, which the skirt covers and
    # which no camera can distinguish from a slightly thicker slab.
    through = ground[ok] - (z[ok] + lift)
    d = np.abs(z[ok] - ground[ok])
    return {"samples": int(ok.sum()),
            "abs_mean_mm": round(float(d.mean()) * 1000.0, 2),
            "abs_p99_mm": round(float(np.percentile(d, 99)) * 1000.0, 2),
            "abs_max_mm": round(float(d.max()) * 1000.0, 2),
            "pierced_fraction": round(float((through > 0.0).mean()), 5),
            "pierced_p999_mm": round(float(np.percentile(through, 99.9)) * 1000.0, 2),
            "pierced_max_mm": round(float(through.max()) * 1000.0, 2),
            "note": ("sampled at random points inside the shipped top faces. abs_* is |draped top - "
                     "landscape| with the lift removed, the draping error itself. pierced_* is "
                     "landscape - top surface: positive means bare terrain rises through the "
                     "pavement, which is the only side of the error that is visible."),
            "excluded_variable_lift": excluded}


def _make_object(name: str, pos: np.ndarray, tri: np.ndarray, is_top: np.ndarray,
                 road_line: np.ndarray, material_name: str, props: dict):
    """Mesh from flat arrays, UVs in metres, one material, node extras carrying the surface class."""
    import bpy

    import nycsim_bpy as nb

    nv, nt = len(pos), len(tri)
    me = bpy.data.meshes.new(name)
    me.vertices.add(nv)
    me.vertices.foreach_set("co", np.ascontiguousarray(pos, dtype=np.float32).ravel())
    me.loops.add(nt * 3)
    me.loops.foreach_set("vertex_index", np.ascontiguousarray(tri, dtype=np.int32).ravel())
    me.polygons.add(nt)
    me.polygons.foreach_set("loop_start", np.arange(nt, dtype=np.int32) * 3)
    # use_smooth only suppresses the exporter's per-face vertex split; NORMAL is not exported, so a
    # glTF client computes flat normals from the winding -- which is what a faceted slab wants.
    me.polygons.foreach_set("use_smooth", np.ones(nt, dtype=bool))
    me.update()
    # UVs in metres, planar in the tile's own X/Y: a tiling asphalt or concrete texture then has its
    # real physical size and runs continuously across the tile seam.
    uv = pos[tri][:, :, :2].reshape(-1, 2)
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", np.ascontiguousarray(uv, dtype=np.float32).ravel())
    # Face domain, so the residual check and any consumer can tell the surface from its walls
    # without guessing from a normal. Not exported (glTF has no face attributes); it lives in the
    # Blender mesh for the duration of this process.
    a = me.attributes.new(name="is_top", type="BOOLEAN", domain="FACE")
    a.data.foreach_set("value", np.ascontiguousarray(is_top, dtype=bool))
    # Which surface this face was draped on: a centreline index, or -1 for the ground. Without it
    # the residual check compares an elevated carriageway against the ground 17 m below and reports
    # a 13 m error that is not an error; with a mere flag it compares it against whichever deck
    # happens to be nearest and reports the same thing where decks stack.
    b = me.attributes.new(name="road_line", type="INT", domain="FACE")
    b.data.foreach_set("value", np.ascontiguousarray(road_line, dtype=np.int32))
    kind = int(props.get("kind", 0))
    _name, _lift, _skirt = pvlib.PAVEMENT_KINDS.get(kind, ("roadbed", 0.10, 0.30))
    me.materials.append(_pavement_material(material_name, kind))
    ob = bpy.data.objects.new(name, me)
    for k, v in props.items():
        ob[k] = v
    bpy.context.scene.collection.objects.link(ob)
    return ob


#: Base colour and roughness per kind, the same values the verification renderer has been drawing.
_LOOK = {
    0: ((0.055, 0.055, 0.058, 1.0), 0.85),
    1: ((0.34, 0.335, 0.32, 1.0), 0.88),
    2: ((0.30, 0.30, 0.29, 1.0), 0.88),
    3: ((0.33, 0.31, 0.30, 1.0), 0.80),
    4: ((0.42, 0.42, 0.41, 1.0), 0.80),
    # The crossing area is asphalt: since J52 the paint on it is the bars, kinds 10 and 11.
    5: ((0.058, 0.058, 0.061, 1.0), 0.85),
    6: ((0.075, 0.075, 0.078, 1.0), 0.85),
    7: ((0.075, 0.075, 0.078, 1.0), 0.85),
    # A curb ramp is the same concrete as the sidewalk it is cut into, a little lighter where it is
    # newer than what is around it, and its detectable warning surface is a separate material the
    # kit does not have yet -- so the ramp is one flat concrete for now (DEVIATIONS J21).
    8: ((0.46, 0.455, 0.44, 1.0), 0.86),
    # Thermoplastic: brighter and glossier than the asphalt it is laid on (J52).
    10: ((0.80, 0.80, 0.78, 1.0), 0.62),
    11: ((0.74, 0.60, 0.13, 1.0), 0.62),
}


def _pavement_material(name: str, kind: int):
    import nycsim_bpy as nb

    colour, rough = _LOOK.get(int(kind), _LOOK[0])
    return nb.pbr_material(name, base_color=colour, roughness=rough)


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
    """Free the tile's Blender data-blocks so RSS stays bounded over 972 tiles."""
    import bpy

    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
        for item in list(coll):
            coll.remove(item, do_unlink=True)


# --------------------------------------------------------------------------- CLI


def run_serial(tiles: list[str], args) -> int:
    ok = 0
    for i, tile in enumerate(tiles, 1):
        out = Path(args.out) / tile / GLB_NAME
        if args.skip_existing and out.exists() and (out.parent / MANIFEST_NAME).exists():
            print(f"[{i}/{len(tiles)}] {tile} skipped (exists)", flush=True)
            ok += 1
            continue
        try:
            m = build_tile(tile, out_root=Path(args.out), tol_m=args.tol,
                           tol_fraction=args.tol_fraction, cell_m=args.cell,
                           min_edge_m=args.min_edge, max_edge_m=args.max_edge,
                           simplify_m=args.simplify, skirt_kinds=_parse_kinds(args.skirt_kinds),
                           road_z=not args.no_road_z,
                           cut_landmark_ground=not args.no_landmark_cut)
        except Exception as exc:
            LOG.exception("tile %s failed", tile)
            print(f"[{i}/{len(tiles)}] {tile} FAILED: {exc}", flush=True)
            continue
        finally:
            _purge()
        ok += 1
        r = m.get("draping_residual_m") or {}
        print(f"[{i}/{len(tiles)}] {tile} polys={m['polygons_meshed']} tris={m['triangles']} "
              f"bytes={m['glb']['bytes']} drape_p99={r.get('abs_p99_mm', 0)}mm "
              f"pierced={r.get('pierced_fraction', 0)} "
              f"t={m['seconds']['total']}s", flush=True)
    return 0 if ok == len(tiles) else 1


def run_parallel(tiles: list[str], args) -> int:
    n = max(1, min(args.workers, 2))          # resource etiquette: 4 vCPU shared, never more than 2
    logdir = Path(args.out) / "_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    procs = []
    for i in range(n):
        chunk = tiles[i::n]
        if not chunk:
            continue
        listfile = logdir / f"pavement_worker{i}.tiles"
        listfile.write_text("\n".join(chunk))
        cmd = ["nice", "-n", str(args.nice), sys.executable, str(Path(__file__).resolve()),
               "--tile-list", str(listfile), "--out", str(args.out),
               "--tol", str(args.tol), "--tol-fraction", str(args.tol_fraction),
               "--cell", str(args.cell),
               "--simplify", str(args.simplify),
               "--min-edge", str(args.min_edge),
               "--max-edge", str(args.max_edge)]
        cmd += ["--skirt-kinds", args.skirt_kinds]
        if args.no_road_z:
            cmd.append("--no-road-z")
        if args.no_landmark_cut:
            cmd.append("--no-landmark-cut")
        if args.skip_existing:
            cmd.append("--skip-existing")
        log = open(logdir / f"pavement_worker{i}.log", "w")
        procs.append((subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT), log))
        print(f"worker {i}: {len(chunk)} tiles -> {logdir / f'pavement_worker{i}.log'}", flush=True)
    rc = 0
    for p, log in procs:
        rc |= p.wait()
        log.close()
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tile", help="single tile name, e.g. t_-4_4")
    g.add_argument("--tiles", help="comma separated tile names")
    g.add_argument("--tile-list", help="file with one tile name per line")
    g.add_argument("--all", action="store_true", help="every tile with a pavement table")
    ap.add_argument("--out", default=str(OUT_ROOT), help="output root (default blender_out/tiles)")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL_M,
                    help="draping tolerance in metres, overriding the per-kind fraction; "
                         "0 (default) means use --tol-fraction of each kind's lift")
    ap.add_argument("--cell", type=float, default=DEFAULT_CELL_M,
                    help="grid cell the polygons are cut on, metres; 0 to ear-clip instead (default 2.5)")
    ap.add_argument("--tol-fraction", type=float, default=DEFAULT_TOL_FRACTION,
                    help="draping tolerance as a fraction of the kind's lift (default 0.5)")
    ap.add_argument("--simplify", type=float, default=DEFAULT_SIMPLIFY_M,
                    help="Douglas-Peucker tolerance on the source rings in metres (default 0.02)")
    ap.add_argument("--min-edge", type=float, default=DEFAULT_MIN_EDGE_M,
                    help="refinement floor in metres (default 0.5)")
    ap.add_argument("--max-edge", type=float, default=DEFAULT_MAX_EDGE_M,
                    help="longest triangle edge in metres regardless of error (default 25.0)")
    ap.add_argument("--skirt-kinds", default=",".join(str(k) for k in sorted(DEFAULT_SKIRT_KINDS)),
                    help="pavement kinds that carry a downward skirt; empty for none "
                         "(default 1,2,3,4 = sidewalk, median, plaza, curb)")
    ap.add_argument("--no-road-z", action="store_true",
                    help="drape grade-separated roadbeds on the ground as well (they will be drawn "
                         "on whatever is under the viaduct)")
    ap.add_argument("--no-landmark-cut", action="store_true",
                    help="draw pavement inside a landmark's own ground as well")
    ap.add_argument("--workers", type=int, default=1, help="parallel processes (max 2)")
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
        print("no tiles to build", file=sys.stderr)
        return 2
    if args.workers > 1 and len(tiles) > 1:
        return run_parallel(tiles, args)
    return run_serial(tiles, args)


if __name__ == "__main__":
    raise SystemExit(main())
