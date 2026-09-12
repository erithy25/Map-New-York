# Hugh L. Carey (Brooklyn-Battery) Tunnel Manhattan portal

`landmark_hugh_carey_tunnel_portal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:1-25 Broadway NYC rear 7.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-02-05 09:21:56, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:1-25_Broadway_NYC_rear_7.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.70207, -74.01509 (NYC_TM -5503, 226) at z 4.9 m NAVD88 | azimuth 200.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **459.4 m** away, past the 250 m rule. The recorded azimuth of 200.0° agrees with the bearing to the subject to **0.1°**. **The lens stayed at 35 mm and the axis stayed level**, because nothing built stands within 6 m of the subject's coordinate — the nearest is `t_-6_0_struct_seawall`, **36.7 m** away at bearing 45°. **The deck rule moved the camera to a parapet** (J65): the eye point stood on the roof of `t_-6_0_park_park_ground_grass`, which the item records as a single lat/lon for the whole deck, so the camera was *walked 6 m along the view azimuth to the parapet, the last point the roof still supports, which is where the reference photographs are taken*. From there the azimuth is clear for **150 m** and the nearest built thing is that deck **7.6 m** away. Ground under the camera reads **3.271 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 3.17 to 3.54 m.

**Sun** — azimuth 136.3°, elevation 21.3° at 2020-02-05T09:21:56−05:00, from the photograph's own **EXIF DateTimeOriginal**; 671.5 W/m² direct normal, sky at strength 0.0399, Filmic, **+0.76 stops and not clamped**. The linear frame's median is **0.106012** against a middle-grey target of 0.18; the physical rule would have given **+1.03 stops** — one of the few sheets where the physical rule asks for *more* than the meter (J83).

**In the scene** — 2,860,810 triangles: 4 building tiles (37,530 tris) with **2 missing**, 5 landmark models of which 1 falls inside the 54.4° frame — the ferry terminals, 4,006 m away — 17,133 pavement polygons with **0 dropped**, 628 props, 251 kit pieces, 12 park-ground meshes over 159 surfaces, 5 structures tiles (**108,008 tris**) with 1 without a file, 89 vehicles and 262 people, terrain 84,872 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the portal is not in the frame and the tonal comparison is void, because the reference is a clipped near-monochrome taken in fog

**Read the reference's statistics before anything else.** Ninety-fifth percentile **1.0**, chroma **0.0265**, median **0.1742**, development offset **−2.812 stops**. That is a February morning in fog with a blown white sky: the photograph is dark, almost colourless and clipped at the top. Against it the render's figures come out at median **2.859×**, chroma **2.479×** and **3.05 stops** of development apart. None of those is evidence about the build. This sheet is one of the 8 in the J93 survey sitting more than two stops from the grey convention, and one of the 13 whose reference clips at 1.0.

**And the subject is absent.** The stored subject coordinate has **no built fabric within the probe's 6 m reach** — the nearest is a seawall 36.7 m away — so 0 of 43 rays landed, no height was measured, the lens stayed at 35 mm, the axis stayed level and **no sightline was tested** (**J96**). The portal is 143.9 m away on the recorded bearing and nothing in the frame is it.

**What the frame does contain is Battery Park in February, and it is good.** **302 of 357 trees are drawn from modelled branches** — the highest proportion in this pass — with bare winter crowns, correct for 5 February. Benches, waste baskets and a lawn sit under them, a brick block stands on the left, and the harbour shows as a pale band beyond. As a picture of that park on that morning it is convincing; it is simply not a picture of a tunnel mouth.

**The mid-field ground is the worst band measured anywhere in this pass.** Between 150 and 400 m the park surface sits **under** the terrain on **0.7082** of 233 samples — seventy-one per cent — with a **median of −0.158 m**, the only band in the pass whose median is negative. Within 150 m the same surface is almost perfect at **0.0079** under over 378 samples, so the fault is again at the band boundary where the terrain grid coarsens (J85).

**Structures are the strongest part of the scene**: **108,008 triangles** over 5 tiles with only 1 missing — the Battery's seawall, the ferry racks and the tunnel's own vent structures are in that count, even though the portal itself is out of frame.

## What matches

* **The deck rule worked precisely** (J65): the camera was walked 6 m along the view azimuth to the parapet, the last point the roof supports, and the record says that is where the reference photographs are taken.
* **302 of 357 trees drawn from modelled branches** — the highest proportion in the pass — with bare February crowns.
* **The development is metered and unclamped**, +0.76 stops, and this is one of the few sheets where the physical rule asks for more (+1.03) than the meter.
* **Structures carry 108,008 triangles** over 5 tiles, 1 without a file.
* **The recorded azimuth agrees with the bearing to the subject to 0.1°.**
* **Near-field ground is sound**: within 150 m, **0.0079** of 378 samples under the terrain, median **+0.201 m**.
* **The pavement is complete**: 17,133 polygons, **0 dropped**.
* **The record names every limit**: the 36.7 m coordinate offset, the untested sightline, the 459.4 m reference fix it refused, and the two building tiles without shells.

## What does not match

* **The tonal comparison is void**: the reference clips at p95 1.0, carries chroma 0.0265 and sits 2.812 stops below the grey convention (J93).
* **The portal, its ventilation building and its sign are not in the frame**, and no sightline was tested (J96).
* **The only landmark in the frustum is 4,006 m away** — the ferry terminals.
* **Mid-field park ground is 0.7082 under the terrain with a median of −0.158 m** — the worst band in the pass (J85).
* **Seventy per cent of the props are missing**: 628 placed of **2,380 in range**, with **1,667 dropped for the triangle budget** of 1,361,444, 1 on a suppressed building and 3 cards dropped.
* **1,245 tree rows did not fit** that budget, and **0** of the 55 cards are procedural canopy stems.
* **Two of 4 building tiles have no shell file**, and park ground was not built for 2 tiles.
* **Thirty props across five kinds were wanted in range and have no asset**: 11 parks building, 9 artwork, 6 drinking fountain, 3 memorial, 1 parks comfort station. In Battery Park those are the Castle Clinton buildings and the memorials.
* **Every agent is at LOD2** — 89 vehicles and 262 people — and **254 pedestrians were dropped for standing in the carriageway without crossing**.
* **Eight park-ground surface kinds fall back to the builder's flat colour** (J40).
* **356 of 357 tree species were substituted.**

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tonal comparison is void | the reference is a clipped near-monochrome shot in fog; its own frame statistics say so and nothing tests them (J93) | **verification — open, J93** |
| the portal is not in the frame | the stored subject coordinate has no fabric within 6 m — the nearest is a seawall 36.7 m off — so no height, no tilt, no widened lens and no sightline (J96) | **data + verification — open, J96** |
| mid-field ground 0.7082 under the terrain, median −0.158 m | the terrain grid coarsens to 40 m beyond the near band while Battery Park's raised deck keeps its survey shape; the only negative band median in the pass (J85) | **geometry — open, and the worst instance measured** |
| 628 props of 2,380 in range, 1,245 tree rows dropped | the props triangle budget at 1,361,444, which dropped 1,667 | **performance** |
| 2 of 4 building tiles without a shell, 2 without park ground | no files were built for those tiles; the record names them | **data — open, measured** |
| 30 props across five kinds unmapped | no asset exists for those kinds, and here that kind is Castle Clinton and the memorials | **data — open** |
| every agent at LOD2, 254 pedestrians dropped in the carriageway | the LOD rule picks by distance, and the plaza where people stand is carriageway in the planimetric data | performance + **data, open** |
| eight park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 356 of 357 species substituted | the tree catalogue holds almost none of the species surveyed here | **data — open** |
