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

``data/processed/roads/segments.parquet`` — the other alignment source named in the brief — is consumed by
:func:`roads_centreline`: it selects every segment whose ``street_name`` contains the bridge's name, keeps the vertices
inside a 4 km box around the landmark frame, rejects the ones more than ``max_offset_m`` off the principal line (approach
ramps, service roads, the same-named circle at Hell Gate) and returns the rest.  :func:`bridge_axis` then refines the
axis *direction* by a least-squares fit through those vertices, but only when the fit is within 8 deg of the direction
the OSM supports give — the supports always keep the origin and the span.  ``SpanFit.source`` records which of the two
was actually used, and every landmark report prints it.

Axis convention (shared with ``b_bridge_lib.Axis``): ``s`` runs along the bridge with s = 0 at the midpoint of the two
named span supports, ``t`` is positive to the left of +s, ``z`` is NAVD88 metres.  The landmark's local frame origin is
that same midpoint at z = 0.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
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


def roads_centreline(name_like: str, frame: bc.LocalFrame, axis_origin: Sequence[float], axis_dir: Sequence[float],
                     *, half_length_m: float, max_offset_m: float = 45.0) -> list[tuple[float, float]] | None:
    """Deck centreline vertices (local frame) for the named bridge from ``data/processed/roads/segments.parquet``.

    The name alone is not enough: "BROOKLYN BRIDGE" in the LION data also names every approach ramp in City Hall
    Park and in Brooklyn, and a principal-axis fit through all of them misses the main span by 24 degrees.  So the
    supports supply a prior — ``axis_origin`` and the unit ``axis_dir`` they define — and only vertices within
    ``half_length_m`` along that axis and ``max_offset_m`` across it are kept.  With that window every bridge in
    this lane agrees with its OSM supports to better than 0.7 degrees (the Pulaski, whose OSM pier polygons draw
    the pier caps rather than the bascule bearings, is the single exception at 5.4 degrees and is rejected by
    :func:`bridge_axis`'s 8-degree guard only if it drifts further).

    Returns ``None`` when the parquet does not exist, carries no usable name/geometry pair, or matches nothing in
    that window.  Geometries are WKB and may carry a Z ordinate (the roads stage writes ``terrain_applied``
    3-D linestrings), so only the first two ordinates of each vertex are used.
    """
    if not roads_available():
        return None
    try:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
        from shapely import wkb

        schema = pq.read_schema(ROAD_SEGMENTS)
        if "geometry" not in schema.names:
            log.info("segments.parquet has columns %s; no geometry column", schema.names)
            return None
        namecol = next((c for c in ("street_name", "name", "name_norm") if c in schema.names), None)
        if namecol is None:
            log.info("segments.parquet has columns %s; no usable name column", schema.names)
            return None
        table = pq.read_table(ROAD_SEGMENTS, columns=[namecol, "geometry"])
        names = pc.cast(table.column(namecol).combine_chunks(), "string")
        mask = pc.fill_null(pc.match_substring(pc.utf8_lower(names), name_like.lower()), False)
        hit = table.filter(mask)
        if hit.num_rows == 0:
            log.info("segments.parquet: no segment whose %s contains %r", namecol, name_like)
            return None
        o = np.asarray(axis_origin, dtype=float)[:2]
        d = np.asarray(axis_dir, dtype=float)[:2]
        d = d / np.hypot(*d)
        n = np.array([-d[1], d[0]])
        pts: list[tuple[float, float]] = []
        seen = 0
        for geom in hit.column("geometry").to_pylist():
            if not isinstance(geom, (bytes, bytearray)):
                continue
            g = wkb.loads(bytes(geom))
            for part in (list(g.geoms) if g.geom_type.startswith("Multi") else [g]):
                if part.geom_type != "LineString":
                    continue
                for c in part.coords:
                    lx, ly, _ = frame.to_local(float(c[0]), float(c[1]))
                    seen += 1
                    v = np.array([lx, ly]) - o
                    if abs(v @ d) <= half_length_m and abs(v @ n) <= max_offset_m:
                        pts.append((lx, ly))
        if len(pts) < 4:
            log.info("segments.parquet: %r matched %d segments (%d vertices) but only %d inside the main-span "
                     "window (+-%.0f m along, +-%.0f m across)", name_like, hit.num_rows, seen, len(pts),
                     half_length_m, max_offset_m)
            return None
        log.info("roads segments.parquet: %d of %d vertices for %r inside the main-span window",
                 len(pts), seen, name_like)
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
        origin_local = np.asarray(frame.to_local(float(mid[0]), float(mid[1]))[:2])
        pts = roads_centreline(roads_name, frame, origin_local, d, half_length_m=published_span_m / 2.0 + 80.0)
        if pts:
            arr = np.asarray(pts)
            c = arr.mean(axis=0)
            _, _, vt = np.linalg.svd(arr - c, full_matrices=False)
            dd = vt[0]
            if dd @ d < 0:
                dd = -dd
            delta = abs(math.degrees(math.acos(max(-1.0, min(1.0, float(dd @ d))))))
            if delta < 8.0:
                d = dd
                source = (f"roads segments.parquet centreline ({len(pts)} vertices, {delta:.2f} deg from the "
                          f"OSM support axis) + osm supports + published span")
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


