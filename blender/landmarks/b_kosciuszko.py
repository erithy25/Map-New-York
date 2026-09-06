"""Kosciuszko Bridge — Newtown Creek, Brooklyn-Queens Expressway (I-278) between Greenpoint (Brooklyn) and Maspeth
(Queens).  Two parallel cable-stayed structures replacing the 1939 truss: the eastbound span opened 27 April 2017 and
the westbound span 29 August 2019 (the 1939 bridge was demolished 1 October 2017).  NYSDOT / Skanska-Kiewit-ECCO III.

Dimensions used (source in brackets)
------------------------------------
* **Cable-stayed**, longest span 624 ft = **190.20 m**; clearance below 90 ft = **27.43 m**; **9 lanes** in total
  (5 eastbound, 4 westbound) plus a bicycle and pedestrian path on the westbound span; **56 stay cables** in total
  [Wikipedia "Kosciuszko Bridge (New York City)", NYSDOT].
* 56 cables over two structures, each with a single pylon and stays fanning in both directions from two planes
  (one per deck edge): 2 structures x 2 directions x 2 planes x **7 stays** = 56.
* Pylon height **91.4 m** (300 ft) above the deck — *inferred* from NYSDOT's description of the main tower; the
  infobox gives no figure.  Stated as an inference.
* Deck widths: eastbound (5 lanes + shoulders) **21.5 m**, westbound (4 lanes + shoulders + the 6.1 m shared-use
  path) **24.5 m** — *inferred* from the lane counts.
* The 1939 truss bridge it replaced (6,021 ft long, 300 ft main span, 125 ft clearance, 6 lanes) is **not** modelled;
  it no longer exists.

Placement: from the two OSM bridge-deck polygons ``371931262`` and ``673031781`` (the eastbound and westbound
structures), whose centroids are 30.68 m apart across a common axis on a heading of **42.1 deg**, and the two OSM
BQE deck ways ``718450323``/``658193988`` which give that axis over 952 m.  There is **no OSM support way for the
pylons**: each pylon is placed 55 m south-west of the deck centroid so that the published 190.20 m main span crosses
Newtown Creek — that along-bridge position is *inferred*, +-30 m.  ``segments.parquet`` was not available.

Not modelled: the stay anchor boxes and dampers, the LED architectural lighting, the shared-use path's ramps and
overlook, the BQE interchange ramps at Meeker Avenue and the Long Island Expressway, and the noise walls.
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

ID = "b_kosciuszko"
TITLE = "Kosciuszko Bridge"

MAIN_SPAN = 190.20
BACK_SPAN = 150.0            # inferred
CLEARANCE = 27.43
PYLON_H = 91.4               # inferred (NYSDOT "300 ft")
N_STAYS = 7                  # per direction per plane -> 2 x 2 x 2 x 7 = 56 cables in total
DECK_W_EB = 21.5
DECK_W_WB = 24.5
DECK_SEP = 30.68             # measured between the two OSM deck-polygon centroids
S_PYLON = -55.0              # inferred (+-30 m)
MHW = bc.MHW_ABOVE_NAVD88_M
Z_DECK = CLEARANCE + MHW + 3.0        # 31.13 NAVD88
GROUND = 3.0
CENTRE_TM = (1730.0, 3070.0)          # midpoint of the two OSM deck ways
HEADING = 42.1
LENGTH = 900.0


def _axis(t_off: float) -> bl.Axis:
    a = math.radians(HEADING)
    d = Vector((math.sin(a), math.cos(a), 0.0))
    n = Vector((-d.y, d.x, 0.0))
    return bl.Axis(n * t_off, d)


def deck_z(s: float) -> float:
    """Crest over the creek, falling 4 % towards each end of the modelled length."""
    s0, s1 = S_PYLON - BACK_SPAN - 260.0, S_PYLON + MAIN_SPAN + 260.0
    crest = S_PYLON + MAIN_SPAN / 2
    if s <= s0:
        return Z_DECK - 14.0
    if s >= s1:
        return Z_DECK - 14.0
    u = abs(s - crest) / max(crest - s0, s1 - crest)
    return Z_DECK - 14.0 * u * u


def build(lod: int = 0):
    frame = ba.frame_at(CENTRE_TM[0], CENTRE_TM[1], 0.0, HEADING)
    objs: list = []
    s0 = S_PYLON - BACK_SPAN - 260.0
    s1 = S_PYLON + MAIN_SPAN + 260.0
    for name, t_off, width, lanes in (("eb", -DECK_SEP / 2, DECK_W_EB, 5), ("wb", DECK_SEP / 2, DECK_W_WB, 4)):
        axis = _axis(t_off)
        objs += bl.build_cable_stayed(f"{name}_cs", axis, S_PYLON, deck_z(S_PYLON), PYLON_H, width, BACK_SPAN,
                                      MAIN_SPAN, N_STAYS, "steel_white", "steel_white", lod, tower_style="inverted_y")
        walkways = ((width / 2 - 3.3, 6.1, 0.16),) if name == "wb" else ()
        deck = bl.DeckSpec(width=width, thickness=1.6, lanes=lanes, lane_w=3.66,
                           roadway_t=-1.8 if name == "wb" else 0.0,
                           roadway_w=lanes * 3.66 + 2.4, walkways=walkways, truss_depth=0.0, material="asphalt",
                           slab_material="concrete_dark", railing=True, lamps_spacing=45.0,
                           lamp_t=(-width / 2 + 0.8, width / 2 - 0.8), centre_yellow=False)
        objs += bl.build_deck(f"{name}_deck", axis, deck, s0, s1, deck_z, lod, step=8.0)
        ap = dict(kind="viaduct", pier_spacing=42.0, width=width, material="concrete", ground_z=GROUND)
        objs += bl.build_approach(f"{name}_ap0", axis, bl.ApproachSpec(s0, S_PYLON - BACK_SPAN, deck_z(s0),
                                                                      deck_z(S_PYLON - BACK_SPAN), **ap), lod)
        objs += bl.build_approach(f"{name}_ap1", axis, bl.ApproachSpec(S_PYLON + MAIN_SPAN, s1,
                                                                      deck_z(S_PYLON + MAIN_SPAN), deck_z(s1), **ap), lod)

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": HEADING, "height_m": PYLON_H + Z_DECK, "name": TITLE,
        "main_span_m": MAIN_SPAN, "clearance_m": CLEARANCE, "pylon_height_above_deck_m": PYLON_H,
        "stay_cables_total": 56, "lanes_total": 9, "deck_width_eb_m": DECK_W_EB, "deck_width_wb_m": DECK_W_WB,
        "deck_separation_m": DECK_SEP, "total_modelled_length_m": s1 - s0,
        "alignment_source": "OSM deck polygons 371931262 / 673031781 and BQE deck ways 718450323 / 658193988",
        "height_source": "Wikipedia/NYSDOT: 624 ft longest span, 90 ft clearance, 56 stay cables, 9 lanes",
        "sources_ids": ["osm_bbbike", "published_kosciuszko"],
        "fidelity_statement": (
            "Exact to published values: 190.20 m main span, 27.43 m clearance, 9 lanes over two parallel structures "
            "(5 eastbound / 4 westbound), 56 stay cables in total (2 structures x 2 directions x 2 planes x 7), the "
            "shared-use path on the westbound span, and the 30.68 m measured separation of the two decks. Inferred "
            "and stated: 91.4 m pylon height above the deck (NYSDOT's '300 ft'; the infobox gives none), the "
            "pylons' along-bridge position (+-30 m, no OSM support way exists), 150 m back span, 21.5 m / 24.5 m "
            "deck widths, approach grades. The demolished 1939 truss bridge is deliberately absent. Not modelled: "
            "stay anchor boxes and dampers, LED architectural lighting, path ramps and overlook, BQE interchange "
            "ramps, noise walls."),
    }
    return objs, extras


def main() -> None:
    ax = _axis(0.0)
    frame = ba.frame_at(CENTRE_TM[0], CENTRE_TM[1], 0.0, HEADING)   # the same frame build() uses
    ctx = (("water_dark", 0.35, 160.0, (ax.p(S_PYLON + MAIN_SPAN / 2, 0.0).x, ax.p(S_PYLON + MAIN_SPAN / 2, 0.0).y)),
           ("ground_urban", GROUND, 380.0, (ax.p(-430.0, 0.0).x, ax.p(-430.0, 0.0).y)),
           ("ground_urban", GROUND, 380.0, (ax.p(430.0, 0.0).x, ax.p(430.0, 0.0).y)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_kosciuszko_bridge", frame, view="kosciuszko_reference",
                                ground_z=GROUND, target_z=60.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                aim=ax.p(S_PYLON, 0.0, 55.0),
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="newtown_creek", cam=ax.p(S_PYLON + 140.0, -260.0, GROUND + 2.0),
                 target=ax.p(S_PYLON, 0.0, 60.0), fov_deg=58.0, context=ctx, sun_azimuth_deg=240.0,
                 sun_elevation_deg=32.0),
            dict(view="roadway", cam=ax.p(S_PYLON - 220.0, -DECK_SEP / 2, deck_z(S_PYLON - 220.0) + 2.2),
                 target=ax.p(S_PYLON + 60.0, -DECK_SEP / 2, Z_DECK + 40.0), fov_deg=60.0, context=ctx,
                 sun_azimuth_deg=120.0, sun_elevation_deg=44.0),
        ],
        sections={"Placement": "origin NYC_TM (%.1f, %.1f), heading %.2f deg from the two OSM BQE deck ways; the two "
                               "structures are offset +-%.2f m across the axis (measured between the OSM deck-polygon "
                               "centroids). The pylons' along-bridge position is inferred, +-30 m."
                               % (CENTRE_TM[0], CENTRE_TM[1], HEADING, DECK_SEP / 2),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
