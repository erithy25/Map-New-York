# Statue of Liberty

`landmark_statue_of_liberty` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Statue of Liberty, New York City, 20231003 1511 1972.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 15:11:01, 1920x2876. [Commons page](https://commons.wikimedia.org/wiki/File:Statue_of_Liberty,_New_York_City,_20231003_1511_1972.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.68882, -74.04369 (NYC_TM -7919, -1237) at z 4.6 m NAVD88 | azimuth 304.8°, pitch +0.4° | 27 mm on 36 mm (47.4° horizontal, 66.7° vertical, portrait) | 854x1280. Position and heading both come from the photograph: its own EXIF camera GPS, **52.5 m** from the item's recorded viewpoint, and 304.8° is the bearing from there to the subject. The item's recorded azimuth of 315.5° is 10.7° away. The lens was **widened from 35 mm to 27 mm** and the axis tilted **+0.4°** to contain the subject as the probe measured it: the top of `lm_b_statue_of_liberty.11` stands 48 m above the lens at 84 m, **30° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was **not moved** — the viewpoint is in open air, the view azimuth clear for **47.4 m** against the **41.9 m** this frame needs — and the nearest built thing in the frame is `lm_b_statue_of_liberty.4`, the pedestal, **43.5 m** away at −23.7°. Ground under the camera reads **3.011 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 0.0 to 3.87 m.

**Sun** — azimuth 225.8°, elevation 34.2° at 2023-10-03T15:11:01−04:00, from the photograph's own **EXIF DateTimeOriginal**; 804.1 W/m² direct normal, sky at strength 0.0348, Filmic, **+0.10 stops**. This is the best-metered frame in the pass: the linear frame's median is **0.168418** against a middle-grey target of **0.18**, so the scene arrived within a tenth of a stop of a photographable level on its own (J83). The physical rule would have given +0.33.

**In the scene** — 802,378 triangles, the smallest scene in the pass: 4 building tiles (3,520 tris), 2 landmark models of which 1 falls inside the 47.4° frame, 909 pavement polygons (632 sidewalk, 277 plaza) with 0 dropped, 359 props, 1,451 kit pieces (448,618 tris), **0 park-ground meshes**, 4 structures tiles with **none missing** (4,688 tris), **0 vehicles and 0 people**, terrain 83,232 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — she is fully modelled, to the flame, at 15,152 triangles, and her own sheet does not contain her: the probe measured the pedestal, the frame was aimed at half the pedestal's height, and the statue stands above the top edge

**The model is not the problem.** I read `b_statue_of_liberty.glb`: the figure is a single 15,152-triangle mesh spanning **46.737 to 89.687 m**, with `crown_rays` at 83.157 to 85.967, the `tablet` at 62.534 to 69.560, and `torch_handle`, `torch_balcony` and `torch_flame` carrying the arm up to **95.990 m** — against the catalogue's 92.99 m. The pedestal is there (22.810 to 49.940 m), Fort Wood's scarp and terreplein are there (−2.000 to 19.810 m). Everything the photograph shows exists in this build.

**The verification chain lost her in three steps.** The probe measures the object standing at the subject's coordinate (J74) and found `lm_b_statue_of_liberty.11`, height **48.29 m** above a ground of 4.65 m — the pedestal, not the statue, which the catalogue entry 10.9 m away puts at **92.99 m**. The frame was then aimed at that object's mid-height, **24.1 m above its ground**, which is a granite wall. And the sightline cast 13 rays at that point: **0 clear, 0 on the subject**, every one stopped at **47.5 m** by `lm_b_statue_of_liberty.4` — the pedestal again. Visible fraction **0.000**.

**So the render is a picture of the plaza under her.** A granite mass filling the middle, one of Liberty Island's own buildings behind it carrying rows of facade-kit windows, and a pale stone floor. The photograph is the statue against a clear October sky. Chroma **0.028** against **0.2506** — a ratio of **0.112**, the widest colour gap on any sheet in this pass — because the one thing in the reference with any saturation is oxidised copper, and none of it is in the frame.

**This is a fault with a measured extent.** Across the 138 sheets that carry a height probe, **16** measure less than three quarters of the height of a catalogue entry standing within 20 m of the same point — the probe took a member of a multi-part landmark rather than the landmark. In **4** of the 16 the frame ends with a visible fraction of 0.000: this sheet, Trinity Church, `landmark_111_west_57th` and the Central Park Sheep Meadow. In the others the aim is low but the subject still lands, so the fault only destroys a frame when the member it measured is also the thing that blocks. Recorded as **J94**.

## What matches

* **The model is complete and correct in scale** — figure, crown, tablet, torch, pedestal, fort — to **95.990 m** against a catalogue entry of 92.99 m.
* **The metering is the best in the pass.** Median linear luminance **0.168418** against a 0.18 target: +0.10 stops, unclamped, which is what a scene that is genuinely lit like the photograph looks like (J83).
* **The camera stands where the photographer stood** and the heading is the bearing to the subject from there, 10.7° off the item's nominal azimuth.
* **Every structures tile in range has a file** — 4 of 4, 4,688 triangles — the only sheet in this queue with no missing structures.
* **The height probe itself is complete**: 43 of 43 rays on built fabric, and the extent is measured off the object (14.8 m by 14.8 m) rather than assumed (J74).
* **The record is honest about the empty crowd**: `reason: the simulation frame is empty here`. There is no road network on Liberty Island, so 0 vehicles and 0 people is the correct answer rather than a gap.
* **The trees are scaled almost exactly**: 277 placed, mean scale **0.992**, **0** out of band.
* **The record names the missing park ground rather than drawing bare terrain silently**: park ground was not built for 4 tiles inside the 587 m ground radius, and the sheet says so.

## What does not match

* **The statue is not in the frame.** Visible fraction **0.000**, 13 of 13 rays stopped at 47.5 m by the pedestal.
* **The probe measured 48.29 m for a 92.99 m subject** — the pedestal instead of the statue — and the aim followed it to 24.1 m above the pedestal's ground.
* **Chroma is 0.112 of the photograph's**, 0.028 against 0.2506. The render's frame has one saturated thing in it and it is a brick wall.
* **The render is darker and flatter**: mean **0.4292** against **0.5707** (**0.752×**), median **0.5014** against **0.6141** (**0.816×**), standard deviation **0.14** against **0.1482** (**0.945×**). The two exposure offsets from the grey convention are **+0.259** and **+0.897** stops, **0.638 stops** apart, so much of the mean gap is the photograph's own development (J83).
* **Liberty Island's buildings are windowed like tenements.** 1,413 of the 1,451 kit pieces in range are windows, 448,618 triangles of them, on an island whose only real buildings are a museum, a service block and the fort. The facade kit reads a tile's building rows and has no rule that an island administration building is not a walk-up.
* **No park ground at all** — 0 meshes, 0 surfaces, for 4 tiles in range, so Liberty Island's lawns render as bare terrain.
* **Only 8 of 277 trees are drawn from modelled branches**; 269 are six-triangle impostor cards, **0** are procedural canopy stems, 3 cards were dropped, and **277 species were substituted** — every single tree in range is a species the catalogue does not hold.
* **The frustum reports the Statue of Liberty at 94.1 m, 2.3° off axis**, while the subject's coordinate is 83.8 m away: the cone test uses the composite origin, 10 m further out, and it is the only landmark it finds in the frame.
* **Two props of one kind were wanted in range and have no asset**: 2 artwork.
* **No sky colour and no birds.** The reference is a clear October sky with a gull in it; the render's sky is a Nishita dome at strength 0.0348.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the statue is not in the frame, visible fraction 0.000 | the probe measured a member of the landmark (the pedestal, 48.29 m) rather than the landmark (92.99 m), the aim followed it to 24.1 m, and the same member blocked all 13 rays. 16 of 138 probed sheets measure under three quarters of a catalogue entry within 20 m; 4 of those end at 0.000 | **verification — open, J94** |
| chroma 0.112×, mean 0.752× | the copper is out of frame; what is in frame is granite, brick and stone | consequence of the row above |
| 1,413 kit windows on Liberty Island | the facade kit places from a tile's building rows with no rule for what kind of building it is (J51 remains open on openings, and nothing classifies an island service block) | **geometry — open, measured** |
| no park ground on 4 tiles | park ground was not built for those tiles; the record names them | **data — open, four tiles unbuilt** |
| 8 of 277 trees from modelled branches, 277 species substituted | the props triangle budget, and a tree catalogue that holds none of the species surveyed on the island | performance + **data** |
| the frustum reports 94.1 m at 2.3° off axis | the cone test uses the landmark's composite origin, not the member aimed at | verification — open |
| 2 props unmapped | no asset exists for that kind | data |
| no sky colour, no gull | nothing in this build reads a historical sky, and birds are not a class it models | reference — no source exists |

## Measured for this assessment

Six figures above are not in the render record. The record reports a probe height of 48.29 m against a
catalogue entry of 92.99 m for the same landmark 10.9 m away, and only the model can say which part
the probe found and whether the statue exists at all. Read with
`blender_out/landmarks/b_statue_of_liberty.glb`, 17 meshes, bounds and triangle counts taken from each
primitive's POSITION and indices accessors on the glTF up axis.

| figure | where it comes from |
|---|---|
| 15,152 | triangles in the `Mesh` primitive — the statue's figure, from the robe to the shoulders |
| 46.737 | bottom of that mesh, which is where the figure meets the pedestal cap |
| 89.687 | top of that mesh |
| 95.990 | top of `torch_flame`, the highest vertex in the model, against the catalogue's 92.99 m |
| 49.940 | top of `pedestal`, whose base is at 22.810 m, and within 1.7 m of the 48.29 m the probe reported — which is how the member was identified |
| 19.810 | top of `fort_wood_scarp`, below the 24.1 m the frame was aimed at |
| 83.157 | bottom of `crown_rays`, and 85.967 its top; the `tablet` spans 62.534 to 69.560 m |

And four figures come from a survey of the pass itself, read with every `render.json` under
`docs/verification/comparison`, comparing `subject.height_probe.height_above_ground_m` against
`subject.height_probe.nearest_catalogue_origin`:

| figure | where it comes from |
|---|---|
| 138 | render records that carry a height probe at all |
| 16 | of those, records whose probe height is below three quarters of a catalogue entry standing within 20 m |
| 4 | of those 16, records whose `sightline.subject_visible_fraction` is 0.0 — this sheet, `landmark_trinity_church`, `landmark_111_west_57th` and `landmark_central_park_sheep_meadow` |
| 0.104 | the lowest ratio in that survey, `landmark_pier_57`: a probe of 2.01 m against a 19.30 m catalogue entry 15.2 m away, which still reports a visible fraction of 0.769 |
