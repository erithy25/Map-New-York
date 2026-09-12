# Brooklyn Bridge seen from DUMBO / Brooklyn Bridge Park

`landmark_brooklyn_bridge_from_dumbo` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn Bridge March 2023 009.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-03-07 13:20:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn_Bridge_March_2023_009.jpg) — the photograph's view direction is derived from the image at **high** confidence. It is taken from directly beneath the Brooklyn tower, looking up the granite pier: the frame is masonry, main cable, suspenders and deck truss at close range, with the flag at the top and nothing else in it.

**Camera** — 40.704, -73.992 (NYC_TM -3548, 449) at z 3.9 m NAVD88 | azimuth 288.3°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint** and the record says why it did not use the photograph's own GPS: that position is 23 m away and *"the eye point there is inside `t_-4_0_roof_membrane` (a ray straight up from the eye point hits its roof), while the recorded viewpoint is in open air"*. From the recorded point the walk still had to move: boxed in with the azimuth closed off **72 m** ahead against the **80.0 m** this frame needs, so the camera went **4.0 m to the right** — *"the nearest point in open air"* — under the rule `radial search with a clear frame that sees the subject`, and `scored_on_subject_sightline: true`. The view is then clear for **96.0 m**; the nearest built thing in the frame is `prop_tree_honeylocust_small_bare_24` **18.2 m** away and **no simulated agent stands within 20 m**. The ground under the lens reads 2.34 m NAVD88 from 16 samples within 5.0 m, range 1.98 to 2.78 m. The axis is level, and the record gives the rule: *"the subject is 285 m away; anything that far is photographed with a level camera"*.

**Sun** — azimuth 204.6°, elevation 41.1° at 2023-03-07T13:20:26−05:00, from the photograph's own **EXIF DateTimeOriginal**; 847.9 W/m² direct normal, sky at strength 0.0333, Filmic, **+0.51 stops**. Metered: the linear frame's median is **0.126192**, already two thirds of the way to the 0.18 target, so the development is only **0.512 stops** — the scene arrived bright because most of the frame is pale bare ground. The physical rule would have given **0.07**.

**In the scene** — 4,320,955 triangles: 9 building tiles (233,782 tris), 3 landmark models of which 2 fall inside the 54.4° cone, 23,610 pavement polygons, **684 props**, 3,907 kit pieces, 46 park-ground meshes, **8 tiles of structures (114,496 tris)**, 88 vehicles and 434 people. The water table for this frame holds the East River, the Pier 1 Wetlands, a pond and a river, with 15,480 quads on the flattened water surface.

## Verdict — the sheet publishes 55.93 m for a tower the model builds 85.0 m tall, because the probe hit a main cable

**The height probe worked perfectly and answered the wrong question.** All **43 of 43** rays landed on built fabric — as clean a reading as the instrument can give — and J74's rule fired correctly: the nearest catalogue origin is **138.0 m** away, past the 120 m the old rule looked in, so the height came from the geometry rather than from the catalogue's 84.3 m. The answer was **55.93 m** above a ground of 0.0 m, on `lm_b_brooklyn_bridge.35`, whose plan extent the record gives as **761.6 by 728.2 m**.

**That object is a cable.** Measured off `blender_out/landmarks/b_brooklyn_bridge.glb`, the four main cables — `cable_cable_t-12.6`, `t-3.1`, `t+3.1`, `t+12.6` — are each 3,516 triangles spanning **728.2 by 761.6 m** in plan and z 30.3 to 81.6 m, which matches the recorded extent to the decimetre. The item's coordinate falls under the catenary, so the ray up from it met a cable at 55.93 m and stopped. **The tower is in the same file and is not what was measured**: `tower_bk_pier` runs from −13.0 to 36.5 m on a 45.5 by 44.7 m footprint, `tower_bk_body` from 36.5 to **85.0 m** on 43.3 by 42.5 m in 270 triangles, with 456 triangles of string courses, a band at 75.9 m and four cable saddles topping out at 81.4 m. So the model's Brooklyn tower stands 85.0 m against the 84.3 m its own catalogue publishes, and the sheet reports two thirds of that because a rope was in the way.

**The cable's extent then sized the sightline.** The fan's horizontal half-angle is **27.22°**, taken from that 761.6 m width, and the record notes it was *"clipped to the frame, because a ray outside the picture tests something that is not in it"*. A fan built to span a 761 m cable cannot be a test of a 43 m tower. This is J94's fault — a joined mesh whose extent means nothing for a fan — appearing inside a **landmark** model rather than a tile mesh, and the record's `is_tile_mesh: false` reads as reassurance when it is not one. Measured across the pass, **15 of 118 records report a plan extent 300 m or wider, and 8 of those are landmark objects**: the Bronx-Whitestone at 1,040.8 m, the Queensboro at 1,002.4 m, the Throgs Neck at 887.1 by **1.5 m**, both Brooklyn Bridge sheets at 761.6 m, the Pulaski at 634.5 m and the Metropolitan Museum at 322.8 m.

