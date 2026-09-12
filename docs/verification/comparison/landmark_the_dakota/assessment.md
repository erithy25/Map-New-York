# The Dakota

`landmark_the_dakota` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:The Dakota February 2023 002.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-02-08 14:29:37, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:The_Dakota_February_2023_002.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the 72nd Street front at close range: gabled dormers and finials against a deep February sky, oriel bays, cast-iron balconies on every floor, terracotta panels and string courses, a flagstaff with the US flag, a traffic signal at the kerb.

**Camera** — 40.775822, -73.976158 (NYC_TM -2208, 8420) at z 28.9 m NAVD88 | azimuth 3.7°, pitch +0.5° | 18 mm on 36 mm (89.0° horizontal, 73° vertical, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **83.3 m** from the item's recorded viewpoint; the item's recorded azimuth is 306.3°, **57.4° away**. The lens was widened to the **18 mm floor** and the record states that the verticals converge so the frame is not comparable with the photograph on proportion. The walk did not move it: the view azimuth is clear for **69.3 m** against a **37.7 m** requirement, and the nearest built thing in the frame is **`prop_citibike_bike_5` 2.8 m** away — a Citi Bike at the lens (Stage 40). The ground reads 27.317 m NAVD88, the 10th percentile of 113 samples within 12 m, range 26.94 to 27.54 m.

**Sun** — azimuth 217.8°, elevation 25.7° at 2023-02-08T14:29:37−05:00, from the photograph's own **EXIF DateTimeOriginal**; 726.7 W/m² direct normal, sky at strength 0.0377, Filmic, **+1.66 stops** metered and unclamped against a linear median of **0.05709** and a target of **0.18**. The physical rule would have given **0.75 stops**.

**In the scene** — 4,500,095 triangles: 5 building tiles (336,770 tris, 0 missing, 0 LOD-substituted), 6 landmark models of which 3 can fall inside the 89.0° frame, 19,792 pavement polygons, 1,501 props, 3,368 kit pieces, 21 park-ground meshes over 566 surfaces, 1,404 triangles of structures, 50 vehicles and 307 people.

## Verdict — the height is right to about a metre and the building is a plain brick box

**The measurements are close.** The probe found fabric on **43 of 43 rays** and measured **49.83 m** above a ground of 27.2 m against the catalogue's **50.9 m** for `c_the_dakota`, whose origin stands 31.8 m away — agreement to about a metre. The plan extent is **85.2 m by 84.4 m**, and the frustum puts the subject **3.6° off axis** at 107.0 m. Nine of thirteen rays are clear and **seven land on the subject**, a visible fraction of **0.538**.

**And the mass in the frame is a flat brick wall.** The render's left third is a plain brick slab with a shallow setback at its top edge and no opening in it; beyond it stands a second brick block with a regular window grid. The Dakota's whole character — the gables, the dormers, the oriels, the iron balconies, the terracotta, the stepped roofline — is absent. The kit numbers say why: **3,368 pieces drawn of 21,326 in range** at an **868,503-triangle** budget, of which **3,327 are windows** and the entire ornamental inventory is **8 cornices, 8 window accessories, 7 quoins, 7 string courses, 6 entry doors, 2 bulkheads**. On the most ornamented apartment house in New York, the kit placed eight cornices.

**The colour ratio measures the same absence** — chroma **0.0573** against the photograph's **0.1467**, a ratio of **0.391**. A brick box under a February sun has less colour than sandstone, terracotta, painted iron and a flag.

**One thing the render does better than most in the pass.** The trees are **bare**, from the photograph's own 8 February date, and the low 25.7° Sun throws their branch shadows in long fans across the roadway. That shadow pattern is the most convincing thing in the frame, and it is the one part of the picture that needs no ornament to be right.

**Two agent counts stand out.** **320 pedestrians were dropped for standing off a walkable surface** against **307 drawn** — Central Park is across the street and its paths are not a surface the crowd's test can see (J101). And **44 vehicles were dropped for standing on a car-free park drive**, the largest such count on any sheet written so far, which is J95's rule doing its job at the park's 72nd Street entrance.

## What matches

* **The height, to about a metre** — 49.83 m measured against a catalogued 50.9 m, on **43 of 43** probe rays.
* **The sightline** — 9 of 13 rays clear, 7 on the subject, a visible fraction of **0.538**.
* **The bare canopy and its shadows.** `leaf_off` true for 8 February, matching the reference, and the 25.7° Sun's long branch shadows across the asphalt.
* **Central Park's drives are car-free** — **44 vehicles dropped** (J95), the largest count in the pass.
* **569 faces were cut** out of the park ground for the landmark's own ground plate.
* **The block is furnished** — **273 Citi Bike units**, 113 street lamps, 101 manholes, 48 hydrants, 27 subway vent grates, 11 steam vents, **3 subway entrances**, 3 LinkNYC kiosks, and an **ambulance** in the fleet.
* **19,792 pavement polygons and none dropped**, with **5,823 sidewalk** — more sidewalk than roadbed.
* **A body at full detail** — 1 pedestrian at LOD0, 40 at LOD1.

## What does not match

* **The Dakota is a plain brick box.** No gables, dormers, oriels, balconies, terracotta or roofline.
* **Eight cornices, seven quoins and seven string courses** were placed on a 21,326-piece range at an 868,503-triangle budget.
* **Two fifths of the photograph's colour** — chroma **0.391**.
* **The render is brighter at the midtone** — p50 **0.501** against **0.3249**, a ratio of **1.542**, mean **1.432×** — and slightly harder, sd **1.112×**. The photograph's median sits **1.062 stops below** the grey convention and the render's **0.256 above**, a **+1.318-stop** difference (J83).
* **The frame is not comparable on proportion** — 18 mm at the floor, verticals converging, by the record's own words.
* **Props were capped to a third** — **1,501 placed of 4,192 in range** at a **1,051,611-triangle** budget, **2,606 dropped for budget**, **2,532** of them tree rows, 11 impostor cards dropped, 10 dropped on a suppressed building.
* **Three of five tiles in range have no structures file** — 2 imported, **3 without a file**, **1,404 triangles** — over the 72nd Street station, whose control house stands in the street here.
* **11 props across four kinds in range have no asset** — 5 artworks, 3 memorials, 2 drinking fountains, 1 real-time information sign.
* **320 pedestrians dropped off a walkable surface against 307 drawn** (J101).
* **The `subject_lands_on` field names a lamp, not the building** — the nearest hit along the fan is `prop_lamp_cobra_davit_130` at 57.5 m, while seven rays do land on the subject. The field reports the first thing met rather than the subject's own fabric, which reads as though no ray reached it.
* **The openings are drawn on the shell, not cut** (Stage 34 / J51).
* **No cloud.** The reference's sky is a clear deep winter blue that the Nishita sky does not reach at 25.7°; nothing in this build reads a historical sky.
* **1,583 agents were dropped** in total.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Dakota is a plain brick box | the kit budget placed 3,327 windows and 38 ornamental pieces of 21,326 in range, and gables, dormers, oriels and iron balconies are not classes this build models | **performance + geometry — the largest fidelity gap on this sheet** |
| chroma 0.391 | brick and asphalt against sandstone, terracotta, painted iron and a flag | geometry |
| p50 1.542 | the photograph is developed 1.062 stops below the grey convention and the render 0.256 above (J83) | reference |
| not comparable on proportion | 18 mm is the floor and the subject still needs a tilt; the record says so on the sheet | verification — declared |
| 1,501 props of 4,192, 2,532 tree rows dropped | the props triangle budget at 1,051,611 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| three of five tiles without a structures file | those tiles are unbuilt, over the 72nd Street station | **data — open** |
| 11 props across four kinds unmapped | no asset exists for those kinds | data |
| 320 pedestrians off a walkable surface against 307 drawn | Central Park's paths and lawns are not a surface class the crowd's test can read (J101) | **verification — open (J101)** |
| `subject_lands_on` names a lamp | the field reports the first thing the fan meets rather than the subject's own nearest fabric, so a sheet with seven rays on the subject reads as though none reached it | **verification — open, a record wording fault** |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
