"""Shared module for every hand-scripted NYCSim landmark (``blender/landmarks/<id>.py``).

Owned by landmark agent A; agents B and C import it. Run any landmark script with plain ``python3``
(``bpy`` 4.5 is installed as a module). Everything here is in metres, Blender Z-up.

Public API (stable — other agents depend on it)
------------------------------------------------
``load_footprint(key)``            key = landmark id (registered in ``LANDMARK_BINS``/``register``), BIN (int or digit
                                   string) or a building name (case-insensitive, must be unique). Returns a
                                   :class:`Footprint` that also unpacks as ``(polygon, ground_z, height_m, centroid)``.
                                   Per-BIN geometry sources, in order: ``data/processed/landmarks/candidate_footprints.parquet``,
                                   ``data/processed/buildings/footprints_raw.parquet`` (bin-filtered column read).
``load_footprints(bins)``          list of Footprint.
``landmark_meta(id_or_bin)``       row of ``data/processed/buildings/landmark_footprints.parquet`` (LP number, LiDAR roof
                                   height, published ``expected_height_m``). That table's geometry is already unioned over
                                   a landmark's BINs, so it is metadata only — geometry always comes per BIN from the two
                                   footprint parquets above, which is also what ``tests/test_landmarks_a.py`` compares to.
``local_frame(polygon, ground_z)`` :class:`LocalFrame` — origin = footprint centroid rounded to whole metres (NYC_TM),
                                   ``angle_deg`` = direction of the footprint's principal (long) axis from east (CCW),
                                   ``heading_deg`` = compass heading of that same +x axis. Build everything in this
                                   aligned local frame; ``finish`` rotates it back so the exported .glb has axes
                                   parallel to NYC_TM (east, north, up) and its origin at ``origin_tm``.
``MeshBuilder``                    fast vertex/face accumulator with per-face materials: quads, boxes, prisms, lofts,
                                   lathes, vertical n-gons; ``.build(name)`` -> Blender object.
``prism, plinth, tower_tier, facade_grid, cornice, band, loft, lathe, column, colonnade, entablature, pilaster, pediment,
gable_roof, hip_roof, pyramid_roof, dome, balustrade, barrel_vault, clock_face, steps, flagpole, arched_opening,
window_punch, punched_wall`` builders.
``M`` / ``mat(name)``              documented material palette (``PALETTE``: albedo, roughness, metallic, emission, source).
                                   Masonry and paving names carry the CC0 PBR maps served by ``blender/common/textures.py``
                                   (``TEXTURE_NAMES``), tiled in metres over the box-projected UVs that ``MeshBuilder.build``
                                   writes; the colour map is multiplied by a tint that preserves the documented albedo.
                                   ``NYCSIM_LANDMARK_TEXTURES=0`` forces flat colours; ``texture_status()`` reports what was used.
``finish(objects, landmark_id, bins, frame, ...)``
                                   validates (footprint IoU > 0.9 on base-tagged objects, height within 1 %, triangle
                                   budget, LOD1 <= 20 %), builds ``<id>_LOD1``, rotates to NYC_TM axes, exports
                                   ``blender_out/landmarks/<id>.glb`` with extras {origin_tm, bins, heading_deg,
                                   height_m, fidelity_statement, ...} and writes ``blender_out/landmarks/catalog/<id>.json``
                                   (DATA_CONTRACTS §11 fields + polycounts + IoU) via ``nycsim_bpy.write_catalog_entry``.
``render_check(landmark_id, presets)``
                                   Cycles CPU 64 spp stills to ``docs/verification/landmarks/<id>_<view>.png``.
                                   Presets are dicts ``{"view", "azimuth_deg", "elevation_deg"|"street", "distance",
                                   "fov_deg", "target_z"}`` or ``{"view", "eye", "target", "fov_deg"}`` for an explicit
                                   camera (interiors); defaults give a street-level and an aerial view.
                                   ``NYCSIM_RENDER_FAST=1`` renders 16 spp at half size for iteration;
                                   ``NYCSIM_RENDER_SIZE=WxH`` overrides the still size (default 1280x720);
                                   ``NYCSIM_LANDMARK_NO_RENDER=1`` skips the stills entirely (geometry/export checks only).

Conventions
-----------
* Footprint polygons are CCW; for a CCW ring the *outward* normal of edge p0->p1 is (dy, -dx)/len.
* Objects that constitute the base volume (the extruded real footprint) must be tagged ``role="base"`` (``prism``
  does this when ``role="base"``); massing volumes for LOD1 are tagged ``role="mass"`` (``tower_tier`` does).
* The ``nycsim_role`` custom property is exported to glTF node extras so tests can find base volumes.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1] / "common"))
if str(_HERE.parents[2] / "pipeline") not in sys.path:
    sys.path.insert(0, str(_HERE.parents[2] / "pipeline"))

import numpy as np
import bpy
import bmesh
from mathutils import Matrix, Vector

import shapely
import shapely.ops
from shapely import wkb as _wkb
from shapely.geometry import MultiLineString, MultiPolygon, Polygon
from shapely.geometry.polygon import orient as _orient

import nycsim_bpy as nb

log = logging.getLogger("nycsim.landmarks")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

REPO_ROOT = nb.REPO_ROOT
DATA = Path(os.environ.get("NYCSIM_DATA_DIR", REPO_ROOT / "data"))
CANDIDATES_PARQUET = DATA / "processed" / "landmarks" / "candidate_footprints.parquet"
LANDMARK_FOOTPRINTS_PARQUET = DATA / "processed" / "buildings" / "landmark_footprints.parquet"
FOOTPRINTS_RAW_PARQUET = DATA / "processed" / "buildings" / "footprints_raw.parquet"
OUT_DIR = nb.BLENDER_OUT / "landmarks"
CATALOG_DIR = OUT_DIR / "catalog"
VERIFY_DIR = REPO_ROOT / "docs" / "verification" / "landmarks"

TRI_BUDGET_LOD0 = 250_000
TRI_BUDGET_LOD0_LARGE = 600_000
LOD1_MAX_RATIO = 0.20
IOU_MIN = 0.90
HEIGHT_TOL = 0.01

# Landmark id -> BIN(s). Agent A's set is registered here; other agents call ``register`` (or pass BINs directly).
LANDMARK_BINS: dict[str, list[int]] = {
    "empire_state": [1015862],
    "chrysler": [1036156],
    "flatiron": [1016278],
    "one_vanderbilt": [1090825],
    "30_rockefeller_plaza": [1076262],
    "st_patricks_cathedral": [1081150, 1081149, 1082595],
    "grand_central_terminal": [1035381],
    "new_york_public_library": [1034194],
    # the arena drum only; BIN 1083026 (Two Penn Plaza, the 1968 office slab north of it) is a separate building
    "madison_square_garden": [1082908],
    "woolworth": [1087167],
    "municipal_building": [1001394],
    "city_hall": [1079147],
    "trinity_church": [1001028],
    "nyse": [1078981, 1078982],
    "charging_bull": [],
    "federal_hall": [1001020],
    "40_wall_street": [1001018],
    "one_wall_street": [1000815],
    "equitable_building": [1001026],
    "moma": [1081128, 1081130, 1087646],
}


class FidelityError(RuntimeError):
    """Raised when a model fails a hard verification (footprint IoU, height, budgets)."""


def register(landmark_id: str, bins: Sequence[int]) -> None:
    """Register a landmark id -> BIN list so ``load_footprint(landmark_id)`` works (idempotent)."""
    LANDMARK_BINS[landmark_id] = [int(b) for b in bins]


# =============================================================================================== footprints
@dataclasses.dataclass
class Footprint:
    polygon: Polygon            # NYC_TM metres, CCW exterior, holes kept
    ground_z: float             # metres NAVD88 (LiDAR ground elevation)
    height_m: float             # LiDAR roof height (height_roof) — the *dataset* value, not the architectural height
    centroid: tuple[float, float]
    bin: int
    name: str
    source: str                 # which parquet the row came from
    year: int | None = None

    def __iter__(self):
        yield self.polygon
        yield self.ground_z
        yield self.height_m
        yield self.centroid


def _clean_polygon(geom) -> Polygon:
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    if not geom.is_valid:
        geom = geom.buffer(0)
        if isinstance(geom, MultiPolygon):
            geom = max(geom.geoms, key=lambda g: g.area)
    geom = geom.simplify(0.02, preserve_topology=True)
    return _orient(Polygon(geom.exterior.coords, [h.coords for h in geom.interiors]), 1.0)


def _read_rows(path: Path, *, bins: Sequence[int] | None = None, name: str | None = None) -> list[dict]:
    """Per-BIN footprint rows from a parquet with the footprint schema (``bin`` + ``geometry``).

    ``landmark_footprints.parquet`` has a different, per-*landmark* schema (``landmark_id``, ``bins`` list, geometry already
    unioned over the BINs); it is read by :func:`landmark_meta` for LP numbers and published heights, never for per-BIN
    geometry — the union would otherwise collapse a multi-building landmark into one polygon."""
    import pyarrow.parquet as pq
    if not path.exists():
        return []
    pf = pq.ParquetFile(path)
    have = set(pf.schema_arrow.names)
    if "bin" not in have:
        return []
    want = [c for c in ("bin", "name", "height", "ground_z", "cx", "cy", "geometry", "construction_year", "height_roof",
                        "ground_elevation") if c in have]
    filters = None
    if bins is not None:
        filters = [("bin", "in", [int(b) for b in bins])]
    tbl = pq.read_table(path, columns=want, filters=filters)
    rows = tbl.to_pylist()
    if name is not None:
        pat = name.lower()
        rows = [r for r in rows if r.get("name") and pat in str(r["name"]).lower()]
    return rows


def _row_to_footprint(r: dict, source: str) -> Footprint:
    geom = _wkb.loads(r["geometry"]) if isinstance(r["geometry"], (bytes, bytearray)) else shapely.from_wkb(r["geometry"])
    poly = _clean_polygon(geom)
    gz = r.get("ground_z")
    if gz is None or (isinstance(gz, float) and math.isnan(gz)):
        ge = r.get("ground_elevation")
        gz = float(ge) * 0.3048006096012192 if ge is not None else 0.0
    h = r.get("height")
    if h is None or (isinstance(h, float) and math.isnan(h)):
        hr = r.get("height_roof")
        h = float(hr) * 0.3048006096012192 if hr is not None else 0.0
    cx = r.get("cx"); cy = r.get("cy")
    if cx is None or cy is None:
        cx, cy = poly.centroid.x, poly.centroid.y
    yr = r.get("construction_year")
    return Footprint(poly, float(gz), float(h), (float(cx), float(cy)), int(r["bin"]), str(r.get("name") or ""), source,
                     int(yr) if yr not in (None, 0) else None)


def load_footprints(bins: Sequence[int]) -> list[Footprint]:
    """Footprints for several BINs, in the order given. Raises KeyError for a BIN found nowhere."""
    bins = [int(b) for b in bins]
    found: dict[int, Footprint] = {}
    for path in (LANDMARK_FOOTPRINTS_PARQUET, CANDIDATES_PARQUET, FOOTPRINTS_RAW_PARQUET):
        missing = [b for b in bins if b not in found]
        if not missing:
            break
        for r in _read_rows(path, bins=missing):
            if int(r["bin"]) not in found:
                found[int(r["bin"])] = _row_to_footprint(r, path.name)
    missing = [b for b in bins if b not in found]
    if missing:
        raise KeyError(f"BIN(s) {missing} not found in {LANDMARK_FOOTPRINTS_PARQUET.name}, {CANDIDATES_PARQUET.name} or {FOOTPRINTS_RAW_PARQUET.name}")
    return [found[b] for b in bins]


_META_CACHE: dict[str, dict] | None = None


def _landmark_meta_table() -> dict[str, dict]:
    """``data/processed/buildings/landmark_footprints.parquet`` keyed by landmark_id *and* by ``bin:<BIN>``."""
    global _META_CACHE
    if _META_CACHE is not None:
        return _META_CACHE
    out: dict[str, dict] = {}
    if LANDMARK_FOOTPRINTS_PARQUET.exists():
        import pyarrow.parquet as pq
        have = set(pq.ParquetFile(LANDMARK_FOOTPRINTS_PARQUET).schema_arrow.names)
        cols = [c for c in ("landmark_id", "name", "bins", "height_m", "ground_z", "roof_z", "lp_number",
                            "expected_height_m", "height_dev_m", "footprint_area", "n_footprints", "lon", "lat",
                            "centroid_x", "centroid_y", "match_method") if c in have]
        for r in pq.read_table(LANDMARK_FOOTPRINTS_PARQUET, columns=cols).to_pylist():
            r["bins"] = [int(b) for b in (r.get("bins") or [])]
            out[str(r.get("landmark_id"))] = r
            for b in r["bins"]:
                out.setdefault(f"bin:{b}", r)
    _META_CACHE = out
    return out


def landmark_meta(key: str | int) -> dict:
    """Row of ``landmark_footprints.parquet`` for a landmark_id or a BIN (``{}`` when the landmark is not in that table).

    Use it for LP designation numbers, the LiDAR roof height and the published ``expected_height_m`` cross-check — not for
    geometry (see :func:`_read_rows`)."""
    t = _landmark_meta_table()
    if isinstance(key, (int, np.integer)) or (isinstance(key, str) and str(key).isdigit()):
        return dict(t.get(f"bin:{int(key)}", {}))
    return dict(t.get(str(key), {}))


def load_footprint(key: str | int) -> Footprint:
    """Footprint by landmark id, BIN or (unique) name. See module docstring."""
    if isinstance(key, (int, np.integer)) or (isinstance(key, str) and key.isdigit()):
        return load_footprints([int(key)])[0]
    if key in LANDMARK_BINS:
        bins = LANDMARK_BINS[key]
        if not bins:
            raise KeyError(f"landmark {key!r} has no building footprint (sculpture/site) — place it by coordinates")
        return load_footprints(bins)[0]
    rows: list[tuple[dict, str]] = []
    for path in (LANDMARK_FOOTPRINTS_PARQUET, CANDIDATES_PARQUET):
        rows += [(r, path.name) for r in _read_rows(path, name=str(key))]
        if rows:
            break
    if not rows:
        raise KeyError(f"no footprint named like {key!r}")
    exact = [x for x in rows if str(x[0].get("name", "")).lower() == str(key).lower()]
    if len(exact) == 1:
        rows = exact
    if len({int(r["bin"]) for r, _ in rows}) > 1:
        raise KeyError(f"name {key!r} is ambiguous: " + ", ".join(f"{r['bin']}={r.get('name')}" for r, _ in rows[:8]))
    return _row_to_footprint(rows[0][0], rows[0][1])


# =============================================================================================== local frame
@dataclasses.dataclass
class LocalFrame:
    origin: tuple[float, float, float]   # NYC_TM x, y (whole metres) and ground z (NAVD88 m)
    angle_deg: float                     # +x local axis direction, degrees from east, CCW (math convention)

    @property
    def heading_deg(self) -> float:
        """Compass heading (0 = north, clockwise) of the local +x axis."""
        return (90.0 - self.angle_deg) % 360.0

    @property
    def origin_tm(self) -> list[float]:
        return [float(self.origin[0]), float(self.origin[1]), float(self.origin[2])]

    @property
    def rotation(self) -> Matrix:
        return Matrix.Rotation(math.radians(self.angle_deg), 4, "Z")

    def to_local(self, pts):
        """NYC_TM (N,2|3) -> local. Accepts a sequence of points or a numpy array."""
        a = np.asarray(pts, dtype=np.float64)
        one = a.ndim == 1
        a = a.reshape(1, -1) if one else a
        c, s = math.cos(math.radians(self.angle_deg)), math.sin(math.radians(self.angle_deg))
        dx, dy = a[:, 0] - self.origin[0], a[:, 1] - self.origin[1]
        out = a.copy()
        out[:, 0] = c * dx + s * dy
        out[:, 1] = -s * dx + c * dy
        if a.shape[1] > 2:
            out[:, 2] = a[:, 2] - self.origin[2]
        return out[0] if one else out

    def to_world(self, pts):
        a = np.asarray(pts, dtype=np.float64)
        one = a.ndim == 1
        a = a.reshape(1, -1) if one else a
        c, s = math.cos(math.radians(self.angle_deg)), math.sin(math.radians(self.angle_deg))
        out = a.copy()
        out[:, 0] = c * a[:, 0] - s * a[:, 1] + self.origin[0]
        out[:, 1] = s * a[:, 0] + c * a[:, 1] + self.origin[1]
        if a.shape[1] > 2:
            out[:, 2] = a[:, 2] + self.origin[2]
        return out[0] if one else out

    def local_angle(self, compass_deg: float) -> float:
        """Local-frame direction (math degrees from the local +x axis) of a real-world compass heading.
        ``fr.local_angle(90)`` is "east" — use it to find the street front a landmark actually faces."""
        return ((90.0 - float(compass_deg)) - self.angle_deg + 180.0) % 360.0 - 180.0

    def local_cardinal(self, compass_deg: float) -> float:
        """The local axis direction (one of 0 / 90 / 180 / -90 math degrees) nearest to a real-world compass heading.
        Footprint frames are aligned to the building's own long axis, which is rarely exactly on the street grid, so this
        is what you want when asking "which side of this building faces the avenue"."""
        la = self.local_angle(compass_deg)
        return min((0.0, 90.0, 180.0, -90.0), key=lambda a: abs((la - a + 180.0) % 360.0 - 180.0))

    def to_export(self, x: float, y: float, z: float = 0.0) -> tuple[float, float, float]:
        """Local-frame point -> the axes ``finish`` exports in (NYC_TM-parallel, origin still at the model origin).
        Use it to aim ``render_check``'s ``eye``/``target`` at something you positioned in the local frame."""
        c, s = math.cos(math.radians(self.angle_deg)), math.sin(math.radians(self.angle_deg))
        return (c * x - s * y, s * x + c * y, z)

    def _map_polygon(self, poly, fn):
        if isinstance(poly, MultiPolygon):
            return MultiPolygon([self._map_polygon(p, fn) for p in poly.geoms])
        ext = fn(np.asarray(poly.exterior.coords)[:, :2])
        holes = [fn(np.asarray(h.coords)[:, :2]) for h in poly.interiors]
        return _orient(Polygon(ext, holes), 1.0)

    def local_polygon(self, poly: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
        """NYC_TM (Multi)Polygon -> local frame (CCW, holes kept)."""
        return self._map_polygon(poly, self.to_local)

    def world_polygon(self, poly: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
        return self._map_polygon(poly, self.to_world)


def principal_angle_deg(poly: Polygon) -> float:
    """Direction (deg from east, in (-90, 90]) of the long edge of the minimum rotated rectangle."""
    mrr = poly.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    e1 = math.dist((xs[0], ys[0]), (xs[1], ys[1]))
    e2 = math.dist((xs[1], ys[1]), (xs[2], ys[2]))
    if e1 >= e2:
        ang = math.degrees(math.atan2(ys[1] - ys[0], xs[1] - xs[0]))
    else:
        ang = math.degrees(math.atan2(ys[2] - ys[1], xs[2] - xs[1]))
    ang = (ang + 90.0) % 180.0 - 90.0
    if ang <= -90.0:
        ang += 180.0
    return ang


def local_frame(polygon: Polygon, ground_z: float = 0.0, *, angle_deg: float | None = None,
                origin_xy: tuple[float, float] | None = None) -> LocalFrame:
    """Tile-local frame: origin = centroid rounded to metres, +x along the footprint's principal axis
    (override with ``angle_deg``, e.g. to align with a street rather than the long axis)."""
    c = polygon.centroid
    ox, oy = origin_xy if origin_xy is not None else (round(c.x), round(c.y))
    ang = principal_angle_deg(polygon) if angle_deg is None else float(angle_deg)
    return LocalFrame((float(ox), float(oy), float(ground_z)), ang)


# =============================================================================================== 2-D helpers
def ring_coords(poly: Polygon) -> list[tuple[float, float]]:
    """CCW exterior ring without the closing duplicate."""
    p = _orient(poly, 1.0)
    pts = [(float(x), float(y)) for x, y in p.exterior.coords[:-1]]
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-9:
        pts.pop()
    return pts


def hole_coords(poly: Polygon) -> list[list[tuple[float, float]]]:
    p = _orient(poly, 1.0)
    return [[(float(x), float(y)) for x, y in h.coords[:-1]] for h in p.interiors]


def rect(cx: float, cy: float, w: float, d: float, angle_deg: float = 0.0) -> Polygon:
    """Axis-aligned (or rotated) rectangle centred on (cx, cy), width along x, depth along y."""
    p = Polygon([(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)])
    if angle_deg:
        p = shapely.affinity.rotate(p, angle_deg, origin=(0, 0))
    return shapely.affinity.translate(p, cx, cy)


def rect_xy(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def regular_polygon(cx: float, cy: float, r: float, n: int, phase_deg: float = 0.0) -> Polygon:
    return Polygon([(cx + r * math.cos(math.radians(phase_deg) + 2 * math.pi * i / n),
                     cy + r * math.sin(math.radians(phase_deg) + 2 * math.pi * i / n)) for i in range(n)])


def offset_polygon(poly: Polygon, d: float) -> Polygon:
    """Mitred offset (positive = outward). Uses shapely; vertex count may change."""
    out = poly.buffer(d, join_style="mitre", mitre_limit=4.0)
    return _clean_polygon(out) if not out.is_empty else out


def offset_ring(coords: Sequence[tuple[float, float]], d: float, mitre_limit: float = 4.0) -> list[tuple[float, float]]:
    """Per-vertex mitred offset of a CCW ring that *preserves vertex count and order* (for lofts).
    Positive d moves outward."""
    n = len(coords)
    out = []
    for i in range(n):
        p = np.array(coords[i - 1]); v = np.array(coords[i]); q = np.array(coords[(i + 1) % n])
        e1 = v - p; e2 = q - v
        l1 = np.linalg.norm(e1); l2 = np.linalg.norm(e2)
        if l1 < 1e-9 or l2 < 1e-9:
            out.append(tuple(v)); continue
        e1 /= l1; e2 /= l2
        n1 = np.array([e1[1], -e1[0]]); n2 = np.array([e2[1], -e2[0]])
        b = n1 + n2
        lb = np.linalg.norm(b)
        if lb < 1e-9:
            out.append(tuple(v + n1 * d)); continue
        b /= lb
        k = 1.0 / max(float(np.dot(b, n1)), 1.0 / mitre_limit)
        out.append(tuple(v + b * d * k))
    return out


def scale_ring(coords: Sequence[tuple[float, float]], s: float, about: tuple[float, float] | None = None):
    a = np.asarray(coords, dtype=np.float64)
    c = np.asarray(about) if about is not None else a.mean(axis=0)
    return [tuple(p) for p in (c + (a - c) * s)]


def edges_of(coords: Sequence[tuple[float, float]]):
    """Yield (p0, p1, length, tangent, outward_normal) for each edge of a CCW ring."""
    n = len(coords)
    for i in range(n):
        p0 = np.array(coords[i], dtype=np.float64); p1 = np.array(coords[(i + 1) % n], dtype=np.float64)
        d = p1 - p0
        L = float(np.linalg.norm(d))
        if L < 1e-9:
            continue
        t = d / L
        yield p0, p1, L, t, np.array([t[1], -t[0]])


def longest_edge(coords: Sequence[tuple[float, float]]):
    return max(edges_of(coords), key=lambda e: e[2])


def wall_runs(coords: Sequence[tuple[float, float]], direction_deg: float, tol_deg: float = 50.0,
              min_len: float = 0.0) -> list[tuple[list[tuple[float, float]], float]]:
    """Maximal chains of *consecutive* ring edges whose outward normal is within ``tol_deg`` of ``direction_deg``.

    A real footprint states a straight street wall as a run of many short edges, so per-edge tests (``edge_facing``) find
    only a fragment of it; this returns each whole wall as ``(polyline points, total length)`` in ring order. Use it to
    lay bays, oriels, colonnades or entrances out along a facade rather than along one arbitrary edge."""
    d = np.array([math.cos(math.radians(direction_deg)), math.sin(math.radians(direction_deg))])
    edges = list(edges_of(coords))
    if not edges:
        return []
    ok = [float(np.dot(e[4], d)) > math.cos(math.radians(tol_deg)) for e in edges]
    n = len(edges)
    if all(ok):
        pts = [tuple(map(float, e[0])) for e in edges] + [tuple(map(float, edges[-1][1]))]
        return [(pts, sum(e[2] for e in edges))]
    runs: list[tuple[list[tuple[float, float]], float]] = []
    start = next((i for i in range(n) if ok[i] and not ok[i - 1]), None)
    if start is None:
        return []
    i = start
    for _ in range(n):
        if ok[i]:
            pts = [tuple(map(float, edges[i][0]))]
            L = 0.0
            j = i
            while ok[j]:
                pts.append(tuple(map(float, edges[j][1])))
                L += edges[j][2]
                j = (j + 1) % n
                if j == i:
                    break
            if L >= min_len:
                runs.append((pts, L))
            i = j
        else:
            i = (i + 1) % n
        if i == start:
            break
    return runs


def polyline_at(pts: Sequence[tuple[float, float]], s: float):
    """(point, unit tangent, outward normal) at arc length ``s`` along a polyline given in CCW ring order."""
    P = [np.asarray(p, dtype=np.float64) for p in pts]
    acc = 0.0
    for i in range(len(P) - 1):
        d = P[i + 1] - P[i]
        L = float(np.linalg.norm(d))
        if L < 1e-9:
            continue
        if acc + L >= s or i == len(P) - 2:
            t = d / L
            return P[i] + t * max(0.0, min(L, s - acc)), t, np.array([t[1], -t[0]])
        acc += L
    t = np.array([1.0, 0.0])
    return P[0], t, np.array([t[1], -t[0]])


def ring_perimeter(coords: Sequence[tuple[float, float]]) -> float:
    return float(sum(e[2] for e in edges_of(coords)))


def ring_stations(coords: Sequence[tuple[float, float]], spacing: float, *, offset: float = 0.0):
    """Yield ``(point, tangent, outward_normal, s)`` at equal arc-length stations right round a closed ring.

    Real footprints break a straight wall into many short segments and round the corners into 0.2 m chords, so laying
    bays out per *edge* gives a nonsense rhythm. This walks the perimeter instead: use it for buttresses, bay divisions,
    lamp posts, balusters — anything whose real spacing is measured along the wall."""
    if len(coords) < 3:
        return
    ring = list(coords) + [coords[0]]
    per = polyline_length(ring)
    if per < max(spacing, 1e-3):
        return
    n = max(1, int(round(per / max(spacing, 1e-3))))
    step = per / n
    for i in range(n):
        s = (offset + i * step) % per
        p, t, nn = polyline_at(ring, s)
        yield p, t, nn, s


def polyline_length(pts: Sequence[tuple[float, float]]) -> float:
    return float(sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)))


def edge_facing(coords: Sequence[tuple[float, float]], direction_deg: float, min_len: float = 3.0):
    """The longest edge whose outward normal is within 45 deg of ``direction_deg`` (local frame, math degrees)."""
    d = np.array([math.cos(math.radians(direction_deg)), math.sin(math.radians(direction_deg))])
    cands = [e for e in edges_of(coords) if e[2] >= min_len and float(np.dot(e[4], d)) > math.cos(math.radians(45))]
    if not cands:
        raise ValueError(f"no edge facing {direction_deg} deg")
    return max(cands, key=lambda e: e[2])


# =============================================================================================== materials
def _srgb(r: int, g: int, b: int) -> tuple[float, float, float, float]:
    def f(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b), 1.0)


