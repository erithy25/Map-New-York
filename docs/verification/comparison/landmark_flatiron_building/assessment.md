# Flatiron Building

`landmark_flatiron_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Flatiron Building, Fifth Avenue, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-17 17:39:37, 1920x2880. [Commons page](https://commons.wikimedia.org/wiki/File:Flatiron_Building,_Fifth_Avenue,_Manhattan,_New_York.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.742300, -73.989094 (NYC_TM -3302, 4698) at z 14.0 m NAVD88 | azimuth 198.5°, pitch +0.4° | 27 mm on 36 mm (47.8° horizontal, 67.3° vertical, portrait) | 852x1278. The camera stands on **this photograph's own EXIF GPS**, 40.0 m from the item's recorded viewpoint, and was **not moved**. The lens was **widened from 35 mm to 27 mm** so that a near-level axis could contain the subject at all: the top of `lm_flatiron.9` stands 84 m above the lens at 145 m, **30° above the horizon**, and the frame is only 67.3° tall. The record states the consequence itself — **the verticals converge, so this frame is not comparable with the photograph on proportion.** The view azimuth is clear for 110 m; the nearest built thing in the frame is `t_-4_4_limestone` 48.3 m away and the nearest simulated agent is `agent_ped_3886.7` **7.4 m** from the lens at 23.9° off axis.

**Sun** — azimuth 265.9°, elevation 21.3° at 2026-04-17T17:39:37−04:00, from the photograph's own **EXIF DateTimeOriginal**; 672.4 W/m² direct normal, sky at strength 0.0398, Filmic, **+4.47 stops**. That number is the most important one on this sheet. The linear frame's median luminance is **0.008111** against a middle-grey target of **0.18**, and the record marks it **under-lit**: *"the scene needed +4.47 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by."* The physical rule would have given **1.03 stops**.

**In the scene** — 4,500,149 triangles: 4 building tiles (295,276 tris), 2 landmark models of which 1 falls inside the 47.8° frame, 28,796 pavement polygons, 1,195 props, 5,169 kit pieces, 15 park-ground meshes, 51 vehicles and 236 people.

## Verdict — the building is right, the frame is published under-lit by its own measurement, and the lens that was needed to fit it makes proportion uncomparable

**Three things on this sheet are honest in a way earlier passes were not, and all three are uncomfortable.**

**The subject is measured, not assumed.** The height probe casts **43 rays and all 43 land on built fabric**, giving **85.35 m** above a ground of 12.63 m — against the catalogue's own **86.9 m** for the Flatiron, whose origin sits **4.5 m** from the recorded coordinate. The sightline then casts 13 rays, **13 clear**, **9 on the subject**, for a visible fraction of **0.692**; 6 land on the building's own nearer fabric and 4 pass into nothing above or beside it. The wedge is there, it is the right height, and the sheet can say so with numbers rather than by eye.

**The frame is dark and the record says how dark.** +4.47 stops of development is roughly a factor of twenty-two of recovery, past what the note itself calls the four stops a photographer gets hand-held. That is not a rendering defect hidden by a good-looking frame — it is the frame's honest reading. The cause is in the geometry: a 21.3° sun at azimuth 265.9° behind a view pointing 198.5° puts a late-April afternoon low and to the right, and Fifth Avenue at 24th is a canyon. The photograph was exposed for the same shade — its own median sits **1.363 stops** from the middle-grey convention, the render's at **0.235**, a difference of **1.128 stops**. After development the two means agree almost exactly, **0.5658** against **0.5615**, a ratio of **1.008**, and that agreement is the development's, not the scene's.

**The lens had to be widened and the record refuses to claim proportion.** At 35 mm the tower did not fit; at 27 mm it does, with converging verticals the photograph does not have. The note is written into the record rather than left for a reader to notice.

## What matches

* **The Flatiron is recognisably the Flatiron.** The wedge prow closes the view down Fifth Avenue at the same point in the frame as the photograph's, the bay rhythm runs up its two long faces, and it is the only landmark in the 47.8° cone — at 145.9 m, **1.6° off axis**.
* **The view is the photograph's view.** Azimuth **198.5°** is the bearing from the photograph's own GPS to the building; the item's nominal azimuth is 206.3°, **7.8° away**, and was not used.
* **The camera stands on the street, not on a plinth.** The ground under it reads 12.407 m NAVD88 from the 2 m heightmap — the **10th percentile of 113 samples within 12 m**, range 12.31 to 12.7 m, because the viewpoint note places the photographer on the traffic surface and the 1 m DEM carries building grades that would otherwise lift the camera off it.
* **The avenue is dressed.** 28,796 pavement polygons, of which **11,033 white markings, 7,253 sidewalk, 4,636 roadbed, 3,413 curb, 1,281 plaza and 654 crosswalk** — the lane lines and crossing bars in the render's foreground are surveyed geometry, not a texture.
* **The traffic is a Flatiron fleet and the crowd is a rush-hour crowd**: 51 vehicles within 320 m and 236 people within 200 m, from one frame of the simulation at 17:39 with **120 s of simulated time** behind it. Yellow cabs stand where the photograph's do.
* **The near trees are modelled, not cards.** **98 of them are drawn from their modelled branches** within 120 m; 204 more are impostor cards out to 672 m. None is a procedural canopy stem here — this frame has no mapped woodland in it.
* **The shopfronts are kit, not paint.** 350 storefronts, 44 storefront interiors, 27 bulkheads and 52 door entries stand along the frame's two sidewalks.
* **Citi Bike is a station, not a bicycle.** **293 dock units** are in range — the Stage 40 repair, which replaced one bicycle per station with a kiosk and a dock rail.
* **The park ground near the camera sits on the terrain.** Within 150 m the under-fraction is **0.0023** and z-fighting **0.0046**; the median clearance is **0.188 m**.

## What does not match

* **Proportion, and the record says so first.** The verticals converge in the render and stand straight in the photograph. This is the widened lens, and the alternative was not showing the subject.
* **The near foreground is a vehicle body at close range.** A dark delivery vehicle occupies roughly the left third of the render's frame, cut off by the edge, where the photograph has open roadway and a crossing. The clearance walk checks the **view azimuth** for obstruction and found it clear for 110 m; it does not reject an agent that stands beside the axis, and the nearest one is **7.4 m** away at 23.9°. The photograph's own foreground car sits at the bottom-right corner, far smaller in frame.
* **No clouds.** The reference is half sky and that sky is full of April cumulus; the render's is a clear Nishita gradient. **Nothing in this build reads a historical sky** — the instant is the photograph's own and its weather is not.
* **Less contrast and a darker midtone after development.** Standard deviation **0.2531** against **0.3340** (**0.758×**), median **0.4976** against **0.7105** (**0.700×**), 5th percentile **0.1418** against **0.0782**, 95th **0.9328** against **0.9496**. The photograph holds both a blown sky and a black tower; the render's tonal range is compressed between them.
* **Chroma is three-quarters of the photograph's** — **0.0858** against **0.1147**, a ratio of **0.748**.
* **The building is a tan mass where the photograph's is dark limestone with deep relief.** 52 cornices, 64 pilasters, 51 string courses and 22 parapets stand in the whole scene against **4,359 windows**: the Flatiron's rustication, its heavy terracotta cornice and its bracketed prow are extrusion plus openings, not modelled profiles.
* **The scaffolding on the photograph's lower floors is not on the render's building.** 69 scaffold pieces are in the scene; none is on the subject.
* **Four of the photograph's landmarks of the foreground are missing**: the gold-domed Sohmer Piano tower right of centre, the ornate cast-iron street clock, the billboard on the left-hand building, and the traffic signals on their poles. Signals are placed city-wide and none falls in this cone; the clock, the dome's finish and the billboard are not classes this build carries. **18 artwork, 8 memorial, 3 vending machine and 2 drinking fountain** props were wanted in range and had no asset.
* **Both budgets were hit, and hard.** Props were capped at a **1,289,944-triangle** budget and kit at **1,312,916** with **9,052 pieces in range**; at the **1,125,000-triangle agent budget** a further **220 vehicles and 1,507 people** were dropped. The density table asked for **598 vehicles and 4,965 people** over the whole simulated ring, **684 and 3,000** were simulated and **3,397** dropped in total. This frame is at the performance ceiling, and the crowd it shows is what fitted under it.
* **333 people were dropped for standing in the roadway without crossing**, 31 for no sidewalk, 20 vehicles for no roadway in the planimetric data, and **38 cyclists, e-bikes and pedicabs were not drawn at all** because the fleet exports those bodies without a rider — the photograph has a cyclist crossing the frame.
* **Far park ground sinks into the terrain**: beyond 400 m the under-fraction is **0.2622** over 698 samples, z-fighting **0.0172**, minimum clearance **−2.019 m**. Within 150 m it is clean, so this is a horizon artefact of the coarsened 40 m grid.
* **3 of the 4 tiles in range have no structures file**, leaving 384 triangles of structures in the frame.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| verticals converge; proportion not comparable | the subject tops out 30° above the horizon at 145 m and the frame is 67.3° tall, so the lens was widened from 35 to 27 mm to contain it; declared in the record | **verification — declared, not a defect** |
| the frame needed +4.47 stops | a 21.3° sun at 265.9° behind a 198.5° view puts Fifth Avenue at 24th in canyon shade; the photograph was exposed for the same shade at +1.363 stops from the grey convention. Published under-lit and marked so (J83) | **reference + verification — declared** |
| a vehicle body fills the left third of the near frame | the clearance walk tests the view azimuth for built obstruction, not agents beside the axis; the nearest agent is 7.4 m at 23.9° off axis | **verification — open** |
| no clouds | nothing in this build reads a historical sky; only the instant is the photograph's own | reference — no source exists |
| sd 0.758×, p50 0.700× | a frame recovered by 4.47 stops has its tonal range compressed; the photograph holds a blown sky and a black tower at once | reference |
| chroma 0.748× | flat authored colours on shells and park ground against a photographic reference | data |
| the tower is a tan mass without relief | the shell is extruded from a footprint with openings cut; 52 cornices and 64 pilasters stand in a scene of 4,359 windows, and the classifier has no source for a modelled terracotta front | geometry |
| no scaffolding on the subject | 69 scaffold pieces are placed in the scene from the shed dataset and none of them is on this building | data |
| no gold dome, street clock, billboard or near-frame signals | none is a class this build models; 18 artwork and 8 memorial props had no asset. Signal heads are placed city-wide and none falls in this 47.8° cone | geometry + data |
| props, kit, vehicles and people all capped | three triangle budgets — 1,289,944 props, 1,312,916 kit, 1,125,000 agents — each named with what it dropped | performance |
| 38 cyclists not drawn | the fleet exports bicycle, e-bike and pedicab bodies without a rider, so they are dropped rather than drawn riderless | geometry |
| 0.2622 of far park-ground samples under the terrain | the 40 m coarsened grid at the scene edge against surfaces draped on the 2 m heightmap | verification |
