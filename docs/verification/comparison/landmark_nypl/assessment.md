# New York Public Library (Stephen A. Schwarzman Building)

`landmark_nypl` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:New York Public Library - Main Branch (51396225599).jpg by ajay_suresh, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2021-08-21 15:52, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:New_York_Public_Library_-_Main_Branch_(51396225599).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.753350, -73.980853 (NYC_TM -2614, 5953) at z 23.4 m NAVD88 | azimuth 261.7°, pitch +0.3° | 27 mm on 36 mm (67.2° horizontal) | 1280x720. The camera stands on **this photograph's own EXIF GPS**, 75.3 m from the item's recorded viewpoint, and was then **moved 28.3 m onto the nearest real sidewalk polygon**, because the recorded viewpoint was **boxed in**: the view azimuth closed off **35 m ahead** against the 57 m this frame needs. Candidates were ranked on how much of the subject each saw (J79). From the point chosen the view is clear for 69 m, and the nearest built thing in the frame is `prop_lamp_cobra_davit_30` **13.3 m** away at **+34° yaw**. The ground under it reads 21.808 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 21.72 to 22.02 m.

**Sun** — azimuth 245.2°, elevation 42.4° at 2021-08-21T15:52:00−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 854.3 W/m² direct normal, sky at strength 0.0330, Filmic, **+4.67 stops**, marked **under-lit**: more recovery than the four stops the note says a photographer gets hand-held. The linear median is **0.007087**. The physical rule would have given **0.03 stops**.

**In the scene** — 4,500,023 triangles: 6 building tiles (300,026 tris), 9 landmark models of which 2 fall inside the 67.2° frame, 25,557 pavement polygons, 1,332 props, 4,450 kit pieces, 21 park-ground meshes, 53 vehicles and 252 people.

## Verdict — the height agrees with the catalogue to within a tenth of a metre, and a street lamp thirteen metres from the lens hides twelve of thirteen rays, exactly as it did at Madison Square Garden

**The measurement is as good as it gets.** The probe casts **43 rays, all 43 landing on built fabric**, reporting **38.28 m** above a ground of 23.39 m, against a catalogue height of **38.2 m** for a model whose origin sits **3.8 m** from the recorded coordinate. The library is modelled, in place, and the right height.

**The frame shows none of it.** The reference is the Fifth Avenue front: the Beaux-Arts portico with its paired columns, the two marble lions, the incised name, the banners, and a grand staircase covered in people. **The render is a street with a grassy bank, some trees, a curving roadway across its lower half and two building masses at the right.** The portico, the lions and the stairs are not identifiable in it.

**The cause is one street lamp, and this is the second sheet in the pass with the same cause.** Of 13 sightline rays, **1 is clear** and **12 stop at 14.7 m** on `prop_lamp_cobra_davit_30`, giving a visible fraction of **0.077** — the identical figure, from the identical kind of object, as the Madison Square Garden sheet. The clearance walk moved the camera 28.3 m to a point where the view azimuth is clear for 69 m, which is true of *built* fabric; a cobra-head mast standing 13.3 m away at 34° yaw is a prop, and the walk does not weigh it. The library is in the cone at **119.9 m**, **15.3° off axis**, and behind that mast.

## What matches

* **The height, against the catalogue** — 38.28 m measured from 43 rays, all on fabric, against 38.2 m recorded, from an origin 3.8 m from the coordinate.
* **The view is the photograph's own heading.** Azimuth **261.7°** is the bearing from its GPS to the main entrance; the item's recorded azimuth is 292.4°, **30.7° away**, and was not used.
* **The camera was snapped to a surveyed sidewalk**, not to a heuristic offset, keeping its eye height above the heightmap.
* **The park bank on the left is Bryant Park's** and it is drawn with its trees: **69 of them from modelled branches** within 120 m, 424 more as impostor cards out to 659 m.
* **Fifth Avenue is dressed.** 25,557 pavement polygons — **12,009** white markings, 4,849 sidewalk, 4,265 roadbed, 3,243 curb, 646 crosswalk — and the lane lines in the render's foreground are surveyed geometry.
* **The fleet is a Midtown Saturday fleet**: **21 yellow taxis, 11 black cars, 8 boro taxis, 8 sedans, 4 SUVs and an MTA bus**, with the crowd clock reporting **Saturday** for 2021-08-21, which was one.
* **The bus stops are furnished** — 27 bus-stop signs and **10 bus shelters** — and they face the kerb (J84).
* **Citi Bike is a station**: 266 dock units in range (Stage 40).
* **The near park ground is nearly clean**: within 150 m the under-fraction is **0.0202** over 247 samples, median clearance **0.196 m**, and nothing z-fights.
* **The frame statistics agree closely** — mean **0.806×**, standard deviation **0.809×**, median **0.865×**, chroma **0.860×**. Two sunlit Midtown frames of the same brightness and colour, of different subjects.

