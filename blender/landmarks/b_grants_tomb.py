"""General Grant National Memorial ("Grant's Tomb") — Riverside Drive at West 122nd Street, Morningside Heights.
John H. Duncan, dedicated 27 April 1897; the largest mausoleum in North America.  NRHP; a unit of the National Park
Service.

Dimensions used (source in brackets)
------------------------------------
* Height **150 ft = 45.72 m**; the granite mass is a **90 ft = 27.43 m square** podium carrying a Doric portico of
  **10 columns**, above which a colonnaded drum of **44 Ionic columns** supports a stepped conical dome modelled on
  the Mausoleum at Halicarnassus [NPS, NYC Landmarks Preservation Commission, Wikipedia "Grant's Tomb"].
* The real OSM footprint (way ``271922197``, ``building=yes, historic=memorial``) measures **35 x 35 m** and is
  tagged **height 46.9 m**; the real OTI footprint (BIN **1057391**) measures 1,256 m2 with a LiDAR height of
  **46.9 m** over ground **39.6 m NAVD88**.  The published 45.72 m is used for the finial height and the
  measured 46.9 m is recorded as the LiDAR check (2.6 % apart).
* The 8,000-ton granite structure is faced in Maine granite; the two sarcophagi of Ulysses and Julia Grant stand in
  an open crypt below the rotunda floor.

Placement: BIN 1057391 (LiDAR ground 39.6 m NAVD88), cross-checked against OSM way 271922197.  The building faces
**south**, towards the Riverside Drive plaza.

Not modelled: the crypt and its two sarcophagi, the rotunda interior and its mosaics, the allegorical figures over
the entrance, the bronze doors, the 1970s mosaic benches around the plaza, and the granite coursing.
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

ID = "b_grants_tomb"
TITLE = "General Grant National Memorial"
BINS = [1057391]

HEIGHT = 45.72          # 150 ft
PODIUM_SQ = 27.43       # 90 ft
PORTICO_COLS = 10
DRUM_COLS = 44
HEADING = 180.0         # the portico faces south


def build(lod: int = 0):
    fp = bc.load_footprint(BINS[0])
    frame = bc.local_frame(fp, fp.ground_z, HEADING)
    ring = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    objs: list = []
    z_pod = 0.0
    # ---- steps and the granite podium on the real footprint -------------------------------------------------------
    objs.append(bc.prism("steps", pk._offset_ring(ring, 7.5), z_pod - 2.2, z_pod, "granite_dark"))
    objs.append(bc.prism("podium", ring, z_pod, z_pod + 15.5, "granite_gray"))
    objs += pk.entablature("podium_ent", ring, z_pod + 15.5, "granite_gray", architrave=1.0, frieze=1.3, cornice=1.0)
    # ---- Doric portico of ten columns on the south face -----------------------------------------------------------
    a = math.radians(bc.heading_to_math_deg(HEADING))
    d = bc.Vector((math.cos(a), math.sin(a), 0.0))
    n = bc.Vector((-d.y, d.x, 0.0))
    cols = []
    for row, ds in ((0, 12.0), (1, 8.4)):
        for k in range(PORTICO_COLS // 2):
            t = -8.4 + k * 4.2
            p = d * ds + n * t
            cols += pk.column(f"portico{row}_{k}", (p.x, p.y, z_pod), 13.6, 1.05, "granite_gray",
                              order="doric", segments=12 if lod == 0 else 8, lod=lod)
    objs.append(bc.join(cols, "portico_columns"))
    ped = bc.box("portico_pediment", (5.0, 21.0, 3.4), (d.x * 10.2, d.y * 10.2, z_pod + 17.8), "granite_gray")
    objs.append(ped)
    # ---- drum with 44 Ionic columns, and the stepped conical dome --------------------------------------------------
    z_drum = z_pod + 18.8
    r_drum = 11.6
    objs.append(nb.cylinder("drum_core", r_drum - 1.7, 9.6, 32, (0, 0, z_drum), material=bc.mat("granite_gray")))
    dcols = []
    n_dc = DRUM_COLS if lod == 0 else 16
    for k in range(n_dc):
        ang = 2 * math.pi * k / n_dc
        dcols += pk.column(f"drum{k}", (r_drum * math.cos(ang), r_drum * math.sin(ang), z_drum), 9.6, 0.62,
                           "granite_gray", order="ionic", segments=8, lod=lod)
    objs.append(bc.join(dcols, "drum_colonnade"))
    objs.append(nb.cylinder("drum_cornice", r_drum + 1.1, 1.5, 32, (0, 0, z_drum + 9.6), material=bc.mat("granite_gray")))
    z_dome = z_drum + 11.1
    steps_n = 7
    for k in range(steps_n):
        u = k / steps_n
        objs.append(nb.cylinder(f"dome_step{k}", (r_drum + 0.4) * (1 - u * 0.86), (HEIGHT - 2.4 - z_dome) / steps_n,
                                32 if lod == 0 else 16, (0, 0, z_dome + (HEIGHT - 2.4 - z_dome) * u),
                                material=bc.mat("granite_gray")))
    objs.append(nb.cylinder("finial", 1.0, 2.4, 12, (0, 0, z_dome + (HEIGHT - 2.4 - z_dome)),
                            material=bc.mat("granite_gray")))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": HEADING, "height_m": HEIGHT, "name": TITLE,
        "podium_square_m": PODIUM_SQ, "portico_columns": PORTICO_COLS, "drum_columns": DRUM_COLS,
        "lidar_height_m": round(fp.height, 2), "footprint_area_m2": round(fp.geometry.area, 1),
        "height_source": "NPS/LPC: 150 ft high, 90 ft square granite podium, Doric portico of 10 columns, drum of "
                         "44 Ionic columns; LiDAR height 46.9 m (BIN 1057391) and OSM way 271922197 height 46.9 m",
        "sources_ids": ["building_footprints", "osm_bbbike", "published_grants_tomb"],
        "fidelity_statement": (
            "Exact to published values: 45.72 m to the finial, the granite podium on the real OTI footprint of BIN "
            "1057391, a Doric portico of 10 columns, a drum colonnade of 44 Ionic columns, and the stepped conical "
            "dome. Cross-check: LiDAR and OSM both give 46.9 m against the published 150 ft (45.72 m) — 2.6 % "
            "apart, the difference being the finial. Inferred: podium and drum heights, column diameters, step "
            "count of the dome, the 180 deg south heading. Not modelled: the crypt and the two sarcophagi, the "
            "rotunda interior and mosaics, the allegorical figures and bronze doors, the plaza mosaic benches, "
            "granite coursing."),
    }
    return objs, extras


def main() -> None:
    fp = bc.load_footprint(BINS[0])
    ctx = (("grass", -2.3, 260.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=50_000,
        renders=[
            dict(view="riverside_drive", cam=(6.0, -78.0, 1.7), target=(0.0, 0.0, 24.0), fov_deg=52.0, context=ctx,
                 sun_azimuth_deg=200.0, sun_elevation_deg=42.0),
            dict(view="three_quarter", cam=(-72.0, -66.0, 26.0), target=(0.0, 0.0, 26.0), fov_deg=46.0, context=ctx,
                 sun_azimuth_deg=230.0, sun_elevation_deg=38.0),
        ],
        sections={"Placement": "real OTI footprint BIN 1057391, ground %.2f m NAVD88, cross-checked against OSM way "
                               "271922197." % fp.ground_z,
                  "Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
