"""Bow Bridge — Central Park, over the Lake between Cherry Hill and the Ramble.  Calvert Vaux with Jacob Wrey Mould,
1859-1862; cast by Janes, Kirtland & Co.  The second-oldest cast-iron bridge in the United States and the first of
Central Park's cast-iron bridges.  NYC Scenic Landmark (Central Park, LP-0851).

Dimensions used (source in brackets)
------------------------------------
* Span **60 ft = 18.29 m**, overall length **87 ft = 26.52 m**, width **14 ft = 4.27 m** [NYC Parks, Central Park
  Conservancy, Wikipedia "Bow Bridge"].  The deck rises in a shallow bow — the origin of the name — of about
  **1.5 m** camber over the span (*inferred* from photographs, +-0.3 m).
* The balustrade is **cast iron in eight decorative panels a side**, each with the interlaced circles-and-arrows
  motif; the model builds the panel rhythm and the two urn-topped newels at each end but **not** the cast pattern
  itself (stated).
* Two stone abutments of Manhattan schist; eight cast-iron beams under the deck.

Placement: the real OSM way ``580516390`` (``man_made=bridge``, name Bow Bridge, 27 x 41 m), NYC_TM centroid
(-1838, 8413).  The axis is the polygon's principal axis; the modelled 26.52 m length is the published figure, and
the OSM polygon's 27 m diagonal extent agrees with it.

Not modelled: the cast-iron balustrade's decorative pattern, the urn castings, the timber deck planking pattern, the
abutment stonework courses, and the Lake.
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import b_align as ba  # noqa: E402
import b_bridge_lib as bl  # noqa: E402
import b_common as bc  # noqa: E402
import nycsim_bpy as nb  # noqa: E402
from mathutils import Vector  # noqa: E402

ID = "b_bow_bridge"
TITLE = "Bow Bridge"

SPAN = 18.29            # 60 ft
LENGTH = 26.52          # 87 ft
WIDTH = 4.27            # 14 ft
CAMBER = 1.5
PANELS = 8
WAY = 580516390
WATER_Z = 20.9          # the Lake's surface, NAVD88 (inferred from the terrace's 22.9 m ground)
DECK_Z = WATER_Z + 2.3


def deck_z(s: float) -> float:
    u = max(-1.0, min(1.0, s / (LENGTH / 2)))
    return DECK_Z + CAMBER * (1.0 - u * u)


def build(lod: int = 0):
    ring = ba.osm_polygon_local(WAY, bc.LocalFrame(0.0, 0.0))
    if ring is None:
        raise RuntimeError("OSM way 580516390 (Bow Bridge) missing; run b_osm_extract.py")
    import numpy as np
    a = np.asarray(ring)
    c = a.mean(axis=0)
    _, _, vt = np.linalg.svd(a - c, full_matrices=False)
    d = vt[0]
    heading = math.degrees(math.atan2(d[0], d[1])) % 360.0
    frame = bc.local_frame((float(c[0]), float(c[1])), 0.0, heading)
    axis = bl.Axis(Vector((0.0, 0.0, 0.0)), Vector((float(d[0]), float(d[1]), 0.0)))
    objs: list = []
    ss = bl.samples(-LENGTH / 2, LENGTH / 2, 1.2)
    objs.append(bl.sweep("deck", axis, ss, bl.rect_section(WIDTH, 0.28, 0.0, 0.0), deck_z, "wood_deck"))
    objs.append(bl.sweep("beam", axis, ss, bl.rect_section(WIDTH - 0.5, 0.75, 0.0, -0.28), deck_z, "steel_green"))
    # the eight cast-iron beams under the deck follow the bow
    if lod == 0:
        beams = []
        for k in range(8):
            t = -WIDTH / 2 + (k + 0.5) * WIDTH / 8
            beams.append(bl.sweep(f"ironbeam{k}", axis, ss, bl.rect_section(0.16, 0.5, t, -0.3), deck_z, "steel_green"))
        objs.append(bc.join(beams, "cast_iron_beams"))
    # balustrades: eight panels a side plus urn newels
    for side in (-1, 1):
        parts = []
        for k in range(PANELS):
            s0 = -LENGTH / 2 + LENGTH * k / PANELS + 0.18
            s1 = -LENGTH / 2 + LENGTH * (k + 1) / PANELS - 0.18
            p0 = axis.p(s0, side * (WIDTH / 2 - 0.1), deck_z(s0))
            p1 = axis.p(s1, side * (WIDTH / 2 - 0.1), deck_z(s1))
            parts.append(bc.box_between(f"panel{side}_{k}", p0, p1, 0.09, 0.95, "steel_green"))
            parts.append(bc.box_between(f"rail{side}_{k}", p0 + Vector((0, 0, 1.0)), p1 + Vector((0, 0, 1.0)),
                                        0.14, 0.12, "steel_green"))
            post = axis.p(s0 - 0.18, side * (WIDTH / 2 - 0.1), deck_z(s0))
            parts.append(bc.box_between(f"post{side}_{k}", post, post + Vector((0, 0, 1.1)), 0.16, 0.16, "steel_green"))
        for s_end in (-LENGTH / 2, LENGTH / 2):
            p = axis.p(s_end, side * (WIDTH / 2 - 0.1), deck_z(s_end))
            parts.append(bc.box_between(f"newel{side}", p, p + Vector((0, 0, 1.35)), 0.34, 0.34, "steel_green"))
            parts.append(nb.cylinder(f"urn{side}{s_end:+.0f}", 0.26, 0.55, 10,
                                     (p.x, p.y, p.z + 1.35), material=bc.mat("steel_green")))
        objs.append(bc.join(parts, f"balustrade{side}"))
    # stone abutments
    for s_end in (-1, 1):
        ab = bc.box("abutment", (4.2, WIDTH + 3.2, DECK_Z + CAMBER * 0.2 - (WATER_Z - 2.5)),
                    (0, 0, WATER_Z - 2.5), "schist")
        bc.transform(ab, axis.matrix(s_end * (LENGTH / 2 + 1.4)))
        objs.append(ab)

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": CAMBER + 2.3, "name": TITLE,
        "span_m": SPAN, "length_m": LENGTH, "width_m": WIDTH, "camber_m": CAMBER, "balustrade_panels": PANELS,
        "lp_number": "LP-0851 (Central Park scenic landmark)",
        "height_source": "NYC Parks / Central Park Conservancy: 60 ft span, 87 ft long, 14 ft wide, cast iron, 1862",
        "sources_ids": ["osm_bbbike", "published_bow_bridge"],
        "fidelity_statement": (
            "Exact to published values: 26.52 m length, 18.29 m span, 4.27 m width, eight cast-iron beams, eight "
            "balustrade panels a side with urn-topped newels, stone abutments, on the real OSM footprint (way "
            "580516390). Inferred: the 1.5 m bow camber (+-0.3 m, from photographs), the Lake's 20.9 m NAVD88 "
            "surface and the 2.3 m deck clearance above it, beam and rail sections. Not modelled: the cast-iron "
            "balustrade's interlaced-circles pattern, the urn castings, the deck planking pattern, the abutment "
            "stone courses, the Lake."),
    }
    return objs, extras


def main() -> None:
    ctx = (("water_dark", WATER_Z, 220.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, budget_lod0=250_000, budget_lod1=30_000,
        renders=[
            dict(view="from_the_lake", cam=(0.0, -34.0, WATER_Z + 1.4), target=(0.0, 0.0, DECK_Z + 1.6),
                 fov_deg=52.0, context=ctx, sun_azimuth_deg=200.0, sun_elevation_deg=36.0),
            dict(view="deck", cam=(-19.0, 0.0, DECK_Z + 1.7), target=(19.0, 0.0, DECK_Z + 2.4), fov_deg=62.0,
                 context=ctx, sun_azimuth_deg=250.0, sun_elevation_deg=40.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