## What does not match

* **The portico, the columns, the lions, the incised name and the staircase are all absent from the frame.** The lions in particular are exactly the class that has no asset: **8 artwork and 7 memorial** props were wanted in range and had none.
* **Twelve of thirteen rays are blocked by a street lamp 14.7 m from the lens.** The fraction reports 0.077 and the verdict still reads `subject_visible: true` on one ray.
* **The frame needed +4.67 stops** and is marked under-lit. A 42.4° August sun at azimuth 245.2° behind a view pointing 261.7° is almost straight into the lens, so everything facing the camera is in its own shade.
* **4,283 of 4,450 kit pieces are windows**, against **6 cornices, 8 pilasters, 6 string courses and 1 quoin** in the whole scene. Kit was capped by a **932,059-triangle** budget with **40,376 pieces in range** — the frame wanted more than twenty times the kit it could draw, and a Beaux-Arts front is exactly what that shortfall removes.
* **862 tree rows did not fit the props budget.**
* **The crowd is a fraction of the table's ask and of the photograph's.** The density table wanted **1,078 vehicles and 3,733 people**; **1,213 and 3,000** were simulated and **3,904** dropped — **1,291 pedestrians at the agent triangle budget**, 1,224 outside the radius, 158 in the carriageway without crossing, 53 not on a walkable surface, 2 inside buildings, and **20 above the observer**. The photograph's staircase alone carries more people than the render's whole frame.
* **36 riderless bodies were dropped** — bicycles, e-bikes and pedicabs the fleet exports without a rider.
* **197 of 252 people and 44 of 53 vehicles are at LOD2**, with a single agent at LOD0.
* **Far park ground sinks and z-fights**: beyond 400 m the under-fraction is **0.3035** over 201 samples with a z-fight fraction of **0.0498**, the highest z-fighting measured in the pass.
* **4 of the 6 tiles in range have no structures file**, leaving 2,920 triangles of structures.
* **Seven prop kinds were wanted and unmapped**: 9 vending machine, 8 artwork, 7 memorial, 4 drinking fountain, 4 parks building, 1 parks comfort station, 1 passenger-information sign.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| twelve of thirteen rays blocked by a cobra-head lamp 14.7 m from the lens | the clearance walk clears the view azimuth of *built* fabric and does not weigh props; the same failure and the same 0.077 fraction as the Madison Square Garden sheet | **verification — open, and now a pattern across two sheets** |
| no portico, no columns, no lions, no staircase | the shell is an extruded footprint with openings cut, kit capped at 932,059 triangles against 40,376 pieces in range, and the lions' class has no asset (8 artwork, 7 memorial) | **geometry + performance + data** |
| the frame needed +4.67 stops | a 42.4° sun at 245.2° almost straight into a view along 261.7°; published under-lit and marked so (J83) | reference + verification — declared |
| 4,283 windows against 6 cornices | the kit triangle budget removed nineteen pieces in twenty, and the classifier has no source for a modelled Beaux-Arts front | geometry + performance |
| 252 people where the photograph's staircase alone holds more | the agent triangle budget dropped 1,291 pedestrians and the placement rules the rest, each with its count | performance + verification |
| 862 tree rows dropped | the props triangle budget | performance |
| z-fighting at 0.0498 beyond 400 m | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m, the worst case measured | verification |
| 36 riderless bodies dropped | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| seven prop kinds unmapped | no asset exists for those kinds | data |
