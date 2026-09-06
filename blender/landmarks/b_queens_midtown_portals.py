"""Queens-Midtown Tunnel — East River, East 36th/37th Streets at Second Avenue (Manhattan) to Borden Avenue and
21st Street, Long Island City (Queens).  Ole Singstad for the New York City Tunnel Authority, opened 15 November 1940.
MTA Bridges & Tunnels.

Dimensions used (source in brackets)
------------------------------------
* **Northern tube 6,414 ft = 1,955.0 m** (the length named in the build brief), **southern tube 6,272 ft =
  1,911.7 m**; exterior tube diameter 31 ft = **9.45 m**; roadway width 21 ft = **6.40 m**, two lanes per tube
  (**4 lanes** in all); vertical clearance 12 ft 1 in = **3.68 m** [Wikipedia "Queens-Midtown Tunnel", MTA B&T].
* **Two ventilation buildings**, one on each side of the East River: the Manhattan one is octagonal, between 41st and
  42nd Streets at First Avenue; the Queens one is a rectangular tower in the middle of Borden Avenue between Second
  and Fifth Streets.  Both are real OSM buildings with tagged heights — ``265517923`` (Manhattan, 33.3 m) and
  ``280623192`` (Queens, 27.8 m) — and their real polygon footprints are used.
* Interior: white glazed tile to 2.4 m, raised catwalk each side, a **luminaire every 10 m** in each ceiling cove and
  a recessed emergency door every 150 m, alternating sides.
* The low point of the roadway is **not published**; it is modelled 27.0 m below mean high water (*inferred*, +-4 m),
  which is consistent with the tunnel's published 6,414 ft length, its portal elevations and a maximum grade of 4 %.

Placement: both tube centrelines are real OSM ``highway=motorway, tunnel=yes, name=Queens-Midtown Tunnel`` ways —
northern ``11878036`` + ``706015228``, southern ``813727586`` + ``658498546``.  Each chained centreline is trimmed or
extended symmetrically along its end tangents to its published length; the measured-versus-published difference for
each bore is logged and recorded in the catalog entry under ``tube_stats``.  ``segments.parquet`` was not available.

Not modelled: the fan rooms and dampers inside the two ventilation buildings, the octagonal Manhattan building's
faceting above the roof line, the Manhattan and Queens toll-plaza and approach ramps, the lane-control signals and
jet fans, and the individual tile courses.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_tunnel_lib as tl  # noqa: E402

ID = "b_queens_midtown_portals"
TITLE = "Queens-Midtown Tunnel"

NORTH_LEN = 1955.0
SOUTH_LEN = 1911.7
DIAMETER = 9.45
ROAD_W = 6.40
Z_LOW = -27.0 + bc.MHW_ABOVE_NAVD88_M       # -26.30 NAVD88 (inferred)
PORTAL_MN = (-1924.0, 5088.0)               # Manhattan (36th/37th Street at Second Avenue)
PORTAL_QN = (-344.0, 4610.0)                # Queens (Borden Avenue at 21st Street)
GROUND_MN = 4.0
GROUND_QN = 3.0

CFG = tl.TunnelCfg(
    portal_a_tm=PORTAL_MN, portal_b_tm=PORTAL_QN, ground_a=GROUND_MN, ground_b=GROUND_QN, z_low=Z_LOW,
    spec=tl.TubeSpec(diameter=DIAMETER, road_w=ROAD_W, lanes=2, ceiling_h=4.0, ceiling_half=3.45,
                     light_every=10.0, exit_every=150.0, station=12.0),
    portal_width=21.0, portal_height=8.5, portal_depth=6.5, portal_material="granite_gray",
    tubes=[
        tl.TubeCfg("north", (11878036, 706015228), (-344.4, 4616.4),
                   ((-344.4, 4616.4), (-1782.0, 5254.2), (-1953.0, 5105.6)), NORTH_LEN, 2, "westbound (Queens to Manhattan)"),
        tl.TubeCfg("south", (813727586, 658498546), (-1898.2, 5073.1),
                   ((-1898.2, 5073.1), (-1768.9, 5245.7), (-344.0, 4602.5)), SOUTH_LEN, 2, "eastbound (Manhattan to Queens)"),
    ],
    vents=[
        tl.VentCfg("vent_manhattan", 265517923, (-1620.0, 5331.0), 33.3, 0.0, (35.0, 43.0), 3.0, "brick_red"),
        tl.VentCfg("vent_queens", 280623192, (-638.0, 4655.0), 27.8, 0.0, (41.0, 40.0), 3.0, "brick_red"),
    ],
)


def _frame():
    return ba.frame_at((PORTAL_MN[0] + PORTAL_QN[0]) / 2, (PORTAL_MN[1] + PORTAL_QN[1]) / 2, 0.0,
                       math.degrees(math.atan2(PORTAL_QN[0] - PORTAL_MN[0], PORTAL_QN[1] - PORTAL_MN[1])) % 360.0)


def build(lod: int = 0):
    frame = _frame()
    objs, stats = tl.assemble(CFG, frame, lod)
    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": frame.heading_deg, "height_m": 33.3, "name": TITLE,
        "north_tube_length_m": NORTH_LEN, "south_tube_length_m": SOUTH_LEN, "tube_diameter_m": DIAMETER,
        "roadway_width_m": ROAD_W, "lanes_total": 4, "clearance_m": 3.68, "ventilation_buildings": 2,
        "luminaire_pitch_m": 10.0, "emergency_exit_pitch_m": 150.0, "tube_stats": stats,
        "alignment_source": "OSM tunnel ways 11878036+706015228 / 813727586+658498546",
        "height_source": "Wikipedia/MTA B&T: 6,414 ft north tube, 6,272 ft south tube, 31 ft diameter, 21 ft roadway, "
                         "12 ft 1 in clearance; ventilation building heights from OSM tags",
        "sources_ids": ["osm_bbbike", "published_queens_midtown"],
        "fidelity_statement": (
            "Exact to published values: both bores at their published lengths (1,955.0 m north, 1,911.7 m south) on "
            "their real OSM centrelines, 9.45 m tube diameter, 6.40 m two-lane roadway (4 lanes in all), 3.68 m "
            "clearance, both ventilation buildings on their real OSM footprints at their OSM-tagged heights "
            "(33.3 m Manhattan, 27.8 m Queens), tiled interiors with catwalks, a luminaire every 10 m and an "
            "emergency door every 150 m, both tubes drivable end to end. Inferred: the roadway low point (27.0 m "
            "below mean high water, +-4 m — not published), portal head-wall dimensions, ground elevations, the "
            "parabolic vertical profile, catwalk and ceiling dimensions. Modelling note: the lining is inward-facing "
            "ribbon geometry with the outer shell built only for 70 m at each portal. Not modelled: fan rooms and "
            "dampers, the octagonal Manhattan building's upper faceting, the toll plaza and approach ramps, "
            "lane-control signals and jet fans, tile courses."),
    }
    return objs, extras


def main() -> None:
    frame = _frame()
    mn = frame.to_local(*PORTAL_MN)
    qn = frame.to_local(*PORTAL_QN)
    v = frame.to_local(-1620.0, 5331.0)
    path, _ = tl.tube_path(CFG, frame, CFG.tubes[0])
    i = len(path) // 2
    cam_in = path[i] + bc.Vector((0, 0, 1.5))
    tgt_in = path[min(i + 2, len(path) - 1)] + bc.Vector((0, 0, 1.9))
    ctx = (("water_dark", 0.35, 1100.0, (0.0, 0.0)),
           ("ground_urban", GROUND_MN, 280.0, (mn[0] - 200.0, mn[1] + 90.0)),
           ("ground_urban", GROUND_QN, 280.0, (qn[0] + 200.0, qn[1] - 90.0)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_queens_midtown_tunnel_portal", frame, view="manhattan_portal_reference",
                                ground_z=GROUND_MN, target_z=GROUND_MN + 6.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="manhattan_portal", cam=(mn[0] - 80.0, mn[1] + 46.0, GROUND_MN + 7.0),
                 target=(mn[0] + 40.0, mn[1] - 14.0, GROUND_MN + 1.0), fov_deg=58.0, context=ctx,
                 sun_azimuth_deg=140.0, sun_elevation_deg=40.0),
            dict(view="tube_interior", cam=tuple(cam_in), target=tuple(tgt_in), fov_deg=72.0,
                 sun_elevation_deg=88.0, sun_strength=0.02, sky_strength=0.0, exposure=2.4, max_bounces=2, size=(960, 540)),
            dict(view="manhattan_ventilation_building", cam=(v[0] + 90.0, v[1] - 80.0, 26.0),
                 target=(v[0], v[1], 16.0), fov_deg=50.0, context=ctx, sun_azimuth_deg=220.0, sun_elevation_deg=36.0),
        ],
        sections={"Placement": "frame origin NYC_TM (%.1f, %.1f); both bores on real OSM centrelines; both "
                               "ventilation buildings on their real OSM footprints."
                               % ((PORTAL_MN[0] + PORTAL_QN[0]) / 2, (PORTAL_MN[1] + PORTAL_QN[1]) / 2),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
