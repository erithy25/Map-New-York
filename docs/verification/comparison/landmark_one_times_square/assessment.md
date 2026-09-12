# One Times Square

`landmark_one_times_square` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Paramount Building via One Times Square.jpg by Scu ba, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2024-06-27 15:26:26, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Paramount_Building_via_One_Times_Square.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.756008, -73.986589 (NYC_TM -3083, 6212) at z 18.4 m NAVD88 | azimuth 10.6°, pitch +26.9° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, portrait) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, **226.0 m** from the item's recorded viewpoint — inside the 250 m at which it can still be the same view, but barely — and the item's recorded azimuth is 200.0°, **170.6° away**, which is to say the nominal viewpoint faces the opposite direction. The recorded viewpoint was also **boxed in**: the view azimuth closed off **3 m ahead** against the 23 m this frame needs, so the camera was **moved 10.4 m** onto the nearest surveyed crosswalk polygon. From there the view is clear for 58 m and the nearest built thing in the frame is `lm_c_times_square.30` **10.3 m** away. The ground under it reads 16.803 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 16.52 to 17.15 m.

**Sun** — azimuth 251.8°, elevation 54.6° at 2024-06-27T15:26:26−04:00, from the photograph's own **EXIF DateTimeOriginal**; 903.7 W/m² direct normal, sky at strength 0.0315, Filmic, **−0.39 stops**. That minus sign is unique in this pass: the linear frame's median is **0.236155** against a middle-grey target of 0.18, so this is the **only sheet whose scene arrived brighter than a photographable level and had to be pulled down** rather than lifted. The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,175 triangles: 4 building tiles (247,682 tris), 6 landmark models of which 2 fall inside the 73.7° frame, 28,482 pavement polygons, 1,460 props, 5,703 kit pieces, 13 park-ground meshes, **0 triangles of structures**, 52 vehicles and 255 people.

## Verdict — the only frame in the pass that was too bright, and a blank billboard ten metres from the lens is most of it

**Times Square is the one place in this city where the render's own light overshot.** Every other daylight sheet needed lifting — two stops, four, six, one of them clamped at six — and this one needed **pulling down by 0.39 stops**. The cause is in the kit list: **21 billboard pieces**, the emissive surfaces that make this block what it is, and they raised the scene's median to 0.236 against a 0.18 target.

**And they are blank on purpose.** The great pale wedge that fills the upper two-thirds of the render is a billboard seen from underneath at close range — `lm_c_times_square.30` stands **10.3 m** from the lens — and it carries no image because this build never invented one. `data/processed/tiles/t_-4_5/kit_placements.json` states the rule in its own `sign_face_binding` block: `sign_led_*` is "no content: the face models the display hardware", `billboard_*` is "blank vinyl: no source in this environment says what a New York bulletin carries". `docs/DATA_CONTRACTS.md` §6.1.1 says the same of the LED pieces — "the LED pixel matrix and **no content at all**" — and DEVIATIONS B15a records the decision behind it: **no advertising copy was invented anywhere**. So the most colourful place in New York comes out at **chroma 0.042 against the photograph's 0.1356, a ratio of 0.31**: the screens are there, they are lit, and the model refuses to say what is on them.

**The subject is behind the billboard.** Of 13 sightline rays, **3 are clear** and **1 lands on the subject**, giving a visible fraction of **0.077** — the fifth sheet in this pass at exactly that figure — with the rest stopping at **13.1 m** on `lm_c_times_square.58`. The height probe fares worse: **43 rays cast and only 12 landing on built fabric**, the lowest ratio in the pass, which is what a tower does when it stands behind a screen. The **109.53 m** it measures is nonetheless close to One Times Square's real height.

**One more thing the sheet should say about itself.** The reference is filed as *Paramount Building via One Times Square*, and what fills the photograph is the Paramount Building — its setback tower, its great clock and the glass ball above it. The item names One Times Square as the subject. The pairing is defensible, because the photograph is taken past one to see the other; a reader comparing them should know that the thing they are looking at in the left half is not the thing the sheet is measuring.

## What matches

* **The height is close.** 109.53 m measured above a ground of 16.15 m, against One Times Square's real height, on an object **46.1 m by 27.5 m** in plan.
* **The billboards are modelled and lit.** 21 billboard kit pieces, and their emissive contribution is what pushed the development negative — the one sheet where this build's light was too much rather than too little.
* **Times Square is paved as Times Square**: 28,482 polygons including **1,508 plaza** polygons and 623 crosswalk, and the pedestrian plaza's benches (**20**) and the traffic signals on their poles are in the frame.
* **The block is furnished for the crowd it gets**: **31 subway entrances**, 71 vent grates, 167 street lamps, 144 manholes, 109 hydrants, 24 bus-stop signs, 14 newsstands, 13 LinkNYC kiosks, and 393 Citi Bike dock units (Stage 40).
* **The fleet is a Times Square weekday fleet**: **20 yellow taxis, 14 sedans, 10 black cars, 7 boro taxis, 2 SUVs** — a taxi-heavy mix, which is right here — with the crowd clock reporting **a weekday** for 2024-06-27, which was a Thursday.
* **The render holds more contrast than the photograph** — standard deviation **0.3083** against **0.2257** (**1.366×**) — because a blank white screen beside a dark reflective soffit is as much range as a frame can hold.

