# Charging Bull

`landmark_charging_bull` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Bowling Green NYC Feb 2020 15.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-02-05 09:35:51, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Bowling_Green_NYC_Feb_2020_15.jpg) — the photograph carries its own camera GPS, so the view direction is derived from the image at **high** confidence. It is an overcast February morning looking down Broadway past the anti-vehicle granite blocks, and **the bull is behind a crowd**: what marks its position in the left half is thirty people standing round it.

**Camera** — 40.705804, -74.013406 (NYC_TM -5358, 646) at z 9.0 m NAVD88 | azimuth 179.2°, pitch −3.6° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **25.9 m** from the item's recorded viewpoint. It was **not moved**: `moved: false`, offset 0.0 m, with the view azimuth clear for **150.0 m** against a 20.0 m requirement, and **no simulated agent within 60 m**. The nearest built thing in the frame is `prop_lamp_cobra_davit_39` **3.4 m** from the lens at +9.1° yaw and −10.5° pitch. The heading is the bearing from that GPS position to the bull; the item's own recorded azimuth is **217.2°**, **38.0° away**, and the record says it "belongs to its nominal viewpoint". The ground under the lens reads 7.444 m NAVD88, the 10th percentile of 113 samples within 12.0 m, range 7.26 to 8.15 m.

**Sun** — azimuth 139.4°, elevation **23.0°** at 2020-02-05T09:35:51−05:00, from the photograph's own **EXIF DateTimeOriginal**; 695.4 W/m² direct normal, sky at strength 0.0389, Filmic, **+4.66 stops**. The record declares the consequence itself: *"under-lit: the scene needed +4.66 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by"*. The linear frame's median is **0.007128** against the 0.18 target, so the development is **4.658 stops**, unclamped. The physical rule would have given **0.91**.

**In the scene** — 4,500,221 triangles: 4 building tiles (73,986 tris), 10 landmark models of which 3 fall inside the 54.4° cone, 22,244 pavement polygons, 1,189 props, 4,308 kit pieces, 19 park-ground meshes, **3 tiles of structures (43,576 tris)**, 88 vehicles and 309 people. The water table holds the East River, the Hudson, South Cove and Upper New York Bay.

## Verdict — four and two thirds stops of amplification, and a Citi Bike dock where the sculpture should be

**This is the most heavily developed frame read this round, and the record says so before the assessment does.** The scene's linear median is **0.007128** — one twenty-fifth of the 0.18 middle-grey convention — so the metered development is **4.658 stops**, past the +4 at which this build declares a frame under-lit. What you are looking at in the right half is not a picture of the light that was in the scene; it is that light multiplied twenty-five-fold. The consequences are all measurable: the render's 95th percentile is **0.9622**, effectively clipped, its standard deviation is **0.82×** the photograph's, and its chroma is **1.65×** — the only ratio above 1.0 on any sheet read this round, and it is above 1.0 because the photograph is a flat grey overcast morning and the amplification has pushed the render's authored surface colours past it.

**The cause is the geometry of the hour.** A 09:35 February Sun at **23.0°** of elevation and azimuth **139.4°**, against a camera looking at **179.2°**: the direct beam comes over the camera's left shoulder and every facade the frame contains is a north-west face in shade. The only fill is a procedural Nishita sky at strength **0.0389**. The build has no measured sky luminance and no bounce from the pale limestone that lines this block, so a winter canyon arrives at a twenty-fifth of a photographable level and the development pays for it.

**The bull is 818 triangles.** Measured off `blender_out/landmarks/charging_bull.glb`, `charging_bull_bronze` is **818 triangles** with an LOD1 of 138, and its builder is entirely candid about what that means: *"the bull is a massing sculpture, not a scan — the body, neck, head, horns, four legs and tail are built from convex hulls fitted to the published overall dimensions and to reference photographs, so the silhouette and stance are right but the modelled musculature is not the cast surface. This is the largest single fidelity gap in agent A's set, and it cannot be closed without a photogrammetric scan, which no open licence provides."* The published 3.4 m height and 4.9 m length are honoured exactly. What is absent is the only thing a photograph of this sculpture is ever about.

