# One Vanderbilt

`landmark_one_vanderbilt` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:One Vanderbilt January 2023 005.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-25 11:48:51, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:One_Vanderbilt_January_2023_005.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.752025, -73.977767 (NYC_TM -2345, 5778) at z 18.0 m NAVD88 | azimuth 324.1°, pitch **+33.4°** | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, portrait) | 904x1206. The camera stands on **this photograph's own EXIF GPS**, 70.3 m from the item's recorded viewpoint, and was **not moved** — the view azimuth is clear for 150 m. The lens was widened to the **18 mm floor** and the axis tilted **33.4°**, the steepest tilt in the pass, for a subject that tops out **73° above the horizon** at 120 m; the top is still cut off, and the record declares the verticals converge and the frame is not comparable on proportion. The nearest built thing in the frame is `prop_lamp_cobra_davit_59` 19.0 m away and the nearest simulated agent is `agent_veh_camry_taxi_yellow_1334.46` **7.9 m** away at 12.3° off axis.

**Sun** — azimuth 174.7°, elevation 30.2° at 2023-01-25T11:48:51−05:00, from the photograph's own **EXIF DateTimeOriginal**; 771.8 W/m² direct normal, sky at strength 0.0357, Filmic, **+3.40 stops**, measured from the linear frame's median of **0.01701** (J83). The physical rule would have given **0.51 stops**.

**In the scene** — 4,500,179 triangles: 5 building tiles (261,584 tris), 7 landmark models of which 4 fall inside the 73.7° frame, 29,426 pavement polygons, 1,365 props, 5,071 kit pieces, 17 park-ground meshes, 50 vehicles and 251 people.

## Verdict — the tower is modelled well enough to be identified from its setbacks alone, and the height it reports is the crown without the spire

**This is the second-best landmark model in the pass, after the Oculus.** One Vanderbilt's stepped setbacks, its blue-glass bands and the angled taper of its crown are all in the render, in the right order and at the right proportions, and the tower would be identifiable from the render alone. The camera stands on the photograph's own GPS with a clear 150 m view and did not have to move.

**The height is the crown, not the spire.** The probe casts **43 rays, all 43 on built fabric**, and measures **391.73 m** above a ground of 18.54 m, on an object **52.4 m by 52.2 m** in plan. The catalogue's figure for `one_vanderbilt`, whose origin sits **9.2 m** from the coordinate, is **427.0 m** — the published height to the spire tip. The 35 m between them is the mast, which the downward probe does not land on because it is a needle rather than a surface. That is the same distinction J68 was written about, from the other side: there a spire's height became rows of windows, here a spire's height is simply not counted. **Both numbers are in the record and the sheet reports the measured one**, which is the honest choice and also the one a reader has to know how to read.

**The brightness and colour differences are both the photograph's.** The reference is a dark glass tower against a blown white winter sky, developed **2.026 stops above** the middle-grey convention; the render sits at the convention, **0.222** over. That **1.804-stop** difference is the whole of the median ratio of **0.568**. And because the photograph is very nearly monochrome — chroma **0.0488** — the render's ordinary street colour comes out at **2.055×** it, the largest ratio in that direction in the pass.

## What matches

* **The tower's massing is right.** Setbacks, glass bands and crown taper in the correct sequence, at **124.3 m** and **3.8° off axis**.
* **Four landmarks are in the frame and all four belong**: **Grand Central** at **91.0 m** (66.2° off axis, its glazed train-shed roof visible at the left), One Vanderbilt at 124.3 m, the **New York Public Library** at **399.4 m** and **Times Square** at **1,087.7 m**.
* **The sightline is clear of everything but the subject.** 13 rays, **all 13 clear**, **10 on the subject**, fraction **0.769**, with 9 landing on the tower's own nearer fabric and 2 passing into sky beside it.
* **The street is the liveliest in the pass.** A crowd of some thirty figures stands along the sidewalk in dark winter clothing — the J53 repair visible, on a 25 January reference — with a food cart and its vendor, and a yellow taxi at the kerb.
* **The fleet is a Midtown weekday fleet**: **15 yellow taxis, 13 sedans, 10 boro taxis, 6 SUVs, 5 black cars** and a van, with the crowd clock reporting **a weekday** for 2023-01-25, which was a Wednesday. **Five people are at LOD0.**
* **Pershing Square's Citi Bike is a station**: **599 dock units** in range, the second-largest count in the pass (Stage 40).
* **The trees are bare and the date is why** — 14 drawn from modelled branches within 120 m, 140 as impostor cards beyond.
* **The block is furnished**: 138 street lamps, 138 manholes, **22 subway entrances**, 23 vent grates, 21 bus-stop signs, 10 LinkNYC kiosks, all facing the kerb (J84).
* **29,426 pavement polygons**, including **13,094** white markings and 751 crosswalk polygons.

