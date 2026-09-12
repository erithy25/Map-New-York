# Solomon R. Guggenheim Museum

`landmark_guggenheim` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Guggenheim (5957915634).jpg by Kevin Dooley from Chandler, AZ, USA, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2011-06-05 11:14, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Guggenheim_(5957915634).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.78280, -73.95924 (NYC_TM -819, 9218) at z 34.9 m NAVD88 | azimuth 41.3°, pitch +10.5° | 18 mm on 36 mm (90.0° horizontal, 74° vertical) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **65.9 m** from the item's recorded viewpoint, and 41.3° is the bearing from there to the subject. The item's recorded azimuth of 316.6° is **84.7° away**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+10.5°**, and the top of the subject is still cut off: `lm_c_guggenheim.5` stands 28 m above the lens at 30 m, **43° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the azimuth closed **8 m** ahead against the 20.0 m needed — so the camera was **moved 45.4 m** onto the nearest surveyed roadbed, scored on the subject's sightline (6 of 13 rays at the point chosen). From there the azimuth is clear for **60 m** and the nearest built thing is `prop_lamp_park_twin_29` **17.4 m** away. Ground under the camera reads **33.265 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 32.58 to 34.31 m.

**Sun** — azimuth 123.2°, elevation 62.1° at 2011-06-05T11:14−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 923.7 W/m² direct normal, sky at strength 0.0309, Filmic, **+1.09 stops and not clamped**. The linear frame's median is **0.084814** against a middle-grey target of 0.18 (J83); the physical rule would have given 0.0.

**In the scene** — 4,500,118 triangles: 4 building tiles (284,244 tris, none missing, none LOD-substituted), 3 landmark models of which 1 falls inside the 90.0° frame, 15,020 pavement polygons with **0 dropped**, 877 props, 4,065 kit pieces, 13 park-ground meshes over 451 surfaces, 2 structures tiles (2,364 tris) with **2 without a file**, 61 vehicles and 315 people, terrain 81,608 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the reference is a high-key black-and-white abstract, so every tonal figure on this sheet is void, and the chroma ratio of 1044.0 is the number that says so

**Read the reference's own statistics.** Median **1.0**. Ninety-fifth percentile **1.0**. Fifth percentile **0.0**. Chroma **0.0001**. Development offset **+2.474 stops** above the grey convention. That is not a photograph of a building under daylight — it is a heavily processed monochrome: the rotunda's underside as black curves against pure white, with the GUGGENHEIM lettering running across it. More than half the image is clipped white and its colour content is one ten-thousandth.

**Which makes the comparison arithmetic collapse loudly.** The chroma ratio comes out at **1044.0**, mean at 0.635, median at 0.495, and the two development offsets are **2.255 stops** apart. None of those numbers is evidence about this build. This is a fourth axis of the reference fault recorded as **J93**: the chooser has no evidence of a photograph's scale, its subject, its date — or its **processing**. A monochrome high-key image can never be compared with a physically metered render, and the tell is in the reference's own frame statistics, which the pipeline already computes and does not test.

**The render meanwhile is a fair Fifth Avenue.** Looking north-east up the avenue: the park's green on the left, a double row of street trees with **83 of 409 drawn from modelled branches**, the sidewalk and kerb, pedestrians at the park wall, and at the right edge **the Guggenheim's rotunda with its stacked ribbon bands** — modelled, recognisable, and 48.4° off the frame's axis because the walk had to move 45.4 m to find open air.

**The subject is half-seen, and honestly reported.** 13 rays, **9 clear, 6 on the subject**, blocked at **24.6 m** by `prop_tree_honeylocust_large_12`: visible fraction **0.462**. The probe measured **29.9 m** above a ground of 32.48 m over 43 of 43 rays against a catalogue entry 8.7 m away carrying **41.6 m**, which puts this sheet in the J94 survey — the object at the coordinate is the rotunda drum rather than the whole museum.

## What matches

