# Fifth Avenue at 42nd Street (NYPL), street view looking north

`fifth_ave_42nd_north` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:43rd St 5th Av td (2018-05-18) 21.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018 — **the year only**, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:43rd_St_5th_Av_td_(2018-05-18)_21.jpg) — the photograph's own view direction **was not** derived from the image; confidence is **medium**.

**Camera** — 40.754156, -73.980559 (NYC_TM -2581, 6014) at z 22.2 m NAVD88 | azimuth 29.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, **186.8 m** from the item's recorded viewpoint — inside the 250 m at which it can still be the same view, but only just — and was **not moved**; the view azimuth is clear for 150 m. The ground under it reads 20.603 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 20.51 to 21.12 m. The item names no subject, so the axis is level and the lens the default 35 mm, and the record directs the comparison to street width, storey height and material rather than composition. The nearest built thing in the frame is `prop_sign_mta_bus_stop_5` 17.4 m away and **the nearest simulated agent is `agent_ped_242.9` 4.6 m** from the lens at 9.1° off axis.

**Sun** — azimuth 85.5°, elevation 32.2° at 2018-06-21T08:30:00−04:00. **Chosen, not measured**: the photograph carries only a year, 21 June is assumed, and this is the hour whose bearing comes closest to the view azimuth — **85° against 29°, 56° off** (J80). 788.4 W/m² direct normal, Filmic, **+5.36 stops**, marked **under-lit**. The linear median is **0.004374**. The physical rule would have given **0.42 stops**.

**In the scene** — 4,500,059 triangles: 6 building tiles (339,572 tris), 13 landmark models of which **6 fall inside the 54.4° frame**, **36,632 pavement polygons**, 1,244 props, 3,601 kit pieces, 21 park-ground meshes, 54 vehicles and 250 people.

## Verdict — one hundred thousand kit pieces wanted and three and a half thousand drawn, which is why the shed, the signage and the shopfronts are all missing at once

**The number that explains this sheet is 100,664.** That is how many kit pieces were in range; **3,601** were drawn, under a **620,015-triangle** budget. A shortfall of more than a hundred and sixty to one, by far the worst in the pass — and it is the single cause of almost everything the render lacks.

**The photograph's corner is under a green sidewalk shed** with `URBAN OUTFITTERS` along its fascia, scaffolding standards down the kerb, shop windows behind them, street signs on the mast, a Citi Bike dock at the right and red utility spray-paint on the asphalt. **The render has none of it.** Not one scaffold piece appears in this scene's kit at all, against **67 storefronts and 3,505 windows** — and other sheets in this pass carry 69 to 116 scaffold pieces, so the class is placed elsewhere and did not survive the budget here.

**Three commuters 4.6 m from the lens take the foreground.** Business figures with briefcases, seen from behind, filling the right half of the frame where the photograph has a taxi crossing an intersection. That is the second-closest agent in the pass and the same failure as the Sixth Avenue and Flatiron sheets: the walk clears 8 m of *built* fabric in front of the lens and applies no such rule to the crowd (J91).

**What this sheet gets right is the city behind all that.** **Six landmarks fall inside one 54.4° cone** — 30 Rockefeller Plaza, St Patrick's, MoMA, the Seagram Building, Lever House and Billionaires' Row — which is the richest Midtown view in the set and every one of them belongs on a northward look up Fifth Avenue.

## What matches

* **Street width, storey height and material**, which is what the record asks. A wide avenue between tall blocks, the paving reading as concrete and asphalt from **303 material slots** resolved against the shared photographic catalogue.
* **Six landmarks in the frame, all correctly placed**: **30 Rockefeller Plaza** at **554.2 m** (19.7° off axis), **St Patrick's Cathedral** at **608.3 m** (9.4°), **MoMA** at **852.9 m** (10.4°), the **Seagram Building** at **856.0 m** (27.1°), **Lever House** at **888.5 m** (18.1°) and **Billionaires' Row** at **1,165.7 m** (11.7°).
* **The avenue is the second most heavily paved frame in the pass** — 36,632 polygons, of which **20,683** are white markings, 5,800 sidewalk, 4,522 roadbed, 3,981 curb and 927 crosswalk. The crossing bars the near figures are standing on are surveyed geometry.
* **The two halves were developed to within a quarter-stop of each other.** The photograph's median sits **0.503 stops** above the middle-grey convention and the render's **0.246**, a difference of **0.257 stops** — the second-closest development agreement in the pass, after the MetLife sheet.
* **Contrast agrees almost exactly** — standard deviation **0.2248** against **0.2360**, a ratio of **0.953**.
* **The fleet is a Fifth Avenue weekday fleet**: **18 yellow taxis, 11 boro taxis, 10 sedans, 6 black cars, 5 box trucks, 2 SUVs, an MTA bus and a van**, with the crowd clock reporting **a weekday** for the assumed 2018-06-21, which was a Thursday. The photograph has a bus, a box truck and a taxi in it.
* **The crossing is populated.** A file of pedestrians crosses the middle distance where the photograph's do, five agents at LOD0.
* **The kerb-side furniture faces the kerb** (J84): 105 street lamps, **25 bus-stop signs and 8 shelters**, 21 flagpoles, 10 waste baskets, 10 vent grates, 8 subway entrances.
* **309 Citi Bike dock units** are in range (Stage 40).
* **The near park ground is nearly clean**: within 150 m the under-fraction is **0.018** over 222 samples, median clearance **0.186 m**.

