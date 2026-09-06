"""Manhattan Bridge — East River, Canal Street / Bowery to Flatbush Avenue Extension.  Leon Moisseiff / Carrere &
Hastings, opened 31 December 1909.  NYC Landmark (the Manhattan-side arch and colonnade, LP-1240).

Dimensions used (source in brackets)
------------------------------------
* Main span 1,480 ft = **451.1 m**; side spans 725 ft = **221.0 m** each; total length 6,855 ft = **2,089 m**; deck
  width 120 ft = **36.58 m**; clearance 135 ft = **41.15 m** above mean high water; towers 350 ft = **106.68 m** to
  the ornamental finials; anchorages 237 x 182 ft x 135 ft = **72.24 x 55.47 x 41.15 m**
  [Wikipedia "Manhattan Bridge", NYCDOT East River bridges].
* Decks [Wikipedia]: **upper level** two separate roadways of 2 lanes each at the outer edges (east roadway 24 ft,
  west roadway 22.5 ft); **lower level** 3 vehicle lanes in the centre, **4 subway tracks** (a pair under each upper
  roadway — B/D on the north side, N/Q on the south), a 10-12 ft walkway on the south side and a 10-12 ft bicycle path
  on the north side.  Standard gauge 1.435 m.
* Cables: four main cables, two passing over each tower leg (**inferred** pairing from photographs, +-0.4 m on the
  plane offsets); 21 in = 0.533 m diameter.
* Manhattan approach: the 1912 Carrere & Hastings triumphal arch at Canal Street and the flanking semicircular Tuscan
  colonnade (LP-1240).
* Colour: the "Manhattan Bridge blue" of the current paint scheme.

Placement: towers are OSM ways ``317352033`` (Brooklyn) and ``1255353996`` (Manhattan), both ``bridge:support=pylon``;
their measured separation is 445.63 m, 1.21 % short of the published 1,480 ft, so the towers are snapped symmetrically
to 451.1 m about the measured midpoint (that 5.5 m is spread as 2.7 m per tower).  Anchorages are OSM ways
``1255353998`` (Brooklyn) and ``1017507380`` (Manhattan).  ``segments.parquet`` was not available.

Approach lengths: the published total (2,089 m) less the main span, side spans and anchorages leaves 1,051.5 m of
approach viaduct, split here 600 m Manhattan / 451.5 m Brooklyn — that split is **inferred**, the published sources
give only the total.

Not modelled: the cable bands and wrapping, the subway third rail and signals, the 2001-2004 reconstruction's steel
plate reinforcement, the tower finial castings in detail, the arch's sculptural groups ("Spirit of Commerce" and
"Spirit of Industry") and frieze, and the Brooklyn-side pedestrian ramps.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_manhattan_bridge"
TITLE = "Manhattan Bridge"

MAIN_SPAN = 451.1
SIDE_SPAN = 221.0
DECK_W = 36.58
TOWER_H_MHW = 106.68
CLEARANCE_MHW = 41.15
ANCH_L, ANCH_W, ANCH_H = 72.24, 55.47, 41.15
APPROACH_MN = 600.0
APPROACH_BK = 451.5
CABLE_D = 0.533
CABLE_T = (-17.4, -14.6, 14.6, 17.4)
MHW = bc.MHW_ABOVE_NAVD88_M

Z_LOWER_MID = CLEARANCE_MHW + MHW + 1.2      # 43.05 NAVD88 lower roadway at mid-span
DECK_GAP = 9.0                               # upper deck above lower deck (stiffening truss depth)
Z_UPPER_MID = Z_LOWER_MID + DECK_GAP         # 52.05
Z_UPPER_TOWER = Z_UPPER_MID - 1.6
Z_UPPER_ANCH = Z_UPPER_MID - 8.0
Z_TOWER_TOP = TOWER_H_MHW + MHW              # 107.38
Z_SADDLE = Z_TOWER_TOP - 6.0                 # 101.38
Z_CABLE_LOW = Z_UPPER_MID + 2.5              # 54.55 -> sag 46.8 m (1/9.6 of the span)
GROUND = 4.0
Z_APPROACH_END = 14.0

SUPPORTS = [
    ba.Support("tower_bk", 317352033, (-3332.67, 568.80), "pylon", "Brooklyn tower"),
    ba.Support("tower_mn", 1255353996, (-3505.93, 979.37), "pylon", "Manhattan tower"),
    ba.Support("anchorage_bk", 1255353998, (-3234.44, 338.70), "anchorage", "Brooklyn anchorage"),
    ba.Support("anchorage_mn", 1017507380, (-3603.58, 1209.76), "anchorage", "Manhattan anchorage"),
]

S_T_BK, S_T_MN = -MAIN_SPAN / 2, MAIN_SPAN / 2
S_AF_BK, S_AF_MN = S_T_BK - SIDE_SPAN, S_T_MN + SIDE_SPAN
S_A_BK, S_A_MN = S_AF_BK - ANCH_L / 2, S_AF_MN + ANCH_L / 2
S_END_BK, S_END_MN = S_AF_BK - APPROACH_BK, S_AF_MN + APPROACH_MN


def upper_z(s: float) -> float:
    if s <= S_AF_BK:
        u = max(0.0, (s - S_END_BK) / (S_AF_BK - S_END_BK))
        return Z_APPROACH_END + (Z_UPPER_ANCH - Z_APPROACH_END) * u
    if s < S_T_BK:
        u = (s - S_AF_BK) / SIDE_SPAN
        return Z_UPPER_ANCH + (Z_UPPER_TOWER - Z_UPPER_ANCH) * u
    if s <= S_T_MN:
        u = s / (MAIN_SPAN / 2)
        return Z_UPPER_MID - (Z_UPPER_MID - Z_UPPER_TOWER) * u * u
    if s < S_AF_MN:
        u = (s - S_T_MN) / SIDE_SPAN
        return Z_UPPER_TOWER + (Z_UPPER_ANCH - Z_UPPER_TOWER) * u
    u = min(1.0, (s - S_AF_MN) / (S_END_MN - S_AF_MN))
    return Z_UPPER_ANCH + (Z_APPROACH_END - Z_UPPER_ANCH) * u


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_bk", "tower_mn"), MAIN_SPAN, roads_name="Manhattan Bridge")
    axis = fit.axis
    objs: list = []
    tower = bl.TowerSpec(kind="portal", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=DECK_W + 4.0, depth_s=9.0,
                         z_base=-10.0, z_deck=Z_UPPER_TOWER, leg_w=7.2, leg_d=9.0, leg_taper=0.62,
                         struts_z=(Z_UPPER_TOWER - DECK_GAP - 3.0, Z_UPPER_TOWER + 4.0, 74.0, Z_TOWER_TOP - 3.0),
                         x_brace=True, pier_w=DECK_W + 8.0, pier_d=15.0, material="steel_blue",
                         pier_material="granite_dark", cable_t=CABLE_T)
    objs += bl.build_tower("tower_bk", axis, S_T_BK, tower, lod)
    objs += bl.build_tower("tower_mn", axis, S_T_MN, tower, lod)

    anch_bk = bl.AnchorageSpec(S_A_BK, ANCH_L, ANCH_W, ANCH_H + GROUND - 8.0, GROUND - 8.0, "granite_gray", Z_UPPER_ANCH - 4.0, slope=False)
    anch_mn = bl.AnchorageSpec(S_A_MN, ANCH_L, ANCH_W, ANCH_H + GROUND - 8.0, GROUND - 8.0, "granite_gray", Z_UPPER_ANCH - 4.0, slope=False)
    objs += bl.build_anchorage("anch_bk", axis, anch_bk, S_T_BK)
    objs += bl.build_anchorage("anch_mn", axis, anch_mn, S_T_MN)

    deck = bl.DeckSpec(width=DECK_W, thickness=0.9, lanes=2, lane_w=3.35, roadway_t=-11.6, roadway_w=7.3,
                       walkways=(), truss_depth=DECK_GAP, truss_t=(-DECK_W / 2 + 0.6, DECK_W / 2 - 0.6),
                       truss_above=False, truss_panel=9.1, truss_material="steel_blue",
                       material="asphalt", slab_material="steel_blue",
                       lower_deck_dz=-DECK_GAP, lower_lanes=3, lower_width=DECK_W - 2.0,
                       tracks_lower=(-13.4, -9.6, 9.6, 13.4), railing=True, lamps_spacing=45.0,
                       lamp_t=(-DECK_W / 2 + 1.0, DECK_W / 2 - 1.0), centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_AF_BK, S_AF_MN, upper_z, lod, step=6.0)
    objs.append(bl.sweep("deck_road_e", axis, bl.samples(S_AF_BK, S_AF_MN, 6.0), bl.rect_section(6.9, 0.08, 11.6, 0.08),
                         upper_z, "asphalt"))
    # lower-level walkway (south) and bicycle path (north)
    for t, nm in ((-16.4, "walk_s"), (16.4, "bike_n")):
        objs.append(bl.sweep(f"deck_{nm}", axis, bl.samples(S_AF_BK, S_AF_MN, 8.0),
                             bl.rect_section(3.4, 0.3, t, -DECK_GAP + 0.3), upper_z, "sidewalk"))

    cables = bl.CableSpec(t_offsets=CABLE_T, radius=CABLE_D / 2, z_low_mid=Z_CABLE_LOW, suspender_spacing=9.14,
                          suspender_radius=0.05, material="steel_silver", suspender_material="steel_gray", side_spans=True)
    objs += bl.build_suspension_cables("cable", axis, cables, (S_T_BK, S_T_MN), Z_SADDLE, (anch_bk, anch_mn), upper_z, 0.5, lod)

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.8, lanes=4, lane_w=3.35, roadway_w=14.0, material="asphalt",
                          slab_material="steel_blue", railing=True, centre_yellow=True)
    objs += bl.build_approach("ap_bk", axis, bl.ApproachSpec(S_END_BK, S_AF_BK, Z_APPROACH_END, Z_UPPER_ANCH, "girder",
                                                            pier_spacing=32.0, width=DECK_W, material="steel_blue",
                                                            ground_z=GROUND), lod, ap_deck)
    objs += bl.build_approach("ap_mn", axis, bl.ApproachSpec(S_AF_MN, S_END_MN, Z_UPPER_ANCH, Z_APPROACH_END, "girder",
                                                            pier_spacing=32.0, width=DECK_W, material="steel_blue",
                                                            ground_z=GROUND), lod, ap_deck)
    # Carrere & Hastings triumphal arch and colonnade at Canal Street / Bowery (LP-1240)
    objs += bl.portal_arch_building("canal_arch", axis, S_END_MN - 6.0, 30.0, 12.0, 21.0, 12.2, 16.0, "limestone",
                                    colonnade=(46.0, 13.5, 9 if lod == 0 else 5))

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": TOWER_H_MHW,
        "name": TITLE, "lp_number": "LP-1240 (arch and colonnade)",
        "main_span_m": MAIN_SPAN, "side_span_m": SIDE_SPAN, "deck_width_m": DECK_W,
        "tower_height_mhw_m": TOWER_H_MHW, "clearance_mhw_m": CLEARANCE_MHW,
        "total_modelled_length_m": S_END_MN - S_END_BK, "n_cables": 4, "cable_diameter_m": CABLE_D,
        "subway_tracks": 4, "upper_lanes": 4, "lower_lanes": 3,
        "alignment_source": fit.source,
        "height_source": "Wikipedia/NYCDOT: 350 ft towers, 1,480 ft main span, 135 ft clearance",
        "sources_ids": ["osm_bbbike", "published_manhattan_bridge"],
        "fidelity_statement": (
            "Exact to published values: 451.1 m main span, 221.0 m side spans, 36.58 m deck, 106.68 m towers above "
            "MHW, 41.15 m clearance, 72.24 x 55.47 x 41.15 m anchorages, four cables, two-level deck with 4 upper "
            "lanes / 3 lower lanes / 4 standard-gauge subway tracks / south walkway / north bike path, Canal Street "
            "arch and colonnade. Inferred: cable plane pairing and offsets (+-0.4 m), the 600 m / 451.5 m split of "
            "the published 1,051.5 m of approach viaduct, deck elevations between the published mid-span clearance "
            "and the approach ends. Not modelled: cable bands and wrapping, third rail and signals, the 2001-2004 "
            "plate reinforcement, tower finial castings, the arch's sculptural groups and frieze."),
    }
    return objs, extras


def main() -> None:
    """Three verification renders, each framed to answer one question.

    1. ``dumbo_washington_street`` — **the real photographic viewpoint**, taken from
       ``docs/verification/reference/dumbo_washington_st_manhattan_bridge/meta.json``: camera 40.70330 N,
       73.98958 W (Washington Street between Front and Water), azimuth 355.6 deg, subject the Manhattan Bridge's
       Brooklyn tower 134 m away; rendered in portrait like the four Commons photographs the reference records.
       Question: at the real camera position, distance and bearing, is the tower the right size and shape?
       *The brick warehouse walls that frame the tower in the photographs belong to the buildings stage and are
       not in this model, so the render shows the bridge alone against the sky.*
    2. ``tower_three_quarter`` — the Brooklyn tower from the river with the sun 35 deg up and off-axis.
       Question: are the portal legs, the four horizontal struts, the finials and the two deck levels right?
    3. ``elevation_both_towers`` — a long lens with both towers, the 451.1 m main span and both anchorages in
       frame.  Question: is the span, the cable sag and the two-level deck right?
    """
    fit = ba.bridge_axis(SUPPORTS, ("tower_bk", "tower_mn"), MAIN_SPAN)
    ax = fit.axis
    fr = fit.frame
    land_bk, land_mn = ax.p(-900.0, 0.0), ax.p(900.0, 0.0)
    ctx = (("water_dark", 0.35, 1500.0, (0.0, 0.0)),
           ("sidewalk", GROUND, 460.0, (land_bk.x, land_bk.y)),
           ("sidewalk", GROUND, 460.0, (land_mn.x, land_mn.y)))
    washington_st = fr.from_lonlat(-73.98958, 40.70330, GROUND + 1.65)
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded viewpoint, used verbatim (portrait, like the reference photographs)
            ba.reference_render("dumbo_washington_st_manhattan_bridge", fr, view="dumbo_washington_street_reference",
                                ground_z=GROUND, target_z=52.0, fov_deg=62.0, size=(720, 1280), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            ba.reference_render("landmark_manhattan_bridge", fr, view="pebble_beach_reference",
                                ground_z=GROUND, target_z=52.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="dumbo_washington_street", cam=washington_st, target=ax.p(S_T_BK, 0.0, 52.0),
                 fov_deg=62.0, size=(720, 1280), context=ctx, sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="tower_three_quarter", cam=ax.p(S_T_BK - 90.0, -125.0, 26.0),
                 target=ax.p(S_T_BK, 0.0, 58.0), fov_deg=46.0, size=(1280, 720), context=ctx,
                 sun_azimuth_deg=205.0, sun_elevation_deg=35.0),
            dict(view="elevation_both_towers", cam=ax.p(0.0, -1050.0, 55.0), target=ax.p(0.0, 0.0, 56.0),
                 fov_deg=36.0, size=(1280, 720), context=ctx, sun_azimuth_deg=185.0, sun_elevation_deg=35.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Verification renders": main.__doc__.strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
