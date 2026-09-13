# Staten Island ranch houses

`street_staten_island_ranch_houses` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Typical house in Dongan Hills (built in 1960).jpg by MJPlante1, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), stored date 2024-09-27, 1280x681, no camera GPS, viewpoint confidence **low**. A yellow-clapboard single-storey ranch house of 1960 **buried in snow**: drifts up to the sill of its picture window, a mounded path cut to the front door, the roof carrying a hand's depth of it, evergreen shrubs turned into white cones, bare trees against a white sky, an American flag on the neighbour's porch, and in the foreground a parked car showing nothing but its roof and one wing mirror.

**Camera** — 40.548, -74.145 (NYC_TM -16523, -16852) at z 16.786 m NAVD88, a 1.6 m standing eye over terrain read at 15.186 m — the 10th percentile of 113 samples within 12.0 m, whose range is 15.03 to 17.27 | azimuth 0.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1280x680. The camera is on the item's recorded viewpoint because the file carries no GPS, and the walk moved it **9.7 m** onto a roadbed polygon: *"inside `t_-17_-17_tar_roof` (a ray straight up from the eye point hits its roof)"* — the fifth sheet in the pass whose camera was placed or moved by that test (J115). From there the view is *"clear for 60 m"*, no agent stands within 20 m, and the nearest built thing is `t_-17_-17_vinyl_siding` **17.5 m** away at -27° yaw and **+8° pitch** — a house whose nearest visible point is two and a half metres above the lens.

**Sun** — azimuth 244.5°, elevation 23.9° at 2024-09-27T16:30:00-04:00. The date is the photograph's and the hour is not: *"photograph date, no time, and 16:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (244 deg) comes closest to the view azimuth (0 deg), 116 deg off, so the Sun is behind the camera and lights what it looks at."* On a due-north view no hour puts the Sun behind the camera, and the rule says so by printing 116° rather than hiding it. 706 W/m² direct normal, Nishita sky, Filmic, **+1.00 stops**. Metered: **0.998 stops** on a linear median of **0.090143** against a physical rule of 0.86.

## Verdict — a blizzard photograph dated in September, and a render that is three quarters hillside

**The stored date is 27 September and the picture is a snowstorm.** `photo_instant` read that date, found no time beside it, and chose 16:30 to light the view. No snow falls on New York in September; the date on the file is when it reached Commons, not when the shutter opened, and the photograph is plainly a scan — its grain, its colour cast and its 1960 house all say so. The render is therefore a clear late-September afternoon set against a blizzard. **This is the third reference photograph in the pass whose subject is snow**, and the screen that found the other two searched item names and photograph titles for winter words; this title is *"Typical house in Dongan Hills (built in 1960)"* and contains none, so the count of two in J114 is a lower bound and this is the sheet that proves it.

**And there would be no snow at any date.** `rain_mm_h` is 0.00, `temperature_c` 15.0 and `snow_cover` 0.00 on every one of the 172 sheets (J97), so the drifts, the mounded path, the loaded roof and the buried car have no counterpart the renderer could produce.

**Three quarters of the render is a hillside.** The camera sits in a dip at 15.19 m and the ground north of it climbs to **19.81 m at 28 m out** — 4.6 m in 28 m — before falling away again. Measured across the frame, the terrain's own crest stands **+7.19° above the horizon on the left, +5.95° dead ahead and +3.93° on the right**, against a vertical half-angle of **15.3°**. So the ridge fills the picture from its bottom edge to roughly a quarter of the way down from the top, and everything beyond 60 m sits below it and is hidden: the profile from 80 m to 300 m runs between -0.73° and 0.00°, entirely behind the crest. What is left above the ridge is the upper storeys of two building shells with their bases occluded, a yellow clapboard one at the left and a red-brick one at the right, and a strip of sky.

