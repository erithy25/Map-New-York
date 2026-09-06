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
  photographed rib pitch (about 1.9 m), not from a published figure.
* **3 World Trade Center** (Rogers Stirk Harbour, 2018): **329.2 m** (1,079 ft), 80 storeys; **4 World Trade Center**
  (Maki, 2013): **297.7 m** (977 ft), 72 storeys; **7 World Trade Center** (SOM, 2006): **226.1 m** (741.7 ft), 52
  storeys, a parallelogram plan over a Con Edison substation podium.
* **National September 11 Memorial** (Michael Arad / Peter Walker, 2011): **two pools, each set in the 200 ft =
  61.0 m footprint of one of the original towers**, "each pool nearly an acre"; the water falls **9.1 m (30 ft)**
  down the pool walls to a second, smaller void; the names of the **2,983 victims are inscribed on 152 bronze
  parapets** around the pools.  The parapets carry the material slot ``MEMORIAL_NAMES`` so the engine can drive the
  incised-name texture.
* **Plaza trees**: more than **400 swamp white oaks** (*Quercus bicolor*) and one Callery pear (the Survivor Tree).
  The trees come from the street-props agent's library in ``blender_out/props/``.  That library has no swamp white
  oak, so ``tree_pin_oak_medium`` (*Quercus palustris*, same genus, same upright habit) stands in — **a stated
  species substitution** — collapse-decimated to 520 triangles and instanced, so 220 trees cost one mesh in the glb.
  The Survivor Tree is a Callery pear and uses ``tree_callery_pear_medium``, which is the right species.  The prop
  is 18.4 m tall and is scaled to the 11 m canopy the memorial oaks stand at today.  **220 oaks** are placed on the
  modelled part of the plaza on a 7.3 m grid clipped to the plaza polygon, not the full 400+ (the rest stand on the
  parts of the plaza south and east of this model's extent).  If the props library is absent the build falls back to
  ``b_common.simple_tree`` and the report says so.

Placement: every building uses its **real OTI footprint**: 3 WTC BIN **1088797** (9,219 m2, LiDAR height 324.3 m),
4 WTC BIN **1088795** (7,966 m2, 298.2 m), 7 WTC BIN **1086510** (3,019 m2, 226.7 m), the Oculus BIN **1089309**
(5,048 m2) and the memorial museum pavilion BIN **1088798** (1,382 m2).  The two pool centres are **derived** from
the OSM memorial-plaza polygon ``129835611``: its long axis runs on a heading of 160.6 deg and the pools sit
symmetrically +-85 m from its centroid along that axis — *derived, +-15 m*, because neither the extract nor Overpass
has a polygon for the individual pools.

Not modelled: the below-grade PATH platforms, the memorial museum's underground galleries (only the pavilion above
grade is built), 2 World Trade Center (never built above the below-grade box), the Liberty Park elevated garden and
St Nicholas Greek Orthodox Church, the individual curtain-wall panes, and the Oculus's marble interior floor.
"""
from __future__ import annotations

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
PLAZA_AXIS_DEG = 160.6
PLAZA_CENTRE_TM = (-5338.0, 1285.0)
POOL_OFFSET = 85.0
GRND = 3.5                          # plaza level, NAVD88 (LiDAR ground of the site footprints is 1.5-6.4 m)


def _pool_centres(frame):
    a = math.radians(bc.heading_to_math_deg(PLAZA_AXIS_DEG))
    d = Vector((math.cos(a), math.sin(a), 0.0))
    cx, cy, _ = frame.to_local(*PLAZA_CENTRE_TM)
    c = Vector((cx, cy, 0.0))
    return c - d * POOL_OFFSET, c + d * POOL_OFFSET, d


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


def _oculus(objs, frame, lod):
    """Calatrava's ribbed ellipse: two 350 ft arches flanking the skylight, with ribs springing from each."""
    fp = bc.load_footprint(1089309)
    cx, cy = fp.cx - frame.x0, fp.cy - frame.y0
    a = math.radians(bc.heading_to_math_deg(PLAZA_AXIS_DEG))
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


