# Washington Square Arch

`landmark_washington_square_arch` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Washington Square Arch and the Empire State Building, Greenwich Village, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-16 18:16:58, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Washington_Square_Arch_and_the_Empire_State_Building,_Greenwich_Village,_Manhattan,_New_York.jpg) — the view direction is derived from the image at **high** confidence. It is the frontal frame the item's own viewpoint describes: the whole arch square-on from the fountain's south rim, the Empire State Building framed in its opening, the attic inscription and the spandrel figures legible, and a crowd of thirty-odd people with a print seller's work laid on the paving.

**Camera** — 40.730926, -73.997326 (NYC_TM -3998, 3435) at z 10.2 m NAVD88 | azimuth 44.7°, pitch +0.5° | 20 mm on 36 mm (68.8° horizontal, 84.8° vertical, **portrait**) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, **14.2 m** from the item's recorded viewpoint, and was **not moved**: `moved: false`, offset 0.0 m, view azimuth clear for **76.5 m** against a 20.0 m requirement, and **no simulated agent within 60 m**. The nearest built thing in the frame is `prop_tree_honeylocust_large_1` **12.2 m** away at +34.4° yaw and +42.4° pitch. The lens was widened from 35 mm to 20 mm so a level axis contains the subject, and the record declares the cost: *"the verticals converge, so this frame is not comparable with the photograph on proportion"*. The ground under the lens reads 8.612 m NAVD88, the 10th percentile of 113 samples within 12.0 m, range 8.56 to 9.13 m.

**Sun** — azimuth 271.7°, elevation **14.1°** at 2026-04-16T18:16:58−04:00, from the photograph's own **EXIF DateTimeOriginal**; 542.9 W/m² direct normal, sky at strength 0.0479, Filmic, **+2.79 stops**. Metered: the linear median is **0.02599** against the 0.18 target, so the development is **2.792 stops**, unclamped. The physical rule would have given **1.61**. A 14° evening Sun due west, against a camera looking north-east, lights the arch's west return and leaves its south face in shade.

**In the scene** — 3,890,139 triangles: 4 building tiles (425,690 tris), 1 landmark model, in the 68.8° cone, 17,942 pavement polygons, 582 props, 3,883 kit pieces, 24 park-ground meshes, **0 triangles of structures**, 88 vehicles and 433 people.

## Verdict — the arch is a plain pale mass with one column on it, and the camera is turned eighteen degrees off the view the item describes

**What the published frame contains is one pier of the arch, seen obliquely, with no relief on it at all.** The model is **1,072 triangles** with an LOD1 of 208, and at 27.2 m in a 68.8° frame the whole of it reads as a flat pale wall carrying a cornice band at the attic and a single engaged Doric column with a plain capital. There is no spandrel sculpture, no attic inscription, no eagle, no rosettes in the soffit, and neither of Washington's two statues. The photograph's arch is a marble relief composition from top to bottom; this is its envelope.

**And the opening is not in the picture.** The camera's heading is **44.7°**, the bearing from the photograph's GPS to the item's subject coordinate. The item's own recorded azimuth is **26.8°** — *"looking north through the Arch up Fifth Avenue"* — and the two are **17.9° apart**. From 17.9° off the arch's own axis at 27 m the near pier and the attic occlude the void behind them, and the sightline says so numerically: of 13 rays, **7 land on the arch and only 1 passes through into nothing**. So the single most quoted thing about this monument, that you see Fifth Avenue and the Empire State Building through it, is absent from the render because the lens was aimed at a point rather than along a view.

**The tone, by contrast, is the second closest agreement in the whole pass.** The render's median sits **0.245 stops** from the grey convention and the photograph's **0.26** — a gap of **−0.015 stops**, second only to the Bronx-Whitestone Bridge across all 171 measured sheets. Mean comes out at **1.007×**, p50 at **0.995×** and chroma at **0.941×**. That is as close as this build gets to a photograph on brightness and colour together.

**The contrast is where the missing relief shows up.** Standard deviation **0.1458** against the photograph's **0.2338**, a ratio of **0.624**, and the two tails tell the same story: the render's 5th percentile is 0.2078 against 0.1006 and its 95th is 0.7227 against 0.8035. A marble arch in raking 14° light is almost entirely shadow structure — undercut cornices, deep spandrels, the shaded soffit of the opening — and a plain wall with one column has none of it to cast. The tone matches; the modelling does not.

