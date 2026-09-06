# Brooklyn Bridge

Script: `blender/landmarks/b_brooklyn_bridge.py` · agent B · generated 2026-09-06 13:31 UTC

## Placement

axis heading 316.29 deg (compass, +s), origin NYC_TM (-3916.47, 632.47); alignment source: osm bridge:support ways + published span
measured span between tower_bk and tower_mn: 486.49 m vs published 486.30 m (+0.04 %); towers snapped symmetrically to the published value

| support | kind | NYC_TM x | NYC_TM y | s (m) | t (m) | source |
|---|---|---|---|---|---|---|
| tower_bk | pylon | -3748.4 | 456.6 | -243.2 | +0.0 | osm_way/317352708 |
| tower_mn | pylon | -4084.6 | 808.3 | +243.2 | +0.0 | osm_way/1255363983 |
| anchorage_bk | anchorage | -3525.4 | 224.5 | -565.1 | -0.8 | osm_way/888759002 |
| anchorage_mn | anchorage | -4302.3 | 1034.8 | +557.5 | +0.8 | osm_way/1255363984 |

## Published dimensions

* Main span 1,595.5 ft = **486.3 m** between the tower centres; side spans 930 ft = **283.5 m** (tower to anchorage);
  Manhattan approach 1,567 ft = 477.6 m, Brooklyn approach 971 ft = 296.0 m; deck width 85 ft = **25.91 m**
  [Wikipedia "Brooklyn Bridge" / NYCDOT].  Modelled length tower-to-tower + side spans + approaches = 1,827.3 m against
  the published 6,016 ft = 1,833.7 m over-all (the 6.4 m difference is the anchorage masonry, which the published
  figure measures from Centre Street; stated as a gap).
* Towers: **84.3 m** above mean high water (276.5 ft; Wikipedia also quotes 278.25 ft = 84.81 m — the 84.3 m figure
  named in the build brief is used and the model is within 0.6 % of the alternative).  Two pointed Gothic arches per
  tower, each **10.29 m** wide (33.75 ft) and **35.66 m** high (117 ft), springing from the roadway; arch floor
  119.25 ft = 36.35 m above mean water; tower plan at the high-water line 140 x 59 ft = **42.67 x 17.98 m**; tower head
  159 ft (48.5 m) above the roadway.  Granite (Maine/Rockland) over a limestone-and-granite pier.
* Anchorages: 129 x 119 ft = **39.32 x 36.27 m** at the base, 117 x 104 ft = 35.66 x 31.70 m at the top, 89 ft
  (27.1 m) high; the roadway leaves through the top and the four cables enter the front face.
* Cables: **four** main cables, 15.75 in = **0.400 m** diameter, 5,282 galvanised wires each; design sag 128 ft =
  **39.0 m** over the main span, giving a saddle at 81.45 m NAVD88 and a mid-span low point at 42.45 m NAVD88 so that
  the shortest suspender is the published 8 ft (2.44 m).  1,088-1,520 suspenders (this model: 2.286 m = 7.5 ft pitch on
  every cable in main and side spans, 1,832 suspenders) and ~400 diagonal stays (this model: 25 per cable per
  direction per tower = 400), stay reach 18-131 m matching the published 138-449 ft stay lengths.
* Clearance 127 ft = 38.71 m above mean high water at mid-span; the deck crest is a parabola from 37.05 m NAVD88 at
  the towers to 39.41 m NAVD88 at mid-span.  MHW = NAVD88 + 0.70 m (b_common.MHW_ABOVE_NAVD88_M).
* Promenade: 18 ft = **5.5 m** above the roadways, 10-17 ft wide (this model 4.8 m), timber deck on the two inner
  stiffening trusses; it **splits around the central pier at each tower and passes through both Gothic arches**.
* Cable planes at t = +-3.10 m and +-12.55 m: the inner pair rises from the promenade edge trusses and the outer pair
  from the deck-edge trusses, so that all four saddles sit over solid granite either side of the arch openings.  These
  offsets are *inferred* from the six-truss deck division and photographs (+-0.5 m), not from a published table.
* Roadways: two carriageways of 8.9 m each side of the promenade, marked as 3 lanes each.  Published capacity is five
  motor lanes plus (since 2021) a two-way protected bike lane on the innermost Manhattan-bound lane; the model marks
  six lanes and does not distinguish the bike lane (stated gap).

## Verification renders

Four verification renders, each framed and lit to answer one question.

    1. ``dumbo_main_street_park`` — street level in Brooklyn Bridge Park at the foot of Main Street, the canonical
       DUMBO view of *this* bridge.  (The famous Washington Street shot, whose real photographic viewpoint is
       recorded in ``docs/verification/reference/dumbo_washington_st_manhattan_bridge/meta.json`` — camera
       40.7033 N, 73.98958 W, azimuth 355.6 deg — frames the **Manhattan** Bridge, and is rendered on that model.)
       Question: does the bridge read correctly at street level and eye height, at the right size and distance?
    2. ``tower_three_quarter`` — the Brooklyn tower from the river, close enough that the whole 84.3 m tower fills
       the frame, with the sun 35 deg up and roughly 60 deg off the tower's face so the 3.0 m string courses, the
       arch reveals and the batter all cast shadow.  Question: are the two pointed arches, the tower's plan and its
       height right, and does the deck pass through the arches at the right level?
    3. ``promenade`` — deck level on the promenade looking at the Brooklyn tower.  Question: is the promenade
       5.49 m above the roadway, does it split around the centre pier and pass through both arches, and do the
       four cables and the diagonal stay fan converge correctly?
    4. ``elevation_both_towers`` — a long lens from the river with **both** towers and both approaches in frame.
       Question: is the 486.3 m main span, the 39.0 m cable sag, the suspender rhythm and the deck crest right?

## Not modelled

the caissons and their timber, the individual cable wrapping wires and cable bands, the granite coursing
and its joints, the necklace lighting fixtures, the 1950s-era steel approach ramps at Park Row, the vaults inside the
anchorages, the wooden promenade benches, the bronze plaques, and the two intermediate longitudinal trusses under each
roadway (only the four trusses that show above the deck are built).

## Polycounts / outputs

* `blender_out/landmarks/b_brooklyn_bridge.glb` — 121,824 triangles, 5.72 MB, bounds min ['-703.3', '-603.6', '-13.0'] max ['577.8', '734.8', '85.0']
* `blender_out/landmarks/b_brooklyn_bridge_lod1.glb` — 33,496 triangles, 1.40 MB, bounds min ['-703.3', '-603.6', '-13.0'] max ['577.8', '734.8', '85.0']
