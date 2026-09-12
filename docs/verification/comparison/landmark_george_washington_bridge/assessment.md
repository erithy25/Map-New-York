# George Washington Bridge

`landmark_george_washington_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:GWB southeast leg work uncut 2021 jeh.jpg by Jim.henderson, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2021-04-28 10:52:39, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:GWB_southeast_leg_work_uncut_2021_jeh.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.84720, -73.94500 (NYC_TM 422, 16347) at z 21.1 m NAVD88 | azimuth 340.4°, pitch +0.3° | 26 mm on 36 mm (70.1° horizontal, 50° vertical) | 1280x854. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **367.5 m** away, past the 250 m rule. The recorded azimuth of 340.4° agrees with the bearing to the subject to **0.1°**. The lens was **widened from 35 mm to 26 mm** and the axis tilted **+0.3°**: the top of `lm_b_george_washington_bridge.109` stands 165 m above the lens at 401 m, **22° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was not moved — open air, azimuth clear for **150 m** against the 80.0 m needed — and the nearest built thing is `t_0_16_park_park_ground_grass` **6.8 m** away at −12.5° pitch. Ground under the camera reads **19.47 m** NAVD88 from 16 heightmap samples within 5.0 m, range 19.34 to 19.7 m.

**Sun** — azimuth 126.5°, elevation 52.7° at 2021-04-28T10:52:39−04:00, from the photograph's own **EXIF DateTimeOriginal**; 897.7 W/m² direct normal, sky at strength 0.0317, Filmic, **+0.69 stops and not clamped**. The linear frame's median is **0.111563** against a middle-grey target of 0.18 (J83); the physical rule would have given 0.0.

**In the scene** — 2,376,710 triangles: 7 building tiles (204,112 tris) with **2 missing**, 1 landmark model, in the frame, 25,414 pavement polygons with **0 dropped**, 2,272 props, 141 kit pieces, 24 park-ground meshes over 302 surfaces, 2 structures tiles (1,988 tris) with **7 without a file**, 88 vehicles and 14 people, terrain 102,152 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the best-measured landmark in this pass: the probe's 183.9 metres and the catalogue's 184.1 agree to twenty centimetres, and the two frames develop to within a tenth of a stop of each other

**Three independent numbers land on top of each other.** The probe measured the New York tower at **183.9 m** above a ground of 2.4 m over **43 of 43** rays. The catalogue entry carries **184.1 m** — and it was **not used**, because it sits 523.9 m away, past the 120 m the rule looks in, so the record states that the height came from the geometry (J74). Two independent sources agreeing to 0.2 m on a 184 m tower is the strongest single confirmation in the pass that the landmark geometry is built to its stated dimensions.

**And the exposure pairing is the closest in the pass.** Mean **1.014×**, median **1.03×**, and the two development offsets from the grey convention — **+0.238** for the render and **+0.146** for the photograph — are **0.092 stops** apart. Chroma **0.824×**.

**The bridge itself reads correctly.** The tower's steel frame, the main cable slung over it, the suspenders dropping to the deck, the deck running across the frame and the approach viaduct beyond are all in place and at the right proportions for a 401 m standoff. The sightline is sound: 13 rays, **13 clear, 8 on the subject**, 5 into nothing where the fan crosses open water beside the tower.

**What the sheet cannot compare is texture, because the reference is a close-up of steelwork.** The photograph stands under the tower: dense riveted lattice in rust and grey, filling the frame, with maintenance plant at its foot. The render's tower at 401 m is a clean thin frame with no rivet, no paint wear and no plate detail — which is the right level of detail for that distance and simply not what the photograph shows.

**Two render faults are visible and measured.** The foreground is a **vast featureless pale roadway** with a single dashed line, and on the right a **smooth faceted green mass** — Fort Washington Park's slope — rises and cuts into it. The numbers name the second one: beyond 400 m the park surface sits under the terrain on **0.2814** of 2,022 samples, minimum **−6.518 m** against a maximum of **+9.408 m** in the same band — a sixteen-metre spread — after a redrape that moved **634,237** vertices (J85).

**The flattest render in the pass.** Standard deviation **0.0919** against the photograph's **0.3209**, a ratio of **0.286**, and a fifth percentile of **0.3904** against **0.0619**: there is no dark value anywhere in the frame, where the reference is half steel in its own shadow.

## What matches

* **The probe and the catalogue agree to 0.2 m** on a 184 m tower, with the catalogue correctly refused at 523.9 m (J74).
* **The development offsets are 0.092 stops apart** — the closest pairing in the pass — with mean 1.014× and median 1.03× (J83).
* **The bridge's tower, main cable, suspenders, deck and approach all read** at 401 m.
* **The sightline is sound**: 13 of 13 rays clear, 8 on the subject, clear fraction **1.0**.
* **The camera needed no intervention** and the recorded azimuth agrees with the bearing to the subject to 0.1°.
* **The kit was fully placed**: 141 of 141 in range, nothing capped, nothing suppressed.
* **Props were not capped**: 2,272 placed of 2,289 in range, **0** cards dropped.
* **Near-field ground is sound**: within 150 m, **0.0048** of 413 park-surface samples sit under the terrain.
* **The pavement is complete**: 25,414 polygons, **0 dropped**, including **13,726** white markings, 6,240 roadbed, 2,787 curb and 1,462 sidewalk.

## What does not match

* **The reference is a close-up of the tower's steelwork** and the render is a 401 m view, so no texture, rivet or paint comparison is possible on this sheet.
* **Contrast is 0.286 of the photograph's** — the flattest render in the pass — with a fifth percentile of **0.3904** against **0.0619**.
* **A featureless pale roadway fills the foreground**, with one dashed line and no kerb detail, manhole or joint pattern in the near field.
* **A smooth faceted green mass cuts into that roadway** on the right: beyond 400 m the park surface is **0.2814** under the terrain over 2,022 samples, minimum **−6.518 m**, maximum **+9.408 m** (J85).
* **Seven of 9 structures tiles have no structures file**, and the 2 that do carry **1,988 triangles** in total.
* **Two of 7 building tiles have no shell file**, and park ground was not built for 5 tiles.
* **Not one of 2,157 trees is drawn from modelled branches.** All are cards, **851** species were substituted, only **33** are procedural canopy stems, and the mean scale of **0.853** undersizes the canopy.
* **Fourteen people and 88 vehicles.** The table asked for 363 people and 617 vehicles; 602 and 940 were simulated, and **187 pedestrians were dropped for standing where the planimetric data has no sidewalk** — which on the Hudson River Greenway is the greenway.
* **Every vehicle is at LOD2** and every pedestrian too.
* **Fourteen props across four kinds were wanted in range and have no asset**: 11 misc structure, 1 artwork, 1 parks building, 1 parks comfort station.
* **Eight park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The frustum reports the bridge composite at 813.9 m, 32.9° off axis**, which is the composite centroid — mid-span over the river — rather than the tower 401 m away on the axis.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a close-up of steelwork | the chooser matched the bridge's name; the photograph is of maintenance work under the tower (J93's family, on level of detail rather than subject) | **verification — open** |
| sd 0.286×, p05 0.3904 against 0.0619 | nothing in the render's frame is dark, because the tower at 401 m occupies little of it and the foreground is lit roadway | consequence of the pairing |
| a featureless foreground roadway | the near field here is the Henry Hudson Parkway shoulder, whose surveyed markings are drawn further out; joint patterns and kerb detail are not modelled | data + declared scope |
| a faceted park mass cutting the roadway | the terrain grid coarsens to 40 m beyond the near band while Fort Washington Park's steep survey shape keeps its form; the redrape moved 634,237 vertices and cannot close a 16 m spread (J85) | **geometry — open, measured** |
| 7 of 9 structures tiles without a file | no structures file was built for those tiles | **data — open, seven tiles unbuilt** |
| 2 of 7 building tiles without a shell, 5 without park ground | no files were built for those tiles; the record names them | **data — open, measured** |
| 0 of 2,157 trees from modelled branches, 851 species substituted, mean scale 0.853 | the props budget spends its triangles on cards at this density, a tree catalogue that does not hold most species surveyed here, and exported size classes that undersize the surveyed heights | performance + **data** |
| 14 people, 187 dropped off the walkable surface | the Hudson River Greenway is not a walkable surface in the planimetric data | **data — open, measured** |
| every agent at LOD2 | the LOD rule picks by distance and everything in range sits beyond the nearer bands | performance |
| 14 props across four kinds unmapped | no asset exists for those kinds | data |
| eight park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| the composite reported 32.9° off axis at 813.9 m | the frustum test uses a landmark composite's centroid, which for a bridge is mid-span | verification — open |
