# Brooklyn Public Library, Central Library

`landmark_brooklyn_public_library` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn Public Library - Central Library - 2026 (55268462423).jpg by ajay_suresh, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2026-04-23 12:44, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn_Public_Library_-_Central_Library_-_2026_(55268462423).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.67318, -73.96963 (NYC_TM -1659, -2978) at z 43.6 m NAVD88 | azimuth 123.9°, pitch +5.2° | 35 mm on 36 mm (54.4° horizontal) | 1280x720. Position and heading both come from the photograph: its own EXIF camera GPS, **38.5 m** from the item's recorded viewpoint, and 123.9° is the bearing from there to the subject; the item's recorded azimuth of 140.0° is 16.1° away. The lens stayed at 35 mm and the axis was tilted **+5.2°** to the subject's mid-height, 21 m above its ground. The camera was not moved — the viewpoint is in open air and the azimuth is clear for **150 m** against the 67.5 m needed — and the two nearest things in the frame are both at 9.1° off axis: `prop_lamp_cobra_davit_1` at **8.1 m** and `agent_ped_995.7` at **7.6 m**. Ground under the camera reads **42.01 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 41.86 to 42.81 m.

**Sun** — azimuth 174.7°, elevation 61.9° at 2026-04-23T12:44−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 923.2 W/m² direct normal, sky at strength 0.0309, Filmic, **+0.66 stops and not clamped** — the smallest development in this queue. The linear frame's median is **0.113601** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,027,562 triangles: 4 building tiles (427,998 tris, none missing, none LOD-substituted), 3 landmark models of which 2 fall inside the 54.4° frame, 23,720 pavement polygons with **0 dropped**, 1,809 props, 2,999 kit pieces, 16 park-ground meshes over 319 surfaces, **0 triangles of structures**, 50 vehicles and 304 people, terrain 84,676 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — a street lamp eight metres from the lens zeroes the verdict for a building that is plainly in the picture, and next to Castle Williams this is the same chain making the opposite mistake

**The record says the subject is invisible and the picture shows it.** Of 13 rays, **0 clear, 0 on the subject**, every one stopped at **8.2 m** by `prop_lamp_cobra_davit_1` — a cobra-head mast standing 8.1 m from the lens at 9.1° off axis. Visible fraction **0.000** and `subject_visible: False`. Meanwhile the grey-brown mass filling the right two thirds of the frame is the library, 135.0 m away, and the frustum finds it 7.7° off axis. The verdict is a **false negative**, and its cause is one lamp post that J88 already names: the clearance walk clears built fabric along the azimuth and never weighs a street lamp, so a mast can sit in the middle of the frame and close every ray behind it.

**Read this sheet beside `landmark_castle_williams` and the pair is the whole argument for repairing the sightline.** There, 13 of 13 rays landed on a tile mesh spanning an island and the sheet reported **1.000** with no fort in the frame. Here, 13 of 13 rays stopped on a lamp and the sheet reports **0.000** with the building in the frame. The same measurement produces a false positive and a false negative on two sheets of the same pass, and the repair for both is in the objects it is allowed to aim at and count.

**What the render does not have is the library's front.** The photograph's subject is the splayed Art Deco entrance: two limestone wings opening to a recessed centre, a fifteen-metre gilded portal with bronze figures, the incised inscription across the entablature, and a wide flight of steps. The render has a plain rectangular block with shallow vertical ribs, meeting the pavement without steps or portal. The massing is roughly right in bulk — the probe measures **20.74 m** over **43 of 43** rays with a plan extent of **127.0 m by 95.3 m** against a catalogue entry 32.7 m away carrying 29.3 m — and everything that makes the building recognisable is absent.

**The foreground is a lamp post and a pedestrian.** The mast runs floor to ceiling through the middle of the frame, and a simulated pedestrian stands **7.6 m** away, inside the 8 m of nothing-built the walk enforces against geometry and never applies to the crowd (J91). Between them they occupy more of the picture than the subject does.

## What matches