**Three different heights for the same subject appear in one record.** The catalogue entry 4.0 m away carries **3.4 m**, which is the sculpture's published height. The height probe cast 43 rays, **21 landed on fabric**, and measured **2.03 m** — the ray at the item's coordinate met the animal's back, not its horns. And the sightline's own note says something else again: *"the 12 m floor: the subject measures 1.6 m, which is under it, so the fan is the floor rather than the subject"*. The fan is therefore 12.0 m in both directions at 10.06° of half-angle, sized to a floor rather than to a bull.

**The recorded plan extent is the paving, not the sculpture.** The record gives **8.5 by 7.8 m**, and the glb explains it: the exported node carries three materials — `granite_dark`, `bronze_patina` and `bronze` — so the granite setts the bull stands on were joined into the same object as the bronze, and its bounding box is 7.76 by 8.54 m where the bull is 4.9 m long. This is J94's fault at the smallest scale in the pass: one object holding both the subject and the ground it stands on.

**And what the fan actually lands on is a bicycle.** All **13 of 13** rays are clear — a clear fraction of **1.0**, the cleanest sightline read this round — 7 land on the subject and 2 meet nothing, giving **0.538**. But `subject_lands_at_m` is **9.3 m** and `subject_lands_on` is **`prop_citibike_bike_43`**. The render shows exactly that: a Citi Bike dock of a dozen blue bicycles fills the left foreground, 9 m from the lens, in front of a 34 m subject that is 3.4 m tall. Nothing blocked the view; the nearest thing in it is a bike rack.

## What matches

* **The published dimensions are exact.** 3.4 m tall and 4.9 m long, set directly by the builder's own constants from Di Modica's description, and the bull faces north up Broadway as it does.
* **The material split is right.** `bronze_patina` for the body and `bronze` for the horns, nose and rear that visitors have rubbed to a polish — a distinction the builder made deliberately and that the photograph confirms.
* **The camera is where the photographer stood**, on the photograph's own GPS, not moved, with 150.0 m of clear view and nothing within 60 m.
* **The Sun is the real minute** of a real February Wednesday, from EXIF, and the development is metered and declared rather than assumed or hidden.
* **The sightline is completely clear.** 13 of 13 rays, a clear fraction of 1.0.
* **Bowling Green is furnished as Bowling Green**: 168 Citi Bike dock units, 156 street lamps, 120 manholes, **106 benches**, 70 cooling towers, 69 hydrants, 69 subway vent grates, 32 subway entrances, 30 waste baskets, 29 bike racks, 26 bus-stop signs, 5 newsstands and 3 flagpoles.
* **Sixty-one trees are drawn from modelled branches**, not cards — one of the better showings in the pass, because this frame's trees are inside the 120 m band. They are correctly bare: 5 February is a leaf-off date.
* **Structures are here**: 3 tiles imported for 43,576 triangles.
* **The block is paved and marked**: 22,244 polygons with 6,634 white markings, 5,531 roadbed, 4,987 sidewalk, 3,413 curb, 695 plaza, 444 crosswalk and 170 yellow markings, and **0 dropped**.
* **The frame passes its own gate without a retry**: mean 0.5286, sd 0.2148, `usable: true`.

## What does not match

