# The Plaza Hotel

`landmark_the_plaza_hotel` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Plaza Hotel New York 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-12-14 11:11:39, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Plaza_Hotel_New_York_001.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the Fifth Avenue front looking up from Grand Army Plaza: the limestone base and brick shaft, the deep cornice and balustrade, the green copper mansard with its dormers and cresting, and a hard December blue sky.

**Camera** — 40.763869, -73.973717 (NYC_TM -2003, 7093) at z 16.1 m NAVD88 | azimuth 320.6°, pitch +7.2° | 18 mm on 36 mm (90.0° horizontal, 74° vertical, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **38.1 m** from the item's recorded viewpoint; the item's recorded azimuth is 296.3°, **24.3° away**. The lens was widened to the **18 mm floor**, the record noting the top of the subject is still cut off and the verticals converge. The walk did not move it: the view azimuth is clear for **46.9 m** against a **45.4 m** requirement — a margin of a metre and a half — the nearest built thing is **`prop_tree_honeylocust_small_bare_3` 9.8 m** away, and the nearest simulated agent a pedestrian **8.1 m** out. The ground reads 14.489 m NAVD88, the 10th percentile of 113 samples within 12 m, range 14.25 to 16.06 m.

**Sun** — azimuth 170.1°, elevation 25.4° at 2022-12-14T11:11:39−05:00, from the photograph's own **EXIF DateTimeOriginal**; 723.8 W/m² direct normal, sky at strength 0.0378, Filmic, **+2.93 stops** metered and unclamped against a linear median of **0.023641** and a target of **0.18**. The physical rule would have given **0.77 stops**.

**In the scene** — 4,500,514 triangles: 4 building tiles (222,112 tris, 0 missing, 0 LOD-substituted), 8 landmark models of which 3 can fall inside the 90.0° frame, 23,909 pavement polygons, 2,300 props, 5,719 kit pieces, 14 park-ground meshes, 51 vehicles and 258 people.

## Verdict — the closest height agreement in the pass, and the best-recognised hotel frame in it

**Thirteen centimetres.** The probe found fabric on **43 of 43 rays** and measured **76.33 m** above a ground of 15.41 m, against the catalogue's **76.2 m** for `c_the_plaza`, whose origin stands **6.2 m** from the coordinate. That is the third closest probe-to-catalogue agreement in the pass and, at 6.2 m, one of the closest coordinates. The plan extent is **109.0 m by 96.7 m** and the sightline is strong: **12 of 13** rays clear, **11 on the subject**, a visible fraction of **0.846**, with the nearest own fabric at 47.1 m.

**And the picture reads as the Plaza.** The render carries the massing, the arched ground-floor openings with **green awnings** over them, a green copper band at the roofline, a rank of **yellow taxis** along the kerb, lamp standards, Central Park's lawn at the right edge and a crowd of pedestrians on the plaza. A reader shown the render alone would name the building. Of the sheets written so far only Prospect Park's Boathouse and the Queensboro Bridge do that as clearly.

**What is missing is the top and the surface.** The mansard's dormers and cresting, the balustrade and the cornice's depth are not in the render — at the 18 mm floor with a +7.2° tilt the crown is cut off, and what is in frame is a flat brick field with dark window rectangles. Measured: chroma **0.0672** against the photograph's **0.1805**, a ratio of **0.372**, and contrast at **0.813** of the reference's. Limestone against brick against green copper under a hard low Sun is more colour and more range than a single brick tone.

**The canopy is right, and it is why the sightline is not perfect.** `leaf_off` is true for 14 December and the trees are the **bare** honeylocust variants by name — `prop_tree_honeylocust_small_bare_3`, `prop_tree_honeylocust_medium_bare_12` — matching the reference. The one blocked ray stops on the second of those at 20.8 m, which is a bare tree correctly in the way.

## What matches

* **The height, to 0.13 m** — 76.33 m measured against a catalogued 76.2 m, on 43 of 43 rays, from a coordinate 6.2 m off the origin.
* **The sightline** — 12 of 13 clear, 11 on the subject, a visible fraction of **0.846**.
* **The building is recognisable** — massing, arched ground floor, green awnings, the copper roof band, and the taxi rank at the door.
* **The bare canopy, by name** — the placed assets are the `*_bare` honeylocust variants for 14 December (J97's working half).
* **Central Park's drives are car-free** — **10 vehicles dropped** (J95).
* **Grand Army Plaza is paved as a plaza** — 23,909 pavement polygons with **0 dropped**, including **653 plaza** and 516 crosswalk.
* **The block is furnished** — 199 Citi Bike stations in the source rows, 133 cooling towers, 83 street lamps on the 30–40 m rule, 59 hydrants, **31 park post lamps** from OSM, 30 buses in the GTFS rows, **8 subway entrances**, 8 LinkNYC kiosks, 11 bus-stop shelters, 1 newsstand.
* **The park ground is exact near the camera** — within 150 m, **900 samples**, an under-fraction of **0.0078**, a median clearance of **0.16 m**.

## What does not match

* **The mansard, its dormers and cresting, the balustrade and the cornice are absent**, and the crown is cut off at the 18 mm floor.
* **Two fifths of the photograph's colour** — chroma **0.372** — and **0.813** of its contrast.
* **The render is brighter at the midtone** — p50 **0.5005** against **0.3109**, a ratio of **1.61**, mean **1.356×**. The photograph's median sits **1.193 stops below** the grey convention and the render's **0.253 above**, a **+1.446-stop** difference (J83).
* **The frame is not comparable on proportion**, by the record's own words.
* **Kit was capped to under a third** — **5,719 pieces of 19,547 in range** at a **1,135,732-triangle** budget; the openings are drawn rather than cut (Stage 34 / J51).
* **The clearance margin is a metre and a half** — 46.9 m of clear view against a 45.4 m requirement, the tightest in the pass after the Riverside Church sheet.
* **A pedestrian stands 8.1 m from the lens**, nearer than any built thing but a tree, and neither the walk nor the sightline counts it (J98).
* **Beyond 400 m the park ground reads under the terrain on 54 % of 692 samples** — the worst far-field reading on any sheet written so far, and it is Central Park, where the park ground matters most.
* **3,910 agents were dropped** — 1,198 pedestrians at the agent triangle budget, 475 vehicles at the budget, **422 in the carriageway without crossing**, **149 where the planimetric data has no sidewalk** (J101), 33 cyclists the fleet exports without a rider, 10 on car-free park drives, 3 vehicles where there is no roadway.
* **No cloud.** The reference's sky is a clear hard December blue; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no mansard dormers, cresting, balustrade or cornice depth | the crown is above the 18 mm floor's frame, and dormers, copper cresting and balustrades are not classes this build models | geometry + verification — declared |
| chroma 0.372, sd 0.813 | one brick tone against limestone, brick and green copper under a hard low Sun, and a photograph developed 1.193 stops below the grey convention (J83) | geometry + reference |
| 5,719 kit pieces of 19,547 | the kit triangle budget at 1,135,732 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| a pedestrian 8.1 m from the lens | the walk and the sightline count built fabric only, by J49's declared decision, and nothing acts on the agent distance the record publishes (J98) | verification — open (J98) |
| 54 % of far park-ground samples under the terrain | the park builder drapes on its own heightmap and the scene's coarsens to 40 m at the edge; the redrape closes the near field to an under-fraction of 0.0078 and leaves this tail (J71) | **geometry — open, and worst here of any sheet written so far** |
| 258 people of 2,286 asked, 149 off a walkable surface | the agent triangle budget plus the crowd's walkable test, which cannot read Central Park's paths (J101) | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