* **The development is the smallest in this queue** — +0.66 stops from a median linear luminance of 0.113601 — which is what a genuinely bright noon frame looks like when the scene is already near a photographable level (J83).
* **Chroma is 0.832 of the photograph's**, 0.0867 against 0.1042, the second-closest colour match in this queue.
* **The height probe is complete and the extent is the real footprint**: 43 of 43 rays, 20.74 m, 127.0 m by 95.3 m (J74).
* **The camera stands 38.5 m from the item's own viewpoint** with a bearing 16.1° off its nominal azimuth, and needed no walk.
* **The pavement is complete**: 23,720 polygons, **0 dropped**, including 6,313 roadbed, 6,060 white markings, 4,973 sidewalk, 2,844 curb, 2,389 median and 507 crosswalk — and Grand Army Plaza's geometry reads correctly under the traffic.
* **Near-field ground is sound**: within 150 m, **0.0016** of 608 park-surface samples sit under the terrain, median **+0.191 m**.
* **The woodland canopy rule contributes**: **732** of the 1,101 impostor cards are procedural canopy stems, and 80 more trees are drawn from modelled branches.
* **The kit was not capped**: 2,999 placed of 3,457 in range, with 458 suppressed under the landmark shell.
* **Agents carry mixed detail**: 10 vehicles at LOD1, and of 304 people **29 at LOD1 and 4 at LOD0**.

## What does not match

* **The verdict is a false negative**: visible fraction **0.000** for a building that occupies two thirds of the frame, because one mast stands 8.1 m from the lens (J88).
* **The Art Deco portal, the splayed wings, the inscription and the steps are all absent.** The render's block meets the pavement flat.
* **A cobra-head mast and a pedestrian dominate the foreground**, the pedestrian at **7.6 m**, inside the 8 m rule (J91).
* **The render is a third darker than the photograph**: mean **0.676×**, median **0.671×**. Most of that is the reference's own development, which sits **+1.49 stops** above the grey convention against the render's +0.226 — a **1.264-stop** difference (J83) — and it is the brightest reference in this queue.
* **Contrast is 0.728 of the photograph's**, and the render's fifth percentile is **0.1843** against **0.2544**: the render is darker in the shadows and duller in the highlights at once.
* **No structures at all**: **0 tiles imported, 4 without a file, 0 triangles** — under Grand Army Plaza and the Eastern Parkway IRT.
* **A third of the props are missing**: 1,809 placed of **5,452 in range**, with **3,466 dropped for the triangle budget** of 1,199,071 and 13 on a suppressed building.
* **Beyond 400 m the park surface sits under the terrain on 0.45 of 620 samples**, minimum **−2.565 m** — the worst far-band under-fraction in this queue, and that band is Prospect Park (J85).
* **Twenty-one props across six kinds were wanted in range and have no asset**, and **13 of them are artwork**: at Grand Army Plaza that is the arch's bronzes, the Bailey Fountain and the plaza's statuary. 2 drinking fountain, 2 misc structure, 2 parks building, 1 memorial, 1 passenger-information sign.
* **Only 80 of 1,181 trees are drawn from modelled branches**; **486** species were substituted, **2** instances scaled out of band and 4 cards dropped.
* **Seven park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, greenstreet grass, park grass, pool water, recreation grass, bare ground (J40).
* **519 pedestrians were dropped for standing in the carriageway while not crossing** — the largest single drop reason here, and a sign that Grand Army Plaza's walkable surface is narrower in the planimetric data than the plaza is on the ground.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| visible fraction 0.000 for a building in the frame | a cobra-head mast 8.1 m from the lens closes all 13 rays; the clearance walk weighs built fabric and never weighs a street lamp (J88). Read with `landmark_castle_williams`, the same measurement gives a false positive there and a false negative here | **verification — open, J88 and J94 together** |
| no portal, wings, inscription or steps | the landmark builder models massing; entrance sculpture, gilding and incised lettering are not classes it authors | geometry — declared scope |
| a pedestrian 7.6 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| mean 0.676×, p50 0.671× | the photograph is developed 1.264 stops brighter than the render relative to the grey convention (J83) | **reference** |
| sd 0.728×, p05 0.1843 against 0.2544 | a flat-coloured limestone block with no relief has neither the shadow nor the highlight the real facade throws | **data — open, J66 remainder** |
| no structures on any tile | 4 tiles in range and none has a structures file, over the Eastern Parkway IRT | **data — open, four tiles unbuilt** |
| 1,809 props of 5,452 in range | the props triangle budget at 1,199,071, which dropped 3,466 | **performance** |
| 0.45 of far park ground under the terrain, min −2.565 m | the terrain grid coarsens to 40 m beyond the near band across Prospect Park (J85) | geometry — open, measured |
| 21 props unmapped, 13 of them artwork | no asset exists for those kinds, and at Grand Army Plaza that kind is the plaza's bronzes | **data — open, measured** |
| 80 of 1,181 trees from modelled branches, 486 species substituted | the props budget and a tree catalogue that does not hold most species surveyed here | performance + data |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 519 pedestrians dropped in the carriageway | the walkable surface under Grand Army Plaza is narrower in the data than the plaza is | **data — open, measured** |
