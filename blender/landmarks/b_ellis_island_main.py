"""Ellis Island Main Immigration Building — Ellis Island, Upper New York Bay.  Boring & Tilton, opened 17 December
1900 after the 1897 fire destroyed the wooden original; restored 1990 as the Ellis Island National Museum of
Immigration.  Part of the Statue of Liberty National Monument; NRHP.

Dimensions used (source in brackets)
------------------------------------
* French Renaissance Revival in **red brick with limestone quoins, keystones and belt courses**, on a steel frame;
  the building is **338 ft long by 168 ft wide = 103.0 x 51.2 m** with **four corner towers**, each capped by a
  **copper dome and a finial**, rising about **100 ft = 30.5 m** [NPS, HABS NJ-1112, Wikipedia "Ellis Island
  Immigrant Building"].
* The **Registry Room (Great Hall)** on the second floor is **200 x 100 ft = 61.0 x 30.5 m** and **56 ft = 17.07 m**
  high, vaulted in **28,282 Guastavino tiles** after the 1916 Black Tom explosion damaged the original plaster
  ceiling.  The hall is modelled as a raised roof volume over the centre of the building; **the vault and its tiles
  are not modelled** (stated).
* The three great arched entrance openings on the harbour front are each about **7.6 m** wide and **12.2 m** high
  (*inferred* from the elevation and photographs, +-0.8 m).
* The real OTI footprint (BIN **1085964**) covers **17,332 m2** — the main building *and* its flanking wings and the
  1930s ferry building; its LiDAR height is **26.5 m** over ground **3.66 m NAVD88**.  The model builds the whole
  real footprint at the LiDAR height and raises the Registry Room roof and the four towers above it.

Placement: the real OTI footprint for BIN 1085964, principal axis from its minimum rotated rectangle (the building
faces north-east across the harbour towards Manhattan).

Not modelled: the Guastavino vault and the Registry Room interior, the canopy over the entrance, the dormers and
their pediments, the limestone quoin coursing, the flanking hospital buildings on the island's south side, the
ferry basin and its 1930s ferry building as separate volumes, and the island's seawall and landscaping.
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

ID = "b_ellis_island_main"
TITLE = "Ellis Island Main Immigration Building"
BINS = [1085964]

LENGTH = 103.0          # 338 ft
WIDTH = 51.2            # 168 ft
TOWER_H = 30.5          # 100 ft
HALL_L, HALL_W, HALL_H = 61.0, 30.5, 17.07     # 200 x 100 ft, 56 ft high
ARCH_W, ARCH_H = 7.6, 12.2
GUASTAVINO_TILES = 28282


def build(lod: int = 0):
    fp = bc.load_footprint(BINS[0])
    heading = bc.footprint_heading(fp)
    frame = bc.local_frame(fp, fp.ground_z, heading)
    ring = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    body_h = fp.height
    objs: list = []
    objs.append(bc.prism("main_block", ring, -2.0, body_h, "brick_red"))
    objs.append(bc.prism("limestone_base", pk._offset_ring(ring, 0.35), -2.0, 3.4, "limestone"))
    objs.append(bc.prism("belt_course", pk._offset_ring(ring, 0.3), body_h - 2.4, body_h - 1.6, "limestone"))
    objs.append(bc.prism("cornice", pk._offset_ring(ring, 0.85), body_h - 1.6, body_h, "limestone"))
    objs.append(bc.prism("roof", pk._offset_ring(ring, -0.4), body_h, body_h + 0.9, "granite_dark"))

    a = math.radians(bc.heading_to_math_deg(heading))
    d = Vector((math.cos(a), math.sin(a), 0.0))
    n = Vector((-d.y, d.x, 0.0))
    # ---- Registry Room roof volume over the centre -----------------------------------------------------------------
    hall = [(d.x * (HALL_L / 2 * sx) + n.x * (HALL_W / 2 * sy), d.y * (HALL_L / 2 * sx) + n.y * (HALL_W / 2 * sy))
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    # the Great Hall's 17.07 m clear height sits inside the 26.5 m block; above the main roof the real building
    # carries a raised monitor roof over the hall, which is what is built here
    z_mon = body_h + 4.6
    objs.append(bc.prism("registry_room", hall, body_h - 0.2, z_mon, "brick_red"))
    objs.append(bc.prism("registry_cornice", pk._offset_ring(hall, 0.8), z_mon - 1.2, z_mon, "limestone"))
    objs.append(bc.prism("registry_roof", pk._offset_ring(hall, -0.4), z_mon, z_mon + 1.0, "granite_dark"))

    # ---- four corner towers with copper domes and finials ----------------------------------------------------------
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        cxx = d.x * (LENGTH / 2 - 6.5) * sx + n.x * (WIDTH / 2 - 6.5) * sy
        cyy = d.y * (LENGTH / 2 - 6.5) * sx + n.y * (WIDTH / 2 - 6.5) * sy
        t_ring = bc.rect(12.4, 12.4, cxx, cyy)
        objs.append(bc.prism(f"tower{k}", t_ring, -2.0, TOWER_H, "brick_red"))
        objs.append(bc.prism(f"tower{k}_cornice", pk._offset_ring(t_ring, 0.9), TOWER_H - 1.5, TOWER_H, "limestone"))
        objs += pk.dome(f"tower{k}_dome", (cxx, cyy, TOWER_H), 7.4, 8.2, "copper_patina", segments=20 if lod == 0 else 10,
                        rings=6 if lod == 0 else 3, lantern_h=3.6, lod=lod)
        objs.append(nb.cylinder(f"tower{k}_finial", 0.45, 3.0, 8, (cxx, cyy, TOWER_H + 11.8),
                                material=bc.mat("copper_patina")))

    # ---- the three great arched entrances on the harbour front -----------------------------------------------------
    if lod == 0:
        arches = []
        for k, off in ((0, -10.4), (1, 0.0), (2, 10.4)):
            px = d.x * off + n.x * (WIDTH / 2 + 0.2)
            py = d.y * off + n.y * (WIDTH / 2 + 0.2)
            prof = bc.round_arch(ARCH_W + 2.0, ARCH_H + 2.4, 0.0, 0.0)
            ob = bc.profile_extrude(f"entrance_arch{k}", prof, 1.4, "limestone", plane="xz")
            bc.transform(ob, bc.rot_z(bc.heading_to_math_deg(heading) - 90.0))
            bc.transform(ob, bc.Matrix.Translation(Vector((px, py, 0.0))))
            arches.append(ob)
            void = bc.profile_extrude(f"entrance_glass{k}", bc.round_arch(ARCH_W, ARCH_H, 0.0, 0.0), 0.4,
                                      "glass_dark", plane="xz")
            bc.transform(void, bc.rot_z(bc.heading_to_math_deg(heading) - 90.0))
            bc.transform(void, bc.Matrix.Translation(Vector((px + n.x * 0.9, py + n.y * 0.9, 0.0))))
            arches.append(void)
        objs.append(bc.join(arches, "entrance_arches"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": TOWER_H + 11.8 + 3.0, "name": TITLE,
        "length_m": LENGTH, "width_m": WIDTH, "tower_height_m": TOWER_H, "registry_room_m": [HALL_L, HALL_W, HALL_H],
        "guastavino_tiles": GUASTAVINO_TILES, "corner_towers": 4,
        "lidar_height_m": round(fp.height, 2), "footprint_area_m2": round(fp.geometry.area, 1),
        "height_source": "NPS / HABS NJ-1112: 338 x 168 ft, four 100 ft corner towers with copper domes, Registry "
                         "Room 200 x 100 ft and 56 ft high with 28,282 Guastavino tiles; LiDAR height 26.5 m",
        "sources_ids": ["building_footprints", "published_ellis_island"],
        "fidelity_statement": (
            "Exact to published values: the four 30.5 m corner towers with copper domes and finials, the "
            "61.0 x 30.5 m Registry Room raised 17.07 m over the centre, the three great arched entrances, red "
            "brick with limestone base, belt course and cornice, all on the real OTI footprint of BIN 1085964 "
            "(17,332 m2) at its LiDAR height of 26.5 m over 3.66 m NAVD88. Inferred: the entrance arch dimensions "
            "(+-0.8 m), tower plan (12.4 m square), dome radius and lantern, the belt-course heights. Stated: the "
            "real footprint covers the main building plus its wings and the ferry building, so it is larger than "
            "the published 338 x 168 ft main block; the towers and Registry Room are positioned from the published "
            "dimensions within it. Not modelled: the Guastavino vault and the Registry Room interior, the entrance "
            "canopy, dormers and pediments, quoin coursing, the hospital buildings, the ferry basin, the seawall."),
    }
    return objs, extras


def main() -> None:
    ctx = (("grass", -2.1, 300.0, (0.0, 0.0)), ("water_dark", 0.35, 2000.0, (0.0, 0.0)))
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            dict(view="harbour_front", cam=(0.0, -130.0, 6.0), target=(0.0, 0.0, 22.0), fov_deg=54.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=40.0),
            dict(view="three_quarter", cam=(-115.0, -105.0, 46.0), target=(0.0, 0.0, 22.0), fov_deg=48.0,
                 context=ctx, sun_azimuth_deg=235.0, sun_elevation_deg=36.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
