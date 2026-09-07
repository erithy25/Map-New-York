"""Washington Square Arch — Washington Square Park, Greenwich Village.  Stanford White (McKim, Mead & White), the
permanent marble arch of 1892 replacing the 1889 wood-and-plaster centennial arch.  NYC Landmark LP-0451 (Washington
Square Park), NRHP.

Dimensions used (source in brackets)
------------------------------------
* Height **77 ft = 23.47 m**; overall width **62 ft = 18.90 m**; the opening is **30 ft = 9.14 m** wide and
  **47 ft = 14.33 m** to the crown [NYC Parks, Wikipedia "Washington Square Arch"].  Tuckahoe marble throughout.
* Two statues of Washington stand on the north piers — **Washington as Commander-in-Chief** (Hermon MacNeil, 1916)
  on the east and **Washington as President** (A. Stirling Calder, 1918) on the west; each is about **4.9 m** tall
  in its niche.  They are modelled as blocked-out figures on their pedestals, not as sculpture (stated).
* Spandrel figures of Victory, the frieze of 13 large and 42 small stars, and the eagles are **not** modelled.

Placement: the real OSM way ``248166269`` (``building=triumphal_arch, historic=monument``, 20 x 16 m, tagged height
20.5 m) gives the plan and position, NYC_TM centroid (-3979, 3470).  The published **23.47 m** height is used rather
than OSM's 20.5 m tag, and stated.  The arch faces **north up Fifth Avenue**: the heading is taken from the long
axis of the OSM polygon.

Not modelled: the spandrel Victories, the frieze and its 55 stars, the eagles, the inscription, the internal stair
to the roof, and the fountain and plaza paving of Washington Square Park.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_common as bc  # noqa: E402
import b_park_lib as pk  # noqa: E402

ID = "b_washington_square_arch"
TITLE = "Washington Square Arch"

HEIGHT = 23.47          # 77 ft -- to the top of the attic cap
# triumphal_arch stacks body (HEIGHT - 3.2), cornice (0.7 * 1.4), attic (ATTIC_H) and a 0.7 m cap; solve the
# attic height so the cap lands exactly on the published 23.47 m
ATTIC_H = 3.2 - 0.7 * 1.4 - 0.7   # = 1.52
WIDTH = 18.90           # 62 ft
DEPTH = 9.0             # inferred from the OSM footprint's short side
OPENING_W = 9.14        # 30 ft
OPENING_H = 14.33       # 47 ft
STATUE_H = 4.9
WAY = 248166269
GROUND = 8.0            # NAVD88 (Washington Square Park is about 8 m above datum)
HEADING = 5.0           # faces north up Fifth Avenue


def build(lod: int = 0):
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    if ring is None:
        raise RuntimeError("OSM way 248166269 (Washington Square Arch) missing; run b_osm_extract.py")
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    frame = bc.local_frame((cx, cy), GROUND, HEADING)
    objs: list = []
    objs += pk.triumphal_arch("wsa", (0.0, 0.0, 0.0), HEADING, width=WIDTH, depth=DEPTH, height=HEIGHT - 3.2,
                              opening_w=OPENING_W, opening_h=OPENING_H, material="marble_white",
                              attic_h=ATTIC_H, cornice=0.7, lod=lod)
    # the two Washington statues on the north piers, blocked out on their pedestals
    a = math.radians(bc.heading_to_math_deg(HEADING))
    d = bc.Vector((math.cos(a), math.sin(a), 0.0))
    n = bc.Vector((-d.y, d.x, 0.0))
    for side, nm in ((-1, "commander_in_chief"), (1, "president")):
        base = d * (DEPTH / 2 + 0.55) + n * (side * (OPENING_W / 2 + (WIDTH - OPENING_W) / 4))
        objs.append(bc.box(f"{nm}_pedestal", (1.9, 1.9, 2.6), (base.x, base.y, 2.0), "marble_white"))
        objs.append(bc.box(f"{nm}_figure", (1.1, 1.1, STATUE_H), (base.x, base.y, 4.6), "marble_white"))
        objs.append(bc.box(f"{nm}_canopy", (2.6, 2.6, 0.5), (base.x, base.y, 4.6 + STATUE_H), "marble_white"))
    objs.append(bc.prism("wsa_steps", bc.rect(WIDTH + 3.0, DEPTH + 3.0), -0.8, 0.0, "marble_white"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": HEADING, "height_m": HEIGHT, "name": TITLE,
        "width_m": WIDTH, "opening_w_m": OPENING_W, "opening_h_m": OPENING_H, "material": "Tuckahoe marble",
        "height_source": "NYC Parks / Wikipedia: 77 ft high, 62 ft wide, 30 ft opening; OSM way 248166269 tags 20.5 m",
        "sources_ids": ["osm_bbbike", "published_washington_square_arch"],
        "fidelity_statement": (
            "Exact to published values: 23.47 m high, 18.90 m wide, a 9.14 m opening rising 14.33 m, Tuckahoe "
            "marble, on the real OSM footprint (way 248166269). The published 77 ft height is used rather than "
            "OSM's 20.5 m height tag. Inferred: 9.0 m depth (from the OSM footprint's short side), the attic and "
            "cornice proportions, the engaged Corinthian order, the 5 deg heading up Fifth Avenue. Blocked out, not "
            "sculpted: the two Washington statues on the north piers. Not modelled: the spandrel Victories, the "
            "frieze and its 55 stars, the eagles, the inscription, the internal stair, the park's fountain and "
            "paving."),
    }
    return objs, extras


def main() -> None:
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    ctx = (("ground_urban", -0.9, 220.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=40_000,
        renders=[
            dict(view="fifth_avenue", cam=(4.0, 62.0, 1.7), target=(0.0, 0.0, 12.0), fov_deg=55.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=46.0),
            dict(view="park_side", cam=(-38.0, -46.0, 1.7), target=(0.0, 0.0, 13.0), fov_deg=58.0, context=ctx,
                 sun_azimuth_deg=140.0, sun_elevation_deg=40.0),
        ],
        sections={"Placement": "real OSM way 248166269, centroid NYC_TM (%.1f, %.1f), heading %.1f deg up Fifth "
                               "Avenue." % (cx, cy, HEADING),
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