def axis_in_frame(frame: bc.LocalFrame, supports: Sequence[Support], span_pair: tuple[str, str],
                  published_span_m: float, *, tol_m: float = 8.0) -> SpanFit:
    """Place a *secondary* span inside an existing landmark frame (e.g. one of the RFK's three crossings).

    Unlike :func:`bridge_axis`, the local frame is given and is **not** moved: the returned axis has its origin at the
    midpoint of the two named supports *expressed in that frame*, and its direction runs from the first to the second.
    The two span supports are snapped symmetrically to ``published_span_m`` about that midpoint; every other support
    keeps its measured (s, t).  ``SpanFit.frame`` is the frame that was passed in, so ``report()`` prints the parent
    landmark's origin alongside this span's own measured-vs-published comparison.
    """
    by_name = {sp.name: sp for sp in supports}
    for n in span_pair:
        if n not in by_name:
            raise KeyError(f"axis_in_frame: span support {n!r} not in {list(by_name)}")
    for sp in supports:
        sp.resolve(tol_m)
    a = np.asarray(frame.to_local(*by_name[span_pair[0]].resolved)[:2])
    b = np.asarray(frame.to_local(*by_name[span_pair[1]].resolved)[:2])
    measured = float(np.hypot(*(b - a)))
    if measured < 1.0:
        raise ValueError(f"axis_in_frame: span supports {span_pair} coincide")
    mid = 0.5 * (a + b)
    d = (b - a) / measured
    axis = Axis(bc.Vector((float(mid[0]), float(mid[1]), 0.0)), bc.Vector((float(d[0]), float(d[1]), 0.0)))
    s: dict[str, float] = {}
    t: dict[str, float] = {}
    for sp in supports:
        lx, ly, _ = frame.to_local(sp.resolved[0], sp.resolved[1])
        ss, tt = axis.st(lx, ly)
        s[sp.name] = ss
        t[sp.name] = tt
    half = published_span_m / 2.0
    s[span_pair[0]], s[span_pair[1]] = -half, +half
    t[span_pair[0]] = t[span_pair[1]] = 0.0
    fit = SpanFit(frame, axis, s, t, by_name, measured, published_span_m, axis.heading_deg,
                  "osm bridge:support ways + published span (secondary span in the landmark frame)")
    fit.span_pair = span_pair
    log.info("%s (in-frame): measured %.2f m, published %.2f m (%+.2f %%), heading %.2f deg", span_pair, measured,
             published_span_m, fit.span_error_pct, axis.heading_deg)
    return fit


REFERENCE = REPO / "docs" / "verification" / "reference"


