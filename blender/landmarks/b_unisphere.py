"""Unisphere — Flushing Meadows-Corona Park, Queens.  Gilmore D. Clarke, built by U.S. Steel as the theme symbol of
the 1964-65 New York World's Fair.  NYC Landmark LP-1927.

Dimensions used (source in brackets)
------------------------------------
* **140 ft = 42.67 m** high overall, **120 ft = 36.58 m** in diameter, about **350 short tons** of Type 304
  stainless steel; it stands on a **20 ft = 6.10 m** tripod pedestal in a fountain pool **310 ft = 94.49 m** across
  [NYC Parks, LPC designation report LP-1927, Wikipedia "Unisphere"].
* The globe is a **grid of meridians and parallels** carrying the raised continents, encircled by **three orbit
  rings** representing Yuri Gagarin's, John Glenn's and Telstar's orbits.  This model builds **24 meridians and 11
  parallels** (*inferred* — the published sources give no count) and the three orbit rings at their photographed
  inclinations of about 28, 52 and 76 degrees (*inferred*, +-6 degrees).
* The continents are modelled as **raised plates on the sphere**, generated from a coarse continental outline at
  4-degree resolution rather than from a coastline dataset (stated gap).

Placement: OSM way ``596273458`` (``tourism=artwork``, name Unisphere, 36 x 36 m, tagged **height 43 m**), NYC_TM
centroid (8862, 5157); the surrounding fountain basin is the real OTI footprint BIN **4458851** (12,721 m2, LiDAR
ground 7.3 m NAVD88).

Not modelled: the continents' relief detail and their country outlines, the fountain jets and their basin plumbing,
the three capsule-shaped 1964 information plaques, the ring lighting, and the surrounding promenade paving.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import bmesh  # noqa: E402  (bpy is initialised by b_common)
import nycsim_bpy as nb  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

ID = "b_unisphere"
TITLE = "Unisphere"
BINS = [4458851]

TOTAL_H = 42.67        # 140 ft
DIAMETER = 36.58       # 120 ft
PEDESTAL_H = 6.10      # 20 ft
POOL_D = 94.49         # 310 ft
MERIDIANS = 24
PARALLELS = 11
ORBIT_INCL = (28.0, 52.0, 76.0)
WAY = 596273458
GROUND = 7.3
TILT = 23.44           # the globe is set at the Earth's axial tilt

# Coarse continental masses as (lon0, lat0, lon1, lat1) lozenges on the globe -- a deliberately schematic set, not a
# coastline dataset (see the docstring).
CONTINENTS = [
    (-168, 52, -52, 72), (-140, 30, -60, 55), (-120, 15, -78, 33), (-82, -4, -35, 12), (-76, -35, -35, -4),
    (-73, -55, -62, -35), (-18, 5, 50, 36), (8, -35, 40, 5), (-16, 4, 12, 20), (-10, 36, 40, 60), (30, 40, 140, 72),
    (60, 8, 95, 34), (95, 8, 125, 30), (100, -10, 140, 8), (113, -38, 153, -12), (166, -47, 178, -34),
    (-60, 60, -20, 82),
]


def build(lod: int = 0):
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    if ring is None:
        raise RuntimeError("OSM way 596273458 (Unisphere) missing; run b_osm_extract.py")
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    frame = bc.local_frame((cx, cy), GROUND, 0.0)
    R = DIAMETER / 2
    z_c = PEDESTAL_H + R          # sphere centre; the top of the globe is at PEDESTAL_H + DIAMETER = 42.68 m
    objs: list = []
    objs.append(bc.prism("fountain_pool", bc.regular_polygon(48, POOL_D / 2), -1.4, 0.35, "concrete"))
    objs.append(bc.prism("pool_water", bc.regular_polygon(48, POOL_D / 2 - 1.0), -1.0, 0.15, "water"))
    # ---- tripod pedestal -------------------------------------------------------------------------------------------
    for k in range(3):
        a = math.radians(90 + 120 * k)
        base = Vector((7.4 * math.cos(a), 7.4 * math.sin(a), 0.2))
        objs.append(bc.box_between(f"tripod{k}", base, Vector((0, 0, PEDESTAL_H)), 1.5, 1.5, "stainless"))
    objs.append(nb.cylinder("pedestal_cap", 2.4, 1.1, 16, (0, 0, PEDESTAL_H - 0.6), material=bc.mat("stainless")))
    # ---- the globe grid: meridians and parallels, tilted to the Earth's axis ----------------------------------------
    tilt = Matrix.Rotation(math.radians(TILT), 4, "Y")
    grid = []
    nm = MERIDIANS if lod == 0 else 8
    npar = PARALLELS if lod == 0 else 5
    for k in range(nm):
        lon = 2 * math.pi * k / nm
        pts = []
        for i in range(37):
            lat = -math.pi / 2 + math.pi * i / 36
            pts.append(Vector((R * math.cos(lat) * math.cos(lon), R * math.cos(lat) * math.sin(lon), R * math.sin(lat))))
        grid.append(bc.tube_along(f"meridian{k}", pts, 0.16, "stainless", 5 if lod == 0 else 4, cap=False))
    for j in range(1, npar):
        lat = -math.pi / 2 + math.pi * j / npar
        r = R * math.cos(lat)
        z = R * math.sin(lat)
        pts = [Vector((r * math.cos(2 * math.pi * i / 48), r * math.sin(2 * math.pi * i / 48), z)) for i in range(49)]
        grid.append(bc.tube_along(f"parallel{j}", pts, 0.13, "stainless", 5 if lod == 0 else 4, cap=False))
    globe = bc.join(grid, "globe_grid")
    bc.transform(globe, Matrix.Translation(Vector((0, 0, z_c))) @ tilt)
    objs.append(globe)
    # ---- continents as raised plates --------------------------------------------------------------------------------
    if lod == 0:
        bm = bmesh.new()
        for lon0, lat0, lon1, lat1 in CONTINENTS:
            nu, nv = 6, 5
            verts = []
            for i in range(nu + 1):
                row = []
                for j in range(nv + 1):
                    lon = math.radians(lon0 + (lon1 - lon0) * i / nu)
                    lat = math.radians(lat0 + (lat1 - lat0) * j / nv)
                    rr = R * 1.035
                    row.append(bm.verts.new(Vector((rr * math.cos(lat) * math.cos(lon),
                                                    rr * math.cos(lat) * math.sin(lon), rr * math.sin(lat)))))
                verts.append(row)
            for i in range(nu):
                for j in range(nv):
                    bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        cont = nb.bmesh_to_object("continents", bm, materials=[bc.mat("stainless")])
        bc.transform(cont, Matrix.Translation(Vector((0, 0, z_c))) @ tilt)
        objs.append(cont)
    # ---- three orbit rings ------------------------------------------------------------------------------------------
    for k, inc in enumerate(ORBIT_INCL):
        r = R * (1.02 + 0.03 * k)
        pts = [Vector((r * math.cos(2 * math.pi * i / 64), r * math.sin(2 * math.pi * i / 64), 0.0)) for i in range(65)]
        ring_ob = bc.tube_along(f"orbit{k}", pts, 0.34, "stainless", 6 if lod == 0 else 4, cap=False)
        m = (Matrix.Translation(Vector((0, 0, z_c))) @ Matrix.Rotation(math.radians(40 * k), 4, "Z")
             @ Matrix.Rotation(math.radians(inc), 4, "X"))
        bc.transform(ring_ob, m)
        objs.append(ring_ob)

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": 0.0, "height_m": TOTAL_H, "name": TITLE, "lp_number": "LP-1927",
        "diameter_m": DIAMETER, "pedestal_m": PEDESTAL_H, "pool_diameter_m": POOL_D, "meridians": MERIDIANS,
        "parallels": PARALLELS, "orbit_rings": 3, "axial_tilt_deg": TILT, "material": "Type 304 stainless steel",
        "height_source": "NYC Parks / LPC LP-1927: 140 ft high, 120 ft diameter, 350 tons of stainless steel, "
                         "310 ft fountain pool; OSM way 596273458 height 43 m",
        "sources_ids": ["osm_bbbike", "building_footprints", "published_unisphere"],
        "fidelity_statement": (
            "Exact to published values: 42.67 m overall height, 36.58 m globe diameter, 6.10 m tripod pedestal, "
            "94.49 m fountain pool, stainless steel, three orbit rings, the globe set at the Earth's 23.44 deg "
            "axial tilt, on the real OSM footprint (way 596273458, tagged 43 m). Inferred: 24 meridians and 11 "
            "parallels (no published count found), the orbit rings' inclinations (28/52/76 deg, +-6 deg, from "
            "photographs), tripod leg dimensions. Gap: the continents are schematic raised plates from a "
            "17-lozenge outline at 4-degree resolution, not coastline data. Not modelled: continent relief and "
            "country outlines, fountain jets and plumbing, the 1964 plaques, ring lighting, promenade paving."),
    }
    return objs, extras


def main() -> None:
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    ctx = (("grass", -1.5, 400.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            dict(view="promenade", cam=(0.0, -96.0, 2.0), target=(0.0, 0.0, 24.0), fov_deg=48.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=44.0),
            dict(view="close", cam=(-46.0, -44.0, 22.0), target=(0.0, 0.0, 24.0), fov_deg=52.0, context=ctx,
                 sun_azimuth_deg=240.0, sun_elevation_deg=36.0),
        ],
        sections={"Placement": "real OSM way 596273458, centroid NYC_TM (%.1f, %.1f); fountain basin BIN 4458851, "
                               "LiDAR ground %.1f m NAVD88." % (cx, cy, GROUND),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
