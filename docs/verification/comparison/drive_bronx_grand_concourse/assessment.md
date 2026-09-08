# Bronx drive-through: Grand Concourse Art Deco apartments

`drive_bronx_grand_concourse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:VZ E167 St exchange jeh.jpg by Jim.henderson, CC0 (https://creativecommons.org/publicdomain/zero/1.0/deed.en), 2012, 1920x1564. [Commons page](https://commons.wikimedia.org/wiki/File:VZ_E167_St_exchange_jeh.jpg)

**Camera** — 40.83200, -73.91860 (NYC_TM 2690, 14642) at z 27.6 m NAVD88 | azimuth 25.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1158x944. The camera stands on **the item's recorded viewpoint** — and was then **moved 44 m onto the nearest real roadbed polygon**, because the recorded viewpoint is *inside* `t_2_14_roof_membrane`: a ray straight up from the eye point hits that building's roof.

**Sun** — azimuth 95.5°, elevation 43.5° at 2012-06-21T09:30−04:00; 860.1 W/m² direct normal, sky at strength 0.0328, Filmic, +0.00 stops. The photograph carries a **year only**, so 21 June 09:30 is assumed. That date is a **Thursday** and the crowd was drawn for **a weekday**.

**In the scene**, within 720.0 m of the camera and not all of it in frame — 6/6 building tiles (323,032 tris), 2 landmark models of which **0 can fall inside the 54.4° frame**, 29,268 pavement polygons (12,068 white marking, 402 yellow, 5,530 roadbed, 4,902 sidewalk, 3,806 curb, 1,200 median, 767 crosswalk, 549 parking lot, 44 plaza), 400 props of the 872 in range, 5,560 kit pieces, 89 vehicles and 377 people; 4,500,067 triangles. Ground mesh 88,200 triangles, 0 holes.

## Verdict

**Two pictures of two places, and the sheet is explicit about it before a reader has to be.** The photograph is a four-storey brick institutional building seen across a corner in low winter sun; the render is a Bronx side street in June morning light looking 25° up the block. The item names no subject, the photograph's view direction was never derived from the image (confidence **medium**), and — the decisive fact — **the photograph's own EXIF GPS is 290.2 m from the viewpoint**, past the 250 m at which it could still be the same view. The record says what that means and what it does not: *"a statement about this pairing and not about the photograph: a fix this far out is usually correct and simply of somewhere else"* (docs/DEVIATIONS.md J60).

**As a comparison of Bronx fabric it is worth having.** Both halves show four-storey red and tan brick with punched window openings in a regular bay rhythm, a limestone or cast base band, a kerbside street lamp and parked cars. The render adds what the photograph's corner cannot show: fire escapes, a continuous street wall, and the tree line.

## What matches

* **The building stock is the right stock.** 3,961 windows, 436 window accessories, 137 quoins, 111 string courses, 82 cornices, 82 parapets, 73 entry doors and **59 fire escapes** stand in the frame out of 5,560 kit pieces. Red and tan brick tenements with punched openings and a masonry base is what both halves show.
* **The light is real and directional.** Hard tree shadows fall across the sunlit brick on the east side of the street while the west side stands in deep shade — the first render of this block with a shadow in it (docs/DEVIATIONS.md J67).
* **The road is a road.** 5,530 roadbed and 3,806 curb polygons carry the asphalt and concrete their own material names declare, with the kerb reading by its reveal and its shadow. 12,068 white and 402 yellow marking polygons are in range, and a lane line runs up the near carriageway.
* **1,200 median polygons** are in range — the Grand Concourse's planted central mall is in the data even where this frame does not point at it.
* **The crowd is dense and it is the simulation's own**: 377 people at 09:30 on a weekday, with 3 at LOD0, 7 at LOD1 and 368 at LOD2. The fleet is 40 sedans, 22 SUVs, **13 yellow taxis**, 4 black cars, 3 boro taxis, 3 vans, 2 box trucks and 2 MTA buses.
* **The street lamp is the right fixture** — 61 cobra-heads on curved masts, correct for an ordinary Bronx street (J56).
* Nothing was dropped for being missing: 6 of 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground, and **no prop kind unplaced at all**.

## What does not match

* **The two halves face different ways and stand 290 m apart**, so composition, framing and what fills the frame are not comparable here by construction.
* **The camera is 44 m from the recorded viewpoint**, because that viewpoint is inside a building. The move is correct behaviour and it is a second reason the two pictures are not the same view.
* **The frame is five times darker than the photograph and has a third of its colour**: mean **0.1286** against **0.6174** (**0.208×**), chroma **0.0390** against **0.1352** (**0.288×**), 95th percentile **0.4675** against **0.9184**, 5th percentile **0.0064** against **0.1440**. Most of the luminance gap is the pairing: the photograph is a sunlit elevation with a bright sky filling its upper third, the render is a shaded canyon looking along a street. **The chroma gap is not** — at 0.288 the render's surfaces carry markedly less colour than the street does, and three of them are at the albedo cap with the wrong material behind them (`concrete`, `roof_membrane`, `wood_clapboard`, J66). 17 city surfaces are dressed in this frame.
* **Both landmark models in the scene are behind or beside the camera** — Yankee Stadium and the Bronx County Courthouse — so the 2 placed is not 2 in frame, and the caption now says so.
* **No vehicle is visible** although 89 are placed within the vehicle radius and all 89 are at LOD2. They are behind the camera or beyond the trees. A drive-through sheet showing no traffic is not showing what the simulation is doing.
* **575 pedestrians and 123 vehicles were dropped for the triangle budget**, along with 472 props of the 872 in range (cap 1,336,935) and part of the kit (cap 1,392,997), and 15 opaque impostor cards. This is the only frame element trimmed for cost and the sheet declares every count.
* **206 trees stand within 250.0 m and 78 of them are species-substituted.** The canopy is the largest single influence on this frame's light.
* **The Art Deco the item is named for is not in the frame.** Grand Concourse's apartment houses carry stepped brick parapets, corner casements, terracotta banding and cast metal entrance surrounds; the render shows plain brick street wall with punched openings. The kit has 137 quoins and 111 string courses in range but no Deco vocabulary, and the facade classifier has no source that would tell it which block is Deco.
* The Sun is on an assumed instant — the photograph carries a year and nothing finer — so the shadow direction is not evidence about anything, which matters more now that the shadows are visible.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are of different places | the photograph's own GPS is 290.2 m away, past the 250 m band; the item names no subject and the direction was never derived from the image | reference |
| camera 44 m from the recorded viewpoint | that viewpoint is inside `t_2_14_roof_membrane` | verification |
| mean 0.208× and 95th percentile 0.468 against 0.918 | a shaded canyon against a sunlit elevation under a bright sky, plus a camera's automatic exposure against a renderer that never stops down | reference + stated choice |
| chroma 0.288× | not explained by exposure: `concrete`, `roof_membrane` and `wood_clapboard` sit at the albedo cap with the wrong source material behind them (J66) | material |
| 2 landmarks placed, 0 in frame | both stand behind or beside the camera; the count is a scene count and the caption now says which is which (J61) | — (not a gap) |
| no vehicle visible despite 89 placed | they are outside this 54.4° cone; placement is city-wide, the frame is not | verification |
| 575 people, 123 vehicles, 472 props dropped | triangle budgets 1,336,935 and 1,392,997, declared on the sheet | performance |
| no Art Deco vocabulary | the facade classifier has no source naming which block is Deco, and the kit carries no Deco parapet, casement or entrance surround | geometry |
| 78 of 206 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| Sun on an assumed instant | the photograph carries a year and nothing finer | reference |
