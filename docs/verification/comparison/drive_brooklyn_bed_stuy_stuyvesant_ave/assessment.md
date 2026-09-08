# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Decatur Stuyvesant Heights HD 2.JPG by Smallbones, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), 2013, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Decatur_Stuyvesant_Heights_HD_2.JPG)

**Camera** — 40.68150, -73.93231 (NYC_TM 1496, -2054) at z 19.8 m NAVD88 | azimuth 351.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 46.3 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 23.2 m, the nearest built thing in the frame is `prop_tree_sophora_large_3` 14.9 m away, and no simulated agent stands within 60 m of it.

**Sun** — azimuth 95.3°, elevation 43.5° at 2013-06-21T09:30−04:00. The photograph carries a **year only**, so 21 June 09:30 is assumed. That date is a **Friday** and the crowd was drawn for **a weekday**.

**In the scene**, within 766.3 m of the camera and not all of it in frame — 6/6 building tiles (670,572 tris), 0 landmark models, 19,150 pavement polygons (7,648 white marking, 4,326 sidewalk, 3,340 roadbed, 2,895 curb, 451 crosswalk, 212 parking lot, 192 yellow marking, 63 median, 23 plaza), 318 props of the 958 in range, 4,274 kit pieces, 89 vehicles and 301 people; 4,500,248 triangles. Ground mesh 89,888 triangles, 0 holes. 18 city surfaces are dressed from the shared photographic catalogue.

## Verdict

**This is still the closest pairing in the set, and it is now also the clearest demonstration that the assumed instant is the weakest input on these sheets.** The camera stands where the photographer stood, to within the GPS fix, and both halves show a row of Bed-Stuy houses at eye level from across the street. The typology is right in detail — stoops, arched entries, areaway railings, window air-conditioners, garden-level windows.

**Nothing in the frame is in sunlight, and the record's own two numbers say why.** The camera looks along azimuth **351.4°**, so the facade filling the picture faces back at it — very nearly due south — while the Sun bears **95.3°** at **43.5°** elevation. A wall that far off the Sun's bearing takes it at grazing incidence and receives a small fraction of the **860 W/m²** direct normal the record publishes. A south-facing Bed-Stuy row house is edge-on to the Sun at 09:30 in late June and is lit in the afternoon. The instant is *assumed*, because the photograph carries a year and nothing finer, so this is a consequence of a stated choice and not of the renderer.

**The frame is darker than the last render of it, and that is more of the street rather than less.** The trees now stand at the height the census measured them (J70), which costs fewer triangles, so more of this block's trees fit the budget: **202** of them, at a mean scale of **0.937**. What the frame held before is in that entry rather than here. Their shadow covers more of the carriageway. What the sheet shows is a denser and more accurate canopy over a facade that was never going to be lit at this hour.

## What matches

* **The row typology is exact.** Four stoops with iron railings rise to arched doorways with panelled doors; rusticated brownstone at the base with visible coursing; segmental-arched window openings with projecting lintels; garden-level windows under the stoops; areaway fences at the pavement line. 2,734 windows, 339 window accessories, 284 entry doors, **181 cornices**, **170 fire escapes**, 131 bulkheads, 105 storefront pieces, 91 fence pieces, 61 parapets, 58 quoins and 47 string courses stand in the scene out of 4,274.
* **The window air-conditioners are there**, in several openings, and they are in the photograph too. That is the kind of detail that decides whether a street reads as New York.
* **The shadow is a real shadow.** A tree casts hard dappled shade across the pavement and out onto the carriageway. Before the sun-to-sky ratio was corrected this frame had no shadow in it at all (docs/DEVIATIONS.md J67).
* **The camera was not moved.** The photograph's own GPS was usable and the render stands where the picture was taken. That is the best case this pipeline has and it happened here.
* **The road is a road**: 3,340 roadbed, 2,895 curb and 4,326 sidewalk polygons carrying asphalt and concrete from their own material names, with the kerb reading by its reveal.
* **The crowd and the fleet are the simulation's own** — 301 people and 89 vehicles at 09:30 on a weekday. The fleet is 41 sedans, 20 SUVs, 9 yellow taxis, 6 black cars, 4 boro taxis, 4 box trucks, 3 MTA buses and 2 vans.
* Nothing was dropped for being missing: 6 of 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes, and **no prop kind unplaced**.