**The two frames are not of the same thing.** The photograph stands under the tower; the render stands **284.7 m** away across Main Street Park, level, with the bridge a thin pale line across the middle distance behind a screen of bare branches. The walk did what it could — it scored candidates on the subject's own sightline, and `subject_sightline_at_choice` records the answer it settled for: 13 rays, **3 on the subject**, a visible fraction of **0.231**, blocked at **18.9 m** by `prop_tree_honeylocust_large_bare_25`. That is the best point it found. The frame that results is dominated by the park's own bare ground, and that is the second measured fault on this sheet: **3,589 of the 4,373 props in range were dropped** at a 1,106,383-triangle budget, including **3,180 tree rows**, so what should be Brooklyn Bridge Park's planting is 340 bare impostor cards on an empty plane.

**The trees are correctly bare.** 7 March is inside the build's leaf-off window, and every one of the 340 trees drawn is a bare-canopy card. That is the switch behaving (J97) and it happens to be right for this date.

## What matches

* **43 of 43 probe rays on built fabric**, and J74's origin rule fired correctly: the catalogue origin at 138.0 m was past the 120 m reach, so the height was measured rather than copied.
* **The tower itself is well built**, at 85.0 m against a published 84.3 m, on a 43.3 by 42.5 m body over a pier from −13.0 m, with string courses, a band and four saddles.
* **The bridge's structure is genuinely modelled**, not a silhouette: four main cables of 3,516 triangles each, four runs of suspenders, the stays, a deck slab and roadway with markings, thirty-six truss bays, two promenades with railings and 3,016 triangles of promenade lamps.
* **The camera refused a bad viewpoint for the right reason.** The photograph's own GPS would have put the eye inside a roof membrane, so the recorded viewpoint was used and then moved 4.0 m to the nearest open air — and the move was **scored on the subject's own sightline** (J79), not on eye-level clearance.
* **Structures are here in force**: 8 tiles imported for **114,496 triangles**, the largest structures contribution on any sheet read this round, which is the Brooklyn-side rail and pier fabric this view depends on.
* **The kit is complete.** 3,907 pieces drawn of 3,907 in range — nothing capped, nothing suppressed.
* **The park ground is correct in the near field**: 133 samples within 150 m, `under_frac` **0.0075**, median clearance +0.207 m. What the camera can actually see sits on the terrain.
* **The trees are bare, and 7 March is a leaf-off date.**
* **The development is nearly a null operation**: 0.512 stops on a scene whose linear median is already 0.126192, and the 95th percentiles agree closely — 0.6313 against the photograph's 0.6887.
* **The junction is marked**: 23,610 pavement polygons with 12,691 white markings and 692 crosswalk, and **0 dropped**.

## What does not match

