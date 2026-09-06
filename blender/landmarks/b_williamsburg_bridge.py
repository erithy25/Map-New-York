"""Williamsburg Bridge — East River, Delancey Street (Manhattan) to Broadway / Roebling Street (Brooklyn).
Leffert L. Buck (chief engineer) with Henry Hornbostel (architect), opened 19 December 1903.

Dimensions used (source in brackets)
------------------------------------
* Main span 1,600 ft = **487.68 m**; total length 7,308 ft = **2,227.4 m**; deck width 118 ft = **35.97 m**; towers
  335 ft = **102.11 m**; clearance 135 ft = **41.15 m** at mean high water [Wikipedia "Williamsburg Bridge"].
* Side spans 596 ft = **181.66 m** each, each carried on an *intermediate* tower of two piers with four columns —
  unusual for a suspension bridge and modelled as a four-column steel bent under the side-span deck.
* Stiffening trusses **40 ft = 12.19 m deep**, **67 ft = 20.42 m apart** ("three times as deep as those on the
  Brooklyn Bridge") [Wikipedia].  The four main cables run in the plane of those two trusses (two cables per truss
  line, **inferred** +-0.4 m).
* Traffic: 8 roadway lanes (two 4-lane roadways flanking the centre), **2 subway tracks** (J/M/Z) on the centre line,
  and two merged pedestrian/bicycle paths outboard of the trusses.
* Steel lattice towers, unclad — the bridge is the first major steel-tower suspension bridge.  Approach viaducts on
  braced steel columns at a 3 % grade [Wikipedia].

Placement: towers are OSM ways ``1016434034`` (Manhattan) and ``1016434035`` (Brooklyn), ``bridge:support=pylon``;
measured separation 488.15 m, **0.09 %** from the published 1,600 ft.  The Manhattan anchorage is OSM way
``1016434036``; the Brooklyn anchorage has no OSM way and is placed symmetrically at the published side-span distance
(stated as derived, not measured).  ``segments.parquet`` was not available.

Not modelled: the cable wrapping and bands, the 1990s deck replacement's orthotropic panels, the subway station
approaches at Marcy Avenue, the tower rivet detail, the original Hornbostel ornament (removed in the 1910s), and the
individual truss gusset plates.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_williamsburg_bridge"
TITLE = "Williamsburg Bridge"

MAIN_SPAN = 487.68
SIDE_SPAN = 181.66
DECK_W = 35.97
TOWER_H_MHW = 102.11
CLEARANCE_MHW = 41.15
TRUSS_DEPTH = 12.19
TRUSS_T = (-10.21, 10.21)          # 67 ft apart
CABLE_T = (-10.61, -9.81, 9.81, 10.61)
TOTAL_LEN = 2227.4
MHW = bc.MHW_ABOVE_NAVD88_M

Z_DECK_MID = CLEARANCE_MHW + MHW + 1.3       # 43.15 NAVD88 (roadway top; clearance is to the truss soffit)
Z_DECK_TOWER = Z_DECK_MID - 2.0
Z_DECK_ANCH = Z_DECK_MID - 7.5
Z_TOWER_TOP = TOWER_H_MHW + MHW              # 102.81
Z_SADDLE = Z_TOWER_TOP - 4.5
Z_CABLE_LOW = Z_DECK_MID + TRUSS_DEPTH + 2.0  # cable clears the top chord of the 12.19 m trusses
GROUND = 4.0
Z_APPROACH_END = 16.0
ANCH_L, ANCH_W, ANCH_H = 56.0, 59.0, 34.0

SUPPORTS = [
    ba.Support("tower_mn", 1016434034, (-2097.24, 1598.78), "pylon", "Manhattan tower"),
    ba.Support("tower_bk", 1016434035, (-1644.23, 1416.92), "pylon", "Brooklyn tower"),
    ba.Support("anchorage_mn", 1016434036, (-2281.92, 1672.51), "anchorage", "Manhattan anchorage"),
]

S_T_MN, S_T_BK = -MAIN_SPAN / 2, MAIN_SPAN / 2       # +s runs Manhattan -> Brooklyn
S_AF_MN, S_AF_BK = S_T_MN - SIDE_SPAN, S_T_BK + SIDE_SPAN
S_A_MN, S_A_BK = S_AF_MN - ANCH_L / 2, S_AF_BK + ANCH_L / 2
APPROACH = (TOTAL_LEN - (MAIN_SPAN + 2 * SIDE_SPAN + 2 * ANCH_L)) / 2   # 632.4 m each side
S_END_MN, S_END_BK = S_AF_MN - APPROACH, S_AF_BK + APPROACH


def deck_z(s: float) -> float:
    if s <= S_AF_MN:
        u = max(0.0, (s - S_END_MN) / (S_AF_MN - S_END_MN))
        return Z_APPROACH_END + (Z_DECK_ANCH - Z_APPROACH_END) * u
    if s < S_T_MN:
        u = (s - S_AF_MN) / SIDE_SPAN
        return Z_DECK_ANCH + (Z_DECK_TOWER - Z_DECK_ANCH) * u
    if s <= S_T_BK:
        u = s / (MAIN_SPAN / 2)
        return Z_DECK_MID - (Z_DECK_MID - Z_DECK_TOWER) * u * u
    if s < S_AF_BK:
        u = (s - S_T_BK) / SIDE_SPAN
        return Z_DECK_TOWER + (Z_DECK_ANCH - Z_DECK_TOWER) * u
    u = min(1.0, (s - S_AF_BK) / (S_END_BK - S_AF_BK))
    return Z_DECK_ANCH + (Z_APPROACH_END - Z_DECK_ANCH) * u


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_mn", "tower_bk"), MAIN_SPAN, roads_name="Williamsburg Bridge")
    axis = fit.axis
    objs: list = []
    tower = bl.TowerSpec(kind="lattice", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=DECK_W - 3.0, depth_s=11.0,
                         z_base=-9.0, z_deck=Z_DECK_TOWER, leg_w=9.4, leg_d=11.0, leg_taper=0.55,
                         # a lattice tower's portal struts are 9 m-deep girders drawn *upwards* from struts_z, so the top one is
                         # placed 15 m down to bring its top chord just under the cable saddles at 98.31 m
                         struts_z=(Z_DECK_TOWER + TRUSS_DEPTH + 6.0, 78.0, Z_TOWER_TOP - 15.0), x_brace=True,
                         pier_w=DECK_W - 1.0, pier_d=15.0, material="steel_gray", pier_material="granite_dark",
                         cable_t=CABLE_T)
    objs += bl.build_tower("tower_mn", axis, S_T_MN, tower, lod)
    objs += bl.build_tower("tower_bk", axis, S_T_BK, tower, lod)

    anch_mn = bl.AnchorageSpec(S_A_MN, ANCH_L, ANCH_W, ANCH_H, GROUND - 8.0, "granite_gray", Z_DECK_ANCH + 6.0, slope=False)
    anch_bk = bl.AnchorageSpec(S_A_BK, ANCH_L, ANCH_W, ANCH_H, GROUND - 8.0, "granite_gray", Z_DECK_ANCH + 6.0, slope=False)
    objs += bl.build_anchorage("anch_mn", axis, anch_mn, S_T_MN)
    objs += bl.build_anchorage("anch_bk", axis, anch_bk, S_T_BK)

    # deck: two 4-lane roadways either side of the two central subway tracks, walkways outboard of the trusses
    deck = bl.DeckSpec(width=DECK_W, thickness=0.9, lanes=4, lane_w=3.05, roadway_t=-4.6, roadway_w=12.2,
                       walkways=((-16.6, 2.6, 0.15), (16.6, 2.6, 0.15)), truss_depth=TRUSS_DEPTH, truss_t=TRUSS_T,
                       truss_above=True, truss_panel=9.14, truss_material="steel_gray", material="asphalt",
                       slab_material="steel_gray", tracks=(-1.6, 1.6), railing=True, lamps_spacing=48.0,
                       lamp_t=(-15.0, 15.0), centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_AF_MN, S_AF_BK, deck_z, lod, step=6.0)
    objs.append(bl.sweep("deck_road_e", axis, bl.samples(S_AF_MN, S_AF_BK, 6.0), bl.rect_section(12.2, 0.08, 4.6, 0.08),
                         deck_z, "asphalt"))

    cables = bl.CableSpec(t_offsets=CABLE_T, radius=0.24, z_low_mid=Z_CABLE_LOW, suspender_spacing=9.14,
                          suspender_radius=0.045, material="steel_silver", suspender_material="steel_gray")
    objs += bl.build_suspension_cables("cable", axis, cables, (S_T_MN, S_T_BK), Z_SADDLE, (anch_mn, anch_bk), deck_z,
                                       TRUSS_DEPTH, lod)

    # intermediate towers under each side span (two piers of four columns each)
    for name, s_mid in (("int_mn", (S_T_MN + S_AF_MN) / 2), ("int_bk", (S_T_BK + S_AF_BK) / 2)):
        for ds in (-6.0, 6.0):
            for tt in (-14.0, -5.0, 5.0, 14.0):
                objs.append(bc.box_between(f"{name}_col", axis.p(s_mid + ds, tt, -4.0),
                                           axis.p(s_mid + ds, tt, deck_z(s_mid + ds) - 1.2), 1.5, 1.5, "steel_gray"))
        cap = bc.box(f"{name}_cap", (14.0, DECK_W - 3.0, 1.4), (0, 0, deck_z(s_mid) - 1.4), "steel_gray")
        bc.transform(cap, axis.matrix(s_mid))
        objs.append(cap)

    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.8, lanes=8, lane_w=3.05, roadway_w=26.0, material="asphalt",
                          slab_material="steel_gray", railing=True, centre_yellow=True)
    objs += bl.build_approach("ap_mn", axis, bl.ApproachSpec(S_END_MN, S_AF_MN, Z_APPROACH_END, Z_DECK_ANCH, "girder",
                                                            pier_spacing=30.0, width=DECK_W, material="steel_gray",
                                                            ground_z=GROUND), lod, ap_deck)
    objs += bl.build_approach("ap_bk", axis, bl.ApproachSpec(S_AF_BK, S_END_BK, Z_DECK_ANCH, Z_APPROACH_END, "girder",
                                                            pier_spacing=30.0, width=DECK_W, material="steel_gray",
                                                            ground_z=GROUND), lod, ap_deck)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": TOWER_H_MHW, "name": TITLE,
        "main_span_m": MAIN_SPAN, "side_span_m": SIDE_SPAN, "deck_width_m": DECK_W,
        "tower_height_mhw_m": TOWER_H_MHW, "clearance_mhw_m": CLEARANCE_MHW, "truss_depth_m": TRUSS_DEPTH,
        "truss_spacing_m": 20.42, "total_modelled_length_m": S_END_BK - S_END_MN, "n_cables": 4,
        "road_lanes": 8, "subway_tracks": 2, "alignment_source": fit.source,
        "height_source": "Wikipedia: 335 ft towers, 1,600 ft main span, 135 ft clearance, 40 ft trusses 67 ft apart",
        "sources_ids": ["osm_bbbike", "published_williamsburg_bridge"],
        "fidelity_statement": (
            "Exact to published values: 487.68 m main span, 181.66 m side spans, 2,227.4 m total, 35.97 m deck, "
            "102.11 m steel lattice towers, 41.15 m clearance, 12.19 m stiffening trusses 20.42 m apart, 8 road "
            "lanes, 2 subway tracks, outboard walkways, four cables, side spans on intermediate four-column bents. "
            "Inferred: cable plane offsets (+-0.4 m), anchorage block dimensions (no published figure found), deck "
            "elevations away from the published mid-span clearance, the equal split of the approach length. "
            "The Brooklyn anchorage is placed symmetrically (no OSM way); the Manhattan one is measured. "
            "Not modelled: cable wrapping and bands, orthotropic deck panels, Marcy Avenue station approaches, rivet "
            "and gusset detail, the removed Hornbostel ornament."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("tower_mn", "tower_bk"), MAIN_SPAN)
    ax = fit.axis
    land_mn, land_bk = ax.p(-800.0, 0.0), ax.p(800.0, 0.0)
    ctx = (("water_dark", 0.35, 1500.0, (0.0, 0.0)),
           ("ground_urban", GROUND, 470.0, (land_mn.x, land_mn.y)),
           ("ground_urban", GROUND, 470.0, (land_bk.x, land_bk.y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_williamsburg_bridge", fit.frame, view="williamsburg_reference",
                                ground_z=GROUND, target_z=Z_TOWER_TOP - 12.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="east_river_park", cam=ax.p(-330.0, -300.0, 6.0), target=ax.p(0.0, 0.0, 55.0), fov_deg=52.0,
                 context=ctx, sun_azimuth_deg=140.0, sun_elevation_deg=32.0),
            dict(view="elevation_from_river", cam=ax.p(0.0, -560.0, 22.0), target=ax.p(0.0, 0.0, 55.0), fov_deg=40.0,
                 context=ctx, sun_azimuth_deg=180.0, sun_elevation_deg=30.0),
            dict(view="roadway", cam=ax.p(S_T_MN - 120.0, -4.6, deck_z(S_T_MN - 120.0) + 2.2),
                 target=ax.p(S_T_MN + 120.0, -2.0, Z_DECK_MID + 6.0), fov_deg=60.0, context=ctx,
                 sun_azimuth_deg=300.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
