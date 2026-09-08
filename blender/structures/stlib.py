"""Geometry for the rail structures and the waterfront, with no ``bpy`` in it.

986 km of rail structure and 166 ha of pier, seawall and jetty are surveyed, measured and, until
this stage, entirely absent from the world. What the terrain already carries and what it does not is
not a matter of opinion here -- it was measured, by sampling the landscape the engine will build
across 200 structures of each class, perpendicular to the track:

===========  ==================================  ======================================
class        terrain at the centreline           what this stage builds
===========  ==================================  ======================================
elevated     0.10 m **below** the flanks         the whole structure: deck and bents
viaduct      (same; the deck is off the ground)  the whole structure: deck and piers
embankment   3.69 m **above** (92 % over 1 m)    nothing -- the earthwork is in the DEM
open_cut     3.32 m **below** (81 % under -1 m)  nothing -- the cutting is in the DEM
===========  ==================================  ======================================

So an embankment berm modelled here would stand on the berm the terrain already has, and an open cut
trench would be a second trench inside the first. The two classes that *are* missing are the ones
whose structure stands in the air, and they are 505 km of it.

Every dimension below is either a column of the source table or a published standard, and each says
which. The one thing invented is where a pile stops under water, which nobody can see and which the
docstring says outright.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------------------- constants

#: Structural depth of the deck below the rail head, metres.
#:
#: A New York elevated is a steel through-girder or deck-girder structure: the running rails sit on
#: longitudinal stringers carried by transverse floor beams over the bent caps. Rail head to the
#: underside of the floor beam is about 1.2 m on the standard Rapid Transit elevated. A concrete
#: viaduct of the Culver or Hell Gate approach type is deeper, about 1.8 m to the soffit.
DECK_THICKNESS_M = {"elevated": 1.2, "viaduct": 1.8}

#: Distance between bents along the structure, metres.
#:
#: The standard New York elevated bent spacing is 45 feet (13.72 m) -- the panel length the steel
#: was ordered in. Concrete viaducts span further; 24 m is the Culver Viaduct's typical bay.
BENT_SPACING_M = {"elevated": 13.72, "viaduct": 24.0}

#: Column side length, metres (square section). The El's built-up steel columns are about 0.45 m
#: across the flanges; a viaduct pier is a concrete shaft about 1.1 m.
COLUMN_SIDE_M = {"elevated": 0.45, "viaduct": 1.1}

#: How far inboard of the deck edge a column stands, metres. The El's columns carry the deck through
#: a cap girder that cantilevers past them, so the columns are set in from the edge.
COLUMN_INSET_M = {"elevated": 1.3, "viaduct": 1.6}

#: Depth of the cap girder that spans between the two columns of a bent, metres.
CAP_DEPTH_M = {"elevated": 0.9, "viaduct": 1.2}

#: A structure narrower than this is carried on a single line of columns down its centre rather than
#: on a two-column bent: that is what a single-track elevated structure looks like.
SINGLE_COLUMN_MAX_WIDTH_M = 6.0

#: Deck thickness of a pier, metres: a timber or concrete deck on pile caps, about 0.6 m to the
#: soffit.
PIER_DECK_THICKNESS_M = 0.6

#: Pile spacing under a pier deck, metres. New York timber piers are framed on bents of about 4.6 m
#: (15 ft) with piles about 3 m apart along the bent; 4.5 m in both directions is that grid.
PILE_SPACING_M = 4.5

#: Pile diameter, metres (a 14-inch timber or concrete pile).
PILE_DIAMETER_M = 0.36

#: How far below the water surface a pile, a seawall or a jetty is modelled, metres.
#:
#: **This is the one invented number in this module.** The harbour bed is not in any dataset this
#: build has -- the terrain rasters stop at the shoreline -- so a pile that ran to the real bed
#: would be running to a bed nobody measured. It is cut 2 m under the surface instead, which is
#: below anything the camera sees and above anything a boat would hit. Recorded in
#: docs/DEVIATIONS.md.
UNDERWATER_M = 2.0

#: Water surface, metres NAVD88. The tide model moves the rendered surface; the structures are cut
#: against mean water, which is where their own surveyed deck elevations are referenced.
WATER_Z_M = 0.0

#: Thickness of a station platform slab and of a canopy roof, metres. The platform is a concrete
#: deck on the station's own framing; the canopy is a light roof on columns.
PLATFORM_THICKNESS_M = 0.35
CANOPY_THICKNESS_M = 0.30

#: Spacing and section of the columns that carry a platform canopy, metres. NYCT elevated station
#: canopies stand on a line of light steel columns about 4.6 m (15 ft) apart along the platform.
CANOPY_COLUMN_SPACING_M = 4.6
CANOPY_COLUMN_SIDE_M = 0.20

#: How far in from the roof outline the canopy columns stand, metres.
CANOPY_COLUMN_INSET_M = 1.0

#: Material name per structure part, matching the texture library in ``blender/common/textures.py``.
MATERIALS = {
    "el_steel": "painted_metal_green",      # NYC elevated steel is painted; the IRT/BMT els are a grey-green
    "viaduct_concrete": "concrete",
    "pier_deck": "concrete",
    "pier_pile": "concrete",
    "seawall": "concrete",
    "jetty": "stone_rubble",
    "platform": "concrete_sidewalk",
    "canopy": "corrugated_metal",
    "station_house": "tan_brick",
}

#: ``nycsim_gameplay::SurfaceClass`` for the parts a wheel or a foot can touch. The deck of an
#: elevated railway is not drivable, but the collision still resolves a surface, and the pier decks
#: on the Brooklyn and Manhattan waterfronts are places a car can be driven onto.
SURFACE_CLASS = {"el_steel": 6, "viaduct_concrete": 6, "pier_deck": 6, "pier_pile": 6,
                 "seawall": 6, "jetty": 8, "platform": 9, "canopy": 6, "station_house": 6}


# --------------------------------------------------------------------------------------- buffers

@dataclass
class MeshBuffer:
    """Triangles accumulating under one material name."""

    part: str
    verts: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, int, int]] = field(default_factory=list)
    pieces: int = 0

    def add(self, verts: np.ndarray, tris: np.ndarray) -> None:
        base = len(self.verts)
        self.verts.extend((float(a), float(b), float(c)) for a, b, c in verts)
        self.faces.extend((int(a) + base, int(b) + base, int(c) + base) for a, b, c in tris)

    def add_box(self, cx: float, cy: float, z0: float, z1: float, sx: float, sy: float,
                yaw: float = 0.0) -> None:
        """An axis-box, optionally rotated about its own vertical axis."""
        hx, hy = sx / 2.0, sy / 2.0
        c, s = math.cos(yaw), math.sin(yaw)
        corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        ring = [(cx + x * c - y * s, cy + x * s + y * c) for x, y in corners]
        v = np.array([(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring], dtype=np.float64)
        t = np.array([
            (0, 2, 1), (0, 3, 2),            # bottom
            (4, 5, 6), (4, 6, 7),            # top
            (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6),
            (3, 0, 4), (3, 4, 7),
        ], dtype=np.int64)
        self.add(v, t)

    def add_prism(self, ring: np.ndarray, z0: float, z1: float, tris: np.ndarray) -> None:
        """A closed prism: ``ring`` (N,2) capped top and bottom by ``tris`` and walled all round."""
        n = len(ring)
        v = np.concatenate([np.column_stack([ring, np.full(n, z0)]),
                            np.column_stack([ring, np.full(n, z1)])])
        faces = [(int(a), int(c), int(b)) for a, b, c in tris]                 # bottom, wound down
        faces += [(int(a) + n, int(b) + n, int(c) + n) for a, b, c in tris]    # top
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, j + n))
            faces.append((i, j + n, i + n))
        self.add(v, np.asarray(faces, dtype=np.int64))


# --------------------------------------------------------------------------------------- helpers

def offsets(pts: np.ndarray) -> np.ndarray:
    """Unit left-normals at each vertex of a polyline, mitred so a constant offset stays constant.

    At a bend the normal is the bisector of the two segment normals divided by the cosine of half
    the turn, which is what keeps the two offset lines parallel to the centreline through the
    corner. The scale is capped at 3 so a hairpin cannot throw the deck edge to infinity.
    """
    p = np.asarray(pts, dtype=np.float64)
    d = np.diff(p, axis=0)
    seg = np.linalg.norm(d, axis=1)
    good = seg > 1e-9
    d = d[good]
    seg = seg[good]
    if len(d) == 0:
        return np.zeros((len(p), 2))
    d = d / seg[:, None]
    n = np.column_stack([-d[:, 1], d[:, 0]])
    out = np.empty((len(d) + 1, 2))
    out[0] = n[0]
    out[-1] = n[-1]
    if len(n) > 1:
        m = n[:-1] + n[1:]
        norm = np.linalg.norm(m, axis=1)
        norm = np.where(norm < 1e-9, 1.0, norm)
        m = m / norm[:, None]
        cos_half = np.clip(np.sum(m * n[:-1], axis=1), 1.0 / 3.0, 1.0)
        out[1:-1] = m / cos_half[:, None]
    return out


def clean_line(pts: np.ndarray, min_seg_m: float = 1e-6) -> np.ndarray:
    """Drop repeated vertices; a duplicated point has no direction and mitres to nothing."""
    p = np.asarray(pts, dtype=np.float64)[:, :2]
    if len(p) < 2:
        return p
    keep = [0]
    for i in range(1, len(p)):
        if math.dist(p[i], p[keep[-1]]) > min_seg_m:
            keep.append(i)
    return p[keep] if len(keep) >= 2 else p[:2]


def resample(pts: np.ndarray, step_m: float) -> tuple[np.ndarray, np.ndarray]:
    """``(points, tangent directions)`` every ``step_m`` along a polyline, ends included."""
    p = clean_line(pts)
    if len(p) < 2:
        return p, np.zeros((len(p), 2))
    d = np.diff(p, axis=0)
    seg = np.linalg.norm(d, axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(s[-1])
    n = max(2, int(round(total / step_m)) + 1)
    want = np.linspace(0.0, total, n)
    idx = np.clip(np.searchsorted(s, want, side="right") - 1, 0, len(seg) - 1)
    t = (want - s[idx]) / np.where(seg[idx] > 0, seg[idx], 1.0)
    out = p[idx] + d[idx] * t[:, None]
    dirs = d[idx] / np.where(seg[idx] > 0, seg[idx], 1.0)[:, None]
    return out, dirs


def deck_ribbon(buf: MeshBuffer, pts: np.ndarray, width_m: float, z_top: float,
                thickness_m: float) -> int:
    """A closed box beam along ``pts``: top at ``z_top``, soffit ``thickness_m`` below.

    Returns the number of triangles added, 0 if the line is degenerate.
    """
    p = clean_line(pts)
    if len(p) < 2 or width_m <= 0:
        return 0
    n = offsets(p)
    half = width_m / 2.0
    left = p + n * half
    right = p - n * half
    z0 = z_top - thickness_m
    m = len(p)
    v = np.concatenate([
        np.column_stack([left, np.full(m, z_top)]),      # 0     .. m-1
        np.column_stack([right, np.full(m, z_top)]),     # m     .. 2m-1
        np.column_stack([left, np.full(m, z0)]),         # 2m    .. 3m-1
        np.column_stack([right, np.full(m, z0)]),        # 3m    .. 4m-1
    ])
    L, R, LB, RB = 0, m, 2 * m, 3 * m
    faces = []
    for i in range(m - 1):
        j = i + 1
        faces += [(L + i, R + i, R + j), (L + i, R + j, L + j)]              # top
        faces += [(LB + i, RB + j, RB + i), (LB + i, LB + j, RB + j)]        # soffit
        faces += [(L + i, L + j, LB + j), (L + i, LB + j, LB + i)]           # left face
        faces += [(R + i, RB + i, RB + j), (R + i, RB + j, R + j)]           # right face
    faces += [(L, LB, RB), (L, RB, R)]                                       # start cap
    e = m - 1
    faces += [(L + e, R + e, RB + e), (L + e, RB + e, LB + e)]               # end cap
    buf.add(v, np.asarray(faces, dtype=np.int64))
    buf.pieces += 1
    return len(faces)


def bents(buf: MeshBuffer, pts: np.ndarray, width_m: float, soffit_z: float,
          ground_z, spacing_m: float, column_side_m: float, inset_m: float,
          cap_depth_m: float, min_height_m: float = 0.5) -> int:
    """Columns and cap girders under a deck, every ``spacing_m`` along it.

    ``ground_z`` is a scalar or a callable ``f(x, y) -> z`` so the legs land on the terrain the
    engine has rather than on the structure's own median ground elevation.
    """
    p, dirs = resample(pts, spacing_m)
    if len(p) < 2:
        return 0
    half = width_m / 2.0
    single = width_m <= SINGLE_COLUMN_MAX_WIDTH_M
    lever = 0.0 if single else max(0.0, half - inset_m)
    placed = 0
    xs, ys = p[:, 0], p[:, 1]
    if callable(ground_z):
        gz = np.asarray(ground_z(xs, ys), dtype=np.float64)
    else:
        gz = np.full(len(p), float(ground_z))
    cap_bottom = soffit_z - cap_depth_m
    for i in range(len(p)):
        g = gz[i]
        if not math.isfinite(g) or soffit_z - g < min_height_m:
            continue
        nx, ny = -dirs[i, 1], dirs[i, 0]
        yaw = math.atan2(dirs[i, 1], dirs[i, 0])
        legs = [0.0] if single else [-lever, lever]
        for off in legs:
            buf.add_box(p[i, 0] + nx * off, p[i, 1] + ny * off, g, cap_bottom,
                        column_side_m, column_side_m, yaw)
            placed += 1
        if not single:
            # the cap girder spanning the two legs, running across the structure
            buf.add_box(p[i, 0], p[i, 1], cap_bottom, soffit_z,
                        column_side_m, width_m, yaw)
    buf.pieces += placed
    return placed


def pile_grid(ring: np.ndarray, spacing_m: float, inset_m: float = 1.0) -> np.ndarray:
    """Points on a ``spacing_m`` grid that fall inside ``ring``, at least ``inset_m`` from its edge.

    Even-odd ray casting rather than shapely, so the module stays importable inside Blender's Python
    without a geometry stack. The inset keeps a pile from poking out of the deck it holds up.
    """
    r = np.asarray(ring, dtype=np.float64)[:, :2]
    if len(r) < 3:
        return np.zeros((0, 2))
    lo, hi = r.min(axis=0), r.max(axis=0)
    if np.any(hi - lo < 2 * inset_m):
        return np.zeros((0, 2))
    xs = np.arange(lo[0] + spacing_m / 2, hi[0], spacing_m)
    ys = np.arange(lo[1] + spacing_m / 2, hi[1], spacing_m)
    if not len(xs) or not len(ys):
        return np.zeros((0, 2))
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    inside = point_in_ring(pts, r)
    if not inside.any():
        return np.zeros((0, 2))
    pts = pts[inside]
    if inset_m > 0:
        keep = distance_to_ring(pts, r) >= inset_m
        pts = pts[keep]
    return pts


def point_in_ring(pts: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """Even-odd test of many points against one ring."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), dtype=bool)
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        crosses = ((y0 > y) != (y1 > y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = x0 + (y - y0) * (x1 - x0) / np.where(y1 != y0, y1 - y0, np.nan)
        inside ^= crosses & (x < xint)
    return inside


def distance_to_ring(pts: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """Shortest distance from each point to the ring's edges."""
    best = np.full(len(pts), np.inf)
    n = len(ring)
    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        ab = b - a
        L2 = float(ab @ ab)
        if L2 < 1e-12:
            d = np.linalg.norm(pts - a, axis=1)
        else:
            t = np.clip(((pts - a) @ ab) / L2, 0.0, 1.0)
            proj = a + t[:, None] * ab
            d = np.linalg.norm(pts - proj, axis=1)
        best = np.minimum(best, d)
    return best


def ring_area(ring: np.ndarray) -> float:
    r = np.asarray(ring, dtype=np.float64)[:, :2]
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def ear_clip(ring: np.ndarray) -> np.ndarray:
    """Triangulate a simple polygon. Small rings only: piers and seawalls are tens of vertices."""
    r = np.asarray(ring, dtype=np.float64)[:, :2]
    n = len(r)
    if n < 3:
        return np.zeros((0, 3), dtype=np.int64)
    idx = list(range(n))
    if ring_area(r) < 0:
        idx.reverse()
    tris: list[tuple[int, int, int]] = []
    guard = 0
    while len(idx) > 3 and guard < 4 * n:
        guard += 1
        clipped = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = r[i0], r[i1], r[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-12:
                continue
            others = [j for j in idx if j not in (i0, i1, i2)]
            if others:
                p = r[others]
                d0 = (b[0] - a[0]) * (p[:, 1] - a[1]) - (b[1] - a[1]) * (p[:, 0] - a[0])
                d1 = (c[0] - b[0]) * (p[:, 1] - b[1]) - (c[1] - b[1]) * (p[:, 0] - b[0])
                d2 = (a[0] - c[0]) * (p[:, 1] - c[1]) - (a[1] - c[1]) * (p[:, 0] - c[0])
                if np.any((d0 >= 0) & (d1 >= 0) & (d2 >= 0)):
                    continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            clipped = True
            break
        if not clipped:
            break
    if len(idx) == 3:
        tris.append((idx[0], idx[1], idx[2]))
    return np.asarray(tris, dtype=np.int64) if tris else np.zeros((0, 3), dtype=np.int64)


def station(platform_buf: "MeshBuffer", canopy_buf: "MeshBuffer", ring: np.ndarray,
            base_z: float, roof_z: float) -> int:
    """An elevated station: a platform slab, a canopy roof over it, and the columns between.

    The survey digitises the **roof outline**, "delineated to include any underlying stairways"
    (Capture Rules, RAILROAD STRUCTURE), so the polygon is the canopy and the platform under it is
    the same plan. Returns the number of columns placed.
    """
    tris = ear_clip(ring)
    if not len(tris):
        return 0
    platform_buf.add_prism(ring, base_z - PLATFORM_THICKNESS_M, base_z, tris)
    platform_buf.pieces += 1
    canopy_buf.add_prism(ring, roof_z - CANOPY_THICKNESS_M, roof_z, tris)
    canopy_buf.pieces += 1
    posts = pile_grid(ring, CANOPY_COLUMN_SPACING_M, inset_m=CANOPY_COLUMN_INSET_M)
    for px, py in posts:
        canopy_buf.add_box(px, py, base_z, roof_z - CANOPY_THICKNESS_M,
                           CANOPY_COLUMN_SIDE_M, CANOPY_COLUMN_SIDE_M)
    canopy_buf.pieces += len(posts)
    return len(posts)


def station_house(buf: "MeshBuffer", ring: np.ndarray, z0: float, z1: float) -> bool:
    """A stand-alone station at or below grade: one volume from its ground to its roof."""
    tris = ear_clip(ring)
    if not len(tris):
        return False
    buf.add_prism(ring, z0, z1, tris)
    buf.pieces += 1
    return True

