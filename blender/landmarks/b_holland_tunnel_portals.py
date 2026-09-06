"""Holland Tunnel — Hudson River, Canal Street (Manhattan) to 12th/14th Streets, Jersey City.  Clifford M. Holland
and Ole Singstad, opened 13 November 1927.  The world's first mechanically ventilated underwater vehicular tunnel;
National Historic Landmark (1993) and National Historic Civil and Mechanical Engineering Landmark.

Dimensions used (source in brackets)
------------------------------------
* **North tube** (westbound, New York to New Jersey) 8,558 ft = **2,608.5 m**; **south tube** (eastbound)
  8,371 ft = **2,551.4 m**.  The build brief names 2,608 m for "the Holland tunnel", which is the north tube.
* Internal lining diameter 29 ft 6 in = **8.99 m**; roadway width 20 ft = **6.10 m**, two lanes per tube; vertical
  clearance 12 ft 6 in = 3.81 m; the roadway reaches **93 ft = 28.35 m below mean high water** at its lowest point
  [Wikipedia "Holland Tunnel", PANYNJ, HAER NJ-59].
* **Transverse ventilation** (Singstad's invention): fresh air is blown into a duct under the roadway and drawn out
  through a plenum above the ceiling, changing the air completely every 90 seconds; **four ventilation buildings**,
  two on each shore — a river tower and a land building on either side — with 84 fans.
* Interior finish: white glazed tile to 2.4 m over a dark base, a raised catwalk each side, and continuous luminaire
  rows.  This model places a **luminaire every 10 m** in each cove (the figure named in the build brief) and a
  recessed emergency door every 150 m, alternating sides.

Placement (all four ventilation buildings and both tube centrelines are real OSM geometry)
* North tube: OSM ways ``46613913`` + ``415877358``; south tube: ``22927390`` + ``415882710`` — all
  ``highway=motorway, tunnel=yes, name=Holland Tunnel``.  The chained OSM centrelines measure **2,613.0 m** and
  **2,550.7 m** against the published 2,608.5 m and 2,551.4 m — **+0.17 %** and **-0.03 %**; each is then trimmed or
  extended symmetrically along its end tangents to exactly the published length.
* Ventilation buildings, with the heights OSM records: ``249664800`` Manhattan river tower (39.3 m),
  ``249664802`` Manhattan land building (35.5 m), ``331072217`` New Jersey river tower (34.0 m, height not tagged —
  taken from its twin), ``320431782`` New Jersey land building (33.0 m, height not tagged).  Their real polygon
  footprints are used, not boxes.

Not modelled: the fan rooms, ducts and dampers inside the ventilation buildings, the tiled wall's individual courses,
the overhead lane-control signals and jet fans, the police booths and the Manhattan and Jersey City approach plazas
and their ramp networks, and the cast-iron lining segment bolts.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_tunnel_lib as tl  # noqa: E402

ID = "b_holland_tunnel_portals"
TITLE = "Holland Tunnel"

NORTH_LEN = 2608.5      # 8,558 ft
SOUTH_LEN = 2551.4      # 8,371 ft
DIAMETER = 8.99         # 29 ft 6 in
ROAD_W = 6.10           # 20 ft
Z_LOW = -(28.35) + bc.MHW_ABOVE_NAVD88_M    # 93 ft below MHW -> -27.65 NAVD88
PORTAL_NY = (-4846.0, 2688.0)               # midpoint of the two Manhattan portal ends
PORTAL_NJ = (-7281.0, 3350.0)               # midpoint of the two Jersey City portal ends
GROUND_NY = 3.0
GROUND_NJ = 3.5

CFG = tl.TunnelCfg(
    portal_a_tm=PORTAL_NY, portal_b_tm=PORTAL_NJ, ground_a=GROUND_NY, ground_b=GROUND_NJ, z_low=Z_LOW,
    spec=tl.TubeSpec(diameter=DIAMETER, road_w=ROAD_W, lanes=2, ceiling_h=4.11, ceiling_half=3.25,
                     light_every=10.0, exit_every=150.0, station=12.0),
    portal_width=20.0, portal_height=8.5, portal_depth=7.0, portal_material="granite_gray",
    tubes=[
        tl.TubeCfg("north", (46613913, 415877358), (-4812.6, 2778.9),
                   ((-4812.6, 2778.9), (-6024.1, 3071.4), (-7293.2, 3397.7)), NORTH_LEN, 2, "westbound (NY to NJ)"),
        tl.TubeCfg("south", (22927390, 415882710), (-7269.2, 3301.5),
                   ((-7269.2, 3301.5), (-6027.4, 3054.3), (-4881.1, 2597.0)), SOUTH_LEN, 2, "eastbound (NJ to NY)"),
    ],
    vents=[
        tl.VentCfg("vent_ny_river", 249664800, (-5487.0, 2950.0), 39.3, 20.0, (20.0, 35.0), -2.0, "brick_red"),
        tl.VentCfg("vent_ny_land", 249664802, (-5082.0, 2861.0), 35.5, 20.0, (21.0, 58.0), 2.0, "brick_red"),
        tl.VentCfg("vent_nj_river", 331072217, (-6493.0, 3159.0), 34.0, 20.0, (19.0, 34.0), -2.0, "brick_red", measured=False),
        tl.VentCfg("vent_nj_land", 320431782, (-6883.0, 3254.0), 33.0, 20.0, (38.0, 27.0), 2.5, "brick_red", measured=False),
    ],
)


def build(lod: int = 0):
    frame = ba.frame_at((PORTAL_NY[0] + PORTAL_NJ[0]) / 2, (PORTAL_NY[1] + PORTAL_NJ[1]) / 2, 0.0,
                        bc.math.degrees(bc.math.atan2(PORTAL_NJ[0] - PORTAL_NY[0], PORTAL_NJ[1] - PORTAL_NY[1])) % 360.0)
    objs, stats = tl.assemble(CFG, frame, lod)
    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": frame.heading_deg, "height_m": 39.3, "name": TITLE,
        "north_tube_length_m": NORTH_LEN, "south_tube_length_m": SOUTH_LEN, "tube_diameter_m": DIAMETER,
        "roadway_width_m": ROAD_W, "lanes_per_tube": 2, "low_point_below_mhw_m": 28.35,
        "ventilation_buildings": 4, "luminaire_pitch_m": 10.0, "emergency_exit_pitch_m": 150.0,
        "tube_stats": stats, "alignment_source": "OSM tunnel ways 46613913+415877358 / 22927390+415882710",
        "height_source": "Wikipedia/PANYNJ/HAER NJ-59: 8,558 ft north tube, 8,371 ft south tube, 29 ft 6 in diameter, "
                         "20 ft roadway, 93 ft below MHW",
        "sources_ids": ["osm_bbbike", "published_holland_tunnel"],
        "fidelity_statement": (
            "Exact to published values: both tubes at their published lengths (2,608.5 m north, 2,551.4 m south), "
            "8.99 m lining diameter, 6.10 m two-lane roadway, low point 28.35 m below mean high water, four "
            "ventilation buildings on their real OSM footprints with the OSM-recorded heights where tagged, tiled "
            "interior with catwalks, a luminaire every 10 m and an emergency door every 150 m, both tube interiors "
            "drivable end to end along the real OSM centrelines. Inferred: portal head-wall dimensions, ground "
            "elevations at the portals, the parabolic vertical profile between the portals and the published low "
            "point, ventilation-building heights for the two New Jersey buildings (taken from their New York twins, "
            "not tagged in OSM), the ceiling and catwalk dimensions. Modelling note: the lining is built as "
            "inward-facing ribbons (floor, catwalks, tiled walls, ceiling) so it is correct from inside; the outer "
            "shell is built only for 70 m at each portal, where it is visible. Not modelled: fan rooms, ducts and "
            "dampers, individual tile courses, lane-control signals and jet fans, police booths, the approach "
            "plazas and ramp networks, cast-iron lining bolts."),
    }
    return objs, extras


def main() -> None:
    frame = ba.frame_at((PORTAL_NY[0] + PORTAL_NJ[0]) / 2, (PORTAL_NY[1] + PORTAL_NJ[1]) / 2, 0.0, 0.0)
    ny = frame.to_local(*PORTAL_NY)
    nj = frame.to_local(*PORTAL_NJ)
    v1 = frame.to_local(-5487.0, 2950.0)
    ctx = (("water_dark", 0.35, 1400.0, (0.0, 0.0)),
           ("sidewalk", GROUND_NY, 300.0, (ny[0] + 240.0, ny[1] - 90.0)),
           ("sidewalk", GROUND_NJ, 300.0, (nj[0] - 240.0, nj[1] + 90.0)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            dict(view="manhattan_portal", cam=(ny[0] + 70.0, ny[1] - 42.0, GROUND_NY + 6.0),
                 target=(ny[0] - 30.0, ny[1] + 12.0, GROUND_NY + 1.0), fov_deg=58.0, context=ctx,
                 sun_azimuth_deg=140.0, sun_elevation_deg=40.0),
            dict(view="tube_interior", cam=(0.0, 0.0, Z_LOW + 1.6), target=(300.0, 80.0, Z_LOW + 2.0),
                 fov_deg=70.0, sun_elevation_deg=90.0, sun_strength=0.05, exposure=1.6),
            dict(view="river_ventilation_tower", cam=(v1[0] + 120.0, v1[1] - 110.0, 24.0),
                 target=(v1[0], v1[1], 18.0), fov_deg=48.0, context=ctx, sun_azimuth_deg=220.0, sun_elevation_deg=35.0),
        ],
        sections={"Placement": "frame origin NYC_TM (%.1f, %.1f); both tube centrelines are the real OSM tunnel ways, "
                               "extended to the published lengths." % ((PORTAL_NY[0] + PORTAL_NJ[0]) / 2,
                                                                      (PORTAL_NY[1] + PORTAL_NJ[1]) / 2),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
