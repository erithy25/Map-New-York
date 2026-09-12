# New York Stock Exchange

`landmark_nyse` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:New York Stock Exchange August 2017 02.jpg by Arild Vågen, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017 — **the year only**, 1920x1282. [Commons page](https://commons.wikimedia.org/wiki/File:New_York_Stock_Exchange_August_2017_02.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.707158, -74.010533 (NYC_TM -5119, 790) at z 8.2 m NAVD88 | azimuth 243.1°, pitch +1.2° | 18 mm on 36 mm (90.0° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, only 13.0 m from the item's recorded viewpoint — and it still had to move, because **the recorded viewpoint is inside a building**: a ray straight up from the eye point hits the roof of `lm_federal_hall.3`. The camera was moved **7 m** onto the nearest surveyed roadbed polygon. From there the view is clear for 37 m, nothing built stands within 20 m of the lens, and the nearest simulated agent is `agent_ped_2576.0` **17.0 m** away at 45° off axis. The lens was widened to the **18 mm floor** and the subject's top is still cut off at **31° above the horizon**; the record declares the verticals converge and the frame is not comparable on proportion.

**Sun** — azimuth 253.3°, elevation 53.8° at 2017-06-21T15:30:00−04:00. **This instant is chosen, not measured**, and the record says exactly how: the photograph carries only a year, 21 June is assumed, and *"of the hours that put the Sun above 20 deg it is the one whose bearing (253 deg) comes closest to the view azimuth (252 deg), 2 deg off, so the Sun is behind the camera and lights what it looks at"* (J80). 901.3 W/m² direct normal, sky at strength 0.0316, Filmic, **+5.40 stops**, marked **under-lit**. The linear median is **0.004264**. The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,068 triangles: 4 building tiles (106,490 tris), 10 landmark models of which 3 fall inside the 90.0° frame, 20,944 pavement polygons, 2,259 props, 4,972 kit pieces, 19 park-ground meshes with **53,345 faces cut for landmark ground**, 43,576 triangles of structures, 84 vehicles and 251 people.

## Verdict — the worst colour agreement in the pass, and the cause is exactly what the photograph is full of; the viewpoint is inside Federal Hall, the second such coordinate found

**Chroma **0.0305** against **0.1485**, a ratio of **0.205**.** The render holds a fifth of the photograph's colour, the largest such gap measured in this pass, and it is not a materials failure so much as a content one. The reference is full of things this build does not carry: three enormous American flags draped down the Exchange's front, a blue entrance awning, yellow and white vendor umbrellas, a dense summer crowd in coloured clothing, and the bronze George Washington in the near right. **The render is limestone, asphalt and shadow.**

**The recorded viewpoint is inside Federal Hall.** A ray cast straight up from the eye point strikes the roof of `lm_federal_hall.3`, so the walk moved the camera **7 m** onto a surveyed roadbed. This is the second sheet in the pass whose stored viewpoint is inside a building — One World Trade Center's is the other, and there the recovery needed 166 m. Here the photograph's own GPS is only 13.0 m from that coordinate, so the photographer was standing on Federal Hall's steps; the item's coordinate put the eye *in* them.

**The height difference is a naming difference, not an error.** The probe casts **43 rays, all 43 on built fabric**, measuring **42.4 m** above a ground of 5.5 m on an object **57.7 m by 55.7 m** in plan. The catalogue's figure for `nyse`, whose origin sits **15.0 m** away, is **104.8 m** — the whole complex including the 23-storey annex behind. The item names *11 Broad Street*, the 1903 portico block, and 42.4 m is that block. The same distinction appears on the Grand Central facade sheet; unlike that one, here the probe landed on the right piece.

**The sun was placed to light the frame and the canyon swallowed it anyway.** The chosen instant puts a 53.8° June sun **2° off the view axis, behind the camera** — the best light a chooser can pick — and the scene still metered **+5.40 stops** below middle grey. That is Broad Street: two hundred feet of masonry on both sides of a fifty-foot street.

## What matches

* **The Exchange is in the frame** at **56.1 m**, 17.2° off axis, with its colonnade and entablature reading as a classical front, and it is one of 3 landmarks inside the 90° cone — with **One Wall Street** at **104.3 m** and the **Charging Bull** at **299.2 m**, both of which belong on this view.
* **The sightline is strong and honest.** 13 rays, **11 clear**, **11 on the subject**, fraction **0.846**; the two blocked stop at **24.8 m** on a cobra-head lamp, and 4 of the hits are on the building's own nearer fabric.
* **Federal Hall's own columns are in the frame** on the right, where the photograph has them filling its right edge.
* **The instant's reasoning is written down.** A photograph dated by year alone cannot supply an instant, and the record refuses to pretend otherwise: it names the assumption (21 June), the rule (the Sun above 20° whose bearing is closest to the view azimuth), the result (253° against 252°, 2° off) and the purpose (the Sun behind the camera).
* **The camera stands on the traffic surface.** Ground 6.617 m NAVD88 from the **10th percentile of 113 samples within 12 m**, range 6.52 to 9.24 m — a 2.7 m spread across twelve metres, which is why the percentile rule exists here.
* **The near ground is clean.** Within 150 m the under-fraction is **0.0** over 99 samples, median clearance **0.18 m**.
* **The block is furnished as the Financial District is**: **32 subway entrances**, 54 vent grates, 130 street lamps, 123 manholes, 83 hydrants, 67 benches, 8 newsstands, and 229 Citi Bike dock units (Stage 40).
* **The fleet is a weekday Financial District fleet**: **45 sedans, 13 SUVs, 13 yellow taxis, 8 boro taxis**, 2 black cars, 2 vans and an MTA bus, with the crowd clock reporting **a weekday** for the assumed 2017-06-21, which was a Wednesday.
* **Two people are at LOD0.**

## What does not match

* **The flags are absent, and they are the photograph's subject as much as the building is.** Five flagpole props stand in the scene; draped facade flags are not a class this build carries.
* **The crowd is absent from the plaza.** The photograph's forecourt is packed; the render's is empty. **877 pedestrians were dropped at the agent triangle budget**, 1,362 for being outside the radius, 360 for standing in the carriageway without crossing, 127 for not being on a walkable surface and **22 for being inside buildings**.
* **The George Washington statue is not there.** **12 artwork and 7 memorial** props were wanted in range and had no asset — the largest artwork shortfall in the pass, on the block that has the most of it.
* **No pediment sculpture, no awning, no vendor umbrellas.** 4,733 of 4,972 kit pieces are windows, against **11 cornices, 11 string courses, 10 pilasters and 1 quoin**; kit was capped by a **1,335,184-triangle** budget with **26,462 pieces in range**.
* **A brighter midtone.** Median **0.4994** against **0.3556** (**1.404×**), mean **0.5671** against **0.4300** (**1.319×**). The photograph sits **0.793 stops** below the grey convention and the render **0.246** above it, a **1.039-stop** difference (J83).
* **Contrast is close** — standard deviation **0.2275** against **0.2435** (**0.934×**) — which makes the colour gap the whole of the visual difference.
* **The trees near the lens are cards.** **7** are drawn from modelled branches within 120 m against **1,337** impostor cards out to 514 m, with **29 instances scaled out of band** and 1,057 species substituted.
* **The instant is assumed on the calendar as well as the clock.** 21 June is a choice; the photograph could be any day of 2017, and a June sun at 53.8° is the highest the year offers.
* **1 of the 4 tiles in range has no structures file.**
* **21 riderless bodies were dropped** — bicycles, e-bikes and pedicabs the fleet exports without a rider.
* **83 of 84 vehicles and 198 of 251 people are at LOD2.**

## Cause of each gap

| gap | cause | class |
|---|---|---|
| chroma 0.205, the worst in the pass | the photograph is full of classes this build does not carry — draped flags, an awning, vendor umbrellas, a dense coloured crowd, a bronze statue — and the render is limestone and asphalt | **geometry + data — open** |
| the recorded viewpoint is inside Federal Hall | the stored coordinate places the eye under `lm_federal_hall.3`'s roof; the walk recovered by moving 7 m to a surveyed roadbed. Second such coordinate in the pass | **verification — open, the item's coordinate** |
| no flags, no pediment sculpture, no awning | none is a class this build models; kit capped at 1,335,184 triangles with 26,462 pieces in range | geometry + performance |
| no Washington statue | 12 artwork and 7 memorial props had no asset | data |
| the plaza is empty where the photograph's is packed | 877 pedestrians dropped at the agent triangle budget and the placement rules took the rest, each with its count | performance + verification |
| the frame needed +5.40 stops even with the Sun placed behind the camera | Broad Street is a deep masonry canyon; the choice put the Sun 2° off the view axis and the geometry still leaves the frame in shade. Published under-lit and marked so (J80, J83) | reference + verification — declared |
| p50 1.404× | the photograph is developed 0.793 stops under the grey convention and the render 0.246 over it (J83) | reference |
| the instant and the date are both assumed | the photograph carries a year and nothing else; the rule names its assumption rather than inventing an EXIF timestamp (J80) | reference — no source exists |
| 7 modelled trees against 1,337 cards, 29 scaled out of band | the props triangle budget and the scale band the placement rule applies | performance + data |
| 21 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
