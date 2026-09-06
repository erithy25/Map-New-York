"""High Bridge (Aqueduct Bridge) — Harlem River, Highbridge Park (Manhattan) to Highbridge (the Bronx).  John B.
Jervis for the Croton Aqueduct, 1848; the oldest bridge in New York City.  NHL 1972, NYC Landmark LP-0951.

Dimensions used (source in brackets)
------------------------------------
* Length **1,450 ft = 442.0 m**; the deck stands **138 ft = 42.06 m** above the Harlem River [NYC Parks, HAER
  NY-127, Wikipedia "High Bridge (New York City)"].
* Originally **15 masonry arches** — five of 80 ft (24.4 m) over the river channel and ten of 50 ft (15.24 m) over
  land.  In **1927-28 the five river arches were removed** and replaced by a single **steel arch of 450 ft =
  137.16 m** to widen the navigation channel; the ten land arches survive.  The model builds that post-1928 state.
* It carried two 90-inch (2.29 m) Croton Aqueduct pipes under a promenade; it reopened as a pedestrian and cycle
  bridge in June 2015.
* Deck width: **7.3 m** — *inferred* (+-1 m) from the OSM bridge polygon and photographs; no published width was found.

Placement: from the OSM way ``60251530`` (``name=High Bridge``, ``highway=cycleway``, ``bridge=yes``) whose end
vertices are NYC_TM (1566.3, 15818.9) and (1907.7, 15775.9) — 344.1 m apart on a heading of 97.2 deg.  The published
442.0 m is built symmetrically about that way's midpoint; the extra 98 m is the abutment masonry at each end, which
OSM does not draw.  The steel arch is centred 55 m west of the midpoint over the navigation channel (*inferred*
+-30 m: no OSM feature marks the channel).  ``segments.parquet`` was not available and this crossing carries no road.

Not modelled: the two aqueduct pipes inside the deck, the granite coursing, the 1864-vintage cast-iron railing
pattern, the Highbridge Water Tower (a separate landmark 200 m to the east), the 2015 reconstruction's lighting, and
the stairs and ramps at either end.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_high_bridge"
TITLE = "High Bridge"

LENGTH = 442.0
DECK_ABOVE_RIVER = 42.06
STEEL_ARCH_SPAN = 137.16
LAND_ARCH_SPAN = 15.24
WIDTH = 7.3
MHW = bc.MHW_ABOVE_NAVD88_M
Z_DECK = DECK_ABOVE_RIVER + MHW      # 42.76 NAVD88
GROUND = 3.0
S_ARCH_C = -55.0                     # centre of the 1928 steel arch (inferred)

END_A_TM = (1566.3, 15818.9)         # west (Manhattan) end of the OSM deck way
END_B_TM = (1907.7, 15775.9)         # east (Bronx) end


def build(lod: int = 0):
    mid = ((END_A_TM[0] + END_B_TM[0]) / 2, (END_A_TM[1] + END_B_TM[1]) / 2)
    dx, dy = END_B_TM[0] - END_A_TM[0], END_B_TM[1] - END_A_TM[1]
    L = math.hypot(dx, dy)
    heading = math.degrees(math.atan2(dx / L, dy / L)) % 360.0
    frame = ba.frame_at(mid[0], mid[1], 0.0, heading)
    axis = bl.Axis(Vector((0.0, 0.0, 0.0)), Vector((dx / L, dy / L, 0.0)))
    objs: list = []
    s0, s1 = -LENGTH / 2, LENGTH / 2
    a0, a1 = S_ARCH_C - STEEL_ARCH_SPAN / 2, S_ARCH_C + STEEL_ARCH_SPAN / 2

    # ---- surviving masonry arches either side of the 1928 steel arch --------------------------------------------
    objs += bl.build_masonry_arches("west_arches", axis, s0, a0 - 4.0, LAND_ARCH_SPAN, 5.5, Z_DECK, GROUND, WIDTH + 2.4,
                                    "granite_gray", lod)
    objs += bl.build_masonry_arches("east_arches", axis, a1 + 4.0, s1, LAND_ARCH_SPAN, 5.5, Z_DECK, GROUND, WIDTH + 2.4,
                                    "granite_gray", lod)
    # ---- 1928 steel arch over the navigation channel ------------------------------------------------------------
    objs += bl.build_steel_arch("steel_arch", axis, a0, a1, Z_DECK - 2.0, (Z_DECK - 2.0 - 10.0) * 0.0 + 22.0,
                                WIDTH + 1.0, "steel_green", lod, n=32 if lod == 0 else 14, through=False,
                                rib_depth=2.2, hanger_spacing=8.0)
    for s_end in (a0, a1):
        pier = bc.box("arch_skewback", (9.0, WIDTH + 6.0, Z_DECK - 3.0 - (GROUND - 4.0)), (0, 0, GROUND - 4.0),
                      "granite_gray")
        bc.transform(pier, axis.matrix(s_end))
        objs.append(pier)

    # ---- promenade deck, parapets and lamps ---------------------------------------------------------------------
    ss = bl.samples(s0, s1, 6.0)
    objs.append(bl.sweep("deck", axis, ss, bl.rect_section(WIDTH + 2.4, 1.1, 0.0, 0.0), lambda s: Z_DECK, "granite_gray"))
    objs.append(bl.sweep("walk", axis, ss, bl.rect_section(WIDTH, 0.12, 0.0, 0.12), lambda s: Z_DECK, "sidewalk"))
    for side in (-1, 1):
        objs.append(bl.sweep(f"parapet{side}", axis, ss, bl.rect_section(0.7, 1.0, side * (WIDTH / 2 + 0.85), 1.0),
                             lambda s: Z_DECK, "granite_gray"))
    if lod == 0:
        rails, lamps = [], []
        n = int(LENGTH / 30.0)
        for side in (-1, 1):
            for k in range(n):
                a = s0 + LENGTH * k / n
                b = s0 + LENGTH * (k + 1) / n
                rails.append(bc.railing(f"rail{side}_{k}", axis.p(a, side * (WIDTH / 2 + 0.85), Z_DECK + 1.0),
                                        axis.p(b, side * (WIDTH / 2 + 0.85), Z_DECK + 1.0), 1.05, 2.2, "steel_black", 4))
        objs.append(bc.join(rails, "railings"))
        s = s0 + 18.0
        while s < s1:
            for side in (-1, 1):
                lamps.append(bc.lamp_post("lamp", axis.p(s, side * (WIDTH / 2 + 0.4), Z_DECK + 0.12), 4.6, 0.0, 0.0))
            s += 36.0
        objs.append(bc.join(lamps, "lamps"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": DECK_ABOVE_RIVER, "name": TITLE,
        "lp_number": "LP-0951", "length_m": LENGTH, "deck_above_river_m": DECK_ABOVE_RIVER,
        "steel_arch_span_m": STEEL_ARCH_SPAN, "land_arch_span_m": LAND_ARCH_SPAN, "deck_width_m": WIDTH,
        "state_modelled": "post-1928 (five river arches replaced by one steel arch)",
        "alignment_source": "OSM way 60251530 (name=High Bridge, highway=cycleway, bridge=yes) end vertices",
        "height_source": "NYC Parks / HAER NY-127: 1,450 ft long, deck 138 ft above the Harlem River, 450 ft steel arch",
        "sources_ids": ["osm_bbbike", "published_high_bridge"],
        "fidelity_statement": (
            "Exact to published values: 442.0 m length, 42.06 m deck above the river, the 137.16 m 1928 steel arch "
            "replacing the five 80 ft river arches, and the surviving 15.24 m masonry land arches. Inferred: 7.3 m "
            "deck width (+-1 m, no published figure), the steel arch's position 55 m west of the OSM way midpoint "
            "(+-30 m), arch rise, pier widths, lamp and railing spacing. Not modelled: the two 90-inch Croton "
            "Aqueduct pipes inside the deck, granite coursing, the historic cast-iron railing pattern, the "
            "Highbridge Water Tower, the 2015 lighting, and the end stairs and ramps."),
    }
    return objs, extras


def main() -> None:
    mid = ((END_A_TM[0] + END_B_TM[0]) / 2, (END_A_TM[1] + END_B_TM[1]) / 2)
    dx, dy = END_B_TM[0] - END_A_TM[0], END_B_TM[1] - END_A_TM[1]
    L = math.hypot(dx, dy)
    heading = math.degrees(math.atan2(dx / L, dy / L)) % 360.0
    frame = ba.frame_at(mid[0], mid[1], 0.0, heading)
    axis = bl.Axis(Vector((0.0, 0.0, 0.0)), Vector((dx / L, dy / L, 0.0)))
    ctx = (("water_dark", 0.35, 400.0, (axis.p(S_ARCH_C, 0.0).x, axis.p(S_ARCH_C, 0.0).y)),
           ("grass", GROUND, 300.0, (axis.p(200.0, 0.0).x, axis.p(200.0, 0.0).y)),
           ("grass", GROUND, 200.0, (axis.p(-260.0, 0.0).x, axis.p(-260.0, 0.0).y)))
    _ = frame
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_high_bridge", frame, view="high_bridge_reference",
                                ground_z=GROUND, target_z=28.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="from_the_bronx_shore", cam=axis.p(180.0, -160.0, GROUND + 2.0), target=axis.p(-60.0, 0.0, 28.0),
                 fov_deg=58.0, context=ctx, sun_azimuth_deg=200.0, sun_elevation_deg=34.0),
            dict(view="promenade", cam=axis.p(-180.0, 0.0, Z_DECK + 1.8), target=axis.p(200.0, 0.0, Z_DECK + 2.0),
                 fov_deg=62.0, context=ctx, sun_azimuth_deg=110.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": f"origin NYC_TM ({mid[0]:.1f}, {mid[1]:.1f}), heading {heading:.2f} deg, from the end "
                               f"vertices of OSM way 60251530 (measured 344.1 m, published length 442.0 m built "
                               f"symmetrically about the midpoint).",
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
