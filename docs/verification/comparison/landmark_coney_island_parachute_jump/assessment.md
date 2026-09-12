# Coney Island Parachute Jump

`landmark_coney_island_parachute_jump` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Parachute Jump - Coney Island, Brooklyn, New York City, New York, USA - October 3, 2023.jpg by Giorgio Galeotti, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-03 13:13:54, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:Parachute_Jump_-_Coney_Island,_Brooklyn,_New_York_City,_New_York,_USA_-_October_3,_2023.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.57283, -73.98216 (NYC_TM -2723, -14121) at z 5.2 m NAVD88 | azimuth 295.5°, pitch +0.0° | 35 mm on 36 mm (37.8° horizontal, 54.4° vertical, portrait) | 852x1278. Position and heading both come from the photograph: its own EXIF camera GPS, **31.3 m** from the item's recorded viewpoint, and 295.5° is the bearing from there to the subject, 5.7° from the item's own azimuth. **The lens stayed at 35 mm and the axis stayed level, and the record says why**: nothing built stands within 6 m of the subject's coordinate, so its mid-height is not known and there is nothing to tilt towards. The camera was not moved — the eye point stands on `lm_b_coney_island.51`, the boardwalk deck, and this position is the photograph's own fix so there is no viewpoint to walk to. The azimuth is clear for **89.6 m** against the 80.0 m needed, and **the nearest built thing in the frame is that deck at 0.0 m** — the lens is level with its surface. Ground under the camera reads **3.617 m** NAVD88 from 16 heightmap samples within 5.0 m, range 3.32 to 3.88 m.

**Sun** — azimuth 190.2°, elevation 44.9° at 2023-10-03T13:13:54−04:00, from the photograph's own **EXIF DateTimeOriginal**; 866.7 W/m² direct normal, sky at strength 0.0325, Filmic, **+1.33 stops and not clamped**. The linear frame's median is **0.071644** against a middle-grey target of 0.18, and its fifth percentile is **0.0** (J83).

**In the scene** — 920,332 triangles: 4 building tiles (56,382 tris, none missing, none LOD-substituted), 1 landmark model and **0 of it inside the 37.8° frame**, 5,553 pavement polygons with **0 dropped**, 723 props, 625 kit pieces, **0 park-ground meshes**, 4 structures tiles with **none missing** (29,956 tris), 37 vehicles and 28 people, terrain 88,150 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the tower is out of the top of the frame, the bottom third is black, and both follow from the same missing measurement

**The subject coordinate is empty.** 43 rays cast, **0** on built fabric: *nothing built stands within 6 m of the subject's coordinate; the nearest built thing is `t_-3_-15_concrete`, 15 m away at bearing 270 deg*. One of the 13 records in that state (**J96**), and the consequence is mechanical: with no measured height the lens was not widened and the axis was not tilted, so a 76-metre tower 172.7 m away is framed by a level 35 mm axis and lands above the top edge. All that appears of it is **a handful of orange-red struts in the upper left corner**.

**And the camera is level with the deck it stands on.** `lm_b_coney_island.51` is at **0.0 m** from the lens. The deck's surface runs across the middle of the frame as a flat pale band, and below its edge there is nothing but the unlit underside: the bottom third of the render is black, measured at **0.3332** of the frame below a luminance of 0.004 — the second-worst near-black fraction in the pass, behind the One Wall Street sheet's (**J92**). The record's own `linear_p05` of **0.0** says the same thing from the development side, and the published fifth percentile is **0.0** against the photograph's **0.4248**.

**The standard deviation ratio of 2.524 is the largest in the pass**, and it is not range: it is a black third against a clear-sky photograph whose whole frame sits between 0.42 and 0.72.

**What the render does contain is the Aquarium and the boardwalk blocks**, in brick with a curved drum and a row of trees — the right neighbourhood at the right scale, in the upper band of the frame. The photograph contains the tower, the moon, and the painted fronts of the Luna Park rides along the bottom.

## What matches

