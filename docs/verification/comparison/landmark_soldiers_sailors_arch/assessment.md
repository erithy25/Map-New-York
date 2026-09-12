# Soldiers' and Sailors' Memorial Arch (Grand Army Plaza, Brooklyn)

`landmark_soldiers_sailors_arch` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn, NYC (2020) - 30.jpg by Another Believer, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-02-22 14:33:47, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn,_NYC_(2020)_-_30.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.67306, -73.97056 (NYC_TM -1738, -2992) at z 43.6 m NAVD88 | azimuth 97.7°, pitch +0.4° | 18 mm on 36 mm (89.7° horizontal, 58° vertical) | 1280x720. Position and heading both come from the photograph: its own EXIF camera GPS, **231.0 m** from the item's recorded viewpoint, and 97.7° is the bearing from there to the subject. The item's recorded azimuth of 170.0° is **72.3° away** and belongs to its nominal viewpoint on the plaza island. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+0.4°**: the top of `lm_b_soldiers_sailors_arch.0` stands 27 m above the lens at 55 m, **26° above the horizon**, against a 58° vertical frame. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was **not moved** — the viewpoint is in open air, the view azimuth clear for **150 m** against the **27.6 m** this frame needs — and the nearest built thing in the frame is `prop_lamp_cobra_davit_0` **12.3 m** away at 29.9°. Ground under the camera reads **41.979 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 41.8 to 42.84 m.

**Sun** — azimuth 221.6°, elevation 29.2° at 2020-02-22T14:33:47−05:00, from the photograph's own **EXIF DateTimeOriginal**; 763.1 W/m² direct normal, sky at strength 0.0360, Filmic, **+0.72 stops and not clamped**. The linear frame's median is **0.109339** against a middle-grey target of 0.18, so this frame arrived nearer a photographable level than any other in the queue — the physical rule's **+0.56 stops** and the meter's **+0.72** are 0.16 stops apart, the closest the two rules come on any sheet (J83).

**In the scene** — 4,500,097 triangles: 4 building tiles (427,998 tris, none missing, none LOD-substituted), 3 landmark models, **all 3 inside the 89.7° frame**, 26,557 pavement polygons with **0 dropped**, 1,989 props, 4,076 kit pieces, 16 park-ground meshes over 319 surfaces, **0 triangles of structures**, 50 vehicles and 354 people, terrain 87,990 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the arch is the right arch in the right place at the right proportion, and it is bare stone: every bronze on it, including the quadriga, is massing without sculpture

**This is the strongest landmark geometry in the queue so far.** The subject is found at 55.1 m and measured with **43 of 43** probe rays on built fabric. The plan extent is measured off the object — **9.9 m by 9.2 m** — and the sightline lands 6 of 13 rays on the arch itself, visible fraction **0.462**, with no ray passing into nothing. The frame is exposed almost exactly as the photograph was. Both halves show a triumphal arch of the same width-to-height ratio, flanked by bare winter trees, over a plaza carrying traffic.

**The catalogue and the probe disagree by 3.6 m, and both are right.** The probe measured **27.98 m** off `lm_b_soldiers_sailors_arch.0`; the catalogue entry 0.6 m away carries **24.38 m**. I read the model to settle it: `b_soldiers_sailors_arch.glb` puts `ssa_atticcap` top at exactly **24.380** m, the catalogue's figure, and above it a `quadriga` mesh spanning 24.380 to **29.680** m. So the catalogue records the arch's stone and the probe's ray struck the bronze group standing on it. Nothing is wrong here — it is worth stating because a 3.6 m gap between a probe and a catalogue entry is normally a fault, and on this sheet it is the sculpture.

**What is wrong is that the sculpture is only a shape.** The quadriga is in the model at **252 triangles** over a 5.300 m rise, so the render carries a low massing block where the photograph carries four bronze horses, a winged Victory and two attendants. The same is true of everything else the photograph is actually about: the two bronze relief groups on the pylon faces, the spandrel figures, the inscribed frieze and the interior bas-reliefs are all absent, and the arch renders as unmodulated pale stone. That is the honest content of this comparison: **the massing is right and the surface is empty.**