# name: (sRGB albedo 0-255, roughness, metallic, emission rgb or None, emission strength, note/source)
PALETTE: dict[str, tuple] = {
    "limestone":        ((200, 190, 170), 0.75, 0.0, None, 0.0, "Indiana limestone, buff-grey (measured albedo ~0.55)"),
    "limestone_dark":   ((172, 163, 148), 0.8, 0.0, None, 0.0, "weathered/soiled limestone"),
    "limestone_warm":   ((212, 198, 172), 0.72, 0.0, None, 0.0, "Bedford limestone, warm buff (Grand Central, NYPL Vermont marble reads warmer)"),
    "marble_white":     ((228, 224, 216), 0.55, 0.0, None, 0.0, "Vermont/Tuckahoe/Massachusetts white marble"),
    "marble_tennessee": ((206, 190, 178), 0.4, 0.0, None, 0.0, "Tennessee pink marble (Grand Central concourse floor and walls)"),
    "limestone_rusticated": ((196, 186, 166), 0.85, 0.0, None, 0.0, "rusticated limestone base courses (deep-jointed ashlar)"),
    "granite_rusticated":   ((132, 128, 124), 0.8, 0.0, None, 0.0, "rusticated granite base courses"),
    "plaster_cream":    ((214, 204, 186), 0.9, 0.0, None, 0.0, "cast-plaster interior cornices/soffits"),
    "brass":            ((178, 142, 72), 0.3, 0.9, None, 0.0, "polished brass (Grand Central clock, handrails, ticket-window grilles)"),
    "granite_grey":     ((138, 134, 130), 0.7, 0.0, None, 0.0, "Deer Isle/Quincy grey granite"),
    "granite_pink":     ((168, 142, 126), 0.7, 0.0, None, 0.0, "Stony Creek/Milford pink granite"),
    "granite_dark":     ((64, 62, 62), 0.6, 0.0, None, 0.0, "dark polished granite base courses"),
    "granite_black":    ((22, 22, 24), 0.35, 0.0, None, 0.0, "black granite (MoMA Taniguchi, modern lobbies)"),
    "brownstone":       ((112, 76, 60), 0.85, 0.0, None, 0.0, "Little Falls brownstone (Trinity Church)"),
    "sandstone_red":    ((150, 95, 70), 0.85, 0.0, None, 0.0, "red sandstone trim"),
    "white_brick":      ((216, 209, 196), 0.85, 0.0, None, 0.0, "white/grey glazed brick (Chrysler)"),
    "grey_brick_dark":  ((62, 60, 60), 0.85, 0.0, None, 0.0, "dark grey brick trim (Chrysler)"),
    "brick_red":        ((146, 78, 62), 0.9, 0.0, None, 0.0, "red brick"),
    "brick_buff":       ((190, 170, 135), 0.9, 0.0, None, 0.0, "buff brick"),
    "terracotta_cream": ((218, 208, 188), 0.6, 0.0, None, 0.0, "cream glazed terracotta (Woolworth, One Vanderbilt fins)"),
    "terracotta_red":   ((176, 122, 96), 0.75, 0.0, None, 0.0, "red-brown terracotta (Flatiron upper floors)"),
    "concrete":         ((160, 158, 150), 0.85, 0.0, None, 0.0, "precast concrete"),
    "concrete_dark":    ((110, 108, 104), 0.85, 0.0, None, 0.0, "board-formed / MSG precast panels"),
    "glass_dark":       ((18, 26, 34), 0.12, 0.25, None, 0.0, "punched-window glazing, dark reflective"),
    "glass_blue":       ((80, 112, 136), 0.06, 0.55, None, 0.0, "low-e curtain-wall glass"),
    "glass_clear":      ((150, 175, 185), 0.05, 0.4, None, 0.0, "clear storefront/lobby glass"),
    "steel_nirosta":    ((205, 205, 210), 0.22, 1.0, None, 0.0, "Nirosta (Krupp KA-2) stainless steel (Chrysler crown)"),
    "steel_chrome":     ((155, 157, 160), 0.35, 0.9, None, 0.0, "chrome-nickel steel spandrels (Empire State)"),
    "aluminium":        ((175, 176, 178), 0.4, 0.85, None, 0.0, "anodised aluminium mullions"),
    "aluminium_cast":   ((182, 180, 172), 0.55, 0.3, None, 0.0, "cast-aluminium spandrel panels (Rockefeller Center) — matt, only lightly specular"),
    "steel_dark":       ((48, 50, 54), 0.5, 0.7, None, 0.0, "painted steel (dark)"),
    "cast_iron":        ((36, 36, 38), 0.6, 0.6, None, 0.0, "black painted cast iron"),
    "bronze":           ((96, 66, 38), 0.45, 0.85, None, 0.0, "statuary bronze"),
    "bronze_patina":    ((72, 54, 34), 0.55, 0.7, None, 0.0, "handled/patinated bronze (Charging Bull)"),
    "gold":             ((212, 172, 82), 0.3, 1.0, None, 0.0, "gold leaf (Prometheus, Civic Fame, Municipal Building)"),
    "copper_green":     ((82, 142, 122), 0.7, 0.2, None, 0.0, "verdigris copper (40 Wall pyramid, Woolworth crown)"),
    "copper_new":       ((150, 90, 60), 0.4, 0.9, None, 0.0, "new copper"),
    "roof_dark":        ((46, 46, 48), 0.9, 0.0, None, 0.0, "built-up roof membrane"),
    "roof_grey":        ((120, 120, 118), 0.9, 0.0, None, 0.0, "ballasted / pavers"),
    "slate":            ((60, 66, 74), 0.8, 0.0, None, 0.0, "slate roofing"),
    "asphalt":          ((54, 54, 54), 0.95, 0.0, None, 0.0, "street asphalt (render ground)"),
    "pavement":         ((150, 148, 142), 0.9, 0.0, None, 0.0, "concrete sidewalk / plaza pavers"),
    "wood_dark":        ((72, 46, 30), 0.7, 0.0, None, 0.0, "dark stained wood doors"),
    "ice_white":        ((226, 236, 246), 0.2, 0.0, None, 0.0, "skating rink ice"),
    "grass":            ((70, 110, 50), 0.95, 0.0, None, 0.0, "lawn"),
    "water_dark":       ((30, 50, 60), 0.05, 0.3, None, 0.0, "fountain water"),
    "flag_red":         ((178, 34, 52), 0.8, 0.0, None, 0.0, "flag red (US flag Old Glory Red)"),
    "flag_white":       ((240, 240, 240), 0.8, 0.0, None, 0.0, "flag white"),
    "flag_blue":        ((60, 59, 110), 0.8, 0.0, None, 0.0, "flag blue (Old Glory Blue)"),
    "ESB_CROWN":        ((240, 240, 240), 0.5, 0.0, (1.0, 1.0, 1.0), 6.0, "Empire State crown lighting slot — emissive; UE drives colour from live/esb_lights.json"),
    "emissive_warm":    ((250, 235, 200), 0.5, 0.0, (1.0, 0.85, 0.6), 4.0, "warm interior/lobby light"),
    "GCT_CEILING":      ((70, 105, 120), 0.9, 0.0, (0.35, 0.62, 0.75), 3.5, "Grand Central celestial ceiling (cerulean with gold constellations) — emissive at a strength that also lights the concourse, as the real ceiling does"),
}
_MATS: dict[str, bpy.types.Material] = {}