## What does not match

* **The sidewalk shed and its signage are absent**, and with them the photograph's whole left-of-centre. No scaffold piece is in this scene's kit.
* **Three agents 4.6 m from the lens occupy the foreground.**
* **67 storefronts against 3,505 windows**, and **3 cornices, 3 pilasters, 3 string courses and 1 bulkhead** in the entire scene. At 100,664 pieces in range under a 620,015-triangle budget, the frame drew one piece in twenty-eight.
* **No street signs, no shop lettering, no utility spray-paint.** Applied markings other than lane paint are not drawn, and **50 props across eight kinds were wanted in range and had no asset** — 11 artwork, 10 memorial, 10 vending machine, 7 drinking fountain, 6 parks building, 3 misc structure, 2 passenger-information sign, 1 parks comfort station. That is the largest unmapped total in the pass.
* **The Citi Bike dock is not in frame** although 309 units are in range.
* **The chosen instant is 56° off its own target**, and the frame still needed **+5.36 stops** and is marked under-lit.
* **The render is darker in the midtone and more colourful overall** — median **0.4994** against **0.5420** (**0.921×**), mean **0.5189** against **0.4557** (**1.139×**), chroma **0.0537** against **0.0432** (**1.243×**), 95th percentile **0.9537** against **0.7463**. The photograph is a flat overcast with no highlight near white; the render has a clear June sky and hard shadows.
* **The dark building corner mid-frame carries a smooth mirrored band** where the photograph's corner is stone and glass behind scaffolding — a glass-curtain material left analytic because the catalogue has no photographic set for it.
* **1,880 tree rows did not fit the props budget**, capped at **916,361** triangles, and only **37** of the 403 trees placed are drawn from modelled branches within 120 m.
* **The crowd is a fraction of the ask.** The density table wanted **1,210 vehicles and 1,364 people**; **1,320 and 1,781** were simulated and **2,797** dropped — 815 vehicles and 738 pedestrians outside the radius, **638 pedestrians and 418 vehicles at the agent triangle budget**, 87 in the carriageway without crossing, 62 not on a walkable surface, 2 inside buildings, 4 above the observer, and **32 riderless bodies**.
* **Far park ground sinks**: beyond 400 m the under-fraction is **0.3516** over 677 samples, minimum **−4.312 m**, z-fighting **0.0281**.
* **4 of the 6 tiles in range have no structures file**, leaving 2,920 triangles of structures.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no sidewalk shed, no shopfronts, almost no cornice | 100,664 kit pieces in range against a 620,015-triangle budget — one piece in twenty-eight drawn, the worst shortfall in the pass | **performance — the binding constraint on this sheet** |
| three agents 4.6 m from the lens | the walk clears 8 m of built fabric in front of the lens and applies no such rule to the crowd (J91) | verification — open |
| no street signs, no lettering, no utility paint | applied signage and markings other than lane paint are not classes this build draws; 50 props across eight kinds had no asset | geometry + data |
| the Citi Bike dock is not in frame | 309 dock units are in range and none falls in this 54.4° cone from this position | verification |
| the chosen instant is 56° off the view azimuth | no hour above 20° elevation on 21 June puts the Sun behind a 29° heading; the rule reports the miss (J80) | reference — no source exists |
| the frame needed +5.36 stops | a Midtown avenue in canyon shade at 08:30; published under-lit and marked so (J83) | reference + verification — declared |
| p50 0.921×, chroma 1.243×, a blown highlight the render has and the photograph has not | a flat overcast reference against a clear Nishita sky and a chosen June sun | reference — no source for a historical sky |
| a mirrored band on the dark corner | `glass_curtain` is left analytic: the catalogue has no photographic set for a curtain wall, and a photograph of one is a photograph of what it reflects (J63) | data — declared |
| 1,880 tree rows dropped, 37 modelled trees against 366 cards | the props triangle budget at 916,361 triangles | performance |
| 250 people against a table asking 1,364 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| 32 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| 0.3516 of far park-ground samples under the terrain | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
