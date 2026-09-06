# Verrazzano-Narrows Bridge

Script: `blender/landmarks/b_verrazzano_narrows.py` · agent B · generated 2026-09-06 13:14 UTC

## Placement

axis heading 67.10 deg (compass, +s), origin NYC_TM (-8077.59, -10396.60); alignment source: osm bridge:support ways + published span
measured span between tower_si and tower_bk: 1298.68 m vs published 1298.40 m (+0.02 %); towers snapped symmetrically to the published value

| support | kind | NYC_TM x | NYC_TM y | s (m) | t (m) | source |
|---|---|---|---|---|---|---|
| tower_si | pylon | -8675.7 | -10649.3 | -649.2 | +0.0 | osm_way/1016642058 |
| tower_bk | pylon | -7479.4 | -10143.9 | +649.2 | +0.0 | osm_way/1016642060 |
| anchorage_si | anchorage | -9034.2 | -10801.1 | -1038.6 | -0.3 | osm_way/899356447 |
| anchorage_bk | anchorage | -7110.0 | -9988.6 | +1050.1 | -0.7 | osm_way/899356446 |

## Published dimensions

* Main span 4,260 ft = **1,298.4 m**; total length 13,700 ft = **4,176 m**; deck width 103 ft = **31.39 m**; towers
  693 ft = **211.2 m**; clearance below at mean high water 228 ft = **69.49 m**; upper deck **7 lanes**, lower deck
  **6 lanes**; four main cables 36 in = **0.914 m** diameter, 26,108 wires each; anchorages 229 x 129 ft =
  **69.8 x 39.3 m** [Wikipedia "Verrazzano-Narrows Bridge", MTA Bridges & Tunnels].
* Side spans **1,215 ft = 370.3 m** each (the standard published figure; the article gives only the main span).  The
  suspended structure is therefore 2,039.0 m and the remaining 2,137 m of the published total is approach viaduct.
* The tower tops are 1-5/8 in (41.3 mm) further apart than their bases because of the curvature of the Earth — a
  0.003 % effect, below this model's resolution and therefore **not** reproduced (stated).
* Cable sag **117.3 m**: the cable low point sits 3.1 m above the upper deck at mid-span.
* Towers: steel portal towers, each two cellular legs with four portal struts; two cables pass over each leg
  (**inferred** plane offsets +-12.0 / +-14.8 m, +-0.5 m).

## Not modelled

the cable bands and wrapping, the 2017-2021 upper-deck replacement's orthotropic panels, the Fort
Wadsworth and Fort Hamilton batteries under the anchorages, the toll gantry, the Belt Parkway and Staten Island
Expressway interchanges, and the tower elevator machinery.

## Polycounts / outputs

* `blender_out/landmarks/b_verrazzano_narrows.glb` — 117,032 triangles, 4.87 MB, bounds min ['-1253.7', '-541.5', '-25.0'] max ['1253.7', '541.5', '214.4']
* `blender_out/landmarks/b_verrazzano_narrows_lod1.glb` — 28,184 triangles, 0.75 MB, bounds min ['-1253.7', '-541.5', '-25.0'] max ['1253.7', '541.5', '214.4']