**The colour gap is the largest in this queue and says the same thing.** Chroma **0.0605** against the photograph's **0.2419** — a ratio of **0.25**. The photograph's saturation is a February blue sky, oxidised copper green, brown branches and warm limestone. The render has a Nishita dome at strength 0.0360, one flat stone colour, and no copper anywhere.

## What matches

* **The height probe is complete and the extent is real**: 43 of 43 rays on built fabric, 27.98 m above a ground of 42.8 m, extent 9.9 m by 9.2 m from the bounding box of the object measured (J74).
* **The probe, the catalogue and the model all agree once the quadriga is accounted for** — 24.380 m of stone, 29.680 m to the top of the bronze, and a ray at 27.98 m in between.
* **The exposure is the closest to physical in the queue**: metered +0.72 stops against the physical rule's +0.56, unclamped.
* **The season is right, and it was read rather than assumed.** The props are placed with **bare canopies** for a 22 February date, which is why both halves show branch structure and no foliage.
* **The day type is right too**: the crowd clock reads Saturday for 2020-02-22, which was a Saturday, so the density profile used is the real one for that date.
* **The woodland canopy rule contributes here for the first time in this queue**: of 1,252 impostor cards, **804 are procedural canopy stems** placed by rule inside mapped woodland polygons, which is what puts Prospect Park's tree line behind the arch. 84 more trees are drawn from their modelled branches.
* **All three landmark models in range are in the frame** — the arch at 55.7 m dead on axis, the Central Library at 231.9 m and the Brooklyn Museum at 623.3 m — and the frustum's 0.0° off-axis figure for the subject is the only exactly-correct one in this queue.
* **The pavement is complete**: 26,557 polygons, **0 dropped**, including 7,188 white markings, 6,491 sidewalk, 6,430 roadbed, 3,175 curb, 2,128 median and 542 crosswalk.
* **Near-field ground is sound**: within 150 m, the park surface clears the terrain on all but **0.0051** of 591 samples, median **+0.185 m**, minimum −0.026 m.
* **The crowd is nearly the full ask for once**: the table wanted 1,383 people and **2,290** were simulated, of which 354 are drawn.

## What does not match

