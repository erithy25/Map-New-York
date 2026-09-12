# Domino Sugar Refinery

`landmark_domino_sugar_refinery` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Domino Sugar Refinery June 2022.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-28 13:43:57, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Domino_Sugar_Refinery_June_2022.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.713183, -73.967742 (NYC_TM -1463, 1481) at z 7.4 m NAVD88 | azimuth 9.4°, pitch +0.4° | 26 mm on 36 mm (70.0° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 206.9 m from the item's recorded viewpoint — and the heading disagreement is the largest in the pass: the derived bearing is **9.4°** and **the item's recorded azimuth is 198.0°, 171.4° away**, which is to say the nominal viewpoint looks at this building from the opposite side. The photograph's own position and bearing were used. The recorded viewpoint is also **inside a building** — a ray straight up from the eye point hits the roof of `t_-2_1_roof_membrane` — so the camera was **moved 39.2 m** onto the nearest surveyed sidewalk polygon. From there the view is clear for 75 m; the nearest built thing in the frame is `t_-2_1_glass_curtain` 10.3 m away and no simulated agent stands within 20 m. The ground under it reads 5.825 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 5.74 to 7.14 m.

**Sun** — azimuth 211.7°, elevation **70.2°** at 2022-06-28T13:43:57−04:00, from the photograph's own **EXIF DateTimeOriginal** — the highest sun on any sheet in the pass; 938.5 W/m² direct normal, sky at strength 0.0305, Filmic, **+3.29 stops**, measured from the linear frame's median of **0.018427** (J83). The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,140 triangles: 9 building tiles (278,754 tris), 2 landmark models of which 1 falls inside the 70.0° frame, 19,143 pavement polygons, 1,047 props, **7,443 kit pieces** — the most of any sheet in the pass — 36 park-ground meshes, **60,480 triangles of structures across 9 tiles with none missing**, 14,158 quads of water, 78 vehicles and 341 people.

## Verdict — the refinery is genuinely recognisable, its height agrees with the catalogue to five centimetres, and the item's own viewpoint looks at it from the wrong side

**This is one of the better landmark pairings in the set.** The render carries the refinery's dark red brick, its rows of round-arched windows in the right rhythm and even the heavy rust-coloured external steel frame that braces the facade — the three things that make the building identifiable. The probe casts **43 rays, all 43 on built fabric**, and measures **60.05 m** above a ground of 3.11 m against a catalogue **60.0 m** for an origin **22.4 m** from the coordinate: agreement to five centimetres.

**The item's recorded azimuth is 171.4° from the bearing the photograph implies.** That is not a small error in a heading; it is the other side of the building. The rule that prefers the photograph's own position and bearing is what saved this sheet, and the disagreement it had to override is the largest in the pass.

**Its recorded viewpoint is also inside a building** — the fourth such coordinate found, after One World Trade Center, the New York Stock Exchange and the MetLife Building. The walk moved the camera 39.2 m to a surveyed sidewalk and the resulting sightline is decent: **10 of 13 rays clear, 8 on the subject, a fraction of 0.615**, with the blocked ones stopping at 28.1 m on a cobra-head lamp.

**What is missing is the industrial archaeology.** No chimney — the photograph's tall brick stack with `HAVEMEYERS & ELDER` on it is the building's signature — and no construction crane. The render's brick is also clean where the photograph's is a hundred and forty years weathered.

## What matches

* **The building reads as itself**: dark red brick, round-arched window rows, and the external bracing frame in front of the facade.
* **The height, to five centimetres of the catalogue** — 60.05 m measured against 60.0 m recorded.
* **The heading is the photograph's**, not the item's, and the record states the 171.4° it had to reject.
* **This is the most heavily kitted frame in the pass** — 7,443 pieces, including **344 storefronts, 232 window accessories, 94 parapets, 50 door entries, 32 fire escapes, 32 pilasters, 24 bulkheads, 16 cornices, 16 string courses, 13 quoins** and 2 billboards. Williamsburg's converted industrial frontages carry that kind of detail and here some of it survives the budget.
* **Every tile in range has its structures file** — **60,480 triangles across 9 tiles, 0 missing** — the second-best structures coverage in the pass after the Manhattan Bridge.
* **The waterfront is drawn**: **14,158 quads** across the East River, the Navy Yard Basin and the Wallabout Channel.
* **The near park ground is clean**: within 150 m the under-fraction is **0.0** over 166 samples, median clearance **0.204 m** — Domino Park's own esplanade sits on the terrain.
* **The fleet is an outer-Brooklyn fleet**: **37 sedans, 16 SUVs, 12 yellow taxis, 6 box trucks, 3 black cars, 3 boro taxis and a van** — far more private cars than any Manhattan sheet, which is what this neighbourhood has. The crowd clock reports **a weekday** for 2022-06-28, which was a Tuesday.
* **The esplanade is furnished**: 199 street lamps, 185 manholes, **45 benches**, 56 hydrants, 19 bike racks, 12 waste baskets, and 213 Citi Bike dock units (Stage 40).
* **Contrast agrees closely** — standard deviation **0.2125** against **0.2293**, a ratio of **0.927**.

## What does not match

* **The chimney is absent**, and with it the lettering that names the company.
* **The construction crane is absent** — the photograph is of a building site, and cranes are not a class this build carries.
* **The brick is clean.** The photograph's is stained, patched and weathered with gutted openings showing sky through them; the render's is an even course from the shared photographic catalogue.
* **The midtone is more than twice the photograph's** — median **0.4987** against **0.2329** (**2.141×**), mean **0.4577** against **0.3170** (**1.444×**). The photograph's own median sits **2.023 stops** below the middle-grey convention, the render's **0.242** above it, a **2.265-stop** difference which is nearly all of that ratio (J83). The reference is a dark brick mass exposed for a bright sky.
* **Half the photograph's colour** — chroma **0.0772** against **0.1416** (**0.545×**). A summer blue sky over weathered red brick is the reference's palette; the render's Nishita sky and catalogue brick are paler.
* **No cloud.** The reference's sky carries summer cumulus; nothing in this build reads a historical sky.
* **Park ground was not built for three tiles** in the 808 m radius — `t_-1_0`, `t_-1_1`, `t_-1_2` — leaving bare terrain there.
* **6,532 of 7,443 kit pieces are windows**, and kit was still capped by a **1,192,177-triangle** budget with **27,926 pieces in range**.
* **1,116 tree rows did not fit the props budget**, capped at **1,225,587** triangles, and only **11** of the 231 trees placed are drawn from modelled branches within 120 m — with a mean scale of **0.841**, the second-lowest in the pass.
* **The placement rules had an unusually hard time here.** **303 pedestrians were dropped for not being on a walkable surface** and **49 for being inside buildings**, along with **11 vehicles inside buildings** and 43 not on a carriageway — the highest inside-building counts in the pass. A construction site has sparse walkable-surface data and the crowd model does not know that.
* **The crowd is a fraction of the ask.** The density table wanted **289 vehicles and 1,971 people**; **362 and 2,236** were simulated and **2,177** dropped, including **634 pedestrians at the agent triangle budget** and 320 in the carriageway without crossing, plus **13 riderless bodies**.
* **313 of 341 people and 75 of 78 vehicles are at LOD2.**

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the item's recorded azimuth is 171.4° from the photograph's bearing | the nominal viewpoint looks at the building from the opposite side; the rule that prefers the photograph's own position and bearing overrode it, and the record states the size of the disagreement | **verification — open, the item's azimuth** |
| the recorded viewpoint is inside a building | fourth such coordinate in the pass; the walk recovered by moving 39.2 m to a surveyed sidewalk | **verification — open, the item's coordinate (J90)** |
| no chimney, no crane | the chimney is not in the landmark model and construction plant is not a class this build carries | **geometry — open** |
| the brick is clean where the photograph's is weathered | the shared photographic catalogue carries one course per material; per-building weathering has no source (J66) | data — no source exists |
| p50 2.141×, mean 1.444× | the photograph is developed 2.023 stops under the grey convention and the render 0.242 over it, a 2.265-stop difference before the scene (J83) | reference |
| chroma 0.545× | a summer blue over weathered red brick against a Nishita sky and catalogue brick | reference + data |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| bare terrain on three tiles | park ground was not built for `t_-1_0`, `t_-1_1` or `t_-1_2` inside the 808 m radius | **data — open, three tiles unbuilt** |
| 303 pedestrians off a walkable surface, 49 inside buildings, 11 vehicles inside buildings | the placement rules caught them; that the crowd and traffic models put them there is the construction site's sparse walkable-surface data | verification |
| 1,116 tree rows dropped, 11 modelled trees against 220 cards, mean scale 0.841 | the props triangle budget and the scale band the placement rule applies | performance + data |
| 341 people against a table asking 1,971 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
