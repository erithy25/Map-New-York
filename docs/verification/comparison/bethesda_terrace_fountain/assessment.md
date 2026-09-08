# Bethesda Terrace and Fountain

`bethesda_terrace_fountain` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bethesda Fountain and the Lake, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 08:04:45, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Bethesda_Fountain_and_the_Lake,_Central_Park,_Manhattan,_New_York.jpg)

**Camera** — 40.77350, -73.97110 (NYC_TM -1778, 8174) at z 24.2 m NAVD88 | azimuth 13.9°, pitch −1.9° | 28 mm on 36 mm (65.5° horizontal) | 1280x854. The camera stands on **the item's recorded viewpoint**, which puts the eye on the **roof of `lm_b_bethesda_terrace.26`** — the viewpoint is a single lat/lon for a two-level structure — and it was then walked **12 m along the view azimuth to the parapet**, the last point the roof still supports. From there the view is clear for 81 m and the nearest built thing in frame is `prop_lamp_park_twin_6` 3.3 m away, with no simulated agent within 60 m.

**Sun** — azimuth 92.9°, elevation 20.3° at 2026-04-18T08:04:45−04:00, from the photograph's own **EXIF DateTimeOriginal**; 657.2 W/m² direct normal, sky at strength 0.0404, Filmic, **+1.10 stops**. This is the one thing on the sheet that is exactly the photograph's, and the reference's own view direction is recorded at **high** confidence.

**In the scene**, within 742.7 m of the camera — 4/4 building tiles (231,192 tris), 8 landmark models of which **6 can fall inside the 65.5° frame**, 14,791 pavement polygons (5,686 white marking, 5,224 sidewalk, 1,957 roadbed, 1,334 curb, 230 crosswalk, 164 yellow marking, 141 median, 29 parking lot, 26 plaza), 224 props of the 258 in range, 100 kit pieces, 0 vehicles and 11 people; 1,634,662 triangles. Ground mesh 86,028 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the sheet does not show its subject, and it says so in its own record

**`sightline.subject_visible` is `false`.** Of the five rays cast at Bethesda Fountain, **one** lands on it; the line of sight is closed at **14.7 m** by `lm_b_bethesda_terrace.20` — a piece of the terrace the camera is standing on. The frame shows a concrete deck, a roadway with a yellow centre line, a long wall and a distant skyline. The photograph shows the Angel of the Waters, the fountain basin, the Lake and the Ramble. **These are not two views of one place; they are two places.** Nothing below should be read as a comparison of Bethesda Terrace, because no part of Bethesda Terrace as a viewer would recognise it is in this frame.

This is a **camera-placement failure, not a content failure**, and the cause is recorded rather than inferred. The item's recorded viewpoint is a single lat/lon for a two-level structure; the eye landed on the terrace's upper roof, **93.4 m** from the fountain, and the walk to the parapet brought it to **81.4 m** without clearing the line. The photograph's own EXIF GPS is 42.7 m from that point and **51.4 m from the fountain** — very close to where this picture was actually taken — and the render **rejected** it, for a stated and, in isolation, correct reason: at that position the eye point is under `verify_pavement`, with 1.8 m of ground or paving directly overhead. That is the terrace's *lower arcade*. The photographer was standing on the *upper* deck above it, and the rule that decides an eye height has no way to say "the deck, not the vault under it". So the render discarded the right position because it could only see the wrong storey of it, and fell back to a viewpoint on the roof (docs/DEVIATIONS.md J65, still open).

## What matches

**Nothing in the picture does.** The render and the photograph have no object, no surface and no framing in common, for the reason the verdict gives. What follows is what the *record* confirms about the world the frame was drawn from — which is worth stating, and is not the same claim.

