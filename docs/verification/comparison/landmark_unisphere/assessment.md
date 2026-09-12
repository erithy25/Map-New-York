# Unisphere

`landmark_unisphere` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Unisphere 2025.jpg by BakedintheHole, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2025-09-29 08:28:52, 1920x1446. [Commons page](https://commons.wikimedia.org/wiki/File:Unisphere_2025.jpg) — the view direction is derived from the image. The globe fills the frame from close range: the stainless grid of meridians and parallels, the raised continents, the three orbit rings, the tripod under it and the fountain basin's blue rim, with autumn trees behind and a cirrus sky.

**Camera** — 40.746092, -73.845542 (NYC_TM 8822, 5124) at z 8.3 m NAVD88 | azimuth 102.5°, pitch **−2.3°** | 35 mm on 36 mm (54.4° horizontal) | 1204x906. The camera stands on **this photograph's own EXIF GPS**, **127.9 m** from the item's recorded viewpoint, and its heading is the bearing from there to the subject — **47.6°** off the item's recorded 54.9°. It was **not moved**: view azimuth clear for **150.0 m** against a 23.5 m requirement, no simulated agent within 60 m, and the nearest built thing in the frame is `lm_b_unisphere.1` **5.4 m** away. The lens was not widened and the axis points **down**, and the record gives the reason for both: *"the highest built thing at the subject's coordinate is `lm_b_unisphere.1`, 1.0 m above the ground there -- below the 2 m at which a subject has a height worth aiming or framing by, so the lens was not widened to contain it"*, and *"aimed at Unisphere's own ground 47 m away -- nothing stands at its coordinate, so it is a surface, looked down into as the photograph does"*. The ground under the lens reads 6.688 m NAVD88, the 10th percentile of 113 samples within 12.0 m.

**Sun** — azimuth 109.5°, elevation **17.5°** at 2025-09-29T08:28:52−04:00, from the photograph's own **EXIF DateTimeOriginal**; 611.0 W/m² direct normal, sky at strength 0.0434, Filmic, **+0.67 stops**. Metered on a linear median of **0.113149**, nearly two thirds of the 0.18 target, so almost no lift was needed — and the physical rule would have asked for **1.32**, more than twice the measurement.

**In the scene** — 1,877,413 triangles, the lightest scene read this round: 4 building tiles (73,862 tris), 3 landmark models, 15,343 pavement polygons, 1,526 props with **nothing dropped for budget**, 104 kit pieces, 21 park-ground meshes, **3 tiles of structures (16,864 tris)**, 66 vehicles and **2 people**.

## Verdict — a forty-three-metre stainless globe was classified as a one-metre surface, because the object at its coordinate is the pool it stands in

**The Unisphere is not in the published frame.** What the render shows is the fountain basin seen edge-on as a pale curved band, a wide expanse of dark paving filling the lower two thirds, a line of trees along the horizon and a hazy morning sky. The globe, the tripod and the orbit rings are absent from the picture.

**The model is one of the better ones in this build.** Measured off `blender_out/landmarks/b_unisphere.glb`: eleven nodes, with `globe_grid` at **13,440 triangles** spanning 36.9 m in plan from z 5.95 to **42.83 m**, `continents` at 1,020 triangles of raised plates on the sphere, three orbit rings at 768 triangles each reaching **43.89 m**, a three-legged tripod topping at 6.69 m, a pedestal cap and a **94.5 m** fountain pool. The builder cites NYC Parks, the Landmarks Preservation Commission's LP-1927 designation report and the published dimensions: **140 ft = 42.67 m** high, **120 ft = 36.58 m** in diameter, on a **20 ft = 6.10 m** tripod in a **310 ft = 94.49 m** basin, and it states its own inferences — 24 meridians and 11 parallels because no published count exists, and the three orbit inclinations at about 28, 52 and 76 degrees to ±6 degrees.

**And the probe measured the pool.** 43 rays cast, **32 on built fabric**, and the object it reports is `lm_b_unisphere.1` at **1.0 m** above the ground. Node 1 of that file is the fountain pool's water plane; the pool itself tops out 0.35 m above the model's local zero, which is the 1.0 m the record carries above a terrain of 6.62 m. `probe.height_above_ground_m` is **null**. The catalogue entry **44.4 m** away carries **42.67 m** — the published height, correct to the centimetre — and it was not used, because J74 prefers a measurement and the measurement was of a puddle.

**The consequence runs through the whole camera.** 1.0 m is below the **2 m** floor at which this build treats a subject as having a height worth framing by, so: the lens was not widened from 35 mm; the axis was pitched **−2.3° downward** to look *into* what the record calls a surface; and **no sightline was tested at all** — there is no `subject_visible_fraction`, no ray count, no verdict on this record. A 42.83 m object 47 m from the lens went unframed, unaimed and unmeasured because the ray at its coordinate hit the water it stands over.

**This is J94's fault in its purest form.** On the Brooklyn Bridge the probe met a cable; on Two Times Square a tile roof membrane; here the pool. In all three the landmark is modelled, correctly, and the object standing at the coordinate is not it. J94's proposed repair — take the tallest member of the landmark model whose footprint contains the coordinate — would have found `globe_grid` at 42.83 m immediately, and the catalogue's 42.67 m was sitting 44 m away as a cross-check.

**Two measured things here are genuinely good.** Nothing was dropped for the props budget: **1,526 props** including **1,303 trees**, 85 benches and 65 street lamps, and the tree line across the render's horizon is the result. And the development is the second-lightest read this round at **0.67 stops**, below the physical rule's 1.32, on a morning scene that arrived nearly at a photographable level. What the tone does not match is the photograph's own exposure: the reference sits **1.458 stops above** the grey convention — a bright open frame — against the render's 0.213, a gap of **−1.245 stops**, so p50 comes out at **0.675×** and the render is much the darker half.

**And 1,087 of the 1,303 trees are a substituted species** — 83 per cent, the highest share read this round on a sheet drawing more than a thousand (J108). Flushing Meadows' planting is oak, London plane, pin oak and Norway maple in the census; ten species with two states is what the asset set has.

## What matches

* **The model is properly built**: 13,440 triangles of meridian-and-parallel grid to 42.83 m, 1,020 triangles of raised continents, three orbit rings to 43.89 m, a tripod and a 94.5 m basin, with the published dimensions cited and every inference stated.
* **The catalogue's height is exactly right**: 42.67 m, the published 140 ft, 44.4 m from the coordinate.
* **Nothing was dropped for the props budget**: 1,526 placed, including 1,303 trees, and **63 of them drawn from modelled branches**.
* **The development is the second-lightest read this round**, 0.67 stops on a linear median of 0.113149, and below the physical rule's 1.32.
* **The park ground is correct where the camera can see it**: 283 samples within 150 m, `under_frac` **0.0**, median clearance +0.193 m.
* **The camera is the photograph's own GPS**, not moved, with 150.0 m of clear view.
* **Structures are here**: 3 tiles imported for 16,864 triangles, with only 1 tile lacking a file.
* **Two people in the frame is defensible.** This is a park path at 08:28 and the ring is thin: only 48 pedestrians were dropped for being outside the radius and 8 for not standing on a walkable surface.
* **The scene is the lightest read this round**, 1,877,413 triangles, because Flushing Meadows is mostly open ground — which is the right shape for the place.

## What does not match

* **The Unisphere is not in the frame.** A 42.83 m globe 47 m from the lens, and the picture is basin, paving, trees and sky.
* **The probe measured 1.0 m of fountain pool** at the subject's coordinate, and `height_above_ground_m` is null (J94).
* **No sightline was tested at all** — no fraction, no rays, no verdict — because 1.0 m is under the 2 m floor.
* **The lens was not widened and the axis was aimed down**, both as a direct consequence of that 1.0 m.
* **The heading is 47.6° off the item's own recorded azimuth**, because it is the bearing from a GPS fix 127.9 m away to a coordinate rather than the view the item describes.
* **The render is much darker than the photograph**: a **−1.245-stop** exposure gap, mean 0.842× and p50 **0.675×**, because the reference sits 1.458 stops above the grey convention (J83).
* **1,087 of the 1,303 trees are a substituted species** — 83 per cent (J108).
* **The park ground sinks in the middle distance**: 0.2958 of 409 samples in the 150 to 400 m band, worst case −2.401 m, and 0.2033 of 1,259 beyond 400 m with a worst case of −3.875 m. **1,301 faces were cut for landmark ground.**
* **The fountain has no water and no jets.** The pool water plane is modelled; the jets and the basin plumbing are on the builder's explicit not-modelled list, and the reference's basin is full.
* **Forty-four of the sixty-six vehicles are sedans and seventeen are SUVs** on the Grand Central Parkway beside the park — a plausible mix, but with only one yellow cab, one boro taxi, one black car, one box truck and one police car it reads as a private-car fleet rather than a park-edge arterial.
* **The continents are a 4-degree outline.** The builder states it: raised plates generated from a coarse continental outline rather than a coastline dataset, so the shapes are schematic where the photograph's are legible.
* **No cloud.** The photograph's sky is a full cirrus deck across the whole frame; the render's is a Nishita dome at strength 0.0434.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| eleven nodes: globe_grid 13,440 triangles from z 5.95 to 42.83 m on a 36.9 m plan, continents 1,020 triangles, three orbit rings of 768 each to 43.89 m, tripod legs to 6.69 m, pedestal cap, and a 94.5 m fountain pool | the accessor `count` and `min`/`max` of every primitive of every node of `blender_out/landmarks/b_unisphere.glb`, read from the binary glTF header |
| node 1 of that file is the pool's water plane, topping 0.35 m above the model's local zero | the same bounds, for the node the record names as `lm_b_unisphere.1` |
| the published dimensions — 140 ft high, 120 ft or 36.58 m in diameter, 350 short tons, a 20 ft tripod and a 310 ft or 94.49 m basin — and the stated inferences | the dimensions block of `blender/landmarks/b_unisphere.py`, citing NYC Parks, LPC designation report LP-1927 and Wikipedia, and declaring the 24 meridians, 11 parallels and three orbit inclinations as inferred |
| the fountain jets and basin plumbing are on the not-modelled list | the same file's closing note |
| the 2 m floor below which a subject has no height worth framing by | the record's own lens and probe notes, which state the threshold |
| the second-lightest development and the lightest scene read this round | this sheet's 0.67 stops and 1,877,413 triangles, against the forty-six sheets read in the preceding rounds |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Unisphere is not in the frame | the probe measured 1.0 m of fountain pool at the subject's coordinate, that fell below the 2 m framing floor, so the lens was not widened, the axis was pitched down into what the record calls a surface, and no sightline was tested. The model is 42.83 m tall and the catalogue's 42.67 m was 44 m away (J74, J94) | **verification — open, and the purest case of J94 in the pass** |
| no sightline verdict on the record | the same 2 m floor | **verification — open** |
| the heading is 47.6 deg off the item's azimuth | the heading is the bearing from a photograph's GPS fix 127.9 m away to the subject's coordinate, rather than the view the item records | verification — open |
| 1.245 stops of exposure difference | the photograph was developed 1.458 stops above the grey convention and the render is metered to 0.213 above it (J83) | reference — declared, and correct |
| 1,087 of 1,303 trees are a substituted species | the asset set is ten species with two states (J108) | **data — open** |
| the park ground sinks in the middle distance and beyond | the park surfaces were draped on the fine grid and the terrain coarsens to 40.0 m; 1,301 faces were cut for landmark ground (J40, J96) | verification — declared |
| no water jets in the fountain | the jets and the basin plumbing are on the builder's explicit not-modelled list | **declared decision** |
| the continents are schematic | raised plates from a coarse 4-degree continental outline rather than a coastline dataset, declared by the builder | data — declared, no source used |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
