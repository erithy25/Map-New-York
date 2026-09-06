"""Pulaski Bridge — Newtown Creek, McGuinness Boulevard (Greenpoint, Brooklyn) to 11th Street (Long Island City,
Queens).  Opened 10 September 1954; NYC DOT.

Dimensions used (source in brackets)
------------------------------------
* Total length 2,810 ft = **856.5 m**; longest span 177 ft = **53.95 m**; clearance below 39 ft = **11.89 m**;
  **four-leaf bascule** movable span; steel superstructure on reinforced-concrete approaches; five motor-vehicle
  lanes plus pedestrian and bicycle paths (the northbound-side lane became a two-way protected bike lane in 2016)
  [Wikipedia "Pulaski Bridge", NYCDOT].
* Deck width **24.0 m** — *inferred* (+-1.5 m) from the lane count (5 x 3.35 m), the 3.6 m bike lane, a 2.4 m
  sidewalk and parapets; no published width was found.
* Approaches: long concrete viaducts on both sides, carrying the roadway from grade up to the bascule level.

Placement: the two bascule piers are OSM ways ``992001660`` and ``1054539113`` (``bridge:support=pier``); their
measured centre-to-centre separation is **50.79 m** against a published 177 ft (53.95 m) span, so they are snapped
symmetrically to the published value (the OSM polygons draw the pier caps, which sit inside the leaf bearings).
``segments.parquet`` was not available.

Gap: the approach viaducts are modelled for 300 m each side rather than the full 856.5 m published length, because
beyond that the structure is at-grade roadway that the roads stage carries.  The four bascule leaves are modelled in
the closed position with no machinery animation.

Not modelled: the operator's house interior, the counterweight pits and machinery, the trunnion bearings, the traffic
gates and warning signals, and the 2016 bike-lane barrier detail.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_pulaski"
TITLE = "Pulaski Bridge"

MAIN_SPAN = 53.95
CLEARANCE = 11.89
DECK_W = 24.0
MHW = bc.MHW_ABOVE_NAVD88_M
Z_DECK = CLEARANCE + MHW + 2.4        # 14.99 NAVD88 roadway
GROUND = 3.0
APPROACH = 300.0

SUPPORTS = [
    ba.Support("pier_bk", 1054539113, (-227.66, 4332.71), "pier", "Brooklyn (Greenpoint) bascule pier"),
    ba.Support("pier_qn", 992001660, (-219.80, 4382.89), "pier", "Queens (Long Island City) bascule pier"),
]

S_P_BK, S_P_QN = -MAIN_SPAN / 2, MAIN_SPAN / 2
S_END_BK, S_END_QN = S_P_BK - APPROACH, S_P_QN + APPROACH


def deck_z(s: float) -> float:
    if s < S_P_BK:
        u = (S_P_BK - s) / APPROACH
        return Z_DECK - (Z_DECK - 5.5) * u
    if s > S_P_QN:
        u = (s - S_P_QN) / APPROACH
        return Z_DECK - (Z_DECK - 5.5) * u
    return Z_DECK


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("pier_bk", "pier_qn"), MAIN_SPAN, roads_name="Pulaski")
    axis = fit.axis
    objs: list = []
    objs += bl.build_bascule("bascule", axis, 0.0, MAIN_SPAN, Z_DECK, DECK_W, "steel_gray", lod)
    deck = bl.DeckSpec(width=DECK_W, thickness=1.1, lanes=5, lane_w=3.35, roadway_t=-2.6, roadway_w=16.75,
                       walkways=((10.2, 3.6, 0.16), (-11.4, 2.4, 0.16)), truss_depth=0.0, material="asphalt",
                       slab_material="concrete_dark", railing=True, lamps_spacing=40.0, lamp_t=(-11.6, 10.4),
                       centre_yellow=True)
    objs += bl.build_deck("deck", axis, deck, S_END_BK, S_END_QN, deck_z, lod, step=8.0)
    ap = dict(kind="viaduct", pier_spacing=28.0, width=DECK_W, material="concrete", ground_z=GROUND)
    objs += bl.build_approach("ap_bk", axis, bl.ApproachSpec(S_END_BK, S_P_BK - 6.0, deck_z(S_END_BK), Z_DECK, **ap), lod)
    objs += bl.build_approach("ap_qn", axis, bl.ApproachSpec(S_P_QN + 6.0, S_END_QN, Z_DECK, deck_z(S_END_QN), **ap), lod)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": Z_DECK, "name": TITLE,
        "main_span_m": MAIN_SPAN, "clearance_m": CLEARANCE, "deck_width_m": DECK_W, "type": "four-leaf bascule",
        "lanes": 5, "total_modelled_length_m": S_END_QN - S_END_BK, "published_total_length_m": 856.5,
        "alignment_source": fit.source,
        "height_source": "Wikipedia/NYCDOT: 2,810 ft total, 177 ft longest span, 39 ft clearance",
        "sources_ids": ["osm_bbbike", "published_pulaski"],
        "fidelity_statement": (
            "Exact to published values: 53.95 m bascule span, 11.89 m clearance, four-leaf bascule form, five motor "
            "lanes plus the 2016 two-way protected bike lane and a sidewalk. Inferred: 24.0 m deck width (+-1.5 m, "
            "no published figure), approach grade and pier spacing, pier-house size. Gaps: 300 m of approach viaduct "
            "each side instead of the published 856.5 m total; the leaves are fixed closed with no machinery. Not "
            "modelled: operator's house interior, counterweight pits and machinery, trunnion bearings, traffic gates "
            "and signals, bike-lane barrier detail."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("pier_bk", "pier_qn"), MAIN_SPAN)
    ax = fit.axis
    ctx = (("water_dark", 0.35, 200.0, (0.0, 0.0)),
           ("sidewalk", GROUND, 320.0, (ax.p(-360.0, 0.0).x, ax.p(-360.0, 0.0).y)),
           ("sidewalk", GROUND, 320.0, (ax.p(360.0, 0.0).x, ax.p(360.0, 0.0).y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_pulaski_bridge", fit.frame, view="pulaski_reference",
                                ground_z=GROUND, target_z=16.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="newtown_creek", cam=ax.p(-90.0, -140.0, GROUND + 2.0), target=ax.p(40.0, 0.0, 14.0),
                 fov_deg=60.0, context=ctx, sun_azimuth_deg=230.0, sun_elevation_deg=35.0),
            dict(view="roadway", cam=ax.p(-160.0, -2.6, deck_z(-160.0) + 2.0), target=ax.p(200.0, -2.6, Z_DECK + 3.0),
                 fov_deg=58.0, context=ctx, sun_azimuth_deg=110.0, sun_elevation_deg=42.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
