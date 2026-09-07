"""Throgs Neck Bridge — East River at the entrance to Long Island Sound, Throggs Neck (Bronx) to Bay Terrace
(Queens).  Othmar Ammann, opened 11 January 1961.  MTA Bridges & Tunnels.

Dimensions used (source in brackets)
------------------------------------
* Main span 1,800 ft = **548.64 m**; length between anchorages 2,910 ft = **886.97 m**, giving side spans of
  **169.17 m** each; total length with approaches 11,250 ft = 3,429 m (Bronx approach 3,900 ft = 1,189 m, Queens
  approach 2,800 ft = 853 m — modelled at 320 m each, see below); towers **105.5 m** above mean high water (346 ft;
  326 ft = 99.4 m above the artificial islands, which stand 20 ft = 6.1 m out of the water); clearance below
  142 ft = **43.28 m**; roadway 37 ft = 11.28 m per direction with a 4 ft = 1.22 m median, **6 lanes**; stiffening
  trusses 28 ft = **8.53 m** deep; anchorages 250 x 350 ft = **76.2 x 106.7 m**; each main cable has 37 strands of
  296 wires = 10,952 wires [Wikipedia "Throgs Neck Bridge", MTA Bridges & Tunnels].
* Two main cables (one in each truss plane), the standard arrangement for Ammann's post-war Sound crossings; cable
  planes at t = +-11.9 m (**inferred** from the 23.8 m truss spacing, +-0.4 m).
* The towers stand on artificial islands 6.1 m above the water; the model builds those islands.

Placement: towers are OSM ways ``1016661640`` (Bronx) and ``1016661642`` (Queens), tagged ``bridge:support``; their
measured separation is **549.33 m**, 0.13 % from the published 1,800 ft.  Anchorages are OSM ways ``1016661637``
(Bronx, 184.1 m from its tower) and ``1016661644`` (Queens, 177.6 m) — both within 15 m of the published 169.17 m
side span, the balance being the offset of the block centroid behind the cable-entry face.

The approach viaducts are modelled for 320 m beyond each anchorage rather than their full published lengths (1,189 m
and 853 m): beyond that they are ordinary highway viaduct that the roads/terrain stages will carry, and including
them would put 2 km of empty deck into a landmark asset.  **Stated gap.**

Not modelled: the cable bands and wrapping, the toll gantry, the Cross Island Parkway and Clearview Expressway
interchanges, the fender systems around the islands, and the 2010s deck replacement's orthotropic panels.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_throgs_neck"
TITLE = "Throgs Neck Bridge"

MAIN_SPAN = 548.64
SIDE_SPAN = 169.17
DECK_W = 25.9                      # 2 x 11.28 m roadway + 1.22 m median + parapets
TOWER_H_MHW = 105.5
CLEARANCE_MHW = 43.28
TRUSS_DEPTH = 8.53
CABLE_T = (-11.9, 11.9)
ANCH_L, ANCH_W = 76.2, 106.7
ISLAND_Z = 6.1
APPROACH_MODELLED = 320.0
MHW = bc.MHW_ABOVE_NAVD88_M

Z_DECK_MID = CLEARANCE_MHW + MHW + TRUSS_DEPTH + 0.9   # 53.41 NAVD88 roadway top
Z_DECK_TOWER = Z_DECK_MID - 3.0
Z_DECK_ANCH = Z_DECK_MID - 7.0
Z_TOWER_TOP = TOWER_H_MHW + MHW                        # 106.2
Z_SADDLE = Z_TOWER_TOP - 4.0
Z_CABLE_LOW = Z_DECK_MID + 2.4
GROUND = 4.0
Z_APPROACH_END = 24.0

SUPPORTS = [
    ba.Support("tower_bx", 1016661640, (13193.92, 11422.37), "pylon", "Bronx tower"),
    ba.Support("tower_qn", 1016661642, (13198.94, 10873.06), "pylon", "Queens tower"),
    ba.Support("anchorage_bx", 1016661637, (13192.09, 11606.43), "anchorage", "Bronx anchorage"),
    ba.Support("anchorage_qn", 1016661644, (13199.48, 10695.46), "anchorage", "Queens anchorage"),
]

S_T_QN, S_T_BX = -MAIN_SPAN / 2, MAIN_SPAN / 2         # +s runs Queens -> Bronx
S_AF_QN, S_AF_BX = S_T_QN - SIDE_SPAN, S_T_BX + SIDE_SPAN
S_A_QN, S_A_BX = S_AF_QN - ANCH_L / 2, S_AF_BX + ANCH_L / 2
S_END_QN, S_END_BX = S_A_QN - APPROACH_MODELLED, S_A_BX + APPROACH_MODELLED


def deck_z(s: float) -> float:
    if s < S_T_QN:
        u = min(1.0, max(0.0, (s - S_AF_QN) / SIDE_SPAN))
        return Z_DECK_ANCH + (Z_DECK_TOWER - Z_DECK_ANCH) * u
    if s <= S_T_BX:
        u = s / (MAIN_SPAN / 2)
        return Z_DECK_MID - (Z_DECK_MID - Z_DECK_TOWER) * u * u
    u = min(1.0, (s - S_T_BX) / SIDE_SPAN)
    return Z_DECK_TOWER + (Z_DECK_ANCH - Z_DECK_TOWER) * u


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_qn", "tower_bx"), MAIN_SPAN, roads_name="THROGS NECK BRG")
    axis = fit.axis
    objs: list = []
    tower = bl.TowerSpec(kind="portal", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=DECK_W + 2.0, depth_s=8.5,
                         z_base=ISLAND_Z, z_deck=Z_DECK_TOWER, leg_w=6.6, leg_d=8.5, leg_taper=0.62,
                         struts_z=(Z_DECK_TOWER - 2.0, Z_DECK_TOWER + TRUSS_DEPTH + 6.0, Z_TOWER_TOP - 4.0),
                         x_brace=False, pier_w=DECK_W + 6.0, pier_d=14.0, material="steel_gray",
                         pier_material="concrete", cable_t=CABLE_T)
    for nm, s in (("tower_qn", S_T_QN), ("tower_bx", S_T_BX)):
        # artificial island (20 ft above mean high water)
        isl = bc.prism(f"{nm}_island", bc.regular_polygon(20, 46.0), -9.0, ISLAND_Z + MHW, "concrete_dark")
        bc.transform(isl, axis.matrix(s))
        objs.append(isl)
        objs += bl.build_tower(nm, axis, s, tower, lod)

    anch_qn = bl.AnchorageSpec(S_A_QN, ANCH_L, ANCH_W, GROUND + 34.0, GROUND - 12.0, "concrete", Z_DECK_ANCH - 4.0, slope=False)
    anch_bx = bl.AnchorageSpec(S_A_BX, ANCH_L, ANCH_W, GROUND + 34.0, GROUND - 12.0, "concrete", Z_DECK_ANCH - 4.0, slope=False)
    objs += bl.build_anchorage("anch_qn", axis, anch_qn, S_T_QN)
    objs += bl.build_anchorage("anch_bx", axis, anch_bx, S_T_BX)

    deck = bl.DeckSpec(width=DECK_W, thickness=0.5, lanes=6, lane_w=3.76, roadway_t=0.0, roadway_w=23.8,
                       truss_depth=TRUSS_DEPTH, truss_t=(-11.9, 11.9), truss_above=False, truss_panel=9.1,
                       truss_material="steel_gray", material="asphalt", slab_material="concrete_dark",
                       railing=True, lamps_spacing=50.0, lamp_t=(-0.6, 0.6), centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_AF_QN, S_AF_BX, deck_z, lod, step=8.0)

    cables = bl.CableSpec(t_offsets=CABLE_T, radius=0.29, z_low_mid=Z_CABLE_LOW, suspender_spacing=13.72,
                          suspender_radius=0.045, suspender_pairs=True, material="steel_silver",
                          suspender_material="steel_gray")
    objs += bl.build_suspension_cables("cable", axis, cables, (S_T_QN, S_T_BX), Z_SADDLE, (anch_qn, anch_bx), deck_z,
                                       0.5, lod)

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.6, lanes=6, lane_w=3.76, roadway_w=23.8, material="asphalt",
                          slab_material="concrete_dark", railing=True, centre_yellow=False)
    objs += bl.build_approach("ap_qn", axis, bl.ApproachSpec(S_END_QN, S_AF_QN, Z_APPROACH_END, Z_DECK_ANCH, "viaduct",
                                                            pier_spacing=40.0, width=DECK_W, material="concrete",
                                                            ground_z=GROUND), lod, ap_deck)
    objs += bl.build_approach("ap_bx", axis, bl.ApproachSpec(S_AF_BX, S_END_BX, Z_DECK_ANCH, Z_APPROACH_END, "viaduct",
                                                            pier_spacing=40.0, width=DECK_W, material="concrete",
                                                            ground_z=GROUND), lod, ap_deck)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": TOWER_H_MHW, "name": TITLE,
        "main_span_m": MAIN_SPAN, "side_span_m": SIDE_SPAN, "deck_width_m": DECK_W,
        "tower_height_mhw_m": TOWER_H_MHW, "clearance_mhw_m": CLEARANCE_MHW, "truss_depth_m": TRUSS_DEPTH,
        "n_cables": 2, "lanes": 6, "anchorage_plan_m": [ANCH_L, ANCH_W],
        "total_modelled_length_m": S_END_BX - S_END_QN, "alignment_source": fit.source,
        "height_source": "Wikipedia/MTA B&T: 346 ft towers above MHW, 1,800 ft main span, 142 ft clearance",
        "sources_ids": ["osm_bbbike", "published_throgs_neck"],
        "fidelity_statement": (
            "Exact to published values: 548.64 m main span, 169.17 m side spans (from the published 2,910 ft between "
            "anchorages), 105.5 m towers above MHW on artificial islands 6.1 m out of the water, 43.28 m clearance, "
            "8.53 m stiffening trusses, 6 lanes, 76.2 x 106.7 m anchorages, two main cables. Inferred: cable plane "
            "offsets (+-0.4 m), deck elevations away from the published clearance, 13.72 m (45 ft) suspender pitch, "
            "island plan. Gap: the approach viaducts are modelled for 320 m each instead of the published 1,189 m "
            "(Bronx) and 853 m (Queens). Not modelled: cable bands and wrapping, toll gantry, Cross Island Parkway "
            "and Clearview Expressway interchanges, island fenders, orthotropic deck panels."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("tower_qn", "tower_bx"), MAIN_SPAN, roads_name="THROGS NECK BRG")
    ax = fit.axis
    land_qn, land_bx = ax.p(-680.0, 0.0), ax.p(680.0, 0.0)
    ctx = (("water_dark", 0.35, 1800.0, (0.0, 0.0)),
           ("ground_urban", GROUND, 340.0, (land_qn.x, land_qn.y)),
           ("ground_urban", GROUND, 340.0, (land_bx.x, land_bx.y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_throgs_neck_bridge", fit.frame, view="throgs_neck_reference",
                                ground_z=GROUND, target_z=70.0, fov_deg=48.0, size=(1280, 720), context=ctx,
                                aim=ax.p(0.0, 0.0, 70.0),
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="little_bay_park", cam=ax.p(S_T_QN - 60.0, -340.0, GROUND + 2.0), target=ax.p(60.0, 0.0, 70.0),
                 fov_deg=58.0, context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=30.0),
            dict(view="elevation_from_sound", cam=ax.p(0.0, -1000.0, 30.0), target=ax.p(0.0, 0.0, 65.0), fov_deg=40.0,
                 context=ctx, sun_azimuth_deg=190.0, sun_elevation_deg=32.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
