# Midtown drive-through: Sixth Avenue at 45th Street

`drive_midtown_sixth_ave_45th` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:45th St 6th Av td 06 - 1156 Sixth Avenue.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018 — **the year only**, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:45th_St_6th_Av_td_06_-_1156_Sixth_Avenue.jpg) — the photograph's own view direction **was not** derived from the image; confidence is **medium**.

**Camera** — 40.756779, -73.982545 (NYC_TM -2748, 6306) at z 20.1 m NAVD88 | azimuth 29.0°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, 35.3 m from the item's recorded viewpoint, and was **not moved**; the view azimuth is clear for 150 m. The ground under it reads 18.473 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 18.25 to 18.87 m. The item names no subject, so the axis is level and the lens the default 35 mm, and the record directs the comparison: *"compare them on street width, storey height and material, not on composition."* The nearest built thing in the frame is `prop_tree_pin_oak_small_2` 8.0 m away and **the nearest simulated agent is `agent_ped_133.7` 4.0 m** from the lens at 9.1° off axis.

**Sun** — azimuth 85.5°, elevation 32.2° at 2018-06-21T08:30:00−04:00. **Chosen, not measured**, and the record admits the choice did not achieve its own aim: the photograph carries only a year, 21 June is assumed, and of the hours putting the Sun above 20° this is the one whose bearing comes closest to the view azimuth — **85° against 29°, 56° off**. 788.4 W/m² direct normal, Filmic, **+6.00 stops** — and clamped: *"the frame wanted +6.07 stops and was held at +6.00: a scene this far from a photographable level is not developed into a picture of one."* The linear median is **0.002673**. The physical rule would have given **0.42 stops**.

**In the scene** — 4,500,116 triangles: 7 building tiles (315,514 tris), 9 landmark models of which 3 fall inside the 54.4° frame, 29,405 pavement polygons, 902 props, 4,473 kit pieces, 25 park-ground meshes, 53 vehicles and 230 people.

## Verdict — two pedestrians four metres from the lens are the whole picture, and the Citi Bike dock the photograph is about is in the data and not in the frame

**The reference is a shopfront and a bike dock.** A limestone block on Sixth Avenue with its whole ground floor in glass — an optician, a Wells Fargo branch in red, a formalwear shop with three suited mannequins in the window, the street number 1156 — and along the kerb a full Citi Bike station with two dozen blue bicycles in it. Flat overcast, wet asphalt.

**The render is two people.** A figure in a tan jacket seen from behind and another in a black top occupy the centre of the frame from waist to head, **4.0 m from the lens**, with a leafy pin oak filling the upper right and a dark glass tower behind them. Behind the two figures a group of small pedestrians stands on the sidewalk. No storefront, no signage, no bicycles, no hydrant.

**This is the third sheet in the pass where an agent standing beside the view axis takes the frame.** The Flatiron's near third is a delivery vehicle, the Oculus has two figures in its right foreground, and here the pair is the subject. The clearance walk tested the view azimuth and found it clear for **150 m**, which is true of built fabric; an agent 4.0 m away at 9° off axis is not built fabric and the walk does not weigh it.

**And the thing the photograph is about is in the scene.** **348 Citi Bike dock units** are in range — the Stage 40 repair working, and this is exactly the block that has a large station. None of them is in this cone.

## What matches

* **Street width and storey height are Midtown's**, which is what the record asks to be compared: a wide avenue with a tall glass tower on the far side and sidewalk trees at the right spacing.
* **The material palette is the right one.** 348 material slots resolved against the shared photographic catalogue — limestone, concrete sidewalk, asphalt, granite — and the paving reads as concrete rather than as flat colour.
* **Three landmarks are in the cone and all three belong to this view up Sixth Avenue**: **30 Rockefeller Plaza** at **362.6 m** (16.2° off axis), **MoMA** at **678.6 m** (11.4°) and **Billionaires' Row** at **969.0 m** (3.0°).
* **The trees near the lens are modelled, not cards** — **42 of them from their own branches** within 120 m against only 46 impostor cards, the highest modelled-to-card ratio in the pass, and the canopy casts real shadows on the paving.
* **The fleet is a Midtown weekday fleet**: **21 yellow taxis, 11 sedans, 10 boro taxis, 5 black cars, 3 SUVs and 3 vans**, with the crowd clock reporting **a weekday** for the assumed 2018-06-21, which was a Thursday.
* **Eleven agents are at LOD0** — the most on any sheet in the pass — which is why the two near figures hold up at four metres.
* **Sixth Avenue is dressed**: 29,405 pavement polygons (**13,095** white markings, 6,020 sidewalk, 4,753 roadbed, 3,549 curb, 967 plaza, 652 crosswalk), 99 street lamps, **15 subway entrances**, 13 vent grates, 13 bus-stop signs, 5 mailboxes, 4 newsstands, all facing the kerb (J84).
* **The instant's reasoning is written down even though it failed.** A photograph dated by year alone cannot supply one, and the record names the assumption, the rule, the result and — unusually — the size of the miss.

