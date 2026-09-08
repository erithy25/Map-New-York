# Washington Street in DUMBO with the Manhattan Bridge

`dumbo_washington_st_manhattan_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Manhatten Bridge - taken from Washington Street.jpg by David Kernan, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-11-23 14:17:56, 1920x3413. [Commons page](https://commons.wikimedia.org/wiki/File:Manhatten_Bridge_-_taken_from_Washington_Street.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.703061, -73.989602 (NYC_TM -3347, 341) at z 5.1 m NAVD88 | azimuth 1.4°, pitch +0.0° | 28 mm on 36 mm (39.8° horizontal, portrait) | 784x1394. The camera stands on **this photograph's own EXIF GPS**, 34.6 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 150 m, the nearest built thing in the frame is `prop_lamp_cobra_davit_1` 1.5 m away, and no simulated agent stands within 60 m of it.

**Sun** — azimuth 218.4°, elevation 18.9° at 2024-11-23T14:17:56−05:00, from the photograph's own **EXIF DateTimeOriginal**; 636.0 W/m² direct normal, sky at strength 0.0417, Filmic, **+1.20 stops**. That date is a **Saturday** and the crowd was drawn for one. Both the instant and the position on this sheet are the photograph's own.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 9 building tiles (246,176 tris), 3 landmark models of which **1 can fall inside the 39.8° frame**, 28,793 pavement polygons (13,999 white marking, 4,944 curb, 4,076 sidewalk, 4,054 roadbed, 733 crosswalk, 282 yellow marking, 255 median, 226 parking lot, 224 plaza), 564 props of the 1,426 in range, 4,489 kit pieces, 85 vehicles and 376 people; 4,500,000 triangles. Ground mesh 96,800 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the view is now the view, and the thing it is a view *of* is the thing least well modelled

**The tower stands centred between the warehouse blocks, and until this render it did not.** Washington Street framing the Manhattan Bridge's Brooklyn tower is one of the seven viewpoints the brief names, and the whole of it is that alignment. The camera looks along **1.4°**; Washington Street's own centreline at this point bears **2.6°** in `segments.parquet`. The previous render looked along 357.1° and put the bridge to the right of the axis, and the reason was not the camera: the item's recorded subject coordinate stood **29.7 m off the Manhattan Bridge's own carriageway** and **62 m** from the tower, and the azimuth was derived from it (docs/DEVIATIONS.md J75). Moving the subject onto the tower moved the frame onto the view.

**The bridge is a plain blue box truss where the photograph is a riveted Beaux-Arts portal.** The reference shows a pointed arch between finial-capped columns, lattice bracing and rivet lines, with the Empire State Building visible through the opening five kilometres away. The render's tower is a smooth pale-blue truss with a single X-brace: no arch, no columns, no finials, no opening. The model is exact where it was measured — its catalogue entry states towers, main span and clearance from published values, and the probe reads its steel here at **107.38 m** above the ground at the subject's coordinate against the **106.68 m** the catalogue publishes — and it is a massing where the photograph is architecture.

**The record says the subject is not visible and the picture shows it filling the upper middle. The record is wrong here, and the reason is worth stating rather than hiding.** See *What the record gets wrong about itself* below.

## What matches

* **The framing, which is the point of this viewpoint.** The tower sits between the two warehouse blocks with sky either side of it, as it does in the photograph. This is what J75 bought.
* **The street is Washington Street.** A narrow canyon of five- and six-storey brick warehouse blocks, a green-painted storefront band running along the left frontage at ground level, cornice lines and window rhythm on both walls, and a roadway that runs straight to the bridge. 4,489 kit pieces stand in the scene — **3,783 windows**, 343 storefronts, 43 cornices, 43 string courses, 35 scaffold pieces, 26 entry doors, 19 bulkheads and 9 fire escapes.
* **The road is drawn and marked.** 4,054 roadbed, 4,944 curb and 4,076 sidewalk polygons carry asphalt and concrete from their own material names, and **13,999 white and 282 yellow marking polygons** are in range — a lane line runs up the middle of the frame and a manhole cover sits in the near carriageway. An earlier assessment of this sheet said the roadway carried "no lane lines, no crosswalk stripes"; that was true when it was written and J52 is why it is not true now.
* **The brick is photographic, not a flat colour.** 20 city surfaces are dressed from the shared CC0 catalogue, and the two walls read as brick with mortar and courses rather than as two RGB values. The same earlier assessment said "the brick walls have no texture… flat base colours"; J63 is why that is no longer so.
* **The trees are bare, correctly.** The reference was taken on 23 November and the leaf-off variants are selected from the photograph's own date. **221 trees** stand within 284.6 m at a mean scale of **0.9**, none outside the declared band.
* **The light is the photograph's own light.** A 18.9° November sun at 218.4° rakes the left wall and leaves the right in shade, which is what the reference shows.
* **The crowd and the fleet are the simulation's own** — 376 people and 85 vehicles at that Saturday afternoon instant. A green boro taxi stands at the near kerb, a white van at the far one, and pedestrians are legible at the end of the block.
* Nothing was dropped for being missing: 9 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What the record gets wrong about itself

* **`sightline.subject_visible` is `false`, and the tower fills the upper middle of the frame.** The probe casts five rays in a cross, sized since J76 to the subject's own measured height — a fan **107.4 m** across, a half-angle of **13.35°** — and **0 of 5** reach the tower; the nearest blocker is `prop_lamp_cobra_davit_1` at **3.8 m**. Both halves of that are true and the conclusion drawn from them is not. A fan as wide as a 107 m subject seen from 226 m spans **±53 m** at the subject, and Washington Street is about twenty metres wide: the two lateral rays meet the warehouse walls by construction, the upper ray meets the left block's parapet, and a lamp standard three metres from the lens takes another. **Sizing the fan to the subject was right for a subject standing in the open and is wrong for one seen down a canyon**, and this sheet is the case that shows it (docs/DEVIATIONS.md J78). The published ray counts are the thing to read, not the boolean, and the picture is the thing to read before either.
* This is the second correction this sheet has forced on the probe rather than on the world. Before J72 it read `false` on an invented 10 m subject height; before J74 it read `null` because the height was measured off a *model's origin* 226 m away rather than off the steel; it now reads `false` for a third reason. Each was a real fault in the measurement and none of them was ever a fault in the frame.

## What does not match

* **The tower has no portal, no arch and no rivets.** `b_manhattan_bridge` is exact to published dimensions and carries no architectural detail; the Beaux-Arts portal the photograph is a picture of is not modelled. This is the largest single gap on the sheet.
* **The Empire State Building is not visible through the tower**, because there is no opening to see it through — a consequence of the same simplification, not a separate one.
* **The frame is much darker and much less colourful than the photograph**: mean **0.1993** against **0.5499** (**0.362×**), standard deviation **0.1601** against **0.2506** (**0.639×**), chroma **0.053** against **0.1791** (**0.296×**), 95th percentile **0.5397** against **0.8803**, 5th percentile **0.0639** against **0.1424**. The photograph is a tall portrait frame whose upper half is bright sky over sunlit steel; the render is the same view with a canyon in shadow filling more of it, because a level 28 mm frame holds more roadway than a tilted 60 mm one does. The chroma gap is not exposure: **two surfaces still bind the albedo cap** (`roof_membrane`, `wood_clapboard`) and, more than that, one material family is stated per facade class where a DUMBO block carries several brick colours at once (J66).
* **The lens and the axis are not the photograph's.** 28 mm level against about 60 mm tilted up: the record says why — a level axis keeps the verticals vertical, which is the only way the two frames can be compared on proportion, and the 28 mm is the longest normal lens that still contains a 107 m tower at 226 m without tilting.
* **564 props of the 1,426 in range were placed**, and the rest were not — triangle budget 1,262,772 — along with part of the kit (cap 1,262,193) and **13 opaque impostor cards**. Eight point props have no asset at all: 4 misc structures, 2 drinking fountains, a parks building and a payphone.
* **141 of the 221 trees are species-substituted**: they stand at the height their own rows record, but drawn as the nearest species by size and taxon rather than the one the census names.
* **594 pedestrians were dropped for standing in the carriageway without crossing**, 254 more for not being on a walkable surface and 509 more for the triangle budget; 68 vehicles were dropped for having no rider and 313 for the budget. The frame shows what survived those rules, which is fewer people than a Saturday afternoon in DUMBO has.
* **The reference is 1920x3413 and the render is 784x1394.** The aspect is matched to the photograph; the resolution is not, and no comparison here rests on fine detail.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the tower has no portal, arch, columns or rivets | `b_manhattan_bridge` is built to published dimensions and carries no architectural detail; the Beaux-Arts portal is not modelled | **geometry — the largest gap on this sheet** |
| no Empire State Building through the arch | the same simplification: there is no opening to see it through | geometry |
| `subject_visible: false` on a frame the tower fills | a five-ray cross sized to a 107 m subject spans ±53 m at 226 m and Washington Street is 20 m wide, so the walls and a lamp take every ray | **verification — open, DEVIATIONS J78** |
| mean 0.362×, 95th percentile 0.540 against 0.880 | a level 28 mm frame holds more shadowed canyon and less sky than the photograph's tilted long lens, plus a camera's automatic exposure against a renderer that never stops down | reference + stated choice |
| chroma 0.296× | `roof_membrane` and `wood_clapboard` still bind the albedo cap, and one material family is stated per facade class where the block carries several brick colours (J66) | material |
| 28 mm level rather than 60 mm tilted | a level axis is the only way two frames can be compared on proportion, and 28 mm is the longest normal lens containing the subject; both are on the sheet | stated choice |
| most of the props in range, and part of the kit, unplaced | triangle budgets 1,262,772 and 1,262,193, declared on the sheet | performance |
| 8 point props with no asset | misc structures, drinking fountains, a parks building and a payphone have no modelled asset; they stay unplaced rather than become the wrong object (J22, J23) | geometry |
| 141 of 221 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| pedestrians and vehicles dropped in their hundreds | the placement rules — not in the carriageway, on a walkable surface, within the triangle budget — each declared in the record | performance + stated choice |
