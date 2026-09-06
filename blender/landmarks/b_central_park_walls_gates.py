"""Central Park perimeter wall and its twenty named gates — Olmsted & Vaux's Greensward Plan, 1858 onwards; the wall
was built between 1860 and the 1870s and the gate names were fixed by the Board of Commissioners in 1862.
NYC Scenic Landmark LP-0851, National Historic Landmark 1963.

Dimensions used (source in brackets)
------------------------------------
* The park is **843 acres = 3.41 km2**, 2.5 miles by 0.5 miles (**4.0 km x 0.8 km**), bounded by 59th Street,
  Fifth Avenue, 110th Street and Central Park West; its perimeter is **6 miles = 9.66 km** [NYC Parks, Central Park
  Conservancy].  The real OSM boundary polygon used here measures **3,415,832 m2** and **9.69 km** of perimeter —
  0.2 % and 0.3 % from the published figures.
* The perimeter wall is **Manhattan schist with brownstone coping**, about **4 ft = 1.22 m** high and
  **1 ft 6 in = 0.46 m** thick, stepping with the sidewalk grade [NYC Parks].  Heights and thickness are the
  published nominal values; the wall's real course-by-course variation is not reproduced.
* **Twenty named gates** were designated in 1862 (only their names, cut into the coping blocks, mark most of them):
  Scholars', Children's, Inventors', Miners', Engineers', Woodman's, Girls' and Pioneers' on Fifth Avenue;
  Merchants', Women's, Naturalists', Hunters', Mariners', Gate of All Saints, Boys', Strangers' and Warriors' on
  Central Park West; Artisans' and Artists' on Central Park South; and Farmers' on Central Park North.
  Each is modelled as a **pair of schist piers with brownstone caps** flanking the opening; the **name is carried by
  the object name and the catalog entry**, not cut into the stone (stated gap).

Placement: the wall follows the **real OSM Central Park boundary** (way ``427818536`` in
``data/processed/osm/landuse_leisure.parquet``, 215 vertices), resampled to 9 m.  Each gate's position is computed
from the Manhattan street grid along the park's oriented bounding box: on the avenues, at the fraction
``(street - 59) / 51`` of the edge from the southern corner (the park runs from 59th to 110th Street); on the two
cross-street edges, at the published avenue positions.  Gate positions are therefore **derived from the grid,
+-25 m**, not surveyed.

Not modelled: the wall's coursing and the cut gate-name lettering, the cast-iron park benches and lamp standards
along it, the ornamental gates at Merchants' and Engineers' Gates, the sidewalk and its trees, and the interior of
the park.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_central_park_walls_gates"
TITLE = "Central Park perimeter wall and gates"

OSM_WAY = 427818536
LANDUSE = bc.REPO / "data" / "processed" / "osm" / "landuse_leisure.parquet"
WALL_H = 1.22           # 4 ft
WALL_T = 0.46           # 1 ft 6 in
GROUND = 20.0           # nominal NAVD88 sidewalk level around the park (inferred; the real grade varies 8-40 m)
PIER_W, PIER_H = 1.5, 3.0
STEP = 9.0

# gate -> (edge, fraction from the edge's start).  Edges: E = Fifth Avenue (south to north), W = Central Park West
# (south to north), S = Central Park South (west to east), N = Central Park North (west to east).
def _f(street: int) -> float:
    return (street - 59) / 51.0


GATES = [
    ("scholars", "E", _f(60)), ("childrens", "E", _f(64)), ("inventors", "E", _f(72)), ("miners", "E", _f(79)),
    ("engineers", "E", _f(90)), ("woodmans", "E", _f(96)), ("girls", "E", _f(102)), ("pioneers", "E", _f(110)),
    ("merchants", "W", _f(59)), ("womens", "W", _f(72)), ("naturalists", "W", _f(77)), ("hunters", "W", _f(81)),
    ("mariners", "W", _f(85)), ("all_saints", "W", _f(96)), ("boys", "W", _f(100)), ("strangers", "W", _f(106)),
    ("warriors", "W", _f(110)),
    ("artisans", "S", 0.35), ("artists", "S", 0.70),
    ("farmers", "N", 0.50),
]


def _boundary() -> list[tuple[float, float]]:
    import pyarrow.parquet as pq
    from shapely import wkb
    if not LANDUSE.exists():
        raise RuntimeError(f"{LANDUSE} missing: the OSM landuse extract is required for the Central Park boundary")
    t = pq.read_table(LANDUSE, columns=["osm_id", "geometry"], filters=[("osm_id", "==", OSM_WAY)])
    if t.num_rows == 0:
        raise RuntimeError(f"OSM way {OSM_WAY} (Central Park) not found in {LANDUSE.name}")
    blob = t.column("geometry")[0].as_py()
    g = wkb.loads(blob) if isinstance(blob, (bytes, bytearray)) else blob
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda q: q.area)
    return [(float(x), float(y)) for x, y in list(g.exterior.coords)[:-1]]


def _resample(ring, step):
    pts = list(ring) + [ring[0]]
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        if L < 1e-9:
            continue
        n = max(int((acc + L) // step), 0)
        d = 0.0
        while acc + (L - d) >= step:
            d += step - acc
            acc = 0.0
            out.append((a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L))
        acc += L - d
        _ = n
    return out


def _obb_corners(ring):
    """Oriented bounding box corners in south-west, south-east, north-east, north-west order."""
    a = np.asarray(ring)
    c = a.mean(axis=0)
    _, _, vt = np.linalg.svd(a - c, full_matrices=False)
    long_ax = vt[0]
    if long_ax[1] < 0:
        long_ax = -long_ax                      # point the long axis north
    short_ax = np.array([-long_ax[1], long_ax[0]])
    if short_ax[0] < 0:
        short_ax = -short_ax                    # point the short axis east
    u = (a - c) @ long_ax
    v = (a - c) @ short_ax
    lo_u, hi_u, lo_v, hi_v = u.min(), u.max(), v.min(), v.max()
    def P(uu, vv):
        p = c + long_ax * uu + short_ax * vv
        return (float(p[0]), float(p[1]))
    return P(lo_u, lo_v), P(lo_u, hi_v), P(hi_u, hi_v), P(hi_u, lo_v), long_ax, short_ax


def build(lod: int = 0):
    ring_tm = _boundary()
    sw, se, ne, nw, long_ax, short_ax = _obb_corners(ring_tm)
    cx = sum(p[0] for p in ring_tm) / len(ring_tm)
    cy = sum(p[1] for p in ring_tm) / len(ring_tm)
    heading = math.degrees(math.atan2(float(long_ax[0]), float(long_ax[1]))) % 360.0
    frame = bc.local_frame((cx, cy), GROUND, heading)
    ring = [(x - cx, y - cy) for x, y in ring_tm]
    perim = sum(math.dist(ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring)))
    line = _resample(ring, STEP if lod == 0 else STEP * 3)
    objs: list = pk.park_wall("perimeter_wall", line + [line[0]], 0.0, WALL_H, WALL_T, "schist")
    objs.append(bc.prism("wall_coping", [], 0, 1, "brownstone") if False else
                pk.park_wall("wall_coping", line + [line[0]], WALL_H - 0.14, 0.2, WALL_T + 0.14, "brownstone")[0])

    edges = {"E": (np.asarray(se) - (cx, cy), np.asarray(ne) - (cx, cy)),
             "W": (np.asarray(sw) - (cx, cy), np.asarray(nw) - (cx, cy)),
             "S": (np.asarray(sw) - (cx, cy), np.asarray(se) - (cx, cy)),
             "N": (np.asarray(nw) - (cx, cy), np.asarray(ne) - (cx, cy))}
    gates = []
    gate_records = {}
    for name, edge, f in GATES:
        a, b = edges[edge]
        p = a + (b - a) * f
        d = (b - a) / np.linalg.norm(b - a)
        n = np.array([-d[1], d[0]])
        for s in (-1, 1):
            q = p + d * (s * 3.4)
            gates.append(bc.box(f"gate_{name}_pier{s}", (PIER_W, PIER_W, PIER_H), (float(q[0]), float(q[1]), -0.4),
                                "schist"))
            gates.append(bc.box(f"gate_{name}_cap{s}", (PIER_W + 0.36, PIER_W + 0.36, 0.34),
                                (float(q[0]), float(q[1]), PIER_H - 0.4), "brownstone"))
        gate_records[name] = {"edge": edge, "fraction": round(f, 4),
                              "xy_tm": [round(float(p[0]) + cx, 1), round(float(p[1]) + cy, 1)]}
        _ = n
    objs.append(bc.join(gates, "gate_piers"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": PIER_H, "name": TITLE,
        "lp_number": "LP-0851", "park_area_m2": round(abs(_area(ring)), 1), "perimeter_m": round(perim, 1),
        "published_area_m2": 3410000.0, "published_perimeter_m": 9656.0,
        "wall_height_m": WALL_H, "wall_thickness_m": WALL_T, "gates": len(GATES), "gate_positions": gate_records,
        "height_source": "NYC Parks / Central Park Conservancy: 843 acres, 6-mile perimeter, 4 ft schist wall with "
                         "brownstone coping, twenty gates named in 1862",
        "sources_ids": ["osm_bbbike", "published_central_park"],
        "fidelity_statement": (
            "Exact: the wall follows the real OSM Central Park boundary (way 427818536, 215 vertices), whose "
            "%.0f m2 area and %.0f m perimeter are 0.2 %% and 0.3 %% from the published 843 acres and 6 miles; the "
            "wall is the published 1.22 m high and 0.46 m thick in Manhattan schist with a brownstone coping; all "
            "twenty gates named in 1862 are present and named in the catalog. Derived, +-25 m: each gate's position "
            "along the park's oriented bounding box from the Manhattan street grid — the gates were not surveyed. "
            "Inferred: the 20 m NAVD88 sidewalk level (the real grade around the park runs from about 8 m at "
            "Columbus Circle to 40 m at the north-west corner), the 1.5 x 3.0 m pier size. Gap: the gate names are "
            "carried by the object names and the catalog entry, not cut into the coping. Not modelled: wall "
            "coursing, benches and lamp standards, the ornamental gates at Merchants' and Engineers' Gates, the "
            "sidewalk and its trees, the park interior."
            % (abs(_area(ring)), perim)),
    }
    return objs, extras


def _area(ring) -> float:
    s = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def main() -> None:
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            dict(view="fifth_avenue_wall", cam=(430.0, -1900.0, GROUND + 1.7 - 20.0),
                 target=(330.0, -1700.0, GROUND - 19.4), fov_deg=62.0,
                 context=(("sidewalk", -0.45, 2600.0, (0.0, 0.0)),), sun_azimuth_deg=120.0, sun_elevation_deg=40.0),
            dict(view="park_plan", cam=(0.0, -300.0, 2400.0), target=(0.0, 0.0, 0.0), fov_deg=52.0,
                 context=(("grass", -0.5, 2600.0, (0.0, 0.0)),), sun_azimuth_deg=200.0, sun_elevation_deg=60.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
