# 30 Hudson Yards

`landmark_30_hudson_yards` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:30 Hudson Yards 2025 040.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-12-23 14:13:12, 1920x3412. [Commons page](https://commons.wikimedia.org/wiki/File:30_Hudson_Yards_2025_040.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75228, -73.99706 (NYC_TM -4001, 5824) at z 4.1 m NAVD88 | azimuth 302.6°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal, 32.3° vertical, portrait) | 784x1394. Position and heading both come from the photograph: its own EXIF camera GPS, **125.8 m** from the item's recorded viewpoint, and 302.6° is the bearing from there to the subject, 2.6° from the item's recorded azimuth. The lens stayed at 35 mm and the axis level, because the subject is 375 m away. **The clearance walk failed on this sheet and says so.** The recorded viewpoint was boxed in — the azimuth closed **40 m** ahead against the **80.0 m** the frame needs — so the camera was moved **32.0 m** along the view azimuth to the nearest point in open air, ranked on how much of the subject it sees (J79). The record then states: *No point within 80 m had 80 m of open air along the view azimuth with nothing built inside 8 m of the lens*. The frame it settled for is **closed off 96 m ahead**, and the nearest thing in it is `t_-5_5_park_recreation_grass` **3.4 m** away at 5.4° yaw and **−27.2° pitch** — a park-grass surface below and in front of the lens. Ground under the camera reads **2.487 m** NAVD88 from 16 heightmap samples within 5.0 m, range 1.87 to 4.99 m.

**Sun** — azimuth 213.2°, elevation 18.3° at 2025-12-23T14:13:12−05:00, from the photograph's own **EXIF DateTimeOriginal**; 625.7 W/m² direct normal, sky at strength 0.0424, Filmic, **+6.00 stops, clamped**. The linear frame's median is **0.000314** against a middle-grey target of 0.18, so the meter asked for **+9.16 stops** and the development held at the ceiling of 6 — *a scene this far from a photographable level is not developed into a picture of one*. The physical rule would have given **+1.25 stops**.

**In the scene** — 4,500,142 triangles: 10 building tiles (321,814 tris, none missing, none LOD-substituted), 8 landmark models of which 3 fall inside the 32.3° frame, 36,928 pavement polygons with **0 dropped**, 1,134 props, 5,785 kit pieces, 22 park-ground meshes over 220 surfaces, 4 structures tiles (65,356 tris), 69 vehicles and 248 people, terrain 105,044 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the worst frame in this queue: the camera ended up inside a torn park surface, the record knew the frame was closed 96 m ahead before it rendered, and the runner passed it as usable anyway

**The render is not a view of anything.** The lower half is filled by pale green and white planes folded into sharp wedges, seen from a few metres and edge-on; above them sit dark unlit masses and a sliver of brick. The record names the object: `t_-5_5_park_recreation_grass`, **3.4 m** from the lens, 27.2° below the axis. The pale green is the flat colour the park-ground builder authors for mown grass, kept because the texture catalogue has no photographic set for it (J40) — so the wedges filling this frame are recognisably a park lawn, torn into spikes and pushed through the camera.

**Everything downstream agrees that there is nothing to see, and the sheet was still published.** The walk reported that no point within 80 m satisfied its own rule. The sightline cast 13 rays: **0 clear, 0 on the subject**, all stopped at **86.6 m** on `t_-5_5_red_brick`, visible fraction **0.000**. The meter asked for nine stops and was clamped at six. The frame verdict from the runner is **mean 0.285, sd 0.2528, usable: true** — because the usability test reads frame statistics and has no access to any of the three failures above. That is the finding: **the decline mechanism exists and is wired to the wrong signal** (J92's other half).

**The exposure gap is the widest in the pass.** The render's development offset from the grey convention is **−3.038 stops** and the photograph's is **+1.265** — **4.303 stops** apart. Median **0.1597** against **0.6891**, a ratio of **0.232**. Nothing about that is a judgement on the build's lighting; it is the distance between an overcast December afternoon photographed at eye level and a camera buried in a lawn.

**And the probe measured the shed, not the tower.** `lm_c_hudson_yards.44`, **33.94 m** above a ground of 8.94 m, extent **191.4 m by 175.9 m** — a 191-metre-wide, 34-metre-tall object is the Eastern Yard's podium, while the catalogue entry 64.6 m away carries **387.1 m**. The aim then went to that object's mid-height, **16.7 m**, which is inside the podium. This is J94: the probe takes the member standing at the coordinate.

## What matches

* **Every failure is recorded before the fact.** The walk's refusal, the 96 m closure, the 3.4 m obstruction, the nine-stop meter reading and the 0.000 visible fraction are all in `render.json`, in plain words, with their numbers. Nothing here is hidden; what is missing is a rule that acts on them.
* **The camera stood where the photographer stood** and the bearing to the subject is 2.6° from the item's own azimuth.
* **The pavement is complete**: 36,928 polygons, **0 dropped**, including **20,594** white markings, 5,248 sidewalk, 5,087 roadbed, 3,678 curb, 835 crosswalk and 502 median.
* **The season is right and was read**: the props are placed with **bare canopies** for 23 December.
* **Trees are scaled from their own rows**: 237 placed, mean scale **0.938**, **0** out of band, 68 drawn from modelled branches.
* **Chroma is the one statistic that matches** — **0.0596** against **0.0547**, a ratio of **1.09** — because an overcast December photograph has almost no saturation either.
* **Agents carry mixed detail**: 5 vehicles at LOD1, and of 248 people **49 at LOD1 and 3 at LOD0**.

## What does not match

* **There is no subject in the frame.** Visible fraction **0.000**, 13 of 13 rays stopped at 86.6 m.
* **A park-grass surface stands 3.4 m from the lens, torn into spikes**, and fills the lower half of the picture. The redrape moved **100,422** vertices by up to **3.288 m** and down to **−3.503 m** on this tile set; a surface deformed by that much across a platform edge is what produces wedges like these.
* **The frame was passed as usable** on mean and standard deviation alone, with three recorded failures upstream of it.
* **The development is clamped six stops below its own meter reading**, 4.303 stops from the photograph's own development.
* **The probe measured a 33.94 m podium for a 387.1 m tower** and aimed the frame at 16.7 m (J94).
* **Six of 10 structures tiles in range have no structures file.**
* **Mid-field ground is under the terrain on 0.2967 of 273 samples**, minimum −1.153 m; near-field on 0.0748 of 548, minimum **−1.995 m** (J85).
* **34,255 kit records were in range and 5,785 were drawn**, capped at a 943,930-triangle budget.
* **3,493 tree rows did not fit** the props budget of 1,092,832 triangles, **0** of the 169 impostor cards are procedural canopy stems, and 4 cards were dropped.
* **Thirty-eight props across seven kinds were wanted in range and have no asset**: 21 misc structure, 6 artwork, 4 drinking fountain, 3 memorial, 2 vending machine, 1 billboard, 1 passenger-information sign.
* **Seven park-ground surface kinds fall back to the builder's flat colour** (J40) — and on this sheet that flat colour is most of the image.
* **The frustum finds the Hudson Yards composite at 386.1 m, 6.9° off axis**, the Javits Center at 747.6 m and the Lincoln Tunnel at 1,484.2 m; the subject itself has no separate model to find.
* **The crowd is a tenth of the ask**: the table wanted 854 vehicles and 2,773 people; 1,027 and 2,999 were simulated and **3,709** dropped — 1,470 pedestrians and 453 vehicles outside the radius, 779 pedestrians and 441 vehicles at the agent triangle budget, 316 pedestrians in the carriageway without crossing, 184 not on a walkable surface, 34 vehicles not on a carriageway, 4 vehicles and 2 pedestrians inside a building, and **25 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a torn park surface 3.4 m from the lens filling the lower half | the walk found no compliant point within 80 m and took the least bad one; the redrape had deformed that park surface by up to 3.288 m across the platform edge, so the least bad point is inside a spike | **geometry + verification — open** |
| the frame was passed as usable | the usability test reads the frame's mean and standard deviation and never reads the walk's own refusal, the 96 m closure or the 0.000 visible fraction | **verification — open, J92's other half** |
| visible fraction 0.000 | there is no line from any reachable point to this subject at eye level from the photograph's position; the walk says so | verification — open, J87 family |
| clamped at +6.00 against +9.16 asked, 4.303 stops from the photograph | a camera inside geometry reads almost no light; the clamp is declared (J83) | verification — declared clamp, open cause |
| probe 33.94 m for a 387.1 m subject, aim at 16.7 m | the probe takes the member standing at the coordinate — here the Eastern Yard podium, 191.4 m wide (J94) | **verification — open, J94** |
| 6 of 10 structures tiles without a file | no structures file was built for those tiles | **data — open, six tiles unbuilt** |
| 0.2967 of mid-field ground under the terrain | the 2013 bare-earth DEM under the Hudson Yards platform (J85) | geometry — open, measured |
| 34,255 kit records in range, 5,785 drawn | the kit triangle budget at 943,930 | performance |
| 3,493 tree rows dropped, 0 canopy stems | the props triangle budget at 1,092,832 triangles | performance + declared rule |
| 38 props across seven kinds unmapped | no asset exists for those kinds | data |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 248 people where the table asked 2,773 | the agent triangle budget plus the placement rules, each with its count | performance + verification |

## What this sheet is good for

Nothing about 30 Hudson Yards. It is the strongest argument in the pass for one cheap repair: the runner's usability test should read the record it is standing on. Three separate measurements — the walk's own refusal, a 96 m closure against an 80 m requirement, and a visible fraction of 0.000 — were all written before the image was judged, and the judgement ignored all three.
