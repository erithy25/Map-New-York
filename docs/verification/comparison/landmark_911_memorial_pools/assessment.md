# National September 11 Memorial pools

`landmark_911_memorial_pools` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:National September 11 Memorial South Pool - 04.jpg by Oleg Yunakov, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-09-11 17:01:35, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:National_September_11_Memorial_South_Pool_-_04.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.711156, -74.012633 (NYC_TM -5293, 1241) at z 5.8 m NAVD88 | azimuth 314.3°, pitch +0.0° | 35 mm on 36 mm (42.2° horizontal, portrait) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, 36.9 m from the item's recorded viewpoint, and was **not moved**. The eye point stands on `lm_b_wtc_site.233` — the memorial plaza's own deck — and because this position is the photograph's own rather than a nominal viewpoint standing for a whole structure, there is nothing to walk to and nothing was walked. The view azimuth is clear for 150 m and no simulated agent stands within 60 m.

**Sun** — azimuth 254.4°, elevation 23.6° at 2025-09-11T17:01:35−04:00, from the photograph's own **EXIF DateTimeOriginal**. That date is a **Thursday** and the crowd was drawn for a weekday. Both the instant and the position on this sheet are the photograph's own, and the instant is the anniversary itself.

**In the scene**, within 600.7 m of the camera and not all of it in frame — 4 building tiles (106,490 tris), 10 landmark models of which **1 can fall inside the 42.2° frame**, 22,728 pavement polygons (8,296 white marking, 3,994 plaza, 3,649 roadbed, 3,192 sidewalk, 2,585 curb, 454 crosswalk, 321 median, 142 yellow marking, 95 parking lot), 413 props of the 1,932 in range, 1,826 kit pieces, 88 vehicles and 438 people; 3,510,212 triangles. Ground mesh 67,010 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the subject is a void and a bronze parapet with the names on it, and the model has neither

**The memorial is the one thing on this plaza that the build does not contain, and the record says so in a number rather than leaving it to be noticed.** The height probe casts 17 rays at the North Pool's own coordinate; **16 of them land on built fabric** and the highest is `lm_b_wtc_site.232` at **0.1 m** above the ground there. That is the plaza deck. There is no basin, no thirty-foot drop, no falling water, no bronze parapet and no incised names: at the pool's coordinate the world is flat. The record refuses to give the subject a height on that basis — *"below the 2 m at which a subject has a height worth aiming or framing by"* — and refuses to report a sightline, which is the correct output and is why this sheet carries `subject_visible: null` rather than a verdict.

**The photograph is entirely made of the things that are missing.** It is a close view along the parapet: black granite and bronze, the names of the dead incised through it, roses and a small flag pushed into the letters by people who came on the anniversary, the pool's black water and the reflection of a tower in it. Not one of those five things exists in this build.

**What the render does contain is the plaza around the hole.** The swamp white oak grove, the benches, the lamps, the paving and the surrounding towers are all there, in the right places, in the evening light of the photograph's own instant. Read as a comparison of the memorial it shows nothing; read as a comparison of the site the memorial stands in it holds up.

## What matches

* **The grove is the grove.** 294 trees stand within 286.9 m — the memorial plaza's oaks are planted in a grid and the render's canopy reads as one, receding along the pool's long side exactly as the reference's does above the parapet.
* **The plaza is paved as a plaza**: 3,994 plaza polygons and 3,192 sidewalk polygons carry concrete from their own material names, and the pool's coping runs away from the camera as a continuous low edge in the right place.
* **The furniture is the memorial's furniture** — 57 benches and 38 lamps, which is what the plaza carries and what the photograph shows in its middle distance.
* **The instant is the photograph's own**, down to the second, and it is the anniversary: 11 September, 17:01. The low evening light raking across the plaza is the light the reference was taken in.
* **The camera stands where the photograph was taken**, on its own EXIF GPS, and was not moved — which is the best case this pipeline has.
* **The World Trade Center site model is the one landmark that can fall inside the frame**, at 63.4 m and 0.1° off axis. The nine others in the scene are behind or beside the camera and the record distinguishes the two (J61).
* Nothing was dropped for being missing: 4 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground, and the kit was not capped.

## What does not match

* **There is no pool.** No basin, no thirty-foot walls, no water, no falling sheet, no void. The probe's 0.1 m is the measurement of that.
* **There is no parapet and there are no names.** The memorial's subject — the bronze band carrying the name of every person killed — is the photograph's whole foreground and is absent from the model. `memorial` is one of the prop kinds with **no asset at all**, and the record counts it: 1 unplaced memorial in this scene (J23).
* **There are no flowers and no flags**, which is what the photograph is a picture of on this date. The build has no notion of what people leave on an anniversary.
* **The frame is a third of the photograph's brightness and carries under a third of its colour**: mean **0.1284** against **0.4068** (**0.316×**), standard deviation **0.0934** against **0.2388** (**0.391×**), chroma **0.0334** against **0.1162** (**0.287×**), 95th percentile **0.3113** against **0.7841**, 5th percentile **0.0028** against **0.1088**. Three things are in that and they are not the same: the photograph's frame is filled at close range by a sunlit bronze slab and coloured flowers, the render's by shaded paving and dark canopy; the render's darkest pixels reach almost pure black where the photograph's floor is 0.109; and the canopy over this camera is dense.
* **293 of the 294 trees are species-substituted** and the mean scale is **0.708** — the lowest on any sheet so far, meaning the memorial's oaks are drawn at seven tenths of the height the census records for them — with **3 outside the declared scale band**, drawn at their asset's own size and counted (J70).
* **413 props of the 1,932 in range were placed**, and the rest were not — triangle budget 1,301,459 — along with 4 opaque impostor cards.
* **608 pedestrians were dropped for standing in the carriageway without crossing** and 412 more for not being on a walkable surface. The memorial plaza on 11 September is one of the most crowded places in the city and the render carries 438 people, none of them at the parapet.
* **The reference is 1920x2560 and the render is 904x1206.** The aspect is matched; the resolution is not, and no claim here rests on fine detail.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no pool, no void, no water | the memorial's basins are not modelled; at the subject's coordinate the plaza deck is the highest built thing, 0.1 m above its own ground | **geometry — the subject of the sheet** |
| no parapet, no incised names | `memorial` has no prop asset and the landmark model carries the site rather than its monuments; it stays unplaced rather than become the wrong object (J23) | geometry |
| no flowers, no flags | the build has no notion of what people leave on an anniversary; nothing in any source records it | data — no source exists |
| mean 0.316×, 5th percentile 0.003 against 0.109 | the photograph is filled at close range by sunlit bronze and flowers, the render by shaded paving under a dense canopy; the renderer opens no stops and Filmic maps the darkest of it to black | reference + stated choice |
| chroma 0.287× | the photograph's colour is flowers and a flag a metre from the lens; the render's surfaces are concrete, granite and leaf, and one material family is stated per facade class (J66) | reference + material |
| 293 of 294 trees species-substituted, mean scale 0.708 | no modelled species matched exactly; the nearest by size and taxon was used, and the memorial's oaks are drawn well under their measured height | data |
| 3 trees outside the scale band | their measured height is further from the nearest exported size than the declared band allows, so they keep the asset's own size and are counted (J70) | data |
| most of the props in range unplaced | triangle budget 1,301,459, declared on the sheet | performance |
| pedestrians dropped in their hundreds, and none at the parapet | the placement rules — not in the carriageway, on a walkable surface — each named in the record; nothing draws a crowd to a monument | verification + data |