## What does not match

* **Two agents four metres from the lens occupy the frame** where the photograph has a shopfront fifteen metres away.
* **32 storefronts in the whole scene**, against **4,403 windows**. The photograph's entire ground floor is glass shopfront with signage, awnings and window displays. Kit was capped by a **740,124-triangle** budget with **30,816 pieces in range** — the frame wanted more than forty times what it drew, the worst kit shortfall measured in this pass, and shopfronts are what that removes.
* **No signage of any kind.** Shop names, telephone numbers, branch livery and window displays are not classes this build models; **2 artwork, 2 memorial, 1 vending machine and 1 passenger-information sign** props were wanted in range and had no asset.
* **The Citi Bike dock is absent from the frame** although 348 dock units are in range.
* **The chosen instant is 56° off its own target.** The rule exists to put the Sun behind the camera; on a heading of 29° in late June no hour above 20° elevation does that, and the record says so rather than pretending the light is the photograph's.
* **The frame was clamped, not met**: it wanted **+6.07 stops** and was held at **+6.00**, so it is published below even its own metered target.
* **The render has more contrast and more colour than the day had.** Standard deviation **0.2710** against **0.2283** (**1.187×**), chroma **0.0876** against **0.0543** (**1.613×**), 95th percentile **0.9846** against **0.8939**. The reference is a flat overcast on wet asphalt; the render puts a 32° June sun into a clear sky and gets hard tree shadows the photograph has none of.
* **The road is dry.** The photograph's asphalt is wet and reflective; nothing in this build reads a historical sky or a historical pavement condition.
* **1,269 tree rows did not fit the props budget**, capped at **982,596** triangles.
* **The crowd is thin behind the two near figures.** The density table wanted **1,124 vehicles and 1,354 people**; **1,275 and 1,724** were simulated and **2,716** dropped — **682 pedestrians and 375 vehicles at the agent triangle budget**, 612 and 814 outside the radius, 130 pedestrians in the carriageway without crossing, 67 not on a walkable surface, 3 above the observer, and **23 riderless bodies**.
* **There is no park ground within 150 m to check** — **0 samples**. Beyond 400 m the under-fraction is **0.2322** over 534 samples.
* **5 of the 7 tiles in range have no structures file**, leaving 21,504 triangles of structures.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| two agents 4.0 m from the lens fill the frame | the clearance walk tests the view azimuth for *built* obstruction and does not weigh an agent beside it; third sheet in the pass with this failure, after the Flatiron and the Oculus | **verification — open, and now a pattern** |
| 32 storefronts against 4,403 windows | kit capped at 740,124 triangles with 30,816 pieces in range, a shortfall of more than forty to one, and shopfronts are the first thing that removes | **performance — the worst kit budget in the pass** |
| no shop signage, no window displays | applied lettering, livery and displays are not classes this build models; 2 artwork and 1 information sign had no asset | geometry + data |
| the Citi Bike dock is not in frame | 348 dock units are in range and none falls in this 54.4° cone from this position | verification |
| the chosen instant is 56° off the view azimuth | no hour above 20° elevation on 21 June puts the Sun behind a 29° heading; the rule reports the miss rather than hiding it (J80) | reference — no source exists |
| published at the +6.00 clamp having wanted +6.07 | the clamp's rule: a scene this far from a photographable level is not developed into a picture of one (J83) | verification — declared |
| sd 1.187×, chroma 1.613×, hard tree shadows | a flat overcast reference against a clear Nishita sky and a chosen June sun; nothing reads a historical sky | reference — no source exists |
| dry road against wet asphalt | no historical pavement condition is read | reference — no source exists |
| 1,269 tree rows dropped | the props triangle budget at 982,596 triangles | performance |
| 230 people against a table asking 1,354 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| 23 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