# Palette name -> CC0 PBR set in blender/common/textures.py (AmbientCG / Poly Haven; see assets/textures/*/LICENSE.json).
# Only surfaces whose *relief* reads at building scale are textured; glass, polished metal, flags, ice and the emissive
# slots stay flat Principled colours. The colour map is multiplied by a tint that restores the documented albedo below.
TEXTURE_NAMES: dict[str, str] = {
    # Indiana limestone and Vermont marble are near-uniform fine-grained ashlar at building scale: the catalog's
    # "limestone" set (Travertine009) is strongly banded and reads as veneer, so the fine-grained Concrete030 grain is
    # used for smooth ashlar and the coarse sandstone-block set only where the real wall is rusticated.
    "limestone": "concrete", "limestone_dark": "concrete", "limestone_warm": "concrete", "marble_white": "concrete",
    "limestone_rusticated": "limestone_ashlar", "granite_rusticated": "granite_rusticated",
    "granite_grey": "granite", "granite_pink": "granite", "granite_dark": "granite", "granite_black": "granite",
    "brownstone": "brownstone", "sandstone_red": "brownstone",
    "white_brick": "white_glazed_brick", "grey_brick_dark": "white_glazed_brick",
    "brick_red": "red_brick", "brick_buff": "tan_brick",
    "terracotta_cream": "terracotta", "terracotta_red": "terracotta",
    "concrete": "concrete", "concrete_dark": "precast", "pavement": "concrete_sidewalk",
    "asphalt": "asphalt", "roof_dark": "roof_membrane", "roof_grey": "tar_gravel_roof", "cast_iron": "cast_iron",
    "marble_tennessee": "terrazzo", "plaster_cream": "stucco",
}
TEXTURES_ENABLED = os.environ.get("NYCSIM_LANDMARK_TEXTURES", "1") != "0"
TEXTURE_RES = os.environ.get("NYCSIM_LANDMARK_TEXTURE_RES", "1K")
_texture_status: dict[str, str] = {}
_tex_mean: dict[str, tuple[float, float, float]] = {}


def texture_status() -> dict[str, str]:
    """Per palette name: ``"<set> @<res>"`` when PBR maps were attached, or the reason they were not."""
    return dict(_texture_status)


def _image_mean_rgb(path: str) -> tuple[float, float, float]:
    """Mean *linear* RGB of a colour map (cached), used to compute the tint that restores the documented albedo."""
    if path in _tex_mean:
        return _tex_mean[path]
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB"
    n = img.size[0] * img.size[1] * img.channels
    buf = np.empty(n, dtype=np.float32)
    img.pixels.foreach_get(buf)
    buf = buf.reshape(-1, img.channels)[:, :3]           # Blender gives linear float pixels
    m = tuple(float(max(v, 1e-3)) for v in buf.mean(axis=0))
    _tex_mean[path] = m
    return m


def _tint_base_color(material: bpy.types.Material, albedo: tuple[float, float, float, float],
                     color_path: str) -> tuple[float, float, float]:
    """Insert ``colour map x tint`` before Base Color so the textured surface carries the documented mean albedo, and
    return the tint. Blender's glTF exporter turns exactly this node (``ShaderNodeMix``, RGBA, MULTIPLY, factor 1) into
    ``baseColorTexture x baseColorFactor``, so the render and the exported .glb agree.

    glTF restricts ``baseColorFactor`` to [0, 1], so the tint can only *darken*: where the CC0 scan is already darker
    than the documented albedo the tint is 1 and the surface keeps the scan's albedo. The tint actually applied is
    reported by :func:`texture_status` and recorded in the catalog entry."""
    nt = material.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    # socket identity is not stable across RNA accesses, so match by node and socket name
    link = next((l for l in nt.links if l.to_node == bsdf and l.to_socket.name == "Base Color"), None)
    if link is None:
        raise RuntimeError("no colour link into Base Color")
    src = link.from_socket
    mean = _image_mean_rgb(color_path)
    tint = tuple(min(1.0, albedo[i] / mean[i]) for i in range(3))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.remove(link)
    nt.links.new(src, mix.inputs[6])                      # A (colour)
    mix.inputs[7].default_value = (*tint, 1.0)            # B (constant tint)
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return tint


def _texture_maps(name: str) -> tuple[dict[str, str], float] | None:
    """({kind: path}, physical tile size in metres) from blender/common/textures.py, or None (reason recorded once)."""
    if not TEXTURES_ENABLED or name not in TEXTURE_NAMES:
        return None
    if _texture_status.get(name, "").startswith("no texture"):
        return None
    try:
        import textures as tx                              # blender/common/textures.py
        maps = tx.get_texture_set(TEXTURE_NAMES[name], TEXTURE_RES)
        size = float(tx.get_texture_meta(TEXTURE_NAMES[name]).get("physical_size_m") or 2.0)
    except Exception as e:                                 # offline / catalog gap -> documented flat colour, recorded
        _texture_status[name] = f"no texture ({type(e).__name__}: {str(e)[:100]})"
        log.info("material %s: %s; using the documented Principled albedo", name, _texture_status[name])
        return None
    keep = {k: v for k, v in maps.items() if k in ("color", "roughness", "normal", "metallic", "metalness")}
    if "metalness" in keep:
        keep["metallic"] = keep.pop("metalness")
    if "color" not in keep:
        _texture_status[name] = "no texture (set has no colour map)"
        return None
    _texture_status[name] = f"{TEXTURE_NAMES[name]} @{TEXTURE_RES} ({size:g} m tile)"
    return keep, size


