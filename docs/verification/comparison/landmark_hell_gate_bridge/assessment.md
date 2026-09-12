# Hell Gate Bridge

`landmark_hell_gate_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Hell Gate Bridge (84462)p.jpg by Rhododendrites, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-05-18 12:22:17, 1920x838. [Commons page](https://commons.wikimedia.org/wiki/File:Hell_Gate_Bridge_(84462)p.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.78000, -73.92500 (NYC_TM 2110, 8884) at z 1.6 m NAVD88 | azimuth 307.2°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x558. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is 134 m away and the eye point there is **inside `lm_b_rfk_triborough.55`** — a ray straight up from it hits that roof — while the recorded viewpoint is in open air. The recorded azimuth of 307.2° agrees with the bearing to the subject to **0.1°**. **The lens stayed at 35 mm and the axis stayed level**, and the record says why: nothing built stands within 6 m of the subject's coordinate, the nearest built thing being `lm_b_rfk_triborough.28` **74.2 m** away at bearing 338°. The camera was not moved — **nothing built stands within 60 m of the lens**, no agent either, and the azimuth is clear for **150 m**. Ground under the camera reads **0.0 m** NAVD88 from 16 heightmap samples within 5.0 m whose range is **0.0 to 0.0 m** — the flattened water surface of the East River.

**Sun** — azimuth 161.0°, elevation 67.9° at 2019-05-18T12:22:17−04:00, from the photograph's own **EXIF DateTimeOriginal**; 934.9 W/m² direct normal, sky at strength 0.0306, Filmic, **+0.80 stops and not clamped**. The linear frame's median is **0.103636** against a middle-grey target of 0.18 (J83); the physical rule would have given 0.0.

**In the scene** — 1,598,889 triangles: 10 building tiles (316,540 tris, none missing), **2 landmark models and 0 of them inside the 54.4° frame**, 14,997 pavement polygons with **0 dropped**, 2,476 props, **no kit at all**, **0 park-ground meshes**, 57 vehicles and 35 people, terrain 229² at 2.0 m near / 40.0 m far.

## Verdict — the Hell Gate Bridge is modelled, 23,788 triangles of it, and it stands 495 metres away outside this frame while the Triborough's approach fills the picture from fourteen metres

**The subject exists.** `b_hell_gate` is placed in this scene at LOD 0 with **23,788 triangles**, 495.3 m from the camera. It is not in the frame. What is in the frame is `b_rfk_triborough` — **14.2 m from the lens**, 80,446 triangles — whose concrete piers and steel truss fill the upper half of the render, with the East River below and the Astoria shoreline beyond.

**The chain that produced this is legible step by step.** The item's stored subject coordinate has **no built fabric within the probe's 6 m reach**: the nearest is 74.2 m away, and it belongs to the Triborough, not to Hell Gate. So 0 of 43 rays landed, no height was measured, the lens stayed at 35 mm, the axis stayed level, and **no sightline was tested** — one of the 13 sheets in that state under **J96**. The frustum test then found **0 of 2** landmark models inside the frame. Every one of those is recorded; none of them stops the sheet.

**The reference, meanwhile, is exactly the right photograph.** The Hell Gate's steel through-arch spans the river dead centre, its two masonry towers at the abutments, the Triborough's viaduct crossing behind it on the left, Astoria Park's shoreline in the foreground. If the frame had been aimed at the arch, this sheet would have been one of the more informative in the set.

**The camera is standing on the river.** Ground under the lens reads **0.0 m** over sixteen samples whose range is 0.0 to 0.0 — the flattened water surface, as on `landmark_domino_park` and `landmark_ellis_island`. The item's viewpoint is the Astoria Park shore path, which is a built embankment the 2013 bare-earth terrain does not carry.

**What can still be compared is tone, and it is dominated by the photograph's own development.** Mean **0.776×**, median **0.821×**, chroma **0.678×**, and the two development offsets are **0.621 stops** apart. Contrast is **0.473×** — the render's frame is pale concrete and flat water, where the reference has a blue May sky with cumulus, dark green shoreline and the arch's rust-brown steel.

## What matches

* **The Hell Gate Bridge is modelled** at 23,788 triangles and placed 495.3 m from the camera — it exists, it is simply outside the frame.
* **The Triborough's approach is modelled well**: 80,446 triangles of pier and truss, and what fills the frame is believable bridge fabric.
* **The camera correctly refused the photograph's own GPS**, because a ray straight up from it hits the Triborough's roof, and used the recorded viewpoint 134 m away instead.
* **The recorded azimuth agrees with the bearing to the subject to 0.1°.**
* **The development is metered and unclamped**, +0.80 stops from a median linear luminance of 0.103636.
* **The record names every failure**: the 74.2 m coordinate offset, the untested sightline, the 0-of-2 frustum result, the missing kit file and the six tiles without park ground.
* **The pavement is complete**: 14,997 polygons, **0 dropped**.
* **The clearance is genuinely clear**: nothing built within 60 m and no agent either.

## What does not match

* **The subject is outside the frame** while its own model sits 495.3 m away (J96, then the frustum).
* **The item's subject coordinate is 74.2 m off the fabric it names**, and the nearest fabric belongs to a different bridge.
* **No height, no extent, no sightline verdict.**
* **The camera stands on the river at 0.0 m** instead of on the Astoria Park shore path.
* **There is no kit at all.** The record says *kit not placed: no `kit_placements.bin` in range* — ten building tiles are imported and not one carries a facade-kit file, so the Astoria shoreline is bare shells.
* **No park ground at all** — 0 meshes — with **6 tiles** named as unbuilt inside the 900 m ground radius, so Astoria Park renders as bare terrain.
* **Contrast is 0.473 of the photograph's** and chroma **0.678×**: no sky colour, no cumulus, no rust-brown steel and no deep green shoreline.
* **Not one of 2,140 trees is drawn from modelled branches**, though **169** of the cards are procedural canopy stems.
* **Thirty-five people and 57 vehicles**, with **69 pedestrians dropped for standing where the planimetric data has no sidewalk** — the shore path again.
* **The water is a flat mirror** on the Hell Gate tidal strait, which is the most turbulent water in the city.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is outside the frame while its model stands 495 m away | the stored subject coordinate has no fabric within 6 m and the nearest is 74.2 m off on another bridge, so no height was measured and the frame was never widened or aimed; the frustum then reported 0 of 2 models in the cone and nothing acted on it (J96) | **data + verification — open, J96** |
| the camera stands on water at 0.0 m | the Astoria Park shore path is a built embankment the 2013 bare-earth heightmap does not carry (J85's family, as on Domino Park and Ellis Island) | **geometry — open, measured** |
| no kit at all on 10 building tiles | no `kit_placements.bin` exists for any tile in range; the record says so | **data — open, ten tiles without a kit file** |
| no park ground, 6 tiles unbuilt | park ground was not built for those tiles; the record names all six | **data — open, six tiles unbuilt** |
| sd 0.473×, chroma 0.678×, p50 0.821× | no sky colour, no cumulus, no painted steel, and 0.621 stops of development between the halves (J83) | reference + declared scope |
| 0 of 2,140 trees from modelled branches | the props budget spends its triangles on cards at this density | performance |
| 35 people, 69 dropped off the walkable surface | the shore path is not a walkable surface in the planimetric data | **data — open, measured** |
| the water is a flat mirror | water is a flattened surface at a single elevation with no wave or current model — and this is the Hell Gate | **declared scope** |
