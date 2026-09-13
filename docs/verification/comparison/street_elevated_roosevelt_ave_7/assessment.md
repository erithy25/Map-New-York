# Elevated subway street: Roosevelt Avenue under the 7

`street_elevated_roosevelt_ave_7` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Roosevelt Avenue Jackson Avenue Station Station 001.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-12-26 13:41:01, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Roosevelt_Avenue_Jackson_Avenue_Station_Station_001.jpg) — camera GPS on the file, viewpoint confidence **medium**, and its own description says where it is: *"The Roosevelt Avenue Jackson Heights Station on the IND Queens Blvd Line."* **It is a photograph taken underground.** A tiled platform wall recedes down the frame with ROOSEVELT name tablets in black on white, a blue mosaic band above and a dark tiled dado below, fluorescent tubes on a concrete beam-and-slab ceiling, the ballasted track with its running rails and third rail, and the yellow platform edge along the bottom.

**Camera** — 40.7466, -73.8912 (NYC_TM 4966, 5177) at z 22.391 m NAVD88, a 1.6 m standing eye over terrain read at 20.791 m — the 10th percentile of 113 samples within 12.0 m, whose range is 20.6 to 21.18 | azimuth 75.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1280x720. The camera is on the item's recorded viewpoint, and the reason it is not on the photograph's is worth quoting whole: *"This photograph's own EXIF GPS is 34 m away, but the eye point there is inside `t_4_5_struct_el_steel` (a ray straight up from the eye point hits its roof), while the recorded viewpoint is in open air."* So the sheet whose note reads *"roadway centre under the 7 train structure"* was placed, on purpose, at the one nearby point with nothing over it (J115). The camera was **not moved**: it reports *"the view azimuth is clear for 16 m"* — **15.8 m against its own 20.0 m minimum** — with `prop_bike_rack_cityrack_34` 7.0 m away and a simulated pedestrian at 8.0 m.

**Sun** — azimuth 205.8°, elevation 21.5° at 2025-12-26T13:41:01-05:00, from the photograph's own EXIF DateTimeOriginal; 675 W/m² direct normal, Nishita sky, Filmic, **+3.50 stops**. Metered: **3.496 stops** on a linear median of **0.01595** against a physical rule of 1.01 — under the 4-stop threshold, so not declared under-lit, though only just. The instant is real and it lights an outdoor scene that the photograph, being underground, has no counterpart for.

## Verdict — an underground platform beside a brick wall seven metres away, and the right photograph was in the folder

**The reference is inside a subway station on a different line.** The item is Roosevelt Avenue under the **7**, an elevated line at Jackson Heights; the photograph is the **IND Queens Boulevard Line** platform beneath it, and says so in its own stored description and in its Commons category, *"Jackson Heights – Roosevelt Avenue (IND Queens Boulevard Line)"*. The item is flagged `interior: false`. The fetch's indoor screen rejected one candidate on this item and let this one through, because a station platform's title and description contain no word the screen knows.

**And the photograph the sheet needed was kept and ranked last.** Candidate 3, `File:Jackson Heights, Queens NY.jpg`, is described by its own author as *"A full shot of Jackson Heights located in Queens borough of New York, shown with diverse commercials restaurants and the 7 line MTA track"* — the street, the shops and the elevated, which is the sheet's entire brief — 123 m from the reference position, with a full EXIF timestamp. It scores **14.45** against the chosen 15.2 and it loses on the **hard day/night gate**: taken at 19:05:09 on 22 September 2018, when the Sun over this coordinate stands at **-3.20°**, twelve minutes past sunset. A daylight item may not take an after-dark frame, and that rule, which exists to stop a black render, here discarded the only street-level photograph in the folder. Candidate 2 is *"Views from IRT Flushing Line stations"* — taken from the elevated platform, not under it — and carries only a year, so it loses to the clock. Three candidates: one underground, one on the platform, one on the street. The gates removed the street.

**The render is a picture of a brick wall.** With the camera standing where the elevated is not, aimed at 75.0° with a 35 mm lens, the frame is filled by a flank wall about 7 m off: **no elevated, no track, no columns, no station, no storefronts, no trees** — a pale brick plane, a strip of sidewalk, the kerb, and eight pedestrians walking away along it, several in hi-vis vests. The record's own numbers predict it: 15.8 m of clear view where the frame asks for 20.0.

**Nothing moved the camera, and that is by design.** `min_view_m` is a filter applied to candidate positions *after* a move has been triggered, not a trigger of its own; the walk's docstring is explicit that *"the camera is only moved when it is demonstrably inside geometry"*. A camera standing in open air two car-lengths from a wall is never demonstrably inside anything. **Six records in the pass end with less clear view than their own minimum, and this is the only one that did not try** — the other five moved between 10.0 and 106.8 m and still fell short, which is a search failing honestly.

**The elevated is loaded and none of it is in the picture.** 4 structures tiles, **0 without a file, 53,628 triangles** — the largest structures contribution of any streetscape sheet in the pass — carrying the 7 train's deck, bents, platform and canopy above Roosevelt Avenue, 34 m from where the photographer stood and outside a frame that can see 15.8 m.