## What does not match

* **The billboards carry no content.** This is the single largest visual gap on any sheet in the pass, because the subject matter of Times Square *is* its screens. It is a declared decision, not an oversight: the faces carry named material slots (`SIGN_FACE_LED_BLADE` on the LED pieces, `SIGN_FACE_BULLETIN` on the two bulletins) and a defined 0..1 UV, and what is missing is the runtime text binding that would fill them — engine-side work, recorded as DEVIATIONS B15a.
* **The subject is behind one of them.** Visible fraction **0.077**, carried by a single ray.
* **Only 12 of 43 height-probe rays found built fabric** — 31 passed through.
* **The Paramount Building's clock tower, the glass ball and the setbacks are absent** from the render's left half, where the photograph's subject stands.
* **Kit was capped harder than on any other sheet**: **116,174 pieces in range** against a **1,054,817-triangle** budget, so **5,703** were drawn — one piece in twenty. **5,381 of those are windows**, against 11 cornices, 11 string courses, 10 pilasters, 9 parapets and 7 quoins.
* **Not one tree is drawn from modelled branches** within 120 m; all **229** in range are impostor cards, and **1,197 tree rows did not fit** the props budget of **1,150,184** triangles.
* **No structures at all.** **0 tiles imported, 4 without a file, 0 triangles** — the only sheet in the pass with none, on a block that sits over the busiest subway interchange in the system.
* **Fifty-seven props across seven kinds were wanted in range and had no asset**: 21 misc structure, 12 artwork, 11 memorial, 5 drinking fountain, 5 parks building, 2 passenger-information sign, 1 parks comfort station.
* **A brighter midtone** — median **0.4992** against **0.3159** (**1.58×**), mean **0.4929** against **0.3711** (**1.328×**). The photograph's own median sits **1.146 stops** below the grey convention and the render's **0.245** above it, a **1.391-stop** difference (J83).
* **No cloud.** The reference's sky carries summer cumulus; nothing in this build reads a historical sky.
* **The crowd is a small fraction of the ask, and this is the place where that matters most.** The density table wanted **1,317 vehicles and 3,971 people**; **1,575 and 3,000** were simulated and **4,267** dropped — **1,275 pedestrians and 674 vehicles at the agent triangle budget**, 1,208 and 770 outside the radius, 210 pedestrians in the carriageway without crossing, 47 not on a walkable surface, 5 above the observer, and **37 riderless bodies**. Times Square on a June afternoon does not look like 255 people.
* **There is no park ground within 150 m to check** — **0 samples**. Beyond 400 m the under-fraction is **0.226** over 1,168 samples.
* **The frustum reports Times Square 59.8° off axis** at 234.7 m — the composite's centroid again, not the piece being looked at.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the billboards are blank | 21 billboard kit pieces are placed and lit with empty faces, by the rule the tile's own `sign_face_binding` states: an LED face models the display hardware and carries no image, a bulletin face is blank vinyl because no source here records what a New York bulletin advertises. No advertising copy was invented anywhere (DATA_CONTRACTS §6.1.1, DEVIATIONS B5/B15/B15a). This is what drives chroma to 0.31 of the photograph's | **declared decision — the `SIGN_FACE_*` slots and UVs exist; the runtime text binding is the open half (B15a)** |
| the development is negative, −0.39 stops | the emissive billboards raise the scene median to 0.236 against a 0.18 target, so the frame is pulled down rather than lifted — the only such sheet in the pass (J83) | verification — declared, and correct |
| the visible fraction is 0.077 | the walk's chosen point puts `lm_c_times_square.58` 13.1 m in front of the subject; the recorded viewpoint was boxed in at 3 m and this was the best of a bad set (J79, J88) | verification — open |
| 12 of 43 probe rays on fabric | the subject stands behind a screen structure and most of the fan passes it | verification |
| no Paramount clock tower or glass ball | the photograph's own subject is a different building from the item's, and its ornament is not a class this build models | reference + geometry |
| 116,174 kit pieces in range, 5,703 drawn | the kit triangle budget at 1,054,817 — the worst shortfall in the pass | **performance** |
| no modelled trees, 1,197 tree rows dropped | the props triangle budget at 1,150,184 triangles | performance |
| no structures on any tile | 4 tiles in range and none has a structures file, over the busiest subway interchange in the system | **data — open, four tiles unbuilt** |
| 57 props across seven kinds unmapped | no asset exists for those kinds | data |
| p50 1.58× | the photograph is developed 1.146 stops under the grey convention and the render 0.245 over it (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 255 people where the table asked 3,971 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