* **The rotunda's spiral bands are modelled** and read at the right edge of the frame.
* **The probe is complete**: 43 of 43 rays, with the plan extent measured off the object (61.3 m by 43.4 m).
* **The clearance walk worked as designed**: an 8 m closure detected, 45.4 m onto real surveyed roadbed, scored on the subject's sightline (J79).
* **The development is metered and unclamped**, +1.09 stops from a median linear luminance of 0.084814.
* **The sightline verdict is honest**: 0.462, with the blocking honeylocust named at 24.6 m.
* **The car-free rule works here** — **5 vehicles dropped** because the road graph put them on Central Park's drives (J95's rule, inside its one polygon).
* **The day type is right and was read**: the crowd clock reads **Sunday** for 2011-06-05, which was a Sunday.
* **Near-field ground is sound**: within 150 m, **0.003** of 332 park-surface samples sit under the terrain, median **+0.196 m**.
* **The canopy is good for a street**: 83 trees from modelled branches, mean scale **0.966**, **0** out of band.
* **The pavement is complete**: 15,020 polygons, **0 dropped**.

## What does not match

* **Every tonal figure on this sheet is void**, because the reference is a clipped monochrome: median 1.0, p95 1.0, chroma 0.0001, development offset +2.474 stops (J93).
* **The subject sits 48.4° off the frame's axis** at the right edge, because the walk had to move 45.4 m to find a point in open air.
* **The top of the subject is cut off** at the 18 mm floor; it needs 43° of elevation at 30 m.
* **Visible fraction 0.462**, a street tree taking seven of the thirteen rays.
* **The probe's 29.9 m against a 41.6 m catalogue entry 8.7 m away** (J94).
* **Fifty-nine per cent of the props are missing**: 877 placed of **2,140 in range**, with **1,126 dropped for the triangle budget** of 1,143,793 and 13 cards dropped.
* **4,065 of 23,645 kit records were drawn**, capped at a 1,042,144-triangle budget, with 941 suppressed under landmark shells.
* **1,047 tree rows did not fit** the props budget, and **0** of the 326 cards are procedural canopy stems.
* **Two of 4 structures tiles have no structures file**, and the 2 that do carry **2,364 triangles** — under the Lexington Avenue line.
* **Beyond 400 m the park surface sits under the terrain on 0.2824 of 563 samples**, minimum **−2.776 m**, after a redrape that moved **410,951** vertices (J85).
* **Eight props across five kinds were wanted in range and have no asset**: 4 drinking fountain, 1 artwork, 1 parks building, 1 parks comfort station, 1 passenger-information sign.
* **Five park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a fifth of the ask**: the table wanted 315 vehicles and 1,622 people; 366 and 1,813 were simulated and **1,801** dropped — **704** pedestrians and 89 vehicles at the agent triangle budget, 596 pedestrians and 188 vehicles outside the radius, 157 pedestrians in the carriageway without crossing, 36 not on a walkable surface, and **22 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| every tonal figure is void | the reference is a clipped monochrome and the chooser tests nothing about processing; the reference's own frame statistics — median 1.0, chroma 0.0001 — are already computed and not checked. A fourth axis of J93 | **verification — open, J93** |
| the subject is 48.4° off axis at the frame edge | the recorded viewpoint was closed off at 8 m and the nearest open-air roadbed is 45.4 m away, which changes the bearing; the walk took the best point it could score (J79) | verification — open |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 43° at 30 m | **verification — declared limit** |
| visible fraction 0.462 | a large honeylocust 24.6 m out takes seven of thirteen rays; the walk weighs built fabric and not trees (J88's family) | verification — open |
| probe 29.9 m against a 41.6 m catalogue entry | the probe took the object at the coordinate, the rotunda drum rather than the museum (J94) | verification — open, J94 |
| 877 props of 2,140 in range, 1,047 tree rows dropped | the props triangle budget at 1,143,793 | **performance** |
| 4,065 kit pieces of 23,645 in range | the kit triangle budget at 1,042,144, plus 941 suppressed under landmark shells | **performance** |
| 2 of 4 structures tiles without a file | no structures file was built for those tiles | **data — open, two tiles unbuilt** |
| 0.2824 of far park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band across Central Park (J85) | geometry — open, measured |
| 8 props across five kinds unmapped | no asset exists for those kinds | data |
| five park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 315 people where the table asked 1,622 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
