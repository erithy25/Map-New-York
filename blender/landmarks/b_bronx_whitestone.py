"""Bronx-Whitestone Bridge — East River, Ferry Point (Bronx) to Whitestone (Queens).  Othmar Ammann with Aymar
Embury II, opened 29 April 1939.  MTA Bridges & Tunnels.

Dimensions used (source in brackets)
------------------------------------
* Main span 2,300 ft = **701.04 m**; side spans 735 ft = **224.03 m** each; total length 3,770 ft = **1,149 m**; deck
  width between the cables 74 ft = **22.56 m**; towers **114.9 m** above mean high water (377 ft); clearance below
  134 ft 10 in = **41.10 m**; **6 lanes**; each cable 3,965 ft long with 9,862 wires in 37 strands of 266 wires
  0.196 in (5.0 mm) thick [Wikipedia "Bronx-Whitestone Bridge", MTA Bridges & Tunnels].
* Structural history, all three states published: the 1939 deck was a plate girder 11 ft deep (the Art Deco
  "streamlined" original); 14 ft = 4.27 m stiffening trusses were added in the 1940s after Tacoma Narrows and the
  walkways removed to make six lanes (1947); in 2003-2005 those trusses were removed again and replaced by
  **triangular fibreglass fairings** along both sides of the deck, cutting the suspended mass by ~6,000 tons.
  **This model builds the current (post-2005) state**: plate-girder deck with the triangular fairings.
* Two main cables at t = +-11.28 m (the published 74 ft between cables); Art Deco steel towers with the deep
  horizontal struts of Ammann's 1930s vocabulary.

Placement: towers are OSM ways ``1016686393`` (Bronx) and ``1016686394`` (Queens); their measured separation is
**701.15 m**, 0.02 % from the published 2,300 ft.  Anchorages are OSM ways ``1016686391`` (Bronx) and ``1016686396``
(Queens), 230.4 m and 231.5 m from their towers, i.e. 6-7 m beyond the published 735 ft side span.

Not modelled: the cable bands and wrapping, the toll gantry, the Hutchinson River Parkway and Whitestone Expressway
interchanges, the 1939 World's Fair-era lamp standards (replaced), and the aerodynamic tuned mass dampers.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_bronx_whitestone"
TITLE = "Bronx-Whitestone Bridge"

MAIN_SPAN = 701.04
SIDE_SPAN = 224.03
DECK_W = 22.56
TOWER_H_MHW = 114.9
CLEARANCE_MHW = 41.10
CABLE_T = (-11.28, 11.28)
FAIRING_H = 2.4        # triangular fibreglass fairing (2003-2005)
MHW = bc.MHW_ABOVE_NAVD88_M

Z_DECK_MID = CLEARANCE_MHW + MHW + 3.4       # 45.2 NAVD88 roadway top (clearance is to the girder soffit)
Z_DECK_TOWER = Z_DECK_MID - 4.5
Z_DECK_ANCH = Z_DECK_MID - 9.0
Z_TOWER_TOP = TOWER_H_MHW + MHW              # 115.6
Z_SADDLE = Z_TOWER_TOP - 4.5
Z_CABLE_LOW = Z_DECK_MID + 3.0
GROUND = 4.0
ANCH_L, ANCH_W = 60.0, 62.0
APPROACH_MODELLED = 260.0

SUPPORTS = [
    ba.Support("tower_bx", 1016686393, (9993.18, 11654.36), "pylon", "Bronx tower"),
    ba.Support("tower_qn", 1016686394, (10301.74, 11024.75), "pylon", "Queens tower"),
    ba.Support("anchorage_bx", 1016686391, (9894.49, 11861.79), "anchorage", "Bronx anchorage"),
    ba.Support("anchorage_qn", 1016686396, (10405.28, 10818.44), "anchorage", "Queens anchorage"),
]

S_T_BX, S_T_QN = -MAIN_SPAN / 2, MAIN_SPAN / 2      # +s runs Bronx -> Queens
S_AF_BX, S_AF_QN = S_T_BX - SIDE_SPAN, S_T_QN + SIDE_SPAN
S_A_BX, S_A_QN = S_AF_BX - ANCH_L / 2, S_AF_QN + ANCH_L / 2
S_END_BX, S_END_QN = S_A_BX - APPROACH_MODELLED, S_A_QN + APPROACH_MODELLED


def deck_z(s: float) -> float:
    if s < S_T_BX:
        u = min(1.0, max(0.0, (s - S_AF_BX) / SIDE_SPAN))
        return Z_DECK_ANCH + (Z_DECK_TOWER - Z_DECK_ANCH) * u
    if s <= S_T_QN:
        u = s / (MAIN_SPAN / 2)
        return Z_DECK_MID - (Z_DECK_MID - Z_DECK_TOWER) * u * u
    u = min(1.0, (s - S_T_QN) / SIDE_SPAN)
    return Z_DECK_TOWER + (Z_DECK_ANCH - Z_DECK_TOWER) * u


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_bx", "tower_qn"), MAIN_SPAN, roads_name="WHITESTONE BRG")
    axis = fit.axis
    objs: list = []
    tower = bl.TowerSpec(kind="artdeco", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=DECK_W + 3.0, depth_s=8.0,
                         z_base=-14.0, z_deck=Z_DECK_TOWER, leg_w=6.2, leg_d=8.0, leg_taper=0.6,
                         struts_z=(Z_DECK_TOWER - 3.0, Z_DECK_TOWER + 14.0, 82.0, Z_TOWER_TOP - 5.0), x_brace=False,
                         pier_w=DECK_W + 8.0, pier_d=14.0, material="steel_gray", pier_material="concrete",
                         cable_t=CABLE_T)
    objs += bl.build_tower("tower_bx", axis, S_T_BX, tower, lod)
    objs += bl.build_tower("tower_qn", axis, S_T_QN, tower, lod)

    anch_bx = bl.AnchorageSpec(S_A_BX, ANCH_L, ANCH_W, GROUND + 30.0, GROUND - 12.0, "concrete", Z_DECK_ANCH - 3.0, slope=False)
    anch_qn = bl.AnchorageSpec(S_A_QN, ANCH_L, ANCH_W, GROUND + 30.0, GROUND - 12.0, "concrete", Z_DECK_ANCH - 3.0, slope=False)
    objs += bl.build_anchorage("anch_bx", axis, anch_bx, S_T_BX)
    objs += bl.build_anchorage("anch_qn", axis, anch_qn, S_T_QN)

    deck = bl.DeckSpec(width=DECK_W, thickness=3.35, lanes=6, lane_w=3.35, roadway_t=0.0, roadway_w=20.1,
                       truss_depth=0.0, material="asphalt", slab_material="steel_gray", railing=True,
                       lamps_spacing=48.0, lamp_t=(-0.6, 0.6), centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_AF_BX, S_AF_QN, deck_z, lod, step=9.0)
    # 2003-2005 triangular fibreglass fairings along both sides of the deck
    ss = bl.samples(S_AF_BX, S_AF_QN, 12.0)
    for side in (-1, 1):
        w = side * DECK_W / 2
        sec = [(w, 0.1), (w + side * FAIRING_H * 1.6, -FAIRING_H * 0.6), (w, -FAIRING_H * 1.2)]
        objs.append(bl.sweep(f"fairing{side}", axis, ss, sec if side > 0 else list(reversed(sec)), deck_z, "paint_white"))

    cables = bl.CableSpec(t_offsets=CABLE_T, radius=0.28, z_low_mid=Z_CABLE_LOW, suspender_spacing=15.24,
                          suspender_radius=0.045, suspender_pairs=True, material="steel_silver",
                          suspender_material="steel_gray")
    objs += bl.build_suspension_cables("cable", axis, cables, (S_T_BX, S_T_QN), Z_SADDLE, (anch_bx, anch_qn), deck_z,
                                       0.4, lod)

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=1.4, lanes=6, lane_w=3.35, roadway_w=20.1, material="asphalt",
                          slab_material="concrete_dark", railing=True, centre_yellow=False)
    objs += bl.build_approach("ap_bx", axis, bl.ApproachSpec(S_END_BX, S_AF_BX, 18.0, Z_DECK_ANCH, "viaduct",
                                                            pier_spacing=38.0, width=DECK_W, material="concrete",
                                                            ground_z=GROUND), lod, ap_deck)
    objs += bl.build_approach("ap_qn", axis, bl.ApproachSpec(S_AF_QN, S_END_QN, Z_DECK_ANCH, 18.0, "viaduct",
                                                            pier_spacing=38.0, width=DECK_W, material="concrete",
                                                            ground_z=GROUND), lod, ap_deck)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": TOWER_H_MHW, "name": TITLE,
        "main_span_m": MAIN_SPAN, "side_span_m": SIDE_SPAN, "deck_width_m": DECK_W,
        "tower_height_mhw_m": TOWER_H_MHW, "clearance_mhw_m": CLEARANCE_MHW, "n_cables": 2, "lanes": 6,
        "structural_state": "post-2005 (plate girder deck with triangular fibreglass fairings)",
        "total_modelled_length_m": S_END_QN - S_END_BX, "alignment_source": fit.source,
        "height_source": "Wikipedia/MTA B&T: 377 ft towers above MHW, 2,300 ft main span, 134 ft 10 in clearance",
        "sources_ids": ["osm_bbbike", "published_bronx_whitestone"],
        "fidelity_statement": (
            "Exact to published values: 701.04 m main span, 224.03 m side spans, 22.56 m between cables, 114.9 m Art "
            "Deco towers above MHW, 41.10 m clearance, 6 lanes, two main cables, and the current post-2005 deck with "
            "the triangular fibreglass fairings (not the 1939 plate girder or the 1947-2005 trusses). Inferred: "
            "anchorage block sizes, deck elevations away from the published clearance, 15.24 m suspender pitch, "
            "fairing profile. Gap: approach viaducts modelled for 260 m each. Not modelled: cable bands and wrapping, "
            "toll gantry, Hutchinson River Parkway and Whitestone Expressway interchanges, tuned mass dampers."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("tower_bx", "tower_qn"), MAIN_SPAN, roads_name="WHITESTONE BRG")
    ax = fit.axis
    land_bx, land_qn = ax.p(-800.0, 0.0), ax.p(800.0, 0.0)
    ctx = (("water_dark", 0.35, 1900.0, (0.0, 0.0)),
           ("ground_urban", GROUND, 340.0, (land_bx.x, land_bx.y)),
           ("ground_urban", GROUND, 340.0, (land_qn.x, land_qn.y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_bronx_whitestone_bridge", fit.frame, view="whitestone_reference",
                                ground_z=GROUND, target_z=75.0, fov_deg=48.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="ferry_point_park", cam=ax.p(S_T_BX - 40.0, -300.0, GROUND + 2.0), target=ax.p(120.0, 0.0, 75.0),
                 fov_deg=58.0, context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=30.0),
            dict(view="elevation_from_river", cam=ax.p(0.0, -1150.0, 35.0), target=ax.p(0.0, 0.0, 70.0), fov_deg=40.0,
                 context=ctx, sun_azimuth_deg=190.0, sun_elevation_deg=32.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
