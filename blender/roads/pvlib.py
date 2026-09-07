"""Geometry for the road-surface stage: the real paved surfaces of New York as drivable slabs.

Kept apart from ``build_pavement.py`` so the parts that are pure geometry -- refinement, draping,
skirts -- can be tested without Blender.  Nothing here imports ``bpy``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------- the surfaces

#: ``kind`` -> (name, lift above the ground in metres, downward skirt depth in metres).
#:
#: The lifts are the ones the verification renderer has been drawing since Stage 12 and that every
#: comparison sheet was judged against (``blender/verify/scene.py`` ``PAVEMENT_KINDS``): the roadbed
#: at +0.10, everything a pedestrian walks on at +0.25, so the curb reveal between them is the real
#: 0.15 m, and the crosswalk 15 mm proud of the roadbed because that is what a thermoplastic marking
#: is.
#:
#: The skirt is new here and has two jobs.  It gives the curb an actual vertical face -- in the
#: renders the pavement is a zero-thickness sheet, so the 0.15 m step reads only as a silhouette and
#: never as the concrete face that is one of the most visible things at eye level from a car.  And it
#: makes the slab solid, so where the landscape's own triangulation rises above the draped top the
#: seam is a sliver rather than a window into the void under the road.
PAVEMENT_KINDS: dict[int, tuple[str, float, float]] = {
    0: ("roadbed", 0.10, 0.30),
    1: ("sidewalk", 0.25, 0.40),
    2: ("median", 0.25, 0.40),
    3: ("plaza", 0.25, 0.40),
    4: ("curb", 0.25, 0.40),
    5: ("crosswalk", 0.115, 0.02),
    6: ("parking_lot", 0.10, 0.30),
    7: ("driveway", 0.10, 0.30),
}

#: ``surface`` -> name (``pipeline/nycsim_pipeline/roads/schema.py``).
SURFACE_NAMES = {0: "asphalt", 1: "concrete", 2: "cobble", 3: "steel", 4: "gravel", 5: "boardwalk"}

#: ``surface`` -> ``nycsim_gameplay::SurfaceClass`` (``CoreAdapter/GameplayVehicleDynamics.h``),
#: which is also the ``EPhysicalSurface`` index ``DefaultEngine.ini`` names
#: (``SurfaceType1=Asphalt`` ... ``SurfaceType13=Ice``) and which
#: ``UNYCVehicleMovementComponent::ToSurfaceClass`` casts straight across.
SURFACE_TO_CLASS = {0: 1, 1: 2, 2: 3, 3: 4, 4: 6, 5: 7}

#: Two kinds override the material class, because what the tyre meets there is not what the slab is
#: made of: a crosswalk is paint on top of asphalt (``PaintedMarking``, µ 0.60 wet against asphalt's
#: 0.70), and a sidewalk is concrete the car is not supposed to be on (``Sidewalk``, which the
#: friction table gives its own entry).
KIND_FORCES_CLASS = {1: 9, 5: 5}

#: Names of ``SurfaceClass``, for the manifest and the physical-material assets.
SURFACE_CLASS_NAMES = {0: "Default", 1: "Asphalt", 2: "Concrete", 3: "Cobble", 4: "SteelPlate",
                       5: "PaintedMarking", 6: "Gravel", 7: "Boardwalk", 8: "Grass", 9: "Sidewalk",
                       10: "Water", 11: "Metal", 12: "Snow", 13: "Ice"}


def surface_class(kind: int, surface: int) -> int:
    """The ``SurfaceClass`` a wheel meets on this polygon."""
    if kind in KIND_FORCES_CLASS:
        return KIND_FORCES_CLASS[kind]
    return SURFACE_TO_CLASS.get(int(surface), 1)


def material_name(kind: int, surface: int) -> str:
    k = PAVEMENT_KINDS.get(int(kind), ("unknown", 0.0, 0.0))[0]
    s = SURFACE_NAMES.get(int(surface), f"surface{int(surface)}")
    return f"pave_{k}_{s}"


# --------------------------------------------------------------------------- triangulation


def grid_triangulate(poly, cell_m: float):
    """Cut a polygon on a regular grid and triangulate each piece. Returns ``(points, triangles)``.

    Ear clipping is the wrong way to triangulate a planimetric surface. It is correct and it is fast,
    and on a road polygon 11,446 m2 in area with a 2,195 m perimeter it produces long thin triangles
    that no amount of subsequent refinement repairs: measured, 97.4 % of the refined output had a
    shape quality below 0.1, the median quality was 0.001 and the smallest edge was 0.0000 m --
    133,004 triangles at 0.086 m2 each where a 2 m mesh should give 1.7. Longest-edge bisection
    bounds how fast a triangle degenerates; it does not improve one that started bad, and uniform
    subdivision of a sliver just gives four slivers of the same shape.

    Cutting on a grid instead gives compact pieces by construction, and the count is what the area
    says it should be rather than what the ear-clipping order happened to produce. The polygon
    boundary is preserved exactly: every piece is an intersection with the original, so the union of
    the pieces is the original and nothing is approximated.

    The grid is walked row by row, and each row's own pieces decide which columns are visited, so the
    work is proportional to the cells the polygon actually covers rather than to its bounding box --
    which for a ribbon along an avenue is a factor of a hundred.
    """
    import mapbox_earcut as earcut
    import shapely

    if cell_m <= 0.0:
        return _earcut_polygon(poly)
    minx, miny, maxx, maxy = poly.bounds
    j0, j1 = int(np.floor(miny / cell_m)), int(np.ceil(maxy / cell_m))
    if (j1 - j0) > 4000:                       # a degenerate bound; fall back rather than churn
        return _earcut_polygon(poly)

    points: list = []
    tris: list = []

    def emit(piece) -> None:
        for part in (piece.geoms if piece.geom_type in ("MultiPolygon", "GeometryCollection") else [piece]):
            if getattr(part, "geom_type", "") != "Polygon" or part.is_empty or part.area <= 1e-9:
                continue
            pts, faces = _earcut_polygon(part)
            if len(faces) == 0:
                continue
            base = len(points)
            points.extend(pts)
            tris.extend((base + a, base + b, base + c) for a, b, c in faces)

    for j in range(j0, j1):
        row = shapely.box(minx - 1.0, j * cell_m, maxx + 1.0, (j + 1) * cell_m)
        strip = poly.intersection(row)
        if strip.is_empty:
            continue
        for part in (strip.geoms if strip.geom_type in ("MultiPolygon", "GeometryCollection") else [strip]):
            if getattr(part, "geom_type", "") != "Polygon" or part.is_empty:
                continue
            px0, _py0, px1, _py1 = part.bounds
            i0, i1 = int(np.floor(px0 / cell_m)), int(np.ceil(px1 / cell_m))
            if i1 - i0 <= 1:
                emit(part)
                continue
            for i in range(i0, i1):
                cell = shapely.box(i * cell_m, j * cell_m, (i + 1) * cell_m, (j + 1) * cell_m)
                piece = part.intersection(cell)
                if not piece.is_empty:
                    emit(piece)

    if not tris:
        return _earcut_polygon(poly)
    return np.asarray(points, dtype=np.float64), np.asarray(tris, dtype=np.int64).reshape(-1, 3)


def _earcut_polygon(poly):
    """Ear-clip one polygon with its holes, exterior counter-clockwise and holes clockwise."""
    import mapbox_earcut as earcut

    ext = np.asarray(poly.exterior.coords, dtype=np.float64)[:-1, :2]
    if len(ext) < 3:
        return np.zeros((0, 2)), np.zeros((0, 3), dtype=np.int64)
    ext = orient_ring(ext, ccw=True)
    holes = [orient_ring(np.asarray(r.coords, dtype=np.float64)[:-1, :2], ccw=False)
             for r in poly.interiors if len(r.coords) > 3]
    pts = np.vstack([ext, *holes]) if holes else ext
    rings = np.cumsum([len(ext)] + [len(h) for h in holes])
    try:
        faces = earcut.triangulate_float64(pts, rings).reshape(-1, 3)
    except Exception:
        return np.zeros((0, 2)), np.zeros((0, 3), dtype=np.int64)
    return pts, faces


# --------------------------------------------------------------------------- refinement


def boundary_loops(tris: np.ndarray) -> list[list[int]]:
    """Ordered vertex loops of the boundary of a triangulated patch.

    An edge on the boundary is used by exactly one triangle, so with consistently wound triangles
    each boundary edge appears exactly once as a *directed* edge and chaining them recovers loops
    that are already wound correctly -- the outer loop the way the triangles are wound, every hole
    the other way.  That is what the skirt needs, and it is why the skirt does not have to be built
    from the original rings: after refinement those rings carry vertices the rings never had.
    """
    seen: dict[tuple[int, int], int] = {}
    for a, b, c in np.asarray(tris, dtype=np.int64):
        for p_, q in ((int(a), int(b)), (int(b), int(c)), (int(c), int(a))):
            seen[(p_, q)] = seen.get((p_, q), 0) + 1
    nxt: dict[int, list[int]] = {}
    for (p_, q), n in seen.items():
        if n == 1 and seen.get((q, p_), 0) == 0:
            nxt.setdefault(p_, []).append(q)
    loops: list[list[int]] = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        cur = start
        while True:
            outs = nxt.get(cur)
            if not outs:
                break
            nxt_v = outs.pop()
            if not outs:
                nxt.pop(cur, None)
            if nxt_v == start:
                break
            if nxt_v in loop:                 # a pinch point: close here rather than loop forever
                break
            loop.append(nxt_v)
            cur = nxt_v
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def _propagate_longest_edge(verts: list, faces: list, marked: set) -> set:
    """Rivara's rule: a triangle that is split at all is split at its **longest** edge.

    Without it, bisection degenerates. The error criterion marks whichever edge the ground bends
    across, which on an ear-clipped planimetric polygon is very often a sliver's *short* edge;
    splitting that makes two thinner slivers, whose short edges are then marked in turn. Measured on
    the largest roadbed polygon of one Lower Manhattan tile -- 11,446 m2, 254 ear-clipped triangles --
    the result was **137,287** triangles of which **97.4 %** had a shape quality below 0.1, a median
    quality of 0.001 and a smallest edge of 0.0000 m: 0.083 m2 per triangle where a 2 m floor should
    give 1.7.

    Adding the longest edge of every triangle that is being split is what bounds the aspect ratio,
    and it is a theorem about this scheme rather than a heuristic: repeated longest-edge bisection of
    any triangle produces triangles whose smallest angle is at least half the original's.
    """
    marked = set(marked)
    for _ in range(64):
        added = False
        for f in faces:
            e = [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]
            keys = [(a, b) if a < b else (b, a) for a, b in e]
            if not any(k in marked for k in keys):
                continue
            lengths = []
            for a, b in e:
                ax, ay = verts[a]
                bx, by = verts[b]
                lengths.append((ax - bx) ** 2 + (ay - by) ** 2)
            longest = keys[max(range(3), key=lambda i: lengths[i])]
            if longest not in marked:
                marked.add(longest)
                added = True
        if not added:
            break
    return marked


def _split_marked(verts: list, faces: list, marked: set) -> list:
    """Apply the conforming bisection templates for one pass of marked edges."""
    mid: dict[tuple[int, int], int] = {}

    def midpoint(a: int, b: int) -> int:
        key = (a, b) if a < b else (b, a)
        got = mid.get(key)
        if got is None:
            ax, ay = verts[a]
            bx, by = verts[b]
            got = len(verts)
            verts.append(((ax + bx) * 0.5, (ay + by) * 0.5))
            mid[key] = got
        return got

    out: list = []
    for i0, i1, i2 in faces:
        e = [((i0, i1) if i0 < i1 else (i1, i0)) in marked,
             ((i1, i2) if i1 < i2 else (i2, i1)) in marked,
             ((i2, i0) if i2 < i0 else (i0, i2)) in marked]
        n = sum(e)
        if n == 0:
            out.append((i0, i1, i2))
        elif n == 3:
            m0, m1, m2 = midpoint(i0, i1), midpoint(i1, i2), midpoint(i2, i0)
            out += [(i0, m0, m2), (m0, i1, m1), (m2, m1, i2), (m0, m1, m2)]
        elif n == 1:
            if e[1]:
                i0, i1, i2 = i1, i2, i0
            elif e[2]:
                i0, i1, i2 = i2, i0, i1
            m = midpoint(i0, i1)
            out += [(i0, m, i2), (m, i1, i2)]
        else:
            if not e[1]:
                i0, i1, i2 = i2, i0, i1
            elif not e[2]:
                i0, i1, i2 = i1, i2, i0
            m0, m1 = midpoint(i0, i1), midpoint(i1, i2)
            ax, ay = verts[m0]
            bx, by = verts[i2]
            cx, cy = verts[m1]
            dx, dy = verts[i0]
            if (ax - bx) ** 2 + (ay - by) ** 2 <= (cx - dx) ** 2 + (cy - dy) ** 2:
                out += [(i0, m0, i2), (m0, m1, i2), (m0, i1, m1)]
            else:
                out += [(i0, m0, m1), (i0, m1, i2), (m0, i1, m1)]
    return out


def refine_to_terrain(verts_xy: np.ndarray, tris: np.ndarray, height_fn, *,
                      tol_m: float = 0.03, min_edge_m: float = 0.5, max_edge_m: float = 25.0,
                      max_passes: int = 14) -> tuple[np.ndarray, np.ndarray]:
    """Split triangles until the draped surface follows the ground to within ``tol_m``.

    Ear clipping a planimetric polygon gives triangles that are fine in plan and wrong in elevation:
    measured over two tiles the median edge is 0.5 m but the 99th percentile is 66 m and the longest
    is **306 m**, and sampling inside those triangles the draped mesh sits a 99th-percentile 145-208
    mm from the ground with an extreme of **4.0 m** -- a road hanging in the air or buried in it.

    Refining to a fixed edge length is the obvious fix and it is the wrong one: at a 4 m cap one
    Midtown tile came out at **8.1 million** top triangles and a 217 MB glTF, because a uniform cap
    spends the same density on a flat avenue as on a hillside.  The criterion here is the error
    itself.  An edge is split when the ground at its midpoint is further than ``tol_m`` from the
    straight line between its endpoints -- exactly the quantity the refinement exists to reduce -- so
    flat pavement stays coarse and only real grade gets subdivided.

    ``max_edge_m`` still caps the longest edge, because a triangle can be long and still have a
    midpoint error near zero by running along a contour, and such a triangle both shades badly and
    makes the skirt a poor approximation of the slab's side.  ``min_edge_m`` is the floor that
    guarantees termination: below the terrain's own 2 m sample spacing there is no more information
    to resolve.

    The bisection is conforming -- an edge is marked once, globally, so the two triangles sharing it
    are always split the same way -- which is what keeps the patch watertight and free of
    T-junctions.
    """
    verts = [(float(v[0]), float(v[1])) for v in np.asarray(verts_xy, dtype=np.float64)[:, :2]]
    faces = [(int(t[0]), int(t[1]), int(t[2])) for t in np.asarray(tris, dtype=np.int64)]
    zcache: dict[int, float] = {}

    def heights(idx: list[int]) -> None:
        want = [i for i in idx if i not in zcache]
        if not want:
            return
        xy = np.asarray([verts[i] for i in want], dtype=np.float64)
        z = height_fn(xy[:, 0], xy[:, 1])
        for i, zz in zip(want, np.asarray(z, dtype=np.float64)):
            zcache[i] = float(zz) if np.isfinite(zz) else np.nan

    min2, max2 = min_edge_m * min_edge_m, max_edge_m * max_edge_m
    for _ in range(max_passes):
        edges = {(a, b) if a < b else (b, a)
                 for f in faces for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))}
        edges = list(edges)
        heights([i for e in edges for i in e])
        ax = np.asarray([verts[a] for a, _ in edges], dtype=np.float64)
        bx = np.asarray([verts[b] for _, b in edges], dtype=np.float64)
        d2 = ((ax - bx) ** 2).sum(axis=1)
        long_enough = d2 > min2
        too_long = d2 > max2
        cand = np.nonzero(long_enough)[0]
        marked = {edges[i] for i in np.nonzero(too_long)[0]}
        if cand.size:
            mx = (ax[cand, 0] + bx[cand, 0]) * 0.5
            my = (ax[cand, 1] + bx[cand, 1]) * 0.5
            zm = np.asarray(height_fn(mx, my), dtype=np.float64)
            za = np.asarray([zcache[edges[i][0]] for i in cand], dtype=np.float64)
            zb = np.asarray([zcache[edges[i][1]] for i in cand], dtype=np.float64)
            err = np.abs(zm - 0.5 * (za + zb))
            for i in cand[np.nonzero(np.isfinite(err) & (err > tol_m))[0]]:
                marked.add(edges[i])
        if not marked:
            break
        marked = _propagate_longest_edge(verts, faces, marked)
        faces = _split_marked(verts, faces, marked)

    return (np.asarray(verts, dtype=np.float64),
            np.asarray(faces, dtype=np.int64).reshape(-1, 3))





def refine_to_max_edge(verts_xy: np.ndarray, tris: np.ndarray, max_edge_m: float,
                       max_passes: int = 24) -> tuple[np.ndarray, np.ndarray]:
    """Split triangles until no edge is longer than ``max_edge_m``, without leaving T-junctions.

    Draping a polygon on the terrain by lifting only its corners is wrong in proportion to how far
    apart those corners are, and the planimetric polygons are not small: measured over two tiles the
    median triangle edge out of ear clipping is 0.5 m but the 99th percentile is 66 m and the longest
    is **306 m**, a single flat triangle across a third of a tile.  Sampling inside those triangles,
    the mesh sits a median 2-6 mm from the ground it is draped on but the 99th percentile is
    145-208 mm and the extreme is **4.0 m** -- a road hanging in the air or buried, either way not
    drivable.

    The refinement is conforming longest-edge bisection: an edge is marked once, globally, so the two
    triangles that share it are always split the same way and the surface stays watertight.  The
    templates are the standard ones -- one marked edge splits a triangle in two, two in three, three
    in four -- and the pass repeats until nothing is left to mark.
    """
    verts = [tuple(map(float, v)) for v in np.asarray(verts_xy, dtype=np.float64)[:, :2]]
    faces = [tuple(int(i) for i in t) for t in np.asarray(tris, dtype=np.int64)]
    if max_edge_m <= 0.0:
        return np.asarray(verts, dtype=np.float64), np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    limit2 = max_edge_m * max_edge_m

    for _ in range(max_passes):
        mid: dict[tuple[int, int], int] = {}

        def midpoint(a: int, b: int) -> int:
            key = (a, b) if a < b else (b, a)
            got = mid.get(key)
            if got is None:
                ax, ay = verts[a]
                bx, by = verts[b]
                got = len(verts)
                verts.append(((ax + bx) * 0.5, (ay + by) * 0.5))
                mid[key] = got
            return got

        def long_edge(a: int, b: int) -> bool:
            ax, ay = verts[a]
            bx, by = verts[b]
            return (ax - bx) ** 2 + (ay - by) ** 2 > limit2

        marked = {(a, b) if a < b else (b, a)
                  for f in faces for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))
                  if long_edge(a, b)}
        if not marked:
            break

        out: list[tuple[int, int, int]] = []
        for i0, i1, i2 in faces:
            e = [((i0, i1) if i0 < i1 else (i1, i0)) in marked,
                 ((i1, i2) if i1 < i2 else (i2, i1)) in marked,
                 ((i2, i0) if i2 < i0 else (i0, i2)) in marked]
            n = sum(e)
            if n == 0:
                out.append((i0, i1, i2))
            elif n == 3:
                m0, m1, m2 = midpoint(i0, i1), midpoint(i1, i2), midpoint(i2, i0)
                out += [(i0, m0, m2), (m0, i1, m1), (m2, m1, i2), (m0, m1, m2)]
            elif n == 1:
                # Rotate so the marked edge is (i0, i1); the opposite corner is i2.
                if e[1]:
                    i0, i1, i2 = i1, i2, i0
                elif e[2]:
                    i0, i1, i2 = i2, i0, i1
                m = midpoint(i0, i1)
                out += [(i0, m, i2), (m, i1, i2)]
            else:
                # Rotate so the unmarked edge is (i2, i0); (i0,i1) and (i1,i2) are marked.
                if not e[1]:
                    i0, i1, i2 = i2, i0, i1
                elif not e[2]:
                    i0, i1, i2 = i1, i2, i0
                m0, m1 = midpoint(i0, i1), midpoint(i1, i2)
                # Split the quad (i0, m0, m1, i2) along its shorter diagonal, which keeps the worse
                # of the two resulting aspect ratios lower than picking a fixed one.
                ax, ay = verts[m0]
                bx, by = verts[i2]
                cx, cy = verts[m1]
                dx, dy = verts[i0]
                if (ax - bx) ** 2 + (ay - by) ** 2 <= (cx - dx) ** 2 + (cy - dy) ** 2:
                    out += [(i0, m0, i2), (m0, m1, i2), (m0, i1, m1)]
                else:
                    out += [(i0, m0, m1), (i0, m1, i2), (m0, i1, m1)]
        faces = out

    return (np.asarray(verts, dtype=np.float64),
            np.asarray(faces, dtype=np.int64).reshape(-1, 3))


# --------------------------------------------------------------------------- one slab


@dataclass
class SlabBuffer:
    """Accumulates the triangles of one (kind, surface) group for a tile."""

    kind: int
    surface: int
    verts: list = field(default_factory=list)      # (x, y, z), tile-local x/y, absolute z
    faces: list = field(default_factory=list)
    is_top: list = field(default_factory=list)     # per face: True for the surface, False for a wall
    #: Per face: the index of the centreline it was draped on, or -1 for the ground. An index rather
    #: than a flag, because a check that measures a face against *a* nearby road instead of *its own*
    #: reports a 13 m error wherever two decks stack - which is a fact about the check.
    road_line: list = field(default_factory=list)
    polygons: int = 0
    top_triangles: int = 0
    skirt_triangles: int = 0

    def add_polygon(self, pts_local: np.ndarray, z_top: np.ndarray, tris: np.ndarray,
                    skirt_depth: float, *, road_line: int = -1) -> None:
        """Append one refined polygon's top surface and, when ``skirt_depth`` > 0, its walls.

        The walls are raised on the boundary of the *refined* triangulation rather than on the
        polygon's original rings, because refinement puts vertices on ring edges that the rings never
        had; hanging the skirt on the old rings would leave the wall's top edge cutting across those
        new vertices and the slab would not be closed.
        """
        base = len(self.verts)
        pts = np.asarray(pts_local, dtype=np.float64)
        self.verts.extend((float(pts[i, 0]), float(pts[i, 1]), float(z_top[i]))
                          for i in range(len(pts)))
        for a, b, c in np.asarray(tris, dtype=np.int64):
            self.faces.append((base + int(a), base + int(b), base + int(c)))
            self.is_top.append(True)
            self.road_line.append(road_line)
        self.top_triangles += len(tris)
        self.polygons += 1
        if skirt_depth <= 0.0:
            return
        for loop in boundary_loops(tris):
            bottom = len(self.verts)
            self.verts.extend((float(pts[i, 0]), float(pts[i, 1]), float(z_top[i] - skirt_depth))
                              for i in loop)
            n = len(loop)
            for i in range(n):
                ta, tb = base + loop[i], base + loop[(i + 1) % n]
                ba, bb = bottom + i, bottom + (i + 1) % n
                self.faces.append((ta, ba, bb))
                self.faces.append((ta, bb, tb))
                self.is_top.append(False)
                self.is_top.append(False)
                self.road_line.append(road_line)
                self.road_line.append(road_line)
                self.skirt_triangles += 2


def orient_ring(coords: np.ndarray, ccw: bool) -> np.ndarray:
    """Return ``coords`` wound counter-clockwise (``ccw``) or clockwise, by signed area.

    The top faces up only when the exterior is counter-clockwise, and the skirt of a ring faces the
    material's outside only when its winding matches: exterior counter-clockwise, holes clockwise.
    """
    c = np.asarray(coords, dtype=np.float64)
    x, y = c[:, 0], c[:, 1]
    area2 = float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return c if (area2 > 0.0) == ccw else c[::-1].copy()


# --------------------------------------------------------------------------- the carriageway's own height


class RoadSurface:
    """Elevation of the carriageway taken from the road network rather than from the ground under it.

    A planimetric roadbed polygon is a plan view with no elevation, and draping it on the DEM puts
    every grade-separated road on whatever happens to be beneath it. Measured over the paved area of
    one Lower Manhattan tile, **48.2 %** of it sits on polygons that span more than two metres of
    terrain -- against 3.0 % in Midtown -- with a maximum span of 12.6 m. That is the FDR Drive, the
    Battery Tunnel portals and the Brooklyn Bridge approaches being drawn on the street below them.

    The road network already knows better. ``roads/segments.parquet`` carries a **3D** LineString per
    segment, with ``z_source`` saying whether the elevation came from the terrain (0), from a
    constant CSCL level (1) or from a ramp interpolation (2); 7,962 of 122,235 segments are not at
    grade. Taking the carriageway's height from the nearest segment puts an elevated road at the
    height it is, and has the second effect of making the surface smooth: the refinement stops
    subdividing to chase a cliff that the road does not actually cross.

    Points with no segment within ``max_dist_m`` come back as NaN, and the caller falls back to the
    ground - which is the right answer for a car park or a plaza.
    """

    #: How near a polygon's own point must be to a grade-separated centreline before that centreline
    #: is taken to describe it. A viaduct deck is 15-25 m wide, so its roadbed polygon is within this
    #: of its own centreline; the street underneath usually is not. Combined with the z_source test
    #: below it is what keeps a road *under* an elevated one from being lifted onto it.
    ELEVATED_DIST_M = 12.0

    def __init__(self, segments_parquet, bounds, *, margin_m: float = 60.0, max_dist_m: float = 22.0):
        import pyarrow.parquet as pq
        import shapely

        self.max_dist_m = float(max_dist_m)
        self.lines: list = []
        self.z_source: list = []
        self.reason = ""
        self._tree = None
        try:
            table = pq.read_table(segments_parquet, columns=["geometry", "z_source"])
        except Exception as exc:  # noqa: BLE001
            self.reason = f"segments unreadable: {exc}"
            return
        x0, y0, x1, y1 = bounds
        box = shapely.box(x0 - margin_m, y0 - margin_m, x1 + margin_m, y1 + margin_m)
        geoms = shapely.from_wkb(table.column("geometry").to_numpy(zero_copy_only=False))
        sources = table.column("z_source").to_pylist()
        keep = shapely.intersects(geoms, box)
        for g, src, k in zip(geoms, sources, keep):
            if k and g is not None and g.geom_type == "LineString" and g.has_z:
                self.lines.append(g)
                self.z_source.append(int(src))
        if not self.lines:
            self.reason = "no 3D road segment near this tile"
            return
        self._tree = shapely.STRtree(self.lines)

    @property
    def ok(self) -> bool:
        return self._tree is not None

    def line_for(self, poly):
        """The one centreline that describes this polygon, or ``None``.

        One line for the whole polygon, not the nearest line to each point. A per-point lookup makes
        the height field discontinuous wherever two decks at different heights pass close to each
        other -- adjacent vertices snap to different roads and the surface tears. Measured, that left
        a 2.5 m 99th-percentile difference between the shipped surface and the road it was supposed
        to be on, inside polygons that were otherwise correct.
        """
        import shapely

        if self._tree is None:
            return None
        point = poly.representative_point()
        found = self._tree.query_nearest(point, max_distance=self.ELEVATED_DIST_M,
                                         return_distance=False, all_matches=False)
        idx = np.atleast_1d(np.asarray(found)).ravel()
        if idx.size == 0:
            return None
        j = int(idx[-1])
        return j if self.z_source[j] != 0 else None

    def height_on(self, j: int):
        """A height function bound to one centreline: continuous, and defined everywhere.

        ``line_locate_point`` clamps beyond the ends, so a deck that runs past the last centreline
        vertex keeps that vertex's elevation rather than falling to the ground.
        """
        import shapely

        line = self.lines[j]

        def height(x, y):
            x = np.atleast_1d(np.asarray(x, dtype=np.float64))
            y = np.atleast_1d(np.asarray(y, dtype=np.float64))
            pts = shapely.points(x.ravel(), y.ravel())
            s_along = shapely.line_locate_point(line, pts)
            got = shapely.line_interpolate_point(line, s_along)
            return np.asarray(shapely.get_z(got), dtype=np.float64).reshape(x.shape)

        return height

    def is_elevated(self, poly) -> bool:
        """True when the nearest centreline to this polygon is one the network says is not at grade.

        The rule is deliberately narrow. At-grade segments carry ``z_source == 0``, meaning their
        elevation came from the terrain in the first place, and over one Lower Manhattan tile the
        median difference between road z and ground z is **0.00 m** -- so using the road there would
        change nothing and can only introduce a way to be wrong. Only where the network says a
        segment is a constant level (1) or a ramp (2) is the ground beneath it the wrong answer.
        """
        import shapely

        if self._tree is None:
            return False
        point = poly.representative_point()
        found = self._tree.query_nearest(point, max_distance=self.ELEVATED_DIST_M,
                                         return_distance=False, all_matches=False)
        idx = np.atleast_1d(np.asarray(found)).ravel()
        if idx.size == 0:
            return False
        return self.z_source[int(idx[-1])] != 0

    def height(self, x, y):
        """Carriageway elevation at each point, NaN where no segment is within ``max_dist_m``."""
        import shapely

        x = np.atleast_1d(np.asarray(x, dtype=np.float64))
        y = np.atleast_1d(np.asarray(y, dtype=np.float64))
        out = np.full(x.shape, np.nan, dtype=np.float64)
        if self._tree is None or x.size == 0:
            return out
        pts = shapely.points(x.ravel(), y.ravel())
        found = self._tree.query_nearest(pts, max_distance=self.max_dist_m, return_distance=False,
                                         all_matches=False)
        if found.size == 0:
            return out
        src, dst = found[0], found[1]
        flat = out.ravel()
        # Project each point onto its nearest segment and read the z the network already interpolated
        # along it; a 3D interpolate on a 3D LineString carries the elevation through.
        for i, j in zip(src, dst):
            line = self.lines[j]
            s = shapely.line_locate_point(line, pts[i])
            p = shapely.line_interpolate_point(line, s)
            z = shapely.get_z(p)
            if np.isfinite(z):
                flat[i] = float(z)
        return out
