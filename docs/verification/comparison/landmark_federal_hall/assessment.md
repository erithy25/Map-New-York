# Federal Hall National Memorial

`landmark_federal_hall` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Financial District, New York, NY, USA - panoramio - Sergei Gussev (34).jpg by Sergei Gussev, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0), taken 2016 — **the year and nothing finer** — 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Financial_District,_New_York,_NY,_USA_-_panoramio_-_Sergei_Gussev_(34).jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the Doric portico straight on: eight fluted columns, the entablature and pediment above them, the Washington statue on its plinth, three red *THIS PLACE MATTERS* banners hung between the columns, the steps full of about forty people, and a steam stack venting at the left.

**Camera** — 40.706864, -74.010237 (NYC_TM -5093, 759) at z 8.8 m NAVD88 | azimuth 355.0°, pitch +0.4° | 25 mm on 36 mm (71.6° horizontal, 57° vertical, landscape) | 1208x906. The camera stands on **the item's recorded viewpoint**, because *this photograph's own EXIF GPS is 20 m away, but the eye point there is inside `t_-6_0_roof_membrane`* — a joined roof-membrane tile mesh swallowing a Wall Street sidewalk (J94), the fourth sheet written so far with that fault. The recorded azimuth agrees with the bearing to the subject to **0.1°**. The walk then **moved it 5.8 m** onto the nearest surveyed sidewalk polygon, the recorded viewpoint being boxed in at **12 m** against the **20.0 m** the frame needs. From there the view is clear for **20.4 m** — a margin of four tenths of a metre — the nearest built thing is `t_-6_0_glass_curtain` **14.7 m** away, and the note records a boro taxi **3.8 m** from the lens, which the cull over the observer then removed. The ground reads 7.165 m NAVD88, the 10th percentile of 113 samples within 12 m, range 7.05 to 7.73 m.

**Sun** — azimuth 284.1°, elevation 20.2° at 2016-06-21T18:30:00−04:00. The instant is **chosen, not measured** (J80): a year-only photograph, 21 June assumed, 18:30 picked as the hour putting the Sun above 20° whose bearing comes closest to the view azimuth — and closest here is **71° off**, because the view looks north and the solstice Sun never passes north of 58°. 655.4 W/m² direct normal, Filmic, **+6.00 stops** — **clamped** from a wanted **7.59**, with the record's standing note that a scene this far from a photographable level is not developed into a picture of one. The physical rule would have given **1.11 stops**.

**In the scene** — 4,500,082 triangles: 4 building tiles (106,490 tris, 0 missing, 0 LOD-substituted), 11 landmark models of which 5 can fall inside the 71.6° frame, 21,345 pavement polygons, 1,199 props, 4,693 kit pieces, 19 park-ground meshes, 43,576 triangles of structures over 3 tiles, 61 vehicles and 375 people.

## Verdict — the sheet J80 named as the darkest frame in the set now renders, and its Doric colonnade is there

**This sheet used to have no sheet.** J80 records it by name: *`landmark_federal_hall` at mean **0.021**, the darkest frame in the set* — rejected by the luminance gate, no PNG published. It now renders at mean **0.283** with `usable: true` and no retry needed, which is a thirteen-fold change in the same light, at the same chosen instant, from the same recorded viewpoint. The difference is the walk: J79 made it score candidates on the **subject's own sightline** rather than on eye-level clearance, and from 5.8 m away on the nearest sidewalk polygon it found a point with 20.4 m of clear view where the recorded viewpoint had 12 m. One entry's own worked example is now closed by another entry's fix, and that is worth recording plainly.

**The colonnade is modelled.** The render shows eight fluted Doric columns with capitals under a plain entablature, the shafts correctly spaced, the steps rising to them at the left, and the dark recessed doorway behind. Against it the photograph has the same order with a pediment above and the Washington statue in front. Of the landmark models written up so far this is the third to carry a real architectural order — after St John the Divine's arcade and St Patrick's buttressed flank — and the best-resolved of the three.

**The measurements are close.** **43 of 43** probe rays found fabric, measuring **20.25 m** above a ground of 7.59 m against the catalogue's **19.3 m** for `federal_hall`, whose origin stands **12.6 m** from the coordinate. The plan extent is **59.2 m by 53.5 m**.

**The frame is still dark, and honestly so.** Even after the +6.00-stop clamp the render's own median sits **1.302 stops below** the grey convention, against the photograph's **0.385 below** — a **−0.917-stop** difference, and the ratios follow: mean **0.683**, p50 **0.736**, sd **0.603**, with a 95th percentile of **0.4824** against **0.9791**. Nothing in the render is bright. Wall Street at 18:30 looking north on the solstice is a canyon with the Sun 71° off the view axis, which is the best a north-facing street can do (J80), and the clamp refused to invent more.

