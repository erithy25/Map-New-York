# Williamsburg Bridge

Script: `blender/landmarks/b_williamsburg_bridge.py` · agent B · generated 2026-09-06 11:58 UTC

## Placement

axis heading 111.87 deg (compass, +s), origin NYC_TM (-1870.73, 1507.85); alignment source: osm bridge:support ways + published span
measured span between tower_mn and tower_bk: 488.15 m vs published 487.68 m (+0.10 %); towers snapped symmetrically to the published value

| support | kind | NYC_TM x | NYC_TM y | s (m) | t (m) | source |
|---|---|---|---|---|---|---|
| tower_mn | pylon | -2097.2 | 1598.8 | -243.8 | +0.0 | osm_way/1016434034 |
| tower_bk | pylon | -1644.2 | 1416.9 | +243.8 | +0.0 | osm_way/1016434035 |
| anchorage_mn | anchorage | -2281.9 | 1672.5 | -442.9 | -0.4 | osm_way/1016434036 |

## Published dimensions

* Main span 1,600 ft = **487.68 m**; total length 7,308 ft = **2,227.4 m**; deck width 118 ft = **35.97 m**; towers
  335 ft = **102.11 m**; clearance 135 ft = **41.15 m** at mean high water [Wikipedia "Williamsburg Bridge"].
* Side spans 596 ft = **181.66 m** each, each carried on an *intermediate* tower of two piers with four columns —
  unusual for a suspension bridge and modelled as a four-column steel bent under the side-span deck.
* Stiffening trusses **40 ft = 12.19 m deep**, **67 ft = 20.42 m apart** ("three times as deep as those on the
  Brooklyn Bridge") [Wikipedia].  The four main cables run in the plane of those two trusses (two cables per truss
  line, **inferred** +-0.4 m).
* Traffic: 8 roadway lanes (two 4-lane roadways flanking the centre), **2 subway tracks** (J/M/Z) on the centre line,
  and two merged pedestrian/bicycle paths outboard of the trusses.
* Steel lattice towers, unclad — the bridge is the first major steel-tower suspension bridge.  Approach viaducts on
  braced steel columns at a 3 % grade [Wikipedia].

## Not modelled

the cable wrapping and bands, the 1990s deck replacement's orthotropic panels, the subway station
approaches at Marcy Avenue, the tower rivet detail, the original Hornbostel ornament (removed in the 1910s), and the
individual truss gusset plates.

## Polycounts / outputs

* `blender_out/landmarks/b_williamsburg_bridge.glb` — 84,236 triangles, 3.78 MB, bounds min ['-988.3', '-410.7', '-9.0'] max ['988.3', '410.7', '107.3']
