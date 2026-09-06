"""Real-world placement for the B landmarks: bridge towers, anchorages, piers and portals.

Every bridge in this lane is placed from **measured support coordinates**, not from a building footprint (bridges have
no footprint in the OTI layer).  Two sources are used, in this order:

1. ``blender_out/landmarks/b_osm/structures.geojson`` (produced by ``b_osm_extract.py`` from the BBBike NYC OSM extract,
   ODbL, (c) OpenStreetMap contributors).  The relevant ways carry ``bridge:support=pylon|abutment|pier|lift_pier``;
   their polygon centroids, projected to NYC_TM with :func:`nycsim_pipeline.crs.lonlat_to_tm`, are the tower/anchorage
   positions used here.
2. The same centroids **recorded as constants** in each landmark script (``Support.xy``), so that a model can be rebuilt
   byte-identically without the OSM extract.  When both are available they are cross-checked: a disagreement larger than
   ``tol_m`` is logged and the recorded constant wins (the constants were verified against the published span lengths).

``data/processed/roads/segments.parquet`` — the other alignment source named in the brief — did **not** exist when this
module was written (the roads agent had produced only ``data/processed/roads/cache/``).  :func:`roads_available` and
:func:`roads_centreline` implement the consumer side so that a rebuild after the roads stage picks the deck centreline
up automatically; :func:`bridge_axis` records which source it actually used in ``SpanFit.source``.

Axis convention (shared with ``b_bridge_lib.Axis``): ``s`` runs along the bridge with s = 0 at the midpoint of the two
named span supports, ``t`` is positive to the left of +s, ``z`` is NAVD88 metres.  The landmark's local frame origin is
that same midpoint at z = 0.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

import b_common as bc
from b_bridge_lib import Axis

log = logging.getLogger("landmarks.b.align")

REPO = bc.REPO
OSM_STRUCTURES = bc.OUT / "b_osm" / "structures.geojson"
ROAD_SEGMENTS = REPO / "data" / "processed" / "roads" / "segments.parquet"

_OSM_WAYS: dict[int, dict] | None = None


# ------------------------------------------------------------------------------------------------ OSM support lookup


def _ways() -> dict[int, dict]:
    """OSM ways from the B extract, keyed by way id (loaded once)."""
    global _OSM_WAYS
    if _OSM_WAYS is None:
        out: dict[int, dict] = {}
        if OSM_STRUCTURES.exists():
            try:
                data = json.load(open(OSM_STRUCTURES))
            except (json.JSONDecodeError, OSError) as e:
                log.warning("cannot read %s (%s); using recorded support constants only", OSM_STRUCTURES, e)
                data = {"features": []}
            for f in data.get("features", []):
                p = f.get("properties", {})
                if p.get("osm_type") == "way":
                    out[int(p["osm_id"])] = f
        else:
            log.warning("%s missing; using recorded support constants only (run b_osm_extract.py to refresh)", OSM_STRUCTURES)
        _OSM_WAYS = out
    return _OSM_WAYS


def _ring_tm(feature: dict) -> np.ndarray:
    g = feature["geometry"]
    coords = g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"]
    lon = np.asarray([c[0] for c in coords], dtype=np.float64)
    lat = np.asarray([c[1] for c in coords], dtype=np.float64)
    x, y = bc.lonlat_to_tm(lon, lat)
    return np.column_stack([np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)])


def _polygon_centroid(p: np.ndarray) -> tuple[float, float]:
    """Area centroid of a closed ring (falls back to the vertex mean for degenerate rings)."""
    if len(p) >= 4 and abs(p[0, 0] - p[-1, 0]) < 1e-9 and abs(p[0, 1] - p[-1, 1]) < 1e-9:
        x, y = p[:, 0], p[:, 1]
        cross = x[:-1] * y[1:] - x[1:] * y[:-1]
        a2 = cross.sum()
        if abs(a2) > 1e-6:
            cx = ((x[:-1] + x[1:]) * cross).sum() / (3.0 * a2)
            cy = ((y[:-1] + y[1:]) * cross).sum() / (3.0 * a2)
            return float(cx), float(cy)
    return float(p[:, 0].mean()), float(p[:, 1].mean())


@dataclass
class Support:
    """One measured bridge support.

    ``name``      role in the structure ("tower_w", "anchorage_e", "pier2", ...)
    ``way``       OSM way id carrying ``bridge:support`` (0 when the support has no OSM way)
    ``xy``        NYC_TM (x, y) metres — the recorded centroid of that way (or a published/derived position)
    ``kind``      pylon | anchorage | pier | lift_pier | abutment | portal
    ``note``      provenance, printed into the model's verification report
    """
    name: str
    way: int
    xy: tuple[float, float]
    kind: str = "pylon"
    note: str = ""
    resolved: tuple[float, float] = field(init=False, default=(0.0, 0.0))
    delta_m: float = field(init=False, default=0.0)
    source: str = field(init=False, default="recorded")

    def resolve(self, tol_m: float = 8.0) -> tuple[float, float]:
        """Centroid from the OSM extract when it agrees with the recorded constant, else the constant."""
        self.resolved = tuple(float(v) for v in self.xy)
        f = _ways().get(int(self.way)) if self.way else None
        if f is None:
            self.source = "recorded"
            return self.resolved
        cx, cy = _polygon_centroid(_ring_tm(f))
        self.delta_m = math.hypot(cx - self.xy[0], cy - self.xy[1])
        if self.delta_m <= tol_m:
            self.resolved = (cx, cy)
            self.source = f"osm_way/{self.way}"
        else:
            self.source = "recorded"
            log.warning("support %s: OSM way %d centroid is %.1f m from the recorded constant (> %.1f m); "
                        "keeping the recorded value", self.name, self.way, self.delta_m, tol_m)
        return self.resolved


# ------------------------------------------------------------------------------------------------ roads consumer


def roads_available() -> bool:
    return ROAD_SEGMENTS.exists()


def roads_centreline(name_like: str, frame: bc.LocalFrame, max_offset_m: float = 120.0) -> list[tuple[float, float]] | None:
    """Deck centreline vertices (local frame) for the named bridge from ``data/processed/roads/segments.parquet``.

    Returns ``None`` when the parquet does not exist, has no ``name``/``geometry`` columns, or matches nothing.  Only
    vertices within ``max_offset_m`` of the frame origin's 4 km neighbourhood are returned, so that a same-named street
    elsewhere in the city cannot pollute the fit.
    """
    if not roads_available():
        return None
    try:
        import pyarrow.parquet as pq
        from shapely import wkb
        schema = pq.read_schema(ROAD_SEGMENTS)
        cols = [c for c in ("name", "geometry", "street_name") if c in schema.names]
        if "geometry" not in cols or not any(c in cols for c in ("name", "street_name")):
            log.info("segments.parquet has columns %s; no usable name/geometry pair", schema.names)
            return None
        namecol = "name" if "name" in cols else "street_name"
        table = pq.read_table(ROAD_SEGMENTS, columns=cols)
        pts: list[tuple[float, float]] = []
        needle = name_like.lower()
        for rec in table.to_pylist():
            nm = (rec.get(namecol) or "").lower()
            if needle not in nm:
                continue
            geom = rec["geometry"]
            g = wkb.loads(geom) if isinstance(geom, (bytes, bytearray)) else geom
            for x, y in list(g.coords) if g.geom_type == "LineString" else []:
                lx, ly, _ = frame.to_local(float(x), float(y))
                if abs(lx) < 4000.0 and abs(ly) < 4000.0:
                    pts.append((lx, ly))
        if len(pts) < 4:
            return None
        log.info("roads segments.parquet: %d centreline vertices for %r", len(pts), name_like)
        return pts
    except Exception as e:  # a partially written parquet must never break a landmark build
        log.warning("roads_centreline(%r) failed: %s", name_like, e)
        return None


# ------------------------------------------------------------------------------------------------ axis fitting


@dataclass
class SpanFit:
    """Result of placing a bridge: local frame, axis and the s coordinate of every support."""
    frame: bc.LocalFrame
    axis: Axis
    s: dict[str, float]
    t: dict[str, float]
    supports: dict[str, Support]
    osm_span_m: float
    published_span_m: float
    heading_deg: float
    source: str

    @property
    def span_error_pct(self) -> float:
        return 100.0 * (self.osm_span_m - self.published_span_m) / self.published_span_m

    def report(self) -> str:
        lines = [f"axis heading {self.heading_deg:.2f} deg (compass, +s), origin NYC_TM "
                 f"({self.frame.x0:.2f}, {self.frame.y0:.2f}); alignment source: {self.source}",
                 f"measured span between {self.span_pair[0]} and {self.span_pair[1]}: {self.osm_span_m:.2f} m vs published "
                 f"{self.published_span_m:.2f} m ({self.span_error_pct:+.2f} %); towers snapped symmetrically to the published value", ""]
        lines.append("| support | kind | NYC_TM x | NYC_TM y | s (m) | t (m) | source |")
        lines.append("|---|---|---|---|---|---|---|")
        for n, sp in self.supports.items():
            lines.append(f"| {n} | {sp.kind} | {sp.resolved[0]:.1f} | {sp.resolved[1]:.1f} | {self.s[n]:+.1f} | {self.t[n]:+.1f} | {sp.source} |")
        return "\n".join(lines)

    span_pair: tuple[str, str] = ("", "")


def bridge_axis(supports: Sequence[Support], span_pair: tuple[str, str], published_span_m: float, *,
                heading_from: tuple[str, str] | None = None, z0: float = 0.0, tol_m: float = 8.0,
                roads_name: str | None = None) -> SpanFit:
    """Place a bridge from its measured supports.

    ``span_pair`` names the two supports whose separation is the published main span; the axis runs from the first to the
    second, the frame origin is their midpoint and both are snapped symmetrically to exactly ``published_span_m`` so the
    model matches the published figure while staying centred on the real structure.  Every other support keeps its
    measured ``s``/``t``.  When ``roads_name`` is given and ``segments.parquet`` exists, the axis *direction* is refined
    by a least-squares fit through the real deck centreline (the origin always stays on the support midpoint).
    """
    by_name = {sp.name: sp for sp in supports}
    for n in span_pair:
        if n not in by_name:
            raise KeyError(f"bridge_axis: span support {n!r} not in {list(by_name)}")
    for sp in supports:
        sp.resolve(tol_m)
    a = np.asarray(by_name[span_pair[0]].resolved)
    b = np.asarray(by_name[span_pair[1]].resolved)
    measured = float(np.hypot(*(b - a)))
    if measured < 1.0:
        raise ValueError(f"bridge_axis: span supports {span_pair} coincide")
    mid = 0.5 * (a + b)
    if heading_from is not None:
        p = np.asarray(by_name[heading_from[0]].resolved)
        q = np.asarray(by_name[heading_from[1]].resolved)
        d = (q - p) / np.hypot(*(q - p))
    else:
        d = (b - a) / measured
    frame = bc.LocalFrame(float(mid[0]), float(mid[1]), z0, math.degrees(math.atan2(d[0], d[1])) % 360.0)
    source = "osm bridge:support ways + published span"
    if roads_name:
        pts = roads_centreline(roads_name, frame)
        if pts:
            arr = np.asarray(pts)
            c = arr.mean(axis=0)
            _, _, vt = np.linalg.svd(arr - c, full_matrices=False)
            dd = vt[0]
            if dd @ d < 0:
                dd = -dd
            if abs(math.degrees(math.acos(max(-1.0, min(1.0, float(dd @ d)))))) < 8.0:
                d = dd
                source = "roads segments.parquet centreline + osm supports + published span"
            else:
                log.warning("roads centreline for %r differs from the support axis by more than 8 deg; ignoring it", roads_name)
    axis = Axis(bc.Vector((0.0, 0.0, 0.0)), bc.Vector((float(d[0]), float(d[1]), 0.0)))
    s: dict[str, float] = {}
    t: dict[str, float] = {}
    for sp in supports:
        lx, ly, _ = frame.to_local(sp.resolved[0], sp.resolved[1])
        ss, tt = axis.st(lx, ly)
        s[sp.name] = ss
        t[sp.name] = tt
    half = published_span_m / 2.0
    s[span_pair[0]] = -half
    s[span_pair[1]] = +half
    t[span_pair[0]] = 0.0
    t[span_pair[1]] = 0.0
    fit = SpanFit(frame, axis, s, t, by_name, measured, published_span_m, frame.heading_deg, source)
    fit.span_pair = span_pair
    log.info("%s: measured %.2f m, published %.2f m (%+.2f %%), heading %.2f deg", span_pair, measured, published_span_m,
             fit.span_error_pct, frame.heading_deg)
    return fit


def point_axis(frame: bc.LocalFrame, heading_deg: float) -> Axis:
    """Axis through the frame origin with the given compass heading (for structures placed from one point)."""
    a = math.radians(heading_deg)
    return Axis(bc.Vector((0.0, 0.0, 0.0)), bc.Vector((math.sin(a), math.cos(a), 0.0)))


def frame_at(x: float, y: float, z0: float = 0.0, heading_deg: float = 0.0) -> bc.LocalFrame:
    return bc.LocalFrame(float(x), float(y), float(z0), float(heading_deg))


def osm_polygon_local(way_id: int, frame: bc.LocalFrame) -> list[tuple[float, float]] | None:
    """A real OSM way (building/fort/plaza outline) in the landmark's local frame, CCW, closing point removed."""
    f = _ways().get(int(way_id))
    if f is None:
        return None
    p = _ring_tm(f)
    ring = [(float(x - frame.x0), float(y - frame.y0)) for x, y in p]
    if len(ring) > 2 and math.dist(ring[0], ring[-1]) < 1e-6:
        ring.pop()
    if len(ring) < 3:
        return None
    area2 = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
    if area2 < 0:
        ring.reverse()
    return ring