**Two things on this sheet are the best in the pass.** The park ground has the **lowest under-terrain fraction of any sheet**: 0.0257 over 1,322 samples, with **0.0 over 604 samples inside 150 m** and a median clearance of +0.192 m. And **178 of the 237 trees are drawn from their modelled branches** — the highest count read this round — with only 59 as cards. The kit was also **not capped**: all 3,883 pieces in range were drawn, including 32 cornices and 31 string courses.

**The measured height is very good and almost nothing measured it.** 43 rays were cast and **3 landed on built fabric**, giving **23.03 m** above a ground of 8.44 m against a catalogue 23.47 m — **within half a metre**. Three of forty-three is the correct answer for an arch: the vertical fan around the coordinate passes through the void, and the record reports the ratio rather than hiding it.

## What matches

* **The height, to under half a metre.** 23.03 m measured against a catalogued 23.47 m, on a plan extent of 20.1 by 10.5 m — and only 3 of 43 rays found fabric, which is what a void does to a fan.
* **The tone is the second closest in the pass**: a 0.015-stop exposure difference, mean 1.007×, p50 0.995×, chroma 0.941×.
* **The park ground is the best in the pass**: 0.0257 under across 1,322 samples, 0.0 across 604 samples inside 150 m, and only 44 faces cut for landmark ground.
* **The canopy is mostly real branches**: 178 of 237 trees drawn from modelled geometry within 120 m, mean scale 0.944, one outside the band.
* **The kit was not capped**: 3,883 of 3,883 in range, with 32 cornices, 31 string courses, 44 entrance doors and 159 window accessories — the Village's brick and brownstone blocks are properly dressed, and it shows in the render's flanking buildings.
* **The park is furnished as Washington Square**: **226 benches**, 73 street lamps — including the twin park lamp `prop_lamp_park_twin_3` that the sightline's nearest landing is on, 17.1 m from the lens, and the twin lamps are visible in the render — 31 waste baskets, 8 manholes, 6 hydrants and a flagpole.
* **The sightline is completely unobstructed**: 13 of 13 rays clear, a clear fraction of **1.0**, and 7 of them land on the arch.
* **The lens is in portrait**, 68.8° by 84.8°, matching a 1920 by 2560 reference.
* **The fleet is a Village fleet**: 29 yellow taxis of 88 vehicles with 33 sedans, 11 SUVs, 7 black cars and a bus.
* **The Sun is the real minute** of a real Thursday evening, from EXIF, and the development is metered to it.

## What does not match