def reference_view(ref_id: str, frame: bc.LocalFrame, *, eye_m: float = 1.65, ground_z: float = 0.0,
                   target_z: float = 0.0) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Camera and target for one of the comparison agent's real photographic viewpoints, in ``frame`` coordinates.

    ``docs/verification/reference/<ref_id>/meta.json`` records the WGS84 position a photographer stood at and the
    WGS84 position of the subject.  Using those verbatim is what makes this model's render and the reference photo
    the *same* shot, so the comparison agent's sheets line up.  Returns ``None`` when the reference does not exist,
    so a build never depends on another agent's output being finished.

    ``ground_z`` is the NAVD88 elevation the photographer stood on and ``eye_m`` their eye height above it;
    ``target_z`` is the NAVD88 elevation to aim at on the subject.
    """
    meta = REFERENCE / ref_id / "meta.json"
    if not meta.is_file():
        log.info("reference viewpoint %s not on disk; using the hand-placed camera", ref_id)
        return None
    try:
        m = json.loads(meta.read_text())
        vp, sub = m["viewpoint"], m["subject"]
        cx, cy, _ = frame.from_lonlat(float(vp["lon"]), float(vp["lat"]))
        tx, ty, _ = frame.from_lonlat(float(sub["lon"]), float(sub["lat"]))
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning("reference viewpoint %s unusable (%s); using the hand-placed camera", ref_id, e)
        return None
    log.info("reference viewpoint %s: camera (%.1f, %.1f) local, subject (%.1f, %.1f), %.0f m away -- %s",
             ref_id, cx, cy, tx, ty, math.hypot(tx - cx, ty - cy), vp.get("note", ""))
    return (cx, cy, ground_z + eye_m), (tx, ty, target_z)


def reference_render(ref_id: str, frame: bc.LocalFrame, *, view: str | None = None, ground_z: float = 0.0,
                     target_z: float = 0.0, eye_m: float = 1.65, min_distance_m: float = 60.0,
                     aim: Sequence[float] | None = None, **kw) -> dict | None:
    """A ``renders`` entry placed on the comparison agent's real photographic viewpoint, or ``None`` if it is absent.

    ``run_landmark`` drops ``None`` entries, so a landmark can simply list this first and keep its own hand-placed
    views after it; the render is then the *same shot* as the reference photograph in
    ``docs/verification/reference/<ref_id>/``.

    The photographer's position is the reproducible half of a reference and is always used verbatim.  The recorded
    *subject* coordinate is only as good as whoever typed it: the Hell Gate reference names a point 591 m west of
    the arch, which aims the camera at empty water.  So a landmark may pass ``aim`` — a point in its own frame,
    normally the tower or facade the shot is of — and the camera is aimed there instead; the disagreement with the
    recorded subject is logged so a bad reference is visible rather than silent.  ``min_distance_m`` refuses a
    viewpoint that lands on top of the subject in this model's frame (the RFK reference does).
    """
    cam_t = reference_view(ref_id, frame, eye_m=eye_m, ground_z=ground_z, target_z=target_z)
    if cam_t is None:
        return None
    cam, target = cam_t
    if aim is not None:
        recorded = target
        target = (float(aim[0]), float(aim[1]), float(aim[2]) if len(aim) > 2 else target_z)
        off = math.dist(recorded[:2], target[:2])
        log.info("reference viewpoint %s: aiming at the model's own subject, %.0f m from the recorded subject point",
                 ref_id, off)
        if off > 120.0:
            log.warning("reference viewpoint %s records a subject %.0f m from this model's subject; the "
                        "photographer's position is still used verbatim, the aim is not", ref_id, off)
    if math.dist(cam[:2], target[:2]) < min_distance_m:
        # a recorded viewpoint that lands on top of the subject cannot produce evidence; skip rather than render it
        log.warning("reference viewpoint %s is only %.0f m from its subject in this model's frame (< %.0f m); "
                    "skipping it and keeping the hand-placed cameras", ref_id,
                    math.dist(cam[:2], target[:2]), min_distance_m)
        return None
    d = dict(view=view or ref_id, cam=cam, target=target, reference=ref_id)
    d.update(kw)
    return d


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
        wanted = [r for r in renders if r is not None
                  and not (args["views"] and r["view"] not in args["views"])]
        if args["max_views"] > 0:
            wanted = wanted[: args["max_views"]]
        scale = max(0.1, float(args["render_scale"]))
        for r in wanted:
            w, h = r.get("size", (960, 540))
            size = (max(160, int(w * scale) // 2 * 2), max(90, int(h * scale) // 2 * 2))
            shots.append(bc.render_check(landmark_id, r["view"], r["cam"], r["target"], fov_deg=r.get("fov_deg", 50.0),
                                         size=size, samples=r.get("samples", args["samples"]),
                                         sun_azimuth_deg=r.get("sun_azimuth_deg", 220.0),
                                         sun_elevation_deg=r.get("sun_elevation_deg", 35.0),
                                         sun_strength=r.get("sun_strength", 5.0),
                                         sky_strength=r.get("sky_strength", 0.22),
                                         exposure=r.get("exposure", -2.4),
                                         max_bounces=r.get("max_bounces", 4),
                                         context_planes=r.get("context", ())))
    if sections:
        bc.write_report(landmark_id, title, sections, lods, shots)
    if env_only("NYCSIM_LANDMARK_HARD_EXIT"):
        # bpy-as-a-module occasionally blocks forever in its own thread teardown after the scene has been written
        # (observed on b_central_park_walls_gates: 9 min wedged on a futex with every artefact already on disk).
        # The batch driver sets this so a teardown hang cannot stall the queue; everything above has been flushed.
        for stream in (sys.stdout, sys.stderr):
            stream.flush()
        os._exit(0)
    return lods
