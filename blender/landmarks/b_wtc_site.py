"""World Trade Center site — the 6.5 ha superblock bounded by Vesey, Church, Liberty and West Streets: the Oculus
(WTC Transportation Hub), 3, 4 and 7 World Trade Center, the National September 11 Memorial's twin reflecting pools
and the memorial museum pavilion, and the plaza's swamp white oaks.  (One World Trade Center is a separate landmark,
``b_one_world_trade_center``.)

Dimensions used (source in brackets)
------------------------------------
* **Oculus** (Santiago Calatrava, WTC Transportation Hub, opened 4 March 2016): the arched elliptical body is
  **350 ft = 106.7 m long**, **115 ft = 35.1 m wide** at its widest, and rises **96 ft = 29.3 m above grade at the
  apex**; the structural steel ribs continue upward as a pair of canopies reaching **168 ft = 51.2 m above grade**;
  between the two 350 ft arches a **330 ft = 100.6 m operable skylight** runs the length of the building; the
  concourse is column-free and 11,500 tons of structural steel were used [Calatrava, PANYNJ, explorewtc.com].
  This model builds **2 x 56 = 112 ribs** — the rib count is *inferred* from the published 350 ft length and the
  photographed rib pitch (about 1.9 m), not from a published figure.  The body's **long axis is measured from its
  own footprint** (BIN 1089309) at build time, not assumed: the minimum rotated rectangle of that polygon is
  110.0 x 33.3 m with its long edge on **128.2 deg**, and an area-weighted principal axis of the same polygon gives
  128.8 deg.
* **3 World Trade Center** (Rogers Stirk Harbour, 2018): **329.2 m** (1,079 ft), 80 storeys; **4 World Trade Center**
  (Maki, 2013): **297.7 m** (977 ft), 72 storeys; **7 World Trade Center** (SOM, 2006): **226.1 m** (741.7 ft), 52
  storeys, a parallelogram plan over a Con Edison substation podium.
* **National September 11 Memorial** (Michael Arad / Peter Walker, 2011): **two pools, each set in the 200 ft =
  61.0 m footprint of one of the original towers**, "each pool nearly an acre"; the water falls **9.1 m (30 ft)**
  down the pool walls to a second, smaller void; the names of the **2,983 victims are inscribed on 152 bronze
  parapets** around the pools.  The parapets carry the material slot ``MEMORIAL_NAMES`` so the engine can drive the
  incised-name texture.  The **plaza is cut open over both pools** — a plaza built as one unbroken surface hides
  them from every camera standing on it, which is the one thing the memorial views have to show.
* **Plaza trees**: more than **400 swamp white oaks** (*Quercus bicolor*) and one Callery pear (the Survivor Tree).
  The trees come from the street-props agent's library in ``blender_out/props/``.  That library has no swamp white
  oak, so ``tree_pin_oak_medium`` (*Quercus palustris*, same genus, same upright habit) stands in — **a stated
  species substitution** — collapse-decimated to 520 triangles and instanced, so 220 trees cost one mesh in the glb.
  The Survivor Tree is a Callery pear and uses ``tree_callery_pear_medium``, which is the right species.  The prop
  is 18.4 m tall and is scaled to the 11 m canopy the memorial oaks stand at today.  **220 oaks** are placed, not
  the published 400+: a 7.3 m grid on the pools' own axis, clipped to the plaza deck 4 m in from its edge and clear
  of the two openings and the museum pavilion, leaves 387 standing places, and 220 of them are drawn with a fixed
  seed so the grove covers the whole plaza instead of filling one end of it.  If the props library is absent the
  build falls back to ``b_common.simple_tree`` and the report says so.

Placement: every building uses its **real OTI footprint**: 3 WTC BIN **1088797** (5,292 m2, LiDAR height 324.3 m),
4 WTC BIN **1088795** (4,573 m2, 298.2 m), 7 WTC BIN **1086510** (3,019 m2, 226.7 m), the Oculus BIN **1089309**
(2,897 m2) and the memorial museum pavilion BIN **1088798** (1,382 m2).  Those areas are the NYC_TM polygons' own,
measured here; the source table's ``shape_area`` column reads 1.744x the polygon area for every row sampled from it,
so it is not in square metres and the figures quoted before this pass mixed the two.  The two pool centres and the pool squares'
rotation are **measured**, from OSM ways ``697722178`` ("Memorial North Pool") and ``697722181`` ("Memorial South
Pool") in ``data/raw/osm/NewYork.osm.pbf``.  The memorial plaza's outline is OSM way ``129835611``.

Plaza elevation
---------------
The frame origin's z is the **NAVD88 elevation of the plaza**, 4.40 m, and the plaza is 0.0 in model space.  These
were one constant (``GRND = 3.5``, used both as the local datum and as the frame origin's NAVD88 z), so
``blender/verify/scene.py``'s ``world = local + origin`` counted the plaza level twice and put the plaza at 7.00 m
NAVD88 — about 2.6 m above the ground the site stands on, high enough that the memorial-plaza camera had to be
lifted onto the model's own deck.  4.40 m is what the published terrain reads at ``PLAZA_CENTRE_TM``; the deck of
the memorial plaza (OSM way 129835611 minus the two pool squares) has a median of 4.34 m over 6,139 samples at 2 m,
and the streets the plaza meets read 4.56 m along its Greenwich Street frontage, 4.88 m on Fulton Street and 3.47 m
on Liberty Street, which the plaza stands above (as it does in reality, up the steps from Liberty Street).  Across
the 93 landmark catalogue entries the median |origin z - terrain| is 0.072 m; this model was 0.905 m out even
before the doubling.

Not modelled: the below-grade PATH platforms, the memorial museum's underground galleries (only the pavilion above
grade is built), 2 World Trade Center (never built above the below-grade box), the Liberty Park elevated garden and
St Nicholas Greek Orthodox Church, the individual curtain-wall panes, and the Oculus's marble interior floor.  The
ground beyond the memorial plaza is the terrain and pavement stages' work, not this model's: the plaza is the real
8-acre memorial plaza and stops there, where it used to be a 520 x 520 m quad reaching a quarter of a kilometre
past the site and standing over Liberty Street and the Hudson River Greenway.

Axes
----
One constant, ``PLAZA_AXIS_DEG = 160.6``, used to orient the Oculus, carry the frame's informational heading and
aim the Oculus verification cameras.  It measured none of those things.  160.6 deg is the heading of the line
between the two *derived* pool centres the earlier build placed at local (-28.23, 80.17) and (28.23, -80.17) — a
figure the pool correction replaced with measured centres whose line runs 176.3 deg — so after that correction
nothing in this model had that axis.  It is now three separate things, each measured:

* ``OCULUS_AXIS_DEG`` — the Oculus's long axis, **taken from BIN 1089309's own footprint at build time** and
  cross-checked against the recorded 128.2 deg.  At 160.6 deg the modelled body stood 32.4 deg off its footprint:
  only 58 % of its plan lay over BIN 1089309 (IoU 0.41), both ends of the 106.7 m body were about 17 m outside that
  footprint, and the south-east end sat **inside 3 WTC's footprint** (231 m2 of the base prism overlapped it).
  On the measured axis 94 % of the body lies over its own footprint (IoU 0.90) and it overlaps neither 3 WTC nor
  4 WTC at all.
* ``SITE_AXIS_DEG`` — the frame's informational ``heading_deg``: the original towers' grid, which is what the
  memorial pools, 3 WTC and 4 WTC all stand on (pool square edges 29.2 deg measured from OSM ways 697722178 /
  697722181; 3 WTC's footprint 26.5 deg, 4 WTC's 29.4 deg).  The memorial plaza polygon has no usable axis of its
  own — its minimum rotated rectangle runs 15.5 deg while its area-weighted principal axis runs 172.0 deg, 23 deg
  apart, because the plaza is not a rectangle.
* the pools keep ``POOL_AXIS_DEG``, measured, which they already did.
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

ID = "b_wtc_site"
TITLE = "World Trade Center site"
BINS = [1088797, 1088795, 1086510, 1089309, 1088798]

WTC3_M, WTC4_M, WTC7_M = 329.2, 297.7, 226.1
OCULUS_L, OCULUS_W, OCULUS_APEX, OCULUS_TIP = 106.7, 35.1, 29.3, 51.2
SKYLIGHT_L = 100.6
N_RIBS_PER_SIDE = 56
POOL_SIDE = 61.0
POOL_FALL = 9.14
N_NAMES = 2983
N_PARAPETS = 152
OAK_GRID = 7.3
OAK_H_M = 11.0                      # canopy height of the memorial oaks today (photographs; planted at ~8 m)
OAK_PROP = "tree_pin_oak_medium"    # blender_out/props/: closest species in the library to Quercus bicolor
OAK_PROP_H = 18.4                   # measured from the prop's glTF accessor bounds
PEAR_PROP = "tree_callery_pear_medium"   # the Survivor Tree is a Callery pear (Pyrus calleryana)
PEAR_PROP_H = 9.31
SURVIVOR_TREE_INDEX = 96            # one tree of the grid stands in for the Survivor Tree
PLAZA_CENTRE_TM = (-5338.0, 1285.0)

#: The Oculus's long axis, compass degrees.  Recorded from BIN 1089309's own OTI footprint -- minimum rotated
#: rectangle 110.0 x 33.3 m with its long edge on 128.21 deg, area-weighted principal axis 128.79 deg -- and
#: re-derived from that same polygon at build time by :func:`_oculus`, which warns if the two disagree.  See the
#: "Axes" note in the module docstring for what the 160.6 deg this replaces actually was.
OCULUS_AXIS_DEG = 128.2

# The two pools, measured rather than derived.  ``data/raw/osm/NewYork.osm.pbf`` (BBBike, ODbL, (c) OpenStreetMap
# contributors) carries **way 697722178 "Memorial North Pool"** and **way 697722181 "Memorial South Pool"**, both
# five-node squares tagged ``natural=water``.  Their centroids in NYC_TM are recorded here (the extract this lane
# publishes keeps buildings and structures, not water, so there is nothing to cross-check against on disk).  Their
# edges run 29.25 / 119.06 deg, which is the original towers' grid and agrees with the real OTI footprints of
# 3 WTC (26.5 / 116.5 deg) and 4 WTC (29.4 / 119.4 deg); the centres are 123.5 m apart.
POOL_CENTRES_TM = ((-5338.35, 1349.96), (-5330.40, 1226.73))    # north, south
POOL_AXIS_DEG = 29.2                # heading of a pool square's edges

#: The site's principal axis, exported as the catalogue's informational ``heading_deg``: the original towers' grid,
#: which the pools stand on and which 3 WTC (26.5 deg) and 4 WTC (29.4 deg) are built to.  It is the pools' measured
#: edge heading, so it is one measurement rather than a second constant.
SITE_AXIS_DEG = POOL_AXIS_DEG

# Two different things that must not be the same constant.  ``PLAZA_Z`` is the frame origin's NAVD88 elevation --
# what the catalogue exports as ``origin_tm[2]`` and what blender/verify/scene.py adds to every vertex when it
# places the model (world z = local z + origin z).  ``GRND`` is the plaza *in model space*, the local datum every
# offset below is measured from.  Holding both in one constant counted the plaza level twice and stood the whole
# model 3.5 m above the ground it sits on.
PLAZA_Z = 4.40                      # see the "Plaza elevation" note in the module docstring
GRND = 0.0                          # plaza level in model space; every GRND +- x below is an offset from it

PLAZA_OSM_WAY = 129835611           # OSM way for the memorial plaza (ODbL, (c) OpenStreetMap contributors)
PLAZA_POOL_APRON = 3.0              # deck kept around each pool opening so a derived centre cannot leave it hanging
PLAZA_SLAB = 0.30                   # paving slab thickness, so the opening has a visible edge from inside the pool
OAK_EDGE_CLEAR = 4.0                # no oak within this of the plaza edge
OAK_POOL_CLEAR = 4.0                # ... or of a pool opening
OAK_BUILDING_CLEAR = 3.0            # ... or of the museum pavilion

#: The memorial plaza's real outline: **OSM way 129835611** in NYC_TM metres, Douglas-Peucker simplified at 0.5 m
#: (76 -> 20 vertices; 33,046 m2 against the full polygon's 33,019 m2 and the published "eight acres" = 32,375 m2).
#: Recorded as a constant so the model rebuilds without the extract, exactly as the bridge supports are;
#: :func:`_plaza_ring` cross-checks it against ``blender_out/landmarks/b_osm/structures.geojson`` when that file is
#: on disk and logs the disagreement.
PLAZA_RING_TM = [
    (-5400.6, 1426.0), (-5399.0, 1427.5), (-5397.2, 1427.3), (-5248.1, 1344.7), (-5245.1, 1341.8),
    (-5245.1, 1339.8), (-5278.5, 1221.4), (-5298.6, 1146.8), (-5300.3, 1143.7), (-5301.5, 1143.0),
    (-5305.6, 1142.7), (-5307.8, 1143.5), (-5316.7, 1148.6), (-5345.6, 1167.7), (-5391.7, 1201.7),
    (-5429.1, 1224.2), (-5430.8, 1225.9), (-5430.6, 1232.3), (-5422.6, 1294.6), (-5417.9, 1327.1),
]


def _pool_centres(frame):
    """North and south pool centres in frame coordinates, and the unit vector their square edges run along.

    Both come from the measured OSM ways recorded in :data:`POOL_CENTRES_TM` / :data:`POOL_AXIS_DEG`; the grove's
    grid is laid out on the same axis, because the memorial's oaks stand on the site grid the pools do.
    """
    a = math.radians(bc.heading_to_math_deg(POOL_AXIS_DEG))
    d = Vector((math.cos(a), math.sin(a), 0.0))
    out = []
    for cx, cy in POOL_CENTRES_TM:
        lx, ly, _ = frame.to_local(cx, cy)
        out.append(Vector((lx, ly, 0.0)))
    return out[0], out[1], d


def _pool_rings(centre: Vector, d: Vector):
    """The three concentric squares one memorial pool is built from, in frame coordinates.

    ``outer`` is the published 61.0 m edge: it is the parapet's outer face *and* the opening cut in the plaza, so
    the parapet stands on the edge of the opening as it does in reality.  ``inner`` is where the waterfall starts,
    ``void`` the central square the water falls into a second time.
    """
    n = Vector((-d.y, d.x, 0.0))
    h = POOL_SIDE / 2

    def ring(r):
        return [(centre.x + d.x * (r * a) + n.x * (r * b), centre.y + d.y * (r * a) + n.y * (r * b))
                for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    return ring(h), ring(h - 2.2), ring(h * 0.29)


def _plaza_ring(frame) -> list[tuple[float, float]]:
    """The memorial plaza outline in frame coordinates, CCW, cross-checked against the OSM extract.

    The recorded constant is what the model is built from, so a rebuild does not depend on another agent's
    output; when ``b_osm/structures.geojson`` is on disk the two are compared and the disagreement is logged,
    which is the same recorded-constant-plus-cross-check the bridge supports use.
    """
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    poly = orient(Polygon(PLAZA_RING_TM), sign=1.0)
    src = bc.OUT / "b_osm" / "structures.geojson"
    if src.is_file():
        try:
            doc = json.loads(src.read_text())
            feat = next(f for f in doc["features"] if f["properties"].get("osm_id") == PLAZA_OSM_WAY)
            co = feat["geometry"]["coordinates"]
            while isinstance(co[0][0], list):
                co = co[0]
            osm = Polygon([tuple(float(v) for v in bc.lonlat_to_tm(lon, lat)) for lon, lat in co])
            dev = poly.exterior.hausdorff_distance(osm.exterior)
            bc.log.info("memorial plaza outline: recorded constant %.0f m2 vs OSM way %d %.0f m2, "
                        "Hausdorff %.2f m", poly.area, PLAZA_OSM_WAY, osm.area, dev)
            if dev > 3.0:
                bc.log.warning("memorial plaza outline: recorded constant disagrees with OSM way %d by %.1f m; "
                               "the constant is used, re-record it from the extract", PLAZA_OSM_WAY, dev)
        except (OSError, ValueError, KeyError, TypeError, StopIteration) as e:
            bc.log.info("memorial plaza outline: no cross-check against %s (%s)", src.name, e)
    else:
        bc.log.info("memorial plaza outline: %s absent, using the recorded constant uncross-checked", src)
    return [(x - frame.x0, y - frame.y0) for x, y in list(poly.exterior.coords)[:-1]]


def _plaza_deck(objs, frame, pool_outers):
    """The memorial plaza deck, cut open over the two pools.  Returns the deck polygon (frame coordinates).

    An unbroken quad here hides both pools from every camera standing on it, which is precisely what the
    ``landmark_911_memorial_pools`` sheet exists to show.  The deck is the real plaza outline (:func:`_plaza_ring`)
    unioned with a ``PLAZA_POOL_APRON`` margin around each 61 m pool square -- the pool centres are derived, so
    without the apron an opening could hang off the deck edge -- and the two squares are then cut out of it.
    """
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    deck = Polygon(_plaza_ring(frame))
    for sq in pool_outers:
        deck = deck.union(Polygon(sq).buffer(PLAZA_POOL_APRON, join_style=2))
    deck = orient(deck if deck.geom_type == "Polygon" else max(deck.geoms, key=lambda g: g.area), sign=1.0)
    outer = [(float(x), float(y)) for x, y in list(deck.exterior.coords)[:-1]]
    objs.append(nb.extrude_polygon("plaza", outer, GRND - PLAZA_SLAB, GRND,
                                   [list(reversed(sq)) for sq in pool_outers],
                                   material=bc.mat("sidewalk")))
    bc.log.info("memorial plaza deck: %.0f m2 with two %.1f m openings cut for the pools", deck.area, POOL_SIDE)
    return deck


def _tower(objs, name, bin_, frame, height, material, taper=0.0, lod=0, storey=3.9):
    fp = bc.load_footprint(bin_)
    ring = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    z0 = GRND
    objs.append(bc.prism(f"{name}_shaft", ring, z0 - 4.0, z0 + height, material))
    if taper > 0:
        objs.append(bc.prism(f"{name}_crown", pk._offset_ring(ring, -taper), z0 + height, z0 + height + 4.5,
                             "steel_gray"))
    objs.append(bc.prism(f"{name}_parapet", pk._offset_ring(ring, 0.4), z0 + height, z0 + height + 1.4, "steel_gray"))
    if lod == 0:
        bands = []
        for k in range(1, int(height / storey)):
            bands.append(bc.prism(f"{name}_b{k}", pk._offset_ring(ring, 0.1), z0 + k * storey - 0.5, z0 + k * storey,
                                  "steel_gray"))
        objs.append(bc.join(bands, f"{name}_spandrels"))
    return fp


def oculus_axis_deg(fp) -> float:
    """The Oculus's long axis in compass degrees, measured from its own OTI footprint.

    The building is a 110 m ellipse; the long edge of its footprint's minimum rotated rectangle *is* its axis,
    which is what :func:`b_common.footprint_heading` returns.  The recorded :data:`OCULUS_AXIS_DEG` is the same
    measurement written down so the disagreement is visible if the footprint table ever changes under this model
    -- the recorded-constant-plus-cross-check the plaza outline and the bridge supports already use, except that
    here the polygon is loaded anyway (its centroid places the building), so the measurement is what is used.
    """
    got = bc.footprint_heading(fp)
    if abs((got - OCULUS_AXIS_DEG + 90.0) % 180.0 - 90.0) > 1.0:
        bc.log.warning("Oculus axis: BIN 1089309's footprint now measures %.2f deg against the recorded %.1f deg; "
                       "the measurement is used, re-record the constant", got, OCULUS_AXIS_DEG)
    else:
        bc.log.info("Oculus axis: %.2f deg from BIN 1089309's footprint (recorded %.1f deg)", got, OCULUS_AXIS_DEG)
    return got


def _oculus(objs, frame, lod):
    """Calatrava's ribbed ellipse: two 350 ft arches flanking the skylight, with ribs springing from each.

    The body is laid out on the long axis of its *own* footprint (:func:`oculus_axis_deg`), not on the site's.
    Built on the plaza's 160.6 deg it stood 32.4 deg off that footprint and its south-east end lay inside 3 WTC.
    """
    fp = bc.load_footprint(1089309)
    cx, cy = fp.cx - frame.x0, fp.cy - frame.y0
    a = math.radians(bc.heading_to_math_deg(oculus_axis_deg(fp)))
    u = Vector((math.cos(a), math.sin(a), 0.0))          # along the building (350 ft)
    v = Vector((-u.y, u.x, 0.0))                          # across (115 ft)
    c = Vector((cx, cy, GRND))
    half_l, half_w = OCULUS_L / 2, OCULUS_W / 2
    objs.append(bc.prism("oculus_base", [(c.x + u.x * (half_l * t) + v.x * (half_w * s),
                                          c.y + u.y * (half_l * t) + v.y * (half_w * s))
                                         for t, s in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
                         GRND - 8.0, GRND + 1.2, "concrete"))
    ribs = []
    for side in (-1, 1):
        for k in range(N_RIBS_PER_SIDE if lod == 0 else 18):
            n = N_RIBS_PER_SIDE if lod == 0 else 18
            t = -1.0 + 2.0 * (k + 0.5) / n
            # the body's elliptical profile along the length
            hw = half_w * math.sqrt(max(1e-6, 1.0 - t * t)) if abs(t) < 1.0 else 0.02
            apex = OCULUS_APEX * math.sqrt(max(1e-6, 1.0 - (t * 0.94) ** 2))
            tip = OCULUS_TIP * math.sqrt(max(1e-6, 1.0 - (t * 0.94) ** 2))
            foot = c + u * (half_l * t) + v * (side * hw)
            crown = c + u * (half_l * t) + v * (side * 3.2) + Vector((0, 0, apex))
            wing = c + u * (half_l * t) + v * (side * -1.0) + Vector((0, 0, tip))
            pts = [foot,
                   foot + v * (side * -hw * 0.45) + Vector((0, 0, apex * 0.55)),
                   crown,
                   wing]
            ribs.append(bc.tube_along(f"oculus_rib{side}_{k}", pts, 0.42 if lod == 0 else 0.7, "paint_white",
                                      6 if lod == 0 else 4, cap=False))
    objs.append(bc.join(ribs, "oculus_ribs"))
    # the two 350 ft arches and the operable skylight between them
    for side in (-1, 1):
        arc = []
        for k in range(33):
            t = -1.0 + 2.0 * k / 32
            apex = OCULUS_APEX * math.sqrt(max(1e-6, 1.0 - (t * 0.94) ** 2))
            arc.append(c + u * (half_l * t) + v * (side * 3.2) + Vector((0, 0, apex)))
        objs.append(bc.tube_along(f"oculus_arch{side}", arc, 0.85, "paint_white", 8 if lod == 0 else 5, cap=False))
    sky = []
    for k in range(25):
        t = -1.0 + 2.0 * k / 24
        apex = OCULUS_APEX * math.sqrt(max(1e-6, 1.0 - (t * 0.94) ** 2))
        sky.append((c + u * (SKYLIGHT_L / 2 * t) + Vector((0, 0, apex))))
    objs.append(bc.tube_along("oculus_skylight", sky, 2.6, "glass_clear", 6, cap=False))
    return fp


def _pool(objs, name, centre: Vector, d: Vector, lod: int, rings):
    """One memorial pool: the 61 m parapet ring, the 9.14 m waterfall walls, the pool floor and the central void.

    ``rings`` is the (outer, inner, void) triple from :func:`_pool_rings` -- the same ``outer`` square the plaza
    deck is cut open with, so the parapet sits on the edge of the opening rather than under an unbroken plaza.

    The bronze parapet carries the ``MEMORIAL_NAMES`` material slot (b_common's ``memorial_names``), which the engine
    replaces with the incised-name texture; 152 parapet segments are built, matching the published count.
    """
    outer, inner, void = rings
    # plaza-level parapet (bronze, MEMORIAL_NAMES slot) and the waterfall walls
    objs.append(nb.extrude_polygon(f"{name}_parapet", outer, GRND + 0.15, GRND + 1.07,
                                   [list(reversed(inner))], material=bc.mat("memorial_names")))
    objs.append(nb.extrude_polygon(f"{name}_walls", inner, GRND - POOL_FALL, GRND + 0.15,
                                   [list(reversed(void))], material=bc.mat("granite_dark"), cap_bottom=False))
    objs.append(bc.prism(f"{name}_water", pk._offset_ring(inner, -0.25), GRND - POOL_FALL, GRND - POOL_FALL + 0.35,
                         "water", holes=[list(reversed(void))]))
    objs.append(nb.extrude_polygon(f"{name}_void", void, GRND - POOL_FALL - 9.0, GRND - POOL_FALL + 0.4, [],
                                   material=bc.mat("granite_dark"), cap_bottom=False))
    if lod == 0:
        # 152 bronze parapet segments (38 per side) as separate panels on the coping
        panels = []
        per_side = N_PARAPETS // 4
        for si in range(4):
            a0 = outer[si]
            a1 = outer[(si + 1) % 4]
            for k in range(per_side):
                t0 = (k + 0.06) / per_side
                t1 = (k + 0.94) / per_side
                p0 = Vector((a0[0] + (a1[0] - a0[0]) * t0, a0[1] + (a1[1] - a0[1]) * t0, GRND + 1.07))
                p1 = Vector((a0[0] + (a1[0] - a0[0]) * t1, a0[1] + (a1[1] - a0[1]) * t1, GRND + 1.07))
                panels.append(bc.box_between(f"{name}_panel{si}_{k}", p0, p1, 2.3, 0.09, "memorial_names"))
        objs.append(bc.join(panels, f"{name}_name_panels"))


def build(lod: int = 0):
    from shapely.geometry import Point, Polygon
    frame = bc.local_frame(PLAZA_CENTRE_TM, PLAZA_Z, SITE_AXIS_DEG)
    objs: list = []
    # the pool squares are needed before the plaza: they are what the deck is cut open with
    pa, pb, d = _pool_centres(frame)
    rings_n, rings_s = _pool_rings(pa, d), _pool_rings(pb, d)
    deck = _plaza_deck(objs, frame, (rings_n[0], rings_s[0]))
    _tower(objs, "wtc3", 1088797, frame, WTC3_M, "glass_dark", 0.0, lod, 3.95)
    _tower(objs, "wtc4", 1088795, frame, WTC4_M, "glass", 0.0, lod, 4.05)
    _tower(objs, "wtc7", 1086510, frame, WTC7_M, "glass_dark", 0.0, lod, 4.15)
    _oculus(objs, frame, lod)
    # memorial museum pavilion (Snohetta, 2014): a low canted glass-and-steel atrium
    fp_mus = bc.load_footprint(1088798)
    ring_mus = [(x - frame.x0, y - frame.y0) for x, y in fp_mus.ring]
    objs.append(bc.prism("museum_pavilion", ring_mus, GRND, GRND + 17.5, "glass_clear"))
    objs.append(bc.prism("museum_pavilion_cap", pk._offset_ring(ring_mus, -1.6), GRND + 17.5, GRND + 20.4, "steel_gray"))
    # memorial pools
    _pool(objs, "north_pool", pa, d, lod, rings_n)
    _pool(objs, "south_pool", pb, d, lod, rings_s)
    # plaza oaks on a 7.3 m grid clipped to the plaza deck itself -- 4 m in from its edge, clear of the two pool
    # openings and of the museum pavilion.  The street-props agent's library is preferred over b_common.simple_tree:
    # it has no swamp white oak (Quercus bicolor), so the pin oak (Q. palustris) prop is used -- same genus, same
    # upright habit -- collapse-decimated and instanced so that 220 trees cost one mesh in the exported glb.  The
    # Survivor Tree is a Callery pear, which the library does have.
    n_max = 220 if lod == 0 else 70
    plantable = deck.buffer(-OAK_EDGE_CLEAR)
    keep_out = [Polygon(rings_n[0]).buffer(OAK_POOL_CLEAR, join_style=2),
                Polygon(rings_s[0]).buffer(OAK_POOL_CLEAR, join_style=2),
                Polygon(ring_mus).buffer(OAK_BUILDING_CLEAR)]
    n_side = 22
    grid = []
    for i in range(-n_side, n_side + 1):
        for j in range(-n_side, n_side + 1):
            p = Vector((pa.x + pb.x, pa.y + pb.y, 0.0)) / 2 + d * (i * OAK_GRID) + Vector((-d.y, d.x, 0.0)) * (j * OAK_GRID)
            pt = Point(p.x, p.y)
            if not plantable.contains(pt) or any(k.intersects(pt) for k in keep_out):
                continue
            grid.append(p)
    rng = random.Random(20110911)
    # the grid holds more standing room than the count this model claims, so the trees are drawn from it with a
    # fixed seed and spread over the whole plaza rather than filling one end of it in loop order
    if len(grid) > n_max:
        grid = [grid[i] for i in sorted(rng.sample(range(len(grid)), n_max))]
    oak = bc.prop_template(OAK_PROP, max_tris=520 if lod == 0 else 160) if bc.prop_available(OAK_PROP) else None
    pear = bc.prop_template(PEAR_PROP, max_tris=520 if lod == 0 else 160) if bc.prop_available(PEAR_PROP) else None
    trees = []
    for k, p in enumerate(grid):
        if oak is None:
            trees.append(bc.simple_tree(f"oak{k}", (p.x, p.y, GRND), 11.0 if lod == 0 else 9.0, 3.4, 0.24))
        else:
            # the pin oak prop is 18.4 m tall; the memorial oaks were planted at ~8 m and stand ~11 m today
            tpl = pear if (k == SURVIVOR_TREE_INDEX and pear is not None) else oak
            h = OAK_H_M if tpl is oak else 9.0
            sc = h / (PEAR_PROP_H if tpl is pear else OAK_PROP_H)
            trees.append(bc.prop_instance(tpl, f"oak{k}", (p.x, p.y, GRND),
                                          rotation_z=rng.uniform(0.0, 2.0 * math.pi), scale=sc))
    bc.log.info("plaza oaks: %d placed on %.0f m2 of plantable deck", len(trees), plantable.area)
    if oak is None:
        objs.append(bc.join(trees, "plaza_swamp_white_oaks"))
    else:
        objs += trees          # linked duplicates: joining them would copy the mesh 220 times

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": SITE_AXIS_DEG, "height_m": WTC3_M, "name": TITLE,
        "wtc3_m": WTC3_M, "wtc4_m": WTC4_M, "wtc7_m": WTC7_M,
        "oculus_length_m": OCULUS_L, "oculus_width_m": OCULUS_W, "oculus_apex_m": OCULUS_APEX,
        "oculus_canopy_tip_m": OCULUS_TIP, "oculus_skylight_m": SKYLIGHT_L, "oculus_ribs": 2 * N_RIBS_PER_SIDE,
        "pool_side_m": POOL_SIDE, "pool_fall_m": POOL_FALL, "memorial_names": N_NAMES,
        "memorial_parapets": N_PARAPETS, "plaza_oaks_modelled": len(trees), "plaza_oaks_published": "400+", "plaza_oaks_lod1": 70,
        "plaza_datum_navd88_m": PLAZA_Z, "plaza_area_m2": round(deck.area, 1), "plaza_openings": 2,
        "plaza_source": f"OSM way {PLAZA_OSM_WAY} (memorial plaza outline), cut open over both pool squares",
        "pool_centre_source": "OSM ways 697722178 / 697722181 (Memorial North / South Pool), measured centroids",
        "plaza_tree_source": (f"blender_out/props/{OAK_PROP}.glb (species substitution: pin oak for swamp white oak)"
                              if oak is not None else "b_common.simple_tree (props library absent)"),
        "survivor_tree_source": (f"blender_out/props/{PEAR_PROP}.glb" if pear is not None else "not modelled"),
        "material_slots": {"MEMORIAL_NAMES": "bronze memorial parapet with the 2,983 incised names (engine texture)"},
        "height_source": "CTBUH/PANYNJ/Calatrava: 3 WTC 1,079 ft, 4 WTC 977 ft, 7 WTC 741.7 ft, Oculus 350 x 115 ft "
                         "and 96 ft to the apex / 168 ft to the canopy tips, 330 ft skylight; 9/11 Memorial: two "
                         "pools in the 200 ft tower footprints, 2,983 names on 152 bronze parapets",
        "sources_ids": ["building_footprints", "osm_bbbike", "published_wtc_site"],
        "fidelity_statement": (
            "Exact to published values: 3 WTC 329.2 m, 4 WTC 297.7 m and 7 WTC 226.1 m on their real OTI footprints "
            "(BINs 1088797 / 1088795 / 1086510); the Oculus 106.7 x 35.1 m with a 29.3 m apex, 51.2 m canopy tips "
            "and a 100.6 m skylight, centred on its real footprint (BIN 1089309) and laid out on that footprint's "
            "own long axis, measured from the polygon at build time (128.2 deg; 94 % of the modelled body lies "
            "over that footprint, IoU 0.90, and it overlaps neither 3 WTC nor 4 WTC); the memorial museum pavilion on BIN "
            "1088798; two 61.0 m memorial pools with the published 9.14 m waterfall and 152 bronze parapet panels "
            "carrying the MEMORIAL_NAMES slot for the 2,983 names. Measured, not derived: the pool centres and the "
            "rotation of their squares, from OSM ways 697722178 and 697722181 (the earlier build derived them "
            "+-85 m along the plaza polygon's axis and stood them 31.8 m and 30.1 m from these, with the squares "
            "41 deg out of rotation); the memorial plaza's outline, from OSM way 129835611, cut open over both "
            "pools so they can be seen from the plaza. The frame origin is the plaza's real NAVD88 elevation "
            "(4.40 m, the published terrain at the frame origin; the plaza deck's own median is 4.34 m) and the "
            "plaza is 0.0 in model space. Inferred: the Oculus rib count (112, from the "
            "350 ft length and the photographed pitch — no published count found), storey heights, museum pavilion "
            "height. Gaps: 220 swamp white oaks are placed of the "
            "published 400+, and the species is substituted — blender_out/props/ has no swamp white oak, so the "
            "pin oak prop tree_pin_oak_medium is instanced at 11 m; the Survivor Tree uses the correct Callery "
            "pear prop; and the body is a swept ellipse of the published dimensions on the footprint's axis rather "
            "than the footprint's own outline, so 6 % of its plan falls outside BIN 1089309 (it was 42 % when the "
            "body stood on the plaza's 160.6 deg, with its south-east end inside 3 WTC). Not modelled: the PATH platforms, the "
            "museum's underground galleries, 2 WTC, Liberty Park and St Nicholas church, curtain-wall panes, the "
            "Oculus's marble floor."),
    }
    return objs, extras


def main() -> None:
    """Four verification renders, each framed to answer one question.

    1. ``oculus_from_church_street`` — from Church Street on the east side of the site, the viewpoint every
       photograph of the Oculus is taken from, 95 m from the building.  Question: is the ribbed elliptical body
       106.7 m long and 35.1 m wide, 29.3 m to the apex with the canopy rib tips at 51.2 m, and does the rib
       rhythm read?
    2. ``oculus_close`` — half the distance and a longer lens, sun 35 deg up and raking along the ribs.
       Question: do the 112 ribs spring from the two 350 ft arches and rise as a pair of canopies, with the
       100.6 m skylight between them?
    3. ``memorial_plaza`` — the north pool from 38 m out and 12 m above the plaza, with no context ground plane.
       Question: is the plaza actually cut open over the pool, is the pool the published 61.0 m square with a
       9.14 m fall to the void, and do the bronze name parapets ring the opening?
    4. ``site_aerial`` — the whole superblock.  Question: are 3, 4 and 7 WTC on their real footprints at
       329.2 / 297.7 / 226.1 m, and are the two pools and the plaza oaks in the right places?
    """
    frame = bc.local_frame(PLAZA_CENTRE_TM, PLAZA_Z, SITE_AXIS_DEG)
    fp_oc = bc.load_footprint(1089309)
    ocx, ocy = fp_oc.cx - frame.x0, fp_oc.cy - frame.y0
    pa, pb, d = _pool_centres(frame)
    # the render context plane is in model space too: GRND is the plaza, the frame carries the NAVD88 offset
    ctx = (("ground_urban", GRND - 0.05, 700.0, (0.0, 0.0)),)
    a = math.radians(bc.heading_to_math_deg(PLAZA_AXIS_DEG))
    n = Vector((-math.sin(a), math.cos(a), 0.0))
    npool = Vector((-d.y, d.x, 0.0))
    church = (ocx + n.x * 95.0, ocy + n.y * 95.0, GRND + 1.65)
    close = (ocx + n.x * 52.0 + d.x * 34.0, ocy + n.y * 52.0 + d.y * 34.0, GRND + 1.65)
    # The north pool from 38 m out and 12 m up, on the plaza's west side.  It is deliberately not eye level: the
    # parapet is 1.07 m high and the water 9.14 m down, so from 1.65 m the parapet hides the pool, which is why the
    # eye-level shot is the reference view and this one is raised until the whole basin is in it.  It also carries
    # no context ground plane -- a 1,400 m plane 50 mm under the plaza is drawn straight through both openings.
    pool_eye = pa - d * 8.8 + npool * 37.0          # 38 m from the pool centre, out on the plaza's west side
    plaza_cam = (pool_eye.x, pool_eye.y, GRND + 12.0)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            # the comparison agent's recorded viewpoints, used verbatim
            ba.reference_render("landmark_oculus", frame, view="oculus_church_street_reference",
                                ground_z=GRND, target_z=24.0, fov_deg=66.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=250.0, sun_elevation_deg=35.0),
            ba.reference_render("landmark_911_memorial_pools", frame, view="memorial_pools_reference",
                                ground_z=GRND, target_z=GRND - 3.0, fov_deg=66.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=200.0, sun_elevation_deg=48.0),
            dict(view="oculus_from_church_street", cam=church, target=(ocx, ocy, 24.0), fov_deg=66.0,
                 size=(1280, 720), context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=35.0),
            dict(view="oculus_close", cam=close, target=(ocx, ocy, 26.0), fov_deg=62.0, size=(1280, 720),
                 context=ctx, sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="memorial_plaza", cam=plaza_cam,
                 target=(pa.x, pa.y, GRND - POOL_FALL + 0.35), fov_deg=72.0, size=(1280, 720), context=(),
                 sun_azimuth_deg=200.0, sun_elevation_deg=48.0),
            dict(view="site_aerial", cam=(-360.0, -560.0, 300.0), target=(0.0, 0.0, 90.0), fov_deg=52.0,
                 size=(1280, 720), context=ctx, sun_azimuth_deg=210.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": "frame origin NYC_TM (%.1f, %.1f) at %.2f m NAVD88 -- the plaza's own elevation, "
                               "with the plaza at 0.0 in model space; every building on its real OTI footprint; "
                               "pool centres and rotation measured from OSM ways 697722178 / 697722181; plaza "
                               "outline from OSM way %d, cut open over both pools."
                               % (PLAZA_CENTRE_TM[0], PLAZA_CENTRE_TM[1], PLAZA_Z, PLAZA_OSM_WAY),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Verification renders": main.__doc__.strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
