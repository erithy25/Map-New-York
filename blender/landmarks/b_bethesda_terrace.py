"""Bethesda Terrace and Fountain — Central Park, on the axis of the Mall at 72nd Street.  Calvert Vaux (architecture)
with Jacob Wrey Mould (carving), 1859-1864; the Angel of the Waters fountain by Emma Stebbins, unveiled 1873.
NYC Scenic Landmark (Central Park, LP-0851).

Dimensions used (source in brackets)
------------------------------------
* The terrace is a two-level platform on the Lake, reached by two flanking staircases and by the **Arcade** that
  passes under the 72nd Street transverse road; the arcade's ceiling carries **15,876 encaustic Minton tiles** in
  49 panels, the only such ceiling in the world [Central Park Conservancy, NYC Parks].
* The **Bethesda Fountain** basin is **96 ft = 29.26 m** across; the *Angel of the Waters* is **8 ft = 2.44 m** tall
  and stands on a pedestal above four cherubs representing Temperance, Purity, Health and Peace, making the whole
  fountain about **26 ft = 7.92 m** high [NYC Parks, Wikipedia "Bethesda Terrace and Fountain"].
* Materials: New Brunswick sandstone throughout the terrace, with granite steps and a bluestone plaza; the angel and
  cherubs are bronze.

Placement: the terrace's real OTI footprints, BINs **1090516** (1,795 m2) and **1091041** (1,583 m2), both named
"Bethesda Terrace" with LiDAR ground **22.9 m NAVD88**; the fountain is OSM way ``958635828`` (28 x 28 m) and the
arcade OSM way ``234241518``.  The terrace's axis is the Mall's, taken from the footprints' principal axis.

The arcade ceiling carries the material slot ``MINTON_TILE`` (``b_common``'s ``minton_tile``, a lit encaustic-tile
material) so the engine can drive the real tile pattern from a texture.

Not modelled: Mould's carved panels on the staircase piers and balustrades (the seasons, day and night, birds and
plants), the individual Minton tiles, the arcade's vaulting ribs in detail, the lake and its boats, and the terrace's
lamp standards.
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

ID = "b_bethesda_terrace"
TITLE = "Bethesda Terrace and Fountain"
BINS = [1090516, 1091041]

BASIN_D = 29.26         # 96 ft
FOUNTAIN_H = 7.92       # 26 ft
ANGEL_H = 2.44          # 8 ft
MINTON_TILES = 15876
FOUNTAIN_WAY = 958635828
GROUND_UPPER = 22.9     # LiDAR ground of the terrace footprints, NAVD88
LOWER_DROP = 5.2        # upper terrace to the lower plaza (inferred from the staircase run)


def build(lod: int = 0):
    fp = bc.load_footprint(BINS[0])
    heading = bc.footprint_heading(fp)
    fring = ba.osm_polygon_local(FOUNTAIN_WAY, bc.LocalFrame(0.0, 0.0))
    if fring is None:
        raise RuntimeError("OSM way 958635828 (Bethesda Fountain) missing; run b_osm_extract.py")
    fx = sum(p[0] for p in fring) / len(fring)
    fy = sum(p[1] for p in fring) / len(fring)
    frame = bc.local_frame((fx, fy), GROUND_UPPER - LOWER_DROP, heading)
    a = math.radians(bc.heading_to_math_deg(heading))
    d = Vector((math.cos(a), math.sin(a), 0.0))
    n = Vector((-d.y, d.x, 0.0))
    objs: list = []

    # ---- lower plaza and the fountain -----------------------------------------------------------------------------
    objs.append(bc.prism("lower_plaza", bc.rect(78.0, 52.0), -1.2, 0.0, "sidewalk"))
    objs.append(bc.prism("basin_rim", bc.regular_polygon(48, BASIN_D / 2), 0.0, 0.85, "sandstone_red"))
    objs.append(bc.prism("basin_water", bc.regular_polygon(48, BASIN_D / 2 - 0.9), 0.0, 0.62, "water"))
    objs.append(nb.cylinder("fountain_pedestal", 3.1, 1.5, 24, (0, 0, 0.0), material=bc.mat("sandstone_red")))
    objs.append(nb.cylinder("fountain_upper_basin", 4.4, 0.55, 24, (0, 0, 1.5), material=bc.mat("sandstone_red")))
    objs.append(nb.cylinder("fountain_stem", 1.15, FOUNTAIN_H - ANGEL_H - 2.05, 16, (0, 0, 2.05),
                            material=bc.mat("sandstone_red")))
    # four cherubs around the stem
    for k in range(4):
        ang = math.pi / 2 * k + math.pi / 4
        objs.append(bc.box(f"cherub{k}", (0.75, 0.75, 1.5),
                           (2.0 * math.cos(ang), 2.0 * math.sin(ang), 2.4), "bronze_green"))
    # the Angel of the Waters, blocked out in bronze
    z_ang = FOUNTAIN_H - ANGEL_H
    objs.append(bc.box("angel_body", (0.95, 0.95, ANGEL_H), (0, 0, z_ang), "bronze_green"))
    objs.append(bc.box("angel_wings", (0.28, 3.3, 1.6), (0, 0, z_ang + ANGEL_H * 0.42), "bronze_green"))
    objs.append(bc.box("angel_arm", (0.9, 0.28, 0.28), (0.55, 0, z_ang + ANGEL_H * 0.72), "bronze_green"))

    # ---- upper terrace on the real footprints, with the two staircases and the balustrade --------------------------
    for i, bin_ in enumerate(BINS):
        f = bc.load_footprint(bin_)
        ring = [(x - frame.x0, y - frame.y0) for x, y in f.ring]
        objs.append(bc.prism(f"terrace{i}", ring, -1.4, LOWER_DROP, "sandstone_red"))
        objs += pk.balustrade(f"terrace{i}_bal", pk._offset_ring(ring, -0.3), LOWER_DROP, 1.15, "sandstone_red",
                              spacing=0.62, lod=lod)
    # the two flanking staircases down to the plaza
    for side in (-1, 1):
        p0 = d * 22.0 + n * (side * 21.0)
        p1 = d * 34.0 + n * (side * 21.0)
        objs += pk.stairs(f"stair{side}", (p0.x, p0.y, 0.0), (p1.x, p1.y, LOWER_DROP), 6.4, 20, "granite_gray")

    # ---- the Arcade under the transverse road, with the Minton tile ceiling ---------------------------------------
    arc_len, arc_w, arc_h = 24.0, 15.6, 6.2
    c = d * 44.0
    objs.append(bc.prism("arcade_walls", bc.rect(arc_len, arc_w + 5.0, c.x, c.y), 0.0, arc_h + 2.6, "sandstone_red",
                         holes=[list(reversed(bc.rect(arc_len - 1.6, arc_w, c.x, c.y)))]))
    objs.append(bc.prism("arcade_floor", bc.rect(arc_len - 1.6, arc_w, c.x, c.y), -0.15, 0.05, "sidewalk"))
    objs.append(bc.prism("arcade_ceiling", bc.rect(arc_len - 1.6, arc_w, c.x, c.y), arc_h, arc_h + 0.25,
                         "minton_tile"))
    if lod == 0:
        piers = []
        for i in range(4):
            for side in (-1, 1):
                px = c.x + d.x * (-arc_len / 2 + 3.0 + i * (arc_len - 6.0) / 3) + n.x * (side * arc_w / 2 * 0.62)
                py = c.y + d.y * (-arc_len / 2 + 3.0 + i * (arc_len - 6.0) / 3) + n.y * (side * arc_w / 2 * 0.62)
                piers.append(bc.box(f"arcade_pier{i}{side}", (1.5, 1.5, arc_h), (px, py, 0.0), "sandstone_red"))
        objs.append(bc.join(piers, "arcade_piers"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": FOUNTAIN_H, "name": TITLE,
        "lp_number": "LP-0851 (Central Park scenic landmark)", "basin_diameter_m": BASIN_D,
        "fountain_height_m": FOUNTAIN_H, "angel_height_m": ANGEL_H, "minton_tiles": MINTON_TILES,
        "terrace_drop_m": LOWER_DROP,
        "material_slots": {"MINTON_TILE": "the arcade's 15,876-tile encaustic Minton ceiling (engine texture)"},
        "height_source": "NYC Parks / Central Park Conservancy: 96 ft fountain basin, 8 ft Angel of the Waters, "
                         "26 ft fountain, 15,876 Minton tiles in the arcade ceiling",
        "sources_ids": ["building_footprints", "osm_bbbike", "published_bethesda_terrace"],
        "fidelity_statement": (
            "Exact to published values: the 29.26 m fountain basin, the 7.92 m fountain with its 2.44 m Angel of "
            "the Waters and four cherubs, the terrace on its two real OTI footprints (BINs 1090516 and 1091041), "
            "the fountain on its real OSM footprint (way 958635828), and the arcade ceiling carrying the "
            "MINTON_TILE material slot for the 15,876-tile encaustic ceiling. Blocked out, not sculpted: the angel "
            "and the cherubs. Inferred: the 5.2 m terrace-to-plaza drop, the arcade's 24 x 15.6 x 6.2 m interior, "
            "the staircase runs, the balustrade proportions. Not modelled: Mould's carved panels, the individual "
            "Minton tiles, the arcade vault ribs, the Lake and its boats, the lamp standards."),
    }
    return objs, extras


def main() -> None:
    ctx = (("grass", -1.3, 260.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            # The Lake is on the far side of the fountain from the arcade, which this frame builds at +x and
            # the terrace footprints at -y; (-14, -62) is inside the ``terrace0`` prism itself, which is why
            # this render was black (a ray straight up from it hit terrace0 5.2 m overhead).  Standing off
            # the plaza's northern edge puts the fountain in front of the terrace, which is the view.
            dict(view="from_the_lake", cam=(0.0, 62.0, 2.0), target=(0.0, -20.0, 4.0), fov_deg=60.0, context=ctx,
                 sun_azimuth_deg=190.0, sun_elevation_deg=44.0),
            dict(view="terrace", cam=(52.0, 26.0, 12.0), target=(0.0, 0.0, 5.0), fov_deg=58.0, context=ctx,
                 sun_azimuth_deg=230.0, sun_elevation_deg=40.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nThe arcade ceiling")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
