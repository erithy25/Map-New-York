# Queens residential block: Forest Hills Gardens

`drive_queens_forest_hills` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Homes in Forest Hills Gardens 05.jpg by XanderAi, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-09-26 16:04:15, 1920x1081. [Commons page](https://commons.wikimedia.org/wiki/File:Homes_in_Forest_Hills_Gardens_05.jpg)

**Camera** — 40.71761, -73.84488 (NYC_TM 8882, 1961) at z 23.4 m NAVD88 | azimuth 140.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x720. The camera stands on **this photograph's own EXIF GPS**, 221.9 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 24.0 m, the nearest built thing in the frame is `prop_tree_honeylocust_medium_0` 10.4 m away and the nearest simulated agent is `agent_ped_87.8` 15.7 m away.

**Sun** — azimuth 239.6°, elevation 28.3° at 2024-09-26T16:04:15−04:00, from the photograph's own **EXIF DateTimeOriginal**; 754.0 W/m² direct normal, sky at strength 0.0365, Filmic, **+0.61 stops**. That date is a **Thursday** and the crowd was drawn for **a weekday**.

**In the scene**, within 900.0 m of the camera and not all of it in frame — 6/6 building tiles (321,776 tris), 0 landmark models, 27,707 pavement polygons (12,707 white marking, 4,666 roadbed, 4,562 sidewalk, 3,619 curb, 801 crosswalk, 784 yellow marking, 459 median, 106 parking lot, 3 plaza), 428 props of the 2,161 in range, 4,911 kit pieces, 65 vehicles and 407 people; 4,500,101 triangles. Ground mesh 96,800 triangles, 0 holes. 14 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the brightness matches and the colour does not, and that separates two faults that usually hide each other

**This is the closest luminance match in the set: mean 0.3508 against the photograph's 0.3791, a ratio of 0.925, with the tonal spread at 0.768.** The clock is the photograph's own EXIF `DateTimeOriginal`, the camera stands on its EXIF GPS, and the exposure opened +0.61 stops for a 28.3° late-afternoon Sun. Nothing about the light on this sheet is assumed.

**Which is why its chroma reading is the most damning in the set: 0.0302 against 0.1191, a ratio of 0.254.** On every other sheet the colour gap can be argued down to exposure — a camera stops down, this renderer never does. Here the brightness already agrees to within eight per cent, so exposure explains nothing. **The render simply has a quarter of the colour of the street it stands for.**

**Look at the two halves and the cause is not subtle.** The photograph is a Forest Hills Gardens house in variegated clinker brick — orange, red, purple and tan in the same wall — under a **terracotta tile roof**, with half-timbering, leaded casements in dark timber frames and a wrought-iron balcony. The render is a **grey stucco block with a grey pitched roof**. The classifier was right about what it is: the nearest houses carry `queens_tudor_1930` — *"Tudor Revival attached house, brick and stucco with half-timbering"*, pitched roof, casement windows — and the massing and roof pitch follow it. What does not follow is the polychrome brick and the tile, because the class declares `stucco` and `red_brick` as its two materials and **no source in this build records what an individual house is faced with**.

## What matches

* **The reference is genuinely of the item**, which is not true of every sheet in this set: an item asking for Forest Hills Gardens houses is shown a photograph titled *Homes in Forest Hills Gardens*.
* **The building type is right.** Two-storey attached and semi-detached houses with steeply pitched roofs, deep eaves and chimney stacks; **3,382 windows, 494 window accessories, 200 entry doors, 92 bulkheads, 75 cornices, 67 vegetation pieces and 51 fence pieces** stand in the scene out of 4,911. The classifier assigned `queens_tudor_1930` with a pitched roof to the houses nearest the camera, which is the right typology for this district.
* **The luminance and the contrast are the closest in the set** — mean **0.925×** and standard deviation **0.768×** — and the shadows fall the way a 28.3° Sun at 16:04 puts them: long, low and to the left, across the roadway and up the stucco.
* **The garages are garages.** Two of the buildings in the cone are detached back-yard garages on their houses' lots; each carries a single garage door and a borough-and-era-appropriate wall material, and neither is given windows.
* **The road is a road with real markings**: 4,666 roadbed, 3,619 curb and 4,562 sidewalk polygons, with **12,707 white and 784 yellow marking polygons** and 801 crosswalk polygons in range (J52).
* **The trees are at their measured height**: all 154 scaled, mean **0.895**, none outside the declared band (J70).
* Nothing was dropped for being missing: 6 of 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The colour, and it is the whole gap.** Chroma **0.0302** against **0.1191** — **0.254×**, the lowest ratio in the set — with the brightness already matching. The photograph's wall is four brick colours at once and its roof is terracotta; the render's is one stucco grey under a grey roof.
* **There is no tile roof in the frame and no half-timbering.** The class's own name says *"brick and stucco with half-timbering"* and its features list `dormers`; the kit places neither timbering nor a dormer here.
* **The two halves are at very different range.** The photograph is a close-up of one house from across a garden wall; the render is a street view with parked cars filling its lower half. The item names no subject and the photograph's direction was never derived from the image (confidence **medium**), so this is a property of the pairing.
* **Of the 2,161 props in range only 428 were placed**, the largest shortfall in the set, at a triangle budget of 1,313,553 — along with part of the kit (cap 1,356,184) and 22 opaque impostor cards.
* **347 pedestrians were dropped for standing in the carriageway without crossing**, 179 for not being on a walkable surface and 90 for the triangle budget; 188 vehicles went to the budget too. Only 6 of the 65 vehicles are at LOD1 and none at LOD0.
* **70 of the 154 trees are species-substituted.** They are drawn at the height their own rows record; the species they are drawn *as* is the nearest by size and taxon.
* **One surface still sits at the albedo cap** — `roof_membrane` (J66). `concrete` was moved to a scan that does not bind it and **this frame did not change at all** when it was, which is the sharpest evidence on this sheet that the colour gap is not a texture-level fault.
* **5 point props have no asset at all**: 4 vending machines and 1 memorial (J22, J23).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| chroma 0.254× with the brightness matching at 0.925× | the facade class declares two materials for the whole typology and no source records what an individual house is faced with; the photograph's wall is four brick colours at once under a terracotta roof | **material — the whole gap on this sheet, and exposure cannot be blamed for it** |
| no tile roof, no half-timbering, no dormer | the class names all three and the kit carries none of them; the shell takes the class's roof *pitch* and its material list, not its ornament | geometry |
| the two halves are at different range | the item names no subject and the photograph's direction was never derived from the image (confidence medium) | reference |
| 428 of 2,161 props placed | triangle budget 1,313,553, declared on the sheet; this is the largest prop shortfall in the set | performance |
| 347 people dropped in the carriageway, 188 vehicles to the budget | the pedestrian rule refuses to stand a person in a live carriageway unless crossing, and the vehicle budget capped at LOD2 | performance |
| 70 of 154 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| 5 point props unplaced | vending machines and memorials have no asset (J22, J23) | geometry |

---

*Re-checked against the v15 render of 2026-09-08T22:33:45Z. This sheet names no subject, so nothing J74, J75 or J76 changed reaches it: the scene is identical to the render this was written against — the same 428 props of 2,161, 4,911 kit pieces, 65 vehicles and 407 people, the same 154 trees at a mean scale of 0.895 with none outside the band, and the same frame statistics to four decimals. What did change is that the statistics are now measured by the render that made the sheet rather than by hand afterwards (J77).*

*This sheet carries the measurement J66's second amendment rests on and it is unchanged here: the frame matches the photograph on brightness — mean **0.3508** against **0.3791**, a ratio of **0.925** — while carrying **0.254** of its colour, chroma **0.0302** against **0.1191**. When a frame is within eight per cent of the photograph's luminance and holds a quarter of its colour, no amount of stopping down accounts for the difference, and only `roof_membrane` still binds the albedo cap on this sheet. What is left is that one material family is stated per facade class while a Forest Hills Gardens wall carries four brick colours at once — and for nineteen buildings in twenty there is no source that would say which, which is counted in docs/DEVIATIONS.md J66 rather than here.*
