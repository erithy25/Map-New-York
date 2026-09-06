"""Hell Gate Bridge (New York Connecting Railroad Bridge) — Hell Gate, Astoria (Queens) to Wards Island.  Gustav
Lindenthal (engineer) with Henry Hornbostel (architect), opened 9 March 1917.  The largest steel arch in the world
until 1931 and the model for the Sydney Harbour Bridge.

Dimensions used (source in brackets)
------------------------------------
* Steel **through arch**: **1,017 ft = 310.0 m between the outer faces**, 977.5 ft = **297.94 m clear** between the
  inner faces; width 100 ft = **30.48 m**; clearance below **135 ft = 41.15 m**; the deck reaches **145 ft = 44.20 m**
  above mean high water at the centre; the arch crown stands **305 ft = 92.96 m** above mean high water
  [Wikipedia "Hell Gate Bridge"].
* Masonry towers at each end of the arch: **220 ft = 67.06 m** high, concrete clad with Maine granite above ground.
  They are purely architectural — the arch carries no load into them.
* Tracks: **4** originally, **3** in service today (2 Amtrak Northeast Corridor + 1 New York & Atlantic freight);
  standard gauge 1.435 m.  This model lays all four track beds and rails the three in service.
* Approach viaducts: Wards Island ~2,650 ft = 810 m and Randalls Island ~1,965 ft = 599 m to the north-west, plus the
  Astoria approach to the south-east; total structure with approaches 17,000 ft = 5.2 km.
* Colour: the "Hell Gate red" applied in the 1990s.

Placement: the two masonry towers are OSM ways ``1016643614`` (Astoria/Queens) and ``1016643613`` (Wards Island),
tagged ``bridge:support``.  **Their centre-to-centre separation, 329.47 m, is a measurement, not a published figure**
— it is used as-is for the tower positions, and the published 310.0 m arch (outer faces) is then built symmetrically
between them, leaving 9.7 m of masonry outboard of each springing, which matches the photographs.
``segments.parquet`` was not available.

Gap: only 300 m of the Wards Island approach and 220 m of the Astoria approach are modelled, not the published 810 m /
599 m / 5.2 km; beyond that the structure is ordinary railway viaduct that the rail and terrain stages carry.

Not modelled: the Little Hell Gate and Bronx Kill spans (they belong to the same railway but are separate structures),
the catenary masts and overhead wire, the signal bridges, the Hornbostel cornice detail on the towers, the rivet and
gusset plates, and the ballast and sleepers (a continuous bed is used instead).
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402

ID = "b_hell_gate"
TITLE = "Hell Gate Bridge"

TOWER_SEP = 329.47          # measured (OSM), not published
ARCH_SPAN_OUTER = 310.0     # 1,017 ft
ARCH_SPAN_CLEAR = 297.94    # 977.5 ft
WIDTH = 30.48
TOWER_H_MHW = 67.06
CLEARANCE_MHW = 41.15
DECK_MHW = 44.20
CROWN_MHW = 92.96
MHW = bc.MHW_ABOVE_NAVD88_M

Z_DECK = DECK_MHW + MHW            # 44.90 NAVD88 (top of rail bed at the centre)
Z_CROWN = CROWN_MHW + MHW          # 93.66
Z_TOWER_TOP = TOWER_H_MHW + MHW    # 67.76
RIB_DEPTH = 6.0                    # depth between the arch's two chord centrelines (inferred)
UPPER_CHORD_H = 1.2                # section depth of the upper chord in build_steel_arch (inferred)
# build_steel_arch puts the lower chord's crown at z_deck + 0.75 * rise, the upper chord centreline RIB_DEPTH above it
# and the chord section is centred on that line; the published 305 ft is the *top* of the arch, so solve for the rise
# that lands the upper surface of the upper chord exactly on Z_CROWN
RISE = (Z_CROWN - Z_DECK - RIB_DEPTH - UPPER_CHORD_H / 2) / 0.75
TRACKS = (-6.0, -2.0, 2.0, 6.0)
GROUND = 4.0
AP_WARDS = 300.0
AP_ASTORIA = 220.0

SUPPORTS = [
    ba.Support("tower_qn", 1016643614, (2481.07, 9051.52), "pylon", "Astoria (Queens) masonry tower"),
    ba.Support("tower_wi", 1016643613, (2246.72, 9283.10), "pylon", "Wards Island masonry tower"),
]

S_T_QN, S_T_WI = -TOWER_SEP / 2, TOWER_SEP / 2      # +s runs Queens -> Wards Island
S_ARCH0, S_ARCH1 = -ARCH_SPAN_OUTER / 2, ARCH_SPAN_OUTER / 2
S_END_QN, S_END_WI = S_T_QN - AP_ASTORIA, S_T_WI + AP_WARDS


def deck_z(s: float) -> float:
    """Level between the towers, then a 0.5 % descent along the approaches."""
    if s < S_T_QN:
        return Z_DECK - (S_T_QN - s) * 0.005
    if s > S_T_WI:
        return Z_DECK - (s - S_T_WI) * 0.005
    return Z_DECK


def build(lod: int = 0):
    fit = ba.bridge_axis(SUPPORTS, ("tower_qn", "tower_wi"), TOWER_SEP, roads_name="HELL GATE BRG")
    axis = fit.axis
    objs: list = []

    # ---- masonry towers (architectural, not structural) ---------------------------------------------------------
    for nm, s in (("tower_qn", S_T_QN), ("tower_wi", S_T_WI)):
        prof = [(-25.0, -6.0), (25.0, -6.0), (25.0, Z_TOWER_TOP - 8.0), (21.5, Z_TOWER_TOP - 8.0),
                (21.5, Z_TOWER_TOP - 3.0), (23.5, Z_TOWER_TOP - 3.0), (23.5, Z_TOWER_TOP),
                (-23.5, Z_TOWER_TOP), (-23.5, Z_TOWER_TOP - 3.0), (-21.5, Z_TOWER_TOP - 3.0),
                (-21.5, Z_TOWER_TOP - 8.0), (-25.0, Z_TOWER_TOP - 8.0)]
        hole = bc.round_arch(WIDTH + 3.0, Z_DECK + 12.0, 0.0, -5.0)
        body = bc.profile_extrude(f"{nm}_body", prof, 22.0, "granite_gray", holes=[hole], plane="yz")
        bc.transform(body, axis.matrix(s))
        objs.append(body)

    # ---- the steel arch -----------------------------------------------------------------------------------------
    objs += bl.build_steel_arch("arch", axis, S_ARCH0, S_ARCH1, Z_DECK, RISE, WIDTH - 3.0, "steel_red", lod,
                                n=44 if lod == 0 else 20, through=True, rib_depth=RIB_DEPTH, hanger_spacing=9.14)

    # ---- deck: four track beds inside the arch, rails on the three in service -----------------------------------
    ss = bl.samples(S_END_QN, S_END_WI, 9.0)
    objs.append(bl.sweep("deck_floor", axis, ss, bl.rect_section(WIDTH, 1.6, 0.0, 0.0), deck_z, "steel_red"))
    for i, t in enumerate(TRACKS):
        objs.append(bl.sweep(f"track{i}_bed", axis, ss, bl.rect_section(3.6, 0.35, t, 0.35), deck_z, "concrete_dark"))
        if lod == 0 and i < 3:
            for dt in (-0.7175, 0.7175):
                objs.append(bl.sweep(f"track{i}_rail{dt:+.2f}", axis, ss, bl.rect_section(0.07, 0.16, t + dt, 0.51),
                                     deck_z, "steel_gray"))
    if lod == 0:
        rails = []
        n = max(int((S_END_WI - S_END_QN) / 60.0), 1)
        for side in (-1, 1):
            for k in range(n):
                a = S_END_QN + (S_END_WI - S_END_QN) * k / n
                b = S_END_QN + (S_END_WI - S_END_QN) * (k + 1) / n
                rails.append(bc.railing(f"walk{side}_{k}", axis.p(a, side * (WIDTH / 2 - 0.4), deck_z(a)),
                                        axis.p(b, side * (WIDTH / 2 - 0.4), deck_z(b)), 1.1, 3.0))
        objs.append(bc.join(rails, "deck_railing"))

    # ---- approach viaducts: reinforced-concrete arches on the Astoria side, steel girder towards Wards Island ----
    objs += bl.build_masonry_arches("ap_astoria", axis, S_END_QN, S_T_QN - 12.0, 30.0, 6.0, deck_z(S_END_QN) + 0.2,
                                    GROUND, WIDTH - 4.0, "concrete", lod)
    objs += bl.build_approach("ap_wards", axis, bl.ApproachSpec(S_T_WI + 12.0, S_END_WI, deck_z(S_T_WI + 12.0),
                                                               deck_z(S_END_WI), "girder", pier_spacing=30.0,
                                                               width=WIDTH - 3.0, material="steel_red",
                                                               ground_z=GROUND), lod)

    extras = {
        "origin_tm": fit.frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": CROWN_MHW, "name": TITLE,
        "arch_span_outer_m": ARCH_SPAN_OUTER, "arch_span_clear_m": ARCH_SPAN_CLEAR, "width_m": WIDTH,
        "tower_height_mhw_m": TOWER_H_MHW, "clearance_mhw_m": CLEARANCE_MHW, "crown_mhw_m": CROWN_MHW,
        "deck_mhw_m": DECK_MHW, "tracks_total": 4, "tracks_in_service": 3,
        "tower_separation_measured_m": TOWER_SEP, "total_modelled_length_m": S_END_WI - S_END_QN,
        "alignment_source": fit.source,
        "height_source": "Wikipedia: 1,017 ft outer / 977.5 ft clear arch, 220 ft towers, 135 ft clearance, 305 ft crown",
        "sources_ids": ["osm_bbbike", "published_hell_gate"],
        "fidelity_statement": (
            "Exact to published values: 310.0 m arch between outer faces, 30.48 m width, 67.06 m granite-clad towers, "
            "41.15 m clearance, 44.20 m deck and 92.96 m arch crown above MHW, four track beds with the three "
            "in-service tracks railed at 1.435 m gauge, Hell Gate red. The 329.47 m tower separation is a "
            "measurement from the OSM support polygons, not a published figure. Inferred: tower plan dimensions, "
            "rib depth, hanger spacing, approach pier spacing. Gap: 300 m / 220 m of approach viaduct modelled "
            "instead of the published 810 m / 599 m / 5.2 km. Not modelled: the Little Hell Gate and Bronx Kill "
            "spans, catenary masts and wire, signal bridges, Hornbostel cornice detail, rivets, ballast and sleepers."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUPPORTS, ("tower_qn", "tower_wi"), TOWER_SEP, roads_name="HELL GATE BRG")
    ax = fit.axis
    land_qn, land_wi = ax.p(-380.0, 0.0), ax.p(400.0, 0.0)
    ctx = (("water_dark", 0.35, 900.0, (0.0, 0.0)),
           ("ground_urban", GROUND, 240.0, (land_qn.x, land_qn.y)),
           ("ground_urban", GROUND, 240.0, (land_wi.x, land_wi.y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=90_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_hell_gate_bridge", fit.frame, view="astoria_park_reference",
                                ground_z=GROUND, target_z=70.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                aim=ax.p(0.0, 0.0, 70.0),
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="astoria_park", cam=ax.p(S_T_QN - 90.0, -230.0, GROUND + 2.0), target=ax.p(30.0, 0.0, 60.0),
                 fov_deg=60.0, context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=32.0),
            dict(view="elevation", cam=ax.p(0.0, -520.0, 30.0), target=ax.p(0.0, 0.0, 60.0), fov_deg=48.0,
                 context=ctx, sun_azimuth_deg=190.0, sun_elevation_deg=34.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
