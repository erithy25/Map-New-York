# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Arthur Avenue 09 - M&G Restaurant.jpg by Joe Mabel, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), 2026, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Arthur_Avenue_09_-_M%26G_Restaurant.jpg)

**Camera** — 40.85524, -73.88776 (NYC_TM 5255, 17278) at z 25.9 m NAVD88 | azimuth 190.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, 15.9 m from the item's recorded viewpoint — and was then **moved 36 m onto the nearest crosswalk**, because the recorded viewpoint is boxed in: the view azimuth is closed off 10 m ahead, less than the 12 m the frame needs. From the new point the view is clear for 45 m, the nearest built thing in frame is `prop_tree_honeylocust_medium_6` 18.3 m away and the nearest simulated agent is `agent_ped_545.6` 4.6 m away.

**Sun** — azimuth 95.5°, elevation 43.6° at 2026-06-21T09:30−04:00. The photograph carries a **year only**, so 21 June 09:30 is assumed — the one input on this sheet that is a stated choice rather than a measurement. That date is a **Sunday**, and the crowd was drawn for one.

**In the scene**, within 735.9 m of the camera and not all of it in frame — 4/4 building tiles (261,870 tris), 0 landmark models, 25,829 pavement polygons (11,437 white marking, 5,027 sidewalk, 4,117 roadbed, 3,331 curb, 670 crosswalk, 656 parking lot, 403 yellow marking, 148 median, 40 plaza), 451 props of the 984 in range, 6,680 kit pieces, 89 vehicles and 275 people; 4,500,218 triangles. Ground mesh 88,200 triangles, 0 holes. 14 city surfaces are dressed from the shared photographic catalogue.

## Verdict

**The fabric is right and the composition cannot be, which the sheet says of itself.** The photograph is a close-up of one restaurant frontage; the render is a street view down the avenue. Read as a comparison of street width, storey height, shopfront rhythm and material it holds up well. Read as a comparison of pictures it does not, and the caption forbids that: the item names no subject and the photograph's own view direction was never derived from the image (confidence **medium**).

**This is the first render of this street that is a street rather than a tree tunnel.** The 233 trees over it now stand at the height the census measured them, at a mean scale of **0.797** — the lowest of any sheet in the set, which is to say Arthur Avenue's canopy was the most oversized in the city — and none fell outside the scale band. What that bought is visible without measuring anything: the carriageway runs to the vanishing point, the shopfront band and its awning line read as a line, a cobra-head lamp and a hydrant stand at the kerb, pedestrians are legible at 60 m, and there is sky between the crowns.

## What matches

* **The street type is right.** Two- to four-storey party-wall blocks, a continuous glazed shopfront at ground level under a projecting awning line, residential windows above in a regular bay rhythm, on both sides of a two-way street with kerbside parking. That is Arthur Avenue, and it is what the photograph's fragment shows at close range.
* **The shopfront band reads correctly** and is built rather than painted on: **898 storefront and 123 storefront-interior** pieces stand in the scene out of 6,680, with 3,900 windows, 715 window accessories, 191 entry doors, **147 fire escapes**, 176 parapets, 117 quoins, 116 cornices, 109 string courses and 77 pilasters. The fire escapes in particular are a Bronx tenement signature and they are there.
* **The road surface is a road.** 4,117 roadbed and 3,331 curb polygons are drawn with the asphalt and concrete their own material names declare, and the kerb reads by its reveal and its shadow rather than by a lighter tone. A continental crosswalk — separate white bars with asphalt between them, not a painted slab — crosses the near roadway.
* **Road markings are drawn and legible**: 11,437 white and 403 yellow marking polygons in range (J52).
* **The crowd and the traffic are the simulation's own.** 275 people and 89 vehicles from one frame of the pedestrian and traffic simulations at 09:30 on a **Sunday**, not scattered for effect. The fleet is plausible for the Bronx: 49 sedans, 18 SUVs, 5 black cars, 5 yellow taxis, **4 MTA buses**, 3 box trucks, 3 vans and 2 boro taxis.
* **The lamp standard is the right fixture.** 72 street lamps in the scene, cobra-head on a curved mast, which is what an ordinary Bronx street carries and what J56 confirms is still correct here — this is not a park.
* A red FDNY hydrant stands at the kerb; 30 are in the frame's props, along with 50 rooftop cooling towers and 62 manholes.
* Nothing was dropped for being missing: 4 of 4 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground, and only one prop kind unplaced (a parks comfort station).

