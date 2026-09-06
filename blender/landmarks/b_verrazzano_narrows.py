"""Verrazzano-Narrows Bridge — The Narrows, Fort Wadsworth (Staten Island) to Bay Ridge (Brooklyn).  Othmar Ammann,
opened 21 November 1964 (upper level) and 28 June 1969 (lower level).

Dimensions used (source in brackets)
------------------------------------
* Main span 4,260 ft = **1,298.4 m**; total length 13,700 ft = **4,176 m**; deck width 103 ft = **31.39 m**; towers
  693 ft = **211.2 m**; clearance below at mean high water 228 ft = **69.49 m**; upper deck **7 lanes**, lower deck
  **6 lanes**; four main cables 36 in = **0.914 m** diameter, 26,108 wires each; anchorages 229 x 129 ft =
  **69.8 x 39.3 m** [Wikipedia "Verrazzano-Narrows Bridge", MTA Bridges & Tunnels].
* Side spans **1,215 ft = 370.3 m** each (the standard published figure; the article gives only the main span).  The
  suspended structure is therefore 2,039.0 m and the remaining 2,137 m of the published total is approach viaduct.
* The tower tops are 1-5/8 in (41.3 mm) further apart than their bases because of the curvature of the Earth — a
  0.003 % effect, below this model's resolution and therefore **not** reproduced (stated).
* Cable sag **117.3 m**: the cable low point sits 3.1 m above the upper deck at mid-span.
* Towers: steel portal towers, each two cellular legs with four portal struts; two cables pass over each leg
  (**inferred** plane offsets +-12.0 / +-14.8 m, +-0.5 m).

Placement: towers are OSM ways ``1016642058`` (Staten Island) and ``1016642060`` (Brooklyn),
``bridge:support=pylon``; measured separation **1,298.68 m**, 0.02 % from the published 4,260 ft.  Anchorages are OSM
ways ``899356447`` (Staten Island) and ``899356446`` (Brooklyn); their centroids sit 389 m and 401 m from their
towers, i.e. 19-31 m beyond the published 1,215 ft side span, so the model puts the cable-entry face at exactly
370.3 m and the anchorage block behind it.  ``segments.parquet`` was not available.

Not modelled: the cable bands and wrapping, the 2017-2021 upper-deck replacement's orthotropic panels, the Fort
Wadsworth and Fort Hamilton batteries under the anchorages, the toll gantry, the Belt Parkway and Staten Island
Expressway interchanges, and the tower elevator machinery.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_verrazzano_narrows"
TITLE = "Verrazzano-Narrows Bridge"

MAIN_SPAN = 1298.4
SIDE_SPAN = 370.3
DECK_W = 31.39
TOWER_H = 211.2
CLEARANCE_MHW = 69.49
CABLE_D = 0.914
CABLE_SAG = 117.3
CABLE_T = (-14.8, -12.0, 12.0, 14.8)
ANCH_L, ANCH_W = 69.8, 39.3
MHW = bc.MHW_ABOVE_NAVD88_M

Z_LOWER_MID = CLEARANCE_MHW + MHW + 1.4      # 71.59 NAVD88
DECK_GAP = 10.7
Z_UPPER_MID = Z_LOWER_MID + DECK_GAP         # 82.29
Z_TOWER_TOP = TOWER_H + MHW                  # 211.9
Z_SADDLE = Z_UPPER_MID + 3.1 + CABLE_SAG     # 202.69 -> 9.2 m below the tower top
Z_CABLE_LOW = Z_SADDLE - CABLE_SAG
Z_UPPER_TOWER = Z_UPPER_MID - 9.0
Z_UPPER_ANCH = Z_UPPER_MID - 17.0
GROUND_SI = 12.0
GROUND_BK = 10.0

SUPPORTS = [
    ba.Support("tower_si", 1016642058, (-8675.74, -10649.30), "pylon", "Staten Island tower"),
    ba.Support("tower_bk", 1016642060, (-7479.44, -10143.90), "pylon", "Brooklyn tower"),
    ba.Support("anchorage_si", 899356447, (-9034.17, -10801.09), "anchorage", "Staten Island anchorage"),
    ba.Support("anchorage_bk", 899356446, (-7110.00, -9988.63), "anchorage", "Brooklyn anchorage"),
]

S_T_SI, S_T_BK = -MAIN_SPAN / 2, MAIN_SPAN / 2      # +s runs Staten Island -> Brooklyn
S_AF_SI, S_AF_BK = S_T_SI - SIDE_SPAN, S_T_BK + SIDE_SPAN
S_A_SI, S_A_BK = S_AF_SI - ANCH_L / 2, S_AF_BK + ANCH_L / 2
S_END_SI, S_END_BK = S_A_SI - 300.0, S_A_BK + 300.0


def upper_z(s: float) -> float:
    if s < S_T_SI:
        u = min(1.0, max(0.0, (s - S_AF_SI) / SIDE_SPAN))
        return Z_UPPER_ANCH + (Z_UPPER_TOWER - Z_UPPER_ANCH) * u
    if s <= S_T_BK:
        u = s / (MAIN_SPAN / 2)
        return Z_UPPER_MID - (Z_UPPER_MID - Z_UPPER_TOWER) * u * u
    u = min(1.0, (s - S_T_BK) / SIDE_SPAN)
    return Z_UPPER_TOWER + (Z_UPPER_ANCH - Z_UPPER_TOWER) * u


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_si", "tower_bk"), MAIN_SPAN, roads_name="Verrazzano")
    axis = fit.axis
    objs: list = []
    tower = bl.TowerSpec(kind="portal", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=DECK_W + 5.0, depth_s=13.5,
                         z_base=-25.0, z_deck=Z_UPPER_TOWER, leg_w=10.5, leg_d=13.5, leg_taper=0.58,
                         struts_z=(Z_LOWER_MID - 12.0, Z_UPPER_TOWER + 9.0, 145.0, Z_TOWER_TOP - 6.0), x_brace=False,
                         pier_w=DECK_W + 14.0, pier_d=24.0, material="steel_gray", pier_material="concrete",
                         cable_t=CABLE_T)
    objs += bl.build_tower("tower_si", axis, S_T_SI, tower, lod)
    objs += bl.build_tower("tower_bk", axis, S_T_BK, tower, lod)

    anch_si = bl.AnchorageSpec(S_A_SI, ANCH_L, ANCH_W + 30.0, GROUND_SI + 40.0, GROUND_SI - 16.0, "concrete",
                               Z_UPPER_ANCH - 8.0, slope=False)
    anch_bk = bl.AnchorageSpec(S_A_BK, ANCH_L, ANCH_W + 30.0, GROUND_BK + 40.0, GROUND_BK - 16.0, "concrete",
                               Z_UPPER_ANCH - 8.0, slope=False)
    objs += bl.build_anchorage("anch_si", axis, anch_si, S_T_SI)
    objs += bl.build_anchorage("anch_bk", axis, anch_bk, S_T_BK)

    deck = bl.DeckSpec(width=DECK_W, thickness=1.0, lanes=7, lane_w=3.66, roadway_t=0.0, roadway_w=25.6,
                       truss_depth=DECK_GAP, truss_t=(-DECK_W / 2 + 0.7, DECK_W / 2 - 0.7), truss_above=False,
                       truss_panel=10.4, truss_material="steel_gray", material="asphalt", slab_material="steel_gray",
                       lower_deck_dz=-DECK_GAP, lower_lanes=6, lower_width=DECK_W - 3.0, railing=True,
                       lamps_spacing=54.0, lamp_t=(-DECK_W / 2 + 1.0, DECK_W / 2 - 1.0), centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_AF_SI, S_AF_BK, upper_z, lod, step=9.0)

    cables = bl.CableSpec(t_offsets=CABLE_T, radius=CABLE_D / 2, z_low_mid=Z_CABLE_LOW, suspender_spacing=15.24,
                          suspender_radius=0.055, suspender_pairs=True, material="steel_silver",
                          suspender_material="steel_gray")
    objs += bl.build_suspension_cables("cable", axis, cables, (S_T_SI, S_T_BK), Z_SADDLE, (anch_si, anch_bk), upper_z,
                                       0.6, lod)

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.8, lanes=7, lane_w=3.66, roadway_w=25.6, material="asphalt",
                          slab_material="concrete_dark", railing=True, centre_yellow=False)
    objs += bl.build_approach("ap_si", axis, bl.ApproachSpec(S_END_SI, S_AF_SI, Z_UPPER_ANCH - 8.0, Z_UPPER_ANCH,
                                                            "viaduct", pier_spacing=45.0, width=DECK_W,
                                                            material="concrete", ground_z=GROUND_SI), lod, ap_deck)
    objs += bl.build_approach("ap_bk", axis, bl.ApproachSpec(S_AF_BK, S_END_BK, Z_UPPER_ANCH, Z_UPPER_ANCH - 8.0,
                                                            "viaduct", pier_spacing=45.0, width=DECK_W,
                                                            material="concrete", ground_z=GROUND_BK), lod, ap_deck)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": TOWER_H, "name": TITLE,
        "main_span_m": MAIN_SPAN, "side_span_m": SIDE_SPAN, "deck_width_m": DECK_W, "tower_height_m": TOWER_H,
        "clearance_mhw_m": CLEARANCE_MHW, "cable_diameter_m": CABLE_D, "cable_sag_m": CABLE_SAG, "n_cables": 4,
        "upper_lanes": 7, "lower_lanes": 6, "total_modelled_length_m": S_END_BK - S_END_SI,
        "alignment_source": fit.source,
        "height_source": "Wikipedia/MTA B&T: 693 ft towers, 4,260 ft main span, 228 ft clearance, 36 in cables",
        "sources_ids": ["osm_bbbike", "published_verrazzano"],
        "fidelity_statement": (
            "Exact to published values: 1,298.4 m main span, 370.3 m side spans, 31.39 m deck, 211.2 m portal towers, "
            "69.49 m clearance, four 0.914 m cables, 7 upper / 6 lower lanes, 69.8 x 39.3 m anchorages. Inferred: "
            "cable plane offsets (+-0.5 m), 117.3 m sag, deck elevations away from the published mid-span clearance, "
            "approach viaduct pier spacing and ground elevations, 15.24 m (50 ft) suspender pitch. Deliberately not "
            "reproduced: the 41.3 mm extra spacing of the tower tops caused by the curvature of the Earth (0.003 %). "
            "Not modelled: cable bands and wrapping, the 2017-2021 orthotropic upper deck, Fort Wadsworth and Fort "
            "Hamilton, the toll gantry, the Belt Parkway and Staten Island Expressway interchanges."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("tower_si", "tower_bk"), MAIN_SPAN)
    ax = fit.axis
    land_si, land_bk = ax.p(-1150.0, 0.0), ax.p(1150.0, 0.0)
    ctx = (("water_dark", 0.35, 2600.0, (0.0, 0.0)),
           ("grass", GROUND_SI, 460.0, (land_si.x, land_si.y)),
           ("grass", GROUND_BK, 460.0, (land_bk.x, land_bk.y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_verrazzano_narrows_bridge", fit.frame, view="bay_ridge_reference",
                                ground_z=GROUND_BK, target_z=120.0, fov_deg=48.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="shore_road_bay_ridge", cam=ax.p(S_T_BK + 120.0, -330.0, GROUND_BK + 2.0),
                 target=ax.p(S_T_BK - 200.0, 0.0, 140.0), fov_deg=62.0, context=ctx, sun_azimuth_deg=250.0,
                 sun_elevation_deg=28.0),
            dict(view="elevation_from_narrows", cam=ax.p(0.0, -1900.0, 60.0), target=ax.p(0.0, 0.0, 120.0),
                 fov_deg=40.0, context=ctx, sun_azimuth_deg=200.0, sun_elevation_deg=30.0),
            dict(view="upper_deck", cam=ax.p(S_T_SI - 40.0, -8.0, Z_UPPER_MID + 2.2),
                 target=ax.p(S_T_SI + 400.0, 0.0, Z_UPPER_MID + 40.0), fov_deg=58.0, context=ctx,
                 sun_azimuth_deg=120.0, sun_elevation_deg=42.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
