# Brooklyn Bridge seen from DUMBO / Brooklyn Bridge Park

`landmark_brooklyn_bridge_from_dumbo` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn Bridge March 2023 009.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-03-07 13:20:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn_Bridge_March_2023_009.jpg) — the photograph's own view direction is derived from the image at **high** confidence, as 292.9°.

**Camera** — 40.704, -73.992 (NYC_TM -3549, 445) at z 3.7 m NAVD88 | azimuth 288.3°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on the item's recorded viewpoint — *"Pebble Beach at Main Street Park (Brooklyn Bridge Park), water's edge, looking west at the Brooklyn tower"*. This photograph's own EXIF GPS is **22.9 m** away and was not used, because the eye point there is inside `t_-4_0_roof_membrane`; the record names the test and the building. The camera was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 150 m, the nearest built thing in the frame is `prop_tree_honeylocust_medium_bare_6` 11.3 m away and the nearest simulated agent is `agent_ped_3.4` 45.9 m away.

**Sun** — azimuth 204.6°, elevation 41.1° at 2023-03-07T13:20:26−05:00, the photograph's own **EXIF DateTimeOriginal**; 847.9 W/m² direct normal, sky at strength 0.0333, Filmic, **+0.07 stops**. That date is a **Tuesday** and the crowd was drawn for a weekday.

**In the scene** — 9 building tiles, 3 landmark models of which 2 can fall inside the frame, 23,610 pavement polygons, 517 props of the 1,146 in range, 3,907 kit pieces, 88 vehicles and 434 people; 3,950,853 triangles, ground mesh 95,048 triangles with 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the tower is in the frame, the record says it is not, and the record's own coordinate is why

**The two halves are not the same picture and the reason is not the render.** The photograph is taken from directly beneath the Brooklyn tower, looking almost straight up its granite flank with the deck and the cable fan overhead. The render is the view the item asks for — Pebble Beach, water's edge, level axis at 285 m — and it is a wide plaza of bare plane trees with the bridge crossing the middle distance. Nothing here compares two pictures of the same thing.

**But the tower is in the render.** At the upper left, behind the trees: a pale granite pier with the pointed Gothic arch the Brooklyn Bridge's towers carry, the deck crossing in front of it, the suspenders and the cable fan running down to the right. Its top runs off the top edge of the frame. That is the subject of this sheet, in the sheet, at the edge — and the record says `subject_visible: false`.

**The record's subject coordinate is not on the tower.** It is called *Brooklyn Bridge Brooklyn tower*, and the height probe casts 17 rays at it, lands **17 of 17** on built fabric, and reads **44.2 m** above the ground there off `lm_b_brooklyn_bridge.82`. Forty-four metres is the bridge's **deck**. The catalogue entry `b_brooklyn_bridge` stands **138.0 m** away and publishes **84.3 m**, which is the tower. The coordinate is out on the main span (docs/DEVIATIONS.md J82), and every number the record derives from it is a correct number about a point in the middle of the river:

* the **azimuth** is 288.3° as recorded and agrees with the bearing to that coordinate to **0.1°** — so the frame is aimed 285 m out along the span, and the tower falls at its left edge with its top cut off;
* the **sightline** reports **4 of 5 rays clear and 4 into nothing**, meeting nothing at all out to 685 m, and the record says so in its own words: *"the line is open and the subject is not on it, which is a fault in the item's coordinate or in the model, not in the camera"*. It aims at *the subject's mid-height*, 22.1 m, and a deck at 44.2 m standing on piers has open air under it;
* the fifth ray is stopped at **127.6 m** by `prop_tree_honeylocust_large_bare_331` — a park tree, from a fan sized to a 44 m subject across a park planted with trees (J78).

**Read against the picture, not instead of it.** This sheet does not show that the Brooklyn Bridge is missing, badly placed or wrongly modelled. It shows that the point the item calls the tower is not the tower.

## What matches

