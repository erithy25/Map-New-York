"""Brooklyn Bridge — East River, Manhattan (Park Row) to Brooklyn (Adams Street).  J. A. Roebling / W. A. Roebling /
E. W. Roebling, 1869-1883.  NHL 1964, NYC Landmark LP-0098.

Dimensions used (source in brackets)
------------------------------------
* Main span 1,595.5 ft = **486.3 m** between the tower centres; side spans 930 ft = **283.5 m** (tower to anchorage);
  Manhattan approach 1,567 ft = 477.6 m, Brooklyn approach 971 ft = 296.0 m; deck width 85 ft = **25.91 m**
  [Wikipedia "Brooklyn Bridge" / NYCDOT].  Modelled length tower-to-tower + side spans + approaches = 1,827.3 m against
  the published 6,016 ft = 1,833.7 m over-all (the 6.4 m difference is the anchorage masonry, which the published
  figure measures from Centre Street; stated as a gap).
* Towers: **84.3 m** above mean high water (276.5 ft; Wikipedia also quotes 278.25 ft = 84.81 m — the 84.3 m figure
  named in the build brief is used and the model is within 0.6 % of the alternative).  Two pointed Gothic arches per
  tower, each **10.29 m** wide (33.75 ft) and **35.66 m** high (117 ft), springing from the roadway; arch floor
  119.25 ft = 36.35 m above mean water; tower plan at the high-water line 140 x 59 ft = **42.67 x 17.98 m**; tower head
  159 ft (48.5 m) above the roadway.  Granite (Maine/Rockland) over a limestone-and-granite pier.
* Anchorages: 129 x 119 ft = **39.32 x 36.27 m** at the base, 117 x 104 ft = 35.66 x 31.70 m at the top, 89 ft
  (27.1 m) high; the roadway leaves through the top and the four cables enter the front face.
* Cables: **four** main cables, 15.75 in = **0.400 m** diameter, 5,282 galvanised wires each; design sag 128 ft =
  **39.0 m** over the main span, giving a saddle at 81.45 m NAVD88 and a mid-span low point at 42.45 m NAVD88 so that
  the shortest suspender is the published 8 ft (2.44 m).  1,088-1,520 suspenders (this model: 2.286 m = 7.5 ft pitch on
  every cable in main and side spans, 1,832 suspenders) and ~400 diagonal stays (this model: 25 per cable per
  direction per tower = 400), stay reach 18-131 m matching the published 138-449 ft stay lengths.
* Clearance 127 ft = 38.71 m above mean high water at mid-span; the deck crest is a parabola from 37.05 m NAVD88 at
  the towers to 39.41 m NAVD88 at mid-span.  MHW = NAVD88 + 0.70 m (b_common.MHW_ABOVE_NAVD88_M).
* Promenade: 18 ft = **5.5 m** above the roadways, 10-17 ft wide (this model 4.8 m), timber deck on the two inner
  stiffening trusses; it **splits around the central pier at each tower and passes through both Gothic arches**.
* Cable planes at t = +-3.10 m and +-12.55 m: the inner pair rises from the promenade edge trusses and the outer pair
  from the deck-edge trusses, so that all four saddles sit over solid granite either side of the arch openings.  These
  offsets are *inferred* from the six-truss deck division and photographs (+-0.5 m), not from a published table.
* Roadways: two carriageways of 8.9 m each side of the promenade, marked as 3 lanes each.  Published capacity is five
  motor lanes plus (since 2021) a two-way protected bike lane on the innermost Manhattan-bound lane; the model marks
  six lanes and does not distinguish the bike lane (stated gap).

Placement: the two towers are the OSM ways ``317352708`` (Brooklyn) and ``1255363983`` (Manhattan), both tagged
``bridge:support=pylon``; their NYC_TM centroids are 486.49 m apart, 0.04 % from the published 486.3 m.  The
anchorages are OSM ways ``888759002`` (Brooklyn) and ``1255363984`` (Manhattan).  ``data/processed/roads/segments.parquet``
did not exist when this model was built, so the deck centreline comes from the tower pair alone (b_align records the
source in the report).

Not modelled: the caissons and their timber, the individual cable wrapping wires and cable bands, the granite coursing
and its joints, the necklace lighting fixtures, the 1950s-era steel approach ramps at Park Row, the vaults inside the
anchorages, the wooden promenade benches, the bronze plaques, and the two intermediate longitudinal trusses under each
roadway (only the four trusses that show above the deck are built).
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

ID = "b_brooklyn_bridge"
TITLE = "Brooklyn Bridge"

# -------------------------------------------------------------------------------------- published / measured constants
MAIN_SPAN = 486.3          # m, 1,595.5 ft
SIDE_SPAN = 283.5          # m, 930 ft
APPROACH_MN = 477.6        # m, 1,567 ft
APPROACH_BK = 296.0        # m, 971 ft
DECK_W = 25.91             # m, 85 ft
TOWER_H_MHW = 84.3         # m above mean high water, 276.5 ft
TOWER_W = 42.67            # m, 140 ft (across the bridge, at the high-water line)
TOWER_D = 17.98            # m, 59 ft (along the bridge)
ARCH_W = 10.29             # m, 33.75 ft
ARCH_H = 35.66             # m, 117 ft
ARCH_GAP = 8.83            # m, |t| of each arch centre (from the 42.67 m width and the two 10.29 m openings)
ARCH_FLOOR_MHW = 36.35     # m above mean water, 119.25 ft
CLEARANCE_MHW = 38.71      # m above mean high water at mid-span, 127 ft
ANCH_L = 39.32             # m, 129 ft
ANCH_W = 36.27             # m, 119 ft
ANCH_H = 27.13             # m, 89 ft
CABLE_D = 0.400            # m, 15.75 in
CABLE_SAG = 39.0           # m, 128 ft design sag
SUSPENDER_PITCH = 2.286    # m, 7.5 ft
PROMENADE_W = 4.8          # m
PROMENADE_DZ = 5.49        # m, 18 ft above the roadway
CABLE_T = (-12.55, -3.10, 3.10, 12.55)
TRUSS_T = (-12.55, -2.90, 2.90, 12.55)
TRUSS_DEPTH = 5.2          # m, above the deck

MHW = bc.MHW_ABOVE_NAVD88_M
Z_DECK_TOWER = ARCH_FLOOR_MHW + MHW          # 37.05 NAVD88
Z_DECK_MID = CLEARANCE_MHW + MHW             # 39.41 NAVD88
Z_TOWER_TOP = TOWER_H_MHW + MHW              # 85.00 NAVD88
Z_DECK_ANCHOR = 32.0                         # NAVD88, roadway leaving the anchorage (inferred, +-1 m)
Z_APPROACH_MN_END = 13.0                     # NAVD88 at Park Row (inferred; 4.0 % ramp within the published length)
Z_APPROACH_BK_END = 18.0                     # NAVD88 at Adams Street (inferred; 4.7 % ramp)
Z_CABLE_ENTRY = 30.5                         # NAVD88, cable entry face of each anchorage (inferred, +-1 m)
Z_SADDLE = 81.45                             # NAVD88 (Z_DECK_MID + 0.6 + 2.44 + CABLE_SAG)
Z_CABLE_LOW = Z_SADDLE - CABLE_SAG           # 42.45 NAVD88
GROUND_BK = 4.0                              # NAVD88, Brooklyn approach ground
GROUND_MN = 3.0                              # NAVD88, Manhattan approach ground

SUPPORTS = [
    ba.Support("tower_bk", 317352708, (-3748.38, 456.65), "pylon", "Brooklyn tower, OSM bridge:support=pylon"),
    ba.Support("tower_mn", 1255363983, (-4084.56, 808.30), "pylon", "Manhattan tower, OSM bridge:support=pylon"),
    ba.Support("anchorage_bk", 888759002, (-3525.40, 224.51), "anchorage", "Brooklyn anchorage, OSM bridge:support=abutment"),
    ba.Support("anchorage_mn", 1255363984, (-4302.30, 1034.84), "anchorage", "Manhattan anchorage, OSM bridge:support=abutment"),
]

S_TOWER_BK = -MAIN_SPAN / 2
S_TOWER_MN = +MAIN_SPAN / 2
S_ANCH_FACE_BK = S_TOWER_BK - SIDE_SPAN      # -526.65
S_ANCH_FACE_MN = S_TOWER_MN + SIDE_SPAN      # +526.65
S_ANCH_BK = S_ANCH_FACE_BK - ANCH_L / 2
S_ANCH_MN = S_ANCH_FACE_MN + ANCH_L / 2
S_END_BK = S_ANCH_FACE_BK - APPROACH_BK
S_END_MN = S_ANCH_FACE_MN + APPROACH_MN


def deck_z(s: float) -> float:
    """Roadway top elevation (NAVD88) along the bridge: parabolic crest on the main span, straight elsewhere."""
    if s <= S_END_BK:
        return Z_APPROACH_BK_END
    if s < S_ANCH_FACE_BK:
        u = (s - S_END_BK) / (S_ANCH_FACE_BK - S_END_BK)
        return Z_APPROACH_BK_END + (Z_DECK_ANCHOR - Z_APPROACH_BK_END) * u
    if s < S_TOWER_BK:
        u = (s - S_ANCH_FACE_BK) / SIDE_SPAN
        return Z_DECK_ANCHOR + (Z_DECK_TOWER - Z_DECK_ANCHOR) * u
    if s <= S_TOWER_MN:
        u = s / (MAIN_SPAN / 2)
        return Z_DECK_MID - (Z_DECK_MID - Z_DECK_TOWER) * u * u
    if s < S_ANCH_FACE_MN:
        u = (s - S_TOWER_MN) / SIDE_SPAN
        return Z_DECK_TOWER + (Z_DECK_ANCHOR - Z_DECK_TOWER) * u
    if s < S_END_MN:
        u = (s - S_ANCH_FACE_MN) / (S_END_MN - S_ANCH_FACE_MN)
        return Z_DECK_ANCHOR + (Z_APPROACH_MN_END - Z_DECK_ANCHOR) * u
    return Z_APPROACH_MN_END


def promenade_t(s: float) -> float:
    """|t| of each promenade branch centre.  0 = one central walkway; ARCH_GAP = split around the tower's centre pier.

    The transition is a 26 m long straight taper each side of every tower, so the walk opens out, passes through both
    Gothic arches and closes again — the real arrangement.
    """
    for st in (S_TOWER_BK, S_TOWER_MN):
        d = abs(s - st)
        if d <= TOWER_D / 2 + 4.0:
            return ARCH_GAP
        if d <= TOWER_D / 2 + 30.0:
            u = (d - (TOWER_D / 2 + 4.0)) / 26.0
            return ARCH_GAP * (1.0 - u)
    return 0.0


def _promenade(axis: bl.Axis, lod: int) -> list:
    """Timber promenade 5.49 m above the roadway, splitting around each tower pier.

    Built as two mirrored strips whose inner edge is the centreline where the walk is single and ``+-(gap - w/2)``
    where it is split; the two strips coincide into one 4.8 m walk away from the towers.
    """
    out = []
    ss = bl.samples(S_ANCH_FACE_BK, S_ANCH_FACE_MN, 4.0)
    half = PROMENADE_W / 2
    branch_half = 1.55  # each branch through an arch is 3.1 m wide

    def z(s: float) -> float:
        return deck_z(s) + PROMENADE_DZ

    for side in (-1, 1):
        def section(s: float, side=side):
            g = promenade_t(s)
            if g <= 0.01:
                t0, t1 = (0.0, half) if side > 0 else (-half, 0.0)
            else:
                w = branch_half + (half - branch_half) * max(0.0, 1.0 - g / ARCH_GAP)
                t0, t1 = (side * g - w, side * g + w)
            return [(t0, -0.35), (t1, -0.35), (t1, 0.0), (t0, 0.0)]
        out.append(bl.sweep_var(f"promenade{side}", axis, ss, section, z, "wood_deck"))
        if lod == 0:
            rails = []
            n = int((S_ANCH_FACE_MN - S_ANCH_FACE_BK) / 24.0)
            for k in range(n):
                a = S_ANCH_FACE_BK + (S_ANCH_FACE_MN - S_ANCH_FACE_BK) * k / n
                b = S_ANCH_FACE_BK + (S_ANCH_FACE_MN - S_ANCH_FACE_BK) * (k + 1) / n
                sec_a = section(a)
                sec_b = section(b)
                ta = sec_a[1][0] if side > 0 else sec_a[0][0]
                tb = sec_b[1][0] if side > 0 else sec_b[0][0]
                rails.append(bc.railing(f"prom_rail{side}_{k}", axis.p(a, ta, z(a)), axis.p(b, tb, z(b)), 1.15, 2.4, "steel_black", 3))
            out.append(bc.join(rails, f"promenade_railing{side}"))
    if lod == 0:
        lamps = []
        s = S_ANCH_FACE_BK + 20.0
        while s < S_ANCH_FACE_MN:
            g = promenade_t(s)
            for side in (-1, 1):
                t = side * (g + (branch_half + 0.4 if g > 0.01 else half + 0.4))
                lamps.append(bc.lamp_post("prom_lamp", axis.p(s, t, deck_z(s) + PROMENADE_DZ), 4.2, 0.0,
                                          0.0, "steel_black"))
            s += 36.0
        out.append(bc.join(lamps, "promenade_lamps"))
    return out


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_bk", "tower_mn"), MAIN_SPAN, roads_name="Brooklyn Bridge")
    axis = fit.axis
    objs: list = []

    # ---- towers -------------------------------------------------------------------------------------------------
    tower = bl.TowerSpec(kind="gothic", z_top=Z_TOWER_TOP, z_saddle=Z_SADDLE, width_t=TOWER_W, depth_s=TOWER_D,
                         z_base=-13.0, z_deck=Z_DECK_TOWER, arch_w=ARCH_W, arch_h=ARCH_H, arch_gap=ARCH_GAP,
                         batter=0.055, cornice_w=1.6, course_h=3.0, pier_w=TOWER_W + 1.6, pier_d=TOWER_D + 1.6,
                         material="granite_gray", pier_material="granite_dark", cable_t=CABLE_T)
    for name, s in (("tower_bk", S_TOWER_BK), ("tower_mn", S_TOWER_MN)):
        objs += bl.build_tower(name, axis, s, tower, lod)

    # ---- anchorages ---------------------------------------------------------------------------------------------
    anch_bk = bl.AnchorageSpec(S_ANCH_BK, ANCH_L, ANCH_W, ANCH_H + GROUND_BK, GROUND_BK - 6.0, "granite_gray", Z_CABLE_ENTRY)
    anch_mn = bl.AnchorageSpec(S_ANCH_MN, ANCH_L, ANCH_W, ANCH_H + GROUND_MN, GROUND_MN - 6.0, "granite_gray", Z_CABLE_ENTRY)
    objs += bl.build_anchorage("anch_bk", axis, anch_bk, S_TOWER_BK)
    objs += bl.build_anchorage("anch_mn", axis, anch_mn, S_TOWER_MN)

    # ---- deck ---------------------------------------------------------------------------------------------------
    deck = bl.DeckSpec(width=DECK_W, thickness=1.0, lanes=3, lane_w=2.97, roadway_t=-6.85, roadway_w=8.9,
                       truss_depth=TRUSS_DEPTH, truss_t=TRUSS_T, truss_above=True, truss_panel=6.1,
                       truss_material="steel_gray", material="asphalt", slab_material="steel_gray",
                       railing=False, centre_yellow=False)
    objs += bl.build_deck("deck", axis, deck, S_ANCH_FACE_BK, S_ANCH_FACE_MN, deck_z, lod, step=6.0)
    # the second carriageway (build_deck marks one roadway; mirror it)
    deck2 = bl.DeckSpec(width=DECK_W, thickness=0.0, lanes=3, lane_w=2.97, roadway_t=6.85, roadway_w=8.9,
                        truss_depth=0.0, material="asphalt", slab_material="steel_gray", railing=False, centre_yellow=False)
    road2 = bl.sweep("deck_road2", axis, bl.samples(S_ANCH_FACE_BK, S_ANCH_FACE_MN, 6.0),
                     bl.rect_section(8.9, 0.08, 6.85, 0.08), deck_z, "asphalt")
    objs.append(road2)
    if lod == 0:
        parts = []
        n = max(int((S_ANCH_FACE_MN - S_ANCH_FACE_BK) / 100.0), 1)
        for k in range(n):
            a = S_ANCH_FACE_BK + (S_ANCH_FACE_MN - S_ANCH_FACE_BK) * k / n
            b = S_ANCH_FACE_BK + (S_ANCH_FACE_MN - S_ANCH_FACE_BK) * (k + 1) / n
            lm = bc.lane_markings(f"deck_lm2_{k}", axis.p(a, 0, deck_z(a)), axis.p(b, 0, deck_z(b)), 2.97, 3, 0.09,
                                  centre_yellow=False, offset_t=6.85)
            if lm is not None:
                parts.append(lm)
        objs.append(bc.join(parts, "deck_markings2"))
    _ = deck2
    objs += _promenade(axis, lod)

    # ---- cables, suspenders, diagonal stays ---------------------------------------------------------------------
    cables = bl.CableSpec(t_offsets=CABLE_T, radius=CABLE_D / 2, z_low_mid=Z_CABLE_LOW, suspender_spacing=SUSPENDER_PITCH,
                          suspender_radius=0.028, stays_per_direction=25, stay_reach_min=18.0, stay_reach_max=131.0,
                          stay_head_drop=26.0, material="steel_silver", suspender_material="steel_silver", side_spans=True)
    objs += bl.build_suspension_cables("cable", axis, cables, (S_TOWER_BK, S_TOWER_MN), Z_SADDLE, (anch_bk, anch_mn),
                                       deck_z, 0.6, lod)

    # ---- masonry approach viaducts ------------------------------------------------------------------------------
    ap_bk = bl.ApproachSpec(S_END_BK, S_ANCH_FACE_BK, Z_APPROACH_BK_END, Z_DECK_ANCHOR, "masonry_arches",
                            width=DECK_W, material="granite_gray", ground_z=GROUND_BK, arch_span=13.5)
    ap_mn = bl.ApproachSpec(S_ANCH_FACE_MN, S_END_MN, Z_DECK_ANCHOR, Z_APPROACH_MN_END, "masonry_arches",
                            width=DECK_W, material="granite_gray", ground_z=GROUND_MN, arch_span=13.5)
    ap_deck = bl.DeckSpec(width=DECK_W, thickness=0.5, lanes=6, lane_w=2.97, roadway_w=19.0, material="asphalt",
                          slab_material="concrete_dark", railing=True, centre_yellow=True)
    objs += bl.build_approach("ap_bk", axis, ap_bk, lod, ap_deck)
    objs += bl.build_approach("ap_mn", axis, ap_mn, lod, ap_deck)

    height_m = Z_TOWER_TOP - (-13.0)
    extras = {
        "origin_tm": fit.frame.origin_tm,
        "heading_deg": fit.heading_deg,
        "height_m": TOWER_H_MHW,
        "name": TITLE,
        "lp_number": "LP-0098",
        "main_span_m": MAIN_SPAN,
        "side_span_m": SIDE_SPAN,
        "deck_width_m": DECK_W,
        "tower_height_mhw_m": TOWER_H_MHW,
        "tower_top_navd88_m": Z_TOWER_TOP,
        "clearance_mhw_m": CLEARANCE_MHW,
        "arch_opening_m": [ARCH_W, ARCH_H],
        "cable_diameter_m": CABLE_D,
        "cable_sag_m": CABLE_SAG,
        "n_cables": 4,
        "suspender_pitch_m": SUSPENDER_PITCH,
        "stays_per_cable_per_direction": 25,
        "total_modelled_length_m": S_END_MN - S_END_BK,
        "alignment_source": fit.source,
        "height_source": "Wikipedia/NYCDOT: towers 276.5 ft (84.3 m) above MHW, deck 127 ft (38.7 m) clearance",
        "sources_ids": ["osm_bbbike", "published_brooklyn_bridge"],
        "fidelity_statement": (
            "Exact to published values: 486.3 m main span, 283.5 m side spans, 84.3 m towers above MHW, "
            "10.29 x 35.66 m Gothic arch openings, 42.67 x 17.98 m tower plan, 25.91 m deck, 38.71 m mid-span "
            "clearance, four 0.400 m cables with the published 39.0 m design sag, 2.286 m (7.5 ft) suspender pitch on "
            "every cable (1,832 suspenders), 400 diagonal stays reaching 18-131 m, promenade 5.49 m above the roadway "
            "and split around each tower pier through both arches, 39.32 x 36.27 m anchorages, masonry approach "
            "viaducts of the published 296.0 m / 477.6 m lengths. Inferred (stated tolerance): cable plane offsets "
            "+-3.10 / +-12.55 m (+-0.5 m, from the six-truss deck division and photographs), approach ramp end "
            "elevations, anchorage cable-entry elevation, granite batter. Not modelled: caissons, cable wrapping and "
            "bands, granite coursing, necklace lighting, anchorage vaults, the two longitudinal trusses under each "
            "roadway, the 2021 protected bike lane (six lanes are marked instead of five lanes plus a bike lane)."),
    }
    _ = height_m
    return objs, extras


def main() -> None:
    """Four verification renders, each framed and lit to answer one question.

    1. ``dumbo_main_street_park`` — street level in Brooklyn Bridge Park at the foot of Main Street, the canonical
       DUMBO view of *this* bridge.  (The famous Washington Street shot, whose real photographic viewpoint is
       recorded in ``docs/verification/reference/dumbo_washington_st_manhattan_bridge/meta.json`` — camera
       40.7033 N, 73.98958 W, azimuth 355.6 deg — frames the **Manhattan** Bridge, and is rendered on that model.)
       Question: does the bridge read correctly at street level and eye height, at the right size and distance?
    2. ``tower_three_quarter`` — the Brooklyn tower from the river, close enough that the whole 84.3 m tower fills
       the frame, with the sun 35 deg up and roughly 60 deg off the tower's face so the 3.0 m string courses, the
       arch reveals and the batter all cast shadow.  Question: are the two pointed arches, the tower's plan and its
       height right, and does the deck pass through the arches at the right level?
    3. ``promenade`` — deck level on the promenade looking at the Brooklyn tower.  Question: is the promenade
       5.49 m above the roadway, does it split around the centre pier and pass through both arches, and do the
       four cables and the diagonal stay fan converge correctly?
    4. ``elevation_both_towers`` — a long lens from the river with **both** towers and both approaches in frame.
       Question: is the 486.3 m main span, the 39.0 m cable sag, the suspender rhythm and the deck crest right?
    """
    fit = ba.bridge_axis(SUPPORTS, ("tower_bk", "tower_mn"), MAIN_SPAN)
    fr = fit.frame
    ax = fit.axis
    land_bk = ax.p(-800.0, 0.0)
    land_mn = ax.p(900.0, 0.0)
    ctx = (("water_dark", 0.35, 1600.0, (0.0, 0.0)),
           ("sidewalk", GROUND_BK, 480.0, (land_bk.x, land_bk.y)),
           ("sidewalk", GROUND_MN, 560.0, (land_mn.x, land_mn.y)))
    # 1. Brooklyn Bridge Park, Main Street lawn (40.70345 N, 73.99373 W): 90 m east of the Brooklyn tower
    park = fr.from_lonlat(-73.99373, 40.70345, GROUND_BK + 1.65)
    park_t = ax.p(S_TOWER_BK + 40.0, 0.0, 46.0)
    # 2. three-quarter of the Brooklyn tower from the river, south-east of it
    tq = ax.p(S_TOWER_BK - 96.0, -122.0, 26.0)
    tq_t = ax.p(S_TOWER_BK, 0.0, 46.0)
    # 3. promenade, 150 m short of the Brooklyn tower
    prom = ax.p(S_TOWER_BK - 150.0, 0.0, deck_z(S_TOWER_BK - 150.0) + PROMENADE_DZ + 1.65)
    prom_t = ax.p(S_TOWER_BK + 30.0, 0.0, deck_z(S_TOWER_BK) + PROMENADE_DZ + 8.0)
    # 4. full elevation, far enough back and long enough a lens that both towers fit
    elev = ax.p(0.0, -1150.0, 55.0)
    elev_t = ax.p(0.0, 0.0, 52.0)
    ba.run_landmark(
        ID, TITLE, build, bins=(), budget_lod0=900_000, budget_lod1=140_000,
        renders=[
            dict(view="dumbo_main_street_park", cam=park, target=park_t, fov_deg=64.0, context=ctx,
                 sun_azimuth_deg=215.0, sun_elevation_deg=35.0, size=(1280, 720)),
            dict(view="tower_three_quarter", cam=tq, target=tq_t, fov_deg=46.0, context=ctx,
                 sun_azimuth_deg=205.0, sun_elevation_deg=35.0, size=(1280, 720)),
            dict(view="promenade", cam=prom, target=prom_t, fov_deg=62.0, context=ctx,
                 sun_azimuth_deg=250.0, sun_elevation_deg=35.0, size=(1280, 720)),
            dict(view="elevation_both_towers", cam=elev, target=elev_t, fov_deg=34.0, context=ctx,
                 sun_azimuth_deg=185.0, sun_elevation_deg=35.0, size=(1280, 720)),
        ],
        sections={
            "Placement": fit.report(),
            "Published dimensions": __doc__.split("Dimensions used (source in brackets)\n------------------------------------\n")[1]
            .split("\nPlacement:")[0].strip(),
            "Verification renders": main.__doc__.strip(),
            "Not modelled": __doc__.split("Not modelled:")[1].strip(),
        },
    )


if __name__ == "__main__":
    main()
