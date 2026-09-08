# Lower Manhattan drive-through: Broadway at Wall Street

`drive_lower_manhattan_broadway_wall_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File by Benoît Prieur, CC0 (https://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2023-05-21 13:00:40, 1920x1693.

**Camera** — 40.70783, -74.01166 (NYC_TM -5210, 871) at z 12.3 m NAVD88 | azimuth 200.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1112x980. The camera stands on **this photograph's own EXIF GPS**, 56.2 m from the item's recorded viewpoint, and was **not moved**: the viewpoint is in open air on the ground, the view azimuth is clear for 59.3 m, the nearest built thing in the frame is `prop_manhole_coned_3` 6.8 m away, and the nearest simulated agent is 39.2 m away.

**Sun** — azimuth 185.4°, elevation 69.5° at 2023-05-21T13:00:40−04:00, from the photograph's own **EXIF DateTimeOriginal**. That date is a **Sunday** and the crowd was drawn for one.

**In the scene**, within 776.2 m of the camera and not all of it in frame — 4/4 building tiles (106,490 tris), 14 landmark models of which **5 can fall inside the 54.4° frame**, 28,368 pavement polygons (12,518 white marking, 5,222 sidewalk, 4,534 roadbed, 3,852 curb, 787 plaza, 755 crosswalk, 376 median, 290 yellow marking, 34 parking lot), 576 props of the 1,594 in range, 3,865 kit pieces, 89 vehicles and 242 people; 4,500,352 triangles. Ground mesh 88,976 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict

**This is the best-conditioned sheet in the set so far, and it is the only one whose clock and position are both the photograph's own.** The Sun is placed from the photograph's EXIF `DateTimeOriginal` — 21 May 2023 at 13:00:40, a Sunday, elevation 69.5° — and the camera stands on the photograph's own EXIF GPS without being moved. Nothing about the light or the viewpoint on this sheet is an assumption, which is what makes its numbers worth reading: mean **0.3059** against the photograph's **0.4896**, a ratio of **0.625**, the closest in the set.

**And what it shows is a Financial District canyon that reads as one.** Broadway runs to a vanishing point between towers, a lane line and a continental crosswalk lie on the carriageway, cobra-head lamps stand on both kerbs, two subway entrances carry legible **SUBWAY** signs, a car and a cyclist are mid-block, and a crowd of 242 fills both footways at midday on a Sunday.

## What matches

* **The street section is right.** A wide carriageway between continuous towers, no setback at street level, a narrow footway on each side, and the sky closed to a strip. That is Broadway below Wall Street.
* **The transit fabric is dense and correct**: **25 subway entrances**, 56 subway vent grates, 1 subway emergency exit, 12 bus-stop signs, 1 bus shelter and 2 newsstands. Lower Manhattan is the densest subway node in the city and the frame shows it.
* **The road surface is a road.** 4,534 roadbed and 3,852 curb polygons carry asphalt and concrete from their own material names; **12,518 white and 290 yellow marking polygons** are in range, and both a lane line and a continental crosswalk are drawn and legible (J52).
* **787 plaza polygons** are in range — the Financial District's privately owned public spaces are in the pavement data.
* **The crowd is the simulation's own and it is dense**: 242 people at 13:00 on a Sunday, 7 at LOD0, 38 at LOD1 and 197 at LOD2. The fleet is 37 sedans, 20 SUVs, 12 yellow taxis, **10 boro taxis**, 4 vans, 3 black cars, 2 box trucks and 1 MTA bus.
* **The landmark count is honest about what is in frame.** 14 models are in the scene and the record says **5** can fall inside the cone — One Wall Street at 76.8 m and 10.6° off axis, the New York Stock Exchange at 97.4 m, the Charging Bull at 297.3 m, and two more at over a kilometre — while Trinity Church, Federal Hall, 40 Wall Street, the Woolworth Building, One World Trade Center, City Hall and the Brooklyn Bridge stand behind or beside the camera (J61).
* **51 hydrants, 72 street lamps, 70 rooftop cooling towers, 41 benches and 18 waste baskets** are placed from their own sources.
* Nothing was dropped for being missing: 4 of 4 building tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes in the ground.

## What does not match

* **The frame carries about a third of the photograph's colour**: chroma **0.0382** against **0.1120**, a ratio of **0.341**. This is the gap that exposure cannot explain, and on this sheet exposure is not available as an excuse: the clock is the photograph's own and the Sun is at 69.5°. **This is the one frame in the set that the texture repair moved**, and by the amount a canyon of stone and concrete should move: `concrete` went from binding the albedo cap to a clean correction, and mean, chroma and both percentiles all rose. Two surfaces still bind it (`roof_membrane`, `wood_clapboard`, J66). What did not move is the far larger part — `shellmat` varies a building's tone and never its hue.
* **The frame is flatter than the photograph**: standard deviation **0.1161** against **0.2729**, a ratio of **0.425**, with a 95th percentile of **0.4947** against **0.8893**. The photograph has sunlit stone at the top of the canyon and the render's tower faces are dimmer than that.
* **The facades above the first few storeys are bare.** 3,564 windows are in the scene but only **4 window accessories, 15 cornices, 11 pilasters, 5 parapets and 3 quoins** — the Financial District's towers carry deep stone cornices, setback crowns, spandrel bands and rusticated bases, and the kit places almost none of that here. The classifier has no source that would tell it which tower is which.
* **1,232 pedestrians and 69 vehicles were dropped for the triangle budget**, and of the 1,594 props in range only **576** were placed (cap 1,176,089), along with part of the kit (cap 1,099,000) and 5 opaque impostor cards. A further 242 pedestrians were dropped for standing in the carriageway without crossing and 29 for being inside a building.
* **133 trees stand within 306.2 m and 127 of them — 95 % — are species-substituted.** They are drawn at the height their own rows record, at a mean scale of **0.974**, but almost none of them is the species the source names. One fell outside the declared scale band and keeps its asset's own size (J70).
* **16 point props have no asset at all**: 7 artworks, 7 memorials and 2 drinking fountains. Lower Manhattan is dense with both, and they stay unplaced rather than become the wrong object (J22, J23).
* **62 sidewalk-shed pieces are in the scene**, from DOB permits active on 2026-09-05, against a photograph from 2023.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| chroma 0.341× | partly the capped textures, and this is the one frame that shows it — a canyon of stone and concrete, where fixing `concrete` raised mean, chroma and both percentiles. The rest is that `shellmat` varies tone and never hue (J66) | material + data |
| standard deviation 0.425× and 95th percentile 0.495 against 0.889 | the render's tower faces are dimmer than the photograph's sunlit stone; a camera stops down on a bright canyon and this renderer never does | stated choice |
| bare tower facades above the first storeys | the kit places 4 window accessories, 15 cornices and 5 parapets across 3,865 pieces here; the classifier has no source naming a tower's cornice, crown or spandrel treatment | geometry |
| 1,232 people and 69 vehicles dropped, 576 of 1,594 props placed | triangle budgets 1,176,089 and 1,099,000, declared on the sheet | performance |
| 127 of 133 trees species-substituted | no modelled species matched exactly; the nearest by size and taxon was used | data |
| one tree outside the scale band | its measured height is further from the nearest exported size than the declared band allows, so it keeps the asset's own size and is counted (J70) | data |
| 16 point props unplaced | artworks, memorials and drinking fountains have no asset (J22, J23) | geometry |
| sidewalk sheds of the wrong year | the shed source is DOB permits active on 2026-09-05 and the photograph is from 2023 | reference |

---

*Re-checked against the v15 render of 2026-09-08T21:55:08Z. This sheet names no subject, so nothing J74, J75 or J76 changed reaches it: the scene is identical to the render this was written against — the same 28,368 pavement polygons, the same 576 props of 1,594, the same 3,865 kit pieces, 89 vehicles and 242 people, the same 133 trees at a mean scale of 0.974 with one outside the band, and the same frame statistics to four decimals. What did change is that the statistics are now measured by the render that made the sheet rather than by hand afterwards (J77); this sheet's file was one of the stale ones that found the fault, measuring the render of 20:18:42 beside a render from 21:55:08.*