* **The bridge is there and it is the Brooklyn Bridge.** The tower reads as masonry with a **pointed Gothic arch**, not as a steel frame, which is the one thing that distinguishes it from the Manhattan Bridge half a kilometre behind the camera. The deck, the suspenders and the diagonal stays are all in the model and all in the frame.
* **The site is Brooklyn Bridge Park in March.** A wide sunlit concrete and stone plaza, a low sea wall, benches, cobra-head lamps and **300 trees**, all leaf-off — and the leaf-off variants are selected from the photograph's own date, 7 March.
* **The instant is the photograph's own**, to the second: a 41.1° March sun at 204.6°, 847.9 W/m² direct normal, and the exposure moved only **+0.07 stops** to reach the target. The shadows fall the way a 41° sun casts them.
* **The rejection of the photograph's GPS is correct behaviour and is declared.** The eye point there is inside a roof; the record names the object rather than silently walking the camera.
* **The frame is as bright as the photograph** — mean **0.3888** against **0.348**, a ratio of **1.117**, and 95th percentile 0.5686 against 0.6887. Both halves are a sunlit late-winter noon and the render is if anything the brighter of the two. That is the closest luminance agreement on any landmark sheet in this pass.
* **The ground is whole**: 95,048 triangles, 0 holes, 23,610 pavement polygons placed and none dropped.

## What does not match

* **The two halves are of different views**, by the reference's own content: a 60°-up shot from under the tower against a level shot from 285 m away. Composition, scale and what fills the frame are not comparable here by construction.
* **The subject is at the edge of the frame with its top cut off**, and that follows from the coordinate: the axis is aimed out along the span rather than at the tower, by the angle J82 measures.
* **The trees stand in front of the bridge.** 300 of them, all bare, and the near ranks screen the tower. That is what Brooklyn Bridge Park is — but the reference photograph has none of them in it, because it was taken past them.
* **Chroma is 0.257×** — **0.0568** against **0.2208**, the second-lowest in the set so far. The photograph is granite against a saturated blue March sky filling two thirds of the frame; the render's sky is a clear gradient and its plaza is grey concrete. Part is the pairing and part is J66's remainder; this sheet cannot apportion it, because the two halves share almost no surface.
* **Standard deviation is 0.714×** — **0.1504** against **0.2107**. The photograph is high contrast: black stone in shadow against blown sky. The render's tonal range is compressed, which is what a large evenly-lit plaza gives.
* **The granite is a stone material, not Brooklyn Bridge granite.** At 200 m the tower reads as a pale mass with an arch; the coursed limestone-and-granite banding, the cornices and the cable-saddle ironwork are not resolvable and are not claimed from this frame.
* **`subject_visible: false`, and on this sheet the boolean is wrong** — for the reason the verdict gives.
* **Pedestrians and vehicles were dropped in their hundreds** — 1,367 people for being outside the radius, 509 for the triangle budget, 463 for standing in the carriageway without crossing, 189 for not being on a walkable surface, and **38 people and 28 vehicles were found inside buildings** and dropped for it. Brooklyn Bridge Park on a fine Tuesday is drawn with 434 people.
* **The kit is a warehouse kit and DUMBO is a warehouse district**: 3,907 pieces of which **3,306 are windows**, with 317 storefronts, 37 parapets, 36 cornices and 12 quoins. The Empire Stores and the surrounding brick lofts carry heavy arched openings and corbelled brickwork; these are extrusions with openings.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| `subject_visible: false` on a frame the tower stands in | the subject coordinate is on the deck, not the tower; the sightline aims at its mid-height, which under a deck on piers is open air, and 4 of 5 rays meet nothing out to 685 m | **verification — open, DEVIATIONS J82** |
| the tower is at the frame's edge with its top cut off | the recorded azimuth is derived from that same coordinate and agrees with it to 0.1°, so the axis points out along the span and not at the tower; the angle is measured in J82 | **verification — open, DEVIATIONS J82** |
| the fifth ray is stopped by a park tree at 127.6 m | the fan is sized to a 44 m subject and spans more than the gap between the trees; a probe fault, not a frame fault | verification — open, DEVIATIONS J78 |
| the two halves are of different views | the reference is taken from under the tower and the item's viewpoint is Pebble Beach, 285 m away; the render is of the viewpoint the item asks for | **reference — this pairing cannot be fixed by rendering** |
| chroma 0.257×, sd 0.714× | a saturated blue sky over black-and-white stone against a grey plaza under a clear gradient; the pairing dominates and this sheet cannot isolate J66's share | reference |
| trees in front of the bridge | 300 leaf-off park trees, correctly placed and correctly bare for 7 March; the photograph was taken past them | — (not a gap in the city) |
| the photograph's GPS was not used | the eye point there is inside `t_-4_0_roof_membrane`; the record names the test and the building | verification — correct behaviour |
| no coursed granite, no cable-saddle ironwork | the model carries the towers, the arches, the deck and the cable fan; this detail is below what 200 m resolves and is not claimed from this frame | — (not evidence) |
| 66 agents found inside buildings | the placement rules caught them and dropped them; the record names the rule and the count | verification |