## What does not match

* **Proportion, declared.** The photograph's verticals are near-parallel; the render's converge hard at a 33.4° tilt. This is the cost of containing a 392 m subject from 120 m away.
* **The spire is not in the measured height** — 391.73 m against a published 427.0 m — so any reader comparing the render's crown to the photograph's must know the mast is excluded.
* **The render holds twice the photograph's colour** — chroma **0.1003** against **0.0488** (**2.055×**). The reference is dark glass on white sky; the render has a yellow taxi, a coloured crowd and brick.
* **Two-thirds of the contrast** — standard deviation **0.1829** against **0.2889** (**0.633×**) — and a much darker midtone, median **0.4955** against **0.8720**, mean **0.4685** against **0.6946**. The photograph's blown sky is most of its range and the render's sky is a Nishita gradient.
* **No cloud.** The reference's sky carries faint winter cloud; nothing in this build reads a historical sky.
* **4,733 of 5,071 kit pieces are windows**, against **10 cornices, 10 string courses and 15 parapets**. Kit was capped by a **1,072,775-triangle** budget with **38,540 pieces in range** — the frame wanted more than thirty times what it drew.
* **1,644 tree rows did not fit the props budget**, which was capped at **1,161,563** triangles.
* **The crowd is a fraction of the ask.** The density table wanted **1,319 vehicles and 3,256 people**; **1,571 and 2,998** were simulated and **4,268** dropped — **1,183 pedestrians and 658 vehicles at the agent triangle budget**, 909 and 753 outside the radius, 425 pedestrians in the carriageway without crossing, 217 not on a walkable surface, **12 vehicles inside buildings**, 12 pedestrians and 4 vehicles above the observer, and **43 riderless bodies**.
* **The park ground was redraped hardest here.** All **60,062** vertices were shifted onto the scene heightmap, with a maximum lift of **1.626 m**, a maximum drop of **−2.831 m** and a 99th-percentile absolute shift of **2.5909 m** — the largest redrape in the pass, though the weighted median is **0.0006 m**.
* **There is no park ground within 150 m to check** — **0 samples**. Beyond 400 m the under-fraction is **0.343** over 863 samples, minimum **−4.777 m**.
* **3 of the 5 tiles in range have no structures file**, leaving 2,920 triangles of structures.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| verticals converge at a 33.4° tilt | a 392 m subject 120 m away tops out 73° above the horizon and the frame is 90° tall at the 18 mm floor; declared in the record | verification — declared |
| the measured height excludes the spire | the downward probe lands on surfaces, and a spire mast is a needle; the catalogue's 427.0 m is to the tip and the sheet reports the measured 391.73 m. Same distinction as J68, from the other side | **verification — declared, and a reading trap** |
| chroma 2.055×, p50 0.568×, sd 0.633× | the photograph is a dark-glass-on-blown-sky study developed 2.026 stops above the grey convention; the render is an ordinary coloured street at the convention (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 4,733 windows against 10 cornices | shells are extruded footprints with openings cut, and kit was capped at 1,072,775 triangles with 38,540 pieces in range | geometry + performance |
| 1,644 tree rows dropped | the props triangle budget | performance |
| 251 people against a table asking 3,256 | the agent triangle budget dropped 1,183 pedestrians and 658 vehicles; the placement rules took the rest, each with its count | performance + verification |
| 12 vehicles inside buildings | the placement rule caught and dropped them; that the traffic model put them there is its own gap | verification |
| 43 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| a 2.5909 m 99th-percentile redrape shift over 60,062 vertices | the park surfaces are draped on the pipeline heightmap and then redraped onto the render's own grid; the weighted median is 0.0006 m, so this is the tails | verification |
| 0.343 of far park-ground samples under the terrain | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
