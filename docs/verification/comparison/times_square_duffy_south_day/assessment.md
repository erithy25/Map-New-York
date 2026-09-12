# Times Square centre: Duffy Square looking south, daylight

`times_square_duffy_south_day` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Square 3 2023-05-17.jpeg by F ASTILY, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-05-12 12:18:49, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Square_3_2023-05-17.jpeg) — the view direction is derived from the image at **high** confidence. Noon in May from the top of the red steps: the steps themselves in the immediate foreground with people sitting on them, the Father Duffy memorial on its plinth, the plaza's café chairs, and both walls of the bowtie carrying a continuous field of lit advertising — the FOX board, a T-Mobile campaign, Spotify, a dozen more — down to One Times Square closing the view.

**Camera** — 40.759122, -73.984725 (NYC_TM -2932, 6566) at z 21.1 m NAVD88, eye **6.2 m above the terrain** | azimuth 203.6°, pitch 0.0° | 24 mm on 36 mm (58.7° horizontal, 73.7° vertical, **portrait**) | 904x1206. The eye height carries its source: *"top landing of the TKTS red steps at Duffy Square, 4.6 m above the plaza (Perkins Eastman/Choi Ropiha structure, 16 ft to the top of the glazed stair), plus 1.6 m eye height"* (J65). The camera stands on **this photograph's own EXIF GPS**, **8.9 m** from the item's recorded viewpoint, and agrees with its azimuth to **0.4°**. It was **not moved**: view azimuth clear for **150.0 m**, nearest built thing `prop_lamp_cobra_davit_10` at **23.7 m**, nearest simulated body `agent_ped_2904.0` at **15.3 m**. The lens is chosen for the view: *"the bowtie is photographed wide from the TKTS steps; both building walls and One Times Square fit only at 74 deg horizontal"*. The ground under the lens reads 14.939 m NAVD88 from 16 samples within 5.0 m, range 14.81 to 15.17 m.

**Sun** — azimuth 159.9°, elevation **66.3°** at 2023-05-12T12:18:49−04:00, from the photograph's own **EXIF DateTimeOriginal**; 932.2 W/m² direct normal, sky at strength 0.0306, Filmic, **+0.81 stops**. Metered: the linear median is **0.10261**, over half the 0.18 target, so the development is only **0.811 stops**, unclamped. The physical rule would have given **0.0**.

**In the scene** — 4,500,192 triangles: 6 building tiles (296,366 tris), 10 landmark models of which 1 falls inside the 58.7° cone, 30,284 pavement polygons, 2,669 props, 6,149 kit pieces, 22 park-ground meshes, **1 tile of structures (21,408 tris) with 5 having no file**, 54 vehicles and 240 people.

## Verdict — the same blank sign faces that make the night frame too dark make this one too bright, and the square's colour is gone either way

**Read this sheet beside its night companion and the shape of the fault is visible from both sides.** 266 billboard kit pieces stand in this frame with named material slots, a defined 0..1 UV and no content, by the rule the build states about itself (DEVIATIONS B5, B15, B15a). At night that left the square black: the night render's 95th percentile is 0.4047 against its photograph's 0.9367. **In daylight the same blank faces do the opposite.** This render's 95th percentile is **0.877** against the photograph's **0.8289** — the render's highlights are *brighter* than the real square's — because an unbound sign face is a large pale surface catching a 66° Sun, and the great white wall that fills the left third of the frame is exactly that. One decision, two opposite errors, and in both cases the square's colour goes: chroma **0.0492** against **0.1193**, a ratio of **0.412**.

**The contrast, remarkably, matches.** Standard deviation 0.2237 against 0.2272, a ratio of **0.985** — because a blank white wall beside a shaded canyon holds about as much range as a screen wall beside a shaded canyon. The agreement is real and it is measuring the wrong thing.

**The frame does not contain the steps, the plinth or the plaza.** The photograph's lower half is the red steps with people on them and the Duffy memorial standing in the middle distance. The render's lower half is flat pale pavement with a manhole cover and a bench. The steps are modelled — 27 red laminated-glass treads rising 4.9 m, from a real building footprint — and the Duffy plinth and flagpole with them, but none of them is legible here, and the memorial's own prop class has no asset at all: **1 memorial and 4 artwork among the 23 props in range with nothing to draw them with** (J58 remainder).

