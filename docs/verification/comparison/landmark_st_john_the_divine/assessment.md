# Cathedral of St. John the Divine

`landmark_st_john_the_divine` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Cathedral of St. John the Divine (52009407636).jpg by ajay_suresh, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2022-04-16 16:17, 1920x1920. [Commons page](https://commons.wikimedia.org/wiki/File:Cathedral_of_St._John_the_Divine_(52009407636).jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the west front straight on: the great rose window, five recessed portals with carved tympana, the gabled central bay, the north tower under scaffolding behind a green hoarding, a traffic signal and street sign at the kerb, a cyclist and a parked SUV. The street trees are **bare**, with buds only.

**Camera** — 40.804227, -73.963081 (NYC_TM -1104, 11574) at z 38.2 m NAVD88 | azimuth 114.0°, pitch +0.4° | 27 mm on 36 mm (67.8° horizontal, 68° vertical, square) | 1044x1044. The camera stands on **this photograph's own EXIF GPS**, **74.5 m** from the item's recorded viewpoint; the item's recorded azimuth is 80.0°, **34.0° away**. The lens was widened from 35 mm to 27 mm so a level axis contains the subject. The walk did not move it: 150.0 m of clear view against a 46.2 m requirement, the nearest built thing in the frame is **`prop_tree_pin_oak_small_11` 17.5 m** away and the nearest simulated agent a boro taxi **13.0 m** out. The ground reads 36.558 m NAVD88, the 10th percentile of 113 samples within 12 m, range 36.37 to 37.15 m.

**Sun** — azimuth 250.1°, elevation 36.3° at 2022-04-16T16:17:00−04:00, from the photograph's own **EXIF DateTimeOriginal** to the minute; 819.0 W/m² direct normal, sky at strength 0.0343, Filmic, **+5.19 stops** metered and unclamped against a linear median of **0.004918** and a target of **0.18**. The record declares it **under-lit** — *more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by*. The physical rule would have given **0.24 stops**. A west front at 16:17 in April should be in full sun; the frame is dark because the cathedral's own bulk and the street trees fill it.

**In the scene** — 4,500,094 triangles: 6 building tiles (347,420 tris, 0 missing, 0 LOD-substituted), 2 landmark models of which 1 can fall inside the 67.8° frame, 21,633 pavement polygons, 810 props, 3,982 kit pieces, 32 park-ground meshes over 703 surfaces, 7,608 triangles of structures, 67 vehicles and 305 people.

## Verdict — the Gothic arcade is modelled and everything above it is blank, and the canopy is one day past a threshold

**The arch order is there, which matters after Riverside Church.** The render's wall carries **five recessed pointed-arch niches** along its base, at the right rhythm and the right relative width, so this landmark model does carry a Gothic order rather than a flat plane. Above the arcade the wall is blank: no rose window, no gable, no tracery, no tower. So the sheet shows the bottom third of a west front and a smooth stone field where the photograph's whole subject is.

**The measurements are good.** The probe found fabric on **43 of 43 rays** and measured **53.35 m** above a ground of 38.91 m, against the catalogue's **71.0 m** whose origin stands 38.3 m away — the probe took the nave roof and the catalogue figure is the crossing, which is the right answer to a different question (J74, J94). The plan extent, **171.6 m by 125.8 m**, is the cathedral's own footprint. The frustum puts the subject **2.0° off axis** at 121.3 m. Six of thirteen rays are clear and **six land on the subject**, a visible fraction of **0.462**; the seven that do not stop at **17.4 m** on a pin oak.

**The tone is the third closest agreement in the pass.** Mean **1.012**, p50 **0.976**, and the photograph's median sitting **0.316 stops** above the grey convention against the render's **0.238** — a difference of **−0.078 stops**. That is a good result for a frame the meter had to lift by **5.19 stops**, and it is also a warning: a near-perfect tonal match says nothing about whether the picture is right, because this one is missing a rose window.

**And the canopy is wrong by a single day.** The photograph is dated **16 April** and its street trees are bare with buds. `leaf_off` flips on **15 April**, so 16 April falls on the summer side by one day and the render draws **full green foliage** — and drew enough of it to block half the sightline. Of the 25 sheets in the pass sitting in the 16 April to 15 May leaf-out (J97), this is the one where the boundary itself is visible: the switch is not wrong by a season here, it is wrong by a day, and there is no state between bare and full.

## What matches

* **The pointed-arch arcade** — five recessed niches at the base of the west front, in the right rhythm.
* **The height and the plan** — 53.35 m on **43 of 43** probe rays, 171.6 m by 125.8 m in plan, measured off the landmark model.
* **The aim** — the frustum at **2.0° off axis**, 121.3 m, from the photograph's own GPS.
* **The tone** — mean 1.012, p50 0.976, exposure difference **−0.078 stops**; third closest in the pass (see *Measured*).
* **The street is Amsterdam Avenue** — 21,633 pavement polygons with **0 dropped**, including 8,500 white markings, 5,220 sidewalk and **487 crosswalk**, and the crossing bars in the render's foreground are J52's continental bars.
* **The crowd clock reads Saturday** for 2022-04-16, which was a Saturday, and the fleet is a Saturday fleet: 29 sedans, 22 SUVs, 6 yellow taxis, 4 boro taxis, one bus, one Sanitation truck.
* **Bodies at full detail** — 2 pedestrians at LOD0, 33 at LOD1.
* **The park ground is exact near the camera** — within 150 m, 109 samples, an under-fraction of **0.0**, a median clearance of **0.201 m**, a worst of **+0.046 m**, no z-fighting.

## What does not match

* **Everything above the arcade is blank** — no rose window, no gable, no tracery, no tower, no portal carving.
* **The scaffolding and the green hoarding on the north tower are absent**, so the render cannot show the state the photograph caught.
* **The canopy is in full summer leaf against bare, budding trees**, because 16 April is one day past `leaf_off`'s 15 April threshold (J97).
* **Seven of thirteen rays are blocked by one pin oak** at 17.4 m, cutting the visible fraction to 0.462 — the same green canopy that should not be there.
* **Published under-lit at +5.19 stops** against a physical rule of 0.24 (J83).
* **Two thirds of the photograph's contrast** — sd **0.1571** against **0.2425**, a ratio of **0.648** — and **0.71** of its colour, chroma **0.0753** against **0.1061**. Carved stone in raking April light holds shadow that a smooth field cannot.
* **Props were capped to a quarter** — **810 placed of 3,203 in range** at a **987,349-triangle** budget, **2,259 dropped for budget**, **2,014** of them tree rows, 12 impostor cards dropped.
* **Kit was capped to under a fifth** — **3,982 of 22,533 in range** at an **829,652-triangle** budget, the lowest kit budget on any sheet written so far; the openings are drawn rather than cut (Stage 34 / J51).
* **Four of six tiles in range have no structures file** — 2 imported, **4 without a file**, **7,608 triangles** — over the Broadway line and the Cathedral Parkway station.
* **10 props across five kinds in range have no asset** — **6 artworks**, 1 memorial, 1 parks comfort station, 1 swimming pool, 1 vending machine.
* **A boro taxi stands 13.0 m from the lens**, nearer than any built thing but the pin oak, and neither the walk nor the sightline counts it (J98).
* **Between 150 and 400 m the park ground reads under the terrain on 0.1978 of 460 samples, with a worst of −7.103 m** — the deepest mid-field reading on any sheet written so far; beyond 400 m the under-fraction is **0.2955** over 626 samples with a z-fighting fraction of **0.0415**. The redrape moved **698,029** vertices, the largest redrape in the pass, up to 2.266 m up and 1.411 m down.
* **1,083 agents were dropped** — 546 pedestrians outside the radius, 207 vehicles outside the radius, 154 at the agent triangle budget, 114 in the carriageway without crossing, **38 off a walkable surface** on Morningside Park's edge (J101), 17 riderless bodies, 5 over the observer.
* **No cloud.** The reference's sky carries broken April cumulus behind the towers; nothing in this build reads a historical sky.

## Measured for this assessment

| figure | how |
|---|---|
| the third closest tonal agreement in the pass | ranked every record carrying `scene.structures` by the sum of the distances of `frame_stats.json`'s `render_over_reference.mean` and `.p50` from 1.0; the Washington Square Arch and Seagram Building sheets are closer |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| everything above the arcade is blank | the landmark model carries the arch order at the base and massing above it; a rose window, bar tracery, gables and portal carving are not classes this build models | **geometry — open, and the largest fidelity gap on this sheet** |
| no scaffolding or hoarding | the photograph caught a works state; construction hoarding is not a class this build models, and the scaffold kit pieces it does have are facade-mounted | geometry + reference |
| summer leaf against bare, budding trees | `leaf_off` flips on 15 April and the photograph is dated 16 April, so the render falls on the summer side by one day and there is no state between bare and full (J97) | **verification — open (J97), and the boundary is visible here** |
| seven rays blocked by a pin oak | that canopy is the same one the date threshold should not have drawn in full (J97, J79) | verification — a consequence of the line above |
| published under-lit at +5.19 stops | the cathedral's own bulk and the street canopy fill the frame; the development is metered on it (J83) | verification — declared, and correct |
| sd 0.648, chroma 0.71 | carved stone in raking light against a smooth field, and a photograph developed 0.316 stops above the grey convention against a render 0.238 above (J83) | geometry + reference |
| 810 props of 3,203, 2,014 tree rows dropped | the props triangle budget at 987,349 | performance |
| 3,982 kit pieces of 22,533 | the kit triangle budget at 829,652 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| four of six tiles without a structures file | those tiles are unbuilt, over the Broadway line | **data — open** |
| 10 props across five kinds unmapped, 6 of them artworks | no asset exists for those kinds | data |
| a taxi 13.0 m from the lens | the walk and the sightline count built fabric only, by J49's declared decision, and nothing acts on the agent distance the record publishes (J98) | verification — open (J98) |
| a −7.103 m mid-field tail | the park builder drapes on its own heightmap and the scene's differs over Morningside's cliff; the redrape closes the near field to 0.0 and leaves that tail (J71) | geometry — open, bounded |
| 305 people of 948 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
