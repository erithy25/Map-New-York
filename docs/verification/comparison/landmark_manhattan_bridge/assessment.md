# Manhattan Bridge

`landmark_manhattan_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Manhattan Bridge viewed from Brooklyn.jpg by Julius Barclay, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-03-11 16:36:41, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Manhattan_Bridge_viewed_from_Brooklyn.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.703944, -73.991089 (NYC_TM -3472, 439) at z 3.5 m NAVD88 | azimuth 46.9°, pitch +0.4° | 20 mm on 36 mm (83.2° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, 77.2 m from the item's recorded viewpoint, and was **not moved**. The ground under it reads 1.897 m NAVD88 from **16 samples within 5.0 m**, range 1.57 to 1.96 m: the viewpoint note names the raised surface the photographer stood on, so the height at the point itself is the ground. The view azimuth is clear for 105 m — and the nearest built thing in the frame is `t_-4_0_park_park_ground_grass` **2.9 m** away. The lens was widened from 35 mm to 20 mm to contain a tower that tops out **30° above the horizon** at 180 m, and the record declares that the verticals converge and the frame is not comparable on proportion.

**Sun** — azimuth 241.2°, elevation 24.9° at 2024-03-11T16:36:41−04:00, from the photograph's own **EXIF DateTimeOriginal**; 718.6 W/m² direct normal, sky at strength 0.0380, Filmic, **+1.20 stops**, measured from the linear frame's median of **0.078124** (J83). The physical rule would have given **0.79 stops**.

**In the scene** — 4,500,129 triangles: 8 building tiles (208,896 tris), 2 landmark models of which 1 falls inside the 83.2° frame, 20,961 pavement polygons, 930 props, 4,244 kit pieces, 41 park-ground meshes, **114,496 triangles of structures across 8 tiles with none missing**, 15,336 quads of water, 88 vehicles and 368 people.

## Verdict — the best-built sheet in the set: the bridge is there, its height is measured off its own geometry, and the near ground is perfect; the foreground is wrong twice over

**Three measurements on this sheet are the strongest in the pass.**

**The bridge is built, all of it.** **114,496 triangles of structures across 8 imported tiles with not one tile missing a file** — the largest structures count in the set by a factor of three. The Brooklyn tower, the suspension cables, the deck and the truss are all in the render and all recognisable.

**Its height is measured off the thing rather than borrowed.** The nearest landmark model origin is **226.3 m** away, past the 120 m the old rule looked in, so the probe fell back to the geometry: **43 rays, all 43 landing on built fabric**, reporting **107.38 m** above a ground of 0.0 m. The catalogue's own figure for that model is **106.68 m**, which the probe never consulted. This is J74 working exactly as written, and the two numbers agree without being allowed to.

**The near park ground is clean.** Within 150 m the under-fraction is **0.0**, the minimum clearance **0.076 m** and the median **0.206 m** over 245 samples — the only sheet in the pass where no park surface anywhere near the camera sits under the terrain.

**And the foreground fails twice.** The photograph's near half is Pebble Beach: a field of dark rip-rap boulders running down to the East River. **The render has smooth pale paving where those boulders are** — the armour stone is not a class this build carries. Worse, **a park-ground grass polygon stands 2.9 m from the lens and crosses the entire picture as a pale green sheet lying over the paving**, with the ground visible through it. It is the nearest built thing in the frame and it is the first thing a reader sees.

## What matches

* **The bridge, in full.** Tower, cables, deck and stiffening truss, at the same point in the frame as the photograph's, with the tower leg measured at a plan extent of **11.1 m by 10.2 m**.
* **The tower's height, from geometry alone** — 107.38 m, against a catalogue 106.68 m the rule was not permitted to use.
* **The sightline is honest about what interrupts it.** 13 rays, **10 clear**, **10 on the subject**, fraction **0.769**; the three blocked stop at **36.6 m** on `prop_tree_honeylocust_large_bare_53`, a bare honeylocust — and bare honeylocusts stand in that part of the park.
* **The view is the photograph's own.** Azimuth **46.9°** from its GPS to the tower; the item's recorded azimuth is 60.7°, **13.8° away**, and was not used.
* **The water is drawn and it reflects.** **15,336 quads** on the flattened water surface — the largest water count in the set — across the East River, the Pier 1 Wetlands and the park ponds, and the bridge's reflection is in it.
* **The trees are leaf-off and the date is why.** The reference is 11 March; **131 trees are drawn from their modelled branches** within 120 m in bare-canopy form, 280 more as impostor cards out to 764 m.
* **The near park ground clears the terrain at every sample.**
* **The fleet is an outer-Brooklyn fleet, not a Midtown one**: **47 sedans, 21 SUVs, 7 yellow taxis, 5 boro taxis, 4 black cars**, a box truck, a Sanitation truck, a van and an ambulance — far more private cars and far fewer taxis than the Manhattan sheets, which is what this neighbourhood has.
* **The crowd clock is right.** **A weekday** for 2024-03-11, which was a Monday.
* **The Manhattan skyline closes the distance** where the photograph's does, and Citi Bike is a station — 183 dock units in range (Stage 40).

## What does not match

* **A park-ground polygon 2.9 m from the lens crosses the whole frame** as a translucent green plane over the paving. The park ground is built with the pavement subtracted from it, so either this polygon survived that subtraction or its authored base colour is being drawn with transparency; the sheet cannot distinguish the two.
* **The rip-rap is missing.** The photograph's foreground is a boulder field and the render's is smooth paving. Shoreline armour stone is not a class this build models.
* **The sky is a third as colourful as the photograph's.** Chroma **0.0887** against **0.2548**, a ratio of **0.348**. The reference is a deep clear March blue; the render's Nishita sky is pale. On a frame that is half sky, that is the dominant visual difference.
* **The skyline beyond is blockier and lower** than the photograph's — flat-topped extruded masses rather than the reference's varied Lower East Side profile.
* **Brighter midtones.** Median **0.4938** against **0.3761** (**1.313×**), mean **0.4799** against **0.3488** (**1.376×**). The photograph's median sits **0.625 stops** below the grey convention and the render's **0.211** above it, a difference of **0.836 stops** (J83).
* **A little less contrast.** Standard deviation **0.1844** against **0.2099** (**0.879×**).
* **The landmark model's centroid is 37.8° off axis** at **339.5 m** while the subject tower is 179.5 m away — the bridge is a long object and the frustum test reports its middle, not the part being looked at.
* **Every one of the 88 vehicles is at LOD2**, and 347 of 368 people. This frame has no agent at its best form.
* **38 people and 7 vehicles were found inside buildings** and dropped for it, alongside 418 pedestrians in the carriageway without crossing, 248 not on a walkable surface, 1,646 outside the radius, and **66 riderless bodies** the fleet exports without a rider.
* **Both budgets were hit.** Props capped at **1,147,724** triangles and kit at **1,050,667** with **9,754 pieces in range**; **2,265 tree rows did not fit the props budget**. At the agent budget a further **317 vehicles and 280 people** were dropped.
* **Far park ground sinks**: beyond 400 m the under-fraction is **0.3657** over 1,080 samples, minimum **−5.73 m**.
* **3,535 of 4,244 kit pieces are windows**, against 43 cornices, 39 string courses, 9 quoins and 8 pilasters.
* **Five prop kinds were wanted in range and had no asset**: 5 misc structure, 4 parks building, 2 drinking fountain, 1 payphone, 1 vending machine.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a park-ground polygon 2.9 m from the lens crosses the frame as a translucent sheet | either the pavement subtraction missed this polygon or its authored base colour is drawn with transparency; the record shows it as the nearest built thing in frame and the sheet cannot tell the two apart | **geometry — open, needs the polygon opened** |
| no rip-rap in the foreground | shoreline armour stone is not a class this build models | **geometry — open, no class** |
| chroma 0.348 on a half-sky frame | a Nishita sky against a deep clear March blue; nothing in this build reads a historical sky | reference — no source exists |
| the skyline beyond is blockier and lower | shells are extruded footprints from the building tiles at this distance, with kit capped at 1,050,667 triangles | geometry + performance |
| p50 1.313×, mean 1.376× | the photograph is developed 0.625 stops under the grey convention and the render 0.211 over it (J83) | reference |
| the frustum reports the bridge 37.8° off axis at 339.5 m | the test uses the model's centroid and the bridge is over a kilometre long; the subject tower is 179.5 m away and on axis | verification — a known limit of the test |
| every vehicle at LOD2 | the LOD ladder at this distance under the agent budget | performance |
| 38 people and 7 vehicles inside buildings | the placement rules caught them and dropped them, which is the rule working; that they were placed there at all is the traffic and crowd model's | verification |
| props and kit capped, 2,265 tree rows dropped | the per-frame triangle budgets | performance |
| 0.3657 of far park-ground samples under the terrain | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
| five prop kinds unmapped | no asset exists for those kinds | data |