def env_only(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


# ------------------------------------------------------------------------------------------------ build driver


def _decimate_to(objects: Sequence, target_tris: int) -> int:
    """Collapse-decimate a LOD1 object set until it fits ``target_tris``, biggest meshes first.

    The LOD1 generators already build coarser geometry (fewer stations, no railings, no markings, no suspenders);
    this is the backstop that guarantees the LOD1 contract when a model's mass is in geometry that does not
    coarsen — long viaduct decks, tunnel linings, hundreds of small props.
    """
    import bpy
    meshes = [o for o in objects if o is not None and o.type == "MESH"]
    total = bc.tri_count(meshes)
    if total <= target_tris or not meshes:
        return total
    ratio = max(0.03, target_tris / float(total))
    for ob in sorted(meshes, key=lambda o: len(o.data.polygons), reverse=True):
        if len(ob.data.polygons) < 24:
            continue
        mod = ob.modifiers.new("lod1_decimate", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = ob
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError:
            ob.modifiers.remove(mod)
    after = bc.tri_count(meshes)
    log.info("LOD1 decimate: %d -> %d triangles (target %d, ratio %.3f)", total, after, target_tris, ratio)
    return after


def run_landmark(landmark_id: str, title: str, build_fn, *, bins: Sequence[int] = (), sections=None,
                 renders: Sequence[dict] = (), budget_lod0: int = 250_000, budget_lod1: int = 60_000,
                 lod1_max_fraction: float = 0.40, argv: Sequence[str] | None = None) -> dict:
    """Build LOD0 + LOD1, export both, render the verification views and write the per-landmark report.

    ``build_fn(lod)`` returns ``(objects, extras)``; ``extras`` must carry the keys required by
    :func:`b_common.finish` (origin_tm, heading_deg, height_m, fidelity_statement).  LOD0 is built and exported
    first so that the LOD1 pass knows the triangle count it must come in under (``lod1_max_fraction`` of it, and
    ``budget_lod1`` absolutely); LOD0 is then rebuilt for the renders, which need the full-detail scene.

    ``renders`` entries are dicts with ``view``, ``cam`` and ``target`` (local-frame xyz), optionally ``fov_deg``,
    ``size``, ``samples`` overrides, ``sun_azimuth_deg``, ``sun_elevation_deg``, ``sun_strength``, ``exposure``,
    ``max_bounces`` and ``context`` (a sequence of ``(material, z, half_size[, (cx, cy)])`` ground/water planes).
    """
    args = bc.cli_args(argv)
    lods: dict[str, dict] = {}
    bc.new_scene()
    objs0, extras0 = build_fn(0)
    lods["lod0"] = bc.finish(objs0, landmark_id, bins, extras0, lod=0, budget_tris=budget_lod0)
    if not args["lod0_only"]:
        bc.new_scene()
        objs1, extras1 = build_fn(1)
        target = min(budget_lod1, int(lods["lod0"]["triangles"] * lod1_max_fraction))
        _decimate_to(objs1, target)
        lods["lod1"] = bc.finish(objs1, landmark_id, bins, extras1, lod=1, budget_tris=budget_lod1)
    shots: list[Path] = []
    if not args["no_render"]:
        bc.new_scene()
        objs0, _ = build_fn(0)
        for r in renders:
            if args["views"] and r["view"] not in args["views"]:
                continue
            shots.append(bc.render_check(landmark_id, r["view"], r["cam"], r["target"], fov_deg=r.get("fov_deg", 50.0),
                                         size=r.get("size", (960, 540)), samples=r.get("samples", args["samples"]),
                                         sun_azimuth_deg=r.get("sun_azimuth_deg", 220.0),
                                         sun_elevation_deg=r.get("sun_elevation_deg", 35.0),
                                         sun_strength=r.get("sun_strength", 2.0),
                                         exposure=r.get("exposure", -1.6),
                                         max_bounces=r.get("max_bounces", 6),
                                         context_planes=r.get("context", ())))
    if sections:
        bc.write_report(landmark_id, title, sections, lods, shots)
    return lods
