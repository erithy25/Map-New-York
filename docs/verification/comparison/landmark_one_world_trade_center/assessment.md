# One World Trade Center

`landmark_one_world_trade_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:One World Trade Center, top and spire.JPG by Opencooper, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2017-09-15 17:23:28, 1920x2682. [Commons page](https://commons.wikimedia.org/wiki/File:One_World_Trade_Center,_top_and_spire.JPG) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.710111, -74.011636 (NYC_TM -5253, 1285) at z 6.3 m NAVD88 | azimuth 333.1°, pitch +1.7° | 18 mm on 36 mm (71.2° horizontal, 90.0° vertical, portrait) | 884x1234. The camera stands on **this photograph's own EXIF GPS**, 50.7 m from the item's recorded viewpoint — and then had to leave, because **the recorded viewpoint is inside a building**: a ray straight up from the eye point hits the roof of `lm_b_wtc_site.243`. The camera was **moved 166.3 m** onto the nearest real roadbed polygon, the largest displacement in the pass, keeping its eye height above the heightmap. From there the view is clear for 96 m and the nearest built thing in the frame is `lm_b_wtc_site.72` **12.2 m** away at −36° yaw. The lens was widened to the **18 mm floor** and still cuts off the top of a subject that stands **41° above the horizon** at 327 m; the record declares the verticals converge and the frame is not comparable on proportion.

**Sun** — azimuth 257.4°, elevation 18.3° at 2017-09-15T17:23:28−04:00, from the photograph's own **EXIF DateTimeOriginal**; 625.0 W/m² direct normal, sky at strength 0.0424, Filmic, **+5.58 stops**, marked **under-lit**. The linear median is **0.00375**. The physical rule would have given **1.25 stops**.

**In the scene** — 4,500,052 triangles: 7 building tiles (150,452 tris) with **1 tile's shells not built**, 16 landmark models of which 1 falls inside the 71.2° frame, 37,476 pavement polygons, 616 props, 4,040 kit pieces, 26 park-ground meshes with **53,345 faces cut for landmark ground** and **2 tiles with no park ground at all**, 88 vehicles and 374 people.

## Verdict — the item's viewpoint is inside a building and its subject coordinate is on the wrong tower, and the model itself is exact

**Two findings on this sheet matter more than the comparison does.**

**The item's viewpoint is inside a building.** Not near one, inside: a ray cast straight up from the eye point strikes the roof of `lm_b_wtc_site.243`. The walk moved the camera **166.3 m** to the nearest surveyed roadbed, which is the right recovery and also an admission that the viewpoint as recorded is unusable. This is the first sheet in the pass where the stored coordinate is not merely awkward but wrong.

**The height disagrees with itself by two hundred and forty-eight metres.** The probe casts **43 rays**, of which **41 land on built fabric**, and measures **292.65 m** above a ground of 3.36 m on `lm_b_one_world_trade_center.6`, an object whose plan extent is **75.0 m by 75.0 m**. The catalogue's own height for that model, whose origin sits **35.0 m** from the recorded coordinate and therefore well inside the 120 m the rule looks in, is **541.3 m**. J74 prefers the geometry over the catalogue by design, so the figure published is 292.65 m. **The model is not short — I measured it.** `blender_out/landmarks/b_one_world_trade_center.glb` carries twelve meshes whose heights above the podium datum are the published ones: `spire_beacon` tops out at **541.30 m**, `spire_mast` at **542.80 m**, `parapet` at **418.50 m**, `roof` and the top of `shaft` at **417.00 m**, `podium_cap` at **57.80 m** and `podium` at **56.40 m**. Those are the catalogue's figures to the centimetre. **So the 292.65 m is not the tower; it is whatever stands at the coordinate the item recorded.** The record supports that reading: the subject coordinate is **167.6 m** from the camera while the model's origin is **327.4 m** from it, so the coordinate sits well over a hundred metres from the tower it names — out over the memorial plaza, where the neighbouring World Trade Center towers stand. The height rule did its job on the wrong object.

**The comparison itself does not exist.** The photograph is a close upward study of the tower's crown and mast, filling a portrait frame. The render is a plaza at ground level: a broad pale ground plane across the lower two-thirds, a raised planter of dark-green trees across the middle, and the WTC towers behind. Neither the crown nor the mast is the render's subject.

**And the bare terrain shows.** **Building shells were not built for tile `t_-7_0`** and **park ground was not built for `t_-7_0` or `t_-7_1`** inside the 900 m ground radius, leaving bare terrain there. A step runs visibly across the render's foreground where the built surface ends and that terrain begins.

## What matches

* **One World Trade Center is in the frame and on axis** — at **182.7 m**, **0.9° off axis**, the only landmark inside the 71.2° cone out of 16 placed in the scene.
* **The sightline is honest about a partial view.** 13 rays, **11 clear**, **5 on the subject**, fraction **0.385**, with 6 passing into nothing above or beside it and the blocked ones stopping at **12.9 m** on `lm_b_wtc_site.83`. Looking at the render, that is right: the tower's flank is there and most of the fan misses it.
* **The view is the photograph's own heading.** Azimuth **333.1°** from its GPS to the tower; the item's recorded azimuth is 337.3°, **4.2° away**, the closest agreement of any moved-camera sheet.
* **The memorial plaza's own ground is cut into the park ground** — **53,345 faces**, the same count as the Oculus sheet, which is the same plaza.
* **The plaza is the most heavily paved frame in the pass**: 37,476 pavement polygons, including **17,695** white markings and **4,300 plaza** polygons.
* **The oak grove is drawn from modelled branches.** **136 trees within 120 m of the lens are real geometry**, not cards — the highest count of modelled trees on any sheet — with 127 impostor cards beyond.
* **The water is right for Lower Manhattan**: 2,505 quads across the East River, the Hudson, Upper New York Bay, North Cove and South Cove.
* **The fleet is a Financial District Friday fleet**: **45 sedans, 22 SUVs, 10 yellow taxis, 5 boro taxis, 3 MTA buses**, a black car, a box truck and a Sanitation truck, with the crowd clock reporting **a weekday** for 2017-09-15, which was a Friday.
* **The render holds more contrast than the photograph** — standard deviation **0.2122** against **0.1704**, a ratio of **1.245**, the only sheet in the pass where that is true. The reference is a soft-focus crown against cloud; the render has hard glass edges and a lit ground.

## What does not match

* **The subject of the photograph — the crown and the spire — is not the subject of the render.** The lens is at the 18 mm floor and the top is still cut off, which the record states rather than hides.
* **The measured height is 292.65 m and the catalogue's is 541.3 m.** Both are in the record; only one can describe this building.
* **Two tiles have no park ground and one has no building shells**, so bare terrain runs across the near frame with a visible step where the built surface stops.
* **The near ground is an undifferentiated pale plane** over roughly half the picture. 37,476 pavement polygons are recorded, and at this grazing angle with authored base colours they read as one surface.
* **The frame needed +5.58 stops** and is marked under-lit. An 18.3° September sun at azimuth 257.4° behind a view along 333.1° leaves everything facing the lens in its own shade.
* **A darker midtone than the photograph.** Median **0.4968** against **0.6970** (**0.713×**), mean **0.5740** against **0.6437** (**0.892×**). The photograph sits **1.301 stops** above the grey convention and the render **0.230**, a **1.071-stop** difference (J83).
* **More colour than the day had** — chroma **0.1041** against **0.0827** (**1.259×**). The reference is a pale overcast crown; the render's greens and glass are more saturated.
* **616 props is the thinnest dressing in the pass**, and **6,052 tree rows did not fit the props budget** — the largest tree shortfall measured. Props were capped at **1,008,823** triangles and kit at **793,232** with **20,731 pieces in range**.
* **3,670 of 4,040 kit pieces are windows**, against 22 cornices, 23 string courses, 18 quoins and 10 pilasters.
* **The memorial is not furnished.** **9 memorial and 7 artwork** props were wanted in range and had no asset — on the one plaza in the city where that class is the point.
* **Every one of the 88 vehicles is at LOD2**, and 354 of 374 people.
* **The crowd is a fraction of the ask.** The density table wanted **636 vehicles and 4,603 people**; **699 and 3,000** were simulated and **3,237** dropped — 1,234 pedestrians outside the radius, **726 at the triangle budget**, 405 in the carriageway without crossing, 254 not on a walkable surface, **7 inside buildings**, and 15 riderless bodies.
* **There is no park ground within 150 m to check** — **0 samples** in the near band. Beyond 400 m the under-fraction is **0.2176** over 1,705 samples.
* **4 of the tiles in range have no structures file**, leaving 63,424 triangles of structures.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the recorded viewpoint is inside a building | the stored coordinate for this item places the eye under the roof of `lm_b_wtc_site.243`; the walk recovered by moving 166.3 m to a surveyed roadbed | **verification — open, the item's coordinate is wrong** |
| measured height 292.65 m against a catalogue 541.3 m | **not the model**: its glb carries the published heights to the centimetre (beacon 541.30 m, roof 417.00 m, podium 56.40 m, tallest vertex 542.80 m). The item's recorded subject coordinate is 167.6 m from the camera where the model origin is 327.4 m from it, so it stands well over a hundred metres from the tower, so the probe measured a neighbouring World Trade Center tower instead | **verification — open, the item's coordinate** |
| bare terrain and a step across the near frame | building shells were not built for `t_-7_0` and park ground for neither `t_-7_0` nor `t_-7_1`, inside the 900 m ground radius | **data — open, two tiles unbuilt** |
| the crown and spire are not in the render | the lens is at its 18 mm floor and the subject stands 41° above the horizon at 327 m; widening further would stop the frames being comparable at all | verification — declared |
| the frame needed +5.58 stops | an 18.3° sun at 257.4° behind a view along 333.1°; published under-lit and marked so (J83) | reference + verification — declared |
| p50 0.713× | the photograph is developed 1.301 stops above the grey convention and the render 0.230 (J83) | reference |
| chroma 1.259× | a pale overcast reference against a clear Nishita sky, lit glass and modelled foliage | reference — no source for a historical sky |
| the near ground reads as one plane | surveyed pavement with authored base colours at a grazing angle | data |
| 616 props, 6,052 tree rows dropped, 20,731 kit pieces in range against a 793,232-triangle budget | the three per-frame triangle budgets, each named with what it dropped | performance |
| no memorial furniture on the memorial plaza | 9 memorial and 7 artwork props had no asset | data |
| every vehicle at LOD2 | the LOD ladder at this distance under the agent budget | performance |
| 374 people against a table asking 4,603 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
