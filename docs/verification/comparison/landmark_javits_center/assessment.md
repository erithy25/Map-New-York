# Jacob K. Javits Convention Center

`landmark_javits_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Quill Depot-Javits Ctr 05.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-09-16 18:09:32, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Quill_Depot-Javits_Ctr_05.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75673, -73.99971 (NYC_TM -4198, 6301) at z 10.4 m NAVD88 | azimuth 290.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **316.3 m** away, past the 250 m rule. The recorded azimuth of 290.0° agrees with the bearing to the subject to **0.0°**. The camera was not moved — open air, azimuth clear for **141.8 m** against the 80.0 m needed — and the nearest built thing is `prop_lamp_cobra_davit_41` **13.2 m** away, dead on axis. Ground under the camera reads **8.817 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range **2.03 to 9.92 m** — a nearly eight-metre spread inside twelve metres.

**Sun** — azimuth 265.0°, elevation **9.4°** at 2017-09-16T18:09:32−04:00, from the photograph's own **EXIF DateTimeOriginal**; 412.6 W/m² direct normal — the lowest in this queue — sky at strength 0.0574, Filmic, **+4.44 stops**, declared: *under-lit: the scene needed +4.44 stops to read as a picture, more than the 4 a photographer recovers hand-held*. The linear frame's median is **0.008284** against a target of 0.18; the physical rule would have given **+2.12 stops** (J83).

**In the scene** — 4,367,655 triangles: 6 building tiles (213,370 tris, none missing, none LOD-substituted), 7 landmark models of which 2 fall inside the 54.4° frame, 32,487 pavement polygons with **0 dropped**, 1,091 props, 6,873 kit pieces, 17 park-ground meshes over 175 surfaces, 4 structures tiles (**123,024 tris**) with 2 without a file, 53 vehicles and 323 people, terrain 90,958 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the ground in front of the camera has broken into a field of angular grey facets with pedestrians standing along its ridges, and no measurement in the record describes it

**The near field is a geometry failure and the sheet does not know.** The lower right two thirds of the render is a chaotic grey surface: flat triangular facets meeting at sharp ridges, a trench running across it, and a line of simulated pedestrians standing along the crest at inconsistent heights. It is the most visible geometry break in this pass.

**The record's clearance statistics do not cover it.** They sample **park ground against terrain** — within 150 m the under-fraction is **0.0692** over 260 samples with a median of **+0.20 m** — and the broken surface here is roadway and sidewalk, which the record never measures against the terrain at all. What the record does say, at the far end, is that beyond 400 m the park surface reaches a minimum of **−10.395 m** with a first-percentile of **−6.794 m**: the deepest under-reading anywhere in the pass. And the ground sampling under the camera is itself the tell — **113 samples within 12 m ranging from 2.03 m to 9.92 m**, an eight-metre spread under one lens position, on ground that is flat in the photograph.

**So this sheet needs two measurements it does not have**: a pavement-against-terrain clearance, and any measurement at all of what fills the frame (**J92**).

**The subject is behind a lamp post.** 13 rays, **0 clear, 0 on the subject**, all stopped at **13.2 m** by `prop_lamp_cobra_davit_41` — the cobra-head mast running up the middle of the render. Visible fraction **0.000** for a building 250.5 m away whose space-frame wall is actually visible in the frame's right half. That is J88 at its most literal: a street lamp between the lens and a 183-metre-wide subject.

**The reference is the bus depot next door.** `File:Quill Depot-Javits Ctr 05.jpg` shows the Michael J. Quill depot site behind construction fencing with a partly clad steel frame — the Javits' own space-frame glass wall, which the viewpoint note names as the subject, is not what the photograph is of. Another **J93** case, and one whose date matters too: a 2017 construction photograph against a model of the completed expansion.

**What the render does well is the measurement of the subject itself.** The probe found **54.11 m** above a ground of 4.37 m over **43 of 43** rays, and the catalogue entry 32.5 m away carries **53.6 m** — within half a metre. The plan extent, **183.9 m by 151.6 m**, is the convention centre's real footprint. And the kit was **fully placed**: 6,873 of 6,873 records in range, nothing capped, nothing suppressed.

## What matches

* **The probe and the catalogue agree within half a metre** — 54.11 m against 53.6 m — and the plan extent is the real footprint (J74).
* **The kit was fully placed**: 6,873 of 6,873 in range, nothing capped or suppressed.
* **Structures carry 123,024 triangles** over 4 tiles — the Lincoln Tunnel approaches and the rail yard structures.
* **The space-frame wall is modelled** and visible in the frame's right half, with its X-braced panels reading correctly.
* **The development is metered and declared under-lit** with its number, +4.44 stops at a sun elevation of 9.4° (J83).
* **The recorded azimuth agrees with the bearing to the subject to 0.0°.**
* **The pavement data is complete**: 32,487 polygons, **0 dropped**, including **15,799** white markings, 5,836 roadbed, 5,017 sidewalk and 3,850 curb.
* **The record reports the 13.2 m blockage and the 0.000 verdict plainly.**

## What does not match

* **The ground in front of the camera has broken into angular facets and ridges**, with pedestrians standing along them, and no measurement in the record covers it.
* **The heightmap under one lens position ranges 2.03 m to 9.92 m over 113 samples within 12 m** — an eight-metre spread on ground the photograph shows as flat.
* **Visible fraction 0.000**, every ray stopped by a cobra-head mast 13.2 m from the lens (J88).
* **The reference is the bus depot site next door**, photographed during construction in 2017 (J93).
* **Beyond 400 m the park surface reaches −10.395 m** with a first percentile of −6.794 m — the deepest under-reading in the pass (J85).
* **Both frames clip at the top**: the render's ninety-fifth percentile is **0.9994** and the reference's **1.0**, so highlight comparison is void.
* **Chroma is 1.729× the photograph's** — the render is more saturated, because the reference is a dusk construction site in grey and the render carries brick and yellow taxis.
* **Thirty-seven per cent of the props are missing**: 1,091 placed of **2,975 in range**, with **1,753 dropped for the triangle budget** of 1,185,854, 24 on a suppressed building and 5 cards dropped.
* **1,723 tree rows did not fit** that budget; 52 of the 251 cards are procedural canopy stems and 71 trees are drawn from modelled branches.
* **Two of 6 structures tiles have no structures file.**
* **Twenty-five props across seven kinds were wanted in range and have no asset**: 17 misc structure, 3 drinking fountain, 1 artwork, 1 parks building, 1 parks comfort station, 1 passenger-information sign, 1 vending machine.
* **Four park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a tenth of the ask**: the table wanted 1,120 vehicles and 3,105 people; 1,381 and 2,999 were simulated and **4,004** dropped — 999 pedestrians and 374 vehicles at the agent triangle budget, **365** pedestrians in the carriageway without crossing, 281 with no sidewalk under them, 66 vehicles with no roadway, and **25 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the ground has broken into facets and ridges | a terrain and roadway surface disagreement in the near field, on a tile where the heightmap itself spans eight metres inside twelve; the record measures park ground against terrain and never pavement against terrain, and measures nothing about the frame's content (J92) | **geometry — open, and unmeasured: two missing measurements** |
| an eight-metre heightmap spread under one lens position | the 1 m DEM carries building grades and raised plinths at the West Side rail yard edge, and the 10th-percentile rule picks a usable value from a range that should not exist on a flat street | **data — open, measured** |
| visible fraction 0.000 | a cobra-head mast 13.2 m from the lens closes every ray to a subject 250 m away; the walk weighs built fabric and not street lamps (J88) | **verification — open, J88** |
| the reference is the depot site during construction | the chooser matched the Javits' name in a title and tests neither what the photograph depicts nor whether the structure is complete (J93) | **verification — open, J93** |
| −10.395 m beyond 400 m | the terrain grid coarsens to 40 m beyond the near band across the rail yard and the Lincoln Tunnel approaches (J85) | geometry — open, measured |
| both frames clip at the top | a 9.4° sun into the lens in one and a dusk sky in the other | reference |
| chroma 1.729× | a grey dusk construction site against brick and taxis | consequence of the reference |
| 1,091 props of 2,975 in range, 1,723 tree rows dropped | the props triangle budget at 1,185,854 | **performance** |
| 2 of 6 structures tiles without a file | no structures file was built for those tiles | **data — open, two tiles unbuilt** |
| 25 props across seven kinds unmapped | no asset exists for those kinds | data |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 323 people where the table asked 3,105 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
