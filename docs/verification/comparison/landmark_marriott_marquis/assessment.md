# New York Marriott Marquis

`landmark_marriott_marquis` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:W 46th St Duffy Square 11 - Marriott Marquis.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018-03-08 14:28:40, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:W_46th_St_Duffy_Square_11_-_Marriott_Marquis.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.758834, -73.98502 (NYC_TM -2957, 6534) at z 16.2 m NAVD88 | azimuth 255.0°, pitch +21.7° | 18 mm on 36 mm (67.4° horizontal, 90.0° vertical, portrait) | 852x1278. The camera stands on **this photograph's own EXIF GPS**, **123.0 m** from the item's recorded viewpoint — inside the 250 m at which it can still be the same view — and the heading is the bearing from that position to the subject; the item's recorded azimuth is 200.0°, **55.0° away**, and belongs to the nominal viewpoint. The walk **did not move it**, on a tight margin: the view azimuth is clear for **52.9 m** against a **47.7 m** requirement, the nearest built thing in the frame is `prop_lamp_cobra_davit_17` **34.5 m** away **dead ahead** at 0.0° yaw and 0.0° pitch, and the nearest simulated agent is 25.6 m away against a 60.0 m probe. The lens was **held at the 18 mm floor** and the record states the consequence: the top of the subject is still cut off, and it is in the published frame. The ground under it reads 14.601 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 14.52 to 15.44 m.

**Sun** — azimuth 224.4°, elevation 34.2° at 2018-03-08T14:28:40−05:00, from the photograph's own **EXIF DateTimeOriginal**; 803.8 W/m² direct normal, sky at strength 0.0348, Filmic, **+0.84 stops** metered and unclamped, against a linear median of **0.100285** and a target of **0.18**. The physical rule would have given **0.33 stops**, so this is one of the very few frames in the pass where the metered development and the physical one nearly agree — the scene arrived within a stop of a photographable level on its own.

**In the scene** — 4,500,177 triangles: 6 building tiles (332,446 tris, 0 missing, 0 LOD-substituted), 5 landmark models of which 1 can fall inside the 67.4° frame, 26,351 pavement polygons, 1,180 props, 4,720 kit pieces, 22 park-ground meshes, 21,408 triangles of structures, 65 vehicles and 254 people.

## Verdict — the tower is measured off its own geometry and comes out right; the photograph is half billboard and the render's billboards are blank, and the sheet's contrast gap is exactly that

**This is the case J74 was built for, working.** The nearest catalogue origin is `c_times_square`, **269.8 m** away and **past the 120 m** the old rule looked in, so the probe took the height from the geometry instead: **43 of 43 rays** on built fabric, **177.04 m** above a ground of 13.94 m, topping out at z **190.98 m**, on an object **30.0 m by 30.0 m** in plan that is **not a tile mesh**. The record says so in its own note. Under the previous rule this sheet would have inherited the composite's **365.8 m**, which is more than twice the hotel, and framed the shot for a building that is not there.

**The massing is recognisable and the sightline is the best in this batch.** All **13 of 13** rays are clear, **12 land on the subject**, one goes into nothing, and the visible fraction is **0.923**; **11** of them meet the subject's own fabric nearer than the recorded distance, first at **53.9 m** on `lm_c_times_square.21`. The render shows what the photograph shows: the round elevator core rising as a banded cylinder, the slab tower beside it, the deep horizontal bands of guest-room floors, the setback at the top of the atrium, and the tower's crown cut off by the frame exactly as the lens note warned.

**What is missing is the content on the glass, and it is measurable.** The photograph's lower half is two enormous billboards — a pink one filling a third of the frame and a theatre poster below it — and its brightest pixels **clip at 1.0**. The render carries **259 billboard kit pieces** and they are blank, by the rule the tile's own `sign_face_binding` block states and DEVIATIONS B15a records: no advertising copy is invented anywhere. The consequence is not a vague "looks less busy"; it is a **standard deviation of 0.1751 against 0.3383, a ratio of 0.518** — the render holds half the tonal range of the photograph — together with **chroma 0.0465 against 0.0673**, a ratio of **0.691**. On this sheet the blank vinyl is not a detail, it is most of the picture's dynamic range.