## What does not match

* **Every house is the same colour, and the photograph's subject is that they are not.** The reference shows, left to right, deep terracotta, cream, plum-red brick and rust brick in four adjacent houses; the render's whole row is one brownstone. The facade classifier assigns one material family per block face and **no source in this build records the colour of an individual house**. This is the single largest gap on the sheet and it is a data gap, not a rendering one.
* **The chroma gap is the same fact measured**: **0.0245** against the photograph's **0.1381**, a ratio of **0.177** — the render carries under a fifth of the colour variation of the block it stands for. Almost all of it is the missing per-house colour. `shellmat` varies a building's *tone* and never its *hue* — all three channels are scaled by one factor — so this row is one brownstone at four brightnesses where the photograph has four colours. Replacing two of the three capped textures moved this frame's statistics by nothing at all, and only `roof_membrane` and `wood_clapboard` still bind the cap (J66).
* **The frame is much darker and much flatter than the photograph**: mean **0.1267** against **0.3992** (**0.317×**), standard deviation **0.1** against **0.2993** (**0.334×**), 95th percentile **0.3092** against **0.9972**, 5th percentile **0.0249** against **0.0583**. Three things are in that and they should not be confused: the facade is at grazing incidence at the assumed instant; the photograph was taken under a bright overcast whose blown white sky is what puts its 95th percentile near 1; and a camera stops down where this renderer never does.
* **The cornice is missing where the photograph's is the most conspicuous thing on the roofline.** 181 cornice pieces are in the scene; the roofline in frame is plain. The photograph's houses carry deep carved cornices with dentils and brackets.
* **The facades are flat where the photograph's are not.** Two-storey angled bay windows step out of the wall in the reference; the render's wall is planar.
* **No vehicle is in frame** although 89 are placed and all 89 are at LOD2. The photograph has four cars parked along the kerb, which is what that street looks like at any hour.
* **Only 318 of the 958 props in range were placed** — triangle budget 1,245,811 — along with part of the kit (cap 1,370,215) and 23 opaque impostor cards.
* **202 trees stand within 296.3 m and 75 are species-substituted**, and **one tree fell outside the scale band** and is drawn at its asset's own size rather than its measured height; the record counts it (J70).
* The Sun is on an assumed instant; the photograph carries a year and nothing finer.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| every house the same colour | the facade classifier assigns one material family per block face; no source in this build records an individual house's colour | **data — the largest gap on this sheet** |
| chroma 0.177× | `shellmat` varies tone and not hue, so the row is one brownstone at four brightnesses; almost every building in the city takes its material from the class rule and no source records an individual house's colour — the counts are in J66 rather than here | **data — no source exists** |
| nothing in the frame is sunlit | the camera looks along 351.4° so the facade faces very nearly due south, and the Sun bears 95.3° at 43.5°: the wall is at grazing incidence to it. The instant is assumed because the photograph carries only a year | reference + stated choice |
| mean 0.317×, 95th percentile 0.309 against 0.997 | the grazing incidence above, a photograph taken under bright overcast with a blown white sky, and a camera's automatic exposure against a renderer that never stops down | reference + stated choice |
| no cornice on the roofline | 181 cornice pieces are in the scene but none is placed on the visible roofline; the kit's cornice is a generic profile and the classifier has no source for a carved one | geometry |
| flat facades where the reference has bays | the shell is extruded from a footprint; a two-storey angled bay is not in the footprint | geometry |
| no vehicle in frame | placement is city-wide and the frame is not; none of the 89 falls inside this 54.4° cone | verification |
| 318 of 958 props placed, and part of the kit | triangle budgets 1,245,811 and 1,370,215, declared on the sheet | performance |
| 75 of 202 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| one tree outside the scale band | its measured height is further from the nearest exported size than the declared band allows, so it keeps the asset's own size and is counted (J70) | data |
| Sun on an assumed instant | the photograph carries a year and nothing finer | reference |
