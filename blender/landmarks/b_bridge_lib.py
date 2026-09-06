"""Parametric bridge generators for the B landmark scripts.

All bridges are modelled in an *axis frame* (s along the bridge, t across — positive to the left of +s — z up, NAVD88
metres) and mapped into the landmark's local frame by :class:`Axis`.  Alignments come from the OSM extract
(``b_osm_extract.py``: ODbL, © OpenStreetMap contributors); tower / pier positions come from the outline bulges or way
splits in that extract, snapped to the published span lengths quoted in each bridge script's docstring.

Generators: suspension bridge (towers of several architectures, catenary cables, every suspender, stays, stiffening
trusses, single/double decks, anchorages, approach viaducts), cantilever truss, steel arch, vertical-lift span, cable-
stayed, bascule and masonry arch viaducts, plus deck furniture (lanes, walkways, railings, lamps).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
from mathutils import Matrix, Vector

import b_common as bc
import nycsim_bpy as nb

log = logging.getLogger("landmarks.b.bridge")


# ============================================================================================ axis frame


@dataclass
class Axis:
    """Bridge axis in the landmark-local frame: ``origin`` (x, y) is s = 0, ``d`` the unit +s direction, ``n`` = left normal."""
    origin: Vector
    d: Vector

    def __post_init__(self) -> None:
        self.origin = Vector((self.origin[0], self.origin[1], 0.0))
        d = Vector((self.d[0], self.d[1], 0.0))
        if d.length < 1e-9:
            raise ValueError("Axis: zero direction")
        self.d = d.normalized()
        self.n = Vector((-self.d.y, self.d.x, 0.0))

    def p(self, s: float, t: float = 0.0, z: float = 0.0) -> Vector:
        return self.origin + self.d * s + self.n * t + Vector((0, 0, z))

    def st(self, x: float, y: float) -> tuple[float, float]:
        r = Vector((x, y, 0.0)) - self.origin
        return (r.dot(self.d), r.dot(self.n))

    @property
    def heading_deg(self) -> float:
        """Compass heading of +s."""
        return math.degrees(math.atan2(self.d.x, self.d.y)) % 360.0

    def shifted(self, ds: float) -> "Axis":
        return Axis(self.p(ds), self.d)

    def matrix(self, s: float, t: float = 0.0, z: float = 0.0, flip: bool = False) -> Matrix:
        """Rigid transform taking axis-frame (s, t, z) at the given point to local coordinates."""
        d = -self.d if flip else self.d
        n = Vector((-d.y, d.x, 0.0))
        m = Matrix(((d.x, n.x, 0.0, 0.0), (d.y, n.y, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
        m.translation = self.p(s, t, z)
        return m


def axis_from_points(frame: bc.LocalFrame, lonlat_a: tuple[float, float], lonlat_b: tuple[float, float]) -> Axis:
    """Axis through two WGS84 points (s = 0 at A, +s towards B)."""
    ax, ay, _ = frame.from_lonlat(*lonlat_a)
    bx, by, _ = frame.from_lonlat(*lonlat_b)
    return Axis(Vector((ax, ay, 0)), Vector((bx - ax, by - ay, 0)))


def axis_from_osm(frame: bc.LocalFrame, features: Sequence[dict], heading_hint_deg: float | None = None) -> tuple[Axis, np.ndarray]:
    """Principal axis of the given OSM features (local frame). Returns the axis (origin at the centroid) and the (s, t)
    coordinates of all vertices. ``heading_hint_deg`` orients +s (choose the direction closest to the hint)."""
    pts = []
    for f in features:
        g = f["geometry"]
        coords = g["coordinates"] if g["type"] == "LineString" else g["coordinates"][0]
        for lon, lat in coords:
            x, y, _ = frame.from_lonlat(lon, lat)
            pts.append((x, y))
    if len(pts) < 3:
        raise ValueError("axis_from_osm: not enough vertices")
    a = np.asarray(pts, dtype=np.float64)
    c = a.mean(axis=0)
    _, _, vt = np.linalg.svd(a - c, full_matrices=False)
    d = vt[0]
    if heading_hint_deg is not None:
        hint = np.array([math.sin(math.radians(heading_hint_deg)), math.cos(math.radians(heading_hint_deg))])
        if d @ hint < 0:
            d = -d
    axis = Axis(Vector((c[0], c[1], 0)), Vector((d[0], d[1], 0)))
    st = np.column_stack([(a - c) @ d, (a - c) @ np.array([-d[1], d[0]])])
    return axis, st


def outline_clusters(st: np.ndarray, bin_m: float = 25.0, min_n: int = 6) -> list[tuple[float, float, int]]:
    """Dense vertex clusters along s in a bridge outline (towers / piers are drawn with many vertices and are wider than
    the deck). Returns (s_centre, width, n) for bins with >= min_n vertices, merged when adjacent."""
    s = st[:, 0]
    t = st[:, 1]
    lo, hi = float(s.min()), float(s.max())
    edges = np.arange(lo, hi + bin_m, bin_m)
    raw = []
    for e0 in edges:
        m = (s >= e0) & (s < e0 + bin_m)
        if m.sum() >= min_n:
            raw.append((float(s[m].mean()), float(t[m].max() - t[m].min()), int(m.sum())))
    merged: list[tuple[float, float, int]] = []
    for sc, w, n in raw:
        if merged and abs(sc - merged[-1][0]) <= bin_m * 1.5:
            ps, pw, pn = merged[-1]
            merged[-1] = ((ps * pn + sc * n) / (pn + n), max(pw, w), pn + n)
        else:
            merged.append((sc, w, n))
    return merged


def towers_from_outline(st: np.ndarray, span_m: float, tol: float = 0.03, **kw) -> tuple[float, float] | None:
    """Pick the pair of outline clusters whose separation matches the published main span (within ``tol``), and snap
    them symmetrically to exactly ``span_m``. None if no pair matches."""
    cl = outline_clusters(st, **kw)
    best = None
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            sep = cl[j][0] - cl[i][0]
            err = abs(sep - span_m) / span_m
            if err <= tol and (best is None or err < best[0]):
                best = (err, cl[i][0], cl[j][0])
    if best is None:
        return None
    mid = 0.5 * (best[1] + best[2])
    log.info("towers_from_outline: clusters at %.1f/%.1f (sep %.1f, published %.1f, err %.2f%%)", best[1], best[2], best[2] - best[1], span_m, best[0] * 100)
    return (mid - span_m / 2, mid + span_m / 2)


# ============================================================================================ sweep


def sweep(name: str, axis: Axis, s_samples: Sequence[float], section: Sequence[tuple[float, float]], z_fn: Callable[[float], float],
          material: str, t_shift: float = 0.0, cap: bool = True, path_fn: Callable[[float], Vector] | None = None) -> bc.bpy.types.Object:
    """Extrude a closed 2-D cross-section (t, dz), CCW, along the axis; dz is added to z_fn(s). ``path_fn`` optionally
    overrides the centreline point for curved alignments (must return the local point for s)."""
    import bmesh
    if len(section) < 3:
        raise ValueError("sweep: section needs >= 3 points")
    bm = bmesh.new()
    rings = []
    for s in s_samples:
        z = z_fn(s)
        base = path_fn(s) if path_fn is not None else axis.p(s)
        ring = [bm.verts.new(base + axis.n * (t + t_shift) + Vector((0, 0, z + dz))) for t, dz in section]
        rings.append(ring)
    k = len(section)
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(k):
            j = (i + 1) % k
            bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
    if cap:
        tris = nb.triangulate_2d(section)
        for a, b_, c in tris:
            bm.faces.new((rings[0][a], rings[0][b_], rings[0][c]))
            bm.faces.new((rings[-1][c], rings[-1][b_], rings[-1][a]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return nb.bmesh_to_object(name, bm, materials=[bc.mat(material)])


def rect_section(width: float, height: float, t0: float = 0.0, z_top: float = 0.0) -> list[tuple[float, float]]:
    """Rectangle in (t, dz): top at z_top, bottom at z_top - height, centred on t0."""
    return [(t0 - width / 2, z_top - height), (t0 + width / 2, z_top - height), (t0 + width / 2, z_top), (t0 - width / 2, z_top)]


def sweep_var(name: str, axis: Axis, s_samples: Sequence[float], section_fn: Callable[[float], Sequence[tuple[float, float]]],
              z_fn: Callable[[float], float], material: str, cap: bool = True) -> bc.bpy.types.Object:
    """Like :func:`sweep` but the cross-section may change along s (same vertex count at every station).

    Used for decks whose walkway splits around a tower pier, tapering ramps and the tunnel tube transitions.
    """
    import bmesh
    bm = bmesh.new()
    rings = []
    k = None
    for s in s_samples:
        sec = list(section_fn(s))
        if k is None:
            k = len(sec)
            if k < 3:
                raise ValueError("sweep_var: section needs >= 3 points")
        elif len(sec) != k:
            raise ValueError(f"sweep_var({name}): section vertex count changed ({k} -> {len(sec)}) at s={s}")
        z = z_fn(s)
        rings.append([bm.verts.new(axis.p(s) + axis.n * t + Vector((0, 0, z + dz))) for t, dz in sec])
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for i in range(k):
            j = (i + 1) % k
            bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
    if cap:
        for a, b_, c in nb.triangulate_2d(list(section_fn(s_samples[0]))):
            bm.faces.new((rings[0][a], rings[0][b_], rings[0][c]))
        for a, b_, c in nb.triangulate_2d(list(section_fn(s_samples[-1]))):
            bm.faces.new((rings[-1][c], rings[-1][b_], rings[-1][a]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return nb.bmesh_to_object(name, bm, materials=[bc.mat(material)])


def samples(s0: float, s1: float, step: float) -> list[float]:
    n = max(int(math.ceil(abs(s1 - s0) / step)), 1)
    return [s0 + (s1 - s0) * i / n for i in range(n + 1)]


# ============================================================================================ deck elevation profiles


class DeckProfile:
    """Piecewise deck elevation: knots (s, z) with optional parabolic vertical curves between knots (``curve`` list of
    knot indices where the segment to the next knot is a symmetric sag/crest parabola through a given mid value)."""

    def __init__(self, knots: Sequence[tuple[float, float]], parabolic: dict[int, float] | None = None) -> None:
        self.knots = sorted(knots)
        self.parabolic = parabolic or {}  # segment index -> mid-segment z

    def z(self, s: float) -> float:
        k = self.knots
        if s <= k[0][0]:
            return k[0][1]
        if s >= k[-1][0]:
            return k[-1][1]
        for i in range(len(k) - 1):
            (s0, z0), (s1, z1) = k[i], k[i + 1]
            if s0 <= s <= s1:
                u = (s - s0) / (s1 - s0) if s1 > s0 else 0.0
                lin = z0 + (z1 - z0) * u
                if i in self.parabolic:
                    zm = self.parabolic[i]
                    bulge = zm - 0.5 * (z0 + z1)
                    return lin + bulge * 4 * u * (1 - u)
                return lin
        return k[-1][1]


# ============================================================================================ specs


@dataclass
class TowerSpec:
    kind: str                     # gothic | portal | lattice | artdeco | concrete | stone_arch_pier
    z_top: float                  # top of tower (NAVD88)
    z_saddle: float               # cable saddle elevation
    width_t: float                # overall across-bridge width at deck level
    depth_s: float                # along-bridge depth at deck level
    z_base: float = -2.0          # foundation top below water
    z_deck: float = 30.0          # deck elevation at tower (for arch openings / portal geometry)
    leg_w: float = 6.0            # steel leg width (t) at deck level
    leg_d: float = 6.0            # steel leg depth (s)
    leg_taper: float = 0.6        # top/base width ratio
    struts_z: Sequence[float] = ()  # portal strut elevations
    x_brace: bool = False
    arch_w: float = 10.3          # gothic: arch opening width
    arch_h: float = 35.7          # gothic: arch opening height above roadway
    arch_gap: float = 8.83        # gothic: |t| of each arch centre (half the pier-to-pier spacing)
    cornice_w: float = 1.5        # gothic: projection of the crown cornice course
    batter: float = 0.0           # gothic: half-width lost per metre of height (granite batter)
    pier_w: float = 43.0          # masonry pier (below deck) width t
    pier_d: float = 18.0          # masonry pier depth s
    material: str = "steel_gray"
    pier_material: str = "granite_gray"
    cable_t: Sequence[float] = ()  # cable plane offsets (for saddle blocks / leg placement)


@dataclass
class CableSpec:
    t_offsets: Sequence[float]    # cable plane offsets
    radius: float                 # main cable radius
    z_low_mid: float              # cable low point at mid main span
    suspender_spacing: float      # m along s
    suspender_radius: float = 0.03
    suspender_pairs: bool = False # two ropes per hanger (Verrazzano, GWB)
    stays_per_direction: int = 0  # diagonal stays fanning from each tower (Brooklyn: 25 per cable per direction)
    stay_reach_min: float = 18.0  # horizontal reach of the shortest stay (m from the tower centreline)
    stay_reach_max: float = 131.0  # horizontal reach of the longest stay
    stay_head_drop: float = 26.0  # the stay heads occupy this much of the tower below the saddle
    material: str = "steel_silver"
    suspender_material: str = "steel_silver"
    side_spans: bool = True       # suspenders in side spans


@dataclass
class DeckSpec:
    width: float
    thickness: float
    lanes: int
    lane_w: float = 3.3
    roadway_t: float = 0.0        # roadway centre offset
    roadway_w: float | None = None
    walkways: Sequence[tuple[float, float, float]] = ()   # (t_centre, width, dz above deck top)
    walkway_material: str = "sidewalk"
    truss_depth: float = 0.0
    truss_t: Sequence[float] = ()
    truss_above: bool = True      # truss above deck (Brooklyn) or below (deck truss)
    truss_panel: float = 6.0
    truss_material: str = "steel_gray"
    material: str = "asphalt"
    slab_material: str = "concrete_dark"
    lower_deck_dz: float = 0.0    # < 0 -> second deck this far below
    lower_lanes: int = 0
    lower_width: float | None = None
    tracks: Sequence[float] = ()  # railway track centre offsets (t) on this deck
    tracks_lower: Sequence[float] = ()
    railing: bool = True
    lamps_spacing: float = 0.0
    lamp_t: Sequence[float] = ()
    centre_yellow: bool = True


@dataclass
class AnchorageSpec:
    s_centre: float
    length_s: float
    width_t: float
    z_top: float
    z_base: float = 0.0
    material: str = "granite_gray"
    z_cable_entry: float | None = None
    slope: bool = True            # sloped rear face (Brooklyn style)


@dataclass
class ApproachSpec:
    s0: float
    s1: float
    z0: float
    z1: float
    kind: str = "viaduct"         # viaduct | masonry_arches | embankment | girder
    pier_spacing: float = 30.0
    width: float = 26.0
    material: str = "concrete"
    ground_z: float = 3.0
    arch_span: float = 12.0


# ============================================================================================ component builders


def build_tower(name: str, axis: Axis, s: float, spec: TowerSpec, lod: int = 0) -> list:
    """One tower at s. Styles: gothic (Brooklyn), portal (Manhattan/Whitestone/Throgs/RFK/Verrazzano), lattice (GWB,
    Williamsburg), artdeco (Whitestone), concrete (Kosciuszko)."""
    out = []
    M = axis.matrix(s)
    pier_top = spec.z_deck - 1.0
    # masonry / concrete pier below deck for every style (steel legs bear on masonry piers)
    if spec.kind in ("gothic", "stone_arch_pier"):
        pier_top = spec.z_deck - 0.5
    pier = bc.box(f"{name}_pier", (spec.pier_d, spec.pier_w, pier_top - spec.z_base), (0, 0, spec.z_base), spec.pier_material)
    bc.transform(pier, M)
    out.append(pier)
    if spec.kind == "gothic":
        # The masonry shaft is a single battered block pierced by two pointed arches; the profile is drawn in (t, z)
        # and extruded along s, so the arch soffits run the full depth of the tower (a real through-passage).
        z0 = spec.z_deck - 0.5   # below this the tower is the solid granite pier built above
        W = spec.width_t
        b = spec.batter
        w_top = W / 2 - b * (spec.z_top - spec.z_deck)
        cw = spec.cornice_w
        prof = [(-W / 2, z0), (W / 2, z0),                                   # base at the water line
                (W / 2, spec.z_deck), (w_top, spec.z_top - 4.0),             # battered shaft
                (w_top + cw, spec.z_top - 4.0), (w_top + cw, spec.z_top - 2.6),   # cornice course
                (w_top + cw * 0.45, spec.z_top - 2.6), (w_top + cw * 0.45, spec.z_top),
                (-(w_top + cw * 0.45), spec.z_top), (-(w_top + cw * 0.45), spec.z_top - 2.6),
                (-(w_top + cw), spec.z_top - 2.6), (-(w_top + cw), spec.z_top - 4.0),
                (-w_top, spec.z_top - 4.0), (-W / 2, spec.z_deck)]
        gap = spec.arch_gap
        holes = [bc.pointed_arch(spec.arch_w, spec.arch_h, -gap, spec.z_deck), bc.pointed_arch(spec.arch_w, spec.arch_h, gap, spec.z_deck)]
        body = bc.profile_extrude(f"{name}_body", prof, spec.depth_s, spec.material, holes=holes, plane="yz")
        bc.transform(body, M)
        out.append(body)
        # string course above the arch crowns, where the real towers step back
        zz = spec.z_deck + spec.arch_h + 3.2
        w_here = W / 2 - b * (zz - spec.z_deck)
        band = bc.box(f"{name}_band", (spec.depth_s + 1.0, 2 * w_here + 1.0, 1.0), (0, 0, zz), spec.material)
        bc.transform(band, M)
        out.append(band)
        # cable saddles on the tower top (one per cable plane)
        for t in spec.cable_t:
            sad = bc.box(f"{name}_saddle", (spec.depth_s * 0.5, 2.2, 2.0), (0, t, spec.z_saddle - 2.0), "steel_black")
            bc.transform(sad, M)
            out.append(sad)
    elif spec.kind in ("portal", "artdeco", "concrete"):
        legs = []
        for side in (-1, 1):
            t_leg = side * (spec.width_t / 2 - spec.leg_w / 2)
            wb, wt = spec.leg_w, spec.leg_w * spec.leg_taper
            db, dt = spec.leg_d, spec.leg_d * spec.leg_taper
            zb, zt = pier_top, spec.z_top
            # tapered box leg via 8 vertices
            verts = [(-db / 2, t_leg - wb / 2, zb), (db / 2, t_leg - wb / 2, zb), (db / 2, t_leg + wb / 2, zb), (-db / 2, t_leg + wb / 2, zb),
                     (-dt / 2, t_leg - wt / 2, zt), (dt / 2, t_leg - wt / 2, zt), (dt / 2, t_leg + wt / 2, zt), (-dt / 2, t_leg + wt / 2, zt)]
            faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
            leg = nb.mesh_object(f"{name}_leg{side}", verts, faces, materials=[bc.mat(spec.material)])
            bc.transform(leg, M)
            legs.append(leg)
        out += legs
        inner = spec.width_t - 2 * spec.leg_w
        for i, zz in enumerate(spec.struts_z):
            frac = (zz - pier_top) / max(spec.z_top - pier_top, 1e-6)
            w_here = spec.leg_w * (1 - frac) + spec.leg_w * spec.leg_taper * frac
            d_here = spec.leg_d * (1 - frac) + spec.leg_d * spec.leg_taper * frac
            span = spec.width_t - w_here
            depth = 2.2 if spec.kind == "artdeco" else 3.0
            strut = bc.box(f"{name}_strut{i}", (d_here * 0.9, span, depth if spec.kind != "artdeco" else 5.0), (0, 0, zz), spec.material, anchor="center")
            bc.transform(strut, M)
            out.append(strut)
            if spec.x_brace and i + 1 < len(spec.struts_z):
                z2 = spec.struts_z[i + 1]
                a = axis.p(s, -inner / 2, zz)
                b = axis.p(s, inner / 2, z2)
                out.append(bc.box_between(f"{name}_xa{i}", a, b, 1.0, d_here * 0.6, spec.material))
                out.append(bc.box_between(f"{name}_xb{i}", axis.p(s, inner / 2, zz), axis.p(s, -inner / 2, z2), 1.0, d_here * 0.6, spec.material))
        for t in spec.cable_t:
            sad = bc.box(f"{name}_saddle", (spec.leg_d * spec.leg_taper * 0.8, 2.0, 2.5), (0, t, spec.z_top), "steel_black")
            bc.transform(sad, M)
            out.append(sad)
    elif spec.kind == "lattice":
        # two lattice legs, each a tapered 4-chord lattice column, plus lattice portal struts
        for side in (-1, 1):
            t_leg = side * (spec.width_t / 2 - spec.leg_w / 2)
            col = bc.lattice_column(f"{name}_leg{side}", axis.p(s, t_leg, pier_top), axis.p(s, t_leg, spec.z_top), spec.leg_w, spec.leg_w * spec.leg_taper,
                                    spec.material, panels=max(int((spec.z_top - pier_top) / 12), 4), member=1.1 if lod == 0 else 1.6, x_brace=(lod == 0))
            out.append(col)
        for i, zz in enumerate(spec.struts_z):
            inner = spec.width_t - spec.leg_w
            if lod == 0 and spec.x_brace:
                out.append(bc.truss_girder(f"{name}_strut{i}", axis.p(s, -inner / 2, zz), axis.p(s, inner / 2, zz), 9.0, spec.leg_d * 0.7, 9.0, spec.material, chord=1.0, web=0.7))
            else:
                strut = bc.box(f"{name}_strut{i}", (spec.leg_d * 0.7, inner, 9.0), (0, 0, zz), spec.material, anchor="center")
                bc.transform(strut, M)
                out.append(strut)
        for t in spec.cable_t:
            sad = bc.box(f"{name}_saddle", (spec.leg_d * spec.leg_taper, 2.4, 3.0), (0, t, spec.z_top), "steel_black")
            bc.transform(sad, M)
            out.append(sad)
    else:
        raise ValueError(f"unknown tower kind {spec.kind}")
    return out


def cable_polyline(axis: Axis, t: float, s_anchor_a: float, z_anchor_a: float, s_tower_a: float, s_tower_b: float, z_saddle: float,
                   s_anchor_b: float, z_anchor_b: float, z_low_mid: float, step: float = 6.0) -> list[Vector]:
    """Main cable through anchorage A, tower A saddle, mid-span low point, tower B saddle, anchorage B (true catenaries;
    side spans share the main span's catenary parameter, i.e. the same horizontal tension)."""
    main = bc.catenary_points(s_tower_a, z_saddle, s_tower_b, z_saddle, z_saddle - z_low_mid, n=max(int((s_tower_b - s_tower_a) / step), 8))
    # catenary parameter a from the main span sag
    L = s_tower_b - s_tower_a
    sag = z_saddle - z_low_mid
    lo, hi = 1e-3, 1e7
    for _ in range(200):
        a = math.sqrt(lo * hi)
        if a * (math.cosh(L / (2 * a)) - 1) > sag:
            lo = a
        else:
            hi = a
    a = math.sqrt(lo * hi)

    def side(s0, z0, s1, z1):
        Ls = abs(s1 - s0)
        sag_side = a * (math.cosh(Ls / (2 * a)) - 1)
        pts = bc.catenary_points(min(s0, s1), z0 if s0 < s1 else z1, max(s0, s1), z1 if s0 < s1 else z0, max(sag_side, 0.05), n=max(int(Ls / step), 6))
        return pts

    pa = side(s_anchor_a, z_anchor_a, s_tower_a, z_saddle)
    pb = side(s_tower_b, z_saddle, s_anchor_b, z_anchor_b)
    pts = pa[:-1] + main + pb[1:]
    return [axis.p(sx, t, zx) for sx, zx in pts], pts


def build_suspension_cables(name: str, axis: Axis, cs: CableSpec, s_towers: tuple[float, float], z_saddle: float, anchors: tuple[AnchorageSpec, AnchorageSpec],
                            deck_z: Callable[[float], float], deck_hanger_dz: float, lod: int = 0, hanger_t_fn: Callable[[float], float] | None = None) -> list:
    """Cables + suspenders + stays for every cable plane. ``deck_hanger_dz`` is where hangers attach relative to deck_z."""
    out = []
    sa, sb = s_towers
    A, B = anchors
    za = A.z_cable_entry if A.z_cable_entry is not None else A.z_top - 1.0
    zb = B.z_cable_entry if B.z_cable_entry is not None else B.z_top - 1.0
    s_a_entry = A.s_centre + A.length_s / 2 if A.s_centre < sa else A.s_centre - A.length_s / 2
    s_b_entry = B.s_centre - B.length_s / 2 if B.s_centre > sb else B.s_centre + B.length_s / 2
    hang_parts = []
    stay_parts = []
    for t in cs.t_offsets:
        pts3d, pts2d = cable_polyline(axis, t, s_a_entry, za, sa, sb, z_saddle, s_b_entry, zb, cs.z_low_mid)
        out.append(bc.tube_along(f"{name}_cable_t{t:+.1f}", pts3d, cs.radius, cs.material, segments=10 if lod == 0 else 5))
        if lod >= 1:
            continue
        # suspenders (skip inside the towers / anchorages)
        s = s_a_entry + cs.suspender_spacing
        while s < s_b_entry:
            in_side = s < sa - 3 or s > sb + 3
            if (cs.side_spans or not in_side) and abs(s - sa) > 4 and abs(s - sb) > 4:
                zc = bc.catenary_z(pts2d, s)
                zd = deck_z(s) + deck_hanger_dz
                if zc - zd > 0.5:
                    th = hanger_t_fn(t) if hanger_t_fn else t
                    if cs.suspender_pairs:
                        for dt in (-0.25, 0.25):
                            hang_parts.append(bc.cylinder_between(f"{name}_h", axis.p(s, th + dt, zd), axis.p(s, t + dt, zc), cs.suspender_radius, cs.suspender_material, 4))
                    else:
                        hang_parts.append(bc.cylinder_between(f"{name}_h", axis.p(s, th, zd), axis.p(s, t, zc), cs.suspender_radius, cs.suspender_material, 4))
            s += cs.suspender_spacing
        # diagonal stays (Brooklyn): from below the saddle to deck points fanning out in both directions
        n_stay = cs.stays_per_direction
        for st_ in (sa, sb):
            for direction in (-1, 1):
                for i in range(n_stay):
                    u = i / max(n_stay - 1, 1)
                    reach = cs.stay_reach_min + u * (cs.stay_reach_max - cs.stay_reach_min)
                    s_deck = st_ + direction * reach
                    if s_deck < s_a_entry + 5 or s_deck > s_b_entry - 5:
                        continue
                    # the stay heads are anchored down the tower shaft: the longest stay leaves from the highest point
                    z_from = z_saddle - 2.5 - (1.0 - u) * cs.stay_head_drop
                    stay_parts.append(bc.cylinder_between(f"{name}_stay", axis.p(st_ + direction * 3.2, t, z_from),
                                                          axis.p(s_deck, t, deck_z(s_deck) + deck_hanger_dz),
                                                          cs.suspender_radius * 1.4, cs.suspender_material, 4))
    if hang_parts:
        # join in chunks to keep object counts sane
        for k in range(0, len(hang_parts), 400):
            out.append(bc.join(hang_parts[k:k + 400], f"{name}_suspenders_{k // 400}"))
    if stay_parts:
        out.append(bc.join(stay_parts, f"{name}_stays"))
    return out


def build_anchorage(name: str, axis: Axis, spec: AnchorageSpec, towards_s: float) -> list:
    """Masonry / concrete anchorage block. The cable-entry (front) face looks toward ``towards_s``; the rear is sloped."""
    M = axis.matrix(spec.s_centre, flip=towards_s < spec.s_centre)
    L, W, H = spec.length_s, spec.width_t, spec.z_top - spec.z_base
    if spec.slope:
        # front face vertical (facing the tower, at +s in the flipped local frame), rear stepped/sloped
        verts = [(-L / 2, -W / 2, spec.z_base), (L / 2, -W / 2, spec.z_base), (L / 2, W / 2, spec.z_base), (-L / 2, W / 2, spec.z_base),
                 (-L / 2 + L * 0.35, -W / 2, spec.z_top), (L / 2, -W / 2, spec.z_top), (L / 2, W / 2, spec.z_top), (-L / 2 + L * 0.35, W / 2, spec.z_top)]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        ob = nb.mesh_object(f"{name}_block", verts, faces, materials=[bc.mat(spec.material)])
    else:
        ob = bc.box(f"{name}_block", (L, W, H), (0, 0, spec.z_base), spec.material)
    bc.transform(ob, M)
    cornice = bc.box(f"{name}_cornice", (L * 0.66 + 1.0, W + 1.0, 1.0), (L * 0.17, 0, spec.z_top), spec.material)
    bc.transform(cornice, M)
    return [ob, cornice]


def build_deck(name: str, axis: Axis, ds: DeckSpec, s0: float, s1: float, deck_z: Callable[[float], float], lod: int = 0, step: float = 5.0,
               skip_ranges: Sequence[tuple[float, float]] = (), path_fn=None) -> list:
    """Deck slab(s), roadway surface, walkways, stiffening trusses, railings, lamps and lane markings between s0 and s1.
    ``skip_ranges`` leaves gaps (e.g. inside gothic towers the roadway continues; used for lift spans)."""
    out = []
    ss = samples(s0, s1, step)
    w = ds.width
    rw = ds.roadway_w or (ds.lanes * ds.lane_w)
    # structural slab
    out.append(sweep(f"{name}_slab", axis, ss, rect_section(w, ds.thickness, 0.0, 0.0), deck_z, ds.slab_material, path_fn=path_fn))
    # roadway wearing surface
    out.append(sweep(f"{name}_road", axis, ss, rect_section(rw, 0.08, ds.roadway_t, 0.08), deck_z, ds.material, path_fn=path_fn))
    # curbs / walkways
    for i, (tc, ww, dz) in enumerate(ds.walkways):
        out.append(sweep(f"{name}_walk{i}", axis, ss, rect_section(ww, 0.25 + dz, tc, 0.25 + dz), deck_z, ds.walkway_material, path_fn=path_fn))
    # lower deck
    if ds.lower_deck_dz < 0:
        lw = ds.lower_width or w
        lz = lambda s: deck_z(s) + ds.lower_deck_dz
        out.append(sweep(f"{name}_lower_slab", axis, ss, rect_section(lw, ds.thickness, 0.0, 0.0), lz, ds.slab_material, path_fn=path_fn))
        if ds.lower_lanes:
            out.append(sweep(f"{name}_lower_road", axis, ss, rect_section(ds.lower_lanes * ds.lane_w, 0.08, 0.0, 0.08), lz, ds.material, path_fn=path_fn))
        for i, tt in enumerate(ds.tracks_lower):
            out += build_tracks(f"{name}_ltrack{i}", axis, ss, tt, lz, lod)
    for i, tt in enumerate(ds.tracks):
        out += build_tracks(f"{name}_track{i}", axis, ss, tt, deck_z, lod)
    # stiffening trusses
    if ds.truss_depth > 0:
        for i, tt in enumerate(ds.truss_t):
            if lod == 0:
                seg_len = 120.0
                s = s0
                while s < s1 - 1.0:
                    e = min(s + seg_len, s1)
                    zb0 = deck_z(s) + (0.0 if ds.truss_above else -ds.truss_depth - ds.thickness)
                    zb1 = deck_z(e) + (0.0 if ds.truss_above else -ds.truss_depth - ds.thickness)
                    p0 = (path_fn(s) if path_fn else axis.p(s)) + axis.n * tt + Vector((0, 0, zb0))
                    p1 = (path_fn(e) if path_fn else axis.p(e)) + axis.n * tt + Vector((0, 0, zb1))
                    out.append(bc.truss_girder(f"{name}_truss{i}_{int(s)}", p0, p1, ds.truss_depth, 0.6, ds.truss_panel, ds.truss_material, chord=0.5, web=0.3))
                    s = e
            else:
                dz0 = 0.0 if ds.truss_above else -ds.thickness
                out.append(sweep(f"{name}_truss{i}", axis, ss, rect_section(0.6, ds.truss_depth, tt, dz0 + (ds.truss_depth if ds.truss_above else 0.0)), deck_z, ds.truss_material, path_fn=path_fn))
    if lod >= 1:
        return out
    # railings at deck edges and walkway edges
    if ds.railing:
        for side in (-1, 1):
            rail_parts = []
            for a, b_ in zip(ss[:-1], ss[1:]):
                if b_ - a < 0.5:
                    continue
            n_seg = max(int((s1 - s0) / 60.0), 1)
            for k in range(n_seg):
                a = s0 + (s1 - s0) * k / n_seg
                b_ = s0 + (s1 - s0) * (k + 1) / n_seg
                pa = (path_fn(a) if path_fn else axis.p(a)) + axis.n * (side * (w / 2 - 0.15)) + Vector((0, 0, deck_z(a)))
                pb = (path_fn(b_) if path_fn else axis.p(b_)) + axis.n * (side * (w / 2 - 0.15)) + Vector((0, 0, deck_z(b_)))
                rail_parts.append(bc.railing(f"{name}_rail{side}_{k}", pa, pb, 1.2, 3.0))
            out.append(bc.join(rail_parts, f"{name}_railing{side}"))
    # lane markings
    if ds.lanes > 0 and rw > 0:
        n_seg = max(int((s1 - s0) / 100.0), 1)
        parts = []
        for k in range(n_seg):
            a = s0 + (s1 - s0) * k / n_seg
            b_ = s0 + (s1 - s0) * (k + 1) / n_seg
            pa = (path_fn(a) if path_fn else axis.p(a)) + Vector((0, 0, deck_z(a)))
            pb = (path_fn(b_) if path_fn else axis.p(b_)) + Vector((0, 0, deck_z(b_)))
            lm = bc.lane_markings(f"{name}_lm{k}", pa, pb, ds.lane_w, ds.lanes, 0.09, centre_yellow=ds.centre_yellow, offset_t=-ds.roadway_t)
            if lm is not None:
                parts.append(lm)
        if parts:
            out.append(bc.join(parts, f"{name}_markings"))
    # lamps
    if ds.lamps_spacing > 0 and ds.lamp_t:
        lamps = []
        s = s0 + ds.lamps_spacing / 2
        while s < s1:
            for tt in ds.lamp_t:
                base = (path_fn(s) if path_fn else axis.p(s)) + axis.n * tt + Vector((0, 0, deck_z(s)))
                lamps.append(bc.lamp_post(f"{name}_lamp", base, 7.5, 1.5, math.degrees(math.atan2(-axis.n.y * math.copysign(1, tt), -axis.n.x * math.copysign(1, tt)))))
            s += ds.lamps_spacing
        if lamps:
            out.append(bc.join(lamps, f"{name}_lamps"))
    return out


def build_tracks(name: str, axis: Axis, ss: Sequence[float], t: float, z_fn: Callable[[float], float], lod: int) -> list:
    """Standard-gauge track: two rails (1.435 m gauge) on a ballast/tie strip."""
    out = [sweep(f"{name}_bed", axis, ss, rect_section(3.0, 0.15, t, 0.15), z_fn, "concrete_dark")]
    if lod == 0:
        for dt in (-0.7175, 0.7175):
            out.append(sweep(f"{name}_rail{dt:+.2f}", axis, ss, rect_section(0.07, 0.15, t + dt, 0.30), z_fn, "steel_gray"))
    return out


def build_approach(name: str, axis: Axis, ap: ApproachSpec, lod: int = 0, ds: DeckSpec | None = None) -> list:
    """Approach viaduct: deck ramp on piers (concrete/steel) or masonry arches (Brooklyn), or an embankment."""
    out = []
    z_fn = lambda s: ap.z0 + (ap.z1 - ap.z0) * (s - ap.s0) / (ap.s1 - ap.s0)
    ss = samples(ap.s0, ap.s1, 5.0)
    if ap.kind == "embankment":
        sec = [(-ap.width / 2 - 8, ap.ground_z - 100), (ap.width / 2 + 8, ap.ground_z - 100), (ap.width / 2, 0.0), (-ap.width / 2, 0.0)]
        # sloped retaining sides: bottom at ground
        sec = [(-ap.width / 2 - 6, -1e9), (ap.width / 2 + 6, -1e9), (ap.width / 2, 0.0), (-ap.width / 2, 0.0)]
        # sweep needs finite dz; do a per-sample custom mesh instead
        import bmesh
        bm = bmesh.new()
        rings = []
        for s in ss:
            zt = z_fn(s)
            ring = [bm.verts.new(axis.p(s, -ap.width / 2 - (zt - ap.ground_z) * 1.5, ap.ground_z)), bm.verts.new(axis.p(s, ap.width / 2 + (zt - ap.ground_z) * 1.5, ap.ground_z)),
                    bm.verts.new(axis.p(s, ap.width / 2, zt)), bm.verts.new(axis.p(s, -ap.width / 2, zt))]
            rings.append(ring)
        for r0, r1 in zip(rings[:-1], rings[1:]):
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        out.append(nb.bmesh_to_object(f"{name}_embankment", bm, materials=[bc.mat(ap.material)]))
    elif ap.kind == "masonry_arches":
        # solid masonry viaduct with round-arched openings through it (Brooklyn approaches)
        wall_h = lambda s: z_fn(s) - ap.ground_z
        for side in (-1, 1):
            # build wall as extruded profile in (s, z) with arch holes; split into 120 m chunks for earcut robustness
            s = ap.s0
            chunk = ap.arch_span * 8
            k = 0
            while s < ap.s1 - 1.0:
                e = min(s + chunk, ap.s1)
                prof = [(s, ap.ground_z - 1.0), (e, ap.ground_z - 1.0), (e, z_fn(e) - 0.6), (s, z_fn(s) - 0.6)]
                holes = []
                a = s + ap.arch_span * 0.5
                while a + ap.arch_span * 0.5 < e:
                    h = min(wall_h(a) - 3.5, ap.arch_span * 1.1)
                    if h > 3.0:
                        holes.append(bc.round_arch(ap.arch_span * 0.7, h, a, ap.ground_z))
                    a += ap.arch_span
                wall = bc.profile_extrude(f"{name}_wall{side}_{k}", prof, 1.6, ap.material, holes=holes, plane="xz")
                bc.transform(wall, Matrix.Translation((0, side * (ap.width / 2 - 0.8), 0)))
                bc.transform(wall, axis.matrix(0.0))
                out.append(wall)
                s = e
                k += 1
        # vault between the walls (deck support)
        out.append(sweep(f"{name}_vault", axis, ss, rect_section(ap.width - 1.6, 1.2, 0.0, -0.6), z_fn, ap.material))
    else:
        # girder / viaduct on piers
        out.append(sweep(f"{name}_girders", axis, ss, rect_section(ap.width - 1.0, 2.0 if ap.kind == "viaduct" else 3.0, 0.0, -0.4), z_fn, "steel_gray" if ap.kind == "girder" else ap.material))
        s = ap.s0 + ap.pier_spacing / 2
        while s < ap.s1:
            zt = z_fn(s) - 2.4
            if zt > ap.ground_z + 1.0:
                if ap.kind == "girder":
                    for tt in (-ap.width / 3, ap.width / 3):
                        out.append(bc.cylinder_between(f"{name}_col", axis.p(s, tt, ap.ground_z - 0.5), axis.p(s, tt, zt), 0.9, ap.material, 12))
                    cap = bc.box(f"{name}_cap", (2.0, ap.width - 2.0, 1.2), (0, 0, zt - 1.2), ap.material)
                    bc.transform(cap, axis.matrix(s))
                    out.append(cap)
                else:
                    pier = bc.box(f"{name}_pier", (3.0, ap.width * 0.6, zt - ap.ground_z + 0.5), (0, 0, ap.ground_z - 0.5), ap.material)
                    bc.transform(pier, axis.matrix(s))
                    out.append(pier)
            s += ap.pier_spacing
    if ds is not None:
        out += build_deck(f"{name}_deck", axis, ds, ap.s0, ap.s1, z_fn, lod)
    return out


# ============================================================================================ other structural systems


def build_cantilever_truss(name: str, axis: Axis, piers_s: Sequence[float], deck_z: Callable[[float], float], depth_pier: float, depth_mid: float,
                           width: float, material: str, lod: int = 0, panel: float = 9.0, pier_spec: dict | None = None, z_water: float = -3.0,
                           top_frac: float = 0.55, bot_frac: float = 0.45) -> list:
    """Cantilever truss (Queensboro type): trusses deepen over the piers (depth_pier, extending *above* the deck as the
    towers) and taper to depth_mid at mid-span / anchor ends. Piers: masonry, from z_water to the deck.

    ``top_frac``/``bot_frac`` split the local depth above and below the reference line ``deck_z``: (0.55, 0.45) gives a
    truss centred on the deck, (1.0, 0.0) a level bottom chord at deck_z with the top chord rising over the piers —
    the Queensboro arrangement, where the lower roadway rides the bottom chord for the whole length."""
    out = []
    s_start, s_end = piers_s[0], piers_s[-1]
    ss = samples(s_start, s_end, panel)

    def depth_at(s):
        # nearest pier distance -> depth profile (linear taper within each span half)
        best = None
        for i in range(len(piers_s) - 1):
            a, b_ = piers_s[i], piers_s[i + 1]
            if a - 1e-6 <= s <= b_ + 1e-6:
                u = abs(s - a) / (b_ - a)
                u = min(u, 1 - u) * 2  # 0 at pier, 1 at mid
                d = depth_pier + (depth_mid - depth_pier) * math.sqrt(u)
                best = d
        return best if best is not None else depth_mid

    for side in (-1, 1):
        tt = side * width / 2
        parts = []
        top_pts = [axis.p(s, tt, deck_z(s) + depth_at(s) * top_frac) for s in ss]
        bot_pts = [axis.p(s, tt, deck_z(s) - depth_at(s) * bot_frac) for s in ss]
        for i in range(len(ss) - 1):
            parts.append(bc.box_between(f"{name}_tc", top_pts[i], top_pts[i + 1], 0.9, 0.9, material))
            parts.append(bc.box_between(f"{name}_bc", bot_pts[i], bot_pts[i + 1], 0.9, 0.9, material))
            if lod == 0:
                parts.append(bc.box_between(f"{name}_v", bot_pts[i], top_pts[i], 0.6, 0.6, material))
                # diagonals lean toward the nearest pier (cantilever)
                nearest = min(piers_s, key=lambda p: abs(p - ss[i]))
                if ss[i] < nearest:
                    parts.append(bc.box_between(f"{name}_d", bot_pts[i], top_pts[i + 1], 0.5, 0.5, material))
                else:
                    parts.append(bc.box_between(f"{name}_d", top_pts[i], bot_pts[i + 1], 0.5, 0.5, material))
        parts.append(bc.box_between(f"{name}_v", bot_pts[-1], top_pts[-1], 0.6, 0.6, material))
        out.append(bc.join(parts, f"{name}_truss{side}"))
    # lateral bracing (top) and piers
    lat = []
    for i in range(0, len(ss), 2):
        s = ss[i]
        lat.append(bc.box_between(f"{name}_lat", axis.p(s, -width / 2, deck_z(s) + depth_at(s) * top_frac), axis.p(s, width / 2, deck_z(s) + depth_at(s) * top_frac), 0.5, 0.5, material))
    if lat:
        out.append(bc.join(lat, f"{name}_lateral"))
    ps = pier_spec or {}
    for i, s in enumerate(piers_s):
        pw = ps.get("width", width + 6)
        pd = ps.get("depth", 12.0)
        z_top = deck_z(s) - depth_at(s) * bot_frac - 0.5
        pier = bc.box(f"{name}_pier{i}", (pd, pw, z_top - z_water), (0, 0, z_water), ps.get("material", "granite_dark"))
        bc.transform(pier, axis.matrix(s))
        out.append(pier)
    return out


def build_steel_arch(name: str, axis: Axis, s0: float, s1: float, z_deck: float, rise: float, width: float, material: str, lod: int = 0,
                     n: int = 40, through: bool = True, rib_depth: float = 4.0, hanger_spacing: float = 12.0, crown_dz: float = 0.0) -> list:
    """Two-hinged steel arch (Hell Gate type): two parabolic ribs (upper + lower chord) with spandrel/hanger verticals
    to the deck. ``through``: deck hangs below the arch (Hell Gate) — the deck sits above the springing."""
    out = []
    L = s1 - s0
    sm = 0.5 * (s0 + s1)
    z_spring = z_deck - (rise * 0.25 if through else rise)

    def arch_z(s, off=0.0):
        """Parabolic rib: the two chords stay ``off`` apart even at the springings (a real arch has finite rib depth
        at its skewbacks, and a zero-depth end would make degenerate web members)."""
        u = (s - sm) / (L / 2)
        return z_spring + rise * (1 - u * u) + off

    ss = samples(s0, s1, L / n)
    for side in (-1, 1):
        tt = side * width / 2
        parts = []
        pts_lo = [axis.p(s, tt, arch_z(s)) for s in ss]
        pts_hi = [axis.p(s, tt, arch_z(s, rib_depth)) for s in ss]
        for i in range(len(ss) - 1):
            parts.append(bc.box_between(f"{name}_lo", pts_lo[i], pts_lo[i + 1], 1.4, 1.4, material))
            parts.append(bc.box_between(f"{name}_hi", pts_hi[i], pts_hi[i + 1], 1.2, 1.2, material))
            if lod == 0:
                parts.append(bc.box_between(f"{name}_w", pts_lo[i], pts_hi[i], 0.6, 0.6, material))
                parts.append(bc.box_between(f"{name}_wd", pts_lo[i], pts_hi[i + 1], 0.45, 0.45, material))
        parts.append(bc.box_between(f"{name}_w", pts_lo[-1], pts_hi[-1], 0.6, 0.6, material))
        # skewback blocks where the ribs meet the abutment
        for end in (0, -1):
            parts.append(bc.box_between(f"{name}_skew", pts_lo[end], pts_hi[end], 2.2, 2.2, material))
        out.append(bc.join(parts, f"{name}_rib{side}"))
    # bracing between ribs (top)
    br = []
    for i in range(0, len(ss), 2):
        s = ss[i]
        br.append(bc.box_between(f"{name}_br", axis.p(s, -width / 2, arch_z(s, rib_depth)), axis.p(s, width / 2, arch_z(s, rib_depth)), 0.6, 0.6, material))
        if lod == 0 and i + 2 < len(ss):
            s2 = ss[i + 2]
            br.append(bc.box_between(f"{name}_brx", axis.p(s, -width / 2, arch_z(s, rib_depth)), axis.p(s2, width / 2, arch_z(s2, rib_depth)), 0.4, 0.4, material))
    out.append(bc.join(br, f"{name}_bracing"))
    # hangers / spandrel posts
    if lod == 0:
        hp = []
        s = s0 + hanger_spacing
        while s < s1 - 1:
            za = arch_z(s)
            for side in (-1, 1):
                tt = side * width / 2
                if through and za > z_deck + 0.5:
                    hp.append(bc.box_between(f"{name}_hg", axis.p(s, tt, z_deck), axis.p(s, tt, za), 0.5, 0.5, material))
                elif not through and za < z_deck - 0.5:
                    hp.append(bc.box_between(f"{name}_sp", axis.p(s, tt, za), axis.p(s, tt, z_deck), 0.5, 0.5, material))
            s += hanger_spacing
        if hp:
            out.append(bc.join(hp, f"{name}_hangers"))
    return out


def build_lift_span(name: str, axis: Axis, s0: float, s1: float, z_deck: float, tower_h: float, width: float, material: str, lod: int = 0, raised: float = 0.0) -> list:
    """Vertical-lift span: two lattice towers at the span ends with sheave houses, counterweights, and a truss lift span."""
    out = []
    for s in (s0, s1):
        for side in (-1, 1):
            tt = side * (width / 2 + 3.0)
            out.append(bc.lattice_column(f"{name}_tw", axis.p(s, tt, z_deck - 8.0), axis.p(s, tt, z_deck + tower_h), 6.0, 4.0, material, panels=max(int(tower_h / 8), 3), member=0.8 if lod == 0 else 1.2, x_brace=(lod == 0)))
        house = bc.box(f"{name}_sheave", (8.0, width + 12.0, 5.0), (0, 0, z_deck + tower_h), material)
        bc.transform(house, axis.matrix(s))
        out.append(house)
        for side in (-1, 1):
            cw = bc.box(f"{name}_cw", (3.0, 3.0, 8.0), (0, side * (width / 2 + 3.0), z_deck + tower_h - 14.0 - raised), "concrete_dark")
            bc.transform(cw, axis.matrix(s))
            out.append(cw)
        # lateral bracing between the two towers at each end
        out.append(bc.box_between(f"{name}_tb", axis.p(s, -(width / 2 + 3.0), z_deck + tower_h * 0.5), axis.p(s, width / 2 + 3.0, z_deck + tower_h * 0.5), 1.0, 1.0, material))
    out.append(bc.truss_girder(f"{name}_span", axis.p(s0 + 4, 0, z_deck + raised - 0.4), axis.p(s1 - 4, 0, z_deck + raised - 0.4), 7.0, width, 8.0, material, chord=0.8, web=0.4, kind="pratt"))
    return out


def build_cable_stayed(name: str, axis: Axis, s_tower: float, z_deck: float, tower_h: float, width: float, span_back: float, span_main: float,
                       n_stays: int, material: str, cable_material: str, lod: int = 0, tower_style: str = "inverted_y") -> list:
    """Single-pylon cable-stayed unit (Kosciuszko has two such units per structure). Fan of stays from the pylon head to
    deck anchor points spaced evenly along both spans."""
    out = []
    zt = z_deck + tower_h
    if tower_style == "inverted_y":
        for side in (-1, 1):
            out.append(bc.box_between(f"{name}_leg{side}", axis.p(s_tower, side * (width / 2 + 1.5), -3.0), axis.p(s_tower, 0.0, z_deck + tower_h * 0.55), 4.0, 5.0, material))
        out.append(bc.box_between(f"{name}_mast", axis.p(s_tower, 0.0, z_deck + tower_h * 0.5), axis.p(s_tower, 0.0, zt), 4.0, 5.0, material))
        cross = bc.box(f"{name}_cross", (5.0, width + 3.0, 3.0), (0, 0, z_deck - 3.0), material)
        bc.transform(cross, axis.matrix(s_tower))
        out.append(cross)
    else:
        for side in (-1, 1):
            out.append(bc.box_between(f"{name}_leg{side}", axis.p(s_tower, side * (width / 2 + 1.5), -3.0), axis.p(s_tower, side * (width / 2 + 1.5), zt), 4.0, 5.0, material))
        cross = bc.box(f"{name}_cross", (5.0, width + 6.0, 3.0), (0, 0, zt - 3.0), material)
        bc.transform(cross, axis.matrix(s_tower))
        out.append(cross)
    if lod == 0:
        stays = []
        for direction, span in ((-1, span_back), (1, span_main)):
            for i in range(1, n_stays + 1):
                s = s_tower + direction * span * i / n_stays
                z_head = zt - 2.0 - (n_stays - i) * (tower_h * 0.35 / n_stays)
                for side in (-1, 1):
                    stays.append(bc.cylinder_between(f"{name}_stay", axis.p(s_tower, 0.0 if tower_style == "inverted_y" else side * (width / 2 + 1.5), z_head),
                                                     axis.p(s, side * (width / 2 - 0.5), z_deck - 0.2), 0.12, cable_material, 5))
        out.append(bc.join(stays, f"{name}_stays"))
    return out


def build_bascule(name: str, axis: Axis, s_centre: float, span: float, z_deck: float, width: float, material: str, lod: int = 0) -> list:
    """Double-leaf trunnion bascule (Pulaski type): two pier houses, counterweight pits, two steel leaves meeting at mid."""
    out = []
    for direction in (-1, 1):
        s_pier = s_centre + direction * span / 2
        pier = bc.box(f"{name}_pier", (10.0, width + 4.0, z_deck - 1.5 + 3.0), (0, 0, -3.0), "concrete")
        bc.transform(pier, axis.matrix(s_pier + direction * 5.0))
        out.append(pier)
        house = bc.box(f"{name}_house", (6.0, 6.0, 6.0), (direction * 6.0, (width / 2 + 1.0) * (1 if direction < 0 else -1), z_deck + 0.2), "brick_red")
        bc.transform(house, axis.matrix(s_pier))
        out.append(house)
        leaf = bc.box(f"{name}_leaf", (span / 2 - 0.3, width, 2.2), (direction * (span / 4 + 0.15), 0, z_deck - 2.4), material)
        bc.transform(leaf, axis.matrix(s_centre))
        out.append(leaf)
    return out


def build_masonry_arches(name: str, axis: Axis, s0: float, s1: float, arch_span: float, pier_w: float, z_deck: float, z_ground: float, width: float,
                         material: str, lod: int = 0) -> list:
    """Masonry arched viaduct (High Bridge): semicircular arches on piers, spandrel walls to the deck."""
    n = max(int(round((s1 - s0) / (arch_span + pier_w))), 1)
    pitch = (s1 - s0) / n
    span = pitch - pier_w
    prof = [(s0, z_ground - 1.0), (s1, z_ground - 1.0), (s1, z_deck - 0.3), (s0, z_deck - 0.3)]
    holes = []
    for i in range(n):
        c = s0 + pitch * (i + 0.5)
        h = min(z_deck - 3.0 - z_ground, span / 2 + (z_deck - z_ground) * 0.55)
        holes.append(bc.round_arch(span, h, c, z_ground))
    wall = bc.profile_extrude(f"{name}_arches", prof, width, material, holes=holes, plane="xz")
    bc.transform(wall, axis.matrix(0.0))
    return [wall]


# ============================================================================================ furniture helpers


def portal_arch_building(name: str, axis: Axis, s: float, width: float, depth: float, height: float, arch_w: float, arch_h: float, material: str,
                         colonnade: tuple[float, float, int] | None = None) -> list:
    """Triumphal arch (Manhattan Bridge / Washington Square style) with optional flanking colonnade (length, height, columns)."""
    out = []
    prof = [(-width / 2, 0.0), (width / 2, 0.0), (width / 2, height), (-width / 2, height)]
    arch = bc.profile_extrude(f"{name}_arch", prof, depth, material, holes=[bc.round_arch(arch_w, arch_h, 0.0, 0.0)], plane="yz")
    bc.transform(arch, axis.matrix(s))
    out.append(arch)
    attic = bc.box(f"{name}_attic", (depth + 0.8, width + 0.8, 1.2), (0, 0, height), material)
    bc.transform(attic, axis.matrix(s))
    out.append(attic)
    if colonnade:
        L, H, ncol = colonnade
        for side in (-1, 1):
            for i in range(ncol):
                u = (i + 0.5) / ncol
                t = side * (width / 2 + L * u)
                # gentle curve: colonnade sweeps back (Manhattan plaza is a semicircle)
                ds_ = (u * u) * L * 0.55
                out.append(bc.cylinder_between(f"{name}_col", axis.p(s + ds_, t, 0.0), axis.p(s + ds_, t, H - 1.5), 0.8, material, 12))
                cap = bc.box(f"{name}_cap", (2.0, 2.0, 0.6), (0, 0, H - 1.5), material)
                bc.transform(cap, axis.matrix(s + ds_, t))
                out.append(cap)
            ent_pts = [axis.p(s + (((i + 0.5) / ncol) ** 2) * L * 0.55, side * (width / 2 + L * (i + 0.5) / ncol), H - 0.6) for i in range(ncol)]
            for a, b_ in zip(ent_pts[:-1], ent_pts[1:]):
                out.append(bc.box_between(f"{name}_ent", a, b_, 2.2, 1.6, material))
    return out