def mat(name: str) -> bpy.types.Material:
    """Palette material by name (created once per scene). Masonry/paving names get the CC0 PBR maps that
    ``blender/common/textures.py`` provides, tiled in metres over the box-projected UVs written by ``MeshBuilder.build``;
    every other name (and every name textures.py cannot serve) is the documented flat Principled albedo."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    if name not in PALETTE:
        raise KeyError(f"unknown palette material {name!r}; add it to PALETTE with its documented albedo")
    rgb, rough, metal, emis, estr, _ = PALETTE[name]
    albedo = _srgb(*rgb)
    tex = None if emis else _texture_maps(name)
    if tex is None:
        return nb.pbr_material(name, base_color=albedo, roughness=rough, metallic=metal,
                               emission=(emis + (1.0,)) if emis else None, emission_strength=estr)
    maps, size = tex
    m = nb.pbr_material(name, base_color=albedo, roughness=rough, metallic=metal, textures=maps, uv_scale_m=size)
    try:
        tint = _tint_base_color(m, albedo, maps["color"])
        _texture_status[name] += " tint " + "/".join(f"{v:.2f}" for v in tint)
    except Exception as e:                                 # keep the (untinted) textured material rather than failing
        log.warning("material %s: could not tint the colour map to the documented albedo (%s)", name, e)
        _texture_status[name] += " (untinted)"
    m["nycsim_texture_set"] = TEXTURE_NAMES[name]
    m["nycsim_uv_tile_m"] = size
    return m


class _MatProxy:
    def __getattr__(self, name):
        return mat(name)

    def __getitem__(self, name):
        return mat(name)


M = _MatProxy()


def custom_material(name: str, rgb255: tuple[int, int, int], roughness: float = 0.7, metallic: float = 0.0,
                    emission: tuple[float, float, float] | None = None, emission_strength: float = 0.0, note: str = "") -> bpy.types.Material:
    """Add a one-off material to the palette (so it is documented) and return it."""
    PALETTE.setdefault(name, (rgb255, roughness, metallic, emission, emission_strength, note))
    return mat(name)


# =============================================================================================== mesh builder
def box_uv(me: bpy.types.Mesh, layer: str = "UVMap") -> None:
    """Box-project UVs **in metres**: every face is projected onto the world plane its normal points along most strongly
    (x-normal -> (y, z), y-normal -> (x, z), z-normal -> (x, y)). Tiling is then purely physical — a material built by
    :func:`mat` divides by its texture's ``physical_size_m``, so one tile always covers that many metres of wall."""
    if not me.polygons:
        return
    uv = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    nv = len(me.vertices)
    co = np.empty(nv * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    nl = len(me.loops)
    vidx = np.empty(nl, dtype=np.int32); me.loops.foreach_get("vertex_index", vidx)
    npoly = len(me.polygons)
    nrm = np.empty(npoly * 3, dtype=np.float32); me.polygons.foreach_get("normal", nrm)
    ltot = np.empty(npoly, dtype=np.int32); me.polygons.foreach_get("loop_total", ltot)
    axis = np.repeat(np.argmax(np.abs(nrm.reshape(-1, 3)), axis=1), ltot)
    if axis.shape[0] != nl:                                  # non-contiguous loops (should not happen for from_pydata)
        raise RuntimeError(f"mesh {me.name}: {axis.shape[0]} loop slots for {nl} loops")
    p = co[vidx]
    out = np.empty((nl, 2), dtype=np.float32)
    out[:, 0] = np.where(axis == 0, p[:, 1], p[:, 0])
    out[:, 1] = np.where(axis == 2, p[:, 1], p[:, 2])
    uv.data.foreach_set("uv", out.ravel())


class MeshBuilder:
    """Accumulates vertices/faces with a material index per face, then builds one Blender object.

    Faces may be tris, quads or n-gons; n-gons must be planar. All coordinates are local-frame metres."""

    def __init__(self):
        self.v: list[tuple[float, float, float]] = []
        self.f: list[tuple[int, ...]] = []
        self.fm: list[int] = []
        self.fs: list[bool] = []
        self.mats: list[bpy.types.Material] = []
        self._mi: dict[str, int] = {}

    # -- bookkeeping
    def mi(self, material) -> int:
        if material is None:
            material = mat("concrete")
        if material.name not in self._mi:
            self._mi[material.name] = len(self.mats)
            self.mats.append(material)
        return self._mi[material.name]

    def vert(self, x, y, z) -> int:
        self.v.append((float(x), float(y), float(z)))
        return len(self.v) - 1

    def face(self, idx: Sequence[int], material, smooth: bool = False) -> None:
        if len(idx) < 3:
            return
        self.f.append(tuple(int(i) for i in idx))
        self.fm.append(self.mi(material))
        self.fs.append(smooth)

    def quad(self, a, b, c, d, material, smooth=False) -> None:
        """Quad from four 3-D points (CCW seen from the outside)."""
        i = [self.vert(*p) for p in (a, b, c, d)]
        self.face(i, material, smooth)

    def tri(self, a, b, c, material, smooth=False) -> None:
        self.face([self.vert(*p) for p in (a, b, c)], material, smooth)

    @property
    def tri_count(self) -> int:
        return sum(len(f) - 2 for f in self.f)

    # -- primitives
    def box(self, center, size, material, *, top=True, bottom=True, sides=True, material_top=None, rot_deg: float = 0.0) -> None:
        """Axis-aligned box (optionally rotated about Z through its centre)."""
        cx, cy, cz = center; sx, sy, sz = size
        c, s = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))

        def P(dx, dy, dz):
            return (cx + c * dx - s * dy, cy + s * dx + c * dy, cz + dz)
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        p = [P(-hx, -hy, -hz), P(hx, -hy, -hz), P(hx, hy, -hz), P(-hx, hy, -hz), P(-hx, -hy, hz), P(hx, -hy, hz), P(hx, hy, hz), P(-hx, hy, hz)]
        i = [self.vert(*q) for q in p]
        if bottom:
            self.face((i[0], i[3], i[2], i[1]), material)
        if top:
            self.face((i[4], i[5], i[6], i[7]), material_top or material)
        if sides:
            for a, b, cc, d in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
                self.face((i[a], i[b], i[cc], i[d]), material)

    def box_from_to(self, p0, p1, normal, depth, z0, z1, material, *, top=True, bottom=False, material_top=None):
        """Box spanning the wall segment p0->p1 (2-D), extruded *outward* along ``normal`` by ``depth``, between z0 and z1."""
        p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); n = np.asarray(normal, dtype=np.float64)
        q0 = p0 + n * depth; q1 = p1 + n * depth
        i = [self.vert(*p0, z0), self.vert(*p1, z0), self.vert(*q1, z0), self.vert(*q0, z0),
             self.vert(*p0, z1), self.vert(*p1, z1), self.vert(*q1, z1), self.vert(*q0, z1)]
        # outward face is q0-q1 (front), sides p0-q0 and p1-q1, back p0-p1 (usually hidden)
        self.face((i[3], i[2], i[6], i[7]), material)            # front (outward)
        self.face((i[0], i[3], i[7], i[4]), material)            # side at p0
        self.face((i[2], i[1], i[5], i[6]), material)            # side at p1
        self.face((i[1], i[0], i[4], i[5]), material)            # back
        if top:
            self.face((i[4], i[7], i[6], i[5]), material_top or material)
        if bottom:
            self.face((i[0], i[1], i[2], i[3]), material)

    def prism(self, ring, z0, z1, material, *, holes=(), material_top=None, material_bottom=None, cap_top=True, cap_bottom=True,
              smooth_sides=False) -> None:
        """Vertical prism from a CCW ring (+ CW/CCW holes, orientation fixed here)."""
        ring = [tuple(p[:2]) for p in ring]
        if len(ring) < 3:
            return
        holes = [[tuple(p[:2]) for p in h] for h in holes]
        holes = [h if Polygon(h).exterior.is_ccw else list(reversed(h)) for h in holes]
        holes = [list(reversed(h)) for h in holes]  # CW so their walls face inward
        b0 = [self.vert(x, y, z0) for x, y in ring]
        b1 = [self.vert(x, y, z1) for x, y in ring]
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            self.face((b0[i], b0[j], b1[j], b1[i]), material, smooth_sides)
        hb0, hb1 = [], []
        for h in holes:
            h0 = [self.vert(x, y, z0) for x, y in h]; h1 = [self.vert(x, y, z1) for x, y in h]
            m = len(h)
            for i in range(m):
                j = (i + 1) % m
                self.face((h0[i], h0[j], h1[j], h1[i]), material, smooth_sides)
            hb0.append(h0); hb1.append(h1)
        if cap_top or cap_bottom:
            try:
                tris = nb.triangulate_2d(ring, holes)
            except ValueError as e:
                # A hole that touches or crosses the outer ring (a wall ring offset too far inwards for a thin part of
                # the plan) cannot be triangulated. The walls are already built; skip the caps and say which shape.
                log.warning("prism: skipping caps, cannot triangulate ring of %d pts with %d hole(s): %s",
                            len(ring), len(holes), e)
                return
            top_idx = b1 + [v for h in hb1 for v in h]
            bot_idx = b0 + [v for h in hb0 for v in h]
            for a, b, c in tris:
                if cap_top:
                    self.face((top_idx[a], top_idx[b], top_idx[c]), material_top or material)
                if cap_bottom:
                    self.face((bot_idx[c], bot_idx[b], bot_idx[a]), material_bottom or material)

    def loft(self, rings, material, *, cap_top=True, cap_bottom=True, smooth=False, material_top=None, closed=True) -> None:
        """Loft successive rings of *equal vertex count* (each ring: list of (x, y, z)). Rings CCW seen from above."""
        rings = [[tuple(map(float, p)) for p in r] for r in rings]
        n = len(rings[0])
        for r in rings:
            if len(r) != n:
                raise ValueError("loft rings must have equal vertex counts")
        idx = [[self.vert(*p) for p in r] for r in rings]
        for k in range(len(rings) - 1):
            a, b = idx[k], idx[k + 1]
            rng = range(n) if closed else range(n - 1)
            for i in rng:
                j = (i + 1) % n
                self.face((a[i], a[j], b[j], b[i]), material, smooth)
        if closed and cap_bottom:
            tris = nb.triangulate_2d([p[:2] for p in rings[0]])
            for a_, b_, c_ in tris:
                self.face((idx[0][c_], idx[0][b_], idx[0][a_]), material)
        if closed and cap_top:
            tris = nb.triangulate_2d([p[:2] for p in rings[-1]])
            for a_, b_, c_ in tris:
                self.face((idx[-1][a_], idx[-1][b_], idx[-1][c_]), material_top or material)

    def lathe(self, profile, segments, material, *, origin=(0.0, 0.0, 0.0), smooth=True, phase_deg=0.0, cap=True, scale_xy=(1.0, 1.0)) -> None:
        """Surface of revolution about a vertical axis through ``origin``. ``profile`` = [(r, z), ...] bottom->top;
        r = 0 makes a pole. ``scale_xy`` squashes the circle into an ellipse."""
        ox, oy, oz = origin
        ang = [math.radians(phase_deg) + 2 * math.pi * i / segments for i in range(segments)]
        rings: list[list[int] | int] = []
        for r, z in profile:
            if abs(r) < 1e-6:
                rings.append(self.vert(ox, oy, oz + z))
            else:
                rings.append([self.vert(ox + r * math.cos(a) * scale_xy[0], oy + r * math.sin(a) * scale_xy[1], oz + z) for a in ang])
        for k in range(len(rings) - 1):
            a, b = rings[k], rings[k + 1]
            if isinstance(a, int) and isinstance(b, int):
                continue
            if isinstance(a, int):
                for i in range(segments):
                    j = (i + 1) % segments
                    self.face((a, b[j], b[i]), material, smooth)
            elif isinstance(b, int):
                for i in range(segments):
                    j = (i + 1) % segments
                    self.face((a[i], a[j], b), material, smooth)
            else:
                for i in range(segments):
                    j = (i + 1) % segments
                    self.face((a[i], a[j], b[j], b[i]), material, smooth)
        if cap:
            if not isinstance(rings[0], int):
                self.face(tuple(reversed(rings[0])), material)
            if not isinstance(rings[-1], int):
                self.face(tuple(rings[-1]), material)

    def hull(self, pts3d, material, *, smooth: bool = False) -> None:
        """Convex hull solid of the given 3-D points (outward-oriented triangles). Use for wedges, pyramids, pediments."""
        from scipy.spatial import ConvexHull
        P = np.asarray(pts3d, dtype=np.float64)
        if len(P) < 4:
            return
        try:
            h = ConvexHull(P)
        except Exception:
            h = ConvexHull(P, qhull_options="QJ")
        base = len(self.v)
        for q in P:
            self.vert(*q)
        for simplex, eq in zip(h.simplices, h.equations):
            a, b_, c = (int(i) for i in simplex)
            nrm = np.cross(P[b_] - P[a], P[c] - P[a])
            if np.dot(nrm, eq[:3]) < 0:
                a, c = c, a
            self.face((base + a, base + b_, base + c), material, smooth)

    def ngon_vertical(self, pts3d, material, *, flip=False) -> None:
        """Planar vertical polygon (e.g. an arch face) given 3-D points in order; triangulated in its own plane."""
        p = np.asarray(pts3d, dtype=np.float64)
        d = p[:, :2] - p[0, :2]
        L = np.linalg.norm(d, axis=1)
        k = int(np.argmax(L))
        t = d[k] / L[k] if L[k] > 1e-9 else np.array([1.0, 0.0])
        u = d @ t
        pts2 = list(zip(u, p[:, 2]))
        # ensure CCW in (u, z)
        area = 0.5 * sum(pts2[i][0] * pts2[(i + 1) % len(pts2)][1] - pts2[(i + 1) % len(pts2)][0] * pts2[i][1] for i in range(len(pts2)))
        tris = nb.triangulate_2d(pts2)
        idx = [self.vert(*q) for q in p]
        for a, b, c in tris:
            f = (idx[a], idx[b], idx[c]) if (area > 0) != flip else (idx[c], idx[b], idx[a])
            self.face(f, material)

    def ngon(self, pts3d, material, *, flip=False) -> None:
        """Planar horizontal polygon (CCW from above) as one n-gon face."""
        idx = [self.vert(*q) for q in pts3d]
        self.face(tuple(reversed(idx)) if flip else tuple(idx), material)

    def merge(self, other: "MeshBuilder") -> None:
        off = len(self.v)
        self.v.extend(other.v)
        remap = {i: self.mi(m) for i, m in enumerate(other.mats)}
        for f, m, s in zip(other.f, other.fm, other.fs):
            self.f.append(tuple(i + off for i in f)); self.fm.append(remap[m]); self.fs.append(s)

    def transform(self, matrix: Matrix) -> None:
        self.v = [tuple(matrix @ Vector(p)) for p in self.v]

    def translate(self, dx, dy, dz) -> None:
        self.v = [(x + dx, y + dy, z + dz) for x, y, z in self.v]

    def build(self, name: str, *, role: str | None = None, col=None) -> bpy.types.Object:
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for p, m, s in zip(me.polygons, self.fm, self.fs):
            p.material_index = m
            p.use_smooth = s
        me.validate(verbose=False, clean_customdata=False)
        me.update()
        box_uv(me)
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        nb.link(ob, col)
        if role:
            ob["nycsim_role"] = role
        return ob


# =============================================================================================== high-level builders
def tag(ob: bpy.types.Object, role: str) -> bpy.types.Object:
    ob["nycsim_role"] = role
    return ob


def prism(name: str, poly: Polygon, z0: float, z1: float, material, *, inset: float = 0.0, material_top=None,
          role: str | None = None, cap_bottom: bool = True) -> bpy.types.Object:
    """Extrude a (local-frame) shapely polygon (holes kept, MultiPolygon parts joined) between z0 and z1."""
    b = MeshBuilder()
    parts = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
    for p in parts:
        if inset:
            p = offset_polygon(p, -inset)
            if p.is_empty:
                continue
            if isinstance(p, MultiPolygon):
                for q in p.geoms:
                    b.prism(ring_coords(q), z0, z1, material, holes=hole_coords(q), material_top=material_top, cap_bottom=cap_bottom)
                continue
        b.prism(ring_coords(p), z0, z1, material, holes=hole_coords(p), material_top=material_top, cap_bottom=cap_bottom)
    return b.build(name, role=role)


def wall_ring(b: MeshBuilder, poly: Polygon | MultiPolygon, z0: float, z1: float, thickness: float, material, *,
              cap_top: bool = True, cap_bottom: bool = False, material_top=None) -> None:
    """A wall of ``thickness`` following ``poly``: the polygon extruded z0->z1 with its inward offset cut out as a hole.
    Where the inward offset would close or split the ring (a plan too thin for that thickness), the wall is built solid
    there instead of failing — parapets, garden walls, string courses and balustrade plinths all go through this."""
    parts = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
    for p in parts:
        inner = offset_polygon(p, -abs(thickness))
        holes: list[list[tuple[float, float]]] = []
        if isinstance(inner, Polygon) and not inner.is_empty and inner.area > 1e-3 and inner.within(p):
            holes = [ring_coords(inner)]
        elif isinstance(inner, MultiPolygon):
            holes = [ring_coords(q) for q in inner.geoms if q.area > 1e-3 and q.within(p)]
        b.prism(ring_coords(p), z0, z1, material, holes=holes, cap_top=cap_top, cap_bottom=cap_bottom,
                material_top=material_top)


