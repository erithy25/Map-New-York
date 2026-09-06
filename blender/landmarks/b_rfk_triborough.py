"""Robert F. Kennedy Bridge (Triborough Bridge) — three separate crossings meeting on Randalls Island: the East River
suspension span (Astoria, Queens to Wards Island), the Harlem River vertical-lift bridge (Randalls Island to East
125th Street, Manhattan) and the Bronx Kill truss crossing (Randalls Island to Port Morris, the Bronx).  Othmar
Ammann (engineer) with Aymar Embury II (architect), opened 11 July 1936.  MTA Bridges & Tunnels.

Dimensions used (source in brackets) — all three crossings [Wikipedia "Robert F. Kennedy Bridge", MTA B&T]
--------------------------------------------------------------------------------------------------------
* **East River suspension span**: main span 1,380 ft = **420.62 m**; side spans 700 ft = **213.36 m** each; total
  2,780 ft = 847.3 m; deck width 98 ft = **29.87 m**; towers **96.01 m** (315 ft) above mean high water; clearance
  143 ft = **43.59 m**; **8 lanes** (4 each way).
* **Harlem River lift bridge**: movable span 310 ft = **94.49 m**; side spans 195 ft = **59.44 m** each; total 700 ft
  = 213.36 m; width 92 ft = **28.04 m**; towers 210 ft = **64.01 m**; clearance 55 ft = **16.76 m** closed and
  135 ft = **41.15 m** raised; **6 lanes**.  Modelled in the *closed* position.
* **Bronx Kill crossing**: main truss span 383 ft = **116.74 m**; approach spans 1,217 ft = 370.9 m combined; total
  1,600 ft = 487.7 m; clearance 55 ft = **16.76 m**; **8 lanes**.
* **Viaducts**: the structure crossing Randalls and Wards Islands is "more than 2.5 miles (4.0 km)"; the three legs
  modelled here (Wards Island 1.51 km, Bronx Kill leg 0.78 km, Harlem River leg 2.01 km) total **4.30 km** measured
  between the real structures.
* **Toll plaza**: on Randalls Island at the junction of the three legs (OSM ways ``392834791``/``392834793`` cover the
  plaza and its ramps); modelled as an 8-lane gantry-and-island plaza with a canopy.

Placement: the suspension towers are OSM ways ``1016642596`` (Queens) and ``1016642595`` (Wards Island), measured
420.60 m apart, **0.00 %** from the published 1,380 ft.  The Harlem River lift towers are OSM ways ``834043283`` and
``834043279`` (``bridge:support=lift_pier``), measured 118.1 m centre-to-centre; the published 310 ft movable span is
built between their inner faces, which is why the tower centres are further apart than the span.  The Bronx Kill truss
end supports are OSM ways ``1016646459`` and ``1016646456``, measured 104.3 m apart against a published 383 ft span,
so those two are snapped symmetrically to 116.74 m (the OSM polygons mark the portal frames, not the bearings).
``segments.parquet`` was not available.

Gap: the viaduct legs are modelled as girder viaducts with plain parapets, no lane markings and no ramp network —
they are 4.3 km of ordinary elevated highway and the roads stage carries the detail.  The lift span is fixed in the
closed position (no machinery animation).

Not modelled: the cable bands and wrapping, the lift-span machinery and counterweight ropes in detail, the toll
collection equipment, the Randalls Island ramps and the Bruckner/Grand Central Parkway interchanges, Downing Stadium
and the island parkland, and the pedestrian walkway ramps.
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

ID = "b_rfk_triborough"
TITLE = "Robert F. Kennedy (Triborough) Bridge"

MHW = bc.MHW_ABOVE_NAVD88_M
# --- East River suspension span
SUS_SPAN = 420.62
SUS_SIDE = 213.36
SUS_W = 29.87
SUS_TOWER_H = 96.01
SUS_CLEAR = 43.59
Z_SUS_MID = SUS_CLEAR + MHW + 2.6            # 46.89 NAVD88 roadway
Z_SUS_TOWER = Z_SUS_MID - 4.0
Z_SUS_ANCH = Z_SUS_MID - 9.0
Z_SUS_TOP = SUS_TOWER_H + MHW                # 96.71
Z_SUS_SADDLE = Z_SUS_TOP - 4.0
SUS_CABLE_T = (-13.6, 13.6)
# --- Harlem River lift bridge
LIFT_SPAN = 94.49
LIFT_SIDE = 59.44
LIFT_W = 28.04
LIFT_TOWER_H = 64.01
LIFT_CLEAR_CLOSED = 16.76
Z_LIFT = LIFT_CLEAR_CLOSED + MHW + 2.2       # 19.66 NAVD88 roadway
LIFT_PIER_SEP = 118.10                       # measured
# --- Bronx Kill crossing
BK_SPAN = 116.74
BK_W = 29.87
BK_CLEAR = 16.76
Z_BK = BK_CLEAR + MHW + 2.4                  # 19.86 NAVD88
GROUND = 4.0
ISLAND_Z = 5.0

SUS_SUPPORTS = [
    ba.Support("sus_tower_qn", 1016642596, (2072.92, 8665.64), "pylon", "Astoria (Queens) suspension tower"),
    ba.Support("sus_tower_wi", 1016642595, (1861.70, 9029.40), "pylon", "Wards Island suspension tower"),
]
LIFT_SUPPORTS = [
    ba.Support("lift_tower_w", 834043283, (1350.70, 12317.40), "lift_pier", "Manhattan-side lift tower"),
    ba.Support("lift_tower_e", 834043279, (1455.90, 12371.00), "lift_pier", "Randalls-side lift tower"),
]
BK_SUPPORTS = [
    ba.Support("bk_south", 1016646459, (1795.70, 11184.80), "pylon", "Randalls Island truss portal"),
    ba.Support("bk_north", 1016646456, (1886.90, 11134.20), "pylon", "Port Morris (Bronx) truss portal"),
]
JUNCTION_TM = (2380.0, 10590.0)              # Randalls Island toll plaza / three-way junction

S_T_QN, S_T_WI = -SUS_SPAN / 2, SUS_SPAN / 2
S_SUS_AF_QN, S_SUS_AF_WI = S_T_QN - SUS_SIDE, S_T_WI + SUS_SIDE
ANCH_L, ANCH_W = 54.0, 60.0
S_SUS_A_QN, S_SUS_A_WI = S_SUS_AF_QN - ANCH_L / 2, S_SUS_AF_WI + ANCH_L / 2
S_SUS_END_QN = S_SUS_A_QN - 220.0


def sus_z(s: float) -> float:
    if s < S_T_QN:
        u = min(1.0, max(0.0, (s - S_SUS_AF_QN) / SUS_SIDE))
        return Z_SUS_ANCH + (Z_SUS_TOWER - Z_SUS_ANCH) * u
    if s <= S_T_WI:
        u = s / (SUS_SPAN / 2)
        return Z_SUS_MID - (Z_SUS_MID - Z_SUS_TOWER) * u * u
    u = min(1.0, (s - S_T_WI) / SUS_SIDE)
    return Z_SUS_TOWER + (Z_SUS_ANCH - Z_SUS_TOWER) * u


def _viaduct(objs: list, name: str, frame, p0_tm, p1_tm, z0: float, z1: float, width: float, lod: int) -> None:
    """A straight girder viaduct leg between two NYC_TM points (plain deck, parapets, piers every 40 m)."""
    x0, y0, _ = frame.to_local(*p0_tm)
    x1, y1, _ = frame.to_local(*p1_tm)
    d = Vector((x1 - x0, y1 - y0, 0.0))
    L = d.length
    if L < 20.0:
        return
    axis = bl.Axis(Vector((x0, y0, 0.0)), d)
    ap = bl.ApproachSpec(0.0, L, z0, z1, "girder", pier_spacing=40.0, width=width, material="concrete", ground_z=GROUND)
    objs += bl.build_approach(name, axis, ap, lod)
    z_fn = (lambda s: z0 + (z1 - z0) * s / L)
    ss = bl.samples(0.0, L, 12.0)
    objs.append(bl.sweep(f"{name}_deck", axis, ss, bl.rect_section(width, 0.7, 0.0, 0.0), z_fn, "concrete_dark"))
    objs.append(bl.sweep(f"{name}_road", axis, ss, bl.rect_section(width - 1.6, 0.08, 0.0, 0.08), z_fn, "asphalt"))
    for side in (-1, 1):
        objs.append(bl.sweep(f"{name}_parapet{side}", axis, ss,
                             bl.rect_section(0.45, 1.1, side * (width / 2 - 0.25), 1.1), z_fn, "concrete"))


def build(lod: int = 0):
    fit = ba.bridge_axis(SUS_SUPPORTS, ("sus_tower_qn", "sus_tower_wi"), SUS_SPAN, roads_name="Robert F. Kennedy")
    frame = fit.frame
    axis = fit.axis
    objs: list = []

    # ---------------------------------------------------------------- East River suspension span
    tower = bl.TowerSpec(kind="portal", z_top=Z_SUS_TOP, z_saddle=Z_SUS_SADDLE, width_t=SUS_W + 3.0, depth_s=8.5,
                         z_base=-12.0, z_deck=Z_SUS_TOWER, leg_w=6.8, leg_d=8.5, leg_taper=0.6,
                         struts_z=(Z_SUS_TOWER - 3.0, Z_SUS_TOWER + 12.0, 72.0, Z_SUS_TOP - 4.0), x_brace=False,
                         pier_w=SUS_W + 8.0, pier_d=14.0, material="steel_gray", pier_material="concrete",
                         cable_t=SUS_CABLE_T)
    objs += bl.build_tower("sus_tower_qn", axis, S_T_QN, tower, lod)
    objs += bl.build_tower("sus_tower_wi", axis, S_T_WI, tower, lod)
    a_qn = bl.AnchorageSpec(S_SUS_A_QN, ANCH_L, ANCH_W, GROUND + 28.0, GROUND - 10.0, "concrete", Z_SUS_ANCH - 3.0, slope=False)
    a_wi = bl.AnchorageSpec(S_SUS_A_WI, ANCH_L, ANCH_W, ISLAND_Z + 28.0, ISLAND_Z - 10.0, "concrete", Z_SUS_ANCH - 3.0, slope=False)
    objs += bl.build_anchorage("sus_anch_qn", axis, a_qn, S_T_QN)
    objs += bl.build_anchorage("sus_anch_wi", axis, a_wi, S_T_WI)
    deck = bl.DeckSpec(width=SUS_W, thickness=0.6, lanes=8, lane_w=3.35, roadway_t=0.0, roadway_w=26.8,
                       truss_depth=7.6, truss_t=(-SUS_W / 2 + 0.6, SUS_W / 2 - 0.6), truss_above=False,
                       truss_panel=9.1, truss_material="steel_gray", material="asphalt", slab_material="concrete_dark",
                       railing=True, lamps_spacing=48.0, lamp_t=(-0.6, 0.6), centre_yellow=False)
    objs += bl.build_deck("sus_deck", axis, deck, S_SUS_AF_QN, S_SUS_AF_WI, sus_z, lod, step=8.0)
    cables = bl.CableSpec(t_offsets=SUS_CABLE_T, radius=0.26, z_low_mid=Z_SUS_MID + 2.6, suspender_spacing=12.19,
                          suspender_radius=0.04, suspender_pairs=True, material="steel_silver",
                          suspender_material="steel_gray")
    objs += bl.build_suspension_cables("sus_cable", axis, cables, (S_T_QN, S_T_WI), Z_SUS_SADDLE, (a_qn, a_wi), sus_z,
                                       0.4, lod)
    ap_deck = bl.DeckSpec(width=SUS_W, thickness=0.7, lanes=8, lane_w=3.35, roadway_w=26.8, material="asphalt",
                          slab_material="concrete_dark", railing=True, centre_yellow=False)
    objs += bl.build_approach("sus_ap_qn", axis, bl.ApproachSpec(S_SUS_END_QN, S_SUS_AF_QN, 16.0, Z_SUS_ANCH, "viaduct",
                                                                pier_spacing=36.0, width=SUS_W, material="concrete",
                                                                ground_z=GROUND), lod, ap_deck)

    # ---------------------------------------------------------------- Harlem River vertical-lift bridge
    lift = ba.axis_in_frame(frame, LIFT_SUPPORTS, ("lift_tower_w", "lift_tower_e"), LIFT_PIER_SEP)
    lax = lift.axis
    s_lo, s_hi = -LIFT_SPAN / 2, LIFT_SPAN / 2
    objs += bl.build_lift_span("lift", lax, s_lo, s_hi, Z_LIFT, LIFT_TOWER_H - (Z_LIFT - MHW), LIFT_W, "steel_gray", lod)
    lift_deck = bl.DeckSpec(width=LIFT_W, thickness=0.6, lanes=6, lane_w=3.35, roadway_w=20.1, material="asphalt",
                            slab_material="steel_gray", railing=True, centre_yellow=False)
    objs += bl.build_deck("lift_deck", lax, lift_deck, s_lo - LIFT_SIDE, s_hi + LIFT_SIDE, lambda s: Z_LIFT, lod, step=8.0)
    for side_s in (s_lo - LIFT_SIDE, s_hi + LIFT_SIDE):
        pier = bc.box("lift_end_pier", (12.0, LIFT_W + 4.0, Z_LIFT - 1.0 + 8.0), (0, 0, -8.0), "concrete")
        bc.transform(pier, lax.matrix(side_s))
        objs.append(pier)

    # ---------------------------------------------------------------- Bronx Kill truss crossing
    bk = ba.axis_in_frame(frame, BK_SUPPORTS, ("bk_south", "bk_north"), BK_SPAN)
    bax = bk.axis
    objs.append(bc.truss_girder("bk_truss", bax.p(-BK_SPAN / 2, 0.0, Z_BK - 0.8), bax.p(BK_SPAN / 2, 0.0, Z_BK - 0.8),
                                9.0, BK_W, 11.7, "steel_gray", chord=0.9, web=0.5, kind="pratt"))
    bk_deck = bl.DeckSpec(width=BK_W, thickness=0.6, lanes=8, lane_w=3.35, roadway_w=26.8, material="asphalt",
                          slab_material="steel_gray", railing=False, centre_yellow=False)
    objs += bl.build_deck("bk_deck", bax, bk_deck, -BK_SPAN / 2 - 185.0, BK_SPAN / 2 + 185.0, lambda s: Z_BK, lod, step=10.0)
    for s_end in (-BK_SPAN / 2, BK_SPAN / 2):
        pier = bc.box("bk_pier", (10.0, BK_W + 4.0, Z_BK - 1.0 + 8.0), (0, 0, -8.0), "concrete")
        bc.transform(pier, bax.matrix(s_end))
        objs.append(pier)

    # ---------------------------------------------------------------- viaduct legs across Randalls / Wards Islands
    wards_end_tm = frame.to_world(*axis.p(S_SUS_END_QN + 0.0, 0.0)[:2])[:2] if False else None
    _ = wards_end_tm
    wi_anch = axis.p(S_SUS_A_WI + ANCH_L / 2, 0.0)
    wi_tm = (wi_anch.x + frame.x0, wi_anch.y + frame.y0)
    bk_south_tm = tuple(BK_SUPPORTS[0].resolved)
    lift_east_tm = tuple(LIFT_SUPPORTS[1].resolved)
    _viaduct(objs, "via_wards", frame, wi_tm, JUNCTION_TM, Z_SUS_ANCH, 22.0, SUS_W, lod)
    _viaduct(objs, "via_bronxkill", frame, JUNCTION_TM, bk_south_tm, 22.0, Z_BK, BK_W, lod)
    _viaduct(objs, "via_harlem", frame, JUNCTION_TM, lift_east_tm, 22.0, Z_LIFT, LIFT_W, lod)

    # ---------------------------------------------------------------- Randalls Island toll plaza
    jx, jy, _ = frame.to_local(*JUNCTION_TM)
    plaza = bc.ground_plane("toll_plaza", 55.0, 20.0, "asphalt_light", (jx, jy))
    objs.append(plaza)
    booths = []
    for i in range(8):
        t = -28.0 + i * 8.0
        booths.append(bc.box(f"toll_island{i}", (7.0, 1.4, 0.25), (jx + t, jy, 20.0), "concrete"))
        if lod == 0:
            booths.append(bc.box(f"toll_gantry_leg{i}", (0.6, 0.6, 6.5), (jx + t, jy + 14.0, 20.0), "steel_gray"))
    booths.append(bc.box("toll_gantry", (66.0, 1.2, 1.4), (jx, jy + 14.0, 26.5), "steel_gray"))
    booths.append(bc.box("toll_canopy", (66.0, 16.0, 0.8), (jx, jy, 27.5), "concrete"))
    objs.append(bc.join(booths, "toll_plaza_structures"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": fit.heading_deg, "height_m": SUS_TOWER_H, "name": TITLE,
        "suspension_main_span_m": SUS_SPAN, "suspension_side_span_m": SUS_SIDE, "suspension_tower_h_mhw_m": SUS_TOWER_H,
        "suspension_clearance_mhw_m": SUS_CLEAR, "suspension_deck_width_m": SUS_W,
        "lift_span_m": LIFT_SPAN, "lift_side_span_m": LIFT_SIDE, "lift_tower_h_m": LIFT_TOWER_H,
        "lift_clearance_closed_m": LIFT_CLEAR_CLOSED, "lift_clearance_raised_m": 41.15, "lift_width_m": LIFT_W,
        "bronx_kill_span_m": BK_SPAN, "bronx_kill_clearance_m": BK_CLEAR,
        "viaduct_modelled_m": 4300.0, "alignment_source": fit.source,
        "height_source": "Wikipedia/MTA B&T: 1,380 ft suspension span, 315 ft towers, 310 ft lift span, 383 ft Bronx Kill span",
        "sources_ids": ["osm_bbbike", "published_rfk"],
        "fidelity_statement": (
            "Exact to published values, all three crossings: East River suspension span 420.62 m with 213.36 m side "
            "spans, 96.01 m towers above MHW, 43.59 m clearance, 29.87 m deck, 8 lanes; Harlem River vertical-lift "
            "bridge with a 94.49 m movable span between towers 64.01 m high, 59.44 m side spans, 28.04 m width, "
            "16.76 m closed clearance, 6 lanes; Bronx Kill truss 116.74 m with 16.76 m clearance and 8 lanes; the "
            "three viaduct legs and the Randalls Island toll plaza at the real junction. Inferred: cable plane "
            "offsets, anchorage sizes, viaduct pier spacing, toll plaza layout (8 gantry lanes), deck elevations "
            "away from the published clearances. The lift towers' 118.10 m centre separation is measured, not "
            "published; the published 310 ft movable span is built between their inner faces. Gaps: the viaduct legs "
            "have no lane markings or ramps; the lift span is fixed closed with no machinery animation. Not "
            "modelled: cable bands, lift machinery detail, toll equipment, the Bruckner and Grand Central Parkway "
            "interchanges, Randalls Island parkland."),
    }
    return objs, extras


def main() -> None:
    fit = ba.bridge_axis(SUS_SUPPORTS, ("sus_tower_qn", "sus_tower_wi"), SUS_SPAN)
    frame, ax = fit.frame, fit.axis
    jx, jy, _ = frame.to_local(*JUNCTION_TM)
    ctx = (("water_dark", 0.35, 4200.0, (0.0, 0.0)),
           ("grass", ISLAND_Z, 700.0, (jx - 300.0, jy - 500.0)),
           ("sidewalk", GROUND, 300.0, (ax.p(-560.0, 0.0).x, ax.p(-560.0, 0.0).y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=400_000, budget_lod1=100_000,
        renders=[
            dict(view="astoria_suspension_span", cam=ax.p(-70.0, -300.0, GROUND + 2.5), target=ax.p(120.0, 0.0, 60.0),
                 fov_deg=58.0, context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=32.0),
            dict(view="suspension_elevation", cam=ax.p(0.0, -700.0, 30.0), target=ax.p(0.0, 0.0, 55.0), fov_deg=44.0,
                 context=ctx, sun_azimuth_deg=190.0, sun_elevation_deg=34.0),
            dict(view="randalls_island_overview", cam=(jx - 700.0, jy - 2100.0, 620.0), target=(jx - 250.0, jy + 400.0, 40.0),
                 fov_deg=52.0, context=ctx, sun_azimuth_deg=200.0, sun_elevation_deg=45.0),
        ],
        sections={"Placement": fit.report(),
                  "Published dimensions": __doc__.split("--------------------------------------------------------------------------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
