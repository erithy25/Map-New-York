# Hearst Tower

`landmark_hearst_tower` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Hearst Tower (Manhattan) May 2023.JPG by Benoît Prieur, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2023-05-20 15:45:06, 1280x2789. [Commons page](https://commons.wikimedia.org/wiki/File:Hearst_Tower_(Manhattan)_May_2023.JPG) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.76613, -73.98336 (NYC_TM -2802, 7337) at z 23.5 m NAVD88 | azimuth 339.1°, pitch +33.1° | 18 mm on 36 mm (49.3° horizontal, 90.0° vertical, portrait) | 708x1542. Position and heading both come from the photograph: its own EXIF camera GPS, **113.5 m** from the item's recorded viewpoint, and 339.1° is the bearing from there to the subject. The item's recorded azimuth of 20.0° is **40.9° away**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+33.1°**, and the top of the subject is still cut off: `lm_c_hearst_tower.5` stands 181 m above the lens at 56 m, **73° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the azimuth closed **18 m** ahead against the 28.2 m needed — so the camera was **moved 14.7 m** onto the nearest surveyed sidewalk, scored on the subject's sightline (11 of 13 rays at the point chosen). From there the azimuth is clear for **38.7 m** and the nearest built thing is `prop_lamp_cobra_davit_29` **12.4 m** away. Ground under the camera reads **21.909 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 21.74 to 22.51 m.

**Sun** — azimuth 253.7°, elevation 48.0° at 2023-05-20T15:45:06−04:00, from the photograph's own **EXIF DateTimeOriginal**; 880.1 W/m² direct normal, sky at strength 0.0322, Filmic, **+5.66 stops**, declared: *under-lit: the scene needed +5.66 stops to read as a picture, more than the 4 a photographer recovers hand-held*. The linear frame's median is **0.003564** against a target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,500,081 triangles: 4 building tiles (202,434 tris, none missing, none LOD-substituted), 6 landmark models of which 2 fall inside the 49.3° frame, 22,320 pavement polygons with **0 dropped**, 1,541 props, 5,632 kit pieces, 15 park-ground meshes over 187 surfaces with **2,814 faces cut** for landmark ground, 1 structures tile (21,408 tris) with **3 without a file**, 55 vehicles and 244 people, terrain 82,920 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the best facade in this pass: the diagrid is built, the Art Deco base is built, the probe and the catalogue agree to forty-three centimetres, and the frame is published 5.66 stops under-lit in sunshine the photograph does not have

**The geometry is right and distinctive.** The render carries Hearst Tower's diagrid: the four-storey triangular bays, the chamfered bird's-mouth corners where the diagonals meet the slab edges, the glass set back behind them. Below it sits the 1928 Art Deco base with its giant order of pilasters, its recessed window bays and its cornice line. Nothing else in this pass reproduces a facade this specific, and it reads immediately as the same building as the photograph.

**Two measurements confirm it.** The probe found **182.43 m** above a ground of 22.13 m over **43 of 43** rays, and the catalogue entry **4.0 m** away carries **182.0 m** — the two figures within half a metre of each other, and the second closest agreement in the pass after the George Washington Bridge. The plan extent measured off the object is **46.3 m by 45.8 m**. The sightline returns 13 rays, **13 clear, 11 on the subject**, visible fraction **0.846**.

**And the chroma matches almost exactly**: **0.0622** against the photograph's **0.0638**, a ratio of **0.975**.

**What separates the two halves is weather and exposure, not the model.** The photograph is overcast and wet — grey sky, reflective asphalt, no shadows. The render is in direct sun at 48° elevation with hard shadows across the sidewalk, because the sun position comes from the photograph's own EXIF timestamp and **nothing in this build reads historical weather**. On top of that the frame is **5.66 stops under-lit**: a street canyon in shade behind a glass tower reads almost no light, and the record declares the number as past hand-held recovery. Between them those two facts account for the median ratio of **0.731** and the mean of **0.79**, with the two development offsets **0.992 stops** apart (J83).

**The kit shortfall is the second largest in the pass.** **60,773** kit records were in range and **5,632** were drawn, capped at a 1,214,443-triangle budget with 2,500 more suppressed. On this sheet it costs less than elsewhere, because the diagrid and the base come from the landmark model rather than the kit — but the blocks up Eighth Avenue behind them are bare.

## What matches

* **The diagrid and the Art Deco base are both modelled** and both read correctly — the most specific facade geometry in the pass.
* **The probe's 182.43 m and the catalogue's 182.0 m** agree within half a metre on a 182 m tower (J74).
* **Chroma is 0.975 of the photograph's** — the closest colour match in the pass.
* **The sightline is strong**: 13 of 13 rays clear, 11 on the subject, visible fraction 0.846.
* **The clearance walk worked as designed**: an 18 m closure detected, 14.7 m onto real surveyed sidewalk, scored on the subject's sightline (J79).
* **The crosswalk, kerb line and corner geometry are right**, and the crowd stands on the sidewalk where it should.
* **The under-lit development is declared with its number** rather than smoothed (J83).
* **The day type is right and was read**: the crowd clock reads **Saturday** for 2023-05-20, which was a Saturday.
* **The landmark-ground rule did real work**: **2,814** park-ground faces cut.
* **The pavement is complete**: 22,320 polygons, **0 dropped**.

## What does not match

* **The weather is wrong, and cannot be right.** The photograph is overcast and wet; the render is in direct sun from the same timestamp, because nothing in this build reads historical weather.
* **The frame is 5.66 stops under-lit**, which the record states is past what a photographer recovers hand-held.
* **The median is 0.731× and the mean 0.79×**, most of it the 0.992-stop difference between the two developments (J83).
* **The top of the subject is cut off** at the 18 mm floor; the tower needs 73° of elevation at 56 m.
* **5,632 of 60,773 kit records were drawn** — the second largest shortfall in the pass — capped at 1,214,443 triangles with 2,500 suppressed, so the avenue behind the subject is bare shells.
* **Fifty-two per cent of the props are missing**: 1,541 placed of **3,182 in range**, with **1,412 dropped for the triangle budget** of 1,237,126, 9 on a suppressed building and 10 cards dropped.
* **1,126 tree rows did not fit** the props budget, and **0** of the 331 cards are procedural canopy stems.
* **Three of 4 structures tiles have no structures file**, under the Columbus Circle and 57th Street interchanges.
* **There is no park ground within 150 m to check** — 0 samples. Between 150 and 400 m the park surface sits under the terrain on **0.3017** of 179 samples (J85).
* **Sixteen props across seven kinds were wanted in range and have no asset**: 4 passenger-information sign, 3 artwork, 2 drinking fountain, 2 misc structure, 2 payphone, 2 vending machine, 1 parks building.
* **Six park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a thirteenth of the ask**: the table wanted 805 vehicles and 3,114 people; 884 and 3,000 were simulated and **3,573** dropped — 1,246 pedestrians and 321 vehicles outside the radius, **1,227** pedestrians and 425 vehicles at the agent triangle budget, 208 pedestrians in the carriageway without crossing, 47 not on a walkable surface, 38 vehicles not on a carriageway, 21 pedestrians above the observer, 7 inside a building, and **44 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the weather is wrong | the sun comes from the photograph's own EXIF timestamp and nothing in this build reads a historical sky or cloud cover, so an overcast wet photograph is rendered in the sunshine that timestamp implies | **reference — no source exists** |
| +5.66 stops, under-lit | a shaded street canyon behind a glass tower at 48° sun elevation; declared with its number (J83) | verification — declared |
| p50 0.731×, mean 0.79× | 0.992 stops of development between the halves, on top of the weather (J83) | reference |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 73° at 56 m | **verification — declared limit** |
| 5,632 kit pieces of 60,773 in range | the kit triangle budget at 1,214,443, plus 2,500 suppressed under landmark shells | **performance** |
| 1,541 props of 3,182 in range, 1,126 tree rows dropped | the props triangle budget at 1,237,126 | **performance** |
| 3 of 4 structures tiles without a file | no structures file was built for those tiles | **data — open, three tiles unbuilt** |
| 0.3017 of mid-field park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| 16 props across seven kinds unmapped | no asset exists for those kinds | data |
| six park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 244 people where the table asked 3,114 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