def plinth(name: str, poly: Polygon, z0: float, z1: float, material, *, role: str = "base", material_top=None) -> bpy.types.Object:
    """Flush ground-floor volume on the *real* footprint (this is what the IoU check slices)."""
    return prism(name, poly, z0, z1, material, role=role, material_top=material_top)


@dataclasses.dataclass
class Fenestration:
    """Facade grid recipe for :func:`facade_grid`.

    floor_h: storey height (m) or explicit list of floor-line z values (absolute, local) via ``floor_z``.
    bay_w: target bay module (m) -> bays per edge = round(L / bay_w) (min 1); or ``bays_for(edge_len)`` callback.
    window_frac: window width / bay module (0..1). pier material shows between windows.
    recess: depth of the glass plane behind the pier face (m). spandrel_h: spandrel band height (m) at each floor line.
    spandrel_proud: how far the spandrel protrudes from the glass plane (<= recess).
    strip: True -> continuous vertical window strips (spandrels flush with glass, ESB style).
    mullions: number of vertical sub-mullions inside each window (thin bars).
    sill: sill/lintel band depth (m) below each window (0 = none).
    min_edge: edges shorter than this get a plain wall.
    """
    floor_h: float = 3.6
    bay_w: float = 3.2
    window_frac: float = 0.55
    recess: float = 0.35
    spandrel_h: float = 0.9
    spandrel_proud: float = 0.12
    strip: bool = False
    mullions: int = 0
    sill: float = 0.0
    min_edge: float = 2.0
    pier: str = "limestone"
    spandrel: str = "limestone"
    glass: str = "glass_dark"
    mullion: str = "aluminium"
    floor_z: Sequence[float] | None = None
    bays_for: object = None    # callable(edge_len) -> int
    window_h: float | None = None   # explicit window height (m); default = storey - spandrel


def facade_edge(b: MeshBuilder, p0, p1, normal, z0: float, z1: float, fen: Fenestration, *, top_cap: bool = True) -> None:
    """Fenestrated skin for one wall edge p0->p1 (2-D), outward ``normal``. Pier faces lie on the p0-p1 line; the glass plane
    is ``fen.recess`` behind it. Per storey (between consecutive floor lines): spandrel band at the bottom, window above it
    up to ``window_h`` (or the next floor line), remaining head zone filled with spandrel material. ``strip`` mode keeps the
    glass/spandrel strip continuous (spandrels flush) as on the Empire State Building."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); n = np.asarray(normal, dtype=np.float64)
    L = float(np.linalg.norm(p1 - p0))
    if L < 1e-6:
        return
    t = (p1 - p0) / L
    pier_m, span_m, glass_m, mull_m = mat(fen.pier), mat(fen.spandrel), mat(fen.glass), mat(fen.mullion)
    back = -n * fen.recess
    if L < fen.min_edge:
        b.box_from_to(p0 + back, p1 + back, n, fen.recess, z0, z1, pier_m, top=top_cap)
        return
    nb_ = int(fen.bays_for(L)) if fen.bays_for else max(1, int(round(L / fen.bay_w)))
    module = L / nb_
    w = module * fen.window_frac
    pw = module - w
    if fen.floor_z is not None:
        zs = [float(z) for z in fen.floor_z if z0 + 1e-6 < z < z1 - 1e-6]
        zs = [z0] + zs + [z1]
    else:
        nfl = max(1, int(round((z1 - z0) / fen.floor_h)))
        zs = [z0 + (z1 - z0) * k / nfl for k in range(nfl + 1)]
    # piers: half-width at both ends (they meet the neighbouring facade's end pier at the corner), full between bays
    for k in range(nb_ + 1):
        s0 = 0.0 if k == 0 else k * module - pw / 2
        s1 = L if k == nb_ else k * module + pw / 2
        a = p0 + t * s0 + back; c = p0 + t * s1 + back
        b.box_from_to(a, c, n, fen.recess, z0, z1, pier_m, top=top_cap)
    for k in range(nb_):
        s0 = k * module + pw / 2
        s1 = (k + 1) * module - pw / 2
        a = p0 + t * s0 + back; c = p0 + t * s1 + back
        b.quad((a[0], a[1], z0), (c[0], c[1], z0), (c[0], c[1], z1), (a[0], a[1], z1), glass_m)
        proud = 0.02 if fen.strip else min(fen.spandrel_proud, fen.recess - 0.01)
        for si in range(len(zs) - 1):
            zf0, zf1 = zs[si], zs[si + 1]
            storey = zf1 - zf0
            sp = min(fen.spandrel_h, storey * 0.6)
            if fen.strip and si == 0:
                sp = 0.0  # strip starts at the tier base
            if sp > 0:
                b.box_from_to(a, c, n, proud, zf0, zf0 + sp, span_m, top=True, bottom=True)
                if fen.sill > 0 and not fen.strip:
                    b.box_from_to(a, c, n, min(fen.recess - 0.01, fen.sill), zf0 + sp, zf0 + sp + 0.12, pier_m, top=True, bottom=True)
            if fen.window_h is not None and not fen.strip:
                head0 = zf0 + sp + fen.window_h
                if head0 < zf1 - 0.05:
                    b.box_from_to(a, c, n, proud, head0, zf1, span_m, top=True, bottom=True)
        if fen.mullions > 0:
            for mk in range(1, fen.mullions + 1):
                sm = s0 + (s1 - s0) * mk / (fen.mullions + 1)
                q = p0 + t * sm + back + n * 0.05
                b.box((q[0], q[1], (z0 + z1) / 2), (0.08, 0.10, z1 - z0), mull_m, rot_deg=math.degrees(math.atan2(t[1], t[0])), top=False, bottom=False)


def facade_grid(name: str, poly: Polygon, z0: float, z1: float, fen: Fenestration, *, edges: Iterable[int] | None = None,
                top_cap: bool = True, blank_edges: Iterable[int] = ()) -> bpy.types.Object:
    """Fenestrated skin around every edge of ``poly`` (CCW local polygon) between z0 and z1.
    ``edges`` restricts to edge indices; ``blank_edges`` get a plain wall."""
    b = MeshBuilder()
    coords = ring_coords(poly)
    blank = set(blank_edges)
    sel = set(edges) if edges is not None else None
    for i, (p0, p1, L, t, n) in enumerate(edges_of(coords)):
        if sel is not None and i not in sel:
            continue
        if i in blank:
            b.box_from_to(p0 - n * fen.recess, p1 - n * fen.recess, n, fen.recess, z0, z1, mat(fen.pier), top=top_cap)
            continue
        facade_edge(b, p0, p1, n, z0, z1, fen, top_cap=top_cap)
    return b.build(name)


def tower_tier(name: str, poly: Polygon, z0: float, z1: float, fen: Fenestration, *, roof_material: str = "roof_dark",
               parapet_h: float = 0.9, parapet_t: float = 0.4, blank_edges: Iterable[int] = (), coping: bool = True,
               mass_role: str = "mass") -> list[bpy.types.Object]:
    """A fenestrated massing tier: inset solid core (LOD1 mass, tagged) + facade skin + roof + parapet."""
    objs = []
    core_inset = fen.recess + 0.02
    core = prism(f"{name}_mass", poly, z0, z1, mat(fen.pier), inset=core_inset, material_top=mat(roof_material), role=mass_role)
    objs.append(core)
    objs.append(facade_grid(f"{name}_skin", poly, z0, z1, fen, top_cap=True, blank_edges=blank_edges))
    if parapet_h > 0:
        outer = poly
        inner = offset_polygon(poly, -parapet_t)
        if not inner.is_empty:
            b = MeshBuilder()
            b.prism(ring_coords(outer), z1, z1 + parapet_h, mat(fen.pier), holes=[ring_coords(inner)] if isinstance(inner, Polygon) else [], cap_bottom=False)
            objs.append(b.build(f"{name}_parapet"))
    return objs


def cornice(name: str, poly: Polygon, z: float, profile: Sequence[tuple[float, float]], material, *, closed: bool = True,
            edges: Iterable[int] | None = None) -> bpy.types.Object:
    """Profiled band around ``poly`` at height z. ``profile`` = [(outward_offset, dz), ...] from bottom to top; the first and
    last points are joined back to the wall so the band is a closed solid. Vertex count is preserved per ring (mitred)."""
    b = MeshBuilder()
    coords = ring_coords(poly)
    if edges is None:
        rings = []
        prof = [(0.0, profile[0][1])] + list(profile) + [(0.0, profile[-1][1])]
        for off, dz in prof:
            r = offset_ring(coords, off)
            rings.append([(x, y, z + dz) for x, y in r])
        b.loft(rings, material, cap_top=False, cap_bottom=False)
        # close top and bottom between wall ring and first/last profile ring
        r0 = rings[0]; r1 = rings[1]; rt0 = rings[-2]; rt1 = rings[-1]
        n = len(coords)
        for i in range(n):
            j = (i + 1) % n
            b.quad(r0[i], r0[j], r1[j], r1[i], material)  # bottom face (faces down)
            b.quad(rt0[i], rt0[j], rt1[j], rt1[i], material)  # top face
    else:
        for ei, (p0, p1, L, t, nrm) in enumerate(edges_of(coords)):
            if ei not in set(edges):
                continue
            prof = [(0.0, profile[0][1])] + list(profile) + [(0.0, profile[-1][1])]
            rings = []
            for off, dz in prof:
                a = p0 + nrm * off; c = p1 + nrm * off
                rings.append([(a[0], a[1], z + dz), (c[0], c[1], z + dz)])
            for k in range(len(rings) - 1):
                a, c = rings[k], rings[k + 1]
                b.quad(a[0], a[1], c[1], c[0], material)
            # end caps
            for end in (0, 1):
                pts = [r[end] for r in rings]
                b.ngon_vertical(pts, material, flip=(end == 1))
    return b.build(name)


def band(name: str, poly: Polygon, z0: float, z1: float, proud: float, material, *, edges=None) -> bpy.types.Object:
    """Simple rectangular string course / belt course protruding ``proud`` from the wall between z0 and z1."""
    return cornice(name, poly, z0, [(proud, 0.0), (proud, z1 - z0)], material, edges=edges)


def loft(name: str, rings, material, **kw) -> bpy.types.Object:
    b = MeshBuilder(); b.loft(rings, material, **kw); return b.build(name)


def lathe(name: str, profile, segments: int, material, **kw) -> bpy.types.Object:
    b = MeshBuilder(); b.lathe(profile, segments, material, **kw); return b.build(name)


def column_profile(order: str, h: float, r: float) -> tuple[list[tuple[float, float]], float]:
    """Lathe profile (r, z) for a classical column of shaft radius r and total height h, plus the capital top z.
    Orders: doric (Greek, no base), tuscan, ionic, corinthian, composite; proportions after Vignola/Chitham (simplified)."""
    o = order.lower()
    prof: list[tuple[float, float]] = []
    z = 0.0
    if o != "doric":
        # attic base: plinth + torus + scotia + torus
        prof += [(1.35 * r, 0.0), (1.35 * r, 0.25 * r), (1.2 * r, 0.27 * r), (1.2 * r, 0.45 * r), (1.02 * r, 0.6 * r), (1.12 * r, 0.75 * r), (1.0 * r, 0.9 * r)]
        z = 0.9 * r
    else:
        prof += [(1.0 * r, 0.0)]
    cap_h = {"doric": 1.0 * r, "tuscan": 1.0 * r, "ionic": 1.3 * r, "corinthian": 2.3 * r, "composite": 2.3 * r}[o]
    shaft_top = h - cap_h
    # shaft with entasis: full radius to 1/3, tapering to 0.85 r at the neck
    prof += [(1.0 * r, z + (shaft_top - z) / 3), (0.94 * r, z + (shaft_top - z) * 0.7), (0.85 * r, shaft_top - 0.15 * r), (0.9 * r, shaft_top - 0.1 * r), (0.85 * r, shaft_top)]
    if o in ("doric", "tuscan"):
        prof += [(0.9 * r, shaft_top + 0.25 * r), (1.2 * r, shaft_top + 0.55 * r), (1.25 * r, shaft_top + 0.6 * r), (1.25 * r, shaft_top + cap_h)]
    elif o == "ionic":
        prof += [(0.95 * r, shaft_top + 0.3 * r), (1.15 * r, shaft_top + 0.6 * r), (1.15 * r, shaft_top + 0.8 * r), (1.3 * r, shaft_top + 0.9 * r), (1.3 * r, shaft_top + cap_h)]
    else:  # corinthian bell (acanthus simplified as a flared bell)
        prof += [(0.9 * r, shaft_top + 0.1 * r), (1.0 * r, shaft_top + 0.7 * r), (1.15 * r, shaft_top + 1.3 * r), (1.35 * r, shaft_top + 1.9 * r), (1.5 * r, shaft_top + 2.1 * r), (1.5 * r, shaft_top + cap_h)]
    return prof, h


def column(b: MeshBuilder, x: float, y: float, z0: float, h: float, r: float, material, *, order: str = "corinthian",
           segments: int = 20, fluted: bool = True, abacus: bool = True) -> None:
    """Classical column into builder ``b`` (shaft, base, capital as lathe; square abacus box on top)."""
    prof, top = column_profile(order, h, r)
    b.lathe(prof, segments if not fluted else max(segments, 24), material, origin=(x, y, z0), smooth=True, cap=True)
    if abacus:
        aw = {"doric": 2.5 * r, "tuscan": 2.4 * r, "ionic": 2.6 * r, "corinthian": 2.9 * r, "composite": 2.9 * r}[order.lower()]
        b.box((x, y, z0 + top + 0.12 * r), (aw, aw, 0.24 * r), material)


def pilaster(b: MeshBuilder, p0, p1, normal, z0, z1, depth, material, *, cap_h: float = 0.5) -> None:
    """Flat pilaster on a wall segment with a simple capital block."""
    b.box_from_to(p0, p1, normal, depth, z0, z1 - cap_h, material, top=False)
    p0 = np.asarray(p0); p1 = np.asarray(p1); t = (p1 - p0) / np.linalg.norm(p1 - p0)
    b.box_from_to(p0 - t * 0.12, p1 + t * 0.12, normal, depth + 0.12, z1 - cap_h, z1, material)


def colonnade(b: MeshBuilder, p0, p1, normal, z0: float, h: float, r: float, count: int, material, *,
              order: str = "corinthian", stand_off: float = 0.0, segments: int = 20, end_margin: float | None = None,
              engaged: bool = False) -> list[tuple[float, float]]:
    """``count`` columns of height ``h`` and shaft radius ``r`` evenly spaced along the wall segment p0->p1, their axes
    ``stand_off`` metres out from that line along ``normal``. ``end_margin`` (default: half a bay) sets the distance from
    the ends to the first/last column axis; ``engaged`` pulls them back onto the wall (pilaster-like). Returns the axes."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); n = np.asarray(normal, dtype=np.float64)
    L = float(np.linalg.norm(p1 - p0))
    if count < 1 or L < 1e-6:
        return []
    t = (p1 - p0) / L
    margin = (L / (2 * count)) if end_margin is None else float(end_margin)
    span = L - 2 * margin
    axes = []
    off = n * (stand_off - (r if engaged else 0.0))
    for k in range(count):
        u = margin + (span * k / (count - 1) if count > 1 else span / 2)
        q = p0 + t * u + off
        column(b, float(q[0]), float(q[1]), z0, h, r, material, order=order, segments=segments)
        axes.append((float(q[0]), float(q[1])))
    return axes


