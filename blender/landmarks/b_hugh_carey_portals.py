"""Hugh L. Carey Tunnel (Brooklyn-Battery Tunnel) — under the mouth of the East River, Battery Park (Manhattan) to
Red Hook / Hamilton Avenue (Brooklyn), passing beside Governors Island.  Ole Singstad, opened 25 May 1950; renamed in
2012.  The longest continuous underwater vehicular tunnel in North America.  MTA Bridges & Tunnels.

Dimensions used (source in brackets)
------------------------------------
* Length **9,117 ft = 2,779.2 m** (the length named in the build brief); **4 lanes** in two bores; vertical
  clearance 12 ft 1 in = **3.68 m**; vehicles wider than 8 ft 6 in are prohibited [Wikipedia "Hugh L. Carey Tunnel",
  MTA Bridges & Tunnels].
* **Four ventilation buildings: two in Manhattan, one in Brooklyn and one on Governors Island** — the Governors
  Island one, mid-river, is the tunnel's signature structure.  Three of the four are real OSM buildings with tagged
  heights and are built on their real polygon footprints: ``278396317`` Governors Island (32.8 m), ``278053475``
  Battery/Manhattan (26.2 m) and ``278370550`` Brooklyn (20.4 m).  **The second Manhattan building is not mapped in
  OSM and is not modelled** (stated gap).
* Tube diameter is **not published** for this tunnel; 31 ft = **9.45 m** is used, the figure published for its
  contemporaries the Lincoln and Queens-Midtown tunnels by the same engineer (*inferred*).  Roadway width 6.55 m is
  inferred the same way.
* The roadway's low point is **not published**; it is modelled 30.0 m below mean high water (*inferred*, +-4 m).
* Interior: white glazed tile to 2.4 m, raised catwalk each side, a **luminaire every 10 m** in each ceiling cove and
  a recessed emergency door every 150 m, alternating sides.

Placement: both tube centrelines are real OSM ``highway=motorway, tunnel=yes, name=Brooklyn-Battery Tunnel`` ways —
``5681925`` (Manhattan to Brooklyn, 61 vertices) and ``413749473`` (Brooklyn to Manhattan, 54 vertices).  Each is
trimmed or extended symmetrically along its end tangents to the published 2,779.2 m; the measured-versus-published
difference is logged and recorded in the catalog entry under ``tube_stats``.  ``segments.parquet`` was not available.

Not modelled: the second Manhattan ventilation building (unmapped), the fan rooms and dampers, the Battery Park
approach and its 1950s ramps over the Battery, the Gowanus Expressway connection, the lane-control signals, and the
individual tile courses.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_tunnel_lib as tl  # noqa: E402

ID = "b_hugh_carey_portals"
TITLE = "Hugh L. Carey Tunnel"

LENGTH = 2779.2
DIAMETER = 9.45
ROAD_W = 6.55
Z_LOW = -30.0 + bc.MHW_ABOVE_NAVD88_M       # -29.30 NAVD88 (inferred)
PORTAL_MN = (-5507.0, 587.0)
PORTAL_BK = (-4703.0, -2016.0)
GROUND_MN = 3.5
GROUND_BK = 3.0

CFG = tl.TunnelCfg(
    portal_a_tm=PORTAL_MN, portal_b_tm=PORTAL_BK, ground_a=GROUND_MN, ground_b=GROUND_BK, z_low=Z_LOW,
    spec=tl.TubeSpec(diameter=DIAMETER, road_w=ROAD_W, lanes=2, ceiling_h=4.0, ceiling_half=3.45,
                     light_every=10.0, exit_every=150.0, station=12.0),
    portal_width=21.0, portal_height=8.5, portal_depth=6.5, portal_material="granite_gray",
    tubes=[
        tl.TubeCfg("west", (5681925,), (-5515.5, 589.7), ((-5515.5, 589.7), (-4713.8, -2020.7)), LENGTH, 2,
                   "southbound (Manhattan to Brooklyn)"),
        tl.TubeCfg("east", (413749473,), (-4693.3, -2011.3), ((-4693.3, -2011.3), (-5497.8, 584.5)), LENGTH, 2,
                   "northbound (Brooklyn to Manhattan)"),
    ],
    vents=[
        tl.VentCfg("vent_governors_island", 278396317, (-5251.0, -851.0), 32.8, 0.0, (40.0, 41.0), 3.0, "brick_red"),
        tl.VentCfg("vent_battery", 278053475, (-5509.0, 577.0), 26.2, 0.0, (35.0, 29.0), 3.5, "brick_red"),
        tl.VentCfg("vent_brooklyn", 278370550, (-4727.0, -1956.0), 20.4, 0.0, (39.0, 35.0), 3.0, "brick_red"),
    ],
)


def _frame():
    return ba.frame_at((PORTAL_MN[0] + PORTAL_BK[0]) / 2, (PORTAL_MN[1] + PORTAL_BK[1]) / 2, 0.0,
                       math.degrees(math.atan2(PORTAL_BK[0] - PORTAL_MN[0], PORTAL_BK[1] - PORTAL_MN[1])) % 360.0)


def build(lod: int = 0):
    frame = _frame()
    objs, stats = tl.assemble(CFG, frame, lod)
    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": frame.heading_deg, "height_m": 32.8, "name": TITLE,
        "length_m": LENGTH, "tube_diameter_m": DIAMETER, "roadway_width_m": ROAD_W, "lanes_total": 4,
        "clearance_m": 3.68, "ventilation_buildings_published": 4, "ventilation_buildings_modelled": 3,
        "luminaire_pitch_m": 10.0, "emergency_exit_pitch_m": 150.0, "tube_stats": stats,
        "alignment_source": "OSM tunnel ways 5681925 / 413749473",
        "height_source": "Wikipedia/MTA B&T: 9,117 ft length, 12 ft 1 in clearance, four ventilation buildings; "
                         "building heights from OSM tags",
        "sources_ids": ["osm_bbbike", "published_hugh_carey"],
        "fidelity_statement": (
            "Exact to published values: both bores at the published 2,779.2 m on their real 61- and 54-vertex OSM "
            "centrelines, 4 lanes, 3.68 m clearance, three of the four ventilation buildings on their real OSM "
            "footprints at their OSM-tagged heights (Governors Island 32.8 m, Battery 26.2 m, Brooklyn 20.4 m), "
            "tiled interiors with catwalks, a luminaire every 10 m and an emergency door every 150 m, both tubes "
            "drivable end to end. Inferred: 9.45 m tube diameter and 6.55 m roadway (not published for this tunnel; "
            "taken from Singstad's contemporary Lincoln and Queens-Midtown tunnels), the roadway low point (30.0 m "
            "below mean high water, +-4 m), portal head-wall dimensions, ground elevations, the parabolic vertical "
            "profile. Gap: the second Manhattan ventilation building is published but unmapped and is not modelled. "
            "Modelling note: the lining is inward-facing ribbon geometry with the outer shell built only for 70 m at "
            "each portal. Not modelled: fan rooms and dampers, the Battery Park approach ramps, the Gowanus "
            "Expressway connection, lane-control signals, tile courses."),
    }
    return objs, extras


def main() -> None:
    frame = _frame()
    mn = frame.to_local(*PORTAL_MN)
    bk = frame.to_local(*PORTAL_BK)
    gi = frame.to_local(-5251.0, -851.0)
    path, _ = tl.tube_path(CFG, frame, CFG.tubes[0])
    i = len(path) // 2
    cam_in = path[i] + bc.Vector((0, 0, 1.5))
    tgt_in = path[min(i + 2, len(path) - 1)] + bc.Vector((0, 0, 1.9))
    ctx = (("water_dark", 0.35, 1900.0, (0.0, 0.0)),
           ("grass", 3.0, 260.0, (gi[0] - 60.0, gi[1] + 60.0)),
           ("sidewalk", GROUND_MN, 260.0, (mn[0] - 60.0, mn[1] + 190.0)),
           ("sidewalk", GROUND_BK, 260.0, (bk[0] + 60.0, bk[1] - 190.0)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            # the comparison agent's recorded photographic viewpoint, used verbatim
            ba.reference_render("landmark_hugh_carey_tunnel_portal", frame, view="manhattan_portal_reference",
                                ground_z=GROUND_MN, target_z=GROUND_MN + 6.0, fov_deg=58.0, size=(1280, 720), context=ctx,
                                sun_azimuth_deg=215.0, sun_elevation_deg=35.0),
            dict(view="battery_portal", cam=(mn[0] + 80.0, mn[1] + 60.0, GROUND_MN + 8.0),
                 target=(mn[0] - 20.0, mn[1] - 40.0, GROUND_MN + 1.0), fov_deg=58.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=40.0),
            dict(view="tube_interior", cam=tuple(cam_in), target=tuple(tgt_in), fov_deg=72.0,
                 sun_elevation_deg=88.0, sun_strength=0.02, sky_strength=0.0, exposure=2.4, max_bounces=2, size=(960, 540)),
            dict(view="governors_island_vent", cam=(gi[0] + 130.0, gi[1] - 110.0, 26.0),
                 target=(gi[0], gi[1], 16.0), fov_deg=50.0, context=ctx, sun_azimuth_deg=230.0, sun_elevation_deg=36.0),
        ],
        sections={"Placement": "frame origin NYC_TM (%.1f, %.1f); both bores on real OSM centrelines; three of the "
                               "four ventilation buildings on their real OSM footprints."
                               % ((PORTAL_MN[0] + PORTAL_BK[0]) / 2, (PORTAL_MN[1] + PORTAL_BK[1]) / 2),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