**The relief is real and the road through it may not be.** Dongan Hills has that ground; the 1 m DEM carries it and the record's own ground detail confirms 15.03 to 17.27 m within twelve metres of the lens. What a residential street does not have is a four-and-a-half-metre earth bank across it at twenty-eight metres, so either the roadway climbs the ridge and the render is honest about a steep block, or the road's cut is missing from the terrain and the pavement is buried in it. This sheet cannot settle which, and says so rather than guessing.

**The vinyl siding is there and it is the nearest thing to the camera.** `t_-17_-17_vinyl_siding` at 17.5 m: the left-hand shell in the render is clapboard, correctly, on the sheet whose neighbour item is named for that material and does not show it.

**The roofs are pitched and the roofscape is not.** **1,316 of this tile's 1,613 buildings carry a roof pitch** — 10°, 22°, 30° or 38° — with an eave elevation beside it, and the shells honour them: **388 of 6,185 sampled triangles in `tile_buildings.glb` are sloped**, neither wall nor flat roof. So the ranch house's roof *form* is modelled. What is absent is everything on it. The kit is **174 assets in 20 categories** and not one of them is a roof, an eave, a gable end, a dormer, a chimney, a shutter, a porch or a garage door: the vocabulary is storefronts (36 assets), fire escapes, parapets, water towers and billboards, which is a commercial and apartment vocabulary, and **97 parapets** were placed on a block of houses that mostly have eaves.

**The scene is the sparsest streetscape in the pass and correctly so.** 1,762,221 triangles against four and a half million on a Midtown sheet. **3,951 props with none dropped**, of which **3,814 are trees** — and the whole rest of the inventory is 77 manholes, 29 hydrants, 30 street lamps and one mailbox. No bench, no waste basket, no bike rack, no bus shelter, no Citi Bike dock, no newsstand, no LinkNYC kiosk: outer Staten Island has none of those and neither does the render. **1,645 kit pieces**, the smallest count read this round.

**Two yellow cabs and no boro taxi.** The 52 vehicles are 38 sedans, 9 SUVs, 2 box trucks, a DSNY truck and **2 yellow medallion cabs**, with **no green Street Hail Livery cab at all**. Staten Island is the borough where a cruising yellow cab is a genuine rarity and where the boro taxi is the licensed fleet, so this frame has the exclusion-zone inversion the wrong way round twice over (J105). Every one of the 52 vehicles and all 48 pedestrians are at LOD2.

**Snow does to this photograph what it did to the Brooklyn one.** The reference's median sits **1.52 stops above** the grey convention and its 95th percentile is 0.9669; the render is metered to 0.238 above. The gap is **-1.282 stops** with the render darker, the p50 ratio **0.668**, contrast **0.607** and chroma **0.573**. All four are measuring the weather.

**No park ground at all**: 0 meshes and 0 surfaces, with 6 tiles in the 720 m radius carrying no park-ground file.

## What matches

* **The vinyl siding is modelled and is the nearest building to the lens.**
* **The roof pitches are in the data and in the geometry**: 1,316 of the tile's buildings carry one and the shells build them.
* **The street furniture is correctly almost absent**: 77 manholes, 29 hydrants, 30 lamps, one mailbox, and none of the dense-borough kinds.
* **Nothing dropped from the props budget** and nothing capped in the kit.
* **3,814 trees** on a block where the canopy is most of what is not house.
* **Building tiles complete**: 6 of 6, 191,562 triangles, none missing, none LOD-substituted.
* **The hour is declared as chosen and its own weakness printed**: 116° off the view azimuth, which the record states rather than rounds.
* **The development is small**: 0.998 stops against a physical rule of 0.86.

## What does not match