* **The published height is 55.93 m for an 85.0 m tower.** The instrument measured a cable and reported it as the subject.
* **The sightline fan was sized from a 761.6 m cable** and had to be clipped to the frame, so the 0.231 visible fraction is not a test of the tower.
* **The subject's ground is 0.0 m NAVD88** — the tidal datum, because every tidal water body in this build is flattened to it (J103). The tower's pier actually stands in the river.
* **Eighty-two per cent of the props in range were dropped.** 684 drawn of 4,373 at a 1,106,383-triangle budget, **3,589 dropped for budget**, of which **3,180 are tree rows**. Brooklyn Bridge Park is a planted park and the render shows bare ground.
* **Not one tree is drawn from modelled branches.** All 340 are six-triangle impostor cards out to 880 m, 312 of them a substituted species, all 340 scaled at a mean of 0.872, and 4 cards dropped as opaque.
* **A bare tree 18.9 m from the lens blocks five of the thirteen rays** to a bridge 285 m away.
* **The photograph is a granite close-up and the render is a park.** The reference has no ground, no sky below the deck and no middle distance; this frame is two thirds pale bare earth. Nothing about masonry coursing, cable diameter, suspender spacing or the arch profile can be read across the two halves.
* **A stop and five eighths of the brightness difference is exposure.** The photograph sits **1.391 stops below** the grey convention and the render 0.238 above it, a **1.629-stop** gap, so p50 reads **1.714×** and mean 1.288× (J83). The render also holds much less contrast, sd 0.1636 against 0.2107 (**0.776×**), because the photograph is black granite against a hard blue sky and this frame is pale dirt.
* **The render carries just over a quarter of the photograph's colour**: chroma 0.0591 against 0.2208, a ratio of **0.268**.
* **The park ground sinks badly away from the camera.** Over all 1,765 samples `under_frac` is **0.387**, worst case **−5.681 m**; in the 150 to 400 m band it is **0.4748** of 238 samples, which is worse than the far field. This is the worst park-ground clearance on any sheet read this round.
* **Sixty-six agents stand inside buildings.** 38 pedestrians and 28 vehicles, the highest count read this round, alongside **189 pedestrians dropped for not being on a walkable surface** — on a waterfront park whose promenade is not a road-network sidewalk (J101).
* **434 people and 88 vehicles** where the density table asked for 654 vehicles and 2,757 people; 871 and 3,000 were simulated and **3,349 dropped** — 1,367 pedestrians outside the radius, 509 and 299 at the agent budget, 463 in the carriageway without crossing, 352 vehicles outside the radius, 53 off the carriageway and 51 riderless bodies.
* **Every vehicle is at the coarsest LOD.** All 88 are LOD2, and 433 of the 434 people.
* **Ten props across five kinds had no asset**: 4 parks building, 2 drinking fountain, 2 misc structure, 1 memorial, 1 vending machine. A waterfront park's buildings and fountains are exactly the missing kinds.
* **One tile has no structures file** beside the eight that do.
* **No cloud.** The reference's sky is a hard clear March blue; the render's is a procedural Nishita dome at strength 0.0333.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the four main cables are 3,516 triangles each, 728.2 by 761.6 m in plan, z 30.3 to 81.6 m | the accessor `count` and `min`/`max` of every primitive of every node of `blender_out/landmarks/b_brooklyn_bridge.glb`, read from the binary glTF header; the nodes are named `cable_cable_t-12.6`, `t-3.1`, `t+3.1` and `t+12.6` |
| the Brooklyn tower: a pier from -13.0 to 36.5 m on 45.5 by 44.7 m, a body from 36.5 to 85.0 m on 43.3 by 42.5 m in 270 triangles, 456 triangles of string courses, a band at 75.9 m, four saddles topping at 81.4 m | the same accessor bounds, for the nodes named `tower_bk_pier`, `tower_bk_body`, `tower_bk_string_courses`, `tower_bk_band` and `tower_bk_saddle` |
| the model carries 103 mesh nodes including four runs of suspenders, the stays, deck slab, roadway, markings, thirty-six truss bays, two promenades with railings and 3,016 triangles of promenade lamps | the node list of the same file |
| 15 of 118 records measure a plan extent 300 m or wider, and 8 of those are landmark objects rather than tile meshes | counted over every record carrying `subject.plan_extent`; the eight are the Bronx-Whitestone 1,040.8 m, the Queensboro 1,002.4 m, the Throgs Neck 887.1 by 1.5 m, this sheet and the Brooklyn Bridge walkway at 761.6 m, the Pulaski 634.5 m and the Metropolitan Museum 322.8 m |
| 82 per cent of the props in range were dropped | the record's own `props.placed` of 684 against `props.in_range` of 4,373 |
| 7 March is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py`, which is true for a date on or after 15 November or on or before 15 April (J97) |
| the worst park-ground clearance read this round | this sheet's `under_frac` of 0.387 over 1,765 samples, against the twenty-nine sheets read in the preceding rounds |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 55.93 m published for an 85.0 m tower | the item's coordinate falls under the main cables' catenary, so the probe's ray met a cable first; the probe has no way to prefer masonry over a rope, and the object it hit spans 761.6 m so nothing about its extent flags the mistake (J74, J94) | **verification — open; the repair is the same as J94's, that an object this large cannot stand for the subject** |
| the fan was sized from a cable and clipped to the frame | the horizontal half-angle is taken from the hit object's plan extent, which is a 761.6 m cable (J94, extended to landmark models) | **verification — open** |
| the subject's ground is the tidal datum | every tidal water body is flattened to 0.0 m NAVD88 (J103) | declared decision |
| 3,589 props dropped, 3,180 of them trees | the props triangle budget at 1,106,383 triangles, on a frame whose foreground is a planted park | **performance — the largest props shortfall on any sheet read this round** |
| no modelled tree canopy | none of the 340 rows drawn falls within the 120 m at which branches are drawn | performance — declared |
| a bare tree blocks five of thirteen rays | the walk's clearance probe tests built fabric, and a tree is a prop, so a candidate with a trunk 18 m from the lens scores as clear; the sightline ranking then cannot see it either (J88) | **verification — open** |
| the two frames are not of the same thing | the item's viewpoint is 285 m from a subject the photograph was taken underneath; the chooser has no framing test (J71) | verification — open |
| 1.629 stops of exposure difference | the photograph was developed 1.391 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| chroma 0.268 | flat authored surface colours and a procedural sky against black granite in hard March sun | data — declared (J66) |
| park ground 0.387 under the terrain over 1,765 samples | the park surfaces were draped on the fine grid and the scene's terrain coarsens to 40.0 m (J40, J96) | verification — declared |
| 66 agents inside buildings, 189 off a walkable surface | the crowd's walkable test reads only road-network sidewalk classes, so a waterfront promenade is not standable and the placer's fallbacks put bodies indoors (J101) | **verification — open** |
| 434 people where the table asked 2,757 | the 1,125,000-triangle agent budget plus the placement rules | performance + verification |
| 10 props across 5 kinds unmapped | no asset exists for those kinds | data |
| 1 tile with no structures file | that tile was not built (B13 remainder) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