**Three of thirteen rays reach the subject.** The visible fraction is **0.231**, and the other ten stop at **12.2 m** on `prop_lamp_cobra_davit_2` — one cobra-head lamp on a 20 m-wide sidewalk, again.

## Measured for this assessment

| figure | how |
|---|---|
| mean 0.021 before, mean 0.283 now | the earlier figure is quoted from DEVIATIONS J80, which names this sheet as the darkest frame in the set; the current one is this record's own `frame.mean`, with `usable: true` and `frame_retry: null` |

## What matches

* **The Doric order.** Eight fluted columns with capitals under an entablature, correctly spaced, with the steps at their foot.
* **The height** — 20.25 m on **43 of 43** rays against a catalogued 19.3 m from an origin 12.6 m away.
* **The aim** — the recorded azimuth agrees with the measured bearing to **0.1°**.
* **The frame is usable where it was not.** mean **0.283**, sd **0.1354**, `usable: true`, no retry — against the **0.021** J80 recorded.
* **The refusal to stand on the photograph's GPS was right**, that point being inside a joined roof-membrane mesh (J65, J94).
* **The Financial District is furnished** — **27 subway entrances**, 272 Citi Bike stations in the source rows, 107 cooling towers, 98 station-status rows, 83 hydrants, 34 railroad structures, 32 street trees, 11 bus routes, 8 newsstands.
* **43,576 triangles of structures** over 3 tiles, on a block sitting over the Broad Street and Wall Street stations.
* **21,345 pavement polygons and none dropped**, including **580 plaza** and 439 crosswalk.

## What does not match

* **No pediment, no tympanum, no Washington statue, no banners.** The statue is an artwork, and no printed copy is invented anywhere (B5, B15a).
* **The steps are bare** where the photograph has forty people sitting on them; **375 people** are in the scene and none of them is there.
* **Published at the +6.00-stop clamp** from a wanted 7.59, and still **1.302 stops** below the grey convention (J83).
* **The instant is chosen, not measured, and 71° off the view axis** — the worst any chosen instant achieves in the pass, because the view faces north (J80). The luminance comparison here is not evidence about the render.
* **Three of thirteen rays reach the subject**, the rest stopped by one cobra-head lamp at 12.2 m.
* **A clearance margin of 0.4 m** — 20.4 m of clear view against a 20.0 m requirement, the tightest in the pass.
* **Props were capped to under half** — **1,199 placed of 2,660 in range** at a **1,165,725-triangle** budget, **1,268 dropped for budget**, **1,167** of them tree rows, and only **3 trees** are drawn from modelled branches against 174 impostor cards; 11 were dropped on a suppressed building.
* **Kit was capped to one piece in seven** — **4,693 of 31,870 in range** at a **1,082,432-triangle** budget, with **117** suppressed under landmark shells; the openings are drawn rather than cut (Stage 34 / J51).
* **One of four structure tiles has no file.**
* **There is no park ground within 150 m to check** — **0 samples**.
* **3,340 agents were dropped** — 703 pedestrians at the agent triangle budget, **293 in the carriageway without crossing**, 171 vehicles at the budget, **135 where the planimetric data has no sidewalk** (J101), 22 cyclists the fleet exports without a rider, 4 vehicles where there is no roadway.
* **Three quarters of the photograph's colour** — chroma **0.742** — and **0.603** of its contrast.
* **No cloud, and no steam.** The reference's steam stack vents across the left third of the frame; a venting stack is modelled as geometry here and not as vapour.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no pediment, statue or banners | the pediment's tympanum is above the frame at 25 mm; the Washington statue is an artwork, an unmapped prop kind; and no printed copy is invented anywhere (B5, B15a) | geometry + data + declared decision |
| the steps are bare | the crowd's placement test reads the road network's sidewalk, median, plaza and crosswalk, and a flight of steps is none of them (J101) | verification — open (J101) |
| published at the clamp, 1.302 stops under | Wall Street looking north at 18:30 on the solstice, with the Sun 71° off the view axis because it never passes north of 58°; the clamp refused to lift further (J80, J83) | verification — declared, and correct |
| three of thirteen rays reach the subject | one rule-placed cobra-head lamp at 12.2 m on a narrow sidewalk (J56, J79) | verification + data |
| a 0.4 m clearance margin | the recorded viewpoint was boxed in at 12 m and the nearest sidewalk polygon with a clear frame was 5.8 m away; there was nothing better (J79) | verification — the best available |
| the photograph's GPS is inside a roof | one tile's roof-membrane surfaces are joined into a single object whose extent covers a Wall Street sidewalk (J94) | **geometry — open, the join is the fault** |
| 1,199 props of 2,660, 1,167 tree rows dropped | the props triangle budget at 1,165,725 | performance |
| 4,693 kit pieces of 31,870 | the kit triangle budget at 1,082,432 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| one of four structure tiles without a file | that tile is unbuilt | data — open |
| no steam | a venting stack is modelled as geometry, and vapour is not a class this build carries | geometry |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
