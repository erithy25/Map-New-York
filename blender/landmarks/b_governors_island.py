"""Governors Island — Castle Williams and Fort Jay, Upper New York Bay.  Both are National Historic Landmarks and
form the Governors Island National Monument (2001).

Dimensions used (source in brackets)
------------------------------------
* **Castle Williams** (Lt. Col. Jonathan Williams, 1807-1811): a circular casemated battery of red sandstone,
  **200 ft = 60.96 m in outside diameter**, its walls **40 ft = 12.19 m high** and **8 ft = 2.44 m thick**, with
  **three tiers of casemates** carrying **26 guns per tier** plus a barbette tier on the roof [NPS, HABS NY-6396,
  Wikipedia "Castle Williams"].  Its real OSM plan (way ``278396567``) measures **63 x 62 m** — 3 % over the
  published 200 ft, the difference being the modern parapet and the entrance sally-port block; the model uses the
  published 60.96 m diameter centred on the OSM polygon and states the difference.  The inner court is OSM way
  ``278396580`` (37 x 35 m).
* **Fort Jay** (1794, rebuilt 1806-1809): a **four-bastioned star fort** of earth faced in stone, with a dry ditch
  and a sandstone gate with the 1790s sculpted arms of the United States.  Its real OSM plan (way ``1388461669``,
  ``historic=fort``) spans **188 x 201 m**, which is the covered way; the scarp is modelled inside it.  Fort Jay
  Theatre inside the fort is OSM way ``278396529`` (43 x 47 m, tagged height 10.6 m).
* Ground level on the island is taken as **4.0 m NAVD88** (the LiDAR ground of the island's building footprints runs
  3.7-5.2 m).

Placement: both forts are built on their **real OSM plans**; nothing is placed by hand.

Not modelled: the casemate interiors and the gun carriages, the sally-port and its sculpted arms, Fort Jay's
barracks buildings and the officers' quarters inside the walls, the dry ditch's counterscarp masonry, the island's
other buildings (Nolan Park, Colonels Row, the Admiral's House), Hills park and the ferry landings.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_governors_island"
TITLE = "Governors Island: Castle Williams and Fort Jay"

CW_DIAMETER = 60.96     # 200 ft
CW_WALL_H = 12.19       # 40 ft
CW_WALL_T = 2.44        # 8 ft
CW_TIERS = 3
CW_GUNS_PER_TIER = 26
CW_WAY = 278396567
FJ_WAY = 1388461669
FJ_THEATRE_WAY = 278396529
FJ_WALL_H = 8.5         # inferred: the scarp above the ditch floor
FJ_DITCH = 4.0
GROUND = 4.0


def build(lod: int = 0):
    cw_ring = ba.osm_polygon_local(CW_WAY, bc.LocalFrame(0.0, 0.0))
    fj_ring = ba.osm_polygon_local(FJ_WAY, bc.LocalFrame(0.0, 0.0))
    if cw_ring is None or fj_ring is None:
        raise RuntimeError("Castle Williams (way 278396567) or Fort Jay (way 1388461669) missing from the OSM "
                           "extract; run b_osm_extract.py")
    cwx = sum(p[0] for p in cw_ring) / len(cw_ring)
    cwy = sum(p[1] for p in cw_ring) / len(cw_ring)
    fjx = sum(p[0] for p in fj_ring) / len(fj_ring)
    fjy = sum(p[1] for p in fj_ring) / len(fj_ring)
    ox, oy = (cwx + fjx) / 2, (cwy + fjy) / 2
    frame = bc.local_frame((ox, oy), GROUND, 0.0)
    objs: list = []

    # ---- Castle Williams: the circular casemated battery, on the published 200 ft diameter -----------------------
    c = Vector((cwx - ox, cwy - oy, 0.0))
    objs += pk.casemate_tower("castle_williams", c, CW_DIAMETER / 2, CW_WALL_H, CW_WALL_T, "sandstone_red",
                              tiers=CW_TIERS, ports_per_tier=CW_GUNS_PER_TIER, segments=44 if lod == 0 else 22,
                              lod=lod)
    # sally port on the landward (north) side
    objs.append(bc.box("cw_sallyport", (7.0, 9.0, 8.0), (c.x, c.y + CW_DIAMETER / 2 - 1.0, 0.0), "sandstone_red"))

    # ---- Fort Jay: the four-bastioned star, on its real OSM plan ---------------------------------------------------
    fj = [(x - ox, y - oy) for x, y in fj_ring]
    scarp = pk._offset_ring(fj, -14.0)
    objs.append(bc.prism("fj_glacis", fj, -0.5, 1.4, "grass"))
    objs.append(nb.extrude_polygon("fj_ditch", pk._offset_ring(fj, -8.0), -FJ_DITCH, 1.2,
                                   [list(reversed(scarp))], material=bc.mat("grass")))
    objs += pk.star_fort("fort_jay", scarp, -FJ_DITCH, FJ_WALL_H + FJ_DITCH, 5.0, "granite_gray", parapet_h=1.8,
                         lod=lod)
    # the gate on the south face and the theatre building inside
    objs.append(bc.box("fj_gate", (9.0, 5.0, 9.0), (sum(p[0] for p in scarp) / len(scarp),
                                                    min(p[1] for p in scarp) + 1.0, 0.0), "sandstone_red"))
    th = ba.osm_polygon_local(FJ_THEATRE_WAY, bc.LocalFrame(ox, oy))
    if th is not None:
        objs.append(bc.prism("fj_theatre", th, 0.0, 10.6, "brick_red"))
        objs.append(bc.prism("fj_theatre_roof", pk._offset_ring(th, 0.5), 10.6, 11.4, "granite_dark"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": 0.0, "height_m": CW_WALL_H, "name": TITLE,
        "castle_williams_diameter_m": CW_DIAMETER, "castle_williams_wall_h_m": CW_WALL_H,
        "castle_williams_wall_t_m": CW_WALL_T, "castle_williams_tiers": CW_TIERS,
        "castle_williams_guns_per_tier": CW_GUNS_PER_TIER, "fort_jay_bastions": 4,
        "height_source": "NPS / HABS NY-6396: Castle Williams 200 ft diameter, 40 ft walls, 8 ft thick, three tiers "
                         "of 26 guns; Fort Jay a four-bastioned star fort of 1806-09",
        "sources_ids": ["osm_bbbike", "published_governors_island"],
        "fidelity_statement": (
            "Exact to published values: Castle Williams at the published 60.96 m outside diameter with 12.19 m "
            "walls 2.44 m thick and three tiers of 26 gun ports, centred on its real OSM polygon (way 278396567); "
            "Fort Jay's four-bastioned star built on its real OSM plan (way 1388461669) with its glacis, dry ditch "
            "and scarp, and the Fort Jay Theatre on its real OSM footprint at its tagged 10.6 m. Stated "
            "difference: the OSM Castle Williams polygon measures 63 x 62 m, 3 % over the published 200 ft, so the "
            "published diameter is used and the polygon only fixes the centre. Inferred: Fort Jay's 8.5 m scarp and "
            "4.0 m ditch (no published figures found), the 14 m offset from the covered way to the scarp, the sally "
            "port and gate sizes, the 4.0 m NAVD88 ground. Not modelled: casemate interiors and gun carriages, the "
            "sculpted arms over the sally port, Fort Jay's barracks and officers' quarters, the counterscarp "
            "masonry, Nolan Park and Colonels Row, Hills park, the ferry landings."),
    }
    return objs, extras


def main() -> None:
    ctx = (("grass", -0.6, 500.0, (0.0, 0.0)), ("water_dark", 0.35, 2000.0, (0.0, 0.0)))
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            dict(view="castle_williams", cam=(-120.0, -170.0, 40.0), target=(-88.0, -68.0, 8.0), fov_deg=48.0,
                 context=ctx, sun_azimuth_deg=210.0, sun_elevation_deg=38.0),
            dict(view="fort_jay", cam=(190.0, -190.0, 90.0), target=(80.0, 60.0, 6.0), fov_deg=52.0, context=ctx,
                 sun_azimuth_deg=230.0, sun_elevation_deg=42.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
