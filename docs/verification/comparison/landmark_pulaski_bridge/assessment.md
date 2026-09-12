# Pulaski Bridge

`landmark_pulaski_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Long Island Expwy td (2022-04-13) 045 - Greenpoint Skyline.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-13 12:35:50, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Long_Island_Expwy_td_(2022-04-13)_045_-_Greenpoint_Skyline.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **Its filename says what it is: a Greenpoint skyline**, shot over a highway parapet — the Long Island City towers under construction cranes, the Manhattan skyline behind them in haze, oil tanks and warehouses along Newtown Creek, and a scaffold gantry across the top right corner. The bascule span sits low and small in the middle distance.

**Camera** — 40.736209, -73.951079 (NYC_TM -108, 4066) at z 5.5 m NAVD88 | azimuth 340.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x854. The camera stands on **the item's recorded viewpoint, not the photograph's**: the photograph's own EXIF GPS is **826.2 m** away, far past the 250 m at which it could be the same view, and the record says plainly that this is a statement about the pairing rather than about the photograph. The recorded azimuth of 340.0° agrees with the measured bearing to the subject to **0.1°**, and the axis was left **level** because the subject is 350 m off. The walk then **moved the camera 48 m along the view azimuth**: the recorded viewpoint is boxed in, closed off **16 m ahead** against the **80.0 m** this frame needs. From there the view is clear for **96.0 m**, **nothing built stands within 20 m** and no simulated agent within 20 m. The ground under it reads 3.912 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 3.75 to 3.91 m.

**Sun** — azimuth 170.4°, elevation 58.2° at 2022-04-13T12:35:50−04:00, from the photograph's own **EXIF DateTimeOriginal**; 914.0 W/m² direct normal, sky at strength 0.0312, Filmic, **+0.55 stops** metered and unclamped against a linear median of **0.122776** and a target of **0.18**. The physical rule would have given **0.0 stops** — a high April Sun on an open site, and the scene arrived within half a stop of a photographable level by itself.

**In the scene** — 2,554,881 triangles: 6 building tiles (139,388 tris, 0 missing, 0 LOD-substituted), 2 landmark models of which 1 can fall inside the 54.4° frame, 25,991 pavement polygons, 2,549 props, 1,051 kit pieces, **0 park-ground meshes**, 27,492 triangles of structures over 6 tiles with **none missing**, 89 vehicles and 390 people.

## Verdict — the bridge is not in the frame, the two halves are 826 m apart, and nearly half the render is bare terrain because four tiles have no park ground built

**The height is right and the frame is not.** The probe measured **15.4 m** above a ground of **0.0 m** — the creek surface at the NAVD88 datum, which is the correct datum for a bridge over water — against the catalogue's **14.99 m** for `b_pulaski`, whose origin stands **14.4 m** from the coordinate. The object it measured, `lm_b_pulaski.35`, is **634.5 m by 162.9 m** in plan: the whole span as one member, not a tile mesh. Only **18 of 43** probe rays found built fabric, which is what a fan aimed at a 15 m deck over open water does. Of thirteen sightline rays, **4 are clear** and **2 land on the subject** — a visible fraction of **0.154** — and the other nine stop at **31.1 m** on `t_-1_4_red_brick`, one tile's red-brick surfaces joined into a single object (J94). In the published render the bascule span is not identifiable: a low brick warehouse row runs across the middle distance with bare trees and lamp standards in front of it, and behind that nothing reads as a bridge.

**The two halves are pictures of places 826 m apart.** The photograph was taken from the Long Island Expressway, high enough to see over the warehouses to Long Island City and Manhattan. The item's recorded viewpoint is on McGuinness Boulevard at street level, and the walk moved it 48 m further. So the reference has a skyline and the render has a wall.

**Nearly half the render is one flat grey surface, and the record names the cause.** **0 park-ground meshes and 0 surfaces** were built in this scene, and the note says why: the park ground was **not built for four tiles** in the 900 m ground radius — `t_-1_3`, `t_-1_4`, `t_0_3`, `t_0_4` — so there is bare terrain there. That bare terrain is the pale plane filling the lower 45 % and the left middle of the frame. It is a data gap with an exact list, not a rendering artefact — and those four tiles are not empty of parkland: the parks source holds **32, 37, 2 and 3** surfaces in them. Counted over the whole city while writing this sheet, the parks stage classified **27,493** surfaces covering **130.0 km²** and the geometry stage built **5,529** of them covering **19.7 km²**, so **110.4 km²** on **743** tiles was never draped (J102).

**The measured contrast says the same thing three ways.** Standard deviation **0.1252** against the photograph's **0.2633**, a ratio of **0.476** — the render holds less than half the tonal range. Its 95th percentile is **0.5676** against **0.8626**: there is nothing bright in the frame at all, no water, no hazy sky mass, no lit tower faces. And chroma **0.0587** against **0.1145**, a ratio of **0.513**. A grey plane, a brick wall and bare branches cannot reach a skyline's range.

**One thing this sheet gets right that most of the pass does not.** The photograph is dated **13 April** and the render drew **bare-canopy trees** — the date fell inside `leaf_off`'s window and the reference's trees are leafless, so the foliage matches. It is the second sheet written so far where J97's working half is visible, and the render's trees are the most convincing thing in the frame.

## Measured for this assessment

| figure | how |
|---|---|
| 32, 37, 2 and 3 surfaces in the four tiles the record names | counted in `data/processed/parks/surfaces.parquet` by its own `tile` column |
| 27,493 surfaces and 130.0 km² classified, 5,529 and 19.7 km² built, 110.4 km² on 743 tiles unbuilt | that file's `area_m2` and `tile` columns against the tiles that carry a `blender_out/tiles/*/tile_parkground.glb`; recorded as DEVIATIONS J102 |

## What matches

* **The height and the datum** — 15.4 m above a creek surface at 0.0 m NAVD88, against a catalogue entry of 14.99 m whose origin stands 14.4 m from the coordinate.
* **The aim** — the recorded azimuth agrees with the measured bearing to **0.1°**, and the frustum puts the bridge **1.6° off axis** at 313.5 m.
* **The trees are bare, from the photograph's own date** — 13 April, inside `leaf_off`'s window (J97's working half).
* **Every tile in range has its structures file** — 6 tiles, **0 without a file**, 27,492 triangles, over a creek crossed by rail and road structures.
* **Nothing was capped anywhere.** Props **2,549 placed of 2,611 in range**, kit **1,051 of 1,051**, **0 dropped for budget**, **0 suppressed** under landmark shells. This is one of the few sheets in the pass that drew everything it had.
* **The industrial waterfront is named in the terrain** — five water bodies in range: Dutch Kills, the East Channel, the East River, **Newtown Creek** and Whale Creek.
* **The development was almost unnecessary** — +0.55 stops metered against 0.0 by the physical rule.
* **25,991 pavement polygons and none dropped**, including **1,733 parking-lot** polygons, which is what this stretch of Greenpoint is made of.

## What does not match

* **The bascule span is not identifiable in the frame.** 2 of 13 rays reach it, at 304.5 m.
* **The camera is 826.2 m from where the photograph was taken**, and 48 m further after the walk. The reference is a skyline from an expressway; the render is a street behind a warehouse.
* **No park ground was built for four tiles in range** — `t_-1_3`, `t_-1_4`, `t_0_3`, `t_0_4` — so the frame's lower half is bare terrain.
* **Nine of thirteen rays are stopped by a joined tile mesh** at 31.1 m (J94).
* **Less than half the photograph's contrast** — sd **0.476×** — with a 95th percentile of **0.5676** against **0.8626**, and **0.513** of its colour.
* **The render is darker at the midtone** — p50 **0.4982** against **0.5924**, a ratio of **0.841**, mean **0.796×**. The photograph's median sits **0.783 stops** above the grey convention and the render's **0.239**, a **−0.544-stop** difference (J83).
* **No Manhattan skyline, no construction cranes, no oil tanks** — the photograph's own middle ground is outside this frame.
* **No cloud and no haze.** The reference's skyline is softened by spring haze, which is a large part of why its midtone sits high; nothing in this build reads a historical sky or an aerosol depth.
* **813 of the 2,174 trees are a substituted species** and **10** are scaled outside the allowed band, the highest out-of-band count written so far after the Boathouse's 26; 8 impostor cards were dropped.
* **The woodland is inferred** — **263** of the 2,112 impostor cards are procedural canopy stems placed by rule inside mapped woodland, with inferred species and heights (Stage 55).
* **2 props in range have no asset** — 1 billboard, 1 misc structure.
* **740 agents were dropped** — **204 pedestrians in the carriageway without crossing**, 50 vehicles at the agent triangle budget, 25 pedestrians where the planimetric data has no sidewalk, 9 cyclists and e-bikes the fleet exports without a rider, 2 vehicles where there is no roadway.
* **The windows are drawn on the shells, not cut** (Stage 34 / J51).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the span is not identifiable | the recorded viewpoint is at street level behind a warehouse row, and nine of thirteen rays are stopped 31 m out by a joined tile mesh; the walk's 48 m move was the best open air available (J79, J94) | **verification + geometry — open** |
| the two halves are 826 m apart | the photograph's EXIF GPS is far past the 250 m at which it could be the same view, so the item's recorded viewpoint was used; the record says so rather than pretending otherwise | verification — declared, and the honest choice |
| nearly half the frame is bare terrain | the park ground was not built for `t_-1_3`, `t_-1_4`, `t_0_3` and `t_0_4`, named in the record | **data — open (J102), 85 % of the city's mapped open space** |
| sd 0.476, p95 0.5676, chroma 0.513 | a grey plane, a brick wall and bare branches against a hazy skyline with water and lit towers; the photograph is developed 0.783 stops above the grey convention and the render 0.239 above (J83) | reference + data |
| no skyline, cranes or oil tanks | they stand beyond this frame from the recorded viewpoint | verification — the pairing |
| no cloud, no haze | nothing in this build reads a historical sky or an aerosol depth | reference — no source exists |
| 813 substituted species, 10 out of band | the species lists do not cover this stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| 263 procedural canopy stems | only individually mapped trees exist in the sources, so woodland polygons are filled by rule (Stage 55) | data — declared |
| 2 props unmapped | no asset exists for those kinds | data |
| 204 pedestrians in the carriageway | the crowd model puts walkers on surfaces the placement test reads as roadway; on this sheet that is most of the drop (J101's neighbour case) | verification |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
