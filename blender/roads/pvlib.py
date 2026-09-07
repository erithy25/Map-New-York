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
    polygons: int = 0
    top_triangles: int = 0
    skirt_triangles: int = 0

    def add_polygon(self, pts_local: np.ndarray, z_top: np.ndarray, tris: np.ndarray,
                    skirt_depth: float) -> None:
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
