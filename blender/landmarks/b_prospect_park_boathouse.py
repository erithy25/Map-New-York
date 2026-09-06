"""Prospect Park Boathouse (the Audubon Center at the Boathouse) — on the Lullwater of Prospect Park, Brooklyn.
Helmle & Huberty, 1905, modelled on Jacopo Sansovino's Libreria Sansoviniana on the Piazzetta in Venice; saved from
demolition in 1964 and restored in 1971 and 1998-2002.  NYC Landmark LP-0596, NRHP.

Dimensions used (source in brackets)
------------------------------------
* A **Beaux-Arts loggia of white glazed terracotta over a limestone base**, two storeys, with a **round-arched
  arcade of six bays** on the Lullwater front separated by paired Corinthian columns, a full entablature with a
  carved frieze, and a **balustraded roof terrace** [LPC designation report LP-0596, NYC Parks].
* The real OTI footprint (BIN **3347249**, "Audubon Center at the Boathouse") measures **663 m2** with a LiDAR
  height of **11.4 m** over ground **20.4 m NAVD88**; the Lullwater's water surface is taken as **18.6 m NAVD88**
  (*inferred*, +-0.6 m).  **No published overall dimensions were found** beyond the designation report's
  description, so the bay rhythm (six arches), the storey heights and the terracotta detail proportions are all
  *inferred from photographs and the footprint*, and stated.

Placement: the real OTI footprint of BIN 3347249, principal axis from its minimum rotated rectangle (the arcade
faces the Lullwater).

Not modelled: the carved terracotta frieze, the cartouches and the lion masks, the interior (the Audubon Center's
exhibits), the boat landing and its steps down to the Lullwater, the Lullwater Bridge, and the surrounding planting.
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

ID = "b_prospect_park_boathouse"
TITLE = "Prospect Park Boathouse (Audubon Center)"
BINS = [3347249]

BAYS = 6
WATER_Z = 18.6
BASE_H = 1.6
ARCADE_H = 6.4
ENT_H = 2.3
BAL_H = 1.25


def build(lod: int = 0):
    fp = bc.load_footprint(BINS[0])
    heading = bc.footprint_heading(fp)
    frame = bc.local_frame(fp, fp.ground_z, heading)
    ring = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    body_h = fp.height
    objs: list = []
    objs.append(bc.prism("terrace_platform", pk._offset_ring(ring, 3.4), WATER_Z - fp.ground_z - 1.2, 0.0, "limestone"))
    objs.append(bc.prism("base", ring, -1.2, BASE_H, "limestone"))
    objs.append(bc.prism("body", pk._offset_ring(ring, -0.3), BASE_H, BASE_H + ARCADE_H, "marble_white"))
    objs += pk.entablature("entablature", pk._offset_ring(ring, 0.25), BASE_H + ARCADE_H, "marble_white",
                           architrave=0.7, frieze=0.95, cornice=0.65, projection=0.7)
    z_roof = BASE_H + ARCADE_H + ENT_H
    objs.append(bc.prism("roof", pk._offset_ring(ring, -0.6), z_roof, z_roof + 0.4, "granite_dark"))
    objs += pk.balustrade("roof_balustrade", pk._offset_ring(ring, 0.3), z_roof, BAL_H, "marble_white",
                          spacing=0.6, lod=lod)

    # ---- the six-bay arcade on the Lullwater front ------------------------------------------------------------------
    a = math.radians(bc.heading_to_math_deg(heading))
    d = Vector((math.cos(a), math.sin(a), 0.0))
    n = Vector((-d.y, d.x, 0.0))
    xs = [p[0] * d.x + p[1] * d.y for p in ring]
    ys = [p[0] * n.x + p[1] * n.y for p in ring]
    L = max(xs) - min(xs)
    W = max(ys) - min(ys)
    front = min(ys)
    arch_w = L / BAYS * 0.62
    arches = []
    for k in range(BAYS):
        u = min(xs) + L * (k + 0.5) / BAYS
        p = d * u + n * (front - 0.15)
        prof = bc.round_arch(arch_w, ARCADE_H * 0.86, 0.0, 0.0)
        ob = bc.profile_extrude(f"arch{k}", prof, 0.9, "glass_clear", plane="xz")
        bc.transform(ob, bc.rot_z(bc.heading_to_math_deg(heading) - 90.0))
        bc.transform(ob, bc.Matrix.Translation(Vector((p.x, p.y, BASE_H))))
        arches.append(ob)
        if lod == 0:
            for s in (-1, 1):
                q = d * (u + s * (L / BAYS) * 0.42) + n * (front - 0.7)
                arches += pk.column(f"col{k}{s}", (q.x, q.y, BASE_H), ARCADE_H, 0.42, "marble_white",
                                    order="corinthian", segments=10, lod=lod)
    objs.append(bc.join(arches, "lullwater_arcade"))
    _ = W, body_h, nb

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": heading, "height_m": z_roof + BAL_H, "name": TITLE,
        "lp_number": "LP-0596", "arcade_bays": BAYS, "lidar_height_m": round(fp.height, 2),
        "footprint_area_m2": round(fp.geometry.area, 1), "water_level_m": WATER_Z,
        "height_source": "LPC LP-0596 / NYC Parks: a two-storey white glazed terracotta loggia after Sansovino's "
                         "Venetian library; LiDAR height 11.4 m over ground 20.4 m NAVD88 (BIN 3347249)",
        "sources_ids": ["building_footprints", "published_prospect_park_boathouse"],
        "fidelity_statement": (
            "Exact: the real OTI footprint of BIN 3347249 (663 m2) on its LiDAR ground of 20.4 m NAVD88, at its "
            "LiDAR height of 11.4 m; white glazed terracotta over a limestone base, a six-bay round-arched arcade "
            "with paired Corinthian columns, a full entablature and a balustraded roof terrace, as described in the "
            "LPC designation report. Inferred and stated: no published overall dimensions were found, so the bay "
            "rhythm's proportions, the 1.6 m base / 6.4 m arcade / 2.3 m entablature split, the arch width and the "
            "18.6 m NAVD88 Lullwater surface (+-0.6 m) all come from the footprint and photographs. Not modelled: "
            "the carved frieze, cartouches and lion masks, the interior, the boat landing and steps, the Lullwater "
            "Bridge, the planting."),
    }
    return objs, extras


def main() -> None:
    ctx = (("grass", -1.3, 200.0, (0.0, 0.0)), ("water_dark", WATER_Z - 20.4, 300.0, (0.0, -70.0)))
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=40_000,
        renders=[
            dict(view="from_the_lullwater", cam=(0.0, -48.0, -0.6), target=(0.0, 0.0, 7.0), fov_deg=56.0,
                 context=ctx, sun_azimuth_deg=200.0, sun_elevation_deg=44.0),
            dict(view="three_quarter", cam=(38.0, -40.0, 9.0), target=(0.0, 0.0, 7.0), fov_deg=54.0, context=ctx,
                 sun_azimuth_deg=240.0, sun_elevation_deg=38.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
