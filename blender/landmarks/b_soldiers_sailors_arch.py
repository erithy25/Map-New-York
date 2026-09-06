"""Soldiers' and Sailors' Memorial Arch — Grand Army Plaza, Brooklyn.  John H. Duncan, 1889-1892, dedicated to
"the Defenders of the Union, 1861-1865".  NYC Landmark (Grand Army Plaza, LP-0994), NRHP.

Dimensions used (source in brackets)
------------------------------------
* Height **80 ft = 24.38 m**, width **80 ft = 24.38 m**, depth **35 ft = 10.67 m**; the opening is **50 ft =
  15.24 m** high and **35 ft = 10.67 m** wide [NYC Parks, Wikipedia "Soldiers' and Sailors' Memorial Arch"].
* Sculpture (Frederick MacMonnies, 1894-1901): the bronze **quadriga** *Army and Navy* on the attic — a chariot with
  **four horses**, a winged Victory and two attendant figures; two bronze groups, *The Army* and *The Navy*, on the
  inner pier faces; and equestrian reliefs of Lincoln and Grant inside the arch.  The quadriga is blocked out in
  bronze (chariot, four horses, three figures) but **not sculpted** (stated); the pier groups and the reliefs are
  not modelled.
* Granite over a brick core, with the two flanking Doric colonnades of the plaza.

Placement: OSM way ``20679503`` (``building=triumphal_arch, historic=monument``, 24 x 14 m, tagged height 24 m) and
the real OTI footprint BIN **3347227** (257 m2, LiDAR height 23.2 m over ground 43.0 m NAVD88).  Both measurements
agree with the published 80 ft to within 5 %.  The arch faces **north-west up Flatbush Avenue**, on the axis of the
plaza.

Not modelled: the MacMonnies pier groups and the Lincoln and Grant reliefs, the inscriptions, the internal stair and
rooms, the plaza's Bailey Fountain and its sculpture, and the flanking Stanford White colonnades and berms.
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

ID = "b_soldiers_sailors_arch"
TITLE = "Soldiers' and Sailors' Memorial Arch"
BINS = [3347227]

HEIGHT = 24.38          # 80 ft -- to the top of the attic cap, the quadriga stands above it
# triumphal_arch stacks body (HEIGHT - 4.4), cornice (0.9 * 1.4), attic (ATTIC_H) and a 0.7 m attic cap; solve the
# attic height so the cap lands exactly on the published 24.38 m
ATTIC_H = HEIGHT - (HEIGHT - 4.4) - 0.9 * 1.4 - 0.7   # = 2.44
WIDTH = 24.38           # 80 ft
DEPTH = 10.67           # 35 ft
OPENING_W = 10.67       # 35 ft
OPENING_H = 15.24       # 50 ft
WAY = 20679503
HEADING = 330.0         # up Flatbush Avenue
GROUND = 43.0           # NAVD88 (LiDAR ground for BIN 3347227)


def build(lod: int = 0):
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    if ring is None:
        raise RuntimeError("OSM way 20679503 (Soldiers' and Sailors' Arch) missing; run b_osm_extract.py")
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    frame = bc.local_frame((cx, cy), GROUND, HEADING)
    objs: list = []
    objs += pk.triumphal_arch("ssa", (0.0, 0.0, 0.0), HEADING, width=WIDTH, depth=DEPTH, height=HEIGHT - 4.4,
                              opening_w=OPENING_W, opening_h=OPENING_H, material="granite_gray",
                              attic_h=ATTIC_H, cornice=0.9, lod=lod)
    objs.append(bc.prism("ssa_steps", bc.rect(WIDTH + 4.0, DEPTH + 4.0), -1.1, 0.0, "granite_gray"))
    # ---- the MacMonnies quadriga on the attic: chariot, four horses, three figures (blocked out) -------------------
    a = math.radians(bc.heading_to_math_deg(HEADING))
    d = Vector((math.cos(a), math.sin(a), 0.0))
    n = Vector((-d.y, d.x, 0.0))
    z_attic = HEIGHT  # top of the attic cap = the published 80 ft; the quadriga stands above it
    q = []
    q.append(bc.box("quadriga_chariot", (2.6, 3.0, 1.9), (-d.x * 2.2, -d.y * 2.2, z_attic), "bronze_green"))
    for k, t in enumerate((-3.3, -1.1, 1.1, 3.3)):
        p = d * 2.0 + n * t
        q.append(bc.box(f"quadriga_horse{k}_body", (3.4, 1.1, 1.5), (p.x, p.y, z_attic + 0.9), "bronze_green"))
        q.append(bc.box(f"quadriga_horse{k}_neck", (1.0, 0.9, 1.5), (p.x + d.x * 1.7, p.y + d.y * 1.7, z_attic + 1.9),
                        "bronze_green"))
        for leg in (-1.2, 1.2):
            q.append(bc.box(f"quadriga_horse{k}_legs{leg:+.0f}", (0.35, 0.35, 1.0),
                            (p.x + d.x * leg, p.y + d.y * leg, z_attic), "bronze_green"))
    q.append(bc.box("quadriga_victory", (0.9, 0.9, 3.4), (-d.x * 2.2, -d.y * 2.2, z_attic + 1.9), "bronze_green"))
    q.append(bc.box("quadriga_wings", (0.4, 4.6, 2.2), (-d.x * 2.6, -d.y * 2.6, z_attic + 2.8), "bronze_green"))
    for side in (-1, 1):
        q.append(bc.box(f"quadriga_attendant{side}", (0.8, 0.8, 2.4),
                        (-d.x * 2.0 + n.x * side * 2.6, -d.y * 2.0 + n.y * side * 2.6, z_attic + 1.6), "bronze_green"))
    objs.append(bc.join(q, "quadriga"))
    _ = nb

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": HEADING, "height_m": HEIGHT, "name": TITLE,
        "width_m": WIDTH, "depth_m": DEPTH, "opening_w_m": OPENING_W, "opening_h_m": OPENING_H,
        "quadriga_horses": 4, "lp_number": "LP-0994 (Grand Army Plaza)",
        "height_source": "NYC Parks / Wikipedia: 80 ft high and wide, 35 ft deep, 50 x 35 ft opening; OSM way "
                         "20679503 height 24 m; LiDAR height 23.2 m (BIN 3347227)",
        "sources_ids": ["osm_bbbike", "building_footprints", "published_soldiers_sailors_arch"],
        "fidelity_statement": (
            "Exact to published values: 24.38 m high and wide, 10.67 m deep, a 10.67 x 15.24 m opening, granite, "
            "on the real OSM footprint (way 20679503); both the OSM height tag (24 m) and the LiDAR height "
            "(23.2 m, BIN 3347227) agree with the published 80 ft to within 5 %. Blocked out, not sculpted: the "
            "MacMonnies quadriga (chariot, four horses, winged Victory, two attendants) in patinated bronze. "
            "Inferred: attic and cornice proportions, the engaged order, the 330 deg heading up Flatbush Avenue. "
            "Not modelled: the pier groups The Army and The Navy, the Lincoln and Grant reliefs, the inscriptions, "
            "the internal stair, Bailey Fountain, and the flanking colonnades and berms of Grand Army Plaza."),
    }
    return objs, extras


def main() -> None:
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    ctx = (("ground_urban", -1.2, 220.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=40_000,
        renders=[
            dict(view="flatbush_avenue", cam=(-32.0, -56.0, 1.7), target=(0.0, 0.0, 14.0), fov_deg=54.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=44.0),
            dict(view="quadriga", cam=(-26.0, -34.0, 30.0), target=(0.0, 0.0, 24.0), fov_deg=42.0, context=ctx,
                 sun_azimuth_deg=230.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": "real OSM way 20679503, centroid NYC_TM (%.1f, %.1f); BIN 3347227 gives ground "
                               "%.1f m NAVD88." % (cx, cy, GROUND),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
