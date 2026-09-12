# Kosciuszko Bridge

`landmark_kosciuszko_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Under the K Bridge Park 017.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-07-01 14:21:51, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Under_the_K_Bridge_Park_017.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.72567, -73.93322 (NYC_TM 1427, 2823) at z 11.1 m NAVD88 | azimuth 57.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **300.9 m** from the item's recorded viewpoint — **past the 250 m sanity radius, and kept anyway for a stated reason**: *this item is a view of Kosciuszko Bridge and the photograph stands 415 m from it against the recorded viewpoint's 500 m, on the same side to 37.0 deg, so the measurement is kept and the estimate is not*. The recorded viewpoint was **boxed in** — the azimuth closed **6 m** ahead against the 80.0 m needed — so the camera was **moved 27.3 m** onto the nearest surveyed roadbed, scored on the subject's sightline. From there the azimuth is clear for **92.5 m**, nothing built stands within 20 m of the lens, and no agent either. Ground under the camera reads **9.456 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 9.24 to 10.01 m.

**Sun** — azimuth 230.6°, elevation 65.3° at 2022-07-01T14:21:51−04:00, from the photograph's own **EXIF DateTimeOriginal**; 930.3 W/m² direct normal, sky at strength 0.0307, Filmic, **+0.62 stops and not clamped**. The linear frame's median is **0.117135** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,031,162 triangles: 12 building tiles (279,056 tris, none missing), 1 landmark model, in the frame, 19,911 pavement polygons with **0 dropped**, 1,188 props, 4,612 kit pieces, **0 park-ground meshes**, 68 vehicles and 369 people, terrain 243² at 2.0 m near / 40.0 m far.

## Verdict — the cable-stayed tower and its stay fan are modelled and read from four hundred metres, and the ground in front of them is a blank plain with two black tears in it

**The bridge is right.** The render carries the pylon with its fan of stay cables, the deck it holds, the elevated approach viaduct crossing the right of the frame on its piers, and the retaining wall below — the same elements the photograph shows from under the old viaduct. For a 2017 cable-stayed bridge built from planimetric data at 423 m, this reads correctly.

**The reference pairing is handled with unusual care, and the record explains it.** The photograph's own GPS lies 300.9 m from the item's recorded viewpoint, past the 250 m radius that normally rejects it. The record keeps it and says why: the *subject* is 415 m from the photograph against 500 m from the recorded viewpoint, on the same side of the bridge to within 37°, so the photograph is a better measurement of this view than the item's own estimate. That is the 250 m rule reasoning about the subject rather than about the viewpoint, and it is the right call.

**The foreground is empty, and torn.** The bottom two fifths of the render is a single pale ground surface with no markings, no kerb, no joint and no texture — and **two black crescent-shaped gaps** open in it, one at the centre-left and one under the viaduct. Nothing in the record names them: the clearance walk reports the azimuth clear for 92.5 m and nothing built within 20 m, and no measurement covers what fills the frame (**J92**). There are **0 park-ground meshes** in the whole scene and the record names **7 tiles** inside the 900 m ground radius for which park ground was not built, so this is bare terrain and pavement meeting each other with nothing between.

**The subject is behind its own retaining wall.** 13 rays, **3 clear, 2 on the subject**, blocked at **28.6 m** by `t_1_2_concrete` — visible fraction **0.154**. The probe measured **78.07 m** above a ground of 0.0 m over **36 of 43** rays, against a catalogue entry 36.2 m away carrying **122.53 m**: the mast tops out at 122.5 m and the object the rays struck is the deck and pylon base, so this sheet sits in the J94 survey.

**The colour gap is the July sky.** Chroma **0.0567** against **0.1274** (**0.445×**) and contrast **0.607×**: the reference is half cumulus over blue with a graffiti-painted retaining wall and dense green scrub, and the render has concrete, pale ground and a Nishita dome at strength 0.0307.

## What matches

* **The pylon, its stay fan, the deck and the approach viaduct** all read at 423 m.
* **The 250 m rule reasoned about the subject** and kept a measurement it would otherwise have rejected, with the distances stated.
* **The development is metered and unclamped**, +0.62 stops from a median linear luminance of 0.117135.
* **The clearance walk worked as designed**: a 6 m closure detected, 27.3 m onto real surveyed roadbed, scored on the subject's sightline (J79).
* **The kit is nearly complete**: 4,612 pieces of 4,730 in range, nothing capped.
* **Every building tile has a shell** — 12 of 12, 279,056 triangles.
* **The pavement is complete**: 19,911 polygons, **0 dropped**, including 5,704 roadbed, 5,547 white markings, 3,859 sidewalk, 2,313 parking lot and 1,495 curb.
* **The crowd reads as a park**: 369 people drawn, standing in groups along the wall.

## What does not match

* **Two black crescent gaps open in the ground surface**, and nothing in the record names or measures them (J92).
* **The foreground is featureless** — no markings, kerb, joint or texture over two fifths of the frame.
* **No park ground at all** — 0 meshes — with **7 tiles** named as unbuilt, so Under the K Bridge Park is bare terrain.
* **Visible fraction 0.154**, eleven of thirteen rays stopped by the bridge's own retaining wall 28.6 m out.
* **The probe's 78.07 m against a 122.53 m catalogue entry** 36.2 m away (J94).
* **Chroma is 0.445 of the photograph's** and contrast **0.607×**: no cumulus, no graffiti, no green scrub.
* **Only 1 of 316 trees is drawn from modelled branches**; **2,552 tree rows** did not fit the props budget of 1,376,403, and 48 of the 315 cards are procedural canopy stems.
* **Props were capped**: 1,188 placed, with 176 vehicles and 13 people further dropped at the agent budget, and 1 impostor card dropped.
* **Sixteen vehicles were placed where the planimetric data has no roadway** and dropped rather than drawn; **199 pedestrians in the roadway while not crossing** and **71 with no sidewalk under them** went the same way.
* **No cloud.** The reference's cumulus is half the picture.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| two black gaps in the ground | terrain and pavement meet with no park-ground surface between them on tiles where park ground was not built, and nothing in the record measures the frame's content (J92) | **geometry — open, and unmeasured** |
| a featureless foreground | the near field here is the park's own ground, which was not built, so what remains is bare terrain under a pavement edge | **data — open, seven tiles unbuilt** |
| visible fraction 0.154 | the bridge's own retaining wall stands 28.6 m from the lens across the fan; the walk scored this as the best reachable point (J79) | verification — open |
| probe 78.07 m against a 122.53 m catalogue entry | the probe takes the object standing at the coordinate, here the deck and pylon base rather than the mast (J94) | verification — open, J94 |
| chroma 0.445×, sd 0.607× | no cumulus, no graffiti and no scrub in the render's frame | reference + declared scope |
| 1 of 316 trees from modelled branches, 2,552 rows dropped | the props triangle budget at 1,376,403 | **performance** |
| 16 vehicles, 199 pedestrians in the roadway and 71 off the sidewalk, all dropped for having no surface under them | the park's paths and the bridge approach are not walkable or drivable surface in the planimetric data | **data — open, measured** |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