**And the exposure runs the other way here, which is worth saying because it is rare.** Across this pass the photographs sit *above* the grey convention and the renders below. Here the photograph's median sits **0.27 stops below** it and the render's **0.241 above**, a **+0.511-stop** difference, so the render is the **brighter** of the two at the midtone — p50 **0.4986** against **0.4227**, a ratio of **1.18**. That is a photographer letting the shade under a cantilever go black to hold a white billboard, and it is the correct exposure for that frame. The comparison is still an exposure comparison before it is a scene comparison (J83).

**One thing this sheet gets right that most of the pass does not, and one it gets wrong in the same breath.** The photograph is dated 8 March and the render drew **bare-canopy trees** — the date reached the props stage and set `leaf_off`, and the reference's own trees are leafless. The same date never reached the crowd: the people on the sidewalk are dressed for a fixed 15.0 °C on a March afternoon, because the crowd request carries position, hour, day type, seed and headlights and no weather at all (J97). One sheet, both halves of the fault, one of them working.

## What matches

* **The height, measured rather than looked up** — 177.04 m on 43 of 43 rays, from the geometry, because the nearest catalogue origin was 269.8 m away (J74).
* **The sightline** — 13 of 13 rays clear, 12 on the subject, a visible fraction of **0.923** and a clear fraction of **1.0**.
* **The massing.** The round elevator core, the slab tower, the banded guest-room floors and the atrium setback are all in the render and all in the photograph.
* **The crown is cut off in both the record and the picture.** The lens note says it will be, at the 18 mm floor with a +21.7° tilt, and it is — the record and the frame agree.
* **The trees are bare, from the photograph's own date.** `leaf_off` true for 8 March, and the reference's trees are leafless (J97's working half).
* **The billboards exist as hardware** — 259 pieces placed and lit, with named `SIGN_FACE_*` material slots and a defined 0..1 UV.
* **The development is nearly physical** — +0.84 stops metered against 0.33 by the physical rule, the closest agreement of the two on any sheet in this batch.
* **The block is furnished for Times Square** — 338 Citi Bike units, 180 cooling towers, 155 street lamps, 133 manholes, 89 hydrants, 53 subway vent grates, **22 subway entrances**, 27 LinkNYC kiosks, 14 newsstands.
* **The fleet is a Times Square fleet** — **20 yellow taxis** and **10 boro taxis** against 17 sedans, 8 black cars, 3 SUVs, 2 MTA buses, 3 box trucks and **1 Sanitation truck**.
* **26,351 pavement polygons and none dropped**, including **1,419 plaza** polygons and 534 crosswalk — Duffy Square's pedestrian surface is there.

## What does not match

* **The billboards carry no image.** Two of them are most of the reference frame. Declared (B5, B15, B15a), and the largest visual gap on the sheet.
* **Half the tonal range** — sd **0.1751** against **0.3383** (**0.518×**) — and **0.691** of the colour. Both are consequences of the line above.
* **No `MARRIOTT MARQUIS` lettering.** The photograph carries the name four times on the facade; no printed copy is invented anywhere.
* **The glass elevator bubble at the base is absent** from the render, where the photograph has it as the first thing the eye lands on.
* **Kit was capped to one piece in thirteen** — **4,720 drawn of 63,393 in range** at a **908,866-triangle** budget, of which 4,120 are windows; and **4,276 further pieces were suppressed** under landmark shells, so the tile's own buildings and their windows give way to the composite.
* **Props were capped to one in three** — **1,180 of 3,195 in range** at a **1,071,044-triangle** budget, **1,775 dropped for budget**, **1,351** of them tree rows, **18** dropped on a suppressed building.
* **Only 89 trees in range at all**, 6 from modelled branches and 83 as impostor cards, with 16 species substituted.
* **Five of six tiles in range have no structures file** — 1 imported, **5 without a file**, **21,408 triangles** — over the Times Square–42nd Street interchange, the busiest in the system. The same shortfall as the One Times Square sheet.
* **40 props across six kinds in range have no asset** — 21 misc structure, 7 artwork, 4 memorial, 4 real-time information sign, 3 vending machine, 1 drinking fountain.
* **The crowd is dressed for 15.0 °C on 8 March**, and the render drew **254 people** where the density table asked **4,071** — with **1,152 dropped at the agent triangle budget**, 1,129 outside the radius, 281 in the carriageway without crossing, **171 not on a walkable surface**, 13 above the observer, and 654 vehicles at the budget, 616 outside the radius, 32 riderless, 28 off the carriageway. **4,076 dropped** in total. Times Square on a weekday afternoon does not look like 254 people.
* **The near foreground is an empty grey plaza** across the bottom quarter of the render, where the photograph has a traffic signal, a lamp standard and the billboards' own scaffolding.
* **No cloud.** The reference's sky is a pale March haze; nothing in this build reads a historical sky.
* **There is no park ground within 150 m to check** — **0 samples**. Between 150 and 400 m the **z-fighting fraction reaches 0.0875** over 80 samples, the highest in this batch, and the under-fraction is 0.1375; beyond 400 m it is **0.2054** over 1,066 samples with a worst reading of **−1.663 m**. The redrape moved **183,090** vertices, up to 2.739 m up and 3.331 m down.
* **Six park surface kinds keep the builder's flat colour** — infield clay, hard sport court, park grass, recreation grass, rink ice and bare ground (J40).
* **The frustum reports Times Square 347.6 m away at 14.1° off axis** while the subject stands at 95.4 m — the composite's centroid again, not the member being looked at.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the billboards are blank | the faces model the display hardware and carry no image; no advertising copy is invented anywhere (the signage section of `docs/DATA_CONTRACTS.md`, DEVIATIONS B5, B15 and B15a). This is what drives sd to 0.518 and chroma to 0.691 of the photograph's | **declared decision — the `SIGN_FACE_*` slots and UVs exist; the runtime text binding is the open half (B15a)** |
| no facade lettering | the same rule | declared decision |
| no glass elevator bubble | the atrium's exterior lift enclosure is not a class this build models | geometry |
| p50 1.18, the render brighter | the photograph is developed 0.27 stops **below** the grey convention to hold a clipping billboard, and the render 0.241 above it (J83) | reference |
| 4,720 kit pieces of 63,393, and 4,276 more suppressed | the kit triangle budget at 908,866, plus the landmark shell replacing the tile's buildings | performance + declared decision |
| 1,180 props of 3,195, 1,351 tree rows dropped | the props triangle budget at 1,071,044 | performance |
| five of six tiles without a structures file | those tiles are unbuilt, over the Times Square–42nd Street interchange | **data — open, five tiles** |
| 40 props across six kinds unmapped | no asset exists for those kinds | data |
| the crowd in summer dress on 8 March | the crowd request never receives the render date's weather: temperature fixed at 15.0 °C, rain and snow cover at 0.00 (J97) | **verification — open, and the garments exist (J53, J62)** |
| 254 people of 4,071 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| z-fighting 0.0875 mid-range, under-fraction 0.2054 far | the park builder drapes on its own heightmap and the scene's differs; the redrape closes the bulk and leaves a −1.663 m tail (J71) | geometry — open, bounded |
| six park surface kinds flat | the texture catalogue has no photographic set for clay, court, grass, ice or bare ground (J40) | data — declared, named on the sheet |
| the frustum 347.6 m off a 95.4 m subject | the composite's catalogue centroid, not the member being looked at | verification — cosmetic |
