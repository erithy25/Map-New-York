# St. Patrick's Cathedral

`landmark_st_patricks_cathedral` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:St Patrick's Cathedral August 2021 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-21 12:42:57, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:St_Patrick%E2%80%99s_Cathedral_August_2021_001.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the west front looking up: the twin spires, the rose window, the great gabled portal with its carved tympanum, crockets and finials, a US flag on its staff, a street tree, and a white August sky. The stone is almost colourless — the reference's measured chroma is **0.0196**, the lowest of any photograph in the pass.

**Camera** — 40.758811, -73.977586 (NYC_TM -2306, 6511) at z 23.6 m NAVD88 | azimuth 106.5°, pitch 0.0° | 35 mm on 36 mm (42.2° horizontal, 54.4° vertical, portrait) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, **33.8 m** from the item's recorded viewpoint, and its heading agrees with the recorded 111.2° to **4.7°**. The walk then **moved it 30.2 m** onto the nearest surveyed crosswalk polygon, because *the recorded viewpoint is inside `t_-3_6_roof_membrane`* — a ray straight up from Rockefeller Plaza hits one tile's joined roof-membrane mesh (J94). From there the view is clear for **73 m** against a **61.0 m** requirement, the nearest built thing is `prop_lamp_cobra_davit_51` **18.3 m** away, and the note records a pedestrian **2.1 m** from the lens, which the cull over the observer then removed. The ground reads 22.029 m NAVD88, the 10th percentile of 113 samples within 12 m, range 21.97 to 22.53 m.

**Sun** — azimuth 171.9°, elevation 60.9° at 2021-08-21T12:42:57−04:00, from the photograph's own **EXIF DateTimeOriginal**; 920.9 W/m² direct normal, sky at strength 0.0309, Filmic, **+4.31 stops** metered and unclamped against a linear median of **0.009047** and a target of **0.18**. Declared **under-lit** — beyond hand-held recovery — against a physical rule of **0.0 stops**.

**In the scene** — 4,500,157 triangles: 6 building tiles (251,580 tris, 0 missing, 0 LOD-substituted), 12 landmark models of which 3 can fall inside the 42.2° frame, 25,612 pavement polygons, 796 props, 2,737 kit pieces, 23 park-ground meshes, 2,920 triangles of structures, 52 vehicles and 340 people.

## Verdict — the frame refused to tilt, so the render looks along the flank and the spires are outside the picture, and the record says exactly that

