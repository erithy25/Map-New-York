# Lower Manhattan drive-through: Stone Street

`drive_lower_manhattan_stone_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Financial District Manhattan April 2022 008.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-19 13:45:47, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District_Manhattan_April_2022_008.jpg)

**Camera** — 40.70410, -74.01070 (NYC_TM -5133, 465) at z 4.0 m NAVD88 | azimuth 60.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 20.2 m from the item's recorded viewpoint — and was then **moved 7.2 m onto the nearest sidewalk**, because the recorded viewpoint is boxed in: the view azimuth is closed off 11 m ahead, less than the 12 m the frame needs. From the new point the view is clear for 60 m, the nearest built thing in frame is `t_-6_0_red_brick` 11.2 m away, and no simulated agent stands within 20 m.

**Sun** — azimuth 204.4°, elevation 58.6° at 2022-04-19T13:45:47−04:00, from the photograph's own **EXIF DateTimeOriginal**; 915.1 W/m² direct normal, sky at strength 0.0311, Filmic, +0.00 stops. That date is a **Tuesday** and the crowd was drawn for **a weekday**.

**In the scene**, within 740.2 m of the camera and not all of it in frame — 6/6 building tiles (86,646 tris), 12 landmark models of which **2 can fall inside the 54.4° frame** (Pier 17 at 789.2 m and the Brooklyn Bridge at 1,227.8 m), 23,768 pavement polygons (8,502 white marking, 5,392 roadbed, 4,263 sidewalk, 3,443 curb, 987 plaza, 563 crosswalk, 393 median, 212 yellow marking, 13 parking lot), 669 props of the 1,281 in range, 6,193 kit pieces, 89 vehicles and 380 people; 4,500,143 triangles. Ground mesh 88,180 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict

**The render is right about Stone Street and the two halves are not pointed the same way, and on this sheet the difference is almost entirely one of pitch.** The photograph is tilted up: its upper third is a bright white overcast sky, and its 95th percentile is **1.0** — blown, exactly. The render's optical axis is **level**, because the item names no subject to aim at, so its upper third is brick. That single difference carries most of the luminance and nearly all of the contrast gap between them.

**What the render does show is Stone Street.** A narrow pedestrian alley of red brick and brownstone party walls, a continuous run of green awnings over shopfronts on both sides, café light strings under them, a hydrant at the wall, and people standing in the middle of a carriageway that has no traffic on it. That is what this block is: a restaurant alley in the Financial District, and the frame reads as one.

## What matches

* **The street type is exact.** Four- to six-storey party-wall brick and brownstone, no setback, a shopfront at every ground-floor bay, awnings the full length of both sides, and a paved surface with no lane markings on it. **283 storefront and 50 storefront-interior pieces** stand in the scene out of 6,193, with 5,528 windows, 105 window accessories, 65 entry doors, 33 parapets, 24 cornices and 24 pilasters.
* **The clock is the photograph's own.** The Sun is placed from EXIF `DateTimeOriginal` — 19 April 2022 at 13:45:47, a Tuesday, elevation 58.6°, 915.1 W/m² direct normal — so nothing about the light on this sheet is assumed.
* **The camera stands where the photograph was taken**, to within 20.2 m of the item's viewpoint and 7.2 m of walking to get a frame that is not a wall.
* **987 plaza polygons** are in range: Stone Street's pedestrianised surface and the Financial District's public spaces are in the pavement data as their own kind, not as roadbed.
* **The street furniture is dense and it is the right furniture** — 94 benches, 85 manholes, 81 street lamps, 77 rooftop cooling towers, 61 hydrants, 35 subway vent grates, 32 waste baskets, 25 bike racks, 11 flagpoles, 4 newsstands, 3 subway entrances, 2 LinkNYC kiosks and 2 Citi Bike docks.
* **The crowd is the simulation's own and it is dense**: 380 people at 13:45 on a weekday, 1 at LOD0, 13 at LOD1 and 367 at LOD2, drawn from all **36** baked bodies with none folded onto another (J62).
* Nothing was dropped for being missing: 6 of 6 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The photograph is aimed up and the render is level.** The reference's upper third is blown white sky at a 95th percentile of exactly **1.0**; the render's is brick, at **0.1897**. Comparing the two frames' means compares a picture of sky with a picture of a wall.
* **The frame is the flattest in the set**: standard deviation **0.0652** against **0.3019**, a ratio of **0.216**, and mean **0.1145** against **0.4021** (**0.285×**). Part of that is the pitch above; part is that a 6 m alley between six-storey walls sees very little sky, which is a true fact about Stone Street and not a fault. But nothing in this frame is *lit*, and at a 58.6° Sun something should be.
* **The chroma gap is smaller here than elsewhere and still real**: **0.0174** against **0.0469**, a ratio of **0.371**. The photograph itself is a low-chroma picture — grey overcast on brown brick — which is why the ratio flatters this sheet relative to the others. Three surfaces sit at the albedo cap with the wrong source material behind them (`concrete`, `roof_membrane`, `wood_clapboard`, J66).
* **The facades are plainer than the photograph's.** The reference carries iron balconies, arched window heads, a stone pediment over a doorway, wall-mounted lanterns and hanging signs. The render has 5,528 windows and **2 quoins, 6 fire escapes and 11 string courses** across the whole scene; the classifier has no source for an individual building's ironwork or door surround.
* **No awning text or shop name is legible**, and the photograph carries three — a bar sign, two branded event canopies.
* **647 pedestrians and 213 vehicles were dropped for the triangle budget**, and of the 1,281 props in range only **669** were placed (cap 1,237,192), along with part of the kit (cap 1,212,714) and 9 opaque impostor cards. A further 517 pedestrians were dropped for standing in the carriageway without crossing.
* **145 trees stand within 270.2 m and 98 of them are species-substituted**; 144 are drawn at the height their own rows record, at a mean scale of **0.871**, and one fell outside the declared scale band and keeps its asset's own size (J70).
* **6 point props have no asset at all**: 3 memorials, 2 artworks and 1 vending machine (J22, J23).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the photograph is aimed up and the render is level | the item names no subject to aim at, so the optical axis is level; the reference is tilted up and its upper third is blown white sky at a 95th percentile of 1.0 | reference + stated choice |
| standard deviation 0.216× and mean 0.285× | the pitch above, plus a 6 m alley between six-storey walls that genuinely sees little sky, plus a renderer that never stops down | reference + stated choice |
| chroma 0.371× | `concrete`, `roof_membrane` and `wood_clapboard` sit at the albedo cap with the wrong source material behind them (J66) | material |
| plainer facades than the reference | 2 quoins, 6 fire escapes and 11 string courses across 6,193 kit pieces; the classifier has no source for an individual building's ironwork, balconies or door surrounds | geometry |
| no legible awning or shop sign | shopfront signage carries real business names as data but nothing resolves them to geometry at this distance (B15a) | geometry |
| 647 people, 213 vehicles and part of the props and kit dropped | triangle budgets 1,237,192 and 1,212,714, declared on the sheet | performance |
| 98 of 145 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| one tree outside the scale band | its measured height is further from the nearest exported size than the declared band allows, so it keeps the asset's own size and is counted (J70) | data |
| 6 point props unplaced | memorials, artworks and vending machines have no asset (J22, J23) | geometry |
