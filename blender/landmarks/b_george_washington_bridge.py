"""George Washington Bridge — Hudson River, Fort Lee NJ to Washington Heights, Manhattan.  Othmar Ammann (engineer)
with Cass Gilbert (architect); upper level opened 25 October 1931, lower level 29 August 1962.  NHL 1981.

Dimensions used (source in brackets)
------------------------------------
* Main span 3,500 ft = **1,066.8 m**; total length 4,760 ft = **1,450.8 m**; deck width 119 ft = **36.27 m**;
  towers **184.1 m** (604 ft); clearance below at mid-span 212 ft = **64.62 m**; lane width 11 ft = 3.35 m;
  **8 lanes** on the upper level and **6** on the lower [Wikipedia "George Washington Bridge", PANYNJ].
* Side spans: the published total less the main span leaves 1,260 ft; the standard split is **610 ft = 185.93 m** on
  the New Jersey side (the anchorage is driven into the Palisades rock) and **650 ft = 198.12 m** on the New York side
  (a free-standing concrete anchorage in Fort Washington Park).
* Cables: **four**, 3 ft = **0.914 m** diameter, 61 strands x 434 wires = 26,474 wires each; two cables pass over each
  tower leg (**inferred** plane offsets +-14.0 / +-17.0 m, +-0.5 m).  Design sag 327 ft = **99.7 m**, which places the
  cable low point 2 m above the upper deck at mid-span — the bridge's characteristic profile.
* Towers: bare **steel lattice**; Cass Gilbert's granite cladding was cancelled in the Depression and never applied.
  Each tower is two lattice legs braced by lattice portal struts, the lower one framing the roadway.
* Deck: the 1962 lower level hangs from the same suspenders inside a stiffening truss between the two roadway levels.

Placement: towers are OSM ways ``741784700`` (New York) and ``741784699`` (New Jersey), ``bridge:support=pylon``;
their measured separation is 1,066.25 m, **0.05 %** from the published 3,500 ft.  The New York anchorage is OSM way
``899357171``; its centroid lies 217.5 m from the New York tower, i.e. 19 m beyond the published 650 ft side span,
because the OSM polygon takes in the approach structure in front of the anchorage — the model puts the cable-entry
face at exactly 198.12 m and the block behind it.  The New Jersey anchorage is inside the Palisades and has no
polygon; it is placed at the published 185.93 m.  ``segments.parquet`` was not available.

Not modelled: the Cass Gilbert cladding that was never built (correctly absent), the cable bands and wrapping, the
Little Red Lighthouse under the New York tower, the toll plaza and its canopies, the Trans-Manhattan Expressway
approach and its bus station, the Palisades Interstate Parkway interchange, and the tower rivet and gusset detail.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_george_washington_bridge"
TITLE = "George Washington Bridge"

MAIN_SPAN = 1066.8
SIDE_SPAN_NY = 198.12
SIDE_SPAN_NJ = 185.93
DECK_W = 36.27
TOWER_H = 184.1
CLEARANCE_MHW = 64.62
CABLE_D = 0.914
CABLE_SAG = 99.7
CABLE_T = (-17.0, -14.0, 14.0, 17.0)
MHW = bc.MHW_ABOVE_NAVD88_M

Z_LOWER_MID = CLEARANCE_MHW + MHW + 1.4      # 66.72 NAVD88 lower roadway
DECK_GAP = 10.3
Z_UPPER_MID = Z_LOWER_MID + DECK_GAP         # 77.02
Z_TOWER_TOP = TOWER_H + MHW                  # 184.8
Z_SADDLE = Z_UPPER_MID + 2.1 + CABLE_SAG     # 178.82 -> 6.0 m below the tower top
Z_CABLE_LOW = Z_SADDLE - CABLE_SAG           # 79.12
Z_UPPER_TOWER = Z_UPPER_MID - 5.5
Z_UPPER_ANCH = Z_UPPER_MID - 10.5
GROUND_NY = 12.0
GROUND_NJ = 40.0                             # Palisades bench under the NJ tower approach (inferred)
ANCH_L, ANCH_W, ANCH_H = 76.0, 55.0, 43.0

SUPPORTS = [
    ba.Support("tower_nj", 741784699, (-740.38, 16979.95), "pylon", "New Jersey tower"),
    ba.Support("tower_ny", 741784700, (292.04, 16713.51), "pylon", "New York tower"),
    ba.Support("anchorage_ny", 899357171, (501.61, 16655.21), "anchorage", "New York anchorage (Fort Washington Park)"),
]

S_T_NJ, S_T_NY = -MAIN_SPAN / 2, MAIN_SPAN / 2      # +s runs New Jersey -> New York
S_AF_NJ, S_AF_NY = S_T_NJ - SIDE_SPAN_NJ, S_T_NY + SIDE_SPAN_NY
S_A_NJ, S_A_NY = S_AF_NJ - ANCH_L / 2, S_AF_NY + ANCH_L / 2
S_END_NJ, S_END_NY = S_A_NJ - 140.0, S_A_NY + 140.0


def upper_z(s: float) -> float:
    if s < S_T_NJ:
        u = min(1.0, max(0.0, (s - S_AF_NJ) / SIDE_SPAN_NJ))
        return Z_UPPER_ANCH + (Z_UPPER_TOWER - Z_UPPER_ANCH) * u
    if s <= S_T_NY:
        u = s / (MAIN_SPAN / 2)
        return Z_UPPER_MID - (Z_UPPER_MID - Z_UPPER_TOWER) * u * u
    u = min(1.0, (s - S_T_NY) / SIDE_SPAN_NY)
    return Z_UPPER_TOWER + (Z_UPPER_ANCH - Z_UPPER_TOWER) * u


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_nj", "tower_ny"), MAIN_SPAN, roads_name="George Washington Bridge")
    axis = fit.axis
    objs: list = []
    tower = bl.TowerSpec(kind="lattice", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=DECK_W + 6.0, depth_s=15.0,
                         z_base=-16.0, z_deck=Z_UPPER_TOWER, leg_w=12.0, leg_d=15.0, leg_taper=0.52,
                         struts_z=(Z_LOWER_MID - 14.0, Z_UPPER_TOWER + 8.0, 120.0, Z_TOWER_TOP - 8.0), x_brace=True,
                         pier_w=DECK_W + 12.0, pier_d=22.0, material="steel_gray", pier_material="concrete",
                         cable_t=CABLE_T)
    objs += bl.build_tower("tower_nj", axis, S_T_NJ, tower, lod)
    objs += bl.build_tower("tower_ny", axis, S_T_NY, tower, lod)

    anch_nj = bl.AnchorageSpec(S_A_NJ, ANCH_L, ANCH_W, GROUND_NJ + ANCH_H, GROUND_NJ - 30.0, "granite_dark",
                               Z_UPPER_ANCH - 6.0, slope=False)
    anch_ny = bl.AnchorageSpec(S_A_NY, ANCH_L, ANCH_W, GROUND_NY + ANCH_H, GROUND_NY - 12.0, "concrete",
                               Z_UPPER_ANCH - 6.0, slope=False)
    objs += bl.build_anchorage("anch_nj", axis, anch_nj, S_T_NJ)
    objs += bl.build_anchorage("anch_ny", axis, anch_ny, S_T_NY)

    deck = bl.DeckSpec(width=DECK_W, thickness=1.0, lanes=8, lane_w=3.35, roadway_t=0.0, roadway_w=27.0,
                       walkways=((-17.4, 1.6, 0.2), (17.4, 1.6, 0.2)), truss_depth=DECK_GAP,
                       truss_t=(-DECK_W / 2 + 0.7, DECK_W / 2 - 0.7), truss_above=False, truss_panel=9.5,
                       truss_material="steel_gray", material="asphalt", slab_material="steel_gray",
                       lower_deck_dz=-DECK_GAP, lower_lanes=6, lower_width=DECK_W - 4.0, railing=True,
                       lamps_spacing=52.0, lamp_t=(-DECK_W / 2 + 1.2, DECK_W / 2 - 1.2), centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_AF_NJ, S_AF_NY, upper_z, lod, step=8.0)

    cables = bl.CableSpec(t_offsets=CABLE_T, radius=CABLE_D / 2, z_low_mid=Z_CABLE_LOW, suspender_spacing=18.29,
                          suspender_radius=0.06, suspender_pairs=True, material="steel_silver",
                          suspender_material="steel_gray")
    objs += bl.build_suspension_cables("cable", axis, cables, (S_T_NJ, S_T_NY), Z_SADDLE, (anch_nj, anch_ny), upper_z,
                                       0.6, lod)

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.8, lanes=8, lane_w=3.35, roadway_w=27.0, material="asphalt",
                          slab_material="steel_gray", railing=True, centre_yellow=False)
    objs += bl.build_approach("ap_nj", axis, bl.ApproachSpec(S_END_NJ, S_AF_NJ, Z_UPPER_ANCH - 3.0, Z_UPPER_ANCH,
                                                            "girder", pier_spacing=36.0, width=DECK_W,
                                                            material="concrete", ground_z=GROUND_NJ), lod, ap_deck)
    objs += bl.build_approach("ap_ny", axis, bl.ApproachSpec(S_AF_NY, S_END_NY, Z_UPPER_ANCH, Z_UPPER_ANCH - 4.0,
                                                            "girder", pier_spacing=36.0, width=DECK_W,
                                                            material="concrete", ground_z=GROUND_NY), lod, ap_deck)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": TOWER_H, "name": TITLE,
        "main_span_m": MAIN_SPAN, "side_span_ny_m": SIDE_SPAN_NY, "side_span_nj_m": SIDE_SPAN_NJ,
        "deck_width_m": DECK_W, "tower_height_m": TOWER_H, "clearance_mhw_m": CLEARANCE_MHW,
        "cable_diameter_m": CABLE_D, "cable_sag_m": CABLE_SAG, "n_cables": 4,
        "upper_lanes": 8, "lower_lanes": 6, "total_modelled_length_m": S_END_NY - S_END_NJ,
        "alignment_source": fit.source,
        "height_source": "Wikipedia/PANYNJ: 604 ft towers, 3,500 ft main span, 212 ft clearance, 3 ft cables",
        "sources_ids": ["osm_bbbike", "published_gwb"],
        "fidelity_statement": (
            "Exact to published values: 1,066.8 m main span, 36.27 m deck, 184.1 m bare steel lattice towers, "
            "64.62 m clearance, four 0.914 m cables with the published 99.7 m sag, 8 upper / 6 lower lanes at the "
            "published 3.35 m lane width, two decks in a stiffening truss. Inferred: the 610 ft / 650 ft side-span "
            "assignment to the New Jersey / New York sides, cable plane offsets (+-0.5 m), anchorage block sizes and "
            "the Palisades bench elevation, deck elevations away from the published mid-span clearance, 18.29 m "
            "(60 ft) suspender pitch. Not modelled: the never-built Cass Gilbert stone cladding, cable bands and "
            "wrapping, the Little Red Lighthouse, the toll plaza, the Trans-Manhattan Expressway approach and bus "
            "station, the Palisades Interstate Parkway interchange, rivet and gusset detail."),
    }
    return objs, extras


def main() -> None:
    """Four verification renders, each framed to answer one question.

    1. ``fort_washington_park`` — the canonical viewpoint: the Manhattan shore in Fort Washington Park about 300 m
       south of the New York tower (40.8480 N, 73.9480 W), where the Little Red Lighthouse stands almost directly
       under the tower.  Question: does the 184.1 m bare-lattice tower read at the right height and proportion from
       the ground, and does the main span leave it at the right angle?
    2. ``tower_lattice`` — close to the New York tower with the sun 35 deg up and off-axis.  Question: is this the
       *unclad* steel lattice (Cass Gilbert's granite was never applied), with two tapering legs and four lattice
       portal struts, and do the four cables pass over the legs in pairs?
    3. ``elevation_both_towers`` — a long lens from the Hudson with both towers in frame.  Question: is the
       1,066.8 m span and the 99.7 m cable sag right — the cable should come down to within about 2 m of the upper
       deck at mid-span, which is the GWB's signature profile?
    4. ``upper_deck`` — eye level on the upper roadway looking towards the New Jersey tower.  Question: are the
       8 upper lanes, the suspender pitch and the tower portal at deck level right?
    """
    fit = ba.bridge_axis(SUPPORTS, ("tower_nj", "tower_ny"), MAIN_SPAN)
    ax = fit.axis
    fr = fit.frame
    land_nj, land_ny = ax.p(-820.0, 0.0), ax.p(760.0, 0.0)
    ctx = (("water_dark", 0.35, 2000.0, (0.0, 0.0)),
           ("ground_urban", GROUND_NJ, 400.0, (land_nj.x, land_nj.y)),
           ("ground_urban", GROUND_NY, 380.0, (land_ny.x, land_ny.y)))
    fort_washington = fr.from_lonlat(-73.9480, 40.8480, GROUND_NY + 1.65)
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded Fort Washington Park viewpoint, used verbatim
            ba.reference_render("landmark_george_washington_bridge", fr, view="fort_washington_park_reference",
                                ground_z=GROUND_NY, target_z=110.0, fov_deg=72.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=235.0, sun_elevation_deg=35.0),
            dict(view="fort_washington_park", cam=fort_washington, target=ax.p(S_T_NY - 40.0, 0.0, 90.0),
                 fov_deg=72.0, size=(1280, 720), context=ctx, sun_azimuth_deg=235.0, sun_elevation_deg=35.0),
            dict(view="tower_lattice", cam=ax.p(S_T_NY - 150.0, -180.0, 40.0), target=ax.p(S_T_NY, 0.0, 110.0),
                 fov_deg=52.0, size=(1280, 720), context=ctx, sun_azimuth_deg=205.0, sun_elevation_deg=35.0),
            dict(view="elevation_both_towers", cam=ax.p(0.0, -1750.0, 110.0), target=ax.p(0.0, 0.0, 105.0),
                 fov_deg=40.0, size=(1280, 720), context=ctx, sun_azimuth_deg=185.0, sun_elevation_deg=35.0),
            dict(view="upper_deck", cam=ax.p(S_T_NJ + 80.0, -11.0, Z_UPPER_MID + 1.8),
                 target=ax.p(S_T_NJ - 40.0, 0.0, Z_UPPER_MID + 40.0), fov_deg=62.0, size=(1280, 720), context=ctx,
                 sun_azimuth_deg=120.0, sun_elevation_deg=35.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Verification renders": main.__doc__.strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
