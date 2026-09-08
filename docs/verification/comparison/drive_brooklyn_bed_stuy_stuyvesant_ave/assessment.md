# Brooklyn brownstone block: Bed-Stuy, Stuyvesant Avenue

`drive_brooklyn_bed_stuy_stuyvesant_ave` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Decatur Stuyvesant Heights HD 2.JPG by Smallbones, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), 2013, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Decatur_Stuyvesant_Heights_HD_2.JPG)

**Camera** — 40.68150, -73.93231 (NYC_TM 1496, -2054) at z 19.8 m NAVD88 | azimuth 351.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 46.3 m from the item's recorded viewpoint — the position the picture was taken from — and was **not moved**: the viewpoint is in open air on the ground, the nearest built thing in the frame is `prop_tree_ginkgo_large_2` 15.6 m away, and no simulated agent stands within 60 m of it.

**Sun** — azimuth 95.3°, elevation 43.5° at 2013-06-21T09:30−04:00; 860.2 W/m² direct normal, sky at strength 0.0328, Filmic, +0.00 stops. The photograph carries a **year only**, so 21 June 09:30 is assumed. That date is a **Friday** and the crowd was drawn for **a weekday**.

**In the scene**, within 766.3 m of the camera and not all of it in frame — 6/6 building tiles (670,572 tris), 0 landmark models, 19,150 pavement polygons (7,648 white marking, 192 yellow, 4,326 sidewalk, 3,340 roadbed, 2,895 curb, 451 crosswalk, 212 parking lot, 63 median, 23 plaza), 261 props of the 958 in range, 4,312 kit pieces, 89 vehicles and 301 people; 4,500,194 triangles. Ground mesh 89,888 triangles, 0 holes.

## Verdict

**This is the closest pairing in the set so far and the most useful one, because for once the two halves are of the same kind of thing from nearly the same place.** The camera stands where the photographer stood, to within the GPS fix, and both halves show a row of Bed-Stuy houses at eye level from across the street. The typology is right in detail — stoops, arched entries, areaway railings, window air-conditioners. **What the render cannot do is the thing the photograph is actually about: every house on that block is a different colour, and every house in the render is the same one.**

## What matches

* **The row typology is exact.** Four stoops with iron railings rise to arched doorways with panelled doors; rusticated brownstone at the base with visible coursing; segmental-arched window openings with projecting lintels; garden-level windows under the stoops; areaway fences at the pavement line. 275 entry doors, 2,794 windows, 337 window accessories, 180 cornices, 170 fire escapes, 129 bulkheads, 87 fence pieces and 57 quoins stand in the frame out of 4,312.
* **The window air-conditioners are there**, in several openings, and they are in the photograph too. That is the kind of detail that decides whether a street reads as New York.
* **The light is directional and the shadow is a real shadow.** A tree casts a hard dappled shadow across the pavement and out onto the carriageway; the facade above it takes grazing morning light from the east. Before the sun-to-sky ratio was corrected this frame had no shadow in it at all (docs/DEVIATIONS.md J67).
* **The camera was not moved.** The photograph's own GPS was usable, the clearance probe found 23.2 m of open air along the view azimuth, and the render stands where the picture was taken. That is the best case this pipeline has and it happened here.
* **The road is a road**: 3,340 roadbed, 2,895 curb and 4,326 sidewalk polygons carrying asphalt and concrete from their own material names, with the kerb reading by its reveal.
* Nothing was dropped for being missing: 6 of 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes, and **no prop kind unplaced**.

## What does not match

* **Every house is the same colour, and the photograph's subject is that they are not.** The reference shows, left to right, deep terracotta, cream, plum-red brick and rust brick in four adjacent houses; the render's whole row is one brownstone. The facade classifier assigns one material family per block face and **no source in this build records the colour of an individual house**. This is the single largest gap on the sheet and it is a data gap, not a rendering one.
* **The chroma gap is the same fact measured**: **0.0241** against the photograph's **0.1381**, a ratio of **0.175** — the render carries under a fifth of the colour variation of the block it stands for. Part is the missing per-house colour; part is that `brownstone` is drawn with a travertine scan and `concrete`, `roof_membrane` and `wood_clapboard` sit at the albedo cap with the wrong source material behind them (docs/DEVIATIONS.md J66). 18 city surfaces are dressed in this frame.
* **The cornice is missing where the photograph's is the most conspicuous thing on the roofline.** 180 cornice pieces are in range; the roofline in frame is plain. The photograph's houses carry deep carved cornices with dentils and brackets.
* **The facades are flat where the photograph's are not.** Two-storey angled bay windows step out of the wall in the reference; the render's wall is planar.
* **The frame is much darker and much flatter**: mean **0.1466** against **0.3992** (**0.367×**), sd **0.1117** against **0.2993** (**0.373×**), 95th percentile **0.3277** against **0.9972**. **A large part of that is a difference of weather, not of rendering.** The photograph was taken under a bright overcast — its blown-out white sky is what puts its 95th percentile at 0.9972 — and the render assumes a clear sky at an assumed instant. The two frames are lit by different days.
* **No vehicle is in frame** although 89 are placed and all 89 are at LOD2. The photograph has four cars parked along the kerb, which is what that street looks like at any hour.
* **697 props in range were not placed** — triangle budget 1,245,811 — along with part of the kit (cap 1,364,135) and 17 opaque impostor cards.
* **168 trees stand within 296.3 m and 67 are species-substituted.**
* The Sun is on an assumed instant; the photograph carries a year and nothing finer.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| every house the same colour | the facade classifier assigns one material family per block face; no source in this build records an individual house's colour | **data — the largest gap on this sheet** |
| chroma 0.175× | the missing per-house colour, plus `brownstone` drawn from a travertine scan and three surfaces at the albedo cap with the wrong source material (J66) | material |
| no cornice on the roofline | 180 cornice pieces are in range but none is placed on the visible roofline; the kit's cornice is a generic profile and the classifier has no source for a carved one | geometry |
| flat facades where the reference has bays | the shell is extruded from a footprint; a two-storey angled bay is not in the footprint | geometry |
| mean 0.367×, 95th percentile 0.328 against 0.997 | the photograph was taken under a bright overcast and the render assumes a clear sky at an assumed instant — different days, not different renderers | reference |
| no vehicle in frame | placement is city-wide and the frame is not; none of the 89 falls inside this 54.4° cone | verification |
| 697 props and part of the kit dropped | triangle budgets 1,245,811 and 1,364,135, declared on the sheet | performance |
| 67 of 168 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| Sun on an assumed instant | the photograph carries a year and nothing finer | reference |
