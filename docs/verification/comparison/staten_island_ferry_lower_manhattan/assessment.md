# Staten Island Ferry deck view of Lower Manhattan

`staten_island_ferry_lower_manhattan` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lower Manhattan from Staten Island Ferry February 2015 002.jpg by King of Hearts, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2015-02-15 13:51, 1920x840. [Commons page](https://commons.wikimedia.org/wiki/File:Lower_Manhattan_from_Staten_Island_Ferry_February_2015_002.jpg) — the view direction is derived from the image at **high** confidence. The whole Lower Manhattan ridge in crisp winter light, and **the harbour is frozen**: a field of broken pack ice fills the lower half of the picture from the bow to the seawall.

**Camera** — 40.691, -74.0215 (NYC_TM -6044, -997) at z **8.0 m above sea level** | azimuth 15.8°, pitch 0.0° | 28 mm on 36 mm (65.5° horizontal) | 1280x560. The eye datum is `sea`, and the record says exactly what it means: *"open bow deck of a Molinari/Barberi-class Staten Island Ferry: upper (promenade) deck about 6.4 m above the waterline, plus 1.6 m eye height; **the boat is not modelled, so the camera floats free at that height over the Upper Bay**"*. The camera stands on the item's recorded viewpoint; the photograph's own EXIF GPS is **699.0 m** away, and the record's reasoning is worth quoting in full: *"past the 250 m at which it could still be the same view, so the camera was not stood on it. That is a statement about this pairing and not about the photograph: a fix this far out is usually correct and simply of somewhere else."* The heading agrees with the item's recorded azimuth to **0.1°**. Nothing built stands within 60 m of the lens and no simulated agent within 60 m.

**Sun** — azimuth 209.3°, elevation **31.9°** at 2015-02-15T13:51:00−05:00, from the photograph's own **EXIF DateTimeOriginal**; 785.9 W/m² direct normal, sky at strength 0.0353, Filmic, **+0.53 stops**. Metered: the linear median is **0.125065**, already two thirds of the 0.18 target, so the development is only **0.525 stops**. The physical rule would have given **0.43**.

**In the scene** — 3,553,329 triangles: **103 building tiles (1,366,976 tris), 17 missing, 16 substituted by a lower LOD**, 30 landmark models of which 16 fall inside the 65.5° cone, 4,662 pavement polygons, 4,007 props, 236 kit pieces, 4 park-ground meshes, **56 tiles of structures (419,072 tris) with 56 more having no file**, 50 vehicles and **7 people**. The water table names **35 separate bodies**, from the Narrows and Newark Bay to Prospect Lake, with **64,657 quads** on the flattened water surface.

## Verdict — two rays hit One World Trade Center's own model and the sheet published a visible fraction of 0.0, because they landed seven metres past a fixed tolerance

**The sightline's own fields contradict its verdict.** `subject_rays_on_subject` is **0** and `subject_visible_fraction` is **0.0**. But `subject_lands_on` is **`lm_b_one_world_trade_center.5`** — the subject's own model — at `subject_lands_at_m` **2,545.5 m**, and two of the thirteen rays are clear. The on-subject test in `blender/verify/camera.py` counts a ray when it lands within `span + reach`, and here `subject_range_m` is **2,513.6 m** and `subject_reach_m` is **25.0 m**, so the threshold is 2,538.6 m. The rays landed **6.9 m** beyond it. **Two rays reached the tallest building in the western hemisphere and were scored as misses by seven metres on a two-and-a-half-kilometre shot.**

**The reach is a fixed 25 m and it should not be.** At this range 25 m is one per cent of the distance, and the subject is 75.0 m wide by its own recorded extent, so its far face stands 75 m beyond its near one. A tolerance that does not scale with either the distance or the subject's own size cannot decide whether a ray landed on it. Measured across the pass, **two records land their nearest ray on the subject's own model and still publish 0.0**: this sheet at 6.9 m past the threshold, and the **Empire State Building** sheet at **3.1 m** past it. So two of the nineteen zeros J100 counts are not sheets that miss their subject at all — they are sheets that hit it and were refused by a metre or two of arithmetic. This is recorded as J109.

**And the record misattributes it in the same breath.** The note reads: *"nothing stands within 25 m of the subject's recorded coordinate on any clear ray: the clear rays run on to `lm_b_one_world_trade_center.5` at 2546 m. The line is open and the subject is not on it, which is a fault in the item's coordinate or in the model, not in the camera."* It names the subject's own model as the thing the clear rays hit, and then concludes that the subject is not on the line. The same sentence appears on the Chrysler sheet with the same false conclusion.

**Under that, the height is the promenade sheet's fault repeated.** 43 rays, 41 on fabric, **292.65 m** on the same 75.0 m square facet of the tower's taper, against the catalogue's **541.3 m** — the same under-measurement by nearly a quarter of a kilometre, which is what then aimed the fan low enough for eleven of the thirteen rays to run into the Financial District and stop at **1,636.4 m** on `t_-6_0_limestone_LOD1`, a joined tile mesh drawn at its first LOD (J94, J106).

**The harbour was frozen and the render's is a mirror.** 15 February 2015 fell in the coldest February New York has recorded, and the reference photograph's lower half is pack ice from edge to edge. This build draws open water as a flat specular plane with no wave state, no turbidity and no ice (J103), so the Upper Bay reflects the skyline cleanly. That is the single largest visual difference between the two halves and it accounts for most of the measured gap: chroma **0.427**, mean **0.711×**, p50 **0.749×**.

**The boat is not modelled, and the record says so before anything else does.** A camera floating 8.0 m over open water with no bow, no rail and no deck is a declared simplification with its own reasoning in the eye-source field. It is the right way to publish that decision.

## What matches

* **The skyline is recognisable.** 103 building tiles at 1,366,976 triangles and 30 landmark models, with One World Trade Center at the centre and the Financial District's towers stepping down to the Battery.
* **The heading agrees with the item's own recorded azimuth to 0.1°.**
* **The reference chooser refused a 699 m fix and argued the refusal.** The wording separates the pairing from the photograph — *"a fix this far out is usually correct and simply of somewhere else"* — which is the fairest treatment of reference evidence in any record read this round.
* **The eye datum is `sea` and the unmodelled boat is declared** with the deck height it stands for.
* **Nothing was capped.** Props 4,007 of 4,011 in range with **0 dropped for budget**; kit 236 of 236. The only sheet read this round with neither budget biting.
* **The scene arrived bright and needed almost nothing**: 0.525 stops on a linear median of 0.125065.
* **Structures are here in force**: 56 tiles imported for **419,072 triangles**, the largest structures contribution in the pass.
* **The water is comprehensive as a surface**: 35 named bodies and 64,657 quads on the flattened surface.
* **The park ground is correct where it can be seen**: 153 samples within 150 m, `under_frac` **0.0**, median clearance +0.20 m; 0.0979 across all 2,543 samples.
* **The date and the day type agree**: the real minute from EXIF, and **15 February 2015 was a Sunday**, which is the density profile the simulation used.
* **The trees are bare.** 15 February is inside the leaf-off window and all 3,971 are bare-canopy (J97).
* **Seven people in the frame is the right answer.** The camera is over open water 150 m from the nearest land; a crowd here would be wrong.

## What does not match

* **The published fraction is 0.0 while two rays landed on the subject's own model**, 6.9 m past a fixed 25 m tolerance (J109).
* **The record concludes that the subject is not on the line** in the same sentence that names the subject as what the clear rays hit.
* **The height is 292.65 m for a 541.3 m tower**, and the fan aimed from that figure put eleven rays into the Financial District (J94, J106).
* **Eleven rays stop 1,636 m away on a joined limestone tile mesh at LOD1** (J94).
* **The harbour is not frozen.** The reference's lower half is pack ice; the render's is a specular mirror. Open water in this build has no wave state, no turbidity and no ice (J103).
* **The render carries under half the photograph's colour**: chroma **0.427**. A February harbour of white ice and blue water against a hazy procedural gradient.
* **Almost a stop of the brightness difference is exposure.** The photograph sits **1.151 stops above** the grey convention — bright ice under winter sun — and the render 0.235 above it, a **−0.916-stop** gap, so mean reads 0.711× and p50 0.749× (J83).
* **Seventeen building tiles were not built at all** and **sixteen more were drawn at a lower LOD than their distance asks**, on a sheet whose subject is a skyline two and a half kilometres away.
* **Fifty-six structures tiles have no file** beside the fifty-six that do.
* **Only 47 of the 3,971 trees are drawn from modelled branches**; 3,924 are six-triangle cards out to 1,500 m, and **2,332 of them are a substituted species** (J108).
* **One tile in the 900 m ground radius has no park ground built at all** (J102).
* **No ferry, no wake, no other traffic on the water.** The photograph's harbour carries the ice and the render's carries nothing at all.
* **No taxis in the fleet.** 37 sedans, 10 SUVs, 2 vans and a sanitation truck, 150 m from the Battery — though at this distance none of them is legible.
* **Every pedestrian and most vehicles are at the coarsest LOD**: 40 of 50 vehicles and all 7 people at LOD2.
* **No cloud.** The reference's sky is a clear hard winter blue; the render's is a hazy Nishita gradient at strength 0.0353 that pales toward the horizon in a way the photograph does not.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the on-subject threshold is 2,538.6 m and the rays landed 6.9 m past it | the recorded `subject_range_m` of 2,513.6 m plus the recorded `subject_reach_m` of 25.0 m, against the recorded `subject_lands_at_m` of 2,545.5 m; the test is `dist <= span + reach_m` in `subject_sightline` in `blender/verify/camera.py` |
| two records in the pass land their nearest ray on the subject's own model and still publish 0.0 | counted over every record carrying a sightline: this sheet at 6.9 m past the threshold and `landmark_empire_state_building` at 3.1 m past it, both with `subject_rays_on_subject` 0 and `subject_lands_on` naming their own landmark model |
| 25 m is one per cent of this distance, and the subject is 75.0 m wide | the recorded reach against the recorded distance of 2,509.6 m and the recorded `plan_extent` of 75.0 by 75.0 m |
| the only sheet read this round with neither the props nor the kit budget biting | this sheet's `props.dropped_for_budget` of 0 and `kit` of 236 of 236, against the forty sheets read in the preceding rounds |
| the largest structures contribution in the pass | this sheet's 419,072 triangles, counted against every record carrying `scene.structures` |
| 15 February 2015 was a Sunday, and inside the leaf-off window | the record's own `crowd_clock`, and the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the published fraction is 0.0 while two rays hit the subject | the on-subject test uses a fixed 25 m reach regardless of distance or of the subject's own size, so a ray landing 6.9 m past the threshold on the subject's own model is scored as a miss. The repair is to scale the reach with the subject's measured extent, which the record already carries (J109, new) | **verification — open; this is one of two sheets whose zero in J100 is arithmetic rather than absence** |
| the record concludes the subject is not on the line | the note is generated from the miss count rather than from what the rays hit, so it names the subject's own model and then denies it. The same sentence appears on the Chrysler sheet | **verification — open; a record that mis-states its own failure is worse than one that reports it plainly** |
| the height is 292.65 m for a 541.3 m tower, and the fan aimed low | the ray at the coordinate met a 75.0 m square facet of the taper, and the fan is centred on the mid-height of that figure rather than on the subject's true angular extent (J94, J106) | **verification — open** |
| eleven rays stop on a joined limestone tile mesh | every surface of one material in a tile is joined into one object (J94) | verification — open |
| the harbour is not frozen | open water is a flat specular plane with no wave state, no turbidity and no ice state at all (J103). February 2015's pack ice is a condition this build cannot represent | **data — open, no source and no state** |
| no ferry and no wake | the boat is not modelled and the camera floats at the deck height it stands for | **declared decision — stated in the record's own eye-source field** |
| chroma 0.427 and 0.916 stops of exposure difference | a hazy procedural gradient against clear winter blue, and a photograph developed 1.151 stops above the grey convention while the render is metered to it (J83) | reference — declared, and correct |
| 17 building tiles not built and 16 drawn at a lower LOD | those tiles have no shell file, and the LOD substitution is the streaming rule working as designed at this range | data + performance |
| 56 structures tiles with no file | those tiles were not built (B13 remainder) | **data — open** |
| 47 modelled tree canopies in 3,971, and 2,332 substituted species | only 47 rows fall within the 120 m branch band, and the asset set is ten species with two states (J108) | performance + data |
| 1 tile with no park ground built | 85 per cent of the city's mapped open space has no ground geometry (J102) | data — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
