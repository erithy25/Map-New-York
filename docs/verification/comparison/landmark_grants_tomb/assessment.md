# General Grant National Memorial (Grant's Tomb)

`landmark_grants_tomb` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Grant's Tomb Mar 2026 03.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-03-14 14:40:17, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Grant%27s_Tomb_Mar_2026_03.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.81232, -73.96344 (NYC_TM -1134, 12473) at z 40.1 m NAVD88 | azimuth 16.1°, pitch +0.0° | 35 mm on 36 mm (42.2° horizontal, 54.4° vertical, portrait) | 904x1206. Position and heading both come from the photograph: its own EXIF camera GPS, **33.2 m** from the item's recorded viewpoint, and 16.1° is the bearing from there to the subject; the item's recorded azimuth of 0.0° is 16.1° away. The lens stayed at 35 mm and **the axis stayed level**, and the record explains the choice: the subject is 117 m away and would need +8° of tilt, *a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion*. The camera was not moved: the eye point stands on `t_-2_12_park_park_ground_grass` and this position is the photograph's own fix. The azimuth is clear for **117.1 m** against the 58.5 m needed, and the nearest built thing is that grass surface **2.6 m** away at −27.2° pitch. Ground under the camera reads **38.473 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 38.42 to 39.22 m.

**Sun** — azimuth 212.7°, elevation 41.7° at 2026-03-14T14:40:17−04:00, from the photograph's own **EXIF DateTimeOriginal**; 851.0 W/m² direct normal, sky at strength 0.0332, Filmic, **+0.49 stops and not clamped**. The linear frame's median is **0.128271** against a middle-grey target of 0.18, and the physical rule would have given **+0.05 stops** — the two rules within half a stop of each other, which is rare (J83).

**In the scene** — 3,771,585 triangles: 6 building tiles (287,184 tris, none missing, none LOD-substituted), 2 landmark models of which 1 falls inside the 42.2° frame, 17,119 pavement polygons with **0 dropped**, 1,412 props, 2,557 kit pieces, 22 park-ground meshes over 414 surfaces with **314 faces cut** for landmark ground, 3 structures tiles (21,568 tris) with **3 without a file**, 53 vehicles and 388 people, terrain 82,502 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the first honest 1.000 in this pass: thirteen of thirteen rays land on the mausoleum's own fabric, the dome and colonnade are unmistakable, and the granite plaza in front of it is a hill of grass

**The monument is right.** A cubic granite base, a colonnaded drum above it and a stepped conical dome on top — the render reads as Grant's Tomb at 117 m without having to be told. The probe measured **34.93 m** above a ground of 40.34 m over **42 of 43** rays, plan extent **18.1 m** square, against a catalogue entry 14.3 m away carrying **45.72 m** (the dome's full height above its own ground). And the sightline returns **13 rays, 13 clear, 13 on the subject**, visible fraction **1.000**, all landing on `lm_b_grants_tomb.16` at 112.6 m against the subject's own coordinate at 117.0 m.

**That 1.000 is worth distinguishing from the one on `landmark_castle_williams`.** There, thirteen rays landed on a tile mesh spanning an island and the fort was absent. Here every ray lands on a member of the mausoleum's own model, four metres nearer than the recorded coordinate, and the mausoleum is in the middle of the frame. The same number, earned two different ways — which is exactly why J94 is about the objects the sightline is allowed to count, not about the count.

**And then the plaza.** The photograph's lower two thirds is a broad granite-paved forecourt under a double row of bare plane trees, the paving joints running to the portico steps. The render's lower two thirds is **a pale green grass surface rising steeply toward the monument**, with tree shadows falling across it. 17,119 pavement polygons are in the scene and **0 were dropped**, so the paving exists in the data; what the frame shows at that spot is the park-ground grass mesh the camera is standing on — the record names it as the surface under the eye point and as the nearest built thing, 2.6 m away at 27.2° below the axis. Within 150 m only **0.0309** of 680 samples sit under the terrain, so this is not the clearance fault of J85 — it is a park polygon covering a paved forecourt.

