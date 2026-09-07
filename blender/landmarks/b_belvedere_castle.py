"""Belvedere Castle — Central Park, on Vista Rock above the Turtle Pond and the Delacorte Theater.  Calvert Vaux with
Jacob Wrey Mould, 1869; restored 1983 and 2019.  NYC Scenic Landmark (Central Park, LP-0851); the National Weather
Service has recorded Central Park's official weather here since 1919.

Dimensions used (source in brackets)
------------------------------------
* A Gothic/Romanesque Revival folly of **Manhattan schist quarried on site** with **grey granite trim**, built at
  half the scale Vaux originally drew.  The square **tower** rises about **9 m above the terrace** and the whole
  castle stands on **Vista Rock, 30 m above the Turtle Pond** — the highest natural point in the park after
  Summit Rock [Central Park Conservancy, NYC Parks].
* The real OTI footprint (BIN **1083837**, "Belvedere Castle Visitor Center") is **906 m2** with a LiDAR height of
  **7.6 m** over ground **42.7 m NAVD88**; the OSM way ``278363023`` (``historic=castle``) is 13 x 17 m and is
  tagged **height 7.8 m**.  No published overall height was found: the tower is modelled at **16.5 m** above the
  terrace (LiDAR main-roof height 7.6 m plus a 9 m tower), *inferred* and stated.
* Features modelled from photographs: the square crenellated tower with its open **belvedere** stage and conical
  cap, the round turret at the south-west corner, the open loggia over the Turtle Pond, the crenellated terrace
  parapet, and the pointed-arch openings.

Placement: the real OTI footprint of BIN 1083837, LiDAR ground 42.7 m NAVD88, cross-checked against OSM way
278363023.

Not modelled: the interior (the Henry Luce Nature Observatory), the weather instruments on the tower, the individual
schist courses, the pavilion's timber roof structure, and Vista Rock's outcrop and the Turtle Pond.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_belvedere_castle"
TITLE = "Belvedere Castle"
BINS = [1083837]

MAIN_H = 7.6            # LiDAR height of the main mass
TOWER_H = 16.5          # inferred: main roof + a 9 m tower
TURRET_H = 11.0
GROUND = 42.7           # LiDAR ground, NAVD88


def _crenellation(name, ring, z, h, material, pitch=1.15):
    parts = []
    pts = list(ring) + [ring[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        n = max(int(L / pitch), 1)
        for k in range(0, n, 2):
            u0, u1 = (k + 0.12) / n, (k + 0.88) / n
            p0 = Vector((a[0] + (b[0] - a[0]) * u0, a[1] + (b[1] - a[1]) * u0, z))
            p1 = Vector((a[0] + (b[0] - a[0]) * u1, a[1] + (b[1] - a[1]) * u1, z))
            parts.append(bc.box_between(f"{name}_m{k}", p0, p1, 0.42, h, material))
    return [bc.join(parts, name)] if parts else []


def build(lod: int = 0):
    fp = bc.load_footprint(BINS[0])
    heading = bc.footprint_heading(fp)
    frame = bc.local_frame(fp, fp.ground_z, heading)
    ring = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    objs: list = []
    # terrace on the real footprint
    objs.append(bc.prism("terrace", pk._offset_ring(ring, 3.2), -4.0, 0.0, "schist"))
    objs += _crenellation("terrace_crenels", pk._offset_ring(ring, 3.0), 0.0, 1.0, "schist", 1.35)
    # main hall on the real footprint
    objs.append(bc.prism("hall", ring, 0.0, MAIN_H, "schist"))
    objs.append(bc.prism("hall_band", pk._offset_ring(ring, 0.25), MAIN_H - 0.55, MAIN_H, "granite_gray"))
    objs += _crenellation("hall_crenels", pk._offset_ring(ring, 0.2), MAIN_H, 0.95, "schist")
    # square tower on the north-west corner of the footprint
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    tx, ty = min(xs) + 3.6, max(ys) - 3.6
    tower_ring = bc.rect(6.4, 6.4, tx, ty)
    objs.append(bc.prism("tower", tower_ring, 0.0, TOWER_H, "schist"))
    objs.append(bc.prism("tower_belvedere", bc.rect(7.4, 7.4, tx, ty), TOWER_H, TOWER_H + 2.6, "schist",
                         holes=[list(reversed(bc.rect(5.4, 5.4, tx, ty)))]))
    objs += _crenellation("tower_crenels", bc.rect(7.6, 7.6, tx, ty), TOWER_H + 2.6, 1.05, "schist", 1.05)
    objs += pk.dome("tower_cap", (tx, ty, TOWER_H + 3.65), 3.0, 3.6, "granite_gray", segments=8, rings=3, lod=lod)
    # round turret on the opposite corner
    ux, uy = max(xs) - 2.6, min(ys) + 2.6
    objs.append(nb.cylinder("turret", 2.3, TURRET_H, 14, (ux, uy, 0.0), material=bc.mat("schist")))
    objs += _crenellation("turret_crenels", bc.regular_polygon(14, 2.5, ux, uy), TURRET_H, 0.9, "schist", 0.95)
    objs += pk.dome("turret_cap", (ux, uy, TURRET_H + 0.9), 2.4, 2.8, "granite_gray", segments=12, rings=3, lod=lod)
    # pointed-arch openings on the hall's four faces and the open loggia over the pond
    if lod == 0:
        arches = []
        for k, (px, py, w) in enumerate(((min(xs) + 0.2, (min(ys) + max(ys)) / 2, 2.2),
                                         (max(xs) - 0.2, (min(ys) + max(ys)) / 2, 2.2),
                                         ((min(xs) + max(xs)) / 2, min(ys) + 0.2, 2.6),
                                         ((min(xs) + max(xs)) / 2, max(ys) - 0.2, 2.6))):
            prof = bc.pointed_arch(w, 4.2, 0.0, 0.6)
            ob = bc.profile_extrude(f"arch{k}", prof, 0.9, "granite_gray", plane="xz")
            bc.transform(ob, bc.Matrix.Translation(Vector((px, py, 0.0))))
            arches.append(ob)
        objs.append(bc.join(arches, "arch_surrounds"))
        cols = []
        for k in range(4):
            cols += pk.column(f"loggia{k}", (min(xs) - 2.2, min(ys) + 1.6 + k * 2.4, 0.0), 4.4, 0.4, "granite_gray",
                              order="doric", segments=8, lod=lod)
        objs.append(bc.join(cols, "loggia_columns"))
        objs.append(bc.prism("loggia_roof", bc.rect(3.4, 11.0, min(xs) - 2.2, min(ys) + 5.2), 4.4, 5.1, "schist"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": TOWER_H + 3.65 + 3.6, "name": TITLE,
        "main_height_m": MAIN_H, "tower_height_m": TOWER_H, "turret_height_m": TURRET_H,
        "lidar_height_m": round(fp.height, 2), "footprint_area_m2": round(fp.geometry.area, 1),
        "lp_number": "LP-0851 (Central Park scenic landmark)",
        "height_source": "LiDAR height 7.6 m (BIN 1083837) and OSM way 278363023 height 7.8 m for the main mass; "
                         "no published overall height found, so the tower is inferred at 16.5 m",
        "sources_ids": ["building_footprints", "osm_bbbike", "published_belvedere_castle"],
        "fidelity_statement": (
            "Exact: the real OTI footprint of BIN 1083837 (906 m2) on its LiDAR ground of 42.7 m NAVD88, the "
            "7.6 m LiDAR height of the main mass, Manhattan schist with granite trim, and the arrangement of the "
            "square crenellated tower, round turret, open loggia and terrace taken from photographs. Inferred and "
            "stated: the 16.5 m tower height and 11.0 m turret height — no published overall height was found; the "
            "conical caps, arch sizes, crenellation pitch and loggia column count. Not modelled: the Henry Luce "
            "Nature Observatory interior, the weather instruments, the schist coursing, the timber roof structure, "
            "Vista Rock's outcrop and the Turtle Pond."),
    }
    return objs, extras


def main() -> None:
    ctx = (("grass", -4.1, 200.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=40_000,
        renders=[
            # eye height above the pond-side grass plane in ``ctx`` (z -4.1), not below it: at the -12.0 m
            # this camera used to sit at, it was 7.9 m under that plane and the render was pure black.
            dict(view="from_turtle_pond", cam=(-46.0, -38.0, -2.4), target=(0.0, 0.0, 12.0), fov_deg=50.0,
                 context=ctx, sun_azimuth_deg=210.0, sun_elevation_deg=40.0),
            dict(view="terrace", cam=(26.0, 22.0, 8.0), target=(0.0, 0.0, 12.0), fov_deg=56.0, context=ctx,
                 sun_azimuth_deg=250.0, sun_elevation_deg=42.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