* **No snow**, on a photograph that is nothing but snow (J97).
* **A late-September afternoon** against a blizzard, because the file's stored date is 27 September and the exposure plainly is not (J114).
* **Three quarters of the frame is a terrain ridge** 28 m away, hiding everything beyond 60 m.
* **The houses stand above the lens with their bases occluded**, the nearest at +8° of pitch.
* **No roof, eave, gable, dormer, chimney, shutter, porch or garage door in the kit** — 174 assets in 20 categories and not one of them.
* **97 parapets** on a block of pitched-roof houses.
* **1.282 stops darker, p50 0.668, contrast 0.607, chroma 0.573** — all four ratios measuring the storm.
* **Two yellow cabs and no boro taxi on Staten Island**, which is the exclusion-zone inversion twice over (J105).
* **No park ground**: 0 meshes and 0 surfaces over 6 tiles with no file.
* **No signage of any kind** (J110), no flag, no mailbox at the kerb, no fence, no driveway and no parked car in the near field.
* **Every agent at LOD2.**

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the ground rises 4.6 m to 19.81 m at 28 m north of the camera, and the terrain's crest stands +7.19, +5.95 and +3.93 deg above the horizon across the frame | sampling `data/processed/tiles/t_-17_-17/terrain.png` with its own `z_min_m` and `z_scale_m` along bearings inside the record's field of view, against the record's camera position and eye height |
| everything from 80 m to 300 m out lies between -0.73 and 0.00 deg and is therefore behind that crest | the same profile, continued north to 400 m |
| the frame's vertical half-angle is 15.3 deg | the record's 54.432 deg horizontal on a 1280 by 680 frame |
| 1,316 of this tile's 1,613 buildings carry a roof pitch of 10, 22, 30 or 38 deg with an eave elevation, and 297 are flat | the `roof_pitch_deg`, `roof_type` and `roof_eave_z` columns of `data/processed/tiles/t_-17_-17/buildings.parquet` |
| 388 of 6,185 sampled triangles in the tile's shells are sloped, neither wall nor flat roof | computing face normals from positions and indices in `blender_out/tiles/t_-17_-17/tile_buildings.glb` |
| the kit is 174 assets in 20 categories and none of them is a roof, eave, gable, dormer, chimney, shutter, porch or garage door | the `category` field of every entry in `data/processed/kit_catalog.json` |
| 1,645 kit pieces | the sum of the record's `scene.kit.per_category`, whose `total` is null |
| this is the third reference photograph in the pass whose subject is snow, and the title screen that found two cannot find it | the winter-word screen over item names and photograph titles recorded in DEVIATIONS J114, against this photograph's own title |
| 27 September is outside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no snow | the snapshot request carries no weather at all, so rain, temperature and snow cover are the defaults on every sheet (J97) | **verification — open** |
| a September instant on a blizzard | `photo_instant` takes the stored date at face value; on a scan, that date is the upload and not the exposure, and nothing reads the picture or its description to disagree (J114) | **verification — open** |
| three quarters of the frame is a ridge | the camera was snapped to a roadbed polygon in a dip and the terrain north of it climbs 4.6 m in 28 m; whether the road's own cut is missing from the DEM cannot be settled from this record | **data or verification — open, and undetermined** |
| no roof, eave, dormer, chimney, shutter or porch | the kit vocabulary was built for commercial and apartment facades; the detached-house vocabulary does not exist | **content — open, and the largest single gap for the outer boroughs** |
| 97 parapets on pitched-roof houses | the kit places a parapet where a shell presents a flat top, which is right for the 297 flat-roofed buildings on this tile and wrong wherever it lands on the other 1,316 | content — open |
| all four tone ratios off | snow puts a photograph's median 1.52 stops above the grey convention and flattens its shadows; the render has neither (J83's metering doing exactly what it should) | reference — the weather, not the render |
| two yellow cabs and no boro taxi | `TrafficSim::sampleClass` splits the taxi share 70/30 with no geography, so the borough that should be almost all green gets none (J105) | **runtime — open** |
| no park ground | 6 tiles in range carry no park-ground file | data — open |
| no signage, flag, fence, driveway or parked car | the verification renderer never reads the sign export and the props catalogue has 34 kinds of which 20 appear anywhere in the pass; none of these is among them (J110) | **verification and content — open** |