def entablature(b: MeshBuilder, p0, p1, normal, z0: float, h: float, depth: float, material, *, overhang: float = 0.35) -> None:
    """Architrave / frieze / cornice band over a colonnade: a plain band with a projecting corona at the top."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); n = np.asarray(normal, dtype=np.float64)
    t = (p1 - p0) / float(np.linalg.norm(p1 - p0))
    a = p0 - t * overhang; c = p1 + t * overhang
    b.box_from_to(a, c, n, depth, z0, z0 + h * 0.72, material, top=False, bottom=True)
    b.box_from_to(a - t * overhang, c + t * overhang, n, depth + overhang, z0 + h * 0.72, z0 + h, material, top=True, bottom=True)


def gable_roof(b: MeshBuilder, ring: Sequence[tuple[float, float]], z_eave: float, rise: float, material, *,
               ridge_dir_deg: float = 0.0, overhang: float = 0.0, gable_material=None) -> None:
    """Pitched roof over a convex ring: the ridge runs along ``ridge_dir_deg`` (local math degrees) through the centroid and
    every eave vertex rises linearly with its distance from the ridge line, so the two slopes meet at the ridge."""
    pts = [tuple(map(float, p[:2])) for p in ring]
    c = np.asarray(pts, dtype=np.float64).mean(axis=0)
    d = np.array([math.cos(math.radians(ridge_dir_deg)), math.sin(math.radians(ridge_dir_deg))])
    nrm = np.array([-d[1], d[0]])
    if overhang:
        pts = offset_ring(pts, overhang)
    off = [float(np.dot(np.asarray(p) - c, nrm)) for p in pts]
    hmax = max(abs(o) for o in off) or 1.0
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        a, e = pts[i], pts[j]
        za = z_eave + rise * (1.0 - abs(off[i]) / hmax)
        ze = z_eave + rise * (1.0 - abs(off[j]) / hmax)
        ua = float(np.dot(np.asarray(a) - c, d)); ue = float(np.dot(np.asarray(e) - c, d))
        ra = tuple(c + d * ua); rb = tuple(c + d * ue)
        b.face([b.vert(a[0], a[1], z_eave), b.vert(e[0], e[1], z_eave), b.vert(e[0], e[1], ze), b.vert(a[0], a[1], za)],
               gable_material or material)                                     # fascia between eave and roof plane
        b.face([b.vert(a[0], a[1], za), b.vert(e[0], e[1], ze), b.vert(rb[0], rb[1], z_eave + rise),
                b.vert(ra[0], ra[1], z_eave + rise)], material)                # slope up to the ridge


def hip_roof(b: MeshBuilder, ring: Sequence[tuple[float, float]], z_eave: float, rise: float, material, *,
             inset: float | None = None, overhang: float = 0.0) -> list[tuple[float, float]]:
    """Hipped roof: the ring is offset inward by ``inset`` (default: half the short side) and lifted by ``rise``.
    Returns the ridge ring so a cupola or a deck can sit on it."""
    pts = [tuple(map(float, p[:2])) for p in ring]
    if overhang:
        pts = offset_ring(pts, overhang)
    if inset is None:
        w, d = Polygon(pts).bounds[2] - Polygon(pts).bounds[0], Polygon(pts).bounds[3] - Polygon(pts).bounds[1]
        inset = min(w, d) * 0.28
    top = offset_ring(pts, -inset)
    b.loft([[(x, y, z_eave) for x, y in pts], [(x, y, z_eave + rise) for x, y in top]], material, cap_bottom=False)
    return top


def pyramid_roof(b: MeshBuilder, ring: Sequence[tuple[float, float]], z0: float, h: float, material, *,
                 steps_n: int = 1) -> tuple[float, float]:
    """Pyramid (or stepped pyramid) over a ring; returns the apex xy. ``steps_n`` > 1 makes ``steps_n`` stacked frusta."""
    pts = [tuple(map(float, p[:2])) for p in ring]
    c = np.asarray(pts, dtype=np.float64).mean(axis=0)
    rings = []
    for k in range(steps_n + 1):
        s = 1.0 - k / steps_n
        rings.append([(float(c[0] + (x - c[0]) * s), float(c[1] + (y - c[1]) * s), z0 + h * k / steps_n) for x, y in pts])
    b.loft(rings[:-1] + [[(float(c[0]), float(c[1]), z0 + h)] * len(pts)], material, cap_bottom=False, cap_top=False)
    return float(c[0]), float(c[1])


def dome_profile(r: float, h: float, *, kind: str = "hemisphere", n: int = 12) -> list[tuple[float, float]]:
    """(radius, z) profile of a dome of springing radius ``r`` and height ``h``: ``hemisphere`` (elliptical),
    ``ogee`` (S-curved, as on Beaux-Arts cupolas) or ``cone``."""
    if kind == "cone":
        return [(r, 0.0), (0.0, h)]
    out = []
    for i in range(n + 1):
        f = i / n
        if kind == "ogee":
            rr = r * (1.0 - f ** 2) ** 0.5 * (1.0 - 0.28 * math.sin(math.pi * f))
            zz = h * (f ** 1.35)
        else:
            a = math.pi / 2 * f
            rr = r * math.cos(a); zz = h * math.sin(a)
        out.append((rr, zz))
    return out


def dome(b: MeshBuilder, x: float, y: float, z0: float, r: float, h: float, material, *, kind: str = "hemisphere",
         segments: int = 32, n: int = 12, finial_h: float = 0.0, finial_material=None) -> None:
    """Dome on a vertical axis, optionally topped by a ball-and-spike finial."""
    b.lathe(dome_profile(r, h, kind=kind, n=n), segments, material, origin=(x, y, z0), smooth=True, cap=False)
    if finial_h > 0:
        fm = finial_material or material
        rr = max(0.12, r * 0.09)
        b.lathe([(0.0, 0.0), (rr, rr * 0.9), (rr * 1.15, rr * 2.0), (rr * 0.6, rr * 3.0), (rr * 0.25, finial_h * 0.7),
                 (0.0, finial_h)], max(10, segments // 2), fm, origin=(x, y, z0 + h), smooth=True)


def balustrade(b: MeshBuilder, ring: Sequence[tuple[float, float]], z0: float, h: float, material, *,
               spacing: float = 0.75, baluster_r: float = 0.09, rail_t: float = 0.22, plinth_h: float = 0.18) -> None:
    """Stone balustrade around a ring: bottom plinth, turned balusters at ``spacing``, top rail."""
    pts = [tuple(map(float, p[:2])) for p in ring]
    wall_ring(b, Polygon(pts), z0, z0 + plinth_h, rail_t, material)
    wall_ring(b, Polygon(pts), z0 + h - rail_t, z0 + h, rail_t, material, cap_bottom=True)
    zb0, zb1 = z0 + plinth_h, z0 + h - rail_t
    prof = [(baluster_r * 0.8, 0.0), (baluster_r * 1.15, (zb1 - zb0) * 0.14), (baluster_r * 0.62, (zb1 - zb0) * 0.42),
            (baluster_r * 0.95, (zb1 - zb0) * 0.78), (baluster_r * 0.8, zb1 - zb0)]
    for p0, p1, L, t, nrm in edges_of(pts):
        k = max(1, int(round(L / spacing)))
        for i in range(k):
            q = p0 + t * (L * (i + 0.5) / k) - nrm * rail_t / 2
            b.lathe(prof, 8, material, origin=(float(q[0]), float(q[1]), zb0), smooth=True)


def barrel_vault(b: MeshBuilder, p0, p1, span: float, z_spring: float, rise: float, material, *, segments: int = 24,
                 thickness: float = 0.0, lunette_material=None, closed_ends: bool = True) -> None:
    """Elliptical barrel vault whose axis runs p0->p1 (2-D centre line) with the given ``span`` (full width) and ``rise``
    above the springing line. With ``thickness`` > 0 the soffit is doubled by an extrados shell (a real shell, not a plane).
    ``closed_ends`` fills the two end lunettes with ``lunette_material``."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64)
    L = float(np.linalg.norm(p1 - p0))
    t = (p1 - p0) / L
    nrm = np.array([t[1], -t[0]])
    a = span / 2

    def arc(off: float, r_extra: float):
        pts = []
        for i in range(segments + 1):
            th = math.pi * i / segments
            u = (a + r_extra) * math.cos(th); z = z_spring + (rise + r_extra) * math.sin(th)
            q = p0 + t * off + nrm * u
            pts.append((float(q[0]), float(q[1]), float(z)))
        return pts
    inner = [arc(0.0, 0.0), arc(L, 0.0)]
    b.loft(inner, material, cap_top=False, cap_bottom=False, smooth=True, closed=False)
    if thickness > 0:
        outer = [arc(0.0, thickness), arc(L, thickness)]
        b.loft(outer, material, cap_top=False, cap_bottom=False, smooth=True, closed=False)
        for k in (0, 1):                                     # close the shell along both edges of the barrel
            for i in range(segments):
                b.quad(inner[k][i], inner[k][i + 1], outer[k][i + 1], outer[k][i], material)
    if closed_ends:
        for k, ring in enumerate(inner):
            b.ngon_vertical(ring + [(ring[-1][0], ring[-1][1], z_spring), (ring[0][0], ring[0][1], z_spring)],
                            lunette_material or material, flip=(k == 1))


def clock_face(b: MeshBuilder, cx: float, cy: float, z: float, normal, r: float, face_material, hand_material, *,
               bezel_material=None, hours: int = 12, hour_angle_deg: float = 300.0, minute_angle_deg: float = 60.0,
               depth: float = 0.12) -> None:
    """Flat clock dial facing ``normal``: bezel ring, dial, hour ticks and two hands at the given angles (clockwise from 12)."""
    n = np.asarray(normal, dtype=np.float64)[:2]
    n = n / float(np.linalg.norm(n))
    t = np.array([-n[1], n[0]])                              # in-plane horizontal axis
    bez = bezel_material or hand_material

    def P(u, v, d=0.0):
        return (cx + t[0] * u + n[0] * d, cy + t[1] * u + n[1] * d, z + v)
    seg = 36
    ring_out = [P(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), depth) for i in range(seg)]
    ring_in = [P(r * 0.9 * math.cos(2 * math.pi * i / seg), r * 0.9 * math.sin(2 * math.pi * i / seg), depth) for i in range(seg)]
    dial = [P(r * 0.9 * math.cos(2 * math.pi * i / seg), r * 0.9 * math.sin(2 * math.pi * i / seg), depth * 0.45) for i in range(seg)]
    b.ngon_vertical(dial, face_material)
    for i in range(seg):
        j = (i + 1) % seg
        b.quad(ring_in[i], ring_out[i], ring_out[j], ring_in[j], bez)
        b.quad(dial[i], dial[j], ring_in[j], ring_in[i], bez)
    for k in range(hours):
        a = math.pi / 2 - 2 * math.pi * k / hours
        u0, v0 = r * 0.78 * math.cos(a), r * 0.78 * math.sin(a)
        u1, v1 = r * 0.88 * math.cos(a), r * 0.88 * math.sin(a)
        w = r * 0.035
        b.quad(P(u0 - w, v0, depth * 0.5), P(u1 - w, v1, depth * 0.5), P(u1 + w, v1, depth * 0.5), P(u0 + w, v0, depth * 0.5), hand_material)
    for ang, length, w in ((hour_angle_deg, r * 0.52, r * 0.055), (minute_angle_deg, r * 0.82, r * 0.038)):
        a = math.pi / 2 - math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        b.quad(P(-uy * w, ux * w, depth * 0.6), P(ux * length - uy * w, uy * length + ux * w, depth * 0.6),
               P(ux * length + uy * w, uy * length - ux * w, depth * 0.6), P(uy * w, -ux * w, depth * 0.6), hand_material)


def pediment(b: MeshBuilder, p0, p1, normal, z0: float, rise: float, depth: float, material, *, tympanum=None,
             cornice_t: float = 0.35, overhang: float = 0.0) -> None:
    """Triangular pediment over the wall segment p0->p1 (outward normal): a raking-cornice wedge (convex hull, ``cornice_t``
    thick, ``depth`` deep, optional ``overhang`` beyond the ends) plus a recessed tympanum triangle."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); n = np.asarray(normal, dtype=np.float64)
    t = (p1 - p0) / np.linalg.norm(p1 - p0)
    a = p0 - t * overhang; c = p1 + t * overhang; mid = (p0 + p1) / 2
    tym = tympanum or material
    # tympanum: vertical triangle set back cornice_t from the front plane
    f0 = p0 + n * (depth - cornice_t); f1 = p1 + n * (depth - cornice_t); fm = mid + n * (depth - cornice_t)
    b.ngon_vertical([(f0[0], f0[1], z0), (f1[0], f1[1], z0), (fm[0], fm[1], z0 + rise)], tym)
    # raking cornice as two wedge solids (left and right slopes)
    for s0, s1, za, zc in ((a, mid, z0, z0 + rise), (mid, c, z0 + rise, z0)):
        pts = []
        for q, z in ((s0, za), (s1, zc)):
            for dn in (0.0, depth):
                pts.append((q[0] + n[0] * dn, q[1] + n[1] * dn, z))
                pts.append((q[0] + n[0] * dn, q[1] + n[1] * dn, z - cornice_t))
        b.hull(pts, material)
    # horizontal cornice along the base of the pediment
    pts = []
    for q in (a, c):
        for dn in (0.0, depth):
            pts.append((q[0] + n[0] * dn, q[1] + n[1] * dn, z0 - cornice_t)); pts.append((q[0] + n[0] * dn, q[1] + n[1] * dn, z0 - 2 * cornice_t))
    b.hull(pts, material)


def steps(b: MeshBuilder, p0, p1, normal, z_top: float, n_steps: int, riser: float, tread: float, material, *, z_bottom=None) -> None:
    """Stair flight descending *outward* from the wall segment p0->p1: top step at the wall, each next step ``tread`` further out."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); n = np.asarray(normal, dtype=np.float64)
    zb = z_bottom if z_bottom is not None else z_top - n_steps * riser
    for k in range(n_steps):
        zt = z_top - k * riser
        depth = (k + 1) * tread
        b.box_from_to(p0, p1, n, depth, zb, zt, material, top=True, bottom=False)


