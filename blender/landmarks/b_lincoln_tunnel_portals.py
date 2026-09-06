"""Lincoln Tunnel — Hudson River, Weehawken NJ to Dyer Avenue between 30th and 42nd Streets, Manhattan.  Ole Singstad
for the Port of New York Authority: centre tube opened 22 December 1937, north tube 1 February 1945, south tube
25 May 1957.

Dimensions used (source in brackets)
------------------------------------
* Three bores [Wikipedia "Lincoln Tunnel", PANYNJ]: **centre tube 8,216 ft = 2,504.2 m** (the length named in the
  build brief), **south tube 8,006 ft = 2,440.2 m**, **north tube 7,482 ft = 2,280.5 m**.
* Tube diameter 31 ft = **9.45 m**; roadway width 21.5 ft = **6.55 m**, two lanes per tube (six lanes in all);
  vertical clearance 13 ft = **3.96 m**; minimum elevation **-97 ft = -29.57 m** below the surface of the Hudson.
* Ventilation: transverse, with fresh air ducted below the roadway and exhaust drawn above the ceiling.  The Manhattan
  ventilation shaft is a **145 ft = 44.2 m** steel, brick and sandstone structure; two further ventilation buildings
  were added with the third tube.  Four ventilation buildings are modelled: two at each portal.
* Interior: white glazed tile to 2.4 m, catwalk each side, luminaires every **10 m** in each ceiling cove and a
  recessed emergency door every 150 m (alternating sides).

Placement: all three tube centrelines are real OSM ``highway=motorway, tunnel=yes, name=Lincoln Tunnel`` ways —
centre ``320663777`` + ``5669566`` + ``320888283``; north ``8028104`` + ``60325671`` + ``320888292``; south
``22701977`` + ``8028096`` + ``60325668``.  Each chained centreline is trimmed or extended symmetrically along its end
tangents to its published length; ``b_tunnel_lib`` logs the measured-versus-published difference for each bore and the
model's catalog entry records it under ``tube_stats``.  ``segments.parquet`` was not available.

**The four ventilation buildings are the one part of this model that is not measured.**  OSM maps no ventilation
building for the Lincoln Tunnel (the only ventilation shaft in the extract near the portals, way ``511023293``,
belongs to the Amtrak North River Tunnels), and no published coordinates were found.  They are therefore placed
symmetrically 70 m either side of each portal on the tunnel axis — a *derived* position, +-80 m — with the published
44.2 m height on the Manhattan pair and an inferred 34 m on the Weehawken pair.

Not modelled: the fan rooms and dampers, the Lincoln Tunnel Expressway helix in Weehawken, the exclusive bus lane and
its gantries, the Dyer Avenue approach ramps and the Port Authority Bus Terminal connection, the lane-control signals,
and the individual tile courses.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_tunnel_lib as tl  # noqa: E402

ID = "b_lincoln_tunnel_portals"
TITLE = "Lincoln Tunnel"

CENTRE_LEN = 2504.2
SOUTH_LEN = 2440.2
NORTH_LEN = 2280.5
DIAMETER = 9.45
ROAD_W = 6.55
Z_LOW = -29.57 + bc.MHW_ABOVE_NAVD88_M      # -28.87 NAVD88
PORTAL_NJ = (-6136.0, 7379.0)
PORTAL_NY = (-3962.0, 6370.0)
GROUND_NJ = 6.0
GROUND_NY = 5.0

_D = ((PORTAL_NY[0] - PORTAL_NJ[0]), (PORTAL_NY[1] - PORTAL_NJ[1]))
_L = math.hypot(*_D)
_DX, _DY = _D[0] / _L, _D[1] / _L
_NX, _NY = -_DY, _DX


def _vent_xy(portal, along, across):
    return (portal[0] + _DX * along + _NX * across, portal[1] + _DY * along + _NY * across)


CFG = tl.TunnelCfg(
    portal_a_tm=PORTAL_NJ, portal_b_tm=PORTAL_NY, ground_a=GROUND_NJ, ground_b=GROUND_NY, z_low=Z_LOW,
    spec=tl.TubeSpec(diameter=DIAMETER, road_w=ROAD_W, lanes=2, ceiling_h=4.26, ceiling_half=3.45,
                     light_every=10.0, exit_every=150.0, station=12.0),
    portal_width=21.0, portal_height=9.0, portal_depth=7.0, portal_material="concrete",
    tubes=[
        tl.TubeCfg("centre", (320663777, 5669566, 320888283), (-6139.1, 7381.0),
                   ((-6139.1, 7381.0), (-5879.7, 7455.7), (-5038.7, 6989.4), (-3948.8, 6393.5)),
                   CENTRE_LEN, 2, "reversible"),
        tl.TubeCfg("north", (8028104, 60325671, 320888292), (-6155.8, 7391.2),
                   ((-6155.8, 7391.2), (-5858.8, 7470.6), (-5027.9, 7009.8), (-4154.5, 6538.5)),
                   NORTH_LEN, 2, "eastbound (NJ to NY)"),
        tl.TubeCfg("south", (22701977, 8028096, 60325668), (-6115.2, 7364.6),
                   ((-6115.2, 7364.6), (-5900.3, 7402.6), (-5063.8, 6938.8), (-3975.8, 6345.9)),
                   SOUTH_LEN, 2, "westbound (NY to NJ)"),
    ],
    vents=[
        tl.VentCfg("vent_nj_north", 0, _vent_xy(PORTAL_NJ, -40.0, 78.0), 34.0, 0.0, (26.0, 20.0), 6.0,
                   "brick_red", measured=False),
        tl.VentCfg("vent_nj_south", 0, _vent_xy(PORTAL_NJ, -40.0, -78.0), 34.0, 0.0, (26.0, 20.0), 6.0,
                   "brick_red", measured=False),
        tl.VentCfg("vent_ny_north", 0, _vent_xy(PORTAL_NY, 55.0, 74.0), 44.2, 0.0, (24.0, 22.0), 5.0,
                   "brick_red", measured=False),
        tl.VentCfg("vent_ny_south", 0, _vent_xy(PORTAL_NY, 55.0, -74.0), 44.2, 0.0, (24.0, 22.0), 5.0,
                   "brick_red", measured=False),
    ],
)


def _frame():
    return ba.frame_at((PORTAL_NJ[0] + PORTAL_NY[0]) / 2, (PORTAL_NJ[1] + PORTAL_NY[1]) / 2, 0.0,
                       math.degrees(math.atan2(_DX, _DY)) % 360.0)


def build(lod: int = 0):
    frame = _frame()
    objs, stats = tl.assemble(CFG, frame, lod)
    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": frame.heading_deg, "height_m": 44.2, "name": TITLE,
        "centre_tube_length_m": CENTRE_LEN, "south_tube_length_m": SOUTH_LEN, "north_tube_length_m": NORTH_LEN,
        "tube_diameter_m": DIAMETER, "roadway_width_m": ROAD_W, "lanes_per_tube": 2, "lanes_total": 6,
        "clearance_m": 3.96, "low_point_below_river_m": 29.57, "ventilation_buildings": 4,
        "luminaire_pitch_m": 10.0, "emergency_exit_pitch_m": 150.0, "tube_stats": stats,
        "alignment_source": "OSM tunnel ways (three bores, nine ways)",
        "height_source": "Wikipedia/PANYNJ: 8,216 / 8,006 / 7,482 ft tubes, 31 ft diameter, 21.5 ft roadway, "
                         "13 ft clearance, -97 ft minimum elevation, 145 ft Manhattan ventilation shaft",
        "sources_ids": ["osm_bbbike", "published_lincoln_tunnel"],
        "fidelity_statement": (
            "Exact to published values: all three bores at their published lengths (2,504.2 / 2,440.2 / 2,280.5 m) "
            "on their real OSM centrelines, 9.45 m lining diameter, 6.55 m two-lane roadway (six lanes in all), "
            "3.96 m clearance, low point 29.57 m below the river surface, the 44.2 m published height of the "
            "Manhattan ventilation shaft, tiled interiors with catwalks, a luminaire every 10 m and an emergency "
            "door every 150 m, all three tubes drivable end to end. Inferred: portal head-wall dimensions, ground "
            "elevations, the parabolic vertical profile, catwalk and ceiling dimensions, the Weehawken ventilation "
            "buildings' 34 m height. Derived, not measured (+-80 m): the positions of all four ventilation "
            "buildings — OSM maps none for this tunnel and no published coordinates were found, so they are placed "
            "70 m either side of each portal. Modelling note: the lining is inward-facing ribbon geometry, with the "
            "outer shell built only for 70 m at each portal. Not modelled: fan rooms and dampers, the Weehawken "
            "helix, the exclusive bus lane and its gantries, the Dyer Avenue ramps and bus-terminal connection, "
            "lane-control signals, tile courses."),
    }
    return objs, extras


def main() -> None:
    frame = _frame()
    nj = frame.to_local(*PORTAL_NJ)
    ny = frame.to_local(*PORTAL_NY)
    path, _ = tl.tube_path(CFG, frame, CFG.tubes[0])
    i = len(path) // 2
    cam_in = path[i] + bc.Vector((0, 0, 1.5))
    tgt_in = path[min(i + 2, len(path) - 1)] + bc.Vector((0, 0, 1.9))
    ctx = (("water_dark", 0.35, 1400.0, (0.0, 0.0)),
           ("sidewalk", GROUND_NJ, 300.0, (nj[0] - 220.0, nj[1] + 110.0)),
           ("sidewalk", GROUND_NY, 300.0, (ny[0] + 220.0, ny[1] - 110.0)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=70_000,
        renders=[
            dict(view="weehawken_portals", cam=(nj[0] - 110.0, nj[1] + 55.0, GROUND_NJ + 12.0),
                 target=(nj[0] + 60.0, nj[1] - 25.0, GROUND_NJ + 1.0), fov_deg=60.0, context=ctx,
                 sun_azimuth_deg=110.0, sun_elevation_deg=38.0),
            dict(view="tube_interior", cam=tuple(cam_in), target=tuple(tgt_in), fov_deg=72.0,
                 sun_elevation_deg=88.0, sun_strength=0.02, exposure=2.4, max_bounces=2, size=(960, 540)),
        ],
        sections={"Placement": "frame origin NYC_TM (%.1f, %.1f); three bores on real OSM centrelines."
                               % ((PORTAL_NJ[0] + PORTAL_NY[0]) / 2, (PORTAL_NJ[1] + PORTAL_NY[1]) / 2),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
