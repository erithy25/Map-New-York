# Ellis Island Main Immigration Building

Script: `blender/landmarks/b_ellis_island_main.py` · agent B · generated 2026-09-06 13:29 UTC

## Published dimensions

* French Renaissance Revival in **red brick with limestone quoins, keystones and belt courses**, on a steel frame;
  the building is **338 ft long by 168 ft wide = 103.0 x 51.2 m** with **four corner towers**, each capped by a
  **copper dome and a finial**, rising about **100 ft = 30.5 m** [NPS, HABS NJ-1112, Wikipedia "Ellis Island
  Immigrant Building"].
* The **Registry Room (Great Hall)** on the second floor is **200 x 100 ft = 61.0 x 30.5 m** and **56 ft = 17.07 m**
  high, vaulted in **28,282 Guastavino tiles** after the 1916 Black Tom explosion damaged the original plaster
  ceiling.  The hall is modelled as a raised roof volume over the centre of the building; **the vault and its tiles
  are not modelled** (stated).
* The three great arched entrance openings on the harbour front are each about **7.6 m** wide and **12.2 m** high
  (*inferred* from the elevation and photographs, +-0.8 m).
* The real OTI footprint (BIN **1085964**) covers **17,332 m2** — the main building *and* its flanking wings and the
  1930s ferry building; its LiDAR height is **26.5 m** over ground **3.66 m NAVD88**.  The model builds the whole
  real footprint at the LiDAR height and raises the Registry Room roof and the four towers above it.

## Placement

the real OTI footprint for BIN 1085964, principal axis from its minimum rotated rectangle (the building
faces north-east across the harbour towards Manhattan).

## Not modelled

the Guastavino vault and the Registry Room interior, the canopy over the entrance, the dormers and
their pediments, the limestone quoin coursing, the flanking hospital buildings on the island's south side, the
ferry basin and its 1930s ferry building as separate volumes, and the island's seawall and landscaping.

## Polycounts / outputs

* `blender_out/landmarks/b_ellis_island_main.glb` — 5,992 triangles, 0.31 MB, bounds min ['-191.6', '-113.2', '-2.0'] max ['99.2', '99.6', '45.3']
* `blender_out/landmarks/b_ellis_island_main_lod1.glb` — 2,602 triangles, 0.18 MB, bounds min ['-191.6', '-113.2', '-2.0'] max ['99.2', '99.6', '45.3']
