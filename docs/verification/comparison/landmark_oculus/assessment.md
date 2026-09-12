# World Trade Center Transportation Hub (Oculus)

`landmark_oculus` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Oculus (36813913993).jpg by Billie Grace Ward from New York, USA, CC BY 2.0 (https://creativecommons.org/licenses/by/2.0), taken 2017-08-15 08:32, 1920x1281. [Commons page](https://commons.wikimedia.org/wiki/File:Oculus_(36813913993).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.711450, -74.010300 (NYC_TM -5095, 1273) at z 9.6 m NAVD88 | azimuth 274.2°, pitch +0.3° | 34 mm on 36 mm (56.2° horizontal) | 1280x854. The camera stands on **this photograph's own EXIF GPS**, 30.3 m from the item's recorded viewpoint, and was **not moved**. The ground under it reads 8.004 m NAVD88, the **10th percentile of 113 samples within 12 m**, range 7.91 to 8.6 m. The view azimuth is clear for 66 m; the nearest built thing in the frame is `prop_lamp_cobra_davit_17` **26.7 m** away and the nearest simulated agent is `agent_veh_camry_black_car_206.48` **11.4 m** away at 28.1° off axis.

**Sun** — azimuth 94.1°, elevation 26.3° at 2017-08-15T08:32:00−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 733.9 W/m² direct normal, sky at strength 0.0373, Filmic, **+4.02 stops**, marked **under-lit**: *"the scene needed +4.02 stops to read as a picture, more than the 4 a photographer recovers hand-held."* The linear median is **0.011111**. The physical rule would have given **0.71 stops**.

**In the scene** — 4,500,139 triangles: 4 building tiles (106,490 tris), 12 landmark models of which 1 falls inside the 56.2° frame, 21,643 pavement polygons, 1,415 props, 5,481 kit pieces, 19 park-ground meshes with **53,345 faces cut for landmark ground**, 43,576 triangles of structures, 50 vehicles and 264 people.

## Verdict — the best-modelled landmark in the pass, and J74 is the reason this sheet does not claim a 29 m canopy is 329 m tall

**The Oculus is unmistakable in the render.** The white steel ribs sweep across the upper half of the frame in the right curve, splayed at the right pitch, with the spine reading as a spine. Of every landmark model opened in this pass this is the one that most looks like the thing it is named after — it is not an extruded footprint with a texture, it is the shape.

**And the height rule saved the sheet from a gross error.** The nearest landmark model origin is `b_wtc_site`, **166.7 m** away with a catalogue height of **329.2 m** — that is One World Trade Center, not the Oculus. Under the old rule, which looked for an origin within 120 m and took its catalogue height, this sheet would have been outside that radius and fallen through; had the radius been a little wider it would have reported the transit hall's canopy as **329 m tall**. Instead the probe measured the geometry: **43 rays, all 43 landing on built fabric**, **29.44 m** above a ground of 4.27 m, on an object whose plan extent is **83.3 m by 66.4 m**. That is the canopy. This is J74 doing precisely the job it was written for.

**The brightness difference is the photograph's own decision, not the render's.** The reference is a deliberately bright frame — a white sky behind white steel — developed **2.046 stops above** the middle-grey convention, with its median at **0.8774** and its 95th percentile at **0.9684**. The render sits at the convention, **0.241** stops over, with a median of **0.4986**. The **1.805-stop** difference between those two choices is the whole of the mean ratio of **0.644** (J83). The render is not dark; the photograph is bright on purpose.

## What matches

* **The canopy is the canopy.** Ribs, spine and sweep, at the same place in the frame as the photograph's and in the same white.
* **Its height is measured off its own geometry** — 29.44 m from 43 rays, all landing on fabric, with the catalogue's 329.2 m correctly refused as belonging to a different building 167 m away (J74).
* **The view is the photograph's own.** Azimuth **274.2°** from its GPS to the Oculus; the item's recorded azimuth is 282.4°, **8.2° away**, and was not used. The lens barely moved, from 35 mm to **34 mm**, because the subject is wide rather than tall.
* **The sightline is honest about a partial view.** 13 rays, **10 clear**, **7 on the subject**, fraction **0.538**: half the fan lands on the canopy and the rest goes past it or stops at **26.8 m** on a street lamp. Looking at the render, that is right — the canopy fills the upper left and the upper right is tower and sky.
* **The plaza's own ground is cut into the park ground.** **53,345 faces cut for landmark ground**, the largest such count in the pass, which is what the WTC plaza is: a landmark surface standing over the terrain rather than on it.
* **The near ground is clean.** Within 150 m the under-fraction is **0.0** over 526 samples, minimum clearance **0.049 m**, median **0.181 m**.
* **The kerb-side furniture is dense and right for the block**: **41 subway entrances**, 44 vent grates, 182 street lamps, 22 bus-stop signs, 19 flagpoles, 66 benches.
* **Citi Bike is a station**: 372 dock units in range (Stage 40).
* **The crowd clock is right** — **a weekday** for 2017-08-15, which was a Tuesday — and the fleet is a Financial District weekday fleet: **30 sedans, 9 SUVs, 8 yellow taxis**, a boro taxi, a box truck and an NYPD car.
* **Four people are at LOD0**, the only sheet so far with more than one agent at its best form.

## What does not match

* **Two figures stand in the near right of the frame at a scale that dominates it**, facing roughly across the view with red objects in their hands, where the photograph's foreground is empty sky. The record's nearest agent is a vehicle at **11.4 m** and 28.1° off axis; the clearance walk checks the view azimuth for *built* obstruction and does not weigh an agent standing beside it.
* **The composition is not the photograph's.** The reference is a near-abstract upward view along the rib spine with two glass towers; the render is a street-level three-quarter view across a roadway. Both contain the canopy; only one is *of* it.
* **The frame needed +4.02 stops** and is marked under-lit — more recovery than the four stops the note says a photographer gets hand-held. An 08:32 sun at **26.3° elevation and 94.1° azimuth** is almost directly behind a view pointing 274.2°, so the frame is back-lit and everything facing the lens is in its own shade.
* **Two-thirds of the photograph's colour** — chroma **0.0399** against **0.0613** (**0.651×**). Both are nearly grey; the render is greyer.
* **Slightly less contrast** — standard deviation **0.2114** against **0.2281** (**0.927×**) — the closest contrast agreement in the pass, on two frames of very different content.
* **The traffic is queued nose to tail** across the near roadway, five dark sedans in a rank where the photograph has none.
* **5,267 of 5,481 kit pieces are windows**, against 7 cornices, 8 string courses, 6 pilasters and 3 quoins. Kit was capped by a **1,039,319-triangle** budget with **16,500 pieces in range**.
* **1,831 tree rows did not fit the props budget**, and the trees that were placed are scaled small — mean scale **0.815**, the lowest in the pass, with 3 out of band.
* **The 9/11 memorial's own furniture is absent.** **5 artwork and 5 memorial** props were wanted in range and had no asset.
* **The crowd is a third of the table's ask.** The density table wanted **576 vehicles and 1,936 people**; **645 and 2,265** were simulated and **2,596** dropped — 911 pedestrians outside the radius, **614 at the triangle budget**, 323 in the carriageway without crossing, 148 not on a walkable surface, 4 inside buildings, and 14 riderless bodies.
* **1 of the 4 tiles in range has no structures file.**
* **Far park ground sinks**: beyond 400 m the under-fraction is **0.1592** over 917 samples, minimum **−1.643 m** — the mildest far-band figure in the pass.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| two agents dominate the near frame | the clearance walk tests the view azimuth for built obstruction, not agents standing beside it; the nearest is recorded at 11.4 m and 28.1° off axis | **verification — open, same rule as the Flatiron sheet** |
| the composition is not the photograph's | the reference is an upward abstraction along the rib spine; the aim rule points at the subject's mid-height from a street-level eye, which cannot reproduce it | verification — declared |
| the frame needed +4.02 stops | a 26.3° sun at 94.1° behind a view along 274.2° back-lights everything facing the lens; published under-lit and marked so (J83) | reference + verification — declared |
| mean 0.644×, p50 0.568× | the photograph is developed 2.046 stops above the grey convention and the render 0.241 above it, a 1.805-stop difference; this is the photograph's exposure choice, not the render's light (J83) | reference |
| chroma 0.651× | two near-grey frames; the render's is greyer because its sky is a Nishita gradient rather than a blown white | reference |
| traffic queued nose to tail | the traffic model's signal state at this instant | verification |
| 5,267 windows against 7 cornices | shells are extruded footprints with openings cut; kit capped at 1,039,319 triangles with 16,500 in range | geometry + performance |
| 1,831 tree rows dropped, mean tree scale 0.815 | the props triangle budget, and the scale band the placement rule applies | performance + data |
| no memorial furniture | 5 artwork and 5 memorial props had no asset | data |
| 264 people against a table asking 1,936 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| 0.1592 of far park-ground samples under the terrain | surfaces draped on the 2 m heightmap against a scene edge coarsened to 40 m | verification |
