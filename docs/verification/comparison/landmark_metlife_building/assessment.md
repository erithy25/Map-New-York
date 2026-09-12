# MetLife Building (200 Park Avenue)

`landmark_metlife_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Park Av Nov 2025 05.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2025-11-05 08:45:28, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Park_Av_Nov_2025_05.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.750676, -73.977285 (NYC_TM -2289, 5566) at z 17.0 m NAVD88 | azimuth 10.0°, pitch +6.6° | 18 mm on 36 mm (90.0° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint, not the photograph's**: the photograph's own EXIF GPS is **912.3 m away**, far past the 250 m at which it could still be the same view. And the item's own viewpoint is **inside a building** — a ray straight up from the eye point hits the roof of `t_-3_5_roof_membrane` — so the camera was **moved 62.2 m onto the nearest surveyed crosswalk polygon**. The record then states the outcome plainly: *"No point within 80 m had 80 m of open air along the view azimuth with nothing built inside 8 m of the lens, so the frame is closed off 20 m ahead."* The nearest built thing in the frame is `t_-3_5_glass_curtain` **19.5 m** away and the nearest simulated agent is `agent_ped_1634.5` **3.4 m** away.

**Sun** — azimuth 135.0°, elevation 20.5° at 2025-11-05T08:45:28−05:00, from the photograph's own **EXIF DateTimeOriginal**; 661 W/m² direct normal, Filmic, **+5.24 stops**.

**In the scene** — 4,500,210 triangles: 8 building tiles (335,232 tris), 11 landmark models of which 7 fall inside the 90.0° frame, **39,576 pavement polygons** — the most of any sheet in the pass — 1,124 props, 4,042 kit pieces, 28 park-ground meshes, 87 vehicles and 429 people.

## Verdict — every sightline ray is stopped by a glass wall twenty metres ahead, the walk says in advance that no better point existed, and the sheet publishes the failure rather than a number

**`subject_visible: false`, and for once the zero is unambiguous.** Of 13 rays, **none is clear** and **none lands on the subject**: all 13 stop at **20.1 m** on `t_-3_5_glass_curtain`, the curtain wall of the building the camera is standing beside. The visible fraction is **0.0**. Unlike the Empire State sheet, where a false verdict sat over a frame that plainly contained the tower, this one is correct: **the MetLife Building is not in the picture.** The render is a close three-quarter view of a glass-walled corner with a ground-floor arcade, a crosswalk, a queue of taxis and a stone planter wall at the lens.

**Three separate coordinate failures stack on this one sheet.** The photograph's GPS is **912.3 m** from the item's viewpoint, so the pairing is between a photograph of Park Avenue and a viewpoint that is not where it was taken. The item's own viewpoint is **inside a building**, the third such coordinate found in this pass after One World Trade Center and the New York Stock Exchange. And the recovery could not succeed: the walk searched 80 m and reports that **no candidate had both the open air and the 8 m clearance the frame needed**, then took the least bad one.

**What the sheet does get right is the height.** The probe casts **43 rays, all 43 on built fabric**, and measures **244.84 m** above a ground of 18.25 m against a catalogue **246.3 m** for an origin **21.1 m** from the coordinate. The slab is modelled and it is the right height. It is 380.2 m away and **4.0° off axis**, directly behind the wall.

## What matches

* **The height, against the catalogue** — 244.84 m measured against 246.3 m recorded.
* **The heading is consistent.** 10.0° as recorded agrees with the bearing from the camera position actually used to the MetLife Building, **10.0°**, to **0.0°** — the only exact agreement in the pass.
* **Seven landmarks are inside the frame and every one belongs to this stretch of Park Avenue**: the **Chrysler Building** at **225.2 m**, **Grand Central** at **290.1 m**, **One Vanderbilt** at **339.5 m**, the MetLife slab at **380.2 m**, **St Patrick's Cathedral** at **929.0 m** and **30 Rockefeller Plaza** at **1,015.3 m**.
* **The avenue is the most heavily paved frame in the pass** — 39,576 polygons, of which **23,085** are white markings, 4,951 roadbed, 4,932 sidewalk, 4,063 curb and 1,128 crosswalk. The crossing in the render's middle distance is surveyed geometry.
* **The two halves were developed almost identically.** The photograph's median sits **0.305 stops** above the middle-grey convention and the render's **0.235**, a difference of **0.07 stops** — the closest development agreement in the pass. Means **0.4991** against **0.4914** (**1.016×**) and medians **0.4975** against **0.5089** (**0.978×**) follow from that, on two overcast frames.
* **The fleet is a Grand Central weekday fleet**: **29 yellow taxis, 21 sedans, 17 SUVs, 10 black cars, 9 boro taxis** and 2 box trucks, with the crowd clock reporting **a weekday** for 2025-11-05, which was a Wednesday.
* **The arcade has people standing in it**, and the kerb-side furniture faces the kerb (J84): 95 street lamps, **16 subway entrances**, 17 vent grates, 10 LinkNYC kiosks.
* **Park Avenue's Citi Bike is a station**: 511 dock units in range (Stage 40).
* **The trees are leaf-off** on a 5 November reference — 48 from modelled branches within 120 m, 157 as cards beyond.

## What does not match

* **The subject is behind a wall.** No slab, no MetLife sign, no Helmsley tower, no flag, no plaza with steps — none of what the photograph is about.
* **The camera is 912 m from where the photograph was taken.** The record says what that means: a fix this far out is usually correct and simply of somewhere else.
* **A stone planter wall stands at the lens** in the immediate foreground, occupying the lower left of the frame, and a pedestrian stands **3.4 m** from the camera.
* **Two-thirds of the photograph's contrast** — standard deviation **0.1733** against **0.2565** (**0.676×**). The reference holds a bright overcast sky above dark facades; the render has almost no sky in it.
* **Half again the photograph's colour** — chroma **0.0828** against **0.0586** (**1.413×**) — mostly the taxis.
* **3,901 of 4,042 kit pieces are windows**, against **1 cornice, 1 quoin, 1 string course and 1 billboard** in the whole scene. Kit was capped by a **753,564-triangle** budget with **19,597 pieces in range**, the tightest kit budget in the pass.
* **2,936 tree rows did not fit the props budget**, which was capped at **987,603** triangles — the second-largest tree shortfall measured.
* **Not one agent is above LOD2.** All **88 vehicles** and all **437 people** in the scene are at their coarsest form, the only sheet in the pass where that is true of both.
* **The crowd is a fraction of the ask.** The density table wanted **1,001 vehicles and 2,291 people**; **1,219 and 2,678** were simulated and **3,372** dropped — 974 pedestrians outside the radius, **747 at the triangle budget**, 316 in the carriageway without crossing, 199 not on a walkable surface, **5 inside buildings**, 8 above the observer, and **33 riderless bodies**.
* **4 of the 8 tiles in range have no structures file**, leaving 5,204 triangles of structures.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| every ray stopped by a glass curtain wall 20 m ahead; the subject is not in the frame | the item's viewpoint is inside a building, and the walk reports that no point within 80 m had both open air and 8 m of clearance; it took the least bad candidate and published the zero | **verification — open, the item's coordinate, and a walk with nowhere to go** |
| the camera is 912.3 m from the photograph's GPS | the pairing is wrong: the fix is past the 250 m at which it could be the same view, so the item's viewpoint was used instead | **reference — the pairing is wrong, and the record says so** |
| a planter wall at the lens and a pedestrian 3.4 m away | the clearance walk had no candidate that satisfied its own 8 m rule | verification |
| sd 0.676×, chroma 1.413× | the reference is half overcast sky above dark facades; the render has almost no sky and a rank of yellow taxis | reference |
| 3,901 windows against 1 cornice | shells are extruded footprints with openings cut, and kit was capped at 753,564 triangles with 19,597 pieces in range | geometry + performance |
| 2,936 tree rows dropped | the props triangle budget at 987,603 triangles | performance |
| every agent at LOD2 | the LOD ladder at this distance under the agent budget, with 747 pedestrians and 465 vehicles already dropped at it | performance |
| 429 people against a table asking 2,291 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| 33 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
