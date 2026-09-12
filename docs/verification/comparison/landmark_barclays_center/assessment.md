# Barclays Center

`landmark_barclays_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Barclays Center (54458684337).jpg by Eden, Janine and Jim from New York City, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2025-04-17 18:23, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Barclays_Center_(54458684337).jpg) — the photograph carries its own camera GPS, so the view direction is derived from the image at **high** confidence.

**Camera** — 40.683866, -73.977453 (NYC_TM -2321, -1791) at z 15.6 m NAVD88 | azimuth 130.4°, pitch +5.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x720. The camera stands on **this photograph's own EXIF GPS**, **57.2 m** from the item's recorded viewpoint — the position the picture was actually taken from. It was **not moved**: `moved: false`, offset 0.0 m, with the view azimuth clear for **148.8 m** against an 80.0 m requirement. The nearest built thing in the frame is `prop_hydrant_fdny_2` **4.6 m** away at +18.1° yaw and −16.1° pitch, and the nearest simulated body is `agent_veh_camry_black_car_580.44` at **22.8 m**. The heading is the bearing from that GPS position to the item's subject coordinate; the item's own recorded azimuth is **144.8°**, **14.4° away**, and the record says it "belongs to its nominal viewpoint". The ground under the lens reads 13.959 m NAVD88, the 10th percentile of 113 samples within 12.0 m, range 13.89 to 14.22 m.

**Sun** — azimuth 273.1°, elevation **13.2°** at 2025-04-17T18:23:00−04:00, from the photograph's own **EXIF DateTimeOriginal** to the minute; 521.0 W/m² direct normal, sky at strength 0.0494, Filmic, **+2.53 stops**. Metered: the linear frame's median is **0.031222** against the 0.18 target, so the development is **2.527 stops** with nothing clamped. The physical rule would have given **1.71** — the largest agreement between rule and measurement on any sheet read so far this round is nowhere near this close, and the gap of eight tenths of a stop is the low Sun: at 13.2° of elevation the direct beam is raking and most of the frame is in the towers' shadow.

**In the scene** — 4,500,049 triangles: 7 building tiles (464,918 tris), 2 landmark models of which 1 falls inside the 54.4° cone, 28,306 pavement polygons, 4,049 props, 7,065 kit pieces, 33 park-ground meshes, **2 tiles of structures (14,788 tris)**, 50 vehicles and 334 people. The Gowanus Canal is in the water table for this frame.

## Verdict — the most sculptural building skin in New York is an eighty-four-triangle prism with three flat rings around it

**The arena's form is a straight vertical extrusion of its own footprint.** Measured off `blender_out/landmarks/c_barclays_center.glb`, the whole model is **7,058 triangles** outside its LOD: the `body` is **84**, the `base` 84, the sunken `bowl` 44, the oculus canopy 98, and the three weathering-steel bands carry the remaining **6,748**. The body is built as `C.prism(offset_polygon(P, -1.2), 3.0, 41.5)` — the real OTI footprint pushed straight up — and the bands stand 1.2 m proud of it on that same footprint at three fixed height ranges. So every surface of this building is **vertical**. The real arena's bands lean out, swell and peel away over the entrance; that is what the left half of the sheet is a photograph of, and the right half has three parallel rings on a box. The crop shows it plainly: the bands' top edges look curved only because of perspective, and the near corner turns through a chamfer rather than a sweep.

**The panel rhythm is there and it is a quarter of the real one.** The builder's own note names **12,000 pre-weathered steel panels**. The band loop lays a quad grid of 4.9 m by 1.5 m panels — `npan = round(L / 4.9)`, `nrow = round((z1 - z0) / 1.5)` — over a 181.8 by 166.6 m footprint in three bands 12.0, 11.0 and 11.5 m tall, which comes to roughly **3,266 panels**, each a flat quad displaced by `1.2 + 0.55·sin(...)·0.25` metres. So each panel has a little skew in how far it stands out and **no twist at all**, and there are about a quarter as many of them as the building has. The builder's fidelity note says exactly this — *"NOT modelled: the individual twist of each of the 12,000 panels"* — and the count is worth putting beside it.

**The oculus is modelled, and the camera pushed it to the edge of the frame.** `c_barclays_center_oculus` is 98 triangles standing 43.2 by 39.2 m in plan from z 3.0 to 12.5 m, projecting **19.5 m** beyond the body's own edge: two plates at 9.5 and 12.5 m, three edge quads, four tapering struts and an emissive oval ring 9.1 m across on a 1.55:1 lathe. J81's repair holds — it is on the Atlantic/Flatbush end, chosen as the convex footprint vertex nearest the road network's own crossing node, not the acute vertex at the 6th Avenue end. But in this frame it is a dark plate along the **left edge**, seen almost edge-on and mostly cut off, because the camera is aimed at the item's recorded subject coordinate **216.8 m** away, which lies deep inside a building 181.8 m long. The photograph puts the canopy in the middle of the picture. Turning the 14.4° back to the item's recorded 144.8° azimuth would have done the same here; aiming at a point rather than at a face is what did not.

**The measurement, by contrast, is the best in the pass.** The height probe cast 43 rays and **all 43 landed on built fabric** — the only reading of its kind read this round — giving **40.36 m** above a ground of 14.24 m against the model's LiDAR-derived 42.1 m, and a plan extent of **178.7 by 163.7 m**, which is the `body` prism to the decimetre. The catalogue origin is 21.8 m away and carries 42.1 m, so for once the catalogue and the probe agree and the difference is the 0.6 m the builder deliberately holds back below the roof.

**The sightline is J88 again.** 13 rays, **8 clear and 8 on the subject**, **0 into nothing**, a visible fraction of **0.615** — and the five that fail all stop at **37.3 m** on `prop_lamp_cobra_davit_18`, a cobra-head street lamp. Six of the eight hits are the arena's own fabric met nearer than the recorded coordinate, first at **145.2 m** on `lm_c_barclays_center.0`, which is the bands: the continuity rule correctly counts a hit on the near face of a 182 m building as the subject rather than as an obstruction.

## What matches

* **The height and the footprint, to the decimetre.** 40.36 m measured from **43 of 43** probe rays on fabric, against the 42.1 m LiDAR roof the model is built to, on a plan extent of 178.7 by 163.7 m.
* **The three bands and their glazed slots are the right composition.** Three rust rings at 3.0–15.0, 17.0–28.0 and 30.0–41.5 m with dark steel trim above and below each, separated by glazed slots, and a faint panel quilt across the rust. Stand far enough back and the render reads as Barclays Center.
* **The oculus canopy exists and is on the right end.** 19.5 m of cantilever with a 9.1 m emissive oval ring and four tapering struts, placed on the convex corner nearest the Atlantic × Flatbush crossing node — J81's repair, holding.
* **The camera is where the photographer stood.** The photograph's own EXIF GPS, 57.2 m from the nominal viewpoint, not moved, with 148.8 m of clear view.
* **The Sun is the real minute of the real evening.** 13.2° of elevation at 18:23 on 17 April, from EXIF, and the frame is metered to it rather than assumed: 2.527 stops, nothing clamped.
* **The contrast matches almost exactly.** Standard deviation 0.2287 against 0.2254, a ratio of **1.015** — the closest agreement on any figure between these two halves.
* **The fleet is a Brooklyn fleet.** 31 sedans, 8 SUVs, 4 boro taxis, 4 yellow taxis, 2 black cars and a van. Four green Street Hail Liveries at Flatbush and Atlantic is correct: this is where they are legally allowed to work, and it is the opposite of what the Times Square sheets show (J105).
* **The junction is paved as the junction.** 28,306 polygons with **12,441 white markings**, 5,023 sidewalk, 4,926 roadbed, 3,289 curb, 782 crosswalk, 740 plaza, 453 median and 385 yellow markings, and **0 dropped**.
* **The neighbourhood is planted.** 4,049 props of 4,182 in range with nothing lost to budget, including **3,260 trees**, 151 cooling towers, 149 street lamps, 145 Citi Bike dock units, 138 manholes, 82 hydrants, 38 bike racks, 38 vent grates, 16 bus-stop signs, 13 waste baskets, 9 subway entrances, 4 bus shelters and 2 mailboxes.
* **Structures are actually here.** 2 tiles imported for 14,788 triangles — one of the minority of sheets in the pass that has any, on the Atlantic Terminal rail approach.

## What does not match

* **The skin does not curve.** The body is an 84-triangle prism and the bands are three flat rings on it, so the building's defining geometry — the outward lean, the plan undulation, the peel over the entrance — is absent. Nothing in the record is wrong about this; the builder's own fidelity note declares it.
* **About 3,266 panels where the building has 12,000**, each a flat quad with a skewed offset rather than a twist.
* **No signage.** The photograph's blue "BARCLAYS CENTER" letters across the canopy fascia, the script signage and the sponsor boards under it are not a class this build models; the canopy's only emissive is the oval ring.
* **No green roof.** The sedum roof added in 2015 is visible in the photograph and is on the builder's explicit not-modelled list.
* **No subway entrance canopy** at the plaza, also declared.
* **The canopy is at the frame edge.** The camera aims at a subject coordinate 216.8 m away inside a 181.8 m building, which turns the lens 14.4° off the item's own recorded azimuth and puts the entrance the photograph is about along the left border, seen edge-on.
* **Five of thirteen sightline rays are stopped by a street lamp** 37.3 m from the lens — the visible fraction of 0.615 is a lamp mast, not the arena (J88).
* **A stop and a half of the brightness difference is exposure, and the rest is shadow.** The photograph sits **0.64 stops below** the grey convention and the render 0.247 above it, an **0.887-stop** gap, so mean reads 1.332× and p50 1.335× (J83). The photograph's own 5th percentile is **0.0488** against the render's 0.1527: the real 18:23 light leaves hard black shadow between the towers that the render's lifted development does not.
* **The render carries under half the photograph's colour**: chroma 0.094 against 0.1987, a ratio of **0.473**. The photograph's weathered steel is a saturated rust against a deep blue April sky; the render's `rust` material is an authored albedo of 122, 74, 50 at roughness 0.72 and the sky is a procedural Nishita dome.
* **334 people and 50 vehicles at the busiest junction in Brooklyn.** The density table asked for 753 vehicles and 2,638 people over the simulated ring; 906 and 2,999 were simulated and **3,521 dropped** — 936 pedestrians and 437 vehicles outside the radius, **848 pedestrians in the carriageway without crossing**, 773 and 356 at the 1,125,000-triangle agent budget, 103 not on a walkable surface, 49 riderless vehicle bodies, 14 off the carriageway and 5 above the observer. The photograph's own foreground is four lanes of stationary traffic.
* **The kit was capped.** 7,065 pieces drawn of 8,648 in range against a **1,363,289**-triangle budget, of which 5,536 are windows against 54 cornices, 54 quoins and 52 string courses.
* **Only 25 trees in 3,260 are drawn from modelled branches.** The other 3,235 are six-triangle impostor cards out to 804 m, 830 of them a substituted species, 3,252 scaled at a mean of 0.926 with 8 outside the band, and 5 cards dropped as opaque.
* **The park ground sinks at every distance that was measured.** 1,676 samples, `under_frac` **0.2476**, more than 0.05 m under on 0.2136, worst case −1.918 m; and in the 150 to 400 m band it is worse than in the far field, 0.274 of 219 samples. There are **0 samples within 150 m**, so the near field is untested. One tile in the 804 m ground radius has no park ground built at all.
* **Five props across five kinds had no asset**: 1 each of artwork, misc structure, parks building, passenger-information sign and vending machine.
* **Five tiles have no structures file** beside the 2 that do.
* **No cloud.** The reference's sky is clear, which helps, but nothing in this build reads a historical sky either way.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| 7,058 triangles outside the LOD: bands 6,748 with base 84, body 84, bowl 44 and oculus 98, beside an LOD1 of 212 | the accessor `count` and `min`/`max` of every primitive of every node in `blender_out/landmarks/c_barclays_center.glb`, read from the binary glTF header |
| the bands span 184.3 by 169.3 m and z 2.7 to 41.8 m; the body 178.7 by 163.7 m and z 3.0 to 41.5 m | the same accessor bounds, per node, in the model's own local frame |
| the oculus is 43.2 by 39.2 m in plan, z 3.0 to 12.5 m, projecting 19.5 m past the body's edge, with its emissive ring lathed on a 1.55 to 1 oval | the accessor bounds for `c_barclays_center_oculus` against `c_barclays_center_body`, and the `b.lathe(..., scale_xy=(1.55, 1.0))` call that makes the ring |
| 12,000 panels, three bands, a 4.9 by 1.5 m panel, a 25.0 m cantilever, a 9.1 m opening, a 9.5 m soffit, a footprint of 18,607 m2 at 181.8 by 166.6 m, 137 ft of height, BIN 3398156 | the dimensions block of `blender/landmarks/c_barclays_center.py`, which cites SHoP, ASI Limited, Ellerbe Becket and the OTI LiDAR for each |
| about 3,266 panels in the model | the band loop's own arithmetic in the same file: `npan = round(L / 4.9)` panels along each footprint edge and `nrow = round((z1 - z0) / 1.5)` rows up each of the three bands, over that perimeter |
| each panel is displaced by 1.2 m plus a skew of 0.55 times a sine, and is a flat quad | the `b.quad(...)` call inside that loop |
| the three bands stand at 3.0 to 15.0, 17.0 to 28.0 and 30.0 to 41.5 m, which makes them 12.0, 11.0 and 11.5 m tall | the `BANDS` constant in the same file |
| the entrance corner is the convex vertex nearest the Atlantic x Flatbush node, 161.8 m from it, against 275.9 m for the 86.6 deg corner at the 6th Avenue end | the `ENTRANCE_XY` comment in the same file, which records the node's own coordinate from `data/processed/roads/nodes.parquet` and the two distances (J81) |
| the rust albedo is 122, 74, 50 at roughness 0.72 | the `C.custom_material("rust", ...)` call in the same file, declared there because weathering steel is not in the shared palette |
| 43 of 43 probe rays on fabric is the only such reading read this round | this sheet's own `subject.height_probe`, against the twenty-nine sheets read in the preceding rounds |
| the sd ratio of 1.015 is the closest agreement between these two halves | this sheet's own `frame_stats.json`, comparing its four ratios |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the skin does not curve; the body is 84 triangles | the arena is built as a straight prism of its footprint with three proud rings on it. A curved, leaning, undulating skin is not derivable from the OTI footprint and the LiDAR roof height, which is all the measured input there is | **geometry — declared in the builder's own fidelity note; the form would have to be authored from photographs** |
| 3,266 panels where the building has 12,000 | the panel grid is laid at the published 4.9 by 1.5 m module on a footprint whose perimeter will not carry 12,000 of them, because the real panels wrap a longer, doubly curved surface | geometry — a consequence of the straight prism |
| no twist on any panel | declared: each panel is a flat quad with a skewed proud offset | **declared decision** |
| no signage on the canopy | building-mounted lettering and sponsor boards are not a class this build models; no advertising or identifying copy was invented anywhere (DEVIATIONS B5/B15/B15a) | **declared decision** |
| no green roof, no subway entrance canopy | both on the builder's explicit not-modelled list | declared decision |
| the canopy is at the left edge of the frame | the lens is aimed at the item's recorded subject coordinate, a point 216.8 m away inside a 181.8 m building, rather than at the face the photograph shows; the item's own azimuth would have been 14.4 deg to the right | **verification — open, and the same shape as J74 and J107: a point is not a face** |
| the visible fraction is 0.615 | five of thirteen rays stop at 37.3 m on a cobra-head lamp mast, which the walk's clearance probe cannot see because a lamp is a prop (J88) | **verification — open** |
| 0.887 stops of exposure difference | the photograph was developed 0.64 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| chroma 0.473 | an authored rust albedo and a procedural sky against weathered steel under a real April evening | data — declared, no per-building colour source (J66) |
| 334 people where the table asked 2,638 | the 1,125,000-triangle agent budget plus the placement rules; 848 of the drops are pedestrians the simulation put in the carriageway without a crossing, at a junction where people cross constantly | performance + verification |
| the kit was capped at 1,363,289 triangles | 8,648 pieces in range, 7,065 drawn | performance |
| 25 modelled trees in 3,260 | only 25 of the rows in range fall within the 120 m at which branches are drawn | performance — declared |
| park ground under the terrain at 0.2476 of 1,676 samples, and no samples at all within 150 m | the park surfaces were draped on the fine grid and the scene's terrain coarsens to 40.0 m (J40, J96); the near field has no park surface to test | verification — declared |
| 5 props across 5 kinds unmapped | no asset exists for those kinds | data |
| 5 tiles with no structures file | those tiles were not built (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