def _pool(objs, name, centre: Vector, d: Vector, lod: int):
    """One memorial pool: the 61 m parapet ring, the 9.14 m waterfall walls, the pool floor and the central void.

    The bronze parapet carries the ``MEMORIAL_NAMES`` material slot (b_common's ``memorial_names``), which the engine
    replaces with the incised-name texture; 152 parapet segments are built, matching the published count.
    """
    n = Vector((-d.y, d.x, 0.0))
    h = POOL_SIDE / 2

    def ring(r):
        return [(centre.x + d.x * (r * a) + n.x * (r * b), centre.y + d.y * (r * a) + n.y * (r * b))
                for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    outer = ring(h)
    inner = ring(h - 2.2)
    void = ring(h * 0.29)
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
    fp7 = bc.load_footprint(1086510)
    frame = bc.local_frame((fp7.cx, fp7.cy), GRND, PLAZA_AXIS_DEG)
    # centre the frame on the site rather than on 7 WTC
    frame = bc.local_frame(PLAZA_CENTRE_TM, GRND, PLAZA_AXIS_DEG)
    objs: list = []
    objs.append(bc.ground_plane("plaza", 260.0, GRND, "sidewalk"))
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
    pa, pb, d = _pool_centres(frame)
    _pool(objs, "north_pool", pa, d, lod)
    _pool(objs, "south_pool", pb, d, lod)
    # plaza oaks on a 7.3 m grid, clipped to the plaza and clear of the pools and buildings.  The street-props agent's
    # library is preferred over b_common.simple_tree: it has no swamp white oak (Quercus bicolor), so the pin oak
    # (Q. palustris) prop is used -- same genus, same upright habit -- collapse-decimated and instanced so that 220
    # trees cost one mesh in the exported glb.  The Survivor Tree is a Callery pear, which the library does have.
    trees = []
    keep_out = [(pa, POOL_SIDE / 2 + 5.0), (pb, POOL_SIDE / 2 + 5.0)]
    n_max = 220 if lod == 0 else 70
    oak = bc.prop_template(OAK_PROP, max_tris=520 if lod == 0 else 160) if bc.prop_available(OAK_PROP) else None
    pear = bc.prop_template(PEAR_PROP, max_tris=520 if lod == 0 else 160) if bc.prop_available(PEAR_PROP) else None
    rng = random.Random(20110911)
    n_side = 22
    k = 0
    for i in range(-n_side, n_side + 1):
        for j in range(-n_side, n_side + 1):
            p = Vector((pa.x + pb.x, pa.y + pb.y, 0.0)) / 2 + d * (i * OAK_GRID) + Vector((-d.y, d.x, 0.0)) * (j * OAK_GRID)
            if any((p - c).length < r for c, r in keep_out):
                continue
            if abs(i * OAK_GRID) > 155 or abs(j * OAK_GRID) > 62:
                continue
            if len(trees) >= n_max:
                continue
            if oak is None:
                trees.append(bc.simple_tree(f"oak{k}", (p.x, p.y, GRND), 11.0 if lod == 0 else 9.0, 3.4, 0.24))
            else:
                # the pin oak prop is 18.4 m tall; the memorial oaks were planted at ~8 m and stand ~11 m today
                tpl = pear if (k == SURVIVOR_TREE_INDEX and pear is not None) else oak
                h = OAK_H_M if tpl is oak else 9.0
                sc = h / (PEAR_PROP_H if tpl is pear else OAK_PROP_H)
                trees.append(bc.prop_instance(tpl, f"oak{k}", (p.x, p.y, GRND),
                                              rotation_z=rng.uniform(0.0, 2.0 * math.pi), scale=sc))
            k += 1
    if oak is None:
        objs.append(bc.join(trees, "plaza_swamp_white_oaks"))
    else:
        objs += trees          # linked duplicates: joining them would copy the mesh 220 times

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": PLAZA_AXIS_DEG, "height_m": WTC3_M, "name": TITLE,
        "wtc3_m": WTC3_M, "wtc4_m": WTC4_M, "wtc7_m": WTC7_M,
        "oculus_length_m": OCULUS_L, "oculus_width_m": OCULUS_W, "oculus_apex_m": OCULUS_APEX,
        "oculus_canopy_tip_m": OCULUS_TIP, "oculus_skylight_m": SKYLIGHT_L, "oculus_ribs": 2 * N_RIBS_PER_SIDE,
        "pool_side_m": POOL_SIDE, "pool_fall_m": POOL_FALL, "memorial_names": N_NAMES,
        "memorial_parapets": N_PARAPETS, "plaza_oaks_modelled": len(trees), "plaza_oaks_published": "400+", "plaza_oaks_lod1": 70,
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
            "and a 100.6 m skylight on its real footprint (BIN 1089309); the memorial museum pavilion on BIN "
            "1088798; two 61.0 m memorial pools with the published 9.14 m waterfall and 152 bronze parapet panels "
            "carrying the MEMORIAL_NAMES slot for the 2,983 names. Inferred: the Oculus rib count (112, from the "
            "350 ft length and the photographed pitch — no published count found), storey heights, museum pavilion "
            "height. Derived, +-15 m: the two pool centres, taken from the OSM memorial-plaza polygon 129835611's "
            "long axis (no polygon exists for the individual pools). Gaps: 220 swamp white oaks are placed of the "
            "published 400+, and the species is substituted — blender_out/props/ has no swamp white oak, so the "
            "pin oak prop tree_pin_oak_medium is instanced at 11 m; the Survivor Tree uses the correct Callery "
            "pear prop. Not modelled: the PATH platforms, the "
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
    3. ``memorial_plaza`` — eye level at the north pool's parapet.  Question: is the pool the published 61.0 m
       square with a 9.14 m fall to the void, and do the bronze name parapets ring it?
    4. ``site_aerial`` — the whole superblock.  Question: are 3, 4 and 7 WTC on their real footprints at
       329.2 / 297.7 / 226.1 m, and are the two pools and the plaza oaks in the right places?
    """
    frame = bc.local_frame(PLAZA_CENTRE_TM, GRND, PLAZA_AXIS_DEG)
    fp_oc = bc.load_footprint(1089309)
    ocx, ocy = fp_oc.cx - frame.x0, fp_oc.cy - frame.y0
    pa, pb, d = _pool_centres(frame)
    ctx = (("sidewalk", GRND - 0.05, 700.0, (0.0, 0.0)),)
    a = math.radians(bc.heading_to_math_deg(PLAZA_AXIS_DEG))
    n = Vector((-math.sin(a), math.cos(a), 0.0))
    church = (ocx + n.x * 95.0, ocy + n.y * 95.0, GRND + 1.65)
    close = (ocx + n.x * 52.0 + d.x * 34.0, ocy + n.y * 52.0 + d.y * 34.0, GRND + 1.65)
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
            dict(view="memorial_plaza", cam=(pa.x + d.x * 62.0 + 26.0, pa.y + d.y * 62.0 + 14.0, GRND + 1.65),
                 target=(pa.x, pa.y, GRND - 3.0), fov_deg=66.0, size=(1280, 720), context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=48.0),
            dict(view="site_aerial", cam=(-360.0, -560.0, 300.0), target=(0.0, 0.0, 90.0), fov_deg=52.0,
                 size=(1280, 720), context=ctx, sun_azimuth_deg=210.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": "frame origin NYC_TM (%.1f, %.1f) on the memorial plaza, site grid %.1f deg; every "
                               "building on its real OTI footprint; pool centres derived from OSM way 129835611."
                               % (PLAZA_CENTRE_TM[0], PLAZA_CENTRE_TM[1], PLAZA_AXIS_DEG),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Verification renders": main.__doc__.strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