* **Every city surface resolves its own material.** 20 photographic surfaces are dressed from the shared CC0 catalogue, and one, `glass_curtain`, stays analytic by design. This is a sheet rendered with J63 closed.
* **The crowd is drawn from the whole cast.** `npc_archetypes_available` is **36** and no fold is recorded: no person in this frame stands in for another. Before J62 the renderer drew from twelve bodies.
* **The frame is honest about its own emptiness.** 0 vehicles, and the record says why: **46 were dropped for being on a car-free park drive**, 5 for not being on a carriageway, 44 for being outside the radius. Central Park's drives have been closed to cars since 2018 and the simulation places none on them. That is a correct result, arrived at by a rule that was checked.
* **The trees stand at the height their own rows record.** All 76 are scaled to it, at a mean of **0.946**, and none fell outside the declared band (J70).
* **The day is a Saturday** — 2026-04-18, spelled out in the record rather than left as the day-type code a reader would transcribe as Monday.
* **Six of the eight landmark models can fall inside the frame**, including Bethesda Terrace itself at 81.3 m and 0.1° off axis. The count on the caption is a scene count and the record distinguishes the two (J61).
* Nothing was dropped for being missing: 4 of 4 tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground, and no prop capped for the triangle budget.

## What does not match, beyond the viewpoint

* **The frame is too bright and much too pale.** Mean luminance **0.5359** against the photograph's **0.3910** — **1.371×**. Mean chroma **0.0604** against **0.1435**, a ratio of **0.421**. The tonal spread is the part most clearly wrong: standard deviation **0.1195** against **0.2089**, and the render's 5th percentile is **0.3269** where the photograph's is **0.0933** — there is nothing dark in this frame, and a picture with the Ramble in it has deep shadow all through it. The exposure is part of it: **+1.10 stops** are opened for a 20.3° Sun, over a frame filled by a pale concrete deck with no canopy over it.
* **There is no water and no canopy where the picture has both.** The scene knows about the Lake — the terrain record names `THE LAKE`, `Turtle Pond`, `The Pond` and `BOAT BASIN` among its water bodies — and the camera is aimed over the parapet rather than at them.
* **76 trees are in the frame's props and all 76 are species-substituted**; the photograph's whole background is the Ramble in April leaf. Central Park's canopy is the thing this view is mostly made of and the render has nothing of it.
* **The subject is a fountain and the fountain is not modelled as one.** The landmark model `b_bethesda_terrace` carries the terrace; the record names its own ground (5,049.8 m²) but the sheet shows no basin, no angel, no water jet.
* **A road with a yellow centre line runs across the middle of the frame.** 1,957 roadbed and 164 yellow marking polygons are in range over 742.7 m, which is correct for a scene that reaches the park drives and Fifth Avenue — but a drive crossing the view at this distance is a statement about where the camera is pointing, not about Central Park.
* **34 props in range were not placed and 3 opaque impostor cards were dropped**, and the reason is not the triangle budget: **34 point props have no asset at all** — 11 artworks, 9 drinking fountains, 6 parks buildings, 5 memorials and 3 comfort stations. Two of those categories matter here specifically — the Angel of the Waters is an *artwork* and this sheet is a picture of it.
* **Three surfaces sit at the albedo cap with the wrong source material behind them** — `concrete`, `roof_membrane` and `wood_clapboard` (J66) — and the frame is mostly concrete.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is not in the frame | the recorded viewpoint is one lat/lon for a two-level structure; the eye landed on the terrace roof, and the photograph's own GPS was rejected because at that point the upper deck is 1.8 m overhead | **verification — open, DEVIATIONS J65** |
| line of sight closed at 14.7 m | by `lm_b_bethesda_terrace.20`, the structure the camera stands on | verification |
| frame mean 1.371× the photograph | +1.10 stops opened for a 20.3° sun, over a frame filled by a pale concrete deck | verification |
| chroma 0.421× and a 5th percentile of 0.3269 against 0.0933 | no foliage, no water and no brick paving in the frame; what is in it is concrete and asphalt, three surfaces of which are at the albedo cap with the wrong material (J66) | verification + material |
| no fountain, no angel, no water jet | the landmark model carries the terrace and its ground; the fountain itself is not modelled, and `artwork` has no prop asset (J23) | geometry |
| all 76 trees species-substituted | the park-tree ingest places OSM trees by taxon where it can and falls back to the census population; none of these 76 matched a modelled species exactly | data |
| 0 vehicles | 46 dropped as being on a car-free park drive — correct, and the record says so | — (not a gap) |
| 34 point props unplaced | artworks, memorials, drinking fountains, comfort stations and parks buildings have no asset; they stay unplaced rather than become the wrong object (J22, J23) | geometry |
