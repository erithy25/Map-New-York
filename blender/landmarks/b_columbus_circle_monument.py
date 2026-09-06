"""Columbus Circle — the Christopher Columbus Monument at the centre of the circle, with the Deutsche Bank Center
(the former Time Warner Center) twin towers on its west side.  Manhattan, at the south-west corner of Central Park.

Dimensions used (source in brackets)
------------------------------------
* **Columbus Monument** (Gaetano Russo, unveiled 13 October 1892, the 400th anniversary of the landfall): a
  **70 ft = 21.34 m** granite rostral column carrying a **14 ft = 4.27 m** marble figure of Columbus, giving an
  overall **76 ft = 23.16 m** from the plaza; the shaft is decorated with three bronze **prows of ships** (rostra)
  and the pedestal carries a bronze relief of the Nina, Pinta and Santa Maria and a winged genius.  The point from
  which all official distances to New York City are measured [NYC Parks, Wikipedia "Columbus Monument
  (Manhattan)"].
* **Columbus Circle** itself is the real OSM way ``109269254`` (``tourism=attraction``), **65 x 65 m**; the 2005
  reconstruction laid out the fountain rings and benches around the monument.
* **Deutsche Bank Center** (David Childs / SOM, opened 2004 as the Time Warner Center): **twin towers of 750 ft =
  228.60 m**, 55 storeys, on a curved podium that follows the circle; the real OTI footprint (BIN **1026318**,
  23,629 m2, LiDAR roof **217.9 m** over ground 25.6 m NAVD88) and the real OSM polygon (way ``167923911``, tagged
  height 45 m for the podium) are both used — the podium on the footprint, the two towers as 44 x 44 m shafts
  (*inferred* plan) rising to the published 228.60 m.
  The 10.7 m difference between the published 750 ft and the LiDAR 217.9 m is the towers' glass crowns, which the
  LiDAR return misses; the published figure is used and the difference stated.

Placement: the monument on OSM way 109269254's centroid, the Deutsche Bank Center on OTI BIN 1026318.

Not modelled: Russo's Columbus figure and the pedestal reliefs (blocked out), the rostra beyond three bronze prow
blocks, the 2005 fountain jets and their basins, the Maine Monument at the north-west of the circle (a separate
memorial), the Deutsche Bank Center's atrium and its curtain-wall mullions, and the subway entrances.
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

ID = "b_columbus_circle_monument"
TITLE = "Columbus Circle Monument and Deutsche Bank Center"
BINS = [1026318]

COLUMN_H = 21.34        # 70 ft
FIGURE_H = 4.27         # 14 ft
TOTAL_H = 23.16         # 76 ft from the plaza (the figure overlaps the capital)
CIRCLE_WAY = 109269254
DBC_TOWER_H = 228.60    # 750 ft
DBC_PODIUM_H = 45.0     # OSM tag
DBC_TOWER_PLAN = 44.0   # inferred
GROUND = 25.6           # LiDAR ground of BIN 1026318, NAVD88


def build(lod: int = 0):
    ring_c = ba.osm_polygon_local(CIRCLE_WAY, bc.LocalFrame(0.0, 0.0))
    if ring_c is None:
        raise RuntimeError("OSM way 109269254 (Columbus Circle) missing; run b_osm_extract.py")
    cx = sum(p[0] for p in ring_c) / len(ring_c)
    cy = sum(p[1] for p in ring_c) / len(ring_c)
    frame = bc.local_frame((cx, cy), GROUND, 0.0)
    objs: list = []

    # ---- the circle plaza and its fountain rings -------------------------------------------------------------------
    objs.append(bc.prism("circle_plaza", bc.regular_polygon(48, 32.5), -0.6, 0.0, "sidewalk"))
    for i, r in enumerate((8.4, 12.6)):
        objs.append(bc.prism(f"fountain_ring{i}", bc.regular_polygon(40, r), 0.0, 0.7, "granite_gray"))
        objs.append(bc.prism(f"fountain_water{i}", bc.regular_polygon(40, r - 0.55), 0.0, 0.45, "water"))

    # ---- the Columbus Monument -------------------------------------------------------------------------------------
    objs.append(bc.prism("monument_steps", bc.regular_polygon(8, 5.6), 0.0, 1.1, "granite_gray"))
    objs.append(bc.prism("monument_pedestal", bc.rect(4.4, 4.4), 1.1, 6.4, "granite_gray"))
    objs.append(bc.prism("pedestal_cornice", bc.rect(5.2, 5.2), 6.4, 7.1, "granite_gray"))
    objs.append(bc.box("pedestal_relief", (4.7, 4.7, 2.4), (0, 0, 2.6), "bronze_green", anchor="center"))
    z_col = 7.1
    shaft_h = COLUMN_H - (z_col - 1.1) - 1.9
    objs += pk.column("rostral_column", (0, 0, z_col), shaft_h + 1.9, 1.35, "granite_gray", order="doric",
                      segments=16 if lod == 0 else 10, entasis=0.03, lod=lod)
    if lod == 0:
        prows = []
        for k in range(3):
            a = 2 * math.pi * k / 3
            z = z_col + shaft_h * (0.24 + 0.24 * k)
            p = Vector((2.05 * math.cos(a), 2.05 * math.sin(a), z))
            prows.append(bc.box(f"rostrum{k}", (2.6, 1.0, 1.1), (p.x, p.y, p.z), "bronze_green", anchor="center"))
        objs.append(bc.join(prows, "bronze_rostra"))
    z_fig = 1.1 + COLUMN_H
    objs.append(bc.box("columbus_figure", (1.15, 1.15, FIGURE_H), (0, 0, z_fig - FIGURE_H + TOTAL_H - COLUMN_H - 1.1),
                       "marble_white"))

    # ---- Deutsche Bank Center: podium on the real footprint, twin towers to the published 750 ft -------------------
    fp = bc.load_footprint(BINS[0])
    ring_b = [(x - frame.x0, y - frame.y0) for x, y in fp.ring]
    objs.append(bc.prism("dbc_podium", ring_b, -6.0, DBC_PODIUM_H, "glass_dark"))
    objs.append(bc.prism("dbc_podium_cap", pk._offset_ring(ring_b, -1.2), DBC_PODIUM_H, DBC_PODIUM_H + 1.6,
                         "steel_gray"))
    bx = sum(p[0] for p in ring_b) / len(ring_b)
    by = sum(p[1] for p in ring_b) / len(ring_b)
    # the two towers straddle the podium's long axis, set back from the circle
    import numpy as np
    a = np.asarray(ring_b)
    c = a.mean(axis=0)
    _, _, vt = np.linalg.svd(a - c, full_matrices=False)
    lg = vt[0]
    for k, s in enumerate((-1, 1)):
        tx = bx + float(lg[0]) * s * 42.0
        ty = by + float(lg[1]) * s * 42.0
        t_ring = bc.rect(DBC_TOWER_PLAN, DBC_TOWER_PLAN, tx, ty)
        objs.append(bc.prism(f"dbc_tower{k}", t_ring, DBC_PODIUM_H, DBC_TOWER_H, "glass_dark"))
        objs.append(bc.prism(f"dbc_tower{k}_crown", pk._offset_ring(t_ring, -2.6), DBC_TOWER_H, DBC_TOWER_H + 6.0,
                             "glass_clear"))
        if lod == 0:
            bands = []
            for j in range(1, int((DBC_TOWER_H - DBC_PODIUM_H) / 4.05)):
                z = DBC_PODIUM_H + j * 4.05
                bands.append(bc.prism(f"dbc{k}_b{j}", pk._offset_ring(t_ring, 0.1), z - 0.5, z, "steel_gray"))
            objs.append(bc.join(bands, f"dbc_tower{k}_spandrels"))

    extras = {
        "origin_tm": frame.origin_tm, "heading_deg": 0.0, "height_m": DBC_TOWER_H, "name": TITLE,
        "monument_total_m": TOTAL_H, "column_m": COLUMN_H, "figure_m": FIGURE_H, "rostra": 3,
        "deutsche_bank_center_m": DBC_TOWER_H, "deutsche_bank_center_lidar_m": round(fp.height, 2),
        "deutsche_bank_center_podium_m": DBC_PODIUM_H, "towers": 2,
        "height_source": "NYC Parks: 70 ft column, 14 ft Columbus figure, 76 ft overall; SOM/CTBUH: Deutsche Bank "
                         "Center twin towers 750 ft; LiDAR roof 217.9 m (BIN 1026318); OSM way 167923911 podium 45 m",
        "sources_ids": ["osm_bbbike", "building_footprints", "published_columbus_circle"],
        "fidelity_statement": (
            "Exact to published values: the 21.34 m rostral column with three bronze rostra and a 4.27 m Columbus "
            "figure, 23.16 m overall, on the real OSM Columbus Circle polygon (way 109269254); the Deutsche Bank "
            "Center's podium on the real OTI footprint of BIN 1026318 at the OSM-tagged 45 m, and twin towers to "
            "the published 750 ft (228.60 m). Blocked out, not sculpted: the Columbus figure and the pedestal "
            "reliefs. Inferred: the twin towers' 44 m square plan and their 42 m offsets along the podium's long "
            "axis, the fountain ring radii, the pedestal proportions, 4.05 m storeys. Stated difference: the LiDAR "
            "roof of 217.9 m is 10.7 m below the published 750 ft because the glass crowns give no return; the "
            "published height is used. Not modelled: the rostra beyond three bronze blocks, the 2005 fountain jets, "
            "the Maine Monument, the atrium and curtain-wall mullions, the subway entrances."),
    }
    return objs, extras


def main() -> None:
    ctx = (("sidewalk", -0.7, 600.0, (0.0, 0.0)),)
    ba.run_landmark(
        ID, TITLE, build, bins=BINS, budget_lod0=250_000, budget_lod1=60_000,
        renders=[
            dict(view="circle", cam=(66.0, -34.0, 1.8), target=(0.0, 0.0, 14.0), fov_deg=62.0, context=ctx,
                 sun_azimuth_deg=150.0, sun_elevation_deg=44.0),
            dict(view="monument_and_towers", cam=(150.0, -120.0, 60.0), target=(-40.0, 10.0, 100.0), fov_deg=48.0,
                 context=ctx, sun_azimuth_deg=120.0, sun_elevation_deg=38.0),
        ],
        sections={"Published dimensions": __doc__.split("------------------------------------\n")[1].split("\nPlacement:")[0].strip(),
                  "Placement": __doc__.split("Placement:")[1].split("\nNot modelled:")[0].strip(),
                  "Not modelled": __doc__.split("Not modelled:")[1].strip()},
    )


if __name__ == "__main__":
    main()
