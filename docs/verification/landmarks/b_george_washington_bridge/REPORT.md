# George Washington Bridge

Script: `blender/landmarks/b_george_washington_bridge.py` · agent B · generated 2026-09-06 11:58 UTC

## Placement

axis heading 104.47 deg (compass, +s), origin NYC_TM (-223.65, 16842.53); alignment source: osm bridge:support ways + published span
measured span between tower_nj and tower_ny: 1066.19 m vs published 1066.80 m (-0.06 %); towers snapped symmetrically to the published value

| support | kind | NYC_TM x | NYC_TM y | s (m) | t (m) | source |
|---|---|---|---|---|---|---|
| tower_nj | pylon | -739.8 | 16975.7 | -533.4 | +0.0 | osm_way/741784699 |
| tower_ny | pylon | 292.5 | 16709.3 | +533.4 | +0.0 | osm_way/741784700 |
| anchorage_ny | anchorage | 501.6 | 16655.2 | +749.1 | -0.2 | osm_way/899357171 |

## Published dimensions

* Main span 3,500 ft = **1,066.8 m**; total length 4,760 ft = **1,450.8 m**; deck width 119 ft = **36.27 m**;
  towers **184.1 m** (604 ft); clearance below at mid-span 212 ft = **64.62 m**; lane width 11 ft = 3.35 m;
  **8 lanes** on the upper level and **6** on the lower [Wikipedia "George Washington Bridge", PANYNJ].
* Side spans: the published total less the main span leaves 1,260 ft; the standard split is **610 ft = 185.93 m** on
  the New Jersey side (the anchorage is driven into the Palisades rock) and **650 ft = 198.12 m** on the New York side
  (a free-standing concrete anchorage in Fort Washington Park).
* Cables: **four**, 3 ft = **0.914 m** diameter, 61 strands x 434 wires = 26,474 wires each; two cables pass over each
  tower leg (**inferred** plane offsets +-14.0 / +-17.0 m, +-0.5 m).  Design sag 327 ft = **99.7 m**, which places the
  cable low point 2 m above the upper deck at mid-span — the bridge's characteristic profile.
* Towers: bare **steel lattice**; Cass Gilbert's granite cladding was cancelled in the Depression and never applied.
  Each tower is two lattice legs braced by lattice portal struts, the lower one framing the roadway.
* Deck: the 1962 lower level hangs from the same suspenders inside a stiffening truss between the two roadway levels.

## Not modelled

the Cass Gilbert cladding that was never built (correctly absent), the cable bands and wrapping, the
Little Red Lighthouse under the New York tower, the toll plaza and its canopies, the Trans-Manhattan Expressway
approach and its bus station, the Palisades Interstate Parkway interchange, and the tower rivet and gusset detail.

## Polycounts / outputs

* `blender_out/landmarks/b_george_washington_bridge.glb` — 94,736 triangles, 4.03 MB, bounds min ['-873.4', '-244.8', '-16.0'] max ['885.2', '241.8', '187.8']
