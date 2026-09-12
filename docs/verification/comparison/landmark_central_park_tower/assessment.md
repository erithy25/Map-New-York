# Central Park Tower (Billionaires' Row)

`landmark_central_park_tower` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Central Park Tower February 2023 010.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-02-25 12:14:03, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:Central_Park_Tower_February_2023_010.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.76563, -73.98219 (NYC_TM -2616, 7320) at z 26.0 m NAVD88 | azimuth 51.7°, pitch +33.9° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, portrait) | 904x1206. Position and heading both come from the photograph: its own EXIF camera GPS, **78.3 m** from the item's recorded viewpoint, and 51.7° is the bearing from there to the subject, 3.8° from the item's own azimuth. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+33.9°**, and the top of the subject is still cut off: `lm_c_billionaires_row.43` stands 466 m above the lens at 138 m, **73° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the azimuth closed **48 m** ahead against the **69.2 m** needed — so the camera was **moved 106.8 m** onto the nearest surveyed roadbed, ranked on how much of the subject it sees. The record then states the walk's own failure: *No point within 80 m had 69 m of open air along the view azimuth with nothing built inside 8 m of the lens*, so **the frame is closed off 18 m ahead** and the nearest built thing is `prop_lamp_cobra_davit_216` **8.4 m** away. Ground under the camera reads **24.36 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 23.28 to 24.63 m.

**Sun** — azimuth 181.7°, elevation 40.2° at 2023-02-25T12:14:03−05:00, from the photograph's own **EXIF DateTimeOriginal**; 842.8 W/m² direct normal, sky at strength 0.0335, Filmic, **+5.49 stops**, declared: *under-lit: the scene needed +5.49 stops to read as a picture, more than the 4 a photographer recovers hand-held*. The linear frame's median is **0.004002** against a target of 0.18; the physical rule would have given **+0.10 stops** (J83).

**In the scene** — 4,500,092 triangles: 4 building tiles (202,434 tris, none missing, none LOD-substituted), 10 landmark models of which 2 fall inside the 73.7° frame — **neither is the subject** — 24,965 pavement polygons with **0 dropped**, 1,416 props, 6,033 kit pieces, 15 park-ground meshes over 187 surfaces with **2,814 faces cut** for landmark ground, 1 structures tile (21,408 tris), 52 vehicles and 243 people, terrain 86,332 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — a visible fraction of 0.769 for a 477-metre tower, and all ten of the rays that scored it landed on a tan brick wall twenty-two metres from the lens, because that wall belongs to the same composite

**Read the two sightline counters together.** `subject_rays_on_subject` is **10**; `subject_rays_on_own_fabric_nearer_than_recorded` is also **10**. Every ray that counted toward the 0.769 struck fabric nearer than the recorded coordinate — `lm_c_billionaires_row.41`, at **22.5 m** — while the subject's own coordinate is **138.3 m** away. The tower is not what those rays hit. They hit a neighbouring building that happens to be a member of the same landmark composite, and the sightline treats any member as the subject.

**This is a distinct failure mode inside J94's family and it is worth stating separately.** J94 is about the probe measuring the wrong member. This is the sightline *counting* the wrong member: a composite that contains a whole street corridor — Billionaires' Row — will certify a view of any building in it as a view of any other. The record does publish both counters, which is the only reason the fault is visible; nothing acts on their agreement.

**The picture confirms it.** A tan brick wall fills the centre and lower half of the frame, a cobra-head mast crosses it, and above the parapet there are fragments of two glass towers and a slice of sky. The subject — a 477 m tower that the probe measured correctly over **43 of 43** rays, extent **101.3 m by 89.4 m**, with the nearest catalogue origin (Carnegie Hall, 175.9 m away, 55.2 m tall) properly refused (J74) — is not identifiable in the frame.

