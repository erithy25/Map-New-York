# Empire State Building

`landmark_empire_state_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Empire State Building August 2021 007.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-19 11:47:25, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Empire_State_Building_August_2021_007.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.746000, -73.987600 (NYC_TM -3162, 5101) at z 14.4 m NAVD88 | azimuth 31.1°, pitch +21.3° | 18 mm on 36 mm (90.0° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint, not the photograph's**: the photograph's own EXIF GPS is **357 m away**, past the 250 m at which it could still be the same view. The record states what that means — *"a fix this far out is usually correct and simply of somewhere else."* The recorded viewpoint was then found **boxed in** (the view azimuth closed off 51 m ahead, against the 80 m this frame needs), so the camera was **moved 16 m to the right** to the nearest point in open air, chosen by ranking candidates on **how much of the subject each one sees** (J79). No point within 80 m had 80 m of open air with nothing built inside 8 m of the lens; the chosen point is closed off 54 m ahead.

**Sun** — azimuth 145.6°, elevation 57.7° at 2021-08-19T11:47:25−04:00, from the photograph's own **EXIF DateTimeOriginal**; 912.7 W/m² direct normal, sky at strength 0.0312, Filmic, **+1.80 stops**, measured from the linear frame's median of **0.051677** placed at middle grey (J83). The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,097 triangles: 7 building tiles (392,028 tris), 5 landmark models of which 2 fall inside the 90.0° frame, 33,712 pavement polygons, 3,237 props, 5,204 kit pieces, 29 park-ground meshes, 88 vehicles and 428 people.

## Verdict — the two halves are not the same view, and both the pairing and the sightline verdict are wrong in ways the record names itself

**This sheet fails, and it fails honestly.** The photograph was taken from the sidewalk directly beneath the tower, looking straight up its full height; the render looks north-north-east **down Fifth Avenue from 30th Street at a tower 313 m away**. Nothing about the composition, the proportion or the tonal range is comparable, and the cause is in the first line of the record: the photograph's EXIF GPS is **357 m** from the item's recorded viewpoint, so the camera could not be stood on it. The pairing is between a photograph of the base and a viewpoint a block to the south.

**The second failure is the sightline, and it points the other way.** The record reports `subject_visible: **false**` with a visible fraction of **0.0**: of 13 rays, **3 are clear**, **none lands on the subject**, and 10 are blocked at **54.8 m** by `t_-4_5_terracotta`. **And the tower is plainly in the render**, its setback crown and mast inside the top edge, recognisably itself. The record explains the contradiction rather than hiding it: *"nothing stands within 25 m of the subject's recorded coordinate on any clear ray: the clear rays run on to `lm_empire_state.19` at 412 m. The line is open and the subject is not on it, which is a fault in the item's coordinate or in the model, not in the camera."* The clear rays hit the Empire State model — just a piece of it **95 m beyond** the coordinate's own 317 m, and therefore outside the 25 m reach that decides whether a hit counts as the subject.

**What did work is the measurement of the thing itself.** The height probe casts **43 rays, all 43 on built fabric**, and measures **431.0 m** above a ground of 15.08 m, against the catalogue's **443.2 m** for a model whose origin is **3.6 m** from the recorded coordinate. The tower is modelled and it is the right height. The verdict about seeing it is what is broken.

## What matches

* **The Empire State Building is in the frame and is the right building.** At **313.5 m**, **4.1° off axis**, its crown setbacks and mast read correctly against the sky, and it is one of 2 landmarks inside the 90° cone — the other being the New York Public Library at **916.1 m**, 2.5° off axis.
* **The tower's height is measured, not asserted** — 431.0 m from 43 rays, all of them landing on fabric, against a catalogue height of 443.2 m.
* **The azimuth is consistent.** 31.1° as recorded agrees with the bearing from the camera position actually used to the building, **31.2°**, to **0.1°**.
* **The camera stands on the street.** The ground under it reads 12.79 m NAVD88 — the **10th percentile of 113 samples within 12 m**, range 12.64 to 14.09 m — because the viewpoint note places the photographer on the traffic surface and the 1 m DEM carries plinths that would lift the camera off it.
* **The lens and the tilt are both justified in the record, in order.** At 35 mm the tower did not fit; widened to the **18 mm floor** a level axis still cuts off a top that stands **54° above the horizon**; the axis was then tilted **+21.3°** to contain it, and the record declares that the verticals converge and the frame is therefore not comparable on proportion.
* **The street canyon is dressed and plausible.** 33,712 pavement polygons (**19,469** white markings, 4,624 sidewalk, 3,847 roadbed, 3,748 curb, 865 crosswalk), 252 storefronts with 33 interiors and 34 bulkheads along the frontages, 98 fire escapes on the mid-rise walls, 12 water towers on the roofs.
* **The crowd and the fleet are the simulation's own for 11:47 on a Thursday** — 88 vehicles within 320 m and 428 people within 200 m, after 120 s of simulated time.
* **Citi Bike is a station**: 174 dock units in range, the Stage 40 repair.

## What does not match

* **The view.** The photograph is a ground-level upward view from the base; the render is a street view from a block away. There is no gap to measure here because the frames do not share a subject framing.
* **The render is four times as colourful as the photograph** — chroma **0.1386** against **0.0346**, a ratio of **4.006**, the largest colour disagreement in the set and in the unusual direction. The reference is a near-monochrome overcast of grey limestone and dark glass; the render's canyon is brick, terracotta and tan. The photograph is desaturated because of what it is looking at, and the render is not looking at it.
* **Brighter midtones and less contrast.** Median **0.4932** against **0.3115** (**1.583×**), mean **0.5606** against **0.4418** (**1.269×**), standard deviation **0.2037** against **0.3030** (**0.672×**), 5th percentile **0.2424** against **0.1095**. The photograph's own median sits **1.187 stops** below the middle-grey convention and the render's **0.207** above it — a difference of **1.394 stops** that accounts for most of the ratio before the scene does (J83).
* **No overcast.** The reference's sky is a flat white August overcast; the render's is a clear Nishita sky at 57.7° elevation. Nothing in this build reads a historical sky.
* **The near ground is an undifferentiated pale plane** across the bottom third of the render, where 33,712 pavement polygons are recorded as present. The geometry is there; at this grazing angle with authored base colours it reads as one flat surface rather than as roadway, kerb and sidewalk.
* **The mid-rise walls are extrusion with openings.** **4,294 windows** against **37 cornices, 49 pilasters, 35 string courses and 17 quoins** in the whole scene: Murray Hill's brick and terracotta fronts carry far more relief than the shells have.
* **Kit hit its ceiling and the agents hit theirs.** Kit was capped by a **1,429,456-triangle** budget with **13,067 pieces in range**; at the **1,125,000-triangle agent budget** a further **132 vehicles and 971 people** were dropped. The density table asked for **644 vehicles and 3,285 people** over the simulated ring, **773 and 2,999** were simulated, and **3,256** were dropped in total.
* **168 people were dropped for standing in the roadway without crossing**, 91 for no sidewalk, 11 vehicles for no roadway in the planimetric data, and **15 cyclists, e-bikes and pedicabs were not drawn** because the fleet exports those bodies without a rider.
* **Far park ground sinks badly.** Beyond 400 m the under-fraction is **0.3724** over 811 samples, with a minimum clearance of **−11.983 m** and a 1st percentile of **−9.296 m**. Between 150 and 400 m it is **0.1439**. This is the worst park-ground disagreement measured on any sheet so far, and it is at the scene edge where the terrain grid coarsens to 40 m.
* **4 of the 7 tiles in range have no structures file**, leaving 3,216 triangles of structures.
* **The trees near the lens are almost all cards.** **19** are drawn from modelled branches within 120 m against **2,526** impostor cards out to 907 m; 989 species were substituted and 2,540 instances scaled, mean scale 0.904.
* **Seven prop kinds were wanted and had no asset**: 3 memorial, 3 payphone, 3 vending machine, 2 misc structure, 1 artwork, 1 drinking fountain, 1 real-time passenger information sign.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are not the same view | the photograph's EXIF GPS is 357 m from the item's recorded viewpoint, past the 250 m at which it could be the same view, so the item's viewpoint was used. The photograph is of the base; the viewpoint is a block south | **reference — the pairing is wrong, and the record says so** |
| `subject_visible: false` while the tower is visibly in the frame | the clear rays run past the recorded coordinate to `lm_empire_state.19` at 412 m, outside the 25 m reach within which a hit counts as the subject; the coordinate and the model disagree in plan. The record names it as a fault in the coordinate or the model, not the camera | **verification — open** |
| the camera had to move 16 m and still sees the subject on no ray | the recorded viewpoint is boxed in at 51 m against the 80 m the frame needs, and no candidate within 80 m had both the open air and the sightline; the walk chose the best available and recorded the sightline it got (J79) | verification — declared |
| verticals converge; proportion not comparable | the subject tops out 54° above the horizon and the frame is 74° tall at the 18 mm floor, so the axis was tilted +21.3°; declared in the record | verification — declared |
| chroma 4.006× | the reference is a near-monochrome overcast of limestone seen from beneath; the render is a brick canyon in sunlight. This follows from the wrong pairing, not from the materials | reference |
| p50 1.583×, sd 0.672× | the photograph is developed 1.187 stops under the grey convention and the render 0.207 over it, a 1.394-stop difference before any scene effect (J83) | reference |
| no overcast | nothing in this build reads a historical sky | reference — no source exists |
| the near ground reads as one flat plane | pavement geometry is present; its materials are authored base colours and the grazing angle flattens them further | data |
| 4,294 windows against 37 cornices | the shells are extrusions with openings cut; no source exists for modelled Murray Hill relief | geometry |
| kit, vehicles and people all capped | the 1,429,456-triangle kit budget and the 1,125,000-triangle agent budget, each named with what it dropped | performance |
| 0.3724 of far park-ground samples under the terrain, minimum −11.983 m | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | **verification — open, the largest such disagreement measured** |
| 15 cyclists not drawn | the fleet exports bicycle, e-bike and pedicab bodies without a rider | geometry |
| seven prop kinds unmapped | no asset exists for payphone, vending machine, memorial, artwork, drinking fountain, misc structure or passenger-information sign | data |
