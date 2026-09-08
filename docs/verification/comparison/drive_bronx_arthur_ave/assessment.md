# Bronx drive-through: Arthur Avenue (Belmont)

`drive_bronx_arthur_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Arthur Avenue 09 - M&G Restaurant.jpg by Joe Mabel, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), 2026, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Arthur_Avenue_09_-_M%26G_Restaurant.jpg)

**Camera** — 40.85524, -73.88776 (NYC_TM 5255, 17278) at z 25.9 m NAVD88 | azimuth 190.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, 15.9 m from the item's recorded viewpoint — and was then **moved 36 m onto the nearest real crosswalk polygon**, because the recorded viewpoint is boxed in: the view azimuth is closed off 10 m ahead, less than the 12 m the frame needs.

**Sun** — azimuth 95.5°, elevation 43.6° at 2026-06-21T09:30−04:00. The photograph carries a **year only**, so 21 June 09:30 is assumed; this is the one input on this sheet that is a stated choice rather than a measurement.

**In frame** — 4/4 building tiles (261,870 tris), 0 landmarks, 14,249 pavement polygons (**11,437 white marking, 403 yellow marking**, 977 curb, 551 crosswalk, 403 roadbed, 241 sidewalk, 134 parking lot, 77 median, 26 plaza), 391 props of the 984 in range, 6,691 kit pieces, **89 vehicles and 275 people**; 4,500,309 triangles. Ground mesh 88,200 triangles, 0 holes.

**Verdict — the fabric matches and the composition cannot: the photograph is a facade close-up of one restaurant and the render is a street view down the avenue, which the sheet says of itself. Read as a comparison of street width, storey height, shopfront rhythm and material it holds up; read as a comparison of pictures it does not, and the caption is right to forbid that.**

## What matches

* **The street type is right.** Two- to four-storey party-wall blocks with a continuous glazed shopfront at ground level and residential windows above, in a regular bay rhythm, on both sides of a two-way street with kerbside parking — which is Arthur Avenue, and is what the photograph's fragment shows at close range.
* **The shopfront band reads correctly**: continuous glazing under a projecting awning line and a signboard fascia, at roughly the same proportion of the storey as the photograph's M&G frontage. 890 storefront and 122 storefront-interior kit pieces are in the frame, out of 6,691 kit pieces.
* **Road markings are drawn and legible.** A continental crosswalk — separate white bars with asphalt between them, not a painted slab — crosses the near roadway at the bottom of the frame. 11,437 white and 403 yellow marking polygons are in range (J52).
* **The crowd is the simulation's own and it is dense in the right way.** 275 pedestrians and 89 vehicles are placed from one frame of the traffic and pedestrian simulations at 09:30 on a June weekday, not scattered for effect. Figures stand on the pavement, one is crossing in the foreground, and the density falls away down the street.
* A red FDNY hydrant stands at the kerb on the right, and a cobra-head lamp standard leans over the carriageway at the upper left — the correct fixture for an ordinary Bronx street, and the one J56 confirms is still correct here (this is not a park).
* Street trees line both kerbs in leaf, which the photograph corroborates at its top right corner.
* Nothing was dropped for being missing: 4 of 4 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The two halves do not face the same way, and the sheet says so.** The item names no subject, and the photograph's view direction was never derived from the image — `estimated_viewpoint.confidence` is **medium**. The render looks 190° down the avenue; the photograph looks across the pavement at a single shopfront from a few metres. Composition, framing and what fills the frame are therefore not comparable here, by construction.
* **The camera is 36 m from where the photograph was taken**, having been moved onto the nearest crosswalk polygon because the recorded viewpoint had only 10 m of open air ahead of it. That is the correct behaviour for a usable frame and it is a second reason the two pictures are not the same view.
* **The render is far too dark.** Frame mean luminance **0.2322**, sd 0.1715, against a photograph in open daylight. The street tree canopy closes over the carriageway and shades almost the whole frame; the photograph's own tree is a single small crown. 199 trees are placed within 266 m and the allée they form is denser than Arthur Avenue's.
* **No vehicle is visible** in the frame although **89 are placed** within 320 m and all 89 are at LOD2. They are behind the camera or beyond the trees; a drive-through sheet that shows no traffic is not showing what the simulation is doing.
* The facades are flat-toned and uniform where the photograph's are not: painted brick, clapboard siding, a red-painted timber shopfront, a striped fabric awning and a hand-lettered sign, all different materials within ten metres. The render's block reads as one material family with the same awning colour repeated.
* No sign, awning text or shop name is legible, where the photograph's whole subject is a sign.
* The foreground pedestrian's clothing shows a visible texture seam across the trousers and the shoulder.
* **593 props in range were not placed** — the triangle budget capped at 1,376,923 — and 21 opaque impostor cards were dropped. This is the only frame element the sheet trims for cost, and it says so.
* The Sun is placed on an assumed instant. The photograph carries a year and no month, day or time, so 21 June 09:30 was chosen; the shadow direction in this frame is therefore not evidence about anything.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves face different ways | the item names no subject and the photograph's direction was never derived from the image (confidence medium) | reference |
| camera 36 m from the photograph's position | the recorded viewpoint has 10 m of open air, below the 12 m the frame needs, so the camera was walked onto the nearest crosswalk | verification |
| frame mean 0.23 against open daylight | the street-tree allée is denser than the real street's and closes the canopy over the carriageway | data |
| no vehicle in frame despite 89 placed | they are outside this 54.4° cone; the placement is city-wide, the frame is not | verification |
| flat, uniform facade materials | the facade classifier assigns one material family per block face; per-building paint, siding and shopfront colour are not in any source it reads | material |
| no legible sign or awning text | shopfront signage carries real business names as geometry but at this distance and resolution none resolves | geometry |
| texture seam on a pedestrian | the NPC bodies are exported with a single UV layout per garment and the seam falls on the visible side | geometry |
| 593 props not placed | triangle budget 1,376,923, declared on the sheet | performance |
| Sun on an assumed instant | the photograph carries a year and nothing finer | reference |