def flagpole(b: MeshBuilder, x: float, y: float, z0: float, h: float, *, flag: tuple[str, ...] = ("flag_red", "flag_white", "flag_blue"),
             flag_w: float = 1.5, flag_h: float = 1.0, radius: float = 0.06, angle_deg: float = 0.0) -> None:
    """Vertical flagpole with a rectangular flag (stripes as bands) — flags are static geometry."""
    b.lathe([(radius, 0), (radius * 0.7, h), (0.0, h + 0.15)], 8, mat("aluminium"), origin=(x, y, z0), smooth=True)
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    nband = len(flag)
    for i, mname in enumerate(flag):
        z1 = z0 + h - 0.25 - flag_h * i / nband
        z2 = z0 + h - 0.25 - flag_h * (i + 1) / nband
        b.quad((x, y, z2), (x + c * flag_w, y + s * flag_w, z2), (x + c * flag_w, y + s * flag_w, z1), (x, y, z1), mat(mname))
        b.quad((x, y, z1), (x + c * flag_w, y + s * flag_w, z1), (x + c * flag_w, y + s * flag_w, z2), (x, y, z2), mat(mname))


def arch_points(cx: float, z_spring: float, half_w: float, rise: float | None = None, n: int = 12, *, pointed: bool = False):
    """2-D (u, z) points of an arch head from the left springing to the right springing. Semicircular by default
    (``rise`` = vertical radius for a segmental/elliptical head); ``pointed=True`` gives a two-centred Gothic arch whose
    apex is ``rise`` above the springing line (equilateral when rise = sqrt(3) * half_w)."""
    pts = []
    if not pointed:
        r = half_w if rise is None else rise
        for i in range(n + 1):
            a = math.pi - math.pi * i / n
            pts.append((cx + half_w * math.cos(a), z_spring + r * math.sin(a)))
        return pts
    rise = rise if rise is not None else math.sqrt(3.0) * half_w
    c = (rise ** 2 - half_w ** 2) / (2 * half_w)      # centre offset of the left arc, right of cx
    R = half_w + c
    th_apex = math.atan2(rise, -c)                    # angle of the apex seen from the left arc centre
    m = max(2, n // 2)
    left = []
    for i in range(m + 1):
        th = math.pi + (th_apex - math.pi) * i / m
        left.append((cx + c + R * math.cos(th), z_spring + R * math.sin(th)))
    right = [(2 * cx - u, z) for u, z in reversed(left[:-1])]
    return left + right


def arched_opening(b: MeshBuilder, p0, p1, normal, z0: float, z_spring: float, rise: float | None, depth: float, material_wall,
                   material_glass, *, pointed: bool = False, n: int = 12, reveal: float | None = None) -> None:
    """A recessed arched window/door in a wall between p0 and p1 (the opening spans the full p0-p1 width): the glass sits
    ``depth`` behind the wall plane; reveals (jambs/intrados) are generated so the recess reads at grazing angles."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); nrm = np.asarray(normal, dtype=np.float64)
    L = float(np.linalg.norm(p1 - p0)); t = (p1 - p0) / L
    hw = L / 2
    head = arch_points(hw, z_spring, hw, rise, n, pointed=pointed)
    outline = [(0.0, z0)] + head + [(L, z0)]  # left bottom, around the head to right bottom
    back = -nrm * depth
    front3 = [(p0[0] + t[0] * u, p0[1] + t[1] * u, z) for u, z in outline]
    back3 = [(x + back[0], y + back[1], z) for x, y, z in front3]
    # glass at the back
    b.ngon_vertical(back3, material_glass)
    # reveals
    for i in range(len(outline) - 1):
        a, c = front3[i], front3[i + 1]; ab, cb = back3[i], back3[i + 1]
        b.quad(a, ab, cb, c, material_wall)


def window_punch(b: MeshBuilder, p0, p1, normal, z0: float, z1: float, depth: float, material_wall, material_glass, *, sill: float = 0.06) -> None:
    """Rectangular recessed window with jambs, head and sill between p0-p1 (full width) and z0-z1."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); nrm = np.asarray(normal, dtype=np.float64)
    back = -nrm * depth
    a0 = (p0[0] + back[0], p0[1] + back[1]); a1 = (p1[0] + back[0], p1[1] + back[1])
    b.quad((a0[0], a0[1], z0), (a1[0], a1[1], z0), (a1[0], a1[1], z1), (a0[0], a0[1], z1), material_glass)
    b.quad((p0[0], p0[1], z0), (a0[0], a0[1], z0), (a0[0], a0[1], z1), (p0[0], p0[1], z1), material_wall)   # left jamb
    b.quad((a1[0], a1[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (a1[0], a1[1], z1), material_wall)   # right jamb
    b.quad((p0[0], p0[1], z1), (a0[0], a0[1], z1), (a1[0], a1[1], z1), (p1[0], p1[1], z1), material_wall)   # head
    b.quad((p0[0], p0[1], z0), (p1[0], p1[1], z0), (a1[0], a1[1], z0), (a0[0], a0[1], z0), material_wall)   # sill
    if sill > 0:
        b.box_from_to(p0, p1, nrm, sill, z0 - 0.1, z0, material_wall)


def punched_wall(b: MeshBuilder, p0, p1, normal, z0: float, z1: float, floor_zs: Sequence[float], material_wall, material_glass, *,
                 bays: int, window_w: float, window_h: float, sill_h: float, depth: float = 0.4, arched_top: bool = False,
                 margin: float | None = None) -> None:
    """Solid masonry wall p0->p1 with a grid of punched windows (bays x floors). The wall itself is built as the set of
    solid panels around the openings (so the openings are real holes through a ``depth`` thick skin)."""
    p0 = np.asarray(p0, dtype=np.float64); p1 = np.asarray(p1, dtype=np.float64); nrm = np.asarray(normal, dtype=np.float64)
    L = float(np.linalg.norm(p1 - p0)); t = (p1 - p0) / L
    back = -nrm * depth
    module = L / bays
    margin = (module - window_w) / 2 if margin is None else margin
    xs = []  # (u0, u1) of each window
    for k in range(bays):
        c = module * (k + 0.5)
        xs.append((c - window_w / 2, c + window_w / 2))
    # vertical solid strips between windows (full height)
    strips = [(0.0, xs[0][0])] + [(xs[k][1], xs[k + 1][0]) for k in range(bays - 1)] + [(xs[-1][1], L)]
    for u0, u1 in strips:
        a = p0 + t * u0 + back; c = p0 + t * u1 + back
        b.box_from_to(a, c, nrm, depth, z0, z1, material_wall, top=False, bottom=False)
    # horizontal solid bands between windows within each bay column
    for (u0, u1) in xs:
        a = p0 + t * u0 + back; c = p0 + t * u1 + back
        zprev = z0
        for zf in list(floor_zs):
            wz0 = zf + sill_h; wz1 = min(zf + sill_h + window_h, z1)
            if wz0 >= z1:
                break
            if wz0 > zprev:
                b.box_from_to(a, c, nrm, depth, zprev, wz0, material_wall, top=False, bottom=False)
            if arched_top:
                arched_opening(b, p0 + t * u0, p0 + t * u1, nrm, wz0, wz1 - window_w / 2, None, depth, material_wall, material_glass, n=8)
            else:
                window_punch(b, p0 + t * u0, p0 + t * u1, nrm, wz0, wz1, depth, material_wall, material_glass, sill=0.0)
            zprev = wz1
        if zprev < z1:
            b.box_from_to(a, c, nrm, depth, zprev, z1, material_wall, top=False, bottom=False)


# =============================================================================================== verification helpers
def all_mesh_objects(objects: Iterable[bpy.types.Object]) -> list[bpy.types.Object]:
    return [o for o in objects if o.type == "MESH"]


def tri_count(objects: Iterable[bpy.types.Object]) -> int:
    n = 0
    for o in all_mesh_objects(objects):
        n += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return n


def object_bounds(objects: Iterable[bpy.types.Object]) -> tuple[np.ndarray, np.ndarray]:
    lo = np.array([math.inf] * 3); hi = np.array([-math.inf] * 3)
    for o in all_mesh_objects(objects):
        if not o.data.vertices:
            continue
        co = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        if o.matrix_world != Matrix.Identity(4):
            co = np.asarray([o.matrix_world @ Vector(p) for p in co])
        lo = np.minimum(lo, co.min(axis=0)); hi = np.maximum(hi, co.max(axis=0))
    return lo, hi


def slice_polygon(objects: Iterable[bpy.types.Object], z: float) -> Polygon | MultiPolygon:
    """Horizontal cross-section of the given meshes at height z (local frame) as a (Multi)Polygon.
    Per object the cut segments are snapped to 0.1 mm, merged into rings and combined even-odd (so courtyards stay holes);
    objects are then unioned."""
    import functools
    result = Polygon()
    for o in all_mesh_objects(objects):
        me = o.data
        me.calc_loop_triangles()
        nv = len(me.vertices)
        if nv == 0 or len(me.loop_triangles) == 0:
            continue
        co = np.empty(nv * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        if o.matrix_world != Matrix.Identity(4):
            mw = np.array(o.matrix_world)
            co = (mw[:3, :3] @ co.T).T + mw[:3, 3]
        tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int64); me.loop_triangles.foreach_get("vertices", tri); tri = tri.reshape(-1, 3)
        P = co[tri]
        zmin = P[:, :, 2].min(axis=1); zmax = P[:, :, 2].max(axis=1)
        segs = []
        for a, b_, c in P[(zmin < z) & (zmax > z)]:
            pts = []
            for u, v in ((a, b_), (b_, c), (c, a)):
                if (u[2] - z) * (v[2] - z) < 0:
                    s = (z - u[2]) / (v[2] - u[2])
                    pts.append((round(float(u[0] + s * (v[0] - u[0])), 4), round(float(u[1] + s * (v[1] - u[1])), 4)))
            if len(pts) == 2 and pts[0] != pts[1]:
                segs.append(pts)
        if not segs:
            continue
        merged = shapely.ops.linemerge(shapely.ops.unary_union(MultiLineString(segs)))
        lines = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
        polys = []
        for ln in lines:
            cs = list(ln.coords)
            if len(cs) < 4:
                continue
            if cs[0] != cs[-1]:
                if math.dist(cs[0], cs[-1]) < 0.02:
                    cs.append(cs[0])
                else:
                    continue
            pg = Polygon(cs)
            if not pg.is_valid:
                pg = pg.buffer(0)
            if pg.area > 1e-6:
                polys.append(pg)
        if not polys:
            continue
        obj_poly = functools.reduce(lambda a, b: a.symmetric_difference(b), polys)
        result = result.union(obj_poly)
    return result


def iou(a, b) -> float:
    if a.is_empty or b.is_empty:
        return 0.0
    inter = a.intersection(b).area
    uni = a.union(b).area
    return inter / uni if uni > 0 else 0.0


def footprint_iou(objects: Iterable[bpy.types.Object], real_local: Polygon | MultiPolygon, *, z_cut: float = 1.5) -> tuple[float, Polygon]:
    """IoU between the model cross-section at z_cut (only objects tagged role='base') and the real footprint (local)."""
    base = [o for o in all_mesh_objects(objects) if o.get("nycsim_role") == "base"]
    if not base:
        raise FidelityError("no objects tagged role='base' — build the ground-floor volume with plinth()/prism(role='base')")
    sec = slice_polygon(base, z_cut)
    return iou(sec, real_local), sec


def _bake_transforms(objects: Iterable[bpy.types.Object]) -> None:
    for o in all_mesh_objects(objects):
        if o.matrix_world != Matrix.Identity(4):
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix.Identity(4)


def _rotate_meshes(objects: Iterable[bpy.types.Object], angle_deg: float) -> None:
    R = Matrix.Rotation(math.radians(angle_deg), 4, "Z")
    for o in all_mesh_objects(objects):
        o.data.transform(R)
        o.data.update()


def join_copies(objects: Iterable[bpy.types.Object], name: str) -> bpy.types.Object:
    """One new mesh object containing copies of all faces of ``objects`` (materials preserved)."""
    bm = bmesh.new()
    mats: list[bpy.types.Material] = []
    mat_index: dict[str, int] = {}
    for o in all_mesh_objects(objects):
        me = o.data
        remap = []
        for m in me.materials:
            if m is None:
                remap.append(0); continue
            if m.name not in mat_index:
                mat_index[m.name] = len(mats); mats.append(m)
            remap.append(mat_index[m.name])
        tmp = bmesh.new(); tmp.from_mesh(me)
        if o.matrix_world != Matrix.Identity(4):
            bmesh.ops.transform(tmp, matrix=o.matrix_world, verts=tmp.verts)
        for f in tmp.faces:
            f.material_index = remap[f.material_index] if remap else 0
        tmp_me = bpy.data.meshes.new("_tmp_join"); tmp.to_mesh(tmp_me); tmp.free()
        bm.from_mesh(tmp_me)
        bpy.data.meshes.remove(tmp_me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    me.update()
    ob = bpy.data.objects.new(name, me)
    nb.link(ob)
    return ob


def decimate_to(ob: bpy.types.Object, max_tris: int) -> bpy.types.Object:
    """Collapse-decimate ``ob`` in place until its triangle count is <= max_tris (evaluated via depsgraph, no operators)."""
    cur = tri_count([ob])
    if cur <= max_tris:
        return ob
    ratio = max(0.02, max_tris / cur * 0.9)
    for _ in range(6):
        mod = ob.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"; mod.ratio = ratio; mod.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        new_me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=dg)
        for m in ob.data.materials:
            new_me.materials.append(m)
        ob.modifiers.remove(mod)
        old = ob.data; ob.data = new_me; bpy.data.meshes.remove(old)
        cur = tri_count([ob])
        if cur <= max_tris:
            break
        ratio *= 0.6
    if cur > max_tris:
        raise FidelityError(f"could not decimate {ob.name} to {max_tris} tris (at {cur})")
    return ob


def make_lod1(objects: Sequence[bpy.types.Object], landmark_id: str, *, lod1_objects: Sequence[bpy.types.Object] | None = None,
              max_ratio: float = LOD1_MAX_RATIO) -> bpy.types.Object:
    """``<id>_LOD1``: joined copies of ``lod1_objects`` (default: objects tagged base/mass), decimated if still over budget."""
    lod0 = tri_count(objects)
    src = list(lod1_objects) if lod1_objects else [o for o in all_mesh_objects(objects) if o.get("nycsim_role") in ("base", "mass")]
    if not src:
        src = list(all_mesh_objects(objects))
    ob = join_copies(src, f"{landmark_id}_LOD1")
    budget = int(lod0 * max_ratio * 0.95)
    decimate_to(ob, max(budget, 12))
    box_uv(ob.data)                       # decimation scrambles the inherited UVs; re-project in metres
    ob["nycsim_role"] = "lod1"
    return ob


# =============================================================================================== scene / finish
def reset() -> None:
    """Fresh empty scene (metres)."""
    nb.reset_scene()
    _MATS.clear()


def script_name() -> str:
    return os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "interactive"


def _record_manifest(landmark_id: str, glb: Path, bins: Sequence[int], extra: dict) -> None:
    try:
        import fcntl
        from nycsim_pipeline import manifest as mf
        lock = mf.MANIFEST / ".processed.lock"
        with open(lock, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            mf.record_processed(f"landmark_glb:{landmark_id}", glb, stage="landmarks", sources=["building_footprints"],
                                rows=None, schema="blender_out/landmarks/<id>.glb (DATA_CONTRACTS §13)", extra={"bins": list(map(int, bins)), **extra})
            fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception as e:  # manifest is bookkeeping; never fail the build for it, but say so
        log.warning("manifest.record_processed failed for %s: %s", landmark_id, e)


def finish(objects: Sequence[bpy.types.Object], landmark_id: str, bins: Sequence[int], frame: LocalFrame, *, height_m: float,
           name: str, fidelity_statement: str, real_footprint: Polygon | MultiPolygon | None = None, lp_number: str = "",
           height_source: str = "", footprint_source: str = "NYC Building Footprints (OTI, 5zhs-2jue) via candidate_footprints.parquet",
           notes: str = "", dimensions: dict | None = None, lod1_objects: Sequence[bpy.types.Object] | None = None,
           tri_budget: int = TRI_BUDGET_LOD0, iou_min: float = IOU_MIN, require_base: bool = True, extras: dict | None = None,
           material_slots: dict | None = None) -> dict:
    """Validate, build LOD1, rotate to NYC_TM axes, export the .glb and write the catalog entry. Returns the catalog entry.

    ``real_footprint``: union of the real footprint(s) in *local* coordinates (default: the registered BINs' footprints).
    ``height_m``: architectural height (tip) the model must reach within 1 %.
    """
    objects = [o for o in objects if o is not None]
    meshes = all_mesh_objects(objects)
    if not meshes:
        raise FidelityError("nothing to export")
    _bake_transforms(meshes)
    lod0 = tri_count(meshes)
    if lod0 > tri_budget:
        raise FidelityError(f"{landmark_id}: LOD0 has {lod0} tris > budget {tri_budget}")
    lo, hi = object_bounds(meshes)
    model_h = float(hi[2])
    if abs(model_h - height_m) > HEIGHT_TOL * height_m:
        raise FidelityError(f"{landmark_id}: model height {model_h:.2f} m differs from documented {height_m:.2f} m by > 1 %")
    # footprint IoU
    fp_iou = None
    if require_base:
        if real_footprint is None:
            fps = load_footprints(bins)
            real_footprint = shapely.ops.unary_union([frame.local_polygon(f.polygon) for f in fps])
        fp_iou, sec = footprint_iou(meshes, real_footprint)
        if fp_iou < iou_min:
            raise FidelityError(f"{landmark_id}: footprint IoU {fp_iou:.3f} < {iou_min} (section area {sec.area:.1f} vs real {real_footprint.area:.1f})")
    # LOD1
    lod1 = make_lod1(meshes, landmark_id, lod1_objects=lod1_objects)
    lod1_tris = tri_count([lod1])
    if lod1_tris > LOD1_MAX_RATIO * lod0:
        raise FidelityError(f"{landmark_id}: LOD1 {lod1_tris} tris > 20 % of LOD0 {lod0}")
    # rotate everything into NYC_TM-parallel axes
    all_objs = meshes + [lod1]
    _rotate_meshes(all_objs, frame.angle_deg)
    root = bpy.data.objects.new(landmark_id, None)
    nb.link(root)
    for o in meshes:
        o.parent = root
    lo_w, hi_w = object_bounds(meshes)
    glb = OUT_DIR / f"{landmark_id}.glb"
    ex = {
        "landmark_id": landmark_id, "name": name, "origin_tm": frame.origin_tm, "bins": [int(b) for b in bins],
        "heading_deg": round(frame.heading_deg, 3), "principal_axis_deg_from_east": round(frame.angle_deg, 3),
        "height_m": float(height_m), "fidelity_statement": fidelity_statement, "lp_number": lp_number,
        "frame": "model axes parallel to NYC_TM (x east, y north, z up before glTF Y-up conversion); origin_tm is the NYC_TM position of the model origin (ground); no rotation to apply on import",
        "tris_lod0": lod0, "tris_lod1": lod1_tris, "footprint_iou": None if fp_iou is None else round(fp_iou, 4),
        "bounds_local_m": {"min": [round(float(v), 3) for v in lo_w], "max": [round(float(v), 3) for v in hi_w]},
        "lod1_node": f"{landmark_id}_LOD1",
    }
    if material_slots:
        ex["material_slots"] = material_slots
    if extras:
        ex.update(extras)
    nb.export_glb(glb, objects=[root] + all_objs, extras=ex)
    entry = {
        "id": landmark_id, "name": name, "bins": [int(b) for b in bins], "lp_number": lp_number, "script": f"blender/landmarks/{landmark_id}.py",
        "footprint_source": footprint_source, "height_m": float(height_m), "height_source": height_source, "notes": notes,
        "fidelity_statement": fidelity_statement, "glb": str(glb.relative_to(REPO_ROOT)), "origin_tm": frame.origin_tm,
        "heading_deg": round(frame.heading_deg, 3), "tris_lod0": lod0, "tris_lod1": lod1_tris, "lod1_ratio": round(lod1_tris / lod0, 4),
        "footprint_iou": None if fp_iou is None else round(fp_iou, 4), "model_height_m": round(model_h, 3),
        "bounds_local_m": ex["bounds_local_m"], "dimensions": dimensions or {}, "renders": [], "material_slots": material_slots or {},
        "generator_script": script_name(), "git_commit": nb.git_commit(), "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "schema_version": nb.SCHEMA_VERSION,
        "materials": sorted({m.name for o in meshes for m in o.data.materials if m is not None}),
        "textures": {k: v for k, v in sorted(texture_status().items())},
    }
    nb.write_catalog_entry(CATALOG_DIR, entry)
    _record_manifest(landmark_id, glb, bins, {"tris_lod0": lod0, "tris_lod1": lod1_tris, "footprint_iou": entry["footprint_iou"]})
    log.info("%s: exported %s (%d tris LOD0, %d tris LOD1, IoU %s, height %.1f m)", landmark_id, glb, lod0, lod1_tris, entry["footprint_iou"], model_h)
    return entry


def _clear_verify_objects() -> None:
    for o in list(bpy.data.objects):
        if o.name.startswith("verify_"):
            bpy.data.objects.remove(o, do_unlink=True)


def render_check(landmark_id: str, presets: Sequence[dict] | None = None, *, objects: Sequence[bpy.types.Object] | None = None,
                 samples: int = 64, size: tuple[int, int] = (1280, 720), ground: bool = True, hide_lod1: bool = True,
                 sun_azimuth_deg: float | None = None, sun_elevation_deg: float = 38.0) -> list[Path]:
    """Verification stills. Preset keys: view (name), azimuth_deg (compass direction *from the model to the camera*),
    elevation_deg (camera elevation angle; use "street" for a 1.7 m eye at ``distance`` m), distance (m; default from bounds),
    fov_deg, target_z (m; default mid-height for aerial, 0.35*h for street), look_up_deg (street only).
    ``eye`` and ``target`` (absolute (x, y, z) in the exported frame) override the azimuth/distance placement — that is how
    interior views are aimed; ``ground=False`` or a preset ``no_ground`` drops the render ground plane for them."""
    if os.environ.get("NYCSIM_LANDMARK_NO_RENDER") == "1":
        log.info("%s: NYCSIM_LANDMARK_NO_RENDER=1 — export verified, stills skipped", landmark_id)
        return []
    env_size = os.environ.get("NYCSIM_RENDER_SIZE")
    if env_size:
        w, _, h = env_size.partition("x")
        size = (int(w), int(h))
    fast = os.environ.get("NYCSIM_RENDER_FAST") == "1"
    if fast:
        samples, size = 16, (size[0] // 2, size[1] // 2)
    objs = [o for o in (objects or bpy.data.objects) if o.type == "MESH" and not o.name.startswith("_render_")]
    lod1 = [o for o in objs if o.name.endswith("_LOD1")]
    if hide_lod1:
        for o in lod1:
            o.hide_render = True
    lo, hi = object_bounds([o for o in objs if o not in lod1])
    h = float(hi[2] - min(0.0, lo[2]))
    cx, cy = float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2)
    radius = float(max(hi[0] - lo[0], hi[1] - lo[1]) / 2)
    if presets is None:
        presets = [{"view": "street", "azimuth_deg": 205, "elevation_deg": "street"}, {"view": "aerial", "azimuth_deg": 215, "elevation_deg": 30}]
    out: list[Path] = []
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    ground_ob = None
    if ground:
        # A flat, untextured asphalt plane: it fills most of an aerial frame, and tiling a 1 K texture over kilometres
        # of it costs several times the whole building in Cycles while adding nothing to the verification.
        rgb, rough, metal, _, _, _ = PALETTE["asphalt"]
        gmat = nb.pbr_material("_render_ground", base_color=_srgb(*rgb), roughness=rough, metallic=metal)
        b = MeshBuilder()
        b.box((cx, cy, -0.05), (max(4000.0, radius * 20), max(4000.0, radius * 20), 0.1), gmat)
        ground_ob = b.build("_render_ground")
    for p in presets:
        _clear_verify_objects()
        view = p.get("view", "view")
        if ground_ob is not None:
            ground_ob.hide_render = bool(p.get("no_ground", False))
        az = math.radians(90.0 - float(p.get("azimuth_deg", 210.0)))  # compass -> math
        fov = float(p.get("fov_deg", 55.0))
        aspect = size[0] / size[1]
        if p.get("eye") is not None:
            eye = tuple(float(v) for v in p["eye"])
            target = tuple(float(v) for v in p.get("target", (cx, cy, h * 0.5)))
            fov = float(p.get("fov_deg", 60.0))
        elif p.get("elevation_deg") == "street":
            fov = float(p.get("fov_deg", 60.0))
            d = float(p.get("distance", 2.2 * radius + 45.0))
            eye = (cx + d * math.cos(az), cy + d * math.sin(az), float(p.get("eye_z", 1.7)))
            tz = float(p.get("target_z", min(h * 0.3, d * math.tan(math.radians(float(p.get("look_up_deg", 16.0)))))))
            target = (cx, cy, tz)
        else:
            el = math.radians(float(p.get("elevation_deg", 30.0)))
            vfov = 2 * math.atan(math.tan(math.radians(fov) / 2) / aspect)   # Blender's FOV is the horizontal one for landscape frames
            need_v = (h * math.cos(el) + 2 * radius * math.sin(el)) / (2 * math.tan(vfov / 2))
            need_h = (2 * radius) / (2 * math.tan(math.radians(fov) / 2))
            d = float(p.get("distance", max(need_v, need_h) * 1.15 + radius))
            eye = (cx + d * math.cos(el) * math.cos(az), cy + d * math.cos(el) * math.sin(az), float(p.get("target_z", h * 0.5)) + d * math.sin(el))
            target = (cx, cy, float(p.get("target_z", h * 0.5)))
        path = VERIFY_DIR / f"{landmark_id}_{view}.png"
        # nycsim_bpy.quick_render's sun_azimuth_deg is the direction the light travels *towards* (shadow direction), so the
        # sun stands at azimuth+180. We want the sun ~25 deg to the side of the camera direction: param = camera_az + 25 - 180.
        sun_from = float(p.get("sun_azimuth_deg", sun_azimuth_deg if sun_azimuth_deg is not None else (float(p.get("azimuth_deg", 210.0)) + 25.0)))
        sun_az = (sun_from + 180.0) % 360.0
        sc = bpy.context.scene
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.exposure = float(p.get("exposure", -0.6))
        t0 = time.time()
        nb.quick_render(path, camera_location=eye, camera_target=target, fov_deg=fov, size=size, samples=samples,
                        sun_azimuth_deg=sun_az, sun_elevation_deg=float(p.get("sun_elevation_deg", sun_elevation_deg)))
        log.info("render %s in %.0f s", path.name, time.time() - t0)
        out.append(path)
    _clear_verify_objects()
    g = bpy.data.objects.get("_render_ground")
    if g is not None:
        bpy.data.objects.remove(g, do_unlink=True)
    for o in lod1:
        o.hide_render = False
    # append render paths to the catalog entry if it exists
    cat = CATALOG_DIR / f"{landmark_id}.json"
    if cat.exists():
        try:
            e = json.loads(cat.read_text())
            e["renders"] = sorted({*(e.get("renders") or []), *[str(x.relative_to(REPO_ROOT)) for x in out]})
            cat.write_text(json.dumps(e, indent=1, sort_keys=True))
        except Exception as ex:  # keep renders even if the catalog is unreadable
            log.warning("could not update catalog renders for %s: %s", landmark_id, ex)
    return out


def floor_lines(z0: float, floors: int, floor_h: float, *, first_h: float | None = None) -> list[float]:
    """Absolute z of each floor line from z0: [z0, z0+first_h, +floor_h, ...] (floors + 1 values)."""
    zs = [z0]
    z = z0 + (first_h if first_h is not None else floor_h)
    zs.append(z)
    for _ in range(floors - 1):
        z += floor_h; zs.append(z)
    return zs


__all__ = [n for n in dir() if not n.startswith("_")]