* **The development is metered and unclamped**, +1.33 stops from a median linear luminance of 0.071644.
* **The camera stands where the photographer stood**, 31.3 m from the item's viewpoint, on a bearing 5.7° from its recorded azimuth.
* **The record refuses to invent a height** — 0 of 43 rays, the 14.8 m offset named, no lens change and no sightline claimed (J74, J96).
* **The record states the 0.0 m obstruction** rather than reporting the frame as clear.
* **Every structures tile in range has a file** — 4 of 4, **29,956 triangles**, and the boardwalk deck is among them.
* **Neither kit nor props were capped**: 625 kit pieces of 625 in range — everything placed — and 723 props of 746.
* **The Aquarium's drum and the boardwalk blocks read correctly** in brick at the right height.
* **The pavement is complete**: 5,553 polygons, **0 dropped**.

## What does not match

* **The tower is out of frame**, save for a few struts in the corner, because no subject height was measured (J96).
* **The bottom third of the frame is black** — 0.3332 of pixels below a luminance of 0.004 — the unlit underside of the deck the lens is level with (J92).
* **Contrast is 2.524× the photograph's**, the largest ratio in the pass, and it is a black third rather than range.
* **The fifth percentile is 0.0 against 0.4248**, and the mean **0.667×**.
* **Chroma is 0.308 of the photograph's**, 0.0981 against 0.318 — the reference is a rust-red tower against deep blue with painted ride fronts below; the render has brick, sand and a pale sky.
* **No park ground at all** — 0 meshes — and the record names **4 tiles** inside the 708 m ground radius for which it was not built.
* **Only 6 of 498 trees are drawn from modelled branches**; **307** species were substituted, **1** instance scaled out of band, and the mean scale of **0.802** is the smallest in this queue, so the canopy is systematically undersized.
* **Twenty-three props across seven kinds were wanted in range and have no asset**: 8 parks building, 5 drinking fountain, 4 vending machine, 2 misc structure, 2 parks comfort station, 1 billboard, 1 memorial.
* **Twenty-eight people and 37 vehicles**, with **54 pedestrians dropped for standing where the planimetric data has no sidewalk** — which on the boardwalk is the boardwalk.
* **No landmark model falls inside the frame** — 1 placed, **0 in the cone**.
* **The moon is in the photograph and no sky in this build carries one.**

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower is above the frame | the stored subject coordinate has no fabric within the probe's 6 m reach, so no height was measured, so the lens was never widened and the axis never tilted (J96) | **data + verification — open, J96** |
| the bottom third is black | the lens is level with the boardwalk deck it stands on, 0.0 m away, and the deck's unlit underside fills the lower frame; nothing in the record measures the frame's content (J92) | **verification — open, J92** |
| sd 2.524×, p05 0.0 against 0.4248, mean 0.667× | the black third, against a photograph whose entire frame lies between 0.42 and 0.72 | consequence of the row above |
| chroma 0.308× | no rust-red steel, no deep blue sky and no painted ride fronts in the render's frame | consequence of the first row |
| no park ground, 4 tiles unbuilt | park ground was not built for those tiles; the record names all four | **data — open, four tiles unbuilt** |
| 6 of 498 trees from modelled branches, mean scale 0.802 | the props budget spends its triangles on cards at this density, and the size classes the cards are exported at undersize the surveyed heights here (J70's family) | performance + **data** |
| 23 props across seven kinds unmapped | no asset exists for those kinds | data |
| 28 people, 54 dropped off the walkable surface | the boardwalk is not a walkable surface in the planimetric data | **data — open, measured** |
| no moon | nothing in this build reads a historical sky, let alone an ephemeris | reference — no source exists |

## Measured for this assessment

Two figures above are not in the render record, because the record measures the path to the subject
and never the frame's content — the gap recorded as J92. I measured the frame itself. Read with
`docs/verification/comparison/landmark_coney_island_parachute_jump/render.png` (852x1278), luminance
as 0.2126 R + 0.7152 G + 0.0722 B on the 8-bit sRGB values.

| figure | where it comes from |
|---|---|
| 0.004 | the luminance threshold below which a pixel counts as black, the same one used in the J92 survey |
| 0.3332 | fraction of this render's pixels below that threshold, second highest of the 5 frames in the pass above 5 % |