* **The arch has no relief.** 1,072 triangles: a cornice band, one engaged column, and flat faces. No spandrel figures, no attic inscription, no soffit rosettes, no statues of Washington.
* **The frame is 17.9° off the view the item describes**, so the opening is occluded and the Empire State Building is not framed in it. Only one ray of thirteen passes through the arch.
* **The verticals converge and the photograph's do not.** 20 mm at 27 m against a photograph made to hold the arch square; the record declares the two halves incomparable on proportion.
* **The contrast is five eighths of the photograph's**, sd 0.624×, because there is no modelled shadow structure on the subject.
* **The trees are in full summer leaf on 16 April.** The date is **one day** past the build's leaf-off threshold of 15 April, so the binary switch puts every tree in the scene into full canopy, where the photograph shows the sparse fresh leaf of mid-April (J97). The single large tree at the right of the render is denser than anything in the reference.
* **211 of the 237 trees are a substituted species** (J108).
* **The fountain is absent — and the fountain is where the photograph was taken from.** The item's viewpoint is *"south rim of the Washington Square fountain"*, and 16 props across six kinds had no asset: **9 drinking fountain**, 3 artwork, 1 memorial, 1 parks building, 1 parks comfort station, 1 swimming pool.
* **The plaza is empty.** 433 people are drawn in the frame's radius and none of them is on the paving in front of the arch, because **179 were dropped for not being on a walkable surface** — Washington Square's plaza is park ground, not a road-network sidewalk (J101). The photograph's foreground is thirty people and a print seller.
* **Three quarters of the props in range were dropped.** 582 drawn of 2,979 at a 1,319,857-triangle budget, **2,241 dropped**, including **1,318 tree rows**, with 9 impostor cards dropped as opaque.
* **No structures at all**: 0 tiles imported, 4 without a file, 0 triangles — one of the nineteen sheets in the pass with none, over the West Fourth Street junction.
* **433 people and 88 vehicles** where the density table asked for 504 vehicles and 3,734 people; 560 and 2,999 were simulated and **3,038 dropped** — 1,141 pedestrians outside the radius, 996 at the 1,125,000-triangle agent budget, 285 vehicles outside the radius, 234 in the carriageway without crossing, 179 not on a walkable surface, 174 vehicles at the budget, 16 inside buildings and 13 riderless bodies.
* **Every agent is at the coarsest LOD**: all 88 vehicles and all 433 people at LOD2.
* **No cloud.** The photograph carries a broken evening cumulus that is most of its sky; the render's is a Nishita dome at strength 0.0479.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the arch is 1,072 triangles beside an LOD1 of 208 | the accessor `count` of every primitive of every node of `blender_out/landmarks/b_washington_square_arch.glb` and its `_lod1` companion, read from the binary glTF header |
| the second closest tonal agreement of the 171 measured sheets | ranked over every sheet whose `frame_stats.json` matches the render beside it, on the absolute `render_over_reference.exposure_offset_stops`; the closest is the Bronx-Whitestone Bridge at 0.007 stops against this sheet's 0.015 |
| the lowest park-ground under-terrain fraction of any sheet in the pass | ranked over every record carrying `parkground.terrain_clearance.bands.all_draws` with at least 500 samples; this sheet's 0.0257 over 1,322 samples is the lowest, ahead of Fort Jay at 0.0596 and the Metropolitan Museum at 0.0626 |
| the highest count of trees drawn from modelled branches read this round | this sheet's 178 of 237, against the thirty-six sheets read in the preceding rounds |
| 16 April is one day past the leaf-off threshold | the `leaf_off` rule in `blender/verify/render_sheets.py`, true for a date on or before 15 April, so 16 April is drawn in full canopy (J97) |
| the opening is occluded from this angle | the record's own sightline: 7 of 13 rays land on the arch and 1 passes through into nothing, at a heading 17.9 deg off the arch's own axis |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the arch has no relief | 1,072 triangles of envelope; spandrel sculpture, an inscription and statuary are not derivable from a footprint and a height, and no scan exists under an open licence | **geometry — declared by its triangle count** |
| the frame is 17.9 deg off the item's own azimuth, so the opening is not in it | the heading is the bearing from the photograph's GPS to the subject's coordinate rather than the direction the item records or the photograph faces; a point is not a view (the same fault as the Barclays Center canopy and J74's shape) | **verification — open** |
| the verticals converge | 20 mm at 27 m is the widest the build will go, and the record declares the two halves incomparable on proportion | verification — declared |
| the contrast is 0.624 of the photograph's | there is no modelled shadow structure on the subject to catch a 14 deg Sun | geometry — consequence of the above |
| full summer canopy on 16 April | the leaf switch is binary with a 15 April threshold and the photograph was taken one day after it (J97) | **declared decision — the rule is stated and it has two positions** |
| 211 of 237 trees are a substituted species | the asset set is ten species with two states (J108) | data — open |
| the fountain is absent | no asset exists for the drinking fountain, artwork, memorial or parks building kinds (J58 remainder) | **data — open, and this sheet's own viewpoint is the fountain's rim** |
| nobody on the paving in front of the arch | the crowd's walkable test reads only road-network sidewalk classes, so a park plaza is not standable and 179 bodies were dropped for it (J101) | **verification — open** |
| 2,241 props dropped, 1,318 of them trees | the props triangle budget at 1,319,857 triangles | performance |
| no structures on any of the 4 tiles | four tiles in range and none has a structures file; 19 sheets in the pass share it | data — open |
| 433 people where the table asked 3,734 | the 1,125,000-triangle agent budget plus the placement rules | performance + verification |
| 7 boro taxis in the Village | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