**And the crowd is a tenth of the ask.** The density table wanted **3,119 people**; **240** are drawn. 1,501 vehicles and 3,000 people were simulated and **4,207 dropped**: **1,251 pedestrians at the 1,125,000-triangle agent budget**, 1,031 outside the radius, 744 vehicles outside the radius, 637 vehicles at the budget, 309 in the carriageway without crossing, **164 not on a walkable surface**, 37 riderless bodies, 29 off the carriageway and 5 above the observer. The plaza and the steps are not road-network sidewalk classes, so the places the photograph's crowd is standing are places this crowd cannot stand (J101).

**What the record gets right it states plainly.** The eye is on the steps at 6.2 m with its structural source. The height probe refused the catalogue — the nearest entry 12.2 m away carries **365.8 m**, the Bank of America Tower's spire — and measured **109.44 m** on `lm_c_times_square.32`, which is One Times Square's own roof (J74). Only **4 of 43** probe rays found fabric, the correct answer for a tower standing behind screens, and the ratio is published rather than hidden. **Eleven of thirteen sightline rays are clear**, so the view down the bowtie is genuinely open; the published fraction of **0.154** is low because only two rays land within the tolerance of a subject 354 m away, not because anything is in the way.

## What matches

* **The eye is on the steps**, 6.2 m above the terrain, with the TKTS structure's own 4.6 m landing named as its source (J65).
* **The camera and heading are the photograph's own**, 8.9 m from the nominal viewpoint and agreeing with its azimuth to **0.4°**.
* **The lens was chosen for the view**, at 24 mm and 58.7° horizontal, because both walls of the bowtie and One Times Square fit in nothing narrower.
* **The height is One Times Square's own roof**: 109.44 m measured, with the catalogue's 365.8 m correctly refused as a different member of the composite.
* **The view down the bowtie is open**: 11 of 13 rays clear, and the two that stop do so at 108.7 m on a tile mesh well down the block.
* **The contrast agrees almost exactly**: sd 0.985×.
* **The bowtie is paved as the bowtie**: 30,284 polygons with **13,787 white markings**, 5,868 sidewalk, 4,739 roadbed, 3,672 curb, **1,136 plaza**, 696 crosswalk and 302 median, and **0 dropped**.
* **The square is furnished**: 181 Citi Bike dock units, 126 cooling towers, 98 street lamps, 85 manholes, 54 hydrants, 17 vent grates, **16 LinkNYC kiosks**, 15 benches, 11 subway entrances, **10 newsstands**, 7 bike racks, 5 bus-stop signs and 4 waste baskets.
* **Nothing was dropped for the props budget**: 2,669 placed of 2,783 in range.
* **The fleet is a Times Square fleet**: 18 yellow taxis of 54 vehicles, with 11 boro taxis, 11 sedans, 7 black cars, 4 box trucks, 2 SUVs and a van.
* **The day type is right**: 12 May 2023 was a Friday and the simulation used its weekday profile.
* **The scene arrived bright and needed almost nothing**: 0.811 stops on a linear median of 0.10261.

## What does not match

