# Deno's Wonder Wheel

`landmark_coney_island_wonder_wheel` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Wonder Wheel Coney Island 015.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-08-12 13:36:25, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Wonder_Wheel_Coney_Island_015.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.57342, -73.97906 (NYC_TM -2468, -14052) at z 4.4 m NAVD88 | azimuth 25.3°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **80.3 m** from the item's recorded viewpoint, and 25.3° is the bearing from there to the subject; the item's recorded azimuth of 9.9° is 15.4° away. **The lens stayed at 35 mm and the axis stayed level**, because nothing built stands within 6 m of the subject's coordinate so its mid-height is not known. The recorded viewpoint was **boxed in** — the azimuth closed **7 m** ahead against the 35.5 m needed — so the camera was **moved 8.0 m to the left**, and because there was no subject height to score against, the walk fell back to a *radial search with a clear frame* with `scored_on_subject_sightline` **false**. From there the azimuth is clear for **60 m** and the nearest built thing is `t_-3_-15_red_brick` **8.7 m** away. Ground under the camera reads **2.814 m** NAVD88 from 16 heightmap samples within 5.0 m, range 2.57 to 3.15 m.

**Sun** — azimuth 199.2°, elevation 63.1° at 2022-08-12T13:36:25−04:00, from the photograph's own **EXIF DateTimeOriginal**; 925.8 W/m² direct normal, sky at strength 0.0308, Filmic, **+0.45 stops and not clamped**. The linear frame's median is **0.131889** against a middle-grey target of 0.18 (J83); the physical rule would have given 0.0.

**In the scene** — 1,067,535 triangles: 6 building tiles (102,188 tris, none missing, none LOD-substituted), 1 landmark model, in the frame, 4,557 pavement polygons with **0 dropped**, 698 props, 817 kit pieces, **0 park-ground meshes**, 6 structures tiles with **none missing** (51,412 tris), 36 vehicles and 28 people, terrain 83,216 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the wheel is modelled properly, rim, spokes, hub and coloured cars, and it is cut off at the top of the frame and painted the wrong colour, and the plaza under it is empty

**The Wonder Wheel is one of the better objects in this build.** The rim, the radial spokes, the hub and the swinging cars are all there, and the cars carry the right primary reds, blues and yellows. Structurally it is right.

**Two things go wrong, and the first causes the second.** The stored subject coordinate has **no built fabric within the probe's 6 m reach** — the nearest built thing is `t_-3_-14_tan_brick`, **48.3 m** away, the largest offset among the Coney Island items — so 0 of 43 rays landed, no height was measured, the axis stayed level, and the wheel is cut across by the top edge of the frame instead of standing in it. Because there was also no subject height to score the walk against, the clearance search fell back to a radial one with no sightline test at all (**J96**). The reference has the whole wheel centred, base to crown.

**The wheel is the wrong colour.** Deno's Wonder Wheel is painted coral pink and pale green; the render's rim, spokes and hub are white-grey, with colour only on the cars. That is the per-object colour gap (J66's remainder) showing on the object where it costs most: chroma **0.0591** against the photograph's **0.3951**, a ratio of **0.15** — the widest colour gap on any sheet in this pass.

**And the amusement park has no amusements.** The bottom three fifths of the render is a single pale plaza with one hard shadow across it. There are kiosks with lit fascia panels along the middle distance — the storefront kit is the largest category here at 299 pieces, and it is doing real work — but no rides, no stalls, no fencing, no queue rails, and **26 props across seven kinds were wanted and have no asset**, 7 of them parks buildings and 5 of them vending machines. At Coney Island those kinds are the park.

## What matches

* **The wheel's structure is right**: rim, spokes, hub and swinging cars, with the cars in the right primary colours.
* **The development is metered and unclamped**, +0.45 stops from a median linear luminance of 0.131889.
* **The mean is within 5 per cent** — 1.051× — and the two development offsets are **0.437 stops** apart (J83).
* **The record refuses to invent a height** and names the 48.3 m offset, and it also records that the walk was **not** scored on the subject's sightline rather than implying it was (J74, J96).
* **Every structures tile in range has a file** — 6 of 6, **51,412 triangles**.
* **The storefront kit carries the boardwalk fronts**: 299 storefront pieces of 817 in range, with 141 suppressed under the landmark shell and nothing capped.
* **Props were not capped**: 698 placed of 756 in range, **0** impostor cards dropped.
* **The pavement is complete**: 4,557 polygons, **0 dropped**.

## What does not match

* **The wheel is cut off at the top of the frame**, because no subject height was measured and the axis stayed level (J96).
* **The wheel is white-grey where it is painted coral and green.** Chroma **0.15** of the photograph's, the widest colour gap in the pass.
* **The plaza is empty** — no rides, no stalls, no fencing, no queue rails — and the bottom three fifths of the frame carries nothing but pale ground and one shadow.
* **Twenty-six props across seven kinds were wanted in range and have no asset**: 7 parks building, 5 billboard, 5 vending machine, 3 drinking fountain, 3 misc structure, 2 parks comfort station, 1 artwork.
* **Contrast is 1.206× the photograph's** and the render's fifth percentile is **0.2178** against **0.308** — the empty plaza with a hard shadow on it holds more range than the photograph, which is almost all wheel and sky.
* **No park ground at all** — 0 meshes — and the record names **6 tiles** inside the 594 m ground radius for which it was not built.
* **Not one of 383 trees is drawn from modelled branches**; **262** species were substituted, **1** instance scaled out of band, and the mean scale of **0.855** undersizes the canopy.
* **Twenty-eight people and 36 vehicles** on a Friday in August, with **57 pedestrians dropped for standing where the planimetric data has no sidewalk** — which here is the amusement area itself.
* **No cloud and a pale sky.** The reference's deep blue with one cumulus is a Nishita dome at strength 0.0308.
* **The frustum reports the Coney Island composite at 94.3 m, 19.4° off axis**, which is the composite centroid rather than the wheel.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the wheel is cut off at the top | the stored subject coordinate has no fabric within the probe's 6 m reach — the nearest is 48.3 m away — so no height, no tilt and no widened lens (J96) | **data + verification — open, J96** |
| the wheel is the wrong colour | there is no per-object or per-building colour source; a landmark shell keeps the builder's material colour (J66 remainder) | **data — open, and this is where it costs most** |
| an empty plaza | rides, stalls, fencing and queue rails are not classes this build models, and the props that would stand in for them have no asset | geometry — declared scope + **data** |
| chroma 0.15×, sd 1.206×, p05 0.2178 against 0.308 | no paint on the wheel, no sky colour, and an empty plaza with a hard shadow where the photograph has wheel and sky | consequence of the rows above |
| 26 props across seven kinds unmapped | no asset exists for those kinds, and at Coney Island those kinds are the park | **data — open** |
| no park ground, 6 tiles unbuilt | park ground was not built for those tiles; the record names all six | **data — open, six tiles unbuilt** |
| 0 of 383 trees from modelled branches, mean scale 0.855 | the props budget spends its triangles on cards at this density, and the exported size classes undersize the surveyed heights | performance + **data** |
| 28 people, 57 dropped off the walkable surface | the amusement area is not walkable surface in the planimetric data | **data — open, measured** |
| the walk was not scored on the subject's sightline | there was no subject height to score against, so the walk fell back to a radial search; the record says so (J79's rule needs J96's input) | **verification — open, and correctly reported** |
| the composite reported 19.4° off axis | the frustum test uses a landmark composite's centroid | verification — open |