* **The quadriga is a 252-triangle massing block**, not a bronze group of horses, Victory and attendants.
* **Every relief is absent**: the two pylon bronzes, the spandrel figures, the frieze inscription and the interior bas-reliefs. The photograph's subject matter is precisely this ornament.
* **The stone is one flat colour.** No banding, no weathering, no joint pattern — the arch reads as a plaster model at 55 m.
* **Chroma is 0.25 of the photograph's**, 0.0605 against 0.2419, the widest colour gap in this queue.
* **The render is flatter and darker**: standard deviation **0.1741** against **0.1882** (**0.925×**), mean **0.4575** against **0.5532** (**0.827×**), median **0.4964** against **0.5448** (**0.911×**). The two exposure offsets from the grey convention are **+0.227** and **+0.519** stops, **0.292 stops** apart, so some of the mean gap is the photograph's own development (J83).
* **No cloud and no sky colour.** The reference's clear February blue is a single Nishita dome at strength 0.0360.
* **A cobra-head mast closes 7 of the 13 subject rays** — `prop_lamp_cobra_davit_4` at 17.0 m — so the visible fraction of 0.462 is a street lamp's doing, and the clearance walk weighs built fabric and never weighs a lamp (J88).
* **A simulated pedestrian stands 8.8 m from the lens** at 44.8°, just inside the 8 m the walk enforces against geometry and never applies to the crowd (J91).
* **No structures at all**: **0 tiles imported, 4 without a file, 0 triangles** — and Grand Army Plaza sits directly over the Brooklyn IRT junction.
* **The Central Library is a plain slab.** At 231.9 m it contributes massing only; its limestone pylons and gilded entrance figures are not modelled, which matters because they are the second thing in this view.
* **36,493 kit records were in range and 4,076 were drawn**, capped at a 1,122,226-triangle budget.
* **4,603 tree rows did not fit** the props budget of 1,188,361 triangles, 14 impostor cards were dropped, 564 species were substituted, and **2** tree instances were scaled out of band.
* **Beyond 400 m the park surface sits under the terrain on 0.4075 of 1,124 samples**, minimum **−2.787 m** — the worst far-band figure in this queue, and it is Prospect Park's own ground (J85).
* **Seven park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, greenstreet grass, park grass, pool water, recreation grass, bare ground (J40).
* **Twenty-five props across seven kinds were wanted in range and have no asset**: 13 artwork, 4 drinking fountain, 3 misc structure, 2 parks building, 1 memorial, 1 parks comfort station, 1 passenger-information sign. On this plaza, "artwork" and "memorial" are the Bailey Fountain and the plaza's own bronzes.
* **705 pedestrians were dropped for standing in the carriageway while not crossing** — the largest single drop reason on this sheet, and a sign the walkable surface under Grand Army Plaza's islands is thinner than the plaza is.
* **The traffic reads as a parked row.** 50 vehicles are drawn across the middle distance at similar headings; the photograph's plaza carries moving traffic at mixed angles.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the quadriga is a 252-triangle block | the landmark builder models massing; sculpture is not a class this build authors | **geometry — declared scope** |
| every bronze relief absent, stone one flat colour | the same, plus no per-building facade colour or relief mapping (J66 remainder) | geometry — declared scope + **data, open** |
| chroma 0.25× | flat stone, no copper, and a single-dome sky with no historical colour | consequence of the two rows above + reference |
| probe 27.98 m against a 24.38 m catalogue entry | the catalogue records the arch's stone to the attic cap and the probe's ray struck the quadriga standing on it, 24.380 to 29.680 m in the model — not a fault | **verification — resolved here** |
| visible fraction 0.462 | a cobra-head mast at 17.0 m across 7 of 13 rays; the walk weighs built fabric and not lamps (J88) | verification — open |
| a pedestrian 8.8 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| no structures on any tile | 4 tiles in range and none has a structures file, over the Brooklyn IRT junction | **data — open, four tiles unbuilt** |
| the Central Library is a plain slab | massing-only landmark, as above | geometry — declared scope |
| 36,493 kit records in range, 4,076 drawn | the kit triangle budget at 1,122,226 | performance |
| 4,603 tree rows dropped | the props triangle budget at 1,188,361 triangles | performance |
| 0.4075 of far park ground under the terrain, min −2.787 m | the terrain grid coarsens to 40 m beyond the near band, over Prospect Park's own survey shape (J85) | geometry — open, measured |
| 705 pedestrians dropped in the carriageway | the walkable surface under the plaza islands is narrower than the plaza, so the simulation puts bodies where the planimetric data has no sidewalk | **data — open, measured** |
| 25 props across seven kinds unmapped | no asset exists for those kinds | data |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| traffic reads as a parked row | 50 vehicles from one simulation frame at a junction where most are queuing; not a modelling fault, a sampling one | verification |

## Measured for this assessment

Four figures above are not in the render record. The record reports a probe height of 27.98 m and a
catalogue height of 24.38 m for the same object 0.6 m apart, and only the model can say why they
differ. Read with `blender_out/landmarks/b_soldiers_sailors_arch.glb`, 26 meshes, bounds taken from
each primitive's POSITION accessor on the glTF up axis.

| figure | where it comes from |
|---|---|
| 24.380 | top of `ssa_atticcap` — exactly the height the catalogue entry carries, so the entry records the arch's stone |
| 29.680 | top of `quadriga`, the highest vertex in the model |
| 5.300 | the quadriga's own rise, 24.380 to 29.680 m, which is where the probe's 27.98 m ray landed |
| 252 | triangles in the `quadriga` primitive, over a plan of 9.2 by 9.9 m |