* **The sculpture's surface.** 818 triangles of fitted convex hulls where the subject is a cast bronze whose entire interest is its modelled musculature. Declared by the builder as its largest single fidelity gap.
* **The frame is under-lit by the build's own standard** — 4.658 stops, past the +4 threshold — so its tone, contrast and colour are all a consequence of amplification rather than of the scene.
* **The render carries more colour than the photograph**, chroma 1.65×, which is the amplification and the overcast reference together, not a match.
* **A stop and a quarter of the brightness difference is exposure.** The photograph sits **1.04 stops below** the grey convention and the render 0.245 above it, a **1.285-stop** gap, so mean reads 1.351× and p50 **1.525×** (J83).
* **Neither half contains its subject clearly.** The photograph's bull is behind a crowd; the render's is 34 m away behind a Citi Bike dock, and the recorded landing distance of 9.3 m on a bicycle says so numerically.
* **Three heights, one subject**: 3.4 m in the catalogue, 2.03 m from the probe, 1.6 m in the fan's own note.
* **The recorded plan extent of 8.5 by 7.8 m is the granite setts**, because the export joined them into the bronze's object (J94).
* **More than half the park surface within 150 m sits under the terrain.** 490 samples, `under_frac` **0.5633**, median clearance **−0.288 m** — Bowling Green's own ground is buried by about 29 cm across the near field, which is the part of the frame the camera can see. Beyond 400 m it is better, 0.2092 of 239 samples.
* **53,345 faces were cut for landmark ground** — two orders of magnitude above a typical sheet, because ten landmark models stand inside this radius.
* **Nearly four in five kit pieces never reached the frame.** 4,308 drawn of **19,694** in range against a 1,180,419-triangle budget, of which 3,938 are windows against 13 cornices, 13 string courses and 15 pilasters. This is the Financial District, where the ornament is the architecture.
* **Two thirds of the props in range were dropped.** 1,189 drawn of 3,713 at a 1,216,824-triangle budget, **2,362 dropped**, including **2,121 tree rows**.
* **The massing behind the bull is plain.** The Cunard and Standard Oil buildings that frame this view in the photograph — colonnade, rusticated base, curved cornice — are tile shells with a window grid, because the kit that would carry their order was capped.
* **Twenty-six props across six kinds had no asset**: 8 artwork, 8 memorial, 4 drinking fountain, 3 misc structure, 1 parks building, 1 parks comfort station. At Bowling Green, *artwork* and *memorial* with no asset means the Netherlands Memorial Flagpole and the rest of the plaza's own monuments are absent.
* **Five green boro taxis at Bowling Green**, inside the zone where a Street Hail Livery may not take a hail, and only 7 yellow cabs in the Financial District at 09:35 on a weekday (J105).
* **Every vehicle is at the coarsest LOD** — all 88 at LOD2.
* **309 people where the table asked 2,381.** 728 vehicles and 2,381 people were wanted over the simulated ring; 769 and 2,661 were simulated and **3,033 dropped** — 920 pedestrians outside the radius, 787 at the agent budget, **526 in the carriageway without crossing**, 353 vehicles outside the radius, 274 at the budget, 96 not on a walkable surface, 29 riderless bodies, **18 vehicles and 17 pedestrians inside buildings** and 6 above the observer.
* **The frustum report is meaningless here, correctly.** It names the Whitehall, Battery Maritime and St. George ferry terminals as in the cone at **4,434.1 m** and **34.8° off axis** — outside a 54.4° frame's own half-angle — because the test is whether a footprint's angular span crosses the field of view, and that composite's footprint spans the harbour. The code says as much in its own note; the input is what is meaningless (J99).
* **No cloud.** The reference is flat overcast, which is precisely the sky this build cannot make: a Nishita dome has no cloud deck, so the render's shadows are hard where the photograph has none at all.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the bull is 818 triangles with an LOD1 of 138, and its exported node spans 7.76 by 8.54 m in plan and z -0.12 to 3.40 m | the accessor `count` and `min`/`max` of `charging_bull_bronze` and `charging_bull_LOD1` in `blender_out/landmarks/charging_bull.glb`, read from the binary glTF header |
| the node carries three materials, `granite_dark`, `bronze_patina` and `bronze` | the `materials` array of the same file, which is why the granite setts are inside the bronze's bounding box |
| a massing sculpture of convex hulls, not a scan; the published 3.4 m height, 4.9 m length and 3,200 kg | the dimensions and fidelity blocks of `blender/landmarks/charging_bull.py`, which cite Di Modica's own description and Wikipedia, and name this as the largest single fidelity gap in its set |
| the sculpture has no building footprint and is placed by coordinates | the same file's header: `require_base=False`, `bins=[]`, placed at 40.70552 N, 74.01344 W |
| one twenty-fifth of the middle-grey convention | the recorded `median_linear` of 0.007128 against the recorded `target_linear` of 0.18 |
| the most heavily developed frame and the only chroma ratio above 1.0 read this round | this sheet's 4.658 stops and 1.65 chroma ratio, against the thirty-two sheets read in the preceding rounds |
| the frustum test asks whether a footprint's angular span crosses the field of view | `landmarks_in_cone` in `tools/sheet_facts.py`, whose test is `abs(off) - span <= half` and whose own note says it "is not a visibility test" |
| 5 February is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py`, true for a date on or after 15 November or on or before 15 April (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 818 triangles of convex hulls for a cast bronze | a photogrammetric scan of the sculpture exists under no open licence, so the model is fitted to published dimensions and photographs. The builder declares this as its largest single gap | **data — no source exists; declared** |
| 4.658 stops of development, past the under-lit threshold | a 23.0 deg February Sun behind the camera's shoulder, every facade in the frame in shade, and a procedural Nishita sky at strength 0.0389 as the only fill. There is no measured sky luminance and no indirect bounce budget for a winter canyon (J83) | **verification — declared, and the number is published with the frame** |
| chroma 1.65x and sd 0.82x | the amplification above, against a flat overcast photograph | verification — consequence of the development |
| 1.285 stops of exposure difference | the photograph was developed 1.04 stops under the grey convention and the render is metered to it (J83) | reference — declared, and correct |
| three heights for one subject | the catalogue publishes 3.4 m, the probe measures whatever its ray meets at the coordinate (2.03 m, the animal's back), and the fan's floor note carries a third figure. The three are never reconciled in the record (J74, J94) | **verification — open** |
| the plan extent is the granite setts | the export joined the setts into the bronze's object, so the bounding box of "the object standing at the coordinate" is the paving (J94) | **verification — open; the same fault as the Brooklyn Bridge cable, at the other end of the scale** |
| the nearest thing the fan lands on is a bicycle 9.3 m away | a Citi Bike dock stands between the lens and a 3.4 m subject 34 m off, and nothing in the walk's clearance probe weighs a prop (J88) | verification — open |
| the kit withheld: 4,308 drawn of 19,694 in range | the kit triangle budget at 1,180,419 triangles, in the district whose architecture is its ornament | **performance** |
| 2,362 props dropped, 2,121 of them trees | the props triangle budget at 1,216,824 triangles | performance |
| the near-field park surface under the terrain, at an under_frac of 0.5633 | the park surfaces were draped on the fine grid and this scene's terrain coarsens away from the lens (J40, J96); the near field is where it shows | **verification — open, and this is the worst near-field reading read this round** |
| 26 props across 6 kinds unmapped, among them artwork and memorial | no asset exists for those kinds, so Bowling Green's own monuments are absent (J58 remainder) | data |
| 5 boro taxis inside the exclusion zone, 7 yellow cabs in the Financial District | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography (J105) | data — open |
| 309 people where the table asked 2,381 | the 1,125,000-triangle agent budget plus the placement rules; 35 agents were placed inside buildings | performance + verification |
| the frustum names a composite 4.4 km away | a composite's footprint spans the harbour, so its angular span crosses any field of view. The test is correct and its input is not (J99) | verification — open |
| flat overcast cannot be reproduced | a Nishita sky has no cloud deck and nothing in this build reads a historical sky | reference — no source exists |
