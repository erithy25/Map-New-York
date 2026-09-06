"""Ed Koch Queensboro Bridge (59th Street Bridge) — East River, Manhattan (Second Avenue at 59th Street) over
Roosevelt Island to Long Island City, Queens.  Gustav Lindenthal (engineer) with Henry Hornbostel (architect), opened
30 March 1909.  NYC Landmark LP-1226, NRHP 1978.

Dimensions used (source in brackets)
------------------------------------
* **Double-decked cantilever bridge**, five steel spans, measured Manhattan to Queens [Wikipedia "Queensboro Bridge"]:

  | span | published | modelled | measured between the OSM pier centroids |
  |---|---|---|---|
  | 1 York Avenue | 469.5 ft = 143.1 m | 143.1 m | 141.3 m |
  | 2 East River west channel | 1,182 ft = 360.3 m | 360.3 m | 360.9 m |
  | 3 over Roosevelt Island | 630 ft = 192.0 m | 192.0 m | 191.2 m |
  | 4 East River east channel | 984 ft = 300.0 m | 300.0 m | 300.7 m |
  | 5 Vernon Boulevard | 459 ft = 139.9 m | 139.9 m | 139.2 m |

  Total steel length 1,135.3 m; total length with approaches 7,449 ft = 2,270 m; deck width 100 ft = **30.48 m**;
  overall height 350 ft = **106.68 m**; clearance below 130 ft = **39.62 m**; the truss towers stand 185 ft = **56.4 m**
  above the lower chords; the masonry piers are 100-125 ft (30.5-38.1 m) tall.
* Decks: **upper level 4 lanes** (two roadways of 2), **lower level 4 vehicular lanes** plus the pedestrian/bicycle
  path on the north side.  The lower roadway rides the level bottom chord for the whole length, so the model uses the
  bottom chord as the truss reference line (``top_frac=1.0, bot_frac=0.0``) and lets the top chord rise from 10.5 m
  above it at mid-span to the 106.68 m tower tops over the piers.
* Colour: the current buff/tan paint scheme.

Placement: all four river piers and both abutments are OSM ``bridge:support`` ways — ``1016487161`` (Manhattan
abutment), ``1016487159``, ``1016487155``, ``1016487154``, ``1016487157`` (piers, west to east) and ``1016487170``
(Queens abutment).  The five measured spans are within **1.3 %** of the published set (see the table); each is snapped
to its published value about the pier-2/pier-3 midpoint.  ``segments.parquet`` was not available.

Not modelled: the Hornbostel terracotta and the Guastavino-vaulted market under the Manhattan approach, the demolished
Roosevelt Island elevator/trolley kiosk, the finials on the pier towers in detail, the rivet and gusset plates, the
1930s-1950s roadway rebuilds, and the Queens Plaza ramp network.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_queensboro_bridge"
TITLE = "Ed Koch Queensboro Bridge"

SPANS = (143.1, 360.3, 192.0, 300.0, 139.9)      # Manhattan -> Queens
DECK_W = 30.48
HEIGHT = 106.68
CLEARANCE_MHW = 39.62
MHW = bc.MHW_ABOVE_NAVD88_M
Z_LOWER = CLEARANCE_MHW + MHW + 1.2              # 41.52 NAVD88 lower roadway (bottom chord)
DECK_GAP = 10.5
Z_UPPER = Z_LOWER + DECK_GAP                     # 52.02
Z_TOWER_TOP = HEIGHT + MHW                       # 107.38
DEPTH_PIER = Z_TOWER_TOP - Z_LOWER               # 65.86 (bottom chord level, top chord at the tower tops)
DEPTH_MID = DECK_GAP
GROUND = 4.0

SUPPORTS = [
    ba.Support("abut_mn", 1016487161, (-893.78, 6608.11), "abutment", "Manhattan abutment (York Avenue)"),
    ba.Support("pier1", 1016487159, (-770.94, 6538.24), "pier", "Manhattan-shore pier"),
    ba.Support("pier2", 1016487155, (-457.40, 6359.42), "pier", "west channel pier (Roosevelt Island west)"),
    ba.Support("pier3", 1016487154, (-291.55, 6264.24), "pier", "east channel pier (Roosevelt Island east)"),
    ba.Support("pier4", 1016487157, (-30.11, 6115.66), "pier", "Queens-shore pier"),
    ba.Support("abut_qn", 1016487170, (91.54, 6047.92), "abutment", "Queens abutment (Vernon Boulevard)"),
]

# s runs Manhattan (-) -> Queens (+); the frame origin is the midpoint of pier2/pier3 (the Roosevelt Island span)
S_P2 = -SPANS[2] / 2
S_P3 = +SPANS[2] / 2
S_P1 = S_P2 - SPANS[1]
S_P4 = S_P3 + SPANS[3]
S_ABUT_MN = S_P1 - SPANS[0]
S_ABUT_QN = S_P4 + SPANS[4]
PIERS = (S_ABUT_MN, S_P1, S_P2, S_P3, S_P4, S_ABUT_QN)
APPROACH = 400.0


def deck_z(s: float) -> float:
    return Z_LOWER


def upper_z(s: float) -> float:
    return Z_UPPER


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("pier2", "pier3"), SPANS[2], heading_from=("abut_mn", "abut_qn"),
                         roads_name="Queensboro")
    axis = fit.axis
    objs: list = []
    objs += bl.build_cantilever_truss("qb", axis, PIERS, deck_z, DEPTH_PIER, DEPTH_MID, DECK_W, "steel_tan", lod,
                                      panel=11.0, pier_spec={"width": DECK_W + 8.0, "depth": 16.0,
                                                             "material": "granite_dark"},
                                      z_water=-8.0, top_frac=1.0, bot_frac=0.0)
    # lower deck (4 lanes + north pedestrian/bicycle path) on the bottom chord
    lower = bl.DeckSpec(width=DECK_W - 2.0, thickness=0.8, lanes=4, lane_w=3.2, roadway_t=-1.6, roadway_w=12.8,
                        walkways=((11.6, 3.6, 0.2),), truss_depth=0.0, material="asphalt",
                        slab_material="steel_tan", railing=True, centre_yellow=False)
    objs += bl.build_deck("lower", axis, lower, S_ABUT_MN, S_ABUT_QN, deck_z, lod, step=11.0)
    # upper deck: two roadways of two lanes at the outer edges
    upper_slab = bl.sweep("upper_slab", axis, bl.samples(S_ABUT_MN, S_ABUT_QN, 11.0),
                          bl.rect_section(DECK_W - 3.0, 0.7, 0.0, 0.0), upper_z, "steel_tan")
    objs.append(upper_slab)
    for t, nm in ((-9.5, "w"), (9.5, "e")):
        objs.append(bl.sweep(f"upper_road_{nm}", axis, bl.samples(S_ABUT_MN, S_ABUT_QN, 11.0),
                             bl.rect_section(6.7, 0.08, t, 0.08), upper_z, "asphalt"))
        if lod == 0:
            parts = []
            n = max(int((S_ABUT_QN - S_ABUT_MN) / 110.0), 1)
            for k in range(n):
                a = S_ABUT_MN + (S_ABUT_QN - S_ABUT_MN) * k / n
                b = S_ABUT_MN + (S_ABUT_QN - S_ABUT_MN) * (k + 1) / n
                lm = bc.lane_markings(f"upper_lm_{nm}{k}", axis.p(a, 0, Z_UPPER), axis.p(b, 0, Z_UPPER), 3.35, 2, 0.09,
                                      centre_yellow=False, offset_t=t)
                if lm is not None:
                    parts.append(lm)
            objs.append(bc.join(parts, f"upper_markings_{nm}"))
    if lod == 0:
        rails = []
        n = max(int((S_ABUT_QN - S_ABUT_MN) / 60.0), 1)
        for side in (-1, 1):
            for k in range(n):
                a = S_ABUT_MN + (S_ABUT_QN - S_ABUT_MN) * k / n
                b = S_ABUT_MN + (S_ABUT_QN - S_ABUT_MN) * (k + 1) / n
                rails.append(bc.railing(f"upper_rail{side}_{k}", axis.p(a, side * (DECK_W / 2 - 1.7), Z_UPPER),
                                        axis.p(b, side * (DECK_W / 2 - 1.7), Z_UPPER), 1.2, 3.0))
        objs.append(bc.join(rails, "upper_railing"))

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.8, lanes=4, lane_w=3.35, roadway_w=13.4, material="asphalt",
                          slab_material="steel_tan", railing=True, centre_yellow=False)
    objs += bl.build_approach("ap_mn", axis, bl.ApproachSpec(S_ABUT_MN - APPROACH, S_ABUT_MN, 12.0, Z_LOWER, "girder",
                                                            pier_spacing=30.0, width=DECK_W, material="steel_tan",
                                                            ground_z=GROUND), lod, ap_deck)
    objs += bl.build_approach("ap_qn", axis, bl.ApproachSpec(S_ABUT_QN, S_ABUT_QN + APPROACH, Z_LOWER, 12.0, "girder",
                                                            pier_spacing=30.0, width=DECK_W, material="steel_tan",
                                                            ground_z=GROUND), lod, ap_deck)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": HEIGHT, "name": TITLE,
        "lp_number": "LP-1226", "spans_m": list(SPANS), "longest_span_m": SPANS[1], "deck_width_m": DECK_W,
        "clearance_mhw_m": CLEARANCE_MHW, "upper_lanes": 4, "lower_lanes": 4,
        "steel_length_m": sum(SPANS), "total_modelled_length_m": sum(SPANS) + 2 * APPROACH,
        "alignment_source": fit.source,
        "height_source": "Wikipedia/NYCDOT: 350 ft height, 1,182 ft longest span, 130 ft clearance, 100 ft width",
        "sources_ids": ["osm_bbbike", "published_queensboro"],
        "fidelity_statement": (
            "Exact to published values: all five span lengths (143.1 / 360.3 / 192.0 / 300.0 / 139.9 m), 30.48 m "
            "deck, 106.68 m overall height, 39.62 m clearance, double deck with 4 upper and 4 lower lanes plus the "
            "north pedestrian/bicycle path, cantilever trusses on four masonry river piers whose measured positions "
            "agree with the published spans to 1.3 %. Inferred: 10.5 m deck-to-deck spacing, truss panel length, "
            "pier plan dimensions, approach ramp elevations. Gap: the approaches are modelled for 400 m each rather "
            "than the full published 2,270 m over-all length. Not modelled: the Guastavino-vaulted market under the "
            "Manhattan approach, the Hornbostel terracotta, the demolished Roosevelt Island kiosk, rivets and "
            "gussets, the Queens Plaza ramp network."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("pier2", "pier3"), SPANS[2], heading_from=("abut_mn", "abut_qn"))
    ax = fit.axis
    isl = ax.p(0.0, 0.0)
    land_mn, land_qn = ax.p(-820.0, 0.0), ax.p(700.0, 0.0)
    ctx = (("water_dark", 0.35, 1600.0, (0.0, 0.0)),
           ("grass", GROUND, 120.0, (isl.x, isl.y)),
           ("ground_urban", GROUND, 420.0, (land_mn.x, land_mn.y)),
           ("ground_urban", GROUND, 420.0, (land_qn.x, land_qn.y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_queensboro_bridge", fit.frame, view="queensboro_reference",
                                ground_z=GROUND, target_z=60.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="elevation_from_river", cam=ax.p(-120.0, -520.0, 20.0), target=ax.p(-120.0, 0.0, 55.0),
                 fov_deg=52.0, context=ctx, sun_azimuth_deg=200.0, sun_elevation_deg=32.0),
            dict(view="roosevelt_island", cam=ax.p(30.0, -95.0, GROUND + 2.0), target=ax.p(-260.0, 0.0, 70.0),
                 fov_deg=62.0, context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=34.0),
            dict(view="upper_deck", cam=ax.p(S_P1 - 30.0, -9.5, Z_UPPER + 2.0), target=ax.p(S_P3, -3.0, Z_UPPER + 25.0),
                 fov_deg=60.0, context=ctx, sun_azimuth_deg=120.0, sun_elevation_deg=42.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