**The walk failed and said so.** It moved 106.8 m, reported that no point within 80 m satisfied its own rule, and settled for a frame **closed off 18 m ahead** against the 69.2 m this composition needs. As on `landmark_30_hudson_yards`, that recorded failure did not stop the sheet being published or the runner marking the frame usable (J92's other half).

**The colour runs backwards here, and for a legitimate reason.** Chroma **0.0737** against the photograph's **0.0504** — a ratio of **1.462**, the only sheet in this queue where the render is *more* saturated than its reference. The photograph is a grey February overcast against grey-blue glass; the render's frame is a warm brick wall in sun. The median is **0.742×** because the reference sits **1.189 stops** above the grey convention and the render **0.246** above it, a **0.943-stop** difference (J83).

## What matches

* **The probe is exact on the subject**: 43 of 43 rays, **476.54 m** above a ground of 13.81 m, plan extent 101.3 m by 89.4 m — a correct measurement of a 477 m tower, taken from the geometry with the catalogue refused because the nearest origin is 175.9 m away and belongs to Carnegie Hall (J74).
* **The record publishes the counter that exposes its own fault** — `subject_rays_on_own_fabric_nearer_than_recorded: 10` beside `subject_rays_on_subject: 10`.
* **The walk's failure is recorded verbatim**, with the 48 m closure, the 106.8 m move, the 69.2 m requirement and the 18 m result all in the record.
* **The under-lit development is declared with its number**, +5.49 stops, and the record says that is past hand-held recovery (J83).
* **The day type and season are right and were read**: bare canopies for 25 February, and the crowd clock reads **Saturday** for a date that was a Saturday.
* **The pavement is complete**: 24,965 polygons, **0 dropped**, including 9,961 white markings, 6,505 sidewalk, 4,067 roadbed, 2,959 curb and 535 crosswalk.
* **The landmark-ground rule did real work**: **2,814** park-ground faces cut.
* **Agents carry the widest detail spread in this queue**: of 52 vehicles, 8 at LOD1 and 1 at LOD0; of 243 people, 41 at LOD1 and 6 at LOD0.

## What does not match

* **The 0.769 visible fraction is measured against a wall 22.5 m from the lens**, not against the tower 138.3 m away.
* **Neither landmark in the frustum is the subject** — the Billionaires' Row composite at 426.8 m, 65.1° off axis, and the Central Park perimeter wall at 2,415.8 m.
* **The frame is closed 18 m ahead** against a 69.2 m requirement, and was published anyway.
* **The frame is 5.49 stops under a photographable level.**
* **The top of the subject is cut off** at the 18 mm floor; the tower needs 73° of elevation at 138 m.
* **The median is 0.742× and the chroma 1.462×** — both driven by the two frames containing different materials under different weather, 0.943 stops of development apart.
* **6,033 of 48,994 kit records were drawn**, capped at a 982,470-triangle budget — the second worst shortfall in the pass. It is why the tan wall filling the frame has no windows in its lower half and why the towers above it are bare.
* **Fifty-eight per cent of the props are missing**: 1,416 placed of **3,405 in range**, with **1,803 dropped for the triangle budget** of 1,112,181 and 9 on a suppressed building.
* **Only 25 of 262 trees are drawn from modelled branches**; **1,703 tree rows** did not fit the props budget, **0** of the 237 cards are procedural canopy stems, 6 cards were dropped and **2** instances were scaled out of band.
* **Three of 4 structures tiles in range have no structures file**, under the Columbus Circle and 57th Street interchanges.
* **There is no park ground within 150 m to check** — 0 samples. Beyond 400 m the park surface sits under the terrain on **0.4078** of 1,599 samples, minimum **−4.981 m**, with a z-fighting fraction of **0.0482** — the worst far-band figures in this queue, and that band is Central Park's southern end (J85).
* **Fifteen props across five kinds were wanted in range and have no asset**: 4 artwork, 3 misc structure, 3 payphone, 3 passenger-information sign, 2 drinking fountain.
* **Six park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, park grass, recreation grass, rink ice, bare ground (J40).
* **The crowd is a fifteenth of the ask**: the table wanted 714 vehicles and 3,583 people; 905 and 3,000 were simulated and **3,610** dropped — **1,340** pedestrians and 385 vehicles at the agent triangle budget, 1,139 pedestrians and 394 vehicles outside the radius, 204 pedestrians in the carriageway without crossing, 54 not on a walkable surface, 40 vehicles not on a carriageway, 17 pedestrians inside a building, 3 above the observer, and **34 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| visible fraction 0.769 scored on a wall 22.5 m away | the sightline counts a hit on any member of the landmark composite as a hit on the subject, and `c_billionaires_row` is a whole street corridor. Both counters are published and nothing compares them — J94's family, on the counting rather than the measuring | **verification — open** |
| the frame is closed 18 m ahead, and published | the walk found no compliant point within 80 m and the usability test reads only the frame's mean and standard deviation (J92's other half) | **verification — open** |
| +5.49 stops, under-lit | a February street canyon at 40.2° sun elevation with a brick wall 22 m from the lens; declared with its number (J83) | verification — declared |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 73° at 138 m | **verification — declared limit** |
| p50 0.742×, chroma 1.462× | grey overcast glass against a sunlit brick wall, 0.943 stops of development apart (J83) | reference |
| 6,033 kit pieces of 48,994 in range | the kit triangle budget at 982,470 | **performance** |
| 1,416 props of 3,405 in range | the props triangle budget at 1,112,181, which dropped 1,803 | performance |
| 1,703 tree rows dropped, 0 canopy stems | the props budget, and no mapped woodland polygon in this radius | performance + declared rule |
| 3 of 4 structures tiles without a file | no structures file was built for those tiles | **data — open, three tiles unbuilt** |
| 0.4078 of far park ground under the terrain, min −4.981 m, z-fighting 0.0482 | the terrain grid coarsens to 40 m beyond the near band across Central Park's southern end (J85) | geometry — open, measured |
| 15 props across five kinds unmapped | no asset exists for those kinds | data |
| six park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 243 people where the table asked 3,583 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