## What does not match

* **The two halves do not face the same way, by construction.** The item names no subject, the photograph's direction was never derived from the image, and the render looks 190° down the avenue while the photograph looks across the footway at a single shopfront from a few metres.
* **The camera is 36 m from where the photograph was taken.** It started on the photograph's own EXIF GPS, 15.9 m from the recorded viewpoint, and was walked onto the nearest crosswalk because the recorded viewpoint had only 10 m of open air ahead of it. That is correct behaviour for a usable frame and a second reason the two pictures are not the same view.
* **The frame is much darker than the photograph and has far less colour in it**: mean **0.1481** against **0.3920** (**0.378×**), standard deviation **0.1353** against **0.2686** (**0.504×**), 95th percentile **0.4293** against **0.8750**, and a 5th percentile of **0.0** against **0.0519** — there is pure black in this frame and none in the photograph. Part of that is real and part is not, and the two parts should not be confused. The render is a canopy-shaded street at 09:30 and the photograph is a sunlit shopfront; a camera's automatic exposure lifts a shaded street and this renderer deliberately never stops down. But **0.357 of the photograph's chroma is not explained by exposure** — **0.0329** against **0.0921** — and the render's surfaces carry less colour than the street does.
* **Two city surfaces are drawn with a texture that is the wrong material, not the wrong exposure**: `concrete` and `roof_membrane` bind the albedo cap, and their residuals are published in the record (J66).
* **233 trees stand within 265.9 m and 80 of them are species-substituted.** They are drawn at the height their own row records; the species they are drawn *as* is the nearest by size and taxon rather than the one the census names.
* **533 props in range were not placed** — the triangle budget capped at 1,368,778 — and **20 opaque impostor cards were dropped**. The kit was capped too, at 1,644,785.
* **The facades are more uniform than the street is.** The classifier assigns one material family per block face, and per-building paint, siding and shopfront colour are in no source it reads. The photograph's ten metres carry painted brick, clapboard, a red timber shopfront, a striped fabric awning and a hand-lettered sign.
* **No sign, awning text or shop name is legible.** The photograph's entire subject is a sign.
* The Sun is placed on an assumed instant: the photograph carries a year and no month, day or time, so 21 June 09:30 was chosen. The shadow direction in this frame is therefore not evidence about anything — which matters more now that the shadows are visible.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves face different ways | the item names no subject and the photograph's direction was never derived from the image (confidence medium) | reference |
| camera 36 m from the photograph's position | the recorded viewpoint has 10 m of open air, below the 12 m the frame needs, so the camera was walked onto the nearest crosswalk | verification |
| mean 0.378× and 95th percentile 0.429 against 0.875 | a canopy-shaded street at 09:30 against a sunlit shopfront, plus a camera's automatic exposure against a renderer that never stops down | reference + stated choice |
| chroma 0.357× | not explained by exposure: the dressed surfaces carry less colour than the street, and two of them (`concrete`, `roof_membrane`) are the wrong material at the albedo cap (J66) | material |
| a 5th percentile of 0.0 | the shaded side of the street receives sky light only, and Filmic maps the darkest of it to black; the renderer opens no stops | stated choice |
| 80 of 233 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| 533 props and part of the kit not placed | triangle budgets 1,368,778 and 1,644,785, declared on the sheet | performance |
| uniform facade materials | one material family per block face; per-building paint and shopfront colour are in no source | material |
| no legible sign or awning text | shopfront signage carries real business names as data but nothing resolves them to geometry at this distance (B15a) | geometry |
| Sun on an assumed instant | the photograph carries a year and nothing finer | reference |