* **The sign faces are blank, and in daylight that makes the render brighter than the real square** in the highlights: 95th percentile 0.877 against 0.8289, with the left third of the frame a single pale unbound face.
* **The square's colour is gone.** Chroma 0.412× — this is the most colourful block in the city and the render carries two fifths of its saturation.
* **The steps, the plinth and the café chairs are not in the frame**, where the photograph's lower half is all three.
* **No monument asset exists.** 23 props across five kinds had no asset: 14 misc structure, 4 artwork, 3 vending machine, 1 memorial, 1 passenger-information sign.
* **240 people where the table asked 3,119**, none of them on the plaza or the steps (J101).
* **Three quarters of the kit was withheld.** 6,149 drawn of **24,132** in range against a **1,114,895**-triangle budget, of which 5,528 are windows and 266 billboards against **19 cornices**; a further **4,312** were suppressed under the landmark shells.
* **Eight trees in 2,031 are drawn from modelled branches**; 2,023 are six-triangle cards and **804 are a substituted species** (J108).
* **Structures are almost absent**: 1 tile imported for 21,408 triangles with **5 having no file**, over the Times Square–42nd Street interchange.
* **Two thirds of a stop of the brightness difference is exposure.** The photograph sits **0.446 stops below** the grey convention and the render 0.236 above it, a **0.682-stop** gap, so mean reads 1.186× and p50 1.248× (J83).
* **The park ground sinks in the middle distance**: 0.2308 of 78 samples in the 150 to 400 m band with a z-fight fraction of 0.1154 there, and 0.2445 across all 1,403. There are **0 samples within 150 m**.
* **Eleven of the fifty-four vehicles are green boro taxis** in Times Square, inside the zone where a Street Hail Livery may not take a hail (J105).
* **The frustum reports the composite's centroid**: Times Square at 385.2 m and 34.9° off axis, while the camera stands inside the composite (J99).
* **No cloud.** The photograph carries scattered May cumulus in the strip of sky between the walls; the render's is a Nishita dome at strength 0.0306.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the night companion's 95th percentile is 0.4047 against its photograph's 0.9367 | the `frame_stats.json` of `times_square_duffy_south_night`, whose render and reference blocks carry those two figures |
| 109.44 m is One Times Square's own roof height | the recorded probe height against the building's published roof, and against the catalogue entry the probe refused, whose 365.8 m the Times Square builder's own note identifies as the Bank of America Tower's spire |
| the sign faces carry named slots, a defined UV and no content | the `sign_face_binding` block of the tile's own `kit_placements.json` and the signage section of DATA_CONTRACTS: an LED face models the display hardware and a bulletin is blank vinyl (DEVIATIONS B5, B15, B15a) |
| the steps are 27 red laminated-glass treads rising 4.9 m from a real footprint, with the Duffy plinth and a flagpole to 8.2 m | the Father Duffy Square block of `blender/landmarks/c_times_square.py` and its `TKTS_STEPS`, `TKTS_RISE` and `DUFFY_H` constants |
| the plaza and the steps are not walkable surface classes | `PED_SURFACES` in `blender/verify/agents.py` admits only sidewalk, median, plaza and crosswalk road-network classes, and a landmark structure's own treads are none of them (J101) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the sign faces are blank, so the highlights are too bright by day and absent by night | 266 billboard pieces are placed with named material slots, defined UVs and no content, because no advertising copy was invented anywhere. The same decision produces opposite errors in the two frames | **declared decision — the slots and UVs exist; the runtime content binding is the open half (B15a)** |
| chroma 0.412 | the same blank faces, on the most colourful block in the city | **declared decision — same half** |
| the steps, plinth and chairs are not in the frame | the geometry exists but does not fall in this frame's lower half; the plaza furniture the photograph shows is café seating, which is not a prop kind this build carries | geometry + data |
| no memorial or artwork asset | no asset exists for those kinds (J58 remainder) | data — open |
| 240 people where the table asked 3,119 | the 1,125,000-triangle agent budget plus the placement rules; 164 bodies were dropped for not standing on a road-network sidewalk class, which is what the plaza and the steps are not (J101) | **performance + verification** |
| the kit withheld — 6,149 drawn of 24,132 in range — and 19 cornices drawn | the kit triangle budget at 1,114,895 triangles, plus 4,312 pieces suppressed under the landmark shells | performance |
| 8 modelled tree canopies in 2,031, 804 substituted species | only 8 rows fall within the 120 m branch band, and the asset set is ten species with two states (J108) | performance + data |
| 21,408 triangles of structures over the busiest interchange in the system | five of the six tiles in range have no structures file (B13 remainder) | **data — open** |
| 0.682 stops of exposure difference | the photograph was developed 0.446 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| park ground under the terrain in the middle distance, with z-fighting | the park surfaces were draped on the fine grid and the terrain coarsens to 40.0 m (J40, J96) | verification — declared |
| 11 boro taxis in Times Square | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| the frustum names the composite's centroid | a composite landmark is tested by its centroid, and this camera stands inside the composite (J99) | verification — open |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