**Everything else is close.** Mean **0.885×**, median **0.926×**, chroma **0.671×**, contrast **0.709×**, with the two development offsets **0.241 stops** apart. The bare canopy is right for 14 March and **82 of 1,017 trees are drawn from modelled branches**.

## What matches

* **The dome, the colonnaded drum and the cubic base** all read correctly at 117 m.
* **Visible fraction 1.000, honestly earned**: 13 of 13 rays on the mausoleum's own fabric.
* **The probe and the catalogue are consistent**: 34.93 m measured on the member the rays hit against 45.72 m for the whole monument 14.3 m away.
* **The level axis is a declared choice with a reason**: +8° of tilt was available and refused so that proportion stays comparable.
* **The two development rules are within half a stop** — metered +0.49 against a physical +0.05 (J83).
* **The season is right and was read**: bare canopies for 14 March, and 82 trees drawn from modelled branches.
* **The day type is right**: the crowd clock reads **Saturday** for 2026-03-14, which was a Saturday.
* **The crowd is substantial**: 388 people drawn of 1,406 simulated, the second largest in this queue.
* **Neither kit nor props were capped**: 2,557 kit pieces of 3,408 with 851 suppressed under the landmark shell, and 1,412 props of 1,503.
* **The pavement data is complete**: 17,119 polygons, **0 dropped**, including 5,555 white markings, 4,104 sidewalk, 3,938 roadbed and 2,404 curb.

## What does not match

* **The granite forecourt renders as a grass slope.** The paving is in the data and a park-ground polygon is drawn over it.
* **No portico steps, pediment or inscription.** The photograph's entrance is a flight of steps between paired columns under an inscribed entablature; the render's base meets the grass flat.
* **The double row of plane trees is not a row.** 935 of the 1,017 trees are impostor cards scattered rather than the formal allée the photograph shows, and **0** are procedural canopy stems.
* **Chroma is 0.671 of the photograph's** and contrast **0.709×** — no deep blue sky, no granite grain, no dark doorway.
* **All 3 structures tiles in range have no structures file**, and the 3 that are imported carry 21,568 triangles.
* **Park ground was not built for 2 tiles** inside the 620 m ground radius.
* **Beyond 400 m the park surface sits under the terrain on 0.261 of 793 samples**, minimum **−7.017 m** — the deepest single under-reading in this queue — after a redrape that moved **422,828** vertices (J85).
* **Nine props across five kinds were wanted in range and have no asset**: 3 artwork, 2 drinking fountain, 2 memorial, 1 parks building, 1 parks comfort station. The memorial's own flanking sculpture is in those classes.
* **Eight park-ground surface kinds fall back to the builder's flat colour** (J40) — and the grass over the forecourt is one of them.
* **378 tree species were substituted**, 1 instance scaled out of band and 12 impostor cards dropped.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the granite forecourt renders as grass | the open-space survey's park polygon covers this area and the park builder fills it with grass, with only 314 faces cut where the landmark supplies its own ground; the 17,119 pavement polygons are present and none was dropped. Not the J85 clearance fault — within 150 m only 0.0309 of samples sit under the terrain | **data — open, measured** |
| no portico steps, pediment or inscription | the landmark builder models massing; steps, entablature sculpture and incised lettering are not classes it authors | geometry — declared scope |
| the allée is scattered cards, not a row | the props budget spends its triangles on cards at this density, and the survey rows are placed individually rather than as a formal planting | performance + **data** |
| chroma 0.671×, sd 0.709× | no sky colour, no granite grain and no dark opening in the render's frame (J40, J66 remainder) | **declared decision + data, open** |
| 3 of 3 structures tiles without a file | no structures file was built for any tile in range | **data — open, three tiles unbuilt** |
| park ground missing on 2 tiles | not built for those tiles; the record names both | **data — open, two tiles unbuilt** |
| 0.261 of far park ground under the terrain, min −7.017 m | the terrain grid coarsens to 40 m beyond the near band over Riverside Park's steep slope to the Hudson (J85) | geometry — open, measured |
| 9 props across five kinds unmapped | no asset exists for those kinds | data |
| eight park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 378 species substituted, 12 cards dropped | the tree catalogue does not hold most species surveyed here | data |
