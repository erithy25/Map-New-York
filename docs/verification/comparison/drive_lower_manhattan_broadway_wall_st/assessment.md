# Lower Manhattan drive-through: Broadway at Wall Street

`drive_lower_manhattan_broadway_wall_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Wall Street sign & US Flag (May 2023).JPG by Benoît Prieur, CC0 (http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2023-05-21 13:00:40, 1920x1693. [Commons page](https://commons.wikimedia.org/wiki/File:Wall_Street_sign_%26_US_Flag_(May_2023).JPG)

**Camera** — 40.707828, -74.011658 (NYC_TM -5210, 871) at z 12.3 m NAVD88 | azimuth 200.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1112x980.

**Sun** — azimuth 185.4°, elevation 69.5° at 2023-05-21T13:00:40-04:00 (EXIF DateTimeOriginal); 937.5 W/m² direct normal, sky at strength 0.0305, Filmic, +1.34 stops.

**In the scene**, within 776.2 m of the camera and not all of it in frame — 4 building tiles (106,490 tris), 14 landmark models of which **5 can fall inside the 54.4° frame**, 28,368 pavement polygons (12,518 white, 5,222 sidewalk, 4,534 roadbed, 3,852 curb, 787 plaza, 755 crosswalk, 376 median, 290 yellow, 34 parking lot), 1018 props of the 6,174 in range, 3,279 kit pieces, 89 vehicles and 242 people; 4,500,137 triangles. Ground mesh 88,976 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the render is a street and the photograph is a street sign; the halves share a corner and nothing else

**This sheet does not compare a view with a view of the same thing.** The photograph is taken from the kerb at Broadway and Wall Street with the camera tilted steeply upward: it is filled by the black "Wall St" fingerpost with its 1-21 arrow, a United States flag on its pole, and behind them the upper storeys of a Beaux-Arts limestone facade with a rounded corner bay, balustraded string courses and a modillioned band, against a strip of blue sky at top left. There is no roadway, no kerb, no person and no vehicle in it. The render is a level 35 mm view along the carriageway at azimuth 200.0° from an eye 1.6 m above the street, and it contains nothing the photograph contains: no sign, no flag, no carved stone. The record says so in its own words — the item names no subject, the 200.0° is the street heading copied from `meta.json` and "not derived from the photo", and the halves "are not guaranteed to face the same way". They do not; the photograph faces up.

**What the record establishes is the position and the instant, and both are the photograph's own.** The camera stands on the photograph's EXIF GPS, **56.2 m** from the item's recorded viewpoint, and was not moved; the axis is clear for **59.3 m**, the nearest built thing is a coned manhole **6.8 m** away below the axis, and the nearest simulated pedestrian on the axis is **39.2 m** off. The Sun is placed from EXIF `DateTimeOriginal`, 21 May 2023 at 13:00:40, a Sunday, at elevation **69.5°** and azimuth **185.4°** — nearly overhead, a little right of the view. The crowd was drawn for a Sunday. None of that is assumed, and it is all the halves share.

**The reader must not read the frame statistics on this sheet as a measurement of the city.** The photograph's standard deviation, 95th percentile and chroma are a red-white-and-blue flag and sunlit limestone against a black sign; the render's are grey asphalt and a tan tower. A chroma ratio of **0.408** here is a flag against a road, not New York against its model. The fault is the open one under **DEVIATIONS I12**: the reference chooser establishes no view direction, so a photograph taken at the right corner but pointed at the sky passes as the reference for a drive along the street. All three photographs fetched for this item (`1.jpg`, `2.jpg`, `3.jpg`) are of that kind — a Wall Street sign, a Broadway sign, the tower of Trinity Church — each tilted up from the kerb, none along Broadway.

**Judged against the place, the render is a plausible Financial District canyon and a bare one.** Broadway runs to a vanishing point between slab towers; a lane line and a continental crosswalk lie on the asphalt; cobra-head lamps stand on both kerbs; green "SUBWAY" railings sit on both footways; a dark sedan waits at the crossing beside a cyclist; the right footway carries a crowd. But the left foreground tower is a grey grid of deep square openings, the towers beyond are flat tan slabs with pinprick windows, and one pedestrian stands mid-carriageway a few metres from the lens with no crossing under her feet.

## What matches

* **Position and instant.** Both halves are made at the same corner — the camera on the photograph's EXIF GPS, offset **0.0 m** by the clearance rule — and at the same second. The light on the photograph's limestone is high and hard; the render's shadows are short, as a 69.5° Sun gives.
* **The development convention.** The render is metered at **+1.34** stops (the physical rule alone would have given **+0.00**), placing a linear median of **0.071176** at middle grey; the photographer's exposure sits **0.225** stops from that convention and the render's **0.255**, a difference of **0.03** stops. The median pixels agree to **1.009** (0.5008 against 0.4961). Whatever else differs, the halves are developed alike.
* **The street section.** A wide carriageway, continuous towers with no setback, a narrow footway each side, the sky closed to a strip — Broadway below Wall Street. 4,534 roadbed, 3,852 curb, **12,518 white** and 290 yellow marking polygons are in range; a lane line and a continental crosswalk are drawn (J52).
* **The transit fabric.** **27 subway entrances**, 67 vent grates and 99 street lamps from their own rows; three entrances and a station sign are visible in the first block.
* **A Sunday crowd at one o'clock.** 242 people within 200 m and 89 vehicles within 320 m from the simulation's own snapshot, 12 of them yellow taxis and 10 boro taxis.
* **The landmark models are there and the record is honest about the cone.** 14 placed, **5** able to fall inside it — One Wall Street at **76.8 m** and 10.6° left of axis, the Stock Exchange at **97.4 m** and 42.0° off — with Trinity Church at **52.8 m**, Federal Hall and 40 Wall Street behind or aside. The photograph's facade is none of these; it is a tile shell.
* Nothing was dropped for want of data: 4 of 4 tiles, 0 LOD substitutions, 0 pavement polygons dropped, 0 holes.

## What does not match

* **The subject.** A street sign, a flag and six storeys of carved limestone seen from below, against a render that has none of them. The kit places **3 quoins, 12 cornices, 11 pilasters and 12 string courses** across 3,279 pieces, **3,010** of them windows; the balustrades, rounded bay and modillions have no source in the classifier and are not there.
* **Contrast and colour, which here measure the reference, not the city.** Standard deviation **0.1442** against **0.2729** (ratio **0.528**), 95th percentile **0.6735** against **0.8893**, chroma **0.0457** against **0.112** (**0.408**). The photograph's bright tail is the flag's white stripes and sunlit stone; its chroma is the flag and the sky. That the render's facades are one hue per class at several tones (J66) is true and visible in the flat tan slabs, but this pairing cannot measure it.
* **A pedestrian in the carriageway in the foreground.** The clearance probe found the nearest agent on the axis **39.2 m** away, and that is true — she is left of it. The snapshot dropped **242** pedestrians for standing in the carriageway without crossing and kept this one.
* **What the budgets removed.** **1018** of 6,174 props placed (triangle budget 1095576); **1,232** pedestrians and **69** vehicles dropped for theirs; the kit capped at 949929 triangles. 174 trees stand within 306.2 m and **163** are species-substituted (J70); 11 artworks, 9 memorials and 4 drinking fountains have no asset (J23); **57** scaffold pieces come from present-day permits against a photograph of May 2023.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the halves show different things: a sign and flag looked up at, against a level view along the street | the chooser matched the photograph to the place by GPS (56.2 m) and never to a view direction; all three photographs fetched for this item are tilted-up details from the kerb | reference — **DEVIATIONS I12** (open: "the chooser still establishes no view direction") |
| no carved limestone, balustrade or rounded bay | the facade is a tile shell extruded from a footprint; the classifier has no source for a Beaux-Arts corner | geometry |
| sd 0.528×, p95 0.6735 against 0.8893, chroma 0.408× | the photograph's bright and coloured pixels are a flag, sunlit stone and sky the render's frame does not contain; the ratios measure the reference, not the model | — (not a gap) |
| one hue per facade class in the tan slabs | `shellmat.shaded` varies tone and not hue, and nineteen buildings in twenty take their material from the class rule | material — **DEVIATIONS J66** (open, second half) |
| a pedestrian standing in the road a few metres from the lens | the carriageway filter dropped 242 of her kind and kept her; the clearance probe tests the axis only and she is off it | verification |
| 1018 of 6,174 props, 1,232 people and 69 vehicles dropped, kit capped | triangle budgets 1095576 and 949929 and the agent budget, declared on the sheet | performance |
| 163 of 174 trees species-substituted; artworks, memorials and fountains unplaced | no modelled species matched (J70); kinds with no asset stay empty rather than become the wrong object (J23) | data |
| 57 scaffold pieces against a 2023 photograph | sidewalk sheds come from current DOB permits, not the photograph's year | stated choice |
