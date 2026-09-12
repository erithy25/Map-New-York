# 220 Central Park South

`landmark_220_central_park_south` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Central Park Tower 2020-03 jeh.jpg by Jim.henderson, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-03-15 17:14:27, 1920x3413. [Commons page](https://commons.wikimedia.org/wiki/File:Central_Park_Tower_2020-03_jeh.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.76517, -73.98125 (NYC_TM -2698, 7275) at z 24.8 m NAVD88 | azimuth 10.0°, pitch +15.2° | 18 mm on 36 mm (58.7° horizontal, 90.0° vertical, portrait) | 784x1394. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **559.7 m** away, past the 250 m at which it could still be the same view. The recorded azimuth of 10.0° agrees with the bearing to the subject to **0.1°**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+15.2°**, and the top of the subject is still cut off: `lm_c_billionaires_row.23` stands 283 m above the lens at 200 m, **55° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the azimuth closed **52 m** ahead against the **80 m** needed — so the camera was **moved 69.3 m** onto the nearest surveyed sidewalk polygon, scored on the subject's sightline, which returned 1 of 13 rays at the chosen point and was still the best available. From there the azimuth is clear for **96 m**, **nothing built stands within 20 m of the lens**, and the nearest agent is 19.6 m away. Ground under the camera reads **23.167 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 23.06 to 23.45 m.

**Sun** — azimuth 249.9°, elevation 19.4° at 2020-03-15T17:14:27−04:00, from the photograph's own **EXIF DateTimeOriginal**; 642.8 W/m² direct normal, sky at strength 0.0412, Filmic, **+5.18 stops**, declared: *under-lit: the scene needed +5.18 stops to read as a picture, more than the 4 a photographer recovers hand-held*. The linear frame's median is **0.00498** against a target of 0.18; the physical rule would have given **+1.17 stops** (J83).

**In the scene** — 4,500,031 triangles: 6 building tiles (314,652 tris, none missing, none LOD-substituted), 10 landmark models of which 3 fall inside the 58.7° frame — **none of them the subject** — 24,926 pavement polygons with **0 dropped**, 2,947 props, 6,299 kit pieces, 22 park-ground meshes over 295 surfaces with **2,814 faces cut** for landmark ground, 2 structures tiles (21,504 tris), 76 vehicles and 331 people, terrain 88,046 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the reference is a building site with a tower crane on it and the render is the finished tower, and in the render the avenue's walls are blank tan slabs with no windows at all

**The two halves are of different buildings in different years.** The photograph, taken 15 March 2020, shows the tower still under construction: a **tower crane** standing on the top, the uppermost floors in bare structure and orange formwork, the Novotel sign on the left. The model is the completed building. Nothing in the chooser looks at whether a photograph shows a finished structure, and nothing in the record notes it, so a 2020 construction photograph serves as the reference for a completed model — a temporal version of the scale fault recorded in J93.

**The render's bigger problem is that the avenue has no windows.** The masses on the left and centre-left are flat tan surfaces from pavement to parapet: no window grid, no cornice, no string course, no shopfront. **6,299 kit pieces were drawn out of 19,608 in range**, capped at a 1,030,689-triangle budget, and 6,129 of those 6,299 are windows spent on the nearer faces — so the further half of the canyon gets nothing. This is the clearest picture in the queue of what the kit budget costs at street level.

**The subject is behind a terracotta wall.** 13 rays, **1 clear**, **1 on the subject**, blocked at **31.8 m** by `t_-3_7_terracotta`, visible fraction **0.077**. The walk moved 69.3 m and this was the best point it could score.

**The height is measured and the catalogue was correctly refused.** `lm_c_billionaires_row.23`, **287.7 m** above a ground of 20.44 m, **43 of 43** rays, extent **26.4 m by 24.8 m** — a slender tower, correctly measured. The nearest catalogue origin is `b_columbus_circle_monument` **155.8 m** away carrying 228.6 m, a different landmark, and the record says the height came from the geometry and not the catalogue (J74).

## What matches

* **The height probe is clean and the extent is right for a needle tower**: 43 of 43 rays, 287.7 m, plan extent 26.4 m by 24.8 m.
* **The catalogue was refused on the right grounds** — the nearest origin belongs to the Columbus Circle monument, 155.8 m away (J74).
* **The camera stands on the recorded viewpoint for the right reason**: the photograph's own fix is 559.7 m away, well past the 250 m rule.
* **The clearance walk left the lens clear.** Nothing built within 20 m and the nearest simulated agent 19.6 m away — the only sheet in this queue that satisfies the 8 m rule with room to spare, on both geometry and crowd.
* **The season and the day type are right and were read**: bare canopies for 15 March, and the crowd clock reads **Sunday** for a date that was a Sunday.
* **Near-field ground is perfect**: within 150 m, **0.0** of 149 park-surface samples sit under the terrain, median **+0.12 m**, minimum +0.056 m.
* **The landmark-ground rule did real work**: **2,814** park-ground faces cut where a landmark supplies its own ground.
* **Props were not capped**: 2,947 placed of 3,078 in range, 0 dropped for the budget.
* **The pavement is complete**: 24,926 polygons, **0 dropped**, including 10,507 white markings, 5,308 sidewalk, 4,415 roadbed, 3,027 curb, 552 crosswalk and 522 plaza.

## What does not match

* **The reference shows the building under construction**, with a crane on top and bare structure at the crown; the render shows it finished.
* **The canyon walls have no windows.** Flat tan surfaces on the left and centre-left, floor to parapet, on the busiest block of Seventh Avenue.
* **The subject is behind a terracotta wall**: visible fraction **0.077**, 1 of 13 rays.
* **The frame is 5.18 stops under a photographable level**, declared as past hand-held recovery.
* **None of the three landmarks in the frustum is the subject** — the Columbus Circle monument at 285.2 m, Lincoln Center at 780.3 m and the Central Park perimeter wall at 2,499.9 m.
* **The render has no deep shadow**: fifth percentile **0.2973** against the photograph's **0.0594**, and standard deviation **0.1803** against **0.2779** (**0.649×**). The reference's left half is a building in full shade; the render's is a lit slab.
* **Chroma is 0.372 of the photograph's**, 0.0673 against 0.1808 — the reference carries a clear March sky and an orange Novotel sign, the render carries tan concrete.
* **The render is brighter overall and darker at the midtone**: mean **1.224×**, median **0.863×**, with the two development offsets **0.462 stops** apart (J83).
* **Only 18 of 2,034 trees are drawn from modelled branches.** 2,016 are six-triangle impostor cards, **0** are procedural canopy stems, 6 cards were dropped, **975** species were substituted and **5** instances were scaled out of band. The render's one visible tree is a bare card.
* **Four of 6 structures tiles in range have no structures file**, under the 57th Street and Columbus Circle interchanges.
* **Beyond 400 m the park surface sits under the terrain on 0.315 of 1,270 samples**, minimum **−3.382 m**, after a redrape that moved **235,952** vertices (J85). That band is Central Park's own ground.
* **Seven props across four kinds were wanted in range and have no asset**: 3 passenger-information sign, 2 misc structure, 1 artwork, 1 payphone.
* **Six park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, park grass, recreation grass, rink ice, bare ground (J40).
* **The crowd is an eighth of the ask**: the table wanted 804 vehicles and 4,227 people; 1,013 and 2,999 were simulated and **3,603** dropped — 1,229 pedestrians and 515 vehicles outside the radius, **1,165** pedestrians and 381 vehicles at the agent triangle budget, 202 pedestrians in the carriageway without crossing, 53 not on a walkable surface, 22 vehicles not on a carriageway, 16 pedestrians inside a building, 3 pedestrians and 1 vehicle above the observer, and **18 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a construction photograph, the model is the finished building | the chooser matches on place, subject terms and a minimum year, and has no evidence of whether the structure in the photograph is complete. J93's family in the time dimension | **verification — open** |
| the avenue's walls have no windows | 6,299 kit pieces drawn of 19,608 in range at a 1,030,689-triangle budget, and the nearer faces consume them; the further half of the canyon gets none | **performance — measured, and the clearest instance in the pass** |
| visible fraction 0.077 | a terracotta wall 31.8 m out; the walk moved 69.3 m and scored this as the best point available (J79) | verification — open |
| +5.18 stops, under-lit | a Seventh Avenue canyon at 19.4° sun elevation in March; declared with its number (J83) | verification — declared |
| p05 0.2973 against 0.0594, sd 0.649× | the render's canyon walls are lit where the photograph's are in full shade, because there is no per-building facade colour and no deep interior shadow in a flat-coloured slab (J66 remainder) | **data — open** |
| chroma 0.372×, mean 1.224×, p50 0.863× | no sky and no signage colour in the render's frame, and 0.462 stops of development between the two halves | reference + J83 |
| 18 of 2,034 trees from branches, 975 species substituted, 0 canopy stems | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| 4 of 6 structures tiles without a file | no structures file was built for those tiles | **data — open, four tiles unbuilt** |
| 0.315 of far park ground under the terrain, min −3.382 m | the terrain grid coarsens to 40 m beyond the near band, across Central Park's own survey shape (J85) | geometry — open, measured |
| 7 props across four kinds unmapped | no asset exists for those kinds | data |
| six park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 331 people where the table asked 4,227 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