**The refusal is deliberate and written down.** The pitch note reads: *level optical axis (St. Patrick's Cathedral is 122 m away and would need +9 deg of tilt; a real frame would use a wider lens instead, and a tilted axis would stop the render being comparable on proportion)*. So the axis stayed level, the lens stayed at 35 mm, and what a level 42.2° frame contains from 95 m is the **Fifth Avenue flank**, not the west front. The render shows that flank well: a long receding run of **buttresses with lancet openings between them**, at the right pitch and rhythm, with the aisle roof behind. The photograph shows the two spires, the rose window and the portal — none of which is in the frame.

**The measurements are sound and about the nave.** The probe found fabric on **43 of 43 rays** and measured **42.71 m** above a ground of 21.95 m. The catalogue's own entry for `st_patricks_cathedral` is **100.6 m** and its origin stands **3.3 m** from the coordinate — the closest catalogue agreement in the pass — so the catalogue is right about the spires and the probe is right about the roof it found (J74, J94). The plan extent, **112.8 m by 78.5 m**, is the cathedral's own footprint. Of thirteen rays, **7 are clear** and **5 land on the subject**, a visible fraction of **0.385**; the rest stop at **18.4 m** on a cobra-head lamp.

**The colour ratio is the most extreme inversion in the pass, and it is honest.** The render carries **2.852×** the photograph's chroma. The reference is grey limestone under a white sky at 0.0196; the render's frame holds a green street tree, tan brick, a crowd in coloured clothing and warm pavement. Neither number is a fidelity fault; they are two different framings of one block.

**Rockefeller Plaza tests as a roof.** The recorded viewpoint — beside the Atlas statue, on open pavement — is reported as *inside* a joined roof-membrane tile mesh, so the walk had to move 30.2 m. That is the same fault as the Little Island sheet, from the opposite side of the city, and it is the joined mesh rather than the viewpoint that is wrong (J94).

## What matches

* **The flank's Gothic order** — buttresses with lancet openings between them, receding at the right rhythm.
* **The height and the plan** — 42.71 m on **43 of 43** probe rays, 112.8 m by 78.5 m in plan, measured off the model.
* **The catalogue is right where it is used** — its origin stands **3.3 m** from the coordinate, the closest agreement in the pass, and its 100.6 m is the spires' height.
* **The aim** — the recorded azimuth agrees with the measured bearing to **4.7°**, and the frustum puts the subject **5.8° off axis** at 105.1 m; it also names the Seagram Building at 436.4 m and the Citigroup Center at 627.7 m in the same 42.2° cone.
* **The flag row is here too** — **81 flagpoles**, Rockefeller Center's own row across the avenue, flying flags rather than bare poles (J58).
* **Fifth Avenue is paved as Fifth Avenue** — 25,612 pavement polygons with **0 dropped**, including **1,386 plaza** polygons and 6,033 sidewalk.
* **The fleet is a Midtown fleet** — **20 yellow taxis and 12 boro taxis** against 6 sedans, 8 black cars, 4 SUVs, 2 box trucks, 1 bus.
* **A crowd on the cathedral steps** — 340 people, 2 of them at LOD0, 18 at LOD1.

## What does not match

* **The spires, the rose window and the west front are outside the frame**, by the pitch rule's declared choice.
* **Published under-lit at +4.31 stops** against a physical rule of 0.0 (J83).
* **The render is brighter at the midtone** — p50 **0.4992** against **0.3165**, a ratio of **1.577**, mean **1.481×** — and flatter, sd **0.209** against **0.2522** (**0.829×**). The photograph's median sits **1.14 stops below** the grey convention and the render's **0.245 above**, a **+1.385-stop** difference (J83).
* **Nearly three times the photograph's colour** — chroma **2.852**, from a green tree and a coloured crowd against almost colourless limestone.
* **No carved ornament anywhere** — no crockets, no finials, no tympanum, no tracery in the lancets.
* **Rockefeller Plaza tests as inside a roof**, forcing a 30.2 m move (J94).
* **Kit was capped to one piece in seven** — **2,737 of 18,679 in range** at a **685,819-triangle** budget, the lowest kit budget on any sheet written so far, of which 2,645 are windows; the openings are drawn rather than cut (Stage 34 / J51).
* **Props were capped to under half** — **796 placed of 1,967 in range** at a **952,894-triangle** budget, **1,040 dropped for budget**, **650** of them tree rows, 3 dropped on a suppressed building.
* **Four of six tiles in range have no structures file** — 2 imported, **4 without a file**, **2,920 triangles** — over the Fifth Avenue–53rd Street station and the Sixth Avenue lines.
* **12 props across four kinds in range have no asset** — **7 artworks**, 3 memorials, 1 drinking fountain, 1 real-time information sign. Across from this block the artwork is Atlas.
* **The park ground is only sampled beyond 400 m** — all **509 samples** fall in that band, with an under-fraction of **0.3301** and a worst of **−1.652 m**.
* **3,588 agents were dropped** — 1,194 pedestrians at the agent triangle budget, 298 vehicles at the budget, 165 in the carriageway without crossing, 35 where the planimetric data has no sidewalk, 24 cyclists the fleet exports without a rider.
* **No cloud.** The reference's sky is a flat white August haze; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the spires and west front are outside the frame | the pitch rule refuses a +9° tilt at 122 m, because a tilted axis would stop the two frames being comparable on proportion, and the lens was not widened either — so a level 42.2° frame gets the flank | **verification — declared, and the rule's own trade-off** |
| no carved ornament | crockets, finials, tympana and window tracery are not classes this build models | geometry |
| Rockefeller Plaza tests as inside a roof | one tile's roof-membrane surfaces are joined into a single object whose extent covers open pavement (J94) | **geometry — open, the join is the fault** |
| published under-lit at +4.31 stops | a north-lit flank in a Midtown canyon at 60.9°; the development is metered on the frame (J83) | verification — declared, and correct |
| p50 1.577, chroma 2.852 | the photograph is developed 1.14 stops below the grey convention on almost colourless limestone, and the render's frame holds a green tree and a coloured crowd (J83) | reference |
| 2,737 kit pieces of 18,679 | the kit triangle budget at 685,819 | performance |
| 796 props of 1,967, 650 tree rows dropped | the props triangle budget at 952,894 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| four of six tiles without a structures file | those tiles are unbuilt, over the Fifth Avenue–53rd Street station | **data — open** |
| 12 props across four kinds unmapped, 7 of them artworks | no asset exists for those kinds | data |
| the park ground is sampled only beyond 400 m | there is no park within 400 m of this camera to sample (J71) | verification — nothing nearer to check |
| 340 people of 3,102 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
