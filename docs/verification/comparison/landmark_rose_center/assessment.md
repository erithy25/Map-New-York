# Rose Center for Earth and Space

`landmark_rose_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Upper West Side, New York, NY, USA - panoramio (28).jpg by kajikawa, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0), taken 2013 — **the year and nothing finer** — 1920x1434. [Commons page](https://commons.wikimedia.org/wiki/File:Upper_West_Side,_New_York,_NY,_USA_-_panoramio_(28).jpg) — the photograph's own view direction is derived from the image at **high** confidence. **It is an interior photograph**: the Cullman Hall of the Universe inside the glass cube, with its ring of exhibit consoles, the Willamette meteorite on its plinth, the sweeping ramp and stair, and the cube's own soffit overhead.

**Camera** — 40.781936, -73.974698 (NYC_TM -2140, 9127) at z 27.4 m NAVD88 | azimuth 110.0°, pitch +4.8° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1208x902. The camera stands on **the item's recorded viewpoint**, and the record gives the same reason it gives on the Moynihan and Queens Museum sheets: *this photograph's own EXIF GPS is 89 m away, but the eye point there is inside `lm_c_american_museum_natural_history.7` (a ray straight up from the eye point hits its roof)*. The recorded azimuth of 110.0° agrees with the bearing to the subject to **0.1°**. The walk then **moved the camera 61.2 m** onto the nearest surveyed median polygon: the recorded viewpoint is boxed in, closed off **11 m ahead** against the **65.1 m** this frame needs. From there the view is clear for **74.0 m**, and the nearest built thing in the frame is `prop_lamp_cobra_davit_274` **8.2 m** away at +9° yaw and 0° pitch. The ground reads 25.77 m NAVD88, the 10th percentile of 113 samples within 12 m, range 25.7 to 26.01 m.

**Sun** — azimuth 107.9°, elevation 54.6° at 2013-06-21T10:30:00−04:00. The instant is **chosen, not measured** (J80): the photograph carries a year, 21 June is the project-wide fallback date, and 10:30 is the hour whose bearing, 108°, comes closest to the view azimuth of 110° — **2° off**, the closest agreement any chosen instant achieves in the pass. 903.7 W/m² direct normal, Filmic, **+4.30 stops** metered and unclamped against a linear median of **0.009122** and a target of **0.18**. The record declares it **under-lit** — *more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by*. The physical rule would have given **0.0 stops**. Per J80 the luminance comparison here is not evidence about the render.

**In the scene** — 4,500,241 triangles: 4 building tiles (276,676 tris, 0 missing, 0 LOD-substituted), 4 landmark models of which 2 can fall inside the 54.4° frame, 15,919 pavement polygons, 776 props, 4,230 kit pieces, 16 park-ground meshes over 525 surfaces, 1,404 triangles of structures, 89 vehicles and 394 people.

## Verdict — the third interior reference in the pass, and a street lamp 8.2 m from the lens hides the glass cube

**The cube was measured and is not in the picture.** The probe found fabric on **43 of 43 rays** and measured **33.46 m** above a ground of 20.37 m on `lm_c_american_museum_natural_history.12`, whose plan extent is **39.7 m by 39.7 m** — square in plan, which is the Rose Center's own shape and nothing else in the museum's footprint is. So the model carries the cube, at the right place, roughly the right size and the right height. And **eight of thirteen** sightline rays stop at **8.2 m** on `prop_lamp_cobra_davit_274`: a single cobra-head lamp standard, planted on the median the walk moved the camera onto, cuts the visible fraction to **0.385**. The five rays that get through land on a different member at 73.5 m. The published frame shows the museum's limestone 81st Street elevation with its arcaded ground floor, street trees, lawn and the park wall — a good picture of the wrong elevation.

**And the reference is an interior, for the third time.** The record's detector fired again — the photograph's own GPS puts the eye inside a landmark model's roof — and the chooser used the photograph anyway. Three sheets written so far are paired this way: Moynihan Train Hall, the Queens Museum and this one (J100). For a build that declares no interiors anywhere except volumes visible from the street through glass (B10, I5), a photograph taken inside the subject cannot be compared at all, and the four ratios the sheet publishes — mean **1.416**, sd **1.09**, p50 **1.355**, chroma **1.387** — are arithmetic across a limestone street elevation and an exhibition hall.

**The chosen instant is the best-aimed one in the pass and the frame is still under-lit.** J80's chooser had a year and nothing else, picked 10:30 on 21 June, and got the Sun's bearing within **2°** of the view azimuth — the tightest agreement any chosen instant reaches. The frame still needed **+4.30 stops**, because a westward-facing wall on Columbus Avenue at 10:30 stands in its own shade whatever the Sun's bearing. That is worth stating plainly: the hour chooser did its job and the geometry of the street beat it.

## What matches

* **The cube is modelled** — 39.7 m square in plan, 33.46 m tall, on 43 of 43 probe rays.
* **The aim** — recorded azimuth against measured bearing at **0.1°**, and the chosen Sun within **2°** of the view direction (J80).
* **The museum's own elevation is good.** Limestone, an arcaded ground floor, a regular upper window grid, the park wall and the lawn are all in the render and all in the right relation.
* **Central Park's drives are car-free** — **8 vehicles dropped** for standing on East, West, Terrace or Center Drive (J95).
* **2,328 faces were cut** out of the park ground for the landmark's own ground plate.
* **The park ground is close near the camera** — within 150 m, **998 samples**, an under-fraction of **0.0782**, a median clearance of **0.198 m**.
* **The fleet is an Upper West Side fleet** — 31 sedans, 20 SUVs, 12 yellow taxis, 9 black cars, 7 boro taxis, 4 vans, 3 box trucks, **2 Sanitation trucks**, 1 bus.
* **15,919 pavement polygons and none dropped**, including **5,617 sidewalk** — more sidewalk than roadbed, which is what this block is.

## What does not match

* **The reference is an interior and this build has no interiors** (B10, I5, J100).
* **The glass cube is not in the frame** — one cobra-head lamp 8.2 m from the lens blocks eight of thirteen rays.
* **The four published ratios compare a street elevation with an exhibition hall.**
* **Published under-lit at +4.30 stops** on a **chosen** instant, so the luminance comparison is not evidence about the render (J80, J83).
* **Props were capped to one in five** — **776 placed of 3,811 in range** at a **1,114,917-triangle** budget, **2,933 dropped for budget**, **2,633** of them tree rows, 9 impostor cards dropped.
* **Kit was capped to under a quarter** — **4,230 of 17,420 in range** at a **1,049,235-triangle** budget, and **1,524 further pieces suppressed** under landmark shells; the openings are drawn rather than cut (Stage 34 / J51).
* **Both tiles in range have no structures file** — 2 tiles, **2 without a file**, **1,404 triangles** — directly over the 81st Street–Museum of Natural History station, whose mezzanine is part of the museum.
* **258 of the 464 trees are a substituted species** and **7** are scaled outside the allowed band.
* **13 props across five kinds in range have no asset** — 5 drinking fountains, 3 memorials, 3 vending machines, 1 artwork, 1 parks building.
* **739 agents were dropped** — 414 pedestrians outside the radius, 156 vehicles outside the radius, **89 pedestrians in the carriageway without crossing**, **33 off a walkable surface** (J101), 26 vehicles at the agent triangle budget, 8 riderless bodies, 8 on a car-free park drive, 5 vehicles off the carriageway.
* **Between 150 and 400 m the park ground reads under the terrain on 0.1722 of 511 samples**, worst **−3.413 m**; beyond 400 m **0.1494** over 609 samples. The redrape moved **477,007** vertices, up to 1.155 m up and 1.165 m down.
* **No cloud**, and the reference has no sky in it at all.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is an interior | the chooser paired a photograph taken inside the subject with an exterior-only build, although the record detected that its GPS lies inside a landmark model's roof; three sheets written so far are paired this way (B10, I5, J100) | **verification — open (J100), and the evidence was already in the record** |
| the cube is not in the frame | one rule-placed cobra-head lamp 8.2 m from the lens blocks eight of thirteen rays, on the median the walk moved the camera onto (J79, J56) | **verification + data — open** |
| the four ratios compare unrelated images | comparison statistics are computed for every sheet regardless of whether the pair is comparable (J100) | verification — open (J100) |
| published under-lit at +4.30 stops | a westward-facing wall on Columbus Avenue at 10:30 stands in its own shade; the hour was chosen and got within 2° of the view azimuth, and the street's geometry beat it (J80, J83) | verification — declared, and correct |
| 776 props of 3,811, 2,633 tree rows dropped | the props triangle budget at 1,114,917 | performance |
| 4,230 kit pieces of 17,420, 1,524 more suppressed | the kit triangle budget at 1,049,235, plus the landmark shell replacing the tile's buildings | performance + declared decision |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| both tiles without a structures file | those tiles are unbuilt, over the 81st Street–Museum of Natural History station | **data — open** |
| 258 substituted species, 7 out of band | the species lists do not cover this stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| 13 props across five kinds unmapped | no asset exists for those kinds | data |
| 33 pedestrians off a walkable surface | the crowd's walkable test reads only the road network's surfaces, so the museum's lawn and Central Park's paths are unwalkable (J101) | verification — open (J101) |
| under-fraction 0.1722 mid-range | the park builder drapes on its own heightmap and the scene's differs; the redrape leaves a −3.413 m tail (J71) | geometry — open, bounded |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
