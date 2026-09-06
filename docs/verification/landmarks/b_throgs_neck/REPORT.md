# Throgs Neck Bridge

Script: `blender/landmarks/b_throgs_neck.py` · agent B · generated 2026-09-06 13:27 UTC

## Placement

axis heading 359.48 deg (compass, +s), origin NYC_TM (13196.43, 11147.72); alignment source: osm bridge:support ways + published span
measured span between tower_qn and tower_bx: 549.34 m vs published 548.64 m (+0.13 %); towers snapped symmetrically to the published value

| support | kind | NYC_TM x | NYC_TM y | s (m) | t (m) | source |
|---|---|---|---|---|---|---|
| tower_bx | pylon | 13193.9 | 11422.4 | +274.3 | +0.0 | osm_way/1016661640 |
| tower_qn | pylon | 13198.9 | 10873.1 | -274.3 | +0.0 | osm_way/1016661642 |
| anchorage_bx | anchorage | 13191.9 | 11599.7 | +452.0 | +0.4 | osm_way/1016661637 |
| anchorage_qn | anchorage | 13199.5 | 10695.5 | -452.3 | +1.1 | osm_way/1016661644 |

## Published dimensions

* Main span 1,800 ft = **548.64 m**; length between anchorages 2,910 ft = **886.97 m**, giving side spans of
  **169.17 m** each; total length with approaches 11,250 ft = 3,429 m (Bronx approach 3,900 ft = 1,189 m, Queens
  approach 2,800 ft = 853 m — modelled at 320 m each, see below); towers **105.5 m** above mean high water (346 ft;
  326 ft = 99.4 m above the artificial islands, which stand 20 ft = 6.1 m out of the water); clearance below
  142 ft = **43.28 m**; roadway 37 ft = 11.28 m per direction with a 4 ft = 1.22 m median, **6 lanes**; stiffening
  trusses 28 ft = **8.53 m** deep; anchorages 250 x 350 ft = **76.2 x 106.7 m**; each main cable has 37 strands of
  296 wires = 10,952 wires [Wikipedia "Throgs Neck Bridge", MTA Bridges & Tunnels].
* Two main cables (one in each truss plane), the standard arrangement for Ammann's post-war Sound crossings; cable
  planes at t = +-11.9 m (**inferred** from the 23.8 m truss spacing, +-0.4 m).
* The towers stand on artificial islands 6.1 m above the water; the model builds those islands.

## Not modelled

the cable bands and wrapping, the toll gantry, the Cross Island Parkway and Clearview Expressway
interchanges, the fender systems around the islands, and the 2010s deck replacement's orthotropic panels.

## Polycounts / outputs

* `blender_out/landmarks/b_throgs_neck.glb` — 50,392 triangles, 2.33 MB, bounds min ['-58.4', '-801.7', '-9.0'] max ['58.4', '801.7', '108.7']
* `blender_out/landmarks/b_throgs_neck_lod1.glb` — 10,608 triangles, 0.35 MB, bounds min ['-58.4', '-801.7', '-9.0'] max ['58.4', '801.7', '108.7']