**The tone gap is the largest thing the two halves agree to disagree about.** The photograph's median sits **1.556 stops below** the grey convention: an underground platform is a dark box with fluorescent tubes in it. The render is metered to 0.246 above. That is a **1.802-stop** gap with the render brighter, a p50 ratio of **1.819**, and a range ratio of **0.488** — the render has less than half the photograph's contrast, because a flat sunlit brick wall has no highlight and no shadow while the reference has blown tubes over a black track bed. Chroma alone agrees, at 0.969, and it is agreeing by coincidence: cream tile and blue mosaic against pink brick and hi-vis yellow.

**What the scene has, out of frame.** 4 of 4 building tiles with none missing or LOD-substituted, 313,508 triangles; **7,215 kit pieces** with nothing capped and nothing suppressed, among them 4,144 windows and **1,200 storefronts** — the shopfront density Roosevelt Avenue actually has; 26,110 pavement polygons with 11,812 white markings and 801 crosswalk; 3,181 props with **none dropped**, including 33 subway vent grates and 9 subway entrances. All of it behind or beside the wall.

**And no park ground at all**: 0 meshes and 0 surfaces, with 4 tiles in the 754 m radius carrying no park-ground file.

## What matches

* **The instant is real** and taken from the photograph's own EXIF.
* **The elevated is built and complete here**: 4 structures tiles, none without a file, 53,628 triangles.
* **The street's commercial density is modelled**: 1,200 storefronts and 4,144 windows over 4 complete building tiles.
* **Nothing dropped from the props budget** and nothing capped in the kit.
* **The record states plainly why the camera is not on the photograph's GPS**, and why the two halves may not face the same way.
* **The pedestrians are dressed for late December** and the trees are leaf-off, both correct for 26 December.

## What does not match

* **The reference is an underground platform on the IND Queens Boulevard Line**, on a sheet about a street under the elevated 7 (J71).
* **The one street-level photograph in the folder was excluded** because its Sun sits 3.20° below the horizon.
* **The render is a brick wall 7 m away** with 15.8 m of clear view against a 20.0 m minimum, and the camera was not moved.
* **The elevated is not in the frame**, on the sheet named for standing under it (J115).
* **No track, no third rail, no station, no train, no tiled wall, no name tablet** — none of the photograph's content has a counterpart, and none of it could.
* **1.802 stops brighter with 0.488× the range**: daylight against a lit underground box.
* **No park ground**: 0 meshes and 0 surfaces over 4 tiles with no file.
* **No signage** of any kind (J110), against a photograph whose subject is a row of station name tablets.
* **Five yellow cabs to two boro taxis in Jackson Heights** (J105), one of the densest boro-taxi neighbourhoods in the city.
* **828 people dropped to the triangle budget** and 828 more outside the radius, on a corner that is among the busiest transit interchanges in Queens.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the excluded street-level candidate's Sun stands 3.20 deg below the horizon at its own timestamp | `sun_for(40.7466, -73.8912, 2018-09-22 19:05:09 America/New_York)` from `blender/verify/render_sheets.py`, against the `lit_bad` gate in `pick_reference_photo`, which requires a daylight item's photograph to have the Sun above 3 deg |
| the three kept candidates are an underground platform, a view from the elevated platform, and the street | the `description` and `categories` fields of `docs/verification/reference/street_elevated_roosevelt_ave_7/meta.json`, with their scores of 15.2, 15.05 and 14.45 |
| six records in the pass end with less clear view than their own minimum, and this is the only one whose camera was not moved | the `clearance.view_m`, `min_view_m` and `moved` of all 171 records; the other five moved between 10.0 and 106.8 m |
| the minimum view is a filter on candidates rather than a trigger for the walk | the docstring of `_move_clear_of_geometry` in `blender/verify/camera.py`: "The camera is only moved when it is demonstrably inside geometry" |
| 7,215 kit pieces | the sum of the record's `scene.kit.per_category`, whose `total` is null |
| 26 December is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is an underground station | the indoor screen matches words like lobby and corridor and knows nothing of platforms, and nothing tests what a photograph is a picture of (J71, and J57's note on the same screen) | **verification — open** |
| the street-level candidate was discarded | the day/night gate is a hard first term and a photograph taken twelve minutes after sunset fails it outright, whatever else it is right about | **verification — open; the gate is correct and its priority is not** |
| the camera stands where the elevated is not | the origin rejected the photograph's GPS for being under the structure, because the indoors test cannot tell a railway deck from a ceiling (J115) | **verification — open** |
| a brick wall at 7 m | `min_view_m` filters candidate positions once a move has been triggered and never triggers one; a camera in open air is never moved however little it can see | **verification — open** |
| 1.802 stops brighter with half the range | one half is outdoors at 21.5 deg of December Sun and the other is a fluorescent-lit underground platform | reference — the pairing, not the render |
| no signage of any kind | the verification renderer never reads the sign or signal export (J110) | **verification — open** |
| no park ground | 4 tiles in range carry no park-ground file | data — open |
| five yellow cabs to two boro taxis | `TrafficSim::sampleClass` splits the taxi share with no geography (J105) | **runtime — open** |
| 828 people dropped to the triangle budget | a 1,125,000-triangle agent budget against 1,502 people the density table asks for at this interchange | performance — declared |
